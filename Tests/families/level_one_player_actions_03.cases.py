"""Cases for level_one_player_actions_03: Observed Level 1 player actions batch 3.

Every random value is drawn when the case list is generated, never inside a
setup function, so each setup rebuilds the identical memory image.
"""
import math
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

M = 0xFFFFFFFF

F_B630 = 0x41B630
F_C4E0 = 0x41C4E0
F_C5A0 = 0x41C5A0
F_CE80 = 0x41CE80
F_D6F0 = 0x41D6F0
F_D750 = 0x41D750
F_D850 = 0x41D850
F_DE90 = 0x41DE90
F_E710 = 0x41E710
F_F850 = 0x41F850
F_FC30 = 0x41FC30

RAND = 0x4A3050
TILE = "tile"

G_INPUT = 0x537204      # pointer to the input state: +4 pressed, +8 held, +0xc latched
G_STEP = 0x5430C4       # animation step
G_DT = 0x53720C         # frame time
G_POWER = 0x534EAC
G_POWER_TIME = 0x534EA8
G_NOPHYSICS = 0x534E58
G_SOUND = 0x532C0C
G_UI = 0x5371FC         # the game object: +0x2c is the engine, whose vtable +0x10 is queried
G_NOTIFY = 0x5349DC
G_DEATH = 0x537960
G_FLAGS = {"mute": 0x53C9A4}
MOTION = 0x534DB8       # the player's motion state, doubles
MOTION_END = 0x534EA8

BASE_NAMES = ("CLAW_STAND", "CLAW_JUMP", "CLAW_FALL", "CLAW_WALK", "CLAW_LAND", "CLAW_CLIMB", "CLAW_DUCK",
              "CLAW_IDLE", "CLAW_LIFTWALK", "CLAW_LIFT2", "CLAW_LOOKUP", "CLAW_TEETER", "CLAW_THROW")
ATTACK_NAMES = (
    "CLAW_SWIPE", "CLAW_POWERUPSWIPE", "CLAW_UPPERCUT", "CLAW_EMPTYPISTOL", "CLAW_PISTOL", "CLAW_EMPTYMAGIC",
    "CLAW_MAGIC", "CLAW_DUCKSWIPE", "CLAW_DUCKPOWERUPSWIPE", "CLAW_JUMPSWIPE", "CLAW_JUMPPOWERUPSWIPE",
    "CLAW_EMPTYJUMPPISTOL", "CLAW_JUMPPISTOL", "CLAW_EMPTYJUMPMAGIC", "CLAW_JUMPMAGIC", "CLAW_EMPTYDYNAMITE",
    "CLAW_PREDYNAMITE", "CLAW_POSTDYNAMITE", "CLAW_PUNCH", "CLAW_KICK", "CLAW_DUCKEMPTYPISTOL", "CLAW_DUCKPISTOL",
    "CLAW_DUCKEMPTYMAGIC", "CLAW_DUCKMAGIC", "CLAW_DUCKEMPTYDYNAMITE", "CLAW_DUCKPREDYNAMITE",
    "CLAW_DUCKPOSTDYNAMITE", "CLAW_EMPTYJUMPDYNAMITE", "CLAW_JUMPDYNAMITE", "CLAW_FALLDEATH", "CLAW_LIFT",
    "CLAW_DUCKLIFT", "CLAW_DAMAGE1", "CLAW_DAMAGE2")
NAMES = BASE_NAMES + ATTACK_NAMES
SOUND_NAMES = ("CLAW_HIT", "GAME_HIT1", "GAME_HIT2", "GAME_HIT3", "GAME_HIT4", "CLAW_1110048", "CLAW_1110049",
               "CLAW_1110050", "CLAW_1110051", "CLAW_LEFTFOOT1", "GAME_CLICK")
SPAWN_NAMES = ("PistolBullet", "MagicBullet", "Dynamite", "FireBullet", "LightningBullet", "IceBullet", "HitBurst",
               "GlitterMother")

def thin(generator, stride, offset=0):
    """Keep every stride-th case. The generator still draws everything, so the kept cases are stable."""
    for position, item in enumerate(generator):
        if position % stride == offset:
            yield item


def f64(value):
    return struct.pack("<d", float(value))


# --------------------------------------------------------------------------
# Object builders
# --------------------------------------------------------------------------

def string_map(env, entries, buckets=1):
    """An object whose +0x10 is a string hash map. Entries are chained in order inside their bucket."""
    holder = env.object(0x40, "map-owner", fill=0)
    table = env.object(4 * buckets + 4, "map-buckets", fill=0)
    env.put(holder + 0x14, table, buckets)
    heads = [0] * buckets
    for key, value in reversed(entries):
        hashed = 0
        for byte in key.encode():
            hashed = (hashed * 0x21 + (byte - 256 if byte > 127 else byte)) & M
        slot = hashed % buckets
        key_pointer = env.object(len(key) + 4, "map-key", data=key.encode() + b"\0")
        node = env.object(0x10, "map-node", fill=0)
        env.put(node, heads[slot], 0, key_pointer, value)
        heads[slot] = node
    for slot, head in enumerate(heads):
        env.put(table + 4 * slot, head)
    return holder


def animation(env, value, delay=0, kind=9):
    """An animation of one frame. Stepping it returns `value` (the frame's +0x1c)."""
    frame = env.object(0x40, "frame", fill=0)
    env.put(frame + 0x0C, kind)
    env.put(frame + 0x18, delay)
    env.put(frame + 0x1C, value)
    frames = env.object(8, "frames", fill=0)
    env.put(frames, frame)
    result = env.object(0x40, "animation", fill=0)
    env.put(result + 0x0C, frames)
    env.put(result + 0x10, 1)
    return result


def tile_effect(rules):
    def effect(env, call):
        x, y = call.arguments[0], call.arguments[1]
        for x0, y0, x1, y1, cls in rules:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return cls
        return 0
    return effect


def collision_world(env, rules, empty=False, margin=(300, 300)):
    """One giant tile; the tile's class function is a pure function of the position."""
    tile_map = env.object(0x100, "tile-map", fill=0)
    cells = env.object(8, "tile-cells", fill=0)
    rows = env.object(8, "tile-rows", fill=0)
    tiles = env.object(8, "tile-table", fill=0)
    tile = env.object(8, "tile", fill=0)
    vtable = env.object(0x40, "tile-vtable", fill=0)
    env.put(tile, vtable)
    env.put(vtable + 0x20, env.stub(TILE, "thiscall", 2, tile_effect(rules)))
    env.put(tiles, tile)
    env.put(cells, 0xEEEEEEEE if empty else 0)
    env.put(rows, 0)
    env.put(tile_map + 0x20, cells)
    env.put(tile_map + 0x24, rows)
    env.put(tile_map + 0x30, 2048, 2048)
    env.put(tile_map + 0x8C, 12, 12)
    world = env.object(0x100, "collision-world", fill=0)
    env.put(world + 0x4C, tiles)
    env.put(world + 0x5C, tile_map)
    env.put(world + 0x64, margin[0], margin[1])
    holder = env.object(0x40, "world-holder", fill=0)
    inner = env.object(0x40, "world-inner", fill=0)
    env.put(holder + 8, inner)
    env.put(world + 0x0C, holder)
    return world


# --------------------------------------------------------------------------
# The shared world
# --------------------------------------------------------------------------

ACTOR_POINTERS = (0x0C, 0x6C, 0x80, 0x170, 0x174, 0x188, 0x18C, 0x190, 0x194, 0x198, 0x19C, 0x1A0, 0x1A4,
                  0x1A8, 0x1AC, 0x1B0, 0x1B4)


def near(r, ref):
    """A counter value around a step size: both sides of the subtraction in the timers."""
    return r.choice((0, 1, max(0, ref - 1), ref, ref + 1, ref * 3, 3000, 20000, r.randrange(0, 40000)))


def draw(r, **override):
    """All the numbers of one world."""
    step = r.randrange(1, 40)
    dt = r.randrange(1, 40)
    spec = {
        "seed": r.getrandbits(32),
        "flags": r.getrandbits(32) & ~0x400090,      # actor +8
        "x": r.randrange(200, 1800),
        "y": r.randrange(200, 1800),
        "mode": r.choice((1, 2, 3, 4, 5, 6)),         # actor +0xcc
        "state": 0x18,                                # state object +0x1c
        "p0": r.choice((0, 1)),                       # facing
        "p1": 0,                                      # attack active
        "p2": r.choice((0, 1)), "p3": r.choice((0, 1)),
        "p7": r.choice((0, 1)), "p8": r.choice((0, 1)),
        "p_f": 0,                                     # attack kind P[0xf]
        "p_c": r.choice((1, 2, 3)),
        "p21": r.randrange(-300, 300),
        "p_x": 0,                                     # P[0x4b] linked actor
        "q_size": 0x20,                               # bitset of the linked actor's logic
        "q_count": r.randrange(0, 3),                 # Q[0x20]
        "p49": True, "p4a": True,
        "timers": [near(r, r.choice((step, dt))) for _ in range(6)],
        "p3c": near(r, step),
        "p10": r.choice((0, 5, 599, 600, 601, 999, 1000, 1001, r.randrange(-2000, 5000))),
        "step": step,
        "dt": dt,
        "input": [0, 0, 0],                           # +4, +8, +0xc
        "power": 0,
        "nophysics": 0,
        "rules": [],
        "empty_tiles": False,
        "margin": (300, 300),
        "player": "raw",                              # state of the animation player
        "pvalue": 0x333,                              # what stepping the player's animation returns
        "pvalue2": 0x332,
        "delay": 0,
        "present": NAMES,                             # animation names in the level's map
        "sound_off": 1,
        "motion": r.getrandbits(32),
        "platform": False,
        "mover": (r.randrange(-20, 20), r.randrange(-20, 20)),
        "rand": r.getrandbits(32),
        "engine": 1,                                  # what the engine query returns
        "resume": (-1, -1),                           # engine +0x44/+0x48
        "notify": False,
        "death": 0,
        "limits": None,
        "lookup": None,
        "st_timer": 0,
        "p19": None,
        "globals_extra": {},
        "p13": (r.randrange(200, 1800), r.randrange(200, 1800)),
        "probe_items": True,
    }
    spec.update(override)
    return spec


