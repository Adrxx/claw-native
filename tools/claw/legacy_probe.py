"""Runs one legacy comparison script under observation, without changing it.

    python tools/claw/legacy_probe.py Tests/compare_x.py [arguments...]      (run from the tree to test)

Environment: CLAW_PROBE_OUT names the JSON file to write; CLAW_PROBE_SALT, when
not 0, changes every random seed the script uses, so the script runs on inputs
its author never saw. The probe records which original functions the script
called directly and which original instructions ran.
"""
import hashlib
import json
import os
import random
import runpy
import sys

TEXT = (0x401000, 0x50ADB5)
salt = int(os.environ.get("CLAW_PROBE_SALT", "0"))
roots, blocks = {}, set()


def mixed(seed):
    if seed is None or not salt:
        return seed
    return int.from_bytes(hashlib.sha256(f"{salt}:{seed!r}".encode()).digest()[:8], "little")


if salt:
    plain_seed = random.seed

    class Salted(random.Random):
        def __init__(self, x=None):
            super().__init__(mixed(x))

        def seed(self, a=None, version=2):
            super().seed(mixed(a), version)

    random.seed = lambda a=None, version=2: plain_seed(mixed(a), version)
    random.Random = Salted

import unicorn  # noqa: E402

plain_init, plain_start = unicorn.Uc.__init__, unicorn.Uc.emu_start


def on_block(uc, address, size, user):
    if TEXT[0] <= address < TEXT[1]:
        blocks.add((address, size))


def watched_init(self, *arguments, **keywords):
    plain_init(self, *arguments, **keywords)
    self.hook_add(unicorn.UC_HOOK_BLOCK, on_block)


def watched_start(self, begin, until, timeout=0, count=0):
    if TEXT[0] <= begin < TEXT[1]:
        roots[begin] = roots.get(begin, 0) + 1
    return plain_start(self, begin, until, timeout, count)


unicorn.Uc.__init__ = watched_init
unicorn.Uc.emu_start = watched_start


def save():
    merged = []
    for address, size in sorted(blocks):
        if merged and address <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], address + size)
        else:
            merged.append([address, address + size])
    with open(os.environ["CLAW_PROBE_OUT"], "w") as out:
        json.dump({"salt": salt, "roots": {f"{a:#x}": n for a, n in sorted(roots.items())}, "executed": merged}, out)


if __name__ == "__main__":
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    sys.path.insert(0, os.path.join(os.getcwd(), "Tests"))
    try:
        runpy.run_path(script, run_name="__main__")
    finally:
        save()
