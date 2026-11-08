"""Bounded FSIN/FCOS transport controls, including unchanged Omar call chains.

This checks parity with the reference interpreter, not hardware transcendental
accuracy. No game body, arithmetic fixture, or host-libm result is used as a
native implementation. All original instructions/data come from hash-checked
claw(); independent synthetic opcodes are only single-instruction controls.
"""
import ctypes as C
import json
import math
import random
import struct
import subprocess

from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EDX,
                               UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI)
from .. import build
from ..env import Env, Halt, NativeCall, CALLBACK
from ..kernel import Machine
from ..program import claw
from .x87_exact import synthetic, entry, state, snapshot, native

E = Machine.extended
SIN, COS = 22, 23
LOWER = ((0x8000000000000001, 0xbfff), (0, 0x8000), (1, 0),
         (0xb17217f7d1cf79ac, 0x3ffe), (0xc000000000000123, 0x7fff),
         (0x923456789abcdef1, 0x4002), (0xffffffffffffffff, 0x403d))
VECTORS = (
    ('zero', (0, 0)), ('negative_zero', (0, 0x8000)),
    ('one', E(1.0)), ('negative_one', E(-1.0)),
    ('extended_one', (0x8000000000000001, 0x3fff)),
    ('extended_half_pi', (0xc90fdaa22168c235, 0x3fff)),
    ('half_pi_below', E(math.nextafter(math.pi / 2, 0))),
    ('half_pi_above', E(math.nextafter(math.pi / 2, math.inf))),
    ('pi_below', E(math.nextafter(math.pi, 0))),
    ('pi_above', E(math.nextafter(math.pi, math.inf))),
    ('range_below', (0xffffffffffffffff, 0x403d)),
    ('range_equal', (1 << 63, 0x403e)),
    ('range_extended_above', ((1 << 63) + 1, 0x403e)),
    ('range_double_above', E(math.nextafter(2.0**63, math.inf))),
    ('range_negative_equal', (1 << 63, 0xc03e)),
    ('range_negative_above', E(-math.nextafter(2.0**63, math.inf))),
    ('infinity', (1 << 63, 0x7fff)), ('negative_infinity', (1 << 63, 0xffff)),
    ('quiet_nan', (0xc000000000000123, 0x7fff)),
    ('signaling_nan', (0x8000000000000123, 0xffff)),
    ('subnormal', (1, 0)), ('negative_tiny', (1 << 63, 0x8001)),
    ('unnormal', (0x4000000000000000, 0x3fff)),
    ('pseudo_denormal', (1 << 63, 0)),
)


def client(env, flavor):
    f = entry(flavor, 'claw_x87_register_selftest_entry')

    def run(s, op, words=()):
        env._begin_case(random.Random(87))
        inp = env.object(C.sizeof(s), 'input', data=bytes(s), fill=0)
        out = env.object(C.sizeof(s), 'output', fill=0)
        env._freeze()
        padded = tuple(words) + (0,) * (2 - len(words))
        result = env.run_native(f, 0x4010e0, 0, (inp, op, *padded, out, len(words)))
        return result, type(s).from_buffer_copy(env.read(out, C.sizeof(s)))
    return run


def primitive_checks(flavor):
    checks, env = {}, Env(synthetic())
    run = client(env, flavor)
    reference = Machine(synthetic(), 0x3000000, 0x40000)
    # Independent opcode selection; never import the implementation's table.
    reference.write(0x2001000, bytes.fromhex('d9fe c3'))
    reference.write(0x2001010, bytes.fromhex('d9ff c3'))
    seen = {}
    for op, pc in ((SIN, 0x2001000), (COS, 0x2001010)):
        for depth in range(1, 9):
            for index, (name, value) in enumerate(VECTORS):
                top = index % 8
                before = (0x23f, (top << 11) | (0x4721 if index & 1 else 0),
                          (value, *LOWER[:depth - 1]))
                reference.set_x87_state(*before)
                assert reference.call(pc).completed
                expected = reference.x87_state()
                result, out = run(state(before), op)
                checks[f'primitive_{op}_{depth}_{name}'] = (
                    result.completed and not result.errors and not result.events and
                    out.returned == 1 and out.popCount == out.pushCount == 1 and
                    out.eax == out.edx == 0 and snapshot(out) == expected and
                    expected[0] == before[0] and expected[1] >> 11 & 7 == top and
                    len(expected[2]) == depth and expected[2][1:] == before[2][1:])
                seen.setdefault((op, depth), set()).add(top)
    checks['all_depths_all_tops'] = len(seen) == 16 and all(len(v) == 8 for v in seen.values())
    # Hand expectations independently pin signs, C2 clearing, and unchanged
    # out-of-range ST(0). The reference accepts exactly 2**63, unlike hardware.
    for op in (SIN, COS):
        for sign in (0, 0x8000):
            result, out = run(state((0x23f, 0x4521, ((0, sign), LOWER[0]))), op)
            checks[f'known_zero_{op}_{sign}'] = (result.completed and
                snapshot(out) == (0x23f, 0x4121, (((0, sign) if op == SIN else E(1.0)), LOWER[0])))
        for value in (E(math.nextafter(2.0**63, math.inf)), E(-math.nextafter(2.0**63, math.inf)),
                      E(2.0**64), (1 << 63, 0x7fff)):
            before = (0x23f, 0x4121, (value, LOWER[0]))
            result, out = run(state(before), op)
            checks[f'known_range_{op}_{value}'] = result.completed and snapshot(out) == (0x23f, 0x4521, before[2])
        for value in (E(2.0**63), E(-2.0**63)):
            result, out = run(state((0x23f, 0x4521, (value,))), op)
            checks[f'reference_endpoint_{op}_{value}'] = (result.completed and not out.status & 0x400 and
                                                       snapshot(out)[2] != (value,))
    checks.update(rejection_checks(env, run))
    return checks


