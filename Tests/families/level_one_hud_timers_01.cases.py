"""Cases for level_one_hud_timers_01: Level 1 HUD frames and number group entries.

Layout notes (all recovered from the original disassembly):

* actor (frame argument): +8 flags, +0xc world, +0x40 flags, +0x64 layer, +0x6c info, +0xfc next-extra-life score,
  +0x16c/+0x170/+0x174 frame index / image set / current image, +0x188 animation (its +8 stays 0 so 0x4c82a0 returns at once).
* info (actor+0x6c): +0x18 binder group, +0x1c state (0 build, 5 run), +0x130 counter, +0x168 player stats.
* group (0x60 bytes): binder fields +4..+0x24 and +0x5c, and from +0x28 the number group: +0x2c value, +0x30 count, +0x34.. digit actors.
* world: +0x10 string table owner (image sets), +0x14 (digit class), +0x28 (extra life table + flag at +0x30), +0x2c (animations).
  String tables are embedded at owner+0x10: +4 bucket array, +8 bucket count, nodes [next, ?, key, value].
"""
import random

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns  # noqa: F401

M32 = 0xFFFFFFFF

# owned functions
INIT = 0x490590
BIND = 0x490760
SCORE = 0x4908B0
CONSTRUCT = 0x490C40
HEALTH = 0x490C50
WEAPON = 0x490F80
LIVES = 0x4912A0
TIMER = 0x491540

OPERATOR_NEW = 0x4F63EC

# globals
G_GS = 0x5371FC
G_L, G_T, G_R, G_B = 0x5370C8, 0x5370CC, 0x5370D0, 0x5370D4
G_PLAYER = 0x537E88
G_TICK = 0x5430C4
G_SCORE = 0x534CC4
G_HEALTH = 0x534CC8
G_MS = 0x534EA8
G_MANAGER = 0x53C9FC
G_SOUND_ON = 0x532C0C
G_SOUND_ID = 0x532C10

VT_ACTOR = 0x5137F0  # vtable the constructed digit actor gets: +4 delete, +0x28 create

NAMES = {
    "treasure": b"GAME_INTERFACE_TREASURECHEST",
    "heart": b"GAME_INTERFACE_HEALTHHEART",
    "pistol": b"GAME_INTERFACE_WEAPONS_PISTOL",
    "magic": b"GAME_INTERFACE_WEAPONS_MAGIC",
    "dynamite": b"GAME_INTERFACE_WEAPONS_DYNAMITE",
    "lives": b"GAME_INTERFACE_LIVESHEAD",
    "stopwatch": b"GAME_INTERFACE_STOPWATCH",
    "score_numbers": b"GAME_INTERFACE_SCORENUMBERS",
    "health_numbers": b"GAME_INTERFACE_HEALTHNUMBERS",
    "small_numbers": b"GAME_INTERFACE_SMALLNUMBERS",
}
DIGIT_CLASS = b"StatusNumberDigit"
EXTRA_LIFE = b"GAME_EXTRALIFE"
ANIM_NAMES = (b"GAME_INTERFACE_CHEST", b"GAME_INTERFACE_PISTOL", b"GAME_INTERFACE_MAGIC", b"GAME_INTERFACE_DYNAMITE",
              b"GAME_INTERFACE_LIVES", b"GAME_CYCLE100")


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def rnd(rs, n=1, low=1, high=1 << 32):
    return [rs.randrange(low, high) for _ in range(n)]


def small_signed(rs, span=300):
    return rs.randrange(-span, span)


def make_registry(env, rs, entries, buckets=None):
    """String table owner. Each bucket also carries a decoy whose key only differs after the real name."""
    buckets = buckets or rs.choice((1, 3, 5, 7, 11))
    owner = env.object(0x40, "registry-owner", words=rnd(rs, 0x10))
    table = owner + 0x10
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, (value ^ 0xFFFF) & M32])
        env.put(array + 4 * index, decoy if rs.random() < 0.5 else node)
    return owner


def make_set(env, rs, low, high, zero_at=()):
    """An image set: +0x14 array indexed by frame number, +0x64 first and +0x68 last frame. Entries are frame objects."""
    pad = max(0, -low)
    top = max(high, 0, low) + 1
    frames = []
    for index in range(top):
        frames.append(0 if index in zero_at else env.object(0x30, "frame", words=[rs.randrange(1, 90) for _ in range(12)]))
    base = env.object(4 * (top + pad), "set-array", words=[rs.randrange(1, 1 << 32) for _ in range(pad)] + frames)
    image_set = env.object(0x70, "image-set", words=rnd(rs, 28))
    env.put(image_set + 0x14, base + 4 * pad)
    env.put(image_set + 0x64, low & M32, high & M32)
    return image_set


def digit_set(env, rs, kind="full"):
    if kind == "full":
        return make_set(env, rs, 0, 9)
    if kind == "short":
        return make_set(env, rs, 0, rs.randrange(4, 9))
    if kind == "shifted":
        return make_set(env, rs, rs.randrange(1, 4), 9)
    if kind == "dashed":
        return make_set(env, rs, -3, 9)
    if kind == "empty":
        return make_set(env, rs, 5, 4)
    raise ValueError(kind)


def make_anim(env, seed):
    """An animation record as 0x4c79e0 stores it: +0xc frame array, +0x10 count; each frame has +0x1c a distinct value and ends the cycle (+0xc == 9)."""
    r = random.Random(seed)
    count = r.randrange(2, 4)
    frames = []
    for _ in range(count):
        words = [0] * 16
        words[3] = 9
        words[7] = r.randrange(1, 1 << 20)
        frames.append(env.object(0x40, "anim-frame", words=words))
    array = env.object(4 * count, "anim-frames", words=frames)
    return env.object(0x40, "anim", words=[r.randrange(1, 1 << 30) for _ in range(3)] + [array, count] + [r.randrange(1, 1 << 30) for _ in range(11)])


