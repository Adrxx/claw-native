"""Compare the Level 4 Mac route with the hash-verified original reference.

MPSCULLY advances Levels 1 through 3. Compare every player frame, pickup,
health transition, state reuse, delivered cheat/Return key and presented hash.
--reuse compares retained app evidence without launching.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import stored_path, trace_rows

WORK = ROOT / 'work/level-four-play'
TRACE = ROOT / 'work/level-4-map/trace.json'
OUT = WORK / 'run'
spec = importlib.util.spec_from_file_location('level_two_check', ROOT/'scripts/check-level-two-play.py')
play = importlib.util.module_from_spec(spec)
spec.loader.exec_module(play)


def original():
    cache = WORK/'original.json'
    path = stored_path(TRACE)
    identity = [str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size,
                hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    if cache.exists():
        cached = json.loads(cache.read_text())
        if cached.get('identity') == identity:
            return cached['reference']
    keep = {'frames', 'plan', 'play_frames', 'state_transitions', 'key_deliveries', 'frame_cycles', 'presentations', 'game_functions'}
    data, posted = {}, []
    for key, kind, value in trace_rows(TRACE):
        if kind == 'array' and key in keep:
            data[key] = []
        elif kind == 'item':
            if key in keep:
                data[key].append(value)
            if key == 'physical_events' and value.get('service') == 'PostMessageA':
                posted.append(hex(value['wparam']))
        elif kind == 'value' and key in ('status', 'stop', 'startup_profile', 'parent_checkpoint', 'played_ms'):
            data[key] = value
    if data['status'] != 'pass':
        raise ValueError('Original Level 4 trace is not passing')
    presentations = iter(p for p in data.pop('presentations') if p['phase'].startswith('level-4-'))
    data['screens'] = [[[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
                        for p in (next(presentations) for _ in range(c['presentations']))]
                       for c in data.pop('frame_cycles') if c['phase'].startswith('level-4-')]
    data['posted'] = posted
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(identity=identity, reference=data)))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--reference', type=Path, help='Staged original trace; defaults to the retained reference')
    parser.add_argument('--evidence', type=Path, help='Separate comparison directory for staged evidence')
    args = parser.parse_args()
    global WORK, TRACE, OUT
    if args.reference:
        TRACE = args.reference.resolve()
    if args.evidence:
        WORK = args.evidence.resolve()
        if not WORK.is_relative_to(ROOT/'work'):
            parser.error('--evidence must stay under work/')
        OUT = WORK/'run'
    report = dict(check='level-four', status='fail', accepted=False, errors=[],
                  reference=str(TRACE), evidence=str(OUT), fresh=not args.reuse,
                  paper=os.environ.get('PAPER', '0') == '1')
    errors = report['errors']
    try:
        ref = original()
        report['startup_profile'] = ref.get('startup_profile')
        parent = ref.get('parent_checkpoint') or {}
        level_two_prefix = (ref.get('startup_profile') == {'paper': True, 'query_ms': 1}
                            and Path(parent.get('path', '')).name == 'level-two-start.pkl')
        report['level_two_prefix'] = level_two_prefix
        with stored_path(TRACE).open('rb') as stream:
            report['reference_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if not args.reuse:
            OUT.mkdir(parents=True, exist_ok=True)
            for name in ('app-menu.json', 'live-state.json', 'level-four-route.json'):
                (OUT/name).unlink(missing_ok=True)
            (WORK/'plan.json').write_text(json.dumps(ref['plan']))
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                '--menu-live-check', str(OUT), '--new-game-clock', '--level-four-route', str(WORK/'plan.json')]
                + (['--route-level-two-prefix'] if level_two_prefix else []),
                cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
        app = json.loads((OUT/'level-four-route.json').read_text())
        if app.get('status') != 'pass':
            errors.append('App route did not pass')
        for label, expected, actual in [('Level 1', ref['play_frames'], app['level_one_frames']),
                                        ('Level 4', ref['frames'], app['level_four_frames'])]:
            difference = play.frames_divergence(expected, actual)
            if difference:
                errors.append(f'{label}: {difference}')
        actual = app['level_four_frames']
        original_events = play.summaries([f['player'] for f in ref['frames']])
        actual_events = play.summaries([f['player'] for f in actual])
        if actual_events != original_events:
            errors.append('Pickup or health transitions differ')
        report.update(frames=len(actual), pickups=actual_events[0], health_changes=actual_events[1])
        if not original_events[0]:
            errors.append('Original route lacks pickups')
        shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
        if shape(ref['state_transitions']) != shape(app['state_transitions']):
            errors.append('State transitions differ')
        def identities(states):
            objects = [s['object'] for s in states]
            return [objects.index(obj) for obj in objects]
        if identities(ref['state_transitions']) != identities(app['state_transitions']):
            errors.append('State object reuse differs from the original')
        def keys(rows, states):
            start = states[0]['milliseconds']
            return [(k['phase'], k['key'], k['scan'], k['target'], k['vtable'], k['milliseconds']-start) for k in rows]
        ak = keys(app['key_deliveries'], app['state_transitions'])
        rk = keys(ref['key_deliveries'], ref['state_transitions'])
        if ak != rk:
            errors.append(f'Key deliveries differ: {ak}, original {rk}')
        report['key_deliveries'] = len(ak)
        tail = lambda p: p[p.index('0x800e'):] if '0x800e' in p else []
        if tail(ref['posted']) != tail(app['posted_commands']):
            errors.append('Posted commands differ')
        screens = [f.get('screens', []) for f in actual[1:]]
        matched = sum(a == b for a, b in zip(screens, ref['screens']))
        report['presented_frames'] = dict(original=len(ref['screens']), app=len(screens), matched=matched)
        if matched != len(ref['screens']) or len(screens) != len(ref['screens']):
            first = next((i for i, (a,b) in enumerate(zip(screens, ref['screens'])) if a != b), None)
            errors.append(f'Presented screens differ at frame {first}')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        errors.append(str(error))
        try:
            report['app'] = json.loads((OUT/'app-menu.json').read_text())
        except (OSError, ValueError):
            pass
    report['status'] = 'fail' if errors else 'pass'
    report['accepted'] = not errors and not args.reuse
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK/'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
