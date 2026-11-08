"""Cases for level_one_batch_powerups_01: Level 1 powerup pickups: special, curse, health, ammo, glitterless."""
import random

from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

M32 = 0xFFFFFFFF
SPECIAL, CURSE, WRAPPER, HEALTH, AMMO = 0x470430, 0x470A20, 0x470100, 0x470D00, 0x471100
NEW = 0x4F63EC

G_APP, G_TICK, G_CURSOR, G_COUNT = 0x5371FC, 0x53720C, 0x5430C4, 0x52A190
G_SKIP_INIT, G_CURSE_FLAG = 0x538418, 0x52550C
T_KEYS, T_VALUES, T_FLAGS, T_TYPES = 0x537EC8, 0x537FD0, 0x5380D8, 0x538310
TABLE_WORDS = 66
LEVEL_INFO = 0x537960

# Names that the table initializer 0x4719e0 looks up, by registry.
NAMES_R10 = [
    "GAME_TREASURE_COINS", "GAME_TREASURE_GOLDBARS", "GAME_TREASURE_RINGS_RED", "GAME_TREASURE_RINGS_GREEN",
    "GAME_TREASURE_RINGS_BLUE", "GAME_TREASURE_RINGS_PURPLE", "GAME_TREASURE_NECKLACE", "GAME_TREASURE_CROSSES_RED",
    "GAME_TREASURE_CROSSES_GREEN", "GAME_TREASURE_CROSSES_BLUE", "GAME_TREASURE_CROSSES_PURPLE",
    "GAME_TREASURE_SCEPTERS_RED", "GAME_TREASURE_SCEPTERS_GREEN", "GAME_TREASURE_SCEPTERS_BLUE",
    "GAME_TREASURE_SCEPTERS_PURPLE", "GAME_TREASURE_GECKOS_RED", "GAME_TREASURE_GECKOS_GREEN",
    "GAME_TREASURE_GECKOS_BLUE", "GAME_TREASURE_GECKOS_PURPLE", "GAME_AMMO_DEATHBAG", "GAME_AMMO_SHOT",
    "GAME_AMMO_SHOTBAG", "GAME_CATNIPS_NIP1", "GAME_CATNIPS_NIP2", "LEVEL_HEALTH", "GAME_HEALTH_POTION3",
    "GAME_HEALTH_POTION1", "GAME_HEALTH_POTION2", "GAME_MAGIC_GLOW", "GAME_MAGIC_STARGLOW", "GAME_MAGICCLAW",
    "LEVEL_GEM", "GAME_MAPPIECE", "GAME_WARP", "GAME_DYNAMITE", "GAME_CURSES_AMMO", "GAME_CURSES_MAGIC",
    "GAME_CURSES_HEALTH", "GAME_CURSES_LIFE", "GAME_CURSES_TREASURE", "GAME_CURSES_FREEZE",
    "GAME_TREASURE_CHALICES_RED", "GAME_TREASURE_CHALICES_GREEN", "GAME_TREASURE_CHALICES_BLUE",
    "GAME_TREASURE_CHALICES_PURPLE", "GAME_TREASURE_CROWNS_RED", "GAME_TREASURE_CROWNS_GREEN",
    "GAME_TREASURE_CROWNS_BLUE", "GAME_TREASURE_CROWNS_PURPLE", "GAME_TREASURE_JEWELEDSKULL_RED",
    "GAME_TREASURE_JEWELEDSKULL_GREEN", "GAME_TREASURE_JEWELEDSKULL_BLUE", "GAME_TREASURE_JEWELEDSKULL_PURPLE",
    "GAME_POWERUPS_GHOST", "GAME_POWERUPS_INVULNERABLE", "GAME_POWERUPS_EXTRALIFE", "GAME_POWERUPS_FIRESWORD",
    "GAME_POWERUPS_LIGHTNINGSWORD", "GAME_POWERUPS_ICESWORD", "GAME_POWERUPS_PLASMASWORD", "GAME_VERTWARP",
]
NAMES_R14 = ["TreasurePowerup", "AmmoPowerup", "HealthPowerup", "MagicPowerup", "EndOfLevelPowerup",
             "SpecialPowerup", "CursePowerup"]
