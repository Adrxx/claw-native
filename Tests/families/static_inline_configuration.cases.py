"""Blind original display stores, including the complete optional CPU state."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

ENTRY = 0x425230
RETURN_PC = 0x4A5896  # Genuine static-table driver's indirect-call continuation.
GLOBAL_GUARD = 0x5370B8


def setup_case(random_source, index, source=False):
    # All bytes in the four destination words start poisoned. Guards on both
    # sides distinguish shifted, widened and additional global stores.
    poison = bytes(random_source.randrange(1, 256) for _ in range(48))
    boundaries = (0xFFFFFFFF, 0x80808080, 0x01010101, 0xA55AA55A,
                  0x7FFFFFFF, 0x80000001, 0xFFFFFFFF, 0xFEFDFCFB)
    words = tuple(boundaries[(index + word) % len(boundaries)]
                  if index < 8 else int.from_bytes(poison[16+4*word:20+4*word], 'little')
                  for word in range(4))
    if not source:
        def ordinary(env):
            env.write(GLOBAL_GUARD, poison)
            env.put(0x5370C8, *words)
        return ordinary

    stack = random_source.randbytes(STACK_SIZE)
    registers = [random_source.getrandbits(32) for _ in range(7)]
    # Explicit zero and unsigned boundaries supplement distinct random words.
    registers[index % 7] = (0, 1, 0xFFFFFFFF, 0x80000000)[index % 4]
    flag_bits = (1, 4, 0x10, 0x40, 0x80, 0x800)
    flags = 2 | (flag_bits[index] if index < 6 else
                 (0x8D5 ^ flag_bits[index - 6]) if index < 12 else
                 random_source.getrandbits(12) & 0x8D5)
    frame = STACK_TOP - (0, 4, 0x100, 0x2000, 0x6000, 0x9000)[index % 6]
    fs_first, fs_second = STACK_BASE + 0x100, STACK_BASE + 0x180

    def explicit(env):
        env.write(GLOBAL_GUARD, poison)
        env.put(0x5370C8, *words)
        env.write(STACK_BASE, stack)
        env.put(fs_first, fs_second, ENTRY, 0xFFFFFFFF)
        env.put(fs_second, 0xFFFFFFFF, ENTRY, 0xFFFFFFFF)
        env.put(frame, RETURN_PC)
        context = NativeSourceContext()
        context.size, context.version = 72, 1
        context.inputMask = context.outputMask = 0x7FF
        context.preserveMask = 0x472
        for name, value in zip(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'), registers):
            setattr(context, name, value)
        context.esp, context.eip = frame, ENTRY
        context.eflags = flags
        context.fsHead = (0xFFFFFFFF, fs_second, fs_first)[index % 3]
        return {'source': context}
    return explicit


def cases(random_source):
    for index in range(16):
        yield Case(f'ordinary-poison-{index}', ENTRY,
                   setup_case(random_source, index))
    for index in range(24):
        yield Case(f'full-source-poison-{index}', ENTRY,
                   setup_case(random_source, index, source=True),
                   source_context=lambda tokens: tokens['source'],
                   source_return_pc=RETURN_PC)
