"""Inherited x87 environments for ordinary owners; controls only, admits nothing.

Independent synthetic owners exercise full comparisons. The original-backed
probe executes the unchanged CALL at 0x4dca5c and its actual 0x403b40 callee.
"""
import ctypes as C
import json
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from .. import build, runner
from ..cases import Case, compiler_contract_errors
from ..env import Env, HarnessError, Halt, NativeCall, NativeHost, NativeX87State, NativeX87Value, CALLBACK, U32
from ..kernel import Machine, STACK_TOP
from ..program import Program, Section, claw
from .x87_balanced import motion_object
from .x87_balanced import VALUES

DIRECT, FACTORY, BALANCED, CONVERT, STARTUP = 0x401000, 0x401040, 0x401200, 0x401240, 0x401280
MODULE = Path(__file__).with_name('X87EnvironmentModule.cpp')
EFFECT = {'pop': 0, 'push': 0}
FLAGS = (0, 0x20, 0x21, 0x3f)
ARITH, PRESERVE = 0x401080, 0x4010c0
CONTROLS = tuple(pc | rc << 10 | 0x3f for pc in (0, 0x200, 0x300) for rc in range(4))


def profiles():
    for control in CONTROLS:
        for depth in (0, 1, 3, 6):
            top = (depth + (control >> 10) + 1) & 7
            yield dict(control=control, status=top << 11 | 0x4521, slots=VALUES[:depth])


def synthetic(wrong=None):
    # CALL balanced; FILD the second ordinary word; CALL integer conversion.
    direct = b'\xe8' + struct.pack('<i', BALANCED - (DIRECT + 5)) + b'\xdb\x44\x24\x08'
    direct += b'\xe8' + struct.pack('<i', CONVERT - (DIRECT + len(direct) + 5)) + b'\xc3'
    factory = bytes.fromhex('ff742408 ff742408')
    factory += b'\xe8' + struct.pack('<i', DIRECT - (FACTORY + len(factory) + 5)) + bytes.fromhex('83c408 c3')
    bodies = {DIRECT: direct, FACTORY: factory, BALANCED: bytes.fromhex('d9e8 d9ee ded9 c3'),
              CONVERT: bytes.fromhex('83ec08 df3c24 58 5a c3'),
              STARTUP: bytes.fromhex('d92d00204000 c3'),
              ARITH: bytes.fromhex('dd442404 dc0508204000 83ec08 dd1c24 58 5a c3'),
              PRESERVE: bytes.fromhex('31c0 c3')}
    if wrong is not None:
        bodies[DIRECT] = bytes.fromhex({'push': 'd9ee c3', 'top': 'd9f7 c3', 'cw': 'd92d02204000 c3'}[wrong])
    code = bytearray(b'\xcc' * 0x300)
    for address, body in bodies.items():
        code[address - DIRECT:address - DIRECT + len(body)] = body
    return Program('x87-environment-synthetic', '', 0x400000, 0x3000,
        [Section('.text', DIRECT, len(code), bytes(code)), Section('.data', 0x402000, 0x1000,
            b'\x3f\x02\x3f\x03' + bytes(4) + struct.pack('<d', 1.0) + bytes(4080))],
        (DIRECT, DIRECT + len(code)), {}, startup_calls=(STARTUP,), control_word=(0xffff, 0x023f))


def entry(flavor):
    library = C.CDLL(str(build.library('x87-environment-selftest', [MODULE], flavor)))
    f = library.claw_x87_environment_selftest_entry
    f.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    f.restype = U32
    return f


def declared_env():
    env = Env(synthetic())
    for target in (DIRECT, FACTORY, ARITH, PRESERVE): env.owned_x87_environment(target, EFFECT)
    env.whole_x87(BALANCED, 'cdecl', 0, exact=EFFECT)
    env.whole_x87(CONVERT, 'cdecl', 0, exact={'pop': 1, 'push': 0})
    return env


