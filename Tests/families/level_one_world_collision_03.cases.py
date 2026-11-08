"""Cases for level_one_world_collision_03: Level 1 world and collision entries, batch 3."""
from clawparity.cases import Case
from clawparity.fixtures import allocate
from clawparity.world import resource_manager

SCAN = 0x4CDA10
DESTROY = 0x4CDCB0
GET_C = 0x4CDDC0
SIZE_14 = 0x4CDE00
HIT_TEST = 0x4CDE10
SIZE_28 = 0x4CDE40
CTOR = 0x4D03B0
LOAD = 0x4D0450
DIMS = 0x4D0CD0
CLEAR = 0x4F4A90

OPERATOR_NEW = 0x4F63EC
COPY_RECT = 0x546D58

M32 = 0xFFFFFFFF
EE = 0xEEEEEEEE
FF = 0xFFFFFFFF


def u(value):
    return value & M32


def this_of(tokens):
    return tokens["this"]


# ---------------------------------------------------------------- tiny functions

def tiny_cases(rng):
    for index in range(10):
        words = [rng.getrandbits(32) for _ in range(8)]
        if index == 0:
            words[3] = 0
        elif index == 1:
            words[3] = M32
        elif index == 2:
            words[3] = 0x80000000

        def setup(env, words=words):
            return {"this": env.object(32, "record", words=words)}
        yield Case(f"get word at +0xc #{index}", GET_C, setup, receiver=this_of,
                   arguments=(rng.getrandbits(32), rng.getrandbits(32)))
    yield Case("constant 0x14", SIZE_14)
    yield Case("constant 0x28", SIZE_28)

    def clear_setup(words):
        def setup(env):
            return {"this": env.object(16, "pair", words=words)}
        return setup
    for index in range(6):
        words = [rng.getrandbits(32) | 0x01010101 for _ in range(4)]
        yield Case(f"clear pair #{index}", CLEAR, clear_setup(words), receiver=this_of)
    yield Case("clear pair already zero", CLEAR, clear_setup([0, 0, 7, 9]), receiver=this_of)


def hit_cases(rng):
    def make(left, top, right, bottom, inside, outside, noise):
        def setup(env):
            words = [0] * 10
            words[3] = outside
            words[4] = inside
            words[5], words[6], words[7], words[8] = left, top, right, bottom
            words[0], words[1], words[2], words[9] = noise
            return {"this": env.object(40, "region", words=[u(w) for w in words])}
        return setup

    def case(label, bounds, x, y):
        left, top, right, bottom = bounds
        inside, outside = rng.getrandbits(32) | 0x10000, rng.getrandbits(32) | 0x01
        noise = [rng.getrandbits(32) for _ in range(4)]
        return Case(label, HIT_TEST, make(left, top, right, bottom, inside, outside, noise),
                    receiver=this_of, arguments=(u(x), u(y)))

    bounds = (-5, 3, 20, 40)
    left, top, right, bottom = bounds
    for xl, x in (("left-1", left - 1), ("left", left), ("mid", 7), ("right", right), ("right+1", right + 1)):
        for yl, y in (("top-1", top - 1), ("top", top), ("mid", 22), ("bottom", bottom), ("bottom+1", bottom + 1)):
            yield case(f"hit x {xl} y {yl}", bounds, x, y)
    # signed comparison: negative and large bounds
    yield case("signed: positive x above negative left", (-10, -10, 10, 10), 5, 5)
    yield case("signed: negative x inside", (-10, -10, 10, 10), -10, -10)
    yield case("signed: min x", (-10, -10, 10, 10), -0x80000000, 0)
    yield case("signed: max y", (-10, -10, 10, 10), 0, 0x7FFFFFFF)
    yield case("signed: huge bounds", (-0x80000000, -0x80000000, 0x7FFFFFFF, 0x7FFFFFFF), 0x12345678, -0x12345678)
    yield case("inverted bounds", (10, 10, -10, -10), 0, 0)
    for index in range(30):
        lo_x, lo_y = rng.randrange(-300, 300), rng.randrange(-300, 300)
        bnd = (lo_x, lo_y, lo_x + rng.randrange(0, 200), lo_y + rng.randrange(0, 200))
        yield case(f"hit random #{index}", bnd, rng.randrange(-400, 600), rng.randrange(-400, 600))


# ---------------------------------------------------------------- 0x4d0cd0 (dimensions)

