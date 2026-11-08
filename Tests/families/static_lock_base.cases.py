"""Independent complete leaf cases with physical source frames and guarded backing."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

ENTRY = 0x4A2F62
CONTINUATION = 0x4A2D1E
FLAGS = (1, 4, 16, 64, 128, 2048)


def profile(random_source, index, flags):
    words = [random_source.getrandbits(32) for _ in range(7)]
    argument = (0, 1, 0xFFFFFFFF, 0x80000000, 0xDEADBEEF,
                random_source.getrandbits(32))[index % 6]
    frame = (STACK_TOP - 40, STACK_BASE, STACK_BASE + STACK_SIZE - 8,
             STACK_TOP - 0x120, STACK_BASE + 0x700)[index % 5]
    offset = (0, 4, 12, 28, 60)[index % 5]
    initial = bytes(random_source.getrandbits(8) for _ in range(offset + 40))
    stack_poison = bytes(random_source.getrandbits(8) for _ in range(128))
    field = (0, 1, 0xFFFFFFFF, 0x80000000, 0x55555555,
             0xAAAAAAAA, random_source.getrandbits(32))[index % 7]

    def setup(env):
        # Vary allocation addresses and keep separate neighbors observable.
        env.object(12 + index * 4, "preceding guard", data=bytes([0xA7]) * (12 + index * 4))
        backing = env.object(len(initial), "receiver backing", data=initial)
        receiver = backing + offset
        env.object(32, "following guard", data=bytes([0xD3]) * 32)
        env.put(receiver + 4, field)
        poison_start = min(max(frame - 64, STACK_BASE), STACK_BASE + STACK_SIZE - 128)
        env.write(poison_start, stack_poison)
        # Physical RET4 consumes the genuine continuation and exactly one word.
        env.put(frame, CONTINUATION, argument)
        fs_head = 0xFFFFFFFF
        if index % 3:
            outer = STACK_BASE + 0x1000
            inner = outer + 16
            env.put(outer, 0xFFFFFFFF, CONTINUATION, words[0])
            env.put(inner, outer, CONTINUATION, words[1])
            fs_head = outer if index % 3 == 1 else inner
        source = NativeSourceContext()
        source.size, source.version = 72, 1
        source.inputMask, source.outputMask, source.preserveMask = 0x7FF, 0x7FF, 0
        source.eax, source.ebx, source.edx, source.esi, source.edi, source.ebp = words[:6]
        source.ecx = receiver
        source.esp, source.eip, source.eflags, source.fsHead = frame, ENTRY, flags, fs_head
        return {"receiver": receiver, "argument": argument, "source": source}

    return Case(f"full source profile {index} flags {flags:#x}", ENTRY, setup,
                receiver=lambda t: t["receiver"], arguments=(lambda t: t["argument"],),
                source_context=lambda t: t["source"], source_return_pc=CONTINUATION)


def cases(random_source):
    # Every arithmetic input combination challenges the exact AND flag result.
    for index in range(64):
        flags = 2 | sum(bit for n, bit in enumerate(FLAGS) if index & (1 << n))
        yield profile(random_source, index, flags)
    for index in range(64, 96):
        flags = 2 | sum(bit for bit in FLAGS if random_source.randrange(2))
        yield profile(random_source, index, flags)
    # Last eight mapped stack bytes provide genuine live borrowed backing.
    # The physical caller frame and FS registrations are kept elsewhere.
    for index in range(96, 108):
        flags = 2 | sum(bit for bit in FLAGS if random_source.randrange(2))
        case = profile(random_source, index, flags)
        original_setup = case.setup
        poison = (random_source.getrandbits(32), random_source.getrandbits(32))

        def boundary_setup(env, original_setup=original_setup, poison=poison):
            tokens = original_setup(env)
            receiver = STACK_BASE + STACK_SIZE - 8
            source = tokens["source"]
            source.esp = STACK_TOP - 40
            source.ecx = receiver
            env.put(source.esp, CONTINUATION, tokens["argument"])
            env.put(receiver, *poison)
            tokens["receiver"] = receiver
            return tokens

        case.label = f"mapped-end receiver profile {index} flags {flags:#x}"
        case.setup = boundary_setup
        yield case
