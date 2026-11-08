#!/usr/bin/env python3
"""Compare complete original movement/collision responses without callee stubs."""
import argparse
import ctypes as c
import json
import random
import struct
import zlib
from pathlib import Path
from original_v10 import OriginalV10

p = argparse.ArgumentParser()
p.add_argument('exe', type=Path)
p.add_argument('library', type=Path)
p.add_argument('--cases', type=int, default=5000)
p.add_argument('--world', type=Path)
p.add_argument('--swift-traces', type=Path)
a = p.parse_args()
m = OriginalV10(a.exe)
u = m.u
manager, plane, actor = 0x1000000, 0x1001000, 0x1002000
owner, actor_list, nodes, actor_data = 0x1004000, 0x1005000, 0x1008000, 0x100a000
desc_ptrs, desc_data, cell_data, row_data = 0x1020000, 0x1030000, 0x1040000, 0x1080000
U32, I32 = c.c_uint32, c.c_int32
class Rect(c.Structure):
    _fields_ = [(f, U32) for f in ['left', 'top', 'right', 'bottom']]
class Actor(c.Structure):
    _fields_ = [(f, U32) for f in ['flags', 'x', 'y', 'mode', 'type', 'stepX', 'stepY',
                                  'supportToken', 'token', 'deltaX', 'deltaY']] + [('moveRect', Rect), ('hitRect', Rect)]
class Description(c.Structure):
    _fields_ = [(f, U32) for f in ['type', 'width', 'height', 'insideAttribute', 'outsideAttribute']] + [
        (f, I32) for f in ['left', 'top', 'right', 'bottom']]
class World(c.Structure):
    _fields_ = [('cells', c.POINTER(U32)), ('rowOffsets', c.POINTER(U32)), ('width', I32), ('height', I32),
                ('shiftX', U32), ('shiftY', U32), ('descriptions', c.POINTER(Description)), ('descriptionCount', U32),
                ('actors', c.POINTER(Actor)), ('actorCount', U32), ('maximumStepX', U32), ('maximumStepY', U32)]
lib = c.CDLL(str(a.library.resolve()))
resolve, move = lib.claw_collision_resolve, lib.claw_collision_move
for fn in [resolve, move]:
    fn.argtypes = [c.POINTER(World), c.POINTER(Actor), U32, U32, U32]
resolve.restype, move.restype = U32, U32
horizontal=lib.claw_collision_horizontal_clear
horizontal.argtypes=[c.POINTER(World),U32,U32,U32,U32,c.POINTER(U32)];horizontal.restype=U32
place = lib.claw_collision_place_on_ground
place.argtypes, place.restype = [c.POINTER(World), c.POINTER(Actor)], U32
rng = random.Random(199712)

def install_world(cells, columns, rows_count, descriptions, platforms, step=64):
    rows = [i * columns for i in range(rows_count)]
    m.write_words(manager + 0xc, [owner])
    m.write_words(owner + 8, [actor_list])
    m.write_words(actor_list + 0x14, [nodes if platforms else 0])
    m.write_words(manager + 0x4c, [desc_ptrs])
    m.write_words(manager + 0x5c, [plane])
    m.write_words(manager + 0x64, [step, step])
    m.write_words(plane + 0x20, [cell_data, row_data])
    m.write_words(plane + 0x30, [columns * 64, rows_count * 64])
    m.write_words(plane + 0x8c, [6, 6])
    m.write_words(cell_data, cells)
    m.write_words(row_data, rows)
    for index, d in enumerate(descriptions):
        address = desc_data + index * 0x40
        m.write_words(address, [0x513980 if d.type == 1 else 0x5139c8, d.width, d.height,
            d.insideAttribute if d.type == 1 else d.outsideAttribute, d.insideAttribute, d.left, d.top, d.right, d.bottom])
    m.write_words(desc_ptrs, [desc_data + i * 0x40 for i in range(len(descriptions))])
    for index, platform in enumerate(platforms):
        words = [rng.getrandbits(32) for _ in range(128)]
        copy_actor(platform, words, platforms)
        m.write_words(actor_data + index * 0x300, words)
        m.write_words(nodes + index * 0x20, [nodes + (index + 1) * 0x20 if index + 1 < len(platforms) else 0,
            0, actor_data + index * 0x300])
    native_cells, native_rows = (U32 * len(cells))(*cells), (U32 * len(rows))(*rows)
    native_descs, native_actors = (Description * len(descriptions))(*descriptions), (Actor * len(platforms))(*platforms)
    world = World(native_cells, native_rows, columns * 64, rows_count * 64, 6, 6,
                  native_descs, len(descriptions), native_actors, len(platforms), step, step)
    # Keep backing memory alive through every original/native call.
    world.storage = (native_cells, native_rows, native_descs, native_actors)
    return world

