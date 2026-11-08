"""Blind original constructor cases: CPU frames, opaque inputs and byte guards."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_TOP, STACK_SIZE

ROOTS = (0x440ee0, 0x4dc280, 0x4dc200)
RETURN_PC = {0x440ee0: 0x43d34c, 0x4dc280: 0x440ef2,
             0x4dc200: 0x4dc2c4}
TAGS = (0, 1, 0xffff, 0x10000, 0x10001, 0x7fffffff, 0x80000000,
        0xffffffff, 0x12345678, 0xabcd0000, 0xdeadbeef, 0x80008000)
FACTORIES = (0, 1, 0xffffffff, 0x4c96b0, 0x440ee0, 0x4dc200,
             0x12345678, 0x80000000, 0xffff0000, 0x0000ffff)


def constructor_case(rng, root, index):
    tag = TAGS[index] if index < len(TAGS) else rng.getrandbits(32)
    factory = FACTORIES[index] if index < len(FACTORIES) else rng.getrandbits(32)
    args = ((tag,) if root == 0x440ee0 else
            (factory, tag) if root == 0x4dc280 else (tag, factory))
    size = 0x10 if root == 0x4dc200 else 0x2c
    registers = [rng.getrandbits(32) for _ in range(6)]
    # In particular EDX's high half is distinct from the tag's high half.
    registers[3] = ((tag ^ 0xa55a0000) & 0xffff0000) | rng.getrandbits(16)
    ebp = (0, 0xffffffff, 0x12345679, rng.getrandbits(32))[index % 4]
    frame = (STACK_BASE + 0x40, STACK_TOP - 0x400,
             STACK_TOP - 0x38, STACK_BASE + 0x834)[index % 4]
    flags = 2 | (rng.getrandbits(32) & 0x8d5)
    head = 0xffffffff if index % 3 == 0 else STACK_BASE + 0x1800
    warm = bool(index % 2)
    table = [rng.getrandbits(32) or 1 for _ in range(8)]
    # Distinct bytes around every writable field expose width/offset errors.
    poison = bytes(((i * 43 + index * 17 + 0x61) & 255)
                   for i in range(size + 32))
    random_poison = bytes(rng.getrandbits(8) for _ in range(size + 32))
    if index >= 12:
        poison = random_poison
    stack_pattern = bytes(rng.getrandbits(8) for _ in range(256))

    def setup(env):
        if index in (0, 13) and root != 0x4dc200:
            receiver = 0x537668
            env.write(receiver - 16, poison)
        else:
            allocation = env.object(size + 32, 'receiver and adjacent byte guards', data=poison)
            receiver = allocation + 16
        env.write(STACK_BASE, stack_pattern * (STACK_SIZE // 256))
        if head != 0xffffffff:
            env.put(head, head + 0x30, 0x50a098, 0xffffffff)
            env.put(head + 0x30, 0xffffffff, 0x50a098, 0xffffffff)
        # The real base constructor reads this table and publishes cold strings.
        # Other manager bytes remain backed, distinct, and untouched.
        env.write(0x544b80, bytes((i * 29 + index + 1) & 255 for i in range(64)))
        env.put(0x544b30, *table)
        env.put(0x544b4c, table[-1] if warm else 0)
        context = NativeSourceContext(72, 1, 0x7ff, 0x7ff, *registers,
                                      ebp, frame, root, flags, head, 0x472, 0, 0)
        context.ecx = receiver
        env.put(frame, RETURN_PC[root], *args)
        return {'receiver': receiver, 'source': context}

    return Case(f'{root:x} raw-tag={tag:08x} factory={factory:08x} '
                f'{"warm" if warm else "cold"} cpu={index}', root, setup,
                receiver=lambda t: t['receiver'], arguments=args,
                source_context=lambda t: t['source'], source_return_pc=RETURN_PC[root],
                covers=('whole CPU and bounded stack', 'receiver byte guards',
                        'raw tag truncation', 'inherited FS chain',
                        'cold publication' if not warm else 'warm table preservation'))


def cases(random_source):
    for root in ROOTS:
        for index in range(20):
            yield constructor_case(random_source, root, index)
