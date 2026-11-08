"""Original/common-native constructor environment transport and refusal checks.

Run: PYTHONPATH=. work/test-env/bin/python -m Tests.NativeLevels.base_x87_check
Uses sealed constructor inputs, unchanged admitted bodies and physical fixtures.
This is a join comparison, not a family admission or full-route acceptance.
"""
import ctypes as C
import importlib.util
import hashlib
import json
import random
import struct
from collections import Counter
from types import MethodType
from pathlib import Path

from Tests.NativeLevelOne.native_join import LevelOneNativeJoin, Call, X87
from Tests.NativeMenuBase.trace import Blocked, ROOT

loader = importlib.util.spec_from_file_location('base_proof', ROOT/'scripts/check-level-eight-base-x87.py')
proof = importlib.util.module_from_spec(loader)
loader.loader.exec_module(proof)


def state_tuple(state):
    return (state.control, state.status,
            tuple((v.significand, v.exponent) for v in state.slots[:state.count]))


def packet(value):
    control, status, slots = value
    state = X87(size=C.sizeof(X87), version=1, control=control, status=status, count=len(slots))
    for slot, (significand, exponent) in zip(state.slots, slots):
        slot.significand, slot.exponent = significand, exponent
    return state


class CommonEnv(proof.Joined):
    """Reuse sealed fixture inputs; route environment handshakes to common code.

    The adapter supplies only native entry frames and memory already owned by
    Env. Every ENTRY, RESULT and exact environment decision is common join code.
    Non-joined physical/original callees retain the existing comparison harness.
    """
    def _reset_entry_x87(self):
        super()._reset_entry_x87()
        if getattr(self,'live_profile',False):
            # One exact extended value below all temporary constructor values,
            # with a nonzero TOP. Apply to both backends at the entry boundary.
            cw, sw, _ = self.machine.x87_state()
            self.machine.set_x87_state(cw, sw | (5<<11), ((0x923456789abcdef0,0x4001),))

    def _native_call(self, user, pointer):
        raw = pointer.contents
        if raw.function in getattr(self,'import_aliases',{}):
            # The old sealed Officer setup declares rectangle stand-ins through
            # named stubs. Resolve a canonical slot request to that same physical
            # identity without modifying any import slot or game instruction.
            copied = type(raw).from_buffer_copy(raw)
            copied.function = self.import_aliases[raw.function]
            return super()._native_call(user,C.pointer(copied))
        if raw.function==0x4a30e0 and raw.x87ArgumentCount==1:
            # The unchanged Officer owner still has a legacy binary64 ftol
            # edge. Normalize its physical scalar operand to the exact observer
            # declaration needed by the joined base chain, then run real ftol.
            from clawparity.env import Call as HarnessCall, NativeX87State
            from clawparity.kernel import Machine
            state = self.common.x87_ambient
            bits = struct.unpack('<II',struct.pack('<d',raw.x87Argument))
            cw, sw, slots = Machine.x87_step(self.machine,3,state_tuple(state),bits)
            exact = packet((cw,sw,slots)); exact.pop=1
            native = NativeX87State.from_buffer(exact)
            result = super()._bridge(HarnessCall(raw.function,0,0,(),0),x87=native)
            self.common.x87_ambient = exact
            return result
        if raw.function == 0x44c000 and not raw.x87ArgumentCount:
            try:
                request = Call.from_buffer_copy(raw)
                state = self.common.x87_ambient
                state.pop=state.push=state.returned=state.eax=state.edx=0
                # The original whole-callee declaration logs the exact incoming
                # environment. The ordinary native CALL borrows that same state.
                arguments = tuple(request.arguments[:request.count])
                sig = self.x87_callees[raw.function]
                captured = tuple(self._capture(k,v) for k,v in zip(sig.arguments,arguments))
                before = state_tuple(state)
                self.events.append((raw.function,raw.receiver,0,arguments,captured,
                                    ('extended-v1',*before),self._digest()))
                value = self.common.invoke(raw.function,raw.receiver,list(arguments),
                                           request.stack or self.common.child_stack())
                self.receipts.append((raw.function,before,state_tuple(self.common.x87_ambient)))
                return value
            except Exception as error:
                self.errors.append(error)
                self._host.fault = self._host.fault or 5
                return 0
        return super()._native_call(user,pointer)

    def _native_x87_outer(self, raw):
        request = Call.from_buffer_copy(raw)
        if self.negative and request.x87_count == 5 and request.function == self.negative[0]:
            state = X87.from_address(request.x87_state)
            field = self.negative[1]
            if field == 'cw': state.control ^= 0x100
            elif field == 'slot': state.slots[0].significand ^= 1
            elif field == 'top': state.status ^= 0x800
            elif field == 'push': state.push = 1
            elif field == 'missing-entry': self.common.x87_frames[-1]['entered'] = False
            elif field == 'duplicate':
                self.common.x87_outer(request)
            else: state.status ^= field
        return self.common.x87_outer(request)

    def _bridge(self, call, *args, x87=None, **kwargs):
        if call.function not in proof.CHAIN:
            return super()._bridge(call, *args, x87=x87, **kwargs)
        if x87 is None:
            raise proof.HarnessError('joined constructor requires exact transport')
        state = X87.from_address(C.addressof(x87))
        before = state_tuple(state)
        sig = self.x87_callees[call.function]
        captured = tuple(self._capture(k, v) for k, v in zip(sig.arguments, call.arguments))
        self.events.append((call.function, call.receiver, 0, call.arguments, captured,
                            ('extended-v1', *before), self._digest()))
        request = Call(function=call.function, receiver=call.receiver, count=len(call.arguments),
                       x87_count=2, x87_state=C.addressof(state))
        for i, arg in enumerate(call.arguments): request.arguments[i] = arg
        result = self.common.exact_game_call(request)
        self.receipts.append((call.function, before, state_tuple(state)))
        return result


