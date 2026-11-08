"""Check Level 8 base calls and the app's exact Gabriel x87 environment transport."""
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


def environment_checks(library, results):
    """Exercise the actual app adapter, including inherited flags and live slots.

    Family gates establish the game arithmetic. This checks ENTRY/RESULT
    transport and rejects missing publications and damaged caller state.
    """
    invoke = library.claw_level_x87_environment_invoke
    invoke.restype = shared.U32
    refuse = C.CFUNCTYPE(shared.U32, C.c_void_p, C.POINTER(shared.Call))(lambda user, call: 0)
    for flags in (0, 0x20, 0x21):
        for depth in (0, 1, 7, 8):
            for mode in ('ok', 'silent', 'control', 'top', 'count', 'slot', 'duplicate'):
                if mode == 'slot' and not depth:
                    continue
                initial = shared.X87(size=C.sizeof(shared.X87), version=1,
                                     control=0x23f, status=0x2800 | flags, count=depth)
                for i in range(depth):
                    initial.slots[i].significand = 0x8000000000000000 | i
                    initial.slots[i].exponent = 0x3fff + i
                state = shared.X87.from_buffer_copy(initial)
                def entry(function, receiver, arguments, count, host, out):
                    h = host.contents
                    local = shared.X87(size=C.sizeof(shared.X87), version=1)
                    q = shared.Call(function=function, x87_count=4, x87_state=C.addressof(local))
                    h.call(h.user, C.pointer(q))
                    local.returned = 0
                    local.status |= 0x100
                    if mode == 'control': local.control ^= 0x400
                    if mode == 'top': local.status ^= 0x800
                    if mode == 'count': local.count = (depth + 1) % 9
                    if mode == 'slot': local.slots[0].significand ^= 1
                    q.x87_count = 5
                    if mode != 'silent': h.call(h.user, C.pointer(q))
                    if mode == 'duplicate': h.call(h.user, C.pointer(q))
                    out[0] = 7
                    return 1
                callback = shared.ENTRY(entry)
                host = shared.Host(call=refuse, entry_stack_pointer=0x2007000)
                out = shared.U32()
                got = invoke(callback, shared.U32(0x443290), shared.U32(0),
                             (shared.U32 * 1)(0x61001000), shared.U32(1),
                             C.byref(host), C.byref(state), C.byref(out))
                name = f'environment-{flags:x}-{depth}-{mode}'
                results[name] = (got == 1 and host.fault == 0) == (mode == 'ok')
                if mode == 'ok':
                    expected = shared.X87.from_buffer_copy(initial)
                    expected.status |= 0x100
                    expected.returned = 1
                    expected.eax = 7
                    results[name+'-full-state'] = bytes(state) == bytes(expected) and out.value == 7


def main():
    program = claw()
    def read(address, count):
        section = next(s for s in program.sections if s.address <= address < s.address+len(s.data))
        return section.data[address-section.address:address-section.address+count]
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    results = {}
    call = next(decoder.disasm(read(0x48429e, 5), 0x48429e))
    results['original-direct-call'] = call.mnemonic == 'call' and call.op_str == '0x43efe0'
    results['original-return'] = next(decoder.disasm(read(0x4842a4, 1), 0x4842a4)).mnemonic == 'ret'
    table = struct.unpack('<45I', read(0x50f394, 180))
    results['original-override'] = table[0x58//4] == 0x484260 and 0x43efe0 not in table
    library = shared.build()
    environment_checks(library, results)
    admit = library.claw_level_pirate_base_call_ok
    admit.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32, shared.U32]
    admit.restype = shared.U32
    def request():
        return shared.Call(function=0x43efe0, receiver=0x61001000, count=0)
    def check(name, q, expected, caller=0x484260, vtable=0x50f394, slot=0x484260):
        before = bytes(q) if q is not None else None
        results[name] = admit(C.byref(q) if q is not None else None, caller, vtable, slot) == expected
        if q is not None:
            results[name+'-unchanged'] = bytes(q) == before
    check('null', None, 0)
    check('valid', request(), 1)
    q = request(); q.stack = 0x2007000; check('tracked-stack', q, 1)
    for name, values in {'caller': (0, 0x48425f, 0x484261), 'vtable': (0, 0x50f390, 0x50f398),
                         'slot': (0, 0x43efe0, 0x484261)}.items():
        for value in values:
            check(f'{name}-{value:x}', request(), 0, **{name: value})
    malformed = {'function': 0x43efe1, 'receiver': 0, 'receiver2': 1, 'count': 1,
                 'source': 1, 'compiler': 1, 'callback_cpu': 1, 'callback_activation': 1,
                 'x87_count': 1, 'x87_argument': 1.0, 'x87_state': 1, 'x87_operation': 1,
                 'return_pc': 1, 'transfer_version': 1, 'transfer_kind': 1, 'transfer_site': 1,
                 'caller': 1, 'disposition': 1}
    for field, value in malformed.items():
        q = request(); setattr(q, field, value); check('malformed-'+field, q, 0)
    gabriel = struct.unpack('<45I', read(0x50de1c, 180))
    results['original-gabriel-override'] = gabriel[0x5c//4] == 0x40e660 and 0x44e0c0 not in gabriel
    call = next(decoder.disasm(read(0x40e668, 5), 0x40e668))
    results['original-gabriel-base-call'] = call.mnemonic == 'call' and call.op_str == '0x44e0c0'
    base = library.claw_level_boss_base_call_ok
    base.argtypes = admit.argtypes; base.restype = shared.U32
    q = shared.Call(function=0x44e0c0, receiver=0x61001000, count=1)
    q.arguments[0] = 0x61002000
    results['gabriel-base'] = base(C.byref(q), 0x40e660, 0x50de1c, 0x40e660) == 1
    for field, value in {**malformed, 'function': 0x44e0bf, 'count': 0}.items():
        invalid = shared.Call.from_buffer_copy(q); setattr(invalid, field, value)
        results['gabriel-malformed-'+field] = base(C.byref(invalid), 0x40e660, 0x50de1c, 0x40e660) == 0
    for caller, vtable, slot in ((0x40e661, 0x50de1c, 0x40e660),
                               (0x40e660, 0x50de20, 0x40e660),
                               (0x40e660, 0x50de1c, 0x44e0c0)):
        results[f'gabriel-unreviewed-{caller:x}-{vtable:x}-{slot:x}'] = base(C.byref(q), caller, vtable, slot) == 0
    failures = [name for name, passed in results.items() if not passed]
    report = dict(check='level-eight-transports', status='fail' if failures else 'pass',
                  original_sha256=program.sha256, checks=len(results), failures=failures)
    target = ROOT/'work/level-eight-play'; target.mkdir(parents=True, exist_ok=True)
    (target/'transport-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
