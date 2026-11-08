"""Independent original-derived Level 9 projectile and hazard cases."""
from clawparity.cases import Case
from clawparity.fixtures import reallocate


def map_at(env, address, entries):
    head = 0
    for key, value in reversed(entries):
        name = env.object(len(key)+1, 'map-key', data=key.encode()+b'\0')
        head = env.object(16, 'map-node', words=[head, 0, name, value])
    buckets = env.object(4, 'map-bucket', words=[head])
    env.put(address+4, buckets, 1)


def registry(env):
    env.put(0x537668+0x18, 0)


def setup_base(env, flags=0x24680002, collection=0, direction=4, alternate=0, value=37):
    receiver = env.object(0x90, 'projectile', fill=0xa7)
    actor = env.object(0x1c0, 'actor',fill=0)
    logic = env.object(0x174, 'logic', fill=0x35)
    world = env.object(0x60, 'world',fill=0)
    manager = env.object(0x40, 'actor-manager',fill=0)
    images = env.object(0x30, 'images',fill=0)
    classes = env.object(0x30, 'classes',fill=0)
    animations = env.object(0x30, 'animations',fill=0)
    env.put(world+8, manager, 0, images, classes)
    env.put(world+0x2c, animations)
    env.put(manager+0xc, world)
    free_node = env.object(12, 'free-list-node',fill=0)
    env.put(manager+0x20, free_node)
    env.put(actor+8, flags, world)
    env.put(actor+0x4c, 121, 233)
    env.put(actor+0x64, 71)
    env.put(actor+0x6c, logic)
    env.put(actor+0x104, value, value+1)
    env.put(actor+0x110, direction)
    env.put(actor+0x148, value+2, value+3)
    env.put(actor+0x190, 0)
    env.put(logic+0xc, world)
    env.put(logic+0x1c, value+4, value+5)
    env.put(logic+0x2c, 111, 327, 543, 765)
    env.put(logic+0x64, 0, alternate)
    env.put(logic+0xbc, value+6)
    env.put(receiver+8, actor, actor, logic)
    env.put(receiver+0x28, actor, actor, logic)
    env.put(receiver+0x48, 0, 0, 19, 29)
    env.put(receiver+0x60, 1)
    if collection:
        coll = env.object(0x70, 'image-collection',fill=0)
        pointers = env.object(16, 'image-pointers', words=[0x12345678,0x23456789,0x3456789a,0x456789ab])
        lo, hi = {1:(0,2),2:(1,2),3:(-2,-1)}[collection]
        env.put(coll+0x14, pointers)
        env.put(coll+0x64, lo, hi)
        env.put(actor+0x170, coll)
    registry(env)
    map_at(env, images+0x10, [])
    map_at(env, classes+0x10, [])
    map_at(env, animations+0x10, [])
    return dict(r=receiver,a=actor,l=logic,w=world,m=manager,images=images,classes=classes,animations=animations)


def case(label, address, setup, arg=False, **kw):
    return Case(label,address,setup,receiver=(0 if address==0x462330 else lambda t:t['r']),arguments=((lambda t:t['a'],) if arg else ()),**kw)


def bullet_setup(direction=4, alternate=0, image=True, mutate=False, value=37):
    def setup(env):
        t=setup_base(env,direction=direction,alternate=alternate,value=value)
        log=env.object(64,'callback-log',fill=0)
        motion=env.object(0x150,'bullet-motion',fill=0x59)
        vt=env.object(0x30,'motion-vtable',fill=0)
        env.put(motion,vt)
        def reset(env,call):
            env.put(log+16,call.receiver,env.get(motion+0x148))
            return 0x789abcd
        env.put(vt+0x28,env.stub('motion reset','thiscall',0,reset))
        def create(env,call):
            bullet=call.arguments[0]
            logic=env.get(bullet+0x6c)
            env.put(log,bullet,env.get(bullet+0xd0),env.get(bullet+0x104),env.get(log+12)+1)
            env.put(logic+0x18,motion)
            if mutate:
                env.put(t['a']+0x148,0x80000000,0xfffffff9)
            return 0xabcdef12
        entry=env.stub('Bullet logic','cdecl',1,create)
        config=env.object(0x30,'Bullet class',fill=0)
        env.put(config+0x10,entry)
        map_at(env,t['classes']+0x10,[('Bullet',config)])
        if image:
            coll=env.object(0x70,'bullet-images',fill=0)
            pointers=env.object(12,'bullet-image-pointers',words=[0x778899aa,0x8899aabb,0x99aabbcc])
            env.put(coll+0x14,pointers)
            env.put(coll+0x64,0,2)
            map_at(env,t['images']+0x10,[('LEVEL_PROJECTILES',coll),('LEVEL_PROJECTILES_'+str(alternate),coll)])
        # Single-byte C locale classification tables for CString's fixed %d format.
        env.put(0x52f01c,1)
        classification=env.object(514,'ctype-table',fill=0)
        env.put(0x52ee10,classification+2)
        env.write(0x540bf9,bytes(257))
        def decrement(env,call):
            p=call.arguments[0]
            n=(env.get(p)-1)&0xffffffff
            env.put(p,n)
            return n
        env.override(0x5469e8,decrement)
        env.override(0x5469e4,lambda env,call:len(env.cstr(call.arguments[0])))
        t['motion']=motion
        return t
    return setup


