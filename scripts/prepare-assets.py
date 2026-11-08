#!/usr/bin/env python3
"""Copy the local CrazyHook pack's original Claw assets into the development app."""
import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("pack", type=Path, help="The existing CrazyHook complete-pack ZIP")
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
destination = project / "App" / "GameData"
with zipfile.ZipFile(args.pack) as archive, tempfile.TemporaryDirectory() as temporary:
    base = Path(temporary)
    for member in archive.infolist():
        path = Path(member.filename)
        parts = path.parts
        if len(parts) < 4 or parts[1] != "Assets":
            continue
        relative = Path(*parts[2:])
        wanted = relative.parts[:2] in [("CLAW", "IMAGES"), ("CLAW", "ANIS")]
        wanted = wanted or relative.as_posix() == "LEVEL1/PALETTES/MAIN.PAL"
        if not wanted or member.is_dir():
            continue
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe archive path")
        target = base / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(member))
    for name in ["IMAGES", "ANIS"]:
        source = base / "CLAW" / name
        if not source.is_dir():
            raise ValueError(f"Pack lacks {source.name}")
    palette = base / "LEVEL1/PALETTES/MAIN.PAL"
    if not palette.is_file():
        raise ValueError("Pack lacks Level 1 palette")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ["IMAGES", "ANIS"]:
        shutil.copytree(base / "CLAW" / name, destination / name, dirs_exist_ok=True)
    shutil.copy2(palette, destination / "MAIN.PAL")
print(f"Prepared local assets in {destination}")
