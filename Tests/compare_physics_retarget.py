#!/usr/bin/env python3
"""Full original target-velocity routine, including its x87 return; no stubs."""
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
m = OriginalV10(a.exe)
address = 0x1000000
D3 = c.c_double * 3
class Physics(c.Structure):
    _fields_ = [('elapsed', c.c_double), ('timestep', c.c_double)] + [
        (f, D3) for f in ['acceleration', 'velocity', 'position', 'minimum', 'maximum', 'delta']] + [
        ('stopped', c.c_uint32), ('unused', c.c_uint32)] + [
        (f, D3) for f in ['remainder', 'maximumDelta', 'maximumVelocity']]
lib = c.CDLL(str(a.library.resolve()))
fn = lib.claw_physics_retarget
fn.argtypes = [c.POINTER(Physics), c.c_double, c.c_double, c.c_double]
fn.restype = c.c_double
rng = random.Random(199713)
def check(value, target, label):
    before = bytes(value)
    m.u.mem_write(address, before)
    expected = m.call_float(0x420dd0, address, struct.pack('<3d', *target))
    actual = fn(c.byref(value), *target)
    original = bytes(m.u.mem_read(address, c.sizeof(value)))
    assert original == bytes(value), (label, [(hex(i), original[i:i+8].hex(), bytes(value)[i:i+8].hex())
        for i in range(0, len(original), 8) if original[i:i+8] != bytes(value)[i:i+8]])
    assert struct.pack('<d', actual) == struct.pack('<d', expected), (label, 'return', expected, actual)

for i in range(a.cases):
    value = Physics.from_buffer_copy(rng.randbytes(c.sizeof(Physics)))
    value.position = D3(*(rng.uniform(-100000, 100000) for _ in range(3)))
    value.acceleration = D3(*(rng.uniform(-10000, 10000) for _ in range(3)))
    if i % 8 == 0:
        value.acceleration = D3(0, 0, 0)
    elif i % 8 == 1:
        value.acceleration = D3(*(rng.uniform(-0.2, 0.2) for _ in range(3)))
    target = [value.position[j] + rng.uniform(-10000, 10000) for j in range(3)]
    if i % 8 == 2:
        target = list(value.position)
    check(value, target, ('generated', i))
print(f'PASS: {a.cases} original target-velocity calls; complete state and floating return agree')

for i in range(1000):
    value = Physics()
    value.position = D3(rng.randrange(24576), rng.randrange(6144), 0)
    value.acceleration = D3(0, 2250, 0)
    check(value, [value.position[0], value.position[1] - 45, 0], ('jump target', i))
    assert value.velocity[1] == -450.0 and value.velocity[0] == 0
print('PASS: 1000 original jump retargets from map coordinates choose vertical velocity -450')
print(f'{len(m.executed)} original/capture instruction addresses reached; no original callees stubbed')
