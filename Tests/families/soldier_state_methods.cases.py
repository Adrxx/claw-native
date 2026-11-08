"""Cases for soldier_state_methods: Soldier state dispatch and idle behaviour.

0x48b0c0 looks a state id up in a table of handlers (global record at 0x53c328), growing the table
through 0x4db6e0 when the id is out of range, and falls back to 0x44c840 when no handler is set.
0x48b730 is the idle behaviour: an animation pick on a timer, a line-of-sight test against the player
and a random chance of changing direction.

Every case that reaches rand supplies its sequence. Coverage of every branch is enumerated, so it does
not depend on the random seed; the random source only varies the surrounding values.
"""
from clawparity.cases import Case
from clawparity.fixtures import reallocate, returns, sequence

DISPATCH = 0x48B0C0
IDLE = 0x48B730
RAND = 0x4A3050
REALLOC = 0x4A9070

M32 = 0xFFFFFFFF
TICK = 0x537210            # millisecond clock
PLAYER = 0x537E88          # pointer to the player object
FLAG_26B7 = 0x534EAC
FLAG_RAND = 0x541334
ANIM_STEP = 0x5430C4

# Handler table record of the dispatcher (0x53c328) and of the fallback in 0x44c840 (0x537878).
MAIN = 0x53C328
FALLBACK = 0x537878
RECORDS = {
    MAIN: dict(err=0x53C32C, lo=0x53C330, hi=0x53C334, base=0x53C338, default=0x53C33C, size=0x53C340,
               fresh=0x53C344, grown=0x53C348),
    FALLBACK: dict(err=0x53787C, lo=0x537880, hi=0x537884, base=0x537888, default=0x53788C, size=0x537890,
                   fresh=0x537894, grown=0x537898),
}


def u32(value):
    return value & M32


# ---------------------------------------------------------------------------------------------
# Dispatcher (0x48b0c0)
# ---------------------------------------------------------------------------------------------

def handler(env, name, result):
    return env.stub(name, "thiscall", 0, returns(result))


def error_object(env, mode, word=0x1234):
    """The object that 0x4db4d0 reports to. Mode 4 and 1 store the halfword; 0 does nothing; 2 calls a stub."""
    error = env.object(0x40, "error-sink", fill=0x3C)
    env.put(error + 0x08, word)
    env.put(error + 0x0C, mode)
    if mode == 2:
        env.put(error, env.stub("error-callback", "cdecl", 2, returns(0)))
        env.put(error + 0x14, env.object(16, "error-prefix", data=b"sink: state\0 pad"))
    return error


def build_table(env, record, lo, hi, slots, size=4, extra=0, default=None, mode=4, tag="s", seed=0):
    """Fill one handler record. `slots` lists the handler of each id lo..hi (0 for no handler)."""
    names = RECORDS[record]
    count = hi - lo + 1
    assert len(slots) == count
    array = env.object(max(4, (count + extra) * size), "handlers", fill=0x6B)
    for index, entry in enumerate(slots):
        env.put(array + index * size, entry)
        for pad in range(4, size, 4):
            env.put(array + index * size + pad, 0x70000000 + seed * 16 + index * 4 + pad)
    for index in range(count, count + extra):
        env.put(array + index * size, handler(env, f"{tag}-extra{index}", 0x900 + index))
    slot = env.object(8, "default-slot", words=[default or 0, 0x44445555])
    env.put(record, 0x51000000 + record)
    env.put(names["err"], error_object(env, mode))
    env.put(names["lo"], u32(lo))
    env.put(names["hi"], u32(hi))
    env.put(names["base"], array)
    env.put(names["default"], slot)
    env.put(names["size"], size)
    env.put(names["fresh"], 0xABCD0001)
    env.put(names["grown"], 0x00C0FFEE)
    env.put(0x544B4C, 0x00533428)
    return array


def dispatcher(label, setup, state, **options):
    return Case(label, DISPATCH, setup, receiver=lambda tokens: tokens["receiver"],
                arguments=(u32(state),), **options)


