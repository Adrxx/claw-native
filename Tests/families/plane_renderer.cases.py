"""Original-only plane and actor drawing cases; physical COM methods observe draws."""
from clawparity.cases import Case

LIST = 0x4C91D0
ACTOR = 0x4C9E00
WORLD = 0x4CB9B0
PLANE = 0x4D0D50
FILL = 0xEEEEEEEE
EMPTY = 0xFFFFFFFF


def recorder(env):
    log = env.object(32768, 'surviving callback observations', fill=0)

    def record(env, values):
        index = env.get(log)
        env.put(log + 4 + index * 128, *values)
        env.put(log, index + 1)
        return index

    return record


def plane(env, context, record, tag, mode='frames', viewport=(3, 5, 52, 57),
          dimensions=(8, 8), shifts=(4, 4), mutate=None, tile_size=(16, 16)):
    obj = env.object(0x160, f'plane {tag}', fill=(tag % 251) + 1)
    tiles = env.object(2048, f'tiles {tag}')
    alternate = env.object(2048, f'alternate tiles {tag}')
    # Backing permits negative starting coordinates as well as positive wraps.
    rows_base = env.object(256, f'row offsets {tag}')
    rows = rows_base + 64
    for row in range(-16, 48):
        env.put(rows + row * 4, 128 + row * 8)
    sets = env.object(12, f'tilesets {tag}')
    wrappers = []
    for set_index in range(3):
        tile_set = env.object(0x6c, f'tileset {tag}/{set_index}', fill=0x53 + set_index)
        frames = env.object(32, f'frames {tag}/{set_index}')
        env.put(tile_set + 0x14, frames)
        env.put(tile_set + 0x64, 1, 6)
        env.put(sets + set_index * 4, tile_set)
        for frame_index in range(8):
            frame = env.object(0x30, f'frame {tag}/{set_index}/{frame_index}', fill=0x21 + frame_index)
            wrapper = env.object(12, f'source wrapper {tag}/{set_index}/{frame_index}', fill=0x37)
            surface = env.object(4, f'source surface {tag}/{set_index}/{frame_index}')
            env.put(wrapper + 8, surface)
            env.put(frame + 0x28, 0x101 + set_index * 0x10 + frame_index, wrapper)
            env.put(frames + frame_index * 4, frame)
            wrappers.append(wrapper)
    for index in range(512):
        word = (index % 3) << 16 | (1 + index % 6)
        if mode == 'fill':
            word = FILL
        elif mode == 'empty':
            word = EMPTY
        elif mode == 'mixed':
            word = (word, FILL, EMPTY)[index % 3]
        env.put(tiles + index * 4, word)
        env.put(alternate + index * 4, ((index + 1) % 3) << 16 | (1 + (index + 2) % 6))
    env.put(obj + 8, 0xA0)
    env.put(obj + 0x20, tiles, rows, *dimensions)
    env.put(obj + 0x38, *tile_size, *viewport, 23 + tag, 41 + tag)
    env.put(obj + 0x60, 2, 3, 15, 14)
    env.put(obj + 0x8c, *shifts)
    env.put(obj + 0xa0, sets)
    # Physical COM callbacks record dereferenced rectangles, not merely stack pointers.
    methods = env.object(32, f'COM methods {tag}')
    surface = env.object(4, f'destination surface {tag}', words=[methods])
    wrapper = env.object(12, f'destination wrapper {tag}', fill=0x45)
    env.put(wrapper + 8, surface)
    counter = env.object(4, f'COM counter {tag}', fill=0)

    def observe(env, call, fill):
        a = call.arguments
        rect = a[1] if fill else a[4]
        values = [tag, int(fill), call.receiver, *a, *[env.get(rect + i * 4) for i in range(4)]]
        if fill:
            values += [env.get(a[5] + i * 4) for i in range(4)]
        record(env, values)
        n = env.get(counter)
        env.put(counter, n + 1)
        if mutate and n == 0:
            if mutate == 'geometry':
                env.put(obj + 0x38, 19, 21)
                env.put(obj + 0x50, 87 + tag)
                env.put(obj + 0x60, 4, 5, 18, 20)
                env.put(obj + 0x28, 2, 2)
            elif mutate == 'arrays':
                env.put(obj + 0x20, alternate)
                env.put(rows + 4, 152)
            elif callable(mutate):
                mutate(env, obj)
        return 0

    env.put(methods + 0x14, env.stub(f'Blt {tag}', 'stdcall', 6, lambda e, c: observe(e, c, True)))
    env.put(methods + 0x1c, env.stub(f'BltFast {tag}', 'stdcall', 6, lambda e, c: observe(e, c, False)))
    env.put(context + 0x2c, wrapper)
    return obj


def plane_setup(**options):
    def setup(env):
        record = recorder(env)
        context = env.object(0x30, 'drawing context', fill=0x69)
        obj = plane(env, context, record, 7, **options)
        return {'receiver': obj, 'context': context}
    return setup


