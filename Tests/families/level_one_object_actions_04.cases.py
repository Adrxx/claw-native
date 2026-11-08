"""Cases for level_one_object_actions_04: Observed Level 1 level object actions batch 3, treasure and glitter."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

F_46FD10, F_470110, F_4719E0, F_4736B0 = 0x46FD10, 0x470110, 0x4719E0, 0x4736B0
RAND = 0x4A3050
M32 = 0xFFFFFFFF
G_COUNT = 0x52A190       # number of table entries
G_KEYS = 0x537EC8        # object kind keys
G_VALUES = 0x537FD0      # kind values (copied to obj+0xfc)
G_STEP = 0x538310        # words copied to [logic+0x168]
G_FLAGS = 0x5380D8       # words copied to obj+0xd0 when it is 1
G_BUILT = 0x538418       # table already built
G_SCALE = 0x5430C4       # animation step
G_LEVEL_PTR = 0x537960   # pointer to the level number word
G_TICKS = 0x53720C       # tick delta
G_ENV = 0x5371FC         # pointer to an object with a flag at +0x124
SKIP_HANDLER = 0x470100  # logic handler that suppresses the glitter object

NAMES = """CursePowerup AmmoPowerup MagicPowerup TreasurePowerup SpecialPowerup EndOfLevelPowerup PowerupGlitter
HealthPowerup GAME_DYNAMITE GAME_CYCLE100 GAME_MAGICCLAW GAME_MAPPIECE GAME_TREASURE_CHALICES_PURPLE
GAME_TREASURE_CHALICES_BLUE GAME_TREASURE_CHALICES_GREEN GAME_TREASURE_CHALICES_RED GAME_TREASURE_CROSSES_PURPLE
GAME_TREASURE_CROSSES_BLUE GAME_TREASURE_CROSSES_GREEN GAME_TREASURE_CROSSES_RED GAME_TREASURE_SCEPTERS_PURPLE
GAME_TREASURE_SCEPTERS_BLUE GAME_TREASURE_SCEPTERS_GREEN GAME_TREASURE_SCEPTERS_RED GAME_TREASURE_GECKOS_PURPLE
GAME_TREASURE_GECKOS_BLUE GAME_TREASURE_GECKOS_GREEN GAME_TREASURE_GECKOS_RED GAME_TREASURE_COINS GAME_WARP
GAME_POWERUP GAME_GLITTER LEVEL_GEM GAME_POWERUPS_EXTRALIFE GAME_MAGICPOWERUP GAME_VERTWARP GAME_POWERUPS_PLASMASWORD
GAME_POWERUPS_ICESWORD GAME_POWERUPS_LIGHTNINGSWORD GAME_POWERUPS_FIRESWORD GAME_EXTRALIFE GAME_POWERUPS_INVULNERABLE
GAME_POWERUPS_GHOST GAME_TREASURE_JEWELEDSKULL_PURPLE GAME_TREASURE_JEWELEDSKULL_BLUE GAME_TREASURE_JEWELEDSKULL_GREEN
GAME_TREASURE_JEWELEDSKULL_RED GAME_TREASURE_CROWNS_PURPLE GAME_TREASURE_CROWNS_BLUE GAME_TREASURE_CROWNS_GREEN
GAME_TREASURE_CROWNS_RED GAME_CURSES_FREEZE GAME_CURSE1 GAME_CURSES_TREASURE GAME_CURSE4 GAME_CURSES_LIFE GAME_CURSE5
GAME_CURSES_HEALTH GAME_CURSE6 GAME_CURSES_MAGIC GAME_CURSE2 GAME_CURSES_AMMO GAME_CURSE3 GAME_MAGIC_STARGLOW
GAME_MAGIC_GLOW GAME_HEALTH_POTION2 GAME_HEALTH_POTION1 GAME_HEALTH_POTION3 GAME_MILK LEVEL_HEALTH GAME_FOODITEM
GAME_CATNIPS_NIP2 GAME_CATNIPS_NIP1 GAME_CATNMAG GAME_AMMO_SHOTBAG GAME_AMMO_SHOT GAME_AMMO_DEATHBAG GAME_AMMUNITION
GAME_PICKUP2 GAME_SCEPTER GAME_CROSS GAME_TREASURE_NECKLACE GAME_PICKUP1 GAME_TREASURE_RINGS_PURPLE
GAME_TREASURE_RINGS_BLUE GAME_TREASURE_RINGS_GREEN GAME_TREASURE_RINGS_RED GAME_RINGS GAME_TREASURE_GOLDBARS
GAME_TREASURE GAME_COIN GAME_POINTS PointsIcon""".split()
NAMES = [name.encode() for name in NAMES]


def words_of(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def make_registry(env, r, entries, buckets):
    """The string table behind FUN_004f6286, embedded at owner+0x10: +4 buckets, +8 count, nodes [next, ?, key, value].
    Every key also gets a decoy node with a near-miss key so a wrong string compare finds the wrong value."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    table = owner + 0x10
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)
    return owner