def standard_for(lo, hi, state, filled, **options):
    """Like `standard`, with the fallback record widened so that the dispatched id is also in range there."""
    options = dict(options)
    fallback = options.get("fallback", "handler")
    fb_size = options.get("fb_size", 4)
    realloc = options.get("realloc")
    fail = options.get("fail", False)
    size = options.get("size", 4)
    extra = options.get("extra", 0)
    default = options.get("default", False)
    mode = options.get("mode", 4)
    preset = options.get("preset_grown")
    fb_fail = options.get("fallback_in_range", True)

    def setup(env):
        slots = []
        names = {}
        for identifier in range(lo, hi + 1):
            if filled(identifier):
                names[identifier] = handler(env, f"state{identifier}", 0x100 + (identifier & 0xFF))
                slots.append(names[identifier])
            else:
                slots.append(0)
        default_handler = handler(env, "default-state", 0x777) if default else None
        build_table(env, MAIN, lo, hi, slots, size=size, extra=extra, default=default_handler, mode=mode, seed=1)
        if preset is not None:
            env.put(RECORDS[MAIN]["grown"], preset)
        fb_lo = (min(lo, state) if fb_fail else lo) - 1
        fb_hi = (max(hi, state) if fb_fail else hi) + 1
        fb_slots = []
        for identifier in range(fb_lo, fb_hi + 1):
            if fallback == "handler" and (identifier & 1) == (state & 1):
                fb_slots.append(handler(env, f"fallback{identifier}", 0x200 + (identifier & 0xFF)))
            elif fallback == "handler" and identifier == state:
                fb_slots.append(handler(env, "fallback-state", 0x2FF))
            else:
                fb_slots.append(0)
        fb_default = handler(env, "fallback-default", 0x888) if fallback == "handler" else None
        build_table(env, FALLBACK, fb_lo, fb_hi, fb_slots, size=fb_size, default=fb_default, tag="f", seed=2)
        override = realloc(env, names) if realloc else reallocate(fail=fail)
        env.override(REALLOC, override)
        return {"receiver": env.object(0x900, "soldier", fill=0x21), "handlers": names}
    return setup


def always(_identifier):
    return True


def never(_identifier):
    return False


def even(identifier):
    return identifier % 2 == 0


def realloc_then_zero_size(env, names):
    """Grow normally, then zero the element size behind 0x4db6e0's back so the grown slot 0 is read."""
    base = reallocate()

    def effect(env, call):
        result = base(env, call)
        if result:
            env.put(RECORDS[MAIN]["size"], 0)
        return result
    return effect


def regrow(env, call):
    """The second growth: a smaller copy of the old array, so the zero element size is harmless."""
    pointer = call.arguments[0]
    moved = env.object(32, "regrown")
    env.write(moved, env.read(pointer, min(env.spans[pointer], 32)))
    env.release(pointer)
    return moved


def cascade_up(env, names):
    """Upward growth zeroes the element size and moves the lower bound above the id; the second growth fixes it."""
    base = reallocate()

    def effect(env, call):
        if env.calls_so_far(call.function) > 1:
            return regrow(env, call)
        result = base(env, call)
        env.put(RECORDS[MAIN]["size"], 0)
        env.put(RECORDS[MAIN]["lo"], 0x7FFF0000)
        return result
    return effect


def cascade_down(env, names):
    """Downward growth zeroes the element size and moves the upper bound below the id."""
    base = reallocate()

    def effect(env, call):
        if env.calls_so_far(call.function) > 1:
            return regrow(env, call)
        result = base(env, call)
        env.put(RECORDS[MAIN]["size"], 0)
        env.put(RECORDS[MAIN]["hi"], 0x80010000)
        return result
    return effect


IN_RANGE_TABLES = [(0, 7), (5, 12), (-3, 4), (100, 104), (0, 0), (-8, -2), (-2, 2)]


