"""Bounded original-side cases for archive, bitmap, image and surface helpers."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

NEW = 0x4f63ec

def case(label, function, setup, arguments=()):
    return Case(label, function, setup, receiver=lambda t:t['self'], arguments=arguments)

def surface(env, height=3, row=5, stride=8, lock=0, mutate=None):
    target=env.object(0xbc,'surface',fill=0)
    pixels=env.object(max(128,abs(height)*max(1,abs(stride))+abs(row)+16),'pixels')
    dd=env.object(4,'ddraw');vt=env.object(0x84,'ddraw-vtable',fill=0)
    log=env.object(64,'surface-call-log',fill=0)
    def locked(env,c):
        env.put(log,env.get(log)+1,*c.arguments)
        env.put(target+0x30,pixels)
        if mutate is not None:env.put(target+0x14,*mutate)
        return lock
    def unlocked(env,c):
        env.put(log+28,env.get(log+28)+1,*c.arguments)
        return 0x19
    env.put(dd,vt)
    env.put(vt+0x64,env.stub('lock','stdcall',5,locked))
    env.put(vt+0x80,env.stub('unlock','stdcall',2,unlocked))
    env.put(target,0x513690)
    env.put(target+8,dd)
    env.put(target+0x14,height,row,stride)
    env.put(target+0x30,pixels)
    env.put(target+0xa4,8,row)
    return {'self':target,'pixels':pixels,'log':log}

def flip_setup(height,row,stride,lock=0,allocation_fail=False,allocation_shape=None):
    def setup(env):
        t=surface(env,height,row,stride,lock)
        if allocation_fail:env.override(NEW,allocate(fail=True))
        if allocation_shape is not None:
            def alloc(env,c):
                env.put(t['self']+0x14,*allocation_shape)
                return env.object(max(1,c.arguments[0]),'scratch')
            env.override(NEW,alloc)
        return t
    return setup

def bitmap_setup(width,height,bitmap_depth,context_depth,palette,target_depth=8,lock=0):
    def setup(env):
        t=surface(env,height,max(1,width)*3,max(1,width)*3+4,lock)
        env.put(t['self']+0x18,width)
        env.put(t['self']+0xa4,target_depth,max(1,width)*3)
        context=env.object(0x87c,'bitmap-context')
        env.put(context+0x474,context_depth)
        env.put(context+0x878,palette)
        bmp=env.object(0x1000,'bitmap')
        env.put(bmp+0x12,width)
        env.put(bmp+0x16,height)
        env.write(bmp+0x1c,bitmap_depth.to_bytes(2,'little'))
        env.put(bmp+0xa,0x440)
        t.update(context=context,bmp=bmp)
        return t
    return setup

def rle_setup(data,width,height,shifts):
    def setup(env):
        target=env.object(0x24,'image',fill=0)
        src=env.object(max(16,len(data)),'encoded-runs',data=bytes(data))
        pal=env.object(1024,'palette')
        env.put(target+4,width,height,src)
        env.put(target+0x20,pal)
        for at,value in zip((0x541368,0x54136c,0x541370,0x54135c,0x541360),shifts):env.put(at,value)
        return {'self':target,'source':src}
    return setup

def create_setup(result,tail=False):
    def setup(env):
        manager=env.object(0x3d4,'image-manager',fill=0)
        log=env.object(64,'create-log',fill=0)
        node=env.object(12,'free-list-node',fill=0)
        env.put(manager+0x3c8,node)
        if tail:
            old=env.object(12,'old-tail',fill=0)
            env.put(manager+0x3c0,old)
        def created(env,c):
            env.put(log,c.receiver,*c.arguments)
            return result
        def destroyed(env,c):
            env.put(log+24,c.receiver,*c.arguments)
            return 0
        env.put(0x513690+0x28,env.stub('create-image','thiscall',4,created))
        env.put(0x513690,env.stub('destroy-image','thiscall',1,destroyed))
        return {'self':manager}
    return setup

def archive_setup(gate=0,compact=False,path=b'C:\\CLAW\\CLAW.REZ',close=0):
    def setup(env):
        archive=env.object(0x48,'archive',fill=0)
        tree=env.object(0x4c,'empty-tree',fill=0)
        buckets=env.object(16,'empty-buckets',fill=0)
        methods=env.object(12,'archive-methods',fill=0)
        env.put(methods+8,env.stub('archive-error','thiscall',0,returns(0)))
        env.put(archive,methods)
        env.put(archive+4,gate if compact else 0x63)
        env.put(archive+0xc,0x12345678)
        env.put(archive+0x18,0xabcde1,0x200,gate if not compact else 0,tree,0x91726354)
        env.put(archive+0x34,0x12345678,0xabcdef12,0x71922331,0xc0d0e0f0)
        env.put(tree+0x18,archive)
        env.put(tree+0x3c,1,buckets,1,buckets)
        pathname=env.object(len(path)+1,'pathname',data=path+b'\0')
        env.put(archive+0x44,pathname)
        env.override(0x4a7840,returns(0))
        env.override(0x4a73e0,lambda e,c:c.arguments[2])
        env.override(0x4a7920,returns(0))
        env.override(0x4a7ae0,returns(close))
        env.override(0x4f1d90,returns(0x12343210))
        def clock(e,c):
            if c.arguments[0]:e.put(c.arguments[0],0x13579bdf)
            return 0x13579bdf
        env.override(0x4a3b10,clock)
        env.override(0x546adc,returns(1))
        env.override(0x546ae0,returns(1))
        env.override(0x546b0c,returns(0))
        if compact:
            # Physical allocator padding keeps the unchanged request visible.
            env.override(NEW,lambda e,c:e.object((c.arguments[0]+17)&~15,'padded-allocation'))
        return {'self':archive}
    return setup

def cases(random_source):
    for height in (-2,0,1,2,3,4,7):
        for row in (0,1,5,9):
            for extra in (0,3):
                yield case(f'flip h{height} row{row} pad{extra}',0x4b99d0,flip_setup(height,row,row+extra))
    for n in range(8):
        h=random_source.randrange(2,9);row=random_source.randrange(1,18)
        yield case(f'random flip {n}',0x4b99d0,flip_setup(h,row,row+2))
    yield case('flip lock null pixel',0x4b99d0,flip_setup(3,5,8,lock=0x80004005))
    yield case('flip scratch failure unlock',0x4b99d0,flip_setup(3,5,8,allocation_fail=True))
    yield case('flip allocation changes geometry negative',0x4b99d0,flip_setup(3,5,8,allocation_shape=(0,0)))
    yield case('flip allocation changes geometry narrow',0x4b99d0,flip_setup(7,9,12,allocation_shape=(3,2)))
    for w,h,bd,cd,pal,td,lock in ((2,2,8,8,0,8,0),(2,2,24,24,0,24,0),(2,2,4,8,0,8,0),(2,2,8,24,0,24,0),(2,2,24,8,0,8,0),(2,2,24,8,1,8,0),(2,2,8,16,0,0,0),(2,2,8,8,0,8,0x80004005)):
        yield case(f'bitmap {w} {h} {bd} {cd} {pal} {td} {lock}',0x4bdda0,bitmap_setup(w,h,bd,cd,pal,td,lock),(lambda t:t['context'],lambda t:t['bmp'],0x13572468))
    for shifts in ((0,0,0,0,0),(3,2,3,11,5),(32,33,34,35,36)):
        for data,width,height in (([0],1,1),([0x81],2,1),([0x82,0x81],4,1),([1,0x31],2,1),([3,0x27,0xfe,0x80],4,1),([0x82,1,9],2,2),([0],1,0),([0],1,-1)):
            yield case(f'rle {data} w{width} h{height} shifts{shifts}',0x4bfd80,rle_setup(data,width,height,shifts),(lambda t:t['source'],))
    for result in (0,1,0x87654321):
        for tail in (False,True):yield case(f'create result{result} oldtail{tail}',0x4bc740,create_setup(result,tail),(0x1234,0x5678,0x9abc))
    for gate in (0,1,0x12345678):
        yield case(f'header gate{gate}',0x4b7550,archive_setup(gate))
    yield case('compact disabled',0x4b76b0,archive_setup(1,True))
    for path in (b'a.rez',b'C:\\CLAW\\CLAW.REZ',b'D:\\Games\\test-long-name.rez'):
        for close in (0,1):
            yield case(f'compact archive {path} close{close}',0x4b76b0,archive_setup(0,True,path,close))
    for which in ('width','height'):
        def mismatch(env,which=which):
            t=bitmap_setup(2,2,8,8,0)(env)
            env.put(t['self']+(0x18 if which=='width' else 0x14),3)
            return t
        yield case(f'bitmap {which} mismatch',0x4bdda0,mismatch,(lambda t:t['context'],lambda t:t['bmp'],0x54321))
    for bd,cd,pal,td,lock in ((24,16,0,32,0),(8,24,0,24,0x80004005),(24,8,1,8,0x80004005)):
        yield case(f'bitmap conversion outcome {bd} {cd} {pal} {td} {lock}',0x4bdda0,bitmap_setup(2,2,bd,cd,pal,td,lock),(lambda t:t['context'],lambda t:t['bmp'],0x13579))
    for token,receiver_token,width in ((0,1,1),(0x81,0x84,5),(1,2,3)):
        def differing_source(env,token=token,receiver_token=receiver_token,width=width):
            t=rle_setup([token,0x27,0x38,0x49],width,1,(3,2,3,11,5))(env)
            src=env.object(16,'receiver-count-source',data=bytes([receiver_token,0x71,0x72,0x73]))
            env.put(t['self']+0xc,src)
            return t
        yield case(f'RLE argument token {token} receiver token {receiver_token}',0x4bfd80,differing_source,(lambda t:t['source'],))