def resource(env, r, first, last, frames=None):
    """A frame set: +0xc frame pointers, +0x10 frame count, +0x14 word table, +0x64 first, +0x68 last."""
    count = 16 if frames is None else frames
    table = env.object(4 * 16, "frame-words", words=words_of(r, 16))
    pointers = []
    for _ in range(count):
        pointers.append(env.object(0x40, "frame", words=words_of(r, 0x10)))
    array = env.object(4 * count, "frame-pointers", words=pointers)
    obj = env.object(0x80, "resource", words=words_of(r, 0x20))
    env.put(obj + 0x0C, array, count)
    env.put(obj + 0x14, table)
    env.put(obj + 0x64, first & M32)
    env.put(obj + 0x68, last & M32)
    return obj


def subset(r, names, keep):
    return {name: r.randrange(1, 1 << 32) for name in names if r.random() < keep}


def make_world(env, r, *, keep=1.0, coins=True, glitter=True, glitter_first=2, glitter_last=7, cycle=True,
               powerup=True, glitter_object=False, level=None, buckets=(3, 5, 7)):
    """The level world W. Returns W; sub-objects are recorded in env-independent dictionary W_INFO via tokens."""
    info = {}
    e10 = subset(r, NAMES, keep)
    if coins:
        info["coins"] = resource(env, r, 0, 3)
        e10[b"GAME_TREASURE_COINS"] = info["coins"]
    else:
        e10.pop(b"GAME_TREASURE_COINS", None)
    if glitter:
        info["glitter_set"] = resource(env, r, glitter_first, glitter_last)
        e10[b"GAME_GLITTER"] = info["glitter_set"]
    else:
        e10.pop(b"GAME_GLITTER", None)
    e14 = subset(r, NAMES, keep)
    e28 = subset(r, NAMES, keep)
    e2c = {}
    if cycle:
        info["cycle"] = resource(env, r, 0, 4, frames=r.randrange(1, 5))
        e2c[b"GAME_CYCLE100"] = info["cycle"]
    if powerup:
        info["powerup"] = resource(env, r, 0, 4, frames=r.randrange(1, 5))
        e2c[b"GAME_POWERUP"] = info["powerup"]
    e2c.update({name: r.randrange(1, 1 << 32) for name in NAMES[:6]})
    w2_entries = {b"PointsIcon_": r.randrange(1, 1 << 32)}
    plane = env.object(0x98, "map-plane", words=words_of(r, 0x26))
    tmap = env.object(0x80, "map", words=words_of(r, 0x20))
    env.put(tmap + 0x5C, plane)
    env.put(plane + 0x84, r.randrange(0, 700), r.randrange(0, 700))
    info["plane"] = plane
    if glitter_object:
        # The real actor factory (0x4c8be0) runs, so the scene and its context must look like a live scene.
        w2 = env.object(0x40, "world2", fill=0)
        scene = env.object(0x40, "scene", fill=0)
        pool = env.object(64 * 12, "list-node-pool", fill=0)
        for i in range(63):
            env.put(pool + i * 12, pool + (i + 1) * 12)
        env.put(scene + 0x20, pool)
        env.put(scene + 0x28, 64)
        metadata = env.object(0x18, "actor-metadata", fill=0)
        env.put(metadata + 8, 0x2)
        env.put(metadata + 0x10, env.stub("metadata-notify", "cdecl", 1, returns(0)))
        w2_entries[b"PowerupGlitter"] = metadata
        env.override(0x4F63EC, lambda e, c: e.object(c.arguments[0], "creation-allocation", fill=0xB7))
    else:
        w2 = env.object(0x40, "world2", words=words_of(r, 0x10))
        scene = env.object(0x40, "scene", words=words_of(r, 0x10))
    env.put(w2 + 0x14, make_registry(env, r, w2_entries, r.choice(buckets)))
    env.put(scene + 0x0C, w2)
    world = env.object(0x60, "world", words=words_of(r, 0x18))
    env.put(world + 0x08, scene)
    env.put(world + 0x10, make_registry(env, r, e10, r.choice(buckets)))
    env.put(world + 0x14, make_registry(env, r, e14, r.choice(buckets)))
    env.put(world + 0x24, tmap)
    env.put(world + 0x28, make_registry(env, r, e28, r.choice(buckets)))
    env.put(world + 0x2C, make_registry(env, r, e2c, r.choice(buckets)))
    if level is not None:
        word = env.object(4, "level-word", words=[level & M32])
        env.put(G_LEVEL_PTR, word)
    info["world"] = world
    return world, info


