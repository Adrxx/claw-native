"""Cases for seagull: Seagull object logic."""
from clawparity.cases import Case
from clawparity import world
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

LOGIC = 0x486E90
OPERATOR_NEW = 0x4F63EC
CONSTRUCTOR = 0x486F50
G_LO, G_HI, G_BASE, G_STRIDE, G_ARRAY, G_COUNT = 0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0, 0x5376B4, 0x5376B8
ENTRIES = 12


def signed(value):
    return value - (1 << 32) if value & 0x80000000 else value


def make_table(env, count, stride, tag):
    """An array of CString objects (one pointer each, `stride` bytes apart) whose buffers have the MFC header
    (reference count 1, length, allocated length) in front of the characters."""
    table = env.object(count * stride, f"{tag}-strings", fill=0x5A)
    for slot in range(count):
        buffer = env.object(12 + 16, f"{tag}-buffer-{slot}", fill=0x41 + slot)
        env.put(buffer, 1, 4, 16)
        env.put(table + slot * stride, buffer + 12)
    return table


def seagull(state, index=0, stride=8, hook=None):
    """setup(): owner object (+0x6c -> record), record (+0x1c state, +0x18 child), child with a vtable of stubs.

    The default path looks the owner's +0x1c word up in the string table at G_BASE (G_LO..G_HI)."""
    def setup(env):
        owner = env.object(0x80, "owner", fill=0x11)
        record = env.object(0x40, "record", fill=0x22)
        child = env.object(0x60, "child", fill=0x33)
        vtable = env.object(0x40, "child-vtable", fill=0x44)
        table = make_table(env, ENTRIES, stride, "table")
        lookup = (state + 7) & 0xFFFFFFFF if signed(state) < 0x7FFFFF00 else state
        # The original compares bounds as signed integers. Near INT_MIN a
        # randomly selected index must not wrap the lower bound to positive.
        table_index = min(index, signed(lookup) + (1 << 31))
        low = (lookup - table_index) & 0xFFFFFFFF
        env.put(owner + 0x1C, lookup)
        env.put(G_LO, low)
        env.put(G_HI, (low + ENTRIES - 1) & 0xFFFFFFFF)
        env.put(G_BASE, table)
        env.put(G_STRIDE, stride)
        env.put(G_COUNT, 0)
        tokens = {"owner": owner, "record": record, "child": child, "vtable": vtable, "table": table,
                  "stride": stride, "index": table_index}
        for offset, argc in ((0x04, 1), (0x08, 1), (0x0C, 1), (0x10, 0), (0x1C, 0), (0x20, 0)):
            def effect(env, call, offset=offset):
                return 0x1000 + offset
            env.put(vtable + offset, env.stub(f"child-method-{offset:#x}", "thiscall", argc, effect))
        env.put(vtable, env.stub("child-method-0", "thiscall", 0, returns(0x1000)))
        env.put(child, vtable)
        env.put(child + 0x10, owner)
        env.put(owner + 0x6C, record)
        env.put(record + 0x18, child)
        env.put(record + 0x1C, state)
        if hook:
            hook(env, tokens)
        return tokens
    return setup


def logic(label, setup, **options):
    return Case(label, LOGIC, setup, receiver=0, arguments=(lambda t: t["owner"],), **options)


def _existing_cases(random_source):
    yield logic("state 0x1d calls slot 0x20", seagull(0x1D))
    yield logic("state 0x1e calls slot 0x1c", seagull(0x1E))
    yield logic("state 1000 does nothing", seagull(1000))
    for state in (1, 2, 0x1C, 0x1F, 0x20, 999, 1001, 0xFFFFFFFF, 0x80000000):
        yield logic(f"state {state:#x} default path", seagull(state, index=random_source.randrange(0, ENTRIES)
                                                              if signed(state) < 0x7FFFFF00 else 0))
    for _ in range(12):
        state = random_source.choice([random_source.randrange(2, 0x1C), random_source.randrange(0x1F, 999),
                                      random_source.randrange(1002, 100000)])
        yield logic(f"random state {state} default path",
                    seagull(state, index=random_source.randrange(0, ENTRIES), stride=random_source.choice((4, 8, 12, 20))))

    def moves_the_table(env, t):
        # the +4 method changes what the vtable +8 call goes through, and the +8 method moves the table bounds
        other = make_table(env, ENTRIES, t["stride"], "other")
        second = env.object(0x40, "second-vtable", fill=0x66)
        env.put(second + 0x08, env.stub("second-method-8", "thiscall", 1, returns(0x2008)))
        env.put(second + 0x0C, env.stub("second-method-c", "thiscall", 1, returns(0x200C)))

        def first(env, call):
            env.put(t["child"], second)
            return 0x1004

        def middle(env, call):
            env.put(G_BASE, other)
            env.put(G_STRIDE, t["stride"] + 4)
            env.put(G_COUNT, 0)
            return 0x1008

        env.put(t["vtable"] + 0x04, env.stub("first", "thiscall", 1, first))
        env.put(second + 0x04, env.stub("second-method-4", "thiscall", 1, returns(0x2004)))
        env.put(second, env.stub("second-method-0", "thiscall", 0, returns(0x2000)))
        env.put(t["vtable"] + 0x08, env.stub("middle", "thiscall", 1, middle))

    yield logic("methods change the child vtable and the table globals between calls",
                seagull(5, index=3, hook=moves_the_table))

    def table_shifts(env, t):
        def shift(env, call):
            env.put(G_LO, env.get(G_LO) + 2)
            env.put(G_HI, env.get(G_HI) + 2)
            return 0x1008
        env.put(t["vtable"] + 0x08, env.stub("shift", "thiscall", 1, shift))

    yield logic("second lookup re-reads the bounds", seagull(9, index=4, hook=table_shifts))