def dims_cases(rng):
    first = [0, 1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 31, 32, 33, 64, 100, 255, 256, 1000, 1023, 1024, 0x10000,
             0x40000000, 0x7FFFFFFF, -1, -2, -100, -0x80000000]
    second = [1, 2, 3, 7, 0, -3, 0x7FFFFFFF, 99]

    def make(words):
        def setup(env):
            return {"this": env.object(0xA0, "dimension-record", words=words)}
        return setup

    for index, value in enumerate(first):
        words = [rng.getrandbits(32) for _ in range(40)]
        words[0x28 // 4] = rng.randrange(1, 1000)
        words[0x2C // 4] = rng.randrange(1, 1000) if index % 3 else rng.getrandbits(32)
        arg2 = second[index % len(second)]
        yield Case(f"dimensions {value} x {arg2}", DIMS, make(words), receiver=this_of,
                   arguments=(u(value), u(arg2)))
    for index in range(25):
        words = [rng.getrandbits(32) for _ in range(40)]
        arg1 = rng.choice([rng.getrandbits(32), rng.randrange(0, 5000), 1 << rng.randrange(0, 31),
                           (1 << rng.randrange(1, 31)) - 1])
        yield Case(f"dimensions random #{index}", DIMS, make(words), receiver=this_of,
                   arguments=(arg1, rng.getrandbits(32)))


# ---------------------------------------------------------------- 0x4d03b0 (constructor)

def ctor_cases(rng):
    for index in range(12):
        words = [rng.getrandbits(32) for _ in range(0x58)]
        args = [rng.getrandbits(32) for _ in range(3)]
        if index == 0:
            args = [0, 0, 0]
        elif index == 1:
            args = [M32, M32, M32]

        def setup(env, words=words):
            return {"this": env.object(0x160, "constructed", words=words)}
        yield Case(f"construct #{index}", CTOR, setup, receiver=this_of, arguments=tuple(args))


# ---------------------------------------------------------------- 0x4cdcb0 (palette conversion loop)

SHIFT_GLOBALS = (0x54135C, 0x541360, 0x541368, 0x54136C, 0x541370)


def converter_entry(env, rng_words, bpp=16, index=5, break_at=None):
    """One object reached by the loop in 0x4cdcb0, with the whole chain that 0x4d2140 reads."""
    entry = env.object(0x150, "converted-object", words=rng_words)
    owner = env.object(0x20, "chain-a", fill=0)
    chain_b = env.object(0x14, "chain-b", fill=0)
    chain_c = env.object(0x1C, "chain-c", fill=0)
    chain_d = env.object(0x68, "chain-d", fill=0)
    chain_e = env.object(0x14, "chain-e", fill=0)
    chain_f = env.object(0x10, "chain-f", fill=0)
    palette = env.object(1024, "palette", words=[(rng_words[i % len(rng_words)] * 2654435761 + i) & M32
                                                  for i in range(256)])
    env.put(entry + 0xC, owner)
    env.put(entry + 0x144, u(index))
    env.put(owner + 4, chain_b)
    env.put(owner + 0x18, chain_d)
    env.put(chain_b + 0x10, chain_c)
    env.put(chain_c + 0x18, bpp)
    env.put(chain_d + 0x64, 0 if break_at == "e" else chain_e)
    env.put(chain_e + 0x10, chain_f)
    env.put(chain_f + 0xC, 0 if break_at == "palette" else palette)
    return entry


def destroy_cases(rng):
    def make(specs, count_override, shifts):
        def setup(env):
            for address, value in zip(SHIFT_GLOBALS, shifts):
                env.put(address, value)
            entries = [converter_entry(env, [rng_word for rng_word in words], **spec) for spec, words in specs]
            table = env.object(4 * max(1, len(entries)) + 8, "entry-table", fill=0)
            for position, entry in enumerate(entries):
                env.put(table + 4 * position, entry)
            this = env.object(0x50, "container", fill=0)
            env.put(this + 0x38, table)
            env.put(this + 0x3C, len(entries) if count_override is None else count_override)
            return {"this": this, "entries": entries}
        return setup

    def shifts():
        return [rng.choice([10, 11, 0, 5]), rng.choice([5, 6, 0, 2]), rng.randrange(0, 8), rng.randrange(0, 8),
                rng.randrange(0, 8)]

    def words():
        return [rng.getrandbits(32) for _ in range(8)]

    yield Case("loop: no entries", DESTROY, make([], 0, shifts()), receiver=this_of)
    yield Case("loop: negative count", DESTROY, make([({}, words())], -3, shifts()), receiver=this_of)
    yield Case("loop: one 16-bit entry", DESTROY, make([({"bpp": 16, "index": 7}, words())], None, [11, 5, 3, 2, 3]),
               receiver=this_of)
    yield Case("loop: one 8-bit entry untouched", DESTROY, make([({"bpp": 8, "index": 7}, words())], None, shifts()),
               receiver=this_of)
    specs = [({"bpp": 16, "index": 1}, words()), ({"bpp": 8, "index": 2}, words()),
             ({"bpp": 16, "index": 255}, words()), ({"bpp": 24, "index": 3}, words()),
             ({"bpp": 16, "index": 0}, words()), ({"bpp": 32, "index": 4}, words()),
             ({"bpp": 15, "index": 4}, words()), ({"bpp": 0, "index": 4}, words())]
    yield Case("loop: mixed depths", DESTROY, make(specs, None, [11, 5, 3, 2, 3]), receiver=this_of)
    yield Case("loop: count limits the walk", DESTROY, make(specs, 3, shifts()), receiver=this_of)
    specs = [({"bpp": 16, "index": -1}, words()), ({"bpp": 16, "index": 256}, words()),
             ({"bpp": 16, "index": 0x7FFFFFFF}, words()), ({"bpp": 16, "index": 0x80000000}, words()),
             ({"bpp": 16, "index": 6, "break_at": "e"}, words()),
             ({"bpp": 16, "index": 6, "break_at": "palette"}, words())]
    yield Case("loop: invalid palette index and missing chain", DESTROY, make(specs, None, shifts()),
               receiver=this_of)
    for count in range(1, 7):
        for _ in range(3):
            specs = [({"bpp": rng.choice([16, 16, 16, 8, 24]), "index": rng.randrange(0, 256)}, words())
                     for _ in range(count)]
            yield Case(f"loop: random {count} entries", DESTROY, make(specs, None, shifts()), receiver=this_of)


# ---------------------------------------------------------------- 0x4cda10 (scan)

def scan_world(width, height, shift_x, shift_y, grid, results, stride_extra, base_offset, noise):
    """grid[row][col] holds the raw tile word (EE, FF, or a handler index with arbitrary high bits)."""
    cols = ((width - 1) >> shift_x) + 1
    rows = ((height - 1) >> shift_y) + 1

    def setup(env):
        handler_count = 8
        log = env.object(4 + 16 * 1200, "handler-log", fill=0)
        result_table = env.object(4 * len(results), "handler-results", words=[u(r) for r in results])

        def make_handler(number):
            # thiscall slot +0x20: ECX is the tile handler object, two stack arguments are local x and y.
            # The result depends on which handler object is the receiver, and the receiver is logged.
            def handler(env, call):
                count = env.get(log)
                env.put(log + 4 + 16 * count, call.receiver, call.arguments[0], call.arguments[1], number)
                env.put(log, count + 1)
                return env.get(result_table + 4 * ((count + number) % len(results)))
            return handler

        objects = []
        for number in range(handler_count):
            stub = env.stub(f"tile handler {number}", "thiscall", 2, make_handler(number))
            vtable = env.object(0x40, f"handler-vtable-{number}", words=[0x1000 + i for i in range(16)])
            env.put(vtable + 0x20, stub)
            objects.append(env.object(16, f"handler-{number}", words=[vtable, 0x600 + number, 0, 0]))
        handlers = env.object(4 * handler_count, "handler-table", words=objects)
        stride = cols + stride_extra
        tiles = env.object(4 * (base_offset + rows * stride) + 4, "tile-data", words=[noise] * (base_offset + rows * stride))
        row_table = env.object(4 * rows, "row-offsets", words=[base_offset + row * stride for row in range(rows)])
        for row in range(rows):
            for col in range(cols):
                env.put(tiles + 4 * (base_offset + row * stride + col), u(grid[row][col]))
        plane = env.object(0x98, "tile-plane", fill=0xA5)
        env.put(plane + 0x20, tiles)
        env.put(plane + 0x24, row_table)
        env.put(plane + 0x30, width)
        env.put(plane + 0x34, height)
        env.put(plane + 0x8C, shift_x)
        env.put(plane + 0x90, shift_y)
        this = env.object(0x70, "scanner", fill=0x5A)
        env.put(this + 0x4C, handlers)
        env.put(this + 0x5C, plane)
        return {"this": this, "log": log, "objects": objects}
    return setup


def scan_cases(rng):
    width, height, shift_x, shift_y = 37, 40, 3, 4
    cols, rows = 5, 3

    def random_tile():
        return (rng.getrandbits(16) << 16) | rng.randrange(0, 8)

    all_valid = [[random_tile() for _ in range(cols)] for _ in range(rows)]
    all_ee = [[EE] * cols for _ in range(rows)]
    all_ff = [[FF] * cols for _ in range(rows)]
    mixed = [[0x00010001, EE, 0xABCD0002, FF, 0x00070003],
             [FF, 0x00000004, EE, 0x12340005, 0xFFFF0006],
             [0x00000007, EE, FF, 0x00000000, 0xEEEE0001]]
    all_valid[1][2] = 0xFFFF0003  # still not the -1 marker
    grids = (("valid", all_valid), ("empty-ee", all_ee), ("empty-ff", all_ff), ("mixed", mixed))
    scans = [(-10, 20, 50, 7), (0, 5, 36, 9), (5, -8, 30, 11), (3, 60, 45, 5), (10, 17, 10, 4),
             (50, 20, -10, 7), (36, 0, 0, 6), (30, 70, 2, 9), (-5, 16, -30, 3), (100, 20, 80, 8),
             (0, 39, 36, 1), (36, 16, 0, 1), (2, 2, 3, 1000), (20, 33, 4, 1000), (8, 8, 8, 3)]
    sequences = [[0], [2], [0, 0, 1], [0x101, 0, 0xFFFFFFFF, 1, 0], [1]]
    for grid_name, grid in grids:
        for number, scan in enumerate(scans):
            sequence = sequences[number % len(sequences)] if grid_name != "empty-ee" else [1]
            setup = scan_world(width, height, shift_x, shift_y, grid, sequence, 1 + number % 3, number % 4,
                               rng.getrandbits(32))
            yield Case(f"scan {grid_name} {scan} results {sequence}", SCAN, setup, receiver=this_of,
                       arguments=tuple(u(v) for v in scan))
    # every handler result combination on the all-valid grid for a forward and a backward walk
    for sequence in ([0], [1], [0, 1], [0, 0, 0, 1], [3, 1], [0, 0, 0, 0, 0, 0, 0, 0, 1], [0xFFFFFFFF], [0x80000001], [0x100]):
        for scan in ((-4, 9, 45, 6), (44, 9, -4, 6), (12, 25, 12, 5)):
            setup = scan_world(width, height, shift_x, shift_y, all_valid, sequence, 2, 1, 0x77777777)
            yield Case(f"scan valid {scan} results {sequence}", SCAN, setup, receiver=this_of,
                       arguments=tuple(u(v) for v in scan))
    # different geometry: swapped shifts expose confusion between x and y
    for _ in range(40):
        shift_x2, shift_y2 = rng.randrange(0, 6), rng.randrange(0, 6)
        width2, height2 = rng.randrange(1, 200), rng.randrange(1, 200)
        cols2 = ((width2 - 1) >> shift_x2) + 1
        rows2 = ((height2 - 1) >> shift_y2) + 1
        grid2 = [[rng.choice([EE, FF, random_tile(), random_tile(), random_tile()]) for _ in range(cols2)]
                 for _ in range(rows2)]
        x1, x2 = rng.randrange(-30, width2 + 30), rng.randrange(-30, width2 + 30)
        y = rng.randrange(-30, height2 + 30)
        step = rng.randrange(1, 40)
        sequence = [rng.choice([0, 0, 0, 1, 2]) for _ in range(rng.randrange(1, 12))]
        setup = scan_world(width2, height2, shift_x2, shift_y2, grid2, sequence, rng.randrange(0, 3),
                           rng.randrange(0, 5), rng.getrandbits(32))
        yield Case(f"scan random {width2}x{height2} shifts {shift_x2},{shift_y2} x {x1}..{x2} y {y} step {step}",
                   SCAN, setup, receiver=this_of, arguments=(u(x1), u(y), u(x2), step))


# ---------------------------------------------------------------- 0x4d0450 (loader)

def copy_rect(env, call):
    env.write(call.arguments[0], env.read(call.arguments[1], 16))
    return 1


def frame_list(env, slots, lo, hi, count, dims):
    """The frame-list object whose first slot 0x4d0450 inspects when flag 0x10 is set."""
    record = env.object(0x70, "frame-list", fill=0)
    capacity = max(count, hi + 1, len(slots), 1)
    table = env.object(4 * capacity, "frame-slots", fill=0)
    for position, slot in enumerate(slots):
        if slot is not None:
            frame = env.object(0x20, f"frame-{position}", fill=0)
            env.put(frame + 0x10, *dims[position % len(dims)])
            env.put(table + 4 * position, frame)
    env.put(record + 0x14, table)
    env.put(record + 0x18, count)
    env.put(record + 0x64, lo, hi)
    return record


def loader(garbage, text=b"", count=0, entries=None, flags=0, magic=0xA0, bucket_count=17, preset=None,
           dims=(3, 2, 4, 5), start=(10, 7), scale=(100, 50), word78=0x33, pixel_origin=0x80, pixel_flags=0x1234,
           rect=(1, 2, 30, 40), name=b"sprite", pointer_route=None, offset=0, new_fail=False, pixels=None,
           level_fields=(0, 0), extra=(0xCAFE, 0xBEEF)):
    """Build the descriptor, the target and the level of 0x4d0450. Returns a setup function."""
    def setup(env):
        env.override(COPY_RECT, copy_rect)
        if new_fail:
            env.override(OPERATOR_NEW, allocate(fail=True))
        entry_values = {}
        for key, value in (entries or {}).items():
            entry_values[key] = value(env) if callable(value) else value
        manager = resource_manager(env, entry_values, bucket_count, "sprite-map")
        level = env.object(0x40, "level", fill=0)
        env.put(level + 0x10, manager)
        env.put(level + 8, level_fields[0])
        env.put(level + 0x24, level_fields[1])
        target = env.object(0x160, "target", words=list(garbage))
        env.put(target + 0xC, level)
        data, size, capacity, grow, array_vtable = 0, 0, 0, 0, 0x5108FC
        if preset is not None:
            values, capacity, grow = preset
            size = len(values)
            capacity = max(capacity, size)
            data = env.object(4 * max(capacity, 1), "array-data", fill=0)
            for position, value in enumerate(values):
                env.put(data + 4 * position, value(env) if callable(value) else value)
        env.put(target + 0x9C, array_vtable, data, size, capacity, grow, 0)
        text_object = env.object(len(text) + 16, "text", fill=0)
        env.write(text_object, text)
        n = dims[2] * dims[3]
        pixel_object = env.object(4 * max(n, 1) + 16, "pixels", fill=0)
        env.write(pixel_object, bytes((7 * i + 3) & 0xFF for i in range(4 * max(n, 0))) if pixels is None else pixels)
        descriptor = env.object(0xA0, "descriptor", fill=0)
        env.write(descriptor + 0x10, name + b"\0")
        env.put(descriptor, magic)
        env.put(descriptor + 8, flags)
        env.put(descriptor + 0x58, dims[0], dims[1], dims[2], dims[3], u(start[0]), u(start[1]), scale[0], scale[1],
                word78)
        env.put(descriptor + 0x7C, count)
        env.put(descriptor + 0x80, pixel_flags)
        env.put(descriptor + 0x84, u(pixel_object - offset))
        env.put(descriptor + 0x88, u(text_object - offset))
        arg2 = offset
        pointer_extra = 0
        if pointer_route is not None:
            pointer_extra = pointer_route[0]
            arg2 = u(pointer_route[1] if pointer_route[1] is not None else -pointer_extra)
            env.put(descriptor + 0x84, u(pixel_object - arg2))
            env.put(descriptor + 0x88, u(text_object - arg2))
        env.put(descriptor + 0x8C, pointer_extra)
        env.put(descriptor + 0x90, pixel_origin)
        rect_words = list(rect) if rect is not None else [0x80000000, 0x11111111, 0x22222222, 0x33333333]
        rect_object = env.object(16, "rect", words=[u(v) for v in rect_words])
        return {"this": target, "descriptor": descriptor, "rect": rect_object, "offset": arg2}
    return setup


def load_case(label, garbage, **options):
    setup = loader(garbage, **options)
    return Case(label, LOAD, setup, receiver=this_of,
                arguments=(lambda t: t["descriptor"], lambda t: t["offset"], lambda t: t["rect"]))


def load_cases(rng):
    def garbage():
        return [rng.getrandbits(32) for _ in range(0x58)]

    def frames_of(slots, lo, hi, count, dims=((6, 4), (9, 3), (2, 8))):
        return lambda env: frame_list(env, slots, lo, hi, count, dims)

    # ---- guard
    for magic in (0x9F, 0xA1, 0, M32, 0xA0 << 8):
        yield load_case(f"descriptor magic {magic:#x} rejected", garbage(), magic=magic)

    # ---- no tokens, plain flags
    for flags in (0, 1, 2, 4, 8, 12, 13, 3, 0x20):
        yield load_case(f"no tokens flags {flags:#x}", garbage(), flags=flags)
        yield load_case(f"no tokens flags {flags:#x} no rect", garbage(), flags=flags, rect=None)
    for name in (b"", b"a", b"ab", b"abc", b"abcd", b"abcde", b"fedcba9876543210" * 4 + b"x"[:0]):
        yield load_case(f"name {len(name)} bytes", garbage(), name=name, rect=None)
    yield load_case("name 71 bytes", garbage(), name=bytes(range(65, 65 + 71)), flags=1)
    yield load_case("rect with large values", garbage(), rect=(-50, -60, 70, 90), flags=1)
    yield load_case("rect with equal edges", garbage(), rect=(5, 6, 5, 6), flags=1)
    yield load_case("rect with inverted edges", garbage(), rect=(30, 40, 3, 2), flags=1)
    yield load_case("rect with odd extents", garbage(), rect=(0, 0, 8, 12), flags=0)
    yield load_case("rect first word 0x7fffffff", garbage(), rect=(0x7FFFFFFF, 9, 100, 100), flags=1)

    # ---- scaling and positions
    for start in ((10, 7), (0, 0), (-10, -7), (250, 300), (-250, 400), (33, -2)):
        for flags in (0, 1, 4, 8, 12, 5, 9):
            yield load_case(f"start {start} flags {flags:#x}", garbage(), start=start, flags=flags)
    for scale in ((100, 50), (0, 0), (250, 3), (1, 999), (-100, -50), (50, -20)):
        yield load_case(f"scale {scale}", garbage(), scale=scale, start=(17, -9))
        yield load_case(f"scale {scale} unscaled", garbage(), scale=scale, flags=1, start=(17, -9))
    for dims in ((1, 1, 1, 1), (6, 6, 5, 5), (2, 9, 3, 1), (9, 2, 1, 6), (5, 3, 0, 0), (4, 4, 1, 0), (3, 3, 0, 4)):
        yield load_case(f"dims {dims}", garbage(), dims=dims, flags=0 if dims[2] * dims[3] == 0 else 12, start=(5, 6))
    yield load_case("no rect with empty pixel data", garbage(), dims=(2, 2, 0, 0), rect=None)

    # ---- allocation failure only matters while nothing is copied
    yield load_case("allocation fails, nothing to copy", garbage(), dims=(3, 3, 0, 0), new_fail=True, rect=None)
    yield load_case("allocation fails, nothing to copy, rect", garbage(), dims=(3, 3, 0, 0), new_fail=True)

    # ---- tokens and lookup
    value_a, value_b, value_c = rng.getrandbits(32) | 1, rng.getrandbits(32) | 1, rng.getrandbits(32) | 1
    table = {b"alpha": value_a, b"beta": value_b, b"gamma": value_c, b"Zeta7": 0x7777}
    yield load_case("one token found", garbage(), text=b"alpha", count=1, entries=table)
    yield load_case("two tokens found", garbage(), text=b"alpha beta", count=2, entries=table)
    yield load_case("three tokens with separators", garbage(), text=b"  alpha\x01\x02beta\t/gamma  ", count=3,
                    entries=table)
    yield load_case("token not found stores zero", garbage(), text=b"nothere alpha", count=2, entries=table)
    yield load_case("count larger than tokens", garbage(), text=b"alpha", count=4, entries=table)
    yield load_case("count smaller than tokens", garbage(), text=b"alpha beta gamma", count=2, entries=table)
    yield load_case("only separators", garbage(), text=b"   \x01\x7f"[:4], count=2, entries=table)
    yield load_case("empty text", garbage(), text=b"", count=3, entries=table)
    yield load_case("word characters 0x30 and 0x7f", garbage(), text=b"0 \x7f Zeta7 0\x7f", count=4,
                    entries={b"0": 0x1010, b"\x7f": 0x2020, b"0\x7f": 0x3030, b"Zeta7": 0x7777})
    yield load_case("0x2f and high bytes separate words", garbage(), text=b"ab/cd\x80ef\xffgh", count=5,
                    entries={b"ab": 0x11, b"cd": 0x22, b"ef": 0x33, b"gh": 0x44})
    yield load_case("long word", garbage(), text=b"w" * 96 + b" alpha", count=2,
                    entries={b"w" * 96: 0x4242, b"alpha": 0x2424})
    yield load_case("single bucket chain", garbage(), text=b"gamma alpha beta Zeta7", count=4, entries=table,
                    bucket_count=1)
    yield load_case("two buckets", garbage(), text=b"gamma alpha beta Zeta7", count=4, entries=table, bucket_count=2)
    yield load_case("prefix words do not match", garbage(), text=b"alph alphaa alpha", count=3, entries=table,
                    bucket_count=1)
    yield load_case("text offset 1", garbage(), text=b"alpha beta", count=2, entries=table, offset=1)
    yield load_case("text offset 3 and pixels", garbage(), text=b"beta gamma", count=2, entries=table, offset=3,
                    flags=1)
    yield load_case("many tokens grow the array", garbage(), text=b" ".join(b"alpha beta gamma Zeta7 nope".split() * 3),
                    count=15, entries=table)
    yield load_case("tokens fill preset array", garbage(), text=b"alpha beta gamma", count=3, entries=table,
                    preset=([0x1111, 0x2222, 0x3333, 0x4444], 8, 0))
    yield load_case("tokens overwrite and extend array", garbage(), text=b"alpha beta gamma Zeta7 beta", count=5,
                    entries=table, preset=([0x1111, 0x2222], 3, 0))
    yield load_case("tokens grow with explicit step", garbage(), text=b"alpha beta gamma Zeta7 beta", count=5,
                    entries=table, preset=([0x1111], 1, 6))
    yield load_case("tokens into empty array with step", garbage(), text=b"alpha beta", count=2, entries=table,
                    preset=([], 0, 2))

    # ---- frame list (flag 0x10)
    ok_slots = [None, "a", "b", None, "c"]
    yield load_case("frame list: first valid slot is index 1", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of(ok_slots, 0, 4, 5)})
    yield load_case("frame list: first slot valid", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of(["a", "b"], 0, 1, 2, ((7, 3),))})
    yield load_case("frame list: low bound skips slots", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of(["a", "b", "c", "d"], 2, 3, 4)})
    yield load_case("frame list: high bound stops short", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of(["a", "b", "c", "d"], 0, 0, 4)})
    yield load_case("frame list: slot at high bound", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of([None, None, None, "d"], 0, 3, 4)})
    yield load_case("frame list: slot just above the high bound ignored", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of([None, None, "c", "d"], 0, 1, 4)})
    yield load_case("frame list: all slots empty", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of([None, None, None], 0, 2, 3)})
    yield load_case("frame list: no slots", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of([], 0, 0, 0)})
    yield load_case("frame list: negative slot count", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of([], 0, 0, -2)})
    yield load_case("frame list: bounds exclude every slot", garbage(), flags=0x10, text=b"fr", count=1,
                    entries={b"fr": frames_of(["a", "b"], 5, 9, 2)})
    for flags in (0x10, 0x11, 0x14, 0x18, 0x1C, 0x1D):
        yield load_case(f"frame list flags {flags:#x}", garbage(), flags=flags, text=b"fr other", count=2,
                        entries={b"fr": frames_of([None, "a", "b"], 0, 2, 3, ((6, 5), (11, 4)))},
                        start=(12, 9))
    yield load_case("frame list preset in array", garbage(), flags=0x10, count=0,
                    preset=([frames_of([None, "x"], 0, 1, 2, ((5, 4), (13, 2)))], 2, 0))
    yield load_case("frame list second token does not replace first slot", garbage(), flags=0x10, count=2,
                    text=b"fr nowhere", entries={b"fr": frames_of(["a"], 0, 0, 1)})

    # ---- step 0x4d1620
    for route, label in (((0x30, None), "pointer is zero"), ((0x30, 0x10), "level without +8"),
                         ((0x1C, 5), "level without +0x24")):
        fields = (0, 0) if label != "level without +0x24" else (0x1234, 0)
        yield load_case(f"steps: {label}", garbage(), pointer_route=route, level_fields=fields, offset=0,
                        rect=(1, 2, 9, 12), flags=1)
        yield load_case(f"steps: {label} unscaled flags", garbage(), pointer_route=route, level_fields=fields,
                        flags=0, rect=None)
    yield load_case("steps: pointer is zero with tokens", garbage(), pointer_route=(0x44, None), text=b"alpha",
                    count=1, entries=table)

    # ---- random
    for number in range(70):
        words = [rng.randrange(0x30, 0x7F) for _ in range(rng.randrange(1, 9))]
        vocabulary = [bytes(rng.randrange(0x30, 0x7F) for _ in range(rng.randrange(1, 9))) for _ in range(5)]
        entries = {}
        for word in vocabulary:
            if rng.random() < 0.7:
                entries[word] = rng.getrandbits(32)
        tokens = [rng.choice(vocabulary) for _ in range(rng.randrange(0, 7))]
        separator = lambda: bytes(rng.choice([1, 9, 32, 47, 0x80, 0xC3, 0xFF]) for _ in range(rng.randrange(1, 4)))
        text = separator() if rng.random() < 0.5 else b""
        for token in tokens:
            text += token + separator()
        count = len(tokens) + rng.choice([0, 0, 0, 1, 2]) if rng.random() < 0.85 else max(0, len(tokens) - 1)
        flags = rng.choice([0, 1, 2, 4, 8, 12, 5, 9, 13, 3, 0x20, 0x21, 0x2C])
        dims = (rng.randrange(1, 7), rng.randrange(1, 7), rng.randrange(1, 6), rng.randrange(1, 6))
        preset = None
        if rng.random() < 0.4:
            preset = ([rng.getrandbits(32) for _ in range(rng.randrange(0, 5))], rng.randrange(0, 9), rng.randrange(0, 5))
        route = None
        if rng.random() < 0.15:
            route = (rng.choice([0x10, 0x30, 0x44]), rng.choice([None, 0x7000, 0x22]))
        yield load_case(f"random load #{number}", garbage(), text=text, count=count, entries=entries, flags=flags,
                        dims=dims, preset=preset, start=(rng.randrange(-200, 300), rng.randrange(-200, 300)),
                        scale=(rng.randrange(1, 300), rng.randrange(1, 300)), word78=rng.getrandbits(32),
                        pixel_origin=rng.getrandbits(32), pixel_flags=rng.getrandbits(32),
                        rect=(None if rng.random() < 0.2 else (rng.randrange(-50, 50), rng.randrange(-50, 50),
                                                              rng.randrange(0, 150), rng.randrange(0, 150))),
                        name=bytes(rng.randrange(1, 256) for _ in range(rng.randrange(0, 60))),
                        pointer_route=route, offset=rng.randrange(0, 5),
                        bucket_count=rng.choice([1, 2, 5, 17]))


