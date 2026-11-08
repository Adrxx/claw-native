"""Independent original-only composed MFC factory success reference.

Run with work/test-env/bin/python Tests/NativeMfcFactories/reference.py.
No native implementation is loaded. Only physical LocalAlloc is supplied;
all compiler helpers, allocation wrappers and constructors execute original x86.
Derived bytes go exclusively to ignored work/ output.
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

HEAP_BASE = 0x03000000
HEAP_SIZE = 0x20000
LOCAL_ALLOC = 0x546AA8
FUNCTIONS = ((0x502335, 0x5033BE, 0x118), (0x502369, 0x503450, 0x1074))
ARITHMETIC_BITS = (1, 4, 0x10, 0x40, 0x80, 0x800)
PATTERNS = (0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0xAAAAAAAA,
            0x55555555, 0x01010101, 0xFEFEFEFE, 0x12345678, 0x87654321,
            0x000000FF, 0xFFFFFF00, 0x00010000, 0xFFFF0000, 0x80808080)
LOW_BYTES = (0, 8, 0x78, 0x80, 0xB0, 0xB8, 0xF0, 0xF8)


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
    for function, return_pc, size in FUNCTIONS:
        for index in range(80):
            flags = 2 | sum(bit for i, bit in enumerate(ARITHMETIC_BITS)
                            if index & (1 << i))
            # Include the exact successful graph's minimum stack headroom.
            minimum = 44 if function == 0x502335 else 48
            frames = (STACK_BASE + minimum, STACK_BASE + 0x600,
                      STACK_TOP, STACK_BASE + STACK_SIZE - 4)
            frame = frames[index % len(frames)]
            registers = [PATTERNS[(index + i * 3) % len(PATTERNS)]
                         for i in range(6)]
            if index >= 64:
                registers = [PATTERNS[index - 64]] * 6
            old_base = (0, 1, 0xFFFFFFFF, 0x12345678, frame + 1,
                        STACK_BASE + 0x10000, 0x80000000,
                        PATTERNS[index % len(PATTERNS)])[index % 8]
            head = 0xFFFFFFFF if index % 3 == 0 else STACK_BASE + 0x10000
            words = [[frame, return_pc]]
            chain_length = 0 if head == 0xFFFFFFFF else (1 if index % 3 == 1 else 3)
            for link in range(chain_length):
                address = head + link * 0x20
                next_head = address + 0x20 if link + 1 < chain_length else 0xFFFFFFFF
                words.extend([[address, next_head], [address + 4, 0x508BF8],
                              [address + 8, 0xFFFFFFFF]])
            state = dict(zip(CONTEXT_FIELDS,
                             [*registers, old_base, frame, function, flags, head]))
            yield {
                "label": f"factory-{function:06x}-profile-{index:02d}",
                "function": function, "return_pc": return_pc,
                "allocation_address": HEAP_BASE + 0x1000 + LOW_BYTES[index % 8],
                "allocation_size": size, "stack_seed": (index * 19 + (function & 255)) & 255,
                "stack_words": words, "input": state,
            }


def run_profile(program, profile):
    machine = Machine(program, HEAP_BASE, HEAP_SIZE)
    state = profile["input"]
    initial_stack = bytearray((i * 37 + profile["stack_seed"]) & 255
                              for i in range(STACK_SIZE))
    for address, value in profile["stack_words"]:
        struct.pack_into("<I", initial_stack, address - STACK_BASE, value)
    machine.write(STACK_BASE, initial_stack)
    machine.write(HEAP_BASE, bytes([0xA6]) * HEAP_SIZE)
    context = NativeSourceContext(72, 1, 0x7FF, 0x7FF,
                                  *(state[name] for name in CONTEXT_FIELDS), 0x472, 0, 0)
    events, entries, visited = [], [], set()
    minimum_esp = [state["esp"]]
    observed = {profile["function"], 0x4A48C0, 0x502F84, 0x501F01, 0x501FDE}

    def instruction(uc, address, size, user):
        visited.add(address)
        minimum_esp[0] = min(minimum_esp[0], machine.register(UC_X86_REG_ESP))
        if address in observed:
            snapshot = cpu(machine)
            entries.append({"function": address, "cpu": snapshot,
                            "return_pc": machine.words(snapshot["esp"], 1)[0]})

    machine.uc.hook_add(UC_HOOK_CODE, instruction,
                        begin=program.text[0], end=program.text[1] - 1)

    def external(current, address):
        if address != current.import_stub[LOCAL_ALLOC]:
            raise AssertionError(f"Unexpected physical service {address:#x}")
        snapshot = cpu(current, LOCAL_ALLOC)
        sp = snapshot["esp"]
        return_pc, flags, size = current.words(sp, 3)
        assert (return_pc, flags, size) == (0x502F91, 0x40, profile["allocation_size"])
        assert not events
        events.append({
            "function": LOCAL_ALLOC, "return_pc": return_pc,
            "arguments": [flags, size], "cpu": snapshot,
            "frame_hex": current.read(sp, state["esp"] + 4 - sp).hex(),
            "stack_sha256": sha(current.read(STACK_BASE, STACK_SIZE)),
        })
        pointer = profile["allocation_address"]
        assert pointer % 8 == 0
        current.write(pointer, bytes(size))
        # Explicit physical-service domain: EAX is the live token; ECX, EDX,
        # EFLAGS, nonvolatiles and FS are preserved. stdcall RET pops 8 bytes.
        # No game-code return or output register is fabricated by the fixture.
        current.return_from_external(pointer, 8)

    machine.on_external = external
    pointer = profile["allocation_address"]
    size = profile["allocation_size"]

    def heap_access(address, count, is_write, instruction_address):
        if not pointer <= address <= pointer + size - count:
            raise AssertionError(f"Original heap access outside allocation at {instruction_address:#x}")

    machine.watch_heap(heap_access)
    result = machine.call_source(profile["function"], context, profile["return_pc"],
                                 convention="cdecl", timeout_seconds=3)
    assert result.completed and result.eax == pointer
    assert len(events) == 1
    assert [entry["function"] for entry in entries] == [
        profile["function"], 0x4A48C0, 0x502F84,
        0x501F01 if profile["function"] == 0x502335 else 0x501FDE]
    expected_headroom = 44 if profile["function"] == 0x502335 else 48
    assert events[0]["cpu"]["esp"] == state["esp"] - expected_headroom
    assert minimum_esp[0] >= state["esp"] - expected_headroom
    allocation = machine.read(pointer, size)
    assert machine.read(HEAP_BASE, pointer - HEAP_BASE) == bytes([0xA6]) * (pointer - HEAP_BASE)
    after = pointer + size
    assert machine.read(after, HEAP_BASE + HEAP_SIZE - after) == bytes([0xA6]) * (HEAP_BASE + HEAP_SIZE - after)
    return dict(profile, expected={
        "cpu": {name: getattr(context, name) for name in CONTEXT_FIELDS},
        "stack_sha256": sha(machine.read(STACK_BASE, STACK_SIZE)),
        "allocation_hex": allocation.hex(), "allocation_sha256": sha(allocation),
        "local_alloc": events,
    }, original_call_entries=entries, original_instruction_pcs=sorted(visited),
        initial_stack_sha256=sha(initial_stack))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "work/native-mfc-factories-check/reference.json")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / "work").resolve()):
        parser.error("Original-derived output must stay under ignored work/")
    program = claw()  # Mandatory original executable SHA-256 verification.
    outputs = [run_profile(program, profile) for profile in profiles()]
    document = {
        "schema": 1, "program_sha256": program.sha256,
        "producer": "Tests/NativeMfcFactories/reference.py",
        "stack_base": STACK_BASE, "stack_size": STACK_SIZE,
        "heap_base": HEAP_BASE, "heap_size": HEAP_SIZE,
        "cpu_fields": list(CONTEXT_FIELDS), "input_mask": 0x7FF,
        "output_mask": 0x7FF, "preserve_mask": 0x472,
        "initial_stack_rule": "byte[i] = (i * 37 + stack_seed) & 255, then little-endian stack_words overlays",
        "fixture_policy": {
            "only_fixture": LOCAL_ALLOC, "convention": "stdcall", "argument_bytes": 8,
            "return": "allocation_address in EAX; zero exactly allocation_size bytes",
            "preserve": ["ebx", "ecx", "edx", "esi", "edi", "ebp", "eflags", "fsHead"],
            "eip_at_physical_observation": "Canonical IAT slot 0x546aa8; harness import stub address is normalized only for identity",
            "allocation_token": "Input profile chooses an actual live eight-byte-aligned guest heap address; native service may reserve that token",
            "domain": "This is one explicit Win32-compatible volatile-register policy, not a universal Windows implementation claim",
        },
        "failure_boundary": {"missing_native_dependency": 0x4F50FD,
                             "native_zero_allocation_policy": "Stop unimplemented at original throw entry until source EH exists; never use original RaiseException as fabricated native EH"},
        "count": len(outputs), "profiles": outputs,
    }
    data = (json.dumps(document, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(json.dumps({"status": "reference-generated", "profiles": len(outputs),
                      "sha256": sha(data), "output": str(args.output),
                      "program_sha256": program.sha256}))


if __name__ == "__main__":
    main()
