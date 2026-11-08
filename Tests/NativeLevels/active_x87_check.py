"""Focused original/native checks for active level-join x87 environments.

Run as Tests.NativeLevels.active_x87_check. Uses unchanged sealed setup inputs
and real original/native owners; this comparison does not admit a family or
establish parity for a complete level route.
"""
import ctypes as C
import hashlib
import json
import random
import struct
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace, MethodType

from Tests.NativeLevels.base_x87_check import attach, packet, proof, state_tuple
from Tests.NativeLevelOne.native_join import Call, X87, Source, LevelOneNativeJoin
from Tests.NativeMenuBase.trace import Blocked, ROOT

FAMILIES = ('level_one_enemy_actions', 'soldier_state_methods',
            'level_one_object_actions_01', 'mercat_helper_01',
            'level_one_player_actions_01', 'red_tail_pirate_core')
TARGETS = {0x43d490, 0x43e420, 0x4dca10}
INNER = TARGETS | {0x44c840, 0x44d000}
LOOT_PATH = (0x4dc830, 0x483ae0, 0x44df60, 0x483e10,
             0x44e0c0, 0x42df90, 0x40e690)


class ActiveEnv(proof.Env):
    def _reset_entry_x87(self):
        super()._reset_entry_x87()
        self.machine.set_x87_state(0x23f, self.profile,
            tuple((0x923456789abcdef0+i, 0x4001+i) for i in range(self.live)))

    def _native_x87_outer(self, raw):
        request = Call.from_buffer_copy(raw)
        if self.negative and request.x87_count == 5 and request.function in TARGETS:
            state = X87.from_address(request.x87_state)
            if self.negative == 'cw': state.control ^= 0x100
            elif self.negative == 'slot': state.slots[0].significand ^= 1
            elif self.negative == 'top': state.status ^= 0x800
            elif self.negative == 'push': state.push = 1
            elif self.negative == 'missing-entry': self.common.x87_frames[-1]['entered'] = False
            elif self.negative == 'duplicate': self.common.x87_outer(request)
            else: state.status ^= self.negative
        return self.common.x87_outer(request)

    def log_boundary(self, function, receiver, arguments, before):
        sig = self.x87_callees.get(function)
        if sig is not None:
            captured = tuple(self._capture(k, v) for k, v in zip(sig.arguments, arguments))
            self.events.append((function, receiver, 0, tuple(arguments), captured,
                                ('extended-v1', *before), self._digest()))

    def _native_call(self, user, pointer):
        raw = pointer.contents
        if raw.function not in INNER or raw.x87ArgumentCount:
            return super()._native_call(user, pointer)
        try:
            request = Call.from_buffer_copy(raw)
            before = self.incoming_state()
            arguments = tuple(request.arguments[:request.count])
            self.log_boundary(raw.function, raw.receiver, arguments, before)
            value = self.common.invoke(raw.function, raw.receiver, list(arguments),
                                       request.stack or self.common.child_stack(), request.source, request.return_pc)
            self.receipts.append((raw.function, before, state_tuple(self.common.x87_ambient)))
            return value
        except Exception as error:
            self.errors.append(error)
            self._host.fault = self._host.fault or 5
            return 0

    def incoming_state(self):
        frames = self.common.x87_frames
        if frames:
            frame = frames[-1]
            state = frame.get('ordinary_cursor', frame.get('caller'))
            if state is not None:
                return state_tuple(state)
        return state_tuple(self.common.x87_ambient)

    def _bridge(self, call, *args, x87=None, **kwargs):
        if call.function not in INNER:
            return super()._bridge(call, *args, x87=x87, **kwargs)
        if x87 is None:
            raise proof.HarnessError('joined exact boundary is missing x87 packet')
        state = X87.from_address(C.addressof(x87))
        before = state_tuple(state)
        self.log_boundary(call.function, call.receiver, call.arguments, before)
        request = Call(function=call.function, receiver=call.receiver,
                       count=len(call.arguments), x87_count=2, x87_state=C.addressof(state))
        for i, value in enumerate(call.arguments): request.arguments[i] = value
        result = self.common.exact_game_call(request)
        self.receipts.append((call.function, before, state_tuple(state)))
        return result


