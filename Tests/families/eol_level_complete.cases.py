"""Cases for eol_level_complete: End-of-level level-complete command path.

Coverage is deterministic: every branch is reached by a fixed case.  The random
source only supplies junk bytes around the fields the functions touch, and a few
extra argument values.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

SET_LEVEL_GLOBALS = 0x42AE40
INIT_LINK = 0x45FE20
DELETING_DTOR = 0x462A00
WND_DTOR = 0x462A20
LEVEL_COMPLETE = 0x46AB30
CONTAINER_DTOR = 0x4D2230
ARRAY_DTOR = 0x4D4AB0
RELEASE_GRID = 0x4D5120

G_A, G_B, G_C = 0x537208, 0x53720C, 0x537210
G_D, G_E = 0x5430C8, 0x5430C4
NIL_STRING = 0x52E1C8  # holds the address of the shared empty string header
SLOT_COUNT = 0x544D18  # count of the registration table walked by 0x4dc560
GLOBAL_X = 0x537E88  # tested by 0x46bdb0


def junk(rng, size):
    return bytes(rng.getrandbits(8) for _ in range(size))


def word(rng):
    return rng.getrandbits(32) | 1


def dtor_stub(env, name, log=None):
    """A virtual deleting destructor stand-in: records nothing itself (the harness compares the call), frees the receiver."""
    def effect(env, call):
        env.release(call.receiver)
        return 0
    return env.stub(name, "thiscall", 1, effect)


# ---------------------------------------------------------------- 0x42ae40

def levels_case(label, a, b, c, rng):
    def setup(env):
        for address in (G_A, G_B, G_C, G_D, G_E):
            env.put(address, word(rng))
        return {}
    return Case(label, SET_LEVEL_GLOBALS, setup, arguments=(a, b, c))


# ---------------------------------------------------------------- 0x45fe20

def link_case(label, rng, size=16, fill=None):
    def setup(env):
        data = junk(rng, size) if fill is None else bytes([fill]) * size
        return {"obj": env.object(size, "link", data=data)}
    return Case(label, INIT_LINK, setup, receiver=lambda t: t["obj"])


# ------------------------------------------------- 0x462a20 / 0x462a00

def decrement(env, call):
    """InterlockedDecrement stand-in: the value in the interlocked word is decremented in place."""
    pointer = call.arguments[0]
    value = (env.get(pointer) - 1) & 0xFFFFFFFF
    env.put(pointer, value)
    return value


def string_slot(env, rng, kind):
    """A string member: the shared empty string, a string with one owner, or one with several."""
    if kind == "nil":
        return env.get(NIL_STRING) + 12
    header = env.object(12 + 8, "string", data=junk(rng, 20))
    env.put(header, 1 if kind == "last" else 3, 4, 4)
    return header + 12


def window(rng, capacity=0x20, buffer="object", strings=("nil", "nil"), size=0x320):
    """A window-like object: a registration sub-object at +0x2f4 whose capacity (+8) and buffer (+0xc) decide a free,
    and two empty strings at +0x1a4 and +0x1a8."""
    def setup(env):
        obj = env.object(size, "window", data=junk(rng, size))
        env.override(0x5469E8, decrement)
        env.put(SLOT_COUNT, 0)
        env.put(obj + 0x1A4, string_slot(env, rng, strings[0]))
        env.put(obj + 0x1A8, string_slot(env, rng, strings[1]))
        env.put(obj + 0x2F4 + 8, capacity)
        tokens = {"obj": obj}
        if buffer == "object":
            tokens["buffer"] = env.object(0x40, "buffer", data=junk(rng, 0x40))
            env.put(obj + 0x2F4 + 0xC, tokens["buffer"])
        else:
            env.put(obj + 0x2F4 + 0xC, 0)
        return tokens
    return setup


def cases_window(rng):
    for strings in (("last", "last"), ("shared", "last"), ("last", "shared"), ("nil", "last"), ("last", "nil"),
                    ("shared", "shared")):
        yield Case(f"window dtor strings {strings}", WND_DTOR, window(rng, 0x30, strings=strings),
                   receiver=lambda t: t["obj"])
    yield Case("deleting dtor strings both last", DELETING_DTOR, window(rng, 0x10, strings=("last", "last")),
               receiver=lambda t: t["obj"], arguments=(1,))
    yield Case("deleting dtor strings mixed, no delete", DELETING_DTOR, window(rng, 0x10, strings=("shared", "last")),
               receiver=lambda t: t["obj"], arguments=(2,))
    for capacity in (0, 1, 0x1F, 0x20, 0x21, 0x22, 0x100, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield Case(f"window dtor capacity {capacity:#x}", WND_DTOR, window(rng, capacity), receiver=lambda t: t["obj"])
    yield Case("window dtor big capacity, null buffer", WND_DTOR, window(rng, 0x40, buffer=None), receiver=lambda t: t["obj"])
    for flags in (0, 1, 2, 3, 4, 0x80, 0x100, 0xFE, 0xFF, 0x101, 0xFFFFFFFE, 0xFFFFFFFF):
        yield Case(f"deleting dtor flags {flags:#x}", DELETING_DTOR, window(rng, 0x40), receiver=lambda t: t["obj"],
                   arguments=(flags,))
    for flags in (0, 1):
        for capacity in (0x20, 0x21):
            yield Case(f"deleting dtor flags {flags} capacity {capacity:#x}", DELETING_DTOR, window(rng, capacity),
                       receiver=lambda t: t["obj"], arguments=(flags,))
        yield Case(f"deleting dtor flags {flags} null buffer", DELETING_DTOR, window(rng, 0x80, buffer=None),
                   receiver=lambda t: t["obj"], arguments=(flags,))
    for _ in range(4):
        flags = rng.getrandbits(32)
        capacity = rng.getrandbits(32)
        yield Case(f"deleting dtor random {flags:#x} {capacity:#x}", DELETING_DTOR, window(rng, capacity),
                   receiver=lambda t: t["obj"], arguments=(flags,))


# ---------------------------------------------------------------- 0x46ab30

def level(rng, *, a=False, a_string=True, b=False, c38=False, a9c=False, z_busy=True, global_x=0, depth=24, fade=False, c10=False, fade_global=False, times=(1000, 1100, 1300, 1600)):
    def setup(env):
        nil = env.get(NIL_STRING) + 12
        obj = env.object(0x780, "game", data=junk(rng, 0x780))
        env.put(G_C, word(rng))
        env.put(GLOBAL_X, global_x)
        tokens = {"obj": obj}
        a_obj = 0
        if a:
            a_obj = env.object(0x100, "game-a", data=junk(rng, 0x100))
            env.put(a_obj + 0xC0, nil)
            z = 0
            if a9c:
                z = env.object(0xB0, "game-z", data=junk(rng, 0xB0))
                env.put(z + 0xA0, 1 if z_busy else 0)
                if not z_busy:
                    env.put(z + 4, 0)
                    env.put(z + 8, 0)
            env.put(a_obj + 0x9C, z)
            tokens["a"] = a_obj
        env.put(obj + 4, a_obj)
        env.put(obj + 0x38, 0x77 if c38 else 0)
        env.put(obj + 0x2C, 0)
        if a:
            env.put(a_obj + 0x78, depth)
        if b:
            # b -> +0x10 -> c; c+4 -> d (a palette-like object whose vtable slot 0x10 is a stand-in); c+0xc a 0x400 byte table
            pal_entries = env.stub("Palette::GetEntries", "stdcall", 5, returns(0))
            vtable = env.object(0x40, "palette-vtable", data=junk(rng, 0x40))
            env.put(vtable + 0x10, pal_entries)
            d = env.object(0x20, "palette", data=junk(rng, 0x20))
            env.put(d, vtable)
            c = env.object(0x40, "c", data=junk(rng, 0x40))
            env.put(c + 4, d)
            table = env.object(0x400, "palette-table", data=junk(rng, 0x400))
            env.put(c + 0xC, table)
            bobj = env.object(0x40, "b", data=junk(rng, 0x40))
            env.put(bobj + 0x10, c)
            env.put(obj + 0x2C, bobj)
            tokens.update(b=bobj, c=c, d=d)
            # +0xc -> e (+4 -> f); the surfaces hang off f+0x10 and f+0x14
            surfaces = []
            for n in range(2):
                iface_vtable = env.object(0x80, "surface-vtable", data=junk(rng, 0x80))
                env.put(iface_vtable + 0x2C, env.stub("Surface::SetPalette", "stdcall", 3, returns(0)))
                env.put(iface_vtable + 0x14, env.stub("Surface::Blt", "stdcall", 6, returns(0)))
                iface = env.object(0x20, "surface-interface", data=junk(rng, 0x20))
                env.put(iface, iface_vtable)
                k = env.object(0x60, "surface", data=junk(rng, 0x60))
                env.put(k + 8, iface)
                holder = env.object(0x60, "holder", data=junk(rng, 0x60))
                env.put(holder + 0x2C, k if (n == 0 or fade) else 0)
                surfaces.append(holder)
            f = env.object(0x100, "f", data=junk(rng, 0x100))
            env.put(f + 0x10, surfaces[0])
            env.put(f + 0x14, surfaces[1])
            e = env.object(0x40, "e", data=junk(rng, 0x40))
            env.put(e + 4, f)
            env.put(obj + 0xC, e)
            if fade:
                env.put(vtable + 0x18, env.stub("Palette::SetEntries", "stdcall", 5, returns(0)))
                env.override(0x546DF0, sequence(*times))
                env.put(c + 0x10, env.object(0x400, "palette-copy", data=junk(rng, 0x400)) if c10 else 0)
                gx = 0
                if fade_global:
                    flip_vtable = env.object(0x80, "flip-vtable", data=junk(rng, 0x80))
                    env.put(flip_vtable + 0x58, env.stub("Display::Update", "stdcall", 3, returns(0)))
                    flip_object = env.object(0x10, "flip-object", data=junk(rng, 0x10))
                    env.put(flip_object, flip_vtable)
                    gx = env.object(0x10, "flip-holder", data=junk(rng, 0x10))
                    env.put(gx, flip_object)
                env.put(0x541374, gx)
            tokens["f"] = f
        return tokens
    return setup


def cases_level(rng):
    receiver = lambda t: t["obj"]
    for command in (0, 1, 5, 10, 13, 0xFFFFFFFF, 0x7FFFFFFF, 0x10B, 0x10C):
        yield Case(f"level plain command {command:#x}", LEVEL_COMPLETE, level(rng), receiver=receiver, arguments=(command,))
    yield Case("level a", LEVEL_COMPLETE, level(rng, a=True), receiver=receiver, arguments=(3,))
    yield Case("level a, hook set", LEVEL_COMPLETE, level(rng, a=True, c38=True), receiver=receiver, arguments=(3,))
    yield Case("level a with z busy", LEVEL_COMPLETE, level(rng, a=True, c38=True, a9c=True), receiver=receiver, arguments=(4,))
    yield Case("level a with z idle", LEVEL_COMPLETE, level(rng, a=True, c38=True, a9c=True, z_busy=False),
               receiver=receiver, arguments=(4,))
    fades = [dict(), dict(c10=True), dict(fade_global=True), dict(c10=True, fade_global=True, times=(5, 6, 700)),
             dict(times=(0xFFFFFF00, 0x100, 0x200, 0x300, 0x400))]
    for number, options in enumerate(fades):
        for hooked in (False, True):
            yield Case(f"level fade {number} hook {hooked}", LEVEL_COMPLETE,
                       level(rng, a=True, b=True, fade=True, c38=hooked, a9c=hooked, **options), receiver=receiver,
                       arguments=((0xA, 0xD, 0, 1, 2, 5, 9, 0x10B, 0x10C, 0x1B, 0xB0, 0x20, 0xFFFFFFFF)[(number * 2 + hooked) % 13],))
    for command in (0xB0, 0x20, 0xFFFFFFFF, 0x10B, 0x1C, 0xA, 0xD):
        yield Case(f"level fade command {command:#x}", LEVEL_COMPLETE, level(rng, a=True, b=True, fade=True, c38=True),
                   receiver=receiver, arguments=(command,))
    for command in (0xB, 0xC):
        yield Case(f"level b command {command}", LEVEL_COMPLETE, level(rng, a=True, b=True), receiver=receiver, arguments=(command,))
        yield Case(f"level b command {command} with a and hook", LEVEL_COMPLETE, level(rng, a=True, b=True, c38=True),
                   receiver=receiver, arguments=(command,))


# ---------------------------------------------------------------- grids

def grid(env, rng, objects, vtable, shape=(4, 3), shifts=(2, 2), nodes=()):
    """A cell grid: +0xc stride, +0x14/+0x18 shifts, +0x28..+0x34 rectangle, +0x40 table of 8-byte cells.
    `nodes` is a sequence of (cell index, x, y, has_object); inside the rectangle's cells."""
    columns, rows = shape
    sx, sy = shifts
    x0, y0 = rng.randrange(0, 40), rng.randrange(0, 40)
    x1, y1 = x0 + ((columns - 1) << sx) + 1, y0 + ((rows - 1) << sy) + 1
    stride = columns + 1
    table = env.object((rows * stride + columns + 2) * 8, "cells", data=junk(rng, (rows * stride + columns + 2) * 8))
    for index in range((rows * stride + columns + 2)):
        env.put(table + index * 8, 0)
    g = env.object(0x60, "grid", data=junk(rng, 0x60))
    env.put(g, vtable)
    env.put(g + 0xC, stride)
    env.put(g + 0x14, sx)
    env.put(g + 0x18, sy)
    env.put(g + 0x28, x0, y0, x1, y1)
    env.put(g + 0x40, table)
    heads = {}
    for index, x, y, with_object in nodes:
        node = env.object(0x28, "node", data=junk(rng, 0x28))
        target = 0
        if with_object:
            target = env.object(0x20, "tenant", data=junk(rng, 0x20))
            env.put(target, objects)
        env.put(node, heads.get(index, 0))
        env.put(node + 0x10, x if x is not None else x0, y if y is not None else y0, target)
        heads[index] = node
        env.put(table + index * 8, node)
    return g, (x0, y0, x1, y1)


