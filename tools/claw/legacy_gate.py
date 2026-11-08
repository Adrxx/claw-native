"""Measures a legacy family the way the admission gate would, without editing its tests.

    python -m tools.claw regate <family> [--record]
    python -m tools.claw regate --all [--jobs N] [--record]

For each family this runs its comparison scripts twice in a private copy of the
tree, so nothing is written into the original worker's directory: once as
written, once with every random seed changed. It records which original
functions the scripts call directly and how much of each one actually ran.
Prints one JSON line per invocation.
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import index, legacy, manifest
from .paths import PYTHON, ROOT, WORK

LINKED = ("Sources", "Original", "App", "docs", "scripts", "research", "tools", "Claw.xcodeproj")
PROBE = ROOT / "tools" / "claw" / "legacy_probe.py"


def build_tree(spec):
    """A private tree: tests and the family's scratch directories are copy-on-write clones, the rest are links."""
    tree = WORK / "gate-trees" / spec["id"]
    if tree.exists():
        shutil.rmtree(tree)
    (tree / "work").mkdir(parents=True)
    for name in LINKED:
        if (ROOT / name).exists():
            (tree / name).symlink_to(ROOT / name)
    subprocess.run(["cp", "-Rc", str(ROOT / "Tests"), str(tree / "Tests")], check=True)
    private = set(spec["oracle"].get("work_dirs", []))
    for command in spec["oracle"].get("commands", []):
        private |= legacy.work_dirs(ROOT / command["script"])
    private = {Path(p).parts[1] for p in private if len(Path(p).parts) > 1}
    private -= {"test-env", "tools", "gate-trees", "corpus", "archive", "build", "packets", "baseline"}
    for entry in WORK.iterdir():
        target = tree / "work" / entry.name
        if entry.name in private and entry.is_dir():
            subprocess.run(["cp", "-Rc", str(entry), str(target)], check=True)
        elif entry.name != "gate-trees":
            target.symlink_to(entry)
    return tree


def run_pass(spec, tree, salt, timeout):
    """Run every comparison script of the family once. Returns (status, roots, executed intervals, failure text)."""
    roots, executed, failure = {}, [], None
    status = "pass"
    for number, command in enumerate(spec["oracle"]["commands"]):
        for line in command.get("prerequisites", []):
            subprocess.run(line, shell=True, cwd=tree, capture_output=True)
        output = tree / f"probe-{salt}-{number}.json"
        environment = dict(os.environ, CLAW_PROBE_OUT=str(output), CLAW_PROBE_SALT=str(salt))
        arguments = [str(PYTHON), str(PROBE), command["script"], *command.get("arguments", [])]
        try:
            done = subprocess.run(arguments, cwd=tree, capture_output=True, text=True, timeout=timeout, env=environment)
            if done.returncode:
                status, failure = "fail", failure or f"{command['script']}: {done.stderr[-500:]}"
        except subprocess.TimeoutExpired:
            status, failure = "timeout", failure or f"{command['script']}: no result in {timeout} s"
        if output.exists():
            probe = json.loads(output.read_text())
            for address, count in probe["roots"].items():
                roots[int(address, 16)] = roots.get(int(address, 16), 0) + count
            executed.extend(probe["executed"])
    return status, roots, executed, failure


def executed_bytes(ranges, executed):
    total = covered = 0
    for low, high in ranges:
        marks = bytearray(high - low)
        for first, last in executed:
            first, last = max(first, low), min(last, high)
            if first < last:
                marks[first - low:last - low] = b"\1" * (last - first)
        total += len(marks)
        covered += sum(marks)
    return total, covered


