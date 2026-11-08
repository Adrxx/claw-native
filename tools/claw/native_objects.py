"""Compiles the C++ modules for the native gate in parallel, reusing unchanged objects.

    python -m tools.claw.native_objects --dir <directory> [--asan] [--jobs 4]

Prints the object file paths, one per line, for the shell script to link. An
object is rebuilt only when its source, any header or the flags changed. Extra
compiler flags come from CLAW_NATIVE_CXXFLAGS (for example "-Os" to build the
way the app's Release configuration does).
"""
import argparse
import concurrent.futures
import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from .paths import ROOT, SOURCES


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--asan", action="store_true")
    parser.add_argument("--jobs", type=int, default=int(os.environ.get("CLAW_NATIVE_JOBS", "4")))
    options = parser.parse_args(argv)
    if options.jobs < 1:
        parser.error("--jobs must be positive")
    directory = Path(options.dir)
    directory.mkdir(parents=True, exist_ok=True)
    flags = ["-std=c++17", "-ffp-contract=off"] + shlex.split(os.environ.get("CLAW_NATIVE_CXXFLAGS", ""))
    if options.asan:
        flags += ["-fsanitize=address", "-fno-omit-frame-pointer"]
    headers = hashlib.sha256()
    for header in sorted(SOURCES.glob("*.h")) + sorted(SOURCES.glob("*.hpp")) + sorted(SOURCES.glob("*.inc")):
        headers.update(header.read_bytes())
    names = (ROOT / "scripts" / "native-gate-sources.txt").read_text().split()

    def build(name):
        source = SOURCES / f"{name}.cpp"
        source_bytes = source.read_bytes()
        # Native ABI aliases include the unchanged admitted canonical body.
        # Its bytes must participate in the object cache identity as well.
        included = b"".join((SOURCES / name.decode()).read_bytes() for name in
                            re.findall(rb'^#include "([^"/]+\.cpp)"', source_bytes, re.M))
        key = hashlib.sha256(source_bytes + included + headers.digest() + " ".join(flags).encode()).hexdigest()[:12]
        output = directory / f"{name}-{key}.o"
        if not output.exists():
            done = subprocess.run(["xcrun", "clang++", *flags, "-c", str(source), "-o", str(output)],
                                  capture_output=True, text=True)
            if done.returncode:
                raise RuntimeError(f"{name}: {done.stderr[-2000:]}")
        return str(output)

    with concurrent.futures.ThreadPoolExecutor(max_workers=options.jobs) as pool:
        objects = list(pool.map(build, names))
    print("\n".join(objects))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
