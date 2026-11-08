"""Check a generated local WWD in the original loader and muted Mac app.

Generate first with tools.claw.test_level. --reuse-original keeps the costly
original probe; --reuse checks retained evidence only. Neither certifies a family.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT/'work/test-env/bin/python'
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import read_trace


def cool():
    while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        print('Waiting for load below 16', flush=True)
        time.sleep(10)


def real_keys(path):
    output = path.parent/'input'
    output.mkdir(parents=True, exist_ok=True)
    for name in ('before.json', 'after.json', 'result.json'):
        (output/name).unlink(missing_ok=True)
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    session = Session(output, helper=helper)
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    try:
        session.launch(app, dict(CLAW_LOCAL_TEST_LEVELS='1'),
            ['--test-level', str(path), '--menu-live-check', str(output), '--no-paper-startup'])
        session.run(1)
        before = session.mark('before')
        session.post('press', 124, 'down')
        session.run(12)
        session.post('press', 124, 'up')
        session.run(1)
        after = session.mark('after')
        assert before and after and after['player']['x'] > before['player']['x'], 'Real Right key did not move the player'
        assert not session.failed(), 'App faulted after real input'
        report = dict(status='pass', x_before=before['player']['x'], x_after=after['player']['x'],
            transitions=session.transitions(), wwd_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
        return report
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wwd', type=Path, default=ROOT/'work/test-levels/objects.WWD')
    parser.add_argument('--reuse-original', action='store_true')
    parser.add_argument('--reuse', action='store_true')
    args = parser.parse_args()
    path = args.wwd.resolve()
    if not path.is_relative_to((ROOT/'work/test-levels').resolve()):
        parser.error('WWD must remain in work/test-levels/')
    manifest = json.loads(path.with_suffix('.json').read_text())
    output = path.parent/'app'
    result = dict(check='test-level', status='fail', errors=[])
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == manifest['output_sha256'], 'Generated WWD changed'
        if not args.reuse and not args.reuse_original:
            cool()
            subprocess.run([str(PYTHON), '-m', 'Tests.NativeLevels.test_level_trace',
                '--wwd', str(path)], cwd=ROOT, check=True, timeout=600)
        original = read_trace(path.parent/'original/trace.json')
        assert original['status'] == 'pass', 'Original object probe failed'
        assert original['wwd_sha256'] == digest, 'Original probe used another WWD'
        if not args.reuse:
            cool()
            output.mkdir(parents=True, exist_ok=True)
            (output/'app-menu.json').unlink(missing_ok=True)
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(output), '180',
                '--test-level', str(path), '--menu-check', str(output), '--menu-frames', '61'],
                cwd=ROOT, env=dict(os.environ, CLAW_LOCAL_TEST_LEVELS='1'), check=True, timeout=200)
        app = json.loads((output/'app-menu.json').read_text())
        assert app['status'] == 'pass', 'App did not complete its scene'
        probe = app['test_level']
        assert probe['sha256'] == digest and probe['substitutions'] == 1 \
            and probe['runtime_level'] == manifest['source_level'], 'App fixture mismatch'
        assert len(app['frames']) == 61 and all(f['resourceFault'] == f['displayFault'] == 0
            and f['state_vtable'] == 0x50c264 for f in app['frames']), 'App scene fault or state change'
        selected = {row['id']: row for row in manifest['objects']}
        observed = {row['id']: row for row in probe['objects']}
        for identity, row in selected.items():
            actual = observed.get(identity, {})
            assert actual.get('logic') == row['logic'] and actual.get('actor') \
                and actual.get('image_set', 0) not in (0, 0xffffffff), f"App did not bind {row['logic']} ({identity})"
        assert len({r['logic'] for r in selected.values()}) >= 10, 'Acceptance requires ten object types'
        assert 7 <= manifest['source_level'] <= 13, 'Acceptance source must be Levels 7-13'
        keys = json.loads((path.parent/'input/result.json').read_text()) if args.reuse else real_keys(path)
        assert keys['status'] == 'pass' and keys['wwd_sha256'] == digest, 'Real-input evidence mismatch'
        result.update(status='pass', source_level=manifest['source_level'], runtime_level=manifest['source_level'],
            object_types=len(selected), original_played_ms=original['played_ms'], app_frames=len(app['frames']),
            wwd_sha256=digest, original_image=str(path.parent/'original/original.png'),
            app_image=str(output/'menu.png'), real_input=keys,
            scope='Original draws, native actor/image bindings and real input; inspect paired PNGs for visibility; not family parity')
    except (OSError, ValueError, KeyError, AssertionError, RuntimeError, subprocess.SubprocessError) as error:
        result['errors'].append(str(error))
    (path.parent/'check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return result['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
