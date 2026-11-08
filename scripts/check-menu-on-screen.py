"""Check the Mac app's presented frames against the existing original trace.

Run scripts/run-mac.sh --menu-check "$PWD/work/menu-on-screen", inspect the
window, then run this script. This checks the app presentation boundary only;
family admission and the full native join remain their existing checks.
Menu evidence ignores live input by default; --menu-allow-live-input opts in.
Run scripts/check-menu-input-isolation.py to verify isolation with real events.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--evidence", type=Path, default=ROOT / "work/menu-on-screen")
parser.add_argument("--reference", type=Path, default=ROOT / "work/menu-map/trace.json")
args = parser.parse_args()
original = json.loads(args.reference.read_text())
actual = json.loads((args.evidence / "app-menu.json").read_text())
assert original["status"] == actual["status"] == "pass"
assert original["executable_sha256"] == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263"
assert actual["initializer"] == "45ace0" and actual["frameEntry"] == "428b60"
assert len(actual["frames"]) >= len(original["presentations"]) == 61
for index, frame in enumerate(actual["frames"], 1):
    assert frame["frame"] == frame["presentations"] == index
    assert (frame["width"], frame["height"]) == (640, 480)
    assert frame["resourceFault"] == frame["displayFault"] == 0
for index, (frame, reference) in enumerate(zip(actual["frames"], original["presentations"]), 1):
    assert frame["frame"] == frame["presentations"] == index
    assert (frame["width"], frame["height"]) == (640, 480)
    assert frame["resourceFault"] == frame["displayFault"] == 0
    assert frame["pixels"] == reference["pixels_sha256"], (index, "pixels")
    assert frame["palette"] == reference["palette_sha256"], (index, "palette")
    if original.get('startup_paper'):
        clock = original['input_witnesses'][index-1]
        assert frame['frame_ms'] == clock['frame_ms'], (index, 'frame clock')
        assert frame['milliseconds'] - actual['frames'][0]['milliseconds'] == clock['milliseconds'] - original['input_witnesses'][0]['milliseconds'], (index, 'elapsed clock')
assert (args.evidence / "menu.png").is_file()
if len(actual["frames"]) >= 1801:
    assert actual["ceilCalls"] > 0 and actual["directSoundCalls"] > 0
print(json.dumps({"status": "pass", "compared_frames": 61, "total_presented_frames": len(actual["frames"]),
                  "pixels": "original for first 61 frames", "palette": "original for first 61 frames",
                  "scope": "Mac app presentation; inspect its window separately", "evidence": str(args.evidence)}))
