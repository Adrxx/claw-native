"""Cases for level_one_collision_dispatch_02: Level 1 tile collision movement resolvers.

One shared world builder: a level object (tile table at +0x4c, tile plane at +0x5c, platform list behind
+0xc), a tile plane (pixel size, shifts, row-offset table, tile ids), tile objects whose virtual slot +0x20
is a scripted stand-in, and an actor.  The stand-in answers from a per-pixel type map unless a scripted
sequence overrides the Nth call, can modify actor fields at the Nth call, and logs every call (receiver and
coordinates) into surviving memory.

Every owned byte range is reached by the fixed deterministic scenarios (private seeded generators); the
random_source only adds variety.
"""
import random

from clawparity.cases import Case

CBFF0, CC1B0, CC420, CC570, CC6C0 = 0x4CBFF0, 0x4CC1B0, 0x4CC420, 0x4CC570, 0x4CC6C0
CC9A0, CCC50, CCEF0, CD1C0, CD800 = 0x4CC9A0, 0x4CCC50, 0x4CCEF0, 0x4CD1C0, 0x4CD800

# actor field offsets
X, Y, FLAGS, PLAT, STATE, XSTEP, YSTEP, LEFT, TOP, RIGHT, BOTTOM = (
    0x4C, 0x50, 0x08, 0x80, 0xCC, 0xDC, 0xE0, 0x118, 0x11C, 0x120, 0x124)
EMPTY_A, EMPTY_B = 0xEEEEEEEE, 0xFFFFFFFF
NO_OVERRIDE = 0x7FFFFFFF
LOG_CAPACITY = 400
SEQ_CAPACITY = 40


def _bytes(rng, n):
    return bytes(rng.randrange(1, 256) for _ in range(n))


def make_spec(rng, style=None, sx=None, sy=None):
    """A random but deterministic world description."""
    sx = rng.choice((2, 3)) if sx is None else sx
    sy = rng.choice((2, 3)) if sy is None else sy
    tw, th = 1 << sx, 1 << sy
    cols, rows = rng.randint(3, 6), rng.randint(3, 6)
    spec = {
        "sx": sx, "sy": sy, "cols": cols, "rows": rows,
        "width": cols * tw - rng.randrange(tw), "height": rows * th - rng.randrange(th),
    }
    kinds = [[t] * (tw * th) for t in (0, 1, 2, 3, 4, 5)]
    palettes = ((0, 0, 1, 1, 2), (0, 3, 3, 1, 4), (1, 2, 3, 0, 5, 0x101), (0, 0, 0, 0, 3, 1))
    for palette in palettes:
        kinds.append([rng.choice(palette) for _ in range(tw * th)])
    spec["kinds"] = kinds
    spec["kind_width"] = [rng.randint(5, 41) for _ in kinds]
    style = rng.randrange(6) if style is None else style
    weights = {
        0: (6, 1, 1, 1, 1, 0, 1, 1, 1, 1),   # mostly empty air
        1: (1, 4, 1, 1, 1, 0, 1, 1, 1, 1),   # mostly solid
        2: (1, 1, 1, 5, 1, 0, 1, 1, 1, 1),   # mostly one-way
        3: (2, 1, 1, 1, 1, 1, 3, 3, 3, 3),   # noisy
        4: (3, 2, 2, 2, 1, 1, 1, 1, 1, 1),   # mixed
        5: (1, 1, 4, 1, 1, 0, 1, 1, 1, 1),   # mostly type 2
    }[style]
    # indices: 0 -> uniform 0 or empty marker, 1.. map to kinds 1..5, 6..9 noisy kinds
    grid = []
    for _ in range(rows):
        row = []
        for _ in range(cols):
            pick = rng.choices(range(10), weights)[0]
            if pick == 0:
                row.append(rng.choice((EMPTY_A, EMPTY_B, 0, 0xABCD0000, 0x00010000)))
            else:
                row.append((rng.choice((0, 0, 0x1234, 0xFFFF, 0x8000)) << 16) | pick)
        grid.append(row)
    spec["grid"] = grid
    spec["stride_perm"] = rng.sample(range(rows), rows)
    return spec


