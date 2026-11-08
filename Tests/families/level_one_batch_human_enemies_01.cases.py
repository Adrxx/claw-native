"""Cases for level_one_batch_human_enemies_01: Level 1 shared human enemy states, batch 1.

Every case builds one enemy object (O) with all fields the owned functions read filled in, a body
object (X) with its animation record at X+0x188, a controller (C), a string table, a name trie and
stand-in virtual methods. Structure (which branch is taken) is enumerated; field values come from a
per-case generator seeded from the random source.
"""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

RAND = 0x4A3050
TABLE = 0x537698        # string table record
TRIE = 0x537668         # name trie record
G_TIME = 0x537210
G_DELTA = 0x5430C4
G_FLAG = 0x532C0C
G_ARG = 0x532C10
G_EVENT = 0x534EAC
G_PLAYER = 0x537E88
G_MBCS = 0x540E00

F_HOME, F_PAUSE, F_WAIT, F_TURN, F_REST, F_TRACK = 0x44DA20, 0x44DD30, 0x44DE50, 0x44E510, 0x44EA10, 0x44EA60
F_FAST, F_SEEK, F_SCAN, F_DECAY_A, F_DECAY_B, F_IDLE = 0x44EBB0, 0x44EC80, 0x44F290, 0x44F490, 0x44F660, 0x44F800

INT_MIN = 0x80000000
NEAR_MISS_HOME = ("LS_HOMF", "LS_HOM", "LS_HOME2", "ls_home", "LS_HOME ", "", "LS_HOMD", "XS_HOME")
NEAR_MISS_PAUSE = ("LS_PAUSF", "LS_PAUS", "LS_PAUSE2", "ls_pause", "", "LS_PAUSD", "LS_HOME", "XS_PAUSE")


def dbl(value):
    return struct.unpack("<II", struct.pack("<d", value))


NAN = float("nan")


def cstring(env, text):
    return env.object(len(text) + 1, "string", data=text.encode() + b"\0")


def noise(r, size):
    return bytes(r.getrandbits(8) for _ in range(size))


def sentinel_pairs(r, mask):
    """Six values for X+0x118/0x120, 0x128/0x130, 0x138/0x140 with INT_MIN leading the pairs in mask."""
    values = []
    for index in range(3):
        first = INT_MIN if mask >> index & 1 else r.choice((-1, 1)) * r.randrange(1, 9000)
        values += [first, r.choice((-1, 1)) * r.randrange(1, 9000)]
    return values


# ---- sub-structures --------------------------------------------------------------------------------

def sequence_object(env, r):
    """A frame sequence the animation can restart: one benign frame, unique value in frame+0x1c."""
    frame = env.object(0x40, "frame", data=noise(r, 0x40))
    env.put(frame + 0x04, r.randrange(8))              # flags: bit 2 and bit 0 both vary
    env.put(frame + 0x08, 0)                           # no step kind
    env.put(frame + 0x0C, 6)                           # no end-of-frame action
    env.put(frame + 0x10, r.randrange(4))              # position mode
    env.put(frame + 0x18, r.randrange(4))              # frame duration
    env.put(frame + 0x1C, r.randrange(1, 1 << 24))     # unique marker copied into the record
    env.put(frame + 0x20, r.randrange(-300, 300), r.randrange(-300, 300))
    env.put(frame + 0x2C, 0)                           # no sound or effect object
    frames = env.object(4, "frames", words=[frame])
    seq = env.object(0x20, "sequence", data=noise(r, 0x20))
    env.put(seq + 0x0C, frames)
    env.put(seq + 0x10, 1)
    return seq


def string_table(env, r, text, other, grow=0, stride=None):
    """Fill the global string table so the entry for the returned id holds `text`, its neighbours `other`.

    With grow > 0 the id lies grow entries past the end, so the table grows through realloc and the
    new-entry loop runs; that only leaves a readable first word with stride 4 (or grow 1)."""
    low = r.randrange(0, 30)
    high = low + r.randrange(4, 12)
    ident = high + grow if grow else r.randrange(low + 1, high)
    stride = stride or r.choice((8, 12, 16))
    base = env.object(stride * (high - low + 1), "string-entries", data=noise(r, stride * (high - low + 1)))
    for index in range(low, high + 1):
        env.put(base + (index - low) * stride, cstring(env, text if index == ident else other))
    env.put(TABLE + 0x08, low, high)
    env.put(TABLE + 0x10, base)
    env.put(TABLE + 0x18, stride)
    return ident


