"""Original XMIDI manager cases; no native implementation dependencies."""
from clawparity.cases import Case
from clawparity.fixtures import returns, allocate

NEW = 0x4f63ec
D = 0x54131c

def base(env):
    empty = env.object(16, 'empty CString', words=[0xffffffff, 0, 0, 0])
    env.put(0x52e1c8, empty, empty + 12)
    env.put(D, 0x3157, 17, 0x3199)
    for slot in (0x546a54,0x546ac4,0x546ac8,0x546acc,0x546e68,0x546e6c,0x546e70,0x546e74,0x546e78,0x546e7c,0x546e80,0x546e84,0x546e88,0x546e8c,0x546e90,0x546e94,0x546e98,0x546e9c):
        env.override(slot, returns(1))
    env.override(0x5469e4, lambda e,c: len(e.cstr(c.arguments[0])))
    def atomic(delta):
        def effect(e,c):
            a=c.arguments[0]; v=(e.get(a)+delta)&0xffffffff; e.put(a,v); return v
        return effect
    env.override(0x5469e8, atomic(-1)); env.override(0x5469ec, atomic(1))


def resource(env, valid=1, status=4, pause=3, payload=False, play=0x71, mutate=None):
    r=env.object(0x60,'resource',fill=0xa7)
    vt=env.object(0x34,'resource callbacks',fill=0)
    log=env.object(0x100,'callback observations',fill=0)
    env.put(r,vt); env.write(r+4,b'tune\0'); env.put(r+0x44,pause,0x37,0x5219,63,87,0x7213,0)
    if payload: env.put(r+0x5c,env.object(19,'old payload',fill=0x6d))
    for off,argc,result in ((4,1,0),(0x14,3,0x91),(0x20,0,valid),(0x24,2,play),(0x28,0,0x73),(0x2c,1,0x75),(0x30,0,0x79)):
        def effect(e,c,off=off,result=result):
            n=e.get(log); a=log+4+28*(n%8)
            e.put(a,off,c.receiver,e.get(r+0x44),e.get(r+0x48),e.get(r+0x4c),*(list(c.arguments)+[0,0])[:2]); e.put(log,n+1)
            if mutate: mutate(e,c,off,r)
            return result
        env.put(vt+off,env.stub('resource method '+hex(off),'thiscall',argc,effect))
    env.override(0x546e7c,returns(status))
    return r


def manager(env, entries=(), current=True, enabled=1, parameter=0x9183, play=0x71, mutate=None):
    m=env.object(0x2c,'manager',fill=0)
    env.put(m+8,17); env.put(m+0x18,4,0,parameter,0x8179,enabled)
    r=resource(env,play=play,mutate=mutate)
    if current: env.put(m+0x1c,r)
    if entries:
        buckets=env.object(68,'map buckets',fill=0)
        block=env.object(4+16*len(entries),'map node block',fill=0)
        env.put(m+4,buckets,17,len(entries),0,block)
        for i,(key,has_resource) in enumerate(entries):
            b=key.encode(); header=env.object(13+len(b),'CString '+key,words=[1,len(b),len(b)],data=None)
            env.write(header+12,b+b'\0')
            h=0
            for ch in b: h=((h<<5)+h+ch)&0xffffffff
            bucket=h%17; node=block+4+16*i
            env.put(node,env.get(buckets+4*bucket),bucket,header+12,r if has_resource else 0)
            env.put(buckets+4*bucket,node)
    return {'m':m,'r':r,'name':env.object(8,'query',data=b'tune\0xxx')}


def mc(label,f,setup, args=()):
    return Case(label,f,setup,receiver=lambda t:t['m'],arguments=args)


def rc(label,f,valid=1,status=4,pause=3,payload=False,args=(),mutate=None,extra=None):
    def setup(e):
        base(e); r=resource(e,valid,status,pause,payload,mutate=mutate)
        if extra: extra(e,r)
        return {'r':r}
    return Case(label,f,setup,receiver=lambda t:t['r'],arguments=args)


