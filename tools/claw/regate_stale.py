"""Re-run the admission gate for every family whose recorded build admission is stale.

    python -m tools.claw.regate_stale [--jobs N] [--dry-run]

An admission fingerprints its sources, cases and selected harness paths. Only affected
admissions become stale. The dispatcher runs this after each exclusive (harness)
task. Reports the stale count before starting; the last JSON line fails if any re-gate is not admitted.
"""
import concurrent.futures
import json
import os
import subprocess
import sys

from .paths import FAMILIES, ROOT, WORK


def stale_families(*, root=ROOT):
    sys.path.insert(0, str(ROOT))
    from Tests.clawparity import build_inputs
    stale = []
    for path in sorted((root / "Tests/families").glob("*.json")):
        spec = json.loads(path.read_text())
        if "id" in spec and build_inputs.admission_errors(spec, root=root):
            stale.append(spec["id"])
    return stale


def regate(family):
    log = WORK / "regate" / f"{family}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as out:
        subprocess.run(["nice", "-n", "10", "make", "gate", f"FAMILY={family}", "ARGS=--record --jobs 1"],
                       cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, env={**os.environ, "CLAW_GATE_JOBS": "1"})
    try:
        return family, json.loads(log.read_text().strip().splitlines()[-1]).get("status", "error")
    except (IndexError, ValueError):
        return family, "error"


def main(argv):
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 4
    stale = stale_families()
    if "--dry-run" in argv or not stale:
        print(json.dumps({"command": "regate-stale", "stale_count": len(stale),
                          "stale": stale, "status": "pass"}), flush=True)
        return 0
    print(json.dumps({"command": "regate-stale", "stale_count": len(stale),
                      "status": "starting"}), flush=True)
    # Families borrowed through shared_sources must be fresh before their borrowers are gated.
    borrowed = set()
    for path in FAMILIES.glob("*.json"):
        for entry in json.loads(path.read_text()).get("shared_sources", []) or []:
            owner = entry.get("family") if isinstance(entry, dict) else None
            if owner:
                borrowed.add(owner)
    results = {}
    for phase in ([f for f in stale if f in borrowed], [f for f in stale if f not in borrowed]):
        with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
            results.update(dict(pool.map(regate, phase)))
    failed = {k: v for k, v in results.items() if v != "admitted"}
    print(json.dumps({"command": "regate-stale", "stale_count": len(stale),
                      "regated": len(results), "failed": failed,
                      "status": "fail" if failed else "pass"}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
