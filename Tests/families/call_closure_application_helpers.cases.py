"""Original-backed shell and multiplayer helper domains."""
from clawparity.cases import Case
from clawparity.fixtures import returns, allocate
import struct


def recorder(env, log, slot, value=0, extra=None):
    def effect(e,c):
        at=log+slot*32
        e.put(at,c.receiver,len(c.arguments),*c.arguments)
        if extra: extra(e,c)
        return value
    return effect


def physical(env):
    env.override(0x5469e4,lambda e,c:len(e.cstr(c.arguments[0])))
    def decrement(e,c):
        v=(e.get(c.arguments[0])-1)&0xffffffff;e.put(c.arguments[0],v);return v
    def increment(e,c):
        v=(e.get(c.arguments[0])+1)&0xffffffff;e.put(c.arguments[0],v);return v
    env.override(0x5469e8,decrement);env.override(0x5469ec,increment)


def destroy(seed,child):
    def setup(e):
        obj=e.object(0x300,'shell',fill=0);log=e.object(256,'destructor log',fill=0)
        e.put(obj+0x34,seed);e.put(0x5375bc,seed^0x1234)
        if child:
            v=e.object(4,'child methods');p=e.object(16,'child',words=[v,seed,seed^1,seed^2])
            e.put(v,e.stub('child destructor','thiscall',1,recorder(e,log,0)))
            e.put(obj+0x160,p)
        return dict(obj=obj)
    return setup


def popup(seed,kind):
    def setup(e):
        obj=e.object(0x300,'popup',fill=0);table=e.object(0x200,'popup methods',fill=0)
        log=e.object(256,'selection log',fill=0);buckets=e.object(28,'integer buckets',fill=0)
        e.put(obj,table);e.put(obj+0x68,seed^0x1155);e.put(obj+0x278+4,buckets,7)
        key=seed&0xffff;value=0x235 if kind==1 else 0x237
        if kind:
            node=e.object(12,'integer association',words=[0,key,value]);e.put(buckets+((key>>4)%7)*4,node)
        controls=e.object(0x5c*3,'controls',fill=0)
        e.write(obj+0x14,struct.pack('<H',3));e.put(obj+0x3c,controls)
        for i,k in enumerate((0x111,0x237,0x333)):e.write(controls+i*0x5c+0x10,struct.pack('<H',k))
        e.put(table+0x1b0,e.stub('select control','thiscall',2,recorder(e,log,0)))
        e.put(table+0x1f8,e.stub('publish selection','thiscall',0,recorder(e,log,1)))
        return dict(obj=obj,key=key)
    return setup


def portal(path,open_result=7,reg_error=0,query_error=0,query_type=1,launch=0):
    def setup(e):
        physical(e);out=e.object(320,'path output',fill=0x5a);obj=e.object(0x280,'application',fill=0)
        log=e.object(1024,'physical log',fill=0)
        def reg(e,c):
            n=e.calls_so_far(0x546834)
            if reg_error and n==reg_error:return 5
            e.put(c.arguments[7],0x100+n)
            if c.arguments[8]:e.put(c.arguments[8],1)
            return 0
        def query(e,c):
            e.put(c.arguments[3],query_type);e.write(c.arguments[4],path+b'\0');e.put(c.arguments[5],len(path)+1)
            return query_error
        def format_command(e,c):
            data=b'"'+e.cstr(c.arguments[2])+b'"\0'
            e.write(c.arguments[0],data);return len(data)-1
        e.override(0x546834,reg);e.override(0x54682c,query)
        e.override(0x546a30,returns(open_result));e.override(0x546830,returns(0))
        e.override(0x546cfc,format_command)
        e.override(0x546a20,recorder(e,log,0,launch))
        e.override(0x546d50,recorder(e,log,3,1))
        return dict(obj=obj,out=out)
    return setup


