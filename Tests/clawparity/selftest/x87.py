"""Register-boundary tests, using hand-written synthetic code and the hash-checked original CRT."""
import ctypes as C
import json
import math
import random
import struct
import sys
import tempfile
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_EDX, UC_X86_REG_FPCW, UC_X86_REG_FPTAG

from .. import build, runner
from ..env import Env, NativeCall, NativeHost, U32
from ..kernel import EmulationFault, STACK_TOP
from ..program import Program, Section, claw

ENTRY, CONVERT = 0x401080, 0x4010C0


def synthetic():
    # cdecl(pointer, callee): load the pointed-to double and call the callee.
    # The callee rounds ST(0) using the active CW, consumes it and returns EAX.
    code = bytearray(b'\xcc' * 0x100)
    outer = bytes.fromhex('8b442404 dd00 ff542408 c3')
    callee = bytes.fromhex('83ec04 db1c24 58 c3')
    code[0x80:0x80 + len(outer)] = outer
    code[0xC0:0xC0 + len(callee)] = callee
    return Program('x87-synthetic', '', 0x400000, 0x3000,
                   [Section('.text', 0x401000, len(code), bytes(code)),
                    Section('.data', 0x402000, 0x1000, bytes(0x1000))],
                   (0x401000, 0x401100), {})


def entry(defines=(), flavor='O2'):
    library = C.CDLL(str(build.library('x87-selftest', [Path(__file__).with_name('X87Module.cpp')], flavor, defines)))
    result = library.claw_x87_selftest_entry
    result.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    result.restype = U32
    return result


def setup(env, value):
    env._begin_case(random.Random(123))
    token = env.object(16, 'operand', data=struct.pack('<d', value), fill=0)
    env._freeze()
    return token


