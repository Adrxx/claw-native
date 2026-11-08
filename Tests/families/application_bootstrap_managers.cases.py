"""Original-derived bootstrap inputs; movie cases bound file-query delegation only."""
from clawparity.cases import Case

NEW = 0x4F63EC
KEY = 0x546CE4
JOY = 0x546DE8
OPEN = 0x546A30


def patterned(random_source, size):
    return bytes(random_source.randrange(1, 256) for _ in range(size))


def map_init(env, address):
    env.put(address, 0x510054, 0, 17, 0, 0, 0, 10)


def physical_strings(env):
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))
    def decrement(e, c):
        value = (e.get(c.arguments[0]) - 1) & 0xFFFFFFFF
        e.put(c.arguments[0], value)
        return value
    env.override(0x5469E8, decrement)


def cases(random_source):
    for fail in (False, True):
        for old_present in (False, True):
            data = patterned(random_source, 32)
            block = patterned(random_source, 128)
            def setup(env, fail=fail, old_present=old_present, data=data, block=block):
                receiver = env.object(32, 'lookup-owner', data=data)
                old = env.object(128, 'previous-owned-lookup', data=block) if old_present else 0
                env.put(receiver + 4, old)
                def allocation(e, c):
                    return 0 if fail else e.object(c.arguments[0], 'new-lookup', data=block)
                env.override(NEW, allocation)
                return receiver
            yield Case(f'lookup failure={fail} old={old_present}', 0x493C20, setup, receiver=lambda t: t)

    for index in range(12):
        data = patterned(random_source, 64)
        arguments = [(0, 1, 0xFFFFFFFF), (0x80000000, 0x7FFFFFFF, 0x12345678)][index] if index < 2 else tuple(random_source.getrandbits(32) for _ in range(3))
        def setup(env, data=data):
            return env.object(64, 'opaque-resource-manager', data=data)
        yield Case(f'resource sparse words {index}', 0x4EC010, setup, receiver=lambda t: t, arguments=arguments)
    # Opaque arguments may alias receiver fields; they remain values, never dereferenced.
    for offset in (0, 4, 8, 0x24):
        data = patterned(random_source, 64)
        def setup(env, data=data):
            return env.object(64, 'resource-alias', data=data)
        yield Case(f'resource alias {offset}', 0x4EC010, setup, receiver=lambda t: t,
                   arguments=(lambda t, o=offset: t + o, lambda t: t + 4, lambda t: t + 0x24))

    for registry_index, failed_records in enumerate(((), 'all', (1,), (2, 5, 11))):
        data = patterned(random_source, 0x140)
        owner = (0, 1, 0x80000000, random_source.getrandbits(32))[registry_index]
        def setup(env, data=data, failed_records=failed_records):
            receiver = env.object(0x140, 'command-registry', data=data)
            map_init(env, receiver + 4)
            physical_strings(env)
            log = env.object(8192, 'allocation-observations', fill=0)
            def allocation(e, c):
                n = e.calls_so_far(NEW)
                e.put(log + (n - 1) * 8, c.arguments[0], e.get(receiver))
                size = c.arguments[0]
                record_number = e.get(log + 8188) + (1 if size == 8 else 0)
                e.put(log + 8188, record_number)
                if size == 8 and (failed_records == 'all' or record_number in failed_records):
                    return 0
                return e.object(size, 'physical-heap-block', fill=0xB7)
            env.override(NEW, allocation)
            return receiver
        yield Case(f'command record failures {failed_records}', 0x422890, setup, receiver=lambda t: t, arguments=(owner,))

    configurations = [
        (1, 0, 0, 150, 150, 0, 0),
        (0, 0, 0, 150, 150, 0, 0),
        (0, 1, 0, 99, 150, 1, 0),
        (0, 1, 1, 99, 150, 0x1FF, 0),
        (0, 1, 0x80000000, 201, 201, 0x155, 0),
        (0, 1, 0, 100, 100, 2, 0),
        (0, 1, 0, 200, 200, 4, 0),
        (0, 1, 1, 101, 199, 8, 0),
        (0, 1, 1, 0xFFFFFFFF, 0, 0xAA, 0),
        (0, 1, 0, 99, 201, 0xFF, 167),
    ]
    for i in range(10):
        configurations.append((random_source.choice((0, 1, 0x80000000)), 1, random_source.choice((0, 1, 0xFFFFFFFF)), random_source.randrange(95, 206), random_source.randrange(95, 206), random_source.randrange(512), 0))
    for index, (global_value, available, bypass, x, y, buttons, error) in enumerate(configurations):
        manager_data = patterned(random_source, 0xA0)
        device_data = patterned(random_source, 0x248)
        key_values = tuple(random_source.choice((0, 1, 0x8000, 0x8001, 0x7FFF, 0xFFFF)) for _ in range(256))
        def setup(env, global_value=global_value, available=available, x=x, y=y, buttons=buttons, error=error,
                  manager_data=manager_data, device_data=device_data, key_values=key_values, index=index):
            manager = env.object(0xA0, 'input-manager', data=manager_data)
            device = env.object(0x248, 'physical-input-device', data=device_data)
            map_init(env, manager + 0x74)
            env.put(0x53723C, global_value)
            env.put(device, index % 2)
            env.put(device + 0x40, 9 if index % 2 else 8)
            env.put(device + 0x198, 52, 0x83, x, y, 0, 0, 0, 0, buttons, 1, 0xFFFF, 0, 0)
            env.put(device + 0x1CC, 0, available, index % 2, (index // 2) % 2)
            env.put(device + 0x220, 100, 200, 100, 200)
            physical_strings(env)
            log = env.object(8192, 'physical-sample-observations', fill=0)
            def keyboard(e, c):
                n = e.calls_so_far(KEY)
                key = c.arguments[0]
                e.put(log + (n - 1) * 32, key, e.get(manager), e.get(manager + 4), e.get(manager + 8), e.get(manager + 0xC), e.get(manager + 0x70), e.get(device + 0x1CC), e.get(device + 0x214))
                return key_values[key % 256]
            def joystick(e, c):
                n = e.calls_so_far(JOY)
                e.put(log + 4096 + (n - 1) * 16, c.arguments[0], c.arguments[1], e.get(device + 0x1CC), e.get(manager + 0x70))
                if not error:
                    # Independent successive physical samples; no game decisions here.
                    e.put(c.arguments[1], 52, 0x83, x if n == 1 else y, y if n == 1 else x, 0, 0, 0, 0, buttons if n == 1 else buttons ^ 0x55, 1, 0xFFFF, 0, 0)
                return error
            env.override(KEY, keyboard)
            env.override(JOY, joystick)
            env.override(NEW, lambda e, c: e.object(c.arguments[0], 'input-map-allocation', fill=0xC3))
            return manager, device
        yield Case(f'input physical configuration {index}', 0x430590, setup, receiver=lambda t: t[0], arguments=(lambda t: t[1], bypass))

    for path, result, mode in ((None, 0, 0), (b'', 0, 0), (b'MOVIES/INTRO.SMK', 0xFFFFFFFF, 0), (b'MOVIES/INTRO.SMK', 0xFFFFFFFF, 0x80000000), (b'MOVIES/INTRO.SMK', 7, 1), (b'other-resource.rez', 0, 0xFFFFFFFF)):
        data = patterned(random_source, 0x124)
        def setup(env, path=path, result=result, mode=mode, data=data):
            app = env.object(0x124, 'movie-application', data=data)
            pathname = 0 if path is None else env.object(len(path) + 1, 'resource-path', data=path + b'\0')
            env.put(app + 0x100, pathname)
            env.put(app + 0x9C, mode)
            log = env.object(16, 'file-query-observation', fill=0)
            def query(e, c):
                e.put(log, c.arguments[0], c.arguments[2], e.get(app + 0x9C), e.get(app + 0x120))
                output = bytearray(136)
                output[0] = 136
                output[2:4] = (2 if result == 0xFFFFFFFF else 0).to_bytes(2, 'little')
                output[8:8 + len(path)] = path
                e.write(c.arguments[1], bytes(output))
                return result
            env.override(OPEN, query)
            return app
        yield Case(f'movie bounded path={path!r} query={result:#x} mode={mode:#x}', 0x42B900, setup, receiver=lambda t: t)
