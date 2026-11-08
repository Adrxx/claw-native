"""Cases for level_one_collision_dispatch_03 (actor collision probes).

Every branch is reached by hand-built or deterministic-grid cases; random_source only adds cases.
"""
from clawparity.cases import Case

F_CC2B0 = 0x4CC2B0
F_CCDD0 = 0x4CCDD0
F_CCF80 = 0x4CCF80
F_CD060 = 0x4CD060
F_CD120 = 0x4CD120

EMPTY = 0xEEEEEEEE
NONE = 0xFFFFFFFF
NKINDS = 8


def pattern_words(count, salt):
    """Distinct small positive filler so unread fields differ."""
    return [((i * 13 + salt * 7 + 5) & 0x7F) + 1 for i in range(count)]


def default_rv(kind, lx, ly):
    return kind


def world(env, grid, cols, rows, sx=0, sy=0, wp=None, hp=None, rv=None, sx_junk=0, sy_junk=0):
    """Tile manager, tile objects (virtual +0x20 stubs) and a receiver `this`."""
    rv = rv or default_rv
    wp = (cols << sx) if wp is None else wp
    hp = (rows << sy) if hp is None else hp
    stride = cols + 3
    base = 2
    data = [EMPTY] * (rows * stride + 6)
    for iy in range(rows):
        for ix in range(cols):
            tile = grid(ix, iy)
            if tile is None:
                word = EMPTY
            elif tile == "F":
                word = NONE
            else:
                junk = ((ix * 31 + iy * 17 + 3) & 0x7FFF) << 16
                word = (tile & 0xFFFF) | junk
            data[iy * stride + base + ix] = word
    tiles = env.object(len(data) * 4, "tile-data", words=data)
    rowoff = env.object(rows * 4, "tile-rows", words=[iy * stride + base for iy in range(rows)])
    objects = []
    for kind in range(NKINDS):
        def effect(env, call, kind=kind):
            return rv(kind, call.arguments[0], call.arguments[1]) & 0xFFFFFFFF

        stub = env.stub(f"tile-{kind}", "thiscall", 2, effect)
        vtable = env.object(0x44, f"vtable-{kind}", words=pattern_words(17, kind))
        env.put(vtable + 0x20, stub)
        obj = env.object(16, f"tile-object-{kind}", words=[vtable, 5 + 3 * kind, 0x77 + kind, 0x99 + kind])
        objects.append(obj)
    objlist = env.object(4 * NKINDS, "tile-objects", words=objects)
    manager = env.object(0x98, "tile-manager", words=pattern_words(38, 3))
    env.put(manager + 0x20, tiles)
    env.put(manager + 0x24, rowoff)
    env.put(manager + 0x30, wp)
    env.put(manager + 0x34, hp)
    env.put(manager + 0x8C, 0x300 + sx + sx_junk)
    env.put(manager + 0x90, 0x500 + sy + sy_junk)
    this = env.object(0x70, "this", words=pattern_words(28, 5))
    env.put(this + 0x4C, objlist)
    env.put(this + 0x5C, manager)
    return {"this": this, "manager": manager, "objlist": objlist, "objects": objects}


