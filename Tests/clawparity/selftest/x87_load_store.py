"""Bounded FLD m32/m64 SNaN correction controls; no family cases or game copies.

Intel SDM vol. 1 4.8.3.5 and vol. 2 FLD/FST define the bit expectations.
An independent Bochs instruction probe is retained in work/x87-signaling-nan/.
"""
import json
import struct

from unicorn import UC_PROT_READ
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP

from ..kernel import EmulationFault, Machine
from ..program import Program, Section, claw

# Explicit binary64 answers, independent of the correction's extended encoding.
VECTORS = (
    (0x7ff0000000000001, 0x7ff8000000000001),
    (0xfff0000000000001, 0xfff8000000000001),
    (0x7ff123456789abcd, 0x7ff923456789abcd),
    (0xfff23456789abcde, 0xfffa3456789abcde),
    *((v, v) for v in (0, 0x8000000000000000, 0x3ff0000000000000,
        0xbff0000000000000, 0x3ff0000000000001, 0x7fefffffffffffff,
        0xffefffffffffffff, 1, 0x8000000000000001, 0x000fffffffffffff,
        0x0010000000000000, 0x7ff0000000000000, 0xfff0000000000000,
        0x7ff8123456789abc, 0xfff8fedcba987654)),
)
ENTRY, INPUT, OUTPUT = 0x401000, 0x402000, 0x403000
LOWER = tuple((0x8123456789abcdef + i, 0x3fff + i) for i in range(8))

# Explicit binary32 inputs and quiet binary64 store results. A nonzero word
# after each input ensures the load still consumes four bytes, not eight.
VECTORS32 = (
    (0x7f800001, 0x7ff8000020000000),
    (0xff800001, 0xfff8000020000000),
    (0x7f812345, 0x7ff82468a0000000),
    (0xffa34567, 0xfffc68ace0000000),
    (0, 0), (0x80000000, 0x8000000000000000),
    (0x3f800000, 0x3ff0000000000000), (0xbf800000, 0xbff0000000000000),
    (0x3f800001, 0x3ff0000020000000), (0x7f7fffff, 0x47efffffe0000000),
    (1, 0x36a0000000000000), (0x80000001, 0xb6a0000000000000),
    (0x007fffff, 0x380fffffc0000000), (0x00800000, 0x3810000000000000),
    (0x7f800000, 0x7ff0000000000000), (0xff800000, 0xfff0000000000000),
    (0x7fc12345, 0x7ff82468a0000000), (0xffc12345, 0xfff82468a0000000),
)


class RawMachine(Machine):
    def _x87_load_instruction(self, uc, address, size, user):
        pass  # Control: unchanged Unicorn, without the correction.


def synthetic(load=bytes.fromhex('dd00')):
    # EAX-indirect input, three independent absolute-address stores.
    code = load + bytes.fromhex('dd1500304000 dd1508304000 dd1d10304000 c3')
    return Program('x87-load-store', '', 0x400000, 0x4000,
        [Section('.text', ENTRY, len(code), code),
         Section('.data', INPUT, 0x2000, bytes(0x2000))], (ENTRY, ENTRY + len(code)), {})


def prepare(machine, bits, top=0, depth=0, cw=0x23f):
    machine.write(INPUT, struct.pack('<Q', bits))
    machine.write(OUTPUT, b'\xa5' * 24)
    machine.uc.reg_write(UC_X86_REG_EAX, INPUT)
    machine.set_x87_state(cw, top << 11, LOWER[:depth])


def run(machine, bits, top=0, depth=0, cw=0x23f):
    prepare(machine, bits, top, depth, cw)
    assert machine.call(ENTRY).completed
    return machine.read(OUTPUT, 24), machine.x87_state(), machine.read(INPUT, 8)


