"""Original/native profiles of the player's three-word idle call transport.

Use --library with an existing native level join library. This check builds
nothing and establishes a boundary comparison, not family or app acceptance.
Random and audio dependencies are bounded, shared stand-ins; the idle game
owner itself executes independently as original instructions and native C++.
"""
import argparse
from collections import Counter, deque
import ctypes as C
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86_const import X86_INS_CALL, X86_INS_RET, X86_OP_IMM
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)

from Tests.clawparity.program import claw
from Tests.NativeMenuBase.native_join import Call, NativeMemory, U32
from Tests.NativeMenuBase.trace import Blocked, ROOT, STACK
from Tests.NativeLevels.native_join import EndOfLevelNativeJoin, LevelNativeJoin, adapt_idle_call

CALLER, TARGET, SITE, CONTINUATION = 0x415df0, 0x420480, 0x41979f, 0x4197a4
RANDOM, AUDIO, EFFECT = 0x4a3050, 0x48c8a0, 0x20000000
CONTEXT_FIELDS = (
    'receiver', 'receiver2', 'stack', 'source', 'return_pc', 'x87_count',
    'x87_argument', 'compiler', 'transfer_version', 'transfer_kind',
    'transfer_site', 'caller', 'disposition', 'x87_state', 'x87_operation',
    'callback_cpu', 'callback_activation')


def request(arguments=(0x12345678, 0x87654321, 0xffffffff)):
    call = Call(function=TARGET, count=3)
    for i, argument in enumerate(arguments):
        call.arguments[i] = argument
    return call


def profiles():
    # Two quotients for every switch arm, then signed/default boundaries.
    for i, random in enumerate((*range(24), 0x7fffffff, 0xffffffff,
                                0xfffffff4, 0x80000000)):
        yield dict(random=random, audio=(0, 1, 0xffffffff, 0x89abcdef)[i % 4],
                   arguments=((0, 1, 0xffffffff, 0x12345678)[i % 4],
                              0x80000000 + i, 0xfedcba98 - i))


def dependency(machine, events, address, arguments, profile):
    """Shared deterministic provider, with an observable ordered memory effect."""
    events.append((address, tuple(arguments)))
    value = profile['random'] if address == RANDOM else profile['audio']
    offset = 0 if address == RANDOM else 16
    words = [address, len(events), value, sum(arguments) & 0xffffffff]
    machine.mem_write(EFFECT + offset, b''.join(w.to_bytes(4, 'little') for w in words))
    return value


def original_results(program):
    code = next(s for s in program.sections if s.name == '.text')
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    caller_body = decoder.disasm(code.data[CALLER-code.address:0x419a10-code.address], CALLER)
    idle_sites = [i.address for i in caller_body if i.id == X86_INS_CALL
                  and i.operands[0].type == X86_OP_IMM and i.operands[0].imm == TARGET]
    assert idle_sites == [SITE]
    instructions = list(decoder.disasm(code.data[SITE-3-code.address:CONTINUATION+3-code.address], SITE-3))
    assert [(i.mnemonic, i.op_str) for i in instructions[:3]] == [
        ('push', 'edi'), ('push', 'ebx'), ('push', 'esi')]
    call = instructions[3]
    assert call.id == X86_INS_CALL and call.address == SITE and call.address + call.size == CONTINUATION
    assert call.operands[0].type == X86_OP_IMM and call.operands[0].imm == TARGET
    assert (instructions[4].mnemonic, instructions[4].op_str) == ('add', 'esp, 0xc')
    body = list(decoder.disasm(code.data[TARGET-code.address:0x42055d-code.address], TARGET))
    returns = {i.address for i in body if i.id == X86_INS_RET}
    assert len(returns) == 12 and all(not i.op_str for i in body if i.id == X86_INS_RET)
    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    machine.mem_map(program.base, program.size)
    for section in program.sections:
        machine.mem_write(section.address, section.data)
    machine.mem_map(STACK-0x2000, 0x4000)
    machine.mem_map(EFFECT, 0x1000)
    events, visited_returns = [], set()
    active = {}

    def hook(uc, address, size, unused):
        sp = uc.reg_read(UC_X86_REG_ESP)
        word = lambda a: int.from_bytes(uc.mem_read(a, 4), 'little')
        if address == TARGET:
            assert [word(sp + 4*i) for i in range(4)] == [CONTINUATION, *active['arguments']]
        elif address == CONTINUATION:
            assert sp == STACK - 12
        if address in returns:
            visited_returns.add(address)
        if address in (RANDOM, AUDIO):
            arguments = [] if address == RANDOM else [word(sp+4), word(sp+8)]
            value = dependency(uc, events, address, arguments, active)
            uc.reg_write(UC_X86_REG_EAX, value)
            uc.reg_write(UC_X86_REG_ESP, sp+4)
            uc.reg_write(UC_X86_REG_EIP, word(sp))

    machine.hook_add(UC_HOOK_CODE, hook)
    results = []
    preserved = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
    for profile in profiles():
        active = profile
        events.clear()
        machine.mem_write(STACK-0x2000, b'\xa5'*0x4000)
        machine.mem_write(EFFECT, b'\x5a'*32)
        actor, state, payload = profile['arguments']
        before = (state, actor, payload, 0x11223344)
        for register, value in zip(preserved, before):
            machine.reg_write(register, value)
        for register, value in ((UC_X86_REG_ECX, 0x76543210), (UC_X86_REG_EDX, 0xabcdef01),
                                (UC_X86_REG_EAX, 0x87654321), (UC_X86_REG_EFLAGS, 0x246),
                                (UC_X86_REG_ESP, STACK)):
            machine.reg_write(register, value)
        machine.emu_start(SITE-3, CONTINUATION+3, count=100)
        assert machine.reg_read(UC_X86_REG_EIP) == CONTINUATION+3
        assert machine.reg_read(UC_X86_REG_ESP) == STACK
        assert tuple(machine.reg_read(r) for r in preserved) == before
        assert bytes(machine.mem_read(STACK, 64)) == b'\xa5'*64
        results.append((profile, machine.reg_read(UC_X86_REG_EAX), list(events),
                        bytes(machine.mem_read(EFFECT, 32))))
    assert visited_returns == returns
    return results