def rejection_checks(env, run):
    checks = {}
    before = (0x23f, 0x1821, (E(0.75), *LOWER[:2]))
    for op in (SIN, COS):
        for label, s, words in (
            ('empty', state((0x23f, 0, ())), ()),
            ('one_operand', state(before), (0,)),
            ('two_operands', state(before), (0, 0)),
            ('other_precision', state((0x33f, before[1], before[2])), ()),
            ('other_rounding', state((0xa3f, before[1], before[2])), ()),
        ):
            result, _ = run(s, op, words)
            checks[f'client_reject_{op}_{label}'] = not result.completed and result.fault == 5
        for field, value in (('size', 0), ('version', 2), ('count', 9), ('reserved1', 1), ('status', 0x10000)):
            s = state(before); setattr(s, field, value)
            result, _ = run(s, op)
            checks[f'client_reject_{op}_{field}'] = not result.completed and result.fault == 5

        def raw_request(field=None, value=None, raw_field=False):
            s = state(before, 1, 1)
            raw = NativeCall(); raw.x87ArgumentCount = 3; raw.x87Operation = op
            raw.x87State = C.pointer(s)
            if field: setattr(raw if raw_field else s, field, value)
            env._host.fault = 0
            env._native_call(None, C.pointer(raw))
            return env._host.fault, s
        fault, out = raw_request()
        checks[f'raw_accept_{op}'] = fault == 0 and out.returned == 1
        for field, value in (('returned', 1), ('eax', 1), ('edx', 1), ('popCount', 0), ('pushCount', 0),
                             ('control', 0x33f), ('count', 0), ('reserved0', 1)):
            fault, _ = raw_request(field, value)
            checks[f'raw_reject_{op}_{field}'] = fault == 5
        for field, value in (('argumentCount', 1), ('function', 0x464051), ('receiver', 1),
                             ('receiver2', 1), ('stackPointer', 0x2008000), ('x87Argument', 1.0),
                             ('x87ArgumentCount', 2), ('sourceReturnPC', 0x464053),
                             ('sourceTransferVersion', 1), ('x87Operation', 24)):
            fault, _ = raw_request(field, value, True)
            checks[f'raw_reject_{op}_{field}'] = fault == 5
        original = env._host.call
        for mode in ('ignored', 'receipt', 'lower', 'top', 'depth', 'control', 'request',
                     'eax', 'edx', 'pop', 'push', 'inactive', 'reserved', 'status'):
            def corrupt(user, pointer, mode=mode):
                if mode == 'ignored': return 0
                value = env._native_call(user, pointer)
                s = pointer.contents.x87State.contents
                if mode == 'receipt': s.returned = 0
                elif mode == 'lower': s.slots[1].significand ^= 1
                elif mode == 'top': s.status ^= 0x800
                elif mode == 'depth': s.count -= 1
                elif mode == 'control': s.control = 0x33f
                elif mode == 'request': pointer.contents.x87Operation ^= 1
                elif mode == 'eax': value = 1
                elif mode == 'edx': s.edx = 1
                elif mode == 'pop': s.popCount = 0
                elif mode == 'push': s.pushCount = 0
                elif mode == 'inactive': s.slots[7].significand = 1
                elif mode == 'reserved': s.slots[0].reserved = 1
                elif mode == 'status': s.status |= 0x10000
                return value
            callback = CALLBACK(corrupt); env._host.call = callback
            try: result, _ = run(state(before), op)
            finally: env._host.call = original
            checks[f'bad_host_{op}_{mode}'] = not result.completed and result.fault == 5
    for op in (0, 24, 0xff, 0xffffffff):
        result, _ = run(state(before), op)
        checks[f'unknown_{op}'] = not result.completed and result.fault == 5
    # The primitive engine cannot change original memory or CPU state.
    m = env.machine
    saved = m.x87_state(), m.read(0x3000000, 0x1000), m.register(UC_X86_REG_EAX)
    for op in (SIN, COS): m.x87_step(op, before)
    checks['isolated_engine'] = saved == (m.x87_state(), m.read(0x3000000, 0x1000), m.register(UC_X86_REG_EAX))
    return checks


