"""Compare the original rope CALL/continuation with its native discard transport.

Run: work/test-env/bin/python -m Tests.NativeLevels.rope_x87_check
No family cases, translations, game-result fixtures or app execution are used.
"""
from __future__ import annotations
import ctypes as C
import hashlib
import json
import struct
from types import SimpleNamespace
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn import x86_const as x86
from Tests.clawparity.program import claw
from Tests.NativeLevelOne.native_join import (
    Call, LevelOneNativeJoin, STACK, X87, validate_rope_x87_call)
from Tests.NativeLevels.native_join import build
from Tests.NativeMenuBase.trace import Blocked, ROOT

CALLER, CALLEE, SITE, CONTINUATION = 0x4181c0, 0x420dd0, 0x4183c6, 0x4183cb
RECEIVER, ACTOR, PRIVATE = 0x534db8, 0x61000000, 0x61001000
PRESERVED = ('ebx', 'ebp', 'esi', 'edi', 'ecx', 'edx')


def register(name):
    return getattr(x86, 'UC_X86_REG_' + name.upper())


def cpu(machine):
    return {name: machine.reg_read(register(name)) for name in PRESERVED}


def floating(machine):
    status = machine.reg_read(x86.UC_X86_REG_FPSW)
    top = (status >> 11) & 7
    tags = machine.reg_read(x86.UC_X86_REG_FPTAG)
    slots = [machine.reg_read(x86.UC_X86_REG_FP0 + ((top + i) & 7))
             for i in range(8) if (tags >> (2 * ((top + i) & 7))) & 3 != 3]
    return dict(control=machine.reg_read(x86.UC_X86_REG_FPCW), status=status, slots=slots)


class ObservedJoin(LevelOneNativeJoin):
    def owned_x87_result(self, request, state):
        self.boundary_input = X87.from_buffer_copy(state)
        value = super().owned_x87_result(request, state)
        self.boundary_output = X87.from_buffer_copy(state)
        return value


def observation(state):
    return dict(control=state.control, status=state.status,
                slots=[(s.significand, s.exponent) for s in state.slots[:state.count]])


def request(arguments):
    q = Call(function=CALLEE, receiver=RECEIVER, count=6)
    for i, value in enumerate(arguments):
        q.arguments[i] = value
    return q


def profile(program, library, entries, x, y, acceleration_x, acceleration_z, origin_z):
    original = Uc(UC_ARCH_X86, UC_MODE_32)
    original.mem_map(0x400000, 0x160000)
    for section in program.sections:
        original.mem_write(section.address, bytes(section.data))
    original.mem_map(0x1ff0000, 0x20000)
    original.mem_map(ACTOR, 0x2000)
    original.mem_write(ACTOR + 0x4c, struct.pack('<ii', x, y))
    original.mem_write(RECEIVER + 0x10, struct.pack('<ddd', acceleration_x, 0, acceleration_z))
    original.mem_write(RECEIVER + 0x50, struct.pack('<d', origin_z))
    # The rope prologue's saved nonvolatile registers and caller return word.
    saved = struct.pack('<5I', 0x11223344, 0x22334455, 0x33445566, 0x44556677, 0x70000000)
    original.mem_write(STACK - 16, saved)
    for name, value in dict(esp=STACK-16, edi=ACTOR, esi=PRIVATE, ebx=0, ebp=0x12345678).items():
        original.reg_write(register(name), value)
    original.reg_write(x86.UC_X86_REG_FPCW, 0x23f)
    original.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)

    # Execute unchanged argument preparation and the actual CALL instruction.
    original.emu_start(0x418361, CALLEE, count=200)
    assert original.reg_read(register('eip')) == CALLEE
    entry_sp = original.reg_read(register('esp'))
    assert struct.unpack('<I', original.mem_read(entry_sp, 4))[0] == CONTINUATION
    assert original.reg_read(register('ecx')) == RECEIVER
    arguments = struct.unpack('<6I', original.mem_read(entry_sp+4, 24))
    before_cpu, before_fp = cpu(original), floating(original)
    assert before_fp == dict(control=0x23f, status=0, slots=[])
    receiver_before = bytes(original.mem_read(RECEIVER, 0xb0))
    original.emu_start(CALLEE, CONTINUATION, count=1000)
    assert original.reg_read(register('eip')) == CONTINUATION
    assert original.reg_read(register('esp')) == entry_sp + 4 + 6 * 4 == STACK - 16
    assert cpu(original) == before_cpu
    original_fp = floating(original)
    assert len(original_fp['slots']) == 1
    receiver_after = bytes(original.mem_read(RECEIVER, 0xb0))
    assert bytes(original.mem_read(STACK-16, len(saved))) == saved

    native = ObservedJoin(library, entries)
    try:
        native.machine.mem_write(RECEIVER, receiver_before)
        native.machine.mem_write(STACK-16, saved)
        for name, value in before_cpu.items():
            native.machine.reg_write(register(name), value)
        native.native_functions = [CALLER]
        native.native_frames = [STACK]
        frames_before = list(native.native_frames)
        q = request(arguments)
        request_before = bytes(q)
        native.service(None, C.pointer(q))
        assert native.native_error is None, native.native_error
        assert native.native_counts[CALLEE] == 1
        assert native.x87_discarded[(CALLER, CALLEE)] == 1
        assert observation(native.boundary_input) == before_fp
        assert observation(native.boundary_output) == original_fp
        assert native.machine.mem_read(RECEIVER, 0xb0) == receiver_after
        assert cpu(native.machine) == cpu(original)
        assert native.native_frames == frames_before
        assert native.native_functions == [CALLER]
        assert native.machine.mem_read(STACK-16, len(saved)) == saved
        assert bytes(q) == request_before
        assert not native.x87_frames
        assert native.child_stack() < STACK - 16 - 24
        # The caller observes neither volatile EAX/flags nor the popped argument
        # slots rewritten by the original callee. Compare the live frame instead.
        native_fp = observation(native.boundary_output)
    finally:
        native.close()

    original.emu_start(CONTINUATION, 0x4183cd, count=2)
    assert floating(original)['slots'] == []
    assert floating(original)['control'] == before_fp['control']
    assert ((floating(original)['status'] >> 11) & 7) == 0
    original.emu_start(0x4183cd, 0x70000000, count=10)
    assert original.reg_read(register('eip')) == 0x70000000
    assert original.reg_read(register('esp')) == STACK + 4
    assert [original.reg_read(register(r)) for r in ('edi', 'esi', 'ebp', 'ebx')] == list(struct.unpack('<4I', saved[:16]))
    return dict(input=[x, y, acceleration_x, acceleration_z, origin_z],
                arguments=list(arguments), x87=native_fp, preserved_cpu=before_cpu,
                callee_stack_pop=28, caller_frame_intact=True, caller_return_stack=STACK+4,
                receiver_sha256=hashlib.sha256(receiver_after).hexdigest())


