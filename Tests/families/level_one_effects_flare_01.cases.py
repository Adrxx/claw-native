"""Cases for level_one_effects_flare_01: Level 1 Flare effect.

Every scenario is deterministic; the random source only adds extra draws on top
(object contents, table sizes, index ranges, key values).

Object map used throughout:
  P (the "actor" object, 0x200 bytes): +0x0c -> Q (table directory), +0x6c -> LGC (logic state),
      +0x70 / +0x78 slot objects, +0x170 animation container, +0x188 animation state S.
  Q: +0x10 -> R1 (flare container table), +0x14 -> R3 (LogicHit/LogicAttack table), +0x2c -> R2 (frame list table)
  A table lives at R + 0x10: buckets pointer at R + 0x14, bucket count at R + 0x18.
  LGC: +0x18 -> sub object, +0x1c state word.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns  # noqa: F401

M = 0xFFFFFFFF

ENTRY = 0x457F00
CTOR = 0x458120
ON_ENTER = 0x4581C0
IDLE = 0x458530
TICK = 0x458570
SET_ALL = 0x4CE850
OPERATOR_NEW = 0x4F63EC

G_FLARE_MANAGER = 0x5371FC     # -> G, G+0x2c -> H, H+0x768 value
G_SPEED_2 = 0x5430B0
G_TICK_ARG = 0x5430C4
G_TRIE = 0x537668              # LS_ name table (trie object): +0x18 root
G_STR_LO, G_STR_HI, G_STR_BASE, G_STR_STRIDE = 0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0
G_CASE_FLAG = 0x540E00

STD_VTABLE = 0x513740          # slot 0x1c = 0x4c81b0 (release), slot 0x24 = 0x4c8160 (init)
FLARE_KEY = "GAME_LIGHTFX_FLARE"
HIT_KEY, ATTACK_KEY = "LogicHit", "LogicAttack"
IDLE_KEY = b"LS_IDLE"


# ---------------------------------------------------------------- generic helpers

def pad(count, seed):
    """Distinct non-zero words."""
    out, x = [], (seed * 2654435761 + 12345) & M
    for _ in range(count):
        x = (x * 1664525 + 1013904223) & M
        out.append(x | 0x01000001)
    return out


def junk(env, size, name, seed):
    return env.object(size, name, words=pad(size // 4, seed))


def cstring(env, text, name="string"):
    data = text.encode() if isinstance(text, str) else bytes(text)
    return env.object(len(data) + 8, name, data=data + b"\0")


def hash_bucket(key, buckets):
    h = 0
    for c in key.encode():
        h = (h * 0x21 + (c if c < 128 else c - 256)) & M
    return h % buckets


def recorder(log, tag, result=0):
    """Callback effect: writes (tag, receiver, arg0, arg1) into slot n of this tag's area of the log object."""
    def effect(env, call):
        n = env.calls_so_far(call.function)
        args = list(call.arguments) + [0, 0]
        env.put(log + tag * 0x40 + ((n - 1) % 4) * 16, 0xC0DE0000 + tag * 0x100 + n, call.receiver, args[0], args[1])
        return result
    return effect


def log_object(env):
    return env.object(0x400, "callback-log", fill=0)


# ---------------------------------------------------------------- hash tables, containers

def table(env, entries, buckets, seed, nobuckets=False):
    """Table object R; the table proper is R + 0x10. entries are (key, value); later ones sit nearer the chain head."""
    R = junk(env, 0x30, "table", seed)
    heads = [0] * buckets
    for key, value in entries:
        b = hash_bucket(key, buckets)
        heads[b] = env.object(0x10, "node", words=[heads[b], 0x5EED0000 + b + 1, cstring(env, key, "key"), value])
    arr = env.object(4 * buckets, "buckets", words=heads) if any(heads) else env.object(4 * buckets, "buckets", fill=0)
    env.put(R + 0x14, 0 if nobuckets else arr, buckets)
    return R


def lookup_table(env, key, value, mode, seed, buckets=7):
    """mode: found, chain (decoys ahead of the key), tail (key ahead of decoys), missing, empty, nobuckets."""
    decoys = [(key[:-1], 0x0DEC0001 + seed), (key + "X", 0x0DEC0002 + seed), (key.lower(), 0x0DEC0003 + seed)]
    if mode == "found":
        return table(env, [(key, value)], buckets, seed)
    if mode == "chain":
        return table(env, [(key, value)] + decoys, 1, seed)
    if mode == "tail":
        return table(env, decoys + [(key, value)], 1, seed)
    if mode == "missing":
        return table(env, decoys, 1, seed)
    if mode == "empty":
        return table(env, [], buckets, seed)
    if mode == "nobuckets":
        return table(env, [(key, value)], buckets, seed, nobuckets=True)
    raise ValueError(mode)


def entry(env, seed, kind="ok"):
    """A container entry E (+0x30 -> target S whose +0x14 and +0x1c are the fields being set)."""
    target = junk(env, 0x30, "target", seed + 1)
    e = junk(env, 0x40, "entry", seed + 2)
    env.put(e + 0x30, 0 if kind == "notarget" else target)
    return e


