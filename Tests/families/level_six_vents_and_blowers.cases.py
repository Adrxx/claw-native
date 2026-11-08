"""Independent original-based cases for the Level 6 vents and blowers."""
from clawparity.cases import Case


def u32(x):
    return x & 0xffffffff


def signed(x):
    return x if x < 0x80000000 else x - 0x100000000


def rect(env, address):
    return [signed(env.get(address + i * 4)) for i in range(4)]


def base(seed, *, anim=False, frame=1, finished=0, pause=0, delay=19, elapsed=0,
         state=0x12345678, strength=17, actor_rect=(-4, -8, 9, 12), actor_flag=0):
    def setup(env):
        receiver = env.object(0x80, 'logic', data=seed[:0x80])
        actor = env.object(0x240, 'actor', fill=0)
        data = env.object(0xc0, 'logic-data', fill=0)
        world = env.object(0x80, 'world', fill=0)
        for off in (0x10, 0x14, 0x2c):
            table = env.object(0x40, 'resource-table', fill=0)
            env.put(table + 0x18, 1)
            env.put(world + off, table)
        env.put(actor + 0xc, world)
        env.put(actor + 0x6c, data)
        env.put(actor + 0x16c, frame)
        env.put(actor + 0x118, *map(u32, actor_rect))
        env.put(actor + 0x4c, 103, u32(-211))
        env.put(actor + 0x64, actor_flag)
        env.put(actor + 8, 0x11441155)
        env.put(actor + 0x190, 0)
        env.put(actor + 0x138, 0x99887766, 0x778899aa, 0xaabbccdd, 0x33445566)
        env.put(data + 0x1c, state)
        env.put(data + 0x38, u32(strength))
        env.put(data + 0xb8, delay)
        env.put(receiver + 8, actor, actor, data)
        env.put(receiver + 0x28, actor, actor, data, 0x3456789a)
        env.put(receiver + 0x48, 0, delay, 0xfffffff0, delay)
        env.put(0x537210, u32(0xfffffff0 + elapsed))
        env.put(0x5430c4, 3)
        env.put(0x537668 + 0x18, 0)
        env.put(actor + 0x18c, actor)
        env.put(actor + 0x19c, pause)
        env.put(actor + 0x1a4, finished)
        animation = 0
        if anim:
            command = env.object(0x30, 'animation-command', fill=0)
            env.put(command + 0xc, 9)
            env.put(command + 0x1c, 0x98765432)
            pointers = env.object(4, 'animation-commands', words=[command])
            animation = env.object(0x18, 'animation', fill=0)
            env.put(animation + 0xc, pointers, 1)
            env.put(actor + 0x190, animation, command, 0, pause, 1, finished,
                    0x12344321, 0x56788765, 0x3f800000)
        player = env.object(0x240, 'player', fill=0)
        env.put(player + 0x4c, 102, u32(-210))
        env.put(player + 0x118, *map(u32, (-8, -9, 8, 9)))
        env.put(0x537e88, player)
        def copy(e, call):
            e.write(call.arguments[0], e.read(call.arguments[1], 16))
            return 1
        def empty(e, call):
            l,t,r,b = rect(e, call.arguments[0])
            return int(l >= r or t >= b)
        def intersect(e, call):
            a, b = rect(e, call.arguments[1]), rect(e, call.arguments[2])
            result = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
            valid = result[0] < result[2] and result[1] < result[3]
            e.put(call.arguments[0], *map(u32, result if valid else (0, 0, 0, 0)))
            return int(valid)
        env.override(0x546d58, copy)
        env.override(0x546d4c, empty)
        env.override(0x546ce0, intersect)
        return dict(receiver=receiver, actor=actor, data=data, world=world, animation=animation, player=player)
    return setup


def state_lookup(setup, name, value):
    def configured(env):
        t = setup(env)
        key = env.object(len(name) + 1, 'state-key', data=name + b'\0')
        node = env.object(0x14, 'state-node', fill=0)
        env.put(node, node, node, 0, key, value)
        env.put(0x537668 + 0x18, node)
        return t
    return configured


