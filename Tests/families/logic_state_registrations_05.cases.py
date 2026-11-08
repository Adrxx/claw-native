"""State registration inputs constructed from the original registry layouts."""
from clawparity.cases import Case
from clawparity.fixtures import halt

TRIE = 0x537668
STRINGS = 0x537698
NEXT = 0x52712C
ENTRIES = (
    (0x457860, 0x537A90, ('ES_IDLE', 'ES_FALLING'), None),
    (0x4583A0, 0x537AC0, ('LS_IDLE',), None),
    (0x4588B0, 0x537AF0, ('LS_STARTUP', 'LS_HOME', 'LS_WAITFORPARROT', 'LS_IDLE', 'LS_JUMPOVER', 'LS_HITHIGH', 'LS_HITLOW', 'LS_FIRING'), (0x523274, 0x52876C)),
    (0x45A520, 0x537B20, ('ES_IDLE', 'ES_CLOSING', 'ES_OPENING'), None),
    (0x460820, 0x537B68, ('LS_IDLE', 'LS_HOME', 'LS_FIRING', 'LS_BLOCK'), (0x523A5C, 0x5294D4)),
    (0x462C00, 0x537BA0, ('LS_HOME', 'LS_IDLE'), (0x523A5C, 0x529864)),
    (0x463C50, 0x537BD0, ('LS_HOME', 'LS_IDLE', 'LS_DEAD', 'LS_WAIT', 'LS_MAGICATTACK', 'LS_MOVETOPOSITION'), (0x523274, 0x529A50)),
    (0x4652C0, 0x537C00, ('LS_IDLE',), None),
    (0x465EC0, 0x537C30, ('LS_IDLE', 'LS_FLYABOUT', 'LS_STRIKESETUP', 'LS_STRIKE', 'LS_FLYTOIDLE', 'LS_FLYTOMARROW', 'LS_CARRYMARROW', 'LS_GENERICHIT', 'LS_DEAD'), (0x52670C, 0x529C14)),
    (0x468BE0, 0x537C60, ('LS_HOME', 'LS_ROLLFORWARD', 'LS_ROLLBACKWARD', 'LS_FIRING'), (0x523A5C, 0x529C8C)),
    (0x46F7B0, 0x537EA0, ('LS_EXPLODING', 'LS_THROWN', 'LS_DROPPED'), (0x52670C, 0x52A184)),
)
ARRAYS = (0x5349B8, 0x537638, 0x537878) + tuple(x[1] for x in ENTRIES)
PARENT_NAMES = ('LS_STARTUP', 'LS_FALLING', 'LS_STRIKE', 'LS_DEAD', 'LS_JUMP', 'LS_MOVINGLEFT', 'LS_MOVINGRIGHT', 'LS_IDLE', 'LS_HOME', 'LS_FIRING', 'LS_HITHIGH', 'LS_HITLOW')


