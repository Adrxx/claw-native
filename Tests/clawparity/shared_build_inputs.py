"""Opt-in references to sources owned by an admitted canonical family."""
import hashlib
import json
import re
from pathlib import Path

from . import build_inputs as owned_inputs

ROOT = owned_inputs.ROOT


def shared(spec, *, root=ROOT):
    """Resolve explicit, one-level references without transferring ownership."""
    if "shared_sources" not in spec:
        return [], {}
    references = spec["shared_sources"]
    if spec.get("abi") != "canonical" or not isinstance(references, list) or not references:
        raise ValueError("shared_sources requires canonical ABI and a nonempty list")
    paths, owners = [], {}
    seen = set(spec.get("sources", []))
    for reference in references:
        if not isinstance(reference, dict) or set(reference) != {"family", "sources"}:
            raise ValueError("shared_sources requires family and sources")
        family, selected = reference["family"], reference["sources"]
        if (not isinstance(family, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", family)
                or family == spec.get("id") or family in owners):
            raise ValueError("shared_sources requires unique other family owners")
        if not isinstance(selected, list) or not selected:
            raise ValueError("shared_sources owner requires a nonempty source list")
        owner_path = root / "Tests/families" / (family + ".json")
        if not owner_path.is_file() or owner_path.resolve() != root.resolve() / owner_path.relative_to(root):
            raise ValueError(f"shared_sources owner missing or aliased: {family}")
        owner = json.loads(owner_path.read_text())
        if (owner.get("id") != family or owner.get("abi") != "canonical" or
                owner.get("evidence", {}).get("level") != "admitted"):
            raise ValueError(f"shared_sources owner must be admitted canonical: {family}")
        # Deliberately bounded: no recursive linking, cycles or implicit inputs.
        if "shared_sources" in owner:
            raise ValueError("shared_sources owners cannot themselves borrow sources")
        errors = owned_inputs.admission_errors(owner, root=root)
        if errors:
            raise ValueError(f"shared_sources owner {family}: {'; '.join(errors)}")
        compiled = owned_inputs.sources(owner, root=root)
        for source in selected:
            if (not isinstance(source, str) or source in seen or
                    source not in owner.get("sources", []) or
                    Path(source).suffix not in (".cpp", ".h", ".hpp")):
                raise ValueError("shared_sources must be unique paths owned by the named family")
            path = Path(source)
            if (path.is_absolute() or path.as_posix() != source or ".." in path.parts or
                    (root / path).resolve() != root.resolve() / path or not (root / path).is_file()):
                raise ValueError("shared_sources paths must exist, be local and unaliased")
            if source.endswith(".cpp") and source not in compiled:
                raise ValueError("shared_sources must select the owner's canonical translation units")
            seen.add(source)
            paths.append(source)
        owners[family] = owner
    return paths, owners


def sources(spec, *, root=ROOT, require_exists=True):
    # A spec that owns no sources selects no translation units; building or
    # borrowing still requires an owned primary module.
    selected = ([] if "sources" not in spec and "canonical_sources" not in spec else
                owned_inputs.sources(spec, root=root, require_exists=require_exists))
    borrowed, _ = shared(spec, root=root)
    if borrowed and not selected:
        raise ValueError("shared_sources requires an owned primary module")
    return selected + [s for s in borrowed if s.endswith(".cpp")]


def library(spec, flavor="O2", defines=(), *, module_source=None, guest_transfer=False):
    if "shared_sources" not in spec:
        return owned_inputs.library(spec, flavor, defines, module_source=module_source,
                                    guest_transfer=guest_transfer)
    from . import build
    selected = sources(spec)
    borrowed, owners = shared(spec)
    paths = [ROOT / s for s in selected]
    if module_source is not None:
        paths[0] = Path(module_source)
    headers = set(spec["sources"] + borrowed)
    for owner in owners.values():
        headers.update(owner["sources"])
    dependencies = [ROOT / s for s in sorted(headers) if not s.endswith(".cpp")]
    context = json.dumps({"canonical_sources": spec.get("canonical_sources"),
                          "shared_sources": spec["shared_sources"], "selected": selected}, sort_keys=True)
    return build.library(spec["id"], paths, flavor, defines, guest_transfer=guest_transfer,
                         dependencies=dependencies, cache_context=context)


def fingerprint(spec, *, root=ROOT):
    baseline = owned_inputs.fingerprint(spec, root=root)
    if "shared_sources" not in spec:
        return baseline
    sources(spec, root=root)
    borrowed, owners = shared(spec, root=root)
    state = hashlib.sha256(baseline.encode())
    for name in sorted(set(borrowed)):
        state.update(name.encode())
        state.update((root / name).read_bytes())
    for family, owner in sorted(owners.items()):
        state.update(family.encode())
        state.update(owned_inputs.fingerprint(owner, root=root).encode())
    return state.hexdigest()


def admission_errors(spec, *, root=ROOT):
    if spec.get("evidence", {}).get("level") != "admitted":
        return []
    if "shared_sources" not in spec:
        return owned_inputs.admission_errors(spec, root=root)
    try:
        current = fingerprint(spec, root=root)
    except (ValueError, OSError, KeyError) as error:
        return [f"canonical shared build admission inputs invalid: {error}"]
    if (spec.get("evidence", {}).get("level") == "admitted" and
            spec.get("evidence", {}).get("gate", {}).get("build_inputs_sha256") != current):
        return ["canonical shared build admission is stale; rerun the admission gate"]
    return []