def make_voice_pool(env, rs, player_sound, probe):
    """A pool with one idle voice so 0x4b45f0 reaches its COM style buffer methods. Returns (voice, log)."""
    log = env.object(0x80, "voice-log", fill=0)

    def recorder(slot, result=0, out_arg=None):
        def effect(env, call):
            n = env.calls_so_far(call.function)
            env.put(log + slot * 0x10, n, call.receiver & M32, *[a & M32 for a in call.arguments[:2]])
            if out_arg is not None:
                env.put(call.arguments[out_arg], 0)
            return result
        return effect

    vtable = env.object(0x60, "voice-vtable", words=rnd(rs, 24))
    env.put(vtable + 0x24, env.stub("voice-status", "stdcall", 2, recorder(0, 0, 1)))
    env.put(vtable + 0x30, env.stub("voice-play", "stdcall", 4, recorder(1)))
    env.put(vtable + 0x3C, env.stub("voice-frequency", "stdcall", 2, recorder(2)))
    env.put(vtable + 0x40, env.stub("voice-volume", "stdcall", 2, recorder(3)))
    env.put(vtable + 0x44, env.stub("voice-pan", "stdcall", 2, recorder(4)))
    buf = env.object(0x10, "voice-buffer", fill=0)
    env.put(buf, vtable)
    voice = env.object(0x60, "voice", words=rnd(rs, 24))
    env.put(voice + 0x04, 0, 0)
    env.put(voice + 0x0C, buf)
    env.put(voice + 0x10, probe)
    env.put(voice + 0x30, rs.randrange(1, 1 << 32))
    env.put(player_sound + 0x30, voice + 4, voice + 4)
    env.put(player_sound + 0x18, rs.randrange(1, 1000), rs.randrange(1, 1000), rs.randrange(1, 1000), rs.randrange(1, 1000))
    return voice, log


def make_world(env, rs, o):
    """World with the string tables the frames look into. o['sets'] maps a NAMES key to a kind (or None to omit it)."""
    sets = {}
    entries = {}
    for key, name in NAMES.items():
        kind = o.get("sets", {}).get(key, "frame")
        if kind is None:
            continue
        if key.endswith("numbers"):
            sets[key] = digit_set(env, rs, "full" if kind == "frame" else kind)
        else:
            sets[key] = make_set(env, rs, rs.randrange(0, 3), rs.randrange(3, 9)) if kind == "frame" else digit_set(env, rs, kind)
        entries[name] = sets[key]
    images = make_registry(env, rs, entries)
    classes = make_registry(env, rs, {DIGIT_CLASS: rs.randrange(1, 1 << 32)} if o.get("digit_class", True) else {})
    extra_entries = {}
    handler = None
    if o.get("extra_life_entry", False):
        handler = env.object(0x20, "sound-handler", words=rnd(rs, 8))
        holder = env.object(0x20, "sound-holder", words=rnd(rs, 8))
        player_sound = env.object(0x40 if o.get("voice") else 0x30, "sound-player", words=rnd(rs, 16 if o.get("voice") else 12))
        probe = env.object(0x90, "sound-probe", words=rnd(rs, 36))
        env.put(holder + 0x10, player_sound)
        env.put(player_sound + 0x10, probe)
        env.put(probe + 0x78, o.get("probe78", 0))
        if o.get("voice"):
            make_voice_pool(env, rs, player_sound, probe)
        extra_entries[EXTRA_LIFE] = holder
    extra = make_registry(env, rs, extra_entries)
    env.put(extra + 0x30, o.get("extra_flag", 0))
    anim_entries = {name: make_anim(env, 7000 + index) for index, name in enumerate(ANIM_NAMES)} if o.get("anims") else {}
    anims = make_registry(env, rs, anim_entries)
    renderer = env.object(8, "renderer", fill=0)
    vtable = env.object(0x40, "renderer-vtable", words=rnd(rs, 16))
    env.put(renderer, vtable)
    env.put(vtable + 0x28, env.stub("renderer-place", "thiscall", 3, returns(rs.randrange(0, 1 << 32))))
    world = env.object(0x40, "world", words=rnd(rs, 16))
    env.put(world + 0x0C, renderer)
    env.put(world + 0x10, images)
    env.put(world + 0x14, classes)
    env.put(world + 0x28, extra)
    env.put(world + 0x2C, anims)
    return world, sets, renderer


def make_stats(env, rs, o):
    stats = env.object(0xA0, "player-stats", words=rnd(rs, 40))
    st = o.get("stats", {})
    env.put(stats + 0x18, st.get("s18", 0 if o.get("timer_hide", False) else rs.randrange(1, 50)))
    env.put(stats + 0x30, st.get("weapon", 1))
    env.put(stats + 0x70, st.get("ammo1", rs.randrange(0, 40)))
    env.put(stats + 0x74, st.get("ammo2", rs.randrange(0, 40)))
    env.put(stats + 0x78, st.get("ammo3", rs.randrange(0, 40)))
    env.put(stats + 0x7C, st.get("lives", rs.randrange(1, 9)))
    return stats


def make_player(env, rs, o, stats):
    pinfo = env.object(0x40, "player-info", words=rnd(rs, 16))
    env.put(pinfo + 0x14, stats)
    player = env.object(0x120, "player", words=rnd(rs, 72))
    env.put(player + 0x6C, pinfo)
    env.put(player + 0xF8, o.get("p_score", rs.randrange(0, 900000)))
    env.put(player + 0x10C, o.get("p_health", rs.randrange(1, 100)))
    return player


def make_digit(env, rs, world, image_set, value_hint=None):
    info = env.object(0x80, "digit-info", words=rnd(rs, 32))
    digit = env.object(0x180, "digit", words=rnd(rs, 96))
    env.put(digit + 0x6C, info)
    env.put(digit + 0x0C, world)
    env.put(digit + 0x170, image_set)
    env.put(digit + 0x40, rs.randrange(0, 1 << 32))
    return digit


def make_group(env, rs, o, actor, world, sets):
    """Hand built binder + number group for the run state."""
    g = o["group"]
    group = env.object(0x60, "group", words=rnd(rs, 24))
    env.put(group + 0x04, g.get("ax", 1))
    env.put(group + 0x08, g.get("ox", small_signed(rs)))
    env.put(group + 0x0C, g.get("ay", 4))
    env.put(group + 0x10, g.get("oy", small_signed(rs)))
    env.put(group + 0x14, g["g14"] & M32)
    env.put(group + 0x18, g["g18"] & M32)
    env.put(group + 0x24, actor)
    count = g.get("count", 3)
    env.put(group + 0x2C, g.get("value", rs.randrange(0, 1 << 31)) & M32)
    env.put(group + 0x30, count)
    env.put(group + 0x5C, g.get("g5c", rs.randrange(1, 1 << 32)) & M32)
    digits = []
    kinds = g.get("digit_kinds") or ["full"] * count
    for index in range(count):
        kind = kinds[index % len(kinds)]
        image_set = 0 if kind is None else digit_set(env, rs, kind)
        digit = make_digit(env, rs, world, image_set)
        digits.append(digit)
        env.put(group + 0x34 + 4 * index, digit)
    return group, digits


