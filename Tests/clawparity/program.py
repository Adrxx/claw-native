"""The executable under test: its bytes, sections and imports."""
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAW_EXE = ROOT / "Original" / "claw10" / "CLAW.EXE"
CLAW_SHA256 = "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263"


@dataclass
class Section:
    name: str
    address: int
    size: int      # virtual size
    data: bytes    # initialized bytes; the rest of the section is zero


@dataclass
class Program:
    name: str
    sha256: str
    base: int
    size: int                 # mapped size, a multiple of 4096
    sections: list
    text: tuple               # (start, end) of executable code
    imports: dict             # import-table slot address -> "DLL!Function"
    startup_calls: tuple = () # run once after mapping, before any test
    control_word: tuple = None  # (mask, value) the x87 control word must match after startup

    def in_text(self, address):
        return self.text[0] <= address < self.text[1]

    @property
    def data_start(self):
        """First address after the code. Everything from here to the end of the image is compared as data."""
        return (self.text[1] + 0xFFF) & ~0xFFF

    @classmethod
    def from_pe(cls, path, sha256, name, startup_calls=(), control_word=None):
        raw = Path(path).read_bytes()
        return cls.from_bytes(raw, sha256, name, startup_calls, control_word, origin=str(path))

    @classmethod
    def from_bytes(cls, raw, sha256, name, startup_calls=(), control_word=None, *, origin="PE bytes"):
        found = hashlib.sha256(raw).hexdigest()
        if found != sha256:
            raise ValueError(f"{origin}: expected SHA-256 {sha256}, found {found}")
        header = struct.unpack_from("<I", raw, 0x3C)[0]
        section_count = struct.unpack_from("<H", raw, header + 6)[0]
        optional_size = struct.unpack_from("<H", raw, header + 20)[0]
        base = struct.unpack_from("<I", raw, header + 52)[0]
        image_size = struct.unpack_from("<I", raw, header + 80)[0]
        import_rva = struct.unpack_from("<I", raw, header + 24 + 96 + 8)[0]
        sections = []
        table = []  # (rva, raw offset, raw size) for address translation
        for index in range(section_count):
            at = header + 24 + optional_size + 40 * index
            label = raw[at:at + 8].rstrip(b"\0").decode("latin-1")
            virtual_size, rva, raw_size, raw_offset = struct.unpack_from("<4I", raw, at + 8)
            sections.append(Section(label, base + rva, virtual_size, raw[raw_offset:raw_offset + raw_size]))
            table.append((rva, raw_offset, raw_size))

        def offset(rva):
            for start, raw_offset, raw_size in table:
                if start <= rva < start + raw_size:
                    return raw_offset + rva - start
            raise ValueError(f"RVA {rva:#x} is not backed by file bytes")

        def text_at(rva):
            start = offset(rva)
            return raw[start:raw.index(b"\0", start)].decode("latin-1")

        imports = {}
        descriptor = offset(import_rva) if import_rva else None
        while descriptor is not None:
            lookup, _, _, name_rva, thunks = struct.unpack_from("<5I", raw, descriptor)
            if not name_rva:
                break
            library = text_at(name_rva)
            entry = offset(lookup or thunks)
            index = 0
            while True:
                value = struct.unpack_from("<I", raw, entry + 4 * index)[0]
                if not value:
                    break
                function = f"#{value & 0xFFFF}" if value & 0x80000000 else text_at(value + 2)
                imports[base + thunks + 4 * index] = f"{library}!{function}"
                index += 1
            descriptor += 20
        code = next(s for s in sections if s.name == ".text")
        return cls(name, sha256, base, (image_size + 0xFFF) & ~0xFFF, sections,
                   (code.address, code.address + code.size), imports, tuple(startup_calls), control_word)


def claw():
    """Captain Claw v1.0. The startup call is the C runtime's floating-point precision setup."""
    return Program.from_pe(CLAW_EXE, CLAW_SHA256, "claw-v1.0", startup_calls=(0x4A7EF0,), control_word=(0x0F3F, 0x023F))


def claw_v13():
    """Load v1.3 lazily; its implementation is not a v1.0 admission input."""
    from .program_v13 import claw_v13 as load
    return load()


def __getattr__(name):
    # Preserve the public identity constants without importing another profile
    # on the v1.0 runner path.
    if name in ("CLAW_V13_WRAPPER", "CLAW_V13_WRAPPER_SHA256", "CLAW_V13_SHA256"):
        from . import program_v13
        return getattr(program_v13, name)
    raise AttributeError(name)


def profile(name="claw-v1.0"):
    """Select a pinned game identity; no path/hash override and no implicit rebasing."""
    if name == "claw-v1.0":
        return claw()
    if name == "claw-v1.3":
        return claw_v13()
    raise ValueError(f"unknown Claw profile {name!r}")