def negative_controls(entry):
    refused = []
    base = request([0]*6)
    mutations = dict(receiver=RECEIVER+4, receiver2=1, count=5, stack=STACK,
        source=1, return_pc=CONTINUATION, x87_count=2, x87_argument=1.0,
        compiler=1, transfer_version=1, transfer_kind=1, transfer_site=SITE,
        caller=CALLER, disposition=1, x87_state=1, x87_operation=1,
        callback_cpu=1, callback_activation=1)
    for name, value in mutations.items():
        q = Call.from_buffer_copy(base)
        setattr(q, name, value)
        # Use the real service's rejection path; any attempt to dispatch fails
        # this control because this probe has no invoke/library implementation.
        probe = object.__new__(LevelOneNativeJoin)
        faults = []
        probe.entries = {CALLEE: entry}
        probe.native_functions = [CALLER]
        probe.native_frames = []
        probe.native_error = probe.error_stack = None
        probe.host = None
        probe.library = SimpleNamespace(menu_fault=lambda host, address: faults.append(address))
        assert probe.service(None, C.pointer(q)) == 0
        assert probe.native_error == 'Unelected rope x87 discard boundary'
        assert faults == [CALLEE]
        refused.append(name)
    for name, caller, target, metadata in (
            ('unelected-caller', 0x4181c1, CALLEE, entry),
            ('wrong-target', CALLER, CALLEE+1, entry),
            ('changed-argc', CALLER, CALLEE, dict(entry, argc=5)),
            ('changed-result', CALLER, CALLEE, dict(entry, returns='u32')),
            ('changed-x87-contract', CALLER, CALLEE, dict(entry, x87_result=dict(pop=1, push=1)))):
        q = Call.from_buffer_copy(base)
        q.function = target
        try:
            validate_rope_x87_call(q, caller, metadata)
        except Blocked:
            refused.append(name)
        else:
            raise AssertionError(f'Accepted {name}')
    # An ordinary x87 call from an unreviewed owner must still fault in service.
    probe.native_functions = [0x4181c1]
    probe.native_error = probe.error_stack = None
    faults.clear()
    assert probe.service(None, C.pointer(base)) == 0
    assert 'Ordinary call into x87-result owner' in probe.native_error
    assert faults == [CALLEE]
    refused.append('unelected-service-caller')
    return refused


def main():
    program = claw()  # Checks the v1.0 executable SHA-256 before reading it.
    section = next(s for s in program.sections if s.name == '.text')
    offset = SITE-section.address
    call = bytes(section.data[offset:offset+5])
    assert call[0] == 0xe8 and SITE+5+struct.unpack('<i', call[1:])[0] == CALLEE
    assert CONTINUATION == SITE+5
    library, entries = build(8)
    profiles = [profile(program, library, entries, *values) for values in (
        (1234, 5678, 0, 0, 0), (2805, 5531, 0, 0, 0),
        (-1234, -5678, 1, 2, 3), (0, 0, -3, 7, -4),
        (2147483647, -2147483000, 16, -8, 12),
        (-2147483648, 2147483647, -11, 4, -9))]
    report = dict(status='pass', profiles=profiles, controls=negative_controls(entries[CALLEE]),
                  caller=hex(CALLER), site=hex(SITE), callee=hex(CALLEE), continuation=hex(CONTINUATION),
                  owner='level_one_player_actions_04b', native_game_execution='admitted C++',
                  original_scope='argument preparation, actual CALL, callee, discard and epilogue',
                  cpu_scope='preserved registers, saved caller frame, thiscall cleanup and continuation',
                  unobserved='volatile EAX/flags and dead callee argument slots', app_acceptance=False)
    report['inputs_sha256'] = {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in (
        'Tests/NativeLevelOne/native_join.py', 'Tests/NativeLevels/rope_x87_check.py',
        'Tests/families/level_one_claw_rope_01.json',
        'Tests/families/level_one_player_actions_04b.json')}
    target = ROOT/'work/native-level-eight-rope-x87'
    target.mkdir(parents=True, exist_ok=True)
    (target/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status='pass', profiles=len(profiles), controls=len(report['controls']),
                         evidence=str(target/'result.json'))))


if __name__ == '__main__':
    main()
