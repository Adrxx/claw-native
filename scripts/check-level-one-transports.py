"""Native check of the app host's Level 1 contextual transports against the join.

Compiles Sources/ClawNativeLevelTransport.cpp (the checks the app host applies
in ClawNativeMenuResources) and compares each transport's decision with the
rule in Tests/NativeLevelOne/native_join.py LevelOneNativeJoin, on fixed and
exhaustive cases. When the join's transport census
(work/native-level-one-join/transports.json) and the shipped election
(App/GameData/MENU/level-one-transports.json) exist, every transport shape the
join served is replayed and must be accepted. No guest code runs. Prints one
JSON line last.
"""
import ctypes as C
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeMenuBase.native_join import Source, X87, Call  # noqa: E402
from Tests.NativeLevelOne import native_join as join  # noqa: E402
from Tests.NativeLevelOne.trace import LevelOneTrace  # noqa: E402

U32 = C.c_uint32
SOURCE = ROOT / "Sources/ClawNativeLevelTransport.cpp"


class Owner(C.Structure):
    _fields_ = [(n, U32) for n in ("owned", "source_capability", "input_mask", "output_mask", "preserve_mask", "returns_x87")]


class Host(C.Structure):
    pass


ENTRY = C.CFUNCTYPE(U32, U32, U32, C.POINTER(U32), U32, C.POINTER(Host), C.POINTER(U32))
Host._fields_ = [("user", C.c_void_p), ("bytes", C.c_void_p),
                 ("call", C.CFUNCTYPE(U32, C.c_void_p, C.POINTER(Call))),
                 ("maximum_operations", U32), ("fault", U32), ("fault_address", U32), ("float_result", C.c_double),
                 ("entry_stack_pointer", U32), ("remaining_operations", C.c_void_p), ("compiler_context", C.c_void_p),
                 ("source_context", C.c_void_p), ("source_return_pc", U32), ("guest_session", C.c_void_p),
                 ("callback_cpu", C.c_void_p)]


def build():
    compiler = subprocess.check_output(["xcrun", "--find", "clang++"], text=True).strip()
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    digest = hashlib.sha256()
    for path in (SOURCE, ROOT / "Sources/ClawNativeLevelTransport.h", ROOT / "Sources/ClawRuntime.h",
                 ROOT / "Sources/ClawCanonicalDispatch.h"):
        digest.update(path.read_bytes())
    target = ROOT / "work/build/level-one-transports" / digest.hexdigest()[:24]
    target.mkdir(parents=True, exist_ok=True)
    library = target / "transports.dylib"
    if not library.exists():
        subprocess.run(["nice", "-n", "10", compiler, "-std=c++17", "-O1", "-isysroot", sdk, "-dynamiclib",
                        "-I" + str(ROOT / "Sources"), str(SOURCE), "-o", str(library)], check=True)
    lib = C.CDLL(str(library))
    for name in ("claw_level_narrow_source", "claw_level_tail_request_ok", "claw_level_tail_receipt",
                 "claw_level_physical_source_pop", "claw_level_physical_source_frame_ok",
                 "claw_level_x87_discard_elected", "claw_level_x87_exact_kind", "claw_level_x87_owned_invoke",
                 "claw_level_tail_only_ok", "claw_level_child_gap", "claw_level_is_game", "claw_level_game_range"):
        getattr(lib, name).restype = U32
    return lib