def constructor(setup, *, image=False, resource=False, mutate=False):
    def configured(env):
        t = setup(env)
        # Construction must publish every base pointer, even if callers reused
        # receiver storage that previously referred to a different actor.
        prior = env.object(0x240, 'previous-constructor-actor', data=env.read(t['actor'], 0x240))
        env.put(t['receiver'] + 0x28, prior)
        if image:
            picture = env.object(0x30, 'sprite', fill=0)
            env.put(picture + 0x18, 17, 23, 7, 11)
            env.put(t['actor'] + 0x174, picture)
        if resource:
            # One bucket holds a real animation lookup; all other lookup tables stay empty.
            table = env.get(t['world'] + 0x2c) + 0x10
            key = b'LEVEL_GOOVENT_GOOVENT' if resource == 'goo' else b'LEVEL_GROUNDBLOWER'
            text = env.object(len(key) + 1, 'animation-key', data=key + b'\0')
            node = env.object(16, 'animation-node', words=[0, 0, text, t['animation']])
            buckets = env.object(4, 'animation-buckets', words=[node])
            env.put(table + 4, buckets, 1)
        if mutate:
            # A physical rectangle service may change actor fields before the caller re-reads them.
            def copy(e, call):
                e.write(call.arguments[0], e.read(call.arguments[1], 16))
                e.put(t['actor'] + 0x64, 0x55667788)
                e.put(t['actor'] + 8, 0x89abcdef)
                e.put(t['actor'] + 0x118, 3, 7, 15, 31)
                return 1
            env.override(0x546d58, copy)
        return t
    return configured


def dispatch(seed, table, index, *, callback=True, low=4, high=6, stride=4, grow_again=False):
    def setup(env):
        obj = env.object(0x80, 'dispatch-receiver', data=seed[:0x80])
        log = env.object(32, 'callback-log', fill=0)
        def effect(e, call):
            e.put(log, call.receiver, e.get(table + 0x20), e.get(table + 8), e.get(table + 0xc))
            e.put(log + 16, e.get(obj + 0x1c), e.get(obj + 0x24))
            return 0x24681357
        entries = env.object(max(4, (high-low+1)*stride), 'dispatch-table', fill=0)
        for i in range(high-low+1):
            def selected(e, call, slot=i):
                result = effect(e, call)
                e.put(log + 24, slot, 0x81234567 + slot)
                e.put(obj + 0x38, 0xface0000 + slot)
                return result
            fn = env.stub(f'state-handler-{i}', 'thiscall', 0, selected) if callback else 0
            env.put(entries + i*stride, fn)
        error = env.object(0x20, 'dispatch-error', fill=0)
        env.put(error + 0xc, 4)
        env.put(table + 4, error, u32(low), u32(high), entries, entries, stride, 0xfeedface, 0xa5a55a5a)
        # A grown empty entry falls back to the receiver RTTI.
        rtti = env.object(16, 'rtti', fill=0)
        descriptor = env.object(16, 'type-descriptor', fill=0)
        vtable = env.object(12, 'rtti-vtable', fill=0)
        env.put(vtable, rtti)
        env.put(rtti + 0xc, descriptor)
        env.put(obj, vtable+4)
        if grow_again:
            def realloc(e, call):
                n = e.calls_so_far(0x4a9070)
                p = e.object(max(4, call.arguments[1]), 'grown-table', fill=0)
                e.write(p, e.read(call.arguments[0], 4))
                if n == 1:
                    e.put(table + 0xc, u32(index-1))
                return p
            env.override(0x4a9070, realloc)
        return dict(receiver=obj)
    return setup


def case(label, address, setup, arguments=()):
    return Case(label, address, setup, receiver=lambda t:t['receiver'], arguments=arguments)


