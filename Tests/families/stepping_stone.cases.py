"""Cases for stepping_stone: SteppingStone object logic (0x49e810, registered object-logic callback)."""
from clawparity.cases import Case
from clawparity.fixtures import returns

FUNC = 0x49E810
G_TABLE = 0x537960      # pointer to a record whose +0x88..+0x97 is copied into the object
G_TIME = 0x537210       # time given to the phase test 0x49e4b0
G_CLOCK = 0x5430C4      # clock given to the animation step 0x4c82a0
G_FLAG = 0x532C0C       # the animation-ease switch tested by 0x4c88e0
G_SCALE = 0x532C10      # 100 means no float rescale in 0x4c88e0
NAME_RISE = 0x52DD7C
NAME_SINK = 0x52DD8C
NAME_FORWARD = 0x52DD04
NAME_BACKWARD = 0x52DD14
ROUTINES = (0x49EAD0, 0x49EAF0, 0x49EB10)
STATES = (0x3EA, 0x3EB, 0x3EC, 0x3ED, 0x3EE, 0x3EF)
MASK = 0xFFFFFFFF


def hash_name(text):
    value = 0
    for byte in text:
        signed = byte - 256 if byte >= 128 else byte
        value = (value * 0x21 + signed) & MASK
    return value


def fill_random(env, address, size, rs):
    for offset in range(0, size, 4):
        env.put(address + offset, rs.randrange(1, 1 << 30))


def make_table(env, base, names, found, rs, maker=None):
    """A hash table embedded at base (+4 buckets, +8 count). Names in `found` are present, behind a decoy in the same bucket."""
    count = rs.choice((7, 11, 13, 31))
    buckets = env.object(count * 4, "buckets", fill=0)
    env.put(base + 4, buckets)
    env.put(base + 8, count)
    values = {}
    for name_address in names:
        if name_address not in found:
            continue
        text = env.cstr(name_address)
        if maker is not None:
            slot = hash_name(text if isinstance(text, bytes) else text.encode("latin-1")) % count
            sound = maker(env)
            decoy_name = env.object(8, "decoy-name", data=b"ZZ_DECOY\0")
            decoy = env.object(16, "decoy", words=[env.get(buckets + slot * 4), 0, decoy_name, rs.randrange(1, 1 << 20)])
            node = env.object(16, "node", words=[decoy, 0, name_address, sound])
            env.put(buckets + slot * 4, node)
            values[name_address] = sound
            continue
        slot = hash_name(text if isinstance(text, bytes) else text.encode("latin-1")) % count
        anim_frames = env.object(12, "frames", fill=0)
        frame = env.object(0x30, "frame", fill=0)
        env.put(frame + 0x1C, rs.randrange(1, 1 << 20))
        env.put(anim_frames, frame)
        anim = env.object(0x80, "anim", fill=0)
        env.put(anim + 0x0C, anim_frames)
        env.put(anim + 0x10, 1)
        decoy_name = env.object(8, "decoy-name", data=b"ZZ_DECOY\0")
        decoy = env.object(16, "decoy", words=[env.get(buckets + slot * 4), 0, decoy_name, rs.randrange(1, 1 << 20)])
        node = env.object(16, "node", words=[decoy, 0, name_address, anim])
        env.put(buckets + slot * 4, node)
        values[name_address] = anim
    return values


def make_sound(env, rs, o, obj):
    """A sound for 0x4c88e0. "poison": reaching 0x4c88e0 faults. "ok": the chain is valid and the voice is obj+0x180,
    so the voice's device word is obj+0x190, which 0x4c79e0 fills with the animation (the call order shows)."""
    s = env.object(0x40, "sound", fill=0)
    if o["sound_rich"] == "poison":
        return s
    b = env.object(0x20, "sound-b", fill=0)
    env.put(b + 0x10, o.get("val", 3000))
    a = env.object(0x20, "sound-a", fill=0)
    env.put(a + 0x10, b)
    z = env.object(0x90, "sound-z", fill=0)
    env.put(z + 0x84, o.get("ebx", 100) & MASK)
    y = env.object(0x80, "sound-y", fill=0)
    env.put(y + 0x5C, z)
    x = env.object(0x40, "sound-x", fill=0)
    env.put(x + 4, a)
    env.put(x + 0x24, y)
    env.put(s + 0x0C, x)
    env.put(s + 0x10, obj + 0x180)
    return s


