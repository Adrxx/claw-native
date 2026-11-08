"""Shared driver for the checks that post real window input to their own muted Claw instance.

Fast (the default): the app runs with --fast-clock and the input gate (App/ClawApp.swift, inputGate). It
starts paused at frame 0 and runs only as far as this driver lets it: "run <n>" in the control file runs n
frames back to back and pauses again (gate.json reports each pause), and after every real event this driver
posts through the window (scripts/post-window-input.swift, as before) it waits for that key and direction in input.json, so the app
stays paused until the event has arrived and the game sees it at the frame the check chose. Waits and sleeps
are counted in frames of the game's own clock (60 per second), the clock the real-time run's game sees too.

Real time (--real-time, or REAL_TIME=1): the previous behaviour, kept for occasional pacing checks; the
app runs on the display timer and waits and sleeps are wall-clock seconds.
Key taps hold through four completed game frames on both clocks, including blocking transitions.
"""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS = 60
# Mac virtual key positions to the Windows virtual keys reported by the input view.
MAC_TO_VK = {30:0xdd,33:0xdb,39:0xde,41:0xba,42:0xdc,43:0xbc,44:0xbf,47:0xbe,50:0xc0,0: 65, 1: 83, 2: 68, 3: 70, 4: 72, 5: 71, 6: 90, 7: 88, 8: 67, 9: 86,
             11: 66, 12: 81, 13: 87, 14: 69, 15: 82, 16: 89, 17: 84, 18: 49, 19: 50,
             20: 51, 21: 52, 22: 54, 23: 53, 24: 0xbb, 25: 57, 26: 55, 27: 0xbd, 28: 56,
             29: 48, 31: 79, 32: 85, 34: 73, 35: 80, 36: 13, 37: 76, 38: 74, 40: 75,
             45: 78, 46: 77, 48: 9, 49: 32, 51: 8, 53: 27, 56: 16, 58: 18, 59: 17,
             60: 16, 61: 18, 62: 17, 69: 0x6b, 78: 0x6d, 76: 13, 113: 0x13,
             122: 0x70, 120: 0x71, 99: 0x72, 118: 0x73, 96: 0x74, 97: 0x75,
             98: 0x76, 100: 0x77, 101: 0x78, 109: 0x79, 103: 0x7a, 111: 0x7b,
             123: 37, 124: 39, 125: 40, 126: 38}


def claw_pids():
    found = subprocess.run(["pgrep", "-x", "Claw"], capture_output=True, text=True).stdout.split()
    return {int(p) for p in found}


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def real_time_requested(argv_flag):
    return bool(argv_flag) or os.environ.get("REAL_TIME") == "1"


def build_helper(helper):
    helper = Path(helper)
    source = ROOT / "scripts" / "post-window-input.swift"
    if not helper.exists() or helper.stat().st_mtime < source.stat().st_mtime:
        helper.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["xcrun", "swiftc", "-O", str(source), "-o", str(helper)], check=True, timeout=300)
    return helper