NAMES_R28 = ["GAME_COIN", "GAME_TREASURE", "GAME_RINGS", "GAME_PICKUP1", "GAME_CROSS", "GAME_SCEPTER", "GAME_PICKUP2",
             "GAME_AMMUNITION", "GAME_CATNMAG", "GAME_FOODITEM", "GAME_MILK", "GAME_MAGICPOWERUP", "GAME_CURSE3",
             "GAME_CURSE2", "GAME_CURSE6", "GAME_CURSE5", "GAME_CURSE4", "GAME_CURSE1", "GAME_EXTRALIFE"]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def small(r, lo=-3000, hi=3000):
    return r.randrange(lo, hi) & M32


def registry(env, r, entries, buckets):
    """A string table as 0x4f6286 reads it, embedded at owner+0x10. Nodes: [next, 0, key, value], with decoys."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    table = owner + 0x10
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        raw = name.encode()
        key = env.object(len(raw) + 4, "registry-key", data=raw + b"\0")
        decoy_key = env.object(len(raw) + 8, "decoy-key", data=raw + b"X\0")
        index = key_hash(raw) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)
    return owner


def animation(env, r):
    """An animation record as 0x4c8220 reads it: +0xc frame array, +0x10 count (at least one)."""
    frame = env.object(0x40, "frame", words=words_of(r, 16))
    frames = env.object(8, "frames", words=[frame, frame])
    return env.object(0x40, "animation", words=[*words_of(r, 3), frames, r.randrange(1, 4), *words_of(r, 11)])


BASE = dict(
    state=0, handler=0xDEAD0000, mode=(3,), a124=1, skip=1, count=40, key="plain", found_at=7,
    coins_reg=True, warp_reg=True, dyn_reg=True, life_reg=True, glitter_reg=True, cycle_reg=True, powerup_reg=True,
    z=0, anim="none", rect=True, gl=False, nodes=(), free_node=True, tick=17, cursor=3, lo=0, s130=500, s64=0, s68=0,
    flags200=False, curse_flag=1, list16c=None, buckets=7, full=False, level_word=2)


def spec(**changes):
    unknown = set(changes) - set(BASE)
    assert not unknown, unknown
    return {**BASE, **changes}


def world(o, seed):
    """setup(env) for one option set."""

    def setup(env):
        r = random.Random(seed)
        env.override(NEW, lambda env, call: env.object(call.arguments[0], name="allocation", fill=0xB7))
        full = o["full"]

        # ---- registries
        ids = {name: r.randrange(1, 1 << 32) for name in NAMES_R10}
        used = set(ids.values())
        for name in NAMES_R14 + NAMES_R28 + ["PowerupGlitter"]:
            value = r.randrange(1, 1 << 32)
            while value in used:
                value = r.randrange(1, 1 << 32)
            used.add(value)
            ids[name] = value
        glitter = animation(env, r)
        env.put(glitter + 8, r.randrange(1, 1 << 32))
        buckets = o["buckets"]
        if full:
            e10 = {n: ids[n] for n in NAMES_R10}
            e14 = {n: ids[n] for n in NAMES_R14}
            e28 = {n: ids[n] for n in NAMES_R28}
        else:
            e10 = {}
            e14 = {}
            e28 = {}
        for flag, name in ((o["coins_reg"], "GAME_TREASURE_COINS"), (o["warp_reg"], "GAME_WARP"),
                           (o["dyn_reg"], "GAME_DYNAMITE"), (o["life_reg"], "GAME_POWERUPS_EXTRALIFE")):
            if flag:
                e10[name] = ids[name]
            else:
                e10.pop(name, None)
        if o["glitter_reg"]:
            e14["PowerupGlitter"] = glitter
        e2c = {}
        if o["cycle_reg"]:
            e2c["GAME_CYCLE100"] = animation(env, r)
        if o["powerup_reg"]:
            e2c["GAME_POWERUP"] = animation(env, r)
        r10 = registry(env, r, e10, buckets)
        r14 = registry(env, r, e14, buckets)
        r28 = registry(env, r, e28, buckets)
        r2c = registry(env, r, e2c, buckets)

        # ---- world, graphics service, sprite list
        quadrant = env.object(0x90, "scroll-box", words=words_of(r, 36))
        env.put(quadrant + 0x84, small(r, -400, 900), small(r, -400, 900))
        parent = env.object(0x70, "view", words=words_of(r, 28))
        env.put(parent + 0x5C, quadrant)
        w = env.object(0x80, "world", words=words_of(r, 32))
        g = env.object(0x40, "graphics", words=words_of(r, 16))
        env.put(w + 0x24, parent)
        env.put(w + 8, g)
        env.put(w + 0x10, r10)
        env.put(w + 0x14, r14)
        env.put(w + 0x28, r28)
        env.put(w + 0x2C, r2c)
        env.put(g + 0xC, w)
        # CPtrList at g+0x10: vptr, head, tail, count, free list, blocks, block size
        previous = 0
        node_addrs = []
        for z, flag2 in o["nodes"]:
            item = env.object(0x70, "listed-actor", words=words_of(r, 28))
            env.put(item + 0x64, z & M32)
            env.write(item + 10, bytes([0x02 if flag2 else r.choice((0x00, 0x01, 0x04, 0x05))]))
            node = env.object(12, "list-node", words=[0, previous, item])
            if previous:
                env.put(previous, node)
            node_addrs.append(node)
            previous = node
        head = node_addrs[0] if node_addrs else 0
        tail = node_addrs[-1] if node_addrs else 0
        free = env.object(12, "free-node", words=words_of(r, 3)) if o["free_node"] else 0
        if free:
            env.put(free, 0)
        env.put(g + 0x10, r.randrange(1, 1 << 32), head, tail, len(node_addrs), free, 0, r.randrange(2, 5))

        # ---- application object and the mode query
        mode_stub = env.stub("game mode query", "thiscall", 0, sequence(*o["mode"]))
        vtable = env.object(0x20, "app-vtable", fill=0)
        env.put(vtable + 0x10, mode_stub)
        service = env.object(0xBE0, "game service", fill=0)
        env.put(service, vtable)
        env.put(service + 0xBD4, r.randrange(1, 1 << 32))
        app = env.object(0x130, "app", words=words_of(r, 0x130 // 4))
        env.put(app + 0x2C, service)
        env.put(app + 0x124, (r.randrange(1, 1 << 32) if o["a124"] else 0))
        env.put(G_APP, app)

        # ---- globals
        levels = env.object(8, "level info", words=[o["level_word"], r.randrange(1, 1 << 32)])
        env.put(LEVEL_INFO, levels)
        env.put(G_SKIP_INIT, o["skip"])
        env.put(G_COUNT, o["count"] & M32)
        env.put(G_TICK, o["tick"] & M32)
        env.put(G_CURSOR, o["cursor"] & M32)
        env.put(G_CURSE_FLAG, o["curse_flag"])

        # ---- the actor
        key = {"plain": r.randrange(1, 1 << 32), "zero": 0, "coins": ids["GAME_TREASURE_COINS"],
               "goldbars": ids["GAME_TREASURE_GOLDBARS"], "warp": ids["GAME_WARP"],
               "dynamite": ids["GAME_DYNAMITE"], "life": ids["GAME_POWERUPS_EXTRALIFE"],
               "vertwarp": ids["GAME_VERTWARP"], "ghost": ids["GAME_POWERUPS_GHOST"]}[o["key"]]
        count = o["count"] if o["count"] < 0x80000000 else 0
        if not o["skip"]:
            pass  # 0x4719e0 fills the tables from the registries
        else:
            found_at = o["found_at"]
            seen = {key}
            for table in (T_KEYS, T_VALUES, T_FLAGS, T_TYPES):
                values = []
                for index in range(TABLE_WORDS):
                    value = r.randrange(1, 1 << 32)
                    while table == T_KEYS and value in seen:
                        value = r.randrange(1, 1 << 32)
                    if table == T_KEYS:
                        seen.add(value)
                    values.append(value)
                env.put(table, *values)
            if found_at is not None and 0 <= found_at < min(max(count, 0), TABLE_WORDS):
                env.put(T_KEYS + 4 * found_at, key)
        sub = env.object(0x180, "state", words=words_of(r, 0x180 // 4))
        env.put(sub + 0x1C, o["state"])
        env.put(sub + 0x10, o["handler"])
        env.put(sub + 0x130, o["s130"] & M32)
        env.put(sub + 0x64, o["s64"] & M32)
        env.put(sub + 0x68, o["s68"] & M32)
        if o["list16c"] is not None:
            env.put(sub + 0x16C, o["list16c"](env, r))
        elif o["state"] == 5:
            env.put(sub + 0x16C, 0)
        else:
            # non-zero junk so that a clear or a shifted store near +0x168 shows up
            env.put(sub + 0x16C, random.Random(seed ^ 0x16C).randrange(1, 1 << 32))
        actor = env.object(0x1C0, "actor", words=words_of(r, 0x1C0 // 4))
        env.put(actor + 4, r.randrange(1, 1 << 16))
        env.put(actor + 8, r.randrange(1, 1 << 32) & ~0x0003_0000 & ~0x80000 & ~0x20000)
        env.put(actor + 0xC, w)
        env.put(actor + 0x4C, small(r), small(r))
        env.put(actor + 0x64, o["z"] & M32)
        env.put(actor + 0x6C, sub)
        if o["gl"]:
            gl = env.object(0x20, "glitter", words=words_of(r, 8))
            env.put(gl + 8, r.randrange(1, 1 << 32) & ~0x10000)
            env.put(actor + 0xC8, gl)
        else:
            gl = 0
            env.put(actor + 0xC8, 0)
        env.put(actor + 0xD0, r.choice((0x0, 0x5, 0x80, 0x1234)))
        env.put(actor + 0xFC, r.randrange(1, 1 << 32))
        for offset in (0x138, 0x13C, 0x140, 0x144):
            env.put(actor + offset, small(r, -50, 50))
        env.put(actor + 0x164, (r.randrange(1, 1 << 32) & ~0x200) | (0x200 if o["flags200"] else 0))
        env.put(actor + 0x170, key)
        if o["rect"]:
            rect = env.object(0x40, "rect", words=[*words_of(r, 6), small(r, 5, 90), small(r, 5, 90),
                                                     small(r, 5, 90), small(r, 5, 90), *words_of(r, 6)])
            env.put(actor + 0x174, rect)
            env.put(rect + 0x18, small(r, 0, 20), small(r, 0, 20), small(r, 30, 90), small(r, 30, 90))
        else:
            env.put(actor + 0x174, 0)
        # animation cursor block at actor+0x188 (its +8 is actor+0x190)
        block = actor + 0x188
        anim = o["anim"]
        if anim == "none":
            env.put(block + 8, 0)
        else:
            clip = animation(env, r)
            env.put(block + 8, clip)
            env.put(block + 0xC, r.randrange(1, 1 << 32))
            if anim == "count1":       # countdown by one
                env.put(block + 0x14, r.randrange(2, 9))
                env.put(block + 0x18, 0)
            elif anim == "countdown":  # countdown by the global step
                env.put(block + 0x14, o["cursor"] + r.randrange(1, 9))
                env.put(block + 0x18, r.randrange(1, 1 << 32))
            elif anim == "expired":    # step covers the remainder, frame stays, +0x20 returned
                env.put(block + 0x14, max(1, o["cursor"] - r.randrange(0, 2)) if o["cursor"] else 1)
                env.put(block + 0x18, r.randrange(1, 1 << 32))
                env.put(block + 0x1C, r.randrange(1, 1 << 32))
            elif anim == "idle":
                env.put(block + 0x14, 0)
                env.put(block + 0x1C, r.randrange(1, 1 << 32))
            env.put(block + 0x20, r.randrange(1, 1 << 32))
            env.put(block + 0x24, r.randrange(1, 1 << 32))
        return {"actor": actor, "sub": sub, "world": w, "ids": ids}

    return setup


def case(label, function, r, **changes):
    o = spec(**changes)
    return Case(label, function, world(o, r.randrange(1 << 30)), arguments=(lambda tokens: tokens["actor"],))


def sweep(r, function, label, base, dims, combos=0):
    """Base case, every single-dimension change from it, and some random combinations of changes."""
    yield case(f"{label} base", function, r, **base)
    for name, values in dims.items():
        for value in values:
            yield case(f"{label} {name}={value}", function, r, **{**base, name: value})
    flat = [(n, v) for n, vs in dims.items() for v in vs]
    for index in range(combos):
        picks = {}
        for name, value in r.sample(flat, r.randrange(2, 6)):
            picks[name] = value
        yield case(f"{label} mix {index}", function, r, **{**base, **picks})


def position_list(box, count):
    """Factory: S+0x16c object, head at +4, nodes [next, ?, item], item [x, y]; the actor's x and y come from the actor."""

    def build(env, r):
        # the actor is built after the state object, so x and y are patched by fix_positions()
        holder = env.object(0x20, "position-list", words=words_of(r, 8))
        items = []
        previous = 0
        nodes = []
        for index in range(count):
            item = env.object(0x10, "position", words=words_of(r, 4))
            items.append(item)
            node = env.object(12, "position-node", words=[0, 0, item])
            if previous:
                env.put(previous, node)
            nodes.append(node)
            previous = node
        env.put(holder + 4, nodes[0] if nodes else 0)
        box.append(items)
        return holder

    return build


