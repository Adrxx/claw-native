"""Original-only seagull construction, dispatch, hit and idle witnesses."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_TOP


def put_double(env, address, value):
    env.write(address, struct.pack('<d', value))


def animation(env, tag):
    frame = env.object(0x30, tag+' frame', fill=0)
    env.put(frame+0x1c, 37)
    frames = env.object(4, tag+' frame list', words=[frame])
    anim = env.object(0x20, tag, fill=0)
    env.put(anim+0xc, frames, 1)
    return anim


def basic(env, fill=0x69, receiver_prefix=0):
    obj = env.object(0x440 + receiver_prefix, 'seagull', fill=fill) + receiver_prefix
    actor = env.object(0x220, 'actor', fill=0)
    desc = env.object(0x180, 'description', fill=0)
    env.put(obj+0xc, actor, desc)
    env.put(obj+0x12c, actor)
    env.put(actor+0x6c, desc)
    env.put(desc+0x1c, 0x13579)
    env.put(obj+0x418, animation(env, 'flying'))
    env.put(obj+0x41c, animation(env, 'hit high'), animation(env, 'hit low'), 0, 0, 0, 0)
    env.put(obj+0x138, 17)
    env.put(obj+0x140, 43)
    for off, value in [(0x118,11),(0x120,31),(0x128,19),(0x130,47),(0x138,23),(0x140,53)]:
        env.put(actor+off, value)
    env.put(actor+0x190, 0x2468)
    env.put(0x537680, 0)  # original name tree is empty
    env.put(0x532c0c, 0)
    return {'obj':obj, 'actor':actor, 'desc':desc}


def idle_setup(left, right, flags, sentinel, speed, fill):
    def setup(env):
        t=basic(env, fill)
        obj, actor=t['obj'],t['actor']
        put_double(env,obj+0x68,left); put_double(env,obj+0x98,right)
        put_double(env,0x50f550,speed)
        env.put(actor+0x40,flags)
        for i,off in enumerate((0x118,0x128,0x138)):
            if sentinel & (1<<i): env.put(actor+off,0x80000000)
        return t
    return setup


def with_x87_status(setup, status):
    """Elect inherited exception flags without changing the original inputs."""
    def prepare(env):
        tokens = setup(env)
        env.entry_x87_status(status)
        return tokens
    return prepare


def destructor_setup(bits, ref1, ref2, fill):
    def setup(env):
        t=basic(env,fill); obj=t['obj']
        env.put(obj+0x2fc,bits)
        if bits>32: env.put(obj+0x300,env.object(16,'owned bit storage',fill=0x83))
        for off,ref in ((0x1a4,ref1),(0x1a8,ref2)):
            if ref is None: env.put(obj+off,env.get(0x52e1c8)+12)
            else:
                s=env.object(24,'string allocation',fill=0x4d)
                env.put(s,ref);env.put(obj+off,s+12)
        def decrement(env,call):
            a=call.arguments[0]; value=(env.get(a)-1)&0xffffffff
            env.put(a,value);return value
        env.override(0x5469e8,decrement)
        return t
    return setup


def hit_setup(rands, change, fill):
    def setup(env):
        t=basic(env,fill);obj,actor=t['obj'],t['actor']
        other=env.object(0x180,'hit actor',fill=0x57)
        env.put(other+8,0x123456)
        env.put(other+0x138,0x80000000)
        env.put(actor+0x38,0xffffffff) # original effect spawn declines this actor
        put_double(env,obj+0x68,72.25);put_double(env,obj+0x70,-19.75)
        record=env.object(32,'callback witness',fill=0xad)
        def callback(env,call):
            env.put(record,call.receiver,call.arguments[0],env.get(actor+8),env.get(other+8),env.get(obj+0x3d4),env.get(t['desc']+0x1c))
            if change:
                env.put(other+8,0x822003)
                env.put(t['desc']+0x1c,0x6abc)
            return 0xdeadbeef
        vt=env.object(0x40,'hit vtable',fill=0);env.put(vt+0x28,env.stub('hit notification','thiscall',1,callback));env.put(obj,vt)
        env.override(0x4a3050,sequence(*rands))
        env.put(0x537210,0x76543210)
        t['other']=other
        return t
    return setup


def dispatch_setup(index, low, high, stride, fallback, fill):
    def setup(env):
        t=basic(env,fill);obj=t['obj']
        record=env.object(24,'dispatch witness')
        def callback(env,call):
            env.put(record,call.receiver,env.get(0x53c290),env.get(0x544b14),env.get(0x53c278),env.get(0x53c27c),env.get(0x53c280))
            return 0x63a875
        cb=env.stub('state callback','thiscall',0,callback)
        entries=env.object((high-low+1)*stride,'states',fill=0x75)
        for i in range(high-low+1):env.put(entries+i*stride,0 if fallback else cb)
        default=env.object(stride,'default state',words=[0 if fallback else cb])
        error=env.object(0x30,'error policy',fill=0);env.put(error+0xc,4)
        env.put(0x53c274,error,low,high,entries,default,stride,0,0xfeed)
        env.put(0x53763c,error,low-1,high+1,env.object((high-low+3)*stride,'base states'),default,stride,0,0xbeef)
        base=env.get(0x537648)
        for i in range(high-low+3):env.put(base+i*stride,cb)
        # Full source CPU inputs with distinct preservation witnesses.
        source=NativeSourceContext(72,1,0x7ff,0x5f3,0x1020304,0x1726354,obj,0x21314151,0x43536373,0x61718191,0x11223344,STACK_TOP,0x4873a0,0x847,0xffffffff,0x472,0,0)
        t['source']=source
        return t
    return setup


def constructor_image_alias_setup(fill):
    def setup(env):
        t = construct_setup(True, 0, 1.0, fill, receiver_prefix=0x64)(env)
        obj, actor, desc = t['obj'], t['actor'], t['desc']
        # Original4c7970 reads image+0x64 as a signed frame index. Alias that
        # read with the constructor's vtable store so its publication order is
        # observable. The preceding allocation prefix backs the image header.
        image = obj - 0x64
        image_frame = env.object(0x30, 'aliased image frame', fill=0)
        env.put(image_frame + 0x18, 7, 11, 29, 41)
        frame_word = env.object(4, 'aliased image frame word', words=[image_frame])
        # Guest x86 addressing wraps modulo32 bits; the old base vtable index
        # resolves to this live word without a large frame-array allocation.
        env.put(image + 0x14, (frame_word - 4 * 0x50dd34) & 0xffffffff)
        env.put(desc + 0x168, 0x50e000)
        manager = env.get(actor + 0x0c)
        resource_map(env, env.get(manager + 0x10), [('LEVEL_SEAGULL', image)])
        return t
    return setup


def cases(random_source):
    yield Case('constructor publishes derived vtable before aliased image lookup',
               0x486f50, constructor_image_alias_setup(random_source.randrange(1, 256)),
               receiver=lambda t: t['obj'], arguments=(lambda t: t['actor'],))
    # These profiles are fixed independently of the gate seed: ambient sticky
    # exceptions must survive while original arithmetic updates condition flags.
    for status in (0, 0x20, 0x21):
        for left, right in ((2.5, 2.5), (2.5, -3.25), (float('nan'), 2.0)):
            setup = idle_setup(left, right, 0x82, 0, -3.5, random_source.randrange(1, 256))
            yield Case(f'idle inherited SW {status:x} compare {left} {right}',
                       0x487830, with_x87_status(setup, status), receiver=lambda t: t['obj'])
        for function in (0x443170, 0x486f50):
            for scale in (1.0, 3.75):
                setup = construct_setup(True, 0, scale, random_source.randrange(1, 256))
                yield Case(f'construct inherited SW {status:x} {function:x} scale {scale}',
                           function, with_x87_status(setup, status),
                           receiver=lambda t: t['obj'], arguments=(lambda t: t['actor'],))
    for left,right in ((2.5,2.5),(2.5,-3.25),(0.0,-0.0),(float('nan'),2.0),(float('inf'),float('inf'))):
        for flags in (0x80,0x82,0xfffffffd,0xffffffff):
            for sentinel in (0,1,2,3,7):
                fill=random_source.randrange(1,256)
                yield Case(f'idle {left} {right} {flags:x} sentinel {sentinel}',0x487830,idle_setup(left,right,flags,sentinel,random_source.choice((0.0,1.25,-3.5)),fill),receiver=lambda t:t['obj'])
    for function in (0x443220,0x4872d0,0x443200,0x4872b0):
        for bits,ref1,ref2 in ((0,None,None),(32,1,3),(33,2,1),(65,0,2)):
            for flags in ((0,1,2,3,0x100,0x101) if function in (0x443200,0x4872b0) else (0,)):
                yield Case(f'destruct {function:x} bits {bits} refs {ref1} {ref2} flags {flags}',function,destructor_setup(bits,ref1,ref2,random_source.randrange(1,256)),receiver=lambda t:t['obj'],arguments=(flags,) if function in (0x443200,0x4872b0) else ())
    for function in (0x4877a0,0x4877d0,0x487800):
        for rands in ((0,0,49),(8,8,50),(0xffffffff,0x80000000,99),(100,101,100)):
            for change in (False,True):
                yield Case(f'hit {function:x} random {rands} mutation {change}',function,hit_setup(rands,change,random_source.randrange(1,256)),receiver=lambda t:t['obj'],arguments=(lambda t:t['other'],))
    for index,low,high in ((-2,-2,2),(2,-2,2),(0,-2,2),(-3,-2,2),(3,-2,2)):
        for stride in (4,12):
            for fallback in (False,True):
                yield Case(f'dispatch {index} stride {stride} base {fallback}',0x4873a0,dispatch_setup(index,low,high,stride,fallback,random_source.randrange(1,256)),receiver=lambda t:t['obj'],arguments=(index,),source_context=lambda t:t['source'],source_return_pc=0x4874aa)
    for function in (0x443170,0x486f50):
        for present in (False,True,"fallback","alternating"):
            for category in (0,0x2134,0x7654):
                for scale in (0.5,1.0,3.75,-2.0):
                    yield Case(f'construct {function:x} present {present} category {category} scale {scale}',function,construct_setup(present,category,scale,random_source.randrange(1,256)),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))


def resource_map(env, owner, items):
    head=0
    for name,value in reversed(items):
        key=env.object(len(name)+1,'resource key',data=name.encode()+b'\0')
        head=env.object(16,'resource node',words=[head,0,key,value])
    buckets=env.object(4,'resource buckets',words=[head])
    env.put(owner+0x14,buckets,1)


def construct_setup(present,category,scale,fill,receiver_prefix=0):
    def setup(env):
        t=basic(env,fill,receiver_prefix);obj,actor,desc=t['obj'],t['actor'],t['desc']
        manager=env.object(0x40,'resource manager',fill=0)
        env.put(actor+0xc,manager)
        env.put(actor+0x64,category,0x2134)
        # Distinct low words and nondefault config bounds expose misplaced stores
        # even though the original base constructor initializes these same fields.
        put_double(env,0x513e10,1.23456789)
        put_double(env,0x513e18,-7.65432109)
        env.put(desc+0x34,83)
        env.put(desc+0x38,-91)
        env.put(actor+0x4c,101,203)
        env.put(actor+0xcc,7)
        grid=env.object(0x80,'spatial grid',fill=0);env.put(grid+0x64,4096,4096);env.put(manager+0x24,grid)
        for off in (0x10,0x14,0x28,0x2c):
            owner=env.object(0x40,'resource owner',fill=0);env.put(manager+off,owner)
            resource_map(env,owner,[])
        if present:
            suffixes=('DIVE1','DIVE2','DIVE3','DIVE4','FEATHEREXPLODE','FEATHERFLOAT','FLYING','HITHIGH','HITLOW','HOME','KILLFALL')
            items=[('LEVEL_SEAGULL_'+s,animation(env,s)) for i,s in enumerate(suffixes) if present is True or (present=='alternating' and i%2==0)]
            items.append(('GAME_NULL',animation(env,'null')))
            resource_map(env,env.get(manager+0x2c),items)
            # Original image selection installs a frame used by406290. Distinct
            # rectangle coordinates make that dependency observable before the
            # following SetRect service event as well as after construction.
            image_frame=env.object(0x30,'image frame',fill=0)
            env.put(image_frame+0x18,7,11,29,41)
            image_frames=env.object(4,'image frame array',words=[image_frame])
            image=env.object(0x70,'image resource',fill=0)
            env.put(image+0x14,image_frames)
            env.put(image+0x64,0,0)
            resource_map(env,env.get(manager+0x10),[('LEVEL_SEAGULL',image)])
            die=env.object(0x20,'death audio resource',fill=0x59)
            dive=env.object(0x20,'dive audio resource',fill=0xa7)
            resource_map(env,env.get(manager+0x28),[('LEVEL_SEAGULL_SEAGULLDIE',die),('LEVEL_SEAGULL_SEAGULLDIVE',dive)])
        env.put(desc+0x2c,17,-37,83,-91)
        env.put(desc+0xf0,0,0,0,0,0,0,0,0)
        env.put(0x537210,0)
        env.put(0x534940,0)
        for addr,value in ((0x5262b8,50.0),(0x50f558,scale),(0x5262b4,scale),(0x5262b0,scale)):
            env.write(addr,struct.pack('<f',value))
        return t
    return setup
