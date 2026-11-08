"""Original popup callbacks, surface graph, cursor counters and input repeats."""
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence


def obj(env, *args, **kwargs):
    kwargs.setdefault("fill", 0)
    return env.object(*args, **kwargs)


def base(env, salt=0xA5C37E91):
    p = obj(env, 0x2BC, 'popup-parent')
    v = obj(env, 0x1FC, 'parent-vtable')
    active = obj(env, 0x2BC, 'active-popup')
    av = obj(env, 0x1FC, 'active-vtable')
    log = obj(env, 256, 'callback-observations')
    env.put(p, v)
    env.put(active, av)
    env.put(p + 0x160, active)
    env.put(active + 0x2B8, salt)
    t = dict(p=p, active=active, av=av, v=v, log=log)

    def record(env, call):
        n = env.get(log)
        dest = log + 4 + n * 24
        env.put(dest, call.receiver, len(call.arguments), *(list(call.arguments) + [0] * (2-len(call.arguments))), env.get(active + 0x2B8), env.get(p + 0x16C))
        env.put(log, n+1)
        return salt

    for slot, argc in ((0x1D8, 0), (0x1DC, 2), (0x1E0, 0), (0x1F4, 1), (0x1F8, 0)):
        env.put(av + slot, env.stub('popup-%x' % slot, 'thiscall', argc, record))
    env.put(v + 0x2C, env.stub('parent-command', 'thiscall', 2, record))
    for a in (0x54139C, 0x5413A0, 0x5413A4, 0x5413A8):
        env.put(a, 0)
    return t


def surface(env, name, rect=(7, 11, 38, 58), blt=None, flip=None):
    s = obj(env, 0xBC, name)
    i = obj(env, 4, name+'-interface')
    v = obj(env, 0x84, name+'-COM-vtable')
    env.put(s, 0x513690)
    env.put(s + 8, i)
    env.put(s + 0x7C, *rect)
    env.put(i, v)
    observed = obj(env, 512, name+'-Blt-observations')
    def observe_blt(env, call):
        n = env.get(observed)
        dest = observed + 4 + n * 80
        env.put(dest, call.receiver, *call.arguments)
        for offset, pointer in ((32, call.arguments[1]), (48, call.arguments[3])):
            if pointer:
                env.write(dest + offset, env.read(pointer, 16))
            else:
                env.put(dest + offset, 0xD15AB1ED, 0xD15AB1ED, 0xD15AB1ED, 0xD15AB1ED)
        env.put(observed, n + 1)
        return blt(env, call) if blt else 0
    env.put(v + 0x14, env.stub(name+'-Blt', 'stdcall', 6, observe_blt))
    env.put(v + 0x2C, env.stub(name+'-Flip', 'stdcall', 3, flip or returns(0)))
    env.put(v + 8, env.stub(name+'-Release', 'stdcall', 1, returns(1)))
    return s, i, v


def graphics(env, t, blt=None, flip=None, flags=0):
    a = obj(env, 0x20, 'application')
    d = obj(env, 0x18, 'display')
    f = obj(env, 0x38, 'display-flags')
    h1 = obj(env, 0x30, 'front-holder')
    h2 = obj(env, 0x30, 'back-holder')
    s1, i1, v1 = surface(env, 'front', flip=flip)
    s2, i2, v2 = surface(env, 'back', blt=blt)
    env.put(t['p'] + 0xC, a)
    env.put(a + 4, d)
    env.put(d + 0xC, f, h1, h2)
    env.put(f + 0x34, flags)
    env.put(h1 + 0x2C, s1)
    env.put(h2 + 0x2C, s2)
    t.update(app=a, display=d, front=s1, back=s2, h1=h1, h2=h2, i2=i2, v2=v2)
    return t


def rect_copy(env, call):
    env.write(call.arguments[0], env.read(call.arguments[1], 16))
    return 0


def mfc(env, hdc):
    wrapper = obj(env, 32, 'permanent-CDC')
    tls = obj(env, 4, 'TLS-key', words=[0x71])
    block = obj(env, 16, 'TLS-block')
    slots = obj(env, 12, 'TLS-slots')
    thread = obj(env, 8, 'thread-state')
    module = obj(env, 0x1074, 'module-state')
    mt = obj(env, 0x20, 'module-thread-state')
    hm = obj(env, 0x60, 'handle-map')
    buckets = obj(env, 4, 'map-buckets')
    node = obj(env, 12, 'permanent-map-node', words=[0, hdc, wrapper])
    env.put(0x540AF0, tls)
    env.put(0x53EC9C, 1)
    env.put(block + 8, 3, slots)
    env.put(slots + 4, thread, mt)
    env.put(thread + 4, module)
    env.put(module + 0x1070, 2)
    env.put(mt + 0x1C, hm)
    env.put(hm + 4, buckets, 1)
    env.put(buckets, node)
    env.override(0x546A7C, returns(block))
    return wrapper


