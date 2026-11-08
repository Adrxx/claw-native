"""Original-only cases for observed Level 1 actor dispatch."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate


def words(value):
    return struct.unpack('<II', struct.pack('<d', value))


def physics(axes, dt=1.0, paused=0, status=0):
    def setup(env):
        env.entry_x87_status(status)
        obj = env.object(0xf0, 'physics', fill=0x59)
        env.write(obj, struct.pack('<d', 17.25))
        env.put(obj + 0xa0, paused)
        for i, (accel, speed, pos, low, high, step, cap) in enumerate(axes):
            for offset, value in ((0x10, accel), (0x28, speed), (0x40, pos),
                                  (0x58, low), (0x70, high), (0xc0, step), (0xd8, cap)):
                env.write(obj + offset + 8*i, struct.pack('<d', value))
        return obj
    return Case(f'physics {axes} dt={dt} pause={paused} incoming-sw={status:#x}', 0x403b40, setup,
                receiver=lambda t: t, arguments=words(dt))


def ambient(function, state=0, resource=True, world=True, manager=True,
            same=False, rect=(0, -13, 0, 27), timed=0, bounds=11,
            allocation_fail=False, sound=True, linked=True, mutate=False):
    def setup(env):
        obj = env.object(0x230, 'actor', fill=0xa6)
        logic = env.object(0x180, 'logic', fill=0xb7)
        root = env.object(0x60, 'world', fill=0)
        mgr = env.object(0x30, 'sound-manager', fill=0)
        res = env.object(0x20, 'resource')
        env.put(obj + 0x6c, logic)
        env.put(obj + 8, 0x842202a2)
        env.put(obj + 0x40, 0x39020400)
        env.put(logic + 0x10, 0x402ca0 if same else 0x402e20)
        env.put(logic + 0x1c, state)
        env.put(logic + 0x2c, *(v & 0xffffffff for v in rect))
        env.put(obj + 0x184, res if resource else 0)
        env.put(0x5371fc, root if world else 0)
        env.put(root + 0x5c, mgr if manager else 0)
        env.put(mgr + 4, 0x6a5b4c3d)
        free = env.object(12, 'free-list-node', fill=0)
        env.put(mgr + 0x18, free)
        env.put(mgr + 0x14, 2)  # list count, retained nodes avoid RemoveAll
        source = env.object(0x20, 'sound-source')
        context = env.object(0x80, 'sound-context', fill=0)
        env.put(source + 0x10, context)
        env.put(res + 0x10, source)
        env.put(obj + 0x104, 0x1234abcd)
        env.put(obj + 0x118, 7, timed & 0xffffffff, 13, 29)
        env.put(obj + 0x128, 0xffffffd3, 19, 71, 103)
        env.put(obj + 0x138, 0xffffffef, bounds & 0xffffffff, 61, 97)
        env.put(obj + 0x4c, 147, 259)
        record = env.object(80, 'callback-record')
        def copy_rect(e, call):
            dst, src = call.arguments
            e.put(record, call.receiver, dst, src, e.get(obj + 8), e.get(obj + 0x40), e.get(logic + 0x1c))
            e.write(dst, e.read(src, 16))
            if mutate:
                e.put(obj + 0x104, 0x76543210)
                e.put(obj + 0x138, 101, 103, 107, 109)
            return 1
        def set_rect(e, call):
            e.put(call.arguments[0], *call.arguments[1:])
            e.put(record + 24, *call.arguments)
            return 1
        env.override(0x546d58, copy_rect)
        env.override(0x546d5c, set_rect)
        env.override(0x4a3050, lambda e, c: 17)
        if allocation_fail:
            env.override(0x4f63ec, allocate(fail=True))
        if state == 30:
            active = env.object(0x48, 'active-sound', fill=0xc9)
            vtable = env.object(4, 'active-vtable')
            node = env.object(12, 'active-list-node')
            prev = env.object(12, 'previous-list-node')
            nxt = env.object(12, 'next-list-node')
            env.put(active, vtable, source if sound else 0)
            env.put(active + 0x3c, node if linked else 0)
            env.put(node, nxt, prev, active)
            env.put(logic + 0x168, active if resource else 0)
            def destroy(e, call):
                e.put(record + 48, call.receiver, call.arguments[0], e.get(logic + 0x1c),
                      e.get(logic + 0x168), e.get(active + 0x14), e.get(mgr + 0x18))
                return 0xdebca987
            env.put(vtable, env.stub('sound deleting destructor', 'thiscall', 1, destroy))
        return obj
    label = f'ambient {function:x} state={state} res={resource} world={world} manager={manager} same={same} rect={rect} timed={timed} bounds={bounds} fail={allocation_fail} sound={sound} linked={linked} mutate={mutate}'
    return Case(label, function, setup, arguments=(lambda t: t,))


def rectangle(function, values, present=True, alias=False):
    def setup(env):
        obj = env.object(0x230, 'actor', fill=0x49)
        shape = env.object(0x50, 'shape', fill=0x67)
        output = shape + 0x18 if alias else env.object(16, 'output', fill=0xe3)
        env.put(shape + 0x18, *(v & 0xffffffff for v in values))
        env.put(obj + 0x174, shape if present else 0)
        return obj, output
    return Case(f'rectangle {function:x} {values} present={present} alias={alias}', function, setup,
                receiver=lambda t: t[0], arguments=((lambda t: t[1]),) if function == 0x4061e0 else ())


def lookup(function, key, found, collision=False):
    def setup(env):
        obj = env.object(0x40, 'lookup-owner', fill=0x67)
        map_obj = obj
        if function == 0x4062e0:
            p1 = env.object(0x20, 'owner-link')
            p2 = env.object(0x30, 'level-link')
            map_obj = env.object(0x30, 'map-owner')
            env.put(obj + 4, p1)
            env.put(p1 + 0xc, p2)
            env.put(p2 + 0x2c, map_obj)
        keyp = env.object(len(key)+1, 'lookup-key', data=key+b'\0')
        table = env.object(4*7, 'hash-buckets', fill=0)
        env.put(map_obj + 0x14, table if found or collision else 0, 7)
        hash_value = 0
        for b in key:
            hash_value = (hash_value*33 + (b if b < 128 else b-256)) & 0xffffffff
        first = env.object(16, 'hash-first')
        second = env.object(16, 'hash-second')
        other = env.object(8, 'different-key', data=b'wrong!\0')
        env.put(table + 4*(hash_value % 7), first)
        env.put(first, second if collision else 0, 0x12345678, other if collision else keyp, 0x97352ac1)
        env.put(second, 0, 0x456789ab, keyp if found else other, 0xf835ab29)
        return obj, keyp
    return Case(f'lookup {function:x} {key!r} found={found} collision={collision}', function,
                setup, receiver=lambda t: t[0], arguments=(lambda t: t[1],))


def cases(random_source):
    for function in (0x402ca0, 0x402cc0):
        for opts in ({'state':5}, {'resource':False}, {'world':False}, {'manager':False},
                     {'same':True}, {'rect':(3,7,0,31)}, {'rect':(-3,7,5,31)},
                     {'timed':3}, {'timed':-1}, {'bounds':0}, {'bounds':-1},
                     {'allocation_fail':True}, {'timed':3,'allocation_fail':True},
                     {'mutate':True, 'timed':3}):
            yield ambient(function, **opts)
    for opts in ({'state':5}, {'state':30,'resource':False}, {'resource':False},
                 {'world':False}, {'manager':False}, {}, {'allocation_fail':True}):
        yield ambient(0x402e20, **opts)
    for sound in (False, True):
        for linked in (False, True):
            yield ambient(0x402e20, state=30, sound=sound, linked=linked)
    profiles = []
    for accel in (-20., -2., 0., 2., 20.):
        for speed in (-10., -1., 0., 1., 10.):
            for low, high, step in ((-100.,100.,.25), (-.5,.5,100.)):
                profiles.append((accel,speed,0.,low,high,step,3.))
    profiles += [(2.,1.,0.,-100.,100.,-2.,100.), (0.,0.,0.,-100.,100.,100.,100.), (0.,1.,0.,-1.,1.,1.,1.)]
    for profile in profiles:
        yield physics([profile]*3)
    yield physics([profiles[0]]*3, paused=1)
    # Independent of the random seed: final FCOMP must publish its own
    # condition bits while preserving inherited exception flags. The dt=0
    # shape includes the native base constructor's zero-motion physics call.
    zero_motion = (0., 0., 0., -2147483646., 2147483646., 2147483646., 2147483646.)
    status_profiles = [
        ([zero_motion]*3, 0., 0),
        ([(0., 1., 0., -100., 100., 100., 2.)]*3, 1., 0),
        ([(0., 1., 0., -100., 100., 100., 1.)]*3, 1., 0),
        ([(0., 2., 0., -100., 100., 100., 1.)]*3, 1., 0),
        ([zero_motion]*3, .125, 1),
        ([(2., 1., 0., -100., 100., .25, 3.)]*3, 1., 0),
        ([(-2., -1., 0., -100., 100., .25, 3.)]*3, 1., 0),
        ([(2., 1., 0., -.5, .5, 100., 3.)]*3, 1., 0),
        ([(-2., -1., 0., -.5, .5, 100., 3.)]*3, 1., 0),
        ([(.1, .3, .7, -100., 100., 100., 3.)]*3, .1, 0),
        ([(0., 0., 0., -100., 100., 100., 3.),
          (2., 1., 0., -.5, .5, .25, 3.),
          (-2., -1., 0., -.5, .5, .25, 3.)], .125, 0),
        ([(0., 0., 0., -100., 100., 100., 3.),
          (0., 0., 0., -100., 100., 100., 3.),
          (0., 1., 0., -100., 100., 100., float('nan'))], 1., 0),
    ]
    for status in (0, 0x20, 0x21):
        for axes, dt, paused in status_profiles:
            yield physics(axes, dt=dt, paused=paused, status=status)
    for _ in range(24):
        axes = [(random_source.uniform(-5,5),random_source.uniform(-8,8),random_source.uniform(-2,2),
                 -4.,4.,random_source.choice((.25,2.,100.)),random_source.uniform(-1,6)) for _ in range(3)]
        yield physics(axes, dt=random_source.choice((0., .125, .5, 1.5, -1.)))
    for flags in (0, 1, 2, 0xfffffffe):
        def setup(env, flags=flags):
            obj = env.object(0x230, 'copy-owner', fill=0x63)
            target = env.object(0x150, 'copy-target', fill=0xa7)
            state = env.object(0x44, 'copy-state')
            env.put(obj + 0xc, target)
            env.put(obj + 0x12c, state)
            env.put(state + 0x40, flags)
            env.put(obj + 0x210, 0xffffffef, 23, 51, 79)
            return obj
        yield Case(f'copy bounds flags {flags:x}', 0x405000, setup, receiver=lambda t:t)
    for mask in range(8):
        def setup(env, mask=mask):
            obj = env.object(0x150, 'flip-owner', fill=0x3b)
            for i,offset in enumerate((0x118,0x128,0x138)):
                env.put(obj + offset, 0x80000000 if mask & (1 << i) else (0xfffffff1+i),
                        0x12345678+i, 0x80000000 if i == 1 else 31+i, 0x98765432+i)
            return obj
        yield Case(f'flip sentinel mask {mask}', 0x4060b0, setup, receiver=lambda t:t)
    values = [(3,7,19,31), (-17,23,53,-71), (0,1,1,0),
              (0x7fffffff,0x80000000,0xffffffff,2)]
    values += [tuple(random_source.getrandbits(32) for _ in range(4)) for _ in range(8)]
    for function in (0x4061e0,0x406290):
        yield rectangle(function, values[0], present=False)
        for value in values:
            yield rectangle(function,value)
        if function == 0x4061e0:
            yield rectangle(function,values[0],alias=True)
    for function in (0x4061b0,0x4062e0):
        for key in (b'', b'CaptainClaw', b'\x80\xffz'):
            for found,collision in ((False,False),(True,False),(True,True),(False,True)):
                yield lookup(function,key,found,collision)
