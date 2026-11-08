"""Cases for level_one_player_actions_01: Observed Level 1 player actions batch 1.

Every random value is drawn when the case list is generated, never inside a
setup function, so each setup rebuilds the identical memory image.
"""
import random
import struct

from clawparity.cases import Case

CONSTRUCT = 0x40E750
BEGIN_STATE = 0x40E690
DISPATCH_BY_ID = 0x40EBE0
ENTER_ANIMATION = 0x40EFA0
STEP_ANIMATION = 0x40F010
LAND = 0x40F0E0
STEP_LANDED = 0x40F200
UPDATE = 0x40F2A0
SET_FIELD = 0x40F6A0
RESET_VECTORS = 0x40F6F0
BIND_CONTEXT = 0x40F760

OPERATOR_NEW = 0x4F63EC

TIME = 0x537210
ANIMATION_STEP = 0x5430C4
TRIE_OBJECT = 0x537668
TRIE_ROOT = 0x537680
NAME_TABLE = 0x5376A0  # minimum, maximum, base, (unused), stride
HANDLER_TABLE = 0x5349E8  # minimum, maximum, base, (unused), stride
BEHAVIOUR_COUNT = 0x52A190
BEHAVIOUR_IDS = 0x537EC8
BEHAVIOUR_SPEED = 0x537FD0
BEHAVIOUR_FLAGS = 0x5380D8
BEHAVIOUR_HANDLERS = 0x538208
BEHAVIOUR_SLOPE = 0x538310
DEFAULTS_READY = 0x538418
DEBUG_ENABLED = 0x532C0C

KEY_FALLING = "LS_FALLING"
KEY_BOUNCE = "LS_BOUNCE"
KEY_DEAD = "LS_DEAD"
KEY_CYCLE = "GAME_CYCLE100"
KEY_SOUND = "GAME_PUBOUNCE1"

M = 0xFFFFFFFF


def f64(value):
    return struct.pack("<d", float(value))


def s32(r, low, high):
    return r.randrange(low, high) & M


# --------------------------------------------------------------------------
# Object builders
# --------------------------------------------------------------------------

def cstring(env, text):
    """A reference counted string: the character pointer has a 12 byte header in front of it."""
    data = text.encode() + b"\0"
    base = env.object(12 + len(data) + 4, "string", fill=0)
    env.put(base, 1, len(text), len(text) + 1)
    env.write(base + 12, data)
    return base + 12


def string_map(env, entries):
    """An object whose +0x10 is a one-bucket string hash map. The entries are chained in order."""
    holder = env.object(0x40, "map-owner", fill=0)
    table = env.object(8, "map-buckets", fill=0)
    env.put(holder + 0x14, table, 1)
    head = 0
    for key, value in reversed(entries):
        key_pointer = env.object(len(key) + 4, "map-key", data=key.encode() + b"\0")
        node = env.object(0x10, "map-node", fill=0)
        env.put(node, head, 0, key_pointer, value)
        head = node
    env.put(table, head)
    return holder


def animation(env, frame_value, count):
    frame = env.object(0x40, "frame", fill=0)
    env.put(frame + 0x1C, frame_value)
    frames = env.object(8, "frames", fill=0)
    env.put(frames, frame)
    result = env.object(0x40, "animation", fill=0)
    env.put(result + 0x0C, frames)
    env.put(result + 0x10, count)
    return result


def sound_chain(env):
    """Three linked objects ending in one whose +0x78 is zero."""
    last = env.object(0x90, "sound-last", fill=0)
    middle = env.object(0x20, "sound-middle", fill=0)
    env.put(middle + 0x10, last)
    first = env.object(0x20, "sound-first", fill=0)
    env.put(first + 0x10, middle)
    return first


def install_trie(env, values, decoys=()):
    """The three state names in a bit-indexed trie. A name in `decoys` gets a leaf whose key differs."""
    leaves = {}
    for key in (KEY_DEAD, KEY_BOUNCE, KEY_FALLING):
        text = key[:-1] + "X" if key in decoys else key
        pointer = env.object(len(text) + 4, "trie-key", data=text.encode() + b"\0")
        leaf = env.object(0x20, "trie-leaf", fill=0)
        env.put(leaf + 8, 0, pointer, values.get(key, 0))
        leaves[key] = leaf
    inner = env.object(0x20, "trie-inner", fill=0)
    env.put(inner, leaves[KEY_BOUNCE], leaves[KEY_FALLING], 3 * 8 + 2)
    root = env.object(0x20, "trie-root", fill=0)
    env.put(root, leaves[KEY_DEAD], inner, 3 * 8 + 1)
    env.put(TRIE_ROOT, root)


def name_table(env, low, names, stride):
    """The table of state names starting at index `low`. Slot 0 of each entry is a string pointer."""
    high = low + len(names) - 1
    base = env.object(stride * len(names) + 8, "name-table", fill=0)
    for position, text in enumerate(names):
        slot = base + position * stride
        env.put(slot, cstring(env, text))
        if stride > 4:
            env.put(slot + 4, 0x5000 + position)
    env.put(NAME_TABLE, low & M, high & M, base)
    env.put(NAME_TABLE + 0x10, stride)
    return base


# --------------------------------------------------------------------------
# The shared world
# --------------------------------------------------------------------------

