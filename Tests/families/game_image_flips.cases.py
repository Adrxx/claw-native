"""Original-only inputs for the six flipped image drawing entries."""
from clawparity.cases import Case

ENTRIES = ((0x4D3550, 'xy', False), (0x4D3790, 'x', False),
           (0x4D3A00, 'y', False), (0x4D2BB0, 'xy', True),
           (0x4D2E10, 'x', True), (0x4D3080, 'y', True))


def scene(kind, surface, x, y, width=9, height=7, mode='target',
          clip=(2, 3, 6, 5), mutate=False, failure=False, seed=19):
    def setup(env):
        image = env.object(0x34, 'image', fill=0x31)
        actor = env.object(0x64, 'actor', fill=0x65)
        target = env.object(0x34, 'target-image', fill=0x73)
        owner = env.object(0x28, 'image-owner', fill=0x29)
        viewport = env.object(0x20, 'viewport', fill=0x17)
        world = env.object(0x60, 'world', fill=0x43)
        transform = env.object(0x58, 'transform', fill=0)
        desc = env.object(0x28, 'software-descriptor', fill=0)
        source_pixels = env.object(32 * 32, 'source-pixels',
            data=bytes(((i * 37 + i // 32 * 11 + seed) % 255) + 1 for i in range(1024)))
        pixels = env.object(40 * 34, 'guarded-destination', fill=0xA7)
        dst = env.object(188, 'destination-wrapper', fill=0)
        src = env.object(188, 'source-wrapper', fill=0)
        interface = env.object(4, 'destination-interface')
        src_interface = env.object(4, 'source-interface')
        methods = env.object(132, 'COM-vtable', fill=0)
        journal = env.object(512, 'callback-observations', fill=0)
        env.put(image + 0x0c, owner, width, height, 3, 5, 2, 4)
        env.put(image + 0x2c, src, desc)
        env.put(actor + 8, 0x40000 if mode == 'viewport' else 0x10201)
        env.put(actor + 0x10, 1, 2)
        # Choose the requested pre-transform coordinate with distinct origin fields.
        ax = x + 6 if kind != 'y' else x
        ay = y - 1 if kind == 'x' else y + 11
        if mode == 'viewport':
            ax += 4
            ay += 6
        env.put(actor + 0x3c, world)
        env.put(actor + 0x4c, ax, ay)
        env.put(actor + 0x54, *(clip if mode == 'actor' else (0x80000000, 13, 17, 19)))
        env.put(owner + 0x24, viewport)
        env.put(viewport + 0x10, *clip)
        env.put(world + 0x5c, transform)
        env.put(transform + 0x40, 7, 9, 23, 29, 3, 3)
        env.put(target + 0x10, 12, 10)
        env.put(target + 0x2c, dst)
        env.put(desc + 4, 32, 32, source_pixels)
        env.put(desc + 0x14, 0)
        env.write(desc + 0x24, b'\x01')
        env.put(dst + 8, interface)
        env.put(src + 8, src_interface)
        env.put(dst + 0x14, 32, 32, 40)
        env.put(dst + 0x30, pixels + 40)
        env.put(interface, methods)
        env.put(src_interface, methods)

        def record(env, call, tag):
            count = env.get(journal)
            out = journal + 4 + count * 112
            env.put(journal, count + 1)
            env.put(out, tag, call.receiver, len(call.arguments), *call.arguments)
            env.write(out + 40, env.read(actor + 0x18, 36))
            return out

        def lock(env, call):
            record(env, call, 1)
            env.put(dst + 0x30, pixels + 40)
            return 0

        def unlock(env, call):
            record(env, call, 2)
            return 0x80004005 if failure else 0

        def blt(env, call):
            out = record(env, call, 3)
            env.write(out + 76, env.read(call.arguments[1], 16))
            env.write(out + 92, env.read(call.arguments[3], 16))
            if mutate:
                env.put(call.arguments[1], 4, 5, 8, 9)
            return 0x80004005 if failure else 0

        env.put(methods + 0x14, env.stub('Blt', 'stdcall', 6, blt))
        env.put(methods + 0x64, env.stub('Lock', 'stdcall', 5, lock))
        env.put(methods + 0x80, env.stub('Unlock', 'stdcall', 2, unlock))
        for address in (0x54139c, 0x5413a0, 0x5413a4, 0x5413a8):
            env.put(address, 0)

        def copy_rect(env, call):
            out = record(env, call, 4)
            env.write(out + 76, env.read(call.arguments[1], 16))
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            if mutate:
                # The actor's output fields must be published after drawing.
                env.put(actor + 0x18, 0x13579, 0x24680)
            return 1

        env.override(0x546d58, copy_rect)
        return {'image': image, 'actor': actor, 'target': target}
    return setup


def cases(random_source):
    for entry, kind, surface in ENTRIES:
        def emit(label, **kw):
            return Case(f'{entry:x} {label}', entry, scene(kind, surface, **kw),
                receiver=lambda t: t['image'],
                arguments=(lambda t: t['actor'], lambda t: t['target']))
        for mode in ('target', 'actor', 'viewport'):
            for x, y in ((3, 4), (-2, -1), (8, 7), (-3, 2), (2, -2),
                         (20, 3), (3, 20), (0, 0), (2, 3)):
                yield emit(f'{mode} at {x},{y}', x=x, y=y, mode=mode)
            yield emit(f'{mode} unclipped', x=3, y=4, mode=mode, clip=(-10, -9, 30, 29))
            yield emit(f'{mode} mutation', x=0, y=1, mode=mode, mutate=True)
        for width, height in ((0, 7), (9, 0), (-1, 7), (9, -1), (1, 1), (1, 7), (9, 1)):
            yield emit(f'geometry {width}x{height}', x=3, y=4, width=width, height=height)
        yield emit('draw failure ignored', x=3, y=4, failure=True)
        for i in range(12):
            yield emit(f'random {i}', x=random_source.randrange(-5, 15),
                y=random_source.randrange(-5, 13), width=random_source.randrange(1, 13),
                height=random_source.randrange(1, 11), mode=random_source.choice(('target', 'actor', 'viewport')),
                seed=random_source.randrange(255))