def name_trie(env, r, mode):
    """Binary trie of three names. mode: ok, wrong-key (leaf key differs), empty (no root)."""
    values = [r.randrange(1, 1 << 28) for _ in range(3)]
    keys = ["LS_FASTADVANCE", "LS_ADVANCE", "LS_PACING"]
    if mode == "wrong-key":
        keys = [key + "X" for key in keys]

    def leaf(key, value):
        node = env.object(0x14, "leaf", data=noise(r, 0x14))
        env.put(node + 0x08, 0)
        env.put(node + 0x0C, cstring(env, key))
        env.put(node + 0x10, value)
        return node

    fast, advance, pacing = (leaf(k, v) for k, v in zip(keys, values))
    inner = env.object(0x14, "node", data=noise(r, 0x14))
    env.put(inner, advance, pacing)
    env.put(inner + 0x08, 28)
    root = env.object(0x14, "root", data=noise(r, 0x14))
    env.put(root, inner, fast)
    env.put(root + 0x08, 26)
    env.put(TRIE + 0x18, 0 if mode == "empty" else root)
    return values


def animation(env, r, x, owner, mode, c14=None, c1c=None, delta=None):
    """Configure the animation record at x+0x188. Returns the delta stored in the global."""
    base = x + 0x188
    env.put(base + 0x04, owner)
    env.put(base + 0x28, 0x3F800000)
    delta = r.randrange(1, 4) if delta is None else delta
    frame = env.object(0x40, "frame", data=noise(r, 0x40))
    env.put(frame + 0x04, r.randrange(8))
    env.put(frame + 0x08, 0)
    env.put(frame + 0x0C, 6)
    env.put(frame + 0x10, r.randrange(4))
    env.put(frame + 0x18, r.randrange(4))
    env.put(frame + 0x1C, r.randrange(1, 1 << 24))
    env.put(frame + 0x20, r.randrange(-300, 300), r.randrange(-300, 300))
    env.put(frame + 0x2C, 0)
    env.put(base + 0x0C, frame)
    env.put(base + 0x10, r.randrange(0, 6))
    env.put(base + 0x20, r.randrange(1, 1 << 20))
    env.put(base + 0x24, r.randrange(1, 1 << 20))
    if mode == "idle":                  # no sequence loaded: the update returns at once
        env.put(base + 0x08, 0)
        env.put(base + 0x14, r.randrange(0, 5) if c14 is None else c14)
        env.put(base + 0x18, r.randrange(2))
        env.put(base + 0x1C, r.randrange(0, 3) if c1c is None else c1c)
    elif mode == "tick":                # counter decrements by one
        env.put(base + 0x08, owner)
        env.put(base + 0x14, r.randrange(2, 9) if c14 is None else c14)
        env.put(base + 0x18, 0)
        env.put(base + 0x1C, r.randrange(1, 3) if c1c is None else c1c)
    elif mode == "tick-delta":          # counter decrements by the global delta
        env.put(base + 0x08, owner)
        env.put(base + 0x14, delta + r.randrange(1, 9) if c14 is None else c14)
        env.put(base + 0x18, 1)
        env.put(base + 0x1C, r.randrange(1, 3) if c1c is None else c1c)
    elif mode == "expire":              # counter reaches zero on this update
        env.put(base + 0x08, owner)
        env.put(base + 0x14, 1)
        env.put(base + 0x18, 0)
        env.put(base + 0x1C, r.randrange(1, 3) if c1c is None else c1c)
    elif mode == "heavy":               # counter already zero: advances to the benign frame
        env.put(base + 0x08, owner)
        env.put(base + 0x14, 0)
        env.put(base + 0x18, r.randrange(2))
        env.put(base + 0x1C, 0)
    env.put(G_DELTA, delta)
    return delta


def line_of_sight(env, r, kind, direction):
    """Tile layer for the sight test. Returns (layer, actor_x, actor_y, player_x)."""
    cells = env.object(16 * 4 * 4 + 32, "cells")
    rows = env.object(4 * 4, "row-offsets")
    for row in range(4):
        env.put(rows + row * 4, row * 16 + 3)
    classes = []
    effects = (returns(0), returns(1),
               lambda env, call: 1 if call.arguments[0] >= 16 else 0,
               lambda env, call: 1 if call.arguments[1] >= 16 else 0)
    for index, effect in enumerate(effects):
        method = env.stub(f"tile-class-{index}", "thiscall", 2, effect)
        table = env.object(0x24, "tile-vtable", data=noise(r, 0x24))
        env.put(table + 0x20, method)
        classes.append(env.object(8, "tile-class", words=[table]))
    class_table = env.object(16, "tile-classes", words=classes)
    ty = r.randrange(0, 4)
    first, second = (r.randrange(1, 7), r.randrange(9, 15))
    start_col, end_col = (first, second) if direction == "right" else (second, first)
    lo, hi = min(start_col, end_col), max(start_col, end_col)

    def cell(column, row, cls):
        env.put(cells + (row * 16 + 3 + column) * 4, (r.randrange(1, 0x7FFF) << 16) | cls if cls is not None else 0xFFFFFFFF)

    for row in range(4):
        for column in range(16):
            cell(column, row, r.choice((0, 0, None)) if row == ty else r.choice((0, 1, 2, 3, None)))
    mid = r.randrange(lo + 1, hi)
    if kind == "wall-mid":
        cell(mid, ty, 1)
    elif kind == "wall-target":
        cell(end_col, ty, 1)
    elif kind == "wall-start":
        cell(start_col, ty, 1)
    elif kind == "half-x":
        cell(mid, ty, 2)
    elif kind == "half-y":
        cell(mid, ty, 3)
    elif kind == "gap":
        cell(mid, ty, None)
    layer = env.object(0x70, "tile-layer", data=noise(r, 0x70))
    info = env.object(0x98, "map-info", data=noise(r, 0x98))
    env.put(layer + 0x4C, class_table)
    env.put(layer + 0x5C, info)
    env.put(info + 0x20, cells)
    env.put(info + 0x24, rows)
    env.put(info + 0x30, 16 * 32, 4 * 32)
    env.put(info + 0x8C, 5, 5)
    actor_x = start_col * 32 + r.randrange(0, 32)
    player_x = end_col * 32 + r.randrange(0, 32)
    actor_y = ty * 32 + r.randrange(0, 32)
    return layer, actor_x, actor_y, player_x