def draw(r, **override):
    """All the numbers of one world."""
    spec = {
        "seed": r.getrandbits(32),
        "flags": r.getrandbits(32) & ~0x400010,
        "hit": False,                       # actor flag 0x400000
        "x": r.randrange(-3000, 3000),
        "y": r.randrange(-3000, 3000),
        "a64": r.randrange(1, 5000),
        "a100": s32(r, -2000, 2000),
        "a148": s32(r, -2000, 2000),
        "a14c": s32(r, -2000, 2000),
        "a164": r.getrandbits(32) & ~0x200,
        "a170": r.randrange(1, 1 << 30),
        "a0d0": r.choice((1, r.randrange(2, 99))),
        "a0fc": r.getrandbits(32),
        "state": 7,
        "limits": [r.randrange(1, 900) for _ in range(4)],  # B[0x2c], B[0x34], B[0x30], B[0x38]
        "ring": [r.choice((0, r.randrange(1, 1 << 30))) for _ in range(8)],  # B[f0 f8 f4 fc 100 108 104 10c]
        "b1c": r.randrange(1, 1 << 30),
        "b18": r.getrandbits(32),
        "b168": r.getrandbits(32),
        "b10": r.getrandbits(32),
        "limit_w": (r.randrange(1, 300), r.randrange(1, 300)),
        "probe": True,                      # the actor has a sprite probe object at +0x174
        "probe_box": [r.randrange(0, 200), r.randrange(0, 200), r.randrange(201, 500), r.randrange(201, 500)],
        "a190": r.choice((0, r.randrange(1, 1 << 30))),
        "cycle": False,                     # "GAME_CYCLE100" is in the level's map
        "sound": False,                     # "GAME_PUBOUNCE1" is in the level's map
        "t_anim": False,                    # T[0x18c] points at an animation
        "t_sound": False,                   # T[0x188] points at a sound chain
        "t190": 0,
        "t194": r.randrange(0, 3),
        "t198": r.getrandbits(32),
        "t19c": r.randrange(1, 5000),
        "t184": r.randrange(0, 40),
        "t20": r.getrandbits(32),
        "t24": r.getrandbits(32),
        "t134": r.getrandbits(32),
        "ap_mode": "wait",
        "ap": [r.randrange(1, 1 << 20) for _ in range(8)],
        "time": r.randrange(0, 1 << 31),
        "step": r.randrange(1, 40),
        "trie": None,                       # None: no trie. Else dict key -> value
        "decoys": (),
        "separate_q": True,
        "separate_a8": True,
        "ids": None,
        "match": None,
        "handler_index": None,
        "sync_position": False,
        "physics": None,                    # (t40, t50, t58, t70) for the landing arithmetic
        "debug": True,
        "behaviours": [],                   # names ("LogicHit", "LogicAttack") found in the level's behaviour map
    }
    spec.update(override)
    return spec


def put_player(env, actor, mode, s, stored, ap):
    """Fill the animation player embedded at actor+0x188 so that stepping it takes a short path."""
    env.put(actor + 0x190, stored)
    env.put(actor + 0x194, ap[0], ap[1], ap[2], ap[3], ap[4], ap[5], ap[6])
    step = s["step"]
    held = stored or 0x1234
    if mode == "raw":
        pass
    elif mode == "none":
        env.put(actor + 0x190, 0)
    else:
        env.put(actor + 0x190, held)
        env.put(actor + 0x1A4, ap[1] | 1)
        if mode == "wait":                      # counter set, flag clear: just count down
            env.put(actor + 0x19C, ap[0] | 1)
            env.put(actor + 0x1A0, 0)
        elif mode == "short":                   # flag set, step smaller than the counter
            env.put(actor + 0x19C, step + 1 + (ap[0] & 0xFF))
            env.put(actor + 0x1A0, 1)
        elif mode == "long":                    # flag set, step larger than the counter
            env.put(actor + 0x19C, max(1, step - 1 - (ap[0] % step)) if step > 1 else 1)
            env.put(actor + 0x1A0, 1)
            if step == 1:
                env.put(actor + 0x19C, 1)
        elif mode == "equal":                   # flag set, step equal to the counter
            env.put(actor + 0x19C, step)
            env.put(actor + 0x1A0, 1)
        elif mode == "ready":                   # counter zero
            env.put(actor + 0x19C, 0)
            env.put(actor + 0x1A0, ap[4] & 1)
    env.put(actor + 0x1A8, ap[2], ap[3])


