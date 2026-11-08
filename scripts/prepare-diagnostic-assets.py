"""Copy checked-in diagnostic tables; no original EXE is needed."""
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
def prepare(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "App/OriginalTables/DiagnosticPolicy.json", destination)
    return destination
if __name__ == "__main__":
    import sys
    print(prepare(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT / "App/GameData/DiagnosticPolicy.json"))
