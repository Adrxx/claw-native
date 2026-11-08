"""The original's keyboard accelerators reach the game on real key presses in Level 1.

The original loads its main window's accelerator table (RT_ACCELERATOR "CLAW", 58
entries) at window creation (0x4b8b13) and its pump 0x4b8d10 passes every message to
TranslateAcceleratorA before translating and dispatching it anyway. The window's
WM_COMMAND handler 0x4b8810 hands (HIWORD, LOWORD, lParam) to 0x426e30. Reachable in
single-player Level 1 (state type 3): '-' (0x801c) and '=' or keypad + (0x801b) step
the viewport through 0x429e30/0x429e70 unless paused; Pause (0x8007) toggles
application +0x0c; F1 (0x8035) opens Help and Escape returns to the game. Tab, Shift+Tab, F9 and F10 are guarded by
state type 4, which no single-player state returns, so they change nothing. F2-F8
(0x42aa90) have the same guard, verified here against the hash-checked original.
Control+D (0x8070, admitted screen dump 0x495be0) increments the persisted count
and writes CLAWnnnn.BMP. No entry uses Alt+Return; Alt keys arrive
as WM_SYSKEYDOWN, whose window handler 0x4b8890 is inert.

The check launches its own muted instance on the real clock (CLAW_REAL_SPEED_LOG gives
the live state each frame; its key script only walks the menu to Level 1) and posts
real window-server key events to that process only (scripts/post-window-input.swift),
the path a physical keyboard takes. It closes only the instance it started.

Usage: work/test-env/bin/python scripts/check-accelerators.py [--config Release] [--real-time]
Runs on the fast clock through the app's input gate (scripts/real_input.py); --real-time (or REAL_TIME=1)
keeps the display timer and wall-clock waits for pacing checks.
Prints one JSON line last.
"""
import argparse
import hashlib
import json
import os
import random
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_input import Session, build_helper, real_time_requested  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WORK = ROOT / "work" / "accelerators"
OUT = WORK / "check"
HELPER = WORK / "post-window-input"
# Mac virtual key codes.
MINUS, EQUAL, PAD_PLUS, PAD_MINUS = 27, 24, 69, 78
F1, F2, F9, F15, TAB, RETURN, ESCAPE = 122, 120, 101, 113, 48, 36, 53
ONE, CONTROL, OPTION, SHIFT, RIGHT, D = 18, 59, 58, 56, 124, 2
GAMEPLAY, HELP = "0x50c264", "0x50c11c"
MENU_KEYS = [{"ms": ms + d, "key": 13, "down": 1 - d // 80} for ms in (3000, 5000, 7000) for d in (0, 80)]


def original_function_key_guard():
    """Execute the real helper for every slot and non-multiplayer state type."""
    from Tests.clawparity.env import Env
    from Tests.clawparity.program import claw
    from Tests.clawparity.fixtures import returns
    program = claw()
    count = 0
    for kind in (None, 0, 1, 2, 3, 5, 6, 7, 8, 0xffffffff):
        for slot in range(7):
            env = Env(program)
            env._begin_case(random.Random(0))
            app = env.object(0x140, "application", fill=0x79)
            state = 0
            if kind is not None:
                state = env.object(0x40, "state", fill=0x39)
                vt = env.object(0x20, "state-vtable", fill=0x5b)
                env.put(state, vt)
                env.put(vt + 0x10, env.stub("state-type", "thiscall", 0, returns(kind)))
            env.put(app + 0x2c, state)
            env._freeze()
            outcome = env.run_original(0x42aa90, app, [slot], check_objects=True)
            assert outcome.completed and not outcome.errors and outcome.eax == 0, (kind, slot, outcome.errors)
            assert outcome.heap == env._frozen[0]
            assert outcome.image == env._frozen[1][env.data_offset:]
            count += 1
    return {"status": "pass", "cases": count, "program_sha256": program.sha256}


def original_bitmap(pixels, width, height, rgb):
    """Run the unchanged original BMP writer with native file/Lock services.

    No game or bitmap decisions are stubbed. Only CFile lifetime/I/O and the
    physical DirectDraw Lock/Unlock boundary are supplied here.
    """
    from Tests.clawparity.env import Env
    from Tests.clawparity.program import claw
    from Tests.clawparity.fixtures import returns
    env = Env(claw(), heap_bytes=max(0x40000, width*height+0x10000))
    writes = []
    env.fixture(0x4b9730, "thiscall", 1, lambda e, c: storage, "surface Lock")
    env.fixture(0x4f72c9, "thiscall", 0, lambda e, c: c.receiver, "CFile constructor")
    env.fixture(0x4f7448, "thiscall", 3, returns(1), "CFile Open")
    env.fixture(0x4f75aa, "thiscall", 2,
                lambda e, c: writes.append(e.read(c.arguments[0], c.arguments[1])) or 0, "CFile Write")
    env.fixture(0x4f7369, "thiscall", 0, returns(0), "CFile destructor")
    env._begin_case(random.Random(0))
    surface = env.object(0xbc, "surface", fill=0)
    vt = env.object(0x20, "surface-vtable", fill=0)
    interface = env.object(4, "DirectDraw")
    com = env.object(0x84, "DirectDraw-vtable", fill=0)
    storage = env.object(len(pixels), "pixels", data=pixels)
    palette = env.object(0x10, "palette", fill=0)
    entries = env.object(1024, "palette-entries", data=bytes(c for i in range(256) for c in (*rgb[i*3:i*3+3], 0)))
    filename = env.object(16, "filename", data=b"CLAW0001.BMP\0")
    env.put(surface, vt)
    env.put(vt+0x14, env.stub("surface valid", "thiscall", 0, returns(1)))
    env.put(surface+8, interface)
    env.put(surface+0x14, height, width, width)
    env.put(surface+0xa4, 8)
    env.put(interface, com)
    env.put(com+0x80, env.stub("DirectDraw Unlock", "stdcall", 2, returns(0)))
    env.put(palette+0xc, entries)
    env._freeze()
    outcome = env.run_original(0x4b9e10, surface, [filename, 1, palette], check_objects=True)
    assert outcome.completed and not outcome.errors and outcome.eax == 1, outcome.errors
    return b"".join(writes)


def check_bitmap(path, event):
    data = path.read_bytes()
    signature, size, reserved1, reserved2, offset = struct.unpack_from("<2sIHHI", data)
    header, width, height, planes, bits, compression = struct.unpack_from("<IiiHHI", data, 14)
    assert (signature, size, reserved1, reserved2, offset) == (b"BM", len(data), 0, 0, 1078)
    assert (header, width, height, planes, bits, compression) == (40, event["width"], event["height"], 1, 8, 0)
    assert len(data) == 1078 + width * height
    pixels = b"".join(data[1078+y*width:1078+(y+1)*width] for y in reversed(range(height)))
    rgb = bytes(c for i in range(256) for c in (data[54+i*4+2], data[54+i*4+1], data[54+i*4]))
    assert hashlib.sha256(pixels).hexdigest() == event["pixels_sha256"], "BMP rows differ from captured surface"
    assert hashlib.sha256(rgb).hexdigest() == event["rgb_sha256"], "BMP colors differ from source palette"
    assert len(set(pixels)) > 1, "blank screen dump"
    reference = original_bitmap(pixels, width, height, rgb)
    # The old writer never initializes RGBQUAD's unused reserved bytes. Compare
    # all defined bytes; native files make the reserved byte zero.
    defined = bytearray(b"\1" * len(data))
    defined[57:1078:4] = b"\0" * 256
    assert len(reference) == len(data)
    assert all(a == b for a, b, keep in zip(data, reference, defined) if keep), "BMP differs from original writer"


def claw_pids():
    found = subprocess.run(["pgrep", "-x", "Claw"], capture_output=True, text=True).stdout.split()
    return {int(p) for p in found}


def live():
    try:
        return json.loads((OUT / "live.json").read_text())
    except (OSError, ValueError):
        return {}


def wait(predicate, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Release"))
    parser.add_argument("--real-time", action="store_true", help="the display timer and wall-clock waits (pacing check)")
    args = parser.parse_args()
    fast = not real_time_requested(args.real_time)
    session = Session(OUT, fast=fast, helper=HELPER)
    wait = session.wait
    derived = Path(os.environ.get("CLAW_DERIVED_DATA", ROOT / "work" / "MacCatalyst"))
    app = derived / "Build" / "Products" / f"{args.config}-maccatalyst" / "Claw.app"
    result = {"check": "accelerators", "status": "fail", "config": args.config, "fast": fast, "errors": []}
    errors = result["errors"]
    result["original_function_key_guard"] = original_function_key_guard()
    WORK.mkdir(parents=True, exist_ok=True)
    build_helper(HELPER)
    subprocess.run(["rm", "-rf", str(OUT)], check=True)
    OUT.mkdir(parents=True)
    (OUT / "menu-keys.json").write_text(json.dumps(MENU_KEYS))
    control = session.control
    before = claw_pids()
    pid = None
    steps = []

    def post(*key):
        session.post("press", *key)

    def tap(code, flags=None, hold=0.12):
        post(code, "down", *([flags] if flags else []))
        session.sleep(hold)
        post(code, "up", *([flags] if flags else []))

    def chord(modifier, flag, code):
        post(modifier, "down")
        session.sleep(0.05)
        tap(code, flag)
        post(modifier, "up")

    def shot(name):
        """The presented indexed pixels' hash of the frame saved for step `name`."""
        path = OUT / f"{name}.json"
        wait(path.exists, 3)
        try:
            return json.loads(path.read_text()).get("pixels_sha256")
        except (OSError, ValueError):
            return None

    def step(name, action, expect_commands, settle=0.8):
        """Run `action`, then compare the newly translated accelerators with `expect_commands`
        (command, delivered) and return (before, after) live states."""
        first = live()
        count = len(first.get("accelerators", []))
        action()
        session.sleep(settle)
        with control.open("a") as f:
            f.write(f"s {name}\n")
        last = live()
        new = [(c["command"], c["delivered"]) for c in last.get("accelerators", [])[count:]]
        steps.append({"step": name, "accelerators": new, "viewport": [first.get("app_viewport"), last.get("app_viewport")],
                      "paused": [first.get("app_paused"), last.get("app_paused")],
                      "state": [first.get("state_vtable"), last.get("state_vtable")],
                      "game_ms": [first.get("game_ms"), last.get("game_ms")],
                      "held_keys": (last.get("weapons") or {}).get("held_keys"), "frame": last.get("frame")})
        if new != expect_commands:
            errors.append(f"{name}: translated {new}, expected {expect_commands}")
        return first, last

    try:
        try:
            pid = session.launch(app, {"CLAW_REAL_SPEED_KEYS": OUT / "menu-keys.json"},
                                 ["-ClawCheckDirectory", str(OUT), "--screen-dump-dir", str(OUT / "dumps"),
                                  "--settings-dir", str(OUT / "settings")])
        except RuntimeError as error:
            errors.append(f"instance did not start: {error}")
            return result
        result["pid"] = pid
        if not wait(lambda: live().get("state_vtable") == GAMEPLAY and live().get("game_ms", 0) > 1500, 90):
            errors.append("Level 1 never became live")
            return result
        session.sleep(1.5)
        start = live().get("app_viewport")
        result["initial_viewport"] = start
        if not isinstance(start, int) or not 1 <= start <= 10:
            errors.append(f"viewport size step {start} outside 1..10")
            return result

        # '-' shrinks (0x429e30: only above 1), '=' and keypad + grow (0x429e70: only below 10).
        def expect_view(name, first, last, delta):
            want = min(10, max(1, first.get("app_viewport") + delta))
            if last.get("app_viewport") != want:
                errors.append(f"{name}: viewport {first.get('app_viewport')} -> {last.get('app_viewport')}, expected {want}")
        expect_view("minus", *step("minus", lambda: tap(MINUS), [("0x801c", 1)]), -1)
        expect_view("equal", *step("equal", lambda: tap(EQUAL), [("0x801b", 1)]), 1)
        expect_view("keypad-minus", *step("keypad-minus", lambda: tap(PAD_MINUS), [("0x801c", 1)]), -1)
        expect_view("keypad-plus", *step("keypad-plus", lambda: tap(PAD_PLUS), [("0x801b", 1)]), 1)
        # Shift+'=' types '+', which no entry names.
        expect_view("shift-equal", *step("shift-equal", lambda: chord(SHIFT, "shift", EQUAL), []), 0)

        # Pause toggles +0x0c (0x42a570); the viewport keys are refused while paused (0x42afd0).
        first, last = step("pause", lambda: tap(F15), [("0x8007", 1)])
        if (first.get("app_paused"), last.get("app_paused")) != (0, 1):
            errors.append(f"pause: +0x0c {first.get('app_paused')} -> {last.get('app_paused')}, expected 0 -> 1")
        def hold_right():
            post(RIGHT, "down")
            session.sleep(0.6)
            post(RIGHT, "up")
        first, last = step("paused-right", hold_right, [])
        result["paused_picture"] = [shot("pause"), shot("paused-right")]
        paused_picture, held_picture = result["paused_picture"]
        if not paused_picture or paused_picture != held_picture:
            errors.append("paused-right: the presented picture changed or was not captured")
        # The original's idle handler 0x4b9070 skips the application frame while
        # window +0x244 is clear. Real right-arrow delivery must leave Claw still.
        result["paused_moved"] = [first.get("x"), last.get("x")]
        for field in ("x", "y", "game_ms"):
            prior_value, current_value = first.get(field), last.get(field)
            if not isinstance(prior_value, (int, float)) or prior_value != current_value:
                errors.append(f"paused-right: {field} {prior_value} -> {current_value}, expected no change")
        if (first.get("app_paused"), last.get("app_paused")) != (1, 1):
            errors.append("paused-right: Pause did not remain active")
        expect_view("paused-minus", *step("paused-minus", lambda: tap(MINUS), [("0x801c", 1)]), 0)
        first, last = step("resume", lambda: tap(F15), [("0x8007", 1)])
        if last.get("app_paused") != 0:
            errors.append(f"resume: +0x0c {last.get('app_paused')}")

        # Guarded by state type 4: translated and delivered, no visible change.
        for name, action, command in (("tab", lambda: tap(TAB), "0x803c"),
                                      ("shift-tab", lambda: chord(SHIFT, "shift", TAB), "0x803d"),
                                      ("f9", lambda: tap(F9), "0x8082")):
            first, last = step(name, action, [(command, 1)])
            if last.get("state_vtable") != GAMEPLAY or last.get("app_paused") != 0 or last.get("app_viewport") != first.get("app_viewport"):
                errors.append(f"{name}: changed state {last.get('state_vtable')}, paused {last.get('app_paused')}, viewport {last.get('app_viewport')}")
        first, last = step("unpaused-right", hold_right, [])
        if first.get("x") == last.get("x"):
            errors.append(f"unpaused: the right arrow did not move Claw from x {first.get('x')}")
        for slot, key in enumerate((120, 99, 118, 96, 97, 98, 100)):
            name = f"f{slot+2}"
            first, last = step(name, lambda key=key: tap(key), [(hex(0x8050+slot), 1)])
            for field in ("state_vtable", "app_paused", "app_viewport", "screen_dump_count", "screen_dumps"):
                if first.get(field) != last.get(field):
                    errors.append(f"{name}: changed {field}")
        def dump(name, success=True):
            first, last = step(name, lambda: chord(CONTROL, "control", D), [("0x8070", 1)])
            count = first.get("screen_dump_count", 0) + 1
            events = last.get("screen_dumps", [])
            if last.get("screen_dump_count") != count or len(events) != len(first.get("screen_dumps", []))+1:
                errors.append(f"{name}: count or write did not advance: {last.get('screen_dump_count')}, {events}")
                return
            event = events[-1]
            try:
                assert event["success"] == success and event["name"] == f"CLAW{count:04d}.BMP"
                if success:
                    check_bitmap(OUT / "dumps" / event["name"], event)
                registry = json.loads((OUT / "settings" / "registry.json").read_text())
                key = r"HKEY_LOCAL_MACHINE\Software\Monolith Productions\Claw\1.0"
                assert registry[key]["Screen Dump Count"] == {"type": 4, "hex": struct.pack("<I", count).hex()}
            except (AssertionError, OSError, KeyError, ValueError) as error:
                errors.append(f"{name}: invalid BMP or persisted count: {error}")
        dump("control-d")
        dump("control-d-again")
        # A physical write failure still consumes its number, as 0x495be0
        # writes the setting before calling the platform writer.
        (OUT / "dumps" / "CLAW0003.BMP").mkdir(parents=True, exist_ok=True)
        dump("control-d-write-failure", success=False)
        # Control+1 (0x802f) has no 0x426e30 branch: delivered, nothing happens.
        step("control-1", lambda: chord(CONTROL, "control", ONE), [("0x802f", 1)])
        # Option+Return: no accelerator, inert WM_SYSKEYDOWN handler, the window stays as it is.
        first, last = step("option-return", lambda: chord(OPTION, "option", RETURN), [])
        if last.get("state_vtable") != GAMEPLAY:
            errors.append(f"option-return changed the state to {last.get('state_vtable')}")

        # F1 pushes Help; Help's Escape key handler pops it through the admitted destructor.
        first, last = step("f1", lambda: tap(F1), [("0x8035", 1)])
        if (first.get("state_vtable"), last.get("state_vtable")) != (GAMEPLAY, HELP):
            errors.append(f"F1: state {first.get('state_vtable')} -> {last.get('state_vtable')}, expected game -> Help")
        dump("help-control-d")
        result["screen_dumps"] = live().get("screen_dumps", [])
        first, last = step("help-escape", lambda: tap(ESCAPE), [])
        if (first.get("state_vtable"), last.get("state_vtable")) != (HELP, GAMEPLAY):
            errors.append(f"Escape: state {first.get('state_vtable')} -> {last.get('state_vtable')}, expected Help -> game")

        # Key up: a held key is released by its key-up event; nothing stays held.
        post(RIGHT, "down")
        session.sleep(0.3)
        held = (live().get("weapons") or {}).get("held_keys", [])
        post(RIGHT, "up")
        session.sleep(0.5)
        released = (live().get("weapons") or {}).get("held_keys", [])
        result["right_held"], result["after_release"] = held, released
        if 0x27 not in held or released:
            errors.append(f"right arrow held {held}, after release {released}")
        return result
    finally:
        result["steps"] = steps
        if pid and pid not in before:
            session.close()
        if session.retries:
            errors.append(f"lost window events posted again {session.retries}")
        # Evidence compared between the fast and real-time runs (scripts/compare-real-input.py): no frame numbers
        # or clocks.
        (OUT / "evidence.json").write_text(json.dumps({"steps": [{k: v for k, v in st.items() if k not in ("frame", "game_ms")}
            for st in steps], "right": [result.get("right_held"), result.get("after_release")]}, indent=1, sort_keys=True))
        if not errors and steps:
            result["status"] = "pass"


if __name__ == "__main__":
    out = main()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["status"] == "pass" else 1)