class BoundaryProbe(LevelNativeJoin):
    def service(self, unused, pointer):
        call = pointer.contents
        if self.native_functions[-1:] == [TARGET] and call.function in (RANDOM, AUDIO):
            if call.function == self.missing_dependency:
                self.native_error = f'Boundary dependency deliberately withheld: {call.function:#x}'
                self.library.menu_fault(self.host, call.function)
                return 0
            return dependency(self.machine, self.events, call.function,
                              list(call.arguments[:call.count]), self.profile)
        return super().service(unused, pointer)


def native_probe(library, entry, program, profile):
    probe = object.__new__(BoundaryProbe)
    probe.library, probe.entries, probe.program = library, {TARGET: dict(entry)}, program
    probe.machine = NativeMemory()
    probe.machine.mem_map(STACK-0x2000, 0x4000)
    probe.machine.mem_map(EFFECT, 0x1000)
    probe.machine.mem_write(STACK-0x2000, b'\xa5'*0x4000)
    probe.machine.mem_write(EFFECT, b'\x5a'*32)
    probe.native_functions, probe.native_frames = [CALLER], [STACK]
    probe.native_calls, probe.native_counts = deque(), Counter()
    probe.native_error = probe.error_stack = probe.deny_owner = probe.missing_dependency = None
    probe.edge_call_adaptations = probe.idle_call_adaptations = 0
    probe.events, probe.profile = [], profile
    probe._bytes = C.CFUNCTYPE(C.c_void_p, C.c_void_p, U32, U32)(probe.resolve)
    probe._call = C.CFUNCTYPE(U32, C.c_void_p, C.POINTER(Call))(probe.service)
    library.menu_host.argtypes = [C.c_void_p, type(probe._bytes), type(probe._call)]
    library.menu_host.restype = C.c_void_p
    library.menu_run.argtypes = [C.c_void_p, U32, U32, C.POINTER(U32), U32, U32,
                                C.c_void_p, U32, C.POINTER(U32)]
    library.menu_fault.argtypes = [C.c_void_p, U32]
    library.menu_fault_address.argtypes = library.menu_fault_code.argtypes = [C.c_void_p]
    library.menu_free.argtypes = [C.c_void_p]
    probe.host = library.menu_host(None, probe._bytes, probe._call)
    return probe