def container(env, lo, kinds, seed, hi=None, name="container"):
    """Container with index range lo..hi; kinds is a list of entry kinds ('ok', 'null', 'notarget')."""
    entries = [0 if k == "null" else entry(env, seed + 10 * i, k) for i, k in enumerate(kinds)]
    if len(kinds) > 2 and kinds[-1] == "ok":
        entries[1] = entries[-1] if kinds[1] == "ok" else entries[1]      # one entry shared twice
    hi = lo + len(kinds) - 1 if hi is None else hi
    slots = env.object(max(4, 4 * len(kinds)), name + "-slots", words=entries or [0])
    c = junk(env, 0x70, name, seed)
    env.put(c + 100, lo & M)
    env.put(c + 0x68, hi & M)
    env.put(c + 0x14, (slots - 4 * lo) & M)
    return c


def frame_list(env, count, seed):
    """Object V: +0x10 count (>= 1), +0xc -> array of frame pointers whose +0x1c is read."""
    frames = [junk(env, 0x40, "frame", seed + 5 * i) for i in range(count)]
    arr = env.object(4 * count, "frame-array", words=frames)
    v = junk(env, 0x30, "frame-list", seed)
    env.put(v + 0xC, arr)
    env.put(v + 0x10, count)
    return v


# ---------------------------------------------------------------- LS_ name trie at 0x537668

def keybit(index):
    return (IDLE_KEY[index >> 3] >> (index & 7)) & 1 if (index >> 3) < len(IDLE_KEY) else 0


def trie(env, path, target, leaf_key, value, seed, dead_at=None, dead_side=False):
    """Patricia nodes for the bit indices in `path`. The taken child of node k is node k+1; the taken child of the last
    node is node `target`, whose key is compared with LS_IDLE. dead_at: the taken child of that node is null."""
    nodes = [env.object(0x20, "trie-node", words=pad(8, seed + k)) for k in range(len(path))]
    keys = [cstring(env, leaf_key if k == target else f"LS_N{k}x", "trie-key") for k in range(len(path))]
    for k, node in enumerate(nodes):
        taken = nodes[k + 1] if k + 1 < len(path) else nodes[target]
        if dead_at == k:
            taken = 0
        other = env.object(0x20, "trie-decoy", words=[0, 0, 0, cstring(env, "LS_DECOY"), 0x0DEC0DEC + k, 0, 0, 0])
        left, right = (other, taken) if keybit(path[k]) else (taken, other)
        env.put(node, left, right, path[k], keys[k], value if k == target else 0xBAD00000 + k)
    return nodes[0]


def install_trie(env, root):
    env.put(G_TRIE + 0x18, root)
    env.put(G_TRIE + 0x1C, 0xA1A1A1A1, 0xA2A2A2A2, 0xA3A3A3A3, 0xA4A4A4A4)
    env.put(G_CASE_FLAG, 0)


# idle trie scenarios: label -> (path, target, leaf key, value, extra options)
TRIES = {
    "root bit 0 self leaf": ([0], 0, "LS_IDLE", 0x600D0001, {}),
    "root bit 2 right branch self leaf": ([2], 0, "LS_IDLE", 0x600D0002, {}),
    "root bit 63 limit": ([63], 0, "LS_IDLE", 0x600D0003, {}),
    "two level left": ([0, 9], 0, "LS_IDLE", 0x600D0004, {}),
    "two level target second": ([4, 9], 1, "LS_IDLE", 0x600D0005, {}),
    "three level mixed": ([2, 12, 33], 1, "LS_IDLE", 0x600D0006, {}),
    "three level to root": ([3, 6, 50], 0, "LS_IDLE", 0x600D0007, {}),
    "deep chain": ([0, 2, 3, 6, 9, 17, 40, 62], 5, "LS_IDLE", 0x600D0008, {}),
    "leaf smaller first byte": ([1, 5], 0, "AS_IDLE", 0x600D0009, {}),
    "leaf larger first byte": ([1, 5], 0, "ZS_IDLE", 0x600D000A, {}),
    "leaf differs at second byte": ([1, 5], 1, "LT_IDLE", 0x600D000B, {}),
    "leaf differs at fourth byte": ([2, 5], 1, "LS_XDLE", 0x600D000C, {}),
    "leaf is longer": ([2, 5], 1, "LS_IDLEX", 0x600D000D, {}),
    "leaf is shorter": ([2, 5], 1, "LS_IDL", 0x600D000E, {}),
    "leaf empty": ([2, 5], 1, "", 0x600D000F, {}),
    "bit index past the key": ([5, 70], 0, "LS_IDLE", 0x600D0010, {}),
    "bit index 64": ([64], 0, "LS_IDLE", 0x600D0011, {}),
    "taken child null at root": ([2, 9], 0, "LS_IDLE", 0x600D0012, {"dead_at": 0}),
    "taken child null at second": ([2, 9, 30], 0, "LS_IDLE", 0x600D0013, {"dead_at": 1}),
}


