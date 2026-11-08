"""Make local object-wiring scenes from authenticated original WWD placements.

    work/test-env/bin/python -m tools.claw.test_level --source-level 13
    work/test-env/bin/python -m tools.claw.test_level --source-level 11 --family laser

Only object table counts, reused record bytes and copied object positions change. Original
tiles, descriptions, palette/resource names and player spawn remain intact.
Scenes and their provenance manifests must stay under ignored work/test-levels/.
Use one source level per scene: LEVEL_ aliases and palettes belong to that level.
"""
import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

from Tests.NativeObjectConnections.rez import entries, REZ_SHA256

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / 'work/test-levels'
DEFAULT_LOGICS = (
    'TreasurePowerup', 'HealthPowerup', 'AmmoPowerup', 'MagicPowerup',
    'SpecialPowerup', 'Checkpoint', 'FrontCrate', 'BehindCrate',
    'PowderKeg', 'SpringBoard', 'TogglePeg', 'Elevator',
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def unpack_world(packed):
    if len(packed) < 1524 or word(packed, 0) != 1524:
        raise ValueError('Invalid WWD header')
    offset = word(packed, 736)
    raw = bytearray(packed[:offset] + zlib.decompress(packed[offset:])
                    if word(packed, 8) & 2 else packed)
    count = word(raw, 732)
    if not 1 <= count <= 16 or offset + count * 160 > len(raw):
        raise ValueError('Invalid WWD plane table')
    planes = []
    for plane_index in range(count):
        header = offset + plane_index * 160
        if word(raw, header) != 160:
            raise ValueError('Invalid WWD plane header')
        at = word(raw, header + 140)
        objects = []
        for index in range(word(raw, header + 128)):
            if at + 284 > len(raw):
                raise ValueError('Truncated WWD object')
            lengths = struct.unpack_from('<4I', raw, at + 4)
            end = at + 284 + sum(lengths)
            if end > len(raw):
                raise ValueError('Truncated WWD object strings')
            cursor, texts = at + 284, []
            for length in lengths:
                texts.append(bytes(raw[cursor:cursor+length]).split(b'\0')[0].decode('ascii'))
                cursor += length
            objects.append(dict(index=index, plane=plane_index, logic=texts[1],
                image_set=texts[2], record=bytes(raw[at:end]),
                id=word(raw, at), x=struct.unpack_from('<i', raw, at+20)[0],
                y=struct.unpack_from('<i', raw, at+24)[0]))
            at = end
        planes.append(dict(header=header, flags=word(raw, header+8), objects=objects))
    return raw, planes


def collision_descriptions(raw):
    at = word(raw, 740)
    if word(raw, at) != 32:
        raise ValueError('Invalid tile description table')
    count = word(raw, at+8)
    at += 32
    result = []
    for _ in range(count):
        kind = word(raw, at)
        if kind == 1:
            result.append((1, word(raw, at+16)))
            at += 20
        elif kind == 2:
            result.append((2, word(raw, at+16), word(raw, at+20),
                           *struct.unpack_from('<4i', raw, at+24)))
            at += 40
        else:
            raise ValueError('Unsupported original tile description')
    return result


def solid_at(raw, plane, descriptions, x, y):
    header = plane['header']
    tw, th, width, height = struct.unpack_from('<4I', raw, header+88)
    if not 0 <= x < tw * width or not 0 <= y < th * height:
        return False
    tile = struct.unpack_from('<i', raw, word(raw, header+132) +
                              4 * ((y//th) * width + x//tw))[0]
    if tile == -1:
        return False
    tile &= 0xffff
    if tile >= len(descriptions):
        raise ValueError('Tile outside original collision descriptions')
    desc = descriptions[tile]
    if desc[0] == 1:
        attribute = desc[1]
    else:
        _, outside, inside, left, top, right, bottom = desc
        attribute = inside if left <= x % tw <= right and top <= y % th <= bottom else outside
    # 1 is solid; 2 is a traversable one-way surface. Hazard attributes are
    # intentionally unsuitable for the object-wiring scene's landing places.
    return attribute in (1, 2)


def floor_below(raw, plane, descriptions, x, y, distance=512):
    for at in range(max(0, y), max(0, y)+distance):
        if solid_at(raw, plane, descriptions, x, at) and not solid_at(raw, plane, descriptions, x, at-1):
            return at
    raise ValueError(f'No safe original ground within {distance} pixels below ({x}, {y}); change --spacing/--start-offset')


def family_logics(families):
    if not families:
        return []
    symbols = json.loads((ROOT/'Tests/symbols.json').read_text())
    callbacks = {item['name']: int(address, 16)
                 for address, item in symbols['symbols'].items()
                 if item['kind'] == 'logic-callback'}
    for conflict in symbols.get('conflicts', []):
        item = conflict.get('dropped', {})
        if item.get('kind') == 'logic-callback':
            callbacks.setdefault(item['name'], int(conflict['address'], 16))
    selected = []
    for family in families:
        if not family or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in family):
            raise ValueError('Family must be a family id, not a path')
        path = ROOT/'Tests/families'/f'{family}.json'
        if not path.is_file():
            raise ValueError(f'Unknown family: {family}')
        spec = json.loads(path.read_text())
        owned = {int(item['address'] if isinstance(item, dict) else item, 16)
                 for item in spec.get('owned', [])}
        names = sorted(name for name, address in callbacks.items() if address in owned)
        if not names:
            raise ValueError(f'Family {family} owns no registered object callback; select --logic explicitly')
        selected.extend(names)
    return selected


def generate(packed, source_level, logics, *, spacing=64, start_offset=40, uncompressed=False):
    raw, planes = unpack_world(packed)
    action = next((p for p in planes if p['flags'] & 1), None)
    if action is None:
        raise ValueError('Original WWD has no action plane')
    sx, sy = struct.unpack_from('<2I', raw, 720)
    descriptions = collision_descriptions(raw)
    available = {}
    for obj in action['objects']:
        available.setdefault(obj['logic'], []).append(obj)
    if not logics:
        logics = [name for name in DEFAULT_LOGICS if name in available][:10]
    logics = list(dict.fromkeys(logics))
    if not logics:
        raise ValueError('No object logic selected')
    missing = set(logics) - available.keys()
    if missing:
        raise ValueError(f'Not placed in source Level {source_level}: {sorted(missing)}')
    records, manifest = [], []
    for slot, logic in enumerate(logics):
        # The closest real placement tends to use the source level's ordinary
        # variant rather than a remote boss arena's specially configured one.
        obj = min(available[logic], key=lambda o: abs(o['x']-sx)+abs(o['y']-sy))
        x = sx + start_offset + slot * spacing
        ground = floor_below(raw, action, descriptions, x, sy)
        try:
            old_ground = floor_below(raw, action, descriptions, obj['x'], obj['y'])
            foot = min(64, max(0, old_ground-obj['y']))
        except ValueError:
            foot = 32
        y = ground - foot
        record = bytearray(obj['record'])
        struct.pack_into('<2i', record, 20, x, y)
        translated = [5, 6]
        # WWD movement bounds are absolute; hit/attack/clip bounds are local
        # sprite coordinates and must remain copied verbatim.
        movement = struct.unpack_from('<4i', record, 19*4)
        if any(movement):
            dx, dy = x-obj['x'], y-obj['y']
            struct.pack_into('<4i', record, 19*4,
                             movement[0]+dx, movement[1]+dy,
                             movement[2]+dx, movement[3]+dy)
            translated.extend((19, 20, 21, 22))
        records.append(bytes(record))
        manifest.append(dict(logic=logic, id=obj['id'], source_plane=obj['plane'],
            source_index=obj['index'], source_x=obj['x'], source_y=obj['y'],
            x=x, y=y, ground_y=ground, image_set=obj['image_set'],
            source_record_sha256=sha256(obj['record']), record_sha256=sha256(record),
            translated_words=translated))
    record_bytes = b''.join(records)
    record_offset = word(raw, action['header']+140)
    original_capacity = sum(len(obj['record']) for obj in action['objects'])
    if len(record_bytes) > original_capacity:
        raise ValueError('Selected records do not fit the original action object table')
    # Reuse the original table span and retain the exact decoded byte count.
    # Native and original loaders can therefore consume this as a replacement
    # physical codec payload without changing their allocation contracts.
    raw[record_offset:record_offset+len(record_bytes)] = record_bytes
    for plane in planes:
        struct.pack_into('<I', raw, plane['header']+128, len(records) if plane is action else 0)
    offset = word(raw, 736)
    # Uncompressed WWD is an original format path; it avoids spending the
    # reference emulator's instruction budget in the original zlib decoder.
    if uncompressed:
        struct.pack_into('<I', raw, 8, word(raw, 8) & ~2)
    output = bytes(raw[:offset])+zlib.compress(raw[offset:]) if word(raw, 8) & 2 else bytes(raw)
    report = dict(schema=1, source_level=source_level, source_wwd_sha256=sha256(packed),
        source_compressed_sha256=sha256(packed[offset:]), payload_length=len(raw)-offset,
        source_rez_sha256=REZ_SHA256, output_sha256=sha256(output), spawn=dict(x=sx,y=sy),
        objects=manifest, object_types=len(logics), spacing=spacing, start_offset=start_offset,
        compressed=bool(word(raw, 8) & 2),
        decoded_length=len(raw), record_offset=record_offset, record_bytes=len(record_bytes),
        usage='Load with the same source level resource/palette namespace; this scene replaces its object tables only.')
    return output, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source-level', type=int, choices=range(1,15), default=13)
    parser.add_argument('--input', type=Path, help='Optional extracted original WWD, checked against the disc')
    parser.add_argument('--logic', action='append', default=[], help='Repeat for each exact registered logic name')
    parser.add_argument('--family', action='append', default=[], help='Repeat for each family id owning an object callback')
    parser.add_argument('--spacing', type=int, default=64)
    parser.add_argument('--start-offset', type=int, default=40)
    parser.add_argument('--uncompressed', action='store_true',
                        help='Write original uncompressed WWD format to shorten reference loading')
    parser.add_argument('--output', type=Path, default=DESTINATION/'objects.WWD')
    parser.add_argument('--list', action='store_true', help='List placed logic names without writing a scene')
    args = parser.parse_args(argv)
    try:
        target = args.output.resolve()
        if not target.is_relative_to(DESTINATION.resolve()) or target.suffix.upper() != '.WWD':
            raise ValueError('Output must be a WWD under work/test-levels/')
        if not 1 <= args.spacing <= 512 or abs(args.start_offset) > 4096:
            raise ValueError('Spacing must be 1..512 and start offset within 4096 pixels')
        archive_path = f'LEVEL{args.source_level}/WORLDS/WORLD.WWD'
        packed = next(payload for name,payload in entries() if name == archive_path)
        if args.input is not None and args.input.read_bytes() != packed:
            raise ValueError('--input must equal the authenticated original source-level WWD')
        if args.list:
            _, planes = unpack_world(packed)
            counts = {}
            for plane in planes:
                for obj in plane['objects']:
                    counts[obj['logic']] = counts.get(obj['logic'], 0)+1
            print(json.dumps(dict(command='test-level-list', source_level=args.source_level,
                                  objects=dict(sorted(counts.items())), status='pass')))
            return 0
        output, report = generate(packed, args.source_level,
            args.logic+family_logics(args.family), spacing=args.spacing, start_offset=args.start_offset,
            uncompressed=args.uncompressed)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
        report['output'] = str(target.relative_to(ROOT))
        target.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(dict(command='test-level', status='pass', output=report['output'],
                             manifest=str(target.with_suffix('.json').relative_to(ROOT)),
                             source_level=args.source_level, object_types=report['object_types'])))
        return 0
    except (ValueError, OSError, StopIteration, struct.error, zlib.error) as exc:
        parser.exit(1, f'test-level: {exc}\n')


if __name__ == '__main__':
    sys.exit(main())
