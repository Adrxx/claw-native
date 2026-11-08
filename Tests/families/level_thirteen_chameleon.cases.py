"""Original-only cases for the Level 13 chameleon's state transitions."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence

RAND = 0x4A3050


def base(env, *, now=10000, alpha=93, linked=2, flags=0xA531, direction=2,
         state=9, elapsed=100, delay=100, randoms=(95, 617), mutate=False):
    actor = env.object(0x490, 'chameleon', fill=0x35)
    sprite = env.object(0x220, 'sprite', fill=0)
    world = env.object(0x220, 'world', fill=0)
    status = env.object(0x180, 'status', fill=0)
    player = env.object(0x140, 'player', fill=0)
    palette = env.object(0x40, 'palette', fill=0x69)
    link = env.object(0x40, 'link', fill=0x47)
    log = env.object(0x100, 'callback observations', fill=0)
    vtable = env.object(0x50, 'virtual methods', fill=0)
    env.put(actor, vtable)
    env.put(actor + 0xC, world, status)
    env.put(actor + 0x12C, sprite)
    env.put(actor + 0x18C, direction)
    env.put(actor + 0x184, state)
    env.put(actor + 0x138, -31, 17, 57, 23)
    env.put(actor + 0x2FC, 9, 0)
    env.put(actor + 0x30C, 0, 0)
    env.put(actor + 0x344, 0)
    env.put(actor + 0x34C, 0)
    env.put(actor + 0x458, 0)
    env.put(actor + 0x45C, now - elapsed, delay, now - elapsed, delay,
            now - elapsed, delay, now - elapsed, delay,
            link if linked else 0, alpha)
    env.put(sprite + 8, flags & ~0x10)
    env.put(sprite + 0x40, flags)
    env.put(sprite + 0x118, -11, 13, 19, 29, -37, 41, 43, 47, -53, 59, 61)
    env.put(sprite + 0x190, 0)
    env.put(link + 0x30, palette if linked == 2 else 0)
    env.put(status + 0x1C, 0x27)
    env.put(world + 0x170, 0)
    env.put(0x537E88, player)
    env.put(player + 0x4C, 100)
    env.put(player + 0x118, 20)
    env.put(player + 0x120, 40)
    env.put(0x537210, now)
    env.put(0x534EF0, 0xBADC0FFE)
    env.put(0x537680, 0)  # empty state-name trie
    env.put(0x532C0C, 0)
    env.put(0x52F01C, 1)
    env.override(RAND, sequence(*randoms))

    def observe(e, call):
        count = e.get(log)
        at = log + 4 + count * 0x40
        e.put(at, call.receiver, len(call.arguments), e.get(actor + 0x480),
              e.get(sprite + 0x40), e.get(actor + 0x46C), e.get(actor + 0x470),
              e.get(actor + 0x474), e.get(palette + 0x18))
        e.put(log, count + 1)
        if mutate:
            e.put(actor + 0x480, 0x1234)
        return 0x87654321

    callback = env.stub('state callback', 'thiscall', 0, observe)
    env.put(vtable + 0x44, callback, callback)
    return dict(actor=actor, sprite=sprite, world=world, status=status,
                player=player, palette=palette, link=link, callback=callback, log=log)


def transition(address, label, **options):
    return Case(label, address, lambda env: base(env, **options),
                receiver=lambda t: t['actor'])


def cases(random_source):
    # Deterministic branch and threshold grid remains complete on every gate seed.
    for address in (0x422050, 0x4221B0):
        for linked in (0, 1, 2):
            for alpha in (-11, -1, 0, 9, 10, 245, 246, 255, 256):
                for elapsed in (4, 5):
                    yield transition(address, f'{address:x} link {linked} alpha {alpha} elapsed {elapsed}',
                                     alpha=alpha, linked=linked, elapsed=elapsed, delay=5)
    for elapsed, delay in ((0, 0), (0, 1), (0xFFFFFFFF, 0x80000000), (1, 0xFFFFFFFF)):
        for address in (0x421F80, 0x422050, 0x4221B0):
            yield transition(address, f'{address:x} unsigned elapsed {elapsed} delay {delay}',
                             now=0, elapsed=elapsed, delay=delay)
    for direction in (1, 2, 3):
        for flags in (0xA531, 0xA533):
            for state, randoms in ((0, (65,)), (0, (66,)), (1, (100,)),
                                   (2, (39, 500)), (2, (40,)), (3, (79,)),
                                   (4, (80,)), (5, (2,)), (6, (3,)), (9, (95,))):
                yield transition(0x421E00, f'decision direction {direction} flags {flags} state {state} rand {randoms}',
                                 direction=direction, flags=flags, state=state, randoms=randoms)
    for elapsed in (99, 100):
        yield transition(0x421E00, f'strike cooldown {elapsed}', state=2,
                         randoms=(0, 501), elapsed=elapsed, delay=100)
    for linked in (0, 1, 2):
        for elapsed in (99, 100):
            yield transition(0x421F80, f'phase out cooldown {elapsed} link {linked}',
                             linked=linked, elapsed=elapsed, delay=100, mutate=True)
    for low, high in ((-100.75, 100.25), (20.0, 19.0), (120.0, 120.0),
                      (140.0, 140.0), (141.0, 141.0)):
        for rand in (0, 1, 32767):
            def phasein(env, low=low, high=high, rand=rand):
                t = base(env, randoms=(rand, 1500 + rand))
                env.write(t['actor'] + 0x80, struct.pack('<d', low))
                env.write(t['actor'] + 0x98, struct.pack('<d', high))
                return t
            yield Case(f'phase in range {low}:{high} rand {rand}', 0x4220E0,
                       phasein, receiver=lambda t: t['actor'])
    for rand in (0, 2, 3, 99, 100, 102, 0xFFFFFFFF):
        yield transition(0x421D70, f'home rand {rand}', randoms=(rand,))
    for _ in range(24):
        address = random_source.choice((0x422050, 0x4221B0, 0x421F80))
        yield transition(address, f'random transition {_}', alpha=random_source.randrange(-30, 290),
                         now=random_source.randrange(0x100000000), linked=random_source.randrange(3),
                         elapsed=random_source.randrange(1000), delay=random_source.randrange(1000),
                         flags=random_source.randrange(0x100000000))
    for address in (0x421D70, 0x421E00):
        for sound in (0, 1, 2):
            def sounds(env, sound=sound):
                t = base(env, state=5, randoms=(2,))
                resource = env.object(0x20, 'sound resource', fill=0)
                voice = env.object(0x20, 'voice', fill=0)
                manager = env.object(0x80, 'sound manager', fill=0)
                env.put(resource + 0x10, voice)
                env.put(voice + 0x10, manager)
                env.put(t['actor'] + 0x458, resource if sound else 0)
                env.put(0x532C0C, int(sound == 2))
                return t
            yield Case(f'sound branch {address:x} {sound}', address, sounds, receiver=lambda t:t['actor'])
    for address in (0x421D70, 0x421E00):
        for chance in (0, 2, 3, 4, 99, 100, 0xFFFFFFFF):
            for state in (5, 6):
                yield transition(address, f'sound absent threshold {address:x} chance {chance} state {state}',
                                 state=state, randoms=(chance,))
    for function in (0x421B80, 0x421B60):
        for flag in (0, 1, 2, 255):
            for count in (2, 3):
                def destroy(env, count=count):
                    t = base(env)
                    storage = env.object(20, 'string allocation', fill=0)
                    env.put(storage, count, 3, 7)
                    env.put(t['actor'] + 0x1A4, storage + 12, storage + 12)
                    env.put(t['actor'] + 0x2FC, 33 if count == 2 else 10)
                    if count == 2:
                        bits = env.object(8, 'long bitset', fill=0x5A)
                        env.put(t['actor'] + 0x300, bits)
                    env.put(0x544D18, 0)
                    def decrement(e, call):
                        pointer = call.arguments[0]
                        value = (e.get(pointer) - 1) & 0xFFFFFFFF
                        e.put(pointer, value)
                        return value
                    env.override(0x5469E8, decrement)
                    return t
                yield Case(f'destructor {function:x} flags {flag} refs {count}', function,
                           destroy, receiver=lambda t:t['actor'],
                           arguments=(flag,) if function == 0x421B60 else ())
    for phase in ('LS_PHASEOUT', 'LS_PHASEIN', 'LS_DEAD', 'LS_HOME'):
        for level, facing, active, state in ((13, 0, 0, 9), (14, 0, 0, 3), (14, 1, 1, 3),
                                              (14, 0, 1, 4), (14, 1, 1, 2)):
            for chance in (2, 3):
                def update(env, phase=phase, level=level, facing=facing, active=active, state=state, chance=chance):
                    t = base(env, state=state, randoms=(chance,))
                    text = env.object(len(phase)+1, 'current phase', data=phase.encode()+b'\0')
                    table = env.object(4, 'phase index', words=[text])
                    env.put(0x5376A0, 0x27, 0x27, table, table, 4, 0, 0)
                    scratch = env.object(12, 'temporary string slots', fill=0)
                    if level == 13:
                        env.put(0x5376A0, 0x26, 0x26)
                    else:
                        env.put(0x5376B4, scratch if phase != 'LS_DEAD' else 0, 2 if phase != 'LS_DEAD' else 1)
                    env.put(0x537964, level)
                    env.put(0x534EAC, 0x26B7)
                    env.put(0x541334, 1)
                    owner = env.object(0x180, 'carrying object', fill=0)
                    ownerstate = env.object(0x20, 'carrying state', fill=0)
                    env.put(owner + 0x164, 0x8000)
                    env.put(owner + 0x6C, ownerstate)
                    env.put(ownerstate + 0x1C, 5)
                    env.put(t['sprite'] + 8, 0x10)
                    env.put(t['sprite'] + 0x80, owner)
                    controls = env.object(8, 'player controls', words=[facing, active])
                    playerlogic = env.object(0x20, 'player logic', fill=0)
                    env.put(t['player']+0x6C, playerlogic)
                    env.put(playerlogic+0x14, controls)
                    env.write(t['actor']+0x68, struct.pack('<d', 101.0 if facing else 99.0))
                    if phase == 'LS_HOME' and level == 13:
                        table = env.object(12, 'aliased status phase table', words=[text]*3)
                        env.put(0x5376A0, -3, -1, table, table, 4, 0, -7)
                        env.put(t['actor'] + 0x10, 0x53769C)
                    return t
                yield Case(f'update phase {phase} level {level} facing {facing} active {active} state {state} rand {chance}',
                           0x421BF0, update, receiver=lambda t:t['actor'], arguments=(0x5234EC,))
    for index in (-2, 0, 2, 4):
        for fallback in (False, True):
            def dispatch(env, index=index, fallback=fallback):
                t = base(env)
                table = env.object(12, 'dispatch table', words=[t['callback']] * 3)
                backup = env.object(36, 'base dispatch table', words=[t['callback']] * 9)
                env.put(0x534ED8, 0, 2, table, table, 4)
                env.put(0x537880, -4, 4, backup, backup, 4)
                if fallback and 0 <= index <= 2:
                    env.put(table + index*4, 0)
                return t
            yield Case(f'dispatch {index} fallback {fallback}', 0x421320, dispatch,
                       receiver=lambda t:t['actor'], arguments=(index,))
    for bounds in ((900, 902), (902, 904), (901, 900)):
        def outimage(env, bounds=bounds):
            t = base(env)
            image = env.object(0x70, 'out image', fill=0)
            frames = env.object(0xE28, 'out frames', fill=0)
            env.put(image + 0x14, frames)
            env.put(image + 0x64, *bounds)
            env.put(frames + 0xE14, t['palette'])
            env.put(t['world'] + 0x170, image)
            return t
        yield Case(f'phase out image bounds {bounds}', 0x421F80, outimage, receiver=lambda t:t['actor'])
    for bitsize in (9, 33):
        def changed_bits(env, bitsize=bitsize):
            t = constructor(env, True, (900, 902))
            bits = env.object(8, 'extended bitset', fill=0x67)
            def rectangle(e, call):
                pointer, left, top, right, bottom = call.arguments
                e.put(pointer, left, top, right, bottom)
                count = e.get(t['log'])
                e.put(t['log'] + 4 + count*20, pointer, left, top, right, bottom)
                e.put(t['log'], count + 1)
                if pointer == t['actor'] + 0x220:
                    e.put(t['actor'] + 0x2FC, bitsize, bits)
                return 1
            env.override(0x546D5C, rectangle)
            return t
        yield Case(f'constructor bitset changed by SetRect {bitsize}', 0x421710,
                   changed_bits, receiver=lambda t:t['actor'], arguments=(lambda t:t['sprite'],))
    for rich in (False, True):
        for imagebounds in ((900, 902), (902, 904), (901, 900)):
            yield Case(f'constructor resources {rich} imagebounds {imagebounds}', 0x421710,
                       lambda env, rich=rich, imagebounds=imagebounds: constructor(env, rich, imagebounds),
                       receiver=lambda t:t['actor'], arguments=(lambda t:t['sprite'],))


def constructor(env, rich, bounds):
    t = base(env)
    sprite, status = t['sprite'], t['status']
    resources = env.object(0x40, 'resource containers', fill=0)
    env.put(sprite + 0xC, resources)
    env.put(sprite + 0x6C, status)
    env.put(sprite + 0x4C, 128, 512)
    env.write(0x5262B0, struct.pack('<f', 1.25))
    env.write(0x5262B4, struct.pack('<f', 0.75))
    env.put(sprite + 0x104, 0x2468)
    env.put(sprite + 0x118, 0x80000000)
    collision = env.object(0x80, 'collision manager', fill=0)
    env.put(resources + 0x24, collision)
    env.put(status + 0x2C, 120, 140, 3, 7)
    animation = env.object(0x20, 'animation resource', fill=0)
    action = env.object(0x30, 'animation action', fill=0)
    actions = env.object(4, 'action list', words=[action])
    env.put(animation + 0xC, actions, 1)
    env.put(action + 0x1C, 0x27)
    image = env.object(0x70, 'chameleon image', fill=0)
    frames = env.object(0xE28, 'chameleon frames', fill=0)
    frame = env.object(0x40, 'image frame', fill=0)
    env.put(image + 0x14, frames)
    env.put(image + 0x64, *bounds)
    for index in range(900, 905):
        env.put(frames + index*4, frame)
    env.put(frame + 0x18, -3, -7, 31, 41)
    env.put(frame + 0x30, t['palette'])
    env.put(frames + 0xE14, frame)
    root = env.object(0x30, 'root manager', fill=0)
    stage = env.object(0x780, 'stage', fill=0)
    env.put(0x5371FC, root)
    env.put(root + 0x2C, stage)
    env.put(stage + 0x770, 0x12345678)

    def mapping(items, name):
        obj = env.object(0x30, name, fill=0)
        bucket = env.object(4, name + ' bucket', fill=0)
        head = 0
        for key, value in items:
            text = env.object(len(key)+1, key, data=key.encode()+b'\0')
            node = env.object(16, name + ' node', words=[head, 0, text, value])
            head = node
        env.put(bucket, head)
        env.put(obj + 0x14, bucket, 1)
        return obj

    names = ('IDLE', 'FASTADVANCE', 'HIT', 'JUMP', 'KILLFALL', 'STRIKE1')
    animitems = [('LEVEL_CHAMELEON_' + name, animation) for name in names] if rich else []
    animitems.append(('GAME_NULL', animation))
    # Each resource has a distinct identity so swapped assignment slots differ.
    distinct = []
    for key, value in animitems:
        own = env.object(0x20, 'animation ' + key, fill=0)
        env.put(own + 0xC, actions, 1)
        distinct.append((key, own))
    animitems = distinct
    env.put(resources + 0x2C, mapping(animitems, 'animations'))
    env.put(resources + 0x10, mapping([('LEVEL_CHAMELEON', image)] if rich else [], 'images'))
    env.put(resources + 0x14, mapping([], 'logic hit'))
    env.put(resources + 0x18, mapping([], 'logic attack'))
    env.put(resources + 0x28, mapping([], 'sounds'))
    env.put(0x544D18, 0)
    return t

