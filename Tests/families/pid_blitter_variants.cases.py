"""Cases for pid_blitter_variants: eight original compressed PID blitters.

Branch selection never depends on the seed: run patterns, rectangles, modes and
destinations are fixed lists.  The seed only varies pixel data and lookup tables.
"""
from clawparity.cases import Case

F0450, F0920, F0CC0, F1190 = 0x4C0450, 0x4C0920, 0x4C0CC0, 0x4C1190
F25B0, F3800, F4C20, F5E80 = 0x4C25B0, 0x4C3800, 0x4C4C20, 0x4C5E80

PITCH = 48
BUFFER = 3072
MIDDLE = 1536
TABLE = 4096 + 512
W = 9

# Signed run lengths (positive literal, negative transparent), each row sums to W.
PATTERNS = (
    (9,), (-9,), (3, -2, 4), (-3, 2, -4), (4, -1, 1, 3), (-4, 3, 2), (1, 1, 1, 1, 1, 1, 1, 1, 1),
    (2, -3, 2, -2), (5, 4), (-1, 8), (8, -1), (6, -2, 1),
)


def pixel_runs(rows):
    return rows


def build_stream(random_source, rows, bpp, width):
    out = bytearray()
    for row in rows:
        total = sum(abs(n) for n in row)
        assert total == width, (row, width)
        for n in row:
            if n > 0:
                out.append(n)
                out.extend(random_source.randrange(1, 16) for _ in range(n * bpp))
            else:
                out.append(128 - n)
    return bytes(out)


def scene(random_source, receiver_fn, rows, bpp, mode, dither, param, rect, dest,
          width=W, height=None, no_light=False, unlock_result=0, lock_result=0):
    height = len(rows) if height is None else height
    # Complete extra rows: unchecked bottoms read ahead safely.
    extra = [(width,), (-1, width - 1) if width > 1 else (-1,)]
    stream = build_stream(random_source, list(rows) + extra, bpp, width)
    table = bytes(random_source.randrange(1, 16) for _ in range(TABLE))
    pixels_init = bytes(random_source.randrange(1, 16) for _ in range(BUFFER))
    salt = random_source.randrange(1, 255)

    def setup(env):
        pixels = env.object(BUFFER, "destination with guard rows", data=pixels_init)
        stream_ptr = env.object(len(stream), "compressed rows", data=stream)
        table_ptr = env.object(TABLE, "lighting table", data=table)
        lighting = env.object(16, "lighting owner", words=[0x1A2B, 0x3C4D, table_ptr, 0x5E6F])
        image = env.object(0x30, "PID image", fill=0xA5)
        env.put(image, dither, width, height, stream_ptr, 0x523F, mode, param,
                0 if no_light else lighting, 0x8917)
        env.write(image + 0x24, bytes([bpp, 0xB6, salt, 0xDA]))
        surface = env.object(0xBC, "surface wrapper", fill=0)
        interface = env.object(4, "DirectDraw interface")
        vtable = env.object(0x84, "DirectDraw vtable", fill=0)
        log = env.object(64, "callback observations", fill=0)
        dest_ptr = env.object(16, "destination point", words=dest)
        rect_ptr = env.object(16, "source rectangle", words=rect)
        env.put(surface + 8, interface)
        env.put(surface + 0x1C, PITCH)
        env.put(surface + 0x30, pixels + MIDDLE)
        env.put(interface, vtable)

        def lock(env, call):
            env.put(log, env.get(log) + 1)
            env.put(log + 4, call.receiver, *call.arguments)
            env.put(surface + 0x30, pixels + MIDDLE)
            return lock_result

        def unlock(env, call):
            env.put(log + 32, env.get(log) + 1, call.receiver, *call.arguments)
            env.put(log + 52, env.get(surface + 0x30))
            return unlock_result

        env.put(vtable + 0x64, env.stub("IDirectDrawSurface::Lock", "stdcall", 5, lock))
        env.put(vtable + 0x80, env.stub("IDirectDrawSurface::Unlock", "stdcall", 2, unlock))
        return dict(image=image, dest=dest_ptr, surface=surface, rect=rect_ptr)

    return setup


def blit(label, function, random_source, rows, bpp=1, mode=1, dither=0, param=7, rect=(0, 0, W - 1, 3),
         dest=(3, 2, 77, 5), **options):
    setup = scene(random_source, function, rows, bpp, mode, dither, param, rect, dest, **options)
    return Case(label, function, setup, receiver=lambda t: t["image"],
                arguments=(lambda t: t["dest"], lambda t: t["surface"], lambda t: t["rect"]))


def rotated(k, count=5):
    return [PATTERNS[(k + i * 3) % len(PATTERNS)] for i in range(count)]


# Geometry sweeps.  Rectangles are (left, top, right, bottom).
FULL_RIGHT = tuple((left, top, W - 1, bottom)
                   for left in (0,) for top, bottom in ((0, 3), (1, 3), (2, 2), (1, 0), (0, 4)))
