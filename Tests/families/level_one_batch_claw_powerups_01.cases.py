"""Cases for level_one_batch_claw_powerups_01: Level 1 Claw powerup timers and flare.

Coverage is explicit and independent of the random seed; random_source only adds extra worlds and varies fillers.
"""
import random

from clawparity.cases import Case
from clawparity.fixtures import returns

M32 = 0xFFFFFFFF
MODE_SWITCH, TIMER_ADD, TICK, GLITTER, LIST_WALK = 0x41F990, 0x41F990, 0x420070, 0x448400, 0x4CE7B0
AIL_STATUS = 0x546E7C
NEW = 0x4F63EC

G_APP, G_PAUSED, G_MODE, G_TIMER = 0x5371FC, 0x53C9C0, 0x534EAC, 0x534EA8
G_SOUND_SESSION, G_SESSION_PAUSE, G_HELD = 0x53C9A4, 0x53C9A0, 0x537E88
G_FLARE_TIMER, G_FLARE_FRAME = 0x534EC8, 0x534ECC
G_ANIM = (0x5430B0, 0x5430B4, 0x5430B8, 0x5430BC)
CAP = 0xF3E58
BASE_MODE = 0x26B7
NAMES = {0x26B7: b"CLAW_1110064", 0x26BD: b"CLAW_1110064", 0x26B8: b"CLAW_1110001",
         0x26B9: b"CLAW_1110022", 0x26BA: b"CLAW_1110012"}


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def fill_table(env, r, table, entries, buckets):
    """A string table as 0x4f6286 reads it: +4 bucket array, +8 bucket count, nodes [next, 0, key, value]."""
    array = env.object(4 * buckets, "buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)


def registry(env, r, entries, buckets=7):
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    fill_table(env, r, owner + 0x10, entries, buckets)
    return owner


def sequence_object(env, r, alive, status):
    """A music sequence: vtable slots 0x20 alive, 0x24 start, 0x28 stop, 0x2c fade, 0x30 pause. +0x58 is the AIL handle,
    and the stand-in AIL_sequence_status answers with the handle itself."""
    vtable = env.object(0x40, "vtable", words=words_of(r, 0x10))
    obj = env.object(0x80, "sequence", words=words_of(r, 0x20))
    env.put(obj, vtable)
    env.put(obj + 0x58, status)
    env.put(vtable + 0x20, env.stub("alive", "thiscall", 0, returns(alive)))
    env.put(vtable + 0x24, env.stub("start", "thiscall", 2, returns(r.randrange(1, 1 << 32))))
    env.put(vtable + 0x28, env.stub("stop", "thiscall", 0, returns(r.randrange(1, 1 << 32))))
    env.put(vtable + 0x2C, env.stub("fade", "thiscall", 1, returns(r.randrange(1, 1 << 32))))
    env.put(vtable + 0x30, env.stub("pause", "thiscall", 0, returns(r.randrange(1, 1 << 32))))
    return obj


# Sequence states: absent from the registry, dead, alive but idle, alive and playing (status 4 or 0x10).
SEQ_STATES = (("absent", 0, 0), ("dead", 0, 4), ("idle", 1, 3), ("play4", 1, 4))
SEQ_EXTRA = (("play10", 1, 0x10), ("idle0", 1, 0))
CURRENT = ("none", "power", "level", "other")


def glitter_world(env, r, mode):
    """The scene seen through param_1+0xc+8. mode: junk (never read), missing (no GlitterMother), real (actor factory runs)."""
    zone = env.object(0x20, "zone", words=words_of(r, 8))
    if mode == "junk":
        scene = env.object(0x40, "scene", words=words_of(r, 0x10))
        env.put(zone + 8, scene)
        return zone
    if mode == "missing":
        scene = env.object(0x40, "scene", words=words_of(r, 0x10))
        w2 = env.object(0x40, "world2", words=words_of(r, 0x10))
        env.put(w2 + 0x14, registry(env, r, {b"Other": r.randrange(1, 1 << 32), b"GlitterMothe": 5}))
        env.put(scene + 0x0C, w2)
        env.put(zone + 8, scene)
        return zone
    w2 = env.object(0x40, "world2", fill=0)
    scene = env.object(0x40, "scene", fill=0)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for i in range(63):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    metadata = env.object(0x18, "actor-metadata", fill=0)
    env.put(metadata + 8, 0x2)
    env.put(metadata + 0x10, env.stub("metadata-notify", "cdecl", 1, returns(0)))
    env.put(w2 + 0x14, registry(env, r, {b"GlitterMother": metadata, b"Other": r.randrange(1, 1 << 32)}))
    env.put(scene + 0x0C, w2)
    env.put(zone + 8, scene)
    env.override(NEW, lambda env, call: env.object(call.arguments[0], "creation-allocation", fill=0xB7))
    return zone


def list_object(env, r, lo, hi, items, offset=0, extra_slots=4):
    """A list as 0x4ce7b0 walks it: +0x14 array, +0x64 first, +0x68 last. items maps index -> element kind."""
    count = max(1, max(items, default=0) + 1 + extra_slots)
    array = env.object(4 * (count + 8 + offset), "array", fill=0)
    elements = {}
    for index, kind in items.items():
        element = env.object(0x40, "element", words=words_of(r, 0x10))
        if kind == "null":
            env.put(array + 4 * (offset + index), 0)
            continue
        if kind == "nocomponent":
            env.put(element + 0x30, 0)
        else:
            component = env.object(0x40, "component", words=words_of(r, 0x10))
            env.put(element + 0x30, component)
        env.put(array + 4 * (offset + index), element)
        elements[index] = element
    obj = env.object(0x80, "list", words=words_of(r, 0x20))
    env.put(obj + 0x14, array + 4 * offset)
    env.put(obj + 0x64, lo & M32, hi & M32)
    return obj


def spec_world(*, seq=(SEQ_STATES[3], SEQ_STATES[3]), current="none", x_count=True, a14=1, paused=0, mode=0, timer=0, session="found",
               glitter="junk", list_items=None, o130=True, state=0x34, seed=1, held=False, wake=1, **_):
    """setup(env) for one call of 0x41f990."""

    def setup(env):
        r = random.Random(seed)
        env.override(AIL_STATUS, lambda env, call: call.arguments[0])
        for slot in G_ANIM:
            env.put(slot, r.randrange(1, 1 << 32))
        env.put(G_APP, 0)
        app = env.object(0x100, "app", words=words_of(r, 0x40))
        env.put(G_APP, app)
        env.put(app + 0x14, a14)
        env.put(G_PAUSED, paused)
        env.put(G_MODE, mode & M32)
        env.put(G_TIMER, timer & M32)
        # The sequence registry is embedded in the object at app+0x50 (the lookup receiver is that object itself).
        table = env.object(0x40, "sequence-table", words=words_of(r, 0x10))
        env.put(app + 0x50, table)
        objects = {}
        entries = {}
        for name, key in ((b"POWERUP", "power"), (b"LEVEL", "level")):
            label, alive, status = seq[0] if key == "power" else seq[1]
            if label == "absent":
                continue
            objects[key] = sequence_object(env, r, alive, status)
            entries[name] = objects[key]
        objects["other"] = sequence_object(env, r, 1, 4)
        entries[b"Decoy"] = objects["other"]
        fill_table(env, r, table, entries, 5)
        env.put(table + 0x1C, 0 if current == "none" else objects.get(current, 0))
        if not x_count:
            env.put(table + 0x20, 0)
        # Sound session behind 0x48c8a0.
        env.put(G_SESSION_PAUSE, 0)
        env.put(G_HELD, 0)
        if session == "none":
            env.put(G_SOUND_SESSION, 0)
        else:
            sess = env.object(0x200, "sound-session", words=words_of(r, 0x80))
            inner = env.object(0x40, "session-inner", words=words_of(r, 0x10))
            q = env.object(0x40, "session-state", words=words_of(r, 0x10))
            names = {n: r.randrange(1, 1 << 32) for n in set(NAMES.values())} if session == "found" else \
                {b"CLAW_1110000": 77}
            env.put(inner + 0x28, registry(env, r, names))
            env.put(sess + 0xC, inner)
            env.put(sess + 0x6C, q)
            env.put(G_SOUND_SESSION, sess)
            if held:
                held_state = env.object(0x40, "held-state", words=words_of(r, 0x10))
                held_logic = env.object(0x80, "held-logic", words=words_of(r, 0x20))
                env.put(held_logic + 0x1C, 0x138D)
                env.put(held_state + 0x6C, held_logic)
                env.put(G_HELD, held_state)
        # Claw object (param_1), pickup (param_3).
        claw = env.object(0x200, "claw", words=words_of(r, 0x80))
        zone = glitter_world(env, r, glitter)
        env.put(claw + 0xC, zone)
        if list_items is None:
            env.put(claw + 0x170, 0)
        else:
            env.put(claw + 0x170, list_object(env, r, *list_items))
        pickup = env.object(0x200, "pickup", words=words_of(r, 0x80))
        if o130:
            flagged = env.object(0x40, "flagged", words=words_of(r, 0x10))
            env.put(pickup + 0x130, flagged)
        else:
            env.put(pickup + 0x130, 0)
        return {"claw": claw, "pickup": pickup}

    return setup


def switch_case(label, new, p5, **world):
    return Case(label, MODE_SWITCH, spec_world(**world), arguments=(
        lambda t: t["claw"], world.get("seed", 1) * 0x10001 & M32 or 9, lambda t: t["pickup"], new & M32, p5 & M32))


def tick_world(timer, frame, state_slot, component="full", seed=1):
    def setup(env):
        r = random.Random(seed)
        for slot in G_ANIM:
            env.put(slot, r.randrange(1, 1 << 32))
        env.put(G_FLARE_TIMER, timer & M32)
        env.put(G_FLARE_FRAME, frame)
        claw = env.object(0x200, "claw", words=words_of(r, 0x80))
        if component == "none":
            env.put(claw + 0x174, 0)
        else:
            holder = env.object(0x80, "flare", words=words_of(r, 0x20))
            if component == "nochild":
                env.put(holder + 0x30, 0)
            elif component == "self":
                # 4c6130 stores the 0x5430b4 word over holder+0x30 itself, so the second null check can fail.
                env.put(holder + 0x30, holder + 0x14)
            else:
                child = env.object(0x40, "child", words=words_of(r, 0x10))
                env.put(holder + 0x30, child)
            env.put(claw + 0x174, holder)
        return {"claw": claw}

    return setup


def tick_case(label, timer, frame, dt, component="full", zero_anim=False, seed=1):
    base = tick_world(timer, frame, 0, component, seed)

    def setup(env):
        tokens = base(env)
        if zero_anim:
            env.put(G_ANIM[1], 0)
        return tokens

    return Case(label, TICK, setup, arguments=(lambda t: t["claw"], dt & M32))


def zero_claw_case(label, timer, frame, dt):
    def setup(env):
        env.put(G_FLARE_TIMER, timer)
        env.put(G_FLARE_FRAME, frame)
        return {}

    return Case(label, TICK, setup, arguments=(0, dt))


def glitter_case(label, claw_kind, seed=1):
    def setup(env):
        r = random.Random(seed)
        env.override(AIL_STATUS, lambda env, call: call.arguments[0])
        if claw_kind == "null":
            return {"claw": 0}
        zone = glitter_world(env, r, claw_kind)
        claw = env.object(0x200, "claw", words=words_of(r, 0x80))
        env.put(claw + 0xC, zone)
        return {"claw": claw}

    return Case(label, GLITTER, setup, arguments=(lambda t: t["claw"],))


def walk_world(lo, hi, items, offset=0, interference=None, seed=1):
    """A list for a direct 0x4ce7b0 call. interference: 'hi' or 'lo' makes component writes land on the list's own bounds."""

    def setup(env):
        r = random.Random(seed)
        for slot in G_ANIM:
            env.put(slot, r.randrange(0, 6) if interference else r.randrange(1, 1 << 32))
        obj = list_object(env, r, lo, hi, items, offset)
        if interference:
            first = min(i for i in items if items[i] == "full") if any(k == "full" for k in items.values()) else None
            if first is not None:
                element = env.get(env.get(obj + 0x14) + 4 * first)
                # component = obj+0x4c: 4c6130 writes obj+0x60 and obj+0x68; component = obj+0x50: writes obj+0x64, obj+0x6c.
                env.put(element + 0x30, obj + (0x4C if interference == "hi" else 0x50))
        return {"list": obj}

    return setup


def walk_case(label, param, lo, hi, items, **options):
    return Case(label, LIST_WALK, walk_world(lo, hi, items, **options), receiver=lambda t: t["list"], arguments=(param & M32,))


def cases(random_source):
    r = random_source
    # ---- 0x41f990: old mode by new mode, both the same-mode timer and the transition paths
    olds = (0, 0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC, 0x26BD, 0x26BE)
    news = (-1, 0, 1, 0x26B6, 0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC, 0x26BD, 0x26BE)
    items = {0: "full", 1: "null", 2: "nocomponent", 3: "full"}
    n = 0
    for old in olds:
        for new in news:
            for p5 in (0, 9):
                n += 1
                glitter = "real" if new == 0x26BC and old != new else "junk"
                yield switch_case(f"mode {old:#x} to {new & M32:#x} timer {p5}", new, p5, mode=old, timer=r.randrange(0, 1000),
                                  glitter=glitter, list_items=(0, 3, items) if n % 2 else None,
                                  o130=bool(n % 3), seed=n)
    # ---- same-mode timer accumulation and cap
    for mode in (0, 0x26B7, 0x26BE):
        for timer, add in ((0, 1), (5, 0), (100, 200), (CAP - 10, 10), (CAP - 10, 11), (CAP - 10, 9), (CAP, 0), (CAP, 1),
                           (CAP + 1, 0), (0xFFFFFFF0, 0x20), (0xFFFFFFFF, 0xFFFFFFFF), (1, M32)):
            yield switch_case(f"same mode {mode:#x}: {timer:#x} + {add:#x}", mode if mode else 5, add, mode=mode if mode else 5,
                              timer=timer, seed=timer & 0xFFFF or 3)
    # ---- music selection
    for new, p5 in ((0, 0), (0x26B8, 5)):
        for power in SEQ_STATES:
            for level in SEQ_STATES:
                for current in CURRENT:
                    yield switch_case(f"music {new:#x}/{p5} power {power[0]} level {level[0]} current {current}", new, p5,
                                      mode=0x26B9, timer=3, seq=(power, level), current=current, session="none",
                                      seed=hash((new, p5, power[0], level[0], current)) & 0xFFFF)
    for power in SEQ_EXTRA:
        for level in SEQ_EXTRA + SEQ_STATES[1:2]:
            for current in ("power", "level"):
                yield switch_case(f"music status power {power[0]} level {level[0]} current {current}", 0, 3, mode=0, seq=(power, level),
                                  current=current, session="none", seed=11)
                yield switch_case(f"music change {power[0]} {level[0]} current {current}", 0x26B8, 3, mode=0x26B9, seq=(power, level),
                                  current=current, session="none", seed=12)
    # ---- gates for the music selection
    for a14 in (0, 7):
        for paused in (0, 0x40):
            for x_count in (True, False):
                yield switch_case(f"gate a14 {a14} paused {paused} table {x_count}", 0, 4, mode=0x26B9, seq=(SEQ_STATES[3], SEQ_STATES[3]),
                                  current="power", a14=a14, paused=paused, x_count=x_count, session="none", seed=21)
                yield switch_case(f"gate change a14 {a14} paused {paused} table {x_count}", 0x26BA, 4, mode=0x26B9,
                                  seq=(SEQ_STATES[3], SEQ_STATES[2]), current="other", a14=a14, paused=paused, x_count=x_count,
                                  session="none", seed=22)
    # ---- sound session behind the announcement call
    for new in (0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BD):
        for session in ("none", "found", "missing"):
            for held in ((False, True) if session == "found" else (False,)):
                yield switch_case(f"announce {new:#x} session {session} held {held}", new, 2, mode=0x26BB, session=session, held=held,
                                  seed=new & 0xFF)
    # ---- flare creation
    for glitter in ("real", "missing"):
        for o130 in (True, False):
            yield switch_case(f"flare {glitter} pickup slot {o130}", 0x26BC, 6, mode=0x26BB, glitter=glitter, o130=o130, seed=31)
    # ---- leaving a mode, with and without a list or a flagged pickup
    for old in (0x26B7, 0x26BC, 0x26BD, 0x26B8):
        for lst in (None, (0, 0, {0: "full"}), (2, 4, {2: "full", 3: "nocomponent", 4: "full"})):
            for o130 in (True, False):
                yield switch_case(f"leave {old:#x} list {lst is not None} slot {o130}", 0x26B8, 2, mode=old, list_items=lst, o130=o130,
                                  seed=41 + old & 0xFF)
    # ---- random worlds
    for index in range(15):
        yield switch_case(f"random {index}", r.choice(news), r.choice((0, 0, r.randrange(1, 1 << 32), r.randrange(0, 5000))),
                          mode=r.choice(olds), timer=r.randrange(0, 1 << 32), seq=(r.choice(SEQ_STATES), r.choice(SEQ_STATES)),
                          current=r.choice(CURRENT), a14=r.randrange(0, 2), paused=r.randrange(0, 2),
                          session=r.choice(("found", "none", "missing")), glitter=r.choice(("real", "missing")),
                          list_items=r.choice((None, (0, 3, items))), o130=bool(r.randrange(2)), seed=r.randrange(1, 1 << 30))

    # ---- 0x420070: flare timer and frame cycle
    yield zero_claw_case("tick without claw", 50, 0x34, 7)
    yield zero_claw_case("tick without claw expiring", 5, 0x34, 7)
    for timer, dt in ((100, 1), (100, 99), (100, 100), (100, 101), (0, 0), (5, 4), (5, 6), (M32, M32), (7, M32)):
        for frame in (0x34, 0x35, 0x36, 0x37, 0x65, 0, 0x33):
            yield tick_case(f"tick {timer:#x}-{dt:#x} frame {frame:#x}", timer, frame, dt, seed=timer * 3 + frame & 0xFFFF)
    for component in ("none", "nochild", "self"):
        for zero_anim in ((False, True) if component != "self" else (True,)):
            for timer, dt in ((10, 20), (10, 3)):
                yield tick_case(f"tick component {component} zero {zero_anim} {timer}/{dt}", timer, 0x35, dt, component, zero_anim, seed=9)
    for index in range(5):
        yield tick_case(f"tick random {index}", r.randrange(0, 300), r.choice((0x34, 0x35, 0x36, 0x37, 0x65, r.randrange(0, 1 << 32))),
                        r.randrange(0, 300), r.choice(("full", "none", "nochild")), seed=r.randrange(1, 1 << 30))

    # ---- 0x448400
    yield glitter_case("flare factory without claw", "null")
    yield glitter_case("flare factory name missing", "missing")
    yield glitter_case("flare factory real", "real")
    yield glitter_case("flare factory real again", "real", seed=7)

    # ---- 0x4ce7b0: walk a list and send each component a request
    full = {i: "full" for i in range(5)}
    for param in (1, 2, 4, 8, 0x32, 0x33, 0, M32, 0x1234):
        yield walk_case(f"walk param {param:#x}", param, 0, 4, full, seed=param & 0xFFFF)
    mixed = {0: "null", 1: "full", 2: "nocomponent", 3: "full", 4: "null", 5: "full", 6: "nocomponent"}
    for lo, hi in ((0, 6), (1, 5), (3, 3), (4, 4), (2, 2), (5, 2), (0, 0), (6, 0), (-1, 1), (-2, 0), (0, 7)):
        yield walk_case(f"walk range {lo}..{hi}", 4, lo, hi, mixed, offset=3 if lo < 0 else 0, seed=(lo * 7 + hi) & 0xFFFF)
    for param in (2, 4, 8, 0x32, 5, 0):
        for place in ("hi", "lo"):
            yield walk_case(f"walk bound overwritten {place} param {param:#x}", param, 0, 3, {i: "full" for i in range(6)},
                            interference=place, seed=param + 5)
    for index in range(5):
        hi = r.randrange(0, 6)
        lo = r.randrange(-1, hi + 1)
        yield walk_case(f"walk random {index}", r.choice((1, 2, 4, 8, 0x32, r.randrange(0, 1 << 32))), lo, hi,
                        {i: r.choice(("full", "full", "null", "nocomponent")) for i in range(7)},
                        offset=2 if lo < 0 else 0, seed=r.randrange(1, 1 << 30))