# configure resolves this class when constructing its unchanged fixture host.
proof.Joined = CommonEnv


def attach(env, specs, entries):
    common = object.__new__(LevelOneNativeJoin)
    common.entries = {int(e['address'], 16): e for spec in specs for e in spec['owned']}
    common.native_error = None
    common.native_functions = []
    common.x87_frames = []
    common.x87_environments = Counter()
    common.x87_ambient = packet((0x23f, 0, ()))
    common.child_stack = lambda: proof.STACK_TOP - 0x800 * (len(common.x87_frames) + 1)
    env.common = common
    by_address = {int(e['address'],16): entry for spec, entry in zip(specs, entries) for e in spec['owned']}

    def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        assert not source and not return_pc
        saved = env._frame_entry, env._host.entryStackPointer
        incoming = struct.pack('<'+'I'*(len(arguments)+1), 0, *arguments)
        C.memmove(C.addressof(env._stack)+stack-proof.STACK_BASE, incoming, len(incoming))
        env._frame_entry = address, receiver, tuple(arguments), stack
        env._host.entryStackPointer = stack
        result = proof.U32()
        self.native_functions.append(address)
        try:
            done = by_address[address](address, receiver, (proof.U32*len(arguments))(*arguments),
                                       len(arguments), C.byref(env._host), C.byref(result))
            if not done or env._host.fault:
                raise Blocked(f'native join failed: {env.errors}')
            return result.value
        finally:
            self.native_functions.pop()
            env._frame_entry, env._host.entryStackPointer = saved
    common._invoke = MethodType(invoke, common)
    return common


def controls():
    common = object.__new__(LevelOneNativeJoin)
    common.x87_frames = []
    valid = packet((0x23f, 0, ()))
    entry = X87(size=C.sizeof(X87), version=1)
    request = Call(function=0x44c000, x87_count=4, x87_state=C.addressof(entry))
    rejected = []
    def reject(name, action):
        try: action()
        except Blocked: rejected.append(name); return
        raise AssertionError('Accepted '+name)
    reject('unelected-entry', lambda: common.x87_outer(request))
    for field, value in [('size', 0), ('version', 2), ('control', 0x37f), ('count', 9),
                         ('status', 0x10000), ('reserved0', 1), ('reserved1', 1)]:
        wrong = X87.from_buffer_copy(valid); setattr(wrong, field, value)
        reject('state-'+field, lambda: common.validate_x87_state(wrong))
    common.entries = {0x44c000: dict(convention='thiscall',argc=1,returns='u32',x87_environment=dict(pop=0,push=0))}
    for field, value in [('source', 1), ('compiler', 1), ('transfer_kind', 1), ('return_pc', 1),
                         ('callback_cpu', 1), ('count', 0), ('x87_operation', 1)]:
        wrong = Call(function=0x44c000, count=1); setattr(wrong,field,value)
        reject('request-'+field, lambda: common.environment_call(wrong,valid))
    common.entries[0x44c000]['x87_environment'] = dict(pop=0,push=1)
    reject('st0-disguise', lambda: common.environment_call(Call(function=0x44c000,count=1), valid))
    return rejected


