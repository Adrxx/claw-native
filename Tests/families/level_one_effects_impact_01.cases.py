"""Cases for level_one_effects_impact_01: Level 1 impact particle effects (HitBurst and Splash)."""
from clawparity.cases import Case
from clawparity.fixtures import sequence

M32 = 0xFFFFFFFF
RAND, NEW = 0x4A3050, 0x4F63EC
BURST, SPLASH_CREATE, HIT_UPDATE, SPLASH_UPDATE = 0x461A00, 0x461C40, 0x461A90, 0x461BC0
DELTA = 0x5430C4                      # frame delta read by the animation update

N_ENEMY, N_CLAW = b"GAME_ENEMYHIT", b"GAME_CLAWHIT"
N_SML, N_MED, N_BIG = b"GAME_SMLHITBURST", b"GAME_MEDHITBURST", b"GAME_BIGHITBURST"
N_GSPLASH, N_LSPLASH = b"GAME_SPLASH", b"LEVEL_SPLASH"
BURST_NAME, SPLASH_NAME = b"HitBurst", b"Splash"

FLAG_DONE = 0x10000


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def registry(env, r, entries, buckets=5):
    """String table behind 0x4f6286, at owner+0x10 (+4 bucket array, +8 bucket count). Node: [next, 0, key, value]."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(owner + 0x10 + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)
    return owner


def animation(env, r, count=None):
    """An animation resource read by 0x4c8220: +0xc array of frame pointers, +0x10 count (at least one)."""
    count = count or r.randrange(1, 4)
    frames = [env.object(0x30, "frame", words=words_of(r, 12)) for _ in range(count)]
    array = env.object(4 * count, "frame-array", words=frames)
    return env.object(0x30, "animation", words=[0, 0, 0, array, count] + words_of(r, 7)), frames


def sprite_set(env, r, low=None, high=None):
    """A frame-set read by 0x4c7970: +0x64 first, +0x68 last, +0x14 table of frame values indexed by first."""
    low = r.randrange(0, 6) if low is None else low
    high = r.randrange(low, low + 4) if high is None else high
    table = env.object(0x40, "sprite-table", words=words_of(r, 16))
    obj = env.object(0x80, "sprite-set", words=words_of(r, 0x20))
    env.put(obj + 0x14, table)
    env.put(obj + 0x64, low & M32, high & M32)
    return obj


def metadata_for(env, r, callback, flags):
    meta = env.object(0x18, "actor-metadata", words=words_of(r, 6))
    env.put(meta + 8, flags)
    env.put(meta + 0x10, callback)
    return meta


def world(env, r, a_names=(N_ENEMY, N_CLAW, N_LSPLASH, N_GSPLASH), c_names=(N_SML, N_MED, N_BIG, N_GSPLASH, N_LSPLASH),
          b_names=(BURST_NAME, SPLASH_NAME), burst_flags=None, splash_flags=None, sets=None, extra_a=None,
          sprite_args=None, callback=True, log_tag=0):
    """A scene with its context, three name tables, an observation log and a service callback."""
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    env.put(scene + 0xC, context)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for i in range(63):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    log = env.object(0x800, "observations", fill=0)
    fill = r.randrange(1, 256)

    def allocate_filled(env, call):
        return env.object(call.arguments[0], "allocation", fill=fill)
    env.override(NEW, allocate_filled)

    def notify(env, call):
        actor = call.arguments[0]
        n = env.get(log)
        env.put(log, n + 1)
        row = log + 4 + n * 40
        service = env.get(actor + 0x6C)
        env.put(row, log_tag, call.receiver, actor, env.get(actor + 0x80), env.get(actor + 0x16C),
                env.get(actor + 0x170), env.get(actor + 0x174), env.get(service + 0x1C), env.get(actor + 8))
        return 0
    stub = env.stub("hit-burst-service-callback", "cdecl", 1, notify)

    sets = sets or {}
    a_values = {}
    for name in a_names:
        a_values[name] = sets.get(name) or sprite_set(env, r)
    if extra_a:
        a_values.update(extra_a)
    anims, frames = {}, {}
    for name in c_names:
        anims[name], frames[name] = animation(env, r)
    metas = {}
    for name in b_names:
        flags = burst_flags if name == BURST_NAME else splash_flags
        metas[name] = metadata_for(env, r, stub if callback else 0, r.randrange(0, 4) if flags is None else flags)
    env.put(context + 0x10, registry(env, r, a_values))
    env.put(context + 0x14, registry(env, r, metas))
    env.put(context + 0x2C, registry(env, r, anims))
    owner = env.object(0x20, "owner", words=words_of(r, 8))
    env.put(owner + 8, scene)
    return {"owner": owner, "scene": scene, "context": context, "log": log, "a": a_values, "c": anims,
            "frames": frames, "meta": metas, "stub": stub}


def hit_target(env, r, flags=0, link=0x1234, x=None, y=None):
    target = env.object(0x60, "hit-target", words=words_of(r, 0x18))
    env.put(target + 8, flags)
    env.put(target + 0x38, link)
    env.put(target + 0x4C, r.randrange(0, 1 << 32) if x is None else x)
    env.put(target + 0x50, r.randrange(0, 1 << 32) if y is None else y)
    return target


# ---------------------------------------------------------------------------------------------------------------
# 0x461a00 and 0x461c40: spawn
def burst_case(r, label, *, target="ok", flags=0, link=0x1234, hit=0, x=None, y=None, z=None, world_args=None):
    world_args = world_args or {}
    x = r.randrange(0, 1 << 32) & ~0x200000 if x is None else x

    def setup(env):
        t = world(env, r, **world_args)
        if target == "null":
            t["target"] = 0
        else:
            t["target"] = hit_target(env, r, flags, link)
        return t
    return Case(label, BURST, setup, arguments=(lambda t: t["owner"], x, r.randrange(0, 1 << 32) if y is None else y,
                                                r.randrange(-50, 50) & M32 if z is None else z, hit,
                                                lambda t: t["target"]))


def splash_case(r, label, *, null_owner=False, x=None, world_args=None):
    world_args = world_args or {}
    x = r.randrange(0, 1 << 32) & ~0x200000 if x is None else x

    def setup(env):
        t = world(env, r, **world_args)
        return t
    return Case(label, SPLASH_CREATE, setup,
                arguments=(0 if null_owner else (lambda t: t["owner"]), x, r.randrange(0, 1 << 32),
                           r.randrange(-50, 50) & M32))


def spawn_cases(r):
    # Deterministic guard grid on the target.
    yield burst_case(r, "target null", target="null")
    yield burst_case(r, "target null, claw", target="null", hit=1)
    for link in (M32, 0, 1, 0xFFFFFFFE, 0x7FFFFFFF, 0x80000000):
        for flags in (0, FLAG_DONE, M32, 0xFFFEFFFF, 0x8000, 0x20000, 0x10000 | 0x21):
            yield burst_case(r, f"target link {link:#x} flags {flags:#x}", flags=flags, link=link)
    # Hit type selects the animation-set name; the creation flag bit 0x200000 runs the service callback early.
    for hit in (0, 1, 2, 0x100, 0x80000000, M32):
        for bit in (0, 0x200000):
            yield burst_case(r, f"hit {hit:#x} x-bit {bit:#x}", hit=hit, x=(r.randrange(0, 1 << 32) & ~0x200000) | bit)
    # Frame-set ranges for the two names: low <= high, low > high, signed comparison.
    for low, high in ((0, 0), (2, 5), (3, 3), (5, 2), (1, 0x80000000), (0, M32), (4, 7)):
        for hit in (0, 1):
            def setup(env, hit=hit, low=low, high=high):
                t = world(env, r, a_names=())
                # swap in sets built with explicit ranges, distinct for each name
                a = {N_ENEMY: sprite_set(env, r, low, high), N_CLAW: sprite_set(env, r, low + 1, high + 1)}
                env.put(t["context"] + 0x10, registry(env, r, a))
                t["a"] = a
                t["target"] = hit_target(env, r)
                return t
            yield Case(f"burst sets {low:#x}..{high:#x} hit {hit}", BURST, setup,
                       arguments=(lambda t: t["owner"], 0x1111, 0x2222, 3, hit, lambda t: t["target"]))
    # Missing names.
    base = dict(target="ok")
    yield burst_case(r, "no HitBurst metadata", world_args={"b_names": (SPLASH_NAME,)})
    yield burst_case(r, "no metadata at all", world_args={"b_names": ()})
    yield burst_case(r, "no enemy-hit set", world_args={"a_names": (N_CLAW,)})
    yield burst_case(r, "no claw-hit set", hit=1, world_args={"a_names": (N_ENEMY,)})
    yield burst_case(r, "no claw-hit set but enemy", hit=0, world_args={"a_names": (N_ENEMY,)})
    yield burst_case(r, "no enemy-hit set but claw", hit=1, world_args={"a_names": (N_CLAW,)})
    yield burst_case(r, "no sets at all", world_args={"a_names": ()})
    yield burst_case(r, "only the other metadata", world_args={"b_names": (SPLASH_NAME,)}, hit=1)
    # Metadata flag combinations.
    for meta_flags in (0, 1, 2, 3):
        yield burst_case(r, f"metadata flags {meta_flags}", world_args={"burst_flags": meta_flags})
    # Randomized end to end.
    for i in range(30):
        yield burst_case(
            r, f"random burst {i}", flags=r.choice((0, 0x10000, r.randrange(0, 1 << 32))),
            link=r.choice((M32, r.randrange(0, 1 << 32))), hit=r.choice((0, r.randrange(0, 1 << 32))),
            x=r.randrange(0, 1 << 32), y=r.randrange(0, 1 << 32), z=r.randrange(0, 1 << 32),
            world_args={"burst_flags": r.randrange(0, 4)})
    # Splash creation.
    yield splash_case(r, "splash null owner", null_owner=True)
    yield splash_case(r, "splash ok")
    for bit in (0, 0x200000):
        yield splash_case(r, f"splash x-bit {bit:#x}", x=(r.randrange(0, 1 << 32) & ~0x200000) | bit)
    yield splash_case(r, "splash name missing", world_args={"b_names": (BURST_NAME,)})
    yield splash_case(r, "splash no names", world_args={"b_names": ()})
    for meta_flags in (0, 1, 2, 3):
        yield splash_case(r, f"splash metadata flags {meta_flags}", world_args={"splash_flags": meta_flags})
    for i in range(8):
        yield splash_case(r, f"random splash {i}", x=r.randrange(0, 1 << 32),
                          world_args={"splash_flags": r.randrange(0, 4)})

    # Found entry whose value is zero: the lookup reports found, so the call returns its found flag.
    def found_zero(env):
        t = world(env, r, b_names=())
        meta_owner = registry(env, r, {SPLASH_NAME: 0})
        env.put(t["context"] + 0x14, meta_owner)
        return t
    yield Case("splash entry present with zero value", SPLASH_CREATE, found_zero,
               arguments=(lambda t: t["owner"], 7, 8, 9))


# ---------------------------------------------------------------------------------------------------------------
# 0x461a90 and 0x461bc0: update
def actor_setup(r, *, state, target="ok", target_flags=0, link=0x77, a_names=None, c_names=None, rand=(0,),
                anim_state=None, delta=1, actor_flags=None, sets=None, missing_service=False, with_target=True):
    """An effect actor. anim_state is (anim_pointer_kind, timer, hold, done) for the animation player at +0x188."""
    def setup(env):
        kwargs = {}
        if a_names is not None:
            kwargs["a_names"] = a_names
        if c_names is not None:
            kwargs["c_names"] = c_names
        t = world(env, r, **kwargs)
        env.override(RAND, sequence(*rand))
        env.put(DELTA, delta)
        actor = env.object(0x1B4, "effect-actor", words=words_of(r, 0x1B4 // 4))
        service = env.object(0x40, "actor-service", words=words_of(r, 0x10))
        env.put(service + 0x1C, state)
        env.put(actor + 0xC, t["context"])
        env.put(actor + 0x6C, service)
        env.put(actor + 8, r.randrange(0, 1 << 32) if actor_flags is None else actor_flags)
        if with_target:
            if target == "null":
                env.put(actor + 0x80, 0)
            else:
                tgt = hit_target(env, r, target_flags, link)
                env.put(actor + 0x80, tgt)
                t["target"] = tgt
        if anim_state is not None:
            kind, timer, hold, done = anim_state
            base = actor + 0x188
            env.put(base + 0x14, timer)
            env.put(base + 0x18, hold)
            env.put(base + 0x1C, done)
            env.put(base + 0x20, r.randrange(1, 1 << 32), r.randrange(1, 1 << 32))
            if kind == "none":
                env.put(base + 8, 0)
            else:
                env.put(base + 8, env.object(0x30, "playing-animation", words=words_of(r, 12)))
        t["actor"] = actor
        t["service"] = service
        return t
    return setup


def update_case(r, label, function, **kwargs):
    return Case(label, function, actor_setup(r, **kwargs), arguments=(lambda t: t["actor"],))


# Animation-player states for the state-5 branch: (pointer kind, timer, hold, done) with a delta.
ANIM_STATES = [
    ("none", 0, 0, 0), ("none", 0, 0, 1), ("none", 5, 0, 0), ("none", 5, 0, 1), ("none", 5, 1, 1),
    ("none", 0, 1, 0), ("none", 0, 1, 1), ("none", M32, 1, 0xFFFF),
    ("set", 0, 0, 1),            # finished: copies the pending frame and stays at zero
    ("set", 1, 0, 1),            # unheld timer ticks down by one and reaches zero
    ("set", 1, 0, 0),
    ("set", 2, 0, 1),            # ticks down to one: not finished
    ("set", 2, 0, 0),
    ("set", 6, 1, 1),            # held timer reduced by the delta
]


def update_cases(r):
    # ---- 0x461a90 early exits and states
    yield update_case(r, "hit update: no target", HIT_UPDATE, state=0, target="null")
    yield update_case(r, "hit update: no target state 5", HIT_UPDATE, state=5, target="null")
    for state in (0, 5, 3):
        for link in (M32, 0, 1, 0x7FFFFFFF, 0x80000000):
            for flags in (0, FLAG_DONE, M32, 0xFFFEFFFF, 0x4000, 0x20000):
                yield update_case(r, f"hit update state {state} link {link:#x} flags {flags:#x}", HIT_UPDATE,
                                  state=state, link=link, target_flags=flags)
    for actor_flags in (0, M32, 0x10000, 0xFFFEFFFF, 0x21):
        yield update_case(r, f"hit update no target actor flags {actor_flags:#x}", HIT_UPDATE, state=0,
                          target="null", actor_flags=actor_flags)
    # State 0: which burst animation is chosen by the random number.
    for value in (0, 1, 2, 3, 4, 5, 7, 8, 100, 0x7FFF, 0x7FFE, M32, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC,
                  0x80000000, 0x80000001, 0x7FFFFFFF):
        yield update_case(r, f"hit update spawn rand {value:#x}", HIT_UPDATE, state=0, rand=(value,))
    for value in (0, 1, 2, M32, 4):
        for missing in (N_SML, N_MED, N_BIG):
            names = tuple(n for n in (N_SML, N_MED, N_BIG, N_GSPLASH, N_LSPLASH) if n != missing)
            yield update_case(r, f"hit update spawn rand {value:#x} without {missing.decode()}", HIT_UPDATE,
                              state=0, rand=(value,), c_names=names)
    for actor_flags in (0, M32, 0x21, 0x10000):
        yield update_case(r, f"hit update spawn flags {actor_flags:#x}", HIT_UPDATE, state=0, rand=(1,),
                          actor_flags=actor_flags)
    # Other states do nothing.
    for state in (1, 2, 4, 6, 9, 0x80000000, M32, 0x500, 0x105):
        yield update_case(r, f"hit update state {state:#x}", HIT_UPDATE, state=state)
    # State 5 with every animation-player situation and delta.
    for anim in ANIM_STATES:
        for delta in (0, 1, 3, 6, 7, M32):
            yield update_case(r, f"hit update follow {anim} delta {delta:#x}", HIT_UPDATE, state=5,
                              anim_state=anim, delta=delta)
    for delta in (4, 5, 6):
        yield update_case(r, f"hit update held exact timer delta {delta}", HIT_UPDATE, state=5,
                          anim_state=("set", 5, 1, 1), delta=delta)
    for i in range(25):
        anim = (r.choice(("none", "set")), r.choice((0, 1, 2, r.randrange(0, 1 << 32))),
                r.choice((0, 1, 5)), r.choice((0, 1, 7)))
        if anim[0] == "set" and anim[3] == 0:
            anim = ("set", r.randrange(1, 4), 0, 0)
        yield update_case(r, f"hit update random follow {i}", HIT_UPDATE, state=5, anim_state=anim,
                          delta=r.choice((0, 1, 2, r.randrange(0, 1 << 32))), link=r.randrange(0, 0x7FFFFFFF),
                          actor_flags=r.randrange(0, 1 << 32))

    # ---- 0x461bc0
    for state in (0,):
        for actor_flags in (0, M32, 0x21, 0x10000, 0x20, 0x01):
            yield update_case(r, f"splash update spawn flags {actor_flags:#x}", SPLASH_UPDATE, state=state,
                              actor_flags=actor_flags, with_target=False)
    for names_c, names_a, label in (
            ((N_GSPLASH,), (N_LSPLASH,), "only own names"),
            ((N_LSPLASH,), (N_GSPLASH,), "names in the other table"),
            ((), (), "no names"),
            ((N_GSPLASH,), (), "no level splash"),
            ((), (N_LSPLASH,), "no game splash"),
            ((N_GSPLASH, N_LSPLASH), (N_GSPLASH, N_LSPLASH), "both tables")):
        yield update_case(r, f"splash update spawn {label}", SPLASH_UPDATE, state=0, c_names=names_c,
                          a_names=names_a, with_target=False)
    for state in (1, 2, 4, 6, 9, 0x80000000, M32, 0x500, 0x105):
        yield update_case(r, f"splash update state {state:#x}", SPLASH_UPDATE, state=state, with_target=False)
    for anim in ANIM_STATES:
        for delta in (0, 1, 3, 6, 7, M32):
            yield update_case(r, f"splash update follow {anim} delta {delta:#x}", SPLASH_UPDATE, state=5,
                              anim_state=anim, delta=delta, with_target=False)
    for i in range(15):
        anim = (r.choice(("none", "set")), r.choice((0, 1, 2, r.randrange(0, 1 << 32))),
                r.choice((0, 1, 5)), r.choice((0, 1, 7)))
        if anim[0] == "set" and anim[3] == 0:
            anim = ("set", r.randrange(1, 4), 0, 0)
        yield update_case(r, f"splash update random follow {i}", SPLASH_UPDATE, state=5, anim_state=anim,
                          delta=r.choice((0, 1, 2, r.randrange(0, 1 << 32))), with_target=False,
                          actor_flags=r.randrange(0, 1 << 32))


def cases(random_source):
    yield from spawn_cases(random_source)
    yield from update_cases(random_source)