def grid_setup(rng, node_plan, shape=(4, 3), shifts=(2, 2)):
    def setup(env):
        tenant_vtable = env.object(8, "tenant-vtable")
        env.put(tenant_vtable + 4, dtor_stub(env, "Tenant::delete"))
        grid_vtable = env.object(8, "grid-vtable")
        env.put(grid_vtable + 4, dtor_stub(env, "Grid::delete"))
        g, rect = grid(env, rng, tenant_vtable, grid_vtable, shape, shifts, node_plan)
        return {"grid": g, "rect": rect}
    return setup


def cases_grid(rng):
    receiver_free = lambda t: 0
    plans = {
        "empty": [],
        "one node cell 0": [(0, None, None, True)],
        "node without tenant": [(0, None, None, False)],
        "two nodes one cell": [(0, None, None, True), (0, None, None, True)],
        "nodes spread over cells": [(0, None, None, True), (1, None, None, True), (3, None, None, False),
                                    (5, None, None, True), (7, None, None, True)],
        "last cell": [(11, None, None, True)],
        "chain of three with gaps": [(2, None, None, True), (2, None, None, False), (2, None, None, True),
                                     (6, None, None, True)],
    }
    for name, plan in plans.items():
        yield Case(f"grid {name}", RELEASE_GRID, grid_setup(rng, plan), arguments=(lambda t: t["grid"],))
    for name, shape, shifts in (("1x1", (1, 1), (0, 0)), ("1 wide", (1, 4), (3, 1)), ("1 high", (5, 1), (1, 3)),
                                ("wide cells", (3, 3), (5, 4)), ("unit cells", (6, 2), (0, 0))):
        stride = shape[0] + 1
        plan = [(0, None, None, True), ((shape[1] - 1) * stride, None, None, True),
                (shape[1] * 0 + shape[0] - 1, None, None, True)]
        yield Case(f"grid shape {name}", RELEASE_GRID, grid_setup(rng, plan, shape, shifts),
                   arguments=(lambda t: t["grid"],))
    for _ in range(3):
        shape = (rng.randrange(1, 6), rng.randrange(1, 5))
        cells = shape[0] * (shape[0] + 1) + shape[0]
        plan = [(rng.randrange(0, shape[0]), None, None, rng.randrange(0, 4) != 0) for _ in range(rng.randrange(0, 6))]
        yield Case(f"grid random {shape}", RELEASE_GRID, grid_setup(rng, plan, shape, (rng.randrange(0, 4), rng.randrange(0, 4))),
                   arguments=(lambda t: t["grid"],))


