"""Cases for level_one_world_timer_01: Level 1 timer-update entry 0x4224f0."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

UPDATE = 0x4224F0
REMOVE_START = 0x4F53EB
STRING_EMPTY = 0x4F650F
STRING_FREE = 0x4F6584
LIMIT = 0x2710
M32 = 0xFFFFFFFF


def timer(mode, acc, t24, t28, f2c, f30, tag=0):
    """A timer object with distinct non-zero filler. Every scripted callee appends (function, receiver,
    first argument, +0x20, +0x2c, +0x30) to a log object so the comparison sees order and state."""
    def setup(env):
        base = 0x5000 + (tag & 0xFF) * 0x11
        obj = env.object(0x40, "timer", fill=0)
        for off in range(0, 0x40, 4):
            env.put(obj + off, 0xA0A00000 + (base << 4) + off)
        env.put(obj + 0x0C, mode & M32)
        env.put(obj + 0x20, acc & M32)
        env.put(obj + 0x24, t24 & M32)
        env.put(obj + 0x28, t28 & M32)
        env.put(obj + 0x2C, f2c & M32)
        env.put(obj + 0x30, f30 & M32)
        log = env.object(0x100, "log", fill=0)

        def record(env, call):
            n = env.get(log)
            env.put(log, n + 1)
            arg = call.arguments[0] if call.arguments else 0
            env.put(log + 4 + 24 * n, call.function, call.receiver, arg,
                    env.get(obj + 0x20), env.get(obj + 0x2C), env.get(obj + 0x30))
            return 0x600D0000 + n

        for fn in (REMOVE_START, STRING_EMPTY, STRING_FREE):
            env.override(fn, record)
        return {"obj": obj, "log": log}
    return setup


def update(label, delta, *args, **kw):
    return Case(label, UPDATE, timer(*args, **kw), receiver=lambda t: t["obj"], arguments=(delta & M32,))


def cases(random_source):
    rnd = random_source

    # Timer at +0x2c/+0x30: threshold 0x2710 is exclusive and compared unsigned.
    for f30 in (0, 0x77777777):
        for f2c, delta in (
            (0, LIMIT - 1), (0, LIMIT), (0, LIMIT + 1), (LIMIT - 1, 1), (LIMIT, 0), (LIMIT, 1),
            (LIMIT + 1, 0), (LIMIT - 5, 5), (LIMIT - 5, 6), (0x1111, 0x1600), (0x1111, 0x15FF),
            (M32, 0), (M32, LIMIT + 1), (M32 - 4, 5), (M32 - 4, 0x2000), (0x80000000, 0x80000000),
            (0x7FFFFFFF, 1), (0x7FFFFFFF, 0x7FFFFFFF), (0x80000000, 0), (0xF0000000, 0x10002711),
            (1, M32), (5, 0x80000000), (0x10, 0x20),
        ):
            for mode in (0, 5):
                yield update(f"timer30={f30:#x} 2c={f2c:#x} d={delta:#x} mode={mode}", delta,
                             mode, 0x100, 0x100000, 0x200000, f2c, f30)

    # Modes 0..4+, accumulation +0x20, thresholds +0x24 (mode<4) and +0x28 (mode>=4) at equal/below/above.
    modes = (0, 1, 2, 3, 4, 5, M32, 0x80000000)
    for mode in modes:
        for acc, delta in ((0, 7), (9, 0), (0x1234, 0x4321), (M32 - 3, 10)):
            total = (acc + delta) & M32
            acc_eff = 0 if mode == 0 else acc
            total_eff = (acc_eff + delta) & M32
            for off24 in (-1, 0, 1):
                for off28 in (-1, 0, 1):
                    yield update(f"mode={mode:#x} acc={acc:#x} d={delta:#x} t24{off24:+d} t28{off28:+d}", delta,
                                 mode, acc, total_eff + off24, total_eff + off28, 0x40, 0, tag=mode + off24 * 3 + off28)
            # Both thresholds on the same side, to expose swapped threshold offsets.
            yield update(f"mode={mode:#x} acc={acc:#x} d={delta:#x} t24 low t28 high", delta,
                         mode, acc, 0, M32, 0x40, 0, tag=1)
            yield update(f"mode={mode:#x} acc={acc:#x} d={delta:#x} t24 high t28 low", delta,
                         mode, acc, M32, 0, 0x40, 0, tag=2)
            del total

    # Both timer and mode paths in one call: the callee order and the intermediate +0x30 state matter.
    for mode in (0, 1, 3, 4, 9):
        for f30 in (0, 0xBEEF):
            yield update(f"timer expires and mode {mode} fires", LIMIT + 5, mode, 0, 3, 4, 0x20, f30, tag=7)
            yield update(f"timer expires, mode {mode} below", LIMIT + 5, mode, 0, M32, M32, 0x20, f30, tag=8)

    # Random cases.
    for i in range(40):
        mode = rnd.choice([0, 1, 2, 3, 4, 5, rnd.randrange(0, 1 << 32), rnd.randrange(-5, 12) & M32])
        delta = rnd.choice([0, 1, rnd.randrange(0, 0x4000), rnd.randrange(0, 1 << 32)])
        acc = rnd.choice([0, rnd.randrange(0, 0x4000), rnd.randrange(0, 1 << 32)])
        acc_eff = 0 if mode == 0 else acc
        total = (acc_eff + delta) & M32
        t24 = rnd.choice([total, total - 1, total + 1, rnd.randrange(0, 1 << 32)])
        t28 = rnd.choice([total, total - 1, total + 1, rnd.randrange(0, 1 << 32)])
        f2c = rnd.choice([0, LIMIT - 1, LIMIT, rnd.randrange(0, 0x4000), rnd.randrange(0, 1 << 32)])
        f30 = rnd.choice([0, 1, rnd.randrange(1, 1 << 32)])
        yield update(f"random {i}", delta, mode, acc, t24, t28, f2c, f30, tag=i)