def idle_dependency_gate():
    """Withholding is limited to the selected level's active idle dependency."""
    rows = [
        ({}, RANDOM, True),
        ({'deny_idle_random': False}, RANDOM, False),
        ({}, AUDIO, False),
        ({'native_functions': [CALLER]}, RANDOM, False),
        ({'native_functions': []}, RANDOM, False),
        ({'native_functions': [TARGET, CALLER]}, RANDOM, False),
        ({'phase': 'loading'}, RANDOM, False),
        ({'phase': 'level-8-stand'}, RANDOM, False),
        ({'phase': 'level-90-stand'}, RANDOM, False),
        ({'target_level': 10}, RANDOM, False),
    ]
    sentinel = object()
    for updates, address, refuse in rows:
        probe = object.__new__(LevelNativeJoin)
        probe.deny_idle_random = True
        probe.native_functions = [CALLER, TARGET]
        probe.target_level, probe.phase = 9, 'level-9-stand'
        for field, value in updates.items():
            setattr(probe, field, value)
        with patch.object(EndOfLevelNativeJoin, 'fixture', return_value=sentinel) as fallback:
            if refuse:
                try:
                    LevelNativeJoin.fixture(probe, address)
                except Blocked as error:
                    assert str(error) == 'Idle random service deliberately withheld: 0x4a3050'
                else:
                    raise AssertionError('Selected idle dependency was not withheld')
                fallback.assert_not_called()
            else:
                assert LevelNativeJoin.fixture(probe, address) is sentinel
                fallback.assert_called_once_with(probe, address)
    # Existing minimal probes and default hosts need no opt-in attribute.
    del probe.deny_idle_random
    probe.target_level = 9
    with patch.object(EndOfLevelNativeJoin, 'fixture', return_value=sentinel) as fallback:
        assert LevelNativeJoin.fixture(probe, RANDOM) is sentinel
        fallback.assert_called_once_with(probe, RANDOM)
    return len(rows) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True, type=Path)
    args = parser.parse_args()
    dependency_gate_controls = idle_dependency_gate()
    program = claw()
    expected = original_results(program)
    spec = json.loads((ROOT/'Tests/families/level_one_claw_states_02.json').read_text())
    assert spec['evidence']['level'] == 'admitted'
    entry = next(e for e in spec['owned'] if int(e['address'], 16) == TARGET)
    assert (entry['convention'], entry['argc'], entry['returns']) == ('cdecl', 0, 'u32')
    library = C.CDLL(str(args.library.resolve()))
    for profile, result, events, effect in expected:
        probe = native_probe(library, entry, program, profile)
        try:
            call = request(profile['arguments'])
            before = bytes(call)
            adapted = adapt_idle_call(call, CALLER)
            assert bytes(call) == before and C.addressof(call) != C.addressof(adapted)
            assert adapted.function == TARGET and adapted.receiver == 0 and adapted.count == 0
            assert probe.service(None, C.pointer(call)) == result
            assert probe.native_error is None and library.menu_fault_code(probe.host) == 0
            assert probe.native_counts[TARGET] == 1 and probe.idle_call_adaptations == 1
            assert probe.native_calls[0]['arguments'] == []
            assert probe.events == events
            assert bytes(probe.machine.mem_read(EFFECT, 32)) == effect
            assert probe.native_functions == [CALLER] and probe.native_frames == [STACK]
            assert bytes(probe.machine.mem_read(STACK, 64)) == b'\xa5'*64
            assert bytes(call) == before
        finally:
            library.menu_free(probe.host)

    malformed = [(field, 1) for field in CONTEXT_FIELDS]
    malformed += [('function', TARGET+1), ('count', 0), ('count', 1), ('count', 2), ('count', 4), ('count', 33)]
    for field, value in malformed:
        call = request()
        setattr(call, field, value)
        before = bytes(call)
        try:
            adapt_idle_call(call, CALLER)
        except Blocked:
            assert bytes(call) == before
        else:
            raise AssertionError(f'Malformed {field} accepted')
    wrong_callers = (0, CALLER+1, 0x419a10)
    for caller in wrong_callers:
        try:
            adapt_idle_call(request(), caller)
        except Blocked:
            pass
        else:
            raise AssertionError('Unelected caller accepted')

    controls = [('denied-owner', None, None), ('missing-owner', None, None),
                ('convention', 'thiscall', None), ('argc', 3, None), ('returns', 'void', None),
                ('source_context', {}, None), ('compiler_context', {}, None), ('x87_result', {}, None)]
    controls += [('request', field, value) for field, value in malformed if (field, value) != ('count', 0)]
    controls += [('wrong-caller', caller, None) for caller in wrong_callers]
    controls += [('missing-dependency', address, None) for address in (RANDOM, AUDIO)]
    for kind, field, value in controls:
        probe = native_probe(library, entry, program, next(profiles()))
        call = request()
        try:
            if kind == 'denied-owner':
                probe.deny_owner = TARGET
            elif kind == 'missing-owner':
                probe.entries.clear()
            elif kind == 'request':
                setattr(call, field, value)
            elif kind == 'wrong-caller':
                probe.native_functions[:] = [field]
            elif kind == 'missing-dependency':
                probe.missing_dependency = field
            else:
                probe.entries[TARGET][kind] = field
            before = bytes(call)
            probe.service(None, C.pointer(call))
            assert probe.native_error and library.menu_fault_code(probe.host), (kind, field)
            assert probe.idle_call_adaptations == 0, (kind, field)
            assert bytes(call) == before
            if kind != 'missing-dependency':
                assert not probe.events, (kind, field)
            else:
                assert 'deliberately withheld' in probe.native_error
                assert [e[0] for e in probe.events] == ([] if field == RANDOM else [RANDOM])
            assert bytes(probe.machine.mem_read(STACK, 64)) == b'\xa5'*64
        finally:
            library.menu_free(probe.host)
    print(json.dumps(dict(status='pass', original_sha256=program.sha256,
        library_sha256=hashlib.sha256(args.library.read_bytes()).hexdigest(),
        call_site=hex(SITE), continuation=hex(CONTINUATION), target=hex(TARGET),
        original_native_profiles=len(expected), original_plain_returns=12,
        malformed_controls=len(malformed)+len(wrong_callers), actual_service_controls=len(controls),
        dependency_gate_controls=dependency_gate_controls)))


if __name__ == '__main__':
    main()
