"""Check the native Level 2 and Level 4 boss base-call boundaries; no guest execution.

Uses the shared native transport build and ABI. The original is read only
through the hash-checked program loader. This is an integration check, not a
family admission check. Prints one JSON result last.
"""
import ctypes as C
import importlib.util
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw


def main():
    spec = importlib.util.spec_from_file_location(
        "level_one_transport_checks", ROOT / "scripts/check-level-one-transports.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    Call, U32 = shared.Call, shared.U32
    results = []

    def check(name, condition):
        results.append((name, bool(condition)))

    program = claw()

    def read(address, size):
        for section in program.sections:
            offset = address - section.address
            if 0 <= offset and offset + size <= len(section.data):
                return section.data[offset:offset + size]
        raise ValueError(f"unbacked original address {address:#x}")

    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86_const import X86_INS_CALL, X86_INS_RET, X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True

    def instruction(address, identity, argument):
        insn = next(decoder.disasm(read(address, 15), address, count=1))
        return (insn.id == identity and len(insn.operands) == 1
                and insn.operands[0].type == X86_OP_IMM
                and insn.operands[0].imm == argument)

    check("original-direct-base-call", instruction(0x40e668, X86_INS_CALL, 0x44e0c0))
    for address in (0x40e68c, 0x44e113):
        check(f"original-ret4-{address:x}", instruction(address, X86_INS_RET, 4))
    words = struct.unpack("<45I", read(0x50f1ac, 0xb4))
    check("original-raux-override-slot", words[0x5c // 4] == 0x40e660)
    check("original-base-absent-from-raux-vtable", 0x44e0c0 not in words)

    check("original-katherine-direct-base-call", instruction(0x40e668, X86_INS_CALL, 0x44e0c0))
    check("original-katherine-ret4", instruction(0x40e68c, X86_INS_RET, 4))
    katherine = struct.unpack("<45I", read(0x50e2a4, 0xb4))
    check("original-katherine-override-slot", katherine[0x5c // 4] == 0x40e660)
    check("original-base-absent-from-katherine-vtable", 0x44e0c0 not in katherine)

    lib = shared.build()
    admit = lib.claw_level_boss_base_call_ok
    admit.argtypes = [C.POINTER(Call), U32, U32, U32]
    admit.restype = U32

    def request():
        q = Call(function=0x44e0c0, receiver=0x61001000, count=1)
        q.arguments[0] = 0x61002000
        return q

    def run(name, q, expected, caller=0x40e660, vtable=0x50f1ac, slot=0x40e660):
        before = bytes(q) if q is not None else None
        got = admit(C.byref(q) if q is not None else None, caller, vtable, slot)
        check(name, got == expected)
        if q is not None:
            check(name + "-preserves-request", bytes(q) == before)

    run("null-request", None, 0)
    for receiver in (1, 0x61001000, 0xffffffff):
        for argument in (0, 1, 0x61002000, 0xffffffff):
            q = request()
            q.receiver, q.arguments[0] = receiver, argument
            run(f"ordinary-{receiver:x}-{argument:x}", q, 1)
    for receiver in (1, 0x61001000, 0xffffffff):
        for argument in (0, 1, 0x61002000, 0xffffffff):
            q = request()
            q.receiver, q.arguments[0] = receiver, argument
            run(f"katherine-{receiver:x}-{argument:x}", q, 1,
                caller=0x40e660, vtable=0x50e2a4, slot=0x40e660)
    for caller, vtable, slot in ((0x40aaf0, 0x50e2a4, 0x40aaf0),
                                (0x40aaf0, 0x50b38c, 0x40aaf0),
                                (0x40e660, 0x50e2a4, 0x44e0c0),
                                (0x483e10, 0x50f394, 0x483e10)):
        run(f"unreviewed-{caller:x}-{vtable:x}-{slot:x}", request(), 0,
            caller=caller, vtable=vtable, slot=slot)
    q = request()
    q.stack = 0x2007000
    run("ordinary-tracked-stack", q, 1)

    for name, values in (
            ("caller", (0, 0x40e65f, 0x40e661, 0x44e0c0)),
            ("vtable", (0, 0x50f1a8, 0x50f1b0)),
            ("slot", (0, 0x44e0c0, 0x40e661))):
        for value in values:
            run(f"invalid-{name}-{value:x}", request(), 0, **{name: value})

    invalid = {
        "function": (0, 0x44e0bf, 0x44e0c1, 0x40e660),
        "count": (0, 2, 32, 33, 0xffffffff),
        "receiver": (0,), "receiver2": (1, 0xffffffff),
        "compiler": (1,), "source": (1,), "callback_cpu": (1,),
        "callback_activation": (1, 1 << 32),
        "x87_count": (1, 2, 3, 4, 5), "x87_argument": (1.0, -1.0),
        "x87_state": (1,), "x87_operation": (1,),
        "return_pc": (0x40e66d,), "transfer_version": (1,),
        "transfer_kind": (1,), "transfer_site": (0x40e668,),
        "caller": (0x40e660,), "disposition": (1,),
    }
    for field, values in invalid.items():
        for index, value in enumerate(values):
            q = request()
            setattr(q, field, value)
            run(f"invalid-{field}-{index}", q, 0)
            run(f"katherine-invalid-{field}-{index}", q, 0,
                caller=0x40e660, vtable=0x50e2a4, slot=0x40e660)

    failures = [name for name, passed in results if not passed]
    print(json.dumps(dict(command="check-level-two-boss-transport",
                          status="fail" if failures else "pass",
                          checks=len(results), failures=failures)))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
