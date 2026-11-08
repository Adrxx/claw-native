"""Check the original RedTailPirate death base-call transport and rejection cases."""
import ctypes as C
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw


def main():
    spec = importlib.util.spec_from_file_location('shared_transport', ROOT/'scripts/check-level-one-transports.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    program = claw()
    def read(address, size):
        section = next(s for s in program.sections if s.address <= address < s.address+len(s.data))
        return section.data[address-section.address:address-section.address+size]
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86_const import X86_INS_CALL, X86_INS_RET, X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    results = []
    def check(name, value): results.append((name, bool(value)))
    def instruction(address, identity, immediate):
        item = next(decoder.disasm(read(address, 15), address, count=1))
        return item.id == identity and len(item.operands) == 1 and item.operands[0].type == X86_OP_IMM and item.operands[0].imm == immediate
    check('original-direct-death-base-call', instruction(0x483e2e, X86_INS_CALL, 0x44e0c0))
    check('original-override-ret4', instruction(0x483e33, X86_INS_RET, 4))
    check('original-base-ret4', instruction(0x44e113, X86_INS_RET, 4))
    # The original pushes its incoming stack argument without changing ECX.
    check('original-forwards-one-argument-and-receiver', read(0x483e29, 5) == bytes.fromhex('8b44240450'))
    table = struct.unpack('<45I', read(0x50f394, 180))
    check('original-death-override-slot', table[0x5c//4] == 0x483e10)
    check('original-base-absent-from-derived-table', 0x44e0c0 not in table)
    lib = shared.build()
    admit = lib.claw_level_pirate_base_call_ok
    admit.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32, shared.U32]
    admit.restype = shared.U32
    def request(): return shared.Call(function=0x44e0c0, receiver=0x61001000, count=1)
    def run(name, q, expected, caller=0x483e10, vtable=0x50f394, slot=0x483e10):
        before = bytes(q) if q is not None else None
        check(name, admit(C.byref(q) if q is not None else None, caller, vtable, slot) == expected)
        if q is not None: check(name+'-preserves-request', before == bytes(q))
    run('null', None, 0)
    for value in (0, 1, 0x61002000, 0xffffffff):
        q = request(); q.arguments[0] = value; run(f'argument-{value:x}', q, 1)
    for field, values in {
        'function': (0, 0x43efe0, 0x44e0c1), 'count': (0, 2, 33), 'receiver': (0,),
        'receiver2': (1,), 'compiler': (1,), 'source': (1,), 'callback_cpu': (1,),
        'callback_activation': (1,), 'x87_count': (1, 2, 3, 4, 5), 'x87_argument': (1.0,),
        'x87_state': (1,), 'x87_operation': (1,), 'return_pc': (0x483e33,),
        'transfer_version': (1,), 'transfer_kind': (1,), 'transfer_site': (0x483e2e,),
        'caller': (0x483e10,), 'disposition': (1,),
    }.items():
        for i, value in enumerate(values):
            q=request(); setattr(q,field,value); run(f'refuse-{field}-{i}',q,0)
    for field, values in {'caller': (0,0x483e11,0x484260), 'vtable': (0,0x50f1ac), 'slot': (0,0x44e0c0,0x484260)}.items():
        for value in values: run(f'refuse-{field}-{value:x}',request(),0,**{field:value})
    failed = [name for name, passed in results if not passed]
    print(json.dumps(dict(check='level-seven-transports',status='fail' if failed else 'pass',checks=len(results),failures=failed)))
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