def with_positions(label, function, r, match_index, count, near_miss=False, **changes):
    box = []
    o = spec(list16c=position_list(box, count), **changes)
    inner = world(o, r.randrange(1 << 30))

    def setup(env):
        tokens = inner(env)
        items, match, miss = box[-1], match_index, near_miss
        x, y = env.get(tokens["actor"] + 0x4C), env.get(tokens["actor"] + 0x50)
        for index, item in enumerate(items):
            if index == match:
                env.put(item, x, y)
            elif miss and index % 2 == 0:
                env.put(item, x, (y + index + 1) & M32)
            elif miss:
                env.put(item, (x + index + 1) & M32, y)
            else:
                env.put(item, (x + 17 + index) & M32, (y + 29 + index) & M32)
        return tokens

    return Case(label, function, setup, arguments=(lambda tokens: tokens["actor"],))


# ------------------------------------------------------------------------------------------------
STATES_QUIET = (1, 2, 3, 4)


def build_dims(extra=None):
    dims = dict(
        handler=(0x470100,), mode=((4,), (3,), (4, 3), (4, 4)), a124=(0,), count=(0, 1, 66, 0xFFFFFFFF),
        found_at=(0, 1, 39, None), key=("zero", "coins", "goldbars", "warp", "dynamite", "life"),
        coins_reg=(False,), warp_reg=(False,), dyn_reg=(False,), life_reg=(False,), glitter_reg=(False,),
        cycle_reg=(False,), powerup_reg=(False,), z=(5, 0xFFFFFFFF), anim=("count1", "countdown", "expired", "idle"),
        rect=(False,), nodes=(((3, False),), ((50, False),), ((50, True),), ((4, False), (60, False), (70, True)),
                              ((900, True), (2, False))),
        free_node=(False,), buckets=(1, 3, 13),
    )
    if extra:
        dims.update(extra)
    return dims


