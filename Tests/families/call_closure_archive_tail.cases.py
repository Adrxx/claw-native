"""Independent original-backed archive and message presentation cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns


def tree(env, at, payloads, embedded=None):
    buckets=env.object(16,'buckets',fill=0)
    env.put(at,1,buckets)
    nodes=[(p+embedded if embedded is not None else env.object(24,'node',fill=0)) for p in payloads]
    env.put(buckets+8,nodes[0]+4 if nodes else 0)
    for i,(n,p) in enumerate(zip(nodes,payloads)):
        env.put(n,0,nodes[i+1]+4 if i+1<len(nodes) else 0,0,at,0,p)
    return nodes


def base(env, seed=0x12345678):
    entry=env.object(0x70,'entry',fill=0)
    parent=env.object(0x50,'directory',fill=0)
    archive=env.object(0x48,'archive',fill=0)
    env.put(entry+0x24,parent)
    env.put(parent+0x10,0x13579bdf,0x2468ace0,archive)
    env.put(archive+4,0xaba1aba2)
    env.put(archive+0x1c,0x1437)
    env.put(archive+0x28,0x91abcdef)
    env.put(archive+0x34,7)
    env.put(archive+0x40,11)
    tree(env,parent+0x3c,[])
    tree(env,parent+0x44,[])
    def timestamp(e,c):
        e.put(c.arguments[0],seed ^ 0x55555555)
        return seed
    env.override(0x4a3b10,timestamp)
    return dict(entry=entry,parent=parent,archive=archive)


def cursor(env, first=1, positive_delay=0, negative_delay=0, result=0x71628394):
    record=env.object(256,'cursor-message-observations',fill=0)
    def show(e,c):
        i=e.get(record)
        e.put(record,i+1)
        e.put(record+8+i*4,c.arguments[0])
        if c.arguments[0]:
            k=e.get(record+4);e.put(record+4,k+1)
            return first if k==0 else (-1 if k<=positive_delay else 2)
        k=e.get(record+248);e.put(record+248,k+1)
        return 1 if k<negative_delay else 0xffffffff
    def message(e,c):
        e.put(record+224,*c.arguments)
        data=e.cstr(c.arguments[1])
        e.write(record+128,data[:80]+b'\0')
        return result
    env.override(0x546d54,show)
    env.override(0x546d48,message)
    return record


def application(env, display=False):
    app=env.object(0x38,'app',fill=0)
    window=env.object(8,'window',words=[0x87654321,0x16738495])
    env.put(app+4,window)
    if display:
        d=env.object(0x30,'display',fill=0);render=env.object(0x20,'render',fill=0)
        arg=env.object(0x30,'restore-argument',fill=0)
        env.put(render+0x14,arg);env.put(d+4,render)
        surface=env.object(4,'surface',fill=0);vt=env.object(0x30,'surface-vtable',fill=0)
        env.put(surface,vt)
        observations=env.object(8,'restore-observations',fill=0)
        def restore(e,c):e.put(observations,c.arguments[0]);return 0x7123
        env.put(vt+0x28,env.stub('surface restore','stdcall',1,restore))
        slot=env.object(4,'surface-slot',words=[surface]);env.put(d+0x1c,slot)
        env.put(app+0x30,d)
    return app


def io(env, t, short=False, mutate=False):
    archive=t['archive']
    vt=env.object(12,'archive-vtable',fill=0)
    env.put(archive,vt)
    env.put(vt+8,env.stub('archive retry','thiscall',0,returns(0)))
    stream=env.object(32,'FILE-identity',fill=0x72)
    env.put(archive+0xc,stream)
    record=env.object(8192,'stream-observations',fill=0)
    def seek(e,c):
        e.put(record+4,c.arguments[1])
        return 0
    def write(e,c):
        n=c.arguments[1]*c.arguments[2]
        used=e.get(record)
        e.put(record+32+used,e.get(record+4),n)
        e.write(record+40+used,e.read(c.arguments[0],n))
        e.put(record,used+8+n)
        if mutate:
            e.put(archive+0x1c,0x19a7)
            e.put(t['entry']+0x14,3)
        return 0 if short else c.arguments[2]
    env.override(0x4a7840,seek)
    env.override(0x4a73e0,write)
    return record


def cases(random_source):
    for old in (0,1,17):
      for new in (0,1,4,19):
       for cache in (False,True):
        def setup(env,old=old,new=new,cache=cache):
            t=base(env,random_source.getrandbits(32))
            env.put(t['entry']+0x14,old,env.object(max(old,1),'old-data',data=bytes(range(max(old,1)))))
            env.put(t['entry']+0x28,0x99887766)
            if cache:env.put(t['parent']+0x20,env.object(9,'parent-cache',fill=0x7b))
            return t
        yield Case(f'resize {old}->{new} cache {cache}',0x4b6260,setup,receiver=lambda t:t['entry'],arguments=(new,))
    for capacity in (0,1,3):
      for index in (0,1,3,5):
       for high in (0,1,9):
        def setup(env,capacity=capacity,high=high):
            t=base(env)
            env.put(t['entry']+0x1c,capacity)
            old=env.object(max(4,capacity*4),'old-indices',data=b''.join((0x71620000+i*0x34567).to_bytes(4,'little') for i in range(max(1,capacity))))
            env.put(t['entry']+0x20,old)
            env.put(t['archive']+0x34,high)
            return t
        yield Case(f'index cap{capacity} index{index} high{high}',0x4b62d0,setup,receiver=lambda t:t['entry'],arguments=(index,random_source.getrandbits(32)))
    def no_old(env):
        t=base(env);env.put(t['entry']+0x1c,0,0);return t
    yield Case('index no prior pointer',0x4b62d0,no_old,receiver=lambda t:t['entry'],arguments=(2,0x97654321))
    for name in (None,b'',b'a',b'abc',b'abcd',b'long-name-17.dat'):
      for old in (False,True):
       for bound in (0,4,99):
        def setup(env,name=name,old=old,bound=bound):
            t=base(env)
            if old:env.put(t['entry']+0xc,env.object(9,'old-name',data=b'old-name\0'))
            t['name']=0 if name is None else env.object(len(name)+1,'new-name',data=name+b'\0')
            env.put(t['archive']+0x40,bound)
            return t
        yield Case(f'name {name!r} old{old} bound{bound}',0x4b6350,setup,receiver=lambda t:t['entry'],arguments=(lambda t:t['name'],))
    for timestamp in (0,1,0x81234567,random_source.getrandbits(32)):
        yield Case(f'timestamp {timestamp:x}',0x4b6480,lambda e,v=timestamp:base(e,v),receiver=lambda t:t['entry'])
    for value in (0,1,0x87654321,random_source.getrandbits(32)):
        yield Case(f'image error callback {value:x}',0x4bd090,arguments=(value,))
    for recursive in (0,1,0xffffffff):
      for cache in (False,True):
       for count in (0,1,2):
        def setup(env,cache=cache,count=count):
            t=base(env)
            if cache:env.put(t['parent']+0x20,env.object(13,'cache',fill=0xe3))
            buckets=[]
            for i in range(count):
                b=env.object(0x30,'entry-group',fill=0);entries=[]
                for j in range(i+1):
                    entry=env.object(0x70,'group-entry',fill=0)
                    env.put(entry+0x18,env.object(5+j,'entry-data',fill=0x51+j))
                    entries.append(entry)
                tree(env,b+0x1c,entries,0x48);buckets.append(b)
            tree(env,t['parent']+0x44,buckets,4)
            children=[]
            for i in range(count):
                child=env.object(0x50,'child-directory',fill=0)
                tree(env,child+0x44,[]);tree(env,child+0x3c,[])
                env.put(child+0x20,env.object(7,'child-cache',fill=0x7c));children.append(child)
            tree(env,t['parent']+0x3c,children)
            return t
        yield Case(f'release cache{cache} groups{count} recursive{recursive}',0x4b6820,setup,receiver=lambda t:t['parent'],arguments=(recursive,))
    for first in (2,0,-1):
      for delay in (0,2):
       for back in (0,2):
        for display in (False,True):
         def setup(env,first=first,delay=delay,back=back,display=display):
            app=application(env,display);cursor(env,first,delay,back)
            return dict(app=app,text=env.object(15,'message-text',data=b'Message 42!?\0'))
         yield Case(f'message cursor{first} delay{delay}/{back} display{display}',0x42a690,setup,receiver=lambda t:t['app'],arguments=(lambda t:t['text'],0x12345678))
    for text in (None,b'',b'hello',b'Text %d!?'):
      for error in (0,-7,1,2147483647):
       for app_present in (False,True):
        def setup(env,text=text,app_present=app_present):
            m=env.object(8,'multiplayer',fill=0)
            if app_present:env.put(m+4,application(env));cursor(env,0,1,1)
            p=0 if text is None else env.object(len(text)+1,'text',data=text+b'\0')
            return dict(m=m,text=p)
        yield Case(f'multiplayer message {text!r} error{error} app{app_present}',0x47c4b0,setup,receiver=lambda t:t['m'],arguments=(lambda t:t['text'],error))
    yield Case('flush zero data',0x4b63e0,lambda e:base(e),receiver=lambda t:t['entry'])
    yield Case('write index empty',0x4b6c50,lambda e:dict(base(e),out=e.object(4,'index-size',fill=0xa6)),receiver=lambda t:t['parent'],arguments=(0x1234,lambda t:t['out']))

    for size in (1,3,9):
      for offset in (0,0x1291):
       for short in (False,True):
        for mutate in (False,True):
         def setup(env,size=size,offset=offset,short=short,mutate=mutate):
            t=base(env)
            data=env.object(size,'data-to-flush',data=bytes((i*31+7)&255 for i in range(size)))
            env.put(t['entry']+0x14,size,data)
            env.put(t['entry']+0x28,offset)
            io(env,t,short,mutate)
            return t
         yield Case(f'flush size{size} off{offset} short{short} mutate{mutate}',0x4b63e0,setup,receiver=lambda t:t['entry'])
    for directories in (0,1,2):
      for groups in (0,1,2):
       for names in (False,True):
        for count in (0,1,3):
         for short in (False,True):
          def setup(env,directories=directories,groups=groups,names=names,count=count,short=short):
            t=base(env);io(env,t,short)
            children=[]
            for i in range(directories):
                d=env.object(0x30,'serialized-directory',fill=0)
                env.put(d,env.object(8,'directory-name',data=b'dir-17!\0') if names else 0,0x128100+i,0x427300+i)
                env.put(d+0x14,0x789100+i);children.append(d)
            tree(env,t['parent']+0x3c,children)
            buckets=[]
            for i in range(groups):
                b=env.object(0x30,'serialized-group',fill=0);env.put(b,0x719300+i)
                entries=[]
                for j in range(i+1):
                    entry=env.object(0x70,'serialized-entry',fill=0)
                    env.put(entry,env.object(8,'entry-name',data=b'entry.X\0') if names else 0,0x918000+j)
                    env.put(entry+0xc,env.object(6,'alias',data=b'alias\0') if names else 0)
                    env.put(entry+0x10,0x613782+j,0x927435+j)
                    env.put(entry+0x1c,count,env.object(max(4,count*4),'indices',data=b''.join((0x97823611+k*0x3182).to_bytes(4,'little') for k in range(max(1,count)))))
                    env.put(entry+0x28,0x719823+j);entries.append(entry)
                tree(env,b+0x1c,entries);buckets.append(b)
            tree(env,t['parent']+0x44,buckets)
            t['out']=env.object(4,'index-byte-count',fill=0xa7)
            return t
          yield Case(f'index dir{directories} groups{groups} names{names} count{count} short{short}',0x4b6c50,setup,receiver=lambda t:t['parent'],arguments=(0x1357,lambda t:t['out']))
    for new in (0,11):
        def setup(env):
            t=base(env);env.put(t['entry']+0x14,7)
            env.override(0x4f63ec,allocate(fail=True))
            return t
        yield Case(f'resize allocation failure size{new}',0x4b6260,setup,receiver=lambda t:t['entry'],arguments=(new,))
    def changed_index(env):
        t=base(env);old=env.object(12,'original-indices',words=[0x11112222,0x33334444,0x55556666]);replacement=env.object(12,'replacement-indices',words=[0xabcde123,0x98765432,0x10102020])
        env.put(t['entry']+0x1c,3,old)
        def effect(e,c):
            result=e.object(c.arguments[0],'allocation',fill=0x91)
            e.put(t['entry']+0x20,replacement)
            return result
        env.override(0x4f63ec,effect)
        return t
    yield Case('index pointer re-read after allocation',0x4b62d0,changed_index,receiver=lambda t:t['entry'],arguments=(4,0x83847576))
    for fn in (0x4b6820,0x4b6c50):
        def empty_group(env):
            t=base(env);b=env.object(0x30,'empty-entry-group',fill=0)
            tree(env,b+0x1c,[]);tree(env,t['parent']+0x44,[b],4)
            t['out']=env.object(4,'index-byte-count',fill=0x9d)
            if fn==0x4b6c50:io(env,t)
            return t
        yield Case(f'empty group {fn:x}',fn,empty_group,receiver=lambda t:t['parent'],arguments=(1,) if fn==0x4b6820 else (0x2713,lambda t:t['out']))
