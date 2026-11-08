"""Cases for level_one_collision_dispatch_01: Level 1 tile-manager collision dispatch.

The tile manager ("this") owns a tile map and a table of tile objects whose vtable slot 0x20 classifies a
point inside the tile.  Every classification goes through a stand-in, so the original callees run on a
fully controlled world.  Coverage does not depend on the random seed: the sweeps below use their own
fixed-seed generator, and `random_source` only adds extra worlds.
"""
import random

from clawparity.cases import Case
from clawparity.fixtures import returns  # noqa: F401

DISPATCH = 0x4CBB60
STEP = 0x4CBCD0
MOVE_H = 0x4CBE30

SHIFT_X = 3
SHIFT_Y = 3
COLS = 16
ROWS = 16
WIDTH = COLS << SHIFT_X
HEIGHT = ROWS << SHIFT_Y

EMPTY = "E"   # cell value 0xeeeeeeee
NONE = "F"    # cell value 0xffffffff

# tile id -> collision class returned by the tile object, or a function of the local point
TILE_CLASSES = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 0, 5: 1, 6: 3, 7: 2,
    8: lambda x, y: 1 if x < 4 else 0,
    9: lambda x, y: 3 if y < 4 else 0,
    10: lambda x, y: 1 if y >= 4 else 3,
    11: lambda x, y: 2 if x >= 4 else 1,
}
TILE_WIDTHS = {i: 8 + 8 * (i % 3) + (i // 3) for i in TILE_CLASSES}


def make_grid(index):
    """Deterministic terrain number `index`."""
    rng = random.Random(7000 + index)
    grid = [[0] * COLS for _ in range(ROWS)]
    kind = index % 8
    for r in range(ROWS):
        for c in range(COLS):
            if kind == 0:
                v = 0
            elif kind == 1:
                v = 1 if r >= 11 else 0
            elif kind == 2:
                v = 1 if (c in (4, 11) or r >= 13) else 0
            elif kind == 3:
                v = 3 if (c in (3, 9)) else (1 if r >= 12 else 0)
            elif kind == 4:
                v = rng.choice([0, 0, 1, 2, 3, 8, 9, 10, 11])
            elif kind == 5:
                v = rng.choice([0, 1, 1, 2, 3, 5, 6, 7, 10, 11, EMPTY, NONE])
            elif kind == 6:
                v = 2 if r in (6, 9) else (1 if r >= 14 else (3 if c == 7 else 0))
            else:
                v = rng.choice([0, 4, 1, 2, 3, 6, 7, 8, 9, EMPTY, NONE])
            grid[r][c] = v
    if index >= 8:  # extra worlds get a few extra random cells
        for _ in range(12):
            grid[rng.randrange(ROWS)][rng.randrange(COLS)] = rng.choice([0, 1, 2, 3, 8, 9, 10, 11, EMPTY, NONE])
    return grid


def world(grid, actor, limits=(8, 8), other=None, hi_bits=0, platforms=()):
    """setup() for a tile manager, a tile map, tile objects and one actor."""
    def setup(env):
        manager = env.object(0x80, "tile-manager")
        tilemap = env.object(0xA0, "tile-map")
        tiles = env.object(4 * (max(TILE_CLASSES) + 2), "tile-table")
        data = env.object(4 * ROWS * COLS, "map-data")
        rows = env.object(4 * ROWS, "map-rows")
        object_ = env.object(0x140, "actor")
        for i in range(0x140 // 4):
            env.put(object_ + 4 * i, 0x3A000000 + 0x101 * i)
        for i in range(0xA0 // 4):
            env.put(tilemap + 4 * i, 0x5B000000 + 0x77 * i)
        for i in range(0x80 // 4):
            env.put(manager + 4 * i, 0x6C000000 + 0x31 * i)
        for tile_id, cls in TILE_CLASSES.items():
            effect = (lambda env, call, cls=cls: cls(call.arguments[0], call.arguments[1])) if callable(cls) \
                else returns(cls)
            method = env.stub(f"tile-class-{tile_id}", "thiscall", 2, effect)
            vtable = env.object(0x40, f"tile-vtable-{tile_id}", fill=0x5A)
            env.put(vtable + 0x20, method)
            tile = env.object(0x10, f"tile-{tile_id}", fill=0x33)
            env.put(tile, vtable, TILE_WIDTHS[tile_id])
            env.put(tiles + 4 * tile_id, tile)
        for r in range(ROWS):
            env.put(rows + 4 * r, r * COLS)
            for c in range(COLS):
                v = grid[r][c]
                if v == EMPTY:
                    word = 0xEEEEEEEE
                elif v == NONE:
                    word = 0xFFFFFFFF
                else:
                    word = v | (((r * 31 + c * 7 + hi_bits) & 0x3FFF) << 16 if hi_bits else 0)
                env.put(data + 4 * (r * COLS + c), word)
        env.put(tilemap + 0x20, data, rows)
        env.put(tilemap + 0x30, WIDTH, HEIGHT)
        env.put(tilemap + 0x8C, SHIFT_X, SHIFT_Y)
        env.put(manager + 0x4C, tiles)
        env.put(manager + 0x5C, tilemap)
        env.put(manager + 0x64, limits[0], limits[1])
        a = actor
        env.put(object_ + 0x08, a.get("flags", 0))
        env.put(object_ + 0x4C, a["x"], a["y"])
        if "y54" in a:
            env.put(object_ + 0x54, a["y54"])
        env.put(object_ + 0xCC, a["state"])
        env.put(object_ + 0xDC, a.get("sx", 3))
        env.put(object_ + 0xE0, a.get("sy", 3))
        left, top, right, bottom = a.get("box", (2, 0, 13, 20))
        env.put(object_ + 0x118, left, top, right, bottom)
        partner = 0
        if other is not None:
            partner = env.object(0x140, "partner")
            for i in range(0x140 // 4):
                env.put(partner + 4 * i, 0x71000000 + 0x13 * i)
            env.put(partner + 0x4C, other["x"], other["y"])
            env.put(partner + 0xD0, other.get("kind", 0x80))
            env.put(partner + 0x128, other.get("l", 0))
            env.put(partner + 0x12C, other.get("t", 0))
            env.put(partner + 0x130, other.get("r", 20))
            env.put(partner + 0x134, other.get("b", 24))
        env.put(object_ + 0x80, partner)
        scene = env.object(0x20, "scene", fill=0x44)
        owner = env.object(0x20, "platform-owner", fill=0x45)
        env.put(manager + 0x0C, scene)
        env.put(scene + 0x08, owner)
        head = 0
        for platform in reversed(platforms):
            node = env.object(0x10, "platform-node", fill=0x46)
            body = env.object(0x180, "platform", fill=0x47)
            for i in range(0x180 // 4):
                env.put(body + 4 * i, 0x72000000 + 0x17 * i)
            env.put(body + 0x4C, platform["x"], platform["y"])
            env.put(body + 0xD0, platform.get("kind", 0x80))
            env.put(body + 0x128, platform["l"], platform["t"], platform["r"], platform["b"])
            env.put(body + 0x15C, platform.get("v", 0))
            env.put(node, head, 0x1234, body)
            head = node
        env.put(owner + 0x14, head)
        return {"manager": manager, "object": object_}
    return setup


def call(label, function, setup, x, y, flags):
    return Case(label, function, setup, receiver=lambda t: t["manager"],
                arguments=(lambda t: t["object"], x, y, flags))


def scenario(rng, state, partner_needed=False):
    """One deterministic scenario drawn from `rng`."""
    grid = make_grid(rng.randrange(0, 8))
    ax, ay = rng.randrange(-4, WIDTH + 4), rng.randrange(-4, HEIGHT + 4)
    tx = ax + rng.choice([0, 0, 1, -1, 3, -3, 9, -9, 24, -24, 70, -70])
    ty = ay + rng.choice([0, 0, 1, -1, 3, -3, 9, -9, 24, -24, 70, -70])
    if rng.random() < 0.2:
        tx, ty = rng.randrange(-20, WIDTH + 20), rng.randrange(-20, HEIGHT + 20)
    flags = rng.choice([0, 1, 2, 3, 8, 9, 10, 0x10, 0x11, 0x12, 0x13, 0x18, 0x19, 0x1B, 0x20, 0x7B])
    actor = {
        "x": ax, "y": ay, "state": state,
        "flags": rng.choice([0, 0, 0x10, 0x400000, 0x400010, 0x1, 0x20000]),
        "sx": rng.choice([1, 2, 3, 5]), "sy": rng.choice([1, 2, 3, 5]),
        "box": rng.choice([(2, 0, 13, 20), (0, 0, 7, 7), (3, 4, 10, 30), (1, 2, 5, 16), (0, 0, 0, 0)]),
    }
    other = None
    if partner_needed or flags & 8 or rng.random() < 0.6:
        px = ax + rng.randrange(-6, 7)
        py = ay + rng.randrange(-6, 7)
        other = {"x": px, "y": py, "kind": rng.choice([0x80, 0x80, 0x80, 0x40]),
                 "l": rng.choice([-1, 0, -3, 2]), "t": 0, "r": rng.choice([6, 12, 20, 40]),
                 "b": rng.choice([4, 10, 24])}
    platforms = []
    for _ in range(rng.choice([0, 1, 1, 2, 3])):
        platforms.append({"x": ax + rng.randrange(-12, 13), "y": ay + rng.randrange(-4, 30),
                          "kind": rng.choice([0x80, 0x80, 0x80, 0x40]),
                          "l": rng.choice([-1, 0, -4, 2, 5]), "t": rng.choice([-1, 0, 3, -2]),
                          "r": rng.choice([8, 14, 26, 40]), "b": rng.choice([4, 10, 24]),
                          "v": rng.choice([0, 0, 1, -1, 3, -3])})
    limits = rng.choice([(8, 8), (4, 4), (16, 16), (40, 40), (8, 40), (40, 8), (2, 3)])
    return grid, actor, limits, other, tx, ty, flags, platforms


def cases(random_source):
    rng = random.Random(0xC0111DE)
    index = 0
    for function, name, states, count in (
        (STEP, "step", range(0, 10), 14),
        (MOVE_H, "move", (0, 1, 2, 4, 5, 6, 8), 24),
        (DISPATCH, "dispatch", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), 10),
    ):
        for state in states:
            for _ in range(count):
                grid, actor, limits, other, tx, ty, flags, platforms = scenario(rng, state, function != MOVE_H)
                if function == DISPATCH and index % 3 == 0:
                    # force the far path: a long distance and no early-out flags
                    tx = actor["x"] + rng.choice([-1, 1]) * rng.randrange(20, 90)
                    ty = actor["y"] + rng.choice([-1, 1, 0]) * rng.randrange(0, 90)
                    actor["flags"] &= ~0x10
                setup = world(grid, actor, limits, other, hi_bits=index % 2, platforms=platforms)
                yield call(f"{name} state {state} #{index}", function, setup, tx, ty, flags)
                index += 1
    # worlds drawn from the case random source
    for n in range(12):
        function = (STEP, MOVE_H, DISPATCH)[n % 3]
        grid = make_grid(8 + random_source.randrange(0, 40))
        actor = {
            "x": random_source.randrange(-4, WIDTH + 4), "y": random_source.randrange(-4, HEIGHT + 4),
            "state": random_source.choice([1, 2, 3, 4, 5, 6, 8]),
            "flags": random_source.choice([0, 0x10, 0x400000]),
            "sx": random_source.randrange(1, 6), "sy": random_source.randrange(1, 6),
            "box": (random_source.randrange(0, 4), random_source.randrange(0, 4),
                    random_source.randrange(4, 16), random_source.randrange(8, 32)),
        }
        other = {"x": actor["x"] + random_source.randrange(-5, 6), "y": actor["y"] + random_source.randrange(-5, 6),
                 "l": random_source.randrange(-2, 3), "r": random_source.randrange(8, 40),
                 "b": random_source.randrange(4, 30)} if n % 2 else None
        tx = random_source.randrange(-10, WIDTH + 10)
        ty = random_source.randrange(-10, HEIGHT + 10)
        flags = random_source.randrange(0, 0x40)
        limits = (random_source.randrange(1, 40), random_source.randrange(1, 40))
        platforms = [{"x": actor["x"] + random_source.randrange(-10, 11), "y": actor["y"] + random_source.randrange(0, 30),
                      "kind": random_source.choice([0x80, 0x80, 0x10]), "l": random_source.randrange(-2, 4),
                      "t": random_source.randrange(-2, 4), "r": random_source.randrange(6, 40),
                      "b": random_source.randrange(4, 30), "v": random_source.randrange(-3, 4)}
                     for _ in range(random_source.randrange(0, 3))]
        yield call(f"random world {n}", function, world(grid, actor, limits, other, hi_bits=n % 2, platforms=platforms), tx, ty, flags)

    # exact-boundary cases: distances equal to, one below and one above the step limits (distinct per axis)
    limit_x, limit_y = 8, 12
    xs = (0, 7, 8, 9, 17, -8, -9, -16)
    ys = (0, 11, 12, 13, -12, -13, -24)
    states = (1, 3, 4, 8, 6, 2, 5)
    # Early dispatch versus stepping.  Within both limits the dispatcher hands the whole move to 0x4cbcd0
    # once; outside them it steps and repeats until arrival or a stop bit.  The object x never equals its y, so
    # reading the wrong field for the vertical distance changes which path runs.  Distances sit exactly on a
    # limit, and terrain gives partial moves so that one dispatch and a repeated one report different values.
    sweep_rng = random.Random(0xB0DA)
    walls = make_grid(2)
    grids = (make_grid(0), make_grid(1), walls, make_grid(3), make_grid(4), make_grid(6), make_grid(5), make_grid(7))
    n = 0
    for kind in "AABBCCDDEEFF":
        for state in (1, 2, 5, 3, 4, 8):
            if sweep_rng.random() < 0.45:
                continue
            gi = sweep_rng.randrange(len(grids))
            ax = sweep_rng.choice([29, 44, 52, 66, 81, 100])
            ay = sweep_rng.choice([37, 58, 73, 90, 101])
            sx = sweep_rng.choice([-1, 1])
            sy = sweep_rng.choice([-1, 1])
            if kind == "A":      # x on the limit, y inside
                tx, ty = ax + sx * limit_x, ay + sweep_rng.choice([0, 5, -5]) * sy
            elif kind == "B":    # y on the limit, x inside
                tx, ty = ax + sweep_rng.choice([0, 3, -3]) * sx, ay + sy * limit_y
            elif kind == "C":    # both on the limit
                tx, ty = ax + sx * limit_x, ay + sy * limit_y
            elif kind == "D":    # far in y, but |object x - target y| is small
                ty = ay + sy * sweep_rng.choice([30, 45, 60])
                ax = ty + sweep_rng.choice([-3, 2, 6])
                tx = ax + sweep_rng.choice([0, 4, -4])
            elif kind == "E":    # y inside the limit, but |object x - target y| is large
                ty = ay + sy * sweep_rng.choice([3, 9, 11])
                ax = ty + sx * sweep_rng.choice([40, 70])
                tx = ax + sweep_rng.choice([0, 4, -4])
            else:                # one past each limit
                tx, ty = ax + sx * (limit_x + 1), ay + sy * sweep_rng.choice([0, limit_y + 1])
            actor = {"x": ax, "y": ay, "state": state, "flags": 0, "sx": 3, "sy": 3}
            flags = sweep_rng.choice([0, 0, 1, 2, 3])
            yield call(f"boundary dispatch {kind} state {state} #{n}", DISPATCH,
                       world(grids[gi], actor, (limit_x, limit_y), None), tx, ty, flags)
            n += 1
    for function in (STEP, MOVE_H):
        for state in (1, 2, 5, 3, 4, 6, 7, 8):
            if function == MOVE_H and state in (3, 7):
                continue
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, -1), (8, 12), (-8, -12), (9, 13)):
                actor = {"x": 40, "y": 50, "state": state, "flags": 0, "sx": 2, "sy": 2}
                yield call(f"boundary {function:#x} state {state} d {dx},{dy}", function,
                           world(make_grid(0 if dx >= 0 else 1), actor, (limit_x, limit_y), None), 40 + dx, 50 + dy, 0)


    # repeated stepping with a zero horizontal limit: the target x differs from the target y, so a second pass
    # that reads the saved target x from the outer entry frame instead of the y argument gives another result
    n = 0
    for state in (1, 2, 5):
        for grid_index, (tx, ty, vlimit) in enumerate(((40, 90, 8), (40, 75, 8), (20, 100, 5), (45, 120, 12))):
            actor = {"x": 60, "y": 60, "state": state, "flags": 0, "sx": 3, "sy": 3}
            yield call(f"zero h-limit repeat state {state} #{n}", DISPATCH,
                       world(make_grid(grid_index % 2), actor, (0, vlimit), None), tx, ty, 0)
            n += 1

    # state 8 rising into a ceiling: the step lands the object in state 4 and the dispatch restores state 8
    ceiling = [[1 if r == 8 else 0 for _ in range(COLS)] for r in range(ROWS)]
    for n, (ty, x, flags, state) in enumerate(((70, 60, 0, 8), (68, 61, 0, 8), (71, 59, 1, 8), (66, 64, 2, 8),
                                               (70, 60, 0, 3), (68, 61, 0, 3), (66, 64, 2, 3))):
        actor = {"x": x, "y": 100, "state": state, "flags": 0, "sx": 3, "sy": 3}
        yield call(f"step state {state} ceiling #{n}", STEP, world(ceiling, actor, (8, 40), None), x, ty, flags)


    # return value of the dispatcher (EAX = the last 0x4cbcd0 result) on every exit path.  The actor flag
    # 0x400000 makes 0x4cbcd0 always report 0x100000, so the expected value is never zero.
    open_grid = make_grid(0)
    floor_grid = make_grid(1)                      # solid floor from row 11 (y >= 88)
    wall_grid = make_grid(2)                       # walls in columns 4 and 11, floor from row 13
    roof_grid = [[1 if r == 8 else 0 for _ in range(COLS)] for r in range(ROWS)]
    n = 0
    for bits, pflags in ((0x400000, 0), (0x400001, 9)):
        if True:
            base = {"x": 60, "y": 60, "flags": bits, "sx": 3, "sy": 3}
            # early dispatch: target inside both step limits
            for state in (1, 3, 8):
                yield call(f"return early state {state} #{n}", DISPATCH,
                           world(open_grid, dict(base, state=state), (8, 8), None), 63, 58, pflags)
                n += 1
            # actor flag 0x10 (bit 0x200000 in the result): far target
            yield call(f"return flag 0x10 #{n}", DISPATCH,
                       world(open_grid, dict(base, state=1, flags=bits | 0x10), (8, 8), None), 120, 20, pflags)
            n += 1
            # state 7 copies the target
            yield call(f"return state 7 #{n}", DISPATCH,
                       world(open_grid, dict(base, state=7), (8, 8), None), 20, 110, pflags)
            n += 1
            # stepping all the way to the target
            for state, tx, ty in ((1, 100, 85), (2, 20, 40), (5, 75, 120)):
                yield call(f"return arrival state {state} #{n}", DISPATCH,
                           world(open_grid, dict(base, state=state), (8, 8), None), tx, ty, pflags)
                n += 1
            # blocked by a wall: the step makes no progress (0x400000) or collides (0x10000)
            for state, tx in ((1, 140), (2, 140), (5, 0)):
                yield call(f"return blocked state {state} #{n}", DISPATCH,
                           world(wall_grid, dict(base, state=state, x=30, y=60), (8, 8), None), tx, 60, pflags)
                n += 1
            # the step loop ends because the state changed: rising into a roof (3 -> 4), falling onto a floor (4 -> 1)
            yield call(f"return state change 3 to 4 #{n}", DISPATCH,
                       world(roof_grid, dict(base, state=3, y=100), (8, 8), None), 60, 30, pflags)
            n += 1
            yield call(f"return state change 4 to 1 #{n}", DISPATCH,
                       world(floor_grid, dict(base, state=4, y=60), (8, 8), None), 60, 130, pflags)
            n += 1
            yield call(f"return state 8 down #{n}", DISPATCH,
                       world(floor_grid, dict(base, state=8, y=60), (8, 8), None), 60, 130, pflags)
            n += 1
            yield call(f"return state 8 up #{n}", DISPATCH,
                       world(roof_grid, dict(base, state=8, y=100), (8, 8), None), 60, 30, pflags)
            n += 1


    # A long vertical move must be stepped, not jumped.  The word after the object's y holds a value close to
    # the target y, so a vertical distance read from the wrong field would pass the early test and tunnel
    # through the one-tile-thick floor or ceiling that the stepped move stops at.
    thin_floor = [[1 if r == 11 else 0 for _ in range(COLS)] for r in range(ROWS)]
    n = 0
    for state, grid, y0, ty, near in ((4, thin_floor, 60, 140, 0), (4, thin_floor, 58, 141, 5), (4, thin_floor, 62, 139, -12),
                                      (8, thin_floor, 60, 140, 3), (8, thin_floor, 55, 138, 12),
                                      (3, roof_grid, 110, 30, 0), (3, roof_grid, 112, 29, -4), (3, roof_grid, 108, 33, 12),
                                      (8, roof_grid, 110, 31, 2), (6, thin_floor, 60, 140, 0), (1, thin_floor, 60, 141, 7)):
        for x0, tx, flags in ((60, 60, 0), (57, 64, 2)):
            actor = {"x": x0, "y": y0, "y54": ty + near, "state": state, "flags": 0, "sx": 3, "sy": 3}
            yield call(f"long vertical move state {state} #{n}", DISPATCH,
                       world(grid, actor, (8, 12), None), tx, ty, flags)
            n += 1


    # Early-dispatch distance tests against huge step limits or the signed wrap.  With ordinary limits a move
    # that sits exactly on a limit gives the same result whether it is dispatched at once or stepped once, so
    # these inputs make the stepped path differ: the first step target is position plus or minus the full limit.
    big = 0x7FFFFFFC
    wrap_cases = (
        # (label, object x, object y, target x, target y, limits)
        ("x axis on limit", 40, 60, 48, 64, (8, big)),
        ("x axis wrap", 0x7FFFFFFF, 60, 0x80000000, 64, (1, 8)),
        ("x axis wrap reverse", 0x80000000, 60, 0x7FFFFFFF, 56, (1, 8)),
        ("y axis on limit", 40, 60, 48, 72, (big, 12)),
        ("y axis wrap", 40, 0x7FFFFFFF, 44, 0x80000000, (8, 1)),
        ("y axis wrap reverse", 40, 0x80000000, 36, 0x7FFFFFFF, (8, 1)),
    )
    n = 0
    for label, ax, ay, tx, ty, limits in wrap_cases:
        for state, flags in ((1, 0), (2, 2), (5, 0)):
            actor = {"x": ax, "y": ay, "state": state, "flags": 0, "sx": 3, "sy": 3}
            yield call(f"huge limit {label} state {state} flags {flags} #{n}", DISPATCH,
                       world(make_grid(0), actor, limits, None), tx, ty, flags)
            n += 1


# Preserve the original generator and its random-source consumption byte for byte.
_cases_before_collision_alias_audit = cases


def collision_manager_actor_alias():
    """Manager limits alias coordinates; the original saves limits before moving."""
    actor = {"x": 96, "y": 87, "state": 1, "flags": 0, "box": (2, 0, 13, 0)}
    base_setup = world(make_grid(1), actor, (96, 87))

    def setup(env):
        tokens = base_setup(env)
        old_manager = tokens["manager"]
        old_actor = tokens["object"]
        # These are guest tokens into one backed slab, never host pointers.
        manager = env.object(0x158, "overlapping-manager-and-actor")
        object_ = manager + 0x18
        tile_table = env.get(old_manager + 0x4C)
        tile_map = env.get(old_manager + 0x5C)
        env.write(manager, env.read(old_manager, 0x80))
        env.write(object_, env.read(old_actor, 0x140))
        env.put(manager + 0x4C, tile_table)
        env.put(manager + 0x5C, tile_map)
        # manager+0x64/+0x68 are now actor+0x4c/+0x50: x=96 and y=87.
        return {"manager": manager, "object": object_}

    return setup


def cases(random_source):
    yield from _cases_before_collision_alias_audit(random_source)
    # At 0x4cbc0f/0x4cbc15 both limits are saved. The first step writes actor x=0,
    # so re-entering the limit-loading entry at the next dispatch would read 0
    # as the horizontal limit instead of continuing with the saved step of 96.
    yield call("collision step limits alias moving actor coordinates", DISPATCH,
               collision_manager_actor_alias(), -96, 87, 0)
