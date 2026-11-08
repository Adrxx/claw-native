"""Independent original-derived actor, controller and volume cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns, store_words


def world(env, active=True):
    root = env.object(0x80, 'game', fill=0)
    settings = env.object(0x40, 'settings', fill=0)
    controller = env.object(0x90, 'audio controller', fill=0)
    env.put(0x5371fc, root)
    env.put(0x53720c, 17)
    env.put(root + 0x10, 1)
    env.put(root + 0x5c, settings)
    env.put(settings + 0x24, 1)
    env.put(controller + 0x78, int(active))
    sound = env.object(0x30, 'sound', fill=0)
    interface = env.object(4, 'COM buffer')
    methods = env.object(0x60, 'COM methods', fill=0)
    env.put(interface, methods)
    env.put(methods + 0x18, env.stub('GetVolume', 'stdcall', 2, store_words(1, [0], 0)))
    env.put(methods + 0x24, env.stub('GetStatus', 'stdcall', 2, store_words(1, [1], 0)))
    for slot, argc in ((0x30, 4), (0x3c, 2), (0x40, 2), (0x44, 2), (0x48, 1)):
        env.put(methods + slot, env.stub('buffer method %x' % slot, 'stdcall', argc, returns(0)))
    env.put(sound + 0xc, interface, controller, 0x72, 22050)
    actor = env.object(0x58, 'actor', fill=0x6b)
    env.put(actor + 4, sound, 73, 82, 61, 0)
    env.put(actor + 0x18, 0x80000000, 0, 100, 100, 0x80000000, 0, 200, 200, 0, 0)
    env.put(actor + 0x40, 0, 0, 21, 47, 0, 0)
    manager = env.object(0x30, 'manager', fill=0)
    backend = env.object(0x90, 'backend', fill=0)
    env.put(root + 0x2c, backend)
    env.put(manager, root, 82)
    env.put(manager + 0x20, 4, 1, 23, 37)
    env.override(0x4a3050, returns(11))
    env.override(0x546df0, returns(1234))
    return dict(actor=actor, sound=sound, manager=manager, root=root, settings=settings,
                backend=backend, controller=controller)


def configured(**words):
    def setup(env):
        t = world(env, True)
        for key, value in words.items():
            if key.startswith('a') and len(key) == 3:
                env.put(t['actor'] + int(key[1:], 16), value)
            elif key == 'enabled':
                env.put(t['root'] + 0x10, value)
            elif key == 'allowed':
                env.put(t['settings'] + 0x24, value)
        return t
    return setup


def actor_case(label, function, setup, args=()):
    return Case(label, function, setup, receiver=lambda t: t['actor'], arguments=args)


def linked(env, count=3, payloads=True, active=False):
    t = world(env, active)
    nodes = [env.object(12, 'list node %d' % i, fill=0) for i in range(count)]
    actors = [t['actor']]
    for i in range(1, count):
        a = env.object(0x58, 'actor %d' % i, fill=0x35 + i)
        env.put(a + 4, t['sound'], 30 + i * 19, 17 + i, 0, i & 1)
        actors.append(a)
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i + 1 < count else 0,
                nodes[i - 1] if i else 0, actors[i] if payloads or i != 1 else 0)
    env.put(t['manager'] + 0xc, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, count)
    t.update(nodes=nodes, actors=actors)
    return t


def cases(random_source):
    for nonzero in (0, 1):
        yield Case('manager init %d' % nonzero, 0x402240, world,
                   receiver=lambda t: t['manager'], arguments=(lambda t, nonzero=nonzero: t['root'] if nonzero else 0, 93))
    yield actor_case('reset base', 0x4023f0, world)
    for flag in (0, 1, 2, 0x101):
        yield actor_case('deleting destructor %x' % flag, 0x4022d0, world, (flag,))
    for fn in (0x402610, 0x402a60):
        for sound in (False, True):
            for points in (None, (0, 0, 0, 0), (0, 2, 3, 4), (1, 0, 0, 0), (-8, 13, 47, 92)):
                def init(env, sound=sound, points=points):
                    t = world(env)
                    p = 0
                    if points is not None:
                        p = env.object(16, 'bounds')
                        env.put(p, *points)
                    t['points'] = p
                    t['input_sound'] = t['sound'] if sound else 0
                    return t
                yield actor_case('initialize %x %s %s' % (fn, sound, points), fn, init,
                                 (lambda t: t['input_sound'], 57, 83, lambda t: t['points'], 29))
    for fn in (0x4022f0, 0x402370, 0x402400):
        for fail in (False, True):
            for sound in (False, True):
                for interval in ((7, 14), (9, 8)):
                    for parity in (0, 1):
                        def create(env, fail=fail, parity=parity):
                            t = world(env)
                            p = env.object(16, 'creation bounds')
                            env.put(p, -7, 3, 23, 67)
                            t['points'] = p
                            free = env.object(24, 'MFC free nodes', fill=0)
                            env.put(free, free + 12)
                            env.put(t['manager'] + 0x18, free)
                            env.override(0x4f63ec, allocate(fail=fail))
                            env.override(0x4a3050, returns(12 + parity))
                            return t
                        args = (lambda t, sound=sound: t['sound'] if sound else 0, 43,
                                lambda t: t['points'], 71, 0x1234)
                        if fn == 0x402400:
                            args += (23, *interval, 0x9876)
                        yield Case('create %x fail%s sound%s interval%s parity%d' %
                                   (fn, fail, sound, interval, parity), fn, create,
                                   receiver=lambda t: t['manager'], arguments=args)
    for fn in (0x402270, 0x4022a0, 0x402520, 0x402570, 0x4025c0, 0x4024e0):
        for count in (0, 3):
            for backend in (False, True):
                def manager_setup(env, fn=fn, count=count, backend=backend):
                    t = linked(env, count, payloads=False)
                    if not backend:
                        env.put(t['root'] + 0x2c, 0)
                    if fn in (0x402570, 0x4025c0, 0x4022a0, 0x402270):
                        for a in t['actors']:
                            vt = env.object(8, 'actor callbacks')
                            # These slots are game code, so use original addresses.
                            env.put(vt, 0x4022d0, 0x402720)
                            env.put(a, vt)
                            env.put(a + 0x18, 0x80000000)
                    return t
                args = (73, 91) if fn == 0x4025c0 else ((38,) if fn == 0x4024e0 else ())
                yield Case('manager %x nodes%d backend%s' % (fn, count, backend), fn,
                           manager_setup, receiver=lambda t: t['manager'], arguments=args)
    # Distinct master/base/optional scales, threshold neighbours, signed truncation and wrap.
    volume_inputs = [(5, 73, 0), (6, 73, 0), (15, 73, -1), (16, 73, 61),
                     (-7, 73, 61), (115, 100, 100), (116, 100, 100),
                     (999, 91, 13), (0x7fffffff, 0x70000001, 0x60000003),
                     (82, 73, 61)]
    volume_inputs += [(random_source.randrange(-200, 400), random_source.randrange(-200, 400),
                       random_source.randrange(-20, 200)) for _ in range(16)]
    for master, base, scale in volume_inputs:
        for fn in (0x4026a0, 0x402840):
            for fade in ((0, 9) if fn == 0x402840 else (0,)):
                def volume(env, master=master, base=base, scale=scale, fade=fade):
                    t = world(env, active=not fade)
                    env.put(t['actor'] + 8, base, master - 1, scale)
                    return t
                args = (master,) if fn == 0x4026a0 else (base, fade, 7)
                yield actor_case('volume %x %d %d %d fade%d' % (fn, master, base, scale, fade), fn, volume, args)
    yield actor_case('master unchanged skips null backend', 0x4026a0,
                     configured(a04=0, a0c=93), (93,))
    for start in (0, 1):
        for playing in (0, 1):
            for fade in (0, 31):
                for master, scale in ((5, 0), (6, 51), (16, -2), (-17, 55), (191, 131)):
                    yield actor_case('toggle %d %d %d %d %d' % (start, playing, fade, master, scale),
                                     0x4028c0, configured(a14=playing, a0c=master, a10=scale),
                                     (start, 89, fade))
    for words in (dict(a04=0), dict(enabled=0), dict(allowed=0), dict(a14=1)):
        yield actor_case('toggle early %s' % words, 0x4028c0, configured(**words), (1, 37, 91))
    points = [(-1, 50), (0, 50), (1, 50), (99, 50), (100, 50), (50, 0), (50, 100),
              (50, 1), (50, 99), (50, 101), (50, -1), (50, 50), (150, 150)]
    for fn in (0x402720, 0x402f10):
        for x, y in points:
            for playing in (0, 1):
                for immediate in (0, 1):
                    yield actor_case('region %x %d %d play%d immediate%d' % (fn, x, y, playing, immediate),
                                     fn, configured(a18=0, a28=100, a2c=100, a30=200, a34=200, a14=playing),
                                     (x, y, immediate))
        for words in (dict(a14=1), dict(a04=0), dict(a08=0), dict(enabled=0), dict(allowed=0), {}):
            yield actor_case('unbounded %x %s' % (fn, words), fn, configured(**words), (25, 37, 1))
    for phase in (0, 1):
        for countdown in (0, 16, 17, 18, 0xffffffff):
            for interval in ((11, 23), (0x7fffffff, 0x7ffffffe)):
                for draw in (12, 13):
                    def timer(env, phase=phase, countdown=countdown, interval=interval, draw=draw):
                        t = world(env, False)
                        env.put(t['actor'] + 0x40, *interval, *interval, countdown, phase)
                        env.override(0x4a3050, returns(draw))
                        return t
                    yield actor_case('timer phase%d left%d range%s draw%d' % (phase, countdown, interval, draw),
                                     0x402f10, timer, (7, 9, 0))
    for x, y in ((0, 0), (3, 4), (399, 0), (-399, 0), (640, 640), (641, 0), (0, 641),
                 (-640, -640), (-641, 0), (0, -641), (120, 340), (0x80000000, 0), (0, 0x80000000)):
        for playing in (0, 1):
            yield actor_case('spatial %d %d playing%d' % (x, y, playing), 0x402ac0,
                             configured(a14=playing), (x, y, 19))
    for fn, identities in ((0x48c4d0, (0x48c1e0, 0x48c410, 0x48c430, 0x48c450, 0x48c470, 0x48c490, 0x48c4b0)),
                           (0x48cb00, (0x48c8f0, 0x48ca40, 0x48ca60, 0x48ca80, 0x48caa0, 0x48cac0, 0x48cae0))):
        for identity in (*identities, 0, 0x12345678):
            def bounds(env, identity=identity):
                obj = env.object(0x150, 'game actor', fill=0x79)
                desc = env.object(0x14, 'description', fill=0x53)
                env.put(desc + 0x10, identity)
                return obj, desc
            yield Case('bounds %x identity%x' % (fn, identity), fn, bounds,
                       arguments=(lambda t: t[0], lambda t: t[1]))
    for rewrite_head in (False, True):
        def cleanup_order(env, rewrite_head=rewrite_head):
            t = linked(env, 3, payloads=False, active=True)
            fade = env.object(0x28, 'pending stop fade', fill=0)
            env.put(fade, 0x513520)
            env.put(fade + 0x10, t['sound'], 1, 37)
            env.put(t['backend'] + 0xc, fade + 4, fade + 4)
            observed = env.object(32, 'callback observations', fill=0)
            methods = env.get(env.get(t['sound'] + 0xc))
            def stopped(env, call):
                env.put(observed, env.get(t['manager'] + 4), env.get(t['manager'] + 0xc),
                        env.get(t['actor'] + 0xc), call.arguments[0])
                if rewrite_head:
                    env.put(t['manager'] + 0xc, t['nodes'][2])
                return 0
            def volume_changed(env, call):
                env.put(observed + 16, env.get(t['actor'] + 0xc), env.get(t['manager'] + 4),
                        call.arguments[0], call.arguments[1])
                # Traversal must already have cached next, so this must not skip node three.
                env.put(t['nodes'][0], 0)
                return 0
            env.put(methods + 0x48, env.stub('Stop observes publication', 'stdcall', 1, stopped))
            env.put(methods + 0x3c, env.stub('SetVolume mutates current link', 'stdcall', 2, volume_changed))
            return t
        yield Case('master cleanup publication and cached-next head%s' % rewrite_head,
                   0x4024e0, cleanup_order, receiver=lambda t: t['manager'], arguments=(93,))
    for fn in (0x402270, 0x402520):
        def no_application(env):
            t = world(env)
            env.put(t['manager'], 0)
            return t
        yield Case('null application %x' % fn, fn, no_application,
                   receiver=lambda t: t['manager'])
    for fn in (0x402720, 0x402f10):
        for words in (dict(a18=0, a28=0x80000000), dict(a18=0, a28=100, a2c=100, a30=200, a34=200)):
            for x, y in ((100, 150), (150, 100), (200, 150), (150, 200), (150, 150)):
                yield actor_case('second rectangle edges %x %s %d %d' % (fn, words, x, y),
                                 fn, configured(**words), (x, y, 0))
    for words in (dict(a18=0, a14=0, enabled=0), dict(a18=0, a14=0, allowed=0),
                  dict(a18=0, a14=0, a04=0)):
        yield actor_case('region start gates %s' % words, 0x402720, configured(**words), (50, 50, 1))
    for words in (dict(enabled=0), dict(allowed=0), dict(a0c=-23), dict(a0c=192, a10=199)):
        yield actor_case('spatial state %s' % words, 0x402ac0, configured(**words), (37, 43, 1))
    for fn in (0x4028c0, 0x402ac0):
        for fade in (0, 43):
            def play_mutates(env):
                t = world(env)
                voice = env.object(0x30, 'replacement voice', fill=0)
                old_interface = env.get(t['sound'] + 0xc)
                methods = env.get(old_interface)
                interface = env.object(4, 'replacement COM buffer')
                env.put(interface, methods)
                env.put(voice + 0xc, interface, t['controller'], 0x62, 11025)
                observations = env.object(16, 'play observation', fill=0)
                def play(env, call):
                    env.put(observations, env.get(t['actor'] + 8), env.get(t['actor'] + 0xc),
                            env.get(t['actor'] + 0x14), call.arguments[0])
                    env.put(t['actor'] + 4, voice, 39, 47, 29)
                    return 0
                env.put(methods + 0x30, env.stub('Play changes actor settings', 'stdcall', 4, play))
                return t
            args = (1, 87, fade) if fn == 0x4028c0 else (27, 43, 1)
            yield actor_case('play reloads %x fade%d' % (fn, fade), fn, play_mutates, args)
    for words in ({}, dict(a04=0), dict(a14=1), dict(enabled=0), dict(allowed=0)):
        yield actor_case('timer forced phase gates %s' % words, 0x402f10,
                         configured(a54=1, **words), (23, 45, 1))
    for bounds in ((0, 0, 3, 0), (0, 0, 0, 4)):
        def trailing_bound(env, bounds=bounds):
            t = world(env)
            p = env.object(16, 'trailing nonzero bound')
            env.put(p, *bounds)
            t['points'] = p
            return t
        yield actor_case('initializer trailing nonzero %s' % (bounds,), 0x402610, trailing_bound,
                         (lambda t: t['sound'], 37, 83, lambda t: t['points'], 29))
    def replace_application(env):
        t = world(env)
        other = env.object(0x80, 'replacement application', fill=0x31)
        t['replacement'] = other
        return t
    yield Case('manager replaces previous application', 0x402240, replace_application,
               receiver=lambda t: t['manager'], arguments=(lambda t: t['replacement'], 47))
    for fn in (0x402610, 0x402a60):
        for playing in (1, 0x7fffffff):
            def active_initializer(env, playing=playing):
                t = world(env)
                env.put(t['actor'] + 0x14, playing)
                p = env.object(16, 'distinct initializer input')
                env.put(p, -31, 17, 89, 103)
                t['points'] = p
                return t
            yield actor_case('initializer clears active %x %x' % (fn, playing), fn,
                             active_initializer, (lambda t: t['sound'], 37, 59, lambda t: t['points'], 41))
    for fn in (0x4022f0, 0x402370, 0x402400):
        for valid in (False, True):
            def dirty_factory(env):
                t = world(env)
                p = env.object(16, 'factory distinct input')
                env.put(p, -19, 23, 47, 83)
                t['points'] = p
                def dirty_allocate(env, call):
                    return env.object(call.arguments[0], 'nonzero allocation', fill=0x5d)
                env.override(0x4f63ec, dirty_allocate)
                return t
            args = (lambda t, valid=valid: t['sound'] if valid else 0, 37,
                    lambda t: t['points'], 41, 0x6712)
            if fn == 0x402400:
                args += (53, 61, 89, 0x7823)
            yield Case('factory dirty allocation %x valid%s' % (fn, valid), fn, dirty_factory,
                       receiver=lambda t: t['manager'], arguments=args)
    for with_fade in (False, True):
        def audible_stop_all(env, with_fade=with_fade):
            t = linked(env, 3, payloads=False, active=True)
            for i, actor in enumerate(t['actors']):
                env.put(actor + 0x14, 7 + i)
            observations = env.object(0x80, 'stop snapshots', fill=0)
            methods = env.get(env.get(t['sound'] + 0xc))
            # Keep the recording cursor in surviving memory, independent of fixture API names.
            cursor = env.object(4, 'stop cursor', fill=0)
            def record_stop(env, call):
                index = env.get(cursor)
                env.put(cursor, index + 1)
                env.put(observations + index * 16, *(env.get(a + 0x14) for a in t['actors']),
                        env.get(t['manager'] + 0xc))
                return 0
            env.put(methods + 0x48, env.stub('Stop snapshots active actors', 'stdcall', 1, record_stop))
            if with_fade:
                fade = env.object(0x28, 'stop-all pending fade', fill=0)
                env.put(fade, 0x513520)
                env.put(fade + 0x10, t['sound'], 1, 37)
                env.put(t['backend'] + 0xc, fade + 4, fade + 4)
            return t
        yield Case('stop all audible actors fade%s' % with_fade, 0x402520, audible_stop_all,
                   receiver=lambda t: t['manager'])
    # A volume callback may overwrite the percentage already published before it.
    # The actor update restores its requested percentage after this boundary.
    for fn in (0x402720, 0x4028c0, 0x402ac0, 0x402f10):
        for fade in ((0, 43) if fn == 0x4028c0 else (0,)):
            def volume_mutates(env):
                t = world(env)
                env.put(t['actor'] + 0x54, 1)
                observations = env.object(0x100, 'volume publication snapshots', fill=0)
                cursor = env.object(4, 'volume cursor', fill=0)
                methods = env.get(env.get(t['sound'] + 0xc))
                def changed(env, call):
                    index = env.get(cursor)
                    env.put(cursor, index + 1)
                    env.put(observations + 16 * index, env.get(t['actor'] + 8),
                            env.get(t['actor'] + 0x14), env.get(t['actor'] + 0x38), call.arguments[1])
                    env.put(t['actor'] + 8, 0x4567)
                    return 0
                env.put(methods + 0x3c, env.stub('SetVolume overwrites percentage', 'stdcall', 2, changed))
                env.put(methods + 0x18, env.stub('GetVolume overwrites percentage', 'stdcall', 2,
                    lambda env, call: (env.put(t['actor'] + 8, 0x5678), env.put(call.arguments[1], 0), 0)[-1]))
                return t
            args = (1, 87, fade) if fn == 0x4028c0 else (27, 43, 1)
            yield actor_case('volume callback publication %x fade%d' % (fn, fade), fn, volume_mutates, args)
    for phase in (0, 1, 2, 3):
        def distinct_intervals(env, phase=phase):
            t = world(env, False)
            env.put(t['actor'] + 0x40, 11, 19, 101, 137, 0, phase)
            return t
        yield actor_case('timer distinct intervals nonboolean phase%d' % phase,
                         0x402f10, distinct_intervals, (17, 29, 0))
