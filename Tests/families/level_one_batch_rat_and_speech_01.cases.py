"""Cases for level_one_batch_rat_and_speech_01: Level 1 Rat construction and update, batch 1."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

RAT_STATE = 0x47C850
RAT_CONSTRUCT = 0x47C910
RECT_FROM_SPRITE = 0x408050
FLIP_OFF = 0x406310
FLIP_ON = 0x4357A0
MIN_INT = 0x80000000
M32 = 0xFFFFFFFF
RAND, LOCK, REALLOC, NEW, MALLOC = 0x4A3050, 0x4A7BC0, 0x4A9070, 0x4F63EC, 0x4A48E0
INTERLOCKED, SET_RECT_EMPTY, SET_RECT = 0x5469E8, 0x546CDC, 0x546D5C
G_TICKS, G_STRING = 0x537210, 0x534938
G_RAND_SCALE, G_LOCALE = 0x5262B8, 0x540E00
GAME_NAMES = [b"GAME_SPLASH", b"GAME_HIT1", b"GAME_HIT2", b"GAME_HIT3", b"GAME_HIT4", b"GAME_PURELEASE1",
              b"GAME_EEHH", b"GAME_MOUSEKILL", b"GAME_NULL"]
WALK_NAMES = (b"LEVEL_RAT_WALK", b"LEVEL_RAT_IDLE", b"LEVEL_RAT_THROWSOUTH", b"LEVEL_RAT_THROWEASTWEST", b"LEVEL_RAT_DEAD")


def word(random_source, low=-2000, high=2000):
    return random_source.randrange(low, high) & 0xFFFFFFFF


# ---- 0x408050 -------------------------------------------------------------------------------------------
def rect_setup(rects):
    def setup(env):
        obj = env.object(0x180, "sprite-owner", fill=0xA5)
        rect = 0
        if rects is not None:
            rect = env.object(0x30, "frame", fill=0x5A)
            env.put(rect + 0x18, *rects[0:2])
            env.put(rect + 0x20, *rects[2:4])
            env.put(rect + 0x1C, rects[4])
            env.put(rect + 0x24, rects[5])
        env.put(obj + 0x174, rect)
        env.put(obj + 0x138, 0x11111111, 0x22222222, 0x33333333, 0x44444444)
        return {"obj": obj}
    return setup


# ---- 0x406310 and 0x4357a0 ------------------------------------------------------------------------------
def flip_setup(flags, pairs, outer, inner):
    def setup(env):
        obj = env.object(0x40, "rat", fill=0)
        owner = env.object(0x150, "owner", fill=0)
        env.put(obj + 4, owner)
        env.put(obj + 0x10, outer[0])
        env.put(obj + 0x18, outer[1])
        env.put(owner + 0x40, flags)
        for index, base in enumerate((0x118, 0x128, 0x138)):
            first, second = pairs[index]
            env.put(owner + base, first)
            env.put(owner + base + 8, second)
            env.put(owner + base + 4, 0x70000000 + index)
        return {"obj": obj, "owner": owner}
    return setup


def cases(random_source):
    r = random_source
    # 0x408050
    yield Case("frame rect: no frame", RECT_FROM_SPRITE, rect_setup(None), receiver=lambda t: t["obj"])
    yield Case("frame rect: fixed", RECT_FROM_SPRITE, rect_setup((3, 5, 40, 77, 11, 90)), receiver=lambda t: t["obj"])
    yield Case("frame rect: negatives", RECT_FROM_SPRITE, rect_setup((0xFFFFFFF0, 7, 5, 0xFFFFFF00, 0xFFFFFFFE, 3)), receiver=lambda t: t["obj"])
    for n in range(4):
        values = tuple(word(r) for _ in range(6))
        yield Case(f"frame rect: random {n}", RECT_FROM_SPRITE, rect_setup(values), receiver=lambda t: t["obj"])

    # 0x406310 / 0x4357a0
    for function, name in ((FLIP_OFF, "unflip"), (FLIP_ON, "flip")):
        for flag_bit in (0, 2):
            for combo in range(8):
                pairs = []
                for index in range(3):
                    if combo >> index & 1:
                        pairs.append((MIN_INT, word(r, 1, 900)))
                    else:
                        pairs.append((word(r, -900, 900) or 5, word(r, -900, 900) or 7))
                flags = 0xFFFFFFFD | flag_bit if flag_bit == 0 else 0x00000002
                flags = (flags ^ (word(r, 0, 1 << 30) & 0xFFFFFFFC)) if combo & 1 else flags
                outer = (word(r, 1, 500), word(r, 1, 500))
                yield Case(f"{name}: bit1 {'set' if flags & 2 else 'clear'} sentinels {combo:03b}", function,
                           flip_setup(flags, pairs, outer, None), receiver=lambda t: t["obj"])
    yield Case("unflip: only bit1 set", FLIP_OFF, flip_setup(2, [(5, 6), (7, 8), (9, 10)], (3, 4), None), receiver=lambda t: t["obj"])
    yield Case("flip: all bits except bit1", FLIP_ON, flip_setup(0xFFFFFFFD, [(5, 6), (7, 8), (9, 10)], (3, 4), None), receiver=lambda t: t["obj"])
    yield Case("flip: sentinel in second only", FLIP_ON, flip_setup(0, [(5, MIN_INT), (7, MIN_INT), (9, MIN_INT)], (3, 4), None), receiver=lambda t: t["obj"])
    yield Case("flip: zeros", FLIP_ON, flip_setup(0, [(0, 0), (0, 0), (0, 0)], (0, 0), None), receiver=lambda t: t["obj"])
    yield Case("unflip: zeros", FLIP_OFF, flip_setup(2, [(0, 0), (0, 0), (0, 0)], (0, 0), None), receiver=lambda t: t["obj"])
    yield from state_cases(r)
    yield from ctor_cases(r)
    yield construct_state_case(r, "state 0 constructs the rat")
    yield construct_state_case(r, "state 0 with a long bit string", big_string=b"40", a148=0, lookup="miss")
    yield construct_state_case(r, "state 0 without animations", walk=(False,) * 5, null_fallback=False, depth=0)


# ---- 0x47c850 -------------------------------------------------------------------------------------------
def state_setup(state, slots=(0x20, 0x1C, 0x10, 0x4, 0x8, 0xC)):
    def setup(env):
        arg = env.object(0x80, "level-object", fill=0x3C)
        record = env.object(0x30, "record", fill=0x6B)
        heap_obj = env.object(0x40, "speech", fill=0x2D)
        vtable = env.object(0x40, "vtable", fill=0)
        env.put(arg + 0x6C, record)
        env.put(record + 0x1C, state)
        env.put(record + 0x18, heap_obj)
        env.put(heap_obj, vtable)
        for slot in slots:
            env.put(vtable + slot, env.stub(f"slot{slot:x}", "thiscall", 0, returns(0x1234 + slot)))
        return {"arg": arg, "record": record, "obj": heap_obj}
    return setup


def state_case(label, state, **kw):
    return Case(label, RAT_STATE, state_setup(state, **kw), arguments=(lambda t: t["arg"],))


def state_cases(r):
    yield state_case("state 0x1d calls slot 0x20", 0x1D)
    yield state_case("state 0x1e calls slot 0x1c", 0x1E)
    yield state_case("state 0x3e8 does nothing", 0x3E8)
    for state in (1, 5, 0x1C, 0x1F, 0x20, 0x3E7, 0x3E9, 0xFFFFFFFF, r.randrange(0x21, 0x3E7), r.randrange(0x3EA, 1 << 31)):
        yield default_case(f"default state {state:#x}", state, r.randrange(10, 21))
    yield default_case("default: handle at table low end", 7, 10)
    yield default_case("default: handle at table high end", 7, 20)
    yield default_case("default: stride 4", 9, 13, stride=4)
    yield default_case("default: long string", 9, 15, length=40, alloc=60)
    yield default_case("default: shared string is copied", 9, 15, refcount=2, pooled=True)
    yield default_case("default: shared long string is copied", 9, 15, refcount=3, length=24, alloc=30, pooled=True)
    yield default_case("default: negative capacity is copied", 9, 15, alloc=0xFFFFFFFF, pooled=True)
    yield default_case("default: empty shared string", 9, 15, refcount=2, length=0, alloc=3, pooled=True)


TABLE_LOW, TABLE_HIGH, TABLE_BASE, TABLE_STRIDE = 0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0


def default_setup(state, handle, low=10, high=20, base=0x40, stride=0x20, refcount=1, length=5, alloc=16, pooled=False):
    """State outside {0, 0x1d, 0x1e, 0x3e8}: 0x4dc870 looks a CString up by handle and calls three methods."""
    def setup(env):
        tokens = state_setup(state)(env)
        obj = tokens["obj"]
        inner = env.object(0x30, "handle-holder", fill=0x44)
        env.put(inner + 0x1C, handle)
        env.put(obj + 0x10, inner)
        vtable = env.get(obj)
        for slot in (0x4, 0x8, 0xC):
            env.put(vtable + slot, env.stub(f"default{slot:x}", "thiscall", 1, returns(0x900 + slot)))
        table = env.object(0x400, "table", fill=0x77)
        header = env.object(0xC + max(length, 0 if alloc > 0x7FFFFFFF else alloc) + 1, "string", fill=0x61)
        env.put(header, refcount, length, alloc)
        index = handle - low
        env.put(table + base + index * stride, header + 0xC)
        env.put(TABLE_LOW, low)
        env.put(TABLE_HIGH, high)
        env.put(TABLE_BASE, table + base)
        env.put(TABLE_STRIDE, stride)
        env.put(0x5376B8, 0x55555555)
        if pooled:
            env.put(0x52E1C8, header)
        tokens["table"] = table
        return tokens
    return setup


def default_case(label, state, handle, **options):
    return Case(label, RAT_STATE, default_setup(state, handle, **options), arguments=(lambda t: t["arg"],))


# ---- 0x47c910 -------------------------------------------------------------------------------------------
def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def make_registry(env, r, entries, buckets):
    """A string table behind 0x4f6286, embedded at owner+0x10 (+4 buckets, +8 bucket count). Nodes: [next, 0, key, value]."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(owner + 0x10 + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)
    return owner


