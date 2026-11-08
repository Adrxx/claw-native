"""Cases for level_one_batch_claw_hit_ranged_02: Level 1 Claw hit reset (0x417b00) and ranged attack (0x41cc60).

Coverage is by explicit cases; random_source only varies the values and layouts.
"""
import random

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns, sequence  # noqa: F401

RESET = 0x417B00
RANGED = 0x41CC60
RAND = 0x4A3050

G_GAME = 0x5371FC       # pointer to game object
G_FLAGS = 0x537204      # pointer to object whose +0xc holds flags
G_CURRENT = 0x534EAC
G_COUNTER = 0x534EA8
G_PAUSE = 0x53C9C0
G_E00 = 0x540E00
G_CTYPE = 0x540BF8
G_SWORD_ARG = 0x532C10
G_SWORD_ON = 0x532C0C
G_FALL_ARG = 0x5430C4
G_534DE8 = 0x534DE8
G_534DEC = 0x534DEC
G_534DD0 = 0x534DD0
G_534DD4 = 0x534DD4

FIREBALL, LIGHTNING, ICE = 0x26B8, 0x26B9, 0x26BA
BULLET_NAMES = {FIREBALL: b"FireBullet", LIGHTNING: b"LightningBullet", ICE: b"IceBullet"}
SWORD_NAMES = {FIREBALL: b"CLAW_FIRESWORD", LIGHTNING: b"CLAW_LIGHTSWORD", ICE: b"CLAW_ICESWORD"}


def word(random_source):
    return random_source.randrange(1, 0x7FFFFFFF)


def string_hash(key):
    value = 0
    for byte in key:
        value = (value * 0x21 + (byte if byte < 128 else byte - 256)) & 0xFFFFFFFF
    return value


def build_map(env, base, entries, buckets, random_source, decoys=(), table=True):
    """Fill the string-to-pointer map whose object starts at `base` (+4 table, +8 bucket count)."""
    chains = [0] * buckets
    items = list(decoys) + list(entries)
    random_source.shuffle(items)
    for key, value in items:
        text = env.object(len(key) + 1, "key", fill=0)
        env.write(text, key + b"\0")
        node = env.object(16, "assoc", fill=0)
        index = string_hash(key) % buckets
        env.put(node, chains[index], string_hash(key), text, value)
        chains[index] = node
    env.put(base + 8, buckets)
    if table:
        array = env.object(4 * buckets, "buckets", fill=0)
        env.put(array, *chains)
        env.put(base + 4, array)
    else:
        env.put(base + 4, 0)


def animation(env, random_source, frames=2, mode=0, kind=9, flags=0):
    """An animation record (+0xc frame array, +0x10 count) with distinct frames."""
    frame_list = []
    for index in range(frames):
        frame = env.object(0x48, "frame", fill=0)
        env.put(frame + 0x04, flags)
        env.put(frame + 0x08, 0)
        env.put(frame + 0x0C, kind)
        env.put(frame + 0x10, mode)
        env.put(frame + 0x14, word(random_source))
        env.put(frame + 0x18, random_source.randrange(1, 90))
        env.put(frame + 0x1C, word(random_source))
        env.put(frame + 0x20, random_source.randrange(1, 5000))
        env.put(frame + 0x24, random_source.randrange(1, 5000))
        env.put(frame + 0x2C, 0)
        frame_list.append(frame)
    array = env.object(4 * frames, "frames", fill=0)
    env.put(array, *frame_list)
    record = env.object(0x40, "animation", fill=0)
    env.put(record + 0x0C, array)
    env.put(record + 0x10, frames)
    return record


