"""Original-backed Gabriel core cases; fixed branch matrix plus seeded payloads."""
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence


def obj(env,size,name,**kw):
    kw.setdefault("fill",0)
    return env.object(size,name,**kw)


def table(env, header, low=-4, high=40, value=0):
    data = obj(env,(high-low+1)*4, 'table-cells')
    fallback = obj(env,4, 'table-fallback')
    env.put(header+8, low, high, data, fallback, 4, 0, 0)
    if value:
        for i in range(high-low+1): env.put(data+4*i, value)
    return data


def record(env, receiver, name, argc=0):
    log = obj(env,32, name+'-observation')
    def effect(e, call):
        e.put(log, e.get(log)+1, call.receiver, *call.arguments)
        e.put(log+20, e.get(receiver+0x138), e.get(receiver+0x140), e.get(receiver+0x24))
        return 0x793156ab
    return env.stub(name, 'thiscall', argc, effect)


def animation(env, serial):
    frame=obj(env,0x30, 'animation-frame')
    env.put(frame+0x18, 37+serial, 0x13579+serial)
    frames=obj(env,4,'animation-frames',words=[frame])
    anim=obj(env,0x20,'animation')
    env.put(anim+0xc,frames,1)
    return anim


def base(env, salt=0):
    r=obj(env,0x538,'gabriel',fill=0x35)
    s=obj(env,0x1c0,'sprite')
    state=obj(env,0x180,'actor-state')
    scene=obj(env,0x80,'scene')
    collision=obj(env,0x80,'collision')
    env.put(scene+0x24,collision)
    env.put(s+0xc,scene)
    env.put(s+0x6c,state)
    env.put(r+0xc,s,state)
    env.put(r+0x128,s,s)
    env.put(r+0x138,0x80000000 if salt&1 else 13+salt)
    env.put(r+0x140,0xffffffe9-salt)
    env.put(r+0x18c,2)
    env.put(r+0x520,0)
    env.put(r+0x534,0)
    env.put(r+0x524,0)
    for n,off in enumerate((0x118,0x128,0x138)):
        env.put(s+off,17+salt+n)
        env.put(s+off+8,0xffffffdb-salt-n)
    for off in (0x460,0x464,0x478,0x490): env.put(r+off,animation(env,off+salt))
    env.put(s+0x18c,s)
    env.put(s+0x190,0)
    env.put(s+0x1a4,0)
    env.put(s+0x1b0,0x3f800000)
    env.put(state+0x1c,31+salt)
    env.put(0x537680,0)
    env.put(0x537210,0xfffffff0)
    env.put(0x5430c4,3)
    methods=obj(env,0xc0,'gabriel-vtable')
    env.put(r,methods)
    for off,argc in ((4,1),(8,1),(12,1),(0x10,0),(0x1c,0),(0x20,0),(0x48,0),(0xb0,0)):
        env.put(methods+off,record(env,r,'virtual-'+hex(off),argc))
    env.override(0x4a3050,sequence(1,2,0))
    env.put(0x53c9ac,0)
    return {'r':r,'s':s,'state':state,'scene':scene,'methods':methods}


def selected(function,label,change=lambda e,t:None,salt=0,args=()):
    def setup(e):
        t=base(e,salt); change(e,t); return t
    return Case(label,function,setup,receiver=lambda t:t['r'],arguments=args)


def constructor(env, present=False, salt=0):
    t=base(env,salt)
    s,scene=t['s'],t['scene']
    # Resource managers use one bucket; entries contain actual original keys.
    for sceneoff in (0x10,0x14,0x28,0x2c):
        manager=obj(env,0x40,'resources')
        env.put(manager+0x18,1)
        env.put(scene+sceneoff,manager)
        if present and sceneoff==0x2c:
            bucket=obj(env,4,'resource-bucket')
            env.put(manager+0x14,bucket)
            prior=0
            names=(0x527770,0x527758,0x527744,0x527730,0x527718,0x527700,0x5276e8,0x5276d0,0x5276b8,0x5276a0,0x527688,0x527670,0x527658,0x527640,0x527628,0x527610,0x5234b4)
            for i,key in enumerate(names):
                node=obj(env,16,'resource-node',words=[prior,0,key,animation(env,i+salt)])
                prior=node
            env.put(bucket,prior)
    env.put(s+0x4c,100+salt,240+salt)
    env.put(s+0x118,0x80000000)
    env.put(0x533470,32)
    return t