def dispatch_setup(index=2, null=False, grow=False, fail=False):
    def setup(env):
        t=setup_base(env)
        log=env.object(16,'dispatch-log',fill=0)
        def invoke(env,call):
            env.put(log,call.receiver,env.get(0x53cac0),env.get(0x53caa8),env.get(0x53caac))
            return 0x12345678
        fn=env.stub('projectile state','thiscall',0,invoke)
        table=env.object(12,'dispatch-table',words=[fn,0 if null else fn,fn])
        fallback=env.object(4,'dispatch-fallback',words=[fn])
        error=env.object(24,'error-policy',fill=0)
        env.put(error+0xc,4)
        env.put(0x53caa4,error,1,3,table,fallback,4)
        env.put(0x53cac0,0xdeadbeef)
        # Minimal RTTI graph for the null-entry branch.
        typ=env.object(8,'type-descriptor',fill=0)
        descriptor=env.object(16,'rtti',words=[0,0,0,typ])
        vtable=env.object(12,'rtti-vtable',words=[descriptor,0,0])
        env.put(t['r'],vtable+4)
        if grow:
            actual_reallocate=reallocate()
            def moving(env,call):
                n=env.calls_so_far(call.function)
                env.put(0x53caa8,index)
                env.put(0x53caac,index-1 if n==1 else index)
                env.put(0x53cac0,0x12345678)
                return actual_reallocate(env,call)
            env.override(0x4a9070,moving)
        if fail:
            env.override(0x4a9070,lambda env,call:0)
        t['index']=index
        return t
    return setup


