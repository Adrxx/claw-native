"""Original-backed image ownership, cached resources, and physical COM cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

NEW = 0x4F63EC
DELETE = 0x4F6428


def base(env):
    for address in (0x54139C, 0x5413A0, 0x5413A4, 0x5413A8):
        env.put(address, 0)
    env.put(0x54316C, 0)
    env.put(0x543170, 0x37)
    obj = env.object(0x34, 'image', fill=0x5B)
    env.put(obj + 0x2C, 0, 0)
    manager = env.object(0x900, 'manager', fill=0)
    env.put(obj + 0xC, manager)
    env.put(manager + 0x1C, manager)
    return {'obj': obj, 'manager': manager}


def physical(env, t, lost=1, restores=(0,), lock_result=0, mutate=False):
    surface = env.object(0xBC, 'surface', fill=0)
    pixels = env.object(1024, 'pixels', fill=0xB7)
    env.put(surface, 0x513690)
    env.put(surface + 0x14, 2, 4, 16)
    env.put(surface + 0x30, pixels)
    env.put(surface + 0xA4, 8)
    trace = env.object(128, 'callback observations', fill=0)
    interfaces = []
    for index in range(2):
        com = env.object(4, 'COM surface', fill=0)
        table = env.object(0x84, 'COM methods', fill=0)
        env.put(com, table)
        env.put(table + 0x60, env.stub('IsLost', 'stdcall', 1, returns(lost)))
        def restore(e, call, i=index):
            count = e.get(trace)
            e.put(trace, count + 1)
            e.put(trace + 4 + count * 8, call.receiver, call.arguments[0])
            if mutate and i == 0:
                e.put(surface + 8, interfaces[1])
            return restores[min(i if mutate else count, len(restores) - 1)]
        env.put(table + 0x6C, env.stub('Restore', 'stdcall', 1, restore))
        def lock(e, call):
            desc = call.arguments[2]
            e.put(desc + 0x10, 16)
            e.put(desc + 0x24, pixels)
            return lock_result
        env.put(table + 0x64, env.stub('Lock', 'stdcall', 5, lock))
        env.put(table + 0x80, env.stub('Unlock', 'stdcall', 2, returns(0)))
        env.put(table + 0x74, env.stub('SetColorKey', 'stdcall', 3, returns(0)))
        interfaces.append(com)
    env.put(surface + 8, interfaces[0])
    env.put(t['obj'] + 0x2C, surface)
    t.update(surface=surface, pixels=pixels, trace=trace)
    return t


def cached(env, t, tag=0x524944, size=32, null=False, owner_cache=False):
    entry = env.object(0x2C, 'resource entry', fill=0)
    owner = env.object(0x24, 'resource owner', fill=0)
    fmt = env.object(4, 'resource format', words=[tag])
    data = env.object(0x400, 'resource bytes', fill=0)
    env.put(data + 8, 3, 2)  # PID width mismatch and invalid BMP/PCX headers safely reject.
    env.put(entry + 8, fmt)
    env.put(entry + 0x14, size, 0 if null else data)
    env.put(entry + 0x24, owner, 0x1234)
    env.put(owner + 0xC, 0x1234)
    if owner_cache:
        env.put(owner + 0x20, data)
    if null and size:
        env.override(NEW, allocate(fail=True))
    t['entry'] = entry
    return t


def case(label, function, setup, arguments=()):
    return Case(label, function, setup, receiver=lambda t: t['obj'], arguments=arguments)


def cases(random_source):
    for first in (False, True):
        for second in (False, True):
            def setup(env, a=first, b=second):
                t = base(env)
                obj = env.object(0x24, 'buffer', fill=0x93)
                env.put(obj + 0xC, env.object(17, 'buffer bytes', fill=0) if a else 0)
                env.put(obj + 0x20, env.object(23, 'secondary bytes', fill=0) if b else 0)
                t['obj'] = obj
                return t
            yield case(f'buffer pointers {first} {second}', 0x4BFC20, setup)
    def changing_delete(env):
        t = base(env)
        obj = env.object(0x24, 'buffer', fill=0)
        a = env.object(7, 'first allocation', fill=0)
        b = env.object(11, 'second allocation', fill=0)
        c = env.object(13, 'replacement allocation', fill=0)
        env.put(obj + 0xC, a)
        env.put(obj + 0x20, b)
        def destroy(e, call):
            if call.arguments[0] == a:
                e.put(obj + 0x20, c)
            e.release(call.arguments[0])
            return 0
        env.override(DELETE, destroy)
        t['obj'] = obj
        return t
    yield case('buffer re-reads second pointer after release', 0x4BFC20, changing_delete)
    for function in (0x4CE900, 0x4D26C0, 0x4CE8E0):
        for with_buffer in (False, True):
            for flags in ((0, 1, 0x100, 0x101) if function == 0x4CE8E0 else (0,)):
                def setup(env, b=with_buffer):
                    t = base(env)
                    if b:
                        buffer = env.object(0x24, 'buffer', fill=0)
                        env.put(buffer + 0xC, env.object(9, 'bytes', fill=0))
                        env.put(buffer + 0x20, env.object(15, 'other bytes', fill=0))
                        env.put(t['obj'] + 0x30, buffer)
                    return t
                yield case(f'destroy {function:x} buffer {with_buffer} flag {flags}', function, setup,
                           (flags,) if function == 0x4CE8E0 else ())
    yield case('flip absent surface unused argument', 0x4D2790, base, (0x85A731,))
    for lost, statuses, mutate in ((0, (1,), False), (1, (0,), False), (1, (1, 0), False),
                                   (1, (1, 7), False), (1, (1, 0), True), (1, (1, 0x80004005), True)):
        yield case(f'retry lost {lost} restore {statuses} mutate {mutate}', 0x4D56D0,
                   lambda e, l=lost, s=statuses, m=mutate: physical(e, base(e), l, s, mutate=m))
    yield case('retry absent surface', 0x4D56D0, base)
    yield case('restore absent surface', 0x4D27A0, base, (0x123, 0xABC))
    yield case('restore healthy surface', 0x4D27A0,
               lambda e: physical(e, base(e), lost=0), (0x123, 0xABC))
    def callback_reload(env):
        t = physical(env, base(env), restores=(0x80004005,))
        v1 = env.object(0x30, 'first image vtable', fill=0)
        v2 = env.object(0x30, 'replacement image vtable', fill=0)
        def destroy(e, call):
            e.put(t['trace'] + 40, call.receiver, e.get(t['obj'] + 0x2C))
            e.put(t['obj'], v2)
            return 0xABCD
        def create(e, call):
            e.put(t['trace'] + 52, call.receiver, *call.arguments)
            return 0x73A9
        env.put(v1 + 0x1C, env.stub('image teardown', 'thiscall', 0, destroy))
        env.put(v1 + 0x2C, env.stub('stale image create', 'thiscall', 2, returns(0xEE)))
        env.put(v2 + 0x2C, env.stub('image recreate', 'thiscall', 2, create))
        env.put(t['obj'], v1)
        return t
    yield case('restore failed calls teardown and reloaded create', 0x4D27A0, callback_reload,
               (random_source.getrandbits(32), random_source.getrandbits(32)))
    for tag in (0, 0x424D50, 0x504358, 0x504944, 0x524944, 0xFFFFFFFF):
        for mode in ('cached', 'owner', 'zero', 'null'):
            def setup(env, tag=tag, mode=mode):
                t = physical(env, base(env))
                return cached(env, t, tag, 0 if mode == 'zero' else 32,
                              null=mode == 'null', owner_cache=mode == 'owner')
            yield case(f'restore tag {tag:x} {mode}', 0x4D27A0, setup,
                       (lambda t: t['entry'], 0xAB57))
    for width, height, depth, flags, palette, fail in (
        (3,2,8,0,False,False), (8,2,8,0,False,False), (4,3,8,0,False,False),
        (4,2,8,0,False,False), (4,2,8,1,False,False),
        (4,2,32,0,False,False), (4,2,32,0,True,False),
        (4,2,24,0,True,False), (4,2,24,0x81,False,False),
        (4,2,24,0,True,True), (4,2,8,0x80,False,False)):
        def setup(env, w=width,h=height,d=depth,f=flags,p=palette,fail=fail):
            t = physical(env, base(env))
            env.put(t['manager'] + 0x474, d)
            env.put(t['manager'] + 0x878, int(p))
            env.write(t['manager'] + 0x478, bytes((i * 37 + 13) % 256 for i in range(1024)))
            env.put(t['surface'] + 0xA4, d)
            data = env.object(0x340, 'PID', fill=0)
            env.put(data + 4, f,w,h)
            env.write(data + 0x20, bytes([1,2,3,4,5,6,7,8,9,10,11,12]))
            env.write(data + 0x40, bytes((i * 17 + 29) % 256 for i in range(768)))
            t.update(obj=t['surface'], data=data, size=0x340)
            if fail:
                env.override(NEW, allocate(fail=True))
            return t
        yield case(f'PID {width} {height} depth {depth} flags {flags} palette {palette} allocfail {fail}',
                   0x4BF680, setup, (lambda t:t['manager'],lambda t:t['data'],lambda t:t['size'],0x57))
    for function in (0x4D2790, 0x4BF680):
        for failure in (0, 0x80004005):
            def setup(env, fail=failure, function=function):
                t = physical(env, base(env), lock_result=fail)
                data = env.object(0x40, 'PID bytes', fill=0)
                env.put(data + 4, 0, 4, 2)
                env.write(data + 0x20, bytes([0xC4, 39, 0xC4, 117]))
                env.put(t['manager'] + 0x474, 8)
                t['data'] = data
                if function == 0x4BF680:
                    t['obj'] = t['surface']
                return t
            args = (0x1234,) if function == 0x4D2790 else (lambda t:t['manager'],lambda t:t['data'],0x40,0xFFFFFFFF)
            yield case(f'physical lock {function:x} result {failure:x}', function, setup, args)
    for length in (0, 0x300):
        def short_palette(env):
            t = physical(env, base(env))
            data = env.object(0x40, 'short PID', fill=0)
            env.put(data + 4, 0x80, 4, 2)
            env.put(t['manager'] + 0x474, 8)
            t.update(obj=t['surface'], data=data)
            return t
        yield case(f'embedded palette length boundary {length}',0x4BF680,short_palette,
                   (lambda t:t['manager'],lambda t:t['data'],length,0x65))
    for w,h,keyed,global_flags,create_error in ((7,5,0,0,0),(9,3,1,1,0),
                                               (0xFFFFFFFD,0xFFFFFFFF,1,0,0),
                                               (4,2,0,1,0x80004005)):
        def create_setup(env,w=w,h=h,keyed=keyed,g=global_flags,error=create_error):
            t = base(env)
            dd = env.object(4, 'DirectDraw', fill=0)
            methods = env.object(0x1C, 'DirectDraw methods', fill=0)
            env.put(dd, methods)
            env.put(t['manager'], dd)
            env.put(t['manager'] + 0x474, 8)
            node = env.object(12, 'existing manager list node', fill=0)
            free_node = env.object(12, 'manager free list node', fill=0)
            env.put(t['manager'] + 0x3BC, node,node,1,free_node)
            com = env.object(4, 'created COM surface', fill=0)
            vtable = env.object(0x84, 'created COM methods', fill=0)
            env.put(com,vtable)
            def desc(e,call):
                e.put(call.arguments[1]+8,h,w,max(4,w & 0xFFFF))
                e.put(call.arguments[1]+0x54,8)
                return 0
            env.put(vtable+0x58,env.stub('GetSurfaceDesc','stdcall',2,desc))
            env.put(vtable+0x74,env.stub('created SetColorKey','stdcall',3,returns(0)))
            env.put(vtable+8,env.stub('created Release','stdcall',1,returns(0)))
            def create(e,call):
                if not error:
                    e.put(call.arguments[2],com)
                return error
            env.put(methods+0x18,env.stub('CreateSurface','stdcall',4,create))
            env.put(0x54316C,g)
            return t
        yield case(f'create geometry {w:x} {h:x} keyed {keyed} flags {global_flags} error {create_error:x}',
                   0x4D2540, create_setup, (w,h,keyed))
    for function in (0x4D26C0,0x4CE900,0x4CE8E0):
        def release_surface(env):
            t=physical(env,base(env))
            node=env.object(12,'surface list node',fill=0)
            sentinel=env.object(12,'remaining list node',fill=0)
            env.put(node,sentinel,0,t['surface'])
            env.put(sentinel,0,node,0x1357)
            env.put(t['manager']+0x3BC,node,sentinel,2,0)
            env.put(t['surface']+4,node)
            com=env.get(t['surface']+8)
            table=env.get(com)
            env.put(table+8,env.stub('release surface COM','stdcall',1,returns(0)))
            return t
        yield case(f'owned release of original-backed surface {function:x}',function,release_surface,
                   (1,) if function==0x4CE8E0 else ())
