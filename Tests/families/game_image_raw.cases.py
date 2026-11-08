"""Independent original-derived cases for the raw, unflipped image entry."""
from clawparity.cases import Case
from clawparity.fixtures import halt

ENTRY = 0x4D32E0
COPYRECT = 0x546D58
STACK = 0x02008000


def draw(label, xy=(3, 4), size=(7, 6), branch='target', clip=(0, 0, 15, 14),
         target_size=(16, 15), flags=0, dispatcher_flags=0, projection=(0, 0, 0), mutation=None,
         reject=False, unlock_mutation=False, seed=37, halt_at=None, origins=(5, 7, 2, 3, 11, 13)):
    def setup(env):
        image = env.object(0x34, 'image', fill=0x31)
        actor = env.object(0x64, 'actor', fill=0x59)
        target = env.object(0x30, 'target', fill=0x63)
        owner = env.object(0x28, 'world owner', fill=0x72)
        world = env.object(0x20, 'world rectangle owner', fill=0x86)
        projection_owner = env.object(0x60, 'projection owner', fill=0x42)
        project = env.object(0x58, 'projection', fill=0)
        record = env.object(0x280, 'surviving callback observations', fill=0xAD)
        env.put(owner + 0x24, world)
        env.put(world + 0x10, *clip)
        env.put(projection_owner + 0x5C, project)
        px, py, wrap = projection
        env.put(project + 8, wrap)
        env.put(project + 0x30, 32, 29)
        env.put(project + 0x40, px, py, 80, 75, 2, 3)
        subx, suby, addx, addy, offx, offy = origins
        env.put(image + 0x0C, owner, *size, subx, suby, addx, addy)
        env.put(actor + 8, flags | (0x40000 if branch == 'world' else 0))
        env.put(actor + 0x10, xy[0] - addx - offx + subx,
                xy[1] - addy - offy + suby)
        env.put(actor + 0x3C, projection_owner, dispatcher_flags)
        env.put(actor + 0x4C, offx, offy)
        env.put(actor + 0x54, *(clip if branch == 'actor' else (0x80000000, 17, 18, 19)))
        env.put(target + 0x10, *target_size)

        def make_pid(index):
            pid = env.object(0x28, 'pid %d' % index, fill=0x27 + index)
            # Complete distinct literal rows; clipping can legally consume a whole run.
            stream = bytes(v for row in range(40) for v in
                           ([32] + [1 + ((seed + index * 53 + row * 17 + x * 7) % 254)
                                    for x in range(32)]))
            payload = env.object(len(stream), 'rle stream %d' % index, data=stream)
            env.put(pid + 4, 0 if reject else 32, 40, payload)
            env.put(pid + 0x14, 1)
            env.put(pid + 0x24, 1)
            return pid

        def make_surface(index):
            surface = env.object(0x34, 'surface %d' % index, fill=0x45 + index)
            dd = env.object(4, 'DD receiver %d' % index)
            vt = env.object(0x84, 'DD methods %d' % index)
            pixels = env.object(65536, 'padded pixels %d' % index, fill=0x91 + index)
            env.put(surface + 8, dd)
            env.put(surface + 0x1C, 128)
            env.put(surface + 0x30, pixels + 32768)
            env.put(dd, vt)

            def observe(env, call, offset):
                local_record = record + 0x180 + offset // 2
                env.write(local_record, env.read(STACK + 4, 4))
                env.write(local_record + 4, env.read(STACK - 0x50, 16))
                if branch == 'world' or flags & 0x40000:
                    env.write(local_record + 20, env.read(STACK - 0x30, 32))
                env.put(record + offset, call.receiver, *call.arguments)
                env.write(record + offset + 0x20, env.read(actor + 0x18, 0x24))
                env.write(record + offset + 0x48, env.read(STACK - 0x40, 16))
                env.write(record + offset + 0x58, env.read(STACK - 0x10, 16))

            def lock(env, call):
                observe(env, call, 0)
                if halt_at == 'lock':
                    return halt()(env, call)
                # Observe descriptor address and live pre-publication actor state.
                env.put(surface + 0x30, pixels + 32768)
                return 0

            def unlock(env, call):
                observe(env, call, 0x80)
                if halt_at == 'unlock':
                    return halt()(env, call)
                env.write(record + 0x100, env.read(pixels + 32768, 64))
                if unlock_mutation:
                    env.put(STACK - 0x40, 21, 23, 25, 27)
                    env.put(actor + 0x18, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9)
                return 0x887601C2

            env.put(vt + 0x64, env.stub('DD Lock %d' % index, 'stdcall', 5, lock))
            env.put(vt + 0x80, env.stub('DD Unlock %d' % index, 'stdcall', 2, unlock))
            return surface

        pids = [make_pid(0), make_pid(1)]
        surfaces = [make_surface(0), make_surface(1)]
        env.put(image + 0x30, pids[0])
        env.put(target + 0x2C, surfaces[0])

        def copy_rect(env, call):
            destination, source = call.arguments
            env.put(record + 0x140, call.receiver, destination, source)
            env.write(record + 0x14C, env.read(source, 16))
            env.write(record + 0x15C, env.read(STACK + 4, 4))
            env.write(record + 0x160, env.read(STACK - 0x50, 4))
            env.write(record + 0x164, env.read(STACK - 0x40, 16))
            env.write(record + 0x220, env.read(STACK - 0x4C, 12))
            if halt_at == 'copy':
                return halt()(env, call)
            env.write(destination, env.read(source, 16))
            if mutation == 'reload':
                env.put(image + 0x30, pids[1])
                env.put(target + 0x2C, surfaces[1])
            elif mutation == 'geometry':
                env.put(image + 0x10, 1, 2)
                env.put(actor + 8, 0xFFFFFFFF)
                env.put(world + 0x10, 40, 41, 42, 43)
                env.put(target + 0x10, 2, 3)
            elif mutation == 'output':
                env.put(destination, 2, 3, 8, 9)
            return 0  # CopyRect BOOL is ignored.

        env.override(COPYRECT, copy_rect)
        return dict(image=image, actor=actor, target=target)
    return Case(label, ENTRY, setup, receiver=lambda t: t['image'],
                arguments=(lambda t: t['actor'], lambda t: t['target']),
                expect='halt' if halt_at else 'return')


