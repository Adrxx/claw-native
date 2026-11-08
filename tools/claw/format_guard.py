"""Format guard: prove that clang-format cannot change the compiled behavior of Sources/.

Subcommands:
  check  compile each tracked Sources/*.cpp at git HEAD and in the working tree
         with identical flags and require byte-identical object files.
  apply  run clang-format -i on tracked Sources/*.cpp and *.h that are not
         listed in tools/claw/format_exclude.json.

Source is fed to the compiler on stdin so no file path is embedded in the
object code. The last stdout line is one JSON object.
"""

import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_FILE = ROOT / "tools" / "claw" / "format_exclude.json"
COMPILE_FLAGS = ["-std=c++17", "-O2", "-ffp-contract=off"]
WORKERS = 16
LONG_LINE = 200


def run(command, input_bytes=None, cwd=ROOT):
    return subprocess.run(command, input=input_bytes, cwd=cwd, capture_output=True)


def tracked_sources():
    output = run(["git", "ls-files", "Sources"]).stdout.decode()
    paths = [line for line in output.splitlines() if line.endswith((".cpp", ".h"))]
    return [path for path in paths if path != "Sources/Claw-Bridging-Header.h"]


def tracked_cpp_files():
    return [path for path in tracked_sources() if path.endswith(".cpp")]


def excluded_paths():
    entries = json.loads(EXCLUDE_FILE.read_text())
    return sorted(entry["path"] for entry in entries)


def materialize_head_tree(destination):
    """Write every tracked file under Sources/ as of HEAD into destination/Sources."""
    listing = run(["git", "ls-tree", "-r", "--name-only", "HEAD", "Sources"]).stdout.decode()
    for path in listing.splitlines():
        content = run(["git", "show", "HEAD:" + path]).stdout
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def compile_object(source_bytes, include_dir):
    command = ["xcrun", "clang++", *COMPILE_FLAGS, "-I", str(include_dir), "-c", "-x", "c++", "-", "-o", "-"]
    result = run(command, input_bytes=source_bytes)
    if result.returncode != 0:
        return None, result.stderr.decode(errors="replace")[-500:]
    return result.stdout, ""


def check_one(path, head_include, work_include):
    head_source = run(["git", "show", "HEAD:" + path]).stdout
    work_source = (ROOT / path).read_bytes()
    head_object, head_error = compile_object(head_source, head_include)
    work_object, work_error = compile_object(work_source, work_include)
    if head_object is None or work_object is None:
        return path, False, "compile failed: " + (head_error or work_error)
    return path, head_object == work_object, ""


def count_long_lines(texts):
    return sum(1 for text in texts for line in text.splitlines() if len(line) > LONG_LINE)


def long_lines_before(paths):
    texts = [run(["git", "show", "HEAD:" + path]).stdout.decode(errors="replace") for path in paths]
    return count_long_lines(texts)


def long_lines_after(paths):
    texts = [(ROOT / path).read_text(errors="replace") for path in paths]
    return count_long_lines(texts)


def command_check():
    paths = tracked_cpp_files()
    with tempfile.TemporaryDirectory() as scratch:
        head_include = Path(scratch) / "Sources"
        materialize_head_tree(Path(scratch))
        work_include = ROOT / "Sources"
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(pool.map(lambda p: check_one(p, head_include, work_include), paths))
    different = sorted(path for path, same, _ in results if not same)
    for path, same, note in results:
        if not same:
            print(f"DIFFERENT {path} {note}", file=sys.stderr)
    all_sources = tracked_sources()
    summary = {
        "command": "format-guard",
        "files": len(paths),
        "identical": len(paths) - len(different),
        "different": different,
        "excluded": excluded_paths(),
        "lines_over_200_before": long_lines_before(all_sources),
        "lines_over_200_after": long_lines_after(all_sources),
        "status": "pass" if not different else "fail",
    }
    print(json.dumps(summary))
    return 0 if not different else 1


def command_apply():
    skip = set(excluded_paths())
    targets = [path for path in tracked_sources() if path not in skip]
    for start in range(0, len(targets), 50):
        batch = targets[start:start + 50]
        result = run(["xcrun", "clang-format", "-i", *batch])
        if result.returncode != 0:
            print(result.stderr.decode(), file=sys.stderr)
            print(json.dumps({"command": "format-apply", "status": "fail"}))
            return 1
    print(json.dumps({"command": "format-apply", "formatted": len(targets), "skipped": sorted(skip), "status": "pass"}))
    return 0


def main(argv):
    if len(argv) != 1 or argv[0] not in ("check", "apply"):
        print(json.dumps({"command": "format-guard", "status": "fail", "error": "usage: check|apply"}))
        return 2
    return command_check() if argv[0] == "check" else command_apply()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
