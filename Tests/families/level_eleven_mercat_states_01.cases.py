"""Original-backed Mercat state inputs; all game callees execute unchanged."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_case(entry, **cfg):
    def setup(env):
        def obj(*args, **kwargs):
            kwargs.setdefault("fill", 0)
            return env.object(*args, **kwargs)
        r = obj(0x600, 'mercat')
        sprite = obj(0x220, 'mercat-sprite')
        holder = obj(0x80, 'state-holder')
        target = obj(0x220, 'player-sprite')
        world = obj(0x100, 'world')
        context = obj(0x80, 'context')
        factory = obj(0x80, 'sprite-factory')
        vtable = obj(0x100, 'mercat-vtable')
        log = obj(0x2000, 'callback-observations')
        tick = cfg.get('tick', 0x12345678)
        env.put(r, vtable)
        env.put(r + 0xc, sprite, holder)
        env.put(r + 0x12c, sprite, context)
        env.put(r + 0x194, target)
        env.put(r + 0x184, cfg.get('action', 9))
        env.put(r + 0x18c, cfg.get('facing', 2))
        env.put(r + 0x138, cfg.get('left', 7))
        env.put(r + 0x140, cfg.get('right', 19))
        env.put(r + 0x50, 0xdeadbeef, 0x40abcdef)
        env.put(r + 0x24, 0x2222)
        env.put(r + 0x134, 0x3333)
        env.put(r + 0x1a0, 0x4444)
        env.put(r + 0x4cc, cfg.get('dx', 28), cfg.get('dy', 13), cfg.get('speed', 400), 0x5555, cfg.get('firing', 0))
        env.put(holder + 0x1c, 3)
        env.put(sprite + 0x40, cfg.get('flip', 0x100))
        env.put(sprite + 0x4c, 128, 128)
        env.put(sprite + 0x64, 57)
        env.put(sprite + 0x16c, cfg.get('event', 0))
        env.put(sprite + 0x18c, sprite)
        env.put(sprite + 0x118, 7, 11, 19, 23)
        env.put(sprite + 0x128, 29, 31, 37, 41)
        env.put(sprite + 0x138, 43, 47, 53, 59)
        env.put(target + 0x4c, 160, 128 + cfg.get('target_dy', 0))
        env.put(target + 0x38, cfg.get('target_state', 0))
        env.put(sprite + 0x38, cfg.get('target_state', 0))
        env.put(r + 0x190, context)
        env.put(context + 0xc, world)
        env.put(world + 8, factory)
        env.put(factory + 0xc, world)
        free_nodes = obj(0xc0, 'factory-free-nodes')
        for n in range(15):
            env.put(free_nodes + n * 12, free_nodes + (n + 1) * 12)
        env.put(factory + 0x20, free_nodes)
        env.put(factory + 0x28, 16)

        def physical_callback(env, call):
            at = env.get(log)
            env.put(log + 4 + at * 256, call.receiver, len(call.arguments), *(list(call.arguments[:2]) + [0, 0])[:2])
            env.write(log + 20 + at * 256, env.read(r + 0x20, 0x40))
            env.write(log + 84 + at * 256, env.read(r + 0x480, 0x60))
            env.put(log + 180 + at * 256, env.get(env.get(0x53c9ac) + 0x184))
            env.put(log, at + 1)
            if cfg.get('mutate_tick'):
                env.put(0x537210, tick + 71)
            return cfg.get('callback_result', 0xabcdef01)

        for offset in (0x44, 0x48, 0x58, 0x90):
            argc = 1 if offset == 0x90 else 0
            env.put(vtable + offset, env.stub('mercat-virtual-%x' % offset, 'thiscall', argc, physical_callback))

        def mapping(name, entries):
            m = obj(0x40, name)
            buckets = obj(4, name + '-buckets')
            env.put(m + 4, buckets, 1)
            head = 0
            for key, value in entries:
                text = obj(len(key) + 1, name + '-key', data=key.encode() + b'\0')
                node = obj(16, name + '-node', words=[head, 0, text, value])
                head = node
            env.put(buckets, head)
            return m

        descriptor = obj(0x20, 'TridentBullet-definition')
        env.put(descriptor + 8, 0)
        env.put(descriptor + 0x10, cfg.get('factory_callback', 0x410580))
        classes = mapping('class-map', [('TridentBullet', descriptor)])
        class_manager = obj(0x60, 'class-manager')
        # Maps are embedded at manager+0x10, rather than pointed to.
        env.write(class_manager + 0x10, env.read(classes, 0x30))
        env.put(world + 0x14, class_manager)
        image = obj(0x80, 'trident-image')
        frame = obj(0x40, 'trident-frame')
        frames = obj(4, 'trident-frames', words=[frame])
        env.put(frame + 0x18, 3, 5, 17, 29)
        env.put(image + 0x14, frames)
        env.put(image + 0x64, 0, 0)
        images = mapping('image-map', [('LEVEL_TRIDENT_TRIDENTPROJECTILE', image), ('LEVEL_PROJECTILES_STALACTITE', image)] if cfg.get('image', True) else [])
        image_manager = obj(0x60, 'image-manager')
        env.write(image_manager + 0x10, env.read(images, 0x30))
        env.put(world + 0x10, image_manager)
        animations = mapping('animation-map', [])
        animation_manager = obj(0x60, 'animation-manager')
        env.write(animation_manager + 0x10, env.read(animations, 0x30))
        env.put(world + 0x2c, animation_manager)
        env.put(world + 0x28, animation_manager)
        collision = obj(0x100, 'collision-world')
        env.put(world + 0x24, collision)
        geometry = obj(0x100, 'tile-geometry')
        tiles = obj(4, 'tiles', words=[0])
        rows = obj(4, 'tile-rows', words=[0])
        tile_classes = obj(4, 'tile-classes')
        tile = obj(4, 'tile')
        tile_vtable = obj(0x24, 'tile-vtable')
        def tile_kind(env, call):
            return cfg.get('blocked', 0)
        env.put(tile_vtable + 0x20, env.stub('tile-kind', 'thiscall', 2, tile_kind))
        env.put(tile, tile_vtable)
        env.put(tile_classes, tile)
        env.put(collision + 0x4c, tile_classes)
        env.put(collision + 0x5c, geometry)
        env.put(collision + 0x64, 1000, 1000)
        env.put(geometry + 0x20, tiles, rows)
        env.put(geometry + 0x30, 4096, 4096)
        env.put(geometry + 0x8c, 12, 12)
        env.put(0x537210, tick)
        env.put(0x5430c4, cfg.get('step', 7))
        env.put(0x534eac, cfg.get('level_flag', 0))
        env.put(0x537e88, target)
        env.put(0x537964, cfg.get('level', 11))
        env.put(0x532c0c, 0)
        env.put(0x532c10, 0x123)
        env.put(0x53724c, 1)
        env.put(0x534874, 0)
        env.put(0x53490c, 0x7fffffff)
        sound_sprite = obj(0x200, 'sound-player')
        sound_state = obj(0x140, 'sound-state')
        env.put(sound_sprite + 0x6c, sound_state)
        env.put(sound_state + 0x1c, 15)
        env.put(sound_state + 0x130, 0x5678)
        env.put(0x53c9ac, sound_sprite)
        env.put(0x53c9a8, 0)
        env.put(0x53c9b0, sprite)
        env.put(0x537668 + 0x18, 0)
        state_name = obj(8, 'state-name', data=b'OTHER\0')
        state_slot = obj(4, 'state-slot', words=[state_name])
        env.put(0x537698 + 8, 0, 20, state_slot, state_slot, 0)
        env.put(0x5376b8, 0)
        for offset, duration_key, elapsed_key in [(0x484, 'home_duration', 'home_elapsed'), (0x48c, 'fire_duration', 'fire_elapsed'), (0x494, 'release_duration', 'release_elapsed'), (0x4a4, 'cool_duration', 'cool_elapsed'), (0x4ac, 'pace_duration', 'pace_elapsed'), (0x4b4, 'projectile_duration', 'projectile_elapsed')]:
            duration = cfg.get(duration_key, 100)
            elapsed = cfg.get(elapsed_key, 100)
            env.put(r + offset, (tick - elapsed) & 0xffffffff, duration)
        for off in (0x308, 0x30c, 0x310, 0x34c, 0x4bc, 0x4c0, 0x4c4, 0x4c8):
            animation = obj(0x20, 'animation-%x' % off)
            animation_frame = obj(0x30, 'animation-frame-%x' % off)
            animation_frames = obj(4, 'animation-frames-%x' % off, words=[animation_frame])
            env.put(animation + 0xc, animation_frames, 1)
            env.put(animation_frame + 0xc, 9)
            env.put(animation_frame + 0x18, 127, 0x10000 + off)
            env.put(r + off, animation)
            if off == 0x308 and cfg.get('live_animation'):
                env.put(sprite + 0x190, animation, animation_frame, 0, 37, 1, 0, 0x1234, 0x5678, 0x3f800000)
        for off in range(0x454, 0x47c, 4):
            env.put(r + off, 0x1000 + off)
        env.put(r + 0x450, obj(0x20, 'sound') if cfg.get('sound', False) else 0)
        env.put(r + 0x400, 97, 151)
        env.put(r + 0x2fc, 3, 4)  # bit 2 elects the genuine original virtual pacing path
        def copy_rect(env, call):
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            return 1
        env.override(0x546d58, copy_rect)
        def physical_allocate(env, call):
            return env.object(call.arguments[0], 'allocation', fill=0)
        env.override(0x4f63ec, physical_allocate)
        env.override(0x4a3050, sequence(*cfg.get('random', [99, 99, 99, 99])))
        if entry == 0x4616e0:
            for off, value in [(0x50, 3.), (0x58, 5.), (0x68, 19.), (0x70, 23.), (0x80, 1.), (0x98, 37.), (0xb0, 0.), (0xb8, 0.)]:
                env.write(r + off, struct.pack('<d', value))
            env.put(sprite + 0x118, 3, 5, 17, 29)
        return {'receiver': r}
    return setup


def item(label, entry, **cfg):
    return Case(label, entry, setup_case(entry, **cfg), receiver=lambda t: t['receiver'])


def cases(random_source):
    for facing in (1, 2, 3):
        for flip in (0x100, 0x102):
            for elapsed in (99, 100, 101):
                yield item(f'fire-entry facing{facing} flip{flip} elapsed{elapsed}', 0x461360, facing=facing, flip=flip, fire_elapsed=elapsed, left=random_source.getrandbits(32), right=random_source.getrandbits(32))
    for action in range(9):
        for choice in (-1, 0, 1, 2, 3, 20, 99):
            yield item(f'home action{action} random{choice}', 0x460c50, action=action, random=[choice, choice % 3, 99, 99], fire_elapsed=99)
    for elapsed in (99, 100, 101, 0xffffffff):
        for facing in (1, 2):
            yield item(f'home cooldown {elapsed} face{facing}', 0x460c50, cool_elapsed=elapsed, facing=facing, home_elapsed=elapsed)
    for dy in (-51, -50, -49, 0, 49, 50, 51):
        yield item(f'home target dy{dy}', 0x460c50, target_dy=dy)
    for flag, blocked, target_state in [(0x26b7, 0, 0), (0, 1, 0), (0, 0, -1)]:
        yield item(f'home reject {flag}/{blocked}/{target_state}', 0x460c50, level_flag=flag, blocked=blocked, target_state=target_state)
    for action in range(9):
        for choice in (-3, -1, 0, 1, 2, 3, 4, 19, 20, 24, 25, 50, 51, 99):
            yield item(f'pace action{action} random{choice}', 0x460ea0, action=action, random=[choice, 0, choice, 99])
    for elapsed in (99, 100, 101, 0xffffffff):
        yield item(f'pace cooldown {elapsed}', 0x460ea0, action=5, cool_elapsed=elapsed, pace_elapsed=elapsed, random=[0, 19, 51])
    for event in (0, 203, 204):
        for firing in (0, 1, 7):
            for elapsed in (99, 100, 101):
                yield item(f'firing event{event} flag{firing} elapsed{elapsed}', 0x4614c0, event=event, firing=firing, projectile_elapsed=elapsed, release_elapsed=elapsed)
    for level in (10, 11, 12):
        for sound in (False, True):
            for speed in (-2147483648, -400, -1, 0, 1, 400, 2147483647):
                yield item(f'projectile level{level} sound{sound} speed{speed}', 0x4614c0, event=203, sound=sound, speed=speed, level=level, dx=random_source.randrange(-100, 101), dy=random_source.randrange(-100, 101))
    for image in (False, True):
        yield item(f'projectile image{image}', 0x4614c0, firing=1, image=image)
    for tick in (0, 1, 0x7fffffff, 0xffffffff):
        yield item(f'firing timer-wrap {tick}', 0x4614c0, firing=1, tick=tick)
    for _ in range(8):
        yield item('death original physical rectangle', 0x4616e0, tick=random_source.randrange(1, 100000))

    for action in (3, 4):
        for elapsed in (99, 100, 101):
            yield item(f'home-vcall duration boundary {action}/{elapsed}', 0x460c50, action=action, home_elapsed=elapsed, mutate_tick=True)

    # The registry is input. This unchanged Stalactite factory initializes both
    # sprite extents and the common actor +0x12c field. It reaches the defensive
    # second-extent mirror that normal Trident initialization leaves sentinel.
    for speed in (1, 400, 2147483647):
        yield item(f'original alternate actor factory speed{speed}', 0x4614c0, firing=1, speed=speed, factory_callback=0x4073e0)

    for facing in (1, 2, 3):
        for flip in (0x100, 0x102):
            yield item(f'fire-entry clears prior firing {facing}/{flip}', 0x461360, facing=facing, flip=flip, firing=0x76543210)
    for action in (0, 2, 3, 5, 9):
        yield item(f'home observes animation progress {action}', 0x460c50, action=action, live_animation=True, random=[99, 99])
        yield item(f'pace observes animation progress {action}', 0x460ea0, action=action, live_animation=True, random=[1, 19, 51])
    for sound_choice in (0, 24, 25, 50, 51, 99):
        yield item(f'pace callback observes sound publication {sound_choice}', 0x460ea0, action=5, random=[0, 0, sound_choice])
