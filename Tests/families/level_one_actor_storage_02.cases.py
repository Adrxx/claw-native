"""Original-derived collision, coordinate, and actor initialization cases."""
from clawparity.cases import Case

MASK = 0xFFFFFFFF


def words(env, size, name, seed=0x13579BDF):
    return env.object(size, name, words=[(seed + i * 0x01030507) & MASK for i in range(size // 4)])


def actor(env, name, flags=0, masks=(1, 1, 1), rect=(0, 0, 10, 10), position=(23, -17), health=9, damage=3):
    obj = words(env, 0x180, name)
    env.put(obj + 8, flags)
    env.put(obj + 0x4C, *(v & MASK for v in position))
    controller = words(env, 0x40, name + '-controller')
    env.put(obj + 0x6C, controller, 0, 0x12344321, 0, 0x56788765)
    env.put(obj + 0xD0, *masks)
    env.put(obj + 0x104, damage & MASK)
    env.put(obj + 0x10C, health & MASK)
    env.put(obj + 0x128, *(v & MASK for v in rect))
    env.put(obj + 0x138, *(v & MASK for v in rect))
    return obj


def collision_setup(options, mutation=None):
    def setup(env):
        manager = words(env, 0x30, 'manager')
        actors = [actor(env, f'actor-{i}', **option) for i, option in enumerate(options)]
        log = env.object(4096, 'callback-observations')
        env.put(log, 0)
        nodes = [words(env, 12, f'node-{i}') for i in range(len(actors))]
        for i, obj in enumerate(actors):
            env.put(nodes[i], nodes[i+1] if i + 1 < len(nodes) else 0, 0xA1000000 + i, obj)
            for offset in (0x70, 0x78):
                table = words(env, 24, f'callback-table-{i}-{offset}')
                def effect(env, call, offset=offset):
                    count = env.get(log)
                    out = log + 4 + count * 80
                    env.put(out, call.receiver, call.arguments[0], offset)
                    for j, a in enumerate(actors[:2]):
                        env.put(out + 12 + j * 24, env.get(a+8), env.get(a+0x74), env.get(a+0x7C), env.get(a+0x10C), env.get(a+0xD0), env.get(a+0xD4))
                    env.put(log, count + 1)
                    if count == 0 and mutation:
                        if mutation == 'flags':
                            env.put(actors[0] + 8, 8)
                        elif mutation == 'reverse-mask':
                            env.put(actors[1] + 0xD4, 0)
                            env.put(actors[0] + 0xD8, 0)
                        elif mutation == 'disable-reverse':
                            env.put(actors[0] + 8, 0x80)
                        elif mutation == 'health':
                            env.put(actors[0] + 0x10C, 2)
                            env.put(actors[1] + 0x104, 7)
                        elif mutation == 'callbacks':
                            env.put(actors[0] + 0x70, 0)
                        elif mutation == 'node':
                            env.put(nodes[0], 0)
                    return 0x8192A3B4
                env.put(table + 0x10, env.stub(f'collision-{i}-{offset}', 'cdecl', 1, effect))
                env.put(obj + offset, table if not options[i].get('no_callbacks', False) else 0)
        env.put(manager + 0x14, nodes[0] if nodes else 0)
        return {'receiver': manager}
    return setup


def collision(label, options, mutation=None):
    # no_callbacks is a setup-only option, removed before constructing actors.
    clean = [dict(o) for o in options]
    absent = [o.pop('no_callbacks', False) for o in clean]
    base = collision_setup(clean, mutation)
    def setup(env):
        tokens = base(env)
        node = env.get(tokens['receiver'] + 0x14)
        for no_callback in absent:
            obj = env.get(node + 8)
            if no_callback:
                env.put(obj + 0x70, 0)
                env.put(obj + 0x78, 0)
            node = env.get(node)
        return tokens
    return Case(label, 0x4C9390, setup, receiver=lambda t: t['receiver'])


def rect_case(label, first, second, actor_rect=False, positions=((0, 0), (0, 0)), sentinel=0):
    def setup(env):
        if actor_rect:
            a = actor(env, 'first', rect=first, position=positions[0])
            b = actor(env, 'second', rect=second, position=positions[1])
            if sentinel == 1:
                env.put(a + 0x128, 0x80000000)
            if sentinel == 2:
                env.put(b + 0x138, 0x80000000)
        else:
            a = env.object(16, 'first-rectangle', words=[v & MASK for v in first])
            b = env.object(16, 'second-rectangle', words=[v & MASK for v in second])
        return {'a': a, 'b': b}
    return Case(label, 0x4C95B0 if actor_rect else 0x4CA230, setup, arguments=(lambda t:t['a'], lambda t:t['b']))


def wrap_case(label, flags, xy, dims, bounds, translation, alias=None):
    def setup(env):
        obj = words(env, 0x80, 'coordinate-owner')
        env.put(obj+8, flags)
        env.put(obj+0x30, *(v & MASK for v in dims))
        env.put(obj+0x40, *(v & MASK for v in bounds))
        env.put(obj+0x50, *(v & MASK for v in translation))
        point = env.object(16, 'point-with-guards', words=[0xA1B2C3D4, xy[0]&MASK, xy[1]&MASK, 0x12345678])
        x, y = point+4, point+8
        if alias == 'same':
            y = x
        elif alias == 'x-field':
            x = obj+0x40
        elif alias == 'y-field':
            y = obj+0x44
        elif alias == 'flags':
            x = obj+8
        return {'receiver':obj, 'x':x, 'y':y}
    return Case(label, 0x4C96D0, setup, receiver=lambda t:t['receiver'], arguments=(lambda t:t['x'], lambda t:t['y']))


def response_case(label, flags, health, damage, callback=True):
    def setup(env):
        a = actor(env, 'damaged', flags=flags, health=health)
        b = actor(env, 'attacker', damage=damage)
        log = env.object(64, 'response-observations')
        if callback:
            table = words(env, 24, 'response-table')
            def effect(env, call):
                env.put(log, call.receiver, call.arguments[0], env.get(a+0x74), env.get(a+0x10C), env.get(b+0x104))
                env.put(a+0x10C, 0xDECAFBAD)
                return 0x84736251
            env.put(table+0x10, env.stub('response', 'cdecl', 1, effect))
            env.put(a+0x70, table)
        return {'receiver':a, 'other':b}
    return Case(label, 0x4C9AE0, setup, receiver=lambda t:t['receiver'], arguments=(lambda t:t['other'],))


def cases(random_source):
    rects = [(0,0,10,10), (11,0,20,10), (-20,0,-1,10), (0,11,10,20), (0,-20,10,-1), (10,10,20,20), (0,0,0,0), (5,5,4,4), (-2147483648,-2147483648,-2147483648,-2147483648), (2147483647,2147483647,2147483647,2147483647)]
    for i, rect in enumerate(rects):
        for mode in (False, True):
            yield rect_case(f'rect {i} actor={mode}', rects[0], rect, mode)
            yield rect_case(f'rect reversed {i} actor={mode}', rect, rects[0], mode)
    for sentinel in (1,2):
        yield rect_case(f'actor sentinel {sentinel}', rects[0], rects[0], True, sentinel=sentinel)
    for i in range(24):
        rect1 = tuple(random_source.randrange(-30,31) for _ in range(4))
        rect2 = tuple(random_source.randrange(-30,31) for _ in range(4))
        positions = tuple(tuple(random_source.randrange(-50,51) for _ in range(2)) for _ in range(2))
        yield rect_case(f'random-rect {i}', rect1, rect2, i%2 == 0, positions)
    for flags in (0,4,8,12,0xFFFFFFF3,0xFFFFFFFF):
        for xy in ((-1,-2),(0,0),(3,5),(9,11),(10,12),(11,13),(-31,29),(2147483647,-2147483648)):
            yield wrap_case(f'wrap {flags:x} {xy}', flags, xy, (10,12), (7,9,20,24), (31,-27))
    for bounds in ((7,9,9,11),(7,9,10,12),(20,30,15,18),(1,1,11,13),(-4,-7,20,24)):
        for xy in ((0,0),(1,1),(5,6)):
            yield wrap_case(f'wrap bounds {bounds} {xy}',12,xy,(10,12),bounds,(37,-19))
    for alias in ('same','x-field','y-field','flags'):
        yield wrap_case(f'wrap alias {alias}',12,(-3,14),(10,12),(7,9,20,24),(31,-27),alias)
    for i in range(12):
        yield wrap_case(f'random wrap {i}',random_source.getrandbits(32),tuple(random_source.randrange(-90,91) for _ in range(2)),(37,53),(19,23,75,110),(83,-47))
    for flags in (0,8,0x100,0x108):
        for health, damage in ((9,3),(3,3),(2,3),(-7,3),(7,-3),(0,0),(-2147483648,1),(2147483647,-1)):
            yield response_case(f'response {flags:x} {health} {damage}',flags,health,damage)
    yield response_case('response absent callback',0,9,3,False)
    yield collision('empty actor list',[])
    yield collision('single actor',[{}])
    yield collision('both collision directions',[{},{}])
    for first_flags, second_flags in ((1,0),(0,1),(1,1),(0x40000,0),(0,0x40000),(0x40000,0x40000),(4,0),(0,4),(0x80,0),(0,0x80),(8,0),(0,8),(8,8),(0x84,0x84)):
        yield collision(f'collision flags {first_flags:x} {second_flags:x}',[{'flags':first_flags},{'flags':second_flags}])
    for first_masks, second_masks in (((0,0,0),(0,0,0)),((1,0,0),(1,1,1)),((1,1,1),(1,0,0)),((1,0,1),(1,0,0)),((0,1,0),(1,0,0)),((1,0,0),(0,1,0)),((1,0,0),(0,0,1)),((2,4,8),(16,32,64))):
        yield collision(f'collision masks {first_masks} {second_masks}',[{'masks':first_masks},{'masks':second_masks}])
    for side in (0,1):
        options=[{},{}]
        options[side]={'rect':(-2147483648,0,10,10)}
        yield collision(f'collision sentinel side {side}',options)
        options=[{},{}]
        options[side]={'no_callbacks':True}
        yield collision(f'collision callbacks absent side {side}',options)
    yield collision('collision neither callback',[{'no_callbacks':True},{'no_callbacks':True}])
    yield collision('collision disjoint',[{}, {'rect':(100,100,120,120)}])
    for health in (10,3,2):
        yield collision(f'first damage health {health}',[{'flags':8,'health':health},{}])
        yield collision(f'second damage health {health}',[{}, {'flags':8,'health':health}])
    for mutation in ('flags','reverse-mask','disable-reverse','health','callbacks','node'):
        yield collision(f'callback mutates {mutation}',[{},{}],mutation)
    yield collision('three actors distinct flags',[{}, {'flags':1}, {'flags':8,'health':2}])
    yield collision('three actors all callbacks',[{}, {}, {}])
    for result in (0,1,0x87654321):
        for child_flags in (0,1,2,3):
            def setup(env, result=result, child_flags=child_flags):
                obj = words(env, 0x180, 'initializing-actor')
                child = words(env, 0x40, 'initializing-child')
                parent = words(env, 0x40, 'initializing-parent')
                table = words(env, 0x30, 'initializing-vtable')
                data = words(env, 0x20, 'initializing-argument', random_source.getrandbits(32))
                log = env.object(128, 'initialization-observations')
                env.put(obj+0x0C, parent)
                env.put(obj+0x6C, child)
                env.put(child,table)
                env.put(child+8,child_flags)
                def effect(env, call):
                    env.put(log,call.receiver,*call.arguments)
                    env.write(log+12,env.read(obj+0x3C,0x30))
                    env.put(log+64,env.get(obj+0x64),env.get(obj+0xF0),env.get(obj+0x10C))
                    return result
                env.put(table+0x24,env.stub('child-initialize','thiscall',2,effect))
                return {'receiver':obj,'data':data,'scalar':random_source.getrandbits(32)}
            yield Case(f'initialize result={result:x} child_flags={child_flags}',0x4C9F80,setup,receiver=lambda t:t['receiver'],arguments=(lambda t:t['scalar'],lambda t:t['data']))
    for flags, mutation in ((0,None),(2,None),(0xFFFFFFFD,None),(0xFFFFFFFF,None),(0,'enable'),(2,'disable'),(2,'pointers')):
        def setup(env, flags=flags, mutation=mutation):
            obj = words(env, 0x30, 'surface-owner')
            context = words(env,0x40,'surface-context')
            env.put(obj+0x0C,context)
            env.put(context+0x34,flags)
            log = env.object(4096,'surface-observations')
            env.put(log,0)
            wrappers=[]
            for i in range(6):
                wrapper = words(env,0x40,f'surface-wrapper-{i}')
                surface = words(env,0x20,f'surface-{i}')
                com = words(env,4,f'com-{i}')
                table = words(env,0x40,f'com-vtable-{i}')
                env.put(wrapper+0x2C,surface)
                env.put(surface+8,com)
                env.put(com,table)
                wrappers.append(wrapper)
                for method, argc in ((0x14,6),(0x2C,3)):
                    def effect(env,call,method=method):
                        count=env.get(log)
                        out=log+4+count*160
                        env.put(out,call.receiver,method,len(call.arguments),*(call.arguments[:-1] if method==0x14 else call.arguments))
                        if method==0x14:
                            env.write(out+40,env.read(call.arguments[5],100))
                        env.put(log,count+1)
                        if mutation=='pointers':
                            env.put(obj+0x10,wrappers[(count+2)%6],wrappers[(count+3)%6])
                        if count==3 and mutation in ('enable','disable'):
                            env.put(context+0x34,2 if mutation=='enable' else 0)
                        return 0
                    env.put(table+method,env.stub(f'surface-{i}-method-{method}','stdcall',argc,effect))
            env.put(obj+0x10,wrappers[0],wrappers[1])
            return {'receiver':obj,'scalar':random_source.getrandbits(32)}
        yield Case(f'surface flags={flags:x} mutation={mutation}',0x4CAAA0,setup,receiver=lambda t:t['receiver'],arguments=(lambda t:t['scalar'],))

    # The original pair pass constructs its own rectangles before the predicate.
    pair_rectangles = (
        ((0, 20, 5, 30), (0, 0, 5, 10)),
        ((0, 0, 5, 10), (0, 20, 5, 30)),
        ((0, 20, 5, 30), (0, 25, 5, 35)),
        ((0, 25, 5, 35), (0, 20, 5, 30)),
        ((0, 20, 5, 30), (0, 30, 5, 40)),
        ((0, 30, 5, 40), (0, 20, 5, 30)),
        ((0, 20, 5, 30), (0, 31, 5, 40)),
        ((0, 31, 5, 40), (0, 20, 5, 30)),
        ((20, 20, 30, 30), (0, 20, 10, 30)),
        ((0, 20, 10, 30), (20, 20, 30, 30)),
        ((20, 20, 30, 30), (25, 20, 35, 30)),
        ((25, 20, 35, 30), (20, 20, 30, 30)),
        ((20, 20, 30, 30), (30, 20, 40, 30)),
        ((30, 20, 40, 30), (20, 20, 30, 30)),
    )
    for index, (defender, attacker) in enumerate(pair_rectangles):
        for positions in (((0, 0), (0, 0)), ((17, 43), (19, 41))):
            yield pair_geometry_case(f'pair geometry {index} positions={positions}', defender, attacker, positions)


def pair_geometry_case(label, defender, attacker, positions):
    # First-actor bit 0x80 suppresses only the reverse pass. The first hit and
    # second attack rectangles alone decide the observable first-pass callbacks.
    base = collision_setup([
        {'flags': 0x80, 'rect': defender, 'position': positions[0]},
        {'flags': 0, 'rect': attacker, 'position': positions[1]},
    ])
    def setup(env):
        tokens = base(env)
        first_node = env.get(tokens['receiver'] + 0x14)
        first_actor = env.get(first_node + 8)
        second_actor = env.get(env.get(first_node) + 8)
        # Unused neighboring fields differ from each consumed rectangle edge.
        env.put(first_actor + 0x138, *((v & MASK) for v in (-77, -66, -55, -44)))
        env.put(second_actor + 0x128, *((v & MASK) for v in (-33, -22, -11, 0)))
        env.put(second_actor + 0x148, (-91) & MASK)
        return tokens
    return Case(label, 0x4C9390, setup, receiver=lambda t: t['receiver'])
