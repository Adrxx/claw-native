"""Compare the fourteen reviewed roots with real native scene/input dispatch.

Run: work/test-env/bin/python Tests/SceneInputJoin/compare.py
Only platform/allocator fixtures from the two family specifications are used.
The generated manifest is a comparison composition, never an admission claim.
"""
import json
import importlib.util
import os
import random
from collections import Counter
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
INPUT = {'0x430d30', '0x430d80', '0x430ec0', '0x431300', '0x4b3430', '0x4b3490', '0x4b3ab0'}


def main():
    scene = json.loads((ROOT / 'Tests/families/scene_camera.json').read_text())
    inputs = json.loads((ROOT / 'Tests/families/application_input_configuration.json').read_text())
    manifest = dict(scene)
    manifest['id'] = 'scene_input_join'
    manifest['sources'] = scene['sources'] + inputs['sources'] + ['Tests/SceneInputJoin/dispatch.cpp']
    manifest['owned'] = scene['owned'] + [o for o in inputs['owned'] if o['address'] in INPUT]
    manifest['callees'] = dict(scene['callees'])
    for address in INPUT:
        manifest['callees'].pop(address)
    # All setup overrides remain legal, even when this subset does not call them.
    for address, callee in inputs['callees'].items():
        manifest['callees'].setdefault(address, callee)
    manifest['oracle'] = {'kind': 'clawparity', 'cases': 'Tests/SceneInputJoin/cases.py',
                          'entry': 'claw_scene_input_join_entry'}
    manifest['evidence'] = {'level': 'none'}
    sys.path.insert(0, str(ROOT / 'Tests'))
    case_spec = importlib.util.spec_from_file_location('scene_input_join_cases', ROOT / 'Tests/SceneInputJoin/cases.py')
    case_module = importlib.util.module_from_spec(case_spec)
    case_spec.loader.exec_module(case_module)
    os.environ.pop('CLAW_JOIN_MISSING', None)
    direct = Counter(hex(case.function) for case in case_module.cases(random.Random(29)))
    if set(direct) != {o['address'] for o in manifest['owned']}:
        raise RuntimeError('The comparison must directly exercise exactly all fourteen reviewed roots')
    folder = ROOT / 'work/scene-input-join'
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for missing in (False, True):
        manifest['oracle']['entry'] = 'claw_scene_input_join_missing_entry' if missing else 'claw_scene_input_join_entry'
        path = folder / ('missing.json' if missing else 'joined.json')
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        env = dict(os.environ)
        if missing:
            env['CLAW_JOIN_MISSING'] = '1'
        else:
            env.pop('CLAW_JOIN_MISSING', None)
        process = subprocess.run([sys.executable, '-m', 'tools.claw', 'oracle', str(path), '--seed', '29'],
                                 cwd=ROOT, env=env, capture_output=True, text=True)
        (folder / ('missing.log' if missing else 'joined.log')).write_text(process.stdout + process.stderr)
        report = json.loads(process.stdout.strip().splitlines()[-1])
        results.append(report)
        if not missing:
            if report.get('status') != 'pass' or report.get('cases') != sum(direct.values()):
                print(json.dumps(report))
                return 1
        else:
            failures = report.get('failures', [])
            if (not failures or report.get('passed') != 0 or report.get('failed') != report.get('cases')
                    or any(f.get('kind') != 'native-fault' or 'fault unimplemented at ' not in f.get('detail', '')
                           for f in failures)):
                print(json.dumps(report))
                return 1
    summary = {'command': 'scene-input-join', 'status': 'pass',
               'roots': [o['address'] for o in manifest['owned']],
               'direct_calls': dict(sorted(direct.items())),
               'joined_cases': results[0]['cases'],
               'outside_calls_compared': results[0]['outside_calls_compared'],
               'missing_owner_faults': results[1]['failed'],
               'scope': 'Canonical test composition; shipping app and visible menu acceptance remain pending.'}
    (folder / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