def build(env, rs, o):
    """Scene for one frame call. Returns the tokens the case needs."""
    c8, ct, cr, cb = o.get("rect", (rs.randrange(-40, 40), rs.randrange(-40, 40), rs.randrange(300, 700), rs.randrange(300, 500)))
    env.put(G_L, c8 & M32)
    env.put(G_T, ct & M32)
    env.put(G_R, cr & M32)
    env.put(G_B, cb & M32)
    env.put(G_TICK, o.get("tick", rs.randrange(1, 60)))
    env.put(G_SCORE, o.get("score", rs.randrange(0, 1 << 31)) & M32)
    env.put(G_HEALTH, o.get("health", rs.randrange(0, 101)) & M32)
    env.put(G_MS, o.get("ms", rs.randrange(0, 1 << 31)) & M32)
    env.put(G_SOUND_ON, o.get("sound_on", 1))
    env.put(G_SOUND_ID, o["sound_id"] if "sound_id" in o else rs.randrange(1, 1 << 32))

    world, sets, renderer = make_world(env, rs, o)
    ph = o.get("phase", 7)
    gs = env.object(0x80, "game-state", words=rnd(rs, 32))
    env.put(gs + 0x68, ph & M32)
    env.put(gs + 0x6C, o.get("gs6c", 1) & M32)
    mode_object = env.object(8, "mode-object", fill=0)
    mode_vtable = env.object(0x40, "mode-vtable", words=rnd(rs, 16))
    env.put(mode_object, mode_vtable)
    env.put(mode_vtable + 0x10, env.stub("game-mode", "thiscall", 0, returns(o.get("mode", 1))))
    env.put(gs + 0x2C, mode_object)
    env.put(G_GS, gs)

    stats = make_stats(env, rs, o)
    if o.get("player", True):
        player = make_player(env, rs, o, stats if o.get("player_stats", True) else 0)
        env.put(G_PLAYER, player)
    else:
        player = 0
        env.put(G_PLAYER, 0)

    info = env.object(0x180, "hud-info", words=rnd(rs, 96))
    actor = env.object(0x1C0, "hud-actor", words=rnd(rs, 112))
    env.put(actor + 0x6C, info)
    env.put(actor + 0x0C, world)
    env.put(actor + 0x08, rs.randrange(0, 1 << 32) & ~1 if o.get("flag8_clear", True) else rs.randrange(0, 1 << 32))
    env.put(actor + 0x40, o.get("flag40", rs.randrange(0, 1 << 32)))
    env.put(actor + 0x64, rs.randrange(0, 200))
    env.put(actor + 0xFC, o.get("next_life", rs.randrange(0, 1 << 31)) & M32)
    cyc = o.get("cycle")
    if cyc is None:
        env.put(actor + 0x170, 0)
        env.put(actor + 0x16C, rs.randrange(0, 5))
        env.put(actor + 0x174, rs.choice((0, env.object(0x30, "frame", words=[rs.randrange(1, 90) for _ in range(12)]))))
    else:
        cset = make_set(env, rs, cyc["low"], cyc["high"], cyc.get("zero_at", ()))
        env.put(actor + 0x170, cset)
        env.put(actor + 0x16C, cyc["idx"] & M32)
        env.put(actor + 0x174, env.object(0x30, "frame", words=[rs.randrange(1, 90) for _ in range(12)]))
    if o.get("anims"):
        env.put(actor + 0x18C, actor)  # the animation player's owner
    env.put(actor + 0x190, 0)  # animation object +8 == 0: 0x4c82a0 returns -1 at once
    env.put(info + 0x1C, o.get("state", 5))
    env.put(info + 0x168, stats if o.get("info_stats", True) else 0)
    env.put(info + 0x130, o.get("counter", rs.randrange(0, 400)))
    tokens = {"actor": actor, "info": info, "world": world, "gs": gs, "player": player, "stats": stats}

    if o.get("state", 5) == 0:
        manager = env.object(0x1D0, "manager", words=rnd(rs, 116))
        env.put(manager + 0x0C, world)
        env.put(manager + 0x1B4, 0, 0, 0, 0, 0, 0, rs.randrange(3, 9))  # CPtrList: vptr head tail count free blocks blocksize
        env.put(G_MANAGER, manager)
        env.put(VT_ACTOR + 4, env.stub("digit-delete", "thiscall", 1, returns(0)))
        env.put(VT_ACTOR + 0x28, env.stub("digit-create", "thiscall", 4, returns(o.get("create", 1))))
        tokens["manager"] = manager
        if o.get("small_alloc_fails", False):
            env.override(OPERATOR_NEW, allocate(fail_from_call=o["small_alloc_fails"]))
        if o.get("group_alloc_fails", False):
            def deny(env, call):
                if call.arguments[0] == 0x60:
                    return 0
                return env.object(call.arguments[0], name="allocation")
            env.override(OPERATOR_NEW, deny)
        if o.get("digit_info_fails", False):
            def deny_info(env, call):
                if call.arguments[0] == 0x174:
                    return 0
                return env.object(call.arguments[0], name="allocation")
            env.override(OPERATOR_NEW, deny_info)
    elif o.get("group") is None:
        env.put(info + 0x18, 0)
    elif o.get("state", 5) == 5:
        group, digits = make_group(env, rs, o, actor, world, sets)
        env.put(info + 0x18, group)
        tokens.update(group=group, digits=digits)
    if "sets" in o and not o.get("state", 5) == 0:
        pass
    tokens["sets"] = sets
    return tokens


def frame_case(label, function, **o):
    def setup(env, _o=o):
        return build(env, RS[0], _o)
    return Case(label, function, setup, arguments=(lambda t: t["actor"],))


RS = [None]  # the random source of the current cases() call


# ---------------------------------------------------------------------------------------------
# scenario tables


