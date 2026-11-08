"""Check the original Wolvington base-call boundary and malformed requests."""
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
    from Tests.NativeLevels.level_six_boss_trace import WolvingtonTrace
    tail = list(decoder.disasm(read(0x4a1302, 0x6b), 0x4a1302))
    results['original-update-advance-tail'] = tail[-1].address == 0x4a136c and tail[-1].mnemonic == 'ret'
    targets = struct.unpack('<7I', read(0x4a1370, 28))
    results['original-update-advance-table'] = set(targets) == {0x4a1320, 0x4a132d, 0x4a133a}
    results['game-tail-elected'] = all(WolvingtonTrace.is_game(i.address) for i in tail)
    results['table-and-crt-not-elected'] = not WolvingtonTrace.is_game(0x4a1370) and not WolvingtonTrace.is_game(0x4a3050)
    library = shared.build()
    malformed = {'function': 0x44e0bf, 'receiver': 0, 'receiver2': 1, 'count': 0,
                 'source': 1, 'compiler': 1, 'callback_cpu': 1, 'callback_activation': 1,
                 'x87_count': 1, 'x87_argument': 1.0, 'x87_state': 1, 'x87_operation': 1,
                 'return_pc': 1, 'transfer_version': 1, 'transfer_kind': 1, 'transfer_site': 1,
                 'caller': 1, 'disposition': 1}
    wolvington = struct.unpack('<45I', read(0x50ff2c, 180))
    results['original-wolvington-override'] = wolvington[0x5c//4] == 0x40e660 and 0x44e0c0 not in wolvington
    call = next(decoder.disasm(read(0x40e668, 5), 0x40e668))
    results['original-wolvington-base-call'] = call.mnemonic == 'call' and call.op_str == '0x44e0c0'
    base = library.claw_level_boss_base_call_ok
    base.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32, shared.U32]; base.restype = shared.U32
    q = shared.Call(function=0x44e0c0, receiver=0x61001000, count=1)
    q.arguments[0] = 0x61002000
    results['wolvington-base'] = base(C.byref(q), 0x40e660, 0x50ff2c, 0x40e660) == 1
    for field, value in {**malformed, 'function': 0x44e0bf, 'count': 0}.items():
        invalid = shared.Call.from_buffer_copy(q); setattr(invalid, field, value)
        results['wolvington-malformed-'+field] = base(C.byref(invalid), 0x40e660, 0x50ff2c, 0x40e660) == 0
    for caller, vtable, slot in ((0x40e661, 0x50ff2c, 0x40e660),
                               (0x40e660, 0x50ff30, 0x40e660),
                               (0x40e660, 0x50ff2c, 0x44e0c0)):
        results[f'wolvington-unreviewed-{caller:x}-{vtable:x}-{slot:x}'] = base(C.byref(q), caller, vtable, slot) == 0
    failures = [name for name, passed in results.items() if not passed]
    report = dict(check='level-six-transports', status='fail' if failures else 'pass',
                  original_sha256=program.sha256, checks=len(results), failures=failures)
    target = ROOT/'work/level-six-play'; target.mkdir(parents=True, exist_ok=True)
    (target/'transport-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
