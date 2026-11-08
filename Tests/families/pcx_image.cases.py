"""Independent inputs recovered from the hash-verified original PCX packet."""
import struct
from clawparity.cases import Case

NEW = 0x4F63EC


def surface(env, width=4, height=2, depth=24, pitch=40, lock_null=False,
            mutate=False, alias=None, lock_result=0):
    target = env.object(188, 'surface', fill=0x53)
    pixels = env.object(2048, 'guarded pixels', data=bytes((i * 29 + 17) & 255 for i in range(2048)))
    pixel_start = pixels + (1024 if pitch < 0 else 16)
    interface = env.object(4, 'surface COM')
    table = env.object(132, 'COM vtable', fill=0)
    own_table = env.object(32, 'surface vtable', fill=0)
    record = env.object(256, 'callback observations', fill=0)
    alternate = env.object(4, 'replacement COM')
    alt_table = env.object(132, 'replacement vtable', fill=0)

    def observe(e, c, tag):
        n = e.get(record)
        e.put(record, n + 1)
        e.put(record + 4 + n * 32, tag, c.receiver, len(c.arguments),
              *(list(c.arguments) + [0] * (5 - len(c.arguments))))
        e.put(record + 200, e.get(target + 0x14), e.get(target + 0x18),
              e.get(target + 0x30), e.get(pixel_start))

    def unlock(e, c):
        observe(e, c, 0x8822)
        e.put(target + 0xB0, 0xA17C0021)
        return 0x80004005

    unlock_fn = env.stub('Unlock with visible effects', 'stdcall', 2, unlock)
    env.put(table + 0x80, unlock_fn)
    env.put(alt_table + 0x80, unlock_fn)
    env.put(alternate, alt_table)

    def lock(e, c):
        observe(e, c, 0x6411)
        e.put(target + 0x30, 0 if lock_null else pixel_start)
        if mutate:
            e.put(target + 0x14, 1, 3, pitch + 3)
            e.put(target + 8, alternate)
        return lock_result

    env.put(table + 0x64, env.stub('Lock publishes pixels', 'stdcall', 5, lock))
    env.put(interface, table)
    env.put(target, own_table)
    env.put(target + 8, interface)
    env.put(target + 0x14, height & 0xFFFFFFFF, width & 0xFFFFFFFF, pitch & 0xFFFFFFFF)
    env.put(target + 0x30, pixel_start)
    env.put(target + 0xA4, depth, max(0, width) * 3)
    env.put(target + 0xB4, 0)
    env.put(0x54139C, 0, 0, 0, 0)
    source = env.object(2048, 'source', data=bytes((i * 71 + 13) & 255 for i in range(2048)))
    palette_data = bytes(v for i in range(256) for v in (i, (i * 5 + 3) & 255, (i * 11 + 9) & 255, (i ^ 0xA5)))
    palette = env.object(1024, 'distinct RGBX palette', data=palette_data)
    # 565 format controls consumed by unchanged original conversion callees.
    env.put(0x54135C, 11, 5, 0, 3, 2, 3)
    if alias == 'source':
        source = pixel_start + 1
    elif alias == 'palette':
        palette = pixel_start
    return dict(surface=target, pixels=pixels, source=source, palette=palette,
                record=record)


def entry(label, fn, setup, arguments=()):
    return Case(label, fn, setup, receiver=lambda t: t['surface'], arguments=arguments)


def rle(width, height, planes, salt=0):
    # Every plane has zero-run, literal and nonzero-run forms. Escaped values
    # deliberately include high marker bytes, and each plane has distinct data.
    encoded = bytearray()
    for row in range(max(0, height)):
        for plane in range(planes):
            v = (row * 19 + plane * 37 + salt) & 255
            encoded.extend((0xC0, 0xF1, (v + 7) % 192))
            if width > 1:
                encoded.extend((0xC0 | min(63, width - 1), (v + 0xC1) & 255))
    return bytes(encoded) or b'\x27'


def decoder_setup(width, height, planes, null=False, lock_null=False,
                  mutate=False, alias=False, overshoot=False):
    def setup(env):
        t = surface(env, width, height, 8 if planes == 1 else 24,
                    lock_null=lock_null, mutate=mutate)
        data = rle(width, height, planes, 17)
        if overshoot:
            data = bytes((0xFF, 0xEA)) * max(1, height * planes)
        env.write(t['source'], data)
        if alias:
            env.write(t['pixels'] + 16, data)
            t['source'] = t['pixels'] + 16
        if null:
            t['source'] = 0
        return t
    return setup


