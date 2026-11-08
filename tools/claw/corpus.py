"""Function corpus of the original executable: merge, disassemble, check, look up.

The corpus lives under work/corpus (ignored by git) and is produced by
tools/ghidra/DumpProgram.java:
  work/corpus/c/<entry>.c        decompiled C per function
  work/corpus/meta/<entry>.json  per-function record written by the dump
  work/corpus/phaseA.json        interior seeds and pointer-seeded functions
  work/corpus/seeds.txt          addresses earlier workers decompiled
  work/corpus/index.json         merged index
  work/corpus/asm/<entry>.asm    capstone listing per function

Subcommands: merge, asm, check, show <address>. Each prints one JSON line last.
"""
import argparse
import hashlib
import json
import struct
import sys

from tools.claw.paths import CORPUS, ORIGINAL_EXE, ORIGINAL_SHA256, relative

IMAGE_BASE = 0x400000
TEXT_START = 0x401000
TEXT_SIZE = 0x109DB5
MIN_FUNCTIONS = 2500

INDEX_FILE = CORPUS / "index.json"
C_DIR = CORPUS / "c"
ASM_DIR = CORPUS / "asm"
META_DIR = CORPUS / "meta"
SEEDS_FILE = CORPUS / "seeds.txt"
PHASE_A_FILE = CORPUS / "phaseA.json"


def read_index():
    return json.loads(INDEX_FILE.read_text())


def write_index(index):
    INDEX_FILE.write_text(json.dumps(index, indent=1))


def read_seeds():
    lines = SEEDS_FILE.read_text().split()
    return sorted({int(line, 16) for line in lines})


def find_function(index, address):
    """The function record whose body contains address, or None."""
    for function in index["functions"]:
        for start, end in function["ranges"]:
            if start <= address < end:
                return function
    return None


# ------------------------------------------------------------------ merge


def command_merge(arguments):
    functions = [json.loads(path.read_text()) for path in META_DIR.glob("*.json")]
    functions.sort(key=lambda function: function["entry"])
    previous = {}
    if INDEX_FILE.exists():
        previous = {f["entry"]: f for f in read_index()["functions"]}
    for function in functions:
        old = previous.get(function["entry"])
        if old and "instruction_count" in old:
            function["instruction_count"] = old["instruction_count"]
    phase_a = json.loads(PHASE_A_FILE.read_text())
    index = {
        "sha256": ORIGINAL_SHA256,
        "functions": functions,
        "interior_seeds": phase_a["interior_seeds"],
        "pointer_seeded": phase_a["pointer_seeded"],
    }
    write_index(index)
    return {"functions": len(functions), "index": relative(INDEX_FILE)}


# -------------------------------------------------------------------- asm


class PeImage:
    """Just enough PE parsing to map virtual addresses to file bytes."""

    def __init__(self, data):
        self.data = data
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
        optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
        table = pe_offset + 24 + optional_size
        self.sections = []
        for number in range(section_count):
            fields = struct.unpack_from("<8sIIII", data, table + 40 * number)
            self.sections.append(fields)

    def read(self, address, length):
        relative_address = address - IMAGE_BASE
        for _name, virtual_size, virtual_address, raw_size, raw_pointer in self.sections:
            if virtual_address <= relative_address < virtual_address + max(virtual_size, raw_size):
                start = raw_pointer + relative_address - virtual_address
                return self.data[start:start + length]
        raise ValueError("address %08x is not in any section" % address)


def load_image():
    data = ORIGINAL_EXE.read_bytes()
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256:
        raise SystemExit("CLAW.EXE does not match the fingerprinted original v1.0")
    return PeImage(data)


def disassemble_function(disassembler, image, function):
    """Listing lines and instruction count for one function."""
    lines = []
    count = 0
    for start, end in function["ranges"]:
        code = image.read(start, end - start)
        offset = 0
        while offset < len(code):
            address = start + offset
            decoded = list(disassembler.disasm(code[offset:], address, 1))
            if not decoded:
                lines.append("%08x: %02x  db 0x%02x" % (address, code[offset], code[offset]))
                offset += 1
                continue
            instruction = decoded[0]
            raw = bytes(instruction.bytes).hex()
            text = (instruction.mnemonic + " " + instruction.op_str).rstrip()
            lines.append("%08x: %s  %s" % (instruction.address, raw, text))
            count += 1
            offset += instruction.size
    return lines, count


def command_asm(arguments):
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs

    image = load_image()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_32)
    ASM_DIR.mkdir(parents=True, exist_ok=True)
    index = read_index()
    total = 0
    for function in index["functions"]:
        lines, count = disassemble_function(disassembler, image, function)
        function["instruction_count"] = count
        (ASM_DIR / (function["entry"] + ".asm")).write_text("\n".join(lines) + "\n")
        total += count
    write_index(index)
    return {"asm_files": len(index["functions"]), "instructions": total}


# ------------------------------------------------------------------ check


def covered_text_bytes(functions):
    spans = sorted(tuple(r) for function in functions for r in function["ranges"])
    text_end = TEXT_START + TEXT_SIZE
    covered = 0
    cursor = TEXT_START
    for start, end in spans:
        start = max(start, cursor)
        end = min(end, text_end)
        if end > start:
            covered += end - start
            cursor = end
    return covered


def command_check(arguments):
    index = read_index()
    functions = index["functions"]
    entries = {int(function["entry"], 16) for function in functions}
    interior_declared = {int(value, 16) for value in index["interior_seeds"]}
    resolved = 0
    interior = 0
    missing = []
    seeds = read_seeds()
    for seed in seeds:
        if seed in entries:
            resolved += 1
        elif seed in interior_declared or find_function(index, seed):
            interior += 1
        else:
            missing.append("%08x" % seed)
    in_functions = covered_text_bytes(functions)
    c_files = len(list(C_DIR.glob("*.c")))
    asm_files = len(list(ASM_DIR.glob("*.asm")))
    passed = not missing and c_files == asm_files == len(functions) and len(functions) >= MIN_FUNCTIONS
    return {
        "functions": len(functions),
        "text_bytes_in_functions": in_functions,
        "text_bytes_total": TEXT_SIZE,
        "coverage_fraction": round(in_functions / TEXT_SIZE, 6),
        "decompile_failed": sum(1 for f in functions if not f["decompile_ok"]),
        "with_unaff": sum(1 for f in functions if f["unaff_count"] > 0),
        "with_jumptable_warning": sum(1 for f in functions if f["jumptable_warning"]),
        "seeds": len(seeds),
        "seeds_resolved": resolved,
        "seeds_interior": interior,
        "seeds_missing": missing,
        "c_files": c_files,
        "asm_files": asm_files,
        "status": "pass" if passed else "fail",
    }


# ------------------------------------------------------------------- show


def command_show(arguments):
    address = int(arguments.address, 16)
    index = read_index()
    function = find_function(index, address)
    if function is None:
        return {"address": "%08x" % address, "error": "no function contains this address"}
    entry = function["entry"]
    return {
        "address": "%08x" % address,
        "c": relative(C_DIR / (entry + ".c")),
        "asm": relative(ASM_DIR / (entry + ".asm")),
        "function": function,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("merge")
    commands.add_parser("asm")
    commands.add_parser("check")
    show = commands.add_parser("show")
    show.add_argument("address")
    arguments = parser.parse_args(argv)
    handlers = {"merge": command_merge, "asm": command_asm, "check": command_check, "show": command_show}
    result = handlers[arguments.command](arguments)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