def make_actor(rng, spec, **override):
    width, height = spec["width"], spec["height"]
    actor = {
        X: rng.randint(-6, width + 6), Y: rng.randint(-6, height + 6),
        FLAGS: rng.choice((0, 0x1000, 0x20)), PLAT: rng.randrange(1, 1 << 30), STATE: rng.choice((1, 1, 6, 0, 2, 4, 3)),
        XSTEP: rng.randint(1, 9), YSTEP: rng.randint(1, 9),
        LEFT: -rng.randint(2, 12), TOP: -rng.randint(4, 24), RIGHT: rng.randint(1, 12), BOTTOM: rng.randint(0, 6),
    }
    actor.update(override)
    return actor


def build(spec, actor, items=(), script=None, hooks=()):
    """setup(env) for one world.  `script` is a list of override return values for the first calls of the
    type stand-in (NO_OVERRIDE keeps the map).  `hooks` is a list of (call_number, field, value) writes to the
    actor, performed when that stand-in call starts."""
    script = list(script or ())
    hooks = list(hooks)
    seed_rng = random.Random(repr((spec["sx"], spec["sy"], spec["cols"], spec["rows"], spec["width"])))

    def setup(env):
        sx, sy = spec["sx"], spec["sy"]
        tw, th = 1 << sx, 1 << sy
        cols, rows = spec["cols"], spec["rows"]
        log = env.object(4 + 12 * LOG_CAPACITY, "type-call-log", fill=0)
        control = env.object(4 + 4 * SEQ_CAPACITY + 16 * 8 + 16, "script", fill=0)
        plane = env.object(0x100, "plane", data=_bytes(seed_rng, 0x100))
        tile_base = env.object(4 * (spec["cols"] * spec["rows"] + 8), "tiles")
        actor_address = env.object(0x200, "actor", data=_bytes(seed_rng, 0x200))
        for offset, value in actor.items():
            env.put(actor_address + offset, value)
        target_of = {"x": actor_address + X, "y": actor_address + Y, "state": actor_address + STATE,
                     "flags": actor_address + FLAGS, "height": plane + 0x34, "width": plane + 0x30, "xstep": actor_address + XSTEP, "ystep": actor_address + YSTEP}
        tile_cell = lambda row, col: (  # noqa: E731
            tile_base + 16 + 4 * (spec["stride_perm"][row] * spec["cols"] + col))
        env.put(control, len(script))
        for index, value in enumerate(script[:SEQ_CAPACITY]):
            env.put(control + 4 + 4 * index, value)
        hook_base = control + 4 + 4 * SEQ_CAPACITY
        env.put(hook_base, len(hooks))
        for index, (number, field, value) in enumerate(hooks[:8]):
            address = tile_cell(field[1], field[2]) if isinstance(field, tuple) else target_of[field]
            env.put(hook_base + 4 + 12 * index, number, address, value)

        def effect(env, call):
            count = env.get(log)
            if count < LOG_CAPACITY:
                env.put(log + 4 + 12 * count, call.receiver, call.arguments[0], call.arguments[1])
            env.put(log, count + 1)
            for index in range(env.get(hook_base)):
                number, address, value = (env.get(hook_base + 4 + 12 * index + 4 * k) for k in range(3))
                if number == count + 1:
                    env.put(address, value)
            if count < env.get(control) and env.get(control + 4 + 4 * count) != NO_OVERRIDE:
                return env.get(control + 4 + 4 * count)
            width = env.get(call.receiver + 8)
            return env.get(call.receiver + 0x10 + 4 * (call.arguments[1] * width + call.arguments[0]))

        stub = env.stub("tile type", "thiscall", 2, effect)
        vtable = env.object(0x40, "vtable", data=_bytes(seed_rng, 0x40))
        env.put(vtable + 0x20, stub)
        objects = []
        for index, kind in enumerate(spec["kinds"]):
            obj = env.object(0x10 + 4 * len(kind), f"tile-kind-{index}", fill=0)
            env.put(obj, vtable, spec["kind_width"][index], tw)
            env.put(obj + 0x10, *kind)
            objects.append(obj)
        table = env.object(4 * len(objects), "tile-table", words=objects)
        stride = cols
        tiles_object = tile_base
        env.put(tiles_object, 3, 3, 3, 3)
        tiles = tiles_object + 16
        offsets = env.object(4 * rows, "row-offsets")
        for row in range(rows):
            start = spec["stride_perm"][row] * stride
            env.put(offsets + 4 * row, start)
            env.put(tiles + 4 * start, *spec["grid"][row])
        env.put(plane + 0x20, tiles, offsets)
        env.put(plane + 0x30, spec["width"], spec["height"])
        env.put(plane + 0x8C, sx)
        env.put(plane + 0x90, sy)
        # platform list: level +0xc -> object +8 -> object +0x14 -> first node ([0] next, [8] item)
        head = 0
        previous = 0
        item_addresses = []
        for item in reversed(list(items)):
            address = env.object(0x180, "item", data=_bytes(seed_rng, 0x180))
            for offset, value in item.items():
                env.put(address + offset, value)
            node = env.object(0x10, "node", data=_bytes(seed_rng, 0x10))
            env.put(node, head)
            env.put(node + 8, address)
            head = node
            item_addresses.append(address)
        holder_inner = env.object(0x20, "list-owner", data=_bytes(seed_rng, 0x20))
        env.put(holder_inner + 0x14, head)
        holder = env.object(0x10, "list-holder", data=_bytes(seed_rng, 0x10))
        env.put(holder + 8, holder_inner)
        level = env.object(0x100, "level", data=_bytes(seed_rng, 0x100))
        env.put(level + 0x0C, holder)
        env.put(level + 0x4C, table)
        env.put(level + 0x5C, 0 if spec.get("no_plane") else plane)
        out = env.object(8, "out", words=[0x7A7A7A7A, 0x6B6B6B6B])
        return {"this": level, "actor": actor_address, "out": out, "log": log, "plane": plane}

    return setup


