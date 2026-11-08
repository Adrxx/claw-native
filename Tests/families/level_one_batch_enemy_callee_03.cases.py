"""Cases for level_one_batch_enemy_callee_03: Level 1 enemy shared helpers 0x43f120, 0x43fe60, 0x43ffa0, 0x404eb0, 0x404ed0, 0x404f00, 0x420370.

Coverage is by deterministic enumeration; the random source only varies data
(field contents, doubles, rand outputs inside a branch class).
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

F_43F120, F_43FE60, F_43FFA0 = 0x43F120, 0x43FE60, 0x43FFA0
F_404EB0, F_404ED0, F_404F00, F_420370 = 0x404EB0, 0x404ED0, 0x404F00, 0x420370
RAND, PLAY_AUDIO = 0x4A3050, 0x4B45F0
TREE = 0x537668
G_FLAG, G_AUDIO_ON, G_AUDIO_ARG, G_TIME = 0x537E88, 0x532C0C, 0x532C10, 0x537210
G_ACTORS = 0x53C9A4
STR_43F120, STR_404ED0, STR_404F00, STR_43FFA0, STR_43FE60 = 0x5234F4, 0x5234EC, 0x523148, 0x524418, 0x5240E8
ALL_STRINGS = (STR_43F120, STR_404ED0, STR_404F00, STR_43FFA0, STR_43FE60)
CONST_LO, CONST_HI = 0x50DBA0, 0x50DBC0


def noise(rs, n):
    return bytes(rs.randrange(1, 256) for _ in range(n))


def w32(rs):
    return rs.randrange(0x100, 0x7FFFFFF0)


def dbl(x):
    return struct.unpack("<II", struct.pack("<d", x))


# ---------------------------------------------------------------- name tree at 0x537668

def build_tree(env, rs, kind, string):
    """Install a name tree at the global lookup object; return the value a hit would give."""
    key = env.cstr(string)
    if isinstance(key, str):
        key = key.encode("latin-1")
    value = w32(rs)
    root = 0
    keyobj = lambda data: env.object(len(data) + 8, "key", data=data + b"\0" * 8)
    node = lambda: env.object(0x14, "node", data=noise(rs, 0x14))
    if kind == "empty":
        root = 0
    elif kind == "far":  # bit index beyond the key
        root = node(); env.put(root + 8, 0x1000)
    elif kind in ("hit", "hit-bit3", "hit-last"):
        root = node()
        bit = {"hit": 0, "hit-bit3": 3, "hit-last": len(key) * 8 + 7}[kind]
        env.put(root, root, root, bit, keyobj(key), value)
    elif kind.startswith("miss"):
        data = bytearray(key)
        pos, delta = {"miss-lo0": (0, -1), "miss-hi0": (0, 1), "miss-lo1": (1, -1), "miss-hi1": (1, 1),
                      "miss-lo2": (2, -1), "miss-hi3": (3, 1)}.get(kind, (0, 1))
        if kind == "miss-short":
            data = data[:-1]
        elif kind == "miss-long":
            data = data + b"x"
        elif pos < len(data):
            data[pos] = max(1, min(255, data[pos] + delta))
        root = node()
        env.put(root, root, root, 0, keyobj(bytes(data)), value)
    elif kind == "null":  # chosen child is null
        root = node(); env.put(root, 0, 0, 0, keyobj(key), value)
    elif kind == "deep":  # two-level: root at bit 0, child at bit 3 pointing back
        child = node(); env.put(child, child, child, 3, keyobj(key), value)
        root = node(); env.put(root, child, child, 0, keyobj(b"zz"), value ^ 0x55)
    elif kind == "deep-null":
        child = node(); env.put(child, 0, 0, 3, keyobj(key), value)
        root = node(); env.put(root, child, child, 0, keyobj(b"zz"), value ^ 0x55)
    elif kind == "deep-far":
        child = node(); env.put(child, child, child, 0x2000, keyobj(key), value)
        root = node(); env.put(root, child, child, 0, keyobj(b"zz"), value ^ 0x55)
    elif kind == "decoy":  # key belongs to another function's string
        others = [s for s in ALL_STRINGS if s != string]
        other = env.cstr(others[value % len(others)])
        if isinstance(other, str):
            other = other.encode("latin-1")
        root = node(); env.put(root, root, root, 0, keyobj(other), value)
    else:
        raise ValueError(kind)
    env.put(TREE + 0x18, root)
    # look-up bookkeeping fields start with distinct stale contents
    env.put(TREE + 0x1C, w32(rs), w32(rs), w32(rs), w32(rs), w32(rs))
    return value


TREE_KINDS = ("empty", "far", "hit", "hit-bit3", "hit-last", "miss-lo0", "miss-hi0", "miss-lo1", "miss-hi1",
              "miss-lo2", "miss-hi3", "miss-short", "miss-long", "null", "deep", "deep-null", "deep-far", "decoy")
TREE_SMALL = ("empty", "hit", "miss-lo0", "miss-hi1", "deep", "decoy")


# ---------------------------------------------------------------- the enemy object

DEFAULTS = dict(
    count=0, tree="hit", string=STR_43F120,
    a64=0x2134, r1=3, r2=4, flag=1, audio_on=1, b_d0=2, e18c=3,
    world=None, d3a4=1, d3a8=1, d3ac=1, d3b0=1, d3b8=1, p368=1, p36c=1, p374=1,
)


def play_object(env, rs):
    obj = env.object(0x20, "audio-voice", data=noise(rs, 0x20))
    env.put(obj + 0x10, env.object(0x10, "audio-receiver", data=noise(rs, 0x10)))
    return obj


def list_object(env, rs):
    """A list header whose first element is an object with a word at +0x1c (what 0x4c8220 reads)."""
    element = env.object(0x30, "element", data=noise(rs, 0x30))
    array = env.object(8, "array", data=noise(rs, 8)); env.put(array, element)
    header = env.object(0x20, "list", data=noise(rs, 0x20))
    env.put(header + 0xC, array); env.put(header + 0x10, 1 + rs.randrange(3))
    return header


def enemy_setup(rs, **given):
    o = dict(DEFAULTS); o.update(given)

    def setup(env):
        this = env.object(0x400, "enemy", data=noise(rs, 0x400))
        a = env.object(0x100, "actor", data=noise(rs, 0x100))
        b = env.object(0xE0, "actor-b", data=noise(rs, 0xE0))
        c = env.object(0x30, "name-slot", data=noise(rs, 0x30))
        d = env.object(0x1C0, "anim", data=noise(rs, 0x1C0))
        env.put(this + 0xC, a); env.put(this + 0x10, c); env.put(this + 0x12C, d)
        env.put(a + 0x74, b); env.put(a + 0x64, o["a64"]); env.put(b + 0xD0, o["b_d0"])
        env.put(this + 0x18C, o["e18c"])
        for off, key in ((0x3A4, "d3a4"), (0x3A8, "d3a8"), (0x3AC, "d3ac"), (0x3B0, "d3b0"), (0x3B8, "d3b8")):
            env.put(this + off, play_object(env, rs) if o[key] else 0)
        for off, key in ((0x368, "p368"), (0x36C, "p36c"), (0x374, "p374")):
            env.put(this + off, list_object(env, rs) if o[key] else 0)
        count = o["count"]
        env.put(this + 0x2FC, count)
        if count > 0x20:
            words = env.object(4 * ((count + 31) // 32) + 8, "bits", data=noise(rs, 4 * ((count + 31) // 32) + 8))
            env.put(this + 0x300, words)
        else:
            env.put(this + 0x300, w32(rs) & ~0x11 | 0x20000000)
        env.put(this + 0x2F4, 0, 0)
        if o["world"] is not None:
            install_world(env, rs, flag="none" if not o["flag"] else "plain", **o["world"])
        else:
            env.put(G_FLAG, o["flag"])
        env.put(G_AUDIO_ON, o["audio_on"]); env.put(G_AUDIO_ARG, w32(rs))
        env.put(G_TIME, w32(rs))
        build_tree(env, rs, o["tree"], o["string"])
        env.override(RAND, sequence(o["r1"], o["r2"], o["r2"] + 1))
        env.override(PLAY_AUDIO, sequence(0x11111111, 0x22222222, 0x33333333))
        return {"this": this}

    return setup


def case(label, function, setup, arguments=()):
    return Case(label, function, setup, receiver=lambda t: t["this"], arguments=arguments)


# ---------------------------------------------------------------- 0x420370 (cdecl, no receiver)

SOUND_STRINGS = (0x524E04, 0x524DF8, 0x524DEC, 0x524DE0, 0x524DD4, 0x524DC8, 0x524DB8, 0x524DA8, 0x524D98, 0x524D88)


def string_hash(data):
    h = 0
    for ch in data:
        h = (h * 0x21 + (ch - 256 if ch > 127 else ch)) & 0xFFFFFFFF
    return h


def install_world(env, rs, flag="plain", keys=SOUND_STRINGS, with_p6c=True, g9a0=0, buckets=7):
    """The global actor object (0x53c9a4) with a hash map of named sounds, and the player flag object (0x537e88).

    flag: 'none' (0), 'plain', or a state word held in the flag object's slot.
    Each sound name maps to a distinct value so a wrong name shows up in the actor's published word."""
    actors = env.object(0x200, "actors", data=noise(rs, 0x200))
    holder = env.object(0x40, "holder", data=noise(rs, 0x40))
    registry = env.object(0x40, "registry", data=noise(rs, 0x40))
    table = env.object(buckets * 4, "buckets", data=b"\0" * (buckets * 4))
    slots = [0] * buckets
    values = {}
    for key in keys:
        raw = env.cstr(key)
        raw = raw.encode("latin-1") if isinstance(raw, str) else bytes(raw)
        value = env.object(0x10, "sound", data=noise(rs, 0x10))
        values[key] = value
        name = env.object(len(raw) + 4, "name", data=raw + b"\0\0\0\0")
        node = env.object(0x10, "map-node")
        index = string_hash(raw) % buckets
        env.put(node, slots[index], 0, name, value)
        slots[index] = node
    env.put(table, *slots)
    env.put(registry + 0x10 + 0x4, table); env.put(registry + 0x10 + 0x8, buckets)
    env.put(holder + 0x28, registry)
    env.put(actors + 0xC, holder)
    state = env.object(0x20, "actor-state", data=noise(rs, 0x20)) if with_p6c else 0
    env.put(actors + 0x6C, state)
    env.put(G_ACTORS, actors); env.put(0x53C9A0, g9a0)
    if flag == "none":
        env.put(G_FLAG, 0)
    else:
        player = env.object(0x100, "player", data=noise(rs, 0x100))
        pstate = env.object(0x30, "player-state", data=noise(rs, 0x30))
        env.put(player + 0x6C, pstate)
        env.put(pstate + 0x1C, 0x1234 if flag == "plain" else flag)
        env.put(G_FLAG, player)
    return values


