"""Original-backed lifecycle, packet and DirectPlay call cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate


def string(env, text, refs=3):
    b=text.encode('latin1') if isinstance(text,str) else text
    p=env.object(12+len(b)+1,'CString storage',fill=0)
    env.put(p,refs,len(b),len(b))
    env.write(p+12,b+b'\0')
    return p+12


def setup_base(env, *, lookup=1, error=0, name='visitor', silent=0, actor=0, position=0, special=False,
               chat=0, reflect=0, reject=0, server=0, send=0, ready=0, game=0, local=False, publish_null=False):
    state=env.object(0xc20,'multiplayer',fill=0)
    manager=env.object(0x80,'net manager',fill=0)
    com=env.object(4,'DirectPlay',fill=0)
    vtable=env.object(0x80,'DirectPlay vtable',fill=0)
    player=env.object(0x28,'remote player',fill=0)
    me=env.object(0x28,'local player',fill=0)
    pt=env.object(0x10,'player vtable',fill=0)
    data=env.object(0x2c,'actor data',fill=0)
    act=env.object(0xd0,'actor',fill=0)
    packet=env.object(0x400,'packet buffer',fill=0x6d)
    log=env.object(0x800,'callback observations',fill=0)
    app=env.object(0x60,'application',fill=0)
    messages=env.object(0x20,'message list',fill=0)
    free=env.object(0x100,'message free nodes',fill=0)
    env.put(messages+0x10,free)
    env.put(messages+0x18,8)
    for i in range(10):env.put(free+i*12,free+(i+1)*12 if i<9 else 0)
    env.put(app+0x4c,messages)
    context=env.object(0x40,'world context',fill=0)
    world=env.object(0x30,'world',fill=0)
    resource=env.object(0x50,'resource manager',fill=0)
    settings=env.object(0xb0,'settings',fill=0)
    env.put(settings+0xac,0x91a2b3c4)
    env.put(context+8,world)
    env.put(context+0x24,settings)
    env.put(context+0x28,resource)
    env.put(world+0xc,context)
    env.put(context+0x14,resource)
    # Empty string-key maps: hash modulus must stay nonzero even without buckets.
    env.put(resource+0x10+8,17)
    env.put(resource+0x30,1)
    env.put(player,pt,0xabcdef01,string(env,name),string(env,'details'),0x54,data,packet,0x400,0)
    env.put(me,pt,0x11223344,string(env,'local'),string(env,'host'),0x23,0,0,0,0)
    env.put(data,act if actor else 0)
    env.put(data+0x24,silent)
    env.put(act+8,0x12345678)
    env.put(state+4,app)
    env.put(state+0xc,context)
    env.put(state+0x14,0xfedcba98)
    env.put(state+0x780,manager,me,0xabcdef01 if local else 0x11223344,ready)
    env.put(state+0x79c,server)
    env.put(state+0x7a4,send,reflect,chat,reject)
    env.put(state+0x7b8,game)
    env.put(state+0xbc4,0x18273645)
    env.put(state+0xc04,player if special else 0)
    env.put(manager+0x18,com)
    env.put(com,vtable)
    env.put(manager+0x54+0x10,env.object(12,'free player node',fill=0))
    env.put(manager+0x54+0x18,10)
    for g in (0x544d20,0x544d24,0x544d28,0x544d2c):env.put(g,0)
    env.put(0x532c0c,0)
    env.put(0x537e88,settings)
    # This global points to an object with a value at f8, beyond settings.
    root=env.object(0x100,'game state global',fill=0)
    env.put(root+0xf8,0x99887766)
    env.put(0x537e88,root)
    env.put(0x53c25c,1)
    env.put(0x53c264,player)
    def observe(e,c):
        n=e.get(log);off=log+4+n*80
        e.put(log,n+1)
        e.put(off,c.receiver,len(c.arguments),*c.arguments)
        return off
    def find(e,c):
        off=observe(e,c)
        answer=me if lookup==2 else player if lookup else 0
        e.put(c.arguments[2],answer)
        e.put(c.arguments[3],4)
        e.put(off+40,answer)
        return error
    def transmit(e,c):
        off=observe(e,c)
        if c.arguments[4] and c.arguments[5]:
            b=e.read(c.arguments[4],min(c.arguments[5],32));e.write(off+40,b)
        return error
    def publish(e,c):
        observe(e,c)
        if publish_null:e.put(c.arguments[2],0)
        return error
    def destroy(e,c):
        off=observe(e,c)
        e.put(off+40,e.get(c.receiver+0x20),e.get(c.receiver+4))
        e.put(c.receiver+0x20,0xdeadbeef)
        return c.receiver
    env.put(vtable+0x50,env.stub('DirectPlay GetPlayerData','stdcall',5,find))
    env.put(vtable+0x68,env.stub('DirectPlay Send','stdcall',6,transmit))
    env.put(vtable+0x74,env.stub('DirectPlay SetPlayerData','stdcall',5,publish))
    env.put(pt+4,env.stub('player deleting destructor','thiscall',1,destroy))
    def length(e,c):return len(e.cstr(c.arguments[0]))
    def inc(e,c):
        v=(e.get(c.arguments[0])+1)&0xffffffff;e.put(c.arguments[0],v);return v
    def dec(e,c):
        v=(e.get(c.arguments[0])-1)&0xffffffff;e.put(c.arguments[0],v);return v
    env.override(0x5469e4,length)
    env.override(0x5469e8,dec)
    env.override(0x5469ec,inc)
    env.override(0x546ca4,lambda e,c:1)
    env.override(0x546d48,lambda e,c:1)
    return dict(state=state,manager=manager,player=player,me=me,data=data,actor=act,packet=packet,
                log=log,context=context,world=world,resource=resource,pt=pt)


def basic(**options):
    return lambda e:setup_base(e,**options)


def cases(rng):
    # Selection branches and exact-match clearing, independent of random input.
    for active in (0,1,0x80000000):
        for match in (False,True):
            def setup(e,active=active,match=match):
                t=setup_base(e);e.put(0x53c25c,active);t['arg']=t['player'] if match else t['me'];return t
            yield Case(f'selection {active:x} {match}',0x486d50,setup,arguments=(lambda t:t['arg'],))
    for err in (0,1,0x80004005):
        for result in (0,1,2):
            yield Case(f'lookup {err:x} {result}',0x4e0c80,basic(error=err,lookup=result),receiver=lambda t:t['manager'],arguments=(rng.getrandbits(32),))
    for f in (0x4e0cc0,0x4e0d20):
        for err in (0,1,0x80004005):
            for a in (0,1):
                for b in (0,1):
                    for size in (0,1,20,31):
                        args=((lambda t,a=a:t['player'] if a else 0),(lambda t,b=b:t['me'] if b else 0),0x13579bdf,lambda t:t['packet'],size)
                        if f==0x4e0d20:args=(0x23456789 if a else 0,0x98765432 if b else 0,*args[2:])
                        yield Case(f'send {f:x} {err:x} {a}{b} {size}',f,basic(error=err),receiver=lambda t:t['manager'],arguments=args)
    for f,argc in ((0x4776b0,1),(0x4777d0,3),(0x477810,4)):
        for target in (0,1):
            for err in (0,0x80004005):
                for k in range(4):
                    args=(lambda t,target=target:t['player'] if target else 0,)
                    if argc==3:args+=((0x3ed,0x3ee,0xffffffff,0)[k],0x10203+k)
                    if argc==4:args+=((0x3f4,0x3f5,0xffffffff,0)[k],0x82736450+k,0x2134+k)
                    seed=bytes(rng.randrange(256) for _ in range(20))
                    yield Case(f'packet {f:x} {target} {err:x} {k}',f,basic(error=err),receiver=lambda t:t['state'],arguments=args,initial_stack=((-20,seed),))
    for f in (0x4e0fe0,0x4e0fc0):
        for buf in (False,True):
            for data in (False,True):
                for flag in (0,1,2,0x100,0x101,0xff):
                    def setup(e,buf=buf,data=data):
                        t=setup_base(e)
                        if not buf:e.put(t['player']+0x18,0)
                        if not data:e.put(t['player']+0x14,0)
                        return t
                    yield Case(f'destruct {f:x} {buf}{data} {flag:x}',f,setup,receiver=lambda t:t['player'],arguments=(flag,) if f==0x4e0fc0 else ())
    for null in (False,True):
        for pos in (False,True):
            def setup(e,pos=pos):
                t=setup_base(e)
                if pos:
                    p=e.object(12,'list position',fill=0);e.put(t['player']+0x20,p)
                    e.put(t['manager']+0x54+4,p,p,1)
                return t
            yield Case(f'delete {null}{pos}',0x4e0c20,setup,receiver=lambda t:t['manager'],arguments=(lambda t,null=null:0 if null else t['player'],))
    for name in ('','a','abcdefghijk','\xffname'):
        for other in ('','different'):
            for flags in (0,1,0x87654321):
                def setup(e,name=name,other=other):
                    t=setup_base(e);t['name']=e.object(len(name)+1,'raw name',data=name.encode('latin1')+b'\0');t['other']=e.object(len(other)+1,'raw other',data=other.encode()+b'\0');return t
                yield Case(f'initialize {name!r} {other!r} {flags:x}',0x4e1ae0,setup,receiver=lambda t:t['player'],arguments=(rng.getrandbits(32),lambda t:t['name'],lambda t:t['other'],flags))
    # Local player path exercises both independent allocations and preserved existing buffers.
    for null in (False,True):
        for buf in (False,True):
            for data in (False,True):
                for fail in (0,1,2):
                    def setup(e,buf=buf,data=data,fail=fail):
                        t=setup_base(e,local=True)
                        if not buf:e.put(t['player']+0x18,0)
                        if not data:e.put(t['player']+0x14,0)
                        if fail:
                            def alloc(e,c):
                                if e.calls_so_far(0x4f63ec)==fail:return 0
                                return e.object(c.arguments[0],'allocated player storage',fill=0xa7)
                            e.override(0x4f63ec,alloc)
                        return t
                    yield Case(f'prepare local {null}{buf}{data} fail{fail}',0x478f30,setup,receiver=lambda t:t['state'],arguments=(lambda t,null=null:0 if null else t['player'],))
    for found in (0,1,2):
        for silent in (0,1):
            for actor in (0,1):
                for special in (False,True):
                    for chat in (0,1):
                        yield Case(f'remove {found} {silent}{actor}{special}{chat}',0x479000,basic(lookup=found,silent=silent,actor=actor,special=special,chat=chat),receiver=lambda t:t['state'],arguments=(0xabcdef01,))
    for null in (False,True):
        for typ in (0,1,2):
            def setup(e,typ=typ):
                t=setup_base(e,local=True);p=e.object(0x28,'accept packet',fill=0);e.put(p+4,typ,0xabcdef01);t['accept']=p;return t
            yield Case(f'accept basic {null} {typ}',0x47a4b0,setup,receiver=lambda t:t['state'],arguments=(lambda t,null=null:0 if null else t['accept'],))
    for err in (0,1,0x80004005):
        for name in ('','ordinary','__CLAW_FLEX__'):
            def setup(e,name=name,err=err):
                t=setup_base(e,error=err)
                t['name']=e.object(len(name)+1,'create raw name',data=name.encode()+b'\0')
                t['other']=e.object(8,'create raw other',data=b'host123\0')
                return t
            yield Case(f'create {err:x} {name!r}',0x4e0930,setup,receiver=lambda t:t['manager'],arguments=(0x10293847,lambda t:t['name'],lambda t:t['other'],0x79abcdef))
    for mask in range(64):
        name=('__CLAW_FLEX__','__CLAW_FLEX_X','X','')[mask%4]
        def setup(e,mask=mask,name=name):
            t=setup_base(e,local=True,name=name,server=mask&1,chat=(mask>>1)&1,reflect=(mask>>2)&1,
                         reject=(mask>>3)&1,send=(mask>>4)&1,ready=(mask>>5)&1,game=mask&1)
            p=e.object(0x28,'accept policy packet',fill=0x37)
            e.put(p+4,1,0xabcdef01)
            t['accept']=p
            return t
        yield Case(f'accept policy {mask} {name!r}',0x47a4b0,setup,receiver=lambda t:t['state'],arguments=(lambda t:t['accept'],))
    for data in (False,True):
        for sound in (0,1,2):
            def setup(e,data=data,sound=sound):
                t=setup_base(e,chat=1)
                if not data:e.put(t['player']+0x14,0)
                e.put(t['resource']+0x30,0)
                if sound:
                    buckets=e.object(17*4,'sound map buckets',fill=0)
                    node=e.object(16,'sound map node',fill=0)
                    key=e.object(16,'sound resource key',data=b'GAME_NEWMESSAGE\0')
                    res=e.object(0x20,'sound resource',fill=0)
                    soundobj=e.object(0x20,'sound player',fill=0)
                    hardware=e.object(0x80,'sound hardware',fill=0)
                    e.put(soundobj+0x10,hardware)
                    e.put(res+0x10,soundobj)
                    e.put(node,0,0,key,res)
                    for n in range(17):e.put(buckets+n*4,node)
                    e.put(t['resource']+0x10+4,buckets)
                    e.put(0x532c0c,sound-1)
                return t
            yield Case(f'remove no actorData/sound {data} {sound}',0x479000,setup,receiver=lambda t:t['state'],arguments=(0xabcdef01,))
    for err in (0,1):
        for allocation_fail in (False,True):
            def setup(e,err=err,allocation_fail=allocation_fail):
                t=setup_base(e,local=True,lookup=0 if err else 1,error=err)
                p=e.object(0x28,'accept failure packet',fill=0)
                e.put(p+4,1,0xabcdef01)
                n=e.object(8,'accept new name',data=b'newone\0')
                e.put(p+0x20,n,n)
                if allocation_fail and not err:
                    e.put(t['player']+0x18,0);e.override(0x4f63ec,allocate(fail=True))
                t['accept']=p
                return t
            yield Case(f'accept failure {err} {allocation_fail}',0x47a4b0,setup,receiver=lambda t:t['state'],arguments=(lambda t:t['accept'],))
    for found in (False,True):
        for init in (False,True):
            def setup(e,found=found,init=init):
                t=setup_base(e,local=False)
                if found:
                    buckets=e.object(17*4,'actor map buckets',fill=0)
                    node=e.object(16,'actor map node',fill=0)
                    key=e.object(15,'actor resource key',data=b'ClawMultiRacer\0')
                    res=e.object(0x20,'actor resource record',fill=0)
                    payload=e.object(16,'actor resource payload',fill=0x6c)
                    e.put(res+8,0x31415926)
                    e.put(res+0x10,payload if init else 0)
                    e.put(node,0,0,key,res)
                    for n in range(17):e.put(buckets+n*4,node)
                    e.put(t['resource']+0x14,buckets)
                    free=e.object(12,'world free node',fill=0)
                    e.put(t['world']+0x20,free)
                    e.put(t['world']+0x28,10)
                return t
            yield Case(f'prepare remote resource{found} init{init}',0x478f30,setup,receiver=lambda t:t['state'],arguments=(lambda t:t['player'],))
    for name in ('new-player','__CLAW_FLEX__'):
        def setup(e,name=name):
            t=setup_base(e,local=True,lookup=0)
            p=e.object(0x28,'accept new packet',fill=0)
            e.put(p+4,1,0xabcdef01)
            n=e.object(len(name)+1,'accept new player name',data=name.encode()+b'\0')
            e.put(p+0x20,n,n)
            t['accept']=p
            return t
        yield Case(f'accept creates {name!r}',0x47a4b0,setup,receiver=lambda t:t['state'],arguments=(lambda t:t['accept'],))
    for sound in (0,1,2):
        def setup(e,sound=sound):
            t=setup_base(e,local=True,chat=1)
            e.put(t['resource']+0x30,0)
            if sound:
                buckets=e.object(17*4,'accept sound buckets',fill=0)
                node=e.object(16,'accept sound node',fill=0)
                key=e.object(16,'accept sound key',data=b'GAME_NEWMESSAGE\0')
                res=e.object(0x20,'accept sound resource',fill=0)
                sobj=e.object(0x20,'accept sound player',fill=0)
                hardware=e.object(0x80,'accept sound hardware',fill=0)
                e.put(sobj+0x10,hardware);e.put(res+0x10,sobj);e.put(node,0,0,key,res)
                for n in range(17):e.put(buckets+n*4,node)
                e.put(t['resource']+0x14,buckets)
                e.put(0x532c0c,sound-1)
            p=e.object(0x28,'accept sound packet',fill=0);e.put(p+4,1,0xabcdef01)
            t['accept']=p
            return t
        yield Case(f'accept sound {sound}',0x47a4b0,setup,receiver=lambda t:t['state'],arguments=(lambda t:t['accept'],))

    def create_pointer_cleared(e):
        t=setup_base(e,error=0x80004005,publish_null=True)
        t['name']=e.object(8,'create cleared name',data=b'cleared\0')
        return t
    yield Case('create COM error clears local player pointer',0x4e0930,create_pointer_cleared,receiver=lambda t:t['manager'],arguments=(0x10293847,lambda t:t['name'],lambda t:t['name'],0x19384756))
