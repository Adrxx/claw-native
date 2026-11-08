"""Register-indexed, compare and m64 store x87 primitives.

Every expectation comes from an independently assembled instruction in a
separate reference interpreter (register-indirect memory forms, separate
scratch memory) or from explicit hand values. The implementation opcode table
is never imported: operation numbers and encodings below are written from the
public ClawRuntime.h contract and the Intel SDM opcode map.
"""
import ctypes as C
import json
import random
import struct
import subprocess
import sys

from .. import build
from ..env import Env, NativeCall, CALLBACK
from ..kernel import Machine
from .x87_exact import synthetic, entry, state, snapshot

E = Machine.extended
ENTRY = 0x4010e0
CODE, DATA = 0x2001000, 0x2001200

# Non-indexed: operation -> (instruction with EAX = DATA, operand words, pop, push, minimum, stores)
SINGLE = {
    14: ('ded9', 0, 2, 0, 2, False),    # FCOMPP
    15: ('d9fa', 0, 1, 1, 1, False),    # FSQRT
    16: ('d9e1', 0, 1, 1, 1, False),    # FABS
    17: ('dc10', 2, 0, 0, 1, False),    # FCOM m64 [eax]
    18: ('dc18', 2, 1, 0, 1, False),    # FCOMP m64 [eax]
    19: ('dc20', 2, 1, 1, 1, False),    # FSUB m64 [eax]
    20: ('dd10', 0, 1, 1, 1, True),     # FST m64 [eax]
    21: ('dd18', 0, 1, 0, 1, True),     # FSTP m64 [eax]
}
# Register forms: base -> (name, first byte, second byte for ST(0), effect(k))
FORMS = {
    0x100: ('fld', 0xd9, 0xc0, lambda k: (0, 1)),
    0x108: ('fxch', 0xd9, 0xc8, lambda k: (k, k)),
    0x110: ('fst', 0xdd, 0xd0, lambda k: (k, k)),
    0x118: ('fstp', 0xdd, 0xd8, lambda k: (k, k - 1)),
    0x120: ('fcom', 0xd8, 0xd0, lambda k: (0, 0)),
    0x128: ('fcomp', 0xd8, 0xd8, lambda k: (1, 0)),
    0x130: ('fadd_to0', 0xd8, 0xc0, lambda k: (1, 1)),
    0x138: ('fmul_to0', 0xd8, 0xc8, lambda k: (1, 1)),
    0x140: ('fsub_to0', 0xd8, 0xe0, lambda k: (1, 1)),
    0x148: ('fsubr_to0', 0xd8, 0xe8, lambda k: (1, 1)),
    0x150: ('fdiv_to0', 0xd8, 0xf0, lambda k: (1, 1)),
    0x158: ('fdivr_to0', 0xd8, 0xf8, lambda k: (1, 1)),
    0x160: ('fadd_toi', 0xdc, 0xc0, lambda k: (k, k)),
    0x168: ('fmul_toi', 0xdc, 0xc8, lambda k: (k, k)),
    0x170: ('fsubr_toi', 0xdc, 0xe0, lambda k: (k, k)),
    0x178: ('fsub_toi', 0xdc, 0xe8, lambda k: (k, k)),
    0x180: ('fdivr_toi', 0xdc, 0xf0, lambda k: (k, k)),
    0x188: ('fdiv_toi', 0xdc, 0xf8, lambda k: (k, k)),
    0x190: ('faddp', 0xde, 0xc0, lambda k: (k, k - 1)),
    0x198: ('fmulp', 0xde, 0xc8, lambda k: (k, k - 1)),
    0x1a0: ('fsubrp', 0xde, 0xe0, lambda k: (k, k - 1)),
    0x1a8: ('fsubp', 0xde, 0xe8, lambda k: (k, k - 1)),
    0x1b0: ('fdivrp', 0xde, 0xf0, lambda k: (k, k - 1)),
    0x1b8: ('fdivp', 0xde, 0xf8, lambda k: (k, k - 1)),
}


def operations():
    """operation -> (label, instruction hex, words, pop, push, minimum, stores)."""
    found = {op: (f'single{op}', *row) for op, row in SINGLE.items()}
    for base, (name, first, second, effect) in FORMS.items():
        for i in range(8):
            pop, push = effect(i + 1)
            found[base + i] = (f'{name}_st{i}', bytes((first, second + i)).hex(), 0, pop, push, i + 1, False)
    return found