def capture_setup(kind, salt):
    def setup(env):
        t = graphics(env, base(env, salt))
        def prepare_rectangle(env, call):
            backing = env.get(t['p'] + 0x15C)
            env.put(backing + 0x7C, 7, 11, 38, 58)
            return 0
        env.put(t['v2'] + 0x14, env.stub('capture-prepares-rectangle', 'stdcall', 6, prepare_rectangle))
        dims = obj(env, 0x84, 'dimensions')
        env.put(dims + 0x7C, 31, 47)
        env.put(t['p'] + 4, dims)
        manager = obj(env, 0x478, 'surface-manager')
        env.put(t['app'] + 0x1C, manager)
        free = obj(env, 12, 'free-list-node')
        env.put(manager + 0x3C8, free)
        if kind == 'no-dimensions':
            env.put(t['p'] + 4, 0)
        if kind == 'no-popup':
            env.put(t['p'] + 0x160, 0)
        if kind != 'no-manager':
            dd = obj(env, 4, 'DirectDraw')
            dv = obj(env, 0x1C, 'DirectDraw-vtable')
            env.put(manager, dd)
            env.put(dd, dv)
            new_s, new_i, new_v = surface(env, 'created')
            def create(env, call):
                env.put(call.arguments[2], new_i)
                return 0x80004005 if kind == 'create-error' else 0
            def desc(env, call):
                env.put(call.arguments[1] + 8, 47, 31, 37)
                env.put(call.arguments[1] + 0x54, 8)
                return 0
            env.put(dv + 0x18, env.stub('CreateSurface', 'stdcall', 4, create))
            env.put(new_v + 0x58, env.stub('GetSurfaceDesc', 'stdcall', 2, desc))
        if kind == 'old-backing':
            old, _, _ = surface(env, 'old-backing')
            node = obj(env, 12, 'old-list-node', words=[0, 0, old])
            env.put(old + 4, node)
            sentinel = obj(env, 12, 'surviving-list-node')
            env.put(node, sentinel)
            env.put(sentinel + 4, node)
            env.put(manager + 0x3BC, node, sentinel, 2)
            env.put(t['p'] + 0x15C, old)
        replacement, _, _ = surface(env, 'capture-reloaded', (13, 17, 29, 31))
        def copy(env, call):
            rect_copy(env, call)
            if kind == 'reload':
                env.put(t['p'] + 0x15C, replacement)
                env.put(t['h2'] + 0x2C, t['front'])
            return 0
        env.override(0x546D58, copy)
        return t
    return setup