def compare(env, f, function=DIRECT, flags=0, mode=0, value=123):
    env._begin_case(random.Random(17))
    env.entry_x87_status(flags)
    env._freeze()
    native = env.run_native(f, function, 0, (mode, value))
    original = env.run_original(function, 0, (mode, value))
    return native, original, env.compare(native, original, True, STACK_TOP + 4)


def rejected(action):
    try: action()
    except HarnessError: return True
    return False


def transport_checks(flavor):
    env, f, found = declared_env(), entry(flavor), {}
    for function in (DIRECT, FACTORY):
        for flags in FLAGS:
            for value in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff):
                n, o, diff = compare(env, f, function, flags, value=value)
                key = f'equal_{function:x}_{flags:x}_{value:x}'
                found[key] = diff is None and n.x87 == o.x87 == (0x23f, 0x100 | flags, ()) and n.eax == value
                found[key + '_boundaries'] = (n.events == o.events and len(n.events) == 2 and
                    n.events[0][5] == ('extended-v1', 0x23f, flags, ()) and
                    n.events[1][5][2] == 0x3900 | flags)
    for mode in (1, 2):
        n, o, diff = compare(env, f, flags=0x21, mode=mode)
        found[f'wrong_seed_{mode}'] = n.completed and diff is not None and diff['kind'] == 'event'
    n, o, diff = compare(env, f, flags=0x21, mode=3)
    found['wrong_final_sw'] = n.completed and diff is not None and diff['kind'] == 'x87-result'
    n, o, diff = compare(env, f, flags=0x21, mode=14)
    found['integer_return_still_compared'] = n.completed and diff is not None and diff['kind'] == 'return-value'
    for mode in range(4, 14):
        n, o, diff = compare(env, f, flags=0x21, mode=mode)
        found[f'reject_mode_{mode}'] = not n.completed and n.fault == 5 and n.x87 is None
    for wrong in ('push', 'top', 'cw'):
        broken = Env(synthetic(wrong))
        broken.owned_x87_environment(DIRECT, EFFECT)
        broken.whole_x87(BALANCED, 'cdecl', 0, exact=EFFECT)
        broken.whole_x87(CONVERT, 'cdecl', 0, exact={'pop': 1, 'push': 0})
        n, o, diff = compare(broken, f)
        found[f'original_contract_{wrong}'] = (n.completed and o.errors and diff is not None and
                                               diff['kind'] == 'harness' and 'x87_environment' in diff['detail'])
    env.x87_environments.clear()
    n, _, _ = compare(env, f)
    found['undeclared_owner'] = not n.completed and n.fault == 5
    env = declared_env()
    for value in (True, False, -1, 64, 0x80, 0x100, 0x800, 0x8000, 0x10000, 1.0, None, '32'):
        env._begin_case(None)
        found[f'setup_reject_{value!r}'] = rejected(lambda: env.entry_x87_status(value))
    env._begin_case(None); env.entry_x87_status(0)
    found['setup_duplicate'] = rejected(lambda: env.entry_x87_status(0))
    env._freeze()
    found['setup_frozen'] = rejected(lambda: env.entry_x87_status(0x20))
    env._begin_case(None); env._freeze()
    n = env.run_native(f, DIRECT, 0, (0, 1))
    found['new_case_resets_flags'] = n.completed and n.events[0][5][2] == 0
    # Raw requests exercise the host without any C++ helper validation.
    def outer(slots=()):
        env._x87_outer = dict(function=DIRECT, entry=(0x23f, 0x21, slots), push=0, queried=False, result=None)
        env._host.fault = 0; env.errors.clear()
    def request(kind=4):
        s = NativeX87State(); s.size, s.version = C.sizeof(s), 1
        raw = NativeCall(); raw.function = DIRECT; raw.x87ArgumentCount = kind; raw.x87State = C.pointer(s)
        return raw, s
    for kind in (4, 5):
        for field in ('receiver', 'receiver2', 'argumentCount', 'stackPointer', 'x87Argument', 'x87Operation',
                      'sourceReturnPC', 'sourceTransferKind', 'sourceTransferVersion', 'sourceTransferSite',
                      'sourceCallerFunction', 'callbackActivation'):
            outer(); raw, s = request(kind); setattr(raw, field, 1)
            env._native_call(None, C.pointer(raw))
            found[f'raw_mixed_{kind}_{field}'] = env._host.fault == 5 and not s.returned
        for field, val in (('size', 0), ('version', 2), ('reserved0', 1), ('returned', 1), ('eax', 1), ('edx', 1)):
            outer(); raw, s = request(kind); s.control = 0x23f if kind == 5 else 0; setattr(s, field, val)
            env._native_call(None, C.pointer(raw))
            found[f'raw_state_{kind}_{field}'] = env._host.fault == 5 and env._x87_outer['result'] is None
        outer(); raw, s = request(kind); raw.x87State = None
        env._native_call(None, C.pointer(raw))
        found[f'raw_null_{kind}'] = bool(env._host.fault)
    outer(); raw, s = request(5); s.control, s.status = 0x23f, 0x21
    env._native_call(None, C.pointer(raw))
    found['raw_publish_without_entry'] = env._host.fault == 5
    # Raw clients cannot corrupt live slots, independently of public setup validation.
    live = ((0x8000000000000001, 0x3fff), (0, 0x8000))
    for corrupt in (False, True):
        outer(live); raw, s = request(); env._native_call(None, C.pointer(raw))
        s.returned = 0; raw.x87ArgumentCount = 5
        if corrupt: s.slots[1].signExponent ^= 0x8000
        env._native_call(None, C.pointer(raw))
        found[f'raw_live_{corrupt}'] = (env._host.fault == 5 if corrupt else s.returned == 1 and not env._host.fault)
    env._x87_outer = None
    original_callback = env._host.call
    for mode in ('ignored_entry', 'ignored_result', 'entry_push', 'entry_version', 'receipt', 'status', 'request', 'result_value'):
        def corrupt(user, pointer, mode=mode):
            kind = pointer.contents.x87ArgumentCount
            if (mode == 'ignored_entry' and kind == 4) or (mode == 'ignored_result' and kind == 5): return 0
            value = env._native_call(user, pointer)
            s = pointer.contents.x87State.contents
            if kind == 4 and mode == 'entry_push': s.pushCount = 1
            if kind == 4 and mode == 'entry_version': s.version = 2
            if kind == 5:
                if mode == 'receipt': s.returned = 0
                if mode == 'status': s.status ^= 0x20
                if mode == 'request': pointer.contents.function ^= 1
                if mode == 'result_value': return 1
            return value
        cb = CALLBACK(corrupt); env._host.call = cb
        n, _, _ = compare(env, f, flags=0x21)
        found[f'bad_host_{mode}'] = not n.completed and n.fault == 5
    env._host.call = original_callback
    # The same profile works for an owned producer with up to seven lower slots.
    from . import x87_result
    result_env, result_entry = x87_result.declared_env(), x87_result.entry(flavor)
    for cw in CONTROLS:
        for depth in (0, 1, 7):
            lower = (VALUES * 2)[:depth]
            result_env._begin_case(None)
            result_env.entry_x87(dict(control=cw, status=0x2921, slots=lower)); result_env._freeze()
            n = result_env.run_native(result_entry, x87_result.LOAD, 0, (0, 0x3ff00000))
            o = result_env.run_original(x87_result.LOAD, 0, (0, 0x3ff00000))
            found[f'profile_result_{cw:x}_{depth}'] = (
                result_env.compare(n, o, False, STACK_TOP + 12) is None and n.completed and
                n.x87[0] == cw and n.x87[2] == ((1 << 63, 0x3fff), *lower) and
                (n.x87[1] >> 11) & 7 == 4)
    return found


