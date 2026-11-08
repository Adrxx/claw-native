"""Compare Wolvington combat, defeat, MPSCULLY and Level 7 against the original.

--section death checks an unassisted fight through Claw's death and respawn.
References: python -m Tests.NativeLevels.level_six_boss_trace --plan PLAN
--output TRACE --checkpoint work/level-six-boss/level-six-start.pkl
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
WORK = ROOT/'work/level-six-boss'
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
        if data.get('identity') == identity:
            return data['reference']
    keep = {'status', 'stop', 'plan', 'boss_frames', 'play_frames', 'level_seven_frames',
            'state_transitions', 'key_deliveries', 'presentations', 'boss_route_functions',
            'boss_defeat_health_observed', 'boss_death_callback_observed', 'fight_only', 'startup_profile'}
    ref, posted = {}, []
    for key, kind, value in trace_rows(path):
        if key in keep:
            if kind == 'array': ref[key] = []
            elif kind == 'item': ref[key].append(value)
            else: ref[key] = value
        if key == 'physical_events' and kind == 'item' and value.get('service') == 'PostMessageA':
            posted.append(hex(value['wparam']))
    for frame in ref['boss_frames'][1:] + ref['level_seven_frames']:
        frame['screens'] = boss.screens(ref, frame)
    del ref['presentations']
    ref['posted_commands'] = posted
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(identity=identity, reference=ref)))
    return ref


def probe():
    """Reproduce the owner's entry fault; a clean intro is not boss acceptance."""
    out = WORK/'probe-check'
    out.mkdir(parents=True, exist_ok=True)
    plan = out/'plan.json'
    plan.write_text(json.dumps([dict(start_ms=0, end_ms=10000, action='boss-intro',
                                     keys=[], set_x=34645, set_y=4476)]))
    for name in ('app-menu.json', 'level-six-route.json'):
        (out/name).unlink(missing_ok=True)
    subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(out), '900', '--menu-check', str(out),
        '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
        '--menu-live-check', str(out), '--new-game-clock', '--level-six-route', str(plan),
        '--level-six-boss', '--boss-fight-only'], cwd=ROOT, env=dict(os.environ, CLAW_LIVES_BOSS_PROFILE='claw-v1.0'), check=True, timeout=1000)
    app = json.loads((out/'app-menu.json').read_text())
    route = out/'level-six-route.json'
    clean = app.get('status') == 'pass' and route.exists()
    report = dict(check='level-six-boss-entry', status='diagnostic-pass' if clean else 'fail',
                  accepted=False, error=app.get('error'), completed_frames=app.get('completedFrames'),
                  trace_tail=app.get('trace', [])[-12:])
    (WORK/'probe-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(not clean)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Diagnose boss entry without claiming acceptance')
    parser.add_argument('--section', choices=['death'])
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    parser.add_argument('--reference', type=Path, help='Explicit staged original trace')
    parser.add_argument('--evidence-dir', type=Path, help='Isolated cache, run and result directory')
    args = parser.parse_args()
    global WORK, OUT, TRACE
    if args.probe:
        return probe()
    death = args.section == 'death'
    if death:
        WORK = ROOT/'work/level-six-death'
        OUT = WORK/'run'
    if args.reference:
        TRACE = args.reference.resolve()
    elif args.evidence_dir:
        TRACE = WORK/'trace.json'
    if args.evidence_dir:
        WORK = args.evidence_dir.resolve()
        if not WORK.is_relative_to(ROOT/'work'):
            parser.error('Evidence must stay under work/')
        OUT = WORK/'run'
    report = dict(check='level-six-death' if death else 'level-six-boss', status='fail', accepted=False, errors=[],
                  reference=str(TRACE or WORK/'trace.json'), reused=args.reuse,
                  paper=os.environ.get('PAPER') == '1', game_profile='claw-v1.0')
    errors = report['errors']
    try:
        ref = original()
        report['original_startup_profile'] = ref.get('startup_profile')
        if report['paper'] and ref.get('startup_profile') != {'paper': True, 'query_ms': 1}:
            raise ValueError('PAPER=1 requires an original recorded with paper startup and 1 ms queries')
        cov = boss.coverage(ref['boss_frames'])
        report['coverage'] = dict(original=cov)
        report['frames'] = dict(original=len(ref['boss_frames']), level_seven=len(ref['level_seven_frames']))
        report['original_boss_functions'] = {address: ref['boss_route_functions'].get(address, 0)
            for address in ('0x49fb30', '0x44e0c0', '0x491fa0')}
        if ref['status'] != 'pass' or ref['stop'] is not None or ref['fight_only'] != death:
            errors.append('Original full route did not pass')
        if death:
            events = play.summaries([f['player'] for f in ref['boss_frames']])[1]
            report['health_changes'] = events
            if not any(e['health'] == 0 for e in events) or not any(e['health'] > 0 for e in events):
                errors.append('Original route lacks death or respawn')
        else:
            for key in ('boss_active', 'boss_takes_damage', 'boss_defeated', 'boss_attacks'):
                if not cov[key]: errors.append('Original lacks '+key)
            for key in ('boss_defeat_health_observed', 'boss_death_callback_observed'):
                if not ref[key]: errors.append('Original lacks '+key)
            for address in ('0x49fb30', '0x44e0c0', '0x491fa0'):
                if ref['boss_route_functions'].get(address, 0) <= 0:
                    errors.append('Original fight did not execute '+address)
        for side, data in ([] if death else [('original', ref)]):
            completion = [k for k in data['key_deliveries'] if k['phase'].startswith('advance-level-6-cheat-')]
            if [k['key'] for k in completion] != [ord(c) for c in 'MPSCULLY']:
                errors.append(side+' lacks Level 6 MPSCULLY completion')
            if len(data['level_seven_frames']) != 10 or any(f['player']['level'] != 7 for f in data['level_seven_frames']):
                errors.append(side+' lacks ten Level 7 frames')
            progression = iter((s['vtable'], s.get('level')) for s in data['state_transitions'])
            expected = [('0x50c264', 1)]
            for level in range(2, 8): expected.extend([('0x50c0c4', None), ('0x50c264', level)])
            if not all(any(s == wanted for s in progression) for wanted in expected):
                errors.append(side+' lacks complete level/results progression')
        if not args.original_only:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json', 'live-state.json', 'level-six-route.json'):
                    (OUT/name).unlink(missing_ok=True)
                (WORK/'app-plan.json').write_text(json.dumps(ref['plan']))
                subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                    '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                    '--menu-live-check', str(OUT), '--new-game-clock', '--level-six-route', str(WORK/'app-plan.json'),
                    '--level-six-boss', '--boss-fight-only' if death else '--boss-end-on-defeat'], cwd=ROOT, env=dict(os.environ, CLAW_LIVES_BOSS_PROFILE='claw-v1.0'), check=True, timeout=1000)
            app = json.loads((OUT/'level-six-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App route did not pass')
            boss.compare_frames(ref['play_frames'], app['level_one_frames'], play.FIELDS, 'Level 1', errors)
            boss.compare_frames(ref['boss_frames'], app['level_six_frames'], play.FIELDS, 'Wolvington', errors)
            boss.compare_frames(ref['level_seven_frames'], app['level_seven_frames'], play.FIELDS, 'Level 7', errors)
            report['presented_frames'] = {}
            for label, expected, actual in (
                    ('Wolvington', ref['boss_frames'][1:], app['level_six_frames'][1:]),
                    ('Level 7', ref['level_seven_frames'], app['level_seven_frames'])):
                matched = sum(a['screens'] == b.get('screens') for a, b in zip(expected, actual))
                report['presented_frames'][label] = dict(original=len(expected), app=len(actual), matched=matched)
                if len(expected) != len(actual) or matched != len(expected):
                    errors.append(label+' presented pixels or palettes differ')
            report['coverage']['app'] = boss.coverage(app['level_six_frames'])
            report['frames'] = dict(original=len(ref['boss_frames']), app=len(app['level_six_frames']),
                                   level_seven=len(app['level_seven_frames']))
            shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
            if shape(ref['state_transitions']) != shape(app['state_transitions']): errors.append('State transitions differ')
            def keys(rows):
                start = rows[0]['milliseconds']
                return [(k['phase'], k['key'], k['scan'], k['target'], k['vtable'], k['milliseconds']-start) for k in rows]
            if keys(ref['key_deliveries']) != keys(app['key_deliveries']): errors.append('Physical key deliveries differ')
            tail = lambda rows: rows[rows.index('0x800e'):] if '0x800e' in rows else []
            if tail(ref['posted_commands']) != tail(app['posted_commands']): errors.append('Posted commands differ')
            report['boss_base_direct'] = app['transports'].get('boss-base-direct', 0)
            if not death and not report['boss_base_direct']: errors.append('App did not exercise boss base death call')
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
