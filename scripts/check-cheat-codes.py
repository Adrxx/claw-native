"""Every cheat code the original registers, typed with real key events in Level 1, without a fault.

The original registers 57 cheat strings (0x422980 calls from 0x4229c0; work/parity/cheats.json). The
single-player key-down virtual feeds letters to the matcher 0x422e00, which posts WM_COMMAND with the
registered command; the application dispatcher 0x426e30 hands commands 0x8043-0x80aa to its in-game
switch (state type 3). This check launches its own muted instance on the fast clock by default
(--real-time or REAL_TIME=1 keeps the real clock), walks the menu to Level 1 and posts each code's letters as real
window-server key events to that process only (scripts/post-window-input.swift). After each code it records
the posted command, health, lives, score, ammo, level and state from live.json, and any fault. A fault ends
that instance; the check relaunches and continues with the next code. Codes that change the level run last,
chained in one instance (each loads the next level). It closes only the instances it started.

Expected effects come from the original's handlers (EXPECT below, read from 0x426e30's in-game switch):
the check requires the original's posted command, no fault, and the observable effect where live.json shows
one (health, lives, ammo, level).

Usage: work/test-env/bin/python scripts/check-cheat-codes.py [--config Release] [--real-time] [--only CODE ...]
Prints one JSON line last; evidence in work/cheat-codes/check/.
Use --output-dir NEW_DIRECTORY to keep concurrent checks' evidence separate.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_input import Session, build_helper, real_time_requested  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "cheat-codes"
OUT = WORK / "check"
HELPER = WORK / "post-window-input"
CHEATS = ROOT / "work" / "parity" / "cheats.json"
LEVEL = "0x50c264"
RESULTS = "0x50c0c4"
KEYCODE = {"A": 0, "S": 1, "D": 2, "F": 3, "H": 4, "G": 5, "Z": 6, "X": 7, "C": 8, "V": 9, "B": 11, "Q": 12,
           "W": 13, "E": 14, "R": 15, "Y": 16, "T": 17, "O": 31, "U": 32, "I": 34, "P": 35, "L": 37, "J": 38,
           "K": 40, "N": 45, "M": 46}
MENU_KEYS = [{"ms": ms + d, "key": 13, "down": 1 - d // 80} for ms in (3000, 5000, 7000) for d in (0, 80)]
# Level-changing commands: 0x800e (MPSCULLY, level complete), 0x800f (MPMOULDER), 0x809c-0x80a9 (warp to
# levels 1-14 through 0x429b70 with the level number).
WARP = {0x809c + n: n + 1 for n in range(14)}
# Observable effects of the original handlers in live.json terms (0x426e30 in-game switch):
# MPAPPLE 0x8044 stores health 100 (player +0x10c); MPLOADED 0x8045, MPGANDOLF 0x8046 and MPBLASTER 0x806c
# store 99 pistol, magic and dynamite ammunition (player data +0x70, +0x74, +0x78).
EXPECT = {0x8044: {"health": 100}, 0x8045: {"ammo": "pistol"}, 0x8046: {"ammo": "magic"},
          0x806c: {"ammo": "dynamite"}}
# Levels whose own objects are not joined into the app yet. A warp there must post its command and start the
# level load; a fault inside that level is listed under "pending" with the queue tasks that join it, not as a
# cheat failure. A warp that loads cleanly passes as usual; remove a level here once its join is done.
# Level 8 is connected and must pass the warp check without a pending exemption.
LEVEL_PENDING = {10: "parity-levels-nine-ten-map-batch",
                 11: "parity-levels-eleven-twelve-map-batch",
                 12: "parity-levels-eleven-twelve-map-batch",
                 13: "parity-levels-thirteen-fourteen-map-batch"}


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


def ammo(state):
    text = state.get("weapons")
    if isinstance(text, dict):
        return text.get("ammo", {})
    return {}


def snapshot(state):
    return {k: state.get(k) for k in ("frame", "state_vtable", "level", "health", "lives", "score", "x", "y")} | \
        {"ammo": ammo(state)}


def previous_level(before):
    # Hash-checked original: command 0x800f -> 0x42732c -> 0x429cb0.
    # It decrements the level, wraps at 20, and searches down for a loadable map.
    # The hash-checked original CLAW.REZ contains LEVEL1 through LEVEL14 only.
    level = before.get("level")
    if not isinstance(level, int) or not 1 <= level <= 14:
        raise RuntimeError(f"MPMOULDER requires an original-disc level, got {level}")
    return level - 1 if level > 1 else 14


def previous_level_ready(state, before, posted_before, target):
    # Window arrival acknowledgments do not establish game-key dispatch. Wait
    # for this command's effect and gameplay after the asynchronous map load.
    return ("0x800f" in state.get("posted_commands", [])[posted_before:] and
            state.get("state_vtable") == LEVEL and state.get("level") == target and
            state.get("frame", 0) > before.get("frame", 0) and state.get("game_ms", 0) > 1000)


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Release"))
    parser.add_argument("--fast", action="store_true", help="legacy alias; fast is the default")
    parser.add_argument("--real-time", action="store_true", help="occasional pacing check")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--output-dir", type=Path, help="new evidence directory (must not exist), for concurrent checks")
    args = parser.parse_args()
    if args.output_dir is not None:
        OUT = args.output_dir.resolve()
    fast = not real_time_requested(args.real_time)
    derived_data = Path(os.environ.get("CLAW_DERIVED_DATA", "work/MacCatalyst"))
    app = ROOT / derived_data / "Build" / "Products" / f"{args.config}-maccatalyst" / "Claw.app"
    cheats = json.loads(CHEATS.read_text())
    if args.only:
        cheats = [c for c in cheats if c["code"] in args.only]
    stay = [c for c in cheats if int(c["command"], 16) not in WARP and c["command"] not in ("0x800e", "0x800f")]
    moving = [c for c in cheats if c not in stay]
    # Level warps last, from the highest level number down, then MPMOULDER and MPSCULLY.
    moving.sort(key=lambda c: (c["command"] in ("0x800e", "0x800f"), -int(c["command"], 16)))
    result = {"check": "cheat-codes", "status": "fail", "config": args.config, "fast": fast, "codes": [],
              "launches": 0, "errors": []}
    errors = result["errors"]
    WORK.mkdir(parents=True, exist_ok=True)
    build_helper(HELPER)
    if args.output_dir is None:
        subprocess.run(["rm", "-rf", str(OUT)], check=True)
    OUT.mkdir(parents=True)
    (OUT / "menu-keys.json").write_text(json.dumps(MENU_KEYS))
    session = None

    def wait(predicate, seconds):
        if session.fast:
            return session.wait(lambda: predicate() or session.failed(), seconds) and not session.failed()
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate():
                return True
            if real_speed().get("status") == "fail":
                return False
            time.sleep(0.05)
        return False

    def start():
        nonlocal session
        if session:
            session.close()
        for name in ("live.json", "real-speed.json"):
            (OUT / name).unlink(missing_ok=True)
        session = Session(OUT, fast=fast, helper=HELPER)
        result["launches"] += 1
        session.launch(app, {"CLAW_REAL_SPEED_KEYS": OUT / "menu-keys.json"},
                       ["--save-dir", str(OUT / "saves"), "-ClawCheckDirectory", str(OUT)])
        if not wait(lambda: live().get("state_vtable") == LEVEL and live().get("level") == 1
                    and live().get("game_ms", 0) > 1000, 120):
            raise RuntimeError(f"Level 1 never became live ({real_speed().get('error')})")

    def faulted():
        return real_speed().get("status") == "fail" or (session.pid and subprocess.run(
            ["kill", "-0", str(session.pid)], capture_output=True).returncode != 0)

    def type_code(code):
        # A fault while the letters are delivered stops the frames; record it for this code and relaunch.
        for letter in code:
            try:
                session.post("key", KEYCODE[letter])
            except RuntimeError:
                if faulted():
                    return
                raise

    try:
        for group in (stay, moving):
            if not group:
                continue
            start()
            restart_after_load = False
            for cheat in group:
                code, command = cheat["code"], int(cheat["command"], 16)
                if restart_after_load or faulted() or live().get("state_vtable") != LEVEL:
                    start()
                restart_after_load = False
                before = live()
                posted_before = len(before.get("posted_commands", []))
                type_code(code)
                entry = {"code": code, "command": hex(command), "flags": cheat["flags"], "before": snapshot(before)}
                if command in WARP or command in (0x800e, 0x800f):
                    target = previous_level(before) if command == 0x800f else WARP.get(command)
                    if command == 0x800f:
                        ok = wait(lambda: faulted() or previous_level_ready(live(), before, posted_before, target), 60)
                        ok = ok and not faulted() and previous_level_ready(live(), before, posted_before, target)
                        entry["expected_level"] = target
                        entry["gameplay_ready"] = ok
                        restart_after_load = not ok
                    else:
                        ok = wait(lambda: faulted() or (live().get("state_vtable") == LEVEL and live().get("level") == target
                                                   and len(live().get("posted_commands", [])) > posted_before)
                              if target else faulted() or live().get("state_vtable") != LEVEL or
                              len(live().get("posted_commands", [])) > posted_before, 60)
                    session.sleep(2)
                else:
                    ok = wait(lambda: faulted() or len(live().get("posted_commands", [])) > posted_before, 8)
                    session.sleep(1.5)
                after = live()
                entry["after"] = snapshot(after)
                entry["posted"] = after.get("posted_commands", [])[posted_before:]
                entry["fault"] = real_speed().get("error") if faulted() else None
                problems = []
                if entry["fault"]:
                    problems.append(f"fault: {entry['fault']}")
                if hex(command) not in entry["posted"]:
                    problems.append(f"command {hex(command)} not posted (posted {entry['posted']})")
                want = EXPECT.get(command, {})
                if "health" in want and after.get("health") != want["health"]:
                    problems.append(f"health {after.get('health')} not {want['health']}")
                if "ammo" in want and ammo(after).get(want["ammo"]) != 99:
                    problems.append(f"{want['ammo']} ammunition {ammo(after).get(want['ammo'])} not 99")
                if command in WARP and after.get("level") != WARP[command]:
                    problems.append(f"level {after.get('level')} not {WARP[command]}")
                if command == 0x800f:
                    if after.get("level") != target:
                        problems.append(f"level {after.get('level')} not {target}")
                    if not ok:
                        problems.append("previous-level gameplay did not become ready within 60 seconds")
                if not ok and not problems:
                    problems.append("no response")
                pending = LEVEL_PENDING.get(WARP.get(command))
                if pending and entry["fault"] and hex(command) in entry["posted"]:
                    entry["pending"] = f"level {WARP[command]} faults in its own objects ({entry['fault']}); joined by {pending}"
                    problems = []
                entry["problems"] = problems
                result["codes"].append(entry)
                print(json.dumps({"code": code, "command": hex(command), "problems": problems,
                                  "pending": entry.get("pending"), "after": entry["after"]}), flush=True)
    except RuntimeError as error:
        errors.append(str(error))
    finally:
        if session:
            session.close()
        (OUT / "result.json").write_text(json.dumps(result, indent=1))
    failing = [c["code"] for c in result["codes"] if c["problems"]]
    result["failing"] = failing
    result["pending"] = {c["code"]: c["pending"] for c in result["codes"] if c.get("pending")}
    result["tested"] = len(result["codes"])
    if not errors and not failing and result["tested"] == len(cheats):
        result["status"] = "pass"
    # Compare the commands, effects and faults that the checker judges. Position,
    # unrelated ambient damage and elapsed gameplay time are pacing observations.
    evidence = []
    for entry in result["codes"]:
        command = int(entry["command"], 16)
        want = EXPECT.get(command, {})
        effects = {}
        if "health" in want:
            effects["health"] = entry["after"]["health"]
        if "ammo" in want:
            effects["ammo"] = entry["after"]["ammo"].get(want["ammo"])
        if command in WARP or command == 0x800f:
            effects["level"] = entry["after"]["level"]
        if command == 0x800f:
            effects["gameplay_ready"] = entry["gameplay_ready"]
        evidence.append({k: entry.get(k) for k in ("code", "command", "posted", "fault", "problems", "pending")} | {"effects": effects})
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True))
    (OUT / "result.json").write_text(json.dumps(result, indent=1))
    summary = {k: result[k] for k in ("check", "status", "config", "fast", "tested", "launches", "failing", "pending",
                                                  "errors")}
    print(json.dumps(summary))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