def decrement(env, call):
    value = (env.get(call.arguments[0]) - 1) & M32
    env.put(call.arguments[0], value)
    return value


def reallocate(env, call):
    old, size = call.arguments
    result = env.object(max(size, 8), "reallocation", fill=0xBC)
    if old:
        env.write(result, env.read(old, min(env.spans.get(old, 0), size)))
        env.release(old)
    return result


def install_services(env, rands=(1,)):
    env.override(RAND, sequence(*rands))
    env.override(NEW, lambda env, call: env.object(call.arguments[0], "allocation", fill=0xB7))
    env.override(REALLOC, reallocate)
    env.override(INTERLOCKED, decrement)

    def rect_empty(env, call):
        n = env.calls_so_far(call.function) * 0x1010
        env.put(call.arguments[0], n + 1, n + 2, n + 3, n + 4)
        return 1
    env.override(SET_RECT_EMPTY, rect_empty)

    def set_rect(env, call):
        env.put(call.arguments[0], *call.arguments[1:5])
        return 1
    env.override(SET_RECT, set_rect)


def rat_world(env, r, *, depth=1, big_string=None, present=tuple(GAME_NAMES), lookup="hit", rect="entry",
              walk=(True,) * 5, null_fallback=True, a40=False, scale=None, rands=(1,), a148=None):
    install_services(env, rands)
    info = env.object(0x180, "info", words=words_of(r, 0x60))
    env.put(info + 0x64, depth & M32)
    tmap = env.object(0x80, "tilemap", words=words_of(r, 0x20))
    env.put(tmap + 0x64, r.randrange(0, 100), r.randrange(0, 100))
    z = make_registry(env, r, {}, 3)
    names = make_registry(env, r, {n: r.randrange(1, 1 << 32) for n in GAME_NAMES if n in present}, 5)
    rect_object = env.object(0x30, "rat-rectangle", words=[r.randrange(1, 1 << 32) for _ in range(12)])
    env.put(rect_object + 0x18, r.randrange(0, 50), r.randrange(0, 50), r.randrange(50, 200), r.randrange(50, 200))
    lo, hi = {"entry": (1, 3), "empty-range": (2, 1), "null-entry": (0, 2), "last": (3, 3)}[rect]
    table = env.object(32, "rat-rectangles", words=[0, rect_object, 0, rect_object, 0, 0, 0, 0])
    record = env.object(0x70, "rat-record", words=words_of(r, 0x1C))
    env.put(record + 0x14, table)
    env.put(record + 0x64, lo, hi)
    registry = make_registry(env, r, {b"LEVEL_RAT": record} if lookup == "hit" else {}, r.randrange(1, 6))
    entries = {name: r.randrange(1, 1 << 32) for name, there in zip(WALK_NAMES, walk) if there}
    if null_fallback:
        entries[b"GAME_NULL"] = r.randrange(1, 1 << 32)
    breaks = make_registry(env, r, entries, r.randrange(1, 6))
    world = env.object(0x40, "world", words=words_of(r, 0x10))
    env.put(world + 0x10, registry)
    env.put(world + 0x14, z)
    env.put(world + 0x24, tmap)
    env.put(world + 0x28, names)
    env.put(world + 0x2C, breaks)
    actor = env.object(0x1C0, "actor", words=words_of(r, 0x70))
    env.put(actor + 0x0C, world)
    env.put(actor + 0x6C, info)
    env.put(actor + 0x08, r.randrange(0, 1 << 32) & ~0x10)
    env.put(actor + 0x40, (r.randrange(0, 1 << 32) & ~2) | (2 if a40 else 0))
    env.put(actor + 0x174, r.choice((0, rect_object)))
    env.put(G_TICKS, r.randrange(1, 1 << 30))
    if a148 is not None:
        env.put(actor + 0x148, a148)
    env.put(tmap + 0x5C, 0)
    env.put(0x532C0C, 0)
    if scale is not None:
        env.put(G_RAND_SCALE, scale)
    if big_string is not None:
        env.write(G_STRING, big_string + b"\0")
    return {"info": info, "world": world, "actor": actor, "tmap": tmap}


