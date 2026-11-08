"""Focused ordinary EnumDisplayModes transport controls, not family admission.

work/test-env/bin/python -m Tests.clawparity.selftest.enumeration_callback
"""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from .. import build
from ..env import (Env, EnumerationCallbackContract, NativeHost, U32, Halt,
                   BRIDGE_STACK, ContextFault)
from ..kernel import STACK_TOP
from ..program import Program, Section, claw

ROOT = Path(__file__).resolve().parents[3]
CALLBACK = 0x401200


def load(source, symbol, flavor='O2', defines=()):
    path = build.library('enumeration-transport', [ROOT / source], flavor, defines=defines)
    lib = C.CDLL(str(path))
    entry = getattr(lib, symbol)
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    return entry


def synthetic(ending=b'\xc2\x08\x00'):
    text = bytearray(0x1000)
    # root(context): publish incoming stack alias, invoke physical service, reload state.
    root = bytes.fromhex('53 8b5c2408 8d442408 894318 ff7304 53 6a00 6a00 ff7308 ff13 8b4310 5b c20400')
    text[:len(root)] = root
    # Unchanged bridge helper wrapper, calling root with the same argument.
    wrapper = bytes.fromhex('ff742404 e8') + struct.pack('<i', 0x401000 - 0x401109) + bytes.fromhex('c20400')
    text[0x100:0x100+len(wrapper)] = wrapper
    callback = bytes.fromhex('53 8b5c240c 8b542408 8b4b10 6bc90a 030a 894b10 8b4318 c700cefa0000 53 52 ff531c 5b b801000000') + ending
    text[0x200:0x200+len(callback)] = callback
    program = Program('synthetic-enumeration', hashlib.sha256(text).hexdigest(), 0x400000, 0x4000,
        [Section('.text', 0x401000, 0x1000, bytes(text)), Section('.data', 0x402000, 0x1000, bytes(0x1000))],
        (0x401000, 0x402000), {})
    return program, CALLBACK + len(callback)


def elect(env, service, target, end):
    body = env.read(target, end-target)
    env.enumeration_callback(EnumerationCallbackContract(env.program.sha256, service, target, end,
        hashlib.sha256(body).hexdigest()))


def clean(env):
    assert not env._enumeration_graph and not env.machine._physical_pump
    assert not env._physical_requests and not env.machine._callback_returns
    assert env._enumeration_depth == 0 and env._enumeration_frame == 0
    assert not env._host.remainingOperations
    assert env.machine.maximum_active_emulations <= 1


def same(native, original, eax=True):
    assert native.completed and original.completed, (native.errors, original.errors, native.fault)
    assert not native.errors and not original.errors
    for field in ('events', 'heap', 'image', 'spans', 'freed'):
        assert getattr(native, field) == getattr(original, field), field
    if eax:
        assert native.eax == original.eax


def setup_synthetic(action='ok', *, ending=b'\xc2\x08\x00', maximum_operations=50000):
    p, end = synthetic(ending)
    env = Env(p, maximum_operations=maximum_operations)
    context = env.object(32, 'context')
    descriptors = [env.object(0x6c, f'descriptor-{v}', words=[v]) for v in (3, 7)]
    saved = []
    seen = []

    def marker(e, call):
        seen.append((e.side, e.get(context + 16)))
        if action == 'halt':
            raise Halt()
        if action == 'fault':
            raise ContextFault('synthetic callback failure')
        if action == 'recursive':
            # A new actual service request is required for each callback depth.
            signature, effect = e._lookup(e.get(context))
            from ..env import Call
            nested = Call(signature.address, 0, 0, (context, 0, 0, context, CALLBACK), 0)
            e._serve(nested, signature, effect)
        return 0

    marker_address = env.stub('physical marker', 'stdcall', 2, marker)

    def service(e, call):
        saved.append(call)
        args = (descriptors[0], context)
        request = call
        if action == 'copied':
            request = replace(call)
        elif action == 'stale' and len(saved) > 1:
            request = saved[0]
        elif action == 'count':
            args = args[:1]
        elif action == 'negative':
            args = (-1, context)
        elif action == 'bool':
            args = (True, context)
        elif action == 'overflow':
            args = (1 << 32, context)
        elif action == 'context':
            args = (descriptors[0], context + 4)
        elif action == 'dead':
            e.release(descriptors[0])
        elif action == 'short':
            args = (descriptors[0] + 4, context)
        elif action == 'reset':
            e.run_original(0x401000, 0, (context,))
        elif action == 'reset-native':
            e.run_native(None, 0x401000, 0, (context,))
        elif action == 'reset-case':
            e._begin_case(None)
        elif action == 'swallowed':
            try:
                e.invoke_enumeration_callback(call, (0, context))
            except ContextFault:
                pass
            e.put(context + 16, 999)  # poisoned graph must reject further mutation
        elif action == 'unsupported':
            from ..env import Call
            other = Call(marker_address, 0, 0, (descriptors[0], context), 0)
            signature, _ = e._lookup(marker_address)
            e._serve(other, signature, lambda x, c: x.invoke_enumeration_callback(c, args))
        elif action == 'deadline':
            e.machine._physical_deadline = 0
        elif action == 'frame':
            object.__setattr__(call, 'stack_pointer', STACK_TOP + 2)
        before_budget = e._source_budget.value
        assert e.invoke_enumeration_callback(request, args) == 1
        after_budget = e._source_budget.value
        assert after_budget < before_budget
        assert e.get(context + 16) == 3 or action == 'mutant'
        if action == 'shared-budget':
            e._source_budget.value = 0
        assert e.invoke_enumeration_callback(call, (descriptors[1], context)) == 1
        assert e._source_budget.value < after_budget
        return 0

    service_address = env.stub('EnumDisplayModes', 'stdcall', 5, service)
    env.put(context, service_address, CALLBACK + (1 if action == 'target' else 0), context, 0, 0, 0, 0, marker_address)
    elect(env, service_address, CALLBACK, end)
    env._freeze()
    return env, context, saved, seen


