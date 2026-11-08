"""Read access to the local function corpus (work/corpus), which is derived from the original and never tracked."""
import json
import re
from functools import lru_cache

from .paths import CORPUS, TESTS

CALL = re.compile(r"\bcall (?:dword ptr \[)?0x([0-9a-f]+)\]?$")
RETURN = re.compile(r"\bret(?: 0x([0-9a-f]+)| (\d+))?$")


@lru_cache(maxsize=1)
def functions():
    """Every function of the original, keyed by entry address."""
    path = CORPUS / "index.json"
    if not path.exists():
        raise FileNotFoundError("work/corpus/index.json is missing; run `make corpus`")
    return {int(f["entry"], 16): f for f in json.loads(path.read_text())["functions"]}


def containing(address):
    """The function whose body contains `address`, or None."""
    for entry, function in functions().items():
        if any(low <= address < high for low, high in function["ranges"]):
            return function
    return None


@lru_cache(maxsize=1)
def symbols():
    path = TESTS / "symbols.json"
    if not path.exists():
        return {}
    return {int(a, 16): entry for a, entry in json.loads(path.read_text())["symbols"].items()}


def name(address):
    entry = symbols().get(address)
    return entry["name"] if entry else ""


def assembly(entry):
    path = CORPUS / "asm" / f"{entry:08x}.asm"
    return path.read_text().splitlines() if path.exists() else []


def decompile_path(entry):
    return CORPUS / "c" / f"{entry:08x}.c"


def call_targets(entry):
    """Direct calls and import-slot calls made by a function: {target address: number of call sites}."""
    found = {}
    for line in assembly(entry):
        match = CALL.search(line)
        if match:
            target = int(match.group(1), 16)
            found[target] = found.get(target, 0) + 1
    return found


def indirect_call_sites(entry):
    """Call instructions whose target is computed at run time (virtual calls, function pointers)."""
    return [line for line in assembly(entry) if " call " in f" {line}" and not CALL.search(line)]


def returned_bytes(entry):
    """Bytes of stack arguments the function itself removes on return: a set, normally with one member."""
    found = set()
    for line in assembly(entry):
        match = RETURN.search(line)
        if match:
            found.add(int(match.group(1), 16) if match.group(1) else int(match.group(2) or 0))
    return found
