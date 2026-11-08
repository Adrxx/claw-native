"""Independent original-only composed MFC thread-record constructor reference.

Run with work/test-env/bin/python Tests/NativeMfcThreadRecords/reference.py.
Only physical GetCursorPos is supplied; complete original constructor, helper
and nested record routines execute unchanged. Derived output stays in work/.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tests"))

from clawparity.env import NativeSourceContext
from clawparity.kernel import (CONTEXT_FIELDS, CONTEXT_REGISTERS, Machine,
                               STACK_BASE, STACK_SIZE, STACK_TOP)
from clawparity.program import claw
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP

HEAP_BASE, HEAP_SIZE = 0x03000000, 0x20000
FUNCTION, RETURN_PC, GET_CURSOR_POS = 0x503510, 0x502597, 0x546CD0
RECORD_SIZE, CANARY_SIZE = 0x68, 32
ARITHMETIC_BITS = (1, 4, 0x10, 0x40, 0x80, 0x800)
PATTERNS = (0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0xAAAAAAAA,
            0x55555555, 0x01010101, 0xFEFEFEFE, 0x12345678, 0x87654321,
            0x000000FF, 0xFFFFFF00, 0x00010000, 0xFFFF0000, 0x80808080)
RECORD_OFFSETS = (0x1000, 0x1101, 0x1202, 0x1303, 0x1407, 0x15FF, 0x160F, 0x171F)
POINTS = ((0, 0), (-1, 1), (-31, 57), (2147483647, -2147483648),
          (-2147483648, 2147483647), (-65537, -32768), (123456789, -987654321),
          (0x55555555, -1431655766))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cpu(machine, logical_eip=None):
    state = {name: machine.register(register)
             for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS)}
    state["fsHead"] = machine.fs_head
    if logical_eip is not None:
        state["eip"] = logical_eip
    return state


def profiles():
    for index in range(128):
        flags = 2 | sum(bit for i, bit in enumerate(ARITHMETIC_BITS)
                        if index & (1 << i))
        frame = (STACK_BASE + 44, STACK_BASE + 0x600, STACK_TOP,
                 STACK_BASE + STACK_SIZE - 4)[index % 4]
        registers = [PATTERNS[(index + i * 3) % len(PATTERNS)] for i in range(6)]
        receiver = HEAP_BASE + RECORD_OFFSETS[index % len(RECORD_OFFSETS)]
        registers[2] = receiver
        old_base = (0, 1, 0xFFFFFFFF, 0x12345678, frame + 1,
                    STACK_BASE + 0x10000, 0x80000000,
                    PATTERNS[index % len(PATTERNS)])[index % 8]
        head = 0xFFFFFFFF if index % 3 == 0 else STACK_BASE + 0x10000
        words = [[frame, RETURN_PC]]
        chain_length = 0 if head == 0xFFFFFFFF else (1 if index % 3 == 1 else 3)
        for link in range(chain_length):
            address = head + link * 0x20
            next_head = address + 0x20 if link + 1 < chain_length else 0xFFFFFFFF
            words.extend([[address, next_head], [address + 4, 0x5086F4],
                          [address + 8, 0xFFFFFFFF]])
        seed = (index * 29 + 0x53) & 255
        initial_record = bytes((i * 53 + seed) & 255 for i in range(RECORD_SIZE))
        allocation_address = (receiver - CANARY_SIZE) & ~7
        record_offset = receiver - allocation_address
        allocation_size = record_offset + RECORD_SIZE + CANARY_SIZE
        initial_allocation = (bytes([0xA6]) * record_offset + initial_record
                              + bytes([0xA6]) * CANARY_SIZE)
        yield {
            "label": f"thread-record-profile-{index:03d}",
            "function": FUNCTION, "return_pc": RETURN_PC,
            "record_address": receiver, "record_size": RECORD_SIZE,
            "allocation_address": allocation_address, "allocation_size": allocation_size,
            "record_offset": record_offset, "initial_allocation_hex": initial_allocation.hex(),
            "record_seed": seed, "initial_record_hex": initial_record.hex(),
            "cursor_success": index >= 64, "cursor_point": list(POINTS[index % 8]),
            "stack_seed": (index * 19 + 0x10) & 255, "stack_words": words,
            "input": dict(zip(CONTEXT_FIELDS,
                              [*registers, old_base, frame, FUNCTION, flags, head])),
        }


def run_profile(program, profile):
    machine = Machine(program, HEAP_BASE, HEAP_SIZE)
    state, pointer = profile["input"], profile["record_address"]
    initial_stack = bytearray((i * 37 + profile["stack_seed"]) & 255
                              for i in range(STACK_SIZE))
    for address, value in profile["stack_words"]:
        struct.pack_into("<I", initial_stack, address - STACK_BASE, value)
    initial_heap = bytearray([0xA6]) * HEAP_SIZE
    offset = pointer - HEAP_BASE
    initial_heap[offset:offset + RECORD_SIZE] = bytes.fromhex(profile["initial_record_hex"])
    machine.write(STACK_BASE, initial_stack)
    machine.write(HEAP_BASE, initial_heap)
    context = NativeSourceContext(72, 1, 0x7FF, 0x7FF,
                                  *(state[name] for name in CONTEXT_FIELDS), 0x472, 0, 0)
    events, entries, visited = [], [], set()
    minimum_esp = [state["esp"]]
    observed = {FUNCTION, 0x4A48C0, 0x4F6A9A, 0x50354D}

    def observation(current, snapshot):
        sp = snapshot["esp"]
        record = current.read(pointer, RECORD_SIZE)
        return {
            "cpu": snapshot, "return_pc": current.words(sp, 1)[0],
            "frame_hex": current.read(sp, state["esp"] + 4 - sp).hex(),
            "stack_sha256": sha(current.read(STACK_BASE, STACK_SIZE)),
            "record_hex": record.hex(), "record_sha256": sha(record),
            "allocation_hex": current.read(profile["allocation_address"],
                                             profile["allocation_size"]).hex(),
            "record_with_canaries_hex": current.read(pointer - CANARY_SIZE,
                                                     RECORD_SIZE + 2 * CANARY_SIZE).hex(),
            "heap_sha256": sha(current.read(HEAP_BASE, HEAP_SIZE)),
        }

    def instruction(uc, address, size, user):
        visited.add(address)
        minimum_esp[0] = min(minimum_esp[0], machine.register(UC_X86_REG_ESP))
        if address in observed:
            entries.append(dict(function=address, **observation(machine, cpu(machine))))

    machine.uc.hook_add(UC_HOOK_CODE, instruction,
                        begin=program.text[0], end=program.text[1] - 1)

    def external(current, address):
        if address != current.import_stub[GET_CURSOR_POS]:
            raise AssertionError(f"Unexpected physical service {address:#x}")
        snapshot = cpu(current, GET_CURSOR_POS)
        sp = snapshot["esp"]
        minimum_esp[0] = min(minimum_esp[0], sp)
        return_pc, destination = current.words(sp, 2)
        assert (return_pc, destination) == (0x50356F, pointer + 0x5C)
        assert not events
        event = dict(function=GET_CURSOR_POS, arguments=[destination],
                     **observation(current, snapshot))
        if profile["cursor_success"]:
            current.write(destination, struct.pack("<ii", *profile["cursor_point"]))
        # Explicit OS domain: TRUE writes two signed LONGs, FALSE writes nothing.
        # EAX is BOOL; ECX, EDX, flags, nonvolatiles and FS stay unchanged.
        # stdcall RET consumes one pointer argument. No source output is supplied.
        current.return_from_external(int(profile["cursor_success"]), 4)
        event["after_cpu"] = cpu(current)
        event["after_record_hex"] = current.read(pointer, RECORD_SIZE).hex()
        events.append(event)

    machine.on_external = external

    def heap_access(address, count, is_write, instruction_address):
        if not pointer <= address <= pointer + RECORD_SIZE - count:
            raise AssertionError(f"Original heap access outside record at {instruction_address:#x}")

    machine.watch_heap(heap_access)
    result = machine.call_source(FUNCTION, context, RETURN_PC, convention="thiscall",
                                 ecx=pointer, timeout_seconds=3)
    assert result.completed and result.eax == pointer
    assert len(events) == 1
    assert [entry["function"] for entry in entries] == [FUNCTION, 0x4A48C0, 0x4F6A9A, 0x50354D]
    assert [entry["return_pc"] for entry in entries] == [RETURN_PC, 0x50351A, 0x503526, 0x50353E]
    assert entries[1]["cpu"]["eax"] == 0x508CA4
    assert events[0]["cpu"]["esp"] == state["esp"] - 44
    assert minimum_esp[0] == state["esp"] - 44
    final_heap = machine.read(HEAP_BASE, HEAP_SIZE)
    assert final_heap[:offset] == initial_heap[:offset]
    assert final_heap[offset + RECORD_SIZE:] == initial_heap[offset + RECORD_SIZE:]
    record = machine.read(pointer, RECORD_SIZE)
    return dict(profile, expected={
        "cpu": {name: getattr(context, name) for name in CONTEXT_FIELDS},
        "stack_sha256": sha(machine.read(STACK_BASE, STACK_SIZE)),
        "record_hex": record.hex(), "record_sha256": sha(record),
        "allocation_hex": machine.read(profile["allocation_address"],
                                         profile["allocation_size"]).hex(),
        "record_with_canaries_hex": machine.read(pointer - CANARY_SIZE,
                                                  RECORD_SIZE + 2 * CANARY_SIZE).hex(),
        "heap_sha256": sha(final_heap), "get_cursor_pos": events,
    }, original_call_entries=entries, original_instruction_pcs=sorted(visited),
        original_minimum_esp=minimum_esp[0], initial_stack_sha256=sha(initial_stack),
        initial_heap_sha256=sha(initial_heap))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "work/native-mfc-thread-records-check/reference.json")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / "work").resolve()):
        parser.error("Original-derived output must stay under ignored work/")
    program = claw()  # Verifies the pinned whole executable before any execution.
    outputs = [run_profile(program, profile) for profile in profiles()]
    document = {
        "schema": 1, "program_sha256": program.sha256,
        "producer": "Tests/NativeMfcThreadRecords/reference.py",
        "producer_sha256": sha(Path(__file__).read_bytes()),
        "stack_base": STACK_BASE, "stack_size": STACK_SIZE,
        "heap_base": HEAP_BASE, "heap_size": HEAP_SIZE,
        "record_size": RECORD_SIZE, "canary_size": CANARY_SIZE,
        "cpu_fields": list(CONTEXT_FIELDS), "input_mask": 0x7FF,
        "output_mask": 0x7FF, "preserve_mask": 0x472,
        "initial_stack_rule": "byte[i] = (i * 37 + stack_seed) & 255, then little-endian stack_words overlays",
        "initial_heap_rule": "All bytes 0xA6, then record byte[i] = (i * 53 + record_seed) & 255 at record_address",
        "fixture_policy": {
            "only_fixture": GET_CURSOR_POS, "convention": "stdcall", "argument_bytes": 4,
            "return": "EAX=1 with signed POINT writes when cursor_success; EAX=0 and no writes otherwise",
            "preserve": ["ebx", "ecx", "edx", "esi", "edi", "ebp", "eflags", "fsHead"],
            "eip_at_physical_observation": "Canonical IAT slot 0x546cd0; only harness stub identity is normalized",
            "record_token": "Bind record_address to the native runtime's actual same heap record; source constructor performs no allocation",
            "domain": "One explicit physical cursor and volatile-register policy; not universal Windows behavior",
        },
        "observations": "All hashes cover complete indicated byte ranges; frame_hex includes physical return through root return inclusive; events are pre-service unless named after",
        "count": len(outputs), "profiles": outputs,
    }
    data = (json.dumps(document, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(json.dumps({"status": "reference-generated", "profiles": len(outputs),
                      "sha256": sha(data), "producer_sha256": document["producer_sha256"],
                      "output": str(args.output), "program_sha256": program.sha256}))


if __name__ == "__main__":
    main()