def actors(env, record, depths, mutate=None, nested=False):
    head = 0
    nodes = []
    objs = []
    for i, depth in enumerate(depths):
        obj = env.object(0x178, f'actor {i}', fill=0x31 + i)
        table = env.object(0x30, f'actor methods {i}')
        node = env.object(12, f'actor node {i}', fill=0x63 + i)
        env.put(obj, table)
        env.put(obj + 0x64, depth)
        env.put(node, 0)
        env.put(node + 8, obj)
        if nodes:
            env.put(nodes[-1], node)
        else:
            head = node
        nodes.append(node)
        objs.append(obj)

        def draw(env, call, i=i):
            record(env, [0xAC70 + i, call.receiver, *call.arguments, env.get(objs[i] + 0x64)])
            if mutate:
                mutate(env, nodes, objs, i)
            return 0x7ABC0000 + i

        if nested:
            service = env.object(12, f'actor drawing service {i}', fill=0x79 + i)
            service_table = env.object(0x3c, f'actor service methods {i}')
            env.put(service, service_table)
            env.put(obj + 0x174, service)

            def service_draw(env, call, i=i):
                record(env, [0x5E700 + i, call.receiver, *call.arguments,
                             env.get(objs[i] + 0x174), env.get(objs[i] + 0x64)])
                if mutate:
                    mutate(env, nodes, objs, i)
                return 0x61A00000 + i
            env.put(service_table + 0x38, env.stub(f'nested drawing service {i}', 'thiscall', 2, service_draw))
            env.put(table + 0x2c, ACTOR)
        else:
            env.put(table + 0x2c, env.stub(f'actor draw {i}', 'thiscall', 1, draw))
    return head, nodes, objs


def list_setup(depths, change=False, nested=False):
    def setup(env):
        record = recorder(env)
        obj = env.object(0x18, 'actor list', fill=0x73)
        context = env.object(0x30, 'drawing context', fill=0x6B)

        def mutate(env, nodes, objs, i):
            env.put(nodes[i], 0)
            if i + 1 < len(objs):
                env.put(objs[i + 1] + 0x64, 0x12345 + i)
        head, _, _ = actors(env, record, depths, mutate if change else None, nested=nested)
        env.put(obj + 0x14, head)
        return {'receiver': obj, 'context': context}
    return setup


def actor_setup(service):
    def setup(env):
        record = recorder(env)
        obj = env.object(0x178, 'generic actor', fill=0x43)
        context = env.object(0x30, 'drawing context', fill=0x17)
        env.put(obj + 0x174, 0)
        if service:
            target = env.object(8, 'drawing service', fill=0x67)
            table = env.object(0x3c, 'service methods')
            env.put(target, table)

            def draw(env, call):
                record(env, [call.receiver, *call.arguments, env.get(obj + 0x174)])
                env.put(obj + 0x174, 0)
                return 0xF1234567
            env.put(table + 0x38, env.stub('service actor draw', 'thiscall', 2, draw))
            env.put(obj + 0x174, target)
        return {'receiver': obj, 'context': context}
    return setup


def world_setup(flags=1, count=4, insertion=1, depths=(-10, 0, 20, 20, 80),
                first_null=False, mutation=None, nested=False):
    def setup(env):
        record = recorder(env)
        world = env.object(0x64, 'world', fill=0x61)
        context = env.object(0x30, 'drawing context', fill=0x47)
        lst = env.object(0x18, 'world actor list', fill=0x37)
        table = env.object(0x2c, 'world list methods')
        pointers = env.object(32, 'world plane pointers')
        alternate = env.object(32, 'alternate plane pointers')
        env.put(world + 8, flags)
        env.put(world + 0x38, pointers, count)
        env.put(world + 0x60, insertion)
        planes = []

        def plane_change(env, obj):
            if mutation == 'plane-controls':
                env.put(world + 0x60, 0)
                env.put(world + 0x3c, 3)
                env.put(world + 0x38, alternate)
            elif mutation == 'publish-head':
                env.put(lst + 0x14, extra_head)
        for i in range(5):
            p = plane(env, context, record, 20 + i, mode='fill', viewport=(1, 2, 18, 19),
                      mutate=plane_change if i == 0 and mutation in ('plane-controls', 'publish-head') else None)
            env.put(p + 0x80, (-30, 0, 20, 40, 60)[i])
            planes.append(p)
            env.put(pointers + i * 4, p)
        for i, p in enumerate(reversed(planes)):
            env.put(alternate + i * 4, p)
        if first_null:
            env.put(pointers, 0)

        def actor_change(env, nodes, objs, i):
            env.put(nodes[i], 0)
            if mutation == 'actor-array':
                env.put(world + 0x38, alternate)
            if i + 1 < len(objs):
                env.put(objs[i + 1] + 0x64, 100 if i % 2 else -20)
        head, _, _ = actors(env, record, depths, actor_change if mutation == 'actor-array' else None, nested=nested)
        extra_head, _, _ = actors(env, record, (13, 61), nested=nested)
        env.put(lst, table)
        env.put(lst + 0x14, head)

        def list_draw(env, call):
            record(env, [0x1157, call.receiver, *call.arguments, env.get(world + 0x60), env.get(world + 0x3c)])
            if mutation == 'list-controls':
                env.put(world + 0x60, 0)
                env.put(world + 0x3c, 3)
                env.put(world + 0x38, alternate)
            return 0
        env.put(table + 0x28, LIST if nested else env.stub('world list draw', 'thiscall', 1, list_draw))
        return {'receiver': world, 'context': context, 'list': lst}
    return setup


