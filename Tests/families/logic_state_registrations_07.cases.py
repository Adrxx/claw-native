"""Independent original-registration cases; callback bodies are never invoked."""
from clawparity.cases import Case

ENTRIES = (
    0x488B00, 0x489210, 0x489960, 0x48B1D0, 0x48E6E0, 0x4924F0,
    0x4940E0, 0x497240, 0x4982E0, 0x49F2E0, 0x4A0340,
)
ARRAYS = (
    0x5349B8, 0x537638, 0x537698, 0x537878, 0x53C2A0, 0x53C2C8,
    0x53C2F8, 0x53C328, 0x53C9D0, 0x53CA08, 0x53CA40, 0x53CA70,
    0x53CAA0, 0x53EC00, 0x53EC68,
)
NAMES = (
    0x523148, 0x523204, 0x523210, 0x52323C, 0x523268, 0x5234EC,
    0x5234F4, 0x5235F0, 0x5235F8, 0x523604, 0x5236FC, 0x5240E8,
    0x524418, 0x524548, 0x526A38, 0x527170, 0x52717C, 0x527188,
    0x527198, 0x5271A8, 0x5271B4, 0x5271C0, 0x5271CC, 0x5271D8,
    0x5271E4, 0x5271F4, 0x527204, 0x52720C, 0x52726C, 0x527278,
    0x527D60, 0x527D78, 0x527D84, 0x527D94, 0x527DA0, 0x527DAC,
    0x529A48, 0x52B3A4, 0x52C024, 0x52C030, 0x52C8D8, 0x52C8E4,
    0x52C8F4, 0x52CA78, 0x52CA88, 0x52CA98, 0x52D464, 0x52DDBC,
    0x52E0A4, 0x52E0B4, 0x52E0C4, 0x52E0D4, 0x52E0E0,
)
# Compared class-name strings read by the original wrappers.
PARENTS = {
    0x489960: (0x523A5C, 0x52C03C), 0x48B1D0: (0x523A5C, 0x52C47C),
    0x4924F0: (0x52670C, 0x52C900), 0x4940E0: (0x523A5C, 0x52CAA4),
    0x497240: (0x523A5C, 0x52D470), 0x4A0340: (0x523274, 0x52E0EC),
}