# ---------------------------------------------------------------- 0x4d2230

def container(rng, children=(), extra20=False, extra24=False, owner=True, sub=False, shapes=None):
    """children: which of the three grids (+4, +8, +0xc) of the owned container exist; each gets nodes."""
    def setup(env):
        nil_vtable = env.object(8, "tenant-vtable")
        env.put(nil_vtable + 4, dtor_stub(env, "Tenant::delete"))
        grid_vtable = env.object(8, "grid-vtable")
        env.put(grid_vtable + 4, dtor_stub(env, "Grid::delete"))
        obj = env.object(0x140, "container", data=junk(rng, 0x140))
        tokens = {"obj": obj}
        env.put(obj + 0xB0, 0)
        if owner:
            q = env.object(0x20, "owner", data=junk(rng, 0x20))
            env.put(obj + 0xB0, q)
            tokens["owner"] = q
            for slot in (4, 8, 0xC):
                env.put(q + slot, 0)
            for number, slot in enumerate((4, 8, 0xC)):
                if slot in children:
                    plan = [(number + i * 2, None, None, i % 3 != 2) for i in range(number + 1)]
                    g, _ = grid(env, rng, nil_vtable, grid_vtable, (4, 3), (2, 2), plan)
                    env.put(q + slot, g)
        env.put(obj + 0x20, env.object(0x10, "a", data=junk(rng, 0x10)) if extra20 else 0)
        env.put(obj + 0x24, env.object(0x10, "b", data=junk(rng, 0x10)) if extra24 else 0)
        env.put(obj + 0xA0, env.object(0x10, "sub", data=junk(rng, 0x10)) if sub else 0)
        return tokens
    return setup


