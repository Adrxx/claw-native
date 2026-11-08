#!/usr/bin/env python3
"""Native constructor join comparison over sealed family inputs; admits nothing."""
import ctypes as C
import json
import random
import struct
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tests'))
from clawparity import build, runner
from clawparity.cases import resolve, caller_frame_base
from clawparity.env import Env, HarnessError, NativeHost, NativeX87Value, U32
from clawparity.fixtures import CATALOGUE
from clawparity.kernel import STACK_BASE, STACK_TOP
from clawparity.program import claw
FAMILIES = ('level_two_raux_shared', 'level_one_object_actions_01',
            'level_one_enemy_actions', 'level_one_actor_dispatch_01')
CHAIN = {0x44c000: 1, 0x4dca10: 2, 0x403b40: 3}
EFFECT = {'pop': 0, 'push': 0}

class Joined(Env):
    """Route balanced joins into native owners, retaining standard host checks.

    Nested scopes restore the caller's ENTRY/RESULT and caller-frame state.
    Memory is never reset while a nested owner executes.
    """
    def _bridge(self, call, *args, x87=None, **kwargs):
        if call.function not in CHAIN:
            return super()._bridge(call, *args, x87=x87, **kwargs)
        if x87 is None:
            raise HarnessError('joined constructor requires exact transport')
        before = (x87.control, x87.status,
                  tuple((v.significand, v.signExponent) for v in x87.slots[:x87.count]))
        sig = self.x87_callees[call.function]
        captured = tuple(self._capture(k, v) for k, v in zip(sig.arguments, call.arguments))
        self.events.append((call.function, call.receiver, 0, call.arguments, captured,
                            ('extended-v1', *before), self._digest()))
        saved = self._x87_outer, self._frame_entry, self._host.entryStackPointer
        self.join_depth += 1
        frame = STACK_TOP - 0x800 * self.join_depth
        incoming = struct.pack('<' + 'I' * (1 + len(call.arguments)), 0, *call.arguments)
        C.memmove(C.addressof(self._stack) + frame - STACK_BASE, incoming, len(incoming))
        self._host.entryStackPointer = frame
        self._frame_entry = (call.function, call.receiver, call.arguments, frame)
        self._x87_outer = dict(function=call.function, entry=before, queried=False, result=None, push=0)
        result = U32()
        words = (U32 * len(call.arguments))(*call.arguments)
        try:
            ok = self.entries[CHAIN[call.function]](call.function, call.receiver, words,
                len(call.arguments), C.byref(self._host), C.byref(result))
            published = self._x87_outer['result']
            if not ok or self._host.fault or published is None:
                raise HarnessError(f'native join {call.function:#x} failed: {self.errors}')
            control, status, slots = published
            if control != before[0] or slots != before[2] or (status & 0x3800) != (before[1] & 0x3800):
                raise HarnessError('native join corrupted CW, TOP or live slots')
            self.receipts.append((call.function, before, published))
            if self.negative and self.negative[0] == call.function:
                corruption = self.negative[1]
                if corruption == 'cw':
                    control ^= 0x100
                elif corruption == 'slot':
                    slots = slots + ((0x8000000000000000, 0x3fff),)
                else:
                    status ^= corruption
            x87.control, x87.status, x87.count = control, status, len(slots)
            for i in range(8):
                x87.slots[i] = NativeX87Value(*(slots[i] if i < len(slots) else (0, 0)), 0)
            x87.returned, x87.eax, x87.edx = 1, result.value, 0
            return result.value
        finally:
            self._x87_outer, self._frame_entry, self._host.entryStackPointer = saved
            self.join_depth -= 1

