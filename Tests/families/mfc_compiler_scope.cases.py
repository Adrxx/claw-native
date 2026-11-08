"""Blind original compiler-scope cases with explicit registers and caller frame."""
from clawparity.cases import Case
from clawparity.env import NativeCompilerContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

HELPER = 0x4a48c0
CONTINUATIONS = (0x50233f, 0x502373, 0x50342a)
HANDLERS = (0, 1, 0xffffffff, 0x12345678, 0x508525, 0x508539, 0x508bf8,
            0x80000000, 0xdeadbeef)
FLAG_BITS = (1, 4, 16, 64, 128, 2048)


def setup(frame, handler, nested, old_base, continuation, registers, flags, words):
    def build(env):
        # Seed the complete touched frame and surviving neighboring caller words.
        # At the lowest valid ESP the temporary return push reaches STACK_BASE.
        start = max(STACK_BASE, frame - 32)
        end = min(STACK_BASE + STACK_SIZE, frame + 32)
        env.put(start, *words[:(end - start) // 4])
        env.put(frame, continuation)
        head = 0xffffffff
        if nested:
            # Keep distinct existing records away from every touched frame word.
            head = STACK_BASE + (0x1000 if frame >= STACK_BASE + 0x4000 else 0x10000)
            env.put(head - 4, 0x71234567)
            env.put(head, head + 16, 0x508525, 0x13579bdf, 0x2468ace0)
            env.put(head + 16, head + 32, 0x508539, 0xfffffffe, 0x87654321)
            env.put(head + 32, 0xffffffff, 0x508bf8, 0x10293847, 0xfedcba98)
        context = NativeCompilerContext(
            72, 1, 0x7ff, 0x7ff, handler, *registers,
            old_base, frame, HELPER, flags, head, continuation, 0, 0)
        return {"context": context}
    return build


def compiler_case(label, random_source, frame, handler, nested, old_base,
                  continuation, flags):
    registers = [random_source.getrandbits(32) for _ in range(5)]
    words = [random_source.getrandbits(32) | 1 for _ in range(16)]
    return Case(label, HELPER,
                setup(frame, handler, nested, old_base, continuation,
                      registers, flags, words),
                compiler_context=lambda tokens: tokens["context"])


def cases(random_source):
    frames = (STACK_BASE + 16, STACK_BASE + 20, STACK_BASE + 0x100,
              STACK_BASE + 0x8000, STACK_TOP, STACK_BASE + STACK_SIZE - 16)
    serial = 0
    for frame in frames:
        old_bases = (0, 0xffffffff, 1, 0x12345678, frame + 4, frame + 1,
                     0x80000000, random_source.getrandbits(32))
        for continuation in CONTINUATIONS:
            for old_base in old_bases:
                for nested in (False, True):
                    handler = HANDLERS[serial % len(HANDLERS)]
                    flags = 2 if serial % 2 == 0 else 0x8d7
                    yield compiler_case(
                        f"edge {serial} esp{frame:x} ebp{old_base:x} "
                        f"return{continuation:x} nested{int(nested)}",
                        random_source, frame, handler, nested, old_base,
                        continuation, flags)
                    serial += 1
    # Every combination of the six transported arithmetic flags is preserved.
    for combination in range(64):
        flags = 2 | sum(bit for index, bit in enumerate(FLAG_BITS)
                        if combination & (1 << index))
        yield compiler_case(
            f"arithmetic flags {flags:x}", random_source,
            frames[combination % len(frames)],
            HANDLERS[combination % len(HANDLERS)], bool(combination % 2),
            random_source.getrandbits(32), CONTINUATIONS[combination % 3], flags)
    for index in range(64):
        frame = STACK_BASE + 16 + 4 * random_source.randrange((STACK_SIZE - 16) // 4)
        flags = 2 | (random_source.getrandbits(32) & 0x8d5)
        yield compiler_case(
            f"random opaque compiler scope {index}", random_source, frame,
            random_source.getrandbits(32), bool(index % 3),
            random_source.getrandbits(32), CONTINUATIONS[index % 3], flags)
