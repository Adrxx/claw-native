"""Original-backed actor scheduling and creation cases."""
from clawparity.cases import Case

NEW = 0x4F63EC


def observe(env, log, tag, receiver, arguments, fields=()):
    n = env.get(log)
    env.put(log, n + 1)
    row = log + 4 + n * 48
    env.put(row, tag, receiver, len(arguments), *arguments)
    env.put(row + 28, *fields)


def list_setup(env, priorities=(), flags=()):
    scene = env.object(0x40, 'scene', fill=0)
    context = env.object(0x40, 'context', fill=0)
    env.put(scene + 12, context)
    pool = env.object(64 * 12, 'list-node-pool', fill=0)
    for i in range(63):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    log = env.object(0x6000, 'callback-observations', fill=0)
    actors = []
    nodes = []
    for i, priority in enumerate(priorities):
        actor = env.object(0x1b4, f'actor-{i}', fill=0x63 + i)
        service = env.object(0x174, f'service-{i}', fill=0)
        vt = env.object(0x44, f'actor-vtable-{i}', fill=0)
        node = env.object(12, f'live-node-{i}', fill=0)
        env.put(actor, vt)
        env.put(actor + 8, flags[i] if flags else 0)
        env.put(actor + 0x64, priority, node, service)
        env.put(vt + 4, env.stub(f'delete-{i}', 'thiscall', 1,
            lambda e, c: observe(e, log, 2, c.receiver, c.arguments,
                (e.get(scene + 0x14), e.get(c.receiver + 8), e.get(c.receiver + 0x68))) or 0))
        env.put(service + 0x10, env.stub(f'callback-{i}', 'cdecl', 1,
            lambda e, c: observe(e, log, 1, c.receiver, c.arguments,
                (e.get(c.arguments[0] + 8), e.get(e.get(c.arguments[0] + 0x6c) + 0x1c),
                 e.get(0x5430c4))) or 0))
        actors.append(actor)
        nodes.append(node)
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0,
                nodes[i - 1] if i else 0, actors[i])
    env.put(scene + 0x14, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
    return {'scene': scene, 'context': context, 'actors': actors, 'nodes': nodes, 'log': log}


def creation(priorities, flags, priority, incoming_flags, success=True, named=None):
    def setup(env):
        t = list_setup(env, priorities, flags)
        log, scene = t['log'], t['scene']
        allocation_state = env.object(4, 'creation-allocation-state', fill=0)
        def allocate_initialized_bytes(e, c):
            actor = e.get(allocation_state)
            if actor:
                observe(e, log, 13, actor, c.arguments,
                    (e.get(actor + 4), e.get(actor + 8), e.get(actor + 0x4c),
                     e.get(actor + 0x68), e.get(scene + 0x14)))
            result = e.object(c.arguments[0], 'creation-allocation', fill=0xb7)
            if c.arguments[0] == 0x1b4:
                e.put(allocation_state, result)
            return result
        env.override(NEW, allocate_initialized_bytes)
        metadata = env.object(0x18, 'actor-metadata', fill=0)
        callback = env.stub('metadata-notify', 'cdecl', 1,
            lambda e, c: observe(e, log, 12, c.receiver, c.arguments,
                (e.get(c.arguments[0] + 0x68), e.get(scene + 0x1c),
                 e.get(e.get(c.arguments[0] + 0x6c) + 0x1c))) or 0)
        env.put(metadata + 8, 0x2)
        env.put(metadata + 0x10, callback if success else 0)
        t['metadata'] = metadata
        if named is not None:
            manager = env.object(0x30, 'metadata-manager', fill=0)
            buckets = env.object(4, 'map-buckets', fill=0)
            key = env.object(16, 'lookup-key', data=b'actor-name\0', fill=0)
            env.put(t['context'] + 0x14, manager)
            env.put(manager + 0x14, buckets, 1)
            t['key'] = key
            if named:
                node = env.object(16, 'map-node', fill=0)
                collision = env.object(16, 'map-collision', fill=0)
                otherkey = env.object(16, 'collision-key', data=b'other-name\0', fill=0)
                env.put(collision, node, 0, otherkey, 0x31415926)
                env.put(node, 0, 0, key, metadata)
                env.put(buckets, collision)
        return t
    return setup


def update(priorities, flags, timers, skips, initbits=0, mutate=False, physical=False):
    def setup(env):
        t = list_setup(env, priorities, flags)
        env.write(0x5430d0, bytes([initbits]))
        env.put(0x5430f0, 0, 0, 0, 0, 0)
        env.put(0x5430d8, 0, 0, 0, 0, 0)
        env.put(0x5430c4, 9, 0xfffffff7)
        env.override(0x546df0, lambda e, c: 3)
        for i, actor in enumerate(t['actors']):
            service = env.get(actor + 0x6c)
            env.put(service + 0x20, timers[i], skips[i])
        if physical:
            if len(t['actors']) == 1:
                block = env.object(4 + 12 * 8, 'physical-node-block', fill=0)
                node = block + 4
                env.put(node, 0, 0, t['actors'][0])
                for i in range(1, 7):
                    env.put(block + 4 + 12 * i, block + 4 + 12 * (i + 1))
                env.put(t['scene'] + 0x14, node, node, 1,
                        block + 16, block, 8)
                env.put(t['actors'][0] + 0x68, node)
            def physical_snapshot(e, c, tag):
                for actor in t['actors']:
                    observe(e, t['log'], tag, actor, c.arguments,
                        (e.get(actor + 8), e.get(actor + 0x64),
                         e.get(actor + 0x68), e.get(t['scene'] + 0x14),
                         e.get(t['scene'] + 0x1c)))
            def allocate_observed(e, c):
                physical_snapshot(e, c, 30)
                return e.object(c.arguments[0], 'observed-allocation', fill=0)
            def release_observed(e, c):
                physical_snapshot(e, c, 31)
                if c.arguments[0]:
                    e.release(c.arguments[0])
                return 0
            env.override(NEW, allocate_observed)
            env.override(0x4f6428, release_observed)
        if mutate and t['actors']:
            actor = t['actors'][0]
            def change(e, c):
                observe(e, t['log'], 3, c.receiver, c.arguments,
                        (e.get(actor + 8), e.get(0x5430c4), e.get(actor + 0x68)))
                e.put(actor + 8, 0x20000)
                e.put(actor + 0x64, 0xfffffff0)
                e.put(0x5430c4, 1)
                return 0
            env.put(env.get(actor + 0x6c) + 0x10, env.stub('change-flags-priority-delta', 'cdecl', 1, change))
        return t
    return setup


def stage(delta, timer, bounds, effect=False, swap=False):
    def setup(env):
        t = env.object(0x768, 'stage', fill=0)
        parent = env.object(0x60, 'stage-parent', fill=0)
        pause = env.object(0x34, 'pause', fill=0)
        context = env.object(0x28, 'stage-context', fill=0)
        sub = env.object(0x60, 'stage-subcontext', fill=0)
        state = env.object(0x74, 'input-state', fill=0)
        raw = env.object(0x248, 'raw-input', fill=0)
        env.put(state, raw)
        env.put(0x537204, state)
        env.put(t + 4, parent)
        env.put(parent + 0x4c, pause)
        env.put(pause + 0x30, 1)
        env.put(t + 12, context)
        env.put(t + 0x764, timer)
        env.put(context + 0x24, sub)
        if effect:
            obj = env.object(0xb4, 'optional-effect', fill=0)
            env.put(sub + 0x5c, obj)
        glob = env.object(0x178, 'stage-global', fill=0x75)
        env.put(0x537e88, glob)
        env.put(glob + 0x170, 0)
        if bounds is not None:
            interval = env.object(0x70, 'interval', fill=0)
            data = env.object(0x194, 'range-data', fill=0x47)
            env.put(interval + 0x14, data)
            env.put(interval + 0x64, *bounds)
            env.put(glob + 0x170, interval)
        env.put(0x537208, 0xffffffed, delta, 0x12345678)
        log = env.object(0x6000, 'render-observations', fill=0)
        render = env.object(4, 'render', fill=0)
        vt = env.object(0x44, 'render-vtable', fill=0)
        other = env.object(4, 'render-replacement', fill=0)
        vt2 = env.object(0x44, 'render-replacement-vtable', fill=0)
        env.put(render, vt)
        env.put(other, vt2)
        env.put(context + 8, render)
        def tick(e, c):
            observe(e, log, 20, c.receiver, c.arguments,
                    (e.get(0x537208), e.get(0x53720c), e.get(0x537210)))
            if swap:
                e.put(context + 8, other)
            return 0
        for table in (vt, vt2):
            env.put(table + 0x24, env.stub('render-step', 'thiscall', 1, tick))
            env.put(table + 0x40, env.stub('render-finish', 'thiscall', 0,
                lambda e, c: observe(e, log, 21, c.receiver, c.arguments,
                    (e.get(0x53720c), e.get(t + 0x764), e.get(glob + 0x174))) or 0))
        return {'stage': t}
    return setup


def cases(random_source):
    for timer, delta in [(0, 0), (0, 0xffffffff), (1, 0), (1, 1), (1, 2),
                         (9, 8), (9, 9), (9, 10), (0x80000000, 0x7fffffff),
                         (0xffffffff, 0xfffffffe), (0xffffffff, 0xffffffff)]:
        def setup(env, timer=timer):
            s = env.object(0x2c, 'timer-service', fill=0x5b)
            env.put(s + 0x20, timer)
            return s
        yield Case(f'timer {timer:x}/{delta:x}', 0x4c9860, setup, receiver=lambda s:s, arguments=(delta,))
    for _ in range(8):
        timer, delta = random_source.getrandbits(32), random_source.getrandbits(32)
        def setup(env, timer=timer):
            s = env.object(0x2c, 'random-timer', fill=0x83)
            env.put(s + 0x20, timer)
            return s
        yield Case(f'random timer {timer:x}/{delta:x}', 0x4c9860, setup, receiver=lambda s:s, arguments=(delta,))
    for priorities, flags, incoming in [((), (), 5), ((3, 5), (0, 0), 9),
            ((3, 5), (0, 0), 5), ((3, 5), (0, 0), 4), ((3, 5), (0, 0), -9),
            ((20, 3, 9), (0x20000, 0, 0), 5), ((0x7fffffff, -1), (0x20000, 0), -2)]:
        def setup(env, p=priorities, f=flags, incoming=incoming):
            t = list_setup(env, p, f)
            a = env.object(0x70, 'inserted', fill=0x93)
            env.put(a + 0x64, incoming)
            t['inserted'] = a
            return t
        yield Case(f'insert {priorities}/{incoming}', 0x4c9320, setup,
                   receiver=lambda t:t['scene'], arguments=(lambda t:t['inserted'],))
    for i in range(10):
        priorities = tuple(sorted(random_source.randrange(-200, 200) for _ in range(5)))
        incoming = random_source.randrange(-200, 200)
        flags = tuple(random_source.choice((0, 0x20000)) for _ in priorities)
        def setup(env, p=priorities, f=flags, incoming=incoming):
            t = list_setup(env, p, f)
            a = env.object(0x70, 'random-inserted', fill=0xa7)
            env.put(a + 0x64, incoming)
            t['inserted'] = a
            return t
        yield Case(f'random insertion {i}', 0x4c9320, setup,
                   receiver=lambda t:t['scene'], arguments=(lambda t:t['inserted'],))
    for p,f,priority,bits,ok in [((),(),7,0,True), ((1,9),(0,0),4,0x200000,True),
            ((12,1),(0x20000,0),4,0x200000,True), ((1,2),(0,0),8,0,True),
            ((),(),-7,0,False), ((-9,-7),(0,0),-7,0,True)]:
        yield Case(f'create {p}/{priority}/{bits:x}/{ok}', 0x4c8be0,
                   creation(p,f,priority,bits,ok), receiver=lambda t:t['scene'],
                   arguments=(0x31415926,0xabcdef01,0x87654321,priority,lambda t:t['metadata'],bits))
    for hit in (False,True):
        yield Case(f'named map hit {hit}', 0x4c8da0,
                   creation((1,9),(0,0),4,0x200000,True,named=hit), receiver=lambda t:t['scene'],
                   arguments=(0x31415926,0xabcdef01,0x87654321,4,lambda t:t['key'],0x200000))
    for p,f,timers,skips,bits,mutate in [
            ((),(),(),(),0,False), ((),(),(),(),3,False),
            ((1,4,9),(0,0,0),(20,0,0),(0,2,0),1,False),
            ((1,4,9),(0x90000,0x10000,0),(0,0,0),(0,0,0),2,False),
            ((3,9,1),(0x20000,0x20000,0),(0,0,0),(0,0,0),3,False),
            ((1,2),(0x20000,0x20000),(0,0),(0,0),3,False),
            ((1,), (0x20000,), (0,), (0,), 3,False),
            ((1,4,9),(0,0,0),(0,5,0),(0,0,0),3,True)]:
        for clock in (0,1):
            yield Case(f'update {p}/{f}/{bits}/{mutate}/clock{clock}', 0x4c8fc0,
                       update(p,f,timers,skips,bits,mutate), receiver=lambda t:t['scene'], arguments=(clock,))
    for flags in ((0x20000,), (0x90000,), (0x10000,0x20000,0x20000),
                  (0x20000,0x20000,0), (0,0,0)):
        count = len(flags)
        yield Case(f'physical services observe publication {flags}', 0x4c8fc0,
                   update(tuple(range(count)), flags, (0,) * count,
                          (0,) * count, 3, count > 1, physical=True),
                   receiver=lambda t:t['scene'], arguments=(0,))
    for function in (0x46ace0, 0x46ad70):
        for delta,timer,bounds,effect in [(0,0,None,False),(1,1,None,False),
            (18,1,(100,100),True),(19,1,(101,500),False),
            (36,1,(-100,99),True),(55,1,(-100,200),True),(54,1,(-100,200),False)]:
            yield Case(f'stage {function:x}/{delta}/{timer}/{bounds}/{effect}', function,
                       stage(delta,timer,bounds,effect,True), receiver=lambda t:t['stage'])