def cases_container(rng):
    receiver = lambda t: t["obj"]
    yield Case("container no owner", CONTAINER_DTOR, container(rng, owner=False), receiver=receiver)
    yield Case("container no owner, all extras", CONTAINER_DTOR, container(rng, owner=False, extra20=True, extra24=True, sub=True),
               receiver=receiver)
    yield Case("container owner without children", CONTAINER_DTOR, container(rng), receiver=receiver)
    for mask in range(1, 8):
        kids = tuple(slot for bit, slot in enumerate((4, 8, 0xC)) if mask >> bit & 1)
        yield Case(f"container children {kids}", CONTAINER_DTOR, container(rng, kids), receiver=receiver)
    yield Case("container extra 0x20 only", CONTAINER_DTOR, container(rng, (4, 8, 0xC), extra20=True), receiver=receiver)
    yield Case("container extra 0x24 only", CONTAINER_DTOR, container(rng, (4, 8, 0xC), extra24=True), receiver=receiver)
    yield Case("container sub only", CONTAINER_DTOR, container(rng, (4, 8, 0xC), sub=True), receiver=receiver)
    yield Case("container extras both", CONTAINER_DTOR, container(rng, (8,), extra20=True, extra24=True), receiver=receiver)
    yield Case("container everything", CONTAINER_DTOR, container(rng, (4, 8, 0xC), True, True, True, True), receiver=receiver)