def idle_trie_setup(env, label, seed):
    if label == "empty trie":
        install_trie(env, 0)
        return
    path, target, leaf, value, options = TRIES[label]
    install_trie(env, trie(env, path, target, leaf, value, seed, **options))


# ---------------------------------------------------------------- the flare object and its actor

def flare_object(env, actor, logic, frames, seed):
    """The 0x4c-byte flare logic object, as the constructor leaves it."""
    o = junk(env, 0x4C, "flare", seed)
    env.put(o + 0x10, logic)
    env.put(o + 0x2C, actor)
    env.put(o + 0x48, frames)
    return o


def actor_object(env, seed, logic, container_pointer=None):
    p = junk(env, 0x200, "actor", seed)
    env.put(p + 0x6C, logic)
    if container_pointer is not None:
        env.put(p + 0x170, container_pointer)
    return p


def logic_object(env, seed, state=0, sub=0):
    lg = junk(env, 0x30, "logic", seed)
    env.put(lg + 0x18, sub)
    env.put(lg + 0x1C, state)
    return lg


def install_manager(env, value, seed):
    h = junk(env, 0x780, "manager-h", seed)
    env.put(h + 0x768, value)
    g = junk(env, 0x40, "manager-g", seed + 1)
    env.put(g + 0x2C, h)
    env.put(G_FLARE_MANAGER, g)
    env.put(G_SPEED_2, 0x000002B0 + seed)


# ================================================================ 0x4ce850: set the value on every target

def set_all_setup(lo, kinds, seed, hi=None):
    def setup(env):
        c = container(env, lo, kinds, seed, hi=hi)
        return {"c": c}
    return setup


def set_all(label, setup, value):
    return Case(label, SET_ALL, setup, receiver=lambda t: t["c"], arguments=(value,))


def set_all_cases(rnd):
    shapes = [
        ("single", 0, ["ok"]),
        ("two", 0, ["ok", "ok"]),
        ("five", 0, ["ok"] * 5),
        ("offset range", 3, ["ok"] * 4),
        ("negative start", -2, ["ok"] * 4),
        ("all negative", -3, ["ok"] * 3),
        ("null entries", 0, ["ok", "null", "ok", "null"]),
        ("no targets", 1, ["notarget", "ok", "notarget"]),
        ("only holes", 0, ["null", "notarget", "null"]),
        ("shared entry", 0, ["ok", "ok", "ok", "ok"]),
        ("large", 2, ["ok", "null", "notarget"] * 5),
    ]
    for name, lo, kinds in shapes:
        for value in (1, 0x12345678, 0xFFFFFFFF):
            yield set_all(f"set all {name} value {value:#x}", set_all_setup(lo, kinds, 100 + lo, hi=None), value)
    # zero value is ignored whatever the container holds
    for name, lo, kinds in shapes[:4]:
        yield set_all(f"set all {name} value zero", set_all_setup(lo, kinds, 200 + lo), 0)
    # empty and inverted ranges (hi below lo): nothing is touched and the count is zero
    for lo, hi in ((0, -1), (5, 4), (1, 0), (-1, -2), (0, -5), (7, 2)):
        yield set_all(f"empty range {lo}..{hi}", set_all_setup(lo, ["ok", "ok", "ok"], 300 + lo, hi=hi), 0x5A5A5A5A)
    # range shorter than the slot array: only lo..hi is visited
    for lo, count, hi in ((0, 6, 2), (2, 6, 4), (-1, 5, 0)):
        yield set_all(f"partial range {lo}..{hi}", set_all_setup(lo, ["ok"] * count, 400 + lo, hi=hi), 0x7000 + count)
    for i in range(40):
        lo = rnd.randrange(-6, 9)
        kinds = [rnd.choice(("ok", "ok", "ok", "null", "notarget")) for _ in range(rnd.randrange(1, 9))]
        value = rnd.randrange(1, M + 1)
        hi = lo + len(kinds) - 1 if rnd.random() < 0.8 else lo + rnd.randrange(-2, len(kinds))
        yield set_all(f"random set all {i}", set_all_setup(lo, kinds, rnd.randrange(1, 1000), hi=hi), value)


# ================================================================ 0x458530: back to idle

def idle_setup(label, seed, frames_count=0, same_logic=False, state_before=None):
    def setup(env):
        idle_trie_setup(env, label, seed)
        logic = logic_object(env, seed + 3, state=0x7E57BEEF if state_before is None else state_before)
        actor = actor_object(env, seed + 4, logic if same_logic else logic_object(env, seed + 5, 0x1234))
        frames = frame_list(env, frames_count, seed + 6) if frames_count else 0
        o = flare_object(env, actor, logic, frames, seed + 7)
        return {"o": o, "logic": logic, "actor": actor}
    return setup