def _resolve(argument):
    if isinstance(argument, str):
        return lambda tokens, name=argument: tokens[name]
    return argument


def call(label, function, spec, actor, arguments, **world):
    """A case calling `function` on a built world; string arguments name setup tokens."""
    return Case(label, function, build(spec, actor, **world), receiver=lambda tokens: tokens["this"],
                arguments=tuple(_resolve(argument) for argument in arguments))


def _flags(rng):
    value = rng.choice((0, 1, 8, 9, 0x10, 0x11, 0x18, 0x19))
    return value | rng.choice((0, 0, 0x4, 0x20, 0x100, 0x400000))


def _scenario(rng, style=None):
    spec = make_spec(rng, style)
    return spec, make_actor(rng, spec)


def _x_target(rng, spec, actor, direction=None):
    delta = rng.randint(1, 14)
    sign = rng.choice((-1, 1)) if direction is None else direction
    return actor[X] + sign * delta


def _items(rng, spec, actor, count):
    items = []
    for _ in range(count):
        item = {
            0xD0: rng.choice((0x80, 0x80, 0x80, 0x81)),
            0x128: rng.choice((-1, rng.randint(-10, 10), rng.randint(-10, 10))),
            0x4C: actor[X] + rng.randint(-14, 14), 0x50: actor[Y] + rng.randint(-4, 10),
            0x12C: rng.randint(-4, 14), 0x130: rng.randint(-2, 24), 0x15C: rng.choice((-3, 0, 0, 2)),
        }
        items.append(item)
    return items


