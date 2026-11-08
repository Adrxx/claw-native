"""Address-to-name map for the original executable.

Builds Tests/symbols.json from structured data only: the PE import table and
section headers of the hash-pinned original CLAW.EXE, and the registration
tables already recovered in tracked sources (logic class names and state names
with their callback addresses).  No name is inferred from behavior.

Subcommands:
    build           write Tests/symbols.json
    check           verify the map (acceptance) and that the file is current
    name <address>  nearest named symbol at or below an address

Every subcommand prints exactly one line of JSON as its final stdout line.
"""
import hashlib
import json
import re
import struct
import sys

from tools.claw import paths

SYMBOLS_FILE = paths.TESTS / "symbols.json"
IMAGE_BASE = 0x400000
MIN_IMPORTS = 150
MIN_CALLBACKS = 200

LOGIC_REGISTRY = paths.SOURCES / "LogicRegistry.cpp"
STARTUP_PROGRAM = paths.SOURCES / "StartupLogicRegistrationProgram.inc"
STATE_REGISTRY = paths.SOURCES / "LogicStateRegistry.cpp"

# Higher number wins when two sources name the same address.
TRUST = {
    "import": 3,
    "section": 3,
    "logic-callback": 2,
    "state-callback": 2,
    "function": 2,
    "vtable": 1,
}

HEX_ADDRESS = re.compile(r"^0x[0-9a-f]{8}$")


def format_address(address):
    return "0x%08x" % address


def parse_address(text):
    return int(text, 0)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- PE parsing


class PEImage:
    """Just enough of a PE32 file to list sections and imports."""

    def __init__(self, data):
        self.data = data
        self.sections = []
        self.import_rva = 0
        self.image_base = 0
        self._parse_headers()

    def _parse_headers(self):
        data = self.data
        if data[:2] != b"MZ":
            raise ValueError("missing MZ header")
        (pe_offset,) = struct.unpack_from("<I", data, 0x3C)
        if data[pe_offset:pe_offset + 4] != b"PE\0\0":
            raise ValueError("missing PE signature")
        coff = pe_offset + 4
        (_machine, section_count, _stamp, _symtab, _symcount,
         optional_size, _characteristics) = struct.unpack_from("<HHIIIHH", data, coff)
        optional = coff + 20
        (magic,) = struct.unpack_from("<H", data, optional)
        if magic != 0x10B:
            raise ValueError("not a PE32 image")
        (self.image_base,) = struct.unpack_from("<I", data, optional + 28)
        directories = optional + 96
        (self.import_rva, _import_size) = struct.unpack_from("<II", data, directories + 8)
        table = optional + optional_size
        for index in range(section_count):
            self.sections.append(self._parse_section(table + index * 40))

    def _parse_section(self, offset):
        raw_name = self.data[offset:offset + 8].rstrip(b"\0")
        (virtual_size, virtual_address, raw_size,
         raw_pointer) = struct.unpack_from("<IIII", self.data, offset + 8)
        return {
            "name": raw_name.decode("ascii", "replace"),
            "rva": virtual_address,
            "virtual_size": virtual_size,
            "raw_size": raw_size,
            "raw_pointer": raw_pointer,
        }

    def file_offset(self, rva):
        for section in self.sections:
            span = max(section["virtual_size"], section["raw_size"])
            if section["rva"] <= rva < section["rva"] + span:
                return section["raw_pointer"] + rva - section["rva"]
        raise ValueError("RVA 0x%x is not inside a section" % rva)

    def read_string(self, rva):
        start = self.file_offset(rva)
        end = self.data.index(b"\0", start)
        return self.data[start:end].decode("ascii", "replace")

    def imports(self):
        """Yield (iat_slot_address, 'DLL!Function') for every import."""
        if not self.import_rva:
            return
        descriptor = self.file_offset(self.import_rva)
        while True:
            fields = struct.unpack_from("<IIIII", self.data, descriptor)
            lookup_rva, _stamp, _forwarder, name_rva, address_rva = fields
            if not name_rva and not address_rva:
                break
            dll = self.read_string(name_rva)
            yield from self._descriptor_imports(dll, lookup_rva or address_rva, address_rva)
            descriptor += 20

    def _descriptor_imports(self, dll, lookup_rva, address_rva):
        lookup = self.file_offset(lookup_rva)
        slot = 0
        while True:
            (thunk,) = struct.unpack_from("<I", self.data, lookup + slot * 4)
            if thunk == 0:
                break
            if thunk & 0x80000000:
                function = "#%d" % (thunk & 0xFFFF)
            else:
                function = self.read_string(thunk + 2)
            address = self.image_base + address_rva + slot * 4
            yield address, "%s!%s" % (dll, function)
            slot += 1