def main():
    specs = [json.loads((ROOT/'Tests/families'/f'{name}.json').read_text())
             for name in (*proof.FAMILIES,'level_one_object_actions_02')]
    library = C.CDLL(str(proof.build.library('level-eight-base-x87-join',
                     [ROOT/p for spec in specs for p in spec['sources']], 'O2')))
    entries = []
    for spec in specs:
        entry = getattr(library, spec['oracle']['entry'])
        entry.argtypes = [proof.U32, proof.U32, C.POINTER(proof.U32), proof.U32,
                          C.POINTER(proof.NativeHost), C.POINTER(proof.U32)]
        entry.restype = proof.U32
        entries.append(entry)
    selected = [c for c in proof.runner.load_cases(specs[0]).cases(random.Random(0)) if c.function==0x40e0d0]
    rows, negatives = [], []
    for case, live in [(c,False) for c in selected]+[(selected[0],True)]:
        for root in (0x40e0d0, 0x44c000, 0x44bc60):
            declarations = json.loads(json.dumps(specs))
            for spec in declarations:
                spec.get('callees',{}).pop(hex(root),None)
            env = proof.configure(declarations, entries)
            if root != 0x40e0d0:
                env.owned_x87_environment(root, proof.EFFECT)
            common = attach(env, specs, entries)
            env.live_profile = live
            env._begin_case(random.Random(17))
            tokens = case.setup(env)
            env.initial_stack(proof.resolve(case.initial_stack, tokens))
            env._freeze()
            receiver = proof.resolve(case.receiver, tokens)
            arguments = tuple(proof.resolve(a, tokens)&0xffffffff for a in case.arguments)
            def joined(function, receiver, words, count, host, out):
                common.x87_ambient = packet(env.machine.x87_state())
                result = common.invoke(function, receiver, list(words[:count]), proof.STACK_TOP)
                if env._x87_outer is not None:
                    env._x87_outer['result'] = state_tuple(common.x87_ambient)
                C.cast(out,C.POINTER(proof.U32))[0] = result
                return 1
            native = env.run_native(joined, root, receiver, arguments)
            receipts = list(env.receipts)
            original = env.run_original(root, receiver, arguments)
            diff = env.compare(native, original, True, proof.STACK_TOP+8)
            if diff or not native.completed:
                raise AssertionError((case.label, hex(root), diff, native.errors))
            rows.append(dict(label=case.label,live_profile=live,root=hex(root),native=native.x87,original=original.x87,
                             receipts=receipts,environment_owners={hex(a):n for a,n in common.x87_environments.items()}))
            if root == 0x40e0d0:
                for target in (root, *proof.CHAIN):
                    for field in ('cw','slot','top','push','missing-entry','duplicate',0x20,0x100):
                        env.negative = target, field
                        try:
                            wrong = env.run_native(joined, root, receiver, arguments)
                            diff = env.compare(wrong, original, True, proof.STACK_TOP+8)
                            if diff is None: raise AssertionError(('surviving control',hex(target),field))
                        except Blocked:
                            pass
                        negatives.append((hex(target),str(field)))
    # Reuse the admitted loading caller's own sealed event-zero profiles.
    # No constructor or import fixture is replaced by a guessed game result.
    from dataclasses import replace
    loading = [c for c in proof.runner.load_cases(specs[4]).cases(random.Random(0))
               if c.function==0x462350 and c.label.startswith('event 0 constructs')]
    if len(loading)!=2: raise AssertionError('missing sealed loading profiles')
    for case in loading:
        for status in (0,0x20,0x21):
            env = proof.configure(specs,entries)
            common = attach(env,specs,entries)
            env.live_profile = status==0x21
            env._begin_case(random.Random(17))
            tokens = case.setup(env)
            env.import_aliases = {slot:env.get(slot) for slot in (0x546d5c,0x546cdc)}
            if not all(env._lookup(address) is not None for address in env.import_aliases.values()):
                raise AssertionError('sealed import alias has no declared fixture')
            env.entry_x87_status(status)
            env._freeze()
            receiver = proof.resolve(case.receiver,tokens)
            arguments = tuple(proof.resolve(a,tokens)&0xffffffff for a in case.arguments)
            native = env.run_native(joined,0x462350,receiver,arguments)
            native = replace(native,x87=state_tuple(common.x87_ambient))
            receipts = list(env.receipts)
            original = env.run_original(0x462350,receiver,arguments)
            original = replace(original,x87=env.machine.x87_state())
            diff = env.compare(native,original,True,proof.STACK_TOP+4)
            if diff or not native.completed or not any(r[0]==0x44c000 for r in receipts):
                raise AssertionError((case.label,status,diff,native.errors,receipts))
            rows.append(dict(label=case.label,root='0x462350',live_profile=env.live_profile,
                             native=native.x87,original=original.x87,receipts=receipts))
            for field in ('cw','slot','top','push',0x20,0x100):
                env.negative = 0x44c000,field
                try:
                    wrong = env.run_native(joined,0x462350,receiver,arguments)
                    wrong = replace(wrong,x87=state_tuple(common.x87_ambient))
                    if env.compare(wrong,original,True,proof.STACK_TOP+4) is None:
                        raise AssertionError(('surviving loading control',field))
                except Blocked:
                    pass
                negatives.append(('0x462350->0x44c000',str(field)))
    evidence = ROOT/'work/native-base-x87-check.json' 
    evidence.write_text(json.dumps(dict(status='pass',original_sha256=proof.claw().sha256,
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/'Tests/NativeLevelOne/native_join.py',Path(__file__).resolve(),
                      *[ROOT/path for spec in specs for path in spec['sources']]]},
        rows=rows,negative_controls=negatives,refusals=controls()),indent=2)+'\n')
    print(json.dumps(dict(status='pass',comparisons=len(rows),negative_controls=len(negatives),evidence=str(evidence))))


if __name__ == '__main__':
    main()
