"""Prepare build inputs using checked-in tables and player-supplied disc assets."""
import json
import runpy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def prepare(destination=ROOT / "App/GameData"):
    tables = ROOT / "App/OriginalTables"
    sources = sorted(tables.rglob("*.json"))
    if len(sources) != 8:
        raise ValueError("Missing original tables; restore App/OriginalTables from the project")
    for source in sources:
        target = destination / source.relative_to(ROOT / "App/OriginalTables")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
    runpy.run_path(str(ROOT / 'scripts/crazyhook_assets.py'))['copy_helpers'](destination / 'CRAZYHOOK')
if __name__ == "__main__":
    if (ROOT / "App/GameData").exists():
        prepare()
    runpy.run_path(str(ROOT / "scripts/prepare-app-icon.py"))["generate"]()
    print(json.dumps({"status":"pass", "tables":"App/OriginalTables", "original_exe_required":False}))