def import_and_section_symbols():
    """Return (sha256, records) from the original executable."""
    digest = file_sha256(paths.ORIGINAL_EXE)
    if digest != paths.ORIGINAL_SHA256:
        raise ValueError("CLAW.EXE hash mismatch: %s" % digest)
    image = PEImage(paths.ORIGINAL_EXE.read_bytes())
    if image.image_base != IMAGE_BASE:
        raise ValueError("unexpected image base 0x%x" % image.image_base)
    source = "Original/claw10/CLAW.EXE import directory"
    records = []
    for address, name in image.imports():
        records.append((address, name, "import", source, {}))
    section_source = "Original/claw10/CLAW.EXE section table"
    for section in image.sections:
        address = IMAGE_BASE + section["rva"]
        extra = {"size": section["virtual_size"]}
        records.append((address, section["name"], "section", section_source, extra))
    return digest, records


# ------------------------------------------------------- source table parsing

LOGIC_ENTRY = re.compile(
    r'\{\s*"(\w+)"\s*,\s*(\d+)\s*,\s*0x([0-9a-fA-F]+)\s*,\s*0x([0-9a-fA-F]+)\s*,\s*(\d+)\s*\}'
)
PROGRAM_ENTRY = re.compile(r"\{\s*(\d+)u\s*,\s*0x([0-9a-fA-F]+)u\s*\}")
BINDING_ENTRY = re.compile(
    r"\{\s*0x([0-9a-fA-F]+)\s*,\s*0x([0-9a-fA-F]+)\s*,\s*0x([0-9a-fA-F]+)\s*,"
    r"\s*0x([0-9a-fA-F]+)\s*,\s*0x([0-9a-fA-F]+)\s*,\s*\"(\w+)\"\s*\}"
)
BINDING_KINDS = {0: "logic-callback", 1: "state-callback"}


def logic_registry_records():
    """Logic class name -> callback, from LogicRegistry.cpp. Also ordinals."""
    text = LOGIC_REGISTRY.read_text()
    source = "Sources/LogicRegistry.cpp entries[]"
    records = []
    ordinals = {}
    for name, ordinal, _name_address, callback, _flags in LOGIC_ENTRY.findall(text):
        address = int(callback, 16)
        if address == 0:
            continue
        records.append((address, name, "logic-callback", source, {}))
        ordinals[int(ordinal)] = address
    return records, ordinals


def startup_program_conflicts(ordinals):
    """Cross-check the startup program's ordinal -> callback pairs.

    The program names nothing itself; it must agree with LogicRegistry.cpp.
    Returns the list of ordinals whose callback differs.
    """
    text = STARTUP_PROGRAM.read_text()
    disagreements = []
    for ordinal_text, function_text in PROGRAM_ENTRY.findall(text):
        ordinal = int(ordinal_text)
        if ordinal == 0:
            continue
        if ordinals.get(ordinal) != int(function_text, 16):
            disagreements.append(ordinal)
    return disagreements


def state_registry_records():
    """Logic and state names from the bootstrap[] table of LogicStateRegistry.cpp."""
    text = STATE_REGISTRY.read_text()
    start = text.index("const Binding bootstrap[]")
    end = text.index("};", start)
    source = "Sources/LogicStateRegistry.cpp bootstrap[]"
    records = []
    for kind, _token, _literal, function, _flags, name in BINDING_ENTRY.findall(text[start:end]):
        record_kind = BINDING_KINDS.get(int(kind, 16))
        address = int(function, 16)
        if record_kind is None or address == 0:
            continue
        records.append((address, name, record_kind, source, {}))
    return records


# ------------------------------------------------------------------ building


def merge(records):
    """Merge records; keep the higher-trust name and list disagreements."""
    symbols = {}
    conflicts = []
    for address, name, kind, source, extra in records:
        key = format_address(address)
        entry = {"name": name, "kind": kind, "source": source}
        entry.update(extra)
        existing = symbols.get(key)
        if existing is None:
            symbols[key] = entry
            continue
        if existing["name"] == name:
            continue
        keep, drop = existing, entry
        if TRUST[kind] > TRUST[existing["kind"]]:
            keep, drop = entry, existing
            symbols[key] = entry
        if any(c["address"] == key and c["dropped"]["name"] == drop["name"] and c["kept"]["name"] == keep["name"] for c in conflicts):
            continue
        conflicts.append({
            "address": key,
            "kept": {"name": keep["name"], "kind": keep["kind"], "source": keep["source"]},
            "dropped": {"name": drop["name"], "kind": drop["kind"], "source": drop["source"]},
        })
    return dict(sorted(symbols.items())), conflicts


