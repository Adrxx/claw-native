"""Original menu dimension guard, including its real resize callees."""
from clawparity.cases import Case

ENSURE = 0x42A000
CLOCK = 0x546DF0


def setup_case(width, height, resize, callback, mode, marker, clock):
    def setup(env):
        app = env.object(0x500, 'application', fill=0)
        observations = env.object(0x400, 'callback-observations', fill=0)
        env.put(app + 0x78, 32, width, height, marker, marker ^ 0x76543210)
        env.put(app + 0x90, marker ^ 0x11223344)
        env.put(0x537268, 0)
        env.put(0x537E88, 0)
        env.put(0x541328, marker ^ 0x13579BDF, marker ^ 0x2468ACE0, marker)
        env.put(0x537208, marker ^ 0x10203040, marker ^ 0x50607080)
        env.put(0x5430C4, marker, marker ^ 0xABCDEF01)

        def record(kind, call):
            index = env.get(observations)
            at = observations + 4 + index * 48
            env.put(at, kind, call.receiver, len(call.arguments),
                    *(list(call.arguments) + [0, 0])[:2],
                    env.get(app + 0x7C), env.get(app + 0x80),
                    env.get(app + 0x84), env.get(app + 0x88),
                    env.get(app + 0x30), env.get(0x541328), env.get(0x5430C8))
            env.put(observations, index + 1)

        if callback:
            handler = env.object(0x28, 'error-handler', fill=0x35)
            table = env.object(0x24, 'error-handler-vtable', fill=0)
            env.put(handler, table)
            env.put(app + 8, handler)

            def error(env, call):
                record(0xE001, call)
                # Nonzero callback results must never turn resize failure into success.
                env.put(app + 0x90, env.get(app + 0x90) ^ marker)
                return marker | 1

            env.put(table + 0x1C, env.stub('application error', 'thiscall', 2, error))

        if resize:
            scene = env.object(0x80, 'scene', fill=0)
            holder = env.object(0x30, 'surface-holder', fill=0x27)
            surface = env.object(0x40, 'surface', fill=0x49)
            palette_owner = env.object(0x70, 'palette-owner', fill=0)
            camera = env.object(0xE0, 'camera', fill=0x63)
            mode_object = env.object(0x20, 'mode-owner', fill=0x71)
            mode_table = env.object(0x20, 'mode-vtable', fill=0)
            env.put(app + 0x2C, mode_object, scene)
            env.put(scene + 4, holder)
            env.put(scene + 0x18, palette_owner)
            env.put(scene + 0x24, camera)
            env.put(holder + 0x10, surface)
            env.put(surface + 0x10, 640, 480)
            env.put(camera + 0x5C, 0)
            env.put(mode_object, mode_table)

            def get_mode(env, call):
                record(0xD001, call)
                return mode

            env.put(mode_table + 0x10, env.stub('application mode', 'thiscall', 0, get_mode))

        def tick(env, call):
            record(0xC001, call)
            return (clock + env.calls_so_far(CLOCK) * 17) & 0xFFFFFFFF

        env.override(CLOCK, tick)
        return {'app': app}
    return setup


def cases(random_source):
    def case(label, width, height, flag, resize=False, callback=True, mode=3):
        marker = random_source.getrandbits(32)
        clock = random_source.getrandbits(32)
        return Case(label, ENSURE,
                    setup_case(width, height, resize, callback, mode, marker, clock),
                    receiver=lambda t: t['app'], arguments=(flag,))

    yield case('already 640x480 skips even without scene', 640, 480, 0)
    yield case('already 640x480 skips with populated scene', 640, 480, 0, True)
    dimensions = [(0, 480), (639, 480), (641, 480), (0xFFFFFFFF, 480),
                  (0x80000000, 480), (640, 0), (640, 479), (640, 481),
                  (640, 0xFFFFFFFF), (640, 0x80000000), (800, 600)]
    for width, height in dimensions:
        yield case(f'failed resize from {width:#x}x{height:#x}', width, height, 0)
    for flag in (1, 2, 0x80000000, 0xFFFFFFFF):
        yield case(f'force flag {flag:#x} fails even at menu size', 640, 480, flag)
        yield case(f'force flag {flag:#x} succeeds through original', 640, 480, flag, True)
    yield case('failed resize has no error listener', 640, 479, 0, callback=False)
    for mode in (0, 3, 4, 0xFFFFFFFF):
        yield case(f'original resize succeeds with mode {mode:#x}', 901, 377, 0, True, mode=mode)
    for index in range(10):
        width = random_source.getrandbits(32)
        height = random_source.getrandbits(32)
        flag = random_source.choice((0, 1, 0x7FFFFFFF, 0xFFFFFFFF))
        yield case(f'random geometry {index}', width, height, flag,
                   resize=bool(index & 1), callback=bool(index % 3),
                   mode=random_source.choice((0, 3, 4, 7)))


