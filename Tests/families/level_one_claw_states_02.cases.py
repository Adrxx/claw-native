"""Cases for level_one_claw_states_02: Level 1 Claw movement and pose state callbacks batch 2.

Every Claw case builds a small but real world around the Claw object: an animation manager with a real
name map, animation sets and frames, a tile plane whose tile types are stub methods with controlled
answers, an input-flag object, the physics integrator block, the saved state record and the game object
with its state-manager vtable.  Coverage never depends on the random source: each branch is selected by
an explicit option, and the random source only fills unread junk and varies positions, timers and the
like.  The arc functions use hand-picked binary64 grids.
"""
import itertools
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

# owned functions
CLIMB, CLIMB_END, MSG_A, MSG_B, LEDGE, FLY = 0x41BB70, 0x41C030, 0x41C2B0, 0x41C440, 0x41E790, 0x41F4C0
RANDSND, ARC_V, ARC_STEP, FRACT, SPIKE, TILEQ = 0x420480, 0x420BD0, 0x420C40, 0x420D50, 0x417C50, 0x4CD740

RAND, POST = 0x4A3050, 0x546D50

# globals
G_INPUT, G_DT, G_MS, G_WEAPON, G_FPOFF, G_RESULT = 0x537204, 0x53720C, 0x5430C4, 0x534EAC, 0x534E58, 0x544E88
G_INTEG = 0x534DB8
G_GAME, G_SND_A, G_SND_B = 0x53C9A4, 0x532C0C, 0x532C10
G_APP, G_7220, G_722C, G_SPLASH = 0x5371FC, 0x537220, 0x53722C, 0x537960

AIR, AIR2 = 0xFFFFFFFF, 0xEEEEEEEE
DEFAULT_BOX = (-12, -48, 20, 56)      # differs from every body box the functions reset to

NAMES = ("CLAW_CLIMB", "CLAW_CLIMBIDLE", "CLAW_CLIMBDOWN", "CLAW_JUMP", "CLAW_FALL", "CLAW_STAND",
         "CLAW_SPIKEDEATH", "CLAW_WALK", "CLAW_STANDX", "CLAW_FALLEN")
NO_MAPS = ()
SENTINEL = -0x80000000

# tile type kinds (index in the type array)
T_ZERO, T_ONE, T_TWO, T_THREE, T_FOUR, T_HALF, T_ZT, T_ZZT = 0, 1, 2, 3, 4, 5, 6, 7
CONST_KINDS = (0, 1, 2, 3, 4)


def double(value):
    return struct.pack("<d", value)


def words(x):
    raw = struct.pack("<Q", x) if isinstance(x, int) else struct.pack("<d", x)
    return struct.unpack("<II", raw)


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


def tile_effect(kind):
    if kind in CONST_KINDS:
        return lambda env, call: kind
    if kind == T_HALF:
        return lambda env, call: 1 if call.arguments[1] < 4 else 0
    cycle = {T_ZT: (0, 2), T_ZZT: (0, 0, 3)}[kind] if isinstance(kind, int) else kind
    return lambda env, call: cycle[(env.calls_so_far(call.function) - 1) % len(cycle)]


def wide_effect(index):
    return lambda env, call: (0x1000 * (index + 1) + 0x40 * call.arguments[0] + call.arguments[1]) & 0xFFFFFFFF


EFFECTS = (None, (True, 0), (False, 8), (True, 0x20), (False, 0x21), (True, 96))
S1_MODES = ({"s1": 0}, {"s1": 1}, {"s1": 1, "saved_anim": True})


