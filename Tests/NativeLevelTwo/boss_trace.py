"""Original Level 2 boss route, then MPSCULLY/results/Level 3.

Debug placements affect only player position. This is integration discovery,
not family admission. --end-on-boss-defeat waits for positive-to-zero health
and original death callback 0x44e0c0 execution. Derived data stays in work/.
The inherited prefix verifies CLAW.EXE and CLAW.REZ and reaches Level 2 normally.
"""
import argparse
import hashlib
import json
from pathlib import Path

from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeMenuBase.trace import ROOT, Blocked
from Tests.NativeEndOfLevel.trace import CHEAT, LETTERS, SINGLE_PLAYER_VTABLE
from Tests.NativeLevels.storage import exists, write_trace
from Tests.NativeLevelTwo.trace import LevelTwoTrace
from Tests.NativeLevels import grid_fixture
from Tests.NativeLevels.grid_fixture import LargeGridFixture


class BossTrace(LargeGridFixture, LevelTwoTrace):
    def __init__(self, *args, boss_plan, fight_only=False, level_three_frames=10, end_on_boss_defeat=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.boss_end_on_defeat = end_on_boss_defeat
        self.boss_defeat_health_observed = False
        self.boss_death_callback_observed = False
        self.boss_actor_seen = 0
        self.boss_plan = boss_plan
        self.fight_only = fight_only
        self.level_three_requested_frames = level_three_frames
        self.level_three_frames = []
        self.boss_frames = []
        self.boss_placements = []
        self.boss_cheat_keys = []
        self.boss_route_functions = {}
        self.boss_results_started = False
        self.boss_route_complete = False
        self.boss_checkpoint = None

    def boss_snapshot(self):
        active_actor = self.word(0x5349dc)
        if active_actor:
            self.boss_actor_seen = active_actor
        actor = active_actor or self.boss_actor_seen
        result = dict(actor=hex(actor), active=bool(active_actor),
                      live=bool(actor and actor in self.allocations))
        if not result['live']:
            return result
        record = self.word(actor+0x6c)
        # Raux's owning object is record+0x18; player uses record+0x14.
        private = self.word(record+0x18) if record else 0
        result.update(x=self.word(actor+0x4c), y=self.word(actor+0x50),
                      health=self.word(actor+0x10c), actor_flags=self.word(actor+8),
                      record=hex(record), private=hex(private),
                      logic_state=self.word(record+0x1c) if record else None)
        if private and private in self.allocations:
            animation = self.word(private+0x10)
            result.update(vtable=hex(self.word(private)), state=animation,
                          animation_id=self.word(animation+0x1c) if animation else None,
                          callback=hex(self.word(private+0x14)),
                          action_phase=self.word(private+0x20), mode=self.word(private+0x184),
                          facing=self.word(private+0x18c))
        return result

    def resume_two_checkpoint(self, path):
        # Base restore replaces the instance dictionary. This invocation's route
        # and reporting buffers must win over whichever tracer wrote the cache.
        keep = {key: value for key, value in self.__dict__.items()
                if key.startswith('boss_') or key.startswith('level_three_') or key == 'fight_only'}
        def resume_route(application):
            self.__dict__.update(keep)
            self.boss_checkpoint = None
            BossTrace.level_two(self, application)
        self.level_two = resume_route
        try:
            super().resume_two_checkpoint(path)
        finally:
            del self.level_two

    def level_two(self, application):
        if self.boss_checkpoint and not self.resumed_checkpoint:
            self.checkpoint_path = self.boss_checkpoint
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
            self.frame(application, 'level-two-boss-'+action['action'], keys)
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != 2:
                raise Blocked('Boss route left single-player Level 2 before completion command')
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
        self.state_snapshot(application, 'level-two-boss-played')
        if self.fight_only:
            self.boss_route_complete = True
            return
        self.level_complete_posted = False
        self.clock_step = 1
        for index, letter in enumerate(CHEAT):
            vk, scan = LETTERS[letter]
            self.deliver_key(application, vk, scan, f'level-two-complete-key-{index}-{letter}')
            self.boss_cheat_keys.append(dict(letter=letter, key=vk, milliseconds=self.milliseconds))
            self.frame(application, f'level-two-complete-frame-{index}')
        if not self.level_complete_posted:
            raise Blocked('Original Level 2 MPSCULLY did not post level-complete')
        self.boss_results_started = True
        self.results_start = self.milliseconds
        self.waiting_object = None
        self.results(application)

    def results(self, application):
        if not self.boss_results_started:
            return super().results(application)
        while self.milliseconds-self.results_start < self.results_limit_ms:
            entry = self.state_snapshot(application, 'level-two-results')
            state = self.word(application+0x2c)
            if self.word(state) == SINGLE_PLAYER_VTABLE:
                level = self.word(state+0x14)
                if level == 3:
                    self.clock_step = 0
                    for index in range(self.level_three_requested_frames):
                        before = len(self.presentations)
                        self.frame(application, 'level-three-stand')
                        snapshot = self.player_snapshot(application)
                        if snapshot['level'] != 3:
                            raise Blocked('Standing frames left Level 3')
                        self.level_three_frames.append(dict(index=index, player=snapshot,
                            presentation_start=before, presentation_count=len(self.presentations)-before))
                    self.state_snapshot(application, 'level-three-standing')
                    self.boss_route_complete = True
                    return
                if level != 2:
                    raise Blocked(f'Level 2 results continued into unexpected level {level}')
            if entry['object'] != self.waiting_object:
                self.waiting_object, self.waiting_since = entry['object'], self.milliseconds
            elif self.milliseconds-self.waiting_since >= 12000:
                self.deliver_key(application, 13, 0x1c, 'level-two-results-return-'+entry['vtable'])
                self.waiting_since = self.milliseconds
            self.frame(application, 'level-two-results-'+entry['vtable'])
        raise Blocked('Level 2 results did not reach Level 3 within the frame budget')

    def report(self):
        result = super().report()
        result.update(scope='Original Level 2 boss route with debug player placements; MPSCULLY completion and Level 3 standing; integration discovery only',
            boss_tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            large_grid_fixture_sha256=hashlib.sha256(Path(grid_fixture.__file__).read_bytes()).hexdigest(),
            level_two_plan=self.boss_plan, boss_frames=self.boss_frames,
            boss_placements=self.boss_placements, boss_route_functions=self.boss_route_functions,
            boss_cheat_keys=self.boss_cheat_keys, fight_only=self.fight_only,
            end_on_boss_defeat=self.boss_end_on_defeat,
            boss_defeat_health_observed=self.boss_defeat_health_observed,
            boss_death_callback_observed=self.boss_death_callback_observed,
            boss_defeat_endpoint='positive health then signed health <= 0 and original 0x44e0c0 entered during fight',
            level_three_frames=self.level_three_frames,
            status='pass' if self.stop is None and self.boss_route_complete else 'blocked')
        return result


def validate_plan(plan):
    end = 0
    if not isinstance(plan, list) or not plan:
        raise ValueError('Plan must be a nonempty list')
    for action in plan:
        if action['start_ms'] != end or action['end_ms'] <= end:
            raise ValueError('Plan must be contiguous, ordered and start at zero')
        if not isinstance(action['action'], str) or not isinstance(action['keys'], list):
            raise ValueError('Each action needs a name and key list')
        if any(not isinstance(key, int) or not 0 <= key <= 255 for key in action['keys']):
            raise ValueError('Virtual keys must be bytes')
        if 'chase_boss' in action and not isinstance(action['chase_boss'], bool):
            raise ValueError('chase_boss must be boolean')
        if action.get('cheat') not in (None, 'MPKFA'):
            raise ValueError('Boss assistance helper permits only MPKFA')
        if ('set_x' in action) != ('set_y' in action):
            raise ValueError('Placement needs both set_x and set_y')
        end = action['end_ms']
    return end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--fight-only', action='store_true')
    parser.add_argument('--end-on-boss-defeat', action='store_true')
    parser.add_argument('--level-three-frames', type=int, default=10)
    parser.add_argument('--instruction-limit', type=int, default=10_000_000_000)
    parser.add_argument('--paper-startup', action='store_true',
                        help='Original paper objects and 1 ms timer queries from initialization')
    args = parser.parse_args()
    work = (ROOT/'work').resolve()
    if not args.output.resolve().is_relative_to(work) or (args.checkpoint and not args.checkpoint.resolve().is_relative_to(work)):
        parser.error('Derived output and checkpoints must stay under ignored work/')
    if args.level_three_frames < 1:
        parser.error('--level-three-frames must be positive')
    try:
        plan = json.loads(args.plan.read_text())
        duration = validate_plan(plan)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    trace = BossTrace(args.instruction_limit, None, boss_plan=plan, fight_only=args.fight_only,
                     level_two_ms=duration, level_three_frames=args.level_three_frames,
                     end_on_boss_defeat=args.end_on_boss_defeat, startup_paper=args.paper_startup)
    try:
        if args.checkpoint and exists(args.checkpoint):
            trace.resume_two_checkpoint(args.checkpoint.resolve())
        else:
            trace.boss_checkpoint = args.checkpoint.resolve() if args.checkpoint else None
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(args.output.resolve(), report)
    print(json.dumps(dict(status=report['status'], counts=report['counts'], stop=report['stop'],
                         boss_frames=len(trace.boss_frames), level_three_frames=len(trace.level_three_frames), output=str(output))), flush=True)
    return 0 if report['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