def attach_source_frame(env, specs, entries):
    """Mirror NativeJoin.invoke's optional source entry in this small adapter.

    Base comparison attach deliberately invokes ordinary entries directly. The
    Level 2 dispatch instead needs the checked original CPU/frame capability
    that the real native join supplies for optional source owner 0x44c840.
    Every nested invocation saves and restores both source host fields.
    """
    from clawparity.env import NativeSourceContext
    from Tests.NativeMenuBase.trace import STOP
    common = attach(env, specs, entries)
    by_address = {int(e['address'],16):entry
                  for spec, entry in zip(specs, entries) for e in spec['owned']}
    def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        if source or return_pc:
            raise AssertionError('source packet must use the checked common provider')
        saved = (env._frame_entry, env._host.entryStackPointer,
                 C.cast(env._host.sourceContext, C.c_void_p).value, env._host.sourceReturnPC)
        cpu = None
        contract = self.entries.get(address, {}).get('source_context')
        if contract:
            cpu = Source(size=C.sizeof(Source), version=1,
                input_mask=contract['input_mask'], output_mask=contract['output_mask'],
                preserve_mask=contract['preserve_mask'], esp=stack, eip=address,
                ecx=receiver, eflags=2, fs_head=env.machine.fs_head)
            return_pc = STOP
            frame_return = STOP
        else:
            # Preserve the CALL return word in an existing source child frame,
            # exactly as LevelOneNativeJoin._invoke does for ordinary owners.
            frame_return = env.get(stack) if self.native_functions else STOP
        incoming = struct.pack('<'+'I'*(len(arguments)+1), frame_return, *arguments)
        C.memmove(C.addressof(env._stack)+stack-proof.STACK_BASE, incoming, len(incoming))
        env._frame_entry = address, receiver, tuple(arguments), stack
        env._host.entryStackPointer = stack
        env._host.sourceContext = (C.cast(C.pointer(cpu), C.POINTER(NativeSourceContext))
                                   if cpu is not None else C.POINTER(NativeSourceContext)())
        env._host.sourceReturnPC = return_pc
        output = proof.U32()
        self.native_functions.append(address)
        try:
            done = by_address[address](address, receiver,
                (proof.U32*len(arguments))(*arguments), len(arguments),
                C.byref(env._host), C.byref(output))
            if not done or env._host.fault:
                raise Blocked(f'native source-frame {address:#x} join failed: code {env._host.fault} at {env._host.faultAddress:#x}; {env.errors}')
            return output.value
        finally:
            self.native_functions.pop()
            env._frame_entry, env._host.entryStackPointer = saved[:2]
            env._host.sourceContext = C.cast(saved[2], C.POINTER(NativeSourceContext))
            env._host.sourceReturnPC = saved[3]
    common._invoke = MethodType(invoke, common)
    return common


def configure(specs, entries):
    previous = proof.Joined
    try:
        proof.Joined = ActiveEnv
        env = proof.configure(specs, entries)
    finally:
        proof.Joined = previous
    for target in TARGETS:
        if target not in env.x87_callees:
            argc = next(e['argc'] for s in specs for e in s['owned'] if int(e['address'], 16) == target)
            env.whole_x87(target, 'thiscall', argc, 'joined active environment', exact=proof.EFFECT)
    return env


def inputs(specs):
    enemy = list(proof.runner.load_cases(specs[0]).cases(random.Random(0)))
    action = next(c for c in enemy if c.label == 'dispatch genuine owned zero-argument action')
    def dispatch_setup(env):
        tokens = action.setup(env)
        # Both real dispatchers fall through their empty, already-in-range
        # tables to the unchanged owned action. No game callback is replaced.
        for address in (0x53c328, 0x537878):
            table = env.object(4, 'empty-dispatch-slot', fill=0)
            env.put(address+8, 2, 2, table, table, 4, table, 0)
        return tokens
    yield replace(action, label='Soldier through both real inherited dispatchers',
                  function=0x48b0c0, setup=dispatch_setup), 0x43d490, 'soldier'
    mercat = list(proof.runner.load_cases(specs[3]).cases(random.Random(0)))
    for prefix in ('inherited update compare 99.5 100 SW 0x0',
                   'inherited update compare 100.5 100 SW 0x0',
                   'inherited update compare nan 17 SW 0x0'):
        yield next(c for c in mercat if c.label == prefix), 0x43e420, 'mercat'
    loot = [c for c in proof.runner.load_cases(specs[4]).cases(random.Random(0))
            if c.function == 0x40e690 and c.label.startswith('begin state zero')]
    if len(loot) != 4: raise AssertionError('missing sealed loot inputs')
    for case in loot:
        yield case, 0x4dca10, 'loot'