def trie(env, bindings):
    """Build ascending-bit Patricia nodes, including genuine self links."""
    root = 0
    nodes = {}

    def bit(key, index):
        return ((key[index // 8] if index // 8 < len(key) else 0) >> (index % 8)) & 1

    for text, value in bindings:
        key = text.encode() + b'\0'
        parent = 0
        leaf = root
        if root:
            while True:
                parent = leaf
                leaf = nodes[parent][bit(key, nodes[parent][2])]
                if not leaf or nodes[leaf][2] <= nodes[parent][2]:
                    break
        if leaf:
            other = nodes[leaf][5]
            different = next(i for i in range(max(len(key), len(other)) * 8) if bit(key, i) != bit(other, i))
        else:
            different = len(text) * 8 - 1
        new = env.object(20, 'name-node')
        name = env.object(len(key), 'name-key', data=key)
        record = [0, 0, different, name, value, key]
        nodes[new] = record
        record[bit(key, different)] = new
        previous = 0
        current = root
        if root and nodes[root][2] <= different:
            while True:
                previous = current
                current = nodes[current][bit(key, nodes[current][2])]
                if not current or nodes[current][2] <= nodes[previous][2] or nodes[current][2] > different:
                    break
        record[1 - bit(key, different)] = current
        if previous:
            nodes[previous][bit(key, nodes[previous][2])] = new
        else:
            root = new
    for address, record in nodes.items():
        env.put(address, *record[:5])
    env.put(TRIE + 0x14, len(nodes), root, 0, 0, 0, 0)


def setup_case(entry, seed_words, mode, comparison='equal', halt_at=None, mutate=False):
    function, target, names, superclass = entry

    def setup(env):
        empty = env.object(13, 'empty-string', words=[0xFFFFFFFF, 0, 0])
        env.put(0x52E1C8, empty, empty + 12)
        # CRT small-block sentinel forces ordinary physical HeapReAlloc.
        env.put(0x52F2B0, 0x52F2B0)
        env.put(0x52F2C0, 0, 0)
        env.put(0x540FE8, 0)
        env.put(TRIE, *([0] * 12))
        next_id = -27 if mode == 'negative' else 13
        env.put(NEXT, next_id & 0xFFFFFFFF)
        bindings = []
        if mode in ('hit', 'mixed', 'endpoints', 'negative-hit'):
            selected = names if mode != 'mixed' else names[::2]
            bindings = [(name, ((-11 + 2 * i) if mode == 'negative-hit' else ((96 - 15 * i) if mode == 'endpoints' else (4 + 3 * i)))) for i, name in enumerate(selected)]
        if comparison == 'natural':
            for name in PARENT_NAMES:
                if name not in [x[0] for x in bindings] and mode in ('hit', 'endpoints'):
                    bindings.append((name, 40 + len(bindings)))
        trie(env, [(name, value & 0xFFFFFFFF) for name, value in bindings])
        sizes = {}
        for index, address in enumerate((STRINGS,) + ARRAYS):
            low, high = (-32, 96)
            if mode in ('grow-up', 'grow-down', 'negative'):
                low, high = ((0, 1) if mode != 'grow-down' else (48, 49))
            if mode == 'grow-last':
                low, high = (0, next_id + len(names) - 2)
            if mode == 'negative-hit':
                low, high = (0, 2)
            stride = 4 if address == STRINGS else (4, 8, 12)[index % 3]
            count = high - low + 1
            words = [seed_words[(i + index) % len(seed_words)] for i in range(count * stride // 4)]
            storage = env.object(count * stride, f'cells-{address:x}', words=words)
            sizes[storage] = count * stride
            if address == STRINGS:
                for i in range(count):
                    payload = env.object(141, f'old-string-{i}', words=[1, 3, 128])
                    env.write(payload + 12, bytes((65 + i % 25, 65 + index % 25, 90, 0)))
                    env.put(storage + i * stride, payload + 12)
            fallback = env.object(4, 'fallback', words=[seed_words[index % len(seed_words)]])
            env.put(address, seed_words[index % len(seed_words)], 0, low & 0xFFFFFFFF, high & 0xFFFFFFFF, storage, fallback, stride, storage, 0xA0 + index, seed_words[(index + 1) % len(seed_words)], 0)
        if superclass and comparison != 'natural':
            left, right = superclass
            patterns = {
                'equal': (b'abcd\0', b'abcd\0'),
                'even-zero': (b'ab\0', b'ab\0'),
                'odd-zero': (b'a\0', b'a\0'),
                'first-less': (b'A\0', b'Z\0'),
                'first-greater': (b'Z\0', b'A\0'),
                'second-less': (b'aA\0', b'aZ\0'),
                'second-greater': (b'aZ\0', b'aA\0'),
            }
            lhs, rhs = patterns[comparison]
            env.write(left, lhs)
            env.write(right, rhs)
        log = env.object(1024, 'physical-observations')

        def length(env, call):
            n = env.calls_so_far(0x5469E4)
            env.put(log + (n % 32) * 16, call.receiver, call.arguments[0], env.get(NEXT), env.get(target + 0x20))
            if mutate and n == 1:
                env.put(NEXT, env.get(NEXT) + 2)
            return len(env.cstr(call.arguments[0]))

        def reallocate(env, call):
            old, size = call.arguments[2:4]
            fresh = env.object(size, 'reallocated-cells')
            env.write(fresh, env.read(old, min(size, sizes[old])))
            sizes[fresh] = size
            env.release(old)
            return fresh

        env.override(0x5469E4, length)
        env.override(0x546928, reallocate)
        env.override(0x546960, lambda env, call: env.object(call.arguments[2], 'heap-cells'))
        if halt_at:
            env.override(halt_at, halt())
        return {}
    return setup


def cases(random_source):
    for entry in ENTRIES:
        words = tuple(random_source.randrange(1, 0xFFFFFFFF) for _ in range(29))
        modes = ('empty', 'hit', 'mixed', 'endpoints', 'grow-up', 'grow-down', 'grow-last', 'negative', 'negative-hit')
        for mode in modes:
            yield Case(f'{entry[0]:x} {mode}', entry[0], setup_case(entry, words, mode))
        yield Case(f'{entry[0]:x} publication rereads next id', entry[0], setup_case(entry, words, 'empty', mutate=True))
        for fixture in (0x4F63EC, 0x5469E4, 0x546928):
            yield Case(f'{entry[0]:x} physical halt {fixture:x}', entry[0], setup_case(entry, words, 'grow-up', halt_at=fixture), expect='halt')
        if entry[3]:
            for comparison in ('natural', 'even-zero', 'odd-zero', 'first-less', 'first-greater', 'second-less', 'second-greater'):
                yield Case(f'{entry[0]:x} superclass {comparison}', entry[0], setup_case(entry, words, 'empty', comparison))