_guard_cases = cases


def direct_setup(width, height, layout, marker, scene=True):
    def setup(env):
        app = env.object(0x100, 'direct-application', fill=0)
        env.put(app + 0x68, layout, marker)
        env.put(app + 0x78, 32, width, height, marker ^ 0x12345678, marker ^ 0x87654321)
        env.put(0x5370C8, marker, marker ^ 1, marker ^ 2, marker ^ 3)
        if scene:
            sc = env.object(0x40, 'direct-scene', fill=0)
            manager = env.object(0x20, 'direct-manager', fill=0)
            front = env.object(0x30, 'direct-front', fill=0)
            world = env.object(0xE0, 'direct-world', fill=0x57)
            env.put(app + 0x30, sc)
            env.put(sc + 4, manager)
            env.put(sc + 0x24, world)
            env.put(manager + 0x10, front)
            env.put(front + 0x10, width, height, 32)
            env.put(world + 0x38, 0, 0)
            env.put(world + 0x5C, 0)
        def set_rect(env, call):
            env.put(call.arguments[0], *call.arguments[1:])
            return 1
        env.override(0x546D5C, set_rect)
        return {'app': app}
    return setup


def cases(random_source):
    yield from _guard_cases(random_source)
    for state in (0, 0x12345679, 0x80000000):
        for scene in (0, 0x23456781):
            def setup(env, state=state, scene=scene):
                app = env.object(0x34, 'readiness-application', fill=0x73)
                env.put(app + 0x2C, state, scene)
                return {'app': app}
            yield Case(f'readiness tokens {state:x}/{scene:x}', 0x425640, setup,
                       receiver=lambda t: t['app'])
    for listener in (False, True):
        first, second = random_source.getrandbits(32), random_source.getrandbits(32)
        def setup(env, listener=listener):
            app = env.object(12, 'diagnostic-application', fill=0)
            observed = env.object(16, 'diagnostic-observed', fill=0x69)
            if listener:
                handler = env.object(32, 'diagnostic-handler', fill=0x31)
                vt = env.object(32, 'diagnostic-vtable', fill=0)
                env.put(app + 8, handler)
                env.put(handler, vt)
                def report(env, call):
                    env.put(observed, call.receiver, *call.arguments, env.get(app + 8))
                    return 0x13579BDF
                env.put(vt + 0x1C, env.stub('diagnostic report', 'thiscall', 2, report))
            return {'app': app}
        yield Case(f'direct diagnostic listener {listener}', 0x429E10, setup,
                   receiver=lambda t: t['app'], arguments=(first, second))
    for flag in (1, 0xFFFFFFFF, 0x80000000):
        yield Case(f'direct redraw no layout {flag:x}', 0x429EB0,
                   direct_setup(640, 480, 7, random_source.getrandbits(32), False),
                   receiver=lambda t: t['app'], arguments=(flag,))
    for requested in (-2147483648, -1, 0, 1, 2, 5, 9, 10, 11, 2147483647):
        clamped = min(10, max(1, requested))
        for force in (0, 1):
            yield Case(f'viewport clamp {requested} force {force}', 0x429ED0,
                       direct_setup(857, 613, clamped if not force else 6,
                                    random_source.getrandbits(32)),
                       receiver=lambda t: t['app'], arguments=(requested, force, 0))
    for width, height in ((0, 1), (641, 479), (-1, -753), (16777217, 33554431),
                          (2147483647, -2147483648)):
        yield Case(f'camera thresholds {width}/{height}', 0x42AE70,
                   direct_setup(width, height, 4, random_source.getrandbits(32)),
                   receiver=lambda t: t['app'])
    for entry in (0x42A060, 0x42AE70):
        yield Case(f'direct null scene {entry:x}', entry,
                   direct_setup(777, 333, 3, random_source.getrandbits(32), False),
                   receiver=lambda t: t['app'],
                   arguments=(801, 601) if entry == 0x42A060 else ())


_simple_cases = cases