def load_setup(planes=1, context_depth=8, target_depth=None, width=4, height=2,
               mismatch=None, fail_alloc=False, lock_null=False, palette_ready=1,
               allocation_mutation=None, signed_origin=False):
    def setup(env):
        t = surface(env, width, height, target_depth or context_depth, lock_null=lock_null)
        context = env.object(0x900, 'format context', fill=0xA3)
        env.put(context + 0x474, context_depth)
        env.write(context + 0x478, env.read(t['palette'], 1024))
        env.put(context + 0x878, palette_ready)
        header = bytearray(2048)
        x, y = (-11, -7) if signed_origin else (0, 0)
        struct.pack_into('<hhhh', header, 4, x, y, x + width - 1, y + height - 1)
        header[65] = planes
        header[128:128 + len(rle(width, height, planes))] = rle(width, height, planes)
        header[-768:] = bytes((i * 17 + 31) & 255 for i in range(768))
        buffer = env.object(2048, 'PCX buffer', data=bytes(header))
        if mismatch == 'width':
            env.put(t['surface'] + 0x18, width + 1)
        if mismatch == 'height':
            env.put(t['surface'] + 0x14, height + 1)
        if mismatch == 'null':
            buffer = 0
        if fail_alloc or allocation_mutation:
            def alloc(e, c):
                e.put(t['record'] + 220, c.arguments[0], e.get(t['surface'] + 0xA4))
                if fail_alloc:
                    return 0
                if allocation_mutation == 'format':
                    e.put(t['surface'] + 0xA4, 32)
                elif allocation_mutation == 'geometry':
                    e.put(t['surface'] + 0x14, 1, 2)
                return e.object(max(1, c.arguments[0]), 'temporary decoded image', fill=0x91)
            env.override(NEW, alloc)
        t.update(context=context, buffer=buffer)
        return t
    return setup


