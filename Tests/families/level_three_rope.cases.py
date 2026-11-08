"""Independent original-derived rope behavior and state-publication cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def double(env, address, value):
    env.write(address, struct.pack('<d', value))


def recorder(env, log, code, mutate=None, argc=0):
    def effect(e, call):
        count = e.get(log)
        at = log + 4 + count * 24
        e.put(at, code, call.receiver, *(list(call.arguments) + [0, 0])[:2])
        if call.receiver:
            e.put(at + 16, e.get(call.receiver + 0x14), e.get(call.receiver + 0x18))
        e.put(log, count + 1)
        if mutate:
            mutate(e, call)
        return code ^ 0x3c3c
    return env.stub(f'rope-observe-{code}', 'thiscall', argc, effect)


def base(env, fill=0x59):
    obj = env.object(0x178, 'controller', fill=fill)
    state = env.object(0xc0, 'state', fill=0x37)
    env.put(obj + 0x10, state)
    return obj, state


def dictionary(env, root=0):
    env.put(0x537680, root)


def ctor_setup(speed, period, image, fill, idle=0):
    def setup(env):
        obj, state = base(env, fill)
        arg = env.object(0x178, 'game-object', fill=0x26)
        manager = env.object(0x18, 'resource-manager')
        resource = env.object(0x20, 'resources')
        env.put(resource + 0x14, 0, 7)  # empty bucket array, seven buckets
        env.put(manager + 0x10, resource, resource)
        env.put(arg + 0xc, manager)
        env.put(arg + 0x6c, state)
        env.put(arg + 0x64, image)
        env.put(arg + 0x148, period)
        env.put(state + 0xbc, speed)
        env.put(state + 0x1c, 0x1234abcd)
        env.put(0x513e10, 0x13572468, 0x24681357, 0x89abcdef, 0x10293847)
        idle_tree(env, idle)
        return {'obj': obj, 'arg': arg, 'state': state}
    return setup


def aliased_ctor_setup(distance, lo, hi, speed, hit_key=True, global_arg=False):
    """Constructor whose argument object overlaps the rope at a chosen distance.

    The original 0x4c7970 lookup stores words at argument+0x16c/0x170/0x174.
    With the rope placed `distance` bytes after the argument, those stores land
    in the middle of the rope between its two zeroing passes, so a missing or
    misplaced second zeroing store changes final memory.
    """
    def setup(env):
        if global_arg:
            # The lookup's stores at argument+0x16c/0x170 hit globals
            # 0x513e18/0x513e1c, which the constructor re-reads afterwards.
            arg = 0x513cac
            obj = env.object(0x178, 'rope', fill=0x69)
        else:
            big = env.object(distance + 0x160, 'aliased-game-object', fill=0x26)
            arg, obj = big, big + distance
            env.write(obj, b'\x69' * 0x140)
        state = env.object(0xc0, 'state', fill=0x37)
        manager = env.object(0x18, 'resource-manager')
        plain = env.object(0x20, 'plain-resource')
        env.put(plain + 0x14, 0, 7)
        resource = env.object(0x20, 'rope-resource')
        env.put(resource + 0x14, 0, 1)
        if hit_key:
            key = env.cstr(0x52313c)
            name = env.object(len(key) + 1, 'rope-key', data=key + b'\0')
            frames = env.object(64, 'rope-frames', words=[0xa1b2c3d4 ^ (i * 0x1111) for i in range(16)])
            found = env.object(0x70, 'rope-found', fill=0x55)
            env.put(found + 0x14, frames)
            env.put(found + 0x64, lo, hi)
            node = env.object(0x10, 'rope-node')
            env.put(node, 0, 0, name, found)
            bucket = env.object(4, 'rope-bucket', words=[node])
            env.put(resource + 0x14, bucket, 1)
        env.put(manager + 0x10, resource, plain)
        env.put(arg + 0xc, manager)
        env.put(arg + 0x6c, state)
        env.put(arg + 0x64, 0)
        env.put(state + 0xbc, speed)
        env.put(env_ctor_globals := 0x513e10, 0x13572468, 0x24681357, 0x89abcdef, 0x10293847)
        idle_tree(env, 0x2137)
        return {'obj': obj, 'arg': arg, 'state': state}
    return setup


def observed_ctor_setup(offset, mode, low_global=0x5a5a0001, high_global=0x6b6b0002):
    """Make the 0x4c7970 lookup read one rope word between the two passes.

    The looked-up resource lives inside the rope so that its range words
    (+0x64 low, +0x68 high) alias the rope word at `offset`.  The lookup stores
    the low word into argument+0x16c and takes a different branch when the high
    word is negative, so a misplaced early store to `offset` changes the
    constructor's final memory.
    """
    def setup(env):
        big = env.object(0x500, 'rope-arena', fill=0x44)
        obj = big + 0x180
        env.write(obj, b'\x69' * 0x140)
        arg = env.object(0x178, 'game-object', fill=0x26)
        state = env.object(0xc0, 'state', fill=0x37)
        manager = env.object(0x18, 'resource-manager')
        plain = env.object(0x20, 'plain-resource')
        env.put(plain + 0x14, 0, 7)
        resource = env.object(0x20, 'rope-resource')
        key = env.cstr(0x52313c)
        name = env.object(len(key) + 1, 'rope-key', data=key + b'\0')
        found = obj + offset - (0x64 if mode == 'lo' else 0x68)
        node = env.object(0x10, 'rope-node')
        env.put(node, 0, 0, name, found)
        bucket = env.object(4, 'rope-bucket', words=[node])
        env.put(resource + 0x14, bucket, 1)
        frames = env.object(64, 'rope-frames', words=[0xa1b2c3d4 ^ (i * 0x1111) for i in range(16)])
        array_at = found + 0x14
        env.put(array_at, frames)
        env.put(obj + offset, 0x80000005)
        env.put(manager + 0x10, resource, plain)
        env.put(arg + 0xc, manager)
        env.put(arg + 0x6c, state)
        env.put(arg + 0x64, 0)
        env.put(state + 0xbc, 777)
        env.put(0x513e10, 0x13572468, 0x24681357, low_global, high_global)
        idle_tree(env, 0x2137)
        return {'obj': obj, 'arg': arg, 'state': state}
    return setup


def idle_tree(env, result):
    dictionary(env)
    if result:
        node = env.object(0x14, 'idle-tree-node')
        name = env.object(8, 'idle-key', data=b'LS_IDLE\0')
        env.put(node, node, node, 0, name, result)
        dictionary(env, node)


def dispatch_setup(state_id):
    def setup(env):
        obj, state = base(env)
        game = env.object(0x178, 'game')
        table = env.object(0x24, 'controller-vtable')
        log = env.object(512, 'callbacks', fill=0)
        env.put(obj, table)
        env.put(game + 0x6c, state)
        env.put(state + 0x18, obj, state_id)
        for offset in (4, 8, 12, 16, 28, 32):
            env.put(table + offset, recorder(env, log, offset, argc=1 if offset in (4, 8, 12) else 0))
        chars = env.object(32, 'string-storage')
        env.put(chars, 1, 0, 16)
        wrapper = env.object(4, 'state-string', words=[chars + 12])
        env.put(0x5376a0, state_id, state_id, wrapper, wrapper, 4, wrapper, 0)
        return {'obj': obj, 'game': game}
    return setup


def table_setup(index, lo, hi, stride, callback, growth_mode=0):
    def setup(env):
        obj, state = base(env)
        table = env.object((hi-lo+1)*stride, 'state-table', fill=0x71)
        fallback = env.object(4, 'fallback-entry')
        log = env.object(512, 'callbacks', fill=0)
        for i in range(hi-lo+1):
            env.put(table+i*stride, recorder(env, log, i+1) if callback else 0)
        env.put(0x534824, 0, lo, hi, table, fallback, stride, 0x33445566, 0x11223344)
        # Valid original RTTI metadata for the zero callback path.
        vt = env.object(12, 'rtti-vtable')
        locator = env.object(16, 'rtti-locator')
        info = env.object(8, 'rtti-info', fill=0x43)
        env.put(vt, locator)
        env.put(locator + 12, info)
        env.put(obj, vt + 4)
        if growth_mode:
            def grow(e, call):
                old, size = call.arguments
                if growth_mode == 2:
                    return 0
                new = e.object(size, 'grown-state-table')
                e.write(new, e.read(old, min((hi-lo+1)*stride, size)))
                e.release(old)
                # Make upper grow's new slot nonzero AFTER zeroing by choosing
                # an alias: scratch at global +0x20 is the newly cleared slot.
                return new
            env.override(0x4a9070, grow)
        return {'obj': obj}
    return setup


def update_setup(mode, ticks, initial, factor):
    def setup(env):
        obj, state = base(env)
        log = env.object(512, 'update-log', fill=0)
        env.put(obj+0x1c, 91)
        env.put(state+0x1c, 92 if mode == 'mismatch' else 91)
        final = recorder(env, log, 3)
        def change(e, call):
            e.put(obj+0x14, final)
            e.put(obj+0x18, 0x11112222)
            e.put(0x537210, ticks ^ 0x80000000)
            double(e, obj+0x48, initial + 0.75)
        first = recorder(env, log, 1, change if mode == 'mutate' else None)
        second = recorder(env, log, 2)
        env.put(obj+0x14, 0 if mode == 'none' else second, 0 if mode == 'only' else first)
        env.put(obj+0xe8, 1)  # original integrator's documented disabled body
        double(env, obj+0x48, initial)
        double(env, 0x50b088, factor)
        env.put(0x537210, ticks)
        return {'obj': obj}
    return setup


def frame_setup(value, match, active, anim, seed_words):
    def setup(env):
        obj, _ = base(env)
        target = env.object(0x178, 'rope-target', fill=0x62)
        actor = env.object(0x178, 'actor', fill=0x45)
        ast = env.object(0x144, 'actor-state', fill=0x28)
        player = env.object(0x138, 'player', fill=0x36)
        env.put(obj+0xc, target)
        env.put(obj+0x2c, target)
        double(env, obj+0x88, value)
        env.put(0x537e88, actor)
        env.put(actor+0x6c, ast)
        env.put(ast+0x14, player)
        env.put(ast+0x1c, 5007 if active else 5006)
        env.put(player+0x134, target if match else obj)
        env.put(player, seed_words[0] & 1)
        for i in range(-119, 61):
            env.put(0x522f08 + 8*i, (seed_words[1]+i*73)&0xffffffff, (seed_words[2]-i*31)&0xffffffff)
        if anim == 'none':
            env.put(target+0x170, 0)
        else:
            animation = env.object(0x6c, 'animation')
            frames = env.object(1024, 'frames', fill=0x72)
            arr = frames+480  # absolute indexing, including negative frames
            for i in range(-119, 121):
                env.put(arr+4*i, (seed_words[3] ^ (i*0x10203))&0xffffffff)
            env.put(animation+0x14, arr)
            lo, hi = {'inside': (-119, 120), 'below': (121, 130), 'above': (-130, -120), 'edge': (60, 60)}[anim]
            env.put(animation+0x64, lo, hi)
            env.put(target+0x170, animation)
        return {'obj': obj}
    return setup


def construction_dispatch(env):
    t = ctor_setup(1234567, 7, 0, 0x69, 0x2137)(env)
    env.put(t['state'] + 0x1c, 0)
    t['game'] = t['arg']
    return t


def inverted_table(env):
    obj, state = base(env)
    log = env.object(512, 'inverted-callbacks', fill=0)
    callback = recorder(env, log, 77)
    table = env.object(4, 'inverted-table', words=[callback])
    fallback = env.object(4, 'inverted-fallback', words=[callback])
    env.put(0x534824, 0, 1, 0xffffffff, table, fallback, 0, 0, 0)
    def resize(e, call):
        # Zero-width table still has a mapped callback word; both original
        # shift/clear lengths are zero while the signed bounds grow twice.
        new = e.object(4, 'zero-width-grown', data=e.read(call.arguments[0], 4))
        e.release(call.arguments[0])
        return new
    env.override(0x4a9070, resize)
    return {'obj': obj}


def cases(random_source):
    yield Case('dispatch constructs and publishes controller', 0x403100, construction_dispatch, arguments=(lambda t:t['game'],))
    yield Case('inverted zero-width table grows twice', 0x4035a0, inverted_table, receiver=lambda t:t['obj'], arguments=(0,))
    for state in (1, 28, 29, 30, 31, 999, 1000, -1):
        yield Case(f'dispatch state {state}', 0x403100, dispatch_setup(state), arguments=(lambda t:t['game'],))
    for period in (0, 1, -1, 7, -7, 1500, 60001, 0x7fffffff, -0x80000000):
        for image in (0, 0xf96, 3):
            for speed in (0, 1, -1, 0x7fffffff, -0x80000000, 1234567):
                yield Case(f'construct period {period} image {image} speed {speed}', 0x4031c0, ctor_setup(speed,period,image,0x69,0x2137), receiver=lambda t:t['obj'], arguments=(lambda t:t['arg'],))
    for distance in (0xd0, 0xdc, 0xe8, 0xf4, 0x104, 0x110, 0x118, 0x124):
        for lo, hi, speed in ((3, 9, 1234567), (0, 5, -77), (2, 2, 0x7fffffff)):
            yield Case(f'aliased construct {distance:#x} frames {lo}-{hi} speed {speed}', 0x4031c0,
                       aliased_ctor_setup(distance, lo, hi, speed), receiver=lambda t:t['obj'], arguments=(lambda t:t['arg'],))
    for lo, hi, speed in ((3, 9, 1234567), (0, 5, -77), (7, 12, 99)):
        yield Case(f'global-aliased construct frames {lo}-{hi}', 0x4031c0,
                   aliased_ctor_setup(0, lo, hi, speed, global_arg=True), receiver=lambda t:t['obj'], arguments=(lambda t:t['arg'],))
    for offset, mode, lo_g, hi_g in ((0x48,'lo',0,0), (0x88,'lo',0,0), (0x58,'lo',0,0), (0x7c,'lo',0,0), (0x94,'lo',0,0),
                                     (0x54,'hi',0,0), (0x64,'hi',0,0),
                                     (0x10c,'lo',0x30000001,0x50000002), (0x118,'lo',0x50000003,0x30000004)):
        extra = {} if offset < 0x100 else {'low_global': lo_g, 'high_global': hi_g}
        yield Case(f'observed construct {offset:#x} {mode}', 0x4031c0,
                   observed_ctor_setup(offset, mode, **extra), receiver=lambda t:t['obj'], arguments=(lambda t:t['arg'],))
    for index in (-4, 0, 1, 2, 4):
        for callback in (False, True):
            yield Case(f'state table {index} callback {callback}', 0x4035a0, table_setup(index,0,2,12,callback), receiver=lambda t:t['obj'], arguments=(index,))
    for mode in ('none','only','mismatch','both','mutate'):
        for ticks, initial, factor in ((0,0.0,0.001),(0xffffffff,-1.25,0.001),(0x80000000,12.5,-0.003),(random_source.getrandbits(32),random_source.uniform(-30,30),0.001)):
            yield Case(f'update {mode} {ticks}',0x403850,update_setup(mode,ticks,initial,factor),receiver=lambda t:t['obj'],arguments=(0xa5a5a5a5,))
    values = (-240.75,-120.5,-119.0,-60.2,-1.9,-0.0,0.9,1.1,58.9,59.0,59.99,60.0,60.9,61.0,118.9,119.0,120.0,239.9,2147483647.0,-2147483648.0)
    for i,value in enumerate(values):
        for match, active in ((False,True),(True,False),(True,True)):
            anim = ('none','inside','below','above','edge')[i%5]
            words = tuple(random_source.getrandbits(32) for _ in range(4))
            yield Case(f'frame {value} match {match} active {active} anim {anim}',0x4038d0,frame_setup(value,match,active,anim,words),receiver=lambda t:t['obj'])
    for integer in range(-119, 121):
        words = tuple(random_source.getrandbits(32) for _ in range(4))
        # Cover every signed remainder and both rectangle halves independently
        # of random seed, including absolute negative animation indices.
        yield Case(f'frame exhaustive integer {integer}', 0x4038d0,
                   frame_setup(float(integer), True, True, 'inside', words),
                   receiver=lambda t:t['obj'])
    for result in (0,1,0x7fffffff,0xffffffff):
        def idle(env, result=result):
            obj,state = base(env)
            env.put(state+0x1c,0xdeadbeef)
            idle_tree(env,result)
            return {'obj':obj}
        yield Case(f'idle {result}',0x465450,idle,receiver=lambda t:t['obj'])
