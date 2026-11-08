"""Original-only town guard cases, with distinct graph and callback witnesses."""
import struct
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_TOP
from clawparity.fixtures import returns, sequence

ANIMATION_KEYS = (5427716, 5427688, 5387444, 5427656, 5427628, 5427600, 5427576, 5427552, 5427528, 5427500, 5427476, 5427452, 5427424, 5427396, 5427372, 5428304, 5428276, 5428244, 5428216, 5428188, 5428164, 5428140, 5428116, 5428088, 5428064, 5428040, 5428012, 5427984, 5427960, 5428348)
SOUND_KEYS = (5427344, 5427316, 5427288, 5427264, 5427236, 5427208, 5427180, 5427152, 5427124, 5427096, 5427068, 5427040, 5427012, 5426988, 5426964, 5427932, 5427904, 5427876, 5427848, 5427820, 5427792, 5427764)


def resource_map(env, keys=(), animation=False):
    resource = env.object(0x30, 'resource-map')
    bucket = env.object(4, 'bucket')
    env.put(resource + 0x14, bucket, 1)
    node = 0
    for index,key in enumerate(keys):
        value = env.object(0x80, 'animation' if animation else 'sound', fill=0)
        if animation:
            frame = env.object(0x30, 'animation-frame', fill=0x39 + index)
            frames = env.object(4, 'frame-vector', words=[frame])
            env.put(value + 0xc, frames, 1)
        node = env.object(16, 'map-node', words=[node, 0, key, value])
    env.put(bucket, node)
    return resource


def graph(env, primary=False):
    obj = env.object(0x498, 'guard', fill=0)
    actor = env.object(0x1c0, 'actor', fill=0)
    logic = env.object(0x180, 'logic', fill=0)
    world = env.object(0x40, 'world', fill=0)
    animation_keys = () if primary == 'missing' else ANIMATION_KEYS[::2] if primary == 'mixed' else ANIMATION_KEYS + (0x5234b4,) if primary else (0x5234b4,)
    animations = resource_map(env, animation_keys, True)
    empty = resource_map(env)
    sounds = resource_map(env, (0x52d090,0x52d074) if primary == 'sparse-sound' else () if primary == 'missing' else SOUND_KEYS[::2] if primary == 'mixed' else SOUND_KEYS)
    collision = env.object(0x100, 'collision')
    plane = env.object(0xa0, 'collision-plane')
    rows = env.object(4, 'rows', words=[0])
    tiles = env.object(4, 'tiles', words=[0xeeeeeeee])
    env.put(collision + 0x5c, plane)
    env.put(plane + 0x20, tiles, rows)
    env.put(plane + 0x30, 1000, 1000)
    env.put(plane + 0x8c, 20, 20)
    sprite_map=empty
    if primary == 'sprite':
        sprite_map=resource_map(env)
        node=0
        for index,key in enumerate((0x52d204,0x52d450)):
            image=env.object(0x80,'sprite-image')
            sprite=env.object(0x180,'sprite-frame')
            sprite_frames=env.object(12,'sprite-frames',words=[sprite,sprite,sprite])
            env.put(image+0x14,sprite_frames)
            env.put(image+0x64,index+1,2)
            node=env.object(16,'sprite-node',words=[node,0,key,image])
        env.put(env.get(sprite_map+0x14),node)
    env.put(world + 0x10, sprite_map, empty)
    env.put(world + 0x24, collision, sounds, animations)
    env.put(actor + 0xc, world)
    env.put(actor + 0x6c, logic)
    env.put(actor + 0x38, 0xffffffff)
    env.put(actor + 0x4c, 100, 100)
    for off in (0x488,0x48c,0x490,0x494,0x484,0x28c,0x290,0x29c,0x2a0,0x2a4,0x2a8,0x2ac,0x2b0,0x2b4,0x2b8,0x2bc,0x2c0,0x2c4,0x2c8):
        env.put(obj + off, 0x67510000 + off)
    env.put(actor + 0x16c,0x2468ace0,0x13579bdf,0x12345678)
    env.put(obj + 0xc, actor, logic)
    env.put(obj + 0x128, actor, actor)
    env.put(obj + 0x190, actor, actor)
    env.put(0x534eac, 0x26b7)
    env.put(0x541334, 1)
    env.put(0x533470, 32)
    env.put(0x544d18, 0)
    env.put(0x537668 + 0x18, 0)
    env.put(0x53c9ac, 0)
    env.put(0x5262b0, 0x3f800000, 0x3f800000, 0x3f800000)
    env.override(0x4a3050, sequence(99, 99, 99, 99))
    return dict(obj=obj, actor=actor, logic=logic, world=world)