def cases(random_source):
    for fn in (0x4BB040, 0x4BB050, 0x4BB0F0):
        for value in (0, 1, 0xFFFFFFFF, 0x80000001, random_source.getrandbits(32)):
            def geometry(env, value=value):
                t = surface(env)
                env.put(t['surface'] + 0x14, value ^ 0x11223344, value, value ^ 0xA3B4C5D6)
                return t
            yield entry(f'geometry {fn:x} {value:x}', fn, geometry,
                        (0x80000003,) if fn == 0x4BB0F0 else ())

    for callback_result in (None, 0, 1, 0xFFFFFFFF):
        def restore(env, result=callback_result):
            t = surface(env)
            def fallback(e, c):
                e.put(t['record'] + 240, e.get(t['surface'] + 0xA4), c.receiver)
                return 0x721
            env.put(0x54138C, env.stub('restore fallback', 'cdecl', 0, fallback))
            if result is not None:
                def callback(e, c):
                    e.put(t['record'], c.arguments[0], c.receiver)
                    e.put(c.arguments[0] + 0xA4, 0x7B)
                    return result
                env.put(t['surface'] + 0xB4, env.stub('restore callback', 'cdecl', 1, callback))
            return t
        yield entry(f'restore callback {callback_result}', 0x4B9E60, restore)

    for target_depth in (0, 8, 16, 24, 32):
        for source_depth in (0, 1, 8, 16, 24, 32):
            for direction in (1, 2):
                yield entry(f'dispatch {target_depth}/{source_depth} dir {direction}', 0x4B9E90,
                            lambda e, d=target_depth: surface(e, depth=d),
                            (lambda t: t['source'], source_depth, lambda t: t['palette'], direction))

    for fn in (0x4BA2D0, 0x4BA580):
        for direction in (0, 2):
            for width, height in ((4, 2), (0, 2), (3, 0), (-1, 1), (1, 1)):
                yield entry(f'convert {fn:x} {width}/{height} dir {direction}', fn,
                            lambda e, w=width, h=height: surface(e, w, h),
                            (lambda t: t['source'], lambda t: t['palette'], direction))
            for alias in ('source', 'palette'):
                yield entry(f'convert {fn:x} alias {alias} dir {direction}', fn,
                            lambda e, a=alias: surface(e, alias=a),
                            (lambda t: t['source'], lambda t: t['palette'], direction))
            yield entry(f'convert {fn:x} lock changes geometry and COM dir {direction}', fn,
                        lambda e: surface(e, mutate=True),
                        (lambda t: t['source'], lambda t: t['palette'], direction))
        yield entry(f'convert {fn:x} null palette', fn, surface,
                    (lambda t: t['source'], 0, 1))
        yield entry(f'convert {fn:x} null lock pointer', fn,
                    lambda e: surface(e, lock_null=True),
                    (lambda t: t['source'], lambda t: t['palette'], 1))
        # Exact match after index zero, improvement without zero, ties and full scan.
        def search(env):
            t = surface(env, 4, 2)
            env.write(t['palette'], bytes([250, 250, 250, 77]) * 256)
            env.write(t['palette'] + 4, bytes([9, 21, 33, 99]))
            env.write(t['palette'] + 8, bytes([10, 22, 34, 13]))
            env.write(t['source'], bytes([33, 21, 9, 35, 23, 11, 250, 250, 250, 0, 0, 0]) * 2)
            return t
        for direction in (1, 2):
            yield entry(f'palette search decisions dir {direction}', fn, search,
                        (lambda t: t['source'], lambda t: t['palette'], direction))

    for planes, fn, raw in ((1, 0x4BABE0, 0x4BEF50), (3, 0x4BAD30, 0x4BF070)):
        for width, height in ((4, 2), (1, 1), (0, 2), (-1, 1), (3, 0), (2, -1), (63, 1)):
            yield entry(f'surface decode {planes} {width}/{height}', fn,
                        decoder_setup(width, height, planes), (lambda t: t['source'],))
            yield entry(f'raw decode {planes} {width}/{height}', raw,
                        decoder_setup(width, height, planes),
                        (lambda t: t['pixels'] + 16, lambda t: t['source'], width & 0xFFFFFFFF, height & 0xFFFFFFFF))
        for mode in ('null', 'lock_null', 'mutate', 'alias', 'overshoot'):
            yield entry(f'surface decode {planes} {mode}', fn,
                        decoder_setup(4, 2, planes, **{mode: True}), (lambda t: t['source'],))
        for mode in ('destination', 'source', 'alias', 'overshoot'):
            yield entry(f'raw decode {planes} {mode}', raw,
                        decoder_setup(4, 2, planes, alias=mode == 'alias', overshoot=mode == 'overshoot'),
                        (0 if mode == 'destination' else lambda t: t['pixels'] + 16,
                         0 if mode == 'source' else lambda t: t['source'], 4, 2))

    configurations = [dict(mismatch=m) for m in ('null', 'width', 'height')]
    configurations += [dict(planes=2), dict(planes=0), dict(planes=3, palette_ready=0)]
    for planes in (1, 3):
        for context_depth in (8, 16, 24, 32):
            configurations.append(dict(planes=planes, context_depth=context_depth, signed_origin=True))
            configurations.append(dict(planes=planes, context_depth=context_depth, lock_null=True))
            if context_depth != planes * 8:
                configurations.append(dict(planes=planes, context_depth=context_depth, fail_alloc=True))
                configurations.append(dict(planes=planes, context_depth=context_depth, allocation_mutation='format'))
                configurations.append(dict(planes=planes, context_depth=context_depth, allocation_mutation='geometry'))
    for i, options in enumerate(configurations):
        yield entry(f'load buffer {i} {options}', 0x4BEBC0, load_setup(**options),
                    (lambda t: t['context'], lambda t: t['buffer'], 2048))

    for i in range(8):
        width = random_source.randrange(1, 9)
        height = random_source.randrange(1, 4)
        payload = bytes(random_source.randrange(256) for _ in range(1024))
        def randomized(env, w=width, h=height, data=payload):
            t = surface(env, w, h, pitch=w * 3 + 7)
            env.write(t['palette'], data)
            env.write(t['source'], data)
            return t
        for fn in (0x4BA2D0, 0x4BA580):
            yield entry(f'random pixel conversion {i} {fn:x}', fn, randomized,
                        (lambda t: t['source'], lambda t: t['palette'], i % 3))
    for fn in (0x4BA2D0, 0x4BA580, 0x4BABE0, 0x4BAD30):
        yield entry(f'COM lock returns error {fn:x}', fn,
                    lambda e: surface(e, lock_result=0x80004005),
                    (lambda t: t['source'],) if fn in (0x4BABE0, 0x4BAD30) else
                    (lambda t: t['source'], lambda t: t['palette'], 1))

    for fn in (0x4BA2D0, 0x4BA580):
        for pitch in (-40, 0, 2):
            yield entry(f'signed overlapping pitch {fn:x} {pitch}', fn,
                        lambda e, p=pitch: surface(e, pitch=p),
                        (lambda t: t['source'], lambda t: t['palette'], 1))