def cases(random_source):
    seed = bytes(random_source.randrange(256) for _ in range(0xc0))
    for f, table in ((0x448850, 0x5377b8), (0x448e30, 0x5377e8)):
        for index in (4, 5, 6, 3, 7, -1):
            yield case(f'dispatch {f:x} index {index}', f, dispatch(seed, table, index), (u32(index),))
        yield case(f'dispatch {f:x} stride 12', f, dispatch(seed, table, 5, stride=12), (5,))
        yield case(f'dispatch {f:x} null callback RTTI', f, dispatch(seed, table, 5, callback=False), (5,))
        yield case(f'dispatch {f:x} both growth sites', f, dispatch(seed, table, 3, stride=0, grow_again=True), (3,))
    for addr, key in ((0x448b00, b'LS_IDLE'), (0x449270, b'ES_IDLE')):
        for anim in (False, True):
            for state in (0, 0xa5a55a5a):
                s = base(seed, anim=anim, state=state)
                def put_resource(env, s=s, addr=addr):
                    t=s(env)
                    env.put(t['receiver'] + (0x48 if addr==0x448b00 else 0x4c), t['animation'])
                    return t
                s=put_resource
                yield case(f'set idle {addr:x} anim {anim} state {state}', addr, state_lookup(s,key,0x6789abcd))
    for frame in (0,1,2,3,4,5,6,7,8,9,10,0xffffffff):
        for elapsed in (18,19,20):
            yield case(f'goo tick frame {frame} elapsed {elapsed}',0x448b50,base(seed,frame=frame,elapsed=elapsed))
    for finished,pause in ((1,0),(1,1),(0,0)):
        yield case(f'goo restart finished {finished} pause {pause}',0x448b50,base(seed,finished=finished,pause=pause,elapsed=20))
    for delta in (0,1,0x80000000,0xffffffff):
        yield case(f'goo unsigned elapsed {delta}',0x448b50,base(seed,elapsed=delta,delay=0x80000000))
    for addr in (0x4486e0,0x4490e0):
        rects=((0,0,0,0),(1,2,3,4),(0,2,3,4),(0,0,3,4),(0,2,0,4),(0,0,0,4),(7,9,3,4)) if addr==0x4490e0 else ((1,2,3,4),)
        for r in rects:
            for flag in (0,1,0xffffffff):
                yield case(f'constructor {addr:x} rect {r} flag {flag}',addr,constructor(base(seed,actor_rect=r,actor_flag=flag)),(lambda t:t['actor'],))
        yield case(f'constructor {addr:x} resource and sprite',addr,constructor(base(seed,anim=True,actor_rect=(0,0,0,0)),resource='goo' if addr==0x4486e0 else 'blower',image=True),(lambda t:t['actor'],))
    yield case('blower rereads fields after CopyRect',0x4490e0,constructor(base(seed),mutate=True),(lambda t:t['actor'],))
    for frame in (0,1,2,0xffffffff):
        for strength in (-7,0,1,0x7fffffff):
            for overlap in (False,True):
                def setup(env,frame=frame,strength=strength,overlap=overlap):
                    t=base(seed,frame=frame,strength=strength)(env)
                    if not overlap:
                        env.put(t['player']+0x4c, 10000, 20000)
                    return t
                yield case(f'blower frame {frame} strength {strength} overlap {overlap}',0x4492c0,setup)

    for strength in (-1,0,1,17,450,1000):
        def launch(env,strength=strength):
            t=base(seed,frame=1,strength=strength)(env)
            player_data=env.object(0xc0,'player-logic-data',fill=0)
            player_state=env.object(0x140,'player-state',fill=0)
            manager=env.object(0x20,'game-manager',fill=0)
            env.put(0x537204,manager)
            env.put(t['player']+0xc,t['world'])
            env.put(t['player']+0x6c,player_data)
            env.put(t['player']+0xd0,2)
            env.put(player_data+0x14,player_state)
            env.put(player_data+0x1c,9)
            return t
        yield case(f'blower launches player strength {strength}',0x4492c0,launch)

    # Signed bounds and distinct callbacks make slot selection and stride observable.
    for f, table in ((0x448850, 0x5377b8), (0x448e30, 0x5377e8)):
        for low in (-9, -1, 0, 0x7ffffffb):
            for offset in (0, 1, 2):
                stride = random_source.choice((4, 8, 12, 20))
                yield case(f'signed slots {f:x} {low}+{offset} stride {stride}', f,
                           dispatch(seed, table, low+offset, low=low, high=low+2, stride=stride),
                           (u32(low+offset),))

    # Give each pointer-bearing receiver field its own valid target. This distinguishes
    # actor +0x0c from +0x2c and primary logic data from the cached secondary pointer.
    for n in range(24):
        sample = bytes(random_source.randrange(256) for _ in range(0xc0))
        frame = random_source.choice((0,1,2,3,4,5,6,7,8,9,10,0xffffffff))
        elapsed = random_source.choice((0,18,19,20,0x7fffffff,0xffffffff))
        state = random_source.getrandbits(32)
        delay = random_source.choice((0,1,19,0x80000000,0xffffffff))
        def separated(env, sample=sample, frame=frame, elapsed=elapsed, state=state, delay=delay):
            t = base(sample, frame=frame, elapsed=elapsed, state=state, delay=delay)(env)
            for off in (8, 0xc, 0x28):
                actor = env.object(0x240, f'distinct-actor-{off:x}', data=env.read(t['actor'],0x240))
                env.put(actor+0x4c, 0x12340000+off, 0x56780000+off)
                env.put(actor+0x16c, 11)
                env.put(t['receiver']+off, actor)
            for off in (0x10, 0x30):
                data = env.object(0xc0, f'distinct-data-{off:x}', data=env.read(t['data'],0xc0))
                env.put(data+0x1c, u32(state+off))
                env.put(t['receiver']+off, data)
            return t
        for address in (0x448b00, 0x449270, 0x448b50, 0x4492c0):
            def configured(env, address=address, separated=separated):
                t = separated(env)
                if address == 0x449270:
                    env.put(t['receiver']+0x4c, 0)
                return t
            yield case(f'distinct receiver pointers {n} {address:x}',address,configured)

    # IntersectRect is allowed to publish changed game state before the caller
    # reads strength and player again. Preserve every observation in live memory.
    for strength in (-1,0,1,451,1234):
        def changed_collision(env, strength=strength):
            t = base(seed, frame=1, strength=7)(env)
            alternate = env.object(0x240, 'replacement-player', data=env.read(t['player'],0x240))
            data = env.object(0xc0, 'replacement-player-data', fill=0)
            state = env.object(0x140, 'replacement-player-state', fill=0)
            manager = env.object(0x20, 'replacement-game-manager', fill=0)
            env.put(0x537204, manager)
            env.put(alternate+0xc, t['world'])
            env.put(alternate+0x6c, data)
            env.put(alternate+0xd0, 2)
            env.put(data+0x14, state, 0, 9)
            env.put(alternate+0x50, 321)
            log = env.object(48, 'intersection-observations', fill=0)
            def intersect(e, call):
                a, b = rect(e,call.arguments[1]), rect(e,call.arguments[2])
                e.put(log, *call.arguments)
                e.put(log+12, *map(u32,a), *map(u32,b))
                result = [max(a[0],b[0]), max(a[1],b[1]), min(a[2],b[2]), min(a[3],b[3])]
                valid = result[0]<result[2] and result[1]<result[3]
                e.put(call.arguments[0], *map(u32,result if valid else (0,0,0,0)))
                e.put(t['data']+0x38, u32(strength))
                e.put(0x537e88, alternate)
                return int(valid)
            env.override(0x546ce0, intersect)
            return t
        yield case(f'collision republishes strength and player {strength}',0x4492c0,changed_collision)

    # The old animation and the replacement resource are independent. Saving
    # animation state after initializing the replacement loses the old pointer.
    for address, key in ((0x448b00,b'LS_IDLE'), (0x449270,b'ES_IDLE')):
        for old_present, new_present in ((False,True),(True,False),(True,True)):
            for n in range(3):
                sample = bytes(random_source.randrange(256) for _ in range(0xc0))
                def replace_animation(env, address=address, old_present=old_present,
                                      new_present=new_present, sample=sample, n=n):
                    t = base(sample, anim=True, state=0x12340000+n)(env)
                    replacement = t['animation'] if new_present else 0
                    old = 0
                    if old_present:
                        old = env.object(0x18, 'previous-animation', data=env.read(t['animation'],0x18))
                    env.put(t['actor']+0x190, old)
                    env.put(t['receiver']+(0x48 if address==0x448b00 else 0x4c), replacement)
                    return t
                yield case(f'replace animation {address:x} old {old_present} new {new_present} {n}',
                           address, state_lookup(replace_animation,key,0x718293a4))