def rat_ctor_setup(r, lock=None, **options):
    def setup(env):
        tokens = rat_world(env, r, **options)
        this = env.object(0x420, "rat", words=words_of(r, 0x108))
        tokens["this"] = this
        if lock is not None:
            env.put(G_LOCALE, 1)
            env.override(LOCK, lambda env, call: env.put(this + 0x2FC, lock) or 0)
        return tokens
    return setup


def ctor_case(r, label, **options):
    return Case(label, RAT_CONSTRUCT, rat_ctor_setup(r, **options), receiver=lambda t: t["this"],
                arguments=(lambda t: t["actor"],))


def ctor_cases(r):
    yield ctor_case(r, "rat ctor basic")
    yield ctor_case(r, "rat ctor actor +0x148 zero", a148=0)
    yield ctor_case(r, "rat ctor actor +0x148 set", a148=r.randrange(1, 1 << 20))
    for lookup in ("hit", "miss"):
        for rect in ("entry", "empty-range", "null-entry", "last"):
            yield ctor_case(r, f"rat ctor record {lookup} {rect}", lookup=lookup, rect=rect,
                            depth=r.choice((1, 0, -2, 5)), a40=r.random() < 0.5)
    for index in range(5):
        walk = tuple(i != index for i in range(5))
        yield ctor_case(r, f"rat ctor animation {index} missing, fallback present", walk=walk)
        yield ctor_case(r, f"rat ctor animation {index} missing, no fallback", walk=walk, null_fallback=False)
    yield ctor_case(r, "rat ctor no animations", walk=(False,) * 5)
    yield ctor_case(r, "rat ctor no animations, no fallback", walk=(False,) * 5, null_fallback=False)
    yield ctor_case(r, "rat ctor all animations present, no fallback", null_fallback=False)
    for scale in (1.0, 9.9, 10.0, 10.1, 25.0, 0.0, 3.5):
        import struct
        bits = struct.unpack("<I", struct.pack("<f", scale))[0]
        yield ctor_case(r, f"rat ctor random scale {scale}", scale=bits)
    for names in ((), ("GAME_EEHH",), ("GAME_MOUSEKILL",), ("GAME_EEHH", "GAME_MOUSEKILL", "GAME_SPLASH")):
        present = tuple(n for n in GAME_NAMES if n.decode() in names or n == b"GAME_NULL")
        yield ctor_case(r, f"rat ctor sounds {names}", present=present)
    for value in (0, 1, 2, 3):
        yield ctor_case(r, f"rat ctor capacity {value} after lookups", lock=value)
        yield ctor_case(r, f"rat ctor capacity {value}, large string", lock=value, big_string=b"40")
    for value in (4, 9, 0x20):
        yield ctor_case(r, f"rat ctor capacity {value} after lookups", lock=value)
    for string in (b"40", b"3-70", b"1-3 40", b"33", b"5-9", b"2"):
        for depth in (1, 0):
            yield ctor_case(r, f"rat ctor bit string {string!r} depth {depth}", big_string=string, depth=depth,
                            a40=r.random() < 0.5)
    for _ in range(6):
        yield ctor_case(r, "rat ctor random", lookup=r.choice(("hit", "miss")), rect=r.choice(("entry", "last", "null-entry")),
                        depth=r.randrange(-3, 6), big_string=r.choice((None, b"40", b"2")), a40=r.random() < 0.5,
                        walk=tuple(r.random() < 0.6 for _ in range(5)), null_fallback=r.random() < 0.7,
                        present=tuple(r.sample(GAME_NAMES, r.randrange(0, len(GAME_NAMES) + 1))),
                        rands=(r.randrange(1, 1 << 30),))


def construct_state_case(r, label, **options):
    def setup(env):
        tokens = rat_world(env, r, **options)
        env.put(tokens["info"] + 0x1C, 0)
        env.put(tokens["info"] + 0x18, r.randrange(1, 1 << 32))
        return tokens
    return Case(label, RAT_STATE, setup, arguments=(lambda t: t["actor"],))
