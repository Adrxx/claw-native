#!/usr/bin/env python3
"""Check the packaged release identity against the authenticated v1.3 original.

This checks build metadata and the menu's real formatting inputs; the owner
checks the rendered app by hand.
"""
import argparse
import json
from pathlib import Path
import plistlib
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw_v13


def original_version():
    # VS_FIXEDFILEINFO is independent of the string resource used by bundling.
    signature = struct.pack("<II", 0xFEEF04BD, 0x10000)
    records = []
    for section in claw_v13().sections:
        at = section.data.find(signature)
        if at >= 0:
            ms, ls = struct.unpack_from("<II", section.data, at + 8)
            records.append((ms >> 16, ms & 0xffff, ls >> 16, ls & 0xffff))
    assert records == [(1, 3, 0, 60)], records
    return records[0]


def check_menu(path, version):
    spans = {int(k, 16): bytes(v) for k, v in json.loads(path.read_text()).items()}
    actual = struct.unpack("<4I", spans[0x53ec38])
    assert actual == version, (path, actual, version)

    def text(address):
        data = next(data[address - base:] for base, data in spans.items()
                    if base <= address < base + len(data))
        return data.split(b"\0", 1)[0].decode("ascii")

    major, minor, patch, _ = actual
    address = 0x5291c4 if minor else 0x5291d0
    fmt = text(address)
    # The retained menu formatter has the same strings in the v1.3 image.
    original_address = 0x527508 if minor else 0x527514
    p = claw_v13()
    section = next(s for s in p.sections if s.address <= original_address < s.address + s.size)
    original = bytes(section.data[original_address - section.address:]).split(b"\0", 1)[0].decode("ascii")
    assert fmt == original
    displayed = fmt % ((major, minor, patch) if minor else (major, patch))
    assert displayed == "v1.30", displayed
    return displayed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, action="append", default=[])
    args = parser.parse_args()
    version = original_version()
    project = (ROOT / "Claw.xcodeproj/project.pbxproj").read_text()
    assert re.findall(r"MARKETING_VERSION = ([^;]+);", project) == ["1.3", "1.3"]
    displayed = check_menu(ROOT / "App/GameData/MENU/metadata.json", version)
    for app in args.app:
        contents = app / "Contents" if (app / "Contents").is_dir() else app
        resources = contents / "Resources" if contents != app else app
        with (contents / "Info.plist").open("rb") as stream:
            assert plistlib.load(stream)["CFBundleShortVersionString"] == "1.3", app
        check_menu(resources / "GameData/MENU/metadata.json", version)
    print(json.dumps(dict(check="app-version", status="pass", marketing_version="1.3",
                         original_version=version, menu_text=displayed,
                         bundles=[str(app) for app in args.app])))


if __name__ == "__main__":
    main()
