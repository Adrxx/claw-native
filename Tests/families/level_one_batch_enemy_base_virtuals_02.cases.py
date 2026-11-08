"""Cases for level_one_batch_enemy_base_virtuals_02: Level 1 enemies, shared enemy base virtual slots, batch 2.

Every case builds one enemy actor (size 0x500) with distinct non-zero contents, the objects it points to, the
globals the original callees read, and a scripted random source.  Coverage is enumerated by the loops in cases(),
never taken from the random draws: the random source only fills bytes that no branch reads and picks values whose
exact number does not steer control flow.  Every random draw happens when the generator runs, and setup() replays
it from a private generator, so a setup is the same however often it is called.

The sound/effect services behind 0x4b45f0 (OutputDebugString and MessageBox on the failure route) stay out of
reach: 0x532c0c is zero in every case, and the pointers that would be passed to it are only followed when it is not.
"""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

M32 = 0xFFFFFFFF
SENTINEL = 0x80000000

F_FALL, F_STRIKE3, F_STRIKE2, F_STRIKE0 = 0x43ED70, 0x43EEE0, 0x43EE10, 0x43EFE0
F_MOVE, F_DEAD, F_A440, F_AAF0, F_E5B0, F_E1B0 = 0x43FA10, 0x44E0C0, 0x40A440, 0x40AAF0, 0x40E5B0, 0x40E1B0
RAND = 0x4A3050

G_PLAYER = 0x537E88          # DAT_00537e88
G_UI = 0x537204              # DAT_00537204
G_NOW = 0x537210             # DAT_00537210
G_FLAG = 0x532C0C            # DAT_00532c0c: gate in front of 0x4b45f0
G_FLAG_ARG = 0x532C10
G_STEP = 0x5430C4
G_SVC_Q, G_SVC_BUSY, G_SVC_OWNER = 0x53C9AC, 0x53C9A8, 0x53C9B0
G_5349DC = 0x5349DC
G_TAIL = 0x534E60            # six words 41fe80 clears
TRIE = 0x537668
TRIE_ROOT = TRIE + 0x18

KEYS = {"FALLING": b"LS_FALLING", "STRIKE": b"LS_STRIKE", "MOVEAHEAD": b"LS_MOVEAHEAD", "DEAD": b"LS_DEAD",
        "IDLE": b"LS_IDLE"}
GAME_NULL = b"GAME_NULL"


# ------------------------------------------------------------------------------------------------ small helpers
def s32(x):
    x &= M32
    return x - (1 << 32) if x >> 31 else x


def cmod(a, m):
    """C remainder of a signed 32-bit value (idiv)."""
    a = s32(a)
    q = abs(a) % m
    return -q if a < 0 else q


def sub_rng(rs):
    seed = rs.getrandbits(64)
    return lambda: random.Random(seed)


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def junk(r, count):
    return bytes(r.randrange(1, 256) for _ in range(count))


def dbl(x):
    return struct.pack("<d", x)


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


# ------------------------------------------------------------------------------------------------ building blocks
def make_param(env, r, count=None):
    """An animation sequence for 0x4c8220: +0x10 count >= 1, +0xc table whose first entry has a word at +0x1c."""
    frame = env.object(0x40, "frame", words=words_of(r, 16))
    table = env.object(8, "frame-table", words=[frame, r.randrange(1, 1 << 32)])
    param = env.object(0x20, "sequence", words=words_of(r, 8))
    env.put(param + 0xC, table)
    env.put(param + 0x10, count if count is not None else r.choice((1, 2, 3)))
    return param


