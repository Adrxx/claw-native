"""Cases for level_one_loot_breakables_01: Level 1 loot and breakables, batch 1."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

M32 = 0xFFFFFFFF
RAND, MALLOC, FREE, LOCK = 0x4A3050, 0x4A48E0, 0x4A49B0, 0x4A7BC0
REALLOC, NEW, DELETE = 0x4A9070, 0x4F63EC, 0x4F6428
INTERLOCKED, SET_RECT_EMPTY, SET_RECT = 0x5469E8, 0x546CDC, 0x546D5C

F_4170B0, F_42DF90, F_433070, F_433130, F_4339E0 = 0x4170B0, 0x42DF90, 0x433070, 0x433130, 0x4339E0
F_433A00, F_433AD0, F_433ED0, F_433F70, F_434050 = 0x433A00, 0x433AD0, 0x433ED0, 0x433F70, 0x434050

NIL_DATA = 0x52E1C4          # MFC shared empty string data pointer
TRIE = 0x537668              # state-name trie; root pointer at +0x18
G_FACTORY_FLAG, G_FACTORY_ARG, G_Y_SWITCH = 0x532C0C, 0x532C10, 0x53721C
G_LOCALE, G_TICKS = 0x540E00, 0x537210
T1 = 0x537308                # handler table of 0x433ad0
T2 = 0x537638                # base handler table of 0x43d490
T3 = 0x537698                # animation table of 0x4dc870
G_ENTITY_COUNT, G_ENTITY_TABLE = 0x52A190, 0x537EC8
G_STRING = 0x534938

GAME_NAMES = [b"GAME_SPLASH", b"GAME_HIT1", b"GAME_HIT2", b"GAME_HIT3", b"GAME_HIT4", b"GAME_PURELEASE1",
              b"LEVEL_DEATHTILE", b"GAME_SOLHITL2", b"GAME_SOLHITHI", b"GAME_LELAND"]


def s32(value):
    value &= M32
    return value - (1 << 32) if value & 0x80000000 else value


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


# ------------------------------------------------------------------------------------------------
# shared building blocks
def make_registry(env, r, entries, buckets):
    """A string table behind 0x4f6286, embedded at owner+0x10 (+4 buckets, +8 bucket count). Nodes: [next, 0, key, value]."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    table = owner + 0x10
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)
    return owner


def make_log(env):
    return env.object(0x1000, "observation-log", fill=0)


def observe(env, log, tag, receiver, arguments, fields=()):
    n = env.get(log)
    env.put(log, n + 1)
    row = log + 4 + n * 48
    env.put(row, tag, receiver, len(arguments), *arguments)
    env.put(row + 28, *fields)


def logged_stub(env, log, tag, name, convention, argc, result=0, fields=lambda env, call: ()):
    def effect(env, call):
        observe(env, log, tag, call.receiver, call.arguments, fields(env, call))
        return result
    return env.stub(name, convention, argc, effect)


def install_trie(env, r, mode):
    """The tree behind 0x4dba00(0x537668, key). Returns {key: value}."""
    values = {b"LS_DAMAGE": r.randrange(1, 1 << 32), b"LS_FALL": r.randrange(1, 1 << 32)}
    if mode == "empty":
        env.put(TRIE + 0x18, 0)
        return values
    names = {"both": (b"LS_DAMAGE", b"LS_FALL"), "damage": (b"LS_DAMAGE", None), "fall": (None, b"LS_FALL"),
             "other": (b"LS_DAMAGX", b"LS_FALX"), "short": (b"LS_DAM", b"LS_FAL"), "null": (None, None)}[mode]
    leaves = []
    for name, real in zip(names, (b"LS_DAMAGE", b"LS_FALL")):
        if name is None:
            leaves.append(0)
            continue
        key = env.object(16, "trie-leaf-key", data=name + b"\0")
        leaf = env.object(0x20, "trie-leaf", words=words_of(r, 8))
        env.put(leaf, leaf, leaf, 0, key, values[real])
        leaves.append(leaf)
    inner_key = env.object(16, "trie-inner-key", data=b"LS_X\0")
    inner = env.object(0x20, "trie-inner", words=words_of(r, 8))
    env.put(inner, leaves[0], leaves[1], 25, inner_key, r.randrange(1, 1 << 32))
    root_key = env.object(16, "trie-root-key", data=b"LS_Y\0")
    root = env.object(0x20, "trie-root", words=words_of(r, 8))
    env.put(root, inner, 0, 0, root_key, r.randrange(1, 1 << 32))
    env.put(TRIE + 0x18, root)
    return values


def decrement(env, call):
    address = call.arguments[0]
    value = (env.get(address) - 1) & M32
    env.put(address, value)
    return value


def reallocate(env, call):
    old, size = call.arguments
    result = env.object(max(size, 8), "reallocation", fill=0xBC)
    if old:
        old_size = env.spans.get(old, 0)
        env.write(result, env.read(old, min(old_size, size)))
        env.release(old)
    return result


def allocate_filled(env, call):
    return env.object(call.arguments[0], "allocation", fill=0xB7)


