"""Original-derived Level 7 crab bomb and shared player state comparisons."""
import itertools
import math
import struct
from clawparity.cases import Case


def callback(env, name, log, argc=0):
    def effect(e, c):
        e.put(log, e.get(log) + 1, c.receiver, *c.arguments)
        e.put(log+0x14, e.get(c.receiver+0x10),
              e.get(c.receiver+0x24), e.get(c.receiver+0xc8))
        return 0x75a51234
    return env.stub(name, 'thiscall', argc, effect)


def animation(env):
    frame = env.object(0x30, 'animation-frame', fill=0)
    env.put(frame+0x1c, 37)
    frames = env.object(4, 'animation-frames', words=[frame])
    ani = env.object(0x18, 'animation', fill=0)
    env.put(ani+0xc, frames, 1)
    return ani


def maps(env):
    m = env.object(0x30, 'empty-property-map', fill=0)
    env.put(m+0x18, 17)
    return m


def world(env, mode=1):
    w = env.object(0x1c0, 'world', fill=0)
    owner = env.object(0x40, 'world-owner', fill=0)
    m = maps(env)
    grid = env.object(0x70, 'spatial-grid', fill=0)
    env.put(grid+0x64, 16, 16)
    env.put(owner+0x10, m, m)
    env.put(owner+0x24, grid)
    env.put(owner+0x2c, m)
    state = env.object(0x40, 'world-state', fill=0)
    env.put(w+0xc, owner)
    env.put(w+0x6c, state)
    env.put(w+0x170, mode)
    env.put(state+0x1c, 0x1357)
    return w, state


def player_setup(direction, detail_flag, linked, controller_count, seed):
    def setup(env):
        p, s = world(env)
        d = env.object(0x130, 'player-detail', fill=0x69)
        env.put(s+0x14, d)
        env.put(s+0x1c, 0x1390)
        env.put(d, direction, detail_flag)
        env.put(d+0x124, animation(env))
        env.put(d+0x12c, 0)
        if linked:
            other = env.object(0x70, 'linked-world', fill=0)
            os = env.object(0x20, 'linked-state', fill=0)
            ctrl = env.object(0x308, 'controller', fill=0x56)
            env.put(ctrl+0x20, controller_count)
            env.put(ctrl+0x2fc, 1)
            env.put(other+0x6c, os)
            env.put(os+0x18, ctrl)
            env.put(d+0x12c, other)
        env.put(p+8, seed & ~0x10)
        # Distinct old values make omitted clears and geometry stores observable.
        for i, off in enumerate((0xcc,0x104,0x118,0x11c,0x120,0x124,
                                 0x128,0x12c,0x130,0x134,0x148,0x14c)):
            env.put(p+off, (seed+i*0x10203)&0xffffffff)
        flags = env.object(0x10, 'global-flags', fill=0)
        env.put(flags+0xc, seed | 0x03000000)
        env.put(0x537204, flags)
        env.put(0x537e88, p)
        env.put(0x534e60, *[seed+i for i in range(6)])
        return {'receiver':p}
    return setup


def table_setup(index, lo, hi, nonzero, seed, stride=4):
    def setup(env):
        r = env.object(0x178, 'receiver', fill=0x3b)
        log = env.object(0x20, 'callback-log', fill=0)
        cb = callback(env, 'state-dispatch', log)
        data = env.object((hi-lo+1)*stride, 'dispatch-data', fill=0x67)
        for i in range(hi-lo+1):
            # Each slot has its own observable callback identity.
            env.put(data+i*stride, callback(env, 'slot-'+str(i), log) if nonzero else 0)
        fallback = env.object(4, 'fallback', words=[cb])
        env.put(0x5372a8, 0, 0, lo, hi, data, fallback, stride, 0, seed)
        base = env.object(4, 'base-dispatch-data', words=[cb])
        env.put(0x534910, 0, 0, index, index, base, fallback, 4, 0, seed)
        return {'receiver':r}
    return setup