def configure(specs, entries):
    env = Joined(claw())
    env.entries, env.join_depth, env.negative, env.receipts = entries, 0, None, []
    declarations = {}
    for spec in specs:
        for address, callee in spec.get('callees', {}).items():
            if callee.get('kind') == 'fixture' or 'x87_exact' in callee or 'caller_frame' in callee:
                declarations.setdefault(address, (callee, spec))
    for text, (callee, owner) in declarations.items():
        address = int(text, 16)
        if callee.get('kind') == 'fixture':
            env.fixture(address, callee['convention'], callee['argc'],
                        CATALOGUE[callee.get('fixture', 'scripted')], callee.get('name', ''),
                        callee.get('arguments', ()))
        elif 'x87_exact' in callee:
            env.whole_x87(address, callee['convention'], callee['argc'],
                          callee.get('name', ''), callee.get('arguments', ()), exact=callee['x87_exact'])
        elif 'caller_frame' in callee:
            rules = []
            for d in callee['caller_frame']:
                argc = next(o['argc'] for o in owner['owned'] if o['address'] == d['caller'])
                rules.append((int(d['caller'], 16), int(d['site'], 16),
                              *caller_frame_base(d['ebp']['base'], argc), d['ebp']['offset']))
            ranges = runner.owned_ranges(owner)
            env.caller_frame(address, callee['convention'], callee['argc'], rules,
                             {start: [tuple(r) for r in found] for start, found in ranges.items()})
    env.owned_x87_environment(0x40e0d0, EFFECT)
    return env


def main():
    specs = [json.loads((ROOT / 'Tests/families' / (name + '.json')).read_text()) for name in FAMILIES]
    sources = [ROOT / path for spec in specs for path in spec['sources']]
    library = C.CDLL(str(build.library('level-eight-base-x87-join', sources, 'O2')))
    entries = []
    for spec in specs:
        entry = getattr(library, spec['oracle']['entry'])
        entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
        entry.restype = U32
        entries.append(entry)
    selected = [case for case in runner.load_cases(specs[0]).cases(random.Random(0))
                if case.function == 0x40e0d0]
    if not selected:
        raise HarnessError('sealed raux cases contain no constructor input')
    rows, controls = [], []
    for case in selected:
        env = configure(specs, entries)
        env._begin_case(random.Random(17))
        tokens = case.setup(env)
        env.initial_stack(resolve(case.initial_stack, tokens))
        env._freeze()
        receiver = resolve(case.receiver, tokens)
        arguments = tuple(resolve(a, tokens) & 0xffffffff for a in case.arguments)
        native = env.run_native(entries[0], case.function, receiver, arguments)
        receipts = list(env.receipts)
        original = env.run_original(case.function, receiver, arguments)
        diff = env.compare(native, original, True, STACK_TOP + 8)
        if diff or not native.completed or {r[0] for r in receipts} != set(CHAIN):
            raise HarnessError(f'{case.label}: {diff}; receipts={receipts}')
        rows.append(dict(label=case.label, incoming_sw=env._entry_x87_status, native=native.x87, original=original.x87, receipts=receipts))
        for target, mask in ((target, mask) for target in CHAIN for mask in (0x20, 0x100, 0x800, 'cw', 'slot')):
            env.negative, env.receipts = (target, mask), []
            wrong = env.run_native(entries[0], case.function, receiver, arguments)
            mismatch = env.compare(wrong, original, True, STACK_TOP + 8)
            if mismatch is None:
                raise HarnessError(f'negative environment control survived at {target:#x}')
            controls.append(dict(label=case.label, target=hex(target), mask=hex(mask) if isinstance(mask, int) else mask, kind=mismatch['kind']))
    if {row['incoming_sw'] for row in rows} != {0, 0x20, 0x21}:
        raise HarnessError('constructor inputs must cover inherited SW0/20/21')
    if not {0x100, 0x120, 0x121}.issubset({row['original'][1] for row in rows}):
        raise HarnessError('original constructor lacks observed post-base100/120/121')
    result = dict(status='pass', original_sha256=claw().sha256, cases=len(rows),
                  negative_controls=len(controls), rows=rows, controls=controls)
    out = ROOT / 'work/level-eight-boss/base-native-x87-result.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='pass', cases=len(rows), negative_controls=len(controls), evidence=str(out))))


if __name__ == '__main__':
    main()
