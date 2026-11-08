"""Compare the Level 12 Mac route with the hash-verified original reference.

MPSCULLY advances Levels 1 through 11. Compare every player frame, pickup,
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

WORK = ROOT / 'work/level-twelve-play'
TRACE = ROOT / 'work/level-12-map/trace.json'
OUT = WORK / 'run'
spec = importlib.util.spec_from_file_location('level_two_check', ROOT/'scripts/check-level-two-play.py')
play = importlib.util.module_from_spec(spec)
spec.loader.exec_module(play)


def original():
    WORK.mkdir(parents=True, exist_ok=True)
    cache = WORK/'original.json'
    path = stored_path(TRACE)
    identity = [str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size,
                hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    if cache.exists():
        data = json.loads(cache.read_text())
        if data.get('reference_identity') == identity:
            validate_reference(data)
            return data
    keep = {'frames', 'plan', 'play_frames', 'state_transitions', 'key_deliveries', 'frame_cycles', 'presentations', 'game_functions', 'frame_wait_ms', 'respawn_query_events', 'respawn_timing'}
    data, posted = {}, []
    for key, kind, value in trace_rows(TRACE):
        if kind == 'array' and key in keep:
            data[key] = []
        elif kind == 'item':
            if key in keep:
                data[key].append(value)
            if key == 'physical_events' and value.get('service') == 'PostMessageA':
                posted.append(hex(value['wparam']))
        elif kind == 'value' and key in {'status', 'observer_checkpoint', 'string_compare_boundary', 'played_ms',
                'scheduled_play_ms', 'route_scheduler', 'input_source_snapshots', 'respawn_timing'}:
            data[key] = value
    if data['status'] != 'pass':
        raise ValueError('Original Level 12 trace is not passing')
    presentations = iter(p for p in data.pop('presentations') if p['phase'].startswith('level-12-'))
    data['screens'] = [[[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
                        for p in (next(presentations) for _ in range(c['presentations']))]
                       for c in data.pop('frame_cycles') if c['phase'].startswith('level-12-')]
    data['posted'] = posted
    data['reference_identity'] = identity
    validate_reference(data)
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def validate_reference(data):
    checkpoint = data['observer_checkpoint']
    if checkpoint['sha256'] != fingerprint(ROOT/checkpoint['path']):
        raise ValueError('Original Level 12 checkpoint changed')
    for name, digest in checkpoint['inputs_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Original checkpoint input changed: {name}')
    if hashlib.sha256((ROOT/checkpoint['runner']).read_bytes()).hexdigest() != checkpoint['runner_sha256']:
        raise ValueError('Original route runner changed')
    if hashlib.sha256((ROOT/'Tests/NativeLevels/string_compare_fixture.py').read_bytes()).hexdigest() != data['string_compare_boundary']['adapter_sha256']:
        raise ValueError('Original string-compare boundary changed')
    retained = data.get('route_scheduler') == 'retained-17-ms-input-frames'
    scheduled = data.get('scheduled_play_ms') if retained else data['played_ms']
    if scheduled != 105706 or len(data['frames']) != 6219:
        raise ValueError('Original route lacks the full retained 105706 ms')
    if retained:
        waits = data['frame_wait_ms']
        if len(waits) != 6218 or any(w < 1 or w > 17 for w in waits):
            raise ValueError('Original route lacks truthful physical frame waits')
        resumed = {t['frame']: t for t in data['respawn_timing']}
        for index, wait in enumerate(waits):
            timing = resumed.get(index)
            expected = timing['resume_sample_ms']+17-timing['after_ms'] if timing else 17
            if wait != expected:
                raise ValueError(f'Original frame wait differs at frame {index+1}')
        fade_ms = sum(t['after_ms']-t['before_ms'] for t in data['respawn_timing'])
        if (data['played_ms'] < scheduled or data['played_ms'] != sum(waits)+fade_ms
                or data['frames'][-1]['elapsed_ms'] != data['played_ms']):
            raise ValueError('Original physical clock omits frame or fade time')
        for index, frame in enumerate(data['frames'][1:]):
            action = next(a for a in data['plan'] if a['start_ms'] <= index*17 < a['end_ms'])
            if frame['action'] != action['action']:
                raise ValueError(f'Original retained action differs at frame {index+1}')
        if any(b['elapsed_ms'] <= a['elapsed_ms'] for a,b in zip(data['frames'],data['frames'][1:])):
            raise ValueError('Original physical clock is not monotonic')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--reference', type=Path, help='Staged original trace; defaults remain unchanged')
    parser.add_argument('--work', type=Path, help='Isolated app evidence and derived cache directory')
    args = parser.parse_args()
    global WORK, OUT, TRACE
    if args.work: WORK = args.work.resolve()
    OUT = WORK/'run'
    if args.reference: TRACE = args.reference.resolve()

    report = dict(check='level-twelve', status='fail', errors=[])
    errors = report['errors']
    try:
        ref = original()
        if not args.reuse:
            OUT.mkdir(parents=True, exist_ok=True)
            for name in ('app-menu.json', 'live-state.json', 'level-twelve-route.json'):
                (OUT/name).unlink(missing_ok=True)
            (WORK/'plan.json').write_text(json.dumps(ref['plan']))
            transport = []
            if ref.get('route_scheduler') == 'retained-17-ms-input-frames':
                waits = WORK/'frame-waits.json'
                waits.write_text(json.dumps(ref['frame_wait_ms']))
                transport = ['--level-twelve-retained-plan', '--level-twelve-frame-waits', str(waits)]
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '12000',
                '--menu-live-check', str(OUT), '--new-game-clock', '--level-twelve-route', str(WORK/'plan.json'), *transport],
                cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
        app = json.loads((OUT/'level-twelve-route.json').read_text())
        if ref.get('route_scheduler') == 'retained-17-ms-input-frames':
            report.update(scheduled_input_ms=ref['scheduled_play_ms'], physical_play_ms=ref['played_ms'],
                          respawn_queries=len(ref['respawn_query_events']))
            if app.get('respawn_query_events') != ref['respawn_query_events']:
                errors.append('Physical respawn timer queries differ')
        if app.get('status') != 'pass':
            errors.append('App route did not pass')
        for label, expected, actual in [('Level 1', ref['play_frames'], app['level_one_frames']),
                                        ('Level 12', ref['frames'], app['level_twelve_frames'])]:
            difference = play.frames_divergence(expected, actual)
            if difference:
                errors.append(f'{label}: {difference}')
        climb_pairs = sum(a['player']['logic_state'] == b['player']['logic_state'] == 27
            and b['player']['y'] < a['player']['y'] for a, b in zip(ref['frames'], ref['frames'][1:]))
        report['climb_pairs'] = climb_pairs
        if climb_pairs < 10:
            errors.append('Original route lacks sustained ladder climbing')
        actual = app['level_twelve_frames']
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
