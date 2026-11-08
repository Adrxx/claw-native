"""Original Level 7 completion by MPSCULLY, results and ten Level 8 frames.

Level 7 has no boss in the original world. The app's level_seven_boss check
verifies that world inventory and this actual end-of-level boundary instead.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace
from Tests.NativeLevels.storage import exists, write_trace
from Tests.NativeLevels import ROOT
from Tests.NativeMenuBase.trace import Blocked

PLAN = [dict(start_ms=0, end_ms=1000, action='stand', keys=[])]


class LevelSevenEndTrace(LevelTrace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, level=7, route=PLAN, **kwargs)
        self.end_frames = []
        self.next_frames = []
        self.end_complete = False
        self.active_boss_observed = False

    def play_target(self, application):
        if self.target_checkpoint and not self.resumed_checkpoint:
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.target_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        self.clock_step = 0
        start = self.milliseconds
        self.end_frames = [dict(elapsed_ms=0, action='loaded', player=self.player_snapshot(application))]
        while self.milliseconds-start < 1000:
            before = len(self.presentations)
            self.frame(application, 'level-7-end-stand')
            player = self.player_snapshot(application)
            if player['level'] != 7:
                raise Blocked('End route left Level 7 before MPSCULLY')
            self.active_boss_observed |= self.word(0x5349dc) != 0
            self.end_frames.append(dict(elapsed_ms=self.milliseconds-start, action='stand', player=player,
                presentation_start=before, presentation_count=len(self.presentations)-before))
        self.complete_level(application, 7)
        self.clock_step = 0
        for index in range(10):
            before = len(self.presentations)
            self.frame(application, 'level-eight-stand')
            player = self.player_snapshot(application)
            if player['level'] != 8:
                raise Blocked('Completion did not reach Level 8')
            self.next_frames.append(dict(index=index, player=player,
                presentation_start=before, presentation_count=len(self.presentations)-before))
        self.state_snapshot(application, 'level-eight-standing')
        self.end_complete = True

    def report(self):
        result = EndOfLevelTrace.report(self)
        result.update(scope='Original Level 7 MPSCULLY completion and Level 8; no Level 7 boss',
            tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), plan=PLAN,
            end_frames=self.end_frames, next_frames=self.next_frames,
            active_boss_observed=self.active_boss_observed,
            status='pass' if self.stop is None and self.end_complete else 'blocked')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/level-seven-end/trace.json')
    parser.add_argument('--checkpoint', type=Path, default=ROOT/'work/level-seven-end/start.pkl')
    parser.add_argument('--paper-startup', action='store_true')
    args = parser.parse_args()
    for path in (args.output, args.checkpoint):
        if not path.resolve().is_relative_to((ROOT/'work').resolve()):
            parser.error('Derived artifacts must stay under work/')
    trace = LevelSevenEndTrace(15_000_000_000, None, checkpoint=args.checkpoint,
                               startup_paper=args.paper_startup)
    try:
        if exists(args.checkpoint):
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
    print(json.dumps(dict(status=result['status'], stop=result['stop'], end_frames=len(trace.end_frames),
                         next_frames=len(trace.next_frames), output=str(output))), flush=True)
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