def make_peer(env, rs, lo=None, hi=None):
    lo = rs.choice((-9, -4, -1, 0, 1, 3, 8)) if lo is None else lo
    hi = lo + rs.choice((0, 1, 2, 3, 6, 7)) if hi is None else hi
    peer = env.object(0x70, "peer", fill=0)
    fill_random(env, peer, 0x70, rs)
    array = env.object((hi - lo + 1) * 4, "peer-array")
    fill_random(env, array, (hi - lo + 1) * 4, rs)
    env.put(peer + 0x64, lo & MASK)
    env.put(peer + 0x68, hi & MASK)
    env.put(peer + 0x14, (array - lo * 4) & MASK)
    return peer, array, lo, hi


def build(state, rs, **o):
    """setup(): an object, its state record and every structure the original callees walk."""
    def setup(env):
        alias = o.get("alias")
        obj = env.object(0x300 if alias else 0x1C0, "stone", fill=0)
        fill_random(env, obj, 0x300 if alias else 0x1C0, rs)
        if alias:
            rec = obj + alias  # the state record overlaps the object, so statement order shows in memory
        else:
            rec = env.object(0xC8, "state", fill=0)
            fill_random(env, rec, 0xC8, rs)
        owner = env.object(0x40, "owner", fill=0)
        fill_random(env, owner, 0x40, rs)
        service = env.object(0x40, "service", fill=0)
        fill_random(env, service, 0x40, rs)
        sprites = env.object(0x40, "sprites", fill=0)
        fill_random(env, sprites, 0x40, rs)
        svc_b = env.object(0x40, "service-b", fill=0)
        svc_c = env.object(0x80, "service-c", fill=0)
        table = env.object(0xA0, "record", fill=0)
        fill_random(env, table, 0xA0, rs)
        env.put(obj + 0x6C, rec)
        env.put(obj + 0x0C, owner)
        env.put(owner + 0x28, service)
        env.put(owner + 0x2C, sprites)
        env.put(service + 0x0C, svc_b)
        env.put(svc_b + 0x24, svc_c if o.get("service_live", False) else 0)
        env.put(svc_c + 0x5C, rs.randrange(1, 1 << 20))
        env.put(service + 0x30, 0)
        env.put(obj + 0x38, o.get("f38", rs.choice((MASK, 0, 5, rs.randrange(1, 1 << 30)))))
        env.put(rec + 0x1C, state)
        entry_value = o["entry"] if o.get("entry") else rs.randrange(1, 1 << 30)
        env.put(rec + 0x10, entry_value)
        env.put(rec + 0x64, rs.randrange(0, 4000))
        env.put(rec + 0x4C, o.get("period", rs.randrange(1, 4000)))
        env.put(rec + 0xBC, o.get("origin", rs.randrange(0, 4000)))
        env.put(obj + 0x08, o.get("flags", rs.randrange(0, 1 << 30)))
        env.put(obj + 0x64, o.get("p64", rs.randrange(1, 4000)))
        env.put(obj + 0x148, o.get("f148", rs.randrange(0, 3000)))
        env.put(obj + 0x14C, o.get("f14c", rs.randrange(0, 3000)))
        env.put(G_TABLE, table)
        env.put(G_TIME, o.get("time", rs.randrange(0, 1 << 16)))
        env.put(G_CLOCK, o.get("clock", rs.randrange(1, 100)))
        env.put(G_FLAG, 0)
        peer = array = 0
        lo = hi = 0
        if o.get("link", True):
            peer, array, lo, hi = make_peer(env, rs)
            env.put(obj + 0x170, peer)
            if "at16c" in o:
                env.put(obj + 0x16C, o["at16c"](lo, hi))
        else:
            env.put(obj + 0x170, 0)
        # animation player embedded at +0x188: +8 animation, +0x14 counter, +0x18 mode, +0x1c done
        env.put(obj + 0x190, o.get("a190", 0))
        env.put(obj + 0x19C, o.get("a19c", rs.randrange(0, 5)))
        env.put(obj + 0x1A0, o.get("a1a0", 0))
        env.put(obj + 0x1A4, o.get("a1a4", rs.randrange(0, 3)))
        # name tables used by 0x4c79e0 (sprites+0x10) and 0x4ca610 (service+0x10)
        names = (NAME_FORWARD, NAME_BACKWARD)
        make_table(env, sprites + 0x10, names, o.get("anim_found", ()), rs)
        rich = o.get("sound_rich", False)
        make_table(env, service + 0x10, (NAME_RISE, NAME_SINK), o.get("sound_found", ()), rs,
                   maker=(lambda env: make_sound(env, rs, o, obj)) if rich else None)
        if rich:
            env.put(G_FLAG, 1)
            env.put(G_SCALE, 100)
            env.put(obj + 0x4C, (o.get("ebx", 100) + o.get("delta", 0)) & MASK)
            if o.get("voice_ready", False):
                env.put(obj + 0x190, env.object(0x80, "voice-device", fill=0))
        if o.get("equal", False):
            env.put(obj + 0x16C, env.get(rec + 0x64))
        if alias:
            env.put(rec + 0x1C, state)
            if state == 0:
                env.put(rec + 0x10, entry_value)
        return {"obj": obj, "rec": rec, "peer": peer}
    return setup


