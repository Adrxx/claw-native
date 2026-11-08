"""Raux callbacks exercised against the original with observable service effects."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_case(options):
    def setup(env):
        def dbl(address, value):
            env.write(address, struct.pack('<d', value))

        actor = env.object(0x500, 'raux', fill=0xA7)
        sprite = env.object(0x220, 'sprite', fill=0)
        world = env.object(0x180, 'world', fill=0)
        state = env.object(0x30, 'state', fill=0x51)
        table = env.object(0xA0, 'raux-methods', fill=0)
        receipt = env.object(0x180, 'callback-receipts', fill=0)
        env.put(actor, table)
        env.put(actor + 0x0c, world, state)
        env.put(actor + 0x128, sprite, sprite)
        env.put(actor + 0x138, 0xfffffff3, 0x10203040, 19, 0x50607080)
        env.put(actor + 0x184, options.get('mode', 7))
        env.put(actor + 0x18c, options.get('direction', 3))
        env.put(actor + 0x2e4, options.get('threshold', 40))
        env.put(actor + 0x2fc, 3, 4)
        env.put(actor + 0x3c4, options.get('speech', -1))
        env.put(actor + 0x470, options.get('start', 100), options.get('duration', 30))
        env.put(sprite + 8, 0x10203045)
        env.put(sprite + 0x40, options.get('flags', 0x12345680))
        for off, low, high in ((0x118, -7, 11), (0x128, -17, 23), (0x138, -29, 31)):
            env.put(sprite + off, low, 0xabcdef01, high, 0x76543210)
        env.put(sprite + 0x4c, 41, 8)
        env.put(sprite + 0x124, 2)
        env.put(sprite + 0x190, 0)
        env.put(sprite + 0x19c, options.get('delay', 0))
        env.put(sprite + 0x1a4, options.get('finished', 0))
        env.put(state + 0x1c, 0x1234)
        env.put(world + 0xcc, options.get('world_state', 0))
        env.put(0x537210, options.get('now', 130))
        env.put(0x5430c4, 3)
        env.put(0x541334, options.get('disabled', 0))
        env.put(0x53c9ac, 0)
        env.put(0x537668 + 0x18, 0)
        env.put(0x5376b8, 0)
        # Valid indexed name lookup; mismatch leaves the whole home helper early.
        name = env.object(8, 'state-name', data=options.get('name', b'LS_IDLE\0'))
        entry = env.object(4, 'state-name-entry', words=[name])
        env.put(0x537698 + 8, 0x1234, 0x1234, entry)
        env.put(0x537698 + 0x18, 4)
        env.override(0x4a3050, sequence(*options.get('random', (99, 99, 99, 99))))
        for off in (0x44, 0x48, 0x58, 0x64, 0x68, 0x90):
            def callback(e, call, offset=off):
                count = e.get(receipt)
                target = receipt + 4 + count * 32
                e.put(target, offset, call.receiver, e.get(actor + 0x20),
                      e.get(sprite + 8), e.get(world + 0xcc),
                      e.get(actor + 0x138), e.get(actor + 0x140))
                e.put(target + 28, call.arguments[0] if call.arguments else 0)
                e.put(receipt, count + 1)
                if options.get('callback_mutates'):
                    e.put(sprite + 0x1a4, options.get('next_finished', 1))
                    e.put(sprite + 0x19c, options.get('next_delay', 0))
                return 0xfedcba98
            env.put(table + off, env.stub('raux-method-%x' % off, 'thiscall', 1 if off == 0x90 else 0, callback))
        # Nonzero fields make wrong offsets and partial stores observable.
        for off, value in ((0x38, 0.0), (0x40, 1.0), (0x48, 0.0),
                           (0x50, 17.25123456789), (0x58, -9.5123456789), (0x60, 3.75123456789),
                           (0x68, 5.25), (0x70, 3.5), (0x78, 2.25),
                           (0x80, 0.0), (0x98, 60.0)):
            dbl(actor + off, options.get('d%x' % off, value))
        # All animation requests are valid one-frame sequences.
        frame = env.object(0x30, 'animation-frame', fill=0)
        frames = env.object(4, 'animation-frames', words=[frame])
        animation = env.object(0x20, 'animation', fill=0)
        env.put(animation + 0x0c, frames, 1)
        env.put(frame + 0x1c, 0x11223344)
        env.put(frame + 0x0c, 9)
        env.put(frame + 0x18, 5)
        if options.get('progress_animation'):
            env.put(sprite + 0x18c, sprite, animation, frame, 0)
            env.put(sprite + 0x1a8, 0x11223344, 0x55667788, 0x3f800000)
        for off in (0x33c, 0x344, 0x34c, 0x350):
            env.put(actor + off, animation)
        # A one-cell tile map delegates classification to a recorded callback.
        tilemap = env.object(0x80, 'tilemap', fill=0)
        mapdata = env.object(0xa0, 'mapdata', fill=0)
        cells = env.object(4, 'map-cells', words=[0])
        rows = env.object(4, 'map-rows', words=[0])
        tiles = env.object(4, 'tiles', fill=0)
        tile = env.object(4, 'tile', fill=0)
        tilev = env.object(0x24, 'tile-vtable', fill=0)
        env.put(tilemap + 0x4c, tiles)
        env.put(tilemap + 0x5c, mapdata)
        other_map = env.object(0x80, 'alternate-map', fill=0)
        other_data = env.object(0xa0, 'alternate-mapdata', fill=0)
        other_cells = env.object(4, 'alternate-map-cells', words=[0xffffffff])
        env.put(other_map + 0x5c, other_data)
        env.put(other_data + 0x20, other_cells, rows)
        env.put(other_data + 0x30, 512, 512)
        env.put(other_data + 0x8c, 9, 9)
        env.put(world + 0x24, tilemap, other_map)
        env.put(sprite + 0xc, world)
        env.put(mapdata + 0x20, cells, rows)
        env.put(mapdata + 0x30, 512, 512)
        env.put(mapdata + 0x8c, 9, 9)
        env.put(tiles, tile)
        env.put(tile, tilev)
        tile_receipt = env.object(0x100, 'tile-receipts', fill=0)
        def classify(e, call):
            n = e.get(tile_receipt)
            e.put(tile_receipt + 4 + n * 16, call.receiver, *call.arguments)
            e.put(tile_receipt, n + 1)
            values = options.get('tiles', (1, 0))
            return values[min(n, len(values) - 1)]
        env.put(tilev + 0x20, env.stub('tile-classification', 'thiscall', 2, classify))
        player = env.object(0x130, 'player', fill=0)
        env.put(player + 0x50, options.get('player_y', 20))
        env.put(player + 0x124, 7)
        env.put(0x537e88, player)
        if options.get('sound_active'):
            controller = env.object(0x188, 'sound-controller', fill=0)
            sound = env.object(0x20, 'sound', fill=0x71)
            root = env.object(0x34, 'resource-root', fill=0)
            resources = env.object(0x2c, 'resources', fill=0)
            container = env.object(0x1c, 'resource-container', fill=0)
            buckets = env.object(4, 'sound-buckets', fill=0)
            node = env.object(0x10, 'sound-node', fill=0)
            env.put(0x53c9ac, controller)
            env.put(0x53c9a8, 0)
            env.put(controller + 0x6c, sound)
            env.put(0x5371fc, root)
            env.put(root + 0x30, resources)
            env.put(resources + 0x28, container)
            env.put(container + 0x14, buckets, 1)
            env.put(buckets, node)
            env.put(node + 8, 0x52b338, 0x12345678)
        return actor
    return setup


def case(label, function, **options):
    return Case(label, function, setup_case(options), receiver=lambda actor: actor)


def cases(random_source):
    for speech in (-1, 0, 499, 500, 0x7fffffff):
        yield case('idle speech %d' % speech, 0x47f020, speech=speech, sound_active=True)
    for mode in (-1, 0, 1, 2, 3, 4, 5, 6, 7):
        for roll in (4, 5, 0xffffffff):
            yield case('idle tick mode %d roll %x' % (mode, roll), 0x47f0c0,
                       mode=mode, random=(roll,))
    for start, now, duration in ((100, 129, 30), (100, 130, 30),
                                 (0xfffffff0, 14, 30), (1, 0, 0xffffffff)):
        for disabled in (0, 1):
            yield case('tick clock %x %x %x disabled %d' % (start, now, duration, disabled),
                       0x47f0c0, mode=0, start=start, now=now, duration=duration,
                       disabled=disabled, random=(4,))
    for direction in (2, 3):
        for flags in (0x12345680, 0x12345682):
            for mode, roll, second in ((7, 99, 99), (2, 19, 99), (2, 20, 99),
                                        (3, 39, 99), (3, 40, 99), (3, 59, 99),
                                        (3, 60, 99), (4, 0, 49), (4, 0, 50),
                                        (4, 0xffffffff, 0xffffffff)):
                yield case('home %d flags%x mode%d rolls%d/%d' % (direction, flags, mode, roll, second),
                           0x47f160, direction=direction, flags=flags, mode=mode,
                           random=(roll, second, 99, 99))
    for function in (0x47f600, 0x47f680, 0x47f6b0):
        for flags in (0x12345680, 0x12345682):
            for finished, delay in ((0, 0), (1, 0), (1, 3), (0xffffffff, 0)):
                for world_state in (0, 1):
                    yield case('callback %x flags%x finished%d delay%d world%d' %
                               (function, flags, finished, delay, world_state), function,
                               flags=flags, finished=finished, delay=delay, world_state=world_state)
        yield case('callback %x changes animation after hit' % function, function,
                   finished=1, callback_mutates=True, next_finished=0)
    yield case('jump inactive', 0x47f290)
    for direction in (2, 3):
        for values in ((1, 0), (9, 2, 0), (9, 9, 3, 0), (9, 9, 9), (1, 4)):
            yield case('jump direction%d tiles%s' % (direction, values), 0x47f290,
                       direction=direction, world_state=1, tiles=values)
    for lo, hi in ((10.75, 20.25), (0.25, 19.75), (0.0, 20.0), (-20.0, 0.0),
                   (60.0, 0.0), (-0.75, 60.25)):
        for direction in (2, 3):
            yield case('jump bounds %s/%s dir%d' % (lo, hi, direction), 0x47f290,
                       direction=direction, world_state=1, d80=lo, d98=hi)
    for acceleration in ((0., 0., 0.), (0., 1., 0.), (.2, 0., 0.), (.1, -.2, .3), (1., -2., .5), (1.e-8, 0., 0.), (1.e-16, 0., 0.), (1.e-32, 0., 0.), (1.e-64, 0., 0.), (1.e-128, 0., 0.)):
        yield case('jump acceleration %s' % (acceleration,), 0x47f290, world_state=1,
                   d38=acceleration[0], d40=acceleration[1], d48=acceleration[2])
    for index in range(20):
        yield case('random jump %d' % index, 0x47f290, world_state=1,
                   direction=random_source.choice((2, 3)),
                   d38=random_source.uniform(-3, 3), d40=random_source.uniform(-3, 3),
                   d48=random_source.uniform(-3, 3), d68=random_source.uniform(-20, 20),
                   d70=random_source.uniform(-20, 20), d78=random_source.uniform(-20, 20))

    for roll in (19, 20, 21):
        yield case('home jump boundary %d' % roll, 0x47f160, mode=2,
                   world_state=1, random=(roll, 99), direction=2)
    for mode in (3, 4, 7):
        yield case('home helper observes named home %d' % mode, 0x47f160,
                   mode=mode, name=b'LS_HOME\0', random=(39, 0, 0, 0))
    yield case('jump exactly zero displacement', 0x47f290, world_state=1,
               direction=3, d68=20., d70=27., d78=0.)
    for function in (0x47f0c0, 0x47f600, 0x47f680, 0x47f6b0):
        for finished, delay in ((1, 0), (1, 3), (0, 0), (0, 3)):
            yield case('animation progress %x finished%d delay%d' % (function, finished, delay),
                       function, progress_animation=True, finished=finished,
                       delay=delay, mode=7, world_state=1)
