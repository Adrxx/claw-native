"""Cases for object_variants: numbered variants that store a variant number in a global and tail into the base logic."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

# (entry, global written, value written)
VARIANTS = [
    (0x461FE0, 0x537B8C, 2),
    (0x462000, 0x537B8C, 3),
    (0x462020, 0x537B8C, 4),
    (0x4622F0, 0x537B90, 2),
    (0x462310, 0x537B90, 3),
    (0x49EAD0, 0x53EBF0, 2),
    (0x49EAF0, 0x53EBF0, 3),
    (0x49EB10, 0x53EBF0, 4),
]
GLOBALS = (0x537B8C, 0x537B90, 0x53EBF0)
# States the base logic ignores (no branch matches), so the base function returns at once.
IDLE_STATES = (0x3F0, 0x3F1, 0x3FF, 0x1, 0x7FFFFFFF, 0x3E9, 0xFFFFFFFF)


def build(state, previous, words):
    def setup(env):
        record = env.object(0x100, "record", words=words)
        env.put(record + 0x1C, state)
        obj = env.object(0x200, "object", words=[(w * 7 + 3) & 0xFFFFFFFF for w in range(0x80)])
        env.put(obj + 0x6C, record)
        for g, p in zip(GLOBALS, previous):
            env.put(g, p)
        return {"object": obj}

    return setup


def cases(random_source):
    yield from more_cases(random_source)
    for entry, glob, value in VARIANTS:
        for state in IDLE_STATES:
            previous = (0x11111111, 0x22222222, 0x33333333)
            words = [0xA0000000 + i for i in range(0x40)]
            yield Case(f"{entry:#x} state {state:#x}", entry, build(state, previous, words),
                       arguments=(lambda t: t["object"],))
        for _ in range(6):
            state = random_source.choice(IDLE_STATES)
            previous = tuple(random_source.getrandbits(32) for _ in range(3))
            words = [random_source.getrandbits(32) for _ in range(0x40)]
            yield Case(f"{entry:#x} random", entry, build(state, previous, words),
                       arguments=(lambda t: t["object"],))
    # SteppingStone state 0x3ea with no sound id: the base logic only advances the state.
    for entry in (0x49EAD0, 0x49EAF0, 0x49EB10):
        def sink(env):
            tokens = build(0x3EA, (1, 2, 3), [0xB0000000 + i for i in range(0x40)])(env)
            env.put(tokens["object"] + 0x38, 0xFFFFFFFF)
            return tokens

        yield Case(f"{entry:#x} stone sink state", entry, sink, arguments=(lambda t: t["object"],))


# The base logic is the only code that could observe the variant global, and nothing in the program reads it.
# It can still change it: if the object itself sits in global data so that a field the base writes in state 0
# (offset 0xD0) is the variant global, the base's write and the variant's store race, and only the right order
# leaves the base's value behind.
FIELD_AT_GLOBAL = 0xD0
STONE_ENTRIES = (0x49EAD0, 0x49EAF0, 0x49EB10)


def overlay(entry, glob, previous, random_source):
    object_address = glob - FIELD_AT_GLOBAL
    words = [random_source.getrandbits(32) for _ in range(0x70)]
    record_pointer = [random_source.choice((0x461FE0, 0x462000, 0x462020, 0x4622F0, 0x462310, 0x49EAD0, 0x49EAF0,
                                            0x49EB10, 0x12345678))]

    def setup(env):
        record = env.object(0x100, "record", words=[random_source.getrandbits(32) for _ in range(0x40)])
        env.put(record + 0x1C, 0)
        env.put(record + 0x10, record_pointer[0])
        env.write(object_address, b"".join(w.to_bytes(4, "little") for w in words))
        env.put(object_address + 0x6C, record)
        env.put(object_address + 0x170, 0)
        env.put(object_address + 0x174, 0)
        env.put(object_address + 0x64, random_source.choice((0, 0, 77)))
        env.put(object_address + 0x104, random_source.choice((0, 5)))
        stats = env.object(0x100, "stats", words=[random_source.getrandbits(32) for _ in range(0x40)])
        env.put(0x537960, stats)
        env.put(glob, previous)
        return {"object": object_address}

    return setup


def more_cases(random_source):
    for entry, glob, value in VARIANTS:
        for _ in range(4):
            previous = random_source.choice((0x11111111, 0x22222222, 0x7FFFFFFF, 5, 1))
            yield Case(f"{entry:#x} object overlays its own variant global", entry,
                       overlay(entry, glob, previous, random_source), arguments=(lambda t: t["object"],))
