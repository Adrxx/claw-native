"""Compare original Omar combat, defeat, MPSCULLY and Level 14.

--probe compares a diagnostic fight without claiming boss or level acceptance.
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
from Tests.NativeLevels.storage import trace_rows, fingerprint, stored_path
WORK = ROOT/'work/level-fourteen-boss'
OUT = WORK/'run'
REFERENCE = None


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


play = load('level_two_play', 'scripts/check-level-two-play.py')
boss = load('level_two_boss', 'scripts/check-level-two-boss.py')


def combat_phases(functions, label, errors, frames):
    # Shield depletion resets Omar to 100 health. A transient zero at that
    # boundary is not his defeat: require the vulnerable and death owners too.
    for address, minimum in [('0x464360', 4), ('0x4642b0', 1),
                             ('0x464a60', 2), ('0x464b90', 1), ('0x40e5c0', 1)]:
        # The original observer's function census predates Omar's entries;
        # its frame observations and the explicit death hook cover his phases.
        if label == 'Original' and address != '0x40e5c0': continue
        if functions.get(address, 0) < minimum:
            errors.append(f'{label} lacks combat phase {address}')
    health = []
    for frame in frames:
        value = frame['boss'].get('health')
        if value is not None and (not health or health[-1] != value): health.append(value)
    if health[:5] != [100, 75, 50, 25, 100] or health[-1:] != [0]:
        errors.append(f'{label} lacks shield depletion, vulnerable reset and final defeat')


def original(probe):
    path = stored_path(REFERENCE or WORK/('probe-trace.json' if probe else 'trace.json'))
    identity = [str(path.resolve()), fingerprint(path), hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    cache = WORK/('probe-original.json' if probe else 'original.json')
    if cache.exists():
        data = json.loads(cache.read_text())
        if data['identity'] == identity: return data['reference']
    keep = {'status', 'stop', 'plan', 'boss_frames', 'next_frames', 'play_frames', 'state_transitions',
            'key_deliveries', 'presentations', 'boss_route_functions', 'fight_only', 'boss_cheat_keys',
            'tracer_sha256', 'observer_checkpoint', 'adapter_inputs', 'boss_death_callbacks',
            'startup_profile', 'startup_queries', 'startup_objects', 'parent_checkpoint'}
    ref, posted, credits, backgrounds = {}, [], [], []
    for key, kind, value in trace_rows(path):
        if key in keep:
            if kind == 'array': ref[key] = []
            elif kind == 'item': ref[key].append(value)
            else: ref[key] = value
        if key == 'physical_events' and kind == 'item' and value.get('service') == 'PostMessageA':
            posted.append(hex(value['wparam']))
        if key == 'physical_events' and kind == 'item':
            service = value.get('service')
            if service == 'BackgroundMovie::Frame':
                backgrounds.append({k:value[k] for k in ('movie','frame','playing')})
            if service in ('CGdiObject::Attach', 'CGdiObject::DeleteObject'):
                credits.append(dict(service=service))
            elif service == 'CreateRectRgn':
                credits.append(dict(service=service, rectangle=value['rectangle']))
            elif service == 'SelectClipRgn':
                credits.append(dict(service=service, selected=bool(value['region'])))
            elif service == 'DrawTextA' and value.get('flags') in (0x450, 0x50):
                credits.append(dict(service=service, flags=value['flags'], lines=value['lines'], height=value['height'],
                    rectangle=value['calculated_rectangle'] if value.get('calculated') else value['rectangle']))
    for frame in ref['boss_frames'][1:]+ref['next_frames']: frame['screens'] = boss.screens(ref, frame)
    last = ref['boss_frames'][-1]
    end = last.get('presentation_start', 0)+last.get('presentation_count', 0)
    ref['ending_screens'] = [[p['pixels_sha256'][:16],p['palette_sha256'][:16]] for p in ref['presentations'][end:]]
    del ref['presentations']
    ref['posted_commands'] = posted
    ref['credits_services'] = credits
    ref['background_frames'] = backgrounds
    cache.write_text(json.dumps(dict(identity=identity, reference=ref)))
    return ref


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    global WORK, OUT
    if args.reference:
        global REFERENCE
        REFERENCE = args.reference.resolve()
    if args.evidence:
        WORK = args.evidence.resolve()
        OUT = WORK/'run'
    WORK.mkdir(parents=True, exist_ok=True)
    report = dict(check='level-fourteen-boss', status='fail', accepted=False, errors=[])
    errors = report['errors']
    try:
        ref = original(args.probe)
        if os.environ.get('PAPER') == '1':
            queries = ref.get('startup_queries', {})
            objects = ref.get('startup_objects') or {}
            if (ref.get('startup_profile') != dict(paper=True, query_ms=1)
                    or not queries.get('count')
                    or queries.get('increments') != {'1': queries['count']}
                    or any(objects.get(k, '0x0') == '0x0' for k in ('0x44','0x58'))):
                errors.append('Reference lacks original paper startup and 1 ms queries')
        checkpoint = ref['observer_checkpoint']
        if checkpoint['sha256'] != fingerprint(ROOT/checkpoint['path']): errors.append('Original checkpoint changed')
        for name, digest in checkpoint['inputs_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: errors.append('Original input changed: '+name)
        for name, digest in ref['adapter_inputs'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: errors.append('Original adapter changed: '+name)
        if ref['tracer_sha256'] != hashlib.sha256((ROOT/'Tests/NativeLevels/level_fourteen_boss_trace.py').read_bytes()).hexdigest():
            errors.append('Original boss tracer changed')
        if ref['status'] != 'pass' or ref['stop'] is not None: errors.append('Original fight did not pass')
        report['coverage'] = dict(original=boss.coverage(ref['boss_frames']))
        if not args.probe:
            if ref['plan'] != json.loads((ROOT/'Tests/NativeLevels/level_fourteen_boss_plan.json').read_text()):
                errors.append('Original differs from the retained Omar acceptance plan')
            if ref['fight_only']: errors.append('Original lacks completion')
            combat_phases(ref['boss_route_functions'], 'Original', errors, ref['boss_frames'])
            for key in ('boss_active','boss_takes_damage','boss_defeated','boss_attacks','player_damage'):
                if not report['coverage']['original'][key]: errors.append('Original lacks '+key)
            assistance = [a for a in ref['plan'] if a.get('cheat')]
            delivered = [k['key'] for k in ref['key_deliveries'] if k['phase'].startswith('boss-cheat-')]
            if len(assistance) != 1 or delivered != list(map(ord, 'MPKFA')):
                errors.append('Original lacks exactly one delivered MPKFA assistance sequence')
            elif not any(f['player']['health'] < ref['boss_frames'][0]['player']['health']
                         for f in ref['boss_frames'] if f['elapsed_ms'] <= assistance[0]['start_ms']):
                errors.append('Original lacks unassisted damage before MPKFA')
            callbacks = ref['boss_death_callbacks']
            receivers = {f['boss'].get('private') for f in ref['boss_frames']}
            if not callbacks or any(c['address'] != '0x40e5c0' or c['receiver'] not in receivers or boss.signed(c['health']) > 0 for c in callbacks):
                errors.append('Original lacks Omar-specific completed death callback')
            report['death_callbacks'] = callbacks
            complete = [k['key'] for k in ref['key_deliveries'] if k['phase'].startswith('advance-level-14-cheat-')]
            if complete != list(map(ord,'MPSCULLY')): errors.append('Original lacks Level 14 MPSCULLY')
            if not ref['state_transitions'] or ref['state_transitions'][-1]['vtable'] != '0x50c1e4':
                errors.append('Original ending did not return to menu')
        # An incomplete reference cannot establish parity; do not launch an app
        # (or compare stale evidence) until the original itself meets the contract.
        if not args.original_only and not errors:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json','live-state.json','level-fourteen-route.json',
                             'movie-state.json','movie-check.json'): (OUT/name).unlink(missing_ok=True)
                (WORK/'app-plan.json').write_text(json.dumps(ref['plan']))
                subprocess.run([str(ROOT/'work/new-game/launch.sh'),str(OUT),'900','--menu-check',str(OUT),
                    '--menu-input-script',str(ROOT/'work/new-game/play-events.json'),'--menu-frames','16000',
                    '--menu-live-check',str(OUT),'--new-game-clock','--level-fourteen-route',str(WORK/'app-plan.json'),
                    '--level-fourteen-boss']+(['--boss-fight-only'] if args.probe else ['--movie-flow-check',str(OUT)]),
                    cwd=ROOT, env=dict(os.environ),check=True,timeout=1000)
            app = json.loads((OUT/'level-fourteen-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App fight did not pass')
            for expected, actual, label in [('play_frames','level_one_frames','Level 1'),
                ('boss_frames','level_fourteen_frames','Omar')]:
                boss.compare_frames(ref[expected], app[actual], play.FIELDS, label, errors)
            shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
            if shape(ref['state_transitions']) != shape(app['state_transitions']): errors.append('State transitions differ')
            def keys(rows):
                start = rows[0]['milliseconds']
                return [(k['phase'],k['key'],k['scan'],k['target'],k['vtable'],k['milliseconds']-start) for k in rows]
            if keys(ref['key_deliveries']) != keys(app['key_deliveries']): errors.append('Key deliveries differ')
            tail = lambda rows: rows[rows.index('0x800e'):] if '0x800e' in rows else []
            if tail(ref['posted_commands']) != tail(app['posted_commands']): errors.append('Posted commands differ')
            def identities(states):
                objects = [s['object'] for s in states]
                return [objects.index(obj) for obj in objects]
            if identities(ref['state_transitions']) != identities(app['state_transitions']): errors.append('State object reuse differs')
            report['frames'] = dict(original=len(ref['boss_frames']),app=len(app['level_fourteen_frames']))
            report['coverage']['app'] = boss.coverage(app['level_fourteen_frames'])
            if not args.probe:
                combat_phases(app.get('boss_route_functions', {}), 'App', errors, app['level_fourteen_frames'])
                if ref['ending_screens'] != app.get('ending_screens'):
                    errors.append('Ending presentations differ')
                if not ref['credits_services'] or ref['credits_services'] != app.get('credits_services'):
                    errors.append('Credits region lifetime, clipping or text measurement differs')
                services = [e['service'] for e in app.get('credits_services', [])]
                if any(name not in services for name in ('CreateRectRgn', 'CGdiObject::Attach', 'DrawTextA', 'CGdiObject::DeleteObject')):
                    errors.append('Credits lack the required physical service coverage')
                if sum(e.get('flags') == 0x50 for e in app.get('credits_services', [])) < 2:
                    errors.append('Credits lack scrolling text presentations')
                report['credits'] = dict(presentations=len(ref['ending_screens']), services=len(services))
                backgrounds = [{k:e[k] for k in ('movie','frame','playing')} for e in app.get('movie_events', []) if e.get('call') == 'background-frame']
                if not ref['background_frames'] or ref['background_frames'] != backgrounds:
                    errors.append('Credits background frame cadence or loop completion differs')
                if len({e['frame'] for e in backgrounds}) < 2:
                    errors.append('Credits background decoder did not advance')
                report['credits']['background_frames'] = len(backgrounds)
                if app.get('boss_route_functions', {}).get('0x40e5c0', 0) == 0:
                    errors.append('App lacks completed boss death callback')
                ending_plays = [e for e in app.get('movie_events', []) if e.get('call') == 'play' and e.get('movie') == 10]
                if not ending_plays or ending_plays[-1].get('result') != 0x11111111:
                    errors.append('Ending movie did not finish')
                movie = json.loads((OUT/'movie-state.json').read_text())
                finished = [m for m in movie.get('records', []) if m.get('movie') == 10 and m.get('outcome') == 'finished'
                            and m.get('result') == 0x11111111 and m.get('media_seconds', 0) > 1
                            and m.get('seconds', 0) >= m['media_seconds']-1]
                if movie.get('playing') is not False or movie.get('error') or not finished:
                    errors.append('Ending movie lacks natural AVFoundation completion')
                report['movies'] = finished
            if not args.probe and len({f['player']['lives_lost'] for f in app['level_fourteen_frames']}) != 1:
                errors.append('App fight includes a player death/reset')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        errors.append(str(error))
        try:
            app = json.loads((OUT/'app-menu.json').read_text()); report['app_error'] = app.get('error'); report['trace_tail'] = app.get('trace',[])[-12:]
        except (OSError, ValueError): pass
    report['status'] = 'fail' if errors else 'pass'
    report['accepted'] = not errors and not args.probe and not args.original_only
    WORK.mkdir(parents=True,exist_ok=True)
    (WORK/('probe-result.json' if args.probe else 'original-result.json' if args.original_only else 'result.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps(report)); return int(bool(errors))


if __name__ == '__main__': raise SystemExit(main())
