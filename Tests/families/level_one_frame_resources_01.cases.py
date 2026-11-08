"""Original-only inputs for Level 1 frame and resource batch 1."""
from clawparity.cases import Case

COLOR, CLEAR, INSERT, MOVE, THREE, VISIT = (0x4D2140, 0x4D3C40, 0x4D4870, 0x4D4C70, 0x4D51F0, 0x4D5240)


def color_setup(depth, index, shifts, rgb, missing):
    def setup(env):
        r = env.object(0x148, 'color-receiver', fill=0xA7)
        a = env.object(0x1C, 'context', fill=0xB6)
        b = env.object(0x14, 'display-link', fill=0xC5)
        c = env.object(0x1C, 'display', fill=0xD4)
        d = env.object(0x68, 'resources', fill=0xE3)
        e = env.object(0x14, 'resource', fill=0x92)
        f = env.object(0x10, 'palette-link', fill=0x81)
        p = env.object(0x400, 'palette', fill=0x69)
        env.put(r + 0xC, a)
        env.put(r + 0x144, index & 0xFFFFFFFF)
        env.put(a + 4, b)
        env.put(b + 0x10, c)
        env.put(c + 0x18, depth)
        env.put(a + 0x18, d)
        env.put(d + 0x64, 0 if missing == 'resource' else e)
        env.put(e + 0x10, f)
        env.put(f + 0xC, 0 if missing == 'palette' else p)
        if 0 <= index <= 255:
            env.write(p + 4 * index, bytes((*rgb, 0xF1)))
        env.put(0x54135C, shifts[0], shifts[1])
        for address, value in zip((0x541368, 0x54136C, 0x541370), shifts[2:]):
            env.write(address, bytes((value,)))
        return r
    return setup


def scene(env, count=0, allocate=False):
    s = env.object(0x2C, 'scene', fill=0)
    env.put(s + 0x28, 4)
    free = [env.object(12, 'scene-free-node', fill=0x93) for _ in range(0 if allocate else count + 8)]
    for i, node in enumerate(free):
        env.put(node, free[i + 1] if i + 1 < len(free) else 0)
    env.put(s + 0x20, free[0] if free else 0)
    return s


def actor(env, flags=0, template_flags=0, depth=0):
    a = env.object(0x70, 'actor', fill=0xA9)
    t = env.object(12, 'template', fill=0x83)
    env.put(a + 8, flags)
    env.put(a + 0x64, depth & 0xFFFFFFFF)
    env.put(a + 0x6C, t)
    env.put(t + 8, template_flags)
    return a


def grid(env, payloads):
    g = env.object(0x44, 'grid', fill=0)
    cell = env.object(8, 'cell', fill=0)
    members = [env.object(0x1C, 'member', fill=0xBD) for _ in payloads]
    env.put(g + 8, len(members), 1)
    env.put(g + 0x40, cell)
    for i, (m, payload) in enumerate(zip(members, payloads)):
        env.put(m, members[i + 1] if i + 1 < len(members) else 0,
                members[i - 1] if i else 0, 0xA1370000 + i, cell, 0, 0, payload)
    env.put(cell, members[0] if members else 0, members[-1] if members else 0)
    return g, members


