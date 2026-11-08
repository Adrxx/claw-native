"""Cases for saw_blade: SawBlade object logic.

The original at 0x462040 is a state machine. State 0 initialises the object, 0x3ea, 0x3ec, 0x3ed
start animations or sounds, 0x3eb, 0x3ee and 0x3ef wait for a condition. Its callees run as
original code on both sides, so each case builds the small object graph those callees read:
the animation timer at object+0x188, two string-keyed hash maps reached through object+0xc, and
the state record at object+0x6c.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

LOGIC = 0x462040
TIME_GLOBAL = 0x5430C4        # DAT_005430c4: frame time passed to the animation update
SOUND_ENABLED_GLOBAL = 0x532C0C
PHASE_GLOBAL = 0x537210       # DAT_00537210: value passed to the wait test
HANDLERS = (0x4622F0, 0x462310, 0x462330)
NAME_UP = 0x529610            # "LEVEL_SAWBLADE_UP"
NAME_DOWN = 0x5295FC          # "LEVEL_SAWBLADE_DOWN"
NAME_SPIN = 0x5295D4          # "LEVEL_SAWBLADE_SPIN"
SOUND_UP = 0x529624           # "LEVEL_SAWBLADEUP"
SOUND_DOWN = 0x5295E8         # "LEVEL_SAWBLADEDOWN"

S_INIT, S_UPSTART, S_WAITDOWN, S_DOWNSTART, S_WAITUP, S_SPIN, S_WAITPHASE = 0, 0x3EA, 0x3EB, 0x3EC, 0x3ED, 0x3EE, 0x3EF


def word(value):
    return value & 0xFFFFFFFF


def hash_name(text):
    h = 0
    for ch in text:
        c = ch if ch < 128 else ch - 256
        h = word(h * 33 + c)
    return h


def build_map(env, holder, keys, count, chain_decoy=False):
    """Fill the hash map embedded at holder+0x10 (buckets at +0x14, bucket count at +0x18).

    keys is a list of (name_address_in_original, value). Each gets a node: next, ?, key pointer, value.
    """
    buckets = env.object(4 * count, "buckets", fill=0)
    env.put(holder + 0x14, buckets)
    env.put(holder + 0x18, count)
    for address, value in keys:
        text = env.cstr(address)
        raw = text if isinstance(text, bytes) else text.encode("latin-1")
        index = hash_name(raw) % count
        key = env.object(len(raw) + 1, "key", data=raw + b"\0")
        head = env.get(buckets + 4 * index)
        node = env.object(0x10, "node", words=[head, 0x5151, key, value])
        env.put(buckets + 4 * index, node)
        if chain_decoy:
            other = env.object(8, "decoy-key", data=b"DECOY\0\0\0")
            decoy = env.object(0x10, "decoy", words=[env.get(buckets + 4 * index), 0x6262, other, 0xDEAD])
            env.put(buckets + 4 * index, decoy)


def animation_clip(env, frame_word):
    """A clip as 4c8220 reads it: +0x10 frame count, +0xc frame array, frame word at frame+0x1c."""
    frame = env.object(0x40, "frame", fill=0)
    env.put(frame + 0x1C, frame_word)
    frames = env.object(8, "frames", words=[frame, 0])
    clip = env.object(0x40, "clip", fill=0)
    env.put(clip + 0x0C, frames)
    env.put(clip + 0x10, 1)
    return clip


PAN_SCALE_GLOBAL = 0x532C10   # DAT_00532c10: 100 keeps the volume path off the x87 conversion


def sound_object(env, pitch=22050, centre=0x40, spread=48):
    """The sound found in the sound table, as the player at 0x4c88e0 and 0x4b45f0 read it.

    +0xc: listener (+0x24 -> bank, bank+0x5c -> device, device+0x84 = centre; +4 -> a -> b, b+0x10 = spread),
    +0x10: voice pool whose list at +0x30 holds one voice.
    """
    listener = env.object(0x40, "listener", fill=0)
    bank = env.object(0x80, "bank", fill=0)
    device = env.object(0x90, "device", fill=0)
    env.put(device + 0x84, centre)
    env.put(bank + 0x5C, device)
    env.put(listener + 0x24, bank)
    ext_a = env.object(0x20, "ext-a", fill=0)
    ext_b = env.object(0x20, "ext-b", fill=0)
    env.put(ext_b + 0x10, spread)
    env.put(ext_a + 0x10, ext_b)
    env.put(listener + 0x04, ext_a)
    root = env.object(0x100, "pool-root", fill=0)
    env.put(root + 0x78, 1)
    pool = env.object(0x40, "voice-pool", fill=0)
    env.put(pool + 0x10, root)
    env.put(pool + 0x18, 0x1111)
    env.put(pool + 0x1C, 0x2222)
    env.put(pool + 0x20, 0x3333)
    # The voice is disabled (+0x78 of its own root is 0), so every voice method returns at once and no method
    # table is reached: the only trace of the request is that the voice moves to the end of the pool's list.
    dead_root = env.object(0x100, "dead-root", fill=0)
    voice = env.object(0x40, "voice", fill=0)
    env.put(voice + 0x10, dead_root)
    env.put(voice + 0x18, pitch)
    env.put(voice + 0x30, 1)
    env.put(voice + 0x0C, env.object(0x20, "voice-com", fill=0))
    env.put(pool + 0x30, voice + 4)
    sound = env.object(0x20, "sound", fill=0)
    env.put(sound + 0x0C, listener)
    env.put(sound + 0x10, pool)
    return sound


def blade(state, rect=None, flags=0x1234, timeout=None, aux=None, handler=0x401000, id38=5,
          timer=None, check=None, init_fields=None, sink="null", clips="none", chain=False,
          time=777, phase=0, count=7, seeded=0x5A5A, sound_on=0, loud=False, name4c=0x4C4C):
    """setup() for one blade in the given state.

    timer: dict with alive, a14, a18, a1c, a20, a24 for the animation timer at +0x188.
    check: None, or (phase, base, modulus, limit) for the wait test.
    sink: "null" (sound table missing), "busy", "miss", "hit".
    clips: "none" (map missing), "miss", "hit".
    """
    timer = timer or {}

    def setup(env):
        obj = env.object(0x1C0, "blade", fill=0)
        record = env.object(0x1E0, "state-record", fill=0)
        owner = env.object(0x40, "owner", fill=0)
        sound = env.object(0x60, "sound-table", fill=0)
        holder = env.object(0x60, "clip-table", fill=0)
        env.put(obj + 0x08, flags)
        env.put(obj + 0x0C, owner)
        env.put(owner + 0x28, sound)
        env.put(owner + 0x2C, holder)
        env.put(obj + 0x38, id38)
        env.put(obj + 0x4C, name4c)
        env.put(obj + 0x6C, record)
        env.put(record + 0x1C, state)
        env.put(record + 0x10, handler)
        env.put(record + 0xBC, 0x77)
        env.put(record + 0x4C, 0x1357)
        env.put(record + 0x148, 0x246)
        env.put(record + 0x14C, 0x468)
        if timeout is not None:
            env.put(obj + 0x64, timeout)
        if aux is not None:
            env.put(obj + 0x104, aux)
        env.put(obj + 0x138, 0x1111, 0x2222)
        env.put(obj + 0x140, 0x3333, 0x4444)
        env.put(obj + 0xD0, 0x99)
        if init_fields:
            for offset, value in init_fields.items():
                env.put(record + offset if offset < 0x1000 else obj + offset - 0x1000, value)
        rect_obj = None
        if rect is not None:
            rect_obj = env.object(0x30, "rect", fill=0)
            env.put(rect_obj + 0x18, *rect)
            env.put(obj + 0x174, rect_obj)
        t = 0x188
        env.put(obj + t + 0x08, 1 if timer.get("alive") else 0)
        env.put(obj + t + 0x14, timer.get("a14", 0))
        env.put(obj + t + 0x18, timer.get("a18", 0))
        env.put(obj + t + 0x1C, timer.get("a1c", 0))
        env.put(obj + t + 0x20, timer.get("a20", 0x2020))
        env.put(obj + t + 0x24, timer.get("a24", 0x2424))
        if check is not None:
            phase_value, base, modulus, limit = check
            env.put(record + 0xBC, base)
            env.put(record + 0x4C, modulus)
            env.put(record + 0x148, limit)
            env.put(PHASE_GLOBAL, phase_value)
        else:
            env.put(PHASE_GLOBAL, phase)
            env.put(record + 0x4C, 0x40)
        env.put(TIME_GLOBAL, time)
        env.put(SOUND_ENABLED_GLOBAL, sound_on)  # 0: the sound player at 0x4c88e0 returns at once
        if sink != "null":
            host = env.object(0x40, "sound-host", fill=0)
            env.put(sound + 0x0C, host)
            if sink == "busy":
                env.put(sound + 0x30, 1)
            inner = env.object(0x80, "sound-bank", fill=0)
            env.put(host + 0x24, inner)
            env.put(inner + 0x5C, env.object(0x20, "sound-device", fill=0))
            if loud:
                env.put(PAN_SCALE_GLOBAL, 100)
                value_up = sound_object(env)
                value_down = sound_object(env, pitch=44100)
            else:
                value_up, value_down = 0x1000001, 0x1000002
            keys = [] if sink == "miss" else [(SOUND_UP, value_up), (SOUND_DOWN, value_down)]
            build_map(env, sound, keys, count, chain_decoy=chain)
        else:
            env.put(sound + 0x0C, env.object(0x40, "sound-host", fill=0))
            env.put(sound + 0x18, count)
        if clips == "none":
            env.put(holder + 0x18, count)
        else:
            keys = []
            if clips == "hit":
                keys = [(NAME_UP, animation_clip(env, 0x7001)), (NAME_DOWN, animation_clip(env, 0x7002)),
                        (NAME_SPIN, animation_clip(env, 0x7003))]
            build_map(env, holder, keys, count, chain_decoy=chain)
        return {"obj": obj, "record": record, "rect": rect_obj}
    return setup


def run(label, setup):
    return Case(label, LOGIC, setup, arguments=(lambda t: t["obj"],))


def timers(r):
    """Animation timer variants that the update at 0x4c82a0 handles without deep lookups."""
    return [
        {"alive": False, "a14": 0, "a1c": 0},
        {"alive": False, "a14": 3, "a1c": 9},
        {"alive": True, "a14": 0, "a1c": 5},
        {"alive": True, "a14": 0, "a1c": 1, "a20": 0x31, "a24": 0x32},
        {"alive": True, "a14": 1, "a18": 0, "a1c": 7},
        {"alive": True, "a14": 6, "a18": 0, "a1c": 7},
        {"alive": True, "a14": 6, "a18": 1, "a1c": 7, "a20": 0x999},
        {"alive": True, "a14": 900, "a18": 1, "a1c": 7},
        {"alive": True, "a14": 777, "a18": 1, "a1c": 7},
        {"alive": True, "a14": 778, "a18": 1, "a1c": 8},
        {"alive": True, "a14": 2, "a18": 4, "a1c": 3},
        {"alive": True, "a14": r.randrange(1, 2000), "a18": r.randrange(0, 2), "a1c": r.randrange(1, 99),
         "a20": r.getrandbits(32), "a24": r.getrandbits(32)},
    ]


def cases(random_source):
    r = random_source
    # State 0: the initialisation, with and without a bounds object and with every default.
    for rect in (None, (3, 5, 100, 200), (0, 0, 1, 1), (-4, -9, 50, 60), (0x7FFFFFF0, 12, 9, 0x10)):
        yield run(f"init rect {rect}", blade(S_INIT, rect=rect))
    for handler in HANDLERS + (0x401000, 0):
        for timeout in (None, 0, 55):
            for aux in (None, 0, 33):
                for flags in (0, 0x80, 0x20000, 0xFFFFFFFF):
                    yield run(f"init handler {handler:#x} timeout {timeout} aux {aux} flags {flags:#x}",
                              blade(S_INIT, rect=(7, 11, 90, 120), handler=handler, timeout=timeout, aux=aux, flags=flags))
    for field14c in (0, 9):
        for field148 in (0, 4):
            yield run(f"init timing {field148},{field14c}",
                      blade(S_INIT, init_fields={0x148: field148, 0x14C: field14c}))
    yield run("init keeps preset extents without bounds", blade(S_INIT, init_fields={0x1138: 0xFFFFFFF0, 0x113C: 7, 0x1140: 0x7FFFFFFF, 0x1144: 1}))

    # States 0x3ea and 0x3ec: start a clip and a sound.
    for state in (S_UPSTART, S_DOWNSTART):
        for id38 in (-1, 0, 5):
            for sink in ("null", "busy", "miss", "hit"):
                for clips in ("none", "miss", "hit"):
                    for flags in (0x1234, 0x80, 0):
                        yield run(f"state {state:#x} id38 {id38} sink {sink} clips {clips} flags {flags:#x}",
                                  blade(state, id38=id38, sink=sink, clips=clips, flags=flags))
        for count in (1, 2, 13):
            yield run(f"state {state:#x} chained hash count {count}",
                      blade(state, sink="hit", clips="hit", chain=True, count=count))

    # Sound player enabled and a real sound found: the voice methods are called, so whether the sound
    # is requested, and with which name and position, is observable.
    for state in (S_UPSTART, S_DOWNSTART):
        for id38 in (-1, 0, 5, 0x7FFFFFFF):
            for sink in ("busy", "miss", "hit"):
                for name4c in (0x40, 0x41, 0x3A, 0x4C4C, 0x30, 0):
                    yield run(f"loud state {state:#x} id38 {id38} sink {sink} pos {name4c:#x}",
                              blade(state, id38=id38, sink=sink, clips="hit", sound_on=1, loud=True, name4c=name4c))
        for chain in (False, True):
            yield run(f"loud state {state:#x} chain {chain}",
                      blade(state, sink="hit", clips="hit", chain=chain, sound_on=1, loud=True, count=3, name4c=0x47))
        for flags in (0, 0x80, 0xFFFFFF7F):
            yield run(f"loud state {state:#x} flags {flags:#x}",
                      blade(state, sink="hit", clips="hit", flags=flags, sound_on=1, loud=True, name4c=0x44))

    # States that wait on the animation timer.
    for state in (S_WAITDOWN, S_WAITUP):
        for index, timer in enumerate(timers(r)):
            for time in (0, 5, 777):
                for flags in (0x1234, 0x81):
                    yield run(f"state {state:#x} timer {index} time {time} flags {flags:#x}",
                              blade(state, timer=timer, time=time, flags=flags, clips="hit" if index % 2 else "none"))
        for clips in ("none", "miss", "hit"):
            yield run(f"state {state:#x} done clips {clips}", blade(state, timer={"alive": True, "a14": 0, "a1c": 4}, clips=clips))
    for flags in (0, 0x80, 0xFFFFFF80, 0x12345680):
        yield run(f"spin start clears bit 7 of {flags:#x}", blade(S_WAITUP, timer={"alive": True, "a14": 0, "a1c": 4}, flags=flags, clips="hit"))

    # States that wait on the phase test: remainder <= limit, signed.
    for state in (S_SPIN, S_WAITPHASE):
        for timer in ({"alive": False}, {"alive": True, "a14": 0, "a1c": 3}, {"alive": True, "a14": 4, "a18": 0, "a1c": 3}):
            for check in ((110, 10, 100, 0), (110, 10, 100, -1), (115, 10, 100, 5), (115, 10, 100, 4),
                          (3, 10, 100, 0), (3, 10, 100, 0x7FFFFFFF), (0x80000005, 7, 0x99, 0x20),
                          (10, 10, 1, 0), (500, 0, 7, 3), (4, 0, 9, 4)):
                yield run(f"state {state:#x} timer {timer.get('a14')} check {check}", blade(state, timer=timer, check=check, clips="hit"))
    for _ in range(30):
        modulus = r.randrange(1, 400)
        base = r.getrandbits(16)
        phase = word(base + r.randrange(0, 5000))
        limit = r.choice((r.randrange(0, modulus + 3), -r.randrange(1, 5), r.randrange(0, modulus)))
        state = r.choice((S_SPIN, S_WAITPHASE))
        yield run(f"random phase {state:#x} {phase}", blade(state, check=(phase, base, modulus, word(limit)),
                                                          flags=r.getrandbits(32), time=r.getrandbits(16),
                                                          timer=r.choice(timers(r))))

    # States nobody handles leave the object alone.
    for state in (1, 0x3E8, 0x3E9, 0x3F0, 0x3F1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFC15 + 1):
        for timer in ({"alive": True, "a14": 0, "a1c": 3}, {"alive": False}):
            yield run(f"unhandled state {state:#x}", blade(state, timer=timer, check=(1, 0, 3, 3), rect=(2, 3, 4, 5)))

    # Random whole objects.
    for _ in range(80):
        state = r.choice((S_INIT, S_UPSTART, S_WAITDOWN, S_DOWNSTART, S_WAITUP, S_SPIN, S_WAITPHASE, r.getrandbits(32)))
        modulus = r.randrange(1, 300)
        base = r.getrandbits(12)
        yield run(f"random state {state:#x}", blade(
            state,
            rect=r.choice((None, (r.randrange(1, 500), r.randrange(1, 500), r.randrange(1, 500), r.randrange(1, 500)))),
            flags=r.getrandbits(32), timeout=r.choice((None, r.randrange(1, 9999))),
            aux=r.choice((None, r.randrange(1, 99))), handler=r.choice(HANDLERS + (0x401000,)),
            id38=r.choice((-1, r.randrange(0, 99))), timer=r.choice(timers(r)),
            check=(word(base + r.randrange(0, 600)), base, modulus, r.randrange(0, modulus + 2)),
            sink=r.choice(("null", "busy", "miss", "hit")), clips=r.choice(("none", "miss", "hit")),
            chain=r.random() < 0.3, time=r.getrandbits(16), count=r.randrange(1, 20)))
