"""In-game Options > Audio: the four switches and both volumes through real key events, checked step by step
against the admitted original handlers and their service calls.

This check launches its own muted Release (or CLAW_CONFIG) instance on the real clock with a scratch
--save-dir and no settings store (original defaults: every switch on, Sound Volume 80, Music Volume 50),
walks the menu to Level 1, then posts real window-server key events to that process only
(scripts/post-window-input.swift): Escape, Options, Audio (the third Options item); Sound volume down twice, up three times (the
last at the maximum 80); Sound off, Left while off, Sound on; Voice off and on; Ambient off and on; Music
volume up and down, Music off, Right while off, Music on; Back; Escape, which resumes play.

Expected behaviour comes from the admitted original handlers: 0x450ed0 (commands 0x5aa1..0x5aa5, family
pause_menu_commands) for Return, 0x452290 (pause_menu_panels) for Left and Right. After each step the app
records (scripts' "s <name>" control) the application words, the effects master flag 0x532c0c and volume
0x532c10, the ambient group (application +0x5c), the music manager (+0x50) and the native music service
log, plus the counts of every cross-family call so far. Each step checks the switch words, the volumes and
the calls the original handler makes in that state:
  Sound volume: 0x42cdc0 once per changed step (8 per step, 0..80), none at the limit; the ambient group
    volume (+0x04, through 0x4024e0) follows it.
  Sound: application +0x10 and 0x532c0c toggle; 0x4b4b40 once, after which no native voice plays;
    switching on also restarts the ambient group (0x402570). Left while Sound is off changes nothing.
  Voice: application +0x118 toggles; the test voice's status 0x4b3e70 once; on starts it (0x4b3d80).
  Ambient: application +0x11c and the group's +0x24 toggle; off stops the group (0x402520, which stops
    each ambient object's voice through 0x4b3e30), on restarts it (0x402570).
  Music volume: 0x4b5650 then 0x4b55e0 once per step (50 -> 60 -> 50, in tens of the read-back value);
    the native driver receives master volume 76, then 63.
  Music: application +0x14 toggles; off pauses through 0x4b55a0 (native service 0x546e84), on
    goes through 0x4b5570, which stops the current song and starts it again from the beginning (0x546e78,
    0x546e90), as the admitted music family does. Right while Music is off reads nothing.
A second instance starts from a settings store holding Ambient 0 and Sound Volume 40 (--settings-dir):
startup (0x4262e7..0x426343) must give the ambient group volume 40 and leave it disabled (+0x24 clear,
through 0x402520), and switching Ambient on in game must enable and restart it.
Every step keeps the native output muted (mixer volume 0). Speaker acceptance is the owner's. It closes
only the instance it started.

Usage: work/test-env/bin/python scripts/check-ingame-audio-options.py [--config Release] [--real-time]
Runs on the fast clock through the app's input gate (scripts/real_input.py); --real-time (or REAL_TIME=1)
keeps the display timer and wall-clock waits for pacing checks.
Prints one JSON line last.
"""
import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_input import Session, build_helper, real_time_requested  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "audio-options"
OUT = [WORK / "check"]  # the current route's record directory
KEY = "HKEY_LOCAL_MACHINE\\Software\\Monolith Productions\\Claw\\1.0"
HELPER = WORK / "post-window-input"
STEPS = (["esc", "down", "down", "ret", "down", "down", "ret", "#audio",
          "left", "#sv72", "left", "#sv64", "right", "#sv72b", "right", "#sv80", "right", "#sv80b",
          "ret", "#sound-off", "left", "#sound-off-left", "ret", "#sound-on",
          "down", "ret", "#voice-off", "ret", "#voice-on",
          "down", "ret", "#amb-off", "ret", "#amb-on",
          "down", "right", "#mv60", "left", "#mv50", "ret", "#music-off", "right", "#music-off-right",
          "ret", "#music-on", "down", "ret", "#back", "esc", "#resumed"])