def build(env, s):
    """Create the actor, its data, the level and the player logic object. Returns the addresses."""
    noise = random.Random(s["seed"])
    tok = {}
    limit_w = s["limit_w"]

    world = env.object(0x80, "collision-world", fill=0)
    env.put(world + 0x64, limit_w[0], limit_w[1])

    entries = [("LogicHi", noise.getrandbits(32) | 1)]
    for key in s["behaviours"]:
        found = env.object(0x20, "behaviour", fill=0)
        env.put(found + 0x10, noise.randrange(1, 1 << 30))
        entries.append((key, found))
    entries.append(("LogicAttackX", noise.getrandbits(32) | 1))
    owner = string_map(env, entries)   # the level's behaviour map
    cycle_value = animation(env, noise.randrange(1, 1 << 16), noise.randrange(1, 9))
    sound_value = sound_chain(env)
    tok["cycle_value"] = cycle_value
    tok["sound_value"] = sound_value
    decoy_a = noise.randrange(1, 1 << 30)
    decoy_b = noise.randrange(1, 1 << 30)
    cycle_map = string_map(env, [("GAME_CYCLE10", decoy_a)] +
                           ([(KEY_CYCLE, cycle_value)] if s["cycle"] else []) +
                           [("GAME_CYCLE1000", decoy_b)])
    sound_map = string_map(env, [("GAME_PUBOUNCE", decoy_b)] +
                           ([(KEY_SOUND, sound_value)] if s["sound"] else []) +
                           [("game_pubounce1", decoy_a)])
    level = env.object(0x80, "level", fill=0)
    env.put(level + 0x14, owner)
    env.put(level + 0x24, world, sound_map, cycle_map)  # +0x24 world, +0x28 sound map, +0x2c cycle map


    data = env.object(0x180, "actor-data", fill=0)
    limits = s["limits"]
    env.put(data + 0x2C, limits[0])
    env.put(data + 0x34, limits[1])
    env.put(data + 0x30, limits[2])
    env.put(data + 0x38, limits[3])
    ring = s["ring"]
    for offset, value in zip((0xF0, 0xF8, 0xF4, 0xFC, 0x100, 0x108, 0x104, 0x10C), ring):
        env.put(data + offset, value)
    env.put(data + 0x10, s["b10"])
    env.put(data + 0x18, s["b18"])
    env.put(data + 0x1C, s["b1c"])
    env.put(data + 0x168, s["b168"])

    probe = 0
    if s["probe"]:
        probe = env.object(0x40, "probe", fill=0)
        box = s["probe_box"]
        env.put(probe + 0x18, box[0], box[1], box[2], box[3])

    actor = env.object(0x200, "actor", fill=0)
    flags = s["flags"] | (0x400000 if s["hit"] else 0)
    env.put(actor + 0x08, flags)
    env.put(actor + 0x0C, level)
    env.put(actor + 0x14, owner)
    env.put(actor + 0x4C, s["x"] & M, s["y"] & M)
    env.put(actor + 0x64, s["a64"])
    env.put(actor + 0x6C, data)
    env.put(actor + 0xCC, s["state"], s["a0d0"])
    env.put(actor + 0xFC, s["a0fc"], s["a100"])
    env.put(actor + 0x148, s["a148"], s["a14c"])
    env.put(actor + 0x164, s["a164"])
    env.put(actor + 0x170, s["a170"], probe)
    stored = animation(env, noise.randrange(1, 1 << 16), noise.randrange(1, 9)) if s["a190"] else 0
    ap = s["ap"]
    env.put(actor + 0x194, ap[0], ap[1], ap[2], ap[3], ap[4], ap[5], ap[6])
    tok["actor"], tok["data"], tok["level"], tok["probe"] = actor, data, level, probe

    # the animation player embedded at actor+0x188
    put_player(env, actor, s["ap_mode"], s, stored, ap)

    # other actor used for the T[0x12c] role
    if s["separate_q"]:
        q = env.object(0x200, "actor-q", fill=0)
        env.put(q + 0x40, noise.getrandbits(32))
        env.put(q + 0x44, noise.getrandbits(32), noise.getrandbits(32))
        env.put(q + 0x08, noise.getrandbits(32) | (3 if noise.getrandbits(1) else 0))
        ap_q = [noise.randrange(1, 1 << 20) for _ in range(8)]
        put_player(env, q, s["ap_mode"], s, noise.randrange(1, 1 << 30) if stored else 0, ap_q)
    else:
        q = actor
    tok["q"] = q
    if s["separate_a8"]:
        a8 = env.object(0x200, "actor-a8", fill=0)
        b8 = env.object(0x80, "actor-a8-data", fill=0)
        env.put(a8 + 0x6C, b8)
        env.put(b8 + 0x10, 0xDEAD)
    else:
        a8 = actor
        b8 = data
    tok["a8"], tok["b8"] = a8, b8

    # the player logic object
    logic = env.object(0x1A0, "player-logic", fill=0)
    for offset in range(0x28, 0xF0, 8):
        env.write(logic + offset, f64(noise.uniform(-20, 20)))
    env.put(logic + 0x08, a8)
    env.put(logic + 0x0C, actor)
    env.put(logic + 0x10, data)
    env.put(logic + 0x20, s["t20"], s["t24"])
    env.put(logic + 0xC8, 0)
    env.put(logic + 0x120, noise.getrandbits(32), noise.getrandbits(32))
    env.put(logic + 0x12C, q)
    env.put(logic + 0x134, s["t134"])
    env.put(logic + 0x184, s["t184"])
    env.put(logic + 0x188, sound_value if s["t_sound"] else 0)
    env.put(logic + 0x18C, cycle_value if s["t_anim"] else 0)
    env.put(logic + 0x190, s["t190"], s["t194"] & M, s["t198"], s["t19c"])
    if s["sync_position"]:
        env.write(logic + 0x68, f64(s["x"]))
        env.write(logic + 0x70, f64(s["y"]))
    if s["physics"] is not None:
        p40, p50, p58, p70 = s["physics"]
        env.write(logic + 0x40, f64(p40))
        env.write(logic + 0x50, f64(p50))
        env.write(logic + 0x58, f64(p58))
        env.write(logic + 0x70, f64(p70))
    tok["logic"] = logic

    # globals
    count = len(s["ids"]) if s["ids"] is not None else 0x42
    if 0 <= s["t184"] < count:
        handler = env.object(0x40, "state-handler", fill=0)
        marker = env.object(0x20, "state-marker", fill=0)

        def start(env, call, marker=marker, b8=b8, noise=s["seed"]):
            env.put(marker, *call.arguments, 0xBEEF0000 | (noise & 0xFFFF))
            env.put(b8 + 0x20, noise)
            return noise
        env.put(handler + 0x10, env.stub("state-start", "cdecl", 1, start))
        env.put(BEHAVIOUR_HANDLERS + 4 * s["t184"], handler)
    env.put(TIME, s["time"])
    env.put(ANIMATION_STEP, s["step"])
    env.put(DEFAULTS_READY, 1)
    env.put(DEBUG_ENABLED, 1 if s["debug"] else 0)
    if s["trie"] is not None:
        install_trie(env, s["trie"], s["decoys"])
    if s["ids"] is not None:
        for index, value in enumerate(s["ids"]):
            env.put(BEHAVIOUR_IDS + 4 * index, value)
            env.put(BEHAVIOUR_SPEED + 4 * index, (value * 7 + 3) & M)
            env.put(BEHAVIOUR_SLOPE + 4 * index, (value * 13 + 5) & M)
            env.put(BEHAVIOUR_FLAGS + 4 * index, (value * 11 + 9) & M)
        env.put(BEHAVIOUR_COUNT, len(s["ids"]))
    if s["match"] is not None:
        env.put(actor + 0x170, s["ids"][s["match"]])
    return tok


