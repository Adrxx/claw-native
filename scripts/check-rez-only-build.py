#!/usr/bin/env python3
"""Check player data paths/tables, and optionally muted Level 1 through real keys."""
import argparse
import hashlib
import json
import runpy
from pathlib import Path
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def check_data(data):
    rez = (data / 'MENU/CLAW.REZ').read_bytes()
    assert hashlib.sha256(rez).hexdigest() == 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
    files = {}
    def walk(offset, size, parent):
        end = offset + size
        while offset < end:
            kind, target, length = struct.unpack_from('<III', rez, offset)
            start = offset + (16 if kind else 28)
            zero = rez.index(0, start, end)
            name = rez[start:zero].decode('ascii')
            if kind:
                walk(target, length, parent / name)
                offset = zero + 1
            else:
                ext = rez[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii')
                files[(parent / (name+'.'+ext)).as_posix()] = (target, length)
                offset = zero + 2
    walk(*struct.unpack_from('<II', rez, 131), Path())
    worlds = []
    for level in range(1, 15):
        name = f'LEVEL{level}/WORLDS/WORLD.WWD'
        offset, length = files[name]
        assert (data / name).read_bytes() == rez[offset:offset+length], name
        worlds.append(name)
    tables = []
    for source in (ROOT / 'App/OriginalTables').rglob('*.json'):
        relative = source.relative_to(ROOT / 'App/OriginalTables')
        assert source.read_bytes() == (data / relative).read_bytes(), str(relative)
        tables.append(str(relative))
    movie_manifest = data / 'MOVIES/movies.json'
    if movie_manifest.exists():
        manifest = json.loads(movie_manifest.read_text())
        assert sorted(e['movieID'] for e in manifest['entries']) == list(range(1, 13))
        for entry in manifest['entries']:
            path = data / 'MOVIES' / entry['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], str(path)
    helpers = runpy.run_path(str(ROOT / 'scripts/crazyhook_assets.py'))
    included = ROOT / 'App/CrazyHookHelpers'
    manifest = helpers['check_helpers'](included, readme=True)
    assert helpers['check_helpers'](data / 'CRAZYHOOK') == manifest
    for name in [*manifest['files'], 'manifest.json']:
        assert (included / name).read_bytes() == (data / 'CRAZYHOOK' / name).read_bytes(), name
    return dict(worlds_match_rez=len(worlds), tables_match=len(tables),
                crazyhook_helpers_match=len(manifest['files']),
                movies=(data / 'MOVIES/movies.json').exists(),
                original_music=(data / 'MENU/CLAW4.SF2').exists(),
                crazyhook_helpers=(data / 'CRAZYHOOK/manifest.json').exists())


def check_live(app, output, music=False, absent_movies=False):
    sys.path.insert(0, str(ROOT / 'scripts'))
    from real_input import Session, build_helper
    output.mkdir(parents=True, exist_ok=True)
    session = Session(output, fast=True, helper=build_helper(ROOT / 'work/rez-only-build/post-window-input'))
    try:
        session.launch(app, {}, ['--stationary-cursor', '--save-dir', str(output/'saves'),
            '--menu-live-check', str(output),
            *(['--movie-flow-check', str(output)] if absent_movies else []),
            '-ClawCheckDirectory', str(output),
            *(['--music-render', str(output/'music')] if music else [])])
        # Walk New Game, difficulty and player confirmation with real input.
        for attempt in range(12):
            session.run(180)
            state = json.loads((output/'live.json').read_text())
            if state.get('state_vtable') == '0x50c264':
                break
            session.post('press', 36, 'down')
            session.run(4)
            session.post('press', 36, 'up')
        session.run(120)
        before = json.loads((output/'live.json').read_text())
        assert before.get('state_vtable') == '0x50c264', before
        session.post('press', 124, 'down')
        session.run(30)
        session.post('press', 124, 'up')
        session.run(4)
        after = json.loads((output/'live.json').read_text())
        assert before['x'] != after['x'], (before, after)
        assert (output/'input.json').exists(), 'No confirmed real input'
        state = json.loads((output/'live-state.json').read_text())
        assert state.get('status') == 'running', state
        result = dict(level_one_play=True, real_input=True, start=before['x'], end=after['x'])
        if music:
            deadline = time.monotonic() + 120
            renders = []
            while time.monotonic() < deadline:
                renders = [json.loads(p.read_text()) for p in (output/'music').glob('*.json')]
                if any(r.get('status') == 'done' and r.get('nonzero_samples', 0) > 0 for r in renders):
                    break
                if any(r.get('status') == 'fail' for r in renders):
                    raise AssertionError(renders)
                time.sleep(0.1)
            assert any(r.get('nonzero_samples', 0) > 0 for r in renders), renders
            result['offline_music_nonzero'] = True
        return result
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'App/GameData')
    parser.add_argument('--app', type=Path)
    parser.add_argument('--music', action='store_true', help='Require a non-silent offline MIDI render; never uses speakers')
    parser.add_argument('--output', type=Path, default=ROOT/'work/rez-only-build/live')
    args = parser.parse_args()
    report = check_data(args.data)
    if args.app:
        report.update(check_live(args.app.resolve(), args.output.resolve(), args.music, not report['movies']))
    report['status'] = 'pass'
    print(json.dumps(report))


if __name__ == '__main__':
    main()
