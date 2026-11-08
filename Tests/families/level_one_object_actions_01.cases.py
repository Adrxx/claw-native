"""Cases for level_one_object_actions_01: Observed Level 1 level object actions batch 1."""
import struct
from dataclasses import replace

from clawparity.env import NativeSourceContext

from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, reallocate, release, returns, sequence, store_words  # noqa: F401

F_4332F0, F_43EAB0, F_4410F0, F_44AAF0 = 0x4332F0, 0x43EAB0, 0x4410F0, 0x44AAF0
F_44BC60, F_44C000, F_44C840, F_44D000 = 0x44BC60, 0x44C000, 0x44C840, 0x44D000
F_44D3C0, F_44EDD0, F_44EF70 = 0x44D3C0, 0x44EDD0, 0x44EF70
RAND, SET_RECT_EMPTY, SET_RECT = 0x4A3050, 0x546CDC, 0x546D5C
G_WORLD_PLAYER = 0x537E88   # pointer to the player-like object read by the AI
G_MODE = 0x534EAC           # compared against 0x26b7
G_ANIM_STEP = 0x5430C4      # step handed to the animation stepper
G_TICKS = 0x537210
G_PACING_TREE = 0x537668
STATE_NAMES = [0x52720C, 0x527204, 0x527DA0, 0x5234F4, 0x5271D8, 0x5271CC, 0x5271B4]
M32 = 0xFFFFFFFF


