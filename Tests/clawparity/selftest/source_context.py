"""Ordinary source frames, distinct special children, and physical callback witnesses."""
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys

from .. import build
from ..env import Halt, Env, NativeSourceContext, NativeCompilerContext, NativeHost, NativeCall, U32, CALLBACK
from ..kernel import (CONTEXT_ALL, CONTEXT_FIELDS, SOURCE_INPUT_REQUIRED, SOURCE_OUTPUT_REQUIRED,
                      SOURCE_PRESERVABLE, STACK_BASE, STACK_SIZE, STACK_TOP, STOP, ContextFault, validate_source)
from ..program import Program, Section
from .stack import relative_call


def program():
    code = bytearray(b'\xcc' * 0x400)
    # Ordinary source prologue, special helper, physical cdecl callback, exact epilogue.
    caller = (bytes.fromhex('55 89e5') + relative_call(0x401003, 0x401100) + bytes.fromhex('6a33') +
              relative_call(0x40100a, 0x401200) + bytes.fromhex('8d642404 89ec 5d 64 8f05 00000000 5d c3'))
    code[:len(caller)] = caller
    # A synthetic special helper links a two-word FS record then jumps to its real caller PC.
    helper = bytes.fromhex('58 64 ff35 00000000 55 89e5 64 8925 00000000 ffe0')
    code[0x100:0x100+len(helper)] = helper
    code[0x240:0x245] = bytes.fromhex('8b442404 c3')
    descendant = bytes.fromhex('ff742404') + relative_call(0x401264, 0x401200) + bytes.fromhex('8d642404 c3')
    code[0x260:0x260+len(descendant)] = descendant
    outer = bytes.fromhex('6a33') + relative_call(0x401382, 0x401260) + bytes.fromhex('8d642404 c3')
    code[0x380:0x380+len(outer)] = outer
    nested = bytes.fromhex('6a33') + relative_call(0x401362, 0x401240) + bytes.fromhex('8d642404 c3')
    code[0x360:0x360+len(nested)] = nested
    code[0x370:0x375] = b'\xe9' + struct.pack('<i', 0x401000 - 0x401375)
    code[0x300] = 0xc3
    code[0x320:0x325] = bytes.fromhex('8b442404 c3')
    code[0x330:0x337] = bytes.fromhex('8b442404 c20800')
    # LEA avoids undocumented flags in the mask-normalization witness.
    code[0x340:0x34b] = bytes.fromhex('8d040e 8d0c08 8d5201 c3') + b'\x90'
    # Above EAX=ESI+ECX; ECX=EAX+ECX; all are zero after normalization.
    return Program('ordinary-source-synthetic', '', 0x400000, 0x3000,
        [Section('.text', 0x401000, len(code), bytes(code)), Section('.data', 0x402000, 0x1000, bytes(0x1000))],
        (0x401000, 0x401400), {})


def context(function=0x401000, frame=STACK_TOP, ebp=0, head=0xffffffff):
    return NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
        0x12345678, 0x23456789, 0x3456789a, 0x456789ab, 0x56789abc, 0x6789abcd,
        ebp, frame, function, 0x8d7, head, SOURCE_PRESERVABLE, 0, 0)


def callback(env, call):
    s = call.source_context
    if s is None:
        raise AssertionError('physical callback lost source capability')
    for i, value in enumerate((call.source_return_pc, env.get(call.stack_pointer), s.ebp, s.fsHead,
                               s.ebx, s.esi, s.edi, call.arguments[0], s.ecx, s.edx)):
        env.put(0x402000 + i * 4, value)
    return 0xaabbccdd


def halt_callback(env, call):
    callback(env, call)
    raise Halt('synthetic physical boundary; no source EH or return claimed')


def environment():
    env = Env(program())
    env.fixture(0x401200, 'cdecl', 1, callback)
    env.compiler_callees[0x401100] = {'input_mask': CONTEXT_ALL, 'output_mask': CONTEXT_ALL}
    env.source_callees[0x401240] = {'kind':'whole', 'convention':'cdecl', 'argc':1, 'returns':'u32',
        'source_context':{'input_mask':CONTEXT_ALL, 'output_mask':CONTEXT_ALL, 'preserve_mask':SOURCE_PRESERVABLE}}
    env.source_callees[0x401260] = dict(env.source_callees[0x401240])
    return env


