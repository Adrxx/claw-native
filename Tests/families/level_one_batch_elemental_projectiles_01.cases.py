"""Cases for level_one_batch_elemental_projectiles_01: Level 1 fire, lightning and ice sword projectiles.

Three near-identical profiles share their builders: state callback (cdecl, one object argument),
constructor (thiscall, one owner argument) and flight update (thiscall, no arguments).
Coverage is structural: every branch is reached by an explicit case, never by a lucky draw.
The random source only varies the values that flow through those branches.
"""
import math
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate
from clawparity import world as W

OPERATOR_NEW = 0x4F63EC
GLOBAL_FLAG = 0x53724C        # nonzero: the constructor keeps its animation pointer empty
GLOBAL_GAME = 0x5371FC        # pointer to a record whose +0x124 enables the logic lookup
GLOBAL_STEP_KEY = 0x5430C4    # read by the animation stepper called from the flight update
CACHE_LOW, CACHE_HIGH, CACHE_BASE, CACHE_STRIDE = 0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0

PROFILES = (
    dict(name="fire", callback=0x410100, ctor=0x410EC0, update=0x411310,
         proj=b"GAME_PROJECTILES_FIRESWORD", sword=b"GAME_FIRESWORD", vtable=0x50B7BC),
    dict(name="lightning", callback=0x4101C0, ctor=0x411370, update=0x4117C0,
         proj=b"GAME_PROJECTILES_LIGHTNINGSWORD", sword=b"GAME_LIGHTNINGSWORD", vtable=0x50B80C),
    dict(name="ice", callback=0x410280, ctor=0x411820, update=0x411C70,
         proj=b"GAME_PROJECTILES_ICESWORD", sword=b"GAME_ICESWORD", vtable=0x50B844),
)
BULLETS = b"GAME_BULLETS"
IDLE = b"LS_IDLE"


def double(value):
    return struct.pack("<d", value)


def word(rnd, low=1, high=0x7FFFFFFF):
    return rnd.randrange(low, high)


# ---------------------------------------------------------------------------------------
# Synthetic resources
# ---------------------------------------------------------------------------------------
def sprite_value(env, low, high, frame_words, name):
    """A sprite resource: frame table at +0x14, first and last frame numbers at +0x64 and +0x68."""
    slots = max(low, high, 0) + 2
    frames = []
    for index in range(slots):
        frame = env.object(0x28, f"{name}-frame{index}", fill=0)
        env.put(frame + 0x18, *[(w + index) & 0x7FFFFFFF for w in frame_words])
        frames.append(frame)
    table = env.object(4 * slots, f"{name}-frames", fill=0)
    env.put(table, *frames)
    resource = env.object(0x70, name, fill=0)
    env.put(resource + 0x14, table)
    env.put(resource + 0x64, low, high)
    return resource


def animation_value(env, count, entry_word, name):
    """An animation list: count at +0x10, entry table at +0xc, entries carry a duration at +0x1c."""
    entry = env.object(0x28, name + "-entry", fill=0)
    env.put(entry + 0x1C, entry_word)
    entries = env.object(8, name + "-entries", fill=0)
    env.put(entries, entry)
    animation = env.object(0x20, name, fill=0)
    env.put(animation + 0xC, entries)
    env.put(animation + 0x10, count)
    return animation