SNAN64 = 0x7ff0000000000001
# (label, ST(0), the indexed or second operand, binary64 memory operand bits)
VECTORS = [
    ('ordinary', E(3.0), E(-1.25), 0x3ff8000000000000),
    ('extended_only', (0x8000000000000001, 0x3fff), (0xc000000000000401, 0x4000), 0xbff0000000000000),
    ('tie', (0x8000000000000400, 0x3fff), E(1.0), 0x3ff0000000000000),
    ('signed_zero', (0, 0x8000), (0, 0), 0x8000000000000000),
    ('zero_divisor', E(1.0), (0, 0x8000), 0x0000000000000000),
    ('infinity', (1 << 63, 0x7fff), (1 << 63, 0xffff), 0x7ff0000000000000),
    ('quiet_nan', (0xc000000000000123, 0x7fff), E(2.0), 0x7ff8000000000000),
    ('signaling_nan', E(2.0), (0x8000000000000123, 0xffff), SNAN64),
    ('subnormal', (1, 0), (0x10, 0x8000), 0x0000000000000001),
    ('unnormal', (0x4000000000000000, 0x3fff), E(1.0), 0x3ff0000000000000),
    ('pseudo_denormal', (1 << 63, 0), E(-0.5), 0xbfe0000000000000),
    ('equal', E(7.5), E(7.5), 0x401e000000000000),
    ('greater', E(-7.5), E(-8.0), 0xc020000000000000),
    ('negative_sqrt', E(-4.0), E(4.0), 0x4010000000000000),
    ('overflow', E(sys.float_info.max), E(sys.float_info.max), 0x7fefffffffffffff),
    ('snan_st0', (0x8000000000000123, 0x7fff), E(1.0), 0x3ff0000000000000),
]
LOWER = ((0xb17217f7d1cf79ac, 0x3ffe), (0, 0x8000), (1, 0), (0x8000000000000001, 0xbfff),
         (0xc000000000000000, 0x7fff), (1 << 63, 0x4005), (0xfffffffffffff800, 0x43ff))


def layout(op, i, depth, a, b):
    """ST(0) = a, ST(i) = b for an indexed second operand, distinct values elsewhere."""
    slots = [LOWER[j % len(LOWER)] for j in range(depth)]
    slots[0] = a
    if op >= 0x100 and i > 0:
        slots[i] = b
    elif op == 14 and depth > 1:
        slots[1] = b
    return tuple(slots)


def primitive_checks(flavor):
    env, f, checks = Env(synthetic()), entry(flavor, 'claw_x87_register_selftest_entry'), {}

    def run(s, op, words=()):
        env._begin_case(random.Random(42))
        inp = env.object(C.sizeof(s), 'input', data=bytes(s), fill=0)
        out = env.object(C.sizeof(s), 'output', fill=0); env._freeze()
        padded = tuple(words) + (0,) * (2 - len(words))
        result = env.run_native(f, ENTRY, 0, (inp, op, *padded, out, len(words)))
        return result, type(s).from_buffer_copy(env.read(out, C.sizeof(s)))

    reference = Machine(synthetic(), 0x3000000, 0x40000)
    table = operations()
    seen_tops = {}
    for op, (label, instruction, argc, pop, push, minimum, stores) in table.items():
        reference.write(CODE, b'\xb8' + struct.pack('<I', DATA) + bytes.fromhex(instruction) + b'\xc3')
        reference.uc.ctl_remove_cache(CODE, CODE + 0x100)
        i = op & 7 if op >= 0x100 else 0
        top_depth = 8 - push + pop
        for depth in range(max(minimum, 1), min(8, top_depth) + 1):
            for v, (name, a, b, memory) in enumerate(VECTORS):
                top = (depth + 3 * v + i) & 7
                flags = 0x4521 if v & 1 else 0
                before = (0x23f, (top << 11) | flags, layout(op, i, depth, a, b))
                reference.set_x87_state(*before)
                reference.write(DATA, struct.pack('<Q', memory))
                assert reference.call(CODE).completed
                expected = reference.x87_state()
                stored = struct.unpack('<Q', reference.read(DATA, 8))[0] if stores else 0
                words = struct.unpack('<II', struct.pack('<Q', memory)) if argc == 2 else ()
                result, out = run(state(before), op, words)
                checks[f'{label}_{name}_depth{depth}'] = (result.completed and not result.errors and
                    not result.events and out.returned == 1 and snapshot(out) == expected and
                    len(expected[2]) == depth - pop + push and
                    (out.edx << 32 | out.eax) == stored)
                seen_tops.setdefault((op, depth), set()).add(top)
    checks['every_depth_every_top'] = all(len(t) == 8 for t in seen_tops.values())
    # The published SW is what the original's following FNSTSW AX reads.
    from unicorn.x86_const import UC_X86_REG_EAX
    for op, (label, instruction, argc, pop, push, minimum, stores) in table.items():
        if not (op in (14, 17, 18) or 0x120 <= op < 0x130):
            continue
        reference.write(CODE, b'\xb8' + struct.pack('<I', DATA) + bytes.fromhex(instruction + 'dfe0') + b'\xc3')
        reference.uc.ctl_remove_cache(CODE, CODE + 0x100)
        i = op & 7 if op >= 0x100 else 0
        for v, (name, a, b, memory) in enumerate(VECTORS):
            before = (0x23f, (v & 7) << 11 | 0x4500, layout(op, i, minimum, a, b))
            reference.set_x87_state(*before)
            reference.write(DATA, struct.pack('<Q', memory))
            assert reference.call(CODE).completed
            words = struct.unpack('<II', struct.pack('<Q', memory)) if argc == 2 else ()
            result, out = run(state(before), op, words)
            checks[f'fnstsw_{label}_{name}'] = (result.completed and
                out.status == reference.register(UC_X86_REG_EAX) & 0xffff)
    checks.update(known_checks(run))
    checks.update(rejection_checks(env, run, table))
    return checks


