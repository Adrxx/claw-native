#!/usr/bin/env python3
"""Compare v1.0 tile loaders, tile samples and world-foot samples without stubs.

The optional WWD is an asset reference, not proof of v1.0 asset identity.
"""
import argparse
import ctypes as c
import hashlib
import json
import random
import struct
import zlib
from pathlib import Path

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP

p = argparse.ArgumentParser()
p.add_argument('exe', type=Path)
p.add_argument('library', type=Path)
p.add_argument('--world', type=Path)
p.add_argument('--swift-world', type=Path)
p.add_argument('--cases', type=int, default=5000)
a = p.parse_args()
b = a.exe.read_bytes()
assert hashlib.sha256(b).hexdigest() == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
pe = struct.unpack_from('<I', b, 60)[0]
n = struct.unpack_from('<H', b, pe + 6)[0]
opt = struct.unpack_from('<H', b, pe + 20)[0]
base = struct.unpack_from('<I', b, pe + 52)[0]
image_size = struct.unpack_from('<I', b, pe + 80)[0]
u = Uc(UC_ARCH_X86, UC_MODE_32)
u.mem_map(base, (image_size + 4095) & ~4095)
for i in range(n):
    o = pe + 24 + opt + 40 * i
    _, va, rs, ro = struct.unpack_from('<4I', b, o + 8)
    if rs:
        u.mem_write(base + va, b[ro:ro + rs])
u.mem_map(0x1000000, 0x100000)
u.mem_map(0x2000000, 0x10000)
manager, plane, actor = 0x1000000, 0x1001000, 0x1002000
desc_pointers, desc_memory, cell_memory = 0x1003000, 0x1010000, 0x1040000
rows_memory, file_memory = 0x1080000, 0x1090000
stack, stop = 0x2008000, 0x200f000
U32, I32 = c.c_uint32, c.c_int32

class Description(c.Structure):
    _fields_ = [(x, U32) for x in ['type', 'width', 'height', 'insideAttribute', 'outsideAttribute']] + [
        (x, I32) for x in ['left', 'top', 'right', 'bottom']]

lib = c.CDLL(str(a.library.resolve()))
tile_fn = lib.claw_tile_attribute
tile_fn.argtypes = [c.POINTER(Description), I32, I32]
tile_fn.restype = U32
world_fn = lib.claw_world_point_attribute
world_fn.argtypes = [c.POINTER(U32), c.POINTER(U32), I32, I32, U32, U32,
                    c.POINTER(Description), U32, U32, U32, U32, U32]
world_fn.restype = U32
executed = set()

def hook(uc, address, size, user):
    executed.add(address)
    if address == stop:
        uc.emu_stop()

u.hook_add(UC_HOOK_CODE, hook)

def write(address, values):
    u.mem_write(address, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))

def read(address, count):
    return list(struct.unpack('<' + 'I' * count, u.mem_read(address, count * 4)))

def call(address, receiver, *args):
    write(stack, [stop, *args])
    u.reg_write(UC_X86_REG_ESP, stack)
    u.reg_write(UC_X86_REG_ECX, receiver)
    u.emu_start(address, stop, count=500)
    assert u.reg_read(UC_X86_REG_ESP) == stack + 4 * (1 + len(args))
    return u.reg_read(UC_X86_REG_EAX)

def install_description(index, d):
    addr = desc_memory + index * 0x40
    vtable = 0x513980 if d.type == 1 else 0x5139c8
    outside = d.insideAttribute if d.type == 1 else d.outsideAttribute
    write(addr, [vtable, d.width, d.height, outside, d.insideAttribute,
                 d.left, d.top, d.right, d.bottom])
    return addr

rng = random.Random(199710)
edge = [-0x80000000, -1, 0, 1, 63, 64, 0x7fffffff]
for case in range(a.cases):
    kind = 1 + case % 2
    values = [rng.choice(edge) if rng.randrange(2) else I32(rng.getrandbits(32)).value for _ in range(4)]
    if case % 3 == 0:
        values[0], values[2] = sorted(values[::2])
        values[1], values[3] = sorted(values[1::2])
    d = Description(kind, rng.getrandbits(32), rng.getrandbits(32),
                    rng.getrandbits(32), rng.getrandbits(32), *values)
    x = rng.choice(values + edge) if case % 3 else I32(rng.getrandbits(32)).value
    y = rng.choice(values + edge) if case % 3 else I32(rng.getrandbits(32)).value
    address = install_description(0, d)
    before = bytes(u.mem_read(address, 0x40))
    original = call(0x4cddc0 if kind == 1 else 0x4cde10, address, x, y)
    assert tile_fn(c.byref(d), x, y) == original, (case, kind, x, y)
    assert bytes(u.mem_read(address, 0x40)) == before
