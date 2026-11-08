"""Original-backed scene/controller lifetime and resize cases."""
from clawparity.cases import Case

def object0(env, *args, **kwargs):
    kwargs.setdefault("fill", 0)
    return env.object(*args, **kwargs)


NEW, DELETE = 0x4F63EC, 0x4F6428
MAP_CLEAR = (0x4CA300, 0x4CDF40, 0x4D0240, 0x4D4370, 0x4D6290)
DESTRUCTORS = (0x4CE9C0, 0x4CF0C0, 0x4CF180, 0x4CF2A0,
               0x4CF820, 0x4CF8C0, 0x4CF960, 0x4CF9F0)
WRAPPERS = (0x4CE9A0, 0x4CF0A0, 0x4CF160, 0x4CF280,
            0x4CF800, 0x4CF8A0, 0x4CF940, 0x4CF9D0)


def physical(env):
    def atomic(delta):
        def effect(e, c):
            value = (e.get(c.arguments[0]) + delta) & 0xffffffff
            e.put(c.arguments[0], value)
            return value
        return effect
    env.override(0x5469e8, atomic(-1))
    env.override(0x5469ec, atomic(1))
    def copy(e, c):
        e.write(c.arguments[0], e.read(c.arguments[1], 16))
        return 1
    env.override(0x546d58, copy)


def recorder(env, owner, argc=1, mutation=None, name='child destructor'):
    log = object0(env, 4 + 64 * 80, name + ' observations')
    def effect(e, c):
        index = e.get(log)
        e.put(log + 4 + index * 80, c.receiver, *c.arguments)
        e.write(log + 4 + index * 80 + 16, e.read(owner, 64))
        e.put(log, index + 1)
        if mutation:
            mutation(e, c, index)
        return 0x71c39a25
    return env.stub(name, 'thiscall', argc, effect)


def child(env, owner, name, slot=4, mutation=None):
    obj = object0(env, 16, name, words=[0, 0x13121110, 0x23222120, 0x33323130])
    vt = object0(env, 0x60, name + ' vtable')
    env.put(obj, vt)
    env.put(vt + slot, recorder(env, owner, mutation=mutation, name=name))
    return obj


def map_object(env, address, owner, populated, salt=7, mutate=False):
    # MFC CMapStringToPtr: vtable, buckets, bucket count, count, free, blocks, growth.
    env.put(address, 0x510054, 0, 5, 0, 0, 0, 4)
    if not populated:
        return
    buckets = object0(env, 20, 'genuine hash buckets')
    nodes = [object0(env, 16, 'association ' + str(i)) for i in range(4)]
    env.put(address + 4, buckets)
    env.put(address + 12, 4)
    values = [child(env, owner, 'map value '+str(i)) if i != 1 else 0 for i in range(4)]
    if mutate:
        replacement = child(env, owner, 'callback published replacement')
        def publish(e, c, index):
            e.put(nodes[2] + 12, replacement)
        vt = env.get(values[0])
        env.put(vt + 4, recorder(env, owner, mutation=publish, name='map mutation'))
    for i, node in enumerate(nodes):
        key = ('key-%d-%d' % (salt, i)).encode() + b'\0'
        text = object0(env, 12 + len(key), 'CString allocation '+str(i))
        env.put(text, 1, len(key)-1, len(key)-1)
        env.write(text + 12, key)
        bucket = (1, 1, 3, 4)[i]
        env.put(node, nodes[1] if i == 0 else 0, bucket, text+12, values[i])
    env.put(buckets + 4, nodes[0])
    env.put(buckets + 12, nodes[2], nodes[3])


