"""Attack setup inputs derived from the pinned v1.3 packet."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

ATTACK = 0x41F270
RAND = 0x4A595B
LOOKUP = 0x4FC6B4
NEW = 0x4FCAEA


def attack_case(label, attack, *, facing=1, longrange=0, power=0, easy=0,
                roids=0, wimp=0, cheat_easy=0, ammo=1, rng=99,
                bounds=(23, -41, 137, 67), held=None, candidate=None,
                map_fail=False, mutation=None, salt=0, sound=True):
    def setup(env):
        # Padding remains distinctive so wrong writes and word widths survive.
        obj = env.object(0x240, 'Claw', fill=0xA6)
        state = env.object(0x180, 'attack-state', fill=0x5D)
        context = env.object(0x80, 'attack-context', fill=0x39)
        owner = env.object(0x60, 'owner', fill=0)
        world = env.object(0x30, 'world-list', fill=0)
        resources = env.object(0x40, 'animation-resource-map', fill=0x71)
        control = env.object(0x40, 'controls', fill=0xD3)
        env.put(obj + 0xC, owner)
        env.put(owner + 8, world)
        env.put(owner + 0x2C, resources)
        env.put(obj + 0x5C, 500, 300)
        env.put(obj + 0x74, 12)
        env.put(obj + 0xE4, 2)
        env.put(obj + 0x120, 73 + salt)
        env.put(obj + 0x134, 11, 22, 33, 44)
        env.put(obj + 0x144, -20, -30, 20, 30)
        env.put(obj + 0x154, *bounds)
        env.put(state, facing)
        env.put(state + 0x70, *(ammo if isinstance(ammo, tuple) else (ammo, ammo, ammo)))
        env.put(state + 0xE8, 0xFFFFFFFE + (salt & 1))
        env.put(state + 0x12C, 0)
        env.put(0x535918, control)
        env.put(0x532D34, power)
        for address, value in ((0x535930, roids), (0x535940, wimp),
                               (0x53594C, longrange), (0x535950, cheat_easy),
                               (0x535990, easy)):
            env.put(address, value)
        sound_map = env.object(0x40, 'sound-resource-map', fill=0x67)
        sound_logic = env.object(0x40, 'sound-logic', fill=0x17)
        sound_resource = env.object(0x40, 'sound-resource', fill=0x47)
        env.put(owner + 0x28, sound_map)
        env.put(obj + 0x7C, sound_logic)
        env.put(0x53B0DC, obj if sound else 0)
        env.put(0x53B0D8, 0)
        env.put(0x5365D4, 0)

        def resource(name, ordinal):
            animation = env.object(0x30, name, fill=0x83)
            frame = env.object(0x24, name + '-frame', fill=0x95)
            frames = env.object(4, name + '-frames', words=[frame])
            env.put(animation + 0xC, frames, 1)
            env.put(animation + 0x20, 0x3F800000 + ordinal * 0x8000)
            env.put(frame + 0x1C, 29 + ordinal * 17)
            return animation

        prior = resource('prior-animation', 0)
        env.put(obj + 0x1B4, prior)
        names = ('CLAW_SWIPE', 'CLAW_POWERUPSWIPE', 'CLAW_PUNCH',
                 'CLAW_UPPERCUT', 'CLAW_EMPTYPISTOL', 'CLAW_PISTOL',
                 'CLAW_EMPTYMAGIC', 'CLAW_MAGIC', 'CLAW_DUCKSWIPE',
                 'CLAW_DUCKPOWERUPSWIPE', 'CLAW_JUMPSWIPE',
                 'CLAW_JUMPPOWERUPSWIPE', 'CLAW_EMPTYJUMPPISTOL',
                 'CLAW_JUMPPISTOL', 'CLAW_EMPTYJUMPMAGIC', 'CLAW_JUMPMAGIC',
                 'CLAW_EMPTYDYNAMITE', 'CLAW_PREDYNAMITE', 'CLAW_POSTDYNAMITE',
                 'CLAW_KICK', 'CLAW_DUCKEMPTYPISTOL', 'CLAW_DUCKPISTOL',
                 'CLAW_DUCKEMPTYMAGIC', 'CLAW_DUCKMAGIC',
                 'CLAW_DUCKEMPTYDYNAMITE', 'CLAW_DUCKPREDYNAMITE',
                 'CLAW_DUCKPOSTDYNAMITE', 'CLAW_EMPTYJUMPDYNAMITE',
                 'CLAW_JUMPDYNAMITE', 'CLAW_LIFT', 'CLAW_DUCKLIFT')
        animations = {name: resource(name, i + 1) for i, name in enumerate(names)}

        def lookup(e, call):
            name = e.cstr(call.arguments[0])
            if isinstance(name, bytes):
                name = name.decode('ascii')
            # Native map misses leave the output pointer untouched. The original
            # owns initialization of its stack slot for the post-dynamite pointer.
            is_sound = call.receiver == sound_map + 0x10
            value = sound_resource if is_sound else animations.get(name, prior)
            if not map_fail:
                e.put(call.arguments[1], value)
            if mutation:
                for target, offset, value in mutation:
                    address = {'obj': obj, 'state': state, 'global': 0}[target] + offset
                    e.put(address, value)
            return 0 if map_fail else 1

        env.override(LOOKUP, lookup)
        env.override(RAND, returns(rng))
        env.override(NEW, allocate())

        def logic_for(target, capacity, active=1):
            holder = env.object(0x30, 'held-link', fill=0x29)
            logic = env.object(0x380, 'held-logic', fill=0)
            env.put(target + 0x7C, holder)
            env.put(holder + 0x18, logic)
            env.put(logic + 0x10, target)
            env.put(logic + 0x2C, active)
            env.put(logic + 0x31C, 0, 0, capacity)
            if capacity <= 32:
                env.put(logic + 0x328, 0xFEA4D2B6)
            else:
                bits = env.object(32, 'held-bits', fill=0x6A)
                env.put(logic + 0x328, bits)
            return logic

        if held is not None:
            target = env.object(0x240, 'held-object', fill=0xC7)
            logic_for(target, held[0], held[1])
            env.put(state + 0x12C, target)
        if candidate is not None:
            distance, flags, dy, pose = candidate
            target = env.object(0x240, 'throw-candidate', fill=0)
            env.put(target + 0xE8, 4)
            env.put(target + 0x180, flags)
            # 0x41eb30 measures facing-specific box-to-box separation.
            x = 500 + (distance - 28 if facing else 28 - distance)
            env.put(target + 0x5C, x, 300 + dy)
            env.put(target + 0x144, 0, 0, 0, 0)
            env.put(target + 0x140, 44)
            env.put(obj + 0xE4, pose)
            node = env.object(12, 'candidate-list-node', words=[0, 0, target])
            env.put(world + 0x14, node)
            logic = logic_for(target, 32)
            log = env.object(32, 'lift-callback-observations', fill=0)
            vtable = env.object(0xA8, 'candidate-logic-methods', fill=0)
            def on_lift(e, call):
                e.put(log, call.receiver, e.get(state + 0x12C),
                      e.get(obj + 0xE4), e.get(target + 0x74),
                      e.get(logic + 0x328), e.get(state + 0xF0))
                e.put(logic + 0x38, 0x1234ABCD)
                return 0
            env.put(vtable + 0xA4, env.stub('candidate lift callback', 'thiscall', 0, on_lift))
            env.put(logic, vtable)
        return obj, context, state
    return Case(label, ATTACK, setup, arguments=(lambda t: t[0], lambda t: t[1],
                                                lambda t: t[2], attack))


def cases(random_source):
    # Every switch id, default hole, unsigned out-of-range id, facing and tail.
    for attack in (*range(19), -1, 0x80000000, 0x7FFFFFFF):
        for facing in (0, 1):
            for longrange in (0, 1):
                yield attack_case(f'id {attack} face {facing} range {longrange}', attack,
                                  facing=facing, longrange=longrange)
    for attack in (1, 3, 4, 7, 8, 13):
        for power in (0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BC, 0x26BD):
            for easy in (0, 1):
                yield attack_case(f'damage {attack} power {power} easy {easy}', attack,
                                  power=power, easy=easy, cheat_easy=1-easy)
    for attack in (0, 1, 5, 7, 8, 11, 12, 16, 18):
        for roids, wimp in ((0, 1), (1, 0), (1, 1), (0x80000000, 0xFFFFFFFF)):
            yield attack_case(f'cheats {attack} {roids} {wimp}', attack,
                              easy=1, roids=roids, wimp=wimp, longrange=0xFFFFFFFF,
                              facing=0)
    for attack in (5, 6, 9, 10, 12, 14, 15, 16, 18):
        for ammo in (-1, 0, 1, 0x7FFFFFFF, 0x80000000):
            yield attack_case(f'ammo {attack} {ammo}', attack, ammo=ammo)
    for attack, threshold in ((5, 30), (12, 25), (16, 35)):
        for rng in (0, threshold-1, threshold, threshold+1, 99, 100, 100+threshold):
            yield attack_case(f'rng {attack} {rng}', attack, rng=rng)
    for attack in (0, 2, 5, 6, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19):
        for facing in (0, 1):
            for left, right in ((0x80000000, 0x7FFFFFFF), (0x7FFFFFFF, 0xFFFFFF00),
                                (0, 0x80000000), (0xFFFFFFFF, 0xFFFFFEC0)):
                yield attack_case(f'stale {attack} {facing} {left} {right}', attack,
                                  facing=facing, longrange=1,
                                  bounds=(left, -17, right, 61))
    for capacity in (0, 1, 32, 33, 64):
        for active in (-1, 0, 1):
            yield attack_case(f'cancel held {capacity} active {active}', 0,
                              held=(capacity, active))
    for facing in (0, 1):
        for distance in (63, 64):
            for flags in (0, 1, 0x401):
                yield attack_case(f'throw {facing} distance {distance} flags {flags}', 11,
                                  facing=facing, candidate=(distance, flags, 0, 0))
    for facing in (0, 1):
        for flags in (1, 5, 0x401):
            for dy, pose in ((0, 2), (20, 1), (21, 2), (0, 3)):
                yield attack_case(f'lift {facing} flags {flags} dy {dy} pose {pose}', 11,
                                  facing=facing, candidate=(63, flags, dy, pose))
    for attack in (1, 7, 8, 12, 16):
        yield attack_case(f'missing resource {attack}', attack, map_fail=True)
        yield attack_case(f'lookup changes damage tail {attack}', attack,
                          mutation=(('global', 0x535930, 1), ('global', 0x535940, 1),
                                    ('global', 0x53594C, 1), ('state', 0, 0)))
    for i in range(24):
        yield attack_case(f'seeded bounds {i}', random_source.choice((0, 5, 6, 9, 10, 18)),
                          facing=random_source.choice((0, 1)), longrange=1,
                          bounds=tuple(random_source.getrandbits(32) for _ in range(4)),
                          salt=random_source.randrange(1000))

    # Independent neighboring inventory words expose reads from the wrong slot.
    for attack, slot in ((5, 0), (9, 0), (14, 0), (6, 1), (10, 1),
                         (15, 1), (12, 2), (16, 2), (18, 2)):
        for selected, neighbor in ((0, 7), (1, 0), (-1, 11),
                                   (0x80000000, 5), (0x7FFFFFFF, -1), (1, 0x80000000)):
            inventory = [neighbor, neighbor, neighbor]
            inventory[slot] = selected
            yield attack_case(f'independent inventory {attack} {selected} {neighbor}',
                              attack, ammo=tuple(inventory))
    # Both dynamite stances see the same random values around both limits.
    for attack in (12, 16):
        for rng in (24, 25, 29, 30, 34, 35):
            yield attack_case(f'dynamite shared roll {attack} {rng}', attack, rng=rng)
    for attack in (5, 12, 16):
        yield attack_case(f'sound unavailable {attack}', attack, rng=0, sound=False)
