"""Blind cases: original allocator, original policy owners, physical services only."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt

NEW = 0x4f63ec
FIELDS = ('eax','ebx','ecx','edx','esi','edi','ebp')


def profile(rng, number, size, mode):
    stack = rng.randbytes(0x20000)
    registers = [rng.getrandbits(32) for _ in FIELDS]
    flags = 2 | (rng.getrandbits(12) & 0x8d5)
    fill = rng.randrange(1, 256)
    frame = (0x2007000, 0x2003000, 0x200d000)[number % 3] - 16*(number % 11)
    def setup(env):
        env.write(0x1ff0000, stack)
        env.object(1+number*7, 'address variation', fill=fill)
        state = env.object(0x18000, 'physical service ledger', fill=0)
        journal = env.object(0x30000, 'physical service observations', fill=0)
        # state: denyVM, quota, nextTLS, recordCount, eventCount, clock.
        env.put(state, 0, 0x210 if mode.startswith('pool') else 0x100000, 3+number%19, 0, 0, 0x12345670+number)
        def blocks(e):
            return [state+0x1000+i*24 for i in range(e.get(state+12))]
        def lookup(e,a,kind=None):
            for p in blocks(e):
                if e.get(p)==a and e.get(p+16) and (kind is None or e.get(p+8)==kind):return p
            return 0
        def allocate(e,n,kind,zero=False,handle=False):
            a=e.object(max(1,n),'physical backing',fill=0 if zero else fill)
            h=e.object(16,'distinct movable handle',fill=0) if handle else a
            i=e.get(state+12);e.put(state+12,i+1)
            e.put(state+0x1000+i*24,h,n,kind,a,1,0)
            return h
        def heapused(e):return sum(e.get(p+4) for p in blocks(e) if e.get(p+8)==1 and e.get(p+16))
        def heapalloc(e,c):
            h,f,n=c.arguments
            return 0 if heapused(e)+n>e.get(state+4) else allocate(e,n,1,bool(f&8))
        def heapfree(e,c):
            p=lookup(e,c.arguments[2],1)
            if not p:return 0
            e.put(p+16,0);e.release(e.get(p+12));return 1
        def heapsize(e,c):
            p=lookup(e,c.arguments[2],1);return e.get(p+4) if p else 0xffffffff
        def heapresize(e,c):
            h,f,a,n=c.arguments;p=lookup(e,a,1)
            if not p or f!=0x10 or n>e.get(p+4) or heapused(e)-e.get(p+4)+n>e.get(state+4):return 0
            e.put(p+4,n);return a
        def virtual(e,c):
            a,n,f,protect=c.arguments
            if e.get(state):return 0
            if f==0x2000 and a==0:return allocate(e,n,2,True)
            if f==0x1000:
                for p in blocks(e):
                    b=e.get(p+12)
                    if e.get(p+8)==2 and e.get(p+16) and b<=a and a+n<=b+e.get(p+4):return a
            return 0
        def vfree(e,c):
            p=lookup(e,c.arguments[0],2)
            if not p:return 0
            e.put(p+16,0);e.release(e.get(p+12));return 1
        def tlsalloc(e,c):
            i=e.get(state+8);e.put(state+8,i+1);return i
        def tlsget(e,c):return e.get(state+0x100+c.arguments[0]*4)
        def tlsset(e,c):e.put(state+0x100+c.arguments[0]*4,c.arguments[1]);return 1
        def local(e,c):return allocate(e,c.arguments[1],3,bool(c.arguments[0]&0x40))
        def glob(e,c):return allocate(e,c.arguments[1],4,bool(c.arguments[0]&0x40),True)
        def resize(e,c):
            old,n,f=c.arguments;p=lookup(e,old);kind=e.get(p+8);data=e.get(p+12)
            if not (f&2) and n>e.get(p+4):return 0
            if n<=e.get(p+4):e.put(p+4,n);return old
            a=e.object(max(1,n),'resized backing',fill=0 if f&0x40 else fill)
            e.write(a,e.read(data,min(n,e.get(p+4))));e.release(data)
            e.put(p+4,n,kind,a)
            if kind==3:e.put(p,a)
            return old if kind==4 else a
        def globlock(e,c):
            p=lookup(e,c.arguments[0],4)
            if not p:return 0
            e.put(p+20,e.get(p+20)+1);return e.get(p+12)
        def globhandle(e,c):
            for p in blocks(e):
                if e.get(p+12)==c.arguments[0] and e.get(p+8)==4 and e.get(p+16):return e.get(p)
            return 0
        def unlock(e,c):
            p=lookup(e,c.arguments[0],4)
            if not p:return 0
            n=max(0,e.get(p+20)-1);e.put(p+20,n);return int(n!=0)
        def section(e,c):
            p=c.arguments[0]
            if c.function==0x546aa4:e.put(p,0,0xffffffff,0,0,0,0)
            elif c.function==0x546aac:e.put(p+4,(e.get(p+4)+1)&0xffffffff,e.get(p+8)+1,0x1024+number)
            else:
                n=e.get(p+8)-1;e.put(p+4,(e.get(p+4)-1)&0xffffffff,n,0x1024+number if n else 0)
            return 0
        def clock(e,c):
            n=e.get(state+20);e.put(state+20,n+17);return n
        def cursor(e,c):e.put(c.arguments[0],number,number+31);return 1
        def throwing(e,c):
            if c.source_return_pc!=0x4a56cf or c.arguments[1:3]!=(1,3):
                raise RuntimeError('unsupported physical exception transfer')
            e.write(journal+0x2ff00,e.read(c.arguments[3],12));raise Halt()
        effects={0x546950:lambda e,c:0x1001,0x54694c:lambda e,c:1,
            0x546960:heapalloc,0x546964:heapfree,0x54692c:heapsize,0x546928:heapresize,
            0x546990:virtual,0x546954:vfree,0x546a90:tlsalloc,0x546a7c:tlsget,0x546a84:tlsset,
            0x546aa8:local,0x546a80:resize,0x546b1c:glob,0x546a88:resize,
            0x5469c4:globlock,0x546a8c:globhandle,0x5469c8:unlock,
            0x546aa4:section,0x546aac:section,0x546a9c:section,0x546df0:clock,
            0x546abc:lambda e,c:4,0x5469bc:lambda e,c:0xfffffffe,
            0x5469c0:lambda e,c:0x1024+number,0x546cd0:cursor,0x546958:throwing}
        for address,effect in effects.items():
            def observed(e,c,effect=effect):
                i=e.get(state+16);e.put(state+16,i+1);p=journal+(i%1024)*128
                e.put(p,c.function,c.stack_pointer,c.source_return_pc,len(c.arguments),*c.arguments)
                if c.source_context is not None:e.write(p+40,bytes(c.source_context))
                result=effect(e,c);e.put(p+112,result);return result
            env.override(address,observed)
        fs=0x200fc00
        env.put(fs,0xffffffff,0x508525,0xffffffff)
        def context(entry):
            c=NativeSourceContext(size=72,version=1,inputMask=0x7ff,outputMask=0x7ff,preserveMask=0,
                esp=frame,eip=entry,eflags=flags,fsHead=fs)
            for name,value in zip(FIELDS,registers):setattr(c,name,value)
            return c
        def source(entry,args=(),convention='cdecl'):
            env._freeze()
            r=env.run_original_context(entry,context(entry),source_return_pc=0x4f63ff,
                source_convention=convention,arguments=args,check_objects=True)
            if r.errors or not r.completed:raise RuntimeError('original setup '+hex(entry)+': '+str(r.errors))
            env.backend,env.side='initial','setup'
            env._initial['heap'][:]=r.heap;env._initial['image'][env.data_offset:]=r.image
            return r.eax
        source(0x4ab120);source(0x4a7b90)
        if mode.startswith('pool'):
            source(0x4251f0);source(0x4fb412);source(0x4fb41b,(0,),'stdcall')
            source(0x4f63d8,(0x4fe0e5,),'stdcall')
        elif mode in ('null','oversize'):source(0x4f63d8,(0,),'stdcall')
        elif mode=='throw':source(0x5022b5)
        if mode not in ('success','oversize'):
            env.put(state,1)
            if mode in ('null','throw'):env.put(state+4,0)
            for drain_size in dict.fromkeys((0x134,min(size,0x134))):
                for _ in range(512):
                    if not source(0x4a48e0,(drain_size,)):break
                else:raise RuntimeError('bounded original exhaustion did not complete')
            if mode=='pool-free':env.put(state+4,512)
        env.write(0x1ff0000,stack);env.put(fs,0xffffffff,0x508525,0xffffffff)
        return {'source':context(NEW)}
    return setup


def cases(random_source):
    sizes=(0,1,15,16,17,31,32,0x133,0x134,0x135,0x1ff,0x200,0x201,0x1000)
    for i,size in enumerate(sizes+(random_source.randrange(2,0x1800),random_source.randrange(2,0x1800))):
        yield Case(f'actual allocation {i} size {size:x}',NEW,profile(random_source,i,size,'success'),
            arguments=(size,),source_context=lambda t:t['source'],source_return_pc=0x423470)
    for i,(mode,size) in enumerate((('null',0x134),('null',0x1000),('oversize',0xffffffe1),('oversize',0xffffffff),('throw',0x134),
                                   ('pool-shrink',0x134),('pool-shrink',0x120),('pool-free',0x200))):
        yield Case(f'original {mode} request {size:x}',NEW,profile(random_source,20+i,size,mode),
            arguments=(size,),expect='halt' if mode=='throw' else 'return',
            source_context=lambda t:t['source'],source_return_pc=0x423470)
