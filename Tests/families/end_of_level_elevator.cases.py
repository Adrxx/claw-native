"""Cases for end_of_level_elevator: End-of-level elevator entries.

Coverage comes from fixed grids; random_source only adds extra variety.
"""
from clawparity.cases import Case

SETUP060 = 0x49E060
STEP1C0 = 0x49E1C0
ENTRY2A0 = 0x49E2A0
DELTA = 0x537210
SCENE = 0x5371FC
BLOCK = 0x537960
UNICODE = 0x540E00
HANDLER = 0x49E810

M32 = 0xFFFFFFFF
TRAP_KEY = b"LEVEL_TRAPELEVATOR\0"
STONE_KEY = b"LEVEL_STEPPINGSTONE\0"


def u(value):
    return value & M32


def filler(seed, size):
    """Distinct, non-zero words for every position of an object."""
    return [u(0x01010101 * ((seed + n) % 251 + 1) ^ (0x9E3779B1 * (n + seed + 1))) | 0x01000000 for n in range(size // 4)]


def blob(env, size, name, seed):
    return env.object(size, name, words=filler(seed, size))


def hash_key(key):
    value = 0
    for byte in key.rstrip(b"\0"):
        value = u(value * 0x21 + (byte - 256 if byte > 127 else byte))
    return value


# ---------------------------------------------------------------- 0x49e060

X060 = [(s, 0x1111, 0x2222, p) for s in (1, 2, 3, 6, 7, 100, 0x7FFF) for p in (-30, 5)]
X060 += [(z, lo, hi, p) for z in (0, -4)
         for (lo, hi, p) in ((10, 20, 21), (10, 20, 22), (10, 20, 10), (10, 20, 9), (10, 20, 15), (20, 10, 5),
                             (5, 5, 5), (5, 6, 6), (5, 6, 4), (7, 6, 7), (-10, -4, -3), (-10, -4, -12))]
Y060 = [(s, 0x3333, 0x4444, p) for s in (1, 2, 3, 5, 8, 99, 0x6FFF) for p in (-41, 6)]
Y060 += [(z, lo, hi, p) for z in (0, -9)
         for (lo, hi, p) in ((30, 41, 42), (30, 41, 43), (30, 41, 30), (30, 41, 29), (30, 41, 35), (50, 40, 6),
                             (8, 8, 8), (8, 9, 9), (8, 9, 7), (3, 2, 3), (-20, -3, -2), (-20, -3, -22))]
MODES = [7, 1, 4, 8, 9, 0, 2, 3, 5, 6, 10, -1, 0x80000004]
SCALES = [0, 0x7D, 1000, 500, 3, -7, 2000, 1, 12345, -250, 31, 4]


def setup_060(x, y, mode, s148, s14c):
    def setup(env):
        player = blob(env, 0x178, "player", 11)
        state = blob(env, 0xD4, "elevator", 29)
        env.put(player + 0x4C, u(x[3]))
        env.put(player + 0x50, u(y[3]))
        env.put(player + 0x110, u(mode))
        env.put(player + 0x148, u(s148))
        env.put(player + 0x14C, u(s14c))
        env.put(player + 0x158, 0x5A5A5A5A)
        env.put(player + 0x15C, 0xA5A5A5A5)
        env.put(state + 200, u(x[0]))
        env.put(state + 0xCC, u(y[0]))
        env.put(state + 0x2C, u(x[1]))
        env.put(state + 0x30, u(x[2]))
        env.put(state + 0x34, u(y[1]))
        env.put(state + 0x38, u(y[2]))
        return {"player": player, "state": state}
    return setup


def case_060(label, setup):
    return Case(label, SETUP060, setup, arguments=(lambda t: t["player"], lambda t: t["state"]))


# ---------------------------------------------------------------- 0x49e1c0

def setup_1c0(xa, ya, p3_unused=0):
    """xa / ya: dict of axis fields. Keys: scale, extent, half, pos, rel, lo, hi (hi = upper bound)."""
    def setup(env):
        player = blob(env, 0x178, "player", 53)
        state = blob(env, 0xD4, "elevator", 71)
        for axis, offsets in ((xa, (0x148, 0x4C, 0x4C, 0x3C, 0x44, 0x2C, 0x30, 0x158)),
                              (ya, (0x14C, 0x50, 0x50, 0x40, 0x48, 0x34, 0x38, 0x15C))):
            scale, total, half, rel, lo, hi, out = offsets[0], offsets[2], offsets[3], offsets[4], offsets[5], offsets[6], offsets[7]
            env.put(player + scale, u(axis["scale"]))
            env.put(player + total, u(axis["pos"]))
            env.put(player + out, 0x5A5A1234)
            env.put(state + (0x4C if axis is xa else 0x50), u(axis["extent"]))
            env.put(state + half, u(axis["half"]))
            env.put(state + rel, u(axis["rel"]))
            env.put(state + lo, u(axis["lo"]))
            env.put(state + hi, u(axis["hi"]))
        return {"player": player, "state": state}
    return setup


def axis(scale=1000, extent=7, half=3, rel=2, lo=100, hi=106, pos=777):
    return dict(scale=scale, extent=extent, half=half, rel=rel, lo=lo, hi=hi, pos=pos)


def case_1c0(label, xa, ya, p3):
    return Case(label, STEP1C0, setup_1c0(xa, ya), arguments=(lambda t: t["player"], lambda t: t["state"], u(p3)))


def controlled(extent, half, remainder, loop, p3=13, lo=100, pos=777):
    """Axis whose remainder after the division by extent is `remainder` (scale 1000 so q = rel + p3)."""
    quotient = remainder + loop * extent
    return axis(scale=1000, extent=extent, half=half, rel=u(quotient - p3), lo=lo, hi=lo + extent + 3, pos=pos)


# ---------------------------------------------------------------- 0x49e2a0

def setup_2a0(state_value=0, handler=False, quad=True, g10=True, has_trap=True, has_stone=True, p170sel=0,
              p64=0, buckets=1, decoys=True, x=(5, 40, 60, 30), y=(0, 50, 80, 20), mode=7, flags=0x100,
              s148=0x7D, s14c=0, delta=21, seed=0, trap_value=0x1234, stone_value=0x5678):
    def setup(env):
        player = blob(env, 0x178, "player", 101 + seed)
        state = blob(env, 0xD4, "elevator", 131 + seed)
        quadrant = blob(env, 0x30, "quad", 151 + seed)
        block = blob(env, 0xB0, "block", 171 + seed)
        scene_obj = blob(env, 0x40, "scene", 191 + seed)
        mid = blob(env, 0x20, "scene-mid", 211 + seed)
        owner = blob(env, 0x20, "owner", 231 + seed)
        res = blob(env, 0x40, "resource", 251 + seed)
        table = env.object(4 * buckets, "bucket-table", fill=0)
        wanted = {0: 0, 1: trap_value, 2: stone_value, 3: 0xDEAD0007}[p170sel]

        def node(key, value, nxt):
            keyptr = env.object(len(key), "key", data=key)
            return env.object(16, "node", words=[nxt, hash_key(key), keyptr, u(value)])

        chains = {}

        def add(key, value):
            index = hash_key(key) % buckets
            chains[index] = node(key, value, chains.get(index, 0))

        if has_stone:
            add(STONE_KEY, stone_value)
        if has_trap:
            add(TRAP_KEY, trap_value)
        if decoys:
            for key in (b"LEVEL_TRAPELEVATOS\0", b"LEVEL_STEPPINGSTONF\0", b"LEVEL_TRAPE\0", b"LEVEL_STEPPINGSTONE2\0"):
                index = hash_key(key) % buckets
                chains[index] = node(key, 0xBAD0BAD, chains.get(index, 0))
            # decoys that share the wanted buckets, placed in front of the real nodes
            for key in (TRAP_KEY, STONE_KEY):
                index = hash_key(key) % buckets
                chains[index] = node(b"LEVEL_ZZZ\0", 0x0BADF00D, chains.get(index, 0))
        for index, head in chains.items():
            env.put(table + 4 * index, head)
        env.put(res + 0x14, table, buckets)
        env.put(owner + 0x10, res)
        env.put(player + 0xC, owner)
        env.put(player + 0x6C, state)
        env.put(player + 0x170, u(wanted))
        env.put(player + 0x174, quadrant if quad else 0)
        env.put(player + 8, flags)
        env.put(player + 0x64, p64)
        env.put(player + 0xD0, 0x11111111)
        env.put(player + 0x4C, u(x[3]))
        env.put(player + 0x50, u(y[3]))
        env.put(player + 0x110, u(mode))
        env.put(player + 0x148, u(s148))
        env.put(player + 0x14C, u(s14c))
        env.put(state + 0x1C, u(state_value))
        env.put(state + 0x10, HANDLER if handler else 0x49E800 + seed)
        env.put(state + 200, u(x[0]))
        env.put(state + 0xCC, u(y[0]))
        env.put(state + 0x2C, u(x[1]))
        env.put(state + 0x30, u(x[2]))
        env.put(state + 0x34, u(y[1]))
        env.put(state + 0x38, u(y[2]))
        if state_value == 1:
            env.put(state + 0x4C, 14)
            env.put(state + 0x50, 9)
            env.put(state + 0x3C, 6)
            env.put(state + 0x40, 5)
            env.put(state + 0x44, 3)
            env.put(state + 0x48, 4)
        env.put(quadrant + 0x18, u(x[1]), u(y[1]), u(x[2]), u(y[2]))
        scene_obj_ptr = scene_obj
        env.put(scene_obj + 0x2C, mid)
        env.put(mid + 0x14, 10 if g10 else 9)
        env.put(SCENE, scene_obj_ptr)
        env.put(BLOCK, block)
        env.put(DELTA, u(delta))
        env.put(UNICODE, 0)
        return {"player": player, "state": state}
    return setup


def case_2a0(label, **options):
    return Case(label, ENTRY2A0, setup_2a0(**options), arguments=(lambda t: t["player"],))


def cases(random_source):
    # ---- 0x49e060: fixed grid, every combination of the branch tables is reached
    nx, ny = len(X060), len(Y060)
    for i in range(260):
        x, y = X060[i % nx], Y060[(i * 3 + i // nx) % ny]
        mode = MODES[(i * 5 + i // 13) % len(MODES)]
        s148 = SCALES[(i * 7 + i // 12) % len(SCALES)]
        s14c = SCALES[(i * 11 + 5 + i // 5) % len(SCALES)]
        if s148 == -1 or s14c == -1:
            continue
        yield case_060(f"setup grid {i} x={x} y={y} mode={mode} scale={s148},{s14c}", setup_060(x, y, mode, s148, s14c))
    for i, mode in enumerate(MODES):
        yield case_060(f"mode {mode:#x} both axes grow", setup_060((2, 0, 0, 40), (3, 0, 0, 60), mode, 1000, 1000))
        yield case_060(f"mode {mode:#x} presets out of range", setup_060((0, 10, 20, 21), (0, 30, 41, 43), mode, 250, 125))
    for _ in range(30):
        x = (random_source.randrange(-5, 40), random_source.randrange(-60, 60), random_source.randrange(-60, 60),
             random_source.randrange(-100, 100))
        y = (random_source.randrange(-5, 40), random_source.randrange(-60, 60), random_source.randrange(-60, 60),
             random_source.randrange(-100, 100))
        yield case_060("random setup", setup_060(x, y, random_source.choice(MODES), random_source.randrange(-3000, 3000) or 77,
                                                 random_source.randrange(-3000, 3000) or 91))

    # ---- 0x49e1c0: controlled remainders on both axes
    xcfg = []
    for extent in (2, 7, 10):
        for half in (0, 1, extent // 2, extent - 1, extent, extent + 3):
            for remainder in (0, extent // 2, extent - 1):
                xcfg.append((extent, half, remainder))
    n = len(xcfg)
    for i, (extent, half, remainder) in enumerate(xcfg):
        ex, hx, rx = xcfg[(i * 5 + 1) % n]
        yield case_1c0(f"x extent={extent} half={half} rem={remainder}; y extent={ex} half={hx} rem={rx}",
                       controlled(extent, half, remainder, loop=i % 3, lo=100 + i, pos=777 + i),
                       controlled(ex, hx, rx, loop=(i + 1) % 4, p3=13, lo=-50 - i, pos=555 + 3 * i), 13)
    for p3 in (0, 1, -1, 1000, -1000, 0x7FFFFFFF, 0x80000000):
        yield case_1c0(f"p3={p3:#x}", axis(rel=6, extent=7, half=3), axis(rel=9, extent=10, half=5, lo=-20, hi=-10), p3)
    states = [(1000, 6), (0, 6), (-5, 6), (1000, 0), (1000, -3), (1, 1)]
    for i, (sx, ex) in enumerate(states):
        for j, (sy, ey) in enumerate(states):
            yield case_1c0(f"gates x=({sx},{ex}) y=({sy},{ey})",
                           axis(scale=sx, extent=ex, half=2, rel=3, lo=10 + i, hi=15 + i, pos=900 + i),
                           axis(scale=sy, extent=ey, half=4, rel=1, lo=20 + j, hi=29 + j, pos=800 + j), 9)
    scales = [1, 3, 7, 125, 500, 999, 1001, 2000, 12345, 0x10000]
    for k in range(40):
        extent = random_source.randrange(1, 40)
        yield case_1c0("random both axes",
                       axis(scale=random_source.choice(scales), extent=extent, half=random_source.randrange(0, 45),
                            rel=random_source.randrange(-500, 500), lo=random_source.randrange(-100, 100),
                            hi=random_source.randrange(-100, 100), pos=random_source.randrange(-50, 50)),
                       axis(scale=random_source.choice(scales), extent=random_source.randrange(1, 40),
                            half=random_source.randrange(0, 45), rel=random_source.randrange(-500, 500),
                            lo=random_source.randrange(-100, 100), hi=random_source.randrange(-100, 100),
                            pos=random_source.randrange(-50, 50)), random_source.randrange(-300, 300))

    # ---- 0x49e2a0: entry
    index = 0
    for has_trap in (False, True):
        for has_stone in (False, True):
            for p170sel in (0, 1, 2, 3):
                for g10 in (False, True):
                    for handler in (False, True):
                        index += 1
                        yield case_2a0(
                            f"first entry trap={has_trap} stone={has_stone} p170={p170sel} g10={g10} handler={handler}",
                            has_trap=has_trap, has_stone=has_stone, p170sel=p170sel, g10=g10, handler=handler,
                            quad=bool(index % 3), p64=(0, 77)[(index // 3) % 2], buckets=(1, 3, 7)[index % 3],
                            decoys=bool((index // 2) % 2), seed=index,
                            x=X060[index % nx], y=Y060[(index * 3) % ny], mode=MODES[index % len(MODES)],
                            s148=SCALES[(index + 1) % len(SCALES)], s14c=SCALES[(index * 5 + 3) % len(SCALES)],
                            flags=(0x100, 0x20001, 0xFFFFFFFF, 0)[index % 4])
    for quad in (False, True):
        for p64 in (0, 1, 0x80000000):
            yield case_2a0(f"quad={quad} p64={p64:#x}", quad=quad, p64=p64, flags=0x2040, seed=90 + p64 % 7)
    for state_value in (1,):
        for i in range(24):
            yield case_2a0(f"second entry {i}", state_value=state_value, delta=(21, 0, -5, 1000, 0x7FFF, 3)[i % 6],
                           s148=SCALES[i % len(SCALES)], s14c=SCALES[(i * 7 + 2) % len(SCALES)] or 5, seed=i,
                           x=X060[i % nx], y=Y060[(i * 3) % ny], mode=MODES[i % 13])
    for state_value in (2, -1, 0x7FFFFFFF, 0x80000000, 0xFF):
        yield case_2a0(f"unknown state {state_value:#x}", state_value=state_value, seed=3)
    for _ in range(20):
        yield case_2a0("random entry", has_trap=random_source.random() < 0.7, has_stone=random_source.random() < 0.7,
                       p170sel=random_source.randrange(4), g10=random_source.random() < 0.6,
                       handler=random_source.random() < 0.4, quad=random_source.random() < 0.7,
                       p64=random_source.choice((0, random_source.randrange(1, 9999))),
                       buckets=random_source.choice((1, 2, 5, 11)), decoys=random_source.random() < 0.5,
                       seed=random_source.randrange(200), trap_value=random_source.randrange(1, 1 << 30),
                       stone_value=random_source.randrange(1, 1 << 30),
                       x=(random_source.randrange(-3, 30), random_source.randrange(-50, 50),
                          random_source.randrange(-50, 50), random_source.randrange(-90, 90)),
                       y=(random_source.randrange(-3, 30), random_source.randrange(-50, 50),
                          random_source.randrange(-50, 50), random_source.randrange(-90, 90)),
                       mode=random_source.choice(MODES), s148=random_source.choice((0, 5, 1000, -3)),
                       s14c=random_source.choice((0, 7, 1000, -2)))
