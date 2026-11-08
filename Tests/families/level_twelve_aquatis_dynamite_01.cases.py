"""Original-backed Aquatis dynamite cases."""
from clawparity.cases import Case


def state(time=50,saved=50,boss=2,clock=1000,last=0,delay=750,create=0,salt=17,construct=False,callbacks=False):
    def setup(env):
        t=env.object(0x58,'state',fill=salt)
        a=env.object(0x1b4,'actor',fill=0)
        w=env.object(0x100,'world',fill=0)
        l=env.object(0x100,'level',fill=0)
        e=env.object(0x100,'engine',fill=0)
        c=env.object(0x100,'context',fill=0)
        m=env.object(0x100,'manager',fill=0)
        assets=env.object(0x60,'assets',fill=0)
        anim=env.object(0x60,'animations',fill=0)
        env.put(a+0xc,w)
        env.put(a+0x4c,0x12345678^salt,0xfedcba98^salt)
        env.put(a+0x6c,l)
        env.put(w+8,m)
        env.put(w+0x10,anim,assets)
        env.put(w+0x24,0x82736451)
        env.put(l+0xc,w)
        env.put(l+0x1c,0x18273645)
        env.put(l+0x2c,0x71234567,0xf6543210,0x81234567,0x12345678)
        env.put(e+0x6c,c)
        env.put(m+0xc,w)
        env.put(m+0x28,10)
        env.put(anim+0x18,17)
        env.put(assets+0x18,17)
        env.put(t+8,a,a,l)
        env.put(t+0x28,a,a,l)
        env.put(t+0x48,saved,last,delay)
        env.put(0x537e88,e)
        env.put(0x537210,clock)
        env.put(0x537680,0)
        if time is not None:
            timer=env.object(0x80,'timer',fill=salt)
            env.put(timer+0x78,time)
            env.put(c+0x14,timer)
        env.put(0x534874,0)
        if boss:
            b=env.object(0x4d0,'boss',fill=salt)
            env.put(b+0x4b8,int(boss!=1))
            env.put(b+0x4c8,int(boss==3))
            env.put(0x534874,b)
        if create:
            resource=env.object(0x40,'resource',fill=0)
            image=env.object(0x40,'image',fill=0)
            buckets=env.object(68,'buckets',fill=0)
            node=env.object(16,'node',fill=0)
            key=env.cstr(0x522894)
            raw=key if isinstance(key,bytes) else key.encode()
            name=env.object(len(raw)+1,'key',data=raw+b'\0')
            h=0
            for byte in raw:
                h=(h*33+byte)&0xffffffff
            env.put(assets+0x14,buckets,17)
            env.put(buckets+(h%17)*4,node)
            env.put(node,0,0,name,resource)
            env.put(resource+0x10,image if create==2 else 0)
        if callbacks:
            sprite_resources(env,t,a,assets,salt)
        if construct:
            env.write(t, bytes([salt]) * 0x58)
        return {'t':t,'a':a}
    return setup


def sc(label,f,**kw):
    return Case(label,f,state(construct=f==0x4071a0,**kw),receiver=lambda x:x['t'],arguments=(lambda x:x['a'],) if f==0x4071a0 else ())


def dispatch(index,low,high,occupied,salt):
    def setup(env):
        t=env.object(0x58,'receiver',fill=salt)
        table=env.object((high-low+1)*4,'table',fill=0)
        log=env.object(16,'callback-log',fill=0)
        def callback(env,call):
            env.put(log,call.receiver,env.get(t+0x14),env.get(0x5348d8),0x98765432)
            return 0x33445566
        stub=env.stub('dispatch','thiscall',0,callback)
        if occupied:
            env.put(table+(index-low)*4,stub)
        else:
            rtti=env.object(24,'rtti',fill=0)
            desc=env.object(8,'descriptor',fill=salt)
            vtable=env.object(12,'vtable',fill=0)
            env.put(vtable,rtti)
            env.put(t,vtable+4)
            env.put(rtti+0xc,desc)
        env.put(0x5348c0,low,high,table,table,4,0,0x7abcdef0)
        return {'t':t}
    return Case(f'dispatch {index} {low}:{high} occupied {occupied} salt {salt}',0x406ef0,setup,receiver=lambda x:x['t'],arguments=(index,))


def cases(random_source):
    for salt in (1,107,random_source.randrange(2,255)):
        for index,lo,hi in ((0,0,2),(2,0,2),(-3,-3,1),(1,-3,1)):
            yield dispatch(index,lo,hi,True,salt)
        for index in (1,-1,3):
            yield dispatch(index,0,2,False,salt)
        for time,saved in ((None,50),(49,50),(50,50),(51,50),(0xffffffff,0),(0x7fffffff,0x80000000)):
            for boss in (0,2):
                for create in (0,1,2):
                    yield sc(f'spawn {time} {saved} boss {boss} create {create} salt {salt}',0x407360,time=time,saved=saved,boss=boss,create=create,salt=salt)
        yield sc(f'constructor callbacks salt {salt}',0x4071a0,callbacks=True,salt=salt)
        for f in (0x4071a0,0x4072f0):
            for time in (None,49,51):
                yield sc(f'init {f:x} {time} salt {salt}',f,time=time,salt=salt)
        for clock,last,delay in ((749,0,750),(750,0,750),(751,0,750),(0,0,0),(0,0xffffffff,1),(0xffffffff,0,0xffffffff),(0x7fffffff,0,0x80000000)):
            for boss in (0,1,2,3):
                yield sc(f'tick {clock} {last} {delay} boss {boss} salt {salt}',0x407310,clock=clock,last=last,delay=delay,boss=boss,salt=salt)


def sprite_resources(env,t,a,assets,salt):
    log=env.object(64,'sprite-log',fill=0)
    buckets=env.object(68,'ctor-buckets',fill=0)
    env.put(assets+0x14,buckets,17)
    for keyaddr,offset in ((0x522d54,0x70),(0x522d48,0x78)):
        key=env.cstr(keyaddr)
        raw=key if isinstance(key,bytes) else key.encode()
        name=env.object(len(raw)+1,'ctor-key',data=raw+b'\0')
        h=0
        for byte in raw:
            h=(h*33+byte)&0xffffffff
        slot=buckets+(h%17)*4
        descriptor=env.object(32,'sprite-descriptor',fill=salt)
        node=env.object(16,'ctor-node',words=[env.get(slot),0,name,descriptor])
        env.put(slot,node)
        sprite=env.object(0x174,'sprite',fill=salt)
        vt=env.object(0x28,'sprite-vtable',fill=0)
        env.put(sprite,vt)
        env.put(a+offset,sprite)
        def observe(env,call):
            at=env.get(log)
            env.put(log,at+1)
            env.put(log+4+(at%4)*12,call.receiver,env.get(t+0x10),env.get(t+0x14))
            env.put(t+0x14,0xdecafbad)
            return 1
        env.put(vt+0x1c,env.stub('sprite-reset','thiscall',0,observe))
        env.put(vt+0x24,env.stub('sprite-bind','thiscall',2,observe))
