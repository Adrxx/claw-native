"""Cases for player_end_life: End Life command: player kill 0x41f490."""
from clawparity.cases import Case

END_LIFE = 0x41F490
KEY = b"CLAW_FALLDEATH\0"

G_GAME = 0x537204       # object whose +0x0c flags are cleared
G_WORLD = 0x5371FC      # object whose +0x14 gates the music switch
G_PAUSED = 0x53C9C0
G_MODE = 0x534EAC
G_COUNTER = 0x534EA8
G_CLEARED = (0x534DE8, 0x534DEC, 0x534DD0, 0x534DD4)


def noise(random_source, count):
    return random_source.getrandbits(8 * count).to_bytes(count, "little")


def word(random_source):
    return random_source.randrange(1, 1 << 32)


def hash_key(count):
    value = 0
    for byte in KEY[:-1]:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & 0xFFFFFFFF
    return value % count


def build(random_source, health=1, hooked=False, hook_limit=1, bitset_big=False, state_flag=0, state_anim="none",
          lookup="miss", frame_type=0, frame_mode=0, frame_flags=0, frame_ticks=0, owner_flags=0, face=0x2134,
          mode=0, counter=0, side=0, world_gate=False, buckets=3, probe=None):
    """setup() for a player actor with the given health and everything 0x417b00 reaches kept cheap."""

    def setup(env):
        r = random_source
        actor = env.object(0x1C0, "actor", data=noise(r, 0x1C0))
        logic = env.object(0x40, "logic", data=noise(r, 0x40))
        state = env.object(0x140, "state", data=noise(r, 0x140))
        owner = env.object(0x180, "owner", data=noise(r, 0x180))
        game = env.object(0x20, "game", data=noise(r, 0x20))
        world = env.object(0x60, "world", data=noise(r, 0x60))
        sprite = env.object(0x40, "sprite", data=noise(r, 0x40))
        table = env.object(0x40, "table", data=noise(r, 0x40))
        env.put(actor + 0x6C, logic)
        env.put(actor + 0x10C, health & 0xFFFFFFFF)
        env.put(actor + 0x0C, sprite)
        env.put(actor + 0x64, face)
        env.put(actor + 0x170, 0)
        env.put(actor + 0x188 + 4, owner)
        env.put(logic + 0x14, state)
        env.put(sprite + 0x2C, table)
        env.put(owner + 0x170, 0)
        env.put(owner + 0x40, owner_flags)
        env.put(state + 4, state_flag)
        env.put(state + 0x124, 0)
        env.put(state + 0x12C, 0)
        env.put(state + 0x130, 0)
        tokens = {"actor": actor, "logic": logic, "state": state, "owner": owner, "game": game, "world": world}

        # the animation lookup table at table + 0x10: miss, or a chain that ends in the matching node
        buckets_ptr = env.object(4 * buckets, "buckets", fill=0)
        env.put(table + 0x10 + 4, buckets_ptr)
        env.put(table + 0x10 + 8, buckets)
        key = env.object(len(KEY), "key", data=KEY)
        other = env.object(16, "other-key", data=b"CLAW_FALLDEATI\0\0")
        slot = hash_key(buckets)
        wrong = env.object(16, "wrong-node", words=[0, word(r), other, word(r)])
        if lookup == "miss":
            env.put(buckets_ptr + 4 * slot, wrong)
        elif lookup == "empty":
            pass
        elif lookup == "none":
            env.put(table + 0x10 + 4, 0)
        else:
            frame = env.object(0x40, "frame", data=noise(r, 0x40))
            env.put(frame + 4, frame_flags)
            env.put(frame + 8, frame_type)
            env.put(frame + 0xC, 9)
            env.put(frame + 0x10, frame_mode)
            env.put(frame + 0x18, frame_ticks)
            env.put(frame + 0x2C, 0)
            frames = env.object(8, "frames", words=[frame, 0])
            anim = env.object(0x20, "anim", data=noise(r, 0x20))
            env.put(anim + 0x0C, frames)
            env.put(anim + 0x10, 1)
            node = env.object(16, "node", words=[wrong if lookup == "second" else 0, word(r), key, anim])
            if lookup == "second":
                env.put(wrong, 0)
                env.put(buckets_ptr + 4 * slot, wrong)
                env.put(wrong, node)
            else:
                env.put(buckets_ptr + 4 * slot, node)
            if probe is not None:
                # frame type 3 makes 0x4c82a0 read word [set + 0x14] + 4 * index into owner + 0x174: aim it at health
                env.put(frame + 8, 3)
                env.put(frame + 0x14, probe)
                chosen = env.object(0x80, "sprite-set", data=noise(r, 0x80))
                env.put(chosen + 0x64, 0)
                env.put(chosen + 0x68, 3)
                env.put(chosen + 0x14, actor + 0x10C - 4 * probe)
                env.put(owner + 0x170, chosen)
                tokens["sprite_set"] = chosen
            tokens["found_anim"] = anim
            tokens["frame"] = frame

        if state_anim != "none":
            frame2 = env.object(0x40, "frame2", data=noise(r, 0x40))
            frames2 = env.object(8, "frames2", words=[frame2, 0])
            anim2 = env.object(0x20, "anim2", data=noise(r, 0x20))
            env.put(anim2 + 0x0C, frames2)
            env.put(anim2 + 0x10, 1)
            env.put(state + 0x124, anim2)
            tokens["state_anim"] = anim2

        if hooked:
            hook = env.object(0x80, "hook", data=noise(r, 0x80))
            hook_logic = env.object(0x20, "hook-logic", data=noise(r, 0x20))
            pool = env.object(0x340, "pool", data=noise(r, 0x340))
            env.put(state + 0x12C, hook)
            env.put(hook + 0x6C, hook_logic)
            env.put(hook_logic + 0x18, pool)
            env.put(pool + 0x14, word(r))
            env.put(pool + 0x20, hook_limit)
            if bitset_big:
                bits = env.object(16, "bits", data=noise(r, 16))
                env.put(pool + 0x2F4 + 8, 0x40)
                env.put(pool + 0x2F4 + 0xC, bits)
                tokens["bits"] = bits
            else:
                env.put(pool + 0x2F4 + 8, 0x20)
            tokens["pool"] = pool
            tokens["hook"] = hook

        env.put(G_GAME, game)
        env.put(G_WORLD, world)
        env.put(world + 0x14, 0)
        env.put(G_PAUSED, 0)
        if world_gate:
            env.put(world + 0x14, word(r))
            env.put(G_PAUSED, word(r))
        env.put(G_MODE, mode)
        env.put(G_COUNTER, counter)
        for index, address in enumerate(G_CLEARED):
            env.put(address, 0x11110000 + index * 0x1111 + word(r) % 0xFFF)
        if mode == 0x26BC:
            extra = env.object(0x20, "extra", data=noise(r, 0x20))
            if side:
                env.put(state + 0x130, extra)
            tokens["extra"] = extra
        return tokens

    return setup