def construct(primary=False, difficulty=5, scale=1.0, rand=0, count=32, attack_scale=1.0, life_scale=1.0, status=None, witnesses=False):
    def setup(env):
        if status is not None:
            env.entry_x87_status(status)
        t = graph(env, primary)
        env.put(0x537964, difficulty)
        env.write(0x5262b0, struct.pack('<fff', life_scale, attack_scale, scale))
        bits = env.object(16, 'owned-bit-storage', fill=0xa5)
        def random_value(e, call):
            if e.calls_so_far(0x4a3050) == 1:
                e.put(t['obj'] + 0x2fc, count)
                e.put(t['obj'] + 0x300, bits if count > 32 else 0xa5910420)
                if witnesses:
                    # Distinguish derived tuning rewrites from equal base values.
                    for offset in (0x28c, 0x290, 0x29c, 0x2a0, 0x2a4, 0x2a8, 0x2ac, 0x2b0, 0x2b4, 0x2b8, 0x2bc, 0x2c0, 0x2c4, 0x2c8):
                        e.put(t['obj'] + offset, 0x67510000 + offset)
                return rand & 0xffffffff
            return 99
        env.override(0x4a3050, random_value)
        rectangle_log=env.object(64,'rectangle-publication-log')
        def rect(e, call):
            e.put(call.arguments[0], *call.arguments[1:])
            if e.get(t['obj']) in (0x50fabc,0x50fb6c):
                e.put(rectangle_log,e.calls_so_far(0x546d5c),e.get(t['obj']+0x488),e.get(t['obj']+0x484),e.get(t['obj']+0x220))
                e.write(rectangle_log+16,e.read(t['actor']+0x128,16))
                if witnesses and call.arguments[0] == t['obj'] + 0x260:
                    # Alias the first wrapper destination with the next source,
                    # entirely within the live receiver.
                    e.put(t['obj'] + 0x12c, t['obj'] + 0x128)
            return 1
        env.override(0x546d5c, rect)
        return t
    return setup


def construct_overlapping_actor():
    def setup(env):
        t = construct('sparse-sound', 5, 2.25, 99, 32)(env)
        actor = t['obj'] + 0x168
        env.write(actor, env.read(t['actor'], 0x1c0))
        t['actor'] = actor
        # The original embedded base initializer copies actor+100 to its
        # own+4c, which aliases this actor's world pointer. Initialize that
        # source so the overlapping graph stays valid throughout construction.
        env.put(actor + 0x100, t['world'])
        env.put(t['obj'] + 0xc, actor, t['logic'])
        env.put(t['obj'] + 0x128, actor, actor)
        return t
    return setup


def destruct(count=32, refs=0):
    def setup(env):
        t = graph(env)
        obj = t['obj']
        env.put(obj + 0x2fc, count)
        env.put(obj + 0x2f8, 0x544b68)
        env.put(obj + 0x300, env.object(16, 'bit-storage', fill=0xb6) if count > 32 else 0xa5910420)
        for off in (0x1a4,0x1a8):
            if refs:
                header = env.object(24, 'string-header', words=[refs, 3, 7, 0x636261])
                env.put(obj + off, header + 12)
            else:
                env.put(obj + off, env.get(0x52e1c8) + 12)
        def decrement(e, call):
            value = (e.get(call.arguments[0])-1)&0xffffffff
            e.put(call.arguments[0], value)
            return value
        env.override(0x5469e8, decrement)
        return t
    return setup