def known_checks(run):
    """Hand values: name each operation's actual operand order and result."""
    checks = {}

    def step(op, slots, words=(), status=0):
        result, out = run(state((0x23f, status, tuple(slots))), op, words)
        assert result.completed, (op, result.fault)
        return snapshot(out), out.edx << 32 | out.eax

    one, two, three = E(1.0), E(2.0), E(3.0)
    order = {  # operation, stack, expected ST(0)/ST(i) value after
        0x141: ([one, three], E(-2.0), 0),     # FSUB ST(0), ST(1): ST0 - ST1
        0x149: ([one, three], E(2.0), 0),      # FSUBR ST(0), ST(1): ST1 - ST0
        0x151: ([three, two], E(1.5), 0),      # FDIV ST(0), ST(1): ST0 / ST1
        0x159: ([two, three], E(1.5), 0),      # FDIVR ST(0), ST(1): ST1 / ST0
        0x179: ([one, three], E(2.0), 1),      # FSUB ST(1), ST(0): ST1 - ST0
        0x171: ([one, three], E(-2.0), 1),     # FSUBR ST(1), ST(0): ST0 - ST1
        0x189: ([two, three], E(1.5), 1),      # FDIV ST(1), ST(0): ST1 / ST0
        0x181: ([three, two], E(1.5), 1),      # FDIVR ST(1), ST(0): ST0 / ST1
        0x1a9: ([one, three], E(2.0), 0),      # FSUBP ST(1), ST(0): ST1 - ST0, pop
        0x1a1: ([one, three], E(-2.0), 0),     # FSUBRP ST(1), ST(0): ST0 - ST1, pop
        0x1b9: ([two, three], E(1.5), 0),      # FDIVP ST(1), ST(0): ST1 / ST0, pop
        0x1b1: ([three, two], E(1.5), 0),      # FDIVRP ST(1), ST(0): ST0 / ST1, pop
        0x191: ([one, two], three, 0),         # FADDP
        0x199: ([three, E(0.5)], E(1.5), 0),   # FMULP
        0x162: ([one, E(5.0), two], three, 2), # FADD ST(2), ST(0)
        0x132: ([one, E(5.0), two], three, 0), # FADD ST(0), ST(2)
    }
    for op, (slots, value, index) in order.items():
        (_, _, after), _ = step(op, slots)
        checks[f'known_order_{op:x}'] = after[index] == value
    lower = [E(float(n)) for n in range(1, 8)]
    (_, _, after), _ = step(0x10b, [E(9.0)] + lower)
    checks['known_fxch_st3'] = after == (lower[2], lower[0], lower[1], E(9.0), *lower[3:])
    (_, _, after), _ = step(0x102, [E(9.0), *lower[:3]])
    checks['known_fld_st2'] = after == (lower[1], E(9.0), *lower[:3])
    (_, _, after), _ = step(0x11b, [E(9.0), *lower[:4]])
    checks['known_fstp_st3'] = after == (lower[0], lower[1], E(9.0), lower[3])
    (_, _, after), _ = step(0x112, [E(9.0), *lower[:4]])
    checks['known_fst_st2'] = after == (E(9.0), lower[0], E(9.0), lower[2], lower[3])
    # Hardware would also set PE and C1 here; the reference interpreter leaves
    # SW clear, and both comparison sides use that interpreter.
    (_, status, after), _ = step(15, [two])
    checks['known_sqrt_53bit'] = after == ((0xb504f333f9de6800, 0x3fff),) and status == 0
    (_, _, after), _ = step(16, [(0, 0x8000)])
    checks['known_abs_negative_zero'] = after == ((0, 0),)
    (_, _, after), _ = step(16, [(0xc000000000000123, 0xffff)])
    checks['known_abs_nan_sign'] = after == ((0xc000000000000123, 0x7fff),)
    # FCOM condition codes as FNSTSW AX publishes them: C3 bit 14, C2 bit 10, C0 bit 8.
    for name, op, slots, words, codes in [
            ('less_m64', 17, [one], (0, 0x40000000), 0x0100),
            ('greater_m64', 17, [three], (0, 0x40000000), 0),
            ('equal_m64', 18, [two], (0, 0x40000000), 0x4000),
            ('unordered_m64', 17, [(0xc000000000000000, 0x7fff)], (0, 0x40000000), 0x4500),
            ('less_st1', 0x121, [one, two], (), 0x0100),
            ('equal_st1', 0x129, [two, two], (), 0x4000),
            ('greater_pp', 14, [three, two], (), 0),
            ('unordered_pp', 14, [two, (0xc000000000000000, 0x7fff)], (), 0x4500)]:
        (_, status, after), _ = step(op, slots, words, status=0x4500)
        # The reference interpreter does not raise IE for an ordered compare
        # with a quiet NaN (hardware does); unordered still sets C3, C2 and C0.
        checks[f'known_compare_{name}'] = (status & 0x4500) == codes and not status & 1
    for name, value, bits in [('one', one, 0x3ff0000000000000),
                              ('tie_even', (0x8000000000000400, 0x3fff), 0x3ff0000000000000),
                              ('tie_odd', (0x8000000000000c00, 0x3fff), 0x3ff0000000000002),
                              ('negative_zero', (0, 0x8000), 0x8000000000000000),
                              ('overflow', (1 << 63, 0x7ffe), 0x7ff0000000000000)]:
        (_, _, after), stored = step(20, [value, two])
        checks[f'known_fst_{name}'] = stored == bits and after == (value, two)
        (_, _, after), stored = step(21, [value, two])
        checks[f'known_fstp_{name}'] = stored == bits and after == (two,)
    (_, _, after), _ = step(19, [three], (0, 0x40000000))
    checks['known_fsub_m64'] = after == (one,)
    return checks