def refusals(specs):
    """Host contract controls; none supplies a game callee's result."""
    common = object.__new__(LevelOneNativeJoin)
    common.entries = {int(e['address'], 16):e for s in specs for e in s['owned']}
    common.native_error = common.error_stack = None
    common.x87_ambient = packet((0x23f, 0x2821, ((0x923456789abcdef0, 0x4001),)))
    common.child_stack = lambda: proof.STACK_TOP
    rejected = []
    def reject(name, action):
        try: action()
        except Blocked: rejected.append(name); return
        raise AssertionError('accepted '+name)
    def unexpected(*args, **kwargs):
        raise AssertionError('invalid request reached game owner')
    common._invoke = unexpected
    for path, exact in ((LOOT_PATH, False), ((0x44d000,), True)):
        target = 0x43e420 if exact else 0x4dca10
        for fault in ('ancestor', 'path', 'unentered', 'published', 'missing-live',
                      'source', 'continuation', 'target'):
            common.native_functions = list(path)
            frame = dict(function=path[0], caller=X87.from_buffer_copy(common.x87_ambient),
                entered=True, result=None, push=0, ordinary_cursor=X87.from_buffer_copy(common.x87_ambient))
            if exact: frame['exact_scope'] = True
            common.x87_frames = [frame]
            source, continuation, called = None, 0, target
            source_packet = Source()
            if fault == 'ancestor': frame['function'] ^= 1
            elif fault == 'path': common.native_functions[-1] ^= 1
            elif fault == 'unentered': frame['entered'] = False
            elif fault == 'published': frame['result'] = common.x87_ambient
            elif fault == 'missing-live': frame.pop('ordinary_cursor')
            elif fault == 'source': source = C.addressof(source_packet)
            elif fault == 'continuation': continuation = 1
            elif fault == 'target': called = 0x43dfa0
            reject(('exact-' if exact else 'loot-')+fault,
                lambda: common.invoke(called, 0x1234, [], proof.STACK_TOP, source, continuation))
    # The genuine source CALL must retain its checked CPU and stack frame.
    stack, receiver, argument = proof.STACK_TOP-0x1000, 0x1234, 2
    for fault in ('caller', 'continuation', 'size', 'version', 'input_mask', 'output_mask',
                  'preserve_mask', 'eip', 'reserved0', 'reserved1', 'esp', 'return-word',
                  'argument-word', 'receiver', 'argument-count'):
        common.native_functions = [0x44c840]
        common.x87_frames = []
        words = {stack:0x44c94a, stack+4:argument}
        common.word = words.__getitem__
        cpu = Source(size=C.sizeof(Source), version=1, input_mask=0x7ff,
            output_mask=0x7ff, preserve_mask=0x472, ecx=receiver, esp=stack, eip=0x43d490)
        continuation, passed_receiver, arguments = 0x44c94a, receiver, [argument]
        if fault == 'caller': common.native_functions = [0x44c841]
        elif fault == 'continuation': continuation ^= 1
        elif fault == 'return-word': words[stack] ^= 1
        elif fault == 'argument-word': words[stack+4] ^= 1
        elif fault == 'receiver': passed_receiver ^= 1
        elif fault == 'argument-count': arguments = []
        else: setattr(cpu, fault, getattr(cpu, fault)^1)
        reject('source-'+fault, lambda: common.invoke(0x43d490, passed_receiver,
            arguments, stack, C.addressof(cpu), continuation))
    common.native_functions = [0x460af0]
    for fault in ('wrong-caller', 'missing-parent', 'wrong-parent', 'unentered-parent', 'published-parent',
                  'source', 'return_pc', 'receiver2', 'compiler', 'transfer_version',
                  'transfer_kind', 'transfer_site', 'caller', 'disposition', 'callback_cpu',
                  'callback_activation', 'x87_operation', 'x87_argument', 'count', 'unused-argument'):
        common.native_functions = [0x460af0]
        state = X87.from_buffer_copy(common.x87_ambient)
        request = Call(function=0x44d000, receiver=receiver, count=1, x87_count=2,
                       x87_state=C.addressof(state))
        request.arguments[0] = argument
        frame = dict(function=0x460af0, entered=True, result=None)
        common.x87_frames = [frame]
        if fault == 'wrong-caller': common.native_functions = [0x460af1]
        elif fault == 'missing-parent': common.x87_frames = []
        elif fault == 'wrong-parent': frame['function'] ^= 1
        elif fault == 'unentered-parent': frame['entered'] = False
        elif fault == 'published-parent': frame['result'] = state
        elif fault == 'unused-argument': request.arguments[1] = 1
        elif fault == 'count': request.count = 0
        else: setattr(request, fault, 1)
        reject('exact-request-'+fault, lambda: common.exact_game_call(request))
    for field, value in (('size', 0), ('version', 2), ('control', 0x37f), ('status', 0x10000),
                         ('count', 9), ('reserved0', 1), ('reserved1', 1)):
        state = X87.from_buffer_copy(common.x87_ambient)
        setattr(state, field, value)
        reject('environment-'+field, lambda: common.validate_x87_state(state))
    faults = []
    common.library = SimpleNamespace(menu_fault=lambda host, target:faults.append(target))
    common.host = None
    common.x87_frames = [dict(function=0x44d000)]
    common.native_functions = [0x44d000]
    for target, count in ((0x43d490, 1), (0x43e420, 0), (0x4dca10, 0)):
        for field in ('stack', 'count', 'receiver2', 'source', 'return_pc', 'x87_argument',
                      'compiler', 'transfer_version', 'transfer_kind', 'transfer_site', 'caller',
                      'disposition', 'x87_state', 'x87_operation', 'callback_cpu', 'callback_activation',
                      'unused-argument'):
            common.native_error = common.error_stack = None
            request = Call(function=target, receiver=receiver, count=count)
            if count: request.arguments[0] = argument
            if field == 'unused-argument': request.arguments[count] = 1
            elif field == 'count': request.count ^= 1
            else: setattr(request, field, 1)
            common.service(None, C.pointer(request))
            if not common.native_error or not common.native_error.startswith('Malformed '):
                raise AssertionError(('accepted malformed ordinary request', hex(target), field))
            rejected.append(f'ordinary-{target:x}-{field}')
    return rejected


