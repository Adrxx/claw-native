"""Cases for boss_warp: BossWarp object logic."""
from clawparity.cases import Case
from clawparity.fixtures import returns

WARP = 0x470870
GLOBAL_ENGINE = 0x5371FC
GLOBAL_TIMER = 0x5430C4


def key_hash(name, buckets):
    value = 0
    for byte in name.encode():
        signed = byte - 256 if byte > 127 else byte
        value = (value * 33 + signed) & 0xFFFFFFFF
    return value % buckets


def make_map(env, holder, entries, buckets=7):
    """A string-keyed hash map at holder+0x10: +4 bucket array, +8 bucket count, nodes [next, ?, key, value]."""
    array = env.object(4 * buckets, "buckets", fill=0)
    env.put(holder + 0x10, 0, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 1, "key", data=name.encode() + b"\0")
        node = env.object(0x10, "node", fill=0)
        slot = array + 4 * key_hash(name, buckets)
        env.put(node, env.get(slot))
        env.put(node + 8, key, value)
        env.put(slot, node)


def animation(env, kind=0, frames=1, delay=0x66):
    """An animation record: +0x10 frame count, +0xc frame array; frame +8 is the frame kind, +0x1c its delay."""
    frame = env.object(0x80, "frame", fill=0)
    env.put(frame + 0x08, kind)
    env.put(frame + 0x1C, delay)
    array = env.object(4 * max(1, frames), "frames", fill=0)
    env.put(array, frame)
    record = env.object(0x40, "animation", fill=0)
    env.put(record + 0x0C, array)
    env.put(record + 0x10, frames)
    return record


def scene(state, magic=None, anim_maps=None, spawn_map=None, buckets=7, life=0, flags=0x5, anim=0,
          rect=None, mode=4, owner_slot=0x77777777, timer=0x4321, mutate=None):
    """One boss-warp object.  magic, anim_maps and spawn_map are dictionaries name -> value for the three lookup maps."""
    def setup(env):
        owner = env.object(0x200, "owner", fill=0)
        env.put(owner + 0x1C, state)
        env.put(owner + 0x168, owner_slot)
        obj = env.object(0x300, "object", fill=0)
        parent = env.object(0x100, "parent", fill=0)
        holder_28 = env.object(0x40, "holder-28", fill=0)
        holder_2c = env.object(0x40, "holder-2c", fill=0)
        spawner = env.object(0x100, "spawner", fill=0)
        spawner_c = env.object(0x40, "spawner-c", fill=0)
        holder_14 = env.object(0x40, "holder-14", fill=0)
        env.put(parent + 0x08, spawner)
        env.put(parent + 0x28, holder_28)
        env.put(parent + 0x2C, holder_2c)
        env.put(spawner + 0x0C, spawner_c)
        env.put(spawner_c + 0x14, holder_14)
        make_map(env, holder_28, magic or {}, buckets)
        make_map(env, holder_2c, anim_maps or {}, buckets)
        make_map(env, holder_14, spawn_map or {}, buckets)
        env.put(obj + 0x08, flags)
        env.put(obj + 0x0C, parent)
        env.put(obj + 0x4C, 0x1234)
        env.put(obj + 0x50, 0x5678)
        env.put(obj + 0x64, life)
        env.put(obj + 0x6C, owner)
        env.put(obj + 0x138, 0x1000)
        env.put(obj + 0x13C, 0x2000)
        env.put(obj + 0x140, 0x3000)
        env.put(obj + 0x144, 0x4000)
        env.put(obj + 0x190, anim)
        if rect is not None:
            r = env.object(0x40, "rect", fill=0)
            env.put(r + 0x18, *rect[:2])
            env.put(r + 0x20, *rect[2:])
            env.put(obj + 0x174, r)
        engine = env.object(0x80, "engine", fill=0)
        manager = env.object(0x10, "manager", fill=0)
        vtable = env.object(0x40, "vtable", fill=0)
        env.put(engine + 0x2C, manager)
        env.put(manager, vtable)
        env.put(vtable + 0x10, env.stub("query", "thiscall", 0, returns(mode)))
        env.put(GLOBAL_ENGINE, engine)
        env.put(GLOBAL_TIMER, timer)
        tokens = {"obj": obj, "owner": owner}
        if mutate:
            mutate(env, tokens)
        return tokens
    return setup


def run(label, setup, **options):
    return Case(label, WARP, setup, arguments=(lambda t: t["obj"],), **options)


