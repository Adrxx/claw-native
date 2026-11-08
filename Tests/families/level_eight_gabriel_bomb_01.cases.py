"""Cases for level_eight_gabriel_bomb_01: Level 8 Gabriel bomb closure."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, sequence
from clawparity.world import animation, cstring, sprite, world  # noqa: F401

LOGIC = 0x4459D0
DISPATCH = 0x445AF0
CONSTRUCT = 0x445EF0
TRAJECTORY = 0x446130
BEGIN_EXPLOSION = 0x446340
UPDATE_EXPLOSION = 0x4463F0
UPDATE_FALL = 0x446490

RAND = 0x4A3050
OPERATOR_NEW = 0x4F63EC
REALLOC = 0x4A9070

TICK_STEP = 0x5430C4
LIT_FLAG = 0x532C0C
LIT_VALUE = 0x532C10
GAME = 0x53774C
REGISTRY = 0x537668
BOMB_VTABLE = 0x50DED4
ANIMATOR = 0x188

U32 = 0xFFFFFFFF
BOMB_SIZE = 0x198

# string keys of the resources the constructor looks up
SPRITE_KEY = "LEVEL_GABRIELBOMB"
FALL_KEY = "LEVEL_GABRIELBOMB_FALL"
EXPLODE_KEY = "LEVEL_GABRIELBOMB_EXPLODE"
SOUND_KEYS = ("LEVEL_GABRIELBOMB_SEXPLOSION1", "LEVEL_GABRIELBOMB_SEXPLOSION2", "LEVEL_GABRIELBOMB_SEXPLOSION3",
              "LEVEL_GABRIELBOMB_BOMBWHISTLE1")


def d(value):
    return struct.pack("<d", value)


def noise(random_source):
    return random_source.randrange(0x01010101, U32)


def scatter(env, random_source, base, size, skip=()):
    """Distinct non-zero words in a record, so that a store to a wrong offset changes the result."""
    for offset in range(0, size, 4):
        if offset not in skip:
            env.put(base + offset, noise(random_source))


def recorder(log, tag, snapshots=(), result=0, mutate=None):
    """A callback that appends what it saw to surviving memory and may change state behind the caller.

    Each entry is 0x40 bytes: tag, receiver, argument count, three arguments, then up to seven watched words.
    """
    def effect(env, call):
        index = env.get(log)
        at = log + 4 + index * 0x40
        arguments = list(call.arguments)[:3]
        env.put(at, tag, call.receiver, len(call.arguments), *(arguments + [0] * (3 - len(arguments))))
        for slot, address in enumerate(snapshots[:7]):
            env.put(at + 0x18 + 4 * slot, env.get(address))
        env.put(log, index + 1)
        if mutate:
            for address, value in mutate:
                env.put(address, value)
        return result
    return effect


def seed_log(env):
    return env.object(0x800, "observations", fill=0)


# ---------------------------------------------------------------- animator
def animator(env, owner, seq, mode, value, delay=3, param=0, armed=0):
    """The owner's animation cursor at owner+0x188, steered through its cheap paths (see 0x4c82a0).

    mode "none": no sequence, the cursor answers -1.
    mode "wait": a running delay without the repeat flag: answers +0x24, delay drops by one.
    mode "count": a running delay with the flag and param below it: answers +0x24.
    mode "done": delay expired and the cursor finished: answers +0x20, delay becomes 0.
    mode "done-zero": delay already 0 and the cursor finished: answers +0x20.
    """
    a = owner + ANIMATOR
    env.put(a, 0x4C4C4C4C)
    env.put(a + 4, owner)
    env.put(a + 8, 0 if mode == "none" else seq)
    env.put(a + 0x0C, 0x1111)
    env.put(a + 0x10, 0)
    env.put(a + 0x1C, armed)
    env.put(a + 0x20, 0x5A5A5A5A, 0x6B6B6B6B)
    env.put(a + 0x28, 0x3F800000)
    if mode == "wait":
        env.put(a + 0x14, delay, 0)
        env.put(a + 0x24, value)
    elif mode == "count":
        env.put(a + 0x14, delay, 1)
        env.put(a + 0x24, value)
        env.put(TICK_STEP, min(param, delay - 1))
    elif mode == "done":
        env.put(a + 0x14, delay, 1)
        env.put(a + 0x1C, armed or 1)
        env.put(a + 0x20, value)
        env.put(TICK_STEP, delay + param)
    elif mode == "done-zero":
        env.put(a + 0x14, 0, 1)
        env.put(a + 0x1C, armed or 7)
        env.put(a + 0x20, value)
    else:
        env.put(a + 0x14, delay, 0)
    return a


# ------------------------------------------------------------------ worlds
def lay_out_owner(env, random_source, owner, skip=()):
    protected = {0x0C, 0x38, 0x6C}.union(skip)
    for offset in range(0x40, 0x200, 4):
        if offset not in protected and not (ANIMATOR <= offset < ANIMATOR + 0x2C):
            env.put(owner + offset, noise(random_source))


def game_object(env, random_source, flag, limit):
    """The global at 0x53774c: 0 or an object whose +0x520 gates and +0x530 bounds the fall."""
    if flag is None:
        env.put(GAME, 0)
        return 0
    game = env.object(0x540, "game", fill=0)
    scatter(env, random_source, game, 0x540, skip=(0x520, 0x530))
    env.put(game + 0x520, flag)
    env.put(game + 0x530, limit & U32)
    env.put(GAME, game)
    return game


def bare_bomb(env, random_source, owner_words=None, state_words=None, vtable=None):
    """A bomb record filled by hand, for the entry points that run on an already built object."""
    w = world(env, owner_words=owner_words, state_words=state_words)
    owner, state = w["owner"], w["state"]
    lay_out_owner(env, random_source, owner, skip=set(owner_words or ()))
    for offset in range(0x40, 0x180, 4):
        if offset not in (state_words or {}):
            env.put(state + offset, noise(random_source))
    for offset, value in (state_words or {}).items():
        env.put(state + offset, value)
    this = env.object(BOMB_SIZE, "bomb", fill=0)
    scatter(env, random_source, this, BOMB_SIZE)
    env.put(this, vtable or 0)
    env.put(this + 0x0C, owner)
    env.put(this + 0x10, state)
    env.put(this + 0x12C, owner)
    env.put(this + 0x130, state)
    return {"this": this, "owner": owner, "state": state, "world": w}


def lit_sound(env, random_source, early=True, name="sound"):
    """A sound slot whose play request returns at once (the engine object at +0x10 -> +0x10 has no +0x78)."""
    sound = env.object(0x30, name, fill=0x66)
    engine = env.object(0x40, name + "-engine", fill=0x67)
    core = env.object(0x90, name + "-core", fill=0x68)
    env.put(sound + 0x10, engine)
    env.put(engine + 0x10, core)
    env.put(core + 0x78, 0 if early else 0x1234)
    return sound


# -------------------------------------------------------------- 0x4463f0
def update_explosion_setup(random_source, gate, mode, value, delay, armed, done_flag, flags, param=0):
    def setup(env):
        b = bare_bomb(env, random_source, owner_words={8: flags})
        owner, this = b["owner"], b["this"]
        game_object(env, random_source, gate, 0)
        env.put(TICK_STEP, param)
        seq = animation(env, 40)
        animator(env, owner, seq, mode, value, delay, param, armed)
        env.put(this + 0x18C, done_flag)
        return {"this": this, "owner": owner}
    return setup


def update_explosion_cases(random_source):
    def make(label, *args, **kw):
        return Case(f"update explosion {label}", UPDATE_EXPLOSION,
                    update_explosion_setup(random_source, *args, **kw), receiver=lambda t: t["this"])

    for gate in (None, 0, 0x5A5A5A5A):
        for flags in (0, U32, 0x7F):
            yield make(f"gate {gate} flags {flags:#x}", gate, "wait", 1, 3, noise(random_source),
                       noise(random_source), flags)
    index = 0
    for mode in ("none", "wait", "count", "done", "done-zero"):
        for value in (1, 2):
            for done_flag in (0, noise(random_source)):
                for armed in (0, 0x12345):
                    index += 1
                    yield make(f"{mode} value {value} done {done_flag:#x} armed {armed:#x}", 0, mode, value,
                               1 + 3 * (index % 2), armed, done_flag,
                               random_source.choice([0, 0x80, U32, noise(random_source)]),
                               param=random_source.randrange(0, 3))
    yield make("answer is minus one", 0, "wait", U32, 3, 0, 0, 0x80)
    yield make("answer is 0x100000001", 0, "wait", 0x100000001 & U32, 3, 0, 0, 0)


# -------------------------------------------------------------- 0x446490
def fall_setup(random_source, flag, rand_value, slots, lit, game, limit, speed, mode="wait", delay=3, value=7,
               logged=True):
    def setup(env):
        log = seed_log(env)
        vtable = env.object(0x40, "bomb-vtable", fill=0)
        b = bare_bomb(env, random_source, vtable=vtable)
        this, owner = b["this"], b["owner"]
        env.put(this + 0x190, flag)
        for index, present in enumerate(slots):
            env.put(this + 0x178 + 4 * index, lit_sound(env, random_source, name=f"slot{index}") if present else 0)
        env.put(LIT_FLAG, lit)
        env.put(LIT_VALUE, noise(random_source))
        game_object(env, random_source, game, limit)
        env.write(this + 0x70, d(speed))
        env.override(RAND, sequence(*rand_value))
        seq = animation(env, 40)
        animator(env, owner, seq, mode, value, delay, 0, noise(random_source))
        watch = (this + 0x190, owner + 8, this + 0x70)
        env.put(vtable + 0x2C, env.stub("bomb::explode", "thiscall", 0, recorder(log, 0x2C, watch, 0x2C2C2C2C)))
        return {"this": this, "owner": owner, "log": log}
    return setup


def fall_cases(random_source):
    def make(label, *args, **kw):
        return Case(f"update fall {label}", UPDATE_FALL, fall_setup(random_source, *args, **kw),
                    receiver=lambda t: t["this"])

    full = (True, True, True, True, True)
    # first call: which rand value picks which slot, with the slot present, absent, the light off
    for rand_value in (0, 1, 2, 5, 32767, 0xFFFFFFFF, 0xFFFFFFFE, 0x80000001):
        for lit in (0, 0x77):
            yield make(f"rand {rand_value:#x} lit {lit:#x}", 0, (rand_value,), full, lit, None, 0, 1.0)
    for missing, rand_value in enumerate((0xFFFFFFFE, 0xFFFFFFFF, 0, 1, 2)):  # the draw that picks each slot
        slots = tuple(i != missing for i in range(5))
        yield make(f"rand {rand_value:#x} slot {missing} missing", 0, (rand_value,), slots, 1, None, 0, 1.0)
    for flag in (1, 2, U32, noise(random_source)):
        yield make(f"already started {flag:#x}", flag, (1,), full, 1, None, 0, 1.0)
    # the fall limit: a bomb at or below the floor explodes
    for game, limit, speed in ((None, 0, 5.0), (0, 10, 5.0), (0, 10, 10.0), (0, 10, 10.5), (0, 10, 9.99999999),
                               (0, -10, -10.0), (0, -10, -9.5), (0, -10, -10.5), (0, 0, 0.0), (0, 0, -0.0),
                               (0, 0x7FFFFFFF, 2147483647.0), (0, 0x7FFFFFFF, 2147483647.5),
                               (0, 0x7FFFFFFF, 2147483646.5), (0, 0x80000000, -2147483648.0),
                               (0, 0x80000000, -2147483648.5), (0, 0x80000000, -2147483647.5),
                               (0, 1, float("nan")), (0, 1, float("inf")), (0, 1, float("-inf")),
                               (0, 1, 1e300), (0, 1, -1e300), (0, 5, 5.000000000000001), (0, 5, 4.999999999999999),
                               (0, 1 << 24, 16777217.0), (0, 1 << 24, 16777215.5), (0, 3, 3e-300)):
        for flag in ((0, 1) if limit in (10, 0) else (0,)):
            yield make(f"game {game} limit {limit:#x} speed {speed!r} flag {flag}", flag, (2,), full, 1, game,
                       limit, speed)
    # the game object stops the fall
    for blocked in (1, U32):
        for flag in (0, 1):
            yield make(f"game blocked {blocked:#x} flag {flag}", flag, (0,), full, 1, blocked, 3, 99.0)
    for mode in ("none", "wait", "count", "done", "done-zero"):
        yield make(f"animator {mode}", 1, (0,), full, 1, 0, 4, 5.5, mode=mode, delay=2, value=0x70)
    for _ in range(8):
        yield make("random", random_source.choice([0, 0, 1]), (random_source.randrange(0, 40000),),
                   tuple(random_source.random() < 0.7 for _ in range(5)), random_source.choice([0, 1]),
                   random_source.choice([None, 0, 0, 5]), random_source.randrange(-300, 300),
                   random_source.uniform(-300, 300), mode=random_source.choice(["none", "wait", "count"]))


# ----------------------------------------------------------- 0x446340
def registry_with(env, random_source, key, value, extra=False):
    """The state-name trie at 0x537668 holding one entry (a single self-linked node), or an empty trie."""
    root = 0
    if key is not None:
        text = cstring(env, key, "registry-key")
        node = env.object(20, "registry-node", fill=0)
        env.put(node, node, node, 0, text, value)
        root = node
    env.put(REGISTRY + 0x18, root)
    return root


def explosion_setup(random_source, registry, rand_value, slots, lit, anim, old_state, delay=40, owner_flags=None):
    def setup(env):
        log = seed_log(env)
        owner_words = {8: noise(random_source) if owner_flags is None else owner_flags}
        b = bare_bomb(env, random_source, owner_words=owner_words, state_words={0x1C: old_state})
        this, owner, state = b["this"], b["owner"], b["state"]
        registry_with(env, random_source, *registry)
        for index, present in enumerate(slots):
            env.put(this + 0x174 + 4 * (index - 2), lit_sound(env, random_source, name=f"slot{index}") if present else 0)
        env.put(this + 0x170, animation(env, delay) if anim else 0)
        env.put(LIT_FLAG, lit)
        env.put(LIT_VALUE, noise(random_source))
        env.override(RAND, sequence(*rand_value))
        a = owner + ANIMATOR
        env.put(a, 0x4C4C4C4C, owner, 0x7A7A7A7A)
        env.put(a + 0x0C, noise(random_source), noise(random_source))
        env.put(a + 0x14, noise(random_source), noise(random_source), noise(random_source), noise(random_source),
                noise(random_source), noise(random_source), noise(random_source), noise(random_source))
        env.put(owner + 0x190, noise(random_source))
        return {"this": this, "owner": owner, "state": state, "log": log}
    return setup


def begin_explosion_cases(random_source):
    def make(label, *args, **kw):
        return Case(f"begin explosion {label}", BEGIN_EXPLOSION, explosion_setup(random_source, *args, **kw),
                    receiver=lambda t: t["this"])

    live = ("LS_EXPLODING", 0x2468)
    full = (True, True, True, True, True)
    for registry in (live, ("LS_EXPLODING", 0), ("LS_EXPLODING", U32), ("LS_OTHER", 0x1357), (None, 0)):
        for anim in (True, False):
            yield make(f"registry {registry} anim {anim}", registry, (1,), full, 1, anim, noise(random_source))
    for rand_value in (0, 1, 2, 5, 32767, 0xFFFFFFFF, 0xFFFFFFFE, 0x80000001):
        for lit in (0, 0x91):
            signed = rand_value - (1 << 32) if rand_value & 0x80000000 else rand_value
            index = abs(signed) % 3 * (-1 if signed < 0 else 1)  # the slot at +0x170 holds the animation itself
            yield make(f"rand {rand_value:#x} lit {lit:#x}", live, (rand_value,), full, lit, index != -1,
                       noise(random_source))
    for missing in (0, 1, 2):
        slots = tuple(i != missing + 1 for i in range(5))
        for rand_value in (0, 1, 2):
            yield make(f"rand {rand_value} slot {missing} missing", live, (rand_value,), slots, 1, True, 5)
    for flags in (0, U32, 4, 0x80000000):
        yield make(f"owner flags {flags:#x}", live, (0,), full, 1, True, 9, owner_flags=flags)
    for delay in (1, 7, 0x7FFFFFFF):
        yield make(f"frame delay {delay}", live, (1,), full, 0, True, 3, delay=delay)
    for _ in range(4):
        yield make("random", live, (random_source.randrange(0, 40000),),
                   tuple(random_source.random() < 0.7 for _ in range(5)), random_source.choice([0, 1]),
                   random_source.choice([True, False]), noise(random_source),
                   delay=random_source.randrange(1, 300))


# ----------------------------------------------------------- 0x446130
NAN = struct.unpack("<d", struct.pack("<Q", 0x7FF8000000001234))[0]
NEG_NAN = struct.unpack("<d", struct.pack("<Q", 0xFFF8000000005678))[0]


def trajectory_setup(random_source, argument, x, y, z, g1, g3):
    def setup(env):
        this = env.object(0x100, "bomb", fill=0)
        scatter(env, random_source, this, 0x100)
        env.write(this + 0x38, d(g1))
        env.write(this + 0x48, d(g3))
        env.write(this + 0x68, d(x))
        env.write(this + 0x70, d(y))
        env.write(this + 0x78, d(z))
        return {"this": this}
    return setup


def trajectory_cases(random_source):
    def make(label, argument, x=0.0, y=0.0, z=0.0, g1=0.0, g3=0.0):
        return Case(f"trajectory {label}", TRAJECTORY, trajectory_setup(random_source, argument, x, y, z, g1, g3),
                    receiver=lambda t: t["this"], arguments=(argument & U32,))

    # ordinary throws, each axis alone and together
    for argument in (100, -100, 7, 3000):
        for z in (0.0, 55.5, -55.5):
            for g1, g3 in ((0.0, 0.0), (-250.5, 70.25)):
                yield make(f"throw {argument} z {z} g {g1},{g3}", argument, 12.5, 3.0, z, g1, g3)
    # the aim is already reached, or nearly: the speed falls under the threshold
    yield make("zero distance", 0)
    yield make("zero distance with offsets", 0, 5.0, 6.0, 0.0, 9.0, 8.0)
    for g1 in (1e9, 1e10, 3e8, 5e7, -1e9):
        for argument in (1, -2):
            yield make(f"cancelling gravity {g1:g} argument {argument}", argument, 0.0, 0.0, 0.0, g1, 0.0)
    for g3 in (1e9, 1e10, 3e8):
        yield make(f"cancelling depth gravity {g3:g}", 0, 0.0, 0.0, -1.0, 0.0, g3)
    # rounding of (argument + x) - x in the floating point unit
    for x in (0.0, 1e15, 2.0**53, 3e17, -3e17, 1e19, 1.5e22, 123456789012345.678, -9007199254740993.0, 1e300):
        for argument in (1, 100001):
            yield make(f"rounding x {x!r} argument {argument}", argument, x, 2.0, 40.0, 5.0, 2.0)
    # y drops out unless it is not finite
    for y in (0.0, -0.0, 1e300, -4.25, float("inf"), float("-inf"), NAN, NEG_NAN):
        yield make(f"y {y!r}", 50, 1.0, y, 20.0, 3.0, 4.0)
    for z in (float("inf"), float("-inf"), NAN, 1e300, -1e300, 1e-300, 5e-324):
        yield make(f"z {z!r}", 50, 1.0, 1.0, z, 3.0, 4.0)
    for g in (float("inf"), NAN, 1e154, 1e160, -1e160):
        yield make(f"g1 {g!r}", 50, 1.0, 1.0, 9.0, g, 4.0)
        yield make(f"g3 {g!r}", 50, 1.0, 1.0, 9.0, 3.0, g)
    for argument in (0x7FFFFFFF, -0x80000000, 0x40000000, -0x40000001):
        yield make(f"argument {argument}", argument, 1.0, 1.0, 9.0, 3.0, 4.0)
    for _ in range(25):
        yield make("random", random_source.randrange(-5000, 5000), random_source.uniform(-1e4, 1e4),
                   random_source.uniform(-1e4, 1e4), random_source.uniform(-1e4, 1e4),
                   random_source.uniform(-500, 500), random_source.uniform(-500, 500))
    for _ in range(8):
        yield make("random wide", random_source.randrange(-200000, 200000),
                   random_source.uniform(-1, 1) * 10 ** random_source.randrange(0, 20),
                   random_source.uniform(-1, 1), random_source.uniform(-1, 1) * 10 ** random_source.randrange(0, 6),
                   random_source.uniform(-1, 1) * 10 ** random_source.randrange(0, 10),
                   random_source.uniform(-1, 1) * 10 ** random_source.randrange(0, 10))


# ------------------------------------------------------------ 0x445ef0
def sprite_sheet(env, random_source, first, last, frames=4):
    """A sprite resource whose frames carry distinct rectangles at +0x18 (x, y, width, height)."""
    resource = env.object(0x6C, "bomb-sprite", fill=0)
    table = env.object(4 * frames, "bomb-frames", fill=0)
    env.put(resource + 0x14, table)
    env.put(resource + 0x64, first, last)
    chosen = []
    for index in range(frames):
        frame = env.object(0x40, "bomb-frame", fill=0x4B)
        rect = (random_source.randrange(-300, 300), random_source.randrange(-300, 300),
                random_source.randrange(1, 90), random_source.randrange(1, 90))
        env.put(frame + 0x18, *(r & U32 for r in rect))
        env.put(table + 4 * index, frame)
        chosen.append(frame)
    return resource, chosen


def build_world(env, random_source, anims=(True, True), sounds=(True, True, True, True), sprite_mode="hit",
                preset=False, owner_104=0, owner_flags=None, first=1, last=2, bucket_count=17, owner_extra=None, stale=True, state_id=None,
                real_animations=False):
    """The level the constructor reads: sprite, animation and sound maps, the owner and its state."""
    owner_words = {
        8: noise(random_source) & ~0x10 if owner_flags is None else owner_flags,
        0x40: noise(random_source),
        0x4C: noise(random_source),
        0x50: noise(random_source),
        0x64: 0,
        0x104: owner_104,
        0x148: noise(random_source) & 0x3FF,
        0x14C: noise(random_source) & 0x3FF,
        0x158: noise(random_source) & 0xFF,
        0x164: noise(random_source),
        0xCC: noise(random_source),
        0xC8: noise(random_source),
    }
    owner_words.update(owner_extra or {})
    state_words = {0x1C: noise(random_source) if state_id is None else state_id, 0x2C: 0, 0x30: 0, 0x34: 0, 0x38: 0}
    handles = {}
    animations = {}
    for key, present in zip((FALL_KEY, EXPLODE_KEY), anims):
        handles[key] = animation(env, 20 + 7 * len(handles)) if real_animations else env.object(0x20, key, fill=0x70 + len(handles))
        if present:
            animations[key] = handles[key]
    sounds_map = {}
    for key, present in zip(SOUND_KEYS, sounds):
        handles[key] = env.object(0x20, key, fill=0x80 + len(handles))
        if present:
            sounds_map[key] = handles[key]
    sprites = {}
    sheet, frames = None, []
    if sprite_mode != "miss":
        lo, hi = (first, last) if sprite_mode == "hit" else (last + 1, last)
        sheet, frames = sprite_sheet(env, random_source, lo, hi)
        sprites[SPRITE_KEY] = sheet
    w = world(env, owner_words=owner_words, state_words=state_words, bucket_count=bucket_count,
              resources={"sprites": sprites, "animations": animations, "sounds": sounds_map})
    owner = w["owner"]
    stale_frame = env.object(0x40, "stale-frame", fill=0x2D)
    env.put(stale_frame + 0x18, 11, 22, 33, 44)
    env.put(owner + 0x174, stale_frame if stale else 0)
    if preset:
        env.put(owner + 0x170, 0xDEAD5EED)
        env.put(owner + 0x16C, 0xDEAD5EEE)
    else:
        env.put(owner + 0x170, 0)
        env.put(owner + 0x16C, 0xBEEF0001)
    service = env.object(0x40, "level-object-service", fill=0)
    env.put(service + 8, owner)
    env.put(w["state"] + 0x0C, service)
    env.put(0x537E88, owner)
    return {"owner": owner, "state": w["state"], "world": w, "handles": handles, "sheet": sheet, "frames": frames}


def construct_setup(random_source, fill=0x5C, **options):
    def setup(env):
        b = build_world(env, random_source, **options)
        this = env.object(BOMB_SIZE, "new-bomb", fill=fill)
        b["this"] = this
        return b
    return setup


def construct_cases(random_source):
    def make(label, fill=0x5C, **kw):
        return Case(f"construct {label}", CONSTRUCT, construct_setup(random_source, fill=fill, **kw),
                    receiver=lambda t: t["this"], arguments=(lambda t: t["owner"],))

    # which resources exist: all, none, each one alone and each one missing
    yield make("everything present")
    yield make("nothing present", anims=(False, False), sounds=(False,) * 4)
    for index in range(2):
        yield make(f"only animation {index}", anims=tuple(i == index for i in range(2)), sounds=(False,) * 4)
        yield make(f"animation {index} missing", anims=tuple(i != index for i in range(2)))
    for index in range(4):
        yield make(f"only sound {index}", anims=(False, False), sounds=tuple(i == index for i in range(4)))
        yield make(f"sound {index} missing", sounds=tuple(i != index for i in range(4)))
    # the sprite: found with a usable frame range, found with an empty range, not found, already set
    for mode in ("hit", "empty", "miss"):
        for preset in (False, True):
            yield make(f"sprite {mode} preset {preset}", sprite_mode=mode, preset=preset)
    for mode in ("empty", "miss"):
        yield make(f"sprite {mode} without stale frame", sprite_mode=mode, stale=False)
    yield make("sprite preset without stale frame", preset=True, stale=False)
    for first, last in ((0, 0), (0, 3), (3, 3), (2, 1), (3, 2)):
        yield make(f"sprite frames {first}..{last}", first=first, last=last)
    for value in (0, 1, 0x7FFFFFFF, 0x80000000, U32):
        yield make(f"owner 0x104 is {value:#x}", owner_104=value)
    for flags in (0, U32, 0x40, 0x2020, 0x20000):
        yield make(f"owner flags {flags:#x}", owner_flags=flags)
    for buckets in (1, 3, 64):
        yield make(f"resource buckets {buckets}", bucket_count=buckets)
    for fill in (0x00, 0xA7):
        yield make(f"over fill {fill:#x}", fill=fill)
    for _ in range(4):
        yield make("random", fill=random_source.randrange(1, 256),
                   anims=tuple(random_source.random() < 0.6 for _ in range(2)),
                   sounds=tuple(random_source.random() < 0.6 for _ in range(4)),
                   sprite_mode=random_source.choice(["hit", "hit", "empty", "miss"]),
                   preset=random_source.random() < 0.3, owner_104=random_source.choice([0, noise(random_source)]),
                   first=random_source.randrange(0, 3), last=random_source.randrange(0, 4),
                   stale=random_source.random() < 0.7, bucket_count=random_source.randrange(1, 40),
                   owner_extra={0x148: noise(random_source) & 0x3FF})


# ------------------------------------------------------------ 0x445af0
PRIMARY, SECONDARY, TERTIARY = 0x537758, 0x534910, 0x538428


def error_receiver(env, mode):
    """The object an out-of-memory report goes to (see 0x4db4d0): mode 4 and 1 store a halfword, 0 does nothing."""
    receiver = env.object(0x20, "error-receiver", fill=0x35)
    env.put(receiver + 0x0C, mode)
    return receiver


def lay_table(env, random_source, log, base, tag, lo, hi, stride, entries, default, mode=4, noisy_count=True):
    """One state-to-handler table the way the original keeps it: bounds, entry array, stride, default cell.

    entries maps a state to True (a recording handler), default is True (recording handler) or False (empty cell).
    """
    count = hi - lo + 1
    data = env.object(max(count, 1) * stride, f"table-{tag}", fill=0)
    for state in entries:
        env.put(data + (state - lo) * stride, env.stub(f"handler-{tag}-{state}", "thiscall", 0,
                                                       recorder(log, (tag << 16) + (state & 0xFFFF), (0x537778,),
                                                                0x3000 + (state & 0xFF))))
        for extra in range(4, stride, 4):
            env.put(data + (state - lo) * stride + extra, noise(random_source))
    cell = env.object(8, f"default-{tag}", fill=0)
    if default:
        env.put(cell, env.stub(f"default-{tag}", "thiscall", 0, recorder(log, (tag << 16) + 0xDDDD, (0x537778,), 0x4000)))
    env.put(base + 4, error_receiver(env, mode))
    env.put(base + 8, lo & U32, hi & U32, data, cell, stride)
    env.put(base + 0x1C, noise(random_source) if noisy_count else 0)
    env.put(base + 0x20, noise(random_source) if noisy_count else 0)
    return data


def dispatch_setup(random_source, state, primary, secondary=None, tertiary=None):
    """primary/secondary/tertiary: dict(lo, hi, stride, entries, default, mode)."""
    def setup(env):
        log = seed_log(env)
        this = env.object(BOMB_SIZE, "bomb", fill=0x5C)
        scatter(env, random_source, this, BOMB_SIZE)
        env.put(0x544B4C, cstring(env, "OUT OF MEMORY", "message"))
        env.put(0x544B14, noise(random_source))
        for base, tag, spec in ((PRIMARY, 1, primary), (SECONDARY, 2, secondary), (TERTIARY, 3, tertiary)):
            spec = spec or dict(lo=0, hi=0, stride=4, entries={}, default=True)
            lay_table(env, random_source, log, base, tag, spec["lo"], spec["hi"], spec["stride"],
                      spec.get("entries", {}), spec.get("default", True), spec.get("mode", 4))
        return {"this": this, "log": log}
    return setup


def dispatch_cases(random_source):
    def make(label, state, primary, **kw):
        return Case(f"dispatch {label}", DISPATCH, dispatch_setup(random_source, state, primary, **kw),
                    receiver=lambda t: t["this"], arguments=(state & U32,))

    # in range: the handler is picked by (state - lo) * stride
    for lo, hi, stride in ((0, 9, 4), (1, 5, 8), (-3, 4, 12), (-100, -90, 4), (0x7FFFFFF0, 0x7FFFFFFF, 8),
                           (3, 3, 4), (0x40, 0x4F, 16)):
        full = {state: True for state in range(lo, hi + 1)} if hi - lo < 20 else {}
        picks = sorted({lo, hi, (lo + hi) // 2, lo + 1 if lo + 1 <= hi else lo})
        for state in picks:
            yield make(f"in range {lo}..{hi} stride {stride} state {state}", state,
                       dict(lo=lo, hi=hi, stride=stride, entries=full, default=True))
    # in range, but the entry is empty: the base class table takes over
    base = dict(lo=-2, hi=6, stride=8, entries={-2: True, 0: True, 6: True}, default=True)
    for state in (-1, 1, 5):
        for secondary in (dict(lo=0, hi=9, stride=4, entries={1: True, 5: True, -1 + 1: True}, default=True),
                          dict(lo=0, hi=9, stride=4, entries={}, default=True)):
            yield make(f"empty entry {state}", state, base, secondary=secondary,
                       tertiary=dict(lo=-2, hi=12, stride=4, entries={s: True for s in range(-2, 13)}))
    # out of range: the table grows (realloc keeps the old entries)
    for state in (-4, -3, 7, 8, 40, -50, 300, -300):
        yield make(f"grow to {state}", state, dict(lo=-2, hi=6, stride=8, entries={-2: True, 0: True, 6: True}, default=True),
                   secondary=dict(lo=-100, hi=100, stride=4, entries={state: True} if -100 <= state <= 100 else {}),
                   tertiary=dict(lo=-400, hi=400, stride=4, entries={state: True}))
    for _ in range(6):
        lo = random_source.randrange(-50, 50)
        hi = lo + random_source.randrange(0, 12)
        stride = random_source.choice([4, 8, 12])
        state = random_source.randrange(lo - 6, hi + 7)
        entries = {s: True for s in range(lo, hi + 1) if random_source.random() < 0.7}
        yield make(f"random {lo}..{hi} state {state}", state, dict(lo=lo, hi=hi, stride=stride, entries=entries,
                                                                    default=random_source.random() < 0.5),
                   secondary=dict(lo=lo - 8, hi=hi + 8, stride=4, entries={s: True for s in range(lo - 8, hi + 9)}),
                   tertiary=dict(lo=lo - 8, hi=hi + 8, stride=4, entries={s: True for s in range(lo - 8, hi + 9)}))


# -------------------------------------------------------------- 0x4459d0
def collision_plane(env, random_source, w, tile, answer, log, width=64, height=64, shift=3):
    """The tile plane the freshly built bomb is checked against (see its first update).

    tile: -1 / 0xEEEEEEEE for an empty cell, otherwise a tile number whose handler answers `answer`."""
    collision = w["collision"]
    plane = env.object(0xA0, "tile-plane", fill=0)
    columns, rows = width >> shift, height >> shift
    row_table = env.object(4 * rows + 4, "tile-rows", fill=0)
    tiles = env.object(4 * rows * columns + 4, "tiles", fill=0)
    for row in range(rows):
        env.put(row_table + 4 * row, row * columns)
    for index in range(rows * columns):
        env.put(tiles + 4 * index, tile & U32)
    env.put(plane + 0x20, tiles, row_table)
    env.put(plane + 0x30, width, height)
    env.put(plane + 0x8C, shift, shift)
    env.put(collision + 0x5C, plane)
    handlers = env.object(4 * 16, "tile-handlers", fill=0)
    handler = env.object(0x10, "tile-handler", fill=0)
    vtable = env.object(0x40, "tile-vtable", fill=0)
    env.put(handler, vtable)
    env.put(vtable + 0x20, env.stub("tile::test", "thiscall", 2, recorder(log, 0x20, (), answer)))
    for index in range(16):
        env.put(handlers + 4 * index, handler)
    env.put(collision + 0x4C, handlers)
    return plane


def logic_new_setup(random_source, tile=-1, answer=0, registry=("LS_FALLING", 0x777), **options):
    def setup(env):
        log = seed_log(env)
        b = build_world(env, random_source, state_id=0, real_animations=True, **options)
        registry_with(env, random_source, *registry)
        collision_plane(env, random_source, b["world"], tile, answer, log)
        return {"owner": b["owner"], "state": b["state"], "log": log}
    return setup


def logic_vtable_setup(random_source, state_id, tag):
    def setup(env):
        log = seed_log(env)
        w = world(env, state_words={0x1C: state_id})
        owner, state = w["owner"], w["state"]
        scatter(env, random_source, owner, 0x40)  # not the fields in use
        env.put(owner + 0x38, U32)
        env.put(owner + 0x0C, w["world"])
        env.put(owner + 0x6C, state)
        bomb = env.object(0x40, "live-bomb", fill=0x58)
        vtable = env.object(0x60, "live-vtable", fill=0)
        env.put(bomb, vtable)
        env.put(bomb + 0x10, state)
        env.put(state + 0x18, bomb)
        for slot in (0x1C, 0x20):
            env.put(vtable + slot, env.stub(f"bomb::slot{slot:x}", "thiscall", 0,
                                           recorder(log, slot, (state + 0x18, state + 0x1C), 0x1000 + slot)))
        return {"owner": owner, "state": state, "log": log, "bomb": bomb}
    return setup


def logic_name_setup(random_source, state_id, lo, hi, stride, names=True):
    def setup(env):
        log = seed_log(env)
        w = world(env, state_words={0x1C: state_id})
        owner, state = w["owner"], w["state"]
        bomb = env.object(0x40, "live-bomb", fill=0x58)
        vtable = env.object(0x60, "live-vtable", fill=0)
        env.put(bomb, vtable)
        env.put(bomb + 0x10, state)
        env.put(state + 0x18, bomb)
        for slot in (4, 8, 0xC):
            env.put(vtable + slot, env.stub(f"bomb::slot{slot:x}", "thiscall", 1,
                                           recorder(log, slot, (state + 0x1C,), 0x2000 + slot)))
        data = env.object((hi - lo + 1) * stride, "state-names", fill=0)
        for index in range(hi - lo + 1):
            env.put(data + index * stride, cstring(env, f"STATE_{lo + index}_{random_source.randrange(100, 999)}", "name"))
            for extra in range(4, stride, 4):
                env.put(data + index * stride + extra, noise(random_source))
        cell = env.object(8, "default-name", fill=0)
        env.put(cell, cstring(env, "UNKNOWN", "default-name"))
        env.put(0x537698 + 4, error_receiver(env, 4))
        env.put(0x537698 + 8, lo & U32, hi & U32, data, cell, stride)
        env.put(0x537698 + 0x1C, 0, 0)
        return {"owner": owner, "state": state, "log": log, "bomb": bomb}
    return setup


def logic_cases(random_source):
    def make(label, setup):
        return Case(f"logic {label}", LOGIC, setup, arguments=(lambda t: t["owner"],))

    # state 0: the bomb is built and started
    yield make("new bomb", logic_new_setup(random_source))
    for tile in (-1, 0xEEEEEEEE, 5, 0x10002):
        for answer in (0, 1, 2):
            yield make(f"new bomb tile {tile:#x} answer {answer}", logic_new_setup(random_source, tile, answer))
    for registry in (("LS_FALLING", 0), ("LS_OTHER", 4), (None, 0)):
        yield make(f"new bomb registry {registry}", logic_new_setup(random_source, registry=registry))
    for sprite_mode in ("hit", "miss"):
        yield make(f"new bomb sprite {sprite_mode}", logic_new_setup(random_source, sprite_mode=sprite_mode))
    yield make("new bomb without animations", logic_new_setup(random_source, anims=(True, False)))
    # the running states
    for state_id in (0x1D, 0x1E, 1000):
        yield make(f"state {state_id}", logic_vtable_setup(random_source, state_id, state_id))
    for state_id in (1, 2, 5, 7, 9, 0x1C, 0x1F, 0x20, 999, 1001):
        lo, hi = (1, 40) if state_id < 100 else (900, 1100)
        yield make(f"other state {state_id}", logic_name_setup(random_source, state_id, lo, hi, 4))
    for stride in (8, 12):
        yield make(f"other state stride {stride}", logic_name_setup(random_source, 6, 3, 9, stride))
    for _ in range(3):
        lo = random_source.randrange(-5, 5)
        hi = lo + random_source.randrange(3, 9)
        yield make("other state random", logic_name_setup(random_source, random_source.choice(
            [s for s in range(lo, hi + 1) if s not in (0, 0x1D, 0x1E, 1000)]), lo, hi, random_source.choice([4, 8])))


def cases(random_source):
    yield from logic_cases(random_source)
    yield from dispatch_cases(random_source)
    yield from construct_cases(random_source)
    yield from trajectory_cases(random_source)
    yield from begin_explosion_cases(random_source)
    yield from update_explosion_cases(random_source)
    yield from fall_cases(random_source)