def case(label, function, s, receiver="logic", arguments=(), setup_extra=None):
    def setup(env):
        tok = build(env, s)
        if setup_extra:
            extra = setup_extra(env, tok)
            if extra:
                tok.update(extra)
        return tok
    return Case(label, function, setup,
                receiver=(lambda t: t[receiver]) if receiver else 0,
                arguments=tuple((lambda t, name=a: t[name]) if isinstance(a, str) else a for a in arguments))


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------

def cases(random_source):
    r = random_source

    # ---- 0x40f6a0: store a field, mark the owner changed only on a difference
    for old, new in ((0, 0), (5, 5), (5, 6), (0, 1), (0x7FFFFFFF, 0x80000000), (0xFFFFFFFF, 0), (3, 0xFFFFFFFF)):
        flags = r.getrandbits(32)
        def setup(env, old=old, flags=flags, noise=r.getrandbits(64)):
            obj = env.object(0x100, "owner", data=random.Random(noise).randbytes(0x100))
            env.put(obj + 8, flags)
            env.put(obj + 0x64, old)
            return {"obj": obj}
        yield Case(f"set field {old:#x}->{new:#x}", SET_FIELD, setup, receiver=lambda t: t["obj"], arguments=(new,))
    for _ in range(12):
        old, new = r.getrandbits(32), r.getrandbits(32)
        flags = r.getrandbits(32) & ~0x20000 if r.getrandbits(1) else r.getrandbits(32) | 0x20000
        def setup(env, old=old, flags=flags, noise=r.getrandbits(64)):
            obj = env.object(0x100, "owner", data=random.Random(noise).randbytes(0x100))
            env.put(obj + 8, flags)
            env.put(obj + 0x64, old)
            return {"obj": obj}
        yield Case(f"random field {old:#x}->{new:#x} flags {flags:#x}", SET_FIELD, setup,
                   receiver=lambda t: t["obj"], arguments=(new,))

    # ---- 0x40f6f0: reset the vectors
    for _ in range(4):
        def setup(env, noise=r.getrandbits(64)):
            obj = env.object(0x100, "vectors", data=random.Random(noise).randbytes(0x100))
            return {"obj": obj}
        yield Case("reset vectors", RESET_VECTORS, setup, receiver=lambda t: t["obj"])

    # ---- 0x40f760: bind a context
    for _ in range(5):
        def setup(env, value=r.getrandbits(32), noise=r.getrandbits(64)):
            ctx = env.object(0x40, "context", data=random.Random(noise).randbytes(0x40))
            actor = env.object(0x80, "actor", data=random.Random(noise + 1).randbytes(0x80))
            env.put(actor + 0x6C, value)
            return {"ctx": ctx, "actor": actor}
        yield Case("bind context", BIND_CONTEXT, setup, receiver=lambda t: t["ctx"], arguments=(lambda t: t["actor"],))

    # ---- 0x40ebe0: dispatch by id through the handler table
    for position, (low, count, stride) in enumerate(((0, 4, 4), (-3, 6, 8), (10, 1, 12), (100, 5, 16), (-1000, 7, 8))):
        for pick in sorted({0, count - 1, count // 2, r.randrange(0, count)}):
            argument = low + pick
            noise = r.getrandbits(32)

            def setup(env, low=low, count=count, stride=stride, pick=pick, noise=noise):
                table = env.object(count * stride + 8, "handler-table", fill=0)
                marker = env.object(0x40, "markers", fill=0)
                stubs = []
                for index in range(count):
                    def effect(env, call, index=index, noise=noise):
                        env.put(marker + 4 * index, 0xA0000000 | index, call.receiver)
                        return noise + index
                    stubs.append(env.stub(f"handler{index}", "thiscall", 0, effect))
                    env.put(table + index * stride, stubs[-1])
                    if stride > 4:
                        env.put(table + index * stride + 4, noise + index)
                env.put(HANDLER_TABLE, low & M, (low + count - 1) & M, table)
                env.put(HANDLER_TABLE + 0x10, stride)
                receiver = env.object(0x40, "receiver", data=random.Random(noise).randbytes(0x40))
                return {"receiver": receiver}
            yield Case(f"dispatch id {argument} of {low}..{low + count - 1}", DISPATCH_BY_ID, setup,
                       receiver=lambda t: t["receiver"], arguments=(argument & M,))

    # ---- 0x40efa0: enter the animation
    for variant in range(10):
        s = draw(r, t_anim=variant % 2 == 1, cycle=True,
                 trie={KEY_FALLING: r.randrange(1, 1 << 30), KEY_BOUNCE: r.randrange(1, 1 << 30),
                       KEY_DEAD: r.randrange(1, 1 << 30)} if variant % 5 != 4 else None,
                 decoys=((KEY_FALLING,) if variant % 5 == 3 else ()),
                 ap_mode=("none", "wait", "ready")[variant % 3])
        yield case(f"enter animation {variant}", ENTER_ANIMATION, s)
    for key in (KEY_BOUNCE, KEY_DEAD):
        s = draw(r, t_anim=True, trie={KEY_FALLING: 0, KEY_BOUNCE: 0x111, KEY_DEAD: 0x222})
        yield case(f"enter animation only {key} in trie", ENTER_ANIMATION, s)
    s = draw(r, t_anim=True, trie={KEY_FALLING: 0})
    yield case("enter animation: found value zero", ENTER_ANIMATION, s)

    # ---- 0x40f010 and 0x40f200: step the animation and test the landing conditions
    ids = lambda: r.sample(range(1, 1 << 30), 6)
    for fn, name in ((STEP_ANIMATION, "step"), (STEP_LANDED, "landed")):
        for mode in ("none", "wait", "short", "long", "equal", "ready"):
            s = draw(r, ap_mode=mode, a164=0x0100, state=1, debug=True, t_sound=True,
                     trie={KEY_BOUNCE: r.randrange(1, 1 << 30)}, t194=1)
            s["t19c"] = 10
            s["t198"] = (s["time"] - 20) & M
            yield case(f"{name} animation mode {mode}", fn, s)
        # the landing flag in the actor
        for flags in (0x0200, 0x0300, 0x0002, 0x0100, 0x01FF, 0xFFFFFDFF, 0x8000_0200):
            s = draw(r, ap_mode="long", a164=flags, state=1, t_sound=True,
                     trie={KEY_BOUNCE: r.randrange(1, 1 << 30)}, t194=1)
            s["t198"] = (s["time"] - 20) & M
            yield case(f"{name} actor flags {flags:#x}", fn, s)
        for index_pick in (0, 1, 7, 40, 65):
            s = draw(r, ap_mode="wait", a164=0x0200, state=r.choice((1, 7)))
            s["t184"] = index_pick
            s["t198"] = (s["time"] - 5000) & M
            yield case(f"{name} landing branch with state {index_pick}", fn, s)
        for index_pick in (-1, 66, 100, 0x7FFFFFFF):
            s = draw(r, ap_mode="wait", a164=0x0200, state=1)
            s["t184"] = index_pick & M
            s["t198"] = (s["time"] - 5000) & M
            yield case(f"{name} landing branch with out of range state {index_pick}", fn, s)

    # timing window of 0x40f010
    for delta, limit, seen in ((9, 10, 0), (10, 10, 0), (11, 10, 0), (10, 10, 1), (0, 5, 0), (-1, 5, 0),
                               (0x7FFFFFFF, 1, 0), (1, 0xFFFFFFFF, 0), (100, 0, 0), (100, 0, 7)):
        s = draw(r, ap_mode="wait", a164=0x0100, state=r.choice((1, 7)))
        s["t198"] = (s["time"] - delta) & M
        s["t19c"] = limit
        s["t190"] = seen
        s["ids"] = ids()
        s["match"] = r.randrange(0, 6)
        yield case(f"step timing delta {delta} limit {limit:#x} seen {seen}", STEP_ANIMATION, s)
    # the behaviour id lookup inside 0x40f010
    for count, match in ((6, 0), (6, 1), (6, 5), (6, None), (1, 0), (0, None), (66, 65), (66, None)):
        s = draw(r, ap_mode="wait", a164=0x0100, state=r.choice((1, 7)))
        s["t198"] = (s["time"] - 5000) & M
        s["t19c"] = 1
        s["t190"] = 0
        pool = r.sample(range(1, 1 << 30), max(count, 1) + 1)
        s["ids"] = pool[:count]
        s["match"] = match
        if match is None:
            s["a170"] = pool[-1]
        yield case(f"step behaviour lookup {count} entries match {match}", STEP_ANIMATION, s)
    # probe object absent
    s = draw(r, ap_mode="wait", a164=0x0100, state=7, probe=False)
    s["t198"] = (s["time"] - 5000) & M
    s["t19c"] = 1
    yield case("step without probe", STEP_ANIMATION, s)
    s = draw(r, ap_mode="wait", a164=0x0100, state=7, probe=True)
    s["t198"] = (s["time"] - 5000) & M
    s["t19c"] = 1
    s["ids"] = ids()
    s["match"] = 0
    s["a0d0"] = 1
    yield case("step behaviour zero keeps a flag", STEP_ANIMATION, s)

    # 0x40f200: counter boundary
    for counter in (-5, -1, 0, 1, 3, 4, 5, 0x7FFFFFFF, 0x80000000):
        s = draw(r, ap_mode="wait", a164=0x0100, state=r.choice((1, 7)), t194=counter, t_sound=True,
                 trie={KEY_BOUNCE: r.randrange(1, 1 << 30)})
        yield case(f"landed counter {counter}", STEP_LANDED, s)
    for state in (0, 1, 2, 7, 8, 0x10001, 0xFFFFFFFF):
        s = draw(r, ap_mode="ready", a164=0x0100, state=state, t_sound=True,
                 trie={KEY_BOUNCE: r.randrange(1, 1 << 30)}, t194=0)
        yield case(f"landed actor state {state:#x}", STEP_LANDED, s)

    # ---- 0x40f0e0: the landing arithmetic
    scenarios = [
        # (t40, t50, t58, t70)
        (0.0, 3.5, 4.0, 9.0),
        (-0.0, 3.5, -4.0, 9.0),
        (1.0, 3.5, 4.0, 9.0),
        (-1.0, 3.5, 4.0, 9.0),
        (2.0, 3.5, 4.0, 2.0),
        (8.0, 3.5, 4.0, 2.0),
        (8.0, 3.5, -4.0, 2.0),
        (100.0, 1.5, -3.0, 5.0),
        (-100.0, 1.5, 0.0, 5.0),
        (-100.0, 1.5, -0.0, 5.0),
        (-2.0e6, 7.0, 3000.0, 1.0),
        (-2.0e6, 7.0, -3000.0, 1.0),
        (0.5, 0.25, 1500.0, 10.0),
        (-1.0e7, 1.0, 40.0, 0.0),
        (float("nan"), 2.0, 1.0, 3.0),
        (2.0, 2.0, float("nan"), 3.0),
        (-3.0, 2.0, 1.0, 1e300),
    ]
    for _ in range(14):
        scenarios.append((r.uniform(-60, 60), r.uniform(-9, 9), r.uniform(-60, 60), r.uniform(-30, 30)))
    for index, physics in enumerate(scenarios):
        s = draw(r, physics=physics, trie={KEY_BOUNCE: r.randrange(1, 1 << 30)}, t_sound=index % 3 != 0,
                 debug=index % 4 != 1, t194=r.randrange(0, 100))
        yield case(f"landing arithmetic {index}", LAND, s)
    for key, wanted in ((None, "no trie"), ({}, "trie without the key"), ({KEY_BOUNCE: 0}, "zero value")):
        s = draw(r, physics=(3.0, 2.0, -1.0, 4.0), trie=key, t_sound=True)
        yield case(f"landing trie: {wanted}", LAND, s)
    s = draw(r, physics=(3.0, 2.0, -1.0, 4.0), trie={KEY_BOUNCE: 0x55}, decoys=(KEY_BOUNCE,), t_sound=True)
    yield case("landing trie: mismatching leaf", LAND, s)
    s = draw(r, physics=(3.0, 2.0, -1.0, 4.0), trie={KEY_BOUNCE: 0x56, KEY_DEAD: 0x57, KEY_FALLING: 0x58}, t_sound=True)
    yield case("landing trie: all three names present", LAND, s)

    # ---- 0x40f2a0: update with the hit flag and the state name
    names_equal = KEY_DEAD
    for hit in (False, True):
        for low, count, stride, pick in ((0, 4, 8, 2), (-4, 11, 8, 2), (-4, 11, 12, 0), (-4, 11, 8, 10),
                                         (5, 3, 16, 1), (0, 1, 4, 0)):
            for equal in (False, True):
                if not hit and (low, pick) != (0, 2) and not equal:
                    continue
                s = draw(r, hit=hit, sync_position=True, trie={KEY_DEAD: r.randrange(1, 1 << 30)},
                         state=7)
                index = low + pick
                s["b1c"] = index & M
                names = []
                for position in range(count):
                    if position == pick:
                        names.append(names_equal if equal else r.choice(
                            ("LS_DEAF", "LS_DEA", "LS_DEADX", "ls_dead", "", "LS_DEAD ", "XS_DEAD", "LS_FALLING")))
                    else:
                        names.append(r.choice((KEY_DEAD, "LS_OTHER", KEY_BOUNCE, "")))

                def extra(env, tok, low=low, names=names, stride=stride):
                    name_table(env, low, names, stride)
                label = f"update hit={hit} table {low}+{count} index {index} equal={equal}"
                yield case(label, UPDATE, s, setup_extra=extra)
    # the table boundary names
    for index_offset in (0, 10):
        s = draw(r, hit=True, sync_position=True, trie={KEY_DEAD: 7})
        s["b1c"] = (-4 + index_offset) & M
        def extra(env, tok):
            name_table(env, -4, ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"], 8)
        yield case(f"update table edge {index_offset}", UPDATE, s, setup_extra=extra)
    for state_hit in (False, True):
        s = draw(r, hit=state_hit, sync_position=True, trie=None)
        s["b1c"] = 1
        def extra(env, tok):
            name_table(env, 0, ["LS_X", "LS_Y", "LS_Z"], 8)
        yield case(f"update without trie hit={state_hit}", UPDATE, s, setup_extra=extra)

    # ---- 0x40ebe0 and 0x40f2a0: the table grows (realloc fixture), the empty slot reaches typeid
    yield from growth_cases(r)

    # ---- 0x40e750: the constructor
    ctor_variants = []
    for pattern in range(16):
        ctor_variants.append(dict(limits=[(i + 1) * 37 if pattern >> i & 1 else 0 for i in range(4)]))
    for pattern in range(9):
        ring = [(k + 1) * 11 if (pattern >> k) & 1 else 0 for k in range(8)]
        ctor_variants.append(dict(ring=ring, a100=0 if pattern % 2 else 5))
    for number, extra_spec in enumerate(ctor_variants):
        s = draw(r, state=r.choice((0, 3, 7)), separate_q=False, separate_a8=False, ap_mode="raw",
                 cycle=number % 2 == 0, sound=number % 3 != 1, a190=(0, 0, 0x4321)[number % 3],
                 trie=None if number % 4 == 3 else {KEY_FALLING: r.randrange(1, 1 << 30), KEY_BOUNCE: r.randrange(1, 1 << 30),
                                                    KEY_DEAD: r.randrange(1, 1 << 30)},
                 decoys=(KEY_FALLING,) if number % 4 == 2 else (),
                 **extra_spec)
        if number % 5 == 0:
            s["a64"] = 0
        yield ctor_case(f"construct {number}", s)
    for _ in range(8):
        s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw", cycle=r.getrandbits(1) == 1, sound=r.getrandbits(1) == 1,
                 state=r.choice((0, 7, r.getrandbits(32))))
        yield ctor_case("construct random", s)
    s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw", cycle=True, sound=True, a190=0, a64=0)
    yield ctor_case("construct with a map hit and no stored animation", s)
    for number, (hit, attack, parent) in enumerate(((None, None, False), ("fixture", None, True), ("fixture", "fixture", False),
                                                    (None, "fixture", True), ("new", "new", False), ("new", "fixture", True),
                                                    ("fixture", "new", True), (None, "new", False))):
        names = [name for name, mode in (("LogicHit", hit), ("LogicAttack", attack)) if mode]
        for repeat in range(2):
            s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw", behaviours=names,
                     cycle=repeat == 0, sound=repeat == 1, a190=(0, 0x2222)[repeat],
                     trie={KEY_FALLING: r.randrange(1, 1 << 30)})
            yield ctor_case(f"construct with links hit={hit} attack={attack} parent={parent} #{repeat}", s,
                            hit=hit, attack=attack, parent=parent)
    s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw", cycle=True, sound=True, a190=0x99, a64=2000)
    yield ctor_case("construct with a stored animation", s)

    # ---- 0x40e690: begin the state
    for state in (0x1D, 0x1E, 0x3E8, 1, 5, 0x1C, 0x1F, 0x3E7, 0x3E9, 0x7FFFFFFF, 0xFFFFFFFF):
        for kind in range(2 if state not in (0x1D, 0x1E, 0x3E8) else 1):
            s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw")
            s["b1c"] = state
            low, count, stride, pick = ((-2, 7, 8, 3), (0, 3, 12, 2))[kind]
            yield state_case(f"begin state {state:#x}", s, state, low, count, stride, pick)
    s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw", cycle=True, sound=True,
             trie={KEY_FALLING: r.randrange(1, 1 << 30)})
    s["b1c"] = 0
    yield state_case("begin state zero", s, 0, 0, 1, 4, 0)
    for number in range(3):
        s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw", cycle=number != 1, sound=number != 0,
                 a190=(0, 0x31, 0)[number], limits=[0, 5, 0, 9] if number == 2 else [4, 0, 6, 0],
                 trie=None if number == 0 else {KEY_FALLING: r.randrange(1, 1 << 30)})
        s["b1c"] = 0
        yield state_case(f"begin state zero variant {number}", s, 0, 0, 1, 4, 0)
    for index in range(1, 4):
        s = draw(r, separate_q=False, separate_a8=False, ap_mode="raw")
        s["b1c"] = r.choice((2, 0x1B, 0x20, 0x500))
        low, count, stride, pick = ((-2, 5, 8, 0), (-2, 5, 8, 4), (3, 1, 16, 0))[index - 1]
        yield state_case("begin default state at the table edge", s, s["b1c"], low, count, stride, pick)


