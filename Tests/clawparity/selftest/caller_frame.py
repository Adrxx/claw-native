"""Declared caller EBP for original callees, and the realloc/IsBadReadPtr/SetRect stand-ins.

Independent synthetic x86: owned 0x401000 sets EBP = this + 0x40 and calls 0x401050 once
(site 0x401008); owned 0x401020 sets EBP = this + 0x80 and calls it twice (0x40102b, 0x401037).
0x401050 (cdecl, one argument) returns and stores [EBP + 4] + argument, as an original helper
that reads its caller's EBP does.
"""
import ctypes as C
import json
import random
import subprocess
import sys
from pathlib import Path

from .. import build
from ..cases import caller_frame_errors
from ..env import Call, ContextFault, Env, HarnessError, NativeHost, U32
from ..fixtures import CATALOGUE, reallocate
from ..kernel import STACK_TOP
from ..program import Program, Section

CODE = {
    0x401000: "55 8d6940 ff742408 e843000000 83c404 5d c20400",
    0x401020: "55 8da980000000 ff742408 e820000000 83c404 ff742408 e814000000 83c404 5d c20400",
    0x401050: "8b4504 03442404 a310204000 c3",
}
A, B, CALLEE, GLOBAL = 0x401000, 0x401020, 0x401050, 0x402010
RANGES = {A: [(0x401000, 0x401014)], B: [(0x401020, 0x401043)]}


def program():
    text = bytearray(b"\xcc" * 0x100)
    for address, encoded in CODE.items():
        code = bytes.fromhex(encoded.replace(" ", ""))
        text[address - 0x401000:address - 0x401000 + len(code)] = code
    return Program("caller-frame-synthetic", "", 0x400000, 0x3000,
                   [Section(".text", 0x401000, 0x100, bytes(text)), Section(".data", 0x402000, 0x1000, bytes(0x1000))],
                   (0x401000, 0x401100), {0x402000: "SYNTH.dll!IsBadReadPtr"})


def manifest(callee=None, owned=None):
    return {"abi": "canonical",
            "owned": owned or [{"address": "0x401000", "convention": "thiscall", "argc": 1},
                               {"address": "0x401020", "convention": "thiscall", "argc": 1},
                               {"address": "0x401060", "convention": "cdecl", "argc": 1}],
            "callees": {"0x401050": callee if callee is not None else {
                "kind": "whole", "convention": "cdecl", "argc": 1,
                "caller_frame": [{"caller": "0x401000", "site": "0x401008", "ebp": {"base": "receiver", "offset": 64}}]}}}


def structure_checks():
    found = {"well_formed_accepted": caller_frame_errors(manifest()) == []}
    good = {"caller": "0x401000", "site": "0x401008", "ebp": {"base": "receiver", "offset": 64}}
    whole = {"kind": "whole", "convention": "cdecl", "argc": 1}
    bad = {
        "fixture_kind": {**whole, "kind": "fixture", "fixture": "scripted", "caller_frame": [good]},
        "x87_mixed": {**whole, "x87_args": 1, "caller_frame": [good]},
        "source_mixed": {**whole, "source_context": {}, "caller_frame": [good]},
        "no_signature": {"kind": "whole", "caller_frame": [good]},
        "empty_list": {**whole, "caller_frame": []},
        "not_a_list": {**whole, "caller_frame": good},
        "unowned_caller": {**whole, "caller_frame": [{**good, "caller": "0x401030"}]},
        "duplicate_caller": {**whole, "caller_frame": [good, {**good, "site": "0x40100c"}]},
        "duplicate_site": {**whole, "caller_frame": [good, {**good, "caller": "0x401020"}]},
        "extra_key": {**whole, "caller_frame": [{**good, "esi": {}}]},
        "unknown_base": {**whole, "caller_frame": [{**good, "ebp": {"base": "esi", "offset": 0}}]},
        "argument_range": {**whole, "caller_frame": [{**good, "ebp": {"base": "argument:1", "offset": 0}}]},
        "argument_padding": {**whole, "caller_frame": [{**good, "ebp": {"base": "argument:00", "offset": 0}}]},
        "boolean_offset": {**whole, "caller_frame": [{**good, "ebp": {"base": "receiver", "offset": True}}]},
        "wide_offset": {**whole, "caller_frame": [{**good, "ebp": {"base": "receiver", "offset": 1 << 32}}]},
        "receiver_of_cdecl": {**whole, "caller_frame": [{"caller": "0x401060", "site": "0x401068",
                                                         "ebp": {"base": "receiver", "offset": 0}}]},
    }
    for label, callee in bad.items():
        found[f"{label}_rejected"] = bool(caller_frame_errors(manifest(callee)))
    found["argument_base_accepted"] = caller_frame_errors(manifest({**whole, "caller_frame": [
        {"caller": "0x401060", "site": "0x401068", "ebp": {"base": "argument:0", "offset": -8}}]})) == []
    return found


