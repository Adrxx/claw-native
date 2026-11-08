"""Lifecycle cases with physical DirectDraw services and actual mode callbacks."""
from clawparity.cases import Case
from clawparity.env import EnumerationCallbackContract

NEW, DELETE = 0x4F63EC, 0x4F6428
GLOBAL_ARRAY = 0x541378


def array(env, at, values=(), capacity=None):
    capacity = len(values) if capacity is None else capacity
    data = env.object(capacity * 4, 'array-data', fill=0x65) if capacity else 0
    if values:
        env.put(data, *values)
    env.put(at, 0x5133B0, data, len(values), capacity, 3)


def base(env, error=0):
    target = env.object(0x884, 'manager', fill=0xA7)
    for offset in (0x3B8, 0x3D4):
        env.put(target + offset, 0x5133A0, 0, 0, 0, 0, 0, 10)
    array(env, target + 0x3F0)
    array(env, GLOBAL_ARRAY)
    env.put(target, 0)
    env.put(target + 0x880, error)
    env.put(0x541374, 0x1963A5)
    env.put(0x541398, 0)
    env.put(0x54139C, 0, 0, 0, 0)
    env.put(0x54135C, 0x11335577, 0x22446688, 0x33557799,
            0x446688AA, 0x557799BB, 0x6688AACC)
    return target


def services(env, target, *, coop=0, caps=0, enum=0, mode=0, query=0,
             masks=(0xF800, 0x7E0, 0x1F), depth=16, hardware=0x08000000,
             mutate=None):
    interface = env.object(4, 'DirectDraw')
    table = env.object(0x58, 'DirectDraw-vtable')
    record = env.object(0x800, 'service-observations')
    env.put(interface, table)
    env.put(target, interface)

    def effect(slot, result):
        def invoke(e, call):
            # Surviving records expose explicit receiver/args and publication order.
            row = record + slot * 0x10
            e.put(row, call.receiver, *call.arguments)
            e.put(row + 0x20, e.get(0x541374), e.get(target),
                  e.get(target + 0x470), e.get(target + 0x880))
            if slot == 0x2C:
                e.write(row + 0x40, e.read(call.arguments[1], 0x13C))
                e.write(row + 0x180, e.read(call.arguments[2], 0x13C))
                e.put(call.arguments[1] + 4, hardware | 0x124)
            if slot == 0x30:
                e.write(row + 0x40, e.read(call.arguments[1], 0x6C))
                e.put(call.arguments[1] + 0x54, depth, *masks)
            if mutate:
                mutate(e, call, slot)
            return result
        return invoke

    for slot, argc, result in ((8, 1, 0xA001), (0x20, 5, enum),
                               (0x2C, 3, caps), (0x30, 2, query),
                               (0x4C, 1, 0xA002), (0x50, 3, coop), (0x54, 4, mode)):
        env.put(table + slot, env.stub(f'DirectDraw[{slot:#x}]', 'stdcall', argc, effect(slot, result)))
    return interface


def surface(env, count=3, borrowed=0, present=True, shrink=False):
    target = env.object(0xB8, 'surface', fill=0xC3)
    record = env.object(0x100, 'surface-observations')
    table = env.object(12, 'surface-methods')
    com = env.object(4, 'surface-COM')
    values = []
    for index in range(count):
        if index == 1:
            values.append(0)
            continue
        child = env.object(12, f'child-{index}', fill=0x41 + index)
        vtable = env.object(4, f'child-vtable-{index}')
        def destroy(e, call, index=index):
            e.put(record + index * 16, call.receiver, *call.arguments,
                  e.get(target), e.get(target + 0x98))
            if shrink:
                e.put(target + 0x98, 1)
            e.release(call.receiver)
            return 0xAB00 + index
        env.put(vtable, env.stub(f'child-{index}-destroy', 'thiscall', 1, destroy))
        env.put(child, vtable)
        values.append(child)
    array(env, target + 0x90, values)
    def com_release(e, call):
        e.put(record + 0xC0, call.receiver, *call.arguments, e.get(target + 8),
              e.get(target + 0xB4))
        return 0x7788
    env.put(table + 8, env.stub('surface-Release', 'stdcall', 1, com_release))
    env.put(com, table)
    env.put(target + 8, com if present else 0)
    env.put(target + 0x78, borrowed)
    return target