def cases(random_source):
    # Equality and one-step boundaries on every inclusive clipping axis.
    for branch in ('target', 'actor', 'world'):
        for x in (-1, 0, 1, 8, 9, 10, 15, 16):
            yield draw('%s x=%d' % (branch, x), xy=(x, 4), branch=branch,
                       clip=(0, 0, 15, 14), projection=(2, 3, 0))
        for y in (-1, 0, 1, 8, 9, 10, 14, 15):
            yield draw('%s y=%d' % (branch, y), xy=(3, y), branch=branch,
                       clip=(0, 0, 15, 14), projection=(2, 3, 0))
        yield draw(branch + ' all four sides clipped', xy=(-2, -3), size=(23, 22),
                   branch=branch, projection=(2, 3, 0))
        for size in ((0, 6), (7, 0), (-1, 6), (7, -1), (1, 1)):
            yield draw('%s size %r' % (branch, size), size=size, branch=branch,
                       projection=(2, 3, 0))
    for flag in (1, 2, 4, 8, 0x10, 0x20, 0x100, 0x80000000, 0xFFFFFFFF):
        yield draw('direct actor flags %#x' % flag, flags=flag)
    for dispatcher_flags in (1, 2, 4, 6, 8, 0x10000008, 0x10000000, 0x1000000F):
        yield draw('direct dispatcher flags %#x' % dispatcher_flags,
                   dispatcher_flags=dispatcher_flags)
    for mutation in ('reload', 'geometry', 'output'):
        yield draw('CopyRect mutation ' + mutation, branch='world', mutation=mutation,
                   projection=(2, 3, 0), unlock_mutation=True)
    yield draw('post-pixel destination mutation', unlock_mutation=True)
    yield draw('real blit rejection still publishes actor', reject=True)
    for xy in ((-1, -1), (32, 29), (31, 28), (0, 0), (33, 30)):
        yield draw('real wrapped projection %r' % (xy,), branch='world', xy=xy,
                   projection=(4, 5, 12), clip=(-10, -10, 60, 60))
    for branch in ('actor', 'world'):
        for clip in ((4, 5, 8, 9), (3, 4, 9, 9), (4, 4, 9, 9), (3, 5, 9, 9),
                     (3, 4, 8, 9), (3, 4, 9, 8), (40, 0, 45, 10), (0, 40, 10, 45),
                     (-30, -31, -20, -21)):
            yield draw('%s clip %r' % (branch, clip), branch=branch, clip=clip,
                       projection=(2, 3, 0))
    for i in range(24):
        branch = random_source.choice(('target', 'actor', 'world'))
        xy = (random_source.randrange(-5, 20), random_source.randrange(-5, 20))
        size = (random_source.randrange(1, 14), random_source.randrange(1, 12))
        yield draw('random %d %s' % (i, branch), branch=branch, xy=xy, size=size,
                   seed=random_source.randrange(1, 255), projection=(2, 3, 0))
    for service in ('copy', 'lock', 'unlock'):
        yield draw('physical halt at ' + service, branch='world', halt_at=service,
                   projection=(2, 3, 0))
    # Arithmetic wraps first; signed clipping then safely rejects distant extents.
    for x in (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield draw('wrapped coordinate %#x' % x, xy=(x, 4), reject=True)