def environment(declarations):
    env = Env(program())
    if declarations is not None:
        env.caller_frame(CALLEE, "cdecl", 1, declarations, RANGES)
    return env


def rejected(function):
    try:
        function()
    except (ContextFault, HarnessError):
        return True
    return False


def run_pair(env, entry, function, receiver_offset, argument, word):
    env._begin_case(None)
    receiver = env.object(0x100, "receiver", fill=0)
    env.put(receiver + receiver_offset, word)
    env._freeze()
    native = env.run_native(entry, function, receiver, (argument,))
    original = env.run_original(function, receiver, (argument,))
    return native, original, receiver


def runtime_checks(flavor="O2"):
    library = C.CDLL(str(build.library("caller-frame-selftest", [Path(__file__).with_name("CallerFrameModule.cpp")], flavor)))
    entry = library.claw_caller_frame_selftest_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    source = random.Random(0xCA11)
    found = {}
    declared = [(A, 0x401008, "receiver", None, 0x40)]
    env = environment(declared)
    for trial in range(6):
        word, argument = source.randrange(1 << 32), source.randrange(1, 0x1000)
        native, original, _ = run_pair(env, entry, A, 0x44, argument, word)
        expected = (word + argument) & 0xFFFFFFFF
        found[f"declared_{trial}_equal"] = env.compare(native, original, True, STACK_TOP + 8) is None
        found[f"declared_{trial}_value"] = (native.completed and original.completed and not native.errors and
                                            not original.errors and native.eax == original.eax == expected and
                                            native.bridged == [CALLEE])
    # Without the declaration the native bridge has no caller EBP: the case cannot pass silently.
    plain = environment(None)
    native, original, _ = run_pair(plain, entry, A, 0x44, 5, 0x1234)
    found["undeclared_native_differs"] = (not original.errors and original.eax == 0x1239 and
                                          (bool(native.errors) or not native.completed or native.eax != original.eax))
    # A declaration that disagrees with the original is a harness failure on the original side.
    wrong = environment([(A, 0x401008, "receiver", None, 0x44)])
    native, original, _ = run_pair(wrong, entry, A, 0x44, 5, 0x1234)
    found["wrong_offset_rejected_by_original"] = any("says EBP" in str(e) for e in original.errors)
    wrong_base = environment([(A, 0x401008, "entry_esp", None, 0x40)])
    _, original, _ = run_pair(wrong_base, entry, A, 0x44, 5, 0x1234)
    found["wrong_base_rejected_by_original"] = any("says EBP" in str(e) for e in original.errors)
    # Entry 0x401020 has no declaration: its native bridge is refused.
    native, original, _ = run_pair(env, entry, B, 0x84, 5, 0x1234)
    found["undeclared_entry_refused"] = (not native.completed and
                                         any("undeclared for entry" in str(e) for e in native.errors) and
                                         not original.errors)
    # A second CALL from a declared caller that is not its declared site is refused by the original side.
    partial = environment([(B, 0x40102b, "receiver", None, 0x80)])
    native, original, _ = run_pair(partial, entry, B, 0x84, 5, 0x1234)
    found["undeclared_site_rejected"] = any("undeclared caller-frame site" in str(e) for e in original.errors)
    both = environment([(A, 0x401008, "receiver", None, 0x40), (B, 0x40102b, "receiver", None, 0x80)])
    native, original, _ = run_pair(both, entry, A, 0x44, 9, 0x77)
    found["second_caller_declared"] = native.completed and native.eax == original.eax == 0x80
    # Native misuse of the declared callee's signature.
    for label, argument in (("argc", 0xBAD), ("receiver", 0xBAE)):
        native, _, _ = run_pair(env, entry, A, 0x44, argument, 1)
        found[f"native_{label}_mismatch_refused"] = not native.completed and any(
            "ordinary direct call" in str(e) for e in native.errors)
    # Malformed declarations are refused before any run.
    found["site_not_call_refused"] = rejected(lambda: environment([(A, 0x401004, "receiver", None, 0x40)]))
    found["site_outside_caller_refused"] = rejected(lambda: environment([(A, 0x40102b, "receiver", None, 0x40)]))
    found["unknown_caller_refused"] = rejected(lambda: environment([(0x401060, 0x401008, "receiver", None, 0)]))
    found["duplicate_caller_refused"] = rejected(lambda: environment([(A, 0x401008, "receiver", None, 0)] * 2))
    found["unknown_base_refused"] = rejected(lambda: environment([(A, 0x401008, "esi", None, 0)]))
    fixture_first = Env(program())
    fixture_first.fixture(CALLEE, "cdecl", 1, CATALOGUE["return-zero"])
    found["fixture_then_frame_refused"] = rejected(
        lambda: fixture_first.caller_frame(CALLEE, "cdecl", 1, declared, RANGES))
    frame_first = environment(declared)
    found["frame_then_fixture_refused"] = rejected(
        lambda: frame_first.fixture(CALLEE, "cdecl", 1, CATALOGUE["return-zero"]))
    found["frame_then_x87_refused"] = rejected(lambda: frame_first.whole_x87(CALLEE, "cdecl", 1))
    found["fastcall_signature_refused"] = rejected(
        lambda: Env(program()).caller_frame(CALLEE, "fastcall", 1, declared, RANGES))
    return found