def build(env, s):
    """Create the actor, its data, the level and the globals. Returns the addresses."""
    noise = random.Random(s["seed"])
    tok = {}

    def word():
        return noise.getrandbits(32)

    def make_probe(kind):
        low, high = (0, 0x200) if kind == "wide" else (0x100, 0x200)
        array = env.object(4 * 0x202, "probe-array", words=[word() for _ in range(0x202)])
        for index in range(0x17F, 0x186):
            if s["probe_items"] and noise.getrandbits(2):
                env.put(array + 4 * index, env.object(0x40, "probe-item", words=[word() for _ in range(0x10)]))
            else:
                env.put(array + 4 * index, 0)
        result = env.object(0x80, "probe", words=[word() for _ in range(0x20)])
        env.put(result + 0x14, array)
        env.put(result + 0x64, low, 0, 0, high)
        return result

    # the level: collision world, sound map, animation map
    world = collision_world(env, s["rules"], s["empty_tiles"], s["margin"])
    anims = {}
    for index, name in enumerate(NAMES):
        anims[name] = animation(env, 0x100 + index * 7 + (word() & 3), delay=s["delay"])
    anims["CLAW_STAND"] = animation(env, s["pvalue"], delay=s["delay"])
    entries = [("CLAW_ZZZ", word() | 1)]
    for name in s["present"]:
        entries.append((name, anims[name]))
    entries.append(("CLAW_STANDX", word() | 1))
    animation_owner = string_map(env, entries)
    sound_owner = string_map(env, [("CLAW_LEFTFOOT1", env.object(0x20, "sound", fill=0)), ("GAME_CLICK", env.object(0x20, "sound", fill=0))])
    env.put(sound_owner + 0x30, s["sound_off"])
    level = env.object(0x80, "level", fill=0)
    holder = env.object(0x40, "level-holder", fill=0)
    env.put(level + 8, holder)
    env.put(level + 0x24, world)
    env.put(level + 0x28, sound_owner)
    env.put(level + 0x2C, animation_owner)
    level_maps = string_map(env, [("LEVEL_DECOY", word() | 1)])
    env.put(level + 0x14, level_maps)
    named = [("CLAW_X", word() | 1)]
    if s.get("lookup"):
        named.append(("CLAW", make_probe(s["lookup"])))
    named.append(("CLAWS", word() | 1))
    env.put(level + 0x10, string_map(env, named))

    # the linked actor and its logic
    linked = 0
    queue = 0
    if s["p_x"]:
        size = s["q_size"]
        queue = env.object(0x340, "linked-logic", words=[word() for _ in range(0xD0)])
        env.put(queue + 0x20, s["q_count"])
        env.put(queue + 0x14, word())
        env.put(queue + 0x2FC, size)
        vtable = env.object(0x100, "linked-vtable", fill=0)
        for slot in (0x80, 0x84, 0x88, 0xA0, 0xB0):
            env.put(vtable + slot, env.stub(f"Q::{slot:#x}", "thiscall", 0, lambda env, call: 0))
        env.put(queue, vtable)
        if size > 0x20:
            data = env.object(4 * ((size + 31) // 32) + 4, "bits", words=[word() for _ in range(((size + 31) // 32) + 1)])
            env.put(queue + 0x300, data)
            tok["bits"] = data
        else:
            env.put(queue + 0x300, word())
        logic = env.object(0x80, "linked-state", words=[word() for _ in range(0x20)])
        env.put(logic + 0x18, queue)
        linked = env.object(0x80, "linked", words=[word() for _ in range(0x20)])
        env.put(linked + 0x6C, logic)

    # the player data
    p = env.object(0x138, "player-data", words=[word() for _ in range(0x4E)])
    state = env.object(0x140, "state", words=[word() for _ in range(0x50)])
    env.put(state + 0x14, p)
    env.put(state + 0x1C, s["state"])
    env.put(state + 0x18, queue)
    limits = s["limits"] or (0, 2047, 0, 2047)
    env.put(state + 0x2C, limits[0], limits[2], limits[1], limits[3])
    env.put(state + 0x130, s["st_timer"])
    env.put(p + 0, s["p0"])
    env.put(p + 4, s["p1"])
    env.put(p + 8, s["p2"], s["p3"])
    env.put(p + 0x1C, s["p7"], s["p8"])
    env.put(p + 0x30, s["p_c"])
    env.put(p + 0x3C, s["p_f"])
    env.put(p + 0x40, s["p10"])
    env.put(p + 0x84, s["p21"])
    env.put(p + 0xF0, s["p3c"])
    env.put(p + 0x4C, s["p13"][0], s["p13"][1])
    env.put(p + 0x64, s["p19"] if s.get("p19") is not None else s["y"] - 45 + noise.randrange(-3, 4))
    env.put(p + 0x18, 1 | word())
    env.put(p + 0x12C, linked)
    env.put(p + 0x130, 0, linked)
    stored = animation(env, 0x500 + (word() & 0xFF)) if s["p49"] else 0
    stored2 = animation(env, 0x600 + (word() & 0xFF)) if s["p4a"] else 0
    env.put(p + 0x124, stored)
    env.put(p + 0x128, stored2)
    timers = s["timers"]
    env.put(p + 0x114, timers[0])      # P[0x45]
    env.put(p + 0xFC, timers[1])       # P[0x3f]
    env.put(p + 0x120, timers[2])      # P[0x48]
    env.put(p + 0x118, timers[3])      # P[0x46]
    env.put(p + 0xF8, timers[4])       # P[0x3e]
    tok["stored"] = stored
    tok["stored2"] = stored2

    # the actor
    actor = env.object(0x200, "actor", words=[word() for _ in range(0x80)])
    for offset in ACTOR_POINTERS:
        env.put(actor + offset, 0)
    env.put(actor + 8, s["flags"])
    env.put(actor + 0x0C, level)
    env.put(actor + 0x4C, s["x"], s["y"])
    env.put(actor + 0x6C, state)
    env.put(actor + 0xCC, s["mode"])
    env.put(actor + 0xDC, 6, 5)
    env.put(actor + 0x118, 0xFFFFFFF0, 0xFFFFFFCC, 0x10, 0x3C)
    env.put(actor + 0x128, 0xFFFFFFF1, 0xFFFFFFD3, 0x16, 0x34)
    env.put(actor + 0x138, 0xFFFFFFF1, 0xFFFFFFD3, 0x16, 0x22)
    env.put(actor + 0x148, noise.randrange(-300, 300) & M, noise.randrange(-300, 300) & M)
    env.put(actor + 0x18C, actor)
    if s.get("probe"):
        probe = make_probe(s["probe"])
        env.put(actor + 0x170, probe)
        env.put(actor + 0x16C, noise.randrange(0, 0x200))
        tok["probe"] = probe
    if s["platform"]:
        mover = env.object(0x180, "mover", words=[word() for _ in range(0x60)])
        env.put(mover + 0xD0, 0x80)
        env.put(mover + 0x158, s["mover"][0] & M, s["mover"][1] & M)
        env.put(actor + 0x80, mover)
        env.put(actor + 8, s["flags"] | 0x10)
        tok["mover"] = mover
    # the animation player embedded at +0x188
    mode = s["player"]
    if mode != "none":
        stepped = anims["CLAW_STAND"]
        env.put(actor + 0x190, stepped)
        env.put(actor + 0x194, env.get(env.get(stepped + 0x0C)))
        env.put(actor + 0x198, 0)
        env.put(actor + 0x19C, s["timers"][5] if mode == "raw" else 0)
        env.put(actor + 0x1A0, noise.getrandbits(1))
        env.put(actor + 0x1A4, 1 if mode != "fresh" else 0)
        env.put(actor + 0x1A8, s["pvalue"], s["pvalue2"])
        env.put(actor + 0x1B0, 0x3F800000)
    # the game object the player logic queries
    ui = env.object(0x100, "ui", fill=0)
    engine = env.object(0x800, "engine", fill=0)
    engine_vtable = env.object(0x40, "engine-vtable", fill=0)
    env.put(engine_vtable + 0x10, env.stub("Engine::query", "thiscall", 0, returns(s["engine"])))
    env.put(engine, engine_vtable)
    env.put(engine + 0x44, s["resume"][0] & M, s["resume"][1] & M)
    env.put(ui + 0x2C, engine)
    env.put(G_UI, ui)
    if s["notify"]:
        notify_vtable = env.object(0x100, "notify-vtable", fill=0)
        env.put(notify_vtable + 0xB0, env.stub("Notify::0xb0", "thiscall", 0, returns(0)))
        notify_queue = env.object(0x40, "notify-queue", fill=0)
        env.put(notify_queue, notify_vtable)
        notify_state = env.object(0x40, "notify-state", fill=0)
        env.put(notify_state + 0x18, notify_queue)
        notify = env.object(0x80, "notify", fill=0)
        env.put(notify + 0x6C, notify_state)
        env.put(G_NOTIFY, notify)
    else:
        env.put(G_NOTIFY, 0)
    death = env.object(0x100, "death", fill=0)
    env.put(death + 0x44, s["death"])
    env.put(G_DEATH, death)
    # the input and the globals
    inp = env.object(0x20, "input", words=[word(), s["input"][0], s["input"][1], s["input"][2]])
    env.put(G_INPUT, inp)
    env.put(G_STEP, s["step"])
    env.put(G_DT, s["dt"])
    env.put(G_POWER, s["power"])
    env.put(G_POWER_TIME, s.get("power_time", 0))
    env.put(G_NOPHYSICS, s["nophysics"])
    env.put(G_SOUND, 0)
    mrand = random.Random(s["motion"])
    for address in range(MOTION, MOTION_END, 8):
        env.write(address, f64(mrand.uniform(-40, 40)))
    env.put(G_NOPHYSICS, s["nophysics"])
    for address, value in s["globals_extra"].items():
        env.put(address, value)
    for address, value in s.get("globals", {}).items():
        env.put(address, value)
    for address, value in s.get("doubles", {}).items():
        env.write(address, f64(value))
    rolls = random.Random(s["rand"])
    env.override(RAND, sequence(*[rolls.getrandbits(15) for _ in range(24)]))
    tok.update(actor=actor, state=state, p=p, level=level, input=inp, world=world, linked=linked, queue=queue,
               animation_owner=animation_owner, sound_owner=sound_owner, anims=anims)
    return tok


def call(label, function, s, extra=None, arguments=None):
    def setup(env):
        tok = build(env, s)
        extend(env, tok, s)
        if extra:
            extra(env, tok)
        return tok

    if arguments is None:
        arguments = (lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"])
    return Case(label, function, setup, arguments=arguments)


def geometry(r, x, y):
    """A few solid regions around the actor (hit box: 16 each side, 52 up, 60 down)."""
    rules = []
    for kind in r.sample(("floor", "wall_right", "wall_left", "ladder", "oneway", "pit", "ceiling", "kill"), r.randrange(0, 4)):
        if kind == "floor":
            rules.append((0, y + 61 + r.randrange(-6, 14), 2047, 2047, 1))
        elif kind == "wall_right":
            rules.append((x + 17 + r.randrange(-3, 40), 0, x + 80, 2047, 1))
        elif kind == "wall_left":
            rules.append((x - 80, 0, x - 17 - r.randrange(-3, 40), 2047, 1))
        elif kind == "ladder":
            rules.append((x - 30, y - 150, x + 30, y + 150, 3))
        elif kind == "oneway":
            rules.append((0, y + 61 + r.randrange(-6, 14), 2047, y + 70 + r.randrange(0, 20), 2))
        elif kind == "pit":
            rules.append((x - 40, y + 61, x + 40, y + 400, 0))
        elif kind == "ceiling":
            rules.append((0, 0, 2047, y - 53 + r.randrange(-4, 20), 1))
        else:
            rules.append((x - 40, y + 20, x + 40, y + 70, 4))
    return rules


def input_bits(r, arrows=None):
    arrows = r.getrandbits(4) if arrows is None else arrows
    return [r.choice((0, 0, 1, 8, 9, 2, 0x20, 0x22)), (arrows << 24) | r.choice((0, 0, 1, 4, 0x100)), r.getrandbits(32)]


def sweep_world(r, **override):
    base = draw(r)
    p1 = override.get("p1", r.choice((0, 0, 1)))
    allowed = (0, 1, 4, 6, 0x63, 0x333) if p1 else (0, 1, 2, 3, 5, 6, 0x63, 0x333)
    values = {
        "x": base["x"], "y": base["y"],
        "rules": geometry(r, base["x"], base["y"]),
        "margin": r.choice(((300, 300), (300, 300), (3, 3), (40, 2))),
        "empty_tiles": r.random() < 0.1,
        "power": r.choice((0, 0, 0, 0x26bc, 0x26b8)),
        "nophysics": r.choice((0, 0, 0, 1)),
        "platform": r.random() < 0.2,
        "p_f": r.choice((0, 0, 8, 9, 10, 0x12, 3, 7)),
        "p1": p1,
        "p_x": r.choice((0, 0, 1)),
        "q_size": r.choice((0x20, 0x40, 0x10, 0)),
        "player": r.choice(("raw", "raw", "fresh", "none")),
        "present": r.choice((NAMES, NAMES, ())),
        "sound_off": r.choice((0, 1)),
        "probe": r.choice((None, "wide", "high")),
        "pvalue": r.choice(allowed),
        "pvalue2": r.choice(allowed),
        "input": input_bits(r),
    }
    values.update(override)
    return draw(r, **values)


def grounded(r, **override):
    """The actor stands on a floor and nothing is pressed (or one arrow is)."""
    base = draw(r)
    x, y = base["x"], base["y"]
    allowed = (0, 1, 6, 0x63, 0x333)
    values = {"x": x, "y": y, "rules": [(0, y + 61, 2047, 2047, 1)], "mode": 1, "p_f": 0, "p1": 0, "nophysics": 0,
              "platform": False, "power": 0, "player": "raw", "present": NAMES,
              "pvalue": r.choice(allowed), "pvalue2": r.choice(allowed), "input": input_bits(r, r.choice((0, 0, 1, 2, 4, 8)))}
    values.update(override)
    return draw(r, **values)


PRESSED = (1, 2, 4, 8, 0x20, 0x40, 0x80, 0x100, 0x1000000, 0x2000000)


def pressed_bits(r, extra=0, drop=0):
    bits = 0
    for bit in PRESSED:
        if r.random() < 0.18:
            bits |= bit
    return (bits | extra) & ~drop


def pworld(r, state, **kw):
    base = draw(r)
    x, y = base["x"], base["y"]
    p1 = kw.get("p1", r.choice((0, 0, 1)))
    allowed = (0, 1, 4, 6, 0x63, 0x333) if p1 else (0, 1, 2, 3, 5, 6, 0x63, 0x333)
    power = r.choice((0, 0, 0, 0x26bc, 0x26b8, 0x26b9))
    dt = base["dt"]
    values = {
        "x": x, "y": y, "state": state,
        "rules": geometry(r, x, y),
        "margin": r.choice(((300, 300), (300, 300), (3, 3))),
        "empty_tiles": r.random() < 0.05,
        "power": power, "power_time": r.choice((0, 0, near(r, dt))),
        "nophysics": r.choice((0, 0, 0, 1)),
        "platform": False,
        "p_f": r.choice((0, 0, 8, 9, 10, 0x12, 3, 7)),
        "p1": p1,
        "p_x": r.choice((0, 1)),
        "q_size": r.choice((0x20, 0x40, 0x10, 0)),
        "player": r.choice(("raw", "raw", "fresh", "none")),
        "present": r.choice((NAMES, NAMES, ())),
        "sound_off": r.choice((0, 1)),
        "probe": r.choice((None, "wide", "high")),
        "pvalue": r.choice(allowed), "pvalue2": r.choice(allowed),
        "input": [pressed_bits(r), r.getrandbits(4) << 24 | r.choice((0, 1, 4, 0x100)), r.getrandbits(32)],
        "engine": r.choice((1, 4)),
        "notify": r.random() < 0.5,
        "death": r.choice((0, 0, 2)),
        "st_timer": near(r, dt),
        "limits": r.choice((None, None, (x - 20, x + 20, y - 20, y + 20), (x + 5, x + 30, y + 5, y + 30),
                            (x - 90, x - 20, y - 90, y - 20))),
        "lookup": r.choice((None, "wide", "high")),
        "resume": r.choice(((-1, -1), (-1, 5), (r.randrange(200, 1800), r.randrange(200, 1800)))),
        "globals_extra": {0x537230: r.choice((0, 0, 1)), 0x537214: r.choice((0, 0, 1)),
                          0x53C9F8: r.getrandbits(16), 0x52C6EC: r.getrandbits(8), 0x52C6E4: r.getrandbits(16),
                          0x534EB4: r.choice((0, 1)), 0x53C9C0: r.choice((0, 2, 3)),
                          0x537220: r.choice((0, 1))},
    }
    values.update(kw)
    return draw(r, **values)




# --------------------------------------------------------------------------
# Additions for this family: the actor list, spawn prototypes, sounds, other actors
# --------------------------------------------------------------------------

G_TIME = 0x537210
G_CHEAT_A = 0x537218
G_CHEAT_B = 0x537228
G_CHEAT_C = 0x53725C
G_SOUND_HANDLE = 0x532C10
G_CACHE_TIME = 0x534EC0
G_CACHE_SOUND = 0x534EC4
G_FLASH = 0x534EC8
G_FLASH_FRAME = 0x534ECC
G_MUTE = 0x53C9A4

_stub_count = [0]


def quiet_stub(env, argc=0, convention="thiscall", value=0):
    _stub_count[0] += 1
    return env.stub(f"stub{_stub_count[0]}", convention, argc, returns(value))


def sound_object(env):
    """A sound whose playback returns at once: sound+0x10 -> x, x+0x10 -> y, y+0x78 == 0."""
    x = env.object(0x40, "sound-x", fill=0)
    y = env.object(0x90, "sound-y", fill=0)
    env.put(x + 0x10, y)
    sound = env.object(0x20, "sound", fill=0)
    env.put(sound + 0x10, x)
    return sound


def anim_set(env, r, low, high, items=True):
    """An object like a sprite probe: +0x64 first index, +0x68 last, +0x14 an array of items with +0x30 objects."""
    word = lambda: r.getrandbits(32)
    array = env.object(4 * (high + 2), "set-array", words=[word() for _ in range(high + 2)])
    for index in range(low, high + 1):
        if items and r.getrandbits(2):
            target = env.object(0x40, "set-target", words=[word() for _ in range(0x10)])
            item = env.object(0x40, "set-item", words=[word() for _ in range(0x10)])
            env.put(item + 0x30, target)
            env.put(array + 4 * index, item)
        else:
            env.put(array + 4 * index, 0)
    result = env.object(0x80, "set", words=[word() for _ in range(0x20)])
    env.put(result + 0x14, array)
    env.put(result + 0x64, low, 0, 0, high)
    return result


def make_actor(env, r, spec=None):
    """An actor with a logic object and a queue object (vtable slots stubbed, bit set of `bits` bits)."""
    spec = dict(spec or {})
    bits = spec.pop("bits", 0x20)
    count = spec.pop("count", 1)
    word = lambda: r.getrandbits(32)
    queue = env.object(0x340, "queue", words=[word() for _ in range(0xD0)])
    env.put(queue + 0x20, count)
    vtable = env.object(0x100, "queue-vtable", fill=0)
    for slot in (0x2C, 0x80, 0x84, 0x88, 0xA0, 0xB0):
        env.put(vtable + slot, quiet_stub(env))
    env.put(queue, vtable)
    env.put(queue + 0x0C, env.object(0x80, "queue-owner", words=[word() for _ in range(0x20)]))
    env.put(queue + 0x2FC, bits)
    if bits > 0x20:
        words = (bits + 31) // 32
        env.put(queue + 0x300, env.object(4 * words + 4, "bits", words=[word() for _ in range(words + 1)]))
    else:
        env.put(queue + 0x300, word())
    logic = env.object(0x180, "logic", words=[word() for _ in range(0x60)])
    env.put(logic + 0x18, queue)
    env.put(logic + 0x168, sound_object(env) if spec.pop("snd", False) else 0)
    actor = env.object(0x200, "actor-x", words=[word() for _ in range(0x80)])
    env.put(actor + 0x6C, logic)
    for offset, value in spec.items():
        env.put(actor + offset, value & M)
    return actor


def extend(env, tok, s):
    """Things only this family needs, applied on top of the world from build()."""
    r = random.Random(s["seed"] ^ 0x5A5A5A5A)
    word = lambda: r.getrandbits(32)
    level, actor, state, p = tok["level"], tok["actor"], tok["state"], tok["p"]
    manager = env.get(level + 8)
    env.put(manager + 0x0C, level)
    owner = string_map(env, [(name, sound_object(env)) for name in s.get("sounds", ())])
    env.put(owner + 0x30, s["sound_off"])
    if s.get("snoise"):
        # distinct non-zero neighbours around the mute slot, so a shifted read gives a different answer
        for position, offset in enumerate((0x1C, 0x20, 0x24, 0x28, 0x2C, 0x34, 0x38, 0x3C)):
            env.put(owner + offset, (0x01010101 * (position + 3)) ^ (s["seed"] | 0x80000001))
    env.put(level + 0x28, owner)
    entries = [("LEVEL_DECOY", word() | 1)]
    for name, flavour in s.get("spawn", {}).items():
        proto = env.object(0x40, "proto", words=[word() for _ in range(0x10)])
        env.put(proto + 8, flavour & 3)
        env.put(proto + 0x10, quiet_stub(env, 1, "cdecl") if flavour else 0)
        entries.append((name, proto))
    env.put(level + 0x14, string_map(env, entries))
    # the actor list the manager owns
    free = 0
    for _ in range(s.get("free", 4)):
        node = env.object(12, "free-node", fill=0)
        env.put(node, free)
        free = node
    env.put(manager + 0x20, free, 0, 10)
    nodes = []
    for spec in s.get("actors", ()):
        node = env.object(12, "list-node", fill=0)
        env.put(node + 8, make_actor(env, r, spec))
        nodes.append(node)
    for index, node in enumerate(nodes):
        env.put(node, nodes[index + 1] if index + 1 < len(nodes) else 0, nodes[index - 1] if index else 0)
    env.put(manager + 0x14, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
    tok["nodes"] = nodes
    if s.get("other") is not None:
        tok["other"] = make_actor(env, r, s["other"])
        env.put(actor + 0x74, tok["other"])
    if s.get("rolls"):
        env.override(RAND, sequence(*s["rolls"]))
    env.put(state + 0x168, sound_object(env) if s.get("state168") else 0)
    env.put(G_SOUND, s.get("sound_on", 0))
    env.put(G_SOUND_HANDLE, word())
    env.put(G_MUTE, 0)
    env.put(G_CHEAT_A, s.get("cheat_a", 0))
    env.put(G_CHEAT_B, s.get("cheat_b", 0))
    env.put(G_CHEAT_C, s.get("cheat_c", 0))
    env.put(G_TIME, s.get("time", 0))
    env.put(G_CACHE_TIME, s.get("cache_time", 0))
    env.put(G_CACHE_SOUND, s.get("cache_sound", 0))
    env.put(G_FLASH, s.get("flash", 0))
    env.put(G_FLASH_FRAME, s.get("flash_frame", 0))
    if s.get("link_other"):
        env.put(p + 0x12C, tok["other"])
    for offset, value in s.get("aset", {}).items():
        env.put(actor + offset, value & M)
    for index, value in s.get("pset", {}).items():
        env.put(p + 4 * index, value & M)
    for offset, value in s.get("sset", {}).items():
        env.put(state + offset, value & M)
    for offset, value in s.get("held", {}).items():
        env.put(tok["input"] + offset, value & M)


# --------------------------------------------------------------------------
# Random worlds
# --------------------------------------------------------------------------

PRESSED_BITS = (1, 2, 4, 8, 0x20, 0x40, 0x80, 0x100)
HELD_BITS = (1, 2, 4, 8, 0x100, 0x1000000, 0x2000000, 0x4000000)
POWERS = (0, 0, 0, 0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC, 0x26BD)


def some_bits(r, bits, chance=0.25):
    value = 0
    for bit in bits:
        if r.random() < chance:
            value |= bit
    return value


def candidate(r, x, y, fixed=None):
    spec = {
        0x04: r.randrange(0, 0x40),
        0x08: r.getrandbits(32) & ~0x10 | r.choice((0, 0x20000)),
        0x4C: x + r.randrange(-160, 160),
        0x50: y + r.choice((r.randrange(-120, 120), r.randrange(-25, 25))),
        0x124: r.choice((60, 0x3C, 50, 40, 0, 70)),
        0x64: r.randrange(0, 0x3000),
        0xD0: r.choice((4, 4, 0x200, 0x10, 0x40, 0)),
        0x128: r.randrange(-30, -5) & M, 0x12C: r.randrange(-60, -30) & M,
        0x130: r.randrange(5, 40), 0x134: r.randrange(30, 60),
        0x164: r.choice((0, 1, 1, 0x400, 0x401, 0x20, 0x21, r.getrandbits(32))),
        "bits": r.choice((0x20, 0x40, 0x10)),
        "count": r.randrange(0, 3),
    }
    spec.update(fixed or {})
    return spec


def other_spec(r, x, y, kind=None):
    kinds = (0x10, 0x1000000, 4, 0x40, 0x100, 0x40000, 0x10000, 0x200000, 0x100000, 0x800000, 0x20, 7, 0)
    kind = r.choice(kinds) if kind is None else kind
    return candidate(
        r, x, y, {
            0xD0: kind,
            0xFC: r.choice((0, 1, 5, 50, 99, 100, 101, 150, 0xFFFFFFFD, 0x26BF if kind == 0x40 else 7,
                            r.randrange(0, 200))),
            0x104: r.choice((0, 0, 1, 3, 5, 20, 0xFFFFFFFC)),
            0x108: r.choice((0, 0, 7, r.randrange(1, 500), 0xFFFFFFF0)),
            0x138: r.choice((0x80000000, 0x80000000, r.randrange(-30, 30) & M)),
            0x13C: r.randrange(-40, 10) & M, 0x144: r.randrange(10, 50),
            0x164: r.choice((0, 0x10, 0x20, 0x30, 0x2, 0x1, r.getrandbits(32))),
            0x04: r.randrange(0, 0x36),
            0x08: r.getrandbits(32) & ~0x10000,
            "snd": r.random() < 0.5,
        })


def rw(r, **kw):
    """One random world with the extra data of this family."""
    base = draw(r)
    x, y = base["x"], base["y"]
    p1 = kw.get("p1", r.choice((0, 0, 1)))
    dt = base["dt"]
    values = {
        "x": x, "y": y,
        "state": r.choice((0x18, 0x18, 0x19, 0x1A, 4, 5000, 0x1F, 1)),
        "rules": geometry(r, x, y),
        "margin": r.choice(((300, 300), (300, 300), (3, 3))),
        "empty_tiles": r.random() < 0.05,
        "power": r.choice(POWERS), "power_time": r.choice((0, 0, near(r, dt), 5, 100000)),
        "nophysics": r.choice((0, 0, 0, 1)),
        "p_f": r.choice((0, 0, 8, 9, 10, 0x12, 3, 7)),
        "p1": p1,
        "p_x": r.choice((0, 1, 1)),
        "q_size": r.choice((0x20, 0x40, 0x10, 0, 0)),
        "q_count": r.randrange(0, 3),
        "player": r.choice(("raw", "raw", "fresh", "none")),
        "present": r.choice((NAMES, NAMES, NAMES, ())),
        "sound_off": r.choice((0, 0, 1)),
        "pvalue": r.choice((0, 1, 2, 3, 4, 5, 6, 0x63, 0x333)),
        "pvalue2": r.choice((0, 1, 2, 3, 4, 5, 6, 0x63, 0x333)),
        "engine": r.choice((1, 4)),
        "mode": r.choice((1, 1, 2, 3, 4, 5, 6, 7, 8)),
        "input": [some_bits(r, PRESSED_BITS), some_bits(r, HELD_BITS), r.getrandbits(32)],
        "timers": [near(r, r.choice((base["step"], dt))) for _ in range(6)],
        "globals_extra": {0x537220: r.choice((0, 1)), 0x53C9C0: r.choice((0, 2))},
        "sounds": list(r.sample(SOUND_NAMES, r.choice((0, len(SOUND_NAMES), len(SOUND_NAMES), 4)))),
        "sound_on": r.choice((0, 1)),
        "spawn": {name: (r.choice((1, 2, 3, 1, 1, 0))) for name in SPAWN_NAMES},
        "actors": [candidate(r, x, y) for _ in range(r.choice((0, 0, 1, 2, 3)))],
        "cheat_a": r.choice((0, 0, 0, 1)), "cheat_b": r.choice((0, 0, 0, 1)), "cheat_c": r.choice((0, 0, 0, 1)),
        "time": r.randrange(0, 5), "cache_time": r.randrange(0, 5), "cache_sound": r.choice((0, 0, 1)),
        "state168": r.random() < 0.5,
        "p19": r.choice((y - 45, y - 45 + 2, y + 200, y - 300, r.randrange(0, 2000))),
    }
    values.update(kw)
    return draw(r, **values)


def with_p(s, **fields):
    s = dict(s)
    s["pset"] = {**s.get("pset", {}), **{int(k[1:], 16): v for k, v in fields.items()}}
    return s


# --------------------------------------------------------------------------
# The simple functions
# --------------------------------------------------------------------------

def counter_cases(r):
    """0x41f850: the kind in the first object picks which counters in the second one are bumped."""
    kinds = list(range(0, 0x37)) + [0x100, 0x7FFFFFFF, 0xFFFFFFFF, 0x80000000]
    for kind in kinds:
        noise = r.getrandbits(32)
        counters = [r.randrange(1, 1000) for _ in range(0x38)]

        def setup(env, kind=kind, noise=noise, counters=counters):
            a = env.object(0x40, "kind-owner", words=[noise ^ i for i in range(0x10)])
            env.put(a + 4, kind)
            b = env.object(0xE0, "counters", words=counters)
            return {"a": a, "b": b}
        yield Case(f"counters kind {kind:#x}", F_F850, setup, arguments=(lambda t: t["a"], lambda t: t["b"]))
    for value in (0x7FFFFFFF, 0xFFFFFFFF):
        def setup(env, value=value):
            a = env.object(0x40, "kind-owner", fill=0)
            env.put(a + 4, 1)
            b = env.object(0xE0, "counters", fill=0)
            env.put(b + 0x88 + 4, value)
            env.put(b + 0xB0 + 4, value)
            return {"a": a, "b": b}
        yield Case(f"counters wrap {value:#x}", F_F850, setup, arguments=(lambda t: t["a"], lambda t: t["b"]))


def sound_cache_cases(r):
    """0x41d6f0: the sound is restarted only when the clock or the sound object changed."""
    for same_time in (0, 1):
        for same_sound in (0, 1):
            for has_sound in (0, 1):
                for enabled in (0, 1):
                    for _ in range(1):
                        clock = r.randrange(1, 1 << 30)
                        noise = r.getrandbits(32)

                        def setup(env, same_time=same_time, same_sound=same_sound, has_sound=has_sound,
                                  enabled=enabled, clock=clock, noise=noise):
                            sound = sound_object(env) if has_sound else 0
                            logic = env.object(0x180, "logic", words=[noise ^ i for i in range(0x60)])
                            env.put(logic + 0x168, sound)
                            actor = env.object(0x80, "actor", words=[noise + i for i in range(0x20)])
                            env.put(actor + 0x6C, logic)
                            env.put(G_TIME, clock)
                            env.put(G_CACHE_TIME, clock if same_time else clock + 7)
                            env.put(G_CACHE_SOUND, sound if same_sound else sound ^ 0x10)
                            env.put(G_SOUND, enabled)
                            env.put(G_SOUND_HANDLE, noise)
                            return {"actor": actor}
                        yield Case(f"sound cache t{same_time} s{same_sound} h{has_sound} e{enabled}", F_D6F0, setup,
                                   arguments=(lambda t: t["actor"],))


def power_tick_cases(r):
    """0x41fc30: the power-up timer runs down and ends or acts on its power."""
    for power in (0, 0x26B7, 0x26B8, 0x26BC, 0x26BD, 0x26BB):
        for left, spend in ((0, 5), (5, 5), (6, 5)):
            for with_set in (0, 1):
                noise = r.getrandbits(32)
                rng = random.Random(noise)

                def setup(env, power=power, left=left, spend=spend, with_set=with_set, noise=noise, rng=rng):
                    actor = env.object(0x200, "actor", words=[noise ^ i for i in range(0x80)])
                    env.put(actor + 0x170, anim_set(env, random.Random(noise), 3, 6) if with_set else 0)
                    env.put(actor + 0x174, 0)
                    if with_set == 1 and power == 0x26B7:
                        env.put(actor + 0x174, anim_set(env, random.Random(noise ^ 1), 1, 2)
                                if noise & 1 else 0)
                    if power == 0x26B7 and with_set:
                        item = env.object(0x40, "probe-item", words=[noise + i for i in range(0x10)])
                        env.put(item + 0x30, env.object(0x40, "probe-target", words=[noise - i for i in range(0x10)]))
                        env.put(actor + 0x174, item)
                    if power == 0x26BD:
                        item = env.object(0x40, "probe-item", words=[noise + i for i in range(0x10)])
                        if with_set:
                            env.put(item + 0x30, env.object(0x40, "probe-target", words=[noise - i for i in range(0x10)]))
                        else:
                            env.put(item + 0x30, 0)
                        env.put(actor + 0x174, item)
                    state = env.object(0x80, "state", words=[noise ^ i for i in range(0x20)])
                    p = env.object(0x138, "p", words=[noise + i for i in range(0x4E)])
                    ball = env.object(0x40, "ball", words=[noise ^ (i * 3) for i in range(0x10)])
                    env.put(p + 0x130, ball if noise & 2 else 0)
                    env.put(G_POWER, power)
                    env.put(G_POWER_TIME, left)
                    env.put(0x534EB8, noise)
                    env.put(G_FLASH, rng.randrange(1, 90))
                    env.put(G_FLASH_FRAME, rng.choice((0x34, 0x35, 0x36, 0x37, 0x65, 0x99)))
                    env.put(G_SOUND, 0)
                    env.put(G_MUTE, 0)
                    env.put(G_UI, env.object(0x100, "ui", fill=0))
                    return {"actor": actor, "state": state, "p": p}
                yield Case(f"power tick {power:#x} {left}-{spend} set{with_set}", F_FC30, setup,
                           arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], spend))


def edge_cases(r):
    """0x41e710: a standing place must be solid at both ends and free in between."""
    for index in range(14):
        x = r.randrange(300, 1700)
        y = r.randrange(300, 1700)
        low = r.choice((-16, -20, 0, r.randrange(-60, 10)))
        high = low + r.choice((1, 6, 12, 13, 16, 24, 40, r.randrange(1, 90)))
        foot = r.choice((60, 0x3C, r.randrange(20, 80)))
        row = y + foot + 1
        flavour = index % 7
        solid = r.choice((1, 2, 3))
        rules = []
        if flavour != 0:
            rules.append((x + low, row, x + low, row, solid))
        if flavour not in (1, 6):
            rules.append((x + high, row, x + high, row, r.choice((1, 2, 3))))
        if flavour == 2:
            rules.append((x + low + 12, row, x + high - 1, row, 1))
        if flavour == 3 and high - low > 14:
            rules.append((x + low + 16, row, x + low + 16, row, 3))
        if flavour == 4:
            rules.append((x + low, row, x + high, row, 1))
        if flavour == 5:
            rules = [(x + low, row, x + low, row, 1), (x + high, row, x + high, row, 2)]
        if r.random() < 0.3:
            rules.append((0, row, 2047, row, r.choice((0, 4))))
        flags = r.choice((0, 0, 0, 0x10, 0x20, r.getrandbits(32)))
        noise = r.getrandbits(32)

        def setup(env, x=x, y=y, low=low, high=high, foot=foot, rules=rules, flags=flags, noise=noise):
            world = collision_world(env, rules)
            level = env.object(0x80, "level", words=[noise ^ i for i in range(0x20)])
            env.put(level + 0x24, world)
            actor = env.object(0x200, "actor", words=[noise + i for i in range(0x80)])
            env.put(actor + 8, flags)
            env.put(actor + 0xC, level)
            env.put(actor + 0x4C, x, y)
            env.put(actor + 0x118, low & M)
            env.put(actor + 0x120, high & M)
            env.put(actor + 0x124, foot)
            return {"actor": actor}
        yield Case(f"edge {index} flavour {flavour} [{low},{high}]", F_E710, setup, arguments=(lambda t: t["actor"],))



# --------------------------------------------------------------------------
# The functions that act on the player world
# --------------------------------------------------------------------------

def ammo_set(r):
    return {
        4: r.choice((0, 0, 1)), 0x15: r.randrange(10, 120), 0x16: r.randrange(-30, 30) & M,
        0x1B: r.randrange(0, 4), 0x1C: r.choice((0, 1, 2, 9)), 0x1D: r.choice((0, 1, 2, 9)),
        0x1E: r.choice((0, 1, 2, 9)), 0x3A: r.randrange(0, 20),
        0x40: r.choice((0, 10, 600, 1999, 2000, 2500)), 0x41: r.choice((0x32, 0x32, 20, 100, 500)),
        0x42: r.choice((2000, 2000, 500, 30)), 0x49: 0,
    }


def c4e0_cases(r):
    for index in range(6):
        s = rw(r, p_x=1, p1=r.choice((0, 1)), q_size=r.choice((0, 0, 0x10, 0x20, 0x21, 0x40)),
               q_count=r.choice((0, 1, 2)), p49=r.choice((True, False)), p4a=True)
        yield call(f"clear grab {index}", F_C4E0, s)
    for index in range(2):
        s = rw(r, p_x=0, p1=r.choice((0, 1)))
        yield call(f"clear without grab {index}", F_C4E0, s)


def d750_cases(r):
    for index in range(7):
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        actors = [candidate(r, x, y, {0x4C: x + r.randrange(-140, 140), 0x50: y + r.randrange(-130, 130)})
                  for _ in range(r.choice((0, 1, 2, 3, 4, 6)))]
        s = rw(r, x=x, y=y, p0=r.choice((0, 1)), actors=actors)
        out = r.choice((True, True, False))

        def extra(env, tok, out=out):
            tok["out"] = env.object(8, "out", words=[0xAAAAAAAA, 0xBBBBBBBB]) if out else 0
        yield call(f"nearest target {index}", F_D750, s, extra,
                   arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], lambda t: t["out"]))