def cases(random_source):
    yield from tiny_cases(random_source)
    yield from hit_cases(random_source)
    yield from dims_cases(random_source)
    yield from ctor_cases(random_source)
    yield from destroy_cases(random_source)
    yield from scan_cases(random_source)
    yield from load_cases(random_source)
    yield from readability_survivor_cases(random_source)


def readability_clamp_setup(axis, limit):
    """Interior pointers keep all negative and zero indices inside live objects."""
    def setup(env):
        log = env.object(4 + 16 * 4, "nonpositive-limit-log", fill=0)
        handlers = []
        for number in range(3):
            def probe(env, call, number=number):
                count = env.get(log)
                env.put(log + 4 + count * 16, call.receiver,
                        call.arguments[0], call.arguments[1], number)
                env.put(log, count + 1)
                return 0
            method = env.stub(f"nonpositive-limit-handler-{number}", "thiscall", 2, probe)
            vtable = env.object(0x24, f"nonpositive-limit-vtable-{number}", fill=0)
            env.put(vtable + 0x20, method)
            handlers.append(env.object(16, f"nonpositive-limit-object-{number}",
                                       words=[vtable, 0x12340000 + number, 0, 0]))
        handler_table = env.object(12, "nonpositive-limit-handlers", words=handlers)
        cell_storage = env.object(12, "backed-negative-cells", words=[0, 1, 2])
        if axis == "x":
            # width=-1/0 selects cell[-2]/cell[-1]; <=0 mutant selects cell[0].
            cells = cell_storage + 8
            rows = env.object(4, "single-backed-row", words=[0])
            width, height = limit, 1
        else:
            # height=-1/0 selects row[-2]/row[-1]; <=0 mutant selects row[0].
            cells = cell_storage
            rows = env.object(12, "backed-negative-rows", words=[0, 1, 2]) + 8
            width, height = 1, limit
        plane = env.object(0x98, "nonpositive-limit-plane", fill=0xA5)
        env.put(plane + 0x20, cells, rows)
        env.put(plane + 0x30, u(width), u(height))
        env.put(plane + 0x8C, 0, 0)
        scanner = env.object(0x70, "nonpositive-limit-scanner", fill=0x5A)
        env.put(scanner + 0x4C, handler_table)
        env.put(scanner + 0x5C, plane)
        return {"this": scanner, "log": log}
    return setup


