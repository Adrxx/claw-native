"""Cases for level_one_images_light: Level 1 closure: surface color converters, restore handler and light palette helpers."""
from clawparity.cases import Case
from clawparity.fixtures import allocate

OPERATOR_NEW = 0x4F63EC
BD0A0_POINTER = 0x54138C
SHIFT_ADDRESSES = (0x54135C, 0x541360, 0x541368, 0x54136C, 0x541370)
DEFAULT_SHIFTS = (11, 5, 3, 2, 3)
FIXED_SHIFTS = (
    DEFAULT_SHIFTS,
    (0, 0, 0, 0, 0),
    (1, 2, 3, 4, 5),
    (8, 9, 10, 11, 12),
    (15, 16, 17, 18, 19),
    (24, 25, 6, 7, 8),
    (31, 32, 33, 34, 35),
    (37, 40, 9, 8, 7),
    (3, 4, 1, 0, 2),
    (16, 8, 8, 16, 1),
)
LOST = 0x887601C2
MODES = (2, 0, 1, 3, 0x102, 0xFFFFFFFE)


def u32(value):
    return value & 0xFFFFFFFF


def put_shifts(env, shifts, high):
    for address, count, upper in zip(SHIFT_ADDRESSES, shifts, high):
        env.put(address, u32(count | (upper << 8)))


def surface_setup(random_source, width, height, pitch, bytes_per_pixel, source, palette, lock=(0,), restore=1,
                  unlock=0, shifts=DEFAULT_SHIFTS, null_surface=False):
    """A locked-surface wrapper with stand-in Lock, Unlock and restore methods; geometry is published by Lock."""
    rows = width > 0 and height > 0
    capacity = (height - 1) * pitch + width * bytes_per_pixel if rows else 1
    dest = random_source.randbytes(capacity)
    high = [random_source.randrange(0, 1 << 24) for _ in SHIFT_ADDRESSES]

    def setup(env):
        pixels = env.object(capacity, "pixels", data=dest)
        src = env.object(max(1, len(source)), "source", data=source or b"\0")
        pal = env.object(1024, "palette", data=palette) if palette is not None else 0
        wrapper = env.object(0x78, "surface", fill=0)
        vtable = env.object(0x20, "wrapper-vtable", fill=0)
        interface = env.object(4, "directdraw-surface")
        methods = env.object(0x88, "directdraw-vtable", fill=0)

        def lock_effect(env, call):
            result = lock[min(env.calls_so_far(call.function), len(lock)) - 1]
            if result == 0 and not null_surface:
                env.put(wrapper + 0x14, u32(height), u32(width), u32(pitch))
                env.put(wrapper + 0x30, pixels)
            return result

        env.put(wrapper, vtable)
        env.put(wrapper + 0x08, interface)
        env.put(wrapper + 0x14, u32(height + 2), u32(width + 3), u32(pitch + 5))
        env.put(interface, methods)
        env.put(methods + 0x64, env.stub("IDirectDrawSurface::Lock", "stdcall", 5, lock_effect))
        env.put(methods + 0x80, env.stub("IDirectDrawSurface::Unlock", "stdcall", 2, lambda env, call: unlock))
        env.put(vtable + 0x1C, env.stub("Surface::Restore", "thiscall", 0, lambda env, call: restore))
        put_shifts(env, shifts, high)
        return {"surface": wrapper, "source": src, "palette": pal}

    return setup


def converter(address, label, setup, mode, with_palette):
    arguments = [lambda t: t["source"]]
    if with_palette:
        arguments.append(lambda t: t["palette"])
    arguments.append(mode)
    return Case(label, address, setup, receiver=lambda t: t["surface"], arguments=tuple(arguments))


GEOMETRIES = ((0, 0), (0, 3), (3, 0), (-1, 2), (2, -1), (1, 1), (1, 4), (3, 1), (2, 3), (5, 4), (7, 3))
SHIFT_GEOMETRY = (3, 2)


def random_shifts(random_source):
    return tuple(random_source.randrange(0, 42) for _ in range(5))


def pixel_count(width, height):
    return max(0, width) * max(0, height)


