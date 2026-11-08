"""Independent synthetic register/FS transport witnesses and pinned-original readiness.

The synthetic native caller uses shared transport; its two callees are x86-only.
The reference caller is separately authored x86. This admits no game function.
"""
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys

from unicorn.x86_const import UC_X86_REG_FPTAG

from .. import build
from ..env import (CALLBACK, Env, NativeCompilerContext, NativeHost, U32, check_host_layout)
from ..kernel import (CONTEXT_ALL, CONTEXT_FIELDS, CONTEXT_REQUIRED, ContextFault, Machine,
                      STACK_BASE, STACK_SIZE, STACK_TOP, STOP)
from ..program import Program, Section, claw
from .stack import relative_call


def synthetic():
    code = bytearray(b'\xcc' * 0x200)
    # Two real calls, then an explicit continuation transfer through EDI.
    caller = (relative_call(0x401000, 0x401100) + relative_call(0x401005, 0x401180) + b'\xd9\xee' +
              relative_call(0x40100c, 0x4011a0) + b'\xff\xe7')
    code[:len(caller)] = caller
    # Save incoming FS through EBP, compute a register result, move the frame,
    # publish it as FS, discard the call word and jump through ESI.
    child = bytes.fromhex('8b0424 a3 04204000 64 a1 00000000 8945fc 8d0411 8d6c2408 64 892d 00000000 8d642404 ffe6')
    code[0x100:0x100 + len(child)] = child
    # Ordinary child witnesses the previously published thread head.
    ordinary = bytes.fromhex('64 a1 00000000 a3 00204000 8d4004 64 a3 00000000 c3')
    code[0x180:0x180 + len(ordinary)] = ordinary
    floating = bytes.fromhex('dd1d 08204000 64 a1 00000000 c3')
    code[0x1a0:0x1a0 + len(floating)] = floating
    return Program('compiler-context-synthetic', '', 0x400000, 0x3000,
                   [Section('.text', 0x401000, len(code), bytes(code)),
                    Section('.data', 0x402000, 0x1000, bytes(0x1000))], (0x401000, 0x401200), {})


def context(frame=STACK_TOP, head=0xffffffff):
    return NativeCompilerContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                                 0x10203040, 0x98765432, 0x1111, 0x2222, 0x401005, 0x401080,
                                 frame + 0x80, frame, 0x401000, 0x8d7, head, 0x401080, 0, 0)


def copy_context(value):
    return NativeCompilerContext.from_buffer_copy(value)


