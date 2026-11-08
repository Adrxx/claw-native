"""Exact x87 transport only. Original probes do not admit or translate a family."""
import ctypes as C
from dataclasses import replace
import json
import math
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_FPCW, UC_X86_REG_FPSW
from .. import build, runner
from ..env import Env, Halt, NativeCall, NativeHost, NativeX87State, NativeX87Value, U32, CALLBACK
from ..kernel import Machine
from ..program import Program, Section, claw

ENTRY, CONVERT, SUM = 0x401090, 0x401100, 0x401120


def synthetic():
    code = bytearray(b'\xcc' * 0x200)
    # Truncate to int64, return EDX:EAX; separately add two extended operands.
    convert = bytes.fromhex('83ec08 df3c24 58 5a c3')
    code[0x100:0x100+len(convert)] = convert
    code[0x120:0x123] = bytes.fromhex('dec1 c3')
    return Program('x87-exact-synthetic', '', 0x400000, 0x3000,
                   [Section('.text', 0x401000, len(code), bytes(code)),
                    Section('.data', 0x402000, 0x1000, bytes(0x1000))], (0x401000, 0x401200), {})


def entry(flavor, symbol='claw_x87_exact_selftest_entry'):
    library = C.CDLL(str(build.library('x87-selftest', [Path(__file__).with_name('X87Module.cpp')], flavor)))
    f = getattr(library, symbol)
    f.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    f.restype = U32
    return f


def state(snapshot, pop=1, push=0):
    control, status, slots = snapshot
    result = NativeX87State()
    result.size, result.version = C.sizeof(result), 1
    result.control, result.status, result.count = control, status, len(slots)
    result.popCount, result.pushCount = pop, push
    for i, (sig, exp) in enumerate(slots):
        result.slots[i] = NativeX87Value(sig, exp, 0)
    return result


def snapshot(s):
    return s.control, s.status, tuple((v.significand, v.signExponent) for v in s.slots[:s.count])


def native_stack_result(env, f, value, target, words, receiver=0):
    env._begin_case(random.Random(781))
    inp = env.object(C.sizeof(value), 'input', data=bytes(value), fill=0)
    out = env.object(C.sizeof(value), 'output', fill=0)
    env._freeze()
    result = env.run_native(f, 0x4010d0, 0, (inp, target, *words, out, receiver))
    return result, NativeX87State.from_buffer_copy(env.read(out, C.sizeof(value)))