def state_zero_cases(r, function, label, extra=None, combos=40):
    yield from sweep(r, function, f"{label} build", dict(state=0), build_dims(extra), combos)
    # table initializer runs (skip flag clear), with the full registries, for several keys
    for number, key in enumerate(("coins", "goldbars", "warp", "dynamite", "life", "vertwarp", "ghost", "plain", "zero")):
        for glitter in (True, False):
            yield case(f"{label} initialized tables key={key} glitter={glitter}", function, r, state=0, skip=0,
                       full=True, count=66, key=key, glitter_reg=glitter, found_at=None,
                       level_word=(2, 3, 0xD)[(number + glitter) % 3])
    yield case(f"{label} initialized tables, count 0", function, r, state=0, skip=0, full=True, count=0, key="plain")


def clear_cases(r, f, label, **base):
    """State 0 with the pointers that the entry clears set non-zero beforehand, and key 0 against missing names."""
    base = {"state": 0, "mode": (4,), **base}
    regs = ("coins_reg", "warp_reg", "dyn_reg", "life_reg")
    for name, changes in (
            ("glitter held", dict(gl=True)), ("glitter held, no glitter registry", dict(gl=True, glitter_reg=False)),
            ("glitter held, a124 clear", dict(gl=True, a124=0)), ("glitter held, no powerup", dict(gl=True, powerup_reg=False)),
            ("zero key, coins missing", dict(key="zero", coins_reg=False)),
            ("zero key, warp missing", dict(key="zero", warp_reg=False)),
            ("zero key, dynamite missing", dict(key="zero", dyn_reg=False)),
            ("zero key, life missing", dict(key="zero", life_reg=False)),
            ("zero key, all missing", dict(key="zero", **{n: False for n in regs})),
            ("zero key, all missing, mode 3", dict(key="zero", mode=(3,), **{n: False for n in regs})),
            ("zero key, coins missing, a124 clear", dict(key="zero", coins_reg=False, a124=0)),
            ("zero key, warp missing, glitter held", dict(key="zero", warp_reg=False, gl=True))):
        yield case(f"{label} clears: {name}", f, r, **{**base, **changes})


