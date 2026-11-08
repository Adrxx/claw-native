"""Focused original/native scenery join using sealed owner inputs.

The caller, grid iterator and missing filter execute as native owners together.
Scenery initialization is also compared with High Detail on/off and with the
hidden bit already set, as when a dormant object becomes visible after loading.
No game instructions or shared harness files are changed.
"""
import ctypes as C
import json
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'Tests')]
from clawparity import build_inputs, runner
from clawparity.env import Env, NativeHost, U32, HEAP_BASE
from clawparity.cases import resolve
from clawparity.fixtures import CATALOGUE
from clawparity.kernel import STACK_TOP
from clawparity.program import claw

KINDS = {0x461770, 0x4617d0, 0x4618e0, 0x461970}


class Joined(Env):
    def _native_call(self, user, pointer):
        q = pointer.contents
        if q.function not in self.entries:
            return super()._native_call(user, pointer)
        old = self._host.entryStackPointer
        self._host.entryStackPointer = q.stackPointer or old - 0x1000
        try:
            result = U32()
            self.calls.add(q.function)
            accepted = self.entries[q.function](q.function, q.receiver, q.arguments,
                                                q.argumentCount, C.byref(self._host), C.byref(result))
            if not accepted:
                self._host.fault = 4
            return result.value
        finally:
            self._host.entryStackPointer = old


def main():
    specs = [json.loads((ROOT / f'Tests/families/{name}.json').read_text()) for name in
             ('level_one_play_state', 'level_one_frame_resources_01', 'low_detail_scenery', 'scenery_logic')]
    env = Joined(claw(), heap_bytes=0x40000, symbols=runner.load_symbols())
    env.entries = {}
    libraries = []
    for spec in specs:
        library = C.CDLL(str(build_inputs.library(spec, 'O2')))
        libraries.append(library)
        entry = getattr(library, spec['oracle']['entry'])
        entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
        entry.restype = U32
        env.entries.update({int(o['address'], 16): entry for o in spec['owned']})
        for address, f in spec.get('callees', {}).items():
            if f['kind'] == 'fixture':
                env.fixture(int(address, 16), f['convention'], f['argc'], CATALOGUE[f['fixture']],
                            f.get('name', ''), f.get('arguments', ()))
    rows = []
    for spec in (specs[0], specs[3]):
        for case in runner.load_cases(spec).cases(random.Random(0)):
            if case.function != 0x46ef80 and case.function not in KINDS:
                continue
            env._begin_case(random.Random(17))
            tokens = case.setup(env)
            env.initial_stack(resolve(case.initial_stack, tokens))
            env._freeze()
            receiver = resolve(case.receiver, tokens)
            args = tuple(resolve(a, tokens) & 0xffffffff for a in case.arguments)
            visible = None
            if case.function in KINDS and ' z ' in case.label:
                visible = dict(high_detail=env.get(env.get(0x5371fc) + 0x124),
                               before_flags=env.get(args[0] + 8))
            env.calls = set()
            native = env.run_native(env.entries[case.function], case.function, receiver, args)
            calls = sorted(hex(f) for f in env.calls)
            original = env.run_original(case.function, receiver, args)
            declared = next(o for o in spec['owned'] if int(o['address'], 16) == case.function)
            pop = len(args) * 4 if declared['convention'] in ('thiscall', 'stdcall') else 0
            difference = env.compare(native, original, declared['returns'] != 'void', STACK_TOP + 4 + pop)
            if difference or not native.completed or not original.completed:
                raise AssertionError((case.label, difference, native.errors, original.errors))
            row = dict(label=case.label, root=hex(case.function), native_callees=calls)
            if visible is not None:
                visible['after_flags'] = struct.unpack_from('<I', native.heap, args[0] - HEAP_BASE + 8)[0]
                assert bool(visible['after_flags'] & 0x10000) == (visible['high_detail'] == 0)
                row['visible_flags'] = visible
            rows.append(row)
    assert any('0x46eff0' in row['native_callees'] and '0x4d51f0' in row['native_callees'] for row in rows)
    # Carry the actual filter output into subsequent scenery initialization.
    # In particular +0x40 bit 1 must survive when dormant scenery activates.
    scenery = runner.load_cases(specs[3])
    activation = []
    for kind in sorted(KINDS):
        for enabled in (0, 1):
            env._begin_case(random.Random(17))
            actor = scenery.scenery(flags=0x4820, enabled=enabled)(env)
            env.put(env.get(actor + 0x6c) + 0x10, kind)
            env._freeze()
            env.calls = set()
            native = env.run_native(env.entries[0x46eff0], 0x46eff0, 0, (actor,))
            original = env.run_original(0x46eff0, 0, (actor,))
            assert env.compare(native, original, False, STACK_TOP + 4) is None
            offset = actor - HEAP_BASE
            flags = struct.unpack_from('<I', native.heap, offset + 8)[0]
            dormant = struct.unpack_from('<I', native.heap, offset + 0x40)[0]
            assert flags & 0x10000 and dormant & 1
            env._initial['heap'][:] = native.heap
            env._initial['image'][:] = native.image
            env._freeze()
            native = env.run_native(env.entries[kind], kind, 0, (actor,))
            original = env.run_original(kind, 0, (actor,))
            assert env.compare(native, original, True, STACK_TOP + 4) is None
            after = struct.unpack_from('<I', native.heap, offset + 8)[0]
            after_dormant = struct.unpack_from('<I', native.heap, offset + 0x40)[0]
            assert after & 0x10000 and after_dormant == dormant
            activation.append(dict(kind=hex(kind), high_detail=enabled, before_flags=flags,
                                   after_flags=after, dormant_flags=after_dormant))
    result = dict(status='pass', check='low-detail-scenery-join', original_sha256=claw().sha256,
                  comparisons=len(rows), scenery_kinds=sorted(hex(f) for f in KINDS),
                  dormant_activation=activation, rows=rows)
    out = ROOT / 'work/parity-display/scenery-join.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