def stack_result_checks(flavor):
    """Independent producer bodies, including a result binary64 cannot carry."""
    program = synthetic()
    code = bytearray(program.sections[0].data)
    # Load the two incoming ordinary words as binary64, expose their order in
    # EDX:EAX, and return. The extended producer loads independent m80 data.
    bodies = {
        0x401140: 'dd442404 8b442404 8b542408 c3',
        0x401160: 'dd442404 8b442404 8b542408 c20800',
        0x401180: 'db2d00204000 8b442404 8b542408 c3',
        0x4011a0: 'c3',  # wrong actual effect
        0x4011b0: 'dd442404 d9e8 dec1 c3',  # transient overflow at depth 7
        0x4011d0: 'dd442404 d9c9 d9e0 d9c9 c3',  # corrupt a lower live slot
    }
    for address, body in bodies.items():
        raw = bytes.fromhex(body)
        code[address-0x401000:address-0x401000+len(raw)] = raw
    program.sections[0].data = bytes(code)
    extended = (0x8000000000000001, 0x3fff)
    program.sections[1].data = struct.pack('<QH', *extended) + bytes(0x1000-10)
    env, reference, checks = Env(program), Machine(program, 0x3000000, 0x40000), {}
    f = entry(flavor, 'claw_x87_stack_result_selftest_entry')
    for target in bodies:
        env.whole_x87(target, 'stdcall' if target == 0x401160 else 'cdecl', 2,
                      exact={'pop': 0, 'push': 1})
    lower = (extended, (0, 0x8000), (0xb17217f7d1cf79ac, 0x3ffe))
    words = struct.unpack('<II', struct.pack('<d', -13.123456789))
    for target in (0x401140, 0x401160, 0x401180):
        for depth in range(8):
            for rounding in range(4):
                before = (0x33f | rounding << 10, (depth << 11) | 0x4521,
                          tuple(lower[i % len(lower)] for i in range(depth)))
                reference.set_x87_state(*before)
                returned = reference.call(target, arguments=words)
                expected = reference.x87_state()
                result, out = native_stack_result(env, f, state(before, 0, 1), target, words)
                checks[f'producer_{target:x}_{depth}_{rounding}'] = (
                    returned.completed and result.completed and not result.errors and
                    out.returned == 1 and snapshot(out) == expected and
                    out.eax == words[0] and out.edx == words[1] and
                    result.events[0][3] == words and result.events[0][5] == ('extended-v1', *before) and
                    snapshot(out)[2][1:] == before[2] and
                    snapshot(out)[2][0] == (extended if target == 0x401180 else
                                            Machine.extended(-13.123456789)))
    # Exercise thiscall's receiver as well as the two independently ordered words.
    env.x87_callees[0x401160] = replace(env.x87_callees[0x401160], convention='thiscall')
    result, out = native_stack_result(env, f, state((0x23f, 0, ()), 0, 1), 0x401160, words, 0x12345678)
    checks['producer_thiscall'] = result.completed and result.events[0][1] == 0x12345678
    valid = state((0x23f, 0x4521, lower), 0, 1)
    full = state((0x23f, 0, tuple(lower[i % 3] for i in range(8))), 0, 1)
    result, _ = native_stack_result(env, f, full, 0x401140, words)
    checks['producer_full_cpp'] = not result.completed and result.fault == 5 and not result.events
    # Bypass the C++ validator: the host must reject overflow before executing.
    raw = NativeCall(); raw.function = 0x401140; raw.x87ArgumentCount = 2
    raw.argumentCount = 2; raw.arguments[0], raw.arguments[1] = words
    raw.x87State = C.pointer(full)
    env._host.fault = 0; env.events.clear(); env._native_call(None, C.pointer(raw))
    checks['producer_full_host'] = env._host.fault == 5 and not full.returned and not env.events
    for field, value in [('argumentCount', 1), ('argumentCount', 3), ('receiver', 1),
                         ('x87Operation', 1), ('sourceTransferKind', 1), ('x87Argument', 1)]:
        broken = NativeCall.from_buffer_copy(raw); broken.x87State = C.pointer(valid)
        setattr(broken, field, value)
        env._host.fault = 0; env._native_call(None, C.pointer(broken))
        checks[f'producer_bad_request_{field}'] = env._host.fault == 5 and not valid.returned
    for field, value in [('popCount', 1), ('pushCount', 0), ('pushCount', 2), ('returned', 1),
                         ('eax', 1), ('edx', 1), ('count', 9), ('control', 0x13f)]:
        broken = NativeX87State.from_buffer_copy(valid); setattr(broken, field, value)
        result, _ = native_stack_result(env, f, broken, 0x401140, words)
        checks[f'producer_bad_state_{field}'] = not result.completed and result.fault == 5
    for target in (0x4011a0, 0x4011b0, 0x4011d0):
        result, _ = native_stack_result(env, f, valid if target != 0x4011b0 else
            state((0x23f, 0, tuple(lower[i % 3] for i in range(7))), 0, 1), target, words)
        checks[f'producer_wrong_effect_{target:x}'] = (
            not result.completed and result.fault == 5 and bool(result.events))
    # Both directions of a wrong cdecl/stdcall declaration must fail cleanup.
    for target, convention in ((0x401140, 'stdcall'), (0x401160, 'cdecl')):
        env.x87_callees[target] = replace(env.x87_callees[target], convention=convention)
        result, _ = native_stack_result(env, f, valid, target, words)
        checks[f'producer_bad_cleanup_{target:x}'] = not result.completed and result.fault == 5
    env.x87_callees[0x401140] = replace(env.x87_callees[0x401140], convention='cdecl')
    original_callback = env._host.call
    for mode in ('ignored', 'lower', 'cw', 'top', 'count', 'receipt', 'effect', 'request', 'eax'):
        def corrupt(user, pointer):
            if mode == 'ignored': return 0
            value = env._native_call(user, pointer)
            s = pointer.contents.x87State.contents
            if mode == 'lower': s.slots[1].significand ^= 1
            elif mode == 'cw': s.control ^= 0x400
            elif mode == 'top': s.status ^= 0x800
            elif mode == 'count': s.count = 0
            elif mode == 'receipt': s.returned = 0
            elif mode == 'effect': s.popCount = 1
            elif mode == 'request': pointer.contents.arguments[1] ^= 1
            elif mode == 'eax': s.eax ^= 1
            return value
        cb = CALLBACK(corrupt); env._host.call = cb
        result, _ = native_stack_result(env, f, valid, 0x401140, words)
        checks[f'producer_bad_host_{mode}'] = not result.completed and result.fault == 5
    env._host.call = original_callback
    return checks


def native(env, f, value, target):
    env._begin_case(random.Random(781))
    inp = env.object(C.sizeof(value), 'input', data=bytes(value), fill=0)
    out = env.object(C.sizeof(value), 'output', fill=0)
    env._freeze()
    result = env.run_native(f, ENTRY, 0, (inp, target, out))
    return result, NativeX87State.from_buffer_copy(env.read(out, C.sizeof(value)))


def direct_load(m, slots, cw):
    # Independent architectural FLD m80 loads, not the register-write bridge.
    m.reset_x87()
    m.uc.reg_write(UC_X86_REG_FPCW, cw)
    scratch, data = 0x2001000, 0x2001200
    code = bytearray()
    for i, value in enumerate(reversed(slots)):
        m.write(data + 16*i, struct.pack('<QH', *value))
        code += b'\xdb\x2d' + struct.pack('<I', data + 16*i)
    m.write(scratch, bytes(code) + b'\xc3')
    # Scratch loader instructions can vary between cases.
    m.uc.ctl_remove_cache(scratch, scratch + 0x100)
    assert m.call(scratch).completed
    return m.x87_state()


