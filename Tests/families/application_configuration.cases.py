"""Original-only registry boundary cases; no host registry is consulted."""
from clawparity.cases import Case

CREATE = 0x546834
QUERY = 0x54682C


def text(env, value, name):
    return env.object(len(value) + 1, name, data=value + b'\0')


def setup_record(env, flag=1):
    obj = env.object(540, 'configuration', data=bytes((i * 37 + 19) % 256 for i in range(540)))
    env.put(obj, flag, 0x80000002, 0x13571111, 0x24682222,
            0x35793333, 0x468A4444, 0x579B5555)
    return obj


def creation(env, obj, statuses, disposition=1):
    log = env.object(5 * 640, 'create observations', fill=0xB7)

    def effect(e, call):
        n = e.calls_so_far(CREATE) - 1
        args = call.arguments
        slot = log + n * 640
        e.put(slot, call.receiver, *args)
        e.write(slot + 40, e.read(obj, 540) if obj else bytes(540))
        name = e.cstr(args[1])
        e.put(slot + 580, len(name))
        # Names are observed by the declared cstr argument too; retain a prefix.
        e.write(slot + 584, name[:48])
        status = statuses[min(n, len(statuses) - 1)]
        if status == 0:
            e.put(args[7], 0x61010000 + n * 0x101)
            e.put(args[8], disposition)
        e.put(slot + 632, e.get(args[7]), e.get(args[8]))
        return status

    env.override(CREATE, effect)


def querying(env, obj, value_type, payload, status=0, reported=None, error_data=b''):
    log = env.object(640, 'query observations', fill=0xD3)

    def effect(e, call):
        a = call.arguments
        cap = e.get(a[5])
        e.put(log, call.receiver, *a, cap)
        e.write(log + 32, e.read(obj, 540))
        name = e.cstr(a[1])
        e.put(log + 572, len(name))
        e.write(log + 576, name[:32])
        result = status
        count = len(payload) if reported is None else reported
        if result == 0 and len(payload) > cap:
            result = 234
        data = payload if result == 0 else error_data
        # Deterministic type -> bounded data -> length writes, including aliases.
        e.put(a[3], value_type)
        if len(data) > cap:
            raise ValueError('fixture data exceeds captured byte capacity')
        if data:
            e.write(a[4], data)
        e.put(a[5], count)
        e.put(log + 612, result, e.get(a[3]), e.get(a[5]))
        e.write(log + 624, e.read(a[4], min(cap, 16)))
        return result

    env.override(QUERY, effect)


def initializer(label, product, selection, statuses=(0,), flag=0, custom=False, alias=0, disposition=1):
    def setup(env):
        obj = setup_record(env, flag)
        company = text(env, b'Monolith Productions', 'company')
        version = text(env, b'1.0', 'version')
        prod = text(env, product, 'product')
        sel = 0 if selection is None else text(env, selection, 'selection')
        if alias:
            prod = obj + 0x1C + alias - 1
            env.write(prod, product + b'\0')
            if selection is not None:
                sel = obj + 0x11C + alias - 1
                env.write(sel, selection + b'\0')
        base = text(env, b'Independent Base', 'base') if custom else 0
        creation(env, obj, statuses, disposition)
        return dict(obj=obj, args=(company, prod, version, sel, 0x80000002, base))
    return Case(label, 0x4B5C50, setup, receiver=lambda t: t['obj'], arguments=tuple(lambda t, i=i: t['args'][i] for i in range(6)))


def string_case(label, flag=1, name=b'User', cap=30, fallback=b'default', value_type=1,
                payload=b'user\0', status=0, reported=None, error_data=b'', alias=None, null_data=False):
    def setup(env):
        obj = setup_record(env, flag)
        buf = env.object(280, 'destination with canaries', fill=0xA6) + 8
        length = env.object(12, 'length with canaries', fill=0xC9) + 4
        env.put(length, cap)
        nm = 0 if name is None else text(env, name, 'value name')
        fb = 0 if fallback is None else text(env, fallback, 'fallback')
        if alias == 'self':
            env.write(buf, fallback + b'\0')
            fb = buf
        elif alias == 'forward':
            env.write(buf + 4, fallback + b'\0')
            fb = buf + 4
        elif alias == 'source':
            env.write(obj + 0x1C, name + b'\0')
            nm = obj + 0x1C
            buf = obj + 0x11C
        elif alias == 'name-data':
            env.write(buf, name + b'\0')
            nm = buf
        elif alias == 'length-data':
            length = buf
            env.put(length, cap)
        querying(env, obj, value_type, payload, status, reported, error_data)
        return dict(obj=obj, args=(nm, 0 if null_data else buf, length, fb))
    return Case(label, 0x4B5E90, setup, receiver=lambda t: t['obj'], arguments=tuple(lambda t, i=i: t['args'][i] for i in range(4)))