def de90_cases(r):
    """0x41de90: every attack kind under four fixed settings of the power, cheats, ammunition and dice."""
    kinds = list(range(0, 0x14)) + [0x7FFFFFFF, 0xFFFFFFFF]
    # power, (cheat a, b, c), ammunition, the dice value (below and above the 25, 30 and 35 percent tests)
    combos = ((0, (0, 0, 0), 5, 10), (0x26BC, (0, 0, 1), 0, 90), (0, (1, 0, 1), 5, 90), (0x26BC, (0, 1, 0), 5, 10))
    plan = [(kind, i, *combo) for kind in kinds for i, combo in enumerate(combos)]
    for kind in (1, 7, 8):
        for i, power in enumerate((0x26B8, 0x26B9, 0x26BA, 0x26BB)):
            plan.append((kind, i, power, (0, 0, 0), 5, 10))
    for kind, i, power, cheat, ammo, dice in plan:
        s = rw(r, p0=i % 2, power=power, p_x=0 if i == 3 else 1, q_size=(0x20, 0x40, 0, 0x10)[i],
               q_count=(1, 0, 2, 1)[i])
        s["cheat_a"], s["cheat_b"], s["cheat_c"] = cheat
        s["rolls"] = [dice, dice + 1, dice + 2, dice, dice + 3, dice, dice, dice]
        s["aset"] = {0x138: r.choice((0x80000000, r.randrange(-30, 30) & M)), 0x13C: r.getrandbits(32),
                     0x140: r.getrandbits(32), 0x144: r.getrandbits(32), 0x104: r.getrandbits(32)}
        s["pset"] = {0x1C: ammo, 0x1D: ammo, 0x1E: ammo, 0x4A: r.getrandbits(32)}
        yield call(f"attack {kind:#x} #{i} power{power:#x}", F_DE90, s,
                   arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], kind))
    # the grab: the nearest target must be in front, within 64, flagged and level with the player
    index = 0
    for facing in (0, 1):
        for mode in (1, 2, 4):
            for flag, dy in ((0x401, 0), (0x1, 25)):
                if True:
                    x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                    tx = x - 37 - 3 if facing == 0 else x + 37 + 3
                    actors = [candidate(r, x, y, {0x4C: tx, 0x50: y + dy, 0xD0: 4, 0x128: M - 14, 0x130: 22,
                                                  0x124: 60, 0x164: flag})]
                    s = rw(r, x=x, y=y, p0=facing, mode=mode, actors=actors, power=0, p1=0)
                    s["aset"] = {0x128: M - 14, 0x130: 22, 0x124: 60}
                    yield call(f"grab {index} face{facing} mode{mode} flag{flag:#x} dy{dy}", F_DE90, s,
                               arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], 0xB))
                    index += 1