PARTIAL = tuple((0, top, right, bottom)
                for right in (0, 2, 3, 4, 6, 7, 8, 12) for top, bottom in ((0, 3), (1, 4)))
LEFT = tuple((left, top, right, bottom)
             for left in (1, 3, 4, 7) for right in (2, 5, 8, 11) for top, bottom in ((0, 3), (2, 4)))
DESTS = ((3, 2, 77, 5), (-2, 4, 31, 3), (5, -3, 19, 8))


def geometry_cases(random_source, function, name, bpp, mode, dither=0, param=7, step=1):
    index = 0
    for group, rects, stride in (("full", FULL_RIGHT, 1), ("partial", PARTIAL, step), ("left", LEFT, step)):
        for rect in rects[::stride]:
            index += 1
            yield blit(f"{name} {group} {rect} bpp{bpp} mode{mode}", function, random_source,
                       rotated(index), bpp=bpp, mode=mode, dither=dither, param=param, rect=rect,
                       dest=DESTS[index % len(DESTS)])


def cases(random_source):
    # Plain copies, one and two byte pixels, three geometry classes.
    for function in (F0450, F0920, F0CC0):
        for bpp in (1, 2):
            yield from geometry_cases(random_source, function, hex(function), bpp, 1, step=3)
    # Lit variants: every switch arm and the default, with and without the dither flag.
    for function in (F1190, F25B0, F3800, F4C20):
        for mode, param in ((1, 7), (2, 9), (4, 13), (8, 11), (0x16, 0xC3), (0x32, 150), (3, 5)):
            for dither in ((0, 1) if mode in (2, 4) else (0,)):
                yield from geometry_cases(random_source, function, hex(function), 1, mode, dither, param, step=9)

    # Missing lighting object: the lit variants return before touching the surface.
    for function in (F1190, F25B0, F3800, F4C20):
        yield blit(f"{function:#x} no lighting object", function, random_source, rotated(1), mode=4,
                   no_light=True, rect=(1, 0, 6, 3))
        yield blit(f"{function:#x} no lighting object, full width", function, random_source, rotated(2), mode=2,
                   no_light=True)
    # Other widths: single column, and wide runs for the word-copy loops.
    wide = (16,), (-16,), (5, -4, 7), (-6, 3, -7), (1, 15), (15, 1)
    narrow = (1,), (-1,)
    for function in (F0450, F0920, F0CC0, F1190, F25B0, F3800, F4C20):
        modes = (1,) if function in (F0450, F0920, F0CC0) else (2, 0x32)
        for mode in modes:
            for bpp in ((1, 2) if function in (F0450, F0920, F0CC0) else (1,)):
                for rect in ((0, 0, 15, 3), (3, 0, 11, 2), (6, 1, 15, 3)):
                    yield blit(f"{function:#x} wide mode{mode} bpp{bpp} {rect}", function, random_source,
                               [wide[(i + rect[0]) % len(wide)] for i in range(5)], bpp=bpp, mode=mode,
                               param=150 if mode == 0x32 else 9, rect=rect, width=16)
                for rect in ((0, 0, 0, 3),):
                    yield blit(f"{function:#x} narrow mode{mode} bpp{bpp} {rect}", function, random_source,
                               [narrow[i % 2] for i in range(5)], bpp=bpp, mode=mode, rect=rect, width=1)
    # Unlock errors are ignored by every caller.
    for function in (F0450, F0920, F0CC0, F1190, F25B0, F3800, F4C20):
        yield blit(f"{function:#x} unlock error ignored", function, random_source, rotated(4), mode=8,
                   rect=(2, 1, 6, 3), unlock_result=0x80004005)

    # The shared lighting row routine, called directly with every mode and tail length.
    def row(mode, count, param):
        stream = [random_source.randrange(1, 16) for _ in range(40)]
        backdrop = bytes(random_source.randrange(1, 16) for _ in range(64))
        table = bytes(random_source.randrange(1, 16) for _ in range(TABLE))

        def setup(env):
            tbl = env.object(TABLE, "lighting table", data=table)
            owner = env.object(16, "lighting owner", words=[0x11, 0x22, tbl, 0x33])
            image = env.object(0x30, "image", fill=0x9B)
            env.put(image + 0x14, mode, param, owner)
            env.put(image + 0x1C, owner)
            dest = env.object(64, "destination row", data=backdrop)
            src = env.object(48, "source bytes", data=bytes(stream))
            return dict(image=image, dest=dest + 40, src=src)
        return Case(f"row routine mode {mode:#x} count {count}", F5E80, setup,
                    receiver=lambda t: t["image"],
                    arguments=(lambda t: t["dest"], lambda t: t["src"], count))

    for mode, param in ((2, 0), (4, 12), (8, 17), (0x16, 0xC9), (0x32, 100), (0x32, 255), (1, 5), (3, 5), (0x17, 5)):
        for count in (0, 1, 3, 4, 5, 9, 13):
            yield row(mode, count, param)
