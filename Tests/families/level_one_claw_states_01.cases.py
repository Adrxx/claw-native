"""Cases for level_one_claw_states_01: Level 1 Claw movement and pose state callbacks batch 1.

Every case builds a small but real world around the Claw object: an animation manager with a real
name map, animation sets and frames, a tile plane whose tile types are fixtures with controlled
answers, an input-flag object, the physics integrator block and the saved state record. Deterministic
cases select each branch through explicit options; the random source only varies positions, timers,
junk in unread fields and the like.
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import sequence

# owned functions
CLIMB, TEETER, WALK_L, WALK_R = 0x4170F0, 0x417480, 0x417DD0, 0x417F20
STAND_FALL, LOOKUP, PHYS_A, PHYS_B, PHYS_C, PHYS_D = 0x418790, 0x4197E0, 0x4198D0, 0x419C80, 0x419FD0, 0x41A490

RAND = 0x4A3050

# globals
G_INPUT, G_DT, G_MS, G_WEAPON, G_FPOFF, G_RESULT = 0x537204, 0x53720C, 0x5430C4, 0x534EAC, 0x534E58, 0x544E8C
G_INTEG = 0x534DB8
G_GAME, G_SND_A, G_SND_B = 0x53C9A4, 0x532C0C, 0x532C10

CELL_SHIFT = 3
GRID = 64                      # 64 x 64 cells of 8 pixels
PIXELS = GRID << CELL_SHIFT
AIR, AIR2 = 0xFFFFFFFF, 0xEEEEEEEE

NAMES = ("CLAW_CLIMB", "CLAW_TEETER", "CLAW_WALK", "CLAW_STAND", "CLAW_LOOKUP", "CLAW_FALL",
         "CLAW_JUMP", "CLAW_STANDX", "CLAW_WALKER")

HALF = 5   # tile type answering 1 in the upper half of the tile and 0 below it


def double(value):
    return struct.pack("<d", value)


def words(env, address, values):
    env.put(address, *values)


def junk(r, count, low=0x101, high=0x7FFF):
    return [r.randrange(low, high) for _ in range(count)]


def string_hash(name):
    h = 0
    for ch in name.encode():
        h = (h * 0x21 + (ch if ch < 128 else ch - 256)) & 0xFFFFFFFF
    return h


def make_map(env, header, entries, buckets=3):
    """A string-keyed map in the layout of the original: hash table pointer at +4, bucket count at +8."""
    if not entries:
        env.put(header + 4, 0, 1)
        return
    table = env.object(buckets * 4, "map-table", fill=0)
    for name, value in entries.items():
        h = string_hash(name)
        slot = table + (h % buckets) * 4
        key = env.object(len(name) + 1, "map-key", data=name.encode() + b"\0")
        assoc = env.object(16, "map-assoc", words=[env.get(slot), h, key, value])
        env.put(slot, assoc)
    env.put(header + 4, table, buckets)


def make_animation_set(env, r, index, frames=3, delay=6, flags=0):
    frame_objects = []
    for i in range(frames):
        frame = env.object(0x40, "frame", fill=0)
        env.put(frame + 0x04, flags)
        env.put(frame + 0x18, delay + i)
        env.put(frame + 0x1C, 1 + (index + i) % 5)
        env.put(frame + 0x20, 0x300 + 16 * index + i)
        env.put(frame + 0x24, 0x400 + 16 * index + i)
        frame_objects.append(frame)
    array = env.object(4 * frames, "frames", words=frame_objects)
    animation = env.object(0x40, "animation-set", fill=0)
    env.put(animation + 0x0C, array)
    env.put(animation + 0x10, frames)
    return animation


def set_tile(tiles, x, y, value):
    if 0 <= x < PIXELS and 0 <= y < PIXELS:
        tiles[(y >> CELL_SHIFT) * GRID + (x >> CELL_SHIFT)] = value


def build(env, r, o):
    """Build the world for one case. `o` holds the options; returns the tokens."""
    g = o.get
    x = g("x", 256 + r.randrange(-20, 21))
    y = g("y", 8 * r.randrange(24, 31) + 3)   # feet row (y + 61) falls on a tile boundary
    state = g("state", 1)

    # ---- animation sets and name map -------------------------------------------------------
    sets = {}
    for i, name in enumerate(NAMES):
        sets[name] = make_animation_set(env, r, i, frames=3, delay=g("delay", 6), flags=g("frame_flags", 0))
    listed = {n: sets[n] for n in NAMES if n in g("maps", NAMES)}
    anim_manager = env.object(0x40, "animation-manager", fill=0)
    make_map(env, anim_manager + 0x10, listed)
    second_manager = env.object(0x40, "second-manager", fill=0)
    make_map(env, second_manager + 0x10, {})
    spawn_leaf = env.object(0x40, "spawn-leaf", fill=0)
    make_map(env, spawn_leaf + 0x10, {})
    spawn_mid = env.object(0x40, "spawn-mid", words=[0] * 5 + [spawn_leaf])
    spawn_root = env.object(0x40, "spawn-root", fill=0)
    env.put(spawn_root + 0x0C, spawn_mid)
    # spawn_mid + 0x14 -> leaf, root + 0xC -> mid

    # ---- tile plane and physics ------------------------------------------------------------
    types = []
    answers = (0, 1, 2, 3, 4, None)
    holder = {}

    def make_effect(answer):
        def effect(env_, call):
            if holder.get("clear"):
                env_.put(holder["state"], 0)   # the facing word changes behind the caller's back
            if answer is None:
                return 1 if call.arguments[1] < 4 else 0
            return answer
        return effect

    for index, answer in enumerate(answers):
        effect = make_effect(answer)
        method = env.stub(f"tile-type-{index}", "thiscall", 2, effect)
        vtable = env.object(0x40, "tile-vtable", fill=0)
        env.put(vtable + 0x20, method)
        types.append(env.object(8, "tile-type", words=[vtable, 0x77 + index]))
    type_array = env.object(4 * len(types), "tile-types", words=types)
    base = {"air": AIR, "air2": AIR2, "zero": 0x1230000}[g("base", "air")]
    tiles = [base] * (GRID * GRID)

    def paint(px, py, attr_type):
        set_tile(tiles, px, py, (0xABCD0000 if attr_type % 2 else 0x13570000) | attr_type)

    feet = y + 60 + 1
    for px0, py0, px1, py1, attr_type in g("rects", ()):
        for py in range(py0, py1 + 1, 4):
            for px in range(px0, px1 + 1, 4):
                paint(x + px, y + py, attr_type)
    for dx, attr_type in zip((-16, -4, 8, 16), g("probes", ())):
        if attr_type is not None:
            paint(x + dx, feet, attr_type)
    floor = g("floor")
    if floor is not None:
        gap, attr_type = floor
        for py in range(feet + gap, feet + gap + 24, 4):
            for px in range(x - 80, x + 81, 4):
                paint(px, py, attr_type)
    ladder = g("ladder")
    if ladder:
        for py in range(y - 90, y + 100, 4):
            for px in range(x - 6, x + 7, 4):
                paint(px, py, 3)
    tile_array = env.object(4 * len(tiles), "tiles", words=tiles)
    row_offsets = env.object(4 * GRID, "tile-rows", words=[row * GRID for row in range(GRID)])
    plane = env.object(0xA0, "plane", fill=0)
    env.put(plane + 0x20, tile_array, row_offsets)
    env.put(plane + 0x30, PIXELS, PIXELS)
    env.put(plane + 0x8C, CELL_SHIFT, CELL_SHIFT)
    platform_list = 0
    if g("platforms"):
        platform_list = 0  # filled below once the platform exists
    list_owner = env.object(0x40, "list-owner", fill=0)
    list_root = env.object(0x40, "list-root", fill=0)
    physics = env.object(0xA0, "physics", fill=0)
    env.put(physics + 0x4C, type_array)
    env.put(physics + 0x5C, plane)
    env.put(physics + 0x64, 4000, 4000)
    env.put(physics + 0x0C, list_root)
    env.put(list_root + 0x08, list_owner)

    # ---- world, input, platform ------------------------------------------------------------
    world = env.object(0x50, "world", fill=0)
    env.put(world + 0x08, spawn_root)
    env.put(world + 0x24, physics)
    env.put(world + 0x28, second_manager)
    env.put(world + 0x2C, anim_manager)
    inputs = env.object(0x20, "input", words=junk(r, 8))
    base8 = r.randrange(0, 1 << 31) & ~(0x2000000 | 0x1000000 | 0x4000000 | 0x8000000 | 0x104)
    env.put(inputs + 4, (r.randrange(0, 1 << 31) & ~0xC4) | g("in4", 0), base8 | g("in8", 0),
            g("inc", r.randrange(0, 1 << 31)))
    env.put(G_INPUT, inputs)

    platform = env.object(0x170, "platform", words=junk(r, 0x5C))
    platform_x = x + g("platform_dx", 0)
    env.put(platform + 0x4C, platform_x, g("platform_y", feet - 20))
    env.put(platform + 0xD0, g("platform_kind", 0x80))
    env.put(platform + 0x128, g("platform_left", -40))
    env.put(platform + 0x12C, g("platform_top", 12))
    env.put(platform + 0x130, g("platform_right", 40))
    env.put(platform + 0x158, g("platform_ox", r.randrange(-9, 10)), g("platform_oy", r.randrange(-9, 10)))
    if g("platforms"):
        node = env.object(16, "platform-node", words=[0, 0, platform, 0])
        env.put(list_owner + 0x14, node)

    # ---- the Claw ----------------------------------------------------------------------------
    claw = env.object(0x1C0, "claw", words=junk(r, 0x70))
    flags = (r.randrange(0, 1 << 31) & ~0x90 & ~0x400000) | g("cflags", 0)
    env.put(claw + 0x08, flags)
    env.put(claw + 0x0C, world)
    env.put(claw + 0x40, (r.randrange(0, 1 << 30) & ~2) | g("cflags2", 0))
    env.put(claw + 0x4C, x, y)
    env.put(claw + 0x80, platform if g("on_platform", False) else 0)
    env.put(claw + 0xCC, state)
    env.put(claw + 0xDC, 6, 5)
    left, top, right, bottom = g("box", (-16, -52, 16, 60))
    env.put(claw + 0x118, left, top, right, bottom)
    env.put(claw + 0x128, *g("attack", (-23, -45, 29, 49, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555)))
    env.put(claw + 0x16C, 0, 0, 0)
    env.put(claw + 0x170, 0)
    env.put(claw + 0x1B0, r.randrange(0x3F000000, 0x3FFF0000))

    # animation player embedded at +0x188
    player = claw + 0x188
    mode = g("anim", "none")
    first_set = sets["CLAW_STAND"]
    frame0 = env.get(env.get(first_set + 0x0C))
    env.put(player + 0x00, 0)
    env.put(player + 0x04, claw)
    env.put(player + 0x28, 0x3F800000)
    event = g("event", 0)
    if mode == "none":
        env.put(player + 0x08, 0, 0, 0, g("steps", 0), 0, g("finished", 0), 0, 0)
        env.put(player + 0x14, g("timer", 0))
    else:
        env.put(player + 0x08, first_set, frame0, 0)
        if mode == "timer":
            env.put(player + 0x14, 5000, 1, 0, r.randrange(2, 9), event)
        elif mode == "tick":
            env.put(player + 0x14, 7, 0, 0, r.randrange(2, 9), event)
        elif mode == "expire":
            env.put(player + 0x14, 1, 1, g("finished", 1), r.randrange(2, 9), event)
        elif mode == "advance":
            env.put(player + 0x14, 0, 0, 0, event, r.randrange(2, 9))
    # the frame advance writes the owner's +0x10/+0x14 through the player's owner slot

    # ---- saved state record ----------------------------------------------------------------
    s = env.object(0x140, "state-record", words=junk(r, 0x4C))
    values = {
        0: g("face", r.randrange(0, 2)), 1: g("s1", 0), 7: g("s7", 0), 8: g("s8", 0), 0x0B: 0x2A1, 0x0C: g("weapon_kind", 1),
        0x0F: g("s0f", 0), 0x10: g("s10", 0), 0x15: g("s15", r.randrange(20, 60)), 0x16: g("s16", r.randrange(-30, 30)),
        0x1A: 0x11, 0x1B: g("s1b", 3), 0x1C: g("s1c", 1), 0x1D: g("s1d", 4), 0x1E: g("s1e", 5), 0x21: g("s21", 0),
        0x3A: g("s3a", 17), 0x3E: 0x1F, 0x3F: 0x20, 0x40: g("s40", 30), 0x41: g("s41", 10), 0x42: g("s42", 90),
        0x44: g("s44", 50), 0x45: g("s45", 70), 0x46: 0x21, 0x48: 0x22, 0x49: 0, 0x4A: 0, 0x4B: 0,
    }
    if g("s4", 0) is not None:
        values[4] = g("s4", 0)
    for index, value in values.items():
        env.put(s + 4 * index, value)
    env.put(s + 4 * 0x49, sets["CLAW_JUMP"] if g("saved_anim") else 0)
    env.put(s + 4 * 0x4A, sets["CLAW_WALKER"] if g("saved_anim_b") else 0)

    holder["clear"] = g("clear_face", False)
    holder["state"] = s

    # effect object chain behind s[0x4b]
    effect = g("effect")
    if effect is not None:
        positive, bits = effect
        target = env.object(0x340, "effect-target", words=junk(r, 0xD0))
        env.put(target + 0x14, 0x1234)
        env.put(target + 0x20, r.randrange(1, 9) if positive else r.randrange(-9, 1))
        env.put(target + 0x2F4 + 8, bits)
        if bits == 0:
            env.put(target + 0x2F4 + 0xC, 0)
        elif bits <= 0x20:
            env.put(target + 0x2F4 + 0xC, r.randrange(0, 1 << 31) & ~1)
        else:
            bitmap = env.object(((bits + 31) // 32) * 4, "bitmap", words=[r.randrange(0, 1 << 31) & ~1] * ((bits + 31) // 32))
            env.put(target + 0x2F4 + 0xC, bitmap)
        middle = env.object(0x80, "effect-middle", words=junk(r, 0x20))
        env.put(middle + 0x18, target)
        outer = env.object(0x80, "effect-outer", words=junk(r, 0x20))
        env.put(outer + 0x6C, middle)
        env.put(s + 4 * 0x4B, outer)

    # second argument object
    handle = env.object(0x40, "state-id-owner", words=junk(r, 0x10))

    # ---- globals -------------------------------------------------------------------------
    env.put(G_DT, g("dt", r.randrange(3, 40)))
    env.put(G_MS, g("ms", r.randrange(4, 30)))
    env.put(G_WEAPON, g("weapon", 0x26B0))
    env.put(G_FPOFF, g("fp", 0))
    env.put(G_RESULT, 0x7777)
    env.put(G_GAME, 0)
    env.put(G_SND_A, 0)
    env.put(G_SND_B, 100)
    integ = []
    for offset in range(0, 0xF0, 8):
        integ.append(r.uniform(-40.0, 40.0))
    block = bytearray(b"".join(double(v) for v in integ))
    block[0x10:0x28] = b"".join(double(v) for v in (r.uniform(-3, 3), r.uniform(-3, 3), r.uniform(-3, 3)))
    block[0x58:0x60] = double(-4000.0)
    block[0x60:0x68] = double(-4000.0)
    block[0x68:0x70] = double(-4000.0)
    block[0x70:0x78] = double(4000.0)
    block[0x78:0x80] = double(4000.0)
    block[0x80:0x88] = double(4000.0)
    for offset in (0xC0, 0xC8, 0xD0):
        block[offset:offset + 8] = double(r.uniform(5.0, 60.0))
    for offset in (0xD8, 0xE0, 0xE8):
        block[offset:offset + 8] = double(r.uniform(150.0, 600.0))
    block[0xA0:0xA4] = struct.pack("<I", g("fp", 0))
    env.write(G_INTEG, bytes(block))
    env.write(G_INTEG + 0x28, double(r.uniform(-300, 300)))
    if "rand" in o:
        env.override(RAND, sequence(o["rand"]))
    return {"claw": claw, "handle": handle, "state": s}


def case(label, function, r, **options):
    seed = r.getrandbits(64)

    def setup(env):
        import random
        return build(env, random.Random(seed), options)

    return Case(label, function, setup, arguments=(lambda t: t["claw"], lambda t: t["handle"], lambda t: t["state"]))


EFFECTS = (None, (True, 0), (False, 8), (True, 0x20), (False, 0x21), (True, 96))
S1_MODES = ({"s1": 0}, {"s1": 1}, {"s1": 1, "saved_anim": True})
NO_MAPS = ()
PLATFORMS = ({}, {"cflags": 0x10, "on_platform": True}, {"cflags": 0x10})
SENTINEL = -0x80000000


def pose_cases(r, function, tag, extra):
    """The shared prologue of the pose functions: saved effect chain, pending animation, name lookups."""
    n = 0
    for e, effect in enumerate(EFFECTS):
        for m, mode in enumerate(S1_MODES):
            n += 1
            yield case(f"{tag} effect {e} s1 {m}", function, r, effect=effect, face=(e + m) % 2, **mode, **extra(n))
    for n2 in range(6):
        n += 1
        yield case(f"{tag} empty map {n2}", function, r, effect=EFFECTS[n2], maps=NO_MAPS, face=n2 % 2,
                   **S1_MODES[n2 % 3], **extra(n))


def cases(random_source):
    r = random_source

    def nothing(n):
        return {}

    yield from pose_cases(r, CLIMB, "climb", nothing)
    yield from pose_cases(r, LOOKUP, "lookup", nothing)
    teeter_rands = (0, 44, 45, 99, 100, 32767)

    def teeter(n):
        return {"rand": teeter_rands[n % 6] if n % 7 else 100 + r.randrange(0, 32600)}
    yield from pose_cases(r, TEETER, "teeter", teeter)
    for name, function in (("walk left", WALK_L), ("walk right", WALK_R)):
        yield from pose_cases(r, function, name, nothing)
        for face in (0, 1):
            for box in (0, 1):
                for a1 in (0, 1):
                    for a2 in (0, 1):
                        attack = (SENTINEL if a1 else -23, -45, 29, 49, SENTINEL if a2 else 0x1111, 0x2222, 0x3333, 0x4444, 0x5555)
                        yield case(f"{name} face {face} box {box} a {a1}{a2}", function, r, face=face,
                                   box=(SENTINEL, -52, 16, 60) if box else (-16, -52, 16, 60), attack=attack,
                                   effect=EFFECTS[(face + 2 * box + a1 + a2) % 6], **S1_MODES[(box + a1 + 2 * a2) % 3])
    yield from stand_fall_cases(r)
    yield from phys_a_cases(r)
    yield from phys_b_cases(r)
    yield from phys_c_cases(r)
    yield from phys_d_cases(r)
    yield from active_animation_timer_cases(r)


FALL_S0F = (8, 9, 10, 0x12, 0, 5)
WEAPON_FP = (
    {"weapon": 0x26BC, "s45": 70, "dt": 20},
    {"weapon": 0x26B0, "s45": 12, "dt": 20},
    {"weapon": 0x26B0, "s45": 70, "dt": 20},
    {"weapon": 0x26BC, "s45": 10, "dt": 20},
    {"weapon": 0x26B0, "s45": 20, "dt": 20},
    {"weapon": 0x26B0, "s45": 21, "dt": 20},
)


def stand_fall_cases(r):
    stand = {"state": 1, "floor": (0, 1)}
    fall = {"state": 4}
    n = 0
    for e in (0, 1, 2):
        for m in range(3):
            n += 1
            yield case(f"stand effect {e} s1 {m}", STAND_FALL, r, effect=EFFECTS[e], face=n % 2, **S1_MODES[m], **stand,
                       **WEAPON_FP[n % 6], fp=n % 2, **PLATFORMS[n % 3])
    for i, s0f in enumerate(FALL_S0F):
        for face in (0, 1):
            n += 1
            yield case(f"fall s0f {s0f} face {face}", STAND_FALL, r, s0f=s0f, face=face, **fall, **WEAPON_FP[n % 6],
                       fp=n % 2, **PLATFORMS[n % 3])
    for face in (0, 1):
        yield case(f"fall empty map face {face}", STAND_FALL, r, s0f=0, face=face, maps=NO_MAPS, **fall)
        yield case(f"fall named lookup empty map face {face}", STAND_FALL, r, s0f=9, face=face, maps=NO_MAPS, **fall)
    for state in (0, 2, 7, 9):
        n += 1
        yield case(f"other state {state}", STAND_FALL, r, state=state, floor=(0, 2), **WEAPON_FP[n % 6], fp=n % 2,
                   **PLATFORMS[n % 3])
    for combo in WEAPON_FP:
        for fp in (0, 1):
            for p in (0, 1, 2):
                yield case(f"stand weapon/timer {combo['s45']}/{combo['weapon']:x} fp {fp} plat {p}", STAND_FALL, r,
                           fp=fp, **combo, **PLATFORMS[p], **stand)


def phys_a_cases(r):
    n = 0
    for s0f in FALL_S0F:
        for m, maps in enumerate((NATIVE_ALL, NO_MAPS)):
            n += 1
            yield case(f"A fall s0f {s0f} maps {m}", PHYS_A, r, state=4, s0f=s0f, face=n % 2, maps=maps,
                       **PLATFORMS[n % 3])
    for m, maps in enumerate((NATIVE_ALL, NO_MAPS)):
        for p in range(3):
            yield case(f"A climb maps {m} plat {p}", PHYS_A, r, state=6, ladder=True, maps=maps, face=p % 2, **PLATFORMS[p])
    inputs = ({"in8": 0x2000000}, {"in8": 0x1000000}, {"in8": 0}, {"in8": 0x3000000})
    for k, inp in enumerate(inputs):
        for face in (0, 1):
            for anim in ({"anim": "expire"}, {"anim": "none", "finished": 1}):
                n += 1
                yield case(f"A walk input {k} face {face} {anim['anim']}", PHYS_A, r, state=7, face=face, **inp, **anim,
                           effect=EFFECTS[n % 6], **PLATFORMS[n % 3])
    for k, anim in enumerate(({"anim": "none"}, {"anim": "timer", "event": 2}, {"anim": "tick", "event": 3},
                              {"anim": "advance", "event": 1}, {"anim": "expire", "finished": 0})):
        yield case(f"A not finished {k}", PHYS_A, r, state=0, face=k % 2, in8=0x2000000, **anim)
    for state in (1, 2, 5):
        for face in (0, 1):
            yield case(f"A ground state {state} face {face}", PHYS_A, r, state=state, floor=(0, 1), face=face,
                       anim="expire", in8=0x1000000 if face else 0x2000000)
    yield case("A empty map walk", PHYS_A, r, state=7, face=0, in8=0x1000000, anim="expire", maps=NO_MAPS)


NATIVE_ALL = NAMES

PROBE_PATTERNS = (
    (None, None, None, None), (1, 1, 1, 1), (1, None, None, None), (None, None, None, 1), (1, None, None, 1),
    (None, 1, None, None), (None, None, 2, None), (3, None, None, 2), (None, None, None, 5), (4, 4, 4, 4),
)


def phys_b_cases(r):
    n = 0
    for k, pattern in enumerate(PROBE_PATTERNS):
        for face in (0, 1):
            n += 1
            yield case(f"B probes {k} face {face}", PHYS_B, r, state=7, face=face, probes=pattern,
                       in8=(0, 0x4000000, 0x8000000, 0xC000000)[n % 4], base="air" if n % 2 else "zero",
                       **PLATFORMS[n % 3])
    for in8 in (0, 0x4000000, 0x8000000, 0xC000000):
        for face in (0, 1):
            yield case(f"B flags {in8:x} face {face}", PHYS_B, r, state=0, face=face, in8=in8, probes=(1, None, None, 1))
    for k, pattern in enumerate(((None,) * 4, (1, 1, 1, 1), (1, None, None, None))):
        yield case(f"B face cleared by a tile query {k}", PHYS_B, r, state=7, face=1, probes=pattern, base="zero",
                   clear_face=True, in8=(0, 0x4000000, 0x8000000)[k])
    yield case("B narrow box", PHYS_B, r, state=7, face=1, box=(-4, -52, 4, 60), probes=(1, 1, 1, 1))
    yield case("B narrow box no support", PHYS_B, r, state=7, face=1, box=(-4, -52, 4, 60))
    yield case("B platform with probe", PHYS_B, r, state=7, face=1, cflags=0x10, on_platform=True)
    yield case("B platform flag only", PHYS_B, r, state=7, face=1, cflags=0x10)
    for s0f in FALL_S0F:
        yield case(f"B fall s0f {s0f}", PHYS_B, r, state=4, s0f=s0f, face=s0f % 2, in8=0x4000000 if s0f % 3 else 0)
    for face in (0, 1):
        for maps in (NATIVE_ALL, NO_MAPS):
            yield case(f"B climb face {face}", PHYS_B, r, state=6, ladder=True, face=face, maps=maps,
                       probes=(1, 1, 1, 1))
    for face in (0, 1):
        yield case(f"B ground state 1 face {face}", PHYS_B, r, state=1, face=face, floor=(0, 1), in8=0x8000000)
        yield case(f"B ground state 2 face {face}", PHYS_B, r, state=2, face=face, floor=(0, 2), in8=0x4000000)


def phys_c_cases(r):
    n = 0
    base = {"state": 7, "s1": 1, "s8": 1}
    for event in range(0, 7):
        for anim in ("timer", "tick", "advance"):
            n += 1
            yield case(f"C event {event} {anim}", PHYS_C, r, anim=anim, event=event, face=n % 2, s7=n % 2, s4=0, s0c=1,
                       **{**base, "s8": n % 2}, in4=(0x4, 0x40, 0x80, 0)[n % 4])
    for wk in (0, 1, 2, 3):
        for s4 in (0, 1):
            yield case(f"C shoot kind {wk} s4 {s4}", PHYS_C, r, anim="timer", event=2, weapon_kind=wk, s4=s4, s1=1, state=7,
                       s7=s4)
    for wk in (1, 2, 3):
        for in4 in (0, 4, 0x40, 0x80):
            for s1c in (0, 5):
                yield case(f"C release kind {wk} in4 {in4:x} ammo {s1c}", PHYS_C, r, anim="timer", event=3, weapon_kind=wk,
                           in4=in4, s1c=s1c, state=7, s1=1, s8=1)
    for in8 in (0, 4, 0x100, 0x104):
        for s41, s40, s42 in ((10, 30, 90), (40, 30, 90), (10, 30, 35), (10, 30, 30), (10, 25, 31), (10, 28, 31)):
            yield case(f"C charge in8 {in8:x} {s41}/{s40}/{s42}", PHYS_C, r, anim="timer", event=4, in8=in8, s41=s41,
                       s40=s40, s42=s42, dt=8, state=7, s1=1, s8=1, saved_anim_b=in8 % 2 == 0)
    for weapon in (0x26B0, 0x26BC):
        for s7 in (0, 1):
            yield case(f"C sword weapon {weapon:x} s7 {s7}", PHYS_C, r, anim="timer", event=5, weapon=weapon, s7=s7,
                       state=7, s1=1, s8=1)
    yield case("C finished animation", PHYS_C, r, anim="expire", event=2, state=7, s1=1, s8=1, effect=EFFECTS[1])
    yield case("C finished animation effect", PHYS_C, r, anim="expire", event=2, state=7, s1=1, s8=1, effect=EFFECTS[2])
    yield case("C finished, timer left", PHYS_C, r, anim="advance", event=2, state=7, s1=1, s8=1)
    yield case("C no flag", PHYS_C, r, anim="timer", event=2, state=7, s1=0)
    yield case("C no flag s8", PHYS_C, r, anim="timer", event=2, state=7, s1=0, s8=1)
    for s44, ms in ((50, 10), (10, 10), (9, 10), (0, 10)):
        yield case(f"C timer {s44}/{ms}", PHYS_C, r, state=7, s44=s44, ms=ms, s1=0)
    for fp in (0, 1):
        for s21 in (0, 61, -45):
            for p in (0, 1, 2):
                yield case(f"C speed s21 {s21} fp {fp} plat {p}", PHYS_C, r, state=7, s1=0, s21=s21, fp=fp, dt=11,
                           **PLATFORMS[p])
    for s0f in FALL_S0F:
        for s1 in (0, 1):
            yield case(f"C fall s0f {s0f} s1 {s1}", PHYS_C, r, state=4, s0f=s0f, s1=s1, s8=s1, s21=33 * (s0f % 2),
                       fp=s0f % 2)
    for s1, s8 in ((0, 0), (0, 1), (1, 0), (1, 1)):
        for face in (0, 1):
            for in8 in (0, 0x8000000, 0x1000000, 0x2000000, 0x9000000, 0xA000000):
                for state in (5, 7):
                    if (s1 + face + state + (in8 >> 24)) % 2:
                        continue
                    yield case(f"C tail s1 {s1} s8 {s8} face {face} in8 {in8:x} state {state}", PHYS_C, r, state=state,
                               s1=s1, s8=s8, face=face, in8=in8, anim="timer", event=0,
                               floor=(0, 1) if state == 5 else None)


def phys_d_cases(r):
    n = 0
    for s0f in FALL_S0F:
        for face in (0, 1):
            n += 1
            yield case(f"D fall s0f {s0f} face {face}", PHYS_D, r, state=4, s0f=s0f, face=face, s21=40 * (n % 2), fp=n % 2,
                       **PLATFORMS[n % 3], in8=(0, 0x4000000)[n % 2])
    for e in range(6):
        for m in range(3):
            n += 1
            yield case(f"D stand effect {e} s1 {m}", PHYS_D, r, state=1, floor=(0, 1), effect=EFFECTS[e],
                       face=n % 2, s21=(0, 27, -53)[n % 3], fp=n % 2, **S1_MODES[m], **PLATFORMS[n % 3],
                       base=("air", "air2", "zero")[n % 3])
    for face in (0, 1):
        yield case(f"D stand empty map {face}", PHYS_D, r, state=1, floor=(0, 2), face=face, maps=NO_MAPS, s1=1)
    for in8 in (0x4000000, 0x4000001):
        yield case(f"D blocked by input {in8:x}", PHYS_D, r, state=1, floor=(0, 1), in8=in8)
    for state in (0, 2, 7):
        yield case(f"D other state {state}", PHYS_D, r, state=state, floor=(0, 1))
    for fp in (0, 1):
        for s21 in (0, 61):
            for ms in (5, 25):
                yield case(f"D timers fp {fp} s21 {s21} ms {ms}", PHYS_D, r, state=7, fp=fp, s21=s21, ms=ms,
                           s44=(20, 90)[ms == 5], dt=17)
    for k in range(3):
        yield case(f"D landing {k}", PHYS_D, r, state=4, s0f=0, floor=(2 + 4 * k, 1), face=k % 2)


def active_animation_timer_cases(r):
    """Expose elapsed-time reads through the original animation player's live timer.

    Original 0x4c82a0 subtracts elapsed milliseconds from player+0x14 when
    player+0x08 is nonzero, player+0x18 is one and the timer has not expired.
    Keep these additions last so existing cases consume the same random draws.
    """
    paths = (
        ("stand-fall", STAND_FALL, {"state": 0, "floor": (0, 2), "fp": 1}),
        ("B", PHYS_B, {"state": 7, "face": 1, "probes": (1, None, None, None), "in8": 0x4000000}),
        ("D", PHYS_D, {"state": 1, "floor": (0, 1), "in8": 0x4000000}),
    )
    for tag, function, path in paths:
        for milliseconds in (11, 23):
            yield case(f"{tag} active animation timer ms {milliseconds}", function, r,
                       anim="timer", ms=milliseconds, dt=37, x=256, y=195, **path)
