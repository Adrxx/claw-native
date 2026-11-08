"""Cases for path_elevator: PathElevator object logic."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

ENTRY = 0x49EE30
OPERATOR_NEW = 0x4F63EC
G_TABLE = 0x537960     # pointer to a table of 4-word records at +0x68 and +0x98
G_LEVEL = 0x5371FC     # pointer to a record whose +0x2c holds a record with the level number at +0x14
G_TIME = 0x537210      # the global time value passed to the per-frame step
KEY_STRING = 0x528A4C  # "LEVEL_TRAPELEVATOR"
VTABLE = 0x50FEE4


def hash_of(text, buckets):
    h = 0
    for ch in text:
        c = ch - 256 if ch >= 128 else ch
        h = (h * 0x21 + c) & 0xFFFFFFFF
    return h % buckets


def words(random_source, n):
    return [random_source.randrange(1, 0x7FFF) for _ in range(n)]


def build(random_source, state=0, kind=1, state_ptr=0, period=None, rect=True, level=10,
          trap_id=None, found=True, buckets=7, fields=None, flags=0x24, owner_zero=False,
          time=None, elevator=None, wrap=False):
    """setup() for one object plus the globals the function reads."""
    def setup(env):
        r = random_source
        info = env.object(0xC8, "info", words=[r.randrange(1, 99) for _ in range(50)])
        env.put(info + 0xBC, period if period is not None else r.randrange(1, 400))
        env.put(info + 0x1C, state)
        env.put(info + 0x18, state_ptr)
        obj = env.object(0x180, "object", words=words(r, 0x60))
        env.put(obj + 0x6C, info)
        env.put(obj + 0x08, flags)
        env.put(obj + 0x100, kind)
        env.put(obj + 0x110, r.randrange(1, 1000))
        env.put(obj + 0xD0, r.randrange(1, 999))
        env.put(obj + 0x158, r.randrange(1, 500))
        env.put(obj + 0x15C, r.randrange(1, 500))
        # rectangle record: +0x18 left, +0x1c top, +0x20 right, +0x24 bottom
        if rect:
            box = env.object(0x30, "rect", words=words(r, 12))
            env.put(obj + 0x174, box)
        else:
            env.put(obj + 0x174, 0)
        # lookup chain: obj+0xc -> +0x10 -> map at +0x10 (+4 buckets, +8 count)
        key = bytes(env.read(KEY_STRING, 18))
        table_id = trap_id if trap_id is not None else r.randrange(1, 40)
        env.put(obj + 0x170, table_id)
        outer = env.object(0x20, "outer", words=words(r, 8))
        middle = env.object(0x40, "middle", words=words(r, 16))
        env.put(obj + 0xC, outer)
        env.put(outer + 0x10, middle)
        slots = env.object(buckets * 4, "buckets", fill=0)
        env.put(middle + 0x10 + 8, buckets)
        env.put(middle + 0x10 + 4, slots)
        if found:
            name = env.object(32, "name", data=key + b"\0")
            entry = env.object(16, "entry", words=[0, 0, name, table_id if trap_id is None else trap_id])
            decoy_name = env.object(32, "decoy-name", data=b"OTHER\0")
            decoy = env.object(16, "decoy", words=[entry, 0, decoy_name, 12345])
            env.put(slots + 4 * hash_of(key, buckets), decoy)
        table = env.object(0xB0, "table", words=words(r, 44))
        env.put(G_TABLE, table)
        level_a = env.object(0x40, "levela", words=words(r, 16))
        level_b = env.object(0x20, "levelb", words=words(r, 8))
        env.put(level_a + 0x2C, level_b)
        env.put(level_b + 0x14, level)
        env.put(G_LEVEL, level_a)
        env.put(G_TIME, time if time is not None else r.randrange(0, 5000))
        if fields:
            for offset, value in fields.items():
                env.put(obj + offset, value)
        if elevator is not None:
            elevator(env, obj, info)
        return {"obj": obj, "info": info, "table": table}
    return setup


def entry(label, setup):
    return Case(label, ENTRY, setup, arguments=(lambda t: t["obj"],))


def mover(random_source, count, kinds, periods=(100,), total_only=False):
    """An already-built elevator: owner back pointer, step list, period, offset."""
    def make(env, obj, info):
        r = random_source
        steps = env.object(0x104, "steps", fill=0)
        for i, (k, d) in enumerate(zip(kinds, [r.randrange(20, 400) for _ in kinds])):
            env.put(steps + 4 * i, k)
            env.put(steps + 0x80 + 4 * i, d)
        env.put(steps + 0x100, count)
        elev = env.object(0x18, "elevator", fill=0)
        env.put(elev, VTABLE)
        env.put(elev + 4, obj)
        env.put(elev + 8, steps)
        env.put(elev + 0xC, periods[0])
        env.put(elev + 0x10, r.randrange(1, 3000))
        env.put(elev + 0x14, r.randrange(0, 700))
        env.put(obj + 0x4C, r.randrange(-500, 500) & 0xFFFFFFFF)
        env.put(obj + 0x50, r.randrange(-500, 500) & 0xFFFFFFFF)
        env.put(obj + 0xE8, r.randrange(-50, 50) & 0xFFFFFFFF)
        env.put(obj + 0xEC, r.randrange(-50, 50) & 0xFFFFFFFF)
        env.put(obj + 0x6C, info)
        env.put(info + 0x18, elev)
    return make


def cases(random_source):
    yield from base_cases(random_source)
    yield from dirty_cases(random_source)
    yield from dirty_cases_2(random_source)


def base_cases(random_source):
    r = random_source
    # state 0: initialisation, by object kind and by what the step builders accept
    for kind in (1, 2, 3, 0, -1, 99):
        yield entry(f"init kind {kind}", build(r, kind=kind))
    for kind in (1, 2):
        for period in (0, 1, 100, 1000):
            yield entry(f"init kind {kind} period {period}", build(r, kind=kind, period=period))
    # kind 3 with a usable set of fields, so the second builder succeeds in several ways
    good = {0x118: 40, 0x11C: 25, 0x120: 30, 0x124: 20, 0x128: 10, 0x12C: 15, 0x130: 5, 0x134: 9,
            0x138: 3, 0x13C: 4, 0x140: 6, 0x144: 7, 0x54: 8, 0x58: 11, 0x5C: 12, 0x60: 13}
    yield entry("init generic with full step fields", build(r, kind=3, fields=dict(good)))
    yield entry("init generic with full step fields, no rect", build(r, kind=3, fields=dict(good), rect=False))
    yield entry("init generic with full step fields, not found", build(r, kind=3, fields=dict(good), found=False, level=10))
    for off in (0x118, 0x11C, 0x120, 0x124, 0x128, 0x12C, 0x130, 0x134, 0x138, 0x13C, 0x140, 0x144, 0x54, 0x58, 0x5C, 0x60):
        fields = dict(good)
        fields[off] = 0
        yield entry(f"init generic field {off:#x} zero", build(r, kind=3, fields=fields))
    fields = dict(good)
    fields[0x118] = 0x80000000
    yield entry("init generic first extent is the minimum int", build(r, kind=3, fields=fields))
    # the extents are rejected, so the generic kind builds nothing and the state becomes 5
    for kind in (3, 0, 99):
        yield entry(f"init kind {kind} with zero first extent: state 5", build(r, kind=kind, fields={0x118: 0}))
        yield entry(f"init kind {kind} with zero second extent: state 5", build(r, kind=kind, fields={0x118: 9, 0x11C: 0}))
    def first_fails(env):
        tokens = build(r, kind=3, fields={0x118: 0})(env)
        env.override(OPERATOR_NEW, allocate(fail_from_call=1))
        return tokens
    yield entry("first allocation fails, builders skipped", first_fails)
    def all_fail(env):
        tokens = build(r, kind=3, fields={0x118: 0})(env)
        env.override(OPERATOR_NEW, allocate(fail=True))
        return tokens
    yield entry("both allocations fail", all_fail)
    # level 10 trap elevator table override
    for level, trap_id, found in ((10, 5, True), (10, 5, False), (10, 0, False), (10, 0, True),
                                   (9, 5, True), (11, 5, True), (0, 5, True), (-10, 5, True)):
        yield entry(f"level {level} id {trap_id} found {found}", build(r, level=level, trap_id=trap_id, found=found))
    for buckets in (1, 2, 3, 13, 101):
        yield entry(f"level 10 lookup in {buckets} buckets", build(r, level=10, buckets=buckets))
    yield entry("level 10, entry value differs from id", build(r, level=10, trap_id=None))
    # rect handling
    yield entry("no rect pointer", build(r, rect=False))
    # flags
    for flags in (0, 1, 0x24, 0xFFFFFFFE, 0xFFFFFFFF):
        yield entry(f"flags {flags:#x}", build(r, flags=flags))
    # wrap of the +0x134 increment
    yield entry("0x134 increment from a negative value", build(r, level=0, fields={0x134: 0xFFFFFFF0}))
    # a failing second allocation faults in the original (it stores through a null this), so it has no case
    # state 1: per-frame step
    for kinds, count in (([6, 7], 2), ([1, 2, 3, 4, 5], 5), ([6, 7, 5, 6, 1, 8, 9], 7), ([2], 1), ([], 0)):
        for time in (0, 1, 77, 450, 100000):
            yield entry(f"step {kinds} time {time}", build(r, state=1, state_ptr=1, time=time,
                        elevator=mover(r, count, kinds)))
    for period in (1, 50, 100, 997):
        yield entry(f"step period {period}", build(r, state=1, state_ptr=1, elevator=mover(r, 4, [6, 7, 1, 3], periods=(period,))))
    def big_move(env, obj, info):
        mover(r, 2, [6, 9])(env, obj, info)
        steps = env.get(env.get(info + 0x18) + 8)
        env.put(steps + 0x80, 60)
        env.put(steps + 0x84, 60)
    yield entry("step with large displacement", build(r, state=1, state_ptr=1, time=40, elevator=big_move))
    def huge_move(env, obj, info):
        mover(r, 1, [6])(env, obj, info)
        elev = env.get(info + 0x18)
        steps = env.get(elev + 8)
        env.put(steps, 6)
        env.put(steps + 0x80, 0x7FFF)
        env.put(elev + 0x14, 0)
    yield entry("step displacement above the clamp", build(r, state=1, state_ptr=1, time=0, elevator=huge_move))
    yield entry("state 1 with no elevator", build(r, state=1, state_ptr=0))
    for state in (2, 3, 5, 7, 0xFFFFFFFF, 0x80000000):
        yield entry(f"state {state:#x} does nothing", build(r, state=state, state_ptr=0))
        yield entry(f"state {state:#x} with a pointer", build(r, state=state, state_ptr=0x1234))
    for _ in range(25):
        kind = r.choice((1, 2, 3, 7))
        yield entry(f"random init {kind}", build(r, kind=kind, level=r.choice((9, 10, 10, 11)),
                                                  found=r.choice((True, False)), rect=r.choice((True, False)),
                                                  buckets=r.randrange(1, 30), fields=dict(good) if r.random() < 0.5 else None))
    for _ in range(15):
        count = r.randrange(1, 6)
        kinds = [r.randrange(1, 10) for _ in range(count)]
        yield entry(f"random step {kinds}", build(r, state=1, state_ptr=1, time=r.randrange(0, 20000),
                                                  elevator=mover(r, count, kinds, periods=(r.randrange(1, 500),))))


def dirty_allocate(fill, only_size=None):
    """The allocator, but fresh objects hold a non-zero pattern, so a missing store shows."""
    def effect(env, call):
        size = call.arguments[0]
        return env.object(size, name="allocation", fill=fill if only_size in (None, size) else 0)
    return effect


def dirty_cases(random_source):
    r = random_source
    good = {0x118: 40, 0x11C: 25, 0x120: 30, 0x124: 20, 0x128: 10, 0x12C: 15, 0x130: 5, 0x134: 9,
            0x138: 3, 0x13C: 4, 0x140: 6, 0x144: 7, 0x54: 8, 0x58: 11, 0x5C: 12, 0x60: 13}
    for fill in (0xA5, 0x5A, 0xFF):
        for only in (None, 0x18, 0x104):
            for kind, fields in ((1, None), (2, None), (3, dict(good)), (3, {0x118: 0}), (0, None)):
                def make(kind=kind, fields=fields, fill=fill, only=only):
                    def setup(env):
                        tokens = build(r, kind=kind, fields=fields)(env)
                        env.override(OPERATOR_NEW, dirty_allocate(fill, only))
                        return tokens
                    return setup
                yield entry(f"dirty allocation fill {fill:#x} size {only} kind {kind} fields {bool(fields)}", make())


def first_fails_then_dirty(fill):
    """The first allocation fails; the second succeeds with a non-zero pattern in it."""
    def effect(env, call):
        if env.calls_so_far(call.function) == 1:
            return 0
        return env.object(call.arguments[0], name="allocation", fill=fill)
    return effect


def dirty_cases_2(random_source):
    r = random_source
    for fill in (0xA5, 0x3C, 0xFF):
        for kind in (3, 0):
            def make(kind=kind, fill=fill):
                def setup(env):
                    tokens = build(r, kind=kind, fields={0x118: 0})(env)
                    env.override(OPERATOR_NEW, first_fails_then_dirty(fill))
                    return tokens
                return setup
            yield entry(f"first allocation fails, elevator memory dirty {fill:#x}, kind {kind}", make())