def cases(random_source):
    for skip,opened,driver in ((0,0,0x2345),(0,1,0x2345),(0,0,0),(1,0,0x2345)):
        def setup(e,opened=opened,driver=driver):
            base(e); t=manager(e)
            def open_(e,c): e.put(c.arguments[0],driver); return opened
            e.override(0x546e74,open_); return t
        yield mc(f'initialize {skip} {opened} {driver}',0x4b52a0,setup,(0x4356,0x9813,skip))
    for f in (0x4b5300,0x4b5340):
        for entries in ((),(('tune',True),('other',False),('third',True))):
            for cur in (False,True):
                def setup(e,entries=entries,cur=cur): base(e); return manager(e,entries,cur)
                yield mc(f'clear {f:x} {len(entries)} {cur}',f,setup)
    for current in (False,True):
        for existing in (False,True):
            def setup(e,current=current,existing=existing):
                base(e); return manager(e,(('tune',True),) if existing else (),current)
            yield mc(f'insert {current} {existing}',0x4b5470,setup,(lambda t:t['r'],))
    for parameter,name in ((0,'tune'),(1,None),(1,''),(1,'missing'),(1,'tune')):
        def setup(e,parameter=parameter,name=name):
            base(e); t=manager(e,(('tune',True),),parameter=parameter)
            t['query']=0 if name is None else e.object(len(name)+1,'lookup name',data=name.encode()+b'\0'); return t
        yield mc(f'lookup {parameter} {name}',0x4b54a0,setup,(lambda t:t['query'],))
    for enabled,found,play in ((0,True,1),(1,False,1),(1,True,0),(1,True,0x831)):
        def setup(e,enabled=enabled,found=found,play=play):
            base(e); return manager(e,(('tune' if found else 'else',True),),enabled=enabled,play=play)
        yield mc(f'play {enabled} {found} {play}',0x4b54f0,setup,(lambda t:t['name'],0xfffffffe))
    for f,argc in ((0x4b5550,0),(0x4b5570,1),(0x4b55a0,0),(0x4b55b0,1),(0x4b55d0,0)):
        for current in (False,True):
            def setup(e,current=current): base(e); return manager(e,current=current)
            yield mc(f'forward {f:x} {current}',f,setup,(0x814731,) if argc else ())
    def reload(e):
        base(e); t=manager(e); alternate=resource(e,play=0x8a1)
        vt=e.get(t['r'])
        def stop(e,c): e.put(t['m']+0x1c,alternate,0xa123); return 0x511
        e.put(vt+0x30,e.stub('replace current on stop','thiscall',0,stop)); return t
    yield mc('replay reloads current and parameter',0x4b5570,reload,(0x7541,))
    for driver in (0,0x5197):
        for v in (-2147483648,-1,0,1,39,99,100,2147483647):
            def setup(e,driver=driver): base(e); e.put(D,driver)
            yield Case(f'set volume {driver} {v}',0x4b55e0,setup,arguments=(v&0xffffffff,))
        for v in (-2147483648,-1,0,1,63,126,127,2147483647):
            def setup(e,driver=driver,v=v): base(e); e.put(D,driver); e.override(0x546e8c,returns(v&0xffffffff))
            yield Case(f'get volume {driver} {v}',0x4b5650,setup)
    for valid in (0,1):
        yield rc(f'valid handle {valid}',0x4b56a0,extra=lambda e,r,valid=valid:e.put(r+0x58,valid))
    for f,args in ((0x4b56b0,(0,)),(0x4b56b0,(0x101,)),(0x4b56b0,(0x100,)),(0x4b56d0,())):
        yield rc(f'destructor {f:x} {args}',f,args=args,payload=True)
    for valid in (0,1,0x80):
        for f,args in ((0x4b5a80,(0x7619,0)),(0x4b5a80,(0x9143,0xffffffff)),(0x4b5ad0,()),(0x4b5a40,())):
            yield rc(f'resource operation {f:x} {valid} {args}',f,valid=valid,args=args,payload=bool(valid))
    for f in (0x4b5b00,0x4b5b40,0x4b5b90,0x4b5bd0):
        for valid,status,pause,force in ((0,4,2,0),(1,4,0,0),(1,16,3,0),(1,1,0,0),(1,1,1,0),(1,1,2,0),(1,1,3,1),(1,1,0xffffffff,0),(1,4,0xffffffff,0)):
            yield rc(f'pause state {f:x} {valid} {status} {pause} {force}',f,valid,status,pause,args=(force,) if f==0x4b5b40 else ())
    def stop_mutation(e,r):
        def stop(e,c): e.put(r+0x44,0x1247); return 0
        e.override(0x546e84,stop)
    yield rc('pause reloaded after stop',0x4b5b00,pause=0,extra=stop_mutation)
    def start_mutation(e,r):
        def start(e,c): e.put(r+0x58,0x9871); return 0
        e.override(0x546e90,start)
    yield rc('sequence reloaded after start',0x4b5a80,args=(0x3197,1),extra=start_mutation)
    # Load byte widths, terminators, existing payload, errors and default naming.
    for size,name,payload,driver,init,fail in ((0,'x',False,1,1,False),(3,'x',False,1,1,False),(4,'abc',False,0,1,False),(4,None,False,1,1,False),(5,'',False,1,1,False),(6,'ab',False,1,1,False),(7,'abcdef',False,1,0,False),(19,'longer-name',True,1,1,False),(8,'x',False,1,1,True)):
        data=bytes(random_source.randrange(1,256) for _ in range(max(4,size)))
        def setup(e,size=size,name=name,payload=payload,driver=driver,init=init,fail=fail,data=data):
            base(e); r=resource(e,payload=payload); e.put(D,driver); e.put(0x541320,0xffffffff)
            d=e.object(len(data),'input MIDI',data=data); n=0 if name is None else e.object(len(name)+1,'input name',data=name.encode()+b'\0')
            e.override(0x546e98,returns(init)); e.override(0x546e9c,returns(0x2391))
            if fail: e.override(NEW,allocate(fail=True))
            return {'r':r,'data':d,'name':n}
        yield Case(f'load {size} {name} {payload} {driver} {init} {fail}',0x4b58a0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['data'],size,lambda t:t['name']))
    yield rc('load null data',0x4b58a0,args=(0,0xffffffff,0))
    for stage in range(4):
        def setup(e,stage=stage):
            base(e); r=resource(e); data=e.object(13,'locked resource',fill=0x93)
            def find(e,c): e.put(0x541324,0x8219); return 0 if stage==0 else 0x3157
            def load(e,c): e.put(0x541324,0x9137); return 0 if stage==1 else 0x7315
            e.override(0x546ac8,find); e.override(0x546acc,load); e.override(0x546ac4,returns(0 if stage==2 else data)); e.override(0x546a54,returns(13))
            return {'r':r}
        yield Case(f'Windows resource stage {stage}',0x4b59c0,setup,receiver=lambda t:t['r'],arguments=(0x34,0x8913))
    for init in (0,1):
        def setup(e,init=init):
            base(e); t=manager(e,current=False); t['data']=e.object(7,'create MIDI',data=b'\x91\x83\x75\x67\x59\x4b\x3d'); t['n']=e.object(5,'create name',data=b'tune\0'); e.override(0x546e98,returns(init)); return t
        yield mc(f'create resource init {init}',0x4b53f0,setup,(lambda t:t['data'],7,lambda t:t['n']))
    def play_parameter(e):
        base(e); t=manager(e,(('tune',True),))
        def stop(e,c): e.put(t['m']+0x20,0xdead7123); return 0
        e.put(e.get(t['r'])+0x30,e.stub('stop changes playback parameter','thiscall',0,stop)); return t
    yield mc('play reloads parameter after stopping old current',0x4b54f0,play_parameter,(lambda t:t['name'],0x5513))
    def cleanup_mutation(e,r):
        replacement=e.object(11,'replacement cleanup payload',fill=0x91)
        def stop(e,c): e.put(r+0x58,0x7139); return 0
        e.put(e.get(r)+0x30,e.stub('cleanup stop replaces sequence','thiscall',0,stop))
        def release(e,c): e.put(r+0x5c,replacement); return 0
        e.override(0x546e94,release)
    yield rc('cleanup reloads handle and payload after callbacks',0x4b5a40,payload=True,extra=cleanup_mutation)
    for init_result in (0,0x8123):
        def setup(e,init_result=init_result):
            base(e); r=resource(e); d=e.object(9,'replacement source',fill=0x83); other=e.object(9,'replacement MIDI payload',fill=0x69)
            name=e.object(64,'max normal resource name',data=b'Q'*63+b'\0')
            def sequence(e,c): e.put(r+0x5c,other); return 0
            def initialize(e,c): e.put(r+0x58,0x9231); return init_result
            e.override(0x546e9c,sequence); e.override(0x546e98,initialize)
            return {'r':r,'data':d,'name':name}
        yield Case(f'load reloads payload and failed sequence {init_result}',0x4b58a0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['data'],9,lambda t:t['name']))
    def resource_vtable_reload(e):
        base(e); r=resource(e); replacement=resource(e); d=e.object(17,'resource bytes',fill=0x9b)
        e.override(0x546ac8,returns(0x7319)); e.override(0x546acc,returns(0x4197)); e.override(0x546ac4,returns(d))
        def size(e,c): e.put(r,e.get(replacement)); return 17
        e.override(0x546a54,size); return {'r':r}
    yield Case('resource callback vtable reloaded after size',0x4b59c0,resource_vtable_reload,receiver=lambda t:t['r'],arguments=(0x317,0x9a13))
    # Hash collisions and distinct content expose wrong node order/value offsets.
    for i in range(8):
        key='r'+str(random_source.randrange(100000,999999)); marker=random_source.randrange(1,0xffffffff)
        def setup(e,key=key,marker=marker):
            base(e); t=manager(e,((key,True),('other',False)),current=False)
            t['query']=e.object(len(key)+1,'random lookup',data=key.encode()+b'\0'); e.put(t['r']+0x4c,marker); return t
        yield mc(f'random map lookup {i}',0x4b54a0,setup,(lambda t:t['query'],))
    for function,args in ((0x4b5a80,(0x8347,1)),(0x4b5ad0,()),(0x4b5b00,()),(0x4b5b40,(0,)),(0x4b5b90,()),(0x4b5bd0,())):
        for status in (1,4,16):
            yield rc(f'original resource vtable {function:x} status {status}',function,status=status,args=args,extra=lambda e,r:e.put(r,0x513528))
    # Constructors must publish initialized state even when original load rejects
    # its inputs before it can overwrite defaults. Poison allocation contents so
    # zero-initialized allocator memory cannot conceal a missing field write.
    for rejection in ('null input','short input','missing driver','success'):
        for fill in (0x39,0xc7):
            def setup(e,rejection=rejection,fill=fill):
                base(e); t=manager(e,current=False)
                t['data']=e.object(7,'constructor MIDI input',data=b'\x93\x81\x6f\x5d\x4b\x39\x27')
                t['n']=e.object(5,'constructor name',data=b'tune\0')
                if rejection=='missing driver': e.put(D,0)
                if rejection=='null input': t['data']=0
                t['size']=3 if rejection=='short input' else 7
                def poisoned_new(e,c):
                    return e.object(c.arguments[0],'poisoned original allocation',fill=fill)
                e.override(NEW,poisoned_new)
                return t
            yield mc(f'constructor state before {rejection} fill {fill}',0x4b53f0,setup,(lambda t:t['data'],lambda t:t['size'],lambda t:t['n']))