def reset_world(random_source, *, current=0, counter=0, pending=True, grid=True, flags_bits=None,
                bitset=None, cursor=True, pending_queue=True, death=True, hit_flags=None, hit_depth=None,
                vtable_result=4, game_flag=0, pause=0, a64=None, t20=None, falldeath_mode=0,
                falldeath_flags=0, falldeath_kind=9, pending_anim=True, buckets=3, e00=0, powerup=True,
                other_fields=None, sword_on=0):
    def setup(env):
        r = random_source
        env.put(G_E00, e00)
        if e00:
            env.write(G_CTYPE, bytes(0x102))
        env.put(G_SWORD_ON, sword_on)
        env.put(G_SWORD_ARG, word(r))
        env.put(G_FALL_ARG, word(r))
        for address in (G_534DE8, G_534DEC, G_534DD0, G_534DD4):
            env.put(address, word(r))
        env.put(G_CURRENT, current)
        env.put(G_COUNTER, counter)
        env.put(G_PAUSE, pause)
        flags_object = env.object(0x20, "flags", fill=0)
        flag_word = flags_bits if flags_bits is not None else (r.getrandbits(32) | 0x03000000)
        env.put(flags_object + 0x0C, flag_word)
        env.put(G_FLAGS, flags_object)

        # game object
        game = env.object(0x800, "game", fill=0)
        env.put(G_GAME, game)
        vtable = env.object(0x40, "e-vtable", fill=0)
        env.put(vtable + 0x10, env.stub("e-state", "thiscall", 0, returns(vtable_result)))
        eobj = env.object(0x800, "e-object", fill=0)
        env.put(eobj, vtable)
        env.put(game + 0x2C, eobj)
        env.put(game + 0x14, game_flag)
        powerup_map = env.object(0x40, "sequence-map", fill=0)
        env.put(game + 0x50, powerup_map)
        env.put(powerup_map + 0x20, 0)

        # the actor
        actor = env.object(0x400, "actor", fill=0)
        env.write(actor, bytes(r.getrandbits(8) for _ in range(0x400)))
        env.put(actor + 0x04, word(r))
        env.put(actor + 0x08, r.getrandbits(32))
        env.put(actor + 0x64, a64 if a64 is not None else r.choice((0x2134, word(r))))
        env.put(actor + 0x18C, actor)
        # anim state at +0x188 (this of 0x4c8220/0x4c82a0)
        env.put(actor + 0x188 + 0x14, 0)
        env.put(actor + 0x188 + 0x1C, 0)
        env.put(actor + 0x188 + 0x28, 0x3F800000)
        scene = env.object(0x40, "scene-a", fill=0)
        env.put(actor + 0x0C, scene)
        resources = env.object(0x40, "resources", fill=0)
        env.put(scene + 0x2C, resources)
        entries = []
        if death:
            entries.append((b"CLAW_FALLDEATH", animation(env, r, frames=r.randrange(1, 4), mode=falldeath_mode,
                                                         kind=falldeath_kind, flags=falldeath_flags)))
        decoys = [(b"CLAW_FALLDEATH2", word(r)), (b"claw_falldeath", word(r)), (b"CLAW_FALL", word(r))]
        build_map(env, resources + 0x10, entries, buckets, r, decoys=decoys)
        # the actor's listener list used by 0x41f990 / 0x4ce7b0
        if cursor:
            listener = env.object(0x80, "listener", fill=0)
            env.put(listener + 0x64, 5)
            env.put(listener + 0x68, 4)  # empty range: nothing visited
            env.put(actor + 0x170, listener)
        else:
            env.put(actor + 0x170, 0)

        second = env.object(0x30, "b", fill=0)
        env.put(second + 0x1C, word(r))
        env.put(second + 0x20, word(r))

        claw = env.object(0x180, "claw", fill=0)
        env.write(claw, bytes(r.getrandbits(8) for _ in range(0x180)))
        env.put(claw + 0x04, word(r) if pending else 0)
        env.put(claw + 0x20, word(r))
        env.put(claw + 0x3C, word(r))
        env.put(claw + 0x40, word(r))
        env.put(claw + 0x124, animation(env, r, frames=r.randrange(1, 4), mode=r.choice((0, 1, 2, 3)),
                                        kind=r.choice((9, 9)), flags=r.choice((0, 0, 8))) if pending_anim else 0)
        env.put(claw + 0x130, env.object(0x20, "slot-object", fill=0) if r.getrandbits(1) else 0)
        if pending_queue:
            q = env.object(0x80, "q", fill=0)
            rr = env.object(0x80, "r", fill=0)
            t = env.object(0x400, "t", fill=0)
            env.write(t, bytes(r.getrandbits(8) for _ in range(0x400)))
            env.put(claw + 0x12C, q)
            env.put(q + 0x6C, rr)
            env.put(rr + 0x18, t)
            env.put(t + 0x20, t20 if t20 is not None else r.choice((0, 1, 2, 7)))
            env.put(t + 0x14, word(r))
            bits = bitset if bitset is not None else r.choice((0, 1, 5, 0x20, 0x21, 0x40, 0x80))
            base = t + 0x2F4
            env.put(base + 8, bits)
            if bits == 0 or bits <= 0x20:
                env.put(base + 0x0C, r.getrandbits(32))
            else:
                words = (bits + 31) // 32
                array = env.object(4 * words, "bits", fill=0)
                env.put(array, *[r.getrandbits(32) for _ in range(words)])
                env.put(base + 0x0C, array)
        else:
            env.put(claw + 0x12C, 0)
        if other_fields:
            other_fields(env, actor, claw)

        # powerup / level lookup is disabled (map reports empty)
        return {"actor": actor, "b": second, "claw": claw}
    return setup