def decide_cases(r):
    for index in range(28):
        mode = index % 7
        pressed = {0: 2, 1: 4, 2: 0x40, 3: 0x80, 4: 0x100, 5: 0x20, 6: 0}[mode]
        if r.random() < 0.15:
            pressed |= some_bits(r, PRESSED_BITS, 0.4)
        if mode == 0 and r.random() < 0.5:
            pressed &= ~0
        held = r.choice((0, 0x4000000, 0x4000000, 0x1000000, 0x2000000, 0x5000000, 0x4000000 | 0x2000000,
                         some_bits(r, HELD_BITS)))
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        actors = [candidate(r, x, y, {0x4C: x + r.randrange(-110, 110), 0xD0: r.choice((4, 4, 0x200, 0x10)),
                                      0x164: r.choice((1, 1, 0x401, 0x400, 0))})
                  for _ in range(r.choice((0, 1, 1, 2, 3)))]
        s = rw(r, x=x, y=y, actors=actors, p1=r.choice((0, 0, 0, 0, 0, 1)), p_c=r.choice((0, 1, 2, 3)),
               state=r.choice((0x19, 4, 0x1A, 0x18, 5000)),
               mode=r.choice((1, 1, 1, 2, 3, 4)),
               power=r.choice((0, 0, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC)),
               p0=r.choice((0, 1)))
        s["input"] = [pressed, held, r.getrandbits(32)]
        s["pset"] = {0x1C: r.choice((0, 3)), 0x1D: r.choice((0, 3)), 0x1E: r.choice((0, 3)), 0x4B: 0}
        # the dice that pick among the four attacks are fixed by the loop, not by the seed
        roll = (index * 3) % 8
        s["rolls"] = [roll] * 6
        yield call(f"decide {index} mode {mode}", F_D850, s)