# ---- the whole world -------------------------------------------------------------------------------

def world(env, r, o):
    """Build every object a case needs. Options in `o` select the branch; unspecified fields are drawn from r."""
    env.put(G_MBCS, 0)
    env.override(RAND, sequence(*o.get("rand", (r.randrange(32768), r.randrange(32768), r.randrange(32768)))))
    # virtual methods
    slots = {}
    vtable = env.object(0xA0, "vtable", data=noise(r, 0xA0))
    for slot in (0x44, 0x48, 0x58, 0x78, 0x90):
        arguments = 1 if slot == 0x90 else 0
        slots[slot] = env.stub(f"slot-{slot:#x}", "thiscall", arguments, returns(r.randrange(1 << 16)))
        env.put(vtable + slot, slots[slot])
    # controller and name record
    controller = env.object(0xD8, "controller", data=noise(r, 0xD8))
    env.put(controller + 0xCC, o.get("cc", 1))
    name = env.object(0x40, "name-record", data=noise(r, 0x40))
    # string table
    kind = o.get("name", "ok")
    if "pause" in o:
        text = "LS_PAUSE" if o["pause"] else NEAR_MISS_PAUSE[o.get("variant", 0) % len(NEAR_MISS_PAUSE)]
        other = NEAR_MISS_PAUSE[(o.get("variant", 0) + 3) % 5] if o["pause"] else "LS_PAUSE"
    else:
        match = o.get("home", True)
        text = "LS_HOME" if match else NEAR_MISS_HOME[o.get("variant", 0) % len(NEAR_MISS_HOME)]
        other = NEAR_MISS_HOME[(o.get("variant", 0) + 3) % 6] if match else "LS_HOME"
    ident = string_table(env, r, text, other, o.get("grow", 0), o.get("stride"))
    trie_values = name_trie(env, r, o.get("trie", "ok"))
    # body, its owner and animation record
    owner = env.object(0x100, "anim-owner", data=noise(r, 0x100))
    x = env.object(0x1C0, "body", data=noise(r, 0x1C0))
    flag2 = o.get("flag2", r.randrange(2))
    env.put(x + 0x08, (r.getrandbits(32) & ~0x10004) | (0x10004 if o.get("x8full") else 0) | (0x4 if o.get("x8bit4") else 0))
    env.put(x + 0x40, (r.getrandbits(32) & ~2) | (2 if flag2 else 0))
    pairs = sentinel_pairs(r, o.get("sent", r.randrange(8)))
    env.put(x + 0x118, pairs[0]); env.put(x + 0x120, pairs[1])
    env.put(x + 0x128, pairs[2]); env.put(x + 0x130, pairs[3])
    env.put(x + 0x138, pairs[4]); env.put(x + 0x140, pairs[5])
    env.put(x + 0x190, r.randrange(1, 1 << 24))
    delta = animation(env, r, x, owner, o.get("anim", "idle"), o.get("c14"), o.get("c1c"))
    # the enemy object
    obj = env.object(0x440, "enemy", data=noise(r, 0x440))
    env.put(obj, vtable)
    env.put(obj + 0x0C, controller)
    env.put(obj + 0x10, name)
    if "pause" in o:                        # 44dd30 reads the id from the enemy; 44da20 from the name record
        env.put(name + 0x1C, r.randrange(1 << 20))
        env.put(obj + 0x24, ident)
    else:
        env.put(name + 0x1C, ident)
        env.put(obj + 0x24, r.randrange(1 << 20))
    env.put(obj + 0x20, r.randrange(1 << 20))
    env.put(obj + 0x12C, x)
    env.put(obj + 0x134, r.randrange(1 << 20))
    pairs = sentinel_pairs(r, 0)
    env.put(obj + 0x138, pairs[4]); env.put(obj + 0x140, pairs[5])
    spawn_k = o.get("spawn_k", r.choice((0, -4)))
    spawn_pointer = x if (spawn_k <= 0 and o.get("spawn_ptr")) else 0           # 42df90: never reach the spawn objects
    if o.get("spawn_obj"):                  # a handler object whose inner object has no handler word
        inner = env.object(0x90, "spawn-inner", data=noise(r, 0x90))
        env.put(inner + 0x78, 0)
        middle = env.object(0x20, "spawn-middle", data=noise(r, 0x20))
        env.put(middle + 0x10, inner)
        spawn_pointer = env.object(0x20, "spawn-handler", data=noise(r, 0x20))
        env.put(spawn_pointer + 0x10, middle)
    env.put(obj + 0x148, spawn_pointer)
    env.put(obj + 0x14C, o.get("spawn_n", r.choice((0, -2))))
    env.put(obj + 0x150, spawn_k)
    env.put(obj + 0x184, o.get("kind", r.randrange(7)) )
    env.put(obj + 0x18C, o.get("face", r.choice((2, 3, 0, 1))))
    env.put(obj + 0x2E4, o.get("thr", r.randrange(1, 400)))
    for offset in (0x308, 0x30C, 0x344, 0x34C):
        env.put(obj + offset, 0 if offset in o.get("no_seq", ()) else sequence_object(env, r))
    env.put(obj + 0x400, r.choice((-1, 1)) * r.randrange(1, 900))
    env.put(obj + 0x404, r.choice((-1, 1)) * r.randrange(1, 900))
    # bit set consulted by 44edd0 (bit 2) and 44f290 (bit 8)
    size = o.get("bits_size", r.choice((0, 2, 3, 9, 33)))
    word = o.get("bits", r.getrandbits(32))
    env.put(obj + 0x2FC, size)
    if size > 0x20:
        env.put(obj + 0x300, env.object(8, "bit-words", words=[word, r.getrandbits(32)]))
    else:
        env.put(obj + 0x300, word)
    # doubles at 0x50 (velocity), 0x68, 0x80, 0x98
    d1 = float(r.randrange(-500, 500)) + 0.25
    d2, d3 = d1 + r.choice((1.0, -3.5, 40.0)), d1 + r.choice((2.0, -7.5, 9.0))
    eq = o.get("eq", ())
    if "12" in eq:
        d2 = d1
    if "13" in eq:
        d3 = d1
    if "nan1" in eq:
        d1 = NAN
    if "nan2" in eq:
        d2 = NAN
    if "zero" in eq:
        d1, d2 = 0.0, -0.0
    env.put(obj + 0x68, *dbl(d1))
    env.put(obj + 0x80, *dbl(d2))
    env.put(obj + 0x98, *dbl(d3))
    velocity = o.get("velocity")
    if velocity is None:
        velocity = float(r.randrange(-90, 90)) + 0.5
    if isinstance(velocity, tuple):
        env.put(obj + 0x50, *velocity)
    else:
        env.put(obj + 0x50, *dbl(velocity))
    # timers: (uint)b <= (uint)(now - a)
    for a_offset, b_offset in ((0x428, 0x42C), (0x438, 0x43C)):
        a, b = r.randrange(1 << 20), r.randrange(1, 1 << 12)
        mode = o.get("time", "ge")
        elapsed = {"ge": b + r.randrange(1, 500), "eq": b, "lt": b - 1, "wrap": -r.randrange(1, 900), "huge": 0}[mode]
        if mode == "huge":
            b = INT_MIN + r.randrange(1 << 20)
            elapsed = 77
        env.put(obj + a_offset, a)
        env.put(obj + b_offset, b)
        env.put(G_TIME, (a + elapsed) & 0xFFFFFFFF)
    # sound objects on the 4b45f0 path (early exit: its inner object has no handler word)
    for offset in (0x38C, 0x3A4):
        if o.get("sound", {}).get(offset):
            inner = env.object(0x90, "sound-inner", data=noise(r, 0x90))
            env.put(inner + 0x78, 0)
            middle = env.object(0x20, "sound-middle", data=noise(r, 0x20))
            env.put(middle + 0x10, inner)
            outer = env.object(0x20, "sound", data=noise(r, 0x20))
            env.put(outer + 0x10, middle)
            env.put(obj + offset, outer)
        else:
            env.put(obj + offset, 0)
    env.put(G_FLAG, o.get("gflag", 0))
    env.put(G_ARG, r.randrange(1 << 16))
    # line of sight
    sight = o.get("sight", "clear")
    layer, ax, ay, px = line_of_sight(env, r, sight, o.get("direction", "right"))
    link = env.object(0x20, "link", data=noise(r, 0x20))
    middle = env.object(0x30, "link2", data=noise(r, 0x30))
    env.put(obj + 0x190, link)
    env.put(link + 0x0C, middle)
    env.put(middle + 0x24, layer)
    target = env.object(0x60, "target", data=noise(r, 0x60))
    env.put(target + 0x4C, ax, ay)
    env.put(target + 0x38, o.get("t38", r.randrange(0, 1000)))
    env.put(obj + 0x194, target)
    player = env.object(0x60, "player", data=noise(r, 0x60))
    dy = o.get("dy", 0)
    env.put(player + 0x4C, px, ay + dy)
    env.put(G_PLAYER, player)
    env.put(G_EVENT, o.get("event", 0x26B7 + 1 + r.randrange(100)))
    return {"O": obj, "X": x, "slots": slots, "trie": trie_values}