def cases(random_source):
    for salt in (0,7,random_source.randrange(8,100)):
        for rand in (0,49,50,99,100,0xffffffff,0x80000000):
            yield selected(0x444140,f'startup {salt} {rand}',lambda e,t,v=rand:e.override(0x4a3050,returns(v)),salt)
        for lock in (0,3):
            for direction in (0,2):
                for flipped in (0,2):
                    for rand in (49,50):
                        def change(e,t,lock=lock,direction=direction,flipped=flipped,rand=rand):
                            e.put(t['r']+0x520,lock);e.put(t['r']+0x18c,direction)
                            e.put(t['s']+0x40,0xa0|flipped);e.override(0x4a3050,returns(rand))
                        yield selected(0x4441f0,f'idle {salt} {lock} {direction} {flipped} {rand}',change,salt)
        for direction in (0,2):
            for flipped in (0,2):
                for mask in (0,7):
                    for rand in (0,1,2,0xffffffff,0xfffffffe):
                        def change(e,t,direction=direction,flipped=flipped,mask=mask,rand=rand):
                            e.put(t['r']+0x18c,direction);e.put(t['s']+0x40,0x80|flipped)
                            for n,off in enumerate((0x118,0x128,0x138)):
                                if mask&(1<<n):e.put(t['s']+off,0x80000000)
                            e.override(0x4a3050,sequence(rand,0,0))
                            e.put(t['r']+0x498,0,0,0)
                            e.put(t['r']+0x4b4,0,0)
                        yield selected(0x444330,f'choose {salt} {direction} {flipped} {mask} {rand}',change,salt)
    for mode in (0,2,0xffffffff):
        yield selected(0x4441b0,f'tick mode {mode}',lambda e,t,m=mode:e.put(0x53c9c0,m))
    for lock,done,delay,elapsed,period,startup in ((1,1,0,1000,1000,0),(0,0,0,1000,1000,0),(0,1,1,1000,1000,0),(0,1,0,999,1000,0),(0,1,0,1000,1000,1),(0,1,0,1000,1000,0),(0,1,0,0,0,0),(0,1,0,0xffffffff,1000,0)):
        def change(e,t,lock=lock,done=done,delay=delay,elapsed=elapsed,period=period,startup=startup):
            e.put(t['r']+0x520,lock);e.put(t['s']+0x1a4,done);e.put(t['s']+0x19c,delay)
            e.put(t['r']+0x4dc,(0xfffffff0-elapsed)&0xffffffff,period)
            e.put(t['r']+0x534,startup);e.override(0x4a3050,returns(0xffffffff))
        yield selected(0x4442c0,f'idle tick {lock,done,delay,elapsed,period,startup}',change)
    for value in (0,1,0x76543210):
        yield selected(0x405f60,f'sound {value}',args=(value,))
    for state in (1,29,30,1000,0xffffffff):
        def setup(e,state=state):
            t=base(e);e.put(t['state']+0x18,t['r'],state)
            table(e,0x537698,low=-4,high=40)
            # Original CString state description for generic dispatch.
            desc=obj(e,16,'description',words=[1,0,0,0])+12
            arr=e.get(0x5376a8)
            e.put(arr+(e.get(t['state']+0x1c)+4)*4,desc) if state<40 else None
            e.put(t['s']+0x6c,t['state'])
            return t
        # Outer state selects dispatch; Gabriel's state controls original state table.
        if state==0xffffffff:
            def setup(e):
                t=base(e);outer=obj(e,0x20,'outer-state');e.put(outer+0x18,t['r'],0xffffffff)
                e.put(t['s']+0x6c,outer);table(e,0x537698,low=-4,high=40)
                desc=obj(e,16,'description',words=[1,0,0,0])+12;e.put(e.get(0x5376a8)+(31+4)*4,desc)
                return t
        yield Case(f'factory state {state}',0x443290,setup,arguments=(lambda t:t['s'],))
    for present in (False,True):
        for salt in (0,random_source.randrange(1,40)):
            def setup(e,present=present,salt=salt):return constructor(e,present,salt)
            yield Case(f'constructor {present} {salt}',0x443ab0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['s'],))
    for present in (False,True):
        def setup(e,present=present):
            t=constructor(e,present,7);e.put(t['state']+0x18,0,0)
            return t
        yield Case(f'factory initial {present}',0x443290,setup,arguments=(lambda t:t['s'],))
    # Every masked exception-flag combination, with an empty incoming x87 stack.
    # Keep this matrix fixed across seeds and exercise both resource lookup paths
    # through the direct constructor and its real state-zero factory caller.
    for sw in range(0x40):
        for present in (False,True):
            for factory in (False,True):
                def setup(e,sw=sw,present=present,factory=factory):
                    e.entry_x87_status(sw)
                    t=constructor(e,present,7)
                    if factory:
                        e.put(t['state']+0x18,0,0)
                    return t
                yield Case(
                    f'x87 {"factory" if factory else "constructor"} sw={sw:#04x} resources={present}',
                    0x443290 if factory else 0x443ab0,
                    setup,
                    receiver=0 if factory else lambda t:t['r'],
                    arguments=(lambda t:t['s'],),
                )
    for flags in (0,1,2,3,0x80000001):
        def setup(e):
            t=base(e);e.put(t['r']+0x2fc,32)
            empty=e.get(0x52e1c8)+12
            e.put(t['r']+0x1a4,empty,empty)
            return t
        yield Case(f'delete flags {flags}',0x444120,setup,receiver=lambda t:t['r'],arguments=(flags,))
    for key in (-5,-4,0,4,5):
        for populated in (False,True):
            def setup(e,key=key,populated=populated):
                t=base(e);cb=record(e,t['r'],'dispatch')
                table(e,0x537728,-4,4,cb if populated else 0)
                table(e,0x5349b8,-8,8,cb)
                return t
            yield Case(f'dispatch {key} {populated}',0x4433b0,setup,receiver=lambda t:t['r'],arguments=(key,))