def cases(random_source):
    for i in range(8):
        n=random_source.randrange(1,100000)
        def simple(env,n=n):
            t=setup_base(env,value=n)
            env.put(t['l']+0x1c,0x789)
            return t
        yield case('saw wrapper '+str(i),0x462330,simple,True)
    for coll in range(4):
        for initialized in (False,True):
            def constructor(env,coll=coll,initialized=initialized):
                t=setup_base(env,collection=coll,value=random_source.randrange(1,10000))
                for off in (8,0xc,0x28,0x2c):
                    previous=env.object(0x1c0,'previous actor '+str(off),data=env.read(t['a'],0x1c0))
                    env.put(t['r']+off,previous)
                if not initialized:
                    for off in (0x64,0x148,0x14c,0x108,0x110):env.put(t['a']+off,0)
                    env.put(t['l']+0xbc,0)
                return t
            yield case(f'projectile constructor {coll} {initialized}',0x497f70,constructor,True)
    for i in range(4):
        yield case('skull constructor '+str(i),0x48a8c0,lambda env:setup_base(env,value=random_source.randrange(1,10000)),True)
    for address in (0x498580,0x498590):
        for first in (0,1,0xffffffff):
            def transition(env,first=first):
                t=setup_base(env,value=random_source.randrange(1,10000))
                env.put(t['r']+0x60,first)
                env.put(t['r']+0x4c,0x76543210)
                return t
            yield case(f'firing transition {address:x} {first}',address,transition)
    for i in range(5):
        yield case('waiting transition '+str(i),0x4988b0,lambda env:setup_base(env,value=random_source.randrange(1,10000)))
    for flags in (0,1,0xfffffffe,0xffffffff):
        for start,now,duration in ((100,109,10),(100,110,10),(100,111,10),(0xfffffff8,3,11),(0x80000000,0x7fffffff,0xffffffff),(17,17,0),(0,0x80000000,0x7fffffff)):
            def waiting(env,flags=flags,start=start,now=now,duration=duration):
                t=setup_base(env,flags=flags)
                env.put(t['r']+0x50,start,duration)
                env.put(0x537210,now)
                return t
            yield case(f'wait {flags:x} {start} {now} {duration}',0x4988f0,waiting)
    for index,null in ((1,False),(2,False),(3,False),(2,True),(-1,False),(5,False)):
        yield Case(f'dispatch {index} null{null}',0x4981c0,dispatch_setup(index,null),receiver=lambda t:t['r'],arguments=(index,))
    yield Case('dispatch bounds reload after realloc',0x4981c0,dispatch_setup(-1,grow=True),receiver=lambda t:t['r'],arguments=(-1,))
    for direction in (0,1,2,3,4,5,6,7,8,9,0xffffffff):
        for alternate in (0,3):
            yield case(f'launch direction{direction} alternate{alternate}',0x498690,bullet_setup(direction,alternate,value=random_source.randrange(1,10000)))
    for image in (False,True):
        yield case('launch image '+str(image),0x498690,bullet_setup(4,0,image,True))
    for fired in (0,1):
        for finished in (0,1):
            for pending in (0,1):
                for coll in range(4):
                    def update(env,fired=fired,finished=finished,pending=pending,coll=coll):
                        t=bullet_setup()(env)
                        env.put(t['r']+0x4c,fired)
                        env.put(t['a']+0x1a4,finished)
                        env.put(t['a']+0x19c,pending if finished else pending+1)
                        env.put(t['a']+0x190,1)
                        env.put(t['a']+0x1a8,0 if finished else 1)
                        env.put(t['a']+0x1ac,0 if finished else 1)
                        if coll:
                            c=env.object(0x70,'update collection',fill=0)
                            ptr=env.object(4,'update frame',words=[0x123abcd])
                            env.put(c+0x14,ptr)
                            lo,hi={1:(0,0),2:(1,2),3:(-2,-1)}[coll]
                            env.put(c+0x64,lo,hi)
                            env.put(t['a']+0x170,c)
                        return t
                    yield case(f'update {fired} {finished} {pending} {coll}',0x4985f0,update)

    def skull_resources(env):
        t=setup_base(env,value=1234)
        def anim(label,duration):
            frame=env.object(0x30,label+' frame',fill=0)
            env.put(frame+0x1c,duration)
            frames=env.object(4,label+' frames',words=[frame])
            result=env.object(0x18,label,fill=0)
            env.put(result+0xc,frames,1)
            return result
        home=anim('home animation',117)
        firing=anim('firing animation',239)
        previous=anim('previous animation',351)
        env.put(t['a']+0x190,previous)
        images=env.object(0x70,'skull images',fill=0)
        pointers=env.object(12,'skull image pointers',words=[0x71234567,0x82345678,0x93456789])
        env.put(images+0x14,pointers)
        env.put(images+0x64,0,2)
        map_at(env,t['images']+0x10,[('LEVEL_SKULLCANNON',images)])
        map_at(env,t['animations']+0x10,[('LEVEL_SKULLCANNON_FIRING',firing),('LEVEL_SKULLCANNON_HOME',home)])
        other=env.object(0x30,'neighbor animation manager',fill=0)
        map_at(env,other+0x10,[])
        env.put(t['w']+0x28,other, t['animations'],other)
        other_world=env.object(0x60,'configuration owner world',data=env.read(t['w'],0x60))
        env.put(other_world+0x2c,other)
        env.put(t['l']+0xc,other_world)
        return t
    yield case('skull distinct resources',0x48a8c0,skull_resources,True)

    for first in (0,1):
        def firing_resources(env,first=first):
            t=setup_base(env,value=6543)
            def anim(label,duration):
                frame=env.object(0x30,label+' frame',fill=0)
                env.put(frame+0x1c,duration)
                frames=env.object(4,label+' frames',words=[frame])
                result=env.object(0x18,label,fill=0)
                env.put(result+0xc,frames,1)
                return result
            current=anim('current firing animation',113)
            selected=anim('selected firing animation',227)
            env.put(t['a']+0x190,current)
            env.put(t['r']+0x48,selected,0x12345678)
            env.put(t['r']+0x60,first)
            return t
        yield case('firing distinct current animation '+str(first),0x498590,firing_resources)
