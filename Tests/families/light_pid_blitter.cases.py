"""Exercise the original dispatcher with original rasterizers and physical DD callbacks."""
from clawparity.cases import Case

BLIT = 0x4BFFA0


def scene(random_source, mode=1, bpp=1, flags=(0, 0), rect=None,
          width=9, height=4, sparse=True, dither=0, parameter=73,
          unlock_result=0, no_light=False, point=None, lock_changes=False):
    # Complete extra rows make an unchecked bottom beyond image height safe.
    rows = max(8, height + 2) if 0 < height < 100 else 8
    stream = bytearray()
    for row in range(rows):
        runs = ((2, False), (2, True), (width - 4, False)) if sparse and width >= 5 else ((width, False),)
        for count, transparent in runs:
            stream.append(count + 128 if transparent else count)
            if not transparent:
                stream.extend(random_source.randrange(1, 256) for _ in range(count * bpp))
    initial_pixels = bytes(random_source.randrange(1, 256) for _ in range(8192))
    # Neither symmetric nor separable: wrong source/destination lookup order is visible.
    salt = random_source.randrange(1, 256)
    table_data = bytes(((x * 37 + y * 53 + (x ^ y) * 7 + salt) & 255)
                       for y in range(256) for x in range(256))
    rectangle = (0, 0, width - 1, height - 1) if rect is None else rect
    destination = (5, 3, 19, 11) if point is None else point

    def setup(env):
        pixels = env.object(len(initial_pixels), 'guarded destination', data=initial_pixels)
        stream_ptr = env.object(len(stream), 'compressed complete rows', data=bytes(stream))
        table = env.object(len(table_data), 'asymmetric lighting lookup', data=table_data)
        lighting = env.object(12, 'lighting owner', words=[0x129A, 0x5481, table])
        image = env.object(0x28, 'light PID', fill=0xAD)
        env.put(image, dither, width, height, stream_ptr, 0x523F, mode, parameter,
                0 if no_light else lighting, 0x8917)
        env.write(image + 0x24, bytes([bpp, 0xB6, 0xC9, 0xDA]))
        surface = env.object(0xBC, 'surface wrapper', fill=0)
        interface = env.object(4, 'DirectDraw interface')
        vtable = env.object(0x84, 'DirectDraw vtable', fill=0)
        log = env.object(80, 'physical callback order and arguments', fill=0)
        point_ptr = env.object(16, 'destination rectangle', words=destination)
        rect_ptr = env.object(16, 'source rectangle', words=rectangle)
        env.put(surface + 8, interface)
        env.put(surface + 0x1C, 64)
        env.put(surface + 0x30, pixels + 2048)
        env.put(interface, vtable)

        def lock(env, call):
            env.put(log, env.get(log) + 1)
            env.put(log + 4, *call.arguments)
            env.put(log + 24, env.get(image + 0x14), env.get(image + 4), env.get(rect_ptr))
            env.put(surface + 0x30, pixels + 2048)
            # A physical lock publishes destination memory before game rendering.
            env.write(pixels + 2048 + 3 * 64 + 5, bytes([0xD3, 0x8A, 0x41]))
            if lock_changes:
                env.put(image + 0x18, 149)
            return 0

        def unlock(env, call):
            env.put(log + 36, env.get(log) + 1, *call.arguments)
            env.put(log + 48, env.get(surface + 0x30), env.get(image + 0x18))
            return unlock_result

        env.put(vtable + 0x64, env.stub('IDirectDrawSurface::Lock', 'stdcall', 5, lock))
        env.put(vtable + 0x80, env.stub('IDirectDrawSurface::Unlock', 'stdcall', 2, unlock))
        return dict(image=image, point=point_ptr, surface=surface, rect=rect_ptr)

    return setup


def draw(label, random_source, flags=(0, 0), **options):
    return Case(label, BLIT, scene(random_source, flags=flags, **options),
                receiver=lambda t: t['image'],
                arguments=(lambda t: t['point'], lambda t: t['surface'],
                           lambda t: t['rect'], *flags))


