"""Check menu evidence isolation with confirmed real window events (Release by default)."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from real_input import ROOT, Session, build_helper


def run(out, app, helper, *, allow=False, scripted=False):
    out.mkdir(parents=True, exist_ok=True)
    (out / "app-menu.json").unlink(missing_ok=True)
    args = ["--menu-check", str(out), "--menu-live-check", str(out),
            "--menu-frames", "181", "--no-paper-startup"]
    if allow:
        args += ["--menu-allow-live-input"]
    if scripted:
        events = out / "events.json"
        events.write_text(json.dumps([{"frame": 2, "key": 65, "message": 256},
                                      {"frame": 3, "key": 65, "message": 257}]))
        args += ["--menu-input-script", str(events)]
    # Real display ticks exercise the formerly unguarded, script-free path.
    session = Session(out, fast=False, helper=helper)
    try:
        session.launch(app, {}, args)
        session.post("key", 125)  # Down arrow; receipt is confirmed by input.json.
        session.post("press", 125, "down", "option")
        session.post("press", 125, "up", "option")
        session._post(["click"])
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            report = json.loads((out / "app-menu.json").read_text())
            if report.get("status") != "running":
                break
            time.sleep(0.05)
        assert report["status"] == "pass", report
        live = json.loads((out / "live-state.json").read_text())
        events = live["events"]
        keys = [e for e in events if e.get("key") == 40 and e.get("down")]
        pointers = [e for e in events if "message" in e]
        assert keys, ("real keys did not reach handlers", events)
        ignored = not allow or scripted
        assert all(e.get("ignored", False) == ignored for e in keys + pointers), events
        assert any(e.get("system") for e in keys), "system-key path not exercised"
        if scripted:
            assert any(e.get("key") == 65 and not e.get("ignored") for e in events), events
        if ignored:
            subprocess.run([str(ROOT / "work/test-env/bin/python"),
                            str(ROOT / "scripts/check-menu-on-screen.py"),
                            "--evidence", str(out)], check=True)
        else:
            assert any(f["selected"] != report["frames"][0]["selected"]
                       for f in report["frames"]), "opt-in key did not change the menu"
        return {"status": "pass", "evidence": str(out), "live_input_ignored": ignored,
                "observed_pointer_events": len(pointers),
                "confirmed_key_transitions": session.input_state()["received"]}
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="Release")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--derived-data", type=Path, default=ROOT / "work/MacCatalyst")
    args = parser.parse_args()
    assert args.runs > 0
    app = args.derived_data.resolve() / f"Build/Products/{args.config}-maccatalyst/Claw.app"
    out = ROOT / "work/new-game/menu-input-isolation"
    helper = build_helper(out / "post-window-input")
    results = [run(out / f"isolated-{i + 1}", app, helper) for i in range(args.runs)]
    results.append(run(out / "opt-in", app, helper, allow=True))
    results.append(run(out / "script-priority", app, helper, allow=True, scripted=True))
    report = {"status": "pass", "config": args.config, "consecutive_menu_matches": args.runs,
              "runs": results}
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
