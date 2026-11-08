"""Owned entries returning one value in ST(0). Controls only; admits nothing.

Synthetic bodies are independently written. The original proof runs the
hash-checked 0x420af0 unchanged through the ordinary runner path and
compares the native module's published ST(0), SW and stack bit-exactly.
"""
import ctypes as C
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

from .. import build, runner
from ..cases import compiler_contract_errors
from ..env import Env, HarnessError, NativeCall, NativeHost, NativeX87State, U32, CALLBACK

LOAD, PRODUCED, MODE = 0x401000, 0x401020, 0x401060
NONE, TWO, CONTROL, PRODUCER, STARTUP = 0x401080, 0x4010a0, 0x4010c0, 0x4010e0, 0x401100
BODIES = {
    LOAD: 'dd442404 c20800',                        # FLD m64 [esp+4]; RET 8
    # Push the two words in order, call the cdecl producer, clean up, return.
    PRODUCED: 'ff742408 ff742408 e8{rel} 83c408 c3',
    MODE: 'dd442408 c3',                            # FLD m64 [esp+8]
    NONE: 'c20800',                                 # wrong: no result
    TWO: 'd9e8 d9ee c20800',                        # wrong: two results
    CONTROL: 'd92d10204000 dd442404 c20800',        # wrong: changes CW
    PRODUCER: 'dd442404 d9e0 c3',                   # FLD m64; FCHS
    STARTUP: 'd92d12204000 c3',                     # FLDCW 0x023f
}
SPEC = Path(__file__).with_name('x87_result_family.json')
VALUES = (0x0000000000000000, 0x8000000000000000, 0x3ff0000000000000, 0x0000000000000001,
          0x7ff0000000000000, 0x7ff0000000000001, 0xfff8000000000000, 0x7fefffffffffffff,
          0xc00921fb54442d18)


def synthetic():
    from ..program import Program, Section
    code = bytearray(b'\xcc' * 0x200)
    for address, body in BODIES.items():
        if '{rel}' in body:
            call_end = address + 8 + 5
            body = body.format(rel=struct.pack('<i', PRODUCER - call_end).hex())
        raw = bytes.fromhex(body.replace(' ', ''))
        code[address - 0x401000:address - 0x401000 + len(raw)] = raw
    data = bytearray(0x1000)
    data[0x10:0x14] = struct.pack('<HH', 0x003f, 0x023f)
    return Program('x87-result-synthetic', '', 0x400000, 0x3000,
                   [Section('.text', 0x401000, len(code), bytes(code)),
                    Section('.data', 0x402000, 0x1000, bytes(data))], (0x401000, 0x401200), {},
                   startup_calls=(STARTUP,), control_word=(0xffff, 0x023f))


def entry(flavor):
    library = C.CDLL(str(build.library('x87-result-selftest', [Path(__file__).with_name('X87ResultModule.cpp')], flavor)))
    f = library.claw_x87_result_selftest_entry
    f.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    f.restype = U32
    return f


def declared_env():
    env = Env(synthetic())
    for address in (LOAD, PRODUCED, MODE, NONE, TWO, CONTROL):
        env.owned_x87_result(address, {'pop': 0, 'push': 1})
    env.whole_x87(PRODUCER, 'cdecl', 2, exact={'pop': 0, 'push': 1})
    return env


def compare(env, f, function, arguments, receiver=0):
    env._begin_case(random.Random(function ^ sum(arguments)))
    env._freeze()
    native = env.run_native(f, function, receiver, arguments)
    original = env.run_original(function, receiver, arguments)
    return native, original, env.compare(native, original, False, 0x02008000 + 4 + (8 if function in (LOAD, NONE, TWO, CONTROL) else 0))


def words(bits):
    return bits & 0xffffffff, bits >> 32