def cases(random_source):
    for size in (0, 1, 4):
        yield Case(f'list {size} nodes', LIST, list_setup(tuple(range(size))),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    yield Case('list captures next before mutating draw', LIST, list_setup((3, 7, 11), True),
               receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    yield Case('list calls generic actor owned method and physical service', LIST,
               list_setup((-17, 0, 59), True, nested=True),
               receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    for present in (False, True):
        yield Case(f'generic actor service {present}', ACTOR, actor_setup(present),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    yield Case('plane skip flag', PLANE, lambda e: {'receiver': e.object(12, 'skipped plane', words=[17, 29, 2])},
               receiver=lambda t: t['receiver'], arguments=(0xAABBCCDD,))
    for mode in ('frames', 'fill', 'empty', 'mixed'):
        for dimensions in ((8, 8), (2, 2), (1, 1)):
            yield Case(f'plane {mode} wrap {dimensions}', PLANE,
                       plane_setup(mode=mode, dimensions=dimensions),
                       receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    for viewport in ((3, 5, 8, 9), (3, 5, 20, 21), (3, 5, 36, 37),
                     (-13, -11, 36, 37), (19, 21, 4, 6), (0, 0, 48, 48)):
        yield Case(f'plane viewport {viewport}', PLANE, plane_setup(viewport=viewport, mode='mixed'),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    for mode in ('frames', 'fill'):
        for mutation in ('geometry', 'arrays'):
            yield Case(f'plane callback changes {mutation} {mode}', PLANE,
                       plane_setup(mode=mode, mutate=mutation),
                       receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    for shifts in ((36, 36), (0, 0), (33, 33)):
        yield Case(f'plane masked shifts {shifts}', PLANE,
                   plane_setup(shifts=shifts, viewport=(0, 0, 3, 3), mode='frames'),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    for dimensions, shifts, tile_size, viewport in (
            ((3, 7), (3, 5), (8, 32), (11, 37, 45, 141)),
            ((7, 3), (5, 3), (32, 8), (71, 11, 205, 45)),
            ((2, 5), (2, 4), (4, 16), (5, 19, 21, 85)),
            ((5, 2), (4, 2), (16, 4), (19, 5, 85, 21)),
            ((3, 7), (35, 37), (11, 41), (11, 37, 45, 141))):
        for mode in ('frames', 'fill', 'mixed'):
            yield Case(f'non-square plane {dimensions} {shifts} {mode}', PLANE,
                       plane_setup(dimensions=dimensions, shifts=shifts,
                                   tile_size=tile_size, viewport=viewport, mode=mode),
                       receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    for i in range(8):
        left, top = random_source.randrange(0, 20), random_source.randrange(0, 20)
        viewport = (left, top, left + random_source.randrange(0, 65), top + random_source.randrange(0, 65))
        yield Case(f'random plane {i} {viewport}', PLANE,
                   plane_setup(viewport=viewport, mode=('mixed', 'frames', 'fill')[i % 3]),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'],))
    worlds = [dict(), dict(count=1), dict(count=1, depths=()), dict(depths=()),
              dict(depths=(-80, -50, -40)), dict(depths=(0, 20, 40, 60)),
              dict(count=0, insertion=-1), dict(count=-1, insertion=-1),
              dict(first_null=True, insertion=-1, mutation='list-controls'),
              dict(flags=0, insertion=-1), dict(flags=0, insertion=0),
              dict(flags=0, insertion=3), dict(flags=0, count=0, insertion=-1),
              dict(flags=0, mutation='list-controls'), dict(flags=0, mutation='plane-controls'),
              dict(mutation='publish-head'), dict(mutation='actor-array'),
              dict(nested=True), dict(flags=0, nested=True),
              dict(flags=0, nested=True, insertion=-1),
              dict(nested=True, mutation='actor-array')]
    for i, options in enumerate(worlds):
        yield Case(f'world {i} {options}', WORLD, world_setup(**options),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['context'], lambda t: t['list']))
