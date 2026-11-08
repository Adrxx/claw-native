"""Original-backed Omar state and transition cases."""
from clawparity.cases import Case
from clawparity.fixtures import returns


def state(**opts):
    def setup(env):
        obj = env.object(0xd80, 'omar', fill=0)
        sprite = env.object(0x240, 'sprite', fill=0)
        owner = env.object(0x200, 'world', fill=0)
        control = env.object(0x40, 'state-controller', fill=0)
        table = env.object(0x50, 'omar-vtable', fill=0)
        log = env.object(0x60, 'callback-observations', fill=0)
        resource = env.object(0x40, 'animation-resources', fill=0)
        env.put(resource + 0x18, 1)
        env.put(owner + 0x2c, resource)
        env.put(sprite + 0xc, owner)
        env.put(obj, table)
        env.put(obj + 0xc, owner, control)
        env.put(control + 0x1c, opts.get('old_state', 0x12345678))
        env.put(obj + 0x128, 0x13579, sprite)
        env.put(obj + 0x138, opts.get('left', 0x2468))
        env.put(obj + 0x140, opts.get('right', 0xffff91ab))
        env.put(obj + 0x18c, opts.get('direction', 2))
        env.put(obj + 0x184, opts.get('range', 8))
        env.put(obj + 0x3c4, opts.get('distance', 100))
        env.put(obj + 0xd1c, opts.get('shield', 1))
        env.put(obj + 0xd30, opts.get('start', 100))
        env.put(obj + 0xd34, opts.get('duration', 1000))
        env.put(obj + 0xd38, opts.get('x', 0xffffff83), opts.get('y', 0x7654321))
        env.put(obj + 0x1a0, opts.get('fired', 1))
        env.put(obj + 0xd40, opts.get('ended', 0))
        env.put(obj + 0x45c, 1)
        env.put(obj + 0x50, 0x1234abcd, 0x78ef0123, 0x61352487)
        env.put(obj + 0xd20, 0x917531)
        env.put(sprite + 0x4c, 257, 509, 1021)
        for index in range(5):
            env.put(obj + 0x464 + index*4, 0x731 + index*43)
        env.put(sprite + 8, opts.get('flags8', 0x93b4))
        env.put(sprite + 0x38, opts.get('sound_id', 0xffffffff))
        env.put(sprite + 0x40, opts.get('flags', 0xa5c8))
        for i, off in enumerate((0x118, 0x128, 0x138)):
            env.put(sprite + off, 0x80000000 if opts.get('sentinel', 0) & (1 << i) else 0x123 + i * 79)
            env.put(sprite + off + 8, 0xfffffedc - i * 97)
        # The original animation can return a selected frame marker while stopped.
        animation = env.object(0x20, 'animation', fill=0)
        env.put(sprite + 0x18c, sprite, animation)
        env.put(sprite + 0x19c, opts.get('pending', 0) if opts.get('complete', 1) else max(1, opts.get('pending', 0)))
        env.put(sprite + 0x1a4, opts.get('complete', 1))
        env.put(sprite + 0x1a8, opts.get('marker', 7))
        env.put(sprite + 0x1ac, opts.get('marker', 7))
        if opts.get('rich_animation'):
            frame = env.object(0x30, 'transition animation frame', fill=0)
            env.put(frame + 0xc, 9)
            env.put(frame + 0x18, 23, 13)
            frames = env.object(4, 'transition frame pointers', words=[frame])
            animation_resource = env.object(0x20, 'transition animation resource', fill=0)
            env.put(animation_resource + 0xc, frames, 1)
            env.put(obj + 0x350, animation_resource, 0)
            env.put(obj + 0x460, animation_resource)
            env.put(sprite + 0x194, frame)
            env.put(sprite + 0x19c, 7, 1, 0, 23, 29)
            strike_name = env.object(19, 'strike name', data=b'LEVEL_OMAR_STRIKE3\0')
            strike_node = env.object(0x10, 'strike animation node', words=[0, 0, strike_name, animation_resource])
            strike_bucket = env.object(4, 'strike bucket', words=[strike_node])
            env.put(resource + 0x14, strike_bucket)
        env.put(0x537210, opts.get('now', 1099))
        env.put(0x5430c4, 3 if opts.get('rich_animation') else 0)
        env.put(0x537668 + 0x18, 0)
        env.put(0x532c0c, opts.get('sound_enabled', 0))
        sound_target = env.object(0x200, 'subtitle-target', fill=0)
        sound_logic = env.object(0x40, 'subtitle-logic', fill=0)
        env.put(sound_target + 0x6c, sound_logic)
        env.put(0x53c9ac, sound_target)
        env.put(0x53c9a8, 0)
        player = env.object(0x200, 'player', fill=0)
        env.put(player + 0x10c, opts.get('health', 0))
        player_logic = env.object(0x40, 'player-logic', fill=0)
        env.put(player + 0x6c, player_logic)
        env.put(0x537e88, player)
        configuration = env.object(0x200, 'game-configuration', fill=0)
        env.put(configuration + 0x12c, 3)
        env.put(0x5371fc, configuration)
        env.put(obj + 0x3a4, 0x1947)
        env.override(0x4a3050, returns(opts.get('random', 17)))
        def callback(env, call):
            n = env.get(log)
            env.put(log, n + 1, call.receiver)
            env.put(log + 8, env.get(obj + 0x68), env.get(obj + 0x6c), env.get(obj + 0x70), env.get(obj + 0x74))
            env.put(log + 24, env.get(sprite + 8), env.get(sprite + 0x40))
            if opts.get('callback_mutate'):
                env.put(obj + 0x50, 0xabcdef13)
            return 0x98765432
        env.put(table + 0x44, env.stub('state complete', 'thiscall', 0, callback))
        if opts.get('sound'):
            sound = env.object(0x30, 'sound', fill=0)
            channel = env.object(0x30, 'channel', fill=0)
            backend = env.object(0x80, 'disabled-backend', fill=0)
            env.put(sound + 0x10, channel)
            env.put(channel + 0x10, backend)
            env.put(obj + 0x478, sound)
            if opts.get('active_audio'):
                interface = env.object(4, 'directsound interface', fill=0)
                methods = env.object(0x50, 'directsound methods', fill=0)
                env.put(interface, methods)
                env.put(channel + 0xc, interface)
                env.put(channel + 0x18, 22050)
                env.put(backend + 0x78, 1)
                def audio_effect(env, call):
                    count = env.get(log + 32)
                    env.put(log + 32, count + 1, call.arguments[0])
                    for index, value in enumerate(call.arguments[1:]):
                        env.put(log + 40 + index*4, value)
                    return 0
                for offset, argc in ((0x3c, 2), (0x40, 2), (0x44, 2), (0x30, 4), (0x48, 1)):
                    env.put(methods + offset, env.stub(f'DirectSound operation {offset:x}', 'stdcall', argc, audio_effect))
                other = env.object(0x30, 'neighbor sound', fill=0)
                other_channel = env.object(0x30, 'neighbor channel', fill=0)
                env.put(other + 0x10, other_channel)
                env.put(other_channel + 0x10, env.object(0x80, 'neighbor disabled backend', fill=0))
                env.put(obj + 0x474, other)
                env.put(obj + 0x47c, other)
        if opts.get('spawn'):
            manager = env.object(0x80, 'sprite-manager', fill=0)
            env.put(manager + 0xc, owner)
            nodes = env.object(0x30, 'spare-list-nodes', fill=0)
            env.put(manager + 0x20, nodes)
            registry = env.object(0x40, 'logic-resource-map', fill=0)
            buckets = env.object(4, 'one-bucket', fill=0)
            node = env.object(0x10, 'OmarBullet resource node', fill=0)
            name = env.object(11, 'OmarBullet name', data=b'OmarBullet\0')
            definition = env.object(0x20, 'OmarBullet definition', fill=0)
            env.put(definition + 0x10, 0x433070 if opts.get('crate') else 0x410400)
            env.put(node + 8, name, definition)
            env.put(buckets, node)
            env.put(registry + 0x14, buckets, 1)
            env.put(owner + 0x14, registry)
            env.put(owner + 0x10, resource)
            env.put(owner + 0x28, resource)
            if opts.get('projectile_frame'):
                texture = env.object(0x70, 'bullet sprite frames', fill=0)
                image = env.object(0x30, 'bullet frame image', fill=0)
                env.put(image + 0x18, 13, 19, 31, 47)
                images = env.object(4, 'bullet image pointers', words=[image])
                env.put(texture + 0x14, images)
                chain = 0
                for text in (b'GAME_BULLETS\0', b'LEVEL_OMARPROJECTILE\0'):
                    key = env.object(len(text), 'image resource key', data=text)
                    entry = env.object(0x10, 'image resource map node', words=[chain, 0, key, texture])
                    chain = entry
                image_buckets = env.object(4, 'image resource buckets', words=[chain])
                env.put(resource + 0x14, image_buckets)
            collision = env.object(0x80, 'collision world', fill=0)
            env.put(owner + 0x24, collision)
            frame = env.object(0x30, 'animation-frame', fill=0)
            env.put(frame + 0xc, 9)
            env.put(frame + 0x1c, 1)
            env.put(sprite + 0x194, frame)
            env.put(sprite + 0x1a4, 0)
            holder = env.object(0x20, 'logic-holder', fill=0)
            env.put(holder + 8, manager)
            env.put(control + 0xc, holder)
            env.put(obj + 0x130, control)
            env.put(obj + 0xd2c, opts.get('velocity', -300))
            env.put(obj + 0xd24, 65, -20)
            if opts.get('attack_sound'):
                env.put(obj + 0x474, env.object(0x20, 'attack-sound', fill=0))
        for i in range(9):
            ring = env.object(0x20, 'ring', fill=0x31+i)
            env.put(obj + 0x484 + 4*i, ring)
        return {'obj': obj, 'sprite': sprite}
    return setup