def phase_scenarios(rs):
    """(g14, phase, gs6c, g18) combinations through the binder refresh condition."""
    yield "same phase, 6c>0", dict(phase=12, gs6c=3, group=dict(g14=12, g18=40))
    yield "same phase, 6c==0 skips", dict(phase=12, gs6c=0, group=dict(g14=12, g18=40))
    yield "same phase, 6c<0 skips", dict(phase=12, gs6c=-4, group=dict(g14=12, g18=40))
    yield "new phase within end", dict(phase=9, gs6c=0, group=dict(g14=12, g18=40))
    yield "new phase equals end", dict(phase=40, gs6c=0, group=dict(g14=12, g18=40))
    yield "new phase past end", dict(phase=41, gs6c=2, group=dict(g14=12, g18=40))
    yield "negative phase", dict(phase=-20, gs6c=0, group=dict(g14=5, g18=-3))
    yield "phase zero triggers place", dict(phase=0, gs6c=0, group=dict(g14=12, g18=40))
    yield "phase zero equal 6c>0", dict(phase=0, gs6c=1, group=dict(g14=0, g18=0))
    yield "phase zero past end", dict(phase=0, gs6c=1, group=dict(g14=0, g18=-1))
    yield "random phase", dict(phase=rs.randrange(-50, 90), gs6c=rs.randrange(-2, 3),
                               group=dict(g14=rs.randrange(-50, 90), g18=rs.randrange(-50, 90)))


ANCHORS = [(1, 3), (2, 4), (3, 5), (1, 5), (2, 3), (3, 4), (0, 0), (9, 7), (1, 4), (2, 5), (3, 3)]


def rect_values(rs):
    # even, odd, negative-odd differences so the halving rounds both ways
    yield (10, 20, 410, 330)
    yield (11, 21, 410, 330)
    yield (-30, -25, -3, 4)
    yield (500, 300, 40, 33)
    yield (-7, 13, 6, -34)
    yield (rs.randrange(-99, 99), rs.randrange(-99, 99), rs.randrange(-99, 99), rs.randrange(-99, 99))


# ---------------------------------------------------------------------------------------------
# HudBindNumberGroup / Construct


def bind_case(label, args, o=None):
    o = o or {}

    def setup(env):
        rs = RS[0]
        c8, ct, cr, cb = o.get("rect", (rs.randrange(-40, 40), rs.randrange(-40, 40), rs.randrange(300, 700), rs.randrange(300, 500)))
        env.put(G_L, c8 & M32)
        env.put(G_T, ct & M32)
        env.put(G_R, cr & M32)
        env.put(G_B, cb & M32)
        gs = env.object(0x80, "game-state", words=rnd(rs, 32))
        env.put(gs + 0x6C, o.get("gs6c", 1) & M32)
        env.put(G_GS, gs)
        renderer = env.object(8, "renderer", fill=0)
        vtable = env.object(0x40, "renderer-vtable", words=rnd(rs, 16))
        env.put(renderer, vtable)
        env.put(vtable + 0x28, env.stub("renderer-place", "thiscall", 3, returns(rs.randrange(0, 1 << 32))))
        world = env.object(0x40, "world", words=rnd(rs, 16))
        env.put(world + 0x0C, renderer)
        digit = env.object(0x180, "digit", words=rnd(rs, 96))
        env.put(digit + 0x0C, world)
        env.put(digit + 0x174, rs.randrange(1, 1 << 32))
        env.put(digit + 0x40, rs.randrange(0, 1 << 32))
        env.put(digit + 0x4C, rs.randrange(1, 1 << 32))
        env.put(digit + 0x50, rs.randrange(1, 1 << 32))
        this = env.object(0x60, "binder", words=rnd(rs, 24))
        return {"this": this, "digit": digit}

    return Case(label, BIND, setup, receiver=lambda t: t["this"],
                arguments=tuple((lambda t, a=a: t["digit"] if a == "digit" else a & M32) for a in args))


def cases(random_source):
    RS[0] = random_source
    return _all_cases(random_source)


def _all_cases(rs):
    # --- HudNumberGroupConstruct
    for index in range(3):
        def setup(env, index=index):
            obj = env.object(rs.choice((0x10, 0x40, 0x60)), "group-construct", words=rnd(rs, 4))
            return {"obj": obj}
        yield Case(f"construct writes only the vtable {index}", CONSTRUCT, setup, receiver=lambda t: t["obj"])

    # --- HudBindNumberGroup
    def binder(label, args, **o):
        return bind_case(label, args, o)

    for ax in (0, 1, 2, 3, 4, -1):
        for ay in (0, 2, 3, 4, 5, 6):
            yield binder(f"bind phase0 ax={ax} ay={ay}", ("digit", 0, 50, ax, small_signed(rs), ay, small_signed(rs)))
    for index, rect in enumerate(rect_values(rs)):
        for ax, ay in ((3, 3), (1, 4), (2, 5), (3, 4)):
            yield binder(f"bind rect{index} ax={ax} ay={ay}", ("digit", 5, 77, ax, small_signed(rs), ay, small_signed(rs)),
                         rect=rect)
    # refresh condition: param_2 == -99 with the game state flag, param_2 > param_3
    for gs6c in (1, 0, -1):
        yield binder(f"bind start -99 gs6c={gs6c}", ("digit", -99, 30, 3, 4, 3, 5), gs6c=gs6c)
        yield binder(f"bind start -99 zero end gs6c={gs6c}", ("digit", -99, -99, 2, 4, 4, 5), gs6c=gs6c)
    for start, end in ((10, 9), (10, 10), (-5, -6), (-5, -5), (0, -1), (0, 0), (-98, 0), (-100, -100), (-100, 50), (3, 100)):
        yield binder(f"bind start={start} end={end}", ("digit", start, end, 1, small_signed(rs), 4, small_signed(rs)))
    for _ in range(12):
        start = rs.choice((-99, 0, 0, rs.randrange(-30, 30)))
        yield binder("bind random", ("digit", start, rs.randrange(-30, 60), rs.randrange(0, 5), small_signed(rs),
                                     rs.randrange(2, 7), small_signed(rs)), gs6c=rs.randrange(-1, 2), rect=rs.choice(list(rect_values(rs))))

    yield from _frame_cases(rs)
    yield from _init_cases(rs)