def converter_cases(random_source, address, name, bytes_in, bytes_out, with_palette, source_words=False):
    """Shared structure for the four surface converters."""
    def sources(width, height):
        count = pixel_count(width, height)
        if source_words:
            return b"".join(random_source.randrange(65536).to_bytes(2, "little") for _ in range(count))
        return random_source.randbytes(count * bytes_in)

    def build(width, height, extra, **options):
        palette = options.pop("palette", random_source.randbytes(1024) if with_palette else None)
        source = options.pop("source", None)
        source = sources(width, height) if source is None else source
        return surface_setup(random_source, width, height, width * bytes_out + extra if width > 0 else extra,
                             bytes_out, source, palette, **options)

    for width, height in GEOMETRIES:
        for mode in (2, 0):
            yield converter(address, f"{name} {width}x{height} mode {mode}",
                            build(width, height, random_source.randrange(0, 6)), mode, with_palette)
    for mode in MODES[2:]:
        yield converter(address, f"{name} other mode {mode:#x}", build(4, 3, 3), mode, with_palette)
    yield converter(address, f"{name} overlapping rows", build(5, 3, 0), 2, with_palette)
    for index, shifts in enumerate(FIXED_SHIFTS + tuple(random_shifts(random_source) for _ in range(6))):
        width, height = SHIFT_GEOMETRY
        yield converter(address, f"{name} shifts {index}",
                        build(width, height, 1, shifts=shifts), (2, 0)[index % 2], with_palette)
        yield converter(address, f"{name} shifts {index} other mode",
                        build(width, height, 0, shifts=shifts), (0, 2)[index % 2], with_palette)
    yield converter(address, f"{name} unlock failure is ignored", build(3, 2, 2, unlock=0x80004005), 0, with_palette)
    yield converter(address, f"{name} unlock failure is ignored mode 2", build(3, 2, 2, unlock=1), 2, with_palette)
    yield converter(address, f"{name} lock fails, surface lost, restore fails",
                    build(3, 2, 2, lock=(LOST,), restore=0), 0, with_palette)
    yield converter(address, f"{name} lock fails, surface lost, restore works",
                    build(3, 2, 2, lock=(LOST, 0), restore=1), 2, with_palette)
    yield converter(address, f"{name} lock fails, surface lost, restore works, other mode",
                    build(4, 3, 1, lock=(LOST, 0), restore=1), 0, with_palette)
    yield converter(address, f"{name} lock returns no pointer",
                    build(3, 2, 2, null_surface=True), 0, with_palette)
    yield converter(address, f"{name} lock returns no pointer mode 2",
                    build(3, 2, 2, null_surface=True), 2, with_palette)
    for _ in range(4):
        width, height = random_source.randrange(1, 9), random_source.randrange(1, 6)
        yield converter(address, f"{name} random {width}x{height}",
                        build(width, height, random_source.randrange(0, 5), shifts=random_shifts(random_source)),
                        random_source.choice((2, 0)), with_palette)


def cases_4b9fa0(random_source):
    yield from converter_cases(random_source, 0x4B9FA0, "palette to 16", 1, 2, True)

    def no_palette(mode):
        def setup(env):
            tokens = surface_setup(random_source, 3, 2, 8, 2, random_source.randbytes(6), None)(env)
            return tokens
        return converter(0x4B9FA0, f"palette to 16 no palette mode {mode}", setup, mode, True)

    yield no_palette(2)
    yield no_palette(0)


def cases_4ba150(random_source):
    yield from converter_cases(random_source, 0x4BA150, "24 to 16", 3, 2, False)


def cases_4ba3f0(random_source):
    yield from converter_cases(random_source, 0x4BA3F0, "16 to 3x16", 2, 6, False, source_words=True)


def model_colour(word, shifts):
    s35c, s360, _, s36c, s370 = (s & 31 for s in shifts)
    s368 = shifts[2] & 31
    a = (((word >> s35c) & 0xFF) << s368) & 0xFF
    b = (((word >> s360) & 0xFF) << s36c) & 0xFF
    c = ((word & 0xFF) << s370) & 0xFF
    return a, b, c


def cases_4ba890(random_source):
    yield from converter_cases(random_source, 0x4BA890, "16 to indices", 2, 1, True, source_words=True)
    count = 8
    for index, shifts in enumerate((DEFAULT_SHIFTS, (0, 0, 0, 0, 0), (1, 2, 3, 4, 5), (9, 6, 2, 3, 4),
                                    random_shifts(random_source), random_shifts(random_source))):
        words = [random_source.randrange(65536) for _ in range(count)]
        palette = bytearray(random_source.randbytes(1024))
        slots = random_source.sample(range(256), count)
        for word, slot in zip(words[: 2 + index], slots):
            palette[slot * 4: slot * 4 + 3] = bytes(model_colour(word, shifts))
        source = b"".join(word.to_bytes(2, "little") for word in words)
        yield converter(0x4BA890, f"16 to indices exact matches {index}",
                        surface_setup(random_source, 4, 2, 7, 1, source, bytes(palette), shifts=shifts),
                        (2, 0)[index % 2], True)
    for kind in ("first", "last", "tie", "duplicate", "second", "middle"):
        shifts = DEFAULT_SHIFTS if kind != "middle" else (1, 2, 3, 4, 5)
        word = random_source.randrange(65536)
        a, b, c = model_colour(word, shifts)
        far = bytes(((a + 128) & 255, (b + 128) & 255, (c + 128) & 255, 7)) * 256
        palette = bytearray(far)
        if kind == "first":
            palette[0:3] = bytes((a, b, c))
        elif kind == "last":
            palette[1020:1023] = bytes((a ^ 4, b, c))
            palette[1023] = 9
        elif kind == "tie":
            sa, sb = (1 if a < 128 else -1), (1 if b < 128 else -1)
            palette[5 * 4: 5 * 4 + 3] = bytes((a + 3 * sa, b, c))
            palette[9 * 4: 9 * 4 + 3] = bytes((a, b + 3 * sb, c))
        elif kind == "duplicate":
            for slot in (7, 20, 100):
                palette[slot * 4: slot * 4 + 3] = bytes((a, b, c))
        elif kind == "second":
            palette[4:7] = bytes((a, b, c))
        else:
            for slot, delta in ((10, 30), (50, 20), (51, 20), (200, 5), (201, 6), (254, 9)):
                palette[slot * 4: slot * 4 + 3] = bytes((a ^ delta, b, c))
        source = word.to_bytes(2, "little") * 6
        for mode in (2, 0):
            yield converter(0x4BA890, f"16 to indices {kind} mode {mode}",
                            surface_setup(random_source, 3, 2, 4, 1, source, bytes(palette), shifts=shifts),
                            mode, True)

    def no_palette(mode):
        def setup(env):
            return surface_setup(random_source, 3, 2, 4, 1, random_source.randbytes(12), None)(env)
        return converter(0x4BA890, f"16 to indices no palette mode {mode}", setup, mode, True)

    yield no_palette(2)
    yield no_palette(0)