def make(label, function, seeds, **options):
    seed = seeds.getrandbits(32)

    def setup(env):
        return world(env, random.Random(seed), options)

    return Case(label, function, setup, receiver=lambda tokens: tokens["O"])


def rand_for(modulus, remainder, quotient=3):
    return quotient * modulus + remainder


# ---- cases ----------------------------------------------------------------------------------------------

def cases(random_source):
    R = random_source
    SIGHTS = ("clear", "wall-mid", "wall-target", "wall-start", "half-x", "half-y", "gap")
    TIMES = ("ge", "eq", "lt", "wrap", "huge")

    # ---- 0x44da20: home state ------------------------------------------------------------------
    for variant in range(8):
        yield make(f"home: name {variant} does not match", F_HOME, R, home=False, variant=variant,
                   kind=(0, 2, 3, 5, 1, 4, 6, 3)[variant], face=(2, 3, 2, 3, 2, 3, 2, 3)[variant])
    for face, flag2 in ((2, 0), (2, 1), (3, 0), (3, 1)):
        for kind in (0, 1, 2, 3, 4, 5, 6, 7, INT_MIN, 0xFFFFFFFF):
            options = {}
            if kind in (3, 4):
                options["rand"] = (rand_for(0x1A5, 3), 11, 12)
                options["thr"] = 4 + (kind + face) % 3        # remainder 3 is below the threshold
            yield make(f"home: face {face} flag {flag2} kind {kind:#x}", F_HOME, R, face=face, flag2=flag2, kind=kind,
                       variant=kind % 7, **options)
    for kind in (3, 4):
        for face, flag2 in ((2, 0), (3, 1)):
            for label, remainder, delta in (("just above", 1, 1), ("equal", 0, 0), ("far above", 200, -150)):
                threshold = remainder + delta if label != "equal" else remainder
                for no_seq in ((), (0x344,)):
                    yield make(f"home: kind {kind} face {face} threshold {label} sequence {'none' if no_seq else 'set'}",
                               F_HOME, R, face=face, flag2=flag2, kind=kind, thr=threshold,
                               rand=(rand_for(0x1A5, remainder, 5), rand_for(0x12D, 40 + kind, 7), 9), no_seq=no_seq,
                               anim=("idle", "tick", "heavy")[kind % 3])
    for grow, stride in ((1, 4), (2, 4), (3, 4), (1, 8), (1, 16), (4, 4)):
        yield make(f"home: table grows by {grow} entries of {stride} bytes", F_HOME, R, grow=grow, stride=stride, kind=grow % 7,
                   face=(2, 3)[grow % 2], flag2=grow % 2)
    yield make("home: kind 3 negative threshold", F_HOME, R, kind=3, face=2, flag2=0, thr=-5, rand=(rand_for(0x1A5, 2, 4), 7, 8))
    yield make("home: kind 4 threshold above every remainder", F_HOME, R, kind=4, face=3, flag2=1, thr=0x1A5 + 3,
               rand=(rand_for(0x1A5, 0x1A4, 2), 0x12C + 50, 8))
    for index in range(6):
        remainder = R.randrange(0, 0x1A5)
        yield make(f"home: random remainder {index}", F_HOME, R, kind=3 + index % 2, face=(2, 3)[index % 2], flag2=index // 3,
                   thr=remainder + (-1, 0, 1, 2, 1, 0)[index],
                   rand=(R.randrange(0, 80) * 0x1A5 + remainder, R.randrange(32768), R.randrange(32768)))
    for face in (4, 0xFFFFFFFF, 1):
        for kind in (0, 3, 2):
            yield make(f"home: unusual face {face:#x} kind {kind}", F_HOME, R, kind=kind, face=face, flag2=1,
                       thr=1000, rand=(rand_for(0x1A5, 9, 3), 40, 2))
    yield make("home: kind 5 wrong pacing key", F_HOME, R, kind=5, trie="wrong-key", face=2, flag2=0)
    yield make("home: kind 0 empty name trie", F_HOME, R, kind=0, trie="empty", face=3, flag2=1)
    yield make("home: kind 2 wrong advance key", F_HOME, R, kind=2, trie="wrong-key")

    # ---- 0x44dd30: pause state -----------------------------------------------------------------
    for grow, stride in ((1, 4), (2, 4), (1, 12)):
        yield make(f"pause: table grows by {grow} entries of {stride} bytes", F_PAUSE, R, pause=False, grow=grow, stride=stride,
                   time=("ge", "lt", "wrap")[grow % 3], cc=1)
    for variant in range(4):
        yield make(f"pause: name {variant} matches", F_PAUSE, R, pause=True, variant=variant, time=TIMES[variant % 5])
    for variant in range(8):
        yield make(f"pause: name {variant} does not match", F_PAUSE, R, pause=False, variant=variant,
                   time=("ge", "lt")[variant % 2], cc=(1, 0)[variant // 4])
    index = 0
    for time in ("ge", "eq", "wrap"):
        for first in (0, 1):
            for second in (0, 1):
                for gflag in (0, 1):
                    yield make(f"pause: expired time {time} sound {first}{second} gate {gflag}", F_PAUSE, R, pause=False,
                               variant=index, time=time, gflag=gflag, x8full=index % 2,
                               sound={0x3A4: first, 0x38C: second}, spawn_ptr=bool(index % 2),
                               spawn_k=(0, -4, 3)[index % 3], spawn_n=(0, -2, -1)[index % 3])
                    index += 1
    for gflag in (0, 1):
        for spawn_k in (1, 3):
            yield make(f"pause: expired with spawn handler count {spawn_k} gate {gflag}", F_PAUSE, R, pause=False, variant=gflag,
                       time="ge", gflag=gflag, spawn_obj=True, spawn_k=spawn_k, spawn_n=-spawn_k, sound={0x3A4: 1, 0x38C: gflag})
    for time in ("lt", "huge"):
        for cc in (1, 0, 2, 0x101):
            for anim in ("idle", "tick", "tick-delta", "heavy"):
                if (cc, anim) in ((1, "idle"), (1, "tick"), (1, "tick-delta"), (1, "heavy"), (0, "idle"), (2, "tick"), (0x101, "tick-delta")):
                    yield make(f"pause: waiting {time} controller {cc} animation {anim}", F_PAUSE, R, pause=False,
                               variant=index, time=time, cc=cc, anim=anim)
                    index += 1

    # ---- 0x44de50: wait state ------------------------------------------------------------------
    index = 0
    for time in ("ge", "eq", "wrap"):
        for first in (0, 1):
            for second in (0, 1):
                for gflag in (0, 1):
                    if (index % 2) == 0 or time == "ge":
                        yield make(f"wait: expired time {time} sound {first}{second} gate {gflag}", F_WAIT, R, time=time,
                                   gflag=gflag, sound={0x3A4: first, 0x38C: second}, anim=("idle", "tick", "tick-delta")[index % 3],
                                   spawn_ptr=bool(index % 2), spawn_k=(0, -4, 3)[index % 3], spawn_n=(0, -2, -1)[index % 3],
                                   x8full=index % 2)
                    index += 1
    for gflag in (0, 1):
        yield make(f"wait: expired with spawn handler gate {gflag}", F_WAIT, R, time="eq", gflag=gflag, spawn_obj=True,
                   spawn_k=2 + gflag, spawn_n=-1, sound={0x3A4: gflag, 0x38C: 1})
    for time in ("lt", "huge"):
        for cc in (1, 0, 2, 0x101):
            for anim in ("idle", "tick", "heavy"):
                if (cc + (anim == "heavy")) % 2 == 1 or cc == 1:
                    yield make(f"wait: not yet {time} controller {cc} animation {anim}", F_WAIT, R, time=time, cc=cc, anim=anim)

    # ---- 0x44e510: turn state ------------------------------------------------------------------
    index = 0
    for face in (2, 3):
        for flag2 in (0, 1):
            for sent in range(8):
                if flag2 == (1 if face == 2 else 0) and sent > 1:
                    continue
                yield make(f"turn: face {face} flag {flag2} sentinels {sent}", F_TURN, R, face=face, flag2=flag2, sent=sent,
                           cc=(1, 1, 0)[sent % 3], anim=("idle", "tick", "tick-delta", "heavy")[index % 4])
                index += 1
    for cc in (1, 0, 2, 0x101):
        yield make(f"turn: controller {cc}", F_TURN, R, face=2, flag2=0, cc=cc, sent=5)
        yield make(f"turn: other face controller {cc}", F_TURN, R, face=0, flag2=1, cc=cc, sent=3)

    # ---- 0x44ea10: rest state ------------------------------------------------------------------
    for cc in (1, 0, 2, 0x101, 0xFFFFFFFF):
        for x8 in (False, True):
            yield make(f"rest: controller {cc} body flag {x8}", F_REST, R, cc=cc, x8bit4=x8,
                       anim=("idle", "tick", "tick-delta", "expire")[(cc + x8) % 4])

    # ---- 0x44ea60: track state ------------------------------------------------------------------
    for eq in ((), ("12",), ("13",), ("12", "13"), ("nan1",), ("nan2",), ("zero",)):
        yield make(f"track: doubles {'+'.join(eq) or 'distinct'}", F_TRACK, R, eq=eq, kind=(0, 3, 5, 6, 0, 3, 0)[len(eq) + len(eq[:1])] if eq else 1,
                   face=(2, 3, 2, 3, 2, 3, 2)[len(eq) % 7], flag2=len(eq) % 2)
    for face, flag2 in ((2, 0), (2, 1), (3, 0), (3, 1), (0, 0), (0, 1)):
        for kind in (0, 1, 2, 3, 4, 5, 6, 7):
            if (face + flag2 + kind) % 2 == 0 or kind in (0, 3, 5):
                yield make(f"track: face {face} flag {flag2} kind {kind}", F_TRACK, R, face=face, flag2=flag2, kind=kind,
                           anim=("idle", "tick", "tick-delta")[kind % 3], eq=(() , ("12",), ("13",))[(kind + face) % 3],
                           sent=(face * 3 + kind) % 8)
    for face in (4, 0xFFFFFFFF, 1):
        for kind in (0, 3, 5):
            yield make(f"track: unusual face {face:#x} kind {kind}", F_TRACK, R, face=face, kind=kind, flag2=1)
    yield make("track: kind 0x80000000", F_TRACK, R, kind=INT_MIN, face=2, flag2=0)
    yield make("track: kind 0xffffffff", F_TRACK, R, kind=0xFFFFFFFF, face=3, flag2=1)
    yield make("track: kind 0 wrong fast key", F_TRACK, R, kind=0, trie="wrong-key")
    yield make("track: kind 0 empty trie", F_TRACK, R, kind=0, trie="empty")
    for face in (3, 2):
        yield make(f"track: velocity from field 0x400, face {face}", F_TRACK, R, kind=7, face=face, flag2=0)

    # ---- 0x44ebb0: fast advance ----------------------------------------------------------------
    index = 0
    for face, flag2 in ((2, 0), (2, 1), (3, 0), (3, 1), (0, 1), (1, 0)):
        for no_seq in ((), (0x30C,)):
            yield make(f"fast: face {face} flag {flag2} sequence {'none' if no_seq else 'set'}", F_FAST, R, face=face,
                       flag2=flag2, no_seq=no_seq, sent=(index * 3) % 8, anim=("idle", "tick", "heavy")[index % 3],
)
            index += 1
    for face in (4, 0xFFFFFFFF):
        yield make(f"fast: unusual face {face:#x}", F_FAST, R, face=face, flag2=1)
    for mode in ("wrong-key", "empty"):
        yield make(f"fast: trie {mode}", F_FAST, R, face=3, flag2=1, trie=mode)

    # ---- 0x44ec80: seek state -------------------------------------------------------------------
    combos = []
    for eq in ((), ("12",), ("13",), ("12", "13")):
        for face in (2, 3, 0):
            combos.append((eq, face, R.randrange(2)))
    combos += [((), 2, 1 - combos[0][2]), (("12",), 2, 1), (("13",), 2, 0), (("12", "13"), 2, 1)]
    for index, (eq, face, flag2) in enumerate(combos):
        for pick in range(3):
            kind = (index + pick * 3) % 8
            kind = kind if kind != 7 else INT_MIN
            yield make(f"seek: doubles {'+'.join(eq) or 'distinct'} face {face} flag {flag2} kind {kind:#x}", F_SEEK, R,
                       eq=eq, face=face, flag2=flag2, kind=kind, sent=(index + pick) % 8,
                       anim=("idle", "tick", "tick-delta")[(index + pick) % 3])
    for face in (2, 3):
        for kind in (0, 1, 5, 2, 3, 6):
            yield make(f"seek: nothing equal, face {face}, kind {kind}", F_SEEK, R, face=face, kind=kind, flag2=kind % 2)
    for face in (4, 0xFFFFFFFF):
        for eq in ((), ("12",), ("13",)):
            yield make(f"seek: unusual face {face:#x} doubles {'+'.join(eq) or 'distinct'}", F_SEEK, R, eq=eq, face=face, kind=0)
    for eq in (("nan1",), ("nan2",), ("zero",)):
        for face in (3, 2):
            yield make(f"seek: doubles {eq[0]} face {face}", F_SEEK, R, eq=eq, face=face, kind=0, flag2=0)

    # ---- 0x44f290: scan state --------------------------------------------------------------------
    for size in (0, 1, 8, 9, 0x20, 0x21, 100):
        for bit in (0, 1):
            word = (0x100 if bit else 0) | (R.getrandbits(32) & ~0x100) | (0x4 if size % 2 else 0)
            yield make(f"scan: set size {size:#x} bit8 {bit}", F_SCAN, R, bits_size=size, bits=word, kind=3 + (size % 2) * 3,
                       sight="clear", anim=("idle", "tick")[bit])
    for size, word, label in ((12, 0x80, "bit7 only"), (12, 0x200, "bit9 only"), (0xFFFFFFFF, 0x100, "huge size with bit8"),
                              (0xFFFFFFFF, 0x2FF, "huge size without bit8"), (0x22, 0x100, "pointer variant"),
                              (0x1F, 0x1FF, "inline variant")):
        yield make(f"scan: set {label}", F_SCAN, R, bits_size=size, bits=word, kind=1 + len(label) % 5, sight="clear")
    for index in range(6):
        remainder = (1, 1, 0, 2, 1, 1)[index]
        yield make(f"scan: random remainder {index}", F_SCAN, R, bits_size=0, kind=5 + index % 2, time="ge",
                   rand=(R.randrange(0, 160) * 0xC9 + remainder, R.randrange(32768), 1))
    for event in (0x26B7, 0x26B6):
        yield make(f"scan: event {event:#x}", F_SCAN, R, bits_size=40, bits=0x1FF, event=event, kind=3)
    for sight in SIGHTS:
        for direction in ("right", "left"):
            yield make(f"scan: sight {sight} {direction}", F_SCAN, R, bits_size=12, bits=0x100 | R.getrandbits(8), sight=sight,
                       direction=direction, kind=(0, 1, 2, 3, 4, 5, 6)[len(sight) % 7], dy=R.randrange(-0x30, 0x31))
    for t38 in (0x1FF, 0xFFFFFFFF, 0xFF, 0):
        yield make(f"scan: target field {t38:#x}", F_SCAN, R, bits_size=9, bits=0x100, dy=3, t38=t38, kind=7, sight="clear")
    for dy in (0x31, 0x32, -0x31, -0x32, 0, 0x100, -0x100):
        for t38 in (-1, 5):
            yield make(f"scan: vertical gap {dy:#x} target {t38}", F_SCAN, R, bits_size=9, bits=0x100, dy=dy, t38=t38,
                       kind=7, sight="clear", direction="left" if dy < 0 else "right")
    for kind in (0, 1, 2, 3, 4, 5, 6, 7, INT_MIN):
        yield make(f"scan: kind {kind:#x}", F_SCAN, R, bits_size=0, kind=kind, rand=(rand_for(0xC9, 1, 6), 3, 4), time="ge")
    for kind in (5, 6):
        for label, remainder, time in (("rand miss", 0, "ge"), ("rand miss high", 2, "ge"), ("time early", 1, "lt"),
                                       ("time equal", 1, "eq"), ("time wrap", 1, "wrap"), ("time huge", 1, "huge"),
                                       ("rand and time", 1, "ge")):
            yield make(f"scan: kind {kind} {label}", F_SCAN, R, bits_size=0, kind=kind, time=time,
                       rand=(rand_for(0xC9, remainder, 40 + kind), 5, 7), bits=R.getrandbits(32) & ~4)

    # ---- 0x44f490 / 0x44f660: decay states ---------------------------------------------------------
    for function, tag in ((F_DECAY_A, "decay-a"), (F_DECAY_B, "decay-b")):
        for mode, c14, c1c in (("idle", 0, 1), ("idle", 0, 0), ("idle", 3, 2), ("expire", None, 1), ("expire", None, 2),
                               ("tick", 4, 1), ("tick-delta", None, 2), ("heavy", None, 0)):
            for face, shape in ((3, "lt"), (2, "gt")):
                for velocity in ("equal", "differs", "nan"):
                    if (velocity == "differs") or (mode in ("idle", "tick")) == (velocity == "equal") or face == 3 and mode == "heavy":
                        yield make_decay(R, function, f"{tag}: {mode} c14 {c14} c1c {c1c} face {face} velocity {velocity}",
                                         mode, c14, c1c, face, velocity)

    # ---- 0x44f800: idle state ---------------------------------------------------------------------------
    for cc in (1, 0, 2, 0x101, 0xFFFFFFFF):
        for anim in ("idle", "tick", "tick-delta", "heavy"):
            if cc == 1 or anim in ("idle", "heavy"):
                yield make(f"idle: controller {cc} animation {anim}", F_IDLE, R, cc=cc, anim=anim)


def make_decay(random_source, function, label, mode, c14, c1c, face, velocity):
    seed = random_source.getrandbits(32)

    def setup(env):
        r = random.Random(seed)
        tokens = world(env, r, {"anim": mode, "c14": c14, "c1c": c1c, "face": face, "kind": r.randrange(7)})
        low, high = struct.unpack("<II", env.read(0x50E100, 8))
        if velocity == "equal":
            env.put(tokens["O"] + 0x50, low, high)
        elif velocity == "nan":
            env.put(tokens["O"] + 0x50, *dbl(NAN))
        else:
            constant = struct.unpack("<d", env.read(0x50E100, 8))[0]
            env.put(tokens["O"] + 0x50, *dbl(constant + r.choice((1.0, -3.25, 1000.5, 0.125))))
        return tokens

    return Case(label, function, setup, receiver=lambda tokens: tokens["O"])
