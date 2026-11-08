"""Original-derived Red Tail wind/spike cases."""
from clawparity.cases import Case
from clawparity.fixtures import sequence, returns


def obj(env, *args, **kwargs):
    kwargs.setdefault('fill', 0)
    return env.object(*args, **kwargs)


def signed(v):
    return v - 0x100000000 if v & 0x80000000 else v


def registry(env, table, pairs):
    bucket = obj(env, 4, 'class registry bucket')
    head = 0
    for name, value in pairs:
        key = obj(env, len(name) + 1, 'registry key', data=name.encode() + b'\0')
        head = obj(env, 16, 'registry node', words=[head, 0, key, value])
    env.put(bucket, head)
    env.put(table + 4, bucket, 1)


def state_registry(env, salt):
    leaves = []
    for name, value in [('ES_BLOW', salt ^ 0x1234), ('ES_IDLE', salt ^ 0x5678)]:
        text = obj(env, len(name) + 1, 'state name', data=name.encode() + b'\0')
        node = obj(env, 20, 'state leaf')
        env.put(node, node, node, 0, text, value)
        leaves.append(node)
    root = obj(env, 20, 'state tree', words=[*leaves, 24, 0, 0])
    env.put(0x537668 + 0x18, root)


def setup_world(salt, sound=0, player=True, red=True, active=1, now=1000, create=False, mutate=False):
    def setup(env):
        receiver = obj(env, 0x90, 'wind logic', fill=0x95)
        actor = obj(env, 0x600, 'wind actor', fill=0x75)
        logic = obj(env, 0x100, 'logic context', fill=0x46)
        scene = obj(env, 0x100, 'scene')
        definitions = obj(env, 0x50, 'definitions')
        game = obj(env, 0x100, 'game')
        env.put(receiver + 0x10, logic)
        env.put(receiver + 0x2c, actor)
        env.put(logic + 0xc, scene)
        env.put(logic + 0x1c, salt)
        env.put(actor + 0xc, scene)
        env.put(actor + 0x6c, logic)
        env.put(actor + 0x70, 0)
        env.put(actor + 0x78, 0)
        env.put(actor + 0x174, 0)
        env.put(scene + 0x14, definitions)
        env.put(scene + 0x28, game)
        registry(env, definitions + 0x10, [])
        registry(env, game + 0x10, [])
        state_registry(env, salt)
        target = obj(env, 0x600, 'player', fill=0x31)
        target_context = obj(env, 0x30, 'player context')
        player_body = obj(env, 0x100, 'player body', fill=0x21)
        env.put(target + 0x6c, target_context)
        env.put(target_context + 0x14, player_body if player else 0)
        env.put(target + 0x4c, 15, 25)
        env.put(0x537e88, target)
        boss = obj(env, 0x600, 'red tail', fill=0x63)
        env.put(boss + 0x4e4, active)
        env.put(0x53c19c, boss if red else 0)
        env.put(0x537210, now)
        env.put(0x52b34c, salt)
        env.put(0x52b350, 600)
        env.put(0x52b354, 10, 30, 20, 40)
        env.put(0x532c0c, int(sound == 3))
        env.put(receiver + 0x4c, now - 20, 100, now, 100)
        env.put(receiver + 0x48, 0)
        receipt = obj(env, 0x100, 'callback receipts')
        if sound:
            sound_desc = obj(env, 0x20, 'sound descriptor')
            sound_obj = obj(env, 0x30, 'sound object')
            sound_manager = obj(env, 0x100, 'sound manager')
            dsound = obj(env, 8, 'DirectSound buffer')
            methods = obj(env, 0x60, 'DirectSound methods')
            env.put(sound_desc + 0x10, sound_obj)
            env.put(sound_obj + 0xc, dsound)
            env.put(sound_obj + 0x10, sound_manager)
            env.put(sound_manager + 0x78, int(sound == 2))
            env.put(dsound, methods)
            def status(e, call):
                e.put(call.arguments[1], 1 if sound == 2 else 0)
                e.put(receipt, call.arguments[0], call.receiver, e.get(receiver + 0x24))
                if mutate:
                    e.put(sound_manager + 0x78, 0)
                return 0
            env.put(methods + 0x18, env.stub('DirectSound GetVolume', 'stdcall', 2, lambda e,c: (e.put(c.arguments[1], 0) or 0)))
            env.put(methods + 0x24, env.stub('DirectSound GetStatus', 'stdcall', 2, status))
            env.put(receiver + 0x48, sound_desc)
            registry(env, game + 0x10, [('LEVEL_REDTAIL_WINDWHISTLING', sound_desc)])
        env.override(0x4a3050, sequence(0, 180, 10000, 100, 90, 50))
        env.override(0x546df0, returns(now))
        def pt(e, call):
            p, x, y = call.arguments
            l, t, r, b = (signed(e.get(p + i)) for i in (0, 4, 8, 12))
            e.put(receipt + 0x20, l, t, r, b, x, y)
            return int(l <= signed(x) < r and t <= signed(y) < b)
        env.override(0x546cd4, pt)
        if True:
            creator = obj(env, 0x40, 'object creator')
            env.put(scene + 8, creator)
            env.put(creator + 0xc, scene)
            env.put(creator + 0x28, 4)
            descriptor = obj(env, 0x20, 'WindDebris class')
            record = obj(env, 0x20, 'WindDebris definition')
            env.put(record + 8, 0)
            env.put(record + 0x10, descriptor)
            def initialize(e, call):
                debris = call.arguments[0]
                context = e.get(debris + 0x6c)
                body = obj(e, 0x200, 'new debris body', fill=0x37)
                e.put(context + 0x18, body)
                e.put(receipt + 0x40, debris, context, e.get(debris + 0x4c), e.get(debris + 0x50), e.get(debris + 0x64))
                if mutate:
                    new_context = obj(e, 0x40, 'callback replaced context')
                    e.put(new_context + 0x18, body)
                    e.put(debris + 0x6c, new_context)
                    e.put(0x537210, now + 17)
                return salt
            env.put(record + 0x10, env.stub('WindDebris initialize', 'cdecl', 1, initialize))
            if create:
                registry(env, definitions + 0x10, [('WindDebris', record)])
        return dict(receiver=receiver, actor=actor, logic=logic, scene=scene, definitions=definitions, game=game, target=target, boss=boss, receipt=receipt)
    return setup