def idle_cases(rnd):
    labels = ["empty trie"] + list(TRIES)
    for i, label in enumerate(labels):
        yield Case(f"idle {label}, no frames", IDLE, idle_setup(label, 500 + i), receiver=lambda t: t["o"])
        yield Case(f"idle {label}, frames", IDLE, idle_setup(label, 600 + i, frames_count=1 + i % 3),
                   receiver=lambda t: t["o"])
    for count in (1, 2, 5):
        yield Case(f"idle frames {count} same logic", IDLE, idle_setup("two level left", 700 + count, count, True),
                   receiver=lambda t: t["o"])
    for i in range(30):
        label = rnd.choice(labels)
        yield Case(f"random idle {i} {label}", IDLE,
                   idle_setup(label, rnd.randrange(1, 5000), rnd.randrange(0, 4), rnd.random() < 0.5,
                              rnd.randrange(0, M + 1)),
                   receiver=lambda t: t["o"])


# ================================================================ 0x4581c0: enter the flare

def enter_setup(seed, kinds=None, lo=0, hi=None, frames_count=0, trie_label="two level left", manager=0x4D4D0001,
                share_logic=False, container_none=False):
    def setup(env):
        env.put(G_TICK_ARG, 3)
        install_manager(env, manager, seed)
        idle_trie_setup(env, trie_label, seed + 1)
        logic = logic_object(env, seed + 2, state=0x51A7E000 + seed)
        a = 0 if container_none or kinds is None else container(env, lo, kinds, seed + 3, hi=hi)
        actor = actor_object(env, seed + 4, logic if share_logic else logic_object(env, seed + 5, 0x77), a)
        frames = frame_list(env, frames_count, seed + 6) if frames_count else 0
        o = flare_object(env, actor, logic, frames, seed + 7)
        return {"o": o, "actor": actor, "container": a, "logic": logic}
    return setup


def enter_cases(rnd):
    shapes = [
        ("no container", None, 0),
        ("one target", ["ok"], 0),
        ("two targets", ["ok", "ok"], 0),
        ("offset targets", ["ok"] * 4, 3),
        ("negative start", ["ok"] * 3, -2),
        ("with holes", ["ok", "null", "notarget", "ok"], 1),
        ("only holes", ["null", "notarget"], 0),
        ("many", ["ok"] * 7, -1),
    ]
    for i, (name, kinds, lo) in enumerate(shapes):
        for frames in (0, 1, 3):
            yield Case(f"enter {name}, frames {frames}", ON_ENTER,
                       enter_setup(800 + 10 * i + frames, kinds, lo, frames_count=frames, manager=0x4D4D0000 + i + 1),
                       receiver=lambda t: t["o"])
    for hi in (-1, 0, 1):
        yield Case(f"enter inverted range hi {hi}", ON_ENTER,
                   enter_setup(900 + hi, ["ok", "ok", "ok"], 2, hi=hi, frames_count=2), receiver=lambda t: t["o"])
    for manager in (0, 1, 0xFFFFFFFF):
        yield Case(f"enter manager value {manager:#x}", ON_ENTER,
                   enter_setup(950 + (manager & 7), ["ok", "ok"], 0, frames_count=1, manager=manager),
                   receiver=lambda t: t["o"])
    for i, label in enumerate(("empty trie", "root bit 2 right branch self leaf", "bit index past the key",
                               "deep chain", "taken child null at root", "leaf is longer")):
        yield Case(f"enter then idle trie {label}", ON_ENTER,
                   enter_setup(1000 + i, ["ok", "ok"], 0, frames_count=2, trie_label=label),
                   receiver=lambda t: t["o"])
    yield Case("enter shared logic object", ON_ENTER, enter_setup(1100, ["ok", "ok"], 0, frames_count=2, share_logic=True),
               receiver=lambda t: t["o"])
    for i in range(30):
        kinds = None if rnd.random() < 0.15 else [rnd.choice(("ok", "ok", "null", "notarget")) for _ in range(rnd.randrange(1, 7))]
        yield Case(f"random enter {i}", ON_ENTER,
                   enter_setup(rnd.randrange(1, 4000), kinds, rnd.randrange(-4, 6), frames_count=rnd.randrange(0, 4),
                               trie_label=rnd.choice(list(TRIES)), manager=rnd.randrange(0, M + 1),
                               share_logic=rnd.random() < 0.3),
                   receiver=lambda t: t["o"])


# ================================================================ 0x458570: advance the animation

FLOAT_ONE = 0x3F800000


