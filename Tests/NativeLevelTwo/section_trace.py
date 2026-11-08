"""Original Level 2 section: the Level 2 route's prefix, then a plan of keys and debug placements.

The prefix is the one Tests/NativeLevelTwo/trace.py runs (New Game, Level 1 stands 1000 ms, MPSCULLY,
results with Return, Level 2 loaded). Level 2 then replays a plan file instead of the trace's own
60000 ms walk: entries {start_ms, end_ms, action, keys} as in --play-script, and an entry may carry
"set_x"/"set_y", which writes the player actor's position words (+0x4c, +0x50) once, before the
entry's first frame, as the app's --level-two-route does. That reaches a far part of the level
(a tower cannon, for example) without playing to it; it writes no cheat state.

Usage: work/test-env/bin/python -m Tests.NativeLevelTwo.section_trace --plan <plan.json> --output work/<dir>/trace.json
  [--checkpoint work/<dir>/level-two-start.pkl]  resume Level 2 start from a local cache, or write it when absent.
Prints one JSON line last. Discovery only, no admission claim.
"""
import argparse
from Tests.NativeLevels.storage import exists, fingerprint, load_checkpoint, restore_memory, save_checkpoint, write_trace
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeMenuBase.trace import ROOT, Blocked
from Tests.NativeEndOfLevel.trace import SINGLE_PLAYER_VTABLE
from Tests.NativeLevelTwo.trace import LevelTwoTrace


class SectionTrace(LevelTwoTrace):
    section_plan = []
    section_checkpoint = None

    def level_two(self, application):
        if not self.resumed_checkpoint and self.section_checkpoint is not None:
            self.checkpoint_path = self.section_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        self.clock_step = 0
        self.level_two_loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.level_two_frames = [dict(elapsed_ms=0, action='loaded', player=first)]
        placed = set()
        end = max(a['end_ms'] for a in self.section_plan)
        while self.milliseconds-start < end:
            elapsed = self.milliseconds-start
            action = next(a for a in self.section_plan if a['start_ms'] <= elapsed < a['end_ms'])
            if 'set_x' in action and action['start_ms'] not in placed:
                placed.add(action['start_ms'])
                actor = self.word(0x537e88)
                self.put(actor+0x4c, action['set_x'])
                self.put(actor+0x50, action['set_y'])
            self.frame(application, 'level-two-'+action['action'], action['keys'])
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != 2:
                raise Blocked('Original Level 2 play left the single-player Level 2 state')
            self.level_two_played_ms = self.milliseconds-start
            self.level_two_frames.append(dict(elapsed_ms=self.level_two_played_ms, action=action['action'],
                player=self.player_snapshot(application)))
            if len(self.level_two_frames) % 120 == 0:
                print(json.dumps(dict(event='level-two', **self.level_two_frames[-1])), flush=True)
        self.level_two_game_ms = (self.level_two_frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, 'level-two-played')

    def resume_two_checkpoint(self, path):
        # The cached state carries the plan it was written with; this run's plan wins.
        plan, base_plan = self.section_plan, self.plan
        def level_two(application):
            # A cache written before the section plan had its own name may carry it as `plan`.
            self.section_plan, self.plan = plan, base_plan
            self.section_checkpoint = None
            SectionTrace.level_two(self, application)
        self.level_two = level_two
        try:
            super().resume_two_checkpoint(path)
        finally:
            del self.level_two

    def report(self):
        result = super().report()
        end = max(a['end_ms'] for a in self.section_plan)
        result.update(scope='Original Level 2 section plan with debug placements; discovery only, no admission claim',
                      level_two_plan=self.section_plan)
        result['status'] = 'pass' if self.stop is None and self.level_two_played_ms >= end else 'blocked'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--instruction-limit', type=int, default=10_000_000_000)
    parser.add_argument('--paper-startup', action='store_true')
    args = parser.parse_args()
    work = (ROOT/'work').resolve()
    output = args.output.resolve()
    if not output.is_relative_to(work) or (args.checkpoint and not args.checkpoint.resolve().is_relative_to(work)):
        parser.error('Derived output and checkpoints must stay under ignored work/')
    plan = json.loads(args.plan.read_text())
    end = max(a['end_ms'] for a in plan)
    trace = SectionTrace(args.instruction_limit, None, level_two_ms=end, startup_paper=args.paper_startup)
    trace.section_plan = plan
    try:
        if args.checkpoint and exists(args.checkpoint):
            trace.resume_two_checkpoint(args.checkpoint.resolve())
        else:
            trace.section_checkpoint = args.checkpoint.resolve() if args.checkpoint else None
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(output, result)
    print(json.dumps(dict(status=result['status'], counts=result['counts'], stop=result['stop'],
        played_ms=result['level_two_played_ms'], output=str(output))), flush=True)
    return 0 if result['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