def reset_case(label, random_source, rand_values=(), **options):
    flag = options.pop("flag", 0)
    sub = random.Random(random_source.getrandbits(64))
    setup = reset_world(sub, **options)
    wanted = tuple(rand_values)

    def full(env):
        tokens = setup(env)
        if wanted:
            env.override(RAND, sequence(*wanted))
        return tokens
    return Case(label, RESET, full,
                arguments=(lambda t: t["actor"], lambda t: t["b"], lambda t: t["claw"],
                           flag))


def reset_cases(random_source):
    r = random_source
    # every combination of the pending flag, the pending queue and the death animation
    for pending in (False, True):
        for queue in (False, True):
            for death in (False, True):
                for flag in (0, 1):
                    yield reset_case(f"reset pending={pending} queue={queue} death={death} message={flag}", r,
                                     rand_values=(r.randrange(0, 1 << 32),), pending=pending, pending_queue=queue,
                                     death=death, flag=flag, pending_anim=pending)
    # the bit set grows or sets in place
    for bits in (0, 1, 2, 31, 32, 33, 64, 65, 200):
        yield reset_case(f"bit set of {bits} bits", r, bitset=bits)
    for t20 in (0, 1, 2, 100):
        yield reset_case(f"slot level {t20}", r, t20=t20)
    # the new state field: equal to 0x2134 or not
    for a64 in (0x2134, 0x2133, 0x2135, 0, 0xFFFFFFFF):
        yield reset_case(f"state {a64:#x}", r, a64=a64)
    # states of the shared weapon register
    for current in (0, 0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC, 0x26BD, 0x26BE, 0x1234):
        for counter in (0, 0xF3E58, 0xF3E59, 0xFFFFFFF0):
            if counter and current not in (0, 0x26B7, 0x26BC):
                continue
            yield reset_case(f"register {current:#x} counter {counter:#x}", r, current=current, counter=counter)
        yield reset_case(f"register {current:#x} without listener", r, current=current, cursor=False)
    # an animation of every mode on the death frame
    for mode in (0, 1, 2, 3, 4):
        for flags in (0, 4, 8, 0x40):
            yield reset_case(f"death animation mode {mode} flags {flags:#x}", r, falldeath_mode=mode,
                             falldeath_flags=flags if flags in (0, 8) else 0, pending=bool(flags & 8))
    # one-bucket map so every key collides
    yield reset_case("one bucket collisions", r, buckets=1)
    yield reset_case("many buckets", r, buckets=61)
    # game object with the lookup branch live but nothing found
    for pause in (0, 1):
        yield reset_case(f"game flag set pause {pause}", r, game_flag=1, pause=pause, current=0x26B8)
        yield reset_case(f"game flag set pause {pause} again", r, game_flag=1, pause=pause)
    # state result of the vtable
    for result in (0, 3, 4, 5, 0xFFFFFFFF):
        yield reset_case(f"e state {result:#x}", r, vtable_result=result, flag=1, rand_values=(7,))
    # every random message index
    for value in list(range(0, 27)) + [0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFE6]:
        yield reset_case(f"random {value:#x}", r, flag=1, rand_values=(value,))
    # sensitivity of the locale branch of string compare (_lock/_unlock events)
    for e00 in (1,):
        for buckets in (1, 3):
            yield reset_case(f"locale compare buckets {buckets}", r, e00=e00, buckets=buckets)
    for _ in range(30):
        yield reset_case("random reset", r,
                         pending=bool(r.getrandbits(1)), pending_queue=bool(r.getrandbits(1)),
                         death=bool(r.getrandbits(1)), flag=r.getrandbits(1),
                         current=r.choice((0, 0x26B7, 0x26BC, 0x26BD, 0x26B8, 0x1111)),
                         counter=r.choice((0, 5, 0xF3E58, 0xF3E59)),
                         buckets=r.randrange(1, 40), flags_bits=r.getrandbits(32),
                         falldeath_mode=r.randrange(0, 4),
                         rand_values=(r.randrange(0, 1 << 32),), vtable_result=r.choice((4, 4, 3)),
                         a64=r.choice((0x2134, r.getrandbits(32))), bitset=r.choice((None, 0, 3, 40)))


