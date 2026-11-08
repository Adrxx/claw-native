"""Independent original-behavior cases for Katherine's Level 4 states."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence

RAND = 0x4A3050


def setup_case(values):
    def setup(env):
        def obj(*args, **kwargs):
            kwargs.setdefault("fill", 0)
            return env.object(*args, **kwargs)
        backing = obj(0x1000, 'katherine-backing', fill=0x35)
        actor = backing + 0x300
        sprite = actor - 0x5C if values.get('alias_stamp') else obj(0x300, 'sprite')
        scene = obj(0x100, 'scene')
        state = obj(0x40, 'state-controller', fill=0x62)
        world = obj(0x80, 'world')
        mapobj = obj(0x80, 'collision-map')
        layer = obj(0xA0, 'layer')
        tile = obj(4, 'tile')
        tv = obj(0x24, 'tile-vtable')
        cells = obj(4, 'cells', words=[0])
        rows = obj(4, 'rows', words=[0])
        tiles = obj(4, 'tiles', words=[tile])
        log = obj(256, 'callbacks', fill=0)
        vtable = obj(0xA0, 'katherine-vtable')
        player = obj(0x100, 'player')
        resources = obj(0x60, 'resources')
        frame = obj(0x40, 'animation-frame')
        animation = obj(0x20, 'animation')
        frames = obj(4, 'frames', words=[frame])
        env.put(animation + 0xC, frames, 1)
        env.put(frame + 0xC, 9)
        env.put(frame + 0x18, 7, 0x391, 0x927)
        env.put(sprite + 0x188 + 4, sprite, 0)
        env.put(actor, vtable)
        env.put(actor + 0xC, scene, state)
        env.put(actor + 0x128, sprite, sprite)
        env.put(sprite + 0xC, world)
        env.put(world + 0x24, mapobj, resources)
        env.put(resources + 0x18, 1)
        env.put(mapobj + 0x4C, tiles)
        env.put(mapobj + 0x5C, layer)
        env.put(layer + 0x20, cells, rows)
        env.put(layer + 0x30, 1024, 1024)
        env.put(layer + 0x8C, 10, 10)
        env.put(tile, tv)
        env.put(player + 0x4C, values.get('player_x', 500))
        env.put(0x537E88, player)
        env.put(0x541334, values.get('busy', 0))
        env.put(0x5430C4, values.get('delta', 3))
        env.put(0x53C9AC, 0)
        env.put(0x532C0C, 0)
        if values.get('zero_epsilon'):
            env.write(0x513E20, struct.pack('<d', 0.0))
        env.put(0x537668 + 0x18, 0)
        # Bound reverse state lookup to one non-HOME entry, avoiding unrelated HOME logic.
        entry = obj(4, 'state-name-entry', words=[0x523148])
        old_state = values.get('old_state', 0x123)
        env.put(0x537698 + 8, old_state, old_state, entry)
        env.put(0x537698 + 0x18, 4)
        env.put(0x5376B8, 0)
        env.put(state + 0x1C, old_state)
        env.put(sprite + 0x38, values.get('sound', -1))
        env.put(sprite + 0x40, values.get('flags', 0xA0))
        env.put(sprite + 0x4C, 430, 100)
        env.put(sprite + 0x124, 0)
        env.put(sprite + 0x190, animation, frame)
        env.put(sprite + 0x1B0, 0x3F800000)
        env.put(actor + 0x18C, values.get('direction', 2))
        env.put(actor + 0x184, values.get('state', 1))
        env.put(actor + 0x3C4, values.get('timer', 0))
        env.put(actor + 0x138, values.get('left', -13))
        env.put(actor + 0x140, values.get('right', 29))
        for i, offset in enumerate((0x118, 0x128, 0x138)):
            env.put(sprite + offset, 0x80000000 if values.get('sentinels', 0) & (1 << i) else (17 + i * 13))
            env.put(sprite + offset + 8, 73 + i * 19)
        env.put(actor + 0x350, animation if values.get('animation', True) else 0)
        env.put(actor + 0x464, animation if values.get('animation', True) else 0)
        env.put(actor + 0x468, animation if values.get('animation', True) else 0)
        env.put(actor + 0x34C, animation)
        env.put(actor + 0x2FC, 3)
        env.put(actor + 0x300, 4)
        for off, val in ((0x38, 1.25), (0x40, -2.5), (0x48, 4.0), (0x50, 5.500000000000001),
                         (0x58, -8.250000000000002), (0x60, 9.750000000000002), (0x68, 450.25), (0x70, 50.75), (0x78, 7.5)):
            env.write(actor + off, struct.pack('<d', values.get('f' + hex(off), val)))
        # Different, nonzero callback results and memory records expose receiver and publication order.
        for off, argc in ((0x44, 0), (0x48, 0), (0x50, 3), (0x54, 2), (0x60, 0), (0x64, 0)):
            def effect(env, call, off=off):
                n = env.get(log)
                env.put(log, n + 1)
                env.put(log + 4 + n * 24, off, call.receiver, env.get(actor + 0x20), env.get(actor + 0x3A0), env.get(sprite + 8), env.get(actor + 0x134))
                return 0xAB00 + off
            env.put(vtable + off, env.stub('virtual-' + hex(off), 'thiscall', argc, effect))
        def collision(env, call):
            y = call.arguments[1]
            if y == 101:
                return values.get('ground', 1)
            if y == 100:
                return values.get('head', 0)
            return values.get('path', 0)
        env.put(tv + 0x20, env.stub('tile-contact', 'thiscall', 2, collision))
        env.override(RAND, sequence(*values.get('randoms', (0, 50, 99, 7))))
        env.put(sprite + 0x19C, values.get('pending', 0))
        env.put(sprite + 0x1A4, values.get('complete', 1))
        if values.get('lookup'):
            # A one-bucket chained map with exact original keys and distinct objects.
            bucket = obj(4, 'sound-bucket')
            head = 0
            for address in (0x528510, 0x528504, 0x528354):
                soundobj = obj(0x80, 'sound')
                if values.get('audio_enabled'):
                    engine = obj(0x80, 'sound-engine')
                    env.put(0x532C0C, 1)
                    env.put(engine + 0x78, 1)
                    env.put(soundobj + 0x10, engine)
                    env.put(soundobj + 0x18, 8000, 9, 17)
                    instance = obj(0x40, 'sound-instance')
                    interface = obj(4, 'directsound-interface')
                    methods = obj(0x50, 'directsound-methods')
                    env.put(soundobj + 0x30, instance + 4)
                    env.put(instance + 0xC, interface, engine, 5, 8000)
                    env.put(instance + 0x30, 1)
                    env.put(interface, methods)
                    for slot, argc in ((0x24, 2), (0x30, 4), (0x3C, 2), (0x40, 2), (0x44, 2)):
                        def sound_effect(env, call, slot=slot):
                            if slot == 0x24:
                                env.put(call.arguments[1], 0)
                            return 0
                        env.put(methods + slot, env.stub('sound-' + hex(slot), 'stdcall', argc, sound_effect))
                wrapper = obj(0x20, 'sound-resource')
                env.put(wrapper + 0x10, soundobj)
                node = obj(16, 'resource-node', words=[head, 0, address, wrapper])
                head = node
            env.put(bucket, head)
            env.put(resources + 0x14, bucket, 1)
        if values.get('state_lookup'):
            key = values.get('name', b'LS_FLIP3\0')
            name = obj(len(key), 'state-name', data=key)
            node = obj(20, 'state-node')
            env.put(node, node, node, 0, name, values.get('state_result', 0xB97531))
            env.put(0x537668 + 0x18, node)
        else:
            name = obj(10, 'state-name', data=b'LS_CUSTOM\0')
        # Give every adjacent animation source a valid but observably different value.
        for offset in (0x34C, 0x354, 0x460, 0x468, 0x46C):
            altframe = obj(0x40, 'distinct-frame')
            altanim = obj(0x20, 'distinct-animation')
            altframes = obj(4, 'distinct-frames', words=[altframe])
            env.put(altframe + 0xC, 9)
            env.put(altframe + 0x18, 11, 0xC000 + offset, 0xD000 + offset)
            env.put(altanim + 0xC, altframes, 1)
            env.put(actor + offset, altanim)
        if not values.get('animation', True):
            env.put(actor + 0x468, 0)
        if values.get('distinct_geometry'):
            geometry = obj(0x300, 'geometry-sprite', data=env.read(sprite, 0x300))
            env.put(geometry + 0x190, 0x56789)
            env.put(actor + 0x128, geometry)
            if values.get('distinct_world'):
                alternate_world = obj(0x80, 'alternate-world', data=env.read(world, 0x80))
                alternate_map = obj(0x80, 'alternate-map', data=env.read(mapobj, 0x80))
                alternate_tiles = obj(4, 'alternate-tiles')
                alternate_tile = obj(4, 'alternate-tile')
                alternate_methods = obj(0x24, 'alternate-tile-vtable')
                env.put(alternate_tiles, alternate_tile)
                env.put(alternate_tile, alternate_methods)
                def alternate_collision(env, call):
                    return 1
                env.put(alternate_methods + 0x20, env.stub('alternate-contact', 'thiscall', 2, alternate_collision))
                env.put(alternate_map + 0x4C, alternate_tiles)
                env.put(alternate_world + 0x24, alternate_map)
                env.put(sprite + 0xC, alternate_world)
        if values.get('alias_state'):
            env.put(actor + 0x10, actor + 8)
            env.put(actor + 0x24, old_state)
        if values.get('alias_state_stamp'):
            # state + 0x1c coincides with the publication slot actor + 0x134.
            env.put(actor + 0x10, actor + 0x118)
            env.put(actor + 0x134, old_state)
        return dict(actor=actor, sprite=sprite, animation=animation, name=name)
    return setup


def case(label, function, **values):
    args = ()
    if function == 0x455360:
        args = (lambda t: t['animation'] if values.get('animation', True) else 0, values.get('update', 0))
    elif function == 0x4553A0:
        args = (lambda t: t['name'],)
    return Case(label, function, setup_case(values), receiver=lambda t: t['actor'] + (0x128 if function == 0x455360 else 0), arguments=args)


def cases(random_source):
    for direction in (0, 2, 3, 0xFFFFFFFF):
        for flags in (0xA0, 0xA2):
            for mask in range(8):
                yield case(f'mirror {direction:x}/{flags:x}/{mask}', 0x4550E0, direction=direction, flags=flags, sentinels=mask,
                           left=random_source.getrandbits(32), right=random_source.getrandbits(32))
    for state in (-1, 0, 1, 2, 3, 4, 5, 6, 7):
        for timer in (-1, 0, 399, 400, 599, 600):
            yield case(f'attack {state}/{timer}', 0x454A10, state=state, timer=timer, direction=2 if timer & 1 else 3)
    for first in (-101, -1, 0, 49, 50, 99, 100, 0x7FFFFFFF, 0x80000000):
        for second in (49, 50):
            yield case(f'stab threshold {first}/{second}', 0x454A10, state=4, randoms=(first, second), lookup=True)
        for sound in (-1, 17):
            yield case(f'whip threshold {first}/{sound}', 0x454A10, randoms=(first,), sound=sound)
    for state in (-1, 0, 1, 2, 3, 4, 5, 6, 7, 0x80000000):
        for busy in (0, 1):
            for rand in (4, 5):
                yield case(f'idle {state}/{busy}/{rand}', 0x454C20, state=state, busy=busy, randoms=(rand,))
    for fn in (0x454B90, 0x455280, 0x455230, 0x455360, 0x4553A0):
        for animation in (False, True):
            for lookup in (False, True):
                for update in (0, 1):
                    yield case(f'state setter {fn:x}/{animation}/{lookup}/{update}', fn, animation=animation,
                               state_lookup=lookup, name=b'LS_IDLE\0' if fn == 0x454B90 else b'LS_FLIP3\0', update=update)
    for fn in (0x455230,):
        for mode in (-1, 0, 1, 2, 8):
            # Set scene's update mode through a dedicated setup wrapper below.
            c = case(f'flip wait {mode}', fn)
            original = c.setup
            def setup(env, original=original, mode=mode):
                t = original(env)
                env.put(env.get(t['actor'] + 0xC) + 0xCC, mode)
                return t
            c.setup = setup
            yield c
    for complete in (0, 1):
        for pending in (0, 1):
            for rand in (-1, 0, 9, 10, 99):
                for sound in (-1, 7):
                    yield case(f'flip end {complete}/{pending}/{rand}/{sound}', 0x4552D0, complete=complete, pending=pending, randoms=(rand,), sound=sound, flags=0xA7)
    for direction in (2, 3):
        for path, ground, head in ((1, 1, 0), (0, 0, 0), (0, 4, 0), (0, 1, 1), (0, 1, 0), (0, 2, 0), (0, 3, 0)):
            for lookup in (False, True):
                yield case(f'jump {direction}/{path}/{ground}/{head}/{lookup}', 0x454CB0, direction=direction, path=path, ground=ground, head=head, lookup=lookup)
    for acceleration in (0.0, 1e-12, -1.0, 12.5):
        for origin in (300.0, 700.0):
            yield case(f'left trajectory {acceleration}/{origin}', 0x454CB0, direction=3, f0x38=acceleration, f0x40=0.0, f0x48=0.0, f0x68=origin, f0x78=0.0)

    yield case('zero acceleration normalized branch', 0x454CB0, direction=3, f0x38=0.0, f0x40=0.0, f0x48=0.0, zero_epsilon=True)
    yield case('idle entry sound', 0x454B90, sound=7)

    for acceleration in (-0.5, -0.1, 0.001, 0.1, 0.5):
        for origin in (300.0, 700.0):
            for z in (0.0, 17.25):
                yield case(f'finite normalized trajectory {acceleration}/{origin}/{z}', 0x454CB0,
                           direction=3, f0x38=acceleration, f0x40=acceleration / 3,
                           f0x48=-acceleration / 7, f0x68=origin, f0x78=z)
    for old in (0x13579BDF, 0x80000000, 0xFFFFFFFF):
        for fn in (0x454B90, 0x455230, 0x455280, 0x455360, 0x4553A0):
            for alias in ('alias_state', 'alias_state_stamp'):
                yield case(f'aliased state {fn:x}/{old:x}/{alias}', fn, old_state=old,
                           state_lookup=True, name=b'LS_IDLE\0' if fn == 0x454B90 else b'LS_FLIP3\0', **{alias: True})
    for fn in (0x454B90, 0x455280, 0x455360):
        yield case(f'distinct geometry {fn:x}', fn, distinct_geometry=True, state_lookup=True)
        yield case(f'alias stamp {fn:x}', fn, alias_stamp=True, state_lookup=True)
    for direction in (2, 3):
        for rand in (-200, -1, 0, 199, 200, 201, 0x7FFFFFFF, 0x80000000):
            yield case(f'jump signed random {direction}/{rand}', 0x454CB0, direction=direction,
                       randoms=(rand,), distinct_geometry=True, lookup=True)

    for direction in (2, 3):
        for lookup in (False, True):
            yield case(f'audible jump {direction}/{lookup}', 0x454CB0, direction=direction, lookup=lookup, audio_enabled=True)
    for acceleration in (0.0, 0.003, -0.17, 1.73):
        for x, y, z in ((300.1, 50.33, -7.71), (700.7, -8.3, 13.91)):
            yield case(f'asymmetric trajectory {acceleration}/{x}', 0x454CB0, direction=3,
                       f0x38=acceleration, f0x40=acceleration * 2.31, f0x48=-acceleration * 0.713,
                       f0x68=x, f0x70=y, f0x78=z)

    for direction in (2, 3):
        for ground in (1, 3):
            yield case(f'distinct neighboring worlds {direction}/{ground}', 0x454CB0, direction=direction, distinct_geometry=True, distinct_world=True, ground=ground)