def clear_setup(count, base_result, mutate, seed):
    def setup(env):
        r = env.object(0x1CC, 'clear-receiver', fill=0xA6)
        context = env.object(0x28, 'base-context', fill=0)
        template = env.object(12, 'base-template', fill=0)
        table = env.object(0x28, 'base-vtable', fill=0)
        descriptor = env.object(0x14, 'descriptor', fill=0xB3)
        record = env.object(0x200, 'callback-observations', fill=0)
        env.put(r + 0xC, context)
        env.put(context + 0x24, 0x17395B7D)
        env.put(r + 0x6C, template)
        env.put(template, table)
        env.put(template + 8, seed & 3)
        env.put(descriptor + 8, 0x89ABCDEF)
        env.put(descriptor + 0x10, 0x13579BDF)
        nodes = [env.object(12, 'attached-node', fill=0) for _ in range(count)]
        objects = [env.object(8, 'attached-object', fill=0xD7) for _ in range(count)]
        dt = env.object(8, 'delete-vtable', fill=0)
        def destroy(env, call):
            n = env.get(record)
            env.put(record + 4 + n * 20, call.receiver, call.arguments[0],
                    env.get(r + 0x1B8), env.get(r + 0x1C0), env.get(r + 0x4C))
            env.put(record, n + 1)
            if mutate:
                for obj, node in zip(objects, nodes):
                    if call.receiver == obj:
                        env.put(node, 0)
            return 0xFEDCBA98
        env.put(dt + 4, env.stub('attached-destructor', 'thiscall', 1, destroy))
        for i, node in enumerate(nodes):
            env.put(objects[i], dt)
            env.put(node, nodes[i + 1] if i + 1 < count else 0, 0xF1030000 + i,
                    0 if i % 3 == 1 else objects[i])
        env.put(r + 0x1B8, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, count, 0)
        block = env.object(16, 'attached-block', fill=0x97) if count else 0
        if block:
            env.put(block, 0)
        env.put(r + 0x1C8, block)
        def initialize(env, call):
            env.put(record + 0x140, call.receiver, *call.arguments,
                    env.get(r + 0x1B8), env.get(r + 0x1BC), env.get(r + 0x1C0),
                    env.get(r + 0x1C4), env.get(r + 0x1C8), env.get(r + 0x4C), env.get(r + 0x50))
            if mutate:
                env.put(r + 0x4C, 0x3157799B, 0x2468ACE0)
            return base_result
        env.put(table + 0x24, env.stub('initialize-template', 'thiscall', 2, initialize))
        return r, descriptor
    return setup


