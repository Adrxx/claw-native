"""Maintainer-only regeneration of the checked-in original data tables. Never run by a player build."""
import json
import os
import re
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw, claw_v13
from Tests.NativeMenuResources.compare import prepare, WORK


def release_version():
    """Use the authenticated v1.3 FileVersion, as the original startup does."""
    versions = []
    marker = "FileVersion\0".encode("utf-16le")
    for section in claw_v13().sections:
        at = section.data.find(marker)
        if at < 6:
            continue
        length, count, kind = struct.unpack_from("<3H", section.data, at - 6)
        start = (at + len(marker) + 3) & ~3
        if kind != 1 or start + 2 * count > at - 6 + length:
            raise ValueError("Invalid v1.3 FileVersion resource")
        versions.append(tuple(int(v) for v in section.data[start:start + 2 * count]
                              .decode("utf-16le").rstrip("\0").split(", ")))
    if len(versions) != 1 or len(versions[0]) != 4 or versions[0][:2] != (1, 3):
        raise ValueError("Expected one v1.3 FileVersion resource")
    return versions[0]


def main():
    program = claw()
    destination = ROOT / "App/OriginalTables/MENU"
    destination.mkdir(parents=True, exist_ok=True)
    # Use exactly the metadata spans and native physical font elected by the
    # existing original/native join, without running its comparison/emulator.
    os.environ["CLAW_MENU_FULL_INITIALIZER"] = "1"
    prepare(interface=True)
    literals = {}
    for address in (0x5334f0, 0x52a004, 0x52c69c, 0x528b08, 0x52372c, 0x523ce0, 0x52cdc0, 0x52cdd0):
        section = next(s for s in program.sections if s.address <= address < s.address + s.size)
        literals[f"{address:x}"] = list(section.data[address-section.address:].split(b"\0", 1)[0] + b"\0")
    (destination / "literals.json").write_text(json.dumps(literals) + "\n")
    metadata = json.loads((WORK / "interface-metadata.json").read_text())
    # Retain the v1.0 title artwork and host addresses, but give the recovered
    # menu formatter the shipped release's version globals (v1.30 on screen).
    metadata["53ec38"] = list(struct.pack("<4I", *release_version()))
    (destination / "metadata.json").write_text(json.dumps(metadata) + "\n")
    shutil.copy2(WORK / "menu-font.json", destination / "font.json")
    # Monochrome FreeType gives a few glyphs a negative left bearing.
    # The atlas contains that bearing already; interior glyph placement and
    # the first glyph's pen advance need it separately when drawing a line.
    from Tests.NativeMenuBase.trace import MenuTrace
    font = MenuTrace().font
    atlas = json.loads((destination / "font.json").read_text())
    for code, glyph in atlas['glyphs'].items():
        glyph['leftBearing'] = font.getmask2(chr(int(code)), mode='1')[1][0]
    (destination / "font.json").write_text(json.dumps(atlas) + '\n')
    accelerator_count = accelerators(program, destination)
    level_one = level_one_data(program, destination)
    transports = level_one_transports(program, destination)
    import runpy
    runpy.run_path(str(ROOT / "scripts/extract-application-tables.py"))["prepare"]()
    runpy.run_path(str(ROOT / "scripts/extract-diagnostic-tables.py"))["prepare"](ROOT / "App/OriginalTables/DiagnosticPolicy.json")
    print(json.dumps({"status": "pass", "output": str(destination),
                      "accelerators": accelerator_count, "level_one_data_spans": level_one, "level_one_transports": transports}))



def level_one_data(program, destination):
    """Original image bytes (BSS as zero): the complete .rdata, .data and
    .idata sections, plus the code-section spans the native Level 1 join
    touches, recorded by `python -m Tests.NativeLevelOne.native_join
    --record-data-spans`. The app fills the unmapped part of these spans
    before the New Game launch command."""
    recorded = ROOT / "work/native-level-one-join/data-spans.json"
    target = destination / "level-one-data.json"
    if not recorded.exists():
        raise ValueError(f"Missing required maintainer election: {recorded}")
    election = json.loads(recorded.read_text())
    if election.get("status") != "native-complete":
        raise ValueError("Level 1 data spans were recorded from an incomplete join")
    data = {}
    # The original process maps its whole image, and so does the join. The
    # join's touched spans cover only its own 30 seconds of play; any other
    # game path (an officer's strike, a key the join never pressed) reads
    # original data outside them. Ship the complete non-code sections, BSS as
    # zero; code-section spans stay the recorded ones.
    whole = (".rdata", ".data", ".idata")
    for section in program.sections:
        if section.name in whole:
            data[f"{section.address:x}"] = list(bytes(section.data).ljust(section.size, b"\0")[:section.size])
    for address, size, name in election["spans"]:
        if name in whole:
            continue
        start = int(address, 16)
        section = next(s for s in program.sections if s.name == name)
        if not (section.address <= start and start + size <= section.address + section.size):
            raise ValueError(f"Level 1 data span {address} outside {name}")
        image = bytes(section.data).ljust(section.size, b"\0")
        data[address] = list(image[start - section.address:start - section.address + size])
    # Switch tables the original keeps in its code section and canonical
    # translations read as data (jump and index tables). The join records only
    # the entries its own route used, so a path it never took (Load Game >
    # Save Point, parity-save-load-profiles) read an unshipped entry and
    # faulted. Ship each referenced table whole.
    for address, extent in code_section_tables(program):
        key = f"{address:x}"
        if len(data.get(key, ())) < len(extent):
            data[key] = list(extent)
    target.write_text(json.dumps(data) + "\n")
    return len(data)


