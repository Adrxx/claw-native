"""Load, validate and save family manifests (Tests/families/<id>.json)."""
import json
import re
import sys
from Tests.clawparity.abi import CALL_ARGUMENT_CAPACITY

from pathlib import Path

from .paths import FAMILIES, ROOT
from .owned_ranges import body_range_errors, canonical_overlap_errors
from Tests.clawparity.cases import compiler_contract_errors
from Tests.clawparity import build_inputs

SCHEMA = json.loads((FAMILIES / "schema.json").read_text()) if (FAMILIES / "schema.json").exists() else None
KEY_ORDER = list(SCHEMA["properties"]) if SCHEMA else []
# Shared, opt-in parity harness transport, with no original function ownership.
# This inventory exception neither admits a family nor changes app membership.
HARNESS_SUPPORT_SOURCES = frozenset({"Sources/ClawGuestTransfer.cpp"})


def _check(value, schema, where, errors):
    """A small JSON Schema subset: type, const, enum, pattern, required, properties, items."""
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in {schema['enum']}")
    kinds = schema.get("type")
    if kinds:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        names = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "null": type(None)}
        if not any(isinstance(value, names[k]) and not (k == "integer" and isinstance(value, bool)) for k in kinds):
            errors.append(f"{where}: expected {kinds}, found {type(value).__name__}")
            return
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{where}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing {key}")
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                _check(item, properties[key], f"{where}.{key}", errors)
            elif isinstance(extra, dict):
                _check(item, extra, f"{where}.{key}", errors)
            elif extra is False:
                errors.append(f"{where}: unexpected key {key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _check(item, schema["items"], f"{where}[{index}]", errors)


def validate(manifest, name=None):
    from Tests.clawparity.guest_contract import guest_contract_errors
    errors = compiler_contract_errors(manifest)
    errors.extend(guest_contract_errors(manifest))
    _check(manifest, SCHEMA, name or manifest.get("id", "?"), errors)
    if manifest.get("program") == "claw-v1.3":
        from Tests.clawparity.profiles import validate as validate_profile
        try:
            validate_profile(manifest)
        except (ValueError, OSError, KeyError, TypeError) as error:
            errors.append(f"invalid claw-v1.3 profile: {error}")
    errors.extend(body_range_errors(manifest))
    if "canonical_sources" in manifest or "shared_sources" in manifest:
        try:
            build_inputs.sources(manifest)
        except ValueError as error:
            errors.append(str(error))
    errors.extend(build_inputs.admission_errors(manifest))
    if name and manifest.get("id") != name:
        errors.append(f"{name}: id {manifest.get('id')!r} does not match the file name")
    for path in manifest.get("sources", []) + manifest.get("docs", []):
        if not (ROOT / path).exists():
            errors.append(f"{manifest.get('id')}: {path} does not exist")
    for address, callee in manifest.get("callees", {}).items():
        if not isinstance(callee, dict):
            continue
        if "x87_exact" in callee:
            effect = callee['x87_exact']
            if (not isinstance(effect, dict) or set(effect) != {'pop', 'push'} or
                    type(effect.get('pop')) is not int or not 0 <= effect['pop'] <= 8 or
                    type(effect.get('push')) is not int or not 0 <= effect['push'] <= 1):
                errors.append(f"{address}: invalid exact x87 stack effect")
        if "x87_exact" in callee and (callee.get("kind") != "whole" or
                callee.get("convention") not in ("cdecl", "stdcall", "thiscall") or
                type(callee.get("argc")) is not int or not 0 <= callee["argc"] <= CALL_ARGUMENT_CAPACITY or
                any(k in callee for k in ("x87_args", "source_context", "compiler_context"))):
            errors.append(f"{address}: x87_exact requires an exclusive original whole ordinary callee")
        if "x87_args" in callee and (callee.get("kind") != "whole" or
                                    callee.get("convention") not in ("cdecl", "stdcall", "thiscall") or
                                    type(callee.get("argc")) is not int or not 0 <= callee["argc"] <= CALL_ARGUMENT_CAPACITY):
            errors.append(f"{address}: x87_args requires an original whole callee with convention and argc (0..{CALL_ARGUMENT_CAPACITY})")
    return errors


def paths():
    return sorted(p for p in FAMILIES.glob("*.json") if p.name != "schema.json" and not p.name.startswith("_"))


def load(family):
    return json.loads((FAMILIES / f"{family}.json").read_text())


def load_all():
    return {p.stem: json.loads(p.read_text()) for p in paths()}


def save(manifest):
    ordered = {k: manifest[k] for k in KEY_ORDER if k in manifest}
    (FAMILIES / f"{manifest['id']}.json").write_text(json.dumps(ordered, indent=2) + "\n")


def check_all():
    """Validate every manifest and the cross-family rules. Returns a JSON-ready summary."""
    manifests = load_all()
    errors = []
    for name, manifest in manifests.items():
        errors.extend(validate(manifest, name))
    errors.extend(canonical_overlap_errors(manifests))
    owner = {}
    for name, manifest in manifests.items():
        for source in manifest.get("sources", []):
            if source.endswith(".cpp"):
                if source in owner:
                    errors.append(f"{source}: owned by both {owner[source]} and {name}")
                owner[source] = name
    for cpp in sorted((ROOT / "Sources").glob("*.cpp")):
        if f"Sources/{cpp.name}" not in owner and f"Sources/{cpp.name}" not in HARNESS_SUPPORT_SOURCES:
            errors.append(f"Sources/{cpp.name}: belongs to no family")
    script_owner = {}
    for name, manifest in manifests.items():
        for command in manifest.get("oracle", {}).get("commands", []):
            script = command["script"]
            if script in script_owner:
                errors.append(f"{script}: listed by both {script_owner[script]} and {name}")
            script_owner[script] = name
    for script in sorted((ROOT / "Tests").glob("compare_*.py")):
        if f"Tests/{script.name}" not in script_owner:
            errors.append(f"Tests/{script.name}: belongs to no family")
    address_owner = {}
    for name, manifest in manifests.items():
        for entry in manifest.get("owned", []):
            address_owner.setdefault(entry["address"], []).append(name)
    shared = {a: n for a, n in address_owner.items() if len(n) > 1}
    return {
        "command": "manifest-check",
        "families": len(manifests),
        "errors": errors[:60],
        "error_count": len(errors),
        "addresses_owned": len(address_owner),
        "addresses_owned_by_several": len(shared),
        "status": "pass" if not errors else "fail",
    }


def main(argv):
    print(json.dumps(check_all()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
