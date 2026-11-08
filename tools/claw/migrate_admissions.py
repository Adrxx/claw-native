"""One-time, fail-closed admission migration from the owner-named fresh commit.

    python -m tools.claw.migrate_admissions [--record]

This never treats a passing comparison or an AST-equivalent file as byte identity.
Unproven families keep their existing evidence and go through the normal gate.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from .paths import ROOT, WORK
from Tests.clawparity import admission_inputs, build_inputs

BASELINE = "dad242f"  # last commit with every admission fresh (2026-10-29)
# Owner decision 2026-10-29 (readability option 2): these exact harness versions differ from the baseline only by
# one-line opt-in dispatch to named_layout_mutants for specs with "mutation": "named-layout"; the coordinator reviewed
# both diffs: other families take the unchanged path. Any further edit changes the hash and fails closed again.
REVIEWED_HARNESS = {
    "Tests/clawparity/admission_inputs.py": "b03796c852a99fceca34f7058325f0248291ddfd6fa0666dacdcb7187775609c",
    "Tests/clawparity/mutants.py": "c2ad35db5e0216978e8cccfac2f81fcc7553088950bad9fc9e6e2b4b5685f71b",
}


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


class Baseline:
    def __init__(self, root=ROOT):
        self.root = root
        self.commit = subprocess.check_output(
            ["git", "rev-parse", BASELINE + "^{commit}"], cwd=root, text=True).strip()
        self.cache = {}

    def read(self, name):
        if name not in self.cache:
            result = subprocess.run(["git", "show", f"{self.commit}:{name}"], cwd=self.root,
                                    capture_output=True)
            self.cache[name] = result.stdout if result.returncode == 0 else None
        return self.cache[name]


def contract(spec):
    return {k: v for k, v in spec.items() if k not in ("evidence", "integration")}


def recorded_inputs(spec, prior, baseline, *, root):
    """Bind current family bytes to its last gate, not just similarly named files."""
    gate = spec.get("evidence", {}).get("gate") or {}
    if gate.get("status") != "admitted":
        return {"verified": False, "basis": "last gate is not an admitted result"}
    if (prior.get("evidence", {}).get("level") == "admitted" and
            gate == prior.get("evidence", {}).get("gate")):
        return {"verified": True, "basis": "owner-named fresh commit and identical gate record"}
    # Reproduce the pre-migration algorithm, not the new fingerprint. Later
    # re-gates used the profile-aware runner; older gates used the commit's
    # runner. Matching the recorded digest proves the complete input tuple.
    if not gate.get("build_inputs_sha256") or "shared_sources" in spec:
        return {"verified": False, "basis": "no reproducible last-admission input digest"}
    harness = {"Tests/clawparity/" + name for name in
               ("build_inputs.py", "build.py", "runner.py", "mutants.py", "gate.py")}
    names = set(spec["sources"]) | {spec["oracle"]["cases"]} | harness
    names.update(str(p.relative_to(root)) for p in (root / "Sources").glob("ClawRuntime.h*"))
    for current_runner in (False, True):
        state = hashlib.sha256(json.dumps(contract(spec), sort_keys=True).encode())
        for name in sorted(names):
            data = ((root / name).read_bytes() if name not in harness or
                    (current_runner and name == "Tests/clawparity/runner.py") else baseline.read(name))
            if data is None:
                break
            state.update(name.encode())
            state.update(data)
        else:
            if state.hexdigest() == gate["build_inputs_sha256"]:
                return {"verified": True, "basis": "reproduced last-admission input digest",
                        "sha256": state.hexdigest(), "runner": "current" if current_runner else "baseline"}
    return {"verified": False, "basis": "last-admission input digest does not match"}


def compare_files(names, baseline, *, root):
    result = {}
    for name in sorted(names):
        path = root / name
        current = path.read_bytes() if path.is_file() else None
        reference = baseline.read(name)
        result[name] = {"current_sha256": digest(current), "baseline_sha256": digest(reference),
                        "identical": current is not None and reference is not None and current == reference}
    return result


def proof(spec, baseline, *, root=ROOT):
    """Prove both conditions; absent old source hashes never imply unchanged."""
    reasons = []
    path = f"Tests/families/{spec['id']}.json"
    raw = baseline.read(path)
    prior = json.loads(raw) if raw is not None else {}
    same_contract = bool(prior) and contract(spec) == contract(prior)
    record = recorded_inputs(spec, prior, baseline, root=root)
    if spec.get("program", "claw-v1.0") != "claw-v1.0":
        reasons.append("migration authority covers only claw-v1.0")
    if not same_contract:
        reasons.append("family contract differs from the owner-named fresh baseline")
    if not record["verified"]:
        reasons.append("last admission input bytes are not proven: " + record["basis"])
    harness = admission_inputs.paths(spec)
    named = set(spec["sources"]) | admission_inputs.case_inputs(spec, root=root, harness=harness)
    named.update(str(p.relative_to(root)) for p in (root / "Sources").glob("ClawRuntime.h*"))
    named.add("Tests/clawparity/fixtures.py")
    if (root / "Tests/symbols.json").exists() or baseline.read("Tests/symbols.json") is not None:
        named.add("Tests/symbols.json")
    for entry in spec.get("shared_sources", []):
        named.update(entry["sources"])
    inputs = compare_files(named, baseline, root=root)
    modules = compare_files(harness, baseline, root=root)
    if any(not row["identical"] for row in inputs.values()):
        reasons.append("named source, case, fixture or runtime input differs from baseline")
    for name, row in modules.items():
        row["owner_reviewed"] = not row["identical"] and row["current_sha256"] == REVIEWED_HARNESS.get(name)
    if any(not row["identical"] and not row["owner_reviewed"] for row in modules.values()):
        reasons.append("a selected harness module is absent from or not byte-identical to baseline "
                       "and is not an owner-reviewed version")
    return {"family": spec["id"], "eligible": not reasons, "reasons": reasons,
            "contract_identical": same_contract, "last_record": record,
            "previous_gate": spec.get("evidence", {}).get("gate"),
            "inputs": inputs, "harness": modules}


def migrate(baseline, *, root=ROOT, record=False):
    results = {}
    paths = list((root / "Tests/families").glob("*.json"))
    # Owners first; the normal shared-input validator still requires freshness.
    paths.sort(key=lambda p: (bool(json.loads(p.read_text()).get("shared_sources")), p.name))
    for path in paths:
        before = path.read_bytes()
        spec = json.loads(before)
        if spec.get("evidence", {}).get("level") != "admitted":
            continue
        try:
            result = proof(spec, baseline, root=root)
            if result["eligible"]:
                result["new_fingerprint"] = build_inputs.fingerprint(spec, root=root)
        except (OSError, ValueError, KeyError) as error:
            result = {"family": spec["id"], "eligible": False, "reasons": [str(error)]}
        result["migrated"] = False
        if result["eligible"] and record:
            # Re-read immediately before the only mutation in this operation.
            if path.read_bytes() != before:
                result["eligible"] = False
                result["reasons"].append("family changed during migration proof")
            elif proof(spec, baseline, root=root) != {k: v for k, v in result.items()
                                                      if k not in ("new_fingerprint", "migrated")}:
                result["eligible"] = False
                result["reasons"].append("inputs changed during migration proof")
            elif build_inputs.fingerprint(spec, root=root) != result["new_fingerprint"]:
                result["eligible"] = False
                result["reasons"].append("fingerprint changed during migration proof")
            else:
                spec["evidence"].setdefault("gate", {})["build_inputs_sha256"] = result["new_fingerprint"]
                path.write_text(json.dumps(spec, indent=2) + "\n")
                result["migrated"] = True
        results[spec["id"]] = result
    return {"command": "migrate-admissions", "status": "pass", "baseline": baseline.commit,
            "record": record, "families": results,
            "migrated": sum(r["migrated"] for r in results.values()),
            "eligible": sum(r["eligible"] for r in results.values()),
            "requires_gate": [name for name, r in results.items() if not r["eligible"]]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    result = migrate(Baseline(), record=args.record)
    output = WORK / "regate/migration.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "families"}))


if __name__ == "__main__":
    main()
