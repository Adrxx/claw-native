"""Stored settings and startup movie counters persist across app launches, as the original's registry.

The original reads its settings under HKLM\\Software\\Monolith Productions\\Claw\\1.0 at startup
(0x425827..0x425ad9; Skip Logo Movies at 0x426767) and writes them at teardown (0x42698f..0x426ad6).
The native app keeps those values in <settings-dir>/registry.json. This check launches its own muted
instances with --movie-check and an isolated --settings-dir (never the owner's settings), skipping each
startup movie with a real key press (scripts/post-window-input.swift), and checks:
  1. a fresh store: logo and intro play, and teardown stores Num Runs 1 and Num Movies 1;
  2. the next launch reads them (runs 2, intro count 1) and plays the logo alone;
  3. single-player options changed in the store (Skip Logo Movies 1, Music 0, Voice 0, Music Volume 30,
     Status Layout 7) are read at startup, no movie plays, and teardown writes them back with Num Runs 3.
     Music Volume returns as 29: the original sets it through 0x4b55e0 (percent to master 0..127, truncated)
     and reads it back through 0x4b5650 (truncated again), so each launch loses up to one percent, as in the
     original (fresh 50 is stored as 49).
It closes only the instances it started. Usage: work/test-env/bin/python scripts/check-settings-persistence.py
[--config Release]. Prints one JSON line last.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from real_input import MAC_TO_VK, Session, build_helper, real_time_requested

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "settings-persistence"
STORE = WORK / "store"
KEY = ("HKEY_LOCAL_MACHINE\\Software\\Monolith Productions\\Claw\\1.0")
spec = importlib.util.spec_from_file_location("movie_skip", ROOT / "scripts" / "check-movie-skip.py")
skip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skip)


def values():
    try:
        data = json.loads((STORE / "registry.json").read_text()).get(KEY, {})
    except (OSError, ValueError):
        return {}
    out = {}
    for name, v in data.items():
        raw = bytes.fromhex(v["hex"])
        out[name] = int.from_bytes(raw, "little") if v["type"] == 4 and len(raw) == 4 else raw.split(b"\0")[0].decode("latin-1")
    return out


def store(name, value):
    path = STORE / "registry.json"
    data = json.loads(path.read_text())
    data[KEY][name] = {"type": 4, "hex": value.to_bytes(4, "little").hex()}
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def skip_movie(session, movie):
    # Movie-check exits once startup reaches the menu. Send the real down/up
    # pair together, without Session.post("key") advancing gated game frames
    # between them. Persisted input acknowledgements remain readable after exit.
    vk = MAC_TO_VK[skip.KEY_A]
    before = session.transitions()
    expected = {f"{vk}:{direction}": before.get(f"{vk}:{direction}", 0) + 1
                for direction in ("down", "up")}
    posted = skip.post(session.pid, "key", skip.KEY_A)
    if posted.get("status") != "posted":
        raise RuntimeError(f"movie {movie}: key pair was not posted: {posted}")
    def acknowledged():
        received = session.transitions()
        state = session.movie()
        return (all(received.get(key, 0) >= count for key, count in expected.items())
                and not (state.get("movie") == movie and state.get("playing")))
    if not skip.wait(acknowledged, 5):
        raise RuntimeError(f"movie {movie}: skip/key-up not acknowledged: {session.transitions()}")
    return {"movie": movie, "key": vk, "expected": expected,
            "received": session.transitions(), "uptime": posted["uptime"]}


def launch(app, name, fast):
    out = WORK / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    skip.OUT = out
    session = Session(out, fast=fast, helper=skip.HELPER)
    posts = []
    try:
        session.launch(app, {}, ["--movie-check", str(out), "--settings-dir", str(STORE)])
        report_path = out / "movie-check.json"
        end = time.monotonic() + 300
        skipped = set()
        while time.monotonic() < end and not report_path.exists():
            s = skip.state()
            if s.get("playing") and s.get("ready") and s.get("movie") not in skipped:
                if not fast:
                    time.sleep(1.0)
                posts.append(skip_movie(session, s["movie"]))
                skipped.add(s.get("movie"))
            time.sleep(0.1)
        if not report_path.exists():
            return {"error": "movie-check.json not written"}
        time.sleep(0.5)
        report = json.loads(report_path.read_text())
        for post in posts:
            post["skip_recorded"] = any(
                s.get("movie") == post["movie"] and s.get("skip_key") == post["key"]
                and 0 <= s.get("uptime", -1) - post["uptime"] < 2
                for s in report.get("movies", []))
        (out / "input-confirmation.json").write_text(json.dumps(posts, indent=2, sort_keys=True))
        report["confirmed_skips"] = posts
        return report
    except RuntimeError as error:
        return {"error": str(error), "confirmed_skips": posts}
    finally:
        session.close()


def summary(report):
    events = report.get("events", [])
    start = next((e for e in events if e.get("call") == "startup"), {})
    repeat = next((e for e in events if e.get("call") == "repeat-launch"), None)
    reads = {e["name"]: e["result"] for e in report.get("settings", []) if e.get("call") == "RegQueryValueExA"}
    writes = {e["name"]: e["value"] for e in report.get("settings", []) if e.get("call") == "RegSetValueExA"}
    return {"status": report.get("status"), "error": report.get("error", ""), "menu_live": report.get("menu_live"),
            "silent": report.get("silent"), "runs": start.get("runs"), "intro_count": start.get("intro_count"),
            "repeat": repeat, "movies": [m["movie"] for m in report.get("movies", []) if "file" in m],
            "movie_results": [{k: m.get(k) for k in ("movie", "outcome", "result")}
                              for m in report.get("movies", []) if "file" in m],
            "confirmed_skips": [{k: v for k, v in p.items() if k != "uptime"}
                                for p in report.get("confirmed_skips", [])],
            "stored_reads": sorted(n for n, r in reads.items() if r == 0), "writes": writes,
            "written": report.get("settings_written"), "store_failure": report.get("settings_failure")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Release"))
    parser.add_argument("--real-time", action="store_true")
    args = parser.parse_args()
    fast = not real_time_requested(args.real_time)
    app = ROOT / "work" / "MacCatalyst" / "Build" / "Products" / f"{args.config}-maccatalyst" / "Claw.app"
    result = {"check": "settings-persistence", "status": "fail", "config": args.config, "errors": []}
    errors = result["errors"]
    build_helper(skip.HELPER)
    shutil.rmtree(STORE, ignore_errors=True)
    runs = result["runs"] = []

    def expect(label, condition):
        if not condition:
            errors.append(label)

    r = summary(launch(app, "a-fresh", fast)); r["store"] = values(); runs.append(r)
    expect("fresh launch: runs 1, intro count 0", (r["runs"], r["intro_count"]) == (1, 0))
    expect("fresh launch: logo and intro", r["movies"] == [1, 2] and r["repeat"] is None)
    expect("fresh launch: nothing stored was read", r["stored_reads"] == [])
    expect("fresh launch: teardown stored Num Runs 1, Num Movies 1",
           (r["store"].get("Num Runs"), r["store"].get("Num Movies")) == (1, 1))

    r = summary(launch(app, "b-repeat", fast)); r["store"] = values(); runs.append(r)
    expect("repeat launch: runs 2, intro count 1", (r["runs"], r["intro_count"]) == (2, 1))
    expect("repeat launch: logo alone", r["movies"] == [1] and r["repeat"] == {"call": "repeat-launch", "skip_logo": 0})
    expect("repeat launch: stored counters read", {"Num Runs", "Num Movies"} <= set(r["stored_reads"]))
    expect("repeat launch: Num Runs 2 stored", (r["store"].get("Num Runs"), r["store"].get("Num Movies")) == (2, 1))

    for name, value in [("Skip Logo Movies", 1), ("Music", 0), ("Voice", 0), ("Music Volume", 30), ("Status Layout", 7)]:
        store(name, value)
    r = summary(launch(app, "c-changed", fast)); r["store"] = values(); runs.append(r)
    expect("changed launch: runs 3", (r["runs"], r["intro_count"]) == (3, 1))
    expect("changed launch: Skip Logo Movies skips the logo", r["movies"] == [] and r["repeat"] == {"call": "repeat-launch", "skip_logo": 1})
    expect("changed launch: stored options read",
           {"Skip Logo Movies", "Music", "Voice", "Music Volume", "Status Layout"} <= set(r["stored_reads"]))
    expect("changed launch: options written back at teardown",
           all(r["writes"].get(k) == v for k, v in [("Num Runs", 3), ("Music", 0), ("Voice", 0), ("Music Volume", 29)]))
    expect("changed launch: store keeps them",
           all(r["store"].get(k) == v for k, v in [("Num Runs", 3), ("Music", 0), ("Voice", 0), ("Music Volume", 29),
                                                   ("Status Layout", 7), ("Skip Logo Movies", 1)]))
    for r in runs:
        expect("each startup movie has a confirmed real down/up pair",
               [p["movie"] for p in r["confirmed_skips"]] == r["movies"])
        expect("each startup movie ended by skipping",
               all(m.get("outcome") == "skipped" and m.get("result") == 1 for m in r["movie_results"]))
        for post in r["confirmed_skips"]:
            expect(f"movie {post['movie']}: expected key caused the skip",
                   post.get("skip_recorded", False))
        if r["status"] != "pass" or not r["menu_live"] or not r["silent"] or not r["written"] or r["store_failure"]:
            errors.append(f"launch not pass, menu not live, not silent or not written: {r['status']} {r['error']}")
    if not errors:
        result["status"] = "pass"
    (WORK / "evidence.json").write_text(json.dumps(runs, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    outcome = main()
    print(json.dumps(outcome))
    sys.exit(0 if outcome["status"] == "pass" else 1)