class Checks:
    def __init__(self):
        self.lib = build()
        self.results = {}

    def check(self, name, condition, detail=""):
        entry = self.results.setdefault(name, dict(cases=0, failures=[]))
        entry["cases"] += 1
        if not condition and len(entry["failures"]) < 5:
            entry["failures"].append(detail)

    def source_narrowing(self, census):
        rng = random.Random(7)
        pairs = [(0x7ff, 0x7ff, 0, 0x7ff, 0x7ff, 0x472)]
        pairs += [tuple(rng.choice((0, 0x472, 0x7ff, 0x5f1, rng.getrandbits(11))) for _ in range(6)) for _ in range(3000)]
        for ci, co, cp, ki, ko, kp in pairs:
            caller = Source(size=C.sizeof(Source), version=1, input_mask=ci, output_mask=co, preserve_mask=cp,
                            eax=1, ebx=2, ecx=3, edx=4, esi=5, edi=6, ebp=7, esp=0x2007000, eip=0x401000, eflags=2, fs_head=9)
            owner = Owner(1, 1, ki, ko, kp, 0)
            adapted = Source()
            got = self.lib.claw_level_narrow_source(C.byref(caller), C.byref(owner), C.byref(adapted))
            # The join (LevelOneNativeJoin.invoke): equal masks pass through,
            # an incompatible edge is refused, otherwise a narrowed copy.
            if (ci, co, cp) == (ki, ko, kp):
                want = 0
            elif ki & ~ci or ko & ~co or cp & ~kp:
                want = 2
            else:
                want = 1
            self.check("source-narrowing", got == want, f"{(ci, co, cp, ki, ko, kp)} -> {got}, join {want}")
            if got == 1:
                expected = Source.from_buffer_copy(caller)
                expected.input_mask, expected.output_mask, expected.preserve_mask = ki, ko, kp
                self.check("source-narrowing", bytes(adapted) == bytes(expected), "adapted copy")
                adapted.eax, adapted.esp, adapted.eip = 0x55, 0x2007004, 0x401234
                self.lib.claw_level_restore_source(C.byref(caller), C.byref(adapted))
                self.check("source-narrowing", (caller.eax, caller.esp, caller.eip, caller.input_mask) == (0x55, 0x2007004, 0x401234, ci),
                           "restore copies EAX..FS head only")
        for event in census.get("narrow", []):
            ci, co, cp, ki, ko, kp = (int(v, 16) for v in (*event[:3], *event[4:]))
            caller = Source(size=C.sizeof(Source), version=1, input_mask=ci, output_mask=co, preserve_mask=cp)
            owner, adapted = Owner(1, 1, ki, ko, kp, 0), Source()
            self.check("source-narrowing-census", self.lib.claw_level_narrow_source(C.byref(caller), C.byref(owner), C.byref(adapted)) == 1,
                       f"join narrowed {event}")
        root = Source()
        owner = Owner(1, 1, 0x7ff, 0x7ff, 0x472, 0)
        self.lib.claw_level_root_source(C.byref(root), C.byref(owner), U32(0x2007f00), U32(0x4254a0), U32(0x61000000), U32(0xffffffff))
        want = Source(size=C.sizeof(Source), version=1, input_mask=0x7ff, output_mask=0x7ff, preserve_mask=0x472,
                      esp=0x2007f00, eip=0x4254a0, ecx=0x61000000, eflags=2, fs_head=0xffffffff)
        self.check("source-root", bytes(root) == bytes(want), "root CPU differs from NativeJoin.invoke")

    def tail(self, census):
        def request(**changes):
            cpu = Source(size=C.sizeof(Source), version=1, input_mask=0x7ff, output_mask=0x7ff, esp=0x2006ffc, eip=0x49f890)
            receipt = join.Disposition()
            q = Call(function=0x4f6439, stack=0x2006ffc, return_pc=0x49f895, transfer_version=1, transfer_kind=1,
                     transfer_site=0x49f890, caller=0x49f8a0)
            q.source = C.addressof(cpu)
            q.disposition = C.addressof(receipt)
            for key, value in changes.items():
                setattr(q, key, value)
            return q, cpu, receipt
        q, cpu, receipt = request()
        self.check("source-tail", self.lib.claw_level_tail_request_ok(C.byref(q), U32(0x49f895)) == 1, "valid tail refused")
        self.check("source-tail", self.lib.claw_level_tail_request_ok(C.byref(q), U32(0x49f896)) == 0, "wrong continuation word")
        for change in (dict(transfer_version=2), dict(transfer_kind=0), dict(disposition=None), dict(source=None),
                       dict(count=1), dict(compiler=1), dict(callback_cpu=1), dict(return_pc=0), dict(stack=0x2006ff8)):
            bad, _, _ = request(**change)
            word = 0 if change.get("return_pc") == 0 else 0x49f895
            self.check("source-tail", self.lib.claw_level_tail_request_ok(C.byref(bad), U32(word)) == 0, f"accepted {change}")
        # Receipt only after the target returned to the continuation.
        self.check("source-tail", self.lib.claw_level_tail_receipt(C.byref(q), U32(0x2006ffc)) == 0, "receipt before return")
        cpu.eip, cpu.esp = 0x49f895, 0x2007000
        self.check("source-tail", self.lib.claw_level_tail_receipt(C.byref(q), U32(0x2006ffc)) == 1, "receipt refused")
        want = (C.sizeof(join.Disposition), 1, 1, 0x49f8a0, 0x49f890, 0x4f6439, 0x2006ffc, 0x49f895, C.addressof(q))
        got = (receipt.size, receipt.version, receipt.disposition, receipt.caller, receipt.site, receipt.target,
               receipt.entry_stack, receipt.return_pc, receipt.request)
        self.check("source-tail", got == want, f"receipt {got} != join {want}")
        for event in census.get("tail", []):
            sample, target, kind = event
            if kind == "physical":
                pop = U32()
                self.check("source-tail-census", self.lib.claw_level_physical_source_pop(U32(target), U32(sample["count"]), C.byref(pop)) == 1,
                           f"physical tail target {target:#x} not elected")
            self.check("source-tail-census", sample["count"] == 0 and sample["masks"] is not None, f"tail shape {sample}")

    def physical(self, census):
        targets = census.get("physical", {})
        for target, count in sorted(targets.items()):
            pop = U32()
            self.check("source-physical", self.lib.claw_level_physical_source_pop(U32(target), U32(count), C.byref(pop)) == 1,
                       f"physical source target {target:#x} not elected")
        for target, count in ((0x4a3050, 0), (0x4a3040, 1)):
            pop = U32(99)
            self.check("source-physical", self.lib.claw_level_physical_source_pop(U32(target), U32(count), C.byref(pop)) == 1 and pop.value == 0,
                       "CRT cdecl transport refused or popped caller arguments")
            self.check("source-physical", self.lib.claw_level_physical_source_pop(U32(target), U32(count + 1), C.byref(U32())) == 0,
                       "CRT transport accepted wrong argument count")
        self.check("source-physical", self.lib.claw_level_physical_source_pop(U32(0x4a3041), U32(1), C.byref(U32())) == 0,
                   "unreviewed physical source target accepted")
        cpu = Source(size=C.sizeof(Source), version=1, input_mask=0x7ff, output_mask=0x7ff, esp=0x2006f00, ebx=0x12)
        q = Call(function=0x4f65f2, count=1, stack=0x2006f00, return_pc=0x40b835)
        q.source = C.addressof(cpu)
        self.check("source-physical", self.lib.claw_level_physical_source_frame_ok(C.byref(q), U32(0x40b835)) == 1, "frame refused")
        self.check("source-physical", self.lib.claw_level_physical_source_frame_ok(C.byref(q), U32(0)) == 0, "wrong continuation")
        pop = U32()
        self.lib.claw_level_physical_source_pop(U32(0x4f65f2), U32(1), C.byref(pop))
        self.lib.claw_level_physical_source_return(C.byref(cpu), U32(0x40b835), pop, U32(0x61001000))
        # The tracer's returned(result, pop): EAX, EIP = continuation, ESP + 4 + pop.
        self.check("source-physical", (cpu.eax, cpu.eip, cpu.esp, cpu.ebx) == (0x61001000, 0x40b835, 0x2006f08, 0x12), "return frame")

    def x87(self, census):
        lib = self.lib
        for caller in (0x415df0, 0x418120, 0x41b630, 0x41e710, 0x4063b0, 0):
            for function in (0x420dd0, 0x420b60):
                self.check("x87-discard", lib.claw_level_x87_discard_elected(U32(caller), U32(function)) ==
                           int((caller, function) in join.X87_DISCARD), f"{caller:#x}->{function:#x}")
        # The rope jump-off caller was outside the Level 1 discovery route.
        # Check its original boundary independently of the join's route election.
        from Tests.clawparity.program import claw
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        from capstone.x86_const import X86_INS_CALL, X86_INS_FILD, X86_INS_FSTP, X86_OP_IMM, X86_OP_REG, X86_REG_ST0
        program = claw()
        section = next(s for s in program.sections if s.address <= 0x418399 < s.address + s.size)
        code = section.data[0x418399-section.address:0x4183cd-section.address]
        decoder = Cs(CS_ARCH_X86, CS_MODE_32); decoder.detail = True
        instructions = list(decoder.disasm(code, 0x418399))
        depth = 0
        for instruction in instructions:
            if instruction.address >= 0x4183c6:
                break
            if instruction.id == X86_INS_FILD:
                depth += 1
            elif instruction.id == X86_INS_FSTP:
                depth -= 1
            self.check("rope-x87-original", depth >= 0, "unbalanced pre-call stack")
        call, discard = instructions[-2:]
        self.check("rope-x87-original", depth == 0 and call.id == X86_INS_CALL and
                   call.operands[0].type == X86_OP_IMM and call.operands[0].imm == 0x420dd0 and
                   discard.id == X86_INS_FSTP and discard.operands[0].type == X86_OP_REG and
                   discard.operands[0].reg == X86_REG_ST0,
                   "original rope call must have an empty stack and discard its return")
        for caller in (0x4181c0, 0x4181bf, 0x4181c1, 0):
            for function in (0x420dd0, 0x420b60, 0x420dd1):
                self.check("rope-x87-election", lib.claw_level_x87_discard_elected(U32(caller), U32(function)) ==
                           int((caller, function) == (0x4181c0, 0x420dd0)), f"{caller:#x}->{function:#x}")
        for pair in census.get("discard", []):
            self.check("x87-discard-census", lib.claw_level_x87_discard_elected(U32(pair[0]), U32(pair[1])) == 1, f"{pair}")
        empty = X87()
        lib.claw_level_x87_empty_request(C.byref(empty))
        want = X87(); want.size = C.sizeof(X87); want.version = 1; want.control = 0x023f; want.push = 1
        self.check("x87-discard", bytes(empty) == bytes(want), "empty request differs from the join")
        # exact_game_call: owned (0,1) on an x87-result owner with room, balanced (0,0) on an ordinary owner.
        for count in range(9):
            for pop in range(2):
                for push in range(3):
                    for returns in (0, 1):
                        for dirty in (0, 1):
                            s = X87(size=C.sizeof(X87), version=1, control=0x023f, count=count, pop=pop, push=push)
                            if dirty: s.returned = 1
                            got = lib.claw_level_x87_exact_kind(C.byref(s), U32(returns))
                            if dirty: want = 0
                            elif (pop, push) == (0, 1) and returns and count < 8: want = 2
                            elif (pop, push) != (0, 0) or returns: want = 0
                            else: want = 1
                            self.check("x87-exact", got == want, f"count {count} pop {pop} push {push} returns {returns} dirty {dirty}: {got} != {want}")
        for key in census.get("exact", []):
            self.check("x87-exact-census", key in ("pop0 push0", "pop0 push1"), key)
        self.owned_result(census)

    def owned_result(self, census):
        lib = self.lib
        pushed = (0xc000000000000000, 0x3fff)  # 1.5

        def fake(mode):
            def entry(function, receiver, arguments, count, host, out):
                h = host.contents
                state = X87(size=C.sizeof(X87), version=1)
                q = Call(function=function, x87_count=4)
                q.x87_state = C.addressof(state)
                h.call(h.user, C.pointer(q))
                caller = X87.from_buffer_copy(state)
                result = X87.from_buffer_copy(caller)
                result.returned = result.pop = result.eax = 0
                result.push = 1
                if mode != "no-push":
                    for i in range(caller.count, 0, -1):
                        C.memmove(C.addressof(result.slots[i]), C.addressof(caller.slots[i - 1]), C.sizeof(result.slots[0]))
                    result.slots[0].significand, result.slots[0].exponent = pushed
                    result.count = caller.count + 1
                    result.status = (caller.status & ~0x3800) | ((((caller.status >> 11) + 7) & 7) << 11)
                if mode == "clobber" and caller.count:
                    result.slots[1].significand ^= 1 << 62
                if mode != "silent":
                    q = Call(function=function, x87_count=5)
                    q.x87_state = C.addressof(result)
                    h.call(h.user, C.pointer(q))
                out[0] = 7
                return 1
            return ENTRY(entry)
        refuse = C.CFUNCTYPE(U32, C.c_void_p, C.POINTER(Call))(lambda user, call: 0)
        for mode, accepted in (("ok", True), ("no-push", False), ("clobber", False), ("silent", False)):
            for depth in ((1, 3) if mode == "clobber" else (0, 1, 3)):
                caller = X87(size=C.sizeof(X87), version=1, control=0x023f, count=depth, status=0x3800)
                for i in range(depth):
                    caller.slots[i].significand, caller.slots[i].exponent = 0x8000000000000000 | i, 0x3fff + i
                state = X87.from_buffer_copy(caller)
                state.push = 1
                host = Host(call=refuse, entry_stack_pointer=0x2007000)
                out = U32()
                arguments = (U32 * 2)(1, 2)
                entry = fake(mode)
                got = lib.claw_level_x87_owned_invoke(entry, U32(0x420b60), U32(0x61000000), arguments, U32(2),
                                                      C.byref(host), C.byref(state), C.byref(out))
                ok = got == 1 and host.fault == 0
                self.check("x87-owned", ok == accepted, f"{mode} depth {depth}: {got} fault {host.fault}")
                if ok:
                    slots = [(state.slots[i].significand, state.slots[i].exponent) for i in range(state.count)]
                    want = [pushed] + [(caller.slots[i].significand, caller.slots[i].exponent) for i in range(depth)]
                    self.check("x87-owned", slots == want and (state.pop, state.push, state.returned, state.eax, out.value) == (0, 1, 1, 7, 7),
                               f"result {slots} {state.pop, state.push, state.returned, state.eax}")
        for key in census.get("owned", []):
            self.check("x87-owned-census", key.endswith("pop0 push1"), key)

    def tail_only(self, census, election):
        lib = self.lib
        thunks = {int(k, 16): int(v, 16) for k, v in election.get("tail_thunks", {}).items()}
        for thunk, target in census.get("tail_only", []):
            slot = thunks.get(thunk, 0)
            q = Call(function=target, receiver=0x61000000)
            self.check("tail-only-census", target in {int(a, 16) for a in election.get("tail_only", [])} and
                       lib.claw_level_tail_only_ok(C.byref(q), U32(slot), U32(target)) == 1, f"{thunk:#x}->{target:#x}")
        q = Call(function=0x433fb0, receiver=0x61000000)
        self.check("tail-only", lib.claw_level_tail_only_ok(C.byref(q), U32(0xb0), U32(0x433fb0)) == 1, "valid tail-only refused")
        self.check("tail-only", lib.claw_level_tail_only_ok(C.byref(q), U32(0), U32(0x433fb0)) == 0, "no thunk accepted")
        self.check("tail-only", lib.claw_level_tail_only_ok(C.byref(q), U32(0xb0), U32(0x433f30)) == 0, "foreign vtable accepted")
        for change in (dict(count=1), dict(source=1), dict(x87_count=2), dict(compiler=1), dict(transfer_version=1)):
            bad = Call(function=0x433fb0, receiver=0x61000000, **change)
            self.check("tail-only", lib.claw_level_tail_only_ok(C.byref(bad), U32(0xb0), U32(0x433fb0)) == 0, f"accepted {change}")

    def frames(self, census, election):
        lib = self.lib
        for extent in range(0, 0x800, 4):
            self.check("child-frame", lib.claw_level_child_gap(U32(extent)) == max(0x400, (extent + 0x4f) & ~0xf), f"extent {extent:#x}")
        extents = {int(k, 16): v for k, v in election.get("frame_extents", {}).items()}
        for caller, gap in census.get("gaps", []):
            self.check("child-frame-census", lib.claw_level_child_gap(U32(extents.get(caller, 0))) == gap, f"{caller:#x} gap {gap:#x}")
        for address in list(range(0x400ff0, 0x401010, 4)) + list(range(0x4a12f0, 0x4a1310, 4)) + \
                list(range(0x4b33f0, 0x4b3410, 4)) + list(range(0x4effe0, 0x4f0010, 4)) + list(range(0x4f4480, 0x4f4ab0, 4)):
            self.check("game-ownership", lib.claw_level_is_game(U32(address)) == int(LevelOneTrace.is_game(address)), f"{address:#x}")


