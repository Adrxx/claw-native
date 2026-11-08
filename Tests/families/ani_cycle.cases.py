"""Cases for ani_cycle: AniCycle object logic (also AniCycleNormal)."""
from clawparity.cases import Case

LOGIC = 0x4918B0
NAME = 0x5240D8          # "GAME_CYCLE100"
TICK_STEP = 0x5430C4     # global animation step passed to the player tick
KEY = b"GAME_CYCLE100\0"


def hash_name(key):
    value = 0
    for byte in key.rstrip(b"\0"):
        signed = byte - 256 if byte >= 128 else byte
        value = (value * 0x21 + signed) & 0xFFFFFFFF
    return value


def build(env, rnd, state, flags=None, player_animation=None, player_fields=None, table=None, extra=None):
    """Build the object, its state record and its animation table. Returns the tokens."""
    obj = env.object(0x1C0, "ani-cycle", words=[rnd.getrandbits(32) | 0x01010101 for _ in range(0x70)])
    record = env.object(0x40, "state-record", words=[rnd.getrandbits(32) | 1 for _ in range(16)])
    env.put(record + 0x1C, state)
    env.put(obj + 0x6C, record)
    flag_value = rnd.getrandbits(32) & ~1 if flags is None else flags
    env.put(obj + 0x08, flag_value)
    env.put(obj + 0x190, 0 if player_animation is None else player_animation)
    tokens = {"obj": obj, "record": record, "flags": flag_value}
    if table is not None:
        tokens.update(table(env, obj, rnd))
    if player_fields:
        for offset, value in player_fields.items():
            env.put(obj + 0x188 + offset, value)
    if extra:
        extra(env, tokens)
    return tokens


def lookup_table(buckets=7, present=True, decoys=0, frames=2, null_buckets=False, frame_value=0x1234, step=3):
    """The animation hash table reachable from obj+0x0c -> +0x2c -> +0x10."""
    def make(env, obj, rnd):
        host = env.object(0x40, "animation-host", words=[rnd.getrandbits(32) | 1 for _ in range(16)])
        index = env.object(0x40, "animation-index", words=[rnd.getrandbits(32) | 1 for _ in range(16)])
        env.put(obj + 0x0C, host)
        env.put(host + 0x2C, index)
        env.put(index + 0x10 + 8, buckets)
        env.put(TICK_STEP, step)
        if null_buckets:
            env.put(index + 0x10 + 4, 0)
            return {"index": index}
        slots = env.object(buckets * 4, "buckets", fill=0)
        env.put(index + 0x10 + 4, slots)
        slot = hash_name(KEY) % buckets
        key = env.object(16, "key", data=KEY)
        frame_list = []
        for number in range(frames):
            frame = env.object(0x40, "frame", words=[rnd.getrandbits(32) | 1 for _ in range(16)])
            env.put(frame + 0x1C, frame_value + number)
            frame_list.append(frame)
        array = env.object(4 * max(frames, 1), "frames", words=frame_list or [0])
        animation = env.object(0x40, "animation", words=[rnd.getrandbits(32) | 1 for _ in range(16)])
        env.put(animation + 0x0C, array)
        env.put(animation + 0x10, frames)
        head = 0
        if present:
            head = env.object(0x10, "node", words=[0, 0, key, animation])
        # decoys: other keys chained in the same bucket, in front of (or instead of) the real one
        for number in range(decoys):
            other = env.object(16, "other-key", data=(b"OTHER_%d\0" % number))
            head = env.object(0x10, "decoy", words=[head, 0, other, rnd.getrandbits(32) | 1])
        env.put(slots + 4 * slot, head)
        return {"index": index, "animation": animation, "frames": frame_list}
    return make


def player_tick_setup(counter, running, frame_fields=None, scale=0x3F800000, mode=0, extra_player=None):
    """A player whose animation is already attached, so the state-5 tick runs the original code."""
    def make(env, obj, rnd):
        animation = env.object(0x40, "animation", words=[rnd.getrandbits(32) | 1 for _ in range(16)])
        owner = env.object(0x180, "owner", words=[rnd.getrandbits(32) | 1 for _ in range(0x60)])
        frame = env.object(0x40, "frame", words=[0] * 16)
        for offset, value in (frame_fields or {0x0C: 9, 0x18: 11}).items():
            env.put(frame + offset, value)
        env.put(animation + 0x08, 0)
        fields = {0x04: owner, 0x08: animation, 0x0C: frame, 0x10: 2, 0x14: counter, 0x18: running,
                  0x1C: mode, 0x20: 0x55, 0x24: 0x66, 0x28: scale}
        for offset, value in fields.items():
            env.put(obj + 0x188 + offset, value)
        for offset, value in (extra_player or {}).items():
            env.put(obj + 0x188 + offset, value)
        return {"animation": animation, "owner": owner, "frame": frame}
    return make