def tick_state(env, seed, counter=0, flag=0, done=0, mode=None, frame_flags=0, kind=0, next_kind=0, owner_flags=0,
               has_anim=True, container_lo=0, anim_count=3, current=0):
    """Returns (actor, S): the animation state S at actor + 0x188."""
    lg = junk(env, 0x80, "sprite-logic", seed)
    cont = container(env, container_lo, ["ok", "ok", "ok"], seed + 30)
    env.put(lg + 0x170, cont)
    env.put(lg + 0x16C, (container_lo + 1) & M)
    env.put(lg + 0x40, owner_flags)
    frames = [junk(env, 0x40, "anim-frame", seed + 40 + 3 * i) for i in range(anim_count)]
    for i, f in enumerate(frames):
        env.put(f + 0x2C, 0)
        env.put(f + 0x04, frame_flags)
        env.put(f + 0x08, 0 if mode is None else mode)
        env.put(f + 0x0C, next_kind)
        env.put(f + 0x10, kind)
        env.put(f + 0x14, 3)
        env.put(f + 0x18, 0x2A + i)
        env.put(f + 0x20, 0x100 + 7 * i + 1)
        env.put(f + 0x24, 0x300 + 5 * i + 1)
    farr = env.object(4 * anim_count, "anim-array", words=frames)
    al = junk(env, 0x30, "anim-list", seed + 50)
    env.put(al + 0xC, farr)
    env.put(al + 0x10, anim_count)
    actor = junk(env, 0x200, "actor", seed + 60)
    s = actor + 0x188
    env.put(s + 4, lg)
    env.put(s + 8, al if has_anim else 0)
    env.put(s + 0xC, frames[current])
    env.put(s + 0x10, current)
    env.put(s + 0x14, counter)
    env.put(s + 0x18, flag)
    env.put(s + 0x1C, done)
    env.put(s + 0x20, 0x20D0 + seed)
    env.put(s + 0x24, 0x24D0 + seed)
    env.put(s + 0x28, FLOAT_ONE)
    return actor, s, lg, frames


def tick_setup(seed, param, **options):
    def setup(env):
        env.put(G_TICK_ARG, param)
        actor, s, lg, frames = tick_state(env, seed, **options)
        o = junk(env, 0x4C, "flare", seed + 70)
        env.put(o + 0x2C, actor)
        return {"o": o, "actor": actor}
    return setup


def tick_case(label, seed, param, **options):
    return Case(label, TICK, tick_setup(seed, param, **options), receiver=lambda t: t["o"])


def tick_cases(rnd):
    yield tick_case("tick without animation", 1200, 4, has_anim=False)
    yield tick_case("tick without animation param zero", 1201, 0, has_anim=False)
    for counter, flag in ((1, 0), (2, 0), (9, 0)):
        yield tick_case(f"tick countdown {counter} without flag", 1210 + counter, 5, counter=counter, flag=flag)
    for counter, param in ((5, 1), (5, 4), (5, 5), (5, 6), (1, 1), (3, 0), (2, 0xFFFFFFFF), (0xFFFFFFFF, 0x7FFFFFFF)):
        yield tick_case(f"tick flagged counter {counter} param {param:#x}", 1230 + counter + param % 17, param,
                        counter=counter, flag=1, done=1)
    yield tick_case("tick idle done", 1260, 2, done=1)
    yield tick_case("tick idle done flagged", 1261, 2, done=1, flag=3)
    for mode in (0, 4, 5):
        for kind in (0, 1, 2, 3):
            for next_kind in (9, 8, 0):
                if kind == 2 and mode == 5:
                    continue
                yield tick_case(f"tick body mode {mode} kind {kind} next {next_kind}",
                                1300 + mode * 100 + kind * 10 + next_kind, 2 + kind,
                                mode=mode, kind=kind, next_kind=next_kind,
                                frame_flags=kind & 1, owner_flags=2 if kind == 2 else 0)
    yield tick_case("tick body kind 2 owner flag clear", 1700, 2, mode=4, kind=2, next_kind=9, owner_flags=0)
    yield tick_case("tick body kind 2 owner flag set", 1701, 2, mode=4, kind=2, next_kind=9, owner_flags=2)
    yield tick_case("tick body flags bit 1", 1702, 2, mode=4, kind=1, next_kind=9, frame_flags=1)
    yield tick_case("tick body next frame last", 1703, 2, mode=4, kind=1, next_kind=0, current=2)
    yield tick_case("tick body empty animation", 1704, 2, mode=4, kind=1, next_kind=0, anim_count=1)
    for i in range(24):
        mode = rnd.choice((0, 4, 5))
        kind = rnd.randrange(0, 4)
        yield tick_case(f"random tick {i}", rnd.randrange(1, 9000), rnd.randrange(0, M + 1),
                        counter=rnd.choice((0, 0, rnd.randrange(1, 9))), flag=rnd.randrange(0, 2),
                        done=rnd.choice((0, 0, 1)), mode=mode, kind=kind, next_kind=rnd.choice((0, 8, 9)),
                        frame_flags=rnd.randrange(0, 8), owner_flags=rnd.choice((0, 2)),
                        current=rnd.randrange(0, 3), container_lo=rnd.randrange(-2, 4))


# ================================================================ 0x458120: construct

