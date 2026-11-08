"""Compare the Mac app's scripted Level 1 play with the native Level 1 join.

Join: work/test-env/bin/python -m Tests.NativeLevelOne.native_join  (work/native-level-one-join/result.json)
App:  work/new-game/run-play.sh  (writes work/new-game/play/play-frames.json)
Check: work/test-env/bin/python scripts/check-level-one-play.py

Every play frame's elapsed time, scripted action and player fields must match.
The input plan the app replayed must be the join tracer's own plan.
"""
import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('x', 'y', 'health', 'score', 'player_state', 'logic_state', 'treasure_counts',
          'input_mask', 'game_ms', 'level', 'vtable')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, default=ROOT / 'work/new-game/play')
parser.add_argument('--plan', type=Path, default=ROOT / 'work/new-game/play-plan.json')
parser.add_argument('--join', type=Path, default=ROOT / 'work/native-level-one-join/result.json')
args = parser.parse_args()


def tracer_plan():
    tree = ast.parse((ROOT / 'Tests/NativeLevelOne/trace.py').read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Attribute)
                and node.targets[0].attr == 'input_plan' and isinstance(node.value, ast.List)):
            return [{k.arg: ast.literal_eval(k.value) for k in item.keywords} for item in node.value.elts]
    raise SystemExit('tracer input plan not found')


def main():
    report = dict(check='level-one-play', evidence=str(args.evidence))
    try:
        plan = json.loads(args.plan.read_text())
        if plan != tracer_plan():
            raise AssertionError('app play plan differs from the join tracer input plan')
        join = json.loads(args.join.read_text())
        if join.get('status') != 'native-complete' or not join['comparison']['passed']:
            raise AssertionError('join result is not a passing native-complete run')
        app = json.loads((args.evidence / 'play-frames.json').read_text())
        if app.get('status') != 'pass':
            raise AssertionError('app play run did not complete')
        reference, actual = join['play_frames'], app['play_frames']
        matched, divergence = 0, None
        for index, (a, b) in enumerate(zip(reference, actual)):
            fields = [k for k in FIELDS if a['player'].get(k) != b['player'].get(k)]
            if a['elapsed_ms'] != b['elapsed_ms'] or a['action'] != b['action'] or fields:
                divergence = dict(frame=index, elapsed_ms=[a['elapsed_ms'], b['elapsed_ms']],
                                  action=[a['action'], b['action']],
                                  fields={k: [a['player'].get(k), b['player'].get(k)] for k in fields})
                break
            matched += 1
        moved = actual[-1]['player']['x'] != actual[0]['player']['x']
        report.update(join_frames=len(reference), app_frames=len(actual), matched_frames=matched,
                      divergence=divergence, claw_moved=moved,
                      start=dict(x=actual[0]['player']['x'], y=actual[0]['player']['y']),
                      end=dict(x=actual[-1]['player']['x'], y=actual[-1]['player']['y'],
                               score=actual[-1]['player']['score']))
        passed = divergence is None and len(reference) == len(actual) and moved
        report['status'] = 'pass' if passed else 'fail'
    except (AssertionError, OSError, KeyError, ValueError) as error:
        report.update(status='fail', error=str(error))
    print(json.dumps(report))
    raise SystemExit(0 if report['status'] == 'pass' else 1)


main()