def case(label, setup):
    return Case(label, LOGIC, setup, arguments=(lambda tokens: tokens["obj"],))


def cases(random_source):
    rnd = random_source

    # State 0, no player yet: the original looks the cycle up and starts it.
    for buckets in (1, 2, 7, 13, 61):
        for decoys in (0, 1, 3):
            for frames in (1, 3):
                yield case(f"start: buckets {buckets} decoys {decoys} frames {frames}",
                           lambda env, b=buckets, d=decoys, f=frames: build(
                               env, rnd, 0, table=lookup_table(buckets=b, decoys=d, frames=f,
                                                               frame_value=rnd.getrandbits(16) + 1)))
    for _ in range(12):
        buckets = rnd.randrange(1, 90)
        yield case(f"start random buckets {buckets}",
                   lambda env, b=buckets: build(env, rnd, 0, flags=rnd.getrandbits(32),
                                                table=lookup_table(buckets=b, decoys=rnd.randrange(0, 4),
                                                                   frames=rnd.randrange(1, 5),
                                                                   frame_value=rnd.getrandbits(20) + 1)))
    yield case("start: flag already set", lambda env: build(env, rnd, 0, flags=0xFFFFFFFF, table=lookup_table()))
    yield case("start: only bit 0 set", lambda env: build(env, rnd, 0, flags=1, table=lookup_table()))
    yield case("start: lookup misses", lambda env: build(env, rnd, 0, table=lookup_table(present=False, decoys=2)))
    yield case("start: lookup misses, empty bucket",
               lambda env: build(env, rnd, 0, table=lookup_table(present=False)))
    yield case("start: bucket array missing", lambda env: build(env, rnd, 0, table=lookup_table(null_buckets=True)))

    # State 0 with a player already attached: no lookup, state still advances.
    for animation in (1, 0x7FFFFFFF, 0xFFFFFFFF, 0x12345678):
        yield case(f"start: player already attached {animation:#x}",
                   lambda env, a=animation: build(env, rnd, 0, player_animation=a))
    yield case("start: attached, flags set", lambda env: build(env, rnd, 0, flags=0x80000000, player_animation=5))

    # State 5: tick the player.
    yield case("tick: player empty returns early", lambda env: build(env, rnd, 5))
    yield case("tick: player empty keeps flags", lambda env: build(env, rnd, 5, flags=0xA5A5A5A4))
    for counter, running, step in ((7, 0, 3), (1, 0, 9), (7, 1, 3), (7, 1, 7), (7, 1, 100), (5, 1, 1), (2, 1, 1), (0xFFFFFFFF, 0, 1)):
        yield case(f"tick: counter {counter} running {running} step {step}",
                   lambda env, c=counter, r=running, s=step: build(
                       env, rnd, 5, player_animation=1,
                       table=lambda e, o, q: (e.put(TICK_STEP, s), player_tick_setup(c, r)(e, o, q))[1]))
    for step in (0, 1, 2, 5):
        yield case(f"tick: counter 0 step {step}",
                   lambda env, s=step: build(
                       env, rnd, 5, player_animation=1,
                       table=lambda e, o, q: (e.put(TICK_STEP, s), player_tick_setup(0, 1)(e, o, q))[1]))
    for mode in (1, 3, 0x7FFFFFFF):
        yield case(f"tick: player mode {mode} returns held value",
                   lambda env, m=mode: build(env, rnd, 5, player_animation=1,
                                             table=player_tick_setup(0, 1, mode=m)))
    yield case("tick: counter 0 full frame step",
               lambda env: build(env, rnd, 5, player_animation=1,
                                 table=player_tick_setup(0, 0, frame_fields={0x0C: 9, 0x18: 4, 0x04: 1, 0x2C: 0})))

    # Any other state does nothing.
    for state in (1, 2, 3, 4, 6, 7, 8, 0xFFFFFFFF, 0x80000000, 0x100, 0x1000000, 0x7FFFFFFF):
        yield case(f"other state {state:#x}", lambda env, s=state: build(env, rnd, s, player_animation=1))
    for _ in range(8):
        state = rnd.getrandbits(32)
        if state in (0, 5):
            state = 6
        yield case(f"random state {state:#x}",
                   lambda env, s=state: build(env, rnd, s, player_animation=rnd.getrandbits(32) | 1))

    # The state record is re-read from the object each call; two objects share nothing.
    yield case("state 5 and animation tick with large step",
               lambda env: build(env, rnd, 5, player_animation=1,
                                 table=lambda e, o, q: (e.put(TICK_STEP, 0xFFFFFFFF),
                                                        player_tick_setup(3, 1)(e, o, q))[1]))
