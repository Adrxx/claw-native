"""Original Katherine fight through defeat, MPSCULLY, results and Level 5.

Debug placements change only player coordinates; combat and progression use
original game code and physical inputs. References and checkpoints stay local.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevelTwo.boss_trace import BossTrace, validate_plan
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, SINGLE_PLAYER_VTABLE, LETTERS
from Tests.NativeLevels.storage import exists, write_trace
from Tests.NativeLevels import ROOT
from Tests.NativeMenuBase.trace import Blocked


class KatherineTrace(LevelTrace):
    boss_snapshot = BossTrace.boss_snapshot

    def __init__(self, *args, boss_plan, fight_only=False, **kwargs):
        super().__init__(*args, level=4, route=boss_plan, **kwargs)
        self.boss_plan = boss_plan
        self.boss_end_on_defeat = True
        self.boss_defeat_health_observed = False
        self.boss_death_callback_observed = False
        self.boss_actor_seen = 0
        self.boss_checkpoint = None
        self.boss_frames = []
        self.boss_placements = []
        self.boss_cheat_keys = []
        self.boss_route_functions = {}
        self.boss_route_complete = False
        self.fight_only = fight_only
        self.level_five_frames = []

    def resume_target(self, path):
        keep = {key: value for key, value in self.__dict__.items()
                if key.startswith('boss_') or key in ('fight_only', 'level_five_frames')}
        def resume(application):
            self.__dict__.update(keep)
            KatherineTrace.play_target(self, application)
        self.play_target = resume
        try:
            super().resume_target(path)
        finally:
            del self.play_target

    def play_target(self, application):
        if self.target_checkpoint and not self.resumed_checkpoint:
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.target_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        self.clock_step = 0
        self.level_two_loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.level_two_frames = [dict(elapsed_ms=0, action='loaded', player=first)]
        self.boss_frames = [dict(elapsed_ms=0, action='loaded', boss=self.boss_snapshot(), player=first)]
        functions_before = self.functions.copy()
        placed = set()
        cheat_progress = {}
        saw_positive_health = False
        end = self.boss_plan[-1]['end_ms']
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
            self.frame(application, 'level-4-boss-'+action['action'], keys)
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != 4:
                raise Blocked('Boss route left single-player Level 4 before completion command')
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
                    saw_positive_health = True
                elif saw_positive_health:
                    self.boss_defeat_health_observed = True
            self.boss_death_callback_observed = self.functions[0x44e0c0] > functions_before[0x44e0c0]
            if (self.boss_end_on_defeat and self.boss_defeat_health_observed and
                    self.boss_death_callback_observed):
                break
            if len(self.boss_frames) % 120 == 0:
                print(json.dumps(dict(event='boss-frame', **self.boss_frames[-1])), flush=True)
        self.boss_route_functions = {hex(a): count-functions_before[a]
            for a, count in self.functions.items() if count > functions_before[a]}
        self.level_two_game_ms = (self.level_two_frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, 'level-4-boss-played')
        if self.fight_only:
            self.boss_route_complete = True
            return
        self.complete_level(application, 4)
        self.clock_step = 0
        for index in range(10):
            before = len(self.presentations)
            self.frame(application, 'level-five-stand')
            player = self.player_snapshot(application)
            if player['level'] != 5:
                raise Blocked('Standing frames left Level 5')
            self.level_five_frames.append(dict(index=index, player=player,
                presentation_start=before, presentation_count=len(self.presentations)-before))
        self.state_snapshot(application, 'level-five-standing')
        self.boss_route_complete = True

    def report(self):
        result = EndOfLevelTrace.report(self)
        result.update(scope='Original Katherine combat, defeat, MPSCULLY and Level 5; integration reference',
            boss_tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            plan=self.boss_plan, boss_frames=self.boss_frames,
            boss_placements=self.boss_placements, boss_route_functions=self.boss_route_functions,
            fight_only=self.fight_only, boss_defeat_health_observed=self.boss_defeat_health_observed,
            boss_death_callback_observed=self.boss_death_callback_observed,
            level_five_frames=self.level_five_frames,
            status='pass' if self.stop is None and self.boss_route_complete else 'blocked')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--fight-only', action='store_true')
    parser.add_argument('--paper-startup', action='store_true',
                        help='Original startup fader/palette and 1 ms timer queries from initialization')
    args = parser.parse_args()
    for path in (args.output, args.checkpoint):
        if path and not path.resolve().is_relative_to((ROOT/'work').resolve()):
            parser.error('Derived artifacts must stay under work/')
    plan = json.loads(args.plan.read_text())
    validate_plan(plan)
    trace = KatherineTrace(15_000_000_000, None, boss_plan=plan,
                          fight_only=args.fight_only, checkpoint=args.checkpoint,
                          startup_paper=args.paper_startup)
    try:
        if args.checkpoint and exists(args.checkpoint):
            trace.resume_target(args.checkpoint)
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(args.output, result)
    print(json.dumps(dict(status=result['status'], stop=result['stop'], boss_frames=len(trace.boss_frames),
                         level_five_frames=len(trace.level_five_frames), output=str(output))), flush=True)
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
