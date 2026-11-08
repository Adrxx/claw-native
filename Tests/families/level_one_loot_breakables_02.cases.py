"""Cases for level_one_loot_breakables_02: Level 1 loot and breakables, batch 2."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns  # noqa: F401

M32 = 0xFFFFFFFF
OPERATOR_NEW = 0x4F63EC
MALLOC = 0x4A48E0
SET_RECT = 0x546D5C          # import slot read by 0x46f2a0: stdcall (rect, left, top, right, bottom)
SET_RECT_EMPTY = 0x546CDC    # import slot read by the base constructor: stdcall (rect)
G_TICKS = 0x537210
G_STEP = 0x5430C4
G_TREE = 0x537668
G_KEG_FLAG = 0x52A194
BIG_STRING = 0x534938
ACTOR_INIT_SLOT = 0x5137F0 + 0x28     # vtable written by the actor factory 0x4c8be0
SOUND_VTABLE_PLAY = 0x513740 + 0x24   # vtable of the 0x174 byte member allocated by 0x4c7f20
KEG_VTABLE_SLOT = 0x50EDD4 + 0x10
CRATE_VTABLE_SLOT = 0x50F824 + 0x10

TABLE_MAIN = dict(lo=0x537EA8, hi=0x537EAC, base=0x537EB0, fallback=0x537EB4, stride=0x537EB8, flag=0x537EC0,
                  error=0x537EA4, address=0x537EA0)
TABLE_SECOND = dict(lo=0x537640, hi=0x537644, base=0x537648, fallback=0x53764C, stride=0x537650, flag=0x537658,
                    error=0x53763C, address=0x537638)


def words_of(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


def observe(env, log, tag, call, with_receiver=False, extra=()):
    """Append one row to a case log: the call a stand-in saw, as surviving case memory."""
    count = env.get(log)
    env.put(log, count + 1)
    row = log + 4 + count * 40
    words = [tag, call.receiver if with_receiver else 0] + list(call.arguments)[:6] + list(extra)
    env.put(row, *words[:10])
    return 0


def new_log(env):
    return env.object(0x2000, "case-log", fill=0)


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def make_registry(env, random_source, entries, buckets):
    """The string table behind 0x4f6286, embedded at owner+0x10: +4 buckets, +8 count, nodes [next, ?, key, value].
    Every key also gets a decoy node with a near-miss key so a wrong string compare finds the wrong value."""
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


def make_resource(env, random_source, first, last, extra=4):
    """A frame set: +0x14 frame pointer table indexed by absolute frame number, +0x64 first, +0x68 last, +0x10 a word."""
    count = max(first, last, 0) + 1 + extra
    frames = [env.object(0x40, "frame", words=words_of(random_source, 0x10)) for _ in range(count)]
    table = env.object(4 * count, "frame-table", words=frames)
    resource = env.object(0x80, "resource", words=words_of(random_source, 0x20))
    env.put(resource + 0x14, table)
    env.put(resource + 0x64, first, last)
    return resource


def make_tilemap(env, random_source, width, height, shift_x, shift_y, classify, log=None):
    """Tile map: +0x4c tile objects (vtable +0x20 returns the tile class), +0x5c plane with cells and row offsets."""
    columns = (width + (1 << shift_x) - 1) >> shift_x
    rows = (height + (1 << shift_y) - 1) >> shift_y
    tiles = []
    for tile_class in range(4):
        vtable = env.object(0x40, "tile-vtable")
        if log is None:
            effect = returns(tile_class)
        else:
            effect = lambda e, c, tile_class=tile_class: observe(e, log, 0x70 + tile_class, c, True) or tile_class
        env.put(vtable + 0x20, env.stub(f"tile-class-{tile_class}", "thiscall", 2, effect))
        tile = env.object(8, "tile-object")
        env.put(tile, vtable)
        tiles.append(tile)
    table = env.object(16, "tile-table", words=tiles)
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
    env.put(tmap + 0x64, random_source.randrange(0, 100), random_source.randrange(0, 100))
    return tmap


def random_classifier(random_source, rows=4, columns=4, weights=(None, 0, 0, 1, 2, 3)):
    grid = {(cx, cy): random_source.choice(weights) for cx in range(columns) for cy in range(rows)}
    return lambda cx, cy: grid.get((cx, cy))


def install_tree(env, random_source, mode, key):
    """The tree behind 0x4dba00(&0x537668, key); the root pointer lives at 0x537680."""
    if mode == "empty":
        env.put(G_TREE + 0x18, 0)
        return 0
    value = random_source.randrange(1, 1 << 32)
    stored = {"mismatch": key[:-1] + b"X\0", "short": key[:3] + b"\0", "long": key + b"2\0"}.get(mode, key + b"\0")
    keyobj = env.object(16, "tree-key", data=stored)
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
    env.put(G_TREE + 0x18, root)
    return value


# ----------------------------------------------------------------------------------------------
# 0x434170 and 0x434180: tail jumps through the receiver's vtable
def thunk_cases(r):
    for function, slot, other in ((0x434170, 0xB0, 0xAC), (0x434180, 0xAC, 0xB0)):
        for index in range(6):
            def setup(env, slot=slot, other=other, index=index):
                log = new_log(env)
                vtable = env.object(0x100, "thunk-vtable", words=words_of(r, 0x40))
                obj = env.object(0x30, "thunk-object", words=words_of(r, 12))
                wanted = r.randrange(1, M32)
                env.put(vtable + slot, env.stub("wanted-slot", "thiscall", 0, lambda e, c: observe(e, log, slot, c, True) or wanted))
                env.put(vtable + other, env.stub("other-slot", "thiscall", 0, lambda e, c: observe(e, log, other, c, True) or 7))
                env.put(obj, vtable)
                return {"obj": obj}
            yield Case(f"vtable thunk {function:#x} {index}", function, setup, receiver=lambda t: t["obj"])


# ----------------------------------------------------------------------------------------------
# 0x48de40
def crate_item_cases(r):
    for value in (0x20, 0x1F, 0x21, 0, 0x2000, M32, 0x120, 0x20):
        for _ in range(2):
            def setup(env, value=value):
                owner_actor = env.object(0x160, "crate-owner-actor", words=words_of(r, 0x58))
                owner = env.object(0x50, "crate-logic", words=words_of(r, 0x14))
                env.put(owner + 0x0C, owner_actor)
                service = env.object(0x174, "crate-item-service", words=words_of(r, 0x5D))
                item = env.object(0x1B4, "crate-item", words=words_of(r, 0x6D))
                env.put(item + 0x6C, service)
                env.put(item + 0x100, value)
                return {"logic": owner, "item": item}
            yield Case(f"crate item {value:#x}", 0x48DE40, setup, receiver=lambda t: t["logic"], arguments=(lambda t: t["item"],))


# ----------------------------------------------------------------------------------------------
# 0x46f6a0 and the dispatch tables behind it (0x4db6e0, 0x43d490)
def fill_table(env, r, g, lo, hi, stride, handlers, fallback, error_mode=3, base_null=False):
    """handlers: stand-in addresses (or 0) for lo..hi."""
    count = max(hi - lo + 1, 0) if hi < (1 << 31) else 0
    size = max(count * stride, 4) + 4
    area = 0 if base_null else env.object(size, "dispatch-entries", words=words_of(r, size // 4))
    for index, handler in enumerate(handlers):
        env.put(area + index * stride, handler)
    entry = env.object(8, "dispatch-fallback", words=[fallback, r.randrange(1, M32)])
    error = env.object(0x20, "dispatch-error-sink", words=words_of(r, 8))
    env.put(error + 0x0C, error_mode)
    env.put(g["lo"], lo & M32)
    env.put(g["hi"], hi & M32)
    env.put(g["base"], area)
    env.put(g["fallback"], entry)
    env.put(g["stride"], stride)
    env.put(g["flag"], r.randrange(1, M32))
    env.put(g["error"], error)
    return area


def dispatch_setup(r, identifier, *, main="hit", second="hit", fail_from=None, error_mode=3, fallback_main=True):
    """main: hit | zero | grow-up | grow-down | fail.  second: hit (the handler runs from the second table)."""
    def setup(env):
        log = new_log(env)
        receiver = env.object(0x20, "dispatch-receiver", words=words_of(r, 8))
        stride = r.choice((4, 8, 12, 16))
        handler = env.stub("dispatch-handler", "thiscall", 0, lambda e, c: observe(e, log, 1, c, True) or 0x111)
        second_handler = env.stub("second-handler", "thiscall", 0, lambda e, c: observe(e, log, 2, c, True) or 0x222)
        fallback_handler = env.stub("fallback-handler", "thiscall", 0, lambda e, c: observe(e, log, 3, c, True) or 0x333) if fallback_main else 0
        if main == "hit":
            lo = identifier - r.randrange(0, 4)
            hi = identifier + r.randrange(0, 4)
            handlers = [env.stub(f"entry-{n}", "thiscall", 0, lambda e, c, n=n: observe(e, log, 10 + n, c, True) or 0x400 + n)
                        if lo + n != identifier else handler for n in range(hi - lo + 1)]
            fill_table(env, r, TABLE_MAIN, lo, hi, stride, handlers, fallback_handler, error_mode)
        elif main == "zero":
            lo = identifier - r.randrange(0, 3)
            hi = identifier + r.randrange(0, 3)
            handlers = [0 if lo + n == identifier else env.stub(f"other-{n}", "thiscall", 0, returns(n)) for n in range(hi - lo + 1)]
            fill_table(env, r, TABLE_MAIN, lo, hi, stride, handlers, fallback_handler, error_mode)
        elif main == "grow-up":
            fill_table(env, r, TABLE_MAIN, 0 if identifier >= 0 else identifier, -1, stride, [], fallback_handler, error_mode, base_null=True)
        elif main == "grow-down":
            lo = identifier + r.randrange(1, 4)
            fill_table(env, r, TABLE_MAIN, lo, lo - 1, stride, [], fallback_handler, error_mode, base_null=True)
        else:  # fail: the table cannot grow; an empty table, no storage
            fill_table(env, r, TABLE_MAIN, 0, -1, stride, [], fallback_handler, error_mode, base_null=True)
        lo2 = identifier - r.randrange(0, 3)
        hi2 = identifier + r.randrange(0, 3)
        handlers2 = [second_handler if lo2 + n == identifier else env.stub(f"second-other-{n}", "thiscall", 0, returns(n)) for n in range(hi2 - lo2 + 1)]
        fill_table(env, r, TABLE_SECOND, lo2, hi2, r.choice((4, 8, 12)), handlers2, 0, 3)
        if main in ("grow-up", "grow-down", "fail") or fail_from is not None:
            env.override(MALLOC, allocate(fail_from_call=fail_from if fail_from is not None else 10 ** 9))
        return {"this": receiver, "log": log}
    return setup


def dispatch_cases(r):
    for identifier in (0, 1, 7, 100, 300, r.randrange(2, 90), r.randrange(100, 900)):
        for main in ("hit", "zero"):
            yield Case(f"dispatch {main} id {identifier}", 0x46F6A0, dispatch_setup(r, identifier, main=main),
                       receiver=lambda t: t["this"], arguments=(identifier,))
    for identifier in (0, 3, 40, r.randrange(1, 200)):
        yield Case(f"dispatch grows upward id {identifier}", 0x46F6A0, dispatch_setup(r, identifier, main="grow-up"),
                   receiver=lambda t: t["this"], arguments=(identifier,))
    for identifier in (-1, 2, r.randrange(-20, 5)):
        yield Case(f"dispatch grows downward id {identifier}", 0x46F6A0, dispatch_setup(r, identifier, main="grow-down"),
                   receiver=lambda t: t["this"], arguments=(identifier & M32,))


# ----------------------------------------------------------------------------------------------
# 0x471530, 0x471720, 0x471750: the crate/keg state machine
def sm_setup(r, state, *, res=None, p170=True, found=True, p70="object", s10_special=False, p64=0, p10c=0,
             p174="frame", anim="none", s130=0, step=3, s64=0, late=None):
    def setup(env):
        log = new_log(env)
        resource = make_resource(env, r, *res) if res is not None else 0
        key = env.cstr(0x5228DC)
        registry = make_registry(env, r, {key: make_resource(env, r, 0, 2)} if found else {}, r.choice((3, 5, 7)))
        world = env.object(0x40, "world", words=words_of(r, 0x10))
        env.put(world + 0x14, registry)
        service = env.object(0x180, "service", words=words_of(r, 0x60))
        actor = env.object(0x1C0, "actor", words=words_of(r, 0x70))
        env.put(actor + 0x0C, world)
        env.put(actor + 0x6C, service)
        env.put(actor + 0x170, resource if p170 else 0)
        frame = env.object(0x40, "current-frame", words=words_of(r, 0x10))
        env.put(actor + 0x174, frame if p174 == "frame" else 0)
        replacement = env.object(0x40, "replacement-frame", words=words_of(r, 0x10))
        late_values = (replacement if late == "frame" else 0, r.choice((0x3E7, 0x3E6, 0, 5)), r.choice((0, 9, 0x31)),
                       0x99 if s10_special else 0x471720)

        def voice_effect(e, c, tag):
            observe(e, log, tag, c, True)
            if late:
                e.put(actor + 0x174, late_values[0])
                e.put(actor + 0x10C, late_values[1])
                e.put(actor + 0x64, late_values[2])
                e.put(service + 0x10, late_values[3])
            return 6
        voice_vtable = env.object(0x80, "voice-vtable", words=words_of(r, 0x20))
        env.put(voice_vtable + 0x1C, env.stub("voice-query", "thiscall", 0, lambda e, c: observe(e, log, 0x1C, c, True) or 5))
        env.put(voice_vtable + 0x24, env.stub("voice-play", "thiscall", 2, lambda e, c: voice_effect(e, c, 0x24)))
        if p70 == "object":
            voice = env.object(0x20, "voice", words=words_of(r, 8))
            env.put(voice, voice_vtable)
            env.put(actor + 0x70, voice)
        else:
            env.put(actor + 0x70, 0)
            env.put(SOUND_VTABLE_PLAY, env.stub("new-voice-play", "thiscall", 2, lambda e, c: voice_effect(e, c, 0x25)))
        env.put(actor + 0x64, p64)
        env.put(actor + 0x10C, p10c & M32)
        env.put(service + 0x1C, state)
        env.put(service + 0x10, 0x471720 if s10_special else r.choice((0x471750, 0, 0x12345678)))
        env.put(service + 0x130, s130)
        env.put(service + 0x64, s64)
        env.put(G_STEP, step, r.randrange(1, M32))
        base = actor + 0x188
        if anim == "none":
            env.put(base + 8, 0)
        elif anim == "pending-hold":
            env.put(base + 8, r.randrange(1, M32))
            env.put(base + 0x14, 9)
            env.put(base + 0x18, 0)
        elif anim == "pending-slow":
            env.put(base + 8, r.randrange(1, M32))
            env.put(base + 0x14, step + 5)
            env.put(base + 0x18, 1)
        elif anim == "pending-done":
            env.put(base + 8, r.randrange(1, M32))
            env.put(base + 0x14, max(step, 1))
            env.put(base + 0x18, 1)
        elif anim == "finished":
            env.put(base + 8, r.randrange(1, M32))
            env.put(base + 0x14, 0)
        env.put(base + 0x1C, r.choice((0, 1, 7)) if anim in ("pending-hold", "pending-slow", "none") else r.randrange(1, M32))
        env.put(base + 0x20, r.randrange(1, M32))
        env.put(base + 0x24, r.randrange(1, M32))
        return {"actor": actor, "service": service, "log": log}
    return setup


def sm_cases(r):
    def case(function, label, **options):
        state = options.pop("state")
        return Case(f"{label} {function:#x} state {state:#x}", function, sm_setup(r, state, **options),
                    receiver=0, arguments=(lambda t: t["actor"],))

    for p170 in (True, False):
        for res in ((0, 5), (3, 9), (4, 2), (7, 7)):
            for found in (True, False):
                for s10 in (False, True):
                    for p64 in (0, 0x77):
                        if r.random() < 0.55:
                            continue
                        yield case(0x471530, f"enter p170={p170} res={res} found={found} s10={s10} p64={p64}", state=0,
                                   p170=p170, res=res, found=found, s10_special=s10, p64=p64,
                                   p10c=r.choice((0, 1, 2, 0x3E6, 0x3E7, 0x3E8, M32, -9)), p70=r.choice(("object", "new")),
                                   p174=r.choice(("frame", "none")))
    for p10c in (0, 1, 2, 3, 0x3E6, 0x3E7, 0x3E8, 0x7FFFFFFF, 0x80000000, M32):
        for s10 in (False, True):
            yield case(0x471530, f"counter {p10c:#x} s10={s10}", state=0, res=(1, 4), s10_special=s10, p10c=p10c)
    for p70 in ("object", "new"):
        yield case(0x471530, f"voice {p70}", state=0, res=(0, 3), p70=p70)
        for late in ("frame", "zero"):
            for s10 in (False, True):
                yield case(0x471530, f"changed by the voice {late} {p70} s10={s10}", state=0, res=(1, 5), p70=p70, late=late,
                           s10_special=s10, p64=r.choice((0, 3)), p10c=r.choice((0, 2)))
    for s130 in (0, 1, 5, 20, 0x7FFFFFFF, M32):
        for step in (0, 1, 5, 20, 0x80000000):
            if r.random() < 0.5:
                continue
            yield case(0x471530, f"wait s130={s130:#x} step={step:#x}", state=5, s130=s130, step=step)
    for s64 in (0, 1, 0x55AA):
        yield case(0x471530, f"settle s64={s64}", state=10, s64=s64)
    for anim in ("none", "pending-hold", "pending-slow", "pending-done", "finished"):
        for step in (1, 3, 11):
            yield case(0x471530, f"animate {anim} step={step}", state=31, anim=anim, step=step)
    for state in (1, 2, 3, 4, 6, 7, 9, 11, 30, 32, 33, 0x100, 0x3E8, M32, 0x80000000, 0x20, 0x1F):
        yield case(0x471530, "other", state=state, s64=r.randrange(0, M32))
    for function in (0x471720, 0x471750):
        for state in (0, 5, 10, 31, 4, 40, 0x400):
            def setup(env, state=state):
                tokens = sm_setup(r, state, res=(r.randrange(0, 3), r.randrange(3, 8)), s130=r.choice((0, 9)),
                                  anim=r.choice(("none", "finished", "pending-hold")), p10c=r.choice((0, 5)))(env)
                env.put(G_KEG_FLAG, r.randrange(0, M32))
                env.put(tokens["service"] + 0x64, r.randrange(0, 3))
                return tokens
            yield Case(f"start {function:#x} state {state:#x}", function, setup, arguments=(lambda t: t["actor"],))


# ----------------------------------------------------------------------------------------------
# the keg logic constructor 0x46f2a0 and its creator 0x46f1e0
def install_rect_imports(env, r, log, delta=0, special_left=False, late=None):
    """late: what the fourth SetRect call changes behind the constructor's back: size / word of the bit set, or a
    replacement actor for the +0x12c slot."""
    def set_rect(env, call):
        rect = call.arguments[0]
        number = env.calls_so_far(call.function)
        values = [(v + delta) & M32 for v in call.arguments[1:5]]
        if special_left and number == 3:
            values[0] = 0x80000000
        env.put(rect, *values)
        observe(env, log, 0x50, call, False)
        if late and number == 4:
            logic = rect - 0x260
            if "size" in late:
                env.put(logic + 0x2FC, late["size"])
                env.put(logic + 0x300, late["word"])
            if "actor" in late:
                env.put(logic + 0x12C, late["actor"])
        return 1
    env.put(SET_RECT, env.stub("SetRect", "stdcall", 5, set_rect))

    def set_empty(env, call):
        n = env.calls_so_far(call.function) * 0x1010
        env.put(call.arguments[0], n + 1, n + 2, n + 3, n + 4)
        observe(env, log, 0x51, call, False)
        return 1
    env.put(SET_RECT_EMPTY, env.stub("SetRectEmpty", "stdcall", 1, set_empty))


LIFT_KEYS = (0x52A15C, 0x52A144, 0x52A12C, 0x52A114)
CTOR_KEYS = (0x5266EC, 0x524870, 0x524864, 0x524858, 0x52484C, 0x5266DC)


def keg_world(env, r, *, res=(0, 12), lifts=(True, True, True, True), game_null=True, kegboom=True, ctor_names=None,
              hooks=False, info_zero=(), depth=1, big_string=None, malloc_fail=None, rect_delta=0, special_left=False,
              classify=None, tree="match", pos=None, state_before=None, voice=False, size=0x460, late=None):
    log = new_log(env)
    resource = make_resource(env, r, *res) if res is not None else 0
    map_width, map_height = 4 << 5, 4 << 5
    tmap = make_tilemap(env, r, map_width, map_height, 5, 5, classify or random_classifier(r), log)
    entries2c = {}
    for present, address in zip(lifts, LIFT_KEYS):
        if present:
            entries2c[env.cstr(address)] = r.randrange(1, M32)
    if game_null:
        entries2c[env.cstr(0x5234B4)] = r.randrange(1, M32)
    entries28 = {}
    names = CTOR_KEYS if ctor_names is None else [CTOR_KEYS[i] for i in ctor_names]
    for address in names:
        entries28[env.cstr(address)] = r.randrange(1, M32)
    if kegboom:
        entries28[env.cstr(0x52A104)] = r.randrange(1, M32)
    entries14 = {}
    if hooks:
        entries14[env.cstr(0x522D54)] = make_resource(env, r, 0, 3)
        entries14[env.cstr(0x522D48)] = make_resource(env, r, 0, 3)
    world = env.object(0x40, "world", words=words_of(r, 0x10))
    env.put(world + 0x10, make_registry(env, r, {env.cstr(0x52A174): resource} if resource else {}, r.choice((3, 5, 7))))
    env.put(world + 0x14, make_registry(env, r, entries14, r.choice((3, 5))))
    env.put(world + 0x24, tmap)
    env.put(world + 0x28, make_registry(env, r, entries28, r.choice((5, 7))))
    env.put(world + 0x2C, make_registry(env, r, entries2c, r.choice((3, 5, 7))))
    info = env.object(0x180, "info", words=words_of(r, 0x60))
    for offset in info_zero:
        env.put(info + offset, 0)
    env.put(info + 0x64, depth & M32)
    if pos is None:
        pos = (r.randrange(-20, 150), r.randrange(-60, 110))
    # the constructor places the actor from these four numbers (as doubles); they must stay small
    env.put(info + 0x2C, r.randrange(-50, 300) & M32)
    env.put(info + 0x30, pos[0] & M32)
    env.put(info + 0x34, r.randrange(-50, 300) & M32)
    env.put(info + 0x38, pos[1] & M32)
    for offset in info_zero:
        env.put(info + offset, 0)
    if state_before is not None:
        env.put(info + 0x1C, state_before)
    actor = env.object(0x1C0, "actor", words=words_of(r, 0x70))
    env.put(actor + 0x0C, world)
    env.put(actor + 0x6C, info)
    env.put(actor + 0x08, r.randrange(0, 1 << 32) & ~0x10)
    env.put(actor + 0x40, r.randrange(0, 1 << 32) & ~2)
    env.put(actor + 0x70, 0)
    env.put(actor + 0x78, 0)
    env.put(actor + 0x16C, 0)
    env.put(actor + 0x170, 0)
    env.put(actor + 0x174, 0)
    env.put(actor + 0x118, 5, 6, 7, 8)
    env.put(actor + 0x4C, pos[0] & M32, pos[1] & M32)
    env.put(actor + 0x148, pos[0] & M32, pos[1] & M32)
    if hooks:
        env.put(SOUND_VTABLE_PLAY, env.stub("new-voice-play", "thiscall", 2, lambda e, c: observe(e, log, 0x25, c, True) or 6))
    env.put(G_TICKS, r.randrange(1, 1 << 30))
    if big_string is not None:
        env.write(BIG_STRING, big_string + b"\0")
    late_effects = None
    if late == "swap-actor":
        other = env.object(0x1C0, "second-actor", words=words_of(r, 0x70))
        env.put(other + 0x0C, world)
        env.put(other + 0x6C, info)
        for offset in (0x16C, 0x170, 0x174, 0x70, 0x78):
            env.put(other + offset, 0)
        env.put(other + 0x118, 9, 10, 11, 12)
        env.put(other + 0x4C, pos[0] & M32, pos[1] & M32)
        env.put(other + 0x08, r.randrange(0, 1 << 32) & ~0x10)
        late_effects = {"actor": other}
    elif late is not None:
        size_late, word_late = late
        if size_late > 0x20:
            buffer = env.object(4 * ((size_late + 31) // 32) + 8, "late-bits", words=words_of(r, (4 * ((size_late + 31) // 32) + 8) // 4))
            word_late = buffer
        late_effects = {"size": size_late, "word": word_late}
    install_rect_imports(env, r, log, rect_delta, special_left, late_effects)
    install_tree(env, r, tree, b"LS_IDLE")
    if malloc_fail is not None:
        env.override(MALLOC, allocate(fail_from_call=malloc_fail))
    logic = env.object(size, "keg-logic", words=words_of(r, size // 4))
    return {"L": logic, "P": actor, "S": info, "log": log, "world": world}


def keg_setup(r, **options):
    return lambda env: keg_world(env, r, **options)


def keg_cases(r):
    pick = r.choice
    yield Case("keg all present", 0x46F2A0, keg_setup(r), receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for mask in range(16):
        lifts = tuple(bool(mask >> bit & 1) for bit in range(4))
        for game_null in (True, False):
            if r.random() < 0.45:
                continue
            yield Case(f"keg lifts {mask:#x} null={game_null}", 0x46F2A0,
                       keg_setup(r, lifts=lifts, game_null=game_null, kegboom=pick((True, False)),
                                 res=pick(((0, 12), (9, 12), (10, 12), (0, 8), (2, 9), (9, 9), (4, 1)))),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for res in (None, (0, 12), (0, 9), (0, 8), (9, 20), (10, 3), (5, 9), (9, 9), (6, 7), (12, 4)):
        for kegboom in (True, False):
            yield Case(f"keg resource {res} kegboom={kegboom}", 0x46F2A0, keg_setup(r, res=res, kegboom=kegboom),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for string in (None, b"40", b"3, 40", b"1-3 40", b"5-9", b"33", b"3-70", b"2"):
        for depth in (1, 0, -2):
            yield Case(f"keg bit string {string!r} depth {depth}", 0x46F2A0,
                       keg_setup(r, big_string=string, depth=depth), receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for fail in (2, 3, 4):
        yield Case(f"keg allocation fails from call {fail}", 0x46F2A0,
                   keg_setup(r, big_string=pick((None, b"40")), malloc_fail=fail), receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for zeros in ((), (0x2C,), (0x34,), (0x30,), (0x38,), (0x2C, 0x34, 0x30, 0x38), (0x2C, 0x38), (0x34, 0x30)):
        yield Case(f"keg info zero {[hex(z) for z in zeros]}", 0x46F2A0, keg_setup(r, info_zero=zeros),
                   receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for tree in ("empty", "mismatch", "short", "long", "null", "deep", "far", "match"):
        yield Case(f"keg pacing tree {tree}", 0x46F2A0, keg_setup(r, tree=tree, state_before=pick((0, 0x3E8, r.randrange(1, M32)))),
                   receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for special in (False, True):
        for delta in (0, 2, -3):
            yield Case(f"keg rects delta {delta} special left {special}", 0x46F2A0, keg_setup(r, rect_delta=delta, special_left=special),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for shape in ("all-open", "floor-at-once", "floor-later", "ceiling-stop", "solid-slope", "everything-solid", "mixed"):
        def classifier(shape=shape):
            if shape == "all-open":
                return lambda cx, cy: 0
            if shape == "floor-at-once":
                return lambda cx, cy: 1
            if shape == "floor-later":
                return lambda cx, cy: 0 if cy < 2 else 1
            if shape == "ceiling-stop":
                return lambda cx, cy: 0 if cy < 1 else 2
            if shape == "solid-slope":
                return lambda cx, cy: 0 if cy < 2 else 3
            if shape == "everything-solid":
                return lambda cx, cy: 3
            return random_classifier(r)
        for pos in ((10, -50), (40, 0), (500, 30), (-30, 20), (60, 200), (60, 90), (30, 110)):
            if r.random() < 0.5:
                continue
            yield Case(f"keg tiles {shape} at {pos}", 0x46F2A0, keg_setup(r, classify=classifier(), pos=pos),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for late in ("swap-actor", (0, 0x55), (0, 0), (1, 0x80000000), (0x20, 0xFFFFFFFF), (0x21, 0), (0x40, 0), (9, 0x201)):
        for tree in ("match", "empty"):
            yield Case(f"keg changed behind its back {late}", 0x46F2A0, keg_setup(r, late=late, tree=tree),
                       receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))
    for _ in range(25):
        yield Case("keg random", 0x46F2A0,
                   keg_setup(r, res=pick((None, (0, 12), (r.randrange(0, 12), r.randrange(0, 14)))),
                             lifts=tuple(r.random() < 0.6 for _ in range(4)), game_null=r.random() < 0.7, kegboom=r.random() < 0.7,
                             big_string=pick((None, b"40", b"3-70")), depth=pick((1, 0, 5)), hooks=False,
                             rect_delta=r.randrange(-4, 5), special_left=r.random() < 0.15,
                             tree=pick(("match", "match", "empty", "deep", "mismatch")),
                             pos=(r.randrange(-40, 160), r.randrange(-80, 120)),
                             malloc_fail=pick((None, None, None, 2, 3))),
                   receiver=lambda t: t["L"], arguments=(lambda t: t["P"],))


def holder_setup(r, state, mode, build=None, swap=False):
    """The object a creator works on: actor P with service S whose state selects the action."""
    def setup(env):
        if build is None:
            tokens = keg_world(env, r, size=0x20)
        else:
            tokens = build(env)
        log = tokens["log"]
        service, actor = tokens["S"], tokens["P"]
        env.put(service + 0x1C, state)
        vtable = env.object(0x100, "held-vtable", words=words_of(r, 0x40))
        held = env.object(0x420, "held-logic", words=words_of(r, 0x108))
        env.put(held, vtable)
        env.put(vtable + 0x1C, env.stub("held-slot-1c", "thiscall", 0, lambda e, c: observe(e, log, 0x1C, c, True) or 1))
        env.put(vtable + 0x20, env.stub("held-slot-20", "thiscall", 0, lambda e, c: observe(e, log, 0x20, c, True) or 2))
        env.put(vtable + 0x04, env.stub("held-slot-04", "thiscall", 1, lambda e, c: observe(e, log, 0x04, c, True) or 3))
        env.put(vtable + 0x08, env.stub("held-slot-08", "thiscall", 1, lambda e, c: observe(e, log, 0x08, c, True) or 4))
        env.put(vtable + 0x0C, env.stub("held-slot-0c", "thiscall", 1, lambda e, c: observe(e, log, 0x0C, c, True) or 5))
        env.put(service + 0x18, held)
        # the cache read by 0x4dc870 for any other state
        identifier = r.randrange(3, 40)
        link = env.object(0x40, "held-link", words=words_of(r, 0x10))
        env.put(link + 0x1C, identifier)
        env.put(held + 0x10, link)
        lo = identifier - r.randrange(0, 3)
        hi = identifier + r.randrange(0, 3)
        stride = r.choice((4, 8, 12))
        area = env.object((hi - lo + 1) * stride + 4, "string-cache", words=words_of(r, ((hi - lo + 1) * stride + 4) // 4))
        for number in range(hi - lo + 1):
            text = b"cache-entry-%d" % (lo + number)
            header = env.object(12 + len(text) + 8, "cstring", data=struct.pack("<III", 1, len(text), len(text) + 4) + text + b"\0")
            env.put(area + number * stride, header + 12)
        env.put(0x5376A0, lo, hi, area)
        env.put(0x5376B0, stride, r.randrange(1, M32), 0)
        other_service = env.object(0x180, "replacement-info", words=words_of(r, 0x60))

        def after_construction(e, c):
            observe(e, log, 0x110, c, True)
            if swap:
                e.put(actor + 0x6C, other_service)
            return 9
        env.put(KEG_VTABLE_SLOT, env.stub("keg-slot-10", "thiscall", 0, after_construction))
        env.put(CRATE_VTABLE_SLOT, env.stub("crate-slot-10", "thiscall", 0, lambda e, c: observe(e, log, 0x111, c, True) or 9))
        tokens["held"] = held
        return tokens
    return setup


def creator_cases(r):
    pick = r.choice
    for state in (0x1D, 0x1E, 0x3E8, 1, 2, 5, 0x1C, 0x1F, 0x40, 0x7FFFFFFF, M32, 0x3E7, 0x3E9):
        for _ in range(2):
            yield Case(f"keg creator state {state:#x}", 0x46F1E0, holder_setup(r, state, None), arguments=(lambda t: t["P"],))
    for _ in range(8):
        def build(env):
            return keg_world(env, r, size=0x20, lifts=tuple(r.random() < 0.7 for _ in range(4)), big_string=pick((None, b"40")),
                             pos=(r.randrange(-40, 160), r.randrange(-80, 120)), depth=pick((1, 0)))
        yield Case("keg creator builds a keg", 0x46F1E0, holder_setup(r, 0, None, build), arguments=(lambda t: t["P"],))
    for _ in range(3):
        yield Case("keg creator, actor service replaced meanwhile", 0x46F1E0, holder_setup(r, 0, None, None, True),
                   arguments=(lambda t: t["P"],))


# ----------------------------------------------------------------------------------------------
# the crate logic 0x48d6e0 and its creator 0x48d560
def crate_world(env, r, *, values=(0x20, 0x31, 0, 0x40, 0x20, 0, 0x55, 0x66, 0x20), p100=0, p64=0, existing=(),
                names_found=True, hooks=False, p50=None, p4c=None, mutate=None, swap_service=False):
    log = new_log(env)
    owner_actor_slot = []
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    env.put(scene + 0x0C, context)
    env.put(context + 0x08, scene)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for index in range(63):
        env.put(pool + index * 12, pool + (index + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    actors, nodes = [], []
    for index, (priority, flags) in enumerate(existing):
        other = env.object(0x1B4, f"queued-actor-{index}", fill=0x63 + index)
        node = env.object(12, f"queued-node-{index}", fill=0)
        env.put(other + 8, flags)
        env.put(other + 0x64, priority & M32, node, 0)
        actors.append(other)
        nodes.append(node)
    for index, node in enumerate(nodes):
        env.put(node, nodes[index + 1] if index + 1 < len(nodes) else 0, nodes[index - 1] if index else 0, actors[index])
    env.put(scene + 0x14, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
    metadata = env.object(0x18, "crate-metadata", fill=0)
    crate_key = env.cstr(0x522C28)
    env.put(context + 0x14, make_registry(env, r, {crate_key: metadata} if names_found else {}, r.choice((3, 5, 7))))

    logic_words = words_of(r, 0x104)
    mutation_words = words_of(r, 4)
    replacement_service_words = words_of(r, 0x5D)

    def make_logic(env, call):
        actor = call.arguments[0]
        service = env.get(actor + 0x6C)
        logic = env.object(0x410, "crate-logic", words=logic_words)
        env.put(service + 0x18, logic)
        number = env.calls_so_far(call.function)
        if mutate == "items" and number == 1:
            owner_service = env.get(owner_actor_slot[0] + 0x6C)
            env.put(owner_service + 0xF4, 0)
            env.put(owner_service + 0xF8, 0x66)
            env.put(owner_service + 0xFC, mutation_words[0] | 1)
        elif mutate == "position":
            owner = owner_actor_slot[0]
            env.put(owner + 0x50, (env.get(owner + 0x50) + 7 * number) & M32)
            env.put(owner + 0x64, (env.get(owner + 0x64) + 3) & M32)
        elif mutate == "service" and number % 2 == 1:
            replacement_service = env.object(0x174, "replacement-service", words=replacement_service_words)
            replacement_logic = env.object(0x410, "replacement-logic", words=logic_words)
            env.put(replacement_service + 0x18, replacement_logic)
            env.put(actor + 0x6C, replacement_service)
        observe(env, log, 0xC0, call, False,
                extra=(env.get(actor + 0x100), env.get(actor + 0x148), env.get(actor + 0xFC), env.get(actor + 0x4C), env.get(actor + 0x50)))
        return 0
    callback = env.stub("crate-service-callback", "cdecl", 1, make_logic)

    def init(env, call):
        actor = call.receiver
        service = env.get(actor + 0x6C)
        x, y, priority, meta = call.arguments
        env.put(actor + 0x4C, x, y)
        env.put(actor + 0x64, priority)
        env.put(service + 0x10, callback)
        observe(env, log, 0xC1, call, True)
        return 1
    env.put(ACTOR_INIT_SLOT, env.stub("actor-initializer", "thiscall", 4, init))
    other_service = env.object(0x174, "replacement-owner-service", words=words_of(r, 0x5D))

    def after_construction(e, c):
        observe(e, log, 0x111, c, True)
        if swap_service:
            e.put(owner_actor_slot[0] + 0x6C, other_service)
        return 9
    env.put(CRATE_VTABLE_SLOT, env.stub("crate-slot-10", "thiscall", 0, after_construction))
    service = env.object(0x174, "owner-service", words=words_of(r, 0x5D))
    env.put(service + 0x0C, context)
    for index, value in enumerate(values[:8]):
        env.put(service + 0xF0 + 4 * index, value)
    env.put(service + 0x1C, 0)
    registry = make_registry(env, r, {}, 3)
    if hooks:
        env.put(SOUND_VTABLE_PLAY, env.stub("new-voice-play", "thiscall", 2, returns(6)))
    world = env.object(0x160, "world", words=words_of(r, 0x58))
    env.put(world + 0x14, registry)
    actor = env.object(0x1C0, "owner-actor", words=words_of(r, 0x70))
    owner_actor_slot.append(actor)
    env.put(actor + 0x0C, world)
    env.put(actor + 0x6C, service)
    env.put(actor + 0x70, 0)
    env.put(actor + 0x78, 0)
    env.put(actor + 0x100, p100)
    env.put(actor + 0x64, p64 & M32)
    env.put(actor + 0x4C, r.randrange(-50, 400) & M32, (p50 if p50 is not None else r.randrange(100, 500)) & M32)
    env.put(actor + 0x08, r.randrange(0, 1 << 32) & ~0x10001)
    env.put(actor + 0x40, r.randrange(0, 1 << 32))
    crate = env.object(0x4C, "crate-logic-object", words=words_of(r, 0x13))
    return {"P": actor, "S": service, "C": crate, "log": log}


def crate_cases(r):
    pick = r.choice
    items = (0x20, 0x31, 0x44, 0x1000, 0x7F)
    def pattern(count_mask):
        values = []
        for index in range(8):
            values.append(pick(items) if count_mask >> index & 1 else 0)
        return tuple(values)

    for mask in (0xFF, 0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xAA, 0x55, 0x03, 0xC0, 0x7E):
        for p100 in (0, 0x20, 0x31):
            if r.random() < 0.4:
                continue
            for value in (0x1388, 0):
                yield Case(f"crate logic mask {mask:#x} p100={p100:#x} value={value:#x}", 0x48D6E0,
                           lambda env, mask=mask, p100=p100: crate_world(env, r, values=pattern(mask), p100=p100,
                                                                         p64=pick((0, 0, 5))),
                           receiver=lambda t: t["C"], arguments=(lambda t: t["P"], value))
    for _ in range(8):
        value = r.randrange(0, M32)
        yield Case("crate logic random priority", 0x48D6E0,
                   lambda env: crate_world(env, r, values=pattern(r.randrange(0, 256)), p100=pick((0, 0x20)),
                                           p64=pick((0, 7, 0x80000000)),
                                           existing=pick(((), ((3, 0), (9, 0)), ((20, 0x20000),), ((0x7FFFFFFF, 0), (-1, 0))))),
                   receiver=lambda t: t["C"], arguments=(lambda t: t["P"], value))
    for mutate in ("items", "position", "service"):
        for mask in (0xFF, 0x7F, 0xAB):
            yield Case(f"crate logic changed behind its back: {mutate} mask {mask:#x}", 0x48D6E0,
                       lambda env, mutate=mutate, mask=mask: crate_world(env, r, values=pattern(mask), p100=pick((0, 0x20)), mutate=mutate),
                       receiver=lambda t: t["C"], arguments=(lambda t: t["P"], 0x1388))
    for p64 in (1, 2, 0x44):
        yield Case(f"crate logic keeps priority {p64}", 0x48D6E0,
                   lambda env, p64=p64: crate_world(env, r, p64=p64), receiver=lambda t: t["C"], arguments=(lambda t: t["P"], 0x1388))


def crate_creator_setup(r, state, **options):
    def setup(env):
        tokens = crate_world(env, r, **options)
        log = tokens["log"]
        service = tokens["S"]
        env.put(service + 0x1C, state)
        vtable = env.object(0x100, "held-vtable", words=words_of(r, 0x40))
        held = env.object(0x420, "held-logic", words=words_of(r, 0x108))
        env.put(held, vtable)
        env.put(vtable + 0x1C, env.stub("held-slot-1c", "thiscall", 0, lambda e, c: observe(e, log, 0x1C, c, True) or 1))
        env.put(vtable + 0x20, env.stub("held-slot-20", "thiscall", 0, lambda e, c: observe(e, log, 0x20, c, True) or 2))
        env.put(vtable + 0x04, env.stub("held-slot-04", "thiscall", 1, lambda e, c: observe(e, log, 0x04, c, True) or 3))
        env.put(vtable + 0x08, env.stub("held-slot-08", "thiscall", 1, lambda e, c: observe(e, log, 0x08, c, True) or 4))
        env.put(vtable + 0x0C, env.stub("held-slot-0c", "thiscall", 1, lambda e, c: observe(e, log, 0x0C, c, True) or 5))
        env.put(service + 0x18, held)
        identifier = r.randrange(3, 40)
        link = env.object(0x40, "held-link", words=words_of(r, 0x10))
        env.put(link + 0x1C, identifier)
        env.put(held + 0x10, link)
        stride = r.choice((4, 8))
        lo, hi = identifier - 1, identifier + 1
        area = env.object((hi - lo + 1) * stride + 4, "string-cache", words=words_of(r, ((hi - lo + 1) * stride + 4) // 4))
        for number in range(hi - lo + 1):
            text = b"cache-entry-%d" % (lo + number)
            header = env.object(12 + len(text) + 8, "cstring", data=struct.pack("<III", 1, len(text), len(text) + 4) + text + b"\0")
            env.put(area + number * stride, header + 12)
        env.put(0x5376A0, lo, hi, area)
        env.put(0x5376B0, stride, r.randrange(1, M32), 0)
        return tokens
    return setup


def crate_creator_cases(r):
    for _ in range(3):
        yield Case("crate creator, actor service replaced meanwhile", 0x48D560,
                   crate_creator_setup(r, 0, values=(0x20, 0x31, 0, 0x44, 0, 0, 0, 0x20), swap_service=True), arguments=(lambda t: t["P"],))
    for state in (0x1D, 0x1E, 0x3E8, 1, 5, 0x1C, 0x1F, 0x40, M32, 0x3E9):
        yield Case(f"crate creator state {state:#x}", 0x48D560, crate_creator_setup(r, state), arguments=(lambda t: t["P"],))
    for mask in (0xFF, 0x01, 0x81, 0x00, 0x55):
        for p100 in (0, 0x20):
            values = tuple((r.choice((0x20, 0x31, 0x44)) if mask >> index & 1 else 0) for index in range(8))
            yield Case(f"crate creator builds mask {mask:#x} p100 {p100:#x}", 0x48D560,
                       crate_creator_setup(r, 0, values=values, p100=p100), arguments=(lambda t: t["P"],))


def cases(random_source):
    r = random_source
    yield from thunk_cases(r)
    yield from crate_item_cases(r)
    yield from dispatch_cases(r)
    yield from sm_cases(r)
    yield from keg_cases(r)
    yield from creator_cases(r)
    yield from crate_cases(r)
    yield from crate_creator_cases(r)
