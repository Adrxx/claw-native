"""Cases for start_stepping_stone: StartSteppingStone object logic."""
from clawparity.cases import Case

FUNCTION = 0x49EB30
G_TABLE = 0x537960   # pointer to a table whose +0x88..+0x94 are copied into the object
G_PLAYER = 0x537E88  # pointer to the player-like object
G_DELTA = 0x5430C4   # time step passed to the animation update
CB_A, CB_B, CB_C, CB_D = 0x49EAD0, 0x49EAF0, 0x49EB10, 0x49EE20


def build(state=0, callback=0x401000, *, other=True, flags=0x0, timer=0, player_flags=0x10,
          player_target="self", sub14=0, sub1c=0, s64=5, other64=5, other68=20,
          s68=0x7777, mark=0x6666, o16c=5, random_source=None):
    """setup() for one object in a given state. Distinct non-zero words everywhere."""
    def setup(env):
        obj = env.object(0x200, "object", fill=0)
        st = env.object(0xD0, "state", fill=0)
        oth = env.object(0x80, "other", fill=0)
        table = env.object(0xA0, "table", fill=0)
        player = env.object(0x90, "player", fill=0)
        q = env.object(0x20, "q", fill=0)
        r = env.object(0x90, "r", fill=0)
        for i in range(0, 0x200, 4):
            env.put(obj + i, 0x11000000 + i)
        for i in range(0, 0xD0, 4):
            env.put(st + i, 0x22000000 + i)
        for i in range(0, 0xA0, 4):
            env.put(table + i, 0x33000000 + i)
        for i in range(0, 0x80, 4):
            env.put(oth + i, 0x44000000 + i)
        env.put(obj + 0x6C, st)
        x = env.object(0x40, "owner", fill=0)
        m = env.object(0x40, "lookup", fill=0)
        buckets = env.object(0x40, "buckets", fill=0)
        env.put(m + 0x10 + 0x04, buckets)
        env.put(m + 0x10 + 0x08, 7)
        env.put(x + 0x2C, m)
        env.put(obj + 0x0C, x)
        env.put(obj + 0x4, 0)
        env.put(obj + 0x188 + 0x08, 0)
        arr = env.object(0x400, "frames", fill=0)
        for i in range(0, 0x400, 4):
            env.put(arr + i, 0x55000000 + i)
        env.put(oth + 0x14, arr + 0x200)
        env.put(obj + 0x08, flags)
        env.put(obj + 0x64, timer)
        env.put(obj + 0x16C, o16c)
        env.put(obj + 0x170, oth if other else 0)
        env.put(obj + 0x188 + 0x14, sub14)
        env.put(obj + 0x188 + 0x1C, sub1c)
        env.put(obj + 0xE8, 0x5A5A0001)
        env.put(obj + 0xEC, 0x5A5A0002)
        env.put(st + 0x1C, state)
        env.put(st + 0x10, callback)
        env.put(st + 0x64, s64)
        env.put(st + 0x68, s68)
        env.put(oth + 0x64, other64)
        env.put(oth + 0x68, other68)
        env.put(table + 0x88, 0xA1, 0xA2, 0xA3, 0xA4)
        env.put(player + 0x08, player_flags)
        env.put(player + 0x6C, q)
        env.put(player + 0x80, obj if player_target == "self" else 0x99)
        env.put(q + 0x14, r)
        env.put(r + 0x80, mark)
        env.put(G_TABLE, table)
        env.put(G_PLAYER, player)
        env.put(G_DELTA, 0x10)
        return {"obj": obj, "st": st}
    return setup


def case(label, setup):
    return Case(label, FUNCTION, setup, arguments=(lambda t: t["obj"],))


def cases(random_source):
    for st in (0x3EA, 0x3EC, 0x3EE, 0x3EB, 0x3ED, 0x3EF, 0, 5, 0x3F0, 0x3E9, 0xFFFFFFFF, 0x80000000):
        yield case(f"state {st:#x}", build(st))

    # state 0: initialisation
    for cb in (CB_A, CB_B, CB_C, CB_D, 0x401234):
        for timer in (0, 77):
            for other in (True, False):
                yield case(f"init cb {cb:#x} timer {timer} other {other}",
                           build(0, cb, other=other, timer=timer, flags=0x8000 | (timer << 8)))
    for lo, hi, idx in ((5, 20, 5), (5, 20, 20), (5, 20, 4), (5, 20, 21), (-3, 40, 0), (0, 3, 3)):
        yield case(f"init frame index {idx} in [{lo},{hi}]", build(0, other64=lo, other68=hi, o16c=idx))
    for lo, hi in ((10, 21), (-9, -2), (-10, 3), (-7, 4), (3, 4), (0, 0), (-1, 0), (100, 201), (-100, -201)):
        yield case(f"init average of {lo} and {hi}", build(0, other64=lo, other68=hi, s64=0x4321))
    for flags in (0, 1, 0x20000, 0x3, 0x5A5A5A5A, 0xFFFFFFFF):
        yield case(f"init flags {flags:#x}", build(0, flags=flags, timer=0))
        yield case(f"init flags {flags:#x} with timer", build(0, flags=flags, timer=9))

    # state 0x3eb and 0x3ed: waiting for the animation
    for st in (0x3EB, 0x3ED):
        for same in (True, False):
            for sub14 in (0, 3):
                for sub1c in (0, 8):
                    for cb in (0x401000, CB_D):
                        yield case(f"state {st:#x} same {same} sub14 {sub14} sub1c {sub1c} cb {cb:#x}",
                                   build(st, cb, o16c=5 if same else 6, s64=5, sub14=sub14, sub1c=sub1c))
    for mark in (0x6666, 0x7777):
        for target in ("self", "other"):
            yield case(f"3ed on callback D, mark {mark:#x}, player {target}",
                       build(0x3ED, CB_D, s68=0x7777, mark=mark, sub1c=1, sub14=0, player_target=target))
    yield case("3ed on callback D, mark changed, other missing", build(0x3ED, CB_D, other=False, sub1c=1))

    # state 0x3ef: wait for the player
    for pf in (0, 0x10, 0x1, 0xFFFFFFEF, 0xFFFFFFFF, 0x30):
        for target in ("self", "other"):
            yield case(f"3ef player flags {pf:#x} target {target}", build(0x3EF, player_flags=pf, player_target=target))

    # random mixtures
    states = (0, 0x3EA, 0x3EB, 0x3EC, 0x3ED, 0x3EE, 0x3EF, 0x3F0, 0x100)
    callbacks = (CB_A, CB_B, CB_C, CB_D, 0x401000)
    for n in range(80):
        r = random_source
        st = r.choice(states)
        lo = r.randrange(-50, 50)
        yield case(f"random {n} state {st:#x}", build(
            st, r.choice(callbacks), other=r.random() < 0.8, flags=r.getrandbits(32), timer=r.choice((0, r.getrandbits(16))),
            player_flags=r.getrandbits(8), player_target=r.choice(("self", "other")),
            sub14=r.choice((0, r.randrange(1, 9))), sub1c=r.choice((0, r.randrange(1, 9))),
            s64=r.choice((5, r.randrange(0, 30))), other64=lo, other68=lo + r.randrange(0, 60),
            s68=r.choice((0x7777, 0x6666)), mark=r.choice((0x7777, 0x6666)), o16c=r.randrange(lo - 2, lo + 30)))
