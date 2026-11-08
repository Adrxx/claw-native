"""Original-only enemy action cases, including observable callback publication."""
import struct
from clawparity.cases import Case


def signed(v):
    return v if v < 0x80000000 else v - 0x100000000


def double(env, at, value):
    env.write(at, struct.pack('<d', value))


def base(env, x=40.75, y=55.25):
    e = env.object(0x420, 'enemy', fill=0xA7)
    a = env.object(0x180, 'actor', fill=0)
    v = env.object(0x100, 'enemy-vtable', fill=0)
    player = env.object(0x180, 'player', fill=0)
    level = env.object(0x40, 'level', fill=0)
    scene = env.object(0x100, 'scene', fill=0)
    env.put(e, v)
    env.put(e+0xc, a)
    env.put(a+0xc, level)
    env.put(level+0x24, scene)
    env.put(scene+0x64, 10000, 10000)
    env.put(a+0x4c, int(x), int(y))
    env.put(a+0xcc, 7)
    env.put(0x537e88, player)
    env.put(player+0x4c, 45, 55)
    env.put(0x537210, 2000)
    env.put(0x534eac, 0)
    env.put(e+0xc8, 1)
    for off in range(0x28, 0x118, 8):
        double(env, e+off, 0.0)
    double(env,e+0x68,x)
    double(env,e+0x70,y)
    double(env,e+0x80,x-80)
    double(env,e+0x98,x+80)
    env.put(e+0x124,0)
    env.put(e+0x120,0)
    env.put(e+0x2fc,0,0)
    env.put(e+0x184,0x12345678,0,0x87654321)
    env.put(e+0x3c8,1500,500)
    env.put(a+0x38,3)
    for i in range(5):
        env.put(e+0x28c+i*8, 10+i*4, 3+i*3)
    env.put(e+0x2a4,12)
    env.put(e+0x2d0,17)
    record=env.object(0x800,'callback-record',fill=0)
    def record_call(tag, mutate=None):
        def effect(en,call):
            n=en.get(record)
            p=record+4+n*40
            en.put(p,tag,call.receiver,len(call.arguments),*(list(call.arguments)+[0]*3)[:3],en.get(e+0x14),en.get(e+0x18),en.get(e+0x1c),en.get(e+0x184))
            en.put(record,n+1)
            if mutate: mutate(en,call)
            return 0x71234567
        return effect
    env.put(v+0x24,env.stub('post virtual','thiscall',0,record_call(3)))
    env.put(v+0x5c,env.stub('motion virtual','thiscall',1,record_call(4)))
    def rect(en,call):
        en.put(call.arguments[0],*call.arguments[1:])
        return 1
    def inside(en,call):
        p,xv,yv=call.arguments
        l,t,r,b=[signed(en.get(p+i*4)) for i in range(4)]
        return int(l<=signed(xv)<r and t<=signed(yv)<b)
    env.override(0x546d5c,rect)
    env.override(0x546cd4,inside)
    env.override(0x546a40,lambda en,c:0)
    return dict(e=e,a=a,v=v,player=player,scene=scene,record=record,record_call=record_call)


def choose_setup(x,y,**kw):
    def setup(env):
        t=base(env,**kw)
        env.put(t['player']+0x4c,x,y)
        return t
    return setup


def one(label, fn, setup, arg=None):
    return Case(label,fn,setup,receiver=(0 if fn==0x4dc830 else lambda t:t['e']),arguments=((lambda t:t['e'],) if fn==0x4dc830 else (() if arg is None else (arg,))))