def rejected(label, width=9, height=4, rect=(0, 0, 8, 3), mode=1, bpp=1):
    def setup(env):
        image = env.object(0x28, 'rejected PID', fill=0x91)
        env.put(image + 4, width, height)
        env.put(image + 0x14, mode)
        env.write(image + 0x24, bytes([bpp, 0xA9, 0xB4, 0xEF]))
        source = env.object(16, 'rejected source rectangle', words=rect)
        # All pointers are backed, even though rejected calls must not use them.
        point = env.object(16, 'unused destination', fill=0x37)
        surface = env.object(0xBC, 'unused surface', fill=0x63)
        return dict(image=image, rect=source, point=point, surface=surface)
    return Case(label, BLIT, setup, receiver=lambda t: t['image'],
                arguments=(lambda t: t['point'], lambda t: t['surface'],
                           lambda t: t['rect'], 0xFFFFFFFF, 0x80000000))


def cases(random_source):
    # Every mirror pair renders distinct rows and columns, including non-boolean flags.
    flag_pairs = ((0, 0), (7, 0), (0, 0x80000000), (0xFFFFFFFF, 19))
    for flags in flag_pairs:
        for bpp in (1, 2):
            yield draw(f'plain {bpp} byte pixels mirrors {flags}', random_source,
                       flags=flags, bpp=bpp)
        for mode in (2, 4, 8, 0x16, 0x32):
            yield draw(f'lighting mode {mode} mirrors {flags}', random_source,
                       flags=flags, mode=mode, lock_changes=(mode == 8))
        for mode in (2, 4):
            yield draw(f'dithered mode {mode} mirrors {flags}', random_source,
                       flags=flags, mode=mode, dither=1)
        yield draw(f'cropped left and right mirrors {flags}', random_source,
                   flags=flags, rect=(2, 0, 6, 3), mode=0x16)
        yield draw(f'unlock error ignored mirrors {flags}', random_source,
                   flags=flags, unlock_result=0x80004005)

    yield rejected('left negative short circuits', rect=(-1, -1, 0x7FFFFFFF, 3))
    yield rejected('left minimum signed', rect=(-0x80000000, 0, 8, 3))
    yield rejected('right just outside', rect=(0, 0, 9, 3))
    yield rejected('right maximum signed', rect=(0, 0, 0x7FFFFFFF, 3))
    yield rejected('top negative', rect=(0, -1, 8, 3))
    yield rejected('top minimum signed', rect=(0, -0x80000000, 8, 3))
    yield rejected('top just outside', rect=(0, 4, 8, 3))
    yield rejected('top maximum signed', rect=(0, 0x7FFFFFFF, 8, 3))
    yield rejected('zero width bound', width=0)
    yield rejected('negative width bound', width=0xFFFFFFFF)
    yield rejected('zero height bound', height=0)
    yield rejected('negative height bound', height=0xFFFFFFFF)
    for bpp in (0, 2, 0xFF):
        yield rejected(f'lighting rejects pixel-size {bpp}', mode=0x16, bpp=bpp)

    # Accepted bounds that a plausible extra validation would wrongly reject.
    yield draw('bottom beyond height is forwarded', random_source, rect=(0, 0, 8, 5))
    yield draw('bottom negative is forwarded', random_source, rect=(0, 0, 8, -1))
    yield draw('top equals height minus one', random_source, rect=(0, 3, 8, 3))
    yield draw('left exceeds right still accepted', random_source, rect=(7, 0, 3, -1))
    yield draw('negative right still accepted', random_source, rect=(0, 0, -1, -1))
    yield draw('single pixel image', random_source, width=1, height=1, sparse=False)
    # Early return in the real lighting child allows wrapped bound extremes safely.
    for width, height in ((0x80000000, 4), (9, 0x80000000)):
        # Stream widths stay small; only the receiver's declared geometry changes.
        setup = scene(random_source, mode=0x16, no_light=True)
        def extreme(env, setup=setup, width=width, height=height):
            tokens = setup(env)
            env.put(tokens['image'] + 4, width, height)
            return tokens
        yield Case(f'wrapped signed bounds {width:#x} {height:#x}', BLIT, extreme,
                   receiver=lambda t: t['image'],
                   arguments=(lambda t: t['point'], lambda t: t['surface'],
                              lambda t: t['rect'], 0, 0))
    for mode in (0, 3, 0x1000001, 0xFFFFFFFF):
        yield draw(f'non-one mode {mode:#x} selects lighting', random_source,
                   mode=mode, no_light=True)
    for i in range(12):
        width = random_source.randrange(5, 20)
        height = random_source.randrange(1, 6)
        yield draw(f'random geometry and flags {i}', random_source,
                   width=width, height=height, mode=random_source.choice((1, 2, 4, 8, 0x16)),
                   flags=random_source.choice(flag_pairs), sparse=bool(i % 2),
                   parameter=random_source.randrange(1, 255))