def cases_4bd0a0(random_source):
    def hook(pointer_kind, value):
        def setup(env):
            marker = env.object(16, "marker", fill=0)

            def target(env, call):
                env.put(marker, u32(call.receiver), len(call.arguments))
                return value

            env.put(BD0A0_POINTER, env.stub("global hook", "cdecl", 0, target) if pointer_kind else 0)
            return {"marker": marker}
        return setup

    for label, kind, value in (("hook returns value", True, 0x12345678), ("hook returns zero", True, 0),
                               ("hook returns random", True, random_source.randrange(1, 1 << 32)),
                               ("no hook", False, 0)):
        yield Case(f"tail call: {label}", 0x4BD0A0, hook(kind, value), receiver=random_source.randrange(1, 1 << 32))


def container_setup(random_source, kind, index, growth=0):
    """Returns a function env -> container address for a pointer array with `index` existing elements."""
    def build(env):
        this = env.object(0x18, "container", fill=0)
        env.put(this + 4, random_source.randrange(1, 1 << 32))
        if kind == "null":
            env.put(this + 0xC, index)
        elif kind == "spare":
            data = env.object(4 * (index + 8), "elements",
                              data=random_source.randbytes(4 * (index + 8)))
            env.put(this + 0x8, data, index, index + 8, growth)
        else:
            data = env.object(4 * max(index, 1), "elements", data=random_source.randbytes(4 * max(index, 1)))
            env.put(this + 0x8, data, index, max(index, 1), growth)
        return this
    return build


def bounded_new(env, call):
    size = call.arguments[0]
    return env.object(size if 0 < size <= 0x100000 else 16, name="allocation")


def light_case(random_source, label, kind, index, count, a3, a4, a5, growth=0, allocator=None):
    palette = random_source.randbytes(1024)
    high = random_source.randrange(1, 1 << 24)

    def setup(env):
        this = container_setup(random_source, kind, index, growth)(env)
        pal = env.object(1024, "palette", data=palette)
        if allocator is not None:
            env.override(OPERATOR_NEW, allocator)
        return {"this": this, "palette": pal}

    return Case(label, 0x4C68E0, setup, receiver=lambda t: t["this"],
                arguments=(lambda t: t["palette"], u32(count), u32(a3), u32(a4), u32(a5 | (high << 8))))


def cases_4c68e0(random_source):
    plan = (
        ("null", 0, 2, 100, 0, 0, 0),
        ("spare", 3, 2, 400, 1, 60, 0),
        ("grow", 5, 2, 250, -7, 0x1C3, 0),
        ("grow", 1, 1, 150, 3, 90, 4),
    )
    for number, (kind, index, count, a3, a4, a5, growth) in enumerate(plan):
        yield light_case(random_source, f"light table {number} {kind}", kind, index, count, a3, a4, a5, growth)
    for count in (0, -3, -256):
        yield light_case(random_source, f"light table count {count} writes nothing", "spare", 2, count, 120, 3, 9,
                         allocator=bounded_new)
    yield light_case(random_source, "light table count 0 grows array", "grow", 3, 0, 120, 3, 9, allocator=bounded_new)
    yield light_case(random_source, "light table object allocation fails", "null", 0, 3, 120, 3, 9,
                     allocator=allocate(fail=True))
    yield light_case(random_source, "light table buffer allocation fails", "spare", 1, 3, 120, 3, 9,
                     allocator=allocate(fail_from_call=2))


def cases(random_source):
    yield from cases_4b9fa0(random_source)
    yield from cases_4ba150(random_source)
    yield from cases_4ba3f0(random_source)
    yield from cases_4ba890(random_source)
    yield from cases_4bd0a0(random_source)
    yield from cases_4c68e0(random_source)