def decide_state_cases(r):
    """0x41d850: the attack picked for each pressed button depends on the grip count and the state value."""
    index = 0
    for pressed in (4, 0x40, 0x80, 0x100, 0x20, 2):
        for p_c in (1, 2, 3):
            for state in (0x19, 4, 0x1A, 0x18):
                if pressed != 4 and state in (0x19, 0x18):
                    continue
                x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                s = rw(r, x=x, y=y, actors=[], p1=0, p_c=p_c, state=state, mode=1, power=0, p0=r.choice((0, 1)))
                s["input"] = [pressed, 0x4000000 if index % 2 else 0, r.getrandbits(32)]
                s["pset"] = {0x1C: 0, 0x1D: 3, 0x1E: 0, 0x4B: 0}
                yield call(f"decide state {index} press{pressed:#x} c{p_c} s{state:#x}", F_D850, s)
                index += 1


def decide_power_cases(r):
    """0x41d850: the swipe button with each power-up, and with no target or only a far one."""
    index = 0
    for power in (0, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC):
        for far in (False, True):
            if power not in (0, 0x26B8) and far:
                continue
            x, y = r.randrange(300, 1700), r.randrange(300, 1700)
            actors = [candidate(r, x, y, {0x4C: x - 37 - 200, 0x50: y, 0xD0: 4, 0x128: M - 14, 0x130: 22,
                                          0x164: 0x401})] if far else []
            s = rw(r, x=x, y=y, actors=actors, p1=0, p_c=2, state=0x18, mode=1, power=power, p0=0)
            s["aset"] = {0x128: M - 14, 0x130: 22}
            s["input"] = [2, 0, r.getrandbits(32)]
            s["pset"] = {0x1C: 0, 0x1D: 3, 0x1E: 0, 0x4B: 0}
            yield call(f"decide power {index} {power:#x} far{far}", F_D850, s)
            index += 1