def declaration_checks():
    found = {}
    base = dict(abi='canonical', owned=[dict(address='0x401000', convention='cdecl', argc=2, returns='u32', x87_environment=EFFECT)])
    found['schema_valid'] = compiler_contract_errors(base) == []
    for key, val in (('returns', 'x87'), ('returns', 'context'), ('convention', 'fastcall'), ('argc', True),
                     ('argc', 33), ('source_context', {}), ('compiler_context', {}), ('attached_entries', []),
                     ('x87_result', {'pop': 0, 'push': 1}), ('x87_exact', EFFECT), ('x87_args', 1),
                     ('x87_environment', None), ('x87_environment', True), ('x87_environment', {'pop': False, 'push': 0}),
                     ('x87_environment', {'pop': 0, 'push': 1}), ('x87_environment', {**EFFECT, 'extra': 0})):
        candidate = {**base, 'owned': [{**base['owned'][0], key: val}]}
        found[f'schema_bad_{key}_{val}'] = bool(compiler_contract_errors(candidate))
    found['schema_legacy'] = bool(compiler_contract_errors({**base, 'abi': 'legacy'}))
    found['schema_callee'] = bool(compiler_contract_errors({**base, 'callees': {'0x401200': {'x87_environment': EFFECT}}}))
    env = declared_env()
    for address, effect in ((DIRECT, EFFECT), (BALANCED, EFFECT), (0x500000, EFFECT), (0x401080, None),
                            (0x401080, {'pop': False, 'push': 0}), (0x401080, {'pop': 0, 'push': 1})):
        found[f'declaration_bad_{address:x}_{effect}'] = rejected(lambda: env.owned_x87_environment(address, effect))
    found['callee_after_owner'] = rejected(lambda: env.whole_x87(DIRECT, 'cdecl', 0, exact=EFFECT))
    found['fixture_after_owner'] = rejected(lambda: env.fixture(DIRECT, 'cdecl', 0, lambda e, c: 0))
    found['guest_exclusive'] = bool(compiler_contract_errors({**base, 'oracle': {'guest_graph': {}}}))
    found['result_conflict'] = rejected(lambda: env.owned_x87_result(DIRECT, {'pop': 0, 'push': 1}))
    return found