def build(env, r, o):
    """Build the world for one case. `o` holds the options; returns the tokens."""
    g = o.get
    x = g("x", 256 + r.randrange(-20, 21))
    y = g("y", 8 * r.randrange(24, 31) + 3)
    state = g("state", 6)
    width, height = g("size", (512, 512))
    sx, sy = g("shift", (3, 3))
    cols, rows = width >> sx, height >> sy

    # ---- animation sets and name map ---------------------------------------------------------
    sets = {}
    for i, name in enumerate(NAMES):
        sets[name] = make_animation_set(env, r, i, frames=3, delay=g("delay", 6), flags=g("frame_flags", 0))
    listed = {n: sets[n] for n in NAMES if n in g("maps", NAMES)}
    anim_manager = env.object(0x40, "animation-manager", fill=0)
    make_map(env, anim_manager + 0x10, listed)
    second_manager = env.object(0x40, "second-manager", fill=0)
    if g("deathtile"):
        zone = env.object(0x80, "death-zone", fill=0)
        link = env.object(0x80, "death-link", fill=0)
        env.put(link + 0x10, zone)
        env.put(zone + 0x78, 0)
        obj = env.object(0x40, "death-tile", words=junk(r, 0x10))
        env.put(obj + 0x10, link)
        make_map(env, second_manager + 0x10, {"LEVEL_DEATHTILE": obj, "OTHER": obj})
    else:
        make_map(env, second_manager + 0x10, {})
    env.put(second_manager + 0x30, g("sm30", 0))
    spawn_leaf = env.object(0x40, "spawn-leaf", fill=0)
    splash_desc = env.object(0x40, "splash-descriptor", fill=0) if g("splashmap") else 0
    make_map(env, spawn_leaf + 0x10, {"Splash": splash_desc} if g("splashmap") else {})
    spawn_mid = env.object(0x40, "spawn-mid", words=[0] * 5 + [spawn_leaf])
    spawn_root = env.object(0x40, "spawn-root", fill=0)
    env.put(spawn_root + 0x0C, spawn_mid)

    # ---- tile plane and physics ------------------------------------------------------------
    kinds = g("kinds", (0, 1, 2, 3, 4, T_HALF, T_ZT, T_ZZT))
    types = []
    for index, kind in enumerate(kinds):
        effect = wide_effect(index) if g("wide") else tile_effect(kind)
        method = env.stub(f"tile-type-{index}", "thiscall", 2, effect)
        vtable = env.object(0x40, "tile-vtable", fill=0)
        env.put(vtable + 0x20, method)
        types.append(env.object(8, "tile-type", words=[vtable, 0x77 + index]))
    type_array = env.object(4 * len(types), "tile-types", words=types)
    base = {"air": AIR, "air2": AIR2, "zero": 0x1230000}[g("base", "air")]
    tiles = [base] * (cols * rows)
    if g("random_tiles"):
        for i in range(len(tiles)):
            pick = r.randrange(0, len(types) + 2)
            tiles[i] = AIR if pick == len(types) else AIR2 if pick == len(types) + 1 else \
                ((0xABCD0000 if pick % 2 else 0x13570000) | pick)

    def paint(px, py, attr_type):
        if 0 <= px < width and 0 <= py < height:
            tiles[(py >> sy) * cols + (px >> sx)] = (0xABCD0000 if attr_type % 2 else 0x13570000) | attr_type

    feet = y + g("box", DEFAULT_BOX)[3] + 1
    for dx, attr_type in g("probes", {}).items():
        paint(x + dx, feet, attr_type)
    for px0, py0, px1, py1, attr_type in g("rects", ()):
        for py in range(py0, py1 + 1, 4):
            for px in range(px0, px1 + 1, 4):
                paint(x + px, y + py, attr_type)
    floor = g("floor")
    if floor is not None:
        gap, attr_type = floor
        for py in range(feet + gap, feet + gap + 24, 4):
            for px in range(x - 80, x + 81, 4):
                paint(px, py, attr_type)
    ladder = g("ladder")                    # (first_dy, last_dy): a column of ladder tiles under the Claw
    if ladder:
        for dy in range(ladder[0], ladder[1] + 1, 4):
            paint(x, y + dy, T_THREE)
    tile_array = env.object(4 * len(tiles), "tiles", words=tiles)
    row_offsets = env.object(4 * rows, "tile-rows", words=[row * cols for row in range(rows)])
    plane = env.object(0xA0, "plane", fill=0)
    env.put(plane + 0x20, tile_array, row_offsets)
    env.put(plane + 0x30, width, height)
    env.put(plane + 0x8C, sx, sy)
    list_owner = env.object(0x40, "list-owner", fill=0)
    list_root = env.object(0x40, "list-root", fill=0)
    physics = env.object(0xA0, "physics", fill=0)
    env.put(physics + 0x4C, type_array)
    env.put(physics + 0x5C, plane)
    env.put(physics + 0x64, g("step_limit", 4000), g("step_limit", 4000))
    env.put(physics + 0x0C, list_root)
    env.put(list_root + 0x08, list_owner)

    # ---- world, input, platform ------------------------------------------------------------
    world = env.object(0x50, "world", fill=0)
    env.put(world + 0x08, spawn_root)
    env.put(world + 0x24, physics)
    env.put(world + 0x28, second_manager)
    env.put(world + 0x2C, anim_manager)
    inputs = env.object(0x20, "input", words=junk(r, 8))
    base8 = r.randrange(0, 1 << 31) & ~(0x2000000 | 0x1000000 | 0x4000000 | 0x8000000 | 0x104 | 1)
    env.put(inputs + 4, (r.randrange(0, 1 << 31) & ~0xC4 & ~1) | g("in4", 0), base8 | g("in8", 0),
            g("inc", r.randrange(0, 1 << 31)))
    env.put(G_INPUT, inputs)

    platform = env.object(0x170, "platform", words=junk(r, 0x5C))
    env.put(platform + 0x4C, x, feet - 20)
    env.put(platform + 0x158, g("platform_ox", r.randrange(-9, 10)), g("platform_oy", r.randrange(-9, 10)))
    env.put(platform + 0x128, -40)
    env.put(platform + 0x12C, 12)
    env.put(platform + 0x130, 40)
    env.put(platform + 0xD0, 0x80)

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
    left, top, right, bottom = g("box", DEFAULT_BOX)
    env.put(claw + 0x118, left, top, right, bottom)
    env.put(claw + 0x128, -23, -41, 29, 49, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555)
    env.put(claw + 0x148, g("vx", r.randrange(-300, 300)), g("vy", r.randrange(-300, 300)))
    env.put(claw + 0x16C, 0, 0, 0)
    if g("ctable", True):
        # animation table read by the pose setter at 0x4209d0: valid index range and a per-index entry list
        entries = env.object(4 * 0x190, "pose-entries", words=[0x9000 + 3 * i for i in range(0x190)])
        table = env.object(0x80, "pose-table", fill=0)
        env.put(table + 0x14, entries)
        env.put(table + 0x64, 0x17F)
        env.put(table + 0x68, 0x185)
        env.put(claw + 0x170, table)
    else:
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
    elif mode == "finished":      # set, no timer, finished flag set: 4c82a0 returns player+0x20
        env.put(player + 0x08, first_set, frame0, 0, 0, 0, 1, g("ret", 1), 7)
    elif mode == "last":          # timer 1, ticks to zero and returns player+0x24 with the finished flag set
        env.put(player + 0x08, first_set, frame0, 0, 1, 0, 1, 3, g("ret", 1))
    elif mode == "timer":
        env.put(player + 0x08, first_set, frame0, 0, 5000, 1, 0, 5, g("ret", 1))
    elif mode == "expire":
        env.put(player + 0x08, first_set, frame0, 0, 1, 1, g("finished", 1), r.randrange(2, 9), event)
    elif mode == "advance":
        env.put(player + 0x08, first_set, frame0, 0, 0, 0, 0, event, r.randrange(2, 9))
    elif mode == "plain":         # set, timer 0, unfinished: a plain frame advance
        env.put(player + 0x08, first_set, frame0, 0, 0, 0, 0, r.randrange(2, 9), event)

    # ---- saved state record ----------------------------------------------------------------
    s = env.object(0x140, "state-record", words=junk(r, 0x4C))
    values = {
        0: g("face", r.randrange(0, 2)), 1: g("s1", 0), 6: g("s6", 0), 0x0B: g("s0b", 0x2A1), 0x0F: g("s0f", 0x33),
        0x10: g("s10", 0), 0x18: g("s18", r.randrange(-40, 80)), 0x19: g("s19", r.randrange(-40, 80)),
        0x1A: g("s1a", 0), 0x1F: g("s1f", 3), 0x20: g("s20", 7), 0x3C: 0x3C3C, 0x3E: 0x1F, 0x3F: 0x20,
        0x45: g("s45", 0), 0x46: g("s46", 91), 0x48: 0x22, 0x49: 0, 0x4B: 0,
    }
    for index, value in values.items():
        env.put(s + 4 * index, value)
    env.put(s + 4 * 0x49, sets["CLAW_JUMP"] if g("saved_anim") else 0)
    env.put(s + 4 * 0x43, 0x4343)

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

    for index, value in g("state_raw", {}).items():
        env.put(s + 4 * index, value & 0xFFFFFFFF)
    for offset, value in g("claw_raw", {}).items():
        env.put(claw + offset, value & 0xFFFFFFFF)

    handle = env.object(0x40, "state-id-owner", words=junk(r, 0x10))

    # ---- the game object and its state manager ----------------------------------------------
    gs_method = env.stub("game-state-query", "thiscall", 0, returns(g("gs", 1)))
    gs_vtable = env.object(0x40, "state-manager-vtable", fill=0)
    env.put(gs_vtable + 0x10, gs_method)
    gs_manager = env.object(0x800, "state-manager", fill=0)
    env.put(gs_manager, gs_vtable, *junk(r, 15))
    app = env.object(0x20, "application", words=junk(r, 8))
    env.put(app + 4, g("hwnd", 0x11A0 + r.randrange(0, 0x100)))
    game = env.object(0x80, "game", words=junk(r, 0x20))
    env.put(game + 0x04, app)
    env.put(game + 0x14, 0)
    env.put(game + 0x2C, gs_manager)
    env.put(G_APP, game)
    env.put(G_7220, g("g7220", 0))
    env.put(G_722C, g("g722c", 0))
    splash = env.object(0xC0, "splash-flags", words=junk(r, 0x30))
    env.put(splash + 0x44, g("splash", 0))
    env.put(splash + 0xB0, 0x37)
    env.put(G_SPLASH, splash)

    # ---- other globals -----------------------------------------------------------------------
    env.put(G_DT, g("dt", r.randrange(3, 40)))
    env.put(G_MS, g("ms", r.randrange(4, 30)))
    env.put(G_WEAPON, g("weapon", 0))
    env.put(0x534EA8, 0x5151)
    env.put(G_FPOFF, g("fp", 0))
    env.put(G_RESULT, 0x7777)
    env.put(G_GAME, 0)
    env.put(G_SND_A, g("snd", 0))
    env.put(G_SND_B, 100)
    integ = [r.uniform(-40.0, 40.0) for _ in range(0, 0xF0, 8)]
    block = bytearray(b"".join(double(v) for v in integ))
    block[0x10:0x28] = b"".join(double(v) for v in g("vec", (r.uniform(-3, 3), r.uniform(-3, 3), r.uniform(-3, 3))))
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
    if "origin" in o:
        env.write(G_INTEG + 0x48, double(o["origin"][0]))
        env.write(G_INTEG + 0x50, double(o["origin"][1]))
    for address, value in g("glob", {}).items():
        env.put(address, value & 0xFFFFFFFF)
    env.override(RAND, sequence(*g("rand", (7,))))
    env.override(POST, returns(g("pm", 1)))
    return {"claw": claw, "handle": handle, "state": s, "physics": physics}