# ---------------------------------------------------------------- 0x41cc60

def ranged_world(random_source, *, ammo, direction, sword="found", list_shape="empty", buckets=3,
                 bullet_found=True, mask_bit=None, sword_on=0, e00=0, fail_alloc=False):
    def setup(env):
        r = random_source
        env.put(G_E00, e00)
        if e00:
            env.write(G_CTYPE, bytes(0x102))
        env.put(G_CURRENT, ammo)
        env.put(G_SWORD_ON, sword_on)
        env.put(G_SWORD_ARG, word(r))

        player = env.object(0x400, "player", fill=0)
        env.write(player, bytes(r.getrandbits(8) for _ in range(0x400)))
        base_x = r.randrange(100, 100000)
        env.put(player + 0x4C, base_x)
        env.put(player + 0x50, r.randrange(100, 100000))
        env.put(player + 0x64, r.randrange(1, 5000))

        scene = env.object(0x40, "scene", fill=0)
        env.put(player + 0x0C, scene)
        manager = env.object(0x80, "manager", fill=0)
        env.put(scene + 0x08, manager)
        sword_res = env.object(0x80, "sword-resources", fill=0)
        env.put(scene + 0x28, sword_res)
        middle = env.object(0x40, "middle", fill=0)
        env.put(manager + 0x0C, middle)
        tables = env.object(0x80, "tables", fill=0)
        env.put(middle + 0x14, tables)

        blueprints = {}
        entries = []
        for code, name in BULLET_NAMES.items():
            blueprint = env.object(0x40, "blueprint", fill=0)
            env.put(blueprint + 0x08, r.getrandbits(32))
            env.put(blueprint + 0x10, word(r))
            env.put(blueprint + 0x14, word(r))
            blueprints[code] = blueprint
            if bullet_found or code != ammo:
                entries.append((name, blueprint))
        decoys = [(b"FireBullet2", word(r)), (b"fireBullet", word(r)), (b"Bullet", word(r))]
        build_map(env, tables + 0x10, entries, buckets, r, decoys=decoys)

        # scene list at manager+0x10 (head +0x14, tail +0x18, count +0x1c, free +0x20, blocks +0x24, size +0x28)
        def make_data(z, flags):
            data = env.object(0x80, "data", fill=0)
            env.write(data, bytes(r.getrandbits(8) for _ in range(0x80)))
            env.put(data + 0x64, z)
            env.put(data + 0x08, flags)
            return data

        new_z = env.get(player + 0x64) + 1
        shapes = {
            "empty": [],
            "all_lower": [(new_z - 1, 0), (new_z, 0)],
            "one_higher": [(new_z - 1, 0), (new_z + 1, 0), (new_z + 5, 0)],
            "flagged_then_higher": [(new_z + 3, 0x200), (new_z + 7, 0x200 | 1), (new_z + 2, 0)],
            "first_higher": [(new_z + 10, 0)],
            "flagged_all": [(new_z + 4, 0x200), (new_z + 9, 0x2200)],
        }
        nodes = []
        for z, flags in shapes[list_shape]:
            data = make_data(z, flags | (r.getrandbits(8) << 16))
            node = env.object(12, "node", fill=0)
            env.put(node + 8, data)
            nodes.append(node)
        for index, node in enumerate(nodes):
            env.put(node, nodes[index + 1] if index + 1 < len(nodes) else 0)
            env.put(node + 4, nodes[index - 1] if index else 0)
        if nodes:
            env.put(manager + 0x14, nodes[0], nodes[-1], len(nodes))
        env.put(manager + 0x28, r.randrange(2, 7))

        # sword animation map
        flag_value = 0 if sword != "skip" else word(r)
        env.put(sword_res + 0x30, flag_value)
        sword_entries = []
        sword_values = {}
        for code, name in SWORD_NAMES.items():
            value = env.object(0x40, "sword-anim", fill=0)
            inner = env.object(0x40, "inner", fill=0)
            mid = env.object(0x100, "mid", fill=0)
            env.put(value + 0x10, inner)
            env.put(inner + 0x10, mid)
            env.put(mid + 0x78, 0)
            sword_values[code] = value
            if sword == "found" or code != ammo:
                sword_entries.append((name, value))
        build_map(env, sword_res + 0x10, sword_entries, buckets,
                  r, decoys=[(b"CLAW_FIRESWORD2", word(r)), (b"CLAW_SWORD", word(r))])

        info = env.object(0x100, "info", fill=0)
        env.write(info, bytes(r.getrandbits(8) for _ in range(0x100)))
        env.put(info, direction)
        env.put(info + 0x54, r.randrange(1, 4000))
        env.put(info + 0x58, r.randrange(1, 4000) if r.getrandbits(1) else (-r.randrange(1, 4000)) & 0xFFFFFFFF)
        env.put(info + 0xE8, word(r))
        if mask_bit is not None:
            # choose the player x so that the bullet x has bit 0x200000 set (True) or clear (False)
            step = env.get(info + 0x54)
            step = step if direction else (-step) & 0xFFFFFFFF
            target = (0x200000 | r.randrange(0, 0x1FFFFF)) if mask_bit else r.randrange(0, 0x1FFFFF)
            env.put(player + 0x4C, (target - step) & 0xFFFFFFFF)
        return {"player": player, "info": info}
    return setup


