"""Check that the app regression runner cannot hide filtered check failures."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    runner = (ROOT / "work/new-game/regressions.sh").read_text()
    scenarios = {
        "pipeline_failure": ("false | tail -1", False),
        "earlier_traceback": (
            "print 'Traceback (most recent call last):'; print AssertionError; true", False),
        "reported_failure": ("print '{\"status\":\"fail\"}'", False),
        "success": ("print '{\"status\":\"pass\"}'", True),
    }
    results = {}
    for name, (body, expected_pass) in scenarios.items():
        stub = (f"PY={sys.executable!r}\nCHECKS=(runner_probe)\nREAL_INPUT_CHECKS=()\n"
                f"check_runner_probe() {{ {body}; }}")
        script = runner.replace('cd "${0:A:h:h:h}"', '', 1).replace(
            "source work/new-game/checks.sh", stub, 1)
        with tempfile.TemporaryDirectory(prefix="claw-regression-runner-") as directory:
            run = subprocess.run(["zsh", "-s", "--", "runner_probe"], input=script,
                                 cwd=directory, capture_output=True, text=True)
        records = [json.loads(line) for line in run.stdout.splitlines()
                   if line.startswith('{"regressions":')]
        passed = (run.returncode == 0 and len(records) == 1
                  and records[0]["status"] == "pass" and records[0]["failures"] == 0)
        failed = (run.returncode != 0 and len(records) == 1
                  and records[0]["status"] == "fail" and records[0]["failures"] == 1)
        results[name] = passed if expected_pass else failed
    ok = all(results.values())
    print(json.dumps({"check": "regression-runner", "status": "pass" if ok else "fail",
                      "scenarios": results}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
