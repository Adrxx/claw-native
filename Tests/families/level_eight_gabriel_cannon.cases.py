"""Original-driven cases for the Gabriel cannon controller."""
from clawparity.cases import Case
from clawparity.fixtures import returns


def dictionary(env, entries):
    owner = env.object(0x1c, 'resource dictionary')
    buckets = env.object(4, 'resource bucket')
    env.put(owner + 0x14, buckets, 1)
    head = 0
    for key, value in entries:
        text = env.object(len(key) + 1, 'resource key', data=key.encode() + b'\0')
        node = env.object(16, 'resource node', words=[head, 0xBAD123, text, value])
        head = node
    env.put(buckets, head)
    return owner


def animation(env, value):
    command = env.object(0x30, 'animation command', fill=0)
    env.put(command + 0xc, 9)
    env.put(command + 0x18, 3, value)
    array = env.object(4, 'animation commands', words=[command])
    result = env.object(0x14, 'animation', fill=0)
    env.put(result + 0xc, array, 1)
    return result


def state_tree(env, key, value):
    env.put(0x537680, 0)
    if key:
        text = env.object(len(key) + 1, 'state name', data=key.encode() + b'\0')
        node = env.object(0x14, 'state node')
        env.put(node, node, node, 0, text, value)
        env.put(0x537680, node)


def scene(salt, **options):
    def setup(env):
        c = env.object(0x98, 'cannon', fill=(salt & 255) or 0x79)
        o = env.object(0x1b4, 'sprite object', fill=0)
        motion = env.object(0x1b4, 'motion object', fill=0x68)
        s = env.object(0x24, 'logic state', fill=0x45)
        g = env.object(0x538, 'boss', fill=0x36)
        record = env.object(0x100, 'callback observations', fill=0)
        env.put(s + 0x18, c, options.get('state', salt))
        env.put(o + 0x6c, s)
        env.put(c + 0xc, motion, s)
        env.put(c + 0x2c, o, s)
        env.put(c + 0x48, 0, 0, 0, 0)
        env.put(c + 0x7c, 0, 0, 0, 0)
        env.put(c + 0x8c, options.get('pending', 0), options.get('raised', 0), salt ^ 0x12345)
        env.put(c + 0x70, options.get('orientation', 0))
        env.put(g + 0x518, options.get('fire', 0), options.get('rise', 0), options.get('busy', 0))
        env.put(g + 0x534, options.get('reset', 0))
        env.put(0x53774c, g if options.get('boss', True) else 0)
        env.put(0x532c0c, options.get('sound_enabled', 0), salt)
        env.put(0x5430c4, options.get('ticks', 1))
        env.put(0x540e00, 0)
        for at in (0x54130c, 0x541310, 0x541314, 0x541318):
            env.put(at, 0)
        state_tree(env, options.get('state_key', 'LS_ROTATE'), salt ^ 0x1234)
        home = animation(env, salt ^ 0x1357)
        rise = animation(env, salt ^ 0x2468)
        rest = animation(env, salt ^ 0x3579)
        env.put(c + 0x48, home if options.get('animations', True) else 0)
        env.put(c + 0x4c, rise if options.get('animations', True) else 0, rest if options.get('animations', True) else 0)
        env.put(c + 0x7c, rise if options.get('animations', True) else 0, rest if options.get('animations', True) else 0)
        current = animation(env, salt ^ 0x468a)
        env.put(o + 0x18c, o, current if options.get('current', False) else 0)
        env.put(o + 0x194, 0)
        env.put(o + 0x19c, options.get('delay', 0), options.get('timed', 0), options.get('done', 0))
        env.put(o + 0x1a8, salt ^ 0x579b, salt ^ 0x68ac, 0x3f800000)
        if options.get('current', False):
            env.put(o + 0x194, env.get(env.get(current + 0xc)))
        if options.get('sprite', True):
            frames = env.object(16, 'frames', words=[salt ^ 0x101, salt ^ 0x202, salt ^ 0x303, salt ^ 0x404])
            sprite = env.object(0x6c, 'sprite resource')
            env.put(sprite + 0x14, frames)
            env.put(sprite + 0x64, options.get('first', 0), options.get('last', 3))
            env.put(o + 0x170, sprite)
        env.put(o + 0x16c, salt ^ 0x777)
        env.put(o + 0x174, salt ^ 0x888)
        sound_manager = env.object(0x7c, 'sound manager', fill=0)
        playback = env.object(0x30, 'sound playback', fill=0)
        env.put(playback + 0x10, sound_manager)
        handle = env.object(0x14, 'sound handle')
        env.put(handle + 0x10, playback)
        if options.get('sound', False):
            env.put(c + 0x84, handle, handle)
        manager = env.object(0x30, 'resource manager')
        empty = dictionary(env, [])
        env.put(manager + 0x10, empty, empty)
        env.put(manager + 0x28, empty, empty)
        env.put(o + 0xc, manager)
        env.put(o + 0x40, options.get('facing', 0))
        vtable = env.object(0x24, 'controller methods')
        def callback(slot):
            def effect(env, call):
                n = env.get(record)
                env.put(record + 4 + n * 24, slot, call.receiver, call.arguments[0] if call.arguments else 0,
                        env.get(s + 0x18), env.get(s + 0x1c), env.get(c + 0x8c))
                env.put(record, n + 1)
                return salt ^ slot
            return effect
        for slot in (4, 8, 12, 16, 28, 32):
            env.put(vtable + slot, env.stub('controller method %d' % slot, 'thiscall', 1 if slot in (4, 8, 12) else 0, callback(slot)))
        env.put(c, vtable)
        if options.get('constructor', False):
            mask = options.get('mask', 127)
            keys = ['LEVEL_GABRIELCANNON_HORZFIRE', 'LEVEL_GABRIELCANNON_VERTIFIRE', 'LEVEL_GABRIELCANNON_RISE', 'LEVEL_GABRIELCANNON_REST', 'LEVEL_GABRIELCANNON_CANNONRISE', 'LEVEL_GABRIELCANNON_CANNONDROP', 'LEVEL_GABRIELCANNON_CANNON']
            values = [animation(env, salt ^ (i + 9) * 0x153) for i in range(4)]
            for i in range(3):
                resource = env.object(0x14, 'sound resource %d' % i, fill=0x30 + i)
                env.put(resource + 0x10, playback)
                values.append(resource)
            entries = [(key, values[i]) for i, key in enumerate(keys) if mask & (1 << i)]
            env.put(manager + 0x2c, dictionary(env, entries[:sum(bool(mask & (1 << i)) for i in range(4))]))
            env.put(manager + 0x28, dictionary(env, [(key, values[i]) for i, key in enumerate(keys) if i >= 4 and mask & (1 << i)]))
            env.put(manager + 0x10, dictionary(env, [('LEVEL_GABRIELCANNON', env.get(o + 0x170))] if options.get('sprite', True) else []))
        return dict(c=c, o=o, s=s, g=g, record=record, callback=callback, manager=manager)
    return setup