def synthetic_controls(entry, mutant, rejected, fallback):
    count = 0
    for root in (0x401000, 0x401100):
        env, ctx, saved, seen = setup_synthetic()
        native = env.run_native(entry, root, 0, (ctx,))
        native_records = list(env.callback_executions)
        # Native wrapper dispatches the unchanged helper at BRIDGE_STACK.
        # Execute the reference helper at that same frame so stack aliases and
        # their event digests remain independently comparable.
        frame = STACK_TOP if root == 0x401000 else BRIDGE_STACK
        original = env.run_original(0x401000, 0, (ctx,), trace=True, check_objects=True, stack_pointer=frame)
        same(native, original)
        assert original.stack_pointer == frame + 8
        assert seen == [('native', 3), ('native', 37), ('original', 3), ('original', 37)]
        assert all(r['entered'] and r['returned'] for r in native_records + env.callback_executions)
        assert all(r['backend'] == 'native' for r in native_records)
        try:
            env.invoke_enumeration_callback(saved[-1], (ctx, ctx))
            raise AssertionError('retired request accepted')
        except ContextFault:
            pass
        clean(env)
        count += 1

    for action in ('copied', 'target', 'count', 'negative', 'bool', 'overflow', 'context', 'dead', 'short',
                   'reset', 'reset-native', 'reset-case', 'swallowed', 'fault', 'halt', 'recursive',
                   'unsupported', 'deadline', 'frame', 'shared-budget'):
        env, ctx, _, _ = setup_synthetic(action)
        results = []
        for side in ('native', 'original'):
            result = env.run_native(entry, 0x401000, 0, (ctx,)) if side == 'native' else env.run_original(0x401000, 0, (ctx,))
            assert not result.completed, (action, side)
            assert result.halted if action == 'halt' else result.errors, (action, side)
            if action == 'recursive':
                assert any('depth exceeded' in str(error) for error in result.errors), result.errors
            if action == 'shared-budget':
                assert any('operations exhausted' in str(error) for error in result.errors) or result.fault == 3
            clean(env)
            results.append(result)
            count += 1
        if action in ('fault', 'halt', 'swallowed'):
            for field in ('events', 'heap', 'image', 'spans', 'freed'):
                assert getattr(results[0], field) == getattr(results[1], field), (action, field)
            assert env._host.entryStackPointer == STACK_TOP

    env, ctx, saved, _ = setup_synthetic('stale')
    assert env.run_native(entry, 0x401000, 0, (ctx,)).completed
    retired = saved[0]
    result = env.run_original(0x401000, 0, (ctx,))
    assert not result.completed and result.errors and not env.callback_executions
    assert retired is not saved[-1]
    clean(env)
    count += 1

    for channel in ('compiler_context', 'source_context', 'original-context'):
        env, ctx, _, _ = setup_synthetic()
        try:
            if channel == 'original-context':
                env.run_original_context(0x401000, object())
            else:
                env.run_native(entry, 0x401000, 0, (ctx,), **{channel: object()})
            raise AssertionError('unsupported root context accepted')
        except ContextFault:
            pass
        count += 1

    for ending in (b'\xc3', b'\xc2\x04\x00', bytes.fromhex('bb78563412 c20800')):
        env, ctx, _, _ = setup_synthetic(ending=ending)
        result = env.run_original(0x401000, 0, (ctx,))
        assert not result.completed and result.errors
        clean(env)
        count += 1

    for replacement in ({'program_sha256': 'bad'}, {'body_sha256': 'bad'}, {'target': CALLBACK + 1},
                        {'body_end': CALLBACK}, {'service': -1}, {'service': True}, {'target': 'bad'}):
        env, ctx, _, _ = setup_synthetic()
        c, _ = next(iter(env._enumeration_contracts.values()))
        env._enumeration_contracts.clear()
        try:
            env.enumeration_callback(replace(c, **replacement))
            raise AssertionError('malformed declaration accepted')
        except ContextFault:
            pass
        count += 1

    env, _, _, _ = setup_synthetic()
    try:
        env.fixture(CALLBACK, 'stdcall', 2, 1)
        raise AssertionError('owned callback fixture accepted')
    except ContextFault:
        pass
    count += 1

    for chosen in (mutant, rejected, fallback):
        env, ctx, _, _ = setup_synthetic('mutant')
        native = env.run_native(chosen, 0x401000, 0, (ctx,))
        original = env.run_original(0x401000, 0, (ctx,))
        assert original.completed
        assert not native.completed or native.heap != original.heap
        clean(env)
        count += 1

    for side in ('native', 'original'):
        env, ctx, _, _ = setup_synthetic(maximum_operations=20)
        result = env.run_native(entry, 0x401000, 0, (ctx,)) if side == 'native' else env.run_original(0x401000, 0, (ctx,))
        assert not result.completed
        clean(env)
        count += 1
    return count