def cursor_witnesses(specs):
    common = object.__new__(LevelOneNativeJoin)
    common.entries = {int(e['address'],16):e for s in specs for e in s['owned']}
    common.x87_frames, common.native_functions = [], []
    common.native_error = None
    common.x87_environments = Counter()
    common.child_stack = lambda:proof.STACK_TOP
    observed = []
    def publish(address, receiver, arguments, stack):
        observed.append('ordinary_cursor' in common.x87_frames[-1])
        common.native_functions = [address]
        raw = X87(size=C.sizeof(X87), version=1)
        common.x87_outer(Call(function=address, x87_count=4, x87_state=C.addressof(raw)))
        raw.returned = 0
        common.x87_outer(Call(function=address, x87_count=5, x87_state=C.addressof(raw)))
        common.native_functions = []
        return 1
    common._invoke = publish
    rows = []
    for target, death, expected in ((0x483ae0, 0x483e10, True),
        (0x483ae1, 0x483e10, False), (0x483ae0, 0x483e11, False),
        (0x44df60, 0x483e11, True)):
        actor, holder, logic, vtable = 0x1000, 0x2000, 0x3000, 0x4000
        words = {actor+0x6c:holder, holder+0x18:logic, logic:vtable,
                 vtable+0x14:target, vtable+0x5c:death}
        common.word = words.__getitem__
        request = Call(function=0x4dc830, count=1)
        request.arguments[0] = actor
        common.environment_call(request, packet((0x23f, 0x2821, ())))
        if observed[-1] != expected:
            raise AssertionError(('wrong virtual cursor witness', hex(target), hex(death)))
        rows.append(dict(target=hex(target), death=hex(death), cursor=observed[-1]))
    return rows


