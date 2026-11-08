"""Lists build leftovers under work/ that can be deleted, with sizes. Deletes nothing unless told to.

    python -m tools.claw.cleanup                 list only
    python -m tools.claw.cleanup --delete        delete what was listed

Never touches the current app bundle directory, the root Ghidra project, the function corpus, archives, captured
corpora, worker scratch directories or tools.
"""
import json
import shutil
import subprocess
import sys

from .paths import WORK

KEEP = {"NativeSurfaceFactoryMac", "dd", "ghidra-project", "corpus", "archive", "tools", "test-env", "baseline", "gate",
        "review-2026-10-12", "build", "packets", "pilot", "native-gate"}


def size(path):
    done = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True)
    return int(done.stdout.split()[0]) * 1024 if done.stdout else 0


def candidates():
    found = []
    for entry in sorted(WORK.iterdir()):
        if entry.name in KEEP or not entry.is_dir() or entry.is_symlink():
            continue
        if (entry / "Build" / "Products").exists() or (entry / "Build" / "Intermediates.noindex").exists():
            found.append((entry, "Xcode build directory"))
        elif entry.name.startswith("Export") or entry.name.endswith("Verification"):
            found.append((entry, "exported app copy"))
        elif entry.name == "gate-trees":
            found.append((entry, "private trees left by the measurement gate"))
        elif (entry / "ghidra-project").is_dir():
            found.append((entry / "ghidra-project", "private copy of the Ghidra project"))
    for shard in sorted((WORK / "corpus").glob("proj[0-9]*")):
        found.append((shard, "Ghidra project copy used once to dump the corpus"))
    return found


def main(argv):
    items = [(path, reason, size(path)) for path, reason in candidates()]
    total = sum(s for _, _, s in items)
    for path, reason, bytes_ in items:
        print(f"{bytes_ / 1e6:9.1f} MB  {path.relative_to(WORK.parent)}  ({reason})")
    deleted = 0
    if "--delete" in argv:
        for path, _, _ in items:
            shutil.rmtree(path, ignore_errors=True)
            deleted += 1
    print(json.dumps({"command": "cleanup", "items": len(items), "bytes": total, "gigabytes": round(total / 1e9, 2),
                      "deleted": deleted, "status": "pass"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
