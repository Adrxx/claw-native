"""Compare the Level 13 Mac route with the hash-verified original reference.

MPSCULLY advances Levels 1 through 12. Compare every player frame, pickup,
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
from Tests.NativeLevels.storage import stored_path, trace_rows, fingerprint

WORK = Path(os.environ.get('CLAW_LEVEL_THIRTEEN_PLAY_WORK', ROOT / 'work/level-thirteen-play'))
TRACE = Path(os.environ.get('CLAW_LEVEL_THIRTEEN_PLAY_REFERENCE', ROOT / 'work/native-level-13-join/original-route.json'))
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
        data = json.loads(cache.read_text())
        if data.get('reference_identity') == identity:
            validate_reference(data)
            return data
    keep = {'frames', 'plan', 'play_frames', 'state_transitions', 'key_deliveries', 'frame_cycles', 'presentations', 'game_functions', 'startup_context'}
    data, posted = {}, []
    for key, kind, value in trace_rows(TRACE):
        if kind == 'array' and key in keep:
            data[key] = []
        elif kind == 'item':
            if key in keep:
                data[key].append(value)
            if key == 'physical_events' and value.get('service') == 'PostMessageA':
                posted.append(hex(value['wparam']))
        elif kind == 'value':
            data[key] = value
    if data['status'] != 'pass':
        raise ValueError('Original Level 13 trace is not passing')
    presentations = iter(p for p in data.pop('presentations') if p['phase'].startswith('level-13-'))
    data['screens'] = [[[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
                        for p in (next(presentations) for _ in range(c['presentations']))]
                       for c in data.pop('frame_cycles') if c['phase'].startswith('level-13-')]
    data['posted'] = posted
    data['reference_identity'] = identity
    validate_reference(data)
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def validate_reference(data):
    from Tests.NativeLevels.level_thirteen_join import validate_independent
    plan = json.loads((ROOT/'work/level-13-map/plan.json').read_text())
    validate_independent(data, plan)
    if os.environ.get('PAPER') == '1':
        bindings = {e.get('binding') for e in data.get('startup_context', [])}
        queries = data.get('startup_queries', {})
        objects = data.get('startup_objects') or {}
        if (data.get('startup_profile') != {'paper': True, 'query_ms': 1}
                or not queries.get('count') or queries.get('increments') != {'1': queries['count']}
                or any(objects.get(hex(o), '0x0') == '0x0' for o in (0x44, 0x58))
                or not {'application+0x44', 'application+0x58'} <= bindings):
            raise ValueError('Original lacks paper startup and 1 ms startup queries')
    if len(data['frames']) != 3531:
        raise ValueError('Original route lacks all 3531 snapshots')
    if data.get('route_scheduler') == 'retained-17-ms-input-frames':
        if data['frames'][-1]['elapsed_ms'] != data['played_ms']:
            raise ValueError('Original physical elapsed time is inconsistent')
        for index, frame in enumerate(data['frames'][1:]):
            action = next(a for a in plan if a['start_ms'] <= index * 17 < a['end_ms'])
            if frame['action'] != action['action']:
                raise ValueError('Original skipped a retained input action')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    args = parser.parse_args()
    report = dict(check='level-thirteen', status='fail', errors=[])
    errors = report['errors']
    try:
        ref = original()
        report.update(reference=str(TRACE), reference_sha256=fingerprint(TRACE), fresh=not args.reuse)
        if not args.reuse:
            OUT.mkdir(parents=True, exist_ok=True)
            for name in ('app-menu.json', 'live-state.json', 'level-thirteen-route.json'):
                (OUT/name).unlink(missing_ok=True)
            (WORK/'plan.json').write_text(json.dumps(ref['plan']))
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '12000',
                '--menu-live-check', str(OUT), '--new-game-clock', '--level-thirteen-route', str(WORK/'plan.json')] +
                (['--level-thirteen-retained-plan'] if ref.get('route_scheduler') == 'retained-17-ms-input-frames' else []),
                cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
        app = json.loads((OUT/'level-thirteen-route.json').read_text())
        if app.get('status') != 'pass':
            errors.append('App route did not pass')
        for label, expected, actual in [('Level 1', ref['play_frames'], app['level_one_frames']),
                                        ('Level 13', ref['frames'], app['level_thirteen_frames'])]:
            difference = play.frames_divergence(expected, actual)
            if difference:
                errors.append(f'{label}: {difference}')
        climb_pairs = sum(a['player']['logic_state'] == b['player']['logic_state'] == 27
            and b['player']['y'] < a['player']['y'] for a, b in zip(ref['frames'], ref['frames'][1:]))
        report['climb_pairs'] = climb_pairs
        if climb_pairs != 0:
            errors.append('Original Level 13 has no ladder tiles; climbing is unexpected')
        actual = app['level_thirteen_frames']
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
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK/'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