def profile_checks(flavor):
    env, f, found = declared_env(), entry(flavor), {}
    seen_arithmetic = set()
    for index, profile in enumerate(profiles()):
        before = (profile['control'], profile['status'], profile['slots'])
        for function in (DIRECT, FACTORY, ARITH):
            arguments = (1, 0x3ff00000) if function == ARITH else (0, 123)
            env._begin_case(None); env.entry_x87(profile); env._freeze()
            n = env.run_native(f, function, 0, arguments)
            o = env.run_original(function, 0, arguments)
            found[f'profile_{index}_{function:x}'] = (env.compare(n, o, True, STACK_TOP + 4) is None and
                n.completed and o.completed and n.x87[0] == before[0] and n.x87[2] == before[2] and
                (n.x87[1] >> 11) & 7 == (before[1] >> 11) & 7)
            if function != ARITH:
                found[f'profile_entry_{index}_{function:x}'] = n.events[0][5] == ('extended-v1', *before)
                found[f'profile_final_sw_{index}_{function:x}'] = n.x87[1] & 0x4500 == 0x100
            else:
                seen_arithmetic.add(n.eax)
                expected = (0x20000000 if before[0] & 0x300 == 0 else 1) if before[0] & 0xc00 == 0x800 else 0
                found[f'profile_known_rounding_{index}'] = n.eax == o.eax == expected
    found['rounding_is_observable'] = len(seen_arithmetic) > 1
    # Eight live registers are legal for a balanced owner that needs no temporary slots.
    for top in range(8):
        profile = dict(control=0x23f, status=top << 11 | 0x4721, slots=(VALUES * 2)[:8])
        env._begin_case(None); env.entry_x87(profile); env._freeze()
        n = env.run_native(f, PRESERVE, 0, (0, 0)); o = env.run_original(PRESERVE, 0, (0, 0))
        found[f'full_stack_{top}'] = (env.compare(n, o, True, STACK_TOP + 4) is None and
            n.x87 == (profile['control'], profile['status'], profile['slots']))
    valid = dict(control=0x23f, status=0x3921, slots=VALUES[:2])
    invalid = [None, (), {}, {**valid, 'reserved': 0}, {k: v for k, v in valid.items() if k != 'status'}]
    invalid += [{**valid, 'control': cw} for cw in (True, -1, 0x23e, 0x13f, 0x123f, 0x237f, 0x223f, 0x10000, 575.0)]
    invalid += [{**valid, 'status': sw} for sw in (True, -1, 0x40, 0x80, 0x8000, 0x10000, 0.0)]
    invalid += [{**valid, 'slots': slots} for slots in (
        VALUES * 2, {0: VALUES[0]}, [None], [VALUES[0], None, VALUES[1]], [(0,)],
        [(0, 0, 0)], [(True, 0)], [(-1, 0)], [(1 << 64, 0)], [(0, -1)], [(0, 0x10000)],
        [(1, 0x3fff)], [(1 << 63, 0)], [(0, 0x7fff)], [(0, False)], [(0.0, 0)] )]
    for i, profile in enumerate(invalid):
        env._begin_case(None)
        found[f'profile_invalid_{i}'] = rejected(lambda: env.entry_x87(profile)) and env._entry_x87_profile is None
    for first, second in ((lambda: env.entry_x87(valid), lambda: env.entry_x87(valid)),
                          (lambda: env.entry_x87_status(0), lambda: env.entry_x87(valid)),
                          (lambda: env.entry_x87(valid), lambda: env.entry_x87_status(0))):
        env._begin_case(None); first()
        found[f'profile_repeated_{len(found)}'] = rejected(second)
    env._begin_case(None); env._freeze()
    found['profile_frozen'] = rejected(lambda: env.entry_x87(valid))
    mutable = {**valid, 'slots': [list(v) for v in valid['slots']]}
    env._begin_case(None); env.entry_x87(mutable)
    mutable['slots'][0][0] = 0; mutable['control'] = 0
    env._freeze(); n = env.run_native(f, PRESERVE, 0, (0, 0))
    found['profile_copied'] = n.x87 == (valid['control'], valid['status'], valid['slots'])
    found['profile_after_execution'] = rejected(lambda: env.entry_x87(valid))
    env._begin_case(None); env._freeze(); n = env.run_native(f, PRESERVE, 0, (0, 0))
    found['profile_reset'] = n.x87 == (0x23f, 0, ())
    env._begin_case(None); env.entry_x87(valid); env._freeze()
    found['profile_undeclared_native'] = rejected(lambda: env.run_native(f, BALANCED, 0, ()))
    found['profile_undeclared_original'] = rejected(lambda: env.run_original(BALANCED, 0, ()))
    found['profile_context_original'] = rejected(lambda: env.run_original_context(DIRECT, None))
    found['profile_context_native'] = rejected(lambda: env.run_native(f, DIRECT, 0, (0, 0), compiler_context=object()))
    # A result owner must have room for its extra value before either side runs.
    env.x87_environments.pop(PRESERVE)
    env.owned_x87_result(PRESERVE, {'pop': 0, 'push': 1})
    env._begin_case(None); env.entry_x87(dict(control=0x23f, status=0, slots=(VALUES * 2)[:8])); env._freeze()
    found['profile_result_overflow_native'] = rejected(lambda: env.run_native(f, PRESERVE, 0, (0, 0)))
    found['profile_result_overflow_original'] = rejected(lambda: env.run_original(PRESERVE, 0, (0, 0)))
    env.x87_results.pop(PRESERVE); env.owned_x87_environment(PRESERVE, EFFECT)
    # Supported special encodings are preserved even when no arithmetic reads them.
    special = ((0, 0), (0, 0x8000), (1, 0x8000), (1 << 63, 0x7fff),
               (1 << 63, 0xffff), (0x8000000000000001, 0x7fff), (0xc000000000000123, 0xffff))
    env._begin_case(None); env.entry_x87(dict(control=0x33f, status=0x2800, slots=special)); env._freeze()
    n = env.run_native(f, PRESERVE, 0, (0, 0)); o = env.run_original(PRESERVE, 0, (0, 0))
    found['profile_special_bits'] = env.compare(n, o, True, STACK_TOP + 4) is None and n.x87 == (0x33f, 0x2800, special)
    # Every kind of final live-state corruption must fail through the public setup path.
    original_callback = env._host.call
    for mode in ('lower', 'count', 'top', 'cw', 'sw'):
        def corrupt(user, pointer, mode=mode):
            raw = pointer.contents
            if raw.x87ArgumentCount == 5:
                s = raw.x87State.contents
                if mode == 'lower': s.slots[1].significand ^= 1
                elif mode == 'count': s.count -= 1; s.slots[s.count] = NativeX87Value()
                elif mode == 'top': s.status ^= 0x800
                elif mode == 'cw': s.control ^= 0x400
                elif mode == 'sw': s.status ^= 0x20
            return env._native_call(user, pointer)
        cb = CALLBACK(corrupt); env._host.call = cb
        env._begin_case(None); env.entry_x87(valid); env._freeze()
        n = env.run_native(f, PRESERVE, 0, (0, 0)); o = env.run_original(PRESERVE, 0, (0, 0))
        found[f'profile_publication_corrupt_{mode}'] = env.compare(n, o, True, STACK_TOP + 4) is not None
    env._host.call = original_callback
    return found


