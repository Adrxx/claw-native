"""Blind original byte fill: alignment, tails, low-byte and source arg aliases."""
from clawparity.cases import Case
from clawparity.kernel import STACK_TOP
from clawparity.kernel import STACK_BASE, STACK_SIZE
from clawparity.env import NativeSourceContext


def source_setup(random_source, count, value, alignment=0, alias=None, raw=None):
    frame = STACK_TOP - random_source.choice((0, 0x2000, 0x6000))
    pattern = bytes(random_source.randrange(256) for _ in range(1024))
    stack = (pattern * (STACK_SIZE // len(pattern)))
    data = bytes(random_source.randrange(256) for _ in range(count + 40))
    registers = [random_source.getrandbits(32) or 1 for _ in range(7)]
    flags = 2 | random_source.choice((0, 1, 4, 0x10, 0x40, 0x80, 0x800, 0x8d5))
    fs = random_source.choice((0xffffffff, STACK_BASE + 0x100, STACK_BASE + 0x200))

    def setup(env):
        env.write(STACK_BASE, stack)
        if raw is not None:
            destination = raw
        elif alias is not None:
            destination = frame + alias
        else:
            destination = env.object(len(data), 'source-fill-canaries', data=data) + 16 + alignment
        source = NativeSourceContext()
        source.size, source.version = 72, 1
        source.inputMask = source.outputMask = 0x7ff
        source.preserveMask = 0x452
        for name, value_in in zip(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'), registers):
            setattr(source, name, value_in)
        source.esp, source.eip = frame, 0x4a4a20
        source.eflags, source.fsHead = flags, fs
        return {'source': source, 'destination': destination}
    return setup


def source_case(label, random_source, count, value, **options):
    return Case(label, 0x4a4a20,
        source_setup(random_source, count, value, **options),
        arguments=(lambda tokens: tokens['destination'], value, count),
        source_context=lambda tokens: tokens['source'], source_return_pc=0x503225)


def buffer_setup(data, offset):
    def setup(env):
        token = env.object(len(data), 'fill-buffer-and-canaries', data=data)
        return token + offset
    return setup


def cases(random_source):
    lengths = (0,1,2,3,4,5,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129,255,256,257,4095,4096,4097)
    for count in lengths:
        for alignment in range(4):
            for value in (0,255,0xa5,0x80000039):
                data = bytes(random_source.randrange(256) for _ in range(count+40))
                yield Case(f'count{count}-alignment{alignment}-value{value:x}',0x4a4a20,
                    buffer_setup(data,16+alignment), arguments=(lambda token:token,value,count))
    for index in range(64):
        count = random_source.randrange(0,2000)
        offset = random_source.randrange(0,20)
        value = random_source.getrandbits(32)
        data = bytes(random_source.randrange(256) for _ in range(count+40))
        yield Case(f'random{index}',0x4a4a20,buffer_setup(data,offset),arguments=(lambda token:token,value,count))
    for pointer in (0,1,0xdeadbeef,0xffffffff):
        yield Case(f'zero-raw-pointer{pointer:x}',0x4a4a20,arguments=(pointer,0x12345678,0))
    # Source captures fill/count before writes, but reloads destination at F+4
    # after writes. Mutating that word makes stack stores visible through EAX.
    for offset in range(4,8):
        for count in (1,2,3,4,8,12):
            yield Case(f'incoming-destination-word+{offset}-count{count}',0x4a4a20,
                arguments=(STACK_TOP+offset,0x8765435a,count))
    # Independent full CPU and bounded-stack observations use the real caller PC.
    for count in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 17,
                  31, 32, 33, 63, 64, 65, 255, 256, 257, 4095, 4096, 4097):
        for alignment in range(4):
            for value in (0x12345600, 0xfedcba01, 0x7654327f, 0xabcdef80, 0x876543ff):
                yield source_case(f'source-count{count}-align{alignment}-value{value:x}',
                    random_source, count, value, alignment=alignment)
    # Every saved EDI byte can be changed without touching the return word.
    for offset in range(-4, 0):
        for count in range(1, -offset + 1):
            for value in (0x12345600, 0x8765435a, 0x765432ff):
                yield source_case(f'source-saved-edi{offset}-count{count}-value{value:x}',
                    random_source, count, value, alias=offset)
    # Captured operands survive writes, but returned EAX reloads the destination slot.
    for offset in range(4, 16):
        for count in (1, 2, 3, 4, 5, 8, 12, 17, 33):
            yield source_case(f'source-argument+{offset}-count{count}', random_source,
                count, random_source.getrandbits(32), alias=offset)
    for pointer in (0, 1, 0xdeadbeef, 0xffffffff):
        for value in (0, 0xffffffff, 0x12345678):
            yield source_case(f'source-zero-raw{pointer:x}-value{value:x}',
                random_source, 0, value, raw=pointer)
    for index in range(64):
        count = random_source.randrange(1, 2000)
        yield source_case(f'source-random{index}', random_source, count,
            random_source.getrandbits(32), alignment=random_source.randrange(4))