def install_services(env, rands=(1,)):
    env.override(RAND, sequence(*rands))
    env.override(NEW, allocate_filled)
    env.override(REALLOC, reallocate)
    env.override(INTERLOCKED, decrement)

    def rect_empty(env, call):
        n = env.calls_so_far(call.function) * 0x1010
        env.put(call.arguments[0], n + 1, n + 2, n + 3, n + 4)
        return 1

    def set_rect(env, call):
        env.put(call.arguments[0], *call.arguments[1:5])
        return 1
    env.override(SET_RECT_EMPTY, rect_empty)
    env.override(SET_RECT, set_rect)


def cstring(env, refcount, text=b"crate text"):
    """A shared MFC string: header (refcount, length, capacity) and the text. Returns the data pointer."""
    block = env.object(12 + len(text) + 4, "cstring", fill=0)
    env.put(block, refcount & M32, len(text), len(text) + 2)
    env.write(block + 12, text + b"\0")
    return block + 12


# ------------------------------------------------------------------------------------------------
# 0x4170b0
def box_cases(r):
    def make(first, tag):
        def setup(env):
            a = env.object(0x130, "box", words=words_of(r, 0x4C))
            p = env.object(8, "box-source", words=[first, r.randrange(1, 1 << 32)])
            return {"a": a, "p": p}
        return Case(tag, F_4170B0, setup, arguments=(lambda t: t["a"], lambda t: t["p"]))
    yield make(0, "box source zero")
    yield make(1, "box source one")
    yield make(0xFFFFFFFF, "box source minus one")
    for i in range(6):
        yield make(r.randrange(0, 1 << 32), f"box random {i}")