def other_state_cases(r, function, label, tick_states=False):
    for state in (1, 2, 3, 4, 6, 9, 0x1C, 0x1E, 0x2328, 0x232A, 9001, 0x7FFFFFFF, 0xFFFFFFFF):
        yield case(f"{label} state {state:#x} does nothing", function, r, state=state, skip=1)
    for gl in (False, True):
        yield case(f"{label} state 0x1d gl={gl}", function, r, state=0x1D, gl=gl)
    for anim in ("none", "count1", "countdown", "expired", "idle"):
        for cursor in (0, 3):
            yield case(f"{label} state 5 anim={anim} cursor={cursor}", function, r, state=5, anim=anim, cursor=cursor)
    for flags200 in (False, True):
        yield case(f"{label} state 5 flags200={flags200}", function, r, state=5, flags200=flags200)


def special_cases(r):
    f = SPECIAL
    yield from state_zero_cases(r, f, "special", combos=30)
    yield from other_state_cases(r, f, "special")
    for flags200 in (False, True):
        for anim in ("none", "idle"):
            yield case(f"special state 5 anim={anim} flags200={flags200}", f, r, state=5, anim=anim, flags200=flags200,
                       cursor=r.randrange(0, 9))
    for gl in (False, True):
        for _ in range(2):
            yield case(f"special rise state 9000 gl={gl}", f, r, state=9000, gl=gl)
    # rise: signed and unsigned arithmetic on large and negative positions
    # the rising flight: tick against remaining time, and each velocity present or absent
    for tick in (0, 1, 499, 500, 501, 0xFFFF, 0x80000000, 0xFFFFFFFF):
        for s64, s68 in ((0, 0), (-5, 7), (9, -300), (123456, 654321)):
            yield case(f"special flight tick={tick:#x} v=({s64},{s68})", f, r, state=0x2329, tick=tick, s64=s64 & M32,
                       s68=s68 & M32, s130=r.choice((500, 1, 0, 0x80000001)))
    for tick in (7, 500, 501):
        yield case(f"special flight exact remainder tick={tick}", f, r, state=0x2329, tick=tick, s130=tick, s64=33, s68=44,
                   anim="count1", cursor=2)
    for s130 in (0, 17):
        yield case(f"special flight zero tick s130={s130}", f, r, state=0x2329, tick=0, s130=s130, s64=-1 & M32, s68=1)