def case(label, function, r, **options):
    seed = r.getrandbits(64)

    def setup(env):
        import random
        return build(env, random.Random(seed), options)

    if function == TILEQ:
        return Case(label, function, setup, receiver=lambda t: t["physics"],
                    arguments=(lambda t: t["claw"], options.get("dx", 0) & 0xFFFFFFFF))
    if function == LEDGE:
        return Case(label, function, setup, arguments=(lambda t: t["claw"],))
    if function == RANDSND:
        return Case(label, function, setup)
    return Case(label, function, setup, arguments=(lambda t: t["claw"], lambda t: t["handle"], lambda t: t["state"]))


# ------------------------------------------------------------------------------------------------
def climb_cases(r):
    n = 0
    # --- the jump-off branch: weapon and carried-item variants, effect chain, saved animation ---------
    for weapon, s45 in ((0x26BC, 0), (0x26BC, 0x5DC), (0, 0), (0, 0x5DC), (0x26B0, 0x5DC), (0x26B0, 0)):
        n += 1
        yield case(f"climb jump weapon {weapon:x} s45 {s45:x}", CLIMB, r, in4=1, weapon=weapon, s45=s45, state=6,
                   in8=(0, 0x8000000, 0x2000000)[n % 3], effect=EFFECTS[n % 4], face=n % 2, **S1_MODES[n % 3])
    for e in range(3):
        for m in range(3):
            n += 1
            yield case(f"climb jump effect {e} s1 {m}", CLIMB, r, in4=1, effect=EFFECTS[e], face=(e + m) % 2, state=6, **S1_MODES[m])
    yield case("climb jump empty map", CLIMB, r, in4=1, maps=NO_MAPS, state=6, effect=EFFECTS[1], s1=1)
    yield case("climb jump ignored by up", CLIMB, r, in4=1, in8=0x4000000, state=6, ladder=(-60, 60))
    # --- the ladder search -------------------------------------------------------------------
    for lad in (None, (-60, 80), (0, 80), (50, 100), (-80, -57)):
        for in8 in (0x4000000, 0x8000000, 0):
            n += 1
            yield case(f"climb search ladder {lad} in8 {in8:x}", CLIMB, r, ladder=lad, in8=in8, state=6, fp=n % 2,
                       s0b=(5, 2, 8, 0x2A1)[n % 4], weapon=0x26BC if n % 3 == 0 else 0)
    yield case("climb search exits after one probe", CLIMB, r, ladder=(-60, 80), in8=0x4000000, state=6, box=(-16, -52, 16, -52))
    yield case("climb search empty body", CLIMB, r, ladder=None, in8=0x4000000, state=6, box=(-16, 10, 16, 5))
    # --- idle / up / down with an existing ladder row ------------------------------------------------
    for in8 in (0x4000000, 0x8000000, 0, 0xC000000):
        for weapon in (0x26BC, 0):
            n += 1
            yield case(f"climb pose in8 {in8:x} weapon {weapon:x}", CLIMB, r, in8=in8, weapon=weapon,
                       s0b=(8, 2, 5, 0x2A1)[n % 4], s1a=300 + n, fp=n % 2, maps=NO_MAPS if n % 5 == 0 else NAMES, state=6)
    for s0b, in8 in ((8, 0x4000000), (2, 0x8000000), (5, 0), (5, 0x4000000), (8, 0x8000000)):
        yield case(f"climb pose already {s0b} in8 {in8:x}", CLIMB, r, in8=in8, s0b=s0b, s1a=333, fp=1, state=6)
    # --- the end-of-ladder animation ranges: row offset = box bottom - s1a + y --------------------------------
    for target in (-1, 0, 16, 17, 35, 51, 52, 69, 86, 103, 120, 121, 122):
        n += 1
        yield case(f"climb end range {target}", CLIMB, r, in8=(0x4000000, 0x8000000, 0)[n % 3], fp=1, state=6, y=100,
                   state_raw={0x1A: DEFAULT_BOX[3] + 100 - target})
    for target in (17, 70, 100):
        yield case(f"climb end range moving {target}", CLIMB, r, in8=0x4000000, fp=0, state=6, y=100,
                   state_raw={0x1A: DEFAULT_BOX[3] + 100 - target})
    # --- the falling / standing states after the move --------------------------------------------
    for s0f in (8, 9, 10, 0x12, 0, 5):
        for maps in (NAMES, NO_MAPS):
            n += 1
            yield case(f"climb fall s0f {s0f} map {len(maps)}", CLIMB, r, state=4, s0f=s0f, maps=maps, s10=555,
                       in8=(0, 0x4000000, 0x8000000)[n % 3], s1=n % 2, s1a=300 + n, fp=1, effect=EFFECTS[n % 6])
    for state in (1, 6, 3):
        for fp in (0, 1):
            n += 1
            yield case(f"climb state {state} fp {fp}", CLIMB, r, state=state, fp=fp, in8=(0, 0x4000000)[n % 2],
                       s1a=300 + n, floor=(0, 1) if state == 1 else None, s0f=8)
    for pattern in range(4):
        yield case(f"climb random {pattern}", CLIMB, r, state=6, in8=(0, 0x4000000, 0x8000000)[pattern % 3],
                   fp=pattern % 2, s1a=300 + pattern if pattern % 2 else 0, ladder=(-40 + 8 * pattern, 90),
                   dt=r.randrange(1, 60), ms=r.randrange(2, 40), weapon=(0, 0x26BC)[pattern // 2])


def climb_end_cases(r):
    n = 0
    for anim in ("none", "finished", "last", "timer", "expire", "plain"):
        for ret in (1, 5):
            for vx in (120, -3):
                n += 1
                yield case(f"climb end {anim} ret {ret} vx {vx}", CLIMB_END, r, anim=anim, ret=ret, vx=vx, state=(6, 4, 1)[n % 3],
                           cflags=0x10 if n % 3 == 0 else 0, on_platform=n % 2 == 0, face=n % 2, effect=EFFECTS[n % 6],
                           **S1_MODES[n % 3], ms=(4, 17, 33)[n % 3], finished=n % 2, event=n % 8,
                           maps=NO_MAPS if n % 11 == 0 else NAMES)
        yield case(f"climb end {anim} no motion", CLIMB_END, r, anim=anim, ret=1, vx=0, state=6)
    for flags, platform in ((0x10, True), (0x10, False), (0, True), (0, False)):
        n += 1
        yield case(f"climb end platform {flags:x} {platform}", CLIMB_END, r, anim="finished", ret=1, vx=(50, -50)[n % 2],
                   cflags=flags, on_platform=platform, state=6)
    for i, effect in enumerate(EFFECTS):
        for face in (0, 1):
            n += 1
            yield case(f"climb end reset effect {i} face {face}", CLIMB_END, r, anim="finished", ret=(1, 2)[n % 2],
                       effect=effect, face=face, state=(4, 1)[n % 2], **S1_MODES[n % 3])
    yield case("climb end reset empty map", CLIMB_END, r, anim="finished", maps=NO_MAPS, s1=1, state=6)
    for s1, saved in itertools.product((0, 1), (False, True)):
        for face in (0, 1):
            yield case(f"climb end pending s1 {s1} saved {saved} face {face} no maps", CLIMB_END, r, anim="finished", maps=NO_MAPS,
                       s1=s1, saved_anim=saved, face=face, state=6, effect=EFFECTS[(2 * s1 + face) % 4])
    for vx, ms in ((1, 4), (7, 19), (500, 1), (-500, 19)):
        yield case(f"climb end scaled move vx {vx} ms {ms}", CLIMB_END, r, anim="timer", ret=1, vx=vx, ms=ms, state=6)
    yield case("climb end moves with fall state", CLIMB_END, r, anim="finished", ret=1, vx=-9, state=4)


def msg_cases(r):
    n = 0
    counters = (799, 800, 801, 2000, -5)
    for function in (MSG_A, MSG_B):
        tag = "A" if function == MSG_A else "B"
        for fp in (0, 1):
            for counter in counters:
                n += 1
                yield case(f"msg {tag} fp {fp} counter {counter}", function, r, fp=fp, s10=counter, gs=(1, 4)[n % 2],
                           s6=(0, 9)[(n // 2) % 2] if counter not in (800, 801, 802, 2000) else 0, g722c=(0, 1)[(n // 3) % 2],
                           s1f=(0, 1, 2, -3)[n % 4], anim="none", finished=1, state_raw={0x20: 40 + n}, pm=n % 3, hwnd=0x2000 + n)
        for s6 in (0, 1):
            for gs in (1, 4):
                for g722c in (0, 1):
                    for s1f in (-1, 1):
                        n += 1
                        yield case(f"msg {tag} full s6 {s6} gs {gs} g722c {g722c} s1f {s1f}", function, r, fp=1, s10=900, s6=s6,
                                   gs=gs, g722c=g722c, s1f=s1f, finished=1, state_raw={0x20: 40 + n}, pm=n % 2, hwnd=0x3000 + n)
    for steps, finished in ((0, 0), (1, 1), (7, 5)):
        yield case(f"msg B player timer {steps} finished {finished}", MSG_B, r, anim="none", steps=steps,
                   finished=finished, ms=3, s6=0, gs=1, s1f=1)
    for anim in ("finished", "last", "timer", "expire", "advance", "plain"):
        yield case(f"msg B player {anim}", MSG_B, r, anim=anim, s6=0, gs=1, s1f=0, event=3)
        yield case(f"msg A player {anim}", MSG_A, r, anim=anim, s6=0, gs=4, s1f=0, event=3, s10=900, fp=0)
    for dt, fp in ((1, 0), (40, 0), (17, 1)):
        yield case(f"msg A integrator dt {dt} fp {fp}", MSG_A, r, dt=dt, fp=fp, s10=700 + dt % 90, s6=0)


def ledge_cases(r):
    n = 0
    base = {"state": 7}
    yield case("ledge platform flag", LEDGE, r, cflags=0x10, probes={16: T_ONE}, **base)
    box = (-16, -52, 16, 60)
    for head in (None, T_ZERO, T_ONE, T_TWO, T_THREE, T_FOUR, T_HALF, T_ZT, T_ZZT):
        for mid in (None, T_ONE):
            for left in (None, T_THREE, T_ZT, T_ZZT):
                n += 1
                if (head in (None, T_ZERO, T_FOUR) and n % 4) or (mid and left and n % 2) or (head and mid is None and left is not None and n % 3 == 0):
                    continue
                probes = {}
                if head is not None:
                    probes[16] = head
                if mid is not None:
                    probes[4] = mid
                if left is not None:
                    probes[-16] = left
                yield case(f"ledge head {head} mid {mid} left {left}", LEDGE, r, probes=probes, box=box, x=256, **base)
    # every middle probe on its own, over a wide box so the loop runs to each probe
    wide = (-40, -52, 40, 60)
    for i, dx in enumerate((28, 24, 16, 8, 4, 0, -4, -12, -16, -24, -32, -36)):
        kind = (T_ONE, T_ZT, T_HALF)[i % 3]
        yield case(f"ledge wide blocked at {dx} kind {kind}", LEDGE, r, probes={40: T_TWO, dx: kind, -40: T_THREE},
                   box=wide, x=256, **base)
    yield case("ledge wide clear", LEDGE, r, probes={40: T_TWO}, box=wide, x=256, **base)
    yield case("ledge wide clear and ledge", LEDGE, r, probes={40: T_TWO, -40: T_FOUR}, box=wide, x=256, **base)
    yield case("ledge wide left support", LEDGE, r, probes={40: T_THREE, -40: T_ONE}, box=wide, x=256, **base)
    # narrow boxes where the middle loop is skipped
    for left, right in ((-4, 8), (-4, 7), (-4, 9), (0, 12), (0, 13), (-8, 0), (3, 3), (5, 2)):
        yield case(f"ledge narrow box {left}..{right}", LEDGE, r, probes={right: T_ONE, left: T_FOUR}, box=(left, -52, right, 60),
                   x=256, **base)
    for base_name in ("air", "air2", "zero"):
        yield case(f"ledge base {base_name}", LEDGE, r, base=base_name, probes={16: T_ONE}, box=box, x=264, **base)
    for dy in (0, 1):
        yield case(f"ledge feet row offset {dy}", LEDGE, r, probes={16: T_HALF, -16: T_ONE}, box=box, x=264, y=100 + dy, **base)
    for _ in range(3):
        rx = r.randrange(200, 300)
        rl, rr = -r.randrange(5, 30), r.randrange(15, 40)
        probes = {}
        for dx in range(rl, rr + 1, 4):
            if r.random() < 0.25:
                probes[dx] = r.choice((T_ONE, T_TWO, T_THREE, T_ZT, T_ZZT, T_FOUR, T_HALF))
        probes[rr] = r.choice((T_ONE, T_TWO, T_THREE))
        yield case("ledge random", LEDGE, r, x=rx, probes=probes, box=(rl, -52, rr, 60), **base)


def fly_cases(r):
    n = 0
    zero_vec = (0.0, 0.0, 0.0)
    small_vec = (0.1, 0.0, 0.0)
    big_vec = (1.5, -2.25, 0.5)
    # (vec, origin) pairs selecting the three math outcomes: zero, linear and quadratic
    for vec_name, vec in (("zero", zero_vec), ("small", small_vec), ("tiny", (0.2, 0.2, 0.0)), ("big", big_vec),
                          ("opposed", (0.0, 4.0, -5.0)), ("aligned", (0.0, -4.0, 5.0)), ("axis", (-6.0, 0.0, 0.0))):
        for origin in ((10.0, 20.0), (-30.0, 0.0)):
            n += 1
            yield case(f"fly math {vec_name} origin {origin}", FLY, r, in8=1, s46=200, ms=8, vec=vec, origin=origin,
                       s18=70, s19=-35 + n, g7220=0, weapon=0, s45=n % 2, dt=n % 17 + 3)
    yield case("fly input off", FLY, r, in8=0, s46=100, ms=8)
    yield case("fly no timer", FLY, r, in8=1, s46=0, ms=8)
    for s46, ms in ((9, 8), (8, 8), (7, 8), (250, 8), (0x80000005, 8), (0xFFFFFFFF, 8), (1, 1), (2, 1)):
        yield case(f"fly timer {s46:x} ms {ms}", FLY, r, in8=1, s46=s46, ms=ms, vec=big_vec, s18=33, s19=-90)
    for g7220, weapon, s45 in ((1, 0, 0), (1, 0x26BC, 5), (0, 0x26BC, 0), (0, 0x26BC, 7), (0, 0, 0), (0, 0, 9), (0, 0x26B0, 3)):
        for s46, (s18, s19) in zip((60, 250, 400), ((200, -50), (30, 31), (-200, 400))):
            n += 1
            yield case(f"fly const g7220 {g7220} weapon {weapon:x} s45 {s45} s46 {s46} s18 {s18} s19 {s19}", FLY, r, in8=1,
                       s46=s46, ms=5, g7220=g7220, weapon=weapon, s45=s45, s18=s18, s19=s19,
                       vec=(big_vec, small_vec, zero_vec)[n % 3], origin=(r.uniform(-90, 90), r.uniform(-90, 90)))
    for _ in range(8):
        yield case("fly random", FLY, r, in8=1, s46=r.randrange(1, 600), ms=r.randrange(1, 60), g7220=r.randrange(0, 2),
                   weapon=r.choice((0, 0x26BC)), s45=r.randrange(0, 3), s18=r.randrange(-500, 500), s19=r.randrange(-500, 500),
                   vec=(r.uniform(-9, 9), r.uniform(-9, 9), r.uniform(-9, 9)), origin=(r.uniform(-90, 90), r.uniform(-90, 90)))


def rand_cases(r):
    for value in list(range(12)) + [12, 23, 0x7FFFFFFF, 0x80000000, 0x80000007, 0xFFFFFFF4]:
        yield case(f"random sound {value:#x}", RANDSND, r, rand=(value,))
    for _ in range(4):
        value = r.randrange(0, 1 << 15)
        yield case(f"random sound random {value}", RANDSND, r, rand=(value,))


def spike_cases(r):
    n = 0
    for splash in (0, 1):
        for sm30 in (0, 5):
            for snd in (0, 4):
                for deathtile in (False, True):
                    n += 1
                    yield case(f"spike splash {splash} sm30 {sm30} snd {snd} deathtile {deathtile}", SPIKE, r, splash=splash,
                               sm30=sm30, snd=snd, deathtile=deathtile, effect=EFFECTS[n % 6], **S1_MODES[n % 3], gs=1,
                               face=n % 2, state=(6, 4, 1)[n % 3], cflags=0x10 if n % 3 == 0 else 0,
                               claw_raw={0x4C: 100 + 8 * n, 0x64: 7 * n})
    for i, effect in enumerate(EFFECTS):
        yield case(f"spike effect {i}", SPIKE, r, effect=effect, gs=1, **S1_MODES[i % 3], face=i % 2)
    for weapon in (0, 0x26B7, 0x26B8, 0x26B9, 0x26BA):
        n += 1
        yield case(f"spike weapon {weapon:x}", SPIKE, r, ctable=False, weapon=weapon, gs=(1, 3, 2)[n % 3], deathtile=True)
    for weapon, pick in ((0x26B8, 0), (0x26B9, 25), (0x26BA, 26), (5, 13), (0x26B0, 7), (0x26B8, 51)):
        n += 1
        yield case(f"spike dead message weapon {weapon:x} pick {pick}", SPIKE, r, ctable=False, weapon=weapon, gs=4, rand=(pick,),
                   deathtile=n % 2 == 0, snd=n, sm30=0, **S1_MODES[n % 3])
    for i in range(3):
        yield case(f"spike splash registered {i}", SPIKE, r, ctable=False, splash=1, splashmap=True, gs=1, x=200 + 37 * i,
                   y=150 + 11 * i, claw_raw={0x64: 21 + 9 * i}, face=i % 2, **S1_MODES[i])
    for gs in (3, 0, 5):
        yield case(f"spike game state {gs}", SPIKE, r, gs=gs)
    yield case("spike empty map", SPIKE, r, maps=NO_MAPS, s1=1, deathtile=True, snd=2)
    for s1, saved in itertools.product((0, 1), (False, True)):
        for face in (0, 1):
            yield case(f"spike pending s1 {s1} saved {saved} face {face} no maps", SPIKE, r, maps=NO_MAPS, s1=s1,
                       saved_anim=saved, face=face, splash=face, deathtile=bool(s1), snd=3, sm30=0, gs=1,
                       effect=EFFECTS[(s1 + 2 * face) % 4])


def tileq_cases(r):
    sizes = (((512, 512), (3, 3)), ((640, 384), (4, 3)), ((320, 512), (3, 5)))
    n = 0
    for (size, shift) in sizes:
        w, h = size
        for x, y, box_bottom in ((50, 50, 20), (0, 0, 0), (-7, -9, 5), (w - 1, h - 1, 0), (w + 40, h + 30, 9),
                                 (w // 2 + 3, h // 2 + 5, 30), (11, h - 4, 40), (w - 5, 17, -3)):
            for dx in ((0, 9, -77), (33, -8, 700), (-900, 5, 12))[n % 3][:2 if n % 2 else 1]:
                n += 1
                yield case(f"tileq size {size} pos {x},{y} dx {dx}", TILEQ, r, size=size, shift=shift, x=x, y=y, dx=dx, wide=True,
                           random_tiles=True, claw_raw={0x124: box_bottom}, state=7)
    for base_name in ("air", "zero"):
        for dx in (5,):
            yield case(f"tileq base {base_name} dx {dx}", TILEQ, r, base=base_name, dx=dx, x=100, y=100, wide=True, state=7)
    for _ in range(5):
        size, shift = r.choice(sizes)
        yield case("tileq random", TILEQ, r, size=size, shift=shift, x=r.randrange(-20, size[0] + 20),
                   y=r.randrange(-20, size[1] + 20), dx=r.randrange(-60, 60), wide=True, random_tiles=True,
                   claw_raw={0x124: r.randrange(-5, 80)})


# ------------------------------------------------------------------------------------------------
def arc_object(values):
    def setup(env):
        obj = env.object(0xC0, "arc-object", fill=0)
        for index, offset in enumerate(range(0x08, 0xB8, 8)):
            env.put(obj + offset, *words(1.0 + 0.0625 * (index + 1)))
        for offset, value in values.items():
            env.put(obj + offset, *words(value))
        return {"obj": obj}
    return setup


NAN = 0x7FF8000000000000
NEG_ZERO = 0x8000000000000000
INF = float("inf")
DENORM = 0x0000000000000003


def arc_case(label, function, values, argument):
    return Case(label, function, arc_object(values), receiver=lambda t: t["obj"], arguments=words(argument))


def arc_cases(function, factor_off, value_off, arg_off, extra=None):
    extra = extra or {}
    base = 0.75
    args = (base, base + 1.25, base - 3.75)

    def make(label, factor, value, arg):
        return arc_case(f"arc {function:#x} {label}", function, {factor_off: factor, value_off: value, arg_off: base, **extra}, arg)

    for fi, factor in enumerate((1.5, -1.5)):
        for vi, value in enumerate((0.0, NEG_ZERO, 2.5, -2.5)):
            for ai, arg in enumerate(args):
                yield make(f"f{fi} v{vi} a{ai}", factor, value, arg)
    for value in (2.5, -2.5, 0.0):
        yield make(f"small factor v{value}", 0.3, value, base + 1e-3)
    for fi, factor in enumerate((0.0, NEG_ZERO, NAN, INF, DENORM)):
        for value in (2.5, -2.5):
            yield make(f"special f{fi} v{value}", factor, value, base + 1.25)
    yield make("minus infinity", 1.5, -INF, base + 1.25)
    yield make("nan value", 1.5, NAN, base + 1.25)
    yield make("nan argument", 1.5, 2.5, NAN)
    for factor, value, arg in itertools.product((0.5, -2.0), (0.25,), (0.0, 1.75)):
        yield arc_case(f"arc {function:#x} grid {factor} {value} {arg}", function,
                       {factor_off: factor, value_off: value, arg_off: base + 0.5, **extra}, arg + 0.5)


def fract_cases(r):
    def setup_for(values, flag):
        def setup(env):
            obj = env.object(0xC0, "fraction-block", fill=0)
            for index, offset in enumerate(range(0x08, 0xB8, 8)):
                env.put(obj + offset, *words(3.0 + 0.03125 * (index + 1)))
            for offset, value in values.items():
                env.put(obj + offset, *words(value))
            env.put(obj + 0xA0, flag)
            return {"obj": obj}
        return setup
    n = 0
    for flag in (1, 0x80000000):
        n += 1
        yield Case(f"fract flag {flag:x}", FRACT, setup_for({0x90: 1.5, 0xB0: 0.6}, flag), receiver=lambda t: t["obj"])
    for motion in (0.0, 0.4, 0.5, 1.0, 1.5, 2.25, -0.4, -0.5, -1.0, -2.75, 123456.789, -123456.789, 1.0e-300):
        for carry in (0.0, 0.3, 0.6, -0.6, 1.75):
            n += 1
            if n % 3:
                continue
            yield Case(f"fract motion {motion} carry {carry}", FRACT, setup_for({0x90: motion, 0xB0: carry}, 0),
                       receiver=lambda t: t["obj"])
    for motion, carry in ((0.5, 0.5), (0.75, 0.25), (-0.5, -0.5), (0.999999, 0.000002), (3.0, -1.0)):
        yield Case(f"fract rounding {motion} {carry}", FRACT, setup_for({0x90: motion, 0xB0: carry}, 0), receiver=lambda t: t["obj"])
    for _ in range(8):
        yield Case("fract random", FRACT, setup_for({0x90: r.uniform(-50, 50), 0xB0: r.uniform(-3, 3)}, 0), receiver=lambda t: t["obj"])


def cases(random_source):
    r = random_source
    yield from climb_cases(r)
    yield from climb_end_cases(r)
    yield from msg_cases(r)
    yield from ledge_cases(r)
    yield from fly_cases(r)
    yield from rand_cases(r)
    yield from spike_cases(r)
    yield from tileq_cases(r)
    yield from arc_cases(ARC_V, 0x20, 0x38, 0x50)
    yield from arc_cases(ARC_STEP, 0x18, 0x30, 0x48, {0x90: 0.625})
    yield from fract_cases(r)