def cases(random_source):
    for x in (-100,30,40,45,50,100,1000):
        for y in (55,65,75,85,1000):
            yield one(f'choose geometry {x} {y}',0x43e420,choose_setup(x,y))
    for count,bits,special in ((0,0,0),(1,2,0),(2,2,0),(32,2,0),(33,2,0),(33,0,0),(0,0,0x26b7)):
        def setup(env,count=count,bits=bits,special=special):
            t=base(env); p=env.object(4,'bit-storage',words=[bits])
            env.put(t['e']+0x2fc,count,p if count>32 else bits)
            env.put(0x534eac,special)
            return t
        yield one(f'choose bit layout {count} {bits} {special}',0x43e420,setup)
    for elapsed in (0,499,500,501,0xffffffff):
        def setup(env,elapsed=elapsed):
            t=choose_setup(10000,10000)(env)
            env.put(t['e']+0x188,1)
            env.put(t['e']+0x3c8,(2000-elapsed)&0xffffffff,500)
            return t
        yield one(f'choose timer {elapsed}',0x43e420,setup)
    def vanished(env):
        t=choose_setup(10000,10000)(env);env.put(t['a']+0x38,0xffffffff);return t
    yield one('choose vanished target',0x43e420,vanished)
    for flag in (0,1):
        for rand in (0,1000,1001,0x7fffffff,0xffffffff):
            def setup(env,flag=flag,rand=rand):
                t=base(env);env.put(0x541334,flag);env.override(0x4a3050,lambda en,c:rand);return t
            yield one(f'pre flag {flag} random {rand}',0x404fc0,setup,0x10203040)
    for primary,secondary,match,mutate in ((0,0,0,0),(1,0,1,0),(1,1,0,0),(1,1,1,0),(1,1,1,1)):
        def setup(env,primary=primary,secondary=secondary,match=match,mutate=mutate):
            t=base(env);e=t['e'];seq=env.object(0x30,'sequence',fill=0);env.put(e+0x10,seq)
            env.put(seq+0x1c,23 if match else 24);env.put(e+0x1c,23)
            alt=env.stub('replacement primary','thiscall',0,t['record_call'](9))
            def change(en,c):
                en.put(e+0x14,alt);en.put(e+0x1c,0x10293847)
            env.put(e+0x14,env.stub('primary','thiscall',0,t['record_call'](2)) if primary else 0)
            env.put(e+0x18,env.stub('secondary','thiscall',0,t['record_call'](1,change if mutate else None)) if secondary else 0)
            return t
        yield one(f'post {primary} {secondary} {match} mutate {mutate}',0x4063b0,setup,0x55667788)
    def nested(env):
        t=base(env);p=env.object(0x30,'nested-parent',fill=0);o=env.object(4,'nested-child');v=env.object(0x20,'nested-table',fill=0)
        env.put(t['e']+0x6c,p);env.put(p+0x18,o);env.put(o,v);env.put(v+0x14,env.stub('nested','thiscall',0,t['record_call'](8)));return t
    yield one('nested callback receiver and constant result',0x4dc830,nested)
    for state in (0,1,2,3,4):
        def setup(env,state=state):
            t=base(env);owner=env.object(0x80,'tracked-owner',fill=0);obj=env.object(0x140,'tracked-inner',fill=0x45)
            env.put(0x53c9ac,owner if state else 0);env.put(0x53c9b0,t['a'] if state!=1 else 7)
            env.put(owner+0x6c,obj if state!=2 else 0);env.put(obj+0x1c,15 if state!=3 else 14);return t
        yield one(f'clear tracked {state}',0x43e9b0,setup)
    for _ in range(12):
        x=random_source.uniform(-1000,1000);y=random_source.uniform(-1000,1000)
        yield one(f'integrate free {x} {y}',0x4dca10,lambda en,x=x,y=y:base(en,x,y))
    yield one('motion free mode',0x43dfa0,base)
    for hit in range(5):
        def setup(env,hit=hit):
            t=base(env);e=t['e']
            for i in range(5): env.put(e+0x290+8*i,20 if i==hit else -1)
            return t
        yield one(f'choose isolated rectangle {hit}',0x43e420,setup)
    for platform in (0,1,2):
        for mode in (0,7):
            def setup(env,platform=platform,mode=mode):
                t=base(env);a=t['a'];env.put(a+8,0x10 if platform else 0);env.put(a+0xcc,mode)
                p=env.object(0x160,'moving-platform',fill=0);env.put(p+0x158,7,0xfffffff9)
                env.put(a+0x80,p if platform==2 else 0)
                env.put(a+0x4c,22,33)
                return t
            yield one(f'integrate platform {platform} mode {mode}',0x4dca10,setup)
    for index in (-3,2,4,9):
        for fail in (False,):
            for empty in (False,True):
                def setup(env,index=index,fail=fail,empty=empty):
                    t=base(env);e=t['e'];table=env.object(64,'action-table',fill=0)
                    cb=env.stub('registered action','thiscall',0,t['record_call'](10))
                    for i in range(3):env.put(table+i*8,0 if empty else cb,0x76543210+i)
                    fallback=env.object(4,'fallback-slot',words=[0 if empty else cb])
                    err=env.object(0x18,'registry-error',fill=0);env.put(err+0xc,4)
                    env.put(0x537638,0,err,2,4,table,fallback,8,table,0)
                    env.put(0x540fe8,0)
                    def realloc(en,c):
                        p=en.object(c.arguments[3],'expanded-registry',fill=0xCE)
                        old=c.arguments[2];en.write(p,en.read(old,24));en.release(old);return p
                    env.override(0x546928,realloc)
                    # Null callbacks use a valid RTTI graph, without exception routes.
                    desc=env.object(0x10,'RTTI-descriptor',fill=0);data=env.object(8,'RTTI-type',fill=0x35)
                    vt=env.object(0x104,'RTTI-vtable',fill=0);env.put(vt,desc);env.put(desc+0xc,data);env.put(e,vt+4)
                    return t
                yield one(f'dispatch index {index} fail {fail} empty {empty}',0x43d490,setup,index)
    for mode in (0,1,3,7):
        for direction in (-1,0,1):
            for tile in (0,1,2,3):
                yield one(f'integrate collision mode {mode} dir {direction} tile {tile}',0x4dca10,motion_setup(mode,direction,tile))
    for count,bits in ((0,0),(1,1),(3,0),(4,8),(4,12),(32,8),(33,8),(33,9)):
        for direction in (-1,0,1):
            for tile in (0,1,2,3):
                yield one(f'motion bits {count} {bits} dir {direction} tile {tile}',0x43dfa0,motion_setup(1,direction,tile,count,bits))
    for count,bits in ((0,0),(4,0),(5,16),(32,0),(33,0),(33,16)):
        for state in (0,1,2):
            for dead in (False,True):
                def setup(env,count=count,bits=bits,state=state,dead=dead):
                    t=motion_setup(0,0,0,count,bits)(env);env.put(t['a']+8,0x400000)
                    seq=env.object(0x20,'motion-sequence',fill=0);env.put(seq+0x1c,12);env.put(t['e']+0x10,seq)
                    s=env.object(12,'motion-name',data=b'LS_DEAD\0' if dead else b'LS_OTHER\0')
                    table=env.object(4,'name-table',words=[s]);env.put(0x537698,0,0,12,12,table,table,4,table,0)
                    scene=env.object(0x48,'world-state',fill=0);env.put(scene+0x44,state);env.put(0x537960,scene)
                    return t
                yield one(f'motion death bits {count} {bits} state {state} dead {dead}',0x43dfa0,setup)

    def frozen_motion(env):
        t=motion_setup(1,1,0,4,8)(env)
        env.put(t['e']+0xc8,1)
        return t
    yield one('motion frozen velocity correction gate',0x43dfa0,frozen_motion)
    def primary_publication(env):
        t=base(env);e=t['e']
        replacement=env.object(0x100,'replacement-vtable',fill=0)
        env.put(replacement+0x24,env.stub('replacement virtual','thiscall',0,t['record_call'](21)))
        def publish(en,c):
            en.put(e,replacement)
            en.put(e+0x14,0x55667788,0x12345678,0x87654321)
        env.put(e+0x14,env.stub('publishing primary','thiscall',0,t['record_call'](20,publish)),0,0x76543210)
        return t
    yield one('post primary publishes vtable before final call',0x4063b0,primary_publication,0x76549810)
    for n in range(12):
        x=random_source.uniform(-150,150);y=random_source.uniform(-150,150)
        def setup(env,x=x,y=y,n=n):
            t=base(env,x,y)
            double(env,t['e']+0x80,x+(100 if n%2 else -100))
            double(env,t['e']+0x98,x+(-100 if n%3 else 100))
            env.put(t['player']+0x4c,int(x)+n-6,int(y)+n-6)
            return t
        yield one(f'choose randomized geometry {n}',0x43e420,setup)
    for direction in (-1,1):
        for probe in (0,1,2,3):
            for lower in (0,1):
                for count in (4,33):
                    def setup(env,direction=direction,probe=probe,lower=lower,count=count):
                        t=motion_setup(1,direction,0,count,8)(env);e=t['e']
                        neighbor=env.object(0x130,'probe-neighbor',fill=0)
                        level=env.object(0x28,'probe-level',fill=0)
                        scene=env.object(0x100,'probe-scene',fill=0)
                        grid=env.object(0x98,'probe-grid',fill=0)
                        cells=env.object(4,'probe-cells',words=[0]);rows=env.object(4,'probe-rows',words=[0])
                        env.put(e+0x128,neighbor,t['a']);env.put(neighbor+0xc,level);env.put(neighbor+0x50,60)
                        env.put(level+0x24,scene);env.put(scene+0x5c,grid)
                        env.put(grid+0x20,cells,rows);env.put(grid+0x30,4096,4096);env.put(grid+0x8c,12,12)
                        obj=env.object(4,'probe-tile');vt=env.object(0x24,'probe-vtable',fill=0);lookup=env.object(4,'probe-lookup',words=[obj])
                        env.put(scene+0x4c,lookup);env.put(obj,vt)
                        def effect(en,c):
                            t['record_call'](12)(en,c)
                            return probe if c.arguments[1]==61 else lower
                        env.put(vt+0x20,env.stub('probe solidity','thiscall',2,effect))
                        return t
                    yield one(f'motion ledge {direction} {probe} {lower} {count}',0x43dfa0,setup)
    for same in (False,True):
        for below in (False,True):
            def setup(env,same=same,below=below):
                t=base(env);env.put(t['e']+0x2fc,1,1);env.put(t['player']+0x50,0 if below else 200)
                env.put(t['a']+0x64,17+(4000 if below else 3899) if same else 123)
                return t
            yield one(f'motion depth publication {same} {below}',0x43dfa0,setup)
    def bounce(env):
        t=motion_setup(3,0,0)(env);e=t['e'];a=t['a']
        double(env,e+0x58,-2.5)
        # A legitimate polymorphic tile query publishes a mode transition.
        # The outer collision helper observes it and produces its bounce bit.
        grid=env.get(t['scene']+0x5c);cells=env.get(grid+0x20)
        obj=env.get(env.get(t['scene']+0x4c));vt=env.get(obj)
        def changed(en,c):
            t['record_call'](13)(en,c);en.put(a+0xcc,4);return 0
        env.put(vt+0x20,env.stub('transition tile','thiscall',2,changed))
        return t
    yield one('integrate callback publishes bounce transition',0x4dca10,bounce)

    def dispatch_owned_action(env):
        t=base(env)
        table=env.object(8,'owned-action-table',words=[0x43e9b0,0x12345678])
        fallback=env.object(4,'owned-action-fallback',words=[0x43e9b0])
        env.put(0x537638,0,0,2,2,table,fallback,8,table,0)
        env.put(0x53c9ac,0)
        env.put(0x53c9b0,t['a'])
        return t
    yield one('dispatch genuine owned zero-argument action',0x43d490,dispatch_owned_action,2)

    # Original rectangle hit paths reset an existing timer, and the vertical
    # bound must use the complete coordinate rather than a neighboring field.
    for hit in range(5):
        def setup(env,hit=hit):
            t=base(env);e=t['e']
            env.put(e+0x188,0x76543210)
            for i in range(5):
                env.put(e+0x290+8*i,20 if i==hit else -1)
            return t
        yield one(f'choose hit resets nonzero timer {hit}',0x43e420,setup)
    for x,y in ((-500.125,-1000.875),(800.625,-70.375),(-40.125,300.875),(10.25,2.75)):
        def setup(env,x=x,y=y):
            t=base(env,x,y);e=t['e']
            env.put(e+0x78,0x3ff00000)
            env.put(t['player']+0x4c,int(x)+2,int(y)+1)
            env.put(e+0x188,0x87654321)
            return t
        yield one(f'choose asymmetric vertical bounds {x} {y}',0x43e420,setup)
    for speed in (1.23456789,-3.141592653589793):
        def setup(env,speed=speed):
            t=motion_setup(1,0,0)(env);e=t['e']
            env.put(e+0xc8,1)
            double(env,e+0x58,speed)
            return t
        yield one(f'integrate clears both velocity words {speed}',0x4dca10,setup)
    for player_y in (54,69,70,83):
        def setup(env,player_y=player_y):
            t=base(env);e=t['e']
            env.put(e+0x2fc,1,1)
            env.put(t['a']+0x124,27,0x13572468)
            env.put(t['player']+0x50,player_y)
            env.put(t['player']+0x124,13,0xfffffc18)
            env.put(t['a']+0x64,0x12345678)
            return t
        yield one(f'motion depth uses distinct target height {player_y}',0x43dfa0,setup)

    # Balanced inherited environments must retain the actual PhysicsUpdate
    # comparison flags and sticky exceptions through every later conversion.
    for status in (0, 0x20, 0x21):
        for final_limit in (-1.0, 0.0, 1.0, float('nan')):
            def setup(env, status=status, final_limit=final_limit):
                env.entry_x87_status(status)
                t=motion_setup(7,0,0)(env);e=t['e'];a=t['a']
                env.put(0x537210,0)
                double(env,e+0x28,0.0)
                double(env,e+0x68,40.0)
                double(env,e+0x70,55.0)
                double(env,e+0x60,0.0)
                double(env,e+0x110,final_limit)
                env.put(a+0x4c,40,55)
                return t
            yield one(f'integrate inherited SW {status:#x} zero dt final cap {final_limit}',0x4dca10,setup)
        for mode,direction,tile in ((0,-1,0),(1,1,1),(3,1,2),(7,-1,3)):
            def setup(env,status=status,mode=mode,direction=direction,tile=tile):
                env.entry_x87_status(status)
                return motion_setup(mode,direction,tile)(env)
            yield one(f'integrate inherited SW {status:#x} collision {mode} {direction} {tile}',0x4dca10,setup)
        for platform in (False,True):
            def setup(env,status=status,platform=platform):
                env.entry_x87_status(status)
                t=motion_setup(7,0,0)(env);a=t['a']
                env.put(a+8,0x10 if platform else 0)
                p=env.object(0x160,'environment-platform',fill=0)
                env.put(p+0x158,7,0xfffffff9)
                env.put(a+0x80,p)
                return t
            yield one(f'integrate inherited SW {status:#x} platform {platform}',0x4dca10,setup)

    # The same motion implementation is also reached through ordinary game
    # callbacks. Keep those real owned targets in the slots, so the comparison
    # checks inherited entry state, memory effects and publication order. The
    # three variants elect different sticky flags independently of random seed.
    for route,entry,arg in (
        ('post virtual',0x4063b0,0x10203040),
        ('post primary',0x4063b0,0x55667788),
        ('post secondary',0x4063b0,0x76543210),
        ('registry',0x43d490,2),
        ('nested virtual',0x4dc830,None),
    ):
        for variant in range(3):
            for scenario in range(6):
                def setup(env,route=route,variant=variant,scenario=scenario):
                    env.entry_x87_status((0,0x20,0x21)[variant])
                    mode,direction,tile=(1,1,1) if scenario==4 else (7,0,0)
                    t=motion_setup(mode,direction,tile)(env)
                    e,a=t['e'],t['a']
                    if scenario<4:
                        x,y=((40,55),(-40,-55),(0,1))[variant]
                        env.put(0x537210,0)
                        double(env,e+0x28,0.0)
                        double(env,e+0x68,float(x))
                        double(env,e+0x70,float(y))
                        double(env,e+0x60,0.0)
                        double(env,e+0x110,(-1.0,0.0,1.0,float('nan'))[scenario])
                        env.put(a+0x4c,x & 0xffffffff,y & 0xffffffff)
                    elif scenario==4:
                        double(env,e+0x68,42.75+variant*0.125)
                        double(env,e+0x70,55.25+variant*0.125)
                    elif scenario==5:
                        p=env.object(0x160,'callback-moving-platform',fill=0)
                        dx,dy=((7,-7),(-13,9),(0,0))[variant]
                        env.put(p+0x158,dx & 0xffffffff,dy & 0xffffffff)
                        env.put(a+8,0x10)
                        env.put(a+0x80,p)
                    env.put(e+0x14,0,0,23)
                    if route.startswith('post '):
                        seq=env.object(0x20,'callback-sequence',fill=0)
                        env.put(seq+0x1c,23)
                        env.put(e+0x10,seq)
                        primary=env.stub('outer primary','thiscall',0,t['record_call'](30))
                        secondary=env.stub('outer secondary','thiscall',0,t['record_call'](31))
                        env.put(e+0x14,0x4dca10 if route=='post primary' else primary,
                                0x4dca10 if route=='post secondary' else secondary)
                        if route=='post virtual':
                            env.put(t['v']+0x24,0x4dca10)
                    elif route=='registry':
                        table=env.object(8,'motion-action-table',words=[0x4dca10,0x13572468])
                        fallback=env.object(4,'motion-action-fallback',words=[0x4dca10])
                        env.put(0x537638,0,0,2,2,table,fallback,8,table,0)
                    else:
                        # The nested receiver is the motion object; the cdecl
                        # argument is a distinct owner with its own pointer graph.
                        owner=env.object(0x70,'motion-method-owner',fill=0x39)
                        parent=env.object(0x1c,'motion-method-parent',fill=0)
                        env.put(owner+0x6c,parent)
                        env.put(parent+0x18,e)
                        env.put(t['v']+0x14,0x4dca10)
                        t['e']=owner
                    return t
                yield one(f'owned motion {route} variant {variant} scenario {scenario}',entry,setup,arg)

    # These slots contain the inherited game update itself, rather than a
    # fixture. It reaches integrateMotion internally before its own arithmetic.
    # The post-action route also executes its genuine primary motion callback
    # before the inherited virtual update, checking repeated state handoff.
    for route,entry,arg in (
        ('post inherited update',0x4063b0,0x45671230),
        ('registry inherited update',0x43d490,2),
        ('nested inherited update',0x4dc830,None),
    ):
        for status in (0,0x20,0x21):
            for scenario in range(4):
                def setup(env,route=route,status=status,scenario=scenario):
                    env.entry_x87_status(status)
                    t=motion_setup(7,0,0)(env)
                    e,a=t['e'],t['a']
                    env.put(0x537210,0)
                    double(env,e+0x28,0.0)
                    double(env,e+0x60,0.0)
                    double(env,e+0x110,(-1.0,0.0,1.0,float('nan'))[scenario])
                    if route.startswith('post'):
                        env.put(e+0x14,0x4dca10,0,0x76543210)
                        env.put(t['v']+0x24,0x43dfa0)
                    elif route.startswith('registry'):
                        table=env.object(8,'inherited-action-table',words=[0x43dfa0,0x24681357])
                        fallback=env.object(4,'inherited-action-fallback',words=[0x43dfa0])
                        env.put(0x537638,0,0,2,2,table,fallback,8,table,0)
                    else:
                        owner=env.object(0x70,'inherited-method-owner',fill=0x5b)
                        parent=env.object(0x1c,'inherited-method-parent',fill=0)
                        env.put(owner+0x6c,parent)
                        env.put(parent+0x18,e)
                        env.put(t['v']+0x14,0x43dfa0)
                        t['e']=owner
                    return t
                yield one(f'owned {route} SW {status:#x} final cap {scenario}',entry,setup,arg)


