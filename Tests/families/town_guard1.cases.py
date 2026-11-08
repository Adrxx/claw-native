"""Cases for town_guard1: TownGuard1 object logic (0x496050).

The object at argument 0 has a state block at +0x6C. The block holds a state word at +0x1C and a
guard pointer at +0x18. States 0x1D, 0x1E and 0x3E8 are handled inline, state 0 builds a guard and
every other state goes through the string lookup at 0x4DC870, which reads a key from
guard->[+0x10]->[+0x1C] and finds a CString in a table whose bounds are program globals.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns  # noqa: F401
from clawparity import world as constructor_world

LOGIC = 0x496050
OPERATOR_NEW = 0x4F63EC

LOW, HIGH, STRIDE = 10, 25, 4
COUNT = HIGH - LOW + 1
G_LOW, G_HIGH, G_TABLE, G_STRIDE, G_PENDING_PTR, G_PENDING_COUNT = (
    0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0, 0x5376B4, 0x5376B8)


def world(state, key=12, rng=None, refs=1, capacity=15, on_method=None, table_range=(LOW, HIGH)):
    """setup(): object -> state block -> guard (with a vtable of recording methods) and a string table."""
    def setup(env):
        noise = (lambda: rng.randrange(1, 1 << 32)) if rng else (lambda: 0x11111111)
        obj = env.object(0x200, "town-guard-object", fill=0)
        block = env.object(0x40, "state-block", fill=0)
        guard = env.object(0x40, "guard", fill=0)
        vtable = env.object(0x80, "guard-vtable", fill=0)
        keyobj = env.object(0x40, "guard-key-object", fill=0)

        def method(slot, value):
            def effect(env, call):
                n = env.get(obj + 0x1F8)
                args = list(call.arguments) + [0]
                env.put(obj + 0x100 + 16 * n, call.receiver, slot, args[0], value)  # witness
                env.put(obj + 0x1F8, n + 1)
                if on_method:
                    on_method(env, slot, obj, guard)
                return value
            return effect

        for slot in range(0, 0x80, 4):
            argc = 1 if slot in (4, 8, 0xC) else 0
            env.put(vtable + slot, env.stub(f"guard-method-{slot:#x}", "thiscall", argc, method(slot, 0xA0000000 + slot)))
        env.put(guard, vtable)
        env.put(guard + 4, noise(), noise(), noise())
        env.put(guard + 0x10, keyobj)
        env.put(keyobj + 0x1C, key)
        entries = env.object(4 * COUNT, "string-entries", fill=0)
        for index in range(COUNT):
            text = env.object(12 + 16, f"string-{index}", fill=0)
            env.put(text, refs, 5 + index, capacity)  # CString header: refcount, length, capacity
            env.write(text + 12, bytes(65 + index + k for k in range(5)) + b"\0")
            env.put(entries + 4 * index, text + 12)
        env.put(G_LOW, table_range[0])
        env.put(G_HIGH, table_range[1])
        env.put(G_TABLE, entries)
        env.put(G_STRIDE, STRIDE)
        env.put(G_PENDING_PTR, 0)
        env.put(G_PENDING_COUNT, 0)
        env.put(obj + 0x20, noise(), noise(), noise())
        env.put(obj + 0x6C, block)
        env.put(block + 0x4, noise(), noise(), noise())
        env.put(block + 0x18, guard, state)
        return {"obj": obj, "block": block, "guard": guard, "vtable": vtable}
    return setup


def logic(label, setup, **options):
    return Case(label, LOGIC, setup, arguments=(lambda t: t["obj"],), **options)


def cases(random_source):
    for state in (0x1D, 0x1E, 0x3E8):
        yield logic(f"state {state:#x}", world(state))
        yield logic(f"state {state:#x} noisy", world(state, rng=random_source))
    for state in (0x1F, 0x1C, 1, 2, 0x1B, 0x3E7, 0x3E9, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0x100, 0x1E + 0x100):
        yield logic(f"lookup for state {state:#x}", world(state))
    for key in (LOW, LOW + 1, 17, HIGH - 1, HIGH):
        yield logic(f"key {key} at the table edge", world(0x3E9, key=key))
    for _ in range(10):
        state = random_source.randrange(2, 1 << 32)
        key = random_source.randrange(LOW, HIGH + 1)
        yield logic(f"random state {state:#x} key {key}", world(state, key=key, rng=random_source))
    yield logic("capacity zero", world(0x40, key=14, capacity=0))

    def swap_table(env, slot, obj, guard):
        if slot == 4:
            other = env.object(4 * COUNT, "other-entries", fill=0)
            for index in range(COUNT):
                text = env.object(12 + 16, f"other-string-{index}", fill=0)
                env.put(text, 1, 3, 9)
                env.write(text + 12, bytes(97 + index + k for k in range(3)) + b"\0")
                env.put(other + 4 * index, text + 12)
            env.put(G_TABLE, other)  # the second lookup must use the table as it is by then
    yield logic("table replaced between the two lookups", world(0x40, key=13, on_method=swap_table))

    def widen(env, slot, obj, guard):
        if slot == 4:
            env.put(G_LOW, LOW - 3)
            env.put(G_HIGH, HIGH + 3)
    yield logic("bounds widened between lookups", world(0x40, key=LOW, on_method=widen))


    for mode in ("empty", "missing", "fallback", "hit", "mixed", "sprite"):
        yield logic(f"construct resources {mode}", construction(resource_mode=mode))
    def replace_state_during_allocation(env):
        tokens = construction(resource_mode="hit")(env)
        replacement = env.object(0x180, "replacement-state", data=env.read(tokens["block"], 0x180))

        def allocation_effect(env, call):
            if env.calls_so_far(OPERATOR_NEW) == 1:
                env.put(tokens["obj"] + 0x6C, replacement)
                env.put(replacement + 0x1C, 0x13579BDF)
            return env.object(call.arguments[0], "allocation", fill=0)

        env.override(OPERATOR_NEW, allocation_effect)
        return tokens
    yield logic("construction changes owner state pointer during allocation",
                replace_state_during_allocation)
    for value in (0, 1, 19, 20, 49, 50, 99, 100, 149, 150, 32767):
        yield logic(f"construct rand {value}", construction(rand_value=value))
    for index in range(12):
        owner = {offset: random_source.randrange(1, 1024) for offset in
                 (0x4C, 0x50, 0x104, 0x108, 0x10C, 0x114, 0x148, 0x14C)}
        state = {offset: random_source.randrange(1, 128) for offset in
                 (0x2C, 0x30, 0x34, 0x38, 0x64, 0x68, 0x168)}
        mode = ("empty", "hit", "mixed")[index % 3]
        yield logic(f"random constructor {index} {mode}", construction(
            rand_value=random_source.randrange(0, 32768), resource_mode=mode,
            owner_words=owner, state_words=state,
            duration=random_source.randrange(1, 1000),
            dimensions=(random_source.randrange(1, 100), random_source.randrange(1, 100)),
            origin=(random_source.randrange(-50, 50), random_source.randrange(-50, 50)),
            bucket_count=(1, 7, 17)[index % 3], level=(1, 5, 6)[index % 3]))


def construction(rand_value=50, resource_mode="empty", owner_words=None,
                 state_words=None, duration=100, dimensions=(32, 32),
                 origin=(0, 0), bucket_count=17, level=1):
    """State-zero input; all creature methods and resource lookups run original code."""
    def setup(env):
        resources = {}
        if resource_mode in ("fallback", "hit", "mixed"):
            keys = ("GAME_NULL",) if resource_mode == "fallback" else (
                "LEVEL_TOWNGUARD1_ADVANCE", "LEVEL_TOWNGUARD1_FASTADVANCE",
                "LEVEL_TOWNGUARD1_STRIKE1", "LEVEL_TOWNGUARD1_KILLFALL",
                "LEVEL_TOWNGUARD1_IDLE1", "LEVEL_TOWNGUARD1_IDLE2",
                "LEVEL_TOWNGUARD1_HITLOW", "LEVEL_TOWNGUARD1_HITHIGH",
                "LEVEL_TOWNGUARD1_JUMP", "LEVEL_TOWNGUARD1_HOME",
                "LEVEL_TOWNGUARD1_LIFTED1", "LEVEL_TOWNGUARD1_LIFTED2",
                "LEVEL_TOWNGUARD1_THROWN", "GAME_NULL")
            if resource_mode == "mixed":
                keys = keys[::2]
            resources["animations"] = {
                key: constructor_world.animation(env, duration + index, f"animation-{key}")
                for index, key in enumerate(keys)}
        if resource_mode in ("hit", "mixed", "sprite"):
            resources["sprites"] = {
                "LEVEL_TOWNGUARD1": constructor_world.sprite(
                    env, *dimensions, origin=origin, name="guard-sprite")}
        if resource_mode == "missing":
            resources = {
                "animations": {"UNRELATED_ANIMATION": constructor_world.animation(env, duration)},
                "sprites": {"UNRELATED_SPRITE": constructor_world.sprite(env, *dimensions)}}
        tokens = constructor_world.world(
            env, owner_words=owner_words, state_words=state_words,
            resources=resources, bucket_count=bucket_count)
        constructor_world.rectangle_services(env)
        env.override(0x4A3050, returns(rand_value))
        env.put(0x537964, level)
        previous = env.object(0x20, "previous-guard", words=[0xABCDEF01], fill=0xA7)
        env.put(tokens["state"] + 0x18, previous, 0, 0xFEDCBA98)
        return {"obj": tokens["owner"], "block": tokens["state"]}
    return setup