def sound_setup(rs, flag, rands, world=None):
    """flag: 0 for the zero flag, otherwise an arbitrary non-zero word (no actor world) or, with a world, its state."""
    def setup(env):
        if world is None:
            env.put(G_FLAG, flag)
            env.put(G_ACTORS, 0)
        else:
            install_world(env, rs, flag=("none" if not flag else world.get("state", "plain")),
                          **{k: v for k, v in world.items() if k != "state"})
        env.override(RAND, sequence(*rands))
        return {}
    return setup


def cases(random_source):
    rs = random_source

    # ---- 0x420370: every selector class and every jump table entry
    for flag in (0, 1):
        for arg in (0, 1, 2, 3, 0x20, 0x21, 0x1F, 0xFFFFFFFE, 0x80000002):
            yield Case(f"snd flag={flag:#x} arg={arg:#x}", F_420370, sound_setup(rs, flag, (7,)), arguments=(arg,))
    for arg in (2, 0x20):
        for r in list(range(0, 10)) + [10, 19, 0x7FFF, 0x4000 + 9, -1, -7, -10, -19]:
            yield Case(f"snd arg={arg:#x} rand={r}", F_420370, sound_setup(rs, 1, (r,)), arguments=(arg,))
    # with a real actor world every table entry publishes its own sound
    for r in range(10):
        yield Case(f"snd world rand={r}", F_420370, sound_setup(rs, 1, (r + 10 * rs.randrange(0, 50),), world={}), arguments=(2,))
    for r in (0, 9):
        yield Case(f"snd world arg32 rand={r}", F_420370, sound_setup(rs, 1, (r,), world={}), arguments=(0x20,))
    for state in (0x1C, 0x138D, 0x138C, 0x138B):
        yield Case(f"snd world state={state:#x}", F_420370, sound_setup(rs, 1, (3,), world={"state": state}), arguments=(2,))
    yield Case("snd world no actor state", F_420370, sound_setup(rs, 1, (4,), world={"with_p6c": False}), arguments=(2,))
    yield Case("snd world busy", F_420370, sound_setup(rs, 1, (5,), world={"g9a0": 1}), arguments=(2,))
    yield Case("snd world sound missing", F_420370, sound_setup(rs, 1, (6,), world={"keys": SOUND_STRINGS[:6]}), arguments=(2,))
    yield Case("snd world sound missing 2", F_420370, sound_setup(rs, 1, (8,), world={"keys": SOUND_STRINGS[:6]}), arguments=(0x20,))
    yield Case("snd world one bucket", F_420370, sound_setup(rs, 1, (9,), world={"buckets": 1}), arguments=(2,))
    yield Case("snd world 64 buckets", F_420370, sound_setup(rs, 1, (2,), world={"buckets": 64}), arguments=(2,))
    for _ in range(3):
        yield Case("snd world random", F_420370, sound_setup(rs, 1, (rs.randrange(0, 0x7FFF),), world={"buckets": rs.randrange(1, 40)}),
                   arguments=(rs.choice((2, 0x20)),))

    # ---- 0x404eb0: virtual call then 0x440e20
    def virtual_setup(rs, rands=(0, 0), flag_138=0x1234, gate="map-empty", cur=None, window=None):
        def setup(env):
            this = env.object(0x200, "enemy", data=noise(rs, 0x200))
            vtable = env.object(0x80, "vtable", data=noise(rs, 0x80))
            actor = env.object(0x180, "actor", data=noise(rs, 0x180))
            inner = env.object(0x40, "inner", data=noise(rs, 0x40))
            param = env.object(0x200, "param", data=noise(rs, 0x200))
            env.put(this, vtable); env.put(this + 0xC, actor)
            env.put(actor + 0xC, inner); env.put(actor + 0x64, w32(rs))
            lo, hi = window or (rs.randrange(-300, 0), rs.randrange(0, 300))
            env.put(actor + 0x12C, lo); env.put(actor + 0x134, hi)
            env.put(this + 0x68, *dbl(rs.uniform(-500, 500))); env.put(this + 0x70, *dbl(rs.uniform(-500, 500)))
            env.put(param + 0x138, flag_138)
            env.put(param + 0x13C, rs.randrange(-200, 200)); env.put(param + 0x144, rs.randrange(-200, 200))
            env.put(param + 0x50, rs.randrange(-200, 200))
            if cur is not None:
                env.put(param + 0x13C, cur); env.put(param + 0x144, cur); env.put(param + 0x50, 0)
            # 0x461a00 gates: actor+0x38 == -1, actor flag 0x10000, then a hash-map lookup that finds nothing
            if gate == "stop38":
                env.put(actor + 0x38, 0xFFFFFFFF)
            else:
                env.put(actor + 0x38, 5)
                env.put(actor + 0x8, 0x10000 if gate == "stop-flag" else 0x2)
            level = env.object(0x20, "level", data=noise(rs, 0x20))
            env.put(inner + 0x8, level)
            registry = env.object(0x40, "registry", data=noise(rs, 0x40))
            env.put(level + 0xC, registry)
            maps = env.object(0x40, "maps", data=noise(rs, 0x40))
            env.put(registry + 0x14, maps)
            env.put(maps + 0x14, env.object(20, "buckets", data=b"\0" * 20) if gate == "map-empty" else 0, 5)

            def vslot(env, call):
                env.put(this + 0x1F0, call.receiver, call.arguments[0], env.calls_so_far(call.function))
                return 0x5151

            env.put(vtable + 0x28, env.stub("virtual slot 0x28", "thiscall", 1, vslot))
            env.override(RAND, sequence(*rands))
            return {"this": this, "param": param}
        return setup

    def virt(label, **kw):
        return Case(label, F_404EB0, virtual_setup(rs, **kw), receiver=lambda t: t["this"], arguments=(lambda t: t["param"],))

    for flag in (0x80000000, 0x1234):
        for rands in ((0, 0), (8, 8), (3, 5), (0x7FFF, 0x4001)):
            yield virt(f"virtual flag={flag:#x} rands={rands}", rands=rands, flag_138=flag)
    for gate in ("stop38", "stop-flag", "map-empty", "map-nobuckets"):
        yield virt(f"virtual gate {gate}", gate=gate, rands=(rs.randrange(0x7FFF), rs.randrange(0x7FFF)))
    for _ in range(3):
        yield virt("virtual random", rands=(rs.randrange(0x7FFF), rs.randrange(0x7FFF)), flag_138=rs.choice((0x80000000, 7)),
                   gate=rs.choice(("stop38", "stop-flag", "map-empty")))
    # clamp branches: current value below / above / inside the window
    for lo, hi, cur in ((100, 200, 1000), (100, 200, -1000), (100, 200, 150), (-100, 100, 0)):
        yield virt(f"virtual clamp {lo},{hi},{cur}", rands=(4, 4), window=(lo, hi), cur=cur)

    # ---- 0x404ed0 and 0x404f00: lookup and publish
    for fn, string in ((F_404ED0, STR_404ED0), (F_404F00, STR_404F00)):
        for kind in TREE_KINDS:
            yield case(f"{fn:#x} tree {kind}", fn, enemy_setup(rs, tree=kind, string=string))
        for _ in range(4):
            yield case(f"{fn:#x} random hit", fn, enemy_setup(rs, tree=rs.choice(("hit", "deep", "decoy")), string=string))

    # ---- 0x43ffa0
    for kind in TREE_KINDS:
        yield case(f"43ffa0 tree {kind}", F_43FFA0, enemy_setup(rs, tree=kind, string=STR_43FFA0))
    for d3b8 in (0, 1):
        for audio_on in (0, 1):
            for p368 in (0, 1):
                yield case(f"43ffa0 voice={d3b8} audio={audio_on} list={p368}", F_43FFA0,
                           enemy_setup(rs, tree="hit", string=STR_43FFA0, d3b8=d3b8, audio_on=audio_on, p368=p368))
    for _ in range(4):
        yield case("43ffa0 random", F_43FFA0, enemy_setup(rs, tree=rs.choice(TREE_SMALL), string=STR_43FFA0,
                                                         d3b8=rs.randrange(2), audio_on=rs.randrange(2), p368=rs.randrange(2)))

    # ---- 0x43fe60 (float path)
    values40 = (0.0, -0.0, 1.5, -2.25, 9.0)
    values58 = (0.0, 2.5, -4.0, 17.0)
    values70 = (0.0, 3.5, -1.25, 100.5, 1000.0)
    values50 = (6.5, -3.0, 0.0)

    def fe60(label, tree, v40, v58, v70, v50, p36c=1):
        base = enemy_setup(rs, tree=tree, string=STR_43FE60, p36c=p36c)

        def setup(env):
            tokens = base(env)
            this = tokens["this"]
            env.put(this + 0x40, *dbl(v40)); env.put(this + 0x50, *dbl(v50))
            env.put(this + 0x58, *dbl(v58)); env.put(this + 0x70, *dbl(v70))
            env.put(this + 0x60, w32(rs), w32(rs)); env.put(this + 0xB8, w32(rs), w32(rs))
            return tokens
        return case(label, F_43FE60, setup)

    for v40 in values40:
        for v70 in values70:
            for v58 in values58:
                yield fe60(f"43fe60 {v40} {v58} {v70}", "hit", v40, v58, v70, 6.5)
    for v50 in values50:
        yield fe60(f"43fe60 v50={v50}", "miss-lo0", 2.5, 3.0, 40.0, v50)
    for kind in TREE_KINDS:
        yield fe60(f"43fe60 tree {kind}", kind, 1.5, -4.0, 20.0, 6.5)
    yield fe60("43fe60 no list", "hit", 1.5, 3.0, 20.0, 6.5, p36c=0)
    for _ in range(12):
        yield fe60("43fe60 random", rs.choice(TREE_SMALL), rs.uniform(-20, 20), rs.uniform(-20, 20),
                   rs.uniform(-300, 300), rs.uniform(-9, 9), p36c=rs.randrange(2))

    # ---- 0x43f120
    base = dict(string=STR_43F120)
    sel_cases = []
    for sel in (0, 1, 2, 3, 4, 0xFFFFFFFF):
        for count in (0, 1, 4, 5, 0x20, 0x21, 0x41):
            sel_cases.append((sel, count))
    for sel, count in sel_cases:
        yield case(f"43f120 sel={sel:#x} count={count:#x}", F_43F120, enemy_setup(rs, count=count, **base), (sel,))
    for kind in TREE_KINDS:
        yield case(f"43f120 tree {kind}", F_43F120, enemy_setup(rs, tree=kind, **base), (0,))
    for kind in TREE_SMALL:
        yield case(f"43f120 tree {kind} sel1", F_43F120, enemy_setup(rs, tree=kind, **base), (1,))
    # selector 0 branches
    for a64 in (0x2134, 0x2133, 0, 0x2135):
        yield case(f"43f120 a64={a64:#x}", F_43F120, enemy_setup(rs, a64=a64, **base), (0,))
    for r1 in (0, 24, 25, 99, 124, 125, 0x7FFF, -1, -24, -25, -100):
        for b_d0 in (2, 0x20, 3, 0):
            yield case(f"43f120 r1={r1} b_d0={b_d0}", F_43F120, enemy_setup(rs, r1=r1, b_d0=b_d0, **base), (0,))
    for r2 in range(10):
        yield case(f"43f120 world sound {r2}", F_43F120, enemy_setup(rs, r1=0, r2=r2, b_d0=2, world={}, **base), (0,))
    yield case("43f120 world sound arg32", F_43F120, enemy_setup(rs, r1=0, r2=4, b_d0=0x20, world={}, **base), (0,))
    for flag in (0, 1):
        yield case(f"43f120 flag={flag}", F_43F120, enemy_setup(rs, r1=0, flag=flag, **base), (0,))
    for d3a4 in (0, 1):
        for audio_on in (0, 1):
            yield case(f"43f120 sel0 d3a4={d3a4} audio={audio_on}", F_43F120,
                       enemy_setup(rs, r1=50, d3a4=d3a4, audio_on=audio_on, **base), (0,))
    for e18c in (3, 2, 0, 4, 0xFFFFFFFF):
        yield case(f"43f120 e18c={e18c:#x}", F_43F120, enemy_setup(rs, e18c=e18c, **base), (0,))
    for p374 in (0, 1):
        yield case(f"43f120 p374={p374}", F_43F120, enemy_setup(rs, p374=p374, **base), (0,))
    # selectors 1..3: optional voices and the audio switch
    for sel, key in ((1, "d3b0"), (2, "d3a8"), (3, "d3ac")):
        for voice in (0, 1):
            for audio_on in (0, 1):
                for count in (0, 6):
                    yield case(f"43f120 sel={sel} {key}={voice} audio={audio_on} count={count}", F_43F120,
                               enemy_setup(rs, count=count, audio_on=audio_on, **{key: voice}, **base), (sel,))
    # random full combinations
    for _ in range(30):
        yield case("43f120 random", F_43F120, enemy_setup(
            rs, count=rs.choice((0, 2, 4, 5, 9, 0x20, 0x21, 0x50)), tree=rs.choice(TREE_KINDS), string=STR_43F120,
            a64=rs.choice((0x2134, rs.randrange(1, 0x10000))), r1=rs.randrange(-300, 0x7FFF), r2=rs.randrange(0, 0x7FFF),
            flag=rs.randrange(2), audio_on=rs.randrange(2), b_d0=rs.choice((2, 0x20, rs.randrange(0, 60))),
            e18c=rs.choice((3, rs.randrange(0, 8))), d3a4=rs.randrange(2), d3a8=rs.randrange(2), d3ac=rs.randrange(2),
            d3b0=rs.randrange(2), p374=rs.randrange(2)), (rs.choice((0, 1, 2, 3, 4)),))
