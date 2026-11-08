"""Cases for level_one_player_actions_02: Observed Level 1 player actions batch 2.

Every random value is drawn when the case list is generated, never inside a
setup function, so each setup rebuilds the identical memory image.
"""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

M = 0xFFFFFFFF

F_SET_RECT = 0x40FE90
F_LOOKUP = 0x40F780
F_PLAYER = 0x415DF0
F_STAND = 0x4171D0
F_RESET = 0x417380
F_JUMP = 0x417590
F_FALL = 0x417930
F_FLIP = 0x418120
F_RIGHT = 0x4183E0
F_FORWARD = 0x418B40
F_IDLE = 0x419030

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

NAMES = ("CLAW_STAND", "CLAW_JUMP", "CLAW_FALL", "CLAW_WALK", "CLAW_LAND", "CLAW_CLIMB", "CLAW_DUCK",
         "CLAW_IDLE", "CLAW_LIFTWALK", "CLAW_LIFT2", "CLAW_LOOKUP", "CLAW_TEETER", "CLAW_THROW")


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


def tile_effect(rules, pokes=(), holder=None):
    """The class of a position. A poke changes a field of the world on the n-th query, behind the caller's back."""
    def effect(env, call):
        x, y = call.arguments[0], call.arguments[1]
        if pokes:
            number = env.calls_so_far(call.function)
            for when, key, offset, value in pokes:
                if number == when:
                    env.put(holder[key] + offset, value(holder) if callable(value) else value)
        for x0, y0, x1, y1, cls in rules:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return cls
        return 0
    return effect