def link_object(env, actor, offset, mode, logic, parent):
    """The object an actor already holds at +0x70 (hit) or +0x78 (attack): virtual methods are stubs."""
    if mode != "fixture":
        env.put(actor + offset, 0)
        return
    vtable = env.object(0x40, "link-vtable", fill=0)
    link = env.object(0x40, "link", fill=0)
    env.put(link, vtable)

    def reset(env, call):
        return 0

    def adopt(env, call):
        if parent:
            env.put(logic + 4, parent)    # the constructor re-reads this field afterwards
        return 1
    env.put(vtable + 0x1C, env.stub("link-reset", "thiscall", 0, reset))
    env.put(vtable + 0x24, env.stub("link-adopt", "thiscall", 2, adopt))
    env.put(actor + offset, link)


def ctor_case(label, s, hit=None, attack=None, parent=False):
    def setup(env):
        tok = build(env, s)
        noise = random.Random(s["seed"] ^ 0x5A5A)
        env.write(tok["logic"], noise.randbytes(0x1A0))
        owner_parent = 0
        if parent:
            owner_parent = env.object(0x40, "parent", fill=0)
            parent_level = env.object(0x80, "parent-level", fill=0)
            env.put(parent_level + 0x64, noise.randrange(0, 1 << 20))
            env.put(owner_parent + 0x0C, parent_level)
        link_object(env, tok["actor"], 0x70, hit, tok["logic"], owner_parent)
        link_object(env, tok["actor"], 0x78, attack, tok["logic"], owner_parent)
        return tok
    return Case(label, CONSTRUCT, setup, receiver=lambda t: t["logic"], arguments=(lambda t: t["actor"],))


