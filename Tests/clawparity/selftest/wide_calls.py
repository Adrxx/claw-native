"""Independent bounded ClawCall transport, full-word and return-pop controls."""
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys

from .. import build
from ..env import Env, NativeCall, NativeHost, NativeSourceContext, U32, check_host_layout
from ..kernel import STACK_TOP, STACK_BASE, STACK_SIZE, CONTEXT_ALL, SOURCE_PRESERVABLE
from ..program import Program, Section
from .stack import relative_call

COUNTS = (0, 15, 16, 17, 31, 32)


def words(count):
    return tuple((0x81230000 + i * 0x10203) & 0xffffffff for i in range(count))


def program(count, pop=False):
    text = bytearray(b'\xcc' * 0x1000)
    # Push independent constants, execute the real child, and clean up cdecl.
    caller = b''.join(b'\x68' + struct.pack('<I', v) for v in reversed(words(count)))
    caller += relative_call(0x401000 + len(caller), 0x401400)
    if not pop:
        caller += b'\x81\xc4' + struct.pack('<I', count * 4)
    caller += b'\xc3'
    text[:len(caller)] = caller
    # Every physical word is copied to a distinct output slot; return the last.
    child = b'\x31\xc0'
    for i in range(count):
        child += b'\x8b\x84\x24' + struct.pack('<I', 4 * (i + 1))
        child += b'\xa3' + struct.pack('<I', 0x403000 + 4 * i)
    child += b'\xc2' + struct.pack('<H', count * 4) if pop else b'\xc3'
    text[0x400:0x400 + len(child)] = child
    return Program('wide-call-synthetic', '', 0x400000, 0x4000,
        [Section('.text', 0x401000, len(text), bytes(text)),
         Section('.data', 0x403000, 0x1000, bytes(0x1000))], (0x401000, 0x402000), {})


def dispatch_checks(flavor):
    sys.path.insert(0, str(build.ROOT))
    try:
        from tools.claw.gen_project import canonical_dispatch_text
    finally:
        sys.path.pop(0)
    registry = [dict(address=0x401000 + n * 16, convention='cdecl', argc=n,
        returns='u32', entry='wide_entry', family='synthetic') for n in (*COUNTS, 33)]
    text = canonical_dispatch_text(registry) + r"""
static unsigned entered;
extern "C" uint32_t wide_entry(uint32_t, uint32_t, const uint32_t *args,
    uint32_t n, ClawHost *, uint32_t *out) {
    ++entered;
    for (uint32_t i = 0; i < n; ++i) if (args[i] != 0x81230000u + i * 0x10203u) return 0;
    *out = n ? args[n - 1] : 0;
    return 1;
}
extern "C" uint32_t wide_dispatch(uint32_t n) {
    ClawCall call{}; ClawHost host{}; uint32_t out = 99;
    call.function = 0x401000 + (n > 32 ? 33 : n) * 16; call.argumentCount = n;
    for (uint32_t i = 0; i < CLAW_CALL_ARGUMENT_CAPACITY; ++i)
        call.arguments[i] = 0x81230000u + i * 0x10203u;
    entered = 0;
    auto ok = claw_canonical_dispatch(&call, &host, &out);
    bool valid = n > 32 ? (!ok && !entered && host.fault == CLAW_FAULT_ABI && out == 99) :
        (ok && entered == 1 && !host.fault && out == (n ? 0x81230000u + (n-1) * 0x10203u : 0));
    host.fault = 0; entered = 0; out = 99;
    // Ordinary rows cannot acquire source authority through the context API.
    ok = claw_canonical_dispatch_context(&call, &host, CLAW_CANONICAL_SOURCE_GRAPH, &out);
    return valid && !ok && !entered && host.fault == CLAW_FAULT_ABI && out == 99;
}
"""
    directory = build.CACHE / 'wide-call-generated'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'dispatch.cpp'
    source.write_text(text)
    library = C.CDLL(str(build.library('wide-call-dispatch', [source], flavor)))
    probe = library.wide_dispatch
    probe.argtypes, probe.restype = [U32], U32
    return {f'generated_dispatch_{n}': probe(n) == 1 for n in (*COUNTS, 33, 0xffffffff)}