def _frame_cases(rs):
    anchors = [(1, 4), (2, 5), (3, 3), (0, 0), (2, 3), (3, 5), (1, 3), (4, 6)]

    def stateful(function, name, extra=None, count=3):
        extra = extra or {}
        # other states return at once
        for state in (1, 4, 6, 0xB, 0x7FFFFFFF, -1):
            yield frame_case(f"{name} state {state:#x} does nothing", function, state=state, **extra)
        # run state without a group
        yield frame_case(f"{name} run without group", function, state=5, group=None, **extra)
        # binder refresh scenarios
        for index, (label, scenario) in enumerate(phase_scenarios(rs)):
            ax, ay = anchors[index % len(anchors)]
            group = dict(scenario["group"], ax=ax, ay=ay, count=count)
            opts = dict(extra)
            opts.update(scenario)
            opts["group"] = group
            opts["rect"] = list(rect_values(rs))[index % 6]
            yield frame_case(f"{name} run {label} ax={ax} ay={ay}", function, state=5, **opts)
        for ax, ay in ANCHORS:
            yield frame_case(f"{name} run anchors {ax},{ay}", function, state=5, phase=9, gs6c=0,
                             group=dict(g14=1, g18=50, ax=ax, ay=ay, count=count), rect=rs.choice(list(rect_values(rs))), **extra)

    # --- ScoreFrame
    yield from stateful(SCORE, "score", dict(score=0, p_score=0))
    score_extra = dict(phase=9, gs6c=0)
    for label, p_score, value in (("score changed", 123456, 7), ("score unchanged", 424242, 424242), ("score zero", 0, 5),
                                  ("score max", 0x7FFFFFFF, 1), ("score negative", -123 & M32, 4), ("long number", 98765432, 0)):
        for count in (1, 4, 8, 10):
            yield frame_case(f"score {label} count={count}", SCORE, state=5, p_score=p_score, next_life=2000000000,
                             group=dict(g14=9, g18=99, ax=1, ay=4, count=count, value=value,
                                        digit_kinds=rs.choice((["full"], ["short", "full"], ["shifted"], ["dashed", "full"], [None, "full"], ["empty"]))),
                             **score_extra)
    yield frame_case("score no player", SCORE, state=5, player=False, group=dict(g14=9, g18=99, count=4), **score_extra)
    # extra life thresholds
    for label, p_score, value, next_life in (("equal", 2000000, 5, 2000000), ("above", 3500000, 5, 2000000), ("below", 1999999, 5, 2000000),
                                             ("passed with unchanged score", 2000000, 2000000, 1000000),
                                             ("unchanged below", 10, 10, 1000000), ("negative threshold", 5, 5, -1)):
        for lives, flag, entry, sound in ((3, 0, True, 1), (9, 0, True, 0), (10, 0, True, 1), (25, 0, True, 1), (3, 1, True, 1),
                                          (9, 0, False, 1), (9, 1, False, 0)):
            yield frame_case(f"score extra life {label} lives={lives} flag={flag} entry={entry} sound={sound}", SCORE, state=5,
                             p_score=p_score, next_life=next_life, extra_flag=flag, extra_life_entry=entry, sound_on=sound,
                             stats=dict(lives=lives), probe78=0, phase=9, gs6c=0,
                             group=dict(g14=9, g18=99, ax=1, ay=4, count=rs.randrange(1, 9), value=value))
    for lives in (3, 9, 10):
        yield frame_case(f"score extra life plays sound lives={lives}", SCORE, state=5, p_score=2500000, next_life=2000000,
                         extra_flag=0, extra_life_entry=True, sound_on=1, stats=dict(lives=lives), phase=9, gs6c=0,
                         group=dict(g14=9, g18=99, ax=1, ay=4, count=5, value=1))
    # the extra life sound reaches a live voice: flag, lives, sound switch and threshold each change what the voice receives
    for flag in (0, 1, 2, 0x80000000):
        for lives, sound, p_score, next_life in ((3, 1, 2500000, 2000000), (9, 1, 2500000, 2000000), (10, 1, 2500000, 2000000),
                                                 (3, 0, 2500000, 2000000), (3, 1, 1500000, 2000000), (3, 1, 2000000, 2000000)):
            for sound_id in (0, 1, 3):
                if sound_id == 3 and (flag > 1 or lives != 3):
                    continue
                yield frame_case(f"score extra life voice flag={flag:#x} lives={lives} sound={sound} score={p_score} id={sound_id}", SCORE,
                                 state=5, p_score=p_score, next_life=next_life, extra_flag=flag, extra_life_entry=True, voice=True,
                                 probe78=rs.randrange(1, 1 << 32), sound_on=sound, sound_id=sound_id, stats=dict(lives=lives),
                                 phase=9, gs6c=0, group=dict(g14=9, g18=99, ax=1, ay=4, count=rs.randrange(1, 6), value=7))
    yield frame_case("score extra life voice unchanged score", SCORE, state=5, p_score=2000000, next_life=1000000, extra_flag=0,
                     extra_life_entry=True, voice=True, probe78=1, sound_on=1, sound_id=2, stats=dict(lives=4), phase=9, gs6c=0,
                     group=dict(g14=9, g18=99, ax=1, ay=4, count=3, value=2000000))
    # state 0 build with animation records present so 0x4c79e0 installs them on the actor
    for index, o in enumerate((dict(), dict(score=0), dict(score=1000000), dict(sets={"treasure": None}),
                               dict(digit_class=False), dict(create=0))):
        yield frame_case(f"score build with animations {index}", SCORE, state=0, phase=rs.randrange(-5, 30), anims=True, **o)
    # state 0 build
    for label, o in (("normal", {}), ("score zero", dict(score=0)), ("score million", dict(score=1000000)),
                     ("score just below million", dict(score=999999)), ("negative score", dict(score=-5)),
                     ("score 5.5 million", dict(score=5500000)), ("big score", dict(score=0x7FFFFFFF)),
                     ("no chest set", dict(sets={"treasure": None})),
                     ("empty chest set", dict(sets={"treasure": "empty"})),
                     ("no digit class", dict(digit_class=False)),
                     ("digit create fails", dict(create=0)),
                     ("digit info allocation fails", dict(digit_info_fails=True)),
                     ("no digit sets", dict(sets={"score_numbers": None})),
                     ("short digit sets", dict(sets={"score_numbers": "short"})),
                     ("dashed digit sets", dict(sets={"score_numbers": "dashed"}))):
        yield frame_case(f"score build {label}", SCORE, state=0, phase=rs.randrange(-5, 30), **o)

    # --- HealthFrame
    yield from stateful(HEALTH, "health", dict(counter=77))
    # animation counter and frame cycling
    cycles = {
        "step": dict(low=0, high=4, idx=1),
        "step from low": dict(low=2, high=5, idx=2),
        "wrap at end": dict(low=0, high=4, idx=4),
        "wrap at end shifted": dict(low=2, high=5, idx=5),
        "zero entry then wrap": dict(low=0, high=4, idx=1, zero_at=(2,)),
        "zero everywhere": dict(low=0, high=3, idx=3, zero_at=(0,)),
        "below range": dict(low=3, high=6, idx=-4),
        "empty set": dict(low=5, high=4, idx=4),
        "negative low": dict(low=-3, high=2, idx=-5),
        "single frame": dict(low=1, high=1, idx=1),
        "none": None,
    }
    for name, cyc in cycles.items():
        for counter, tick in ((0, 5), (5, 5), (3, 9), (9, 3)):
            yield frame_case(f"health cycle {name} counter={counter} tick={tick}", HEALTH, state=5, cycle=cyc,
                             counter=counter, tick=tick, p_health=40, phase=9, gs6c=0,
                             group=dict(g14=9, g18=99, ax=2, ay=5, count=3, value=40))
    for p_health in (0, 1, 33, 100, 150, 70000, -5 & M32):
        yield frame_case(f"health counter reload health={p_health}", HEALTH, state=5, counter=2, tick=7, p_health=p_health, phase=9,
                         gs6c=0, cycle=dict(low=0, high=4, idx=1), group=dict(g14=9, g18=99, ax=2, ay=5, count=3, value=p_health))
    # digit refresh: group value vs player health
    for label, p_health, value in (("changed", 55, 3), ("same", 55, 55), ("zero", 0, 12), ("triple", 100, 1)):
        for count in (1, 2, 3, 5):
            yield frame_case(f"health numbers {label} count={count}", HEALTH, state=5, p_health=p_health, counter=50, tick=3, phase=9, gs6c=0,
                             group=dict(g14=9, g18=99, ax=2, ay=5, count=count, value=value,
                                        digit_kinds=rs.choice((["full"], ["short"], ["full", "shifted"]))))
    yield frame_case("health run no player counter pending", HEALTH, state=5, player=False, counter=500, tick=3, phase=9, gs6c=0,
                     group=dict(g14=9, g18=99, ax=2, ay=5, count=3))
    for counter in (0, 3):
        yield frame_case(f"health run frame set missing counter={counter}", HEALTH, state=5, counter=counter, tick=9, phase=9, gs6c=0,
                         group=dict(g14=9, g18=99, ax=2, ay=5, count=3))
    # state 0 build
    for label, o in (("normal", {}), ("no player", dict(player=False)), ("player without stats", dict(player_stats=False)),
                     ("no heart set", dict(sets={"heart": None})), ("empty heart set", dict(sets={"heart": "empty"})),
                     ("no digit class", dict(digit_class=False)), ("digit create fails", dict(create=0)),
                     ("digit info allocation fails", dict(digit_info_fails=True)),
                     ("no health numbers", dict(sets={"health_numbers": None})), ("health 0", dict(health=0)),
                     ("health 100", dict(health=100)), ("health negative", dict(health=-3))):
        yield frame_case(f"health build {label}", HEALTH, state=0, phase=rs.randrange(-5, 30), **o)

    # --- WeaponFrame
    yield from stateful(WEAPON, "weapon", dict(stats=dict(weapon=1)), count=2)
    for weapon in (1, 2, 3, 4, 0, -1, 7):
        for cached in ("same", "other", "unset"):
            for kind in ("frame", None):
                if weapon > 3 and kind is None:
                    continue
                g5c = {"same": weapon, "other": (weapon + 1) & M32, "unset": 0xFFFFCFC7}[cached]
                yield frame_case(f"weapon id={weapon} cached={cached} sets={kind}", WEAPON, state=5, phase=9, gs6c=0,
                                 stats=dict(weapon=weapon & M32, ammo1=rs.randrange(1, 99), ammo2=rs.randrange(0, 99), ammo3=rs.randrange(0, 99)),
                                 sets={"pistol": kind, "magic": kind, "dynamite": kind},
                                 group=dict(g14=9, g18=99, ax=1, ay=4, count=2, g5c=g5c, value=rs.randrange(0, 99)))
    for weapon in (1, 2, 3, 5):
        for ammo in (0, 7, 15, 99, 123456, -4 & M32):
            if rs.random() < 0.4:
                continue
            for value_same in (False, True):
                st = dict(weapon=weapon, ammo1=ammo, ammo2=ammo ^ 1, ammo3=(ammo + 5) & M32)
                expected = {1: st["ammo1"], 2: st["ammo2"], 3: st["ammo3"]}.get(weapon)
                yield frame_case(f"weapon ammo shown weapon={weapon} ammo={ammo} same={value_same}", WEAPON, state=5, phase=9, gs6c=0,
                                 stats=st, group=dict(g14=9, g18=99, ax=1, ay=4, count=rs.choice((2, 3, 1)), g5c=weapon,
                                                      value=expected if (value_same and expected is not None) else 31337,
                                                      digit_kinds=rs.choice((["full"], ["short"], ["shifted"], [None]))))
    for weapon in (1, 2, 3, 4, 0):
        for cached in ("other", "unset"):
            g5c = {"other": (weapon + 1) & M32, "unset": 0xFFFFCFC7}[cached]
            yield frame_case(f"weapon animation swap id={weapon} cached={cached}", WEAPON, state=5, phase=9, gs6c=0, anims=True,
                             stats=dict(weapon=weapon, ammo1=rs.randrange(1, 99), ammo2=rs.randrange(0, 99), ammo3=rs.randrange(0, 99)),
                             group=dict(g14=9, g18=99, ax=1, ay=4, count=2, g5c=g5c, value=rs.randrange(0, 99)))
    for weapon in (1, 2, 3):
        yield frame_case(f"weapon build with animations id={weapon}", WEAPON, state=0, phase=rs.randrange(-5, 30), anims=True,
                         stats=dict(weapon=weapon))
    yield frame_case("weapon run no stats", WEAPON, state=5, info_stats=False, phase=9, gs6c=0, group=dict(g14=9, g18=99, count=2))
    for label, o in (("normal", {}), ("no player", dict(player=False)), ("player without stats", dict(player_stats=False)),
                     ("no pistol set", dict(sets={"pistol": None})), ("empty pistol set", dict(sets={"pistol": "empty"})),
                     ("no digit class", dict(digit_class=False)), ("digit create fails", dict(create=0)),
                     ("digit info allocation fails", dict(digit_info_fails=True)),
                     ("no small numbers", dict(sets={"small_numbers": None}))):
        yield frame_case(f"weapon build {label}", WEAPON, state=0, phase=rs.randrange(-5, 30), **o)

    # --- LivesFrame
    yield from stateful(LIVES, "lives", dict(), count=2)
    for lives in (0, 1, 2, 5, 9, 10, -1 & M32, -50 & M32):
        for value in (0, 1, 4, 8, 9, 3):
            if rs.random() < 0.5:
                continue
            for count in (1, 2):
                yield frame_case(f"lives stats={lives} shown={value} count={count}", LIVES, state=5, phase=9, gs6c=0,
                                 stats=dict(lives=lives), group=dict(g14=9, g18=99, ax=1, ay=3, count=count, value=value,
                                                                      digit_kinds=rs.choice((["full"], ["short"], ["dashed"], [None]))))
    yield frame_case("lives run no player", LIVES, state=5, player=False, phase=9, gs6c=0, group=dict(g14=9, g18=99, count=2))
    for mode in (1, 2, 3, 4, 5, 0, -4 & M32):
        for label, o in (("normal", {}), ("no head set", dict(sets={"lives": None})), ("empty head set", dict(sets={"lives": "empty"})),
                         ("no digit class", dict(digit_class=False)), ("digit create fails", dict(create=0)),
                         ("digit info allocation fails", dict(digit_info_fails=True))):
            if mode != 1 and label != "normal":
                continue
            yield frame_case(f"lives build mode={mode} {label}", LIVES, state=0, mode=mode, phase=rs.randrange(-5, 30), **o)

    for index, mode in enumerate((1, 2, 3, 4, 5)):
        yield frame_case(f"lives build with animations mode={mode}", LIVES, state=0, mode=mode, phase=rs.randrange(-5, 30), anims=True)
    yield frame_case("lives build with animations no head set", LIVES, state=0, mode=1, anims=True, sets={"lives": None})

    # --- TimerFrame
    for index, o in enumerate((dict(), dict(sets={"stopwatch": None}), dict(sets={"score_numbers": "short"}))):
        yield frame_case(f"timer build with animations {index}", TIMER, state=0, phase=rs.randrange(-5, 30), anims=True, **o)
    for state in (1, 4, 6, 0xB):
        yield frame_case(f"timer state {state:#x} does nothing", TIMER, state=state)
    yield frame_case("timer run without group", TIMER, state=5, group=None)
    for ms in (0, 1, 999, 1000, 61000, 3599999, 123456789, 0x7FFFFFFF, 0xFFFFFFFF):
        for value in (None, 0, 61):
            if rs.random() < 0.35:
                continue
            same = value is not None and value == ms // 1000
            yield frame_case(f"timer running ms={ms} shown={value}", TIMER, state=5, ms=ms, phase=9, gs6c=0,
                             flag40=rs.choice((0, 1, 0xFFFFFFFE)), stats=dict(s18=rs.randrange(0, 5)),
                             group=dict(g14=9, g18=99, ax=3, ay=4, count=rs.choice((3, 5, 10)), value=ms // 1000 if same else rs.randrange(1, 1 << 20),
                                        digit_kinds=rs.choice((["full"], ["short", "full"], [None, "full"], ["shifted"]))))
    for index, (label, scenario) in enumerate(phase_scenarios(rs)):
        ax, ay = anchors[index % len(anchors)]
        group = dict(scenario["group"], ax=ax, ay=ay, count=3)
        opts = dict(scenario)
        opts["group"] = group
        yield frame_case(f"timer running {label} ax={ax} ay={ay}", TIMER, state=5, ms=4321, rect=list(rect_values(rs))[index % 6], **opts)
    for ax, ay in ANCHORS:
        yield frame_case(f"timer running anchors {ax},{ay}", TIMER, state=5, ms=5000, phase=9, gs6c=0,
                         group=dict(g14=1, g18=50, ax=ax, ay=ay, count=3), rect=rs.choice(list(rect_values(rs))))
    # stopped timer (ms == 0): show / hide, with and without the stats timer field
    for flag40 in (0, 1, 0xFFFFFFFE, 0x80000001):
        for player, s18 in ((True, 0), (True, 7), (False, 0)):
            for count in (0, 1, 3):
                yield frame_case(f"timer stopped flag40={flag40:#x} player={player} s18={s18} count={count}", TIMER, state=5, ms=0,
                                 flag40=flag40, player=player, stats=dict(s18=s18), phase=9, gs6c=0,
                                 group=dict(g14=9, g18=99, ax=3, ay=4, count=count))
    for label, o in (("normal", {}), ("no chest set", dict(sets={"stopwatch": None})), ("empty stopwatch set", dict(sets={"stopwatch": "empty"})),
                     ("no score numbers", dict(sets={"score_numbers": None})), ("short digits", dict(sets={"score_numbers": "short"})),
                     ("dashed digits", dict(sets={"score_numbers": "dashed"}))):
        yield frame_case(f"timer build {label}", TIMER, state=0, phase=rs.randrange(-5, 30), **o)