def checks64():
    results = {}
    p = synthetic()
    m, raw = Machine(p, 0x3000000, 0x1000), RawMachine(p, 0x3000000, 0x1000)
    for bits, expected in VECTORS:
        for top in range(8):
            for depth in range(8):
                actual, state, source = run(m, bits, top, depth)
                baseline, oldstate, _ = run(raw, bits, top, depth)
                snan = bits != expected
                results[f'value_{bits:016x}_{top}_{depth}'] = (
                    actual == struct.pack('<3Q', expected, expected, expected) and
                    state == (oldstate[0], oldstate[1] | int(snan), oldstate[2]) and
                    state[2] == LOWER[:depth] and source == struct.pack('<Q', bits) and
                    (snan or actual == baseline))
    # Every precision/rounding setting remains usable; this is not arithmetic.
    for cw in (0x7f, 0x23f, 0x37f, 0x63f, 0xa3f, 0xe3f):
        for bits, expected in VECTORS[:4]:
            actual, state, _ = run(m, bits, 5, 7, cw)
            results[f'control_{cw}_{bits}'] = actual == struct.pack('<3Q', *([expected] * 3)) and state[0] == cw
    # Equivalent encodings, including SIB, address/segment/operand overrides.
    for load in ('dd00', 'dd442000', '66dd00', '3edd00', '64dd00', '67dd060020'):
        alternative = Machine(synthetic(bytes.fromhex(load)), 0x3000000, 0x1000)
        if load.startswith('67'):
            # Address-size override uses DS:0x2000; map it separately.
            alternative.uc.mem_map(0x2000, 0x1000)
            alternative.write(0x2000, struct.pack('<Q', VECTORS[2][0]))
        actual, state, _ = run(alternative, VECTORS[2][0])
        results[f'encoding_{load}'] = actual == struct.pack('<3Q', *([VECTORS[2][1]] * 3)) and state[1] & 1 == 1
    # Observers must see quiet extended ST(0), IE, correct TOP and lower slots.
    observed = []
    m.observe(ENTRY + 2, lambda machine, pc: observed.append(machine.x87_state()))
    run(m, 0x7ff0000000000001, 0, 1)
    results['entry_observer'] = observed[-1] == (0x23f, 0x3801, ((0xc000000000000800, 0x7fff), LOWER[0]))
    # A stop immediately after FLD still publishes its architectural state.
    m = Machine(p, 0x3000000, 0x1000)
    prepare(m, 0xfff0000000000001)
    results['stop_after_load'] = (m._execute(ENTRY, ENTRY + 2, 1).completed and
        m.x87_state() == (0x23f, 0x3801, ((0xc000000000000800, 0xffff),)))
    # A code hook stopping before FLD must not invent a load or sticky flag.
    m.observe(ENTRY, lambda machine, pc: machine.uc.emu_stop())
    prepare(m, 0x7ff0000000000001)
    m._execute(ENTRY, ENTRY + 2, 1)
    results['stop_before_load'] = m.x87_state() == (0x23f, 0, ()) and m._x87_loaded is None
    # Unsupported unmasked behavior and stack overflow stay exactly at baseline.
    for depth, cw in ((8, 0x23f), (0, 0x23e)):
        a, b = Machine(p, 0x3000000, 0x1000), RawMachine(p, 0x3000000, 0x1000)
        records = []
        for machine in (a, b):
            prepare(machine, VECTORS[0][0], 3, depth, cw)
            try:
                machine._execute(ENTRY, ENTRY + 2, 1)
                error = None
            except EmulationFault as exc:
                error = str(exc)
            records.append((error, machine.x87_state(), machine.read(OUTPUT, 24)))
        results[f'delegated_{depth}_{cw}'] = records[0] == records[1]
    # Failed reads and stores preserve the original fault, stack and memory prefix.
    for fault in ('unmapped', 'cross_page', 'read_protected', 'store_protected'):
        records = []
        for cls in (Machine, RawMachine):
            machine = cls(p, 0x3000000, 0x1000)
            prepare(machine, VECTORS[0][0])
            if fault == 'unmapped':
                machine.uc.reg_write(UC_X86_REG_EAX, 0x600000)
            elif fault == 'cross_page':
                machine.uc.reg_write(UC_X86_REG_EAX, 0x403ffc)
                machine.write(0x403ffc, b'\x01\x00\x00\x00')
            elif fault == 'read_protected':
                machine.uc.mem_protect(INPUT, 0x1000, 0)
            else:
                machine.uc.mem_protect(OUTPUT, 0x1000, UC_PROT_READ)
            try:
                machine.call(ENTRY)
                raise AssertionError('expected memory fault')
            except EmulationFault as exc:
                records.append((str(exc), machine.register(UC_X86_REG_EIP),
                                machine.x87_state(), machine.read(OUTPUT, 24)))
        if fault == 'store_protected':
            results[f'fault_{fault}'] = (records[0][0:2] == records[1][0:2] and records[0][3] == records[1][3]
                and records[0][2] == (0x23f, 0x3801, ((0xc000000000000800, 0x7fff),)))
        else:
            results[f'fault_{fault}'] = records[0] == records[1]
    # FLD m80 and register FLD are bit transports, not this conversion.
    for load in ('db28', 'd9c0'):
        records = []
        for cls in (Machine, RawMachine):
            machine = cls(synthetic(bytes.fromhex(load)), 0x3000000, 0x1000)
            prepare(machine, VECTORS[0][0], depth=1)
            machine.write(INPUT, struct.pack('<QH', 0x8000000000000800, 0x7fff))
            machine._execute(ENTRY, ENTRY + 2, 1)
            records.append(machine.x87_state())
        results[f'nonconversion_{load}'] = records[0] == records[1]
    # Hash-checked actual entry. No instructions copied into the test fixture.
    original = Machine(claw(), 0x3000000, 0x1000)
    for bits, expected in VECTORS:
        original.reset_x87()
        result = original.call(0x4082d0, ecx=0x3000000, arguments=(bits & 0xffffffff, bits >> 32))
        results[f'original_{bits:016x}'] = (result.completed and
            original.read(0x30000c0, 24) == struct.pack('<3Q', *([expected] * 3)) and
            original.x87_state()[2] == ())
    return results


