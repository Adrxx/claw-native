"""Original-input cases for the state dictionary and registration groups."""
from clawparity.cases import Case

NEW = 0x4F63EC
REGISTRY = 0x537668
NAMES = 0x537698
COUNTER = 0x52712C


def error_object(env):
    return env.object(32, 'error-owner', words=[0, 0x19283746, 0x81726354, 4])


def key_bytes(env, key, label='key'):
    # The first insertion tests a bit in the final character (and empty keys
    # read the backed preceding byte), so retain a nonzero guard on both sides.
    storage = env.object(len(key) + 17, label, fill=0xA7)
    env.write(storage + 8, key + b'\0')
    return storage + 8


def bit(key, position):
    return (key[position // 8] >> (position & 7)) & 1 if 0 <= position // 8 < len(key) else 0


def dictionary(env, entries=(), address=None):
    address = address or env.object(48, 'dictionary', fill=0x67)
    env.put(address + 4, error_object(env))
    env.put(address + 0x14, len(entries), 0, 0, 0, 0, 0)
    nodes = []
    root = None
    # Construct an initial Patricia topology as data, outside the run. Each
    # edge is either a greater decision bit or a leaf/back edge.
    for key, value in entries:
        node = {'key': key, 'value': value, 'ptr': env.object(20, 'dictionary-node', fill=0xB3)}
        if root is None:
            node['bit'] = len(key) * 8 - 1
            node['links'] = [None, None]
            node['links'][bit(key, node['bit'])] = node
            root = node
        else:
            parent = None
            found = root
            previous = -1
            while found is not None and found['bit'] > previous:
                previous = found['bit']
                parent = found
                found = found['links'][bit(key, previous)]
            if found is None:
                split = len(key) * 8 - 1
            else:
                split = next(i for i in range(max(len(key), len(found['key'])) * 8 + 8)
                             if bit(key, i) != bit(found['key'], i))
            predecessor = None
            cursor = root
            prior = -1
            while cursor is not None and cursor['bit'] > prior and cursor['bit'] <= split:
                prior = cursor['bit']
                predecessor = cursor
                cursor = cursor['links'][bit(key, prior)]
            node['bit'] = split
            node['links'] = [cursor, cursor]
            node['links'][bit(key, split)] = node
            if predecessor is None:
                root = node
            else:
                predecessor['links'][bit(key, predecessor['bit'])] = node
        nodes.append(node)
    for node in nodes:
        env.put(node['ptr'], *(other['ptr'] if other else 0 for other in node['links']),
                node['bit'], key_bytes(env, node['key'], 'stored-key'), node['value'])
    env.put(address + 0x18, root['ptr'] if root else 0)
    return address, root


def pending(env, address, root, key):
    parent = root
    child = None
    maximum = len(key) * 8 + 7
    if root:
        cursor = root
        previous = -1
        while cursor is not None and cursor['bit'] > previous:
            if maximum < cursor['bit']:
                child = cursor
                break
            parent = cursor
            previous = cursor['bit']
            child = cursor['links'][bit(key, previous)]
            cursor = child
    env.put(address + 0x1C, parent['ptr'] if parent else 0,
            child['ptr'] if child else 0, maximum, 1)


def dictionary_setup(entries, key, pending_lookup=False, fail=0, value=0x91827364, invalid=0):
    def setup(env):
        obj, root = dictionary(env, entries)
        pointer = key_bytes(env, key)
        if pending_lookup:
            pending(env, obj, root, key)
        if fail:
            def allocation(env, call):
                if env.calls_so_far(NEW) == fail:
                    return 0
                return env.object(max(1, call.arguments[0]), 'allocation', fill=0)
            env.override(NEW, allocation)
        return {'object': obj, 'key': 0 if invalid == 1 else pointer,
                'value': 0 if invalid == 2 else value}
    return setup


def array(env, low, high, stride, address=None, existing=True):
    address = address or env.object(40, 'indexed-array', fill=0x53)
    capacity = max(1, high - low + 1) * stride
    data = env.object(capacity, 'indexed-values', data=bytes((i * 37 + 0x59) & 255 for i in range(capacity))) if existing else 0
    fallback = env.object(max(stride, 16), 'fallback', fill=0x39)
    env.put(address + 4, error_object(env), low, high, data, fallback, stride, 0, 0)
    return address


def grow_setup(low, high, stride, index, padding, existing=True):
    def setup(env):
        obj = array(env, low, high, stride, existing=existing)
        return {'object': obj, 'index': index, 'padding': padding}
    return setup


def core_cases(random_source):
    samples = [b'a', b'ab', b'alpha', b'alpine', b'ALPHA', b'omega', b'\x81z']
    values = [(key, 0x10203040 + i * 0x112233) for i, key in enumerate(samples)]
    for key in samples + [b'', b'absent', b'alph', b'zzz', b'\x82z']:
        yield Case('lookup ' + repr(key), 0x4DBA00, dictionary_setup(values, key),
                   receiver=lambda t: t['object'], arguments=(lambda t: t['key'],))
    yield Case('lookup empty tree', 0x4DBA00, dictionary_setup([], b'empty'),
               receiver=lambda t: t['object'], arguments=(lambda t: t['key'],))
    for entries in ([], values[:1], values[:3], values):
        for key in (b'az', b'alphb', b'zzz', b'\x80k', b'longer-key'):
            yield Case('insert %d %r' % (len(entries), key), 0x4DB7F0,
                       dictionary_setup(entries, key, True), receiver=lambda t: t['object'],
                       arguments=(lambda t: t['key'], lambda t: t['value']))
    for fail in (1, 2):
        yield Case('insert allocation failure %d' % fail, 0x4DB7F0,
                   dictionary_setup(values, b'unique', True, fail=fail), receiver=lambda t: t['object'],
                   arguments=(lambda t: t['key'], lambda t: t['value']))
    for invalid in (2,):
        yield Case('insert invalid %d' % invalid, 0x4DB7F0,
                   dictionary_setup(values, b'x', invalid != 0, invalid=invalid),
                   receiver=lambda t: t['object'], arguments=(lambda t: t['key'], lambda t: t['value']))
    for offset in range(4):
        for position in range(8):
            prefix = bytes(random_source.randrange(1, 256) for _ in range(offset))
            a = prefix + b'\x80tail'
            b = prefix + bytes([0x80 ^ (1 << position)]) + b'tail'
            def setup(env, a=a, b=b):
                return (key_bytes(env, a), key_bytes(env, b))
            yield Case('first differing bit %d:%d' % (offset, position), 0x4DC690,
                       setup, arguments=(lambda t: t[0], lambda t: t[1]))
    for low, high in ((0, -1), (3, 5), (-5, -3)):
        for stride in (1, 3, 4, 7):
            for index in (low - 2, high + 2):
                existing = high >= low
                yield Case('grow %d..%d stride%d index%d' % (low, high, stride, index), 0x4DB6E0,
                           grow_setup(low, high, stride, index, 1, existing=existing),
                           receiver=lambda t: t['object'], arguments=(lambda t: t['index'], lambda t: t['padding']))
    for index in (-4, 0, 4):
        yield Case('indexed CString access %d' % index, 0x406020,
                   grow_setup(-1, 1, 4, index, 0), receiver=lambda t: t['object'],
                   arguments=(lambda t: t['index'],))


def services(env):
    receipt = env.object(4096, 'allocation-sizes', fill=0)
    def reallocate(env, call):
        old, size = call.arguments
        old_size = 0
        for offset in range(0, 4096, 8):
            if env.get(receipt + offset) == old and old:
                old_size = env.get(receipt + offset + 4)
                break
        result = env.object(max(1, size), 'reallocation', fill=0xBC)
        if old:
            env.write(result, env.read(old, min(old_size, size)))
            env.release(old)
        for offset in range(0, 4096, 8):
            if not env.get(receipt + offset):
                env.put(receipt + offset, result, size)
                break
        return result
    def length(env, call):
        return len(env.cstr(call.arguments[0]))
    def decrement(env, call):
        address = call.arguments[0]
        value = (env.get(address) - 1) & 0xFFFFFFFF
        env.put(address, value)
        return value
    env.override(0x4A9070, reallocate)
    env.override(0x5469E4, length)
    env.override(0x5469E8, decrement)
    return receipt


GROUPS = (
    (0x4036C0, 0x534820, (b'LS_IDLE',)),
    (0x404420, 0x534850, (b'LS_STARTUP', b'LS_IDLE', b'LS_HIGHPUNCH', b'LS_LOWPUNCH',
                        b'LS_SUPERFRENZY', b'LS_STALACTITEHIT', b'LS_SCARED',
                        b'LS_HITHIGH', b'LS_HITLOW', b'LS_DEADACT1')),
    (0x406640, 0x534888, (b'LS_IDLE', b'LS_DELAY')),
    (0x407010, 0x5348B8, (b'LS_IDLE',)),
    (0x407620, 0x5348E8, (b'ES_IDLE', b'ES_FALLING', b'ES_DEAD', b'ES_WAITING')),
    (0x408690, 0x534910, (b'LS_FALLING',)),
)


def registration_setup(entry, table, keys, mode, start, narrow=False, same_class=False):
    def setup(env):
        receipt = services(env)
        entries = []
        if mode == 'existing':
            entries = [(key, 4 + i * 2) for i, key in enumerate(keys)]
        elif mode == 'mixed':
            entries = [(key, 3 + i * 3) for i, key in enumerate(keys) if i % 2 == 0]
        dictionary(env, entries, REGISTRY)
        env.put(COUNTER, start)
        for address, stride in ((NAMES, 4), (0x534820, 4), (0x534850, 4),
                                (0x534888, 4), (0x5348B8, 4), (0x5348E8, 4),
                                (0x534910, 4), (0x5376C0, 4), (0x5349B8, 4), (0x538428, 4)):
            array(env, 0, 0 if narrow else 63, stride, address)
            data = env.get(address + 0x10)
            # CString nil shared by all empty slots; original assignment owns
            # the allocation and copy. Negative references mean immortal data.
            if address == NAMES:
                nil = env.object(16, 'empty-cstring', words=[0xFFFFFFFF, 0, 0, 0]) + 12
                env.put(0x52E1CC, nil)
                env.put(0x52E1C8, nil - 12)
                for i in range(1 if narrow else 64):
                    if mode == 'mixed':
                        text = ('old-%02d' % i).encode()
                        previous = env.object(len(text) + 13, 'previous-cstring', words=[1, len(text), len(text)], fill=0x65)
                        env.write(previous + 12, text + b'\0')
                        env.put(data + i * 4, previous + 12)
                    else:
                        env.put(data + i * 4, nil)
            for offset in range(0, 4096, 8):
                if not env.get(receipt + offset):
                    env.put(receipt + offset, data, 4 if narrow else 256)
                    break
        # Exercise both strcmp outcomes without changing either game branch.
        if entry == 0x404420:
            env.write(0x523274, b'CA\0')
            env.write(0x523A5C, b'CA\0')
            if same_class:
                env.write(0x52327C, b'CA\0')
        if entry == 0x408690 and same_class:
            env.write(0x523708, b'CA\0')
            env.write(0x523714, b'CA\0')
        return {}
    return setup


def cases(random_source):
    def no_pending_slot(env):
        receipt = services(env)
        tokens = grow_setup(-1, 1, 4, 4, 0)(env)
        env.put(receipt, env.get(tokens['object'] + 16), 12)
        return tokens
    yield Case('CString upper growth with no prior pending region', 0x406020, no_pending_slot,
               receiver=lambda t: t['object'], arguments=(lambda t: t['index'],))
    def dirty_empty_lookup(env):
        services(env)
        tokens = dictionary_setup([], b'empty')(env)
        stale = env.object(20, 'stale-lookup-candidate', fill=0x63)
        env.put(tokens['object'] + 0x1C, stale, stale, 0xAABBCCDD, 0x557799BB)
        return tokens
    yield Case('empty lookup clears prior and candidate metadata', 0x4DBA00, dirty_empty_lookup,
               receiver=lambda t: t['object'], arguments=(lambda t: t['key'],))
    def exact_bound(env):
        services(env)
        return dictionary_setup([(b'az\x80', 0x12345678)], b'az')(env)
    yield Case('query bound equals decision bit', 0x4DBA00, exact_bound,
               receiver=lambda t: t['object'], arguments=(lambda t: t['key'],))
    for stride in (1, 3, 7):
        for index in (-3, 0, 3):
            original_setup = grow_setup(-3, 3, stride, index, 3-index)
            def setup(env, original_setup=original_setup, size=7*stride):
                receipt = services(env)
                tokens = original_setup(env)
                env.put(receipt, env.get(tokens['object'] + 16), size)
                return tokens
            yield Case('grow existing interval stride%d key%d' % (stride, index), 0x4DB6E0, setup,
                       receiver=lambda t: t['object'],
                       arguments=(lambda t: t['index'], lambda t: t['padding']))
    for case in core_cases(random_source):
        original_setup = case.setup
        def setup(env, original_setup=original_setup, function=case.function):
            receipt = services(env)
            tokens = original_setup(env)
            if 'object' in tokens and function in (0x4DB6E0, 0x406020):
                data = env.get(tokens['object'] + 0x10)
                if data:
                    low = env.get(tokens['object'] + 8)
                    high = env.get(tokens['object'] + 12)
                    size = ((high - low + 1) & 0xFFFFFFFF) * env.get(tokens['object'] + 24)
                    env.put(receipt, data, size)
            return tokens
        # Keep fixture setup outside the input-case definitions.
        yield Case(case.label, case.function, setup, receiver=case.receiver, arguments=case.arguments)
    for trial in range(16):
        low = random_source.randrange(-30, 31)
        high = low + random_source.randrange(1, 8)
        stride = random_source.randrange(1, 14)
        padding = random_source.randrange(0, 5)
        index = low - random_source.randrange(1, 8) if trial % 2 else high + random_source.randrange(1, 8)
        original_setup = grow_setup(low, high, stride, index, padding)
        def setup(env, original_setup=original_setup, size=(high-low+1)*stride):
            receipt = services(env)
            tokens = original_setup(env)
            env.put(receipt, env.get(tokens['object'] + 16), size)
            return tokens
        yield Case('random signed growth %d' % trial, 0x4DB6E0, setup, receiver=lambda t: t['object'],
                   arguments=(lambda t: t['index'], lambda t: t['padding']))
    for entry, table, keys in GROUPS:
        for mode in ('fresh', 'existing', 'mixed'):
            for start in (1, 31):
                for narrow in (False, True):
                    for same_class in (False, True):
                        yield Case('registration %x %s %d narrow%s same%s' % (entry, mode, start, narrow, same_class), entry,
                                   registration_setup(entry, table, keys, mode, start, narrow, same_class))