def checks(flavor='O2'):
    lib = C.CDLL(str(build.library('wide-call-selftest',
        [Path(__file__).with_name('WideCallModule.cpp')], flavor)))
    entry = lib.claw_wide_call_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    source = lib.claw_wide_source
    source.argtypes = [C.POINTER(NativeHost), C.POINTER(NativeSourceContext), U32, U32]
    source.restype = U32
    found = dispatch_checks(flavor)
    from ..cases import compiler_contract_errors
    for count in (*COUNTS, 33, -1, True, 1.5, "31"):
        spec = dict(abi="canonical", owned=[dict(address="0x401000", convention="cdecl", argc=count,
            returns="u32", source_context=dict(input_mask=CONTEXT_ALL, output_mask=CONTEXT_ALL,
            preserve_mask=SOURCE_PRESERVABLE))])
        found[f"declaration_{count!r}"] = bool(compiler_contract_errors(spec)) == (type(count) is not int or count not in COUNTS)
    for count in COUNTS:
        for pop in (False, True):
            env = Env(program(count, pop))
            check_host_layout(env._hostlib)
            env._begin_case(None); env._freeze()
            native = env.run_native(entry, 0x401000, 0, (count, 0x401400, 0))
            original = env.run_original(0x401000, 0, ())
            label = f'{count}_{pop}'
            found[label + '_ordinary'] = (native.completed and original.completed and
                not native.errors and not original.errors and native.eax == original.eax and
                native.image == original.image and native.bridged == [0x401400])
            found[label + '_all_words'] = native.image[0x1000:0x1000 + count * 4] == struct.pack(f'<{count}I', *words(count))
            found[label + '_last_word'] = native.eax == (words(count)[-1] if count else 0)
            # An explicit ordinary source bridge must enforce RET cleanup and
            # compare the complete stack, including the final argument slot.
            for mode in ("valid", "wrong_pop", "wrong_ret", "last_slot"):
                if not count and mode in ("wrong_ret", "last_slot"):
                    continue
                declared_pop = not pop if mode == "wrong_ret" else pop
                env._begin_case(None); env._freeze(); env._reset_run()
                env.side = env.backend = 'native'
                env._host.fault = env._host.faultAddress = 0
                C.memmove(env._image, env._frozen[1], len(env._frozen[1]))
                C.memset(env._stack, 0, STACK_SIZE)
                env._source_graph = True
                env._native_source_entry = None
                env._source_budget = C.c_uint64(100000)
                parent = NativeSourceContext()
                parent.fsHead = 0xffffffff
                env._host.sourceContext = C.pointer(parent)
                context = NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                    0, 0, 0, 0, 0, 0, 0, STACK_TOP - 0x100, 0x401400, 2, 0xffffffff,
                    SOURCE_PRESERVABLE, 0, 0)
                env.source_callees[0x401400] = dict(kind='whole', convention='stdcall' if declared_pop else 'cdecl',
                    argc=count, returns='u32', source_context=dict(input_mask=CONTEXT_ALL,
                    output_mask=CONTEXT_ALL, preserve_mask=SOURCE_PRESERVABLE))
                env.put(context.esp, 0x401f00, *words(count))
                if mode == "last_slot":
                    env.put(context.esp + 4 * count, words(count)[-1] ^ 1)
                expected_pop = count * 4 if declared_pop else 0
                requested_pop = expected_pop + 4 if mode == "wrong_pop" else expected_pop
                ok = source(C.byref(env._host), C.byref(context), count, requested_pop)
                found[label + '_source_' + mode] = (not ok and env._host.fault == 5) if mode != 'valid' else (
                    ok == 1 and not env._host.fault and context.esp == STACK_TOP - 0x100 + 4 + expected_pop and
                    context.eip == 0x401f00 and context.eax == (words(count)[-1] if count else 0) and
                    bytes(env._stack) == env.machine.read(STACK_BASE, STACK_SIZE))
                env._host.sourceContext = None
                env._source_graph = False
    env = Env(program(32))
    for count, raw in ((33, 0), (33, 1), (0xffffffff, 1), (33, 2), (33, 3), (33, 4)):
        env._begin_case(None); env._freeze()
        failed = env.run_native(entry, 0x401000, 0, (count, 0x401400, raw))
        found[f'reject_{count}_{raw}'] = not failed.completed and failed.fault == 5 and not failed.bridged
    # A legal but mismatched count cannot silently truncate a physical call.
    env.fixture(0x401400, 'cdecl', 32, lambda e, c: 123)
    for count in (0, 16, 31):
        env._begin_case(None); env._freeze()
        failed = env.run_native(entry, 0x401000, 0, (count, 0x401400, 1))
        found[f'signature_mismatch_{count}'] = not failed.completed and bool(failed.errors) and not failed.events
    found['ctypes_capacity'] = len(NativeCall().arguments) == 32
    return found


def sanitized_checks():
    command, environment = build.sanitized_python()
    if command is None:
        return {'passed': False, 'detail': 'sanitizer runtime unavailable'}
    child = subprocess.run(command + ['-m', __package__ + '.wide_calls', '--sanitize'],
        env=environment, capture_output=True, text=True, timeout=180)
    if child.returncode:
        return {'passed': False, 'detail': child.stderr[-3000:] or child.stdout[-3000:]}
    return {'passed': True, **json.loads(child.stdout)}


if __name__ == '__main__':
    if '--all' in sys.argv:
        result = {}
        for flavor in ('O0', 'O2'):
            values = checks(flavor)
            result[flavor] = dict(checked=len(values), failed=[k for k, v in values.items() if not v])
        result['sanitize'] = sanitized_checks()
        passed = all(not result[f]['failed'] for f in ('O0', 'O2')) and result['sanitize']['passed']
    else:
        values = checks('sanitize' if '--sanitize' in sys.argv else 'O2')
        result = dict(checked=len(values), failed=[k for k, v in values.items() if not v])
        passed = not result['failed']
    print(json.dumps(result))
    raise SystemExit(not passed)
