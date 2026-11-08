"""Narrowed FLD m32/m64 correction hooks: exact coverage, long x87-free original runs, text writes.

Independent synthetic x86. The correction itself is checked by x87_load_store; this checks that
the hook ranges contain every possible load and its fall-through, that x87-free code runs without a
per-instruction Python hook (a loop of 20 million instructions must return within 5 s), and that
writes into program text fall back to the global hook. When the hash-checked reference program is
present, it also checks that 0x4c7580 (65536 calls per 0x4c6d90) runs outside every hook range.
"""
import json
import random
import struct
import time

from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_FPSW

from ..kernel import X87_LOAD_PREFIXES, X87_LOAD_REACH, Machine, x87_load_ranges
from ..program import Program, Section

BASE, ENTRY, LOOP_END, LOAD, PATCH, INPUT, OUTPUT = 0x400000, 0x401000, 0x401010, 0x405000, 0x403000, 0x406000, 0x406100
ITERATIONS = 10_000_000
SIGNALING, QUIET = 0x7ff0000000000001, 0x7ff8000000000001


class RawMachine(Machine):
    def _x87_load_instruction(self, uc, address, size, user):
        pass  # Control: unchanged Unicorn, without the correction.


def naive_starts(code):
    """Independent reference: each offset that, after accepted prefixes, is D9/DD with a /0 memory operand."""
    found = []
    for start in range(len(code)):
        offset = start
        while offset < len(code) and code[offset] in X87_LOAD_PREFIXES:
            offset += 1
        if (offset + 1 < len(code) and code[offset] in (0xd9, 0xdd) and code[offset + 1] >> 6 != 3 and
                not code[offset + 1] & 0x38):
            found.append((start, offset))
    return found


def covered(ranges, first, last):
    return any(low <= first and last <= high for low, high in ranges)


def load_code(prefix=b''):
    return prefix + bytes.fromhex('dd00') + bytes.fromhex('dd1d') + struct.pack('<I', OUTPUT) + b'\xc3'


def program(prefix=b'', target=LOAD, smc=False, iterations=ITERATIONS):
    text = bytearray(b'\xcc' * 0x5000)
    # mov ecx, ITERATIONS; dec ecx; jnz -3; jmp target
    loop = b'\xb9' + struct.pack('<I', iterations) + b'\x49\x75\xfd'
    if smc:
        code = load_code()
        loop += (b'\xc7\x05' + struct.pack('<I', PATCH) + code[0:4] +
                 b'\xc7\x05' + struct.pack('<I', PATCH + 4) + code[4:8] +
                 b'\xc6\x05' + struct.pack('<I', PATCH + 8) + code[8:9])
    jump = ENTRY + len(loop)
    loop += b'\xe9' + struct.pack('<i', target - (jump + 5))
    text[0:len(loop)] = loop
    text[LOAD - ENTRY:LOAD - ENTRY + len(load_code(prefix))] = load_code(prefix)
    return Program('x87-load-hooks', '', BASE, 0x8000,
                   [Section('.text', ENTRY, len(text), bytes(text)),
                    Section('.data', INPUT, 0x1000, bytes(0x1000))], (ENTRY, ENTRY + len(text)), {})


def execute(machine, timeout=5.0):
    machine.write(INPUT, struct.pack('<Q', SIGNALING))
    machine.write(OUTPUT, b'\xa5' * 8)
    machine.uc.reg_write(UC_X86_REG_EAX, INPUT)
    machine.set_x87_state(0x23f, 0, ())
    began = time.monotonic()
    completed = machine.call(ENTRY, timeout_seconds=timeout).completed
    return (completed, struct.unpack('<Q', machine.read(OUTPUT, 8))[0],
            machine.register(UC_X86_REG_FPSW) & 1, time.monotonic() - began)


def corrected(result):
    completed, stored, invalid, _ = result
    return completed and stored == QUIET and invalid == 1


def checks():
    results = {}
    generator = random.Random(0x4c6d90)
    alphabet = bytes((0xd9, 0xdd, 0x66, 0x67, 0x26, 0x2e, 0x36, 0x3e, 0x64, 0x65, 0x00, 0x05, 0x40, 0x45,
                      0x80, 0x84, 0xc0, 0x08, 0x90, 0xc3))
    misses = 0
    for trial in range(200):
        size = generator.randrange(1, 600)
        code = bytes(generator.choice(alphabet) if generator.random() < 0.6 else generator.randrange(256)
                     for _ in range(size))
        ranges = x87_load_ranges(0x401000, code)
        for start, opcode in naive_starts(code):
            if not covered(ranges, 0x401000 + start, 0x401000 + opcode + 1 + X87_LOAD_REACH):
                misses += 1
    results['ranges_cover_every_load_and_fall_through'] = misses == 0
    results['x87_free_text_has_no_range'] = x87_load_ranges(0x401000, b'\x90' * 4096) == []
    for prefix in (b'', b'\x3e', b'\x2e\x3e', b'\x64', b'\x66'):
        p = program(prefix)
        machine = Machine(p, 0x3000000, 0x1000)
        results[f'loop_outside_ranges_{prefix.hex()}'] = not any(
            low <= LOOP_END and ENTRY <= high for low, high in machine.x87_load_ranges)
        result = execute(machine)
        results[f'corrected_after_long_loop_{prefix.hex()}'] = corrected(result) and result[3] < 5.0
    raw = execute(RawMachine(program(), 0x3000000, 0x1000))
    results['control_without_correction_stays_signaling'] = raw[0] and raw[1] == SIGNALING and raw[2] == 0
    # A harness write of new code into unhooked text restores the global hook.
    machine = Machine(program(target=PATCH, iterations=1000), 0x3000000, 0x1000)
    unchanged = not machine._text_written
    machine.write(ENTRY, machine.read(ENTRY, 16))
    unchanged = unchanged and not machine._text_written
    machine.write(PATCH, load_code())
    results['harness_text_write_falls_back'] = (unchanged and machine._text_written and
                                                machine.x87_load_ranges == [(0, 0xFFFFFFFF)] and
                                                corrected(execute(machine)))
    # So does a write by emulated code, before the written load executes.
    machine = Machine(program(target=PATCH, smc=True, iterations=1000), 0x3000000, 0x1000)
    results['emulated_text_write_falls_back'] = corrected(execute(machine)) and machine._text_written
    results.update(reference_checks())
    return results


def reference_checks():
    try:
        from ..program import claw
        p = claw()
    except Exception:
        return {}  # Reference binary not present: synthetic checks only.
    machine = Machine(p, 0x3000000, 0x10000)
    results = {'reference_leaf_and_builder_outside_ranges': not any(
        low < end and start <= high for low, high in machine.x87_load_ranges
        for start, end in ((0x4c6d90, 0x4c6f97), (0x4c7580, 0x4c764b)))}
    palette = 0x3000100
    machine.write(palette, bytes((7 * i) & 0xff for i in range(1024)))
    began = time.monotonic()
    completed = all(machine.call(0x4c7580, 0, 0, (palette, i, 3 * i & 0xff, 5 * i & 0xff), timeout_seconds=5.0).completed
                    for i in range(2000))
    results['reference_leaf_2000_calls_within_5s'] = completed and time.monotonic() - began < 5.0
    return results


def main():
    values = checks()
    failed = sorted(name for name, passed in values.items() if not passed)
    print(json.dumps({'passed': not failed, 'checked': len(values), 'failed': failed}))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
