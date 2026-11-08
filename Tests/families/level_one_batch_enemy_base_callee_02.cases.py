"""Cases for level_one_batch_enemy_base_callee_02: Level 1 enemy shared helpers 0x404dd0, 0x43f640, 0x43f740.

Coverage is directed: every branch has explicit cases whose rand values and doubles are chosen
from the arithmetic of the original, so nothing depends on the random seed. Random cases come on top.
"""
import math
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns

DEC = 0x404DD0
JUMP = 0x43F640
MOVE = 0x43F740
RAND = 0x4A3050
TRIE = 0x537668          # the global table 0x4dba00 searches
KEY_MOVEBACK = 0x5271A8  # "LS_MOVEBACK"
KEY_JUMP = 0x527204      # "LS_JUMP"

WIDTH, HEIGHT = 500, 40
SHIFT_X, SHIFT_Y = 2, 1
ROW = 128
NAN = float("nan")
INF = float("inf")


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def dbl(value):
    return struct.pack("<d", value)


def trunc32(d):
    """Low word of the 64-bit truncating conversion done by 0x4a30e0 (fistp with chop)."""
    if math.isnan(d) or math.isinf(d) or abs(d) >= 2.0 ** 63:
        return 0
    return int(d) & 0xFFFFFFFF


def x_of(mode, r, d):
    base = (s32(r) - 0x33 * int(s32(r) / 0x33)) + 0x4B  # C-style remainder
    t = s32(trunc32(d))
    return s32(base + t) if mode == 3 else s32(t - base)


def cmp_value(mode, x, rel):
    """The compared double for relation `rel` of the double to (double)x, and the opposite one for the other field."""
    if rel == "nan":
        return NAN
    delta = {"gt": 0.5, "eq": 0.0, "lt": -0.5, "gt_far": 1000.0, "lt_far": -1000.0,
             "gt_tiny": 1e-9, "lt_tiny": -1e-9}[rel]
    return x + delta


def passes(mode, rel):
    if mode == 3:
        return rel in ("gt", "eq", "gt_far", "gt_tiny")
    return rel in ("lt", "eq", "lt_far", "lt_tiny", "nan")


def clamp(v, limit):
    return 0 if v < 0 else (limit - 1 if v >= limit else v)


def cell_index(x, y):
    ix = clamp(x, WIDTH) >> SHIFT_X
    iy = clamp(y, HEIGHT) >> SHIFT_Y
    return (iy % 3) * ROW + ix


def script_effect(script, hook=None):
    def effect(env, call):
        n = env.calls_so_far(call.function)
        value = script[min(n, len(script)) - 1]
        if hook:
            hook(env, n)
        return value & 0xFFFFFFFF
    return effect


def lookup(env, kind, key, value, noise):
    """Build the table 0x4dba00 searches so that `key` hits (or misses) in the way `kind` says."""
    if kind == "none":
        env.put(TRIE + 0x18, 0)
        return
    leaf = env.object(0x20, "leaf", data=noise[:0x20])
    env.put(leaf + 8, 0)
    env.put(leaf + 0xC, key)
    env.put(leaf + 0x10, value)
    root = env.object(0x20, "root", data=noise[:0x20])
    env.put(root, leaf, leaf)
    env.put(root + 8, 0)
    if kind == "hit":
        pass
    elif kind == "deep":
        inner = env.object(0x20, "inner", data=noise[:0x20])
        env.put(inner, leaf, leaf)
        env.put(inner + 8, 5)
        env.put(root, inner, inner)
    elif kind == "miss_string":
        other = env.object(16, "other-key", data=b"LS_MOVEBACX\0\0\0\0\0")
        env.put(leaf + 0xC, other)
    elif kind == "miss_bits":
        env.put(root + 8, 200)
    elif kind == "miss_null":
        env.put(root, 0, 0)
    env.put(TRIE + 0x18, root)


