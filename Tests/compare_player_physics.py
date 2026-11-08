#!/usr/bin/env python3
"""Execute the original physics update and pixel conversion without stubs."""
import argparse
import ctypes as c
import math
import random
import struct
from pathlib import Path
from original_v10 import OriginalV10

p = argparse.ArgumentParser()
p.add_argument('exe', type=Path)
p.add_argument('library', type=Path)
p.add_argument('--cases', type=int, default=5000)
a = p.parse_args()
machine = OriginalV10(a.exe)
u, physics = machine.u, 0x1000000
D3 = c.c_double * 3
U32 = c.c_uint32
class Physics(c.Structure):
    _fields_ = [('elapsed', c.c_double), ('timestep', c.c_double)] + [
        (f, D3) for f in ['acceleration', 'velocity', 'position', 'minimum', 'maximum', 'delta']] + [
        ('stopped', U32), ('unused', U32)] + [(f, D3) for f in ['remainder', 'maximumDelta', 'maximumVelocity']]
assert c.sizeof(Physics) == 0xf0
lib = c.CDLL(str(a.library.resolve()))
construct = lib.claw_physics_construct
construct.argtypes = [c.POINTER(Physics)]
construct.restype = None
update = lib.claw_physics_update
update.argtypes = [c.POINTER(Physics), c.c_double]
update.restype = None
init = lib.claw_physics_initialize
init.argtypes = [c.POINTER(Physics), c.POINTER(c.c_double), c.POINTER(c.c_double), c.c_double]
init.restype = U32
limit = lib.claw_physics_limit_velocity
limit.argtypes = [c.POINTER(Physics), c.c_double]
limit.restype = None
pixels = [lib.claw_physics_pixel_x, lib.claw_physics_pixel_y]
for fn in pixels:
    fn.argtypes = [c.POINTER(Physics), c.POINTER(U32)]
    fn.restype = U32
rng = random.Random(199711)
def compare(value, label):
    original = bytes(u.mem_read(physics, c.sizeof(value)))
    if original != bytes(value):
        differences = []
        for offset in range(0, len(original), 8):
            x, y = original[offset:offset + 8], bytes(value)[offset:offset + 8]
            if x != y:
                differences.append((hex(offset), struct.unpack('<d', x)[0], struct.unpack('<d', y)[0], x.hex(), y.hex()))
        raise AssertionError((label, differences))
def install(value):
    u.mem_write(physics, bytes(value))
def number():
    return rng.choice([0., -0., 1., -1., rng.uniform(-10000, 10000), rng.randint(-5000, 5000) / 16.])

for case in range(1000):
    value = Physics.from_buffer_copy(rng.randbytes(c.sizeof(Physics)))
    # This original constructor has a fixed global receiver.
    u.mem_write(0x534db8, bytes(value))
    machine.call(0x415ab0, 0)
    construct(c.byref(value))
    assert bytes(u.mem_read(0x534db8, c.sizeof(value))) == bytes(value), ('construct', case)
    velocity, acceleration, step = D3(*(number() for _ in range(3))), D3(*(number() for _ in range(3))), number()
    install(value)
    result = machine.call(0x420a40, physics, struct.pack('<7d', *velocity, *acceleration, step))
    assert init(c.byref(value), velocity, acceleration, step) == result == 1
    compare(value, ('initialize', case))
    maximum = number()
    machine.call(0x420ad0, physics, struct.pack('<d', maximum))
    limit(c.byref(value), maximum)
    compare(value, ('limit', case))
print('PASS: 1000 original construct, initialize and limit calls; entire physics buffer agrees, untouched fields preserved')

for case in range(a.cases):
    value = Physics()
    value.elapsed, value.timestep = number(), number()
    for name in ['acceleration', 'velocity', 'position', 'minimum', 'maximum', 'delta', 'remainder', 'maximumDelta', 'maximumVelocity']:
        setattr(value, name, D3(*(number() for _ in range(3))))
    for axis in range(3):
        value.minimum[axis], value.maximum[axis] = sorted([value.minimum[axis], value.maximum[axis]])
        value.maximumDelta[axis] = abs(value.maximumDelta[axis])
    value.stopped = rng.choice([0, 0, 0, 1, 0xffffffff])
    value.unused = rng.getrandbits(32)
    step = rng.choice([0., -0., 0.001, 0.016, 0.033, 0.25, 1., 10., -0.016])
    install(value)
    machine.call(0x403b40, physics, struct.pack('<d', step))
    update(c.byref(value), step)
    compare(value, ('update', case, step))
print(f'PASS: {a.cases} original physics updates; full buffer agrees at recovered 53-bit precision')

for case in range(a.cases):
    value = Physics()
    for axis in range(3):
        value.delta[axis] = rng.choice([number(), rng.uniform(-1, 1), float(rng.getrandbits(32)), -float(rng.getrandbits(32))])
        value.remainder[axis] = rng.choice([number(), rng.uniform(-1, 1)])
    value.stopped, value.unused = rng.choice([0, 0, 0, 1, 0xffffffff]), rng.getrandbits(32)
    install(value)
    for axis, address, scratch_address in [(0, 0x420cd0, 0x544e8c), (1, 0x420d50, 0x544e88)]:
        scratch = U32(rng.getrandbits(32))
        machine.write_words(scratch_address, [scratch.value])
        expected = machine.call(address, physics)
        actual = pixels[axis](c.byref(value), c.byref(scratch))
        assert actual == expected, ('pixel return', case, axis, expected, actual)
        assert scratch.value == machine.read_words(scratch_address, 1)[0], ('scratch', case, axis)
        compare(value, ('pixel state', case, axis))
print(f'PASS: {a.cases * 2} original pixel conversions; return, remainder, scratch and unchanged fields agree')

traces = 0
for history in range(64):
    value = Physics()
    value.acceleration = D3(0, 2250, 0)
    value.velocity = D3(225 if history % 2 else -225, -500, 0)
    value.minimum = D3(-1000000, -1000000, -1000000)
    value.maximum = D3(1000000, 1000000, 1000000)
    value.maximumDelta = D3(32, 32, 32)
    value.maximumVelocity = D3(1000, 1000, 1000)
    install(value)
    for tick in range(360):
        milliseconds = 16 if history % 2 else [0, 1, 7, 13, 33, 80, 200][tick % 7]
        seconds = milliseconds * 0.001
        if tick % 90 == 0:
            value.velocity[0] = rng.choice([-300, -285, -225, 0, 225, 285, 300])
            u.mem_write(physics + 0x28, struct.pack('<d', value.velocity[0]))
        value.stopped = int(tick % 40 == 0)
        machine.write_words(physics + 0xa0, [value.stopped])
        machine.call(0x403b40, physics, struct.pack('<d', seconds))
        update(c.byref(value), seconds)
        compare(value, ('history', history, tick))
        for axis, address, scratch_address in [(0, 0x420cd0, 0x544e8c), (1, 0x420d50, 0x544e88)]:
            scratch = U32(machine.read_words(scratch_address, 1)[0])
            expected = machine.call(address, physics)
            actual = pixels[axis](c.byref(value), c.byref(scratch))
            assert actual == expected and scratch.value == machine.read_words(scratch_address, 1)[0]
            compare(value, ('history pixel', history, tick, axis))
        traces += 1
print(f'PASS: {traces} chained physics steps and {traces * 2} pixel conversions; pause, speed changes, time schedules and accumulated state agree')
print('These are physics-state histories, not complete original gameplay/input traces.')
print(f'Original instruction addresses reached: {len(machine.executed)}. No callees stubbed; not a whole player update.')