def tables(env, r, count, keys, values=None, steps=None, flags=None):
    """The kind tables in global data."""
    env.put(G_COUNT, count & M32)
    values = values if values is not None else words_of(r, 0x42)
    steps = steps if steps is not None else words_of(r, 0x42)
    flags = flags if flags is not None else words_of(r, 0x42)
    for index in range(0x42):
        env.put(G_KEYS + 4 * index, keys[index] if index < len(keys) else r.randrange(1, 1 << 32))
        env.put(G_VALUES + 4 * index, values[index])
        env.put(G_STEP + 4 * index, steps[index])
        env.put(G_FLAGS + 4 * index, flags[index])


def make_rect(env, r):
    rect = env.object(0x30, "rect", words=words_of(r, 0x0C))
    env.put(rect + 0x18, *[r.randrange(0, 400) for _ in range(4)])
    return rect


def make_logic(env, r, state, handler=None):
    logic = env.object(0x200, "logic", words=words_of(r, 0x80))
    env.put(logic + 0x1C, state & M32)
    if handler is not None:
        env.put(logic + 0x10, handler)
    return logic


def make_animator(env, r, obj, kind):
    """The animation state at obj+0x188. kind: none (+8 == 0), run (+0x14 == 0), tick (no-loop countdown), step."""
    base = obj + 0x188
    if kind == "none":
        env.put(base + 8, 0)
    elif kind == "run":
        env.put(base + 8, r.randrange(1, 1 << 32), 0)
        env.put(base + 0x14, 0)
        env.put(base + 0x1C, r.randrange(1, 1000))
    elif kind == "tick":
        env.put(base + 8, r.randrange(1, 1 << 32))
        env.put(base + 0x14, r.randrange(2, 1000))
        env.put(base + 0x18, 0)
    elif kind == "step":
        env.put(base + 8, r.randrange(1, 1 << 32))
        env.put(base + 0x14, r.randrange(20, 1000))
        env.put(base + 0x18, 1)
    return base


def make_object(env, r, world, logic, **fields):
    obj = env.object(0x1C0, "object", words=words_of(r, 0x70))
    env.put(obj + 0x0C, world)
    env.put(obj + 0x6C, logic)
    for offset, value in fields.items():
        env.put(obj + int(offset[1:], 16), value & M32)
    return obj


# ----------------------------------------------------------------------------------------------
# 0x4719e0 builds the kind tables from the world's string registries
def build_cases(r):
    for keep in (1.0, 1.0, 0.0, 0.5, 0.8, 0.3):
        for level in (0, 1, 0xD, 2, 3, 0xC, 0x1F, 0x20, 0xE, 5):
            def setup(env, keep=keep, level=level):
                world, info = make_world(env, r, keep=keep, level=level)
                tables(env, r, r.randrange(-3, 0x43), words_of(r, 0x42))
                env.put(G_BUILT, r.choice((0, 1, 7)))
                env.put(G_SCALE, r.randrange(1, 1 << 16))
                return {"w": world}
            yield Case(f"tables keep={keep} level={level:#x}", F_4719E0, setup, arguments=(lambda t: t["w"],))
    for buckets in ((1,), (2,), (11,)):
        def setup(env, buckets=buckets):
            world, info = make_world(env, r, keep=1.0, level=r.choice((1, 0xD, 4)), buckets=buckets)
            return {"w": world}
        yield Case(f"tables buckets {buckets[0]}", F_4719E0, setup, arguments=(lambda t: t["w"],))
    for _ in range(12):
        def setup(env):
            world, info = make_world(env, r, keep=r.choice((0.6, 0.9, 1.0)), level=r.randrange(0, 0x40))
            tables(env, r, r.randrange(0, 0x42), words_of(r, 0x42))
            return {"w": world}
        yield Case("tables random", F_4719E0, setup, arguments=(lambda t: t["w"],))