def checks():
    results = {}
    env = Env(synthetic())
    env.whole_x87(CONVERT, 'cdecl', 0)
    correct = entry()
    rng = random.Random(923)
    values = [0.0, -0.0, 1.25, -1.75, 2.5, -3.5, math.nextafter(2.0, 0.0),
              math.nextafter(-2.0, 0.0), math.ldexp(1.0, -1074), math.inf, -math.inf, math.nan]
    values += [rng.uniform(-1e6, 1e6) for _ in range(24)]
    for index, value in enumerate(values):
        token = setup(env, value)
        native = env.run_native(correct, ENTRY, 0, (token, CONVERT))
        original = env.run_original(ENTRY, 0, (token, CONVERT))
        results[f'operand_{index}'] = env.compare(native, original, True, STACK_TOP + 4) is None
        results[f'event_{index}'] = len(native.events) == 1 and native.events[0][5] == (env.machine.extended(value),)
    for switch, kind in [('SELFTEST_X87_WRONG_OPERAND', 'event'),
                         ('SELFTEST_X87_WRONG_MEMORY', 'event-memory'),
                         ('SELFTEST_X87_MISSING', 'harness')]:
        token = setup(env, 1.25)
        native = env.run_native(entry((switch,)), ENTRY, 0, (token, CONVERT))
        original = env.run_original(ENTRY, 0, (token, CONVERT))
        difference = env.compare(native, original, True, STACK_TOP + 4)
        results[switch] = difference is not None and difference['kind'] == kind
        if switch == 'SELFTEST_X87_WRONG_OPERAND':
            results['same_integer_still_rejected'] = native.eax == original.eax
    undeclared = Env(synthetic())
    token = setup(undeclared, 1.25)
    native = undeclared.run_native(correct, ENTRY, 0, (token, CONVERT))
    results['undeclared_operand_rejected'] = native.fault == 6 and bool(native.errors)
    raw = NativeCall()
    raw.function, raw.x87ArgumentCount = CONVERT, 4
    env._host.fault = 0
    env._native_call(None, C.pointer(raw))
    results['extra_operand_rejected'] = env._host.fault == 6

    # Validate bad metadata through the same runner used by gate and oracle,
    # before any instructions execute. Keep synthetic cases independent.
    # The supported selftest entry runs from Tests/, outside tools' package root.
    sys.path.insert(0, str(build.ROOT))
    try:
        from tools.claw import manifest
    finally:
        sys.path.pop(0)
    valid = {'kind': 'whole', 'convention': 'cdecl', 'argc': 0, 'x87_args': 1}
    invalid = [{**valid, 'x87_args': value} for value in (0, 2, True, '1', None)]
    invalid += [{**valid, 'kind': 'fixture'}, {**valid, 'convention': 'fastcall'},
                {**valid, 'argc': -1}, {**valid, 'argc': 33}, {**valid, 'argc': True},
                {k: v for k, v in valid.items() if k != 'argc'},
                {k: v for k, v in valid.items() if k != 'convention'}]
    with tempfile.TemporaryDirectory(dir=build.ROOT / 'work', prefix='x87-metadata-') as directory:
        path = Path(directory) / 'family.json'
        spec = json.loads(Path(__file__).with_name('family.json').read_text())
        spec['callees']['0x401060'] = valid
        results['valid_metadata'] = not manifest.validate(spec)
        for index, declaration in enumerate(invalid):
            spec['callees']['0x401060'] = declaration
            path.write_text(json.dumps(spec))
            results[f'metadata_{index}'] = (bool(manifest.validate(spec)) and
                                             runner.run(path, original_only=True)['status'] == 'error')

    # Do not copy original instructions into a synthetic fixture. Run the
    # original CRT itself, comparing the transfer with an independent FLD
    # executed from local scratch memory. program.claw verifies the EXE hash.
    original_env = Env(claw())
    crt = 0x4A30E0
    original_env.whole_x87(crt, 'cdecl', 0)
    m = original_env.machine
    probe = 0x2001000
    data = probe + 0x100
    loader = bytes.fromhex('dd05') + struct.pack('<I', data) + b'\xc3'
    original_values = [0.0, -0.0, 1.9, -1.9, 2147483647 * 1.5, -2147483648 * 1.5,
                       2.0**53, -(2.0**53), math.inf, -math.inf, math.nan]
    original_values += [rng.randint(-2147483648, 2147483647) * 1.5 for _ in range(24)]
    for index, value in enumerate(original_values):
        token = setup(original_env, value)
        native = original_env.run_native(correct, ENTRY, 0, (token, crt))
        actual_edx = m.register(UC_X86_REG_EDX)
        control = m.register(UC_X86_REG_FPCW)
        tags = m.register(UC_X86_REG_FPTAG)
        m.reset_x87()
        m.write(probe, loader)
        m.write(data, struct.pack('<d', value))
        m.call(probe)
        expected_operand = m.x87_operand()
        direct = m.call(crt)
        results[f'original_crt_{index}'] = (not native.errors and native.eax == direct.eax and
                                            actual_edx == m.register(UC_X86_REG_EDX) and
                                            control == m.initial_control_word and tags == 0xFFFF and
                                            native.events[0][5] == (expected_operand,))
    # Altered incoming rounding modes must survive the conversion unchanged;
    # the CRT itself chooses truncation, independently of the caller's mode.
    for mode in range(4):
        for value in (1.75, -1.75):
            m.reset_x87()
            cw = (m.initial_control_word & ~0xC00) | (mode << 10)
            m.uc.reg_write(UC_X86_REG_FPCW, cw)
            m.push_x87(value)
            returned = m.call(crt)
            results[f'control_word_{mode}_{value}'] = (returned.eax == (int(value) & 0xFFFFFFFF) and
                                                       m.register(UC_X86_REG_FPCW) == cw)
    # A second comparison side must not inherit an interrupted operand or CW.
    m.push_x87(12.0)
    m.push_x87(13.0)
    try:
        m.x87_operand()
        results['extra_live_register_rejected'] = False
    except EmulationFault:
        results['extra_live_register_rejected'] = True
    m.reset_x87()
    results['reset_state'] = m.register(UC_X86_REG_FPTAG) == 0xFFFF and m.register(UC_X86_REG_FPCW) == 0x23F
    return results


if __name__ == '__main__':
    found = checks()
    print(json.dumps({'checked': len(found), 'failed': [name for name, passed in found.items() if not passed]}))
    raise SystemExit(not all(found.values()))
