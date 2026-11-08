"""Inputs for the original Low Detail dormant scenery callback at 0x46eff0."""
from clawparity.cases import Case

FILTER = 0x46EFF0
CANDY = (0x461970, 0x4618E0, 0x461770, 0x4617D0)


def scene(kind, flags, dormant, words, *, missing_logic=False):
    def setup(env):
        actor = env.object(0x80, "actor", words=words[:32])
        logic = env.object(0x20, "logic", words=words[32:40])
        env.put(actor + 0x08, flags)
        env.put(actor + 0x40, dormant)
        env.put(actor + 0x6C, 0 if missing_logic else logic)
        env.put(logic + 0x10, kind)
        return actor
    return setup


def cases(random_source):
    yield Case("null actor", FILTER, arguments=(0,))
    words = [random_source.getrandbits(32) for _ in range(40)]
    yield Case("null primary logic", FILTER,
               scene(0x461970, 0xA5A51234, 0xD3D35678, words, missing_logic=True),
               arguments=(lambda actor: actor,))
    flags_pairs = ((0, 0), (1, 0x80000000), (0xFFFF, 0xFFFFFFFE),
                   (0x10000, 1), (0xFFFFFFFF, 0xFFFFFFFF),
                   (0xA5A40002, 0xB6C7D8E0), (0x80000000, 0x123456FE),
                   (0xF00D8000, 0xFEDCBA98))
    for kind in CANDY:
        for flags, dormant in flags_pairs:
            words = [random_source.getrandbits(32) for _ in range(40)]
            yield Case(f"kind {kind:x} flags {flags:x} dormant {dormant:x}", FILTER,
                       scene(kind, flags, dormant, words), arguments=(lambda actor: actor,))
        for index in range(6):
            words = [random_source.getrandbits(32) for _ in range(40)]
            flags, dormant = random_source.getrandbits(32), random_source.getrandbits(32)
            yield Case(f"kind {kind:x} random {index}", FILTER,
                       scene(kind, flags, dormant, words), arguments=(lambda actor: actor,))
    # Every comparison has deterministic near misses on both sides; coverage
    # and selectivity do not depend on the gate's unknown random seed.
    for kind in (0, 1, 0xFFFFFFFF, 0x461730, 0x461750, 0x461830, 0x461870,
                 *(value + delta for value in CANDY for delta in (-1, 1, 0x1000000))):
        words = [random_source.getrandbits(32) for _ in range(40)]
        yield Case(f"unrelated kind {kind:x}", FILTER,
                   scene(kind, 0xABC40042, 0xFACEFE00, words), arguments=(lambda actor: actor,))
