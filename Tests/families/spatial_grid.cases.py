"""Independent original-only spatial grid cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW = 0x4F63EC


def record(env, name, convention, argc, effect=None):
    log = env.object(4096, name + '-observations', fill=0)
    def callback(env, call):
        n = env.get(log)
        at = log + 4 + n * 64
        env.put(log, n + 1)
        env.put(at, call.receiver, *call.arguments)
        if call.receiver:
            env.write(at + 24, env.read(call.receiver, min(24, 0x18)))
        if effect:
            return effect(env, call, at)
        return 0xBAD00000 | n
    return env.stub(name, convention, argc, callback)


def platform(env, fail_call=0, fail_size=0, mutate=None):
    def alloc(env, call):
        if (fail_call and env.calls_so_far(NEW) == fail_call) or call.arguments[0] == fail_size:
            return 0
        result = env.object(call.arguments[0], 'original-allocation', fill=0)
        if mutate:
            mutate(env, call)
        return result
    env.override(NEW, alloc)
    def rect(env, call):
        env.put(call.arguments[0], *call.arguments[1:])
        return 0xFEED
    env.override(0x546D5C, rect)
    env.override(0x5469E4, lambda env, call: len(env.cstr(call.arguments[0])))
    def decrement(env, call):
        p = call.arguments[0]
        v = (env.get(p) - 1) & 0xFFFFFFFF
        env.put(p, v)
        return v
    env.override(0x5469E8, decrement)


def grid(env, points=(), forced_cell=None, callback=None):
    g = env.object(0x44, 'grid', fill=0)
    table = env.object(0x18, 'grid-vtable', fill=0)
    payload = env.object(4 + 16 * 8, 'grid-cell-array', fill=0)
    env.put(payload, 16)
    env.put(g, table, 1, len(points), 4, 4, 4, 4, 16, 63, 63, 0, 0, 63, 63, 16, 16, payload + 4)
    env.put(table + 4, record(env, 'grid-delete', 'thiscall', 1))
    env.put(table + 0x14, callback or record(env, 'query', 'thiscall', 1))
    nodes = []
    for i, (x, y) in enumerate(points):
        p = env.object(0x1C, 'link', fill=0)
        cell = forced_cell if forced_cell is not None else ((y >> 4) * 4 + (x >> 4))
        head = payload + 4 + 8 * cell
        old = env.get(head)
        env.put(p, 0, old, 0xCAFE0000 + i, head, x, y, 0)
        if old:
            env.put(old, p)
        else:
            env.put(head, p)
        env.put(head + 4, p)
        nodes.append(p)
    return g, nodes


def entity(env, flags=0, xy=(31, 31), change_event=False):
    e = env.object(0xA4, 'entity', fill=0)
    logic = env.object(0x20, 'logic', fill=0)
    vt = env.object(8, 'entity-vtable')
    def event(env, call, at):
        obj = call.arguments[0]
        lp = env.get(obj + 0x6C)
        env.put(at + 40, env.get(lp + 0x1C), env.get(obj + 8), env.get(obj + 0x94))
        if change_event:
            env.put(lp + 0x1C, 73)
        return 0xBEEF
    env.put(logic + 0x10, record(env, 'logic-event', 'cdecl', 1, event))
    env.put(logic + 0x1C, 91)
    env.put(vt + 4, record(env, 'entity-delete', 'thiscall', 1))
    env.put(e, vt)
    env.put(e + 8, flags)
    env.put(e + 0x4C, *xy)
    env.put(e + 0x6C, logic)
    env.put(e + 0x98, *xy)
    env.put(e + 0xA0, e)
    return e


def manager(env, active=(), points=(), nullable=0):
    m = env.object(0x70, 'manager', fill=0)
    container = env.object(0x28, 'active-container', fill=0)
    gs = [grid(env, points)[0] for _ in range(3)]
    env.put(m, container, *(0 if nullable & (1 << i) else g for i, g in enumerate(gs)))
    env.put(m + 0x40, 4, 5, 7, 8, 10, 11)
    env.put(m + 0x58, 0, 0, 63, 63, 999, 998)
    nodes = []
    for flags, xy, change in active:
        e = entity(env, flags, xy, change)
        node = env.object(12, 'active-node', words=[0, nodes[-1] if nodes else 0, e])
        if nodes:
            env.put(nodes[-1], node)
        nodes.append(node)
    env.put(container + 0x14, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes), 0, 0)
    return m, gs


def plane(env, null_manager=False, null_config=False, dims=(32, 24), active=(), coordinates=(15.75, -8.25)):
    m, gs = manager(env, active)
    p = env.object(0xB4, 'plane')
    w = env.object(0x28, 'world')
    cfg = env.object(0xE0, 'configuration', fill=0xA6)
    env.put(cfg + 0xB0, 8, 8, 16, 16, 4, 4, 9, 11, 17, 19, 25, 27)
    env.put(w + 8, env.get(m))
    env.put(w + 0x24, 0 if null_config else cfg)
    env.put(p + 0xC, w)
    env.write(p + 0x10, struct.pack('<ff', *coordinates))
    env.put(p + 0x30, *dims)
    env.put(p + 0xB0, 0 if null_manager else m)
    return {'r': p, 'm': m, 'g': gs, 'cfg': cfg, 'w': w}


def case(label, f, setup, args=()):
    return Case(label, f, setup, receiver=lambda t: t['r'], arguments=args)


def cases(random_source):
    for width, height in [(0, 1), (1, 0), (-1, -7), (0x80000000, 0x7FFFFFFF), (640, 480)] + [(random_source.randrange(-4000, 4000), random_source.randrange(-4000, 4000)) for _ in range(4)]:
        yield case(f'default values {width} {height}', 0x4CB040, lambda env: {'r': env.object(0xE0, 'config', fill=0xB3)}, (width, height))
    for offset in (None, 0xC, 0x10, 0x14, 0x18):
        def setup(env, offset=offset):
            r = env.object(0xE0, 'configuration', words=list(range(101, 157)))
            q = env.object(16, 'rectangle', words=[0xFFFFFFFF, 17, 109, 0x80000000]) if offset is None else r + offset
            return {'r': r, 'q': q}
        yield case(f'copy rectangle alias {offset}', 0x4CB0E0, setup, (lambda t: t['q'],))
    for rect in [(0, 0, 63, 47), (63, 47, 0, 0), (-30, 41, 25, -9), (0, 0, 0, 0)]:
        for size in [(1, 1), (2, 3), (7, 8), (15, 17), (32, 33)]:
            def setup(env):
                platform(env)
                return {'r': env.object(0x44, 'grid', fill=0x72)}
            yield case(f'initialize grid {rect} {size}', 0x4F4490, setup, rect + size)
    yield case('initialize grid allocation failure', 0x4F4490, lambda env: (platform(env, fail_call=1) or {'r': env.object(0x44, 'grid', fill=0x34)}), (0, 0, 31, 47, 8, 16))
    for initialized, payload in [(0, False), (1, False), (1, True)]:
        def setup(env, initialized=initialized, payload=payload):
            g, _ = grid(env)
            env.put(g + 4, initialized)
            if not payload:
                env.put(g + 0x40, 0)
            else:
                env.put(g + 0x1C, 3)  # destruction uses allocation prefix, not this field
            return {'r': g}
        yield case(f'cleanup {initialized} {payload}', 0x4F45F0, setup)
    for flags in (0, 1, 2, 0x101):
        yield case(f'deleting grid destructor {flags}', 0x4D4A90, lambda env: {'r': grid(env)[0]}, (flags,))
    for xy in [(0, 0), (15, 16), (63, 63), (31, 47)]:
        for existing in (False, True):
            def setup(env, xy=xy, existing=existing):
                g, nodes = grid(env, [xy] if existing else [])
                n = env.object(0x1C, 'insert-link', words=[0x111, 0x222, 0x333, 0x444, *xy, 0x555])
                return {'r': g, 'n': n}
            yield case(f'insert {xy} existing {existing}', 0x4F4630, setup, (lambda t: t['n'],))
    for index in range(3):
        def setup(env, index=index):
            g, ns = grid(env, [(3, 3), (4, 4), (5, 5)])
            return {'r': g, 'n': ns[index]}
        yield case(f'unlink node position {index}', 0x4F4680, setup, (lambda t: t['n'],))
    rects = [(64, 0, 70, 2), (-8, 0, -1, 9), (0, 64, 2, 70), (0, -8, 9, -1), (-5, -5, 70, 70), (0, 0, 63, 63), (8, 8, 7, 7), (24, 8, 7, 23), (8, 24, 23, 7), (16, 16, 31, 31), (7, 7, 10, 10)]
    for rect in rects:
        for remove in (0, 1):
            def setup(env):
                g, _ = grid(env, [(0, 0), (7, 7), (8, 8), (10, 10), (11, 11), (31, 31), (63, 63)])
                return {'r': g}
            yield case(f'query {rect} remove {remove}', 0x4F46B0, setup, rect + (remove,))
    # Put distinct rejected coordinates into a scanned cell to isolate each per-node comparison.
    for point in [(6, 8), (8, 6), (11, 8), (8, 11), (7, 10), (10, 7)]:
        yield case(f'query node bounds {point}', 0x4F46B0, lambda env, point=point: {'r': grid(env, [point], forced_cell=0)[0]}, (7, 7, 10, 10, 0))
    for rect in rects[:6] + [(16, 16, 31, 31), (8, 8, 7, 7)]:
        for remove in (0, 1):
            def setup(env, rect=rect):
                # Empty scan is safe even for inverted rectangles.
                g, _ = grid(env)
                return {'r': env.object(0x44, 'iterator', fill=0x5A), 'g': g}
            yield case(f'iterator rectangle {rect} {remove}', 0x4F48A0, setup, (lambda t: t['g'],) + rect + (remove,))
    for f in (0x4F4860, 0x4F48A0, 0x4F49C0):
        for remove in (0, 1):
            for cell in (0, 1, 5, 15, None):
                def setup(env, remove=remove, cell=cell):
                    pts = [] if cell is None else [((cell % 4) * 16, (cell // 4) * 16)]
                    g, ns = grid(env, pts)
                    it = env.object(0x44, 'iterator', fill=0)
                    env.put(it + 4, g, 0, ns[0] if cell == 0 else 0, 0, 0, 63, 63, 0, 0, 3, 3, 0, 0, 0, 0, remove)
                    return {'r': it, 'g': g}
                args = () if f == 0x4F49C0 else ((lambda t: t['g'], remove) if f == 0x4F4860 else (lambda t: t['g'], 0, 0, 63, 63, remove))
                yield case(f'iterator entry {f:x} cell {cell} {remove}', f, setup, args)
    for f in (0x4D1FD0, 0x4D2000, 0x4D2030, 0x4D2050):
        for null in (False, True):
            yield case(f'plane wrapper {f:x} null {null}', f, lambda env, null=null: plane(env, null_manager=null))
    for dims in [(9, 11, 17, 19, 25, 27), (-3, -5, -7, -9, -11, -13), (0, 1, 2, 3, 0x80000000, 0x7FFFFFFF)]:
        def setup(env, dims=dims):
            t = plane(env)
            env.put(t['cfg'] + 0xC8, *dims)
            return t
        yield case(f'plane configuration halves {dims}', 0x4D2050, setup)
    yield case('plane null configuration', 0x4D2050, lambda env: plane(env, null_config=True))
    for flags in (0, 0x800000, 0x1000000, 0x1800000):
        def setup(env, flags=flags):
            m, _ = manager(env)
            return {'r': m, 'e': entity(env, flags, (47, 16))}
        yield case(f'entity grid selection {flags:x}', 0x4D51A0, setup, (lambda t: t['e'],))
    for nullable in range(8):
        for f in (0x4D4B00, 0x4D50E0):
            yield case(f'nullable aggregate {f:x} mask {nullable}', f, lambda env, nullable=nullable: {'r': manager(env, nullable=nullable)[0]})
    for f in (0x4D4C40, 0x4D4B50, 0x4D4D10):
        args = () if f == 0x4D4C40 else (31, 31)
        yield case(f'empty manager entry {f:x}', f, lambda env: {'r': manager(env)[0]}, args)
    for xy in [(999, 998), (999, 31), (31, 998), (31, 31)]:
        yield case(f'manager cached center {xy}', 0x4D4B50, lambda env: {'r': manager(env, points=[(31, 31)])[0]}, xy)
    for selection in (0, 0x800000, 0x1000000, 0x1800000):
        for xy in [(31, 31), (0, 31), (31, 0), (63, 31), (31, 63), (-1, -1), (70, 70)]:
            for extra in (0, 0x100000, 0x100020, 0x80020):
                flags = 0x40000 | selection | extra
                active = [(flags, xy, False), (flags | 0x100000, xy, True)]
                yield case(f'active flags {flags:x} xy {xy}', 0x4D4D10, lambda env, active=active: {'r': manager(env, active=active)[0]}, (31, 31))
    for center in [(-321, 31), (384, 31), (31, -221), (31, 284), (31, 31)]:
        for extra in (0, 0x80000):
            active = [(0x40 | 2 | extra, (19, 23), False)]
            yield case(f'active cull center {center} event {extra}', 0x4D4D10, lambda env, active=active: {'r': manager(env, active=active)[0]}, center)
    yield case('active flag skip without process', 0x4D4D10, lambda env: {'r': manager(env, active=[(0, (19, 23), False), (2 | 0x40000, (29, 33), False)])[0]}, (31, 31))
    for fail in (0, 1, 2, 3, 4, 5, 6):
        def setup(env, fail=fail):
            platform(env, fail_call=fail)
            m = env.object(0x70, 'manager', fill=0x7A)
            obj = env.object(0x28, 'container')
            rect = env.object(16, 'world-rectangle', words=[-8, -16, 55, 47])
            pairs = [env.object(8, f'pair-{i}', words=pair) for i, pair in enumerate([(4, 8), (8, 16), (16, 4), (9, -11), (-17, 19), (25, -27)])]
            return {'r': m, 'a': (obj, rect, *pairs)}
        yield case(f'manager initialization allocation {fail}', 0x4D4890, setup, tuple(lambda t, i=i: t['a'][i] for i in range(8)))
    yield case('manager null container leaves receiver', 0x4D4890, lambda env: {'r': env.object(0x70, 'manager', fill=0x87)}, (0,) * 8)
    for mode in ('null-buffer', 'null-container', 'null-config', 'zero-count', 'negative-count', 'grid-fail', 'parse-fail', 'parse-two'):
        def setup(env, mode=mode):
            t = plane(env, null_manager=mode != 'null-container', null_config=mode == 'null-config')
            if mode == 'null-container':
                env.put(t['w'] + 8, 0)
            platform(env, fail_call=5 if mode == 'grid-fail' else 0, fail_size=0x1B4 if mode == 'parse-fail' else 0)
            b = env.object(0x238, 'records', fill=0)
            for offset in (0, 0x11C):
                env.put(b + offset, 11, 0, 0, 0, 0, 999, 999, 0, 0)
            empty = env.object(16, 'shared-empty', words=[0xFFFFFFFF, 0, 0, 0])
            env.put(0x52E1CC, empty + 12)
            env.put(0x52E1C8, empty)
            env.put(0x5137F4, record(env, 'parsed-entity-delete', 'thiscall', 1))
            t['b'] = 0 if mode == 'null-buffer' else b
            return t
        count = 2 if mode == 'parse-two' else (1 if mode == 'parse-fail' else (-3 if mode == 'negative-count' else 0))
        yield case(f'plane initialization {mode}', 0x4D1620, setup, (lambda t: t['b'], count))
    for _ in range(12):
        x, y = random_source.randrange(64), random_source.randrange(64)
        rx, ry = random_source.randrange(8), random_source.randrange(8)
        yield case(f'random query center {x} {y} radii {rx} {ry}', 0x4F46B0, lambda env, x=x, y=y: {'r': grid(env, [(x, y), ((x + 1) % 64, (y + 1) % 64)])[0]}, (x-rx, y-ry, x+rx, y+ry, random_source.randrange(2)))
    for f in (0x4D4C40, 0x4D50E0):
        def setup(env, f=f):
            platform(env)
            m, gs = manager(env)
            container = env.get(m)
            # Give original active-list insertion a ready free node.
            free = env.object(12, 'free-active-node', words=[0, 0, 0])
            env.put(container + 0x20, free)
            for i, g in enumerate(gs):
                e = entity(env, 2 if f == 0x4D4C40 else 0, (i * 16, i * 16))
                n = e + 0x88
                cell = env.get(g + 0x40) + i * 5 * 8
                env.put(cell, n, n)
                env.put(n, 0, 0, 0x12340000 + i, cell, i * 16, i * 16, e)
                env.put(g + 8, 1)
            # Three collector moves need three free nodes.
            next_free = free
            for i in range(2):
                n = env.object(12, 'free-active-node', words=[0, 0, 0])
                env.put(next_free, n)
                next_free = n
            return {'r': m}
        yield case(f'nonempty original aggregate {f:x}', f, setup)
    def cleanup_mutation(env):
        m, gs = manager(env)
        replacement, _ = grid(env)
        def change(env, call, at):
            env.put(at + 48, env.get(m + 4), env.get(m + 8), env.get(m + 12))
            env.put(m + 4, replacement)
            env.put(m + 8, 0)
            env.put(m + 12, replacement)
            return 0xFFFFFFFF
        env.put(env.get(gs[0]) + 4, record(env, 'cleanup-mutates-manager', 'thiscall', 1, change))
        return {'r': m}
    yield case('cleanup re-reads later grid pointers and clears current slot', 0x4D4B00, cleanup_mutation)
    def query_mutation(env):
        m, gs = manager(env, points=[(31, 31)])
        replacement, _ = grid(env, [(5, 5), (31, 31)])
        def change(env, call, at):
            env.put(at + 48, env.get(m + 0x68), env.get(m + 0x6C))
            env.put(m + 8, replacement)
            env.put(m + 0x48, 30, 30)
            return 0x80000000
        env.put(env.get(gs[0]) + 0x14, record(env, 'query-mutates-later-grid', 'thiscall', 1, change))
        return {'r': m}
    yield case('manager query re-reads later pointers and half sizes', 0x4D4B50, query_mutation, (31, 31))
    for remove in (0, 1):
        def setup(env):
            g, ns = grid(env, [(1, 1), (2, 2), (17, 17)])
            def change(env, call, at):
                n = call.arguments[0]
                env.put(at + 48, env.get(g + 8), env.get(n + 0xC), env.get(n))
                env.put(n, 0)  # traversal must use the next pointer captured before this call
                return 0xFFFFFFFF
            env.put(env.get(g) + 0x14, record(env, 'query-changes-next', 'thiscall', 1, change))
            return {'r': g}
        yield case(f'query captures next before callback remove {remove}', 0x4F46B0, setup, (0, 0, 63, 63, remove))
