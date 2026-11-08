"""Check that the Level 14 observer bounds stalled frames without guest writes."""
import hashlib
import json
import time
from unittest.mock import patch
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels.level_fourteen_trace import LevelFourteenTrace, RUNNER, Blocked
from Tests.NativeLevels.string_compare_trace import StringCompareTrace


def main():
    controls = []
    for steps, age, name in ((5013503, 0, 'instruction bound'),
                             (16383, 46, 'wall time bound')):
        tracer = object.__new__(LevelFourteenTrace)
        tracer.frame_started = time.monotonic()-age
        tracer.frame_steps = steps
        tracer.played_ms = 123
        with patch.object(StringCompareTrace, 'hook') as parent:
            try:
                tracer.hook(None, 0x426e30, 1, None)
            except Blocked:
                assert tracer.stop['kind'] == 'frame_budget'
                assert tracer.stop['address'] == '0x426e30'
                assert tracer.stop['elapsed_ms'] == 123
                parent.assert_not_called()
            else:
                raise AssertionError('Stalled frame was not bounded')
        controls.append(name)
    tracer = object.__new__(LevelFourteenTrace)
    tracer.frame_started = None
    with patch.object(StringCompareTrace, 'hook') as parent:
        tracer.hook(None, 0x426e30, 1, None)
        parent.assert_called_once_with(None, 0x426e30, 1, None)
    controls.append('ordinary hooks delegate')
    with patch.object(StringCompareTrace, 'frame', side_effect=Blocked('stop')):
        try:
            tracer.frame(1, 'stand', [])
        except Blocked:
            assert tracer.frame_started is None
        else:
            raise AssertionError('Observer swallowed the stop')
    controls.append('frame interruption propagates and clears budget')
    report = dict(status='pass', controls=controls, runner=RUNNER,
                  runner_sha256=hashlib.sha256((ROOT/RUNNER).read_bytes()).hexdigest())
    (output_dir(14)/'runner-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
