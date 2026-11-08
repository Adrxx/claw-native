"""Startup movies end on real key presses, as the original's 0x4f0380 with play flags 1.

The original's movie loop (0x4f0380) peeks window messages: WM_KEYDOWN ends the movie
when play flag 1 is set, WM_LBUTTONDOWN only when flag 0x100 is set, and
WM_SYSKEYDOWN/WM_SYSKEYUP are swallowed. The logo (0x42b900) and the intro (0x42b140)
both pass flags 1, so any key skips them and a click or an Option key does not.

This check launches its own muted Debug instance with --movie-check and posts real
window-server events to that process only (scripts/post-window-input.swift, CGEventPostToPid),
the path a physical keyboard and mouse take; it never calls the app's key handler.
For each movie it posts a click and an Option press (both must leave the movie
playing; whether a click posted to a process reaches UIKit is reported, not required),
then a key (which must end it within a second, showing the window handles events
while the movie plays). It closes only the instance it started.

Usage: work/test-env/bin/python scripts/check-movie-skip.py [--config Debug]
Prints one JSON line last.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from real_input import Session, build_helper, real_time_requested
from responsiveness import check_heartbeats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "movie-skip" / "check"
HELPER = ROOT / "work" / "movie-skip" / "post-window-input"
# Mac virtual key codes: A, Tab (no game mapping; still WM_KEYDOWN), Option.
KEY_A, KEY_TAB, KEY_OPTION = 0, 48, 58
STEPS = [(1, KEY_A), (2, KEY_TAB)]


def claw_pids():
    found = subprocess.run(["pgrep", "-x", "Claw"], capture_output=True, text=True).stdout.split()
    return {int(p) for p in found}


def state():
    try:
        return json.loads((OUT / "movie-state.json").read_text())
    except (OSError, ValueError):
        return {}


def wait(predicate, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def post(pid, *args):
    result = subprocess.run([str(HELPER), str(pid), *map(str, args)], capture_output=True, text=True, timeout=10)
    line = (result.stdout.strip().splitlines() or ["{}"])[-1]
    return json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.environ.get("CLAW_CONFIG", "Debug"))
    parser.add_argument("--real-time", action="store_true")
    args = parser.parse_args()
    fast = not real_time_requested(args.real_time)
    app = ROOT / os.environ.get("CLAW_DERIVED_DATA", "work/MacCatalyst") / "Build" / "Products" / f"{args.config}-maccatalyst" / "Claw.app"
    result = {"check": "movie-skip", "status": "fail", "config": args.config, "errors": []}
    errors = result["errors"]
    build_helper(HELPER)
    subprocess.run(["rm", "-rf", str(OUT)], check=True)
    OUT.mkdir(parents=True)
    session = Session(OUT, fast=fast, helper=HELPER)
    pid = None
    try:
        pid = session.launch(app, {}, ["--movie-check", str(OUT)])
        result["pid"] = pid
        result["fast"] = fast
        posts = []
        for movie, key in STEPS:
            if not wait(lambda: state().get("movie") == movie and state().get("playing"), 120):
                errors.append(f"movie {movie} never started")
                break
            if not wait(lambda: state().get("ready"), 10):
                raise RuntimeError("movie not ready")
            if not fast:
                time.sleep(1.5)
            posts.append({"movie": movie, "input": "click", **post(pid, "click")})
            posts.append({"movie": movie, "input": "option", **session.post("key", KEY_OPTION, "option")})
            time.sleep(0.1 if fast else 1.0)
            if not (state().get("movie") == movie and state().get("playing")):
                errors.append(f"movie {movie} ended on a click or Option press")
            # A movie skip consumes key-down, then destroys the movie view.
            # Post the physical pair together; do not insert gated game frames
            # before key-up (startup exits after reaching the menu). Delivery
            # is confirmed below by this key's recorded skip and its latency.
            posts.append({"movie": movie, "input": f"key {key}", **post(pid, "key", key)})
            if not wait(lambda: not (state().get("movie") == movie and state().get("playing")), 2.0):
                errors.append(f"movie {movie} not ended within 2 s of a real key press")
        result["posts"] = posts
        report_path = OUT / "movie-check.json"
        if not wait(report_path.exists, 60):
            errors.append("movie-check.json not written")
            return result
        time.sleep(0.5)
        report = json.loads(report_path.read_text())
        heartbeats = report.get("responsiveness", [])
        errors.extend(check_heartbeats(heartbeats, required=("movie-1", "movie-2")))
        result["heartbeat_max_gap_ms"] = max((r["max_gap_ms"] for r in heartbeats), default=None)
        movies = [r for r in report["movies"] if "file" in r]
        skips = [r for r in report["movies"] if "skip_key" in r]
        clicks = [r for r in report["movies"] if "ignored_click" in r]
        plays = [e for e in report["events"] if e.get("call") == "play"]
        result.update(app_status=report["status"], menu_live=report["menu_live"], silent=report["silent"],
                      movies=[{k: m[k] for k in ("movie", "outcome", "result", "seconds", "media_seconds")} for m in movies],
                      play_flags=[e["flags"] for e in plays], ignored_clicks=len(clicks))
        if [m["movie"] for m in movies] != [1, 2]:
            errors.append(f"movies played {[m['movie'] for m in movies]}")
        for m in movies:
            if m["outcome"] != "skipped" or m["result"] != 1:
                errors.append(f"movie {m['movie']} outcome {m['outcome']} result {m['result']}")
        if [e["flags"] for e in plays] != [1, 1] or [e["result"] for e in plays] != [1, 1]:
            errors.append("0x4f0380 calls are not flags 1 with result 1")
        # Latency from each posted key to the app's skip: the window handles events during the movie.
        latencies = []
        for p in [p for p in posts if p["input"].startswith("key")]:
            match = [s for s in skips if s["movie"] == p["movie"]]
            if not match:
                errors.append(f"no skip recorded for movie {p['movie']}")
                continue
            latencies.append(round(match[0]["uptime"] - p["uptime"], 3))
        result["key_to_skip_seconds"] = latencies
        if any(not 0 <= v < 1.0 for v in latencies):
            errors.append(f"key-to-skip latency {latencies}")
        # Informational: a click posted to a process (not through the cursor) does not always
        # reach UIKit's hit test on Catalyst, so delivery is reported, not required; a click that
        # does arrive must not have ended the movie (checked above).
        result["clicks_delivered_in_movies"] = sorted({c.get("movie", 0) for c in clicks})
        if report["status"] != "pass" or not report["menu_live"] or not report["silent"]:
            errors.append("app report not pass, menu not live, or not silent")
        if not errors:
            result["status"] = "pass"
        return result
    finally:
        session.close()
        result["retries"] = session.retries
        evidence = {k: result.get(k) for k in ("app_status", "menu_live", "silent", "play_flags")}
        evidence["movies"] = [{k: m[k] for k in ("movie", "outcome", "result")} for m in result.get("movies", [])]
        evidence["skip_keys"] = [key for _, key in STEPS] if result.get("status") == "pass" else []
        (OUT / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    outcome = main()
    print(json.dumps(outcome))
    sys.exit(0 if outcome["status"] == "pass" else 1)