print(f'PASS: {a.cases} original tile samples; signed/inclusive edges, attributes and untouched state agree')

def install_world(cells, rows, descriptions, width, height, sx, sy):
    write(manager + 0x4c, [desc_pointers])
    write(manager + 0x5c, [plane])
    write(plane + 0x20, [cell_memory, rows_memory])
    write(plane + 0x30, [width, height])
    write(plane + 0x8c, [sx, sy])
    write(cell_memory, cells)
    write(rows_memory, rows)
    write(desc_pointers, [install_description(i, d) for i, d in enumerate(descriptions)])
    return (U32 * len(cells))(*cells), (U32 * len(rows))(*rows), (Description * len(descriptions))(*descriptions)

def compare_world(native, width, height, sx, sy, x, y, bottom, offset, case):
    cells, rows, descriptions = native
    write(actor + 0x4c, [x, y])
    write(actor + 0x124, [bottom])
    before = bytes(u.mem_read(actor, 0x200))
    original = call(0x4cd740, manager, actor, offset)
    recovered = world_fn(cells, rows, width, height, sx, sy, descriptions, len(descriptions), x, y, bottom, offset)
    assert original == recovered, (case, x, y, bottom, offset, original, recovered)
    assert bytes(u.mem_read(actor, 0x200)) == before
    return original

coordinates = [0, 1, 63, 64, 0x7fffffff, 0x80000000, 0xffffffff]
for batch in range(50):
    sx, sy = rng.randrange(8), rng.randrange(8)
    columns, rows_count = rng.randrange(1, 20), rng.randrange(1, 20)
    width, height = columns << sx, rows_count << sy
    descriptions = [Description(1 + i % 2, 1 << sx, 1 << sy, rng.getrandbits(32), rng.getrandbits(32),
                                0, 0, rng.randrange(1 << sx), rng.randrange(1 << sy)) for i in range(8)]
    # Nonsequential runtime row offsets detect accidental assumptions about stride.
    row_order = list(range(rows_count))
    rng.shuffle(row_order)
    rows = [i * columns for i in row_order]
    cells = [rng.choice([0xffffffff, 0xeeeeeeee, rng.getrandbits(16) << 16 | rng.randrange(8)])
             for _ in range(columns * rows_count)]
    native = install_world(cells, rows, descriptions, width, height, sx, sy)
    for case in range(100):
        xy = [rng.choice(coordinates + [width - 1, height - 1]) if case % 2 else rng.getrandbits(32) for _ in range(4)]
        compare_world(native, width, height, sx, sy, *xy, (batch, case))
print('PASS: 5000 original world-foot samples; wrapping, clamping, row offsets, cell flags and empty sentinels agree')