# ---------------------------------------------------------------- 0x4d4ab0

def array_holder(rng, present, count=None):
    def setup(env):
        obj = env.object(0x60, "holder", data=junk(rng, 0x60))
        tokens = {"obj": obj}
        env.put(obj + 4, 0)
        env.put(obj + 0x40, 0)
        if present:
            env.put(obj + 4, word(rng))
        if count is not None:
            block = env.object(4 + 8 * count + 4, "array", data=junk(rng, 4 + 8 * count + 4))
            env.put(block, count)
            env.put(obj + 0x40, block + 4)
            tokens["block"] = block
        return tokens
    return setup


def cases_array(rng):
    receiver = lambda t: t["obj"]
    yield Case("array holder empty link", ARRAY_DTOR, array_holder(rng, False), receiver=receiver)
    yield Case("array holder empty link with array", ARRAY_DTOR, array_holder(rng, False, 2), receiver=receiver)
    yield Case("array holder link no array", ARRAY_DTOR, array_holder(rng, True), receiver=receiver)
    for count in (0, 1, 2, 5):
        yield Case(f"array holder link array of {count}", ARRAY_DTOR, array_holder(rng, True, count), receiver=receiver)


def cases(random_source):
    rng = random_source
    for i, (a, b, c) in enumerate(((1, 2, 3), (0, 0, 0), (0xFFFFFFFF, 0x80000000, 0x7FFFFFFF), (5, 0, 9), (0, 7, 0),
                                   (0, 0, 8), (0x11111111, 0x22222222, 0x33333333))):
        yield levels_case(f"levels {i}", a, b, c, rng)
    for i in range(4):
        yield levels_case(f"levels random {i}", word(rng), word(rng), word(rng), rng)
    yield link_case("link zero", rng, fill=0)
    yield link_case("link ones", rng, fill=0xFF)
    for i in range(3):
        yield link_case(f"link junk {i}", rng, size=32)
    yield from cases_window(rng)
    yield from cases_level(rng)
    yield from cases_grid(rng)
    yield from cases_container(rng)
    yield from cases_array(rng)
