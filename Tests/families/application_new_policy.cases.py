"""Blind source-created allocation-policy owners and physical Win32 services."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt

GET, SET = 0x5022b5, 0x4f63d8
FIELDS = ('eax','ebx','ecx','edx','esi','edi','ebp')


def profile(rng, root, number, history=(), thread=0, failure=None):
    stack = rng.randbytes(0x20000)
    regs = [rng.getrandbits(32) for _ in FIELDS]
    flags = 2 | (rng.getrandbits(12) & 0x8d5)
    fill = rng.randrange(1,256)
    index = rng.randrange(1,30)
    frame = (0x2008000,0x2003000,0x200f000)[number % 3] - number % 13 * 16
    pc = 0x4f63dd if root == GET else 0x4a1b3a

    def setup(env):
        env.write(0x1ff0000, stack)
        env.object(1 + number % 17 * 13, 'independent heap address spacing', fill=fill)
        state = env.object(0x5000, 'physical process and logical thread ownership', fill=0)
        log = env.object(0x20000, 'physical CPU publication and result journal', fill=0)
        env.put(state, index, thread)
        # Physical tables are separate from every source-created record.
        def record(e,c,result):
            n=e.get(state+8); p=log+n*256
            e.put(state+8,n+1)
            e.put(p,c.function,c.stack_pointer,c.source_return_pc,c.receiver,len(c.arguments),*c.arguments)
            if c.source_context is not None:
                e.write(p+48,bytes(c.source_context))
            e.put(p+128,result,e.get(state+4),e.get(0x540af0),e.get(0x53eca0),e.get(0x53ec9c))
            e.write(p+160,e.read(c.stack_pointer,32))
            return result
        def tlsalloc(e,c):
            i=e.get(state);e.put(state,i+1);return i
        def tlsget(e,c):
            return e.get(state+0x100+e.get(state+4)*256+c.arguments[0]*4)
        def tlsset(e,c):
            e.put(state+0x100+e.get(state+4)*256+c.arguments[0]*4,c.arguments[1]);return 1
        def local(e,c):
            f,n=c.arguments
            return e.object(max(1,n),'physical LocalAlloc backing',fill=0 if f&0x40 else fill)
        def localresize(e,c):
            old,n,f=c.arguments
            p=e.object(max(1,n),'physical moved LocalReAlloc backing',fill=0 if f&0x40 else fill)
            e.write(p,e.read(old,min(e.spans[old],n)));e.release(old);return p
        def globalalloc(e,c):
            f,n=c.arguments
            p=e.object(max(1,n),'physical movable data',fill=0 if f&0x40 else fill)
            h=e.object(16,'distinct physical movable handle',words=[p,n,0,f])
            i=e.get(state+12);e.put(state+12,i+1);e.put(state+0x1000+i*4,h);return h
        def handle(e,c):
            for i in range(e.get(state+12)):
                h=e.get(state+0x1000+i*4)
                if e.get(h)==c.arguments[0]:return h
            return 0
        def lock(e,c):
            h=c.arguments[0]
            if not h:return 0
            e.put(h+8,e.get(h+8)+1);return e.get(h)
        def unlock(e,c):
            h=c.arguments[0]
            if not h:return 0
            n=max(0,e.get(h+8)-1);e.put(h+8,n);return int(n!=0)
        def resize(e,c):
            h,n,f=c.arguments;old=e.get(h)
            p=e.object(max(1,n),'physical moved global data',fill=0 if f&0x40 else fill)
            e.write(p,e.read(old,min(e.get(h+4),n)));e.release(old)
            e.put(h,p,n,e.get(h+8),f);return h
        def section(e,c):
            p=c.arguments[0];tid=e.get(state+4)+0x331
            if c.function==0x546aa4:e.put(p,0,0xffffffff,0,0,0,0)
            elif c.function==0x546aac:e.put(p+4,(e.get(p+4)+1)&0xffffffff,e.get(p+8)+1,tid)
            else:
                n=e.get(p+8)-1;e.put(p+4,(e.get(p+4)-1)&0xffffffff,n,tid if n else 0)
            return 0
        def throwing(e,c):
            e.write(log+0x1ff00,e.read(c.arguments[3],12));raise Halt()
        effects={0x546a90:tlsalloc,0x546a7c:tlsget,0x546a84:tlsset,
                 0x546aa8:local,0x546a80:localresize,0x546b1c:globalalloc,
                 0x546a8c:handle,0x5469c4:lock,0x5469c8:unlock,0x546a88:resize,
                 0x546aa4:section,0x546aac:section,0x546a9c:section,
                 0x546abc:lambda e,c:4,0x546958:throwing}
        for address,effect in effects.items():
            def observed(e,c,effect=effect):
                if failure and c.function==failure[0] and e.calls_so_far(c.function)==failure[1]:
                    return record(e,c,0xffffffff if c.function==0x546a90 else 0)
                return record(e,c,effect(e,c))
            env.override(address,observed)
        fs=0xffffffff
        for i in range(number%4):
            p=0x200fc00+i*32;env.put(p,fs,0x508525,0xffffffff);fs=p
        def context(entry):
            c=NativeSourceContext(size=72,version=1,inputMask=0x7ff,outputMask=0x7ff,preserveMask=0,
                esp=frame,eip=entry,eflags=flags,fsHead=fs)
            for name,value in zip(FIELDS,regs):setattr(c,name,value)
            return c
        # Only original roots create records or change handler fields. Carry the
        # actual resulting image and physical tables forward between setup calls.
        for ordinal,(tid,entry,args) in enumerate(history):
            env.put(state+4,tid)
            env._freeze()
            result=env.run_original_context(entry,context(entry),source_return_pc=0x4f63dd if entry==GET else 0x4a1b3a,
                source_convention='cdecl' if entry==GET else 'stdcall',arguments=args,check_objects=True)
            if result.errors or not result.completed:
                raise RuntimeError('original setup root failed: '+str(result.errors))
            env.backend,env.side='initial','setup'
            env._initial['heap'][:]=result.heap
            env._initial['image'][env.data_offset:]=result.image
            env.put(log+0x1f000+ordinal*16,tid,entry,result.eax)
        env.put(state+4,thread)
        env.write(0x1ff0000,stack)
        for i in range(number%4):
            p=0x200fc00+i*32;env.put(p,0xffffffff if i==0 else p-32,0x508525,0xffffffff)
        return {'source':context(root)}
    return setup,pc


def cases(random_source):
    words=(0,0x4f63d0,0x4fe0e5,1,0xffffffff,0x80000000,0x7fffffff,0x55aa55aa,0xaa55aa55)
    histories=((),((0,GET,()),),((0,SET,(0,)),),
        ((0,GET,()),(0,SET,(0x55aa55aa,)),(0,SET,(0x55aa55aa,))),
        ((0,SET,(0xffffffff,)),(1,GET,()),(1,SET,(0x80000000,))),
        ((1,SET,(0x4fe0e5,)),(0,SET,(0,)),(2,SET,(1,)),(1,GET,())))
    for i in range(54):
        history=histories[i%len(histories)]
        root=GET if i%3==0 else SET
        value=words[(i//3)%len(words)] if i<27 else random_source.getrandbits(32)
        setup,pc=profile(random_source,root,i,history,thread=(i//6)%3)
        yield Case(f'source-created owner profile {i} root {root:x} word {value:x}',root,setup,
            arguments=() if root==GET else (value,),source_context=lambda t:t['source'],source_return_pc=pc)
    for i,(service,nth) in enumerate(((0x546a90,1),(0x546b1c,1),(0x546aa8,1),(0x546aa8,2),(0x546aa8,3),(0x546aa8,4),(0x546a80,1))):
        for root in (GET,SET):
            setup,pc=profile(random_source,root,60+i,failure=(service,nth))
            yield Case(f'physical failure {service:x}/{nth} root {root:x}',root,setup,
                arguments=() if root==GET else (0,),expect='halt',source_context=lambda t:t['source'],source_return_pc=pc)
