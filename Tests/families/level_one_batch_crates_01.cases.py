"""Cases for level_one_batch_crates_01: Level 1 stacked crates, crate hits and powder keg states."""
from clawparity.cases import Case
from clawparity.fixtures import sequence

LOGIC_SPAWN = 0x48D620
CRATE_HIT = 0x4717E0
GOODIE_CREATE = 0x40F450
GOODIE_SPRAY = 0x40F540
GOODIE_BY_INDEX = 0x4735B0
GOODIE_LOOKUP = 0x473610
HIT_UPDATE = 0x46FA90
HIT_TICK = 0x46FC20
BOUNCE_TICK = 0x40F400
RAND = 0x4A3050

GOODIE_COUNT = 0x52A190
GOODIE_TABLE = 0x537EC8
RANDOM_FLAG = 0x53721C
TICK_NOW = 0x537210
ANIM_PARAM = 0x5430C4
INIT_DONE = 0x538418
SOUND_READY = 0x532C0C
SOUND_ID = 0x532C10
WAKE_BASE = 0x541328
WAKE_LIMIT = 0x53C260
STRING_LO, STRING_HI, STRING_BASE, STRING_STRIDE = 0x5376A0, 0x5376A4, 0x5376A8, 0x5376B0
STRING_COUNT = 0x5376B8

PATTERN = bytes((index * 37 + 11) & 0xFF for index in range(0x440))


# ---------------------------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------------------------
def hash_string(text):
    value = 0
    for byte in text.encode():
        value = (value * 33 + (byte - 256 if byte > 127 else byte)) & 0xFFFFFFFF
    return value


def string_map(env, at, entries, buckets=7):
    """A string-to-pointer map embedded at `at` (bucket array at +4, bucket count at +8)."""
    slots = env.object(4 * buckets, "map-buckets", fill=0)
    heads = [0] * buckets
    for key, value in entries:
        text = env.object(len(key) + 1, "key-" + key, data=key.encode() + b"\0")
        slot = hash_string(key) % buckets
        heads[slot] = env.object(16, "map-node", words=[heads[slot], 0, text, value])
    env.put(slots, *heads)
    env.put(at + 4, slots, buckets)


def recorder(log, result=0, receiver=False, action=None):
    """A stand-in that appends (receiver, arguments) to a log object and returns `result`."""
    def effect(env, call):
        count = env.get(log)
        entry = log + 4 + 28 * count
        arguments = (list(call.arguments) + [0] * 5)[:5]
        env.put(log, count + 1)
        env.put(entry, call.receiver if receiver else 0, *arguments)
        if action:
            action(env, call)
        return result(env, call) if callable(result) else result
    return effect


def new_log(env):
    return env.object(0x400, "log", fill=0)


def sequence_object(env, start, end, tag):
    """A frame sequence: first index at +0x64, last at +0x68, frame pointers at +0x14."""
    size = max(start, end, 0) + 2
    frames = env.object(4 * size, "frames", words=[(tag << 8) + 0x1000 + i for i in range(size)])
    token = env.object(0x80, "sequence", fill=0)
    env.put(token + 0x14, frames)
    env.put(token + 0x64, start, end)
    return token


def set_goodies(env, count, entries):
    """Global goodie table: `entries` maps index to pointer."""
    env.put(GOODIE_COUNT, count)
    for index, value in entries.items():
        env.put(GOODIE_TABLE + 4 * index, value)


def goodie_world(env, descriptor_flags=0, crate=True, goodie=True, callback=True, body_fill=True, init_maps=None):
    """Level scene: manager with registry (BouncingGoodie, Crate), init callback that supplies actor bodies."""
    scene = env.object(0x80, "scene", fill=0)
    manager = env.object(0x60, "manager", fill=0)
    novel = env.object(0x40, "novel", fill=0)
    registry = env.object(0x40, "registry", fill=0)
    log = new_log(env)
    desc = env.object(0x40, "descriptor", fill=0)

    def supply_body(env, call):
        actor = call.arguments[0]
        logic = env.get(actor + 0x6C)
        if not env.get(logic + 0x18):
            body = env.object(0x440, "body", fill=0)
            if body_fill:
                env.write(body, PATTERN)
            env.put(logic + 0x18, body)

    env.put(desc + 8, descriptor_flags)
    if callback:
        env.put(desc + 0x10, env.stub("actor-init", "cdecl", 1, recorder(log, action=supply_body)))
    env.put(scene + 8, manager)
    env.put(manager + 0xC, novel)
    env.put(manager + 0x28, 10)
    env.put(novel + 0x14, registry)
    entries = []
    if goodie:
        entries.append(("BouncingGoodie", desc))
    if crate:
        entries.append(("Crate", desc))
    string_map(env, registry + 0x10, entries)
    tokens = {"scene": scene, "manager": manager, "log": log, "desc": desc, "registry": registry}
    if init_maps is not None:
        for slot, entries in zip((0x10, 0x14, 0x28), init_maps):
            owner = env.object(0x40, "init-owner", fill=0)
            string_map(env, owner + 0x10, entries)
            env.put(scene + slot, owner)
    return tokens