def network(seed,primary=0,resend=0,changed=0,status=0,directed=0,delta=17,count=3):
    def setup(e):
        obj=e.object(0xc20,'multiplayer',fill=0);mgr=e.object(0x90,'network manager',fill=0)
        interface=e.object(8,'network interface',fill=0);vt=e.object(0x70,'network methods',fill=0)
        local=e.object(0x28,'local player',fill=0);peer=e.object(0x28,'peer',fill=0)
        actor=e.object(0x110,'actor',fill=0);chain=e.object(0x18,'actor chain',fill=0);life=e.object(4,'life',words=[status])
        log=e.object(256,'network log',fill=0)
        e.put(obj+0x780,mgr,local);e.put(mgr+0x18,interface);e.put(mgr+0x60,count)
        e.put(interface,vt);e.put(local+4,0x111);e.put(peer+4,0x222)
        e.put(vt+0x68,e.stub('Send','stdcall',6,recorder(e,log,0,0)))
        e.put(obj+0xbf4,primary,resend,seed&0xffff,seed>>16,0 if directed==0 else local if directed==1 else peer)
        e.put(actor+0x4c,seed,seed^0x1369);e.put(actor+0xf8,seed^0x2468)
        e.put(actor+0x6c,chain);e.put(chain+0x14,life);e.put(0x537e88,actor);e.put(0x53720c,delta)
        cached=[seed,seed^0x1369,seed^0x2468,1 if status==0 else 0]
        if changed:cached[changed-1]^=0x80
        e.put(0x52a7bc,*cached)
        return dict(obj=obj)
    return setup


def ranking(scores,mode,force,dirty=1,enabled=1,delta=17,throttle=5,null_tail=False):
    def setup(e):
        obj=e.object(0xc20,'ranking state',fill=0);mgr=e.object(0x90,'ranking manager',fill=0)
        players=[]
        for i,score in enumerate(scores):
            actor=e.object(0x100,'score object '+str(i),fill=0);ref=e.object(4,'score reference',words=[actor])
            p=e.object(0x20,'rank player '+str(i),fill=0);e.put(p+0x14,ref)
            e.put(actor+0xf8,score&0xffffffff,0xabc000+i);players.append(p)
        nodes=[]
        for p in players:nodes.append(e.object(12,'list node',words=[0,0x1357,p]))
        for i,node in enumerate(nodes[:-1]):e.put(node,nodes[i+1])
        if null_tail and nodes:
            tail=e.object(12,'empty terminal node',words=[0,0x2468,0]);e.put(nodes[-1],tail)
        e.put(mgr+0x58,nodes[0] if nodes else 0);e.put(obj+0x780,mgr);e.put(obj+0x794,dirty)
        # Stale but valid entries distinguish list publication from a no-op,
        # including mode 2 where no later sorting can repair the array.
        e.put(obj+0x7ac,enabled);e.put(obj+0x7c0,*reversed(players)) if players else None
        e.put(obj+0xbc0,len(players));e.put(obj+0xbcc,mode)
        e.put(0x53720c,delta);e.put(0x52a7cc,throttle)
        return dict(obj=obj)
    return setup