def dispatcher_cases(random_source):
    # Ids inside the table: first, last, middle, with and without a handler in the slot.
    for lo, hi in IN_RANGE_TABLES:
        for state in sorted({lo, hi, (lo + hi) // 2, lo + 1 if hi > lo else lo}):
            yield dispatcher(f"in range {lo}..{hi} id {state} handler", standard_for(lo, hi, state, always),
                             state)
            yield dispatcher(f"in range {lo}..{hi} id {state} no handler", standard_for(lo, hi, state, never),
                             state)
        yield dispatcher(f"in range {lo}..{hi} alternating", standard_for(lo, hi, hi, even), hi)
    # Element sizes: the slot is at (id - lo) * size, and only its first word is the handler.
    for size in (4, 8, 12, 16):
        for state in (3, 4, 5, 9):
            yield dispatcher(f"element size {size} id {state}", standard_for(3, 9, state, lambda i: i != 4, size=size),
                             state)
    # Out of range, growth succeeds, the new slot is empty: the fallback runs.
    for lo, hi in ((0, 7), (-3, 4), (100, 104)):
        for delta in (1, 2, 9):
            above, below = hi + delta, lo - delta
            yield dispatcher(f"grow up {lo}..{hi} to {above}", standard_for(lo, hi, above, always), above)
            yield dispatcher(f"grow down {lo}..{hi} to {below}", standard_for(lo, hi, below, always), below)
    for size in (8, 12):
        yield dispatcher(f"grow up element size {size}", standard_for(2, 6, 11, always, size=size), 11)
        yield dispatcher(f"grow down element size {size}", standard_for(2, 6, -4, always, size=size), -4)
    # Growth succeeds but the element size is zeroed during the allocation: the old slot 0 is dispatched.
    for lo, hi in ((0, 7), (-3, 4), (100, 104)):
        for state in (hi + 1, hi + 6, lo - 1, lo - 5):
            yield dispatcher(f"grown then dispatch slot 0 {lo}..{hi} id {state}",
                             standard_for(lo, hi, state, always, realloc=realloc_then_zero_size), state)
    yield dispatcher("grown then empty slot 0 falls back",
                     standard_for(0, 7, 9, never, realloc=realloc_then_zero_size), 9)
    # The allocation changes the bounds as well as the element size, so the second range test fails and a
    # second growth runs; it then dispatches the old slot 0.
    for lo, hi in ((0, 7), (-3, 4), (100, 104)):
        for state in (hi + 2, hi + 9):
            yield dispatcher(f"second growth after upward growth {lo}..{hi} id {state}",
                             standard_for(lo, hi, state, always, realloc=cascade_up), state)
        for state in (lo - 2, lo - 9):
            yield dispatcher(f"second growth after downward growth {lo}..{hi} id {state}",
                             standard_for(lo, hi, state, always, realloc=cascade_down), state)
    # The grown counter is cleared on every entry, and again before the second lookup.
    for preset in (0, 1, 0xFFFFFFFF, 0x12345678):
        yield dispatcher(f"counter preset {preset:#x} in range", standard_for(0, 7, 3, always, preset_grown=preset), 3)
        yield dispatcher(f"counter preset {preset:#x} grown", standard_for(0, 7, 20, always, preset_grown=preset), 20)
    # Random tables.
    for _ in range(40):
        lo = random_source.randrange(-20, 20)
        hi = lo + random_source.randrange(0, 12)
        size = random_source.choice((4, 4, 8, 12))
        pattern = random_source.getrandbits(16)
        state = random_source.randrange(lo - 6, hi + 7)

        def filled(identifier, pattern=pattern, lo=lo):
            return bool((pattern >> ((identifier - lo) % 16)) & 1)
        fail = False
        default = random_source.random() < 0.5
        fallback = "handler"
        realloc = None
        if state > hi and random_source.random() < 0.3:
            realloc = realloc_then_zero_size
        elif state > hi and random_source.random() < 0.3:
            realloc = cascade_up
        elif state < lo and random_source.random() < 0.3:
            realloc = cascade_down
        yield dispatcher(f"random {lo}..{hi} size {size} id {state} fail {fail} default {default}",
                         standard_for(lo, hi, state, filled, size=size, fail=fail, default=default,
                                      fallback=fallback, realloc=realloc), state)


# ---------------------------------------------------------------------------------------------
# Idle behaviour (0x48b730)
# ---------------------------------------------------------------------------------------------

def tile_effect(result, mutate=None):
    def effect(env, call):
        if mutate:
            mutate(env)
        return result
    return effect


def tile_threshold(env, call):
    return 1 if call.arguments[0] >= 8 else 0


def build_map(env, cells, default_cell, mutate=None, width=256, height=192, row_bias=0):
    """A tile map (4cda10's `this`): 16 x 12 cells of 16 pixels. Cell values index four tile objects."""
    objects = []
    behaviours = [tile_effect(0, mutate), tile_effect(1, mutate), tile_effect(2, mutate), tile_threshold]
    for index, effect in enumerate(behaviours):
        table = env.object(0x30, f"tile-vtable{index}", fill=0x5D)
        env.put(table + 0x20, env.stub(f"tile{index}", "thiscall", 2, effect))
        objects.append(env.object(8, f"tile{index}", words=[table, 0x7000 + index]))
    tiles = env.object(16, "tile-table", words=objects)
    columns, rows = 16, 12
    data = env.object((columns * rows + row_bias) * 4, "cells", fill=0x91)
    row_table = env.object(rows * 4, "row-offsets")
    for row in range(rows):
        env.put(row_table + row * 4, row * columns + row_bias)
        for column in range(columns):
            value = cells.get((column, row), default_cell)
            env.put(data + (row * columns + column + row_bias) * 4, value)
    plane = env.object(0x98, "plane", fill=0x4E)
    env.put(plane + 0x20, data, row_table)
    env.put(plane + 0x30, width, height)
    env.put(plane + 0x8C, 4, 4)
    tilemap = env.object(0x60, "tile-map", fill=0x33)
    env.put(tilemap + 0x4C, tiles)
    env.put(tilemap + 0x5C, plane)
    return tilemap


EMPTY_CELLS = (0xEEEEEEEE, 0xFFFFFFFF)


def make_animation(env, tag, kind, flags, mode, tail, null=False, seed=0):
    """An animation resource for 0x4c8220 and 0x4c82a0 that stays on their simple paths."""
    if null:
        return 0
    frame = env.object(0x40, f"{tag}-frame", fill=0x2A)
    env.put(frame + 0x04, flags)
    env.put(frame + 0x08, mode)
    env.put(frame + 0x0C, tail)
    env.put(frame + 0x10, kind)
    env.put(frame + 0x18, 0x30 + seed)
    env.put(frame + 0x1C, 0xA0000 + seed)
    env.put(frame + 0x20, 11 + seed, 23 + seed)
    env.put(frame + 0x2C, 0)
    frames = env.object(8, f"{tag}-frames", words=[frame, 0])
    resource = env.object(0x30, f"{tag}-resource", fill=0x1F)
    env.put(resource + 0x0C, frames)
    env.put(resource + 0x10, 1)
    return resource


def idle_world(now=1000, last1=1000, interval1=500, last2=1000, interval2=500, rands=(0, 0),
               flag_26b7=0, flag_rand=0, anim_step=0x31, kinds=(1, 3), tails=(9, 6), anim_null=(False, False),
               frame_flags=(0, 5), ahead=None, wx=120, wy=96, gx=200, gy=96, w38=7, map_cells=None,
               map_default=0, mutate=None, bits=0x4, bits_big=False, count=3, previous=0x1357, bias=0,
               q_flags=0, step_fixture=None, overlap=False):
    def setup(env):
        env.put(TICK, now)
        env.put(FLAG_26B7, 0x26B7 if flag_26b7 == 1 else (flag_26b7 or 0))
        env.put(FLAG_RAND, flag_rand)
        env.put(ANIM_STEP, anim_step)
        if rands is not None:
            env.override(RAND, sequence(*rands))
        else:
            env.override(RAND, returns(0))
        if overlap:
            # the entity sits 0x5c bytes below the soldier, so the animation's +8 word is the soldier's +0x134
            block = env.object(0x5C + 0x480, "soldier-and-entity", fill=0x66)
            soldier = block + 0x5C
        else:
            soldier = env.object(0x480, "soldier", fill=0x66)
        vtable = env.object(0x60, "soldier-vtable", fill=0x58)
        vcall44 = env.stub("soldier-method44", "thiscall", 0, returns(0x44))
        vcall48 = env.stub("soldier-method48", "thiscall", 0, returns(0x48))
        env.put(vtable + 0x44, vcall44)
        env.put(vtable + 0x48, vcall48)
        env.put(soldier, vtable)
        # animation target
        entity = block if overlap else env.object(0x1D0, "entity", fill=0x44)
        queue = env.object(0x180, "anim-owner", fill=0x39)
        env.put(queue + 0x40, q_flags)
        env.put(queue + 0x4C, 1000, 2000)
        env.put(entity + 0x18C, queue)
        env.put(entity + 0x190, previous)
        env.put(entity + 0x188 + 0x14, 5)
        env.put(soldier + 0x12C, entity)
        env.put(soldier + 0x318, make_animation(env, "pick0", kinds[0], frame_flags[0], 0, tails[0],
                                                anim_null[0], seed=1))
        env.put(soldier + 0x31C, make_animation(env, "pick1", kinds[1], frame_flags[1], 0, tails[1],
                                                anim_null[1], seed=2))
        # timers
        env.put(soldier + 0x464, u32(last1))
        env.put(soldier + 0x468, u32(interval1))
        env.put(soldier + 0x474, u32(last2))
        env.put(soldier + 0x478, u32(interval2))
        # proximity chain
        refs = {}
        tilemap = build_map(env, map_cells or {}, map_default, mutate=(lambda env: mutate(env, refs)) if mutate else None, row_bias=bias)
        v = env.object(0x30, "level-part", fill=0x2B)
        env.put(v + 0x24, tilemap)
        u = env.object(0x20, "level", fill=0x2C)
        env.put(u + 0x0C, v)
        env.put(soldier + 0x190, u)
        player = env.object(0x60, "player", fill=0x12)
        env.put(player + 0x4C, u32(gx), u32(gy))
        env.put(PLAYER, player)
        body = env.object(0x60, "body", fill=0x13)
        env.put(body + 0x4C, u32(wx), u32(wy))
        env.put(body + 0x38, u32(w38))
        env.put(soldier + 0x194, body)
        # 0x44edd0: bit 2 of the flag word leads to virtual method 0x48
        env.put(soldier + 0x2FC, count)
        if count > 0x20:
            bits_object = env.object(8, "flag-words", words=[bits, 0])
            env.put(soldier + 0x300, bits_object)
        else:
            env.put(soldier + 0x300, bits)
        refs.update(soldier=soldier, player=player, body=body)
        return {"soldier": soldier, "entity": entity, "player": player, "body": body}
    return setup


def idle(label, setup):
    return Case(label, IDLE, setup, receiver=lambda tokens: tokens["soldier"])


RAND_PICKS = (0, 1, 2, 3, 4, 0x7FFF, 0x7FFE, 0xFFFFFFFF, 0xFFFFFFFE, 0x80000000, 0x80000001, 0xFFFFFFFD)

TIMER_EDGES = (
    # label, now, last, interval
    ("one short", 1000, 400, 601),
    ("exact", 1000, 400, 600),
    ("one over", 1000, 400, 599),
    ("zero interval", 1000, 1000, 0),
    ("clock behind", 1000, 1500, 100),
    ("wrap exact", 5, 0xFFFFFFFB, 10),
    ("wrap short", 5, 0xFFFFFFFB, 11),
    ("reset interval", 70000, 1000, 1000),
)

LINE_OF_SIGHT_NEUTRAL = dict(flag_26b7=1)


def idle_cases(random_source):
    # First timer: due or not, each possible pick, both animation resources present or one missing.
    for name, now, last, interval in TIMER_EDGES:
        for pick in (0, 1, 0xFFFFFFFF):
            yield idle(f"pick timer {name} rand {pick:#x}",
                       idle_world(now=now, last1=last, interval1=interval, rands=(pick,), **LINE_OF_SIGHT_NEUTRAL))
    for pick in RAND_PICKS:
        yield idle(f"pick rand {pick:#x}", idle_world(now=1000, last1=0, interval1=10, rands=(pick,),
                                                     **LINE_OF_SIGHT_NEUTRAL))
        yield idle(f"pick rand {pick:#x} animation missing",
                   idle_world(now=1000, last1=0, interval1=10, rands=(pick,), anim_null=(True, True),
                              **LINE_OF_SIGHT_NEUTRAL))
        yield idle(f"pick rand {pick:#x} first missing",
                   idle_world(now=1000, last1=0, interval1=10, rands=(pick,), anim_null=(True, False),
                              **LINE_OF_SIGHT_NEUTRAL))
        yield idle(f"pick rand {pick:#x} second missing",
                   idle_world(now=1000, last1=0, interval1=10, rands=(pick,), anim_null=(False, True),
                              **LINE_OF_SIGHT_NEUTRAL))
    # The animation's +8 word is the soldier's +0x134: the old value must be saved before it is replaced.
    for pick in (0, 1):
        for previous in (0x1357, 0xFFFFFFFF, 0):
            for null in (False, True):
                yield idle(f"saved word overlaps animation pick {pick} previous {previous:#x} null {null}",
                           idle_world(now=1000, last1=0, interval1=10, rands=(pick,), previous=previous,
                                      overlap=True, anim_null=(null, null), **LINE_OF_SIGHT_NEUTRAL))
    # Animation resource shapes the original callees walk.
    for kind in (0, 1, 2, 3, 4):
        for tail in (9, 6):
            for flags in (0, 5):
                yield idle(f"animation kind {kind} tail {tail:#x} flags {flags}",
                           idle_world(now=1000, last1=0, interval1=10, rands=(1,), kinds=(kind, kind),
                                      tails=(tail, tail), frame_flags=(flags, flags), q_flags=flags,
                                      **LINE_OF_SIGHT_NEUTRAL))
    for previous in (0, 0x1357, 0xFFFFFFFF):
        yield idle(f"previous animation word {previous:#x}",
                   idle_world(now=1000, last1=0, interval1=10, rands=(0,), previous=previous,
                              **LINE_OF_SIGHT_NEUTRAL))
    for step in (0, 1, 0x31, 0xFFFFFFFF):
        yield idle(f"animation step {step:#x}", idle_world(now=1000, last1=0, interval1=10, rands=(1,),
                                                          anim_step=step, **LINE_OF_SIGHT_NEUTRAL))

    # Line of sight: the player's position against the soldier, in range and out of range.
    base = dict(now=1000, last1=1000, interval1=500, last2=1000, interval2=500, rands=(0,))
    for dy in (-0x34, -0x33, -0x32, -0x31, -1, 0, 1, 0x31, 0x32, 0x33, 0x34):
        for w38 in (-1, 0, 5):
            yield idle(f"proximity dy {dy} body field {w38}",
                       idle_world(**base, wx=120, wy=96, gx=200, gy=96 + dy, w38=w38))
    for wy, gy in ((-100, -70), (-100, -150), (-100, -50), (0x7FFFFFC0, 0x7FFFFFD0), (0x7FFFFFCD, 0x7FFFFFFF)):
        yield idle(f"proximity wide {wy:#x} {gy:#x}", idle_world(**base, wy=wy, gy=gy, gx=200, wx=120))
    # Horizontal sweeps: ascending, descending, equal, partly outside the map.
    for wx, gx in ((120, 200), (200, 120), (150, 150), (-50, 100), (100, -50), (-80, -20), (-20, -80),
                   (250, 400), (400, 250), (0, 255), (255, 0), (16, 48), (48, 16), (0, 0), (255, 255)):
        for cells_name in ("open", "empty", "block_all"):
            cells = {}
            default = {"open": 0, "empty": 0xEEEEEEEE, "block_all": 1}[cells_name]
            yield idle(f"sweep {wx}->{gx} map {cells_name}",
                       idle_world(**base, wx=wx, gx=gx, wy=96, gy=100, map_cells=cells, map_default=default))
    # Blockers in one cell of the row: the first, a middle one and the last sample.
    for wx, gx in ((16, 120), (120, 16), (20, 100), (100, 20), (-30, 90), (90, 300)):
        row = 6
        columns = sorted({max(0, min(15, x >> 4)) for x in range(wx, gx + 1, 8)} |
                         {max(0, min(15, x >> 4)) for x in range(gx, wx + 1, 8)})
        for column in (columns[0], columns[-1]):
            for value in (1, 3, 0x00120001, 0xEEEEEEEE):
                yield idle(f"blocker col {column} value {value:#x} sweep {wx}->{gx}",
                           idle_world(**base, wx=wx, gx=gx, wy=96, gy=100, map_cells={(column, row): value}))
    for bias in (0, 3):
        yield idle(f"row offsets biased {bias}", idle_world(**base, map_cells={(7, 6): 1}, bias=bias,
                                                           wx=40, gx=190, wy=96, gy=100))
    yield idle("tile threshold passes", idle_world(**base, map_cells={(5, 6): 3}, wx=40, gx=190, wy=96, gy=100))
    # The flag 0x26b7 suppresses the check altogether.
    for flag in (1, 0x26B7, 0x26B6, 0x126B7):
        yield idle(f"check flag {flag:#x}", idle_world(**{**base, "flag_26b7": flag}, wx=120, gx=200, wy=96, gy=100))
    # Things a tile callback changes after 0x4cda10 sampled the position.
    def set_field(owner, offset, value):
        return lambda env, refs: env.put(refs[owner] + offset, value)
    sweep = dict(wx=40, gx=190, wy=96, gy=100, map_cells={(7, 6): 0})
    for value in (96 + 0x31, 96 + 0x32, 96 - 0x32, 96 - 0x31, 5):
        yield idle(f"callback sets player y {value:#x}", idle_world(**base, **sweep, mutate=set_field("player", 0x50, value)))
    for value in (96 + 0x33, 96 - 0x20):
        yield idle(f"callback sets body y {value:#x}", idle_world(**base, **sweep, mutate=set_field("body", 0x50, value)))
    for value in (0xFFFFFFFF, 0, 4):
        yield idle(f"callback sets body field {value:#x}",
                   idle_world(**base, **sweep, w38=3 if value == 0xFFFFFFFF else 0xFFFFFFFF,
                              mutate=set_field("body", 0x38, value)))
    yield idle("callback advances the clock past timer", idle_world(
        now=1000, last1=1000, interval1=500, last2=900, interval2=200, rands=(0, 0), wx=40, gx=190, wy=96,
        gy=250, map_cells={(7, 6): 0}, mutate=lambda env, refs: env.put(TICK, 1100)))
    yield idle("callback rewinds the clock before timer", idle_world(
        now=1000, last1=1000, interval1=500, last2=500, interval2=400, rands=(0, 0), wx=40, gx=190, wy=96,
        gy=250, map_cells={(7, 6): 0}, mutate=lambda env, refs: env.put(TICK, 800)))
    yield idle("callback changes the second interval", idle_world(
        now=1000, last1=1000, interval1=500, last2=500, interval2=400, rands=(0, 0), wx=40, gx=190, wy=96,
        gy=250, map_cells={(7, 6): 0}, mutate=lambda env, refs: env.put(refs["soldier"] + 0x478, 900)))

    # Second timer and the rand chance, with the line of sight not met.
    for name, now, last, interval in TIMER_EDGES:
        for roll in (0, 4):
            yield idle(f"turn timer {name} roll {roll}",
                       idle_world(now=now, last1=now, interval1=1 << 30, last2=last, interval2=interval,
                                  rands=(roll,), flag_26b7=1))
    for roll in (0, 1, 3, 4, 5, 6, 99, 100, 104, 105, 0x7FFF, 0x7FFE, 0xFFFFFFFF, 0xFFFFFFFB, 0xFFFFFFFA,
                 0x80000000, 0x80000001, 0x7FFFFFFF):
        yield idle(f"turn roll {roll:#x}",
                   idle_world(now=1000, last1=1000, interval1=500, last2=0, interval2=10, rands=(roll,), flag_26b7=1))
        yield idle(f"turn roll {roll:#x} chosen after pick",
                   idle_world(now=1000, last1=0, interval1=10, last2=0, interval2=10, rands=(roll ^ 1, roll),
                              flag_26b7=1))
    for flag in (1, 2, 0x100, 0xFFFFFFFF):
        yield idle(f"turn blocked by flag {flag:#x}",
                   idle_world(now=1000, last1=1000, interval1=500, last2=0, interval2=10, rands=(0,), flag_26b7=1,
                              flag_rand=flag))
    # Direction change shapes: flag bit 2 present or not, small and large flag words.
    for count, bits, big in ((3, 4, False), (5, 0xF4, False), (0x20, 4, False), (0x21, 4, True), (0x40, 0xFF, True),
                             (7, 0x1C, False)):
        yield idle(f"turn flags count {count} bits {bits:#x}",
                   idle_world(now=1000, last1=1000, interval1=500, last2=0, interval2=10, rands=(0,), flag_26b7=1,
                              count=count, bits=bits, bits_big=big))
    # Line of sight is met: the soldier acts and the turn timer is not consulted.
    for wx, gx in ((40, 190), (190, 40)):
        yield idle(f"sighted {wx}->{gx} ignores turn timer",
                   idle_world(now=1000, last1=1000, interval1=500, last2=0, interval2=10, rands=(0,), wx=wx,
                              gx=gx, wy=96, gy=100))
        yield idle(f"sighted {wx}->{gx} after pick",
                   idle_world(now=1000, last1=0, interval1=10, last2=0, interval2=10, rands=(1, 0), wx=wx,
                              gx=gx, wy=96, gy=100))
    # Random draws around the same model.
    for _ in range(60):
        now = random_source.randrange(0, 5000)
        last1 = random_source.randrange(0, 5000)
        last2 = random_source.randrange(0, 5000)
        wx, gx = random_source.randrange(-60, 330), random_source.randrange(-60, 330)
        wy = random_source.randrange(0, 192)
        gy = wy + random_source.randrange(-0x40, 0x41)
        cells = {}
        for _cell in range(random_source.randrange(0, 5)):
            cells[(random_source.randrange(0, 16), wy // 16)] = random_source.choice((1, 2, 3, 0x40001, 0xEEEEEEEE))
        yield idle(f"random now {now} {last1} {last2} x {wx}->{gx} y {wy}/{gy}",
                   idle_world(now=now, last1=last1, interval1=random_source.randrange(0, 3000),
                              last2=last2, interval2=random_source.randrange(0, 3000),
                              rands=(random_source.getrandbits(32), random_source.getrandbits(32)),
                              flag_26b7=random_source.choice((0, 0, 1)),
                              flag_rand=random_source.choice((0, 0, 3)),
                              wx=wx, gx=gx, wy=wy, gy=gy, w38=random_source.choice((-1, 0, 9)),
                              map_cells=cells, kinds=(random_source.randrange(0, 4), random_source.randrange(0, 4)),
                              frame_flags=(random_source.randrange(0, 8), random_source.randrange(0, 8)),
                              anim_null=(random_source.random() < 0.15, random_source.random() < 0.15),
                              previous=random_source.getrandbits(32)))


def cases(random_source):
    yield from dispatcher_cases(random_source)
    yield from idle_cases(random_source)