def original_checks(flavor):
    program, found = claw(), {}
    reference, env, f = Machine(program, 0x3000000, 0x40000), Env(program), entry(flavor)
    env.owned_x87_environment(0x4dca5c, EFFECT)
    env.whole_x87(0x403b40, 'thiscall', 2, exact=EFFECT)
    captures = {}
    def stop(m, pc):
        captures['after'] = m.x87_state()
        raise Halt()
    reference.observe(0x4dca61, stop)
    original_profiles = [dict(control=0x23f, status=flags, slots=()) for flags in FLAGS]
    original_profiles += [p for p in profiles() if len(p['slots']) <= 3]
    for index, profile in enumerate(original_profiles):
        before = (profile['control'], profile['status'], profile['slots'])
        for mode in ('zero', 'limit', 'random'):
            data, elapsed = motion_object(random.Random(0x403b40), mode)
            words = struct.unpack('<II', struct.pack('<d', elapsed))
            receiver = 0x3000040
            reference.write(receiver, data)
            reference.set_x87_state(*before)
            captures.clear()
            # Enter the real CALL with its two words already on the stack.
            stub_address = 0x2001000
            stub = b'\xb9' + struct.pack('<I', receiver)
            stub += b'\x68' + struct.pack('<I', words[1]) + b'\x68' + struct.pack('<I', words[0])
            stub += b'\xe9' + struct.pack('<i', 0x4dca5c - (stub_address + len(stub) + 5))
            reference.write(stub_address, stub)
            reference.uc.ctl_remove_cache(stub_address, stub_address + len(stub))
            try: reference.call(stub_address)
            except Halt: pass
            expected = captures.get('after')
            env._begin_case(random.Random(17)); env.entry_x87(profile)
            obj = env.object(len(data), 'motion', data=data, fill=0)
            env._freeze()
            n = env.run_native(f, 0x4dca5c, obj, words)
            key = f'original_{mode}_{index}'
            found[key] = (n.completed and not n.errors and expected is not None and n.x87 == expected and
                          n.events[0][5] == ('extended-v1', *before) and
                          env.read(obj, len(data)) == reference.read(receiver, len(data)))
            found[key + '_preserved'] = (expected is not None and expected[0] == before[0] and
                expected[2] == before[2] and (expected[1] >> 11) & 7 == (before[1] >> 11) & 7 and
                expected[1] & before[1] & 0x3f == before[1] & 0x3f)
    return found


