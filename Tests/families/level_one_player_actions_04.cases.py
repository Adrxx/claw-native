"""Cases for level_one_player_actions_04: Observed Level 1 player actions batch 4.

Coverage is directed: every branch has explicit cases. Random values only add variety
(contents, extra inputs), never decide which branch is reached.
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

M32 = 0xFFFFFFFF
RAND = 0x4A3050
INTERLOCKED_DECREMENT = 0x5469E8

F_RANDOM_RANGE = 0x4207B0
F_TILE_LOOKUP = 0x4207F0
F_SET4 = 0x4208B0
F_SET14 = 0x420A40
F_SET_DOUBLE = 0x420AD0
F_ADVANCE = 0x420CD0
F_SET_BIT = 0x420FC0
F_NOP = 0x4C9E30
F_TABLE = 0x4DC870

G_RESULT = 0x544E8C

# Table record at 0x537698
T_LOW, T_HIGH, T_DATA, T_SPARE, T_ELSIZE, T_NEWPTR, T_NEWCOUNT = (
    0x5376A0, 0x5376A4, 0x5376A8, 0x5376AC, 0x5376B0, 0x5376B4, 0x5376B8)


def dbl(env, address, value):
    env.write(address, struct.pack("<d", value))


def noise(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


# ---------------------------------------------------------------- 0x4207b0

def rand_case(label, low, high, value):
    def setup(env):
        env.override(RAND, returns(value))
        return None
    return Case(label, F_RANDOM_RANGE, setup, arguments=(low & M32, high & M32))


# ---------------------------------------------------------------- 0x4207f0

def tile_setup(random_source, width, height, shift_x, shift_y, *, cell_kind="mixed", pad=2):
    """A level plane with a clamp size, tile shifts and a grid of cells whose low half indexes an object table."""
    eff_x, eff_y = shift_x & 0x1F, shift_y & 0x1F
    grid_w = (max(width - 1, 0) >> eff_x) + 1
    grid_h = (max(height - 1, 0) >> eff_y) + 1
    cells_values = []
    for index in range(grid_h * grid_w + pad):
        kind = cell_kind
        if kind == "mixed":
            kind = random_source.choice(("object", "object", "object", "eeee", "ffff"))
        if kind == "eeee":
            cells_values.append(0xEEEEEEEE)
        elif kind == "ffff":
            cells_values.append(0xFFFFFFFF)
        elif kind == "empty":
            cells_values.append(0xEEEEEEEE)
        else:
            cells_values.append((random_source.randrange(1, 0xFFFF) << 16) | random_source.randrange(0, 5))
    row_values = [y * grid_w + pad for y in range(grid_h)]
    object_count = 5
    seeds = noise(random_source, 8)

    def setup(env):
        host = env.object(0x80, "host", fill=0)
        plane = env.object(0xA0, "plane", fill=0)
        cells = env.object((len(cells_values) + pad + 4) * 4 + 16, "cells", fill=0x5A)
        rows = env.object(16 + (len(row_values) + 2) * 4, "rows", fill=0x33)
        objects = env.object(object_count * 4, "objects", fill=0)
        log = env.object(0x200, "log", fill=0)
        env.put(host + 0x5C, plane)
        env.put(host + 0x4C, objects)
        env.put(plane + 0x20, cells + 8)
        env.put(plane + 0x24, rows + 8)
        env.put(plane + 0x30, width & M32, height & M32)
        env.put(plane + 0x8C, shift_x)
        env.put(plane + 0x90, shift_y)
        for index, value in enumerate(cells_values):
            env.put(cells + 8 + index * 4, value)
        for index, value in enumerate(row_values):
            env.put(rows + 8 + index * 4, value)
        env.put(rows + 4, 1)  # row -1, read only when the clamped y is -1
        env.put(cells + 4, 0x44445555)
        for index in range(object_count):
            obj = env.object(8, f"tile-object-{index}", fill=0)
            vt = env.object(0x40, f"tile-vtable-{index}", fill=0)
            env.put(obj, vt)
            env.put(objects + index * 4, obj)

            def effect(en, call, index=index, obj=obj):
                n = en.get(log)
                en.put(log + 4 + n * 16, index + 1, call.receiver, len(call.arguments),
                       *(list(call.arguments) + [0, 0])[:2])
                en.put(log, n + 1)
                return (0x1000 + index * 0x111 + seeds[index]) & M32

            env.put(vt + 0x20, env.stub(f"tile-object-{index}::method20", "thiscall", 2, effect))
        return {"host": host, "log": log}
    return setup


def tile_case(random_source, label, width, height, shift_x, shift_y, x, y, **options):
    return Case(label, F_TILE_LOOKUP, tile_setup(random_source, width, height, shift_x, shift_y, **options),
                receiver=lambda t: t["host"], arguments=(x & M32, y & M32))


# ---------------------------------------------------------------- 0x4208b0 / 0x420a40 / 0x420ad0 / 0x420cd0 / 0x420fc0

def filled_object(size, seed_words):
    def setup(env):
        obj = env.object(size, "target", fill=0xC3)
        for index in range(0, size - 3, 4):
            env.put(obj + index, seed_words[index // 4 % len(seed_words)] ^ (index * 0x01010101 & M32))
        return {"obj": obj}
    return setup


def advance_setup(flag, step, accumulator, seed_words):
    def setup(env):
        obj = env.object(0xB8, "advance", fill=0xC3)
        for index in range(0, 0xB8, 4):
            env.put(obj + index, seed_words[index // 4 % len(seed_words)])
        env.put(obj + 0xA0, flag)
        dbl(env, obj + 0x88, step)
        dbl(env, obj + 0xA8, accumulator)
        env.put(G_RESULT, 0x31415926)
        return {"obj": obj}
    return setup


def bits_setup(random_source, size, set_bits=()):
    words = max(1, (size + 31) // 32) if size else 1
    contents = noise(random_source, words + 1)

    def setup(env):
        owner = env.object(0x20, "bitset", fill=0)
        env.put(owner + 8, size)
        if size <= 0x20:
            env.put(owner + 0xC, contents[0] & ((1 << min(size, 32)) - 1 if size else 0))
            storage = None
        else:
            storage = env.object(words * 4 + 8, "bit-storage", fill=0)
            for index in range(words):
                env.put(storage + index * 4, contents[index])
            env.put(owner + 0xC, storage)
        return {"owner": owner, "storage": storage}
    return setup


# ---------------------------------------------------------------- 0x4dc870

def string_object(env, text, refs=1, alloc=None, length=None):
    body = text.encode() + b"\0"
    size = 12 + (len(body) + 3) // 4 * 4 + 8
    obj = env.object(size, "string", fill=0)
    env.put(obj, refs, len(text) if length is None else length, len(body) + 4 if alloc is None else alloc)
    env.write(obj + 12, body)
    return obj + 12


def table_setup(random_source, low, high, index, elsize=4, *, refs=None, hooks=None, log_state=True,
                stale=True, tail_noise=True, vt_swap=False, interlocked=1, stringless=False):
    """Position a table over [low, high] with string cells and a callback object with three virtual methods.

    hooks: dict with optional 'first', 'second' and 'third' mutators run inside the callbacks.
    refs: dict mapping a cell index to a string reference count (so the string is copied).
    """
    hooks = hooks or {}
    refs = refs or {}
    names = noise(random_source, 4)
    count = high - low + 1

    def setup(env):
        table_count = max(count, 1)
        data = env.object(table_count * max(elsize, 4) + 8, "table-cells", fill=0)
        for cell in range(max(count, 0)):
            text = f"cell{cell}-{names[cell % 4] & 0xFFFF:04x}"
            pointer = string_object(env, text, refs=refs.get(cell, 1))
            env.put(data + cell * elsize, pointer)
            for extra in range(1, elsize // 4):
                env.put(data + cell * elsize + extra * 4, names[(cell + extra) % 4])
        env.put(0x537698, 0x0A0B0C0D, 0x0E0F1011)
        env.put(T_LOW, low & M32, high & M32, data)
        env.put(T_SPARE, 0x55)
        env.put(T_ELSIZE, elsize)
        if stale:
            stale_cells = env.object(16, "stale-new-cells", fill=0x77)
            env.put(T_NEWPTR, stale_cells, 3)
        log = env.object(0x400, "log", fill=0)
        queue = env.object(0x40, "queue-index", fill=0xE1)
        env.put(queue + 0x1C, index & M32)
        vt = env.object(0x20, "vtable", fill=0)
        vt2 = env.object(0x20, "vtable2", fill=0)
        owner = env.object(0x20, "owner", fill=0)
        env.put(owner, vt)
        env.put(owner + 0x10, queue)
        tokens = {"owner": owner, "log": log, "data": data, "vt": vt, "vt2": vt2, "queue": queue}

        def record(en, call, tag):
            n = en.get(log)
            arg = call.arguments[0]
            header = en.read(arg - 12, 16) if tag != 2 and arg > 0x1000 else bytes(16)
            words = list(struct.unpack("<4I", header))
            en.put(log + 4 + n * 64, tag, call.receiver, arg, en.get(owner), en.get(T_LOW), en.get(T_HIGH),
                   en.get(T_DATA), en.get(T_ELSIZE), en.get(T_NEWPTR), en.get(T_NEWCOUNT), *words)
            en.put(log, n + 1)

        def make(tag, name, result):
            def effect(en, call):
                record(en, call, tag)
                hook = hooks.get(name)
                if hook:
                    hook(en, tokens, call)
                return result
            return effect

        env.put(vt + 4, env.stub("owner::first", "thiscall", 1, make(1, "first", 0x1111)))
        env.put(vt + 8, env.stub("owner::second", "thiscall", 1, make(2, "second", 0x2222)))
        env.put(vt + 0xC, env.stub("owner::third", "thiscall", 1, make(3, "third", 0x3333)))
        env.put(vt2 + 4, env.stub("owner2::first", "thiscall", 1, make(4, "first2", 0x4444)))
        env.put(vt2 + 8, env.stub("owner2::second", "thiscall", 1, make(5, "second2", 0x5555)))
        env.put(vt2 + 0xC, env.stub("owner2::third", "thiscall", 1, make(6, "third2", 0x6666)))
        if interlocked is not None:
            env.override(INTERLOCKED_DECREMENT, returns(interlocked))
        return tokens
    return setup


def new_table(en, tokens, low, high, elsize, texts=None):
    """Replace the table by a fresh one (used from a callback so the second pass sees different globals)."""
    count = max(high - low + 1, 1)
    data = en.object(count * max(elsize, 4) + 8, "replacement-cells", fill=0)
    for cell in range(high - low + 1):
        pointer = string_object(en, (texts or "repl{}").format(cell), refs=1)
        en.put(data + cell * elsize, pointer)
        for extra in range(1, elsize // 4):
            en.put(data + cell * elsize + extra * 4, 0xBEEF0000 + cell * 16 + extra)
    en.put(T_LOW, low & M32, high & M32, data)
    en.put(T_ELSIZE, elsize)
    return data


def table_case(random_source, label, low, high, index, elsize=4, **options):
    return Case(label, F_TABLE, table_setup(random_source, low, high, index, elsize, **options),
                arguments=(lambda t: t["owner"],))


# ---------------------------------------------------------------- cases

def cases(random_source):
    r = random_source

    # 0x4207b0: random in an inclusive range
    for rand in (0, 1, 2, 3, 7, 0x12345678, 0x7FFFFFFF):
        for low, high in ((0, 9), (5, 5), (-4, 3), (-10, -1), (100, 1000)):
            yield rand_case(f"range [{low},{high}] rand {rand:#x}", low, high, rand)
    for rand in (0x80000001, 0xFFFFFFFF, 0xFFFFFFFE, 0xC0000000, 0x80000000 + 12345):
        for low, high in ((0, 9), (-4, 3), (7, 7)):
            yield rand_case(f"range [{low},{high}] negative rand {rand:#x}", low, high, rand)
    for rand in (0, 1, 2, 0xFFFFFFFF, 0x80000000, 0x12345679):
        for low in (5, -5, 0x7FFFFFFF, -0x80000000):
            yield rand_case(f"empty range at {low} rand {rand:#x}", low, low - 1, rand)
    for rand in (1, 7, 0xFFFFFFFF, 0x80000001):
        for low, high in ((10, 3), (0, -9), (50, -50)):
            yield rand_case(f"reversed range [{low},{high}] rand {rand:#x}", low, high, rand)
    yield rand_case("full range wraps to empty", -0x80000000, 0x7FFFFFFF, 0x10001)
    yield rand_case("full range wraps to empty even", -0x80000000, 0x7FFFFFFF, 0x10002)
    yield rand_case("huge span", -0x40000000, 0x3FFFFFFF, 0x7ABCDEF1)
    yield rand_case("huge span negative rand", -0x40000000, 0x3FFFFFFF, 0xF1234567)
    for _ in range(25):
        low = r.randrange(-5000, 5000)
        high = low + r.randrange(-3, 3000)
        yield rand_case(f"random range {low}..{high}", low, high, r.randrange(0, 1 << 32))

    # 0x4207f0: map cell lookup with clamping
    geometry = (37, 21, 2, 3)
    xs = (-7, 0, 1, 18, 36, 37, 44)
    ys = (-9, 0, 1, 10, 20, 21, 33)
    for x in xs:
        for y in ys:
            yield tile_case(r, f"lookup 37x21 at {x},{y}", *geometry, x, y)
    others = (
        (8, 8, 0, 0), (100, 64, 4, 4), (1, 1, 0, 0), (64, 40, 5, 1), (50, 31, 3, 0), (33, 33, 1, 5),
        (200, 90, 6, 6), (17, 9, 0, 3),
    )
    for width, height, sx, sy in others:
        picks = [(-1, -1), (0, 0), (width - 1, height - 1), (width, height), (width + 9, -4), (-6, height + 3),
                 (width // 2, height // 3), (width - 1, 0), (0, height - 1)]
        for _ in range(3):
            picks.append((r.randrange(-3, width + 3), r.randrange(-3, height + 3)))
        for x, y in picks:
            yield tile_case(r, f"lookup {width}x{height} sh{sx},{sy} at {x},{y}", width, height, sx, sy, x, y)
    for shift in (0x25, 0x40, 0x23):
        for x, y in ((30, 9), (12, 20), (0, 0)):
            yield tile_case(r, f"shift count masked {shift:#x} at {x},{y}", 40, 24, shift, 0x22, x, y)
    for x, y in ((5, 7), (0, 0), (-3, -3)):
        yield tile_case(r, f"empty plane width 0 at {x},{y}", 0, 5, 0, 0, x, y)
        yield tile_case(r, f"empty plane height 0 at {x},{y}", 5, 0, 0, 0, x, y)
    for kind in ("eeee", "ffff", "object"):
        for x, y in ((3, 4), (20, 15)):
            yield tile_case(r, f"all cells {kind} at {x},{y}", 30, 20, 2, 2, x, y, cell_kind=kind)

    # 0x4208b0: four stores
    for _ in range(6):
        words = [r.randrange(0, 1 << 32) for _ in range(4)]
        seeds = noise(r, 6)
        yield Case("store four words", F_SET4, filled_object(0x140, seeds), receiver=lambda t: t["obj"],
                   arguments=tuple(words))
    yield Case("store four zero", F_SET4, filled_object(0x140, noise(r, 6)), receiver=lambda t: t["obj"],
               arguments=(0, 0, 0, 0))
    yield Case("store four max", F_SET4, filled_object(0x140, noise(r, 6)), receiver=lambda t: t["obj"],
               arguments=(M32, M32, M32, M32))
    yield Case("store four distinct small", F_SET4, filled_object(0x140, noise(r, 6)), receiver=lambda t: t["obj"],
               arguments=(1, 2, 3, 4))

    # 0x420a40: fourteen arguments, nine plain stores, fifteen zero stores
    for _ in range(8):
        args = tuple(r.randrange(1, 1 << 32) for _ in range(14))
        yield Case("store fourteen words", F_SET14, filled_object(0x60, noise(r, 8)), receiver=lambda t: t["obj"],
                   arguments=args)
    yield Case("store fourteen ordered", F_SET14, filled_object(0x60, noise(r, 8)), receiver=lambda t: t["obj"],
               arguments=tuple(0x100 + i for i in range(14)))
    yield Case("store fourteen zeros", F_SET14, filled_object(0x60, noise(r, 8)), receiver=lambda t: t["obj"],
               arguments=(0,) * 14)
    yield Case("store fourteen max", F_SET14, filled_object(0x60, noise(r, 8)), receiver=lambda t: t["obj"],
               arguments=(M32,) * 14)

    # 0x420ad0: one double copied to three slots
    interesting = [0.0, -0.0, 1.0, -1.0, 0.5, 3.14159265358979, -2.5e-10, 1e300, -1e300, 5e-324, 2.2250738585072014e-308,
                   float("inf"), float("-inf"), 123456789.123456789, 1.0000000000000002]
    for value in interesting:
        low, high = struct.unpack("<II", struct.pack("<d", value))
        yield Case(f"copy double {value!r}", F_SET_DOUBLE, filled_object(0x100, noise(r, 8)),
                   receiver=lambda t: t["obj"], arguments=(low, high))
    for _ in range(10):
        value = struct.unpack("<d", struct.pack("<Q", r.randrange(0, 1 << 63) & ~(0x7FF << 52) | (r.randrange(1, 0x7FE) << 52)))[0]
        low, high = struct.unpack("<II", struct.pack("<d", value))
        yield Case(f"copy random double {value!r}", F_SET_DOUBLE, filled_object(0x100, noise(r, 8)),
                   receiver=lambda t: t["obj"], arguments=(low, high))
    yield Case("copy quiet nan with payload", F_SET_DOUBLE, filled_object(0x100, noise(r, 8)),
               receiver=lambda t: t["obj"], arguments=(0x12345678, 0x7FF9ABCD))

    # 0x420cd0: integer part of the accumulated double
    steps = (0.0, 0.25, 0.75, 1.0, 2.999, 10.75, 1234567.375, -0.25, -1.5, -3.0, -10.75,
             -1234567.375, 2147483647.0, 2147483648.5, 3000000000.25, -3000000000.25, 4294967296.5, 1e-9, -1e-9)
    accumulators = (0.0, 0.5, 0.25, 0.9, -0.5, -0.9, 7.0, 1.0, -1.0, 12.3)
    for step in steps:
        for acc in accumulators[:4]:
            yield Case(f"advance step {step!r} acc {acc!r}", F_ADVANCE,
                       advance_setup(0, step, acc, noise(r, 6)), receiver=lambda t: t["obj"])
    for step in (0.7, -0.7, 2.5, -2.5, 5.0, 0.0):
        for acc in accumulators[4:]:
            yield Case(f"advance step {step!r} acc {acc!r}", F_ADVANCE,
                       advance_setup(0, step, acc, noise(r, 6)), receiver=lambda t: t["obj"])
    for flag in (1, 2, 0x80000000, M32, 0x100):
        yield Case(f"advance blocked by flag {flag:#x}", F_ADVANCE,
                   advance_setup(flag, 3.75, 0.5, noise(r, 6)), receiver=lambda t: t["obj"])
    for _ in range(14):
        yield Case("advance random", F_ADVANCE,
                   advance_setup(0, r.uniform(-5000.0, 5000.0), r.uniform(-3.0, 3.0), noise(r, 6)),
                   receiver=lambda t: t["obj"])
    for _ in range(6):
        yield Case("advance random accumulating fractions", F_ADVANCE,
                   advance_setup(0, r.choice((0.1, 0.2, 0.3, -0.1, 0.9)) + r.randrange(0, 3), r.uniform(0.0, 0.99),
                                 noise(r, 6)), receiver=lambda t: t["obj"])

    # 0x420fc0: set one bit
    for size in (1, 2, 5, 17, 31, 32):
        for bit in sorted({0, 1, size - 1, size // 2, 31} & set(range(size))):
            yield Case(f"set bit {bit} of inline {size}", F_SET_BIT, bits_setup(r, size),
                       receiver=lambda t: t["owner"], arguments=(bit,))
    for size in (33, 40, 64, 65, 100, 128, 200):
        for bit in sorted({0, 1, 31, 32, 33, size - 1, size // 2, size - 33} & set(range(size))):
            yield Case(f"set bit {bit} of external {size}", F_SET_BIT, bits_setup(r, size),
                       receiver=lambda t: t["owner"], arguments=(bit,))
    for size, bit in ((0, 0), (0, 3), (1, 1), (1, 40), (8, 8), (8, 9), (8, 31), (31, 32), (32, 32), (32, 33),
                      (32, 64), (32, 100), (40, 40), (40, 41), (40, 64), (40, 127), (64, 64), (100, 100),
                      (100, 300), (33, 33), (33, 96)):
        yield Case(f"set bit {bit} beyond size {size}", F_SET_BIT, bits_setup(r, size),
                   receiver=lambda t: t["owner"], arguments=(bit,))

    # 0x4c9e30: does nothing
    for value in (0, 1, 0x12345678, M32):
        yield Case(f"no-op argument {value:#x}", F_NOP, None, arguments=(value,))

    # 0x4dc870: queue of strings indexed by a table that grows on demand
    yield from table_cases(r)


def first_pass_variants():
    # (label, low, high, index)
    return (
        ("in range middle", 3, 12, 7),
        ("in range low edge", 3, 12, 3),
        ("in range high edge", 3, 12, 12),
        ("in range single", 5, 5, 5),
        ("in range negative bounds", -8, -2, -5),
        ("in range spanning zero", -3, 4, 0),
        ("below by one", 3, 12, 2),
        ("below by many", 3, 12, -4),
        ("above by one", 3, 12, 13),
        ("above by many", 3, 12, 21),
        ("below negative", -6, 2, -9),
        ("above negative", -9, -4, -3),
        ("below signed boundary", 0, 6, -1),
        ("above zero crossing", -4, -1, 0),
    )


def table_cases(r):
    for label, low, high, index in first_pass_variants():
        yield table_case(r, f"table {label}", low, high, index)
        yield table_case(r, f"table {label} stale cells absent", low, high, index, stale=False)
    for elsize in (8, 12, 16):
        yield table_case(r, f"in range elsize {elsize}", 2, 9, 6, elsize)
        yield table_case(r, f"in range elsize {elsize} low edge", 2, 9, 2, elsize)
        yield table_case(r, f"in range elsize {elsize} high edge", 2, 9, 9, elsize)
        yield table_case(r, f"below elsize {elsize}", 2, 9, 1, elsize)
        yield table_case(r, f"below far elsize {elsize}", 2, 9, -3, elsize)
        yield table_case(r, f"above by one elsize {elsize}", 2, 9, 10, elsize)
    for low, high, index in ((0, 4, 100), (-5, 5, 30), (10, 20, 9), (10, 20, -40)):
        yield table_case(r, f"far grow {low}..{high} index {index}", low, high, index)
    for _ in range(14):
        low = r.randrange(-30, 30)
        high = low + r.randrange(0, 12)
        index = r.randrange(low - 15, high + 15)
        yield table_case(r, f"random table {low}..{high} index {index}", low, high, index)

    # the owner's string cell is shared, so it is copied before the callback gets it
    yield table_case(r, "shared string copy in range", 3, 12, 7, refs={4: 3})
    yield table_case(r, "shared string copy edge", 3, 12, 12, refs={9: 2}, interlocked=0)
    yield table_case(r, "shared string copy released", 3, 12, 3, refs={0: 5}, interlocked=0)

    # callbacks change the owner's vtable between calls
    def swap_owner(en, tokens, call):
        en.put(tokens["owner"], tokens["vt2"])
    yield table_case(r, "owner vtable swapped by first callback", 3, 12, 7, hooks={"first": swap_owner})
    yield table_case(r, "owner vtable swapped by second callback", 3, 12, 7, hooks={"second": swap_owner})

    def change_index(en, tokens, call):
        en.put(tokens["queue"] + 0x1C, 99)
    yield table_case(r, "queue index changed by callback is not re-read", 3, 12, 7, hooks={"first": change_index})
    yield table_case(r, "queue index changed by second callback", 3, 12, 7, hooks={"second": change_index})

    # callbacks change the table before the second pass
    def second_pass(low, high, elsize, when):
        def hook(en, tokens, call):
            new_table(en, tokens, low, high, elsize)
        return {when: hook}

    for when in ("first", "second"):
        # index 7 is inside the original table 3..12; the replacement table forces each second-pass path
        yield table_case(r, f"second pass in range replacement ({when})", 3, 12, 7,
                         hooks=second_pass(5, 9, 4, when))
        yield table_case(r, f"second pass in range replacement elsize 8 ({when})", 3, 12, 7,
                         hooks=second_pass(1, 8, 8, when))
        yield table_case(r, f"second pass in range elsize 12 low edge ({when})", 3, 12, 7,
                         hooks=second_pass(7, 11, 12, when))
        yield table_case(r, f"second pass in range high edge ({when})", 3, 12, 7,
                         hooks=second_pass(2, 7, 4, when))
        yield table_case(r, f"second pass grows down ({when})", 3, 12, 7,
                         hooks=second_pass(8, 15, 4, when))
        yield table_case(r, f"second pass grows down far ({when})", 3, 12, 7,
                         hooks=second_pass(20, 24, 4, when))
        yield table_case(r, f"second pass grows up ({when})", 3, 12, 7,
                         hooks=second_pass(-3, 6, 4, when))
        yield table_case(r, f"second pass grows up far ({when})", 3, 12, 7,
                         hooks=second_pass(-30, -20, 4, when))
        yield table_case(r, f"second pass grows down elsize 8 ({when})", 3, 12, 7,
                         hooks=second_pass(8, 12, 8, when))
        yield table_case(r, f"second pass grows up by one elsize 8 ({when})", 3, 12, 7,
                         hooks=second_pass(1, 6, 8, when))
        yield table_case(r, f"grow then second pass grows ({when})", 3, 12, 20,
                         hooks=second_pass(22, 30, 4, when))
        yield table_case(r, f"grow then second pass grows up ({when})", 3, 12, -2,
                         hooks=second_pass(-10, -6, 4, when))
        yield table_case(r, f"grow down then second pass in range ({when})", 3, 12, 0,
                         hooks=second_pass(-4, 4, 4, when))

    # the new-cell count from the first grow must be reset before the second pass
    def keep_count(en, tokens, call):
        en.put(T_NEWCOUNT, 5)
    yield table_case(r, "count forced by callback then in range", 3, 12, 20, hooks={"first": keep_count})
    yield table_case(r, "count forced by second callback then in range", 3, 12, 20, hooks={"second": keep_count})

    # callback replaces the table with another whose cell width differs and whose range is empty of the index
    def shrink_far(en, tokens, call):
        new_table(en, tokens, 40, 41, 4)
    yield table_case(r, "second pass far below", 3, 12, 7, hooks={"second": shrink_far})
