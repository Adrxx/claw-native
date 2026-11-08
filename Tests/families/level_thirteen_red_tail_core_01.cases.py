"""Original-driven Red Tail core inputs."""
import struct
from clawparity.cases import Case


def obj(env,*args,**kwargs):
    kwargs.setdefault("fill",0)
    return env.object(*args,**kwargs)


def table(env, receiver, low, high, stride=4, callback=0):
    data=obj(env,(high-low+1)*stride,'dispatch entries')
    for i in range(high-low+1):
        env.put(data+i*stride,callback)
    env.put(receiver+8,low,high,data,data,stride,0,0)
    return data


def dictionary(env,address,entries):
    buckets=obj(env,4,'resource buckets')
    head=0
    for key,value in entries:
        if isinstance(key,str): key=key.encode()
        text=obj(env,len(key)+1,'resource key',data=key+b'\0')
        head=obj(env,16,'resource association',words=[head,0,text,value])
    env.put(buckets,head)
    env.put(address+4,buckets,1)


def base(env,salt=1):
    target=obj(env,0x540,'red tail')
    actor=obj(env,0x220,'actor')
    state=obj(env,0x200,'state')
    world=obj(env,0x100,'world')
    resources=obj(env,0x80,'resource collection')
    animations=obj(env,0x80,'animation collection')
    collision=obj(env,0xa0,'collision world')
    env.put(target+0xc,actor,state)
    env.put(target+0x128,actor,actor,state)
    env.put(actor+0xc,world)
    env.put(actor+0x6c,state)
    env.put(world+0x10,resources,resources)
    env.put(world+0x24,collision,resources,animations)
    dictionary(env,resources+0x10,[])
    dictionary(env,animations+0x10,[])
    env.put(state+0x1c,0x55660000+salt)
    env.put(0x537668+0x18,0)
    env.put(0x537e88,actor)
    env.put(0x52b35c,0)
    env.put(0x537210,1000+salt)
    env.put(0x5430c4,salt+1)
    env.put(0x532c0c,0)
    env.put(target+0x134,0x11220000+salt)
    env.put(target+0x50,0x13579bdf+salt,0x40234567+salt,0x2468ace1+salt,0xc0356789+salt)
    env.put(target+0x4b8,0xa1b20000+salt,0xc3d40000+salt)
    env.put(target+0x138,13+salt)
    env.put(target+0x140,29+salt)
    for off in (0x118,0x128,0x138):
        env.put(actor+off,17+off+salt)
        env.put(actor+off+8,43+off+salt)
    vt=obj(env,0x50,'callback vtable')
    record=obj(env,0x30,'callback observations')
    def callback(env,call):
        env.put(record,env.get(record)+1,call.receiver,env.get(call.receiver+0x138),env.get(call.receiver+0x140))
        return 0x73570000+salt
    cb=env.stub('state callback','thiscall',0,callback)
    env.put(vt+0x44,cb)
    env.put(target,vt)
    return dict(target=target,actor=actor,state=state,resources=resources,animations=animations,callback=cb,record=record)


def setup_ctor(mode,flags,salt):
    def setup(env):
        t=base(env,salt)
        env.write(t['target'],bytes([0x71+(salt%13)])*0x540)
        env.put(t['actor']+8,0xa5a50105)
        env.put(t['actor']+0x164,0x76543211)
        env.put(t['actor']+0x4c,100+salt,200+salt)
        env.put(t['state']+0x64,salt%2)
        if flags=='force-small':
            flags_text=''
            def rectangle(env,call):
                env.put(call.arguments[0],*call.arguments[1:5])
                env.put(t['target']+0x2fc,8)
                return 1
            env.override(0x546d5c,rectangle)
        else: flags_text=flags
        env.write(0x534938,flags_text.encode()+b'\0')
        env.put(0x533470,0)
        env.put(0x52f01c,1)
        keys=[0x52b698,0x52b680,0x52b668,0x52b654,0x52b640,0x52b62c,0x52b614,0x52b5fc,0x52b5e4,0x52b5cc,0x52b5b4,0x52b59c,0x52b584,0x52b570,0x5234b4]
        entries=[]
        for i,k in enumerate(keys):
            if mode==0 or (mode==2 and i%2): continue
            frame=obj(env,0x30,'animation frame')
            env.put(frame+0x1c,100+i+salt)
            slots=obj(env,4,'animation frame array',words=[frame])
            ani=obj(env,0x20,'animation',words=[0,0,0,slots,1])
            entries.append((env.cstr(k),ani))
        dictionary(env,t['animations']+0x10,entries)
        sounds=[]
        for i,k in enumerate((0x52b558,0x52b540,0x52b528,0x52b510,0x52b4f8,0x52b4e0,0x52b4c8,0x52b4b0,0x52b498,0x52b480,0x52b468,0x52b450,0x52b438,0x52b420,0x52b408,0x52b3f0)):
            sound=obj(env,0x20,'sound resource',words=[0x65430000+i+salt,0x76540000+i])
            sounds.append((env.cstr(k),sound))
        image_frame=obj(env,0x30,'image frame',words=[0x11,0x22,0x33,0x44,0x55,0x66,7,9,47,63])
        image_frames=obj(env,4,'image frames',words=[image_frame])
        image=obj(env,0x70,'image resource')
        env.put(image+0x14,image_frames)
        env.put(image+0x64,0,0)
        sounds.append((env.cstr(0x52b6b4),image))
        dictionary(env,t['resources']+0x10,sounds)
        return t
    return setup