def registry(env, r, entries, buckets, decoys=True):
    """A string table as 0x4f6286 reads it, embedded at owner+0x10.  Nodes are [next, 0, key, value].
    A value of "P" becomes a fresh animation sequence."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(owner + 0x14, array, buckets)
    for name, value in entries.items():
        if value == "P":
            value = make_param(env, r)
        key = env.object(len(name) + 1, "registry-key", data=name + b"\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        env.put(array + 4 * index, node)
        if decoys:
            decoy_name = name + b"~"
            decoy_key = env.object(len(decoy_name) + 1, "decoy-key", data=decoy_name + b"\0")
            decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, r.randrange(1, 1 << 32)])
            env.put(array + 4 * index, decoy)
    return owner


def leaf(env, text, value, wrong=False):
    shown = text[:-1] + b"?" if wrong else text
    key = env.object(len(shown) + 1, "trie-key", data=shown + b"\0")
    node = env.object(0x20, "trie-leaf", fill=0)
    env.put(node + 8, 0)
    env.put(node + 0xC, key)
    env.put(node + 0x10, value)
    return node


def install_trie(env, r, empty=False, missing=(), wrong=()):
    """The string trie at 0x537668.  The keys differ in byte 3, so the nodes test bits 24, 25 and 26.
    missing: names whose child pointer is 0.  wrong: names whose leaf holds another text."""
    env.put(TRIE + 0x1C, *words_of(r, 4))
    values = {name: r.randrange(1, 1 << 32) for name in KEYS}
    if empty:
        env.put(TRIE_ROOT, 0)
        return values
    leaves = {}
    for name, text in KEYS.items():
        leaves[name] = 0 if name in missing else leaf(env, text, values[name], wrong=name in wrong)
    node_a = env.object(0x20, "trie-a", fill=0)
    env.put(node_a + 8, 25)
    env.put(node_a, leaves["DEAD"], leaves["FALLING"])
    node_c = env.object(0x20, "trie-c", fill=0)
    env.put(node_c + 8, 26)
    env.put(node_c, leaves["IDLE"], leaves["MOVEAHEAD"])
    node_b = env.object(0x20, "trie-b", fill=0)
    env.put(node_b + 8, 25)
    env.put(node_b, node_c, leaves["STRIKE"])
    root = env.object(0x20, "trie-root", fill=0)
    env.put(root + 8, 24)
    env.put(root, node_a, node_b)
    env.put(TRIE_ROOT, root)
    return values


def tile_effect(results, hook=None):
    def effect(env, call):
        n = env.calls_so_far(call.function)
        if hook is not None:
            hook(env, n)
        return results[min(n, len(results)) - 1]
    return effect


def tile_world(env, r, stub, ids, y_base, y_extra, hole=None, x_hint=None):
    """The object at E+0x128: +0xc -> object whose +0x24 is the tile map read by 0x4207f0.  A 128x128 layer of
    16 pixel tiles; every cell holds one of `ids` (index into the object table at map+0x4c) with random high
    bits.  hole = (x, y): the cell holding that pixel is emptied (0xffffffff), as 0x4207f0 clamps first."""
    tilemap = env.object(0x80, "tilemap", words=words_of(r, 0x20))
    layer = env.object(0xA0, "layer", words=words_of(r, 0x28))
    data = env.object(4 * 64, "tile-data", fill=0)
    rows = env.object(4 * 8, "tile-rows", fill=0)
    for j in range(8):
        env.put(rows + 4 * j, 8 * j)
    for k in range(64):
        env.put(data + 4 * k, (r.randrange(1, 1 << 16) << 16) | r.choice(ids))
    if hole is not None:
        cx, cy = min(max(hole[0], 0), 127), min(max(hole[1], 0), 127)
        env.put(data + 4 * ((cy >> 4) * 8 + (cx >> 4)), 0xFFFFFFFF)
    vtable = env.object(0x40, "tile-vtable", words=words_of(r, 16))
    env.put(vtable + 0x20, stub)
    table = env.object(4 * (max(ids) + 1), "tile-objects", fill=0)
    for i in range(max(ids) + 1):
        env.put(table + 4 * i, env.object(0x20, "tile-object", words=[vtable] + words_of(r, 7)))
    env.put(layer + 0x20, data, rows)
    env.put(layer + 0x30, 128, 128)
    env.put(layer + 0x8C, 4, 4)
    env.put(tilemap + 0x4C, table)
    env.put(tilemap + 0x5C, layer)
    middle = env.object(0x40, "tile-owner", words=words_of(r, 16))
    env.put(middle + 0x24, tilemap)
    world = env.object(0x180, "tile-world", data=junk(r, 0x180))
    env.put(world + 0xC, middle)
    env.put(world + 0x50, y_extra)
    env.put(world + 0x124, y_base)
    return world


def services(env, r, kind, record_state=None):
    """The queue behind 0x53c9ac that 0x48ce40 and 0x48cf50 read.  kind: ok, none, busy, no-record."""
    queue = env.object(0x200, "service-queue", data=junk(r, 0x200))
    record = env.object(0x140, "service-record", data=junk(r, 0x140))
    env.put(record + 0x1C, record_state if record_state is not None else r.randrange(0x100, 1 << 32))
    env.put(queue + 0x6C, 0 if kind == "no-record" else record)
    env.put(G_SVC_Q, 0 if kind == "none" else queue)
    env.put(G_SVC_BUSY, r.randrange(1, 1 << 32) if kind == "busy" else 0)
    env.put(G_SVC_OWNER, r.randrange(1, 1 << 32))
    return queue, record


# ------------------------------------------------------------------------------------------------ the actor
PARAM_OFFSETS = (0x308, 0x310, 0x32C, 0x350, 0x420, 0x470, 0x474, 0x478)


def actor_init(env, r, o):
    """Everything an enemy needs.  Options (all optional):
    z1c, s38, s40, sent (3 flags), mode, e184, cnt/bits/bits_ptr, f44c, e148/e14c/e150, params {offset: 0|None},
    owner_zero, r1/r2 registries, g4c, q2_1c, pp0/pp1/pp_param, services kind, rand (int or list)."""
    junk_e = junk(r, 0x500)
    e = env.object(0x500, "actor", data=junk_e)
    tok = {"E": e}
    env.put(G_NOW, o.get("now", r.randrange(1, 1 << 32)))
    env.put(G_FLAG, o.get("flag", 0))
    env.put(G_FLAG_ARG, r.randrange(1, 1 << 32))
    env.put(G_STEP, r.randrange(1, 50))
    # the actor's helper objects
    zed = env.object(0x40, "zed", words=words_of(r, 16))
    env.put(zed + 0x1C, o.get("z1c", r.randrange(1, 1 << 32)))
    env.put(e + 0x10, zed)
    owner = env.object(0x200, "owner", data=junk(r, 0x200))
    env.put(e + 0xC, 0 if o.get("owner_zero") else owner)
    scale = env.object(0x200, "scale", data=junk(r, 0x200))
    env.put(scale + 0x190, r.randrange(1, 1 << 32))
    env.put(scale + 0x38, o.get("s38", r.randrange(1, 1 << 31)))
    env.put(scale + 0x40, o.get("s40", r.randrange(1, 1 << 32) & ~2))
    for flag, offset in zip(o.get("sent", (0, 0, 0)), (0x118, 0x128, 0x138)):
        if flag:
            env.put(scale + offset, SENTINEL)
    env.put(e + 0x12C, scale)
    xx = env.object(0x40, "registry-holder", words=words_of(r, 16))
    buckets = r.choice((1, 3, 5, 7))
    env.put(xx + 0x2C, registry(env, r, o.get("r1", {b"UNRELATED_A": "P"}), buckets))
    env.put(xx + 0x28, registry(env, r, o.get("r2", {b"UNRELATED_B": r.randrange(1, 1 << 32)}), r.choice((1, 3, 5, 7))))
    env.put(scale + 0xC, xx)
    # state and parameter words
    env.put(e + 0x18C, o.get("mode", 0))
    env.put(e + 0x184, o.get("e184", 5))
    for offset in PARAM_OFFSETS:
        env.put(e + offset, 0 if o.get("params", {}).get(offset, 1) == 0 else make_param(env, r))
    env.put(e + 0x44C, 0 if o.get("f44c", 1) == 0 else env.object(0x20, "attachment", words=words_of(r, 8)))
    for offset in (0x3A8, 0x3AC, 0x3B0):
        env.put(e + offset, env.object(0x30, "sound-handle", words=words_of(r, 12)) if not o.get("no_sounds") else 0)
    env.put(e + 0x374, make_param(env, r))
    # bit set read by 0x44e0c0
    cnt = o.get("cnt", 5)
    env.put(e + 0x2FC, cnt)
    bits = o.get("bits", 0x10) & M32
    if cnt > 0x20:
        env.put(e + 0x300, env.object(0x10, "flag-words", words=[bits] + words_of(r, 3)))
    else:
        env.put(e + 0x300, bits)
    # 0x42df90 runs on e+0x128: a list of goodies that is empty
    env.put(e + 0x148, o.get("e148", 0))
    env.put(e + 0x14C, o.get("e14c", 0))
    env.put(e + 0x150, o.get("e150", 0))
    env.write(e + 0x154, b"\0" * 32)
    # the player and its records
    player = env.object(0x200, "player", data=junk(r, 0x200))
    env.put(player + 0x4C, o.get("g4c", r.randrange(0, 80)) & M32)
    q2 = env.object(0x40, "player-q2", words=words_of(r, 16))
    env.put(q2 + 0x1C, o.get("q2_1c", r.randrange(1, 1 << 32)))
    env.put(player + 0x6C, q2)
    pp = env.object(0x200, "player-pp", data=junk(r, 0x200))
    env.put(pp, o.get("pp0", 1))
    env.put(pp + 4, o.get("pp1", 0))
    env.put(pp + 0x124, make_param(env, r) if o.get("pp_param", 1) else 0)
    env.put(pp + 0x12C, 0)
    env.put(q2 + 0x14, pp)
    holder = env.object(0x40, "player-holder", words=words_of(r, 16))
    env.put(holder + 0x2C, registry(env, r, {b"UNRELATED_C": "P"}, 3))
    env.put(player + 0xC, holder)
    env.put(G_PLAYER, player)
    env.put(G_UI, env.object(0x20, "ui", words=words_of(r, 8)))
    env.put(G_5349DC, r.randrange(1, 1 << 32))
    env.write(G_TAIL, struct.pack("<6I", *words_of(r, 6)))
    # services behind 48ce40 / 48cf50
    queue, record = services(env, r, o.get("services", "ok"), o.get("record_state"))
    tok.update(player=player, q2=q2, pp=pp, scale=scale, zed=zed, owner=owner, queue=queue, record=record)
    install_trie(env, r, empty=o.get("trie_empty", False), missing=o.get("trie_missing", ()),
                 wrong=o.get("trie_wrong", ()))
    rand = o.get("rand")
    if rand is not None:
        env.override(RAND, returns(rand) if isinstance(rand, int) else sequence(*rand))
    return tok


def make_setup(rs, extra=None, **o):
    mk = sub_rng(rs)

    def setup(env):
        r = mk()
        tok = actor_init(env, r, o)
        if extra is not None:
            tok.update(extra(env, r, tok) or {})
        return tok
    return setup


def case(label, function, setup, *arguments):
    return Case(label, function, setup, receiver=lambda t: t["E"], arguments=tuple(arguments))


def token(name):
    return lambda t: t[name]


# ------------------------------------------------------------------------------------------------ cases
def cases(random_source):
    rs = random_source

    # ------------------------------------------------------------- 0x43ed70 and 0x43efe0: the animation starts
    trie_variants = [("full", {}), ("empty trie", {"trie_empty": True}), ("key child missing", {"trie_missing": ("FALLING", "STRIKE")}),
                     ("key leaf wrong", {"trie_wrong": ("FALLING", "STRIKE")}),
                     ("other leaf wrong", {"trie_wrong": ("DEAD", "IDLE", "MOVEAHEAD")})]
    for function, name, field in ((F_FALL, "fall", 0x32C), (F_STRIKE0, "strike0", 0x310)):
        for text, trie_opts in trie_variants:
            for param in (1, 0):
                yield case(f"{name} {text} param {'set' if param else 'null'}", function,
                           make_setup(rs, params={field: param}, **trie_opts))
        for _ in range(3):
            yield case(f"{name} random", function, make_setup(rs, params={field: 1}))

    # ------------------------------------------------------------- 0x43ee10 / 0x43eee0: registry lookups
    first = {"found": {b"ENEMY_STRIKE_A": "P"}, "zero": {b"ENEMY_STRIKE_A": 0}, "miss": {}}
    second = {"found": {GAME_NULL: "P"}, "zero": {GAME_NULL: 0}, "miss": {}}

    def strike_setup(first_kind, null_kind, third_kind, key1=b"ENEMY_STRIKE_A", key3=b"ENEMY_SOUND_B", same_key=False):
        r1 = {b"OTHER_X": "P", b"OTHER_Y": 0, **{key1: v for v in first[first_kind].values()}, **second[null_kind]}
        r2 = {b"OTHER_Z": 0x1234567}
        if third_kind == "found":
            r2[key3] = None
        elif third_kind == "zero":
            r2[key3] = 0
        elif third_kind == "swapped":
            r1[key3] = "P"           # only the other registry knows this key
        if same_key:
            r2[key1] = None
        mk = sub_rng(rs)

        def setup(env):
            r = mk()
            for name_, value in list(r2.items()):
                if value is None:
                    r2[name_] = r.randrange(1, 1 << 32)
            tok = actor_init(env, r, {"r1": r1, "r2": r2})
            tok["rec"] = env.object(16, "record", words=[r.randrange(1, 1 << 32) for _ in range(4)])
            tok["k1"] = env.object(len(key1) + 1, "key1", data=key1 + b"\0")
            tok["k3"] = env.object(len(key3) + 1, "key3", data=key3 + b"\0")
            return tok
        return setup

    for first_kind in first:
        for null_kind in second:
            yield case(f"strike2 {first_kind} then GAME_NULL {null_kind}", F_STRIKE2,
                       strike_setup(first_kind, null_kind, "miss"), token("k1"), token("rec"))
            for third_kind in ("found", "zero", "miss", "swapped"):
                yield case(f"strike3 {first_kind} then GAME_NULL {null_kind}, third {third_kind}", F_STRIKE3,
                           strike_setup(first_kind, null_kind, third_kind), token("k1"), token("rec"), token("k3"))
    yield case("strike3 both keys equal", F_STRIKE3, strike_setup("found", "found", "found", key3=b"ENEMY_STRIKE_A", same_key=True),
               token("k1"), token("rec"), token("k1"))
    yield case("strike3 long keys", F_STRIKE3,
               strike_setup("found", "miss", "found", key1=b"A_VERY_LONG_STRIKE_ANIMATION_NAME_FOR_ENEMY_NUMBER_ONE",
                            key3=b"AN_EVEN_LONGER_SOUND_EFFECT_NAME_THAT_SPANS_BUCKETS"),
               token("k1"), token("rec"), token("k3"))
    yield case("strike2 high-bit key", F_STRIKE2, strike_setup("found", "found", "miss", key1=b"CAF\xe9_\xff\x80_STRIKE"),
               token("k1"), token("rec"))
    for _ in range(4):
        pick = rs.choice(list(first)), rs.choice(list(second)), rs.choice(("found", "zero", "miss"))
        yield case(f"strike3 random {pick}", F_STRIKE3, strike_setup(*pick), token("k1"), token("rec"), token("k3"))

    # ------------------------------------------------------------- 0x44e0c0: the death transition
    counts = [(0, 0), (1, 0x10), (4, 0x10), (4, 0), (5, 0x10), (5, 0), (0x20, 0x10), (0x20, 0xFFFFFFEF),
              (0x21, 0x10), (0x21, 0xFFFFFFEF), (0x40, 0), (0x40, 0x10), (3, 0xFFFFFFFF)]
    for cnt, bits in counts:
        for p in (4, 7):
            yield case(f"dead cnt {cnt:#x} bits {bits:#x} p {p}", F_DEAD,
                       make_setup(rs, cnt=cnt, bits=bits), lambda t, p=p: p)
    for p in (1, 2, 3, 0xFFFFFFFF, 0x80000000, 5):
        for cnt, bits in ((5, 0x10), (6, 0), (0x30, 0x1F0)):
            yield case(f"dead state {p:#x} cnt {cnt:#x} bits {bits:#x}", F_DEAD, make_setup(rs, cnt=cnt, bits=bits),
                       lambda t, p=p: p)
    for p in (1, 2, 3):
        yield case(f"dead state {p} nothing to stop", F_DEAD, make_setup(rs, cnt=7, bits=0, no_sounds=True),
                   lambda t, p=p: p)
        yield case(f"dead state {p} flag set, handles null", F_DEAD,
                   make_setup(rs, cnt=7, bits=0, no_sounds=True, flag=rs.randrange(1, 1 << 32)), lambda t, p=p: p)
    for e148, e14c, e150 in ((0, 0, 1), (0x4444, 0, 3), (0x4444, 2, 0), (0x5555, 3, -2), (0, 2, 4), (0x6666, 1, 1)):
        yield case(f"dead goodies {e148:#x} {e14c} {e150}", F_DEAD,
                   make_setup(rs, cnt=2, bits=0, e148=e148, e14c=e14c, e150=e150 & M32), lambda t: 6)

    # ------------------------------------------------------------- 0x40aaf0: the dying hook
    pp_variants = [(0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1), (0, 1, 0), (1, 1, 0)]
    for pp0, pp1, pp_param in pp_variants:
        for mode_bits in ((7, 0x10), (7, 0)):
            yield case(f"hook 0x1390 pp {pp0}{pp1}{pp_param} bits {mode_bits[1]:#x}", F_AAF0,
                       make_setup(rs, q2_1c=0x1390, pp0=pp0, pp1=pp1, pp_param=pp_param, cnt=mode_bits[0],
                                  bits=mode_bits[1]), lambda t: 4)
    for q2 in (0, 0x138F, 0x1391, 0x11390, 0x1390 ^ 0x80000000, M32):
        yield case(f"hook not 0x1390: {q2:#x}", F_AAF0, make_setup(rs, q2_1c=q2, cnt=7, bits=0), lambda t: 4)
    yield case("hook state 1", F_AAF0, make_setup(rs, q2_1c=0x1390, cnt=3, bits=0, pp0=0), lambda t: 1)
    yield case("hook random", F_AAF0, make_setup(rs, q2_1c=0x1390, cnt=rs.randrange(5, 9), bits=rs.getrandbits(32) & ~0x10,
                                                 pp0=rs.randrange(2), pp1=rs.randrange(2)), lambda t: 9)

    # ------------------------------------------------------------- 0x40e5b0: stop and clear the service owner
    def stop_setup(owner_matches, kind, record_state, f44c):
        mk = sub_rng(rs)

        def setup(env):
            r = mk()
            tok = actor_init(env, r, {"services": kind, "record_state": record_state, "f44c": f44c})
            e = tok["E"]
            env.put(G_SVC_OWNER, env.get(e + 0xC) if owner_matches else (env.get(e + 0xC) ^ 0x1000) | 1)
            return tok
        return setup

    for owner_matches in (1, 0):
        for kind in ("ok", "none", "no-record", "busy"):
            for record_state in (0xF, 0xE, 0x10, 0, 0x8000000F):
                for f44c in (1, 0):
                    if (kind != "ok" or not owner_matches) and (record_state, f44c) not in ((0xF, 1), (0xE, 0)):
                        continue
                    yield case(f"stop owner {owner_matches} {kind} state {record_state:#x} attach {f44c}", F_E5B0,
                               stop_setup(owner_matches, kind, record_state, f44c))

    # ------------------------------------------------------------- 0x40e1b0: copy the facing vector
    def facing_setup(s40, words, e3a4):
        mk = sub_rng(rs)

        def setup(env):
            r = mk()
            tok = actor_init(env, r, {"s40": s40})
            e = tok["E"]
            env.put(e + 0x210, *words)
            env.put(e + 0x3A4, e3a4)
            return tok
        return setup

    patterns = [(1, 2, 3, 4), (0x11111111, 0x22222222, 0x33333333, 0x44444444), (SENTINEL, 0, 0x7FFFFFFF, 5),
                (0, 0, 0, 0), (M32, M32, M32, M32), (SENTINEL, SENTINEL, SENTINEL, SENTINEL), (0x80, 0xFF, 0x7F, 0x100)]
    for s40 in (0, 2, 3, 0xFFFFFFFD, 0xFFFFFFFF, 0x10, 0x12, 1):
        for words in patterns[:3] + patterns[4:5]:
            yield case(f"facing s40 {s40:#x} words {words[0]:#x}", F_E1B0, facing_setup(s40, words, rs.randrange(1, 1 << 32)))
    for words in patterns:
        yield case(f"facing flipped words {words[0]:#x} {words[2]:#x}", F_E1B0, facing_setup(2, words, rs.getrandbits(32)))
    for _ in range(4):
        words = tuple(rs.getrandbits(32) | 1 for _ in range(4))
        yield case("facing random", F_E1B0, facing_setup(rs.getrandbits(32), words, rs.getrandbits(32)))

    # ------------------------------------------------------------- 0x40a440: the idle bark
    # random sequence: the bark roll (%100 < 60), the sound pick (%3), then the idle roll (%100 < 33) in 0x44f1b0
    def bark_setup(e184, rolls, kind, e470, owner_zero, mode, s38, s40, sent):
        sequence_ = list(rolls)
        mk = sub_rng(rs)

        def setup(env):
            r = mk()
            params = {0x470: 1, 0x474: 1, 0x478: 1, 0x420: 1}
            if e470 == 0:
                params = {off: 0 for off in (0x470, 0x474, 0x478)}
            tok = actor_init(env, r, {"e184": e184, "services": kind, "owner_zero": owner_zero, "mode": mode,
                                      "s38": s38, "s40": s40, "sent": sent, "rand": sequence_, "params": params})
            return tok
        return setup

    def rolls_for(first_roll, pick, idle_roll):
        return [first_roll, pick, idle_roll] if cmod(first_roll, 100) < 0x3C else [first_roll, idle_roll]

    for e184 in (6, 5, 0, 7, M32):
        for first_roll in ((0, 59, 60, 99, 5959, 6000) if e184 in (5, 6) else (0,)):
            for pick in ((0, 1, 2, 3, 4, 5) if first_roll in (0, 59) and e184 in (5, 6) else (0,)):
                yield case(f"bark e184 {e184:#x} roll {first_roll} pick {pick}", F_A440,
                           bark_setup(e184, rolls_for(first_roll, pick, 7777), "ok", 1, 0, 3, 0x5555, 0, (0, 0, 0)))
    for first_roll in (M32 - 99, 0x80000000, 0x8000003B, 0xFFFFFFFF, 0x7FFFFFFF, 0x7FFF):
        for pick in (M32 - 3, 0xFFFFFFFF, 0x80000001, 0x7FFFFFFE):
            if cmod(first_roll, 100) < 0x3C:
                yield case(f"bark signed roll {first_roll:#x} pick {pick:#x}", F_A440,
                           bark_setup(5, rolls_for(first_roll, pick, 31), "ok", 1, 0, 3, 0x5555, 0, (0, 0, 0)))
    for kind in ("ok", "none", "busy", "no-record"):
        for e470, owner_zero in ((1, 0), (0, 0), (1, 1)):
            yield case(f"bark service {kind} sounds {e470} owner_zero {owner_zero}", F_A440,
                       bark_setup(5, rolls_for(10, 1, 50), kind, e470, owner_zero, 3, 0x5555, 0, (0, 0, 0)))
    # the idle roll in 0x44f1b0 and its own services call
    for idle_roll in (0, 32, 33, 34, 99, 0xFFFFFFFF, 0x80000000):
        for s38 in (M32, 0):
            for kind in ("ok", "busy"):
                yield case(f"bark idle roll {idle_roll:#x} s38 {s38:#x} {kind}", F_A440,
                           bark_setup(6, rolls_for(90, 0, idle_roll), kind, 1, 0, 3, s38, 0, (0, 0, 0)))
    for mode in (2, 3, 0, M32):
        for s40 in (0, 2, 3):
            for sent in ((0, 0, 0), (1, 0, 1), (1, 1, 1), (0, 1, 0)):
                if mode != 2 and sent not in ((0, 0, 0), (0, 1, 0)):
                    continue
                yield case(f"bark flip mode {mode:#x} s40 {s40:#x} sent {sent}", F_A440,
                           bark_setup(6, rolls_for(90, 0, 50), "ok", 1, 0, mode, 0x5555, s40, sent))
    for _ in range(4):
        yield case("bark random", F_A440,
                   bark_setup(rs.choice((5, 6)), rolls_for(rs.getrandbits(15), rs.getrandbits(15), rs.getrandbits(15)),
                              rs.choice(("ok", "busy", "none")), rs.randrange(2), rs.randrange(2), rs.choice((2, 3)),
                              rs.randrange(1, 1 << 31), rs.getrandbits(32), (rs.randrange(2), rs.randrange(2), rs.randrange(2))))

    # ------------------------------------------------------------- 0x43fa10: walk ahead
    # random value v = player[0x4c] +/- (rand % 41 + 40); the scripted tile results walk the four lookups
    def move_setup(mode, rand, g4c, y_base, y_extra, results, e80_rule, e98_rule, s40=0, sent=(0, 0, 0), hole_row=False,
                   swap_after=None, params=None):
        mk = sub_rng(rs)
        is_ahead = mode == 3
        offset = cmod(rand, 41) + 0x28
        v = s32(g4c + offset) if is_ahead else s32(g4c - offset)

        def setup(env):
            r = mk()
            opts = {"mode": mode, "rand": rand, "g4c": g4c, "s40": s40, "sent": sent, "cnt": 5, "bits": 0x10}
            if params is not None:
                opts["params"] = params
            tok = actor_init(env, r, opts)
            e = tok["E"]
            env.write(e + 0x80, dbl(e80_rule(v)))
            env.write(e + 0x98, dbl(e98_rule(v)))
            hook = None
            stub_holder = {}

            def tile_hook(env_, n):
                if swap_after is not None and n == swap_after:
                    env_.put(e + 0x128, stub_holder["second"])
            stub = env.stub("tile-lookup", "thiscall", 2, tile_effect(results, tile_hook))
            x_for_hole = max(0, min(127, v))
            hole = (v, y_base + y_extra) if hole_row else None   # y - 1 = y_base + 1 + y_extra - 1
            world = tile_world(env, r, stub, (0, 1, 2, 3), y_base, y_extra, hole=hole)
            env.put(e + 0x128, world)
            if swap_after is not None:
                stub_holder["second"] = tile_world(env, r, stub, (0, 1, 2, 3, 4), (y_base + 37) & 0x7F, 5)
                tok["second"] = stub_holder["second"]
            tok["world"] = world
            return tok
        return setup

    # limits for the walk-ahead branch (mode 3): blocked when limit > v
    a_rules = {
        "equal": lambda v: float(v), "below by 1": lambda v: float(v - 1), "far below": lambda v: float(v) - 2.0 ** 31,
        "minus inf": lambda v: float("-inf"), "nan": lambda v: float("nan"), "minus zero": lambda v: -0.0 if v == 0 else float(v),
        "above by 1": lambda v: float(v + 1), "above by half": lambda v: v + 0.5, "above by a tiny bit": lambda v: v + 2.0 ** -20,
        "plus inf": lambda v: float("inf"), "huge": lambda v: 1e300,
    }
    a_passes = {"equal", "below by 1", "far below", "minus inf", "nan", "minus zero"}
    # limits for the other modes: blocked when limit < v
    b_rules = {
        "equal": lambda v: float(v), "above by 1": lambda v: float(v + 1), "plus inf": lambda v: float("inf"),
        "huge": lambda v: 1e300, "below by 1": lambda v: float(v - 1), "below by half": lambda v: v - 0.5,
        "below by a tiny bit": lambda v: v - 2.0 ** -20, "minus inf": lambda v: float("-inf"),
        "nan": lambda v: float("nan"), "far below": lambda v: float(v) - 2.0 ** 31,
    }
    b_passes = {"equal", "above by 1", "plus inf", "huge"}
    # the other limit is set so that the other branch would decide the opposite way
    anti_for_a = lambda blocks: (lambda v: float(v - 1000) if blocks else float(v + 1000))   # field 0x98 in mode 3
    anti_for_b = lambda blocks: (lambda v: float(v + 1000) if blocks else float(v - 1000))   # field 0x80 in other modes

    scripts = {
        "r1=1 then r4=0": [1, 0], "r1=1 then r4 busy": [1, 9], "r2=2 then r4=0": [0, 2, 0], "r2=2 then r4 busy": [0, 2, 5],
        "r3=3 then r4=0": [0, 0, 3, 0], "r3=3 then r4 busy": [0, 0, 3, 8], "no match": [0, 0, 0], "all other": [5, 6, 7],
        "r1=2 r2=2": [2, 2, 0], "r1=3 r2=3 r3=3": [3, 3, 3, 0], "wide values": [0x101, 2, 0],
        "negative values": [M32, 0xFFFFFFFE, 3, 0], "r3 wide": [0x103, 0x102, 0x103], "r1 big r2=2": [0x80000001, 2, 0xA5],
        "r1=1 r4 wide": [1, 0x10000],
    }
    rand_samples = [0, 1, 40, 41, 0x7FFF, 0x1234]
    # tile walk, every script, three modes (ahead; flipped-mode; other) with a passing limit
    for mode in (3, 2, 0):
        for sname, results in scripts.items():
            rand = rs.choice(rand_samples) if mode != 2 else rs.randrange(0, 0x8000)
            g4c = rs.randrange(10, 70)
            y_base, y_extra = rs.randrange(8, 90), rs.randrange(0, 12)
            if mode == 3:
                e80, e98 = a_rules["equal"], anti_for_a(False)
            else:
                e98, e80 = b_rules["equal"], anti_for_b(False)
            yield case(f"move mode {mode} tiles {sname}", F_MOVE,
                       move_setup(mode, rand, g4c, y_base, y_extra, results, e80, e98))
    # the limit compare
    for mode in (3, 2, 1):
        rules, passes = (a_rules, a_passes) if mode == 3 else (b_rules, b_passes)
        for rname, rule in rules.items():
            blocks = rname not in passes
            for rand in (rs.choice((rs.randrange(0, 0x8000), 0, 0x7FFF)),):
                g4c = rs.randrange(5, 60)
                if mode == 3:
                    e80, e98 = rule, anti_for_a(blocks)
                else:
                    e98, e80 = rule, anti_for_b(blocks)
                yield case(f"move mode {mode} limit {rname} rand {rand}", F_MOVE,
                           move_setup(mode, rand, g4c, rs.randrange(8, 90), rs.randrange(0, 12), [1, 0], e80, e98))
    # signed remainders and wrap-around of the target
    for mode in (3, 2):
        for rand in (0x80000000, 0xFFFFFFFF, 0xFFFFFFD7, 0x80000029, 0xFFFFFFFE, 0x7FFFFFFF, 0xC0000000):
            for g4c in ((50, 0x7FFFFFF0) if rand & 1 else ((-30) & M32, 0x80000010)):
                if mode == 3:
                    e80, e98 = a_rules["equal"], anti_for_a(False)
                else:
                    e98, e80 = b_rules["equal"], anti_for_b(False)
                yield case(f"move mode {mode} rand {rand:#x} player {g4c:#x}", F_MOVE,
                           move_setup(mode, rand, g4c, 40, 3, [1, 0], e80, e98))
    # the coordinates reach the tile lookup clamped, partly clamped and in range
    for mode in (3, 0):
        for g4c, y_base, y_extra in ((-100 & M32, 10, 0), (200, 10, 0), (60, -50 & M32, 3), (60, 300, 3), (-100 & M32, 300, 0),
                                     (60, -1 & M32, 0), (60, 126, 0), (60, 127, 0), (60, 128, 0), (60, 20, 0x80000000), (60, 20, 0x7FFFFFFF)):
            if mode == 3:
                e80, e98 = a_rules["equal"], anti_for_a(False)
            else:
                e98, e80 = b_rules["equal"], anti_for_b(False)
            yield case(f"move mode {mode} coordinates {g4c & M32:#x} {y_base & M32:#x} {y_extra:#x}", F_MOVE,
                       move_setup(mode, 12, g4c, y_base, y_extra, [0, 2, 0], e80, e98))
    # the fourth lookup finds an empty cell (no call); y is a multiple of 16 so the cell above differs
    for mode in (3, 0):
        if mode == 3:
            e80, e98 = a_rules["equal"], anti_for_a(False)
        else:
            e98, e80 = b_rules["equal"], anti_for_b(False)
        for script in ([1], [0, 2], [0, 0, 3]):
            yield case(f"move mode {mode} empty cell above, tiles {script}", F_MOVE,
                       move_setup(mode, 11, 55, 31, 0, script, e80, e98, hole_row=True))
    # the actor's world pointer changes while the lookups run: every lookup re-reads it, y is computed once
    for mode in (3, 0):
        if mode == 3:
            e80, e98 = a_rules["equal"], anti_for_a(False)
        else:
            e98, e80 = b_rules["equal"], anti_for_b(False)
        for script, swap in (([1, 0], 1), ([0, 2, 0], 1), ([0, 2, 0], 2), ([0, 0, 3, 0], 1), ([0, 0, 3, 0], 2), ([0, 0, 3, 0], 3)):
            yield case(f"move mode {mode} world replaced after lookup {swap}, tiles {script}", F_MOVE,
                       move_setup(mode, 17, 50, 40, 3, script, e80, e98, swap_after=swap))
    # what the walk does after a clear path: mode, flip flag, mirror sentinels
    after_bits = [0, 2, 3, 0xFFFFFFFD, 0xFFFFFFFF, 1, 0x12]
    for mode in (3, 2, 0, 1, 4, M32):
        for s40 in after_bits:
            if mode in (1, 4, M32) and s40 not in (0, 2):
                continue
            for sent in ((0, 0, 0), (1, 1, 1)) if s40 in (0, 2) else ((0, 0, 0),):
                if mode == 3:
                    e80, e98 = a_rules["equal"], anti_for_a(False)
                else:
                    e98, e80 = b_rules["equal"], anti_for_b(False)
                yield case(f"move after mode {mode:#x} s40 {s40:#x} sent {sent}", F_MOVE,
                           move_setup(mode, rs.randrange(0, 0x8000), rs.randrange(10, 70), rs.randrange(8, 90), rs.randrange(0, 12),
                                      [1, 0], e80, e98, s40=s40, sent=sent))
    for sent in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (0, 1, 1), (1, 0, 1)):
        for mode in (2, 0):
            yield case(f"move mirror sentinels {sent} mode {mode}", F_MOVE,
                       move_setup(mode, 9, 40, 50, 1, [1, 0], b_rules["equal"], anti_for_b(False),
                                  s40=2 if mode == 0 else 0, sent=sent))
    for param in (0, 1):
        for mode in (3, 0):
            yield case(f"move animation parameter {'null' if param == 0 else 'set'} mode {mode}", F_MOVE,
                       move_setup(mode, 3, 44, 33, 2, [1, 0], a_rules["equal"] if mode == 3 else anti_for_b(False),
                                  anti_for_a(False) if mode == 3 else b_rules["equal"], params={0x308: param}))
    for _ in range(12):
        mode = rs.choice((3, 3, 2, 0, 1))
        script = rs.choice(list(scripts.values()))
        rand = rs.getrandbits(15)
        g4c = rs.randrange(0, 100)
        if mode == 3:
            e80, e98 = a_rules["equal"], anti_for_a(False)
        else:
            e98, e80 = b_rules["equal"], anti_for_b(False)
        yield case(f"move random mode {mode}", F_MOVE,
                   move_setup(mode, rand, g4c, rs.randrange(0, 120), rs.randrange(0, 15), script, e80, e98,
                              s40=rs.getrandbits(32), sent=(rs.randrange(2), rs.randrange(2), rs.randrange(2))))
