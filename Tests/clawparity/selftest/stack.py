"""Downward stack backing: executable synthetic probes, bridge aliases and bounds."""
import ctypes as C
import json
import struct
import subprocess
import sys
from pathlib import Path

from unicorn import UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP

from .. import build
from ..env import BRIDGE_STACK, Call, Env, HarnessError, NativeHost, U32
from ..kernel import EmulationFault, STACK_BASE, STACK_SIZE, STACK_TOP, STOP
from ..program import Program, Section, claw

ENTRY, SWEEP, CALLEE, PROBE, NESTED, CAPTURE = 0x401000, 0x401010, 0x401100, 0x401200, 0x401300, 0x402000
MARKER = 0x13579BDF


def relative_call(at, target):
    return b'\xe8' + struct.pack('<i', target - at - 5)


def synthetic():
    text = bytearray(b'\xcc' * 0x400)

    def put(at, code):
        text[at - ENTRY:at - ENTRY + len(code)] = code

    # cdecl(callee, reservation, output, tracked_sp): one escaped outer local,
    # three callee arguments, and an explicit call frame at STACK_TOP - 20.
    outer = bytes.fromhex('68df9b5713 89e0 50 ff742414 ff742414 ff542414 83c40c')
    outer += bytes.fromhex('8b542410 8b0a 8b09 894a10 8b0c24 894a14 83c404 c3')
    put(ENTRY, outer)
    # Large callee reserves real memory through the probe, saves its local
    # address to output, calls a nested body with that address, and returns.
    code = bytes.fromhex('55 89e5 8b4508')
    code += relative_call(CALLEE + len(code), PROBE)
    code += bytes.fromhex('8b550c 8b4510 8b00 890424 895204 8922 8d442404 894208')
    code += bytes.fromhex('54')
    code += relative_call(CALLEE + len(code), NESTED)
    code += bytes.fromhex('83c404 8b550c 8b0424 89420c 89ec 5d c3')
    put(CALLEE, code)
    # Independent __chkstk-equivalent: remove the return address, touch every
    # descending page plus the remainder, move ESP, then restore the return.
    # ECX/EDX are scratch registers in this synthetic contract.
    probe = bytes.fromhex('5a 89e1 3d00100000 7210 81e900100000 f60100 2d00100000 eb e9'
                          ' 29c1 f60100 89cc 52 c3')
    put(PROBE, probe)
    # A second frame aliases the large callee's local, mutates it, and exposes
    # its bytes through an import, while its own saved local remains separate.
    nested = bytes.fromhex('68efbeadde 8b442408 ff00 8b0c24 894804 50 ff1500204000 83c404 59 c3')
    put(NESTED, nested)
    return Program('stack-synthetic', '', 0x400000, 0x3000,
                   [Section('.text', ENTRY, len(text), bytes(text)),
                    Section('.data', CAPTURE, 0x1000, bytes(0x1000))],
                   (ENTRY, ENTRY + len(text)), {CAPTURE: 'SYNTH.dll!capture'})


def entry(flavor):
    library = C.CDLL(str(build.library('stack-selftest', [Path(__file__).with_name('StackModule.cpp')], flavor)))
    result = library.claw_stack_selftest_entry
    result.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    result.restype = U32
    return result


def setup(env):
    env._begin_case(None)
    token = env.object(24, 'output', fill=0)
    env._freeze()
    return token


