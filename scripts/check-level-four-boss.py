"""Compare Katherine combat, defeat, MPSCULLY and Level 5 against the original.

--section death checks an unassisted fight through Claw's death and respawn.
References: python -m Tests.NativeLevels.level_four_boss_trace --plan PLAN
--output TRACE --checkpoint work/level-four-boss/level-four-start.pkl
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
WORK = ROOT/'work/level-four-boss'
OUT = WORK/'run'
TRACE = WORK/'trace.json'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


play = load('level_two_play', 'scripts/check-level-two-play.py')
boss = load('level_two_boss', 'scripts/check-level-two-boss.py')


def original():
    path = stored_path(TRACE)
    identity = [str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size,
                hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    cache = WORK/'original.json'
    if cache.exists():
        data = json.loads(cache.read_text())
        if data['identity'] == identity:
            return data['reference']
    keep = {'status', 'stop', 'plan', 'boss_frames', 'play_frames', 'level_five_frames',
            'state_transitions', 'key_deliveries', 'presentations', 'boss_route_functions',
            'boss_defeat_health_observed', 'boss_death_callback_observed', 'fight_only',
            'startup_profile', 'startup_queries', 'startup_objects', 'parent_checkpoint'}
    ref, posted = {}, []
    for key, kind, value in trace_rows(path):
        if key in keep:
            if kind == 'array': ref[key] = []
            elif kind == 'item': ref[key].append(value)
            else: ref[key] = value
        if key == 'physical_events' and kind == 'item' and value.get('service') == 'PostMessageA':
            posted.append(hex(value['wparam']))
    for frame in ref['boss_frames'][1:] + ref['level_five_frames']:
        frame['screens'] = boss.screens(ref, frame)
    del ref['presentations']
    ref['posted_commands'] = posted
    cache.write_text(json.dumps(dict(identity=identity, reference=ref)))
    return ref


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section', choices=['death'])
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    parser.add_argument('--reference', type=Path, help='Staged original trace')
    parser.add_argument('--evidence', type=Path, help='Separate staged comparison directory under work/')
    args = parser.parse_args()
    global WORK, OUT, TRACE
    death = args.section == 'death'
    if death:
        WORK = ROOT/'work/level-four-death'
        OUT = WORK/'run'
    TRACE = args.reference.resolve() if args.reference else WORK/'trace.json'
    if args.evidence:
        WORK = args.evidence.resolve()
        if not WORK.is_relative_to(ROOT/'work'):
            parser.error('--evidence must stay under work/')
        OUT = WORK/'run'
    WORK.mkdir(parents=True, exist_ok=True)
    report = dict(check='level-four-death' if death else 'level-four-boss', status='fail', accepted=False, errors=[],
                  reference=str(TRACE), evidence=str(OUT), fresh=not args.reuse,
                  paper=os.environ.get('PAPER', '0') == '1')
    errors = report['errors']
    try:
        ref = original()
        report['startup_profile'] = ref.get('startup_profile')
        with stored_path(TRACE).open('rb') as stream:
            report['reference_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if report['paper']:
            queries = ref.get('startup_queries', {})
            objects = ref.get('startup_objects') or {}
            if (ref.get('startup_profile') != {'paper': True, 'query_ms': 1}
                    or not queries.get('count')
                    or queries.get('increments') != {'1': queries['count']}
                    or any(objects.get(hex(o), '0x0') == '0x0' for o in (0x44, 0x58))):
                errors.append('Original lacks paper startup objects and 1 ms initialization queries')
        cov = boss.coverage(ref['boss_frames'])
        report['coverage'] = dict(original=cov)
        report['frames'] = dict(original=len(ref['boss_frames']), level_five=len(ref['level_five_frames']))
        report['original_boss_functions'] = {address: ref['boss_route_functions'].get(address, 0)
            for address in ('0x40e660', '0x44e0c0', '0x491fa0')}
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
            for address in ('0x40e660', '0x44e0c0', '0x491fa0'):
                if ref['boss_route_functions'].get(address, 0) <= 0:
                    errors.append('Original fight did not execute '+address)
        for side, data in ([] if death else [('original', ref)]):
            completion = [k for k in data['key_deliveries'] if k['phase'].startswith('advance-level-4-cheat-')]
            if [k['key'] for k in completion] != [ord(c) for c in 'MPSCULLY']:
                errors.append(side+' lacks Level 4 MPSCULLY completion')
            if len(data['level_five_frames']) != 10 or any(f['player']['level'] != 5 for f in data['level_five_frames']):
                errors.append(side+' lacks ten Level 5 frames')
            progression = iter((s['vtable'], s.get('level')) for s in data['state_transitions'])
            expected = [('0x50c264', 1)]
            for level in range(2, 6): expected.extend([('0x50c0c4', None), ('0x50c264', level)])
            if not all(any(s == wanted for s in progression) for wanted in expected):
                errors.append(side+' lacks complete level/results progression')
        if not args.original_only:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json', 'live-state.json', 'level-four-route.json'):
                    (OUT/name).unlink(missing_ok=True)
                (WORK/'app-plan.json').write_text(json.dumps(ref['plan']))
                subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                    '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                    '--menu-live-check', str(OUT), '--new-game-clock', '--level-four-route', str(WORK/'app-plan.json'),
                    '--level-four-boss', '--boss-fight-only' if death else '--boss-end-on-defeat'], cwd=ROOT, env=dict(os.environ), check=True, timeout=1000)
            app = json.loads((OUT/'level-four-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App route did not pass')
            boss.compare_frames(ref['play_frames'], app['level_one_frames'], play.FIELDS, 'Level 1', errors)
            boss.compare_frames(ref['boss_frames'], app['level_four_frames'], play.FIELDS, 'Katherine', errors)
            boss.compare_frames(ref['level_five_frames'], app['level_five_frames'], play.FIELDS, 'Level 5', errors)
            report['coverage']['app'] = boss.coverage(app['level_four_frames'])
            report['frames'] = dict(original=len(ref['boss_frames']), app=len(app['level_four_frames']),
                                   level_five=len(app['level_five_frames']))
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
    report['status'] = 'fail' if errors else 'pass'
    report['accepted'] = not errors and not args.original_only
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK/('original-result.json' if args.original_only else 'result.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