def dispatch_setup(base, salt, index, present, fail=False):
    def setup(env):
        receiver = obj(env, 0x90, 'dispatch receiver', fill=0x43)
        receipt = obj(env, 0x40, 'dispatch receipt')
        def callback(e, call):
            e.put(receipt, call.receiver, e.get(base + 0x20), e.get(base + 8), e.get(base + 0xc))
            return salt
        fn = env.stub('state dispatch callback', 'thiscall', 0, callback)
        def other(e, call):
            e.put(receipt + 0x10, call.receiver, salt ^ 0x7abc)
            return salt ^ 0x2468
        other_fn = env.stub('different state callback', 'thiscall', 0, other)
        entries = obj(env, 24, 'state dispatch entries', words=[fn if present else 0, salt, other_fn, salt ^ 0x1234, fn, salt ^ 0x5678])
        fallback = obj(env, 8, 'fallback entry', words=[fn, salt])
        error = obj(env, 0x20, 'table error policy', words=[0, 0, 0, 4])
        env.put(base + 4, error, 3, 5, entries, fallback, 8, salt, salt)
        env.put(0x544d18, 0)
        if True:
            vtable_storage = obj(env, 16, 'RTTI vtable storage')
            rtti = obj(env, 20, 'RTTI locator')
            typeinfo = obj(env, 16, 'type descriptor')
            env.put(vtable_storage, rtti)
            env.put(rtti + 0xc, typeinfo)
            env.put(receiver, vtable_storage + 4)
        if fail:
            env.override(0x4a9070, returns(0))
        return dict(receiver=receiver)
    return setup


