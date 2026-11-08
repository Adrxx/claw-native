"""Re-record app menu references from the local original paper startup cache.

First run Tests.NativeMenuBase.paper_trace. Then run this module with --idle
or --frames 1801. The cache contains the unchanged original's complete startup,
not native results; all requested frames execute the original again.
"""
import argparse
import json
from pathlib import Path
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeMenuBase import input_trace
from Tests.NativeLevelOne.trace import LevelOneTrace
from Tests.NativeMenuBase.paper_trace import OUT, Complete
from Tests.NativeMenuBase.trace import ROOT


class PaperMenuTrace(input_trace.InputTrace, LevelOneTrace):
    # InputTrace supplies physical menu input; LevelOneTrace supplies the same
    # startup managers and cache loader as the app and paper-transition route.
    def __init__(self, output, frames):
        super().__init__(output, frames, startup_paper=True)
        self.navigation_ready = False

    def run(self, address, *args, **kwargs):
        result = super().run(address, *args, **kwargs)
        if address == 0x428b60 and not self.navigation_ready:
            self.navigation_ready = True
            self.setup_navigation(self.application)
        return result

    def execute_frames(self, application):
        self.application = application
        input_trace.InputTrace.execute_frames(self, application)
        raise Complete

    def navigate(self, application):
        self.execute_frames(application)

    def extra_witness(self, application):
        return dict(milliseconds=self.milliseconds, frame_ms=self.word(0x53720c),
                    animation_delta=self.word(0x5430c4))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idle', action='store_true')
    parser.add_argument('--frames', type=int, default=1801)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = (args.output or ROOT/'work/paper-roll/rebased'/('menu-map' if args.idle else 'menu-input')).resolve()
    if not output.is_relative_to(ROOT/'work'):
        parser.error('Original-derived evidence must stay under work/')
    if args.idle:
        input_trace.EVENTS = []
        args.frames = 61
    if not 61 <= args.frames <= 1801:
        parser.error('Expected 61 through 1801 frames')
    output.mkdir(parents=True, exist_ok=True)
    (output/'events.json').write_text(json.dumps(input_trace.EVENTS,indent=2)+'\n')
    trace = PaperMenuTrace(output, args.frames)
    error = None
    try:
        trace.resume_checkpoint(OUT/'startup.checkpoint')
    except Complete:
        pass
    except Exception as caught:
        error = repr(caught)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    report.update(status='pass' if error is None and len(trace.presentations) == args.frames else 'blocked',
        stop=None if error is None else dict(reason=error,phase=trace.phase,pc=hex(trace.machine.reg_read(UC_X86_REG_EIP))),
        events=input_trace.EVENTS, input_witnesses=trace.input_witnesses,
        startup_paper=True, clock_query_ms=1, frame_step_ms=17,
        scope='Original menu frames from the original paper-enabled startup; no native admission claim')
    if not args.idle:
        idle = json.loads((ROOT/'work/paper-roll/rebased/menu-map/trace.json').read_text())
        for key in ('game_functions','platform_calls','platform_imports'):
            previous = {r['address'] for r in idle[key]}
            report['new_'+key] = [r for r in report[key] if r['address'] not in previous]
    path = output/('trace.json' if args.idle else 'original.json')
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],stop=report['stop'],frames=len(trace.presentations),output=str(path))))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
