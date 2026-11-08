"""Cases for level_one_batch_pegs_and_elevators_01: Level 1 CrumblingPeg, TogglePegs and Start/Trigger elevators.

Every branch is reached by an explicit case; random_source only varies the filler words and a few extra
randomised cases.  Objects are sized tightly so that a wrong offset or pointer faults the native side.
"""
from clawparity.cases import Case

E470, E4B0, E4E0, E7B0, E7D0, E7F0 = 0x49E470, 0x49E4B0, 0x49E4E0, 0x49E7B0, 0x49E7D0, 0x49E7F0
C610, CDD0, D860, DAF0, DB10, DB30, DB50, DB70, EE20 = (
    0x4CA610, 0x49CDD0, 0x49D860, 0x49DAF0, 0x49DB10, 0x49DB30, 0x49DB50, 0x49DB70, 0x49EE20)
E810, EB30 = 0x49E810, 0x49EB30  # compared against, never owned here

G_R, G_W, G_TS, G_CLK, G_DT, G_T = 0x537960, 0x537E88, 0x53725C, 0x537210, 0x5430C4, 0x5371FC
G_P10, G_M, G_GV = 0x532C10, 0x532C0C, 0x53EBF0
NAME = {"slide": 0x528A3C, "fwd": 0x52DD04, "bwd": 0x52DD14, "crumble": 0x52DD24, "trap": 0x528A4C}
M32 = 0xFFFFFFFF


def bucket(key, nb):
    h = 0
    for c in key:
        h = (h * 0x21 + (c - 256 if c > 127 else c)) & M32
    return h % nb


def table(env, base, nb, entries, decoys):
    """A hash table whose header sits at `base` (+4 buckets, +8 bucket count)."""
    heads = [0] * nb
    for key, value in list(entries) + [(d, 0xD0D00000 + i) for i, d in enumerate(decoys)]:
        slot = bucket(key, nb)
        if key in decoys:
            slot = bucket(entries[0][0], nb) if entries else slot
        text = env.object(len(key) + 1, "key", data=key + b"\0")
        heads[slot] = env.object(16, "node", words=[heads[slot], 0x1234, text, value])
    buckets = env.object(4 * nb, "buckets", words=heads)
    env.put(base + 4, buckets, nb)


def anim(env, frame_value, count):
    frames = [env.object(0x20, "frame", words=[frame_value + i] * 8) for i in range(count)]
    array = env.object(4 * count, "frames", words=frames)
    return env.object(0x14, "anim", words=[0, 0, 0, array, count])


