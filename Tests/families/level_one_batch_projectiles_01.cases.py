"""Cases for level_one_batch_projectiles_01: Level 1 pistol and magic bullets and enemy bullet logic.

Coverage does not depend on the random seed: every branch has an explicit case. The random source only
varies object contents, positions and scripted random numbers.
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import sequence

LOGIC_PISTOL = 0x40FF80   # state-0 builds the 0x410870 object (0x150 bytes)
LOGIC_MAGIC = 0x410040    # state-0 builds the 0x410900 object (0x158 bytes)
LOGIC_PLAIN = 0x40FEC0    # state-0 builds the 0x4107C0 object (0x150 bytes)
CTOR_PLAIN = 0x4107C0
CTOR_PISTOL = 0x410870
CTOR_MAGIC = 0x410900
SCATTER = 0x410D60
OPERATOR_NEW = 0x4F63EC
RAND = 0x4A3050

KEY_PISTOL = 0x524130     # strings that live in the original image
KEY_MAGIC = 0x52418C
KEY_FLAG = 0x52417C
KEY_SCATTER = 0x522594
KEY_MAGIC_EFFECT = 0x522E24
KEY_NAME_A = 0x522D54
KEY_NAME_B = 0x522D48

POOL_LOW, POOL_HIGH, POOL_BASE, POOL_STRIDE, POOL_COUNT = 0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0, 0x5376B8
GLOBAL_FLAG = 0x53724C
GLOBAL_SCENE = 0x5371FC


def zero_new(env, call):
    """operator new that hands out zeroed memory so both sides start from the same bytes."""
    return env.object(call.arguments[0], name="allocation", fill=0)


def hashed(env, key, buckets):
    value = 0
    for byte in env.cstr(key):
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & 0xFFFFFFFF
    return value % buckets


def registry(env, entries, buckets=1, name="registry"):
    """A name registry (hash map of C strings). entries: (key_address, value); earlier entries come first in
    their chain. Returns the registry object, which holds the map at +0x10."""
    reg = env.object(0x40, name, fill=0)
    table = env.object(max(4, 4 * buckets), name + "-buckets", fill=0)
    env.put(reg + 0x14, table)
    env.put(reg + 0x18, buckets)
    chains = {}
    for key, value in entries:
        chains.setdefault(hashed(env, key, buckets), []).append((key, value))
    for index, chain in chains.items():
        following = 0
        for key, value in reversed(chain):
            node = env.object(0x10, name + "-node", fill=0)
            env.put(node, following, 0x7000 + index, key, value)
            following = node
        env.put(table + 4 * index, following)
    return reg


def record(env, fill, size=0x80, name="record", **words):
    obj = env.object(size, name, fill=fill)
    for offset, value in words.items():
        env.put(obj + int(offset[1:], 16), value)
    return obj


def doubles(value):
    return struct.unpack("<II", struct.pack("<d", value))


def free_nodes(env, count):
    head = 0
    for _ in range(count):
        node = env.object(0xC, "free-node", fill=0)
        env.put(node, head)
        head = node
    return head


def make_world(env, r, lookups=(), flag_entries=(), name_entries=(), glitter=True, magic_effect=True,
               callback=True, scatter_count=3, buckets=1, alias_state=False):
    """The object graph the constructors and the scatter function walk.

    lookups: entries of the owner's lookup registry (W+0x10). flag_entries: registry at W+0x2c.
    name_entries: registry at W+0x14 holding the two names the base constructor looks for.
    """
    owner = env.object(0x400, "owner", fill=0)
    scene = env.object(0x100, "scene", fill=0)
    plane = record(env, 0, 0x100, "plane", **{"o64": 0x7FFFFFFF, "o68": 0x7FFFFFFF})
    if alias_state:
        state = owner + 0x15C  # the state object overlaps the owner: state+0x18 is owner+0x174
    else:
        state = env.object(0x200, "state", fill=0)
        env.put(state + 0x168, 0xD1D10168, 0xD1D1016C, 0xD1D10170, 0xD1D10174, 0xD1D10178)
        env.put(owner + 0x168, 0xC0C00168)
        env.put(owner + 0x178, 0xC0C00178)
    link = env.object(0x40, "state-link", fill=0)
    factory = env.object(0x80, "factory", fill=0)
    factory_scene = env.object(0x100, "factory-scene", fill=0)
    log = env.object(0x200, "effect-log", fill=0)

    def seen_effect(env, call):
        effect = call.arguments[0]
        number = env.calls_so_far(call.function) - 1
        env.put(log + 16 * number, effect, env.get(effect + 0x4C), env.get(effect + 0x50), env.get(effect + 0x64),
                env.get(effect + 0x6C), call.arguments[0])
        return 0

    definitions = []
    if glitter:
        function = env.stub("effect-callback", "cdecl", 1, seen_effect) if callback else 0
        definitions.append((KEY_SCATTER, record(env, 0x5A, 0x40, "definition-scatter",
                                                o08=0x1234 + r.randrange(0x100), o10=function)))
    if magic_effect:
        function = env.stub("effect-callback-magic", "cdecl", 1, seen_effect) if callback else 0
        definitions.append((KEY_MAGIC_EFFECT, record(env, 0x5B, 0x40, "definition-magic",
                                                     o08=0x4321 + r.randrange(0x100), o10=function)))
    effects = registry(env, definitions, buckets, "effects")
    env.put(factory_scene + 0x14, effects)

    env.put(owner + 0x0C, scene)
    env.put(owner + 0x6C, state)
    env.put(owner + 0x4C, 100 + r.randrange(50), 200 + r.randrange(50))
    env.put(owner + 0x64, 480 + r.randrange(100))
    env.put(owner + 0x118, 10, 20, 70, 90)
    env.put(owner + 0x148, 7, 9)
    env.put(scene + 0x10, registry(env, lookups, buckets, "lookups"))
    env.put(scene + 0x14, registry(env, name_entries, buckets, "names"))
    env.put(scene + 0x24, plane)
    env.put(scene + 0x2C, registry(env, flag_entries, buckets, "flags"))
    env.put(state + 0x0C, link)
    env.put(link + 0x08, factory)
    env.put(factory + 0x0C, factory_scene)
    env.put(factory + 0x20, free_nodes(env, scatter_count + 4))
    env.put(factory + 0x28, 10)
    return {"owner": owner, "scene": scene, "state": state, "factory": factory, "log": log,
            "effects": effects, "plane": plane}


def lookup_record(env, r, low, high, name="lookup-record"):
    """A record the owner's lookup finds: +0x64 low, +0x68 high, +0x14 an array of distinct values."""
    array = env.object(0x80, "lookup-array", fill=0)
    rects = []
    for i in range(32):
        rect = env.object(0x40, "lookup-rect", fill=0)
        env.put(rect + 0x18, 3 + i + r.randrange(5), 7 + 2 * i + r.randrange(5), 40 + 3 * i + r.randrange(9),
                30 + 5 * i + r.randrange(9))
        rects.append(rect)
    env.put(array, *rects)
    return record(env, 0x33, 0x80, name, o14=array, o64=low, o68=high), array