def curse_cases(r):
    f = CURSE
    base = dict(state=0, mode=(4,), curse_flag=1)
    dims = dict(
        mode=((3,), (4, 3), (4, 4)), curse_flag=(0,), a124=(0,), handler=(0x470100,), z=(5, 0xFFFFFFFF),
        count=(0, 1, 66, 0xFFFFFFFF), found_at=(0, 1, 39, None), key=("zero", "coins", "goldbars", "warp", "plain"),
        coins_reg=(False,), glitter_reg=(False,), cycle_reg=(False,), powerup_reg=(False,),
        anim=("count1", "countdown"), rect=(False,), free_node=(False,), buckets=(1, 3, 13),
        nodes=(((3, False),), ((50, False),), ((50, True),), ((4, False), (60, False), (70, True)), ((900, True), (2, False))),
    )
    yield from sweep(r, f, "curse build", base, dims, 30)
    for number, key in enumerate(("coins", "goldbars", "warp", "plain", "zero")):
        for glitter in (True, False):
            yield case(f"curse initialized tables key={key} glitter={glitter}", f, r, state=0, mode=(4,), skip=0, full=True,
                       count=66, key=key, glitter_reg=glitter, level_word=(2, 3, 0xD)[(number + glitter) % 3])
    yield case("curse initialized tables count 0", f, r, state=0, mode=(4,), skip=0, full=True, count=0, key="plain")
    for mode in ((3,), (5,), (4, 5), (0,), (0xFFFFFFFF,)):
        for flag in (0, 1):
            yield case(f"curse not available mode={mode} flag={flag}", f, r, state=0, mode=mode, curse_flag=flag)
    for state in (1, 2, 3, 4, 6, 0x1C, 0x1E, 9000, 0x2329, 0xFFFFFFFF):
        yield case(f"curse state {state:#x} does nothing", f, r, state=state)
    for gl in (False, True):
        yield case(f"curse state 0x1d gl={gl}", f, r, state=0x1D, gl=gl)
    for anim in ("none", "count1", "countdown", "expired", "idle"):
        yield case(f"curse state 5 anim={anim} no list", f, r, state=5, anim=anim, cursor=r.randrange(0, 4))
    for count in (1, 2, 3, 4):
        for match in [None, *range(count)]:
            for miss in (False, True):
                if match is None and miss and count > 2:
                    continue
                yield with_positions(f"curse state 5 pickup list count={count} match={match} near_miss={miss}", f, r,
                                     match, count, miss, state=5)
    for count in (0,):
        yield with_positions("curse state 5 empty pickup list", f, r, None, 0, state=5)


