"""Cases for level_one_object_actions_03: Observed Level 1 level object actions batch 3."""
from clawparity.cases import Case
from clawparity.fixtures import returns

CLEAR_AND_WALK = 0x46CAF0
COUNT_OBJECT = 0x46CB40
CLASSIFY_A = 0x46D520
NAME_OF = 0x473630
RUN_ACTION = 0x473660
FLAG_OBJECT = 0x473AE0
CLASSIFY_B = 0x473B10
STEP_TOWARD = 0x486940

COUNT = 0x52A190
TABLE = 0x537EC8
TABLE2 = 0x538208
TALLY = 0x5381E0
FALLBACK = 0x5279B8
SNAP_X = 0x52BE14
SNAP_Y = 0x52BE18
SCALE = 0x5430C4
TABLE_MAX = (TABLE2 - TABLE) // 4

H_IGNORED = 0x49EE30
H_A, H_B, H_C = 0x471530, 0x471720, 0x471750
H_INDIRECT = (0x46FD10, 0x470100, 0x470430, 0x471330, 0x470D00, 0x470F00, 0x471100)

# index -> class, as the original switch maps it; everything else is -1
CLASS_OF = {1: 1, 2: 2, 3: 2, 4: 2, 5: 2, 7: 4, 8: 4, 9: 4, 10: 4, 11: 5, 12: 5, 13: 5, 14: 5,
            15: 6, 16: 6, 17: 6, 18: 6, 0x21: 0, 0x29: 3, 0x2A: 3, 0x2B: 3, 0x2C: 3,
            0x2D: 7, 0x2E: 7, 0x2F: 7, 0x30: 7, 0x31: 8, 0x32: 8, 0x33: 8, 0x34: 8}
SWEEP = list(range(-2, 0x39)) + [0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x100, 0x21 + 0x100, 0x1000021]
REPRESENTATIVES = [0, 1, 2, 5, 6, 7, 0xB, 0xF, 0x13, 0x21, 0x29, 0x2D, 0x31, 0x34, 0x35, 0xFFFFFFFF]


def word(rnd):
    return rnd.randrange(1, 1 << 32)


def preload_tally(env, rnd):
    values = [rnd.randrange(1, 1000) for _ in range(9)]
    env.put(TALLY, *values)
    return values


# ----------------------------------------------------------------- 0x46d520 / 0x473b10

def classify_a_case(value):
    return Case(f"46d520 value {value:#x}", CLASSIFY_A, None, arguments=(value & 0xFFFFFFFF,))


def table_setup(count, entries, extra=None):
    """Global object table with `count` entries (unsigned view stored as given) and the supplied pointers."""
    def setup(env):
        env.put(COUNT, count & 0xFFFFFFFF)
        for i, entry in enumerate(entries):
            env.put(TABLE + 4 * i, entry)
        if extra:
            extra(env)
        return {}
    return setup


def classify_b_case(label, count, entries, argument):
    return Case(label, CLASSIFY_B, table_setup(count, entries), arguments=(argument,))


# ----------------------------------------------------------------- 0x46cb40

def build_subject(env, rnd, handler, kind=5, index=0x21, pointer_field=0, second=None,
                  with_handler_object=True):
    handler_object = env.object(0x120, "handler", fill=0)
    for off in range(0, 0x120, 4):
        env.put(handler_object + off, word(rnd))
    env.put(handler_object + 0x10, handler)
    for off, value in (second or {}).items():
        env.put(handler_object + off, value)
    methods = env.object(0x40, "vtable", fill=0)
    env.put(methods + 0x20, env.stub("virtual kind", "thiscall", 0, returns(kind)))
    subject = env.object(0x180, "subject", fill=0)
    for off in range(0, 0x180, 4):
        env.put(subject + off, word(rnd))
    env.put(subject, methods)
    env.put(subject + 0x6c, handler_object if with_handler_object else 0)
    env.put(subject + 0x100, index & 0xFFFFFFFF)
    env.put(subject + 0x170, pointer_field)
    return subject, handler_object