def close_cases(r):
    """A target just in front of the player with the low flag, so the swipe is chosen by distance.

    The gap and the dice are fixed by the loop: the distance stays under 32 and every dice value 0 to 7 is used.
    """
    for index in range(8):
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        facing = index % 2
        gap = (0, 4, 9, 14, 19, 24, 29, 30)[index]
        tx = x - 37 - gap if facing == 0 else x + 37 + gap
        actors = [candidate(r, x, y, {0x4C: tx, 0x50: y + r.randrange(-15, 15), 0xD0: (4, 0x200)[index // 2 % 2],
                                      0x128: M - 14, 0x130: 22, 0x164: (0x400, 0x401)[index // 4]})]
        s = rw(r, x=x, y=y, actors=actors, p1=0, p_c=(1, 2, 3, 0)[index % 4], state=0x18,
               mode=(1, 1, 2, 1)[index % 4], power=0, p0=facing)
        s["aset"] = {0x128: M - 14, 0x130: 22}
        s["input"] = [2, (0, 0x1000000, 0x2000000, 0)[index % 4], r.getrandbits(32)]
        s["pset"] = {0x4B: 0}
        s["rolls"] = [index] * 6
        yield call(f"close target {index}", F_D850, s)


def action_world(r, index, value, p_c, facing, pressed=0, held=0, ammo=5, player="raw", spawn=1, **pset):
    """One world for 0x41c5a0 whose animation event is `value`; every field that picks a branch is given."""
    x, y = r.randrange(300, 1700), r.randrange(300, 1700)
    timers = [near(r, 5) for _ in range(5)] + [30000 if player == "raw" else 0]
    s = rw(r, x=x, y=y, pvalue=value, pvalue2=value, player=player, timers=timers, p1=1,
           p_c=p_c, p0=facing, p7=index % 2, p8=(index // 2) % 2, p_x=(index // 3) % 2, p49=True, p4a=True,
           mode=(1, 1, 2, 4)[index % 4], actors=[candidate(r, x, y, {0x64: r.randrange(0, 0x3000)}) for _ in range(index % 3)],
           free=4, power=(0, 0x26B8, 0x26BC)[index % 3], delay=0)
    s["input"] = [pressed, held, r.getrandbits(32)]
    s["pset"] = {**ammo_set(r), 4: 0, 0x1C: ammo, 0x1D: ammo, 0x1E: ammo, **{int(k[1:], 16): v for k, v in pset.items()}}
    s["spawn"] = {name: spawn for name in SPAWN_NAMES} if spawn else {}
    return s


def action_cases(r):
    """0x41c5a0: the animation event picks what the attack does."""
    index = 0
    # event 3: the button test, for each grip count and each button, with and without ammunition
    for p_c in (1, 2, 3):
        for pressed in (0, 4, 0x40, 0x80):
            for ammo in (0, 5):
                yield call(f"action button c{p_c} press{pressed:#x} ammo{ammo}", F_C5A0,
                           action_world(r, index, 3, p_c, index % 2, pressed=pressed, ammo=ammo))
                index += 1
    # event 2: the shot that each grip count spawns, facing both ways, with and without a prototype
    for p_c, ammo, spawn, extra in ((1, 5, 1, {}), (1, 5, 1, {}), (1, 5, 0, {}), (2, 0, 1, {}), (2, 2, 1, {}), (2, 2, 0, {}),
                                    (3, 5, 1, {"p40": 10}), (3, 5, 1, {"p40": 1000}), (3, 5, 1, {"p40": 2500}),
                                    (3, 5, 1, {"p40": 10}), (3, 5, 1, {"p40": 1000}), (3, 5, 1, {"p40": 2500}),
                                    (3, 5, 0, {}), (1, 5, 1, {"p4": 1})):
        s = action_world(r, index, 2, p_c, index % 2, ammo=ammo, spawn=spawn, p41=50, p42=2000, **extra)
        yield call(f"action fire c{p_c} spawn{spawn} {sorted(extra.items())}", F_C5A0, s)
        index += 1
    # event 4: charging, released or held
    for held, p40 in ((0, 10), (0, 100), (4, 10), (0x100, 1999), (1, 10)):
        s = action_world(r, index, 4, 2, 0, held=held, p40=p40, p41=50, p42=2000)
        yield call(f"action charge held{held:#x} p40={p40}", F_C5A0, s)
        index += 1
    for value in (0, 1, 5, 6):
        yield call(f"action event {value}", F_C5A0, action_world(r, index, value, 1 + index % 3, index % 2))
        index += 1
    # the player animation has not reached a step: the reset path
    for p_x in (0, 1):
        for p1 in (0, 1):
            s = action_world(r, index, 1, 2, p1, player="raw")
            s["timers"][5] = 0
            s["p_x"], s["p1"] = p_x, p1
            yield call(f"action reset p_x{p_x} p1{p1}", F_C5A0, s)
            index += 1


def motion_cases(r):
    """0x41b630: the player moves under its own motion state."""
    for index in range(40):
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        held = some_bits(r, (1, 0x1000000, 0x2000000, 0x4000000), 0.4)
        timers = [near(r, 5) for _ in range(6)]
        s = rw(r, x=x, y=y, mode=(1, 2, 4, 5, 6, 7, 3, 4)[index % 8], p1=r.choice((0, 0, 1)),
               p_f=r.choice((0, 8, 9, 10, 0x12, 3)), p0=r.choice((0, 1)),
               p_c=r.choice((1, 2, 3)), timers=timers, power=r.choice((0, 0, 0, 0x26BC, 0x26B8)),
               nophysics=r.choice((0, 0, 0, 1)), pvalue=r.choice((0, 1, 2, 3, 4, 5)),
               pvalue2=r.choice((0, 1, 2, 3, 4, 5)), p_x=r.choice((0, 1)))
        if index % 8 == 4:
            # climbing: no ground, a ladder, or a ladder over a floor
            s["rules"] = ([], [(x - 30, y - 150, x + 30, y + 150, 3)],
                          [(x - 30, y - 150, x + 30, y + 150, 3), (0, y + 61, 2047, 2047, 1)])[(index // 8) % 3]
            held = 0x1000000 if (index // 8) % 2 else 0
            s["nophysics"] = 0
        s["input"] = [some_bits(r, PRESSED_BITS), held, r.getrandbits(32)]
        s["pset"] = {**ammo_set(r), 0x46: r.choice((0, 1, 3, 4, 5, 20, 100000)), 0x45: r.choice((0, 0, 1, 700)),
                     0x19: r.choice((y - 45, y + 10, y + 400, y - 400, r.randrange(0, 2000))),
                     0x15: r.randrange(10, 120), 0x21: r.randrange(-200, 200) & M, 0x43: r.randrange(0, 100),
                     0x17: r.randrange(0, 100), 0xF: r.choice((0, 8, 9, 10, 0x12, 3)),
                     0xB: r.getrandbits(8), 0x1A: r.getrandbits(8)}
        s["pset"][0x4A] = 0
        if index % 8 == 4:
            s["pset"][0x19] = y - 45
        s["doubles"] = {MOTION + 0x30: r.choice((r.uniform(-40, 40), 0.0, r.uniform(1, 1000))),
                        MOTION + 0x48: r.choice((r.uniform(-700, 700), 0.0)),
                        MOTION + 0x40: r.uniform(-2000, 2000), MOTION + 0x48 + 0x18: r.uniform(-100, 100)}
        if index % 8 == 4:
            s["doubles"] = {MOTION + 0x30: 0.0, MOTION + 0x48: 0.0, MOTION + 0x40: 0.0, MOTION + 0x48 + 0x18: 0.0}
            s["pset"][0x46] = 0
        yield call(f"motion {index}", F_B630, s)


def hit_cases(r):
    """0x41ce80: the player touches another actor."""
    kinds = (0x10, 0x1000000, 4, 0x40, 0x100, 0x40000, 0x10000, 0x200000, 0x100000, 0x800000, 0x20, 7, 0)
    for index in range(39):
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        other = other_spec(r, x, y, kind=kinds[index % 13])
        variant = index // 13
        # small, clamping and large amounts; kind 0x40 uses its own marker value
        other[0x164] = (0, 0x20, 0x10)[variant]
        other[0xFC] = (5, 60, 150)[variant] if index % 13 != 3 else (0x26BF, 0x26BF, 0x26BF - 0xBF)[variant]
        state = r.choice((0x18, 0x18, 0x1F, 0x19, 4, 5000))
        s = rw(r, x=x, y=y, other=other, state=state, mode=r.choice((1, 2, 3, 4, 5, 6, 7, 8)),
               p_x=r.choice((0, 1, 1)), p1=r.choice((0, 1)), engine=r.choice((1, 4)),
               link_other=(r.random() < 0.15), p49=True, p4a=True,
               actors=[candidate(r, x, y) for _ in range(r.choice((0, 0, 1)))])
        ammo = (5, 98, 98)[variant]
        s["aset"] = {0x10C: (20, 50, 99)[variant], 0xF8: r.getrandbits(32), 0x64: (0x2134, 0x2134, 7000)[variant]}
        s["pset"] = {0x1C: ammo, 0x1D: ammo, 0x1E: ammo, 0xF: (0, 0, 8)[variant], 0x49: 0}
        s["sset"] = {0x1C: state}
        if index % 39 == 7:
            s["aset"][0x74] = 0
        yield call(f"hit {index} kind {other[0xD0]:#x}", F_CE80, s, arguments=(lambda t: t["actor"],))


def roll_cases(r):
    """0x41ce80: every pairing of the two random sound picks on a hit by a kind 4 or kind 0x1000000 actor."""
    for kind in (4, 0x1000000):
        for first in range(4):
            for second in range(4):
                x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                other = other_spec(r, x, y, kind=kind)
                other[0x164] = 0x20 if (kind == 0x1000000 and first == 1) else 0
                other[0x104] = 0 if second % 2 else 3
                s = rw(r, x=x, y=y, other=other, state=0x18, mode=1, p_x=0, p1=0, engine=1, sounds=list(SOUND_NAMES),
                       sound_off=0, sound_on=r.choice((0, 1)), link_other=False, p49=True, p4a=True)
                s["rolls"] = [r.getrandbits(13) << 2 | first, r.getrandbits(13) << 2 | second, 7, 9, 11, 13]
                s["aset"] = {0x10C: 50, 0x64: 0x2134}
                s["pset"] = {0x1C: 5, 0x1D: 5, 0x1E: 5, 0xF: 0, 0x49: 0}
                s["sset"] = {0x1C: 0x18}
                yield call(f"hit kind {kind:#x} rolls {first}{second}", F_CE80, s, arguments=(lambda t: t["actor"],))


def heal_cases(r):
    """0x41ce80: the health pick-up (0x10000) in each of its branches, and the marker pick-up (0x40)."""
    for amount, health, extra in ((5, 20, 0), (5, 100, 0), (60, 50, 0), (150, 50, 7), (150, 50, 0), (150, 50, 0xFFFFFFF0)):
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        other = other_spec(r, x, y, kind=0x10000)
        other[0xFC], other[0x108], other[0x164] = amount, extra, 0
        s = rw(r, x=x, y=y, other=other, state=0x18, mode=1, p_x=0, p1=0, engine=1, link_other=False, p49=True, p4a=True)
        s["aset"] = {0x10C: health, 0x64: 0x2134}
        s["pset"] = {0x1C: 5, 0x1D: 5, 0x1E: 5, 0xF: 0, 0x49: 0}
        s["sset"] = {0x1C: 0x18}
        yield call(f"hit heal {amount} {health} {extra:#x}", F_CE80, s, arguments=(lambda t: t["actor"],))
    for sound_on in (0, 1):
        for mode in (1, 2):
            x, y = r.randrange(300, 1700), r.randrange(300, 1700)
            other = other_spec(r, x, y, kind=0x40)
            other[0xFC] = 0x26BF
            s = rw(r, x=x, y=y, other=other, state=0x18, mode=mode, p_x=0, p1=0, engine=1, sounds=list(SOUND_NAMES),
                   sound_off=0, sound_on=sound_on, link_other=False, p49=True, p4a=True)
            s["aset"] = {0x10C: 50, 0x64: 0x2134}
            s["pset"] = {0x1C: 5, 0x1D: 5, 0x1E: 5, 0xF: 0, 0x49: 0}
            s["sset"] = {0x1C: 0x18}
            yield call(f"hit marker on{sound_on} mode{mode}", F_CE80, s, arguments=(lambda t: t["actor"],))


def tail_cases(r):
    """0x41ce80: what a damaging hit does afterwards, for each actor mode and four settings of the other fields."""
    variants = ((0, 0, 0, 0, 0, 0), (1, 1, 1, 1, 1, 1), (0, 1, 0, 1, 0, 1), (1, 0, 1, 0, 1, 0))
    index = 0
    for mode in (1, 2, 3, 4, 5, 6, 8):
        for bits in variants:
            low_health, hurt_state, linked, active, centered, left = bits
            x, y = r.randrange(300, 1700), r.randrange(300, 1700)
            other = other_spec(r, x, y, kind=4)
            other[0x164] = 0
            other[0x104] = 0 if bits[0] ^ bits[2] else 3
            other[0x4C] = x + (-20 if left else 20)
            other[0x138] = 0x80000000 if centered else 5
            other[0x13C] = M - 9
            other[0x144] = 30
            s = rw(r, x=x, y=y, other=other, state=0x1F if hurt_state else 0x18, mode=mode, p_x=linked, p1=active,
                   engine=1, sounds=list(SOUND_NAMES), sound_off=0, sound_on=0, link_other=False, p49=True, p4a=True)
            s["rolls"] = [r.getrandbits(13) << 2, r.getrandbits(13) << 2 | 1, 7 if left else 77, 9, 11, 13, 15, 17]
            s["aset"] = {0x10C: 1 if low_health else 50, 0x64: 0x2134, 8: 0x10 * (index % 2)}
            s["pset"] = {0x1C: 5, 0x1D: 5, 0x1E: 5, 0xF: 0, 0x49: 0}
            s["sset"] = {0x1C: 0x1F if hurt_state else 0x18}
            yield call(f"hit tail mode{mode} {''.join(map(str, bits))}", F_CE80, s, arguments=(lambda t: t["actor"],))
            index += 1


# --------------------------------------------------------------------------
# Deterministic cases added after the gate rejection. Nothing here depends on the seed for reaching
# its target: every key value is fixed by the loops, the random source only fills incidental words.
# --------------------------------------------------------------------------

def item_flag_cases(r):
    yield from thin(item_flag_all(r), 5)


def item_flag_all(r):
    """0x41d850: a near target with the item flag, then the nearest-target flag test and 0x41e660."""
    index = 0
    helds = (0x4000000, 0x4000000 | 1, 0x4000000 | 0x100 | 4, 0x4000000 | 0x8000 | 0x80, 0x4000000 | 0x10000000)
    for bit0 in (1, 0):
        for adj in (0x400, 0):
            for facing in (0, 1):
                for dy in (0, 20, -20, 21, -21):
                    for gap in (0, 62, 63):
                        yield item_case(r, index, bit0, adj, facing, dy, gap, 1 + index % 2, helds[index % len(helds)])
                        index += 1
    # the reload of the distance bound: just inside and just outside 0x96, and other modes
    for gap, mode in ((148, 1), (149, 1), (150, 2), (151, 2), (10, 3), (10, 0), (10, 4), (10, 5)):
        yield item_case(r, index, 1, 0x400, index % 2, 0, gap, mode, 0x4000000 | 0x20)
        index += 1
    # other held-bit combinations with the flag set
    for held in (0, 0x1000000, 0x2000000, 0x3000000 | 0x4000000, 0x4000000 | 0x2000000, 0x4000000 | 0x1000000, 0x8000000,
                 0x4000000):
        yield item_case(r, index, 1, 0x400 if index % 2 else 0, index % 2, 0, 5, 1, held)
        index += 1
    # the second item-flag path: only the 0x20 bit pressed and mode 1
    for bit0 in (1, 0):
        for adj in (0x400, 0):
            for facing in (0, 1):
                for dy in (0, 21):
                    for gap in (0, 62, 63):
                        yield item_case(r, index, bit0, adj, facing, dy, gap, 1, index % 3 * 0x100000, pressed=0x20)
                        index += 1
    for mode in (2, 3, 0):
        yield item_case(r, index, 1, 0x400, 0, 0, 5, mode, 0, pressed=0x20)
        index += 1


def item_case(r, index, bit0, adj, facing, dy, gap, mode, held, pressed=2):
    x, y = r.randrange(300, 1700), r.randrange(300, 1700)
    adj_d = 0 if adj else 0x30
    tx = x - 37 - gap + adj_d if facing == 0 else x + 37 + gap - adj_d
    flags = ((r.getrandbits(32) | 0x00018002) & ~0x401) | adj | bit0
    extra = candidate(r, x + 300, y + 40, {0xD0: 0x10})
    actors = [candidate(r, x, y, {0x4C: tx, 0x50: y + dy, 0xD0: r.choice((4, 0x200)), 0x124: 60,
                                  0x128: M - 14, 0x130: 22, 0x164: flags}), extra]
    s = rw(r, x=x, y=y, actors=actors, p1=0, p_c=r.choice((1, 2, 3)), state=0x18, mode=mode, power=0, p0=facing)
    s["aset"] = {0x128: M - 14, 0x130: 22, 0x124: 60}
    s["input"] = [pressed, held, r.getrandbits(32)]
    s["pset"] = {0x4B: 0, 0x1C: r.choice((0, 3)), 0x1D: r.choice((0, 3)), 0x1E: r.choice((0, 3))}
    return call(f"item flag {index} press{pressed:#x} bit{bit0} adj{adj:#x} face{facing} dy{dy} gap{gap} mode{mode}", F_D850, s)


def edge_tie_cases(r):
    yield from thin(edge_tie_all(r), 3)


def edge_tie_all(r):
    """0x41d750: the candidate's edge equal to, just below and just above the actor's x, including negative x."""
    index = 0
    for here in (900, -700, 0, -1, 0x7FFFFE00, -0x7FFFFE00):
        for facing in (0, 1):
            for flag400 in (0x400, 0):
                for delta in (-2, -1, 0, 1, 2):
                    a128, a130, c128, c130 = (M - 13, 22, M - 15, 21) if index % 2 else (M - 5, 9, M - 20, 30)
                    adj = 0 if flag400 else 0x30
                    if facing:
                        tx = here + delta - (c128 - (1 << 32)) - adj
                    else:
                        tx = here - delta - c130 + adj
                    yield tie_case(r, index, here, facing, flag400, delta, tx, a128, a130, c128, c130, 0)
                    index += 1
    # vertical bound of 100 and the tie between two equally near candidates
    for dy in (0, 99, -99, 100, -100, 101, -101):
        yield tie_case(r, index, 800, index % 2, 0x400, 3, 800 + 3 + 14 if index % 2 else 800 - 3 - 22, M - 14, 22, M - 14, 22, dy)
        index += 1
    for facing in (0, 1):
        for second_first in (0, 1):
            x, y = 1000, 1000
            tx = x + 40 + 14 if facing else x - 40 - 22
            specs = []
            for order in range(2):
                specs.append(candidate(r, x, y, {0x4C: tx, 0x50: y + 3 * order, 0xD0: 4, 0x128: M - 14, 0x130: 22,
                                                 0x164: 0x400 | order}))
            if second_first:
                specs.reverse()
            s = rw(r, x=x, y=y, p0=facing, actors=specs)
            s["aset"] = {0x128: M - 14, 0x130: 22}
            out = lambda env, tok: tok.__setitem__("out", env.object(8, "out", words=[0xAAAAAAAA, 0xBBBBBBBB]))
            yield call(f"nearest tie {index}", F_D750, s, out, arguments=(
                lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], lambda t: t["out"]))
            index += 1


def tie_case(r, index, here, facing, flag400, delta, tx, a128, a130, c128, c130, dy):
    y = r.randrange(300, 1700)
    actors = [candidate(r, 1000, y, {0x4C: tx & M, 0x50: y + dy, 0xD0: r.choice((4, 0x200)), 0x128: c128,
                                     0x130: c130, 0x164: flag400 | r.choice((0, 1, 0x20))})]
    s = rw(r, x=here & M, y=y, p0=facing, actors=actors)
    s["aset"] = {0x128: a128, 0x130: a130}

    def extra(env, tok):
        tok["out"] = env.object(8, "out", words=[0xAAAAAAAA, 0xBBBBBBBB])
    return call(f"edge tie {index} x{here} face{facing} d{delta} dy{dy}", F_D750, s, extra,
                arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], lambda t: t["out"]))


def span_tie_cases(r):
    yield from thin(span_tie_all(r), 3)


def span_tie_all(r):
    """0x41e710: the span end equal to, just below and just above low + 12 + 4k, with negative positions."""
    index = 0
    for low in (-100, -20, -13, -12, 0, 5):
        for k in range(4):
            for d in (-1, 0, 1):
                high = low + 12 + 4 * k + d
                x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                foot = 60
                row = y + foot + 1
                rules = [(x + low, row, x + low, row, 1 + index % 3), (x + high, row, x + high, row, 1 + (index // 3) % 3)]
                noise = r.getrandbits(32)

                def setup(env, x=x, y=y, low=low, high=high, foot=foot, rules=rules, noise=noise):
                    world = collision_world(env, rules)
                    level = env.object(0x80, "level", words=[noise ^ i for i in range(0x20)])
                    env.put(level + 0x24, world)
                    actor = env.object(0x200, "actor", words=[noise + i for i in range(0x80)])
                    env.put(actor + 8, 0)
                    env.put(actor + 0xC, level)
                    env.put(actor + 0x4C, x, y)
                    env.put(actor + 0x118, low & M)
                    env.put(actor + 0x120, high & M)
                    env.put(actor + 0x124, foot)
                    return {"actor": actor}
                yield Case(f"span tie {index} [{low},{high}]", F_E710, setup, arguments=(lambda t: t["actor"],))
                index += 1


def action_tie_cases(r):
    yield from thin(action_tie_all(r), 5)


def action_tie_all(r):
    """0x41c5a0: animation value 2 (p_c 3) with the two compared counters equal, one above and one below."""
    index = 0
    for event_value in (2,):
        for p_c in (1, 2, 3):
            for p4 in (0, 1):
                for tie in (0, 1, -1):
                    for low in (None, 0, -1, -7, 5000):
                        player = "raw"
                        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                        s = rw(r, x=x, y=y, pvalue=event_value, pvalue2=event_value, player=player, p1=1,
                               p_c=p_c, p0=r.choice((0, 1)), p7=r.choice((0, 1)), p8=r.choice((0, 1)), p_x=1,
                               p49=True, p4a=True, mode=1, actors=[], power=0, delay=0, free=4,
                               timers=[near(r, 5) for _ in range(5)] + [30000])
                        s["input"] = [some_bits(r, (4, 0x40, 0x80), 0.4), some_bits(r, (4, 0x100, 1), 0.5), r.getrandbits(32)]
                        s["pset"] = ammo_set(r)
                        s["pset"][0x42] = s["pset"][0x41] + tie
                        s["pset"][4] = p4
                        if low is not None:
                            s["pset"][0x40] = s["pset"][0x41] + low
                        s["spawn"] = {name: 1 for name in SPAWN_NAMES}
                        yield call(f"action tie {index} c{p_c} p4{p4} tie{tie} low{low}", F_C5A0, s)
                        index += 1


def jump_cases(r):
    """0x41b630: jump button held while the countdown runs: each way the launch speed is chosen."""
    plan = [(1, 0, 0, 5), (1, 0, 0, 20), (1, 0, 0, 100000), (0, 0x26BC, 1, 100000), (0, 0, 0, 100000),
            (0, 0, 1, 100000), (0, 0, 1, 20), (0, 0, 1, 5)]
    for index, (flag220, power, timer45, timer46) in enumerate(plan):
        x, y = r.randrange(300, 1700), r.randrange(300, 1700)
        s = rw(r, x=x, y=y, mode=1, p1=0, p_f=0, p0=r.choice((0, 1)), nophysics=0, power=power, step=20,
               pvalue=1, pvalue2=1)
        s["globals_extra"] = {0x537220: flag220, 0x53C9C0: 0}
        s["input"] = [some_bits(r, PRESSED_BITS), 1 | (0x1000000 if index % 2 else 0), r.getrandbits(32)]
        s["pset"] = {**ammo_set(r), 0x46: timer46, 0x45: timer45, 0x19: y - 45 if index < 4 else y + 400, 0x4A: 0}
        yield call(f"jump {index} f{flag220} power{power:#x} t45={timer45} t46={timer46}", F_B630, s)


def float_cases(r):
    yield from thin(float_all(r), 4)


def float_all(r):
    """0x41b630: the double to integer conversions at, just inside and just beyond plus and minus 2**63."""
    b = 2.0 ** 63
    values = [b, -b, math.nextafter(b, 0.0), math.nextafter(b, math.inf), math.nextafter(-b, 0.0),
              math.nextafter(-b, -math.inf), 2 * b, -2 * b, 2.0 ** 62, -(2.0 ** 62), b - 2048.0, -b + 2048.0,
              b - 0.5 * 2048.0, 4611686018427387904.5, 0.5, -0.5, 4294967296.0, -4294967296.0, 2147483648.0,
              -2147483649.0]
    accs = (0.0, 512.0, -512.0, 1024.0, -1024.0, 2048.0, -2048.0, 0.25)
    index = 0
    for a, value in enumerate(values):
        for step, acc in enumerate(accs):
            if (a + step) % 3 and step not in (0, 4):
                continue
            other = values[(a * 7 + step * 3 + 1) % len(values)]
            other_acc = accs[(step * 3 + a) % len(accs)]
            x, y = r.randrange(300, 1700), r.randrange(300, 1700)
            held = some_bits(r, (1, 0x1000000, 0x2000000, 0x4000000), 0.4)
            s = rw(r, x=x, y=y, mode=r.choice((1, 2, 4, 5)), p1=0, p_f=0, p0=r.choice((0, 1)), nophysics=0,
                   power=r.choice((0, 0x26BC)), pvalue=r.choice((0, 1, 2, 3)), pvalue2=r.choice((0, 1, 2, 3)))
            s["input"] = [some_bits(r, PRESSED_BITS), held, r.getrandbits(32)]
            s["pset"] = {**ammo_set(r), 0x46: r.choice((0, 5)), 0x45: r.choice((0, 700)), 0x19: y - 45,
                         0x4A: 0}
            s["doubles"] = {0x534E40: value, 0x534E60: acc, 0x534E48: other, 0x534E68: other_acc,
                            MOTION + 0x30: r.uniform(-40, 40), MOTION + 0x40: r.uniform(-2000, 2000)}
            yield call(f"float bound {index} {value!r}/{acc!r}", F_B630, s)
            index += 1


def mute_cases(r):
    yield from thin(mute_all(r), 5)


def mute_all(r):
    """0x41ce80, 0x41c5a0: the mute slot at +0x30 of the sound owner is zero or non-zero among distinct neighbours."""
    offs = (0, 1, 2, 0x100, 0x01000000, 0xFFFFFFFF, 0x80000000)
    index = 0
    for off in offs:
        for sound_on in (0, 1):
            for first, second in ((0, 0), (1, 2), (2, 1), (3, 3)):
                x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                other = other_spec(r, x, y, kind=4)
                other[0x164] = 0
                s = rw(r, x=x, y=y, other=other, state=0x18, mode=1, p_x=0, p1=0, engine=1, sounds=list(SOUND_NAMES),
                       sound_off=off, sound_on=sound_on, link_other=False, p49=True, p4a=True, snoise=True)
                s["rolls"] = [r.getrandbits(13) << 2 | first, r.getrandbits(13) << 2 | second, 7, 9, 11, 13]
                s["aset"] = {0x10C: 50, 0x64: 0x2134}
                s["pset"] = {0x1C: 5, 0x1D: 5, 0x1E: 5, 0xF: 0, 0x49: 0}
                s["sset"] = {0x1C: 0x18}
                yield call(f"mute hit {index} off{off:#x} on{sound_on} rolls{first}{second}", F_CE80, s,
                           arguments=(lambda t: t["actor"],))
                index += 1
    for off in offs:
        for sound_on in (0, 1):
            for mode in (1, 2):
                x, y = r.randrange(300, 1700), r.randrange(300, 1700)
                other = other_spec(r, x, y, kind=0x40)
                other[0xFC] = 0x26BF
                s = rw(r, x=x, y=y, other=other, state=0x18, mode=mode, p_x=0, p1=0, engine=1, sounds=list(SOUND_NAMES),
                       sound_off=off, sound_on=sound_on, link_other=False, p49=True, p4a=True, snoise=True)
                s["aset"] = {0x10C: 50, 0x64: 0x2134}
                s["pset"] = {0x1C: 5, 0x1D: 5, 0x1E: 5, 0xF: 0, 0x49: 0}
                s["sset"] = {0x1C: 0x18}
                yield call(f"mute hit 0x40 {index} off{off:#x} on{sound_on} mode{mode}", F_CE80, s,
                           arguments=(lambda t: t["actor"],))
                index += 1
    for off in offs:
        for event in range(8):
            pvalue = (0, 1, 2, 3, 4, 5, 6, 3)[event]
            x, y = r.randrange(300, 1700), r.randrange(300, 1700)
            s = rw(r, x=x, y=y, pvalue=pvalue, pvalue2=r.choice((1, 2, 3, 4, 5)), player="raw", p1=1,
                   p_c=r.choice((1, 2, 3)), p0=r.choice((0, 1)), p_x=1, p49=True, p4a=True, mode=1,
                   actors=[], sounds=list(SOUND_NAMES), sound_off=off, snoise=True, power=0)
            s["input"] = [some_bits(r, (4, 0x40, 0x80), 0.4), some_bits(r, (4, 0x100, 1), 0.5), r.getrandbits(32)]
            s["pset"] = ammo_set(r)
            yield call(f"mute action {index} off{off:#x} event{pvalue}", F_C5A0, s)
            index += 1


def cases(random_source):
    r = random_source
    yield from counter_cases(r)
    yield from sound_cache_cases(r)
    yield from power_tick_cases(r)
    yield from edge_cases(r)
    yield from c4e0_cases(r)
    yield from d750_cases(r)
    yield from de90_cases(r)
    yield from decide_cases(r)
    yield from decide_state_cases(r)
    yield from decide_power_cases(r)
    yield from close_cases(r)
    yield from action_cases(r)
    yield from motion_cases(r)
    yield from jump_cases(r)
    yield from hit_cases(r)
    yield from roll_cases(r)
    yield from tail_cases(r)
    yield from heal_cases(r)
    yield from item_flag_cases(r)
    yield from edge_tie_cases(r)
    yield from span_tie_cases(r)
    yield from action_tie_cases(r)
    yield from float_cases(r)
    yield from mute_cases(r)