def wrapper_cases(r):
    f = WRAPPER
    base = dict(state=0)
    dims = dict(
        handler=(0x470100,), mode=((4,), (3,), (4, 3)), a124=(0,), count=(0, 1, 66, 0xFFFFFFFF),
        found_at=(0, 1, 39, None), key=("zero", "coins", "goldbars", "warp"),
        coins_reg=(False,), cycle_reg=(False,), powerup_reg=(False,), glitter_reg=(False,), z=(5,), rect=(False,),
        anim=("count1",), free_node=(False,),
    )
    yield from sweep(r, f, "wrapper build", base, dims, 10)
    yield case("wrapper initialized tables", f, r, state=0, skip=0, full=True, count=66, key="goldbars", level_word=3)
    for state in (1, 2, 4, 6, 0x1C, 0x1E, 0x232A, 0xFFFFFFFF):
        yield case(f"wrapper state {state:#x}", f, r, state=state)
    for gl in (False, True):
        for _ in range(2):
            yield case(f"wrapper state 0x1d gl={gl}", f, r, state=0x1D, gl=gl)
        yield case(f"wrapper state 9000 gl={gl}", f, r, state=9000, gl=gl, glitter_reg=False)
    for flags200 in (False, True):
        for anim in ("none", "countdown"):
            yield case(f"wrapper state 5 anim={anim} flags200={flags200}", f, r, state=5, flags200=flags200, anim=anim,
                       cursor=r.randrange(0, 5))
    for tick in (0, 5, 499, 500, 501, 0xFFFFFFFF):
        yield case(f"wrapper flight tick={tick:#x}", f, r, state=0x2329, tick=tick, s64=r.randrange(1, 100000),
                   s68=-r.randrange(1, 100000) & M32, s130=500)
    yield case("wrapper flight flag", f, r, state=0x2329, tick=500, s130=500, s64=0, s68=0)


def simple_cases(r, f, label, extra=None):
    base = dict(state=0)
    dims = build_dims(extra)
    dims.pop("mode")
    dims.pop("handler")
    dims.pop("a124", None)
    dims["a124"] = (0,)
    yield from sweep(r, f, f"{label} build", base, dims, 20)
    for number, key in enumerate(("coins", "goldbars", "warp", "dynamite", "plain", "zero")):
        for glitter in (True, False):
            yield case(f"{label} initialized tables key={key} glitter={glitter}", f, r, state=0, skip=0, full=True,
                       count=66, key=key, glitter_reg=glitter, level_word=(2, 3, 0xD)[(number + glitter) % 3])
    yield case(f"{label} initialized tables count 0", f, r, state=0, skip=0, full=True, count=0, key="plain")
    for state in (1, 2, 3, 4, 6, 0x1C, 0x1E, 9000, 0x2329, 0xFFFFFFFF):
        yield case(f"{label} state {state:#x} does nothing", f, r, state=state)
    for gl in (False, True):
        yield case(f"{label} state 0x1d gl={gl}", f, r, state=0x1D, gl=gl)
    for anim in ("none", "count1", "countdown", "expired", "idle"):
        yield case(f"{label} state 5 anim={anim}", f, r, state=5, anim=anim, cursor=r.randrange(0, 4))


def cases(random_source):
    r = random_source
    yield from special_cases(r)
    yield from clear_cases(r, SPECIAL, "special")
    yield from curse_cases(r)
    yield from clear_cases(r, CURSE, "curse", curse_flag=1)
    yield from wrapper_cases(r)
    yield from clear_cases(r, WRAPPER, "wrapper")
    yield from simple_cases(r, HEALTH, "health")
    yield from clear_cases(r, HEALTH, "health")
    yield from simple_cases(r, AMMO, "ammo")
    yield from clear_cases(r, AMMO, "ammo")
