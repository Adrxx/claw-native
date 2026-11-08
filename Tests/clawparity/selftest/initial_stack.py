"""Independent ordinary stack-input transport and sensitivity controls.

Run with --all for O0, O2 and ASan/UBSan. Synthetic instructions are hand-written,
not recovered game code; absolute expected outputs detect shared transport bugs.
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
from ..cases import Case
from ..env import Env, HarnessError, NativeCompilerContext, NativeSourceContext, NativeHost, U32
from ..kernel import STACK_BASE, STACK_SIZE, STACK_TOP, STOP
from ..program import Program, Section

READ, INIT, CAPTURE = 0x401000, 0x401040, 0x402000
SOURCE = Path(__file__).with_name('InitialStackModule.cpp')


def program():
    text = bytearray(b'\xcc' * 0x100)
    # thiscall(output, word): read local at entryESP-16 and actual incoming
    # operand/return slots, publish the xor, pop the argument.
    read = bytes.fromhex('8b4424f0 33442404 330424 8901 c20400')
    text[:len(read)] = read
    # cdecl(): reserve a local, initialize it, expose its pointer to an import,
    # read back, release the local and return.
    init = bytes.fromhex('83ec10 c7042400000000 54 ff1500204000 83c404 8b0424 83c410 c3')
    text[0x40:0x40 + len(init)] = init
    return Program('initial-stack-synthetic', '', 0x400000, 0x3000,
        [Section('.text', READ, len(text), bytes(text)),
         Section('.data', CAPTURE, 0x1000, bytes(0x1000))],
        (READ, READ + len(text)), {CAPTURE: 'SYNTH.dll!capture'})


def entry(flavor, defines=()):
    library = C.CDLL(str(build.library('initial-stack-selftest', [SOURCE], flavor, defines)))
    result = library.claw_initial_stack_entry
    result.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    result.restype = U32
    return result


def manifest():
    return dict(id='initial-stack-selftest', abi='canonical', sources=[str(SOURCE)],
        owned=[dict(address=hex(READ), convention='thiscall', argc=1, returns='u32'),
               dict(address=hex(INIT), convention='cdecl', argc=0, returns='u32')],
        callees={hex(CAPTURE): dict(kind='fixture', convention='cdecl', argc=1,
            fixture='return-zero', arguments=['ptr:4'])},
        oracle=dict(entry='claw_initial_stack_entry'))


def cases(rng):
    for trial in range(3):
        seed, argument = rng.getrandbits(32) | 1, rng.getrandbits(32)
        def setup(env, seed=seed):
            return dict(output=env.object(4, 'output'), seed=struct.pack('<I', seed))
        yield Case(f'read-{trial}', READ, setup, receiver=lambda t: t['output'],
            arguments=(argument,), initial_stack=lambda t: ((-16, t['seed']),))
        yield Case(f'initialize-{trial}', INIT, initial_stack=((-16, struct.pack('<I', seed)),))
    yield Case('default-zero', READ, lambda e: e.object(4, 'output'),
        receiver=lambda t: t, arguments=(0x2468ace0,))


def checks(flavor='O2'):
    found = {}
    native_entry, omitted = entry(flavor), entry(flavor, ('INITIAL_STACK_OMIT_INITIALIZER',))
    env = Env(program())
    if flavor == 'sanitize':
        env._hostlib = C.CDLL(str(build.hostlib(flavor)))
        env._host.bytes = C.cast(env._hostlib.claw_arena_bytes, C.c_void_p)
    env.fixture(CAPTURE, 'cdecl', 1, lambda e, c: 0, arguments=('ptr:4',))
    rng = random.Random(0x1248)
    for trial, seed in enumerate((0, 0x13579bdf, rng.getrandbits(32), 0xffffffff)):
        env._begin_case(None)
        token = env.object(4, 'output')
        regions = [[-16, struct.pack('<I', seed)], [STACK_BASE - STACK_TOP, b'\x91'], [-1, b'\x83']]
        env.initial_stack(regions)
        env._freeze()
        # Mutation of caller-owned containers cannot alter either clone.
        regions[0][1] = b'\0' * 4
        env._initial['stack'][:] = b'\x56' * STACK_SIZE
        argument = rng.getrandbits(32)
        expected = seed ^ argument ^ STOP
        for repeat in range(2):
            native = env.run_native(native_entry, READ, token, (argument,))
            original = env.run_original(READ, token, (argument,))
            label = f'{trial}_{repeat}'
            found[label + '_native_expected'] = native.completed and not native.errors and native.eax == expected
            found[label + '_original_expected'] = original.completed and not original.errors and original.eax == expected
            found[label + '_comparison'] = env.compare(native, original, True, STACK_TOP + 8) is None
            found[label + '_boundary_bytes'] = (bytes(env._stack[:1]) == b'\x91' and
                env.machine.read(STACK_BASE, 1) == b'\x91' and
                bytes(env._stack[STACK_TOP - STACK_BASE - 1:STACK_TOP - STACK_BASE]) == b'\x83' and
                env.machine.read(STACK_TOP - 1, 1) == b'\x83')
        good = env.run_native(native_entry, INIT, 0, ())
        original = env.run_original(INIT, 0, ())
        bad = env.run_native(omitted, INIT, 0, ())
        found[f'{trial}_initializer_correct'] = env.compare(good, original, True, STACK_TOP + 4) is None
        difference = env.compare(bad, original, True, STACK_TOP + 4)
        found[f'{trial}_initializer_sensitivity'] = (difference is None if seed == 0 else
            difference is not None and difference['kind'] == 'event')

    invalid = [None, {}, 'bytes', [(-1, b'')], [(False, b'a')], [(-1.0, b'a')],
        [(-4, bytearray(4))], [(-4, 'word')], [(-4, 4)], [(0, b'a')], [(4, b'a')],
        [(-1, b'ab')], [(STACK_BASE - STACK_TOP - 1, b'a')], [(-4, b'abcd'), (-3, b'a')],
        [(-4, b'abcd'), (-4, b'abcd')], [(-4,)], [(-4, b'a', 1)],
        [(-i - 1, b'a') for i in range(257)]]
    for index, value in enumerate(invalid):
        env._begin_case(None)
        try:
            env.initial_stack(value)
            found[f'malformed_{index}'] = False
        except HarnessError:
            found[f'malformed_{index}'] = True
    env._begin_case(None)
    env.initial_stack([(-2, b'a'), (-1, b'b')])
    env._freeze()
    found['adjacent_regions'] = env._frozen_stack_input == ((-2, b'a'), (-1, b'b'))
    try:
        env.initial_stack(())
        found['setup_only'] = False
    except HarnessError:
        found['setup_only'] = True
    for side in ('native', 'original'):
        try:
            if side == 'native':
                env.run_native(native_entry, READ, 0, (0,), entry_stack_pointer=STACK_BASE)
            else:
                env.run_original(READ, 0, (0,), stack_pointer=STACK_BASE)
            found[side + '_relocated_bounds'] = False
        except HarnessError:
            found[side + '_relocated_bounds'] = True
    context = NativeCompilerContext()
    context.size, context.version = 72, 1
    context.inputMask = context.outputMask = 0x5c1
    context.esp, context.eip, context.fsHead, context.continuation = STACK_TOP, INIT, 0xffffffff, READ
    for side in ('native', 'original'):
        try:
            if side == 'native':
                env.run_native(native_entry, INIT, 0, (), compiler_context=context)
            else:
                env.run_original_context(INIT, context)
            found[side + '_context_exclusive'] = False
        except HarnessError as error:
            found[side + '_context_exclusive'] = 'cannot be mixed' in str(error)
    # New case discards prior explicit input; raw setup stack writes remain
    # ignored on ordinary entries, retaining default-zero compatibility.
    env._begin_case(None)
    token = env.object(4, 'output')
    env.put(STACK_TOP - 16, 0xdeadbeef)
    env._freeze()
    for side in ('native', 'original'):
        result = (env.run_native(native_entry, READ, token, (0,)) if side == 'native' else
                  env.run_original(READ, token, (0,)))
        found[side + '_default_zero'] = result.completed and result.eax == STOP

    # Runner path: callable setup input, unseen seeds, original-only validation,
    # module-source mutant execution and deliberate one-sided transport bugs.
    with tempfile.TemporaryDirectory(prefix='initial-stack-', dir=runner.ROOT / 'work') as directory:
        spec = Path(directory) / 'family.json'
        spec.write_text(json.dumps(manifest()))
        with patch.object(runner, 'load_program', lambda s: program()), \
                patch.object(runner, 'load_cases', lambda s: SimpleNamespace(cases=cases)), \
                patch.object(runner, 'load_symbols', lambda: {}):
            for seed in (0, 0x98765432):
                for original_only in (False, True):
                    result = runner.run(spec, seed=seed, flavor=flavor, original_only=original_only)
                    found[f'runner_{seed}_{original_only}'] = result['status'] == 'pass' and result['cases'] == 7
            mutant = Path(directory) / 'mutant.cpp'
            mutant.write_text(SOURCE.read_text().replace('    run.put(run.automatic(-16), 0);', '    ;'))
            result = runner.run(spec, flavor=flavor, module_source=mutant)
            found['runner_mutant_detected'] = (result['status'] == 'fail' and result['failed'] == 3 and
                all(f['kind'] == 'event' for f in result['failures']))
            for side in ('native', 'original'):
                for altered in (False, True):
                    class BrokenTransport(Env):
                        def _ordinary_stack_input(self, frame):
                            regions = super()._ordinary_stack_input(frame)
                            if self.side == side:
                                return tuple((offset, bytes(b ^ 0x80 for b in data) if altered else bytes(len(data)))
                                             for offset, data in regions)
                            return regions
                    with patch.object(runner, 'Env', BrokenTransport):
                        result = runner.run(spec, flavor=flavor)
                    found[f'detect_{side}_{"alter" if altered else "ignore"}'] = (
                        result['status'] == 'fail' and result['failed'] == 3 and
                        all(f['kind'] != 'harness' for f in result['failures']))
            for index, value in enumerate(invalid):
                with patch.object(runner, 'load_cases', lambda s, value=value: SimpleNamespace(
                        cases=lambda rng: [Case('invalid', INIT, initial_stack=value)])):
                    result = runner.run(spec, flavor=flavor)
                found[f'runner_malformed_{index}'] = (result['status'] == 'fail' and
                    result['failures'][0]['kind'] == 'harness')
            for name, value in (('compiler_context', context), ('source_context', NativeSourceContext())):
                with patch.object(runner, 'load_cases', lambda s, name=name, value=value: SimpleNamespace(
                        cases=lambda rng: [Case('mixed', INIT, initial_stack=((-4, b'abcd'),), **{name: value})])):
                    result = runner.run(spec, flavor=flavor)
                found['runner_excludes_' + name] = (result['status'] == 'fail' and
                    'cannot be mixed' in result['failures'][0]['detail'])
    return found


def sanitized_checks():
    command, environment = build.sanitized_python()
    if command is None:
        return dict(passed=False, detail='sanitizer unavailable')
    child = subprocess.run(command + ['-m', __package__ + '.initial_stack', '--sanitize'],
        env=environment, capture_output=True, text=True, timeout=180)
    if child.returncode:
        return dict(passed=False, detail=child.stderr[-3000:] or child.stdout[-3000:])
    result = json.loads(child.stdout)
    return dict(passed=not result['failed'], **result)


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