def _init_cases(rs):
    sentinel = 0xFFFFCFC7

    def make(label, count, value, mode="ok", x=24, dx=11, y=-3, name_key="score_numbers", **o):
        def setup(env):
            scene = dict(o)
            scene["state"] = 0
            tokens = build(env, rs, scene)
            actor, info = tokens["actor"], tokens["info"]
            binder = env.object(0x60, "binder", words=rnd(rs, 24))
            env.put(binder + 0x04, rs.randrange(1, 4))
            env.put(binder + 0x08, small_signed(rs))
            env.put(binder + 0x0C, rs.randrange(3, 6))
            env.put(binder + 0x10, small_signed(rs))
            env.put(binder + 0x14, o.get("g14", rs.randrange(-30, 30)) & M32)
            env.put(binder + 0x18, o.get("g18", rs.randrange(-30, 60)) & M32)
            env.put(binder + 0x24, actor)
            env.put(info + 0x18, 0 if mode == "no-binder" else binder)
            number = env.object(0x60, "number-group", words=rnd(rs, 24))
            name = env.object(48, "digit-name", data=NAMES[name_key] + b"\0")
            tokens.update(number=number, name=name)
            return tokens

        return Case(label, INIT, setup, receiver=lambda t: t["number"],
                    arguments=(lambda t: env_get(t, "manager"), lambda t: t["actor"], value & M32, count & M32, dx & M32, x & M32, y & M32,
                               lambda t: t["name"]))

    def env_get(t, key):
        return t[key]

    # the manager global is read by the case through the token, as the frames do from G_MANAGER
    for count in (1, 2, 3, 8, 10):
        for value in (0, 5, 42, 1234567890, 0x7FFFFFFF, -1 & M32, -307 & M32, 0x80000000):
            if rs.random() < 0.45:
                continue
            yield make(f"init count={count} value={value:#x}", count, value)
    for count in (11, 12, 100, 0x7FFFFFFF):
        yield make(f"init count clamps to ten ({count})", count, 987654321)
    for count in (0, -1 & M32, -50 & M32):
        yield make(f"init count={count:#x} makes no digits", count, 55)
    for value in (sentinel, sentinel + 1, sentinel - 1):
        yield make(f"init value near sentinel {value:#x}", 4, value)
    yield make("init sentinel value keeps digits blank", 5, sentinel)
    yield make("init without binder returns zero", 3, 12, mode="no-binder")
    for key in ("score_numbers", "health_numbers", "small_numbers"):
        for kind in ("full", "short", "shifted", "dashed", "empty", None):
            yield make(f"init digit set {key} kind={kind}", 4, 9051, name_key=key, sets={key: kind})
    for value in (-1 & M32, -2147483648 & M32, 1999999999, 100):
        yield make(f"init dashed digit set value={value:#x}", 10, value, sets={"score_numbers": "dashed"})
    yield make("init no digit class returns zero", 3, 77, digit_class=False)
    yield make("init digit create fails", 3, 77, create=0)
    yield make("init digit info allocation fails", 3, 77, digit_info_fails=True)
    for from_call in (1, 5, 6, 9):
        yield make(f"init allocation fails from call {from_call}", 5, 123, small_alloc_fails=from_call)
    for _ in range(14):
        yield make("init random", rs.randrange(-2, 14), rs.randrange(0, 1 << 32), x=small_signed(rs), dx=small_signed(rs, 40),
                   y=small_signed(rs), name_key=rs.choice(("score_numbers", "health_numbers", "small_numbers")),
                   sets={"score_numbers": rs.choice(("full", "short", "shifted", "dashed")),
                         "small_numbers": rs.choice(("full", "short", "shifted", "dashed")),
                         "health_numbers": rs.choice(("full", "short", "shifted", "dashed"))})


