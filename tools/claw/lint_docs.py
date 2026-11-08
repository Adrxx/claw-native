"""Keeps the instruction files short and readable. One JSON line.

Every agent reads CLAUDE.md and AGENTS.md at the start of every session, so their length is paid on every worker.
Status belongs in generated files (docs/STATUS.md, tools/queue.json), not in instructions.
"""
import json
import re
import sys

from .paths import ROOT

LIMITS = {"CLAUDE.md": 60, "AGENTS.md": 30, "docs/OPERATING.md": 260}
# A word glued to a number, as in "All14" or "passed2,741": unreadable for people and models alike.
GLUED = re.compile(r"\b(?:[A-Za-z]{3,}\d[\d,]*|\d[\d,]*[A-Za-z]{3,})\b")
ALLOWED = {"sha256", "x86", "utf8", "arm64", "64bit", "32bit"}
STATUS = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}")  # big counts and run ids


def check(path, limit):
    text = (ROOT / path).read_text()
    lines = text.splitlines()
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    prose = re.sub(r"`[^`]*`", "", prose)
    problems = []
    if len(lines) > limit:
        problems.append(f"{len(lines)} lines, limit {limit}")
    glued = sorted({w for w in GLUED.findall(prose) if w.lower() not in ALLOWED and not w.lower().startswith("0x")})
    if glued:
        problems.append("words glued to numbers: " + ", ".join(glued[:12]))
    if path in ("CLAUDE.md", "AGENTS.md") and STATUS.search(prose):
        problems.append("status figures or run ids belong in docs/STATUS.md or tools/queue.json, not here")
    return problems


def main(argv):
    results = {path: check(path, limit) for path, limit in LIMITS.items() if (ROOT / path).exists()}
    failing = {path: p for path, p in results.items() if p}
    print(json.dumps({"command": "lint-docs", "checked": len(results), "problems": failing,
                      "status": "pass" if not failing else "fail"}))
    return 0 if not failing else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