TABLE_READ = re.compile(r"run\.get(8?)\([a-z]+(?:\*0x4)? \+ 0x(4[0-9a-f]{5})\)")


def code_section_tables(program):
    """(address, bytes) for every code-section table a translation in Sources/
    reads: a jump table is its run of code pointers into the same section, an
    index table its bytes below the entry count of the jump table just before
    it (the original's switch layout)."""
    text = next(s for s in program.sections if s.name == ".text")
    image = bytes(text.data).ljust(text.size, b"\0")
    reads = set()
    for source in sorted((ROOT / "Sources").glob("*.cpp")):
        for byte, address in TABLE_READ.findall(source.read_text(errors="replace")):
            address = int(address, 16)
            if text.address <= address < text.address + text.size:
                reads.add((address, byte == "8"))
    jumps = {}
    for address, byte in sorted(reads):
        if byte:
            continue
        offset, count = address - text.address, 0
        while count < 256 and offset + 4 * count + 4 <= len(image):
            target = struct.unpack_from("<I", image, offset + 4 * count)[0]
            if not text.address <= target < text.address + text.size:
                break
            count += 1
        if not count:
            raise ValueError(f"Code-section jump table {address:x} has no entries")
        jumps[address] = count
    tables = [(a, image[a - text.address:a - text.address + 4 * n]) for a, n in jumps.items()]
    for address, byte in sorted(reads):
        if not byte:
            continue
        owner = max((a for a in jumps if a < address), default=None)
        if owner is None or address - owner > 0x400:
            raise ValueError(f"Code-section index table {address:x} has no jump table before it")
        offset, count = address - text.address, 0
        while count < 256 and image[offset + count] < jumps[owner]:
            count += 1
        tables.append((address, image[offset:offset + count]))
    return tables



def accelerators(program, destination):
    """The main window's accelerator table (PE RT_ACCELERATOR "CLAW", which
    window creation loads through LoadAcceleratorsA at 0x4b8b13 and the message
    pump 0x4b8d10 passes to TranslateAcceleratorA): each entry's flags, key and
    command, up to the entry flagged last (0x80)."""
    table, entries = 0x54d99c, []
    section = next(s for s in program.sections if s.address <= table < s.address + s.size)
    if section.name == ".text":
        raise ValueError("Accelerator table must not be executable bytes")
    offset = table - section.address
    while True:
        flags, key, command, _ = struct.unpack_from("<4H", section.data, offset + 8 * len(entries))
        entries.append(dict(flags=flags & 0x7f, key=key, command=command))
        if flags & 0x80 or len(entries) > 256:
            break
    if len(entries) != 58:
        raise ValueError(f"Accelerator table has {len(entries)} entries, expected 58")
    (destination / "accelerators.json").write_text(json.dumps(entries) + "\n")
    return len(entries)


def level_one_transports(program, destination):
    """The native Level 1 join's owner election (work/native-level-one-join/
    owners.json, written by its build): vtable tail thunks with their slots,
    tail-only owners, and the original prologue extent of every elected
    caller whose child frame needs more than the default 0x400 gap."""
    from Tests.NativeLevelOne.native_join import original_frame_extent
    recorded = ROOT / "work/native-level-one-join/owners.json"
    target = destination / "level-one-transports.json"
    if not recorded.exists():
        raise ValueError(f"Missing required maintainer election: {recorded}")
    election = json.loads(recorded.read_text())
    if election.get("unresolved"):
        raise ValueError("Level 1 owner election has unresolved rows")
    extents = {}
    for address in sorted({*election["owners"], *election["tail_only"]}, key=lambda a: int(a, 16)):
        extent = original_frame_extent(program, int(address, 16))
        if ((extent + 0x4f) & ~0xf) > 0x400:
            extents[address] = extent
    data = dict(tail_thunks=election["tail_thunks"], tail_only=sorted(election["tail_only"]),
                frame_extents=extents)
    # Immediate original calls and terminal jumps may name a base body absent from a derived
    # vtable. Keep this authenticated relation with the local transport data,
    # rather than maintaining another caller-by-caller exception in Swift.
    import runpy
    audit = runpy.run_path(str(ROOT / "scripts/check-call-closure.py"))
    inventory = audit["registry"]()
    graph = audit["Graph"](program, {address for address in inventory if audit["game"](address)}).scan()
    targets = {int(address, 16) for address in data["tail_only"]}
    direct = {}
    for edge in graph.edges:
        if edge["kind"] in ("call", "tail") and edge.get("immediate") and edge["target"] in targets and edge["caller"] in inventory:
            direct.setdefault(hex(edge["caller"]), set()).add(hex(edge["target"]))
    data["original_direct_calls"] = {caller: sorted(values) for caller, values in sorted(direct.items())}
    data["original_sha256"] = program.sha256
    target.write_text(json.dumps(data) + "\n")
    return dict(tail_thunks=len(data["tail_thunks"]), tail_only=len(data["tail_only"]), frame_extents=len(extents))


if __name__ == "__main__":
    main()
