"""Verify Level 7 has no original boss, then compare its MPSCULLY end with Level 8.

The queue's level_seven_boss name is retained, but no boss defeat is claimed:
this original level ends with EndOfLevelPowerup. Generate the reference with
python -m Tests.NativeLevels.level_seven_end_trace. All artifacts stay in work/.
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
WORK = ROOT/'work/level-seven-end'
TRACE = WORK/'trace.json'
OUT = WORK/'run'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


play = load('level_two_play', 'scripts/check-level-two-play.py')
boss = load('level_two_boss', 'scripts/check-level-two-boss.py')


def world_inventory():
    packed = (ROOT/'Original/retail-assets/LEVEL7/WORLDS/WORLD.WWD').read_bytes()
    digest = hashlib.sha256(packed).hexdigest()
    if digest != '1b6275eb5cdec3902fc53773a34cddb66ff0a886fde11d758c0df408213c05db':
        raise ValueError('Original Level 7 world hash differs')
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
        raise ValueError('Unexpected boss object in Level 7')
    return dict(world_sha256=digest, boss_present=False, classes=dict(classes))


def original():
    keep = {'status', 'stop', 'plan', 'end_frames', 'next_frames', 'play_frames',
            'state_transitions', 'key_deliveries', 'presentations', 'active_boss_observed', 'startup_profile'}
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
    if os.environ.get('PAPER') == '1' and ref.get('startup_profile') != dict(paper=True, query_ms=1):
        raise ValueError('PAPER=1 requires an original paper startup with 1 ms queries')
    return ref


def main():
    global WORK, TRACE, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    parser.add_argument('--reference', type=Path, default=TRACE)
    parser.add_argument('--work', type=Path, default=WORK)
    args = parser.parse_args()
    TRACE, WORK = args.reference.resolve(), args.work.resolve()
    OUT = WORK/'run'
    report = dict(check='level-seven-boss', scope='No original boss; Level 7 completion to Level 8',
                  status='fail', accepted=False, errors=[], reference=str(TRACE),
                  fresh=not args.reuse and not args.original_only,
                  paper_startup=os.environ.get('PAPER') == '1', requested_game_profile='claw-v1.0')
    errors = report['errors']
    try:
        report['inventory'] = world_inventory()
        ref = original()
        report['startup_profile'] = ref.get('startup_profile')
        if ref['status'] != 'pass' or ref['stop'] is not None or ref['active_boss_observed']:
            errors.append('Original completion route is not passing or unexpectedly activated a boss')
        if len(ref['end_frames']) != 60:
            errors.append('Original lacks one second of Level 7 play')
        if len(ref['next_frames']) != 10 or any(f['player']['level'] != 8 for f in ref['next_frames']):
            errors.append('Original lacks ten Level 8 frames')
        completion = [k for k in ref['key_deliveries'] if k['phase'].startswith('advance-level-7-cheat-')]
        if [k['key'] for k in completion] != [ord(c) for c in 'MPSCULLY']:
            errors.append('Original lacks Level 7 MPSCULLY')
        report['frames'] = dict(level_seven=len(ref['end_frames']), level_eight=len(ref['next_frames']))
        if not args.original_only:
            if not args.reuse:
                OUT.mkdir(parents=True, exist_ok=True)
                for name in ('app-menu.json', 'live-state.json', 'level-seven-route.json'):
                    (OUT/name).unlink(missing_ok=True)
                (WORK/'plan.json').write_text(json.dumps(ref['plan']))
                prefix = ['--route-level-two-prefix'] if any(
                    k['phase'].startswith('results-key-return-') for k in ref['key_deliveries']) else []
                subprocess.run([str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
                    '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
                    '--menu-live-check', str(OUT), '--new-game-clock', *prefix,
                    '--level-seven-route', str(WORK/'plan.json'),
                    '--level-seven-end'], cwd=ROOT, env=dict(os.environ, CLAW_LIVES_BOSS_PROFILE='claw-v1.0'), check=True, timeout=1000)
            app = json.loads((OUT/'level-seven-route.json').read_text())
            if app.get('status') != 'pass': errors.append('App route did not pass')
            for expected, actual, label in [('play_frames', 'level_one_frames', 'Level 1'),
                                           ('end_frames', 'level_seven_frames', 'Level 7'),
                                           ('next_frames', 'level_eight_frames', 'Level 8')]:
                boss.compare_frames(ref[expected], app[actual], play.FIELDS, label, errors)
            shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
            if shape(ref['state_transitions']) != shape(app['state_transitions']): errors.append('State transitions differ')
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