def count_setup(rnd, handler, kind=5, index=0x21, pointer_field=0, second=None, vtable_slot=True,
                with_handler_object=True, table=None, table_count=None):
    """An object with a vtable whose +0x20 method returns `kind`, a handler object at +0x6c with the
    function pointer `handler` at +0x10, type index at +0x100 and the table lookup pointer at +0x170."""
    def setup(env):
        preload_tally(env, rnd)
        if table is not None:
            env.put(COUNT, len(table) if table_count is None else table_count)
            for i, entry in enumerate(table):
                env.put(TABLE + 4 * i, entry)
        else:
            env.put(COUNT, 0)
        subject, handler_object = build_subject(env, rnd, handler, kind, index, pointer_field, second,
                                                with_handler_object)
        return {"subject": subject, "handler": handler_object}
    return setup


def count_case(label, setup):
    return Case(label, COUNT_OBJECT, setup, arguments=(lambda t: t["subject"],))


# ----------------------------------------------------------------- 0x486940

def step_setup(rnd, x, y, tx, ty, snap=None, scale=1000):
    def setup(env):
        pair = env.object(0x20, "motion", fill=0)
        env.put(pair, x & 0xFFFFFFFF, y & 0xFFFFFFFF, tx & 0xFFFFFFFF, ty & 0xFFFFFFFF)
        env.put(pair + 0x10, word(rnd), word(rnd), word(rnd), word(rnd))
        if snap is None:
            env.put(SNAP_X, 0xFFFFFFFF)
            env.put(SNAP_Y, word(rnd))
        else:
            env.put(SNAP_X, snap[0] & 0xFFFFFFFF)
            env.put(SNAP_Y, snap[1] & 0xFFFFFFFF)
        env.put(SCALE, scale & 0xFFFFFFFF)
        return {"pair": pair}
    return setup


def step_case(label, setup, d4, d5, a1=0x1111, a2=0x2222):
    return Case(label, STEP_TOWARD, setup,
                arguments=(a1, a2, lambda t: t["pair"], d4 & 0xFFFFFFFF, d5 & 0xFFFFFFFF))