# ------------------------------------------------------------------------------------------------
# 0x433ed0 and 0x433f70
def damage_setup(r, function, trie, prev=False, nxt=False, alias=False, in_globals=False, t_value=None):
    def setup(env):
        install_services(env)
        values = install_trie(env, r, trie)
        if in_globals:
            this = 0x537674        # this+0x10 is the trie's own +0x1c field, which the lookup rewrites
            for offset in (0x400, 0x404):
                env.put(this + offset, 0)
            first = env.object(0x30, "first-target", words=words_of(r, 12))
            env.put(this + 0x10, first)
            return {"this": this, "values": values}
        size = 0x40C
        block = env.object(size, "crate", words=words_of(r, size // 4))
        this = block + 4 if alias else block
        target = env.object(0x30, "target", words=words_of(r, 12))
        if t_value is not None:
            env.put(target + 0x1C, t_value)
        env.put(this + 0x10, target)
        p = env.object(0x408, "prev", words=words_of(r, 0x102)) if prev else 0
        n = env.object(0x408, "next", words=words_of(r, 0x102)) if nxt else 0
        if alias:
            # prev + 0x404 is this + 0x400, so the second link copy must see the rewritten value
            env.put(this + 0x400, block)
            env.put(this + 0x404, n)
        else:
            env.put(this + 0x400, p)
            env.put(this + 0x404, n)
        return {"this": this, "prev": p, "next": n, "values": values}
    return setup


def damage_cases(r):
    for trie in ("both", "damage", "fall", "empty", "other", "short", "null"):
        for prev, nxt in ((False, False), (True, False), (False, True), (True, True)):
            yield Case(f"damage trie={trie} prev={prev} next={nxt}", F_433ED0,
                       damage_setup(r, F_433ED0, trie, prev, nxt), receiver=lambda t: t["this"])
    for nxt in (False, True):
        yield Case(f"damage links alias each other next={nxt}", F_433ED0,
                   damage_setup(r, F_433ED0, "both", True, nxt, alias=True), receiver=lambda t: t["this"])
    for _ in range(3):
        yield Case("damage random target", F_433ED0,
                   damage_setup(r, F_433ED0, r.choice(("both", "damage")), r.random() < 0.5, r.random() < 0.5,
                                t_value=r.randrange(0, 1 << 32)), receiver=lambda t: t["this"])
    yield Case("damage on the trie itself", F_433ED0, damage_setup(r, F_433ED0, "both", in_globals=True),
               receiver=lambda t: t["this"])

    def fall(trie, value, in_globals=False):
        return Case(f"fall trie={trie} value={value:#x}", F_433F70,
                    damage_setup(r, F_433F70, trie, in_globals=in_globals),
                    receiver=lambda t: t["this"], arguments=(value,))
    for trie in ("both", "damage", "fall", "empty", "other", "short", "null"):
        for value in (0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, 12345):
            if trie != "both" and value not in (0, 0x80000000):
                continue
            yield fall(trie, value)
    for _ in range(6):
        yield fall("both", r.randrange(0, 1 << 32))
    yield fall("both", 77, in_globals=True)


# ------------------------------------------------------------------------------------------------
# 0x433a00 and 0x4339e0
def destroy_setup(r, capacity, strings, bit_data=True):
    def setup(env):
        install_services(env)
        this = env.object(0x418, "crate", words=words_of(r, 0x106))
        env.put(this + 0x2F4, 0x513E34, 0x544B68, capacity)
        bits = 0
        if capacity > 0x20:
            bits = env.object(4 * ((capacity + 31) // 32), "bit-array", words=words_of(r, (capacity + 31) // 32))
            env.put(this + 0x300, bits)
        else:
            env.put(this + 0x300, r.randrange(0, 1 << 32))
        data = []
        for slot, refcount in zip((0x1A8, 0x1A4), strings):
            pointer = NIL_DATA if refcount is None else cstring(env, refcount)
            env.put(this + slot, pointer)
            data.append(pointer)
        return {"this": this, "bits": bits}
    return setup


def destroy_cases(r):
    for capacity in (0, 9, 0x20, 0x21, 0x60):
        for strings in ((None, None), (1, None), (None, 1), (1, 1), (5, 2), (0, 3), (-1 & M32, 1), (2, 1)):
            yield Case(f"destroy capacity {capacity:#x} strings {strings}", F_433A00,
                       destroy_setup(r, capacity, strings), receiver=lambda t: t["this"])
    for arg in (0, 1, 2, 3, 0xFE, 0xFF, 0x100, 0x101, 0xFFFFFF00, 0xFFFFFFFF):
        for capacity, strings in ((0x21, (1, 1)), (5, (None, 2))):
            yield Case(f"delete arg {arg:#x} capacity {capacity:#x}", F_4339E0,
                       destroy_setup(r, capacity, strings), receiver=lambda t: t["this"], arguments=(arg,))


# ------------------------------------------------------------------------------------------------
# 0x433ad0
def dispatch_setup(r, idx, lo, hi, stride, filled, t2_lo=None, mode="table", growth_stub=False):
    """filled: set of table positions (idx - lo) whose handler slot is non-null."""
    def setup(env):
        install_services(env)
        log = make_log(env)
        this = env.object(0x40, "dispatch-receiver", words=words_of(r, 0x10))
        handler = [logged_stub(env, log, 1, f"t1-handler-{i}", "thiscall", 0, 0x1000 + i,
                               lambda env, call: (env.get(T1 + 0x14), env.get(T1 + 0x0C), env.get(T1 + 0x10)))
                   for i in range(4)]
        slots = max(1, hi - lo + 1) if hi >= lo else 1
        width = max(stride, 4)
        data = env.object(slots * width + 8, "t1-data", words=words_of(r, (slots * width + 8) // 4))
        if hi >= lo:
            for position in range(hi - lo + 1):
                env.put(data + position * stride, handler[position % 4] if position in filled else 0)
        env.put(T1 + 4, 0x544B68, lo, hi, data, env.object(16, "t1-default", words=words_of(r, 4)), stride)
        base = env.object(8 * 12, "t2-data", words=words_of(r, 24))
        t2_low = idx - 2 if t2_lo is None else t2_lo
        base_handlers = [logged_stub(env, log, 2, f"t2-handler-{i}", "thiscall", 0, 0x2000 + i) for i in range(3)]
        for i in range(8):
            env.put(base + 12 * i, base_handlers[i % 3])
        env.put(T2 + 4, 0x544B68, t2_low, t2_low + 7, base, env.object(16, "t2-default", words=words_of(r, 4)), 12)
        if growth_stub:
            def grow(env, call):
                result = reallocate(env, call)
                env.put(result, handler[0])
                return result
            env.override(REALLOC, grow)
        return {"this": this, "log": log}
    return setup


def dispatch_cases(r):
    for lo, hi, stride in ((0, 5, 4), (-3, 4, 8), (10, 20, 4), (5, 5, 12), (-8, -2, 4)):
        for position in sorted({0, hi - lo, r.randrange(0, hi - lo + 1)}):
            idx = lo + position
            yield Case(f"dispatch in range idx {idx} handler present", F_433AD0,
                       dispatch_setup(r, idx, lo, hi, stride, {position}), receiver=lambda t: t["this"], arguments=(idx,))
            yield Case(f"dispatch in range idx {idx} handler absent", F_433AD0,
                       dispatch_setup(r, idx, lo, hi, stride, set()), receiver=lambda t: t["this"], arguments=(idx,))
    # boundaries of the signed range tests
    for lo, hi in ((0, 5), (-4, 3)):
        for idx in (lo - 1, hi + 1, lo - 7, hi + 6):
            yield Case(f"dispatch grows the table for idx {idx}", F_433AD0,
                       dispatch_setup(r, idx, lo, hi, 4, {1}), receiver=lambda t: t["this"], arguments=(idx,))
    yield Case("dispatch grows below with a wide stride", F_433AD0,
               dispatch_setup(r, 1, 6, 9, 12, {0, 1, 2, 3}), receiver=lambda t: t["this"], arguments=(1,))
    yield Case("dispatch grows above with a wide stride", F_433AD0,
               dispatch_setup(r, 14, 6, 9, 12, {0, 1, 2, 3}), receiver=lambda t: t["this"], arguments=(14,))
    # a zero stride makes the cached low bound stale: the handler is re-checked and the table grown a second time
    for idx, lo, hi in ((7, 10, 5), (-2, 3, -6), (100, 120, 90)):
        yield Case(f"dispatch second growth idx {idx} lo {lo} hi {hi}", F_433AD0,
                   dispatch_setup(r, idx, lo, hi, 0, {0}, growth_stub=True), receiver=lambda t: t["this"],
                   arguments=(idx,))
    for _ in range(12):
        lo = r.randrange(-10, 10)
        hi = lo + r.randrange(0, 8)
        stride = r.choice((4, 8, 12, 16))
        idx = r.randrange(lo - 4, hi + 5)
        filled = {i for i in range(hi - lo + 1) if r.random() < 0.5}
        yield Case(f"dispatch random idx {idx} in {lo}..{hi}", F_433AD0,
                   dispatch_setup(r, idx, lo, hi, stride, filled), receiver=lambda t: t["this"], arguments=(idx,))


# ------------------------------------------------------------------------------------------------
# the crate world: 0x433130 and 0x433070
def crate_world(env, r, *, depth=1, big_string=None, present=(), lookup="hit", rect="entry", brk="break",
                a40=None, lock=None):
    """Everything 0x4332f0, 0x4c7970, 0x4061b0 and 0x4062e0 read.  Returns the tokens."""
    install_services(env, (r.randrange(1, 1 << 31),))
    info = env.object(0x180, "info", words=words_of(r, 0x60))
    env.put(info + 0x64, depth & M32)
    tmap = env.object(0x80, "tilemap", words=words_of(r, 0x20))
    env.put(tmap + 0x64, r.randrange(0, 100), r.randrange(0, 100))
    z = make_registry(env, r, {}, 3)
    names = make_registry(env, r, {name: r.randrange(1, 1 << 32) for name in GAME_NAMES if name in present}, 5)
    # LEVEL_CRATES record: +0x14 table of rectangles, +0x64 low, +0x68 high
    rect_object = env.object(0x30, "crate-rectangle", words=[r.randrange(1, 1 << 32) for _ in range(12)])
    env.put(rect_object + 0x18, r.randrange(0, 50), r.randrange(0, 50), r.randrange(50, 200), r.randrange(50, 200))
    lo, hi = {"entry": (1, 3), "empty-range": (2, 1), "null-entry": (0, 2), "last": (3, 3)}[rect]
    table = env.object(32, "crate-rectangles", words=[0, rect_object, 0, rect_object, 0, 0, 0, 0])
    record = env.object(0x70, "crate-record", words=words_of(r, 0x1C))
    env.put(record + 0x14, table)
    env.put(record + 0x64, lo, hi)
    crates = {"hit": {b"LEVEL_CRATES": record}, "miss": {}, "decoy": {b"LEVEL_CRATEX": record},
              "locked": {b"LEVEL_CRATES": record}}[lookup]
    registry = make_registry(env, r, crates, r.randrange(1, 6))
    break_value = r.randrange(1, 1 << 32)
    null_value = r.randrange(1, 1 << 32)
    entries = {"break": {b"LEVEL_CRATEBREAK": break_value, b"GAME_NULL": null_value},
               "break-zero": {b"LEVEL_CRATEBREAK": 0, b"GAME_NULL": null_value},
               "null": {b"GAME_NULL": null_value},
               "none": {}}[brk]
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
    env.put(actor + 0x174, r.choice((0, rect_object)))   # kept when the record lookup misses
    env.put(G_TICKS, r.randrange(1, 1 << 30))
    install_trie(env, r, "both")
    if big_string is not None:
        env.write(G_STRING, big_string + b"\0")
    return {"info": info, "world": world, "actor": actor, "break_value": break_value, "null_value": null_value,
            "crates": registry}


def lock_to(env, this_of, value):
    """Make the C runtime lock rewrite the crate's bit-array capacity: the only way to reach the small-capacity arm."""
    env.put(G_LOCALE, 1)

    def effect(env, call):
        env.put(this_of() + 0x2FC, value)
        return 0
    return effect


def crate_ctor_setup(r, **options):
    lock_value = options.pop("lock", None)

    def setup(env):
        tokens = crate_world(env, r, lookup="locked" if lock_value is not None else options.pop("lookup", "hit"),
                             **{k: v for k, v in options.items() if k != "lookup"})
        this = env.object(0x418, "crate", words=words_of(r, 0x106))
        tokens["this"] = this
        if lock_value is not None:
            env.put(G_LOCALE, 1)
            env.override(LOCK, lambda env, call: env.put(this + 0x2FC, lock_value) or 0)
        return tokens
    return setup


def crate_ctor_cases(r):
    base = dict(present=tuple(GAME_NAMES[:4]))

    def case(label, **options):
        merged = dict(base)
        merged.update(options)
        return Case(label, F_433130, crate_ctor_setup(r, **merged), receiver=lambda t: t["this"],
                    arguments=(lambda t: t["actor"],))
    for lookup in ("hit", "miss", "decoy"):
        for rect in ("entry", "empty-range", "null-entry", "last"):
            for brk in ("break", "break-zero", "null", "none"):
                if r.random() < 0.55:
                    continue
                yield case(f"crate ctor lookup={lookup} rect={rect} break={brk}", lookup=lookup, rect=rect, brk=brk,
                           depth=r.choice((1, 0, -2, 5)), a40=r.random() < 0.5)
    yield case("crate ctor hit break", lookup="hit", rect="entry", brk="break")
    yield case("crate ctor miss none", lookup="miss", rect="entry", brk="none")
    yield case("crate ctor break value zero falls back", lookup="hit", rect="entry", brk="break-zero")
    yield case("crate ctor null fallback only", lookup="hit", rect="entry", brk="null")
    for string in (b"40", b"3-70", b"1-3 40", b"33", b"5-9"):
        for depth in (1, 0):
            yield case(f"crate ctor large bit array {string!r} depth {depth}", big_string=string, depth=depth,
                       brk=r.choice(("break", "null")), a40=r.random() < 0.5)
    for value in (0, 1):
        yield case(f"crate ctor small capacity arm {value}", lock=value, brk="break")
    yield case("crate ctor small capacity zero, large string", lock=0, big_string=b"40")
    for _ in range(8):
        yield case("crate ctor random", lookup=r.choice(("hit", "miss")), rect=r.choice(("entry", "last", "null-entry")),
                   brk=r.choice(("break", "null", "none")), depth=r.randrange(-3, 6),
                   big_string=r.choice((None, b"40", b"2")), a40=r.random() < 0.5,
                   present=tuple(r.sample(GAME_NAMES, r.randrange(0, len(GAME_NAMES) + 1))))


# 0x433070
def state_setup(r, state, kind, table_range=None, **options):
    def setup(env):
        if kind == "construct":
            tokens = crate_world(env, r, **options)
            info = tokens["info"]
            env.put(info + 0x1C, state)
            env.put(info + 0x18, r.randrange(1, 1 << 32))
            return tokens
        install_services(env)
        log = make_log(env)
        info = env.object(0x40, "logic", words=words_of(r, 0x10))
        actor = env.object(0x80, "actor", words=words_of(r, 0x20))
        env.put(actor + 0x6C, info)
        env.put(info + 0x1C, state)
        slots = env.object(0x40, "state-vtable", fill=0)
        for slot in (4, 8, 0xC, 0x1C, 0x20):
            env.put(slots + slot, logged_stub(env, log, slot, f"state-slot-{slot:#x}", "thiscall", 1 if slot < 0x10 else 0,
                                              0x300 + slot, lambda env, call: (env.get(info + 0x1C), env.get(info + 0x18))))
        owner = env.object(0x20, "state-owner", words=words_of(r, 8))
        env.put(owner, slots)
        n = r.randrange(-5, 40)
        extra = env.object(0x20, "state-detail", words=words_of(r, 8))
        env.put(extra + 0x1C, n)
        env.put(owner + 0x10, extra)
        env.put(info + 0x18, owner)
        if kind == "table":
            lo, hi = n - r.randrange(0, 3), n + r.randrange(0, 3)
            stride = r.choice((4, 8, 12))
            data = env.object((hi - lo + 1) * stride + 8, "animation-table", fill=0)
            for position in range(hi - lo + 1):
                env.put(data + position * stride, NIL_DATA)
            env.put(T3 + 4, 0x544B68, lo, hi, data, env.object(16, "animation-default", fill=0), stride)
        return {"actor": actor, "info": info, "log": log, "owner": owner}
    return setup


def state_cases(r):
    for state in (0x1D, 0x1E):
        yield Case(f"state {state:#x} virtual call", F_433070, state_setup(r, state, "slots"),
                   arguments=(lambda t: t["actor"],))
    yield Case("state 1000 does nothing", F_433070, state_setup(r, 1000, "slots"), arguments=(lambda t: t["actor"],))
    for state in (1, 2, 0x1C, 0x1F, 0x20, 999, 1001, 0x3E7, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFE3):
        yield Case(f"state {state:#x} runs the animation step", F_433070, state_setup(r, state, "table"),
                   arguments=(lambda t: t["actor"],))
    for lookup in ("hit", "miss"):
        for brk in ("break", "null", "none"):
            for a40 in (True, False):
                yield Case(f"state 0 constructs the crate lookup={lookup} break={brk} a40={a40}", F_433070,
                           state_setup(r, 0, "construct", present=tuple(GAME_NAMES[:5]), lookup=lookup, brk=brk, a40=a40,
                                       depth=r.choice((1, 0, 3))),
                           arguments=(lambda t: t["actor"],))
    yield Case("state 0 constructs with a large bit array", F_433070,
               state_setup(r, 0, "construct", big_string=b"40", present=tuple(GAME_NAMES)),
               arguments=(lambda t: t["actor"],))


# ------------------------------------------------------------------------------------------------
# the bouncing goodie spawner: 0x42df90 and, inside it, 0x434050
ENTITY_KEYS = [b"ENTITY_ZERO", b"ENTITY_COIN", b"ENTITY_RING", b"ENTITY_GEM", b"ENTITY_CROWN", b"ENTITY_SKULL"]


def sound_chain(env, r):
    """X with [[[X+0x10]+0x10]+0x78] == 0: the sound request returns at once."""
    x = env.object(0x30, "sound-owner", words=words_of(r, 12))
    y = env.object(0x30, "sound-iface", words=words_of(r, 12))
    w = env.object(0x90, "sound-state", words=words_of(r, 0x24))
    env.put(x + 0x10, y)
    env.put(y + 0x10, w)
    env.put(w + 0x78, 0)
    return x


def goodie_world(env, r, region, log, *, count, entries, c, sound, flag, y_switch, p100, factory_arg, mutate,
                 known_table=True, sound_object=True):
    """Fill the goodie fields of `region` (the crate's +0x128 block, or a block of its own)."""
    obj1 = env.object(0x20, "goodie-link1", words=words_of(r, 8))
    obj2 = env.object(0x20, "goodie-link2", words=words_of(r, 8))
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    env.put(scene + 12, context)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for i in range(63):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    env.put(region + 8, obj1)
    env.put(obj1 + 0xC, obj2)
    env.put(obj2 + 8, scene)

    # the goodie's logic: the registered callback is the cdecl function that 0x42df90 calls
    def callback(env, call):
        n = call.arguments[0]
        q = env.get(n + 0x6C)
        s = env.object(0x190, "goodie-state", fill=0x5A)
        env.put(q + 0x18, s)
        observe(env, log, 7, call.receiver, call.arguments,
                (env.get(n + 0x148), env.get(n + 0xFC), env.get(n + 0x14C), env.get(n + 0x170), env.get(n + 0x174)))
        done = env.get(log)
        if mutate == "count" and done == 1:
            env.put(region + 0x24, 1 if count > 1 else 0)
        elif mutate == "count-up" and done == 1:
            env.put(region + 0x24, min(count + 2, 14))
        elif mutate == "mode" and done == 1:
            env.put(region + 0x28, 1 if c != 1 else 3)
        elif mutate == "entry" and done == 1:
            env.put(region + 0x2C, 0x1234)
        elif mutate == "flag":
            env.put(G_Y_SWITCH, 0 if y_switch else 5)
        elif mutate == "all" and done == 1:
            env.put(region + 0x28, 1 if c != 1 else 2)
            env.put(region + 0x2C, 0x4321)
            env.put(G_Y_SWITCH, 0 if y_switch else 9)
        return 0
    stub = env.stub("goodie-callback", "cdecl", 1, callback)
    metadata = env.object(0x18, "goodie-metadata", fill=0)
    env.put(metadata + 8, 0x2)
    env.put(metadata + 0x10, stub)
    factory = make_registry(env, r, {b"BouncingGoodie": metadata}, r.randrange(1, 5))
    env.put(context + 0x14, factory)

    # the lookup of the entity: 0x473630 maps an entry to a name, 0x4c7970 finds its record
    env.put(G_ENTITY_COUNT, len(ENTITY_KEYS))
    records = {}
    for index, name in enumerate(ENTITY_KEYS):
        holder = env.object(0x50, "entity-name", fill=0)
        env.write(holder + 0x24, name + b"\0")
        env.put(G_ENTITY_TABLE + 4 * index, holder)
        if known_table and index % 5 != 4:
            lo = r.randrange(0, 3)
            hi = lo + r.randrange(-1, 3)
            cells = env.object(4 * (lo + 2), "entity-frames", words=words_of(r, lo + 2))
            record = env.object(0x70, "entity-record", words=words_of(r, 0x1C))
            env.put(record + 0x14, cells)
            env.put(record + 0x64, lo, hi)
            records[name] = record
    fallback_name = env.cstr(0x5279B8)
    if known_table and fallback_name and r.random() < 0.7:
        cells = env.object(16, "entity-frames", words=words_of(r, 4))
        record = env.object(0x70, "entity-record", words=words_of(r, 0x1C))
        env.put(record + 0x14, cells)
        env.put(record + 0x64, 1, 1)
        records[fallback_name] = record
    env.put(context + 0x10, make_registry(env, r, records, r.randrange(1, 6)))

    p = env.object(0x150, "owner-state", words=words_of(r, 0x54))
    env.put(p + 0x100, p100)
    env.put(region + 0x6C, p)
    env.put(region + 0x20, sound_chain(env, r) if sound and sound_object else 0)
    env.put(region + 0x24, count)
    env.put(region + 0x28, c & M32)
    for index, entry in enumerate(entries):
        env.put(region + 0x2C + 4 * index, entry & M32)
    env.put(G_FACTORY_FLAG, flag)
    env.put(G_FACTORY_ARG, factory_arg)
    env.put(G_Y_SWITCH, y_switch)
    return {"p": p, "scene": scene}


def goodie_setup(r, *, count, entries, c, sound=True, flag=1, y_switch=0, p100=0x20, mutate=None, rands=None,
                 known_table=True, sound_object=True):
    def setup(env):
        install_services(env, rands or tuple(r.randrange(0, 1 << 32) for _ in range(40)))
        log = make_log(env)
        region = env.object(0x80, "goodie-block", words=words_of(r, 0x20))
        tokens = goodie_world(env, r, region, log, count=count, entries=entries, c=c, sound=sound, flag=flag,
                              y_switch=y_switch, p100=p100, factory_arg=r.randrange(1, 1 << 32), mutate=mutate,
                              known_table=known_table, sound_object=sound_object)
        tokens.update({"region": region, "log": log})
        return tokens
    return setup


GOOD_ENTRIES = (1, 2, 3, 4, 5, 6, 7)
ODD_ENTRIES = (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 100, 6)


def goodie_cases(r):
    def case(label, **options):
        return Case(label, F_42DF90, goodie_setup(r, **options), receiver=lambda t: t["region"])
    for c in (-3, -1, 0, 1, 2, 3, 7, 100):
        for count in (0, 1, 2, 4):
            entries = [r.choice(GOOD_ENTRIES) for _ in range(count)]
            yield case(f"goodies mode {c} count {count}", count=count, entries=entries, c=c,
                       y_switch=r.choice((0, 1, 0x80000000)), p100=r.choice((0x20, 0x20, 0x21)))
    for count in (-5, -1, 0):
        yield case(f"goodies with count {count} do nothing", count=count, entries=[1, 2], c=2)
    yield case("goodies skip empty entries", count=5, entries=[0, 1, 0, 2, 0], c=2)
    yield case("goodies skip empty entries in mode 1", count=5, entries=[3, 0, 0, 2, 4], c=1, y_switch=3)
    yield case("sixteen goodies", count=16, entries=[1 + i % 4 for i in range(16)], c=1, y_switch=1)
    yield case("sixteen goodies mode 2", count=16, entries=[1 + i % 5 for i in range(16)], c=2)
    for entries in ([6], [7], [100, 1], [0x7FFFFFFF], [0x80000000, 2], [0xFFFFFFFF, 3], [0, 6, 0], [5]):
        yield case(f"entity out of range or unregistered {entries}", count=len(entries), entries=entries, c=2)
    yield case("no entity records at all", count=3, entries=[1, 2, 3], c=1, known_table=False)
    yield case("sound requested, factory flag off", count=2, entries=[1, 2], c=3, flag=0)
    yield case("sound requested, factory flag on", count=2, entries=[1, 2], c=3, flag=1)
    yield case("no sound object", count=2, entries=[1, 2], c=3, sound_object=False)
    yield case("mode 0 never asks for sound", count=2, entries=[1, 2], c=0, flag=1)
    yield case("owner width is not 0x20", count=2, entries=[1, 2], c=2, p100=0)
    yield case("owner width is 0x20", count=2, entries=[1, 2], c=2, p100=0x20)
    for mutate in ("count", "count-up", "mode", "entry", "flag", "all"):
        for c in (1, 2):
            yield case(f"callback changes {mutate} (mode {c})", count=3, entries=[1, 2, 3], c=c, mutate=mutate,
                       y_switch=r.choice((0, 1)))
    # signed division by 401, 301 and 1001 of negative, zero and extreme draws
    draws = (0, 1, 400, 401, 402, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFE6F, 300, 301, 1000, 1001, 5000)
    for draw in draws:
        yield case(f"mode 1 draw {draw:#x}", count=1, entries=[1], c=1, y_switch=draw & 1,
                   rands=(draw, (draw * 7 + 3) & M32))
    for draw in draws:
        yield case(f"mode 1 draw {draw:#x}, other height", count=1, entries=[2], c=1, y_switch=0,
                   rands=((draw * 5 + 1) & M32, draw))
    for _ in range(14):
        count = r.randrange(0, 8)
        yield case("goodies random", count=count, entries=[r.choice(GOOD_ENTRIES + (0,)) for _ in range(count)],
                   c=r.choice((-4, 0, 1, 1, 2, 5, 9)), y_switch=r.choice((0, 1, r.randrange(0, 1 << 32))),
                   sound=r.random() < 0.7, flag=r.choice((0, 1)), p100=r.choice((0x20, 0x20, 0x40)),
                   mutate=r.choice((None, None, "count", "mode", "entry", "flag", "all")))


# 0x434050
def break_setup(r, *, count, entries, c, m_draw, m30=0, lookup="hit", factory_flag=1, arg="chain", u_d0=0x20,
                vcall_mutates=False, y_switch=0, sound=True, p100=0x20):
    spawned = sum(1 for entry in entries[:max(count, 0)] if entry) if count > 0 else 0
    draws_before = spawned * (2 if c == 1 else 1)

    def setup(env):
        rands = tuple(r.randrange(0, 1 << 32) for _ in range(draws_before)) + (m_draw,) + (0x1234,) * 4
        install_services(env, rands)
        log = make_log(env)
        this = env.object(0x418, "crate", words=words_of(r, 0x106))
        goodie_world(env, r, this + 0x128, log, count=count, entries=entries, c=c, sound=sound, flag=factory_flag,
                     y_switch=y_switch, p100=p100, factory_arg=r.randrange(1, 1 << 32), mutate=None)
        a2 = env.object(0x1C0, "owner", words=words_of(r, 0x70))
        env.put(this + 0x12C, a2)
        env.put(this + 0x410, 0)
        if arg == "chain":
            p2 = env.object(0x30, "frame-source", words=words_of(r, 12))
            p1 = env.object(8, "frame-link", words=[p2, 0])
            argument = env.object(0x30, "frame-set", words=words_of(r, 12))
            env.put(argument + 0xC, p1)
            env.put(argument + 0x10, 1 + r.randrange(0, 4))
            env.put(this + 0x410, argument)
        vt = env.object(0xB0, "crate-vtable", fill=0)
        actor2 = env.object(0x100, "owner-two", words=words_of(r, 0x40))
        u = env.object(0x100, "owner-flags", words=words_of(r, 0x40))
        env.put(u + 0xD0, u_d0)
        env.put(actor2 + 0x74, u)
        info = env.object(0x40, "break-info", words=words_of(r, 0x10))
        mid = env.object(0x40, "break-mid", words=words_of(r, 0x10))
        value = sound_chain(env, r)
        entries_map = {"hit": {b"GAME_CRATEBREAK": value, b"GAME_CRATEBREAK2": value},
                       "only-first": {b"GAME_CRATEBREAK": value}, "only-second": {b"GAME_CRATEBREAK2": value},
                       "decoy": {b"GAME_CRATEBREAK3": value}, "none": {}}[lookup]
        m = make_registry(env, r, entries_map, r.randrange(1, 5))
        env.put(m + 0x30, m30)
        env.put(mid + 0x28, m)
        env.put(info + 0xC, mid)
        env.put(this + 0x10, info)
        env.put(this + 0xC, actor2)
        # a second owner and info, swapped in by the virtual call: they are read again afterwards
        actor3 = env.object(0x100, "owner-three", words=words_of(r, 0x40))
        u3 = env.object(0x100, "owner-flags-three", words=words_of(r, 0x40))
        env.put(u3 + 0xD0, 0x21 if u_d0 == 0x20 else 0x20)
        env.put(actor3 + 0x74, u3)
        mid3 = env.object(0x40, "break-mid-three", words=words_of(r, 0x10))
        m3 = make_registry(env, r, {b"GAME_CRATEBREAK": value, b"GAME_CRATEBREAK2": value}, 3)
        env.put(m3 + 0x30, 0)
        env.put(mid3 + 0x28, m3)
        info3 = env.object(0x40, "break-info-three", words=words_of(r, 0x10))
        env.put(info3 + 0xC, mid3)

        def slot(env, call):
            observe(env, log, 9, call.receiver, call.arguments, (env.get(this + 0x134), env.get(a2 + 8)))
            if vcall_mutates:
                env.put(this + 0xC, actor3)
                env.put(this + 0x10, info3)
            return 0
        env.put(vt + 0xA8, env.stub("crate-slot-a8", "thiscall", 0, slot))
        env.put(this, vt)
        env.put(a2 + 0x190, r.randrange(1, 1 << 32))
        return {"this": this, "log": log}
    return setup


def break_cases(r):
    def case(label, **options):
        options.setdefault("count", 0)
        options.setdefault("entries", [])
        options.setdefault("c", 2)
        options.setdefault("m_draw", 7)
        return Case(label, F_434050, break_setup(r, **options), receiver=lambda t: t["this"])
    for m_draw in (0, 1, 49, 50, 51, 99, 100, 149, 150, 0xFFFFFFFF, 0xFFFFFFCE, 0xFFFFFFCD, 0xFFFFFF9C, 0x7FFFFFFF,
                   0x80000000):
        for lookup in ("hit", "none"):
            yield case(f"break draw {m_draw:#x} lookup {lookup}", m_draw=m_draw, lookup=lookup)
    for lookup in ("hit", "only-first", "only-second", "decoy", "none"):
        for m_draw in (10, 90):
            for flag in (0, 1):
                yield case(f"break lookup {lookup} draw {m_draw} factory flag {flag}", m_draw=m_draw, lookup=lookup,
                           factory_flag=flag)
    for m_draw in (10, 90):
        yield case(f"break sound suppressed by the map flag, draw {m_draw}", m_draw=m_draw, m30=r.randrange(1, 1 << 32))
    for arg in ("chain", "none"):
        for u_d0 in (0x20, 0x21, 0, 0xFFFFFFE0):
            yield case(f"break with frame set {arg}, owner flags {u_d0:#x}", arg=arg, u_d0=u_d0, m_draw=r.randrange(0, 1 << 32))
    for m_draw in (10, 90):
        for u_d0 in (0x20, 0x21):
            yield case(f"break after the virtual call changes owner and info, draw {m_draw} flags {u_d0:#x}",
                       vcall_mutates=True, u_d0=u_d0, m_draw=m_draw)
    for c in (0, 1, 2, 3):
        for count in (1, 2, 3):
            entries = [1, 0, 2, 3][:count] if count > 1 else [4]
            for m_draw in (20, 70):
                yield case(f"break spawns goodies mode {c} count {count} draw {m_draw}", count=count, entries=entries,
                           c=c, m_draw=m_draw, y_switch=r.choice((0, 1)), p100=r.choice((0x20, 0x30)))
    yield case("break spawns goodies without sound owner flag", count=2, entries=[1, 2], c=3, factory_flag=0, m_draw=60)
    for _ in range(10):
        count = r.randrange(0, 5)
        yield case("break random", count=count, entries=[r.choice(GOOD_ENTRIES + (0,)) for _ in range(count)],
                   c=r.choice((0, 1, 2, 4)), m_draw=r.randrange(0, 1 << 32), m30=r.choice((0, 0, 3)),
                   lookup=r.choice(("hit", "only-first", "only-second", "none")), factory_flag=r.choice((0, 1)),
                   arg=r.choice(("chain", "none")), u_d0=r.choice((0x20, 0x21)), vcall_mutates=r.random() < 0.4,
                   y_switch=r.choice((0, 1)))


def cases(random_source):
    r = random_source
    yield from box_cases(r)
    yield from damage_cases(r)
    yield from destroy_cases(r)
    yield from dispatch_cases(r)
    yield from crate_ctor_cases(r)
    yield from state_cases(r)
    yield from goodie_cases(r)
    yield from break_cases(r)