def tile_world(env, noise, salt, sentinels):
    """A tile map R with a vtable object per tile; returns (R, objects)."""
    vtable = env.object(0x40, "tile-vtable", data=noise[:0x40])
    objects = []
    for i in range(6):
        o = env.object(0x10, f"tile-object-{i}", data=noise[i:i + 0x10])
        env.put(o, vtable)
        objects.append(o)
    table = env.object(6 * 4, "tile-table")
    for i, o in enumerate(objects):
        env.put(table + 4 * i, o)
    cells = env.object(3 * ROW * 4, "tile-cells")
    for i in range(3 * ROW):
        env.put(cells + 4 * i, (((i * 7 + salt) & 0x3FFF) << 16) | ((i + salt) % 6))
    for index, value in sentinels.items():
        env.put(cells + 4 * index, value)
    rows = env.object(HEIGHT * 4, "tile-rows")
    for i in range(HEIGHT):
        env.put(rows + 4 * i, (i % 3) * ROW)
    grid = env.object(0x98, "tile-grid", data=noise[:0x98])
    env.put(grid + 0x20, cells)
    env.put(grid + 0x24, rows)
    env.put(grid + 0x30, WIDTH, HEIGHT)
    env.put(grid + 0x8C, SHIFT_X)
    env.put(grid + 0x90, SHIFT_Y)
    tile_map = env.object(0x60, "tile-map", data=noise[:0x60])
    env.put(tile_map + 0x4C, table)
    env.put(tile_map + 0x5C, grid)
    return tile_map, vtable


def swap_sentinels(pairs, noise):
    """Words for S+0x118.. : three pairs of (first, second); first of 0x80000000 means untouched."""
    return pairs


def make_state(env, noise, S_ints, flag, sentinel_pairs, argx, old_o, tail_arg_offset):
    """Objects shared by both functions: O at E+0x10, S at E+0x12c and the 4c8220 argument."""
    o = env.object(0x40, "owner", data=noise[:0x40])
    env.put(o + 0x1C, old_o)
    s = env.object(0x1C0, "second", data=noise[:0x1C0])
    env.put(s + 0x40, flag)
    for k, (a, b) in enumerate(sentinel_pairs):
        env.put(s + 0x118 + 0x10 * k, a)
        env.put(s + 0x120 + 0x10 * k, b)
    env.put(s + 0x190, S_ints[0])
    env.put(s + 8, S_ints[1])
    if argx == "zero":
        x = 0
    else:
        y = env.object(0x40, "list-item", data=noise[:0x40])
        env.put(y + 0x1C, S_ints[2])
        arr = env.object(16, "list-array")
        env.put(arr, y, S_ints[3])
        x = env.object(0x20, "list", data=noise[:0x20])
        env.put(x + 0xC, arr)
        env.put(x + 0x10, {"one": 1, "many": 5}[argx])
    return o, s, x