def cases(random_source):
    salt = random_source.randrange(1, 0x10000)
    for fn, base in [(0x4843d0, 0x53c1d8), (0x4848d0, 0x53c208)]:
        for index in [3, 4, 5, 2, 6]:
            yield Case(f'dispatch {fn:x} index {index}', fn, dispatch_setup(base, salt, index, True), receiver=lambda t:t['receiver'], arguments=(index,))
        yield Case(f'dispatch {fn:x} missing callback RTTI', fn, dispatch_setup(base, salt, 3, False), receiver=lambda t:t['receiver'], arguments=(3,))
    for rect in [None, (0, 0, 10, 20), (-17, -31, -2, 9), (0xffffffff, 0x80000000, 0x7fffffff, 0xffffffff)]:
        def constructor(env, rect=rect):
            t = setup_world(salt)(env)
            if rect is not None:
                box = obj(env, 0x30, 'spike geometry', fill=0x53)
                env.put(box + 0x18, *rect)
                env.put(t['actor'] + 0x174, box)
            return t
        yield Case(f'spike constructor rect {rect}', 0x484680, constructor, receiver=lambda t:t['receiver'], arguments=(lambda t:t['actor'],))
    for sound in [0, 1]:
        yield Case(f'wind constructor sound {sound}', 0x484ca0, setup_world(salt, sound=sound), receiver=lambda t:t['receiver'], arguments=(lambda t:t['actor'],))
    for fn in [0x484db0, 0x484e10, 0x484e30]:
        for red, active in [(False, 0), (True, 0), (True, 1), (True, 0xffffffff)]:
            for sound in [0, 1, 2, 3]:
                yield Case(f'state {fn:x} red{red} active{active} sound{sound}', fn, setup_world(salt, sound=sound, red=red, active=active, mutate=True), receiver=lambda t:t['receiver'])
    for point in [(9,25),(10,20),(15,25),(29,39),(30,25),(15,40),(0xffffffff,0x80000000)]:
        def geometry(env, point=point):
            t=setup_world(salt)(env)
            env.put(t['target']+0x4c,*point)
            return t
        yield Case(f'point {point}',0x484f00,geometry)
    for player in [False,True]:
        for flag in [0,1,0xffffffff]:
            yield Case(f'force player{player} flag{flag}',0x484f60,setup_world(salt,player=player),arguments=(flag,))
    for create in [False,True]:
        for mutate in [False,True]:
            for elapsed, duration in [(0,100),(99,100),(100,100),(101,100),(0,0),(0xffffffff,100)]:
                def debris(env, create=create, mutate=mutate, elapsed=elapsed, duration=duration):
                    t=setup_world(salt,create=create,mutate=mutate)(env)
                    env.put(t['receiver']+0x54,(1000-elapsed)&0xffffffff,duration)
                    return t
                yield Case(f'debris create{create} mutate{mutate} elapsed{elapsed} dur{duration}',0x484fa0,debris,receiver=lambda t:t['receiver'])
    for active in [0,1]:
        for elapsed in [0,99,100,101,0xffffffff]:
            for inside in [False,True]:
                def blow(env,active=active,elapsed=elapsed,inside=inside):
                    t=setup_world(salt,active=active)(env)
                    env.put(t['receiver']+0x4c,(1000-elapsed)&0xffffffff,100)
                    env.put(t['target']+0x4c,15 if inside else 30,25)
                    return t
                yield Case(f'blow active{active} elapsed{elapsed} inside{inside}',0x484ea0,blow,receiver=lambda t:t['receiver'])

    for values in [(0,0,0,0,0,0), (100,180,10000,100,90,49), (101,181,10001,101,91,50), (0xffffffff,0xfffffffe,0x80000000,0xffffffff,0xfffffffc,0xffffffff), (0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff,0x7fffffff,51)]:
        for strength in [0,1,0xffffffff,0x7fffffff,0x80000000]:
            def random_debris(env, values=values, strength=strength):
                t=setup_world(salt,create=True,mutate=True)(env)
                env.put(t['receiver']+0x54,900,100)
                env.put(0x52b34c,strength)
                env.override(0x4a3050,sequence(*values))
                return t
            yield Case(f'debris random values{values} strength{strength}',0x484fa0,random_debris,receiver=lambda t:t['receiver'])

    # Populate the original named lookups so the two constructor calls have
    # visible publications and can change fields that the caller reloads.
    for fn in (0x484680, 0x484ca0):
        for mode in range(4):
            for flags in (0, 2, 0xfffffffe):
                def populated_constructor(env, mode=mode, flags=flags):
                    t = setup_world(salt, sound=1)(env)
                    receiver, actor = t['receiver'], t['actor']
                    alternate = obj(env, 0x600, 'alternate constructor actor', fill=0x29)
                    env.put(alternate + 0xc, t['scene'])
                    env.put(alternate + 0x6c, t['logic'])
                    env.put(alternate + 0x70, 0)
                    env.put(alternate + 0x78, 0)
                    env.put(actor + 0x40, flags)
                    env.put(actor + 0x44, flags ^ 0xabcdef00)
                    next_logic = obj(env, 0x100, 'replacement actor context', fill=0x68)
                    env.put(next_logic + 0xc, t['scene'])
                    env.put(next_logic + 0x1c, salt ^ 0x9bcd)
                    records = []
                    for n, name in enumerate(('LogicHit', 'LogicAttack')):
                        descriptor = obj(env, 0x20, name + ' definition', fill=0x49 + n)
                        env.put(descriptor + 0x10, salt + n * 0x10001)
                        methods = obj(env, 0x30, name + ' component methods')
                        component = obj(env, 0x30, name + ' component', words=[methods])
                        def reset(e, call, n=n):
                            e.put(t['receipt'] + 0x60 + 4 * n, call.receiver)
                            return salt ^ n
                        def publish(e, call, n=n):
                            e.put(t['receipt'] + 0x80 + n * 0x30, call.receiver, *call.arguments,
                                  e.get(receiver), e.get(receiver + 8), e.get(receiver + 0xc),
                                  e.get(receiver + 0x10), e.get(receiver + 0x14),
                                  e.get(receiver + 0x28), e.get(receiver + 0x2c))
                            if mode & 1 and n == 0:
                                e.put(receiver + 0xc, alternate)
                            if mode & 2:
                                e.put(actor + 0x6c, next_logic)
                            return salt ^ (n + 0x7151)
                        env.put(methods + 0x1c, env.stub(name + ' reset', 'thiscall', 0, reset))
                        env.put(methods + 0x24, env.stub(name + ' publish', 'thiscall', 2, publish))
                        env.put(actor + (0x70 if n == 0 else 0x78), component)
                        env.put(alternate + (0x70 if n == 0 else 0x78), component)
                        records.append((name, descriptor))
                    registry(env, t['definitions'] + 0x10, records)
                    return t
                yield Case(f'constructor {fn:x} populated mode{mode} flags{flags}', fn,
                           populated_constructor, receiver=lambda t:t['receiver'],
                           arguments=(lambda t:t['actor'],))

    # Exercise scalar inputs that are independent of the random seed.
    for scale in (0.0, 0.125, -0.75, 1.3125, 1024.25):
        def scaled_spike(env, scale=scale):
            import struct
            t = setup_world(salt)(env)
            env.write(0x5262b0, struct.pack('<f', scale))
            box = obj(env, 0x30, 'distinct spike geometry', fill=0xa7)
            env.put(box + 0x18, 13, 41, 109, 317)
            env.put(t['actor'] + 0x174, box)
            return t
        yield Case(f'spike scale {scale}', 0x484680, scaled_spike,
                   receiver=lambda t:t['receiver'], arguments=(lambda t:t['actor'],))

    for fn in (0x484680, 0x484ca0):
        for offset in (0x10, 0x14, 0x18, 0x20, 0x28):
            if fn == 0x484ca0 and offset == 0x14:
                continue
            def aliased_constructor(env, offset=offset):
                t = setup_world(salt)(env)
                # One allocation backs both receiver and actor. All actor
                # pointers remain valid before constructor publication.
                storage = obj(env, 0x700, 'aliased receiver and actor', fill=0x82)
                actor = storage
                receiver = storage + offset
                env.put(actor + 0xc, t['scene'])
                env.put(actor + 0x6c, t['logic'])
                env.put(actor + 0x70, 0)
                env.put(actor + 0x78, 0)
                env.put(actor + 0x174, 0)
                t.update(receiver=receiver, actor=actor)
                return t
            yield Case(f'constructor {fn:x} alias offset{offset}', fn,
                       aliased_constructor, receiver=lambda t:t['receiver'],
                       arguments=(lambda t:t['actor'],))
