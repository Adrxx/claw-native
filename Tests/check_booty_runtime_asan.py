"""Replay original-matched story/results snapshots under ASAN and UBSAN.

Requires the ignored, hash-pinned original executable and retail resources.
The default regenerates the corpus by executing the original comparison;
--reuse-corpus is for a corpus already regenerated in the current checkout.
This checks recovered controllers, not native rendering or full-game parity.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("family", choices=["story", "results"])
parser.add_argument("--reuse-corpus", action="store_true")
args = parser.parse_args()
work = root / "work" / f"booty-{args.family}-agent"
work.mkdir(parents=True, exist_ok=True)
if not args.reuse_corpus:
    generator = (
        "capture_booty_story_replays.py" if args.family == "story"
        else "compare_booty_results_runtime.py"
    )
    subprocess.run([sys.executable, str(root / "Tests" / generator)], cwd=root, check=True)
corpus = work / "sanitizer-replay.bin.gz"
if not corpus.is_file():
    parser.error("Missing corpus; run without --reuse-corpus to generate it.")
# Link the same frozen C++ modules selected by the current native target.
# Independent workers' unfinished source files are deliberately outside it.
project = (root / "Claw.xcodeproj/project.pbxproj").read_text()
sources = sorted(set(re.findall(r"path = (Sources/[^;]+\.cpp);", project)))
assert sources and all((root / name).is_file() for name in sources)
executable = work / "root-exact-sized-replay"
subprocess.run([
    "clang++", "-std=c++17", "-g", "-O1", "-ffp-contract=off",
    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
    "-Wall", "-Wextra", "-Werror", "-I", str(root / "Sources"),
    str(root / "Tests" / f"booty_{args.family}_exact_replay.cpp"),
    *[str(root / name) for name in sources], "-lz", "-o", str(executable),
], cwd=root, check=True)
subprocess.run([str(executable), str(corpus)], cwd=root, check=True,
               env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"})