def setup_registry(entry, words, selected=(), bounds=(-2, 128), next_id=100,
                   compare=None, string_kind=0, stride=4, late_counter=False):
    def setup(env):
        empty_header = env.object(16, 'empty CString header', words=[0xFFFFFFFF, 0, 0, 0])
        empty = empty_header + 12
        env.put(0x52E1C8, empty_header, empty)
        handler = env.object(24, 'silent error policy', words=[0, 0, 0x13572468, 4, 0, 0])
        env.put(0x544D18, 0)
        env.put(0x52712C, next_id)
        env.put(0x537668, 0xF00D1122, handler, 0x91827364, 0x17263549,
                0xA1B2C3D4, 0, 0, 0, 0, 0, 0, 0xC0FFEE11)
        low, high = bounds
        for ai, address in enumerate(ARRAYS):
            width = 4 if address == 0x537698 else stride
            count = high - low + 1
            data = env.object(count * width, f'array {address:x}', fill=0xB7)
            fallback = env.object(width, f'fallback {address:x}', fill=0xD9)
            for index in range(count):
                if address == 0x537698:
                    if string_kind:
                        capacity = 32 if string_kind == 1 else 1
                        header = env.object(12 + capacity + 1, f'old CString {index}', fill=0x65)
                        env.put(header, 2 if string_kind == 3 else 1, 1, capacity)
                        env.write(header + 12, b'q\0')
                        env.put(data + index * width, header + 12)
                    else:
                        env.put(data + index * width, empty)
                else:
                    env.put(data + index * width, words[(ai + index) % len(words)])
            env.put(fallback, empty if address == 0x537698 else words[ai % len(words)])
            env.put(address, 0xA0B00000 + ai, handler, low, high, data, fallback,
                    width, data + 4, 0xCCDD0000 + ai, 0x33445566, 0x778899AA, 0xBACDFE01)

        # A read-only Patricia tree with explicit terminal back edges. Internal
        # routing nodes have increasing bit positions; terminal nodes use -1.
        pairs = []
        for address, ident in selected:
            key = env.cstr(address)
            if isinstance(key, str):
                key = key.encode('latin1')
            pairs.append((key + b'\0', address, ident))

        def bit(key, position):
            return (key[position // 8] >> (position % 8)) & 1 if position // 8 < len(key) else 0

        def tree(items, start=0):
            node = env.object(20, 'name trie node', fill=0x93)
            key, name, ident = items[0]
            if len(items) == 1:
                env.put(node, node, node, 0xFFFFFFFF, name, ident)
                return node
            position = start
            while len({bit(item[0], position) for item in items}) == 1:
                position += 1
            left = tree([item for item in items if not bit(item[0], position)], position + 1)
            right = tree([item for item in items if bit(item[0], position)], position + 1)
            env.put(node, left, right, position, name, ident)
            return node

        if pairs:
            root = tree(pairs)
            # A singleton root needs a nonnegative routing bit on its first visit.
            if len(pairs) == 1:
                env.put(root + 8, 0)
            env.put(0x53767C, len(pairs), root)
        if compare is not None and entry in PARENTS:
            a, b = PARENTS[entry]
            first, second = compare
            env.write(a, first + b'\0')
            env.write(b, second + b'\0')

        observations = env.object(16384, 'realloc and CString observations')
        def reallocate(env, call):
            old, size = call.arguments
            owner = next(address for address in ARRAYS if env.get(address + 16) == old)
            old_low = env.get(owner + 8)
            old_high = env.get(owner + 12)
            old_low = old_low - 0x100000000 if old_low & 0x80000000 else old_low
            old_high = old_high - 0x100000000 if old_high & 0x80000000 else old_high
            old_size = (old_high - old_low + 1) * env.get(owner + 24)
            index = env.calls_so_far(0x4A9070) - 1
            env.put(observations + index * 32, owner, old, size, env.get(0x52712C),
                    env.get(owner + 8), env.get(owner + 12), env.get(owner + 28), env.get(owner + 32))
            new = env.object(size, 'resized array', fill=0xA5)
            env.write(new, env.read(old, min(size, old_size)))
            env.release(old)
            return new

        def length(env, call):
            # Record the string and registration state before CString assignment.
            index = env.calls_so_far(0x5469E4) - 1
            env.put(observations + 8192 + index * 16, call.arguments[0], env.get(0x52712C),
                    env.get(0x5376B4), env.get(0x5376B8))
            if late_counter and index == 0:
                env.put(0x52712C, env.get(0x52712C) + 2)
            return len(env.cstr(call.arguments[0]))

        def decrement(env, call):
            address = call.arguments[0]
            value = (env.get(address) - 1) & 0xFFFFFFFF
            env.put(address, value)
            return value

        env.override(0x4A9070, reallocate)
        env.override(0x5469E4, length)
        env.override(0x5469E8, decrement)
        return {'observations': observations}
    return setup


def cases(random_source):
    words = tuple(random_source.getrandbits(32) | 1 for _ in range(53))
    identifiers = random_source.sample(range(1, 94), len(NAMES))
    all_names = tuple(zip(NAMES, identifiers))
    partial = tuple(item for index, item in enumerate(all_names) if index % 2)
    for entry in ENTRIES:
        for label, selected, bounds, counter in (
            ('new in range', (), (-2, 128), 100),
            ('new growing upward', (), (0, 0), 7),
            ('new growing downward', (), (120, 123), 3),
            ('existing nonsequential ids', all_names, (-2, 128), 100),
            ('mixed existing and new', partial, (-2, 128), 100),
            ('existing ids below handlers', all_names, (120, 123), 100),
            ('existing ids above handlers', all_names, (0, 0), 100),
        ):
            yield Case(f'{entry:x} {label}', entry,
                       setup_registry(entry, words, selected, bounds, counter))
        for kind in (1, 2, 3):
            yield Case(f'{entry:x} CString kind {kind}', entry,
                       setup_registry(entry, words, bounds=(-2, 128), string_kind=kind))
        yield Case(f'{entry:x} wide callback slots', entry,
                   setup_registry(entry, words, all_names, stride=12))
        yield Case(f'{entry:x} counter re-read after CString service', entry,
                   setup_registry(entry, words, late_counter=True))
        if entry in PARENTS:
            for label, compared in (
                ('equal empty', (b'', b'')), ('equal odd', (b'abc', b'abc')),
                ('equal even', (b'abcd', b'abcd')),
                ('even byte greater', (b'Zbc', b'Abc')),
                ('odd byte greater', (b'aZ', b'aA')),
                ('odd zero prefix', (b'a', b'ab')),
                ('unsigned even byte', (b'\x81b', b'\x7fb')),
            ):
                yield Case(f'{entry:x} parent compare {label}', entry,
                           setup_registry(entry, words,
                                          () if label in ('equal empty', 'equal odd') else all_names,
                                          (0, 0) if label == 'equal odd' else (-2, 128),
                                          compare=compared))