def checks(flavor='O2'):
    library = C.CDLL(str(build.library('compiler-context-selftest',
                     [Path(__file__).with_name('compiler_context_module.cpp')], flavor)))
    entry = library.claw_compiler_context_selftest
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    validator = library.claw_compiler_context_validate
    validator.argtypes = [C.POINTER(NativeHost), C.POINTER(NativeCompilerContext), U32]
    validator.restype = U32
    dispatch = library.claw_compiler_context_call
    dispatch.argtypes = [C.POINTER(NativeHost), C.POINTER(NativeCompilerContext)]
    dispatch.restype = U32
    env = Env(synthetic())
    env.whole_x87(0x4011a0, "cdecl", 0)
    check_host_layout(env._hostlib)
    found = {'abi_layouts': True}
    for frame in (STACK_BASE + 4, STACK_TOP, STACK_BASE + STACK_SIZE - 0x100):
        for head in (0xffffffff, frame + 0x40):
            env._begin_case(None)
            env.put(frame, 0x401080)
            env._freeze()
            initial = context(frame, head)
            native_context, original_context = copy_context(initial), copy_context(initial)
            native = env.run_native(entry, 0x401000, 0, (), compiler_context=native_context)
            native_stack = bytes(env._stack)
            native_x87_empty = env.machine.register(UC_X86_REG_FPTAG) == 0xffff
            original = env.run_original_context(0x401000, original_context)
            label = f'{frame:x}_{head:x}'
            found[label + '_comparison'] = (native.completed and original.completed and not native.fault and
                not native.errors and not original.errors and native.compiler_context == original.compiler_context and
                native.heap == original.heap and native.image == original.image and native.events == original.events)
            found[label + '_outputs'] = (native_context.eax == frame + 8 and native_context.ebp == frame + 4 and
                native_context.esp == frame and native_context.fsHead == frame + 8 and
                native_context.eip == initial.continuation and native_context.eflags == initial.eflags)
            found[label + '_witnesses'] = all(getattr(native_context, name) == getattr(initial, name)
                                               for name in ('ebx', 'ecx', 'edx', 'esi', 'edi'))
            found[label + '_nested_x87'] = native_x87_empty and len(native.events) == 1
            found[label + '_nested_fs'] = struct.unpack_from('<I', native.image)[0] == frame + 4
            found[label + '_parent_stack'] = struct.unpack_from('<I', native_stack,
                initial.ebp - 4 - STACK_BASE)[0] == head
            found[label + '_real_return'] = (struct.unpack_from('<I', native.image, 4)[0] == 0x401005 and
                struct.unpack_from('<I', native_stack, frame - STACK_BASE)[0] == 0x401080)
    invalids = {'size': 68, 'version': 2, 'inputMask': CONTEXT_ALL | 0x8000, 'outputMask': 0,
                'reserved0': 1, 'reserved1': 1, 'esp': STACK_BASE - 4,
                'fsHead': STACK_BASE + STACK_SIZE - 8,
                'eip': 0x401001, 'continuation': STOP, 'eflags': 0x202}
    for name, value in invalids.items():
        bad = context()
        setattr(bad, name, value)
        rejected = False
        try:
            env.machine.call_context(0x401000, bad)
        except ContextFault:
            rejected = True
        env._host.fault = 0
        native_rejected = validator(C.byref(env._host), C.byref(bad), 0) == 0 and env._host.fault == 5
        found['reject_' + name] = rejected and native_rejected
    for name, value in (('esp', STACK_BASE + STACK_SIZE), ('esp', STACK_TOP + 1),
                         ('fsHead', 0), ('fsHead', STACK_BASE + 1), ('continuation', 0x402000)):
        bad = context()
        setattr(bad, name, value)
        try:
            env.machine.call_context(0x401000, bad)
            rejected = False
        except ContextFault:
            rejected = True
        found[f'reject_extra_{name}_{value:x}'] = rejected
    dereference = library.claw_compiler_context_dereference
    dereference.argtypes = [C.POINTER(NativeHost), C.POINTER(NativeCompilerContext)]
    dereference.restype = U32
    for old_base in (0, 1, 0xffffffff, 0x12345678, STACK_BASE + STACK_SIZE):
        value = context()
        value.ebp = old_base
        env._host.fault = 0
        found[f'opaque_ebp_{old_base:x}_accepted'] = validator(C.byref(env._host), C.byref(value), 0) == 1
        env._host.fault = 0
        accepted = dereference(C.byref(env._host), C.byref(value))
        if old_base == STACK_BASE + STACK_SIZE:
            found['opaque_ebp_valid_interior_dereference'] = accepted == 1 and not env._host.fault
        else:
            found[f'opaque_ebp_{old_base:x}_dereference_fails_closed'] = accepted == 0 and env._host.fault == 1
        env.errors.clear()
    env._host.fault = 0
    # A bare ordinary entry cannot accidentally select the special entry.
    env._host.fault = 0
    env._host.compilerContext = None
    result = U32()
    found['missing_context_is_abi_fault'] = (not entry(0x401000, 0, None, 0,
        C.byref(env._host), C.byref(result)) and env._host.fault == 5)
    # A hostile callback cannot rewrite masks or turn an ABI safety fault into return.
    saved_callback = env._host.call
    def corrupt(user, pointer):
        child = pointer.contents.compilerContext.contents
        child.eip = child.continuation
        child.outputMask = CONTEXT_REQUIRED
        return 0
    callback = CALLBACK(corrupt)
    env._host.call = callback
    env._host.fault = 0
    bad = context()
    bad.eip = 0x401100
    found['output_contract_immutable'] = not dispatch(C.byref(env._host), C.byref(bad)) and env._host.fault == 5
    for field, value in (('esp', STACK_BASE - 4), ('fsHead', 0), ('eip', STOP), ('ebx', 99)):
        def bad_output(user, pointer):
            child = pointer.contents.compilerContext.contents
            child.eip = child.continuation
            setattr(child, field, value)
            return 0
        callback = CALLBACK(bad_output)
        env._host.call = callback
        env._host.fault = 0
        bad = context()
        bad.eip, bad.outputMask = 0x401100, CONTEXT_REQUIRED
        found['reject_output_' + field] = not dispatch(C.byref(env._host), C.byref(bad)) and env._host.fault == 5
    def safety_failure(user, pointer):
        env._host.fault = 1
        return 0xe06d7363
    callback = CALLBACK(safety_failure)
    env._host.call = callback
    env._host.fault = 0
    bad = context()
    bad.eip = 0x401100
    found['safety_fault_never_returns_guest_value'] = (not dispatch(C.byref(env._host), C.byref(bad)) and
                                                       env._host.fault == 1)
    env._host.call = saved_callback
    # Minimal output mask retains the caller's unselected witnesses, while ESI
    # still supplies the real continuation as an explicitly selected input.
    partial = context()
    partial.eip, partial.continuation = 0x401100, 0x401005
    partial.outputMask = CONTEXT_REQUIRED
    partial.esp -= 4
    env.machine.write(partial.esp, struct.pack('<I', partial.continuation))
    before = copy_context(partial)
    env.machine.call_context(0x401100, partial)
    found['selected_outputs_only'] = all(getattr(partial, n) == getattr(before, n)
        for i, n in enumerate(CONTEXT_FIELDS) if not partial.outputMask & (1 << i))
    # Existing ordinary ABI still returns through STOP and resets FS only outermost.
    env.machine.fs_head = STACK_TOP
    env.machine.push_x87(0.0)
    ordinary = env.machine.call(0x4011a0, reset_thread=False)
    found['ordinary_preserves_thread_when_nested'] = ordinary.completed and ordinary.eax == STACK_TOP
    env.machine.push_x87(0.0)
    ordinary = env.machine.call(0x4011a0)
    found['ordinary_initializes_thread_at_outer_entry'] = ordinary.completed and ordinary.eax == 0xffffffff
    return found


