"""Original-only probes for the Level 2 end gem closure."""
import struct
from clawparity.cases import Case


def f64(env, address, value):
    env.write(address, struct.pack('<d', value))


def common(env):
    obj = env.object(0x500, 'gem-object', fill=0)
    logic = env.object(0x200, 'logic', fill=0)
    world = env.object(0x200, 'world', fill=0)
    images = env.object(0x80, 'images', fill=0)
    animations = env.object(0x80, 'animations', fill=0)
    env.put(obj + 0xc, world)
    env.put(obj + 0x6c, logic)
    env.put(world + 0x10, images)
    env.put(world + 0x14, images)
    env.put(world + 0x28, images)
    env.put(world + 0x2c, animations)
    env.put(images + 0x18, 17)
    env.put(animations + 0x18, 17)
    env.put(0x537e88, 0)
    env.put(0x52a190, 0)
    env.put(0x538418, 1)
    return {'object': obj, 'logic': logic, 'world': world}


def callback(env, name, argc=0, result=0, convention='thiscall', observer=None):
    log = env.object(0x40, name + '-log', fill=0)
    def effect(env, call):
        n = env.get(log)
        env.put(log, n + 1, call.receiver, *call.arguments)
        if observer is not None:
            observer(env, call, log)
        return result
    return env.stub(name, convention, argc, effect)


def aim_setup(position, acceleration, initial):
    def setup(env):
        t = common(env)
        obj = t['object']
        for offset, value in zip((0x68, 0x70, 0x78), position):
            f64(env, obj + offset, value)
        for offset, value in zip((0x38, 0x40, 0x48), acceleration):
            f64(env, obj + offset, value)
        for offset, value in zip((0x50, 0x58, 0x60), initial):
            f64(env, obj + offset, value)
        return t
    return setup


def tick_setup(x, y, vy, target):
    def setup(env):
        t = common(env)
        obj = t['object']
        other = env.object(0x20, 'published-object', fill=0x93)
        env.put(obj + 0x12c, other)
        f64(env, obj + 0x68, x)
        f64(env, obj + 0x70, y)
        f64(env, obj + 0x58, vy)
        env.put(obj + 0x14c, target)
        env.put(obj + 0xc8, 0x34567890)
        return t
    return setup


def reset_setup(mode, facing=0, mounted=False, animation=False, seed=0x87654321):
    def setup(env):
        t = common(env)
        obj, logic = t['object'], t['logic']
        if mode == 'no-player':
            return t
        env.put(0x537e88, obj)
        if mode == 'no-logic':
            env.put(obj + 0x6c, 0)
            return t
        env.put(logic + 0x1c, 0x1392 if mode == 'active' else 0x1391)
        state = env.object(0x200, 'player-state', fill=0x63)
        env.put(logic + 0x14, state)
        env.put(state, facing, int(animation))
        env.put(state + 0x12c, 0)
        env.put(state + 0x124, 0)
        controller = env.object(0x30, 'controller', fill=0x51)
        env.put(controller + 0xc, seed)
        env.put(0x537204, controller)
        env.put(obj + 8, seed & ~0x80)
        for off in range(0xc0, 0x188, 4):
            if off != 0xc8:
                env.put(obj + off, 0x7a000000 + off)
        env.put(obj + 0x148, 0x76543210, 0xfedcba98)
        for address in range(0x534e60, 0x534e78, 4):
            env.put(address, seed ^ address)
        if mounted:
            mount = env.object(0x100, 'mount-object', fill=0)
            mountlogic = env.object(0x40, 'mount-logic', fill=0)
            mountstate = env.object(0x340, 'mount-state', fill=0)
            env.put(state + 0x12c, mount)
            env.put(mount + 0x6c, mountlogic)
            env.put(mountlogic + 0x18, mountstate)
            env.put(mountstate + 0x20, 2)
            env.put(mountstate + 0x2fc, 32, 0x87654320)
        return t
    return setup


