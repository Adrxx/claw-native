"""Repository locations shared by every tool."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "Tests"
SOURCES = ROOT / "Sources"
DOCS = ROOT / "docs"
WORK = ROOT / "work"
FAMILIES = TESTS / "families"
CORPUS = WORK / "corpus"
PYTHON = WORK / "test-env" / "bin" / "python"
ORIGINAL_EXE = ROOT / "Original" / "claw10" / "CLAW.EXE"
ORIGINAL_SHA256 = "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263"


def relative(path):
    """Path relative to the repository root, as a string, for JSON output."""
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)
