"""Owner's Level 6 startup rand crash, with real keys on a muted fast-clock app.

Probe the native CRT before New Game, after each load and after returning to
the menu. Level 6 must execute the TownGuard2 source-context rand call that
previously faulted at 0x4a3050. No original gameplay or family admission claim.
"""
import json
import os
from pathlib import Path

from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/crt-rand/check"
MENU, LEVEL = "0x50c1e4", "0x50c264"
KEYS = {"M": 46, "P": 35, "G": 5, "O": 31, "F": 3, "C": 8, "Y": 16, "L": 37, "E": 14}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Every run uses fresh profiles, marks and input receipts.
    import shutil
    shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    derived = Path(os.environ.get("CLAW_DERIVED_DATA", ROOT / "work/MacCatalyst"))
    app = derived / "Build/Products/Release-maccatalyst/Claw.app"
    session = Session(OUT, fast=True, helper=build_helper(ROOT / "work/cheat-codes/post-window-input"))
    report = {"check": "crt-rand", "status": "fail", "marks": [], "errors": []}

    def read(name):
        try:
            return json.loads((OUT / name).read_text())
        except (OSError, ValueError):
            return {}

    def require(ok, message):
        if not ok:
            raise RuntimeError(f"{message}: {read('real-speed.json').get('error', '')}")

    def key(code):
        session.post("key", code)
        session.sleep(0.3)
        require(not session.failed(), "frame failed after key")

    def mark(name, state, level=None):
        require(session.wait(lambda: read("live.json").get("state_vtable") == state and
                             (level is None or read("live.json").get("level") == level), 60),
                f"{name}: state/level not reached")
        record = session.mark(name)
        require(record is not None, f"{name}: missing frame mark")
        rng = record.get("crt_random", {})
        before = rng.get("before")
        require(isinstance(before, int), f"{name}: missing rand probe")
        after = (before * 214013 + 2531011) & 0xffffffff
        require(rng.get("after") == after and rng.get("result") == (after >> 16) & 0x7fff
                and rng.get("fault") == 0, f"{name}: native CRT sequence/fault")
        require(not report["marks"] or rng["calls"] > report["marks"][-1]["random"]["calls"],
                f"{name}: rand not called")
        report["marks"].append({"name": name, "state": record["state_vtable"],
                                "level": read("live.json").get("level"), "random": rng})

    def new_game():
        for _ in range(3):
            key(36)
            session.sleep(1)
        require(session.wait(lambda: read("live.json").get("state_vtable") == LEVEL and
                             read("live.json").get("level") == 1 and
                             read("live.json").get("game_ms", 0) > 1000, 90), "New Game never loaded")

    try:
        session.launch(app, {}, ["--save-dir", str(OUT / "saves"), "--menu-live-check", str(OUT),
                                 "--crt-rand-check", "-ClawCheckDirectory", str(OUT)])
        session.sleep(1)
        mark("menu-before-new-game", MENU)
        new_game()
        mark("new-game", LEVEL, 1)
        for letter in "MPGOOFCYCLE":
            session.post("key", KEYS[letter])
        require(session.wait(lambda: read("live.json").get("level") == 6, 90), "Level 6 never loaded")
        # The owner crash occurs during the first idle animation completion.
        session.sleep(5)
        require(not session.failed(), "Level 6 startup fault")
        mark("level-six-start", LEVEL, 6)
        source_calls = read("live-state.json").get("transports", {}).get("source-crt-rand", 0)
        require(source_calls > 0, "TownGuard2 source rand route was not exercised")
        report["source_rand_calls"] = source_calls
        # Escape -> End Game -> Yes through the game's own command handlers.
        for code in (53, 125, 125, 125, 125, 36, 36):
            key(code)
        session.sleep(1)
        mark("returned-menu", MENU)
        new_game()
        mark("second-new-game", LEVEL, 1)
        require(not session.failed(), "final frame fault")
        report["status"] = "pass"
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        report["errors"].append(str(error))
        report["trace"] = read("real-speed.json").get("trace", [])[-16:]
    finally:
        session.close()
    (OUT.parent / "result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return report["status"] != "pass"


if __name__ == "__main__":
    raise SystemExit(main())
