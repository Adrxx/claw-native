#!/usr/bin/env python3
"""Compare reconstructed callback with original x86; stub only its callee."""
import argparse
import hashlib
import ctypes
import random
import struct
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX

parser = argparse.ArgumentParser()
parser.add_argument("exe", type=Path)
parser.add_argument("library", type=Path)
parser.add_argument("--reference", choices=["v1.0", "crazyhook"], default="v1.0")
args = parser.parse_args()
raw = args.exe.read_bytes()
profiles = {
 "v1.0": ("350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263",0x498f40,0x4c82a0,0x6c,0xc8,0x5430c4,"claw_simple_animation_step_v10"),
 "crazyhook": ("33cf6e2663823f073d769c3d05a1ad5e13e3e4993ad2cb6822617737395004c6",0x49ca30,0x4c8550,0x7c,0xe0,0x5aafd8,"claw_simple_animation_step")
}
expected, callback, callee, logicOffset, actorOffset, globalAddress, nativeName = profiles[args.reference]
assert hashlib.sha256(raw).hexdigest() == expected, "Unverified binary; do not reuse addresses"
pe = struct.unpack_from("<I", raw, 60)[0]
section_count = struct.unpack_from("<H", raw, pe + 6)[0]
optional_size = struct.unpack_from("<H", raw, pe + 20)[0]
image_base = struct.unpack_from("<I", raw, pe + 52)[0]
image_size = struct.unpack_from("<I", raw, pe + 80)[0]
engine = Uc(UC_ARCH_X86, UC_MODE_32)
engine.mem_map(image_base, (image_size + 4095) & ~4095)
for i in range(section_count):
    header = pe + 24 + optional_size + i * 40
    _, virtual, size, offset = struct.unpack_from("<4I", raw, header + 8)
    if size:
        engine.mem_write(image_base + virtual, raw[offset:offset + size])
engine.mem_map(0x1000000, 0x10000)
engine.mem_map(0x2000000, 0x10000)
actor, logic, stack, stop = 0x1000000, 0x1002000, 0x2008000, 0x200f000
# Isolate the callback. Do not claim equivalence for the nested callee.
engine.mem_write(callee, b"\xc2\x04\x00")
calls = []
def hook(uc, address, size, user):
    if address == callee:
        esp = uc.reg_read(UC_X86_REG_ESP)
        calls.append((uc.reg_read(UC_X86_REG_ECX), read32(esp + 4)))
engine.hook_add(UC_HOOK_CODE, hook)
def read32(address):
    return struct.unpack("<I", engine.mem_read(address, 4))[0]
def write32(address, value):
    engine.mem_write(address, struct.pack("<I", value))
fn = getattr(ctypes.CDLL(str(args.library.resolve())), nativeName)
ptr = ctypes.POINTER(ctypes.c_uint32)
fn.argtypes = [ptr, ptr, ptr, ctypes.c_uint32, ctypes.c_uint32, ptr, ptr, ptr]
fn.restype = ctypes.c_int
rng = random.Random(1997)
cases = [0, 5, 1, 4, 6, 0xffffffff] * 100
for state in cases:
    field168, fielde0, tick = [rng.getrandbits(32) for _ in range(3)]
    write32(actor + logicOffset, logic)
    write32(logic + 0x1c, state)
    write32(logic + 0x168, field168)
    write32(actor + actorOffset, fielde0)
    write32(globalAddress, tick)
    write32(stack, stop)
    write32(stack + 4, actor)
    engine.reg_write(UC_X86_REG_ESP, stack)
    calls.clear()
    engine.emu_start(callback, stop, count=100)
    values = [ctypes.c_uint32(v) for v in [state, field168, fielde0, 0, 0, 0]]
    a, b, c, invoked, context, argument = values
    result = fn(ctypes.byref(a), ctypes.byref(b), ctypes.byref(c), actor, tick,
                ctypes.byref(invoked), ctypes.byref(context), ctypes.byref(argument))
    assert result == engine.reg_read(UC_X86_REG_EAX)
    assert [a.value, b.value, c.value] == [read32(logic + 0x1c), read32(logic + 0x168), read32(actor + actorOffset)]
    assert calls == ([(context.value, argument.value)] if invoked.value else [])
print(f"PASS: {len(cases)} callback cases match original x86; nested animation callee stubbed")