def intermediate_profiles(specs, entries):
    """Run both real RedTail intermediate owners on sealed fallback inputs."""
    selected = [c for c in proof.runner.load_cases(specs[-1]).cases(random.Random(0))
                if c.label in ('react level=4 hit=3 rand=100',
                               'death special=True flag=0 kind=0')]
    if len(selected) != 2: raise AssertionError('missing RedTail sealed inputs')
    rows = []
    for case in selected:
        for status in (0x20, 0x21, 0x4500):
            for live in (1, 3):
                env = configure(specs, entries)
                env.profile, env.live = status | 0x2800, live
                env._begin_case(random.Random(17))
                tokens = case.setup(env)
                env.initial_stack(proof.resolve(case.initial_stack, tokens))
                env._freeze()
                receiver = proof.resolve(case.receiver, tokens)
                arguments = tuple(proof.resolve(a, tokens)&0xffffffff for a in case.arguments)
                native = env.run_native(entries[-1], case.function, receiver, arguments)
                native = replace(native, x87=env.machine.x87_state())
                bridged = list(env.bridged)
                original = env.run_original(case.function, receiver, arguments)
                original = replace(original, x87=env.machine.x87_state())
                expected = proof.STACK_TOP+4*(1+len(arguments))
                difference = env.compare(native, original, case.function == 0x483ae0, expected)
                boundary = 0x44df60 if case.function == 0x483ae0 else 0x44e0c0
                before = (0x23f, env.profile,
                    tuple((0x923456789abcdef0+i,0x4001+i) for i in range(live)))
                if (difference or not native.completed or native.x87 != original.x87
                        or boundary not in bridged or native.x87[0] != before[0]
                        or (native.x87[1]^before[1])&0x3800 or native.x87[2] != before[2]):
                    raise AssertionError((case.label, difference, native.errors,
                        before, native.x87, original.x87, bridged))
                rows.append(dict(label=case.label, root=hex(case.function), boundary=hex(boundary),
                    incoming=before, native=native.x87, original=original.x87))
    return rows


