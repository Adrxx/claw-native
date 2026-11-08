"""Balanced exact x87 transport (pop 0, push 0). Controls only; admits nothing.

Synthetic bodies are independently written; the original probe runs the
hash-checked reference program unchanged and only supplies entry state.
"""
import ctypes as C
import json
import random
import struct
import subprocess
from dataclasses import replace

from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_ESP
from .. import build
from ..env import Env, Halt, NativeCall, NativeX87State, CALLBACK
from ..kernel import Machine, STACK_TOP
from ..program import Program, Section, claw
from .x87_exact import entry, state, snapshot, native_stack_result, native, ENTRY

# thiscall, two ordinary words, RET 8; each body nets zero x87 slots.
TRANSIENT, EQUAL, LIVE, NONE = 0x401200, 0x401220, 0x401240, 0x401260
# Wrong actual effects under a balanced declaration.
PUSH, POP, LOWER, CONTROL, CDECL_NONE = 0x401280, 0x401290, 0x4012a0, 0x4012b0, 0x4012c0
CONVERT = 0x4012d0  # cdecl pop 1/push 0, for declaration mismatches
BODIES = {
    TRANSIENT: 'd9e8 d9ee ded9 b8efcdab89 ba67452301 c20800',  # FLD1 FLDZ FCOMPP
    EQUAL: 'd9ee d9ee ded9 8b442408 31d2 c20800',              # FLDZ FLDZ FCOMPP -> C3
    LIVE: 'd8d0 89c8 8b542404 c20800',                         # FCOM ST(0), reads live ST0
    NONE: '8b442408 8b542404 c20800',
    PUSH: 'd9ee c20800',
    POP: 'ddd8 c20800',
    LOWER: 'd9e0 c20800',
    CONTROL: 'd92d10204000 c20800',
    CDECL_NONE: 'c20800',
    CONVERT: '83ec08 df3c24 58 5a c3',
}
MOTION, FTOL = 0x403b40, 0x4a30e0


def synthetic():
    code = bytearray(b'\xcc' * 0x400)
    for address, body in BODIES.items():
        raw = bytes.fromhex(body)
        code[address - 0x401000:address - 0x401000 + len(raw)] = raw
    data = bytearray(0x1000)
    data[0x10:0x12] = struct.pack('<H', 0x003f)
    return Program('x87-balanced-synthetic', '', 0x400000, 0x3000,
                   [Section('.text', 0x401000, len(code), bytes(code)),
                    Section('.data', 0x402000, 0x1000, bytes(data))], (0x401000, 0x401400), {})


VALUES = ((0x8000000000000001, 0x3fff), (0, 0x8000), (0xb17217f7d1cf79ac, 0x3ffe),
          (0xc000000000000123, 0x7fff), (1, 0), (0x923456789abcdef1, 0xc002))


def declare(env):
    for target in (TRANSIENT, EQUAL, LIVE, NONE, PUSH, POP, LOWER, CONTROL):
        env.whole_x87(target, 'thiscall', 2, exact={'pop': 0, 'push': 0})
    env.whole_x87(CDECL_NONE, 'cdecl', 2, exact={'pop': 0, 'push': 0})
    env.whole_x87(CONVERT, 'cdecl', 0, exact={'pop': 1, 'push': 0})