def slot_object(env, kind, log, seed, tag):
    """An existing slot object at P + 0x70 / 0x78."""
    if kind == "none":
        return 0
    obj = junk(env, 0x174, "slot", seed)
    if kind in ("std", "std-bare"):
        env.put(obj, STD_VTABLE)
        if kind == "std":
            buffer = junk(env, 0x40, "slot-buffer", seed + 1)
            child_vtable = env.object(0x10, "child-vtable", words=pad(4, seed + 2))
            env.put(child_vtable, env.stub("child-destructor", "thiscall", 1, recorder(log, tag + 2)))
            child = junk(env, 0x20, "slot-child", seed + 3)
            env.put(child, child_vtable)
            env.put(obj + 0x14, buffer)
            env.put(obj + 0x18, child)
        else:
            env.put(obj + 0x14, 0)
            env.put(obj + 0x18, 0)
    elif kind == "stub":
        vt = env.object(0x40, "slot-vtable", words=pad(16, seed + 4))
        env.put(vt + 0x1C, env.stub("slot-reset", "thiscall", 0, recorder(log, tag)))
        env.put(vt + 0x24, env.stub("slot-init", "thiscall", 2, recorder(log, tag + 1, result=0x1234)))
        env.put(obj, vt)
    else:
        raise ValueError(kind)
    return obj


def build_world(env, seed, hit="found", attack="found", flare="found", frames_mode="found", hit_value=0x40,
                attack_value=0x50, slot70="none", slot78="none", state=0, sub=0, container_kinds=("ok", "ok"),
                container_lo=0, frame_count=2, container_hi=None, t1_buckets=5, t2_buckets=3, manager=0x4D4D0099):
    """The actor P and everything the constructor and the state machine reach."""
    log = log_object(env)
    env.put(G_TICK_ARG, 2)
    install_manager(env, manager, seed + 100)
    idle_trie_setup(env, "two level left", seed + 101)
    hit_object = junk(env, 0x30, "hit-value", seed + 102)
    env.put(hit_object + 0x10, hit_value)
    attack_object = junk(env, 0x30, "attack-value", seed + 103)
    env.put(attack_object + 0x10, attack_value)
    a = container(env, container_lo, list(container_kinds), seed + 104, hi=container_hi)
    v = frame_list(env, frame_count, seed + 105)
    r1 = lookup_table(env, FLARE_KEY, a, flare, seed + 106, t1_buckets)
    r2 = lookup_table(env, FLARE_KEY, v, frames_mode, seed + 107, t2_buckets)
    r3_entries = []
    if hit in ("found", "chain", "tail"):
        r3_entries.append((HIT_KEY, hit_object))
    r3 = None
    # one table carries both keys; the mode of each key decides what surrounds it
    keys = []
    if hit != "missing" and hit != "nobuckets":
        keys.append((HIT_KEY, hit_object))
    if attack != "missing" and attack != "nobuckets":
        keys.append((ATTACK_KEY, attack_object))
    buckets = 1 if "chain" in (hit, attack) or "tail" in (hit, attack) else 6
    decoys = [("Logic", 0x0DEC0011 + seed), ("LogicHitX", 0x0DEC0012 + seed), ("logicattack", 0x0DEC0013 + seed)]
    if "chain" in (hit, attack):
        keys = keys + decoys
    elif "tail" in (hit, attack):
        keys = decoys + keys
    elif hit == "missing" or attack == "missing":
        keys = keys + decoys
    r3 = table(env, keys, buckets, seed + 108, nobuckets=("nobuckets" in (hit, attack)))
    q = junk(env, 0x40, "directory", seed + 109)
    env.put(q + 0x10, r1)
    env.put(q + 0x14, r3)
    env.put(q + 0x2C, r2)
    logic = logic_object(env, seed + 110, state=state, sub=sub)
    p = actor_object(env, seed + 111, logic)
    env.put(p + 0xC, q)
    env.put(p + 0x70, slot_object(env, slot70, log, seed + 112, 0))
    env.put(p + 0x78, slot_object(env, slot78, log, seed + 120, 4))
    return {"p": p, "log": log, "logic": logic, "container": a, "frames": v}


def ctor_setup(seed, **options):
    def setup(env):
        tokens = build_world(env, seed, **options)
        tokens["o"] = junk(env, 0x4C, "ctor-target", seed + 130)
        return tokens
    return setup


def ctor_case(label, seed, fail_from=None, **options):
    def setup(env):
        tokens = ctor_setup(seed, **options)(env)
        if fail_from is not None:
            env.override(OPERATOR_NEW, allocate(fail_from_call=fail_from))
        return tokens
    return Case(label, CTOR, setup, receiver=lambda t: t["o"], arguments=(lambda t: t["p"],))