if a.world:
    source = a.world.read_bytes()
    offset, length = struct.unpack_from('<2I', source, 736)[0], struct.unpack_from('<I', source, 744)[0]
    raw = source[:offset] + zlib.decompress(source[offset:]) if struct.unpack_from('<I', source, 8)[0] & 2 else source
    assert len(raw) == offset + length
    plane_count, desc_offset = struct.unpack_from('<I', raw, 732)[0], struct.unpack_from('<I', raw, 740)[0]
    text = lambda bs: bs.split(b'\0', 1)[0].decode('utf8')
    reference = {'name': text(raw[16:80]), 'startX': struct.unpack_from('<I', raw, 720)[0],
                 'startY': struct.unpack_from('<I', raw, 724)[0], 'planes': [], 'descriptions': []}
    action = None
    for index in range(plane_count):
        ph = offset + index * 160
        words = list(struct.unpack_from('<40I', raw, ph))
        width, height = words[24:26]
        cells = list(struct.unpack_from('<' + 'I' * (width * height), raw, words[33]))
        pos = words[34]
        image_sets = []
        for _ in range(words[31]):
            end = raw.index(b'\0', pos)
            image_sets.append(text(raw[pos:end])); pos = end + 1
        pos = words[35]
        objects = []
        for _ in range(words[32]):
            obj = list(struct.unpack_from('<71I', raw, pos)); pos += 284
            strings = []
            for count in obj[1:5]:
                strings.append(text(raw[pos:pos + count])); pos += count
            objects.append({'words': obj, 'strings': strings})
        plane_ref = {'name': text(raw[ph + 16:ph + 80]), 'flags': words[2],
                     'movementX': I32(words[28]).value, 'movementY': I32(words[29]).value,
                     'z': I32(words[36]).value, 'width': width, 'height': height,
                     'tileWidth': words[22], 'tileHeight': words[23], 'tiles': cells,
                     'imageSets': image_sets, 'objects': objects}
        reference['planes'].append(plane_ref)
        if words[2] & 1:
            action = plane_ref
    count = struct.unpack_from('<I', raw, desc_offset + 8)[0]
    pos = desc_offset + 32
    descriptions = []
    for index in range(count):
        kind, unknown, width, height = struct.unpack_from('<4I', raw, pos)
        size = 20 if kind == 1 else 40
        assert kind in (1, 2)
        file_words = list(struct.unpack_from('<' + 'I' * (size // 4), raw, pos))
        outside = 0 if kind == 1 else file_words[4]
        inside = file_words[4] if kind == 1 else file_words[5]
        rect = [0, 0, 0, 0] if kind == 1 else [I32(v).value for v in file_words[6:10]]
        d = Description(kind, width, height, inside, outside, *rect)
        descriptions.append(d)
        reference['descriptions'].append({'type': kind, 'unknown': unknown, 'width': width,
            'height': height, 'inside': inside, 'outside': outside, 'rect': None if kind == 1 else rect})
        # Exercise the real loader as well as the resulting virtual sample method.
        addr = install_description(index, d)
        before = read(addr, 16)
        u.mem_write(file_memory, raw[pos:pos + size])
        assert call(0x4d5840 if kind == 1 else 0x4d5c30, addr, file_memory) == 1
        assert read(addr, 16) == before
        points = [(0, 0), (width - 1, height - 1), (width, height), (-1, -1)]
        if kind == 2:
            points += [(x, y) for x in [d.left - 1, d.left, d.right, d.right + 1]
                       for y in [d.top - 1, d.top, d.bottom, d.bottom + 1]]
        for x, y in points:
            assert call(0x4cddc0 if kind == 1 else 0x4cde10, addr, x, y) == tile_fn(c.byref(d), x, y)
        pos += size
    assert pos == len(raw)
    swift_samples = []
    if a.swift_world:
        swift_world = json.loads(a.swift_world.read_text())
        swift_samples = swift_world.pop('footSamples')
        assert swift_world == reference, 'Swift WWD fields differ from raw reference'
        print(f'PASS: Swift WWD fields agree: {len(reference["planes"])} planes, {len(action["objects"])} complete objects, {count} descriptions')
    assert action is not None
    tw, th = action['tileWidth'], action['tileHeight']
    sx, sy = tw.bit_length() - 1, th.bit_length() - 1
    assert tw == 1 << sx and th == 1 << sy
    width, height = action['width'] * tw, action['height'] * th
    rows = [i * action['width'] for i in range(action['height'])]
    native = install_world(action['tiles'], rows, descriptions, width, height, sx, sy)
    for index, sample in enumerate(swift_samples):
        expected = compare_world(native, width, height, sx, sy, sample['x'], sample['y'],
                                 sample['bottom'], sample['offset'], ('Swift', index))
        assert sample['attribute'] == expected, ('Swift world adapter', index)
    if swift_samples:
        print(f'PASS: {len(swift_samples)} Swift/C adapter foot samples agree with original world query')
    attributes = set()
    for case in range(10000):
        x = rng.randrange(width) if case % 2 else rng.getrandbits(32)
        y = rng.randrange(height) if case % 2 else rng.getrandbits(32)
        attributes.add(compare_world(native, width, height, sx, sy, x, y, 60, rng.choice([-16, 0, 16]) & 0xffffffff, case))
    print(f'PASS: {count} original tile loaders and boundary samples; 10000 original/native Level 1 foot samples; attributes {sorted(attributes)}')
print(f'Original instruction addresses reached: {len(executed)}. No original callees stubbed.')
