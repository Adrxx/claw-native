"""Drafts a canonical specification from the disassembly, so that a model reviews only what a script cannot decide.

    python -m tools.claw.draft_spec --id <id> --title "<title>" --seeds 0x... [0x...] [--pilot]

Writes the specification, the module and cases stubs and the task packet, and prints one JSON line. The line lists
`needs_review`: every point the script could not settle from the disassembly alone. An empty list means the draft can
go straight to the case author.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from . import index, packet, skeleton, speclint
from .paths import ROOT, TESTS

SIGNATURE = re.compile(r"^\s*([\w\s\*]+?)\s+(__\w+)\s+\w+\(([^)]*)\)\s*$", re.M)
KNOWN = TESTS / "clawparity" / "known_fixtures.json"


def paths(family, pilot):
    if pilot:
        directory = f"work/pilot/{family}"
        return f"{directory}/family.json", f"{directory}/Module.cpp", f"{directory}/cases.py"
    name = "".join(part.capitalize() for part in family.split("_"))
    return f"Tests/families/{family}.json", f"Sources/{name}Runtime.cpp", f"Tests/families/{family}.cases.py"


def describe(address, review):
    """Convention, stack-argument count and return type of one function, from its disassembly and decompiled signature."""
    function = index.functions().get(address)
    if function is None:
        review.append(f"{address:#x} is not a function entry")
        return None
    text = index.decompile_path(address).read_text() if index.decompile_path(address).exists() else ""
    match = SIGNATURE.search(text)
    returned, convention, parameters = ("undefined4", function.get("calling_convention", ""), [])
    if match:
        returned, convention = match.group(1).strip(), match.group(2)
        parameters = [p for p in (q.strip() for q in match.group(3).split(",")) if p and p != "void"]
    else:
        review.append(f"{address:#x}: could not read the decompiled signature")
    popped = index.returned_bytes(address)
    if len(popped) > 1:
        review.append(f"{address:#x}: return instructions remove different byte counts {sorted(popped)}")
    removed = max(popped) if popped else 0
    uses_ecx = convention in ("__thiscall", "__fastcall")
    register_parameters = min(len(parameters), 1) if uses_ecx else 0
    if removed:
        argc = removed // 4
        kind = "thiscall" if uses_ecx else "stdcall"
    elif uses_ecx:
        argc, kind = 0, "thiscall"
        if len(parameters) - register_parameters > 0:
            review.append(f"{address:#x}: the decompiler shows {len(parameters)} parameters but the function removes no "
                          f"stack bytes; a second register parameter (EDX) or caller-cleaned arguments are possible")
    else:
        argc, kind = len(parameters), "cdecl"
        if argc:
            review.append(f"{address:#x}: cdecl with {argc} argument(s) taken from the decompiler; confirm against a call site")
    if convention == "__fastcall" and removed and len(parameters) - removed // 4 >= 2:
        review.append(f"{address:#x}: looks like a true fastcall with a parameter in EDX")
    if re.search(r"\b(float|double|float10)\b", returned):
        review.append(f"{address:#x}: returns a floating-point value, which the harness cannot compare yet")
    if function.get("unaff_count") or function.get("jumptable_warning") or not function.get("decompile_ok", True):
        review.append(f"{address:#x}: the decompile is unreliable; the disassembly must be read")
    return {"address": f"{address:#x}", "name": "", "convention": kind, "argc": argc,
            "returns": "void" if returned == "void" else "u32", "confidence": "declared"}


def reachable(owned, known, depth=5):
    """Known fixtures and imports the owned functions can reach through callees that run as original code."""
    functions = index.functions()
    imports = {a for a, s in index.symbols().items() if s["kind"] == "import"}
    found_known, found_imports, seen = set(), {}, set(owned)
    frontier = [(address, (address,)) for address in owned]
    for _ in range(depth):
        following = []
        for address, path in frontier:
            for target in index.call_targets(address):
                if target in known:
                    found_known.add(target)
                elif target in imports:
                    found_imports.setdefault(target, path)
                elif target in functions and target not in seen:
                    seen.add(target)
                    following.append((target, path + (target,)))
        frontier = following
    return found_known, found_imports


def draft(family, title, seeds, pilot, object_logic=False, compiler_context=False, input_mask=None, output_mask=None, source_context=False, preserve_mask=None, library_reason=None):
    if preserve_mask is not None and not source_context:
        raise ValueError('source preservation mask requires --source-context')
    if compiler_context and source_context:
        raise ValueError('source-context and compiler-context channels are exclusive')
    if compiler_context:
        from .manifest import compiler_contract_errors
        signature = {"convention": "compiler-context", "argc": 0, "returns": "context",
                     "compiler_context": {"input_mask": input_mask, "output_mask": output_mask}}
        errors = compiler_contract_errors({"abi": "canonical", "owned": [signature]})
        if object_logic or errors:
            raise ValueError("compiler-context needs valid explicit masks and cannot be object-logic: " + "; ".join(errors))
    elif not source_context and (input_mask is not None or output_mask is not None or preserve_mask is not None):
        raise ValueError("masks require --compiler-context")
    spec_path, module, cases = paths(family, pilot)
    review, advice = [], []
    from .progress_page import in_game
    platform = [f"{a:#x}" for a in seeds if not in_game(a)]
    if platform and not library_reason:
        return {"command": "draft", "family": family, "status": "refused",
                "detail": f"{', '.join(platform)} is C runtime or MFC code. The platform layer is replaced by native "
                          f"code (docs/OPERATING.md). Pass --library-reason only if the owner asked for this function."}
    owned = [entry for entry in (describe(address, review) for address in seeds) if entry]
    if compiler_context:
        owned = [{"address": f"{address:#x}", "name": "", "confidence": "declared", **signature}
                 for address in seeds if address in index.functions()]
        review = [f"{address:#x}: compiler-context ownership, masks and genuine continuations require boundary review"
                  for address in seeds]
    if object_logic:
        # The game calls every registered object-logic callback the same way: cdecl, the object as the only
        # argument, result unused. That settles what the disassembly alone leaves open.
        for entry in owned:
            entry["convention"], entry["argc"], entry["returns"] = "cdecl", 1, "void"
        review[:] = [point for point in review if "cdecl with" not in point and "decompiled signature" not in point
                     and "unreliable" not in point]
    if source_context:
        from .manifest import compiler_contract_errors
        for entry in owned:
            entry['source_context'] = dict(input_mask=input_mask, output_mask=output_mask, preserve_mask=preserve_mask)
        errors = compiler_contract_errors({'abi': 'canonical', 'owned': owned})
        if errors or object_logic:
            raise ValueError('source-context requires explicit valid ordinary contracts: ' + '; '.join(errors))
        review.extend(f"{entry['address']}: source context masks, preservation and real callsites require boundary review" for entry in owned)
    known = {int(a, 16): c for a, c in json.loads(KNOWN.read_text())["fixtures"].items()}
    found_known, found_imports = reachable(seeds, known)
    callees = {f"{a:#x}": known[a] for a in sorted(found_known)}
    limits = [f"{known[a]['name']} is a stand-in ({known[a]['fixture']})." for a in sorted(found_known)]
    for target, path in sorted(found_imports.items()):
        name = index.name(target)
        route = " -> ".join(f"{a:#x}" for a in path)
        if len(path) == 1:
            review.append(f"{path[0]:#x} calls import {target:#x} ({name}) directly: declare it as a fixture with its "
                          f"convention, argument count and behavior")
        else:
            advice.append(f"import {target:#x} ({name}) is reachable through {route}: cases must stay off that path "
                          f"unless a callee on the route becomes a fixture")
    spec = {
        "schema": 1, "id": family, "title": title, "abi": "canonical", "sources": [module], "owned": owned,
        "callees": callees,
        "oracle": {"kind": "clawparity", "cases": cases, "entry": f"claw_{family}_entry"},
        "evidence": {"level": "none"}, "integration": {"level": "source-only"}, "limits": limits,
        "notes": "Drafted by tools/claw/draft_spec.py from the disassembly." + (f" Platform code recovered because: {library_reason}" if library_reason else ""),
    }
    target = ROOT / spec_path
    if target.exists():
        return {"command": "draft", "family": family, "status": "exists", "specification": spec_path, "needs_review": []}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(spec, indent=2) + "\n")
    skeleton.generate(target)
    lint = speclint.lint(target)
    built = packet.build(target)
    review += [f"lint: {error}" for error in lint["errors"]]
    return {"command": "draft", "family": family, "status": "drafted", "specification": spec_path,
            "owned": [(o["address"], o["convention"], o["argc"], o["returns"]) for o in owned],
            "fixtures": sorted(callees), "needs_review": review, "reachable_imports": advice,
            "lint_warnings": lint["warnings"],
            "packet": built["packet"]}


def main(argv):
    parser = argparse.ArgumentParser(prog="claw draft")
    parser.add_argument("--id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--seeds", nargs="+", required=True)
    parser.add_argument("--pilot", action="store_true", help="write under work/pilot/ (a throwaway measurement run)")
    parser.add_argument("--library-reason", help="required to recover C runtime or MFC code: why native code will not do")
    parser.add_argument("--object-logic", action="store_true",
                        help="the seeds are registered object-logic callbacks: cdecl, one argument, result unused")
    parser.add_argument("--source-context", action="store_true", help="explicit ambient source state for ordinary entries")
    parser.add_argument("--source-preserve-mask", type=lambda n: int(n, 0))
    parser.add_argument("--compiler-context", action="store_true", help="explicit register/frame entry; never infer cdecl")
    parser.add_argument("--context-input-mask", type=lambda s: int(s, 0))
    parser.add_argument("--context-output-mask", type=lambda s: int(s, 0))
    options = parser.parse_args(argv)
    print(json.dumps(draft(options.id, options.title, [int(s, 16) for s in options.seeds], options.pilot,
                           options.object_logic, options.compiler_context, options.context_input_mask, options.context_output_mask,
                           options.source_context, options.source_preserve_mask, options.library_reason)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