def ctor_cases(rnd):
    modes = ("found", "chain", "tail", "missing", "empty", "nobuckets")
    slots = ("none", "std", "std-bare", "stub")
    seed = 2000
    for hit in ("found", "chain", "tail", "missing", "nobuckets"):
        for slot70 in slots:
            seed += 1
            yield ctor_case(f"ctor hit {hit} slot70 {slot70}", seed, hit=hit, attack="found", slot70=slot70)
    for attack in ("found", "chain", "tail", "missing", "nobuckets"):
        for slot78 in slots:
            seed += 1
            yield ctor_case(f"ctor attack {attack} slot78 {slot78}", seed, hit="found", attack=attack, slot78=slot78)
    for fail in (1, 2, 3):
        for slot in ("none", "std", "stub"):
            seed += 1
            yield ctor_case(f"ctor allocation fails from call {fail} slot {slot}", seed, fail_from=fail,
                            slot70=slot if fail == 1 else "none", slot78=slot if fail >= 2 else "none")
    for hit_value, attack_value in ((0, 0x50), (0x40, 0), (0, 0), (0xFFFFFFFF, 1)):
        seed += 1
        yield ctor_case(f"ctor values {hit_value:#x} {attack_value:#x} fresh slots", seed, hit_value=hit_value,
                        attack_value=attack_value)
        seed += 1
        yield ctor_case(f"ctor values {hit_value:#x} {attack_value:#x} existing slots", seed, hit_value=hit_value,
                        attack_value=attack_value, slot70="stub", slot78="std")
    for hit in ("empty",):
        seed += 1
        yield ctor_case("ctor hit table empty", seed, hit="missing", attack="missing")
    for i in range(24):
        yield ctor_case(f"random ctor {i}", rnd.randrange(1, 9000), fail_from=rnd.choice((None, None, 1, 2, 3)),
                        hit=rnd.choice(("found", "chain", "tail", "missing")),
                        attack=rnd.choice(("found", "chain", "tail", "missing")),
                        slot70=rnd.choice(slots), slot78=rnd.choice(slots),
                        hit_value=rnd.choice((0, rnd.randrange(1, M + 1))),
                        attack_value=rnd.choice((0, rnd.randrange(1, M + 1))))


# ================================================================ 0x457f00: the state machine

def entry_case(label, seed, fail_from=None, **options):
    def setup(env):
        tokens = build_world(env, seed, **options)
        if fail_from is not None:
            env.override(OPERATOR_NEW, allocate(fail_from_call=fail_from))
        return tokens
    return Case(label, ENTRY, setup, arguments=(lambda t: t["p"],))


def callback_sub(env, log, seed, slots):
    """A sub object whose vtable holds recording stubs at the given slot offsets."""
    vt = env.object(0x40, "sub-vtable", words=pad(16, seed))
    for offset, (argc, tag) in slots.items():
        env.put(vt + offset, env.stub(f"slot-{offset:#x}", "thiscall", argc, recorder(log, tag, result=0x700 + tag)))
    sub = junk(env, 0x30, "sub", seed + 1)
    env.put(sub, vt)
    return sub


def state_case(label, seed, state, slots, **options):
    def setup(env):
        tokens = build_world(env, seed, state=state, **options)
        sub = callback_sub(env, tokens["log"], seed + 200, slots)
        env.put(tokens["logic"] + 0x18, sub)
        tokens["sub"] = sub
        return tokens
    return Case(label, ENTRY, setup, arguments=(lambda t: t["p"],))


