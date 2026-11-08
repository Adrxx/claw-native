"""Relocated entry frames against independent synthetic x86 callers."""
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys

from .. import build
from ..env import Env, HarnessError, NativeHost, U32, check_host_layout
from ..kernel import STACK_BASE, STACK_SIZE, STACK_TOP
from ..program import Program, Section
from .stack import relative_call


def synthetic():
    text = bytearray(b'\xcc' * 0x200)
    # Mutate argument two in its physical slot, reserve one local, pass its
    # address and the output pointer to a whole callee, then inspect the alias.
    outer = bytes.fromhex('8b442408 83f055 89442408 8b542404 83f055 50 89e1 52 51')
    outer += relative_call(0x401000 + len(outer), 0x401100)
    outer += bytes.fromhex('83c408 8b0c24 8b542408 890a 8d0424 894204 8b44240c 894208 83c404 c3')
    text[:len(outer)] = outer
    # Read the initial first argument, write one byte through it, reload the
    # first argument. An argument-slot alias makes the return observably change.
    alias = bytes.fromhex('8b442404 8b4c2408 8808 8b442404 c3')
    text[0x60:0x60 + len(alias)] = alias
    # Modify the caller's local and record actual callee-entry ESP.
    child = bytes.fromhex('8b442404 830007 8b542408 89e1 894a0c 8b00 c3')
    text[0x100:0x100 + len(child)] = child
    return Program('frame-synthetic', '', 0x400000, 0x2000,
                   [Section('.text', 0x401000, len(text), bytes(text))], (0x401000, 0x401200), {})


def checks(flavor='O2'):
    library = C.CDLL(str(build.library('frame-selftest', [Path(__file__).with_name('FrameModule.cpp')], flavor)))
    entry = library.claw_frame_selftest_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    found = {'run_initialization_and_budgets': library.claw_frame_runtime_selftest() == 1}
    env = Env(synthetic())
    check_host_layout(env._hostlib)
    found['verified_host_layout'] = True
    for frame in (0, 0x02007000, 0x01ff1000, 0x0200ff00):
        env._begin_case(None)
        output = env.object(16, 'output', fill=0)
        env._freeze()
        anchor = frame or STACK_TOP
        for operand in (0, 0x13579bdf, 0xfffffff9):
            args = (output, operand)
            native = env.run_native(entry, 0x401000, 0, args, entry_stack_pointer=frame)
            original = env.run_original(0x401000, 0, args, stack_pointer=anchor)
            label = f'{frame:x}_{operand:x}'
            found[label + '_comparison'] = env.compare(native, original, True, anchor + 4) is None
            found[label + '_aliases'] = (native.completed and not native.errors and native.bridged == [0x401100] and
                struct.unpack_from('<4I', native.heap, output - env._arena.heapBase) ==
                ((operand + 7) & 0xffffffff, anchor - 4, operand ^ 0x55, anchor - 16))
    argument_entry = library.claw_frame_arguments_selftest_entry
    argument_entry.argtypes, argument_entry.restype = entry.argtypes, U32
    for frame in (0, STACK_TOP - 0x100):
        anchor = frame or STACK_TOP
        for offset in (None, 4, 5, 6, 7):
            env._begin_case(None)
            destination = env.object(4, 'ordinary-destination', data=b'ABCD') if offset is None else anchor + offset
            env._freeze()
            native = env.run_native(argument_entry, 0x401060, 0, (destination, 0x5a), entry_stack_pointer=frame)
            original = env.run_original(0x401060, 0, (destination, 0x5a), stack_pointer=anchor)
            label = f'incoming_{frame:x}_{offset}'
            found[label] = env.compare(native, original, True, anchor + 4) is None and native.completed
            if offset is not None:
                expected = (destination & ~(255 << (8 * (offset - 4)))) | (0x5a << (8 * (offset - 4)))
                found[label + '_reload'] = native.eax == expected
    for invalid in (STACK_BASE - 4, STACK_BASE + STACK_SIZE - 4, STACK_TOP + 1, 1 << 40, -4, True, False, 1.0):
        rejected = False
        try:
            env.run_native(argument_entry, 0x401060, 0, (0, 0), entry_stack_pointer=invalid)
        except HarnessError:
            rejected = True
        found[f'incoming_reject_{invalid}'] = rejected
    return found


def sanitized_checks():
    command, environment = build.sanitized_python()
    if command is None:
        return {'available': False}
    child = subprocess.run(command + ['-m', 'clawparity.selftest.frames', '--sanitize'], env=environment,
                           capture_output=True, text=True, timeout=120)
    if child.returncode:
        return {'passed': False, 'detail': child.stderr[-2000:] or child.stdout[-2000:]}
    result = json.loads(child.stdout)
    return {'passed': not result['failed'], **result}


if __name__ == '__main__':
    values = checks('sanitize' if '--sanitize' in sys.argv else 'O2')
    print(json.dumps({'checked': len(values), 'failed': [key for key, value in values.items() if not value]}))
    raise SystemExit(not all(values.values()))