# ----------------------------------------------------------------------------------------------
# 0x4736b0
def kind_setup(r, flag, count, hit, d0, rect, key_zero=False, duplicate=False, prepopulate_world=True):
    def setup(env):
        world, info = make_world(env, r, keep=r.choice((0.7, 1.0)), level=r.choice((1, 4, 0xD)))
        keys = words_of(r, 0x42)
        if duplicate and hit is not None and hit + 1 < 0x42:
            keys[hit + 1] = keys[hit]
        tables(env, r, count, keys)
        env.put(G_BUILT, flag)
        logic = make_logic(env, r, r.randrange(0, 10))
        rect_obj = make_rect(env, r) if rect else 0
        if key_zero:
            key = 0
        elif hit is None:
            key = r.randrange(1, 1 << 32)
        else:
            key = keys[hit]
        obj = make_object(env, r, world, logic, **{"o170": key, "o174": rect_obj, "od0": d0})
        if flag == 0:
            # 0x4719e0 rebuilds the tables, so the key must be one it writes: use an owned kind object.
            pass
        return {"o": obj, "info": info}
    return setup


def kind_cases(r):
    for flag in (1,):
        for count in (0, 1, 2, 5, 0x3E, 0x42, -1, -5):
            for hit in (None, 0, 1, 4, 0x3D):
                if hit is not None and hit >= max(count, 0):
                    continue
                for d0 in (1, 0, 0x7777):
                    for rect in (False, True):
                        yield Case(f"kind flag={flag} count={count} hit={hit} d0={d0:#x} rect={rect}", F_4736B0,
                                   kind_setup(r, flag, count, hit, d0, rect), arguments=(lambda t: t["o"],))
    for count in (3, 8):
        yield Case(f"kind duplicate keys count={count}", F_4736B0,
                   kind_setup(r, 1, count, 1, 1, True, duplicate=True), arguments=(lambda t: t["o"],))
        yield Case(f"kind zero key matches empty slot count={count}", F_4736B0,
                   kind_setup(r, 1, count, None, 1, True, key_zero=True), arguments=(lambda t: t["o"],))
    # table built by 0x4719e0 itself, then searched for a real kind
    for name in (b"GAME_TREASURE_COINS", b"GAME_TREASURE_GOLDBARS", b"GAME_TREASURE_SCEPTERS_GREEN", b"GAME_POWERUPS_GHOST",
                 b"LEVEL_HEALTH", b"NOT_A_KIND_"):
        for flag in (0, 1):
            for d0 in (1, 0x40000, 2):
                def setup(env, name=name, flag=flag, d0=d0):
                    world, info = make_world(env, r, keep=1.0, level=r.choice((1, 4)))
                    kind = info.get("coins", 0)
                    # the registry for the searched name is W+0x10; look the value up through the registry owner
                    owner = env.get(world + 0x10)
                    buckets = env.get(owner + 0x10 + 8)
                    array = env.get(owner + 0x10 + 4)
                    found = 0
                    node = env.get(array + 4 * (key_hash(name) % buckets))
                    while node:
                        if env.cstr(env.get(node + 8)) == name:
                            found = env.get(node + 12)
                            break
                        node = env.get(node)
                    tables(env, r, 0, [])
                    env.put(G_BUILT, flag)
                    if flag == 1:
                        env.put(G_COUNT, 0x3E)
                        for i in range(0x42):
                            env.put(G_KEYS + 4 * i, r.randrange(1, 1 << 32))
                        env.put(G_KEYS + 4 * 9, found or 7)
                    logic = make_logic(env, r, 0)
                    obj = make_object(env, r, world, logic, **{"o170": found or 7, "o174": make_rect(env, r),
                                                               "od0": d0})
                    return {"o": obj}
                yield Case(f"kind via built table {name.decode()} flag={flag} d0={d0:#x}", F_4736B0, setup,
                           arguments=(lambda t: t["o"],))
    for _ in range(25):
        flag = 1
        count = r.randrange(-2, 0x43)
        hit = r.randrange(0, max(count, 1)) if count > 0 and r.random() < 0.7 else None
        yield Case("kind random", F_4736B0,
                   kind_setup(r, flag, count, hit, r.choice((1, 1, 0, r.randrange(2, 1 << 32))), r.random() < 0.6),
                   arguments=(lambda t: t["o"],))