def motion_setup(mode,direction,tile,count=0,bits=0):
    def setup(env):
        t=base(env);e=t['e'];a=t['a'];scene=t['scene']
        env.put(a+0xcc,mode);env.put(a+0xdc,1,1)
        env.put(a+0x118,0,0,0,0)
        env.put(e+0xc8,0)
        double(env,e+0x28,1.0)
        double(env,e+0x50,float(direction)*3.25)
        for off in (0x80,0x88,0x90): double(env,e+off,-10000.0)
        for off in (0x98,0xa0,0xa8,0xe8,0xf0,0xf8,0x100,0x108,0x110): double(env,e+off,10000.0)
        double(env,e+0x68,40.75+direction*2)
        double(env,e+0x70,55.25)
        double(env,e+0xb0,float(direction)*3.25)
        env.put(e+0x2fc,count,env.object(4,'heap-bits',words=[bits]) if count>32 else bits)
        env.put(e+0x128,a,a)
        grid=env.object(0x98,'tile-grid',fill=0);cells=env.object(4,'tile-cell',words=[0]);rows=env.object(4,'tile-row',words=[0])
        env.put(grid+0x20,cells,rows);env.put(grid+0x30,4096,4096);env.put(grid+0x8c,12,12)
        env.put(scene+0x5c,grid)
        tileobj=env.object(4,'tile-object');tilevt=env.object(0x24,'tile-vtable',fill=0);lookup=env.object(4,'tile-lookup',words=[tileobj]);env.put(tileobj,tilevt);env.put(scene+0x4c,lookup)
        def query(en,c):
            # One-pixel floor, with selectable walls above it. The floor's
            # preceding pixel stays empty so the original can settle normally.
            x,y=c.arguments
            return 1 if y>=56 else tile
        env.put(tilevt+0x20,env.stub('tile solidity','thiscall',2,query))
        return t
    return setup