def ranged_case(label, random_source, **options):
    sub = random.Random(random_source.getrandbits(64))
    return Case(label, RANGED, ranged_world(sub, **options),
                arguments=(lambda t: t["player"], sub.getrandbits(32), lambda t: t["info"]))


def ranged_cases(random_source):
    r = random_source
    shapes = ("empty", "all_lower", "one_higher", "flagged_then_higher", "first_higher", "flagged_all")
    for ammo in (FIREBALL, LIGHTNING, ICE):
        for direction in (0, 1, 0xFFFFFFFF, 5):
            for sword in ("found", "missing", "skip"):
                yield ranged_case(f"ammo {ammo:#x} direction {direction:#x} sword {sword}", r, ammo=ammo,
                                  direction=direction, sword=sword, list_shape=r.choice(shapes))
        for shape in shapes:
            yield ranged_case(f"ammo {ammo:#x} list {shape}", r, ammo=ammo, direction=r.getrandbits(1),
                              list_shape=shape)
        for buckets in (1, 2, 17):
            yield ranged_case(f"ammo {ammo:#x} buckets {buckets}", r, ammo=ammo, direction=1, buckets=buckets)
        for sword_on in (0, 1):
            yield ranged_case(f"ammo {ammo:#x} sword service {sword_on}", r, ammo=ammo, direction=0,
                              sword_on=sword_on)
        for bit in (False, True):
            yield ranged_case(f"ammo {ammo:#x} x bit21 {bit}", r, ammo=ammo, direction=r.getrandbits(1) , mask_bit=bit,
                              list_shape=r.choice(shapes))
        yield ranged_case(f"ammo {ammo:#x} locale compare", r, ammo=ammo, direction=1, e00=1, buckets=1)
        yield ranged_case(f"ammo {ammo:#x} locale compare sword skipped", r, ammo=ammo, direction=0, e00=1,
                          sword="skip", buckets=2)
    for _ in range(40):
        yield ranged_case("random ranged", r, ammo=r.choice((FIREBALL, LIGHTNING, ICE)),
                          direction=r.choice((0, 1, r.getrandbits(32))),
                          sword=r.choice(("found", "missing", "skip")), list_shape=r.choice(shapes),
                          buckets=r.randrange(1, 30), sword_on=r.getrandbits(1))
    # no ranged weapon selected: nothing is created, result is 0
    for current in (0, 0x26B7, 0x26BB, 0x26BC, 0x26BD, 0xFFFFFFFF):
        for direction in (0, 1):
            yield ranged_case(f"no ranged weapon {current:#x} direction {direction}", r, ammo=current,
                              direction=direction)


def cases(random_source):
    yield from reset_cases(random_source)
    yield from ranged_cases(random_source)