def move_setup(p, noise):
    mode, r = p["mode"], p["r"]
    d68 = p["d68"]
    x = x_of(mode, r, d68)
    ya, yb = p["ya"], p["yb"]
    y = s32(ya + 1 + yb)
    rel = p["rel"]
    used = cmp_value(mode, x, rel)
    ok = passes(mode, rel)
    other = x + (5.0 if (ok and mode == 3) or (not ok and mode != 3) else -5.0)

    def setup(env):
        e = env.object(0x400, "enemy", data=noise[:0x400])
        sentinels = {}
        if p.get("sent_y") is not None:
            sentinels[cell_index(x, y)] = p["sent_y"]
        if p.get("sent_y1") is not None:
            sentinels[cell_index(x, y - 1)] = p["sent_y1"]
        tile_map, _ = tile_world(env, noise, p.get("salt", 3), sentinels)
        q = env.object(0x30, "mid", data=noise[:0x30])
        env.put(q + 0x24, tile_map)
        pp = env.object(0x130, "primary", data=noise[:0x130])
        env.put(pp + 0xC, q)
        env.put(pp + 0x124, ya)
        env.put(pp + 0x50, yb)
        o, s, argx = make_state(env, noise, p["s_ints"], p["flag"], p["pairs"], p["argx"], p["old_o"], 0x308)
        env.put(e + 0x10, o)
        env.put(e + 0x128, pp)
        env.put(e + 0x12C, s)
        env.put(e + 0x18C, mode)
        env.put(e + 0x68, *struct.unpack("<II", dbl(d68)))
        env.put(e + 0x98, *struct.unpack("<II", dbl(used if mode == 3 else other)))
        env.put(e + 0x80, *struct.unpack("<II", dbl(other if mode == 3 else used)))
        env.put(e + 0x138, p["neg"][0], p["neg"][1])  # E+0x138 and E+0x13c
        env.put(e + 0x140, p["neg"][2])
        env.put(e + 0x308, argx)
        lookup(env, p["trie"], KEY_MOVEBACK, p["value"], noise)
        env.override(RAND, returns(r))
        hook = None
        hook_name = p.get("hook")
        if hook_name:
            at = p.get("hook_at", 1)
            if hook_name == "swap_primary":
                map2, _ = tile_world(env, noise[::-1], 11, {})
                q2 = env.object(0x30, "mid2", data=noise[:0x30])
                env.put(q2 + 0x24, map2)
                p2 = env.object(0x130, "primary2", data=noise[:0x130])
                env.put(p2 + 0xC, q2)
                env.put(p2 + 0x124, ya)
                env.put(p2 + 0x50, yb)
            elif hook_name == "swap_second":
                s2 = env.object(0x1C0, "second2", data=noise[::-1][:0x1C0])
                env.put(s2 + 0x40, p["flag"] ^ 2)
                env.put(s2 + 0x190, 0x1234567)
                for k, (a, b) in enumerate(p["pairs"]):
                    env.put(s2 + 0x118 + 0x10 * k, b)
                    env.put(s2 + 0x120 + 0x10 * k, a)
            elif hook_name == "swap_owner":
                o2 = env.object(0x40, "owner2", data=noise[:0x40])
                env.put(o2 + 0x1C, 0x5A5A5A5A)
            elif hook_name == "swap_arg":
                _, _, arg2 = make_state(env, noise[::-1], (7, 8, 9, 10), 0, p["pairs"], "one", 0, 0)

            def hook(env, n, hook_name=hook_name):
                if n != at:
                    return
                if hook_name == "mode_to_2":
                    env.put(e + 0x18C, 2)
                elif hook_name == "mode_from_2":
                    env.put(e + 0x18C, 6)
                elif hook_name == "mode_to_3":
                    env.put(e + 0x18C, 3)
                elif hook_name == "swap_primary":
                    env.put(e + 0x128, p2)
                elif hook_name == "swap_second":
                    env.put(e + 0x12C, s2)
                elif hook_name == "swap_owner":
                    env.put(e + 0x10, o2)
                elif hook_name == "swap_arg":
                    env.put(e + 0x308, arg2)
                elif hook_name == "flag_toggle":
                    env.put(s + 0x40, env.get(s + 0x40) ^ 2)
                elif hook_name == "mode_to_2_flag_set":
                    env.put(e + 0x18C, 2)
                    env.put(s + 0x40, env.get(s + 0x40) | 2)
        stub = env.stub("tile-method", "thiscall", 2, script_effect(p["script"], hook))
        # every tile object shares the vtable, patched here so the method is the case's stand-in
        for token, size in list(env.spans.items()):
            if env.names.get(token) == "tile-vtable":
                env.put(token + 0x20, stub)
        return {"e": e}

    return setup


DEFAULT_PAIRS = [(0x11111111, 0x22222222), (0x33333333, 0x44444444), (0x55555555, 0x66666666)]


def move(label, noise, **kw):
    p = dict(mode=0, r=10, d68=100.0, rel="eq", ya=5, yb=2, script=[1, 0], flag=0, pairs=DEFAULT_PAIRS,
             argx="one", s_ints=(0x0BADF00D, 0x20, 0x3C3C, 0x7A7A), old_o=0x0DDBA11, neg=(0x1234, 0x5678, 0x9ABC),
             trie="hit", value=0x7E57AB1E)
    p.update(kw)
    return Case(label, MOVE, move_setup(p, noise), receiver=lambda t: t["e"])


def jump_setup(flag, argx, trie, value, noise, s8, old_o, s_ints):
    def setup(env):
        e = env.object(0x400, "enemy", data=noise[:0x400])
        m = env.object(0x120, "mode-holder", data=noise[:0x120])
        env.put(m + 0xCC, flag)
        o, s, x = make_state(env, noise, (s_ints[0], s8, s_ints[1], s_ints[2]), 0, DEFAULT_PAIRS, argx, old_o, 0x33C)
        env.put(e + 0xC, m)
        env.put(e + 0x10, o)
        env.put(e + 0x12C, s)
        env.put(e + 0x33C, x)
        lookup(env, trie, KEY_JUMP, value, noise)
        return {"e": e}
    return setup