def constructor_setup(mode, owner_value, seed, mapped=False):
    def setup(env):
        w,s = world(env, mode)
        env.put(w+8, seed & ~0x10)
        env.put(w+0x104, owner_value)
        env.put(w+0x164, seed)
        if mapped:
            m=env.get(env.get(w+0xc)+0x2c)
            buckets=env.object(17*4,'property-buckets',fill=0)
            env.put(m+0x14,buckets)
            for address in (0x526638,0x526620):
                key=env.cstr(address)
                h=0
                for byte in key.encode() if isinstance(key,str) else key:
                    h=(h*33+byte)&0xffffffff
                slot=buckets+(h%17)*4
                node=env.object(16,'property-node',words=[env.get(slot),h,address,animation(env)])
                env.put(slot,node)
        r = env.object(0x178, 'crab-bomb', fill=0x4b)
        return {'receiver':r, 'world':w}
    return setup


def logic_setup(state, seed):
    def setup(env):
        w,s=world(env)
        r=env.object(0x178,'controller',fill=0)
        log=env.object(0x20,'logic-log',fill=0)
        vt=env.object(0x30,'logic-vtable',fill=0)
        for off in (4,8,12,0x1c,0x20):
            env.put(vt+off, callback(env,'logic-'+str(off),log,1 if off in (4,8,12) else 0))
        for off in (0x1c,0x20):
            def observe(e,c):
                e.put(log,e.get(log)+1,c.receiver,e.get(s+0x18),
                      e.get(s+0x1c),e.get(c.receiver+0xc8))
                return seed
            env.put(vt+off,env.stub('logic-observer-'+str(off),'thiscall',0,observe))
        env.put(r+0xc8,seed)
        env.put(r,vt)
        env.put(r+0x10,s)
        env.put(s+0x18,r,state)
        # Real CString wrapper for original 4dc870 fallback.
        string=env.object(0x20,'cstring-record',fill=0)
        env.put(string,1,0,16)
        data=env.object(4,'cstring-slots',words=[string+12])
        env.put(0x537698,0,0,state,state,data,data,4,0,0)
        return {'world':w}
    return setup


def simple_setup(seed, tail=False):
    def setup(env):
        r=env.object(0x178,'simple-bomb',fill=0x39)
        env.put(r+0xc8,seed)
        if tail:
            log=env.object(0x20,'tail-log',fill=0)
            vt=env.object(0x30,'tail-vtable',fill=0)
            def effect(e,c):
                e.put(log,e.get(log)+1,c.receiver,e.get(c.receiver+0xc8))
                return 99
            env.put(vt+0x2c,env.stub('tail-callback','thiscall',0,effect))
            env.put(r,vt)
        return {'receiver':r}
    return setup


def explode_setup(kind, published, active, stopped, seed):
    def setup(env):
        w,s=world(env)
        r=env.object(0x178,'exploding-bomb',fill=0x63)
        env.put(r+0x12c,w)
        env.put(r+0x174,published)
        env.put(w+8,seed | 0x80)
        env.put(w+0x1a4,active)
        env.put(w+0x19c,stopped)
        if kind >= 0:
            ani=animation(env)
            env.put(w+0x190,ani)
            env.put(w+0x19c,1) # countdown path: returns existing disposition
            env.put(w+0x1a0,0)
            env.put(w+0x1ac,kind)
            env.put(w+0x19c,stopped)
            env.put(w+0x19c,2 if not stopped else stopped)
            env.put(w+0x1a0,0)
        return {'receiver':r}
    return setup


def enter_explode(seed, has_animation):
    def setup(env):
        w,s=world(env)
        r=env.object(0x178,'bomb-enter-explosion',fill=0x71)
        env.put(r+0x10,s)
        env.put(s+0x1c,seed)
        env.put(r+0x12c,w)
        env.put(r+0x170,animation(env) if has_animation else 0)
        env.put(w+8,seed)
        env.put(w+0x190,0x75ab)
        env.put(0x537668+0x18,0)
        return {'receiver':r}
    return setup