def original_site_checks(flavor):
    """Run each untouched two-byte instruction, with raw extended inputs."""
    env, checks = Env(claw()), {}
    run = client(env, flavor)
    m = Machine(claw(), 0x3000000, 0x40000)
    sites = ((0x464051, COS), (0x46406d, SIN), (0x4641e8, SIN), (0x46420a, COS))
    def stop(machine, pc): raise Halt()
    for pc, _ in sites: m.observe(pc + 2, stop)
    for pc, op in sites:
        for index, (name, angle) in enumerate(VECTORS):
            before = (0x23f, ((index % 8) << 11) | 0x4721, (angle, angle, *LOWER[:2]))
            m.set_x87_state(*before)
            try:
                m.call(pc)
                raise AssertionError('original probe missed its stop')
            except Halt: pass
            expected = m.x87_state()
            result, out = run(state(before), op)
            checks[f'original_site_{pc:x}_{name}'] = (result.completed and not result.errors and
                snapshot(out) == expected and expected[2][1:] == before[2][1:])
    return checks


def original_chain_checks(flavor):
    """Both ring sequences: angle scales, trig, radius, optional subtraction,
    and two real __ftol calls. Compare every intermediate and exact call input.
    The native side carries its own previous result forward at every step.
    """
    env, checks = Env(claw()), {}
    env.whole_x87(0x4a30e0, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    run, convert = client(env, flavor), entry(flavor)
    m = Machine(claw(), 0x3000000, 0x40000)
    def words(address): return struct.unpack('<II', m.read(address, 8))
    first_scale, second_scale, radius = (words(p) for p in (0x50eab8, 0x50eac8, 0x50ead0))
    owner, world, record, ring, render = (0x3000000 + n * 0x1000 for n in range(5))
    captures, visits = {}, []
    def capture(machine, pc):
        captures[pc] = (machine.x87_state(), machine.register(UC_X86_REG_EAX), machine.register(UC_X86_REG_EDX))
    def stop(machine, pc):
        capture(machine, pc)
        raise Halt()
    updates = [0x46403b, 0x464040, 0x464046, 0x46404c, 0x46404f, 0x464051, 0x464053,
               0x464059, 0x46405b, 0x464060, 0x464068, 0x46406b, 0x46406d, 0x46406f, 0x464075, 0x464077]
    creates = [0x4641d3, 0x4641d6, 0x4641de, 0x4641e6, 0x4641e8, 0x4641ff, 0x464205, 0x46420a, 0x464212, 0x464218]
    for pc in updates + creates: m.observe(pc, capture)
    for pc in (0x46407c, 0x46421d): m.observe(pc, stop)
    m.observe(0x4a30e0, lambda machine, pc: visits.append(machine.x87_state()))
    angles = (tuple(float(n) for n in range(0, 297, 33)) +
              (-360.0, -90.0, -0.0, 90.0, 180.0, 360.0, 89.999999, 90.000001,
               math.nextafter(90.0, 0), math.nextafter(90.0, math.inf),
               math.nextafter(180.0, 0), math.nextafter(180.0, math.inf), 1e-15, 1e15))
    integer_results = {}
    for kind in ('update', 'create'):
        for index, angle in enumerate(angles):
            angle_words = struct.unpack('<II', struct.pack('<d', angle))
            x, y = 101, -37
            sequence = (
                [(0x46403b, 3, angle_words), (0x464040, 9, first_scale), (0x464046, 9, second_scale),
                 (0x46404c, 2, (x,)), (0x46404f, 0x101, ()), (0x464051, COS, ()),
                 (0x464053, 9, radius), (0x464059, 0x1a9, ()), (0x46405b, None, ()),
                 (0x464068, 2, (y & 0xffffffff,)), (0x46406b, 0x109, ()), (0x46406d, SIN, ()),
                 (0x46406f, 9, radius), (0x464075, 0x1a9, ()), (0x464077, None, ())]
                if kind == 'update' else
                [(0x4641d3, 3, angle_words), (0x4641d6, 9, first_scale), (0x4641de, 9, second_scale),
                 (0x4641e6, 0x100, ()), (0x4641e8, SIN, ()), (0x4641ff, 9, radius),
                 (0x464205, None, ()), (0x46420a, COS, ()), (0x464212, 9, radius), (0x464218, None, ())])
            finish = 0x46407c if kind == 'update' else 0x46421d
            # Inherited lower slots are deliberately extended-only and signed zero.
            before = (0x23f, ((index % 8) << 11) | (0x4521 if index & 1 else 0), LOWER[:2])
            m.write(owner + 0xc, struct.pack('<I', world))
            m.write(owner + 0x12c, struct.pack('<I', render))
            m.write(world + 0x4c, struct.pack('<ii', x, y))
            m.write(record, struct.pack('<d', angle))
            m.write(record + 0x100, struct.pack('<I', ring))
            for reg, value in ((UC_X86_REG_EDI, owner), (UC_X86_REG_EBX, record),
                               (UC_X86_REG_ESI, record + (0x100 if kind == 'update' else 8)),
                               (UC_X86_REG_EAX, 0), (UC_X86_REG_EBP, 0)):
                m.uc.reg_write(reg, value)
            m.set_x87_state(*before); captures.clear(); visits.clear()
            try:
                m.call(sequence[0][0])
                raise AssertionError('original chain missed its stop')
            except Halt: pass
            key = f'chain_{kind}_{index}'
            checks[key + '_original'] = (len(visits) == 2 and captures[finish][0][2] == before[2])
            fp, conversions = state(before), []
            for j, (pc, op, operands) in enumerate(sequence):
                checks[f'{key}_{pc:x}_input'] = snapshot(fp) == captures[pc][0]
                if op is None:
                    fp.popCount, fp.pushCount = 1, 0
                    fp.returned = fp.eax = fp.edx = 0
                    actual, fp = native(env, convert, fp, 0x4a30e0)
                    expected, eax, edx = captures[pc + 5]
                    checks[f'{key}_{pc:x}_convert'] = (actual.completed and not actual.errors and
                        fp.eax == eax and fp.edx == edx and snapshot(fp) == expected and
                        len(actual.events) == 1 and actual.events[0][5] == ('extended-v1', *captures[pc][0]))
                    conversions.append((fp.eax, fp.edx))
                else:
                    actual, fp = run(fp, op, operands)
                    checks[f'{key}_{pc:x}_step'] = actual.completed and not actual.errors
                next_pc = sequence[j + 1][0] if j + 1 < len(sequence) else finish
                checks[f'{key}_{pc:x}_output'] = snapshot(fp) == captures[next_pc][0]
            checks[key + '_lower'] = snapshot(fp)[2] == before[2]
            integer_results[kind, angle] = tuple(conversions)
    # The sensitive angles straddle actual integer conversion boundaries.
    for kind in ('update', 'create'):
        checks[f'sensitive_integer_{kind}'] = integer_results[kind, 90.000001] != integer_results[kind, 89.999999]
    # A rounded __ftol operand would hide this extended-only fractional bit.
    exact = (0xffffffffffffffff, 0x3ffe)  # 1 - 2**-64
    outputs = []
    for value in (exact, E(1.0)):
        result, fp = native(env, convert, state((0x23f, 0x1821, (value, *LOWER[:2]))), 0x4a30e0)
        checks[f'exact_ftol_{value}'] = result.completed and snapshot(fp)[2] == LOWER[:2]
        outputs.append(fp.eax)
    checks['rounding_before_ftol_is_detectable'] = outputs == [0, 1]
    return checks


def checks(flavor='O2'):
    return {**primitive_checks(flavor), **original_site_checks(flavor), **original_chain_checks(flavor)}


def sanitized_checks():
    prefix, environment = build.sanitized_python()
    if prefix is None: return {'passed': False, 'detail': 'sanitizer unavailable'}
    done = subprocess.run(prefix + ['-m', 'Tests.clawparity.selftest.x87_trigonometry', '--flavor', 'sanitize'],
                          env=environment, cwd=build.ROOT, capture_output=True, text=True, timeout=300)
    try: result = json.loads(done.stdout)
    except ValueError: result = {'passed': False, 'detail': done.stderr[-3000:]}
    result['passed'] = done.returncode == 0 and result.get('passed') is True
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--flavor', choices=build.FLAVORS, default='O2')
    parser.add_argument('--all', action='store_true'); args = parser.parse_args()
    results = {}
    for flavor in (('O0', 'O2') if args.all else (args.flavor,)):
        found = checks(flavor)
        results[flavor] = {'checked': len(found), 'failed': [k for k, v in found.items() if not v],
                           'passed': all(found.values())}
    if args.all: results['sanitize'] = sanitized_checks()
    passed = all(v['passed'] for v in results.values())
    print(json.dumps({'passed': passed, 'results': results}))
    raise SystemExit(not passed)