def checks(flavor='O2', original=True):
    found = {}
    env = Env(synthetic())
    if flavor == 'sanitize':
        # Instrument the arena resolver too, including accesses across every
        # byte of the expanded backing and rejected boundary requests.
        env._hostlib = C.CDLL(str(build.hostlib(flavor)))
        env._host.bytes = C.cast(env._hostlib.claw_arena_bytes, C.c_void_p)
    native_entry = entry(flavor)
    env.fixture(CAPTURE, 'cdecl', 1, lambda env, call: env.get(call.arguments[0]), arguments=('ptr:8',))
    found['fixed_anchors'] = (STACK_TOP, STOP, BRIDGE_STACK) == (0x02008000, 0x0200F000, 0x02004000)
    found['bounded_lower_extension'] = (STACK_BASE, STACK_BASE + STACK_SIZE) == (0x01FF0000, 0x02010000)
    for size in (0x86A4, 0xA6A4, 0x11000):
        for tracked in (False, True):
            token = setup(env)
            anchor = STACK_TOP - 20 if tracked else BRIDGE_STACK
            args = (CALLEE, size, token, anchor if tracked else 0)
            touched = []
            hook = env.machine.uc.hook_add(UC_HOOK_MEM_READ, lambda uc, kind, address, count, value, user:
                                           touched.append(address), begin=STACK_BASE, end=STACK_BASE + STACK_SIZE - 1)
            try:
                native = env.run_native(native_entry, ENTRY, 0, args)
            finally:
                env.machine.uc.hook_del(hook)
            expected_local = anchor - 4 - size
            values = struct.unpack_from('<6I', native.heap, token - env._arena.heapBase)
            label = f'{size:x}_{"tracked" if tracked else "fallback"}'
            found[label + '_returns'] = native.completed and not native.errors and native.eax == MARKER + 1
            found[label + '_bridge'] = native.bridged == [CALLEE]
            found[label + '_locals'] = values == (expected_local, token, expected_local + 4, MARKER + 1, MARKER + 1, MARKER)
            found[label + '_capture'] = (len(native.events) == 1 and native.events[0][3] == (expected_local,) and
                                          native.events[0][4] == (struct.pack('<2I', MARKER + 1, 0xDEADBEEF),))
            expected_pages = [anchor - 4 - offset for offset in range(0x1000, size, 0x1000)] + [expected_local]
            found[label + '_probe_pages'] = all(page in touched for page in expected_pages)
            found[label + '_callee_return_sp'] = env.machine.register(UC_X86_REG_ESP) == anchor + 4
            if tracked:
                reference = env.run_original(ENTRY, 0, args)
                found[label + '_comparison'] = env.compare(native, reference, True, STACK_TOP + 4) is None

    # Native arena: every byte, including the newly mapped bottom and unchanged
    # last byte, is writable/readable. Live-object heap checks stay strict.
    token = setup(env)
    swept = env.run_native(native_entry, SWEEP, 0, (STACK_BASE, STACK_SIZE, 0, 0))
    found['arena_entire_stack'] = (swept.completed and not swept.errors and
                                  swept.eax == sum(i & 255 for i in range(STACK_SIZE)) and
                                  bytes(env._stack) == bytes(range(256)) * (STACK_SIZE // 256))
    # Round-trip the patterned full mapping through a whole callee, including
    # bytes at both ends outside its frames. The deep local must change too.
    env._bridge(Call(CALLEE, 0, 0, (0xA6A4, token, STACK_TOP - 4), 0))
    low = BRIDGE_STACK - 4 - 0xA6A4
    found['full_bridge_stack_copy'] = (
        bytes(env._stack) == env.machine.read(STACK_BASE, STACK_SIZE) and
        bytes(env._stack[:0x1000]) == bytes(range(256)) * 16 and
        bytes(env._stack[-0x1000:]) == bytes(range(256)) * 16 and
        env.read(low, 8) == struct.pack('<2I', 0xFFFEFDFC + 1, 0xDEADBEEF))
    too_deep = env.run_native(native_entry, ENTRY, 0, (CALLEE, BRIDGE_STACK - STACK_BASE + 0x1000, token, 0))
    found['oversized_probe_faults'] = (not too_deep.completed and too_deep.fault == 6 and
                                     any(isinstance(error, EmulationFault) for error in too_deep.errors))
    for label, address, count in (('below', STACK_BASE - 1, 1), ('above', STACK_BASE + STACK_SIZE, 1),
                                 ('cross_end', STACK_BASE + STACK_SIZE - 1, 2),
                                 ('dead_heap', token + 24, 1)):
        denied = env.run_native(native_entry, SWEEP, 0, (address, count, 0, 0))
        found['native_rejects_' + label] = not denied.completed and denied.fault == 1
    for index, (label, address) in enumerate((('below', STACK_BASE - 1), ('above', STACK_BASE + STACK_SIZE))):
        for write in (False, True):
            scratch = 0x0200D000 + index * 0x200 + int(write) * 0x100
            code = (b'\xc6\x05' + struct.pack('<I', address) + b'\x01' if write else
                    b'\xa0' + struct.pack('<I', address)) + b'\xc3'
            env.machine.write(scratch, code)
            try:
                env.machine.call(scratch)
                found[f'emulated_{label}_{write}'] = False
            except EmulationFault:
                found[f'emulated_{label}_{write}'] = True
        try:
            env.backend = 'native'
            env.read(address, 1)
            found['python_rejects_' + label] = False
        except HarnessError:
            found['python_rejects_' + label] = True

    if original:
        # Hash-checked original CRT probe, with no fixture or interception. The
        # scratch caller is synthetic; no original bytes are copied here.
        program = claw()
        crt, scratch = 0x4A3AE0, 0x0200D000
        for anchor in (STACK_TOP, BRIDGE_STACK):
            for size in (0x86A4, 0xA6A4):
                # Fresh machine avoids reusing Unicorn's translated scratch
                # instructions after changing the immediate reservation size.
                original_env = Env(program)
                machine = original_env.machine
                code = bytes.fromhex('55 89e5 b8') + struct.pack('<I', size)
                code += relative_call(scratch + len(code), crt)
                code += bytes.fromhex('c70424df9b5713 8b0424 89ec 5d c3')
                machine.write(scratch, code)
                touched = []
                hook = machine.uc.hook_add(UC_HOOK_MEM_READ, lambda uc, kind, address, count, value, user:
                                           touched.append(address), begin=STACK_BASE, end=STACK_BASE + STACK_SIZE - 1)
                try:
                    returned = machine.call(scratch, stack_pointer=anchor)
                finally:
                    machine.uc.hook_del(hook)
                low = anchor - 4 - size
                expected_pages = [anchor - 4 - offset for offset in range(0x1000, size, 0x1000)] + [low]
                found[f'original_crt_{anchor:x}_{size:x}'] = (
                    returned.completed and returned.eax == MARKER and returned.stack_pointer == anchor + 4 and
                    all(page in touched for page in expected_pages) and machine.words(low, 1) == (MARKER,) and
                    not machine._intercepted and not original_env.fixtures)
    return found


def sanitized_checks():
    command, environment = build.sanitized_python()
    if command is None:
        return {'available': False}
    child = subprocess.run(command + ['-m', 'clawparity.selftest.stack', '--sanitize'], env=environment,
                           capture_output=True, text=True, timeout=120)
    if child.returncode:
        return {'passed': False, 'detail': child.stderr[-2000:] or child.stdout[-2000:]}
    result = json.loads(child.stdout)
    return {'passed': not result['failed'], **result}


if __name__ == '__main__':
    values = checks('sanitize' if '--sanitize' in sys.argv else 'O2', original='--sanitize' not in sys.argv)
    print(json.dumps({'checked': len(values), 'failed': [key for key, value in values.items() if not value]}))
    raise SystemExit(not all(values.values()))
