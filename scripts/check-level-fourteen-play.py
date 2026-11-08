"""Compare the Level 14 Mac route with the hash-verified original reference.

MPSCULLY advances Levels 1 through 13. Compare every player frame, pickup,
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

WORK = ROOT / 'work/level-fourteen-play'
TRACE = ROOT / 'work/native-level-14-join/original-route.json'
OUT = WORK / 'run'
spec = importlib.util.spec_from_file_location('level_two_check', ROOT/'scripts/check-level-two-play.py')
play = importlib.util.module_from_spec(spec)
spec.loader.exec_module(play)


def original():
    cache = WORK/'original.json'
    identity = [str(TRACE.resolve()), fingerprint(TRACE), hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    if cache.exists():
        data = json.loads(cache.read_text())
        if data.get('source_identity') == identity:
            validate_reference(data)
            return data
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
        elif kind == 'value':
            data[key] = value
    if data['status'] != 'pass':
        raise ValueError('Original Level 14 trace is not passing')
    presentations = iter(p for p in data.pop('presentations') if p['phase'].startswith('level-14-'))
    data['screens'] = [[[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
                        for p in (next(presentations) for _ in range(c['presentations']))]
                       for c in data.pop('frame_cycles') if c['phase'].startswith('level-14-')]
    data['posted'] = posted
    data['source_identity'] = identity
    validate_reference(data)
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def validate_reference(data):
    from Tests.NativeLevels.level_fourteen_join import validate_independent
    plan = json.loads((ROOT/'work/level-14-map/plan.json').read_text())
    paper = data.get('startup_profile', {}).get('paper') is True
    if paper:
        # The fresh paper run includes a synchronous respawn. Its physical
        # 60-second plan remains intact; fewer idle snapshots fit inside it.
        from Tests.NativeLevels.level_fourteen_join import RUNNER, digest, TRACE_INPUTS, EXE_SHA256, REZ_SHA256, REZ_PATH, shared
        if (data.get('status') != 'pass' or data.get('stop') is not None
                or data.get('level') != 14 or data.get('plan') != plan
                or data.get('played_ms') != 60006 or len(data['frames']) != 3368):
            raise ValueError('Incomplete full-duration paper Level 14 route')
        for key in ('prefix_checkpoint_sha256', 'resumed_checkpoint', 'observer_checkpoint',
                    'checkpoint_advancement', 'later_advancement', 'parent_checkpoint'):
            if data.get(key): raise ValueError('Paper route must execute its complete fresh prefix')
        inputs = {**TRACE_INPUTS, 'observer_transport_sha256':'Tests/NativeLevels/level_thirteen_join.py',
                  'independent_runner_sha256':RUNNER}
        for key, path in inputs.items():
            if data.get(key) != digest(path): raise ValueError('Changed original input: '+path)
        rank = data.get('rank_sort_reference', {})
        if (rank.get('algorithm') != 'unchanged original CRT 0x4f1e20'
                or not rank.get('completed') or rank.get('active') is not False):
            raise ValueError('Paper pixels lack original CRT rank ordering')
        resources, clock = data.get('resources', {}), data.get('xmidi_clock_adapter', {})
        if (data.get('executable_sha256') != EXE_SHA256 or resources.get('sha256') != REZ_SHA256
                or resources.get('archive') != str(REZ_PATH.relative_to(ROOT))
                or (clock.get('version'),clock.get('hz'),clock.get('sha256')) !=
                   (shared.CLOCK_VERSION,120,digest('Tests/NativeLevels/xmidi_clock.py'))):
            raise ValueError('Paper original binary, archive or clock changed')
    else:
        validate_independent(data, plan)
    if os.environ.get('PAPER') == '1':
        queries = data.get('startup_queries', {})
        objects = data.get('startup_objects') or {}
        if (data.get('startup_profile') != dict(paper=True, query_ms=1)
                or not queries.get('count')
                or queries.get('increments') != {'1': queries['count']}
                or any(objects.get(k, '0x0') == '0x0' for k in ('0x44','0x58'))):
            raise ValueError('Reference lacks original paper startup and 1 ms queries')
    if not paper and len(data['frames']) != 3531:
        raise ValueError('Original route lacks all 3531 snapshots')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    global WORK, OUT, TRACE
    if args.reference:
        TRACE = args.reference.resolve()
    if args.evidence:
        WORK = args.evidence.resolve()
        OUT = WORK/'run'
    WORK.mkdir(parents=True, exist_ok=True)
    report = dict(check='level-fourteen', status='fail', errors=[])
    errors = report['errors']
    try:
        ref = original()
        if not args.reuse:
            OUT.mkdir(parents=True, exist_ok=True)
            for name in ('app-menu.json', 'live-state.json', 'level-fourteen-route.json'):
                (OUT/name).unlink(missing_ok=True)
            # Original's LevelTrace stops at target_play_ms=60000. The
            # retained plan ends at 60010 to cover the last fixed-step tick.
            # A paper respawn changes that final tick to 60006; use the actual
            # producer duration so the app does not execute one extra tick.
            app_plan = json.loads(json.dumps(ref['plan']))
            if ref.get('startup_profile', {}).get('paper'):
                app_plan[-1]['end_ms'] = 60000
            (WORK/'plan.json').write_text(json.dumps(app_plan))
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '12000',
                '--menu-live-check', str(OUT), '--new-game-clock', '--level-fourteen-route', str(WORK/'plan.json')],
                cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
        app = json.loads((OUT/'level-fourteen-route.json').read_text())
        if app.get('status') != 'pass':
            errors.append('App route did not pass')
        for label, expected, actual in [('Level 1', ref['play_frames'], app['level_one_frames']),
                                        ('Level 14', ref['frames'], app['level_fourteen_frames'])]:
            difference = play.frames_divergence(expected, actual)
            if difference:
                errors.append(f'{label}: {difference}')
        climb_pairs = sum(a['player']['logic_state'] == b['player']['logic_state'] == 27
            and b['player']['y'] < a['player']['y'] for a, b in zip(ref['frames'], ref['frames'][1:]))
        report['climb_pairs'] = climb_pairs
        if climb_pairs < 30:
            errors.append('Original Level 14 lacks sustained climbing')
        actual = app['level_fourteen_frames']
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
