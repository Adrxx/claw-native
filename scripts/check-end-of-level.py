"""Level 1 ends with the MPSCULLY cheat, the results screen shows, and Return continues into Level 2.

The owner's route (2026-10-21): Level 1 is finished with the original's own MPSCULLY
level-skip cheat, which posts the same level-complete command 0x800e as the end-of-level
gem; after the results (booty) screen the original continues into Level 2.

This check launches its own muted instance on the selected clock with a scratch --save-dir
(the real-speed key script only walks the menu to Level 1), then posts real window-server
key events to that process only (scripts/post-window-input.swift, CGEventPostToPid): the
eight letters of MPSCULLY, then Return whenever the results state has waited 12 seconds,
as the original trace does (Tests/NativeEndOfLevel/trace.py). It compares the app with
the original trace work/end-of-level-map/trace.json at the state boundaries: the state
sequence Level 1 (0x50c264) -> results (0x50c0c4) -> Level 2 (0x50c264, level 2, the same
state object), the posted commands from 0x800e on, the Return deliveries to the results
state, the Level 2 start position, and the presented results and Level 2 frames (indexed
pixel and palette hashes) against the original's presentations. Screenshots go to
work/end-of-level/. It closes only the instance it started.

Usage: work/test-env/bin/python scripts/check-end-of-level.py [--config Release] [--real-time]
Runs on the fast clock through the app's input gate (scripts/real_input.py); --real-time (or REAL_TIME=1)
keeps the display timer and wall-clock waits for pacing checks.
Prints one JSON line last.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_input import Session, build_helper, real_time_requested  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import read_trace, stored_path
WORK = ROOT / "work" / "end-of-level"
OUT = WORK / "check"
HELPER = WORK / "post-window-input"
TRACE = ROOT / "work" / "end-of-level-map" / "trace.json"
# Mac virtual key codes for M P S C U L L Y, and Return.
CHEAT = [("M", 46), ("P", 35), ("S", 1), ("C", 8), ("U", 32), ("L", 37), ("L", 37), ("Y", 16)]
RETURN = 36
LEVEL, RESULTS = "0x50c264", "0x50c0c4"
MENU_KEYS = [{"ms": ms + d, "key": 13, "down": 1 - d // 80} for ms in (3000, 5000, 7000) for d in (0, 80)]


def claw_pids():
    found = subprocess.run(["pgrep", "-x", "Claw"], capture_output=True, text=True).stdout.split()
    return {int(p) for p in found}


def live():
    try:
        return json.loads((OUT / "live.json").read_text())
    except (OSError, ValueError):
        return {}


def real_speed():
    try:
        return json.loads((OUT / "real-speed.json").read_text())
    except (OSError, ValueError):
        return {}


SESSION = None


def wait(predicate, seconds):
    if SESSION.fast:
        return SESSION.wait(lambda: predicate() or SESSION.failed(), seconds) and not SESSION.failed()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        if real_speed().get("status") == "fail":
            return False
        time.sleep(0.05)
    return False


def original(trace_path):
    """The original route's boundaries, taken once from the large trace."""
    WORK.mkdir(parents=True, exist_ok=True)
    # Keep staged references out of the default reference's derived cache.
    cache = WORK / ("original-boundaries.json" if trace_path == TRACE else "paper-original-boundaries.json")
    with stored_path(trace_path).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved.get('reference_sha256') == digest and (os.environ.get('PAPER') != '1'
                or saved.get('startup_profile') == dict(paper=True, query_ms=1)):
            return saved
    t = read_trace(trace_path)
    if t.get('status') != 'pass' or t.get('stop') is not None:
        raise ValueError('original trace did not finish')
    if os.environ.get('PAPER') == '1' and (t.get('startup_profile') != dict(paper=True, query_ms=1)
            or not t.get('startup_queries', {}).get('count')
            or t['startup_queries']['increments'] != {'1': t['startup_queries']['count']}
            or (t.get('resumed_checkpoint') and
                (t.get('parent_checkpoint') or {}).get('startup_profile') != dict(paper=True, query_ms=1))):
        raise ValueError('PAPER=1 requires original paper startup and verified parent provenance')
    posted = [hex(e["wparam"]) for e in t["physical_events"] if e.get("service") == "PostMessageA"]
    screens = {}
    for p in t["presentations"]:
        phase = p["phase"]
        kind = "results" if phase.startswith("results-") or phase.startswith("command-807c") else \
            "level-two" if phase.startswith("level-two") else None
        if kind:
            screens.setdefault(kind, []).append([p["pixels_sha256"], p["palette_sha256"]])
    first_two = next(p for p in t["presentations"] if p["phase"].startswith("level-two"))
    data = {"reference_sha256": digest, "reference": str(trace_path),
            "startup_profile": t.get('startup_profile'),
            "posted": posted, "states": t["state_transitions"],
            "returns": [k for k in t["key_deliveries"] if k["phase"].startswith("results-key-return")],
            "level_two_start": t["level_two_frames"][0]["player"], "screens": screens,
            "first_level_two_screen": [first_two["pixels_sha256"], first_two["palette_sha256"]]}
    cache.write_text(json.dumps(data))
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Release"))
    parser.add_argument("--real-time", action="store_true", help="the display timer and wall-clock waits (pacing check)")
    parser.add_argument('--original', type=Path, default=TRACE)
    args = parser.parse_args()
    global SESSION
    fast = not real_time_requested(args.real_time)
    SESSION = session = Session(OUT, fast=fast, helper=HELPER)
    app = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT / 'work' / 'MacCatalyst')).resolve() / 'Build' / 'Products' / f'{args.config}-maccatalyst' / 'Claw.app'
    result = {"check": "end-of-level", "status": "fail", "config": args.config, "fast": fast, "errors": []}
    errors = result["errors"]
    WORK.mkdir(parents=True, exist_ok=True)
    reference = original(args.original)
    result.update(original=reference['reference'], original_sha256=reference['reference_sha256'],
                  startup_profile=reference['startup_profile'])
    build_helper(HELPER)
    subprocess.run(["rm", "-rf", str(OUT)], check=True)
    OUT.mkdir(parents=True)
    (OUT / "menu-keys.json").write_text(json.dumps(MENU_KEYS))
    before = claw_pids()
    pid = None
    posts = []
    states = []
    shots = {}

    def post(code):
        posted = session.post("key", code)
        posts.append({"key": code, "frontmost": posted.get("frontmost"), "status": posted.get("status"),
                      "state_vtable": live().get("state_vtable"), "frame": live().get("frame")})

    def snapshot(name):
        record = session.mark(name)
        if record is not None:
            shots[name] = record

    def boundary(label):
        now = live()
        states.append({"label": label, "frame": now.get("frame"), "object": now.get("app_state"),
                       "vtable": now.get("state_vtable"), "level": now.get("level"),
                       "x": now.get("x"), "y": now.get("y"), "health": now.get("health")})
        return now

    try:
        try:
            pid = session.launch(app, {"CLAW_REAL_SPEED_KEYS": OUT / "menu-keys.json"},
                                 ["--new-game-clock", "--save-dir", str(OUT / "saves"), "-ClawCheckDirectory", str(OUT)])
        except RuntimeError as error:
            errors.append(f"instance did not start: {error}")
            return result
        result["pid"] = pid
        if not wait(lambda: live().get("state_vtable") == LEVEL and live().get("level") == 1
                    and live().get("game_ms", 0) > 1000, 120):
            errors.append(f"Level 1 never became live (live {live().get('state_vtable')}, {real_speed().get('error')})")
            return result
        level_one = boundary("level-one-loaded")
        snapshot("level-one")
        for letter, code in CHEAT:
            post(code)
        if not wait(lambda: live().get("state_vtable") == RESULTS, 20):
            errors.append(f"MPSCULLY did not reach the results state (state {live().get('state_vtable')}, "
                          f"posted {live().get('posted_commands')}, {real_speed().get('error')})")
            return result
        boundary("after-level-complete-command")
        session.sleep(3)
        snapshot("results")
        # As the original route: a state unchanged for 12 seconds is waiting for the player; one Return.
        returns = 0
        for _ in range(10):
            if wait(lambda: live().get("state_vtable") != RESULTS, 12):
                break
            if real_speed().get("status") == "fail":
                break
            snapshot(f"results-before-return-{returns + 1}")
            post(RETURN)
            returns += 1
        result["returns"] = returns
        if not wait(lambda: live().get("state_vtable") == LEVEL and live().get("level") == 2, 60):
            errors.append(f"results did not continue into Level 2 (state {live().get('state_vtable')}, level "
                          f"{live().get('level')}, {real_speed().get('error')})")
            return result
        level_two = boundary("level-two-loaded")
        snapshot("level-two-start")
        session.sleep(5)
        boundary("level-two-played")
        snapshot("level-two-5s")
        final = live()
        if final.get("state_vtable") != LEVEL or final.get("level") != 2:
            errors.append("Level 2 did not stay live for 5 seconds")
        # Original comparison at the state boundaries.
        o_states = reference["states"]
        if level_one.get("app_state") != level_two.get("app_state"):
            errors.append(f"Level 2 state object {level_two.get('app_state')} is not the Level 1 one "
                          f"{level_one.get('app_state')} (the original reuses {o_states[0]['object']})")
        posted = final.get("posted_commands", [])
        tail = posted[posted.index("0x800e"):] if "0x800e" in posted else []
        o_posted = reference["posted"]
        o_tail = o_posted[o_posted.index("0x800e"):]
        result["posted_after_level_complete"] = {"app": tail, "original": o_tail}
        if tail != o_tail:
            errors.append(f"posted commands from 0x800e {tail}, original {o_tail}")
        o_returns = len(reference["returns"])
        result["results_returns"] = {"app": returns, "original": o_returns}
        if returns != o_returns:
            errors.append(f"results took {returns} Return presses, the original {o_returns}")
        o_start = reference["level_two_start"]
        start = {k: level_two.get(k) for k in ("x", "y", "health", "level")}
        result["level_two_start"] = {"app": start, "original": {k: o_start[k] for k in start}}
        if start != {k: o_start[k] for k in start}:
            errors.append(f"Level 2 starts at {start}, original {o_start}")
        # Presented frames: every results snapshot must be a screen the original presented.
        frames = {}
        for name, shot in sorted(shots.items()):
            screen = [shot["pixels_sha256"], shot["palette_sha256"]]
            kind = "results" if name.startswith("results") else "level-two" if name.startswith("level-two") else None
            frames[name] = {"original_presented": screen in reference["screens"].get(kind, []) if kind else None,
                            "pixels_sha256": shot["pixels_sha256"][:16], "png": f"work/end-of-level/check/{name}.png"}
        result["frames"] = frames
        matched = [n for n, f in frames.items() if n.startswith("results") and f["original_presented"]]
        if not matched:
            errors.append("no results frame equals a frame the original presented")
        return result
    finally:
        result["states"] = states
        result["original_states"] = [{k: s.get(k) for k in ("label", "object", "vtable", "level")} for s in reference["states"]]
        result["posts_not_frontmost"] = sum(1 for p in posts if not p["frontmost"])
        result["posts"] = posts
        if real_speed().get("status") == "fail":
            errors.append(f"app failed: {real_speed().get('error')} at frame {real_speed().get('failing_frame')}")
        if pid and pid not in before:
            session.close()
        # Compare the same game frames, not just the eventual results state.
        # The final Y is consumed in one frame and its posted 0x800e command
        # is drained in the next; the transition must not move with the clock.
        frames = real_speed().get("frames", [])
        final_key = next((f for f in frames if f.get("received_key") == 89 and f.get("down")), None)
        cheat_frames = []
        if final_key:
            first = final_key["frame"]
            cheat_frames = [{"offset": f["frame"] - first, "state_vtable": "0x" + f["state_vtable"]}
                            for f in frames if "state_vtable" in f and first <= f["frame"] < first + 4]
        expected_frames = [{"offset": i, "state_vtable": LEVEL if i == 0 else RESULTS} for i in range(4)]
        result["cheat_frames"] = cheat_frames
        if cheat_frames != expected_frames:
            errors.append(f"final Y frame states {cheat_frames}, expected {expected_frames}")
        if len(posts) < 8 or posts[7].get("state_vtable") != RESULTS:
            errors.append("final Y returned before its held frames completed the results transition")
        result["retries"] = session.retries  # dropped window events posted again (scripts/real_input.py)
        if not errors and states:
            result["status"] = "pass"
        (WORK / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True))
        # Evidence compared between the fast and real-time runs (scripts/compare-real-input.py): no frame numbers.
        (OUT / "evidence.json").write_text(json.dumps({
            # Heap addresses and the pixels of frames picked by wall-clock moments vary between any two
            # real-time runs; the check judges the state object's identity and whether the original presented it.
            "states": [dict({k: v for k, v in s.items() if k not in ("frame", "object")},
                            same_object=s.get("object") == states[0].get("object")) for s in states],
            "posts": [{k: p.get(k) for k in ("key", "status", "state_vtable")} for p in posts],
            "cheat_frames": cheat_frames,
            "returns": result.get("returns"), "posted_after_level_complete": result.get("posted_after_level_complete"),
            "frames": {k: v.get("original_presented") for k, v in result.get("frames", {}).items()},
            "status": result["status"]}, indent=1, sort_keys=True))


if __name__ == "__main__":
    out = main()
    print(json.dumps({k: out[k] for k in out if k not in ("posts", "states", "original_states")}, sort_keys=True))
    raise SystemExit(0 if out["status"] == "pass" else 1)