def unhealthy(random_source, health, size=0x110):
    """An actor of the smallest legal size: nothing past +0x10c may be touched, and +0x6c is a trap."""

    def setup(env):
        actor = env.object(size, "actor", data=noise(random_source, size))
        env.put(actor + 0x6C, 0xDEAD0000 | random_source.randrange(0, 0x10000) | 1)
        env.put(actor + 0x10C, health & 0xFFFFFFFF)
        return {"actor": actor}

    return setup


def case(label, setup):
    return Case(label, END_LIFE, setup, arguments=(lambda tokens: tokens["actor"],))


def cases(random_source):
    r = random_source
    yield Case("null actor", END_LIFE, None, arguments=(0,))
    for health in (0, -1, -2, 0x80000000, 0xFFFFFFFF & -0x7FFFFFFF, -r.randrange(2, 1 << 31), 0):
        yield case(f"health {health} does nothing", unhealthy(r, health))
    yield case("health 0 on a larger actor", build(r, health=0))
    yield case("negative health on a larger actor", build(r, health=-r.randrange(1, 1 << 31), hooked=True))

    # health > 0, plain paths
    for health in (1, 2, 0x7FFFFFFF, r.randrange(3, 1 << 31), r.randrange(3, 1 << 31)):
        yield case(f"health {health} is cleared", build(r, health=health))
    yield case("face already 0x2134", build(r, face=0x2134))
    yield case("face differs", build(r, face=r.randrange(0, 0x2134)))
    yield case("face differs high", build(r, face=r.randrange(0x2135, 1 << 32)))

    # private state variations
    for flag in (0, 1, r.randrange(2, 1 << 32)):
        for anim in ("none", "frames"):
            yield case(f"state flag {flag:#x} anim {anim}", build(r, state_flag=flag, state_anim=anim))
    for limit in (0, 1, 2, r.randrange(3, 1 << 31), -1):
        for big in (False, True):
            yield case(f"hooked limit {limit} big {big}", build(r, hooked=True, hook_limit=limit, bitset_big=big))
    yield case("hooked with state flag and anim", build(r, hooked=True, state_flag=1, state_anim="frames", bitset_big=True))

    # animation lookup found, with the frame shapes 0x4c82a0 branches on
    for kind in ("found", "second"):
        for ftype in range(0, 9):
            yield case(f"{kind} frame type {ftype}", build(r, lookup=kind, frame_type=ftype, frame_mode=ftype % 4))
    for mode in range(0, 5):
        for flags in (0, 1, 4, 5):
            for owner_flags in (0, 2):
                for ticks in (0, r.randrange(1, 1 << 16)):
                    if (mode + flags + owner_flags + (ticks > 0)) % 3 == 0:
                        yield case(f"frame mode {mode} flags {flags} owner {owner_flags} ticks {ticks}",
                                   build(r, lookup="found", frame_type=mode, frame_mode=mode, frame_flags=flags,
                                         owner_flags=owner_flags, frame_ticks=ticks))
    for lookup in ("miss", "empty", "none"):
        for buckets in (1, 3, 17):
            yield case(f"lookup {lookup} buckets {buckets}", build(r, lookup=lookup, buckets=buckets, state_flag=1,
                                                                    state_anim="frames"))
    for buckets in (1, 2, 7, 31):
        yield case(f"found with {buckets} buckets", build(r, lookup="found", buckets=buckets, state_flag=1,
                                                          state_anim="frames", hooked=True))

    # music and mode bookkeeping in 0x41f990
    for mode in (0, 5, 0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BD):
        for counter in (0, 0xF3E58, 0xF3E59, 0x7FFFFFFF, r.randrange(1, 0xF3E58)):
            if mode in (0, 0x26B7) or counter == 0:
                yield case(f"mode {mode:#x} counter {counter:#x}", build(r, mode=mode, counter=counter))
    for side in (0, 1):
        yield case(f"mode 0x26bc side {side}", build(r, mode=0x26BC, side=side))
    yield case("world gate with pause", build(r, world_gate=True))
    yield case("world gate with mode 0x26bd", build(r, world_gate=True, mode=0x26BD, hooked=True))

    # health is observable through a sprite-set lookup that runs before 0x417b00 clears it
    for index in (0, 1, 2, 3):
        yield case(f"health read by lookup index {index}", build(r, health=r.randrange(1, 1 << 31), lookup="found",
                                                                 probe=index))
    yield case("health 1 read by lookup", build(r, health=1, lookup="found", probe=0, hooked=True))

    # random mixtures
    for _ in range(30):
        yield case("random mixture", build(
            r, health=r.randrange(1, 1 << 31), hooked=bool(r.getrandbits(1)), hook_limit=r.randrange(-3, 4),
            bitset_big=bool(r.getrandbits(1)), state_flag=r.randrange(0, 3), state_anim=r.choice(("none", "frames")),
            lookup=r.choice(("miss", "empty", "none", "found", "second")), frame_type=r.randrange(0, 9),
            frame_mode=r.randrange(0, 4), frame_flags=r.randrange(0, 8), frame_ticks=r.choice((0, r.randrange(1, 1 << 16))),
            owner_flags=r.randrange(0, 4), face=r.choice((0x2134, r.randrange(0, 1 << 32))),
            mode=r.choice((0, 5, 0x26B7, 0x26BD)), counter=r.choice((0, 0xF3E58, r.randrange(0, 1 << 24))),
            buckets=r.randrange(1, 40)))