def init_entries(env):
    """Name tables for the table-initialising function: three frame sequences plus the other lookups."""
    sequences = [sequence_object(env, 1 + i, 3 + 2 * i, i + 1) for i in range(3)]
    treasure = [("GAME_TREASURE_COINS", sequences[0]), ("GAME_TREASURE_GOLDBARS", sequences[1]),
                ("GAME_TREASURE_RINGS_RED", sequences[2])]
    treasure += [("LEVEL_HEALTH", sequences[1]), ("LEVEL_GEM", sequences[2]), ("GAME_MAPPIECE", sequences[0])]
    powerup = [("TreasurePowerup", env.object(16, "powerup", fill=0x44))]
    sounds = [("GAME_COIN", env.object(16, "sound", fill=0x33)), ("GAME_RINGS", env.object(16, "rings", fill=0x22))]
    return sequences, [treasure, powerup, sounds]


# ---------------------------------------------------------------------------------------------
# 0x473610 and 0x4735b0
# ---------------------------------------------------------------------------------------------
def lookup_cases(random_source):
    def table(count):
        def setup(env):
            marks = [env.object(16, "goodie", fill=0x60 + i) for i in range(6)]
            set_goodies(env, count, {i: marks[i % 6] if i % 3 else 0 for i in range(min(count, 12))})
            return {"marks": marks}
        return setup
    for count in (5, 12):
        for index in (0, 1, 2, 3, count - 1, count, count + 1, -1, -2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            yield Case(f"lookup {index:#x} of {count}", GOODIE_LOOKUP, table(count), arguments=(index & 0xFFFFFFFF,))
    for _ in range(4):
        index = random_source.randrange(-3, 15)
        yield Case(f"lookup random {index}", GOODIE_LOOKUP, table(10), arguments=(index & 0xFFFFFFFF,))


def by_index_cases(random_source):
    def setup_for(index, init_done, stale=False, rand_flag=0, callback=True, goodie=True, level=0xD, rand_values=(9, 8)):
        def setup(env):
            env.put(0x537960, env.object(4, "level-number", words=[level]))
            sequences, maps = init_entries(env)
            tokens = goodie_world(env, init_maps=maps, callback=callback, goodie=goodie)
            env.put(INIT_DONE, init_done)
            env.put(RANDOM_FLAG, rand_flag)
            env.override(RAND, sequence(*rand_values))
            if init_done:
                set_goodies(env, 6, {0: sequences[0], 1: sequences[1], 2: sequences[2], 4: sequences[1]})
            else:
                stale_pointer = env.object(0x80, "stale", fill=0x7E)
                set_goodies(env, 6, {3: stale_pointer, 1: stale_pointer} if stale else {})
            return tokens
        return setup

    def args(index, x=0x123, y=0x456, z=0x78):
        return (lambda t: t["scene"], x, y, z, index & 0xFFFFFFFF)

    for init_done, indices in ((0, (-5, -1, 0, 1, 2, 3, 4, 5, 6, 31, 61, 62, 63, 100, 0x7FFFFFFF, 0x80000000)),
                               (1, (-5, -1, 0, 1, 2, 3, 4, 5, 6, 7, 100, 0x7FFFFFFF, 0x80000000)),
                               (0x100, (0, 1, 3))):
        for index in indices:
            yield Case(f"by-index {index:#x} init={init_done}", GOODIE_BY_INDEX, setup_for(index, init_done, stale=True),
                       arguments=args(index))
    for level in (1, 0xD, 0x2, 0x101):
        yield Case(f"by-index 31 level {level:#x}", GOODIE_BY_INDEX, setup_for(31, 0, level=level), arguments=args(31))
    yield Case("by-index random flag", GOODIE_BY_INDEX, setup_for(1, 1, rand_flag=1), arguments=args(1),
               )
    yield Case("by-index no registry entry", GOODIE_BY_INDEX, setup_for(1, 1, goodie=False), arguments=args(1))
    for _ in range(4):
        index = random_source.randrange(-1, 8)
        yield Case(f"by-index random {index}", GOODIE_BY_INDEX, setup_for(index, random_source.randrange(2)),
                   arguments=args(index, random_source.randrange(0x400000), random_source.randrange(0x800),
                                  random_source.randrange(0x100)))


# ---------------------------------------------------------------------------------------------
# 0x40f450
# ---------------------------------------------------------------------------------------------
def create_cases(random_source):
    def setup_for(index=1, start=2, end=4, rand_flag=0, rand_values=(1, 2), count=6, flags=0, **world):
        def setup(env):
            tokens = goodie_world(env, descriptor_flags=flags, **world)
            seq = sequence_object(env, start, end, 5)
            set_goodies(env, count, {1: seq, 2: seq, 3: 0})
            env.put(RANDOM_FLAG, rand_flag)
            env.override(RAND, sequence(*rand_values))
            tokens["sequence"] = seq
            return tokens
        return setup

    def call(label, x=0x200000, y=0x41, z=0x77, index=1, p6=17, p7=-300, **options):
        return Case(label, GOODIE_CREATE, setup_for(index, **options),
                    arguments=(lambda t: t["scene"], index & 0xFFFFFFFF, x, y, z, p6 & 0xFFFFFFFF, p7 & 0xFFFFFFFF))

    yield call("registry lacks the goodie", goodie=False)
    yield call("registry lacks the goodie, random", goodie=False, rand_flag=1)
    yield call("init callback missing", callback=False)
    yield call("init callback missing, no flag bit", callback=False, x=0x100)
    for flags in (0, 1, 2, 3):
        yield call(f"descriptor flags {flags}", flags=flags)
    for index in (1, 2, 3, 0, 6, 7, -1, 0x80000000):
        yield call(f"goodie index {index:#x}", index=index)
    yield call("x lacks bit 0x200000", x=0x1FFFFF, y=-9, z=0x31)
    yield call("x has only the callback bit", x=0x200000)
    yield call("sequence single frame", start=3, end=3)
    yield call("sequence start after end", start=4, end=2)
    yield call("sequence from zero", start=0, end=3)
    for p6, p7 in ((0, 0), (17, -300), (-5, 7), (0x7FFFFFFF, -0x80000000), (-0x80000000, 0x7FFFFFFF), (1000, -1)):
        yield call(f"plain velocity {p6},{p7}", p6=p6, p7=p7)
    for values in ((0,), (1000,), (1001,), (32767,), (500,), (2002,), (123456 & 0x7FFF,)):
        yield call(f"random velocity {values[0]}", rand_flag=1, rand_values=values, p6=-77, p7=99)
    yield call("random flag is any nonzero value", rand_flag=0x100, rand_values=(5000,), p6=33, p7=44)
    for _ in range(8):
        yield call("random mix", index=random_source.randrange(-1, 8), x=random_source.randrange(0x400000),
                   y=random_source.randrange(-500, 500), z=random_source.randrange(0, 300),
                   p6=random_source.randrange(-2000, 2000), p7=random_source.randrange(-2000, 2000),
                   rand_flag=random_source.randrange(2), rand_values=(random_source.randrange(32768),),
                   start=random_source.randrange(0, 4), end=random_source.randrange(0, 6),
                   flags=random_source.randrange(4))


# ---------------------------------------------------------------------------------------------
# 0x40f540
# ---------------------------------------------------------------------------------------------
SLOT_OFFSETS = (None, 0xF0, 0xF8, 0xF4, 0xFC, 0x100, 0x108, 0x104, 0x10C)  # scan order; None is the actor's own +0x100


def spray_cases(random_source):
    def setup_for(ids, rand_flag=0, rand_values=(7,), count=6, zero_entries=(4,), flags=0, **world):
        def setup(env):
            tokens = goodie_world(env, descriptor_flags=flags, **world)
            actor = env.object(0x120, "spray-actor", fill=0x21)
            logic = env.object(0x120, "spray-logic", fill=0x22)
            env.put(actor + 0x6C, logic)
            env.put(actor + 0xC, tokens["scene"])
            for offset, value in zip(SLOT_OFFSETS, ids):
                env.put((actor + 0x100) if offset is None else (logic + offset), value)
            entries = {}
            for index in range(1, count):
                entries[index] = 0 if index in zero_entries else sequence_object(env, 1 + index % 3, 4, index)
            set_goodies(env, count, entries)
            env.put(RANDOM_FLAG, rand_flag)
            env.override(RAND, sequence(*rand_values))
            tokens["actor"] = actor
            return tokens
        return setup

    def call(label, ids, x=0x200000, y=0x40, z=0x20, **options):
        ids = list(ids) + [0] * (9 - len(ids))
        return Case(label, GOODIE_SPRAY, setup_for(ids, **options),
                    arguments=(lambda t: t["actor"], x, y & 0xFFFFFFFF, z & 0xFFFFFFFF))

    yield call("nothing to spray", [])
    for slot in range(9):
        ids = [0] * 9
        ids[slot] = 1
        yield call(f"only slot {slot}", ids, rand_values=(11 + slot,))
    yield call("all nine valid", [1, 2, 3, 5, 1, 2, 3, 5, 1], rand_values=(0, 300, 301, 32767, 150, 299, 5, 600, 77))
    yield call("all nine valid, random velocity", [1, 2, 3, 5, 1, 2, 3, 5, 1], rand_flag=1,
               rand_values=(10, 1000, 20, 1001, 30, 2002, 40, 32767, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140))
    for count_ids in range(1, 9):
        ids = [1, 2, 3, 5, 1, 2, 3, 5][:count_ids]
        yield call(f"{count_ids} valid slots", ids, rand_values=(3, 250, 299, 300, 123, 9, 41, 8))
    # ids that are not sprayed still count towards the spacing
    yield call("invalid ids count: zero entry", [4, 1, 4, 2, 0, 3, 0, 0, 0])
    yield call("invalid ids count: negative", [-1, 1, -7, 2, 0x80000000, 3, 0, 0, 0])
    yield call("invalid ids count: at bound", [6, 1, 7, 2, 0x7FFFFFFF, 3, 0, 0, 0])
    yield call("invalid ids count: zero id", [0, 1, 0, 2, 0, 3, 0, 0, 0])
    yield call("boundary ids 1 and count-1", [1, 5, 1, 5, 1, 5, 1, 5, 1], rand_values=(1, 2, 3, 4, 5, 6, 7, 8, 9))
    yield call("x without callback bit", [1, 2, 0, 0, 0, 0, 0, 0, 0], x=0x1FFFFF)
    yield call("missing callback", [1, 2, 0, 0, 0, 0, 0, 0, 0], callback=False)
    yield call("registry lacks goodie", [1, 2, 0, 0, 0, 0, 0, 0, 0], goodie=False)
    yield call("descriptor flags", [1, 2, 3, 0, 0, 0, 0, 0, 0], flags=3)
    for _ in range(14):
        ids = [random_source.choice((0, 0, 1, 2, 3, 4, 5, 6, -1, 9)) & 0xFFFFFFFF for _ in range(9)]
        yield call("random mix", ids, x=random_source.randrange(0x400000), y=random_source.randrange(-100, 100),
                   z=random_source.randrange(0, 100), rand_flag=random_source.randrange(2),
                   rand_values=tuple(random_source.randrange(32768) for _ in range(18)),
                   flags=random_source.randrange(4))


# ---------------------------------------------------------------------------------------------
# 0x4717e0
# ---------------------------------------------------------------------------------------------
def crate_hit_cases(random_source):
    def setup_for(counter=1, busy=0, flag20=0x20, spawn_id=0, spawn_slots=(), index_id=1, rand_flag=0, rand_values=(10,),
                  sound_ready=1, flag_z=0, flag_scene=None, found=("GAME_CRATEBREAK", "GAME_CRATEBREAK2", "GAME_CRATEDAMAGE"),
                  sequence_spec=None, previous=0, wake_base=0, break_found=False, init_done=1, **world):
        def setup(env):
            maps = None
            if not init_done:
                _, maps = init_entries(env)
                env.put(0x537960, env.object(4, "level-number", words=[0xD]))
            tokens = goodie_world(env, init_maps=maps, **world)
            sequences = [sequence_object(env, 1 + i, 3 + i, 9 + i) for i in range(3)]
            set_goodies(env, 6, {1: sequences[0], 2: sequences[1], 3: sequences[2]})
            env.put(INIT_DONE, init_done)
            env.put(RANDOM_FLAG, rand_flag)
            env.override(RAND, sequence(*rand_values))
            env.put(SOUND_READY, sound_ready)
            env.put(SOUND_ID, 0x1234)
            hit = env.object(0x1D0, "crate", fill=0x31)
            logic = env.object(0x140, "crate-logic", fill=0x32)
            quirk = env.object(0xE0, "crate-flags", fill=0x33)
            env.put(hit + 0x6C, logic)
            env.put(hit + 0x74, quirk)
            env.put(hit + 0xC, tokens["scene"])
            env.put(quirk + 0xD0, flag20)
            env.put(quirk + 8, 0x1)
            env.put(logic + 0x130, busy)
            env.put(logic + 0x1C, 3)
            env.put(logic + 0x54, 0x1111)
            env.put(logic + 0x64, spawn_id)
            for offset, value in zip(SLOT_OFFSETS[1:], spawn_slots):
                env.put(logic + offset, value)
            env.put(hit + 0x170, 0)
            env.put(hit + 0x10C, counter)
            env.put(hit + 0x100, index_id)
            env.put(hit + 0x4C, 0x2468, 0x1357)
            env.put(hit + 0x64, 0x30)
            env.put(hit + 8, 0x800)
            # sound lookup tables: the damage branch reads them through the scene, the break branch through the logic
            level = env.object(0x40, "level", fill=0)
            env.put(logic + 0xC, level)
            for holder, flag in ((level, flag_z), (tokens["scene"], flag_scene if flag_scene is not None else flag_z)):
                sound_owner = env.object(0x40, "sound-owner", fill=0)
                env.put(holder + 0x28, sound_owner)
                env.put(sound_owner + 0x30, flag)
                entries = []
                for name in found:
                    x = env.object(0x90, "sound-x", fill=0)
                    w = env.object(0x20, "sound-w", words=[0, 0, 0, 0, x])
                    v = env.object(0x20, "sound-v", words=[0, 0, 0, 0, w])
                    entries.append((name, v))
                string_map(env, sound_owner + 0x10, entries)
            # animation of the crate and its cue table
            cue_owner = env.object(0x40, "cue-owner", fill=0)
            env.put(tokens["scene"] + 0x2C, cue_owner)
            cues = []
            if break_found:
                frame = env.object(0x40, "cue-frame", fill=0x44)
                env.put(frame + 0x1C, 0x99)
                list_ = env.object(8, "cue-list", words=[frame, 0])
                cue = env.object(0x40, "cue", fill=0)
                env.put(cue + 0xC, list_)
                env.put(cue + 0x10, 1)
                cues.append(("LEVEL_CRATEBREAK", cue))
            string_map(env, cue_owner + 0x10, cues)
            if sequence_spec is not None:
                start, end, frame_index, frames = sequence_spec
                seq = env.object(0x80, "hit-sequence", fill=0)
                array = env.object(4 * 8, "hit-frames", words=frames)
                env.put(seq + 0x14, array)
                env.put(seq + 0x64, start, end)
                env.put(hit + 0x170, seq)
                env.put(hit + 0x16C, frame_index)
                env.put(hit + 0x174, previous)
            tokens.update(hit=hit, logic=logic)
            return tokens
        return setup

    def call(label, **options):
        return Case(label, CRATE_HIT, setup_for(**options), arguments=(lambda t: t["hit"],))

    for flag20 in (0x20, 0x21, 0):
        yield call(f"busy early out flag {flag20:#x}", busy=1, flag20=flag20)
    yield call("busy high bit", busy=0x80000000)
    yield call("busy 500", busy=500, counter=0)
    # damage branch
    for counter in (2, 3, 100, 0x80000000, 0x7FFFFFFF):
        yield call(f"damage, counter {counter:#x}", counter=counter)
    yield call("damage, sound busy", counter=3, flag_scene=1)
    yield call("damage, only the logic sound is busy", counter=3, flag_z=1, flag_scene=0)
    yield call("damage, sound not ready", counter=3, sound_ready=0)
    yield call("damage, sound lookup fails", counter=3, found=("GAME_CRATEBREAK",))
    sequence_cases = (
        ("reset to start", (2, 5, 0, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("inside range", (2, 5, 1, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("last frame", (2, 5, 4, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("past last frame", (2, 5, 5, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("empty frame resets", (2, 5, 2, [0xA0, 0xA1, 0xA2, 0xA3, 0, 0xA5, 0xA6, 0xA7])),
        ("empty frame and empty first", (2, 5, 2, [0xA0, 0xA1, 0, 0xA3, 0, 0xA5, 0xA6, 0xA7])),
        ("start after end", (4, 2, 3, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("negative frame", (2, 5, -9, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("single frame", (3, 3, 2, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
        ("one before start", (3, 6, 1, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7])),
    )
    for label, spec in sequence_cases:
        yield call("damage, " + label, counter=2, sequence_spec=spec, previous=0xBEEF)
    # break branch, spray
    for value in (49, 50, 0, 99, 149, 150, 12345, 32767):
        yield call(f"break spray, rand {value}", counter=1, spawn_id=0, spawn_slots=(), rand_values=(value,))
    for value in (49, 50, 99, 150):
        yield call(f"break spray with goodies, rand {value}", counter=0, spawn_id=0, spawn_slots=(1, 2),
                   rand_values=(5, 6, value, value))
    yield call("break spray, sound busy", counter=1, flag_z=1, flag_scene=0, rand_values=(10,))
    yield call("break spray, only the scene sound is busy", counter=1, flag_z=0, flag_scene=1, rand_values=(10,))
    yield call("break spray, sound busy, high rand", counter=1, flag_z=1, flag_scene=0, rand_values=(60,))
    yield call("break spray, sound not ready", counter=1, sound_ready=0, rand_values=(10,))
    yield call("break spray, sound not ready, high rand", counter=1, sound_ready=0, rand_values=(77,))
    yield call("break spray, sound entries missing", counter=1, found=(), rand_values=(10,))
    yield call("break spray, second sound missing", counter=1, found=(), rand_values=(70,))
    yield call("break spray, cue found", counter=1, break_found=True, rand_values=(70,))
    yield call("break spray, cue found, entries only low", counter=1, break_found=True, found=("GAME_CRATEBREAK",),
               rand_values=(10,))
    for counter in (0, -1, -100):
        yield call(f"break counter {counter}", counter=counter & 0xFFFFFFFF, rand_values=(20,))
    # break branch, goodie by index
    for index_id in (1, 2, 3, 0, 9):
        yield call(f"break by index {index_id}", counter=1, spawn_id=3, index_id=index_id, rand_values=(40,))
    yield call("break by index, high rand", counter=1, spawn_id=0x80000000, index_id=2, rand_values=(88,))
    yield call("break by index, init pending", counter=1, spawn_id=1, index_id=2, init_done=0, rand_values=(88,))
    yield call("break by index, random velocity", counter=1, spawn_id=1, index_id=2, rand_flag=1,
               rand_values=(4000, 20, 30))
    for _ in range(10):
        spec = (random_source.randrange(0, 4), random_source.randrange(2, 7), random_source.randrange(-1, 7),
                [random_source.choice((0, random_source.randrange(1, 1 << 20))) for _ in range(8)])
        yield call("random mix", counter=random_source.randrange(-2, 5), busy=random_source.choice((0, 0, 0, 3)),
                   flag20=random_source.choice((0x20, 0)), flag_z=random_source.randrange(2),
                   sound_ready=random_source.randrange(2), spawn_id=random_source.choice((0, 0, 2, 3)),
                   index_id=random_source.randrange(0, 5), spawn_slots=(random_source.randrange(0, 6),),
                   sequence_spec=spec, previous=random_source.randrange(1 << 20),
                   rand_values=tuple(random_source.randrange(32768) for _ in range(4)),
                   break_found=bool(random_source.randrange(2)))


# ---------------------------------------------------------------------------------------------
# 0x46fa90, 0x46fc20, 0x40f400
# ---------------------------------------------------------------------------------------------
ANIM = 0x188


def anim_object(env, actor, returns, mode="steady"):
    """Fill the animation state at actor + 0x188 so that 0x4c82a0 returns `returns` without further machinery."""
    base = actor + ANIM
    if mode == "none":                 # +8 == 0: the call returns -1
        env.put(base + 8, 0)
        return
    env.put(base + 8, 1)
    env.put(base + 0x1C, 1)            # no frame advance machinery
    if mode == "steady":               # +0x14 == 0: returns +0x20
        env.put(base + 0x14, 0)
        env.put(base + 0x18, 0)
        env.put(base + 0x20, returns, returns ^ 0x55)
    elif mode == "countdown":          # +0x14 != 0, +0x18 == 0: returns +0x24 and decrements
        env.put(base + 0x14, 5, 0)
        env.put(base + 0x20, returns ^ 0x55, returns)
    elif mode == "elapsed":            # +0x14 != 0, +0x18 != 0, parameter below +0x14: returns +0x24
        env.put(base + 0x14, 0x7FFFFFF0, 1)
        env.put(base + 0x20, returns ^ 0x55, returns)
    elif mode == "expired":            # +0x14 != 0, +0x18 != 0, parameter not below: returns +0x20
        env.put(base + 0x14, 1, 1)
        env.put(base + 0x20, returns, returns ^ 0x55)


def hit_update_cases(random_source):
    def setup_for(returns=1, mode="steady", already=0, rect=True, mirror=False, flags=0x2, cue_a=0, cue_b=0,
                  wake=0, wake_limit=0, a_flags=0x10, anim_param=3, rect_values=(0x10, 0x20, 0x30, 0x40)):
        def setup(env):
            entity = env.object(0x240, "hit-entity", fill=0x41)
            actor = env.object(0x1D0, "hit-actor", fill=0x42)
            level = env.object(0x160, "hit-level", fill=0x43)
            box = env.object(0x30, "hit-box", fill=0)
            env.put(box + 0x18, *rect_values)
            env.put(entity + 0x12C, actor)
            env.put(entity + 0xC, level)
            env.put(entity + 0x1A0, already)
            env.put(entity + 0x220, 0xA0A0, 0xA1A1, 0xA2A2, 0xA3A3)
            env.put(actor + 8, a_flags)
            env.put(actor + 0x40, flags | (0x4 if mirror else 0))
            env.put(actor + 0x174, box if rect else 0)
            env.put(actor + 0x1A4, cue_a)
            env.put(actor + 0x19C, cue_b)
            env.put(level + 0x138, 0x1111, 0x2222, 0x3333, 0x4444)
            env.put(ANIM_PARAM, anim_param)
            env.put(WAKE_BASE, wake)
            env.put(WAKE_LIMIT, wake_limit)
            anim_object(env, actor, returns, mode)
            return {"entity": entity, "actor": actor}
        return setup

    def call(label, **options):
        return Case(label, HIT_UPDATE, setup_for(**options), receiver=lambda t: t["entity"])

    yield call("hit starts, rectangle, mirrored", flags=0x2)
    yield call("hit starts, rectangle, not mirrored", flags=0x1)
    yield call("hit starts, mirror among other bits", flags=0xFD | 0x2)
    yield call("hit starts, no mirror bit among others", flags=0xFD)
    yield call("hit starts, no rectangle", rect=False)
    yield call("hit starts, no rectangle, mirrored", rect=False, flags=0x2)
    yield call("hit already started", already=1)
    yield call("hit already started (any nonzero)", already=0x100)
    for returned in (0, 2, 0xFFFFFFFF, 0x100000001 & 0xFFFFFFFF, 0x80000001):
        yield call(f"animation returns {returned:#x}", returns=returned)
    yield call("animation absent", mode="none")
    for mode in ("countdown", "elapsed", "expired"):
        yield call(f"animation {mode}", mode=mode)
        yield call(f"animation {mode}, not one", mode=mode, returns=3)
    yield call("wake limit raised", wake=100, wake_limit=599)
    yield call("wake limit equal", wake=100, wake_limit=600)
    yield call("wake limit kept", wake=100, wake_limit=601)
    yield call("wake wraps", wake=0xFFFFFF00, wake_limit=0x10)
    yield call("wake large", wake=0xFFFFFE0C, wake_limit=0xFFFFFFFF)
    yield call("rectangle negative", rect_values=(-5, -7, 0x40, 0x30))
    yield call("rectangle empty", rect_values=(0x40, 0x30, 0x40, 0x30))
    yield call("rectangle wide", rect_values=(0, 0, 0x7FFFFFFF, 0x7FFFFFFF))
    yield call("rectangle inverted", rect_values=(0x50, 0x60, 0x10, 0x20))
    for a, b in ((1, 0), (1, 1), (0, 0), (0, 1), (0x80, 0), (7, 0x10000)):
        yield call(f"cue flags {a:#x},{b:#x}", cue_a=a, cue_b=b)
        yield call(f"cue flags {a:#x},{b:#x}, already", cue_a=a, cue_b=b, already=1)
    yield call("flag 0x80 already set", a_flags=0x80)
    yield call("flag 0x80 already set, no start", a_flags=0x80, returns=0)
    for _ in range(8):
        yield call("random mix", returns=random_source.choice((0, 1, 1, 2)), mode=random_source.choice(
            ("steady", "countdown", "elapsed", "expired", "none")), already=random_source.choice((0, 0, 1)),
            rect=bool(random_source.randrange(2)), flags=random_source.randrange(8), cue_a=random_source.randrange(3),
            cue_b=random_source.randrange(3), wake=random_source.randrange(1 << 32),
            wake_limit=random_source.randrange(1 << 32), a_flags=random_source.randrange(1 << 20),
            rect_values=tuple(random_source.randrange(-300, 300) for _ in range(4)))


def hit_tick_cases(random_source):
    def setup_for(state=1, returns=1, mode="steady", anim_param=3):
        def setup(env):
            entity = env.object(0x240, "tick-entity", fill=0x51)
            actor = env.object(0x1D0, "tick-actor", fill=0x52)
            level = env.object(0x160, "tick-level", fill=0x53)
            log = new_log(env)
            methods = env.object(0x100, "tick-methods", fill=0)
            vtable = env.object(4, "tick-vtable", words=[methods])
            env.put(methods + 0x7C, env.stub("tick-method", "thiscall", 0, recorder(log, receiver=True)))
            env.put(entity, methods)
            env.put(entity + 0x12C, actor)
            env.put(entity + 0xC, level)
            env.put(level + 0xCC, state)
            env.put(ANIM_PARAM, anim_param)
            anim_object(env, actor, returns, mode)
            return {"entity": entity, "log": log, "vtable": vtable}
        return setup

    def call(label, **options):
        return Case(label, HIT_TICK, setup_for(**options), receiver=lambda t: t["entity"])

    for state in (1, 0, 2, 0x100000001 & 0xFFFFFFFF, 0xFFFFFFFF, 0x80000000):
        yield call(f"level state {state:#x}", state=state)
    for mode in ("none", "countdown", "elapsed", "expired"):
        yield call(f"animation {mode}", mode=mode)
    yield call("animation param large", anim_param=0x7FFFFFFF, mode="expired")
    yield call("random state", state=random_source.randrange(3), anim_param=random_source.randrange(10))


def bounce_tick_cases(random_source):
    def setup_for(now, started, length, mode="steady", a_flags=0x4, anim_param=3):
        def setup(env):
            entity = env.object(0x240, "bounce-entity", fill=0x61)
            actor = env.object(0x1D0, "bounce-actor", fill=0x62)
            env.put(entity + 0x12C, actor)
            env.put(entity + 0x198, started, length)
            env.put(actor + 8, a_flags)
            env.put(TICK_NOW, now)
            env.put(ANIM_PARAM, anim_param)
            anim_object(env, actor, 1, mode)
            return {"entity": entity}
        return setup

    def call(label, now, started, length, **options):
        return Case(label, BOUNCE_TICK, setup_for(now, started, length, **options), receiver=lambda t: t["entity"])

    yield call("exactly elapsed", 1000, 900, 100)
    yield call("one short", 999, 900, 100)
    yield call("one over", 1001, 900, 100)
    yield call("zero length", 500, 500, 0)
    yield call("zero length, clock behind", 499, 500, 0)
    yield call("clock wrapped", 5, 0xFFFFFFF0, 0x20)
    yield call("clock wrapped, short", 5, 0xFFFFFFF0, 0x22)
    yield call("clock behind by one", 99, 100, 1)
    yield call("huge length", 0x7FFFFFFF, 0, 0x80000000)
    yield call("huge length, reached", 0x80000000, 0, 0x80000000)
    yield call("length high bit", 0xFFFFFFFF, 1, 0xFFFFFFFE)
    yield call("flag already set", 1000, 900, 100, a_flags=0x10000)
    yield call("flag not set when short", 999, 900, 100, a_flags=0xFFFEFFFF)
    for mode in ("none", "countdown", "elapsed", "expired"):
        yield call(f"animation {mode}", 1000, 900, 100, mode=mode)
    for _ in range(6):
        yield call("random clock", random_source.randrange(1 << 32), random_source.randrange(1 << 32),
                   random_source.randrange(1 << 32), a_flags=random_source.randrange(1 << 20))
        yield call("random near boundary", 5000 + random_source.randrange(-3, 4), 4000, 1000)


# ---------------------------------------------------------------------------------------------
# 0x48d620
# ---------------------------------------------------------------------------------------------
def logic_spawn_cases(random_source):
    def setup_for(state, logic_slots=(0, 0, 0, 0, 0, 0, 0, 0), actor_slot=0, z=0, key=None, group=True, **world):
        def setup(env):
            tokens = goodie_world(env, **world)
            log = tokens["log"]
            owner = env.object(0x180, "logic-owner", fill=0x71)
            logic = env.object(0x120, "logic-state", fill=0x72)
            env.put(owner + 0x6C, logic)
            # registry chain used by the logic constructor: owner+0xc -> +0x14 -> +0x10 map
            registry_holder = env.object(0x40, "registry-holder", fill=0)
            registry_owner = env.object(0x40, "registry-owner", fill=0)
            env.put(owner + 0xC, registry_holder)
            env.put(registry_holder + 0x14, registry_owner)
            string_map(env, registry_owner + 0x10, [])
            env.put(owner + 100, z)
            env.put(owner + 8, 0x40)
            env.put(owner + 0x40, 0x10)
            env.put(owner + 0x4C, 0x500, 0x300)
            env.put(owner + 0x100, actor_slot)
            env.put(owner + 0x148, 0x5151, 0x5252)
            level = env.object(0x40, "logic-level", fill=0)
            env.put(logic + 0xC, level)
            env.put(level + 8, tokens["manager"])
            env.put(logic + 0x1C, state)
            for offset, value in zip(SLOT_OFFSETS[1:], logic_slots):
                env.put(logic + offset, value)
            env.put(logic + 0x54, 0x77)
            # an object with a method table, standing for the logic that is already running
            methods = env.object(0x40, "running-methods", fill=0)
            running = env.object(0x40, "running-logic", words=[methods])
            running_owner = env.object(0x40, "running-owner", fill=0)
            env.put(running + 0x10, running_owner)
            env.put(methods + 0x1C, env.stub("running-1c", "thiscall", 0, recorder(log, receiver=True)))
            env.put(methods + 0x20, env.stub("running-20", "thiscall", 0, recorder(log, receiver=True)))
            if state not in (0,):
                env.put(logic + 0x18, running)
            # string table behind the default path
            if key is not None:
                low, high, stride = 10, 14, 4
                strings = env.object(stride * (high - low + 1), "string-slots", fill=0)
                for index in range(high - low + 1):
                    buffer = env.object(32, "string-buffer", fill=0x20 + index)
                    env.put(buffer, 1, 8 + index, 31)  # reference count, length, capacity
                    env.put(strings + stride * index, buffer + 12)
                env.put(STRING_LO, low, high, strings)
                env.put(STRING_STRIDE, stride)
                env.put(STRING_COUNT, 0)
                env.put(running_owner + 0x1C, key)
                for slot, name in ((4, "string-4"), (8, "string-8"), (0xC, "string-c")):
                    env.put(methods + slot, env.stub(name, "thiscall", 1, recorder(log, receiver=True)))
            tokens.update(owner=owner, logic=logic, running=running)
            return tokens
        return setup

    def call(label, state, **options):
        return Case(label, LOGIC_SPAWN, setup_for(state, **options), arguments=(lambda t: t["owner"],))

    yield call("state 0x1d", 0x1D)
    yield call("state 0x1e", 0x1E)
    yield call("state 1000", 1000)
    yield call("state 0 builds crates", 0)
    yield call("state 0 with crate slots", 0, logic_slots=(3, 4, 5, 6, 7, 8, 9, 10), actor_slot=2, z=1000)
    yield call("state 0 with crate slots, own slot clear", 0, logic_slots=(3, 0, 5, 0, 7, 0, 9, 0))
    yield call("state 0 sets depth", 0, z=0, actor_slot=0x20, logic_slots=(0x20, 0x20, 0, 0, 0, 0, 0, 0))
    yield call("state 0 keeps depth", 0, z=77)
    yield call("state 0 keeps depth 1000", 0, z=1000)
    for state in (1, 2, 0x1C, 0x1F, 999, 1001, 0xFFFFFFFF):
        for key in (10, 12, 14):
            if state in (1, 0x1F, 0xFFFFFFFF) or key == 12:
                yield call(f"state {state:#x} release key {key}", state, key=key)


# ---------------------------------------------------------------------------------------------
def cases(random_source):
    yield from lookup_cases(random_source)
    yield from by_index_cases(random_source)
    yield from create_cases(random_source)
    yield from spray_cases(random_source)
    yield from crate_hit_cases(random_source)
    yield from hit_update_cases(random_source)
    yield from hit_tick_cases(random_source)
    yield from bounce_tick_cases(random_source)
    yield from logic_spawn_cases(random_source)