ANIMATION_KEYS = tuple("LEVEL_SEAGULL_" + name for name in (
    "DIVE1", "DIVE2", "DIVE3", "DIVE4", "FEATHEREXPLODE", "FEATHERFLOAT",
    "FLYING", "HITHIGH", "HITLOW", "HOME", "KILLFALL"))


def constructor_world(owner_words=None, state_words=None, resource_mode="empty", duration=100,
                      dimensions=(32, 32), origin=(0, 0), bucket_count=17, allocation_effect=False):
    def setup(env):
        animations = {}
        sprites = {}
        if resource_mode != "empty":
            fallback = world.animation(env, duration, "fallback-animation")
            animations["GAME_NULL"] = fallback
            animations["UNRELATED_ANIMATION"] = world.animation(env, duration + 1, "unrelated-animation")
            sprites["UNRELATED_SPRITE"] = world.sprite(env, 7, 11, (2, -3), "unrelated-sprite")
        if resource_mode in ("hit", "mixed"):
            for index, key in enumerate(ANIMATION_KEYS):
                if resource_mode == "hit" or index % 2 == 0:
                    animations[key] = world.animation(env, duration + index + 2, "animation-" + key)
            sprites["LEVEL_SEAGULL"] = world.sprite(env, *dimensions, origin, "seagull-sprite")
        tokens = world.world(env, owner_words=owner_words, state_words=state_words,
                             resources={"animations": animations, "sprites": sprites},
                             bucket_count=bucket_count)
        world.rectangle_services(env)
        # A distinct live prior-child pointer proves initialization publishes the newly
        # constructed child only after its original virtual initialization call.
        prior_child = env.object(0x40, "prior-child", fill=0xB7)
        env.put(tokens["state"] + 0x18, prior_child)
        if allocation_effect:
            def alloc(env, call):
                if call.arguments[0] == 0x440 and env.calls_so_far(OPERATOR_NEW) == 1:
                    # Changes are visible to the original constructor after allocation.
                    env.put(tokens["owner"] + 0x50, 731)
                    env.put(tokens["state"] + 0x30, 317)
                return env.object(call.arguments[0], "allocation", fill=0xA9)
            env.override(OPERATOR_NEW, alloc)
        return tokens
    return setup


def cases(random_source):
    yield from _existing_cases(random_source)
    for mode in ("empty", "missing", "hit", "mixed"):
        yield logic("state zero constructor resources " + mode,
                    constructor_world(resource_mode=mode, bucket_count=1))
    for index in range(12):
        owner_words = {offset: random_source.randrange(1, 1000) for offset in
                       (0x4C, 0x50, 0x148, 0x14C, 0x108, 0x114)}
        owner_words[0x64] = random_source.choice((0, 0x2134, 19))
        owner_words[0x40] = random_source.choice((0, 2))
        state_words = {offset: random_source.randrange(1, 700) for offset in
                       (0x2C, 0x30, 0x34, 0x38, 0x64, 0x68, 0x168)}
        yield logic(f"random nonzero constructor fields {index}",
                    constructor_world(owner_words, state_words,
                                      random_source.choice(("empty", "missing", "hit", "mixed")),
                                      duration=random_source.randrange(1, 500),
                                      dimensions=(random_source.randrange(1, 80), random_source.randrange(1, 90)),
                                      origin=(random_source.randrange(-15, 15), random_source.randrange(-20, 20)),
                                      bucket_count=random_source.choice((1, 3, 17)), allocation_effect=index % 3 == 0))
