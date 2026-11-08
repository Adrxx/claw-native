"""Verify Level 9 has no original boss, then compare its MPSCULLY end with Level 10.

The queue's level_nine_boss name is retained, but no boss defeat is claimed:
this original level ends with EndOfLevelPowerup. Generate the reference with
python -m Tests.NativeLevels.level_nine_end_trace. All artifacts stay in work/.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import trace_rows
from Tests.NativeLevels.xmidi_clock import CLOCK_VERSION
WORK = ROOT/'work/level-nine-end'
OUT = WORK/'run'
TRACE = WORK/'trace.json'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


play = load('level_two_play', 'scripts/check-level-two-play.py')
boss = load('level_two_boss', 'scripts/check-level-two-boss.py')


def world_inventory():
    packed = (ROOT/'Original/retail-assets/LEVEL9/WORLDS/WORLD.WWD').read_bytes()
    digest = hashlib.sha256(packed).hexdigest()
    if digest != '9fc4d469c8f97b71e3c81882e432891e212a50e51bb5c0ad69c7f17b2aa68e76':
        raise ValueError('Original Level 9 world hash differs')
    header = struct.unpack_from('<I', packed)[0]
    world = packed[:header]+zlib.decompress(packed[header:]) if struct.unpack_from('<I', packed, 8)[0]&2 else packed
    count, offset = struct.unpack_from('<2I', world, 0x2dc)
    classes = Counter()
    for index in range(count):
        plane = offset+index*160
        objects = struct.unpack_from('<I', world, plane+0x80)[0]
        at = struct.unpack_from('<I', world, plane+0x8c)[0]
        for _ in range(objects):
            lengths = struct.unpack_from('<4I', world, at+4)
            name, logic, _, _ = lengths
            value = world[at+284+name:at+284+name+logic].split(b'\0')[0].decode('ascii')
            if value: classes[value] += 1
            at += 284+sum(lengths)
    if classes['EndOfLevelPowerup'] != 1:
        raise ValueError('Original lacks its single EndOfLevelPowerup')
    bosses = {'Raux', 'Rauxe', 'Katherine', 'Wolvington', 'Gabriel', 'Marrow', 'Aquatis', 'RedTail', 'Omar'}
    if bosses.intersection(classes) or any('Boss' in name for name in classes):
        raise ValueError('Unexpected boss object in Level 9')
    return dict(world_sha256=digest, boss_present=False, classes=dict(classes))


def original():
    keep = {'status', 'stop', 'plan', 'end_frames', 'next_frames', 'play_frames',
            'state_transitions', 'startup_profile', 'startup_objects', 'startup_queries', 'key_deliveries', 'presentations', 'active_boss_observed', 'tracer_sha256', 'xmidi_clock_adapter'}
    ref, posted = {}, []
    for key, kind, value in trace_rows(TRACE):
        if key in keep:
            if kind == 'array': ref[key] = []
            elif kind == 'item': ref[key].append(value)
            else: ref[key] = value
        if key == 'physical_events' and kind == 'item' and value.get('service') == 'PostMessageA':
            posted.append(hex(value['wparam']))
    for frame in ref['end_frames'][1:] + ref['next_frames']:
        frame['screens'] = boss.screens(ref, frame)
    del ref['presentations']
    ref['posted_commands'] = posted
    return ref


def main():
    global WORK, OUT, TRACE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='Staged original trace; defaults remain unchanged')
    parser.add_argument('--work', type=Path, help='Separate evidence and derived-cache directory')
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    args = parser.parse_args()
    if args.reference:
        TRACE = args.reference.resolve()
        if not args.work:
            parser.error('--reference requires --work to isolate derived evidence')
    if args.work:
        WORK = args.work.resolve()
        if not WORK.is_relative_to(ROOT/'work'):
            parser.error('Evidence must stay under work/')
        OUT = WORK/'run'
    report = dict(reference=str(TRACE), fresh=not args.reuse, paper=os.environ.get('PAPER') == '1', check='level-nine-boss', scope='No original boss; Level 9 completion to Level 10',
                  status='fail', accepted=False, errors=[])
    errors = report['errors']
    try:
        report['inventory'] = world_inventory()
        ref = original()
        if args.reference:
            queries = ref.get('startup_queries', {})
            objects = ref.get('startup_objects', {})
            if (ref.get('startup_profile') != dict(paper=True, query_ms=1)
                    or not queries.get('count')
                    or queries.get('increments') != {'1': queries['count']}
                    or any(objects.get(hex(o), '0x0') == '0x0' for o in (0x44, 0x58))):
                raise ValueError('Staged reference lacks original paper startup and 1 ms queries')
        tracer = ROOT/'Tests/NativeLevels/level_nine_end_trace.py'
        if ref['tracer_sha256'] != hashlib.sha256(tracer.read_bytes()).hexdigest():
            errors.append('Original completion trace is stale')
        clock = ref['xmidi_clock_adapter']
        clock_source = ROOT/'Tests/NativeLevels/xmidi_clock.py'
        if (clock['version'], clock['hz'], clock['sha256']) != (CLOCK_VERSION, 120, hashlib.sha256(clock_source.read_bytes()).hexdigest()):
            errors.append('Original completion clock is stale')
        expected_states = [('0x50c264', 1)]
        for level in range(2, 11):
            expected_states.extend([('0x50c0c4', None), ('0x50c264', level)])
        progression = iter((s['vtable'], s.get('level')) for s in ref['state_transitions'])
        if not all(any(s == expected for s in progression) for expected in expected_states):
            errors.append('Original lacks the complete level/results progression')
        if ref['status'] != 'pass' or ref['stop'] is not None or ref['active_boss_observed']:
            errors.append('Original completion route is not passing or unexpectedly activated a boss')
        if len(ref['end_frames']) != 60:
            errors.append('Original lacks one second of Level 9 play')
        if len(ref['next_frames']) != 10 or any(f['player']['level'] != 10 for f in ref['next_frames']):
            errors.append('Original lacks ten Level 10 frames')
        completion = [k for k in ref['key_deliveries'] if k['phase'].startswith('advance-level-9-cheat-')]
        if [k['key'] for k in completion] != [ord(c) for c in 'MPSCULLY']:
            errors.append('Original lacks Level 9 MPSCULLY')
        report['frames'] = dict(level_nine=len(ref['end_frames']), level_ten=len(ref['next_frames']))
        if not args.original_only:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json', 'live-state.json', 'level-nine-route.json'):
                    (OUT/name).unlink(missing_ok=True)
                (WORK/'plan.json').write_text(json.dumps(ref['plan']))
                subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                    '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                    '--menu-live-check', str(OUT), '--new-game-clock', '--level-nine-route', str(WORK/'plan.json'),
                    '--level-nine-end'], cwd=ROOT, env=dict(os.environ, CLAW_LIVES_BOSS_PROFILE='claw-v1.0'), check=True, timeout=1000)
            app = json.loads((OUT/'level-nine-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App route did not pass')
            initial = app['level_nine_frames'][0]['player']
            report['game_profile'] = 'claw-v1.0'
            report['initial_lives'] = initial.get('lives')
            if (initial.get('lives'), initial.get('spare_lives')) != (3, 2):
                errors.append('Level 9 v1.0 reference requires three total and two spare lives')
            for expected, actual, label in [('play_frames', 'level_one_frames', 'Level 1'),
                                           ('end_frames', 'level_nine_frames', 'Level 9'),
                                           ('next_frames', 'level_ten_frames', 'Level 10')]:
                boss.compare_frames(ref[expected], app[actual], play.FIELDS, label, errors)
            shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
            if shape(ref['state_transitions']) != shape(app['state_transitions']): errors.append('State transitions differ')
            def identities(states):
                objects = [s['object'] for s in states]
                return [objects.index(obj) for obj in objects]
            if identities(ref['state_transitions']) != identities(app['state_transitions']):
                errors.append('State object reuse differs')
            report['presented_frames'] = sum(len(f.get('screens', [])) for f in app['level_nine_frames'] + app['level_ten_frames'])
            report['key_deliveries'] = len(app['key_deliveries'])
            def keys(rows):
                start = rows[0]['milliseconds']
                return [(k['phase'], k['key'], k['scan'], k['target'], k['vtable'], k['milliseconds']-start) for k in rows]
            if keys(ref['key_deliveries']) != keys(app['key_deliveries']): errors.append('Key deliveries differ')
            tail = lambda rows: rows[rows.index('0x800e'):] if '0x800e' in rows else []
            if tail(ref['posted_commands']) != tail(app['posted_commands']): errors.append('Posted commands differ')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        errors.append(str(error))
        try:
            app = json.loads((OUT/'app-menu.json').read_text())
            report['app_error'] = app.get('error')
            report['trace_tail'] = app.get('trace', [])[-12:]
        except (OSError, ValueError): pass
    report['status'] = 'fail' if errors else 'pass'
    report['accepted'] = not errors and not args.original_only
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK/('original-result.json' if args.original_only else 'result.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