RAW_FIELDS = {'argumentCount', 'function', 'receiver', 'stackPointer', 'x87ArgumentCount'}


def rejection_checks(env, run, table):
    checks = {}
    sample = [op for op in table if op < 0x100 or op & 7 in (0, 1, 7)]
    one = E(1.0)
    # The checked C++ client: unknown operations, depth, overflow, arity and CW.
    for op in (0, 24, 0xff, 0x1c0, 0x1c7, 0x200, 0x10f, 0x80000100):
        result, _ = run(state((0x23f, 0, (one, one))), op)
        checks[f'reject_unknown_{op:x}'] = not result.completed and result.fault == 5
    for op in sample:
        label, _, argc, pop, push, minimum, _ = table[op]
        words = (0, 0x3ff00000) if argc else ()
        result, _ = run(state((0x23f, 0, (one,) * (minimum - 1))), op, words)
        checks[f'reject_{label}_shallow'] = not result.completed and result.fault == 5
        if push > pop:
            result, _ = run(state((0x23f, 0, (one,) * 8)), op, words)
            checks[f'reject_{label}_overflow'] = not result.completed and result.fault == 5
        bad = (0, 0x3ff00000) if not argc else (0,)
        result, _ = run(state((0x23f, 0, (one,) * 8 if push <= pop else (one,) * 7)), op, bad)
        checks[f'reject_{label}_arity'] = not result.completed and result.fault == 5
        for cw in (0x33f, 0x63f, 0xa3f, 0xe3f, 0x27f, 0x37f):
            result, _ = run(state((cw, 0, (one,) * max(minimum, 1))), op, words)
            checks[f'reject_{label}_cw{cw:x}'] = not result.completed and result.fault == 5
    # The comparison host on raw requests: a positive control, then every field.
    for op in sample:
        label, _, argc, pop, push, minimum, _ = table[op]
        depth = max(minimum, 2)
        if depth - pop + push > 8:
            continue  # FLD ST(7) can never be valid; the client checks above reject it.
        def raw_request(field=None, value=None):
            s = state((0x23f, 0, (one,) * depth), pop, push)
            raw = NativeCall(); raw.x87ArgumentCount = 3; raw.x87Operation = op; raw.x87State = C.pointer(s)
            raw.argumentCount = argc
            if argc: raw.arguments[1] = 0x3ff00000
            if field is not None:
                setattr(raw if field in RAW_FIELDS else s, field, value)
            env._host.fault = 0
            env._native_call(None, C.pointer(raw))
            return env._host.fault, s
        fault, s = raw_request()
        checks[f'raw_{label}_accepted'] = fault == 0 and s.returned == 1
        for field, value in [('argumentCount', argc + 1), ('popCount', pop + 1), ('pushCount', push + 1),
                             ('returned', 1), ('eax', 1), ('edx', 1), ('control', 0x33f),
                             ('reserved0', 1), ('status', 0x10000), ('function', 0x401100),
                             ('receiver', 1), ('stackPointer', 0x2004000), ('x87ArgumentCount', 2)]:
            fault, _ = raw_request(field, value)
            checks[f'raw_{label}_reject_{field}'] = fault == 5
    # Hosts that ignore an operation or corrupt its result, TOP, lower slots,
    # the receipt, the immutable request or the published EDX:EAX.
    original = env._host.call
    probes = [(0x101, ()), (0x109, ()), (0x119, ()), (0x129, ()), (0x131, ()), (0x161, ()),
              (0x1a9, ()), (14, ()), (15, ()), (17, (0, 0x3ff00000)), (20, ()), (21, ())]
    for op, words in probes:
        # A store's EDX is data (checked against the reference above); a non-store's must stay 0.
        modes = ('ignored', 'lower', 'top', 'receipt', 'request', 'eax', 'status_bits')
        for mode in modes + (() if table[op][6] else ('edx',)):
            def corrupt(user, pointer, mode=mode):
                if mode == 'ignored': return 0
                value = env._native_call(user, pointer)
                s = pointer.contents.x87State.contents
                if mode == 'lower': s.slots[s.count - 1].significand ^= 1
                elif mode == 'top': s.status ^= 0x800
                elif mode == 'receipt': s.returned = 0
                elif mode == 'request': pointer.contents.x87Operation ^= 2
                elif mode == 'eax': value ^= 1  # returned EAX disagrees with the published one
                elif mode == 'edx': s.edx ^= 1
                elif mode == 'status_bits': s.status |= 0x10000
                return value
            cb = CALLBACK(corrupt); env._host.call = cb
            result, _ = run(state((0x23f, 0, (one,) * 6)), op, words)
            env._host.call = original
            checks[f'bad_host_0x{op:x}_{mode}'] = not result.completed and result.fault == 5
    # Isolation: the primitive VM never touches the guest machine.
    m = env.machine
    saved = m.uc.context_save(); memory = m.read(0x3000000, 0x1000)
    before = m.x87_state()
    m.x87_step(0x109, (0x23f, 0, (one, E(2.0))))
    m.x87_step(20, (0x23f, 0, (one,)))
    checks['primitive_isolation'] = before == m.x87_state() and m.read(0x3000000, 0x1000) == memory
    m.uc.context_restore(saved)
    return checks


def checks(flavor='O2'):
    return primitive_checks(flavor)


def sanitized_checks():
    prefix, environment = build.sanitized_python()
    if prefix is None: return {'passed': False, 'detail': 'sanitizer unavailable'}
    done = subprocess.run(prefix + ['-m', 'Tests.clawparity.selftest.x87_register', '--flavor', 'sanitize'],
                          env=environment, cwd=build.ROOT, capture_output=True, text=True, timeout=900)
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
            results[flavor] = {'checked': len(found), 'failed': [k for k, v in found.items() if not v],
                               'passed': all(found.values())}
        results['sanitize'] = sanitized_checks()
        passed = all(v['passed'] for v in results.values())
        print(json.dumps({'passed': passed, 'results': results}))
    else:
        found = checks(args.flavor); passed = all(found.values())
        print(json.dumps({'passed': passed, 'checked': len(found), 'failed': [k for k, v in found.items() if not v][:60]}))
    raise SystemExit(not passed)
