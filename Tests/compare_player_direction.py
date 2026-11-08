#!/usr/bin/env python3
"""Compare complete original face-left/right routines; no callees or stubs."""
import argparse
import ctypes as c
import hashlib
import random
import struct
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP

p = argparse.ArgumentParser()
p.add_argument('exe', type=Path)
p.add_argument('library', type=Path)
p.add_argument('--cases', type=int, default=5000)
a = p.parse_args()
b = a.exe.read_bytes()
assert hashlib.sha256(b).hexdigest() == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
pe = struct.unpack_from('<I', b, 60)[0]
n, opt = struct.unpack_from('<H', b, pe + 6)[0], struct.unpack_from('<H', b, pe + 20)[0]
base, size = struct.unpack_from('<I', b, pe + 52)[0], struct.unpack_from('<I', b, pe + 80)[0]
u = Uc(UC_ARCH_X86, UC_MODE_32)
u.mem_map(base, (size + 4095) & ~4095)
for i in range(n):
    o = pe + 24 + opt + 40 * i
    _, va, rs, ro = struct.unpack_from('<4I', b, o + 8)
    if rs:
        u.mem_write(base + va, b[ro:ro + rs])
u.mem_map(0x1000000, 0x4000)
u.mem_map(0x2000000, 0x10000)
actor, private, stack, stop = 0x1000000, 0x1001000, 0x2008000, 0x200f000
U32 = c.c_uint32
class Rect(c.Structure):
    _fields_ = [(x, U32) for x in ['left', 'top', 'right', 'bottom']]
class Body(c.Structure):
    _fields_ = [('renderFlags', U32)] + [(x, Rect) for x in ['moveRect', 'hitRect', 'attackRect']]
class Direction(c.Structure):
    _fields_ = [('facing', U32), ('idleTimer', U32)]
lib = c.CDLL(str(a.library.resolve()))
left, right = lib.claw_player_face_left, lib.claw_player_face_right
for fn in [left, right]:
    fn.argtypes = [c.POINTER(Body), c.POINTER(Direction)]
    fn.restype = None
executed = set()
def hook(uc, address, size, user):
    executed.add(address)
    if address == stop:
        uc.emu_stop()
u.hook_add(UC_HOOK_CODE, hook)
def write(address, values):
    u.mem_write(address, struct.pack('<' + 'I' * len(values), *values))
def read(address, count):
    return list(struct.unpack('<' + 'I' * count, u.mem_read(address, count * 4)))
rng = random.Random(19971011)
for case in range(a.cases):
    actor_words = [rng.getrandbits(32) for _ in range(128)]
    private_words = [rng.getrandbits(32) for _ in range(78)]
    for offset in [0x118, 0x128, 0x138]:
        if rng.randrange(3) == 0:
            actor_words[offset // 4] = 0x80000000
        if rng.randrange(3) == 0:
            actor_words[(offset + 8) // 4] = 0x80000000
    private_words[0] = rng.choice([0, 1, 2, 0xffffffff, rng.getrandbits(32)])
    body = Body(actor_words[0x40 // 4], *[Rect(*actor_words[offset // 4:offset // 4 + 4])
                                        for offset in [0x118, 0x128, 0x138]])
    direction = Direction(private_words[0], private_words[69])
    write(actor, actor_words)
    write(private, private_words)
    # Exercise transitions and repeated no-op calls in a single state history.
    schedule = [case % 2, case % 2, 1 - case % 2, 1 - case % 2]
    for tick, face_right in enumerate(schedule):
        (right if face_right else left)(c.byref(body), c.byref(direction))
        write(stack, [stop, actor, rng.getrandbits(32), private])
        u.reg_write(UC_X86_REG_ESP, stack)
        u.reg_write(UC_X86_REG_ECX, rng.getrandbits(32))
        u.emu_start(0x418120 if face_right else 0x418080, stop, count=1000)
        assert u.reg_read(UC_X86_REG_ESP) == stack + 4
        actor_words[0x40 // 4] = body.renderFlags
        for offset, rect in zip([0x118, 0x128, 0x138], [body.moveRect, body.hitRect, body.attackRect]):
            actor_words[offset // 4:offset // 4 + 4] = [getattr(rect, field) for field, _ in Rect._fields_]
        private_words[0], private_words[69] = direction.facing, direction.idleTimer
        assert read(actor, 128) == actor_words, ('actor', case, tick)
        assert read(private, 78) == private_words, ('private', case, tick)
print(f'PASS: {a.cases * 4} original face-left/right calls; entire actor/private buffers agree')
print(f'Original instruction addresses reached: {len(executed)}. No stubs; player movement/update not covered.')