def state_case(label, s, state, low, count, stride, pick):
    """0x40e690 on an actor in the given behaviour state."""
    def setup(env):
        tok = build(env, s)
        data = tok["data"]
        env.put(data + 0x1C, state)
        noise = random.Random(s["seed"] ^ 0xA5A5)
        # the object that already runs the state: virtual methods are stubs
        vtable = env.object(0x40, "behaviour-vtable", fill=0)
        running = env.object(0x40, "running-behaviour", fill=0)
        index_holder = env.object(0x40, "behaviour-index", fill=0)
        env.put(running, vtable)
        env.put(running + 0x10, index_holder)
        index = low + pick
        env.put(index_holder + 0x1C, index & M)
        marker = env.object(0x40, "markers", fill=0)

        def make(slot, count_args):
            def effect(env, call, slot=slot):
                env.put(marker + 4 * slot, 0xC0DE0000 | slot, call.receiver, *(call.arguments or ()))
                return 0x1000 + slot
            return env.stub(f"behaviour-slot{slot}", "thiscall", count_args, effect)
        env.put(vtable + 4, make(1, 1))
        env.put(vtable + 8, make(2, 1))
        env.put(vtable + 0xC, make(3, 1))
        env.put(vtable + 0x1C, make(7, 0))
        env.put(vtable + 0x20, make(8, 0))
        if state != 0:
            env.put(data + 0x18, running)
        name_table(env, low, [f"STATE_{k}" for k in range(count)], stride)
        tok["running"] = running
        return tok
    return Case(label, BEGIN_STATE, setup, receiver=0, arguments=(lambda t: t["actor"],))


