"""Original Omar combat, coordinate-only placements, MPSCULLY and Level 14."""
import argparse
import hashlib
import json
import signal
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels.level_fourteen_join import Original
from Tests.NativeLevels.storage import exists
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevelTwo.boss_trace import BossTrace, validate_plan
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, LETTERS
from Tests.NativeLevels.storage import write_trace, fingerprint
from Tests.NativeLevels import ROOT
from Tests.NativeMenuBase.trace import Blocked


class OmarTrace(Original):
    def __init__(self, *, boss_plan, fight_only=False, checkpoint=None, startup_paper=False):
        super().__init__(boss_plan, startup_paper=startup_paper)
        self.target_checkpoint = checkpoint
        self.boss_death_callbacks = []
        self.boss_plan = boss_plan
        self.fight_only = fight_only
        self.boss_actor_seen = 0
        self.boss_frames = []
        self.next_frames = []
        self.boss_cheat_keys = []
        self.boss_route_functions = {}
        self.boss_route_complete = False

    def checkpoint_inputs(self):
        return {**super().checkpoint_inputs(),
            'Tests/NativeLevels/level_fourteen_join.py': hashlib.sha256((ROOT/'Tests/NativeLevels/level_fourteen_join.py').read_bytes()).hexdigest(),
            'Tests/NativeLevels/level_fourteen_boss_trace.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def resume_target(self, path):
        keep = {k: v for k, v in self.__dict__.items()
                if k.startswith('boss_') or k in ('fight_only', 'next_frames')}
        def resumed(application):
            self.__dict__.update(keep)
            del self.play_target
            OmarTrace.play_target(self, application)
        self.play_target = resumed
        try:
            super().resume_target(path)
        finally:
            self.__dict__.pop('play_target', None)

    def complete_level(self, application, level):
        print(json.dumps(dict(event='complete-prefix', level=level)), flush=True)
        LevelTrace.complete_level(self, application, level)

    def advance_results(self, application, level):
        if level != 14:
            return super().advance_results(application, level)
        start = self.milliseconds
        waiting_object = None
        while self.milliseconds-start < self.results_limit_ms:
            entry = self.state_snapshot(application, 'level-14-ending')
            if entry['vtable'] == '0x50c1e4':
                return self.milliseconds-start
            if entry['object'] != waiting_object:
                waiting_object, waiting_since = entry['object'], self.milliseconds
            elif self.milliseconds-waiting_since >= 1000:
                self.deliver_key(application, 13, 0x1c, 'level-14-results-return')
                waiting_since = self.milliseconds
            self.frame(application, 'level-14-ending-'+entry['vtable'])
        raise Blocked('Level 14 ending did not return to menu')

    def boss_snapshot(self):
        return BossTrace.boss_snapshot(self)

    def play_target(self, application):
        if self.target_checkpoint and not self.resumed_checkpoint:
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.target_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        def death(machine, address, size, user):
            private = self.boss_snapshot().get('private')
            receiver = machine.reg_read(UC_X86_REG_ECX)
            if private == hex(receiver):
                self.boss_death_callbacks.append(dict(address=hex(address), receiver=private,
                    elapsed_ms=self.milliseconds-start, health=self.boss_snapshot().get("health")))
        death_hook = self.machine.uc.hook_add(UC_HOOK_CODE, death, begin=0x40e5c0, end=0x40e5c0)
        self.clock_step = 0
        start = self.milliseconds
        self.boss_frames = [dict(elapsed_ms=0, action='loaded', player=self.player_snapshot(application), boss=self.boss_snapshot())]
        before_functions = self.functions.copy()
        placed, cheats = set(), {}
        while self.milliseconds-start < self.boss_plan[-1]['end_ms']:
            elapsed = self.milliseconds-start
            index, action = next((i,a) for i,a in enumerate(self.boss_plan) if a['start_ms'] <= elapsed < a['end_ms'])
            if 'set_x' in action and index not in placed:
                placed.add(index)
                actor = self.word(0x537e88)
                self.put(actor+0x4c, action['set_x']); self.put(actor+0x50, action['set_y'])
            before = len(self.presentations)
            if action.get('cheat'):
                if action['cheat'] != 'MPKFA': raise Blocked('Only MPKFA assistance is permitted')
                progress = cheats.get(index, 0)
                if progress < 5:
                    letter = 'MPKFA'[progress]
                    vk, scan = dict(LETTERS, K=(0x4b,0x25), F=(0x46,0x21), A=(0x41,0x1e))[letter]
                    phase = f"boss-cheat-{action['start_ms']}-{progress}-{letter}"
                    self.deliver_key(application, vk, scan, phase)
                    self.boss_cheat_keys.append(dict(letter=letter, phase=phase))
                    cheats[index] = progress+1
            keys = list(action['keys'])
            if action.get('chase_boss'):
                keys = [k for k in keys if k not in (37, 39)]
                player, boss = self.word(0x537e88), self.word(0x5349dc)
                if player and boss:
                    px, bx = self.word(player+0x4c), self.word(boss+0x4c)
                    if px != bx: keys.append(37 if bx < px else 39)
            self.frame(application, 'level-14-boss-'+action['action'], keys)
            player = self.player_snapshot(application)
            if player['level'] != 14: raise Blocked('Boss route left Level 14 before completion')
            self.boss_frames.append(dict(elapsed_ms=self.milliseconds-start, action=action['action'], player=player,
                boss=self.boss_snapshot(), presentation_start=before, presentation_count=len(self.presentations)-before))
            if len(self.boss_frames)%120 == 0:
                print(json.dumps(dict(event='boss-frame', **self.boss_frames[-1])), flush=True)
        self.machine.hook_del(death_hook)
        self.boss_route_functions = {hex(a):n-before_functions[a] for a,n in self.functions.items() if n>before_functions[a]}
        if getattr(self, 'boss_completed_checkpoint', None):
            self.prefix_checkpoint_sha256 = fingerprint(self.target_checkpoint)
            self.parent_checkpoint = dict(path=str(self.target_checkpoint.relative_to(ROOT)),
                sha256=self.prefix_checkpoint_sha256, startup_profile=self.startup_profile,
                mode='same fresh original execution; start snapshot retained before combat')
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.boss_completed_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        if not self.fight_only:
            self.complete_level(application, 14)
            self.clock_step = 0
        self.boss_route_complete = True

    def report(self):
        result = EndOfLevelTrace.report(self)
        result.update(scope='Original Omar combat and final ending; app integration reference',
            tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            adapter_inputs={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                ('Tests/NativeLevels/level_fourteen_join.py',
                 'Tests/NativeLevelTwo/boss_trace.py')}, plan=self.boss_plan,
            boss_frames=self.boss_frames, next_frames=self.next_frames, boss_cheat_keys=self.boss_cheat_keys,
            boss_route_functions=self.boss_route_functions, fight_only=self.fight_only,
            boss_death_callbacks=self.boss_death_callbacks,
            independent_prefix=not self.resumed_checkpoint,
            status='pass' if self.stop is None and self.boss_route_complete else 'blocked')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, default=ROOT/'work/level-fourteen-boss/start.checkpoint')
    parser.add_argument('--fight-only', action='store_true')
    parser.add_argument('--paper-startup', action='store_true')
    parser.add_argument('--completed-checkpoint', type=Path, help='Retain completed fight-only combat for the ending adapter')
    args = parser.parse_args()
    if args.completed_checkpoint and not args.fight_only:
        parser.error('--completed-checkpoint requires --fight-only')
    for path in (args.output, args.checkpoint, *([args.completed_checkpoint] if args.completed_checkpoint else [])):
        if not path.resolve().is_relative_to(ROOT/'work'): parser.error('Derived artifacts must stay under work/')
    plan = json.loads(args.plan.read_text()); validate_plan(plan)
    trace = OmarTrace(boss_plan=plan, fight_only=args.fight_only, checkpoint=args.checkpoint.resolve(), startup_paper=args.paper_startup)
    trace.boss_completed_checkpoint = args.completed_checkpoint.resolve() if args.completed_checkpoint else None
    def interrupted(signum, frame):
        raise Blocked("Reference interrupted; partial evidence only")
    previous = signal.signal(signal.SIGINT, interrupted)
    try:
        if exists(args.checkpoint):
            trace.resume_target(args.checkpoint.resolve())
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        signal.signal(signal.SIGINT, previous)
        for stream in trace.files.values(): stream.close()
    result = trace.report()
    result['observer_checkpoint'] = dict(path=str(args.checkpoint.resolve().relative_to(ROOT)),
        sha256=fingerprint(args.checkpoint), inputs_sha256=trace.checkpoint_inputs()) if exists(args.checkpoint) else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(args.output, result)
    print(json.dumps(dict(status=result['status'], stop=result['stop'], boss_frames=len(trace.boss_frames), output=str(output))), flush=True)
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