def cases(random_source):
    yield run("state 5", scene(5))
    yield run("state other", scene(3))
    yield run("state 0 mode 4", scene(0))
    yield run("state 0 mode 2", scene(0, mode=2))
    yield run("state 0 with life, anim", scene(0, life=77, anim=0x999, mode=2))
    yield run("state 0 with rect", scene(0, rect=(10, 20, 300, 400), mode=2))
    yield run("magic value found", scene(0, magic={"GAME_MAGICPOWERUP": 0x31337}, mode=2))
    yield run("magic found, mode 4", scene(0, magic={"GAME_MAGICPOWERUP": 0xABCDEF01}))
    yield run("magic collides with other keys", scene(0, magic={"GAME_MAGICPOWERUP": 5, "GAME_MAGICPOWERUPS": 6, "X": 7}, buckets=1, mode=2))
    yield run("spawn map miss", scene(0, spawn_map={"EndOfLevelPowerups": 0x4242}))
    yield run("bosswarp animation found, flag word nonzero", scene(0, anim_maps={"GAME_BOSSWARP": 0x5000}, anim=3))

    def with_anim_state(extra):
        def mutate(env, tokens):
            for offset, value in extra.items():
                env.put(tokens["obj"] + 0x188 + offset, value)
        return mutate

    yield run("state 5 with animation countdown", scene(5, mutate=with_anim_state({0x08: 1, 0x14: 9, 0x18: 0, 0x20: 0x44, 0x24: 0x55})))
    yield run("state 5 countdown expires", scene(5, timer=20, mutate=with_anim_state({0x08: 1, 0x14: 9, 0x18: 0, 0x20: 0x44, 0x24: 0x55})))

    def named_animation(name, **options):
        def mutate(env, tokens):
            record = animation(env, **options)
            slot_owner = env.get(env.get(tokens["obj"] + 0x0C) + 0x2C)
            map_base = slot_owner + 0x10
            buckets = env.get(map_base + 8)
            node = env.get(env.get(map_base + 4) + 4 * key_hash(name, buckets))
            while node:
                if env.cstr(env.get(node + 8)) == name.encode():
                    env.put(node + 0x0C, record)
                node = env.get(node)
        return mutate

    for name in ("GAME_BOSSWARP", "GAME_POWERUP"):
        placeholder = {name: 1}
        yield run(f"{name} animation found", scene(0, anim_maps=placeholder, mutate=named_animation(name)))
    yield run("both names present, bosswarp wins", scene(0, anim_maps={"GAME_BOSSWARP": 1, "GAME_POWERUP": 1}, mutate=named_animation("GAME_BOSSWARP", kind=0, delay=0x1234)))

    def stale(extra):
        def mutate(env, tokens):
            for offset, value in extra.items():
                env.put(tokens["obj"] + offset, value)
        return mutate

    yield run("stale 0xc8 and owner 0x168 cleared", scene(0, mutate=stale({0xC8: 0x7A7A7A7A})))
    yield run("stale 0xc8 mode 2 magic", scene(0, mode=2, magic={"GAME_MAGICPOWERUP": 9}, mutate=stale({0xC8: 0x1357})))
    neighbours = {o: 0x600D0000 + o for o in (0x184, 0x18C, 0x194, 0x198, 0x1A0, 0x1B0, 0x1C0, 0x110, 0x150)}
    yield run("anim slot zero, neighbours set, bosswarp found",
              scene(0, anim_maps={"GAME_BOSSWARP": 1}, mutate=lambda e, t: (named_animation("GAME_BOSSWARP")(e, t), stale(neighbours)(e, t))))
    yield run("anim slot zero, neighbours set, powerup found",
              scene(0, anim_maps={"GAME_POWERUP": 1}, mutate=lambda e, t: (named_animation("GAME_POWERUP")(e, t), stale(neighbours)(e, t))))
    yield run("anim slot set, bosswarp record found",
              scene(0, anim=0x4444, anim_maps={"GAME_BOSSWARP": 1}, mutate=named_animation("GAME_BOSSWARP", delay=0x2222)))
    yield run("anim slot set, powerup record found",
              scene(0, anim=0x4444, anim_maps={"GAME_POWERUP": 1}, mutate=named_animation("GAME_POWERUP", delay=0x2222)))

    for mode in (0, 1, 3, 5, 0xFFFFFFFF):
        yield run(f"query returns {mode:#x}", scene(0, mode=mode, life=5))
    yield run("life already set keeps flags", scene(0, life=0xFFFFFFFF, flags=0xFFFFFFFF, mode=4))
    yield run("flags without 0x20000 gain it", scene(0, flags=0x100, mode=2))
    yield run("rect wraps", scene(0, rect=(0xFFFFFFF0, 0x80000000, 0x7FFFFFFF, 5), mode=2))
    yield run("rect negative origin", scene(0, rect=(0xFFFFFF00, 0xFFFFFE00, 40, 50), mode=4))

    def live_animation(kind):
        def mutate(env, tokens):
            record = animation(env, kind=kind)
            env.put(tokens["obj"] + 0x188 + 0x08, record)
            env.put(tokens["obj"] + 0x188 + 0x0C, env.get(env.get(record + 0x0C)))
            env.put(tokens["obj"] + 0x188 + 0x04, tokens["obj"])
        return mutate

    for kind in range(0, 8):
        yield run(f"state 5 with frame kind {kind}", scene(5, mutate=live_animation(kind)))

    for index in range(30):
        state = random_source.choice((0, 0, 0, 5, random_source.randrange(1, 9)))
        names = {}
        if random_source.random() < 0.5:
            names["GAME_MAGICPOWERUP"] = random_source.getrandbits(32) | 1
        rect = None
        if random_source.random() < 0.6:
            rect = tuple(random_source.getrandbits(32) for _ in range(4))
        yield run(
            f"random {index} state {state}",
            scene(
                state,
                magic=names,
                spawn_map={"EndOfLevelPowerupX": 1} if random_source.random() < 0.3 else None,
                buckets=random_source.randrange(1, 12),
                life=random_source.choice((0, 0, random_source.getrandbits(32))),
                flags=random_source.getrandbits(32),
                anim=0 if state == 5 else random_source.choice((0, random_source.getrandbits(32) | 1)),
                rect=rect,
                mode=random_source.choice((4, 4, random_source.randrange(0, 9))),
                owner_slot=random_source.getrandbits(32),
                timer=random_source.getrandbits(32),
            ),
        )
