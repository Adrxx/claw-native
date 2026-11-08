"""Original-only behavioral inputs for break and single plank state machines."""
from clawparity.cases import Case
from clawparity.fixtures import allocate


def words(env, size, name, salt=0x13579bdf):
    return env.object(size, name, words=[(salt + i * 0x1020305) & 0xffffffff for i in range(size // 4)])


def graph(env, salt=0x13579bdf):
    r = words(env, 0xa4, 'state', salt)
    a = env.object(0x1b4, 'actor', fill=0)
    d = words(env, 0x174, 'logic data', salt ^ 0x62914bae)
    w = env.object(0x40, 'world', fill=0)
    l = env.object(0x60, 'level', fill=0)
    g = env.object(0x94, 'grid', fill=0)
    tiles = words(env, 4096, 'tile words', salt ^ 0xabcde)
    rows = env.object(256, 'row offsets', words=[i * 32 for i in range(64)])
    c = env.object(0xb0, 'config', fill=0)
    env.put(0x537960, c)
    env.put(c + 0xa8, 17, 0)
    env.put(d + 0xc, w)
    env.put(w + 0x24, l)
    env.put(l + 0x5c, g)
    env.put(g + 0x20, tiles, rows)
    env.put(g + 0x8c, 0, 0)
    env.put(r + 0xc, a, d)
    env.put(r + 0x2c, a, d)
    env.put(r + 0x48, 0, 0, 0, 0, 0x1234, 0x718293a4, 0x55667788, 0x8abcdef0, 0)
    env.put(a + 0x6c, d)
    env.put(a + 0xc, w)
    env.put(a + 0x4c, 5, 7)
    env.put(a + 0x40, salt | 1)
    env.put(a + 0x188 + 4, a, 0)
    env.put(d + 0x1c, salt)
    env.put(0x537668 + 0x18, 0)
    env.put(0x537210, 0xfedcba98)
    env.put(0x5430c4, 0)
    return dict(r=r, a=a, d=d, w=w, l=l, g=g, tiles=tiles, rows=rows, c=c)


def maps(env, t):
    # Empty hash maps are real resource lookup inputs, with a nonzero divisor.
    for off in (0x10, 0x14, 0x2c):
        manager = env.object(0x40, 'resource manager', fill=0)
        env.put(manager + 0x18, 1)
        env.put(t['w'] + off, manager)


def recording(env, name, argc, record, tag):
    def effect(e, call):
        n = e.get(record)
        e.put(record + 4 + n * 20, tag, call.receiver, *(list(call.arguments) + [0] * (3 - argc)))
        e.put(record, n + 1)
        return tag ^ 0xa5a5
    return env.stub(name, 'thiscall', argc, effect)


def state_case(label, f, setup):
    return Case(label, f, setup, receiver=lambda t:t['r'])


def dispatch_setup(base, low, high, index, stride, null=False, expand_again=False):
    def setup(env):
        r = env.object(0xa4, 'dispatch receiver', fill=0)
        log = env.object(128, 'callback log', fill=0)
        cb = recording(env, 'dispatch callback', 0, log, 0x9834)
        table = env.object((high-low+1)*stride, 'dispatch slots', fill=0)
        for i in range(high-low+1):
            env.put(table + i*stride, 0 if null else cb)
        fallback = env.object(4, 'fallback', words=[cb])
        error = env.object(16, 'error sink', words=[0,0,0,4])
        env.put(base+4, error, low, high, table, fallback, stride, 0, 0xabcdef)
        # RTTI graph accepted by the real type_info resolver.
        vt = env.object(40, 'vtable with preceding metadata', fill=0)
        meta = env.object(20, 'RTTI metadata', fill=0)
        desc = env.object(24, 'type descriptor', data=b'\x00'*8+b'.?AVPlank@@\x00')
        env.put(vt, meta)
        env.put(meta+0xc, desc)
        env.put(r, vt+4)
        if expand_again:
            def realloc(e, call):
                n = e.calls_so_far(0x4a9070)
                # First growth leaves the requested slot just before its base,
                # then the second growth uses a changed zero-width registry.
                buf = e.object(128, 'growth callback storage', fill=0)
                e.put(buf, cb, cb, cb, cb)
                if n == 1:
                    e.put(base+8, index+1, index)
                else:
                    e.put(base+8, index+1, index+1)
                    e.put(base+0x18, 0)
                return buf+4
            env.override(0x4a9070, realloc)
        return dict(r=r)
    return setup


def cases(random_source):
    salts = [random_source.getrandbits(32) for _ in range(4)]
    for f, base in ((0x40fb30,0x534a10),(0x4890f0,0x53c2c8)):
        for low, high, index in ((-2,2,-2),(-2,2,0),(-2,2,2),(1,2,0),(1,2,3)):
            for stride in (4,12):
                for null in (False,True):
                    yield Case(f'dispatch {f:x} {low} {high} {index} {stride} {null}', f,
                               dispatch_setup(base,low,high,index,stride,null),receiver=lambda t:t['r'],arguments=(index,))
        yield Case(f'dispatch second growth {f:x}', f,dispatch_setup(base,0,0,2,4,expand_again=True),receiver=lambda t:t['r'],arguments=(2,))
    for f in (0x4894b0,0x4895b0,0x489640):
        for salt in salts:
            for armed in (0,1,0xffffffff):
                def setup(env,salt=salt,armed=armed):
                    t=graph(env,salt); env.put(t['r']+0x68,armed);return t
                yield state_case(f'entry {f:x} {salt:x} {armed}',f,setup)
    for mode in (0,1,2,3,0xffffffff):
        for bottom,left,right in ((15,11,19),(10,11,19),(20,11,19),(9,11,19),(21,11,19),(15,10,19),(15,9,19),(15,11,20),(15,11,21)):
            def setup(env,mode=mode,bottom=bottom,left=left,right=right):
                t=graph(env,salts[0]); p=env.object(0x128,'player',fill=0)
                env.put(0x537e88,p);env.put(p+0xcc,mode)
                env.put(t['a']+0x4c,0,0);env.put(t['a']+0x118,10,10,20,20)
                env.put(p+0x118,left,0,right,bottom)
                return t
            yield state_case(f'player {mode} {bottom} {left} {right}',0x489530,setup)
    for now,start,delay in ((10,0,11),(10,0,10),(10,0,9),(0,0,0),(1,0xffffffff,2),(0,1,0xffffffff),(0,1,0x80000000)):
        for links in ('none','next','previous','both','same','self'):
            def setup(env,now=now,start=start,delay=delay,links=links):
                t=graph(env,salts[1]); n=graph(env,salts[2]);p=graph(env,salts[3])
                env.put(0x537210,now);env.put(t['r']+0x60,start,delay)
                a=n['r'] if links in ('next','both','same') else t['r'] if links=='self' else 0
                b=p['r'] if links in ('previous','both') else n['r'] if links=='same' else t['r'] if links=='self' else 0
                env.put(t['r']+0x50,a,b)
                return t
            yield state_case(f'wait {now} {start} {delay} {links}',0x489600,setup)
    for start,end in ((0,4),(-4,-1),(-3,0),(0x7fffffff,2),(-0x80000000,-1)):
        for delta in (0,1):
            for hide,stop in ((0,0),(1,0),(1,1)):
                def setup(env,start=start,end=end,delta=delta,hide=hide,stop=stop):
                    t=graph(env,salts[2]);s=env.object(0x6c,'sprite descriptor',fill=0)
                    env.put(s+0x64,start,end);env.put(t['a']+0x170,s)
                    total=(start+end)&0xffffffff; total=total if total<0x80000000 else total-0x100000000
                    mid=abs(total)//2*(1 if total>=0 else -1)
                    env.put(t['a']+0x16c,mid+delta)
                    env.put(t['a']+0x1a4,hide);env.put(t['a']+0x19c,stop)
                    return t
                yield state_case(f'crumble {start} {end} {delta} {hide} {stop}',0x489680,setup)
    for count in (0,1,3):
        for changed in (False,True):
            for f in (0x40fe20,0x40fde0):
                def setup(env,count=count,changed=changed):
                    t=graph(env,salts[0]);p=env.object(0x70,'player',fill=0);pd=env.object(0x18,'player data',fill=0);cp=env.object(0x84,'checkpoint',fill=0)
                    env.put(0x537e88,p);env.put(p+0x6c,pd);env.put(pd+0x14,cp);env.put(cp+0x80,0x83726150)
                    env.put(t['r']+0x9c,0x83726150-int(changed));env.put(t['r']+0xa0,0)
                    previous=0
                    for j in range(count):
                        n=graph(env,salts[j%4]);env.put(n['a']+0x4c,j+1,j+2);env.put(n['r']+0x50,previous);previous=n['r']
                    env.put(t['r']+0xa0,previous)
                    return t
                yield state_case(f'reset {f:x} {count} {changed}',f,setup)
    for state in (1,28,29,30,31,999,1000,0xffffffff):
        def setup(env,state=state):
            t=graph(env,salts[0]);env.put(t['d']+0x1c,state);env.put(t['d']+0x18,t['r'])
            log=env.object(256,'logic callback log',fill=0);vt=env.object(36,'logic vtable',fill=0);env.put(t['r'],vt)
            for off,argc in ((4,1),(8,1),(12,1),(16,0),(28,0),(32,0)):
                env.put(vt+off,recording(env,f'logic {off}',argc,log,off))
            if state not in (29,30,1000):
                string=env.object(32,'CString',words=[1,4,8],data=b'\x01\x00\x00\x00\x04\x00\x00\x00\x08\x00\x00\x00idle\x00')
                slot=env.object(4,'CString slot',words=[string+12]);env.put(0x537698+8,state,state,slot,0,4,0,0)
            return t
        yield Case(f'logic state {state}',0x488e30,setup,arguments=(lambda t:t['a'],))
    for depth in (0,1,0xffffffff):
        def setup(env,depth=depth):
            t=graph(env,salts[1]);maps(env,t);env.put(t['a']+0x64,depth);return t
        yield Case(f'single construct depth {depth}',0x488ef0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['a'],))
    for depth in (0,1):
        def setup(env,depth=depth):
            t=graph(env,salts[2]);maps(env,t);env.put(t['d']+0x1c,0);env.put(t['a']+0x64,depth)
            return t
        yield Case(f'logic creates state depth {depth}',0x488e30,setup,arguments=(lambda t:t['a'],))
    for count in (-1,0,1,2,4):
        for depth in (0,7):
            def setup(env,count=count,depth=depth):
                t=graph(env,salts[0]);maps(env,t);env.put(t['a']+0x64,depth)
                env.put(t['d']+0xb8,0x12789456);env.put(t['d']+0xc8,count)
                p=env.object(0x70,'player',fill=0);pd=env.object(0x18,'player data',fill=0);cp=env.object(0x84,'checkpoint',fill=0)
                env.put(0x537e88,p);env.put(p+0x6c,pd);env.put(pd+0x14,cp);env.put(cp+0x80,0x839abdef)
                factory=env.object(0x30,'actor factory',fill=0);env.put(factory+0xc,t['w']);env.put(t['w']+8,factory)
                free=env.object(12*8,'factory list free nodes',fill=0)
                for j in range(7):env.put(free+12*j,free+12*(j+1))
                env.put(factory+0x20,free)
                log=env.object(512,'child initialization observations',fill=0)
                def initialize(e,call):
                    child=call.arguments[0];n=e.get(log);cd=e.get(child+0x6c)
                    e.put(log+4+n*32,child,call.receiver,e.get(child+0x4c),e.get(child+0x50),e.get(child+0x64),e.get(t['r']+0xa0),e.get(t['d']+0x1c),e.get(t['r']+0x9c))
                    e.put(log,n+1)
                    replacement=e.object(0x174,'post callback child logic',fill=0)
                    state=words(e,0x6c,'child state',0x51920384+n*0x112233)
                    e.put(state+0xc,child,replacement);e.put(state+0x2c,child,replacement)
                    e.put(replacement+0xc,t['w']);e.put(replacement+0x18,state)
                    e.put(child+0x6c,replacement)
                    return 0x98765432
                callback=env.stub('SinglePlank factory initializer','cdecl',1,initialize)
                descriptor=env.object(0x20,'SinglePlank logic resource',fill=0);env.put(descriptor+8,0);env.put(descriptor+0x10,callback)
                name=env.object(12,'SinglePlank key',data=b'SinglePlank\x00')
                bucket=env.object(16,'SinglePlank hash node',words=[0,0,name,descriptor]);table=env.object(4,'resource buckets',words=[bucket])
                manager=env.get(t['w']+0x14);env.put(manager+0x14,table,1)
                return t
            yield Case(f'break construct count {count} depth {depth}',0x40f870,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['a'],))
    # Nonnull, silent animations make both their assignment and their timing
    # visible. A stop command keeps them independent of sound platform APIs.
    for f in (0x4894b0,0x489640):
        for duration in (0,1,17,0x80000000):
            def setup(env,duration=duration):
                t=graph(env,salts[3])
                for off,tag in ((0x48,0x318795),(0x4c,0x957813)):
                    frame=env.object(0x30,'silent animation frame',fill=0)
                    env.put(frame+0xc,9);env.put(frame+0x18,duration,tag)
                    frames=env.object(4,'animation frame array',words=[frame])
                    anim=env.object(0x14,'animation resource',fill=0);env.put(anim+0xc,frames,1)
                    env.put(t['r']+off,anim)
                env.put(t['a']+0x190,env.get(t['r']+0x48))
                env.put(0x5430c4,duration)
                return t
            yield state_case(f'animation state {f:x} duration {duration}',f,setup)
    for sx,sy,x,y,adjust in ((1,2,-11,-19,3),(33,34,11,-19,3),(0,0,-2,-3,1),(31,31,-1,-1,0),(32,32,7,9,-8)):
        for f in (0x488ef0,0x489680,0x40fe20):
            def setup(env,sx=sx,sy=sy,x=x,y=y,adjust=adjust,f=f):
                t=graph(env,salts[0]);maps(env,t)
                env.put(t['g']+0x20,t['tiles']+2048,t['rows']+128)
                for j in range(64):env.put(t['rows']+4*j,(j-32)*16)
                env.put(t['g']+0x8c,sx,sy);env.put(t['a']+0x4c,x,y);env.put(t['c']+0xac,adjust)
                sprite=env.object(0x6c,'midpoint sprite',fill=0);env.put(sprite+0x64,0,0)
                env.put(t['a']+0x16c,0,sprite)
                if f==0x40fe20:
                    env.put(t['r']+0xa0,t['r']);env.put(t['r']+0x50,0)
                return t
            yield Case(f'signed tiles {f:x} {sx} {sy} {x} {y} {adjust}',f,setup,receiver=lambda t:t['r'],arguments=((lambda t:t['a']),) if f==0x488ef0 else ())


def map_entry(env, manager, key, value):
    table=env.get(manager+0x14)
    if not table:
        table=env.object(4,'resource bucket',fill=0)
        env.put(manager+0x14,table,1)
    name=env.object(len(key)+1,'resource key',data=key.encode()+b'\x00')
    node=env.object(16,'resource node',words=[env.get(table),0,name,value])
    env.put(table,node)


def state_name(env, name, value):
    key=env.object(len(name)+1,'state name',data=name.encode()+b'\x00')
    node=env.object(20,'state trie leaf',fill=0)
    env.put(node,node,node,0,key,value)
    env.put(0x537668+0x18,node)


def animation(env, tag, moving=False):
    frames=[]
    for j in range(2):
        frame=env.object(0x30,'silent effect frame',fill=0)
        env.put(frame+0xc,0 if moving else 9)
        env.put(frame+0x10,2 if moving else 0)
        env.put(frame+0x18,0,tag+j)
        env.put(frame+0x20,3+j*4,5+j*6)
        frames.append(frame)
    table=env.object(8,'effect frame table',words=frames)
    anim=env.object(0x14,'effect animation',fill=0);env.put(anim+0xc,table,2)
    return anim


def behavior_cases(random_source):
    salt=random_source.getrandbits(32)
    for f,name in ((0x4894b0,'LS_IDLE'),(0x4895b0,'LS_WAIT'),(0x489640,'LS_CRUMBLE')):
        for tag in (0x3456789,0x87abcdef):
            def setup(env,f=f,name=name,tag=tag):
                t=graph(env,salt);state_name(env,name,tag)
                env.put(t['r']+0x68,0)
                env.put(t['r']+0x48,animation(env,0x74589,True),animation(env,0x87549,True))
                env.put(t['a']+0x190,animation(env,0xabc89))
                env.put(t['a']+0x8,0x168200a4)
                env.put(t['a']+0x40,0x76a98537)
                env.put(t['d']+0x1c,0x23456789)
                return t
            yield state_case(f'nonzero state lookup {f:x} {tag:x}',f,setup)
    for available in (0,1,2,3):
        for depth in (0,9):
            def setup(env,available=available,depth=depth):
                t=graph(env,salt);maps(env,t);state_name(env,'LS_IDLE',0x738291ab)
                env.put(t['a']+0x64,depth);env.put(t['a']+8,0x152684a0)
                for bit,key in ((1,'LEVEL_BREAKPLANK_CRUMBLE'),(2,'LEVEL_BREAKPLANK_IDLE')):
                    if available&bit:
                        map_entry(env,env.get(t['w']+0x2c),key,animation(env,0x784512+bit,True))
                for key,tag in (('LogicHit',0x63748291),('LogicAttack',0xa9b8c7d6)):
                    descriptor=env.object(0x14,'collision logic resource',fill=0)
                    env.put(descriptor+0x10,tag)
                    map_entry(env,env.get(t['w']+0x14),key,descriptor)
                sprite=env.object(0x6c,'constructor sprite',fill=0)
                frame=env.object(0x28,'sprite bounds',fill=0);env.put(frame+0x18,7,11,13,17)
                frames=env.object(12,'sprite frame table',words=[frame,frame,frame])
                env.put(sprite+0x14,frames);env.put(sprite+0x64,1,2)
                map_entry(env,env.get(t['w']+0x10),'LEVEL_BREAKPLANK',sprite)
                return t
            yield Case(f'constructor resources {available} depth {depth}',0x488ef0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['a'],))
    for y in (-200,317):
        for mode in (1,2):
            def setup(env,y=y,mode=mode):
                t=graph(env,salt);state_name(env,'LS_WAIT',0x9876543)
                p=env.object(0x128,'offset player',fill=0);env.put(0x537e88,p)
                env.put(t['a']+0x4c,500,y,0x3478192)
                env.put(t['a']+0x118,-50,-10,60,30)
                env.put(p+0x4c,504,y+2);env.put(p+0xcc,mode)
                env.put(p+0x118,-7,-9,8,11)
                return t
            yield state_case(f'independent player y {y} mode {mode}',0x489530,setup)
    for a4,a8 in ((0,1),(1,0),(0xffffffff,0),(0,0xffffffff)):
        for active in (False,True):
            def setup(env,a4=a4,a8=a8,active=active):
                t=graph(env,salt)
                env.put(t['a']+0x1a4,a4,a8)
                if active:
                    anim=animation(env,0x784592,True)
                    env.put(t['a']+0x190,anim)
                    env.put(t['a']+0x194,env.get(env.get(anim+0xc)))
                    env.put(t['a']+0x1a4,a4,a8)
                    env.put(t['a']+0x1b0,0x3f800000)
                sprite=env.object(0x6c,'distinct sprite',fill=0);env.put(sprite+0x64,0,4)
                env.put(t['a']+0x16c,1,sprite)
                return t
            yield state_case(f'independent animation flags {a4} {a8} {active}',0x489680,setup)

    for redirect in (False,True):
        def setup(env,redirect=redirect):
            t=graph(env,salt);other=graph(env,salt ^ 0x98765432)
            state_name(env,'LS_IDLE',0x67382910)
            block=env.object(0x240,'receiver and animation owner alias',fill=0)
            r=block+0x40;env.write(r,env.read(t['r'],0xa4));t['r']=r
            old=animation(env,0x593817,False)
            frame=env.get(env.get(old+0xc))
            env.put(frame+0x10,3)
            env.put(frame+0x20,other['a'] if redirect else t['a'],other['d'])
            env.put(t['r']+0x4c,old)
            env.put(t['a']+0x18c,r-0x20)
            env.put(t['a']+0x190,animation(env,0x81819))
            env.put(t['a']+0x40,0x12345679)
            env.put(other['a']+0x40,0x98765433)
            new=animation(env,0x547821,True)
            env.put(other['a']+0x190,new,env.get(env.get(new+0xc)))
            env.put(other['a']+0x1b0,0x3f800000)
            return t
        yield state_case(f'idle reloads actor after animation redirect {redirect}',0x4894b0,setup)


base_cases=cases

def cases(random_source):
    yield from base_cases(random_source)
    yield from behavior_cases(random_source)