def cases(random_source):
    # ------------------------------------------------------------ directed scenarios
    yield from directed()
    # ------------------------------------------------------------ deterministic random sweeps
    rng = random.Random(0x5EED)
    for index in range(16):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"right sweep {index}", CC420, spec, actor, ("actor", _x_target(rng, spec, actor, 1), actor[Y] + rng.randint(-6, 6), "out", rng.randrange(0, 1 << 16)))
    for index in range(16):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"left sweep {index}", CC570, spec, actor, ("actor", _x_target(rng, spec, actor, -1), actor[Y] + rng.randint(-6, 6), "out", rng.randrange(0, 1 << 16)))
    for index in range(22):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"ceiling {index}", CCC50, spec, actor, ("actor", actor[X] + rng.randint(-8, 8), actor[Y] + rng.randint(-10, 6), rng.randrange(0, 64)))
    for index in range(26):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"floor {index}", CC9A0, spec, actor, ("actor", actor[X] + rng.randint(-8, 8), actor[Y] + rng.randint(-8, 12), _flags(rng)))
    for index in range(22):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"landing {index}", CC6C0, spec, actor, ("actor", actor[X] + rng.randint(-8, 8), actor[Y] + rng.randint(-8, 12), _flags(rng)))
    for index in range(16):
        spec, actor = _scenario(rng, index % 6)
        items = _items(rng, spec, actor, rng.randint(0, 4))
        yield call(f"platforms {index}", CCEF0, spec, actor, ("actor", actor[X] + rng.randint(-8, 8), actor[Y] + rng.randint(-4, 12), "out", rng.choice((8, 9, 0, 0x18, 0x10))), items=items)
    for index in range(16):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"foot probe {index}", CD1C0, spec, actor, ("actor", rng.randint(-10, 10)))
    for index in range(16):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"fall scan {index}", CD800, spec, actor, ("actor", rng.randrange(1 << 32)))
    for index in range(22):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"move {index}", CBFF0, spec, actor, ("actor", _x_target(rng, spec, actor), actor[Y] + rng.randint(-8, 10), _flags(rng)),
                   items=_items(rng, spec, actor, rng.randint(0, 2)))
    for index in range(18):
        spec, actor = _scenario(rng, index % 6)
        yield call(f"move wall {index}", CC1B0, spec, actor, ("actor", _x_target(rng, spec, actor), actor[Y] + rng.randint(-8, 10), _flags(rng)))
    # ------------------------------------------------------------ seed-dependent extra variety
    for index in range(12):
        style = random_source.randrange(6)
        spec = make_spec(random_source, style)
        actor = make_actor(random_source, spec)
        function = random_source.choice((CBFF0, CC1B0, CC420, CC570, CC6C0, CC9A0, CCC50, CCEF0, CD1C0, CD800))
        x = actor[X] + random_source.randint(-12, 12)
        y = actor[Y] + random_source.randint(-8, 12)
        arguments = {
            CBFF0: ("actor", x, y, _flags(random_source)), CC1B0: ("actor", x, y, _flags(random_source)),
            CC420: ("actor", x, y, "out", 0), CC570: ("actor", x, y, "out", 0), CC6C0: ("actor", x, y, _flags(random_source)),
            CC9A0: ("actor", x, y, _flags(random_source)), CCC50: ("actor", x, y, 0),
            CCEF0: ("actor", x, y, "out", 8), CD1C0: ("actor", x - actor[X]), CD800: ("actor", 0),
        }[function]
        yield call(f"random {index}", function, spec, actor, arguments,
                   items=_items(random_source, spec, actor, random_source.randint(0, 3)) if function in (CCEF0, CBFF0) else ())


def fixed_spec(sx, sy, rows_of_tiles, width_trim=0, height_trim=0, seed=1, **extra):
    """A world with a hand-written tile grid.  Entries: 'E'/'F' empty markers, an int kind index (0-9)."""
    rng = random.Random(seed)
    spec = make_spec(rng, 0, sx, sy)
    rows, cols = len(rows_of_tiles), len(rows_of_tiles[0])
    tw, th = 1 << sx, 1 << sy
    spec.update(cols=cols, rows=rows, width=cols * tw - width_trim, height=rows * th - height_trim)
    spec["grid"] = [[EMPTY_A if t == "E" else EMPTY_B if t == "F" else (0x7700 << 16 | t) if t >= 6 else t for t in row]
                    for row in rows_of_tiles]
    spec["stride_perm"] = rng.sample(range(rows), rows)
    spec.update(extra)
    return spec


def plain_actor(**fields):
    base = {X: 20, Y: 16, FLAGS: 0x1000, PLAT: 0x55, STATE: 1, XSTEP: 3, YSTEP: 3,
            LEFT: -4, TOP: -10, RIGHT: 4, BOTTOM: -10}
    names = {"x": X, "y": Y, "flags": FLAGS, "state": STATE, "xstep": XSTEP, "ystep": YSTEP,
             "left": LEFT, "top": TOP, "right": RIGHT, "bottom": BOTTOM}
    for name, value in fields.items():
        base[names[name]] = value
    return base


