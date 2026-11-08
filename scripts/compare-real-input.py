"""Runs real-input checks on the fast clock (input gate) and on the real-time clock and compares their evidence.

Each converted check writes evidence.json: what it judges (states, marks, posted commands, application words,
call deltas), without frame numbers, wall-clock or game-clock times. Equal evidence means the fast run saw what
the real-time run saw. Results: work/real-input-compare/<check>-{fast,real}.json.

Usage: work/test-env/bin/python scripts/compare-real-input.py [check ...] [--config Release]
Use --saved to compare the captures from fast and real-time regressions.sh runs.
Prints one JSON line last.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "real-input-compare"
PY = ROOT / "work" / "test-env" / "bin" / "python"
CHECKS = {
    "end_of_level": ("scripts/check-end-of-level.py", ["work/end-of-level/check/evidence.json"]),
    "ingame_display": ("scripts/check-ingame-display-options.py", ["work/display-options/check/evidence.json"]),
    "ingame_audio": ("scripts/check-ingame-audio-options.py",
                     ["work/audio-options/check/evidence.json", "work/audio-options/stored/evidence.json"]),
    "pause_gameover": ("scripts/check-pause-gameover.py", ["work/pause-gameover/check/evidence.json"]),
    "weapon_keys": ("scripts/check-weapon-keys.py", ["work/weapon-keys/check/evidence.json"]),
    "movie_skip": ("scripts/check-movie-skip.py", ["work/movie-skip/check/evidence.json"]),
    "settings": ("scripts/check-settings-persistence.py", ["work/settings-persistence/evidence.json"]),
    "cheat_codes": ("scripts/check-cheat-codes.py", ["work/cheat-codes/check/evidence.json"]),
    "movie_flows": ("scripts/check-movie-flows.py", ["work/movie-level-replay/replay-skip/evidence.json"]),
    "accelerators": ("scripts/check-accelerators.py", ["work/accelerators/check/evidence.json"]),
}


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: fast {json.dumps(a)[:120]} real {json.dumps(b)[:120]}"]


def run(check, mode, config):
    script, evidence = CHECKS[check]
    for path in evidence:
        (ROOT / path).unlink(missing_ok=True)
    began = time.monotonic()
    flags = ["--real-time"] if mode == "real" else []
    done = subprocess.run(["nice", "-n", "10", str(PY), script, "--config", config, *flags], cwd=ROOT,
                          capture_output=True, text=True, env={**os.environ, "REAL_TIME": "1" if mode == "real" else "0"})
    last = (done.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        status = json.loads(last).get("status")
    except ValueError:
        status = "fail"
    if done.returncode != 0:
        status = "fail"
    record = {"status": status, "seconds": round(time.monotonic() - began, 1), "evidence": [],
              "output_tail": (done.stdout + done.stderr)[-1500:]}
    for path in evidence:
        source = ROOT / path
        record["evidence"].append(json.loads(source.read_text()) if source.exists() else None)
    (OUT / f"{check}-{mode}.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    return record


def capture(check, mode, log, seconds):
    output = Path(log).read_text()
    records = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict) and "status" in value:
                records.append(value)
        except ValueError:
            pass
    status = "pass" if records and all(r["status"] == "pass" for r in records) else "fail"
    evidence = [json.loads((ROOT / path).read_text()) if (ROOT / path).exists() else None for path in CHECKS[check][1]]
    record = {"status": status, "seconds": seconds, "evidence": evidence, "output_tail": output[-1500:]}
    (OUT / f"{check}-{mode}.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    return status == "pass" and None not in evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checks", nargs="*")
    parser.add_argument("--config", default="Release")
    parser.add_argument("--saved", action="store_true", help="compare evidence captured by regressions.sh")
    parser.add_argument("--capture", choices=list(CHECKS))
    parser.add_argument("--mode", choices=["fast", "real"])
    parser.add_argument("--log")
    parser.add_argument("--seconds", type=float, default=0)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.capture:
        if not args.mode or not args.log:
            parser.error("--capture requires --mode and --log")
        return 0 if capture(args.capture, args.mode, args.log, args.seconds) else 1
    results = {}
    for check in args.checks or CHECKS:
        if args.saved:
            def saved(mode):
                path = OUT / f"{check}-{mode}.json"
                return json.loads(path.read_text()) if path.exists() else {"status": "missing", "seconds": 0, "evidence": [None]}
            fast, real = saved("fast"), saved("real")
        else:
            fast, real = run(check, "fast", args.config), run(check, "real", args.config)
        differences = diff(fast["evidence"], real["evidence"])
        missing = None in fast["evidence"] or None in real["evidence"]
        results[check] = {"fast": fast["status"], "real": real["status"], "fast_seconds": fast["seconds"],
                          "real_seconds": real["seconds"], "equal": not differences and not missing,
                          "differences": differences[:20]}
        print(json.dumps({check: results[check]}), file=sys.stderr)
    ok = all(r["fast"] == r["real"] == "pass" and r["equal"] for r in results.values())
    print(json.dumps({"check": "compare-real-input", "status": "pass" if ok else "fail", "results": results}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
