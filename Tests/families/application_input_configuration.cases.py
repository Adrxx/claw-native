"""Blind original-input cases; fixtures represent only physical Windows APIs."""
from clawparity.cases import Case

METRICS, CURSOR, KEY, WARP = 0x546c44, 0x546cd0, 0x546ce4, 0x546d9c
POSITION, CAPS, COUNT = 0x546de8, 0x546df4, 0x546df8
SOURCE_BITS = (0x10000000, 0x20000000, 0x40000000, 0x80000000) + tuple(1 << i for i in range(9))
BIND_BITS = (0x1000000, 0x2000000, 0x4000000, 0x8000000, 1, 2, 4, 8, 0x20, 0x40, 0x80, 0x100, 0x200)


def scene(mode=0, held=None, latch=0, extended=1, buttons=0, axes=(150, 350),
          mouse=(0, 0), tolerance=(6, 9), metrics=(1921, 1081), point=(765, -321),
          detected=1, button_count=9, inhibit=0, joy_status=0, devices=1,
          caps_status=0, ranges=(100, 1101, 200, 2303), binding_latch=0,
          masks=None, binding_keys=None, dirty=0x5a, stale=False, hat=0xffff):
    held = {} if held is None else dict(held)

    def setup(env):
        s = env.object(584, 'original source allocation', fill=dirty)
        b = env.object(144, 'original binding allocation', fill=dirty ^ 0xff)
        env.put(s, 3)
        env.put(s + 0x198, 52, 0, axes[0] & 0xffffffff, axes[1] & 0xffffffff)
        env.put(s + 0x1b8, buttons, 0x87654321, hat)
        env.put(s + 0x40, button_count)
        env.put(s + 0x1cc, mode, detected, extended, inhibit)
        env.put(s + 0x1dc, *range(0x70, 0x7c))
        env.put(s + 0x20c, latch, 0xabcdef01, 0x76543210)
        env.put(s + 0x218, 500, 1100, 100, 200, 300, 400)
        env.put(s + 0x230, mouse[0] & 0xffffffff, mouse[1] & 0xffffffff,
                tolerance[0] & 0xffffffff, tolerance[1] & 0xffffffff, 961, 541)
        env.put(b, s, 0xaabbccdd, 0x11223344, binding_latch)
        env.put(b + 0x10, *(masks if masks is not None else (1, 2, 4, 8, 0x80000000, 16, 32, 64, 128, 256)))
        env.put(b + 0x38, *(binding_keys if binding_keys is not None else range(0x90, 0x9e)))
        # The original CMap subobject is untouched by all owned entries.
        env.put(b + 0x74, 0x510054)

        def key(e, c):
            return held.get(c.arguments[0], 0)

        def metrics_effect(e, c):
            return metrics[c.arguments[0]] & 0xffffffff

        def cursor(e, c):
            e.put(c.arguments[0], point[0] & 0xffffffff, point[1] & 0xffffffff)
            return 1

        def position(e, c):
            if not joy_status and not stale:
                p = c.arguments[1]
                e.put(p + 8, axes[0] & 0xffffffff, axes[1] & 0xffffffff)
                e.put(p + 32, buttons, 0x87654321, hat)
            return joy_status

        def caps(e, c):
            if not caps_status:
                p = c.arguments[1]
                e.write(p, bytes((i * 37 + 11) & 255 for i in range(404)))
                e.put(p + 36, *ranges)
                e.put(p + 60, button_count)
            return caps_status

        env.override(KEY, key)
        env.override(METRICS, metrics_effect)
        env.override(CURSOR, cursor)
        env.override(WARP, lambda e, c: 0)
        env.override(POSITION, position)
        env.override(CAPS, caps)
        env.override(COUNT, lambda e, c: devices)
        return {'source': s, 'binding': b}
    return setup


def entry(label, address, owner='source', arguments=(), **options):
    return Case(label, address, scene(**options), receiver=lambda t: t[owner], arguments=arguments)