def dispatch(state, low=-2, high=2, own=True, fail=False, mutate=False, witness=0x12345678):
    def setup(env):
        obj = env.object(32, 'dispatch-receiver', fill=0x76)
        record = env.object(48, 'callback-observations')
        def callback(e, call):
            e.put(record, call.receiver, len(call.arguments), e.get(0x53ca90), e.get(0x544b14), call.source_return_pc)
            s = call.source_context
            if s:
                e.put(record+20, s.eax,s.ecx,s.edx,s.ebp,s.esp,s.fsHead)
            return witness
        cb = env.stub('state-handler','thiscall',0,callback)
        for table,handler in ((0x53ca70, cb if own else 0),(0x537878, cb)):
            table_low,table_high = (low,high) if table == 0x53ca70 else (-10,10)
            array = env.object((table_high-table_low+1)*8, 'dispatch-slots', fill=0x4b)
            for i in range(table_high-table_low+1):
                def selected(e,call,slot=i,table_address=table):
                    e.put(record+44,0x72000000 + (table_address&0xffff) + slot)
                    return callback(e,call)
                slot_handler=env.stub(f'state-handler-{table:x}-{i}','thiscall',0,selected)
                env.put(array+i*8,slot_handler if handler else 0)
            default = env.object(8, 'default-slot', words=[cb,0x62636465])
            error = env.object(16,'error-owner',words=[0,0,0,4])
            env.put(table+4,error,table_low&0xffffffff,table_high&0xffffffff,array,default,8,0x718293a4,0x8192a3b4)
        if fail: env.override(0x4a9070, returns(0))
        if mutate:
            def realloc(e,call):
                old,n = call.arguments
                out=e.object(max(4,n),'reallocated-slots')
                e.put(out,cb)
                e.release(old)
                # Zero stride is permitted by the source arithmetic. Alter the
                # opposite bound so the second, intentionally repeated lookup grows.
                e.put(0x53ca88,0)
                if e.calls_so_far(0x4a9070) == 1:
                    e.put(0x53ca7c if state < low else 0x53ca78,(state-1 if state < low else state+1)&0xffffffff)
                return out
            env.override(0x4a9070,realloc)
        s=NativeSourceContext(72,1,0x7ff,0x5ff,witness,0x23456789,obj,0x456789ab,0x56789abc,0x6789abcd,0xffffffff,STACK_TOP,0x497130,0x8d7,0xffffffff,0x472,0,0)
        env.put(STACK_TOP,0x49723a,state&0xffffffff)
        return dict(obj=obj,source=s,record=record)
    return setup


def dispatch_nonzero_stride_reload():
    def setup(env):
        t = dispatch(5)(env)
        handlers = {}
        for ordinal in (1, 2):
            for index in range(-8, 40):
                def selected(side, invocation, slot=index):
                    side.put(t['record'], invocation.receiver, slot & 0xffffffff)
                    return 0x67210000 + slot
                handlers[ordinal, index] = env.stub(f'reloaded-slot-{ordinal}-{index}', 'thiscall', 0, selected)
        def reallocate(e, call):
            old, size = call.arguments
            n = e.calls_so_far(0x4a9070)
            storage = e.object(1024, 'padded-reallocation')
            out = storage + 256
            for index in range(-8, 40):
                e.put(out + index * 8, handlers[n, index])
            e.release(old if n == 1 else old - 256)
            # Allocator reentrancy changes the shared table while growth is in
            # progress. Keep a nonzero stride so the reloaded lower bound
            # determines which distinct, backed callback is selected.
            e.put(0x53ca78, 6 if n == 1 else 5, 5)
            return out
        env.override(0x4a9070, reallocate)
        return t
    return setup


def update(primary=False, player_state=5, enabled=1, direction=0, action=1, actor_state=3, probability=90, elapsed=1000, delay=500, rand=0, selector=0, callback_state=2, player_x=50, mutate=False):
    def setup(env):
        t=graph(env,primary)
        obj,actor=t['obj'],t['actor']
        player=env.object(0x1c0,'player')
        logic=env.object(0x30,'player-logic')
        inputs=env.object(0x100,'player-input')
        env.put(player+0x6c,logic)
        env.put(logic+0x14,inputs)
        env.put(inputs,direction,enabled)
        env.put(inputs+0x3c,action)
        env.put(player+0xcc,player_state)
        env.put(player+0x4c,player_x,100)
        env.put(0x537e88,player)
        env.put(0x537210,1000)
        env.put(obj+0x128,actor,actor)
        env.put(actor+8,0x10)
        env.put(obj+0x20,callback_state)
        env.put(obj+0x184,actor_state)
        env.write(obj+0x68,struct.pack('<d',100.0))
        env.put(obj+0x310,0x13579bdf)
        env.put(obj+0x14,0x2468ace0)
        env.put(obj+0x480,probability&0xffffffff)
        env.put(obj+0x490,(1000-elapsed)&0xffffffff,delay)
        env.put(obj+0x2fc,32,0x1ab)
        for off in (0x210,0x220,0x230,0x240):
            env.put(obj+off,0xf1000000+off,off+17,off+39,off+61)
        for off in (0x45c,0x460,0x464): env.put(obj+off,env.object(4,'sound-id',words=[off]))
        sound_actor=env.object(0x190,'sound-actor')
        sound_logic=env.object(0x30,'sound-logic')
        env.put(sound_actor+0x6c,sound_logic)
        env.put(0x53c9ac,sound_actor)
        def random_value(e,call):
            n=e.calls_so_far(0x4a3050)
            if mutate and n == 1:
                # The saved comparison threshold precedes rand, but probability,
                # clock and callback state are independently reloaded after sound.
                e.put(obj+0x480,0x80000000)
                e.put(obj+0x20,3)
                e.put(0x537210,0x76543210)
            return (rand if n == 1 else selector if n == 2 else 99)&0xffffffff
        env.override(0x4a3050,random_value)
        return t
    return setup