def service_setup(marker, *, old=(640, 480), palette=False, failure=False,
                  modes=(3, 4), mutate=False, status=False, switch_manager=False,
                  switch_scene=False):
    def setup(env):
        app = env.object(0x100, 'service-application', fill=0)
        scene = env.object(0x40, 'service-scene', fill=0)
        world = env.object(0xE0, 'service-world', fill=0x39)
        owner = env.object(0x68, 'image-owner', fill=0)
        fresh_scene = env.object(0x40, 'fresh-scene', fill=0) if switch_scene else 0
        fresh_owner = env.object(0x68, 'fresh-image-owner', fill=0) if switch_scene else 0
        observations = env.object(0x8000, 'service-observations', fill=0)
        env.put(app + 0x2C, 0, scene)
        env.put(app + 0x68, 7, marker)
        env.put(app + 0x78, 32, 903, 517, marker ^ 0x12345678, marker ^ 0x87654321)
        env.put(scene + 0x18, owner)
        env.put(scene + 0x24, world)
        env.put(world + 0x38, 0, 0)
        env.put(world + 0x5C, 0)
        env.put(0x537268, int(status))
        env.put(0x537E88, 0)
        env.put(0x541374, 0)
        env.put(0x54139C, 0, 0, 0, 0)
        env.put(0x541328, marker ^ 0x11335577, marker ^ 0x22446688, marker)
        env.put(0x537208, marker ^ 0x10203040, marker ^ 0x50607080)
        env.put(0x5430C4, marker, marker ^ 0xABCDEF01)

        def record(kind, call):
            n = env.get(observations)
            env.put(observations + 4 + n * 64, kind, call.receiver, len(call.arguments),
                    *(list(call.arguments) + [0] * 6)[:6],
                    env.get(app + 0x68), env.get(app + 0x6C),
                    env.get(app + 0x7C), env.get(app + 0x80),
                    env.get(app + 0x84), env.get(app + 0x88), env.get(owner + 0x64))
            env.put(observations, n + 1)

        managers = []
        def manager(label):
            mgr = env.object(0x20, label + '-manager', fill=0)
            for i, name in enumerate(('front', 'back')):
                wrapper = env.object(0x30, label + '-' + name, fill=0)
                vtable = env.object(0x30, label + '-' + name + '-vtable', fill=0)
                actual = env.object(0x10, label + '-' + name + '-actual', fill=0)
                com = env.object(4, label + '-' + name + '-COM', fill=0)
                comvt = env.object(0x30, label + '-' + name + '-COM-vtable', fill=0)
                env.put(mgr + 0x10 + 4 * i, wrapper)
                env.put(wrapper, vtable)
                env.put(wrapper + 0x10, *old, 32)
                env.put(wrapper + 0x2C, actual)
                env.put(actual + 8, com)
                env.put(com, comvt)
                def resize(env, call, wrapper=wrapper, i=i):
                    record(0x100 + i, call)
                    if switch_scene and i == 0:
                        env.write(fresh_scene, env.read(scene, 0x40))
                        env.put(fresh_scene + 0x18, fresh_owner)
                        env.put(app + 0x30, fresh_scene)
                    if not failure:
                        env.put(wrapper + 0x10, *call.arguments)
                    return int(not failure)
                env.put(vtable + 0x28, env.stub(label + name + ' resize', 'thiscall', 3, resize))
                def clear(env, call, i=i):
                    record(0x200 + i, call)
                    if switch_manager and len(managers) == 2:
                        env.put(scene + 4, managers[1])
                    return 0
                def present(env, call, i=i):
                    record(0x300 + i, call)
                    return 0
                env.put(comvt + 0x14, env.stub(label + name + ' Blt', 'stdcall', 6, clear))
                env.put(comvt + 0x2C, env.stub(label + name + ' Flip', 'stdcall', 3, present))
            return mgr
        managers.append(manager('primary'))
        managers.append(manager('alternate'))
        env.put(scene + 4, managers[0])

        states = []
        for index, mode in enumerate(modes):
            state = env.object(0x20, f'state-{index}', fill=0x53)
            vt = env.object(0x20, f'state-{index}-vtable', fill=0)
            env.put(state, vt)
            def get_mode(env, call, index=index, mode=mode):
                record(0x400 + index, call)
                if mutate and index == 0:
                    env.put(app + 0x2C, states[-1])
                    # The changed-size decision must retain its pre-callback value.
                    env.put(managers[0] and env.get(managers[0] + 0x10) + 0x10, 777, 333)
                return mode
            env.put(vt + 0x10, env.stub(f'state-{index} type', 'thiscall', 0, get_mode))
            states.append(state)
        env.put(app + 0x2C, states[0])

        if palette:
            pal = env.object(0x14, 'palette', fill=0)
            com = env.object(4, 'palette-COM', fill=0)
            vt = env.object(0x20, 'palette-COM-vtable', fill=0)
            active = env.object(1024, 'active-palette-table', fill=0x73)
            saved = env.object(1024, 'saved-palette-table', fill=0x2D)
            source = env.object(1024, 'physical-palette-table', fill=0x91)
            env.put(pal + 4, com)
            env.put(pal + 0xC, active, saved)
            env.put(com, vt)
            def get_entries(env, call):
                record(0x500, call)
                env.write(call.arguments[4], env.read(source, 1024))
                return 0
            def set_entries(env, call):
                record(0x501, call)
                start, count, ptr = call.arguments[2:]
                env.write(source + start * 4, env.read(ptr, count * 4))
                return 0
            env.put(vt + 0x10, env.stub('palette GetEntries', 'stdcall', 5, get_entries))
            env.put(vt + 0x18, env.stub('palette SetEntries', 'stdcall', 5, set_entries))
            image = env.object(0x14, 'active-image', fill=0)
            imagevt = env.object(0x38, 'image-vtable', fill=0)
            env.put(image, imagevt)
            env.put(image + 0x10, pal)
            env.put(owner + 0x64, image)
            def image_ready(env, call):
                record(0x502, call)
                return marker
            env.put(imagevt + 0x34, env.stub('image restore', 'thiscall', 0, image_ready))

        def tick(env, call):
            record(0x600, call)
            if mutate and status:
                env.put(app + 0x78, 24, 771, 339)
            return (marker + env.calls_so_far(CLOCK) * 101) & 0xFFFFFFFF
        def set_rect(env, call):
            record(0x700, call)
            env.put(call.arguments[0], *call.arguments[1:])
            return 1
        env.override(CLOCK, tick)
        env.override(0x546D5C, set_rect)
        return {'app': app}
    return setup


