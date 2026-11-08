#!/usr/bin/env python3
"""Compare real enemy callback/owned dispatch with inherited live x87 state.

Per-level entry setup extends the sealed cases; all game dependencies execute
unchanged original code. Family admission remains the gate's responsibility.
"""
import ctypes as C
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tests'))
from clawparity import build_inputs, runner
from clawparity.cases import resolve
from clawparity.env import Env, HarnessError, NativeHost, U32
from clawparity.fixtures import CATALOGUE
from clawparity.kernel import STACK_TOP
from clawparity.program import claw

SPEC = ROOT / 'Tests/families/level_one_enemy_actions.json'
LIVE = ((0x923456789abcdef0, 0x4000), (0xd23456789abcdef0, 0xbffe))


class Boundary(Env):
    def _reset_entry_x87(self):
        super()._reset_entry_x87()
        self.machine.set_x87_state(self.machine.initial_control_word,
                                   (self._entry_x87_status or 0) | (self.top << 11), self.live)

    def _native_x87_outer(self, raw):
        # Corrupt the module's actual publication. The existing receipt checks
        # and original/native comparison must detect each negative control.
        if raw.x87ArgumentCount == 5 and self.negative:
            state = raw.x87State.contents
            if self.negative == 'cw':
                state.control ^= 0x100
            elif self.negative == 'slot':
                state.slots[0].significand ^= 1
            elif self.negative == 'top':
                state.status ^= 0x800
            elif self.negative == 'sticky':
                state.status ^= 1
            elif self.negative == 'condition':
                state.status ^= 0x100
        return super()._native_x87_outer(raw)


def environment(spec):
    env = Boundary(claw())
    env.negative, env.top, env.live = None, 0, ()
    for text, callee in spec['callees'].items():
        address = int(text, 16)
        if callee['kind'] == 'fixture':
            env.fixture(address, callee['convention'], callee['argc'],
                        CATALOGUE[callee.get('fixture', 'scripted')],
                        callee.get('name', ''), callee.get('arguments', ()))
        elif 'x87_exact' in callee:
            env.whole_x87(address, callee['convention'], callee['argc'],
                          callee.get('name', ''), callee.get('arguments', ()), exact=callee['x87_exact'])
    for owner in spec['owned']:
        if 'x87_environment' in owner:
            env.owned_x87_environment(int(owner['address'], 16), owner['x87_environment'])
    return env


def main():
    spec = json.loads(SPEC.read_text())
    library = C.CDLL(str(build_inputs.library(spec, 'O2')))
    entry = getattr(library, spec['oracle']['entry'])
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    selected = [case for case in runner.load_cases(spec).cases(random.Random(0))
                if case.label.startswith(('owned motion ', 'owned post inherited ',
                                          'owned registry inherited ', 'owned nested inherited '))]
    if len(selected) != 126:
        raise HarnessError('expected all 126 real owned callback/dispatch profiles')
    rows, controls = [], []
    for case in selected:
        owner = next(o for o in spec['owned'] if int(o['address'], 16) == case.function)
        compare_eax = case.compare_eax if case.compare_eax is not None else owner['returns'] == 'u32'
        pops = 0 if owner['convention'] == 'cdecl' else 4 * owner['argc']
        for top, live in ((0, ()), (3, LIVE), (7, LIVE[:1])):
            env = environment(spec)
            env._begin_case(random.Random(17))
            tokens = case.setup(env)
            env.initial_stack(resolve(case.initial_stack, tokens))
            env.top, env.live = top, live
            env._freeze()
            receiver = resolve(case.receiver, tokens)
            arguments = tuple(resolve(a, tokens) & 0xffffffff for a in case.arguments)
            native = env.run_native(entry, case.function, receiver, arguments)
            original = env.run_original(case.function, receiver, arguments)
            diff = env.compare(native, original, compare_eax, STACK_TOP + 4 + pops)
            if diff or not native.completed or not original.completed:
                raise HarnessError(f'{case.label}, TOP {top}: {diff}; native={native.errors}; original={original.errors}')
            rows.append(dict(label=case.label, function=hex(case.function), top=top,
                             incoming_sw=env._entry_x87_status, live=len(live),
                             native=native.x87, original=original.x87))
            negatives = ('sticky', 'condition', 'top', 'cw', 'slot') if live else ('sticky', 'condition', 'top', 'cw')
            for negative in negatives:
                env.negative = negative
                wrong = env.run_native(entry, case.function, receiver, arguments)
                mismatch = env.compare(wrong, original, compare_eax, STACK_TOP + 4 + pops)
                if mismatch is None:
                    raise HarnessError(f'{case.label}: {negative} corruption survived')
                controls.append(dict(label=case.label, top=top, corruption=negative, kind=mismatch['kind']))
    if {r['incoming_sw'] for r in rows} != {0, 0x20, 0x21}:
        raise HarnessError('missing inherited sticky flag profiles')
    result = dict(status='pass', original_sha256=claw().sha256, cases=len(rows),
                  negative_controls=len(controls), rows=rows, controls=controls)
    out = ROOT / 'work/level-six-boss/enemy-internal-x87-result.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='pass', cases=len(rows), negative_controls=len(controls), evidence=str(out))))


if __name__ == '__main__':
    main()
