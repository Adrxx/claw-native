"""Compare parameterized Level 2 discovery with the unchanged legacy planner."""
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels import plan as generic
from Tests.NativeLevelTwo import plan as legacy
from Tests.NativeLevelTwo.trace import LevelTwoTrace, PLAN
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevels.routes import route_for


SHARED_INPUTS = {'work/coordinator/all-levels/native.json', 'Sources/LogicStateRegistry.cpp'}
GENERIC_INPUTS = {'Tests/NativeLevels/plan.py', 'Tests/NativeLevels/discovery.py'}


def compare_closures(before, after):
    """Validate each provenance independently, then compare every computed field."""
    for label, closure, expected in (
            ('legacy', before, SHARED_INPUTS),
            ('generic', after, SHARED_INPUTS | GENERIC_INPUTS)):
        inputs = closure['inputs_sha256']
        assert set(inputs) == expected, (label, 'inputs_sha256', sorted(set(inputs) ^ expected))
        for path, digest in inputs.items():
            assert digest == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), (label, path)
    # Only the descriptive method and independently validated provenance differ.
    # Keep the input reports intact for the certificate and negative controls.
    computed = []
    for closure in (before, after):
        fields = dict(closure)
        fields.pop('method')
        fields.pop('inputs_sha256')
        computed.append(fields)
    before_fields, after_fields = computed
    assert before_fields == after_fields, sorted(
        k for k in before_fields.keys() | after_fields.keys()
        if k not in before_fields or k not in after_fields or before_fields[k] != after_fields[k])
    return len(before_fields)


def main():
    out = ROOT/'work/level-3-map/level-two-regression'
    out.mkdir(parents=True, exist_ok=True)
    write = Path.write_text

    def capture(path, data, *args, **kwargs):
        if path.parent == output_dir(2):
            path = out/('legacy-'+path.name)
        return write(path, data, *args, **kwargs)

    # Compare both algorithms against the same current world and admissions,
    # without replacing the retained Level 2 artifacts.
    with patch.object(Path, 'write_text', capture), patch.object(sys, 'argv', ['plan', '--static-only']):
        with contextlib.redirect_stdout(io.StringIO()):
            legacy.main()
    with patch.object(sys, 'argv', ['plan', '--level', '2', '--static-only', '--output-dir', str(out/'generic')]):
        with contextlib.redirect_stdout(io.StringIO()):
            generic.main()
    before = json.loads((out/'legacy-closure.json').read_text())
    after = json.loads((out/'generic/closure.json').read_text())
    exact_static_fields = compare_closures(before, after)
    # Level 2 takes the exact existing play method, unchanged input schedule,
    # and inherited physical services; the additional grid branch is for larger
    # later-level vectors only. Exercise delegation without emulating the game.
    assert route_for(2) is PLAN
    tracer = object.__new__(LevelTrace)
    tracer.target_level = 2
    with patch.object(LevelTwoTrace, 'level_two', return_value='legacy') as call:
        assert tracer.level_two(123) == 'legacy'
        call.assert_called_once_with(123)
    result = dict(status='pass', level=2, totals=after['totals'],
                  exact_static_fields=exact_static_fields, play_delegation=True,
                  plan_sha256=hashlib.sha256(json.dumps(PLAN, sort_keys=True).encode()).hexdigest(),
                  inputs_sha256={**after['inputs_sha256'], **{
                      str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (Path(__file__), Path(legacy.__file__), Path(generic.__file__), ROOT/'Tests/NativeLevelTwo/trace.py',
                                ROOT/'Tests/NativeLevels/trace.py', ROOT/'Tests/NativeLevels/routes.py', ROOT/'Tests/NativeLevels/storage.py')}})
    (out/'check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