def registry(env, base, low, high, callback, stride=4):
    table = env.object((high - low + 1) * stride, 'dispatch table', fill=0x6d)
    for i in range(high - low + 1):
        env.put(table + i * stride, callback)
    handler = env.object(0x18, 'error handler')
    env.put(handler + 0xc, 4)
    fallback = env.object(4, 'fallback slot', words=[callback])
    env.put(base + 4, handler, low, high, table, fallback, stride, 0, 0x123456)
    return table


def dispatch_setup(salt, event, low, high, missing=False, stride=4, fail=False):
    def setup(env):
        t = scene(salt)(env)
        cb = env.stub('dispatch callback', 'thiscall', 0, t['callback'](0x55))
        registry(env, 0x537788, low, high, 0 if missing else cb, stride)
        registry(env, 0x534bf8, min(low, event), max(high, event), cb, stride)
        if fail:
            env.override(0x4a9070, returns(0))
        return t
    return setup


def logic_setup(salt, state, **options):
    def setup(env):
        t = scene(salt, state=state, **options)(env)
        text = env.object(20, 'state string header', words=[1, 3, 7], data=None)
        env.write(text + 12, b'abc\0')
        table = env.object(4, 'state strings', words=[text + 12])
        env.put(0x5376a0, state, state, table, table, 4, 0, 0)
        return t
    return setup


