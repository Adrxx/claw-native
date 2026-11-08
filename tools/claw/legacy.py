"""Run the Codex-era comparison scripts and report each as one JSON record.

The 159 `Tests/compare_*.py` scripts have no common entry point. Most run with
no arguments. Seventeen take the original executable, a prebuilt library and
sometimes an asset directory; their command lines exist only as prose recipes
in the documents. This module finds those recipes mechanically, runs every
script with a timeout, and never interprets the result beyond pass or fail.
"""
import concurrent.futures
import json
import re
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

from .paths import ROOT

RECIPE_DOCS = ("docs", "README.md")
WORK_DIR = re.compile(r"work/[A-Za-z0-9_.-]+")
HELPER_IMPORT = re.compile(r"^\s*(?:import|from)\s+([a-z0-9_]+)", re.M)
HELPER_FILE = re.compile(r"with_name\('([a-z0-9_]+\.py)'\)")


def scripts(tree=ROOT):
    return sorted((Path(tree) / "Tests").glob("compare_*.py"))


def _doc_lines(tree):
    """Every shell line in the documents, with backslash continuations joined."""
    lines = []
    for entry in RECIPE_DOCS:
        path = Path(tree) / entry
        files = sorted(path.glob("*.md")) if path.is_dir() else [path]
        for file in files:
            text = file.read_text(errors="replace").replace("\\\n", " ")
            lines.extend(line.strip() for line in text.splitlines())
    return lines


def takes_arguments(script):
    text = script.read_text(errors="replace")
    return "argparse" in text or "sys.argv" in text


def recipe(script, doc_lines):
    """Arguments and prerequisite build lines for a script, from the documents."""
    needle = f"Tests/{script.name}"
    for line in doc_lines:
        if needle not in line or "python" not in line:
            continue
        command = line[line.index(needle) + len(needle):].strip().strip("`")
        try:
            arguments = shlex.split(command.split("#")[0])
        except ValueError:
            continue
        if not arguments:
            continue
        outputs = [a for a in arguments if a.startswith("work/")]
        prerequisites = [
            candidate for output in outputs for candidate in doc_lines
            if f"-o {output}" in candidate and "clang" in candidate
        ]
        return arguments, prerequisites[:1]
    return None, []


def work_dirs(script, seen=None):
    """Scratch directories a script and its helper chain mention."""
    seen = set() if seen is None else seen
    if script in seen or not script.exists():
        return set()
    seen.add(script)
    text = script.read_text(errors="replace")
    found = set(WORK_DIR.findall(text))
    names = {f"{n}.py" for n in HELPER_IMPORT.findall(text)} | set(HELPER_FILE.findall(text))
    for name in names:
        found |= work_dirs(script.with_name(name), seen)
    return found - {"work/test-env"}


def run_one(script, tree, doc_lines, timeout):
    tree = Path(tree)
    record = {"script": f"Tests/{script.name}", "arguments": [], "prerequisites": []}
    arguments = []
    if takes_arguments(script):
        arguments, prerequisites = recipe(script, doc_lines)
        if arguments is None:
            arguments, prerequisites = [], []  # the script reads sys.argv but its documented command has no arguments
        record.update(arguments=arguments, prerequisites=prerequisites)
        for line in prerequisites:
            built = subprocess.run(line, shell=True, cwd=tree, capture_output=True, text=True)
            if built.returncode:
                record.update(status="prerequisite-failed", seconds=0.0, stderr=built.stderr[-1200:])
                return record
    command = [str(tree / "work/test-env/bin/python"), f"Tests/{script.name}", *arguments]
    started = time.monotonic()
    try:
        done = subprocess.run(command, cwd=tree, capture_output=True, text=True, timeout=timeout)
        status = "pass" if done.returncode == 0 else "fail"
        stdout, stderr, code = done.stdout, done.stderr, done.returncode
    except subprocess.TimeoutExpired as expired:
        status, code = "timeout", None
        stdout = (expired.stdout or b"").decode(errors="replace") if isinstance(expired.stdout, bytes) else (expired.stdout or "")
        stderr = (expired.stderr or b"").decode(errors="replace") if isinstance(expired.stderr, bytes) else (expired.stderr or "")
    record.update(
        status=status,
        returncode=code,
        seconds=round(time.monotonic() - started, 1),
        stdout=stdout[-800:],
        stderr=stderr[-1500:],
    )
    return record


def baseline(tree=ROOT, output=None, jobs=6, timeout=1800, only=None, resume=False):
    """Run every comparison script once. Scripts sharing a scratch directory never overlap."""
    tree = Path(tree)
    doc_lines = _doc_lines(tree)
    todo = [s for s in scripts(tree) if only is None or s.stem in only]
    if resume and output and Path(output).exists():
        finished = {json.loads(line)["script"] for line in Path(output).read_text().splitlines() if line.strip()}
        todo = [s for s in todo if f"Tests/{s.name}" not in finished]
    locks, guard = {}, threading.Lock()
    writer = threading.Lock()
    results = []
    sink = open(output, "a") if output else None

    def task(script):
        dirs = sorted(work_dirs(script)) or [script.stem]
        with guard:
            held = [locks.setdefault(d, threading.Lock()) for d in dirs]
        for lock in held:
            lock.acquire()
        try:
            record = run_one(script, tree, doc_lines, timeout)
        finally:
            for lock in reversed(held):
                lock.release()
        record["work_dirs"] = dirs
        with writer:
            results.append(record)
            if sink:
                sink.write(json.dumps(record) + "\n")
                sink.flush()
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(task, todo))
    # Some scripts load a library that another script builds. Run in parallel, the borrower can start first and
    # fail for that reason alone, so everything that failed gets one more try, one at a time.
    for script in [s for s in todo if any(r["script"] == f"Tests/{s.name}" and r["status"] != "pass" for r in results)]:
        results[:] = [r for r in results if r["script"] != f"Tests/{script.name}"]
        record = task(script)
        record["second_try"] = True
    if sink:
        sink.close()
    counts = {}
    for record in results:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    return {"command": "baseline", "scripts": len(results), "counts": counts, "output": str(output) if output else None}


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(prog="claw legacy")
    parser.add_argument("--tree", default=str(ROOT))
    parser.add_argument("--output")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--resume", action="store_true", help="skip scripts already recorded in the output file")
    options = parser.parse_args(argv)
    summary = baseline(options.tree, options.output, options.jobs, options.timeout,
                       set(options.only) if options.only else None, options.resume)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