def collision_world(env, rules, empty=False, margin=(300, 300), start=(100, 100), pokes=(), holder=None):
    """One giant tile; the tile's class function is a pure function of the position."""
    tile_map = env.object(0x100, "tile-map", fill=0)
    cells = env.object(8, "tile-cells", fill=0)
    rows = env.object(8, "tile-rows", fill=0)
    tiles = env.object(8, "tile-table", fill=0)
    tile = env.object(8, "tile", fill=0)
    vtable = env.object(0x40, "tile-vtable", fill=0)
    env.put(tile, vtable)
    env.put(vtable + 0x20, env.stub(TILE, "thiscall", 2, tile_effect(rules, pokes, holder)))
    env.put(tiles, tile)
    env.put(cells, 0xEEEEEEEE if empty else 0)
    env.put(rows, 0)
    env.put(tile_map + 0x20, cells)
    env.put(tile_map + 0x24, rows)
    env.put(tile_map + 0x30, 2048, 2048)
    env.put(tile_map + 0x8C, 12, 12)
    env.put(tile_map + 0x84, start[0], start[1])
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
        "pokes": (),
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
            mask = s["probe_items"]
            if mask is True:
                mask = -1
            if mask and (mask >> (index - 0x17F)) & 1:
                env.put(array + 4 * index, env.object(0x40, "probe-item", words=[word() for _ in range(0x10)]))
            else:
                env.put(array + 4 * index, 0)
        result = env.object(0x80, "probe", words=[word() for _ in range(0x20)])
        env.put(result + 0x14, array)
        env.put(result + 0x64, low, high)
        return result

    peek = {}
    # the level: collision world, sound map, animation map
    world = collision_world(env, s["rules"], s["empty_tiles"], s["margin"], (s["x"] // 2 + 100, s["y"] // 2 + 100),
                             s["pokes"], peek)
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
        env.put(queue + 0x0C, env.object(0x80, "queue-owner", words=[word() for _ in range(0x20)]))
        env.put(queue + 0x140, noise.randrange(-30, 30) & M, noise.randrange(-30, 30) & M)
        vtable = env.object(0x100, "linked-vtable", fill=0)
        for slot in (0x80, 0x84, 0x88, 0xA0, 0xB0):
            env.put(vtable + slot, env.stub(f"Q::{slot:#x}", "thiscall", 1 if slot == 0x80 else 0, lambda env, call: 0))
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
    env.put(state + 0x14, 0 if s.get("fresh_p") else p)
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
    velocity = (noise.randrange(-300, 300) & M, noise.randrange(-300, 300) & M)
    if s.get("velocity") is not None:
        velocity = s["velocity"]
    env.put(actor + 0x148, *velocity)
    env.put(actor + 0x18C, actor)
    if s.get("probe"):
        probe = make_probe(s["probe"])
        env.put(actor + 0x170, probe)
        env.put(actor + 0x16C, noise.randrange(0, 0x200))
        tok["probe"] = probe
    mover = env.object(0x180, "mover", words=[word() for _ in range(0x60)])
    env.put(mover + 0xD0, 0x80)
    env.put(mover + 0x158, s["mover"][0] & M, s["mover"][1] & M)
    tok["mover"] = mover
    if s["platform"]:
        env.put(actor + 0x80, mover)
        env.put(actor + 8, s["flags"] | 0x10)
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
    peek.update(actor=actor, p=p, state=state, mover=tok.get("mover", 0), input=inp)
    tok.update(actor=actor, state=state, p=p, level=level, input=inp, world=world, linked=linked, queue=queue,
               animation_owner=animation_owner, sound_owner=sound_owner, anims=anims)
    return tok


def call(label, function, s, extra=None, arguments=None):
    def setup(env):
        tok = build(env, s)
        if extra:
            extra(env, tok)
        return tok

    if arguments is None:
        arguments = (lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"])
    return Case(label, function, setup, arguments=arguments)


# --------------------------------------------------------------------------
# The cases
# --------------------------------------------------------------------------

def lookup_cases(r):
    for count in (2, 9):
        for buckets in (1, 7):
            names = [f"KEY_{r.getrandbits(16):04X}" for _ in range(count)]
            values = [r.getrandbits(32) | 1 for _ in range(count)]
            picks = [names[0], names[-1], names[count // 2], "MISSING_KEY", "", names[0][:-1]]
            for pick in (picks if count == 9 else picks[:1] + picks[3:5]):
                def setup(env, names=names, values=values, buckets=buckets, pick=pick, noise=r.getrandbits(32)):
                    owner = string_map(env, list(zip(names, values)), buckets)
                    key = env.object(len(pick) + 4, "key", data=pick.encode() + b"\0")
                    c = env.object(0x40, "c", words=[noise, noise ^ 1, noise ^ 2, noise ^ 3])
                    env.put(c + 0x28, owner)
                    b = env.object(0x20, "b", words=[noise ^ 5, noise ^ 6, noise ^ 7, c])
                    a = env.object(0x20, "a", words=[noise ^ 8, b])
                    return {"this": a, "key": key}
                yield Case(f"lookup {pick!r} among {count} in {buckets} buckets", F_LOOKUP, setup,
                           receiver=lambda t: t["this"], arguments=(lambda t: t["key"],))


def rect_cases(r):
    for _ in range(2):
        values = tuple(r.getrandbits(32) for _ in range(4))

        def setup(env, noise=r.getrandbits(32)):
            return {"obj": env.object(0x200, "rect-owner", words=[noise ^ i for i in range(0x80)])}
        yield Case("store four words", F_SET_RECT, setup, receiver=lambda t: t["obj"], arguments=values)


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


STILL = {MOTION + 0x18: 0.0, MOTION + 0x30: 0.0, MOTION + 0x48: 0.0, MOTION + 0x60: -1e9, MOTION + 0x78: 1e9,
         MOTION + 0xC8: 1e9, MOTION + 0xE0: 1e9, MOTION + 0x90: 0.0, MOTION + 0xB0: 0.0}


def grounded(r, **override):
    """The actor stands on a floor and nothing is pressed (or one arrow is)."""
    base = draw(r)
    x, y = base["x"], base["y"]
    allowed = (0, 1, 6, 0x63, 0x333)
    still = STILL
    values = {"doubles": still, "x": x, "y": y, "rules": [(0, y + 61, 2047, 2047, 1)], "mode": 1, "p_f": 0, "p1": 0, "nophysics": 0,
              "platform": False, "power": 0, "player": "raw", "present": NAMES,
              "pvalue": r.choice(allowed), "pvalue2": r.choice(allowed), "input": input_bits(r, r.choice((0, 0, 1, 2, 4, 8)))}
    values.update(override)
    return draw(r, **values)


def reset_cases(r):
    for index in range(8):
        s = draw(r, state=r.choice((5000, 5000, 0x18, 0x19, 0x138E, 1)), p0=r.choice((0, 1)), present=r.choice((NAMES, ())))
        yield call(f"reset {index}", F_RESET, s)


def fall_cases(r):
    for index in range(10):
        s = sweep_world(r, p_f=(0, 8, 9, 10, 0x12, 3, 0x11, 7)[index % 8], p1=(index // 8) % 2, p_x=index % 2,
                        q_count=(index // 2) % 3)
        s["input"] = [0, 0, r.getrandbits(32)]
        flag = (0, 1, 5)[index % 3]
        yield call(f"fall {index} flag {flag}", F_FALL, s,
                   arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], flag))


def flip_cases(r):
    for index in range(6):
        s = draw(r, p0=index % 2)
        spans = [r.choice((0x80000000, 0x80000000, r.getrandbits(32))) for _ in range(3)]
        coords = [(r.getrandbits(32), r.getrandbits(32)) for _ in range(3)]
        flags = r.getrandbits(32)

        def extra(env, tok, spans=spans, coords=coords, flags=flags):
            a = tok["actor"]
            env.put(a + 0x40, flags)
            for offset, first, (lo, hi) in zip((0x118, 0x128, 0x138), spans, coords):
                env.put(a + offset, first, lo, hi, first ^ 0x55)
                env.put(a + offset, first)
        yield call(f"flip {index}", F_FLIP, s, extra)


def jump_edge_cases(r):
    for offset in (0x50, 0x10, 0x20):
        for value in (-0.0, -1e-300, 0.0, 1e-300):
            s = sweep_world(r, state=0x18, p1=0, power=0)
            s["input"] = [0, 0, r.getrandbits(32)]
            s["doubles"] = {MOTION + 0x50: 5.0, MOTION + 0x10: 5.0, MOTION + 0x20: 5.0, MOTION + offset: value}
            yield call(f"jump edge {offset:#x} {value!r}", F_JUMP, s)


def jump_cases(r):
    for index in range(15):
        s = sweep_world(r, state=(0x18, 4, 0x138B)[(index // 5) % 3], p1=index % 2, power=(0, 0x26bc, 0x26b8)[(index // 2) % 3])
        s["input"] = [0, 0, r.getrandbits(32)]
        mode = index % 5
        doubles = {}
        if mode == 1:
            doubles = {MOTION + 0x50: float("nan")}
        elif mode == 2:
            doubles = {MOTION + 0x10: float("nan")}
        elif mode == 3:
            doubles = {MOTION + 0x50: float("inf"), MOTION + 0x10: -3.0}
        elif mode == 4:
            doubles = {MOTION + 0x50: r.uniform(-900, 900), MOTION + 0x10: r.uniform(-900, 900),
                       MOTION + 0x20: r.uniform(-900, 900)}
        else:
            doubles = {MOTION + 0x50: r.uniform(-60, 60), MOTION + 0x10: r.uniform(-60, 60),
                       MOTION + 0x20: r.uniform(-60, 60)}
        s["doubles"] = doubles
        yield call(f"jump {index}", F_JUMP, s)


ATTACK_ARROWS = (0, 1, 2, 3, 4, 6, 8, 12)
QUIET_ARROWS = (0, 1, 2, 3, 4, 5, 8, 10)


def arrow_grid(r, function, label, state, attack=(0, 1), **extra):
    """Standing on the ground with every combination of the four arrow bits, with and without an attack."""
    for arrows in range(16):
        for p1 in attack:
            if p1 and arrows not in ATTACK_ARROWS:
                continue
            if len(attack) == 1 and arrows not in QUIET_ARROWS:
                continue
            allowed = (0, 1, 4, 6, 0x63, 0x333) if p1 else (0, 1, 6, 0x63, 0x333)
            s = grounded(r, state=state, p1=p1, pvalue=r.choice(allowed), pvalue2=r.choice(allowed),
                         input=input_bits(r, arrows), p10=(5, 700, 999, 1000, 2000, -5)[(arrows + p1) % 6],
                         p0=p1 ^ (arrows & 1), p2=0 if (arrows >> 2) & 1 else 1, nophysics=(arrows >> 3) & 1,
                         step=5, dt=5, p3c=(5, 4, 6, 5)[(arrows + p1) % 4],
                         timers=[(0, 5, 6, 9)[(arrows + p1) % 4], (3, 5, 6, 7, 9, 4)[(arrows // 4 + arrows + p1) % 6], (0, 5, 6, 9)[(arrows // 4) % 4],
                                 (5, 9)[arrows % 2], (0, 5, 7, 5)[(arrows // 8 + arrows) % 4], (3, 5, 9, 6)[(arrows + p1) % 4]],
                         p_x=(arrows + p1) % 2, **extra)
            yield call(f"{label} grid {arrows:x} {p1}", function, s)


def right_cases(r):
    yield from arrow_grid(r, F_RIGHT, "right", 8)
    for index in range(8):
        s = sweep_world(r, state=r.choice((8, 9, 0x138E, 0x18)), mode=r.choice((1, 1, 2, 3, 4, 4, 5, 6, 7)))
        if s["platform"] and s["mode"] in (1, 2, 4, 5, 6):
            s["mode"] = 7
        yield call(f"right {index}", F_RIGHT, s)
    for index in range(4):
        s = grounded(r, state=8, p_x=r.choice((0, 1)))
        yield call(f"right grounded {index}", F_RIGHT, s)


def forward_cases(r):
    yield from arrow_grid(r, F_FORWARD, "forward", 0x19, sound_off=0)
    yield from arrow_grid(r, F_FORWARD, "forward quiet", 0x19, attack=(0,), sound_off=1)
    for index in range(8):
        s = sweep_world(r, state=0x19, mode=r.choice((1, 1, 2, 3, 4, 5, 6, 7)))
        if s["platform"] and s["mode"] in (1, 2, 4, 5, 6):
            s["mode"] = 7
        yield call(f"forward {index}", F_FORWARD, s)
    for index in range(4):
        s = grounded(r, state=0x19, probe=r.choice((None, "wide", "high")), sound_off=r.choice((0, 1)),
                     p_x=r.choice((0, 0, 1)), p0=r.choice((0, 1)))
        yield call(f"forward grounded {index}", F_FORWARD, s)


def idle_cases(r):
    yield from arrow_grid(r, F_IDLE, "idle", 0x18)
    yield from arrow_grid(r, F_IDLE, "idle lowered", 0x1A, attack=(0,))
    for index in range(6):
        state = r.choice((5000, 5000, 0x18, 0x1A))
        s = sweep_world(r, state=state, mode=r.choice((1, 2, 3, 4, 5, 6, 7)), p_x=1 if state == 5000 else r.choice((0, 1)))
        if s["platform"] and s["mode"] in (1, 2, 4, 5, 6):
            s["mode"] = 7
        s["doubles"] = {MOTION + 0x28: r.choice((30.0, -30.0, 0.0, 0.0, r.uniform(-40, 40)))}
        yield call(f"idle {index}", F_IDLE, s)
    for index in range(4):
        s = grounded(r, state=r.choice((0x18, 0x1A, 0x138E)), p_x=r.choice((0, 1)), p1=r.choice((0, 0, 1)))
        s["input"] = input_bits(r, r.choice((0, 4, 8, 12, 1, 2)))
        yield call(f"idle grounded {index}", F_IDLE, s)
    carry = [(arrows, geom, p2, p3, dbl, False) for arrows in (0, 1, 2) for geom in (0, 1)
             for p2, p3, dbl in ((0, 0, 0.0), (1, 0, 30.0), (1, 0, -30.0), (1, 1, 17.5))]
    carry += [(0, 1, 1, 0, 30.0, True), (2, 1, 1, 0, 30.0, True)]
    for index, (arrows, geom, p2, p3, dbl, platform) in enumerate(carry):
        s = sweep_world(r, state=5000, mode=4 if geom else 1, p_x=1, platform=platform, p2=p2, p3=p3, p0=1 if arrows == 1 else 0, dt=4, step=4, p3c=(4, 3, 5, 4)[index % 4], velocity=(0, 0), p7=0, p8=1, p_c=1, pvalue=1, pvalue2=1, empty_tiles=False,
                        nophysics=0, power=0, p_f=0, player="raw", present=NAMES, margin=(300, 300), probe=None, q_size=0x20)
        s["rules"] = [] if geom else [(0, s["y"] + 61, 2047, 2047, 1)]
        s["doubles"] = {**STILL, MOTION + 0x28: dbl}
        s["p1"] = 0
        s["input"] = [0x20 if (p2 and p3) else 0, arrows << 24, r.getrandbits(32)]
        yield call(f"carry {index}", F_IDLE, s)


PRESSED = (1, 2, 4, 8, 0x20, 0x40, 0x80, 0x100, 0x1000000, 0x2000000)


def pressed_bits(r, extra=0, drop=0):
    bits = 0
    for bit in PRESSED:
        if r.random() < 0.18:
            bits |= bit
    return (bits | extra) & ~drop


STABLE = {
    "empty_tiles": False, "player": "raw", "present": NAMES, "p_f": 0, "probe": None, "lookup": None, "engine": 1,
    "notify": False, "death": 0, "margin": (300, 300), "nophysics": 0, "st_timer": 0, "p_c": 1, "power": 0,
    "power_time": 0, "sound_off": 1, "platform": False, "p_x": 0, "p1": 0, "limits": None, "resume": (-1, -1),
    "globals_extra": {0x537230: 0, 0x537214: 0, 0x53C9F8: 1, 0x52C6EC: 1, 0x52C6E4: 1, 0x534EB4: 1, 0x53C9C0: 0,
                      0x537220: 0},
}


def pworld(r, state, stable=True, **kw):
    base = draw(r)
    x, y = base["x"], base["y"]
    p1 = kw.get("p1", r.choice((0, 0, 1)))
    allowed = (0, 1, 4, 6, 0x63, 0x333)
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
        "p_c": r.choice((-5, -1, 0, 1, 2, 3, 9)),
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
        "limits": None,
        "lookup": r.choice((None, "wide", "high")),
        "resume": r.choice(((-1, -1), (-1, 5), (r.randrange(200, 1800), r.randrange(200, 1800)))),
        "globals_extra": {0x537230: r.choice((0, 0, 1)), 0x537214: r.choice((0, 0, 1)),
                          0x53C9F8: r.getrandbits(16), 0x52C6EC: r.getrandbits(8), 0x52C6E4: r.getrandbits(16),
                          0x534EB4: r.choice((0, 1)), 0x53C9C0: r.choice((0, 2, 3)),
                          0x537220: r.choice((0, 1))},
    }
    if stable:
        values.update(STABLE)
    values.update(kw)
    return draw(r, **values)


def player_case(label, s):
    def setup(env):
        return build(env, s)
    return Case(label, F_PLAYER, setup, arguments=(lambda t: t["actor"],))


def directed_player(r):
    """Standing on solid ground, a ledge or a deadly tile, with a chosen key."""
    for index in range(10):
        base = draw(r)
        x, y = base["x"], base["y"]
        floor = (0, y + 61, 2047, 2047, 1)
        kind = index % 8
        rules = [floor]
        if kind == 1:
            rules = [(x + 5 + r.randrange(0, 11), y + 61, 2047, 2047, 1)]      # ground under the right foot only
        elif kind == 2:
            rules = [(0, y + 61, x - 5 - r.randrange(0, 11), 2047, 1)]          # ground under the left foot only
        elif kind in (3, 4):
            rules = [(x - 4, y + 55, x + 4, y + 70, 4), floor]                  # a deadly tile under the feet
        elif kind == 5:
            rules = [(x - 4, y + 55, x + 4, y + 70, 4)]
        arrow = r.choice((0, 0x1000000, 0x2000000))
        jump = 1 if kind == 6 else r.choice((0, 0, 1))
        s = pworld(r, r.choice((0x18, 0x18, 0x18, 4, 8, 0x19)), stable=False, x=x, y=y, rules=rules, mode=1 if kind != 7 else 4,
                   input=[arrow | jump | (8 if r.random() < 0.3 else 0), r.choice((0, 1)), r.getrandbits(32)],
                   p1=1 if kind == 6 else r.choice((0, 0, 1)), p8=1 if kind == 6 else r.choice((0, 1)),
                   platform=kind in (4, 5) or r.random() < 0.1, margin=(300, 300), nophysics=0,
                   p_x=r.choice((0, 1)), power=0, death=0, mover=(0, 0))
        if s["platform"]:
            s["flags"] |= 0x10
        yield player_case(f"player directed #{index}", s)


def poke_sweeps(r):
    """Fields changed by the world in the middle of a call: the mode, the attack flag, the platform."""
    for index in range(10):
        base = draw(r)
        x, y = base["x"], base["y"]
        flags = base["flags"]
        pokes = []
        for _ in range(r.randrange(1, 3)):
            when = r.choice((1, 1, 2, 3, 4, 6, 9, r.randrange(5, 45)))
            pick = r.randrange(7)
            if pick == 0:
                pokes.append((when, "actor", 0xCC, r.choice((1, 2, 4, 6))))
            elif pick == 1:
                pokes.append((when, "p", 4, 1))
            elif pick == 2:
                pokes.append((when, "actor", 8, flags | 0x10))
                pokes.append((when, "actor", 0x80, lambda h: h["mover"]))
            elif pick == 3:
                pokes.append((when, "p", 0, r.choice((0, 1))))
            elif pick == 4:
                pokes.append((when, "p", 0x34, r.choice((0, 5))))
            elif pick == 5:
                pokes.append((1, "actor", 0x120, r.choice((-6, -4, -20))))
            else:
                pokes.append((when, "actor", 0xCC, 1))
        floor = (0, y + 61, 2047, 2047, 1)
        rules = r.choice(([floor], [floor], [(x + 5 + r.randrange(0, 11), y + 61, 2047, 2047, 1)],
                          [(0, y + 61, x - 5 - r.randrange(0, 11), 2047, 1)], [(x - 4, y + 55, x + 4, y + 70, 4), floor]))
        pressed = r.choice((0, 0, 1, 0x1000000, 0x2000000, 1 | 0x1000000, 8, 8 | 0x1000000))
        s = pworld(r, r.choice((0x18, 0x18, 0x18, 0x138E, 0x19, 0x1A, 8, 9, 4)), stable=False, x=x, y=y, rules=rules,
                   mode=r.choice((1, 1, 2, 4)), pokes=tuple(pokes), power=0, death=0, mover=(0, 0), platform=False,
                   input=[pressed, r.getrandbits(4) << 24 | r.choice((0, 1)), r.getrandbits(32)],
                   p1=r.choice((0, 0, 1)), p8=r.choice((0, 1)), nophysics=0, margin=(300, 300),
                   p_x=r.choice((0, 1)))
        yield player_case(f"player poked #{index}", s)


def poke_grid(r):
    """The mode changes under the caller on each of the first calls of the tile query."""
    index = 0
    for when in (2, 4):
        for pressed in (1, 0x2000000, 0x1000000):
            for value in (4, 6, 1):
                base = draw(r)
                x, y = base["x"], base["y"]
                s = pworld(r, 0x18, x=x, y=y,
                           rules=[(0, y + 61, 2047, 2047, 1)], mode=1,
                           pokes=((when, "actor", 0xCC, value),), power=0, death=0, mover=(0, 0), platform=False,
                           input=[pressed, pressed & 0x3000000, r.getrandbits(32)],
                           nophysics=0, margin=(300, 300), p1=0, p8=1, p_x=0)
                index += 1
                yield player_case(f"player poke grid {when} {pressed:#x} {value}", s)
    for value in (1, 2, 3, 5):
        base = draw(r)
        x, y = base["x"], base["y"]
        s = pworld(r, 0x18, x=x, y=y, rules=[(0, y + 61, 2047, 2047, 1)], mode=1,
                   pokes=((value, "p", 4, 1),), power=0, death=0, mover=(0, 0), platform=False,
                   input=[1, 0, r.getrandbits(32)], nophysics=0, margin=(300, 300), p1=1, p8=1, p_x=0)
        yield player_case(f"player poke attack jump {value}", s)


def teeter_sweeps(r):
    for index in range(6):
        base = draw(r)
        x, y = base["x"], base["y"]
        side = r.randrange(3)
        if side == 0:
            rules = [(x + 5 + r.randrange(0, 11), y + 61, 2047, 2047, 1)]
        elif side == 1:
            rules = [(0, y + 61, x - 5 - r.randrange(0, 11), 2047, 1)]
        else:
            rules = [(0, y + 61, 2047, 2047, 1)]
        flags = base["flags"]
        pokes = []
        for _ in range(r.randrange(0, 3)):
            when = r.randrange(4, 50)
            pick = r.randrange(4)
            if pick == 3:
                pokes.append((when, "p", 0, 1))
            elif pick == 0:
                pokes.append((when, "actor", 0xCC, r.choice((6, 4, 1))))
            elif pick == 1:
                pokes.append((when, "actor", 8, flags | 0x10))
                pokes.append((when, "actor", 0x80, lambda h: h["mover"]))
            else:
                pokes.append((when, "actor", 0x120, r.choice((-6, -20))))
        s = pworld(r, 0x18, stable=False, x=x, y=y, rules=rules, mode=1, pokes=tuple(pokes), power=0, death=0, mover=(0, 0),
                   platform=False, input=[r.choice((0, 0, 8)), r.getrandbits(4) << 24 | r.choice((0, 1)), r.getrandbits(32)],
                   p0=r.choice((0, 1)), p1=0, p8=1, nophysics=0, margin=(300, 300), p_x=r.choice((0, 1)))
        yield player_case(f"player teeter #{index}", s)
    for when, pick in [(w, k) for w in (4, 12, 40) for k in range(4)] + [(w, k) for w in (22, 25, 28) for k in (0, 1)] + [(w, 2) for w in (1, 2, 3, 5, 6)]:
        if True:
            base = draw(r)
            x, y = base["x"], base["y"]
            poke = [[(when, "actor", 0xCC, 6)], [(when, "p", 0, 1)], [(when, "actor", 0x120, -6)],
                    [(when, "actor", 8, base["flags"] | 0x10), (when, "actor", 0x80, lambda h: h["mover"])]][pick]
            s = pworld(r, 0x18, x=x, y=y, rules=[(x + 8, y + 61, 2047, 2047, 1)], mode=3,
                       pokes=tuple(poke), power=0, death=0, mover=(0, 0), platform=False,
                       input=[0, 0, r.getrandbits(32)], p0=0, p1=0, p8=1,
                       nophysics=0, margin=(300, 300), p_x=0)
            yield player_case(f"player teeter grid {when} {pick}", s)
    for index in range(6):
        base = draw(r)
        x, y = base["x"], base["y"]
        s = pworld(r, (0x18, 0x138E, 0x19)[index % 3], x=x, y=y, rules=[(0, 0, 2047, 2047, 4)], mode=7,
                   platform=True, power=0, death=0, mover=(0, 0), nophysics=0, margin=(300, 300),
                   input=[r.choice((0, 8)), 0, r.getrandbits(32)], p1=0, p8=1, p_x=0,
                   globals_extra={0x537230: 0, 0x537214: 0, 0x53C9F8: 1, 0x52C6EC: 1, 0x52C6E4: 1, 0x534EB4: 1,
                                  0x53C9C0: 0, 0x537220: 0})
        s["flags"] |= 0x10
        yield player_case(f"player spikes #{index}", s)


def crouch_cases(r):
    """Standing at a ledge (ground under one foot only) with the down keys held."""
    for held in (0x4000000, 0x8000000, 0):
        for side in (0, 1):
            base = draw(r)
            x, y = base["x"], base["y"]
            rules = [[(x + 5 + 3, y + 61, 2047, 2047, 1)], [(0, y + 61, x - 5 - 3, 2047, 1)]][side]
            s = pworld(r, 0x18, x=x, y=y, rules=rules, mode=(2, 3)[side], power=0, death=0,
                       mover=(0, 0), platform=False, input=[0, held, r.getrandbits(32)], p0=side, p1=0, p8=1,
                       nophysics=0, margin=(300, 300), p_x=0)
            yield player_case(f"player crouch {held:#x} {side}", s)


def platform_stand_cases(r):
    """Standing on a moving platform: the carried position goes through the collision step."""
    for index, (dx, dy) in enumerate(((30, 0), (-30, 0), (0, 30), (0, -30), (40, 40), (-40, -40))):
        for geometry_kind in (0, 1):
            base = draw(r)
            x, y = base["x"], base["y"]
            rules = [[(0, y + 61, 2047, 2047, 1)], [(x - 80, y + 61, x + 80, 2047, 1)]][geometry_kind]
            s = pworld(r, 0x18, x=x, y=y, rules=rules, mode=1, power=0, death=0, mover=(dx, dy), platform=True,
                       input=[0, 0, r.getrandbits(32)], p0=index % 2, p1=0, p8=1, nophysics=0, margin=(300, 300), p_x=0)
            s["flags"] |= 0x10
            yield player_case(f"player platform stand {index} {geometry_kind}", s)


RANDOM_STATES = (0, 0x17, 0x1F, 0x1388, 0x138A, 0x138C, 0x138F, 0x1B, 0x19, 4, 8)


def player_cases(r):
    # states with no or little input: the initial and restart states, and the plain dispatchers
    for state in (0, 0x17, 0x1F, 0x1388, 0x1389, 0x138A, 0x138B, 0x138C, 0x138D, 0x138F, 0x1391, 0x1B, 0x19, 0x1A,
                  4, 8, 9, 1, 0x20, 0x1390, 7):
        kw = {}
        if state in (0x1388, 0x1389, 0x138C, 0x138D, 0x1B, 0x138F):
            kw["p_x"] = 1
        if state in RANDOM_STATES:
            yield player_case(f"player {state:#x} random", pworld(r, state, stable=False, **kw))
        # fixed variants: every combination that decides a branch in the state handlers
        for variant in range(2):
            on = variant == 0
            base = draw(r)
            x, y = base["x"], base["y"]
            fixed = dict(kw, x=x, y=y, rules=[(0, y + 61, 2047, 2047, 1)], margin=(300, 300), nophysics=0,
                         power=0x26bc if on else 0, platform=on, mode=4 if on else 1, engine=4 if on else 1,
                         probe="wide", lookup="wide" if on else "high", probe_items=0x2A if on else 0x55, timers=[0 if not on else 3000] * 5 + [3000],
                         globals_extra={0x534EB4: 0, 0x537230: 0, 0x537214: 0, 0x53C9F8: 1, 0x52C6EC: 1,
                                        0x52C6E4: 100 if on else 1, 0x53C9C0: 2 if on else 0, 0x537220: 0},
                         p1=0, p_c=1, input=[4 if (on and state == 0x1388) else 0, (0x3000000 if on else 0x1000000) if state in (8, 9) else 0, r.getrandbits(32)],
                         mover=(0, 0), death=0, notify=on, resume=(-1, -1) if on else (500, 500))
            s = pworld(r, state, **fixed)
            if on:
                s["flags"] |= 0x10
            else:
                s["flags"] |= 0x400000
            yield player_case(f"player {state:#x} fixed {variant}", s)
    for state in (8, 9):
        for arrows in (0x1000000, 0x2000000, 0x8000000, 0):
            for attack in (0, 2):
                s = pworld(r, state, input=[1 | attack, arrows, r.getrandbits(32)], p1=0, p_x=0)
                yield player_case(f"player {state:#x} arrows {arrows:#x}", s)
    for resume in ((-1, -1), (-1, 5), (5, -1), (500, 500)):
        for engine in (1, 4):
            yield player_case(f"player 0x17 resume {resume} {engine}", pworld(r, 0x17, resume=resume, engine=engine))
    for index in range(42):
        base = draw(r)
        x, y = base["x"], base["y"]
        floor = (0, y + 61, 2047, 2047, 1)
        geometry_kind = index % 7
        rules = [[floor], [], [(x - 30, y - 150, x + 30, y + 150, 3), floor], [(0, y + 61, 2047, y + 80, 2)],
                 [(x - 4, y + 55, x + 4, y + 70, 4), floor], [(x + 17, 0, x + 80, 2047, 1), floor],
                 [(0, 0, 2047, y - 53, 1), floor]][geometry_kind]
        arrows = (0, 0x1000000, 0x2000000)[(index // 7) % 3]
        s = pworld(r, (0x18, 4)[(index // 21) % 2], x=x, y=y, rules=rules, p_x=index % 2, p1=(index // 3) % 2, p8=(index // 2) % 2,
                   platform=index % 5 == 0, input=[(arrows if index % 3 else 0) | (1 if index % 2 == 0 else 0) | (8 if index % 4 == 0 else 0), arrows | (0x100 if index % 6 == 0 else 0) | (0x4000000 if index % 4 == 2 else 0), r.getrandbits(32)],
                   fresh_p=False, mode=(1, 3)[index % 2], nophysics=0, margin=(300, 300), power=(0, 0x26bc)[(index // 3) % 2],
                   timers=[near(r, 5) for _ in range(6)])
        if s["platform"]:
            s["flags"] |= 0x10
        yield player_case(f"player 0x18 jump {index}", s)
    for index in range(28):
        base = draw(r)
        x, y = base["x"], base["y"]
        floor = (0, y + 61, 2047, 2047, 1)
        rules = [[floor], [], [(x - 30, y - 150, x + 30, y + 150, 3), floor], [(0, y + 66, 2047, 2047, 1)],
                 [(x - 4, y + 55, x + 4, y + 70, 4), floor], [(x + 17, 0, x + 80, 2047, 1), floor],
                 [(0, y + 57, 2047, 2047, 1)]][index % 7]
        arrow = (0x1000000, 0x2000000)[(index // 7) % 2]
        combo = (index // 14 + index // 7) % 2
        power, platform, t0 = ((0x26bc, False, 3000), (0, True, 0))[combo]
        s = pworld(r, 0x18, x=x, y=y, rules=rules, p_x=index % 2, p1=0, p8=1,
                   platform=platform, input=[arrow, arrow, r.getrandbits(32)],
                   fresh_p=False, mode=(1, 3, 2)[index % 3], nophysics=0, margin=(300, 300), power=power,
                   timers=[t0, 3000, 3000, 3000, 3000, 3000])
        if platform:
            s["flags"] |= 0x10
        yield player_case(f"player 0x18 walk start {index}", s)
    for index in range(0):
        pressed = pressed_bits(r, drop=0x3000001)
        held = (sum(1 << (24 + k) for k in range(4) if r.random() < 0.4)) | r.choice((0, 1, 4, 0x100))
        s = pworld(r, 0x18, p_x=r.choice((0, 1)), p1=r.choice((0, 0, 1)), p8=r.choice((0, 1)),
                   platform=r.random() < 0.25, input=[pressed, held, r.getrandbits(32)],
                   fresh_p=False, mode=r.choice((1, 1, 2, 3, 4, 5, 6)),
                   timers=[near(r, 5) for _ in range(6)])
        if s["platform"]:
            s["flags"] |= 0x10
        yield player_case(f"player 0x18 #{index}", s)
    yield from directed_player(r)
    yield from poke_sweeps(r)
    yield from poke_grid(r)
    yield from crouch_cases(r)
    for facing in (0, 1):
        for attack in (2, 4):
            base = draw(r)
            x, y = base["x"], base["y"]
            s = pworld(r, 0x18, x=x, y=y, rules=[(0, y + 61, 2047, 2047, 1)], mode=3, power=0, death=0, mover=(0, 0),
                       platform=False, p0=facing, p1=0, p8=1, p_c=1, input=[attack, 0, r.getrandbits(32)], nophysics=0,
                       margin=(300, 300))
            yield player_case(f"player attack {facing} {attack}", s)
    for p_c in (-1, 0, 1, 2, 3):
        base = draw(r)
        x, y = base["x"], base["y"]
        s = pworld(r, 0x18, x=x, y=y, rules=[(0, y + 61, 2047, 2047, 1)], mode=3, power=0, death=0, mover=(0, 0),
                   platform=False, p_c=p_c, p1=0, p8=1, input=[8, 0, r.getrandbits(32)], nophysics=0, margin=(300, 300))
        yield player_case(f"player cycle {p_c}", s)
    for index, kind in enumerate(("inside", "past low", "past high")):
        base = draw(r)
        x, y = base["x"], base["y"]
        limits = ((x - 20, x + 20, y - 20, y + 20), (x + 5, x + 30, y + 5, y + 30), (x - 90, x - 20, y - 90, y - 20))[index]
        s = pworld(r, 0x18, x=x, y=y, rules=[(0, y + 61, 2047, 2047, 1)], mode=2, power=0, death=0, mover=(0, 0),
                   platform=False, limits=limits, input=[0, 0, r.getrandbits(32)], nophysics=0, margin=(300, 300))
        yield player_case(f"player limits {kind}", s)
    yield from teeter_sweeps(r)
    for index in range(2):
        s = pworld(r, 0, fresh_p=True, lookup=("wide", "high")[index], probe_items=(0x55, 0x2A)[index],
                   engine=(4, 1)[index], globals_extra={0x534EB4: 0},
                   globals={0x534C80 + 4 * k: (0x1357 + 0x2B * k + index) & M for k in range(0x4E)})
        yield player_case(f"player fresh #{index}", s)
    for index in range(12):
        s = pworld(r, 0x138E, platform=index % 5 == 4,
                   input=[1 if index % 4 == 3 else 0, (0x2000000, 0x1000000, 0)[index % 3], r.getrandbits(32)])
        yield player_case(f"player 0x138e #{index}", s)


def idle_timer_cases(r):
    """Ducking in place: the timer at p+0xfc around the frame step."""
    for mode in (1, 3):
        for t1 in (9, 6, 5, 3):
            s = grounded(r, state=0x18, p1=0, input=input_bits(r, 4), step=5, dt=5, mode=mode,
                         timers=[0, t1, 0, 9, 0, 3], p_x=0)
            yield call(f"idle timer {mode} {t1}", F_IDLE, s)


def mode_poke_cases(r):
    """The collision result changes the mode while the walk function runs."""
    for function, name, state in ((F_RIGHT, "right", 8), (F_FORWARD, "forward", 0x19), (F_IDLE, "idle", 0x18)):
        for arrows in (1, 2):
            for value in (6, 4):
                for p_f in ((8, 0x12) if (function in (F_RIGHT, F_IDLE) and value == 4) else (0,)):
                    s = grounded(r, state=state, input=input_bits(r, arrows), pokes=((2, "actor", 0xCC, value),), p_x=0,
                                 p_f=p_f)
                    yield call(f"{name} mode poke {arrows} {value} {p_f}", function, s)


# --------------------------------------------------------------------------
# Targeted cases: the write of the mode after the animation step, the order of
# the state reset against the animation lookup, and the motion word at 0x534dd0
# --------------------------------------------------------------------------

NONZERO_STILL = {**STILL, MOTION + 0x18: 1e-9}     # the word at 0x534dd0 is not zero before the walk functions clear it


def redirect_owner(env, tok):
    """The animation player's owner pointer (actor +0x18c) points 0xbc into the actor, so the step of
    the animation (which clears owner +0x10) clears the actor's mode (+0xcc) behind the caller's back."""
    env.put(tok["actor"] + 0x18C, tok["actor"] + 0xBC)


def sqrt_zero_cases(r):
    """Operands that cancel exactly: the second square root of the jump arc sees exactly zero."""
    for e_value, a_value in ((189153986772.0, -1618304510824.0), (-53835440583.0, 1119748088732.0),
                             (7519043566053.0, -800590451019.0)):
        s = sweep_world(r, state=0x18, p1=0, power=0)
        s["input"] = [0, 0, r.getrandbits(32)]
        s["doubles"] = {MOTION + 0x50: e_value, MOTION + 0x20: a_value, MOTION + 0x10: 0.0}
        yield call(f"jump sqrt zero {e_value!r}", F_JUMP, s)


def mode_write_cases(r):
    # stand: the mode is cleared by the animation step, then written back
    for index in range(8):
        s = draw(r, p_x=index % 2, q_size=0x20, p1=(index // 2) % 2, player="raw", present=NAMES)
        yield call(f"stand owner {index}", F_STAND, s, redirect_owner)
    # right: the stand branch
    for index in range(4):
        s = grounded(r, state=8, p_x=index % 2, p1=index // 2, input=input_bits(r, 0), doubles=NONZERO_STILL)
        yield call(f"right stand owner {index}", F_RIGHT, s, redirect_owner)
    # forward: stand, land, and the two walk branches
    for p1 in (0, 1):
        for arrows, p10, label in ((0, 5, "stand"), (0, 2000, "land")):
            s = grounded(r, state=0x19, p_x=0, p1=p1, p10=p10, input=input_bits(r, arrows), doubles=NONZERO_STILL)
            yield call(f"forward {label} owner {p1}", F_FORWARD, s, redirect_owner)
        for arrows, label in ((1, "left"), (2, "right")):
            s = grounded(r, state=0x19, p_x=0, p1=p1, p10=5, input=input_bits(r, arrows), doubles=NONZERO_STILL)
            yield call(f"forward walk {label} {p1}", F_FORWARD, s)


def order_cases(r):
    # the world turns the mode to climbing, so the climb branch clears the motion word
    for function, name, state in ((F_FORWARD, "forward", 0x19), (F_IDLE, "idle", 0x18)):
        for doubles, label in ((NONZERO_STILL, "still"), ({}, "random")):
            for arrows in (1, 2):
                for p1 in (0, 1):
                    s = grounded(r, state=state, input=input_bits(r, arrows), pokes=((2, "actor", 0xCC, 6),), p_x=0,
                                 p1=p1, doubles=doubles)
                    yield call(f"{name} climb {label} {arrows} {p1}", function, s)
    # the world turns the mode to falling, with an attack under way
    for function, name, state in ((F_RIGHT, "right", 8), (F_IDLE, "idle", 0x18)):
        for arrows in (1, 2):
            for p1 in (0, 1):
                s = grounded(r, state=state, input=input_bits(r, arrows), pokes=((2, "actor", 0xCC, 4),), p_x=0,
                             p_f=0, p1=p1, doubles=NONZERO_STILL)
                yield call(f"{name} fall {arrows} {p1}", function, s)
    # falling with an attack under way: the stored animation, then the fall animation
    for index in range(4):
        s = sweep_world(r, p_f=0, p1=index // 2, p_x=index % 2, q_count=index % 3)
        s["input"] = [0, 0, r.getrandbits(32)]
        yield call(f"fall attack {index}", F_FALL, s,
                   arguments=(lambda t: t["actor"], lambda t: t["state"], lambda t: t["p"], 0))


def attack_key_cases(r):
    """Falling (0x19): the attack keys are read before the walk function runs."""
    for mode in (1, 4):
        for bit, p_c in ((2, 1), (4, 1), (4, 2), (4, 3), (0x40, 1), (0x80, 1), (0x100, 1)):
            base = draw(r)
            x, y = base["x"], base["y"]
            s = pworld(r, 0x19, x=x, y=y, rules=[(0, y + 61, 2047, 2047, 1)], mode=mode, p1=0, p_c=p_c,
                       input=[bit, 0, r.getrandbits(32)], p_x=0, power=0, death=0, mover=(0, 0), platform=False,
                       nophysics=0, margin=(300, 300))
            yield player_case(f"player 0x19 key {bit:#x} {p_c} {mode}", s)


def cases(random_source):
    r = random_source
    yield from rect_cases(r)
    yield from lookup_cases(r)
    yield from reset_cases(r)
    yield from fall_cases(r)
    yield from flip_cases(r)
    yield from jump_cases(r)
    yield from jump_edge_cases(r)
    yield from right_cases(r)
    yield from forward_cases(r)
    yield from idle_cases(r)
    yield from mode_poke_cases(r)
    yield from idle_timer_cases(r)
    yield from player_cases(r)
    # stand
    for index in range(10):
        s = draw(r, p_x=r.choice((0, 1)), q_size=r.choice((0x20, 0x40, 0x10, 0)), p1=r.choice((0, 1)),
                 player=r.choice(("raw", "fresh", "none")),
                 present=r.choice((NAMES, ())))
        yield call(f"stand {index}", F_STAND, s)
    yield from sqrt_zero_cases(r)
    yield from mode_write_cases(r)
    yield from order_cases(r)
    yield from attack_key_cases(r)