BIG = (
    (0, 1, 2, 3, 4),
    (6, 7, 8, 9, "E"),
    ("F", 1, 1, 2, 3),
    (5, 6, 9, 0, 1),
    (1, 2, 3, 4, 7),
)


def directed():
    yield from requested()
    yield from directed_main()


def requested():
    uniform = tuple(tuple(3 for _ in range(5)) for _ in range(5))
    for name, function in (("move", CBFF0), ("wall", CC1B0)):
        for x in (20, 21, 19, 27):
            for flags in (0, 1, 0x10, 0x11, 0x15):
                hook_options = [None]
                if flags & 0x11 == 0x11:
                    hook_options.append("empty")
                for option in hook_options:
                    call_number = 1 if x == 20 and function == CBFF0 else 2 if x == 20 or function == CBFF0 else 3
                    if function == CC1B0 and x != 20:
                        call_number = 3
                    spec = fixed_spec(3, 3, uniform, 3, 2, seed=5)
                    hooks = [(call_number, ("tile", 0, 2), EMPTY_A)] if option else []
                    actor = plain_actor(state=1, y=16, xstep=100, flags=0x1357)
                    yield call(f"{name} x={x} flags={flags:#x} {option}", function, spec, actor, ("actor", x, 21, flags), hooks=hooks)
    for width in (0, 1):
        spec = fixed_spec(3, 3, BIG, 3, 2, width=width)
        yield call(f"narrow {width} right", CC420, spec, plain_actor(top=-6, bottom=6), ("actor", -4, 14, "out", 0))
        yield call(f"narrow {width} left", CC570, spec, plain_actor(top=-6, bottom=6), ("actor", 4, 14, "out", 0))
        yield call(f"narrow {width} ceiling", CCC50, spec, plain_actor(x=4, xstep=1), ("actor", 4, 14, 0))
        yield call(f"narrow {width} floor", CC9A0, spec, plain_actor(xstep=1), ("actor", 4, 14, 0))
        yield call(f"narrow {width} landing", CC6C0, spec, plain_actor(xstep=1), ("actor", 4, 14, 0))
        yield call(f"narrow {width} probe", CD1C0, spec, plain_actor(x=-3), ("actor", 3))
        yield call(f"narrow {width} fall", CD800, spec, plain_actor(x=0, y=6, bottom=1), ("actor", 7))