def synthetic_checks(flavor):
    checks, env, f = {}, Env(synthetic()), entry(flavor)
    env.whole_x87(CONVERT, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    env.whole_x87(SUM, 'cdecl', 0, exact={'pop': 2, 'push': 1})
    m = Machine(synthetic(), 0x3000000, 0x40000)
    extended = (0x8000000000000001, 0x3fff)  # 1 + 2^-63: cannot be a double
    values = [extended, (0, 0x8000), (1, 0), (0x8000000000000000, 0x7fff),
              (0xc000000000000123, 0x7fff), (0x8000000000000001, 0xbfff)]
    lower = [(0xb17217f7d1cf79ac, 0x3ffe), (0x923456789abcdef1, 0x4002)]
    for i, value in enumerate(values):
        for count in range(1, 9):
            slots = [value] + [lower[j % 2] for j in range(count-1)]
            before = direct_load(m, slots, 0x33f)
            returned = m.call(CONVERT)
            expected, edx = m.x87_state(), m.register(UC_X86_REG_EDX)
            result, out = native(env, f, state(before), CONVERT)
            key = f'synthetic_{i}_depth{count}'
            checks[key] = (result.completed and not result.errors and out.returned == 1 and
                           out.eax == returned.eax and out.edx == edx and snapshot(out) == expected and
                           result.events[0][5] == ('extended-v1', *before))
    for rounding in range(4):
        for precision in (0, 2, 3):
            cw = 0x3f | precision << 8 | rounding << 10
            slots = [m.extended(2**-63), extended, *lower]
            before = direct_load(m, slots, cw)
            m.call(SUM)
            expected = m.x87_state()
            result, out = native(env, f, state(before, 2, 1), SUM)
            checks[f'sum_pc{precision}_rc{rounding}'] = result.completed and snapshot(out) == expected
    # This known extended result would be lost by a binary64 result channel.
    before = direct_load(m, [m.extended(2**-63), extended], 0x33f)
    result, out = native(env, f, state(before, 2, 1), SUM)
    checks['extended_result_bits'] = result.completed and snapshot(out)[2] == ((0x8000000000000002, 0x3fff),)

    valid = state(direct_load(m, [extended, *lower], 0x33f))
    for field, value in [('size', 0), ('version', 2), ('count', 9), ('count', 0), ('popCount', 0),
                         ('popCount', 2), ('pushCount', 2), ('returned', 1), ('eax', 1), ('edx', 1),
                         ('reserved0', 1), ('reserved1', 1), ('control', 0), ('control', 0x13f),
                         ('control', 0x10000), ('status', 0x10000)]:
        broken = NativeX87State.from_buffer_copy(valid)
        setattr(broken, field, value)
        result, _ = native(env, f, broken, CONVERT)
        checks[f'bad_{field}_{value}'] = not result.completed and result.fault == 5
    for i, field, value in [(0, 'reserved', 1), (0, 'signExponent', 0x10000), (7, 'significand', 1)]:
        broken = NativeX87State.from_buffer_copy(valid)
        setattr(broken.slots[i], field, value)
        result, _ = native(env, f, broken, CONVERT)
        checks[f'bad_slot_{i}_{field}'] = not result.completed and result.fault == 5
    for field, value in [('x87ArgumentCount', 0), ('x87ArgumentCount', 1), ('x87Argument', 1),
                         ('receiver', 1), ('receiver2', 1), ('argumentCount', 33), ('sourceReturnPC', 1),
                         ('sourceTransferVersion', 1), ('sourceTransferKind', 1), ('sourceTransferSite', 1),
                         ('sourceCallerFunction', 1), ('function', 0x401150)]:
        raw = NativeCall(); raw.function = CONVERT; raw.x87ArgumentCount = 2; raw.x87State = C.pointer(valid)
        setattr(raw, field, value)
        env._host.fault = 0
        env._native_call(None, C.pointer(raw))
        checks[f'bad_request_{field}_{value}'] = env._host.fault == 5
    raw = NativeCall(); raw.function = CONVERT; raw.x87ArgumentCount = 2
    env._host.fault = 0; env._native_call(None, C.pointer(raw))
    checks['missing_pointer'] = env._host.fault == 5
    # An unaware host, or a host corrupting a valid response, cannot publish success.
    original_callback = env._host.call
    for mode in ('ignored', 'live', 'cw', 'top', 'count', 'receipt', 'header', 'eax', 'request'):
        def corrupt(user, pointer):
            if mode == 'ignored': return 0
            value = env._native_call(user, pointer)
            s = pointer.contents.x87State.contents
            if mode == 'live': s.slots[0].significand ^= 1
            elif mode == 'cw': s.control ^= 0x400
            elif mode == 'top': s.status ^= 0x800
            elif mode == 'count': s.count = 0
            elif mode == 'receipt': s.returned = 0
            elif mode == 'header': s.popCount = 2
            elif mode == 'eax': s.eax ^= 1
            elif mode == 'request': pointer.contents.function ^= 1
            return value
        cb = CALLBACK(corrupt); env._host.call = cb
        result, _ = native(env, f, valid, CONVERT)
        checks[f'bad_host_{mode}'] = not result.completed and result.fault == 5
    env._host.call = original_callback
    # Wrong declaration is also checked against the callee's actual effect.
    env.x87_exact[CONVERT] = {'pop': 2, 'push': 0}
    broken = NativeX87State.from_buffer_copy(valid); broken.popCount = 2
    result, _ = native(env, f, broken, CONVERT)
    checks['wrong_effect_fails_after_original'] = result.fault == 5 and not result.completed
    return checks


def state_five_stack_result_checks(flavor):
    """Run unchanged rounding/cleanup/conversion spans at all three owned sites.

    Only the incoming ABI state is supplied. Neither CRT nor game instructions
    are patched or intercepted; probes stop before unrelated game operations.
    """
    env, checks = Env(claw()), {}
    for target in (0x4a4250, 0x4a4350):
        env.whole_x87(target, 'cdecl', 2, exact={'pop': 0, 'push': 1})
    env.whole_x87(0x4a30e0, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    producer = entry(flavor, 'claw_x87_stack_result_selftest_entry')
    consumer = entry(flavor)
    sites = {0x45f1ef: (0x4a4350, 0x45f204), 0x45f1fc: (0x4a4250, 0x45f204),
             0x45f26c: (0x4a4250, 0x45f274)}
    captures, visits = {}, []
    def capture(m, pc):
        captures[pc] = (m.x87_state(), m.register(UC_X86_REG_EAX),
                        m.register(UC_X86_REG_EDX), m.register(UC_X86_REG_ESP))
    for pc in set(sites) | {pc+5 for pc in sites} | {0x45f204, 0x45f274}:
        env.machine.observe(pc, capture)
    def stop(m, pc):
        capture(m, pc)
        raise Halt()
    for pc in (0x45f209, 0x45f279): env.machine.observe(pc, stop)
    # Confirm the original callees themselves execute on every probe.
    for target in (0x4a4250, 0x4a4350, 0x4a30e0):
        env.machine.observe(target, lambda m, pc: visits.append(pc))
    selected, incoming, before = 0, 0.0, None
    def prepare(m, pc):
        if pc == selected:
            m.set_x87_state(*before)
            m.write(m.register(UC_X86_REG_ESP), struct.pack('<d', incoming))
        capture(m, pc)
    for pc in sites: env.machine.observe(pc, prepare)
    values = (-100.1, -15.5, -1.0, math.nextafter(-1.0, 0.0), -0.0, 0.0,
              0.1, math.nextafter(1.0, 0.0), 1.0, math.nextafter(1.0, 2.0), 15.5, 100.1)
    lower = ((0x8000000000000001, 0x3fff), (0, 0x8000))
    for selected, (target, conversion) in sites.items():
        for index, incoming in enumerate(values):
            for depth in (0, 2):
                before = (0x23f, 0x4000 | ((index % 8) << 11), lower[:depth])
                env._begin_case(random.Random(index)); env._freeze()
                captures.clear(); visits.clear()
                result = env.run_original(selected, 0, ())
                saved, bodies = dict(captures), tuple(visits)
                key = f'state_five_{selected:x}_{index}_{depth}'
                checks[key + '_original'] = result.halted and not result.errors and bodies == (target, 0x4a30e0)
                if not checks[key + '_original']:
                    continue
                produced, _, _, after_sp = saved[selected+5]
                converted, eax, edx, final_sp = saved[conversion+5]
                words = struct.unpack('<II', struct.pack('<d', incoming))
                checks[key + '_cleanup'] = (saved[selected][3] == after_sp and
                    saved[conversion][3] == final_sp == after_sp + 8)
                checks[key + '_entry'] = saved[selected][0] == before
                checks[key + '_conversion_input'] = produced == saved[conversion][0]
                rounded = math.floor(incoming) if target == 0x4a4350 else math.ceil(incoming)
                checks[key + '_integer'] = (eax == rounded & 0xffffffff and
                    edx == (0xffffffff if rounded < 0 else 0) and converted[2] == before[2])
                actual, out = native_stack_result(env, producer, state(before, 0, 1), target, words)
                checks[key + '_producer'] = (actual.completed and not actual.errors and out.returned == 1 and
                    snapshot(out) == produced and actual.events[0][3] == words and
                    actual.events[0][5] == ('extended-v1', *before))
                # Pass the transported bits on, not a reconstructed expected float.
                out.popCount, out.pushCount = 1, 0
                out.returned = out.eax = out.edx = 0
                actual, out = native(env, consumer, out, 0x4a30e0)
                checks[key + '_consumer'] = (actual.completed and not actual.errors and
                    out.returned == 1 and snapshot(out) == converted and out.eax == eax and out.edx == edx)
    return checks


def original_checks(flavor):
    checks, env, f = {}, Env(claw()), entry(flavor)
    env.whole_x87(0x4a30e0, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    env.whole_x87(0x4f1b30, 'cdecl', 0, exact={'pop': 2, 'push': 1})
    captures, body = {}, []
    sites = {0x4f4504: (0x4a30e0, 1, 0), 0x4f451a: (0x4a30e0, 1, 0),
             0x4f4532: (0x4f1b30, 2, 1), 0x4f454b: (0x4f1b30, 2, 1),
             0x4f4537: (0x4a30e0, 1, 0), 0x4f4550: (0x4a30e0, 1, 0)}
    def capture(m, pc):
        captures[pc] = (m.x87_state(), m.register(UC_X86_REG_EAX), m.register(UC_X86_REG_EDX))
    for pc in set(sites) | {pc + 5 for pc in sites} | {0x4f44e8, 0x4f44fa, 0x4f4500, 0x4f4502, 0x4f4518}:
        env.machine.observe(pc, capture)
    env.machine.observe(0x4f1b52, lambda m, pc: body.append(pc))
    def stop(m, pc): raise Halt()
    env.machine.observe(0x4f4555, stop)
    dimensions = [(1, 2), (3, 7), (15, 17), (31, 33), (63, 65), (127, 129),
                  (255, 257), (1023, 1025), (65535, 65537), (2**30-1, 2**30+1)]
    arithmetic = entry(flavor, 'claw_x87_arithmetic_selftest_entry')
    for case, (width, height) in enumerate(dimensions):
        env._begin_case(random.Random(case))
        receiver = env.object(0x44, 'grid', fill=0)
        env._freeze(); captures.clear(); body.clear()
        original = env.run_original(0x4f4490, receiver, (0, 0, 31, 23, width, height))
        checks[f'original_path_{case}'] = original.halted and not original.errors and len(body) == 2
        saved = dict(captures)
        intermediate = (env.machine.initial_control_word, 0, ())
        for op, words, pc in [(1, (), 0x4f44e8), (3, (0, 0x40000000), None),
                              (4, (), 0x4f44fa), (1, (), None), (2, (width,), 0x4f4500),
                              (4, (), 0x4f4502), (5, (), 0x4f4504)]:
            intermediate = env.machine.x87_step(op, intermediate, words)
            if pc is not None:
                checks[f'intermediate_{case}_{pc:x}'] = intermediate == saved[pc][0]
        for pc, (target, pop, push) in sites.items():
            before = saved[pc][0]; after, eax, edx = saved[pc+5]
            result, out = native(env, f, state(before, pop, push), target)
            checks[f'original_{case}_{pc:x}'] = (result.completed and not result.errors and
                snapshot(out) == after and out.eax == eax and
                (target != 0x4a30e0 or out.edx == edx) and
                result.events[0][5] == ('extended-v1', *before))
        checks[f'ln2_extended_{case}'] = saved[0x4f44e8][0][2][0][0] & 0x7ff != 0
        env._begin_case(random.Random(case))
        output = env.object(12 * C.sizeof(NativeX87State), 'arithmetic snapshots', fill=0)
        env._freeze()
        result = env.run_native(arithmetic, 0x4010a0, 0, (width, height, output, env.machine.initial_control_word))
        checks[f'owned_arithmetic_{case}'] = result.completed and not result.errors
        for i, pc in enumerate(sorted(sites)):
            for phase in range(2):
                out = NativeX87State.from_buffer_copy(env.read(output + (i*2+phase)*C.sizeof(NativeX87State),
                                                              C.sizeof(NativeX87State)))
                checks[f'arithmetic_{case}_{pc:x}_{phase}'] = snapshot(out) == saved[pc+5*phase][0]
        # Compare the entry bits of every runtime call, too. This deliberately
        # does not compare test-only snapshot memory with the game's heap.
        checks[f'arithmetic_events_{case}'] = [event[5] for event in result.events] == [
            ('extended-v1', *saved[pc][0]) for pc in sorted(sites)]
    return checks


def volume_checks(flavor):
    """Original owned steps and both unchanged CRT boundaries, never a family gate."""
    env, checks = Env(claw()), {}
    env.whole_x87(0x4f1b30, 'cdecl', 0, exact={'pop': 2, 'push': 1})
    env.whole_x87(0x4a30e0, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    f = entry(flavor, 'claw_x87_volume_selftest_entry')
    captures, stored, body = {}, [], []
    sites = (0x4b3c3e, 0x4b3c40, 0x4b3c46, 0x4b3c4b, 0x4b3c51,
             0x4b3c57, 0x4b3c5d, 0x4b3c69, 0x4b3c73, 0x4b3c75, 0x4b3c7a)
    def capture(m, pc):
        captures[pc] = m.x87_state()
        if pc in (0x4b3c69, 0x4b3c73):
            # The store preceding the final load is an actual original m64 value.
            from unicorn.x86_const import UC_X86_REG_EBP
            stored.append(m.read(m.register(UC_X86_REG_EBP) - 8, 8))
    for pc in sites: env.machine.observe(pc, capture)
    env.machine.observe(0x4f1b52, lambda m, pc: body.append(pc))
    cases = [(n, (100.0, 1.0, 10.0, 2.0)) for n in
             (1, -1, 99, -99, 100, -100, 101, -101, 200, -200, 1000, -1000, 10000, -10000)]
    cases += [(100, (sys.float_info.max, 2.0, 10.0, 2.0)),
              (-100, (sys.float_info.max, 2.0, 10.0, 2.0)),
              (100, (2.0**-1022, 1.0, 10.0, 2.0)),
              (-100, (100.0, 1.0, 3.0, 0.5))]
    for index, (n, constants) in enumerate(cases):
        env._begin_case(random.Random(index))
        env.write(0x5134e8, struct.pack('<4d', *constants))
        output = env.object(10 * C.sizeof(NativeX87State), 'volume snapshots', fill=0)
        env._freeze(); captures.clear(); stored.clear(); body.clear()
        original = env.run_original(0x4b3bf0, 0, (n & 0xffffffff,))
        saved, saved_store = dict(captures), tuple(stored)
        checks[f'volume_original_{index}'] = original.completed and not original.errors and len(body) == 1
        result = env.run_native(f, 0x4010c0, 0, (n & 0xffffffff, 0x5134e8, output))
        checks[f'volume_native_{index}'] = result.completed and not result.errors and result.eax == original.eax
        pcs = [*sites[:7], 0x4b3c69 if n < 0 else 0x4b3c73,
               0x4b3c69 if n < 0 else 0x4b3c75, 0x4b3c7a]
        observed = []
        for i, pc in enumerate(pcs):
            out = NativeX87State.from_buffer_copy(env.read(output + i*C.sizeof(NativeX87State),
                                                          C.sizeof(NativeX87State)))
            observed.append(snapshot(out))
            checks[f'volume_step_{index}_{i}'] = snapshot(out) == saved[pc]
        checks[f'volume_boundaries_{index}'] = [event[5] for event in result.events] == [
            ('extended-v1', *saved[pc]) for pc in (0x4b3c46, pcs[8])]
        checks[f'volume_store_bits_{index}'] = (len(saved_store) == 1 and
            observed[7][2][0] == Machine.extended(struct.unpack('<d', saved_store[0])[0]))
        if index == 14:
            checks['volume_extended_counterexample'] = (
                observed[5][2][0] == (0x88925ffba153b000, 0x43ff) and
                observed[8][2][0] == (0x8925ffba153b4000, 0x43fb))
    return checks


def primitive_checks(flavor):
    env, f, checks = Env(synthetic()), entry(flavor, 'claw_x87_step_selftest_entry'), {}
    def run(s, op, operands=(0, 0)):
        env._begin_case(random.Random(42))
        inp = env.object(C.sizeof(s), 'input', data=bytes(s), fill=0)
        out = env.object(C.sizeof(s), 'output', fill=0); env._freeze()
        result = env.run_native(f, 0x4010b0, 0, (inp, op, *operands, out))
        return result, NativeX87State.from_buffer_copy(env.read(out, C.sizeof(s)))
    s = state((0x23f, 0, ()), 0, 1)
    result, out = run(s, 1)
    checks['ln2_exact_startup_profile'] = (result.completed and
        out.slots[0].significand == 0xb17217f7d1cf79ac and out.slots[0].signExponent == 0x3ffe)
    for cw in (0x13f, 0x23e, 0x123f, 0x237f):
        s = state((cw, 0, ()), 0, 1)
        result, _ = run(s, 1)
        checks[f'primitive_unsupported_cw_{cw:x}'] = not result.completed and result.fault == 5
    for op, n in [(0, 0), (14, 0), (4, 1), (5, 1), (6, 0), (12, 1), (1, 8), (2, 8), (3, 8)] + [(op, 0) for op in range(7, 14)]:
        s = state((0x23f, 0, tuple([Machine.extended(2.0)] * n)), 0, 0)
        result, _ = run(s, op)
        checks[f'primitive_bad_op{op}_depth{n}'] = not result.completed and result.fault == 5
    s = state((0x23f, 0, ()), 0, 1)
    for field, value in [('x87ArgumentCount', 0), ('x87ArgumentCount', 2), ('x87Operation', 99),
                         ('function', CONVERT), ('receiver', 1), ('receiver2', 1), ('stackPointer', 0x2004000),
                         ('argumentCount', 1), ('sourceTransferKind', 1), ('sourceReturnPC', 1)]:
        raw = NativeCall(); raw.x87ArgumentCount = 3; raw.x87Operation = 1; raw.x87State = C.pointer(s)
        setattr(raw, field, value); env._host.fault = 0
        env._native_call(None, C.pointer(raw))
        checks[f'primitive_bad_request_{field}_{value}'] = env._host.fault == 5
    # Independent register-indirect instructions, separate scratch memory and
    # explicit expected values. Never import the implementation opcode table.
    reference = Machine(synthetic(), 0x3000000, 0x40000)
    instructions = {7: 'd9e0', 8: 'dc28', 9: 'dc08', 10: 'dd18 dd00', 11: 'dc30',
                    12: 'd8c1', 13: 'dc00'}
    data, code = 0x2001200, 0x2001000
    vectors = [
        ('cancel', (0x8000000000000001, 0x3fff), 1.0),
        ('extended', Machine.extended(sys.float_info.max), 2.0),
        ('tie_even', (0x8000000000000400, 0x3fff), 1.0),
        ('tie_odd', (0x8000000000000c00, 0x3fff), 1.0),
        ('positive_zero', (0, 0), 0.0), ('negative_zero', (0, 0x8000), -0.0),
        ('subnormal', (1, 0), 1.0),
        ('binary64_subnormal', Machine.extended(2.0**-1074), 0.5),
        ('underflow_tie', (0x8000000000000000, 0x3bcc), 1.0),
        ('infinity', (0x8000000000000000, 0x7fff), float('inf')),
        ('quiet_nan', (0xc000000000000123, 0x7fff), 1.0),
        ('signaling_nan', (0x8000000000000123, 0x7fff), 1.0),
        ('unnormal', (0x4000000000000000, 0x3fff), 1.0),
        ('pseudo_denormal', (0x8000000000000000, 0), 1.0),
        ('operand_nan', Machine.extended(1.0), float('nan')),
        ('divide_zero', Machine.extended(-1.0), 0.0),
        ('add_cancel', (0x8000000000000001, 0x3fff), -1.0),
        ('add_tie_even', Machine.extended(1.0), 2.0**-53),
        ('add_tie_odd', (0x8000000000000800, 0x3fff), 2.0**-53),
        ('add_extended_range', Machine.extended(sys.float_info.max), sys.float_info.max),
    ]
    lower = ((0xb17217f7d1cf79ac, 0x3ffe), (0, 0x8000), (1, 0))
    for op, instruction in instructions.items():
        reference.write(code, b'\xb8' + struct.pack('<I', data) + bytes.fromhex(instruction) + b'\xc3')
        reference.uc.ctl_remove_cache(code, code + 0x100)
        for label, value, operand in vectors:
            words = struct.unpack('<II', struct.pack('<d', operand))
            for depth in range(2 if op == 12 else 1, 9):
                # Rotate through every physical TOP, retain condition/exception
                # flags and make every lower slot observable, including at depth 8.
                before = (0x23f, ((depth - 1) << 11) | 0x4521,
                          (value,) + ((Machine.extended(operand),) if op == 12 else ()) +
                          tuple(lower[i % len(lower)] for i in range(depth - (2 if op == 12 else 1))))
                reference.set_x87_state(*before)
                reference.write(data, struct.pack('<d', operand))
                assert reference.call(code).completed
                expected = reference.x87_state()
                result, out = run(state(before), op, words)
                checks[f'primitive_{op}_{label}_{depth}'] = (result.completed and not result.errors and
                    out.returned == 1 and snapshot(out) == expected and not result.events)
                if depth == (2 if op == 12 else 1):
                    exact = {
                        (7, 'negative_zero'): (0, 0),
                        (8, 'cancel'): (0x8000000000000000, 0xbfc0),
                        (9, 'extended'): (0xfffffffffffff800, 0x43ff),
                        (10, 'tie_even'): (0x8000000000000000, 0x3fff),
                        (10, 'tie_odd'): (0x8000000000001000, 0x3fff),
                        (10, 'negative_zero'): (0, 0x8000),
                        (10, 'underflow_tie'): (0, 0),
                    }.get((op, label))
                    if op in (12, 13):
                        exact = {
                            'add_cancel': (0x8000000000000000, 0x3fc0),
                            'add_tie_even': Machine.extended(1.0),
                            'add_tie_odd': (0x8000000000001000, 0x3fff),
                            'add_extended_range': (0xfffffffffffff800, 0x43ff),
                            'negative_zero': (0, 0x8000),
                        }.get(label)
                    if exact is not None:
                        checks[f'primitive_known_{op}_{label}'] = snapshot(out)[2][0] == exact
        # New operations must reject bad arity, stack effects and stale output.
        for field, value in [('argumentCount', 1), ('popCount', 0), ('pushCount', 0),
                             ('returned', 1), ('eax', 1), ('edx', 1), ('control', 0x123f),
                             ('reserved0', 1), ('status', 0x10000)]:
            s = state((0x23f, 0, (Machine.extended(1.0),) * (2 if op == 12 else 1)), 1, 1)
            raw = NativeCall(); raw.x87ArgumentCount = 3; raw.x87Operation = op; raw.x87State = C.pointer(s)
            raw.argumentCount = 2 if op in (8, 9, 11, 13) else 0
            setattr(raw if field == 'argumentCount' else s, field, value)
            env._host.fault = 0; env._native_call(None, C.pointer(raw))
            checks[f'primitive_{op}_invalid_{field}'] = env._host.fault == 5
    # The checked C++ client must also reject hosts that ignore new operations
    # or corrupt TOP, lower slots, the receipt, or the immutable request.
    original_callback = env._host.call
    for op in instructions:
        for mode in ('ignored', 'lower', 'top', 'receipt', 'request', 'eax', 'edx'):
            def corrupt(user, pointer):
                if mode == 'ignored': return 0
                value = env._native_call(user, pointer)
                s = pointer.contents.x87State.contents
                if mode == 'lower': s.slots[1].significand ^= 1
                elif mode == 'top': s.status ^= 0x800
                elif mode == 'receipt': s.returned = 0
                elif mode == 'request': pointer.contents.x87Operation ^= 1
                elif mode == 'eax': s.eax = value = 1
                elif mode == 'edx': s.edx = 1
                return value
            cb = CALLBACK(corrupt); env._host.call = cb
            result, _ = run(state((0x23f, 0, (Machine.extended(1.0), *lower))), op)
            checks[f'primitive_{op}_bad_host_{mode}'] = not result.completed and result.fault == 5
    env._host.call = original_callback
    # Primitive evaluation must not borrow or modify the guest machine's FPU,
    # registers, heap, code, or stack; it has an independent fixed instruction VM.
    m = env.machine
    old = m.uc.context_save(); memory = m.read(0x3000000, 0x1000)
    before = m.x87_state(), m.register(UC_X86_REG_EAX), m.register(UC_X86_REG_EDX)
    m.x87_step(1, (0x23f, 0, ()))
    checks['primitive_isolation'] = (before == (m.x87_state(), m.register(UC_X86_REG_EAX),
        m.register(UC_X86_REG_EDX)) and m.read(0x3000000, 0x1000) == memory)
    m.uc.context_restore(old)
    return checks


def addition_checks(flavor):
    """Unchanged dialog additions followed by the real __ftol, with no fixtures.

    Supply only incoming CPU/memory state at each owned addition and stop after
    its conversion returns. Expected SW and extended bits come from the original
    instruction span, independently of the primitive table and native client.
    """
    env, checks = Env(claw()), {}
    env.whole_x87(0x4a30e0, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    step = entry(flavor, 'claw_x87_step_selftest_entry')
    consume = entry(flavor)
    captures, visits = {}, []
    selected, before, operand = 0, None, 0.0
    sites = {0x4e281a: (12, 0x4e281c), 0x4e2832: (13, 0x4e2836)}
    def prepare(m, pc):
        if pc != selected: return
        m.set_x87_state(*before)
        if pc == 0x4e2832:
            m.write(m.register(UC_X86_REG_ESP) + 0x30, struct.pack('<d', operand))
    def capture(m, pc):
        captures[pc] = (m.x87_state(), m.register(UC_X86_REG_EAX), m.register(UC_X86_REG_EDX))
    def stop(m, pc):
        capture(m, pc)
        raise Halt()
    for pc, (_, conversion) in sites.items():
        env.machine.observe(pc, prepare)
        env.machine.observe(conversion, capture)
        env.machine.observe(conversion + 5, stop)
    env.machine.observe(0x4a30e0, lambda m, pc: visits.append(pc))
    vectors = [
        ((0x8000000000000001, 0x3fff), -1.0),
        (Machine.extended(1.0), 2.0**-53),
        ((0x8000000000000800, 0x3fff), 2.0**-53),
        (Machine.extended(sys.float_info.max), sys.float_info.max),
        ((0, 0x8000), -0.0),
        ((1, 0), 0.0),
        ((0xc000000000000123, 0x7fff), 1.0),
        (Machine.extended(17.75), -3.5),
        (Machine.extended(1.0), -1.0),  # ST(1) below carries an extra extended bit.
    ]
    lower = ((0xb17217f7d1cf79ac, 0x3ffe), (0x8000000000000001, 0x3fff), (0, 0x8000))
    for selected, (op, conversion) in sites.items():
        for index, (value, operand) in enumerate(vectors):
            for depth in ((2, 8) if op == 12 else (1, 8)):
                for top in range(8):
                    addend = (0x8000000000000001, 0xbfff) if index == 8 else Machine.extended(operand)
                    live = (value,) + ((addend,) if op == 12 else ())
                    live += tuple(lower[i % len(lower)] for i in range(depth - len(live)))
                    before = (0x23f, (top << 11) | (0x4721 if index % 2 else 0), live)
                    env._begin_case(random.Random(index)); env._freeze()
                    captures.clear(); visits.clear()
                    original = env.run_original(selected, 0, ())
                    saved = dict(captures)
                    key = f'dialog_add_{op}_{index}_{depth}_{top}'
                    checks[key + '_original'] = (original.halted and not original.errors and
                                                visits == [0x4a30e0] and len(saved) == 2)
                    if not checks[key + '_original']: continue
                    expected, _, _ = saved[conversion]
                    converted, eax, edx = saved[conversion + 5]
                    s = state(before, 1, 1)
                    words = struct.unpack('<II', struct.pack('<d', operand))
                    env._begin_case(random.Random(index))
                    inp = env.object(C.sizeof(s), 'addition input', data=bytes(s), fill=0)
                    out = env.object(C.sizeof(s), 'addition output', fill=0); env._freeze()
                    result = env.run_native(step, 0x4010b0, 0, (inp, op, *words, out))
                    actual = NativeX87State.from_buffer_copy(env.read(out, C.sizeof(s)))
                    checks[key + '_step'] = (result.completed and not result.errors and not result.events and
                        actual.returned == 1 and snapshot(actual) == expected and
                        expected[0] == before[0] and expected[2][1:] == before[2][1:] and
                        (expected[1] >> 11) & 7 == top)
                    if op == 12 and index == 8:
                        checks[key + '_extended_addend'] = expected[2][0] == (0x8000000000000000, 0xbfc0)
                    actual.popCount, actual.pushCount = 1, 0
                    actual.returned = actual.eax = actual.edx = 0
                    result, actual = native(env, consume, actual, 0x4a30e0)
                    checks[key + '_conversion'] = (result.completed and not result.errors and
                        snapshot(actual) == converted and actual.eax == eax and actual.edx == edx and
                        result.events[0][5] == ('extended-v1', *expected))
    return checks


def metadata_checks():
    sys.path.insert(0, str(build.ROOT))
    try:
        from tools.claw import manifest
    finally:
        sys.path.pop(0)
    valid = {'kind': 'whole', 'convention': 'cdecl', 'argc': 0, 'x87_exact': {'pop': 2, 'push': 1}}
    spec = json.loads(Path(__file__).with_name('family.json').read_text())
    def errors(declaration):
        spec['callees']['0x40107f'] = declaration
        return manifest.validate(spec)
    def execute(path):
        # Synthetic case files use the public clawparity import spelling.
        sys.path.insert(0, str(build.ROOT / 'Tests'))
        try:
            return runner.run(path, original_only=True)
        finally:
            sys.path.pop(0)
    checks = {'metadata_valid': not errors(valid)}
    producer = {**valid, 'argc': 2, 'x87_exact': {'pop': 0, 'push': 1}}
    checks['metadata_producer_valid'] = not errors(producer)
    balanced = {**valid, 'convention': 'thiscall', 'argc': 2, 'x87_exact': {'pop': 0, 'push': 0}}
    checks['metadata_balanced_valid'] = not errors(balanced)
    bad = [{**valid, 'x87_exact': value} for value in (None, {}, {'pop': True, 'push': 0},
           {'pop': -1, 'push': 1}, {'pop': 0, 'push': 2},
           {'pop': 0, 'push': True}, {'pop': 0.0, 'push': 1},
           {'pop': 9, 'push': 0}, {'pop': 2, 'push': 2},
           {'pop': 2, 'push': 1, 'extra': 1}, {'pop': '2', 'push': 0})]
    bad += [{**valid, k: v} for k,v in [('x87_args', 1), ('source_context', {}), ('compiler_context', {}),
            ('kind', 'fixture'), ('convention', 'fastcall'), ('argc', True), ('argc', 33)]]
    with tempfile.TemporaryDirectory(dir=build.ROOT / 'work', prefix='exact-x87-metadata-') as directory:
        path = Path(directory) / 'family.json'
        errors(valid); path.write_text(json.dumps(spec))
        checks['metadata_valid_runner'] = execute(path)['status'] == 'pass'
        errors(producer); path.write_text(json.dumps(spec))
        checks['metadata_producer_valid_runner'] = execute(path)['status'] == 'pass'
        errors(balanced); path.write_text(json.dumps(spec))
        checks['metadata_balanced_valid_runner'] = execute(path)['status'] == 'pass'
        for i, declaration in enumerate(bad):
            rejected = bool(errors(declaration))
            path.write_text(json.dumps(spec))
            checks[f'metadata_bad_{i}'] = rejected and execute(path)['status'] == 'error'

    return checks


def checks(flavor='O2'):
    return {**synthetic_checks(flavor), **stack_result_checks(flavor), **state_five_stack_result_checks(flavor),
            **primitive_checks(flavor), **addition_checks(flavor), **original_checks(flavor),
            **volume_checks(flavor), **metadata_checks()}


def sanitized_checks():
    prefix, environment = build.sanitized_python()
    if prefix is None: return {'passed': False, 'detail': 'sanitizer unavailable'}
    done = subprocess.run(prefix + ['-m', 'Tests.clawparity.selftest.x87_exact', '--flavor', 'sanitize'],
                          env=environment, cwd=build.ROOT, capture_output=True, text=True, timeout=120)
    try: result = json.loads(done.stdout)
    except ValueError: result = {'passed': False, 'detail': done.stderr[-3000:]}
    result['passed'] = done.returncode == 0 and result.get('passed') is True
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--flavor', choices=build.FLAVORS, default='O2')
    parser.add_argument('--all', action='store_true'); args = parser.parse_args()
    if args.all:
        results = {}
        for flavor in ('O0', 'O2'):
            found = checks(flavor)
            results[flavor] = {'checked': len(found), 'failed': [k for k,v in found.items() if not v],
                               'passed': all(found.values())}
        results['sanitize'] = sanitized_checks()
        passed = all(v['passed'] for v in results.values())
        print(json.dumps({'passed': passed, 'results': results}))
    else:
        found = checks(args.flavor); passed = all(found.values())
        print(json.dumps({'passed': passed, 'checked': len(found), 'failed': [k for k,v in found.items() if not v]}))
    raise SystemExit(not passed)
