"""Original resize wrappers with physical DirectDraw services only."""
from clawparity.cases import Case

PRIMARY, AUX, TYPE = 0x4D5720, 0x4D4280, 0x4C9BD0


def setup_case(size, prior, kind=0, flags=0, mode_error=0, create_error=0,
               attached_error=0, invalid_surface=False, mutate_kind=False,
               missing=False, salt=17, mutate_flags=False):
    def setup(env):
        obj = env.object(48, 'resize-wrapper', fill=salt)
        parent = env.object(0x38, 'parent', fill=salt ^ 51)
        manager = env.object(0x884, 'graphics', fill=0)
        control = env.object(0x14, 'display-control', fill=0)
        source = env.object(188, 'source-wrapper', fill=0)
        old = env.object(188, 'old-wrapper', fill=0)
        nodes = env.object(12 * 8, 'list-nodes', fill=0)
        log = env.object(8192, 'physical-observations', fill=0)
        env.put(obj + 4, kind)
        env.put(obj + 12, parent, *prior)
        env.put(obj + 28, 13, 29, 47, 61, old)
        env.put(parent + 4, control)
        env.put(parent + 0x1c, 0 if missing else manager)
        env.put(parent + 0x34, flags)
        env.put(control + 0x10, source)
        env.put(source + 0x2c, source)
        env.put(manager + 0x3bc, nodes, nodes + 12, 2, nodes + 24)
        env.put(nodes, nodes + 12, 0, old)
        env.put(nodes + 12, 0, nodes, source)
        for i in range(2, 8):
            env.put(nodes + i * 12, nodes + (i + 1) * 12 if i < 7 else 0)
        env.put(old, 0x513588)
        env.put(old + 4, nodes)
        for a in (0x54139c, 0x5413a0, 0x5413a4, 0x5413a8):
            env.put(a, 0)

        def record(tag, call, extra=()):
            index = env.get(log)
            at = log + 4 + index * 256
            env.put(log, index + 1)
            env.put(at, tag, call.receiver, len(call.arguments), *call.arguments)
            env.write(at + 40, env.read(obj, 48))
            if extra:
                env.put(at + 88, *extra)

        def descriptor(ptr):
            env.put(ptr + 8, 91, 137, 548)
            env.put(ptr + 0x48, 32, 0x40, 0, 32, 0xff0000, 0xff00, 0xff)
            if invalid_surface:
                env.put(ptr + 8, 0)

        def describe(env_, call):
            record(3, call)
            descriptor(call.arguments[1])
            return 0

        methods = env.object(0x80, 'surface-COM-methods', fill=0)
        physical = env.object(4, 'surface-COM', words=[methods])
        env.put(old + 8, physical)
        env.put(source + 8, physical)

        def release(env_, call):
            record(1, call)
            return 0

        def attached(env_, call):
            record(4, call, (env.get(call.arguments[1]),))
            if mutate_kind:
                env.put(obj + 4, 2)
            if not attached_error:
                env.put(call.arguments[2], physical)
            return attached_error

        env.put(methods + 8, env.stub('surface Release', 'stdcall', 1, release))
        env.put(methods + 0x30, env.stub('GetAttachedSurface', 'stdcall', 3, attached))
        env.put(methods + 0x58, env.stub('GetSurfaceDesc', 'stdcall', 2, describe))
        ddmethods = env.object(0x60, 'DirectDraw-methods', fill=0)
        dd = env.object(4, 'DirectDraw', words=[ddmethods])
        env.put(manager, dd)

        def mode(env_, call):
            record(2, call)
            if mutate_flags:
                env.put(parent + 0x34, flags ^ 2)
            return mode_error

        def getmode(env_, call):
            record(5, call)
            descriptor(call.arguments[1])
            return 0

        def create(env_, call):
            record(6, call, (env.get(call.arguments[1] + 4),
                             env.get(call.arguments[1] + 0x68)))
            env.write(log + 4 + (env.get(log) - 1) * 256 + 128,
                      env.read(call.arguments[1], 108))
            if not create_error:
                env.put(call.arguments[2], physical)
            return create_error

        env.put(ddmethods + 0x54, env.stub('SetDisplayMode', 'stdcall', 4, mode))
        env.put(ddmethods + 0x30, env.stub('GetDisplayMode', 'stdcall', 2, getmode))
        env.put(ddmethods + 0x18, env.stub('CreateSurface', 'stdcall', 4, create))
        return obj
    return setup


def cases(random_source):
    yield Case('menu type constant', TYPE, receiver=0xdeadbeef)
    for function in (PRIMARY, AUX):
        def emit(label, size=(211, 157, 16), prior=(640, 480, 8), **kw):
            return Case(label, function, setup_case(size, prior, **kw),
                        receiver=lambda p: p, arguments=size)
        for size in [(640, 480, 8), (0, -1, 7), (1, 1, 32)]:
            yield emit(f'{function:x} unchanged {size}', size, size)
        for depth in (8, 16, 24, 32, 7, 0, -1, 33):
            yield emit(f'{function:x} depth {depth}', size=(211, 157, depth))
        for w, h in [(0, 157), (-1, 157), (211, 0), (211, -1), (1, 1), (0x7fffffff, 1), (0x80000000, 1)]:
            yield emit(f'{function:x} geometry {w} {h}', size=(w, h, 8))
        for dimension in range(3):
            prior = [211, 157, 16]
            prior[dimension] += 1
            yield emit(f'{function:x} differs field {dimension}', prior=tuple(prior))
        for i in range(8):
            size=(random_source.randrange(1, 1500), random_source.randrange(1, 1000), random_source.choice((8,16,24,32)))
            yield emit(f'{function:x} random {i}', size=size, salt=random_source.randrange(1,255), flags=random_source.getrandbits(8), kind=random_source.choice((0,1,2,0xffffffff)))
        yield emit(f'{function:x} create fails', create_error=0x88760001)
        if function == PRIMARY:
            yield emit('primary missing graphics', missing=True)
            yield emit('primary mode fails', mode_error=0x80004005)
            yield emit('primary validity fails', invalid_surface=True)
            yield emit('primary kind two', flags=2)
            yield emit('primary flags change in SetDisplayMode', mutate_flags=True)
        else:
            yield emit('aux attached', kind=1)
            yield emit('aux attached failure', kind=1, attached_error=0x80004005)
            yield emit('aux kind changes during attach', kind=1, mutate_kind=True)
            yield emit('aux changed kind create fails', kind=1, mutate_kind=True, create_error=0x80004005)