def census_shapes():
    path = ROOT / "work/native-level-one-join/transports.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("status") != "native-complete":
        raise SystemExit(json.dumps(dict(status="fail", error="transport census is from an incomplete join")))
    shapes = dict(narrow=[], tail=[], physical={}, discard=[], exact=[], owned=[], tail_only=[], gaps=[])
    for event in data["events"]:
        kind, key = event["kind"], event["key"]
        if kind == "narrow":
            shapes["narrow"].extend(event["samples"])
        elif kind == "tail":
            target, which = key.split("->")[1].split()
            shapes["tail"].extend((s, int(target, 16), which) for s in event["samples"])
            if which == "physical":
                shapes["physical"][int(target, 16)] = 0
        elif kind == "source-call" and key.endswith("physical"):
            shapes["physical"][int(key.split("->")[1].split()[0], 16)] = event["samples"][0]["count"]
        elif kind == "x87-discard-call":
            shapes["discard"].append(tuple(int(a, 16) for a in key.split("->")))
        elif kind == "x87-exact":
            parts = key.split()
            shapes["exact"].append(" ".join(parts[1:3]))
            if parts[2] == "push1":
                shapes["owned"].append(" ".join(parts[1:3]))
        elif kind == "tail-only":
            shapes["tail_only"].append(tuple(int(a, 16) for a in key.split("->")))
        elif kind == "child-gap":
            caller, gap = key.split(":")
            shapes["gaps"].append((int(caller, 16), int(gap, 16)))
    return shapes


def main():
    census = census_shapes()
    path = ROOT / "App/GameData/MENU/level-one-transports.json"
    election = json.loads(path.read_text()) if path.exists() else {}
    checks = Checks()
    shapes = census or {}
    checks.source_narrowing(shapes)
    checks.tail(shapes)
    checks.physical(shapes)
    checks.x87(shapes)
    checks.tail_only(shapes, election)
    checks.frames(shapes, election)
    failures = {k: v["failures"] for k, v in checks.results.items() if v["failures"]}
    missing = [] if census is not None and election else ["census" if census is None else "election"]
    status = "fail" if failures else ("partial" if missing else "pass")
    print(json.dumps(dict(status=status, transports={k: v["cases"] for k, v in sorted(checks.results.items())},
                          failures=failures, missing=missing)))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