# ----------------------------------------------------------------------------------------------
# 0x470110
def glitter_setup(r, state, *, glitter=True, first=2, last=7, o64=0, o190=0, cycle=True, rand=0, animator="none",
                  scale=3, o8=None):
    def setup(env):
        world, info = make_world(env, r, keep=1.0, glitter=glitter, glitter_first=first, glitter_last=last,
                                 cycle=cycle)
        logic = make_logic(env, r, state)
        obj = make_object(env, r, world, logic, **{"o64": o64, "o190": o190})
        if o8 is not None:
            env.put(obj + 8, o8)
        if o190 == 0:
            env.put(obj + 0x190, 0)
        else:
            make_animator(env, r, obj, "tick" if animator == "none" and state == 0 else animator)
        env.put(G_SCALE, scale)
        env.override(RAND, returns(rand))
        return {"o": obj, "info": info}
    return setup


def glitter_cases(r):
    for glitter, first, last in ((True, 2, 7), (True, 3, 3), (True, 5, 1), (True, 0, 0), (False, 2, 7)):
        for o64 in (0, 0x1234):
            for o190 in (0, 5):
                for cycle in (True, False):
                    for rand in (0, 1, 0xFA, 0xFB, 1000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, r.randrange(0, 1 << 32)):
                        if r.random() < 0.7:
                            continue
                        yield Case(f"glitter init glitter={glitter} {first}-{last} o64={o64:#x} o190={o190} "
                                   f"cycle={cycle} rand={rand:#x}", F_470110,
                                   glitter_setup(r, 0, glitter=glitter, first=first, last=last, o64=o64, o190=o190,
                                                 cycle=cycle, rand=rand, o8=r.randrange(0, 1 << 32)),
                                   arguments=(lambda t: t["o"],))
    # guarantee every combination of the two booleans once per rand class
    for rand in (0xFB, 0xFFFFFFFE, 12345):
        for o64 in (0, 9):
            for o190 in (0, 1):
                yield Case(f"glitter init fixed rand={rand:#x} o64={o64} o190={o190}", F_470110,
                           glitter_setup(r, 0, o64=o64, o190=o190, rand=rand), arguments=(lambda t: t["o"],))
    for animator in ("none", "run", "tick", "step"):
        for scale in (1, 3, 17, 0xFFFF):
            yield Case(f"glitter state 5 animator={animator} scale={scale}", F_470110,
                       glitter_setup(r, 5, o190=5, animator=animator, scale=scale), arguments=(lambda t: t["o"],))
    for state in (1, 2, 4, 6, 9000, 0x1D, 0x2329, 0xFFFFFFFF, 0x80000000, 0x100, 0x3E9):
        yield Case(f"glitter other state {state:#x}", F_470110,
                   glitter_setup(r, state, o190=5, animator="tick"), arguments=(lambda t: t["o"],))
    for _ in range(12):
        yield Case("glitter random", F_470110,
                   glitter_setup(r, r.choice((0, 0, 5, 5, r.randrange(0, 1 << 32))), glitter=r.random() < 0.8,
                                 first=r.randrange(0, 6), last=r.randrange(0, 9), o64=r.choice((0, r.randrange(1, 1 << 32))),
                                 o190=r.choice((0, 0, r.randrange(1, 1 << 32))), cycle=r.random() < 0.8,
                                 rand=r.randrange(0, 1 << 32), animator=r.choice(("none", "run", "tick", "step")),
                                 scale=r.randrange(1, 40)),
                   arguments=(lambda t: t["o"],))


