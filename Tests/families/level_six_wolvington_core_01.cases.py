"""Original-only Wolvington cases with concrete resource and actor graphs."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate

ANIMS = (0x52e074,0x52e054,0x52e038,0x52e020,0x52e008,0x52dff0,0x52dfd4,0x52dfbc,0x52dfa0,0x52df84,0x52df6c,0x52df54)

def table(env, at, lo, values, stride=4):
    buf=env.object(max(4,len(values)*stride),'table cells',fill=0)
    for i,v in enumerate(values): env.put(buf+i*stride,v)
    fallback=env.object(4,'fallback',words=[0])
    env.put(at,0,0,lo,lo+len(values)-1,buf,fallback,stride,0,0)
    return buf

def resources(env, entries):
    root=env.object(0x40,'resource map',fill=0)
    bucket=env.object(4,'resource bucket',words=[0])
    tail=0
    for key,value in entries:
        tail=env.object(16,'resource node',words=[tail,0,key,value])
    env.put(bucket,tail)
    env.put(root+0x14,bucket,1)
    return root

def graph(env, fill=0x6b):
    actor=env.object(0x478,'Wolvington',fill=fill)
    parent=env.object(0x200,'parent',fill=0)
    logic=env.object(0x200,'logic',fill=0)
    world=env.object(0x80,'world',fill=0)
    spatial=env.object(0x200,'spatial',fill=0)
    empty=resources(env,[])
    env.put(world+0x10,empty,empty)
    env.put(world+0x24,spatial,empty,empty)
    env.put(parent+0xc,world)
    env.put(parent+0x6c,logic)
    env.put(parent+0x118,0x80000000)
    env.put(actor+0xc,parent,logic)
    env.put(actor+0x128,parent,parent)
    env.write(0x534938,b'\0')
    env.put(0x52f01c,1)
    env.put(0x534eac,0x26b7)
    env.put(0x541334,1)
    env.write(0x537668,b'\0'*0x2c)
    table(env,0x537698,0,[0x523210]*64)
    def decrement(e,c):
        value=(e.get(c.arguments[0])-1)&0xffffffff
        e.put(c.arguments[0],value)
        return value
    env.override(0x5469e8,decrement)
    return dict(actor=actor,parent=parent,logic=logic,world=world)

def recorder(env, name, argc, journal, value=0):
    def effect(e,c):
        n=e.get(journal)
        e.put(journal+4+n*24,c.receiver,len(c.arguments),*(tuple(c.arguments)+(0,)*4)[:4])
        e.put(journal,n+1)
        return value
    return env.stub(name,'thiscall',argc,effect)

def constructor(mask, factors, fill, factory=False, fallback=False, image=False):
    def setup(env):
        t=graph(env,fill); a=t['actor'];p=t['parent'];w=t['world']
        entries=[]
        for i,key in enumerate(ANIMS):
            if mask>>i&1:
                animation=env.object(0x30,'animation',fill=0)
                frame=env.object(0x20,'frame',fill=0)
                env.put(frame+0x1c,17+i)
                frames=env.object(4,'frame array',words=[frame])
                env.put(animation+0xc,frames,1)
                entries.append((key,animation))
        if fallback:
            frame=env.object(0x20,'fallback frame',fill=0)
            env.put(frame+0x1c,0x123456)
            frames=env.object(4,'fallback frames',words=[frame])
            animation=env.object(0x30,'fallback animation',fill=0)
            env.put(animation+0xc,frames,1)
            entries.append((0x5234b4,animation))
        if image:
            frame=env.object(0x40,'image frame',fill=0x35)
            frames=env.object(4,'image frames',words=[frame])
            picture=env.object(0x70,'image',fill=0)
            env.put(picture+0x14,frames)
            env.put(w+0x10,resources(env,[(0x52e090,picture)]))
        env.put(w+0x2c,resources(env,entries))
        sounds=[]
        for i,key in enumerate((0x524098,0x52df38,0x52df1c,0x52df00,0x52def0,0x52ded4)):
            sounds.append((key,env.object(0x80,'sound handle '+str(i),fill=0x30+i)))
        env.put(w+0x28,resources(env,sounds))
        env.put(p+0x164,0x6ab3)
        for at,v in zip((0x5262b8,0x50ff20,0x5262b4,0x5262b0),factors):env.write(at,struct.pack('<f',v))
        if factory:
            env.put(t['logic']+0x1c,0)
            journal=env.object(1024,'publication journal',fill=0)
            vt=env.object(0x24,'factory virtual methods',fill=0)
            def startup(e,c):
                e.put(journal+800,c.receiver,e.get(t['logic']+0x18),e.get(t['logic']+0x1c),e.get(c.receiver+0x2e4),e.get(c.receiver+0x350))
                return 0
            cb=env.stub('constructed startup','thiscall',0,startup)
            env.put(vt+0x10,cb)
            def new(e,c):
                b=e.object(c.arguments[0],'factory actor',fill=fill)
                e.put(journal+1000,b)
                return b
            env.override(0x4f63ec,new)
            def rect(e,c):
                e.put(c.arguments[0],*c.arguments[1:])
                b=e.get(journal+1000)
                if b:e.put(b,vt)
                return 1
            env.override(0x546d5c,rect)
        return t
    return setup

def destructor(capacity, refs, fill):
    def setup(env):
        t=graph(env,fill);a=t['actor']
        env.put(a+0x2fc,capacity)
        if capacity>32:env.put(a+0x300,env.object(32,'bitset storage',fill=0x91))
        for off,ref in zip((0x1a4,0x1a8),refs):
            if ref is None:ptr=env.get(0x52e1c8)+12
            else:
                ptr=env.object(32,'CString header and payload',words=[ref,8,8],fill=0x71)+12
            env.put(a+off,ptr)
        return t
    return setup

def dispatch(index,lo,hi,callback,fill,stride=4):
    def setup(env):
        t=graph(env,fill)
        log=env.object(2048,'dispatch journal',fill=0)
        cb=recorder(env,'state callback',0,log,0x76543210)
        table(env,0x53ec68,lo,[cb if callback else 0]*(hi-lo+1),stride)
        table(env,0x5349b8,index,[cb])
        env.put(0x53ec88,0x99112233)
        return t
    return setup

def logic_case(state,fill,fail=False):
    def setup(env):
        t=graph(env,fill);a=t['actor'];l=t['logic']
        env.put(l+0x18,a,state)
        env.put(a+0x10,l)
        log=env.object(2048,'virtual journal',fill=0)
        vt=env.object(0x24,'virtual methods',fill=0)
        for off in (4,8,12,16,28,32):env.put(vt+off,recorder(env,'virtual '+str(off),1 if off in (4,8,12) else 0,log))
        env.put(a,vt)
        text=env.object(32,'state CString',words=[1,10,10],data=b'')
        env.write(text+12,b'LS_HITHIGH\0')
        table(env,0x537698,state,[text+12])
        if fail:env.override(0x4f63ec,allocate(fail=True))
        return t
    return setup

def reaction(orientation,facing,enabled,action,rangestate,threshold,count,rand,fill):
    def setup(env):
        t=graph(env,fill);a=t['actor'];p=t['parent']
        env.write(a+0x68,struct.pack('<d',0.0))
        player=env.object(0x80,'player',fill=0)
        pl=env.object(0x20,'player logic',fill=0)
        status=env.object(0x40,'player status',fill=0)
        env.put(player+0x4c,1 if orientation==2 else 0xffffffff,20)
        env.put(player+0x6c,pl);env.put(pl+0x14,status)
        env.put(status,facing,enabled);env.put(status+0x3c,action)
        env.put(0x537e88,player)
        env.put(a+0x184,rangestate,0,orientation)
        env.put(a+0x2e4,threshold)
        env.put(a+0x20,count)
        env.put(a+0x2fc,32,2)
        env.put(p+8,0x10);env.put(p+0x80,0)
        env.override(0x4a3050,lambda e,c:rand)
        return t
    return setup

def leave(name,cleanup,fill):
    def setup(env):
        t=graph(env,fill);a=t['actor'];l=t['logic']
        env.put(l+0x1c,12)
        env.put(a+0x18c,2)
        env.put(t['parent']+0x40,2)
        env.put(a+0x30c,0)
        table(env,0x537698,12,[name])
        if cleanup:
            buf=env.object(cleanup*4,'cleanup cells',fill=0x7d)
            env.put(0x5376b4,buf,cleanup)
        env.override(0x4a3050,lambda e,c:0xfffffffd)
        return t
    return setup

def changing_dispatch(lower):
    def setup(env):
        index=9 if lower else 21
        t=dispatch(index,10,20,True,0x69)(env)
        log=env.object(512,'reentrant journal',fill=0)
        cb=recorder(env,'reloaded state callback',0,log)
        def realloc(e,c):
            old,size=c.arguments
            oldsize=max(0,(e.get(0x53ec74)-e.get(0x53ec70)+1))*e.get(0x53ec80)
            data=e.read(old,min(size,oldsize)) if old and oldsize and size else b''
            result=e.object(max(4,size),'changed table',fill=0)
            if data:e.write(result,data)
            e.put(result,cb)
            if old:e.release(old)
            # The allocator changes table metadata before the owned code's
            # second lookup. Zero-width entries retain the callback word.
            e.put(0x53ec80,0)
            if lower:e.put(0x53ec74,index-1)
            else:e.put(0x53ec70,index+1)
            return result
        env.override(0x4a9070,realloc)
        return t
    return setup

def growing_leave(step,fill):
    def setup(env):
        t=leave(0x5234ec,0,fill)(env)
        table(env,0x537698,10,[0x5234ec,0x5234ec])
        key=9 if step<0 else 12
        env.put(t['logic']+0x1c,key)
        def realloc(e,c):
            old,size=c.arguments
            lo=e.get(0x5376a0);hi=e.get(0x5376a4)
            count=(hi-lo+1)&0xffffffff
            data=e.read(old,count*4) if old and count else b''
            result=e.object(max(4,size),'state growth',fill=0)
            e.write(result,data[:size])
            if old:e.release(old)
            state=e.get(t['logic']+0x1c)
            e.put(t['logic']+0x1c,(state+step)&0xffffffff)
            return result
        env.override(0x4a9070,realloc)
        return t
    return setup

def constructor_sensitivity(mode,poison):
    def setup(env):
        t=constructor(0,(1.25,100.0,0.875,1.125),0x73)(env)
        a=t['actor'];p=t['parent'];w=t['world']
        if mode=='lookup output reset':
            # A successful first output lookup followed by a missing second
            # output must not retain the first handle in the automatic slot.
            handle=env.object(0x80,'first output handle',fill=0x47)
            env.put(w+0x28,resources(env,[(0x52df38,handle)]))
        if mode=='image observes published vtable':
            picture=env.object(0x70,'image with live frame-pointer array',fill=0)
            # The image's one frame-pointer cell aliases the actor's first
            # word, so image selection observes the current publication order.
            env.put(picture+0x14,a)
            env.put(w+0x10,resources(env,[(0x52e090,picture)]))
        alternate=env.object(0x200,'separate render parent',fill=0)
        def rect(e,c):
            e.put(c.arguments[0],*c.arguments[1:])
            if e.get(a)==0x50ff2c and c.arguments[0]==a+0x260:
                # Physical services may reenter or update shared actor data.
                # The owned scalar initialization must replace these values,
                # even when the original base constructor used identical ones.
                for i,off in enumerate((0x2b8,0x2bc,0x2c0,0x2c4,0x2c8,0x28c,0x290,0x294,0x298,0x29c,0x2a0,0x2a4,0x2a8,0x2ac,0x2b0)):
                    e.put(a+off,(poison+i*0x193)&0xffffffff)
                if mode=='separate render aliases':
                    e.write(alternate,e.read(p,0x200))
                    e.put(alternate+0x164,0xa5a5a5a5)
                    e.put(a+0x128,alternate)
            return 1
        env.override(0x546d5c,rect)
        return t
    return setup

def cases(random_source):
    recv=lambda t:t['actor']
    for mask in (0,4095,*[1<<i for i in range(12)]):
        yield Case('constructor animations '+str(mask),0x49fbf0,constructor(mask,(1.25,100.0,1.25,0.75),random_source.randrange(1,256)),receiver=recv,arguments=(lambda t:t['parent'],))
    for factor in (-2.0,0.0,0.99,1.0,1.01,123.25):
        yield Case('constructor float '+str(factor),0x49fbf0,constructor(0,(factor,100.0,-0.125,1.125),0x85),receiver=recv,arguments=(lambda t:t['parent'],))
    yield Case('factory constructs and publishes',0x49fb30,constructor(0,(1.0,100.0,1.0,1.0),0x83,True),arguments=(lambda t:t['parent'],))
    for state in (1,28,29,30,31,999,1000,1001,0xffffffff):
        yield Case('factory state '+str(state),0x49fb30,logic_case(state,random_source.randrange(1,256)),arguments=(lambda t:t['parent'],))
    for capacity in (0,1,32,33,128):
        for refs in ((None,None),(1,1),(2,3),(None,1),(1,None)):
            yield Case('destroy '+str((capacity,refs)),0x4a0160,destructor(capacity,refs,0x8b),receiver=recv)
    for flags in (0,1,2,3,0x100,0x101,0xfffffffe,0xffffffff):
        yield Case('deleting destructor '+str(flags),0x4a0140,destructor(33,(1,2),0x91),receiver=recv,arguments=(flags,))
    for lo,hi in ((-3,3),(10,20)):
        for index in (lo-2,lo-1,lo,lo+1,hi,hi+1,hi+2):
            for callback in (False,True):
                yield Case('dispatch '+str((lo,hi,index,callback)),0x4a0230,dispatch(index,lo,hi,callback,0x79),receiver=recv,arguments=(index,))
    for orientation in (2,3):
        for facing in (0,1):
            for enabled in (0,1):
                for action in (0,1,2,3,4,5,6,7,8,9,0xffffffff):
                    yield Case('reaction classify '+str((orientation,facing,enabled,action)),0x4a0740,reaction(orientation,facing,enabled,action,3,50,2,25,0x8f),receiver=recv,arguments=(0x52720c,))
    for state in (0,2,3,4,5,6):
        for rand,threshold,count in ((0,1,2),(49,50,2),(50,50,2),(99,100,1),(100,1,2),(0xffffffff,0,2),(0x80000000,0,3),(0x7fffffff,99,2),(0,1,0xffffffff)):
            yield Case('reaction probability '+str((state,rand,threshold,count)),0x4a0740,reaction(3,1,1,7,state,threshold,count,rand,random_source.randrange(1,256)),receiver=recv,arguments=(0x52720c,))
    for name in (0x523210,0x523204,0x5240e8,0x5234ec):
        for cleanup in (0,1,3):
            yield Case('leave '+str((name,cleanup)),0x4a0800,leave(name,cleanup,0x67),receiver=recv)

    for lower in (False,True):
        yield Case('dispatch second growth '+str(lower),0x4a0230,changing_dispatch(lower),receiver=recv,arguments=(9 if lower else 21,))
    for step in (-2,-1,1,2):
        yield Case('leave repeated state growth '+str(step),0x4a0800,growing_leave(step,0x71),receiver=recv)

    for mask in (0,1,16,0x555,0xaaa,4095):
        for image in (False,True):
            yield Case('constructor fallback '+str((mask,image)),0x49fbf0,constructor(mask,(1.01,100.0,1.37,-0.25),random_source.randrange(1,256),fallback=True,image=image),receiver=recv,arguments=(lambda t:t['parent'],))

    for mode in ('lookup output reset','image observes published vtable','separate render aliases'):
        for _ in range(4):
            poison=random_source.randrange(0x10000000,0x70000000)
            yield Case('constructor sensitivity '+mode+' '+hex(poison),0x49fbf0,constructor_sensitivity(mode,poison),receiver=recv,arguments=(lambda t:t['parent'],))
