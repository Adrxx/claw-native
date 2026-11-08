"""Original strdup: full source frames, exact copies and post-malloc rescans."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.fixtures import halt
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

ENTRY = 0x4a56e0
MALLOC = 0x4a48e0
RETURN_PC = 0x5025af


def duplicate(random_source, label, payload, alignment=0, mode='success', replacement=None):
    frame = STACK_TOP - random_source.choice((0, 0x400, 0x2000, 0x6000))
    pattern = bytes(random_source.randrange(256) for _ in range(1024))
    stack = pattern * (STACK_SIZE // len(pattern))
    registers = [random_source.getrandbits(32) for _ in range(7)]
    flags = 2 | random_source.choice((0, 1, 4, 0x10, 0x40, 0x80, 0x800, 0x8d5))
    nested = random_source.randrange(3)
    padding = bytes(random_source.randrange(1, 256) for _ in range(24))
    fill = random_source.randrange(1, 256)

    def setup(env):
        env.write(STACK_BASE, stack)
        fs = 0xffffffff
        if nested:
            fs = STACK_BASE + 0x100
            second = STACK_BASE + 0x140
            env.put(fs, second if nested == 2 else 0xffffffff, 0x4a56e0, 0x12345678)
            if nested == 2:
                env.put(second, 0xffffffff, 0x4a56e0, 0x89abcdef)
        source = NativeSourceContext()
        source.size, source.version = 72, 1
        source.inputMask = source.outputMask = 0x7ff
        source.preserveMask = 0x472
        for name, value in zip(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'), registers):
            setattr(source, name, value)
        source.esp, source.eip = frame, ENTRY
        source.eflags, source.fsHead = flags, fs
        pointer = 0
        if payload is not None:
            offset = 8 + alignment
            data = padding[:offset] + payload + b'\0' + padding
            pointer = env.object(len(data), 'input-with-canaries', data=data) + offset
        observation = env.object(64, 'malloc-observation', fill=0xa7)

        def malloc(env, call):
            env.put(observation, call.receiver, call.arguments[0], call.source_return_pc)
            context = call.source_context
            if context is not None:
                env.put(observation + 12, *(getattr(context, field) for field in
                    ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eip', 'eflags', 'fsHead')))
            if mode == 'halt':
                return halt()(env, call)
            if mode == 'failure':
                return 0
            result = env.object(call.arguments[0], 'fresh-exact-allocation', fill=fill)
            if replacement is not None:
                env.write(pointer, replacement + b'\0')
            return result

        env.override(MALLOC, malloc)
        return {'source': source, 'pointer': pointer}

    return Case(label, ENTRY, setup, arguments=(lambda t: t['pointer'],),
                source_context=lambda t: t['source'], source_return_pc=RETURN_PC,
                expect='halt' if mode == 'halt' else 'return')


def cases(random_source):
    for index in range(8):
        yield duplicate(random_source, f'null-{index}', None)
    lengths = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 15, 16, 17, 31, 32, 33,
               63, 64, 65, 127, 128, 129, 255, 256, 257, 1023, 1024, 1025)
    for length in lengths:
        for alignment in range(4):
            payload = bytes(((i * 73 + alignment * 29) % 255) + 1 for i in range(length))
            yield duplicate(random_source, f'length-{length}-alignment-{alignment}', payload, alignment)
    for length in (0, 1, 3, 4, 7, 16, 255, 1024):
        payload = bytes(random_source.randrange(1, 256) for _ in range(length))
        for mode in ('failure', 'halt'):
            yield duplicate(random_source, f'{mode}-length-{length}', payload, length % 4, mode)
    for length in (1, 3, 4, 5, 7, 8, 9, 15, 16, 17, 63, 64, 65, 255):
        payload = bytes(random_source.randrange(1, 256) for _ in range(length))
        for changed_length in sorted(set((0, 1, length // 2, max(0, length - 1), length))):
            replacement = bytes(random_source.randrange(1, 256) for _ in range(changed_length))
            yield duplicate(random_source, f'rescan-{length}-to-{changed_length}', payload,
                            length % 4, replacement=replacement)
    for index in range(32):
        length = random_source.randrange(258, 8193)
        payload = bytes(random_source.randrange(1, 256) for _ in range(length))
        yield duplicate(random_source, f'long-random-{index}-{length}', payload,
                        random_source.randrange(4))