def one(label, setup, **kw):
    return Case(label, FUNC, setup, arguments=(lambda t: t["obj"],), **kw)


def cases(random_source):
    rs = random_source
    both = (NAME_FORWARD, NAME_BACKWARD)
    # state 0: initialisation, every branch of the routine test and the 0x20000 branch
    for link in (True, False):
        for entry in (None,) + ROUTINES:
            for p64 in (0, 1, rs.randrange(2, 4000)):
                for flags in (0, 1, rs.randrange(0, 1 << 30)):
                    yield one(f"init link={link} entry={entry} p64={p64} flags={flags:#x}",
                              build(0, rs, link=link, entry=entry, p64=p64, flags=flags,
                                    f148=rs.choice((0, 7)), f14c=rs.choice((0, 9))))
    for _ in range(8):
        yield one("init random", build(0, rs, entry=rs.choice(ROUTINES + (None,)), p64=rs.choice((0, 3))))
    # state 0x3ea: sink
    for f38 in (MASK, 0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE):
        for live in (False, True):
            for found in ((), (NAME_SINK,)):
                yield one(f"sink f38={f38:#x} live={live} found={bool(found)}",
                          build(0x3EA, rs, f38=f38, service_live=live, sound_found=found))
    # state 0x3ec: rise
    for f38 in (MASK, 3):
        for found in ((), (NAME_FORWARD,), both):
            for live in (False, True):
                for sound in ((), (NAME_RISE,)):
                    yield one(f"rise f38={f38:#x} anim={len(found)} live={live} sound={bool(sound)}",
                              build(0x3EC, rs, f38=f38, anim_found=found, service_live=live, sound_found=sound))
    # the sound path of 0x4c88e0 is only visible through a fault: a poisoned sound faults when the +0x38 gate wrongly opens
    for state, name in ((0x3EA, NAME_SINK), (0x3EC, NAME_RISE)):
        for _ in range(4):
            yield one(f"poisoned sound {state:#x} gate closed",
                      build(state, rs, f38=MASK, service_live=True, sound_found=(name,), sound_rich="poison",
                            anim_found=rs.choice(((), both)), delta=rs.randrange(-900, 900)))
    # a working sound: the sink needs a voice device; in the rise the animation start must come first
    for f38 in (0, 7, 0x7FFFFFFF, MASK, rs.randrange(1, 1 << 30)):
        for _ in range(3):
            yield one(f"working sound 0x3ea f38={f38:#x}",
                      build(0x3EA, rs, f38=f38, service_live=True, sound_found=(NAME_SINK,), sound_rich="ok",
                            voice_ready=True, val=rs.choice((3, 30, 3000, rs.randrange(3, 9000))),
                            ebx=rs.choice((0, 100, rs.randrange(0, 5000), 0xFFFFFF00)),
                            delta=rs.randrange(-1200, 1200)))
            yield one(f"working sound 0x3ec f38={f38:#x}",
                      build(0x3EC, rs, f38=f38, service_live=True, sound_found=(NAME_RISE,), sound_rich="ok",
                            anim_found=both, val=rs.choice((3, 30, 3000, rs.randrange(3, 9000))),
                            ebx=rs.choice((0, 100, rs.randrange(0, 5000), 0xFFFFFF00)),
                            delta=rs.randrange(-1200, 1200)))
    # the state record laid over the object: the order of the entry-routine call against its neighbours shows in memory
    for alias in (0x8C, 0x90, 0x12C, 0x130):
        for entry in ROUTINES + (None,):
            for f148, f14c in ((0, 0), (0, 9), (7, 0), (7, 9)):
                yield one(f"overlaid init alias={alias:#x} entry={entry} f148={f148} f14c={f14c}",
                          build(0, rs, alias=alias, entry=entry, f148=f148, f14c=f14c, p64=rs.choice((0, 5))))
    # the animation start against the state change: the state field overlaps the animation player's +0x20
    for state in (0x3EB, 0x3EC, 0x3ED):
        for _ in range(4):
            yield one(f"overlaid animation start {state:#x}",
                      build(state, rs, alias=0x18C, anim_found=both, a190=0, a19c=0, a1a4=rs.randrange(1, 9),
                            a1a0=rs.randrange(0, 3), f38=MASK))
    # states 0x3eb and 0x3ed: tick the animation, compare position, watch for the end
    for state in (0x3EB, 0x3ED):
        for equal in (False, True):
            for a190 in (0, 0x1234):
                for a19c in (0, 1, 2, 5):
                    for a1a4 in (0, 1, 9):
                        if a190 and a19c == 0 and a1a4 == 0:
                            continue  # would walk the whole animation table; out of reach without more structure
                        for a1a0 in (0, 1):
                            if a190 and a1a0 and not a1a4:
                                continue  # counter expiry without the end flag would walk the animation table
                            for found in ((), both):
                                if rs.randrange(3):
                                    continue
                                yield one(f"{state:#x} equal={equal} a190={a190:#x} a19c={a19c} a1a4={a1a4} a1a0={a1a0}",
                                          build(state, rs, equal=equal, a190=a190, a19c=a19c, a1a4=a1a4, a1a0=a1a0,
                                                clock=rs.randrange(1, 8), anim_found=found,
                                                f38=rs.choice((MASK, 1))))
    # the counter path: mode nonzero, clock larger or smaller than the counter
    for state in (0x3EB, 0x3ED):
        for counter, clock in ((3, 1), (3, 3), (3, 9), (1, 1), (2, 1)):
            for a1a4 in (0, 4):
                if a1a4 == 0 and clock >= counter:
                    continue
                yield one(f"{state:#x} counter {counter} clock {clock} a1a4={a1a4}",
                          build(state, rs, a190=0x77, a19c=counter, a1a0=5, a1a4=a1a4, clock=clock,
                                anim_found=both))
    # states 0x3ee and 0x3ef: phase test against the time global
    for state in (0x3EE, 0x3EF):
        for period in (1, 2, 7, 1000, 3999):
            for threshold in (0, 5, 1000, 3999):
                time = rs.randrange(0, 1 << 20)
                origin = rs.randrange(0, 4000)
                yield one(f"{state:#x} period {period} threshold {threshold}",
                          build(state, rs, period=period, f148=threshold, time=time, origin=origin))
        for time, origin, period, threshold in ((10, 10, 5, 0), (9, 10, 5, 4), (0, 0xFFFFFFF0, 3, 1),
                                                (100, 99, 1000, 0), (100, 99, 1000, 1), (0xFFFFFFFF, 0, 4, 2),
                                                (0x80000000, 0, 3, 0xFFFFFFFF), (5, 0, 5, 0x7FFFFFFF)):
            yield one(f"{state:#x} edge time {time:#x} origin {origin:#x}",
                      build(state, rs, period=period, f148=threshold, time=time, origin=origin))
    # unknown states change nothing
    for state in (1, 2, 0x3E9, 0x3F0, 0x3F1, 0x400, 0x7FFFFFFF, 0x80000000, MASK):
        yield one(f"idle state {state:#x}", build(state, rs))
    for _ in range(20):
        state = rs.choice((0,) + STATES + (rs.randrange(1, 1 << 30),))
        yield one("random", build(state, rs, entry=rs.choice(ROUTINES + (None,)), anim_found=rs.choice(((), both)),
                                  sound_found=rs.choice(((), (NAME_RISE, NAME_SINK))), service_live=rs.choice((False, True)),
                                  a190=rs.choice((0, 0)), link=rs.choice((True, True, False))))