# ----------------------------------------------------------------------------------------------
# 0x46fd10
def treasure_setup(r, state, *, o64=0, o190=0, coins=True, same_coins=True, cycle=True, powerup=True,
                   rect=True, built=1, count=0x3E, hit=3, d0=1, handler=None, env_flag=1, glitter_object=False,
                   animator="none", scale=3, o164=0, ticks=17, o4c=None, o50=None, l130=None, l64=None, l68=None,
                   o8=None, o200=None, glitter_ptr=0, level=None):
    def setup(env):
        world, info = make_world(env, r, keep=1.0, coins=coins, cycle=cycle, powerup=powerup,
                                 glitter_object=glitter_object, level=level if level is not None else r.choice((1, 4, 0xD)))
        keys = words_of(r, 0x42)
        tables(env, r, count, keys)
        env.put(G_BUILT, built)
        logic = make_logic(env, r, state, handler=handler)
        if l130 is not None:
            env.put(logic + 0x130, l130 & M32)
        if l64 is not None:
            env.put(logic + 0x64, l64 & M32)
        if l68 is not None:
            env.put(logic + 0x68, l68 & M32)
        if hit is None:
            kind = r.randrange(1, 1 << 32)
        else:
            kind = keys[hit]
        if state == 0 and coins:
            kind = info["coins"] if same_coins else kind
        rect_obj = make_rect(env, r) if rect else 0
        fields = {"o64": o64, "o174": rect_obj, "o164": o164, "od0": d0, "o170": kind}
        if o4c is not None:
            fields["o4c"] = o4c
        if o50 is not None:
            fields["o50"] = o50
        obj = make_object(env, r, world, logic, **fields)
        if hit is not None and not (state == 0 and coins and same_coins):
            pass
        if state == 0 and coins and same_coins and hit is not None:
            # make the coins resource double as a kind key so the table lookup also hits it
            env.put(G_KEYS + 4 * hit, info["coins"])
        if o8 is not None:
            env.put(obj + 8, o8 & M32)
        if o190 == 0:
            env.put(obj + 0x190, 0)
        else:
            make_animator(env, r, obj, "tick" if animator == "none" and state == 0 else animator)
        glitter = env.object(0x20, "glitter-object", words=words_of(r, 8))
        env.put(obj + 0xC8, glitter if glitter_ptr else 0)
        envobj = env.object(0x140, "environment", words=words_of(r, 0x50))
        env.put(envobj + 0x124, env_flag)
        env.put(G_ENV, envobj)
        env.put(G_SCALE, scale)
        env.put(G_TICKS, ticks & M32)
        return {"o": obj, "info": info, "glitter": glitter}
    return setup