def insert_setup(depth, existing_depths, allocation):
    def setup(env):
        s = scene(env, len(existing_depths), allocate=allocation)
        old = [actor(env, flags=0x20000 if i % 2 else 0, depth=d) for i, d in enumerate(existing_depths)]
        nodes = [env.object(12, 'existing-scene-node', fill=0) for _ in old]
        for i, node in enumerate(nodes):
            env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0, nodes[i - 1] if i else 0, old[i])
        env.put(s + 0x14, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
        a = actor(env, depth=depth)
        parent = env.object(12, 'parent', fill=0xC1)
        env.put(parent + 8, s)
        env.put(a + 0xC, parent)
        member = env.object(0x1C, 'member', fill=0xE7)
        env.put(member + 0x18, a)
        return member
    return setup


def move_setup(flags, switch_scene=False):
    def setup(env):
        s = scene(env, len(flags), allocate=switch_scene)
        r = env.object(4, 'scene-owner', words=[s])
        actors = [actor(env, a, t, d) for a, t, d in flags]
        g, members = grid(env, actors)
        if switch_scene:
            replacement = scene(env, len(flags))
            receipt = env.object(16, 'allocation-observation', fill=0)
            def allocate(env, call):
                env.put(receipt, env.get(r), call.arguments[0], env.get(g + 8), env.get(actors[0] + 0x68))
                env.put(r, replacement)
                return env.object(call.arguments[0], 'scene-block', fill=0)
            env.override(0x4F63EC, allocate)
        return r, g
    return setup


def visit_setup(lengths, mutate=False):
    def setup(env):
        r = env.object(16, 'three-grid-owner', fill=0xE5)
        receipt = env.object(0x400, 'visit-observations', fill=0)
        payloads = [[env.object(8, 'payload', words=[0x91372500 + j * 31 + i, 0xA27D0000 + i])
                     for i in range(n)] for j, n in enumerate(lengths)]
        grids = [grid(env, p) for p in payloads]
        while len(grids) < 3:
            grids.append(grid(env, []))
        env.put(r + 4, *(g for g, _ in grids[:3]))
        replacement, _ = grid(env, [0xA1357901, 0xCE246802])
        def callback(env, call):
            n = env.get(receipt)
            env.put(receipt + 4 + n * 24, call.receiver, call.arguments[0],
                    env.get(r + 4), env.get(r + 8), env.get(r + 12), env.get(grids[0][0] + 8))
            env.put(receipt, n + 1)
            if mutate:
                env.put(r + 8, replacement)
                env.put(r + 12, grids[0][0])
                first_members = grids[0][1]
                if len(first_members) > 1:
                    env.put(first_members[1] + 0x18, 0xB97531DF)
            return (0xFFFFFFFF - n) & 0xFFFFFFFF
        cb = env.stub('visit-callback', 'cdecl', 1, callback)
        return r, grids[0][0], cb
    return setup


def cases(random_source):
    shifts = (11, 5, 3, 2, 3)
    for depth in (8, 0, 15, 16, 24, 32, 0xFFFFFFFF):
        for index in (-1, 0, 1, 254, 255, 256, -0x80000000, 0x7FFFFFFF):
            yield Case(f'color depth={depth} index={index}', COLOR,
                       color_setup(depth, index, shifts, (0xD9, 0xA6, 0x73), None), receiver=lambda t: t)
    for missing in ('resource', 'palette'):
        yield Case(f'color null {missing}', COLOR, color_setup(16, 139, shifts, (1, 2, 3), missing), receiver=lambda t: t)
    for i in range(60):
        counts = tuple(random_source.choice((0, 1, 7, 8, 15, 16, 31, 32, 33, 63, 255)) for _ in range(5))
        rgb = tuple(random_source.randrange(256) for _ in range(3))
        yield Case(f'color randomized counts {i}', COLOR, color_setup(16, random_source.randrange(256), counts, rgb, None), receiver=lambda t: t)
    for count in (0, 1, 2, 5):
        for result in (0, 1, 0x80000000, 0xFFFFFFFF):
            yield Case(f'clear count={count} base-result={result}', CLEAR,
                       clear_setup(count, result, True, random_source.getrandbits(32)),
                       receiver=lambda t: t[0], arguments=(0x17395B7D, 0x82A4C6E8, 0xF13579BD, lambda t: t[1]))
    for depth in (-0x80000000, -1, 0, 1, 0x7FFFFFFF):
        for existing in ([], [-3, 0, 7], [9, -5, 12]):
            yield Case(f'insert depth={depth} existing={existing}', INSERT,
                       insert_setup(depth, existing, not existing), arguments=(lambda t: t,))
    for flags in ([], [(0, 0, 0)], [(2, 0, -1)], [(0, 4, 1)],
                  [(0, 0, 3), (2, 0, -2), (0, 4, 5), (0x80, 0x80, 4), (0xFF, 0xFF, 0)]):
        yield Case(f'move flags={flags}', MOVE, move_setup(flags), receiver=lambda t: t[0], arguments=(lambda t: t[1],))
    yield Case('move reloads scene after allocator changes receiver', MOVE,
               move_setup([(2, 0, 17), (0, 4, -3), (2, 0, 9)], True), receiver=lambda t: t[0], arguments=(lambda t: t[1],))
    for i in range(12):
        flags = [(random_source.randrange(256), random_source.randrange(256), random_source.randrange(-1000, 1000)) for _ in range(random_source.randrange(1, 9))]
        yield Case(f'move randomized {i}', MOVE, move_setup(flags), receiver=lambda t: t[0], arguments=(lambda t: t[1],))
    yield Case('three null callback does not dereference receiver', THREE, arguments=(0,))
    yield Case('empty visit permits null callback', VISIT, lambda env: grid(env, [])[0], arguments=(lambda t: t, 0))
    for lengths in ([0, 0, 0], [1, 0, 0], [0, 2, 3], [3, 1, 4]):
        yield Case(f'three lengths={lengths}', THREE, visit_setup(lengths), receiver=lambda t: t[0], arguments=(lambda t: t[2],))
        yield Case(f'visit first length={lengths[0]}', VISIT, visit_setup(lengths), arguments=(lambda t: t[1], lambda t: t[2]))
    yield Case('three reloads later grids after callback mutations', THREE, visit_setup([3, 1, 1], True), receiver=lambda t: t[0], arguments=(lambda t: t[2],))
    yield Case('visit reloads next payload after callback', VISIT, visit_setup([4], True), arguments=(lambda t: t[1], lambda t: t[2]))