def main():
    specs = [json.loads((ROOT/'Tests/families'/f'{name}.json').read_text()) for name in FAMILIES]
    library = C.CDLL(str(proof.build.library('active-level-x87-join',
        [ROOT/p for s in specs for p in s['sources']], 'O2')))
    entries = []
    for spec in specs:
        entry = getattr(library, spec['oracle']['entry'])
        entry.argtypes = [proof.U32, proof.U32, C.POINTER(proof.U32), proof.U32,
                          C.POINTER(proof.NativeHost), C.POINTER(proof.U32)]
        entry.restype = proof.U32
        entries.append(entry)
    rows, negatives = [], []
    for case, target, route in inputs(specs):
        for status in (0x20, 0x21, 0x4500):
            for live in (0, 1, 3):
                env = configure(specs, entries)
                common = (attach_source_frame(env, specs, entries) if route == 'soldier'
                          else attach(env, specs, entries))
                common.word = env.get
                common.x87_balanced = Counter()
                common.source_ordinary_calls = Counter()
                env.profile, env.live = status | 0x2800, live
                env._begin_case(random.Random(17))
                tokens = case.setup(env)
                env.initial_stack(proof.resolve(case.initial_stack, tokens))
                env._freeze()
                arguments = tuple(proof.resolve(a, tokens)&0xffffffff for a in case.arguments)
                receiver = proof.resolve(case.receiver, tokens)
                expected_stack = proof.STACK_TOP+4*(1+(0 if route == 'loot' else len(arguments)))
                def joined(function, receiver, words, count, host, out):
                    common.x87_ambient = packet(env.machine.x87_state())
                    common.native_functions, common.x87_frames = [], []
                    env.receipts = []
                    common.source_ordinary_calls = Counter()
                    frame = None
                    if route == 'loot':
                        inherited = packet(env.machine.x87_state())
                        frame = dict(function=LOOT_PATH[0], caller=inherited, entered=False,
                            result=None, push=0, ordinary_cursor=X87.from_buffer_copy(inherited))
                        common.x87_frames = [frame]
                        common.native_functions = [LOOT_PATH[0]]
                        borrowed = X87(size=C.sizeof(X87), version=1)
                        common.x87_outer(Call(function=LOOT_PATH[0], x87_count=4,
                                             x87_state=C.addressof(borrowed)))
                        common.native_functions = list(LOOT_PATH[:-1])
                        # Ambient cannot replace the live method frame.
                        common.x87_ambient = packet((0x23f, 0x4500, ()))
                    value = common.invoke(function, receiver, list(words[:count]), proof.STACK_TOP)
                    if frame is not None:
                        raw = X87.from_buffer_copy(inherited)
                        common.native_functions = [LOOT_PATH[0]]
                        common.x87_outer(Call(function=LOOT_PATH[0], x87_count=5,
                                             x87_state=C.addressof(raw)))
                        if state_tuple(frame['result']) != state_tuple(common.x87_ambient):
                            raise AssertionError('enclosing method dropped child status')
                        common.native_functions, common.x87_frames = [], []
                    C.cast(out, C.POINTER(proof.U32))[0] = value
                    return 1
                native = env.run_native(joined, case.function, receiver, arguments)
                native = replace(native, x87=state_tuple(common.x87_ambient))
                receipts = list(env.receipts)
                original = env.run_original(case.function, receiver, arguments)
                original = replace(original, x87=env.machine.x87_state())
                difference = env.compare(native, original, False, expected_stack)
                if difference or not native.completed or native.x87 != original.x87:
                    raise AssertionError((case.label, env.profile, live, difference, native.errors,
                                          native.x87, original.x87, receipts))
                if not any(r[0] == target for r in receipts):
                    raise AssertionError(('missing target', hex(target), receipts))
                if route == 'soldier' and common.source_ordinary_calls[0x43d490] != 1:
                    raise AssertionError('Soldier profile did not execute source dispatch')
                rows.append(dict(label=case.label, route=route, target=hex(target),
                    source_dispatch_calls=common.source_ordinary_calls[0x43d490],
                    incoming=(0x23f, env.profile, live), native=native.x87,
                    original=original.x87, receipts=receipts))
                for corruption in ('cw', 'slot', 'top', 'push', 'missing-entry', 'duplicate', 0x20, 0x100):
                    env.negative = corruption
                    try:
                        wrong = env.run_native(joined, case.function, receiver, arguments)
                        wrong = replace(wrong, x87=state_tuple(common.x87_ambient))
                        if env.compare(wrong, original, False, expected_stack) is None and wrong.x87 == original.x87:
                            raise AssertionError(('surviving corruption', corruption))
                    except Blocked:
                        pass
                    negatives.append(dict(label=case.label, status=env.profile, live=live, corruption=str(corruption)))
    intermediate = intermediate_profiles(specs, entries)
    rejected = refusals(specs)
    witnesses = cursor_witnesses(specs)
    evidence = ROOT/'work/native-active-x87-check.json'
    evidence.write_text(json.dumps(dict(status='pass', original_sha256=proof.claw().sha256,
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__).resolve(), ROOT/'Tests/NativeLevelOne/native_join.py',
                      ROOT/'Tests/NativeLevels/base_x87_check.py',
                      ROOT/'Tests/NativeMenuBase/native_join.py',
                      ROOT/'scripts/check-level-eight-base-x87.py',
                      *[ROOT/'Tests/families'/f'{s["id"]}.json' for s in specs],
                      *[ROOT/s['oracle']['cases'] for s in specs],
                      *[ROOT/p for s in specs for p in s['sources']]]},
        rows=rows, negative_controls=negatives, refusals=rejected,
        cursor_witnesses=witnesses, intermediate_profiles=intermediate), indent=2)+'\n')
    print(json.dumps(dict(status='pass', comparisons=len(rows), intermediate_comparisons=len(intermediate), negative_controls=len(negatives),
        refusals=len(rejected), cursor_witnesses=len(witnesses), evidence=str(evidence))))


if __name__ == '__main__': main()
