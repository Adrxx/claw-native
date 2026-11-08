"""Independent original-backed startup, checkpoint, camera and message cases."""
import struct

from clawparity.cases import Case


def words(env, size, name, seed):
    return env.object(size, name, data=bytes(((seed + i * 37) % 255) + 1 for i in range(size)))


def cache_setup(env, seed=31):
    cache = words(env, 0x21C4, 'checkpoint cache', seed)
    return cache


def record(cache, level, kind):
    return cache + {1: 0x2D4, 2: 0xD24, 3: 0x1774}[kind] + level * 0xB0


def strings(env):
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))

    def decrement(e, c):
        address = c.arguments[0]
        value = (e.get(address) - 1) & 0xFFFFFFFF
        e.put(address, value)
        return value

    env.override(0x5469E8, decrement)


def message_setup(text, count=0, alias=False, refs=1, free_node=False, mutate=False):
    def setup(env):
        strings(env)
        target = env.object(0x1C, 'message list', fill=0)
        env.put(target + 0x18, 3)
        nodes = []
        texts = []
        if count > 0:
            block = env.object(4 + 12 * count, 'existing list block', fill=0)
            env.put(target + 0x14, block)
            for index in range(count):
                payload = (f'old-{index}-distinct-' + 'x' * (index + 1)).encode()
                storage = env.object(12 + len(payload) + 1, f'CString {index}')
                env.put(storage, refs, len(payload), len(payload))
                env.write(storage + 12, payload + b'\0')
                nodes.append(block + 4 + index * 12)
                texts.append(storage + 12)
            for index, node in enumerate(nodes):
                env.put(node, nodes[index + 1] if index + 1 < count else 0,
                        nodes[index - 1] if index else 0, texts[index])
            env.put(target + 4, nodes[0], nodes[-1], count)
        if count < 0:
            env.put(target + 0xC, count & 0xFFFFFFFF)
        if free_node:
            block = env.object(16, 'free-node block', fill=0)
            env.put(block, env.get(target + 0x14))
            env.put(target + 0x14, block)
            env.put(target + 0x10, block + 4)
        pointer = 0 if text is None else env.object(len(text) + 1, 'new message', data=text + b'\0')
        if alias:
            pointer = texts[-1]
        wrapper = words(env, 0x58, 'message wrapper', 43)
        env.put(wrapper + 0x4C, target)
        if mutate:
            def length_and_change(e, c):
                length = len(e.cstr(c.arguments[0]))
                e.put(target + 0xC, 13)
                return length
            env.override(0x5469E4, length_and_change)
        return {'list': target, 'text': pointer, 'wrapper': wrapper}
    return setup


def restore_setup(seed, level=2, kind=1, pending=1, cache_present=True,
                  available=2, xy=(0, 0), score=1999999, count=3,
                  excluded=1, primary_flags=0, alias_camera=False):
    def setup(env):
        cache = cache_setup(env, seed)
        player = words(env, 0x258, 'player', seed + 5)
        application = words(env, 0xE0, 'application', seed + 7)
        link = words(env, 0x30, 'world link', seed + 9)
        collection = words(env, 0x68, 'camera collection', seed + 11)
        env.put(player + 4, application)
        env.put(player + 0xC, link)
        env.put(player + 0x14, level & 0xFFFFFFFF)
        env.put(application + 0x64, cache if cache_present else 0)
        env.put(application + 0xA8, pending)
        env.put(application + 0xD8, kind & 0xFFFFFFFF)
        env.put(link + 0x24, collection)
        lookup_level, lookup_kind = (level - 1, 3) if kind == 0 else (level, kind)
        if 0 <= lookup_level < 15 and lookup_kind in (1, 2, 3):
            saved = record(cache, lookup_level, lookup_kind)
            env.put(saved, available, xy[0] & 0xFFFFFFFF, xy[1] & 0xFFFFFFFF)
            env.put(saved + 0x10, score & 0xFFFFFFFF, (seed * 1001) & 0xFFFFFFFF)
        cameras = []
        for index in range(max(0, count) + 1):
            camera = words(env, 0x90, f'camera {index}', seed + 17 + index)
            env.put(camera + 8, primary_flags if index == 0 else (index % 2))
            env.write(camera + 0x18, struct.pack('<ff', -0.75 if index == 2 else 0.625, 1.375))
            env.put(camera + 0x30, 701 + index * 53, 503 + index * 41)
            env.put(camera + 0x70, 111, 97, 43, 29)
            cameras.append(camera)
        if alias_camera and count > 0:
            cameras[1] = cameras[0]
        array = env.object(max(4, max(0, count) * 4), 'camera pointers')
        for index in range(max(0, count)):
            env.put(array + index * 4, cameras[index + 1])
        env.put(collection + 0x38, array, count & 0xFFFFFFFF)
        env.put(collection + 0x5C, cameras[0], excluded & 0xFFFFFFFF)
        return {'player': player}
    return setup