def _readability_survivor_cases(rs):
    """Additional original-backed observations; existing case generation precedes these."""
    def cached_stats(env):
        tokens = build(env, rs, dict(state=0))
        # 0x4911fe publishes player stats even if the holder held another token.
        decoy = env.object(0xA0, "previous-cached-stats", words=rnd(rs, 40))
        env.put(tokens["info"] + 0x168, decoy)
        return tokens

    yield Case("weapon build replaces previous cached stats", WEAPON, cached_stats,
               arguments=(lambda t: t["actor"],))

    # 0x4c82bd..0x4c82e1: an active timed animation exposes the tick argument
    # through its remaining countdown, even when no animation frame advances.
    for function, name in ((SCORE, "score"), (WEAPON, "weapon"), (LIVES, "lives"), (TIMER, "timer")):
        def active_tick(env, function=function):
            tokens = build(env, rs, dict(state=5, tick=7, ms=4321, phase=9, gs6c=0,
                                        stats=dict(weapon=1), next_life=2000000000,
                                        group=dict(g14=9, g18=99, count=3, g5c=1)))
            actor = tokens["actor"]
            animation = make_anim(env, 19203 + function)
            frame = env.get(env.get(animation + 0x0C))
            env.put(actor + 0x18C, actor, animation, frame, 0, 0xFFFFFFFF, 1, 0,
                    0x1234ABCD, 0x76543210, 0x3F800000)
            return tokens

        yield Case(f"{name} active animation consumes global tick", function, active_tick,
                   arguments=(lambda t: t["actor"],))

    # The original image and animation loads are separate operations. Their
    # order is observable when an animation frame's +0x1c source aliases the
    # actor image-set field (+0x170): 0x4c8247 reads the newly published image.
    for function, weapon, animation_name in ((WEAPON, 1, b"GAME_INTERFACE_PISTOL"),
                                             (WEAPON, 3, b"GAME_INTERFACE_DYNAMITE"),
                                             (TIMER, 0, b"GAME_CYCLE100")):
        def aliased_load(env, function=function, weapon=weapon, animation_name=animation_name):
            options = dict(state=0 if function == TIMER else 5, tick=7, ms=4321,
                           phase=9, gs6c=0, stats=dict(weapon=weapon),
                           group=dict(g14=9, g18=99, count=2, g5c=0, value=31337))
            tokens = build(env, rs, options)
            actor = tokens["actor"]
            frame = actor + 0x154
            # A complete bounded frame with no motion/sound and an end marker.
            env.put(frame, 0, 0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0)
            frames = env.object(4, "aliased-animation-frames", words=[frame])
            animation = env.object(0x40, "aliased-animation", fill=0)
            env.put(animation + 0x0C, frames, 1)
            registry = make_registry(env, rs, {animation_name: animation})
            env.put(tokens["world"] + 0x2C, registry)
            env.put(actor + 0x18C, actor)
            return tokens

        yield Case(f"image precedes aliased animation load function={function:#x} weapon={weapon}",
                   function, aliased_load, arguments=(lambda t: t["actor"],))


_baseline_cases = cases


def cases(random_source):
    yield from _baseline_cases(random_source)
    yield from _readability_survivor_cases(random_source)
