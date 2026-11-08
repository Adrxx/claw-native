"""Prepare bounded startup data from the pinned original, without executing it.

Source strings/globals go in the permitted App/OriginalTables folder. This supplies metadata;
source startup still owns configuration reads and scene election.
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw

STRINGS = (
    0x5258b8, 0x524eec, 0x5258d0, 0x532474, 0x534938,
    0x5258a8, 0x52589c, 0x525890, 0x525880, 0x525874, 0x525860,
    0x525850, 0x525840, 0x52582c, 0x525818, 0x5257fc, 0x5257ec,
    0x5257dc, 0x5257c8, 0x5257b4, 0x525798, 0x525784, 0x525770,
    0x525758, 0x525744, 0x525730, 0x52571c, 0x525714, 0x52570c,
    0x525704, 0x5256fc, 0x5256f4, 0x5256e8, 0x5256dc, 0x5256d0,
    0x5256c0, 0x5256b0,
)
GLOBALS = (
    0x525510, 0x525514, 0x525518, *range(0x537234, 0x53725c, 4),
    0x52c6e4, 0x52c6e8, 0x52c6ec, 0x527134, 0x527130, 0x527138,
)
DISC_STRINGS = (0x525ec4, 0x524f08)
TEXT_STRINGS = (0x5256a8, 0x5256a0, 0x525698, 0x525690,
                0x52568c, 0x525684, 0x52567c, 0x525674)


def prepare():
    program = claw()  # Hash validation precedes every source read.

    def read(address, count):
        for section in program.sections:
            if section.address <= address and address + count <= section.address + section.size:
                if section.name == ".text":
                    raise ValueError("Startup metadata must not contain executable bytes")
                offset = address - section.address
                return section.data[offset:offset + count].ljust(count, b"\0")
        raise ValueError(f"Unmapped source span {address:#x}+{count}")

    def collect(addresses):
        strings = {}
        for address in addresses:
            value = bytearray()
            for offset in range(256):
                value.extend(read(address + offset, 1))
                if value[-1] == 0:
                    break
            else:
                raise ValueError(f"Unterminated source string {address:#x}")
            strings[str(address)] = value.hex()
        return strings

    strings, disc_strings = collect(STRINGS), collect(DISC_STRINGS)
    initial = {str(a): struct.unpack("<I", read(a, 4))[0] for a in GLOBALS}
    text_initial = {str(0x540e88): struct.unpack("<I", read(0x540e88, 4))[0]}
    pregraphics_initial = {str(0x537070): struct.unpack("<I", read(0x537070, 4))[0]}
    destination = ROOT / "App/OriginalTables/APPLICATION/startup.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(dict(schema=1, sha256=program.sha256,
        strings=strings, discStrings=disc_strings, initialGlobals=initial,
        textStrings=collect(TEXT_STRINGS), textInitialGlobals=text_initial,
        pregraphicsInitialGlobals=pregraphics_initial), indent=2) + "\n")
    print(json.dumps(dict(status="pass", source_sha256=program.sha256,
        strings=len(strings), disc_strings=len(disc_strings), globals=len(initial), output=str(destination),
        scope="Prepared source metadata only; no scene election or startup completion")))


if __name__ == "__main__":
    prepare()
