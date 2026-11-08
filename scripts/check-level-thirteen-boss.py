"""Compare original Red Tail combat, defeat, MPSCULLY and Level 14.

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
WORK = Path(os.environ.get('CLAW_LEVEL_THIRTEEN_BOSS_WORK', ROOT/'work/level-thirteen-boss'))
REFERENCE = Path(os.environ.get('CLAW_LEVEL_THIRTEEN_BOSS_REFERENCE', WORK/'trace.json'))
OUT = WORK/'run'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


play = load('level_two_play', 'scripts/check-level-two-play.py')
boss = load('level_two_boss', 'scripts/check-level-two-boss.py')


def original(probe):
    path = stored_path(WORK/'probe-trace.json' if probe else REFERENCE)
    identity = [str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    cache = WORK/('probe-original.json' if probe else 'original.json')
    if cache.exists():
        data = json.loads(cache.read_text())
        if data['identity'] == identity: return data['reference']
    keep = {'status', 'stop', 'plan', 'boss_frames', 'next_frames', 'play_frames', 'state_transitions',
            'key_deliveries', 'presentations', 'boss_route_functions', 'fight_only', 'boss_cheat_keys',
            'tracer_sha256', 'observer_checkpoint', 'adapter_inputs', 'boss_death_callbacks',
            'startup_paper', 'clock_query_ms', 'startup_queries', 'startup_objects', 'startup_context', 'startup_profile', 'parent_checkpoint', 'independent_prefix'}
    ref, posted = {}, []
    for key, kind, value in trace_rows(path):
        if key in keep:
            if kind == 'array': ref[key] = []
            elif kind == 'item': ref[key].append(value)
            else: ref[key] = value
        if key == 'physical_events' and kind == 'item' and value.get('service') == 'PostMessageA':
            posted.append(hex(value['wparam']))
    for frame in ref['boss_frames'][1:]+ref['next_frames']: frame['screens'] = boss.screens(ref, frame)
    del ref['presentations']
    ref['posted_commands'] = posted
    cache.write_text(json.dumps(dict(identity=identity, reference=ref)))
    return ref


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    args = parser.parse_args()
    report = dict(check='level-thirteen-boss', status='fail', accepted=False, errors=[])
    errors = report['errors']
    try:
        ref = original(args.probe)
        report.update(reference=str(REFERENCE), reference_sha256=fingerprint(REFERENCE), fresh=not args.reuse)
        if os.environ.get('PAPER') == '1':
            bindings = {e.get('binding') for e in ref.get('startup_context', [])}
            queries = ref.get('startup_queries', {})
            objects = ref.get('startup_objects') or {}
            if (ref.get('startup_profile') != {'paper': True, 'query_ms': 1}
                    or not queries.get('count') or queries.get('increments') != {'1': queries['count']}
                    or any(objects.get(hex(o), '0x0') == '0x0' for o in (0x44, 0x58))
                    or not {'application+0x44', 'application+0x58'} <= bindings):
                errors.append('Original lacks paper startup and 1 ms startup queries')
            if not ref.get('independent_prefix') and not ref.get('parent_checkpoint', {}).get('startup_profile', {}).get('paper'):
                errors.append('Original lacks independently recorded paper parent')
        checkpoint = ref['observer_checkpoint']
        if checkpoint['sha256'] != fingerprint(ROOT/checkpoint['path']): errors.append('Original checkpoint changed')
        for name, digest in checkpoint['inputs_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: errors.append('Original input changed: '+name)
        for name, digest in ref['adapter_inputs'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: errors.append('Original adapter changed: '+name)
        if ref['tracer_sha256'] != hashlib.sha256((ROOT/'Tests/NativeLevels/level_thirteen_boss_trace.py').read_bytes()).hexdigest():
            errors.append('Original boss tracer changed')
        if ref['status'] != 'pass' or ref['stop'] is not None: errors.append('Original fight did not pass')
        report['coverage'] = dict(original=boss.coverage(ref['boss_frames']))
        if not args.probe:
            if ref['fight_only']: errors.append('Original lacks completion')
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
                errors.append('Original lacks Red Tail-specific completed death callback')
            report['death_callbacks'] = callbacks
            complete = [k['key'] for k in ref['key_deliveries'] if k['phase'].startswith('advance-level-13-cheat-')]
            if complete != list(map(ord,'MPSCULLY')): errors.append('Original lacks Level 13 MPSCULLY')
            if len(ref['next_frames']) != 10 or any(f['player']['level'] != 14 for f in ref['next_frames']):
                errors.append('Original lacks ten Level 14 frames')
        # An incomplete reference cannot establish parity; do not launch an app
        # (or compare stale evidence) until the original itself meets the contract.
        if not args.original_only and not errors:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json','live-state.json','level-thirteen-route.json'): (OUT/name).unlink(missing_ok=True)
                (WORK/'app-plan.json').write_text(json.dumps(ref['plan']))
                subprocess.run([str(ROOT/'work/new-game/launch.sh'),str(OUT),'900','--menu-check',str(OUT),
                    '--menu-input-script',str(ROOT/'work/new-game/play-events.json'),'--menu-frames','16000',
                    '--menu-live-check',str(OUT),'--new-game-clock','--level-thirteen-route',str(WORK/'app-plan.json'),
                    '--level-thirteen-boss']+(['--boss-fight-only'] if args.probe else []),
                    cwd=ROOT, env=dict(os.environ),check=True,timeout=1000)
            app = json.loads((OUT/'level-thirteen-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App fight did not pass')
            for expected, actual, label in [('play_frames','level_one_frames','Level 1'),
                ('boss_frames','level_thirteen_frames','Red Tail'),('next_frames','level_fourteen_frames','Level 14')]:
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
            report['frames'] = dict(original=len(ref['boss_frames']),app=len(app['level_thirteen_frames']),level_fourteen=len(app['level_fourteen_frames']))
            report['coverage']['app'] = boss.coverage(app['level_thirteen_frames'])
            if not args.probe and len({f['player']['lives_lost'] for f in app['level_thirteen_frames']}) != 1:
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