def linked(env, target, offset, palette=False):
    nodes = [env.object(12, f'node-{i}') for i in range(3)]
    record = env.object(32, 'list-observations')
    payloads = []
    for i in range(3):
        if i == 1:
            payloads.append(0)
            continue
        payload = env.object(0x38, f'payload-{i}', fill=0x83 + i)
        if palette:
            env.put(payload + 0xC, env.object(7, 'palette-colors'),
                    env.object(11, 'palette-map'))
            env.put(payload + 0x18, env.object(13, 'palette-extra'))
        else:
            table = env.object(4, 'payload-vtable')
            def destroy(e, call, i=i):
                e.put(record + i * 8, call.receiver, *call.arguments)
                # The next pointer was cached before the deleting callback.
                e.put(nodes[i], 0)
                e.release(call.receiver)
                return 0
            env.put(table, env.stub(f'list-destroy-{i}', 'thiscall', 1, destroy))
            env.put(payload, table)
        payloads.append(payload)
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i < 2 else 0,
                nodes[i - 1] if i else 0, payloads[i])
    # Nodes are separately backed; CPlex ownership is independently released.
    blocks = [env.object(16, f'CPlex-{i}') for i in range(2)]
    env.put(blocks[0], blocks[1]); env.put(blocks[1], 0)
    env.put(target + offset + 4, nodes[0], nodes[-1], 3, 0, blocks[0], 10)


def manager_setup(**options):
    def setup(env):
        target = base(env, options.get('error', 0))
        parameters = {key: value for key, value in options.items()
                      if key not in ('error', 'created', 'create_result', 'old_modes', 'lists')}
        interface = services(env, target, **parameters)
        env.put(0x541398, 0 if options.get('created') else interface)
        if options.get('old_modes'):
            array(env, target + 0x3F0, [env.object(0x6C, 'old-mode', fill=i+1) for i in range(3)])
        if options.get('lists'):
            linked(env, target, 0x3B8)
            linked(env, target, 0x3D4, palette=True)
        def create(e, call):
            if not options.get('create_result', 0):
                e.put(call.arguments[1], interface)
            return options.get('create_result', 0)
        env.override(0x546850, create)
        return {'target': target}
    return setup


def direct(label, address, setup, args=()):
    return Case(label, address, setup, receiver=lambda t: t['target'], arguments=args)


def enumeration_setup(descriptors, status=0, reuse=False, diagnostics=False, **options):
    def setup(env):
        tokens = manager_setup(old_modes=True, **options)(env)
        target = tokens['target']
        # Both arrays begin populated. The old global payloads are borrowed;
        # clearing this array must not delete them as manager-owned modes.
        array(env, GLOBAL_ARRAY, [env.object(0x6C, 'old-global-mode', fill=0x9B)])
        buffers = [env.object(0x6C, f'physical-mode-{i}', data=data)
                   for i, data in enumerate(descriptors)]
        shared = env.object(0x6C, 'reused-physical-descriptor', fill=0xD5) if reuse else 0
        receipt = env.object(0xC0 + len(descriptors) * 0x50, 'enumeration-receipts', fill=0xB6)

        def snapshot(e, at):
            e.put(at, e.get(0x541374), e.get(target + 0x880))
            e.write(at + 8, e.read(target + 0x3F0, 0x14))
            e.write(at + 0x1C, e.read(GLOBAL_ARRAY, 0x14))

        def enumerate_modes(e, call):
            e.put(receipt, call.receiver, *call.arguments)
            snapshot(e, receipt + 0x20)
            for index, buffer in enumerate(buffers):
                descriptor = buffer
                if shared:
                    e.write(shared, e.read(buffer, 0x6C))
                    descriptor = shared
                row = receipt + 0xC0 + index * 0x50
                e.put(row, descriptor, call.arguments[3], e.get(GLOBAL_ARRAY + 8))
                disposition = e.invoke_enumeration_callback(call, (descriptor, call.arguments[3]))
                e.put(row + 0xC, disposition)
                snapshot(e, row + 0x10)
                if not disposition:
                    break
            return status

        service = env.stub('DirectDraw::EnumDisplayModes physical descriptors', 'stdcall', 5,
                           enumerate_modes)
        table = env.get(env.get(target))
        env.put(table + 0x20, service)
        env.enumeration_callback(EnumerationCallbackContract(
            '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',
            service, 0x4BCDA0, 0x4BCDD5,
            'b1ec90ddc031508698743331284259352cdee2a73db06eead82b3bc298efcb2d'))
        if diagnostics:
            env.put(0x5413A4, 1)
            def beep(e, call):
                e.put(receipt + 0x60, call.receiver, *call.arguments)
                snapshot(e, receipt + 0x80)
                return 1
            env.override(0x546CA4, beep)
        return tokens
    return setup