def dispatch_setup(key, filled, growth=0):
    def setup(env):
        t = common(env)
        obj = t['object']
        # A valid RTTI descriptor permits the null callback lookup path.
        vt = env.object(0x30, 'rtti-vtable', fill=0)
        descriptor = env.object(0x20, 'rtti-descriptor', fill=0)
        info = env.object(0x20, 'rtti-info', fill=0x6b)
        env.put(vt, descriptor)
        env.put(descriptor + 0xc, info)
        env.put(obj, vt + 4)
        table = env.object(12, 'state-table', fill=0)
        fn = callback(env, 'state-callback', observer=lambda e,c,l:e.put(l+0x20,e.get(0x537628),e.get(c.receiver+0x148)))
        env.put(table, fn if filled else 0, fn, fn)
        env.put(obj + 0x148, 0x12345678)
        env.put(0x537610, 10, 12, table, 0, 4)
        env.put(0x537628, 0x86543210)
        return t
    return setup


def logic_setup(state):
    def setup(env):
        t = common(env)
        env.put(t['logic'] + 0x1c, state)
        stateobj = env.object(0x150, 'gem-state', fill=0)
        vt = env.object(0x30, 'gem-vtable', fill=0)
        env.put(stateobj, vt)
        env.put(stateobj + 0x10, t['logic'])
        for offset in (4, 8, 12, 0x1c, 0x20):
            env.put(vt + offset, callback(env, 'gem-slot-' + str(offset), 1 if offset in (4,8,12) else 0))
        env.put(t['logic'] + 0x18, stateobj)
        # Empty registry yields the original empty CString (shared immutable data).
        table = env.object(4, 'state-name-table', fill=0)
        header = env.object(16, 'state-name-string', fill=0)
        env.put(header, 1, 0, 0)
        env.put(table, header + 12)
        env.put(0x5376a0, state, state, table, 0, 4)
        return t
    return setup


def res_entries(env):
    entries = []
    for i, name in enumerate(('LEVEL_GEM', 'GAME_MAPPIECE', 'GAME_CHECKEDFLAG')):
        desc = env.object(0x80, 'res-' + name, fill=0)
        array = env.object(0x40, 'res-array-' + name, fill=0)
        env.put(desc + 0x64, i + 1)
        env.put(desc + 0x68, i + 3)
        env.put(desc + 0x14, array)
        for j in range(8):
            sprite = env.object(0x40, 'res-sprite', fill=0)
            env.put(sprite + 0x18, 3 + i + j, 5 + 2 * j, 40 + 11 * i + j, 70 + 7 * j + i)
            env.put(array + 4 * j, sprite)
        entries.append((name, desc))
    return entries


def level_setup(state, glitter, flags, kind, checked, count, match, animated, rect, res=False):
    def setup(env):
        t = common(env)
        obj, logic = t['object'], t['logic']
        env.put(logic + 0x168, 0x5a5a1234)
        env.put(obj + 4, 0x4444)
        env.put(obj + 0xfc, 0x5555)
        env.put(obj + 0x138, 0x6161, 0x6262, 0x6363, 0x6464)
        env.put(logic + 0x1c, state)
        env.put(obj + 8, flags)
        env.put(obj + 0x64, animated)
        if glitter:
            child = env.object(0x30, 'glitter', fill=0xa7)
            env.put(obj + 0xc8, child)
        manager = env.object(0x200, 'manager', fill=0)
        level = env.object(0x30, 'level', fill=0)
        vt = env.object(0x20, 'level-vtable', fill=0)
        env.put(level, vt)
        env.put(level + 0x14, kind)
        env.put(vt + 0x10, callback(env, 'level-kind', result=checked))
        env.put(manager + 0x2c, level)
        checkstr = env.object(0x20, 'checked-string', fill=0)
        env.put(checkstr, int(checked == 3))
        env.put(manager + 0xc0, checkstr + 8)
        env.put(0x5371fc, manager)
        env.put(0x537960, level + 0x14)
        env.put(obj + 0x190, 0 if state == 5 or not animated else 1)
        env.put(obj + 0xd0, animated)
        env.put(0x52a190, count)
        for i in range(max(0, count)):
            env.put(0x537ec8 + 4*i, 0x11220000 + i)
            env.put(0x537fd0 + 4*i, 50 + 13*i)
            env.put(0x538310 + 4*i, 0xa000 + i)
            env.put(0x5380d8 + 4*i, 0xb000 + i)
        last = 0
        if res:
            entries = res_entries(env)
            resource_map(env, env.get(t['world'] + 0x10), entries)
            env.put(env.get(t['world'] + 0x10) + 0x18, 1)
            if checked == 4 or checked == 3:
                last = 2
            elif kind == 13:
                last = 0
            elif kind & 1:
                last = 1
            env.put(obj + 0x174, 0)
        if match >= 0:
            # Resource lookup may replace obj+170; empty lookup returns zero.
            env.put(0x537ec8 + 4*match, entries[last][1] if res else 0)
        if rect:
            image = env.object(0x40, 'image-rectangle', fill=0)
            env.put(image + 0x18, 7, 11, 29, 47)
            env.put(obj + 0x174, image)
        return t
    return setup