def build_owner(env, spec, state_extra=None):
    """The owner object (the spawning actor) with its level, resource maps and state record.

    spec keys: profile, base (None or (low, high)), proj, preset, sword, third, idle, values.
    """
    values = spec["values"]
    profile = spec["profile"]
    sprites = {}
    # every profile's projectile key is present with a distinct value, so a wrong key finds a wrong object
    for index, other in enumerate(PROFILES):
        range_ = spec["proj"] if other is profile else (index, index + 1)
        if range_ is not None:
            sprites[other["proj"]] = sprite_value(env, range_[0], range_[1], values["frame%d" % index], "proj-" + other["name"])
    if spec["base"] is not None:
        sprites[BULLETS] = sprite_value(env, spec["base"][0], spec["base"][1], values["bullet"], "bullets")
    animations = {}
    for index, other in enumerate(PROFILES):
        if other is not profile or spec["sword"]:
            animations[other["sword"]] = animation_value(env, 1 + index + (values["count"] if other is profile else 0),
                                                         values["entry%d" % index], "sword-" + other["name"])
    owner_words = {
        0x08: values["flags"], 0x4C: values["x"], 0x50: values["y"], 0x64: values["steps"],
        0x148: values["a148"], 0x14C: values["a14c"], 0x164: values["a164"],
        0x188 + 0x14: 0, 0x190: values["a190"], 0x170: 0, 0x174: values["a174"],
        0x48: values["n48"], 0x54: values["n54"], 0x60: values["n60"], 0x68: values["n68"],
    }
    if spec["preset"] is not None:
        owner_words[0x170] = sprite_value(env, spec["preset"][0], spec["preset"][1], values["preset"], "preset")
    # the state record chain used by the logic lookup: state +0xc -> scene +8 -> +0xc context -> +0x14 -> map
    flare_entries = {b"Decoy": values["decoy"]}
    if spec.get("flare", True):
        metadata = env.object(0x18, "flare-metadata", fill=0)
        env.put(metadata + 0x8, 2)
        env.put(metadata + 0x10, values["meta"])
        flare_entries[b"Flare"] = metadata
    flare = W.resource_manager(env, flare_entries, values["buckets"], "flare-map")
    context = env.object(0x40, "chain-context", fill=0)
    env.put(context + 0x14, flare)
    scene = env.object(0x40, "chain-scene", fill=0)
    env.put(scene + 0xC, context)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for index in range(63):
        env.put(pool + index * 12, pool + (index + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    chain_a = env.object(0x20, "chain-a", fill=0)
    env.put(chain_a + 0x8, scene)
    env.override(OPERATOR_NEW, lambda e, call: e.object(call.arguments[0], name="allocation",
                                                        fill=0 if call.arguments[0] == 0x158 else 0xB7))
    state_words = {0x0C: chain_a, 0x18: values["old_object"], 0x1C: values["state"],
                   0x2C: values["s2c"], 0x30: values["s30"], 0x34: values["s34"], 0x38: values["s38"]}
    state_words.update(state_extra or {})
    world = W.world(env, owner_words=owner_words, state_words=state_words,
                    resources={"sprites": sprites, "animations": animations}, collision_step=values["step"],
                    idle_state=values["idle"], bucket_count=values["buckets"])
    # the three global switches of the constructor
    mode = spec["third"]
    game = env.object(0x130, "game", fill=0)
    if mode == "flagged":
        env.put(game + 0x124, values["enable"])
        env.put(GLOBAL_FLAG, values["flag"])
        env.put(GLOBAL_GAME, game)
    elif mode == "flagged-null":
        env.put(GLOBAL_FLAG, values["flag"])
        env.put(GLOBAL_GAME, 0)
    elif mode == "disabled":
        env.put(GLOBAL_FLAG, 0)
        env.put(GLOBAL_GAME, game)
    else:
        env.put(game + 0x124, values["enable"])
        env.put(GLOBAL_FLAG, 0)
        env.put(GLOBAL_GAME, game)
    world["sprites"] = sprites
    world["animations"] = animations
    return world


def draw_values(rnd):
    return {
        "flags": word(rnd, 0, 0x7FFFFFFF) | (rnd.randrange(0, 2) << 4) | (rnd.randrange(0, 2) << 22),
        "x": rnd.randrange(100, 200), "y": -rnd.randrange(200, 300), "steps": rnd.randrange(30, 60),
        "n48": word(rnd), "n54": word(rnd), "n60": word(rnd), "n68": word(rnd), "meta": word(rnd),
        "a148": rnd.randrange(-50, 50), "a14c": rnd.randrange(-50, 50), "a164": word(rnd), "a190": word(rnd),
        "a174": word(rnd), "frame0": [word(rnd, 1, 200) for _ in range(4)], "frame1": [word(rnd, 1, 200) for _ in range(4)],
        "frame2": [word(rnd, 1, 200) for _ in range(4)], "bullet": [word(rnd, 1, 200) for _ in range(4)],
        "preset": [word(rnd, 1, 200) for _ in range(4)], "entry0": word(rnd, 1, 500), "entry1": word(rnd, 1, 500),
        "entry2": word(rnd, 1, 500), "count": rnd.randrange(0, 3), "decoy": word(rnd),
        "buckets": rnd.randrange(1, 12), "old_object": word(rnd), "state": word(rnd, 2, 0x1C),
        "s2c": rnd.randrange(-80, 80), "s30": rnd.randrange(-80, 80), "s34": rnd.randrange(-80, 80),
        "s38": rnd.randrange(-80, 80), "step": (rnd.randrange(1, 90), rnd.randrange(1, 90)),
        "idle": rnd.randrange(2, 0x1C), "flag": word(rnd), "game_pointer": 0, "enable": word(rnd),
    }


def spec_for(profile, rnd, base=(0, 0), proj=(0, 0), preset=None, sword=True, third="lookup", idle=True, flare=True):
    values = draw_values(rnd)
    if not idle:
        values["idle"] = None
    return dict(profile=profile, base=base, proj=proj, preset=preset, sword=sword, third=third, flare=flare, values=values)


# ---------------------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------------------
def constructor_setup(spec, rnd):
    marks = [word(rnd) for _ in range(4)]

    def setup(env):
        world = build_owner(env, spec)
        this = env.object(0x158, "projectile", fill=0)
        env.put(this + 0x148, marks[0])
        env.put(this + 0x14C, marks[1])
        env.put(this + 0x150, marks[2])
        env.put(this + 0x154, marks[3])
        return {"this": this, "owner": world["owner"], "state": world["state"]}
    return setup


# (base range, projectile range, preset range, sword found, third mode): a fixed table, every branch of the
# resource lookups and of the three-way switch appears on every profile
CONSTRUCTOR_TABLE = (
    ((0, 0), (0, 0), None, True, "lookup", True),
    ((0, 0), (0, 0), None, True, "disabled", True),
    ((0, 0), (0, 0), None, True, "flagged", True),
    (None, (2, 4), None, True, "lookup", True),
    (None, (1, 1), None, False, "disabled", True),
    ((1, 3), None, None, True, "lookup", True),
    ((2, 2), None, None, False, "flagged-null", True),
    (None, None, None, False, "lookup", False),
    (None, None, None, True, "disabled", True),
    ((0, 1), (3, 1), None, True, "disabled", False),
    ((3, 1), (2, 2), None, False, "lookup", False),
    ((0, 2), (1, 3), (0, 1), True, "lookup", True),
    ((0, 2), None, (2, 3), False, "flagged", True),
    (None, (4, 4), (1, 0), True, "lookup", True),
)


def constructor_cases(rnd):
    for profile in PROFILES:
        for index, (base, proj, preset, sword, third, flare) in enumerate(CONSTRUCTOR_TABLE):
            spec = spec_for(profile, rnd, base, proj, preset, sword, third, True, flare)
            setup = constructor_setup(spec, rnd)
            yield Case(f"{profile['name']} constructor {index}: base {base} projectile {proj} preset {preset} "
                       f"sword {sword} third {third} flare {flare}", profile["ctor"], setup,
                       receiver=lambda t: t["this"], arguments=(lambda t: t["owner"],))


# ---------------------------------------------------------------------------------------
# State callbacks
# ---------------------------------------------------------------------------------------
def virtual_object(env, slots, log):
    """An object whose virtual methods are logging stand-ins. slots: {offset: (argc, return value)}."""
    methods = env.object(0x40, "virtual-table", fill=0)
    for offset, (argc, result) in slots.items():
        def effect(env, call, result=result, offset=offset):
            index = env.get(log)
            env.put(log, index + 1)
            env.put(log + 4 + 16 * index, offset, call.receiver, call.arguments[0] if call.arguments else 0, index)
            return result
        env.put(methods + offset, env.stub(f"virtual+{offset:#x}", "thiscall", argc, effect))
    return methods


def cache_strings(env, count, stride, rnd_words):
    """The numbered string table consumed by the default state: CString slots `stride` bytes apart."""
    table = env.object(stride * count + 16, "string-table", fill=0)
    texts = []
    for index in range(count):
        text = b"text%02d" % index
        header = env.object(12 + 8, f"text{index}", fill=0)
        env.put(header, 1, len(text), 7)
        env.write(header + 12, text + b"\0")
        env.put(table + stride * index, header + 12)
        env.put(table + stride * index + 4, rnd_words[index % len(rnd_words)])
        texts.append(header + 12)
    return table


def callback_setup(spec, state, rnd, variant, stub_slot=False):
    log_words = [word(rnd) for _ in range(6)]
    results = [word(rnd) for _ in range(6)]
    low = rnd.randrange(-20, 20)
    count = rnd.randrange(2, 6)
    stride = (4, 8, 12)[rnd.randrange(0, 3)]
    position = variant % count

    def setup(env):
        log = env.object(0x100, "log", fill=0)
        slots = {0x04: (1, results[0]), 0x08: (1, results[1]), 0x0C: (1, results[2]),
                 0x1C: (0, results[3]), 0x20: (0, results[4])}
        methods = virtual_object(env, slots, log)
        record = env.object(0x30, "index-record", fill=0)
        env.put(record + 0x1C, low + position)
        controlled = env.object(0x30, "controlled", fill=0)
        env.put(controlled, methods)
        env.put(controlled + 0x10, record)
        env.put(controlled + 0x14, log_words[0])
        extra = {0x1C: state}
        if state not in (0,):
            extra[0x18] = controlled
        world = build_owner(env, spec, extra)
        if state == 0:
            if stub_slot:
                def observe_primary(env, call):
                    index = env.get(log)
                    env.put(log, index + 1)
                    primary = env.get(world["state"] + 0x18)
                    env.put(log + 4 + 16 * index, call.receiver, primary, env.get(world["state"] + 0x1C), env.get(call.receiver))
                    return 0
                env.put(spec["profile"]["vtable"] + 0x10, env.stub("projectile-slot-0x10", "thiscall", 0, observe_primary))
        else:
            table = cache_strings(env, count, stride, log_words)
            env.put(CACHE_LOW, low)
            env.put(CACHE_HIGH, low + count - 1)
            env.put(CACHE_BASE, table)
            env.put(CACHE_STRIDE, stride)
        return {"owner": world["owner"], "state": world["state"], "controlled": controlled, "log": log}
    return setup


CALLBACK_STATES = (0x1D, 0x1E, 0x3E8, 1, 0x0F, 0x1C, 0x1F, 0x3E7, 0x3E9, 0xFFFFFFFF, 0x80000000)


def callback_cases(rnd):
    for profile in PROFILES:
        for variant, (base, proj, preset, sword, third, idle) in enumerate((
                ((0, 0), (0, 0), None, True, "lookup", True),
                ((1, 2), (2, 3), None, False, "disabled", False),
                (None, (1, 1), (0, 2), True, "flagged", True),
                ((2, 1), None, None, True, "lookup", False))):
            spec = spec_for(profile, rnd, base, proj, preset, sword, third, idle)
            yield Case(f"{profile['name']} callback state 0 world {variant}", profile["callback"],
                       callback_setup(spec, 0, rnd, variant), arguments=(lambda t: t["owner"],))
        for index, state in enumerate(CALLBACK_STATES):
            spec = spec_for(profile, rnd, (0, 0), (0, 0), None, True, "lookup")
            yield Case(f"{profile['name']} callback state {state:#x}", profile["callback"],
                       callback_setup(spec, state, rnd, index), arguments=(lambda t: t["owner"],))
        # the virtual call on the new projectile is replaced by a stand-in that records the state record
        for variant in range(2):
            spec = spec_for(profile, rnd, (0, 0), (0, 0), None, True, "lookup" if variant else "disabled")
            yield Case(f"{profile['name']} callback state 0, observed slot 0x10 call {variant}", profile["callback"],
                       callback_setup(spec, 0, rnd, variant, True), arguments=(lambda t: t["owner"],))
        # the default branch reads the string table at several positions
        for index in range(1, 4):
            spec = spec_for(profile, rnd, (0, 0), (0, 0), None, True, "lookup")
            yield Case(f"{profile['name']} callback default state position {index}", profile["callback"],
                       callback_setup(spec, 1 + index, rnd, index), arguments=(lambda t: t["owner"],))


# ---------------------------------------------------------------------------------------
# Flight update
# ---------------------------------------------------------------------------------------
SPEEDS = (1.5, 0.0, -0.0, -3.25, 1e-300, 5e-324, 1e300, -1e300, math.inf, -math.inf, math.nan)
OFFSETS = (0.0, 0.5, -0.5, 7.75, -7.75, 19.999, -20.0, 2147483646.5, -2147483647.5, 3.0e9, -3.0e9,
           1e300, math.nan, 123456.789)


def update_setup(spec, rnd, speed, vertical, horizontal, projectile, step, stepper, mark, runs):
    junk = bytes(rnd.randrange(0, 256) for _ in range(0x158))
    target_junk = bytes(rnd.randrange(0, 256) for _ in range(0x60))
    words = [word(rnd) for _ in range(6)]

    def setup(env):
        owner_flags = spec["values"]["flags"] & ~0x10000
        owner_words = {0x08: owner_flags, 0x188 + 0x08: 0, 0x188 + 0x14: 0, 0x188 + 0x1C: 0,
                       0x188 + 0x20: words[0], 0x188 + 0x24: words[1], 0x188 + 0x28: words[2]}
        if stepper == "ready":
            owner_words.update({0x188 + 0x08: words[3], 0x188 + 0x1C: words[4]})
        world = W.world(env, owner_words=owner_words, idle_state=None)
        owner = world["owner"]
        env.put(GLOBAL_STEP_KEY, words[5])
        this = env.object(0x158, "projectile", data=junk)
        target = env.object(0x60, "target", data=target_junk) if projectile else 0
        env.write(this + 0x50, double(speed))
        env.write(this + 0x68, double(vertical))
        env.write(this + 0x70, double(horizontal))
        env.put(this + 0x120, step)
        env.put(this + 0x12C, owner)
        env.put(this + 0x148, mark)
        env.put(this + 0x150, target)
        return {"this": this, "owner": owner, "target": target}
    return setup


def update_cases(rnd):
    for profile in PROFILES:
        index = 0
        # every speed class against fixed and random offsets, with every branch of the helper
        for speed in SPEEDS:
            vertical = OFFSETS[(index * 3) % len(OFFSETS)]
            horizontal = OFFSETS[(index * 5 + 1) % len(OFFSETS)]
            spec = spec_for(profile, rnd)
            yield Case(f"{profile['name']} update speed {speed!r} offsets {vertical!r}, {horizontal!r}", profile["update"],
                       update_setup(spec, rnd, speed, vertical, horizontal, True, 0, "none", 0, 0),
                       receiver=lambda t: t["this"])
            index += 1
        for count in range(10):
            speed = rnd.choice((-1, 1)) * rnd.uniform(0.01, 100)
            vertical = rnd.uniform(-3000, 3000)
            horizontal = rnd.uniform(-3000, 3000)
            spec = spec_for(profile, rnd)
            step = word(rnd, 0, 0x7FFFFFFF) & ~0x10000 | (0x10000 if count % 2 else 0)
            mark = word(rnd) if count % 3 else 0
            stepper = ("ready", "none", "none")[count % 3]
            yield Case(f"{profile['name']} update random {count}", profile["update"],
                       update_setup(spec, rnd, speed, vertical, horizontal, True, step, stepper, mark, 0),
                       receiver=lambda t: t["this"])
        for speed in (2.5, -2.5):
            spec = spec_for(profile, rnd)
            yield Case(f"{profile['name']} update without a target, speed {speed}", profile["update"],
                       update_setup(spec, rnd, speed, 5.5, -6.5, False, 0x10000, "ready", word(rnd), 0),
                       receiver=lambda t: t["this"])
        spec = spec_for(profile, rnd)
        yield Case(f"{profile['name']} update with a target, step flag and animation", profile["update"],
                   update_setup(spec, rnd, 4.0, 11.25, -12.75, True, 0x10000, "ready", word(rnd), 0),
                   receiver=lambda t: t["this"])


def cases(random_source):
    yield from constructor_cases(random_source)
    yield from callback_cases(random_source)
    yield from update_cases(random_source)
