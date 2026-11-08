"""Cases for t_projectile: TProjectile object logic (0x497eb0).

The object's state record sits at owner+0x6c.  Its word at +0x1c selects the branch:
0 builds a projectile logic object, 0x1d and 0x1e call a virtual method of the
target at record+0x18, 0x3e8 does nothing, and any other value runs the
resource-slot lookup at 0x4dc870 on the target.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate

LOGIC = 0x497EB0
OPERATOR_NEW = 0x4F63EC
MALLOC = 0x4A48E0

# Globals of the slot table that 0x4dc870 searches.
TABLE_LOW = 0x5376A0
TABLE_HIGH = 0x5376A4
TABLE_DATA = 0x5376A8
TABLE_DEFAULT = 0x5376AC
TABLE_STRIDE = 0x5376B0
TABLE_FRESH = 0x5376B4
TABLE_FRESH_COUNT = 0x5376B8
TABLE_ERROR_SINK = 0x53769C

TARGET_METHODS = (0x04, 0x08, 0x0C, 0x10, 0x1C, 0x20)


def logic(label, setup, **options):
    return Case(label, LOGIC, setup, arguments=(lambda tokens: tokens["object"],), **options)


def cstring(env, refs=1, length=3, capacity=8, fill=0x61):
    """A reference-counted string: the pointer to its characters, with a 12-byte header in front."""
    block = env.object(0x20, "string", words=[refs, length, capacity, fill | (fill << 8), fill, 0, 0, 0])
    return block + 12


def world(env, state, ident=None, reaction=None):
    """An owner whose record holds `state`, with a target that logs every virtual call it receives.

    `reaction` maps a method offset to a function(env, tokens) run inside that method.
    """
    reaction = reaction or {}
    tokens = {}
    methods = env.object(0x40, "target-vtable")
    for offset in TARGET_METHODS:
        def effect(env, call, offset=offset):
            log = tokens["record"] + 0x34
            env.put(log, env.get(log) + 1, offset, call.receiver)
            env.put(log + 0x0C, call.arguments[0] if call.arguments else 0xA5A5A5A5)
            if offset in reaction:
                reaction[offset](env, tokens)
            return 0x1000 + offset
        argc = 1 if offset in (0x04, 0x08, 0x0C) else 0
        env.put(methods + offset, env.stub(f"target-method-{offset:#x}", "thiscall", argc, effect))
    info_words = [0x11111111 + i for i in range(16)]
    if ident is not None:
        info_words[7] = ident  # info+0x1c: the resource id looked up by 0x4dc870
    info = env.object(0x40, "target-info", words=info_words)
    target = env.object(0x80, "target", words=[0x22222222 + i for i in range(32)])
    env.put(target, methods)
    env.put(target + 0x10, info)
    record = env.object(0x60, "record", words=[0x33333333 + i for i in range(24)])
    env.put(record + 0x18, target)
    env.put(record + 0x1C, state)
    owner = env.object(0x1A0, "owner", words=[0x44444444 + i for i in range(104)])
    env.put(owner + 0x6C, record)
    tokens.update({"object": owner, "record": record, "target": target, "info": info, "methods": methods})
    return tokens


def prepare_owner_for_construction(env, tokens, flag64=0, shield=0, extras=None):
    """Make the owner usable by the projectile constructor at 0x497f70."""
    owner = tokens["object"]
    record = tokens["record"]
    owner_parent = env.object(0x40, "owner-parent", words=[0x55555555 + i for i in range(16)])
    scripts = env.object(0x40, "owner-scripts", words=[0x66666666 + i for i in range(16)])
    env.put(owner_parent + 0x14, scripts)
    env.put(scripts + 0x14, 0)  # name map at scripts+0x10: no buckets, so no script is found
    env.put(scripts + 0x18, 7)
    env.put(owner + 0x0C, owner_parent)
    env.put(owner + 0x64, flag64)
    env.put(owner + 0x08, 0x01010101)
    env.put(owner + 0x170, shield)
    if extras:
        for offset, value in extras.items():
            env.put(owner + offset, value)
    env.put(record + 0x1C, 0)
    tokens["parent"] = owner_parent
    tokens["scripts"] = scripts


def construct(state=0, flag64=0, shield=0, extras=None, record_extras=None, fail_new=False):
    def setup(env):
        tokens = world(env, state)
        prepare_owner_for_construction(env, tokens, flag64, shield, extras)
        for offset, value in (record_extras or {}).items():
            env.put(tokens["record"] + offset, value)
        if fail_new:
            env.override(OPERATOR_NEW, allocate(fail=True))
        return tokens
    return setup


def shield_record(env, tokens, blocked_a, blocked_b, first_word):
    """A shield-like object at owner+0x170 with the three words 0x497f70 reads from it."""
    shield = env.object(0x80, "shield", words=[0x77777777 + i for i in range(32)])
    items = env.object(0x10, "shield-items", words=[first_word, 0x1234, 0x5678, 0x9ABC])
    env.put(shield + 0x14, items)
    env.put(shield + 0x64, blocked_a)
    env.put(shield + 0x68, blocked_b)
    return shield


def lookup(ident, low=0, high=0, grown=False, fail_alloc=False, refs=1, reaction=None, stride=4, state=None):
    """A state that sends 0x4dc870 to look up resource `ident` in a table spanning low..high."""
    def setup(env):
        tokens = world(env, 0x7000 + (ident & 0xFF) if state is None else state, ident=ident, reaction=reaction)
        count = high - low + 1
        if count > 0 and not grown:
            data = env.object(max(4, count * stride), "slots")
            for index in range(count):
                env.put(data + index * stride, cstring(env, refs=refs, length=index + 1, fill=0x41 + index))
        else:
            data = 0
        default_slot = env.object(8, "default-slot", words=[cstring(env, length=0, capacity=1), 0])
        sink = env.object(0x20, "error-sink", words=[0x88888888, 0x99999999, 0xAAAAAAAA, 4, 0xBBBBBBBB, 0xCCCCCCCC, 0xDDDDDDDD, 0xEEEEEEEE])
        env.put(TABLE_LOW, low, high, data, default_slot, stride)
        env.put(TABLE_FRESH, 0, 0)
        env.put(TABLE_ERROR_SINK, sink)
        if fail_alloc:
            env.override(MALLOC, allocate(fail=True))
        tokens.update({"data": data, "sink": sink, "default": default_slot})
        return tokens
    return setup


def cases(random_source):
    # State 0 builds a projectile logic object and calls its virtual method +0x10.
    yield logic("state 0: construct, clean owner", construct())
    yield logic("state 0: owner flag at +0x64 already set", construct(flag64=0xFAA))
    yield logic("state 0: owner flag at +0x64 other value", construct(flag64=7))
    yield logic("state 0: zero defaults filled in", construct(extras={0x148: 0, 0x14C: 0, 0x108: 0, 0x110: 0}, record_extras={0xBC: 0}))
    yield logic(
        "state 0: nonzero values kept",
        construct(extras={0x148: 33, 0x14C: 44, 0x108: 55, 0x110: 66, 0x104: 77}, record_extras={0xBC: 99}),
    )
    yield logic(
        "state 0: only one default zero",
        construct(extras={0x148: 5, 0x14C: 0, 0x108: 9, 0x110: 0}, record_extras={0xBC: 123}),
    )
    yield logic(
        "state 0: only the other default zero",
        construct(extras={0x148: 0, 0x14C: 5, 0x108: 0, 0x110: 8}, record_extras={0xBC: 0}),
    )

    def with_shield(blocked_a, blocked_b, first_word):
        def setup(env):
            tokens = world(env, 0)
            prepare_owner_for_construction(env, tokens)
            shield = shield_record(env, tokens, blocked_a, blocked_b, first_word)
            env.put(tokens["object"] + 0x170, shield)
            env.put(tokens["object"] + 0x16C, 0xFEEDF00D)
            env.put(tokens["object"] + 0x174, 0xFACEB00C)
            return tokens
        return setup

    yield logic("state 0: shield with positive first count", with_shield(3, 5, 0xAB))
    yield logic("state 0: shield with zero first and negative second", with_shield(0, -2, 0xCD))
    yield logic("state 0: shield with zero first and nonnegative second", with_shield(0, 0, 0xEF))
    yield logic("state 0: shield with negative first and nonnegative second", with_shield(-1, 4, 0x123))
    yield logic("state 0: shield with negative both", with_shield(-5, -6, 0x456))
    yield logic("state 0: allocation succeeds with a bigger owner id", construct(extras={0x190: 0xC0FFEE, 0xD0: 9, 0xD8: 8}))

    # A virtual callback may edit the state record before the owner stores
    # the constructed projectile. Distinct sentinels make that later store
    # observable, including its position relative to the callback.
    def construction_callback(marker, move_record=False):
        def setup(env):
            tokens = construct()(env)
            record = tokens["record"]
            alternate = env.object(0x100, "alternate-record", words=[marker ^ i for i in range(64)])

            def initialized(env, call):
                env.put(record + 0x40, env.get(record + 0x18), call.receiver, env.get(record + 0x1C))
                env.put(record + 0x18, marker)
                if move_record:
                    env.put(tokens["object"] + 0x6C, alternate)
                return marker ^ 0xFFFFFFFF

            env.put(0x50FC1C + 0x10, env.stub("projectile-initialize-record-edit", "thiscall", 0, initialized))
            return tokens
        return setup

    for marker in (0, 1, 0xFFFFFFFF, 0x13579BDF):
        for move_record in (False, True):
            yield logic(
                f"state 0: initialization edits record {marker:#x}, redirect={move_record}",
                construction_callback(marker, move_record),
            )
    for _ in range(8):
        marker = random_source.randrange(2, 0xFFFFFFFE)
        yield logic(f"state 0: random initialization edit {marker:#x}", construction_callback(marker))

    # The virtual-method states.
    yield logic("state 0x1d: target method +0x20", lambda env: world(env, 0x1D))
    yield logic("state 0x1e: target method +0x1c", lambda env: world(env, 0x1E))
    yield logic("state 0x3e8: nothing happens", lambda env: world(env, 0x3E8))

    # Neighbours of the compared constants, resolved by the generic lookup.
    for state in (1, 0x1C, 0x1F, 0x20, 0x3E7, 0x3E9, 0x7FFFFFFF, 0xFFFFFFFF):
        yield logic(f"neighbour state {state:#x} takes the lookup path", lookup(0, state=state))

    # The lookup path: ids inside the table.
    yield logic("lookup: id 0 in a single-slot table", lookup(0))
    yield logic("lookup: id at the low end", lookup(10, 10, 14))
    yield logic("lookup: id in the middle", lookup(12, 10, 14))
    yield logic("lookup: id at the high end", lookup(14, 10, 14))
    yield logic("lookup: negative table range", lookup(-2, -5, 3))
    yield logic("lookup: wide stride", lookup(11, 10, 13, stride=8))
    # Ids outside the table grow it (the original calls 0x4db6e0, which allocates).
    yield logic("lookup: id above an empty table", lookup(3, 0, -1, grown=True))
    yield logic("lookup: id below an empty table", lookup(-3, 0, -1, grown=True))
    yield logic("lookup: id above a single-entry table", lookup(5, 0, 0, grown=True))
    yield logic("lookup: id below a single-entry table", lookup(-4, 0, 0, grown=True))
    yield logic("lookup: id far above", lookup(40, 2, 2, grown=True))
    yield logic("lookup: id one below the range", lookup(9, 10, 10, grown=True))
    yield logic("lookup: id one above the range", lookup(11, 10, 10, grown=True))
    # A target method changes the table behind the function's back before the second lookup.
    def shrink_table(env, tokens):
        env.put(TABLE_HIGH, 3)
        env.put(TABLE_DATA, 0)

    yield logic("lookup: table emptied during the first method", lookup(6, 0, 6, reaction={0x08: shrink_table}))

    def move_table_up(env, tokens):
        env.put(TABLE_LOW, 100)
        env.put(TABLE_HIGH, 100)
        env.put(TABLE_DATA, 0)

    yield logic("lookup: table moved away during the first method", lookup(6, 0, 6, reaction={0x08: move_table_up}))

    # Random ids and ranges.
    for _ in range(12):
        low = random_source.randrange(-20, 20)
        width = random_source.randrange(1, 9)
        ident = low + random_source.randrange(0, width)
        yield logic(f"random in-table lookup {ident} in {low}..{low + width - 1}", lookup(ident, low, low + width - 1))
    for _ in range(6):
        low = random_source.randrange(-10, 10)
        ident = low + random_source.choice((-1, 1)) * random_source.randrange(1, 12)
        yield logic(f"random growth lookup {ident} around {low}", lookup(ident, low, low, grown=True))
    for _ in range(6):
        state = random_source.randrange(0x21, 0x3E7)
        yield logic(f"random state {state:#x}", lookup(random_source.randrange(-3, 3), -3, 3, state=state))
