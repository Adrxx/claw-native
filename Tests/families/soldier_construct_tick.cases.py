"""Cases for soldier_construct_tick: Soldier construction and registered tick.

Owned: 0x48a980 (registered tick), 0x48aa40 (constructor), 0x48b6b0 (idle reset).
Everything the constructor calls except the declared fixtures runs as original code
over synthetic resource managers built with clawparity.world.
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate
from clawparity.world import cstring, rectangle_services, sprite, world

TICK = 0x48A980
CONSTRUCT = 0x48AA40
IDLE_RESET = 0x48B6B0
OPERATOR_NEW = 0x4F63EC

# animation key -> object offsets that receive its value (in constructor store order)
ANIMATIONS = (
    ("LEVEL_SOLDIER_ADVANCE", (0x308,)),
    ("LEVEL_SOLDIER_FASTADVANCE", (0x30C, 0x34C)),
    ("LEVEL_SOLDIER_STRIKE1", (0x310,)),
    ("LEVEL_SOLDIER_STRIKE", (0x370,)),
    ("LEVEL_SOLDIER_STAND", (0x318,)),
    ("LEVEL_SOLDIER_STAND1", (0x31C,)),
    ("LEVEL_SOLDIER_FALL", (0x32C, 0x374)),
    ("LEVEL_SOLDIER_HITLOW", (0x334,)),
    ("LEVEL_SOLDIER_HITHIGH", (0x338,)),
    ("LEVEL_SOLDIER_JUMP", (0x33C,)),
    ("LEVEL_SOLDIER_HOME", (0x344,)),
    ("LEVEL_SOLDIER_LIFTED", (0x378,)),
    ("LEVEL_SOLDIER_LIFTED2", (0x37C, 0x380)),
    ("LEVEL_SOLDIER_THROWN", (0x36C,)),
)
# sound key -> object offsets (all looked up in the level sound manager)
SOUNDS = (
    ("LEVEL_SOLDIER_00320006", (0x3A4,)),
    ("LEVEL_SOLDIER_00340016", (0x410,)),
    ("LEVEL_SOLDIER_00320005", (0x414, 0x418)),
    ("LEVEL_SOLDIER_RFHEADBT8-22", (0x3A0,)),
    ("LEVEL_SOLDIER_SOLGUNFR8-22", (0x3B4,)),
    ("LEVEL_SOLDIER_00320020", (0x460,)),
)
FLOAT_GLOBALS = (0x5262B8, 0x5262B4, 0x5262B0)
MODE_GLOBAL = 0x537964
IDLE_NUMBER_GLOBAL = 0x537210
TIMER_GLOBAL = 0x5430C4
MALLOC = 0x4A48E0
SET_RECT = 0x546D5C
SOLDIER_VTABLE = 0x50F774

FLAG_BITS_GLOBAL = 0x533470  # default bit count of the soldier flag set (inline up to 32, heap above)


def f32(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def word(random_source):
    return random_source.randrange(1, 0x100000000)


def moving_animation(env, random_source, name, frames=3):
    """A multi-frame animation whose first frame carries distinct timing words."""
    sequence = env.object(0x14, name, fill=0)
    table = env.object(4 * frames, name + "-frames", fill=0)
    env.put(sequence + 0xC, table, frames)
    for index in range(frames):
        frame = env.object(0x30, f"{name}-frame-{index}", fill=0)
        env.put(frame + 0x1C, random_source.randrange(1, 900))
        env.put(frame + 0x20, random_source.randrange(0, 60))
        env.put(frame + 0x24, random_source.randrange(0, 60))
        env.put(frame + 0x4, random_source.randrange(0, 8))
        env.put(frame + 0x10, random_source.randrange(0, 4))
        env.put(frame + 0x18, random_source.randrange(1, 500))
        env.put(table + 4 * index, frame)
    return sequence


def fresh_world(env, resources, *, bucket_count=1, idle_state=7, wide=True, state_words=None, owner_words=None):
    """Original-code world; the level record is widened because the soldier writes level +0x104/+0x10c."""
    rectangle_services(env)
    tokens = world(env, resources=resources, bucket_count=bucket_count, idle_state=idle_state,
                   owner_words=owner_words, state_words=state_words)
    if wide:
        old = tokens["world"]
        level = env.object(0x180, "wide-level", fill=0)
        env.write(level, env.read(old, 0x40))
        env.put(tokens["owner"] + 0xC, level)
        tokens["world"] = level
    # The owner's animation player at +0x188 points back at the owner (its +0x18c), where the sprite cursor lives.
    env.put(tokens["owner"] + 0x18C, tokens["owner"])
    return tokens


def resource_map(env, random_source, animation_mask, null_mode, sound_mask, sprite_mode, tag=0):
    """animation_mask bit i selects ANIMATIONS[i]; null_mode: 0 no GAME_NULL, 1 GAME_NULL present."""
    animations = {}
    values = {}
    for index, (key, offsets) in enumerate(ANIMATIONS):
        if animation_mask >> index & 1:
            if key == "LEVEL_SOLDIER_STAND":
                value = moving_animation(env, random_source, "stand")
            elif key == "LEVEL_SOLDIER_STAND1":
                value = env.object(0x20, "stand1", fill=0x31 + index)
            else:
                value = env.object(0x20, "anim-" + key, fill=0x31 + index)
            animations[key] = value
            values[key] = value
    if null_mode:
        animations["GAME_NULL"] = moving_animation(env, random_source, "game-null", frames=2)
    sounds = {}
    for index, (key, offsets) in enumerate(SOUNDS):
        if sound_mask >> index & 1:
            sounds[key] = 0x10000000 * (index + 1) + word(random_source) % 0x0FFFFFFF + tag
    for index, key in enumerate(("GAME_SOLHITL2", "GAME_SOLHITHI", "GAME_LELAND", "GAME_HIT1", "LEVEL_DEATHTILE")):
        sounds[key] = 0x0C000000 + 0x01010101 * (index + 1) + word(random_source) % 0xFFFF
    resources = {"animations": animations, "sounds": sounds}
    if sprite_mode == "hit":
        resources["sprites"] = {"LEVEL_SOLDIER": sprite(env, width=19, height=23, origin=(3, 5))}
    elif sprite_mode == "inverted":
        record = sprite(env, width=19, height=23)
        env.put(record + 0x64, 5, 2)  # first index above last index: the guarded lookup is skipped
        resources["sprites"] = {"LEVEL_SOLDIER": record}
    elif sprite_mode == "wide":
        record = sprite(env, width=19, height=23)
        env.put(record + 0x64, 0, 0)
        resources["sprites"] = {"LEVEL_SOLDIER": record}
    return resources


def set_globals(env, mode, multipliers, idle_number, timer):
    env.put(MODE_GLOBAL, mode)
    for address, value in zip(FLOAT_GLOBALS, multipliers):
        env.put(address, f32(value))
    env.put(IDLE_NUMBER_GLOBAL, idle_number)
    env.put(TIMER_GLOBAL, timer)


def construction(random_source, animation_mask, null_mode, sound_mask, sprite_mode,
                 mode=0, multipliers=(1.0, 1.0, 1.0), idle_state=7, bucket_count=1, direct=False,
                 allocation_hook=None, flag_bits=0x20, malloc_fails=False, observer=None, poke=False):
    seed = random_source.randrange(1, 1 << 30)

    def setup(env):
        local = type(random_source)(seed)
        resources = resource_map(env, local, animation_mask, null_mode, sound_mask, sprite_mode)
        owner_words = {0x4C: word(local), 0x50: word(local), 0x40: 0, 0x148: 2, 0x14C: 3}
        state_words = {0x64: local.randrange(0, 3), 0x68: word(local), 0x168: word(local) & 0xFF,
                       0x2C: -71, 0x30: 97, 0x34: -113, 0x38: 151, 0x1C: 0, 0x18: 0}
        tokens = fresh_world(env, resources, bucket_count=bucket_count, idle_state=idle_state,
                             owner_words=owner_words, state_words=state_words)
        set_globals(env, mode, multipliers, word(local), word(local))
        env.put(FLAG_BITS_GLOBAL, flag_bits)
        if malloc_fails:
            env.override(MALLOC, allocate(fail=True))
        if poke:
            fields = list(range(0x28C, 0x2CC, 4)) + [0x2E4, 0x2CC, 0x2D0, 0x450, 0x464, 0x468, 0x46C, 0x470]
            junk = {offset: 0x7E000000 + (offset << 8) + local.randrange(1, 255) for offset in fields}

            def rect_and_scribble(env, call):
                env.put(call.arguments[0], *call.arguments[1:])
                actor = tokens["actor"] if direct else tokens.get("built")
                for offset, value in junk.items():
                    env.put(actor + offset, value)
                return 1

            env.override(SET_RECT, rect_and_scribble)
        if observer:
            log = env.object(0x40, "slot-0x10-log", fill=0)
            replacement = env.object(0x180, "slot-replacement-state", fill=0x35)

            def slot(env, call):
                count = env.get(log)
                env.put(log, count + 1)
                env.put(log + 4 + 4 * min(count, 3), call.receiver)
                env.put(log + 0x14, env.get(tokens["state"] + 0x18), env.get(tokens["state"] + 0x1C),
                        env.get(tokens["owner"] + 0x6C), env.get(call.receiver + 0x10))
                if observer == "mutate":
                    env.put(tokens["owner"] + 0x6C, replacement)
                    env.put(tokens["state"] + 0x18, replacement)
                    env.put(tokens["state"] + 0x1C, 0x1234)
                return 0x5A5A0000 + count

            env.put(SOLDIER_VTABLE + 0x10, env.stub("soldier-vtable-slot-0x10", "thiscall", 0, slot))
        if direct:
            tokens["actor"] = env.object(0x480, "direct-soldier", fill=0x7D)
        else:
            def build(env, call):
                if allocation_hook:
                    allocation_hook(env, tokens)
                tokens["built"] = env.object(call.arguments[0], "soldier-allocation", fill=0x7D)
                return tokens["built"]
            env.override(OPERATOR_NEW, build)
        return tokens
    return setup


def tick_state_setup(command, salt, changing):
    """Copy of the registered-tick dispatch scene: child object with distinct virtual-slot observers."""
    def setup(env):
        owner = env.object(0x200, "dispatch-owner", fill=0x63)
        state = env.object(0x180, "dispatch-state", fill=0x47)
        other = env.object(0x180, "other-state", fill=0x59)
        child = env.object(0x488, "lifecycle-child", fill=0xA9)
        methods = env.object(0x24, "lifecycle-methods", fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, child, command)
        env.put(child, methods)
        env.put(child + 0x10, state)
        table = env.object(4, "state-string-table", fill=0)
        env.put(table, cstring(env, "command-" + str(salt)))
        env.put(0x5376A0, command, command, table, table, 4, 0, 0)
        replacement = env.object(0x24, "replacement-methods", fill=0)

        def effect(offset):
            def called(env, call):
                env.put(child + 0x44 + offset, salt ^ offset)
                env.put(child + 0x40, call.receiver)
                if changing:
                    env.put(owner + 0x6C, other)
                    env.put(state + 0x18, owner)
                    env.put(state + 0x1C, salt)
                    env.put(child, replacement)
                return salt ^ (offset * 13)
            return called

        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + offset, env.stub("child-method-%d" % offset, "thiscall", argc, effect(offset)))
            env.put(replacement + offset, env.stub("replacement-method-%d" % offset, "thiscall", argc, effect(offset)))
        return {"owner": owner, "state": state}
    return setup


def idle_reset_setup(random_source, anim_mode, idle_state, registry):
    seed = random_source.randrange(1, 1 << 30)

    def setup(env):
        local = type(random_source)(seed)
        resources = {}
        tokens = fresh_world(env, resources, idle_state=idle_state if registry else None, wide=False,
                             owner_words={}, state_words={0x1C: word(local)})
        obj = env.object(0x480, "idle-soldier", fill=0x6B)
        owner = tokens["owner"]
        record = owner + 0x188
        for offset in range(0x188, 0x1B0, 4):
            env.put(owner + offset, word(local))
        env.put(owner + 0x190, word(local))
        env.put(owner + 0x18C, owner)
        env.put(obj + 0x10, tokens["state"])
        env.put(obj + 0x12C, owner)
        env.put(obj + 0x50, word(local), word(local))
        env.put(obj + 0x24, word(local))
        env.put(obj + 0x134, word(local))
        env.put(obj + 0x474, word(local), word(local))
        if anim_mode == "none":
            env.put(obj + 0x318, 0)
        elif anim_mode == "single":
            env.put(obj + 0x318, moving_animation(env, local, "single-stand", frames=1))
        else:
            env.put(obj + 0x318, moving_animation(env, local, "multi-stand", frames=local.randrange(2, 6)))
        set_globals(env, local.randrange(0, 3), (1.0, 1.0, 1.0), word(local), word(local))
        tokens["object"] = obj
        tokens["record"] = record
        return tokens
    return setup


def cases(random_source):
    # ---- registered tick: every state dispatch arm, with and without a callee changing the record under it
    for command in (0, 1, 2, 28, 29, 30, 31, 32, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        if command == 0:
            continue
        for changing in (False, True):
            salt = random_source.randrange(1, 0x10000000)
            yield Case(f"tick state {command:#x} changing={changing}", TICK,
                       tick_state_setup(command, salt, changing), arguments=(lambda t: t["owner"],))

    # ---- registered tick, state 0: construct, publish, call virtual slot 0x10
    def moved_state(env, tokens):
        replacement = env.object(0x180, "replacement-state", fill=0x3D)
        env.put(tokens["owner"] + 0x6C, replacement)

    for hook in (None, moved_state):
        for mode in (0, 1):
            for observer in (None, "record", "mutate"):
                yield Case(f"tick state 0 construct hook={bool(hook)} mode={mode} slot={observer}", TICK,
                           construction(random_source, (1 << len(ANIMATIONS)) - 1, 1, 0x3F, "hit", mode=mode,
                                        allocation_hook=hook, observer=observer),
                           arguments=(lambda t: t["owner"],))
    for _ in range(12):
        yield Case("tick state 0 construct random resources", TICK,
                   construction(random_source, random_source.randrange(0, 1 << len(ANIMATIONS)), random_source.randrange(0, 2),
                                random_source.randrange(0, 0x40), random_source.choice(("hit", "none", "inverted", "wide")),
                                mode=random_source.randrange(0, 3), bucket_count=random_source.choice((1, 3, 17)),
                                idle_state=random_source.choice((None, 3, 90)), observer=random_source.choice((None, "record", "mutate")),
                                allocation_hook=random_source.choice((None, moved_state))),
                   arguments=(lambda t: t["owner"],))
    # ---- constructor called directly: lookup hit / fallback / miss for every resource key
    full = (1 << len(ANIMATIONS)) - 1
    base = dict()
    for null_mode in (0, 1):
        for sprite_mode in ("hit", "none", "inverted", "wide"):
            for sound_mask in (0, 0x3F):
                yield Case(f"construct all-or-nothing null={null_mode} sprite={sprite_mode} sounds={sound_mask:#x}", CONSTRUCT,
                           construction(random_source, full if sound_mask else 0, null_mode, sound_mask, sprite_mode, direct=True),
                           receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
    for index in range(len(ANIMATIONS)):
        for null_mode in (0, 1):
            yield Case(f"construct only animation {index} hits null={null_mode}", CONSTRUCT,
                       construction(random_source, 1 << index, null_mode, 0, "hit", direct=True),
                       receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
            yield Case(f"construct only animation {index} misses null={null_mode}", CONSTRUCT,
                       construction(random_source, full & ~(1 << index), null_mode, 0, "hit", direct=True),
                       receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
    for index in range(len(SOUNDS)):
        yield Case(f"construct only sound {index} hits", CONSTRUCT,
                   construction(random_source, 0, 1, 1 << index, "none", direct=True),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
        yield Case(f"construct only sound {index} misses", CONSTRUCT,
                   construction(random_source, full, 1, 0x3F & ~(1 << index), "none", direct=True),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
    for bucket_count in (1, 2, 3, 17):
        for _ in range(3):
            yield Case(f"construct random resources buckets={bucket_count}", CONSTRUCT,
                       construction(random_source, random_source.randrange(0, full + 1), random_source.randrange(0, 2),
                                    random_source.randrange(0, 0x40), random_source.choice(("hit", "none", "inverted", "wide")),
                                    bucket_count=bucket_count, direct=True),
                       receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))

    for bits in (1, 8, 9, 31, 32, 33, 64, 65, 200):
        yield Case(f"construct flag set of {bits} bits", CONSTRUCT,
                   construction(random_source, full, 1, 0x3F, "hit", direct=True, flag_bits=bits),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))

    for bits in (1, 5, 8):
        yield Case(f"construct flag set of {bits} bits, malloc fails", CONSTRUCT,
                   construction(random_source, full, 1, 0x3F, "hit", direct=True, flag_bits=bits, malloc_fails=True),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))

    # ---- the fields the constructor overwrites after the base class and fixtures wrote other values
    for mode in (0, 1, 2):
        for sound_mask in (0, 0x3F):
            for sprite_mode in ("hit", "none"):
                yield Case(f"construct scribbled fields mode={mode} sounds={sound_mask:#x} sprite={sprite_mode}", CONSTRUCT,
                           construction(random_source, full if sound_mask else 0, mode % 2, sound_mask, sprite_mode,
                                        mode=mode, direct=True, poke=True),
                           receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
    for hook in (None, moved_state):
        yield Case("tick state 0 scribbled fields", TICK,
                   construction(random_source, full, 1, 0x3F, "hit", poke=True, allocation_hook=hook),
                   arguments=(lambda t: t["owner"],))
    for _ in range(12):
        yield Case("construct random scribbled fields", CONSTRUCT,
                   construction(random_source, random_source.randrange(0, full + 1), random_source.randrange(0, 2),
                                random_source.randrange(0, 0x40), random_source.choice(("hit", "none")),
                                mode=random_source.randrange(0, 3), direct=True, poke=True),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))

    # ---- constructor tail: difficulty global and the float-scaled stat words
    for mode in (0, 1, 2, 0xFFFFFFFF):
        for multipliers in ((1.0, 1.0, 1.0), (4.0, 2.5, 0.5), (3.99999, 1.5, 3.7), (4.04, 0.3, 11.25),
                            (17.5, 33.0, 0.1), (-1.0, -2.0, -0.5), (0.0, 0.0, 0.0),
                            (3.92, 1.0, 1.0), (3.96, 1.0, 1.0), (3.9999, 1.0, 1.0), (4.0, 1.0, 1.0), (4.04, 0.34, 0.1),
                            (1.0, 1.34, 1.01), (1.0, 2.34, 0.099), (1.0, 2.0, 0.1), (1.0, 0.999, 0.3)):
            yield Case(f"construct tail mode={mode:#x} scale={multipliers}", CONSTRUCT,
                       construction(random_source, full, 1, 0x3F, "hit", mode=mode, multipliers=multipliers, direct=True),
                       receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
    for _ in range(40):
        multipliers = tuple(random_source.uniform(-3.0, 12.0) for _ in range(3))
        yield Case("construct random scales", CONSTRUCT,
                   construction(random_source, random_source.randrange(0, full + 1), 1, random_source.randrange(0, 0x40),
                                "hit", mode=random_source.randrange(0, 3), multipliers=multipliers,
                                idle_state=random_source.randrange(1, 100), direct=True),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))
    for idle in (None, 1, 0x7FFFFFFF):
        yield Case(f"construct idle registry {idle}", CONSTRUCT,
                   construction(random_source, full, 1, 0x3F, "hit", idle_state=idle, direct=True),
                   receiver=lambda t: t["actor"], arguments=(lambda t: t["owner"],))

    # ---- idle reset, called directly
    for registry in (True, False):
        for anim_mode in ("none", "single", "multi"):
            for idle_state in (1, 0x1D, 1000, 0xFFFFFFFF):
                yield Case(f"idle reset registry={registry} animation={anim_mode} idle={idle_state:#x}", IDLE_RESET,
                           idle_reset_setup(random_source, anim_mode, idle_state, registry),
                           receiver=lambda t: t["object"])
    for _ in range(30):
        yield Case("idle reset random", IDLE_RESET,
                   idle_reset_setup(random_source, random_source.choice(("single", "multi")),
                                    random_source.randrange(1, 0x7FFFFFFF), True),
                   receiver=lambda t: t["object"])
