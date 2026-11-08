"""Independent original-only raw PID inputs; no renderer implementation imports."""
from clawparity.cases import Case

ENTRY = 0x4C00B0


def fixture(rows, source, destination, pitch, initial, mutate=False, unlock_result=0):
    width = sum(abs(n) for n in rows[0])
    payload = bytearray()
    value = 19
    for row in rows:
        for n in row:
            payload.append(n if n > 0 else 128 - n)
            if n > 0:
                for _ in range(n):
                    value = (value + 37) % 256
                    payload.append(value)

    def setup(env):
        pixels = env.object(len(initial), 'destination pixels and guard bytes', data=initial)
        stream = env.object(len(payload), 'encoded runs', data=bytes(payload))
        image = env.object(40, 'PID receiver', fill=0x71)
        env.put(image + 4, width, len(rows), stream, len(payload))
        env.write(image + 0x24, b'\x01')
        src = env.object(16, 'source rectangle', words=list(source))
        dst = env.object(16, 'destination rectangle', words=list(destination))
        surface = env.object(188, 'surface', fill=0)
        dd = env.object(4, 'initial DirectDraw interface')
        vt = env.object(132, 'initial DirectDraw methods', fill=0)
        dd2 = env.object(4, 'replacement DirectDraw interface')
        vt2 = env.object(132, 'replacement DirectDraw methods', fill=0)
        log = env.object(128, 'physical callback observations', fill=0)
        env.put(dd, vt)
        env.put(dd2, vt2)
        env.put(surface + 8, dd)
        env.put(surface + 0x1c, pitch)

        def unlock(env, call):
            env.put(log + 48, call.receiver, *call.arguments)
            env.write(log + 64, env.read(pixels, 32))
            env.put(log + 96, env.get(surface + 0x1c), env.get(image + 4))
            return unlock_result

        def lock(env, call):
            env.put(log, call.receiver, *call.arguments)
            env.put(surface + 0x30, pixels)
            if mutate:
                replacement = env.object(len(payload), 'post-lock stream', data=bytes(payload))
                env.put(image + 4, width, len(rows), replacement, len(payload))
                env.write(image + 0x24, b'\x01')
                env.put(src, *source)
                env.put(dst, *destination)
                env.put(surface + 0x1c, pitch + 7)
                env.put(surface + 8, dd2)
            return 0

        env.put(vt + 0x64, env.stub('physical Lock', 'stdcall', 5, lock))
        env.put(vt + 0x80, env.stub('physical initial Unlock', 'stdcall', 2, unlock))
        env.put(vt2 + 0x80, env.stub('physical replacement Unlock', 'stdcall', 2, unlock))
        if mutate:
            env.put(image + 4, width + 3, len(rows) + 2, stream, len(payload))
            env.write(image + 0x24, b'\x02')
            env.put(src, 0, 0, width + 2, 0)
            env.put(dst, 0, 0, 0, 0)
        return dict(image=image, src=src, dst=dst, surface=surface)
    return setup


def cases(random_source):
    patterns = [[8], [-8], [2, -2, 3, -1], [-2, 2, -1, 3], [1, 1, 1, 1, 1, 1, 1, 1], [4, 4]]
    for index, row in enumerate(patterns):
        rows = [patterns[(index + j) % len(patterns)] for j in range(5)]
        for top in (0, 1, 3):
            for left in (0, 1, 2, 3, 4, 7):
                for right in ((0, 2, 4, 7) if left == 0 else (0, 7)):
                    for bottom in (top - 1, top, 4):
                        data = bytes(random_source.randrange(1, 256) for _ in range(512))
                        yield Case(f'pattern {index} source {left},{top},{right},{bottom}', ENTRY,
                                   fixture(rows, (left, top, right, bottom), (3, 2, -91, -77), 23, data),
                                   receiver=lambda t: t['image'],
                                   arguments=(lambda t: t['dst'], lambda t: t['surface'], lambda t: t['src']))
    for index in range(30):
        width = random_source.randrange(1, 65)
        rows = []
        for _ in range(4):
            row, remaining = [], width
            while remaining:
                n = random_source.randrange(1, min(remaining, 127) + 1)
                row.append(n if random_source.randrange(2) else -n)
                remaining -= n
            rows.append(row)
        left = random_source.randrange(width)
        src = (left, 1, width - 1 if index % 2 else width // 2, 3)
        data = bytes(random_source.randrange(256) for _ in range(1024))
        yield Case(f'post-lock reload and random runs {index}', ENTRY,
                   fixture(rows, src, (-2, 2, 123, -12), width + 11, data, True, 0x88760001 + index),
                   receiver=lambda t: t['image'],
                   arguments=(lambda t: t['dst'], lambda t: t['surface'], lambda t: t['src']))
    for width in (1, 127, 128, 4096):
        full = [127] * (width // 127) + ([width % 127] if width % 127 else [])
        rows = [full, [-n for n in full], full]
        for left in (0, width - 1):
            data = bytes(random_source.randrange(256) for _ in range((width + 13) * 7))
            yield Case(f'width boundary {width} left {left}', ENTRY,
                       fixture(rows, (left, 0, width - 1, 2), (2, 1, 0, 0), width + 13, data),
                       receiver=lambda t: t['image'],
                       arguments=(lambda t: t['dst'], lambda t: t['surface'], lambda t: t['src']))
    # Offset zero is a real buffer boundary as well as a valid draw origin.
    # Literal, transparent, and mixed rows distinguish zero-length clipping
    # from the first actual copied byte, including after skipped source rows.
    for row in ([8], [2, -2, 4], [-2, 6], [1, 7]):
        rows = [[3, -2, 3], [-3, 5], row, row]
        for top in (0, 1, 2):
            for left, right in ((0, 0), (0, 1), (0, 2), (0, 7), (1, 0), (2, 7), (3, 0)):
                data = bytes(random_source.randrange(1, 256) for _ in range(256))
                yield Case(f'buffer-origin row {row} source {left},{top},{right},3', ENTRY,
                           fixture(rows, (left, top, right, 3), (0, 0, -71, -19), 17, data),
                           receiver=lambda t: t['image'],
                           arguments=(lambda t: t['dst'], lambda t: t['surface'], lambda t: t['src']))