def native_entry(flavor):
    lib = C.CDLL(str(build.library('source-context-selftest', [Path(__file__).with_name('source_context_module.cpp')], flavor)))
    entry = lib.claw_source_context_selftest_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    return lib, entry


def checks(flavor='O2'):
    lib, entry = native_entry(flavor)
    env = environment()
    checks = {}
    for frame in (STACK_BASE + 32, STACK_TOP, STACK_BASE + STACK_SIZE - 4):
        for ebp in (0, 1, 0xffffffff, 0x12345678, frame):
            for head in (0xffffffff, STACK_TOP + 0x100):
                env._begin_case(None)
                env._freeze()
                initial = context(frame=frame, ebp=ebp, head=head)
                native_source = NativeSourceContext.from_buffer_copy(initial)
                original_source = NativeSourceContext.from_buffer_copy(initial)
                native = env.run_native(entry, 0x401000, 0, (), source_context=native_source, source_return_pc=0x401080)
                stack = bytes(env._stack)
                original = env.run_original_context(0x401000, original_source, source_return_pc=0x401080)
                label = f'{frame:x}_{ebp:x}_{head:x}'
                checks[label + '_graph'] = (native.completed and original.completed and not native.errors and not original.errors and
                    native.image == original.image and native.events == original.events and bytes(native_source) == bytes(original_source))
                checks[label + '_stack'] = stack == env.machine.read(STACK_BASE, STACK_SIZE)
                checks[label + '_real_pc'] = struct.unpack_from('<II', native.image) == (0x40100f, 0x40100f)
                checks[label + '_restored'] = (native_source.ebp == ebp and native_source.fsHead == head and
                    native_source.esp == frame + 4 and native_source.eip == 0x401080)
    # Return-pop checks cover cdecl and every callee-pop conventional signature.
    for convention in ('cdecl', 'stdcall', 'thiscall', 'fastcall'):
        function = 0x401320 if convention == 'cdecl' else 0x401330
        env._begin_case(None); env._freeze()
        s = context(function)
        receiver = s.ecx if convention in ('thiscall', 'fastcall') else 0
        receiver2 = s.edx if convention == 'fastcall' else 0
        n, o = NativeSourceContext.from_buffer_copy(s), NativeSourceContext.from_buffer_copy(s)
        args = (0x7654, 0x3210)
        kw = dict(source_return_pc=0x401080, source_convention=convention, receiver2=receiver2)
        native = env.run_native(entry, function, receiver, args, source_context=n, **kw)
        original = env.run_original_context(function, o, receiver=receiver, arguments=args, **kw)
        checks['convention_' + convention] = native.completed and original.completed and bytes(n) == bytes(o)
    env._begin_case(None); env._freeze()
    s = context(0x401340)
    s.inputMask = SOURCE_INPUT_REQUIRED | 8
    s.outputMask = SOURCE_OUTPUT_REQUIRED | 4
    s.preserveMask = 0x400
    n, o = NativeSourceContext.from_buffer_copy(s), NativeSourceContext.from_buffer_copy(s)
    native = env.run_native(entry, 0x401340, 0, (), source_context=n, source_return_pc=0x401080)
    original = env.run_original_context(0x401340, o, source_return_pc=0x401080)
    checks['normalization_all_mask_modes'] = (native.completed and original.completed and bytes(n) == bytes(o) and
        n.eax == 0 and n.ecx == 0 and n.edx == s.edx and n.ebx == s.ebx and n.esi == s.esi)
    validator = lib.claw_source_validate
    validator.argtypes = [C.POINTER(NativeHost), C.POINTER(NativeSourceContext), U32]
    validator.restype = U32
    for field, value in {'size':68, 'version':2, 'inputMask':0, 'outputMask':0, 'preserveMask':1,
                          'esp':STACK_BASE-4, 'fsHead':0, 'eip':0x401001, 'eflags':0x202,
                          'reserved0':1, 'reserved1':1}.items():
        bad = context(); setattr(bad, field, value)
        env._host.fault = 0
        rejected = validator(C.byref(env._host), C.byref(bad), 0x401080) == 0 and env._host.fault == 5
        try: validate_source(bad, 0x401000, 0x401080, env.program)
        except ContextFault: pass
        else: rejected = False
        checks['reject_' + field] = rejected
    for pc in (0, STOP, STACK_TOP, 0x402000):
        try: validate_source(context(), 0x401000, pc, env.program)
        except ContextFault: rejected = True
        else: rejected = False
        checks[f'reject_pc_{pc:x}'] = rejected
    env._host.fault = 0
    result = U32()
    checks['missing_capability'] = not entry(0x401000, 0, None, 0, C.byref(env._host), C.byref(result)) and env._host.fault == 5
    checks['retired_host_pointers'] = not env._host.sourceContext and not env._host.sourceReturnPC
    # A lower frame can pass envelope validation but must fail its checked push.
    env._begin_case(None); env._freeze()
    bad = context(frame=STACK_BASE)
    failed = env.run_native(entry, 0x401000, 0, (), source_context=bad, source_return_pc=0x401080)
    checks['source_prologue_headroom'] = not failed.completed and failed.fault == 1
    env._begin_case(None); env._freeze()
    n = context(0x401360); o = NativeSourceContext.from_buffer_copy(n)
    native = env.run_native(entry, 0x401360, 0, (), source_context=n, source_return_pc=0x401080)
    native_stack = bytes(env._stack)
    original = env.run_original_context(0x401360, o, source_return_pc=0x401080)
    checks['ordinary_original_bridge'] = (native.completed and original.completed and bytes(n) == bytes(o) and
        native_stack == env.machine.read(STACK_BASE, STACK_SIZE) and native.bridged == [0x401240])
    env.maximum_operations = 5
    env._begin_case(None); env._freeze()
    failed = env.run_native(entry, 0x401000, 0, (), source_context=context(), source_return_pc=0x401080)
    checks['shared_original_bridge_budget'] = not failed.completed and failed.fault == 3
    env.maximum_operations = 50000000
    env._begin_case(None); env._freeze()
    n = context(0x401370)
    n.outputMask = 0x5f3
    o = NativeSourceContext.from_buffer_copy(n)
    native = env.run_native(entry, 0x401370, 0, (), source_context=n, source_return_pc=0x401080)
    native_stack = bytes(env._stack)
    original = env.run_original_context(0x401370, o, source_return_pc=0x401080)
    checks['factory_masks_opaque_volatile_inputs'] = (native.completed and original.completed and bytes(n) == bytes(o) and
        native_stack == env.machine.read(STACK_BASE, STACK_SIZE) and native.image == original.image and
        struct.unpack_from('<II', native.image, 32) == (0x3456789a, 0x456789ab))
    # The C++ call boundary rejects hostile borrowed-context modifications.
    dispatch = lib.claw_source_call_test
    dispatch.argtypes = [C.POINTER(NativeHost), C.POINTER(NativeSourceContext), U32, U32]
    dispatch.restype = U32
    saved_callback = env._host.call
    for name, change in {
        'header': lambda s: setattr(s, 'inputMask', s.inputMask ^ 2),
        'version': lambda s: setattr(s, 'version', 2),
        'reserved': lambda s: setattr(s, 'reserved1', 1),
        'preserved_ebp': lambda s: setattr(s, 'ebp', s.ebp ^ 1),
        'preserved_fs': lambda s: setattr(s, 'fsHead', STACK_TOP + 16),
        'wrong_pop': lambda s: setattr(s, 'esp', s.esp + 4),
        'wrong_pc': lambda s: setattr(s, 'eip', 0x401081),
        'unselected_output': lambda s: setattr(s, 'edx', s.edx ^ 1),
        'host_fault': lambda s: setattr(env._host, 'fault', 1),
    }.items():
        parent, child = context(), context(0x401200)
        child.outputMask &= ~8
        env._host.sourceContext = C.pointer(parent)
        env._host.sourceReturnPC = 0x401080
        env._host.fault = 0
        def corrupt(user, pointer):
            s = pointer.contents.sourceContext.contents
            s.eip, s.esp = pointer.contents.sourceReturnPC, s.esp + 4
            change(s)
            return s.eax
        thunk = CALLBACK(corrupt)
        env._host.call = thunk
        checks['hostile_' + name] = not dispatch(C.byref(env._host), C.byref(child), 0x401080, 0) and bool(env._host.fault)
    env._host.call = saved_callback
    env._host.sourceContext = None
    env._host.sourceReturnPC = 0
    env._host.fault = 0
    child = context(0x401200)
    checks['retired_source_dispatch'] = not dispatch(C.byref(env._host), C.byref(child), 0x401080, 0) and env._host.fault == 5
    # Envelope/code/mask failures cannot silently enter a declared original dependency.
    for name in ('missing_special', 'missing_ordinary', 'wrong_ordinary_masks', 'legacy_outbound'):
        trial = environment()
        function = 0x401000
        if name == 'missing_special': trial.compiler_callees.clear()
        if name in ('missing_ordinary', 'wrong_ordinary_masks'):
            function = 0x401360
            if name == 'missing_ordinary': trial.source_callees.clear()
            else: trial.source_callees[0x401240]['source_context']['output_mask'] ^= 2
        trial._begin_case(None); trial._freeze()
        if name == 'legacy_outbound':
            trial._source_graph = True
            parent = context()
            trial._host.sourceContext = C.pointer(parent)
            call = NativeCall(); call.function = 0x401200; call.argumentCount = 1
            trial._native_call(None, C.pointer(call))
            checks['reject_' + name] = trial._host.fault == 5
            trial._host.sourceContext = None; trial._source_graph = False
        else:
            failed = trial.run_native(entry, function, 0, (), source_context=context(function), source_return_pc=0x401080)
            checks['reject_' + name] = not failed.completed and failed.fault == 5
    trial = environment(); trial._begin_case(None); trial._freeze()
    wrong = context(0x401330)
    original = trial.run_original_context(0x401330, wrong, arguments=(1, 2), source_return_pc=0x401080, source_convention='cdecl')
    checks['original_wrong_ret_pop'] = not original.completed and any(isinstance(e, ContextFault) for e in original.errors)
    # A source pointer can never select the special channel, or vice versa.
    trial._host.sourceContext = C.pointer(context())
    trial._host.compilerContext = C.pointer(NativeCompilerContext())
    trial._host.fault = 0
    result = U32()
    checks['dual_entry_channels'] = not entry(0x401000, 0, None, 0, C.byref(trial._host), C.byref(result)) and trial._host.fault == 5
    trial._host.sourceContext = None; trial._host.compilerContext = None
    for function in (0x401000, 0x401380):
        trial = environment(); trial._begin_case(None)
        trial.override(0x401200, halt_callback); trial._freeze()
        n = context(function); o = NativeSourceContext.from_buffer_copy(n)
        native = trial.run_native(entry, function, 0, (), source_context=n, source_return_pc=0x401080)
        stack = bytes(trial._stack)
        original = trial.run_original_context(function, o, source_return_pc=0x401080)
        checks[f'physical_halt_prefix_{function:x}'] = (native.halted and original.halted and not native.completed and
            not original.completed and native.source_stop is not None and native.source_stop == original.source_stop and
            stack == trial.machine.read(STACK_BASE, STACK_SIZE) and native.image == original.image and native.events == original.events)
        checks[f'halt_retires_scope_{function:x}'] = not trial._source_graph and not trial._host.sourceContext
    trial = environment(); trial._begin_case(None); trial._freeze()
    legacy = trial.run_native(entry, 0x4013a0, 0, ())
    checks['per_entry_legacy_opt_out'] = legacy.completed and legacy.eax == 42
    bad = trial.run_native(entry, 0x4013a0, 0, (), source_context=context(0x4013a0), source_return_pc=0x401080)
    checks['per_entry_legacy_rejects_source'] = not bad.completed and bad.fault == 5
    trial = environment()
    for address in (0x401100, 0x401240):
        try: trial.fixture(address, 'cdecl', 0, lambda e, c: 0)
        except ContextFault: rejected = True
        else: rejected = False
        checks[f'original_dependency_fixture_rejected_{address:x}'] = rejected
    trial._source_graph = True
    try: trial.run_native(entry, 0x401300, 0, (), source_context=context(0x401300), source_return_pc=0x401080)
    except ContextFault: rejected = True
    else: rejected = False
    checks['reentrant_outer_graph_rejected'] = rejected
    trial._source_graph = False
    return checks


def sanitized_checks():
    command, environ = build.sanitized_python()
    if command is None: return {'passed':False, 'error':'sanitizer unavailable'}
    result = subprocess.run(command + ['-m', __name__, '--sanitized-child'], env=environ, capture_output=True, text=True)
    try: report = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError): report = {'passed':False}
    return {**report, 'returncode':result.returncode, 'stderr':result.stderr[-2000:], 'passed':result.returncode == 0 and report.get('passed', False)}


if __name__ == '__main__':
    found = checks('sanitize' if '--sanitized-child' in sys.argv else 'O2')
    failed = [name for name, passed in found.items() if not passed]
    print(json.dumps({'checked':len(found), 'failed':failed, 'passed':not failed}))
    raise SystemExit(bool(failed))
