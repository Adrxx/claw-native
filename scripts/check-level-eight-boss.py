"""Compare Gabriel combat, defeat, MPSCULLY and Level 9 against the original.

--section death checks an unassisted fight through Claw's death and respawn.
References: python -m Tests.NativeLevels.level_eight_boss_trace --plan PLAN
--output TRACE --checkpoint work/level-eight-boss/level-eight-start.pkl
Add --fight-only for the death section. All derived artifacts remain in work/.
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
from Tests.NativeLevels.storage import trace_rows, stored_path
WORK = ROOT/'work/level-eight-boss'
OUT = WORK/'run'
TRACE = None


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


play = load('level_two_play', 'scripts/check-level-two-play.py')
boss = load('level_two_boss', 'scripts/check-level-two-boss.py')


def original():
    path = stored_path(TRACE or WORK/'trace.json')
    identity = [str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size,
                hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    cache = WORK/'original.json'
    if cache.exists():
        data = json.loads(cache.read_text())
        if data['identity'] == identity:
            return data['reference']
    keep = {'status', 'stop', 'plan', 'boss_frames', 'play_frames', 'level_nine_frames',
            'state_transitions', 'key_deliveries', 'presentations', 'boss_route_functions',
            'boss_defeat_health_observed', 'boss_death_callback_observed', 'fight_only',
            'boss_cheat_keys', 'boss_death_callbacks', 'startup_profile', 'parent_checkpoint',
            'startup_queries', 'startup_objects', 'startup_evidence'}
    ref, posted = {}, []
    for key, kind, value in trace_rows(path):
        if key in keep:
            if kind == 'array': ref[key] = []
            elif kind == 'item': ref[key].append(value)
            else: ref[key] = value
        if key == 'physical_events' and kind == 'item' and value.get('service') == 'PostMessageA':
            posted.append(hex(value['wparam']))
    for frame in ref['boss_frames'][1:] + ref['level_nine_frames']:
        frame['screens'] = boss.screens(ref, frame)
    del ref['presentations']
    ref['posted_commands'] = posted
    cache.write_text(json.dumps(dict(identity=identity, reference=ref)))
    return ref


def probe():
    """Reproduce the owner's entry fault; a clean intro is not boss acceptance."""
    out = WORK/'probe-check'
    out.mkdir(parents=True, exist_ok=True)
    plan = out/'plan.json'
    plan.write_text(json.dumps([dict(start_ms=0, end_ms=10000, action='boss-intro',
                                     keys=[], set_x=43054, set_y=5184)]))
    for name in ('app-menu.json', 'level-eight-route.json'):
        (out/name).unlink(missing_ok=True)
    subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(out), '900', '--menu-check', str(out),
        '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
        '--menu-live-check', str(out), '--new-game-clock', '--level-eight-route', str(plan),
        '--level-eight-boss', '--boss-fight-only'], cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
    app = json.loads((out/'app-menu.json').read_text())
    route = out/'level-eight-route.json'
    evidence = json.loads(route.read_text()) if route.exists() else {}
    environment_calls = evidence.get('transports', {}).get('x87-environment', 0)
    active = any(f.get('boss', {}).get('active') for f in evidence.get('level_eight_frames', []))
    clean = app.get('status') == 'pass' and evidence.get('status') == 'pass' and active and environment_calls > 0
    report = dict(check='level-eight-boss-entry', status='diagnostic-pass' if clean else 'fail',
                  accepted=False, error=app.get('error'), completed_frames=app.get('completedFrames'),
                  boss_active=active, x87_environment_calls=environment_calls,
                  trace_tail=app.get('trace', [])[-12:])
    (WORK/'probe-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(not clean)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Only reproduce boss entry; never claims acceptance')
    parser.add_argument('--section', choices=['death'])
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    parser.add_argument('--reference', type=Path, help='Staged original trace; legacy default is unchanged')
    parser.add_argument('--output-dir', type=Path, help='Separate staged comparison evidence and cache')
    args = parser.parse_args()
    global WORK, OUT, TRACE
    if args.probe:
        return probe()
    death = args.section == 'death'
    if death:
        WORK = ROOT/'work/level-eight-death'
        OUT = WORK/'run'
    if args.reference:
        TRACE = args.reference.resolve()
        if not args.output_dir:
            parser.error('--reference requires --output-dir to isolate its derived cache')
    if args.output_dir:
        WORK = args.output_dir.resolve()
        OUT = WORK/'run'
    WORK.mkdir(parents=True, exist_ok=True)
    report = dict(check='level-eight-death' if death else 'level-eight-boss', status='fail', accepted=False, errors=[],
                  reference=str(TRACE or WORK/'trace.json'), fresh=not args.reuse and not args.original_only,
                  paper=os.environ.get('PAPER', '0'))
    errors = report['errors']
    try:
        ref = original()
        report['startup_profile'] = ref.get('startup_profile')
        report['parent_checkpoint'] = ref.get('parent_checkpoint')
        for key in ('startup_queries', 'startup_objects', 'startup_evidence'):
            report[key] = ref.get(key)
        cov = boss.coverage(ref['boss_frames'])
        report['coverage'] = dict(original=cov)
        report['frames'] = dict(original=len(ref['boss_frames']), level_nine=len(ref['level_nine_frames']))
        report['original_boss_functions'] = {address: ref['boss_route_functions'].get(address, 0)
            for address in ('0x443290', '0x44e0c0', '0x491fa0')}
        if ref['status'] != 'pass' or ref['stop'] is not None or ref['fight_only'] != death:
            errors.append('Original full route did not pass')
        if death:
            events = play.summaries([f['player'] for f in ref['boss_frames']])[1]
            report['health_changes'] = events
            if not any(e['health'] == 0 for e in events) or not any(e['health'] > 0 for e in events):
                errors.append('Original route lacks death or respawn')
        else:
            assistance = [a['start_ms'] for a in ref['plan'] if a.get('cheat')]
            before_assistance = [f['player']['health'] for f in ref['boss_frames']
                if not assistance or f['elapsed_ms'] < min(assistance)]
            report['unassisted_health'] = sorted(set(before_assistance), reverse=True)
            if not before_assistance or min(before_assistance) >= before_assistance[0]:
                errors.append('Original lacks player damage before assistance')
            if assistance and [k['letter'] for k in ref.get('boss_cheat_keys', [])] != list('MPKFA'):
                errors.append('Original lacks physical MPKFA assistance deliveries')
            for key in ('boss_active', 'boss_takes_damage', 'boss_defeated', 'boss_attacks'):
                if not cov[key]: errors.append('Original lacks '+key)
            if not ref['boss_defeat_health_observed']:
                errors.append('Original lacks boss_defeat_health_observed')
            # Gabriel's original final death handler creates EndLevelGem; it
            # never calls the shared 0x44e0c0 entry on the Gabriel receiver.
            # That entry's route-wide counts belong to other actors.
            death_functions = {address: ref['boss_route_functions'].get(address, 0)
                               for address in ('0x445720', '0x40e5c0')}
            report['original_gabriel_death_path'] = death_functions
            if death_functions['0x445720'] <= 0:
                errors.append('Original lacks Gabriel final death handler')
            if death_functions['0x40e5c0'] != 1:
                errors.append('Original lacks one EndLevelGem creation')
            for address in ('0x443290', '0x491fa0'):
                if ref['boss_route_functions'].get(address, 0) <= 0:
                    errors.append('Original fight did not execute '+address)
        for side, data in ([] if death else [('original', ref)]):
            completion = [k for k in data['key_deliveries'] if k['phase'].startswith('advance-level-8-cheat-')]
            if [k['key'] for k in completion] != [ord(c) for c in 'MPSCULLY']:
                errors.append(side+' lacks Level 8 MPSCULLY completion')
            if len(data['level_nine_frames']) != 10 or any(f['player']['level'] != 9 for f in data['level_nine_frames']):
                errors.append(side+' lacks ten Level 9 frames')
            progression = iter((s['vtable'], s.get('level')) for s in data['state_transitions'])
            expected = [('0x50c264', 1)]
            for level in range(2, 10): expected.extend([('0x50c0c4', None), ('0x50c264', level)])
            if not all(any(s == wanted for s in progression) for wanted in expected):
                errors.append(side+' lacks complete level/results progression')
        if not args.original_only:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json', 'live-state.json', 'level-eight-route.json'):
                    (OUT/name).unlink(missing_ok=True)
                (WORK/'app-plan.json').write_text(json.dumps(ref['plan']))
                # The 8507-snapshot fight plus the preceding results screens
                # exceeds 9000 app frames. The route quits when it completes.
                subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                    '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '36001',
                    '--menu-live-check', str(OUT), '--new-game-clock', '--level-eight-route', str(WORK/'app-plan.json'),
                    '--level-eight-boss', '--boss-fight-only' if death else '--boss-end-on-defeat'], cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
            app = json.loads((OUT/'level-eight-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App route did not pass')
            boss.compare_frames(ref['play_frames'], app['level_one_frames'], play.FIELDS, 'Level 1', errors)
            boss.compare_frames(ref['boss_frames'], app['level_eight_frames'], play.FIELDS, 'Gabriel', errors)
            boss.compare_frames(ref['level_nine_frames'], app['level_nine_frames'], play.FIELDS, 'Level 9', errors)
            report['coverage']['app'] = boss.coverage(app['level_eight_frames'])
            report['frames'] = dict(original=len(ref['boss_frames']), app=len(app['level_eight_frames']),
                                   level_nine=len(app['level_nine_frames']))
            shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
            if shape(ref['state_transitions']) != shape(app['state_transitions']): errors.append('State transitions differ')
            def keys(rows):
                start = rows[0]['milliseconds']
                return [(k['phase'], k['key'], k['scan'], k['target'], k['vtable'], k['milliseconds']-start) for k in rows]
            if keys(ref['key_deliveries']) != keys(app['key_deliveries']): errors.append('Physical key deliveries differ')
            tail = lambda rows: rows[rows.index('0x800e'):] if '0x800e' in rows else []
            if tail(ref['posted_commands']) != tail(app['posted_commands']): errors.append('Posted commands differ')
            report['boss_base_direct'] = app['transports'].get('boss-base-direct', 0)
            report['x87_environment_calls'] = app['transports'].get('x87-environment', 0)
            if not report['x87_environment_calls']: errors.append('App did not transport the constructor x87 environment')
            if not death:
                report['app_gabriel_death_path'] = {address: app.get('boss_route_functions', {}).get(address, 0)
                    for address in ('0x445720', '0x40e5c0')}
                if report['app_gabriel_death_path'] != report['original_gabriel_death_path']:
                    errors.append('Gabriel final death handler or EndLevelGem creation differs')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        errors.append(str(error))
        try:
            app = json.loads((OUT/'app-menu.json').read_text())
            report['app_error'] = app.get('error')
            report['trace_tail'] = app.get('trace', [])[-12:]
        except (OSError, ValueError):
            pass
    report['status'] = 'fail' if errors else 'pass'
    report['accepted'] = not errors and not args.original_only
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK/('original-result.json' if args.original_only else 'result.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