def runner_checks(flavor):
    # Exercise actual runner registration/setup/comparison, with independently
    # assembled synthetic originals. No production case file or family is changed.
    spec = dict(schema=1, id='x87_environment_selftest', abi='canonical', program='selftest',
                sources=[str(MODULE.relative_to(build.ROOT))],
                owned=[dict(address=hex(f), convention='cdecl', argc=2, returns='u32', x87_environment=EFFECT)
                       for f in (DIRECT, FACTORY)],
                callees={hex(BALANCED): dict(kind='whole', convention='cdecl', argc=0, x87_exact=EFFECT),
                         hex(CONVERT): dict(kind='whole', convention='cdecl', argc=0, x87_exact={'pop': 1, 'push': 0})},
                oracle=dict(entry='claw_x87_environment_selftest_entry'))
    def cases(rng):
        for function in (DIRECT, FACTORY):
            for flags in FLAGS:
                yield Case(f'{function:x}:{flags:x}', function, setup=lambda e, flags=flags: e.entry_x87_status(flags),
                           arguments=(0, 123))
            for index, profile in enumerate(profiles()):
                yield Case(f'profile:{function:x}:{index}', function, entry_x87=profile, arguments=(0, 123))
                yield Case(f'resolver:{function:x}:{index}', function, setup=lambda e, p=profile: p,
                           entry_x87=lambda tokens: tokens, arguments=(0, 123))
    with tempfile.TemporaryDirectory(dir=build.ROOT / 'work') as directory:
        path = Path(directory) / 'spec.json'; path.write_text(json.dumps(spec))
        with patch.object(runner, 'load_program', lambda s: synthetic()), patch.object(runner, 'load_cases', lambda s: SimpleNamespace(cases=cases)):
            good = runner.run(path, flavor=flavor)
            original_only = runner.run(path, flavor=flavor, original_only=True)
            spec['owned'][0]['x87_environment'] = {'pop': 0, 'push': 1}; path.write_text(json.dumps(spec))
            bad = runner.run(path, flavor=flavor)
    return {'runner_full_path': good['status'] == 'pass' and good['cases'] == 200,
            'runner_original_only': original_only['status'] == 'pass' and original_only['cases'] == 200,
            'runner_malformed_refused': bad['status'] == 'error' and 'x87_environment' in bad.get('detail', '')}


def checks(flavor='O2'):
    return {**transport_checks(flavor), **declaration_checks(), **profile_checks(flavor),
            **original_checks(flavor), **runner_checks(flavor)}


def sanitized_checks():
    prefix, environment = build.sanitized_python()
    if prefix is None: return {'passed': False, 'detail': 'sanitizer unavailable'}
    done = subprocess.run(prefix + ['-m', 'Tests.clawparity.selftest.x87_environment', '--flavor', 'sanitize'],
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
            results[flavor] = {'checked': len(found), 'failed': [k for k, v in found.items() if not v], 'passed': all(found.values())}
        results['sanitize'] = sanitized_checks()
        passed = all(v['passed'] for v in results.values())
        print(json.dumps({'passed': passed, 'results': results}))
    else:
        found = checks(args.flavor); passed = all(found.values())
        print(json.dumps({'passed': passed, 'checked': len(found), 'failed': [k for k, v in found.items() if not v]}))
    raise SystemExit(not passed)