def numeric_setup(values, seed):
    def setup(env):
        r=env.object(0x80,'trajectory',fill=0x59)
        for off,val in zip((0x38,0x40,0x48,0x68,0x70,0x78),values):
            env.write(r+off,struct.pack('<d',val))
        env.write(r+0x50,struct.pack('<ddd',seed+0.25,-seed-0.5,seed+0.75))
        return {'receiver':r}
    return setup


def cases(random_source):
    seed=random_source.randrange(0x10000,0x7fffffff)
    for fn in (0x41fce0,0x41fe80):
        yield Case('null player '+hex(fn),fn,lambda e:e.put(0x537e88,0))
        for direction,flag,linked,count in itertools.product((0,1), (0,1), (0,1),(-1,1)):
            yield Case(f'player {fn:x} {direction}/{flag}/{linked}/{count}',fn,player_setup(direction,flag,linked,count,seed))
    def no_state(e):
        p=e.object(0x70,'player-no-state',fill=0); e.put(0x537e88,p)
    yield Case('leave null state',0x41fe80,no_state)
    def other_state(e):
        p,s=world(e);e.put(0x537e88,p)
    yield Case('leave other state',0x41fe80,other_state)
    for index in (-3,0,1,5):
        for present in (False,True):
            yield Case(f'dispatch {index}/{present}',0x431df0,table_setup(index,0,2,present,seed),receiver=lambda t:t['receiver'],arguments=(index,))
    def state_zero(e):
        t=constructor_setup(1,0,seed)(e)
        w=t['world']; state=e.get(w+0x6c)
        e.put(state+0x1c,0)
        grid=e.get(e.get(w+0xc)+0x24)
        tiles=e.object(0x94,'tilemap',fill=0)
        row=e.object(4,'tile-row',words=[0])
        data=e.object(4,'tile-data',words=[0xffffffff])
        e.put(tiles+0x20,data,row)
        e.put(tiles+0x30,1,1)
        e.put(grid+0x5c,tiles)
        e.put(0x537668+0x18,0)
        return t
    yield Case('logic state zero constructs and publishes',0x431cd0,state_zero,arguments=(lambda t:t['world'],))
    for state in (1,28,29,30,31,1000,0xffffffff):
        yield Case(f'logic state {state}',0x431cd0,logic_setup(state,seed),arguments=(lambda t:t['world'],))
    for mode,owner,mapped in itertools.product((0,1),(0,11),(False,True)):
        yield Case(f'constructor {mode}/{owner}/{mapped}',0x4320d0,constructor_setup(mode,owner,seed,mapped),receiver=lambda t:t['receiver'],arguments=(lambda t:t['world'],))
    for fn in (0x432550,0x432560):
        for value in (0,1,seed,0xffffffff):
            yield Case(f'set active {fn:x}/{value}',fn,simple_setup(value,fn==0x432560),receiver=lambda t:t['receiver'])
    for flag in (False,True):
        yield Case(f'enter explosion animation {flag}',0x432460,enter_explode(seed,flag),receiver=lambda t:t['receiver'])
    for k,p,a,s in itertools.product((-1,1,7),(0,1),(0,1),(0,3)):
        yield Case(f'explode {k}/{p}/{a}/{s}',0x4324e0,explode_setup(k,p,a,s,seed),receiver=lambda t:t['receiver'])
    vectors=[(0.,0.,0.,0.,0.,0.),(1.,0.,3.,0.,0.,0.),(1.,0.,3.,20.,2.,7.),(-2.,0.,5.,100.,10.,-3.),(0.,0.,0.,0.,2000.,0.),(0.,0.,0.,0.,2000.0000000001,0.),(0.,0.,0.,0.,1999.9999999999,0.)]
    vectors.extend([
        (float('inf'),0.,1.,0.,0.,0.),
        (float('-inf'),0.,1.,0.,0.,0.),
        (float('nan'),0.,1.,0.,0.,0.),
        (1e-310,0.,-1e-310,1e-310,1e-310,1e-310),
        (1e150,0.,-1e150,1e150,-1e150,1e150),
        (0.,0.,0.,float('nan'),0.,0.),
        (0.,0.,float('nan'),0.,0.,0.),
    ])
    for i in range(24):
        vectors.append(tuple(random_source.uniform(-4000,4000) for _ in range(6)))
    for i,values in enumerate(vectors):
        for arg in (0,1,-1,17,-23,0x40000000,0x80000000):
            yield Case(f'trajectory {i}/{arg}',0x432250,numeric_setup(values,seed),receiver=lambda t:t['receiver'],arguments=(arg,))

    # With zero horizontal velocity and argument, the first computed root is
    # sqrt(2000*abs(source_z)). These neighbors straddle its 0.1 comparison.
    threshold=0.000005
    for sign in (-1.,1.):
        for z in (math.nextafter(threshold,0.),threshold,
                  math.nextafter(threshold,math.inf)):
            yield Case(f'trajectory root boundary {sign}/{z.hex()}',0x432250,
                       numeric_setup((0.,-37.,0.,0.,0.,sign*z),seed),
                       receiver=lambda t:t['receiver'],arguments=(0,))
    # The final abs operates on a wrapping signed32 doubling, including its
    # negative-minimum result, rather than on a mathematical unbounded integer.
    for arg in (0x3fffffff,0x40000001,0x7fffffff,0x80000001,0xc0000000,0xffffffff):
        yield Case(f'trajectory doubled argument boundary {arg:x}',0x432250,
                   numeric_setup((123.,-41.,-17.,-9.,55.,23.),seed),
                   receiver=lambda t:t['receiver'],arguments=(arg,))
    # Original stores and its 53-bit x87 precision determine whether adding a
    # unit to a large source survives the subsequent subtraction.
    for source in (float(2**53),math.nextafter(float(2**53),math.inf),-float(2**53)):
        for arg in (-1,1):
            yield Case(f'trajectory cancellation {source.hex()}/{arg}',0x432250,
                       numeric_setup((3.,-43.,-7.,source,11.,13.),seed),
                       receiver=lambda t:t['receiver'],arguments=(arg,))
    for sign in (-1.,1.):
        yield Case(f'trajectory signed zero {sign}',0x432250,
                   numeric_setup((sign*0.,-47.,sign*0.,sign*0.,sign*0.,sign*0.),seed),
                   receiver=lambda t:t['receiver'],arguments=(0,))

    for i in range(40):
        varied=random_source.getrandbits(32)
        for fn in (0x41fce0,0x41fe80):
            yield Case(f'varied player {fn:x}/{i}',fn,
                       player_setup(random_source.choice((0,1,-1)),
                                    random_source.choice((0,1,0xffffffff)),
                                    i%2,random_source.choice((0,1,2,0x80000000)),varied))
    for stride in (4,8,12):
        for lo in (-7,3):
            for offset in (-1,0,1,2,3):
                for present in (False,True):
                    index=lo+offset
                    yield Case(f'strided dispatch {stride}/{lo}/{offset}/{present}',
                               0x431df0,table_setup(index,lo,lo+2,present,
                                                  random_source.getrandbits(32),stride),
                               receiver=lambda t:t['receiver'],arguments=(index,))
    for i in range(24):
        varied=random_source.getrandbits(32)
        yield Case(f'varied constructor {i}',0x4320d0,
                   constructor_setup(i%3,0 if i%2 else varied,varied,bool(i%2)),
                   receiver=lambda t:t['receiver'],arguments=(lambda t:t['world'],),
                   initial_stack=((-0x60,random_source.randbytes(0x60)),))
    for i in range(24):
        state=random_source.choice((1,28,29,30,31,999,1000,1001,0x80000000,0xffffffff))
        yield Case(f'varied logic {i}/{state}',0x431cd0,
                   logic_setup(state,random_source.getrandbits(32)),
                   arguments=(lambda t:t['world'],))
    for i in range(12):
        yield Case(f'varied explosion entry {i}',0x432460,
                   enter_explode(random_source.getrandbits(32),bool(i%2)),
                   receiver=lambda t:t['receiver'])
    for i in range(20):
        yield Case(f'varied activation {i}',0x432560,
                   simple_setup(random_source.getrandbits(32),True),
                   receiver=lambda t:t['receiver'])
