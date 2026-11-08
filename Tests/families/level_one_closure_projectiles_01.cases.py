"""Cases for level_one_closure_projectiles_01: Level 1 closure projectile, elemental bullet, rat bomb and flare helpers."""
from clawparity.cases import Case
from clawparity.fixtures import reallocate, release

# Five dispatchers share one shape: a table descriptor at BASE with
#   +4 logger, +8 low, +0xc high, +0x10 entries, +0x14 default entry, +0x18 stride, +0x20 scratch
# and an entry is "present" when its first word is nonzero.  Each falls back to a second dispatcher.
DISPATCHERS = {
    0x410A80: (0x534AB0, 0x473F40),
    0x411030: (0x534BA0, 0x473F40),
    0x4114E0: (0x534A38, 0x473F40),
    0x411990: (0x534B00, 0x473F40),
    0x458280: (0x537AC0, 0x4A36F0),
}
FALLBACK_BASE = 0x538428
LOG_STRING = 0x544B4C
LOG_RESULT = 0x544B14
LOG_ENABLE = 0x544D18
OPERATOR_DELETE = 0x4F6428
REALLOC = 0x4A9070
STRIDES = (4, 8, 12, 16, 36)


def descriptor(env, base, low, high, stride, present, rec, slot, log_mode=4, default="stub", tag=0):
    """Build the table at `base`.  `present` is a set of indexes whose entry has a callback; every in-range
    entry gets distinct nonzero payload words so a wrong index, stride or word changes what is called."""
    count = max(1, high - low + 1)
    size = max(4, count * stride)
    entries = env.object(size, "entries", fill=0)
    stubs = {}
    for index in range(low, high + 1):
        offset = (index - low) * stride
        if offset + 4 > size:
            continue
        for word in range(1, stride // 4):
            env.put(entries + offset + 4 * word, (0x11110000 + (index & 0xFFF) * 16 + word + tag) & 0xFFFFFFFF)
        if index in present or (index - low < 40 and index not in present and False):
            ident = (slot[0] + 1)
            slot[0] += 1

            def effect(env, call, ident=ident):
                env.put(rec + 4 * ident, call.receiver, ident)
                return 0x7000 + ident
            stubs[index] = env.stub(f"callback {tag}:{index}", "thiscall", 0, effect)
            env.put(entries + offset, stubs[index])
        elif index not in present:
            env.put(entries + offset, 0)
    logger = env.object(0x20, "logger", fill=0x5A)
    logger_hook = env.stub(f"logger hook {tag}", "cdecl", 2, lambda env, call: env.put(rec + 0x80, *call.arguments) or 0)
    env.put(logger, logger_hook)
    env.put(logger + 8, 0x1111)
    env.put(logger + 0xC, log_mode)
    env.put(logger + 0x14, env.object(16, "prefix", data=b"claw: ok\x00" + b"\x00" * 7))
    default_entry = env.object(8, "default entry", fill=0)
    if default == "stub":
        env.put(default_entry, env.stub(f"default {tag}", "thiscall", 0,
                                        lambda env, call: env.put(rec + 0x90, call.receiver, 0xDEFA) or 0))
    env.put(base + 4, logger)
    env.put(base + 8, low & 0xFFFFFFFF)
    env.put(base + 0xC, high & 0xFFFFFFFF)
    env.put(base + 0x10, entries)
    env.put(base + 0x14, default_entry)
    env.put(base + 0x18, stride)
    env.put(base + 0x1C, 0x13572468)
    env.put(base + 0x20, 0x2468ACE1)
    return {"entries": entries, "logger": logger, "default": default_entry, "stubs": stubs}


def dispatch_case(label, function, low, high, p, stride, present=None, fallback="stub", grow=None, log_mode=4,
                  default="stub", random_source=None, objects=None, null_owner=False):
    base, fallback_function = DISPATCHERS[function]
    present = set(range(low, high + 1)) if present is None else present

    def setup(env):
        rec = env.object(0x100, "record", fill=0)
        slot = [0]
        env.put(LOG_STRING, env.object(24, "message", data=b"table fault\x00" + b"\x7f" * 12))
        env.put(LOG_RESULT, 0xA5A5A5A5)
        env.put(LOG_ENABLE, 0)
        owner = env.object(0x40, "receiver", fill=0)
        env.put(owner, 0x00510000)
        for word in range(1, 16):
            env.put(owner + 4 * word, 0xC0DE0000 + word)
        table = descriptor(env, base, low, high, stride, present, rec, slot, log_mode, default, tag=1)
        if fallback_function == 0x473F40:
            if fallback == "stub":
                descriptor(env, FALLBACK_BASE, 0, 3, 8, {0, 1, 2, 3}, rec, slot, 4, "stub", tag=2)
                # fallback index p wraps into its own table range
            fb = {"low": 0, "high": 3}
            env.put(FALLBACK_BASE + 8, p & 0xFFFFFFFF)
            env.put(FALLBACK_BASE + 0xC, p & 0xFFFFFFFF)
            env.put(FALLBACK_BASE + 0x10, env.object(8, "fallback entries", fill=0))
            if fallback == "stub":
                stub = env.stub("fallback callback", "thiscall", 0,
                                lambda env, call: env.put(rec + 0xA0, call.receiver, 0xFA11) or 0)
                env.put(env.get(FALLBACK_BASE + 0x10), stub)
            env.put(FALLBACK_BASE + 0x18, 8)
            env.put(FALLBACK_BASE + 0x20, 0x77777777)
        else:
            rtti_data = env.object(16, "rtti data", fill=0x3C)
            vtable = env.object(16, "vtable", fill=0)
            rtti = env.object(0x20, "rtti", fill=0x44)
            env.put(rtti + 0xC, rtti_data)
            env.put(vtable, rtti)
            env.put(owner, vtable + 4)
        if grow == "fail":
            env.override(REALLOC, reallocate(fail=True))
        elif grow == "fail-second":
            env.override(REALLOC, reallocate(fail_from_call=2))
        return {"owner": owner, "rec": rec, **table}

    return Case(label, function, setup, receiver=(0 if null_owner else (lambda t: t["owner"])), arguments=(p & 0xFFFFFFFF,))


def regrown_entry_case(label, function, low, count, target_page, tail, random_source):
    """A one-byte-stride table that grows by one entry below `low`.  The grown first dword straddles the new zero byte and
    the first three old bytes, so it is nonzero and names a stub at 0x710000 + 0x100 * target_page: the original takes its
    second pass (zeroing the scratch word at +0x20 that the grow routine just set) and calls through the regrown entry."""
    base, _ = DISPATCHERS[function]
    p = low - 1
    target = 0x710000 + 0x100 * target_page

    def setup(env):
        rec = env.object(0x100, "record", fill=0)
        env.put(LOG_STRING, env.object(24, "message", data=b"table fault\x00" + b"\x7f" * 12))
        env.put(LOG_RESULT, 0xA5A5A5A5)
        env.put(LOG_ENABLE, 0)
        owner = env.object(0x40, "receiver", fill=0)
        env.put(owner, 0x00510000)
        for word in range(1, 16):
            env.put(owner + 4 * word, 0xC0DE0000 + word)
        table = descriptor(env, base, low, low + count - 1, 4, set(), rec, [0], 4, "stub", tag=1)
        old = bytes([(target >> 8) & 0xFF, (target >> 16) & 0xFF, 0]) + bytes(tail)
        old = old + bytes((0x31 + 7 * i) & 0xFF or 1 for i in range(count - len(old)))
        entries = env.object(count, "byte entries", data=old[:count])
        env.put(base + 0x10, entries)
        env.put(base + 0x18, 1)
        env.put(base + 0x24, 0x3C3C3C3C)
        env.put(base + 0x28, 0x4D4D4D4D)
        # burn stub addresses until the next one is the page-aligned target
        while True:
            def effect(env, call, base=base, rec=rec):
                env.put(rec + 4, call.receiver, 0x7000)
                env.put(rec + 0x40, env.get(base + 0x1C), env.get(base + 0x20), env.get(base + 0x10))
                return 0x7001
            address = env.stub("regrown entry", "thiscall", 0, effect)
            if address >= target:
                break
        if address != target:
            raise AssertionError(f"stub address {address:#x} passed the target {target:#x}")
        return {"owner": owner, "rec": rec, **table}
    return Case(label, function, setup, receiver=lambda t: t["owner"], arguments=(p & 0xFFFFFFFF,))


def simple_object_case(label, function, offset, target_size=24, with_target=True, random_source=None):
    def setup(env):
        owner = env.object(0x180, "owner", fill=0)
        for word in range(0, 0x60):
            env.put(owner + 4 * word, 0x20000000 + word * 0x1013)
        target = env.object(target_size, "flag target", fill=0)
        for word in range(target_size // 4):
            env.put(target + 4 * word, random_source.getrandbits(32) | (1 << (word % 31)))
        env.put(owner + offset, target if with_target else 0)
        return {"owner": owner, "target": target}
    return Case(label, function, setup, receiver=lambda t: t["owner"])


def destroy_case(label, flags, random_source):
    def setup(env):
        obj = env.object(0x30, "object", fill=0xCC)
        for word in range(12):
            env.put(obj + 4 * word, random_source.getrandbits(32))
        return {"owner": obj}
    return Case(label, 0x4030E0, setup, receiver=lambda t: t["owner"], arguments=(flags,))


def cases(random_source):
    rnd = random_source
    # simple flag helpers
    for function, offset in ((0x411CD0, 0x150), (0x414010, 0x154)):
        for index in range(6):
            yield simple_object_case(f"{function:#x} sets the flag {index}", function, offset, 16 + 8 * (index % 3), True, rnd)
        for index in range(2):
            yield simple_object_case(f"{function:#x} no target {index}", function, offset, 16, False, rnd)
    for flags in (0, 1, 2, 3, 0xFE, 0xFF, 0x100, 0x101, 0xFFFFFFFE, 0xFFFFFFFF, 0x80000001, 0x12345600):
        yield destroy_case(f"destroy flags {flags:#x}", flags, rnd)
    for index in range(8):
        yield destroy_case(f"destroy random flags {index}", rnd.getrandbits(32), rnd)

    ranges = ((0, 0, 0), (0, 9, 0), (0, 9, 9), (0, 9, 4), (1, 9, 1), (3, 8, 5), (-5, 5, -5), (-5, 5, 5),
              (-5, 5, 0), (-7, -3, -4), (-7, -3, -3), (100, 130, 117))
    for function in DISPATCHERS:
        name = f"{function:#x}"
        for number, (low, high, p) in enumerate(ranges):
            stride = STRIDES[number % len(STRIDES)]
            yield dispatch_case(f"{name} dispatches {p} in [{low},{high}] stride {stride}", function, low, high, p, stride)
        for stride in (4, 12):
            yield dispatch_case(f"{name} stride {stride} neighbour index", function, 2, 12, 7, stride,
                                present=set(range(2, 13)) - {6, 8})
        # a missing entry falls through to the second dispatcher
        for number, (low, high, p) in enumerate(((0, 9, 3), (-4, 4, -4), (5, 5, 5), (0, 9, 9))):

            yield dispatch_case(f"{name} missing entry {p} falls back", function, low, high, p,
                                STRIDES[(number + 1) % len(STRIDES)], present={i for i in range(low, high + 1) if i != p})
        # out of range: the table grows, new entries are empty, fall back
        growth = ((0, 9, 10), (0, 9, 25), (0, 9, -1), (0, 9, -8), (-3, 3, 4), (-3, 3, -4), (50, 60, 40), (50, 60, 90))
        for number, (low, high, p) in enumerate(growth):
            yield dispatch_case(f"{name} grows for {p} in [{low},{high}]", function, low, high, p, STRIDES[number % 5],
                                present=set(range(low, high + 1)))
        yield dispatch_case(f"{name} zero stride in range", function, 0, 4, 2, 0)
        for index in range(3):
            low = rnd.randrange(-40, 40)
            high = low + rnd.randrange(0, 12)
            p = rnd.randrange(low, high + 1)
            yield dispatch_case(f"{name} random in range {index}", function, low, high, p, rnd.choice(STRIDES))
            p = high + rnd.randrange(1, 9) if index % 2 else low - rnd.randrange(1, 9)
            yield dispatch_case(f"{name} random out of range {index}", function, low, high, p, rnd.choice(STRIDES))
    # 0x458280 only: a random hole in a random table reaches the original 0x4a36f0 (RTTI lookup via IsBadReadPtr)
    for index in range(4):
        low = rnd.randrange(-30, 30)
        high = low + rnd.randrange(1, 12)
        hole = rnd.randrange(low, high + 1)
        yield dispatch_case(f"0x458280 random hole {index}", 0x458280, low, high, hole, rnd.choice(STRIDES),
                            present=set(range(low, high + 1)) - {hole})
    # second pass after a successful grow: one-byte stride puts old table bytes into the new entry's first word
    for number, function in enumerate(DISPATCHERS):
        name = f"{function:#x}"
        yield regrown_entry_case(f"{name} regrown entry second pass", function, 4 + number, 6, 2 + number % 2, (0xE1, 0x5C, 0x93), rnd)
        yield regrown_entry_case(f"{name} regrown entry negative low", function, -9 - number, 12, 4, (0x44, 0x88, 0xCC, 0x21, 0x09), rnd)
        yield regrown_entry_case(f"{name} regrown entry minimal", function, 40, 4, 3, (0x77,), rnd)
