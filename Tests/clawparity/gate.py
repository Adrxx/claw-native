"""The admission gate for a canonical family. Prints one line of JSON.

    python -m clawparity.gate Tests/families/<id>.json [--seed N] [--record]

The gate decides whether a family's evidence is strong enough to call it
admitted. It runs with inputs the worker did not choose and checks the things
a passing run can hide. The rules are listed in docs/ADMISSION.md.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import build, build_inputs, mutants, runner

ROOT = Path(__file__).resolve().parents[2]
MUTATION_THRESHOLD = 0.9


def _sanitized(spec_path, seed):
    prefix, environment = build.sanitized_python()
    if prefix is None:
        return {"status": "unavailable", "detail": "no sanitizer runtime on this machine"}
    command = prefix + ["-m", "clawparity.runner", str(spec_path), "--seed", str(seed), "--flavor", "sanitize"]
    done = subprocess.run(command, cwd=ROOT / "Tests", capture_output=True, text=True, env=environment, timeout=1800)
    try:
        summary = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        summary = {"status": "error"}
    result = {"status": summary.get("status") if done.returncode == 0 else "error",
              "cases": summary.get("cases"), "stderr_bytes": len(done.stderr),
              "stderr_tail": done.stderr[-600:], "returncode": done.returncode}
    if 'guest_graph' in summary:
        result['guest_graph'] = summary['guest_graph']
    return result


def _ignored(paths):
    """Inputs that git ignores. Evidence must not depend on anything outside the tracked tree."""
    done = subprocess.run(["git", "check-ignore", *paths], cwd=ROOT, capture_output=True, text=True)
    return done.stdout.split()


def run(spec_path, seed=None, mutant_limit=48, mutant_jobs=4):
    started = time.monotonic()
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    # A seed nobody could have tuned the cases for. Recorded so the run can be repeated.
    seed = int.from_bytes(os.urandom(4), "little") if seed is None else seed
    reasons, checks = [], {}
    try:
        checks["build_inputs_sha256"] = build_inputs.fingerprint(spec)
    except (ValueError, OSError, KeyError) as error:
        checks["build_inputs_sha256"] = None
        reasons.append(f"invalid canonical build inputs: {error}")

    valid = runner.run(spec_path, seed=seed, original_only=True)
    checks["cases_valid_on_original"] = {k: valid.get(k) for k in ("status", "cases", "failed")}
    if valid["status"] != "pass":
        checks["invalid_cases"] = valid.get("failures", [])[:3]
        reasons.append("some cases are invalid on the original alone (objects too small, or a missing stand-in)")

    worker = runner.run(spec_path, seed=0, flavor="O2")
    checks["worker_seed"] = {k: worker.get(k) for k in ("status", "cases", "failed", "detail")}
    if worker["status"] != "pass":
        reasons.append("cases fail with the worker's own seed")

    unseen = runner.run(spec_path, seed=seed, flavor="O2", trace=True)
    checks["gate_seed"] = {k: unseen.get(k) for k in ("status", "cases", "failed", "outside_calls_compared", "detail")}
    checks["first_failures"] = unseen.get("failures", [])[:3] or worker.get("failures", [])[:3]
    if unseen["status"] != "pass":
        reasons.append("cases fail with a seed the worker never saw")

    unoptimized = runner.run(spec_path, seed=seed, flavor="O0")
    checks["unoptimized_build"] = {k: unoptimized.get(k) for k in ("status", "cases", "failed")}
    if unoptimized["status"] != "pass":
        reasons.append("cases fail when the module is built without optimization")

    coverage = unseen.get("coverage", {})
    checks["coverage"] = coverage
    for address, entry in coverage.items():
        if not entry.get("direct_calls"):
            reasons.append(f"owned function {address} is never called directly by a case")
        if entry.get("bytes") is None:
            reasons.append(f"owned function {address} has no known byte range, so coverage cannot be measured")
        elif entry["executed"] < entry["bytes"]:
            reasons.append(f"owned function {address}: {entry['bytes'] - entry['executed']} of {entry['bytes']} bytes "
                           f"never executed and not exempted")
    if not coverage:
        reasons.append("no coverage was measured")

    sanitized = _sanitized(spec_path, seed)
    checks["sanitizer"] = sanitized
    if sanitized["status"] != "pass" or sanitized.get("stderr_bytes"):
        reasons.append("sanitizer run did not pass cleanly")

    if 'guest_graph' in spec.get('oracle', {}):
        from .guest_admission import evidence_errors
        checks['guest_graph'] = {}
        for label, result, native in (('original', valid, False), ('worker', worker, True),
                ('fresh_seed', unseen, True), ('O0', unoptimized, True), ('sanitize', sanitized, True)):
            evidence = result.get('guest_graph')
            checks['guest_graph'][label] = evidence
            reasons.extend(f'{label}: {error}' for error in evidence_errors(evidence, require_native=native))

    if worker["status"] == "pass":
        mutation = mutants.run(spec_path, seed=seed, limit=mutant_limit, jobs=mutant_jobs)
        checks["mutants"] = {k: mutation[k] for k in (
            "candidates", "tried", "killed", "invalid", "score", "survived", "equivalent",
            "source_sha256", "review_errors", "status")}
        if mutation["review_errors"]:
            reasons.append("equivalent-mutant reviews are invalid: " + "; ".join(mutation["review_errors"]))
        if mutation["score"] is None or mutation["score"] < MUTATION_THRESHOLD:
            reasons.append(f"mutation score {mutation['score']} is below {MUTATION_THRESHOLD}")
    else:
        checks["mutants"] = {"skipped": "cases do not pass"}

    inputs = list(spec["sources"]) + [spec["oracle"]["cases"], str(spec_path.relative_to(ROOT))]
    pilot = all(path.startswith("work/pilot/") for path in inputs)
    checks["ignored_inputs"] = [] if pilot else _ignored(inputs)
    checks["pilot"] = pilot  # a throwaway measurement run: lives under work/pilot and is never recorded
    if checks["ignored_inputs"]:
        reasons.append("the specification, cases or module live in a directory git ignores")
    try:
        current = json.loads(spec_path.read_text())
        if build_inputs.fingerprint(current) != checks["build_inputs_sha256"]:
            reasons.append("canonical build inputs changed during the gate")
    except (ValueError, OSError, KeyError) as error:
        reasons.append(f"canonical build inputs became invalid: {error}")

    return {"command": "gate", "family": spec["id"], "status": "admitted" if not reasons else "rejected",
            "seed": seed, "reasons": reasons, "checks": checks, "seconds": round(time.monotonic() - started, 1)}


def main(argv):
    parser = argparse.ArgumentParser(prog="clawparity.gate")
    parser.add_argument("spec")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--mutants", type=int, default=48)
    parser.add_argument("--jobs", type=int, default=int(os.environ.get("CLAW_GATE_JOBS", "4")))
    options = parser.parse_args(argv)
    if options.jobs < 1:
        parser.error("--jobs must be positive")
    result = run(options.spec, options.seed, options.mutants, options.jobs)
    output = ROOT / "work" / "gate" / result["family"]
    output.mkdir(parents=True, exist_ok=True)
    (output / "gate.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["status"] == "admitted" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