class Session:
    """One check's own instance. out: CLAW_REAL_SPEED_LOG directory (control.txt, live.json, gate.json)."""

    def __init__(self, out, fast=True, helper=None):
        self.out = Path(out)
        self.fast = fast
        self.helper = str(helper) if helper else None
        self.control = self.out / "control.txt"
        self.pid = None
        self.seq = 0
        self.frames = 0
        self.retries = []
        self.real_base = None

    # Launch ---------------------------------------------------------------------------------------
    def launch(self, app, env, args, start_seconds=30):
        """open -g -n the app with CLAW_REAL_SPEED_LOG/CONTROL and env; args must name self.out."""
        self.control.write_text("")
        for name in ("gate.json", "input.json", "live.json"):
            (self.out / name).unlink(missing_ok=True)
        # Check load at every launch, including multi-instance check families.
        while float(subprocess.check_output(["sysctl", "-n", "vm.loadavg"], text=True).split()[1]) >= 16:
            time.sleep(10)
        before = claw_pids()
        # Catalyst may leave its input view without a key window after a
        # background launch. Foreground is the default for keyboard checks;
        # the driver still posts only to its own identified pid.
        command = ["open", "-n"] if os.environ.get("CLAW_REAL_INPUT_FOREGROUND", "1") == "1" else ["open", "-g", "-n"]
        env = {"CLAW_REAL_SPEED_LOG": str(self.out), "CLAW_REAL_SPEED_CONTROL": str(self.control), **env}
        if "CLAW_GAME_VERSION" in os.environ:
            env.setdefault("CLAW_GAME_VERSION", os.environ["CLAW_GAME_VERSION"])
        if "CLAW_LIVES_BOSS_PROFILE" in os.environ:
            env.setdefault("CLAW_LIVES_BOSS_PROFILE", os.environ["CLAW_LIVES_BOSS_PROFILE"])
        for key, value in env.items():
            command += ["--env", f"{key}={value}"]
        extra = ["--fast-clock"] if self.fast else []
        if "CLAW_GAME_VERSION" in env:
            extra += ["--game-version", env["CLAW_GAME_VERSION"]]
        command += [str(app), "--args", "-NSAppSleepDisabled", "YES", "--mute", *extra, *args]
        subprocess.run(command, check=True, timeout=30)
        end = time.monotonic() + start_seconds
        while time.monotonic() < end:
            mine = [p for p in claw_pids() - before if str(self.out) in subprocess.run(
                ["ps", "-o", "args=", "-p", str(p)], capture_output=True, text=True).stdout]
            if len(mine) == 1:
                self.pid = mine[0]
                break
            time.sleep(0.05)
        if self.pid is None:
            raise RuntimeError("own instance not found")
        if self.fast:
            self._gate_wait(start_seconds)
        else:
            # The arrival counter's value before this driver posts anything (None: an app without it).
            end = time.monotonic() + start_seconds
            while self._received()[0] is None and not self.movie().get("playing") and not (self.out / "movie-check.json").exists() and time.monotonic() < end and alive(self.pid):
                time.sleep(0.02)
            self.real_base = self._received()[0]
        return self.pid

    # Gate -----------------------------------------------------------------------------------------
    def movie(self):
        try:
            return json.loads((self.out / "movie-state.json").read_text())
        except (OSError, ValueError):
            return {}

    def gate(self):
        try:
            return json.loads((self.out / "gate.json").read_text())
        except (OSError, ValueError):
            return {}

    def _gate_wait(self, seconds=60):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            g = self.gate()
            if g.get("status") == "fail" or g.get("seq", -1) >= self.seq:
                self.frames = g.get("frame", self.frames)
                return g
            if self.movie().get("playing"):
                return {**g, "movie": True}
            if self.pid and not alive(self.pid):
                raise RuntimeError("instance exited")
            time.sleep(0.001)
        raise RuntimeError(f"gate did not answer line {self.seq} within {seconds} s (gate {self.gate()})")

    def _command(self, line):
        with self.control.open("a") as f:
            f.write(line + "\n")
        self.seq += 1

    def failed(self):
        return self.fast and self.gate().get("status") == "fail"

    def run(self, frames):
        """Fast only: run this many frames and pause."""
        if self.movie().get("playing"):
            time.sleep(0.02)
            return {**self.gate(), "movie": True}
        # Complete a frame interrupted by synchronous AVPlayer playback first.
        gate = self._gate_wait()
        if gate.get("status") == "fail":
            return gate
        self._command(f"run {int(frames)}")
        return self._gate_wait()

    # What the checks call -------------------------------------------------------------------------
    def query_step(self, milliseconds):
        """Choose the original route's timer-query increment without advancing a frame."""
        if not self.fast or milliseconds not in (0, 1):
            raise ValueError("query_step requires the fast gate and a 0 or 1 ms increment")
        self._gate_wait()
        self._command(f"query-step {milliseconds}")
        return self._gate_wait()

    def sleep(self, seconds):
        if self.fast:
            if self.movie().get("playing"):
                time.sleep(min(seconds, 0.1))
            else:
                self.run(round(seconds * FPS))
        else:
            time.sleep(seconds)

    def wait(self, predicate, seconds, step=3):
        """Until predicate() holds; False after `seconds` (frames of the game clock when fast)."""
        if not self.fast:
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                if predicate():
                    return True
                time.sleep(0.05)
            return False
        if predicate():
            return True
        for _ in range(int(seconds * FPS) // step):
            if self.run(step).get("status") == "fail":
                return predicate()
            if predicate():
                return True
        return False

    def post(self, *helper_args):
        """One post-window-input command to this instance; fast: pause until its events arrived."""
        if self.failed():
            raise RuntimeError("app failed before input")
        kind = str(helper_args[0])
        if kind == "key":
            # Polling inputs need a frame with the key held, not down and up
            # in the same paused frame. Both transitions still use real events.
            code, *flags = helper_args[1:]
            posted = self.post("press", code, "down", *flags)
            if self.fast:
                self.sleep(0.06)
            elif not self.movie().get("playing"):
                # Match the fast driver's four completed frames. A real key
                # can arrive while a synchronous fade pumps window events;
                # its receipt does not mean that frame (or live.json) is done.
                # A wall-clock sleep also returns in the middle of that fade.
                target = self.input_state()["frame"] + round(0.06 * FPS)
                if not self.wait(lambda: (self._received()[1] or 0) >= target
                                 or self.movie().get("playing"), 60):
                    raise RuntimeError(f"key {code} did not complete held frames through {target}")
            self.post("press", code, "up", *flags)
            return posted
        if kind != "press":
            raise ValueError(f"unsupported confirmed input: {helper_args}")
        code, direction = int(helper_args[1]), str(helper_args[2])
        vk = MAC_TO_VK[code]
        name = f"{vk}:{direction}"
        gated = self.fast and not self.movie().get("playing")
        if gated:
            # Finish any preceding run before choosing this event's frame.
            # A confirmed arrival alone is not proof of deterministic timing.
            gate = self._gate_wait()
            gated = not gate.get("movie") and not self.movie().get("playing")
        expected = self.transitions().get(name, 0) + 1
        if gated:
            planned_frame = gate["frame"]
            self._command(f"await {vk} {direction} {expected}")
        posted = self._post(helper_args)
        for attempt in range(2):
            end = time.monotonic() + 5
            while time.monotonic() < end:
                received = self.input_state()
                if received.get("transitions", {}).get(name, 0) >= expected:
                    if gated:
                        gate = self._gate_wait(5)
                        if received.get("frame") != planned_frame or gate.get("frame") != planned_frame:
                            raise RuntimeError(f"input {name} moved off planned frame {planned_frame}: "
                                               f"received {received.get('frame')}, gate {gate.get('frame')}")
                    return posted
                if not alive(self.pid):
                    raise RuntimeError("instance exited awaiting input")
                time.sleep(0.002)
            if attempt == 0:
                self.retries.append({"command": list(map(str, helper_args)), "transition": name,
                                     "expected": expected, "frame": self.frames})
                self._post(helper_args)
        raise RuntimeError(f"window event lost twice: {name}, expected {expected}, got {self.transitions()}")

    def input_state(self):
        try:
            return json.loads((self.out / "input.json").read_text())
        except (OSError, ValueError):
            return {}

    def transitions(self):
        return self.input_state().get("transitions", {})

    def _post(self, args):
        done = subprocess.run([self.helper, str(self.pid), *map(str, args)], capture_output=True,
                              text=True, timeout=10, check=True)
        posted = json.loads((done.stdout.strip().splitlines() or ["{}"]) [-1])
        if posted.get("status") != "posted":
            raise RuntimeError(f"event helper failed: {posted}")
        return posted

    def _received(self):
        """(input transitions the app received, its presented frame) from live.json; (None, None) if unread."""
        try:
            live = json.loads((self.out / "live.json").read_text())
            return live.get("input_received"), live.get("frame", 0)
        except (OSError, ValueError):
            return None, None

    def mark(self, name, seconds=5):
        """Save the next presented frame as <name>.png/.json; returns its record or None."""
        with self.control.open("a") as f:
            f.write(f"s {name}\n")
        path = self.out / f"{name}.json"
        if self.wait(path.exists, seconds, step=1):
            return json.loads(path.read_text())
        return None

    def close(self):
        if not self.pid:
            return
        if self.fast and not self.failed() and alive(self.pid):
            self._command("quit")
            end = time.monotonic() + 10
            while time.monotonic() < end and alive(self.pid):
                time.sleep(0.02)
        if alive(self.pid):
            subprocess.run(["kill", str(self.pid)])
            end = time.monotonic() + 5
            while time.monotonic() < end and alive(self.pid):
                time.sleep(0.05)