def receive(seed,pending=0,query_result=0,enabled=0,players=1,timeout=100,delta=17,buffer=True,receive_error=0,sender=0x111,local_present=True,sound_mode=0):
    def setup(e):
        physical(e)
        obj=e.object(0xc20,'receiver state',fill=0);mgr=e.object(0x90,'receive manager',fill=0)
        interface=e.object(8,'receive interface',fill=0);vt=e.object(0x70,'receive methods',fill=0)
        ownvt=e.object(0x54,'state methods',fill=0);local=e.object(0x28,'receive player',fill=0)
        packet=e.object(256,'packet',fill=0);log=e.object(512,'receive log',fill=0)
        app=e.object(0x100,'application',fill=0);messages=e.object(0x20,'message list',fill=0)
        resources=e.object(0x30,'resource owner',fill=0);sound=e.object(0x34,'sound map',fill=0)
        e.put(obj,ownvt);e.put(obj+4,app);e.put(obj+0xc,resources);e.put(app+0x4c,messages);e.put(messages+0x18,10)
        e.put(resources+0x28,sound);e.put(sound+0x30,1 if sound_mode==0 else 0)
        sound_buckets=e.object(4,'sound buckets',fill=0)
        e.put(sound+0x14,sound_buckets,1)
        if sound_mode>=2:
            asset=e.object(0x14,'sound asset',fill=0);voice=e.object(0x14,'sound voice',fill=0);backend=e.object(0x7c,'sound backend',fill=0)
            e.put(asset+0x10,voice);e.put(voice+0x10,backend)
            assoc=e.object(16,'sound association',words=[0,0,0x52a824,asset]);e.put(sound_buckets,assoc)
        e.put(0x532c0c,1 if sound_mode==3 else 0);e.put(0x532c10,seed&0xffff)
        e.put(obj+0x780,mgr,local if local_present else 0);e.put(obj+0x7ac,enabled);e.put(obj+0xbf0,timeout)
        e.put(interface,vt);e.put(mgr+0x18,interface);e.put(local+4,0x111)
        e.put(local+0x18,packet if buffer else 0,256);e.put(0x53720c,delta)
        def query(e,c):e.put(c.arguments[2],pending&0xffffffff);return query_result
        def recv(e,c):
            # Persist the inout values before the physical receive replaces them.
            n=e.calls_so_far(e.get(vt+0x64))-1
            e.put(log+256+32*n,e.get(c.arguments[1]),e.get(c.arguments[2]),e.get(c.arguments[5]))
            e.put(c.arguments[1],sender);e.put(c.arguments[2],0x111);e.put(c.arguments[5],8)
            e.put(c.arguments[4],0x12345678,seed)
            at=log+32*min(e.calls_so_far('Receive') if False else 0,8)
            e.put(at,*c.arguments)
            return receive_error
        e.put(vt+0x44,e.stub('GetMessageCount','stdcall',3,query))
        e.put(vt+0x64,e.stub('Receive','stdcall',6,recv))
        e.put(vt+0x50,e.stub('GetPlayerData','stdcall',5,returns(0x80004005)))
        e.put(ownvt+0x50,e.stub('GetPlayerCount','thiscall',0,recorder(e,log,10,players)))
        return dict(obj=obj)
    return setup


def display(seed,depth,has_display=True,old_depth=24,init_result=0,windowed=0):
    def setup(e):
        physical(e);obj=e.object(0x150,'display application',fill=0);display=e.object(0x40,'display',fill=0)
        vt=e.object(0x28,'display methods',fill=0);window=e.object(8,'window',words=[0,seed])
        log=e.object(256,'display log',fill=0)
        e.put(obj+4,window);e.put(obj+0x30,display if has_display else 0);e.put(obj+0x78,old_depth)
        e.put(display,vt);e.put(display+0x38,0xdead)
        e.put(vt+0x1c,e.stub('reset display','thiscall',0,recorder(e,log,0)))
        e.put(vt+0x18,e.stub('initialize display','thiscall',5,recorder(e,log,1,init_result)))
        e.put(0x537234,windowed)
        e.put(0x53724c,seed|0x100);e.put(0x537250,seed^0x98765432)
        return dict(obj=obj)
    return setup


REGISTRATION_TABLES=(0x534820,0x534850,0x534888,0x5348b8,0x5348e8,0x534910,0x534948,0x534978,0x5349b8,0x5349e0,0x534a10,0x534a38,0x534a88,0x534ab0,0x534ad8,0x534b00,0x534b28,0x534b50,0x534b78,0x534ba0,0x534bc8,0x534bf8,0x534c28,0x534c58,0x534ed0,0x537278,0x5372a8,0x5372d8,0x537308,0x537338,0x537598,0x5375d8,0x537608,0x537638,0x537698,0x5376c8,0x5376f8,0x537728,0x537758,0x537788,0x5377b8,0x5377e8,0x537818,0x537848,0x537878,0x537980,0x5379d0,0x537a00,0x537a30,0x537a60,0x537a90,0x537ac0,0x537af0,0x537b20,0x537b68,0x537ba0,0x537bd0,0x537c00,0x537c30,0x537c60,0x537ea0,0x538428,0x538458,0x53c0e8,0x53c118,0x53c148,0x53c178,0x53c1a8,0x53c1d8,0x53c208,0x53c238,0x53c270,0x53c2a0,0x53c2c8,0x53c2f8,0x53c328,0x53c9d0,0x53ca08,0x53ca40,0x53ca70,0x53caa0,0x53ec00,0x53ec68)


