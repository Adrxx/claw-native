"""Focused selectors plus optional original-backed local pilot demonstration.

Run selectors: python -m Tests.clawparity.selftest.named_layout_mutants
Run proof: add --demo-spec work/.../spec.json --baseline work/.../literal-mutations.json
The translator prepares the local source; this check never rewrites a family.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import admission_inputs, mutants
from .. import named_layout_mutants as named

ROOT = named.ROOT


def selectors():
    spec = {"owned": [{"address": "0x1000", "returns": "u32", "argc": 0, "convention": "thiscall"},
                      {"address": "0x2000", "returns": "u32", "argc": 0, "convention": "thiscall"}]}
    source = '''uint32_t first(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ActorFields actorFields{run, receiver};
    LogicHolderFields holderFields{run, receiver};
    // actorFields.holder(); BounceLogicState::Initialized; second(run, receiver, arguments);
    const char *text = "actorFields.holder() BounceLogicState::Initialized";
    uint32_t holder = actorFields.holder();
    holderFields.state(uint32_t(BounceLogicState::Initialized));
    if (holderFields.state() == uint32_t(BounceLogicState::Uninitialized))
        second(run, receiver, arguments);
    return 1;
}
uint32_t second(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x1000: return first(run, receiver, arguments);
    case 0x2000: return second(run, receiver, arguments);
    }
}
'''
    legacy, added = named.population(source, spec)
    every = legacy + added
    assert any('actorFields.holder<4>()' in '\n'.join(row[2]) for row in every)
    assert any('holderFields.state<4>(uint32_t' in '\n'.join(row[2]) for row in every)
    assert sum(op == 'flip-return-literal' for _, op, _ in every) == 2
    assert sum(op == 'swap-named-constant' for _, op, _ in every) == 2
    assert sum(op == 'redirect-named-call' for _, op, _ in every) == 1
    assert any(op == 'drop-statement' and row[6].strip() == ';' for _, op, row in every)
    for _, _, changed in every:
        assert changed[3:5] == source.splitlines()[3:5], 'comments/strings mutated'
    assert named.selected(legacy, added, 2)[-len(added):] == added
    assert len(named.selected(legacy, added, 0)) == len(every)
    qualified = source.replace('BounceLogicState::', 'claw::recovered::v10::BounceLogicState::')
    assert sum(op == 'swap-named-constant' for _, op, _ in named.population(qualified, spec)[1]) == 2
    integer = source.replace('    return 1;', '    constexpr uint32_t Limit = 3;\n    return Limit;')
    integer_mutants = named.population(integer, spec)[1]
    assert any('return (Limit ^ 1u);' in '\n'.join(row[2]) for row in integer_mutants)
    assert all('constexpr uint32_t Limit = 3;' in '\n'.join(row[2]) for row in integer_mutants)
    table = source[:source.index('uint32_t body(')] + 'Entry entries[] = {{0x1000, first}, {0x2000, &second}};'
    assert len(named.population(table, spec)[1]) == len(added)
    assert named.constants(['enum class State { A = 1u, B = 1, C = 2 };'])['State::A'] == 'State::C'
    try:
        named.constants(['enum class State { A = 1 << 2, B = 3 };'])
    except ValueError:
        pass
    else:
        raise AssertionError('enum expression mistaken for a literal')
    void = json.loads(json.dumps(spec))
    void['owned'][1]['returns'] = 'void'
    assert sum(op == 'flip-return-literal' for _, op, _ in sum(named.population(source, void), [])) == 1
    for bad in (source.replace('holderFields.state()', 'holderFields.state<4>()'),
                source.replace('actorFields.holder()', 'actorFields->holder()'),
                source.replace('ActorFields actorFields{run, receiver};', 'auto actorFields = unknown;'),
                source.replace('actorFields.holder()', 'actorFields.holder(\n)'),
                '#if CONDITIONAL\n' + source + '\n#endif',
                source.replace('ActorFields actorFields', 'LogicHolderFields actorFields'),
                source.replace('actorFields.holder()', 'holderFields.logic(actorFields.holder())'),
                source.replace('case 0x1000:', 'case 0x3000:')):
        try:
            named.population(bad, spec)
        except ValueError:
            pass
        else:
            raise AssertionError('unsupported source accepted')
    plain = admission_inputs.paths({})
    elected = admission_inputs.paths({'mutation': 'named-layout'})
    assert elected - plain == {'Tests/clawparity/named_layout_mutants.py', *named.HEADERS}
    # The source from the fixture is never needed to test dispatch isolation.
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'spec.json'
        path.write_text('{"mutation":"named-layout"}')
        with patch.object(named, 'run', return_value={'dispatched': True}) as run:
            assert mutants.run(path, 7, 9, 1) == {'dispatched': True}
            run.assert_called_once_with(path, 7, 9, 1)
        path.write_text('{"mutation":"named-layout", "sources":[]}')
        try:
            named.run(path)
        except ValueError as error:
            assert 'build-cache identity' in str(error)
        else:
            raise AssertionError('headers missing from build cache accepted')
    return {'status': 'pass', 'legacy_candidates': len(legacy), 'named_candidates': len(added)}


def snapshot():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
            (*named.HEADERS, 'Sources/LevelOnePlayerActions01Runtime.cpp',
             'Tests/families/level_one_player_actions_01.json')}


def negative_controls(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    source = (ROOT / spec['sources'][0]).read_text()
    legacy, added = named.population(source, spec)
    targets = [next(row for row in legacy if 'actorFields.holder<4>()' in '\n'.join(row[2])),
               next(row for row in added if row[1] == 'swap-named-constant'
                    and 'CallVirtual20' in source.splitlines()[row[0] - 1]),
               next(row for row in added if row[1] == 'redirect-named-call')]
    controls = []
    scratch = spec_path.parent / 'controls'
    scratch.mkdir(exist_ok=True)
    mapping, unused = named.registrations(named.masked(source), spec)
    import re
    for number, item in enumerate(targets):
        row = named.attempt(spec_path, source, item, number * 2, scratch, 1264891128)
        assert row['result'] == 'killed', row
        # Independent literal spellings of the same three errors. The first
        # offset is the recovered actor+0x6c plus four; enum values below are
        # the pinned v1.0 states, not output learned from a native run.
        text = '\n'.join(item[2])
        if number == 0:
            text = text.replace('actorFields.holder<4>()', 'run.get(actorFields + 0x70)')
        elif number == 1:
            for name, value in {'Uninitialized': '0', 'CallVirtual20': '0x1d',
                                'CallVirtual1c': '0x1e', 'Initialized': '0x3e8'}.items():
                text = text.replace('BounceLogicState::' + name, value)
        else:
            for name, address in mapping.items():
                text = re.sub(rf'\b{name}\b', f'function_{address:x}', text)
        assert text != '\n'.join(item[2])
        twin = named.attempt(spec_path, source, (item[0], item[1] + '-literal', text.splitlines()),
                             number * 2 + 1, scratch, 1264891128)
        assert twin['result'] == 'killed', twin
        assert twin['failures'] == row['failures'], (row, twin)
        controls.append({'named': row, 'literal': twin})
    return controls


def demo(spec_path, baseline_path):
    before = snapshot()
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    assert spec['mutation'] == 'named-layout'
    assert spec['sources'][0].startswith('work/'), 'demo must stay local'
    baseline = json.loads(Path(baseline_path).read_text())
    command = [sys.executable, '-m', 'clawparity.runner', str(spec_path), '--seed', '1264891128']
    done = subprocess.run(command, cwd=ROOT / 'Tests', capture_output=True, text=True)
    oracle = json.loads(done.stdout.strip().splitlines()[-1])
    assert done.returncode == 0 and oracle['status'] == 'pass', (oracle, done.stderr)
    result = mutants.run(spec_path, seed=1264891128, jobs=1)
    (spec_path.parent / 'named-mutations.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['status'] == 'pass', result
    assert result['killed'] >= baseline['killed'], result
    assert result['score'] >= baseline['score'], result
    assert not result['equivalent'], result
    # Three independent, actual-original negative controls, selected from the
    # same candidate generator the opt-in gate uses. Compare literal spellings
    # of these identical mistakes as well; only observed differences earn kills.
    controls = negative_controls(spec_path)
    assert snapshot() == before, 'mutation changed shared header/family inputs'
    report = {'status': 'pass', 'oracle': oracle, 'baseline': baseline,
              'named': result, 'controls': controls, 'shared_inputs_unchanged': True}
    (spec_path.parent / 'proof.json').write_text(json.dumps(report, indent=2) + '\n')
    return {'status': 'pass', 'cases': oracle['cases'], 'literal_score': baseline['score'],
            'literal_killed': baseline['killed'], 'named_score': result['score'],
            'named_killed': result['killed'], 'named_tried': result['tried'],
            'controls_killed': len(controls), 'proof': str(spec_path.parent / 'proof.json')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo-spec')
    parser.add_argument('--baseline')
    parser.add_argument('--controls-only', action='store_true')
    args = parser.parse_args()
    result = {'selectors': selectors()}
    if args.controls_only:
        result['controls'] = negative_controls(args.demo_spec)
    elif args.demo_spec:
        result['demo'] = demo(args.demo_spec, args.baseline)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
