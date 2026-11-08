"""Reviewed gate dependencies, by program and opt-in execution path.

Keep profile implementations in separate modules. Do not slice source text or
learn dependencies from a successful run: either can miss an unexecuted failure
path. Shared dispatch and validation are always inputs, including this policy.
"""
import ast
from pathlib import Path

HARNESS = "Tests/clawparity/"
COMMON = (
    "__init__.py", "admission_inputs.py", "build_inputs.py", "shared_build_inputs.py",
    "build.py", "runner.py", "gate.py", "mutants.py", "mutation_review.py",
    "program.py", "abi.py", "cases.py", "env.py", "kernel.py", "fixtures.py",
    "hostlib.cpp", "guest_exception.py",  # Env imports PhysicalTransfer unconditionally.
)
PROFILES = {
    "claw-v1.0": (),  # loader and pinned identity live in shared program.py
    "claw-v1.3": ("program_v13.py", "profiles.py"),
    "synthetic": ("selftest/__init__.py", "selftest/synthetic.py"),
    "ordinary-source-synthetic": ("selftest/__init__.py", "selftest/source_context.py",
                                  "selftest/stack.py"),
    "compiler-family-synthetic": ("selftest/__init__.py", "selftest/compiler_family.py",),
}
GUEST = (
    "guest_contract.py", "guest_family.py", "guest_admission.py", "guest_adapter.py",
    "guest_reference.py", "guest_compare.py", "guest_policy.py",
)
RANGES = ("tools/claw/__init__.py", "tools/claw/owned_ranges.py",
          "tools/claw/index.py", "tools/claw/paths.py")


def uses_guest(spec):
    return ("guest_graph" in spec.get("oracle", {}) or
            any("attached_entries" in e for e in spec.get("owned", [])) or
            any(c.get("kind") == "guest-service" for c in spec.get("callees", {}).values()))


def paths(spec):
    """Modules whose code can affect this family's comparison or admission."""
    profile = spec.get("program", "claw-v1.0")
    if profile not in PROFILES:
        raise ValueError(f"no reviewed admission inputs for program {profile!r}")
    inputs = {HARNESS + name for name in COMMON + PROFILES[profile]}
    if spec.get("mutation") == "named-layout": inputs.update((HARNESS + "named_layout_mutants.py", "Sources/ClawRecoveredLayout.h", "Sources/ClawRecoveredNames.h"))
    guest = uses_guest(spec)
    if guest:
        inputs.update(HARNESS + name for name in GUEST)
        inputs.update(("Sources/ClawGuestTransfer.h", "Sources/ClawGuestTransfer.cpp"))
    if guest or any("body_ranges" in e for e in spec.get("owned", [])):
        inputs.update(RANGES)
    return inputs


def corpus_input(spec, *, root):
    """Only consumed range data; unrelated corpus functions do not stale a family."""
    if spec.get("program", "claw-v1.0") != "claw-v1.0":
        return None
    entries = spec.get("owned", [])
    guest = uses_guest(spec)
    if not guest and not any("interval_end" not in e for e in entries):
        return None
    import json
    path = root / "work/corpus/index.json"
    if not path.exists():
        return {"missing": True}
    functions = json.loads(path.read_text())["functions"]
    number = lambda n: int(n, 16) if isinstance(n, str) else n
    wanted = {number(e["address"]) for e in entries if "interval_end" not in e}
    result = {str(number(f["entry"])): f.get("ranges", []) for f in functions
              if guest or number(f["entry"]) in wanted}
    if any("body_ranges" in e for e in entries):
        # Whole-body verification also uses other functions as decode anchors.
        result["anchors"] = sorted({a for f in functions for a in
                                    (number(f["entry"]), *(number(r[0]) for r in f.get("ranges", [])))})
    return result


def case_inputs(spec, *, root, harness):
    """Include local Python helpers imported by cases, without importing cases.

    The reviewed harness paths above handle their own conditional dependencies.
    Imports made directly by cases still count, even if they opt into another
    profile's helpers. Third-party packages remain environment dependencies.
    """
    found, pending = set(), [spec["oracle"]["cases"]]

    def module_files(parts):
        # Both repository-root and Tests-root imports are used by the runner.
        for base in (Path(), Path("Tests")):
            module = base.joinpath(*parts)
            candidates = (module.with_suffix(".py"), module / "__init__.py")
            target = next((p for p in candidates if (root / p).is_file()), None)
            if target is not None:
                yield target.as_posix()
                for parent in target.parents:
                    init = parent / "__init__.py"
                    if (root / init).is_file():
                        yield init.as_posix()
                return

    while pending:
        name = pending.pop()
        if name in found or name in harness:
            continue
        found.add(name)
        try:
            tree = ast.parse((root / name).read_bytes(), filename=name)
        except SyntaxError as error:
            raise ValueError(f"invalid case input {name}: {error}") from error
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [entry.name.split(".") for entry in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = (node.module or "").split(".") if node.module else []
                if node.level:
                    package = list(Path(name).parent.parts)
                    prefix = package[:len(package) - node.level + 1] + prefix
                modules = [prefix] + [prefix + [entry.name] for entry in node.names if entry.name != "*"]
            else:
                continue
            for parts in modules:
                if parts:
                    pending.extend(module_files(parts))
    return found
