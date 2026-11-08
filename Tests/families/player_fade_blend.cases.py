"""Independent original cases for palette blend tables and their storage."""
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW = 0x4F63EC
DELETE = 0x4F6428


def table(env, active=1, size=17, pointer=True):
    data = env.object(max(1, size), 'blend bytes', data=bytes((i * 43 + 11) & 255 for i in range(max(1, size)))) if pointer else 0
    obj = env.object(12, 'blend table', words=[active, size, data])
    return obj


def manager(env, count=3, capacity=5, active=1, entries=None):
    if entries is None:
        entries = [table(env, active=(i % 2), size=13 + i) for i in range(max(0, count))]
    storage = env.object(capacity * 4, 'table pointers', words=entries + [0xA1957C32] * (capacity - len(entries))) if capacity else 0
    obj = env.object(24, 'manager', words=[active, 0xFACED123, storage, count, capacity, 7])
    return {'object': obj, 'storage': storage, 'entries': entries}


def direct(label, function, setup, arguments=()):
    return Case(label, function, setup, receiver=lambda t: t['object'], arguments=arguments)


def cases(random_source):
    for active, pointer in ((0, False), (0, True), (1, False), (1, True), (0x80000000, True)):
        for function in (0x4C76E0, 0x4C78D0):
            def setup(env, active=active, pointer=pointer):
                return {'object': table(env, active, 23, pointer)}
            yield direct(f'{function:x} active {active:x} data {pointer}', function, setup)
    yield direct('construct overwrites all three dirty words', 0x4C76D0,
                 lambda e: {'object': e.object(12, 'dirty table', words=[0xDEADBEEF, 0xFBCA2143, 0xACED8172])})

    for active, old, fail in ((0, False, False), (0, True, False), (1, True, False), (0, False, True), (7, True, True)):
        def setup(env, active=active, old=old, fail=fail):
            env.override(NEW, allocate(fail=fail))
            return {'object': table(env, active, 19, old)}
        yield direct(f'allocate active {active} previous {old} failure {fail}', 0x4C76F0, setup, (31,))
    yield direct('allocate zero bytes remains an allocator request', 0x4C76F0,
                 lambda e: {'object': table(e, 0, 12, False)}, (0,))

    for function in (0x4C6270, 0x4C61F0):
        for active, count, capacity in ((0, 0, 0), (0, 0, 3), (1, 0, 0), (1, -1, 0), (1, 3, 5)):
            yield direct(f'{function:x} active {active} count {count} capacity {capacity}', function,
                         lambda e, a=active, n=count, c=capacity: manager(e, n, c, a))

    def clear_changes(env):
        tokens = manager(env, 3, 5, 1)
        # The first table's active data is released, then the manager reloads
        # its current slot and count. Keep displaced objects live for comparison.
        first = tokens['entries'][0]
        env.put(first, 1)
        def change(env, call):
            if env.calls_so_far(DELETE) == 1:
                env.put(tokens['storage'], 0)
                env.put(tokens['object'] + 12, 1)
            env.release(call.arguments[0])
            return 0
        env.override(DELETE, change)
        return tokens
    yield direct('clear reloads current entry and count after release', 0x4C6270, clear_changes)

    for count, selected in ((0, None), (-1, None), (3, None), (3, 0), (3, 1), (3, 2)):
        yield direct(f'remove count {count} selection {selected}', 0x4C7510,
                     lambda e, n=count: manager(e, n, 5),
                     (lambda t, k=selected: 0xF0ABCDEF if k is None else t['entries'][k],))

    def remove_changes(env):
        tokens = manager(env, 3, 5)
        first = tokens['entries'][0]
        env.put(first, 1)
        def change(env, call):
            if env.calls_so_far(DELETE) == 1:
                env.put(tokens['storage'], 0)
                env.put(tokens['object'] + 12, 2)
            env.release(call.arguments[0])
            return 0
        env.override(DELETE, change)
        return tokens
    yield direct('remove reloads slot and count after release', 0x4C7510, remove_changes,
                 (lambda t: t['entries'][0],))

    # Empty, existing, shrink, exposure, explicit growth, both dynamic clamps,
    # and equality/strict inequality at capacity+growth.
    arrays = ((0, 0, 0, 0, -1), (0, 0, 3, 0, 5), (3, 5, 0, 4, -1),
              (3, 5, 2, 0, -1), (3, 5, 3, 0, -1), (3, 5, 5, 0, -1),
              (3, 5, -1, 4, 11), (3, 3, 4, 0, -1), (3, 3, 7, 0, -1),
              (3, 3, 11, 0, -1), (32, 32, 33, 0, -1), (40, 40, 41, 0, -1),
              (8200, 8200, 8201, 0, -1), (3, 3, 4, 9, -1), (3, 3, 12, 9, -1),
              (3, 3, 20, 9, 2))
    for old, capacity, new, grow, replacement in arrays:
        values = [random_source.getrandbits(32) for _ in range(capacity)]
        def setup(env, old=old, capacity=capacity, grow=grow, values=values):
            storage = env.object(capacity * 4, 'array contents', words=values) if capacity else 0
            obj = env.object(20, 'pointer array', words=[0x13579ACE, storage, old, capacity, grow])
            return {'object': obj}
        yield direct(f'array {old}/{capacity} to {new} growth {grow}/{replacement}',
                     0x4DEE30, setup, (new & 0xFFFFFFFF, replacement & 0xFFFFFFFF))

    def array_changes_during_allocation(env):
        old = env.object(12, 'original array', words=[0x81ABCDEF, 0x23765410, 0x99887766])
        replacement = env.object(8, 'replacement array', words=[0xA1B2C3D4, 0xF1E2D3C4])
        obj = env.object(20, 'array with changing source', words=[0x13579ACE, old, 3, 3, 4])
        def change(env, call):
            env.put(obj + 4, replacement, 2)
            return env.object(call.arguments[0], 'grown array')
        env.override(NEW, change)
        return {'object': obj}
    yield direct('array reloads storage and size after allocation', 0x4DEE30,
                 array_changes_during_allocation, (6, 0xFFFFFFFF))

    for label, data, rgb in (
        ('ties retain first', bytes([17, 29, 41, 197]) * 256, (17, 29, 41)),
        ('last palette entry wins', bytes([255, 0, 0, 23]) * 255 + bytes([1, 2, 3, 247]), (1, 2, 3)),
        ('masked channel arguments', bytes([12, 34, 56, 239]) * 256, (0x1234560C, 0xFFFF0022, 0x80000038)),
        ('strict ties at nonzero distance', bytes([10, 20, 30, 1]) + bytes([12, 20, 30, 254]) + bytes([250, 250, 250, 0]) * 254, (11, 20, 30)),
    ):
        yield Case(label, 0x4C7580, lambda e, data=data: e.object(1024, 'palette', data=data),
                   arguments=(lambda t: t, *rgb))
    for i in range(5):
        data = bytes(random_source.getrandbits(8) for _ in range(1024))
        rgb = tuple(random_source.getrandbits(32) for _ in range(3))
        yield Case(f'random nearest {i}', 0x4C7580,
                   lambda e, data=data: e.object(1024, 'palette', data=data), arguments=(lambda t: t, *rgb))

    def blend_setup(data, fail_at=0, initial=False, global_bits=0x3F800000):
        def setup(env):
            tokens = manager(env, 1 if initial else 0, 3 if initial else 0)
            tokens['palette'] = env.object(1024, 'palette', data=data)
            env.put(0x513700, global_bits)
            if fail_at:
                def allocate_n(env, call):
                    if env.calls_so_far(NEW) == fail_at:
                        return 0
                    return env.object(max(1, call.arguments[0]), 'allocation')
                env.override(NEW, allocate_n)
            return tokens
        return setup
    palette = bytes((i * 37 + i // 4 * 19 + 13) & 255 for i in range(1024))
    for failed in (1, 2):
        yield direct(f'blend allocation {failed} fails', 0x4C6BD0, blend_setup(palette, failed),
                     (lambda t: t['palette'], 3, 0x89A3C567))
    for width, bits, initial in ((0, 0x3F800000, False), (0x80000000, 0x3F800000, False), (1, 0x3F800000, False),
                                 (2, 0x3F800000, True), (3, 0x3F800000, False),
                                 (7, 0x3F800001, False), (2, 0xBF000000, False), (1, 0x00000000, False),
                                 (1, 0x80000000, False), (1, 0x00000001, False),
                                 (1, 0x7F7FFFFF, False), (2, 0x7F800000, False),
                                 (2, 0xFF800000, False), (2, 0x7FC12345, False),
                                 (2, 0x7F812345, False)):
        color = random_source.getrandbits(32)
        yield direct(f'blend width {width} constant {bits:08x} existing {initial}', 0x4C6BD0,
                     blend_setup(palette, initial=initial, global_bits=bits),
                     (lambda t: t['palette'], width, color))

    rounding_palette = bytes([13, 50, 87, 123]) + palette[4:]
    yield direct('blend thirds retain adjacent truncation distinctions', 0x4C6BD0,
                 blend_setup(rounding_palette),
                 (lambda t: t['palette'], 3, 0x19A3C567))

    # The inline CString word points twelve bytes beyond its allocated header.
    for refs, shared in ((4, True), (3, False), (1, False), (0, False), (-1, False)):
        def setup(env, refs=refs, shared=shared):
            header = env.object(24, 'CString storage', words=[refs & 0xFFFFFFFF, 7, 11], data=None)
            env.write(header + 12, b'fade me\0')
            env.put(0x52E1C8, header if shared else 0)
            def decrement(env, call):
                result = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
                env.put(call.arguments[0], result)
                return result
            env.override(0x5469E8, decrement)
            return header + 12
        yield Case(f'diagnostic refs {refs} shared {shared}', 0x4EC6B0, setup,
                   arguments=(lambda t: t,))