def resource_map(env, manager, entries):
    buckets = env.object(4, 'resource-bucket', fill=0)
    tail = 0
    for name, value in entries:
        key = env.object(len(name)+1, 'resource-name', data=name.encode()+b'\0')
        node = env.object(16, 'resource-node', fill=0)
        env.put(node, tail, 0, key, value)
        tail = node
    env.put(buckets, tail)
    env.put(manager + 0x14, buckets, 1)


def factory(env, world, entries):
    manager = env.object(0x100, 'factory', fill=0)
    env.put(manager + 0xc, world)
    env.put(manager + 0x28, 10)
    env.put(world + 8, manager)
    resources = env.get(world + 0x14)
    resource_map(env, resources, entries)
    return manager


def glitter_setup(success):
    def setup(env):
        t = level_setup(0, False, 0x12345678, 1, 0, 0, -1, 0, False)(env)
        manager = env.get(0x5371fc)
        env.put(manager + 0x124, 1)
        desc = env.object(0x40, 'glitter-descriptor', fill=0)
        env.put(desc + 0x10, callback(env,'glitter-created',argc=1,convention='cdecl'))
        factory(env,t['world'], [('PowerupGlitter',desc)] if success else [])
        return t
    return setup


def create_setup(sound, enabled, x, y):
    def setup(env):
        t = common(env)
        obj, world = t['object'], t['world']
        source = env.object(0x80, 'source-object', fill=0x49)
        env.put(source + 0x4c, x, y)
        env.put(source + 0x64, 31)
        env.put(obj + 0x12c, source)
        owner = env.object(16, 'factory-owner', fill=0)
        env.put(owner + 12, world)
        env.put(obj + 0x130, owner)
        env.put(world + 0x148, x+137, y+251)
        collision = env.object(0x80, 'spawn-collision-world', fill=0)
        env.put(collision + 0x64, 0x7fffffff, 0x7fffffff)
        env.put(world + 0x24, collision)
        desc = env.object(0x40, 'endgem-resource-descriptor', fill=0)
        env.put(desc + 0x10, 0x43ca60)
        factory(env,world,[('EndLevelGem',desc)])
        env.put(0x537680,0)
        env.put(0x537210,17)
        env.put(0x532c0c,int(enabled),0x12345678)
        if sound:
            snd = env.object(0x20,'sound-holder',fill=0)
            receiver = env.object(0x20,'sound-receiver',fill=0)
            context = env.object(0x80,'sound-context',fill=0)
            env.put(obj+0x458,snd)
            env.put(snd+0x10,receiver)
            env.put(receiver+0x10,context)
        return t
    return setup


def wrapped_dispatch(env):
    t = common(env)
    fn = callback(env, 'wrapped-state-callback',
                  observer=lambda e, c, l: e.put(l + 0x20, e.get(0x537628)))
    table = env.object(4, 'wrapped-table', words=[fn])
    # Both growth distances times stride wrap to zero in the original u32
    # arithmetic. Each realloc requests four bytes and preserves the callback.
    # The first growth fixes only lower, leaving upper below key until the
    # second growth. No fixture changes registry state.
    env.put(0x537610, 0x40000000, -0x40000000, table, 0, 4)
    env.put(0x537628, 0x87654321)
    return t