MAC = {"esc": 53, "down": 125, "up": 126, "ret": 36, "left": 123, "right": 124}
MENU, LEVEL = "50c044", "50c264"
MENU_KEYS = [{"ms": ms + d, "key": 13, "down": 1 - d // 80} for ms in (3000, 5000, 7000) for d in (0, 80)]
WATCH = ["4b4b40", "402570", "402520", "4b3e70", "4b3d80", "4b3e30", "4b5570", "4b55a0", "42cdc0", "4b55e0",
         "4b5650"]
# Per mark: expected application words (offset -> value), effects globals (master, volume), ambient group
# enabled word (+0x24), and calls (watched address -> count since the previous mark; unlisted watched
# addresses must not be called).
EXPECT = {
    "sv72": {"app": {0x10: 1, 0x12c: 72}, "volume": 72, "calls": {"42cdc0": 1}},
    "sv64": {"app": {0x12c: 64}, "volume": 64, "calls": {"42cdc0": 1}},
    "sv72b": {"app": {0x12c: 72}, "volume": 72, "calls": {"42cdc0": 1}},
    "sv80": {"app": {0x12c: 80}, "volume": 80, "calls": {"42cdc0": 1}},
    "sv80b": {"app": {0x12c: 80}, "volume": 80, "calls": {}},
    "sound-off": {"app": {0x10: 0}, "master": 0, "calls": {"4b4b40": 1}, "voices": 0},
    "sound-off-left": {"app": {0x10: 0, 0x12c: 80}, "master": 0, "volume": 80, "calls": {}},
    "sound-on": {"app": {0x10: 1}, "master": 1, "calls": {"4b4b40": 1, "402570": 1}},
    "voice-off": {"app": {0x118: 0}, "calls": {"4b3e70": 1}},
    "voice-on": {"app": {0x118: 1}, "calls": {"4b3e70": 1, "4b3d80": 1}},
    "amb-off": {"app": {0x11c: 0}, "group": 0, "calls": {"402520": 1, "4b3e30": "objects"}},
    "amb-on": {"app": {0x11c: 1}, "group": 1, "calls": {"402570": 1}},
    "mv60": {"calls": {"4b5650": 1, "4b55e0": 1}, "driver_volume": 76},
    "mv50": {"calls": {"4b5650": 1, "4b55e0": 1}, "driver_volume": 63},
    "music-off": {"app": {0x14: 0}, "calls": {"4b55a0": 1}, "service": "546e84"},
    "music-off-right": {"app": {0x14: 0}, "calls": {}},
    "music-on": {"app": {0x14: 1}, "calls": {"4b5570": 1}, "service": "546e90"},
    "back": {"app": {0x10: 1, 0x14: 1, 0x118: 1, 0x11c: 1, 0x12c: 80}, "master": 1, "volume": 80, "group": 1,
             "calls": {}},
}
# A stored Ambient 0 and Sound Volume 40: startup (0x4262e7..0x426343) gives the ambient group volume 40 and
# clears its enabled word through 0x402520; switching Ambient on in game restarts it.
STORED_SETTINGS = {"Ambient": 0, "Sound Volume": 40}
STORED_STEPS = ["esc", "down", "down", "ret", "down", "down", "ret", "#audio", "down", "down", "ret", "#amb-on",
                "down", "down", "ret", "#back", "esc", "#resumed"]
STORED_EXPECT = {
    "amb-on": {"app": {0x11c: 1}, "group": 1, "volume": 40, "calls": {"402570": 1}},
    "back": {"app": {0x10: 1, 0x11c: 1, 0x12c: 40}, "master": 1, "volume": 40, "group": 1, "calls": {}},
}


def claw_pids():
    found = subprocess.run(["pgrep", "-x", "Claw"], capture_output=True, text=True).stdout.split()
    return {int(p) for p in found}


def read(name):
    try:
        return json.loads((OUT[0] / name).read_text())
    except (OSError, ValueError):
        return {}


def wait(predicate, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def compare(name, previous, mark, errors, expect):
    want = expect.get(name)
    if want is None:
        return
    words = mark.get("application_words") or []
    for offset, value in want.get("app", {}).items():
        got = words[offset // 4] if offset // 4 < len(words) else None
        if got != value:
            errors.append(f"{name}: application +{offset:#x} = {got}, expected {value}")
    master, volume = (mark.get("audio_globals") or [None, None])[:2]
    if "master" in want and master != want["master"]:
        errors.append(f"{name}: 0x532c0c = {master}, expected {want['master']}")
    if "volume" in want and volume != want["volume"]:
        errors.append(f"{name}: 0x532c10 = {volume}, expected {want['volume']}")
    group = mark.get("ambient_group") or []
    if len(group) > 9:
        if "group" in want and group[9] != want["group"]:
            errors.append(f"{name}: ambient group +0x24 = {group[9]}, expected {want['group']}")
        if group[1] != volume:
            errors.append(f"{name}: ambient group volume {group[1]} != sound volume {volume}")
    else:
        errors.append(f"{name}: no ambient group")
    before, after = previous.get("invoke_counts") or {}, mark.get("invoke_counts") or {}
    # Each captured pre-selector graph is input to unchanged original code.
    # Nested pool status/start calls are additional to the direct pause-handler
    # calls above. This works at either version's actual dispatch boundary.
    nested = {"4b3e70": 0, "4b3d80": 0}
    if "audio_pool_inputs" not in previous or "audio_pool_inputs" not in mark:
        errors.append(f"{name}: missing original pool input evidence")
    else:
        prefix, inputs = previous["audio_pool_inputs"], mark["audio_pool_inputs"]
        if inputs[:len(prefix)] != prefix:
            errors.append(f"{name}: pool input history changed")
        selections = {"sound-on", "voice-off", "voice-on", "amb-off", "amb-on", "music-off", "music-on"}
        expected_pools = int(name in selections and os.environ.get("CLAW_GAME_VERSION", "1.3") == "1.0")
        if len(inputs) - len(prefix) != expected_pools or after.get("4b4430", 0) - before.get("4b4430", 0) != expected_pools:
            errors.append(f"{name}: expected {expected_pools} original pool selections")
        for snapshot in inputs[len(prefix):]:
            calls = importlib.import_module("check-audio-pool-original").expected_pool_calls(snapshot)
            for address in nested:
                nested[address] += calls[address]
    for function in WATCH:
        delta = after.get(function, 0) - before.get(function, 0)
        expected = want["calls"].get(function, 0)
        if expected == "objects":  # one stop per ambient object in the group's list (+0x14 count)
            expected = group[5] if len(group) > 5 else None
        expected += nested.get(function, 0)
        if delta != expected:
            errors.append(f"{name}: {function} called {delta} times, expected {expected}")
    tail = (mark.get("music_events") or {}).get("tail") or []
    new = (mark.get("music_events") or {}).get("count", 0) - (previous.get("music_events") or {}).get("count", 0)
    recent = tail[-new:] if new > 0 else []
    if "driver_volume" in want and not any(e.get("service") == "546e6c" and e.get("volume") == want["driver_volume"]
                                           for e in recent):
        errors.append(f"{name}: native driver volume {want['driver_volume']} not set ({recent})")
    if "service" in want and not any(e.get("service") == want["service"] for e in recent):
        errors.append(f"{name}: native music service {want['service']} not reached ({recent})")
    output = mark.get("audio_output") or {}
    if "voices" in want and output.get("active_voices") != want["voices"]:
        errors.append(f"{name}: {output.get('active_voices')} native voices playing, expected {want['voices']}")
    if not output.get("muted") or output.get("mixer_volume", 0) not in (0, -1):
        errors.append(f"{name}: output not muted {output}")


FAST = [True]


RETRIES = []


def route(app, name, plan, expect, defaults, settings, errors):
    """One muted instance along one key plan; returns the marks in order."""
    out = WORK / name
    OUT[0] = out
    steps = [{"key": k} if not k.startswith("#") else {"mark": k[1:]} for k in plan]
    subprocess.run(["rm", "-rf", str(out)], check=True)
    out.mkdir(parents=True)
    (out / "menu-keys.json").write_text(json.dumps(MENU_KEYS))
    extra = []
    if settings is not None:
        store = out / "settings"
        store.mkdir()
        (store / "registry.json").write_text(json.dumps({KEY: {k: {"type": 4, "hex": v.to_bytes(4, "little").hex()}
                                                               for k, v in settings.items()}}, indent=2))
        extra = ["--settings-dir", str(store)]
    # -g: launched behind the frontmost app, so the owner's typing never reaches it; events go to its pid.
    session = Session(out, fast=FAST[0], helper=HELPER)
    wait = session.wait
    pid = None
    marks = {}
    order = []
    try:
        pid = session.launch(app, {"CLAW_REAL_SPEED_KEYS": out / "menu-keys.json", "CLAW_AUDIO_POOL_EVIDENCE": "1"},
                             ["--save-dir", str(out / "saves"), "--menu-live-check", str(out), "-ClawCheckDirectory", str(out)] + extra)
        if not wait(lambda: (read("live.json").get("weapons") or {}).get("weapon") is not None
                    and read("live.json").get("game_ms", 0) > 1500, 90):
            raise RuntimeError("Level 1 did not start")
        session.sleep(1.0)
        for index, step in enumerate(steps):
            if "mark" in step:
                mark = step["mark"]
                record = session.mark(mark)
                if record is None:
                    errors.append(f"{name}/{mark}: no presented frame record")
                    continue
                if not session.fast:
                    time.sleep(0.05)
                    record = json.loads((out / f"{mark}.json").read_text())
                marks[mark] = record
                order.append(mark)
                continue
            for direction in ("down", "up"):
                session.post("press", MAC[step["key"]], direction)
                session.sleep(0.12)
            session.sleep(0.5)
            state = read("live-state.json")
            if state.get("status") != "running":
                errors.append(f"{name}/{step['key']}: app {state.get('status')} {state.get('error')}")
                break
            vtable = state.get("state_vtable")
            want = LEVEL if index == len(steps) - 2 else MENU
            if vtable != want:
                errors.append(f"{name}/{step['key']} (step {index}): state {vtable} != {want}")
    except Exception as error:  # noqa: BLE001 - reported as the check's failure
        errors.append(f"{name}: {error}")
    finally:
        try:
            if pid:
                session.sleep(1.0)
        except RuntimeError as error:
            errors.append(f"{name}: {error}")
        finally:
            session.close()
    # Window events the system dropped and the driver posted again (bounded, scripts/real_input.py): reported,
    # not failed; the states, invoke counts and settings below still decide.
    RETRIES.extend({"route": name, **r} for r in session.retries)
    first = marks.get("audio") or {}
    if first:
        words = first.get("application_words") or []
        for offset, value in defaults["app"].items():
            if words[offset // 4] != value:
                errors.append(f"{name}/audio: application +{offset:#x} = {words[offset // 4]}, expected {value}")
        if (first.get("audio_globals") or [None, None])[:2] != [1, defaults["volume"]]:
            errors.append(f"{name}/audio: effects master/volume {first.get('audio_globals')}, expected [1, {defaults['volume']}]")
        group = first.get("ambient_group") or []
        if len(group) < 10 or group[9] != defaults["group"] or group[1] != defaults["volume"]:
            errors.append(f"{name}/audio: ambient group {group[:10]}, expected volume {defaults['volume']}, "
                          f"enabled {defaults['group']}")
    else:
        errors.append(f"{name}: no Audio page record")
    found = []
    for previous, mark in zip(order, order[1:]):
        compare(mark, marks[previous], marks[mark], found, expect)
    errors.extend(f"{name}/{e}" for e in found)
    final = read("live-state.json")
    if final.get("state_vtable") != LEVEL:
        errors.append(f"{name}: after resume: state {final.get('state_vtable')}")
    # Evidence compared between the fast and real-time runs (scripts/compare-real-input.py): no frame numbers.
    # Heap addresses (0x10000000 and up) differ with allocation timing, and application +0x18, +0x20 and +0x24
    # count frames and messages; the rest of each word list is what the steps change.
    def scalars(words, skip=()):
        return {hex(4 * i): w for i, w in enumerate(words or []) if 0 <= w < 0x10000000 and 4 * i not in skip}
    (out / "evidence.json").write_text(json.dumps({"marks": {m: {
        "application_words": scalars(marks[m].get("application_words"), (0x18, 0x20, 0x24)),
        "audio_globals": marks[m].get("audio_globals"), "ambient_group": scalars(marks[m].get("ambient_group")),
        "music_manager": scalars(marks[m].get("music_manager")), "state_vtable": marks[m].get("state_vtable"),
        "posted_commands": marks[m].get("posted_commands")} for m in order},
        "deltas": {mark: {f: (marks[mark].get("invoke_counts") or {}).get(f, 0) - (marks[previous].get("invoke_counts") or {}).get(f, 0)
                          for f in WATCH} for previous, mark in zip(order, order[1:])},
        "final_state": final.get("state_vtable")}, indent=1, sort_keys=True))
    return {"marks": order, "deltas": {mark: {f: (marks[mark].get("invoke_counts") or {}).get(f, 0)
                                              - (marks[previous].get("invoke_counts") or {}).get(f, 0)
                                              for f in WATCH + ["4208e0", "4b45f0"]
                                              if (marks[mark].get("invoke_counts") or {}).get(f, 0)
                                              != (marks[previous].get("invoke_counts") or {}).get(f, 0)}
                                       for previous, mark in zip(order, order[1:])}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Release"))
    parser.add_argument("--real-time", action="store_true", help="the display timer and wall-clock waits (pacing check)")
    args = parser.parse_args()
    FAST[0] = not real_time_requested(args.real_time)
    app = Path(os.environ.get("CLAW_DERIVED_DATA", ROOT / "work" / "MacCatalyst")) / "Build" / "Products" / f"{args.config}-maccatalyst" / "Claw.app"
    result = {"check": "ingame-audio-options", "status": "fail", "config": args.config, "fast": FAST[0], "errors": []}
    result["retries"] = RETRIES
    errors = result["errors"]
    WORK.mkdir(parents=True, exist_ok=True)
    build_helper(HELPER)
    result["game_version"] = os.environ.get("CLAW_GAME_VERSION", "1.3")
    result["defaults"] = route(app, "check", STEPS, EXPECT,
                               {"app": {0x10: 1, 0x14: 1, 0x118: 1, 0x11c: 1, 0x12c: 80}, "volume": 80, "group": 1},
                               None, errors)
    result["stored"] = route(app, "stored", STORED_STEPS, STORED_EXPECT,
                             {"app": {0x10: 1, 0x11c: 0, 0x12c: 40}, "volume": 40, "group": 0},
                             STORED_SETTINGS, errors)
    result["pool_reference_sha256"] = importlib.import_module("check-audio-pool-original").original_program().sha256
    if not errors:
        result["status"] = "pass"
    (WORK / "result.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
