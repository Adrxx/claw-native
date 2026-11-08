"""Independent original/native check of the elected player edge-call adapter.

Use --library with an existing native Level 4 join library; this check never
builds a library. This boundary check does not admit a family or prove a route.
"""
import argparse
from collections import Counter, deque
import ctypes as C
import hashlib
import json
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86_const import X86_INS_CALL, X86_OP_IMM
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)

from Tests.clawparity.program import claw
from Tests.NativeMenuBase.native_join import Call, NativeMemory, U32
from Tests.NativeMenuBase.trace import Blocked, ROOT, STACK
from Tests.NativeLevels.native_join import LevelNativeJoin, adapt_edge_call

CALLER, TARGET, SITE, CONTINUATION = 0x415df0, 0x4bb030, 0x416ab8, 0x416abd


def request(actor=0x12345678):
    call = Call(function=TARGET, count=1)
    call.arguments[0] = actor
    return call


def original_results(program):
    code = next(s for s in program.sections if s.name == '.text')
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    call = next(decoder.disasm(code.data[SITE-code.address:], SITE, 1))
    assert call.id == X86_INS_CALL and call.address+call.size == CONTINUATION
    assert call.operands[0].type == X86_OP_IMM and call.operands[0].imm == TARGET
    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    machine.mem_map(program.base, program.size)
    for section in program.sections:
        machine.mem_write(section.address, section.data)
    machine.mem_map(STACK-0x1000, 0x2000)
    visits = []
    machine.hook_add(UC_HOOK_CODE, lambda uc, address, size, data: visits.append(address))
    results = []
    registers = (UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                 UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
    for actor, ecx, eax, flags in ((0, 0, 1, 2), (1, 0xffffffff, 0x87654321, 0x246),
                                  (0x12345678, 0x10203040, 0xffffffff, 0x203),
                                  (0xffffffff, 1, 0, 0x202)):
        visits.clear()
        machine.mem_write(STACK-0x1000, b'\xa5'*0x2000)
        before = (0x11223344, ecx, 0xaabbccdd, 0x87654321, 0x12345678, actor)
        for register, value in zip(registers, before):
            machine.reg_write(register, value)
        machine.reg_write(UC_X86_REG_ESP, STACK)
        machine.reg_write(UC_X86_REG_EAX, eax)
        machine.reg_write(UC_X86_REG_EFLAGS, flags)
        machine.emu_start(SITE-1, CONTINUATION+3, count=8)
        assert visits == [SITE-1, SITE, TARGET, TARGET+2, CONTINUATION]
        assert machine.reg_read(UC_X86_REG_EIP) == CONTINUATION+3
        assert machine.reg_read(UC_X86_REG_ESP) == STACK
        assert tuple(machine.reg_read(r) for r in registers) == before
        assert int.from_bytes(machine.mem_read(STACK-4, 4), 'little') == actor
        assert int.from_bytes(machine.mem_read(STACK-8, 4), 'little') == CONTINUATION
        assert bytes(machine.mem_read(STACK, 64)) == b'\xa5'*64
        results.append((actor, machine.reg_read(UC_X86_REG_EAX)))
    return results


def native_probe(library, entry, program):
    """Use the real service/invoke methods with only the required host memory."""
    probe = object.__new__(LevelNativeJoin)
    probe.library, probe.entries, probe.program = library, {TARGET: dict(entry)}, program
    probe.machine = NativeMemory()
    probe.machine.mem_map(STACK-0x2000, 0x4000)
    probe.native_functions, probe.native_frames = [CALLER], [STACK]
    probe.native_calls, probe.native_counts = deque(), Counter()
    probe.native_error = probe.error_stack = probe.deny_owner = None
    probe.edge_call_adaptations = 0
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True, type=Path)
    args = parser.parse_args()
    program = claw()
    expected = original_results(program)
    spec = json.loads((ROOT/'Tests/families/booty_progression.json').read_text())
    assert spec['evidence']['level'] == 'admitted'
    entry = next(e for e in spec['owned'] if int(e['address'], 16) == TARGET)
    assert (entry['convention'], entry['argc'], entry['returns']) == ('thiscall', 0, 'u32')
    library = C.CDLL(str(args.library.resolve()))
    probe = native_probe(library, entry, program)
    try:
        for actor, result in expected:
            call = request(actor)
            before = bytes(call)
            adapted = adapt_edge_call(call, CALLER)
            assert bytes(call) == before and C.addressof(call) != C.addressof(adapted)
            assert adapted.function == TARGET and adapted.receiver == 0 and adapted.count == 0
            memory_before = bytes(probe.machine.mem_read(STACK-0x2000, 0x4000))
            count = probe.native_counts[TARGET]
            assert probe.service(None, C.pointer(call)) == result
            assert probe.native_error is None and library.menu_fault_code(probe.host) == 0
            assert probe.native_counts[TARGET] == count+1
            assert probe.native_calls[-1]['arguments'] == []
            assert probe.native_functions == [CALLER] and probe.native_frames == [STACK]
            assert bytes(probe.machine.mem_read(STACK-0x2000, 0x4000)) == memory_before
            assert bytes(call) == before
        assert probe.edge_call_adaptations == len(expected)
    finally:
        library.menu_free(probe.host)

    malformed = [(field, 1) for field in (
        'receiver', 'receiver2', 'stack', 'source', 'return_pc', 'x87_count',
        'x87_argument', 'compiler', 'transfer_version', 'transfer_kind', 'transfer_site',
        'caller', 'disposition', 'x87_state', 'x87_operation', 'callback_cpu', 'callback_activation')]
    malformed += [('function', TARGET+1), ('count', 0), ('count', 2), ('count', 33)]
    for field, value in malformed:
        call = request()
        setattr(call, field, value)
        before = bytes(call)
        try:
            adapt_edge_call(call, CALLER)
        except Blocked:
            assert bytes(call) == before
        else:
            raise AssertionError(f'Malformed {field} accepted')
    for caller in (0, CALLER+1, 0x419a10):
        try:
            adapt_edge_call(request(), caller)
        except Blocked:
            pass
        else:
            raise AssertionError('Unelected caller accepted')

    controls = [('denied-owner', None, None), ('missing-owner', None, None),
                ('convention', 'cdecl', None), ('argc', 1, None), ('returns', 'void', None)]
    controls += [('request', field, value) for field, value in malformed if field not in ('function', 'count')]
    for kind, field, value in controls:
        probe = native_probe(library, entry, program)
        call = request()
        try:
            if kind == 'denied-owner':
                probe.deny_owner = TARGET
            elif kind == 'missing-owner':
                probe.entries.clear()
            elif kind == 'request':
                setattr(call, field, value)
            else:
                probe.entries[TARGET][kind] = field
            probe.service(None, C.pointer(call))
            assert probe.native_error and library.menu_fault_code(probe.host)
            assert probe.edge_call_adaptations == 0 and probe.native_counts[TARGET] == 0
        finally:
            library.menu_free(probe.host)
    print(json.dumps(dict(status='pass', original_sha256=program.sha256,
        library_sha256=hashlib.sha256(args.library.read_bytes()).hexdigest(),
        call_site=hex(SITE), continuation=hex(CONTINUATION), target=hex(TARGET),
        original_native_profiles=len(expected), malformed_controls=len(malformed)+3,
        actual_service_controls=len(controls))))


if __name__ == '__main__':
    main()