def transport_checks(flavor):
    program = synthetic()
    env, reference, checks = Env(program), Machine(program, 0x3000000, 0x40000), {}
    declare(env)
    f = entry(flavor, 'claw_x87_stack_result_selftest_entry')
    words, receiver = (0x13572468, 0x9abcdef0), 0x12345678
    depths = {TRANSIENT: range(7), EQUAL: range(7), LIVE: range(1, 9), NONE: range(9)}
    for target, allowed in depths.items():
        for depth in allowed:
            for rounding in range(4):
                top = (depth * 3 + rounding) & 7
                before = ((0x23f if rounding & 1 else 0x33f) | rounding << 10,
                          top << 11 | (0x4421 if depth & 1 else 0x0700),
                          tuple(VALUES[(i + rounding) % len(VALUES)] for i in range(depth)))
                reference.set_x87_state(*before)
                returned = reference.call(target, receiver, arguments=words)
                expected = reference.x87_state()
                eax, edx = reference.register(UC_X86_REG_EAX), reference.register(UC_X86_REG_EDX)
                result, out = native_stack_result(env, f, state(before, 0, 0), target, words, receiver)
                key = f'balanced_{target:x}_{depth}_{rounding}'
                checks[key] = (returned.completed and result.completed and not result.errors and
                    out.returned == 1 and out.popCount == 0 and out.pushCount == 0 and
                    snapshot(out) == expected and out.eax == eax and out.edx == edx and
                    out.control == before[0] and snapshot(out)[2] == before[2] and
                    (out.status >> 11) & 7 == top and
                    result.events[0][1] == receiver and result.events[0][3] == words and
                    result.events[0][5] == ('extended-v1', *before))
                if target in (TRANSIENT, EQUAL):
                    # The published SW is the callee's, not the incoming word.
                    flag = 0x0100 if target == TRANSIENT else 0x4000
                    checks[key + '_sw'] = out.status & 0x4500 == flag and out.status != before[1]
    checks['balanced_empty_sw_eax_edx'] = all(checks[f'balanced_{t:x}_0_{r}'] for t in (TRANSIENT, EQUAL, NONE)
                                              for r in range(4))
    # Malformed native requests are rejected before the original executes.
    valid = state((0x23f, 0x2000, VALUES[:2]), 0, 0)
    empty = state((0x23f, 0x3800, ()), 0, 0)
    for name, field, value, base in [('pop', 'popCount', 1, valid), ('push', 'pushCount', 1, valid),
                                     ('push_empty', 'pushCount', 1, empty), ('pop_empty', 'popCount', 1, empty),
                                     ('returned', 'returned', 1, empty), ('eax', 'eax', 1, empty),
                                     ('edx', 'edx', 1, empty), ('count', 'count', 9, valid),
                                     ('version', 'version', 2, empty), ('control', 'control', 0x13f, empty)]:
        broken = NativeX87State.from_buffer_copy(base); setattr(broken, field, value)
        result, _ = native_stack_result(env, f, broken, NONE, words, receiver)
        checks[f'balanced_bad_state_{name}'] = not result.completed and result.fault == 5 and not result.events
    broken = NativeX87State.from_buffer_copy(empty); broken.slots[0].significand = 1
    result, _ = native_stack_result(env, f, broken, NONE, words, receiver)
    checks['balanced_bad_state_inactive_slot'] = not result.completed and result.fault == 5
    # Declaration mismatch both ways: balanced request to pop 1 callee, and the reverse.
    env._begin_case(random.Random(5))
    result, _ = native(env, entry(flavor), state((0x23f, 0, VALUES[:1]), 0, 0), CONVERT)
    checks['balanced_request_to_pop_declaration'] = not result.completed and result.fault == 5 and not result.events
    result, _ = native_stack_result(env, f, state((0x23f, 0, VALUES[:1]), 1, 0), NONE, words, receiver)
    checks['pop_request_to_balanced_declaration'] = not result.completed and result.fault == 5 and not result.events
    # Bypass the C++ helper: the host validates the raw request itself.
    raw = NativeCall(); raw.function = NONE; raw.receiver = receiver; raw.x87ArgumentCount = 2
    raw.argumentCount = 2; raw.arguments[0], raw.arguments[1] = words
    for name, field, value in [('argc1', 'argumentCount', 1), ('argc3', 'argumentCount', 3),
                               ('receiver2', 'receiver2', 1), ('operation', 'x87Operation', 1),
                               ('tail', 'sourceTransferKind', 1), ('argument', 'x87Argument', 1),
                               ('undeclared', 'function', 0x401300), ('kind', 'x87ArgumentCount', 1)]:
        target = NativeX87State.from_buffer_copy(empty)
        broken = NativeCall.from_buffer_copy(raw); broken.x87State = C.pointer(target)
        setattr(broken, field, value)
        env._host.fault = 0; env.events.clear(); env._native_call(None, C.pointer(broken))
        checks[f'balanced_bad_request_{name}'] = (env._host.fault == 5 and not target.returned and
                                                  not env.events)
    ordinary = NativeCall.from_buffer_copy(raw); ordinary.x87ArgumentCount = 0
    env._host.fault = 0; env.events.clear(); env._native_call(None, C.pointer(ordinary))
    checks['balanced_ordinary_call_rejected'] = env._host.fault == 5 and not env.events
    # Wrong actual callee effects fail after the unchanged original runs.
    for target, depth in ((PUSH, 0), (PUSH, 3), (POP, 2), (LOWER, 1), (LOWER, 4), (CONTROL, 0),
                          (CONTROL, 2), (CDECL_NONE, 0)):
        before = (0x33f, 0x1800, VALUES[:depth])
        result, _ = native_stack_result(env, f, state(before, 0, 0), target, words,
                                        0 if target == CDECL_NONE else receiver)
        checks[f'balanced_wrong_effect_{target:x}_{depth}'] = (
            not result.completed and result.fault == 5 and bool(result.events))
    env.x87_callees[NONE] = replace(env.x87_callees[NONE], convention='cdecl')
    result, _ = native_stack_result(env, f, empty, NONE, words, receiver)
    checks['balanced_wrong_cleanup'] = not result.completed and result.fault == 5
    env.x87_callees[NONE] = replace(env.x87_callees[NONE], convention='thiscall')
    # A host that ignores, fabricates or corrupts the receipt cannot publish success.
    original_callback = env._host.call
    for mode in ('ignored', 'lower', 'cw', 'top', 'count', 'fabricated', 'receipt', 'pop', 'push',
                 'request', 'eax'):
        for base in (valid, empty):
            if mode == 'lower' and base is empty:
                continue
            def corrupt(user, pointer, mode=mode):
                if mode == 'ignored': return 0
                value = env._native_call(user, pointer)
                s = pointer.contents.x87State.contents
                if mode == 'lower': s.slots[1].significand ^= 1
                elif mode == 'cw': s.control ^= 0x400
                elif mode == 'top': s.status ^= 0x800
                elif mode == 'count': s.count = 0 if s.count else 1
                elif mode == 'fabricated':
                    s.slots[s.count].significand, s.slots[s.count].signExponent = 1 << 63, 0x3fff
                    s.count += 1; s.status = (s.status - 0x800) & 0xffff
                elif mode == 'receipt': s.returned = 0
                elif mode == 'pop': s.popCount = 1
                elif mode == 'push': s.pushCount = 1
                elif mode == 'request': pointer.contents.arguments[1] ^= 1
                elif mode == 'eax': s.eax ^= 1
                return value
            cb = CALLBACK(corrupt); env._host.call = cb
            result, _ = native_stack_result(env, f, base, NONE, words, receiver)
            checks[f'balanced_bad_host_{mode}_{base.count}'] = not result.completed and result.fault == 5
    env._host.call = original_callback
    return checks