REAL_VTABLE = 0x50B2A4  # a vtable of the image: typeid reads its type information word


def handler_table(env, low, count, stride, noise, filled=True):
    """The handler table of 0x40ebe0 with `count` entries from `low`; returns the receiver and a marker area."""
    table = env.object(count * stride + 8, "handler-table", fill=0)
    marker = env.object(0x40, "markers", fill=0)
    for index in range(count):
        if filled:
            def effect(env, call, index=index, noise=noise):
                env.put(marker + 4 * index, 0xB0000000 | index, call.receiver)
                return noise + index
            env.put(table + index * stride, env.stub(f"handler{index}", "thiscall", 0, effect))
        else:
            env.put(table + index * stride, 0)
        if stride > 4:
            env.put(table + index * stride + 4, noise + index)
    env.put(HANDLER_TABLE, low & M, (low + count - 1) & M, table)
    env.put(HANDLER_TABLE + 0x10, stride)
    receiver = env.object(0x40, "receiver", data=random.Random(noise).randbytes(0x40))
    env.put(receiver, REAL_VTABLE)
    return {"receiver": receiver, "table": table, "marker": marker}


def growth_cases(r):
    # empty slot inside the table: no growth, typeid on the receiver
    for low, count, stride, pick in ((0, 3, 4, 1), (-5, 4, 8, 3), (7, 2, 12, 0)):
        noise = r.getrandbits(32)
        def setup(env, low=low, count=count, stride=stride, pick=pick, noise=noise):
            tok = handler_table(env, low, count, stride, noise)
            env.put(tok["table"] + pick * stride, 0)
            return tok
        yield Case(f"dispatch empty slot {low + pick} in {low}..{low + count - 1}", DISPATCH_BY_ID, setup,
                   receiver=lambda t: t["receiver"], arguments=((low + pick) & M,))
    # id outside the table: it grows (up or down) and the new slot is empty
    for low, count, stride, argument in ((0, 3, 4, -1), (0, 3, 4, 5), (-5, 4, 8, -9), (-5, 4, 8, 3),
                                         (10, 1, 12, 8), (10, 1, 16, 15), (100, 5, 8, 140), (100, 5, 4, 63)):
        noise = r.getrandbits(32)
        def setup(env, low=low, count=count, stride=stride, noise=noise):
            return handler_table(env, low, count, stride, noise)
        yield Case(f"dispatch grow id {argument} of {low}..{low + count - 1} stride {stride}", DISPATCH_BY_ID, setup,
                   receiver=lambda t: t["receiver"], arguments=(argument & M,))
    for low, count, stride, argument in ((-2, 3, 8, -0x30), (5, 3, 8, 0x200), (0, 2, 4, 0x7FFF)):
        noise = r.getrandbits(32)
        def setup(env, low=low, count=count, stride=stride, noise=noise):
            return handler_table(env, low, count, stride, noise)
        yield Case(f"dispatch grow far id {argument}", DISPATCH_BY_ID, setup,
                   receiver=lambda t: t["receiver"], arguments=(argument & M,))

    # ---- 0x40f2a0 growing the name table
    for hit_low, count, stride, delta, up in ((0, 3, 4, 3, True), (0, 3, 4, 1, True), (4, 2, 8, 1, True),
                                              (4, 2, 16, 1, True), (-4, 5, 8, 3, False), (6, 3, 12, 1, False),
                                              (6, 3, 4, 4, False), (-4, 5, 16, 2, False), (0, 4, 8, 1, False)):
        s = draw(r, hit=True, sync_position=True, trie={KEY_DEAD: r.randrange(1, 1 << 30)})
        index = (hit_low + count - 1 + delta) if up else (hit_low - delta)
        s["b1c"] = index & M
        names = [r.choice((KEY_DEAD, "LS_OTHER", KEY_BOUNCE, "LS_DEAF")) for _ in range(count)]
        def extra(env, tok, low=hit_low, names=names, stride=stride):
            name_table(env, low, names, stride)
        yield case(f"update grow {'up' if up else 'down'} table {hit_low}+{count} stride {stride} to {index}",
                   UPDATE, s, setup_extra=extra)