def checks32():
    results = {}
    p = synthetic(bytes.fromhex('d900'))
    m, raw = Machine(p, 0x3000000, 0x1000), RawMachine(p, 0x3000000, 0x1000)

    def prepare32(machine, bits, top=0, depth=0, cw=0x23f):
        prepare(machine, bits | (0xa5a5a5a5 << 32), top, depth, cw)

    for index, (bits, expected) in enumerate(VECTORS32):
        for top in range(8):
            for depth in range(8):
                records = []
                for machine in (m, raw):
                    prepare32(machine, bits, top, depth)
                    assert machine.call(ENTRY).completed
                    records.append((machine.read(OUTPUT, 24), machine.x87_state(), machine.read(INPUT, 8)))
                (actual, state, source), (baseline, oldstate, _) = records
                snan = index < 4
                results[f'm32_value_{bits:08x}_{top}_{depth}'] = (
                    actual == struct.pack('<3Q', expected, expected, expected) and
                    state == (oldstate[0], oldstate[1] | int(snan), oldstate[2]) and
                    state[2] == LOWER[:depth] and source == struct.pack('<II', bits, 0xa5a5a5a5) and
                    (snan or actual == baseline))
    for cw in (0x7f, 0x23f, 0x37f, 0x63f, 0xa3f, 0xe3f):
        prepare32(m, VECTORS32[2][0], 5, 7, cw)
        assert m.call(ENTRY).completed
        results[f'm32_control_{cw}'] = (m.read(OUTPUT, 24) == struct.pack('<3Q', *([VECTORS32[2][1]] * 3))
            and m.x87_state() == (cw, (5 << 11) | 1, LOWER[:7]))
    for load in ('d900', 'd9442000', '66d900', '3ed900', '64d900', '67d9060020'):
        machine = Machine(synthetic(bytes.fromhex(load)), 0x3000000, 0x1000)
        if load.startswith('67'):
            machine.uc.mem_map(0x2000, 0x1000)
            machine.write(0x2000, struct.pack('<I', VECTORS32[2][0]))
        prepare32(machine, VECTORS32[2][0])
        assert machine.call(ENTRY).completed
        results[f'm32_encoding_{load}'] = (machine.read(OUTPUT, 24) == struct.pack('<3Q', *([VECTORS32[2][1]] * 3))
            and machine.x87_state()[1] & 1 == 1)
    observed = []
    m.observe(ENTRY + 2, lambda machine, pc: observed.append(machine.x87_state()))
    prepare32(m, 0x7f800001, depth=1)
    assert m.call(ENTRY).completed
    results['m32_entry_observer'] = observed[-1] == (0x23f, 0x3801, ((0xc000010000000000, 0x7fff), LOWER[0]))
    m = Machine(p, 0x3000000, 0x1000)
    prepare32(m, 0xff800001)
    results['m32_stop_after_load'] = (m._execute(ENTRY, ENTRY + 2, 1).completed and
        m.x87_state() == (0x23f, 0x3801, ((0xc000010000000000, 0xffff),)))
    m.observe(ENTRY, lambda machine, pc: machine.uc.emu_stop())
    prepare32(m, 0x7f800001)
    m._execute(ENTRY, ENTRY + 2, 1)
    results['m32_stop_before_load'] = m.x87_state() == (0x23f, 0, ()) and m._x87_loaded is None
    for depth, cw in ((8, 0x23f), (0, 0x23e)):
        records = []
        for cls in (Machine, RawMachine):
            machine = cls(p, 0x3000000, 0x1000)
            prepare32(machine, VECTORS32[0][0], 3, depth, cw)
            try:
                machine._execute(ENTRY, ENTRY + 2, 1)
                error = None
            except EmulationFault as exc:
                error = str(exc)
            records.append((error, machine.x87_state(), machine.read(OUTPUT, 24)))
        results[f'm32_delegated_{depth}_{cw}'] = records[0] == records[1]
    for fault in ('unmapped', 'cross_page', 'read_protected', 'store_protected', 'page_end_valid'):
        records = []
        for cls in (Machine, RawMachine):
            machine = cls(p, 0x3000000, 0x1000)
            prepare32(machine, VECTORS32[0][0])
            if fault == 'unmapped':
                machine.uc.reg_write(UC_X86_REG_EAX, 0x600000)
            elif fault in ('cross_page', 'page_end_valid'):
                at = 0x403ffe if fault == 'cross_page' else 0x403ffc
                machine.uc.reg_write(UC_X86_REG_EAX, at)
                machine.write(at, struct.pack('<I', VECTORS32[0][0])[:0x404000-at])
            elif fault == 'read_protected':
                machine.uc.mem_protect(INPUT, 0x1000, 0)
            else:
                machine.uc.mem_protect(OUTPUT, 0x1000, UC_PROT_READ)
            try:
                machine.call(ENTRY)
                error = None
            except EmulationFault as exc:
                error = str(exc)
            records.append((error, machine.register(UC_X86_REG_EIP), machine.x87_state(), machine.read(OUTPUT, 24)))
        if fault == 'store_protected':
            results[f'm32_fault_{fault}'] = (records[0][0] is not None and records[0][0:2] == records[1][0:2]
                and records[0][3] == records[1][3]
                and records[0][2] == (0x23f, 0x3801, ((0xc000010000000000, 0x7fff),)))
        elif fault == 'page_end_valid':
            results['m32_page_end_valid'] = (records[0][0] is None and records[0][2] == (0x23f, 1, ())
                and records[0][3] == struct.pack('<3Q', *([VECTORS32[0][1]] * 3)))
        else:
            results[f'm32_fault_{fault}'] = records[0] == records[1] and records[0][0] is not None
    return results


def checks():
    return checks64() | checks32()


if __name__ == '__main__':
    found = checks()
    failed = [name for name, passed in found.items() if not passed]
    print(json.dumps({'passed': not failed, 'checked': len(found), 'failed': failed}))
    raise SystemExit(bool(failed))