def cases(random_source):
    rnd = random_source

    # ---------------------------------------------------------------- 0x46d520
    for value in SWEEP:
        yield classify_a_case(value)
    for _ in range(30):
        yield classify_a_case(rnd.randrange(0, 1 << 32))
        yield classify_a_case(rnd.randrange(0, 0x60))

    # ---------------------------------------------------------------- 0x473b10
    # every position of the target, each with a distinct pointer value
    for position in list(range(0, 0x3A)) + [0x7F, 0xC7, 0xCF]:
        count = position + 1 + rnd.randrange(0, 3)
        entries = [word(rnd) | 0x10000 for _ in range(count)]
        # entries after the target repeat it so only the first match counts
        target = entries[position]
        for later in range(position + 1, count):
            if rnd.randrange(2):
                entries[later] = target
        yield classify_b_case(f"473b10 target at position {position}", count, entries, target)
    for position in (1, 5, 6, 0x13, 0x20, 0x21, 0x35, 0x40):
        entries = [word(rnd) | 0x10000 for _ in range(0x45)]
        yield classify_b_case(f"473b10 not within the count at {position}", position, entries, entries[position])
    entries = [word(rnd) | 0x10000 for _ in range(10)]
    yield classify_b_case("473b10 null argument", 10, [0] + entries[1:], 0)
    yield classify_b_case("473b10 unknown pointer", 10, entries, 0x12345678)
    yield classify_b_case("473b10 empty table", 0, entries, entries[3])
    yield classify_b_case("473b10 negative count", 0xFFFFFFFF, entries, entries[3])
    yield classify_b_case("473b10 negative large count", 0x80000000, entries, entries[3])
    yield classify_b_case("473b10 count one, index zero", 1, entries, entries[0])
    yield classify_b_case("473b10 duplicate keeps first", 8, [7, 9, 11, 9, 9, 3, 4, 5], 9)

    # ---------------------------------------------------------------- 0x473630
    for count, index in ((5, 0), (5, 4), (5, 5), (5, 6), (5, 0xFFFFFFFF), (5, 0x80000000), (5, 0x7FFFFFFF),
                         (0, 0), (1, 0), (1, 1), (0x40, 0x3F), (0x40, 0x40), (0x80000000, 0), (0xFFFFFFFF, 0xFFFFFFFE)):
        entries = [env_pointer for env_pointer in (rnd.randrange(0x10000, 0xFFFFFF) & ~3 for _ in range(min(0x44, max(count, 1) if count < 0x100 else 4)))]
        yield Case(f"473630 count {count:#x} index {index:#x}", NAME_OF, table_setup(count, entries), arguments=(index,))
    for _ in range(12):
        count = rnd.randrange(1, 60)
        entries = [rnd.randrange(0x10000, 0xFFFFFF) & ~3 for _ in range(60)]
        yield Case(f"473630 random count {count}", NAME_OF, table_setup(count, entries), arguments=(rnd.randrange(0, 64),))

    # ---------------------------------------------------------------- 0x473ae0
    def flag_setup(flags, bit_word):
        def setup(env):
            subject = env.object(0x170, "subject", fill=0)
            for off in range(0, 0x170, 4):
                env.put(subject + off, word(rnd))
            env.put(subject + 8, bit_word)
            env.put(subject + 0x164, flags)
            return {"subject": subject}
        return setup

    for flags, bits in ((0, 0), (0x200, 1), (0xFFFFFFFF, 0xFFFFFFFE), (0x1FF, 0x2), (0xFFFFFDFF, 0xFFFFFFFF)):
        yield Case(f"473ae0 flags {flags:#x} bits {bits:#x}", FLAG_OBJECT, flag_setup(flags, bits),
                   arguments=(lambda t: t["subject"],))
    for _ in range(12):
        yield Case("473ae0 random contents", FLAG_OBJECT, flag_setup(word(rnd), word(rnd)),
                   arguments=(lambda t: t["subject"],))

    # ---------------------------------------------------------------- 0x473660
    def run_action_setup(count, slot, with_handlers=True):
        def setup(env):
            env.put(COUNT, count & 0xFFFFFFFF)
            handlers = []
            for i in range(8):
                entry = env.object(0x20, f"entry {i}", fill=0)
                for off in range(0, 0x20, 4):
                    env.put(entry + off, word(rnd))
                if with_handlers:
                    stub = env.stub(f"action {i}", "cdecl", 1, returns(rnd.randrange(0, 1 << 32)))
                else:
                    stub = word(rnd)
                env.put(entry + 0x10, stub)
                env.put(TABLE2 + 4 * i, entry)
                handlers.append(stub)
            holder = env.object(0x30, "holder", fill=0)
            for off in range(0, 0x30, 4):
                env.put(holder + off, word(rnd))
            old = env.object(0x30, "slot", fill=0)
            for off in range(0, 0x30, 4):
                env.put(old + off, word(rnd))
            env.put(old + 0x10, env.stub("old", "cdecl", 1, returns(0)))
            env.put(holder + 0x6C, old)
            subject = env.object(0x80, "subject", fill=0)
            for off in range(0, 0x80, 4):
                env.put(subject + off, word(rnd))
            env.put(subject + 0x6C, old)
            return {"subject": subject, "slot": slot}
        return setup

    for count, slot in ((8, 0), (8, 3), (8, 7), (5, 4), (5, 5), (5, 6), (1, 0), (0, 0), (8, 8), (8, 0xFFFFFFFF),
                        (8, 0x80000000), (8, 0x7FFFFFFF), (0x80000000, 0), (0xFFFFFFFF, 0)):
        in_range = (count & 0xFFFFFFFF) < 0x80000000 and slot < 0x80000000 and slot < count and count <= 8
        yield Case(f"473660 count {count:#x} slot {slot:#x}", RUN_ACTION, run_action_setup(count, slot),
                   arguments=(lambda t: t["subject"], slot))
    for slot in range(8):
        yield Case(f"473660 each slot {slot}", RUN_ACTION, run_action_setup(8, slot),
                   arguments=(lambda t: t["subject"], slot))

    # ---------------------------------------------------------------- 0x486940
    yield step_case("486940 x rises, y falls", step_setup(rnd, 100, 900, 5000, 100), 20, 30)
    yield step_case("486940 x falls, y rises", step_setup(rnd, 5000, 100, 100, 900), 20, 30)
    yield step_case("486940 already at target", step_setup(rnd, 77, 88, 77, 88), 20, 30)
    yield step_case("486940 only x at target", step_setup(rnd, 77, 100, 77, 900), 20, 30)
    yield step_case("486940 only y at target", step_setup(rnd, 100, 88, 900, 88), 20, 30)
    for scale in (1, 3, 999, 1000, 1001, 7777, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for d4, d5 in ((1, 1), (7, 13), (1000, 999), (123456, 654321), (0x7FFFFFFF, 0x12345),
                       (-1, -5), (-12345, 99), (0x80000000, 0xFFFFFF00)):
            yield step_case(f"486940 scale {scale:#x} deltas {d4} {d5} rising",
                            step_setup(rnd, -5000, -9000, 1 << 30, 1 << 30, scale=scale), d4, d5)
            yield step_case(f"486940 scale {scale:#x} deltas {d4} {d5} falling",
                            step_setup(rnd, 1 << 30, 1 << 29, -(1 << 30), -(1 << 29), scale=scale), d4, d5)
    # landing exactly on, one short of, and one past the target
    for gap in (1, 2, 19, 20, 21, 22, 40):
        yield step_case(f"486940 x gap {gap} step 20 up", step_setup(rnd, 1000, 5000, 1000 + gap, 5000 + gap, scale=1000), 20, 20)
        yield step_case(f"486940 x gap {gap} step 20 down", step_setup(rnd, 1000 + gap, 5000 + gap, 1000, 5000, scale=1000), 20, 20)
        yield step_case(f"486940 mixed gap {gap}", step_setup(rnd, 1000, 5000 + gap, 1000 + gap, 5000, scale=1000), 20, 20)
    yield step_case("486940 zero step", step_setup(rnd, 1, 2, 100, 200, scale=0), 20, 30)
    yield step_case("486940 zero deltas", step_setup(rnd, 1, 2, 100, 200), 0, 0)
    # the snapshot globals replace the target when the first one is not -1
    yield step_case("486940 snap replaces target", step_setup(rnd, 10, 20, 3000, 4000, snap=(500, 600)), 25, 35)
    yield step_case("486940 snap below position", step_setup(rnd, 1000, 2000, 3000, 4000, snap=(-50, -60)), 25, 35)
    yield step_case("486940 snap equal position", step_setup(rnd, 1000, 2000, 3000, 4000, snap=(1000, 2000)), 25, 35)
    yield step_case("486940 snap zero", step_setup(rnd, 10, 20, 3000, 4000, snap=(0, 0)), 25, 35)
    yield step_case("486940 snap minus two", step_setup(rnd, 10, 20, 3000, 4000, snap=(0xFFFFFFFE, 0xFFFFFFFD)), 25, 35)
    for i in range(80):
        x, y = rnd.randrange(-100000, 100000), rnd.randrange(-100000, 100000)
        tx, ty = rnd.randrange(-100000, 100000), rnd.randrange(-100000, 100000)
        snap = None if i % 3 else (rnd.randrange(-100000, 100000), rnd.randrange(-100000, 100000))
        scale = rnd.choice((rnd.randrange(0, 5000), rnd.randrange(0, 1 << 32), 1000))
        d4 = rnd.choice((rnd.randrange(-5000, 5000), rnd.randrange(0, 1 << 32)))
        d5 = rnd.choice((rnd.randrange(-5000, 5000), rnd.randrange(0, 1 << 32)))
        yield step_case(f"486940 random {i}", step_setup(rnd, x, y, tx, ty, snap=snap, scale=scale), d4, d5,
                        a1=word(rnd), a2=word(rnd))
    for i in range(30):
        base = rnd.randrange(-1000, 1000)
        tx = base + rnd.randrange(-300, 300)
        ty = base + rnd.randrange(-300, 300)
        yield step_case(f"486940 near random {i}", step_setup(rnd, base, base + 7, tx, ty, scale=1000),
                        rnd.randrange(0, 400), rnd.randrange(0, 400))

    # ---------------------------------------------------------------- 0x46cb40
    ptable = [word(rnd) | 0x20000 for _ in range(0x40)]

    yield Case("46cb40 null object", COUNT_OBJECT, lambda env: preload_tally(env, rnd) and {}, arguments=(0,))
    for kind in (0, 1, 4, 6, 0xFFFFFFFF, 0x105):
        yield count_case(f"46cb40 virtual kind {kind:#x} is not 5", count_setup(rnd, H_A, kind=kind, index=1))
    yield count_case("46cb40 no handler object", count_setup(rnd, H_A, with_handler_object=False, index=1))
    yield count_case("46cb40 ignored handler", count_setup(rnd, H_IGNORED, index=1))

    for name, handler in (("A", H_A), ("B", H_B), ("C", H_C)):
        for index in SWEEP:
            yield count_case(f"46cb40 handler {name} index {index & 0xFFFFFFFF:#x}",
                             count_setup(rnd, handler, index=index, pointer_field=word(rnd)))

    for handler in H_INDIRECT:
        for position in (0, 1, 3, 6, 0x21, 0x2D, 0x31):
            table = [word(rnd) | 0x20000 for _ in range(0x34)]
            yield count_case(f"46cb40 handler {handler:#x} table position {position}",
                             count_setup(rnd, handler, index=rnd.randrange(1, 0x35), pointer_field=table[position],
                                         table=table))
        table = [word(rnd) | 0x20000 for _ in range(10)]
        yield count_case(f"46cb40 handler {handler:#x} pointer not in table",
                         count_setup(rnd, handler, index=0x21, pointer_field=0x3333, table=table))
        yield count_case(f"46cb40 handler {handler:#x} null pointer",
                         count_setup(rnd, handler, index=0x21, pointer_field=0, table=table))
        yield count_case(f"46cb40 handler {handler:#x} empty table",
                         count_setup(rnd, handler, index=0x21, pointer_field=table[2], table=table, table_count=0))

    # unknown handler: nine fields classified directly
    unknown = (0x401000, 0x0, 0x46CB40, 0x12345678)

    def unknown_fields(values):
        return {0xF0: values[0] & 0xFFFFFFFF, 0xF4: values[1] & 0xFFFFFFFF, 0xF8: values[2] & 0xFFFFFFFF,
                0xFC: values[3] & 0xFFFFFFFF, 0x100: values[4] & 0xFFFFFFFF, 0x104: values[5] & 0xFFFFFFFF,
                0x108: values[6] & 0xFFFFFFFF, 0x10C: values[7] & 0xFFFFFFFF}

    for handler in unknown:
        for index in SWEEP:
            yield count_case(f"46cb40 unknown handler {handler:#x} subject index {index & 0xFFFFFFFF:#x}",
                             count_setup(rnd, handler, index=index,
                                         second=unknown_fields([rnd.randrange(0, 0x40) for _ in range(8)])))
    for field in range(8):
        for value in REPRESENTATIVES:
            values = [6] * 8
            values[field] = value
            yield count_case(f"46cb40 unknown handler field {field} value {value:#x}",
                             count_setup(rnd, 0x401000, index=6, second=unknown_fields(values)))
    for field in range(8):
        for value in REPRESENTATIVES:
            values = [rnd.randrange(0, 0x40) for _ in range(8)]
            values[field] = value
            yield count_case(f"46cb40 unknown handler mixed field {field} value {value:#x}",
                             count_setup(rnd, 0x401000 + rnd.randrange(0, 0x1000), index=rnd.randrange(0, 0x40),
                                         second=unknown_fields(values)))
    for value in range(-1, 0x37):
        yield count_case(f"46cb40 unknown handler all fields {value}",
                         count_setup(rnd, 0x401000, index=value, second=unknown_fields([value] * 8)))
    for i in range(40):
        choices = list(CLASS_OF) + [0, 6, 0x35, 0x13, 0xFFFFFFFF]
        yield count_case(f"46cb40 unknown handler random {i}",
                         count_setup(rnd, rnd.choice((0x401000, 0x500000, word(rnd) | 0x400000)),
                                     index=rnd.choice(choices),
                                     second=unknown_fields([rnd.choice(choices) for _ in range(8)])))

    # ---------------------------------------------------------------- 0x46caf0
    def grids(env, level):
        """Three spatial grids (the lists 4d51f0 walks). Level 4: all empty by range. Level 5+: populated."""
        result = []
        for g in range(3):
            grid = env.object(0x50, f"grid {g}", fill=0)
            env.put(grid + 0xC, 2)
            env.put(grid + 0x14, 0, 0)
            table = env.object(8 * 4, f"cells {g}", fill=0)
            env.put(grid + 0x40, table)
            if level <= 4:
                env.put(grid + 0x28, 5, 0, 1, 1)   # inverted range: nothing is visited
            else:
                env.put(grid + 0x28, 0, 0, 1, 1)
                for cell in range(4):
                    chain = []
                    for _ in range(rnd.randrange(0, 3)):
                        subject, _h = build_subject(
                            env, rnd, rnd.choice((H_A, H_B, H_C, 0x401000, H_INDIRECT[1], H_IGNORED)),
                            kind=rnd.choice((5, 5, 5, 4)), index=rnd.choice(list(CLASS_OF)),
                            pointer_field=word(rnd),
                            second=unknown_fields([rnd.choice(list(CLASS_OF)) for _ in range(8)]))
                        node = env.object(0x20, "node", fill=0)
                        env.put(node, 0, 0, 0, 0)
                        env.put(node + 0x10, rnd.randrange(0, 2), rnd.randrange(0, 2), subject)
                        chain.append(node)
                    for a, b in zip(chain, chain[1:]):
                        env.put(a, b)
                    if chain:
                        env.put(table + 8 * cell, chain[0])
            result.append(grid)
        return result

    def chain_setup(level):
        """level: 0 no +0xc, 1 no +0x24, 2 no +0x5c, 3 no +0xb0, 4 full chain with empty lists."""
        def setup(env):
            preload_tally(env, rnd)
            owner = env.object(0x20, "owner", fill=0)
            for off in range(0, 0x20, 4):
                env.put(owner + off, word(rnd))
            if level >= 1:
                a = env.object(0x40, "a", fill=0)
                for off in range(0, 0x40, 4):
                    env.put(a + off, word(rnd))
                env.put(owner + 0xC, a)
            else:
                env.put(owner + 0xC, 0)
                return {"owner": owner}
            if level >= 2:
                b = env.object(0x80, "b", fill=0)
                for off in range(0, 0x80, 4):
                    env.put(b + off, word(rnd))
                env.put(a + 0x24, b)
            else:
                env.put(a + 0x24, 0)
                return {"owner": owner}
            if level >= 3:
                c = env.object(0xC0, "c", fill=0)
                for off in range(0, 0xC0, 4):
                    env.put(c + off, word(rnd))
                env.put(b + 0x5C, c)
            else:
                env.put(b + 0x5C, 0)
                return {"owner": owner}
            if level >= 4:
                d = env.object(0x20, "d", fill=0)
                env.put(d + 4, *grids(env, level))
                env.put(c + 0xB0, d)
            else:
                env.put(c + 0xB0, 0)
            return {"owner": owner}
        return setup

    for level in range(7):
        yield Case(f"46caf0 chain level {level}", CLEAR_AND_WALK, chain_setup(level), receiver=lambda t: t["owner"])
