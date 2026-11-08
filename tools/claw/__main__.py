"""The harness command line. Every command prints one line of JSON as its last line of output.

    python -m tools.claw <command> [family] [options]

Run `make help` for the list.
"""
import json
import subprocess
import sys
from pathlib import Path

from . import legacy
from .paths import FAMILIES, PYTHON, ROOT, TESTS, WORK


def find_spec(family):
    """A family id, or a path to its JSON file, to the path of its specification."""
    direct = Path(family)
    if direct.suffix == ".json" and direct.exists():
        return direct.resolve()
    candidates = [FAMILIES / f"{family}.json"]
    candidates += sorted((TESTS / "clawparity" / "examples").glob("*/family.json"))
    candidates += sorted((WORK / "pilot").glob("*/family.json"))
    for candidate in candidates:
        if candidate.exists() and json.loads(candidate.read_text()).get("id") == family:
            return candidate
    raise SystemExit(json.dumps({"status": "error", "detail": f"no family named {family!r}"}))


def _harness(module, spec, extra=()):
    """Run a clawparity module from the Tests directory and pass its JSON through."""
    done = subprocess.run([str(PYTHON), "-m", f"clawparity.{module}", str(spec), *extra], cwd=TESTS)
    return done.returncode


def oracle(arguments):
    spec_path = find_spec(arguments[0])
    spec = json.loads(spec_path.read_text())
    if spec["oracle"]["kind"] == "clawparity":
        return _harness("runner", spec_path, arguments[1:])
    if spec["oracle"]["kind"] == "none":
        print(json.dumps({"command": "oracle", "family": spec["id"], "status": "no-oracle"}))
        return 1
    doc_lines = legacy._doc_lines(ROOT)
    records = [legacy.run_one(ROOT / command["script"], ROOT, doc_lines, 1800) for command in spec["oracle"]["commands"]]
    status = "pass" if all(r["status"] == "pass" for r in records) else "fail"
    print(json.dumps({"command": "oracle", "family": spec["id"], "kind": "legacy", "status": status,
                      "scripts": [{k: r.get(k) for k in ("script", "status", "seconds")} for r in records],
                      "first_failure": next((r.get("stderr", "")[-700:] for r in records if r["status"] != "pass"), None)}))
    return 0 if status == "pass" else 1


def gate(arguments):
    """Run the admission gate. With --record, store the result in the family's manifest."""
    record = "--record" in arguments
    arguments = [a for a in arguments if a != "--record"]
    spec_path = find_spec(arguments[0])
    spec = json.loads(spec_path.read_text())
    if spec["oracle"]["kind"] != "clawparity":
        from . import legacy_gate
        return legacy_gate.main([spec["id"], *arguments[1:], *(["--record"] if record else [])])
    done = subprocess.run([str(PYTHON), "-m", "clawparity.gate", str(spec_path), *arguments[1:]], cwd=TESTS,
                          capture_output=True, text=True)
    sys.stderr.write(done.stderr)
    sys.stdout.write(done.stdout)
    if record and spec_path.parent == FAMILIES:
        from . import manifest
        result = json.loads(done.stdout.strip().splitlines()[-1])
        checks = result["checks"]
        mutants = checks.get("mutants", {})
        spec["evidence"]["gate"] = {
            "kind": "admission", "status": result["status"], "seed": result["seed"],
            "cases": checks.get("gate_seed", {}).get("cases"), "mutants_killed": mutants.get("killed"),
            "mutants_tried": mutants.get("tried"), "mutants_equivalent": len(mutants.get("equivalent", [])),
            "mutation_score": mutants.get("score"), "reasons": result["reasons"],
            "build_inputs_sha256": checks.get("build_inputs_sha256")}
        passes = checks.get("worker_seed", {}).get("status") == "pass"
        spec["evidence"]["level"] = "admitted" if result["status"] == "admitted" else "provisional" if passes else "none"
        manifest.save(spec)
    return done.returncode


def _tool(name):
    def run(arguments):
        import importlib
        return importlib.import_module(f"tools.claw.{name}").main(arguments)
    return run


def _family_tool(name, prefix=()):
    def run(arguments):
        import importlib
        return importlib.import_module(f"tools.claw.{name}").main([*prefix, str(find_spec(arguments[0])), *arguments[1:]])
    return run


COMMANDS = {
    "oracle": oracle,
    "gate": gate,
    "cases-check": lambda arguments: _harness("runner", find_spec(arguments[0]), ["--original-only", *arguments[1:]]),
    "mutants": lambda arguments: _harness("mutants", find_spec(arguments[0]), arguments[1:]),
    "lint": _family_tool("speclint"),
    "skeleton": _family_tool("skeleton"),
    "packet": _family_tool("packet"),
    "feedback": _family_tool("packet", prefix=("feedback",)),
    "guard": _family_tool("packet", prefix=("guard",)),
    "seal": _family_tool("packet", prefix=("seal",)),
    "baseline": _tool("legacy"),
    "manifests": _tool("manifest"),
    "sync": _tool("sync"),
    "status": _tool("status"),
    "regate": _tool("legacy_gate"),
    "draft": _tool("draft_spec"),
    "backlog": _tool("backlog"),
    "queue": _tool("queue"),
    "usage": _tool("codex_usage"),
    "lint-docs": _tool("lint_docs"),
    "disk": _tool("disk"),
    "platform-boundary": _tool("platform_boundary"),
    "milestone": _tool("milestone"),
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(json.dumps({"status": "error", "detail": f"commands: {', '.join(sorted(COMMANDS))}"}))
        return 2
    return COMMANDS[argv[0]](argv[1:]) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
