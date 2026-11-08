"""Original Level 11 completion by MPSCULLY, results and ten Level 12 frames.

Level 11 has no boss in the original world. The app's level_eleven_boss check
verifies that world inventory and this actual end-of-level boundary instead.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels.string_compare_trace import StringCompareTrace
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevels.storage import write_trace, fingerprint
from Tests.NativeLevels import ROOT
from Tests.NativeMenuBase.trace import Blocked

PLAN = [dict(start_ms=0, end_ms=1000, action='stand', keys=[])]


class LevelElevenEndTrace(StringCompareTrace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, level=11, destination=12, evidence_dir=ROOT/"work/level-eleven-end", route=PLAN, **kwargs)
        self.end_frames = []
        self.next_frames = []
        self.end_complete = False
        self.active_boss_observed = False

    def complete_level(self, application, level):
        LevelTrace.complete_level(self, application, level)

    def play_target(self, application):
        self.clock_step = 0
        start = self.milliseconds
        self.end_frames = [dict(elapsed_ms=0, action='loaded', player=self.player_snapshot(application))]
        while self.milliseconds-start < 1000:
            before = len(self.presentations)
            self.frame(application, 'level-11-end-stand')
            player = self.player_snapshot(application)
            if player['level'] != 11:
                raise Blocked('End route left Level 11 before MPSCULLY')
            self.active_boss_observed |= self.word(0x5349dc) != 0
            self.end_frames.append(dict(elapsed_ms=self.milliseconds-start, action='stand', player=player,
                presentation_start=before, presentation_count=len(self.presentations)-before))
        self.complete_level(application, 11)
        self.clock_step = 0
        for index in range(10):
            before = len(self.presentations)
            self.frame(application, 'level-twelve-stand')
            player = self.player_snapshot(application)
            if player['level'] != 12:
                raise Blocked('Completion did not reach Level 12')
            self.next_frames.append(dict(index=index, player=player,
                presentation_start=before, presentation_count=len(self.presentations)-before))
        self.state_snapshot(application, 'level-twelve-standing')
        self.end_complete = True

    def report(self):
        result = super().report()
        result.update(scope='Original Level 11 MPSCULLY completion and Level 12; no Level 11 boss',
            tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), plan=PLAN,
            end_frames=self.end_frames, next_frames=self.next_frames,
            active_boss_observed=self.active_boss_observed,
            status='pass' if self.stop is None and self.end_complete else 'blocked')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper-startup', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'work/level-eleven-end/trace.json')
    parser.add_argument('--checkpoint', type=Path, default=ROOT/'work/level-12-sign-discovery/level-11.checkpoint.gz')
    args = parser.parse_args()
    for path in (args.output, args.checkpoint):
        if not path.resolve().is_relative_to((ROOT/'work').resolve()):
            parser.error('Derived artifacts must stay under work/')
    args.checkpoint = args.checkpoint.resolve()
    trace = LevelElevenEndTrace(instruction_limit=15_000_000_000, deny_platform=None, startup_paper=args.paper_startup)
    try:
        trace.resume_target(args.checkpoint)
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    result["observer_checkpoint"] = dict(path=str(args.checkpoint.relative_to(ROOT)),
        sha256=fingerprint(args.checkpoint), inputs_sha256=trace.checkpoint_inputs())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(args.output, result)
    print(json.dumps(dict(status=result['status'], stop=result['stop'], end_frames=len(trace.end_frames),
                         next_frames=len(trace.next_frames), output=str(output))), flush=True)
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