def controller(function, populated, salt, mutate=False):
    def setup(env):
        physical(env)
        obj = object0(env, 0x70, 'controller')
        env.put(obj, 0x50becc, salt, salt ^ 0x5a5a5a5a, 0x11224488)
        released_state=object0(env,0x70,'state at receiver deallocation')
        def dispose(e,c):
            pointer=c.arguments[0]
            if pointer==obj:
                e.write(released_state,e.read(obj,0x70))
            if pointer:
                e.release(pointer)
            return 0
        env.override(DELETE,dispose)
        if function in (0x4CE9A0, 0x4CE9C0, 0x4CEEF0):
            env.put(obj+4, *([0]*12))
            if populated:
                for off in (0x28, 0x20, 4, 8, 12, 16, 20, 24, 44, 36):
                    env.put(obj+off, child(env, obj, 'scene field %x'%off, slot=0 if off==0x20 else 4))
                graphics = object0(env, 0x480, 'graphics context')
                env.put(obj+0x1c, graphics)
                if mutate:
                    later=child(env,obj,'replacement later manager')
                    replacement=child(env,obj,'replacement current manager')
                    def republish(e,c,index):
                        e.put(obj+0x28,replacement)
                        e.put(obj+8,later)
                    vt=env.get(env.get(obj+0x28))
                    env.put(vt+4,recorder(env,obj,mutation=republish,name='scene publication'))
                # Original graphics destructor walks two real empty MFC lists and array.
            return obj
        list_kind = function in (0x4CF280, 0x4CF2A0, 0x4CF8A0, 0x4CF8C0)
        if list_kind:
            env.put(obj+0x10, 0x5107bc, 0, 0, 0, 0, 0, 4)
            if populated:
                a,b = object0(env, 12,'list node A'),object0(env, 12,'list node B')
                env.put(a,b,0,child(env,obj,'list A'))
                env.put(b,0,a,child(env,obj,'list B'))
                env.put(obj+0x14,a,b,2)
        else:
            map_object(env,obj+16,obj,populated,salt,mutate)
            if function in (0x4CF0A0,0x4CF0C0):
                map_object(env,obj+0x2c,obj,populated,salt+1)
                map_object(env,obj+0x48,obj,populated,salt+2)
                env.put(obj+0x64,0x93af0712)
            elif function in (0x4D4370,):
                env.put(obj+0x64,0x97af0412)
            if function in (0x4CA2E0,0x4CF800,0x4CF820):
                env.put(obj+0x2c,0xa9876543)
        return obj
    return setup


def ready(missing, result, world_change=None):
    def setup(env):
        obj=object0(env, 0x40,'scene readiness')
        world=object0(env, 16,'world')
        vt=object0(env, 0x20,'display callbacks')
        display=object0(env, 32,'display',words=[vt])
        env.put(obj+4,display,0x31,0x43,0x55,0x67)
        env.put(obj+0x24,world)
        if missing:
            env.put(obj+missing,0)
        log=object0(env, 72,'readiness observation')
        def test(e,c):
            e.put(log,c.receiver)
            e.write(log+4,e.read(obj,64))
            if world_change is not None:
                e.put(obj+0x24,world if world_change else 0)
            return result
        env.put(vt+0x14,env.stub('display ready','thiscall',0,test))
        return obj
    return setup


def shutdown(salt):
    def setup(env):
        obj=object0(env, 0x70,'sound controller')
        vt=object0(env, 0x60,'sound vtable')
        env.put(obj,vt)
        env.put(0x54316c,salt,salt^0xffffffff)
        log=object0(env, 16,'published globals during callback')
        def observe(e,c):
            e.put(log,c.receiver,e.get(0x54316c),e.get(0x543170))
            e.put(0x54316c,0xafe11433,0x629ab244)
            return 0
        env.put(vt+0x58,env.stub('sound shutdown','thiscall',0,observe))
        return obj
    return setup


def resize_equal(width,height,depth):
    def setup(env):
        physical(env)
        obj=object0(env, 0x40,'scene')
        display=object0(env, 0x40,'display')
        primary=object0(env, 0x30,'primary',words=[0x5138d8])
        env.put(obj+4,display)
        env.put(display+16,primary)
        env.put(primary+16,width,height,depth^8)
        return obj
    return setup