def motion_object(rng, mode):
    data = bytearray(0xf0)
    if mode == 'zero':
        return bytes(data), 0.0
    for offset in range(0, 0xf0, 8):
        data[offset:offset + 8] = struct.pack('<d', rng.uniform(-900.0, 900.0))
    if mode == 'limit':  # a reachable limit equal to the current value
        data[0xe8:0xf0] = data[0x38:0x40]
    return bytes(data), rng.uniform(0.0, 40.0)


def original_checks(flavor):
    """Unchanged 0x403b40 from its owned call site to the next 0x4a30e0 call.

    The original reference runs the instruction stream from the CALL at
    0x4dca5c through the free-motion path to the CALL at 0x4dcb03. Native
    transport receives only the captured entry state and must publish the
    original's SW; its C3 must be the value that reaches 0x4a30e0.
    """
    program = claw()
    reference, checks = Machine(program, 0x3000000, 0x40000), {}
    env = Env(program)
    env.whole_x87(MOTION, 'thiscall', 2, exact={'pop': 0, 'push': 0})
    f = entry(flavor, 'claw_x87_stack_result_selftest_entry')
    owner, actor, code = 0x3000000, 0x3000200, 0x2001000
    captures = {}
    def capture(m, pc):
        captures[pc] = (m.x87_state(), m.register(UC_X86_REG_EAX), m.register(UC_X86_REG_EDX),
                        m.register(UC_X86_REG_ESP))
    def stop(m, pc):
        capture(m, pc)
        raise Halt()
    reference.observe(MOTION, capture)
    reference.observe(0x4dca61, capture)
    reference.observe(FTOL, stop)
    rng, seen = random.Random(0x403b40), set()
    for case in range(24):
        mode = ('zero', 'limit', 'random')[case % 3]
        motion, elapsed = motion_object(rng, mode)
        words = struct.unpack('<II', struct.pack('<d', elapsed))
        reference.reset_x87()
        top = rng.randrange(8)
        reference.set_x87_state(0x23f, top << 11 | rng.choice((0, 0x4000, 0x0100, 0x4500)), ())
        reference.write(owner, bytes(0x130))
        reference.write(owner + 0x0c, struct.pack('<I', actor))
        reference.write(owner + 0x28, motion)
        reference.write(actor, bytes(0x100))
        # ESI is the owning object; ECX and the two words are the CALL's operands.
        stub = (b'\xbe' + struct.pack('<I', owner) + b'\xb9' + struct.pack('<I', owner + 0x28) +
                b'\x68' + struct.pack('<I', words[1]) + b'\x68' + struct.pack('<I', words[0]) +
                b'\xe9' + struct.pack('<i', 0x4dca5c - (code + 25)))
        reference.write(code, stub)
        reference.uc.ctl_remove_cache(code, code + 0x40)
        captures.clear()
        try:
            reference.call(code, stack_pointer=STACK_TOP)
            halted = False
        except Halt:
            halted = True
        key = f'motion_{case}_{mode}'
        checks[key + '_original'] = halted and {MOTION, 0x4dca61, FTOL} <= set(captures)
        if not checks[key + '_original']:
            continue
        entry_state = captures[MOTION][0]
        after, eax, edx, _ = captures[0x4dca61]
        at_ftol = captures[FTOL][0]
        after_object = bytes(reference.read(owner + 0x28, 0xf0))
        checks[key + '_balanced'] = (len(entry_state[2]) == 0 and len(after[2]) == 0 and
                                     after[0] == entry_state[0] and
                                     (after[1] >> 11) & 7 == (entry_state[1] >> 11) & 7)
        env._begin_case(random.Random(case))
        value = state(entry_state, 0, 0)
        inp = env.object(C.sizeof(value), 'input', data=bytes(value), fill=0)
        out_address = env.object(C.sizeof(value), 'output', fill=0)
        receiver = env.object(0xf0, 'motion', data=motion, fill=0)
        env._freeze()
        result = env.run_native(f, 0x4010d0, 0, (inp, MOTION, *words, out_address, receiver))
        out = NativeX87State.from_buffer_copy(env.read(out_address, C.sizeof(value)))
        checks[key + '_native'] = (result.completed and not result.errors and out.returned == 1 and
            snapshot(out) == after and out.eax == eax and out.edx == edx and
            env.read(receiver, 0xf0) == after_object and
            result.events[0][3] == words and result.events[0][5] == ('extended-v1', *entry_state))
        # The C3 reaching the next conversion is the one the transport returned.
        checks[key + '_c3_crosses'] = (at_ftol[0] == out.control and
                                       at_ftol[1] & 0x4000 == out.status & 0x4000 and
                                       (at_ftol[1] >> 11) & 7 == ((out.status >> 11) - 1) & 7)
        seen.add(bool(out.status & 0x4000))
    checks['motion_c3_both_values'] = seen == {False, True}
    return checks


def checks(flavor='O2'):
    return {**transport_checks(flavor), **original_checks(flavor)}


def sanitized_checks():
    prefix, environment = build.sanitized_python()
    if prefix is None: return {'passed': False, 'detail': 'sanitizer unavailable'}
    done = subprocess.run(prefix + ['-m', 'Tests.clawparity.selftest.x87_balanced', '--flavor', 'sanitize'],
                          env=environment, cwd=build.ROOT, capture_output=True, text=True, timeout=300)
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
        print(json.dumps({'passed': passed, 'checked': len(found), 'failed': [k for k, v in found.items() if not v]}))
    raise SystemExit(not passed)
