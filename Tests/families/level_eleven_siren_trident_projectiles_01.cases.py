"""Original-driven projectile cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence

def object_(env,*args,**kwargs):
    kwargs.setdefault("fill",0)
    return env.object(*args,**kwargs)

def resource_map(env, entries):
    obj=object_(env,0x30,'resource-map')
    bucket=object_(env,4,'bucket')
    previous=0
    for key,value in entries:
        text=object_(env,len(key)+1,'key',data=key+b'\0')
        previous=object_(env,16,'resource-node',words=[previous,0,text,value])
    env.put(bucket,previous)
    env.put(obj+0x14,bucket,1)
    return obj

def graph(seed=1,sprite=False,sound=False,parameter=0):
    def setup(env):
        a=object_(env,0x1b4,'actor')
        l=object_(env,0x200,'logic-data')
        p=object_(env,0x160,'projectile-state')
        w=object_(env,0x40,'world')
        collision=object_(env,0x80,'collision')
        manager=object_(env,0x30,'effect-manager')
        env.put(manager+0xc,w)
        nodes=[object_(env,12,'free-list-node') for _ in range(8)]
        for i,n in enumerate(nodes): env.put(n,nodes[i+1] if i+1<len(nodes) else 0)
        env.put(manager+0x20,nodes[0])
        env.put(manager+0x28,2)
        lw=object_(env,0x10,'logic-world')
        env.put(lw+8,manager)
        env.put(l+0xc,lw)
        env.put(a+0xc,w)
        env.put(a+0x6c,l)
        env.put(a+8,seed & 0xfff7ff8f)
        env.put(a+0x4c,seed+17,seed+39)
        env.put(a+0x64,7)
        env.put(l+0x18,p,1000)
        env.put(p+0xc,a)
        env.put(p+0x10,l)
        env.put(p+0x12c,a,l)
        frame=object_(env,0x60,'sprite-frame')
        env.put(frame+0x18,seed+3,seed+7,seed+31,seed+43)
        frames=object_(env,4,'frames',words=[frame])
        image=object_(env,0x70,'sprite')
        env.put(image+0x14,frames)
        def key(addr):
            v=env.cstr(addr)
            return v.encode() if isinstance(v,str) else v
        images=resource_map(env,[(key(x),image) for x in (0x524130,0x524394,0x5243f8)] if sprite else [])
        parameters=resource_map(env,[(key(x),parameter) for x in (0x52437c,0x5243e0)])
        effect=object_(env,0x20,'effect-record')
        observed=object_(env,64,'effect-callback-observations')
        def created_effect(env,call):
            n=env.get(observed)
            env.put(observed,n+1,call.arguments[0])
            created=call.arguments[0]
            env.put(observed+8,env.get(created+0x4c),env.get(created+0x50),env.get(p+0x158))
            return 1
        env.put(effect+0x10,env.stub('created-effect-logic','cdecl',1,created_effect))
        effects=resource_map(env,[(key(x),effect) for x in (0x522594,0x522e24)])
        env.put(w+0x10,images,effects)
        env.put(w+0x24,collision)
        env.put(w+0x2c,parameters)
        env.put(0x53724c,int(not sound))
        settings=object_(env,0x128,'sound-settings')
        env.put(settings+0x124,int(sound))
        env.put(0x5371fc,settings)
        env.put(0x537680,0)
        env.put(0x5430c4,3)
        return dict(actor=a,logic=l,target=p,frame=frame,manager=manager)
    return setup

def factory_setup(code,seed,sprite=False):
    def setup(env):
        t=graph(seed,sprite)(env)
        env.put(t['logic']+0x1c,code)
        vt=object_(env,0x30,'projectile-vtable')
        env.put(t['target'],vt)
        record=object_(env,0x30,'observations')
        def observe(env,call):
            env.put(record,env.get(record)+1,call.receiver,env.get(t['logic']+0x18),env.get(t['logic']+0x1c))
            return 0x12345678
        for offset in (0x10,0x1c,0x20): env.put(vt+offset,env.stub(f'method-{offset}','thiscall',0,observe))
        name=object_(env,20,'state-name',data=struct.pack('<III',1,3,7)+b'foo\0\0\0\0\0')
        table=object_(env,4,'state-name-table',words=[name+12])
        env.put(0x5376a0,code,code,table,table,4)
        env.put(0x5376b4,table,0)
        for offset in (4,8,12): env.put(vt+offset,env.stub(f'dispatch-{offset}','thiscall',1,observe))
        return t
    return setup

def state_setup(inherited,a,b,flags=0x12340080,animation=0):
    def setup(env):
        t=graph(1)(env)
        actor,target=t['actor'],t['target']
        env.put(actor+8,flags)
        env.put(actor+0x1a4,a)
        env.put(actor+0x19c,b)
        env.put(target+0x120,0x10000 if inherited else 0)
        if animation:
            env.put(actor+0x190,object_(env,4,'active-animation'))
            env.put(actor+0x1a8,animation,animation)
            env.put(actor+0x1a0,1)
            env.put(actor+0x19c,99)
        return t
    return setup

def dispatch_setup(index,present,table_address=0x534bc8):
    def setup(env):
        t=graph(7)(env)
        table=object_(env,12,'siren-state-table')
        base=object_(env,20,'base-state-table')
        record=object_(env,32,'dispatch-observations')
        def callback(env,call):
            env.put(record,call.receiver,env.get(table_address+0x20),index & 0xffffffff)
            return 0x11223344
        fn=env.stub('state-action','thiscall',0,callback)
        for i in range(3):
            selected=fn
            if table_address != 0x534bc8:
                def selected_callback(env,call,i=i):
                    callback(env,call)
                    env.put(record+12,i+0x112200,env.get(t['target']+0x24))
                    return 0x12340000+i
                selected=env.stub(f'trident-state-action-{i}','thiscall',0,selected_callback)
            env.put(table+4*i,selected if present else 0)
        for i in range(5): env.put(base+4*i,fn)
        env.put(table_address+8,10,12,table,table,4)
        env.put(table_address+0x1c,table,0xdeadbeef)
        env.put(0x538430,9,13,base,base,4)
        env.put(0x538444,base,0xdeadbeef)
        return t
    return setup

def scatter_setup(count,xr,yr,tracked,x,y,randoms):
    def setup(env):
        t=graph(9)(env)
        a,p=t['actor'],t['target']
        env.put(a+0x118,xr[0],yr[0],xr[1],yr[1])
        env.put(p+0x158,count)
        env.write(p+0x68,struct.pack('<dd',x,y))
        env.put(p+0x154,t['frame'] if tracked else 0)
        env.override(0x4a3050,sequence(*randoms))
        return t
    return setup

def explosion_setup(seed,flags,state_present,sprite,sequence_present):
    def setup(env):
        t=graph(seed)(env)
        a,p,l=t['actor'],t['target'],t['logic']
        env.put(a+8,flags)
        env.put(a+0xd0,seed^0x1badbeef)
        old_sequence=object_(env,0x40,'old-sequence',fill=0xa5)
        env.put(a+0x190,old_sequence)
        env.put(p+0x24,seed+0x1357)
        env.put(p+0x134,seed+0x2468)
        env.put(p+0xc8,seed+0x369)
        env.put(l+0x1c,seed^0x23456789)
        # A valid one-node Patricia tree: both links lead to its leaf.
        env.put(0x537680,0)
        if state_present:
            key=object_(env,13,'exploding-state-key',data=b'LS_EXPLODING\0')
            node=object_(env,20,'state-trie-leaf')
            env.put(node,node,node,0,key,seed^0x6b82a401)
            env.put(0x537680,node)
        if sprite:
            image=object_(env,0x70,'explosion-sprite')
            frames=object_(env,4,'explosion-frames',words=[t['frame']])
            env.put(image+0x14,frames)
            images=resource_map(env,[(b'LEVEL_TRIDENT_TRIDENTEXPLOSION',image)])
            world=env.get(a+0xc)
            env.put(world+0x10,images)
        if sequence_present:
            frame=object_(env,0x40,'explosion-animation-frame',fill=0x39)
            env.put(frame+0x1c,seed+17)
            frames=object_(env,4,'explosion-animation-frames',words=[frame])
            sequence=object_(env,0x40,'explosion-animation')
            env.put(sequence+0xc,frames,1)
            env.put(p+0x150,sequence)
        else:
            env.put(p+0x150,0)
        return t
    return setup

def cases(random_source):
    for f in (0x4104c0,0x410580):
        for code in (0,1,28,29,30,31,999,1000,1001,0xffffffff):
            yield Case(f'factory {f:x} message {code}',f,factory_setup(code,5),arguments=(lambda t:t['actor'],))
        for sprite in (False,True):
            yield Case(f'factory {f:x} sprite {sprite}',f,factory_setup(0,13,sprite),arguments=(lambda t:t['actor'],))
    for f in (0x412880,0x412ce0):
        for sprite in (False,True):
            for sound in (False,True):
                for param in (0,17,0xffffffff):
                    yield Case(f'constructor {f:x} sprite{sprite} sound{sound} parameter{param}',f,graph(random_source.randrange(1,2000),sprite,sound,param),receiver=lambda t:t['target'],arguments=(lambda t:t['actor'],))
    for f in (0x412cb0,0x413470):
        for inherited in (0,1):
            for a in (0,1,0x80000000):
                for b in (0,3):
                    for flags in (0,0x12340080,0xffffffff):
                        yield Case(f'state {f:x} inherited{inherited} a{a} b{b} flags{flags}',f,state_setup(inherited,a,b,flags),receiver=lambda t:t['target'])
    for animation in (1,2):
        for latch in (0,1,0xffffffff):
            def setup(env,animation=animation,latch=latch):
                t=state_setup(0,0,0,animation=animation)(env)
                env.put(t['target']+0x15c,latch)
                return t
            yield Case(f'explosion animation{animation} latch{latch}',0x413470,setup,receiver=lambda t:t['target'])
    for index in (9,10,11,12,13):
        for present in (False,True):
            yield Case(f'dispatch {index} present{present}',0x4129d0,dispatch_setup(index,present),receiver=lambda t:t['target'],arguments=(index,))
    for count in (-1,0,1,2,3):
        for xr,yr in (((-3,7),(-5,2)),((5,4),(7,6)),((0,-1),(-2,-3))):
            for tracked in (False,True):
                x,y=random_source.uniform(-100,100),random_source.uniform(-100,100)
                yield Case(f'scatter count{count} ranges{xr},{yr} tracked{tracked}',0x413280,scatter_setup(count,xr,yr,tracked,x,y,(1,0,7,8,3,5,1,0)),receiver=lambda t:t['target'])
    yield Case('scatter wrapped range even x odd y',0x413280,scatter_setup(1,(5,4),(7,6),True,13.75,-21.5,(0,1)),receiver=lambda t:t['target'])

    for index in (9,10,11,12,13):
        for present in (False,True):
            yield Case(f'trident dispatch {index} present{present}',0x412e80,dispatch_setup(index,present,0x534a88),receiver=lambda t:t['target'],arguments=(index,))
    for flags in (0,4,0x81234560,0xffffffff):
        for state_present in (False,True):
            for sprite in (False,True):
                for sequence_present in (False,True):
                    seed=random_source.randrange(1,0x10000)
                    yield Case(f'explode flags{flags} state{state_present} sprite{sprite} sequence{sequence_present}',0x4133e0,explosion_setup(seed,flags,state_present,sprite,sequence_present),receiver=lambda t:t['target'])
