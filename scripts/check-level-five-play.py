"""Compare the Level 5 Mac route with the hash-verified original reference.

MPSCULLY advances Levels 1 through 4. Compare every player frame, pickup,
health transition, state reuse, delivered cheat/Return key and presented hash.
--reuse compares retained app evidence without launching.
--section death checks the additional walk into danger, death and respawn.
Regenerate it with python -m Tests.NativeLevels.trace --level 5
--plan work/level-five-death/plan.json --output work/level-five-death/trace.json.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import fingerprint, stored_path, trace_rows

WORK = ROOT / 'work/level-five-play'
TRACE = ROOT / 'work/level-5-map/trace.json'
OUT = WORK / 'run'
spec = importlib.util.spec_from_file_location('level_two_check', ROOT/'scripts/check-level-two-play.py')
play = importlib.util.module_from_spec(spec)
spec.loader.exec_module(play)


def original():
    cache = WORK/'original.json'
    identity = dict(path=str(TRACE.resolve()), sha256=fingerprint(TRACE))
    if cache.exists() and cache.stat().st_mtime >= stored_path(TRACE).stat().st_mtime:
        data = json.loads(cache.read_text())
        if data.get('reference') == identity:
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
        elif kind == 'value' and key in {'status', 'startup_profile', 'parent_checkpoint', 'played_ms'}:
            data[key] = value
    if data['status'] != 'pass':
        raise ValueError('Original Level 5 trace is not passing')
    presentations = iter(p for p in data.pop('presentations') if p['phase'].startswith('level-5-'))
    data['screens'] = [[[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
                        for p in (next(presentations) for _ in range(c['presentations']))]
                       for c in data.pop('frame_cycles') if c['phase'].startswith('level-5-')]
    data['posted'] = posted
    data['reference'] = identity
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def main():
    global WORK, TRACE, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--section', choices=['death'])
    parser.add_argument('--reference', type=Path, help='Explicit staged original trace')
    parser.add_argument('--evidence-dir', type=Path, help='Isolated comparison directory (required with --reference)')
    args = parser.parse_args()
    if args.section:
        WORK = ROOT / 'work/level-five-death'
        TRACE = WORK / 'trace.json'
        OUT = WORK / 'run'
    if bool(args.reference) != bool(args.evidence_dir):
        parser.error('--reference and --evidence-dir must be used together')
    if args.reference:
        TRACE = args.reference.resolve()
        WORK = args.evidence_dir.resolve()
        if not WORK.is_relative_to(ROOT/'work'):
            parser.error('--evidence-dir must stay under work/')
        OUT = WORK/'run'
    report = dict(check='level-five' + ('-death' if args.section else ''), status='fail', errors=[])
    errors = report['errors']
    try:
        ref = original()
        report.update(reference=ref['reference'], startup_profile=ref.get('startup_profile'),
                      fresh=not args.reuse, paper=os.environ.get('PAPER') == '1',
                      game_profile='claw-v1.0')
        # Paper Level 2 parents retain the original 12000 ms results Return
        # schedule. Select that physical prefix; keep every delivery comparison.
        returns = [k for k in ref['key_deliveries'] if k['phase'].startswith('results-key-return-')]
        level_two_prefix = (ref.get('startup_profile') == {'paper': True, 'query_ms': 1}
                            and len(returns) >= 2
                            and returns[1]['milliseconds']-returns[0]['milliseconds'] >= 12000)
        report['level_two_prefix'] = level_two_prefix
        if not args.reuse:
            OUT.mkdir(parents=True, exist_ok=True)
            for name in ('app-menu.json', 'live-state.json', 'level-five-route.json'):
                (OUT/name).unlink(missing_ok=True)
            (WORK/'plan.json').write_text(json.dumps(ref['plan']))
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                '--menu-live-check', str(OUT), '--new-game-clock', '--level-five-route', str(WORK/'plan.json')]
                + (['--route-level-two-prefix'] if level_two_prefix else []),
                # The reference executable is v1.0; select its lives and boss
                # rules explicitly rather than the playable app's defaults.
                cwd=ROOT, env=dict(os.environ, CLAW_LIVES_BOSS_PROFILE='claw-v1.0'), check=True, timeout=1000)
        app = json.loads((OUT/'level-five-route.json').read_text())
        if app.get('status') != 'pass':
            errors.append('App route did not pass')
        for label, expected, actual in [('Level 1', ref['play_frames'], app['level_one_frames']),
                                        ('Level 5', ref['frames'], app['level_five_frames'])]:
            difference = play.frames_divergence(expected, actual)
            if difference:
                errors.append(f'{label}: {difference}')
        actual = app['level_five_frames']
        original_events = play.summaries([f['player'] for f in ref['frames']])
        actual_events = play.summaries([f['player'] for f in actual])
        if actual_events != original_events:
            errors.append('Pickup or health transitions differ')
        report.update(frames=len(actual), pickups=actual_events[0], health_changes=actual_events[1])
        if not original_events[0]:
            errors.append('Original route lacks pickups')
        if args.section == 'death':
            for label, events in [('original', original_events), ('app', actual_events)]:
                if not any(e['health'] == 0 for e in events[1]) or not any(e['health'] > 0 for e in events[1]):
                    errors.append(f'{label} route lacks death or respawn')
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
