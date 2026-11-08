"""Canonical comparison inputs, independent of retained source ownership."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sources(spec, *, root=ROOT, require_exists=True):
    """Ordered translation units; the first is the module replaced by mutants."""
    if "canonical_sources" not in spec:
        return [s for s in spec["sources"] if s.endswith(".cpp")]
    selected = spec["canonical_sources"]
    if spec.get("abi") != "canonical":
        raise ValueError("canonical_sources requires canonical ABI")
    if not isinstance(selected, list) or not selected:
        raise ValueError("canonical_sources must be a nonempty list")
    seen = set()
    for source in selected:
        if (not isinstance(source, str) or not source.endswith(".cpp") or
                source not in spec.get("sources", []) or source in seen):
            raise ValueError("canonical_sources must contain unique owned .cpp paths")
        path = Path(source)
        if (path.is_absolute() or path.as_posix() != source or ".." in path.parts or
                not (root / path).resolve().is_relative_to(root.resolve()) or
                (root / path).resolve() != root.resolve() / path):
            raise ValueError("canonical_sources paths must be local and unaliased")
        if require_exists and not (root / path).is_file():
            raise ValueError(f"canonical_sources input does not exist: {source}")
        seen.add(source)
    return list(selected)


def library(spec, flavor="O2", defines=(), *, module_source=None, guest_transfer=False):
    from . import build
    selected = sources(spec)
    if not selected:
        raise ValueError("canonical family has no .cpp build input")
    paths = [ROOT / s for s in selected]
    if module_source is not None:
        paths[0] = Path(module_source)
    # Headers remain owned inputs even when a portable translation unit is
    # excluded. Include them in cache identity without compiling them.
    dependencies = [ROOT / s for s in spec["sources"] if not s.endswith(".cpp")]
    context = json.dumps({"canonical_sources": spec.get("canonical_sources"),
                          "selected": selected}, sort_keys=True)
    return build.library(spec["id"], paths, flavor, defines,
                         guest_transfer=guest_transfer, dependencies=dependencies,
                         cache_context=context)


def fingerprint(spec, *, root=ROOT):
    """Bind admission to selection, owned inputs, cases and harness semantics."""
    from . import admission_inputs
    sources(spec, root=root)
    contract = {k: v for k, v in spec.items() if k not in ("evidence", "integration")}
    state = hashlib.sha256(b"claw-admission-inputs-v2\0")
    state.update(json.dumps(contract, sort_keys=True).encode())
    state.update(json.dumps(admission_inputs.corpus_input(spec, root=root), sort_keys=True).encode())
    harness = admission_inputs.paths(spec)
    inputs = set(spec["sources"]) | harness
    inputs.update(admission_inputs.case_inputs(spec, root=root, harness=harness))
    inputs.update(str(p.relative_to(root)) for p in (root / "Sources").glob("ClawRuntime.h*"))
    # Symbols are loaded by every runner and are visible to family fixtures.
    symbols = root / "Tests/symbols.json"
    state.update(b"symbols-present" if symbols.exists() else b"symbols-absent")
    if symbols.exists():
        inputs.add("Tests/symbols.json")
    for name in sorted(inputs):
        state.update(name.encode())
        state.update(b"\0")
        state.update(hashlib.sha256((root / name).read_bytes()).digest())
    return state.hexdigest()


def admission_errors(spec, *, root=ROOT):
    """Every admitted family needs a matching fingerprint, including old defaults."""
    gate = spec.get("evidence", {}).get("gate") or {}
    if spec.get("evidence", {}).get("level") != "admitted":
        return []
    try:
        if gate.get("build_inputs_sha256") == fingerprint(spec, root=root):
            return []
    except (ValueError, OSError, KeyError) as error:
        return [f"canonical build admission inputs invalid: {error}"]
    return ["canonical build admission is stale; rerun the admission gate"]