def cases(random_source):
    for dirty in (0x31, 0xe7):
        yield entry(f'clear exact buffers {dirty}', 0x4b3410, dirty=dirty)
        for address in (0x430d30, 0x430d80):
            yield entry(f'default guards {address:x} {dirty}', address, 'binding', dirty=dirty)
    for mode in range(8):
        for detected in (0, 1):
            yield entry(f'modes {mode} device {detected}', 0x4b3430, arguments=(mode | 0x80000100,), detected=detected,
                        metrics=(-1921, 1083))
        for address, owner in ((0x4b3ab0, 'source'), (0x431300, 'binding')):
            yield entry(f'reset {address:x} mode {mode}', address, owner, mode=mode | 0x100,
                        held={i: 0x80008001 for i in range(0x70, 0x7c)}, metrics=(1923, -1081))
    for failure in ('devices', 'position', 'caps'):
        for old in (0, 2, 1, 3, 4, 0x80000102):
            yield entry(f'initialize {failure} old {old:x}', 0x4b3240, arguments=(7, 5), mode=old,
                        devices=0 if failure == 'devices' else 2,
                        joy_status=17 if failure == 'position' else 0,
                        caps_status=19 if failure == 'caps' else 0, extended=0x13579bdf)
    for count in (0, 4, 5, 8, 9, 0x80000009):
        for mode in (0, 3, 7):
            yield entry(f'discovery success count {count:x} modes {mode}', 0x4b3240,
                        arguments=(mode, 1), button_count=count, ranges=(101, 1104, 307, 2508), metrics=(-3, 5))
    for ranges in ((0, 0, 0, 1), (500, 499, 0x80000000, 0x7fffffff), (0, 0xffffffff, 7, 0xfffffffe)):
        yield entry(f'discovery spans {ranges}', 0x4b3240, arguments=(7, 0), ranges=ranges)

    # Absent, newly acquired and already-held states for every source bit.
    for latch in (0, 0xffffffff):
        yield entry(f'source all keyboard latch {latch:x}', 0x4b3490, mode=1, latch=latch,
                    held={i: 0x12348001 for i in range(0x70, 0x7c)})
        yield entry(f'source all joystick latch {latch:x}', 0x4b3490, mode=2, latch=latch,
                    axes=(0, 0xffffffff), buttons=0x1ff)
        yield entry(f'source opposite joystick latch {latch:x}', 0x4b3490, mode=2, latch=latch,
                    axes=(0xffffffff, 0), buttons=0x1ff)
        yield entry(f'source absent latch {latch:x}', 0x4b3490, mode=0, latch=latch)
    for word in (0, 1, 0x8000, 0x8001, 0x80000000, 0x7fff8000, 0xffff0001):
        yield entry(f'keyboard SHORT {word:x}', 0x4b3490, mode=1,
                    held={i: word for i in range(0x70, 0x7c)}, extended=0, latch=0xffffffff)
    for index in range(12):
        yield entry(f'isolated source key {index}', 0x4b3490, mode=1,
                    held={0x70 + index: 0x8001}, latch=SOURCE_BITS[index] ^ 0x02345000)
    for value in (-10, -9, -7, -6, 0, 6, 7, 9, 10, -2147483648, 2147483647):
        yield entry(f'mouse dead zones {value}', 0x4b3490, mode=4, mouse=(value, value),
                    held={1: 1, 2: 0x8000}, point=(value * 3 & 0xffffffff, 777))
    for tolerance in ((0, 0), (-6, -9), (-2147483648, -2147483648)):
        yield entry(f'mouse tolerance {tolerance}', 0x4b3490, mode=4, tolerance=tolerance)
    for value in (0, 99, 100, 101, 199, 200, 201, 299, 300, 301, 399, 400, 401, 0xffffffff):
        yield entry(f'unsigned joystick thresholds {value}', 0x4b3490, mode=2, axes=(value, value), hat=value)
    for count in (4, 5, 8, 9, 0xffffffff):
        for ext, inhibit in ((0, 0), (1, 0), (1, 1)):
            yield entry(f'joystick button gates {count} {ext} {inhibit}', 0x4b3490, mode=2,
                        buttons=0x1ff, button_count=count, extended=ext, inhibit=inhibit,
                        joy_status=7, stale=True)
    for bit in range(9):
        yield entry(f'isolated joystick button {bit}', 0x4b3490, mode=2, buttons=1 << bit, latch=0x34567000)

    for latch in (0, 0xffffffff):
        yield entry(f'binding all source new/held {latch:x}', 0x430ec0, 'binding', mode=1,
                    held={i: 0x8000 for i in range(0x70, 0x7c)}, binding_latch=latch)
        yield entry(f'binding all keys new/held {latch:x}', 0x430ec0, 'binding', mode=0,
                    held={i: 0x8000 for i in range(0x90, 0x9e)}, binding_latch=latch)
        yield entry(f'binding all absent {latch:x}', 0x430ec0, 'binding', binding_latch=latch)
    for index in range(14):
        yield entry(f'isolated binding key {index}', 0x430ec0, 'binding',
                    held={0x90 + index: 0x80008000}, binding_latch=0x50804010)
    for word in (1, 0x80000000, 0x8001, 0xffff0001):
        yield entry(f'binding SHORT {word:x}', 0x430ec0, 'binding',
                    held={i: word for i in range(0x90, 0x9e)}, binding_keys=(0,) * 14 if word == 1 else None)
    yield entry('configured zero binding key held', 0x430ec0, 'binding',
                binding_keys=(0,) * 14, held={0: 0x12348000})
    for masks in ((0,) * 10, (1,) * 10, tuple(1 << i for i in range(10))):
        yield entry(f'binding mask overlap {masks}', 0x430ec0, 'binding', mode=2,
                    masks=masks, buttons=0x155, latch=0xffffffff)
    for _ in range(24):
        held = {i: random_source.choice((0, 1, 0x8000, 0x8001, 0x80000000)) for i in (*range(0x70, 0x7c), *range(0x90, 0x9e), 1, 2)}
        yield entry(f'random binding chord {_}', 0x430ec0, 'binding', mode=random_source.randrange(8),
                    held=held, latch=random_source.getrandbits(32), binding_latch=random_source.getrandbits(32),
                    masks=tuple(random_source.choice((0, 1, 0xff, 0x10000001, random_source.getrandbits(32))) for i in range(10)),
                    buttons=random_source.randrange(512), axes=(random_source.randrange(500), random_source.randrange(500)),
                    mouse=(random_source.randrange(-12, 13), random_source.randrange(-12, 13)))