def resize_real(width, height, world_kind, primary_failure=False, world_publish=None, mode_failure=False):
    def setup(env):
        physical(env)
        scene=object0(env,0x40,'resizing scene')
        display=object0(env,0x40,'display controller')
        primary=object0(env,0x30,'real primary wrapper',words=[0x5138d8])
        back=object0(env,0x34,'real back wrapper',words=[0x50e8e4])
        graphics=object0(env,0x900,'graphics context')
        env.put(scene+4,display)
        env.put(scene+0x1c,graphics)
        env.put(display+0xc,scene,primary,back)
        env.put(primary+0xc,scene,640,480,32)
        # The second surface already has the requested geometry, independently of primary.
        env.put(back+0xc,scene,width,height,32)
        world=object0(env,0x50,'world')
        if world_kind:
            env.put(scene+0x24,world)
        if world_kind==2:
            planes=object0(env,8,'world planes')
            env.put(world+0x38,planes,2)
            for i in range(2):
                plane=object0(env,0x100,'plane '+str(i))
                env.put(plane+0x30,2048,1024)
                env.put(planes+i*4,plane)
        if primary_failure:
            env.put(scene+0x1c,0)
            return scene
        old=object0(env,0xbc,'old primary surface',words=[0x5136c0])
        node=object0(env,12,'old primary list node',words=[0,0,old])
        env.put(old+4,node)
        env.put(primary+0x2c,old)
        env.put(graphics+0x3b8,0x51000c,node,node,1,0,0,4)
        dd=object0(env,4,'DirectDraw interface')
        ddvt=object0(env,0x80,'DirectDraw methods')
        surface=object0(env,4,'physical primary surface')
        svt=object0(env,0x90,'surface methods')
        env.put(graphics,dd)
        env.put(0x54139c,0,0,0,0)
        env.put(dd,ddvt)
        env.put(surface,svt)
        mode=object0(env,0x6c,'physical display mode')
        env.put(mode,0x6c)
        env.put(mode+8,height,width,width*4)
        env.put(mode+0x48,32,0x40,0,32,0xff0000,0xff00,0xff)
        log=object0(env,64,'physical resize observations')
        def set_mode(e,c):
            e.put(log,*c.arguments)
            if mode_failure:
                return 0x88760004
            e.put(mode+8,c.arguments[2],c.arguments[1],max(1,c.arguments[1])*4)
            if world_publish is not None:
                e.put(scene+0x24,world if world_publish else 0)
            return 0
        def describe_mode(e,c):
            e.write(c.arguments[1],e.read(mode,0x6c))
            return 0
        def create(e,c):
            e.put(c.arguments[2],surface)
            return 0
        env.put(ddvt+0x54,env.stub('IDirectDraw SetDisplayMode','stdcall',4,set_mode))
        env.put(ddvt+0x30,env.stub('IDirectDraw GetDisplayMode','stdcall',2,describe_mode))
        env.put(ddvt+0x18,env.stub('IDirectDraw CreateSurface','stdcall',4,create))
        env.put(svt+0x58,env.stub('IDirectDrawSurface GetSurfaceDesc','stdcall',2,describe_mode))
        return scene
    return setup


def cases(random_source):
    salt=random_source.randrange(1,0x7fffffff)
    for f in MAP_CLEAR+(0x4CA2E0,0x4CDF30)+DESTRUCTORS:
        for populated in (False,True):
            yield Case('%x %s'%(f,'populated' if populated else 'empty'),f,
                       controller(f,populated,salt),receiver=lambda x:x)
    for f in WRAPPERS:
        for flag in (0,1,2,0x800000ff):
            yield Case('%x flags %x'%(f,flag),f,controller(f,True,salt),
                       receiver=lambda x:x,arguments=(flag,))
    for f in MAP_CLEAR:
        yield Case('%x callback replaces later value'%f,f,controller(f,True,salt,True),receiver=lambda x:x)
    for f in (0x4CF150,0x4CF930):
        yield Case('constant %x'%f,f)
    for off in (4,8,12,16,20,36):
        yield Case('readiness missing %x'%off,0x4CEFC0,ready(off,1),receiver=lambda x:x)
    for result in (0,1,0xffffffff):
        for change in (None,False,True):
            yield Case('readiness result %x world %s'%(result,change),0x4CEFC0,
                       ready(0,result,change),receiver=lambda x:x)
    for full in (False,True):
        yield Case('scene cleanup '+str(full),0x4CEEF0,controller(0x4CEEF0,full,salt),receiver=lambda x:x)
    yield Case('cleanup callback republishes current and later fields',0x4CEEF0,
               controller(0x4CEEF0,True,salt,True),receiver=lambda x:x)
    yield Case('global shutdown ordering',0x4CFA80,shutdown(salt),receiver=lambda x:x)
    yield Case('same dimensions ignores depth',0x4CF020,resize_equal(640,480,32),receiver=lambda x:x,arguments=(640,480,32))

    yield Case('real primary resize rejects absent graphics',0x4CF020,
               resize_real(800,600,0,True),receiver=lambda x:x,arguments=(800,600,32))
    for width,height,world in ((800,600,0),(640,600,1),(800,600,2),(0,600,1),(800,0,1)):
        yield Case('real resize %dx%d world %d'%(width,height,world),0x4CF020,
                   resize_real(width,height,world),receiver=lambda x:x,arguments=(width,height,32))
    for publish in (False,True):
        yield Case('real resize republishes world '+str(publish),0x4CF020,
                   resize_real(800,600,not publish,world_publish=publish),receiver=lambda x:x,arguments=(800,600,32))

    yield Case('readiness publishes initially missing world',0x4CEFC0,ready(36,1,True),receiver=lambda x:x)
    yield Case('real primary SetDisplayMode physical failure',0x4CF020,
               resize_real(800,600,1,mode_failure=True),receiver=lambda x:x,arguments=(800,600,32))