def build_document():
    digest, records = import_and_section_symbols()
    registry_records, ordinals = logic_registry_records()
    disagreements = startup_program_conflicts(ordinals)
    if disagreements:
        raise ValueError("startup program disagrees with registry for ordinals %s" % disagreements)
    records.extend(registry_records)
    records.extend(state_registry_records())
    symbols, conflicts = merge(records)
    return {"sha256": digest, "symbols": symbols, "conflicts": conflicts}


def render(document):
    return json.dumps(document, indent=1, sort_keys=False) + "\n"


def load_document():
    return json.loads(SYMBOLS_FILE.read_text())


# ------------------------------------------------------------------- commands


def count_by_kind(symbols):
    counts = {}
    for entry in symbols.values():
        counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
    return dict(sorted(counts.items()))


def command_build(_args):
    document = build_document()
    SYMBOLS_FILE.write_text(render(document))
    result = {
        "command": "symbols-build",
        "file": paths.relative(SYMBOLS_FILE),
        "symbols": len(document["symbols"]),
        "by_kind": count_by_kind(document["symbols"]),
        "conflicts": len(document["conflicts"]),
        "status": "pass",
    }
    print(json.dumps(result))
    return 0


def text_section_bounds(symbols):
    for key, candidate in symbols.items():
        if candidate["kind"] == "section" and candidate["name"] == ".text":
            start = int(key, 16)
            return start, start + candidate["size"]
    return None


def check_problems(document):
    problems = []
    symbols = document["symbols"]
    counts = count_by_kind(symbols)
    if document.get("sha256") != paths.ORIGINAL_SHA256:
        problems.append("sha256 does not match the pinned executable")
    if counts.get("import", 0) < MIN_IMPORTS:
        problems.append("fewer than %d imports" % MIN_IMPORTS)
    callbacks = counts.get("logic-callback", 0) + counts.get("state-callback", 0)
    if callbacks < MIN_CALLBACKS:
        problems.append("fewer than %d logic or state callbacks" % MIN_CALLBACKS)
    keys = list(symbols)
    for key in keys:
        if not HEX_ADDRESS.match(key):
            problems.append("malformed key %s" % key)
    if keys != sorted(keys):
        problems.append("keys are not sorted")
    bounds = text_section_bounds(symbols)
    if bounds is None:
        problems.append("no .text section recorded")
    else:
        for key, entry in symbols.items():
            if entry["kind"] == "function" and not bounds[0] <= int(key, 16) < bounds[1]:
                problems.append("function %s outside .text" % key)
    return problems


def command_check(_args):
    problems = []
    document = None
    if not SYMBOLS_FILE.exists():
        problems.append("Tests/symbols.json is missing")
    else:
        document = load_document()
        problems.extend(check_problems(document))
        if render(build_document()) != SYMBOLS_FILE.read_text():
            problems.append("Tests/symbols.json is stale; run build")
    symbols = document["symbols"] if document else {}
    result = {
        "command": "symbols-check",
        "symbols": len(symbols),
        "by_kind": count_by_kind(symbols),
        "conflicts": len(document["conflicts"]) if document else 0,
        "status": "pass" if not problems else "fail",
    }
    if problems:
        result["problems"] = problems
    print(json.dumps(result))
    return 0 if not problems else 1


def command_name(args):
    if not args:
        print(json.dumps({"command": "symbols-name", "status": "fail", "error": "address required"}))
        return 2
    address = parse_address(args[0])
    symbols = load_document()["symbols"]
    best = None
    for key in symbols:
        if int(key, 16) <= address:
            best = key
        else:
            break
    result = {"command": "symbols-name", "address": format_address(address)}
    if best is None:
        result["found"] = False
    else:
        entry = symbols[best]
        result.update({
            "found": True,
            "symbol": best,
            "name": entry["name"],
            "kind": entry["kind"],
            "offset": address - int(best, 16),
        })
    print(json.dumps(result))
    return 0


COMMANDS = {"build": command_build, "check": command_check, "name": command_name}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(json.dumps({"command": "symbols", "status": "fail", "error": "usage: build|check|name <address>"}))
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
