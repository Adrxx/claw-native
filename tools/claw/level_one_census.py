"""Reconcile the Level 1 census contract in tools/queue.json with current admissions, then run the check.

    python -m tools.claw.level_one_census

Batch coordinators must not edit the contract; the orchestrator runs this after each round of admissions.
"""
import json
import subprocess
import sys

from . import queue as task_queue
from .paths import PYTHON, ROOT

UNRESOLVED = ("owned-but-unadmitted", "partial", "unowned")


def main(argv):
    sys.path.insert(0, str(ROOT))
    from Tests.NativeLevelOne.check import census
    ownership = census(ROOT / "work" / "level-one-map" / "trace.json")
    unresolved = sum(1 for row in ownership["rows"] if row["classification"] in UNRESOLVED)
    with task_queue.locked():
        queue = task_queue.load()
        contract = queue["level_one_batch_contract"]
        contract["ownership_counts"] = ownership["counts"]
        contract["unresolved_functions"] = unresolved
        task_queue.save(queue)
    check = subprocess.run([str(PYTHON), "-m", "Tests.NativeLevelOne.check"], cwd=ROOT, capture_output=True, text=True)
    status = "pass" if check.returncode == 0 else "fail"
    print(json.dumps({"command": "level-one-census", "counts": ownership["counts"], "unresolved": unresolved,
                      "check": status, "detail": "" if status == "pass" else check.stderr.strip().splitlines()[-1:],
                      "status": status}))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