def words_of(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


def dbl_words(value):
    return struct.unpack("<II", struct.pack("<d", value))


def dbl_bits(low, high):
    return struct.unpack("<d", struct.pack("<II", low, high))[0]


def neg(value):
    return (-value) & M32


def put_double(env, address, value):
    env.put(address, *dbl_words(value))


def tile_grid(random_source, columns, rows):
    """A tile plane read through +0x20 (data) and +0x24 (row offsets)."""
    def setup(env):
        stride = columns + random_source.randrange(0, 3)
        data = env.object(4 * stride * rows, "tile-data")
        for index in range(stride * rows):
            env.put(data + 4 * index, random_source.randrange(1, 1 << 32))
        offsets = env.object(4 * rows, "row-offsets")
        for row in range(rows):
            env.put(offsets + 4 * row, row * stride)
        plane = env.object(0x30, "plane")
        env.put(plane + 0x20, data, offsets)
        return {"plane": plane, "data": data, "stride": stride}
    return setup


def build_tilemap(env, random_source, width, height, shift_x, shift_y, classify, hook=None):
    """Tile map object T: +0x4c tile table, +0x5c plane.  classify(cell_x, cell_y) -> class 0..3 or None (empty cell)."""
    columns = (width + (1 << shift_x) - 1) >> shift_x
    rows = (height + (1 << shift_y) - 1) >> shift_y
    tiles = []
    for tile_class in range(4):
        vt = env.object(0x40, "tile-vtable")

        def effect(env, call, tile_class=tile_class):
            if hook is not None:
                hook(env, call)
            return tile_class
        env.put(vt + 0x20, env.stub(f"tile-class-{tile_class}", "thiscall", 2, effect))
        obj = env.object(8, "tile-object")
        env.put(obj, vt)
        tiles.append(obj)
    table = env.object(4 * 4, "tile-table", words=tiles)
    cells = []
    for cy in range(rows):
        for cx in range(columns):
            tile_class = classify(cx, cy)
            if tile_class is None:
                cells.append(random_source.choice((0xEEEEEEEE, 0xFFFFFFFF)))
            else:
                cells.append((random_source.randrange(0, 1 << 16) << 16) | tile_class)
    data = env.object(4 * len(cells), "tile-cells", words=cells)
    offsets = env.object(4 * rows, "tile-rows", words=[cy * columns for cy in range(rows)])
    plane = env.object(0x98, "tile-plane", words=words_of(random_source, 0x26))
    env.put(plane + 0x20, data, offsets)
    env.put(plane + 0x30, width, height)
    env.put(plane + 0x8C, shift_x, shift_y)
    tmap = env.object(0x80, "tile-map", words=words_of(random_source, 0x20))
    env.put(tmap + 0x4C, table)
    env.put(tmap + 0x5C, plane)
    return tmap


def make_world(env, tmap):
    world = env.object(0x60, "world")
    env.put(world + 0x24, tmap)
    return world


def set_bits(env, logic, size, word):
    """Bit-set at +0x2fc (size) / +0x300 (inline word, or pointer to words when size > 0x20)."""
    env.put(logic + 0x2FC, size)
    if size > 0x20:
        bits = env.object(4 * ((size + 31) // 32), "bits", words=[word] + [0x5A5A5A5A] * ((size + 31) // 32 - 1))
        env.put(logic + 0x300, bits)
    else:
        env.put(logic + 0x300, word)


def make_vtable(env, slots):
    vt = env.object(0x80, "logic-vtable")
    stubs = {}
    for slot in slots:
        stubs[slot] = env.stub(f"vslot-{slot:#x}", "thiscall", 0, returns(0x1000 + slot))
        env.put(vt + slot, stubs[slot])
    return vt


def make_logic(env, random_source, actor=None, size=0x460, slots=(0x24, 0x44, 0x48)):
    logic = env.object(size, "logic", words=words_of(random_source, size // 4))
    vt = make_vtable(env, slots)
    info = env.object(0x80, "actor-info", words=words_of(random_source, 0x20))
    env.put(logic, vt)
    env.put(logic + 0x10, info)
    return logic


# ----------------------------------------------------------------------------------------------
# 0x4410f0
def lookup_cases(random_source):
    for columns, rows in ((1, 1), (3, 2), (5, 4), (8, 8)):
        grid = tile_grid(random_source, columns, rows)
        for x in sorted({0, columns - 1, random_source.randrange(0, columns)}):
            for y in sorted({0, rows - 1, random_source.randrange(0, rows)}):
                yield Case(f"tile lookup {columns}x{rows} at {x},{y}", F_4410F0, grid,
                           receiver=lambda t: t["plane"], arguments=(x, y))


# ----------------------------------------------------------------------------------------------
# 0x44aaf0
def collector_setup(random_source, zero_mask):
    def setup(env):
        target = env.object(0x80, "collector", words=words_of(random_source, 0x20))
        actor = env.object(0x110, "owner", words=words_of(random_source, 0x44))
        info = env.object(0x110, "owner-info", words=words_of(random_source, 0x44))
        env.put(actor + 0x6C, info)
        offsets = (0xF0, 0xF8, 0xF4, 0xFC, 0x100, 0x108, 0x104, 0x10C)
        for index, offset in enumerate(offsets):
            if zero_mask >> index & 1:
                env.put(info + offset, 0)
        if zero_mask >> 8 & 1:
            env.put(actor + 0x100, 0)
        return {"target": target, "actor": actor}
    return setup


def collector_cases(random_source):
    for mask in (0, 0x1FF, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x155, 0xAA):
        yield Case(f"collector zero mask {mask:#x}", F_44AAF0, collector_setup(random_source, mask),
                   receiver=lambda t: t["target"], arguments=(lambda t: t["actor"],))
    for _ in range(6):
        mask = random_source.randrange(0, 0x200)
        yield Case(f"collector random mask {mask:#x}", F_44AAF0, collector_setup(random_source, mask),
                   receiver=lambda t: t["target"], arguments=(lambda t: t["actor"],))


# ----------------------------------------------------------------------------------------------
# 0x44c840
DISPATCH_GLOBALS = {
    "main": dict(lo=0x537880, hi=0x537884, base=0x537888, stride=0x537890, fallback=0x53788C, flag=0x537898),
    "second": dict(lo=0x537640, hi=0x537644, base=0x537648, stride=0x537650, fallback=0x53764C, flag=0x537658),
}


def dispatch_setup(random_source, low, high, stride, main_values, second_values=None, flag_value=None):
    def setup(env):
        stubs = {}
        for table, values in (("main", main_values), ("second", second_values)):
            if values is None:
                continue
            g = DISPATCH_GLOBALS[table]
            size = max(stride, 4) * (high - low + 1)
            area = env.object(size + 8, f"{table}-dispatch", words=words_of(random_source, (size + 8) // 4))
            for index, value in enumerate(values):
                entry = area + index * stride
                if value:
                    stubs[(table, index)] = env.stub(f"{table}-handler-{index}", "thiscall", 0, returns(0x100 + index))
                    env.put(entry, stubs[(table, index)])
                else:
                    env.put(entry, 0)
            env.put(g["lo"], low)
            env.put(g["hi"], high)
            env.put(g["base"], area)
            env.put(g["stride"], stride)
            if flag_value is not None:
                env.put(g["flag"], flag_value)
        fallback = env.object(0x10, "dispatch-fallback", words=words_of(random_source, 4))
        env.put(0x53788C, fallback)
        target = env.object(0x20, "dispatch-receiver", words=words_of(random_source, 8))
        return {"this": target, "stubs": stubs}
    return setup


def dispatch_cases(random_source):
    low = random_source.randrange(-5, 40)
    high = low + 5
    stride = random_source.choice((4, 8, 12))
    values = [True, False, True, True, False, True]
    for index in range(6):
        yield Case(f"dispatch id {index} in range, main table {'set' if values[index] else 'empty'}",
                   F_44C840, dispatch_setup(random_source, low, high, stride, values, [False, True, True, False, True, True],
                                            flag_value=random_source.randrange(1, 1 << 30)),
                   receiver=lambda t: t["this"], arguments=(low + index,))
    for index in (1, 4):
        yield Case(f"dispatch id {index} second table", F_44C840,
                   dispatch_setup(random_source, low, high, stride, [False] * 6, [True, True, True, True, True, True]),
                   receiver=lambda t: t["this"], arguments=(low + index,))


# ----------------------------------------------------------------------------------------------
# 0x44c840: ids outside [lo, hi] go through the table grow 0x4db6e0 (realloc fixture)
G_DISPATCH_CONTEXT = 0x53787C   # table +4: handed to the error reporter 0x4db4d0 when the grow fails


def grow_dispatch_setup(random_source, low, high, stride, realloc_effect, fallback_handler):
    """Main table covers [low, high]; the second table (reached through 0x43d490 once the main entry is
    empty) covers a wider range and holds a handler for every id the cases use."""
    r = random_source

    def setup(env):
        stubs = {}
        for table, lo, hi in (("main", low, high), ("second", low - 4, high + 10)):
            g = DISPATCH_GLOBALS[table]
            count = hi - lo + 1
            area = env.object(stride * count + 8, f"{table}-dispatch", words=words_of(r, (stride * count + 8) // 4))
            for index in range(count):
                if table == "main":
                    env.put(area + index * stride, 0 if index % 3 == 1 else words_of(r, 1)[0])
                else:
                    stubs[index] = env.stub(f"second-handler-{index}", "thiscall", 0, returns(0x200 + index))
                    env.put(area + index * stride, stubs[index])
            env.put(g["lo"], lo)
            env.put(g["hi"], hi)
            env.put(g["base"], area)
            env.put(g["stride"], stride)
            env.put(g["flag"], r.randrange(1, 1 << 30))
        fallback = env.object(0x10, "dispatch-fallback", words=words_of(r, 4))
        env.put(0x53788C, fallback)
        env.put(0x53764C, env.object(0x10, "second-fallback", words=words_of(r, 4)))
        tokens = {"this": env.object(0x20, "dispatch-receiver", words=words_of(r, 8)), "stubs": stubs}
        context = env.object(0x20, "dispatch-context", words=words_of(r, 8))
        env.put(context + 0x0C, 4)   # reporter 0x4db4d0 takes its short branch (stores a word at +8)
        env.put(G_DISPATCH_CONTEXT, context)
        if fallback_handler:
            tokens["fallback_stub"] = env.stub("fallback-handler", "thiscall", 0, returns(0x777))
            env.put(fallback, tokens["fallback_stub"])
        else:
            env.put(fallback, 0)
        env.override(0x4A9070, realloc_effect)
        return tokens
    return setup


def grow_dispatch_cases(random_source):
    r = random_source
    for offset in (-1, -3, 6, 9):
        low = r.randrange(-5, 40)
        stride = r.choice((4, 8, 12))
        yield Case(f"dispatch id {offset} from base grows the table", F_44C840,
                   grow_dispatch_setup(r, low, low + 5, stride, reallocate(), r.random() < 0.5),
                   receiver=lambda t: t["this"], arguments=(low + offset,))


# ----------------------------------------------------------------------------------------------
# shared actor / logic objects
def make_actor(env, random_source, world=None, size=0x1C0):
    actor = env.object(size, "actor", words=words_of(random_source, size // 4))
    if world is not None:
        env.put(actor + 0x0C, world)
    return actor


def make_script(env, random_source):
    frame = env.object(0x40, "anim-frame", words=words_of(random_source, 0x10))
    frames = env.object(8, "anim-frames", words=[frame, 0])
    script = env.object(0x30, "anim-script", words=words_of(random_source, 0x0C))
    env.put(script + 0x0C, frames)
    env.put(script + 0x10, 1)
    return script


def install_pacing_tree(env, random_source, mode):
    """The tree behind FUN_004dba00(&0x537668, "LS_PACING"); the root pointer lives at 0x537680."""
    if mode == "empty":
        env.put(G_PACING_TREE + 0x18, 0)
        return
    value = random_source.randrange(1, 1 << 32)
    key = {"mismatch": b"LS_PACINX\0", "short": b"LS_PAC\0", "long": b"LS_PACING2\0"}.get(mode, b"LS_PACING\0")
    keyobj = env.object(16, "tree-key", data=key)
    root = env.object(0x20, "tree-root", words=words_of(random_source, 8))
    node = env.object(0x20, "tree-node", words=words_of(random_source, 8))
    env.put(root, root, root, 0, keyobj, value)
    if mode == "null":
        env.put(root, 0, 0)
    elif mode == "deep":
        env.put(root, node, node)
        env.put(node, node, root, 3, keyobj, value ^ 0x55555555)
    elif mode == "far":
        env.put(root + 8, 100)
    env.put(G_PACING_TREE + 0x18, root)


def base_logic(env, random_source, slots=(0x24, 0x44, 0x48)):
    logic = make_logic(env, random_source, slots=slots)
    actor = make_actor(env, random_source)
    env.put(logic + 0x12C, actor)
    return logic, actor


def set_doubles(env, logic, d68, d80, d98):
    for offset, value in ((0x68, d68), (0x80, d80), (0x98, d98)):
        put_double(env, logic + offset, value)


def pick_double(random_source):
    return random_source.choice((0.0, 1.0, -1.0, 17.25, -233.5, 1234.5678, 1e12, -3.0e-7))


# ----------------------------------------------------------------------------------------------
# 0x44edd0
def edd0_setup(random_source, size, word, equal, p40_bit1, p118_special, p128_special, l138_flag, script, tree,
               d68=None, d98=None):
    def setup(env):
        logic, actor = base_logic(env, random_source)
        set_bits(env, logic, size, word)
        first = pick_double(random_source) if d68 is None else d68
        second = first if equal else (pick_double(random_source) + 3.5 if d98 is None else d98)
        if d98 is not None:
            second = d98
        set_doubles(env, logic, first, pick_double(random_source), second)
        env.put(actor + 0x40, (random_source.randrange(0, 1 << 32) & ~2) | (2 if p40_bit1 else 0))
        env.put(actor + 0x118, 0x80000000 if p118_special else random_source.randrange(1, 1 << 31))
        env.put(actor + 0x128, 0x80000000 if p128_special else random_source.randrange(1, 1 << 31))
        env.put(actor + 0x138, 0x80000000 if l138_flag else random_source.randrange(1, 1 << 31))
        env.put(actor + 0x188 + 8, 0)
        env.put(logic + 0x34C, make_script(env, random_source) if script else 0)
        install_pacing_tree(env, random_source, tree)
        return {"L": logic, "P": actor}
    return setup


def edd0_cases(random_source):
    r = random_source
    for size, word in ((3, 0x4), (3, 0xFFFFFFFF), (0x20, 0x80000004), (0x21, 0x4), (0x40, 0x7FFFFFFF), (0x100, 0x4)):
        yield Case(f"edd0 bit 2 set, bit-set size {size:#x}", F_44EDD0,
                   edd0_setup(r, size, word, True, False, False, False, False, False, "empty"),
                   receiver=lambda t: t["L"])
    for size, word in ((0, 0xFFFFFFFF), (1, 0xFFFFFFFF), (2, 0xFFFFFFFF)):
        yield Case(f"edd0 short bit set ignores bit 2 (size {size})", F_44EDD0,
                   edd0_setup(r, size, word, True, False, False, False, False, True, "match"),
                   receiver=lambda t: t["L"])
    for equal in (True, False):
        for bit1 in (False, True):
            for tree in ("empty", "match", "mismatch", "deep"):
                specials = (r.random() < 0.5, r.random() < 0.5, r.random() < 0.5)
                yield Case(f"edd0 equal={equal} p40bit1={bit1} tree={tree}", F_44EDD0,
                           edd0_setup(r, r.choice((3, 5, 0x20, 0x21, 0x60)), r.randrange(0, 1 << 32) & ~4, equal, bit1,
                                      *specials, r.random() < 0.7, tree),
                           receiver=lambda t: t["L"])
    for p118 in (False, True):
        for p128 in (False, True):
            for l138 in (False, True):
                for equal, bit1 in ((True, True), (False, False), (True, False), (False, True)):
                    yield Case(f"edd0 special words {int(p118)}{int(p128)}{int(l138)} equal={equal} bit1={bit1}", F_44EDD0,
                               edd0_setup(r, 8, 0, equal, bit1, p118, p128, l138, r.random() < 0.5,
                                          r.choice(("match", "null", "far", "short", "long"))),
                               receiver=lambda t: t["L"])
    yield Case("edd0 negative zero equals zero", F_44EDD0,
               edd0_setup(r, 8, 0, False, False, False, False, False, False, "match", d68=0.0, d98=-0.0),
               receiver=lambda t: t["L"])
    yield Case("edd0 distinct doubles with equal high words", F_44EDD0,
               edd0_setup(r, 8, 0, False, False, False, False, False, False, "match",
                          d68=dbl_bits(1, 0x40100000), d98=dbl_bits(2, 0x40100000)),
               receiver=lambda t: t["L"])
    yield Case("edd0 distinct doubles with equal low words", F_44EDD0,
               edd0_setup(r, 8, 0, False, True, False, False, False, False, "match",
                          d68=dbl_bits(0x1234, 0x40100000), d98=dbl_bits(0x1234, 0x40200000)),
               receiver=lambda t: t["L"])


# ----------------------------------------------------------------------------------------------
# 0x44d3c0
def d3c0_setup(random_source, callback, second, states_equal, mover, stale_blocked, hold_blocked, x, y):
    def setup(env):
        logic = make_logic(env, random_source)
        info = env.get(logic + 0x10)
        state = random_source.randrange(1, 1 << 20)
        env.put(logic + 0x1C, state)
        env.put(info + 0x1C, state if states_equal else state ^ 0x10)
        env.put(logic + 0x14, env.stub("pending-action", "thiscall", 0, returns(0x71)) if callback else 0)
        env.put(logic + 0x18, env.stub("pending-guard", "thiscall", 0, returns(0x72)) if second else 0)
        put_double(env, logic + 0x68, x)
        put_double(env, logic + 0x70, y)
        if mover:
            mover_obj = env.object(0x1C0, "mover", words=words_of(random_source, 0x70))
            env.put(mover_obj + 0x1A4, 0 if stale_blocked else random_source.randrange(1, 1 << 30))
            env.put(mover_obj + 0x19C, random_source.randrange(1, 1 << 30) if hold_blocked else 0)
            env.put(logic + 0x44C, mover_obj)
        else:
            env.put(logic + 0x44C, 0)
        return {"L": logic}
    return setup


def d3c0_cases(random_source):
    r = random_source
    for callback in (False, True):
        for second in (False, True):
            for equal in (False, True):
                yield Case(f"d3c0 callback={callback} guard={second} states_equal={equal}", F_44D3C0,
                           d3c0_setup(r, callback, second, equal, False, False, False, 10.5, 20.5),
                           receiver=lambda t: t["L"], arguments=(r.randrange(0, 1 << 32),))
    for stale in (False, True):
        for hold in (False, True):
            yield Case(f"d3c0 mover stale_zero={stale} hold={hold}", F_44D3C0,
                       d3c0_setup(r, True, True, True, True, stale, hold, 321.75, -45.25),
                       receiver=lambda t: t["L"], arguments=(1,))
    for x, y in ((0.5, 1.5), (2.5, 3.5), (-0.5, -1.5), (1e9, -1e9), (123.499, 123.501), (-7.0, 99999.5)):
        yield Case(f"d3c0 rounds position {x},{y}", F_44D3C0,
                   d3c0_setup(r, False, False, False, True, False, False, x, y),
                   receiver=lambda t: t["L"], arguments=(0,))
    for _ in range(4):
        yield Case("d3c0 random position", F_44D3C0,
                   d3c0_setup(r, r.random() < 0.5, r.random() < 0.5, r.random() < 0.5, True, False, False,
                              r.uniform(-5000, 5000), r.uniform(-5000, 5000)),
                   receiver=lambda t: t["L"], arguments=(r.randrange(0, 1 << 32),))


# ----------------------------------------------------------------------------------------------
# 0x43eab0: is the logic's actor standing near the edge of a platform
def run_row(random_source, columns, weights):
    row = []
    while len(row) < columns:
        length = random_source.randrange(3, 40)
        row.extend([random_source.choice(weights)] * length)
    return row[:columns]


def edge_setup(random_source, px, ry, shifts=(0, 0), width=320, height=64, floor=None, above=None, change_ry=None):
    """floor: (xl, xr) solid pixel span at row ry (random classes 1..3); above: {x: class} blockers at row ry-1."""
    sx, sy = shifts

    def setup(env):
        columns = (width + (1 << sx) - 1) >> sx
        rows = (height + (1 << sy) - 1) >> sy
        grid = [run_row(random_source, columns, (None, 0, 1, 1, 2, 3, None)) for _ in range(rows)]
        if floor is not None:
            fy = min(max(ry, 0), height - 1) >> sy
            ay = min(max(ry - 1, 0), height - 1) >> sy
            for cx in range(columns):
                grid[ay][cx] = 0 if change_ry is not None else random_source.choice((None, 0))
                grid[fy][cx] = None
            for x in range(max(floor[0], 0), min(floor[1], width - 1) + 1):
                grid[fy][x >> sx] = 1 if change_ry is not None else random_source.choice((1, 1, 2, 3))
            for x, tile_class in (above or {}).items():
                if 0 <= x < width:
                    grid[ay][x >> sx] = tile_class
        holder = {}
        counter = env.object(8, "tile-call-counter", fill=0)

        def hook(env, call):
            count = env.get(counter) + 1
            env.put(counter, count)
            if change_ry is not None and count == change_ry[0]:
                env.put(holder["owner"] + 0x50, change_ry[1] & M32)
        tmap = build_tilemap(env, random_source, width, height, sx, sy, lambda cx, cy: grid[cy][cx], hook)
        world = make_world(env, tmap)
        logic = make_logic(env, random_source)
        owner = make_actor(env, random_source, world)
        holder["owner"] = owner
        mover = make_actor(env, random_source, make_world(env, build_tilemap(env, random_source, 8, 8, 0, 0, lambda cx, cy: 1)))
        extra = random_source.randrange(0, 6)
        env.put(owner + 0x124, extra)
        env.put(owner + 0x50, (ry - 1 - extra) & M32)
        env.put(mover + 0x4C, px & M32)
        env.put(logic + 0x128, owner)
        env.put(logic + 0x12C, mover)
        return {"L": logic}
    return setup


def edge_cases(random_source):
    r = random_source
    px, ry = 150, 40
    yield Case("edge wide floor never ends", F_43EAB0, edge_setup(r, px, ry, floor=(0, 319)), receiver=lambda t: t["L"])
    for d in (0, 1, 49, 50):
        for e in (0, 1, 49, 50):
            yield Case(f"edge floor {d} left {e} right", F_43EAB0,
                       edge_setup(r, px, ry, floor=(px - d, px + e)), receiver=lambda t: t["L"])
    yield Case("edge floor starts at plane edge", F_43EAB0, edge_setup(r, 10, 20, floor=(0, 30)), receiver=lambda t: t["L"])
    yield Case("edge floor ends at plane edge", F_43EAB0, edge_setup(r, 300, 20, floor=(290, 319)), receiver=lambda t: t["L"])
    yield Case("edge floor spans plane, actor at left wall", F_43EAB0, edge_setup(r, 3, 20, floor=(0, 319)), receiver=lambda t: t["L"])
    yield Case("edge floor spans plane, actor beyond right wall", F_43EAB0, edge_setup(r, 400, 20, floor=(0, 319)), receiver=lambda t: t["L"])
    yield Case("edge actor left of plane", F_43EAB0, edge_setup(r, -30, 20, floor=(0, 20)), receiver=lambda t: t["L"])
    for new_ry in (-30, -1, 64, 90, 5, 63):
        yield Case(f"edge row changes to {new_ry} during the first scan", F_43EAB0,
                   edge_setup(r, px, ry, floor=(px - 20, px + 20), change_ry=(2, new_ry)), receiver=lambda t: t["L"])
    yield Case("edge row below plane", F_43EAB0, edge_setup(r, px, 90, floor=(60, 250)), receiver=lambda t: t["L"])
    yield Case("edge row above plane", F_43EAB0, edge_setup(r, px, -20, floor=(60, 250)), receiver=lambda t: t["L"])
    for blocker in (px - 1, px - 3, px - 40, px - 49, px - 50, px + 1, px + 7, px + 48, px + 49, px + 50, px):
        for tile_class in (1, 2, 3):
            yield Case(f"edge blocker {blocker - px} class {tile_class} over floor", F_43EAB0,
                       edge_setup(r, px, ry, floor=(0, 319), above={blocker: tile_class}), receiver=lambda t: t["L"])
    for d, e, blocker in ((10, 20, px - 5), (10, 20, px + 5), (5, 60, px + 30), (60, 5, px - 30)):
        yield Case(f"edge floor {d}/{e} with blocker {blocker - px}", F_43EAB0,
                   edge_setup(r, px, ry, floor=(px - d, px + e), above={blocker: 1}), receiver=lambda t: t["L"])
    for shifts in ((1, 0), (0, 1), (2, 2), (3, 1), (1, 3)):
        for d, e in ((5, 7), (40, 60), (60, 60)):
            yield Case(f"edge shifts {shifts} floor {d}/{e}", F_43EAB0,
                       edge_setup(r, px, ry, shifts=shifts, floor=(px - d, px + e)), receiver=lambda t: t["L"])


# ----------------------------------------------------------------------------------------------
# 0x44ef70
def ef70_setup(random_source, d68, d80, d98, p40_bit1, size, word, state184, scan, anim=None, step=1,
               p118=None, p128=None, l138=None):
    """scan: None or dict(qx, qy, rx, ry, blockers, mode, q38_minus_one, shifts)."""
    def setup(env):
        logic, actor = base_logic(env, random_source)
        set_bits(env, logic, size, word)
        set_doubles(env, logic, d68, d80, d98)
        env.put(actor + 0x40, (random_source.randrange(0, 1 << 32) & ~2) | (2 if p40_bit1 else 0))
        for offset, special in ((0x118, p118), (0x128, p128), (0x138, l138)):
            env.put(actor + offset, 0x80000000 if special else random_source.randrange(1, 1 << 31))
        env.put(logic + 0x184, state184 & M32)
        env.put(G_ANIM_STEP, step)
        anim_base = actor + 0x188
        if anim is None:
            env.put(anim_base + 8, 0)
        else:
            env.put(anim_base + 8, make_script(env, random_source))
            env.put(anim_base + 0x14, anim[0])
            env.put(anim_base + 0x18, anim[1])
        env.put(G_MODE, 0x26B7 if scan is not None and scan.get("mode") == "disabled" else random_source.randrange(0, 0x26B7))
        player = env.object(0x60, "player", words=words_of(random_source, 0x18))
        env.put(G_WORLD_PLAYER, player)
        mover = env.object(0x60, "scanner", words=words_of(random_source, 0x18))
        holder = env.object(0x60, "scan-holder", words=words_of(random_source, 0x18))
        env.put(logic + 0x190, holder)
        env.put(logic + 0x194, mover)
        if scan is None:
            tmap = build_tilemap(env, random_source, 16, 16, 0, 0, lambda cx, cy: 0)
            env.put(holder + 0x0C, make_world(env, tmap))
            return {"L": logic}
        sx, sy = scan.get("shifts", (0, 0))
        width, height = 700, 48
        blockers = scan.get("blockers", ())
        qy = scan["qy"]
        qyc = min(max(qy, 0), height - 1)

        def classify(cx, cy):
            if cy == qyc >> sy:
                if any(((min(max(b, 0), width - 1)) >> sx) == cx for b in blockers):
                    return 1
                return random_source.choice((None, 0, 2, 3, None))
            return random_source.choice((None, 0, 1, 2, 3))
        tmap = build_tilemap(env, random_source, width, height, sx, sy, classify)
        env.put(holder + 0x0C, make_world(env, tmap))
        env.put(mover + 0x4C, scan["qx"] & M32, qy & M32)
        env.put(mover + 0x38, M32 if scan.get("q38_minus_one") else random_source.randrange(0, 1 << 30))
        env.put(player + 0x4C, scan["rx"] & M32, scan["ry"] & M32)
        return {"L": logic}
    return setup


def ef70_cases(random_source):
    r = random_source
    # Every combination of the two special-word tests is covered on purpose, whatever the seed draws.
    for equal_80 in (True, False):
        for equal_98 in (True, False):
            for bit1 in (False, True):
                for p118 in (False, True):
                    for p128 in (False, True):
                        for roll in ((10 if p118 == p128 else 77),):
                            def build(equal_80=equal_80, equal_98=equal_98, bit1=bit1, p118=p118, p128=p128, roll=roll):
                                base = pick_double(r)
                                inner = ef70_setup(r, base, base if equal_80 else base + 1.25,
                                                   base if equal_98 else base - 2.5, bit1, 4, 0, 6, None,
                                                   p118=p118, p128=p128, l138=False)

                                def setup(env):
                                    tokens = inner(env)
                                    env.override(RAND, sequence(roll, roll))
                                    return tokens
                                return setup
                            yield Case(f"ef70 fixed flags d80={equal_80} d98={equal_98} bit1={bit1} p118={p118} "
                                       f"p128={p128} roll={roll}", F_44EF70, build(), receiver=lambda t: t["L"])
    for state in (-1, 0, 1, 4, 5, 6, 100, 0x80000000, 0x7FFFFFFF):
        yield Case(f"ef70 low-state vcall state={state:#x}", F_44EF70,
                   ef70_setup(r, 1.5, 2.5, 3.5, True, 8, 0xFF, state, None), receiver=lambda t: t["L"])
    for size, word in ((9, 0x100), (0x20, 0x80000100), (0x21, 0x100), (0x50, 0x100)):
        yield Case(f"ef70 bit 8 set size {size:#x} no scan (mode disabled)", F_44EF70,
                   ef70_setup(r, 1.5, 2.5, 3.5, True, size, word, 2, dict(qx=100, qy=20, rx=200, ry=20, mode="disabled")),
                   receiver=lambda t: t["L"])
    yield Case("ef70 bit 8 ignored when set bit is beyond size", F_44EF70,
               ef70_setup(r, 1.5, 2.5, 3.5, True, 8, 0x100, 2, None), receiver=lambda t: t["L"])
    scans = [
        dict(qx=100, qy=20, rx=300, ry=20),
        dict(qx=100, qy=20, rx=300, ry=20 + 0x31),
        dict(qx=100, qy=20, rx=300, ry=20 + 0x32),
        dict(qx=100, qy=20, rx=300, ry=20 - 0x31),
        dict(qx=100, qy=20, rx=300, ry=20 - 0x32),
        dict(qx=100, qy=20, rx=300, ry=20 + 0x33),
        dict(qx=100, qy=20, rx=300, ry=5, q38_minus_one=True),
        dict(qx=300, qy=20, rx=100, ry=20),
        dict(qx=300, qy=20, rx=300, ry=21),
        dict(qx=100, qy=20, rx=164, ry=20, blockers=(100,)),
        dict(qx=100, qy=20, rx=300, ry=20, blockers=(164,)),
        dict(qx=100, qy=20, rx=300, ry=20, blockers=(300,)),
        dict(qx=100, qy=20, rx=297, ry=20, blockers=(297,)),
        dict(qx=300, qy=20, rx=100, ry=20, blockers=(268,)),
        dict(qx=300, qy=20, rx=100, ry=20, blockers=(100,)),
        dict(qx=300, qy=20, rx=100, ry=20, blockers=(300,)),
        dict(qx=-40, qy=20, rx=90, ry=20, blockers=(0,)),
        dict(qx=-40, qy=20, rx=90, ry=20),
        dict(qx=650, qy=20, rx=800, ry=20),
        dict(qx=800, qy=20, rx=650, ry=20, blockers=(699,)),
        dict(qx=100, qy=-5, rx=300, ry=-5),
        dict(qx=100, qy=60, rx=300, ry=60, blockers=(699,)),
        dict(qx=100, qy=20, rx=100, ry=20),
        dict(qx=100, qy=20, rx=101, ry=20),
        dict(qx=100, qy=20, rx=99, ry=20),
    ]
    for scan in scans:
        yield Case(f"ef70 scan {scan}", F_44EF70, ef70_setup(r, 1.5, 2.5, 3.5, True, 9, 0x100, 2, dict(scan)),
                   receiver=lambda t: t["L"])
        if scan in scans[:5]:
            yield Case(f"ef70 scan shifted {scan}", F_44EF70,
                       ef70_setup(r, 1.5, 2.5, 3.5, True, 9, 0x100, 2, dict(scan, shifts=(2, 1))),
                       receiver=lambda t: t["L"])
    for anim in ((5, 0), (1, 0), (10, 1), (3, 1), (2, 1)):
        for step in (1, 5):
            yield Case(f"ef70 animation counter {anim} step {step}", F_44EF70,
                       ef70_setup(r, 1.5, 2.5, 3.5, True, 4, 0, 6, None, anim=anim, step=step), receiver=lambda t: t["L"])


# ----------------------------------------------------------------------------------------------
# helpers for the larger logic functions
def attach_edge(env, random_source, logic, result_one):
    """Make 0x43eab0 see a platform edge (result 1) or nothing at all (result 0)."""
    px, ry, width, height = 150, 40, 320, 64

    def classify(cx, cy):
        if result_one and cy == ry and px - 5 <= cx <= px + 5:
            return 1
        if result_one and cy == ry - 1:
            return 0
        return None
    tmap = build_tilemap(env, random_source, width, height, 0, 0, classify)
    owner = make_actor(env, random_source, make_world(env, tmap))
    env.put(owner + 0x124, 0)
    env.put(owner + 0x50, ry - 1)
    env.put(logic + 0x128, owner)
    env.put(env.get(logic + 0x12C) + 0x4C, px)


def attach_scan(env, random_source, logic, kind):
    """The 0x4cda10 collision scan between the logic's actor (L+0x194) and the player (global)."""
    qx, qy, rx = 100, 20, 300
    width, height = 700, 48

    def classify(cx, cy):
        if cy == qy and kind == "blocked" and cx == qx:
            return 1
        return None if cy == qy else random_source.choice((None, 0, 1, 2, 3))
    tmap = build_tilemap(env, random_source, width, height, 0, 0, classify)
    holder = env.object(0x60, "scan-holder", words=words_of(random_source, 0x18))
    env.put(holder + 0x0C, make_world(env, tmap))
    mover = env.object(0x60, "scanner", words=words_of(random_source, 0x18))
    player = env.object(0x60, "player", words=words_of(random_source, 0x18))
    ry = {"far": qy + 0x32, "far-below": qy - 0x32}.get(kind, qy + random_source.randrange(-0x31, 0x32))
    env.put(mover + 0x4C, qx, qy)
    env.put(mover + 0x38, M32 if kind == "minus1" else random_source.randrange(0, 1 << 30))
    env.put(player + 0x4C, rx, ry & M32)
    env.put(logic + 0x190, holder)
    env.put(logic + 0x194, mover)
    env.put(G_WORLD_PLAYER, player)


# ----------------------------------------------------------------------------------------------
# 0x44d000
FN_STRIKE_NAMES = dict(zip(("LS_STRIKE", "LS_JUMP", "LS_JUMPBACK", "LS_DEAD", "LS_LIFTED", "LS_THROWN", "LS_DROPPED"), STATE_NAMES))
LS_DEAD = 0x5234F4


def d000_setup(random_source, name=0x400100, size=12, word=0x2, mode_skip=True, g541334=0, ticks=1000, last=900,
               period=50, p40_bit1=False, scan="none", l184=0, l20=2, p8_bit4=False, p80=None, l448=0, edge=0,
               roll=77, l14=0):
    """p80: None or (flags164, state_at_6c_1c)."""
    def setup(env):
        logic, actor = base_logic(env, random_source)
        word_value = word | (2 if not mode_skip else 0)
        set_bits(env, logic, size, word_value)
        env.put(logic + 0x2F4, 0x513E34)
        env.put(logic + 0x2F8, 0x544B68)
        env.put(G_MODE, 0x26B7 if mode_skip else random_source.randrange(0, 0x26B7))
        env.put(0x541334, g541334)
        env.put(G_TICKS, ticks)
        env.put(logic + 0x440, last & M32)
        env.put(logic + 0x444, period)
        env.put(logic + 0x184, l184 & M32)
        env.put(logic + 0x20, l20 & M32)
        env.put(logic + 0x14, l14)
        env.put(logic + 0x448, l448)
        owner_info = env.object(0x150, "owner-rect", words=words_of(random_source, 0x54))
        env.put(logic + 0x0C, owner_info)
        env.put(actor + 0x40, (random_source.randrange(0, 1 << 32) & ~2) | (2 if p40_bit1 else 0))
        env.put(actor + 0x08, (random_source.randrange(0, 1 << 32) & ~0x10) | (0x10 if p8_bit4 else 0))
        env.put(actor + 0x164, random_source.randrange(0, 1 << 32) & ~0x1)
        if p80 is None:
            env.put(actor + 0x80, 0)
        else:
            platform = env.object(0x180, "platform", words=words_of(random_source, 0x60))
            inner = env.object(0x40, "platform-state", words=words_of(random_source, 0x10))
            env.put(platform + 0x164, p80[0])
            env.put(platform + 0x6C, inner)
            env.put(inner + 0x1C, p80[1])
            env.put(actor + 0x80, platform)
        if scan == "none":
            holder = env.object(0x60, "scan-holder", words=words_of(random_source, 0x18))
            env.put(holder + 0x0C, make_world(env, build_tilemap(env, random_source, 16, 16, 0, 0, lambda cx, cy: 0)))
            env.put(logic + 0x190, holder)
            env.put(logic + 0x194, env.object(0x60, "scanner", words=words_of(random_source, 0x18)))
            env.put(G_WORLD_PLAYER, env.object(0x60, "player", words=words_of(random_source, 0x18)))
        else:
            attach_scan(env, random_source, logic, scan)
        attach_edge(env, random_source, logic, edge)
        env.override(RAND, sequence(roll))
        return {"L": logic, "P": actor}
    return setup


def d000_case(label, random_source, **options):
    name = options.get("name", 0x400100)
    options.pop("name", None)
    return Case(label, F_44D000, d000_setup(random_source, name=name, **options),
                receiver=lambda t: t["L"], arguments=(name,))


def d000_cases(random_source):
    r = random_source
    # Choose branch profiles deterministically; only their unrelated memory words vary by seed.
    for label, name in list(FN_STRIKE_NAMES.items()) + [("other", 0x400100)]:
        for ticks, last, period in ((1000, 900, 100), (1000, 900, 101), (5, 10, 8)):
            yield d000_case(f"d000 name {label} window {ticks}/{last}/{period}", r, name=name,
                            size=12, word=0x202, ticks=ticks, last=last, period=period,
                            g541334=int(period == 101))
    for size, bit9 in ((12, True), (12, False), (9, True), (0x21, True), (0x30, False)):
        yield d000_case(f"d000 bit9={bit9} size={size:#x}", r, size=size,
                        word=(0x200 if bit9 else 0) | 2)
    for roll in (0, 1, 999, 1000, 5000, 0x7FFF):
        yield d000_case(f"d000 random roll {roll}", r, roll=roll)
    for p40 in (False, True):
        for l14 in (0, 0x1234):
            yield d000_case(f"d000 facing flag {p40}", r, p40_bit1=p40, l14=l14)
    for scan in ("blocked", "near", "minus1", "far", "far-below"):
        for size, bit8 in ((12, True), (12, False), (8, True), (9, True), (9, False), (0x25, True)):
            yield d000_case(f"d000 scan {scan} size={size:#x} bit8={bit8}", r, mode_skip=False,
                            scan=scan, size=size, word=(0x100 if bit8 else 0) | 2)
    for l184 in (0, 4, 5, 6, 7, -5):
        for index, (size, bit7) in enumerate(((12, True), (12, False), (8, True), (8, False),
                                            (7, True), (3, False), (0x25, False), (0x25, True))):
            yield d000_case(f"d000 state {l184} size={size:#x} bit7={bit7}", r, l184=l184,
                            size=size, word=0x80 if bit7 else 0, l20=(1, 2, -3)[index % 3],
                            name=LS_DEAD if index == 0 else 0x400100)
    platforms = (None, (0x8000, 5), (0x8000, 4), (0, 5), (0x20000, 5),
                 (0x10000, 5), (0x30000, 5), (0x10000, 4), (0x28000, 5))
    for p8 in (False, True):
        for index, p80 in enumerate(platforms):
            yield d000_case(f"d000 platform p8={p8} p80={p80}", r, p8_bit4=p8, p80=p80,
                            l448=index % 2, size=12, word=0, l20=1 if index == 4 else 2)
    for l20 in (1, 2):
        yield d000_case(f"d000 pending platform reaction l20={l20}", r,
                        p80=(0x20000, 5), l448=1, l20=l20)
    # Both death states and all bit storage forms get each toggle direction.
    for l184 in (5, 6):
        for size in (7, 8, 0x20, 0x21, 0x40):
            for bit7 in (False, True):
                word = (r.randrange(0, 1 << 32) | 0x80) if bit7 else (r.randrange(0, 1 << 32) & ~0x80)
                yield d000_case(f"d000 state toggle {l184} size={size:#x} bit7={bit7}", r,
                                l184=l184, size=size, word=word & ~2, l20=1 if bit7 else 2)
    for size in (2, 3, 0x20, 0x21, 0x30, 0x61):
        for word in (0, 4):
            yield d000_case(f"d000 platform tail size={size:#x} word={word}", r,
                            p8_bit4=True, p80=None, l448=0, size=size, word=word)
    for edge in (0, 1):
        for size, bit2 in ((12, True), (12, False), (2, True), (3, True), (0x22, True), (0x22, False)):
            for l20 in (1, 2):
                yield d000_case(f"d000 edge={edge} size={size:#x} bit2={bit2} l20={l20}", r,
                                edge=edge, size=size, word=4 if bit2 else 0, l20=l20)


# ----------------------------------------------------------------------------------------------
# constructors
def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def make_registry(env, random_source, entries, buckets):
    """The string table behind FUN_004f6286, embedded at owner+0x10: +4 buckets, +8 count, nodes [next, ?, key, value]."""
    owner = env.object(0x40, "registry-owner", words=words_of(random_source, 0x10))
    table = owner + 0x10
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if random_source.random() < 0.5 else node)
    return owner


GAME_NAMES = [b"GAME_SPLASH", b"GAME_HIT1", b"GAME_HIT2", b"GAME_HIT3", b"GAME_HIT4", b"GAME_PURELEASE1",
              b"LEVEL_DEATHTILE", b"GAME_SOLHITL2", b"GAME_SOLHITHI", b"GAME_LELAND"]


def ctor_setup(random_source, present=(), info_zero=(), info_depth=1, p40_bit1=False, big_string=None, rects=True):
    def setup(env):
        info = env.object(0x180, "info", words=words_of(random_source, 0x60))
        for offset in info_zero:
            env.put(info + offset, 0)
        env.put(info + 0x64, info_depth & M32)
        tmap = env.object(0x80, "ctor-tilemap", words=words_of(random_source, 0x20))
        env.put(tmap + 0x64, random_source.randrange(0, 100), random_source.randrange(0, 100))
        h1 = make_registry(env, random_source, {}, 3)
        registry = make_registry(env, random_source,
                                 {name: random_source.randrange(1, 1 << 32) for name in GAME_NAMES if name in present}, 5)
        z, u = h1, registry
        world = env.object(0x40, "ctor-world", words=words_of(random_source, 0x10))
        env.put(world + 0x14, z)
        env.put(world + 0x24, tmap)
        env.put(world + 0x28, u)
        actor = make_actor(env, random_source, world)
        env.put(actor + 0x6C, info)
        env.put(actor + 0x08, random_source.randrange(0, 1 << 32) & ~0x10)
        env.put(actor + 0x40, (random_source.randrange(0, 1 << 32) & ~2) | (2 if p40_bit1 else 0))
        env.put(G_TICKS, random_source.randrange(1, 1 << 30))
        logic = env.object(0x460, "constructed-logic", words=words_of(random_source, 0x118))
        if big_string is not None:
            env.write(0x534938, big_string + b"\0")
        if rects:
            def rect(env, call):
                n = env.calls_so_far(call.function) * 0x1010
                env.put(call.arguments[0], n + 1, n + 2, n + 3, n + 4)
                return 1
            env.override(SET_RECT_EMPTY, rect)

            def set_rect(env, call):
                env.put(call.arguments[0], *call.arguments[1:5])
                return 1
            env.override(SET_RECT, set_rect)
        return {"L": logic, "P": actor}
    return setup


def with_malloc_failure(setup, first_failing_call):
    def wrapped(env):
        tokens = setup(env)
        env.override(0x4A48E0, allocate(fail_from_call=first_failing_call))
        return tokens
    return wrapped


def ctor_cases(random_source):
    r = random_source
    zero_sets = [(), (0x2C,), (0x34,), (0x30,), (0x38,), (0x2C, 0x34, 0x30, 0x38), (0x2C, 0x38), (0x34, 0x30)]
    for zeros in zero_sets:
        present = tuple(r.sample(GAME_NAMES, r.randrange(0, len(GAME_NAMES) + 1)))
        for depth in (r.choice((1, 5)), r.choice((0, -2))):
            yield Case(f"ctor 4332f0 zero info {[hex(z) for z in zeros]} depth {depth}", F_4332F0,
                       ctor_setup(r, present, zeros, depth, r.random() < 0.5),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for string in (b"40", b"3, 40", b"1-3 40", b"5-9", b"33", b"3-70", b"2"):
        for depth in (1, 0):
            yield Case(f"ctor 4332f0 bit string {string!r} depth {depth}", F_4332F0,
                       ctor_setup(r, tuple(GAME_NAMES), (), depth, False, big_string=string),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for failing in (2, 3):
        yield Case(f"ctor 4332f0 allocation fails from call {failing}", F_4332F0,
                   with_malloc_failure(ctor_setup(r, tuple(GAME_NAMES[:4]), (), 1, False, big_string=b"40"), failing),
                   receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for zeros in zero_sets:
        present = tuple(r.sample(GAME_NAMES, r.randrange(0, len(GAME_NAMES) + 1)))
        for p40 in (False, True):
            yield Case(f"ctor 44c000 zero info {[hex(z) for z in zeros]} facing {p40}", F_44C000,
                       ctor_setup(r, present, zeros, r.choice((1, 0, -3)), p40),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    # Distinct, non-zero words at +0x104 and +0x10c of both the actor and the info object, so a tail that re-reads
    # the wrong object pointer leaves different bytes behind.
    for info_word, actor_word in ((0x12345, 0x7654321), (0x7FFFFFF1, 3), (0xFFFF0001, 0x1000), (7, 0x7FFFFFFF)):
        def tail_setup(info_word=info_word, actor_word=actor_word):
            inner = ctor_setup(r, (), (), 1, False)

            def setup(env):
                tokens = inner(env)
                info = env.get(tokens["P"] + 0x6C)
                for offset, delta in ((0x104, 0), (0x10C, 0x11)):
                    env.put(info + offset, (info_word + delta) & M32)
                    env.put(tokens["P"] + offset, (actor_word + delta) & M32)
                return tokens
            return setup
        yield Case(f"ctor 44c000 tail words info={info_word:#x} actor={actor_word:#x}", F_44C000, tail_setup(),
                   receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for string in (b"40", b"3-70"):
        yield Case(f"ctor 44c000 bit string {string!r}", F_44C000,
                   ctor_setup(r, tuple(GAME_NAMES), (), 1, True, big_string=string),
                   receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for zeros in zero_sets:
        for _ in range(2):
            yield Case(f"ctor 44bc60 zero info {[hex(z) for z in zeros]}", F_44BC60,
                       ctor_setup(r, (), zeros, 1, r.random() < 0.5),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))


def ctor_aliased_registry_cases(random_source):
    # Registry buckets may reside in writable receiver storage. This makes the
    # original initialization observable before later resource-result overwrites.
    for offset, name in ((0x3A8, b"GAME_HIT1"), (0x408, b"GAME_HIT1")):
        inner = ctor_setup(random_source, (), (), 1, False)

        def setup(env, inner=inner, offset=offset, name=name):
            tokens = inner(env)
            registry = make_registry(env, random_source, {name: 0x13579BDF}, 1)
            buckets = env.get(registry + 0x14)
            node = env.get(buckets)
            env.put(registry + 0x14, tokens["L"] + offset)
            env.put(tokens["L"] + offset, node)
            world = env.get(tokens["P"] + 0x0C)
            env.put(world + 0x28, registry)
            return tokens

        yield Case(f"ctor44c000 resource buckets alias initialized receiver{offset:#x}", F_44C000,
                   setup, receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))


def ctor_environment_cases(random_source):
    # The original compares the freshly initialized motion state, then the derived
    # constructor performs its own conversions. Never seed an expected final C0.
    for function in (F_4332F0, F_44BC60, F_44C000):
        for status in (0, 0x20, 0x21):
            for ticks in (0, 1, 0xFFFFFFFF):
                inner = ctor_setup(random_source, (), (0x2C, 0x34, 0x30, 0x38), 1, False)

                def setup(env, inner=inner, status=status, ticks=ticks):
                    env.entry_x87_status(status)
                    tokens = inner(env)
                    env.put(G_TICKS, ticks)
                    return tokens

                yield Case(f"ctor {function:x} inherited SW {status:#x} unsigned clock {ticks:#x}",
                           function, setup, receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))


def cases(random_source):
    yield from lookup_cases(random_source)
    yield from collector_cases(random_source)
    yield from dispatch_cases(random_source)
    yield from edd0_cases(random_source)
    yield from d3c0_cases(random_source)
    yield from edge_cases(random_source)
    yield from ef70_cases(random_source)
    yield from d000_cases(random_source)
    yield from ctor_cases(random_source)
    yield from ctor_environment_cases(random_source)
    yield from ctor_aliased_registry_cases(random_source)
    yield from ctor_aliased_info_cases(random_source)
    yield from grow_dispatch_cases(random_source)
    yield from source_dispatch_cases(random_source)
    yield from small_bitset_cases(random_source)



G_DEFAULT_BITS = 0x533470   # default capacity handed to the bit set parser 0x4dbe10
G_BIT_STRING = 0x534938


def small_bitset_setup(random_source, default_bits, text, depth):
    base_setup = ctor_setup(random_source, (), (), depth, False)

    def setup(env):
        tokens = base_setup(env)
        env.put(G_DEFAULT_BITS, default_bits)
        env.write(G_BIT_STRING, text + b"\0")
        return tokens
    return setup


def with_one_malloc_failure(setup, failing_call):
    """Only the `failing_call`-th malloc returns 0; every other call allocates."""
    ordinary = allocate()

    def failing_once(env, call):
        if env.calls_so_far(call.function) == failing_call:
            return 0
        return ordinary(env, call)

    def wrapped(env):
        tokens = setup(env)
        env.override(0x4A48E0, failing_once)
        return tokens
    return wrapped


def small_bitset_cases(random_source):
    """A failed bit-array allocation (0x4dc7b0) leaves the size field as a word count, so the capacity
    seen at 0x433689 and 0x4336a9 can be small."""
    r = random_source
    for default_bits in (40, 100, 270):
        for depth in (3, 0, -2):
            yield Case(f"ctor 4332f0 second bit set allocation fails once, default {default_bits} depth {depth}",
                       F_4332F0,
                       with_one_malloc_failure(small_bitset_setup(r, default_bits, b"", depth), 2),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))


# Physical TownGuard fallback join: CALL 0x497235 returns to 0x49723a.
def source_dispatch_cases(random_source):
    ordinary = list(dispatch_cases(random_source)) + list(grow_dispatch_cases(random_source))
    for ordinal, case in enumerate(ordinary):
        def setup(env, original=case.setup, argument=case.arguments[0], ordinal=ordinal):
            tokens = original(env)
            # Vary incoming frame identity and preserved witnesses independently
            # of the table's receiver/index; these words survive in stack residue.
            source = NativeSourceContext()
            source.size = 72
            source.version = 1
            source.inputMask = 0x7FF
            source.outputMask = 0x5FF
            source.preserveMask = 0x472
            for register in ("eax", "ebx", "edx", "esi", "edi", "ebp"):
                setattr(source, register, random_source.randrange(1, 1 << 32))
            source.ecx = tokens["this"]
            source.esp = 0x02007F00 - (ordinal % 3) * 0x40
            source.eip = F_44C840
            source.eflags = (0x2, 0x46, 0x893)[ordinal % 3]
            source.fsHead = 0xFFFFFFFF
            # Seed neighboring bounded stack words so skipped pushes/pops and
            # misplaced descendant return words cannot hide in zeroed backing.
            env.write(source.esp - 0x100, struct.pack("<" + "I" * 64,
                      *words_of(random_source, 64)))
            env.put(source.esp, 0x49723A)
            index = argument(tokens) if callable(argument) else argument
            env.put(source.esp + 4, index & M32)
            trace = env.object(0x80, "source-handler-observation", fill=0xA5)
            for key in tokens["stubs"]:
                table, slot = key if isinstance(key, tuple) else ("second", key)
                g = DISPATCH_GLOBALS[table]
                area = env.get(g["base"])
                stride = env.get(g["stride"])
                result = (0x100 if isinstance(key, tuple) else 0x200) + slot

                def observe(env, call, result=result):
                    cpu = call.source_context
                    env.put(trace, call.receiver, call.source_return_pc,
                            cpu.eax, cpu.ebx, cpu.ecx, cpu.edx, cpu.esi,
                            cpu.edi, cpu.ebp, cpu.esp, cpu.eip, cpu.fsHead)
                    return result

                handler = env.stub(f"source-{table}-handler-{slot}", "thiscall", 0, observe)
                env.put(area + slot * stride, handler)
            tokens["source"] = source
            return tokens

        yield replace(case, label="source TownGuard fallback " + case.label,
                      setup=setup, source_context=lambda t: t["source"],
                      source_return_pc=0x49723A)


def ctor_aliased_info_cases(random_source):
    # 0x44be6c reads info+0x2c after initializing receiver+0x44/+0x48.
    # Those early zeroes therefore remain observable before the later repeats
    # at 0x44bf83/0x44bf95 when the info storage shares this receiver.
    for info_offset in (0x18, 0x1C):
        inner = ctor_setup(random_source, (), (), 1, False)

        def setup(env, inner=inner, info_offset=info_offset):
            tokens = inner(env)
            env.put(tokens["P"] + 0x6C, tokens["L"] + info_offset)
            return tokens

        yield Case(f"ctor44bc60 info aliases receiver+{info_offset:#x}",
                   F_44BC60, setup, receiver=lambda t: t["L"],
                   arguments=(lambda t: t["P"],))