def actor(env, name="actor", salt=1, **fields):
    obj = env.object(0x170, name, words=pattern_words(0x170 // 4, salt))
    for key, value in fields.items():
        env.put(obj + int(key[1:], 16), value & 0xFFFFFFFF)
    return obj


def out_word(env, name="out", value=0xA5A5A5A5):
    return env.object(4, name, words=[value])


# ---------------------------------------------------------------- grids

def g_mixed(ix, iy):
    h = (ix * 5 + iy * 3 + ix * iy) % 11
    if h == 0:
        return None
    if h == 1:
        return "F"
    return h % NKINDS


def g_bands(ix, iy):
    if ix == 20:
        return "F"
    if iy < 4:
        return 2
    if iy < 12:
        return 3
    if iy < 16:
        return 5
    if iy < 20:
        return 3
    return None


# ---------------------------------------------------------------- 0x4cd120

def cd120_case(label, x, y, cols, rows, sx, sy, wp=None, hp=None, sxj=0, syj=0):
    def setup(env):
        t = world(env, g_mixed, cols, rows, sx, sy, wp, hp, sx_junk=sxj, sy_junk=syj)
        t["o1"] = out_word(env, "out1", 0x11111111)
        t["o2"] = out_word(env, "out2", 0x22222222)
        return t
    return Case(label, F_CD120, setup, receiver=lambda t: t["this"],
                arguments=(x, y, lambda t: t["o1"], lambda t: t["o2"]))


# ---------------------------------------------------------------- 0x4ccdd0

def ccdd0_case(label, grid, x, b, c, cols=24, rows=24, rv=None, sx=0, sy=0):
    def setup(env):
        t = world(env, grid, cols, rows, sx, sy, rv=rv)
        t["out"] = out_word(env)
        return t
    return Case(label, F_CCDD0, setup, receiver=lambda t: t["this"],
                arguments=(x, b, c, lambda t: t["out"]))


def g_col(ix, iy):
    # column pattern per x: 3-runs interrupted by other kinds
    if ix == 3:
        return 3
    if ix == 4:
        return 3 if iy % 5 else 6
    if ix == 5:
        return 7 if iy in (1, 2, 11) else 3
    if ix == 6:
        return None
    if ix == 7:
        return "F"
    return 3 if iy % 4 else 1


# ---------------------------------------------------------------- 0x4ccf80 / 0x4cd060

A_BASE = dict(a50=10, a124=7, a118=4, a120=30, p3=100, p4=20,
              b128=20, b4c=50, b130=61, b12c=9, b50=14, b15c=-5)


def tight(base, kind):
    c = dict(base)
    if kind == "u":
        pass
    elif kind == "e":
        c["p4"] = c["a50"]
        c["b12c"] = 4  # iVar3 = 18 = iVar4 + 1
    elif kind == "t1":  # iVar2 == iVar3 - iVar1
        c["b50"] = c["a124"] + c["a50"] - c["b12c"] + c["b15c"]
    elif kind == "t2":
        c["b128"] = c["a120"] + c["p3"] - c["b4c"]
    elif kind == "t3":
        c["b130"] = c["a118"] + c["p3"] - c["b4c"]
    elif kind == "t4":  # iVar4 == iVar3 - 1, unequal path
        c["p4"] = c["b12c"] + c["b50"] - 1 - c["a124"]
    elif kind == "t5":  # positive b15c, clamped to 0
        c["b15c"] = 6
        c["b50"] = c["a124"] + c["a50"] - c["b12c"]
    elif kind == "t6":  # b15c zero
        c["b15c"] = 0
    elif kind == "t7":  # p4 at the a50 boundary
        c["p4"] = c["a50"] + 1
    return c


def ccf80_case(label, cfg, sentinel=None):
    def setup(env):
        a = actor(env, "first", 2, **{"f50": cfg["a50"], "f124": cfg["a124"], "f118": cfg["a118"], "f120": cfg["a120"]})
        b = actor(env, "second", 3, **{"f128": cfg["b128"], "f4c": cfg["b4c"], "f130": cfg["b130"],
                                       "f12c": cfg["b12c"], "f50": cfg["b50"], "f15c": cfg["b15c"]})
        if sentinel:
            env.put(a + 0x118, sentinel[0] & 0xFFFFFFFF)
        return {"a": a, "b": b, "out": out_word(env)}
    return Case(label, F_CCF80, setup, receiver=0,
                arguments=(lambda t: t["a"], lambda t: t["b"], cfg["p3"], cfg["p4"] & 0xFFFFFFFF,
                           lambda t: t["out"], 0x5AC0FFEE))


def fix_f(cfg):
    return cfg


def ccf80_cases():
    seen = set()
    fields = ("a50", "a124", "a118", "a120", "p3", "p4", "b128", "b4c", "b130", "b12c", "b50", "b15c")
    for kind in ("u", "e", "t1", "t2", "t3", "t4", "t5", "t6", "t7"):
        base = tight(A_BASE, kind)
        variants = [("base", base)]
        for field in (fields if kind in ("u", "e", "t1", "t2", "t3", "t4") else ("p4", "b15c", "b50")):
            for delta in (-1, 1):
                v = dict(base)
                v[field] += delta
                variants.append((f"{field}{delta:+d}", v))
        for name, cfg in variants:
            key = tuple(sorted(cfg.items()))
            if key in seen:
                continue
            seen.add(key)
            yield ccf80_case(f"ccf80 {kind} {name}", cfg)
    # sentinels
    yield Case("ccf80 b128 == -1", F_CCF80, lambda env: _ccf80_sentinel(env, "b"), receiver=0,
               arguments=(lambda t: t["a"], lambda t: t["b"], 100, 20, lambda t: t["out"], 0x5AC0FFEE))
    yield Case("ccf80 a118 == -1", F_CCF80, lambda env: _ccf80_sentinel(env, "a"), receiver=0,
               arguments=(lambda t: t["a"], lambda t: t["b"], 100, 20, lambda t: t["out"], 0x5AC0FFEE))
    # p4 less than a50 (first gate)
    yield ccf80_case("ccf80 p4 below a50", dict(A_BASE, p4=A_BASE["a50"] - 1))
    yield ccf80_case("ccf80 p4 far below a50", dict(A_BASE, p4=-30))
    yield ccf80_case("ccf80 negative coordinates", dict(A_BASE, a50=-20, p4=-12, b50=-10, b12c=-3, b4c=-40, b128=-70, b130=15, p3=-20))


def _ccf80_sentinel(env, which):
    cfg = A_BASE
    a = actor(env, "first", 2, f50=cfg["a50"], f124=cfg["a124"], f118=cfg["a118"], f120=cfg["a120"])
    b = actor(env, "second", 3, f128=cfg["b128"], f4c=cfg["b4c"], f130=cfg["b130"],
              f12c=cfg["b12c"], f50=cfg["b50"], f15c=cfg["b15c"])
    if which == "b":
        env.put(b + 0x128, 0xFFFFFFFF)
    else:
        env.put(a + 0x118, 0xFFFFFFFF)
    return {"a": a, "b": b, "out": out_word(env)}


D_BASE = dict(a118=4, a120=30, a124=7, p3=100, p4=15,
              b128=20, b4c=50, b130=61, b12c=9, b50=14, bd0=0x80, p5=8)


def cd060_case(label, cfg, null_p2=False, a118_raw=None, b128_raw=None):
    def setup(env):
        a = actor(env, "first", 4, f118=cfg["a118"], f120=cfg["a120"], f124=cfg["a124"])
        b = actor(env, "second", 5, f128=cfg["b128"], f4c=cfg["b4c"], f130=cfg["b130"], f12c=cfg["b12c"],
                  f50=cfg["b50"], fd0=cfg["bd0"])
        if a118_raw is not None:
            env.put(a + 0x118, a118_raw)
        if b128_raw is not None:
            env.put(b + 0x128, b128_raw)
        return {"a": a, "b": 0 if null_p2 else b}
    return Case(label, F_CD060, setup, receiver=0,
                arguments=(lambda t: t["a"], lambda t: t["b"], cfg["p3"], cfg["p4"] & 0xFFFFFFFF, cfg["p5"]))


def cd060_cases():
    seen = set()
    fields = ("a118", "a120", "a124", "p3", "p4", "b128", "b4c", "b130", "b12c", "b50", "bd0")
    bases = [("base", D_BASE)]
    t2 = dict(D_BASE, b128=D_BASE["a120"] + D_BASE["p3"] - D_BASE["b4c"])
    t3 = dict(D_BASE, b130=D_BASE["a118"] + D_BASE["p3"] - D_BASE["b4c"])
    bases += [("t2", t2), ("t3", t3)]
    for bname, base in bases:
        variants = [("same", base)]
        for field in fields:
            for delta in (-1, 1):
                v = dict(base)
                v[field] += delta
                variants.append((f"{field}{delta:+d}", v))
        for name, cfg in variants:
            key = tuple(sorted(cfg.items()))
            if key in seen:
                continue
            seen.add(key)
            yield cd060_case(f"cd060 {bname} {name}", cfg)
    for p5 in (0, 1, 7, 8, 9, 0x10, 0xF7, 0xFF, 0x100, 0x108, 0x1F8, 0xFFFFFF00, 0xFFFFFFF8):
        yield cd060_case(f"cd060 p5={p5:#x}", dict(D_BASE, p5=p5))
    yield cd060_case("cd060 null second", D_BASE, null_p2=True)
    yield cd060_case("cd060 b128 -1", D_BASE, b128_raw=0xFFFFFFFF)
    yield cd060_case("cd060 a118 -1", D_BASE, a118_raw=0xFFFFFFFF)
    yield cd060_case("cd060 d0 0x80 plus high bit", dict(D_BASE, bd0=0x80 | 0x100))
    yield cd060_case("cd060 negative geometry", dict(D_BASE, a118=-9, a120=-2, a124=-4, p3=-40, p4=-30,
                                                      b128=-70, b4c=-15, b130=-30, b12c=-20, b50=-9))


# ---------------------------------------------------------------- 0x4cc2b0

BOXES = [
    dict(f118=-4, f120=4, f11c=-8, f124=6, fdc=2, fe0=3),
    dict(f118=-1, f120=2, f11c=-3, f124=2, fdc=1, fe0=1),
    dict(f118=2, f120=5, f11c=-9, f124=3, fdc=5, fe0=4),
]


def g_floor(ix, iy):
    if iy < 20:
        return 3
    if iy < 22:
        return 2
    if iy < 30:
        return 1
    if iy < 32:
        return 4
    return 3


def g_ceiling(ix, iy):
    if iy < 10:
        return 1
    if ix >= 24 and iy < 30:
        return 3
    if iy == 25:
        return 2
    return 3


def g_walls(ix, iy):
    if 16 <= ix <= 18:
        return 1
    if 28 <= ix <= 29:
        return 2
    if iy >= 40:
        return 1
    return 3


def g_all3(ix, iy):
    return 3


def g_empty(ix, iy):
    return None


def g_mix2(ix, iy):
    h = (ix * 7 + iy * 5 + (ix ^ iy)) % 13
    return (None, "F", 0, 1, 2, 3, 3, 3, 4, 5, 1, 2, 3)[h]


def g_steps(ix, iy):
    # stair of solids: height shrinks as ix grows
    top = 36 - (ix // 4) * 3
    if iy >= top:
        return 1
    if iy == top - 1:
        return 2
    if iy == top - 2:
        return 4
    return 3


def g_pits(ix, iy):
    if iy >= 30:
        return 3 if 10 <= ix <= 14 or 33 <= ix <= 35 else 1
    if iy == 12 and ix % 3 == 0:
        return 1
    return 3


def g_rain(ix, iy):
    h = (ix * 3 + iy * 11) % 7
    return (3, 3, 1, 3, 2, 3, 6)[h]


GRIDS = [g_floor, g_ceiling, g_walls, g_all3, g_empty, g_mix2, g_steps, g_pits, g_rain]

POSITIONS = [(10, 14), (22, 19), (30, 27), (20, 40), (12, 29), (35, 20), (8, 35), (26, 11)]


def cc2b0_case(label, grid, box, pos, target, cc, cols=48, rows=48, sx=0, sy=0, rv=None, flags=0x1000):
    def setup(env):
        t = world(env, grid, cols, rows, sx, sy, rv=rv)
        t["actor"] = actor(env, "actor", 6, f4c=pos[0], f50=pos[1], fcc=cc, f8=flags, fd0=0x80, **box)
        return t
    return Case(label, F_CC2B0, setup, receiver=lambda t: t["this"],
                arguments=(lambda t: t["actor"], target[0], target[1] & 0xFFFFFFFF, 0x13572468))


def cc2b0_cases():
    ccs = (0, 1, 6, 4, 2)
    n = 0
    for gi, grid in enumerate(GRIDS):
        for dy in (-9, -1, 0, 1, 9):
            for dx in (-6, 0, 6):
                pos = POSITIONS[(n + gi) % len(POSITIONS)]
                box = BOXES[(n // 2) % len(BOXES)]
                cc = ccs[(n * 3 + gi) % len(ccs)]
                target = (pos[0] + dx, pos[1] + dy)
                yield cc2b0_case(f"cc2b0 {grid.__name__} dy{dy} dx{dx} cc{cc}", grid, box, pos, target, cc)
                n += 1
    # every initial cc against the interesting grids and each branch direction
    for grid in (g_floor, g_pits):
        for cc in ccs:
            for dy in (-7, 6):
                pos = POSITIONS[(cc + dy) % len(POSITIONS)]
                yield cc2b0_case(f"cc2b0 {grid.__name__} cc{cc} dy{dy} same x", grid, BOXES[0], pos,
                                 (pos[0], pos[1] + dy), cc)
    # shifted tile grids and position clamping
    for sx, sy in ((2, 1), (1, 3), (3, 2)):
        for dy, dx in ((-5, 5), (6, -4), (0, 0), (4, 4)):
            pos = POSITIONS[(sx + sy + dy) % len(POSITIONS)]
            yield cc2b0_case(f"cc2b0 shifts {sx},{sy} dy{dy} dx{dx}", g_mix2, BOXES[1], (pos[0] // 2, pos[1] // 2),
                             (pos[0] // 2 + dx, pos[1] // 2 + dy), 0, cols=24, rows=24, sx=sx, sy=sy)
    # edges: clamped negative and beyond the map
    for pos, target in (((2, 3), (-4, -9)), ((45, 44), (60, 70)), ((2, 44), (-3, 60)), ((45, 2), (80, -30)),
                        ((0, 0), (0, 0)), ((3, 46), (3, 47)), ((46, 10), (47, 9))):
        for grid in (g_floor, g_all3, g_mix2):
            yield cc2b0_case(f"cc2b0 edge {grid.__name__} {pos}->{target}", grid, BOXES[1], pos, target, 0)
    # flag bit 0x400000 interplay and distinct return paths with a tile that returns 4
    def rv4(kind, lx, ly):
        return 4 if kind in (4, 5) else kind
    for pos, target in (((10, 14), (10, 24)), ((22, 19), (22, 30)), ((30, 27), (36, 27)), ((30, 27), (24, 27))):
        yield cc2b0_case(f"cc2b0 rv4 {pos}->{target}", g_floor, BOXES[0], pos, target, 0, rv=rv4)


# ---------------------------------------------------------------- the generator

def cases(random_source):
    # 0x4cd120 sweeps
    for x in (-4, 3, 10, 23, 24, 60):
        for y in (-3, 5, 12, 23, 24, 50):
            yield cd120_case(f"cd120 flat x{x} y{y}", x, y, 24, 24, 0, 0)
    for x in (-2, 5, 11, 29, 30, 77):
        for y in (-2, 3, 9, 20, 21, 55):
            yield cd120_case(f"cd120 shifted x{x} y{y}", x, y, 8, 11, 2, 1, wp=30, hp=21, sxj=0x20, syj=0x40)

    # 0x4ccdd0
    xs = (-9, 3, 4, 5, 6, 7, 40)
    spans = ((14, 2), (12, 2), (12, 4), (20, 16), (-3, -10), (40, 6), (5, 5), (4, 9), (13, 12))
    for x in xs:
        for b, c in spans:
            grid = g_col
            yield ccdd0_case(f"ccdd0 x{x} b{b} c{c}", grid, x, b, c)
    for x in (2, 5, 24, 20):
        for b, c in ((12, 2), (22, 14), (16, 1)):
            yield ccdd0_case(f"ccdd0 bands x{x} b{b} c{c}", g_bands, x, b, c)
    yield ccdd0_case("ccdd0 shifted grid", g_mix2, 9, 20, 3, cols=12, rows=8, sx=2, sy=2)
    yield ccdd0_case("ccdd0 all 3 returns 0", g_all3, 6, 15, 2)
    yield ccdd0_case("ccdd0 negative-to-clamp", g_col, 3, 2, -40)
    yield ccdd0_case("ccdd0 stub returns 3 only at one row", g_col, 4, 13, 8,
                     rv=lambda k, lx, ly: 3 if ly == 0 else k)

    # 0x4ccf80, 0x4cd060
    yield from ccf80_cases()
    yield from cd060_cases()

    # 0x4cc2b0
    yield from cc2b0_cases()

    # random additions
    for i in range(25):
        seed = random_source.randrange(1, 1 << 30)
        cols = rows = 48
        kinds = [random_source.choice((None, "F", 0, 1, 1, 2, 3, 3, 3, 4, 5)) for _ in range(64)]
        grid = (lambda s, ks: (lambda ix, iy: ks[((ix * 31 + iy * 17) ^ (ix * iy) ^ s) % 64]))(seed, kinds)
        box = dict(f118=random_source.randrange(-6, 2), f120=random_source.randrange(2, 7),
                   f11c=random_source.randrange(-10, -1), f124=random_source.randrange(1, 8),
                   fdc=random_source.randrange(1, 6), fe0=random_source.randrange(1, 6))
        pos = (random_source.randrange(-3, 52), random_source.randrange(-3, 52))
        target = (pos[0] + random_source.randrange(-9, 10), pos[1] + random_source.randrange(-12, 13))
        cc = random_source.choice((0, 1, 2, 4, 6))
        yield cc2b0_case(f"random cc2b0 {i}", grid, box, pos, target, cc)
    for i in range(10):
        cfg = dict(A_BASE)
        for key in cfg:
            cfg[key] += random_source.randrange(-12, 13)
        yield ccf80_case(f"random ccf80 {i}", cfg)
    for i in range(10):
        cfg = dict(D_BASE)
        for key in cfg:
            if key not in ("bd0", "p5"):
                cfg[key] += random_source.randrange(-12, 13)
        cfg["p5"] = random_source.randrange(0, 256)
        yield cd060_case(f"random cd060 {i}", cfg)
    for i in range(10):
        yield cd120_case_random(random_source, i)


def cd120_case_random(random_source, i):
    sx, sy = random_source.randrange(0, 4), random_source.randrange(0, 4)
    cols, rows = random_source.randrange(3, 14), random_source.randrange(3, 14)
    return cd120_case(f"random cd120 {i}", random_source.randrange(-5, (cols << sx) + 6),
                      random_source.randrange(-5, (rows << sy) + 6), cols, rows, sx, sy)