def stand_in_checks():
    env = Env(program())
    env._begin_case(None)
    found = {}
    realloc = CATALOGUE["reallocate"]
    first = realloc(env, Call(0x4a9070, 0, 0, (0, 12), 0))
    found["realloc_null_allocates"] = env.spans.get(first) == 12
    env.write(first, bytes(range(1, 13)))
    grown = realloc(env, Call(0x4a9070, 0, 0, (first, 20), 0))
    found["realloc_grow_copies"] = (env.spans.get(grown) == 20 and first not in env.spans and
                                    env.read(grown, 12) == bytes(range(1, 13)))
    shrunk = realloc(env, Call(0x4a9070, 0, 0, (grown, 4), 0))
    found["realloc_shrink_copies"] = env.spans.get(shrunk) == 4 and env.read(shrunk, 4) == bytes(range(1, 5))
    failing = reallocate(fail=True)(env, Call(0x4a9070, 0, 0, (shrunk, 64), 0))
    found["realloc_failure_keeps_old"] = failing == 0 and env.spans.get(shrunk) == 4
    found["realloc_zero_frees"] = realloc(env, Call(0x4a9070, 0, 0, (shrunk, 0), 0)) == 0 and shrunk not in env.spans
    found["realloc_unknown_pointer_refused"] = rejected(lambda: realloc(env, Call(0x4a9070, 0, 0, (shrunk, 8), 0)))
    probe = CATALOGUE["is-bad-read-ptr"]
    live = env.object(16, "live", fill=0)
    found["readable_object"] = probe(env, Call(0x402000, 0, 0, (live, 16), 0)) == 0
    found["unreadable_tail"] = probe(env, Call(0x402000, 0, 0, (live + 8, 16), 0)) == 1
    found["readable_image"] = probe(env, Call(0x402000, 0, 0, (0x401000, 8), 0)) == 0
    found["unreadable_null"] = probe(env, Call(0x402000, 0, 0, (0, 4), 0)) == 1
    found["zero_size_readable"] = probe(env, Call(0x402000, 0, 0, (0, 0), 0)) == 0
    rect = env.object(16, "rect", fill=0xAA)
    found["set_rect"] = (CATALOGUE["set-rect"](env, Call(0x402000, 0, 0, (rect, 1, 2, 3, 4), 0)) == 1 and
                         [env.get(rect + 4 * i) for i in range(4)] == [1, 2, 3, 4])
    found["set_rect_empty"] = (CATALOGUE["set-rect-empty"](env, Call(0x402000, 0, 0, (rect,), 0)) == 1 and
                               env.read(rect, 16) == bytes(16))
    return found


def checks(flavor="O2"):
    found = {}
    for prefix, values in (("structure", structure_checks()), ("runtime", runtime_checks(flavor)),
                           ("stand_in", stand_in_checks())):
        found.update({f"{prefix}_{k}": v for k, v in values.items()})
    return found


def sanitized_checks():
    command, environment_ = build.sanitized_python()
    if command is None:
        return {"available": False}
    child = subprocess.run(command + ["-m", "clawparity.selftest.caller_frame", "--sanitize"], env=environment_,
                           capture_output=True, text=True, timeout=180)
    if child.returncode:
        return {"passed": False, "detail": child.stderr[-2000:] or child.stdout[-2000:]}
    result = json.loads(child.stdout.strip().splitlines()[-1])
    return {"passed": not result["failed"], **result}


if __name__ == "__main__":
    values = checks("sanitize" if "--sanitize" in sys.argv else "O0" if "--O0" in sys.argv else "O2")
    print(json.dumps({"command": "selftest-caller-frame", "checked": len(values),
                      "failed": [k for k, v in values.items() if not v],
                      "status": "pass" if all(values.values()) else "fail"}))
    raise SystemExit(not all(values.values()))
