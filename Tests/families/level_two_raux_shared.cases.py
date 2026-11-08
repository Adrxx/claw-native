"""Original-behavior cases for the shared Level 2 raux entries."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def dput(env, a, value):
    env.write(a, struct.pack('<d', value))


def common(env, salt=0):
    obj = env.object(0x460, 'raux', fill=0x69)
    root = env.object(0x180, 'root', fill=0)
    desc = env.object(0x1c0, 'descriptor', fill=0)
    actor = env.object(0x1c0, 'actor', fill=0)
    world = env.object(0x100, 'world', fill=0)
    env.put(obj + 0xc, root, desc)
    env.put(obj + 0x128, root, actor)
    env.put(root + 0xc, world)
    env.put(actor + 0xc, world)
    env.put(actor + 8, 0x451020 + salt)
    env.put(desc + 0x1c, 0x11223344 + salt)
    env.put(obj + 0x340, 0)
    env.put(obj + 0x350, 0)
    env.put(obj + 0x40c, 0)
    env.put(actor + 0x190, 0)
    env.put(0x537668 + 0x18, 0)
    env.put(0x532c0c, 0)
    return dict(obj=obj, root=root, desc=desc, actor=actor, world=world)


def animation(env, token, nonnull=True):
    frame = env.object(0x40, 'frame', fill=0)
    env.put(frame + 0x1c, 0x67452301)
    array = env.object(4, 'frames', words=[frame])
    anim = env.object(0x20, 'animation', fill=0)
    env.put(anim + 0xc, array, 1)
    return anim if nonnull else 0


def destruct(flags=0, capacity=32, count=1):
    def setup(env):
        t = common(env)
        env.put(t['obj'] + 0x2fc, capacity)
        if capacity > 32:
            env.put(t['obj'] + 0x300, env.object(16, 'bitset', fill=0xa9))
        for off in (0x1a4, 0x1a8):
            s = env.object(24, 'string', words=[count, 4, 8, 0x64636261, 0])
            env.put(t['obj'] + off, s + 12)
        def decrement(env, call):
            a = call.arguments[0]
            value = (env.get(a) - 1) & 0xffffffff
            env.put(a, value)
            return value
        env.override(0x5469e8, decrement)
        return t
    return setup


def table(env, base, low, high, stride, callback):
    records = env.object((high - low + 1) * stride, 'dispatch-records', fill=0)
    for i in range(high - low + 1):
        env.put(records + i * stride, callback)
    env.put(base + 8, low, high, records, records, stride, 0, 0x11223344)
    return records


def dispatch(event, null=False, stride=4):
    def setup(env):
        t = common(env)
        log = env.object(16, 'callback-log', fill=0)
        def callback(env, call):
            env.put(log, call.receiver, env.get(0x5349d8), env.get(t['obj'] + 0x20), 0x77665544)
            env.put(t['obj'] + 0x21c, 0xbadc0ffe)
            return 0x12341234
        cb = env.stub('dispatch', 'thiscall', 0, callback)
        table(env, 0x5349b8, -2, 2, stride, 0 if null else cb)
        table(env, 0x537878, -8, 8, stride, cb)
        return t
    return setup


def jump(mode, cls=1, overhead=0, acceleration=(1., 2., 3.), vertical=4., limit=1000., x=100., sound=False):
    def setup(env):
        t = common(env)
        o = t['obj']
        env.put(o + 0x18c, mode)
        for offset, value in zip((0x38, 0x40, 0x48), acceleration):
            dput(env, o + offset, value)
        for offset, value in ((0x68,x),(0x70,17.25),(0x78,vertical),(0x80,limit),(0x98,limit)):
            dput(env, o + offset, value)
        env.put(t['root'] + 0x50, 27)
        env.put(t['root'] + 0x124, 2)
        env.put(t['actor'] + 0x40, 2 if mode != 2 else 0)
        env.put(o + 0x138, 7)
        env.put(o + 0x140, 11)
        for off in (0x118, 0x128, 0x138):
            env.put(t['actor'] + off, 13 + off)
            env.put(t['actor'] + off + 8, 19 + off)
        tilemap = env.object(0x60, 'tilemap', fill=0)
        grid = env.object(0x94, 'grid', fill=0)
        indices = env.object(4, 'tile-indices', words=[0])
        rows = env.object(4, 'row-indices', words=[0])
        tile = env.object(4, 'tile', fill=0)
        tiles = env.object(4, 'tiles', words=[tile])
        vtable = env.object(0x24, 'tile-vtable', fill=0)
        log = env.object(4, 'tile-call-count', fill=0)
        def classify(env, call):
            n = env.get(log)
            env.put(log, n + 1)
            accepted = {1:1, 2:2, 3:3}.get(cls, 3)
            return cls if n < accepted else overhead
        env.put(vtable + 0x20, env.stub('tile-classify', 'thiscall', 2, classify))
        env.put(tile, vtable)
        env.put(grid + 0x20, indices, rows)
        env.put(grid + 0x30, 512, 512)
        env.put(grid + 0x8c, 10, 10)
        env.put(tilemap + 0x4c, tiles)
        env.put(tilemap + 0x5c, grid)
        env.put(t['world'] + 0x24, tilemap)
        if sound:
            env.put(o + 0x40c, env.object(0x20, 'sound', fill=0))
        return t
    return setup


def cases(random_source):
    for cap in (0, 32, 64):
        for count in (1, 2):
            yield Case(f'destroy bits {cap} refs {count}', 0x404e40, destruct(capacity=cap,count=count), receiver=lambda t:t['obj'])
    for flag in (0,1,2,0x100,0x101,0xfffffffe,0xffffffff):
        yield Case(f'deleting destroy {flag:x}', 0x40e190, destruct(), receiver=lambda t:t['obj'], arguments=(flag,))
    for nonnull in (False,True):
        def startup(env, nonnull=nonnull):
            t = common(env)
            env.put(t['actor'] + 0x190, 0x12345678)
            env.put(t['obj'] + 0x350, animation(env,t,nonnull))
            return t
        yield Case(f'startup animation {nonnull}', 0x405060, startup, receiver=lambda t:t['obj'])
    for event in (-4,-2,0,2,4):
        for null in (False,True):
            for stride in (4,12):
                yield Case(f'dispatch {event} null {null} stride {stride}', 0x40e280, dispatch(event,null,stride),receiver=lambda t:t['obj'],arguments=(event,))
    pairs = [(0,1),(-1,0),(0x7fffffff,0x80000000),(0xffffffff,0x12345678)]
    pairs += [(random_source.getrandbits(32),random_source.getrandbits(32)) for _ in range(12)]
    for x,y in pairs:
        def reset(env,x=x,y=y):
            t=common(env); env.put(t['obj']+0x450,x,y); return t
        yield Case(f'reset {x:x} {y:x}',0x40e560,reset,receiver=lambda t:t['obj'])
    for mode in (0,1,2,3,0xffffffff):
        def tick(env,mode=mode):
            t=common(env)
            vt=env.object(0x4c,'vtable',fill=0)
            def callback(env,call):
                env.put(t['obj']+0x21c,call.receiver,env.get(t['actor']+0x190),env.get(0x5430c4)); return 0xaabbccdd
            env.put(vt+0x48,env.stub('tick-callback','thiscall',0,callback))
            env.put(t['obj'],vt);env.put(0x53c9c0,mode);env.put(0x5430c4,173);return t
        yield Case(f'tick mode {mode}',0x40e580,tick,receiver=lambda t:t['obj'])
    for kind in (0,1,2):
        def signal(env,kind=kind):
            manager=env.object(0x110,'manager',fill=0)
            actor=env.object(0x20,'global-actor',fill=0x73)
            env.put(manager+0x6c,actor if kind==2 else 0)
            env.put(0x537e88,manager if kind else 0)
        yield Case(f'signal {kind}',0x420590,signal)
    for function,slot in ((0x455350,0x60),(0x4a07e0,0x9c)):
        for flags in (0,0x10000,0xffffffff,random_source.getrandbits(32)):
            def forward(env,slot=slot,flags=flags):
                t=common(env); vt=env.object(0xa0,'vtable',fill=0)
                arg=env.object(16,'flag-argument',words=[0x12345678,0x87654321,flags,0x11223344])
                def callback(env,call):
                    env.put(t['obj']+0x220,call.receiver,env.get(arg+8));return 0xbadf00d
                env.put(vt+slot,env.stub('forward-callback','thiscall',0,callback));env.put(t['obj'],vt);t['arg']=arg;return t
            yield Case(f'forward {function:x} flags {flags:x}',function,forward,receiver=lambda t:t['obj'],arguments=((lambda t:t['arg']),) if function==0x4a07e0 else ())
    for mode in (3,2,0):
        for cls in (0,1,2,3,4):
            for overhead in (0,1):
                yield Case(f'jump {mode} class {cls} overhead {overhead}',0x44e620,jump(mode,cls,overhead,limit=1000. if mode==3 else -1000.),receiver=lambda t:t['obj'])
    for acceleration in ((0.,0.,0.),(1e-30,0.,0.),(0.,-2.,0.),(-2.,3.,-4.)):
        yield Case(f'jump acceleration {acceleration}',0x44e620,jump(3,acceleration=acceleration),receiver=lambda t:t['obj'])
    for mode,x,limit in ((3,100.,-1000.),(2,100.,1000.),(0,float('nan'),1.)):
        yield Case(f'jump early {mode} {x}',0x44e620,jump(mode,x=x,limit=limit),receiver=lambda t:t['obj'])
    for accel in ((.1,0.,0.),(0.,.1,0.),(0.,0.,-.1)):
        yield Case(f'jump normalize {accel}',0x44e620,jump(3,acceleration=accel,sound=True),receiver=lambda t:t['obj'])
    for count in (-2147483648,-1,0,1,2147483647):
        def update(env,count=count):
            t=common(env)
            env.put(t['obj']+0x2fc,32,0x10)
            env.put(t['obj']+0x45c,1)
            manager=env.object(0x110,'manager',fill=0)
            target=env.object(0x20,'signaled-actor',fill=0x73)
            env.put(manager+0x10c,count)
            env.put(manager+0x6c,target)
            env.put(0x537e88,manager)
            return t
        yield Case(f'update manager count {count}',0x40e660,update,receiver=lambda t:t['obj'],arguments=(17,))
    # All inherited exception profiles are explicit and seed-independent.
    # The base chain computes its actual final C0 and sticky flags; the full
    # environment comparison checks them, without seeding a fitted C0.
    for status in (0, 0x20, 0x21):
        for ticks in (0, 1, 0xffffffff):
            for x,y in ((7,13),(-101,82),(0x7fffffff,0x80000000)):
                def construct(env,x=x,y=y,status=status,ticks=ticks):
                    env.entry_x87_status(status)
                    t=common(env)
                    root=t['root']; world=t['world']
                    env.put(root+0x6c,t['desc'])
                    env.put(root+0x4c,x,y)
                    env.put(0x537210,ticks)
                    registry=env.object(0x40,'registry',fill=0)
                    env.put(registry+0x18,1)
                    env.put(world+0x14,registry)
                    env.put(world+0x28,registry)
                    tilemap=env.object(0x70,'tilemap',fill=0)
                    env.put(world+0x24,tilemap)
                    return t
                yield Case(f'construct {x} {y} incoming SW {status:#x} clock {ticks:#x}',
                           0x40e0d0,construct,receiver=lambda t:t['obj'],
                           arguments=(lambda t:t['root'],))

    for mode in (0,2):
        for elapsed in (0,1,3,17):
            def ticking(env,mode=mode,elapsed=elapsed):
                t=common(env)
                a=animation(env,t)
                env.put(t['actor']+0x190,a)
                env.put(t['actor']+0x19c,23,1,1)
                env.put(t['actor']+0x1a8,0x22446688,0x336699cc)
                vt=env.object(0x4c,'tick-vtable',fill=0)
                def callback(env,call):
                    env.put(t['obj']+0x218,call.receiver,env.get(t['actor']+0x19c),env.get(t['actor']+0x1ac));return 0
                env.put(vt+0x48,env.stub('active-tick','thiscall',0,callback))
                env.put(t['obj'],vt);env.put(0x53c9c0,mode);env.put(0x5430c4,elapsed)
                return t
            yield Case(f'active tick mode {mode} elapsed {elapsed}',0x40e580,ticking,receiver=lambda t:t['obj'])
    for i in range(20):
        accel=tuple(random_source.uniform(-8.,8.) for _ in range(3))
        vertical=random_source.uniform(-20.,20.)
        yield Case(f'jump random coefficients {i}',0x44e620,jump(3,acceleration=accel,vertical=vertical,sound=bool(i%2)),receiver=lambda t:t['obj'])
    for mode in (3,2,0):
        for delta in (-0.125,0.,0.125):
            limit=200. if mode==3 else 0.
            yield Case(f'jump boundary mode {mode} delta {delta}',0x44e620,jump(mode,limit=limit+delta),receiver=lambda t:t['obj'])
