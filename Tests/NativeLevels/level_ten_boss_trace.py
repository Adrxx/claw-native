"""Original Marrow fight, coordinate-only placements, MPSCULLY and Level 11."""
import argparse
import hashlib
import json
import signal
from pathlib import Path
from unicorn import UcError, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
    UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW, UC_X86_REG_FPSW,
    UC_X86_REG_FPTAG, UC_X86_REG_FP0)
from Tests.NativeLevels.xmidi_clock import TempoClockTrace, CLOCK_VERSION
from Tests.NativeLevelTwo.boss_trace import BossTrace, validate_plan
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, SINGLE_PLAYER_VTABLE, LETTERS
from Tests.NativeLevels.storage import exists, write_trace, load_checkpoint, restore_memory
from Tests.NativeLevels import ROOT
from Tests.NativeMenuBase.trace import Blocked


class MarrowTrace(TempoClockTrace):
    def boss_snapshot(self):
        result = BossTrace.boss_snapshot(self)
        private = int(result.get('private', '0x0'), 16)
        if private and private in self.allocations:
            result['cycle_health'] = self.word(private+0x4c0)
            result['floor_open_requested'] = self.word(private+0x4b4)
            result['floor_away'] = self.word(private+0x4bc)
            player = self.word(0x537e88)
            if player:
                result['player_reset_marker'] = self.word(self.word(self.word(player+0x6c)+0x14)+0x80)
            parrot = getattr(self, 'boss_parrot_seen', 0)
            if not parrot:
                parrot = next((a for a, size in self.allocations.items()
                               if size >= 0x450 and self.word(a) == 0x50ec6c), 0)
                self.boss_parrot_seen = parrot
            if parrot and parrot in self.allocations:
                actor = self.word(parrot+0xc)
                result.update(parrot_private=hex(parrot), parrot_actor=hex(actor),
                    parrot_x=self.word(actor+0x4c), parrot_y=self.word(actor+0x50),
                    parrot_state=self.word(self.word(parrot+0x10)+0x1c),
                    parrot_phase=self.word(parrot+0x20), parrot_mode=self.word(parrot+0x184))
        return result

    def __init__(self, *args, boss_plan, fight_only=False, source_level=10, **kwargs):
        super().__init__(*args, level=source_level, route=boss_plan, **kwargs)
        self.boss_plan = boss_plan
        self.boss_end_on_defeat = True
        self.boss_defeat_health_observed = False
        self.boss_death_callback_observed = False
        self.boss_death_callbacks = []
        self.boss_actor_seen = 0
        self.boss_checkpoint = None
        self.boss_parrot_seen = 0
        self.boss_mechanism_events = []
        self.boss_frames = []
        self.boss_placements = []
        self.boss_cheat_keys = []
        self.boss_route_functions = {}
        self.boss_route_complete = False
        self.fight_only = fight_only
        self.level_eleven_frames = []
        self.combat_context = None
        self.combat_until_ms = None
        self.combat_save_path = None
        self.combat_checkpoint_at_ms = None
        self.parrot_wait_entries = []

    def save_combat(self):
        self.combat_version = 1
        self.combat_inputs = self.checkpoint_inputs()
        self.combat_inputs['Tests/NativeLevels/level_ten_boss_trace.py'] = hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest()
        self.checkpoint_path = self.combat_save_path
        try:
            self.save_checkpoint()
        finally:
            self.checkpoint_path = None

    def resume_combat(self, path):
        payload = load_checkpoint(path)
        state = payload['state']
        inputs = self.checkpoint_inputs()
        inputs['Tests/NativeLevels/level_ten_boss_trace.py'] = hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest()
        if (state.get('combat_version') != 1 or state.get('combat_inputs') != inputs
                or payload.get('storage_sha256') != self.storage_fingerprint):
            raise Blocked('Stale or noncombat Marrow checkpoint')
        elapsed = state['milliseconds']-state['combat_context']['start']
        prefix = lambda plan: [dict(a, end_ms=min(a['end_ms'], elapsed))
                               for a in plan if a['start_ms'] < elapsed]
        if self.boss_plan[-1]['end_ms'] <= elapsed or (
                self.combat_until_ms is not None and self.combat_until_ms <= elapsed):
            raise Blocked('Combat resume needs a bound after its retained elapsed time')
        if prefix(self.boss_plan) != prefix(state['boss_plan']):
            raise Blocked('Combat resume changed the already executed plan prefix')
        from Tests.NativeEndOfLevel.trace import REZ_PATH, REZ_SHA256
        with REZ_PATH.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != REZ_SHA256:
                raise Blocked('Original archive hash mismatch')
        keep = {k: getattr(self, k) for k in ('boss_plan', 'fight_only', 'combat_until_ms',
            'combat_save_path', 'combat_checkpoint_at_ms', 'instruction_limit')}
        self.__dict__.update(state)
        self.__dict__.update(keep)
        restore_memory(path, self.machine)
        registers = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
            UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
            UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG)
        for r, value in zip(registers, payload['cpu']):
            self.machine.reg_write(r, value)
        for i, value in enumerate(payload['cpu'][len(registers):]):
            self.machine.reg_write(UC_X86_REG_FP0+i, value)
        # Match only handles already present in the hash-validated checkpoint;
        # all handles must refer to the same original archive used at startup.
        for handle, (name, position) in payload['files'].items():
            if Path(name).resolve() != REZ_PATH.resolve():
                raise Blocked('Unexpected combat checkpoint file')
            self.files[handle] = open(name, 'rb')
            self.files[handle].seek(position)
        self.boss_route_complete = False
        self.resumed_checkpoint = True
        self.play_target(self.application)

    def resume_target(self, path):
        keep = {key: value for key, value in self.__dict__.items()
                if key.startswith('boss_') or key in ('fight_only', 'level_eleven_frames', 'combat_context', 'combat_until_ms',
                    'combat_save_path', 'combat_checkpoint_at_ms', 'parrot_wait_entries')}
        def resume(application):
            self.__dict__.update(keep)
            if self.target_level == 9:
                self.target_level = 10
                self.complete_level(application, 9)
                self.resumed_checkpoint = False
            del self.play_target
            MarrowTrace.play_target(self, application)
        self.play_target = resume
        try:
            super().resume_target(path)
        finally:
            self.__dict__.pop('play_target', None)

    def play_target(self, application):
        if self.target_checkpoint and not self.resumed_checkpoint:
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.target_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        if self.combat_context is None:
            self.clock_step = 0
            self.level_two_loaded = True
            first = self.player_snapshot(application)
            self.level_two_frames = [dict(elapsed_ms=0, action='loaded', player=first)]
            self.boss_frames = [dict(elapsed_ms=0, action='loaded', boss=self.boss_snapshot(), player=first)]
            self.combat_context = dict(start=self.milliseconds, first=first,
                functions_before=self.functions.copy(), placed=set(), cheat_progress={}, saw_positive_health=False)
        context = self.combat_context
        start, first = context['start'], context['first']
        functions_before = context['functions_before']
        def observe_death(machine, address, size, user_data):
            receiver = machine.reg_read(UC_X86_REG_ECX)
            boss = int(self.boss_snapshot().get('private', '0x0'), 16)
            if boss and receiver == boss:
                self.boss_death_callbacks.append(dict(
                    receiver=hex(receiver), address=hex(address),
                    elapsed_ms=self.milliseconds-start))
        death_hook = self.machine.hook_add(UC_HOOK_CODE, observe_death,
                                           begin=0x44e0c0, end=0x44e0c0)
        def observe_wait(machine, address, size, user_data):
            receiver = machine.reg_read(UC_X86_REG_ECX)
            actor = self.word(receiver+0xc)
            parrot = self.word(receiver+0x128)
            self.parrot_wait_entries.append(dict(elapsed_ms=self.milliseconds-start,
                receiver=hex(receiver), health=self.word(actor+0x10c),
                cycle_health=self.word(receiver+0x4c0), phase=self.word(receiver+0x20),
                callback=hex(self.word(receiver+0x14)), parrot=hex(parrot)))
        wait_hook = self.machine.hook_add(UC_HOOK_CODE, observe_wait, begin=0x459830, end=0x459830)
        def observe_mechanism(machine, address, size, user_data):
            self.boss_mechanism_events.append(dict(address=hex(address),
                elapsed_ms=self.milliseconds-start, receiver=hex(machine.reg_read(UC_X86_REG_ECX)),
                marrow=self.boss_snapshot()))
        mechanism_hooks = [self.machine.hook_add(UC_HOOK_CODE, observe_mechanism, begin=a, end=a)
                           for a in (0x45ab2b, 0x45ac75, 0x4663d0, 0x467b50, 0x467c60)]
        placed, cheat_progress = context['placed'], context['cheat_progress']
        end = self.boss_plan[-1]['end_ms']
        if self.combat_until_ms is not None:
            end = min(end, self.combat_until_ms)
        while self.milliseconds-start < end:
            elapsed = self.milliseconds-start
            index, action = next((i, a) for i, a in enumerate(self.boss_plan)
                                 if a['start_ms'] <= elapsed < a['end_ms'])
            if 'set_x' in action and index not in placed:
                placed.add(index)
                actor = self.word(0x537e88)
                self.put(actor+0x4c, action['set_x'])
                self.put(actor+0x50, action['set_y'])
                self.boss_placements.append(dict(elapsed_ms=elapsed, actor=hex(actor),
                    x=action['set_x'], y=action['set_y']))
            before = len(self.presentations)
            if action.get('cheat'):
                if action['cheat'] != 'MPKFA':
                    raise Blocked('Boss assistance helper permits only MPKFA')
                progress = cheat_progress.get(index, 0)
                if progress < len(action['cheat']):
                    letter = action['cheat'][progress]
                    letters = dict(LETTERS, K=(0x4b, 0x25), F=(0x46, 0x21), A=(0x41, 0x1e))
                    vk, scan = letters[letter]
                    phase = f"boss-cheat-{action['start_ms']}-{progress}-{letter}"
                    self.deliver_key(application, vk, scan, phase)
                    self.boss_cheat_keys.append(dict(letter=letter, key=vk, milliseconds=self.milliseconds,
                                                     phase=phase, assistance=True))
                    cheat_progress[index] = progress+1
            keys = list(action['keys'])
            if action.get('chase_boss', False):
                keys = [key for key in keys if key not in (0x25, 0x27)]
                player_actor = self.word(0x537e88)
                boss_actor = self.word(0x5349dc)
                if player_actor and boss_actor:
                    player_x = self.word(player_actor+0x4c)
                    boss_x = self.word(boss_actor+0x4c)
                    player_x = player_x-0x100000000 if player_x >= 0x80000000 else player_x
                    boss_x = boss_x-0x100000000 if boss_x >= 0x80000000 else boss_x
                    if boss_x != player_x:
                        keys.append(0x25 if boss_x < player_x else 0x27)
            self.frame(application, 'level-10-boss-'+action['action'], keys)
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != 10:
                raise Blocked('Boss route left single-player Level 10 before completion command')
            self.level_two_played_ms = self.milliseconds-start
            player = self.player_snapshot(application)
            self.level_two_frames.append(dict(elapsed_ms=self.level_two_played_ms,
                                              action=action['action'], player=player))
            self.boss_frames.append(dict(elapsed_ms=self.level_two_played_ms, action=action['action'],
                player=player, boss=self.boss_snapshot(), presentation_start=before,
                presentation_count=len(self.presentations)-before))
            boss = self.boss_frames[-1]['boss']
            if boss.get('live') and 'health' in boss:
                health = boss['health']
                health = health-0x100000000 if health >= 0x80000000 else health
                if health > 0:
                    context['saw_positive_health'] = True
                elif context['saw_positive_health']:
                    self.boss_defeat_health_observed = True
            self.boss_death_callback_observed = bool(self.boss_death_callbacks)
            if (self.boss_end_on_defeat and self.boss_defeat_health_observed and
                    self.boss_death_callback_observed):
                break
            if (self.combat_save_path and self.combat_checkpoint_at_ms is not None and
                    elapsed < self.combat_checkpoint_at_ms <= self.milliseconds-start):
                self.save_combat()
            if len(self.boss_frames) % 120 == 0:
                print(json.dumps(dict(event='boss-frame', parrot_wait_calls=self.functions[0x459830]-functions_before[0x459830], **self.boss_frames[-1])), flush=True)
        self.machine.hook_del(death_hook)
        self.machine.hook_del(wait_hook)
        for hook in mechanism_hooks:
            self.machine.hook_del(hook)
        if self.combat_save_path and self.combat_checkpoint_at_ms is None:
            self.save_combat()
        self.boss_route_functions = {hex(a): count-functions_before[a]
            for a, count in self.functions.items() if count > functions_before[a]}
        self.level_two_game_ms = (self.level_two_frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, 'level-10-boss-played')
        if self.fight_only:
            self.boss_route_complete = True
            return
        self.complete_level(application, 10)
        self.clock_step = 0
        for index in range(10):
            before = len(self.presentations)
            self.frame(application, 'level-eleven-stand')
            player = self.player_snapshot(application)
            if player['level'] != 11:
                raise Blocked('Standing frames left Level 11')
            self.level_eleven_frames.append(dict(index=index, player=player,
                presentation_start=before, presentation_count=len(self.presentations)-before))
        self.state_snapshot(application, 'level-eleven-standing')
        self.boss_route_complete = True

    def report(self):
        result = EndOfLevelTrace.report(self)
        result.update(scope='Original Marrow combat, defeat, MPSCULLY and Level 11; integration reference',
            boss_tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            xmidi_clock_adapter=dict(version=CLOCK_VERSION, hz=120, sha256=hashlib.sha256((ROOT/"Tests/NativeLevels/xmidi_clock.py").read_bytes()).hexdigest()),
            plan=self.boss_plan, boss_frames=self.boss_frames,
            boss_placements=self.boss_placements, boss_route_functions=self.boss_route_functions,
            boss_mechanism_events=self.boss_mechanism_events,
            boss_cheat_keys=self.boss_cheat_keys, parrot_wait_entries=self.parrot_wait_entries,
            fight_only=self.fight_only, boss_defeat_health_observed=self.boss_defeat_health_observed,
            boss_death_callback_observed=self.boss_death_callback_observed,
            boss_death_callbacks=self.boss_death_callbacks,
            level_eleven_frames=self.level_eleven_frames,
            status='pass' if self.stop is None and self.boss_route_complete else 'blocked')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--fight-only', action='store_true')
    parser.add_argument('--until-ms', type=int, help='Stop at the first frame boundary at this combat elapsed time')
    parser.add_argument('--save-combat', type=Path, help='Save all combat state and accumulated evidence')
    parser.add_argument('--resume-combat', type=Path, help='Resume a trusted local combat checkpoint')
    parser.add_argument('--checkpoint-at-ms', type=int, help='Save at this frame boundary and continue uninterrupted')
    parser.add_argument('--source-checkpoint', type=Path, help='Fresh Level 9 checkpoint, used only to create the Level 10 checkpoint')
    parser.add_argument('--paper-startup', action='store_true')
    args = parser.parse_args()
    for path in (args.output, args.checkpoint, args.source_checkpoint, args.save_combat, args.resume_combat):
        if path and not path.resolve().is_relative_to((ROOT/'work').resolve()):
            parser.error('Derived artifacts must stay under work/')
    for bound in (args.until_ms, args.checkpoint_at_ms):
        if bound is not None and bound <= 0:
            parser.error('Combat bounds must be positive milliseconds')
    plan = json.loads(args.plan.read_text())
    validate_plan(plan)
    source = args.source_checkpoint if args.source_checkpoint and not (args.checkpoint and exists(args.checkpoint)) else None
    trace = MarrowTrace(15_000_000_000, None, boss_plan=plan,
                          fight_only=args.fight_only, checkpoint=args.checkpoint, source_level=9 if source else 10,
                          startup_paper=args.paper_startup)
    trace.combat_until_ms = args.until_ms
    trace.combat_save_path = args.save_combat
    trace.combat_checkpoint_at_ms = args.checkpoint_at_ms
    if (args.until_ms or args.save_combat) and not args.fight_only:
        parser.error('Bounded combat commands require --fight-only')
    if args.checkpoint_at_ms is not None and not args.save_combat:
        parser.error('--checkpoint-at-ms requires --save-combat')
    def interrupted(signum, frame):
        raise Blocked('Reference run interrupted; partial evidence only')
    previous = signal.signal(signal.SIGINT, interrupted)
    try:
        if args.resume_combat:
            trace.resume_combat(args.resume_combat)
        elif source:
            trace.resume_target(source)
        elif args.checkpoint and exists(args.checkpoint):
            trace.resume_target(args.checkpoint)
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        signal.signal(signal.SIGINT, previous)
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(args.output, result)
    print(json.dumps(dict(status=result['status'], stop=result['stop'], boss_frames=len(trace.boss_frames),
                         level_eleven_frames=len(trace.level_eleven_frames), output=str(output))), flush=True)
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
