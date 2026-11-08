"""Cases for floor_spike: FloorSpike object logic (original 0x461d50, a registered per-frame object callback)."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

ENTRY = 0x461D50
HANDLER_A = 0x461FE0
HANDLER_B = 0x462000
HANDLER_C = 0x462020
FORWARD = 0x5295B0
BACKWARD = 0x52959C
LEVEL_UP = 0x5295C0
LEVEL_DOWN = 0x529584
CLOCK = 0x5430C4  # DAT_005430c4, the frame delta handed to the animation advance
TIMER = 0x537210  # DAT_00537210, the time handed to the phase check
SOUND_ON = 0x532C0C  # global tested at the top of the sound-play callee
OBJECT_SIZE = 0x200
STATE_SIZE = 0x180

RESET, UP, WAIT_DOWN, DOWN, WAIT_UP, SETTLE = 0, 0x3EA, 0x3EB, 0x3EC, 0x3ED, 0x3EE
SETTLE_B = 0x3EF
STATES = (RESET, UP, WAIT_DOWN, DOWN, WAIT_UP, SETTLE, SETTLE_B)


def hash_name(text):
    value = 0
    for byte in text:
        value = (value * 33 + (byte - 256 if byte > 127 else byte)) & 0xFFFFFFFF
    return value


def name_map(env, base, entries, buckets=7, decoy=True):
    """Fill the hash map embedded at base+0x10 with name -> value entries."""
    table = env.object(buckets * 4, "buckets", fill=0)
    env.put(base + 0x14, table)
    env.put(base + 0x18, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 1, "key", data=name + b"\0")
        node = env.object(0x10, "node", fill=0)
        slot = table + 4 * (hash_name(name) % buckets)
        head = env.get(slot)
        if decoy and not head:
            other = env.object(0x10, "decoy", fill=0)
            other_key = env.object(8, "decoykey", data=b"ZZ" + name[:3] + b"\0")
            env.put(other, 0, 0, other_key, 0xDEAD)
            env.put(node, other, 0, key, value)
        else:
            env.put(node, head, 0, key, value)
        env.put(slot, node)


def world(state, handler=0x400000, flags=0x12345678, owner=0, name_id=0x1234, d64=0, d104=0, rect=None,
          sub=(0, 0, 0, 0, 0), clock=0, timer=0, st_4c=10, st_bc=100, st_148=5, st_14c=0x214C, anims="none",
          sound="none", sound_on=0, extra=None, player=None):
    """setup() for one FloorSpike object.

    sub is (+8, +0x14, +0x18, +0x1c, +0x20) of the animation player embedded at object+0x188.
    anims: none (no names resolve), found (all four names resolve).
    sound: none (inert), missing (lookup finds nothing), found (name resolves).
    """
    def setup(env):
        obj = env.object(OBJECT_SIZE, "spike", fill=0)
        st = env.object(STATE_SIZE, "state", fill=0)
        parent = env.object(0x40, "parent", fill=0)
        holder = env.object(0x40, "anim-names", fill=0)
        sounds = env.object(0x40, "sounds", fill=0)
        env.put(parent + 0x28, sounds)
        env.put(parent + 0x2C, holder)
        env.put(obj + 0x08, flags)
        env.put(obj + 0x0C, parent)
        env.put(obj + 0x38, owner)
        env.put(obj + 0x4C, name_id)
        env.put(obj + 0x64, d64)
        env.put(obj + 0x6C, st)
        env.put(obj + 0xD0, 0x7777)
        env.put(obj + 0x104, d104)
        env.put(obj + 0x138, 0x1138, 0x113C, 0x1140, 0x1144)
        env.put(obj + 0x188 + 8, sub[0])
        env.put(obj + 0x188 + 0x14, sub[1])
        env.put(obj + 0x188 + 0x18, sub[2])
        env.put(obj + 0x188 + 0x1C, sub[3])
        env.put(obj + 0x188 + 0x20, sub[4])
        env.put(obj + 0x188 + 0x24, 0x2424)
        env.put(st + 0x10, handler)
        env.put(st + 0x1C, state)
        env.put(st + 0x4C, st_4c)
        env.put(st + 0xBC, st_bc)
        env.put(obj + 0x148, st_148, st_14c)
        for offset, value in (extra or {}).items():
            env.put(obj + offset, value)
        env.put(CLOCK, clock)
        env.put(TIMER, timer)
        env.put(SOUND_ON, sound_on)
        if rect is not None:
            box = env.object(0x40, "rect", fill=0)
            env.put(box + 0x18, *rect[:2])
            env.put(box + 0x20, *rect[2:])
            env.put(obj + 0x174, box)
        if anims == "found":
            records = {}
            for name in (FORWARD, BACKWARD):
                frame = env.object(0x40, "frame", fill=0)
                env.put(frame + 0x1C, 0x600 + name % 256)
                array = env.object(8, "frames", words=[frame, 0])
                record = env.object(0x20, "record", fill=0)
                env.put(record + 0x0C, array)
                env.put(record + 0x10, 1)
                records[env.cstr(name)] = record
            name_map(env, holder, records)
        else:
            name_map(env, holder, {})
        if sound != "none":
            a = env.object(0x40, "a", fill=0)
            b = env.object(0x80, "b", fill=0)
            env.put(sounds + 0x0C, a)
            env.put(a + 0x24, b)
            env.put(b + 0x5C, 0x5C5C)
            env.put(b + 0x84, 0)
            if sound == "found":
                up, down = player(env, name_id) if player else (0x1111, 0x2222)
                values = {env.cstr(LEVEL_UP): up, env.cstr(LEVEL_DOWN): down}
            else:
                values = {}
            name_map(env, sounds, values)
        else:
            a = env.object(0x40, "a", fill=0)
            env.put(sounds + 0x0C, a)
        return {"obj": obj, "st": st}
    return setup


def sound_player(delta_up, delta_down):
    """A sound source the player at 0x4c88e0 can drive all the way to its voice calls.

    The base id it subtracts from the object's id is the id minus delta, so the pan argument follows the id.
    """
    def build(env, name_id):
        voices = []
        for tag, delta in (("up", delta_up), ("down", delta_down)):
            vtable = env.object(0x60, "vtable-" + tag, fill=0)
            # Slot 0x24 is handed the address of a stack local, which differs between the two sides, so it points
            # at a tiny original function (xor eax, eax; ret 8) that runs as original code instead of a stand-in.
            env.put(vtable + 0x24, 0x40AF40)
            for offset, argc in ((0x30, 4), (0x3C, 2), (0x40, 2), (0x44, 2)):
                env.put(vtable + offset, env.stub(f"voice-{tag}-{offset:#x}", "stdcall", argc, returns(0)))
            device = env.object(0x20, "device-" + tag, words=[vtable])
            engine = env.object(0x90, "engine-" + tag, fill=0)
            env.put(engine + 0x78, 1)
            voice = env.object(0x40, "voice-" + tag, fill=0)
            env.put(voice + 0x0C, device)
            env.put(voice + 0x10, engine)
            env.put(voice + 0x14, 0xF)
            env.put(voice + 0x18, 0x3000 + delta)
            env.put(voice + 0x30, 1)
            source = env.object(0x40, "source-" + tag, fill=0)
            env.put(source + 0x10, engine)
            env.put(source + 0x18, 0x1111 + delta)
            env.put(source + 0x1C, 0x2222 + delta)
            env.put(source + 0x20, 0x3333 + delta)
            env.put(source + 0x30, voice + 4)
            unit = env.object(0x20, "unit-" + tag, fill=0)
            env.put(unit + 0x10, 300 + delta)
            holder = env.object(0x20, "holder-" + tag, fill=0)
            env.put(holder + 0x10, unit)
            bank = env.object(0x90, "bank-" + tag, fill=0)
            env.put(bank + 0x84, (name_id - delta) & 0xFFFFFFFF)
            level = env.object(0x40, "level-" + tag, fill=0)
            env.put(level + 0x24, bank)
            env.put(level + 0x04, holder)
            # +0x5c of the bank's owner is read through level+0x24: bank is that owner, so point +0x5c at itself.
            env.put(bank + 0x5C, bank)
            player = env.object(0x40, "player-" + tag, fill=0)
            env.put(player + 0x0C, level)
            env.put(player + 0x10, source)
            voices.append(player)
        env.put(0x532C10, 100)
        # The pan and volume tables the voice setup indexes: 101 words ending at 0x541308, all different.
        for index in range(101):
            env.put(0x541308 - 4 * index, 0x1000 + 37 * index)
        return tuple(voices)
    return build


def spike(label, setup):
    return Case(label, ENTRY, setup, arguments=(lambda tokens: tokens["obj"],))


def cases(random_source):
    # Dispatch: every state value near the table edges, and far outside it.
    for state in (0, 1, 0x3E9, 0x3EA, 0x3EB, 0x3EC, 0x3ED, 0x3EE, 0x3EF, 0x3F0, 0x3F1, 0x7FFFFFFF, 0x80000000,
                  0xFFFFFFFF, 0xFFFFFC15 + 0x3EB):
        yield spike(f"state {state:#x}", world(state))

    # State 0 (reset): rect copy, flags, defaults, handler-specific base values.
    for handler in (0x400000, HANDLER_A, HANDLER_B, HANDLER_C):
        for d64 in (0, 77):
            for d104 in (0, 33):
                yield spike(f"reset handler {handler:#x} d64={d64} d104={d104}",
                            world(RESET, handler=handler, d64=d64, d104=d104))
    for rect in ((0, 0, 0, 0), (3, 5, 20, 40), (100, 200, 7, 9), (0xFFFFFFF0, 0xFFFFFFF8, 5, 6),
                 (0x7FFFFFFF, 0x7FFFFFFF, 0x7FFFFFFF, 0x7FFFFFFF)):
        yield spike(f"reset rect {rect}", world(RESET, rect=rect, d64=1, d104=1))
    for flags in (0, 0xFFFFFFFF, 0x80, 0x20000, 0x7F, 0xFFFFFF7F, 0x12340000):
        for d64 in (0, 9):
            yield spike(f"reset flags {flags:#x} d64={d64}", world(RESET, flags=flags, d64=d64))
    for pre in (0, 1, 0x5DC, 0xFFFFFFFF):
        yield spike(f"reset pre-set 148/14c {pre}", world(RESET, handler=HANDLER_C, st_148=pre, st_14c=pre))
        yield spike(f"reset pre-set 148 only {pre}", world(RESET, handler=HANDLER_A, st_148=pre))
        yield spike(f"reset pre-set 14c only {pre}", world(RESET, handler=HANDLER_B, st_14c=pre))

    # State 0x3ea: owner decides whether the sound is asked for; animation lookup found or not.
    for owner in (0, 1, 0x7FFFFFFF, 0xFFFFFFFE, 0xFFFFFFFF):
        for anims in ("none", "found"):
            for sound in ("none", "missing", "found"):
                yield spike(f"up owner={owner:#x} {anims} sound={sound}",
                            world(UP, owner=owner, anims=anims, sound=sound, name_id=0x4C))
    # State 0x3ec: flags bit, backward anim, down sound, then state 0x3eb.
    for owner in (0, 0xFFFFFFFF, 12):
        for anims in ("none", "found"):
            for sound in ("none", "found"):
                for flags in (0, 0x80, 0xFFFFFFFF, 0x1234567F):
                    yield spike(f"down owner={owner:#x} {anims} sound={sound} flags={flags:#x}",
                                world(DOWN, owner=owner, anims=anims, sound=sound, flags=flags))

    # With the sound switch on, the sound call is visible: owner (+0x38) gates it, the id (+0x4c) is passed on.
    # Neighbouring words (+0x3c, +0x50) hold different values so a wrong offset shows.
    for state in (UP, DOWN):
        for owner in (0, 0xFFFFFFFF, 12):
            for near in (0, 0xFFFFFFFF, 0x3C3C3C3C):
                for name_id, player in ((0x4C4C, sound_player(7, -12)), (0x77, sound_player(-30, 20))):
                    yield spike(f"sound on {state:#x} owner={owner:#x} near={near:#x} id={name_id:#x}",
                                world(state, owner=owner, name_id=name_id, anims="found", sound="found", sound_on=1,
                                      player=player,
                                      extra={0x3C: near, 0x50: near ^ 0x5A5A5A5A}))
    for state in (UP, DOWN):
        yield spike(f"sound on {state:#x} missing", world(state, anims="found", sound="missing", sound_on=1))

    # States 0x3eb and 0x3ed: the animation player decides; 0x19c (sub+0x14) must be 0 and 0x1a4 non-zero.
    for state in (WAIT_DOWN, WAIT_UP):
        for sub14 in (0, 1, 5):
            for sub1c in (0, 1, 0x99):
                for sub8 in (0, 0x808):
                    if sub8 and not sub14:
                        continue
                    for anims in ("none", "found"):
                        yield spike(f"wait {state:#x} +8={sub8} +14={sub14} +1c={sub1c} {anims}",
                                    world(state, sub=(sub8, sub14, 0, sub1c, 3), anims=anims,
                                          flags=0xA5A5A5A5 if state == WAIT_UP else 0x0F0F0F0F))
        for clock in (0, 1, 3):
            for sub18 in (0, 1):
                for sub14 in (1, 2, 4, 9):
                    yield spike(f"wait {state:#x} advance clock={clock} +18={sub18} +14={sub14}",
                                world(state, sub=(0x808, sub14, sub18, 0x99, 3), clock=clock, anims="found"))
    for flags in (0, 0x80, 0xFFFFFFFF, 0x7F, 0xFFFFFF7F, 0x1234):
        yield spike(f"wait up clears bit 7 flags={flags:#x}",
                    world(WAIT_UP, flags=flags, sub=(0, 0, 0, 5, 1), anims="found"))

    # States 0x3ee and 0x3ef: the phase check against the time.
    for state in (SETTLE, SETTLE_B):
        for step in (3, 10, 16):
            for allowed in (0, 4, 5, 6, 9, 0xFFFFFFF0, 0xFFFFFFFB):
                for timer in (100, 103, 104, 105, 109, 110, 99, 50, 0, 0xFFFFFFFF):
                    yield spike(f"settle {state:#x} step={step} allowed={allowed:#x} timer={timer}",
                                world(state, st_4c=step, st_148=allowed, timer=timer))
    for state in (SETTLE, SETTLE_B):
        for _ in range(25):
            yield spike(f"settle {state:#x} random",
                        world(state, st_4c=random_source.randrange(1, 40), st_bc=random_source.getrandbits(32),
                              st_148=random_source.choice([random_source.randrange(0, 40),
                                                           random_source.getrandbits(32)]),
                              timer=random_source.getrandbits(32 if random_source.random() < 0.3 else 8)))

    # Random whole-object runs over every state.
    for _ in range(80):
        state = random_source.choice(STATES + (random_source.getrandbits(32),))
        rect = None
        if random_source.random() < 0.6:
            rect = tuple(random_source.getrandbits(32) for _ in range(4))
        sub8 = random_source.choice([0, 0x808])
        # With +8 set and +0x1c zero the animation advance reads the current frame at +0xc, which is null here
        # unless it returns early, so a zero +0x1c is only drawn together with a zero +8.
        sub1c = random_source.getrandbits(8) | 1 if sub8 else random_source.choice([0, random_source.getrandbits(8)])
        yield spike(
            f"random state {state:#x}",
            world(state, handler=random_source.choice([0x400000, HANDLER_A, HANDLER_B, HANDLER_C]),
                  flags=random_source.getrandbits(32), owner=random_source.choice([0, 0xFFFFFFFF, 5]),
                  name_id=random_source.getrandbits(16), d64=random_source.choice([0, random_source.getrandbits(16)]),
                  d104=random_source.choice([0, random_source.getrandbits(8)]), rect=rect,
                  sub=(sub8, random_source.randrange(0, 6), random_source.randrange(0, 2), sub1c, 3),
                  clock=random_source.randrange(0, 3), timer=random_source.getrandbits(8),
                  st_4c=random_source.randrange(1, 30), st_bc=random_source.randrange(0, 200),
                  st_148=random_source.randrange(0, 30), anims=random_source.choice(["none", "found"]),
                  sound=random_source.choice(["none", "missing", "found"])))
