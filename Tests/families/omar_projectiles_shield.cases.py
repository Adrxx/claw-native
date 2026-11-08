"""Independent original-input cases for Omar's projectiles and shield."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence, reallocate

def obj(env, size, *args, **kwargs):
    kwargs.setdefault('fill', 0)
    return env.object(size, *args, **kwargs)


NEW = 0x4F63EC
RAND = 0x4A3050


def record(env, log, tag, call, result=0):
    n = env.get(log)
    env.put(log, n + 1)
    env.put(log + 4 + n * 20, tag, call.receiver, *(tuple(call.arguments) + (0, 0, 0))[:3])
    return result


def dictionary(env, entries=()):
    resource = obj(env, 0x40, 'resource dictionary')
    buckets = obj(env, 4, 'resource buckets')
    head = 0
    for key, value in entries:
        name = obj(env, len(key) + 1, 'resource name', data=key.encode() + b'\0')
        head = obj(env, 16, 'resource node', words=[head, 0, name, value])
    env.put(buckets, head)
    env.put(resource + 0x14, buckets, 1)
    return resource


def animation(env, marker):
    frame = obj(env, 0x40, 'animation frame')
    env.put(frame + 0x18, 3, 5, 13, 17)
    frames = obj(env, 4, 'animation image list', words=[frame])
    images = obj(env, 0x70, 'animation images')
    env.put(images + 0x14, frames)
    env.put(images + 0x64, 0, 0)
    return images


def actor_world(env, seed=0, images=False):
    logic = obj(env, 0x180, 'actor logic')
    actor = obj(env, 0x200, 'actor')
    world = obj(env, 0x80, 'world')
    creator = obj(env, 0x50, 'world creator')
    collision = obj(env, 0x80, 'collision world')
    env.put(collision + 0x64, 32, 32)
    first, second = animation(env, seed), animation(env, seed + 1)
    image_map = dictionary(env, [('LEVEL_FIRESHIELD', first), ('LEVEL_ICESHIELD', second)] if images else ())
    other_map = dictionary(env)
    ani_map = dictionary(env)
    env.put(world + 8, creator)
    env.put(world + 0x10, image_map, other_map)
    env.put(world + 0x24, collision)
    env.put(world + 0x2c, ani_map)
    env.put(creator + 0xc, world)
    env.put(actor + 8, seed & 0x4000)
    env.put(actor + 0xc, world)
    env.put(actor + 0x4c, 200 + seed % 20, 100 + seed % 17)
    env.put(actor + 0x64, 7 + seed % 11)
    env.put(actor + 0x6c, logic)
    env.put(actor + 0x190, 0x12340000 | (seed & 0xffff))
    env.put(logic + 0xc, world)
    env.put(0x537680, 0)  # empty original state-name registry
    flags = obj(env, 0x128, 'difficulty flags')
    env.put(0x5371fc, flags)
    return {'actor': actor, 'logic': logic, 'world': world, 'creator': creator,
            'first': first, 'second': second, 'flags': flags}


def callback_methods(env, receiver, log):
    methods = obj(env, 0x30, 'behavior methods')
    for offset, argc in [(4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)]:
        env.put(methods + offset, env.stub('behavior method ' + str(offset), 'thiscall', argc,
                lambda e, c, tag=offset: record(e, log, tag, c, 0x71000000 + tag)))
    env.put(receiver, methods)


def cstring(env, label):
    data = obj(env, 76, label)
    env.put(data, 1, 0, 63)
    return data + 12


def generic_registry(env, command):
    lower = min(0, command)
    upper = max(31, command)
    # Unknown commands are intentionally kept in a compact signed range.
    cells = obj(env, (upper-lower+1) * 4, 'state names')
    for i in range(upper-lower+1):
        env.put(cells + i*4, cstring(env, 'unique state CString'))
    env.put(0x5376a0, lower, upper, cells)
    env.put(0x5376b0, 4)


def factory_setup(command, seed):
    def setup(env):
        t = actor_world(env, seed)
        logic, actor = t['logic'], t['actor']
        behavior = obj(env, 0x158, 'existing behavior', fill=0x39)
        log = obj(env, 0x500, 'method observations')
        callback_methods(env, behavior, log)
        env.put(behavior + 0x10, logic)
        env.put(logic + 0x18, behavior, command)
        if command not in (0, 29, 30, 1000):
            generic_registry(env, command)
        t['behavior'] = behavior
        return t
    return setup


def constructor_setup(bullet, global_flag, difficulty, health, seed, resources=False, redirect_actor=False):
    def setup(env):
        t = actor_world(env, seed)
        t['receiver'] = obj(env, 0x158 if bullet else 0x48, 'construction destination', fill=0xa7)
        env.put(0x53724c, global_flag)
        env.put(t['flags'] + 0x124, difficulty)
        env.put(t['actor'] + 0x64, health)
        env.put(t['logic'] + 0x2c, seed % 5, seed % 7, seed % 11, seed % 13)
        if resources:
            alternate = actor_world(env, seed + 37)['actor'] if redirect_actor else 0
            log = obj(env, 0x500, 'shield resource callback observations')
            descriptors = []
            for slot, tag in [(0x70, 0x137), (0x78, 0x249)]:
                handler = obj(env, 0x28, 'existing logic handler')
                methods = obj(env, 0x28, 'logic handler methods')
                env.put(handler, methods)
                def observe(e, c, tag=tag, slot=slot):
                    record(e, log, tag, c, tag)
                    n = e.get(log) - 1
                    e.put(log + 0x300 + n * 20, e.get(t['actor'] + 0xd0),
                          e.get(t['actor'] + 0xd4), e.get(t['receiver'] + 0x34),
                          e.get(t['actor'] + 0x190), e.get(t['actor'] + slot))
                    if alternate and tag == 0x137:
                        e.put(t['receiver'] + 0xc, alternate)
                    return tag
                env.put(methods + 0x1c, env.stub('reset logic handler', 'thiscall', 0, observe))
                env.put(methods + 0x24, env.stub('set logic handler', 'thiscall', 2, observe))
                env.put(t['actor'] + slot, handler)
                descriptor = obj(env, 0x18, 'logic resource descriptor')
                env.put(descriptor + 0x10, tag)
                descriptors.append(descriptor)
            logic_map = dictionary(env, [('LogicHit', descriptors[0]), ('LogicAttack', descriptors[1])])
            env.put(t['world'] + 0x14, logic_map)
            env.put(t['world'] + 0x10, dictionary(env, [('LEVEL_FIRESHIELD', t['first'])]))
            frame = obj(env, 0x24, 'shield sequence frame')
            env.put(frame + 0x1c, 37 + seed % 19)
            frames = obj(env, 4, 'shield sequence frames', words=[frame])
            sequence_object = obj(env, 0x18, 'shield animation sequence')
            env.put(sequence_object + 0xc, frames, 1)
            env.put(t['world'] + 0x2c, dictionary(env, [('LEVEL_FIRESHIELD', sequence_object)]))
        return t
    return setup


def dispatch_setup(registry, index, zero, seed, stride=4):
    def setup(env):
        log = obj(env, 0x200, 'state observations')
        receiver = obj(env, 0x158, 'state receiver', fill=0x6d)
        rtti_type = obj(env, 16, 'RTTI type descriptor', fill=0x31)
        rtti = obj(env, 20, 'RTTI complete object record')
        env.put(rtti + 12, rtti_type)
        vtable = obj(env, 12, 'receiver vtable with RTTI')
        env.put(vtable, rtti)
        env.put(receiver, vtable + 4)
        f = env.stub('selected state', 'thiscall', 0, lambda e,c: record(e,log,seed,c))
        table = obj(env, stride * 3, 'state table')
        for n in range(3):
            env.put(table + n * stride, 0 if zero else f)
        env.put(registry + 8, 0, 2, table, table, stride, 0x12345678, 0xdeadbeef, 0x87654321)
        # A bullet falls through to its original projectile state registry.
        fallback = obj(env, 4, 'projectile fallback state', words=[f])
        env.put(0x538430, min(index,0), max(index,0), fallback)
        env.put(0x538440, 0)
        return {'receiver': receiver}
    return setup


def dispatch_reloads_bounds_setup(registry):
    def setup(env):
        t = dispatch_setup(registry, 3, False, 0x317)(env)
        # Both original grows have a four-byte allocation and a zero-byte shift.
        env.put(registry + 8, 3 + 0x40000000, 3 - 0x40000000)
        return t
    return setup


def selection_setup(index, matched, seed):
    def setup(env):
        t = actor_world(env, seed)
        key = 'LEVEL_FIRESHIELD' if index == 0 else 'LEVEL_ICESHIELD'
        target = t['first'] if index == 0 else t['second']
        image_map = dictionary(env, [(key, target)])
        env.put(t['world'] + 0x10, image_map)
        env.put(t['actor'] + 0x170, target if matched else t['second'] if index == 0 else t['first'])
        receiver = obj(env, 0x48, 'shield selection destination', fill=0x6b)
        env.put(receiver + 0xc, t['actor'])
        env.put(receiver + 0x2c, t['actor'])
        t['receiver'] = receiver
        return t
    return setup


def attack_setup(kind, flags):
    def setup(env):
        target = obj(env, 0xd4, 'Claw or other target', fill=0x48)
        env.put(target + 8, flags)
        env.put(target + 0xd0, kind)
        actor = obj(env, 0x78, 'shield actor')
        env.put(actor + 0x74, target)
        receiver = obj(env, 0x10, 'shield behavior')
        env.put(receiver + 0xc, actor)
        return {'receiver': receiver}
    return setup


def falling_setup(count, bounds, values, seed, change_count=False):
    def setup(env):
        t = actor_world(env, seed)
        receiver = obj(env, 0x158, 'falling bullet')
        env.put(receiver + 0xc, t['actor'])
        env.put(receiver + 0x12c, t['actor'], t['logic'])
        env.put(receiver + 0x150, count)
        env.put(receiver + 0x120, 0x10000 if seed & 1 else 0)
        env.write(receiver + 0x68, struct.pack('<dd', 100.25 + seed % 3, -20.75 - seed % 5))
        env.put(t['actor'] + 0x118, *bounds)
        # Real creation uses an original callback record and a resource descriptor.
        blueprint = obj(env, 0x18, 'created object blueprint')
        log = obj(env, 0x500, 'created actor callback observations')
        def created(e, c):
            actor = c.arguments[0]
            record(e, log, 0x14, c)
            n = e.get(log) - 1
            e.put(log + 0x300 + n*20, e.get(actor+0x4c), e.get(actor+0x50), e.get(actor+0x64), e.get(receiver+0x150), e.get(t['actor']+8))
            if change_count:
                e.put(receiver + 0x150, 1)
            return seed
        callback_data = env.stub('created GlitterBaby logic callback', 'cdecl', 1, created)
        env.put(blueprint + 0x10, callback_data)
        resources = dictionary(env, [('GlitterBaby', blueprint)])
        env.put(t['world'] + 0x14, resources)
        free_nodes = obj(env, 12 * 8, 'creator free nodes')
        for i in range(8):
            env.put(free_nodes + i*12, free_nodes+(i+1)*12 if i<7 else 0)
        env.put(t['creator'] + 0x20, free_nodes)
        env.override(RAND, sequence(*values))
        t['receiver'] = receiver
        return t
    return setup


def cases(random_source):
    for function in (0x410400, 0x464f20):
        for command in (29, 30, 1000, 1, 28, 31, -1):
            yield Case(f'factory {function:x} command {command}', function,
                       factory_setup(command, random_source.randrange(1000)),
                       arguments=(lambda t:t['actor'],))
        yield Case(f'factory {function:x} creates behavior', function,
                   factory_setup(0, 17), arguments=(lambda t:t['actor'],))
    for global_flag,difficulty in [(0,0),(0,1),(1,0),(1,1),(0,0xffffffff)]:
        yield Case(f'bullet ctor {global_flag}/{difficulty}', 0x412330,
                   constructor_setup(True,global_flag,difficulty,7,random_source.randrange(1000)),
                   receiver=lambda t:t['receiver'],arguments=(lambda t:t['actor'],))
    for health in (0,1,5000,-1,0x7fffffff):
        yield Case(f'shield ctor health {health}', 0x464fe0,
                   constructor_setup(False,0,0,health,random_source.randrange(1000)),
                   receiver=lambda t:t['receiver'],arguments=(lambda t:t['actor'],))
    for health in (0, 11, 5000):
        yield Case(f'shield ctor live resources health {health}', 0x464fe0,
                   constructor_setup(False, 0, 0, health, random_source.randrange(1000), True),
                   receiver=lambda t:t['receiver'], arguments=(lambda t:t['actor'],))
    yield Case('shield ctor reloads actor after registration callback', 0x464fe0,
               constructor_setup(False, 0, 0, 0, 173, True, True),
               receiver=lambda t:t['receiver'], arguments=(lambda t:t['actor'],))
    for function,registry in [(0x412460,0x534b28),(0x4651a0,0x537c00)]:
        for index in (-2, -1, 0, 1, 2, 3, 5):
            for zero in (False,True):
                yield Case(f'dispatch {function:x} index {index} zero {zero}', function,
                           dispatch_setup(registry,index,zero,index+50),
                           receiver=lambda t:t['receiver'],arguments=(index,))
        yield Case(f'dispatch {function:x} reloads bounds after allocation', function,
                   dispatch_reloads_bounds_setup(registry),
                   receiver=lambda t:t['receiver'], arguments=(3,))
    for index in (0,1,2,-1,0x7fffffff):
        for matched in (False,True):
            yield Case(f'select {index} matched {matched}',0x465480,
                       selection_setup(index,matched,random_source.randrange(1000)),
                       receiver=lambda t:t['receiver'],arguments=(index,))
    for kind in (0,1,0x1f,0x20,0x21,0x2000000,0x2000001,0xffffffff):
        for flags in (0,0x10000,random_source.getrandbits(32)):
            yield Case(f'attack type {kind:x} flags {flags:x}',0x465550,
                       attack_setup(kind,flags),receiver=lambda t:t['receiver'])
    for count in (-1,0):
        yield Case(f'falling inactive {count}',0x412740,
                   falling_setup(count,(0,0,0,0),(0,),5),receiver=lambda t:t['receiver'])
    for bounds in [(0,0,3,4),(-2,-4,5,8),(5,7,4,6),(-1,-1,-2,-2)]:
        for values in [(0,0),(1,1),(2,3),(-7,-5)]:
            yield Case(f'falling {bounds} rand {values}',0x412740,
                       falling_setup(2,bounds,values,13),receiver=lambda t:t['receiver'])
    yield Case('falling reloads count after created actor callback',0x412740,
               falling_setup(3,(0,0,2,2),(3,4),7,True),receiver=lambda t:t['receiver'])