def treasure_cases(r):
    # state 0: every branch of the setup
    for o64 in (0, 777):
        for o190 in (0, 9):
            for coins, same in ((True, True), (True, False), (False, True)):
                for cycle in (True, False):
                    for rect in (True, False):
                        yield Case(f"treasure init o64={o64} o190={o190} coins={coins} same={same} cycle={cycle} "
                                   f"rect={rect}", F_46FD10,
                                   treasure_setup(r, 0, o64=o64, o190=o190, coins=coins, same_coins=same, cycle=cycle,
                                                  powerup=r.random() < 0.7, rect=rect, hit=r.choice((0, 2, 5, None)),
                                                  d0=r.choice((1, 0x40000, 5)), glitter_ptr=r.randrange(0, 2),
                                                  o8=r.randrange(0, 1 << 32), handler=r.choice((None, SKIP_HANDLER))),
                                   arguments=(lambda t: t["o"],))
    for built in (0, 1):
        for hit in (None, 0, 1, 7):
            for d0 in (1, 0x40000):
                for count in (0x3E, 0, 3):
                    yield Case(f"treasure init built={built} hit={hit} d0={d0:#x} count={count}", F_46FD10,
                               treasure_setup(r, 0, built=built, hit=hit, d0=d0, count=count, o190=3, rect=True),
                               arguments=(lambda t: t["o"],))
    # the glitter object: the environment flag and the skip handler decide whether it is created
    for handler in (None, SKIP_HANDLER):
        for env_flag in (0, 1, 0xFFFF):
            for glitter_object in (False, True):
                yield Case(f"treasure init glitter handler={handler} env={env_flag} found={glitter_object}", F_46FD10,
                           treasure_setup(r, 0, handler=handler, env_flag=env_flag, glitter_object=glitter_object,
                                          o190=3, glitter_ptr=1),
                           arguments=(lambda t: t["o"],))
    # state 5
    for o164 in (0, 0x200, 0x1FF, 0x201, 0xFFFFFDFF, 0x100, 0xFFFFFFFF):
        for animator in ("none", "run", "tick", "step"):
            yield Case(f"treasure state 5 o164={o164:#x} animator={animator}", F_46FD10,
                       treasure_setup(r, 5, o164=o164, o190=1, animator=animator, scale=r.randrange(1, 30)),
                       arguments=(lambda t: t["o"],))
    # states that do nothing and the 0x1d release
    for state in (1, 2, 3, 4, 6, 7, 8, 0x1C, 0x1E, 0x100, 8999, 9001, 0x2328, 0x232A, 0xFFFFFFFF, 0x80000000):
        yield Case(f"treasure idle state {state:#x}", F_46FD10,
                   treasure_setup(r, state, o190=1, animator="tick", glitter_ptr=1), arguments=(lambda t: t["o"],))
    for glitter_ptr in (0, 1):
        for o8 in (0, 0x10000, 0xFFFFFFFF, 0x12345678):
            yield Case(f"treasure release glitter ptr={glitter_ptr} o8={o8:#x}", F_46FD10,
                       treasure_setup(r, 0x1D, o190=1, animator="tick", glitter_ptr=glitter_ptr, o8=o8),
                       arguments=(lambda t: t["o"],))
    # state 9000: fly-away setup, with and without a glitter object to release
    for glitter_ptr in (0, 1):
        for o4c, o50 in ((0, 0), (1, 1), (300, 280), (299, 273), (-50 & M32, 100), (5000, -5000 & M32),
                         (r.randrange(0, 2000), r.randrange(0, 2000))):
            yield Case(f"treasure fly-away glitter={glitter_ptr} pos=({o4c:#x},{o50:#x})", F_46FD10,
                       treasure_setup(r, 9000, o190=1, animator="tick", glitter_ptr=glitter_ptr, o4c=o4c, o50=o50,
                                      o8=r.randrange(0, 1 << 32)),
                       arguments=(lambda t: t["o"],))
    # state 0x2329: the fly-away countdown
    for ticks in (0, 1, 16, 17, 400, 401, 1000, 0xFFFFFFF0):
        for l130 in (0, 1, 16, 17, 18, 400):
            for l64, l68 in ((0, 0), (1000, 0), (0, 2000), (500, -700 & M32), (-1000 & M32, 3500)):
                if r.random() < 0.75:
                    continue
                yield Case(f"treasure flying ticks={ticks:#x} l130={l130} l64={l64:#x} l68={l68:#x}", F_46FD10,
                           treasure_setup(r, 0x2329, o190=1, animator="tick", ticks=ticks, l130=l130, l64=l64, l68=l68,
                                          o4c=r.randrange(0, 2000), o50=r.randrange(0, 2000),
                                          o8=r.randrange(0, 1 << 32)),
                           arguments=(lambda t: t["o"],))
    for _ in range(10):
        yield Case("treasure flying equal ticks", F_46FD10,
                   treasure_setup(r, 0x2329, o190=1, animator="step", ticks=r.randrange(1, 500), l130=500,
                                  l64=r.randrange(1, 1 << 31), l68=r.randrange(1, 1 << 31),
                                  o4c=r.randrange(0, 2000), o50=r.randrange(0, 2000), scale=r.randrange(1, 10)),
                   arguments=(lambda t: t["o"],))
    for _ in range(15):
        state = r.choice((0, 0, 5, 0x1D, 9000, 0x2329, r.randrange(0, 1 << 32)))
        yield Case("treasure random", F_46FD10,
                   treasure_setup(r, state, o64=r.choice((0, r.randrange(1, 1 << 32))), o190=r.choice((0, 4)),
                                  coins=r.random() < 0.8, same_coins=r.random() < 0.5, cycle=r.random() < 0.8,
                                  rect=r.random() < 0.8, built=r.randrange(0, 2), count=r.randrange(0, 0x43),
                                  hit=r.choice((None, 0, 3, 9)), d0=r.choice((1, 0x40000, 3)),
                                  handler=r.choice((None, SKIP_HANDLER)), env_flag=r.choice((0, 1)),
                                  animator=r.choice(("none", "run", "tick", "step")), scale=r.randrange(1, 30),
                                  o164=r.choice((0, 0x200, r.randrange(0, 1 << 32))), ticks=r.randrange(0, 1000),
                                  o4c=r.randrange(0, 2000), o50=r.randrange(0, 2000), l130=r.randrange(0, 600),
                                  l64=r.randrange(0, 1 << 32), l68=r.randrange(0, 1 << 32),
                                  glitter_ptr=r.randrange(0, 2), o8=r.randrange(0, 1 << 32)),
                   arguments=(lambda t: t["o"],))


def cases(random_source):
    r = random_source
    yield from build_cases(r)
    yield from kind_cases(r)
    yield from glitter_cases(r)
    yield from treasure_cases(r)