def display_reload(seed,depth,stage,enabled,old_timer=False,old_archive=False):
    def setup(e):
        t=display(seed,depth,init_result=1)(e);obj=t['obj'];dis=e.get(obj+0x30)
        registry=e.object(4,'logic registry interface');methods=e.object(0x28,'logic registry methods',fill=0)
        e.put(registry,methods);e.put(methods+0x24,e.stub('register logic','thiscall',3,returns(1)))
        e.put(dis+0x14,registry)
        graphics=e.object(0x6c,'graphics interface',fill=0);audio=e.object(0x34,'audio manager',fill=0)
        e.put(dis+0x24,graphics,audio if stage!='timer-fail' else 0)
        e.put(obj+0xd0,1);e.put(obj+0xcc,ord('C'))
        e.put(obj+0x11c,enabled);e.put(obj+0x12c,seed&0xffff)
        empty=e.get(0x52e1cc)
        e.put(obj+0xf8,empty,empty,empty)
        e.put(0x537668,*([0]*12));e.put(0x52712c,1)
        for address in REGISTRATION_TABLES:
            cells=e.object(1024,'registration '+hex(address),words=[empty if address==0x537698 else 0]*256)
            e.put(address,0,0,0,255,cells,0,4,0,0,0)
        def cwd(e,c):
            if stage=='setup-fail':return 0
            e.write(c.arguments[1],bytes([67,58,92,67,76,65,87,0]));return 7
        e.override(0x546a28,cwd)
        def open_file(e,c):
            return 0xffffffff if stage=='fallback' and b'CLAW24.REZ' in e.cstr(c.arguments[0]).upper() else 7
        e.override(0x546a30,open_file)
        file=e.object(32,'archive file',fill=0)
        e.override(0x4f1d90,returns(0 if stage=='archive-fail' else file))
        e.override(0x4a7840,returns(0));e.override(0x4a7ae0,returns(0))
        def fread(e,c):
            length=c.arguments[1]*c.arguments[2]
            e.write(c.arguments[0],bytes(length));return c.arguments[2]
        e.override(0x4a7260,fread)
        e.put(0x54130c,0,0,0,0)
        if old_timer:
            timer=e.object(0x30,'old timer',fill=0);e.put(obj+0x5c,timer)
        if old_archive:
            archive=e.object(0x48,'old archive',fill=0);e.put(obj+0x34,archive)
        return t
    return setup