def copy_actor(value, words, platforms):
    for field, offset in [('flags', 8), ('x', 0x4c), ('y', 0x50), ('mode', 0xcc), ('type', 0xd0),
                          ('stepX', 0xdc), ('stepY', 0xe0), ('deltaX', 0x158), ('deltaY', 0x15c)]:
        words[offset // 4] = getattr(value, field)
    support = 0
    if value.supportToken:
        support = actor_data + next(i for i, p in enumerate(platforms) if p.token == value.supportToken) * 0x300
    words[0x80 // 4] = support
    for name, offset in [('moveRect', 0x118), ('hitRect', 0x128)]:
        r = getattr(value, name)
        words[offset // 4:offset // 4 + 4] = [getattr(r, f) for f, _ in Rect._fields_]

def check(world, value, platforms, x, y, options, case, full_move=False):
    before = [rng.getrandbits(32) for _ in range(128)]
    copy_actor(value, before, platforms)
    m.write_words(actor, before)
    platform_before = [bytes(u.mem_read(actor_data + i * 0x300, 512)) for i in range(len(platforms))]
    expected = m.call(0x4cbb60 if full_move else 0x4cbcd0, manager,
                      struct.pack('<4I', actor, x & 0xffffffff, y & 0xffffffff, options))
    actual = (move if full_move else resolve)(c.byref(world), c.byref(value), x, y, options)
    assert actual == expected, ('return', case, hex(expected), hex(actual))
    copy_actor(value, before, platforms)
    after = m.read_words(actor, 128)
    assert after == before, ('actor', case, [(hex(i * 4), hex(e), hex(g)) for i, (e, g) in enumerate(zip(after, before)) if e != g])
    for i in range(len(platforms)):
        assert bytes(u.mem_read(actor_data + i * 0x300, 512)) == platform_before[i]
    return expected

def new_actor(x, y, mode):
    return Actor(0, x & 0xffffffff, y & 0xffffffff, mode, 2, rng.choice([1, 2, 8, 16, 32]),
                 rng.choice([1, 2, 8, 16, 32]), 0, 1, 0, 0,
                 Rect((-16) & 0xffffffff, (-52) & 0xffffffff, 16, 60), Rect(0, 0, 0, 0))

def check_place(world, value, label):
    before = [rng.getrandbits(32) for _ in range(128)]
    copy_actor(value, before, [])
    m.write_words(actor, before)
    expected = m.call(0x4cd800, manager, struct.pack('<I', actor))
    actual = place(c.byref(world), c.byref(value))
    assert actual == expected, (label, 'spawn result', expected, actual)
    copy_actor(value, before, [])
    assert m.read_words(actor, 128) == before, (label, 'spawn actor')
    return actual

def check_horizontal(world,x,y,target,step,label):
    expected=m.call(0x4cda10,manager,struct.pack('<4I',x&0xffffffff,y&0xffffffff,target&0xffffffff,step))
    fault=U32();actual=horizontal(c.byref(world),x&0xffffffff,y&0xffffffff,target&0xffffffff,step,c.byref(fault))
    assert not fault.value and actual==expected,('horizontal',label,x,y,target,step,expected,actual,fault.value)

for batch in range(50):
    columns, rows_count = 16, 12
    descriptions = [Description(1, 64, 64, attribute, 0, 0, 0, 0, 0) for attribute in range(5)]
    descriptions += [Description(2, 64, 64, i % 5, (i + 1) % 5, 8, 12, 48, 63) for i in range(5)]
    cells = [rng.choice(list(range(len(descriptions))) + [0xffffffff, 0xeeeeeeee]) for _ in range(columns * rows_count)]
    platforms = []
    for i in range(5):
        platform = new_actor(rng.randrange(columns * 64), rng.randrange(rows_count * 64), 7)
        platform.token, platform.type = 17 + i, rng.choice([0x80, 0x80, 2])
        platform.hitRect = Rect((-32) & 0xffffffff, (-10) & 0xffffffff, 32, 0)
        platform.deltaY = rng.choice([-20, -1, 0, 1, 20]) & 0xffffffff
        platforms.append(platform)
    world = install_world(cells, columns, rows_count, descriptions, platforms, step=14 if batch%2 else 64)
    for index in range(a.cases//50):
        x,target=rng.randrange(-100,columns*64+100),rng.randrange(-100,columns*64+100)
        if index%7==0:target=x
        check_horizontal(world,x,rng.randrange(-100,rows_count*64+100),target,rng.choice([1,2,7,16,32,64,127]),(batch,index))
    for index in range(a.cases // 50):
        value = new_actor(rng.randrange(-100, columns * 64 + 100), rng.randrange(-100, rows_count * 64 + 100), index % 10)
        value.flags = rng.choice([0, 0, 0x400000, 0x10, 0x400010])
        if value.flags & 0x10:
            value.supportToken = rng.choice(platforms).token
        x, y = (value.x + rng.randint(-64, 64)) & 0xffffffff, (value.y + rng.randint(-40, 40)) & 0xffffffff
        check(world, value, platforms, x, y, index % 32, (batch, index), full_move=index % 2 == 0)
    for i in range(20):
        value = new_actor(rng.randrange(-100, columns * 64 + 100), rng.randrange(-100, rows_count * 64 + 100), 1)
        if i % 5 == 0:
            value.moveRect.left = 0x80000000
        check_place(world, value, ('generated spawn', batch, i))
print(f'PASS: {a.cases} generated original movement/resolver calls; all modes, tile attributes, platforms and complete actor state agree')
print('PASS: 1000 generated original ground placement calls; sentinel, clamping and complete actor bytes agree')
print(f'PASS: {a.cases} original horizontal eligibility queries, both directions, endpoints, clamping, all tile attributes; movement EAX now checked too')

# Directed transitions ensure important successful paths are reached rather
# than relying solely on randomly intersecting a platform or ladder boundary.
columns, rows_count = 16, 12
descriptions = [Description(1, 64, 64, i, 0, 0, 0, 0, 0) for i in range(5)]
cells = [0] * (columns * rows_count)
for x in range(columns):
    cells[8 * columns + x] = 1
world = install_world(cells, columns, rows_count, descriptions, [])
value = new_actor(320, 420, 4)
check(world, value, [], 320, 480, 0, 'directed landing')
assert value.mode == 1 and value.y == 451
for row in range(3, 8):
    cells[row * columns + 4] = 3
world = install_world(cells, columns, rows_count, descriptions, [])
value = new_actor(288, 180, 6)
check(world, value, [], 288, 130, 0, 'directed ladder top')
assert value.mode == 1 and value.y == 131
platform = new_actor(320, 512, 7)
platform.type, platform.token = 0x80, 17
platform.hitRect = Rect((-64) & 0xffffffff, (-10) & 0xffffffff, 64, 0)
platform.deltaY = (-20) & 0xffffffff
world = install_world([0] * (columns * rows_count), columns, rows_count, descriptions, [platform])
value = new_actor(320, 420, 4)
check(world, value, [platform], 320, 450, 8, 'directed platform acquisition')
assert value.mode == 1 and value.y == 441 and value.supportToken == 17 and value.flags & 0x10
check(world, value, [platform], 320, 441, 8, 'directed stationary support')
assert value.mode == 1 and value.supportToken == 17
check(world, value, [platform], 500, 441, 8, 'directed lost support')
assert value.mode == 4
required_entries = [0x4cbb60, 0x4cbcd0, 0x4cbe30, 0x4cbff0, 0x4cc1b0, 0x4cc2b0,
                    0x4cc420, 0x4cc570, 0x4cc6c0, 0x4cc9a0, 0x4ccc50, 0x4ccdd0,
                    0x4ccef0, 0x4ccf80, 0x4cd060, 0x4cd120, 0x4207f0, 0x4410f0]
assert set(required_entries) <= m.executed, [hex(x) for x in set(required_entries) - m.executed]
print('PASS: directed landing, ladder top, platform acquisition, retained/lost support; all 18 original response/helper entries execute')

if a.world:
    raw = a.world.read_bytes()
    offset = struct.unpack_from('<I', raw, 736)[0]
    if struct.unpack_from('<I', raw, 8)[0] & 2:
        raw = raw[:offset] + zlib.decompress(raw[offset:])
    plane_count = struct.unpack_from('<I', raw, 732)[0]
    for i in range(plane_count):
        ph = struct.unpack_from('<40I', raw, offset + 160 * i)
        if ph[2] & 1:
            columns, rows_count = ph[24:26]
            assert ph[22:24] == (64, 64)
            cells = list(struct.unpack_from('<' + 'I' * (columns * rows_count), raw, ph[33]))
            break
    desc_offset = struct.unpack_from('<I', raw, 740)[0]
    count = struct.unpack_from('<I', raw, desc_offset + 8)[0]
    pos = desc_offset + 32
    descriptions = []
    for index in range(count):
        kind, unknown, width, height = struct.unpack_from('<4I', raw, pos)
        if kind == 1:
            descriptions.append(Description(kind, width, height, struct.unpack_from('<I', raw, pos + 16)[0], 0, 0, 0, 0, 0))
            pos += 20
        else:
            assert kind == 2
            outside, inside = struct.unpack_from('<2I', raw, pos + 16)
            rect = struct.unpack_from('<4i', raw, pos + 24)
            descriptions.append(Description(kind, width, height, inside, outside, *rect))
            pos += 40
    world = install_world(cells, columns, rows_count, descriptions, [])
    value = new_actor(*struct.unpack_from('<2I', raw, 720), 1)
    initial = (value.x, value.y)
    assert check_place(world, value, 'Level 1 start') == 1
    print(f'PASS: original Level 1 ground placement: {initial} -> {(value.x, value.y)}')
    for i in range(1000):
        value = new_actor(rng.randrange(columns * 64), rng.randrange(rows_count * 64), 1)
        check_place(world, value, ('Level 1 spawn', i))
    print('PASS: 1000 additional original Level 1 ground placement calls')
    if a.swift_traces:
        entries = json.loads(a.swift_traces.read_text())
        for index, entry in enumerate(entries):
            before = entry['before']
            value = Actor(*before[:11], Rect(*before[11:15]), Rect(*before[15:19]))
            x, y, options = entry['target']
            is_move = entry['operation'] == 'move'
            # check() compares the portable state with complete original actor bytes.
            expected_return = check_place(world, value, ('Swift', index)) if entry['operation'] == 'place' else \
                check(world, value, [], x, y, options, ('Swift', index), full_move=is_move)
            after = [getattr(value, f) for f, _ in Actor._fields_[:11]] + [
                getattr(getattr(value, r), f) for r in ['moveRect', 'hitRect'] for f, _ in Rect._fields_]
            assert after == entry['after'], ('Swift adapter', index, after, entry['after'])
            if not is_move:
                assert entry['result'] == expected_return, ('Swift result', index)
        print(f'PASS: {len(entries)} Swift/C movement and ground placement adapter calls agree with original responses')
    for case in range(a.cases):
        value = new_actor(rng.randrange(columns * 64), rng.randrange(rows_count * 64), case % 9)
        x, y = (value.x + rng.randint(-64, 64)) & 0xffffffff, (value.y + rng.randint(-40, 40)) & 0xffffffff
        check(world, value, [], x, y, case % 32, ('Level 1', case), full_move=case % 2 == 0)
    for case in range(500):
        x=rng.randrange(columns*64);y=rng.randrange(rows_count*64)
        check_horizontal(world,x,y,x+rng.randrange(-200,201),32,('real Level1',case))
    print(f'PASS: {a.cases} original/native response calls in CD-rip Level 1; original actor objects are not instantiated')
print(f'Original instruction addresses reached: {len(m.executed)}. No callees stubbed; gameplay integration remains separate.')
