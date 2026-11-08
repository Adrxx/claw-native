"""Builds the task packet for one canonical family: everything a worker needs, and nothing else.

The packet lives under ignored work/packets/<id>/ because it contains
decompiled and disassembled text from the original. It holds the decompile and
disassembly of every owned function, a table of everything those functions
call, and the hashes of the files the worker must not change. Prints one JSON line.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

from . import index
from .paths import ROOT, WORK
from Tests.clawparity import build_inputs

ROLES = {
    # role: (files the worker edits, files whose hash must not change)
    "translator": ("module", ("spec", "cases")),
    "case-author": ("cases", ("spec", "module")),
}


def _files(spec, spec_path):
    module = build_inputs.sources(spec, require_exists=False)[0]
    return {"spec": str(Path(spec_path).resolve().relative_to(ROOT)), "module": module, "cases": spec["oracle"]["cases"]}


def _sha(path):
    path = ROOT / path
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def build(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    functions = index.functions()
    owned = {int(o["address"], 16): o for o in spec["owned"]}
    declared = {int(a, 16): c for a, c in spec.get("callees", {}).items()}
    guest = spec.get('oracle', {}).get('guest_graph')
    body_assembly = {}
    if any('body_ranges' in o for o in owned.values()):
        from .owned_ranges import resolve_owned_ranges
        from Tests.clawparity.program import claw
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        ranges = resolve_owned_ranges(spec)
        program = claw()
        decoder = Cs(CS_ARCH_X86, CS_MODE_32)
        for address, declaration in owned.items():
            if 'body_ranges' not in declaration:
                continue
            rows = []
            for low, high in ranges[address]:
                section = next(s for s in program.sections if s.address <= low < high <= s.address + len(s.data))
                raw = section.data[low-section.address:high-section.address]
                rows.extend(f'{i.address:08x}: {i.bytes.hex()}  {i.mnemonic} {i.op_str}'.rstrip()
                            for i in decoder.disasm(raw, low))
            body_assembly[address] = rows
    packet = WORK / "packets" / spec["id"]
    packet.mkdir(parents=True, exist_ok=True)
    lines = [f"# Packet: {spec['id']}", "", spec["title"], "", "## Owned functions", "",
             "| Address | Name | Convention | Stack arguments | Returns | Bytes | Decompile reliable |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    callee_rows = {}
    for address, declared_function in owned.items():
        function = functions.get(address, {})
        reliable = function.get("decompile_ok", False) and not function.get("unaff_count") and not function.get("jumptable_warning")
        size = sum(int(r['end'],16)-int(r['start'],16) for r in declared_function['body_ranges']) if 'body_ranges' in declared_function else function.get('size','?')
        lines.append(f"| {address:#x} | {declared_function.get('name', '')} | {declared_function.get('convention')} | "
                     f"{declared_function.get('argc')} | {declared_function.get('returns', 'u32')} | {size} | "
                     f"{'yes' if reliable else 'NO, use the disassembly'} |")
        for kind, source in (("c", index.decompile_path(address)), ("asm", index.CORPUS / "asm" / f"{address:08x}.asm")):
            if source.exists():
                shutil.copyfile(source, packet / f"{address:08x}.{kind}")
        calls = index.call_targets(address)
        if address in body_assembly:
            (packet / f'{address:08x}.asm').write_text('\n'.join(body_assembly[address])+'\n')
            calls = {}
            for row in body_assembly[address]:
                match = index.CALL.search(row)
                if match:
                    target = int(match.group(1),16)
                    calls[target] = calls.get(target,0)+1
        for target, sites in calls.items():
            if target in owned:
                treatment = "owned by this family: call it directly in C++"
            elif declared.get(target, {}).get("kind") == "fixture":
                callee = declared[target]
                treatment = (f"fixture `{callee.get('fixture', 'scripted')}`: {callee['convention']}, {callee['argc']} "
                             f"stack arguments. Native code calls it through run.call or run.icall")
            elif declared.get(target, {}).get('convention') == 'compiler-context':
                treatment = "unchanged original special dependency; run.context_call with exact compiler_context masks"
            elif 'source_context' in declared.get(target, {}):
                treatment = "unchanged original ordinary dependency; run.source_call with explicit state, physical frame and real PC"
            elif target in functions:
                treatment = "runs as original code on both sides: native code calls it with run.call"
            else:
                treatment = "UNDECLARED: report this, do not guess"
            row = callee_rows.setdefault(target, {"sites": 0, "treatment": treatment})
            row["sites"] += sites
    if guest:
        lines += ['', '## Guest source graph', '',
                  'Own the complete declared body, including the attached catch. The assembly includes every owned byte; the corpus decompile may omit the catch.',
                  'Use CLAW_GUEST_SOURCE_MODULE_ENTRY and CLAW_GUEST_FUNCLET_ENTRY. The catch is entered only by genuine original dispatch, never by a separately seeded case.',
                  'Cases require full NativeSourceContext and a genuine original caller continuation. Use expect=return or expect=unhandled; halt is only a physical service stop.',
                  'RaiseException and RtlUnwind are driver-owned nonlocal services. Never override them or replace internal functions with fixtures.',
                  'Only declared original factory addresses are permitted. Immutable original code and EH metadata are enforced.',
                  'Normal outcomes compare the full returned state; unhandled outcomes compare actual terminal state without fabricating a root return.']
    elif any('source_context' in o for o in owned.values()):
        lines += ["", "## Ordinary source context", "",
                  "Calling convention stays ordinary. Each source_context entry requires exact input/output/preserve masks.",
                  "Use CLAW_SOURCE_MODULE_ENTRY with a ClawSourceContract and run.source() for explicit CPU state.",
                  "Model physical prologue/epilogue frames; restore entry ESP before the wrapper's conventional RET.",
                  "Case.source_context and source_return_pc resolve after setup. Return PC must be genuine executable code.",
                  "Use run.source_call for ordinary dependencies with exact source frames/real PCs; compiler helpers use context_call.",
                  "Compiler dependencies are kind whole and execute original code. Never add internal fixtures.",
                  "All bounded stack bytes and declared register/preservation witnesses are compared, including real return PCs.",
                  "expect=halt compares only a genuine physical-service stop prefix: full CPU snapshot, full stack and effects, never EH success."]
    if any(o.get("convention") == "compiler-context" for o in owned.values()):
        lines += ["", "## Compiler-context contract", "",
                  "These are special register/frame entries. Never call or declare them as cdecl0.",
                  "Use CLAW_COMPILER_MODULE_ENTRY with void body(Run &, uint32_t, ClawCompilerContext &).",
                  "Its owned(uint32_t function) predicate returns bool: true for an owned address, false otherwise.",
                  "Do not return argument counts: returning 0 for an owned special entry rejects it.",
                  "Case(..., compiler_context=lambda tokens: tokens[\"context\"]) resolves the context from setup.",
                  "Create NativeCompilerContext from clawparity.env, fill its size=72/version=1, exact owned masks,",
                  "selected registers, genuine continuation and zero reserved words. setup(env) supplies complete",
                  "stack bytes via env.put; the runner freezes setup and clones context independently per side.",
                  "No receiver, arguments, compare_eax override or halt expectation is permitted.",
                  "The runner compares all selected outputs, immutable headers, unselected preservation, and all",
                  "bounded guest stack bytes. Original coverage executes unchanged instructions to continuation.",
                  "See Tests/clawparity/README.md for masks, frame bounds and unsupported exception dispatch.", ""]
    lines += ["", "## Everything the owned functions call", "", "| Target | Name | Call sites | How it is handled |",
              "| --- | --- | --- | --- |"]
    for target in sorted(callee_rows):
        label = declared.get(target, {}).get("name") or index.name(target)
        lines.append(f"| {target:#x} | {label} | {callee_rows[target]['sites']} | {callee_rows[target]['treatment']} |")
    indirect = {a: index.indirect_call_sites(a) for a in owned}
    if any(indirect.values()):
        lines += ["", "## Indirect calls", "",
                  ("Guest cases use only declared original factory pointers; env.stub is forbidden. Native source calls preserve actual call frames and continuations." if guest else
                   "These call through a pointer read at run time (virtual methods, callbacks). Native code reads the pointer and calls it with run.call or run.vcall; test cases supply the pointer with env.stub."), ""]
        for address, sites in indirect.items():
            lines += [f"- {address:#x}: `{site.strip()}`" for site in sites]
    reference = packet / "callees"
    for target in sorted(set(callee_rows) | set(declared)):
        if target in functions and target not in owned:
            reference.mkdir(exist_ok=True)
            for kind, source in (("c", index.decompile_path(target)), ("asm", index.CORPUS / "asm" / f"{target:08x}.asm")):
                if source.exists():
                    shutil.copyfile(source, reference / f"{target:08x}.{kind}")
    files = _files(spec, spec_path)
    lines += ["", "## Files", "",
              f"- Decompile and disassembly of the functions the owned code calls, for reference only: "
              f"`work/packets/{spec['id']}/callees/`. They are not yours to implement.", f"- Specification (never edit): `{files['spec']}`", f"- Module: `{files['module']}`",
              f"- Cases: `{files['cases']}`",
              f"- Decompile and disassembly per owned function: `work/packets/{spec['id']}/<address>.c` and `.asm`",
              "- Worked example of a finished family: `Tests/clawparity/examples/surface_flip/`",
              "- Module helpers: `Sources/ClawRuntime.hpp`. Case helpers: `Tests/clawparity/cases.py`, `fixtures.py`, "
              "and the Env methods documented in `Tests/clawparity/README.md`", "", "## Commands", "",
              f"- `make oracle FAMILY={spec['id']}` runs the cases and prints one JSON line.",
              f"- `make guard FAMILY={spec['id']} ROLE=<role>` checks that protected files are unchanged.", ""]
    (packet / "PACKET.md").write_text("\n".join(lines))
    protected = {role: {name: {"path": files[name], "sha256": _sha(files[name])} for name in names}
                 for role, (_, names) in ROLES.items()}
    (packet / "protected.json").write_text(json.dumps(protected, indent=2) + "\n")
    return {"command": "packet", "family": spec["id"], "packet": str(packet.relative_to(ROOT)),
            "owned": len(owned), "callees": len(callee_rows),
            "undeclared": [f"{t:#x}" for t, r in callee_rows.items() if r["treatment"].startswith("UNDECLARED")],
            "status": "pass"}


def seal(spec_path, role):
    """A role records the file it owns as finished. Later roles are checked against this record."""
    spec = json.loads(Path(spec_path).read_text())
    owns = ROLES[role][0]
    path = _files(spec, spec_path)[owns]
    record_path = WORK / "packets" / spec["id"] / "seals.json"
    seals = json.loads(record_path.read_text()) if record_path.exists() else {}
    seals[owns] = {"path": path, "sha256": _sha(path), "role": role}
    record_path.write_text(json.dumps(seals, indent=2) + "\n")
    return {"command": "seal", "family": spec["id"], "role": role, "sealed": path, "status": "pass"}


def feedback(spec_path):
    """Write blind case-author feedback without native source or failure snippets."""
    spec = json.loads(Path(spec_path).read_text())
    directory = WORK / "gate" / spec["id"]
    report = json.loads((directory / "gate.json").read_text())
    checks = report.get("checks", {})
    result = {"family": spec["id"], "status": report["status"],
              "coverage": checks.get("coverage", {}),
              "invalid_original_cases": checks.get("invalid_cases", []),
              "mutation_score": checks.get("mutants", {}).get("score"),
              "survivors": [{key: mutant[key] for key in ("line", "operator")}
                            for mutant in checks.get("mutants", {}).get("survived", [])]}
    path = directory / "case-author-feedback.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    return {"command": "feedback", "family": spec["id"],
            "feedback": str(path.relative_to(ROOT)), "status": "pass"}


def guard(spec_path, role):
    """After a worker finishes: fail if it changed a file its role must not touch.

    The specification is compared with its state when the packet was built. The
    cases and the module are compared with the state their own role sealed, when
    a seal exists, or with the packet baseline before that role has run.
    """
    spec = json.loads(Path(spec_path).read_text())
    packet = WORK / "packets" / spec["id"]
    recorded = json.loads((packet / "protected.json").read_text())[role]
    seals = json.loads((packet / "seals.json").read_text()) if (packet / "seals.json").exists() else {}
    changed, unchecked = [], []
    for name, entry in recorded.items():
        expected = entry["sha256"] if name == "spec" else seals.get(name, {}).get("sha256", entry["sha256"])
        if expected is None:
            unchecked.append(entry["path"])
        elif _sha(entry["path"]) != expected:
            changed.append(entry["path"])
    return {"command": "guard", "family": spec["id"], "role": role, "changed_protected_files": changed,
            "not_yet_sealed": unchecked, "status": "pass" if not changed else "fail"}


def main(argv):
    if argv[0] == "guard":
        result = guard(argv[1], argv[2])
    elif argv[0] == "seal":
        result = seal(argv[1], argv[2])
    elif argv[0] == "feedback":
        result = feedback(argv[1])
    else:
        result = build(argv[0])
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