# ---------------------------------------------------------------------------------------------------
# callbacks

def callback_setup(state_value, mode="stub", pointer=True):
    """Owner whose state object holds `state_value` and a logic object with recording virtual slots."""

    def setup(env):
        r = LOCAL_RANDOM
        owner = env.object(0x80, "owner", fill=0x11)
        status = env.object(0x40, "state", fill=0x22)
        logic = env.object(0x40, "logic", fill=0x33)
        table = env.object(0x40, "vtable", fill=0)
        seen = env.object(0x40, "seen", fill=0)
        ident = record(env, 0x44, 0x40, "identity", o1c=0x300 + r.randrange(40))
        tokens = {"owner": owner, "status": status, "logic": logic, "seen": seen}

        def make(slot):
            def effect(env, call):
                n = env.get(seen)
                env.put(seen, n + 1)
                env.put(seen + 4 + 8 * (n % 6), slot, call.receiver)
                if slot in (4, 8, 0xC):
                    env.put(seen + 0x34 + 4 * (slot // 4 - 1), call.arguments[0] if call.arguments else 0xFEED)
                return 0x5000 + slot
            return effect

        for slot in (0x10, 0x1C, 0x20):
            env.put(table + slot, env.stub(f"logic-slot-{slot:#x}", "thiscall", 0, make(slot)))
        for slot in (4, 8, 0xC):
            env.put(table + slot, env.stub(f"logic-slot-{slot:#x}", "thiscall", 1, make(slot)))
        env.put(logic, table)
        env.put(logic + 0x10, ident)
        env.put(owner + 0x6C, status)
        env.put(status + 0x1C, state_value)
        env.put(status + 0x18, logic if pointer else 0)
        return tokens

    return setup


LOCAL_RANDOM = None


def pooled_setup(state_value, identity, bound=(0x10, 0x40), stride=0x10):
    """State that sends the callback into the pooled-release function: a CString slot table in globals."""
    base_setup = callback_setup(state_value)

    def setup(env):
        tokens = base_setup(env)
        low, high = bound
        slots = env.object(stride * (high - low + 1) + 16, "pool-slots", fill=0)
        text = env.object(0x40, "pool-text", fill=0x55)
        env.put(text, 1, 5, 0x20)  # reference count, length, capacity
        for index in range(high - low + 1):
            env.put(slots + stride * index, text + 12)
        env.put(POOL_LOW, low)
        env.put(POOL_HIGH, high)
        env.put(POOL_BASE, slots)
        env.put(POOL_STRIDE, stride)
        env.put(POOL_COUNT, 0)
        env.put(tokens["logic"] + 0x10, record(env, 0x44, 0x40, "identity", o1c=identity))
        tokens["text"] = text
        tokens["slots"] = slots
        return tokens

    return setup


def callback(label, function, setup, **options):
    return Case(label, function, setup, arguments=(lambda t: t["owner"],), **options)


def construct_setup(r, **options):
    def setup(env):
        env.override(OPERATOR_NEW, zero_new)
        tokens = make_world(env, r, **options)
        env.put(GLOBAL_FLAG, 1)
        env.put(tokens["state"] + 0x1C, 0)
        env.put(tokens["state"] + 0x18, 0xBAD0BAD0)
        return tokens
    return setup


# ---------------------------------------------------------------------------------------------------

def constructor_setup(r, preset=0, lookups=None, flag_value=None, globals_=None, effect=False, junk174=0x6161,
                      **options):
    """Setup for one constructor call: a fresh object plus the world."""

    def setup(env):
        env.override(OPERATOR_NEW, zero_new)
        entries = []
        arrays = {}
        for key, (low, high) in (lookups or {}).items():
            rec, array = lookup_record(env, r, low, high)
            entries.append((key, rec))
            arrays[key] = array
        flags = [(KEY_FLAG, flag_value)] if flag_value is not None else []
        tokens = make_world(env, r, lookups=entries, flag_entries=flags, magic_effect=effect, **options)
        env.put(tokens["owner"] + 0x170, preset)
        env.put(tokens["owner"] + 0x16C, 0x5151)
        env.put(tokens["owner"] + 0x174, junk174)
        tokens["this"] = env.object(0x160, "this", fill=0x44)
        tokens["arrays"] = arrays
        for address, value in ({GLOBAL_FLAG: 1, **(globals_ or {})}).items():
            if address == GLOBAL_SCENE:
                if value == 1:    # field +0x124 set, its neighbours clear
                    value = env.object(0x200, "global-scene", fill=0)
                    env.put(value + 0x124, 0x1000 + r.randrange(0x100))
                elif value == 2:  # field +0x124 clear, its neighbours set
                    value = env.object(0x200, "global-scene", fill=0x66)
                    env.put(value + 0x124, 0)
                    env.put(value + 0x120, 0x2000 + r.randrange(0x100))
                    env.put(value + 0x128, 0x3000 + r.randrange(0x100))
                else:
                    value = 0
            env.put(address, value)
        return tokens

    return setup


def ctor_case(label, function, setup):
    return Case(label, function, setup, receiver=lambda t: t["this"], arguments=(lambda t: t["owner"],))


def scatter_setup(r, count=2, extra=0, flags=0, rand_values=(), same=False, ranges=None,
                  position=(None, None), with_object=True, definitions=True, flag148=False):
    def setup(env):
        env.override(OPERATOR_NEW, zero_new)
        tokens = make_world(env, r, magic_effect=False, glitter=definitions, scatter_count=max(count, 1) + 4)
        owner = tokens["owner"]
        if ranges:
            env.put(owner + 0x118, *ranges)
        this = env.object(0x160, "this", fill=0x77)
        px = position[0] if position[0] is not None else r.uniform(-300, 300)
        py = position[1] if position[1] is not None else r.uniform(-300, 300)
        env.put(this + 0x0C, owner)
        env.put(this + 0x12C, owner)
        env.put(this + 0x130, tokens["state"])
        env.put(this + 0x68, *doubles(px), *doubles(py))
        env.put(this + 0x120, flags)
        env.put(this + 0x148, 0)
        env.put(this + 0x150, count)
        if with_object:
            target = env.object(0x80, "scatter-target", fill=0x12)
            env.put(this + 0x154, target)
            tokens["target"] = target
        else:
            env.put(this + 0x154, 0)
        if flag148:
            env.put(this + 0x148, 0x4040)
        if rand_values:
            env.override(RAND, sequence(*rand_values))
        tokens["this"] = this
        return tokens

    return setup


def scatter_case(label, setup):
    return Case(label, SCATTER, setup, receiver=lambda t: t["this"])


def cases(random_source):
    r = random_source
    global LOCAL_RANDOM
    LOCAL_RANDOM = r

    # --- the three callbacks: every state value
    for function in (LOGIC_PISTOL, LOGIC_MAGIC, LOGIC_PLAIN):
        name = f"{function:#x}"
        for state in (0x1D, 0x1E, 0x3E8):
            yield callback(f"{name} state {state:#x} calls its slot", function, callback_setup(state))
        yield callback(f"{name} state 0x1d via random owner contents", function,
                       callback_setup(0x1D))
        for state in (1, 0x1C, 0x1F, 0x3E7, 0x3E9, 0xFFFFFFFF, 0x80000000, 0x100000):
            identity = 0x10 + r.randrange(0x20)
            yield callback(f"{name} state {state:#x} releases the object", function,
                           pooled_setup(state, identity))
        yield callback(f"{name} state 2 releases the lowest pooled id", function, pooled_setup(2, 0x10))
        yield callback(f"{name} state 2 releases the highest pooled id", function, pooled_setup(2, 0x40))
        yield callback(f"{name} state 2 releases with single slot pool", function,
                       pooled_setup(2, 0x20, bound=(0x20, 0x20), stride=0x30))
        yield callback(f"{name} state 0x3e9 pool stride 4", function,
                       pooled_setup(0x3E9, 0x15, bound=(0x10, 0x18), stride=4))

    # --- state 0 builds the object through the original constructors
    for function in (LOGIC_PISTOL, LOGIC_MAGIC, LOGIC_PLAIN):
        name = f"{function:#x}"
        yield callback(f"{name} state 0 constructs, no lookups", function, construct_setup(r))
        yield callback(f"{name} state 0 constructs with found lookup", function,
                       _with_lookups(r, {KEY_PISTOL: (2, 9), KEY_MAGIC: (3, 8)}))
        yield callback(f"{name} state 0 constructs with empty range", function,
                       _with_lookups(r, {KEY_PISTOL: (9, 2), KEY_MAGIC: (8, 3)}))
        yield callback(f"{name} state 0 constructs with names registered", function,
                       construct_setup(r, name_entries=[]))

    # --- the new object's +0x10 call must see the previous object pointer slot (state+0x18 is owner+0x174)
    for function in (LOGIC_PISTOL, LOGIC_MAGIC, LOGIC_PLAIN):
        name = f"{function:#x}"
        yield callback(f"{name} state 0 aliased, record found", function,
                       _alias_zero(r, {KEY_PISTOL: (2, 9), KEY_MAGIC: (3, 8)}))
        yield callback(f"{name} state 0 aliased, other record index", function,
                       _alias_zero(r, {KEY_PISTOL: (5, 7), KEY_MAGIC: (6, 10)}))
        yield callback(f"{name} state 0 aliased, no record", function, _alias_zero(r, {}))
    yield callback("magic logic state 0 aliased, effect created", LOGIC_MAGIC,
                   _alias_zero(r, {KEY_MAGIC: (2, 6)}, globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, effect=True))

    # --- constructors called directly
    for function in (CTOR_PLAIN, CTOR_PISTOL, CTOR_MAGIC):
        name = f"{function:#x}"
        for preset in (0, 0x9999):
            for label, lookups in (
                ("no record", {}),
                ("record low<high", {KEY_PISTOL: (2, 9), KEY_MAGIC: (4, 11)}),
                ("record low==high", {KEY_PISTOL: (5, 5), KEY_MAGIC: (6, 6)}),
                ("record low>high", {KEY_PISTOL: (7, 6), KEY_MAGIC: (9, 3)}),
                ("record low=0", {KEY_PISTOL: (0, 4), KEY_MAGIC: (0, 2)}),
                ("record negative low above negative high", {KEY_PISTOL: (0xFFFFFFFE, 0xFFFFFFFB), KEY_MAGIC: (0xFFFFFFFF, 0xFFFFFFF0)}),
                ("pistol only", {KEY_PISTOL: (1, 12)}),
                ("magic only", {KEY_MAGIC: (3, 14)}),
            ):
                yield ctor_case(f"{name} preset {preset:#x} {label}", function,
                                constructor_setup(r, preset=preset, lookups=lookups))
        for buckets in (3, 7, 16):
            yield ctor_case(f"{name} {buckets} buckets with decoy in chain", function,
                            _decoy_setup(r, buckets))

    for flag in (None, 0, 0x11110000 + 0x1234, 0x7FFFFFFF):
        yield ctor_case(f"magic flag registry value {flag}", CTOR_MAGIC,
                        constructor_setup(r, lookups={KEY_MAGIC: (2, 6)}, flag_value=flag))
    # magic bullets create an effect only when the scene global says so
    sets = (
        ("global flag set, scene set", {GLOBAL_FLAG: 1, GLOBAL_SCENE: 1}, 1),
        ("global flag set, scene null", {GLOBAL_FLAG: 1, GLOBAL_SCENE: 0}, 0),
        ("global flag clear, scene set", {GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, 1),
        ("global flag high bit", {GLOBAL_FLAG: 0x80000000, GLOBAL_SCENE: 1}, 0),
    )
    for label, values, _ in sets:
        yield ctor_case(f"magic {label}", CTOR_MAGIC,
                        constructor_setup(r, lookups={KEY_MAGIC: (2, 6)}, globals_=values, effect=True))
    yield ctor_case("magic effect created for a flagged registry value", CTOR_MAGIC,
                    constructor_setup(r, lookups={KEY_MAGIC: (2, 6)}, flag_value=0x2468,
                                      globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, effect=True))
    yield ctor_case("magic world field clear, neighbours set", CTOR_MAGIC,
                    constructor_setup(r, lookups={KEY_MAGIC: (2, 6)},
                                      globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 2}, effect=True))
    yield ctor_case("magic world field clear, neighbours set, no record", CTOR_MAGIC,
                    constructor_setup(r, globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 2}, effect=False))
    yield ctor_case("magic world field set, neighbours clear, effect missing", CTOR_MAGIC,
                    constructor_setup(r, globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, effect=False))
    yield ctor_case("magic flag set, world field set", CTOR_MAGIC,
                    constructor_setup(r, globals_={GLOBAL_FLAG: 5, GLOBAL_SCENE: 1}, effect=True))
    yield ctor_case("magic flag set, world field clear", CTOR_MAGIC,
                    constructor_setup(r, globals_={GLOBAL_FLAG: 5, GLOBAL_SCENE: 2}, effect=True))
    yield ctor_case("magic effect definition missing", CTOR_MAGIC,
                    constructor_setup(r, globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, effect=False))
    for buckets in (1, 5):
        yield ctor_case(f"magic effect with {buckets} effect buckets", CTOR_MAGIC,
                        constructor_setup(r, globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, effect=True,
                                          buckets=buckets))
    for function in (LOGIC_MAGIC,):
        yield callback("magic logic state 0 creates the effect", function,
                       _magic_effect_state_zero(r))

    # --- scatter
    for count in (-3, 0):
        yield scatter_case(f"scatter count {count} does nothing", scatter_setup(r, count=count))
    yield scatter_case("scatter count 0 without target", scatter_setup(r, count=0, with_object=False))
    yield scatter_case("scatter count 1 default", scatter_setup(r, count=1, rand_values=(17, 29)))
    yield scatter_case("scatter count 1 flag 0x10000", scatter_setup(r, count=1, flags=0x10000,
                                                                      rand_values=(5, 6)))
    yield scatter_case("scatter count 1 flag other bits", scatter_setup(r, count=1, flags=0xFFFEFFFF,
                                                                         rand_values=(5, 6)))
    yield scatter_case("scatter prior flag word", scatter_setup(r, count=1, flag148=True, rand_values=(4, 3)))
    yield scatter_case("scatter without target and count 2", scatter_setup(r, count=2, with_object=False,
                                                                           rand_values=(1, 2, 3, 4)))
    for count in (2, 3):
        yield scatter_case(f"scatter count {count}", scatter_setup(
            r, count=count, rand_values=tuple(r.randrange(1, 100000) for _ in range(2 * count))))
    yield scatter_case("scatter negative random numbers", scatter_setup(
        r, count=2, rand_values=(0xFFFFFFF1, 0xFFFFFF00, 0xFFFFFFFF, 0x80000001)))
    yield scatter_case("scatter x range one wide", scatter_setup(r, count=1, ranges=(50, 60, 50, 90),
                                                                 rand_values=(123456, 7)))
    yield scatter_case("scatter y range one wide", scatter_setup(r, count=1, ranges=(10, 20, 70, 20),
                                                                 rand_values=(8, 123457)))
    yield scatter_case("scatter x range empty even random", scatter_setup(
        r, count=1, ranges=(10, 20, 9, 90), rand_values=(0x1234, 7)))
    yield scatter_case("scatter x range empty odd random", scatter_setup(
        r, count=1, ranges=(10, 20, 9, 90), rand_values=(0x1235, 7)))
    yield scatter_case("scatter y range empty even random", scatter_setup(
        r, count=1, ranges=(10, 20, 70, 19), rand_values=(7, 0x2234)))
    yield scatter_case("scatter y range empty odd random", scatter_setup(
        r, count=1, ranges=(10, 20, 70, 19), rand_values=(7, 0x2235)))
    yield scatter_case("scatter both ranges empty", scatter_setup(
        r, count=2, ranges=(30, 40, 29, 39), rand_values=(1, 2, 2, 1)))
    yield scatter_case("scatter inverted ranges", scatter_setup(
        r, count=1, ranges=(10, 20, 5, 4), rand_values=(1001, 2003)))
    yield scatter_case("scatter negative origin", scatter_setup(
        r, count=2, ranges=(-50, -40, 30, 60), position=(-123.75, -45.5),
        rand_values=(11, 12, 13, 14)))
    yield scatter_case("scatter fractional origin", scatter_setup(
        r, count=1, ranges=(1, 2, 3, 4), position=(99.99, 0.5), rand_values=(0x7FFFFFFF, 0x7FFFFFFE)))
    yield scatter_case("scatter definition missing", scatter_setup(r, count=0, definitions=False))
    for index in range(6):
        count = 1 + index % 3
        yield scatter_case(f"scatter random {index}", scatter_setup(
            r, count=count, ranges=(r.randrange(-100, 100), r.randrange(100, 300),
                                    r.randrange(-100, 100), r.randrange(100, 300)),
            rand_values=tuple(r.randrange(0, 1 << 32) for _ in range(2 * count)),
            with_object=bool(index % 2)))


def _with_lookups(r, lookups):
    base = constructor_setup(r, lookups=lookups)

    def setup(env):
        tokens = base(env)
        env.put(tokens["state"] + 0x1C, 0)
        env.put(tokens["state"] + 0x18, 0xBAD0BAD0)
        return tokens
    return setup


def _decoy_setup(r, buckets):
    def setup(env):
        env.override(OPERATOR_NEW, zero_new)
        rec_a, _ = lookup_record(env, r, 2, 9)
        rec_b, _ = lookup_record(env, r, 3, 12)
        decoy, _ = lookup_record(env, r, 1, 1, "decoy")
        entries = [(KEY_SCATTER, decoy), (KEY_NAME_A, decoy), (KEY_PISTOL, rec_a), (KEY_MAGIC, rec_b),
                   (KEY_NAME_B, decoy), (KEY_MAGIC_EFFECT, decoy)]
        tokens = make_world(env, r, lookups=entries, buckets=buckets, magic_effect=False)
        env.put(GLOBAL_FLAG, 1)
        env.put(tokens["owner"] + 0x170, 0)
        tokens["this"] = env.object(0x160, "this", fill=0x44)
        return tokens
    return setup


def _magic_effect_state_zero(r):
    base = constructor_setup(r, lookups={KEY_MAGIC: (2, 6)}, globals_={GLOBAL_FLAG: 0, GLOBAL_SCENE: 1}, effect=True)

    def setup(env):
        tokens = base(env)
        env.put(tokens["state"] + 0x1C, 0)
        env.put(tokens["state"] + 0x18, 0xBAD0BAD0)
        return tokens
    return setup


def _alias_zero(r, lookups, **options):
    base = constructor_setup(r, lookups=lookups, alias_state=True, junk174=0, **options)

    def setup(env):
        tokens = base(env)
        env.put(tokens["state"] + 0x1C, 0)
        return tokens
    return setup