def cases(random_source):
    for i in range(6):
        seed=random_source.getrandbits(32)
        yield Case('shell destructor '+str(i),0x4299d0,destroy(seed,i%2),receiver=lambda t:t['obj'])
        for kind in range(3):yield Case('popup lookup '+str((i,kind)),0x424de0,popup(seed,kind),receiver=lambda t:t['obj'],arguments=(lambda t:t['key'],seed))
    for path in (b'',b'C',b'C:',b'C:\\',b'C:\\CLAW',b'D:\\Games\\Captain Claw\\',b'X'*80):
        for output in (0,1):
            yield Case('portal path '+repr((path,output)),0x42bc40,portal(path),arguments=((lambda t:t['out']) if output else 0,))
    for err in range(1,5):yield Case('portal registry fail '+str(err),0x42bc40,portal(b'C:\\CLAW',reg_error=err),arguments=(lambda t:t['out'],))
    for query_error,query_type,open_result in ((5,1,7),(0,2,7),(0,1,0xffffffff)):
        yield Case('portal service failure '+str((query_error,query_type,open_result)),0x42bc40,portal(b'C:\\CLAW',query_error=query_error,query_type=query_type,open_result=open_result),arguments=(lambda t:t['out'],))
    for launch in (0,1):
        for close in (0,1):yield Case('launch portal '+str((launch,close)),0x42be30,portal(b'C:\\CLAW',launch=launch),receiver=lambda t:t['obj'],arguments=(close,))
    yield Case('launch portal unavailable',0x42be30,portal(b'',reg_error=1),receiver=lambda t:t['obj'],arguments=(1,))
    for primary in (0,1,17,18,0xffffffff):
        for resend in (0,17,18):
            for changed in range(5):
                seed=random_source.getrandbits(32)
                yield Case('network state '+str((primary,resend,changed)),0x4774f0,network(seed,primary,resend,changed,status=changed%2,directed=changed%3),receiver=lambda t:t['obj'])
    for scores in ((),(7,),(0,),(-1,),(1,2),(2,1),(-1,0,1),(2,1,3),(3,3,1),(0,0,0),(0x7fffffff,-0x80000000,0),(7,2,7,2,1)):
        for mode in (0,1,2):
            for force in (0,1):yield Case('ranking '+str((scores,mode,force)),0x478290,ranking(scores,mode,force),receiver=lambda t:t['obj'],arguments=(force,))
    for enabled,dirty,delta,throttle in ((0,1,17,1),(1,0,1,100),(1,0,100,100),(1,0,101,100),(1,1,1,100)):
        yield Case('ranking throttle '+str((enabled,dirty,delta,throttle)),0x478290,ranking((3,1,2),1,0,dirty,enabled,delta,throttle,True),receiver=lambda t:t['obj'],arguments=(0,))
    for pending in (0,1,3,0xffffffff):
        for error in (0,0x80004005):
            for sender in (0x111,0x222):
                yield Case('receive '+str((pending,error,sender)),0x477840,receive(random_source.getrandbits(32),pending,receive_error=error,sender=sender),receiver=lambda t:t['obj'])
    for enabled,players,timeout,query_result,buffer in ((0,3,1,0,True),(1,1,1,0,True),(1,3,100,0,True),(1,3,1,0,True),(1,3,17,0,True),(1,3,18,1,True),(1,3,100,0,False)):
        yield Case('receive idle '+str((enabled,players,timeout,query_result,buffer)),0x477840,receive(0x1357,0,query_result,enabled,players,timeout,buffer=buffer),receiver=lambda t:t['obj'])
    for depth in (0,8,16,24,32,0xffffffff):
        for old in (8,16,24):yield Case('display depth '+str((depth,old)),0x42ce90,display(0xabc,depth,old_depth=old),receiver=lambda t:t['obj'],arguments=(depth,))
    for windowed in (0,1):yield Case('display unavailable '+str(windowed),0x42ce90,display(0xabcd,8,windowed=windowed),receiver=lambda t:t['obj'],arguments=(8,))
    yield Case('no display',0x42ce90,display(5,8,False),receiver=lambda t:t['obj'],arguments=(8,))

    for depth in (8,16):
        for stage in ('setup-fail','archive-fail','timer-fail','success'):
            for enabled in (0,1):
                yield Case('display reload '+str((depth,stage,enabled)),0x42ce90,display_reload(random_source.getrandbits(32),depth,stage,enabled,old_timer=enabled==1,old_archive=enabled==1),receiver=lambda t:t['obj'],arguments=(depth,))

    yield Case('receive no local player',0x477840,receive(0x1357,local_present=False),receiver=lambda t:t['obj'])

    for sm in (1,2,3):
        yield Case('receive idle sound '+str(sm),0x477840,receive(0x1357,enabled=1,players=3,timeout=0,sound_mode=sm),receiver=lambda t:t['obj'])

    yield Case('display recursive indexed fallback owns archive and timer',0x42ce90,display_reload(0x97531,16,'fallback',1),receiver=lambda t:t['obj'],arguments=(16,))

    def timer_allocation_failure(e):
        t=display_reload(0x13579,8,'timer-fail',0)(e)
        default=allocate()
        e.override(0x4f63ec,lambda e,c: 0 if c.arguments[0]==0x30 else default(e,c))
        return t
    yield Case('display timer allocation fails with absent audio',0x42ce90,timer_allocation_failure,receiver=lambda t:t['obj'],arguments=(8,))