def pointer_free_words(rs, size):
    return [rs.randrange(1, 1 << 32) for _ in range(size // 4)]


A_DEF = {0x08: 0x10000, 0x40: 4, 0x4C: 100, 0x50: 200, 0x64: 77, 0x108: 0, 0x110: 4, 0x148: 25, 0x14C: 30,
         0x164: 0, 0x16C: 5, 0x19C: 3, 0x1A4: 9, 0x1A0: 0}
S_DEF = {0x10: E810, 0x1C: 0, 0x2C: 10, 0x30: 20, 0x34: 30, 0x38: 40, 0x4C: 1000, 0x64: 9, 0x68: 4, 0xBC: 50}
GLOBAL_DEF = {"ts": 0, "clk": 1234, "dt": 53, "p10": 100, "m": 0, "wflags": 0x10, "wactor": "self", "hv": 321,
              "tv": 10, "gv": 0xA5A5A5A5}


def build(rs, a=None, s=None, **o):
    a = {**A_DEF, **(a or {})}
    s = {**S_DEF, **(s or {})}
    o = {**GLOBAL_DEF, "anim": "none", "tick": 1, "g": None, "frame": False, "n_found": ("fwd", "bwd"),
         "p_found": ("slide", "crumble"), "trap_found": True, "trap_eq": None, "nb": 3, "p30": 0, "b5c": 1,
         "pb": True, "pa": True, "decoy": True, **o}
    aw = pointer_free_words(rs, 0x1B4)
    sw = pointer_free_words(rs, 0xC0)
    rw = pointer_free_words(rs, 0xA8)
    gen = [rs.randrange(1, 1 << 32) for _ in range(8)]

    def setup(env):
        t = {}
        names = {k: env.cstr(v) for k, v in NAME.items()}
        t["names"] = {k: env.object(len(v) + 1, "name", data=v + b"\0") for k, v in names.items()}
        decoys = [b"LEVEL_PEGSLIDF", b"GAME_FORWARD5", b"zz"] if o["decoy"] else []
        A = t["A"] = env.object(0x1B4, "actor", words=aw)
        S = t["S"] = env.object(0xC0, "state", words=sw)
        env.put(A + 0x6C, S)
        for off, val in a.items():
            env.put(A + off, val)
        for off, val in s.items():
            env.put(S + off, val)
        # manager and name tables
        M = env.object(0x30, "manager")
        env.put(A + 0xC, M)
        Q = env.object(0x1C, "trap-table")
        N = env.object(0x1C, "anim-table")
        P = env.object(0x34, "peg-sprites")
        env.put(M + 0x10, Q, 0, 0)
        env.put(M + 0x28, P, N)
        trap_value = env.object(8, "trap-elevator", words=[gen[0], gen[1]])
        table(env, Q + 0x10, o["nb"], [(names["trap"], trap_value)] if o["trap_found"] else [], decoys)
        if o["trap_eq"] == "found":
            env.put(A + 0x170, trap_value)
        elif o["trap_eq"] == "zero":
            env.put(A + 0x170, 0)
        entries = []
        for key in o["n_found"]:
            entries.append((names[key], anim(env, gen[2] if key == "fwd" else gen[3], 1 + (key == "bwd") * 2)))
        table(env, N + 0x10, o["nb"], entries, decoys)
        t["N"] = N
        pa = env.object(0x28, "sprite-a", words=pointer_free_words(rs, 0x28))
        pb = env.object(0x60, "sprite-b", words=pointer_free_words(rs, 0x60))
        env.put(pa + 0x24, pb if o["pb"] else 0)
        env.put(pb + 0x5C, o["b5c"])
        env.put(P + 0xC, pa)
        env.put(P + 0x30, o["p30"])
        entries = [(names[k], env.object(0x10, "peg", words=[gen[4], gen[5]])) for k in o["p_found"]]
        table(env, P + 0x10, o["nb"], entries, decoys)
        t["P"] = P
        # G: the animation-strip source behind A+0x170
        if o["g"] is not None:
            lo, hi = o["g"]
            count = max(1, hi - lo + 1)
            arr = env.object(4 * count, "strip", words=[0xAAAA0000 + i * 0x11 for i in range(count)])
            G = env.object(0x6C, "strip-owner", words=pointer_free_words(rs, 0x6C))
            env.put(G + 0x14, arr - 4 * lo)
            env.put(G + 0x64, lo, hi)
            env.put(G + 0x68, hi)
            env.put(A + 0x170, G)
        elif o["trap_eq"] is None:
            env.put(A + 0x170, 0)
        if o["frame"]:
            fr = env.object(0x28, "frame", words=[gen[6] + i for i in range(10)])
            env.put(fr + 0x18, 7, 3, 40, 30)
            env.put(A + 0x174, fr)
        else:
            env.put(A + 0x174, 0)
        # animation cursor at A+0x188
        if o["anim"] == "tick":
            env.put(A + 0x190, 0x7777, 0, 0)
            env.put(A + 0x19C, o["tick"])
            env.put(A + 0x1A0, 0)
        elif o["anim"] == "idle":
            env.put(A + 0x190, 0x7777)
            env.put(A + 0x19C, 0)
            env.put(A + 0x1A4, a.get(0x1A4, 9) or 9)
        else:
            env.put(A + 0x190, 0)
        # globals
        R = env.object(0xA8, "pegs-config", words=rw)
        W = env.object(0x84, "world", words=pointer_free_words(rs, 0x84))
        X = env.object(0x18, "world-x", words=pointer_free_words(rs, 0x18))
        Y = env.object(0x84, "world-y", words=pointer_free_words(rs, 0x84))
        env.put(X + 0x14, Y)
        env.put(Y + 0x80, o["hv"])
        env.put(W + 0x6C, X)
        env.put(W + 8, o["wflags"])
        env.put(W + 0x80, {"self": A, "other": W, 0: 0}[o["wactor"]])
        T = env.object(0x30, "level", words=pointer_free_words(rs, 0x30))
        U = env.object(0x18, "level-u", words=pointer_free_words(rs, 0x18))
        env.put(T + 0x2C, U)
        env.put(U + 0x14, o["tv"])
        env.put(G_R, R)
        env.put(G_W, W)
        env.put(G_T, T)
        env.put(G_TS, o["ts"])
        env.put(G_CLK, o["clk"])
        env.put(G_DT, o["dt"])
        env.put(G_P10, o["p10"])
        env.put(G_M, o["m"])
        env.put(G_GV, o["gv"])
        return t

    return setup


def arg_a(t):
    return t["A"]


def case(label, fn, rs, **kw):
    return Case(label, fn, build(rs, **kw), arguments=(arg_a,))


# ---------------------------------------------------------------------------------------------
def cases(random_source):
    rs = random_source
    yield from small_cases(rs)
    yield from direct_4ca610(rs)
    yield from slide_cases(rs)
    yield from crumble_cases(rs)
    yield from elevator_cases(rs)
    yield from thunk_cases(rs)


def small_cases(rs):
    # 0x49e470: both defaults, each default alone, neither
    def e470(a148, a14c):
        def setup(env):
            p1 = env.object(0x150, "p1", words=[rs.randrange(1, 1 << 32) for _ in range(0x54)])
            p2 = env.object(0x50, "p2", words=[rs.randrange(1, 1 << 32) for _ in range(0x14)])
            env.put(p1 + 0x148, a148)
            env.put(p1 + 0x14C, a14c)
            return {"p1": p1, "p2": p2}
        return setup
    for a148, a14c in ((0, 0), (0, 77), (91, 0), (91, 77), (0, 0x7FFFFFFF), (0x80000000, 5), (-3, -9), (1, 0xFFFFFFFF),
                       (0x5DC, 0), (0, 0x5DC), (123456, 654321)):
        yield Case(f"49e470 {a148:#x} {a14c:#x}", E470, e470(a148, a14c), arguments=(lambda t: t["p1"], lambda t: t["p2"]))
    for _ in range(4):
        yield Case("49e470 random", E470, e470(rs.choice((0, rs.randrange(1, 1 << 32))), rs.choice((0, rs.randrange(1, 1 << 32)))),
                   arguments=(lambda t: t["p1"], lambda t: t["p2"]))

    # 0x49e4b0: (p3 - base) % period <= limit
    def e4b0(limit, period, base):
        def setup(env):
            p1 = env.object(0x14C, "p1", words=[rs.randrange(1, 1 << 32) for _ in range(0x53)])
            p2 = env.object(0xC0, "p2", words=[rs.randrange(1, 1 << 32) for _ in range(0x30)])
            env.put(p1 + 0x148, limit)
            env.put(p2 + 0x4C, period)
            env.put(p2 + 0xBC, base)
            return {"p1": p1, "p2": p2}
        return setup
    grid = [(10, 100, 0, 5), (10, 100, 0, 10), (10, 100, 0, 11), (10, 100, 0, 105), (10, 100, 0, 111), (10, 100, 40, 30),
            (10, 100, 40, 145), (0, 100, 0, 0), (0, 100, 0, 1), (-1, 100, 0, 0), (-1, 100, 5, 3), (-100, 7, 3, 9),
            (5, 1, 1000, 2), (5, 0x80000010, 3, 0x70000000), (5, 0x80000010, 0, 0x80000005), (0x7FFFFFFF, 0xF0000000, 0, 0x90000000),
            (3, 0x90000000, 0, 0x8FFFFFFF), (3, 0xFFFFFFFF, 0, 0xFFFFFFFE), (50, 10, 0, 49), (50, 10, 0, 59), (9, 10, 5, 4),
            (9, 10, 0xFFFFFFF0, 3), (0x2EE, 0x5DC, 0x2EE, 0x2EE * 3), (0x2EE, 0x5DC, 0x2EE, 0x2EE * 3 + 1), (7, 3, 0, 0xFFFFFFFF)]
    for limit, period, base, p3 in grid:
        yield Case(f"49e4b0 limit {limit:#x} period {period:#x} base {base:#x} p3 {p3:#x}", E4B0, e4b0(limit, period, base),
                   arguments=(lambda t: t["p1"], lambda t: t["p2"], p3 & M32))
    for _ in range(6):
        yield Case("49e4b0 random", E4B0, e4b0(rs.randrange(-20, 80), rs.randrange(1, 300), rs.randrange(0, 1 << 32)),
                   arguments=(lambda t: t["p1"], lambda t: t["p2"], rs.randrange(0, 1 << 32)))


def direct_4ca610(rs):
    for label, kw, name, p2 in (("found", {}, "slide", 0x1234), ("found other", {}, "crumble", 0x77), ("not found", {"p_found": ()}, "slide", 5),
                                ("one bucket", {"nb": 1}, "crumble", 6), ("seven buckets", {"nb": 7}, "slide", 0xFFFFFFFF),
                                ("busy", {"p30": 9}, "slide", 8), ("no pointer", {"pb": False}, "slide", 8),
                                ("b5c zero", {"b5c": 0}, "slide", 8), ("no decoys", {"decoy": False}, "crumble", 9),
                                ("name missing in table", {"p_found": ("slide",)}, "crumble", 10),
                                ("unrelated name", {}, "trap", 11)):
        yield Case(f"4ca610 {label}", C610, build(rs, **kw), receiver=lambda t: t["P"],
                   arguments=(lambda t, name=name: t["names"][name], p2, 0x2222, 0x3333))
    for i in range(3):
        yield Case(f"4ca610 random {i}", C610, build(rs, nb=rs.choice((1, 2, 11)), p_found=rs.choice((("slide",), ("crumble",), ()))),
                   receiver=lambda t: t["P"], arguments=(lambda t: t["names"][rs.choice(("slide", "crumble"))], rs.randrange(1 << 32), rs.randrange(1 << 32), rs.randrange(1 << 32)))


def peg_world(rs, fn, state, label, **kw):
    return case(label, fn, rs, s={0x1C: state, **kw.pop("s", {})}, **kw)


def p_cases(rs, fn, state, tag, extra_a=None):
    """The 4ca610 variants as seen through the state that calls it."""
    base = dict(a=extra_a)
    yield peg_world(rs, fn, state, f"{tag} sprite found", **base)
    yield peg_world(rs, fn, state, f"{tag} sprite found one bucket", nb=1, **base)
    yield peg_world(rs, fn, state, f"{tag} sprite found bucket 7", nb=7, **base)
    yield peg_world(rs, fn, state, f"{tag} sprite not found", p_found=(), **base)
    yield peg_world(rs, fn, state, f"{tag} sprite only the other name", p_found=("crumble",) if "slide" in tag else ("slide",), **base)
    yield peg_world(rs, fn, state, f"{tag} no decoys", decoy=False, **base)
    yield peg_world(rs, fn, state, f"{tag} sprite busy", p30=5, **base)
    yield peg_world(rs, fn, state, f"{tag} sprite pointer missing", pb=False, **base)
    yield peg_world(rs, fn, state, f"{tag} sprite b5c zero", b5c=0, **base)


def slide_cases(rs):
    """0x49e4e0, TogglePeg: every state."""
    fn = E4E0
    # state 0
    for ptr in (E7B0, E7D0, E7F0, E810, 0, EB30):
        yield peg_world(rs, fn, 0, f"e4e0 init, state fn {ptr:#x}", s={0x10: ptr}, g=(2, 4))
    for g in (None, (2, 4), (3, 3), (5, 4), (-4, 1), (-5, -2), (0, 0), (1, 2)):
        for a64 in (0, 555):
            yield peg_world(rs, fn, 0, f"e4e0 init strip {g} 64={a64}", a={0x64: a64}, g=g)
    for ts, a108 in ((0, 0), (1, 0), (0, 1), (9, 1), (0, 2), (0, 0xFFFFFFFF)):
        yield peg_world(rs, fn, 0, f"e4e0 init ts={ts} a108={a108}", a={0x108: a108}, ts=ts, g=(1, 3))
    for a148, a14c in ((0, 0), (0, 12), (13, 0), (13, 12)):
        for ptr in (E7B0, E810):
            yield peg_world(rs, fn, 0, f"e4e0 init weights {a148} {a14c} {ptr:#x}", a={0x148: a148, 0x14C: a14c},
                            s={0x10: ptr}, g=(2, 3))
    yield peg_world(rs, fn, 0, "e4e0 init flags", a={0x08: 0x80000000}, g=(1, 1))
    yield peg_world(rs, fn, 0, "e4e0 init flags and 64", a={0x08: 0x40, 0x64: 0}, g=(1, 1))
    # state 0x3ea and 0x3ec: sprite calls
    yield from p_cases(rs, fn, 0x3EA, "e4e0 3ea slide", {0x4C: 0x1234})
    for found in (("fwd", "bwd"), ("fwd",), ("bwd",), ()):
        yield peg_world(rs, fn, 0x3EC, f"e4e0 3ec anim {found}", n_found=found)
        yield peg_world(rs, fn, 0x3EC, f"e4e0 3ec anim {found} one bucket", n_found=found, nb=1)
    yield from p_cases(rs, fn, 0x3EC, "e4e0 3ec slide", {0x4C: 0x4321})
    # states 0x3eb and 0x3ed share a shape
    for state in (0x3EB, 0x3ED):
        for anim_mode in ("none", "tick", "idle"):
            for eq in (True, False):
                for a1a4, a19c in ((9, 0), (9, 4), (0, 0), (0, 4)):
                    if anim_mode != "none" and (a1a4, a19c) not in ((9, 0), (0, 0)):
                        continue
                    if anim_mode == "idle" and a1a4 == 0:
                        continue
                    a = {0x16C: 9 if eq else 8, 0x1A4: a1a4, 0x19C: a19c}
                    for tick in ((1, 2) if anim_mode == "tick" else (1,)):
                        yield peg_world(rs, fn, state, f"e4e0 {state:#x} {anim_mode} eq={eq} 1a4={a1a4} 19c={a19c} tick={tick}",
                                        a=a, s={0x64: 9}, anim=anim_mode, tick=tick)
        for found in (("fwd", "bwd"), ("fwd",), ("bwd",), ()):
            yield peg_world(rs, fn, state, f"e4e0 {state:#x} fire anim {found}", a={0x1A4: 5, 0x19C: 0},
                            n_found=found, s={0x64: 3})
    # states 0x3ee and 0x3ef: clock gate
    for state in (0x3EE, 0x3EF):
        for clk, base, period, limit in ((1234, 0, 1000, 300), (1234, 0, 1000, 234), (1234, 0, 1000, 233), (1234, 34, 1000, 200),
                                         (50, 100, 1000, 1000), (50, 100, 7, -1), (999, 0, 1000, 0x7FFFFFFF), (5, 5, 3, 0)):
            yield peg_world(rs, fn, state, f"e4e0 {state:#x} clock {clk} {base} {period} {limit}", a={0x148: limit},
                            s={0x4C: period, 0xBC: base}, clk=clk)
    for state in (1, 5, 0x3E9, 0x3F0, 0x1000, 0xFFFFFFFF, 0x457, 0x17):
        yield peg_world(rs, fn, state, f"e4e0 other state {state:#x}")


def crumble_cases(rs):
    """0x49d860, the CrumblingPeg update."""
    fn = D860
    # state 5: the player is standing on it
    for ts in (0, 3):
        for wf in (0x10, 0x00, 0x1F):
            for who in ("self", "other", 0):
                yield peg_world(rs, fn, 5, f"d860 stand ts={ts} wf={wf:#x} {who}", ts=ts, wflags=wf, wactor=who,
                                a={0x148: 0x61 + ts + wf})
    # state 0 init
    for g in (None, (2, 4), (4, 4), (5, 2), (-3, 3), (-6, -1)):
        for a64 in (0, 4000):
            yield peg_world(rs, fn, 0, f"d860 init strip {g} a64={a64}", g=g, a={0x64: a64})
    for a148, a110 in ((0, 0), (0, 9), (8, 0), (8, 9)):
        yield peg_world(rs, fn, 0, f"d860 init a148={a148} a110={a110}", a={0x148: a148, 0x110: a110}, g=(1, 4))
    for found in (("fwd", "bwd"), ("fwd",), ("bwd",), ()):
        yield peg_world(rs, fn, 0, f"d860 init anim {found}", n_found=found, g=(2, 3))
        yield peg_world(rs, fn, 0, f"d860 init anim {found} one bucket", n_found=found, nb=1, g=(2, 3), a={0x40: 0xFFFFFFFF})
    yield peg_world(rs, fn, 0, "d860 init flags", a={0x08: 0x8000, 0x40: 0xF0F0F0F1, 0x164: 0x1234}, g=(2, 2))
    # state 0x17: wait for the player to pass
    for s64, hv in ((5, 321), (321, 321), (322, 321), (-5, 321), (5, -321), (-321, -321), (-400, -321), (0x7FFFFFFF, -1),
                    (0x80000000, 5)):
        yield peg_world(rs, fn, 0x17, f"d860 wait {s64:#x} vs {hv:#x}", s={0x64: s64}, hv=hv)
    # state 0x3ea: crumble sound
    yield from p_cases(rs, fn, 0x3EA, "d860 3ea crumble", None)
    yield peg_world(rs, fn, 0x3EA, "d860 3ea crumble other dt", dt=999, p10=77)
    # state 0x3ed
    for anim_mode in ("none", "tick", "idle"):
        for eq in (True, False):
            for a1a4, a19c in ((9, 0), (9, 4), (0, 0), (0, 4)):
                if anim_mode != "none" and (a1a4, a19c) not in ((9, 0), (0, 0)):
                    continue
                if anim_mode == "idle" and a1a4 == 0:
                    continue
                for tick in ((1, 2) if anim_mode == "tick" else (1,)):
                    yield peg_world(rs, fn, 0x3ED, f"d860 3ed {anim_mode} eq={eq} 1a4={a1a4} 19c={a19c} tick={tick}",
                                    a={0x16C: 9 if eq else 3, 0x1A4: a1a4, 0x19C: a19c}, s={0x64: 9}, anim=anim_mode,
                                    tick=tick, hv=-17 - tick)
    yield peg_world(rs, fn, 0x3ED, "d860 3ed fire flags", a={0x1A4: 1, 0x19C: 0, 0x40: 0x80}, hv=0x7FFF0000)
    # state 0x457 and others
    for ts in (0, 1, 0xFFFFFFFF):
        yield peg_world(rs, fn, 0x457, f"d860 457 ts={ts:#x}", ts=ts, a={0x148: 71 + ts % 5})
    for state in (1, 2, 3, 4, 6, 0x16, 0x18, 0x3E9, 0x3EB, 0x3EC, 0x3EE, 0x3EF, 0x458, 0x456, 0xFFFFFFFF):
        yield peg_world(rs, fn, state, f"d860 other state {state:#x}")


def elevator_cases(rs):
    """0x49cdd0: the Start/Trigger elevator update."""
    fn = CDD0
    # ---- state 0 initialisation ----
    for ptr, name in ((DAF0, "daf0"), (E810, "e810"), (EB30, "eb30"), (DB30, "db30"), (EE20, "ee20"), (DB50, "db50"),
                      (DB10, "db10"), (DB70, "db70"), (0, "none"), (DB10 + 1, "other")):
        for frame in (True, False):
            yield peg_world(rs, fn, 0, f"cdd0 init {name} frame={frame}", s={0x10: ptr}, frame=frame,
                            a={0x110: 5, 0x164: 0x00F0F000, 0x148: 0, 0x14C: 0})
    for tv in (10, 11):
        for eq in ("found", "zero", None, "other"):
            for found in (True, False):
                if eq == "other":
                    yield peg_world(rs, fn, 0, f"cdd0 init trap tv={tv} other found={found}", tv=tv, trap_found=found, g=(1, 2))
                else:
                    yield peg_world(rs, fn, 0, f"cdd0 init trap tv={tv} eq={eq} found={found}", tv=tv, trap_eq=eq,
                                    trap_found=found, s={0x10: DAF0})
    for nb in (1, 5):
        yield peg_world(rs, fn, 0, f"cdd0 init trap {nb} buckets", nb=nb, trap_eq="found", s={0x10: DB10})
    for d in range(10):
        for a148, a14c in ((0, 0), (17, 19)):
            yield peg_world(rs, fn, 0, f"cdd0 init dir {d} weights {a148} {a14c}", a={0x110: d, 0x148: a148, 0x14C: a14c},
                            frame=bool(d & 1))
    for s2c, s30, s34, s38 in ((0, 0, 0, 0), (1, 0, 0, 0), (0, 2, 0, 0), (0, 0, 3, 0), (0, 0, 0, 4), (5, 6, 7, 8), (0, 6, 0, 8)):
        yield peg_world(rs, fn, 0, f"cdd0 init limits {s2c} {s30} {s34} {s38}", s={0x2C: s2c, 0x30: s30, 0x34: s34, 0x38: s38},
                        a={0x4C: 0x111, 0x50: 0x222})
    for hv in (0, -1, 0x7FFFFFFF):
        yield peg_world(rs, fn, 0, f"cdd0 init hv {hv:#x}", hv=hv, frame=True)
    yield peg_world(rs, fn, 0, "cdd0 init flags", a={0x08: 0x30000, 0x134: 0xFFFFFFF0}, frame=True, s={0x10: DAF0})
    # ---- the pre-switch flag logic ----
    for state in (5, 1000, 0x3E9):
        for f164 in ((0, 1, 2, 3, 0x1000, 0x1001, 0x1002, 0x1003, 0x100) if state != 0x3E9 else (0, 2, 0x1002)):
            for pressed in ("yes", "no"):
                for s64_eq in (True, False):
                    wf, who = (0x10, "self") if pressed == "yes" else (0x10, "other")
                    yield peg_world(rs, fn, state, f"cdd0 flags {state} f164={f164:#x} pressed={pressed} home={s64_eq}",
                                    a={0x164: f164, 0xE8: 0x3131, 0xEC: 0x4242}, s={0x64: 321 if s64_eq else 322},
                                    wflags=wf, wactor=who, hv=321)
    for f164 in (0, 2, 0x1002):
        for wf, who in ((0x0, "self"), (0x10, 0), (0xEF, "self"), (0x1F, "self")):
            yield peg_world(rs, fn, 5, f"cdd0 flags f164={f164:#x} w={wf:#x} {who}", a={0x164: f164, 0xE8: 5, 0xEC: 6},
                            s={0x64: 4}, wflags=wf, wactor=who, hv=8)
    # ---- movement ----
    ds = (0, 3, 40)
    for state in (1000, 0x3E9):
        for f164 in (0, 0x100):
            for dh in ds:
                for dv in ds:
                    if state == 1000:
                        a = {0x4C: 10 + dh, 0x50: 30 + dv}
                        s = {0x2C: 10, 0x34: 30}
                    else:
                        a = {0x4C: 20 - dh, 0x50: 40 - dv}
                        s = {0x30: 20, 0x38: 40}
                    yield peg_world(rs, fn, state, f"cdd0 move {state} f164={f164:#x} dh={dh} dv={dv}",
                                    a={**a, 0x164: f164, 0x148: 37, 0x14C: 41}, s={**s, 0x64: 321}, hv=321, dt=53)
    # speed formula: truncation, clamp, large/negative products
    for state in (1000, 0x3E9):
        for a148, a14c, dt in ((37, 41, 53), (1, 1, 1), (1, 1, 999), (2500, 3000, 6), (100, 10000, 7),
                               (100000, 70000, 50000), (-1, -37, 5),
                               (0x7FFFFFFF, 0x7FFFFFFF, 2), (123456789, 987654321, 12345),
                               (5, 5, -3)):
            if state == 1000:
                a, s = {0x4C: 500, 0x50: 600}, {0x2C: 10, 0x34: 20}
            else:
                a, s = {0x4C: -500, 0x50: -600}, {0x30: -10, 0x38: -20}
            yield peg_world(rs, fn, state, f"cdd0 speed {state} {a148} {a14c} dt={dt}", a={**a, 0x148: a148, 0x14C: a14c},
                            s={**s, 0x64: 321}, hv=321, dt=dt)
    # arrival on one axis only, and exact thresholds
    for state in (1000, 0x3E9):
        for hflag, vflag in ((0, 1), (1, 0), (1, 1), (0, 0)):
            if state == 1000:
                a = {0x4C: 12 if hflag else 10, 0x50: 31 if vflag else 30}
                s = {0x2C: 10, 0x34: 30}
            else:
                a = {0x4C: 18 if hflag else 20, 0x50: 39 if vflag else 40}
                s = {0x30: 20, 0x38: 40}
            yield peg_world(rs, fn, state, f"cdd0 axis {state} h={hflag} v={vflag}", a={**a, 0x148: 400, 0x14C: 400},
                            s={**s, 0x64: 321}, hv=321, dt=20)
    for state in (1000, 0x3E9):
        for dh, dv in ((1, 0), (0, 1), (-1, 0), (0, -1), (16, 16), (-16, -16), (17, 17), (5, 5)):
            if state == 1000:
                a, s = {0x4C: 100 + dh, 0x50: 100 + dv}, {0x2C: 100, 0x34: 100}
            else:
                a, s = {0x4C: 100 - dh, 0x50: 100 - dv}, {0x30: 100, 0x38: 100}
            yield peg_world(rs, fn, state, f"cdd0 edge {state} {dh} {dv}", a={**a, 0x148: 16000, 0x14C: 16000, 0x164: 0x100},
                            s={**s, 0x64: 321}, hv=321, dt=1)
    for state in (5, 0x7, 0x3E8 + 20, 0x80000000, 0xFFFFFFFF, 2, 0x3EA):
        yield peg_world(rs, fn, state, f"cdd0 other state {state:#x}", a={0x164: 0}, s={0x64: 321}, hv=321)
    # ---- randomised extras ----
    for i in range(10):
        state = rs.choice((1000, 0x3E9))
        pos = rs.randrange(-300, 300)
        yield peg_world(rs, fn, state, f"cdd0 random {i}",
                        a={0x4C: pos, 0x50: rs.randrange(-300, 300), 0x148: rs.randrange(-50, 5000),
                           0x14C: rs.randrange(-50, 5000), 0x164: rs.choice((0, 0x100, 0x1000, 0x1100, 0x2, 0x102, 1, 0x1002)),
                           0xE8: rs.randrange(-100, 100), 0xEC: rs.randrange(-100, 100)},
                        s={0x2C: rs.randrange(-300, 300), 0x30: rs.randrange(-300, 300), 0x34: rs.randrange(-300, 300),
                           0x38: rs.randrange(-300, 300), 0x64: rs.choice((321, 322))},
                        hv=321, dt=rs.randrange(1, 400), wflags=rs.choice((0, 0x10)), wactor=rs.choice(("self", "other")))
    for i in range(5):
        yield peg_world(rs, fn, 0, f"cdd0 random init {i}", a={0x110: rs.randrange(0, 10), 0x148: rs.choice((0, 9)),
                                                          0x14C: rs.choice((0, 8)), 0x4C: rs.randrange(-50, 50),
                                                          0x50: rs.randrange(-50, 50)},
                        s={0x10: rs.choice((DAF0, E810, EB30, DB30, EE20, DB50, DB10, DB70, 0)),
                           0x2C: rs.choice((0, 5)), 0x30: rs.choice((0, 6)), 0x34: rs.choice((0, 7)), 0x38: rs.choice((0, 8))},
                        frame=rs.choice((True, False)), hv=rs.randrange(-9, 9), tv=rs.choice((10, 3)),
                        trap_eq=rs.choice(("found", "zero", None)), trap_found=rs.choice((True, False)))


def thunk_cases(rs):
    # state setups chosen so that the called body does something visible
    for fn, label, targets in ((E7B0, "e7b0", E4E0), (E7D0, "e7d0", E4E0), (E7F0, "e7f0", E4E0)):
        for state, ptr in ((0, fn), (0, E810), (0x3EC, fn), (0x3EE, fn), (0x3EF, fn)):
            yield case(f"{label} state {state:#x}", fn, rs, s={0x1C: state, 0x10: ptr}, g=(1, 3), gv=rs.randrange(1 << 32))
    for fn, label in ((DAF0, "daf0"), (DB10, "db10"), (DB30, "db30"), (DB50, "db50"), (DB70, "db70")):
        for state in (0, 1000, 0x3E9, 5):
            yield case(f"{label} state {state:#x}", fn, rs, s={0x1C: state, 0x10: fn}, frame=True,
                       a={0x110: 3, 0x164: 0, 0x148: 20, 0x14C: 21}, gv=rs.randrange(1 << 32))
    # 0x49ee20 reaches the original 0x49eb30, whose own states we also vary
    for state in (0, 0x3EA, 0x3EB, 0x3EC, 0x3ED, 0x3EE, 0x3EF, 5):
        for ptr in (EE20,):
            yield case(f"ee20 state {state:#x} fn {ptr:#x}", EE20, rs, s={0x1C: state, 0x10: ptr, 0x68: 55}, g=(1, 3),
                       a={0x1A4: 1, 0x19C: 0, 0x16C: 9}, hv=77)
