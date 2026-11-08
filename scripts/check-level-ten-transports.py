"""Check the original Marrow base-call boundary and malformed requests."""
import ctypes as C
import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('transports', ROOT/'scripts/check-level-one-transports.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
from Tests.clawparity.program import claw
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def main():
    program = claw()
    def read(address, count):
        section = next(s for s in program.sections if s.address <= address < s.address+len(s.data))
        return section.data[address-section.address:address-section.address+count]
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    results = {}
    library = shared.build()
    malformed = {'function': 0x44e0bf, 'receiver': 0, 'receiver2': 1, 'count': 0,
                 'source': 1, 'compiler': 1, 'callback_cpu': 1, 'callback_activation': 1,
                 'x87_count': 1, 'x87_argument': 1.0, 'x87_state': 1, 'x87_operation': 1,
                 'return_pc': 1, 'transfer_version': 1, 'transfer_kind': 1, 'transfer_site': 1,
                 'caller': 1, 'disposition': 1}
    marrow = struct.unpack('<45I', read(0x50e7ac, 180))
    results['original-marrow-override'] = marrow[0x5c//4] == 0x40e660 and 0x44e0c0 not in marrow
    call = next(decoder.disasm(read(0x40e668, 5), 0x40e668))
    results['original-marrow-base-call'] = call.mnemonic == 'call' and call.op_str == '0x44e0c0'
    base = library.claw_level_boss_base_call_ok
    base.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32, shared.U32]; base.restype = shared.U32
    q = shared.Call(function=0x44e0c0, receiver=0x61001000, count=1)
    q.arguments[0] = 0x61002000
    results['marrow-base'] = base(C.byref(q), 0x40e660, 0x50e7ac, 0x40e660) == 1
    for field, value in {**malformed, 'function': 0x44e0bf, 'count': 0}.items():
        invalid = shared.Call.from_buffer_copy(q); setattr(invalid, field, value)
        results['marrow-malformed-'+field] = base(C.byref(invalid), 0x40e660, 0x50e7ac, 0x40e660) == 0
    for caller, vtable, slot in ((0x40e661, 0x50e7ac, 0x40e660),
                               (0x40e660, 0x50e7b0, 0x40e660),
                               (0x40e660, 0x50e7ac, 0x44e0c0)):
        results[f'marrow-unreviewed-{caller:x}-{vtable:x}-{slot:x}'] = base(C.byref(q), caller, vtable, slot) == 0
    results['null-request'] = base(None, 0x40e660, 0x50e7ac, 0x40e660) == 0
    for table in (0x50f1ac, 0x50e2a4, 0x50de1c, 0x50ff2c):
        results[f'previous-boss-{table:x}'] = base(C.byref(q), 0x40e660, table, 0x40e660) == 1
    failures = [name for name, passed in results.items() if not passed]
    report = dict(check='level-ten-transports', status='fail' if failures else 'pass',
                  original_sha256=program.sha256, checks=len(results), failures=failures)
    target = ROOT/'work/level-ten-play'; target.mkdir(parents=True, exist_ok=True)
    (target/'transport-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
