"""Play the original Level 2 trace route in the Mac app and compare it with the original.

Route (Tests/NativeLevelTwo/trace.py, owner decision 2026-10-21): New Game, Level 1 stands
1000 ms, the MPSCULLY level-skip cheat reaches the single-player state's key-down virtual,
the results screen gets one Return whenever its state has waited 12000 ms, the original
continues into Level 2, and Level 2 replays the trace's 60000 ms walk/jump/attack plan.

The app runs it on the trace's own clock (--new-game-clock --level-two-route through
work/new-game/launch.sh: muted, --fast-clock unless FAST=0, CLAW_CONFIG picks the build,
closes only its own instance) and writes level-two-route.json.
This compares, against the original trace work/level-two-map/trace.json:
  - the Level 1 standing frames and every Level 2 frame: elapsed time, action and the
    player fields (position, health, score, states, treasure counts, input mask, game time);
  - the treasure pickups and the life changes (death and respawn) derived from those frames;
  - the state transitions, the cheat and Return key deliveries (relative times) and the
    posted commands from 0x800e on;
  - every Level 2 frame's presented screens (Flip pixel and palette hashes).

Usage: work/test-env/bin/python scripts/check-level-two-play.py [--reuse] [--section cannon]
  --reference PATH --evidence DIR selects a staged trace and separate comparison output.
  --reuse compares existing evidence without launching the app.
  --section NAME compares a Level 2 section instead of the trace's own route: the same prefix, then
    the plan in work/level-two-NAME/trace.json, written by Tests/NativeLevelTwo/section_trace.py
    (entries may place the player once with set_x/set_y). "cannon" places Claw left of the tower
    cannons at x 11100, whose logic states 0x4145f0/0x4146b0 are reached by a source CALL from 0x4141f0
    (app-owner-crash-level-two-4146b0).
Prints one JSON line last.
"""
import argparse
import hashlib
import json
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import read_trace, stored_path
WORK = ROOT / "work" / "level-two-play"
OUT = WORK / "run"
TRACE = ROOT / "work" / "level-two-map" / "trace.json"


def use_section(name):
    global WORK, OUT, TRACE
    WORK = ROOT / "work" / f"level-two-{name}"
    OUT = WORK / "run"
    TRACE = WORK / "trace.json"
FIELDS = ('x', 'y', 'health', 'score', 'player_state', 'logic_state', 'treasure_counts',
          'input_mask', 'game_ms', 'level', 'vtable')


def original():
    """The route's boundaries, taken once from the 560 MB trace."""
    cache = WORK / "original.json"
    with stored_path(TRACE).open("rb") as stream:
        source = dict(path=str(TRACE.resolve()), sha256=hashlib.file_digest(stream, "sha256").hexdigest())
    if cache.exists() and cache.stat().st_mtime >= stored_path(TRACE).stat().st_mtime:
        data = json.loads(cache.read_text())
        if data.get("source") == source:
            return data
    t = read_trace(TRACE)
    if t.get("status") != "pass":
        raise SystemExit("original Level 2 trace is not a passing run")
    presentations = iter(p for p in t["presentations"] if p["phase"].startswith("level-two-"))
    screens = []
    for cycle in t["frame_cycles"]:
        if cycle["phase"].startswith("level-two-"):
            screens.append([[p["pixels_sha256"][:16], p["palette_sha256"][:16]]
                            for p in (next(presentations) for _ in range(cycle["presentations"]))])
    posted = [hex(e["wparam"]) for e in t["physical_events"] if e.get("service") == "PostMessageA"]
    data = dict(plan=t["level_two_plan"], level_one_frames=t["play_frames"], level_two_frames=t["level_two_frames"],
                screens=screens, states=t["state_transitions"], keys=t["key_deliveries"], posted=posted,
                source=source, startup_profile=t.get("startup_profile"))
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def summaries(players):
    """As Tests/NativeLevelTwo/native_join.py: treasure pickups and life changes per frame."""
    pickups, lives = [], []
    for i in range(1, len(players)):
        a, b = players[i - 1], players[i]
        if sum(b['treasure_counts']) > sum(a['treasure_counts']):
            pickups.append(dict(frame=i, after=b['treasure_counts'], score=b['score']))
        if (a['health'] > 0) != (b['health'] > 0) or b['health'] > a['health']:
            lives.append(dict(frame=i, health=b['health'], score=b['score'], x=b['x'], y=b['y']))
    return pickups, lives


def frames_divergence(reference, actual):
    for index, (a, b) in enumerate(zip(reference, actual)):
        fields = [k for k in FIELDS if a['player'].get(k) != b['player'].get(k)]
        if a['elapsed_ms'] != b['elapsed_ms'] or a['action'] != b['action'] or fields:
            return dict(frame=index, elapsed_ms=[a['elapsed_ms'], b['elapsed_ms']], action=[a['action'], b['action']],
                        fields={k: [a['player'].get(k), b['player'].get(k)] for k in fields})
    if len(reference) != len(actual):
        return dict(frames=[len(reference), len(actual)])
    return None


def run_app(plan):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("app-menu.json", "live-state.json", "level-two-route.json"):
        (OUT / name).unlink(missing_ok=True)
    (WORK / "plan.json").write_text(json.dumps(plan))
    env = dict(os.environ)
    subprocess.run([str(ROOT / "work/new-game/launch.sh"), str(OUT), "900", "--menu-check", str(OUT),
                    "--menu-input-script", str(ROOT / "work/new-game/play-events.json"), "--menu-frames", "9000",
                    "--menu-live-check", str(OUT), "--new-game-clock", "--level-two-route", str(WORK / "plan.json")],
                   check=True, env=env, cwd=ROOT, timeout=1000)