def cases(random_source):
    for fn in (0x496110,0x496990):
        for primary in (False,True):
            yield Case(f'constructor {fn:x} primary {primary}',fn,construct(primary),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    for fn in (0x496860,0x497060,0x496840,0x497040):
        for flags in (0,1,0x100,0x101):
            yield Case(f'destruct {fn:x} flags {flags:x}',fn,destruct(64 if flags&1 else 32,1 if flags&1 else 2),receiver=lambda t:t['obj'],arguments=(flags,) if fn in (0x496840,0x497040) else ())
    for state,own in ((0,True),(0,False),(-4,True),(5,True)):
        yield Case(f'dispatch {state} own {own}',0x497130,dispatch(state,own=own),receiver=lambda t:t['obj'],arguments=(state&0xffffffff,),source_context=lambda t:t['source'],source_return_pc=0x49723a)
    for primary in (False,True):
        for player_state in (4,5):
            yield Case(f'update primary {primary} player {player_state}',0x497510,update(primary,player_state),receiver=lambda t:t['obj'],arguments=(0x52720c,))

    for fn in (0x496110,0x496990):
        for difficulty,count,rand,scale in ((6,64,99,3.25),(4,0,-1,-1.25),(5,5,50,0.0),(5,6,49,2.0),(5,64,50,2.0)):
            yield Case(f'ctor bounds {fn:x} {difficulty} {count} {rand} {scale}',fn,construct(True,difficulty,scale,rand,count),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    for direction in (0,1):
        for player_x in (50,150):
            for action in (0,1,2,3,4,5,6,7,8,9):
                yield Case(f'update actions {direction} {player_x} {action}',0x497510,update(direction=direction,player_x=player_x,action=action),receiver=lambda t:t['obj'],arguments=(0x52720c,))

    for state in (-4,5):
        yield Case(f'dispatch reloaded bounds grow twice {state}',0x497130,dispatch(state,mutate=True),receiver=lambda t:t['obj'],arguments=(state&0xffffffff,),source_context=lambda t:t['source'],source_return_pc=0x49723a)
    variants = (
        dict(enabled=0), dict(actor_state=4,direction=1),dict(actor_state=2,direction=1),
        dict(direction=1,probability=1,rand=0),dict(direction=1,probability=30,rand=29),
        dict(direction=1,probability=31,rand=30),dict(direction=1,probability=90,rand=90),
        dict(direction=1,elapsed=499),dict(direction=1,elapsed=500),
        dict(direction=1,elapsed=0xffffffff,delay=0xffffffff),dict(direction=1,elapsed=0,delay=1),
        dict(direction=1,rand=-1,selector=-1),dict(direction=1,selector=1),
        dict(direction=1,callback_state=1),dict(direction=1,callback_state=-1),
        dict(direction=1,probability=-2147483648,rand=-1),
        dict(direction=1,probability=0,rand=-1),dict(direction=1,probability=29,rand=0),
    )
    for i,options in enumerate(variants):
        yield Case(f'update boundary {i}',0x497510,update(**options),receiver=lambda t:t['obj'],arguments=(0x52720c,))
    for i in range(20):
        difficulty=random_source.choice((4,5,6,0xffffffff))
        count=random_source.choice((0,5,6,31,32,33,64))
        scale=random_source.choice((-1.25,0.0,0.99,1.0,1.01,1.98,2.0,2.01,3.25))
        rand=random_source.randrange(-300,300)
        fn=random_source.choice((0x496110,0x496990))
        yield Case(f'random constructor {i}',fn,construct(bool(i%2),difficulty,scale,rand,count),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],),initial_stack=((-96,random_source.randbytes(16)),))
    for i in range(40):
        options=dict(primary=bool(i%2),player_state=random_source.choice((0,4,5,6)),enabled=random_source.choice((0,1)),direction=random_source.choice((0,1)),action=random_source.randrange(10),actor_state=random_source.choice((2,3,4)),probability=random_source.choice((0,1,29,30,31,90,0x7fffffff,0x80000000)),elapsed=random_source.choice((0,499,500,501,1000,0xffffffff)),delay=random_source.choice((0,500,0xffffffff)),rand=random_source.randrange(-300,300),selector=random_source.randrange(-20,20),callback_state=random_source.choice((-2,0,1,2,3)),player_x=random_source.choice((50,100,150)))
        yield Case(f'random update {i}',0x497510,update(**options),receiver=lambda t:t['obj'],arguments=(random_source.choice((0x52720c,0x527204,0x5234f4)),),initial_stack=((-96,random_source.randbytes(16)),))

    for fn in (0x496110,0x496990):
        for scale in (-1.25,0.0,0.25,1.125,2.75):
            yield Case(f'independent scales {fn:x} {scale}',fn,construct(True,5,2.0,99,64,scale,scale+0.5),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    for fn in (0x496860,0x497060,0x496840,0x497040):
        for flags,count,refs in ((2,0,0),(255,33,0),(0xffffffff,32,1),(0x80000000,31,2)):
            yield Case(f'destruct boundaries {fn:x} {flags:x}',fn,destruct(count,refs),receiver=lambda t:t['obj'],arguments=(flags,) if fn in (0x496840,0x497040) else ())
    yield Case('strike reloads after rand and sound',0x497510,update(direction=1,mutate=True),receiver=lambda t:t['obj'],arguments=(0x52720c,))

    for fn in (0x496110,0x496990):
        for profile in ('missing','mixed'):
            for count in (5,32,64):
                yield Case(f'poisoned ctor {fn:x} maps {profile} bits {count}',fn,construct(profile,5,2.25,99,count),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    for state,low,high in ((-2,-2,2),(2,-2,2),(1,1,3),(3,1,3),(0x7fffffff,0x7ffffffd,0x7fffffff),(-2147483648,-2147483648,-2147483646)):
        yield Case(f'dispatch distinct slot boundary {state}',0x497130,dispatch(state,low,high),receiver=lambda t:t['obj'],arguments=(state&0xffffffff,),source_context=lambda t:t['source'],source_return_pc=0x49723a)

    for fn in (0x496110,0x496990):
        yield Case(f'constructor sprite lookup {fn:x}',fn,construct('sprite',5,2.25,99,32),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))

    for fn in (0x496110,0x496990):
        for rand in (0,99):
            yield Case(f'constructor found first sound missing next {fn:x} {rand}',fn,construct('sparse-sound',5,2.25,rand,32),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    yield Case('dispatch second grow nonzero stride lower bound reload',0x497130,dispatch_nonzero_stride_reload(),receiver=lambda t:t['obj'],arguments=(5,),source_context=lambda t:t['source'],source_return_pc=0x49723a)


    for fn in (0x496110,0x496990):
        yield Case(f'constructor overlapping actor bounds {fn:x}',fn,construct_overlapping_actor(),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))

    # These profiles must remain deterministic: inherited sticky exceptions and
    # independently fractional scale products are part of each constructor ABI.
    for fn in (0x496110, 0x496990):
        for status in (0, 0x20, 0x21):
            for difficulty, speed, attack, life in (
                (5, 1.0, 1.0, 1.0),
                (5, 1.3333333730697632, 1.1777777671813965, 0.9133333563804626),
                (6, 2.0100000000000002, -1.1777777671813965, 0.10000000149011612),
                (4, -0.9900000095367432, 0.3333333432674408, -0.9133333563804626),
            ):
                yield Case(
                    f'constructor x87 status {fn:x} {status:x} difficulty {difficulty} scales {speed} {attack} {life}',
                    fn, construct(True, difficulty, speed, 99, 64, attack, life, status),
                    receiver=lambda t: t['obj'], arguments=(lambda t: t['actor'],),
                )

    for fn in (0x496110, 0x496990):
        yield Case(f'constructor derived tuning and rectangle order witnesses {fn:x}', fn,
                   construct(True, 5, 1.3333333730697632, 99, 64,
                             1.1777777671813965, 0.9133333563804626, 0x21, True),
                   receiver=lambda t: t['obj'], arguments=(lambda t: t['actor'],))
