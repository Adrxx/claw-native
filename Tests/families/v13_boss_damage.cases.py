"""Exact v1.3 damage-store regions, entered with full compiler contexts."""

from clawparity.cases import Case
from clawparity.env import NativeCompilerContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP


# The continuation is the first instruction beyond each owned region.
STORES = (
    (0x48111E, 0x481128, "ecx", "Raux contact"),
    (0x455BA7, 0x455BB1, "ecx", "Katherine contact"),
    (0x4A3CEA, 0x4A3CF4, "ecx", "Wolvington contact"),
    (0x40508E, 0x405098, "edx", "Aquatis contact"),
    (0x4A4941, 0x4A494B, "esi", "Wolvington magic"),
    (0x483521, 0x48352B, "esi", "RedTail knife"),
)
BOMB = (0x4474F1, 0x447503, "eax", "Gabriel bomb")
REGISTERS = ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp")
VALUES = (0, 1, 4, 5, 6, 9, 10, 11, 0xFF, 0x100, 0xFFFF,
          0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF)
FLAG_BITS = (0, 2, 4, 6, 7, 11)


def _flags(index):
    return 2 | sum(1 << bit for i, bit in enumerate(FLAG_BITS) if index & (1 << i))


def _case(random_source, site, serial, supplied, zero, flag_index, label):
    entry, continuation, receiver, name = site
    # Random bytes throughout every object catch misplaced/overwide stores,
    # including bytes immediately before and after the damage word.
    images = tuple(bytes(random_source.randrange(1, 256) for _ in range(0x280))
                   for _ in REGISTERS)
    register_words = tuple(random_source.getrandbits(32) for _ in REGISTERS)
    stack_tile = bytes(random_source.randrange(1, 256) for _ in range(128))
    profile = serial % 4
    displacement = (0, 1, 2, 3, 4, 16, 28, 32)[serial % 8]
    stack_pointer = STACK_TOP - (serial % 17) * 0x40

    def setup(env):
        objects = tuple(env.object(len(data), f"register-{reg}-guard", data=data)
                        for reg, data in zip(REGISTERS, images))
        target = objects[REGISTERS.index(receiver)] + 0x20 + displacement
        env.put(target + 0x120, supplied)
        env.write(STACK_BASE, stack_tile * (STACK_SIZE // len(stack_tile)))
        # No RET occurs in these regions. Keep the real continuation in the
        # stack as well, so an erroneous return or stack write is observable.
        env.put(stack_pointer, continuation)
        registration = stack_pointer - 0x180
        env.put(registration, 0xFFFFFFFF, continuation, register_words[0])

        context = NativeCompilerContext()
        context.size = 72
        context.version = 1
        context.inputMask = context.outputMask = 0x7FF
        for index, reg in enumerate(REGISTERS):
            if profile == 0:
                value = objects[index] + 0x20 + displacement
            elif profile == 1:
                value = register_words[index]
            elif profile == 2:
                value = target
            else:
                value = objects[index] + 0x24 + displacement
            setattr(context, reg, value)
        setattr(context, receiver, target)
        if entry == BOMB[0]:
            context.edi = zero
        context.esp = stack_pointer
        context.eip = entry
        context.eflags = _flags(flag_index)
        context.fsHead = registration if serial & 1 else 0xFFFFFFFF
        context.continuation = continuation
        context.reserved0 = context.reserved1 = 0
        return {"context": context}

    return Case(f"{name}: {label}; context {serial}", entry, setup,
                compiler_context=lambda tokens: tokens["context"])


def cases(random_source):
    # Every incoming arithmetic-flags combination must survive unconditional
    # stores. Existing damage spans signed, byte and half-word boundaries.
    for site in STORES:
        for index in range(64):
            supplied = (VALUES[index % len(VALUES)] if index < 32
                        else random_source.getrandbits(32))
            yield _case(random_source, site, index, supplied, 0, index,
                        f"replace {supplied:#010x}; flags {_flags(index):#x}")

    # Equality is against EDI, including nonzero EDI: it is not an unconditional
    # zero test. Unequal nonzero damage must survive exactly, without scaling.
    for index in range(64):
        value = (VALUES[index % len(VALUES)] if index < 32
                 else random_source.getrandbits(32))
        yield _case(random_source, BOMB, index, value, value, index,
                    f"equal supplied/EDI {value:#010x}")
        other = value ^ (1 << (index % 32))
        yield _case(random_source, BOMB, index + 64, value, other, 63 - index,
                    f"preserve {value:#010x} vs EDI {other:#010x}")

    # Original-constructor EDI=0 contexts explicitly exercise every important
    # nonzero damage boundary, plus low-byte/low-halfword compare impostors.
    for index, value in enumerate(VALUES):
        yield _case(random_source, BOMB, index + 128, value, 0, index,
                    f"original zero register with supplied {value:#010x}")
    for index, (value, zero) in enumerate((
            (0x100, 0), (0x10000, 0), (0x12340005, 5),
            (0xFFFF0005, 5), (0, 0x80000000), (0x80000000, 0),
            (0x7FFFFFFF, 0xFFFFFFFF), (0xFFFFFFFF, 0x7FFFFFFF))):
        yield _case(random_source, BOMB, index + 144, value, zero, index + 32,
                    f"full-width compare {value:#010x} vs {zero:#010x}")
