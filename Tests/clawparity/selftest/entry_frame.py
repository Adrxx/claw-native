"""Case-elected caller EBP at an ordinary outer entry (Env.entry_frame_pointer).

Independent synthetic x86: owned 0x401000 (cdecl, one argument) calls 0x401050 with the EBP it
inherited; 0x401050 is a compiler-context helper that returns [EBP + 4]. Owned 0x401010 overwrites
EBP and returns, which the elected entry frame must reject on the original side.
"""
import ctypes as C
import json
import random
import subprocess
import sys
from pathlib import Path

from .. import build
from ..env import ContextFault, Env, HarnessError, NativeHost, U32
from ..kernel import STACK_TOP
from ..program import Program, Section

CODE = {
    0x401000: "e84b000000 c3",
    0x401010: "bd78563412 c3",
    0x401050: "8b4504 c3",
}
A, CLOBBER, HELPER = 0x401000, 0x401010, 0x401050
MINIMAL = {"input_mask": 0x5c1, "output_mask": 0x5c1}


def program():
    text = bytearray(b"\xcc" * 0x100)
    for address, encoded in CODE.items():
        code = bytes.fromhex(encoded.replace(" ", ""))
        text[address - 0x401000:address - 0x401000 + len(code)] = code
    return Program("entry-frame-synthetic", "", 0x400000, 0x3000,
                   [Section(".text", 0x401000, 0x100, bytes(text)), Section(".data", 0x402000, 0x1000, bytes(0x1000))],
                   (0x401000, 0x401100), {})


def environment(masks=MINIMAL):
    env = Env(program())
    env.compiler_callees[HELPER] = dict(masks)
    return env


def rejected(function):
    try:
        function()
    except (ContextFault, HarnessError):
        return True
    return False


def run_pair(env, entry, function, argument, word, elect=True, offset=0x10):
    env._begin_case(None)
    frame = env.object(0x40, "caller frame", fill=0)
    env.put(frame + offset + 4, word)
    if elect:
        env.entry_frame_pointer(frame + offset)
    env._freeze()
    native = env.run_native(entry, function, 0, (argument,))
    original = env.run_original(function, 0, (argument,))
    return native, original


def runtime_checks(flavor="O2"):
    library = C.CDLL(str(build.library("entry-frame-selftest", [Path(__file__).with_name("EntryFrameModule.cpp")], flavor)))
    entry = library.claw_entry_frame_selftest_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    source = random.Random(0xEB9)
    found = {}
    env = environment()
    for trial in range(6):
        word, offset = source.randrange(1 << 32), 4 * source.randrange(0, 8)
        native, original = run_pair(env, entry, A, 5, word, offset=offset)
        found[f"elected_{trial}_equal"] = env.compare(native, original, True, STACK_TOP + 4) is None
        found[f"elected_{trial}_value"] = (native.completed and original.completed and not native.errors and
                                           not original.errors and native.eax == original.eax == word and
                                           native.bridged == [HELPER])
    # The election does not leak: the next case enters with the machine's previous EBP.
    native, original = run_pair(env, entry, A, 5, 0x1234, elect=False)
    found["unelected_native_refused"] = (not native.completed and
                                         any("inherited entry EBP" in str(e) for e in native.errors))
    found["unelected_original_has_no_frame"] = bool(original.errors) or original.eax != 0x1234
    # The original must return the elected EBP unchanged.
    _, original = run_pair(env, entry, CLOBBER, 5, 0x1234)
    found["clobbered_ebp_rejected"] = any("returned EBP" in str(e) for e in original.errors)
    # Native misuse of the inherited channel.
    for label, argument in (("argument", 0xBAD), ("receiver", 0xBAE)):
        native, _ = run_pair(env, entry, A, argument, 1)
        found[f"native_{label}_refused"] = not native.completed and any(
            "inherited entry EBP" in str(e) for e in native.errors)
    wide = environment({"input_mask": 0x5c3, "output_mask": 0x5c1})
    native, _ = run_pair(wide, entry, A, 5, 1)
    found["non_minimal_callee_refused"] = not native.completed and any(
        "inherited entry EBP" in str(e) for e in native.errors)
    # Election is setup-only, single, 32-bit, and ordinary-entry only.
    env._begin_case(None)
    env.entry_frame_pointer(0x1000)
    found["second_election_refused"] = rejected(lambda: env.entry_frame_pointer(0x2000))
    env._freeze()
    found["context_original_refused"] = rejected(lambda: env.run_original_context(A, None))
    found["context_native_refused"] = rejected(lambda: env.run_native(entry, A, 0, (), compiler_context=object()))
    env._begin_case(None)
    env._freeze()
    found["after_freeze_refused"] = rejected(lambda: env.entry_frame_pointer(0x1000))
    env._begin_case(None)
    found["wide_value_refused"] = rejected(lambda: env.entry_frame_pointer(1 << 32))
    found["boolean_value_refused"] = rejected(lambda: env.entry_frame_pointer(True))
    return found


def checks(flavor="O2"):
    return {f"runtime_{k}": v for k, v in runtime_checks(flavor).items()}


def sanitized_checks():
    command, environment_ = build.sanitized_python()
    if command is None:
        return {"available": False}
    child = subprocess.run(command + ["-m", "clawparity.selftest.entry_frame", "--sanitize"], env=environment_,
                           capture_output=True, text=True, timeout=180)
    if child.returncode:
        return {"passed": False, "detail": child.stderr[-2000:] or child.stdout[-2000:]}
    result = json.loads(child.stdout.strip().splitlines()[-1])
    return {"passed": not result["failed"], **result}


if __name__ == "__main__":
    values = checks("sanitize" if "--sanitize" in sys.argv else "O0" if "--O0" in sys.argv else "O2")
    print(json.dumps({"command": "selftest-entry-frame", "checked": len(values),
                      "failed": [k for k, v in values.items() if not v],
                      "status": "pass" if all(values.values()) else "fail"}))
    raise SystemExit(not all(values.values()))