def cases(random_source):
    yield from _simple_cases(random_source)
    for palette in (False, True):
        for failure in (False, True):
            yield Case(f'direct resize palette {palette} failure {failure}', 0x42A060,
                       service_setup(random_source.getrandbits(32), palette=palette, failure=failure),
                       receiver=lambda t: t['app'], arguments=(801, 601))
    for modes in ((3, 0), (0, 4), (4, 7), (0, 0), (0xFFFFFFFF, 3)):
        for old in ((640, 480), (801, 480), (801, 601)):
            yield Case(f'resize types {modes} old {old}', 0x42A060,
                       service_setup(random_source.getrandbits(32), old=old, modes=modes, mutate=True),
                       receiver=lambda t: t['app'], arguments=(801, 601))
    yield Case('resize formats fresh live dimensions after timer', 0x42A060,
               service_setup(random_source.getrandbits(32), status=True, mutate=True),
               receiver=lambda t: t['app'], arguments=(801, 601))
    for function, arguments in ((0x429ED0, (5, 1, 1)), (0x429EB0, (0,)),
                                (0x42A060, (801, 601))):
        yield Case(f'live manager pairs {function:x}', function,
                   service_setup(random_source.getrandbits(32), switch_manager=True),
                   receiver=lambda t: t['app'], arguments=arguments)


_service_cases = cases


def cases(random_source):
    yield from _service_cases(random_source)
    for layout in (1, 2, 9, 10):
        yield Case(f'viewport poisoned local RECT layout {layout}', 0x429ED0,
                   direct_setup(857, 613, 4, random_source.getrandbits(32)),
                   receiver=lambda t: t['app'], arguments=(layout, 1, 0),
                   initial_stack=((-16, random_source.randbytes(16)),))
    yield Case('palette restores captured image into fresh scene image owner', 0x42A060,
               service_setup(random_source.getrandbits(32), palette=True, switch_scene=True),
               receiver=lambda t: t['app'], arguments=(801, 601))


_stronger_service_cases = cases


def observed_camera_setup(width, height, marker):
    def setup(env):
        tokens = direct_setup(width, height, 3, marker)(env)
        app = tokens['app']
        scene = env.get(app + 0x30)
        world = env.get(scene + 0x24)
        camera = env.object(0xB4, 'live-world-camera', fill=0x67)
        bounds = env.object(0x70, 'published-camera-bounds', fill=0xA9)
        env.put(world + 0x5C, camera)
        env.put(camera + 0xC, scene)
        env.put(camera + 0xB0, bounds)
        return tokens
    return setup


def cases(random_source):
    yield from _stronger_service_cases(random_source)
    for width, height in ((857, 613), (16777217, 33554431), (-715, 967)):
        yield Case(f'camera publishes every threshold pair {width}/{height}', 0x42AE70,
                   observed_camera_setup(width, height, random_source.getrandbits(32)),
                   receiver=lambda t: t['app'])
