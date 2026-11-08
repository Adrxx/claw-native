"""Original actor initialization, signed health arithmetic and physical fills."""
from clawparity.cases import Case

METER = 0x491FA0
FILL = 0x4B9830


def scene(state=5, health=37, initial=100, depth=8, boss=True,
          image=True, surface=True, camera=True, image_id=19,
          lookup=True, mutate=False, error=0, beep=False, shifts=(11, 5, 3, 2, 3),
          geometry=(103, -41, 744, 513), position=(-29, 63), salt=0x79):
    def setup(env):
        actor = env.object(0x178, 'meter', fill=salt)
        record = env.object(0x20, 'actor record', fill=salt ^ 0x39)
        app = env.object(0x80, 'application', fill=salt ^ 0x72)
        target = env.object(0xBC, 'surface', fill=salt ^ 0xA4)
        interface = env.object(4, 'DirectDraw surface')
        methods = env.object(0x18, 'physical vtable')
        img = env.object(0x30, 'image', fill=salt ^ 0x14)
        enemy = env.object(0x110, 'boss', fill=salt ^ 0x31)
        log = env.object(0x800, 'fill observations', fill=0)
        rect = env.object(16, 'direct rectangle', words=geometry)
        env.put(actor + 8, 0x8415, 0)
        env.put(actor + 0x64, image_id)
        env.put(actor + 0x6C, record)
        env.put(actor + 0x10C, initial & 0xFFFFFFFF)
        env.put(actor + 0x174, img if image else 0)
        env.put(record + 0x1C, state)
        env.put(enemy + 0x10C, health & 0xFFFFFFFF)
        env.put(img + 0x20, position[0] & 0xFFFFFFFF, position[1] & 0xFFFFFFFF)
        env.put(img + 0x2C, target if surface else 0)
        env.put(app + 0x78, depth)
        env.put(app + 0x30, 0)
        if camera:
            cam = env.object(0x28, 'camera')
            bounds = env.object(0x20, 'camera bounds')
            env.put(app + 0x30, cam)
            env.put(cam + 0x24, bounds)
            env.put(bounds + 0x10, *(v & 0xFFFFFFFF for v in geometry))
        # A genuine original hash lookup, with a collision before GAME_BOSSBAR.
        world = env.object(0x14, 'world')
        manager = env.object(0x20, 'image manager')
        buckets = env.object(4, 'hash buckets')
        collision = env.object(16, 'collision')
        node = env.object(16, 'bossbar node')
        wrong = env.object(8, 'other key', data=b'OTHER\0')
        name = env.object(16, 'bossbar key', data=b'GAME_BOSSBAR\0')
        animation = env.object(0x6C, 'animation')
        frames = env.object(16, 'animation images')
        env.put(actor + 0xC, world)
        env.put(world + 0x10, manager)
        env.put(manager + 0x14, buckets, 1)
        env.put(buckets, collision if lookup else 0)
        env.put(collision, node, 0, wrong, 0)
        env.put(node, 0, 0, name, animation)
        env.put(animation + 0x14, frames)
        env.put(animation + 0x64, 2, 3)
        env.put(frames + 8, img)
        env.put(0x5371FC, app)
        env.put(0x5349DC, enemy if boss else 0)
        env.put(0x52C6F0, 0xE7A9132B, 0x39B6C841)
        for address, value in zip((0x54135C, 0x541360, 0x541368, 0x54136C, 0x541370), shifts):
            env.put(address, value)
        env.put(0x54139C, 0, 0, int(beep), 0)

        def set_rect(env, call):
            env.put(call.arguments[0], *call.arguments[1:])
            return 1

        def blt(env, call):
            count = env.get(log)
            at = log + 4 + count * 160
            env.put(log, count + 1)
            env.put(at, call.receiver, *call.arguments)
            env.write(at + 32, env.read(call.arguments[1], 16))
            env.write(at + 48, env.read(call.arguments[5], 100))
            env.put(at + 148, env.get(actor + 0x4C), env.get(actor + 0x50), env.get(record + 0x1C))
            if mutate and count == 0:
                env.put(call.arguments[1], 17, 23, 418, 31)
                env.put(0x52C6F0, 0x4A71B26C)
            return error

        def sound(env, call):
            env.put(log + 0x700, env.get(log + 0x700) + 1, *call.arguments)
            return 1

        env.put(target + 8, interface)
        env.put(interface, methods)
        env.put(methods + 0x14, env.stub('IDirectDrawSurface::Blt', 'stdcall', 6, blt))
        env.override(0x546D5C, set_rect)
        env.override(0x546CA4, sound)
        return dict(actor=actor, surface=target, rect=rect)
    return setup


def meter(label, **options):
    return Case(label, METER, scene(**options), arguments=(lambda t: t['actor'],))


def cases(random_source):
    for depth in (8, 16, 24, 0, 32):
        for present in (False, True):
            yield meter(f'initialize depth {depth} boss {present}', state=0, depth=depth,
                        boss=present, image_id=0x2704 if present else 23,
                        camera=present, lookup=present)
    yield meter('16 bit shifts use masked low five bits', state=0, depth=16,
                shifts=(43, 37, 35, 34, 35))
    for state in (1, 4, 6, 0xFFFFFFFF):
        yield meter(f'idle state {state}', state=state)
    yield meter('boss removed', boss=False)
    yield meter('no image', image=False)
    yield meter('no surface', surface=False)
    for health, initial in ((0,100), (1,100), (99,100), (100,100), (101,100),
                            (-1,100), (-100,-100), (50,-100), (-50,-100),
                            (1,3), (2,3), (0,0), (1,0), (-1,0),
                            (0x7FFFFFFF,0x7FFFFFFF), (-0x80000000,0x7FFFFFFF),
                            (0x7FFFFFFF,-0x80000000)):
        yield meter(f'health {health} initial {initial}', health=health, initial=initial)
    yield meter('partial draw rereads mutated rectangle and foreground', mutate=True)
    yield meter('negative camera width truncates toward zero', geometry=(11,21,-8,45))
    yield meter('default camera rectangle', camera=False)
    for index in range(24):
        health = random_source.randrange(-20000, 20000)
        initial = random_source.choice((-1, 1)) * random_source.randrange(1, 20000)
        yield meter(f'random signed ratio {index}', health=health, initial=initial,
                    position=(random_source.randrange(-500,500), random_source.randrange(-500,500)),
                    salt=random_source.randrange(1,256))
    yield Case('direct null rectangle', FILL, scene(), receiver=lambda t:t['surface'], arguments=(0,0x81234567))
    for error in (0, 0x80004005, 0x88760032):
        yield Case(f'direct fill status {error:#x}', FILL, scene(error=error, beep=bool(error)),
                   receiver=lambda t:t['surface'], arguments=(lambda t:t['rect'],0xA792361B))
