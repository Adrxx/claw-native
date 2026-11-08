"""Independent original save-reader and player-record input cases."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

NEW = 0x4F63EC
SIZE = 0x2648
PAYLOAD = SIZE - 4


def string(env, value, name='text'):
    return env.object(len(value) + 1, name, data=value + b'\0')


def cstring(env, value):
    p = env.object(12 + len(value) + 1, 'CString')
    env.put(p, 1, len(value), len(value))
    env.write(p + 12, value + b'\0')
    return p + 12


def physical(env):
    tls = env.object(0x100, 'CRT thread data', fill=0)
    errors = env.object(4, 'last error', words=[7])
    env.override(0x546A7C, returns(tls))
    env.override(0x546B0C, lambda e, c: e.get(errors))
    def set_error(e, c):
        e.put(errors, c.arguments[0])
        return 0
    env.override(0x546AB8, set_error)
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))
    def interlocked(delta):
        def effect(e, c):
            a = c.arguments[0]
            value = (e.get(a) + delta) & 0xffffffff
            e.put(a, value)
            return value
        return effect
    env.override(0x5469E8, interlocked(-1))
    env.override(0x5469EC, interlocked(1))
    env.override(0x546AD0, returns(0))
    def copy_n(e, c):
        dst, src, count = c.arguments
        if count:
            e.write(dst, e.cstr(src)[:count - 1] + b'\0')
        return dst
    env.override(0x5469CC, copy_n)
    env.override(0x546A04, returns(1))
    env.override(0x546B00, returns(0xffffffff))


def manager(env, names=(), free=True):
    physical(env)
    m = env.object(0x60, 'manager', fill=0)
    env.put(m + 0x18, 8, cstring(env, b'C:\\claw\\save.dat'))
    records = []
    nodes = []
    for name in names:
        if name is None:
            record = 0
        elif name == 'wrap':
            record = 0xffffffec
        else:
            record = env.object(SIZE, 'player', fill=0x39)
            env.put(record, 0x50FEAC)
            env.write(record + 0x14, name + b'\0')
        records.append(record)
        nodes.append(env.object(12, 'list node'))
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0,
                nodes[i - 1] if i else 0, records[i])
    env.put(m + 4, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
    if free:
        pool = env.object(12 * 8, 'free list nodes')
        for i in range(8):
            env.put(pool + i * 12, pool + (i + 1) * 12 if i < 7 else 0)
        env.put(m + 0x10, pool)
    return {'m': m, 'records': records, 'nodes': nodes}


def checksums(env, p, fail=None):
    env.put(p + 8, 1)
    for i in range(15):
        for group, offset in enumerate((0x21c4 + i * 0x44, 0x1780 + i * 0xb0, 0x17c4 + i * 0xb0)):
            a = p + offset
            terms = [((i + 1) * 0x1030507 + (j + 1) * 0x7139 + group * 0x81234) & 0xffffffff for j in range(10)]
            env.put(a + 0x1c, *terms)
    # The ranges touch, so derive checksums after every term has been installed.
    for i in range(15):
        for group, offset in enumerate((0x21c4 + i * 0x44, 0x1780 + i * 0xb0, 0x17c4 + i * 0xb0)):
            a = p + offset
            value = sum(env.get(a + 0x1c + j * 4) * env.get(0x52d698 + j * 4) for j in range(10)) & 0xffffffff
            env.put(a + 4, value ^ (1 if fail == (i, group) else 0))


def make_case(label, address, setup, argc=0, **options):
    return Case(label, address, setup, receiver=lambda t: t['m'],
                arguments=tuple((lambda t, i=i: t['args'][i]) for i in range(argc)), **options)


def cases(random_source):
    for address in (0x423F00, 0x49AD50, 0x49ADC0):
        for fill in (0x63, random_source.randrange(1, 256)):
            yield make_case(f'{address:x} distinct memory {fill}', address,
                            lambda e, fill=fill: {'m': e.object(SIZE + 16, 'record with guard', fill=fill)})
    for name in (None, b'', b'a', b'ab', b'abc', b'abcd', b'K' * 31, b'Q' * 32):
        for optional in (0, 1, 2, 3):
            def setup(e, name=name, optional=optional):
                p = e.object(SIZE + 64, 'destination', fill=0xA7)
                return {'m': p, 'args': [string(e, name) if name is not None else 0,
                        string(e, b'first optional' * 7) if optional & 1 else 0,
                        string(e, b'last string') if optional & 2 else 0, random_flag]}
            random_flag = random_source.getrandbits(32)
            # Bind the flag per generated case, including high bytes that must be ignored.
            def bound(e, setup=setup, flag=random_flag):
                result = setup(e)
                result['args'][3] = flag
                return result
            yield make_case(f'initialize name {name!r} optional {optional}', 0x49A5A0, bound, 4)
    for fail in (None, (0, 0), (0, 1), (0, 2), (14, 0), (14, 2), 'version'):
        def setup(e, fail=fail):
            p = e.object(SIZE + 16, 'checksum player', fill=0x47)
            checksums(e, p, fail)
            if fail == 'version':
                e.put(p + 8, 0x80000001)
            return {'m': p}
        yield make_case(f'validate player {fail}', 0x49A8F0, setup)
    yield Case('null checksum record', 0x49A990, arguments=(0,))
    for good in (False, True):
        terms = [random_source.getrandbits(32) for _ in range(10)]
        def setup(e, good=good, terms=terms):
            p = e.object(0x50, 'checksum record', fill=0x91)
            e.put(p + 0x1c, *terms)
            checksum = sum(v * e.get(0x52d698 + i * 4) for i, v in enumerate(terms)) & 0xffffffff
            e.put(p + 4, checksum ^ (0 if good else 0x80000001))
            return {'args': [p]}
        yield Case(f'checksum arithmetic {good}', 0x49A990, setup, arguments=(lambda t: t['args'][0],))
    for name in (None, b'', b'a', b'Z' * 31, b'Y' * 32):
        for valid in (False, True):
            def setup(e, name=name, valid=valid):
                physical(e)
                p = e.object(SIZE + 16, 'copy destination', fill=0x9C)
                src = 0
                if name is not None:
                    block = e.object(SIZE, 'serialized source', fill=0x73)
                    checksums(e, block, None if valid else (3, 1))
                    e.write(block + 0x14, name + b'\0')
                    src = block + 4
                return {'m': p, 'args': [src]}
            yield make_case(f'payload {name!r} checksums {valid}', 0x49A6D0, setup, 1)
    for address in (0x49B950, 0x49B970):
        for names in ((), (b'Alpha',), (b'First', None, b'Last')):
            yield make_case(f'{address:x} cleanup {names}', address, lambda e, names=names: manager(e, names))
    for names in ((), (b'Alpha', b'bETA', b'Gamma'), ('wrap', b'Alpha')):
        for query in (None, b'alpha', b'BETA', b'Gamma', b'missing'):
            def setup(e, names=names, query=query):
                t = manager(e, names)
                t['args'] = [string(e, query) if query is not None else 0]
                return t
            yield make_case(f'lookup {names} {query}', 0x49BEE0, setup, 1)
    for count in (0, 1, 3):
        for index in (-2, -1, 0, count - 1):
            def setup(e, count=count, index=index):
                t = manager(e, tuple(f'Player{i}'.encode() for i in range(count)))
                requested = 0 if index == -2 else (t['records'][index] if 0 <= index < count else e.object(SIZE, 'absent record'))
                t['args'] = [requested]
                return t
            yield make_case(f'remove {count} index {index}', 0x49BF30, setup, 1)
    for address in (0x49BDB0, 0x49BE50):
        for mode in ('null', 'duplicate', 'valid', 'invalid', 'allocation fails'):
            def setup(e, address=address, mode=mode):
                t = manager(e, (b'Existing',))
                name = b'EXISTING' if mode == 'duplicate' else (b'X' * 32 if mode in ('invalid', 'allocation fails') else b'New player')
                if address == 0x49BDB0:
                    t['args'] = [0 if mode == 'null' else string(e, name), string(e, b'A'), string(e, b'B'), 0x104]
                else:
                    p = e.object(SIZE, 'payload source', fill=0x79)
                    checksums(e, p)
                    e.write(p + 0x14, name + b'\0')
                    t['args'] = [0 if mode == 'null' else p + 4]
                if mode == 'allocation fails':
                    e.override(NEW, allocate(fail=True))
                return t
            yield make_case(f'{address:x} {mode}', address, setup, 4 if address == 0x49BDB0 else 1)
    for mode in ('open fails', 'small', 'header zero', 'allocation fails', 'payload zero',
                 'checksum wrong', 'not multiple', 'zero count', 'equal count', 'clamp count',
                 'short records', 'invalid player', 'duplicate player', 'selected same', 'short read'):
        yield make_case(f'reader {mode}', 0x49B9A0, reader_setup(mode, random_source.getrandbits(32)))
    for current, drive, windows, mode in ((b'', 3, b'', 'open fails'),
                                          (b'C:\\Games', 3, b'', 'open fails'),
                                          (b'D:\\Claw', 5, b'C:\\Windows', 'open fails'),
                                          (b'', 3, b'C:\\Win', 'equal count'),
                                          (b'C:\\Games', 3, b'', 'short records'),
                                          (b'C:\\Games', 3, b'', 'duplicate player')):
        def setup(e, current=current, drive=drive, windows=windows, mode=mode):
            t = reader_setup(mode, 0)(e)
            def current_dir(e, c):
                if current:
                    e.write(c.arguments[1], current + b'\0')
                return len(current)
            def win_dir(e, c):
                if windows:
                    e.write(c.arguments[0], windows + b'\0')
                return len(windows)
            e.override(0x546A28, current_dir)
            e.override(0x546A2C, returns(drive))
            e.override(0x546A10, win_dir)
            t['args'] = [string(e, b'captain.sav')]
            return t
        yield make_case(f'startup {current!r} drive {drive} windows {windows!r} {mode}', 0x49B840, setup, 1,
                        initial_stack=((-0x104, bytes([0x6b]) * 0x100),))


    def cached_next(e):
        t = manager(e, (b'First', b'Second', b'Third'))
        journal = e.object(40, 'deletion journal', fill=0)
        def delete(e, c):
            i = e.get(journal)
            e.put(journal + 4 + 12 * i, c.arguments[0], e.get(t['m'] + 4), e.get(t['nodes'][0]))
            e.put(journal, i + 1)
            if c.arguments[0] == t['records'][0]:
                e.put(t['nodes'][0], 0)
            e.release(c.arguments[0])
            return 0
        e.override(0x4F6428, delete)
        return t
    yield make_case('cleanup caches next before original destruction', 0x49B970, cached_next)

    def allocation_reload(e):
        t = manager(e, (b'Existing',))
        name = string(e, b'New name')
        journal = e.object(8, 'allocation publication journal', fill=0)
        def allocator(e, c):
            e.put(journal, e.get(t['m'] + 0xc), e.get(t['m'] + 8))
            e.write(name, b'Existing\0')
            return e.object(c.arguments[0], 'allocation')
        e.override(NEW, allocator)
        t['args'] = [name, 0, 0, 4]
        return t
    yield make_case('create reloads input after allocator mutates name', 0x49BDB0, allocation_reload, 4)

    def selected_reload(e):
        t = reader_setup('selected same', 0x81725)(e)
        state = e.object(8, 'payload allocation and deletion publication', fill=0)
        def allocator(e, c):
            p = e.object(c.arguments[0], 'allocation')
            if c.arguments[0] == PAYLOAD:
                e.put(state, p)
            return p
        def delete(e, c):
            if c.arguments[0] == e.get(state):
                e.put(state + 4, e.get(t['m'] + 0x28))
                e.put(t['m'] + 0x40, 0x7823541)
            e.release(c.arguments[0])
            return 0
        e.override(NEW, allocator)
        e.override(0x4F6428, delete)
        return t
    yield make_case('reader reloads selected after payload release', 0x49B9A0, selected_reload)


def cipher_bytes(env, data, seed):
    """Encode physical file input from the independently inspected original format."""
    random_word = ((seed * 214013 + 2531011) & 0xffffffff) >> 16 & 0x7fff
    state = random_word % 0x1ffffff + 1
    polynomial = env.get(0x52d780 + 24 * 4)
    output = bytearray(data)
    for i in range(len(output)):
        while True:
            state = (state << 1) & 0xffffffff
            if state & 0x2000000:
                state = (state ^ polynomial) | 1
            if state <= 0x1000000:
                break
        output[i] ^= (state - 1) & 255
    return bytes(output)


def reader_setup(mode, seed):
    def setup(e):
        t = manager(e, (b'Player',) if mode == 'duplicate player' else ())
        m = t['m']
        e.put(m + 0x40, 0x91827, seed)
        payload = bytearray()
        for name in ((b'Player', b'Other') if mode in ('equal count', 'clamp count', 'short read') else (b'Player',)):
            record = e.object(SIZE, 'file player template', fill=0x21)
            checksums(e, record)
            e.write(record + 0x14, (b'' if mode == 'invalid player' else name) + b'\0')
            payload += e.read(record + 4, PAYLOAD)
        if mode == 'not multiple':
            payload += b'!'
        header = bytearray(32)
        checksum = 0xffffffff
        for byte in payload:
            checksum ^= e.get(0x52d800 + byte * 4)
        count = 0 if mode == 'zero count' else (1 if mode == 'clamp count' else (9 if mode == 'short records' else len(payload) // PAYLOAD))
        struct.pack_into('<III', header, 4, checksum ^ (1 if mode == 'checksum wrong' else 0),
                         0x91827 if mode == 'selected same' else 0x7654, count)
        file_bytes = cipher_bytes(e, header, seed) + cipher_bytes(e, payload, seed)
        file_data = e.object(len(file_bytes), 'physical save bytes', data=file_bytes)
        cursor = e.object(8, 'file cursor and read index', fill=0)
        e.override(0x546B00, returns(0xffffffff if mode == 'open fails' else 0x1234))
        def seek(e, c):
            _, offset, high, origin = c.arguments
            offset = offset if offset < 0x80000000 else offset - 0x100000000
            size = 32 if mode == 'small' else len(file_bytes)
            position = (0 if origin == 0 else (e.get(cursor) if origin == 1 else size)) + offset
            e.put(cursor, position)
            return position
        e.override(0x546AF4, seek)
        def read(e, c):
            _, target, requested, out_count, _ = c.arguments
            index = e.get(cursor + 4)
            pos = e.get(cursor)
            n = min(requested, len(file_bytes) - pos)
            if mode == 'header zero' and index == 0 or mode == 'payload zero' and index == 1:
                n = 0
            if mode == 'short read':
                n = min(n, 1)
            reported = n
            if n:
                e.write(target, e.read(file_data + pos, n))
            e.put(out_count, reported)
            e.put(cursor, pos + n, index + 1)
            return 1
        e.override(0x546AFC, read)
        if mode == 'allocation fails':
            def allocator(e, c):
                # CString path preparation also allocates; only fail the payload.
                return 0 if c.arguments[0] == len(payload) else e.object(c.arguments[0], 'allocation')
            e.override(NEW, allocator)
        return t
    return setup


# Readability mutation controls extend, rather than replace, the sealed cases.
# The physical imports publish stack-buffer bytes into compared live memory.
_baseline_cases = cases


def cases(random_source):
    yield from _baseline_cases(random_source)

    for current in (b'', b'C:\\Games\\source'):
        def directory_bytes(e, current=current):
            t = manager(e)
            journal = e.object(16, 'directory import byte observations', fill=0)

            def current_directory(e, c):
                e.write(journal, e.read(c.arguments[1], 8))
                if current:
                    e.write(c.arguments[1], current + b'\0')
                return len(current)

            def drive_type(e, c):
                e.write(journal + 8, e.read(c.arguments[0], 8))
                return 3

            e.override(0x546A28, current_directory)
            e.override(0x546A2C, drive_type)
            e.override(0x546A10, returns(0))
            t['args'] = [string(e, b'captain.sav')]
            return t

        yield make_case(f'startup publishes directory bytes {current!r}',
                        0x49B840, directory_bytes, 1,
                        initial_stack=((-0x104, bytes([0x6b]) * 0x100),))

    def equal_neighbor_selection(e):
        t = reader_setup('selected same', 0x81725)(e)
        state = e.object(4, 'payload allocation identity', fill=0)

        def allocator(e, c):
            p = e.object(c.arguments[0], 'allocation')
            if c.arguments[0] == PAYLOAD:
                e.put(state, p)
            return p

        def delete(e, c):
            if c.arguments[0] == e.get(state):
                # Original 0x49bb48 compares +0x40 against +0x28 after release.
                # Its adjacent +0x44 word must not suppress that selection write.
                e.put(t['m'] + 0x40, 0x7823541, e.get(t['m'] + 0x28))
            e.release(c.arguments[0])
            return 0

        e.override(NEW, allocator)
        e.override(0x4F6428, delete)
        return t

    yield make_case('reader selection differs while adjacent word equals header',
                    0x49B9A0, equal_neighbor_selection)