def dec_setup(v, w, noise):
    def setup(env):
        e = env.object(0x20, "receiver", data=noise[:0x20])
        m = env.object(0x120, "holder", data=noise[:0x120])
        env.put(m + 0x10C, v)
        a = env.object(0x110, "argument", data=noise[:0x110])
        env.put(a + 0x104, w)
        env.put(a + 0x10C, 0x77777777)
        env.put(e + 0xC, m)
        return {"e": e, "a": a}
    return setup


def cases(random_source):
    rs = random_source

    def noise():
        return rs.randbytes(0x400)

    # ---- 0x404dd0 -------------------------------------------------------------
    for v in (-0x80000000, -1, 0, 1, 7, 100, 0x7FFFFFFF):
        for w in (0, 1, -1, 100, 0x7FFFFFFF):
            yield Case(f"dec {v} - {w}", DEC, dec_setup(v & 0xFFFFFFFF, w & 0xFFFFFFFF, noise()),
                       receiver=lambda t: t["e"], arguments=(lambda t: t["a"],))
    for _ in range(8):
        v, w = rs.randrange(-300, 3000), rs.randrange(-50, 3000)
        yield Case(f"dec random {v} - {w}", DEC, dec_setup(v & 0xFFFFFFFF, w & 0xFFFFFFFF, noise()),
                   receiver=lambda t: t["e"], arguments=(lambda t: t["a"],))

    # ---- 0x43f640 -------------------------------------------------------------
    for flag in (1, 0, 2, 3, 8, 0x101, 0xFFFFFFFF, 0x80000001):
        for argx in ("one", "zero"):
            yield Case(f"jump flag {flag:#x} arg {argx}", JUMP,
                       jump_setup(flag, argx, "hit", 0x3A3A3A3A, noise(), 0x10, 0x0A0B0C0D, (0x1357, 0x2468, 0x369)),
                       receiver=lambda t: t["e"])
    for argx in ("many", "one", "zero"):
        for trie in ("hit", "deep", "none", "miss_string", "miss_bits", "miss_null"):
            for s8 in (rs.choice((0, 4)),):
                yield Case(f"jump {argx} {trie} s8={s8:#x}", JUMP,
                           jump_setup(1, argx, trie, rs.randrange(1, 1 << 32), noise(), s8,
                                      rs.randrange(1, 1 << 32), (rs.randrange(1 << 32), rs.randrange(1 << 32),
                                                                 rs.randrange(1 << 32))),
                           receiver=lambda t: t["e"])
    for _ in range(10):
        flag = rs.choice((1, 1, 1, rs.randrange(1 << 32)))
        yield Case(f"jump random flag {flag:#x}", JUMP,
                   jump_setup(flag, rs.choice(("one", "many", "zero")), rs.choice(("hit", "deep", "none")),
                              rs.randrange(1, 1 << 32), noise(), rs.randrange(1 << 32), rs.randrange(1 << 32),
                              (rs.randrange(1 << 32), rs.randrange(1 << 32), rs.randrange(1 << 32))),
                   receiver=lambda t: t["e"])

    # ---- 0x43f740: both sign branches x all four fcompp outcomes ---------------------
    modes = (3, 0, 1, 2, 4, 0xFFFFFFFF)
    for mode in modes:
        for rel in ("gt", "eq", "lt", "nan", "gt_far", "lt_far", "gt_tiny", "lt_tiny"):
            if mode not in (3, 0) and rel not in ("gt", "eq", "lt", "nan"):
                continue
            yield move(f"mode {mode:#x} compare {rel}", noise(), mode=mode, rel=rel, d68=100.0, r=17)

    # ---- every outcome pattern of the three 0x4207f0 checks and the final check ---------
    scripts = {
        "first=1,last=0": [1, 0],
        "first=1,last=1": [1, 1],
        "first=1,last=7": [1, 7],
        "first=0,second=2,last=0": [0, 2, 0],
        "first=0,second=2,last=3": [0, 2, 3],
        "first=2,second=2,last=0": [2, 2, 0],
        "first=0,second=0,third=3,last=0": [0, 0, 3, 0],
        "first=3,second=1,third=3,last=0": [3, 1, 3, 0],
        "first=0,second=0,third=3,last=9": [0, 0, 3, 9],
        "first=0,second=0,third=2": [0, 0, 2],
        "first=0,second=0,third=0": [0, 0, 0],
        "first=2,second=0,third=1": [2, 0, 1],
        "first=3,second=3,third=3,last=0": [3, 3, 3, 0],
        "first=4,second=4,third=4": [4, 4, 4],
        "first=big,second=big,third=big": [0xFFFFFFFF, 0x80000002, 0x100000003 & 0xFFFFFFFF],
        "first=1 with high bits": [0x80000001, 0],
    }
    for mode in (3, 0, 2):
        for name, script in scripts.items():
            yield move(f"mode {mode:#x} checks {name}", noise(), mode=mode, rel="eq", script=script, d68=80.0, r=33)

    # ---- tail: mode 2 versus other, swap flag, sentinel values in the 0x4060b0/0x406310 pairs ---
    sentinel = 0x80000000
    pair_sets = {
        "plain": DEFAULT_PAIRS,
        "first-sentinel": [(sentinel, 0x22), (0x33, 0x44), (0x55, 0x66)],
        "second-sentinel": [(0x11, 0x22), (sentinel, 0x44), (0x55, 0x66)],
        "third-sentinel": [(0x11, 0x22), (0x33, 0x44), (sentinel, 0x66)],
        "all-sentinel": [(sentinel, 0x22), (sentinel, 0x44), (sentinel, 0x66)],
        "negatives": [(-0x7FFFFFFF, 0x7FFFFFFF), (-1, 5), (0, -9)],
    }
    for mode in (2, 3, 0):
        for flag in (0, 2, 0xFFFFFFFD, 1):
            yield move(f"tail mode {mode:#x} flags {flag:#x}", noise(), mode=mode, flag=flag, d68=60.0, r=5,
                       rel="eq", script=[1, 0])
        for name, pairs in pair_sets.items():
            for flag in (0, 2):
                yield move(f"tail mode {mode:#x} pairs {name} flags {flag}", noise(), mode=mode, flag=flag,
                           pairs=pairs, d68=60.0, r=5, rel="eq", script=[1, 0])
    for trie in ("hit", "deep", "none", "miss_string", "miss_bits", "miss_null"):
        for mode in (2, 3, 0):
            yield move(f"tail lookup {trie} mode {mode:#x}", noise(), mode=mode, trie=trie, flag=0,
                       value=rs.randrange(1, 1 << 32), old_o=rs.randrange(1, 1 << 32), d68=40.0, r=9)
    for argx in ("zero", "one", "many"):
        for mode in (2, 3, 0):
            yield move(f"tail list {argx} mode {mode:#x}", noise(), mode=mode, argx=argx, d68=40.0, r=9)
    for neg in ((0, 0, 0), (1, 2, 3), (0x80000000, 0x7FFFFFFF, 0x80000000), (-5 & 0xFFFFFFFF, 9, -11 & 0xFFFFFFFF)):
        for mode in (2, 6):
            yield move(f"tail negate {neg} mode {mode}", noise(), mode=mode, neg=neg, flag=0, d68=40.0, r=9)

    # ---- the rand remainder and the ftol conversion ---------------------------------
    rands = (0, 1, 50, 51, 52, 101, 102, 0x7FFE, 0x7FFF, 0x8000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFCE)
    for r in rands:
        for mode in (3, 0):
            d = 120.0 if mode == 3 else 400.0
            yield move(f"rand {r:#x} mode {mode}", noise(), mode=mode, r=r, d68=d, rel="eq")
    doubles = (0.0, -0.0, 1.5, -1.5, -0.75, 99.999, -99.999, 123456.789, 300.25, 2147483647.0, 2147483648.0,
               -2147483649.0, 4294967296.5, 1e10, -1e10, 9.3e18, -9.3e18, 1e19, 1e300, NAN, INF, -INF)
    for d in doubles:
        for mode in (3, 0):
            yield move(f"ftol {d!r} mode {mode}", noise(), mode=mode, d68=d, r=777, rel="eq")

    # ---- tile coordinates: clamps, shifts and sentinel cells -------------------------------
    for ya, yb in ((5, 2), (0, 0), (-1, 0), (-7, 2), (-1, -1), (38, 0), (39, 0), (40, 0), (200, 5), (3, -3),
                   (7, 0), (8, 0), (20, 20), (0x7FFFFFF0, 10)):
        for mode in (3, 0):
            yield move(f"y {ya}+{yb}+1 mode {mode}", noise(), mode=mode, ya=ya, yb=yb, d68=90.0, r=21, rel="eq",
                       script=[0, 2, 0])
    for d in (-900.0, -75.0, 0.0, 10.0, 11.0, 12.0, 13.0, 300.0, 424.0, 425.0, 440.0, 900.0):
        for mode in (3, 0):
            yield move(f"x from {d} mode {mode}", noise(), mode=mode, d68=d, r=0, rel="eq", script=[1, 0],
                       ya=11, yb=4)
    for sent_y in (0xEEEEEEEE, 0xFFFFFFFF, 0xEEEE0001, 0xFFFF0002):
        yield move(f"cell y sentinel {sent_y:#x}", noise(), sent_y=sent_y, script=[1, 0], d68=100.0, r=3, ya=9, yb=2)
    for sent_y1 in (0xEEEEEEEE, 0xFFFFFFFF, 0xEEEE0001):
        for ya, yb in ((9, 2), (8, 2), (60, 0)):
            yield move(f"cell last-row sentinel {sent_y1:#x} y {ya}+{yb}", noise(), sent_y1=sent_y1, script=[1, 0],
                       d68=100.0, r=3, ya=ya, yb=yb)
    for value in (0xEEEEEEEE, 0xFFFFFFFF):
        for mode in (3, 0):
            yield move(f"cell sentinel everywhere mode {mode}", noise(), mode=mode, sent_y=value, sent_y1=value,
                       script=[1, 0], d68=100.0, r=3, ya=9, yb=2)

    # ---- fields a callee changes behind the function's back ---------------------------
    for hook in ("mode_to_2", "mode_from_2", "mode_to_3", "swap_primary", "swap_second", "swap_owner", "swap_arg",
                 "flag_toggle", "mode_to_2_flag_set"):
        for mode in (3, 0, 2):
            for at, script in ((1, [1, 0]), (3, [0, 0, 3, 0])):
                yield move(f"hook {hook} at {at} mode {mode}", noise(), mode=mode, hook=hook, hook_at=at,
                           script=script, flag=0, d68=100.0, r=15)

    # ---- random cases on top ----------------------------------------------------------
    for i in range(70):
        mode = rs.choice((3, 3, 0, 0, 1, 2, 2, 5, rs.randrange(1 << 32)))
        r = rs.choice((rs.randrange(0x8000), rs.randrange(0x8000), rs.randrange(1 << 32)))
        d = rs.choice((rs.uniform(-100, 600), float(rs.randrange(-100, 600)), rs.uniform(-1e11, 1e11)))
        mode_ok = mode == 3
        rel = rs.choice(("gt", "eq", "lt", "eq", "gt", "lt", "nan", "gt_tiny", "lt_tiny"))
        script = [rs.choice((0, 1, 2, 3, 4)) for _ in range(rs.randrange(1, 5))]
        if rs.random() < 0.6:
            script = rs.choice(([1, 0], [0, 2, 0], [0, 0, 3, 0], [2, 2, 0], [3, 1, 3, 0]))
        yield move(f"random {i}", noise(), mode=mode, r=r, d68=d, rel=rel, script=script,
                   ya=rs.randrange(-3, 50), yb=rs.randrange(-3, 12), flag=rs.randrange(1 << 32),
                   pairs=[(rs.choice((sentinel, rs.randrange(1 << 32))), rs.randrange(1 << 32)) for _ in range(3)],
                   argx=rs.choice(("zero", "one", "many")), trie=rs.choice(("hit", "deep", "none", "miss_string")),
                   value=rs.randrange(1, 1 << 32), old_o=rs.randrange(1 << 32),
                   s_ints=(rs.randrange(1 << 32), rs.randrange(1 << 32), rs.randrange(1 << 32), rs.randrange(1 << 32)),
                   neg=(rs.randrange(1 << 32), rs.randrange(1 << 32), rs.randrange(1 << 32)),
                   salt=rs.randrange(100),
                   sent_y=rs.choice((None, None, None, 0xEEEEEEEE, 0xFFFFFFFF)),
                   sent_y1=rs.choice((None, None, None, 0xEEEEEEEE, 0xFFFFFFFF)),
                   hook=rs.choice((None, None, None, "mode_to_2", "swap_second", "flag_toggle")),
                   hook_at=rs.randrange(1, 4))