def dispatch_failure(env):
    t = dispatch_setup(13, False)(env)
    fallback = env.object(4, 'failed-growth-fallback', fill=0)
    error = env.object(16, 'error-context', fill=0)
    env.put(error + 12, 4)
    env.put(0x53760c, error)
    env.put(0x53761c, fallback)
    env.override(0x4a9070, lambda e,c: 0)
    return t


def constructor_setup(config, coords, stamp):
    def setup(env):
        t = common(env)
        receiver = env.object(0x150, 'construction-target', fill=0x91)
        env.put(t['logic'] + 0x2c, *config)
        env.put(t['object'] + 0x4c, *coords)
        env.put(t['object'] + 0x148, -17, 23)
        collision = env.object(0x80, 'collision-world', fill=0)
        env.put(collision + 0x64, 0x7fffffff, 0x7fffffff)
        env.put(t['world'] + 0x24, collision)
        env.put(0x537210, stamp)
        env.put(0x537680, 0)
        f64(env, 0x513e10, 1.1)
        f64(env, 0x513e18, -2.3)
        t['receiver'] = receiver
        return t
    return setup


def cases(random_source):
    yield Case('wrapped table grows twice',0x43cdc0,wrapped_dispatch,receiver=lambda t:t['object'],arguments=(0,))
    for config in ((0,0,0,0),(3,-5,7,-11),(0,17,0,-19),(23,0,-29,0)):
        yield Case(f'construct {config}', 0x43cb20, constructor_setup(config,(-31,47),random_source.getrandbits(32)),receiver=lambda t:t['receiver'],arguments=(lambda t:t['object'],))
    for mask in range(16):
        config = tuple(((-1 if bit % 2 else 1) * (101 + 37 * bit))
                       if mask & (1 << bit) else 0 for bit in range(4))
        coords = (-0x80000000 + mask, 0x7fffffff - 3 * mask)
        stamp = (0, 1, 0x80000000, 0xffffffff)[mask % 4]
        yield Case(f'construct independent defaults mask {mask}', 0x43cb20,
                   constructor_setup(config, coords, stamp),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['object'],))
    for mode in ('no-player', 'no-logic', 'wrong-state'):
        yield Case('reset-' + mode, 0x4205b0, reset_setup(mode))
    for facing in (0, 1, -1):
        for mounted in (False, True):
            for animation in (False, True):
                yield Case(f'reset {facing} mount {mounted} animation {animation}', 0x4205b0,
                           reset_setup('active', facing, mounted, animation, random_source.getrandbits(32) & ~0x80))
    for x,y,vy,target in ((3.75, 8.5, -1., 7),(-17.75,-2.5,0.,-3),(12.,5.,1.,5),(13.,6.,1.,5),(0.,-1.,1.,0),(9.,4.,-0.0,3)):
        yield Case(f'tick {x} {y} {vy} {target}',0x43d070,tick_setup(x,y,vy,target),receiver=lambda t:t['object'])
    for x, y, vy, target in (
            (2147483647.75, -2147483648.75, -1., 0),
            (-2147483648.75, 2147483647.75, -1., 0),
            (float('nan'), 7., -1., 7),
            (float('inf'), -float('inf'), -1., 0),
            (11., 8., float('nan'), 7),
            (11., float('nan'), 1., 7),
            (11., 7.000000000000001, 1., 7),
            (11., 6.999999999999999, 1., 7)):
        yield Case(f'tick boundary {x} {y} {vy} {target}', 0x43d070,
                   tick_setup(x, y, vy, target), receiver=lambda t: t['object'])
    aims = [((0.,0.,0.),(0.,0.,0.),(0,0)),((1.,2.,3.),(0.,0.,0.),(5,7)),
            ((1.,2.,3.),(1e-7,2e-7,-3e-7),(5,7)),((1.,2.,3.),(1.,2.,-3.),(5,7)),
            ((1e16,-2e16,3e16),(1e-9,2e-9,-3e-9),(5,7)),
            ((5.,7.,0.),(1.,2.,3.),(5,7)),((-4.,8.,-12.),(-2.,3.,7.),(0,5)),
            ((1.,2.,3.),(0.,0.,0.),(5,0))]
    for axis in range(3):
        for sign in (-1., 1.):
            for scale in (0., 1e-150, 1e-7, 1., 1e150):
                acceleration = tuple(sign * scale if i == axis else 0. for i in range(3))
                aims.append(((3.25, -7.5, 11.75), acceleration, (19, -23)))
    for _ in range(24):
        aims.append((tuple(random_source.uniform(-100,100) for _ in range(3)),tuple(random_source.uniform(-10,10) for _ in range(3)),tuple(random_source.randrange(-100,101) for _ in range(2))))
    for index,(pos,acc,args) in enumerate(aims):
        yield Case(f'aim {index}',0x43d0f0,aim_setup(pos,acc,(11.1,22.2,-33.3)),receiver=lambda t:t['object'],arguments=args)
    for key in (9,10,11,12,13):
        for filled in (False, True):
            yield Case(f'dispatch {key} filled {filled}',0x43cdc0,dispatch_setup(key,filled),receiver=lambda t:t['object'],arguments=(key,))
    for state in (1,28,29,30,31,1000,1001,0xffffffff):
        yield Case(f'gem-state {state}',0x43ca60,logic_setup(state),arguments=(lambda t:t['object'],))
    for state in (1,29,5):
        for glitter in (False, True):
            yield Case(f'level-state {state} glitter {glitter}',0x4701b0,level_setup(state,glitter,random_source.getrandbits(32),1,0,0,-1,1,False),arguments=(lambda t:t['object'],))
    for kind,checked in ((0,0),(1,0),(13,0),(1,4),(2,3)):
        for count,match in ((0,-1),(3,-1),(3,0),(3,2)):
            for animated in (0,1):
                yield Case(f'level init {kind} checked {checked} count {count} match {match} anim {animated}',0x4701b0,level_setup(0,False,random_source.getrandbits(32),kind,checked,count,match,animated, bool(animated)),arguments=(lambda t:t['object'],))
    for kind,checked in ((0,0),(1,0),(13,0),(1,4),(2,3)):
        for count,match in ((0,-1),(3,-1),(3,1)):
            yield Case(f'level resources {kind} checked {checked} count {count} match {match}',0x4701b0,level_setup(0,False,random_source.getrandbits(32),kind,checked,count,match,1,False,True),arguments=(lambda t:t['object'],))
    def registry_init(env):
        t = level_setup(0,False,0x43210000,13,0,0,-1,0,False)(env)
        env.put(0x538418,0)
        return t
    yield Case('level initialize registry',0x4701b0,registry_init,arguments=(lambda t:t['object'],))
    def zero_gem(env):
        t = constructor_setup((3,-5,7,-11),(-31,47),0)(env)
        env.put(t['logic']+0x1c,0)
        return t
    yield Case('gem state zero constructs and publishes',0x43ca60,zero_gem,arguments=(lambda t:t['object'],))
    for success in (False,True):
        yield Case(f'level glitter creation {success}',0x4701b0,glitter_setup(success),arguments=(lambda t:t['object'],))
    for sound,enabled in ((False,False),(True,False),(True,True)):
        yield Case(f'create endgem sound {sound} enabled {enabled}',0x40e5c0,create_setup(sound,enabled,-41,73),receiver=lambda t:t['object'])
    def create_mutating(env):
        t = create_setup(True,True,19,-37)(env)
        source = env.get(t['object'] + 0x12c)
        def allocate_and_mutate(env, call):
            count = env.calls_so_far(0x4f63ec)
            env.put(source + 0x4c, 500+count, 700+count)
            env.put(t['world'] + 0x148, -900-count, 1100+count)
            return env.object(call.arguments[0], 'callback-allocation', fill=0)
        env.override(0x4f63ec, allocate_and_mutate)
        return t
    yield Case('create rereads target after constructor callbacks',0x40e5c0,create_mutating,receiver=lambda t:t['object'])
    def no_create(env):
        t = common(env)
        env.put(t['object'] + 0x45c, 1)
        return t
    yield Case('already-created',0x40e5c0,no_create,receiver=lambda t:t['object'])
