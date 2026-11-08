"""Original-only counts for the descendants of one acquired audio pool.

The app records a pool immediately before 0x4b4430. Replay its ordered
eligibility and physical busy flags through unchanged v1.0 instructions:
0x4208e0 -> 0x4b45f0 -> 0x4b4430, all voice wrappers, and all list operations.
Only operator new (the audio_resource allocator fixture) and DirectSound COM
methods are supplied by the host. Enabled status/start wrappers each make
exactly one GetStatus/Play COM call, so those observations count the watched
0x4b3e70/0x4b3d80 descendants. No game routine is replaced by a fixture.

expected_pool_calls accepts {"manager_enabled": bool, "voices":
[{"eligible": bool, "playing": bool}, ...]}; equivalent shapes are cached.
Run this file directly for bounded busy/idle/disabled/ineligible controls.
"""
import argparse
from functools import lru_cache
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.env import Env
from Tests.clawparity.program import claw


@lru_cache(maxsize=1)
def original_program():
    return claw()  # The loader verifies the pinned v1.0 executable hash.


@lru_cache(maxsize=256)
def _original_pool_calls(manager_enabled, voice_states):
    env = Env(original_program())
    env.fixture(0x4f63ec, "cdecl", 1,
                lambda e, c: e.object(c.arguments[0], "allocated voice", fill=0),
                "operator new: declared audio_resource physical allocator")
    env._begin_case(random.Random(0))
    observations = {"GetStatus": 0, "Play": 0}
    manager = env.object(0x80, "manager", fill=0)
    device = env.object(4, "DirectSound", fill=0)
    device_vtable = env.object(0x48, "DirectSound vtable", fill=0)
    env.put(device, device_vtable)
    env.put(manager + 0x14, device)
    env.put(manager + 0x78, int(manager_enabled))

    def buffer(name, busy):
        obj = env.object(4, name, fill=0)
        vt = env.object(0x48, name + " vtable", fill=0)
        env.put(obj, vt)
        for slot, value in ((0x18, -1000), (0x1c, 0), (0x20, 22050), (0x24, int(busy))):
            def getter(e, c, slot=slot, value=value):
                if slot == 0x24:
                    observations["GetStatus"] += 1
                e.put(c.arguments[1], value)
                return 0
            env.put(vt + slot, env.stub(name + f" getter {slot:x}", "stdcall", 2, getter))
        for slot in (0x3c, 0x40, 0x44):
            env.put(vt + slot, env.stub(name + f" setter {slot:x}", "stdcall", 2, lambda e, c: 0))
        def play(e, c):
            observations["Play"] += 1
            return 0
        env.put(vt + 0x30, env.stub(name + " Play", "stdcall", 4, play))
        return obj

    source = buffer("source", False)
    duplicate = buffer("duplicate", False)
    def duplicate_buffer(e, c):
        e.put(c.arguments[2], duplicate)
        return 0
    env.put(device_vtable + 0x14, env.stub("DuplicateSoundBuffer", "stdcall", 3, duplicate_buffer))
    pool = env.object(0x38, "pool", fill=0)
    env.put(pool + 0x0c, source, manager)
    env.put(pool + 0x18, 22050, 0, -1000)
    voices = []
    for index, (eligible, playing) in enumerate(voice_states):
        voice = env.object(0x38, f"voice {index}", fill=0)
        physical = buffer(f"voice {index}", playing)
        env.put(voice + 0x0c, physical, manager)
        env.put(voice + 0x18, 22050, 0, -1000, 22050)
        env.put(voice + 0x30, int(eligible), pool)
        voices.append(voice)
    for index, voice in enumerate(voices):
        env.put(voice + 4, voices[index + 1] + 4 if index + 1 < len(voices) else 0,
                voices[index - 1] + 4 if index else 0)
    if voices:
        env.put(pool + 0x30, voices[0] + 4, voices[-1] + 4)
    sound = env.object(0x14, "sound", fill=0)
    env.put(sound + 0x10, pool)
    env.put(0x532c0c, 1)
    env.put(0x54130c, 0, 0, 0, 0)
    env.put(0x541178, *([-10000] + [int(-1000 * math.log2(100 / i)) for i in range(1, 100)] + [0]))
    env._freeze()
    outcome = env.run_original(0x4208e0, sound, [80, 0, 0, 0], check_objects=True)
    if not outcome.completed or outcome.errors or outcome.eax != int(manager_enabled):
        raise RuntimeError(f"original pool replay failed: {outcome.errors}, eax={outcome.eax}")
    return observations["GetStatus"], observations["Play"]


def expected_pool_calls(snapshot):
    """Replay this pre-invocation shape, returning exact watched call counts."""
    states = tuple((bool(v["eligible"]), bool(v["playing"])) for v in snapshot["voices"])
    statuses, starts = _original_pool_calls(bool(snapshot["manager_enabled"]), states)
    return {"4b3e70": statuses, "4b3d80": starts}


def controls():
    for idle_tail in (False, True):
        for busy in range(7):
            states = [(True, True)] * busy + ([(True, False)] if idle_tail else [])
            yield {"manager_enabled": True,
                   "voices": [{"eligible": e, "playing": p} for e, p in states]}
    for states in ([], [(True, True)], [(False, False), (True, True), (False, True)],
                   [(False, False), (True, True), (False, True), (True, False), (True, True)]):
        for enabled in (False, True):
            yield {"manager_enabled": enabled,
                   "voices": [{"eligible": e, "playing": p} for e, p in states]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-file", type=Path, help="JSON list of pool snapshots to replay")
    args = parser.parse_args()
    snapshots = json.loads(args.snapshot_file.read_text()) if args.snapshot_file else list(controls())
    cases = []
    for snapshot in snapshots:
        counts = expected_pool_calls(snapshot)
        statuses = 0
        if snapshot["manager_enabled"]:
            for voice in snapshot["voices"]:
                if voice["eligible"]:
                    statuses += 1
                    if not voice["playing"]:
                        break
        assert counts == {"4b3e70": statuses, "4b3d80": int(bool(snapshot["manager_enabled"]))}, counts
        cases.append({"snapshot": snapshot, "counts": counts})
    print(json.dumps({"check": "audio-pool-original", "status": "pass",
                      "program_sha256": original_program().sha256, "cases": cases}, indent=2))


if __name__ == "__main__":
    main()