def setup_destructor(bits,salt):
    def setup(env):
        t=base(env,salt)
        env.put(t['target']+0x2f4,0,0,0,0)
        env.put(0x544d18,0)
        if bits&4:
            buf=obj(env,12,'external flags',words=[0x10203040,0x50607080,0x9abcdef0])
            env.put(t['target']+0x2fc,65,buf)
        for i,off in enumerate((0x1a4,0x1a8)):
            if bits&(1<<i):
                header=obj(env,24,'cstring data',words=[1+(bits>>3),3,3,0x00434241,0,0])
                ptr=header+12
            else: ptr=env.get(0x52e1c8)+12
            env.put(t['target']+off,ptr)
        def decrement(env,call):
            address=call.arguments[0]
            value=(env.get(address)-1)&0xffffffff
            env.put(address,value)
            return value
        env.override(0x5469e8,decrement)
        return t
    return setup


def setup_home(state,facing,mirror,rand_value,active,expired,salt,matched=True):
    def setup(env):
        t=base(env,salt)
        target,actor=t['target'],t['actor']
        env.put(target+0x184,state)
        env.put(target+0x18c,facing)
        env.put(target+0x4e0,active)
        env.put(target+0x4b8,1000+salt)
        env.put(target+0x4bc,0 if expired else 100)
        env.put(actor+0x40,0x10020|mirror)
        env.put(actor+0xcc,1)
        env.put(actor+0x50,100 if matched else 0)
        env.write(target+0x70,struct.pack('<d',100.0))
        env.put(target+0x4b0,1000+salt)
        env.put(target+0x4b4,100000)
        def rand(env,call):
            return rand_value if env.calls_so_far(0x4a3050)==1 else 100
        env.override(0x4a3050,rand)
        return t
    return setup


def setup_dispatch(index,low,high,stride,use_callback,salt):
    def setup(env):
        t=base(env,salt)
        table(env,0x53c178,low,high,stride,t['callback'] if use_callback else 0)
        table(env,0x5349b8,-8,8,4,t['callback'])
        env.put(0x53c198,0x67670000+salt)
        env.put(0x5349d8,0x78780000+salt)
        return t
    return setup


def cases(random_source):
    for i,(mode,flags) in enumerate((m,f) for m in (0,1,2) for f in ('','0','7','8','9','31','32','33','force-small')):
        yield Case(f'construct lookup {mode} flags {flags!r}',0x47ff90,setup_ctor(mode,flags,i+1),receiver=lambda t:t['target'],arguments=(lambda t:t['actor'],))
    for bits in (0,1,2,3,4,7,11,15):
        for fn,flag in ((0x4805c0,0),(0x4805a0,0),(0x4805a0,1),(0x4805a0,2),(0x4805a0,0xffffffff)):
            yield Case(f'destruct {bits} {fn:x} flags {flag}',fn,setup_destructor(bits,31+bits),receiver=lambda t:t['target'],arguments=() if fn==0x4805c0 else (flag,))
    for salt in range(1,9):
        yield Case(f'virtual callback {salt}',0x480630,base,receiver=lambda t:t['target'])
        for active in (0,1,0xffffffff):
            def setup(env,salt=salt,active=active):
                t=base(env,salt)
                env.put(t['target']+0x4e0,active)
                env.put(t['actor']+8,0xa5a50105^salt)
                frame=obj(env,0x30,'live home frame')
                env.put(frame+0x1c,0x13572468+salt)
                slots=obj(env,4,'live home slots',words=[frame])
                ani=obj(env,0x20,'live home animation',words=[0,0,0,slots,1])
                old=obj(env,0x20,'previous animation')
                env.put(t['actor']+0x190,old)
                env.put(t['target']+0x350,ani)
                return t
            yield Case(f'home enter active {active} {salt}',0x480640,setup,receiver=lambda t:t['target'])
    for index,low,high in ((0,0,2),(2,0,2),(-1,-1,1),(3,-2,2),(-3,-2,2)):
        for stride in (4,12):
            for callback in (False,True):
                yield Case(f'dispatch {index} range {low}:{high} stride {stride} callback {callback}',0x47f800,setup_dispatch(index,low,high,stride,callback,17),receiver=lambda t:t['target'],arguments=(index,))
    for state in (0,1,2,3,4,5,6,7,0xffffffff):
        for facing,mirror in ((2,0),(2,2),(3,0),(3,2)):
            values=(0,32,33,44,45,65,66,79,80,89,90,100) if state==4 else (0,90)
            for value in values:
                yield Case(f'home state {state} facing {facing} mirror {mirror} rand {value}',0x4806c0,setup_home(state,facing,mirror,value,0,True,random_source.randrange(1,100)),receiver=lambda t:t['target'])
    for active,expired in ((1,True),(0xffffffff,True),(0,False)):
        yield Case(f'home early active {active} expired {expired}',0x4806c0,setup_home(4,2,0,33,active,expired,random_source.randrange(1,100)),receiver=lambda t:t['target'])

    for value in (0,44,45,79,80,100):
        yield Case(f'home mismatched actor height rand {value}',0x4806c0,setup_home(4,2,2,value,0,True,random_source.randrange(1,100),matched=False),receiver=lambda t:t['target'])
