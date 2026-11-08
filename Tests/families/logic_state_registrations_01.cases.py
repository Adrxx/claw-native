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


def array(env, low, high, stride, address=None, existing=True):
    address = address or env.object(40, 'indexed-array', fill=0x53)
    capacity = max(1, high - low + 1) * stride
    data = env.object(capacity, 'indexed-values', data=bytes((i * 37 + 0x59) & 255 for i in range(capacity))) if existing else 0
    fallback = env.object(max(stride, 16), 'fallback', fill=0x39)
    env.put(address + 4, error_object(env), low, high, data, fallback, stride, 0, 0)
    return address


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


# Physical registration entry, target table, state names, comparison strings.
GROUPS = (
    (0x4092D0, 0x534948, (b'ES_IDLE',), None),
    (0x40A150, 0x534978, (b'LS_IDLE', b'LS_HOME', b'LS_STARTHUG', b'LS_HUG', b'LS_RELEASE'), (0x523A5C, 0x523A68)),
    (0x40E390, 0x5349B8, (b'LS_STARTUP',), (0x523A5C, 0x523274)),
    (0x40ED00, 0x5349E0, (b'LS_BOUNCE', b'LS_FALLING', b'LS_DEAD'), None),
    (0x40FC50, 0x534A10, (b'LS_IDLE',), None),
    (0x410B90, 0x534AB0, (b'LS_FALLING',), (0x52419C, 0x5241A4)),
    (0x411140, 0x534BA0, (b'LS_FALLING',), (0x52419C, 0x524200)),
    (0x4115F0, 0x534A38, (b'LS_FALLING',), (0x52419C, 0x524264)),
    (0x411AA0, 0x534B00, (b'LS_FALLING',), (0x52419C, 0x5242C0)),
    (0x411F80, 0x534AD8, (b'LS_FALLING',), (0x52419C, 0x524308)),
    (0x412570, 0x534B28, (b'LS_FALLING',), (0x52419C, 0x524354)),
)


def registration_setup(group, mode, start, geometry, comparison, salt):
    entry, target, keys, compared = group

    def setup(env):
        receipt = services(env)
        entries = [(b'unrelated-alpha', 51), (b'unrelated-omega', 57)]
        if mode == 'existing':
            entries += [(key, 5 + i * 3) for i, key in enumerate(keys)]
        elif mode == 'mixed':
            entries += [(key, 7 + i * 3) for i, key in enumerate(keys) if i % 2 == 0]
        dictionary(env, entries, REGISTRY)
        env.put(COUNTER, start)
        nil = env.object(16, 'empty-cstring', words=[0xFFFFFFFF, 0, 0, 0]) + 12
        env.put(0x52E1CC, nil)
        env.put(0x52E1C8, nil - 12)
        # Lower growth, upper growth, and an already sufficient interval.
        bounds = {'wide': (0, 63), 'upper': (0, 0), 'lower': (40, 43)}
        for address in (NAMES, target, 0x537638, 0x537878, 0x538428):
            low, high = bounds[geometry]
            array(env, low, high, 4, address)
            data = env.get(address + 16)
            count = high - low + 1
            env.put(address + 0x1C, data, 1)  # stale pending region must be cleared
            if address == NAMES:
                for i in range(count):
                    # Existing strings force release/copy behavior; references
                    # and capacities differ so accidental slot reuse is visible.
                    text = ('prior-%08x-%02d' % (salt, i)).encode()
                    old = env.object(len(text) + 13, 'previous-cstring',
                                     words=[1, len(text), len(text)], fill=0x6D)
                    env.write(old + 12, text + b'\0')
                    env.put(data + i * 4, old + 12)
            else:
                env.write(data, bytes((salt + i * 47) & 255 for i in range(count * 4)))
            for offset in range(0, 4096, 8):
                if not env.get(receipt + offset):
                    env.put(receipt + offset, data, count * 4)
                    break
        # Stop CHumanEnemy's further ancestor at its real comparison branch.
        if comparison != 'original':
            env.write(0x52670C, b'CA\0')
            env.write(0x523A5C, b'CA\0')
        if compared and comparison != 'original':
            left, right = compared
            pairs = {
                'same-even': (b'CA', b'CA'),
                'same-odd': (b'CAT', b'CAT'),
                'first-less': (b'A', b'Z'),
                'second-greater': (b'CZ', b'CA'),
                'late-less': (b'CAAA', b'CAAZ'),
            }
            a, b = pairs[comparison]
            # The bullet base string has eight physical bytes before its
            # neighbour. All chosen inputs fit without aliasing that neighbour.
            env.write(left, a + b'\0')
            env.write(right, b + b'\0')
            if entry in (0x40A150, 0x40E390):
                env.write(0x52670C, a + b'\0')
        return {}
    return setup


def cases(random_source):
    for group in GROUPS:
        for mode in ('fresh', 'existing', 'mixed'):
            for geometry in ('wide', 'upper', 'lower'):
                for comparison in ('same-even', 'first-less') if group[3] else ('same-even',):
                    salt = random_source.getrandbits(32)
                    start = random_source.randrange(19, 30)
                    yield Case('register %x %s %s %s' % (group[0], mode, geometry, comparison),
                               group[0], registration_setup(group, mode, start, geometry, comparison, salt))
        if group[3]:
            for comparison in ('same-odd', 'second-greater', 'late-less', 'original'):
                yield Case('class comparison %x %s' % (group[0], comparison), group[0],
                           registration_setup(group, 'fresh', random_source.randrange(19, 30),
                                              'upper', comparison, random_source.getrandbits(32)))
