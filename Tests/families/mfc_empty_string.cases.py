"""Independent original empty-string construction and full source-frame witnesses."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP


def sample(rng, function, index, slot_value, alias=False):
    pattern = bytes(rng.randrange(256) for _ in range(1024))
    registers = [rng.getrandbits(32) for _ in range(7)]
    flags = 2 | rng.choice((0, 1, 4, 0x10, 0x40, 0x80, 0x800, 0x8d5))
    frame = STACK_TOP - rng.choice((0, 0x400, 0x2000, 0x6000))
    neighbors = bytes(rng.randrange(256) for _ in range(64))
    nested = index % 3

    def setup(env):
        env.write(STACK_BASE, pattern * (STACK_SIZE // len(pattern)))
        fs = 0xffffffff
        if nested:
            fs = STACK_BASE + 0x100
            env.put(fs, STACK_BASE + 0x140 if nested == 2 else 0xffffffff,
                    0x4f6439, 0x12345678)
            if nested == 2:
                env.put(STACK_BASE + 0x140, 0xffffffff, 0x4f6439, 0x89abcdef)
        if slot_value is not None:
            env.put(0x52e1cc, slot_value)
        receiver = 0x52e1cc if alias else env.object(64, 'receiver-with-canaries', data=neighbors) + 16 + index % 16
        context = NativeSourceContext()
        context.size, context.version = 72, 1
        context.inputMask = context.outputMask = 0x7ff
        context.preserveMask = 0x472
        for name, value in zip(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'), registers):
            setattr(context, name, value)
        context.eip, context.esp = function, frame
        context.eflags, context.fsHead = flags, fs
        if function == 0x4f6439:
            context.ecx = receiver
        return dict(source=context, receiver=receiver)

    return Case(f'empty-{function:x}-{index}-alias-{alias}', function, setup,
                receiver=(lambda t: t['receiver']) if function == 0x4f6439 else 0,
                source_context=lambda t: t['source'],
                source_return_pc=0x4f6441 if function == 0x4f6433 else 0x47ef33)


def cases(random_source):
    values = [None, 0, 1, 0xffffffff, 0x80000000, 0x52e1cc, 0x12345678, 0xa5c369f0]
    values += [random_source.getrandbits(32) for _ in range(24)]
    for function in (0x4f6433, 0x4f6439):
        for index, value in enumerate(values):
            yield sample(random_source, function, index, value)
    for index, value in enumerate(values[:8]):
        yield sample(random_source, 0x4f6439, index, value, alias=True)
