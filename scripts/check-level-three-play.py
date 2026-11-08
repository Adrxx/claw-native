"""Compare the Mac app's Level 3 route with the retained original trace.

The route uses MPSCULLY from Levels 1 and 2 and the original's 1000 ms
results Return schedule. Every player frame and presented pixel/palette hash
is compared. --reuse only compares existing app evidence.
--section rope uses the 45-second physical-key route in work/level-three-rope,
requiring original rope updates, app rope jump-offs, death and respawn.
Regenerate that reference with work/level-three-rope/trace.py --level 3
--plan work/level-three-rope/plan.json --play-ms 45000
--output work/level-three-rope/trace.json (all original artifacts remain local).
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
from Tests.NativeLevels.storage import stored_path, trace_rows

WORK = ROOT / 'work/level-three-play'
TRACE = ROOT / 'work/level-3-map/trace.json'
OUT = WORK / 'run'
spec = importlib.util.spec_from_file_location('level_two_check', ROOT/'scripts/check-level-two-play.py')
play = importlib.util.module_from_spec(spec)
spec.loader.exec_module(play)


def original():
    cache = WORK/'original.json'
    source = stored_path(TRACE)
    identity = dict(path=str(source.resolve()), bytes=source.stat().st_size,
                    modified_ns=source.stat().st_mtime_ns)
    if cache.exists():
        cached = json.loads(cache.read_text())
        if cached.get('reference_source') == identity:
            return cached
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
        elif kind == 'value' and key == 'status':
            data[key] = value
    if data['status'] != 'pass':
        raise ValueError('Original Level 3 trace is not passing')
    presentations = iter(p for p in data.pop('presentations') if p['phase'].startswith('level-3-'))
    data['screens'] = [[[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
                        for p in (next(presentations) for _ in range(c['presentations']))]
                       for c in data.pop('frame_cycles') if c['phase'].startswith('level-3-')]
    data['posted'] = posted
    data['reference_source'] = identity
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--section', choices=['rope'])
    parser.add_argument('--reference', type=Path, help='Explicit staged original trace; keeps the default reference unchanged')
    parser.add_argument('--work-dir', type=Path, help='Separate compact cache, plan and fresh app evidence directory')
    args = parser.parse_args()
    global WORK, OUT, TRACE
    if args.section:
        WORK = ROOT / 'work/level-three-rope'
        TRACE = WORK / 'trace.json'
        OUT = WORK / 'run'
    if args.reference:
        TRACE = args.reference.resolve()
        if not args.work_dir:
            parser.error('--reference requires --work-dir to isolate staged evidence')
    if args.work_dir:
        WORK = args.work_dir.resolve()
        OUT = WORK / 'run'
    report = dict(check='level-three' + ('-rope' if args.section else ''), status='fail', errors=[])
    report.update(reference=str(TRACE), fresh=not args.reuse,
                  paper_startup=os.environ.get('PAPER') == '1', config=os.environ.get('CLAW_CONFIG', 'Release'),
                  reference_game_profile='claw-v1.0')
    errors = report['errors']
    try:
        ref = original()
        if not args.reuse:
            OUT.mkdir(parents=True, exist_ok=True)
            for name in ('app-menu.json', 'live-state.json', 'level-three-route.json'):
                (OUT/name).unlink(missing_ok=True)
            (WORK/'plan.json').write_text(json.dumps(ref['plan']))
            # These original recordings use v1.0 rules, including the HUD lives count.
            subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                '--menu-live-check', str(OUT), '--new-game-clock', '--level-three-route', str(WORK/'plan.json')],
                cwd=ROOT, env=dict(os.environ, CLAW_LIVES_BOSS_PROFILE='claw-v1.0'), check=True, timeout=1000)
        app = json.loads((OUT/'level-three-route.json').read_text())
        if app.get('status') != 'pass':
            errors.append('App route did not pass')
        for label, expected, actual in [('Level 1', ref['play_frames'], app['level_one_frames']),
                                        ('Level 3', ref['frames'], app['level_three_frames'])]:
            difference = play.frames_divergence(expected, actual)
            if difference:
                errors.append(f'{label}: {difference}')
        actual = app['level_three_frames']
        original_events = play.summaries([f['player'] for f in ref['frames']])
        actual_events = play.summaries([f['player'] for f in actual])
        if actual_events != original_events:
            errors.append('Pickup or health transitions differ')
        report.update(frames=len(actual), pickups=actual_events[0], health_changes=actual_events[1])
        if args.section == 'rope':
            for label, events in [('original', original_events), ('app', actual_events)]:
                if not any(e['health'] == 0 for e in events[1]) or not any(e['health'] > 0 for e in events[1]):
                    errors.append(f'{label} rope route lacks death or respawn')
            original_rope = next((f['count'] for f in ref.get('game_functions', []) if f['address'] == '0x4181c0'), 0)
            report['original_rope_updates'] = original_rope
            if not original_rope:
                errors.append('Original route never executed the rope state')
            report['rope_jump_calls'] = app.get('transports', {}).get('rope-jump-x87', 0)
            if report['rope_jump_calls'] <= 0:
                errors.append('App did not jump off the rope through the reviewed x87 call')
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
        # Both routes share this original 6200 ms prefix. Check the speech
        # controller as well as pixels: an off-screen speaker also owns the
        # global speech lock and can suppress the next visible voice.
        speech_ref = json.loads((ROOT/'work/level-three-rope/speech-original.json').read_text())
        def speech(row):
            value = row['player']['speech']
            keys = ['voice', 'state', 'duration', 'flags', 'x', 'y']
            if value['state'] == 15:
                keys.append('remaining')
            return {key: value[key] for key in keys}
        speech_matches = sum(speech(a) == speech(b) for a, b in zip(actual, speech_ref))
        report['speech_frames'] = dict(original=len(speech_ref), matched=speech_matches)
        if speech_matches != len(speech_ref):
            errors.append('Enemy speech selection or marker timing differs from the original prefix')
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
