"""Checks a canonical family's specification against the disassembly. Prints one JSON line."""
import json
import sys
from pathlib import Path

from . import index, manifest
from .owned_ranges import canonical_overlap_errors
from .paths import ROOT


def lint(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    errors, warnings = list(manifest.validate(spec)), []
    if spec.get("abi") != "canonical":
        errors.append("speclint applies to canonical families only")
    if spec.get("program") == "claw-v1.3":
        from Tests.clawparity.profiles import lint as lint_profile
        profile_errors, warnings = lint_profile(spec)
        errors.extend(profile_errors)
        others = {name: other for name, other in manifest.load_all().items() if name != spec.get("id")}
        errors.extend(canonical_overlap_errors([*others.values(), spec]))
        return {"command": "spec-lint", "family": spec.get("id"),
                "status": "pass" if not errors else "fail", "errors": errors, "warnings": warnings}
    functions = index.functions()
    imports = {a for a, s in index.symbols().items() if s["kind"] == "import"}
    owned = {int(o["address"], 16): o for o in spec.get("owned", [])}
    callees = {int(a, 16): c for a, c in spec.get("callees", {}).items()}
    for address, declared in owned.items():
        function = functions.get(address)
        if function is None:
            inside = index.containing(address)
            where = f" (it is inside {inside['entry']})" if inside else ""
            errors.append(f"owned {address:#x} is not a function entry{where}")
            continue
        if declared.get("convention") in (None, "unknown") or declared.get("argc") is None:
            errors.append(f"owned {address:#x}: convention and argc must be declared")
            continue
        popped = set() if declared["convention"] == "compiler-context" else index.returned_bytes(address)
        callee_pops = declared["convention"] in ("thiscall", "stdcall", "fastcall")
        expected = {4 * declared["argc"]} if callee_pops else {0}
        if popped and popped != expected:
            errors.append(f"owned {address:#x}: declared {declared['convention']} with {declared['argc']} stack "
                          f"arguments, but its return instructions remove {sorted(popped)} bytes")
        if function.get("unaff_count") or function.get("jumptable_warning") or not function.get("decompile_ok", True):
            warnings.append(f"owned {address:#x}: the decompile is unreliable (unaff={function.get('unaff_count')}, "
                            f"jumptable={function.get('jumptable_warning')}); work from the disassembly")
        for target, sites in index.call_targets(address).items():
            if target in owned:
                continue
            if target in imports and callees.get(target, {}).get("kind") != "fixture":
                errors.append(f"owned {address:#x} calls import {target:#x} ({index.name(target)}); imports must be "
                              f"declared as fixtures")
            elif target not in callees and target not in functions and target not in imports:
                warnings.append(f"owned {address:#x} calls {target:#x}, which is not a known function entry")
        if index.indirect_call_sites(address):
            warnings.append(f"owned {address:#x} makes {len(index.indirect_call_sites(address))} indirect calls; "
                            + ("guest cases must use the declared original factory addresses" if spec.get('oracle', {}).get('guest_graph')
                               else "cases must supply those function pointers with env.stub"))
    for address, callee in callees.items():
        if callee.get('convention') == 'compiler-context':
            if address not in functions:
                errors.append(f"compiler dependency {address:#x} must name an original function entry")
            continue
        if 'source_context' in callee:
            if address not in functions:
                errors.append(f"source dependency {address:#x} must name an original function entry")
            else:
                popped = index.returned_bytes(address)
                expected = {4 * callee['argc']} if callee['convention'] in ('stdcall', 'thiscall', 'fastcall') else {0}
                if popped and popped != expected:
                    errors.append(f"source dependency {address:#x}: return pop disagrees with ordinary signature")
        if callee["kind"] != "fixture":
            continue
        if "convention" not in callee or "argc" not in callee:
            errors.append(f"fixture {address:#x}: convention and argc are required")
            continue
        if not callee.get("reason"):
            warnings.append(f"fixture {address:#x} has no reason; every stand-in should say why the original cannot run")
        if address in functions:
            popped = index.returned_bytes(address)
            callee_pops = callee["convention"] in ("thiscall", "stdcall", "fastcall")
            expected = {4 * callee["argc"]} if callee_pops else {0}
            if popped and popped != expected:
                errors.append(f"fixture {address:#x}: declared {callee['convention']} with {callee['argc']} arguments, "
                              f"but its return instructions remove {sorted(popped)} bytes")
    others = {name: other for name, other in manifest.load_all().items() if name != spec.get("id")}
    errors.extend(canonical_overlap_errors([*others.values(), spec], corpus=functions))
    return {"command": "spec-lint", "family": spec.get("id"), "status": "pass" if not errors else "fail",
            "errors": errors, "warnings": warnings}


def main(argv):
    result = lint(argv[0])
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