def call(label, fn, **opts):
    return Case(label, fn, state(**opts), receiver=lambda t: t['obj'], arguments=(0x9a75b321,) if fn == 0x464a60 else ())


def cases(random_source):
    for fn in (0x4645c0, 0x464770, 0x464930):
        for direction in (0, 2, 0xffffffff):
            for flags in (0xa5c8, 0xa5ca):
                for sentinel in (0, 1, 2, 4, 7):
                    yield call(f'{fn:x} facing {direction:x} flags {flags:x} sentinel {sentinel}', fn, direction=direction, flags=flags, sentinel=sentinel)
    for delta in (0, 999, 1000, 1001, 0xffffffff):
        yield call(f'move timer {delta:x}', 0x4645c0, now=(100+delta)&0xffffffff, callback_mutate=True)
    for fn in (0x4646f0, 0x4648e0, 0x464c00, 0x464c30):
        for flags in (0x9310, 0x9312):
            for sound in (False, True):
                yield call(f'{fn:x} transition flags {flags:x} sound {sound}', fn, flags=flags, sound=sound, sound_enabled=int(sound))
    for shield in (0, 1, 2, 0xffffffff):
        for sound in (False, True):
            for sound_id in (0xffffffff, 123):
                yield call(f'hit shield {shield:x} sound {sound} id {sound_id:x}', 0x464a60, shield=shield, sound=sound, sound_id=sound_id)
    for complete in (0, 1):
        for pending in (0, 3):
            for ended in (0, 1):
                for health in (0, 1, 0xffffffff):
                    yield call(f'dead {complete} {pending} {ended} {health:x}', 0x464b90, complete=complete, pending=pending, ended=ended, health=health)
    for distance in (-1, 0, 9, 10, 49, 50):
        for near in (-1, 0, 6, 7):
            yield call(f'home range {near} distance {distance}', 0x464930, range=near, distance=distance, shield=0)
    for flags in (0xa5c8, 0xa5ca):
        for direction in (0, 2):
            for marker in (0, 1, 2):
                for fired in (1, 0xffffffff):
                    yield call(f'magic no spawn {flags:x} {direction} {marker} {fired:x}', 0x464cc0, flags=flags, direction=direction, marker=marker, fired=fired)
    for distance in (-1, 0, 9, 10):
        for random in (0, 1, 2, 3, 4, 5, 0x7fffffff):
            for sound_id in (0xffffffff, 11):
                yield call(f'voice {distance} {random:x} {sound_id:x}', 0x464ed0, distance=distance, random=random, sound_id=sound_id)
    for fn in (0x464eb0, 0x464ec0):
        for value in (0, 1, 0xffffffff, 0x80000000, 0x7fffffff, random_source.getrandbits(32)):
            yield Case(f'{fn:x} integer {value:x}', fn, state(), receiver=lambda t:t['obj'], arguments=(value,))
    for value in (0, 0x10000, 0x89abcdef, random_source.getrandbits(32)):
        yield Case(f'ring mark {value:x}', 0x4646e0, state(flags8=value), arguments=(lambda t:t['sprite'],))

    for velocity in (-300, 0, 300):
        yield call(f'magic spawn real bullet {velocity}', 0x464cc0, spawn=True, fired=0, marker=1, velocity=velocity, attack_sound=True)

    for velocity in (-301, 0, 301):
        yield call(f'magic real bullet with image {velocity}', 0x464cc0, spawn=True, fired=0, marker=1, velocity=velocity, projectile_frame=True)

    yield call('magic spawn original crate initializer', 0x464cc0, spawn=True, fired=0, marker=1, velocity=-303, crate=True)

    for fn in (0x4646f0, 0x4648e0, 0x464770, 0x464930, 0x464a60, 0x464c30, 0x464b90):
        for flags in (0x9200, 0x9202):
            yield call(f'rich animation {fn:x} {flags:x}', fn, rich_animation=True, flags=flags, shield=0, distance=5, range=3, health=5)

    for flags in (0xa040, 0xa042):
        yield call(f'active idle audio {flags:x}', 0x4646f0, flags=flags, sound=True, active_audio=True, sound_enabled=1)