def string_table(env, log, seed, state, key, lo, hi, stride, refcount=1, capacity=0x20):
    """Everything the fallback state handler reads: the string slots, the key object and a recording vtable."""
    count = hi - lo + 1
    items = env.object(max(count * stride, 8), "string-slots", words=pad(max(count * stride, 8) // 4, seed))
    buffers = []
    for i in range(count):
        data = env.object(12 + 16, "string-data", words=pad(7, seed + 1 + i))
        env.put(data, refcount & M, 4, capacity)
        env.put(items + i * stride, data + 12)
        buffers.append(data + 12)
    env.put(G_STR_LO, lo & M)
    env.put(G_STR_HI, hi & M)
    env.put(G_STR_BASE, items)
    env.put(G_STR_STRIDE, stride)
    env.put(0x5376B4, 0xB4B4B4B4)
    env.put(0x5376B8, 0x3)
    keyholder = junk(env, 0x30, "key-holder", seed + 90)
    env.put(keyholder + 0x1C, key & M)
    vt = env.object(0x20, "sub-vtable", words=pad(8, seed + 91))
    env.put(vt + 4, env.stub("on-string", "thiscall", 1, recorder(log, 1, result=0x71)))
    env.put(vt + 8, env.stub("on-key", "thiscall", 1, recorder(log, 2, result=0x72)))
    env.put(vt + 0xC, env.stub("on-string-again", "thiscall", 1, recorder(log, 3, result=0x73)))
    sub = junk(env, 0x30, "sub", seed + 92)
    env.put(sub, vt)
    env.put(sub + 0x10, keyholder)
    return sub, buffers


def default_case(label, seed, state, key, lo, hi, stride, **options):
    def setup(env):
        tokens = build_world(env, seed, state=state, **options)
        sub, _ = string_table(env, tokens["log"], seed + 300, state, key, lo, hi, stride)
        env.put(tokens["logic"] + 0x18, sub)
        tokens["sub"] = sub
        return tokens
    return Case(label, ENTRY, setup, arguments=(lambda t: t["p"],))


def entry_cases(rnd):
    # ---- state zero: build the flare object
    seed = 3000
    for flare in ("found", "chain", "tail", "missing", "empty", "nobuckets"):
        for frames in ("found", "missing"):
            seed += 1
            yield entry_case(f"entry start flare {flare} frames {frames}", seed, flare=flare, frames_mode=frames)
    for kinds, lo, hi in ((["ok"], 0, None), (["ok", "ok", "ok"], 2, None), (["ok", "null", "notarget"], -1, None),
                          (["ok", "ok"], 3, 1), (["ok", "ok", "ok"], 0, 0)):
        seed += 1
        yield entry_case(f"entry start container {len(kinds)} lo {lo} hi {hi}", seed, container_kinds=kinds,
                         container_lo=lo, container_hi=hi)
    for hit in ("found", "missing", "chain"):
        for slot in ("none", "std", "stub"):
            seed += 1
            yield entry_case(f"entry start hit {hit} slot70 {slot}", seed, hit=hit, slot70=slot)
    for attack in ("found", "missing", "tail"):
        for slot in ("none", "std", "stub"):
            seed += 1
            yield entry_case(f"entry start attack {attack} slot78 {slot}", seed, attack=attack, slot78=slot)
    for frames in (1, 3):
        seed += 1
        yield entry_case(f"entry start frame count {frames}", seed, frame_count=frames)
    # allocation of the flare object itself succeeds; the slot allocations of the constructor fail
    for fail in (2, 3):
        seed += 1
        yield entry_case(f"entry start slot allocation fails from call {fail}", seed, fail_from=fail)
    for manager in (0, 0xFFFFFFFF):
        seed += 1
        yield entry_case(f"entry start manager value {manager:#x}", seed, manager=manager)
    # ---- states 0x1d and 0x1e: forward to the stored object
    for i, state in enumerate((0x1D, 0x1E)):
        offset = 0x20 if state == 0x1D else 0x1C
        other = 0x1C if state == 0x1D else 0x20
        for j in range(3):
            yield state_case(f"entry state {state:#x} forward {j}", 3500 + 10 * i + j, state,
                             {offset: (0, 1 + j), other: (0, 5), 0x10: (0, 6)})
    # ---- state 0x3e8: nothing happens
    for j in range(3):
        yield state_case(f"entry state 0x3e8 idle {j}", 3600 + j, 0x3E8, {0x10: (0, 1), 0x1C: (0, 2), 0x20: (0, 3)})
    # ---- every other state: the fallback handler
    states = [1, 2, 0x10, 0x1C, 0x1F, 0x20, 0x3E7, 0x3E9, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF]
    for i, state in enumerate(states):
        yield default_case(f"entry fallback state {state:#x} key at low end", 3700 + i, state, -3, -3, 2, 8)
        yield default_case(f"entry fallback state {state:#x} key at high end", 3750 + i, state, 4, 0, 4, 12)
    for key, lo, hi, stride in ((0, 0, 0, 4), (7, 3, 9, 4), (-1, -4, 1, 16), (100, 90, 110, 8)):
        yield default_case(f"entry fallback key {key} range {lo}..{hi} stride {stride}", 3800 + key % 50, 5, key, lo, hi,
                           stride)
    for i in range(20):
        lo = rnd.randrange(-5, 6)
        hi = lo + rnd.randrange(0, 6)
        yield default_case(f"random fallback {i}", rnd.randrange(1, 9000),
                           rnd.choice([1, 2, 0x1C, 0x1F, 0x3E7, 0x3E9, rnd.randrange(0x3EA, M)]),
                           rnd.randrange(lo, hi + 1), lo, hi, rnd.choice((4, 8, 12, 16)))
    for i in range(24):
        yield entry_case(f"random start {i}", rnd.randrange(1, 9000),
                         fail_from=rnd.choice((None, None, None, 2, 3)),
                         flare=rnd.choice(("found", "chain", "tail", "missing")),
                         frames_mode=rnd.choice(("found", "chain", "missing")),
                         hit=rnd.choice(("found", "chain", "tail", "missing")),
                         attack=rnd.choice(("found", "chain", "tail", "missing")),
                         slot70=rnd.choice(("none", "std", "std-bare", "stub")),
                         slot78=rnd.choice(("none", "std", "std-bare", "stub")),
                         container_kinds=[rnd.choice(("ok", "ok", "null", "notarget")) for _ in range(rnd.randrange(1, 5))],
                         container_lo=rnd.randrange(-3, 4), frame_count=rnd.randrange(1, 4),
                         manager=rnd.randrange(0, M + 1))


def cases(random_source):
    yield from set_all_cases(random_source)
    yield from idle_cases(random_source)
    yield from enter_cases(random_source)
    yield from tick_cases(random_source)
    yield from ctor_cases(random_source)
    yield from entry_cases(random_source)
