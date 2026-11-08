"""Adds functions the first corpus dump missed, then re-merges the corpus. Prints one JSON line.

    python -m tools.claw.corpus_extend

The first dump found functions through calls and through pointers in the data sections. Object-logic and state
callbacks are registered by code that pushes their address, so many of them were never made into functions. This
seeds every registered callback from Tests/symbols.json, then repeats with any call target that is still not a
function, until nothing new turns up.
"""
import json
import os
import re
import subprocess
import sys

from . import index
from .paths import CORPUS, PYTHON, ROOT, TESTS, WORK

GHIDRA = WORK / "tools" / "ghidra_12.1.4_PUBLIC"
JAVA = WORK / "tools" / "jdk-21.0.12.1+1" / "Contents" / "Home"
PROJECT = CORPUS / "ghidra-project"
TEXT = (0x401000, 0x50ADB5)


def program_name():
    for log in sorted(CORPUS.glob("*.log")):
        match = re.search(r"-process\s+(\S+)", log.read_text(errors="replace"))
        if match:
            return match.group(1)
    return "CLAW.EXE"


def headless(arguments, read_only):
    command = [str(GHIDRA / "support" / "analyzeHeadless"), str(PROJECT), "ClawOriginal", "-process", program_name(),
               "-noanalysis", "-scriptPath", str(ROOT / "tools" / "ghidra"), "-postScript", "DumpProgram.java", *arguments]
    if read_only:
        command.append("-readOnly")
    environment = dict(os.environ, JAVA_HOME=str(JAVA), GHIDRA_INSTALL_DIR=str(GHIDRA))
    done = subprocess.run(command, capture_output=True, text=True, env=environment)
    return done.returncode, (done.stdout + done.stderr)[-1500:]


def corpus(subcommand):
    done = subprocess.run([str(PYTHON), "-m", "tools.claw.corpus", subcommand], cwd=ROOT, capture_output=True, text=True)
    return json.loads(done.stdout.strip().splitlines()[-1])


def missing_call_targets():
    index.functions.cache_clear()
    functions = index.functions()
    targets = set()
    for entry in functions:
        targets |= {t for t in index.call_targets(entry) if TEXT[0] <= t < TEXT[1]}
    return {t for t in targets if t not in functions and index.containing(t) is None}


def main(argv):
    before = len(index.functions())
    symbols = json.loads((TESTS / "symbols.json").read_text())["symbols"]
    seeds = {int(a, 16) for a, s in symbols.items() if s["kind"] in ("logic-callback", "state-callback")}
    seeds = {a for a in seeds if a not in index.functions() and index.containing(a) is None}
    rounds, log = [], ""
    for round_number in range(1, 5):
        if not seeds:
            break
        seed_file = CORPUS / f"seeds-extend-{round_number}.txt"
        seed_file.write_text("\n".join(f"{a:08x}" for a in sorted(seeds)) + "\n")
        code, log = headless(["seed", str(seed_file), str(CORPUS / f"phaseA-extend-{round_number}.json")], read_only=False)
        if code:
            break
        code, log = headless(["dump", str(CORPUS), "0", "1"], read_only=True)
        if code:
            break
        corpus("merge")
        corpus("asm")
        rounds.append(len(seeds))
        seeds = missing_call_targets()
    check = corpus("check")
    after = len(index.functions.__wrapped__())
    print(json.dumps({"command": "corpus-extend", "functions_before": before, "functions_after": after,
                      "seeded_per_round": rounds, "still_missing_call_targets": len(seeds),
                      "coverage_fraction": check.get("coverage_fraction"), "check": check.get("status"),
                      "last_log": log[-600:] if (not rounds or seeds) else ""}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