def transport_checks(flavor):
    env, f, checks = declared_env(), entry(flavor), {}
    # Correct publications compare exactly against the unchanged original.
    for bits in VALUES:
        for function, receiver, arguments in ((LOAD, 0x1234, words(bits)), (PRODUCED, 0, words(bits)),
                                              (MODE, 0, (0, *words(bits))), (MODE, 0, (11, *words(bits)))):
            native, original, difference = compare(env, f, function, arguments, receiver)
            key = f'equal_{function:x}_{arguments[0] if function == MODE else ""}_{bits:x}'
            checks[key] = (difference is None and native.x87 is not None and native.x87 == original.x87 and
                           len(original.x87[2]) == 1 and original.x87[0] == 0x023f and
                           (original.x87[1] >> 11) & 7 == 7)
            if function == PRODUCED:
                checks[key + '_producer_event'] = (len(native.events) == 1 and native.events[0][0] == PRODUCER and
                                                   native.events == original.events)
    _, original, _ = compare(env, f, MODE, (0, *words(0x7ff0000000000001)))
    checks['signaling_nan_sets_ie'] = original.x87[1] & 1 == 1 and original.x87[2][0][0] >> 62 & 1 == 1
    # Wrong values the host cannot see are caught by the comparison.
    for mode, name in ((1, 'value_bit'), (2, 'sw_c3')):
        for bits in VALUES[:4]:
            native, original, difference = compare(env, f, MODE, (mode, *words(bits)))
            checks[f'wrong_{name}_{bits:x}'] = (native.completed and difference is not None and
                                                difference['kind'] == 'x87-result')
    # Malformed publications fail on the native side before comparison.
    for mode, name in ((3, 'missing'), (4, 'twice'), (5, 'call_after'), (6, 'push_two'), (7, 'top'),
                       (8, 'other_function'), (9, 'entry_twice'), (10, 'control')):
        native, original, difference = compare(env, f, MODE, (mode, *words(0x3ff0000000000000)))
        checks[f'reject_{name}'] = (not native.completed and native.fault == 5 and native.x87 is None and
                                    difference is not None and difference['kind'] == 'native-fault')
    # Original bodies contradicting the declaration are specification errors.
    for function, name in ((NONE, 'none'), (TWO, 'two'), (CONTROL, 'control')):
        native, original, difference = compare(env, f, function, words(0x3ff0000000000000), 0x1234)
        checks[f'original_wrong_{name}'] = (native.completed and difference is not None and
                                            difference['kind'] == 'harness' and 'x87_result' in difference['detail'])
    # An undeclared outer entry cannot use the channel.
    plain = Env(synthetic())
    plain.whole_x87(PRODUCER, 'cdecl', 2, exact={'pop': 0, 'push': 1})
    native, _, _ = compare(plain, f, LOAD, words(0x3ff0000000000000), 0x1234)
    checks['undeclared_entry_rejected'] = not native.completed and native.fault == 5 and native.x87 is None
    # Bypass the helper: the host validates raw requests itself.
    raw = NativeCall(); raw.function = MODE; raw.x87ArgumentCount = 4
    for name, field, value in (('receiver', 'receiver', 1), ('receiver2', 'receiver2', 1), ('argc', 'argumentCount', 1),
                               ('argument', 'x87Argument', 1.0), ('operation', 'x87Operation', 1),
                               ('stack', 'stackPointer', 0x02004000), ('tail', 'sourceTransferKind', 1),
                               ('function', 'function', LOAD), ('word', 'arguments', None)):
        for kind in (4, 5):
            target = NativeX87State(); target.size, target.version = C.sizeof(target), 1
            broken = NativeCall.from_buffer_copy(raw); broken.x87ArgumentCount = kind
            broken.x87State = C.pointer(target)
            if field == 'arguments': broken.arguments[3] = 1
            else: setattr(broken, field, value)
            env._x87_outer = dict(function=MODE, entry=(0x023f, 0, ()), queried=False, result=None)
            env._host.fault = 0; env.errors.clear()
            env._native_call(None, C.pointer(broken))
            checks[f'raw_{name}_{kind}'] = env._host.fault == 5 and not target.returned and env._x87_outer['result'] is None
    for kind in (4, 5):
        target = NativeX87State(); target.size, target.version = C.sizeof(target), 1
        broken = NativeCall.from_buffer_copy(raw); broken.x87ArgumentCount = kind; broken.x87State = C.pointer(target)
        env._x87_outer = None; env._host.fault = 0
        env._native_call(None, C.pointer(broken))
        checks[f'raw_outside_entry_{kind}'] = env._host.fault == 5 and not target.returned
        env._x87_outer = dict(function=MODE, entry=(0x023f, 0, ()), queried=False, result=None)
        empty = NativeCall.from_buffer_copy(raw); empty.x87ArgumentCount = kind
        env._host.fault = 0
        env._native_call(None, C.pointer(empty))
        checks[f'raw_no_state_{kind}'] = env._host.fault == 6 and env._x87_outer['result'] is None  # legacy operand-count rejection
    env._x87_outer = None; env._host.fault = 0; env.errors.clear()
    # A host that ignores or corrupts the receipt cannot complete the entry.
    original_callback = env._host.call
    for mode in ('ignored', 'entry_push', 'entry_eax', 'result_slot', 'result_receipt', 'result_value', 'request'):
        def corrupt(user, pointer, mode=mode):
            kind = pointer.contents.x87ArgumentCount
            if mode == 'ignored' and kind == 5: return 0
            value = env._native_call(user, pointer)
            s = pointer.contents.x87State.contents if pointer.contents.x87State else None
            if kind == 4 and mode == 'entry_push': s.pushCount = 1
            elif kind == 4 and mode == 'entry_eax': s.eax = 1
            elif kind == 5 and mode == 'result_slot': s.slots[0].significand ^= 1
            elif kind == 5 and mode == 'result_receipt': s.returned = 0
            elif kind == 5 and mode == 'result_value': value = 1
            elif kind == 5 and mode == 'request': pointer.contents.function ^= 1
            return value
        cb = CALLBACK(corrupt); env._host.call = cb
        native, _, _ = compare(env, f, MODE, (0, *words(0x3ff0000000000000)))
        checks[f'bad_host_{mode}'] = not native.completed and native.fault == 5
    env._host.call = original_callback
    # Declaration validation.
    base = {'abi': 'canonical', 'owned': [{'address': '0x401000', 'convention': 'thiscall', 'argc': 2,
                                           'returns': 'x87', 'x87_result': {'pop': 0, 'push': 1}}]}
    checks['schema_valid'] = compiler_contract_errors(base) == []
    for name, change in (('returns_u32', {'returns': 'u32'}), ('no_result', {'x87_result': None}),
                         ('push0', {'x87_result': {'pop': 0, 'push': 0}}), ('pop1', {'x87_result': {'pop': 1, 'push': 1}}),
                         ('bool', {'x87_result': {'pop': False, 'push': True}}), ('extra', {'x87_result': {'pop': 0, 'push': 1, 'x': 0}}),
                         ('fastcall', {'convention': 'fastcall'}), ('compiler', {'convention': 'compiler-context'}),
                         ('source', {'source_context': {}}), ('x87_args', {'x87_args': 1}), ('argc', {'argc': 33})):
        entry_ = {**base['owned'][0], **change}
        if change.get('x87_result', 1) is None: del entry_['x87_result']
        checks[f'schema_reject_{name}'] = bool(compiler_contract_errors({**base, 'owned': [entry_]}))
    checks['schema_reject_legacy_abi'] = bool(compiler_contract_errors({**base, 'abi': 'legacy'}))
    for name, address, effect in (('push0', 0x401140, {'pop': 0, 'push': 0}), ('bool', 0x401140, {'pop': False, 'push': True}),
                                  ('outside_text', 0x500000, {'pop': 0, 'push': 1}), ('duplicate', LOAD, {'pop': 0, 'push': 1}),
                                  ('callee', PRODUCER, {'pop': 0, 'push': 1})):
        try:
            env.owned_x87_result(address, effect); checks[f'env_reject_{name}'] = False
        except HarnessError:
            checks[f'env_reject_{name}'] = True
    return checks


