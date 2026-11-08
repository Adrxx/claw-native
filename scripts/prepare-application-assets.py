"""Copy the checked-in application tables; no original EXE is needed."""
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
def prepare():
    target = ROOT / "App/GameData/APPLICATION/startup.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "App/OriginalTables/APPLICATION/startup.json", target)
if __name__ == "__main__":
    prepare()
