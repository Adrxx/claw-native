"""Pistol, magic and dynamite fire in Level 1 on real key presses, with the original's default keys.

The original's default bindings (0x430d80, polled by 0x430ec0 through GetAsyncKeyState):
arrows move, Space jumps, Control attacks, Alt (Option) fires the selected weapon, Shift
cycles pistol, magic, dynamite, Z, and 1 to 4 select a weapon. Windows reports Alt as
WM_SYSKEYDOWN, so the game sees it only through GetAsyncKeyState.

This check launches its own muted instance on the real clock (the debug-only real-speed log
gives the live player state each frame; its key script only walks the menu to Level 1) and
posts real window-server key events to that process only (scripts/post-window-input.swift,
CGEventPostToPid), the path a physical keyboard takes; it never calls the app's key handler.
In Level 1 it fires the pistol with Option, selects magic with 2 and fires it, cycles to
dynamite with Shift and throws it (held, then released), holds Option with the right arrow,
and selects the pistol again with 1. Each shot must take exactly one round of that weapon's
ammo and run that weapon's projectile logic. It closes only the instance it started.

Usage: work/test-env/bin/python scripts/check-weapon-keys.py [--config Debug] [--real-time]
Runs on the fast clock through the app's input gate (scripts/real_input.py); --real-time (or REAL_TIME=1)
keeps the display timer and wall-clock waits for pacing checks.
Prints one JSON line last.
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
WORK = ROOT / "work" / "weapon-keys"
OUT = WORK / "check"
HELPER = WORK / "post-window-input"
# Mac virtual key codes.
OPTION, SHIFT, ONE, TWO, RIGHT = 58, 56, 18, 19, 124
MENU_KEYS = [{"ms": ms + d, "key": 13, "down": 1 - d // 80} for ms in (3000, 5000, 7000) for d in (0, 80)]


def claw_pids():
    found = subprocess.run(["pgrep", "-x", "Claw"], capture_output=True, text=True).stdout.split()
    return {int(p) for p in found}


def live():
    try:
        return json.loads((OUT / "live.json").read_text())
    except (OSError, ValueError):
        return {}


def weapons():
    return live().get("weapons", {})


def wait(predicate, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Debug"))
    parser.add_argument("--real-time", action="store_true", help="the display timer and wall-clock waits (pacing check)")
    args = parser.parse_args()
    fast = not real_time_requested(args.real_time)
    session = Session(OUT, fast=fast, helper=HELPER)
    wait = session.wait
    app = ROOT / "work" / "MacCatalyst" / "Build" / "Products" / f"{args.config}-maccatalyst" / "Claw.app"
    result = {"check": "weapon-keys", "status": "fail", "config": args.config, "fast": fast, "errors": []}
    errors = result["errors"]
    WORK.mkdir(parents=True, exist_ok=True)
    build_helper(HELPER)
    subprocess.run(["rm", "-rf", str(OUT)], check=True)
    OUT.mkdir(parents=True)
    (OUT / "menu-keys.json").write_text(json.dumps(MENU_KEYS))
    control = session.control
    before = claw_pids()
    pid = None
    steps = []
    posts = []

    def post(*key):
        posted = session.post("press", *key)
        posts.append({"key": list(key), "frontmost": posted.get("frontmost"), "status": posted.get("status")})
        return posted

    def tap(code, flags=None, hold=0.15):
        post(code, "down", *([flags] if flags else []))
        session.sleep(hold)
        held = weapons().get("held_keys", [])
        post(code, "up", *([flags] if flags else []))
        return held

    def snapshot(name):
        with control.open("a") as f:
            f.write(f"s {name}\n")
        w = weapons()
        steps.append({"step": name, "weapon": w.get("weapon"), "ammo": w.get("ammo"),
                      "projectile_invokes": w.get("projectile_invokes"), "held_keys": w.get("held_keys"),
                      "frame": live().get("frame")})
        return w

    try:
        try:
            pid = session.launch(app, {"CLAW_REAL_SPEED_KEYS": OUT / "menu-keys.json"}, ["-ClawCheckDirectory", str(OUT)])
        except RuntimeError as error:
            errors.append(f"instance did not start: {error}")
            return result
        result["pid"] = pid
        if not wait(lambda: weapons().get("weapon") is not None and live().get("game_ms", 0) > 1500, 90):
            errors.append("Level 1 player never became live")
            return result
        session.sleep(1.5)
        start = snapshot("start")
        if start.get("weapon") != 1:
            errors.append(f"Level 1 starts with weapon {start.get('weapon')}, not the pistol")

        def fired(name, weapon, ammo_key, hold):
            base = weapons()
            post(OPTION, "down")
            session.sleep(min(hold, 0.1))
            during = weapons().get("held_keys", [])
            session.sleep(max(hold - 0.1, 0))
            post(OPTION, "up")
            session.sleep(1.5)
            after = snapshot(name)
            steps[-1]["held_during_option"] = during
            if 0x12 not in during:
                errors.append(f"{name}: Option did not reach GetAsyncKeyState (held {during})")
            if after.get("weapon") != weapon:
                errors.append(f"{name}: weapon {after.get('weapon')} after firing, expected {weapon}")
            if (base.get("ammo") or {}).get(ammo_key, 0) - (after.get("ammo") or {}).get(ammo_key, 0) != 1:
                errors.append(f"{name}: {ammo_key} ammo {base.get('ammo')} -> {after.get('ammo')}, expected one round")
            invokes = lambda w: (w.get("projectile_invokes") or {}).get(ammo_key, 0)
            steps[-1]["projectile_ran"] = invokes(after) > invokes(base)
            if invokes(after) <= invokes(base):
                errors.append(f"{name}: no {ammo_key} projectile logic ran")
            if after.get("held_keys"):
                errors.append(f"{name}: keys still held after release {after.get('held_keys')}")

        fired("pistol", 1, "pistol", 0.15)
        held = tap(TWO)
        session.sleep(0.8)
        if 0x32 not in held:
            errors.append(f"2 did not reach GetAsyncKeyState (held {held})")
        if snapshot("select-2").get("weapon") != 2:
            errors.append("2 did not select magic")
        fired("magic", 2, "magic", 0.15)
        held = tap(SHIFT)
        session.sleep(0.8)
        if 0x10 not in held:
            errors.append(f"Shift did not reach GetAsyncKeyState (held {held})")
        if snapshot("shift").get("weapon") != 3:
            errors.append("Shift did not cycle from magic to dynamite")
        fired("dynamite", 3, "dynamite", 0.6)
        held = tap(ONE)
        session.sleep(0.8)
        if 0x31 not in held:
            errors.append(f"1 did not reach GetAsyncKeyState (held {held})")
        if snapshot("select-1").get("weapon") != 1:
            errors.append("1 did not select the pistol")
        # A key pressed while Option is held is WM_SYSKEYDOWN: it must still reach the poller.
        post(OPTION, "down")
        session.sleep(0.05)
        post(RIGHT, "down", "option")
        session.sleep(0.15)
        held = weapons().get("held_keys", [])
        post(RIGHT, "up", "option")
        post(OPTION, "up")
        session.sleep(1.5)
        snapshot("option-right")
        steps[-1]["held_during"] = held
        if not {0x12, 0x27} <= set(held):
            errors.append(f"Option with the right arrow held {held}, expected 18 and 39")
        if weapons().get("held_keys"):
            errors.append(f"keys stuck after Option and the right arrow: {weapons().get('held_keys')}")
        session.sleep(0.3)
        return result
    finally:
        result["steps"] = steps
        result["posts_not_frontmost"] = [p for p in posts if not p["frontmost"]]
        if pid and pid not in before:
            session.close()
        if session.retries:
            errors.append(f"lost window events posted again {session.retries}")
        # Evidence compared between the fast and real-time runs (scripts/compare-real-input.py): no frame numbers.
        (OUT / "evidence.json").write_text(json.dumps([{k: v for k, v in st.items() if k not in ("frame", "projectile_invokes")} for st in steps],
                                                      indent=1, sort_keys=True))
        if not errors and steps:
            result["status"] = "pass"


if __name__ == "__main__":
    out = main()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["status"] == "pass" else 1)