def cases(random_source):
    # Every resource independently hits and misses, in both facing directions.
    for facing in (0, 2):
        for mask in range(128):
            salt = random_source.randrange(1, 0x7fffffff)
            yield Case('construct facing=%d resources=%02x' % (facing, mask), 0x446a70,
                       scene(salt, constructor=True, mask=mask, facing=facing),
                       receiver=lambda t: t['c'], arguments=(lambda t: t['o'],))
    for boss in (False, True):
        for first, last in ((0, 3), (1, 1), (-1, 1), (2, 3), (0, 0), (0x80000000, 0x7fffffff)):
            yield Case('reset %s %d %d' % (boss, first, last), 0x446c20,
                       scene(random_source.randrange(1, 0x7fffffff), boss=boss, first=first, last=last, pending=7, raised=9, reset=0xabcdef01, state_key='LS_HOME'), receiver=lambda t: t['c'])
    yield Case('reset without sprite', 0x446c20, scene(0x123, sprite=False), receiver=lambda t: t['c'])
    for function in (0x446d70, 0x446e10):
        for boss in (False, True):
            for sound, enabled in ((False, 1), (True, 0), (True, 1)):
                for animations in (False, True):
                    yield Case('motion %x boss=%s sound=%s enabled=%d anim=%s' % (function, boss, sound, enabled, animations), function,
                               scene(random_source.randrange(1, 0x7fffffff), boss=boss, sound=sound, sound_enabled=enabled, animations=animations, rise=17, raised=7, pending=9), receiver=lambda t: t['c'])
    for boss in (False, True):
        for busy in (0, 8):
            for reset in (0, 0xabcdef01):
                for pending, raised, rise, fire in ((0, 0, 0, 0), (1, 1, 1, 1), (1, 0, 0, 1), (0, 0, 1, 1), (0, 1, 1, 1), (0, 1, 0, 0), (0, 0, 0, 1), (1, 0, 0, 0)):
                    yield Case('update %s %d %x %d%d%d%d' % (boss, busy, reset, pending, raised, rise, fire), 0x446ca0,
                               scene(random_source.randrange(1, 0x7fffffff), boss=boss, busy=busy, reset=reset, pending=pending, raised=raised, rise=rise, fire=fire, orientation=raised), receiver=lambda t: t['c'])
    for current in (False, True):
        for done in (0, 1, 0x80000000):
            for delay in (0, 1, 2, 17):
                yield Case('rotate anim=%s done=%x delay=%d' % (current, done, delay), 0x446eb0,
                           scene(random_source.randrange(1, 0x7fffffff), current=current, done=done, delay=delay), receiver=lambda t: t['c'])
    for state in (0, 1, 28, 29, 30, 31, 999, 1000, 1001, 0xffffffff, 0x80000000):
        yield Case('logic state=%x' % state, 0x446550, logic_setup(random_source.randrange(1, 0x7fffffff), state, constructor=state == 0), arguments=(lambda t: t['o'],))
    for low, high, event in ((-2, 2, -2), (-2, 2, 0), (-2, 2, 2), (0, 2, -1), (-2, 0, 1), (-9, -3, -6), (0x7ffffffd, 0x7fffffff, 0x7fffffff), (-0x80000000, -0x7ffffffe, -0x80000000)):
        for missing in (False, True):
            for stride in (4, 12):
                yield Case('dispatch %d..%d id=%d missing=%s stride=%d' % (low, high, event, missing, stride), 0x446670,
                           dispatch_setup(random_source.randrange(1, 0x7fffffff), event, low, high, missing, stride), receiver=lambda t: t['c'], arguments=(event,))

    def distinct_sprite(salt, found):
        def setup(env):
            t = scene(salt, constructor=True)(env)
            selected = env.object(0x6c, 'different selected sprite', fill=0)
            frames = env.object(16, 'different selected frames', words=[salt, salt ^ 0xfeed, salt ^ 0xbeef, salt ^ 0x1234])
            env.put(selected + 0x14, frames)
            env.put(selected + 0x64, 0, 3)
            env.put(t['manager'] + 0x10, dictionary(env, [('LEVEL_GABRIELCANNON', selected)] if found else []))
            return t
        return setup

    for found in (False, True):
        yield Case('constructor replaces prior sprite found=%s' % found, 0x446a70,
                   distinct_sprite(random_source.randrange(1, 0x7fffffff), found),
                   receiver=lambda t: t['c'], arguments=(lambda t: t['o'],))

    def animation_velocity_alias(salt, function):
        def setup(env):
            t = scene(salt)(env)
            motion = env.get(t['c'] + 0xc)
            command = motion + 0x12c
            env.write(command, bytes(0x30))
            env.put(command + 0xc, 9)
            env.put(command + 0x18, 3, salt)
            array = env.object(4, 'velocity alias animation commands', words=[command])
            resource = env.object(0x14, 'velocity alias animation', fill=0)
            env.put(resource + 0xc, array, 1)
            env.put(t['c'] + (0x7c if function == 0x446d70 else 0x80), resource)
            return t
        return setup

    for function in (0x446d70, 0x446e10):
        yield Case('motion %x command value aliases horizontal velocity' % function, function,
                   animation_velocity_alias(random_source.randrange(1, 0x7fffffff), function), receiver=lambda t: t['c'])

    def constructor_alias(salt, delta, boss_alias=False):
        def setup(env):
            t = scene(salt, constructor=True)(env)
            old_o = env.read(t['o'], 0x1b4)
            old_c = env.read(t['c'], 0x98)
            sprite = env.get(t['o'] + 0x170)
            joint = env.object(0x900, 'overlapping sprite and controller', fill=0)
            o = joint + 0x400
            c = o + delta
            env.write(o, old_o)
            env.write(c, old_c)
            env.put(o + 0xc, t['manager'])
            env.put(o + 0x40, 0)
            env.put(o + 0x6c, t['s'])
            env.put(o + 0x170, sprite)
            env.put(c + 0xc, o, t['s'])
            env.put(c + 0x2c, o)
            env.put(t['s'] + 0x18, c)
            if boss_alias:
                env.put(0x53774c, o + 0x170 - 0x51c)
            t.update(c=c, o=o)
            return t
        return setup

    for delta, boss_alias in ((0x170, False), (0x118, True), (0x110, True)):
        yield Case('constructor overlaps object delta=%x boss-alias=%s' % (delta, boss_alias), 0x446a70,
                   constructor_alias(random_source.randrange(1, 0x7fffffff), delta, boss_alias),
                   receiver=lambda t: t['c'], arguments=(lambda t: t['o'],))
