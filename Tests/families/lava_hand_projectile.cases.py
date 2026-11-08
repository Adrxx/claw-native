"""Original-backed lava hand projectile inputs."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def dput(env,a,v): env.write(a,struct.pack('<d',v))


def dictionary(env, entries=()):
    owner=env.object(0x30,'dictionary',fill=0); buckets=env.object(4,'buckets',fill=0); head=0
    for name,value in entries:
        key=env.object(len(name)+1,'key',data=name.encode()+b'\0')
        head=env.object(16,'node',words=[head,0,key,value])
    env.put(buckets,head); env.put(owner+0x14,buckets,1)
    return owner


def callback(env,label,argc=0,conv='thiscall'):
    log=env.object(20,'callback log',fill=0)
    def effect(e,c):
        e.put(log,e.get(log)+1,c.receiver,*(list(c.arguments)+[0,0,0])[:3]);return 0x7193
    return env.stub(label,conv,argc,effect)


def registry(env,address,low,high,fn=0):
    cells=env.object((high-low+1)*4,'registry cells')
    for i in range(high-low+1):env.put(cells+i*4,fn)
    error=env.object(0x20,'error',fill=0);env.put(error+0xc,4)
    fallback=env.object(4,'fallback',words=[fn])
    env.put(address,0,error,low,high,cells,fallback,4,0,0)
    return cells


def graph(env,image=False,health=0):
    c=env.object(0x180,'controller',fill=0x39)
    e=env.object(0x1b4,'entity',fill=0);l=env.object(0x174,'logic',fill=0);w=env.object(0x100,'world',fill=0)
    collision=env.object(0x100,'collision',fill=0)
    empty=dictionary(env)
    for off in (0x10,0x14,0x28,0x2c):env.put(w+off,empty)
    tilemap=env.object(0x94,'tilemap',fill=0);tiles=env.object(4,'tiles',words=[0xffffffff]);rows=env.object(4,'rows',words=[0]);env.put(tilemap+0x20,tiles,rows);env.put(tilemap+0x30,1000,1000);env.put(tilemap+0x8c,10,10);env.put(collision+0x5c,tilemap);env.put(w+0x24,collision);env.put(e+0xc,w);env.put(e+0x6c,l)
    env.put(e+0x4c,173,291);env.put(e+0x148,5,7);env.put(e+0x104,health)
    env.put(0x537680,0);env.put(l+0xc,w);env.put(l+0x2c,2,3,4,5)
    if image:env.put(e+0x170,env.object(0x70,'image',fill=0))
    env.put(c+0xc,e);env.put(c+0x10,l);env.put(c+0x12c,e);env.put(c+0x130,l)
    return {'c':c,'e':e,'l':l,'w':w}


def aim_setup(values):
    def setup(env):
        c=env.object(0x180,'aim',fill=0x59)
        for off,val in zip((0x38,0x48,0x68,0x70,0x78),values):dput(env,c+off,val)
        return {'c':c}
    return setup


def dispatch_setup(state,mode):
    def setup(env):
        t=graph(env);f=callback(env,'state callback')
        registry(env,0x537a60,0,3,f if mode=='callback' else 0)
        registry(env,0x534910,min(-10,state),max(10,state),f)
        return t
    return setup


def logic_setup(state):
    def setup(env):
        t=graph(env);v=env.object(0x40,'vtable',fill=0)
        env.put(t['c'],v);env.put(t['l']+0x18,t['c'],state)
        for off in (4,8,12,16,28,32):env.put(v+off,callback(env,f'method {off}',1 if off in (4,8,12) else 0))
        # Original CString registry cells carry a valid non-shared header.
        header=env.object(16,'cstring',words=[1,0,0,0]);cells=registry(env,0x537698,-2,1001,header+12)
        return t
    return setup


def explosion_setup(flag,animation,one,done):
    def setup(env):
        t=graph(env);e=t['e'];c=t['c'];env.put(e+8,flag)
        env.put(c+0x178,one);env.put(e+0x1a4,done);env.put(e+0x19c,0)
        if animation:
            a=env.object(0x20,'animation',fill=0);frame=env.object(0x30,'frame',fill=0)
            env.put(e+0x190,a);env.put(e+0x19c,5);env.put(e+0x1a4,1 if animation==1 else 9)
            env.put(e+0x1a8,0);env.put(e+0x1ac,animation)
        env.put(0x5430c4,17)
        return t
    return setup


def begin_setup(sound,enabled):
    def setup(env):
        t=graph(env);c=t['c'];e=t['e'];env.put(t['l']+0x1c,31)
        env.put(0x537668+0x18,0)
        env.put(c+0x170,0)
        if sound:
            s=env.object(0x14,'sound',fill=0);manager=env.object(0x80,'manager',fill=0);obj=env.object(0x14,'sound object',fill=0);env.put(obj+0x10,manager);env.put(s+0x10,obj);env.put(c+0x174,s)
        else:env.put(c+0x174,0)
        env.put(0x532c0c,enabled);env.put(0x532c10,61)
        return t
    return setup


def cases(random_source):
    # Fixed structural coverage plus randomized nonzero values.
    for disp in (0,1,-1,13,-47,0x3fffffff,-0x40000000,-0x80000000,0x7fffffff):
        for vals in ((2.,3.,17.,29.,31.),(0.,0.,0.,0.,0.),(float('nan'),2.,3.,4.,5.),(1e308,1e308,1e308,1e308,1e308)):
            yield Case(f'aim {disp} {vals}',0x4571a0,aim_setup(vals),receiver=lambda t:t['c'],arguments=(disp,))
    for i in range(30):
        vals=tuple(random_source.uniform(-1e4,1e4) for _ in range(5));disp=random_source.randrange(-100000,100001)
        yield Case(f'aim random {i}',0x4571a0,aim_setup(vals),receiver=lambda t:t['c'],arguments=(disp,))
    for state in (0,1,2,3,-1,4):
        for mode in ('callback','fallback'):
            yield Case(f'dispatch {state} {mode}',0x456c20,dispatch_setup(state,mode),receiver=lambda t:t['c'],arguments=(state,))
    for state in (0,29,30,1000,1,-1,31):
        yield Case(f'logic {state}',0x456b00,logic_setup(state),arguments=(lambda t:t['e'],))
    for image in (False,True):
        for health in (0,1,73):
            yield Case(f'construct image {image} health {health}',0x457020,lambda env,image=image,health=health:graph(env,image,health),receiver=lambda t:t['c'],arguments=(lambda t:t['e'],))
    for flag in (0,0x12345678,0xffffffff):
        for anim in (0,1,2):
            for one in (0,1,9):
                for done in (0,1):
                    yield Case(f'explode {flag} {anim} {one} {done}',0x457460,explosion_setup(flag,anim,one,done),receiver=lambda t:t['c'])
    for bounds in ((-4,-7,8,11),(0,0,-1,-1),(7,11,6,10),(7,11,2,3),(-9,13,-9,13)):
        for rv in ((0,1,2,3),(1,0,3,2),(-7,-9,13,19)):
            for count in (0,1):
                yield Case(f'trail {bounds} {rv} {count}',0x4574e0,trail_setup(bounds,rv,count),receiver=lambda t:t['c'])
    for sound,enabled in ((0,0),(0,1),(1,0),(1,1)):
        yield Case(f'begin {sound} {enabled}',0x4573b0,begin_setup(sound,enabled),receiver=lambda t:t['c'])

    for i in range(16):
        health=random_source.choice((0,random_source.randrange(1,0x7fffffff)))
        flags=random_source.getrandbits(32)
        yield Case(f'construct populated resources {i}',0x457020,
                   resource_setup(i%2,health,flags),receiver=lambda t:t['c'],
                   arguments=(lambda t:t['e'],))
    for i in range(12):
        vals=(random_source.choice((-0.,0.,1e-300,1e150)),
              random_source.choice((float('inf'),-float('inf'),-0.,1e-300)),
              random_source.choice((2.**60,-2.**60,1e-300)),
              random_source.uniform(-300,300),random_source.uniform(-300,300))
        yield Case(f'aim numerical edges {i}',0x4571a0,aim_setup(vals),
                   receiver=lambda t:t['c'],arguments=(random_source.choice((-1,1,1073741824,-1073741824)),))
    for sound in (0,1):
        for enabled in (0,1):
            yield Case(f'begin populated animation {sound} {enabled}',0x4573b0,
                       populated_begin_setup(sound,enabled),receiver=lambda t:t['c'])
    for i in range(16):
        x=random_source.randrange(-50,51);y=random_source.randrange(-50,51)
        bounds=(x,y,x+random_source.randrange(1,15),y+random_source.randrange(1,17))
        rand=tuple(random_source.randrange(-0x7fffffff,0x7fffffff) for _ in range(4))
        yield Case(f'trail random {i}',0x4574e0,trail_setup(bounds,rand,i%2),
                   receiver=lambda t:t['c'])

    for mask in range(8):
        for image in (0,1):
            yield Case(f'construct mixed resource mask {mask} image {image}',0x457020,
                       mixed_resource_setup(mask,image),receiver=lambda t:t['c'],
                       arguments=(lambda t:t['e'],))
    for z in (0.,-0.,1e-300,-1e-300,4.999999999999999e-6,5e-6,
              5.000000000000001e-6,-4.999999999999999e-6,-5e-6,
              -5.000000000000001e-6,0.125,-0.125,1000.,-1000.):
        for disp in (0,1,-1):
            yield Case(f'aim speed threshold z {z} dx {disp}',0x4571a0,
                       aim_setup((0.,0.,17.25,-29.125,z)),
                       receiver=lambda t:t['c'],arguments=(disp,))
    for ax,az in ((2000.,0.),(-2000.,0.),(0.,2000.),(0.,-2000.),
                  (2000.,-2000.),(-2000.,2000.),(1e12,-1e12),(-1e12,1e12)):
        for z in (0.,1e-5,-1e-5,173.125):
            for disp in (0,1,-1):
                yield Case(f'aim directed acceleration {ax} {az} z {z} dx {disp}',
                           0x4571a0,aim_setup((ax,az,31.25,-71.5,z)),
                           receiver=lambda t:t['c'],arguments=(disp,))
    for x in (2.**53,-2.**53,2.**64,-2.**64,1e300,-1e300):
        for disp in (-1,1,13):
            yield Case(f'aim displacement cancellation x {x} dx {disp}',0x4571a0,
                       aim_setup((13.25,-71.125,x,51.5,19.25)),
                       receiver=lambda t:t['c'],arguments=(disp,))


def mixed_resource_setup(mask,image):
    def setup(env):
        t=graph(env,image,0x73)
        populate_image(env,t,image)
        lava=animation_asset(env,'mixed lava',0x173)
        explosion=animation_asset(env,'mixed explosion',0x291)
        sound=env.object(0x14,'mixed sound',fill=0x57)
        entries=[]
        if mask&1:entries.append(('LEVEL_LAVAHANDPROJECTILE',lava))
        if mask&2:entries.append(('GAME_DYNAMITEEXPLO',explosion))
        env.put(t['w']+0x2c,dictionary(env,entries))
        env.put(t['w']+0x28,dictionary(env,[('GAME_KEGBOOM',sound)] if mask&4 else []))
        env.put(t['e']+0x164,0x71739395)
        return t
    return setup


def animation_asset(env,label,value):
    frame=env.object(0x30,label+' frame',fill=0)
    env.put(frame+0x1c,value)
    frames=env.object(4,label+' frame array',words=[frame])
    animation=env.object(0x20,label+' animation',fill=0)
    env.put(animation+0xc,frames,1)
    return animation


def resource_setup(image,health,flags):
    def setup(env):
        t=graph(env,image,health)
        populate_image(env,t,image)
        lava=animation_asset(env,'lava',0x173)
        explosion=animation_asset(env,'explosion',0x291)
        sound=env.object(0x14,'resource sound',fill=0x37)
        resources=dictionary(env,[('LEVEL_LAVAHANDPROJECTILE',lava),('GAME_DYNAMITEEXPLO',explosion)])
        sounds=dictionary(env,[('GAME_KEGBOOM',sound)])
        env.put(t['w']+0x2c,resources);env.put(t['w']+0x28,sounds)
        env.put(t['e']+8,flags);env.put(t['e']+0x164,flags^0x75319)
        return t
    return setup


def populated_begin_setup(sound,enabled):
    def setup(env):
        t=begin_setup(sound,enabled)(env)
        current=animation_asset(env,'previous',0x123)
        next_animation=animation_asset(env,'new explosion',0x987)
        env.put(t['e']+0x190,current)
        env.put(t['c']+0x170,next_animation)
        env.put(t['e']+8,0x315790a2)
        env.put(t['c']+0x24,0x9173)
        env.put(t['c']+0xc8,0x6391)
        env.put(t['c']+0x134,0x7359)
        env.put(0x532c10,0x13579)
        return t
    return setup


def trail_setup(bounds,rand,count):
    def setup(env):
        t=graph(env);c=t['c'];e=t['e'];w=t['w'];l=t['l']
        # Off-path animation and collision callbacks remain original, valid state.
        env.put(c+0x164,0xffffffff);env.put(e+0xcc,7)
        dput(env,c+0x68,17.75);dput(env,c+0x70,-29.5)
        env.put(e+0x118,*bounds);env.put(e+0x64,37)
        singleton=env.object(0x128,'singleton',fill=0);env.put(singleton+0x124,count);env.put(0x5371fc,singleton)
        factory=env.object(0x40,'factory',fill=0);env.put(factory+0xc,w);env.put(factory+0x28,10);env.put(w+8,factory)
        desc=env.object(0x20,'GlitterBaby descriptor',fill=0);env.put(desc+0x10,callback(env,'GlitterBaby logic',1,'cdecl'))
        table=dictionary(env,[('GlitterBaby',desc)]);env.put(w+0x14,table)
        env.override(0x4a3050,sequence(*rand))
        env.override(0x4f63ec,lambda en,call:en.object(call.arguments[0],'allocation',fill=0))
        return t
    return setup


def populate_image(env,t,preloaded):
    frame=env.object(0x28,'image frame',fill=0)
    env.put(frame+0x18,13,29,71,103)
    frames=env.object(4,'image frame array',words=[frame])
    image=env.object(0x70,'populated image',fill=0)
    env.put(image+0x14,frames)
    env.put(t['w']+0x10,dictionary(env,[('LEVEL_LAVAHANDPROJECTILE',image)]))
    env.put(t['e']+0x138,0x11111111,0x22222222,0x33333333,0x44444444)
    env.put(t['e']+0x118,0x55555555,0x66666666,0x77777777,0x88888888)
    if preloaded:
        env.put(t['e']+0x170,image,frame)