def cases(random_source):
    for extra in (0, 1, 0x80000000, random_source.getrandbits(32)):
        marker = random_source.getrandbits(32)
        def setup(env, extra=extra, marker=marker):
            env.write(0x534C7C, bytes(((i * 19 + 7) % 255) + 1 for i in range(0x144)))
            env.put(0x53725C, extra)
            env.put(0x52C6E4, marker)
        yield Case(f'global reset mode {extra}', 0x415CE0, setup)
    for seed in (11, 93, random_source.randrange(1, 250)):
        yield Case(f'clear exactly sixty fields {seed}', 0x46C790,
                   lambda e, seed=seed: words(e, 0x258, 'saved fields with guards', seed), receiver=lambda t: t)
    for results in ((0x75391,), (0, 0x94825), (0, 0)):
        def setup(env, results=results):
            target = words(env, 0x40, 'message display', 29)
            observations = env.object(2 * 22 * 4, 'font callback observations', fill=0)

            def font(e, call):
                index = e.calls_so_far(0x546918) - 1
                state = [e.get(target + offset) for offset in range(0x20, 0x38, 4)]
                e.put(observations + index * 22 * 4, index + 1, call.receiver,
                      *call.arguments, *state)
                return results[index]

            env.override(0x546918, font)
            return target
        yield Case(f'font result {results}', 0x4222A0, setup, receiver=lambda t: t,
                   arguments=(random_source.getrandbits(32), random_source.getrandbits(32)))
    for function in (0x49AF30, 0x49AF90):
        for level in (-2147483648, -1, 0, 1, 2, 14, 15, 16, 2147483647):
            for kind in (-1, 0, 1, 2, 3, 4):
                flags = random_source.choice((0, 1, 2, 3, 0xFFFFFFFD, 0xFFFFFFFF))
                seed = random_source.randrange(1, 255)
                def setup(env, flags=flags, seed=seed):
                    cache = cache_setup(env, seed)
                    for k in (1, 2, 3):
                        for l in range(15):
                            env.put(record(cache, l, k), flags)
                    return cache
                yield Case(f'lookup {function:x} level {level} kind {kind} flags {flags}', function, setup,
                           receiver=lambda t: t, arguments=(level & 0xFFFFFFFF, kind & 0xFFFFFFFF))
    for count in (-1, 0, 1, 7, 8):
        for flags in (0, 1, 2, 3, 4, 5, 6, 7, 0xFFFFFF00, 0xFFFFFF07):
            yield Case(f'queue count {count} flags {flags}', 0x422370,
                       message_setup(b'unique status message', count), receiver=lambda t: t['list'],
                       arguments=(lambda t: t['text'], flags))
    for text in (None, b''):
        for flags in (0, 7):
            yield Case(f'queue reject {text} flags {flags}', 0x422370, message_setup(text, 2),
                       receiver=lambda t: t['list'], arguments=(lambda t: t['text'], flags))
    for alias, refs, free_node, mutate in ((True, 1, False, False), (False, 2, False, False),
                                          (False, 1, True, False), (False, 1, False, True)):
        for flags in (0, 2, 4, 6):
            if alias and flags & 4:
                continue  # A cleared string cannot remain the valid text argument.
            yield Case(f'queue storage alias{alias} shared{refs} free{free_node} mutate{mutate} flags{flags}',
                       0x422370, message_setup(b'longer replacement than old strings' * 3, 2, alias, refs, free_node, mutate),
                       receiver=lambda t: t['list'], arguments=(lambda t: t['text'], flags))
    yield Case('replace without list', 0x42AF70,
               lambda e: e.object(0x50, 'null-list receiver', fill=0), receiver=lambda t: t, arguments=(0,))
    for text in (None, b'', b'replacement'):
        yield Case(f'replace existing messages {text}', 0x42AF70, message_setup(text, 3),
                   receiver=lambda t: t['wrapper'], arguments=(lambda t: t['text'],))
    configurations = [dict(pending=0), dict(cache_present=False), dict(level=0), dict(level=-1),
                      dict(available=0), dict(kind=3), dict(kind=4), dict(level=15, kind=0),
                      dict(level=1, kind=0), dict(kind=2), dict(kind=0)]
    for xy in ((0, 19), (23, 0), (-1, 17), (13, -1), (-7, -9), (1, 1),
               (678, 488), (4001, 3001), (16777217, 16777219)):
        for score in (0, 999999, 1000000, -1, -1000001, 2147483647, -2147483648):
            configurations.append(dict(xy=xy, score=score))
    for count in (-1, 0, 1, 3):
        for flags in (0, 1, 12, 13):
            configurations.append(dict(xy=(1793, 1409), count=count, primary_flags=flags, excluded=-1))
    configurations.extend((dict(xy=(100, 200), excluded=0),
                           dict(xy=(400, 500), alias_camera=True, excluded=2)))
    for index, options in enumerate(configurations):
        yield Case(f'restore {index} {options}', 0x46D8E0,
                   restore_setup(random_source.randrange(1, 255), **options), receiver=lambda t: t['player'])
