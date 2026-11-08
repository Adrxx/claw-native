"""Cases for level_one_timers_checkpoints_02: Level 1 timer and checkpoint entries, batch 2.

Owned functions and the cases that reach them:

* 0x4919f0 / 0x491ed0 take an owner P (P+8 flags, P+0x6c state record S, S+0x1c state, S+0x18 entry E).
* 0x4d3ca0 / 0x4d3e50 build a child object through the static vtable 0x5137f0 (+0x28 create, +4 delete) and
  append it to the CPtrList at manager+0x1b4. 0x4c8e00 / 0x4c8f60 do the same through vtable 0x513830 and a depth
  sorted list at manager+0x10. Most cases replace those two vtable slots with recording stubs (the static data of
  the program image is rewritten in setup); the "real" cases leave the vtable alone and let the original create and
  initialise the child from a resource record.
* 0x4d3ef0 / 0x4d3f20 walk the list at manager+0x1b8 and call back into each item.

Every branch is reached by a fixed case list. The random source only changes the values inside the objects.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns  # noqa: F401

M32 = 0xFFFFFFFF

F_4919F0, F_491ED0, F_4C8E00, F_4C8F60 = 0x4919F0, 0x491ED0, 0x4C8E00, 0x4C8F60
F_4D3CA0, F_4D3E50, F_4D3EF0, F_4D3F20 = 0x4D3CA0, 0x4D3E50, 0x4D3EF0, 0x4D3F20

OPERATOR_NEW = 0x4F63EC
G_CURRENT = 0x5371FC          # pointer to the clock record: +0x68 tick, +0x6c step
G_BOUNDS = 0x5370C8           # x low, y low, x high, y high
G_MANAGER = 0x53C9FC          # written by 0x491ed0
G_LOCALE = 0x540E00           # zero selects the single byte string compare
VT_CHILD = 0x5137F0           # +4 delete, +0x28 create (0x4d3ca0)
VT_SORTED = 0x513830          # +4 delete, +0x28 create (0x4c8e00)
LIST_VPTR = 0x5107BC
FRAME_KEYS = (0x5229D8, 0x5229CC, 0x5229C0, 0x5229B4, 0x5229A8)   # ScoreFrame ... TimerFrame

UNBACKED = 0x0BAD0000         # a pointer that no object backs: the original never touches it where used


def s32(value):
    value &= M32
    return value - (1 << 32) if value & 0x80000000 else value


def words(rs, count):
    return [rs.randrange(1, 1 << 32) for _ in range(count)]


def junk(env, rs, size, name):
    """A live object with distinct non-zero contents."""
    return env.object(size, name, words=words(rs, (size + 3) // 4))


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


# ---------------------------------------------------------------------------------------------------------------
# observation log: every stub appends one row to surviving case memory
ROW = 64


def new_log(env):
    return env.object(0x2000, "log", fill=0)


def record(env, log, tag, receiver, args, extra=()):
    n = env.get(log)
    if n >= (0x2000 - 4) // ROW:
        return
    env.put(log, n + 1)
    env.put(log + 4 + n * ROW, tag, receiver, len(args), *(list(args) + [0] * (6 - len(args))), *extra)


def peek(env, address):
    try:
        return env.get(address)
    except Exception:  # an address outside every region
        return 0xDEADDEAD


def logged(env, log, tag, name, convention, argc, result=0, extra=lambda env, call: ()):
    def effect(env, call):
        record(env, log, tag, call.receiver, call.arguments, extra(env, call))
        return result
    return env.stub(name, convention, argc, effect)


# ---------------------------------------------------------------------------------------------------------------
# CPtrList embedded in an owner: +0 vptr, +4 head, +8 tail, +0xc count, +0x10 free, +0x14 blocks, +0x18 block size
def make_list(env, rs, base, items, free=0, blocksize=None, count=None):
    nodes, prev = [], 0
    for item in items:
        node = env.object(12, "list-node", words=[0, prev, item])
        if prev:
            env.put(prev, node)
        nodes.append(node)
        prev = node
    free_head = 0
    for _ in range(free):
        free_head = env.object(12, "free-node", words=[free_head] + words(rs, 2))
    blocks = env.object(16, "old-block", words=words(rs, 4)) if (len(items) + free) % 2 == 0 else 0
    env.put(base, LIST_VPTR, nodes[0] if nodes else 0, nodes[-1] if nodes else 0,
            len(items) if count is None else count, free_head, blocks,
            blocksize if blocksize is not None else rs.randrange(1, 13))
    return nodes


def list_items(env, base):
    """The data words of a list as it stands now, head to tail, and its count."""
    out, node = [], env.get(base + 4)
    while node and len(out) < 64:
        out.append(env.get(node + 8))
        node = env.get(node)
    return out


# ---------------------------------------------------------------------------------------------------------------
# registry (string -> record), the dictionary behind 0x4f6286, embedded at owner+0x10
def make_registry(env, rs, entries, buckets, decoys=True):
    owner = junk(env, rs, 0x40, "registry-owner")
    env.put(G_LOCALE, 0)
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(owner + 0x14, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        index = key_hash(name) % buckets
        old = env.get(array + 4 * index)
        if decoys:
            decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
            if (len(name) + buckets) % 2 == 0:
                node = env.object(16, "registry-node", words=[old, rs.randrange(1, 99), key, value])
                decoy = env.object(16, "registry-decoy", words=[node, 7, decoy_key, (value ^ 0xFFFF) & M32])
                env.put(array + 4 * index, decoy)
            else:
                decoy = env.object(16, "registry-decoy", words=[old, 7, decoy_key, (value ^ 0xFFFF) & M32])
                node = env.object(16, "registry-node", words=[decoy, rs.randrange(1, 99), key, value])
                env.put(array + 4 * index, node)
        else:
            node = env.object(16, "registry-node", words=[old, rs.randrange(1, 99), key, value])
            env.put(array + 4 * index, node)
    return owner


def make_record(env, rs, flags, fn):
    """A resource record: +8 flags, +0x10 pointer to a callback (read by the original child initialiser)."""
    record_ = junk(env, rs, 0x28, "resource-record")
    env.put(record_ + 8, flags)
    env.put(record_ + 0x10, fn)
    return record_


# ---------------------------------------------------------------------------------------------------------------
# a manager: the receiver of 0x4d3ca0, 0x4d3e50, 0x4d3ef0, 0x4d3f20 (list at +0x1b4) and of 0x4c8e00/0x4c8f60 (list at +0x10)
def make_manager(env, rs, list_at=0x1B4, items=(), free=0, blocksize=None, registry=None, size=0x1D0):
    scene = junk(env, rs, 0x30, "scene")
    if registry is None:
        registry = make_registry(env, rs, {}, rs.randrange(1, 8), decoys=False)
    env.put(scene + 0x14, registry)
    manager = junk(env, rs, size, "manager")
    env.put(manager + 0xC, scene)
    nodes = make_list(env, rs, manager + list_at, items, free=free, blocksize=blocksize)
    return manager, nodes


def make_item(env, rs, depth=None, flag=None, fn=0, vt=0):
    """A list item: +0 vtable, +0xa flag byte, +0x64 depth, +0x6c sub object whose +0x10 is a callback."""
    item = junk(env, rs, 0x78, "item")
    sub = junk(env, rs, 0x20, "item-sub")
    env.put(sub + 0x10, fn)
    env.put(item + 0x6C, sub)
    if vt:
        env.put(item, vt)
    if depth is not None:
        env.put(item + 0x64, depth)
    if flag is not None:
        env.write(item + 0xA, bytes([flag & 0xFF]))
    return item


# ---------------------------------------------------------------------------------------------------------------
# virtual create / delete stubs for the static vtables
def create_stub(env, log, vt, results=(1,), depth=None, sub_fn=None, flags=None, swap_sub=None, edit=None):
    """Install the recording create (+0x28) stub: thiscall, four arguments.

    `results` is the result of the first, second, ... call (the last one repeats). The stub may also set the depth the
    original initialiser would store (+0x64), the callback of the sub object (+0x10), the flag word (+8), replace the
    sub object (+0x6c) or run `edit(env, call)`; all of them happen before the owned function reads them again."""
    def effect(env, call):
        obj = call.receiver
        n = env.calls_so_far(call.function)
        sub = peek(env, obj + 0x6C)
        record(env, log, 0xC1, obj, call.arguments,
               (env.get(obj), env.get(obj + 4), env.get(obj + 8), env.get(obj + 0xC), env.get(obj + 0x68), sub,
                peek(env, sub + 4) if sub else 0, peek(env, sub + 0xC) if sub else 0, n))
        if depth is not None:
            env.put(obj + 0x64, depth)
        if flags is not None:
            env.put(obj + 8, flags)
        if sub_fn is not None and sub:
            env.put(sub + 0x10, sub_fn)
        if swap_sub is not None:
            env.put(obj + 0x6C, swap_sub)
        if edit is not None:
            edit(env, call)
        return results[min(n, len(results)) - 1]
    env.put(vt + 0x28, env.stub("child-create", "thiscall", 4, effect))


def delete_stub(env, log, vt):
    def effect(env, call):
        record(env, log, 0xD1, call.receiver, call.arguments, (env.get(call.receiver), env.get(call.receiver + 0x68)))
        env.release(call.receiver)
        return 0
    env.put(vt + 4, env.stub("child-delete", "thiscall", 1, effect))


# ---------------------------------------------------------------------------------------------------------------
# 0x4919f0
def timer_setup(rs, state=5, entry=True, tick=1, step=1, e_tick=None, e_end=100, k1=0, k2=0, x=None, y=None,
                bounds=None, d_valid=True, tamper=None, p_flags=None):
    """Owner P with state record S, entry E, destination D and the clock record G."""
    def setup(env):
        log = new_log(env)
        owner = junk(env, rs, 0x80, "owner")
        if p_flags is not None:
            env.put(owner + 8, p_flags)
        record_ = junk(env, rs, 0x30, "state-record")
        env.put(owner + 0x6C, record_)
        env.put(record_ + 0x1C, state)
        clock = junk(env, rs, 0x70, "clock")
        env.put(clock + 0x68, tick, step)
        env.put(G_CURRENT, clock)
        bx = bounds or (rs.randrange(-400, 400), rs.randrange(-400, 400), rs.randrange(-400, 400), rs.randrange(-400, 400))
        env.put(G_BOUNDS, *bx)
        tokens = {"owner": owner, "state": record_, "clock": clock, "log": log, "bounds": bx}
        if state != 5:
            env.put(record_ + 0x18, UNBACKED + 0x100)
            return tokens
        if not entry:
            env.put(record_ + 0x18, 0)
            return tokens
        e = junk(env, rs, 0x40, "entry")
        env.put(record_ + 0x18, e)
        tokens["entry"] = e
        env.put(e + 4, k1, x if x is not None else rs.randrange(-300, 300), k2, y if y is not None else rs.randrange(-300, 300))
        env.put(e + 0x14, rs.randrange(1, 1 << 32) if e_tick is None else e_tick, e_end)
        if not d_valid:
            env.put(e + 0x24, 0)
            return tokens
        dest = junk(env, rs, 0x178, "destination")
        env.put(e + 0x24, dest)
        tokens["dest"] = dest
        x_node = junk(env, rs, 0x20, "dest-x")
        y_node = junk(env, rs, 0x20, "dest-y")
        table = junk(env, rs, 0x40, "dest-vtable")
        env.put(dest + 0xC, x_node)
        env.put(x_node + 0xC, y_node)
        env.put(y_node, table)

        def effect(env, call):
            record(env, log, 0xA1, call.receiver, call.arguments,
                   (env.get(e + 0x14), env.get(e + 0x1C), env.get(e + 0x20), env.get(dest + 0x40), env.get(e + 0x24)))
            if tamper == "swap-dest":
                other = tokens["other"]
                env.put(e + 0x24, other)
            elif tamper == "dest-flag":
                env.put(dest + 0x40, 0x80000000 | rs_flags)
            elif tamper == "entry-fields":
                env.put(e + 0x1C, 0xAAAA5555, 0x5555AAAA)
            return call.arguments[0] ^ 0x12345678
        rs_flags = 0x2468
        env.put(table + 0x28, env.stub("clock-notify", "thiscall", 3, effect))
        tokens["y"] = y_node
        if tamper == "swap-dest":
            other = junk(env, rs, 0x178, "other-destination")
            tokens["other"] = other
        return tokens
    return setup


def timer_case(label, rs, **o):
    return Case(label, F_4919F0, timer_setup(rs, **o), arguments=(lambda t: t["owner"],))


def timer_cases(rs):
    ticks = (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFF9)
    # state handling
    for state in (0, 1, 2, 4, 6, 0xFF, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield timer_case(f"state {state:#x}", rs, state=state, p_flags=rs.randrange(0, 1 << 32))
    yield timer_case("state 0 keeps set bits", rs, state=0, p_flags=0xFFFFFFFE)
    yield timer_case("state 0 flag already set", rs, state=0, p_flags=1)
    yield timer_case("state 5 without entry", rs, entry=False)
    # equal tick gate against the step
    for tick in (0, 7, 0x80000000, 0xFFFFFFFF):
        for step in (0x80000000, 0xFFFFFFFF, 0, 1, rs.randrange(2, 99)):
            yield timer_case(f"gate tick {tick:#x} step {step:#x}", rs, tick=tick, step=step, e_tick=tick, e_end=0x7FFFFFFF,
                             k1=1, k2=4)
    # different tick: gate open, no matter the step
    for tick in ticks:
        for step in (0xFFFFFFFF, 1):
            yield timer_case(f"gate open tick {tick:#x}", rs, tick=tick, step=step, e_tick=(tick + 3) & M32, e_end=0x7FFFFFFF,
                             k1=2, k2=5)
    # end of the window: signed compare of the tick with the end
    for tick, end in ((0, 0), (0, 1), (0, 0xFFFFFFFF), (0, 0x80000000), (5, 4), (5, 5), (5, 6), (0xFFFFFFFF, 1),
                      (1, 0xFFFFFFFF), (0xFFFFFFFF, 0xFFFFFFFF), (0xFFFFFFFE, 0xFFFFFFFF), (0xFFFFFFFF, 0xFFFFFFFE),
                      (0x80000000, 0x7FFFFFFF), (0x7FFFFFFF, 0x80000000), (0x7FFFFFFF, 0x7FFFFFFF)):
        for step in ((1, 0) if tick in (0, 5, 0xFFFFFFFF) else (1,)):
            yield timer_case(f"window tick {tick:#x} end {end:#x} step {step}", rs, tick=tick, step=step,
                             e_tick=(tick ^ 0x55) & M32, e_end=end, k1=1, k2=3)
    # the switches on the entry kinds, tick not zero so the destination is only written
    for k1 in (0, 1, 2, 3, 4, 0x80000000):
        for k2 in (0, 2, 3, 4, 5, 6, 0xFFFFFFFF):
            yield timer_case(f"kinds {k1:#x}/{k2:#x}", rs, tick=rs.randrange(1, 99), e_end=0x7FFFFFFF, k1=k1, k2=k2)
    # same kinds with a null destination when neither switch matches
    for k1 in (0, 4, 0xFFFFFFFF):
        for k2 in (0, 1, 2, 6):
            yield timer_case(f"no destination kinds {k1:#x}/{k2:#x}", rs, tick=3, e_end=9, k1=k1, k2=k2, d_valid=False)
    # midpoint arithmetic: difference sign and parity
    for lo, hi in ((0, 0), (0, 1), (1, 0), (0, 2), (-3, 4), (4, -3), (-7, -2), (-2, -7), (10, 11),
                   (-1, 0), (0, -1), (-5, 5), (100, -100), (0x7FFFFFF0, -0x7FFFFFF0), (rs.randrange(-999, 999), rs.randrange(-999, 999))):
        for k1, k2 in ((3, 0), (0, 3)):
            yield timer_case(f"midpoint {lo}..{hi} kinds {k1}/{k2}", rs, tick=2, e_end=9, k1=k1, k2=k2,
                             bounds=(lo, lo + 1, hi, hi - 1) if k1 == 3 else (lo, lo, hi, hi),
                             x=rs.randrange(-9, 9), y=rs.randrange(-9, 9))
    # fixed bounds: every kind adds its own bound
    for k1, k2 in ((1, 3), (2, 4), (3, 5), (1, 5), (2, 3), (3, 4)):
        yield timer_case(f"distinct bounds kinds {k1}/{k2}", rs, tick=9, e_end=11, k1=k1, k2=k2, bounds=(1000, 20000, 300000, 4000000),
                         x=7, y=70)
    # the firing path: tick zero, call through the clock chain
    pairs = ((1, 3), (2, 4), (3, 5), (0, 0), (3, 3), (4, 6), (1, 9))
    for e_tick in (0, 1, None):
        for step in (0xFFFFFFFF, 0, 1):
            for e_end in (0, 1, 0x7FFFFFFF):
                k1, k2 = pairs[(step + e_end) % len(pairs)]
                yield timer_case(f"fire entry tick {e_tick} step {step:#x} end {e_end}", rs, tick=0, step=step, e_tick=e_tick,
                                 e_end=e_end, k1=k1, k2=k2)
    for k1 in (0, 1, 2, 3, 4):
        for k2 in (0, 3, 4, 5, 6):
            yield timer_case(f"fire kinds {k1}/{k2}", rs, tick=0, step=1, e_tick=rs.randrange(1, 1 << 32), e_end=rs.randrange(0, 50),
                             k1=k1, k2=k2)
    yield timer_case("fire: window below zero keeps entry", rs, tick=0, step=1, e_tick=5, e_end=0xFFFFFFFF, k1=1, k2=3)
    yield timer_case("fire: window of zero", rs, tick=0, step=1, e_tick=5, e_end=0, k1=3, k2=3)
    # the callback changes what is read afterwards
    for tamper in ("swap-dest", "dest-flag", "entry-fields"):
        for p_flags in (None, 0):
            yield timer_case(f"callback tamper {tamper}", rs, tick=0, step=1, e_tick=9, e_end=3, k1=3, k2=4, tamper=tamper,
                             p_flags=p_flags)


# ---------------------------------------------------------------------------------------------------------------
# 0x4d3ca0 and 0x4c8e00: construct, initialise, list
def child_world(rs, kind, results=(1,), items=(), item_depths=None, item_flags=None, free=0, blocksize=None, entries=None, buckets=None,
                depth=None, flags_arg=0, sub_fn=True, create_edit=None, create_flags=None, swap_sub=False, vt_on=True, fail_new=(),
                fail_sub=False, real=False, record_flags=1, record_fn=True, record_value=True, with_key=None, extra_tick=None,
                direct=True, list_tamper=None, delete_hits=True):
    """Everything 0x4d3ca0 / 0x4c8e00 / their registry wrappers need. kind is 'child' (list +0x1b4, vtable 0x5137f0) or
    'sorted' (list +0x10, vtable 0x513830)."""
    def setup(env):
        log = new_log(env)
        vt = VT_CHILD if kind == "child" else VT_SORTED
        base = 0x1B4 if kind == "child" else 0x10
        made = []
        for index in range(len(items)):
            made.append(make_item(env, rs, depth=item_depths[index] if item_depths else None,
                                  flag=item_flags[index] if item_flags else None))
        registry = None
        record_ptr = 0
        fn = logged(env, log, 0xF1, "record-callback", "cdecl", 1) if record_fn else 0
        if entries is not None:
            table = {}
            for name in entries:
                table[name] = make_record(env, rs, record_flags, fn) if record_value else 0
            registry = make_registry(env, rs, table, buckets or rs.randrange(1, 8))
            record_ptr = table.get(with_key, 0)
        manager, nodes = make_manager(env, rs, list_at=base, items=made, free=free, blocksize=blocksize, registry=registry)
        sub_fn_stub = logged(env, log, 0xF2, "child-callback", "cdecl", 1) if sub_fn else None
        if real:
            record_ptr = make_record(env, rs, record_flags, fn)
        if not real:
            if vt_on:
                create_stub(env, log, vt, results=results, depth=depth, sub_fn=sub_fn_stub, flags=create_flags,
                            swap_sub=None, edit=None if create_edit is None else create_edit(env, manager, nodes))
            delete_stub(env, log, vt)
        tokens = {"manager": manager, "log": log, "record": record_ptr, "nodes": nodes, "items": made, "vt": vt}
        if fail_new:
            def deny(env, call):
                if env.calls_so_far(call.function) in fail_new:
                    return 0
                return env.object(call.arguments[0], name="allocation")
            env.override(OPERATOR_NEW, deny)
        if with_key is not None:
            key = env.object(len(with_key) + 4, "lookup-key", data=with_key + b"\0")
            tokens["key"] = key
        return tokens
    return setup


def sorted_case(label, rs, function, args=(1, 2, 3, 4, 5, 6), **o):
    """0x4c8e00 or 0x4c8f60 with explicit argument list; None entries are replaced by the record pointer / lookup key."""
    setup = child_world(rs, "sorted", **o)

    def arguments_of(tokens):
        out = []
        for index, value in enumerate(args):
            if value == "record":
                out.append(tokens["record"])
            elif value == "key":
                out.append(tokens["key"])
            else:
                out.append(value)
        return out
    return Case(label, function, setup, receiver=lambda t: t["manager"],
                arguments=tuple((lambda t, i=i: arguments_of(t)[i]) for i in range(6)))


def child_case(label, rs, function, args=(1, 2, 3, 4, 5, 6), **o):
    setup = child_world(rs, "child", **o)

    def arguments_of(tokens):
        out = []
        for value in args:
            if value == "record":
                out.append(tokens["record"])
            elif value == "key":
                out.append(tokens["key"])
            else:
                out.append(value)
        return out
    return Case(label, function, setup, receiver=lambda t: t["manager"],
                arguments=tuple((lambda t, i=i: arguments_of(t)[i]) for i in range(6)))


def child_cases(rs):
    for results in ((1,), (0,), (0x80000000,)):
        for flag in (0, 0x200000, 0xFFDFFFFF, 0x1000000):
            yield child_case(f"child results {results[0]:#x} flags {flag:#x}", rs, F_4D3CA0,
                             args=(rs.randrange(1, 1 << 32), rs.randrange(1, 1 << 32), rs.randrange(1, 1 << 32),
                                   rs.randrange(1, 1 << 32), rs.randrange(1, 1 << 32), flag), results=results)
    # argument positions: every one distinct
    yield child_case("child arguments distinct", rs, F_4D3CA0, args=(0x11111111, 0x22222222, 0x33333333, 0x44444444, 0x55555555, 0x200000))
    yield child_case("child arguments distinct no callback", rs, F_4D3CA0,
                     args=(0x1A1A1A1A, 0x2B2B2B2B, 0x3C3C3C3C, 0x4D4D4D4D, 0x5E5E5E5E, 0x66666666))
    # list contents: empty, one, many, with and without a free list
    for count in (0, 1, 3):
        for free in (0, 2):
            for flag in (0, 0x200000):
                yield child_case(f"child list {count} free {free} flag {flag:#x}", rs, F_4D3CA0,
                                 args=tuple(words(rs, 5)) + (flag,), items=tuple(range(count)), free=free,
                                 blocksize=rs.randrange(1, 13))
    for blocksize in (1, 2, 3, 10, 100):
        yield child_case(f"child block size {blocksize}", rs, F_4D3CA0, args=tuple(words(rs, 6)), items=(0,), blocksize=blocksize)
    # failures of the allocator
    yield child_case("child: first allocation fails", rs, F_4D3CA0, args=tuple(words(rs, 6)), fail_new=(1,), items=(0, 1))
    yield child_case("child: first allocation fails, flag set", rs, F_4D3CA0, args=tuple(words(rs, 5)) + (0x200000,), fail_new=(1,))
    # the sub object allocation fails: fine while the 0x200000 callback is not called (it would read address 0x10)
    for results in ((1,), (0,)):
        for count in (0, 2):
            yield child_case(f"child: sub-object allocation fails result {results[0]} list {count}", rs, F_4D3CA0,
                             args=tuple(words(rs, 5)) + (rs.choice((0, 0x100000, 0x400000)),), fail_new=(2,), results=results,
                             items=tuple(range(count)))
    # the create stub changes what the owned function reads afterwards
    def swap_sub(env, manager, nodes):
        replacement = junk(env, rs, 0x20, "replacement-sub")
        env.put(replacement + 0x10, env.stub("replacement-callback", "cdecl", 1, returns(0)))

        def edit(env, call):
            env.put(call.receiver + 0x6C, replacement)
        return edit

    def clear_flag(env, manager, nodes):
        return lambda env, call: env.put(call.receiver + 8, 0x1234)

    def raise_flag(env, manager, nodes):
        return lambda env, call: env.put(call.receiver + 8, 0x200000)

    for edit, name in ((swap_sub, "sub replaced"), (clear_flag, "flag cleared"), (raise_flag, "flag raised")):
        for flag in (0, 0x200000):
            yield child_case(f"child create edit: {name} flag {flag:#x}", rs, F_4D3CA0, args=tuple(words(rs, 5)) + (flag,),
                             create_edit=edit)


def sorted_cases(rs):
    rel = {"lt": -1, "eq": 0, "gt": 1}
    # deterministic enumeration of every walk shape: up to two nodes, any relation and flag combination
    shapes = [()]
    for r1 in rel:
        for f1 in (0, 2):
            shapes.append(((r1, f1),))
            for r2 in rel:
                for f2 in (0, 2):
                    shapes.append(((r1, f1), (r2, f2)))
    for r1 in rel:
        for f1 in (0, 2):
            for r2 in rel:
                for f2 in (0, 2):
                    shapes.append(((r1, f1), (r2, f2), ("gt", 0)))   # 1 + 6 + 36 + 36 shapes
    for shape in shapes:
        mine = rs.randrange(-50, 50)
        depths = [(mine + rel[r] * rs.randrange(1, 9)) if r != "eq" else mine for r, _ in shape]
        flags = [f | (rs.randrange(0, 64) << 2) & ~2 if f == 0 else f | (rs.randrange(0, 64) << 2) for _, f in shape]
        flags = [(f if f2 else f & ~2) for f, (_, f2) in zip(flags, shape)]
        label = "sorted walk " + ",".join(f"{r}{'F' if f else ''}" for r, f in shape)
        yield sorted_case(label, rs, F_4C8E00, args=(rs.randrange(1, 1 << 32), 0x71, 0x72, mine & M32, 0x74, rs.choice((0, 0x200000))),
                          items=tuple(range(len(shape))), item_depths=[d & M32 for d in depths], item_flags=flags, depth=mine & M32,
                          free=rs.randrange(0, 2))
    # signed comparison of the depths
    for item_depth, mine in ((0xFFFFFFFF, 1), (1, 0xFFFFFFFF), (0x80000000, 0x7FFFFFFF), (0x7FFFFFFF, 0x80000000), (0xFFFFFFFE, 0xFFFFFFFF),
                             (0xFFFFFFFF, 0xFFFFFFFE), (0, 0xFFFFFFFF), (0xFFFFFFFF, 0)):
        yield sorted_case(f"sorted signed depths {item_depth:#x} {mine:#x}", rs, F_4C8E00, args=(1, 2, 3, mine, 5, 0),
                          items=(0,), item_depths=[item_depth], item_flags=[0], depth=mine)
    # flag byte: only bit 1 of the byte at +0xa matters
    for flag in (0, 1, 2, 3, 0x80, 0xFD, 0xFF, 0x82):
        yield sorted_case(f"sorted flag byte {flag:#x}", rs, F_4C8E00, args=(1, 2, 3, 5, 5, 0), items=(0, 1), item_depths=[9, 3],
                          item_flags=[flag, 0], depth=5)
    # insertion into the middle, flagged blockers skipped
    yield sorted_case("sorted middle insert", rs, F_4C8E00, args=(1, 2, 3, 5, 5, 0), items=(0, 1, 2, 3), item_depths=[1, 3, 9, 12],
                      item_flags=[0, 0, 0, 0], depth=5)
    yield sorted_case("sorted skip flagged then insert", rs, F_4C8E00, args=(1, 2, 3, 5, 5, 0), items=(0, 1, 2, 3),
                      item_depths=[9, 9, 9, 12], item_flags=[2, 6, 0, 0], depth=5)
    yield sorted_case("sorted all flagged: append", rs, F_4C8E00, args=(1, 2, 3, 5, 5, 0), items=(0, 1, 2), item_depths=[9, 9, 9],
                      item_flags=[2, 2, 2], depth=5)
    # the create stub's result and flags
    for results in ((0,), (1,), (0x80000000,)):
        for flag in (0, 0x200000, 0xFFFFFFFF):
            yield sorted_case(f"sorted results {results[0]:#x} flag {flag:#x}", rs, F_4C8E00,
                              args=(0x61, 0x62, 0x63, 0x64, 0x65, flag), results=results, items=(0, 1), item_depths=[3, 90],
                              item_flags=[0, 0], depth=0x40)
    yield sorted_case("sorted arguments distinct", rs, F_4C8E00, args=(0x11111111, 0x22222222, 0x33333333, 0x44444444, 0x55555555, 0x200000),
                      depth=0x44444444)
    # the first allocation failing makes the original read address 0 (0x4c8ecb), so it is not a case; the sub object
    # allocation failing is fine while the 0x200000 callback is not called
    for results in ((1,), (0,)):
        yield sorted_case(f"sorted sub-object allocation fails result {results[0]}", rs, F_4C8E00, args=tuple(words(rs, 5)) + (0,),
                          fail_new=(2,), depth=3, results=results, items=(0,), item_depths=[8], item_flags=[0])
    for flag in (0, 0x200000):
        for free in (0, 1, 3):
            for blocksize in (1, 4):
                yield sorted_case(f"sorted free {free} block {blocksize} flag {flag:#x}", rs, F_4C8E00,
                                  args=tuple(words(rs, 5)) + (flag,), items=(0, 1), item_depths=[1, 9], item_flags=[0, 0], depth=4,
                                  free=free, blocksize=blocksize)

    def swap_sub(env, manager, nodes):
        replacement = junk(env, rs, 0x20, "replacement-sub")
        env.put(replacement + 0x10, env.stub("replacement-callback", "cdecl", 1, returns(0)))
        return lambda env, call: env.put(call.receiver + 0x6C, replacement)

    def drop_list(env, manager, nodes):
        return lambda env, call: env.put(manager + 0x14, 0)

    def move_head(env, manager, nodes):
        return lambda env, call: env.put(manager + 0x14, nodes[-1]) if nodes else None

    def flag_word(env, manager, nodes):
        return lambda env, call: env.put(call.receiver + 8, 0x200000)

    for edit, name in ((swap_sub, "sub replaced"), (drop_list, "list emptied"), (move_head, "head moved"), (flag_word, "flag word")):
        for flag in (0, 0x200000):
            yield sorted_case(f"sorted create edit: {name} flag {flag:#x}", rs, F_4C8E00, args=tuple(words(rs, 3)) + (5, 0, flag),
                              items=(0, 1, 2), item_depths=[1, 9, 10], item_flags=[0, 0, 0], depth=5, create_edit=edit)


# ---------------------------------------------------------------------------------------------------------------
# the lookup wrappers 0x4d3e50 and 0x4c8f60
def wrapper_cases(rs):
    for function, maker, label in ((F_4D3E50, child_case, "child"), (F_4C8F60, sorted_case, "sorted")):
        names = [b"Alpha", b"Beta", b"Gamma", b"Delta", b"LongerKeyName"]
        for buckets in (1, 2, 3, 7, 29):
            for key in (b"Alpha", b"Gamma", b"LongerKeyName"):
                a = tuple(words(rs, 4))
                yield maker(f"{label} wrapper found {key.decode()} buckets {buckets}", rs, function,
                            args=(a[0], a[1], a[2], a[3], "key", 0x200000), entries=names, buckets=buckets, with_key=key, depth=a[2])
        for key in (b"Missing", b"Alph", b"AlphaX", b"alpha", b""):
            yield maker(f"{label} wrapper missing {key!r}", rs, function, args=tuple(words(rs, 4)) + ("key", 0x200000),
                        entries=names, with_key=key)
        yield maker(f"{label} wrapper record is null", rs, function, args=tuple(words(rs, 4)) + ("key", 0x200000), entries=names,
                    with_key=b"Beta", record_value=False)
        yield maker(f"{label} wrapper empty registry", rs, function, args=tuple(words(rs, 4)) + ("key", 0), entries=[], with_key=b"Beta")
        for flag in (0, 0x200000):
            for results in ((1,), (0,)):
                yield maker(f"{label} wrapper arguments distinct flag {flag:#x} result {results[0]}", rs, function,
                            args=(0x11111111, 0x22222222, 0x33333333, 0x44444444, "key", flag), entries=names, with_key=b"Delta",
                            results=results, depth=0x33333333)
        # EAX on every path: not found (0), found with the created object, found with a failed create (0)
        for flag in (0, 0x200000):
            for key, results, state in ((b"Missing", (1,), "missing"), (b"Gamma", (1,), "created"), (b"Gamma", (0,), "create fails")):
                yield maker(f"{label} wrapper eax {state} flag {flag:#x}", rs, function,
                            args=tuple(words(rs, 4)) + ("key", flag), entries=names, with_key=key, results=results,
                            depth=rs.randrange(-9, 9) & M32, items=(0, 1), item_depths=[3, 8], item_flags=[0, 0])
        if label == "child":
            yield maker(f"{label} wrapper allocation fails", rs, function, args=tuple(words(rs, 4)) + ("key", 0x200000), entries=names,
                        with_key=b"Alpha", fail_new=(1,))
        yield maker(f"{label} wrapper sub-object allocation fails", rs, function, args=tuple(words(rs, 4)) + ("key", 0), entries=names,
                    with_key=b"Alpha", fail_new=(2,), depth=6)
        yield maker(f"{label} wrapper list populated", rs, function, args=tuple(words(rs, 4)) + ("key", 0x200000), entries=names,
                    with_key=b"Alpha", items=(0, 1, 2), item_depths=[1, 5, 9], item_flags=[0, 0, 0], depth=4)


# ---------------------------------------------------------------------------------------------------------------
# real children: the static vtable is left alone, the original initialises the child from a record
def real_cases(rs):
    for flags in (0, 1, 2, 3, 4, 0x81):
        for arg6 in (0, 0x200000, 0x12345678):
            yield child_case(f"real child record flags {flags:#x} arg {arg6:#x}", rs, F_4D3CA0,
                             args=(0x41, 0x42, 0x43, 0x44, "record", arg6), real=True, record_flags=flags, items=(0,))
    for flags in (0, 1, 2, 3):
        for arg6 in (0, 0x200000):
            yield sorted_case(f"real sorted record flags {flags:#x} arg {arg6:#x}", rs, F_4C8E00,
                              args=(0x41, 0x42, 0x43, 0x44, "record", arg6), real=True, record_flags=flags)
    # wrapper through the registry
    names = [b"Alpha", b"Beta"]
    for function, maker, label in ((F_4D3E50, child_case, "child"), (F_4C8F60, sorted_case, "sorted")):
        for flag in (0, 0x200000):
            yield maker(f"real {label} wrapper flag {flag:#x}", rs, function, args=(1, 2, 3, 4, "key", flag), entries=names,
                        with_key=b"Beta", real=True, record_flags=3)
    # A record without callback makes the original initialiser fail and the original destructor then reaches
    # operator delete -> HeapFree, which has no stand-in, so that path is only covered through the stubbed vtable.


# ---------------------------------------------------------------------------------------------------------------
# 0x491ed0
def manager_owner_setup(rs, state, real=False, entries=None, results=(1,), items=(), free=0, blocksize=None, create_edit=None,
                        fail_new=(), p_flags=None, sub_fn=True, record_flags=1, record_fn=True, depth=None):
    def setup(env):
        log = new_log(env)
        fn = logged(env, log, 0xF1, "record-callback", "cdecl", 1) if record_fn else 0
        made = [make_item(env, rs, fn=logged(env, log, 0xE0 + i, f"item-callback-{i}", "cdecl", 1)) for i in range(len(items))]
        registry = None
        if entries is not None:
            registry = make_registry(env, rs, {n: make_record(env, rs, record_flags, fn) if n else 0 for n in entries},
                                     rs.randrange(1, 9))
        manager, nodes = make_manager(env, rs, list_at=0x1B4, items=made, free=free, blocksize=blocksize, registry=registry)
        record_ = junk(env, rs, 0x30, "state-record")
        env.put(record_ + 0x1C, state)
        env.put(manager + 0x6C, record_)
        if p_flags is not None:
            env.put(manager + 8, p_flags)
        env.put(G_MANAGER, rs.randrange(1, 1 << 32))
        if not real:
            stub = logged(env, log, 0xF2, "child-callback", "cdecl", 1) if sub_fn else None
            create_stub(env, log, VT_CHILD, results=results, sub_fn=stub,
                        edit=None if create_edit is None else create_edit(env, manager, nodes))
            delete_stub(env, log, VT_CHILD)
        if fail_new:
            def deny(env, call):
                if env.calls_so_far(call.function) in fail_new:
                    return 0
                return env.object(call.arguments[0], name="allocation")
            env.override(OPERATOR_NEW, deny)
        return {"manager": manager, "log": log, "state": record_, "nodes": nodes}
    return setup


def owner_case(label, rs, **o):
    state = o.pop("state", 0)
    return Case(label, F_491ED0, manager_owner_setup(rs, state, **o), arguments=(lambda t: t["manager"],))


def owner_cases(rs):
    # state 0: every subset of the five registry entries, keys taken from the original's own strings
    for mask in range(32):
        yield Case(f"state 0 frames {mask:05b}", F_491ED0, _frames_setup(rs, mask), arguments=(lambda t: t["manager"],))
    for results in ((1, 0), (0, 1), (0, 0), (1, 1, 0, 1, 1), (1, 1, 1, 1, 0), (5,)):
        yield Case(f"state 0 all frames results {results}", F_491ED0, _frames_setup(rs, 31, results=results),
                   arguments=(lambda t: t["manager"],))
    for free in (0, 1, 3, 6):
        for blocksize in (1, 2, 10):
            yield Case(f"state 0 all frames free {free} block {blocksize}", F_491ED0,
                       _frames_setup(rs, 31, free=free, blocksize=blocksize, preexisting=rs.randrange(0, 3)),
                       arguments=(lambda t: t["manager"],))
    yield Case("state 0 allocation fails first", F_491ED0, _frames_setup(rs, 31, fail_new=(1,)), arguments=(lambda t: t["manager"],))
    yield Case("state 0 sub-object allocation fails", F_491ED0, _frames_setup(rs, 15, fail_new=(2,)), arguments=(lambda t: t["manager"],))
    yield Case("state 0 no frames, allocation unused", F_491ED0, _frames_setup(rs, 0, fail_new=(1, 2, 3, 4, 5, 6)),
               arguments=(lambda t: t["manager"],))
    yield Case("state 0 real frames", F_491ED0, _frames_setup(rs, 31, real=True), arguments=(lambda t: t["manager"],))
    yield Case("state 0 real frames, records flags", F_491ED0, _frames_setup(rs, 31, real=True, record_flags=3),
               arguments=(lambda t: t["manager"],))
    # state 5 walks the list
    for count in (0, 1, 2, 5):
        yield owner_case(f"state 5 walks {count} items", rs, state=5, items=tuple(range(count)))
    for state in (1, 2, 4, 6, 0xFF, 0x80000000, 0xFFFFFFFF):
        yield owner_case(f"state {state:#x} does nothing", rs, state=state, items=(0, 1), p_flags=rs.randrange(0, 1 << 32))


def _frames_setup(rs, mask, results=(1,), free=0, blocksize=None, fail_new=(), real=False, record_flags=1, preexisting=0):
    def setup(env):
        log = new_log(env)
        names = [env.cstr(addr) for addr in FRAME_KEYS]
        fn = logged(env, log, 0xF1, "record-callback", "cdecl", 1)
        table = {names[i]: make_record(env, rs, record_flags, fn) for i in range(5) if mask >> i & 1}
        registry = make_registry(env, rs, table, rs.randrange(1, 9))
        made = [make_item(env, rs, fn=fn) for _ in range(preexisting)]
        manager, nodes = make_manager(env, rs, list_at=0x1B4, items=made, free=free, blocksize=blocksize, registry=registry)
        record_ = junk(env, rs, 0x30, "state-record")
        env.put(record_ + 0x1C, 0)
        env.put(manager + 0x6C, record_)
        env.put(manager + 8, rs.randrange(0, 1 << 32) & ~1)
        env.put(G_MANAGER, rs.randrange(1, 1 << 32))
        if not real:
            create_stub(env, log, VT_CHILD, results=results, sub_fn=logged(env, log, 0xF2, "child-callback", "cdecl", 1))
            delete_stub(env, log, VT_CHILD)
        if fail_new:
            def deny(env, call):
                if env.calls_so_far(call.function) in fail_new:
                    return 0
                return env.object(call.arguments[0], name="allocation")
            env.override(OPERATOR_NEW, deny)
        return {"manager": manager, "log": log, "state": record_}
    return setup


# ---------------------------------------------------------------------------------------------------------------
# 0x4d3ef0 and 0x4d3f20
def walk_setup(rs, count, tamper=None, vt_mode=True):
    def setup(env):
        log = new_log(env)
        items = []
        for index in range(count):
            vt = junk(env, rs, 0x40, "item-vtable")
            fn = logged(env, log, 0x10 + index, f"item-callback-{index}", "cdecl", 1, result=rs.randrange(0, 1 << 32))
            method = logged(env, log, 0x40 + index, f"item-method-{index}", "thiscall", 1, result=rs.randrange(0, 1 << 32))
            item = make_item(env, rs, fn=fn, vt=vt)
            env.put(vt + 0x2C, method)
            items.append(item)
        manager, nodes = make_manager(env, rs, list_at=0x1B4, items=items, free=rs.randrange(0, 2))
        if tamper and count >= 2:
            spare = make_item(env, rs, fn=logged(env, log, 0x90, "spare-callback", "cdecl", 1))
            spare_vt = junk(env, rs, 0x40, "spare-vtable")
            env.put(spare_vt + 0x2C, logged(env, log, 0x91, "spare-method", "thiscall", 1))
            env.put(spare, spare_vt)
            first = items[0]
            if tamper == "item-of-next":
                # the first callback redirects the second node to a different item
                def effect(env, call):
                    record(env, log, 0x10, call.receiver, call.arguments)
                    env.put(nodes[1] + 8, spare)
                    return 3
                sub = env.get(first + 0x6C)
                env.put(sub + 0x10, env.stub("tamper-callback", "cdecl", 1, effect))

                def method_effect(env, call):
                    record(env, log, 0x40, call.receiver, call.arguments)
                    env.put(nodes[1] + 8, spare)
                    return 4
                env.put(env.get(first) + 0x2C, env.stub("tamper-method", "thiscall", 1, method_effect))
            elif tamper == "next-of-current":
                # redirecting the current node's link must not matter: it was read before the call
                def effect(env, call):
                    record(env, log, 0x10, call.receiver, call.arguments)
                    env.put(nodes[0], 0)
                    return 3
                sub = env.get(first + 0x6C)
                env.put(sub + 0x10, env.stub("tamper-callback", "cdecl", 1, effect))

                def method_effect(env, call):
                    record(env, log, 0x40, call.receiver, call.arguments)
                    env.put(nodes[0], 0)
                    return 4
                env.put(env.get(first) + 0x2C, env.stub("tamper-method", "thiscall", 1, method_effect))
            elif tamper == "next-of-next":
                def effect(env, call):
                    record(env, log, 0x10, call.receiver, call.arguments)
                    env.put(nodes[1], 0)
                    return 3
                sub = env.get(first + 0x6C)
                env.put(sub + 0x10, env.stub("tamper-callback", "cdecl", 1, effect))

                def method_effect(env, call):
                    record(env, log, 0x40, call.receiver, call.arguments)
                    env.put(nodes[1], 0)
                    return 4
                env.put(env.get(first) + 0x2C, env.stub("tamper-method", "thiscall", 1, method_effect))
        return {"manager": manager, "log": log, "items": items}
    return setup


def walk_cases(rs):
    for count in range(0, 7):
        yield Case(f"count walk {count} items", F_4D3EF0, walk_setup(rs, count), receiver=lambda t: t["manager"])
        yield Case(f"notify walk {count} items", F_4D3F20, walk_setup(rs, count), receiver=lambda t: t["manager"],
                   arguments=(rs.randrange(0, 1 << 32),))
    for tamper in ("item-of-next", "next-of-current", "next-of-next"):
        for count in (2, 3, 4):
            yield Case(f"count walk tamper {tamper} {count}", F_4D3EF0, walk_setup(rs, count, tamper=tamper), receiver=lambda t: t["manager"])
            yield Case(f"notify walk tamper {tamper} {count}", F_4D3F20, walk_setup(rs, count, tamper=tamper),
                       receiver=lambda t: t["manager"], arguments=(0xA5A5A5A5,))
    for value in (0, 1, 0x80000000, 0xFFFFFFFF, 0x12345678):
        yield Case(f"notify argument {value:#x}", F_4D3F20, walk_setup(rs, 2), receiver=lambda t: t["manager"], arguments=(value,))


def cases(random_source):
    rs = random_source
    yield from timer_cases(rs)
    yield from owner_cases(rs)
    yield from walk_cases(rs)
    yield from child_cases(rs)
    yield from wrapper_cases(rs)
    yield from sorted_cases(rs)
    yield from real_cases(rs)