def original_readiness():
    program = claw()  # Checks the pinned SHA before mapping or reading bytes.
    machine = Machine(program, 0x3000000, 0x1000)
    found = {}
    for frame in (STACK_BASE + 16, STACK_TOP, STACK_BASE + STACK_SIZE - 0x100):
        for head in (0xffffffff, frame + 0x40):
            value = context(frame, head)
            value.eax, value.eip, value.continuation = 0x508525, 0x4a48c0, 0x50233f
            original = copy_context(value)
            machine.write(frame, struct.pack('<2I', value.continuation, 0x10203040))
            result = machine.call_context(0x4a48c0, value)
            found[f'{frame:x}_{head:x}'] = (result.completed and value.eax == original.continuation and
                value.ebp == frame and value.esp == frame - 12 and value.fsHead == frame - 12 and
                value.eip == original.continuation and
                machine.words(frame - 16, 6) == (original.continuation, head, original.eax,
                                                0xffffffff, original.ebp, 0x10203040) and
                all(getattr(value, n) == getattr(original, n) for n in ('ebx', 'ecx', 'edx', 'esi', 'edi', 'eflags')))
    return found


def sanitized_checks():
    command, environment = build.sanitized_python()
    if command is None:
        return {'available': False}
    child = subprocess.run(command + ['-m', 'clawparity.selftest.compiler_context', '--sanitize'],
                           env=environment, capture_output=True, text=True, timeout=120)
    if child.returncode:
        return {'passed': False, 'detail': child.stderr[-2000:] or child.stdout[-2000:]}
    result = json.loads(child.stdout)
    return {'passed': not result['failed'], **result}


if __name__ == '__main__':
    values = checks('sanitize' if '--sanitize' in sys.argv else 'O0' if '--O0' in sys.argv else 'O2')
    values.update({'original_' + key: value for key, value in original_readiness().items()})
    print(json.dumps({'checked': len(values), 'failed': [key for key, value in values.items() if not value]}))
    raise SystemExit(not all(values.values()))
