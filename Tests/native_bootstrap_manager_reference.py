"""Independent original outputs for the native application's manager joins.

The original executable is hash-checked by claw(). No native module is loaded.
"""
import json
import sys
from pathlib import Path

from Tests.clawparity.env import Env
from Tests.clawparity.program import claw


def reference(function, size, args=(), refuse=False):
    env = Env(claw())
    env.fixture(0x4f63ec, "cdecl", 1,
                lambda owner, call: 0 if refuse else owner.object(call.arguments[0], fill=0))
    receiver = env.object(size, "manager", fill=0xa5)
    env._freeze()
    side = env.run_original(function, receiver, args, check_objects=True)
    assert side.completed and not side.errors
    result = {"eax": side.eax, "arguments": args,
              "receiver_bytes": env.machine.read(receiver, size).hex()}
    if function == 0x493c20:
        token = env.machine.words(receiver + 4, 1)[0]
        result["lookup_bytes"] = env.machine.read(token, 128).hex() if token else None
        result["receiver_prefix"] = env.machine.read(receiver, 4).hex()
    return result


def variant(function):
    env = Env(claw())
    actor = env.object(0x1b4, "actor", fill=0)
    state = env.object(0xc0, "state", fill=0)
    env.put(actor + 0x6c, state)
    env.put(state + 0x1c, 1234)
    env._freeze()
    side = env.run_original(function, 0, (actor,), check_objects=True)
    assert side.completed and not side.errors and not side.events
    return {"function": function, "raw_eax": side.eax, "normalized_void_eax": 0,
            "selector": env.machine.words(0x537b8c, 1)[0],
            "state_bytes": env.machine.read(state, 0xc0).hex()}


if __name__ == "__main__":
    result = {
        "scope": "Original 493c20 and4ec010 outputs; allocator physical boundary only",
        "character": reference(0x493c20, 8),
        "character_refused": reference(0x493c20, 8, refuse=True),
        "resource": reference(0x4ec010, 40, (0xDEADBEEF, 0xFFFFFFFC, 0x81234567)),
        "variants": [variant(function) for function in (0x461fe0, 0x462000, 0x462020)],
    }
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + "\n")