def real_profile(entry):
    env = Env(claw())
    # Only allocator/releaser platform boundaries are replaced. All container
    # bodies and both game enumeration owners execute their selected code.
    env.fixture(0x4f63ec, 'cdecl', 1, lambda e, c: e.object(c.arguments[0], 'allocation'))
    env.fixture(0x4f6428, 'cdecl', 1, lambda e, c: e.release(c.arguments[0]) if c.arguments[0] else 0)
    manager = env.object(0x884, 'manager')
    interface = env.object(4, 'DirectDraw')
    table = env.object(0x58, 'DirectDraw vtable')
    env.put(manager, interface)
    env.put(interface, table)
    for at in (manager + 0x3f0, 0x541378):
        env.put(at, 0x5133b0, 0, 0, 0, 3)
    descriptors = []
    for width, height, depth in ((800, 600, 32), (640, 480, 16), (800, 600, 16)):
        d = env.object(0x6c, 'physical display descriptor', fill=0x43)
        env.put(d, 0x6c)
        env.put(d + 8, height, width)
        env.put(d + 0x54, depth)
        descriptors.append(d)

    def enumerate_modes(e, call):
        assert call.arguments == (interface, 0, 0, 0, 0x4bcda0)
        for i, descriptor in enumerate(descriptors):
            assert e.get(0x541380) == i
            assert e.invoke_enumeration_callback(call, (descriptor, call.arguments[3])) == 1
            assert e.get(0x541380) == i + 1
        return 0

    service = env.stub('DirectDraw.EnumDisplayModes', 'stdcall', 5, enumerate_modes)
    env.put(table + 0x20, service)
    elect(env, service, 0x4bcda0, 0x4bcdd5)
    env._freeze()
    native = env.run_native(entry, 0x4bcc50, manager, ())
    records = list(env.callback_executions)
    original = env.run_original(0x4bcc50, manager, (), trace=True, check_objects=True)
    same(native, original, eax=False)  # enumerator is void
    assert len(records) == len(env.callback_executions) == 3
    assert all(r['entered'] and r['returned'] for r in records + env.callback_executions)
    assert 0x4bcda0 not in native.bridged
    assert env.get(manager + 0x3f8) == 3 and env.get(0x541380) == 0
    data = env.get(manager + 0x3f4)
    actual = []
    for i in range(3):
        d = env.get(data + i * 4)
        actual.append((env.get(d + 12), env.get(d + 8), env.get(d + 0x54)))
    assert actual == [(640, 480, 16), (800, 600, 16), (800, 600, 32)]
    assert any(pc == 0x4bcda0 for pc, _ in env.coverage)
    clean(env)
    return dict(callbacks=3, modes=actual, fixture_events=len(native.events))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--flavor', choices=('O0', 'O2', 'sanitize'), default='O2')
    parser.add_argument('--all', action='store_true', help='Run O0, O2 and ASan/UBSan serially')
    args = parser.parse_args()
    if args.all:
        for flavor in ('O0', 'O2', 'sanitize'):
            command, environment = build.sanitized_python() if flavor == 'sanitize' else ([sys.executable], None)
            subprocess.run([*command, '-m', __spec__.name, '--flavor', flavor], env=environment, check=True)
        return
    source = 'Tests/clawparity/selftest/EnumerationModule.cpp'
    symbol = 'claw_enumeration_test_entry'
    entry = load(source, symbol, args.flavor)
    mutant = load(source, symbol, args.flavor, ('ENUM_MUTANT',))
    rejected = load(source, symbol, args.flavor, ('ENUM_REJECT',))
    fallback = load(source, symbol, args.flavor, ('ENUM_FALLBACK',))
    controls = synthetic_controls(entry, mutant, rejected, fallback)
    real = load('Sources/GraphicsManagerLifecycleCanonical.cpp', 'claw_graphics_manager_lifecycle_canonical_entry', args.flavor)
    report = dict(status='pass', flavor=args.flavor, synthetic_controls=controls, real=real_profile(real))
    if args.flavor == 'O2':
        from .physical_callbacks import checks
        regression = checks('O2')
        assert all(regression.values()), [name for name, passed in regression.items() if not passed]
        report['stdcall4_regression_controls'] = len(regression)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
