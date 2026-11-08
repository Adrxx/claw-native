"""Parrot core cases built from the original instruction boundaries."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence, reallocate


def f64(env, at, value):
    env.write(at, struct.pack('<d', value))


def common(env, *, facing=0, sentinel=False, x=11.5, y=23.0, target=23.0, global_actor=False):
    r=env.object(0x480,'parrot',fill=0xA5)
    w=env.object(0x240,'world',fill=0)
    l=env.object(0x200,'logic',fill=0)
    a=env.object(0x240,'actor',fill=0)
    scene=env.object(0x100,'scene',fill=0)
    manager=env.object(0x100,'collision manager',fill=0)
    env.put(scene+0x24,manager)
    env.put(w+0xc,scene)
    env.put(w+0x6c,l)
    env.put(r+0xc,w,l)
    env.put(r+0x12c,a)
    env.put(a+0xc,scene)
    env.put(a+0x40,0xA0|facing)
    for off, vals in [(0x118,(0x80000000 if sentinel else -13,19,-0x80000000,29)),(0x128,(-17,23,31,37)),(0x138,(-21,27,41,43))]:env.put(a+off,*vals)
    env.put(a+0x190,0x713357)
    env.put(r+0x138,-31,13,47,19)
    env.put(r+0x210,-23,-29,37,41)
    env.put(r+0x350,0)
    env.put(r+0x410,0)
    env.put(r+0x434,-137,263)
    env.put(r+0x420,0xA100,0xB200,0xC300)
    env.put(r+0x2fc,0)
    f64(env,r+0x68,x); f64(env,r+0x70,y); f64(env,r+0x88,target)
    f64(env,r+0x50,17.25);f64(env,r+0x58,-31.5);f64(env,r+0x60,91.75)
    f64(env,0x50ebe0,3.25);f64(env,0x50ebf0,12.0)
    env.put(l+0x1c,0x13579)
    env.put(0x537668+0x18,0)
    root=env.object(0x100,'singleton',fill=0)
    mid=env.object(0x100,'singleton level',fill=0)
    timing=env.object(0x100,'timing',fill=0)
    env.put(0x537e88,root);env.put(root+0x6c,mid);env.put(mid+0x14,timing);env.put(timing+0x80,0x1234)
    env.put(0x534eac,0x26b7)
    env.put(0x537210,0)
    env.put(0x5430c4,17)
    sound=env.object(0x200,'sound logic',fill=0)
    env.put(sound+0x6c,l)
    env.put(0x53c9ac,sound);env.put(0x53c9a8,0)
    env.put(0x537b14,0)
    if global_actor:
        g=env.object(0x500,'global actor',fill=0)
        env.put(g+0x4b4,0xBEEF,0)
        env.put(0x537b14,g)
    return dict(r=r,w=w,l=l,a=a,scene=scene,timing=timing,root=root)


def destructor(kind,ref,large):
    def setup(env):
        t=common(env)
        r=t['r']
        env.put(r+0x2fc,64 if large else 16)
        if large:env.put(r+0x300,env.object(8,'bitset storage',fill=0x39))
        else:env.put(r+0x300,0x7531)
        for off in (0x1a4,0x1a8):
            if kind=='empty':env.put(r+off,env.get(0x52e1c8)+12)
            else:
                s=env.object(32,'string block',fill=0x31)
                env.put(s,ref,5,12);env.put(r+off,s+12)
        def decrement(e,c):
            p=c.arguments[0];v=(e.get(p)-1)&0xffffffff;e.put(p,v);return v
        env.override(0x5469e8,decrement)
        return t
    return setup


def dispatch(state,mode='handler',grow=False, handler_address=None, **options):
    def setup(env):
        t=common(env, **options)
        log=env.object(24,'dispatch log',fill=0)
        def cb(e,c):
            e.put(log,c.receiver,e.get(c.receiver+0x24),e.get(0x537c50),0xC0FFEE)
            e.put(c.receiver+0x430,0x5A7E)
            return 0x789
        handler=handler_address if handler_address is not None else env.stub('parrot state handler','thiscall',0,cb)
        base=env.object(16,'state table',fill=0)
        env.put(base,handler if mode=='handler' else 0,handler,handler,handler)
        env.put(0x537c30,0,0,0,3,base,base,4,0,0)
        env.put(0x537638,0,0,-4,8,env.object(52,'base state table',words=[handler]*13),0,4)
        env.put(0x537c50,0xFAFA)
        return t
    return setup


def constructor(difficulty=0,face=0,lookup=False,param=0,scale=1.0,x=-13,y=29):
    def setup(env):
        t=common(env);r,w,l,scene=t['r'],t['w'],t['l'],t['scene']
        env.put(w+0x4c,x,y)
        env.put(w+0x64,param)
        env.put(w+0x40,face)
        env.put(l+0x64,difficulty,0x345)
        env.put(l+0x168,0x932)
        # Three independent hash registries use a single bucket and honest linked entries.
        def hashmap(container,offset,entries):
            obj=env.object(0x40,'registry',fill=0);env.put(container+offset,obj)
            bucket=env.object(4,'hash bucket',fill=0);env.put(obj+0x14,bucket,1)
            head=0
            for key,value in entries:
                keyp=env.object(len(key)+1,'registry name',data=(key.encode() if isinstance(key,str) else key)+b'\0')
                node=env.object(16,'hash entry',words=[head,0,keyp,value]);head=node
            env.put(bucket,head)
        # Animation metadata used by the original animation selector.
        frame=env.object(64,'animation frame',fill=0);env.put(frame+0x1c,71)
        arr=env.object(4,'animation frame table',words=[frame])
        anim=env.object(32,'animation',fill=0);env.put(anim+0xc,arr,1)
        names=[('GAME_NULL',anim)]
        if lookup:names += [('GAME_PARROT_IDLE',anim),('GAME_PARROT_FLY',anim)]
        # Use exact original names read from binary string arguments below.
        names=[(env.cstr(0x5234b4),anim)]
        if lookup:names += [(env.cstr(0x529b94),anim),(env.cstr(0x529b80),anim)]
        hashmap(scene,0x2c,names)
        hashmap(scene,0x28,[(env.cstr(a),0x2220+i*0x111) for i,a in enumerate((0x5266ec,0x524870,0x524864,0x524858,0x52484c,0x5266dc,0x529b24,0x529b08,0x529af0,0x529adc,0x529ac8))])
        hashmap(scene,0x14,[]);hashmap(scene,0x10,[])
        env.put(0x52f01c,1)
        env.write(0x5262b8,struct.pack('<f',scale))
        env.write(0x50ebe8,struct.pack('<f',113.25))
        env.write(0x5262b4,struct.pack('<f',1.75))
        env.write(0x5262b0,struct.pack('<f',2.625))
        return t
    return setup


def ordinary_cases(random_source):
    for kind in ('empty','owned'):
        for ref in (1,2):
            for large in (False,True):
                for f,arg in ((0x465ce0,None),(0x465cc0,0),(0x465cc0,1),(0x465cc0,2),(0x465cc0,0xffffffff)):
                    yield Case(f'destroy {kind} ref{ref} large{large} arg{arg}',f,destructor(kind,ref,large),receiver=lambda t:t['r'],arguments=() if arg is None else (arg,))
    for state in (-3,0,2,3,6):
        for mode in ('handler','fallback'):
            yield Case(f'dispatch {state} {mode}',0x465db0,dispatch(state,mode),receiver=lambda t:t['r'],arguments=(state,))
    for facing in (0,2):
        for sentinel in (False,True):
            for g in (False,True):
                yield Case(f'idle enter {facing} {sentinel} {g}',0x4663d0,lambda e,f=facing,s=sentinel,g=g:common(e,facing=f,sentinel=s,global_actor=g),receiver=lambda t:t['r'])
    for x in (-15.0,12.0,19.0,float('nan')):
        for y,target in ((23.0,23.0),(23.0,37.0),(float('nan'),23.0)):
            for face in (0,2):
                for sentinel in (False,True):
                    yield Case(f'fly {x} {y} {target} {face} {sentinel}',0x466580,lambda e,x=x,y=y,t=target,f=face,s=sentinel:common(e,x=x,y=y,target=t,facing=f,sentinel=s),receiver=lambda t:t['r'])
    for active in (False,True):
        def active_setup(e,active=active):
            t=common(e,global_actor=True)
            e.put(e.get(0x537b14)+0x4b8,int(active))
            e.put(t['a']+0x190,0)
            e.put(t['a']+0x1a4,1)
            e.override(0x4a3050,returns(99))
            return t
        yield Case(f'idle combat active {active}',0x4664d0,active_setup,receiver=lambda t:t['r'])
    for complete in (0,1):
        for delay in (0,3):
            for rand in (0,9,10,99,100,-1,-101):
                for choice in (-1,0,1):
                    def setup(e,co=complete,de=delay,ra=rand,ch=choice):
                        t=common(e,global_actor=True)
                        e.put(t['a']+0x190,0)
                        e.put(t['a']+0x19c,de)
                        e.put(t['a']+0x1a4,co)
                        e.override(0x4a3050,sequence(ra,ch))
                        return t
                    yield Case(f'idle tick {complete} {delay} {rand} {choice}',0x4664d0,setup,receiver=lambda t:t['r'])
    for mode in (0,1):
        for match in (False,True):
            for rand in (-1002,-1,0,1000,1001,0x7fffffff):
                def setup(e,mo=mode,ma=match,ra=rand):
                    t=common(e);e.put(0x541334,mo);e.put(t['r']+0x2ec,0x1234 if ma else 0x4455)
                    e.override(0x4a3050,returns(ra));return t
                yield Case(f'update {mode} {match} {rand}',0x466730,setup,receiver=lambda t:t['r'],arguments=(0x73,))
    for difficulty in (-1,0,2):
        for face in (0,2):
            for lookup in (False,True):
                for param in (0,7):
                    yield Case(f'construct {difficulty} {face} {lookup} {param}',0x465640,constructor(difficulty,face,lookup,param,(-1.5 if param else 0.75),random_source.randrange(-200,200),random_source.randrange(-200,200)),receiver=lambda t:t['r'],arguments=(lambda t:t['w'],))

    for i in range(32):
        coords=[random_source.randrange(-100000,100000) for _ in range(8)]
        def diverse(e,i=i,coords=coords):
            t=common(e,facing=2 if i&1 else 0,sentinel=False,x=coords[0]/8,y=coords[1]/16,target=coords[1]/16,global_actor=bool(i&2))
            r,a=t['r'],t['a']
            e.put(r+0x138,*coords[2:6])
            e.put(a+0x118,*coords[4:8])
            e.put(r+0x434,coords[0],coords[1])
            frame=e.object(64,'diverse animation frame',fill=0)
            e.put(frame+0x1c,0x700+i)
            table=e.object(4,'diverse animation table',words=[frame])
            anim=e.object(32,'diverse animation',fill=0);e.put(anim+0xc,table,1)
            e.put(a+0x190,anim)
            e.put(a+0x1a4,1)
            e.put(a+0x19c,0)
            e.put(r+0x350,anim if i&4 else 0)
            e.put(r+0x410,anim if i&8 else 0)
            e.override(0x4a3050,sequence(i%11,i&1))
            return t
        for function in (0x4663d0,0x4664d0,0x466580):
            yield Case(f'diverse {i} {function:x}',function,diverse,receiver=lambda t:t['r'])

    for face in (0,2):
        for poison in (0x13579BDF,):
            def observable_constructor(e,face=face,poison=poison):
                t=constructor(2,face,True,7,1.375,-313,557)(e)
                r,w,scene=t['r'],t['w'],t['scene']
                # Adjacent actor flags have deliberately different facing bits.
                e.put(w+0x44,2 if not face else 0)
                # A real sprite makes the unchanged geometry helper publish its bounds.
                sprite=e.object(0x80,'sprite metadata',fill=0)
                frame=e.object(0x40,'sprite frame metadata',fill=0)
                e.put(frame+0x18,3,7,29,43)
                table=e.object(4,'sprite frame table',words=[frame])
                e.put(sprite+0x14,table)
                e.put(sprite+0x64,0,0)
                registry=e.get(scene+0x10)
                bucket=e.get(registry+0x14)
                key=e.object(len(e.cstr(0x529ba8))+1,'sprite registry name',data=e.cstr(0x529ba8)+b'\0')
                node=e.object(16,'sprite registry entry',words=[0,0,key,sprite])
                e.put(bucket,node)
                return t
            yield Case(f'constructor observed fields face{face} poison{poison:x}',0x465640,observable_constructor,receiver=lambda t:t['r'],arguments=(lambda t:t['w'],))


def cases(random_source):
    # Sticky input flags are inherited through every reviewed entry. Assignment
    # depends only on case order, so branch coverage never depends on the seed.
    statuses = (0, 0x20, 0x21, 0x3f)
    for index, case in enumerate(ordinary_cases(random_source)):
        original_setup = case.setup
        status = statuses[index % len(statuses)]
        def setup(env, original_setup=original_setup, status=status):
            env.entry_x87_status(status)
            return original_setup(env)
        case.setup = setup
        case.label += f' inherited SW {status:#x}'
        yield case

    # Select real game handlers, exercising x87 changes through both the Parrot
    # registry and its original base-dispatch fallback, rather than a stub.
    for status in statuses:
        for mode in ('handler', 'fallback'):
            for target, options in (
                (0x4663d0, dict(facing=2, global_actor=True)),
                (0x466580, dict(x=-15.0, y=23.0, target=23.0)),
                (0x466580, dict(x=19.0, y=23.0, target=23.0, facing=2)),
                (0x466580, dict(x=19.0, y=23.0, target=37.0)),
                (0x466580, dict(x=float('nan'), y=23.0, target=23.0)),
                (0x466580, dict(x=-15.0, y=float('nan'), target=23.0)),
            ):
                original_setup = dispatch(0, mode, handler_address=target, **options)
                def setup(env, original_setup=original_setup, status=status):
                    env.entry_x87_status(status)
                    return original_setup(env)
                yield Case(f'dispatch real {target:x} {mode} {options} SW {status:#x}',
                           0x465db0, setup, receiver=lambda t:t['r'], arguments=(0,))

    # Every entry gets all supported precision/rounding settings. Three live
    # inherited slots leave five registers for original callees' temporaries.
    specials = (
        (0xC000000000001357, 0x7fff),  # quiet NaN payload
        (0x8000000000002468, 0xffff),  # negative signaling NaN payload
        (0x8000000000000000, 0x7fff),  # infinity
        (1, 0),                     # extended subnormal
    )
    functions = (0x465640, 0x465cc0, 0x465ce0, 0x465db0,
                 0x4663d0, 0x4664d0, 0x466580, 0x466730)
    for pi, precision in enumerate((0, 0x200, 0x300)):
        for ri, rounding in enumerate((0, 0x400, 0x800, 0xc00)):
            index = pi * 4 + ri
            profile = {
                'control': 0x3f | precision | rounding,
                'status': (((index % 7) + 1) << 11) | (0, 0x100, 0x4400, 0x4700)[ri] | statuses[ri],
                'slots': ((0x8000000000000001, 0x3fff), (0, 0x8000), specials[ri]),
            }
            for function in functions:
                arguments = ()
                if function == 0x465640:
                    setup = constructor(2, 2 if index & 1 else 0, bool(index & 2), 7, 1.375, -313, 557)
                    arguments = (lambda t:t['w'],)
                elif function in (0x465cc0, 0x465ce0):
                    setup = destructor('owned', 1 + (index & 1), bool(index & 2))
                    if function == 0x465cc0:
                        arguments = (index & 1,)
                elif function == 0x465db0:
                    setup = dispatch(0, 'fallback' if index & 1 else 'handler', handler_address=0x466580,
                                     x=-15.0 if index & 2 else 19.0, y=23.0,
                                     target=37.0 if index & 4 else 23.0, facing=2)
                    arguments = (0,)
                elif function == 0x4664d0:
                    def setup(e, index=index):
                        t = common(e, global_actor=True)
                        e.put(t['a'] + 0x190, 0)
                        e.put(t['a'] + 0x19c, 0)
                        e.put(t['a'] + 0x1a4, 1)
                        e.put(e.get(0x537b14) + 0x4b8, index & 1)
                        e.override(0x4a3050, sequence(9, index & 1))
                        return t
                elif function == 0x466730:
                    def setup(e, index=index):
                        t = common(e)
                        e.put(0x541334, index & 1)
                        e.put(t['r'] + 0x2ec, 0x1234 if index & 2 else 0x4455)
                        e.override(0x4a3050, returns(-1002))
                        return t
                    arguments = (0x73,)
                else:
                    def setup(e, index=index):
                        return common(e, facing=2 if index & 1 else 0, sentinel=bool(index & 2),
                                      x=-15.0 if index & 4 else 19.0, y=23.0,
                                      target=37.0 if index & 8 else 23.0, global_actor=True)
                yield Case(f'live inherited {function:x} CW {profile["control"]:#x} SW {profile["status"]:#x}',
                           function, setup, receiver=lambda t:t['r'], arguments=arguments, entry_x87=profile)
