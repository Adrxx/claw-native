"""Original-backed lava-hand state, timer, dispatch and projectile cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns


def obj(env, size, name, **kw):
    kw.setdefault("fill", 0)
    return env.object(size, name, **kw)


def registry(env, entries=()):
    reg = obj(env, 0x40, 'registry')
    env.put(reg + 0x18, 1)
    if entries:
        head = 0
        for name, value in reversed(entries):
            key = obj(env, len(name) + 1, 'key', data=name.encode() + b'\0')
            head = obj(env, 0x10, 'map-node', words=[head, 0x91, key, value])
        buckets = obj(env, 4, 'buckets', words=[head])
        env.put(reg + 0x14, buckets)
    return reg


def base(env, x=17, px=80, facing=0x91, sentinel=0, seed=0x519273ab, animation=False, y=-27, alias=False):
    r = obj(env, 0xb8, 'lava-hand', fill=0x5b)
    a = obj(env, 0x300 if alias else 0x1b4, 'actor')
    if alias:
        r = a + 0xdc
        env.write(r, bytes([0x5b]) * 0xb8)
    logic = obj(env, 0x174, 'logic')
    player = obj(env, 0x60, 'player')
    scene = obj(env, 0x40, 'scene')
    env.put(scene + 0x10, registry(env), registry(env))
    env.put(scene + 0x2c, registry(env))
    env.put(a + 0xc, scene)
    env.put(a + 0x6c, logic)
    env.put(a + 8, seed)
    env.put(a + 0x40, facing)
    env.put(a + 0x4c, x, y)
    env.put(a + 0x118, 0x80000000 if sentinel & 1 else -23)
    env.put(a + 0x120, 41)
    env.put(a + 0x128, 0x80000000 if sentinel & 2 else -37)
    env.put(a + 0x130, 59)
    env.put(a + 0x138, -73, -29, 83, 31)
    env.put(a + 0x18c, a)
    env.put(player + 0x4c, px)
    env.put(0x537e88, player)
    env.put(logic + 0x1c, seed ^ 0x12387645)
    env.put(logic + 0x2c, -111, 141, -97, 163)
    env.put(logic + 0xbc, seed ^ 0x98bc7a33)
    env.put(r + 8, a, a, logic)
    env.put(r + 0x28, a, a, logic)
    env.put(r + 0x38, -19)
    env.put(r + 0x40, 67)
    env.put(r + 0xa4, 0)
    env.put(r + 0x9c, 0x12345678, 33)
    env.put(r + 0xa8, 0x456789ab, 3, 5, 0)
    env.put(0x537680, 0)
    env.put(0x540e00, 0)
    env.put(0x5430c4, 1)
    if animation:
        f = obj(env, 0x30, 'animation-frame')
        env.put(f + 0x18, 7, seed ^ 0x28394751)
        arr = obj(env, 4, 'frames', words=[f])
        ani = obj(env, 0x14, 'animation', words=[0, 0, 0, arr, 1])
        env.put(r + 0xa4, ani)
    return dict(r=r, a=a, logic=logic, scene=scene)


def setup_state(options, function):
    def setup(env):
        t = base(env, **{k:v for k,v in options.items() if k in ('x','px','facing','sentinel','seed','animation','y','alias')})
        r,a=t['r'],t['a']
        # A real one-key Patricia leaf supplies distinct nonzero state IDs.
        state_name = b'ES_IDLE' if function == 0x456840 else b'ES_THROWING'
        key=obj(env, len(state_name)+1,'state-key',data=state_name+b'\0')
        node=obj(env, 0x14,'state-node')
        env.put(node,node,node,0,key,0x6a7b8c9d)
        env.put(0x537680,node)
        if 'tick' in options: env.put(0x537210,options['tick'])
        if 'start' in options: env.put(r+0x9c,options['start'])
        if 'duration' in options: env.put(r+0xa0,options['duration'])
        if function == 0x456a10:
            env.put(a+0x16c, options.get('frame',9))
            env.put(a+0x19c,options.get('delay',0))
            env.put(a+0x1a4,options.get('complete',0))
            env.put(r+0xb4,options.get('created',0))
            env.put(r+0xac,options.get('count',3))
            env.put(r+0xb0,options.get('limit',5))
            env.put(r+0x8c,options.get('direction',2))
            factory=obj(env, 0x40,'factory')
            env.put(factory+0xc,t['scene'])
            env.put(t['logic']+0xc,t['scene'])
            env.put(factory+0x28,10)
            env.put(t['scene']+8,factory)
            if options.get('spawn',False):
                record=obj(env, 0x18,'projectile-record')
                log=obj(env, 0x28,'callback-record')
                motion=obj(env, 0x80,'projectile-motion')
                env.write(motion+0x38,struct.pack('<9d',1.25,2.5,0.5,9.,8.,7.,11.,13.,47.))
                def callback(env,call):
                    p=call.arguments[0]
                    d=env.get(p+0x6c)
                    env.put(log,p,call.receiver,env.get(r+0xb4),env.get(r+0xac),env.get(p+0x4c),env.get(p+0x50),env.get(p+0x64))
                    if options.get('reread',False):
                        other=obj(env, 0x1c,'replacement-projectile-logic')
                        env.put(other+0x18,motion)
                        env.put(p+0x6c,other)
                        env.put(r+0x8c,3)
                    else: env.put(d+0x18,motion)
                    return 0x8192abcd
                env.put(record+0x10,env.stub('projectile-created','cdecl',1,callback))
                env.put(t['scene']+0x14,registry(env,[('LavaHandProjectile',record)]))
        return t
    return setup


def dispatch(index, low, high, empty=False, growth=False, fail=False):
    def setup(env):
        t=base(env)
        r=t['r']
        log=obj(env, 0x14,'dispatch-log')
        def callback(env,call):
            env.put(log,call.receiver,env.get(0x537a50),env.get(0x537a38),env.get(0x537a3c),0xdecafb31)
            return 0x7e39abcd
        cb=env.stub('state-dispatch','thiscall',0,callback)
        table=obj(env, (high-low+1)*8,'state-table')
        for i in range(high-low+1): env.put(table+i*8,0 if empty else cb,0x879abcde+i)
        env.put(0x537a38,low,high,table,table,8)
        env.put(0x537a50,0xbadc0ffe)
        env.put(0x537a4c,0,0)
        if empty or growth:
            vt=obj(env, 8,'vtable-with-locator')
            loc=obj(env, 0x10,'locator')
            typ=obj(env, 8,'type-info',words=[0x12349876,0x87654321])
            env.put(vt,loc)
            env.put(loc+0xc,typ)
            env.put(r,vt+4)
        if fail: env.override(0x4a9070,allocate(fail=True))
        return t
    return Case(f'dispatch {index} range {low}:{high} empty{empty} fail{fail}',0x4562e0,setup,receiver=lambda t:t['r'],arguments=(index,))


def changing_dispatch():
    def setup(env):
        t = base(env)
        log = obj(env, 0x10, 'changing-dispatch-log')
        def callback(env, call):
            env.put(log, call.receiver, env.get(0x537a38), env.get(0x537a3c), env.get(0x537a50))
            return 0
        cb = env.stub('changing-state', 'thiscall', 0, callback)
        table = obj(env, 4, 'zero-width-table', words=[cb])
        env.put(0x537a38, 0, 1, table, table, 0)
        env.put(0x537a4c, 0, 0)
        def resizing(env, call):
            if env.calls_so_far(0x4a9070) == 1:
                env.put(0x537a38, -2, -2)
            return table
        env.override(0x4a9070, resizing)
        return t
    return Case('dispatch rechecks bounds changed by realloc', 0x4562e0, setup, receiver=lambda t:t['r'], arguments=(-1,))


def constructor(count, found, seed):
    def setup(env):
        t=base(env,seed=seed)
        env.put(t['a']+0x108,count)
        ani=obj(env, 0x14,'selected-animation')
        if found: env.put(t['scene']+0x2c,registry(env,[('LEVEL_LAVAHAND',ani)]))
        else: env.put(t['scene']+0x2c,registry(env,[('GAME_NULL',ani)]))
        return t
    return Case(f'constructor count{count} found{found}',0x4566b0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['a'],))


def constructor_observed(seed, has_hit=True, has_attack=True):
    def setup(env):
        t=base(env,seed=seed)
        r,a=t['r'],t['a']
        # The constructor must initialize these itself before any callback.
        env.write(r,bytes([0xa7])*0xb8)
        env.put(a+0x108,4)
        log=obj(env,0x100,'logic-interface-record')
        methods=obj(env,0x28,'logic-interface-vtable')
        def reset(env,call):
            offset=(env.calls_so_far(reset_stub)-1)*16
            env.put(log+offset,call.receiver,env.get(r),env.get(r+4),env.get(r+0x10))
            return 0x91234567
        reset_stub=env.stub('logic-reset','thiscall',0,reset)
        def load(env,call):
            off=0x60+(env.calls_so_far(load_stub)-1)*16
            env.put(log+off,call.receiver,call.arguments[0],call.arguments[1],env.get(r+8))
            return 1
        load_stub=env.stub('logic-load','thiscall',2,load)
        env.put(methods+0x1c,reset_stub)
        env.put(methods+0x24,load_stub)
        hit=obj(env,4,'hit-interface',words=[methods])
        attack=obj(env,4,'attack-interface',words=[methods])
        env.put(a+0x70,hit)
        env.put(a+0x78,attack)
        entries=[]
        for enabled,name,value in ((has_hit,'LogicHit',seed),(has_attack,'LogicAttack',seed^0xabababab)):
            if enabled:
                record=obj(env,0x14,name+'-record')
                env.put(record+0x10,value)
                entries.append((name,record))
        env.put(t['scene']+0x14,registry(env,entries))
        ani=obj(env,0x14,'constructor-animation')
        env.put(t['scene']+0x2c,registry(env,[('LEVEL_LAVAHAND',ani)]))
        image=obj(env,0x6c,'constructor-image')
        frames=obj(env,4,'image-frames',words=[0x7a8b9cad])
        env.put(image+0x14,frames)
        env.put(image+0x64,0,0)
        env.put(t['scene']+0x10,registry(env,[('LEVEL_LAVAHAND',image)]))
        # Real string comparison now traverses the declared lock/unlock boundary.
        env.put(0x540e00,1)
        return t
    return Case(f'observed constructor {seed:x} hit{has_hit} attack{has_attack}',0x4566b0,setup,receiver=lambda t:t['r'],arguments=(lambda t:t['a'],))


def cases(random_source):
    for x,px,y in [(0,0,1),(-13,17,29),(-0x80000000,0x7fffffff,0x7fffffff)]:
        o=dict(x=x,px=px,y=y,facing=0x89,animation=True)
        yield Case(f'independent coordinates {o}',0x4568b0,setup_state(o,0x4568b0),receiver=lambda t:t['r'])
    for hit,attack in [(True,True),(True,False),(False,True)]:
        yield constructor_observed(random_source.getrandbits(32),hit,attack)
    o=dict(alias=True,animation=True,x=0,px=80,facing=0x8b)
    yield Case('throw overlapping state and actor animation fields',0x4568b0,setup_state(o,0x4568b0),receiver=lambda t:t['r'])
    yield changing_dispatch()
    for index in (-4,-1,0,1,4):
        yield dispatch(index,-4,4)
        yield dispatch(index,-4,4,empty=True)
    yield dispatch(-6,-4,4,empty=True,growth=True)
    yield dispatch(7,-4,4,empty=True,growth=True)
    for count in (-0x80000000,-2,0,1,2,7,0x7fffffff):
        for found in (False,True): yield constructor(count,found,random_source.getrandbits(32))
    for seed in (0x519273ab,0xfedcba98,0x12345678):
        yield Case(f'idle {seed:x}',0x456840,setup_state(dict(seed=seed),0x456840),receiver=lambda t:t['r'])
    for x,px in [(-0x80000000,0),(0,0),(17,-13),(0x7fffffff,-1)]:
        for facing in (0x89,0x8b):
            for sentinel in range(4):
                for animation in (False,True):
                    o=dict(x=x,px=px,facing=facing,sentinel=sentinel,animation=animation,seed=random_source.getrandbits(32))
                    yield Case(f'throw {o}',0x4568b0,setup_state(o,0x4568b0),receiver=lambda t:t['r'])
    for tick,start,duration in [(99,100,0),(100,100,0),(100,100,1),(101,100,1),(102,100,3),(0,0xffffffff,1),(0xffffffff,0,0xffffffff),(0x80000000,0,0x7fffffff)]:
        o=dict(tick=tick,start=start,duration=duration)
        yield Case(f'idle timer {o}',0x456880,setup_state(o,0x456880),receiver=lambda t:t['r'])
    for frame in (9,10,11):
        for created in (0,1,0xffffffff):
            for complete,delay in [(0,0),(1,1),(1,0)]:
                for count in (3,5,6):
                    o=dict(frame=frame,created=created,complete=complete,delay=delay,count=count,tick=0xfedcba98)
                    yield Case(f'update {o}',0x456a10,setup_state(o,0x456a10),receiver=lambda t:t['r'])
    for direction in (2,3,0xffffffff):
        for reread in (False,True):
            o=dict(frame=10,spawn=True,direction=direction,reread=reread,count=0xffffffff)
            yield Case(f'spawn {o}',0x456a10,setup_state(o,0x456a10),receiver=lambda t:t['r'])
