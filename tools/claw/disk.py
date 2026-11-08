"""Size of work/ against its budget. Fails when over. One JSON line."""
import json
import subprocess
import sys

from .paths import WORK

BUDGET_GB = 60


def main(argv):
    rows = []
    for entry in WORK.iterdir():
        done = subprocess.run(["du", "-sk", str(entry)], capture_output=True, text=True)
        if done.stdout:
            rows.append((int(done.stdout.split()[0]), entry.name))
    rows.sort(reverse=True)
    for kilobytes, name in rows[:10]:
        print(f"{kilobytes / 1048576:6.1f} GB  work/{name}")
    total = sum(k for k, _ in rows) / 1048576
    free = subprocess.run(["df", "-k", str(WORK)], capture_output=True, text=True).stdout.split("\n")[1].split()
    print(json.dumps({"command": "disk", "work_gb": round(total, 1), "budget_gb": BUDGET_GB,
                      "disk_free_gb": round(int(free[3]) / 1048576), "status": "pass" if total <= BUDGET_GB else "fail"}))
    return 0 if total <= BUDGET_GB else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
