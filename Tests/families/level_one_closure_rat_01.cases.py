"""Cases for level_one_closure_rat_01: Level 1 closure: Rat logic helpers."""
from clawparity.cases import Case
from clawparity.fixtures import reallocate, release  # noqa: F401

# 0x47cd70 dispatches through a table descriptor at 0x53c0e8:
#   +4 logger, +8 low, +0xc high, +0x10 entries, +0x14 default entry, +0x18 stride, +0x1c/+0x20 scratch.
# A zero first word in an entry sends it to 0x43d490, which uses the same shape of table at 0x537638.
DISPATCH = 0x47CD70
INIT_A = 0x47D4B0
INIT_B = 0x47D540
INIT_C = 0x47D5D0
SYNC = 0x47D780
MAIN_BASE = 0x53C0E8
FALLBACK_BASE = 0x537638
LOG_STRING = 0x544B4C
LOG_RESULT = 0x544B14
LOG_ENABLE = 0x544D18
STRIDES = (4, 8, 12, 16, 36)

TREE_ROOT = 0x537668  # 0x4dba00 receiver
KEY_STRING = 0x52B0B0


def descriptor(env, base, low, high, stride, present, rec, slot, tag=0):
    """Table at `base`. Every in-range entry gets distinct nonzero payload words; entries in `present` also get a
    callback that records its receiver and identity."""
    count = max(1, high - low + 1)
    size = max(4, count * stride)
    entries = env.object(size, "entries", fill=0)
    for index in range(low, high + 1):
        offset = (index - low) * stride
        if offset + 4 > size:
            continue
        for word in range(1, stride // 4):
            env.put(entries + offset + 4 * word, (0x11110000 + (index & 0xFFF) * 16 + word + tag) & 0xFFFFFFFF)
        if index in present:
            slot[0] += 1
            ident = slot[0]

            def effect(env, call, ident=ident, tag=tag):
                env.put(rec + 8 * ident + 0x200 * (tag - 1), call.receiver, ident * 16 + tag)
                return 0x7000 + ident
            env.put(entries + offset, env.stub(f"callback {tag}:{index}", "thiscall", 0, effect))
        else:
            env.put(entries + offset, 0)
    logger = env.object(0x20, "logger", fill=0x5A)
    env.put(logger, env.stub(f"logger hook {tag}", "cdecl", 2, lambda env, call: env.put(rec + 0x1F0, *call.arguments) or 0))
    env.put(logger + 8, 0x1111)
    env.put(logger + 0xC, 4)
    env.put(logger + 0x14, env.object(16, "prefix", data=b"claw: ok\x00" + b"\x00" * 7))
    default_entry = env.object(8, "default entry", fill=0)
    env.put(default_entry, env.stub(f"default {tag}", "thiscall", 0,
                                    lambda env, call: env.put(rec + 0x1E0, call.receiver, 0xDEFA + tag) or 0))
    env.put(base + 4, logger)
    env.put(base + 8, low & 0xFFFFFFFF)
    env.put(base + 0xC, high & 0xFFFFFFFF)
    env.put(base + 0x10, entries)
    env.put(base + 0x14, default_entry)
    env.put(base + 0x18, stride)
    env.put(base + 0x1C, 0x13572468)
    env.put(base + 0x20, 0x2468ACE1)
    return {"entries": entries}


def globals_setup(env):
    env.put(LOG_STRING, env.object(24, "message", data=b"table fault\x00" + b"\x7f" * 12))
    env.put(LOG_RESULT, 0xA5A5A5A5)
    env.put(LOG_ENABLE, 0)


def make_owner(env, rtti=False):
    owner = env.object(0x40, "receiver", fill=0)
    for word in range(1, 16):
        env.put(owner + 4 * word, 0xC0DE0000 + word)
    if rtti:
        rtti_data = env.object(16, "rtti data", fill=0x3C)
        vtable = env.object(16, "vtable", fill=0)
        rtti_obj = env.object(0x20, "rtti", fill=0x44)
        env.put(rtti_obj + 0xC, rtti_data)
        env.put(vtable, rtti_obj)
        env.put(owner, vtable + 4)
    else:
        env.put(owner, 0x00510000)
    return owner


def dispatch_case(label, low, high, p, stride, present=None, fallback=None, grow_fail=None, rtti=False):
    """`fallback` is None (the fallback table covers only p) or a (low, high) range containing p. The fallback
    entry for p always has a callback: the empty-entry path reaches 0x4a36f0 and IsBadReadPtr, which has no stand-in."""
    present = set(range(low, high + 1)) if present is None else present

    def setup(env):
        rec = env.object(0x400, "record", fill=0)
        globals_setup(env)
        owner = make_owner(env, rtti)
        slot = [0]
        descriptor(env, MAIN_BASE, low, high, stride, present, rec, slot, tag=1)
        flow, fhigh = (p, p) if fallback is None else fallback
        fb_present = {p}
        descriptor(env, FALLBACK_BASE, flow, fhigh, 8, fb_present, rec, [0], tag=2)
        if grow_fail:
            env.override(0x4A9070, reallocate(fail=True))
        return {"owner": owner, "rec": rec}

    return Case(label, DISPATCH, setup, receiver=lambda t: t["owner"], arguments=(p & 0xFFFFFFFF,))


def regrown_entry_case(label, low, count, target_page, tail):
    """A one-byte-stride table that grows by one entry below `low`. The grown first dword straddles the new zero
    byte and the first old bytes, so it is nonzero and names a stub; the original calls through the new entry."""
    p = low - 1
    target = 0x710000 + 0x100 * target_page

    def setup(env):
        rec = env.object(0x400, "record", fill=0)
        globals_setup(env)
        owner = make_owner(env)
        descriptor(env, MAIN_BASE, low, low + count - 1, 4, set(), rec, [0], tag=1)
        old = bytes([(target >> 8) & 0xFF, (target >> 16) & 0xFF, 0]) + bytes(tail)
        old = old + bytes((0x31 + 7 * i) & 0xFF or 1 for i in range(count - len(old)))
        env.put(MAIN_BASE + 0x10, env.object(count, "byte entries", data=old[:count]))
        env.put(MAIN_BASE + 0x18, 1)
        env.put(MAIN_BASE + 0x24, 0x3C3C3C3C)
        env.put(MAIN_BASE + 0x28, 0x4D4D4D4D)
        while True:
            def effect(env, call):
                env.put(rec + 4, call.receiver, 0x7000)
                env.put(rec + 0x40, env.get(MAIN_BASE + 0x1C), env.get(MAIN_BASE + 0x20), env.get(MAIN_BASE + 0x10))
                return 0x7001
            address = env.stub("regrown entry", "thiscall", 0, effect)
            if address >= target:
                break
        if address != target:
            raise AssertionError(f"stub address {address:#x} passed the target {target:#x}")
        return {"owner": owner, "rec": rec}

    return Case(label, DISPATCH, setup, receiver=lambda t: t["owner"], arguments=(p & 0xFFFFFFFF,))


# ---- the three initialisers -------------------------------------------------------------------------

def init_case(label, function, param_offset, rnd, root="none", param="full", count=1, key=None, alias=None):
    """root: "none" (tree empty), "match" (node holds the key), "mismatch", "deep" (key shorter than the node bit).
    param: "full", "null"."""

    def setup(env):
        if alias is None:
            obj = env.object(0x440, "rat", fill=0)
        else:
            # The owner pointer at +0x12c points back into the object, so the 0x4c8220 writes land on the
            # fields the setter also stores (+0x134, +0x1a0): the order of the two stores is observable.
            region = env.object(0x640, "rat with margin", fill=0)
            for word in range(0x100 // 4):
                env.put(region + 4 * word, rnd.getrandbits(32) | 0x02020202)
            obj = region + 0x100
        for word in range(0x110):
            env.put(obj + 4 * word, rnd.getrandbits(32) | 0x01010101)
        inner = env.object(0x40, "inner", fill=0)
        for word in range(16):
            env.put(inner + 4 * word, rnd.getrandbits(32) | 0x80000001)
        env.put(obj + 0x10, inner)
        sub = env.object(0x200, "sub", fill=0)
        for word in range(0x80):
            env.put(sub + 4 * word, rnd.getrandbits(32) | 0x00010001)
        env.put(obj + 0x12C, sub if alias is None else (obj + alias) & 0xFFFFFFFF)
        if param == "null":
            env.put(obj + param_offset, 0)
        else:
            target = env.object(0x40, "list-target", fill=0)
            env.put(target + 0x1C, rnd.getrandbits(32) | 0x00400001)
            items = env.object(4 * count + 4, "items", fill=0)
            env.put(items, target)
            for i in range(1, count):
                env.put(items + 4 * i, 0x00BAD000 + i)
            holder = env.object(0x20, "holder", fill=0)
            env.put(holder + 0x0C, items)
            env.put(holder + 0x10, count)
            env.put(obj + param_offset, holder)
        text = env.cstr(KEY_STRING)
        env.put(TREE_ROOT + 0x1C, 0x600DF00D)
        env.put(TREE_ROOT + 0x20, 0x600DF00E)
        env.put(TREE_ROOT + 0x24, 0x600DF00F)
        env.put(TREE_ROOT + 0x28, 0x600DF010)
        if root == "none":
            env.put(TREE_ROOT + 0x18, 0)
        else:
            node = env.object(0x20, "node", fill=0)
            if root == "deep":
                env.put(node + 8, (len(text) * 8 + 40))
            else:
                env.put(node + 8, 0)
            env.put(node, node)
            env.put(node + 4, node)
            data = bytes(text) if isinstance(text, (bytes, bytearray)) else text.encode("latin-1")
            if root == "mismatch":
                data = bytes([data[0] ^ 1]) + data[1:]
            elif root == "mismatch-late":
                data = data[:-1] + bytes([data[-1] ^ 2])
            env.put(node + 0xC, env.object(len(data) + 2, "node text", data=data + b"\x00"))
            env.put(node + 0x10, rnd.getrandbits(32) | 0x00C00003)
            env.put(TREE_ROOT + 0x18, node)
        return {"owner": obj}

    return Case(label, function, setup, receiver=lambda t: t["owner"])


# ---- 0x47d780 -------------------------------------------------------------------------------------

def sync_case(label, current, cached, flags_kind, flags_word, rnd):
    def setup(env):
        rec = env.object(0x40, "record", fill=0)
        this = env.object(0x1C0, "ratlogic", fill=0)
        for word in range(0x70):
            env.put(this + 4 * word, rnd.getrandbits(32) | 0x01000001)
        vtable = env.object(0x80, "vtable", fill=0)
        env.put(this, vtable)

        def method(env, call):
            env.put(rec, call.receiver, *call.arguments)
            env.put(rec + 0x10, env.get(this + 0x19C), env.get(env.get(env.get(this + 0xC) + 0x74) + 8))
            return 0x5511
        env.put(vtable + 0x5C, env.stub("virtual method 0x5c", "thiscall", 1, method))
        view = env.object(0x100, "view", fill=0)
        for word in range(0x40):
            env.put(view + 4 * word, rnd.getrandbits(32) | 0x00020001)
        env.put(view + 8, flags_word)
        env.put(view + 0xD0, flags_kind)
        parent = env.object(0x80, "parent", fill=0)
        env.put(parent + 0x74, view)
        env.put(this + 0xC, parent)
        env.put(this + 0x19C, cached)
        z = env.object(0x100, "z", fill=0)
        for word in range(0x40):
            env.put(z + 4 * word, rnd.getrandbits(32) | 0x00030001)
        env.put(z + 0xE8, current)
        y = env.object(0x20, "y", fill=0)
        env.put(y + 0x14, z)
        x = env.object(0x80, "x", fill=0)
        env.put(x + 0x6C, y)
        env.put(0x537E88, x)
        return {"owner": this}

    return Case(label, SYNC, setup, receiver=lambda t: t["owner"])


def cases(random_source):
    rnd = random_source
    # ---- 0x47cd70: in-range dispatch
    ranges = ((0, 0, 0), (0, 9, 0), (0, 9, 9), (0, 9, 4), (1, 9, 1), (3, 8, 5), (-5, 5, -5), (-5, 5, 5),
              (-5, 5, 0), (-7, -3, -4), (-7, -3, -3), (100, 130, 117))
    for number, (low, high, p) in enumerate(ranges):
        for stride in (STRIDES[number % 5], STRIDES[(number + 2) % 5]):
            yield dispatch_case(f"in range {p} in [{low},{high}] stride {stride}", low, high, p, stride)
    for stride in (4, 12, 36):
        yield dispatch_case(f"stride {stride} neighbour index", 2, 12, 7, stride, present=set(range(2, 13)) - {6, 8})
    yield dispatch_case("zero stride in range", 0, 4, 2, 0)
    for index in range(10):
        low = rnd.randrange(-40, 40)
        high = low + rnd.randrange(0, 12)
        p = rnd.randrange(low, high + 1)
        yield dispatch_case(f"random in range {index}", low, high, p, rnd.choice(STRIDES))
    # ---- missing entry: falls back to 0x43d490
    for number, (low, high, p) in enumerate(((0, 9, 3), (-4, 4, -4), (5, 5, 5), (0, 9, 9), (-6, 2, 2), (0, 9, 0))):
        yield dispatch_case(f"missing entry {p} falls back", low, high, p, STRIDES[number % 5],
                            present={i for i in range(low, high + 1) if i != p})
    for number, (low, high, p) in enumerate(((0, 9, 3), (-4, 4, -4), (7, 7, 7))):
        yield dispatch_case(f"missing entry {p} fallback table wider", low, high, p, STRIDES[number % 5],
                            present={i for i in range(low, high + 1) if i != p}, fallback=(p - 2, p + 3))
        yield dispatch_case(f"missing entry {p} fallback table starts at it", low, high, p, STRIDES[(number + 1) % 5],
                            present={i for i in range(low, high + 1) if i != p}, fallback=(p, p + 4))
    # ---- out of range: the table grows, new entries are empty, fall back
    growth = ((0, 9, 10), (0, 9, 25), (0, 9, -1), (0, 9, -8), (-3, 3, 4), (-3, 3, -4), (50, 60, 40), (50, 60, 90),
              (0, 0, 1), (0, 0, -1), (-2, -2, 6))
    for number, (low, high, p) in enumerate(growth):
        yield dispatch_case(f"grows for {p} in [{low},{high}]", low, high, p, STRIDES[number % 5])
        yield dispatch_case(f"grows for {p} in [{low},{high}] stride {STRIDES[(number + 3) % 5]}", low, high, p,
                            STRIDES[(number + 3) % 5], present=set())
    for index in range(6):
        low = rnd.randrange(-40, 40)
        high = low + rnd.randrange(0, 12)
        p = high + rnd.randrange(1, 9) if index % 2 else low - rnd.randrange(1, 9)
        yield dispatch_case(f"random out of range {index}", low, high, p, rnd.choice(STRIDES))
    # ---- grown entry is nonzero by straddling old bytes: the original takes its second check and calls it
    for number, (low, count, page, tail) in enumerate(((4, 6, 2, (0xE1, 0x5C, 0x93)), (-9, 12, 4, (0x44, 0x88, 0xCC, 0x21, 0x09)),
                                                         (40, 4, 3, (0x77,)), (0, 5, 5, (0x10, 0x20)), (-30, 9, 6, (0xAB, 0xCD, 0xEF)))):
        yield regrown_entry_case(f"regrown entry {number}", low, count, page, tail)

    # ---- the three initialisers
    for function, offset, name in ((INIT_A, 0x35C, "a"), (INIT_B, 0x360, "b"), (INIT_C, 0x360, "c")):
        for root in ("none", "match", "mismatch", "mismatch-late", "deep"):
            for count in (1, 3):
                yield init_case(f"init {name} root {root} count {count}", function, offset, rnd, root=root, count=count)
        yield init_case(f"init {name} null list", function, offset, rnd, root="none", param="null")
        yield init_case(f"init {name} null list match", function, offset, rnd, root="match", param="null")
        for index in range(3):
            yield init_case(f"init {name} random {index}", function, offset, rnd,
                            root=("none", "match", "mismatch")[index], count=1 + index)

    # ---- the initialisers with the owner overlapping the object (store order against 0x4c8220 writes)
    for function, offset, name in ((INIT_A, 0x35C, "a"), (INIT_B, 0x360, "b"), (INIT_C, 0x360, "c")):
        for alias in (-0x5C, -0x60, -0x64, 0x08, 0x0C, 0x10):
            yield init_case(f"init {name} owner overlaps self at {alias:#x}", function, offset, rnd,
                            root="match", count=2, alias=alias)
        yield init_case(f"init {name} owner overlaps self null list", function, offset, rnd, root="none",
                        param="null", alias=-0x5C)
        yield init_case(f"init {name} owner overlaps self null list late", function, offset, rnd, root="none",
                        param="null", alias=0x10)

    # ---- 0x47d780
    for kind in (0x20, 0x1F, 0x21, 0, 0x120, 0xFFFFFF20, 0x8000):
        for flags in (0, 0x10000, 0xFFFE0000, 0x12345678):
            yield sync_case(f"sync changed kind {kind:#x} flags {flags:#x}", 0x1234, 0x4321, kind, flags, rnd)
    for kind in (0x20, 0x1F):
        yield sync_case(f"sync unchanged kind {kind:#x}", 0x7777, 0x7777, kind, 0x55, rnd)
    for index in range(10):
        current = rnd.getrandbits(32)
        cached = current if index % 3 == 0 else rnd.getrandbits(32)
        yield sync_case(f"sync random {index}", current, cached, rnd.choice((0x20, 0x20, 0, rnd.getrandbits(32))),
                        rnd.getrandbits(32), rnd)
    yield sync_case("sync cached zero current zero", 0, 0, 0x20, 1, rnd)
    yield sync_case("sync cached differs by one", 0x100, 0x101, 0x20, 1, rnd)