def cases(random_source):
    def construct(env):
        return {'target': env.object(0x884, 'unconstructed-manager', fill=0xD9)}
    yield direct('construct poisoned storage', 0x4BC120, construct)
    for address in (0x4B9540, 0x4BC610, 0x4BC5F0):
        for count, borrowed, present, shrink in ((0, 0, False, False), (1, 0, True, False),
                                                (3, 0, True, False), (3, 0x101, True, False),
                                                (3, 0x100, True, True)):
            for flag in ((0, 1, 2, 0x101) if address == 0x4BC5F0 else (0,)):
                def setup(env, count=count, borrowed=borrowed, present=present, shrink=shrink):
                    return {'target': surface(env, count, borrowed, present, shrink)}
                yield direct(f'surface {address:x} count={count} borrowed={borrowed} shrink={shrink} flag={flag}',
                             address, setup, (flag,) if address == 0x4BC5F0 else ())
    for address, offset, palette in ((0x4BC4B0, 0x3B8, False), (0x4BC9D0, 0x3D4, True)):
        for populated in (False, True):
            def setup(env, offset=offset, palette=palette, populated=populated):
                target = base(env)
                if populated:
                    linked(env, target, offset, palette)
                return {'target': target}
            yield direct(f'list {address:x} populated={populated}', address, setup)
    for address in (0x4BC400, 0x4BC1B0):
        for populated in (False, True):
            for restore in (0, 1):
                yield direct(f'manager teardown {address:x} populated={populated} restore={restore}', address,
                             manager_setup(old_modes=populated, lists=populated),
                             (restore,) if address == 0x4BC400 else ())
    def no_interface(env):
        return {'target': base(env)}
    yield direct('release absent interface restore', 0x4BC400, no_interface, (1,))
    for error in (0, 0x7351):
        for failure in ('coop', 'create_result', 'mode', 'query'):
            kwargs = {failure: 0x80004005, 'error': error, 'created': failure == 'create_result'}
            yield direct(f'initialize {failure} error={error}', 0x4BC220, manager_setup(**kwargs),
                         (0x1834, 0, 640, 480, 0 if failure == 'query' else 16, 0x19))
    for width, height, depth in ((0, 480, 0), (-1, 480, 16), (640, 0, 0),
                                  (640, -1, 8), (640, 480, 16), (640, 480, 0)):
        for created in (False, True):
            yield direct(f'initialize {width}x{height}/{depth} created={created}', 0x4BC220,
                         manager_setup(created=created, caps=0x80004005 if created else 0,
                                       enum=0x80004005 if width == 0 else 0,
                                       hardware=0 if created else 0x08000000),
                         (0x1834, 0, width, height, depth, 0x19))
    for status in (0, 0x80004005):
        yield direct(f'enumerate no descriptors status={status}', 0x4BCC50,
                     manager_setup(enum=status, old_modes=True))
    mode_sets = [
        ('singleton', [(640, 480, 16)]),
        ('ascending pair', [(320, 240, 8), (640, 480, 16)]),
        ('descending pair', [(640, 480, 16), (320, 240, 8)]),
        ('equal keys distinct payloads', [(640, 480, 16)] * 4),
        ('last becomes first', [(800, 600, 32), (640, 480, 16), (320, 240, 8)]),
        ('height and depth ties', [(640, 480, 32), (640, 600, 8), (640, 480, 8),
                                   (640, 480, 16), (320, 900, 32)]),
        ('unsigned keys', [(0xFFFFFFFF, 1, 8), (0x80000000, 0, 32), (0, 0xFFFFFFFF, 16),
                           (0, 0x80000000, 32), (0, 0, 0xFFFFFFFF), (0, 0, 0)]),
    ]
    for count in (3, 9, 17):
        mode_sets.append((f'random {count}', [tuple(random_source.getrandbits(32)
                                                   for _ in range(3)) for _ in range(count)]))
    for label, modes in mode_sets:
        descriptors = []
        for width, height, depth in modes:
            data = bytearray(random_source.randrange(256) for _ in range(0x6C))
            for offset, value in ((0, 0x6C), (8, height), (0xC, width), (0x54, depth)):
                data[offset:offset + 4] = value.to_bytes(4, 'little')
            descriptors.append(bytes(data))
        for reuse in (False, True):
            yield direct(f'enumerate {label} reuse={reuse}', 0x4BCC50,
                         enumeration_setup(descriptors, reuse=reuse))
        # A physical enumeration failure does not discard modes already delivered.
        yield direct(f'enumerate {label} partial failure', 0x4BCC50,
                     enumeration_setup(descriptors, status=0x887601C2, diagnostics=True,
                                       error=0x7351))
        if len(modes) == 3:
            for created, mode_result in ((False, 0), (True, 0), (False, 0x80004005)):
                yield direct(f'initialize enumerated {label} created={created} mode={mode_result}',
                             0x4BC220, enumeration_setup(descriptors, created=created, mode=mode_result),
                             (0x1834, 0, 640, 480, 16, 0x19))
    for count, capacity in ((0, 0), (1, 4), (4, 4)):
        data = bytes(random_source.randrange(256) for _ in range(0x6C))
        def setup(env, count=count, capacity=capacity, data=data):
            array(env, GLOBAL_ARRAY, [env.object(0x6C, 'existing-mode', fill=i+1) for i in range(count)], capacity)
            return {'descriptor': env.object(0x6C, 'descriptor', data=data)}
        yield Case(f'callback copies all words count={count} capacity={capacity}', 0x4BCDA0, setup,
                   arguments=(lambda t: t['descriptor'], 0x789ABCDE))
    ordered = [(1, 2, 3), (0xFFFFFFFF, 1, 1), (0x80000000, 0, 0), (0, 0xFFFFFFFF, 32),
               (1, 2, 4), (1, 3, 0), (1, 1, 0), (1, 2, 0xFFFFFFFF)]
    ordered += [tuple(random_source.getrandbits(32) for _ in range(3)) for _ in range(5)]
    for left in ordered:
        for right in ordered:
            def setup(env, left=left, right=right):
                result = {}
                for key, values in (('left', left), ('right', right)):
                    p = env.object(0x6C, key, fill=0x49)
                    env.put(p + 0xC, values[0]); env.put(p + 8, values[1]); env.put(p + 0x54, values[2])
                    result[key] = p
                return result
            yield Case(f'unsigned lexicographic {left}/{right}', 0x4BCDE0, setup,
                       arguments=(lambda t: t['left'], lambda t: t['right']))
    patterns = [(0, 0, 0), (0xFFFFFFFF,) * 3, (1, 0x80000000, 0x55AA55AA),
                (0xFF0000, 0xFF00, 0xFF)]
    patterns += [tuple(random_source.getrandbits(32) for _ in range(3)) for _ in range(8)]
    for masks in patterns:
        yield direct(f'pixel masks {masks}', 0x4BD0C0, manager_setup(masks=masks))
    yield direct('pixel query failure preserves globals', 0x4BD0C0, manager_setup(query=0x80004005))
    for error in (0, 0x3512):
        for mode, query in ((0, 0), (0x887601C2, 0), (0, 0x80004005)):
            yield direct(f'set mode={mode} query={query} error={error}', 0x4BD1C0,
                         manager_setup(error=error, mode=mode, query=query), (801, 603, 24))
    def logger_changes_error(env):
        tokens = manager_setup(mode=0x887601C2)(env)
        target = tokens['target']
        record = env.object(32, 'beep-error-observations')
        env.put(0x5413A4, 1)
        def beep(e, call):
            index = e.calls_so_far(0x546CA4) - 1
            e.put(record + index * 12, *call.arguments, e.get(target + 0x880),
                  e.get(0x541374))
            if index == 1:
                e.put(target + 0x880, 0)
            return 1
        env.override(0x546CA4, beep)
        return tokens
    yield direct('initialize rereads error after physical diagnostic', 0x4BC220,
                 logger_changes_error, (0x1834, 0, 640, 480, 16, 0x19))
    for address in (0x4BC400, 0x4BCC50):
        def shrink_modes(env):
            tokens = manager_setup(old_modes=True)(env)
            target = tokens['target']
            first = env.get(env.get(target + 0x3F4))
            def free_and_shrink(e, call):
                value = call.arguments[0]
                if value == first:
                    e.put(target + 0x3F8, 1)
                if value:
                    e.release(value)
                return 0
            env.override(DELETE, free_and_shrink)
            return tokens
        yield direct(f'mode deletion rereads count {address:x}', address, shrink_modes,
                     (0,) if address == 0x4BC400 else ())
    for address in (0x4BC400, 0x4BCC50):
        def negative_modes(env):
            tokens = manager_setup()(env)
            env.put(tokens['target'] + 0x3F8, 0xFFFFFFFF)
            return tokens
        yield direct(f'negative signed mode count {address:x}', address, negative_modes,
                     (0,) if address == 0x4BC400 else ())
    def interface_changes(env):
        target = base(env)
        second = services(env, target, masks=(0x80000000, 0xAAAAAAAA, 7))
        def replace(e, call, slot):
            if slot == 0x54:
                e.put(target, second)
        services(env, target, mutate=replace)
        return {'target': target}
    yield direct('set mode rereads interface before pixel query', 0x4BD1C0,
                 interface_changes, (1920, 1080, 32))
