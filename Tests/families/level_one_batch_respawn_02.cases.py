"""Cases for level_one_batch_respawn_02: Level 1 respawn cleanup callback 0x46e340."""
from clawparity.cases import Case

CALLBACK = 0x46E340
SIZE = 0x180
FLAGS_OFFSET = 0x164
STATE_OFFSET = 0x08
DEFERRED = 0x2000
REMOVAL = 0x10000


def actor(flags, state, random_source):
    """setup() for an object of random non-zero bytes with the given words at +0x164 and +0x08."""
    data = bytearray(random_source.randrange(1, 256) for _ in range(SIZE))
    data[FLAGS_OFFSET:FLAGS_OFFSET + 4] = (flags & 0xFFFFFFFF).to_bytes(4, "little")
    data[STATE_OFFSET:STATE_OFFSET + 4] = (state & 0xFFFFFFFF).to_bytes(4, "little")
    data = bytes(data)

    def setup(env):
        return {"actor": env.object(SIZE, "actor", data=data)}

    return setup


def call(label, setup):
    return Case(label, CALLBACK, setup, arguments=(lambda tokens: tokens["actor"],))


def cases(random_source):
    yield Case("null argument", CALLBACK, None, arguments=(0,))
    state_values = (0, 0x10000, 0x1, 0xFFFEFFFF, 0xFFFFFFFF, 0x12345678)
    flag_values = (0, DEFERRED, 0xFFFFFFFF, 0xFFFFDFFF, 0x1FFF, 0x2000 | 0x1, 0x4000, 0x8000, 0x1000, 0x20)
    for flags in flag_values:
        for state in state_values:
            yield call(f"flags {flags:#x} state {state:#x}", actor(flags, state, random_source))
    for bit in range(32):
        mask = 1 << bit
        yield call(f"only bit {bit} set", actor(mask, random_source.getrandbits(32), random_source))
        yield call(f"all but bit {bit} set", actor(~mask, random_source.getrandbits(32), random_source))
    for _ in range(60):
        flags = random_source.getrandbits(32)
        state = random_source.getrandbits(32)
        yield call(f"random flags {flags:#x} state {state:#x}", actor(flags, state, random_source))
    for _ in range(30):
        flags = random_source.getrandbits(32) | DEFERRED
        yield call(f"random set {flags:#x}", actor(flags, random_source.getrandbits(32), random_source))
        flags = random_source.getrandbits(32) & ~DEFERRED
        yield call(f"random clear {flags:#x}", actor(flags, random_source.getrandbits(32), random_source))