def measure(family, salt=None, timeout=2400, keep=False):
    started = time.monotonic()
    spec = manifest.load(family)
    result = {"command": "regate", "family": family, "date": datetime.date.today().isoformat()}
    if spec["oracle"]["kind"] != "legacy" or not spec["oracle"].get("commands"):
        result.update(status="no-oracle")
        return result
    salt = int.from_bytes(os.urandom(4), "little") | 1 if salt is None else salt
    tree = build_tree(spec)
    try:
        plain, roots, executed, plain_failure = run_pass(spec, tree, 0, timeout)
        salted, salted_roots, salted_executed, salted_failure = run_pass(spec, tree, salt, timeout)
    finally:
        if not keep:
            shutil.rmtree(tree, ignore_errors=True)
    for address, count in salted_roots.items():
        roots[address] = roots.get(address, 0) + count
    executed = sorted(executed + salted_executed)
    functions = index.functions()
    declared = [int(o["address"], 16) for o in spec["owned"] if "interval_end" not in o]
    inferred = not declared
    owned = declared or sorted(a for a in roots if a in functions)
    per_function, never_called, partial, bytes_total, bytes_run = {}, [], [], 0, 0
    for address in owned:
        function = functions.get(address)
        if function is None:
            per_function[f"{address:#x}"] = {"problem": "not a function entry"}
            continue
        total, covered = executed_bytes(function["ranges"], executed)
        bytes_total, bytes_run = bytes_total + total, bytes_run + covered
        calls = roots.get(address, 0)
        per_function[f"{address:#x}"] = {"bytes": total, "executed": covered, "direct_calls": calls}
        if not calls:
            never_called.append(f"{address:#x}")
        if covered < total:
            partial.append(f"{address:#x}")
    result.update(
        status="measured", plain=plain, salted=salted, salt=salt, owned=len(owned), owned_inferred_from_tests=inferred,
        directly_called=len(owned) - len(never_called), never_called_directly=never_called,
        fully_executed=len(owned) - len(partial), bytes_owned=bytes_total, bytes_executed=bytes_run,
        coverage=round(bytes_run / bytes_total, 4) if bytes_total else None,
        plain_failure=plain_failure, salted_failure=salted_failure, seconds=round(time.monotonic() - started, 1))
    detail = WORK / "gate" / family
    detail.mkdir(parents=True, exist_ok=True)
    (detail / "regate.json").write_text(json.dumps({**result, "functions": per_function, "roots": {f"{a:#x}": n for a, n in sorted(roots.items())}}, indent=1) + "\n")
    return result


def record(result):
    """Store the compact measurement in the family's manifest."""
    if result.get("status") != "measured":
        return
    spec = manifest.load(result["family"])
    keys = ("date", "plain", "salted", "salt", "owned", "owned_inferred_from_tests", "directly_called", "fully_executed",
            "bytes_owned", "bytes_executed", "coverage")
    spec["evidence"]["gate"] = {"kind": "legacy-measurement", **{k: result[k] for k in keys}}
    manifest.save(spec)


def main(argv):
    parser = argparse.ArgumentParser(prog="claw regate")
    parser.add_argument("family", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--salt", type=int)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the private tree for inspection")
    parser.add_argument("--resume", action="store_true", help="with --all: skip families already measured today")
    options = parser.parse_args(argv)
    if not options.all:
        result = measure(options.family, options.salt, keep=options.keep)
        if options.record:
            record(result)
        print(json.dumps(result))
        return 0
    families = [name for name, spec in manifest.load_all().items() if spec["oracle"]["kind"] == "legacy"]
    output = WORK / "gate" / f"regate-{datetime.date.today().isoformat()}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    if options.resume and output.exists():
        results = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
        finished = {r["family"] for r in results}
        families = [name for name in families if name not in finished]
        if options.record:
            for result in results:  # results measured earlier without --record
                record(result)
    with open(output, "a") as sink, concurrent.futures.ThreadPoolExecutor(max_workers=options.jobs) as pool:
        for result in pool.map(lambda name: measure(name, options.salt), families):
            results.append(result)
            sink.write(json.dumps(result) + "\n")
            sink.flush()
            if options.record:
                record(result)
    measured = [r for r in results if r["status"] == "measured"]
    print(json.dumps({
        "command": "regate-all", "families": len(results), "measured": len(measured),
        "plain_pass": sum(r["plain"] == "pass" for r in measured),
        "salted_pass": sum(r["salted"] == "pass" for r in measured),
        "every_owned_function_called_directly": sum(not r["never_called_directly"] for r in measured),
        "every_owned_byte_executed": sum(r["bytes_owned"] and r["bytes_executed"] == r["bytes_owned"] for r in measured),
        "output": str(output.relative_to(ROOT))}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
