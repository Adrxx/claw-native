"""Opt-in Claw profile contracts. Addresses and layouts are never auto-translated."""
from . import program as programs


def owned_ranges(spec, program=None):
    """v1.3 has no v1.0 corpus fallback; every body needs its actual byte extent."""
    program = program or programs.profile(spec["program"])
    result = {}
    for entry in spec.get("owned", []):
        if "body_ranges" in entry or "interval_end" not in entry:
            raise ValueError("claw-v1.3 requires explicit interval_end for each owned body; "
                             "v1.0 corpus/body_ranges cannot supply v1.3 ownership")
        start, end = int(entry["address"], 16), int(entry["interval_end"], 16)
        if not program.text[0] <= start < end <= program.text[1]:
            raise ValueError("claw-v1.3 owned interval must lie in its executable text")
        if start in result or any(max(start, lo) < min(end, hi)
                                  for ranges in result.values() for lo, hi in ranges):
            raise ValueError("claw-v1.3 owned bodies overlap")
        result[start] = [(start, end)]
    return result


def validate(spec):
    """Refuse accidental v1.0 ownership/import declarations in a v1.3 family."""
    if spec.get("abi") != "canonical":
        raise ValueError("claw-v1.3 requires canonical ABI")
    program = programs.profile(spec["program"])
    owned_ranges(spec, program)
    imports = {
        "is-bad-read-ptr": ("kernel32.dll!isbadreadptr", 2),
        "set-rect": ("user32.dll!setrect", 5),
        "set-rect-empty": ("user32.dll!setrectempty", 1),
    }
    for address, declaration in spec.get("callees", {}).items():
        address = int(address, 16)
        if not program.in_text(address) and address not in program.imports:
            raise ValueError(f"{address:#x}: callee is outside the selected program text/imports")
        if declaration.get("kind") != "fixture":
            continue
        identity = program.imports.get(address, "").lower()
        expected = imports.get(declaration.get("fixture"))
        if expected:
            service, argc = expected
            if identity != service:
                raise ValueError(f"{address:#x}: fixture must bind {service} in {program.name}")
            if declaration.get("convention") != "stdcall" or declaration.get("argc") != argc:
                raise ValueError(f"{address:#x}: {service} requires stdcall with {argc} arguments")
        name = declaration.get("name", "").lower()
        if address in program.imports and "!" in name and name != identity:
            raise ValueError(f"{address:#x}: fixture name disagrees with {program.name} import identity")
    return program


def lint(spec):
    """Check explicit v1.3 bodies against v1.3 bytes, never the old corpus."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_MEM

    errors, warnings = [], []
    try:
        program = validate(spec)
    except (ValueError, OSError, KeyError, TypeError) as error:
        return [str(error)], []
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    callees = {int(a, 16): c for a, c in spec.get("callees", {}).items()}
    for entry in spec["owned"]:
        start, end = int(entry["address"], 16), int(entry["interval_end"], 16)
        section = next(s for s in program.sections if s.address <= start < s.address + len(s.data))
        instructions = list(decoder.disasm(section.data[start-section.address:end-section.address], start))
        if sum(i.size for i in instructions) != end - start:
            errors.append(f"owned {start:#x}: interval cuts an instruction or contains undecodable bytes")
        convention, argc = entry.get("convention"), entry.get("argc")
        if convention not in ("cdecl", "stdcall", "thiscall", "fastcall", "compiler-context") or type(argc) is not int:
            errors.append(f"owned {start:#x}: convention and argc must be declared")
            continue
        expected = 4 * argc if convention in ("stdcall", "thiscall", "fastcall") else 0
        for instruction in instructions:
            if instruction.mnemonic == "ret" and convention != "compiler-context":
                popped = instruction.operands[0].imm if instruction.operands else 0
                if popped != expected:
                    errors.append(f"owned {start:#x}: return pop {popped} disagrees with signature")
            if instruction.mnemonic not in ("call", "jmp"):
                continue
            operand = instruction.operands[0]
            if operand.type == X86_OP_MEM and not operand.mem.base and not operand.mem.index:
                slot = operand.mem.disp
                if slot in program.imports and callees.get(slot, {}).get("kind") != "fixture":
                    errors.append(f"owned {start:#x}: import {slot:#x} must be a declared fixture")
    return errors, warnings