def dword_case(label, flag=1, name=b'Runs', default=0x89ABCDEF, value=0xFEDCBA98, value_type=4, status=0, reported=4):
    def setup(env):
        obj = setup_record(env, flag)
        nm = 0 if name is None else text(env, name, 'dword name')
        querying(env, obj, value_type, value.to_bytes(4, 'little'), status, reported)
        return dict(obj=obj, nm=nm)
    return Case(label, 0x4B5F30, setup, receiver=lambda t: t['obj'], arguments=(lambda t: t['nm'], default))


def cases(random_source):
    for size in (0, 1, 2, 3, 4, 7, 255):
        product = bytes(random_source.randrange(33, 127) for _ in range(size))
        selection = bytes(random_source.randrange(33, 127) for _ in range(size))
        yield initializer(f'initialize lengths {size}', product, selection, custom=size % 2 == 0, disposition=1 + size % 2)
    yield initializer('startup string records', b'Claw', None)
    for step in range(5):
        for flag in (0, 0x80000002):
            yield initializer(f'create failure {step} flag {flag}', b'Claw', b'Profile', (0,) * step + (5,), flag, custom=True)
    for alias in (1, 5):
        yield initializer(f'in-place source alias {alias}', b'Claw-Source', b'Profile-Source', alias=alias)
    for status in (0, 2, 5, 234, 0x80000000, 0xFFFFFFFF):
        for disp in (1, 2):
            def setup(env, status=status, disp=disp):
                out = env.object(12, 'handle canaries', fill=0x83) + 4
                name = text(env, b'', 'empty subkey')
                creation(env, 0, (status,), disp)
                return dict(out=out, name=name)
            yield Case(f'direct wrapper status {status} disposition {disp}', 0x4B5FB0, setup,
                       arguments=(0x71234567, lambda t: t['name'], lambda t: t['out']))
    for flag in (0, 1, 2, 0x80000000):
        for name in (None, b'', b'Selected'):
            for status in (0, 5):
                def setup(env, flag=flag, name=name, status=status):
                    obj = setup_record(env, flag)
                    nm = 0 if name is None else text(env, name, 'selection name')
                    creation(env, obj, (status,), 2)
                    return dict(obj=obj, nm=nm)
                yield Case(f'select {flag} {name} {status}', 0x4B5DB0, setup, receiver=lambda t: t['obj'], arguments=(lambda t: t['nm'],))
    for payload in (b'', b'\0', b'a\0', b'ab\0', b'abc\0', b'abcd\0', b'raw-no-NUL'):
        for cap in (1, max(1, len(payload)), 30):
            yield string_case(f'string payload {payload} cap {cap}', payload=payload, cap=cap)
    for n in (0, 1, 2, 3, 4, 7, 255):
        fb = bytes(random_source.randrange(33, 127) for _ in range(n))
        yield string_case(f'unbounded fallback {n}', cap=1, fallback=fb, status=2)
    for typ in (0, 2, 3, 4, 7, 0xFFFFFFFF):
        yield string_case(f'wrong type {typ}', value_type=typ, payload=b'wrong\0')
    for status in (2, 5, 234, 0x80000000):
        for fb in (None, b'fallback'):
            yield string_case(f'query error {status} fallback {fb}', status=status, fallback=fb, error_data=b'ERR', reported=60)
    yield string_case('inactive default', flag=0)
    yield string_case('null name default', name=None)
    yield string_case('null destination null fallback', null_data=True, fallback=None)
    yield string_case('zero capacity default', cap=0)
    yield string_case('unsigned capacity high bit', cap=0x80000000)
    yield string_case('flag two empty name', flag=2, name=b'')
    for alias in ('self', 'forward', 'source', 'name-data', 'length-data'):
        yield string_case(f'alias {alias}', alias=alias, status=2 if alias in ('self', 'forward') else 0)
    for flag in (0, 1, 2, 0x80000000):
        for name in (None, b'', b'Runs'):
            yield dword_case(f'dword flag {flag} name {name}', flag=flag, name=name)
    for value in (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, random_source.getrandbits(32)):
        for reported in (0, 1, 4, 16):
            yield dword_case(f'dword value {value} size {reported}', value=value, reported=reported)
    for typ in (0, 1, 2, 3, 7, 0xFFFFFFFF):
        yield dword_case(f'dword wrong type {typ}', value_type=typ)
    for status in (2, 5, 234, 0x80000000):
        yield dword_case(f'dword error {status}', status=status, default=random_source.getrandbits(32))