def directed_main():
    big = fixed_spec(3, 3, BIG, 3, 2)
    # ---- 4cbff0: re-run of the wall scan after the actor moved during the floor probe
    for direction, start_x in (("right", 26), ("left", 14)):
        for hook_value in (14, 30, 20):
            for script in ([1, 0], [1, 0, 1], [1, 0, 0, 1]):
                spec = fixed_spec(3, 3, BIG, 3, 2)
                yield call(f"move {direction} then actor shifts to {hook_value} script {script}", CBFF0, spec, plain_actor(),
                           ("actor", start_x, 16, 1), script=script, hooks=[(2, "x", hook_value)])
    spec = fixed_spec(3, 3, BIG, 3, 2)
    yield call("move left, wall, actor shifts, nudge flag off", CBFF0, spec, plain_actor(), ("actor", 14, 16, 0x1 | 0x4), script=[1, 3, 3], hooks=[(2, "x", 40)])
    yield call("move, state 1 with wall, no floor flag, actor unchanged", CBFF0, spec, plain_actor(), ("actor", 26, 16, 0), script=[1])
    yield call("move, wall hit while state is not 1", CBFF0, spec, plain_actor(state=6), ("actor", 26, 16, 0), script=[1, 3])
    yield call("move with wall and state 1 and floor flag 3 from callback", CBFF0, spec, plain_actor(), ("actor", 26, 16, 0x11), script=[1, 3, 3])
    for value in (3, 2, 4):
        yield call(f"move, floor probe returns {value}", CC1B0, spec, plain_actor(), ("actor", 26, 16, 0x11), script=[0, 0, value, value, 3])
    # ---- 4cc420/4cc570: edges of the plane
    for x in (-30, -5, 0, 37, 60):
        for y in (-30, 5, 36):
            yield call(f"right scan x={x} y={y}", CC420, big, plain_actor(top=-6, bottom=6), ("actor", x, y, "out", 0))
            yield call(f"left scan x={x} y={y}", CC570, big, plain_actor(top=-6, bottom=6), ("actor", x, y, "out", 0))
    # ---- 4cc6c0: empty cell above solid ground, and scripted type combinations
    air = ((5, 5, 5, 5, 5), ("E", "F", "E", 5, 5), (1, 1, 1, 1, 1), (3, 3, 3, 3, 3), (0, 0, 0, 0, 0))
    spec = fixed_spec(3, 3, air)
    for left, right in ((-2, 2), (-2, 14), (-10, 10)):
        yield call(f"landing under empty air {left},{right}", CC6C0, spec, plain_actor(x=16, y=13, left=left, right=right, bottom=2, xstep=4),
                   ("actor", 16, 13, 0))
    spec = fixed_spec(3, 3, ((5, 5, 5, 5, 5), (5, 5, 5, 5, 5), (1, 2, 1, 2, 1), (5, 5, 5, 5, 5), (5, 5, 5, 5, 5)))
    for index, script in enumerate(([1, 0, 0], [2, 1], [1, 2], [2, 0, 2], [2, 0, 1], [1, 3, 2], [2, 4, 0], [2, 3, 3], [2, 5, 2], [1, 2, 2, 2, 2, 2], [3, 3, 3, 3, 3, 3, 3, 3], [3, 3, 0, 3, 3, 3, 3])):
        for state in (1, 6):
            yield call(f"landing script {index} state {state}", CC6C0, spec, plain_actor(x=12, y=12, left=-3, right=9, bottom=3, xstep=4, state=state),
                       ("actor", 12, 12, 0), script=script)
    # ---- 4cd800: guards and scan lengths
    spec = fixed_spec(3, 3, BIG, 3, 2)
    yield call("fall scan, left bound is the sentinel", CD800, spec, plain_actor(left=-0x80000000 & 0xFFFFFFFF), ("actor", 0))
    yield call("fall scan, left bound off by one", CD800, spec, plain_actor(left=-0x7FFFFFFF), ("actor", 0))
    yield call("fall scan, no tile plane", CD800, fixed_spec(3, 3, BIG, 3, 2, no_plane=True), plain_actor(), ("actor", 0))
    for y in (20, 34, 37, 60):
        for script in (None, [0, 0, 0, 2], [0, 3], [4, 5, 0x101, 1]):
            yield call(f"fall scan y={y} script {script}", CD800, spec, plain_actor(y=y, bottom=2 if y < 40 else 30), ("actor", 7), script=script)
    # the plane shrinks during the scan: the row clamp inside the loop is reached
    for new_height in (4, 9, 1):
        yield call(f"fall scan, plane height becomes {new_height}", CD800, spec, plain_actor(y=6, bottom=1), ("actor", 7),
                   script=[0, 0, 0, 0, 0], hooks=[(2, "height", new_height)])
    for x, y, label in ((34, 6, "E"), (3, 18, "F")):
        for script in (None, [0, 0, 3]):
            yield call(f"fall scan starts on empty tile {label}", CD800, spec, plain_actor(x=x, y=y, bottom=1), ("actor", 7), script=script)
    for x in (-5, 35, 80):
        yield call(f"fall scan x={x}", CD800, spec, plain_actor(x=x, y=6, bottom=1), ("actor", 7))
    # ---- 4cd1c0: every combination of the three probes
    for dx in (-30, 0, 16, 70):
        for script in (None, [1], [0, 2], [0, 0, 3], [0, 0, 0], [5, 4, 3], [2, 2, 2], [0, 2, 3]):
            yield call(f"foot probe dx={dx} script {script}", CD1C0, spec, plain_actor(y=14, bottom=3), ("actor", dx), script=script)
    # ---- 4ccef0 platform scans with chosen geometry
    base_item = {0xD0: 0x80, 0x128: 5, 0x4C: 10, 0x50: 20, 0x12C: 2, 0x130: 12, 0x15C: -1}
    for index, change in enumerate((
            {}, {0xD0: 0x7F}, {0x128: -1}, {0x15C: 3}, {0x15C: 0}, {0x4C: 100}, {0x4C: -100}, {0x50: 100}, {0x50: 0},
            {0x12C: 40}, {0x130: -30}, {0x128: 30}, {0x128: -30, 0x130: 2})):
        for actor_y, arg_y, left in ((17, 17, -4), (12, 18, -4), (12, 16, -4), (30, 30, -1)):
            item = {**base_item, **change}
            tail = {**base_item, **{0x50: 40, 0x4C: 30}}
            yield call(f"platform scan variant {index} y={actor_y}/{arg_y} left={left}", CCEF0, spec,
                       plain_actor(x=14, y=actor_y, left=left, right=6, bottom=4), ("actor", 14, arg_y, "out", 8),
                       items=[{**base_item, **{0xD0: 0x40}}, item, tail])
    yield call("platform scan, flag clear", CCEF0, spec, plain_actor(), ("actor", 14, 16, "out", 7), items=[base_item])
    yield call("platform scan, empty list", CCEF0, spec, plain_actor(), ("actor", 14, 16, "out", 8), items=[])
    # ---- 4cbff0 standing on a platform: the platform scan succeeds and replaces y
    platform = {0xD0: 0x80, 0x128: 5, 0x4C: 10, 0x50: 20, 0x12C: 2, 0x130: 12, 0x15C: -1}
    for flags in (8, 9, 0x18, 0x19, 0x8 | 0x400000):
        for state in (1, 6):
            yield call(f"move onto platform flags {flags:#x} state {state}", CBFF0, spec, plain_actor(x=14, y=12, left=-4, right=6, bottom=4, state=state),
                       ("actor", 14, 18, flags), items=[platform])
    yield call("move onto platform with a wall hit", CBFF0, spec, plain_actor(x=14, y=12, left=-4, right=6, bottom=4, state=6),
               ("actor", 20, 18, 8), items=[platform], script=[1])
    # ---- 4cc6c0 on the first tile row: the upper probe row is clamped to the plane
    for kind_row in ((1, 1, 1, 1, 1), (2, 2, 2, 2, 2), (0, 1, 2, 3, 4)):
        spec_top = fixed_spec(3, 3, (kind_row, (5, 5, 5, 5, 5), (5, 5, 5, 5, 5), (5, 5, 5, 5, 5)))
        yield call(f"landing on the top row {kind_row}", CC6C0, spec_top, plain_actor(x=12, y=-3, left=-10, right=18, bottom=2, xstep=7),
                   ("actor", 12, -3, 0))
    # ---- 4cc9a0: the tile below the feet is the 0xffffffff marker
    spec_f = fixed_spec(3, 3, BIG, 3, 2)
    yield call("floor under the 0xffffffff marker", CC9A0, spec_f, plain_actor(x=3, y=14, left=-2, right=3, bottom=2), ("actor", 3, 14, 0))
    # ---- 4cc9a0 / 4ccc50 scripted
    spec = fixed_spec(3, 3, ((5, 5, 5, 5, 5), (5, 5, 5, 5, 5), (1, 2, 1, 2, 1), (1, 1, 1, 1, 1), (5, 5, 5, 5, 5)))
    for index, script in enumerate(([4], [4, 1, 0], [0, 1, 1, 1, 0], [0, 3, 3, 0], [0, 2, 2, 2, 2, 2, 2], [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
                                    [0, 3, 3, 3, 3, 3, 3, 3, 0], [0, 1, 2, 1, 2, 3, 3], [0, 1, 3, 3, 0, 0], [5, 1, 1, 1, 1, 1, 1, 1, 1, 1])):
        for state, y in ((1, 12), (6, 12), (1, 20), (0, 8)):
            yield call(f"floor script {index} state {state} y {y}", CC9A0, spec, plain_actor(x=12, y=14, left=-3, right=9, top=-9, bottom=3, xstep=4, state=state),
                       ("actor", 12, y, 0), script=script)
            yield call(f"ceiling script {index} state {state} y {y}", CCC50, spec, plain_actor(x=12, y=14, left=-3, right=9, top=-9, bottom=3, xstep=4, state=state),
                       ("actor", 12, y - 10, 0), script=script)