def cases(random_source):
    salt = random_source.getrandbits(32) | 0x80000000
    stack_pattern = bytes(random_source.randrange(1, 256) for _ in range(48))
    def case(label, fn, setup, key='p'):
        stack = ((-48, stack_pattern),) if fn in (0x439480, 0x439630) else ()
        return Case(label, fn, setup, receiver=lambda t: t[key], initial_stack=stack)

    for fn, offset in ((0x452AE0, 0x254), (0x452AF0, 0x254), (0x45FDC0, 0x258), (0x45FDD0, 0x258)):
        for value in (None, 0, 1, salt):
            def setup(env, offset=offset, value=value):
                t = base(env, salt)
                if value is not None:
                    owner = obj(env, 0x44, 'visibility-owner', fill=0x6D)
                    env.put(owner + 0x40, value)
                    env.put(t['p'] + offset, owner)
                return t
            yield case('visibility %x %s' % (fn, value), fn, setup)

    for fn in (0x43A6E0, 0x43A720):
        for owner, policy, steps in ((False, 0, 1), (True, 1, 1), (True, 0, 1), (True, 0, 4)):
            def setup(env, owner=owner, policy=policy, steps=steps, fn=fn):
                t = base(env, salt)
                if owner:
                    o = obj(env, 0x178, 'cursor-owner')
                    env.put(o + 0x40, salt)
                    env.put(o + 0x174, policy)
                    env.put(t['p'] + 0x154, o)
                values = ([0x80000000]*(steps-1)+[0, 1]) if fn == 0x43A6E0 else ([0x7FFFFFFF]*(steps-1)+[0xFFFFFFFF])
                env.override(0x546D54, sequence(*values))
                return t
            yield case('cursor %x owner%s policy%d calls%d' % (fn, owner, policy, steps), fn, setup)

    for types in ((), (13,), (0, 5), (0, 0, 11), (0, 0, 0)):
        for change in ('none', 'null', 'replace') if types and types[-1] else ('none',):
            def setup(env, types=types, change=change):
                t = base(env, salt)
                prior = obj(env, 0x2BC, 'previous-popup')
                other = obj(env, 0x2BC, 'replacement-popup')
                vv = obj(env, 0x18, 'previous-vtable')
                env.put(prior, vv)
                env.put(other, vv)
                for previous in (prior, other):
                    for off in (0x254, 0x258):
                        o = obj(env, 0x44, 'previous-surface')
                        env.put(o + 0x40, salt & ~1)
                        env.put(previous + off, o)
                def query(env, call):
                    n = env.calls_so_far(query_stub)
                    if n == len(types):
                        if change == 'null': env.put(t['p'] + 0x164, 0)
                        if change == 'replace': env.put(t['p'] + 0x164, other)
                    return types[min(n-1, len(types)-1)]
                query_stub = env.stub('previous-type', 'thiscall', 0, query)
                env.put(vv + 0x10, query_stub)
                def closed(env, call):
                    env.put(t['log'], call.receiver, env.get(call.receiver + 0x254), env.get(call.receiver + 0x258))
                    return 0
                env.put(vv + 0x14, env.stub('previous-closed', 'thiscall', 0, closed))
                env.put(t['p'] + 0x164, prior if types else 0)
                env.override(0x546D54, returns(0xFFFFFFFF))
                return t
            yield case('previous %s %s' % (types, change), 0x43A760, setup)

    for bits, held, timer, elapsed in [(0,False,93,7),(0x40000000,False,93,7),(0x80000000,False,93,7),(0xC0000003,False,93,7),(0x20000000,False,93,7),(0x10000000,False,93,7),(1,False,93,7),(0x82,False,93,7),(0x40000000,True,9,3),(0x80000000,True,3,3),(0x20000000,True,2,3),(0x10000000,True,0,0),(0x40000000,True,0x80000010,0x7FFFFFFF),(0x40000000,True,7,0xFFFFFFFF)]:
        def setup(env, bits=bits, held=held, timer=timer, elapsed=elapsed):
            t = base(env, salt)
            inp = obj(env, 0x248, 'input-state')
            env.put(0x537200, inp)
            env.put(inp + 0x1CC, 1)
            env.put(inp + 0x1D4, 1)
            env.put(inp + 0x1DC, *range(31,43))
            env.put(inp + 0x20C, bits if held else 0)
            env.put(t['p'] + 0x16C, timer)
            env.put(0x53720C, elapsed)
            env.put(0x528A60, 173)
            env.put(0x528A64, 37)
            masks = [0x10000000,0x20000000,0x40000000,0x80000000,1,2,4,8,16,32,64,128]
            env.override(0x546CE4, lambda env,c: 0x8000 if bits & masks[c.arguments[0]-31] else 0)
            replacement = obj(env, 0x2BC, 'selected-replacement')
            env.put(replacement, t['av'])
            env.put(replacement + 0x2B8, salt)
            def command(env, call):
                env.put(t['log'], call.receiver, *call.arguments, env.get(t['active']+0x2B8), env.get(t['p']+0x16C))
                env.put(t['p']+0x160, replacement)
                env.put(0x528A60, 191)
                env.put(0x528A64, 43)
                return 0x80004005
            env.put(t['v']+0x2C, env.stub('selection-replaces-popup', 'thiscall', 2, command))
            return t
        yield case('input %x held%s timer%x elapsed%x' % (bits, held, timer, elapsed), 0x4396F0, setup)
    for null, first in ((True,0),(False,salt)):
        def setup(env, null=null, first=first):
            t=base(env,salt)
            env.put(t['p']+0x160, 0 if null else t['active'])
            env.put(t['p']+0x170, first)
            return t
        yield case('input early %s %x' % (null,first), 0x4396F0, setup)

    for mode in ('no-front-holder','no-front','no-back','copy-error','simple','flip','flip-no-holder','flip-no-front','flip-no-back','second-error','replacement'):
        def setup(env, mode=mode):
            t=base(env,salt)
            def blt(env, call):
                n=env.calls_so_far(blt_stub)
                return 0x80004005 if mode=='copy-error' or (mode=='second-error' and n==2) else 0
            blt_stub=env.stub('back-copy', 'stdcall', 6, blt)
            new,_,_=surface(env,'replacement-front',(19,23,71,97))
            holder=obj(env, 0x30,'replacement-holder')
            env.put(holder+0x2C,new)
            def flip(env,call):
                if mode=='flip-no-holder': env.put(t['display']+0x10,0)
                if mode=='flip-no-front': env.put(t['h1']+0x2C,0)
                if mode=='flip-no-back': env.put(t['h2']+0x2C,0)
                if mode=='replacement':
                    env.put(t['display']+0x10,holder)
                return 0x80004005
            graphics(env,t,flags=0 if mode=='simple' else 2,flip=flip)
            env.put(t['v2']+0x14,blt_stub)
            if mode=='no-front-holder': env.put(t['display']+0x10,0)
            if mode=='no-front': env.put(t['h1']+0x2C,0)
            if mode=='no-back': env.put(t['h2']+0x2C,0)
            return t
        yield case('copy '+mode,0x4CAB10,setup,key='display')

    for start,hdc,draw,finish,change in ((0,0,1,1,False),(salt,0,1,0,False),(salt,0,1,salt,True),(salt,0x12340,0,1,False),(salt,0x12340,salt,0,False),(salt,0x12340,salt,salt,True)):
        def setup(env,start=start,hdc=hdc,draw=draw,finish=finish,change=change):
            t=graphics(env,base(env,salt))
            mfc(env,hdc)
            other=obj(env, 0x2BC,'draw-replacement')
            ov=obj(env, 0x1FC,'draw-replacement-vtable')
            env.put(other,ov)
            def begin(env,call):
                if change: env.put(t['p']+0x160,other)
                return start
            env.put(t['av']+0x1D8,env.stub('draw-begin','thiscall',0,begin))
            def getdc(env,call):
                env.put(t['log'],call.receiver,*call.arguments,env.get(call.arguments[1]))
                env.put(call.arguments[1],hdc)
                env.put(t['log']+32,call.arguments[1])
                return 0x80004005
            env.put(t['v2']+0x44,env.stub('GetDC','stdcall',2,getdc))
            new_interface = obj(env, 4, 'post-paint-interface')
            new_methods = obj(env, 0x6C, 'post-paint-methods')
            env.put(new_interface, new_methods)
            env.put(new_methods + 0x68, env.stub('post-paint-ReleaseDC', 'stdcall', 2, returns(0x80004005)))
            def paint(env,call):
                env.put(t['log']+48,call.receiver,*call.arguments)
                if change:
                    env.put(env.get(t['log']+32),hdc+0x100)
                    env.put(t['p']+0x160,t['active'])
                    env.put(t['back'] + 8, new_interface)
                return draw
            for vv in (ov,t['av']):
                env.put(vv+0x1DC,env.stub('paint','thiscall',2,paint))
                env.put(vv+0x1E0,env.stub('draw-end','thiscall',0,returns(finish)))
            env.put(t['v2']+0x68,env.stub('ReleaseDC','stdcall',2,returns(0)))
            return t
        yield case('draw %x HDC%x paint%x end%x replace%s' % (start,hdc,draw,finish,change),0x439590,setup)
    for fn, field in ((0x439590,0x160),(0x439630,0x15C),(0x439630,0x160)):
        def setup(env,field=field):
            t=base(env,salt)
            backing,_,_=surface(env,'backing')
            env.put(t['p']+0x15C,backing)
            env.put(t['p']+field,0)
            return t
        yield case('early %x null%x'%(fn,field),fn,setup)
    for change in (False,True):
        def setup(env,change=change):
            t=graphics(env,base(env,salt),blt=returns(0x80004005))
            backing,_,_=surface(env,'saved',(salt,29,11,0xFFFFFFF1))
            other,_,_=surface(env,'reloaded-backing',(91,92,93,94))
            env.put(t['p']+0x15C,backing)
            def copy(env,call):
                rect_copy(env,call)
                if change:
                    env.put(t['p']+0x15C,other)
                    env.put(t['h2']+0x2C,t['front'])
                return 0
            env.override(0x546D58,copy)
            return t
        yield case('restore reload%s'%change,0x439630,setup)
    for kind in ('no-dimensions','no-popup','no-manager','create-error','success','old-backing','reload'):
        yield case('capture '+kind,0x439480,capture_setup(kind,salt))