def original_checks(flavor):
    """The ordinary runner path against hash-checked, unchanged 0x420af0."""
    checks = {}
    if str(build.ROOT / 'Tests') not in sys.path:
        sys.path.insert(0, str(build.ROOT / 'Tests'))  # family cases import clawparity.cases
    for seed in (1, 77):
        correct = runner.run(SPEC, seed=seed, flavor=flavor, trace=True)
        checks[f'motion_runner_seed{seed}'] = correct['status'] == 'pass' and correct['cases'] == 28
        if seed == 1:
            covered = correct.get('coverage', {}).get('0x420af0', {})
            # The equal-factor exit: entry compare through the first RET 8.
            checks['motion_equal_exit_executed'] = (covered.get('executed') or 0) >= 0x16
    if flavor == 'sanitize':
        return checks
    for define in ('SELFTEST_X87R_WRONG_SW', 'SELFTEST_X87R_WRONG_BIT'):
        wrong = runner.run(SPEC, seed=1, flavor=flavor, defines=(define,))
        kinds = {failure['kind'] for failure in wrong.get('failures', [])}
        checks[f'motion_{define.lower()}'] = wrong['status'] == 'fail' and wrong['failed'] == 28 and kinds == {'x87-result'}
    return checks


def checks(flavor='O2'):
    return {**transport_checks(flavor), **original_checks(flavor)}


def sanitized_checks():
    prefix, environment = build.sanitized_python()
    if prefix is None: return {'passed': False, 'detail': 'sanitizer unavailable'}
    done = subprocess.run(prefix + ['-m', 'Tests.clawparity.selftest.x87_result', '--flavor', 'sanitize'],
                          env=environment, cwd=build.ROOT, capture_output=True, text=True, timeout=600)
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