def readability_aliased_rect_setup(garbage, route):
    # The normal CopyRect fixture still copies source bytes exactly; only the
    # source token aliases fields naturally written by the original loader.
    ordinary_setup = loader(garbage, dims=(3, 2, 4, 5), name=b"\x03",
                            rect=(7, 11, 19, 23), flags=0)
    def setup(env):
        tokens = ordinary_setup(env)
        alias = tokens["this"] + (0x60 if route == "grid" else 0xB4)
        env.put(alias, 7, 11, 19, 23)
        tokens["rect"] = alias
        return tokens
    return setup


def readability_survivor_cases(random_source):
    # Original sites 0x4cda45/5a, 0x4cdb0b/24 and 0x4cdbd6/eb clamp
    # a zero coordinate to signed limit-1 even when that limit is nonpositive.
    for axis in ("x", "y"):
        for limit in (0, -1):
            yield Case(f"readability clamp {axis} signed limit {limit} backed indices", SCAN,
                       readability_clamp_setup(axis, limit), receiver=this_of,
                       arguments=(0, 0, 0, 1))
    # 0x4d0586..0x4d05a3 first loads the rect. Writes to grid +0x60..0x6c
    # or the name at +0xb4 then change the aliased rect. The unchanged CopyRect
    # at 0x4d0689 copies that updated source, and all four repeated destination
    # stores at 0x4d0698..0x4d06ac are therefore observable.
    for route in ("grid", "name"):
        garbage = [random_source.getrandbits(32) for _ in range(0x58)]
        yield Case(f"readability CopyRect aliases {route} fields", LOAD,
                   readability_aliased_rect_setup(garbage, route), receiver=this_of,
                   arguments=(lambda t: t["descriptor"], lambda t: t["offset"], lambda t: t["rect"]))

    # The original loop at 0x4d05fd..0x4d0600 stops strictly before count.
    # A live nonzero slot just past that count makes an extra iteration visible.
    garbage = [random_source.getrandbits(32) for _ in range(0x58)]
    yield load_case("readability frame slot just past count is backed nonzero", garbage,
                    flags=0x10, text=b"fr", count=1,
                    entries={b"fr": lambda env: frame_list(env, [None, "past-count"],
                                                         0, 1, 1, ((9, 7),))})
    # Equal INT_MAX endpoints select the descending walk (0x4cda2f), which
    # probes the last cell twice. An erroneous ascending walk wraps to INT_MIN,
    # reaches the distinct zero cell and stops within four handler invocations.
    yield Case("readability equal signed maximum scan endpoints", SCAN,
               scan_world(2, 1, 0, 0, [[0, 1]], [1, 0, 0], 0, 0, 0),
               receiver=this_of, arguments=(0x7FFFFFFF, 0, 0x7FFFFFFF, 1))