def main():
    global TRACE, WORK, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--section")
    parser.add_argument("--reference", type=Path, help="Staged original trace; defaults remain unchanged")
    parser.add_argument("--evidence", type=Path, help="Separate staged comparison directory")
    args = parser.parse_args()
    if args.section:
        use_section(args.section)
    if args.reference:
        TRACE = args.reference.resolve()
    if args.evidence:
        WORK = args.evidence.resolve()
        OUT = WORK / "run"
    if not WORK.resolve().is_relative_to(ROOT / "work"):
        parser.error("comparison evidence must stay under work/")
    report = dict(check="level-two-" + (args.section or "play"), status="fail", evidence=str(OUT.relative_to(ROOT)), errors=[])
    errors = report["errors"]
    reference = original()
    report.update(reference=reference["source"], startup_profile=reference["startup_profile"],
                  fresh=not args.reuse, paper=os.environ.get("PAPER") == "1")
    if report["paper"] and reference["startup_profile"] != dict(paper=True, query_ms=1):
        raise SystemExit("PAPER=1 requires an original recorded with paper startup and 1 ms queries")
    if not args.reuse:
        run_app(reference["plan"])
    try:
        app = json.loads((OUT / "level-two-route.json").read_text())
    except (OSError, ValueError):
        menu = {}
        try:
            menu = json.loads((OUT / "app-menu.json").read_text())
        except (OSError, ValueError):
            pass
        errors.append(f"app wrote no route evidence (app {menu.get('status')}: {menu.get('error')})")
        print(json.dumps(report))
        return 1
    one = frames_divergence(reference["level_one_frames"], app["level_one_frames"])
    if one:
        errors.append(f"Level 1 standing frames diverge: {one}")
    two = frames_divergence(reference["level_two_frames"], app["level_two_frames"])
    report["level_two_frames"] = dict(original=len(reference["level_two_frames"]), app=len(app["level_two_frames"]))
    if two:
        errors.append(f"Level 2 frames diverge: {two}")
    o_pick, o_lives = summaries([f["player"] for f in reference["level_two_frames"]])
    a_pick, a_lives = summaries([f["player"] for f in app["level_two_frames"]])
    report.update(pickups=a_pick, lives=a_lives)
    def respawn_timing(frames):
        return [dict(frame=i, physical_delta_ms=b['elapsed_ms'] - a['elapsed_ms'])
                for i, (a, b) in enumerate(zip(frames, frames[1:]), 1)
                if a['player']['health'] == 0 and b['player']['health'] > 0]
    expected_respawns = respawn_timing(reference["level_two_frames"])
    report["respawn_timing"] = respawn_timing(app["level_two_frames"])
    if report["respawn_timing"] != expected_respawns:
        errors.append(f"respawn physical timer deltas differ: original {expected_respawns}")
    if report["paper"] and not args.section and not any(r['physical_delta_ms'] > 17 for r in expected_respawns):
        errors.append("paper original lacks synchronous respawn timer progress")
    if (a_pick, a_lives) != (o_pick, o_lives):
        errors.append(f"pickups or lives differ: original {o_pick} {o_lives}")
    if not args.section and (not o_pick or not any(l["health"] == 0 for l in o_lives) or not any(l["health"] > 0 for l in o_lives)):
        errors.append("original route lacks the pickup, death or respawn")
    shape = lambda states: [(s["label"], s["vtable"], s.get("level")) for s in states]
    if shape(app["state_transitions"]) != shape(reference["states"]):
        errors.append(f"states {shape(app['state_transitions'])}, original {shape(reference['states'])}")
    objects = [s["object"] for s in app["state_transitions"]]
    if len(objects) != 3 or objects[0] != objects[2] or objects[0] == objects[1]:
        errors.append(f"state objects {objects}: Level 2 must reuse the Level 1 state object as the original does")
    keys = lambda ks, t0: [(k["phase"], k["key"], k["scan"], k["target"], k["milliseconds"] - t0) for k in ks]
    a_keys = keys(app["key_deliveries"], app["state_transitions"][0]["milliseconds"])
    o_keys = keys(reference["keys"], reference["states"][0]["milliseconds"])
    report["key_deliveries"] = len(a_keys)
    if a_keys != o_keys:
        errors.append(f"key deliveries {a_keys}, original {o_keys}")
    tail = lambda p: p[p.index("0x800e"):] if "0x800e" in p else []
    report["posted_after_level_complete"] = tail(app["posted_commands"])
    if tail(app["posted_commands"]) != tail(reference["posted"]):
        errors.append(f"posted commands {tail(app['posted_commands'])}, original {tail(reference['posted'])}")
    screens = [f.get("screens", []) for f in app["level_two_frames"][1:]]
    matched = sum(a == b for a, b in zip(screens, reference["screens"]))
    report["presented_frames"] = dict(original=len(reference["screens"]), app=len(screens), matched=matched,
                                      presentations=sum(map(len, screens)))
    if matched != len(reference["screens"]) or len(screens) != len(reference["screens"]):
        first = next((i for i, (a, b) in enumerate(zip(screens, reference["screens"])) if a != b), None)
        errors.append(f"presented screens differ, first at Level 2 frame {first}")
    report["end"] = {k: app["level_two_frames"][-1]["player"].get(k) for k in ("x", "y", "health", "score")}
    report["status"] = "fail" if errors else "pass"
    (WORK / "result.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
