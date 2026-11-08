#!/usr/bin/env python3
"""Check the pinned package, local archive, disc differences and muted play.

--disc is optional research input; runtime checks never need Original/.
--app exercises all retail levels with delivered real keys (brief smoke check),
including the Level 9/14 changed worlds and Level 12 omitted tile formats.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import runpy
import struct
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
SETUP = runpy.run_path(str(ROOT / 'scripts/setup-game-data.py'))


def rez_files(path):
    raw = path.read_bytes()
    files = {}
    def walk(offset, length, parent=''):
        end = offset + length
        while offset < end:
            kind, target, size = struct.unpack_from('<III', raw, offset)
            start = offset + (16 if kind else 28)
            zero = raw.index(0, start, end)
            name = raw[start:zero].decode('ascii')
            if kind:
                walk(target, size, parent + name + '/')
                offset = zero + 1
            else:
                ext = raw[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii')
                files[parent + name + ('.' + ext if ext else '')] = raw[target:target+size]
                offset = zero + 2
    walk(*struct.unpack_from('<II', raw, 131))
    return files


def world(raw):
    word = lambda at: struct.unpack_from('<I', raw, at)[0]
    offset = word(736)
    if word(8) & 2:
        raw = raw[:offset] + zlib.decompress(raw[offset:])
    planes = []
    for i in range(word(732)):
        at = offset + i*160
        header = struct.unpack_from('<40I', raw, at)
        cursor = header[35]
        objects = []
        for _ in range(header[32]):
            words = struct.unpack_from('<71i', raw, cursor)
            cursor += 284
            strings = []
            for length in words[1:5]:
                strings.append(raw[cursor:cursor+length].rstrip(b'\0').decode('ascii'))
                cursor += length
            objects.append(dict(words=list(words), strings=strings))
        tiles = raw[header[33]:header[33]+header[24]*header[25]*4]
        # Preserve the ordered image-set strings too, independent of offsets.
        cursor = header[34]
        sets = []
        for _ in range(header[31]):
            end = raw.index(0, cursor)
            sets.append(raw[cursor:end].decode('ascii'))
            cursor = end+1
        used = {}
        for (tile,) in struct.iter_unpack('<i', tiles):
            if tile >= 0:
                used.setdefault(sets[tile >> 16], set()).add(tile & 65535)
        planes.append(dict(objects=objects, tiles=hashlib.sha256(tiles).hexdigest(), sets=sets,
                           used={k: sorted(v) for k, v in used.items()},
                           header=(raw[at:at+128]+raw[at+132:at+160]).hex()))
    return planes


def compare_disc(disc, assets):
    assert SETUP['digest'](disc) == SETUP['REZ_HASH'], 'Unexpected research disc'
    original = rez_files(disc)
    missing = sorted(original.keys() - assets.keys())
    extra = sorted(assets.keys() - original.keys())
    differing = sorted(k for k in original.keys() & assets.keys() if original[k] != assets[k])
    identical = sum(original[k] == assets[k] for k in original.keys() & assets.keys())
    assert (identical, len(missing), len(extra)) == (12756, 318, 221)
    assert differing == ['LEVEL14/WORLDS/WORLD.WWD', 'LEVEL9/WORLDS/WORLD.WWD', 'STATES/CREDITS/CREDITS.TXT']
    changes = {}
    for level in (9, 14):
        key = f'LEVEL{level}/WORLDS/WORLD.WWD'
        before, after = world(original[key]), world(assets[key])
        assert original[key][:740] == assets[key][:740] and original[key][752:1524] == assets[key][752:1524]
        def tile_attributes(raw):
            start = struct.unpack_from('<I', raw, 736)[0]
            decoded = raw[:start]+zlib.decompress(raw[start:])
            return decoded[struct.unpack_from('<I', raw, 740)[0]:]
        assert tile_attributes(original[key]) == tile_attributes(assets[key])
        edits = []
        for p, q in zip(before, after):
            assert (p['tiles'], p['sets']) == (q['tiles'], q['sets'])
            assert p['header'] == q['header'], 'Plane properties differ'
            # Some retail objects share an ID. Count whole records, retaining
            # duplicates, and report the complete permutation separately.
            a, b = p['objects'], q['objects']
            key = lambda o: (tuple(o['words']), tuple(o['strings']))
            ac, bc = Counter(map(key, a)), Counter(map(key, b))
            removed = [dict(words=list(k[0]), strings=list(k[1])) for k in (ac-bc).elements()]
            added = [dict(words=list(k[0]), strings=list(k[1])) for k in (bc-ac).elements()]
            # Map each new ordinal to an old ordinal by complete record bytes.
            ordinals = {}
            for index, obj in reversed(list(enumerate(a))):
                ordinals.setdefault(key(obj), []).append(index)
            permutation = [ordinals[key(obj)].pop() for obj in b]
            edits.append(dict(removed=removed, added=added, new_to_old_ordinals=permutation,
                              reordered=permutation != sorted(permutation)))
        removed = [o['words'][0] for e in edits for o in e['removed']]
        added = [o['words'][0] for e in edits for o in e['added']]
        assert sorted(removed) == ([9720, 9798] if level == 9 else [2314]), removed
        assert not added, added
        changes[str(level)] = edits
    # Missing runtime sounds are restored from identical bytes in this ZIP.
    for name in ('1005', '1044'):
        assert original[f'LEVEL12/SOUNDS/TRIGGER/{name}.WAV'] == assets[f'LEVEL11/SOUNDS/TRIGGER/{name}.WAV']
    assert all(k[:-3]+'PID' in assets for k in missing if k.endswith('.PCX'))
    missing_pid = [k for k in missing if k.endswith('.PID')]
    assert missing_pid == ['LEVEL14/TILES/FRONT/SHORTCUT TO FINAL13.LNK.PID']
    for plane in world(assets['LEVEL14/WORLDS/WORLD.WWD']):
        assert 13 not in plane['used'].get('FRONT', []), 'Missing tile 13 is used'
    # Verify every tile referenced by every packaged world has a numeric PID.
    tile_ids = {}
    for path in assets:
        p = Path(path)
        if '/TILES/' in path and p.suffix == '.PID' and p.stem.isdigit():
            tile_ids.setdefault(p.parent.as_posix(), set()).add(int(p.stem))
    for level in range(1, 15):
        for plane in world(assets[f'LEVEL{level}/WORLDS/WORLD.WWD']):
            for image_set, ids in plane['used'].items():
                for identity in ids:
                    assert identity in tile_ids.get(f'LEVEL{level}/TILES/{image_set}', set()), (level, image_set, identity)
    return dict(identical=identical, missing=missing, extra=extra, differing=differing,
                missing_extensions=dict(Counter(Path(k).suffix for k in missing)), world_changes=changes,
                omissions='156 PCX have PID equivalents; 159 TXT/JBF/DIR/music scratch files are not runtime assets; '
                          'one unused shortcut-named PID (tile 13); two required WAVs restored byte-identically from LEVEL11',
                all_referenced_tiles_present=True)


def check_data(package, data, disc):
    assert SETUP['digest'](package) == SETUP['PACKAGE_HASH']
    prefix = 'CLAW-1.4.5.4/Assets/'
    with zipfile.ZipFile(package) as archive:
        assets = {n[len(prefix):].upper(): archive.read(n) for n in archive.namelist()
                  if n.startswith(prefix) and not n.endswith('/')}
    report = dict(package_sha256=SETUP['PACKAGE_HASH'], source=SETUP['SOURCE_PAGE'])
    if disc:
        report['disc_comparison'] = compare_disc(disc, assets)
    packed = rez_files(data / 'MENU/CLAW.REZ')
    excluded = {k for k in assets if SETUP['community_extension'](k)}
    assert len(excluded) == 221
    if disc:
        assert excluded == set(report['disc_comparison']['extra'])
    assert len(packed) == len(assets)-len(excluded)+2
    for key, raw in assets.items():
        if key in excluded:
            assert key not in packed and not (data/key).exists()
            continue
        assert packed[key] == raw, 'Repacked payload changed: ' + key
        assert (data / key).read_bytes() == raw, 'Loose payload changed: ' + key
    for name in ('1005', '1044'):
        key = f'LEVEL12/SOUNDS/TRIGGER/{name}.WAV'
        assert packed[key] == assets[f'LEVEL11/SOUNDS/TRIGGER/{name}.WAV'] == (data/key).read_bytes()
    report['payloads_unchanged'] = len(assets)-len(excluded)
    report['community_only_assets_excluded'] = len(excluded)
    report['restored_dialog_sounds'] = 2
    assert json.loads((data/'source.json').read_text())['source'] == 'claw-recluse'
    return report


def check_live(app, output):
    from real_input import Session, build_helper
    output.mkdir(parents=True, exist_ok=True)
    helper = build_helper(ROOT/'work/recluse-download/post-window-input')
    results = []
    for level in range(1, 15):
        out = output/f'level-{level}'
        out.mkdir(parents=True, exist_ok=True)
        session = Session(out, helper=helper)
        try:
            session.launch(app, {}, [*(['--crash-sweep-level', str(level)] if level != 1 else []), '--no-paper-startup',
                '--save-dir', str(out/'saves'), '--settings-dir', str(out/'settings')])
            assert not session.failed(), json.loads((out/'real-speed.json').read_text()).get('error')
            if level == 1:
                # Reach Level 1 through New Game using only real menu keys.
                for _ in range(12):
                    session.run(180)
                    if json.loads((out/'live.json').read_text()).get('state_vtable') == '0x50c264':
                        break
                    session.post('key', 36)
            session.run(30)
            before = json.loads((out/'live.json').read_text())
            assert before['state_vtable'] == '0x50c264' and before['level'] == level, before
            session.post('press', 124, 'down')
            session.run(30)
            session.post('press', 124, 'up')
            session.run(4)
            after = json.loads((out/'live.json').read_text())
            assert not session.failed(), session.gate()
            assert before['x'] != after['x'], (before, after)
            assert session.transitions().get('39:down', 0) > 0
            results.append(dict(level=level, status='pass', start=before['x'], end=after['x'], real_input=True))
            print(json.dumps(results[-1]), flush=True)
        finally:
            session.close()
    return results


def check_custom(app, folder, out):
    from real_input import Session, build_helper
    out.mkdir(parents=True, exist_ok=True)
    session = Session(out, helper=build_helper(ROOT/'work/recluse-download/post-window-input'))
    def live():
        return json.loads((out/'live.json').read_text())
    def tap(code):
        session.post('key', code)
        session.run(15)
        assert not session.failed(), session.gate()
    try:
        session.launch(app, {}, ['--custom-dir', str(folder.resolve()), '--no-paper-startup',
            '--save-dir', str(out/'saves'), '--settings-dir', str(out/'settings')])
        session.run(60)
        tap(36)
        for _ in range(10):
            if live().get('menu_selected') == 11003:
                break
            tap(125)
        assert live().get('menu_selected') == 11003
        tap(36)
        assert live().get('custom_dialog')
        tap(36)
        assert live().get('custom_flag') == 1 and live().get('state_vtable') == '0x50c264', live()
        session.run(45)
        before = live()['x']
        session.post('press', 124, 'down')
        session.run(20)
        session.post('press', 124, 'up')
        session.run(4)
        assert not session.failed() and before != live()['x'], live()
        assert session.transitions().get('39:down', 0) > 0
        assert live()['custom_level']['reads'] >= 3, 'Original world reader did not load the custom sample'
        return dict(status='pass', loaded=live()['custom_level'], real_input=True, start=before, end=live()['x'])
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', required=True, type=Path)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--disc', type=Path)
    parser.add_argument('--app', type=Path)
    parser.add_argument('--custom', type=Path, help='Folder with one known-supported CrazyHook sample and its companion assets')
    parser.add_argument('--output', type=Path, default=ROOT/'work/recluse-download/check')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = dict(status='fail')
    try:
        report.update(check_data(args.zip, args.data, args.disc))
        if args.app:
            bundled = args.app / 'Contents/Resources/GameData'
            assert SETUP['digest'](bundled/'MENU/CLAW.REZ') == SETUP['digest'](args.data/'MENU/CLAW.REZ'), 'App has different data'
            assert json.loads((bundled/'source.json').read_text())['source'] == 'claw-recluse'
            report['live'] = check_live(args.app.resolve(), args.output)
            if args.custom:
                report['custom'] = check_custom(args.app.resolve(), args.custom, args.output/'custom')
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], report=str(args.output/'report.json'))))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
