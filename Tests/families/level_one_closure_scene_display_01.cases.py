"""Cases for level_one_closure_scene_display_01: Level 1 closure: Scene display helpers.

The receiver is a bitmap surface wrapper: +0 vtable, +8 DirectDraw surface interface, +0xc the
surface description, +0x14 height, +0x18 width, +0x1c pitch, +0xa4 pixel depth, +0xa8 bytes per row.
The surface interface and the object's own vtable are stand-ins supplied by each case.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns  # noqa: F401

COPY_ROWS = 0x4B9B00
CLEAR = 0x4B9BD0
CREATE_SURFACE_WRAPPER = 0x4BC960
FROM_BMP_BUFFER = 0x4BDAD0
LOAD_BMP = 0x4BDC40
LOAD_RESOURCE = 0x4BE050
LOAD_PCX = 0x4BEA60
LOAD_PID = 0x4BF540
LOAD_BY_EXTENSION = 0x4BFA70

OPERATOR_NEW = 0x4F63EC
OPERATOR_DELETE = 0x4F6428
LOCK_RESOURCE = 0x546AC4
FIND_RESOURCE = 0x546AC8
LOAD_RESOURCE_API = 0x546ACC
CREATE_FILE = 0x546B00
READ_FILE = 0x546AFC
CLOSE_HANDLE = 0x546A04
GET_LAST_ERROR = 0x546B0C
SET_FILE_POINTER = 0x546AF4
GET_FULL_PATH = 0x546AD0
LSTRLEN = 0x5469E4
LSTRCPY = 0x546B10
LSTRCPYN = 0x5469CC
INTERLOCKED_DECREMENT = 0x5469E8

MODULE_HANDLE = 0x541390
LOST = 0x887601C2
FAILED = 0x80004005


def words(random_source, count, low=1, high=0xFFFFFFFF):
    return [random_source.randrange(low, high) for _ in range(count)]


def random_bytes(random_source, count):
    return bytes(random_source.randrange(1, 256) for _ in range(count))


def build_wrapper(env, *, height=3, width=4, pitch=9, rowbytes=4, depth=8, lock=(0,), restore=1,
                  create=1, pixels=None, extra=0, interface_results=None, random_source=None):
    """A wrapper object with a stand-in surface interface. Returns its tokens."""
    capacity = max(1, (max(0, height) - 1) * max(0, pitch) + max(0, rowbytes) + extra)
    surface = pixels if pixels is not None else env.object(capacity, "pixels", fill=0x5A)
    this = env.object(0x400, "wrapper", fill=0)
    vtable = env.object(0x80, "wrapper-vtable", fill=0)
    interface = env.object(4, "surface-interface")
    methods = env.object(0x90, "surface-methods", fill=0)
    results = interface_results or {}

    def lock_effect(env, call):
        n = env.calls_so_far(call.function)
        status = lock[min(n, len(lock)) - 1]
        if status == 0:
            env.put(this + 0x30, surface)
        return status

    def blit_effect(env, call):
        seq = results.get("blit", (0,))
        return seq[min(env.calls_so_far(call.function), len(seq)) - 1]

    def colorkey_effect(env, call):
        return results.get("colorkey", 0)

    restore_seq = restore if isinstance(restore, tuple) else (restore,)
    create_seq = create if isinstance(create, tuple) else (create,)

    def restore_effect(env, call):
        return restore_seq[min(env.calls_so_far(call.function), len(restore_seq)) - 1]

    def create_effect(env, call):
        return create_seq[min(env.calls_so_far(call.function), len(create_seq)) - 1]

    env.put(this, vtable)
    env.put(this + 0x08, interface)
    env.put(this + 0x14, height, width, pitch)
    env.put(this + 0xA4, depth)
    env.put(this + 0xA8, rowbytes)
    env.put(interface, methods)
    env.put(methods + 0x14, env.stub("IDirectDrawSurface::Blt", "stdcall", 6, blit_effect))
    env.put(methods + 0x64, env.stub("IDirectDrawSurface::Lock", "stdcall", 5, lock_effect))
    env.put(methods + 0x74, env.stub("IDirectDrawSurface::SetColorKey", "stdcall", 3, colorkey_effect))
    env.put(methods + 0x80, env.stub("IDirectDrawSurface::Unlock", "stdcall", 2, returns(0)))
    env.put(vtable + 0x1C, env.stub("wrapper::Restore", "thiscall", 0, restore_effect))
    env.put(vtable + 0x0C, env.stub("wrapper::CreateSurfaceSized", "thiscall", 5, create_effect))
    env.put(vtable + 0x20, env.stub("wrapper::CreateSurface", "thiscall", 1, create_effect))
    return {"this": this, "pixels": surface, "vtable": vtable, "interface": interface,
            "methods": methods, "capacity": capacity}


def call(label, function, setup, arguments=(), **options):
    return Case(label, function, setup, receiver=lambda tokens: tokens["this"], arguments=arguments, **options)


def copy_rows_cases(random_source):
    def make(height, rowbytes, pitch, mode, lock=(0,), restore=1, label=""):
        size = max(1, height * rowbytes if height > 0 and rowbytes > 0 else 1) + 8

        def setup(env):
            tokens = build_wrapper(env, height=height, pitch=pitch, rowbytes=rowbytes, lock=lock,
                                   restore=restore, random_source=random_source)
            source = env.object(2 * size + 64, "source", data=random_bytes(random_source, 2 * size + 64))
            tokens["source"] = source + size // 2 + 16
            return tokens

        return call(f"copy rows h{height} bytes{rowbytes} pitch{pitch} mode{mode}{label}", COPY_ROWS, setup,
                    (lambda t: t["source"], mode))

    for mode in (0, 2, 3):
        for height in (-1, 0, 1, 2, 5):
            for rowbytes in (0, 1, 3, 8):
                yield make(height, rowbytes, rowbytes + 5, mode)
    yield make(3, 4, 2, 2, label=" overlapping")
    yield make(4, 5, 5, 1, label=" tight")
    yield make(4, -2, 9, 0, label=" negative width")
    yield make(4, -2, 9, 2, label=" negative width")
    for mode in (0, 2):
        height, rowbytes = random_source.randrange(2, 9), random_source.randrange(1, 17)
        yield make(height, rowbytes, rowbytes + random_source.randrange(0, 6), mode, label=" random")
    yield make(3, 4, 9, 2, lock=(FAILED,), label=" lock error")
    yield make(3, 4, 9, 0, lock=(LOST,), restore=0, label=" lost, restore fails")
    yield make(3, 4, 9, 2, lock=(LOST, 0), restore=1, label=" lost, restored")
    yield make(3, 4, 9, 0, lock=(LOST, FAILED), restore=1, label=" lost, restored, fails again")
    yield make(3, 4, 9, 2, lock=(LOST, LOST), restore=(1, 0), label=" lost twice")


def clear_cases(random_source):
    for flag in (0, 1, 7, 0x80000000):
        for blit in ((0,), (FAILED,), (1, 0), (1, FAILED), (1, LOST), (LOST,)):
            for restore in (0, 1):
                if (len(blit) == 1 or blit[-1] == LOST) and restore:
                    continue  # the original dereferences a null argument when it retries after a lost surface

                def setup(env, blit=blit, restore=restore):
                    return build_wrapper(env, restore=restore, interface_results={"blit": blit})

                yield call(f"clear flag {flag:#x} blit {blit} restore {restore}", CLEAR, setup, (flag,))


def cases(random_source):
    yield from copy_rows_cases(random_source)
    yield from clear_cases(random_source)


def resource_blob(random_source, height, width, header=0x28, bits=8):
    """A DIB resource: header size, width, height, bit count at +0xe, a 256 entry palette, then pixels."""
    pixels = random_bytes(random_source, max(1, height) * max(1, width) + 4)
    head = bytearray(random_bytes(random_source, header))
    head[0:4] = header.to_bytes(4, "little")
    head[4:8] = width.to_bytes(4, "little")
    head[8:12] = height.to_bytes(4, "little")
    head[0xE:0x10] = bits.to_bytes(2, "little")
    return bytes(head) + random_bytes(random_source, 0x400) + pixels


def script_resource(env, blob, *, find=True, load=True, lock=True, module=None):
    """Script the three resource imports; returns the blob address."""
    address = env.object(len(blob), "resource", data=blob)
    env.put(MODULE_HANDLE, module if module is not None else 0x00400000)
    env.override(FIND_RESOURCE, returns(0x7001 if find else 0))
    env.override(LOAD_RESOURCE_API, returns(0x7002 if load else 0))
    env.override(LOCK_RESOURCE, returns(address if lock else 0))
    return address


def cstring(env, text, name="name"):
    return env.object(len(text) + 1, name, data=text.encode() + b"\0")


def resource_cases(random_source):
    def make(label, *, height=3, width=6, header=0x28, bits=8, find=True, load=True, lock=True, create=1,
             lock_status=(0,), flags=None, name="TITLE"):
        flags = random_source.randrange(0, 1 << 32) if flags is None else flags

        def setup(env):
            tokens = build_wrapper(env, height=height, width=width, rowbytes=width, pitch=width + 3,
                                   create=create, lock=lock_status)
            tokens["blob"] = script_resource(env, resource_blob(random_source, height, width, header, bits),
                                             find=find, load=load, lock=lock)
            tokens["name"] = cstring(env, name)
            tokens["display"] = env.object(0x900, "display", fill=0)
            return tokens

        return call(label, LOAD_RESOURCE, setup, (lambda t: t["display"], lambda t: t["name"], flags))

    yield make("resource not found", find=False)
    yield make("resource not loaded", load=False)
    yield make("resource not locked", lock=False)
    for bits in (0, 1, 4, 24, 0x108):
        yield make(f"resource bit count {bits}", bits=bits)
    yield make("resource surface creation fails", create=0)
    for height, width, header in ((1, 1, 0x28), (2, 5, 0x28), (3, 6, 0x2C), (5, 9, 0x28), (4, 16, 0x30)):
        yield make(f"resource {width}x{height} header {header:#x}", height=height, width=width, header=header)
    yield make("resource lock fails", lock_status=(FAILED,))
    yield make("resource lock lost, restore fails", lock_status=(LOST,), create=1)
    yield make("resource flags only 0x40", flags=0)
    yield make("resource flags all", flags=0xFFFFFFFF)
    for _ in range(3):
        yield make("resource random", height=random_source.randrange(1, 7), width=random_source.randrange(1, 20))
    yield make("resource id as name", name="")


def display_object(env, random_source, depth, paletted):
    """The display the surface is created for: +0x474 pixel depth, +0x478 palette, +0x878 palette flag."""
    display = env.object(0x900, "display", fill=0)
    env.put(display + 0x474, depth)
    env.put(display + 0x878, paletted)
    env.write(display + 0x478, random_bytes(random_source, 0x400))
    return display


def bmp_image(random_source, width, height, bpp, offset=None):
    """A BMP file image: pixel offset at +0xa, width at +0x12, height at +0x16, bit count at +0x1c, palette at +0x36."""
    offset = (0x436 if bpp == 8 else 0x36) if offset is None else offset
    rowbytes = (width * bpp // 8 + 3) & ~3
    data = bytearray(random_bytes(random_source, offset + rowbytes * max(height, 1) + 64))
    data[0:2] = b"BM"
    data[0x0A:0x0E] = offset.to_bytes(4, "little")
    data[0x12:0x16] = width.to_bytes(4, "little", signed=True)
    data[0x16:0x1A] = height.to_bytes(4, "little", signed=True)
    data[0x1C:0x1E] = bpp.to_bytes(2, "little")
    return bytes(data)


def bmp_buffer_cases(random_source):
    def make(label, *, bpp, display_depth, paletted=0, surface_depth=None, width=5, height=3, create=1,
             lock=(0,), flags=None, offset=None, restore=1):
        flags = random_source.randrange(0, 1 << 32) if flags is None else flags
        surface_depth = display_depth if surface_depth is None else surface_depth

        def setup(env):
            tokens = build_wrapper(env, height=height, width=width, depth=surface_depth,
                                   rowbytes=width * max(1, surface_depth // 8), pitch=width * 4 + 8, create=create,
                                   lock=lock, restore=restore, extra=96)
            tokens["display"] = display_object(env, random_source, display_depth, paletted)
            tokens["bmp"] = env.object(0x440 + (width * 3 + 4) * height + 128, "bmp",
                                       data=bmp_image(random_source, width, height, bpp, offset))
            return tokens

        return call(label, FROM_BMP_BUFFER, setup,
                    (lambda t: t["display"], lambda t: t["bmp"], random_source.randrange(1, 1 << 32), flags))

    for bpp in (0, 1, 4, 16, 32, 0x108):
        yield make(f"bmp bit count {bpp} refused", bpp=bpp, display_depth=8)
    for bpp in (8, 24):
        for width, height in ((1, 1), (4, 2), (5, 3), (7, 4)):
            yield make(f"bmp {bpp} bit same depth {width}x{height}", bpp=bpp, display_depth=bpp, width=width, height=height)
        yield make(f"bmp {bpp} bit same depth, creation fails", bpp=bpp, display_depth=bpp, create=0)
        yield make(f"bmp {bpp} bit same depth, lock fails", bpp=bpp, display_depth=bpp, lock=(FAILED,))
        yield make(f"bmp {bpp} bit same depth, lost surface", bpp=bpp, display_depth=bpp, lock=(LOST,), restore=0)
    yield make("bmp 24 bit on 8 bit display without palette", bpp=24, display_depth=8, paletted=0)
    yield make("bmp 24 bit on 8 bit display without palette, creation would fail", bpp=24, display_depth=8, create=0)
    for display_depth, surface_depth, bpp in ((16, 16, 8), (24, 24, 8), (16, 16, 24), (24, 24, 16), (32, 32, 8),
                                              (32, 32, 24), (8, 8, 24), (16, 8, 8), (24, 16, 24)):
        for paletted in (0, 1):
            if display_depth == 8 and not paletted:
                continue
            yield make(f"bmp {bpp} bit on {display_depth} bit display {surface_depth}, palette {paletted}",
                       bpp=bpp, display_depth=display_depth, paletted=paletted, surface_depth=surface_depth)
    yield make("bmp 8 bit on 16 bit display, creation fails", bpp=8, display_depth=16, create=0)
    yield make("bmp 24 bit on 8 bit display, creation fails", bpp=24, display_depth=8, paletted=1, create=0)
    yield make("bmp 8 bit on 24 bit display, conversion refused", bpp=8, display_depth=24, surface_depth=5)
    yield make("bmp 8 bit on 24 bit display, wide", bpp=8, display_depth=24, width=11, height=5)
    yield make("bmp 24 bit on 8 bit display, wide", bpp=24, display_depth=8, paletted=1, width=9, height=2)
    yield make("bmp 8 bit pixel offset moved", bpp=8, display_depth=8, offset=0x440)
    for _ in range(3):
        bpp = random_source.choice((8, 24))
        yield make("bmp random", bpp=bpp, display_depth=random_source.choice((8, 16, 24, 32)) if bpp == 24 else 16,
                   paletted=1, width=random_source.randrange(1, 12), height=random_source.randrange(1, 6))


def script_strings(env):
    """The string imports the file wrapper uses to remember its path."""
    def copy_limited(env, call):
        destination, source, limit = call.arguments
        text = env.cstr(source)[:max(limit - 1, 0)] if limit > 0 else b""
        env.write(destination, text + b"\0")
        return destination

    def copy(env, call):
        destination, source = call.arguments
        env.write(destination, env.cstr(source) + b"\0")
        return destination

    def decrement(env, call):
        value = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
        env.put(call.arguments[0], value)
        return value

    env.override(INTERLOCKED_DECREMENT, decrement)
    env.override(GET_FULL_PATH, returns(0))
    env.override(LSTRCPYN, copy_limited)
    env.override(LSTRCPY, copy)
    env.override(LSTRLEN, lambda env, call: len(env.cstr(call.arguments[0])))


def file_open_failure_cases(random_source):
    """The three file loaders when CreateFileA fails: the only path that does not seek."""
    for function, label, arity in ((LOAD_BMP, "bmp", 3), (LOAD_PCX, "pcx", 3), (LOAD_PID, "pid", 4)):
        for error in (0x2, 0x3, 0x20):
            def setup(env, error=error):
                tokens = build_wrapper(env)
                tokens["display"] = display_object(env, random_source, 16, 0)
                tokens["path"] = cstring(env, "ART\\LEVEL%d.%s" % (error, label.upper()), "path")
                script_strings(env)
                env.override(CREATE_FILE, returns(0xFFFFFFFF))
                env.override(GET_LAST_ERROR, returns(error))
                return tokens

            args = [lambda t: t["display"], lambda t: t["path"], random_source.randrange(0, 1 << 32)]
            if arity == 4:
                args.append(random_source.randrange(0, 255))
            yield call(f"{label} open fails with {error}", function, setup, tuple(args))


def dispatcher_cases(random_source):
    def make(label, name, *, key, find=True, lock=True, bits=8, create=1, flags=None, colorkey=0,
             height=3, width=6, open_error=2):
        flags = random_source.randrange(0, 1 << 32) if flags is None else flags

        def setup(env):
            tokens = build_wrapper(env, height=height, width=width, rowbytes=width, pitch=width + 3, create=create,
                                   interface_results={"colorkey": colorkey})
            tokens["display"] = display_object(env, random_source, 16, 0)
            tokens["path"] = cstring(env, name, "path")
            tokens["blob"] = script_resource(env, resource_blob(random_source, height, width, 0x28, bits),
                                             find=find, lock=lock)
            script_strings(env)
            env.override(CREATE_FILE, returns(0xFFFFFFFF))
            env.override(GET_LAST_ERROR, returns(open_error))
            return tokens

        return call(label, LOAD_BY_EXTENSION, setup, (lambda t: t["display"], lambda t: t["path"], flags, key))

    for name in ("TITLE", "ART\\TITLE", "", "A.B\\TITLE", "x.", "x.bmpx", "x.pc", "x.pidd", "x.png", "x.BM", "x.PCX1",
                 "ART\\LEVEL1.XYZ"):
        yield make(f"unknown extension {name!r} resource found", name, key=-1)
        yield make(f"unknown extension {name!r} resource found, key", name, key=0x1F)
    for name in ("TITLE", "x.zzz", "x.pidd"):
        yield make(f"resource {name!r} not found", name, key=3, find=False)
        yield make(f"resource {name!r} not locked", name, key=-1, lock=False)
        yield make(f"resource {name!r} wrong depth", name, key=7, bits=24)
    for key in (0, 1, 0xFF, 0x7FFFFFFF, 0x80000000, -2 & 0xFFFFFFFF):
        yield make(f"resource colour key {key:#x}", "BACK", key=key)
    yield make("resource colour key fails", "BACK", key=9, colorkey=FAILED)
    yield make("resource creation fails with key", "BACK", key=9, create=0)
    for name in ("a.bmp", "A.BMP", "dir.v2\\a.BmP", "a.Bmp", "x.png.bmp"):
        yield make(f"bmp extension {name!r} open fails", name, key=-1, open_error=3)
        yield make(f"bmp extension {name!r} open fails, key", name, key=6, open_error=5)
    for name in ("a.pcx", "A.PCX", "a.b.pCx", "a.Pcx"):
        yield make(f"pcx extension {name!r} open fails", name, key=-1)
        yield make(f"pcx extension {name!r} open fails, key", name, key=6)
    for name in ("a.pid", "A.PID", "a.b.pId", "a.Pid"):
        yield make(f"pid extension {name!r} open fails", name, key=-1)
        yield make(f"pid extension {name!r} open fails, key", name, key=6)
    for _ in range(3):
        name = random_source.choice(("r.bmp", "r.pcx", "r.pid", "r.dat", "r"))
        yield make(f"random {name}", name, key=random_source.randrange(-1, 256), flags=random_source.randrange(0, 1 << 32))


def create_wrapper_cases(random_source):
    """4bc960 builds a new surface wrapper; with no DirectDraw object the creation is refused and it is freed."""
    for count in range(6):
        def setup(env):
            manager = env.object(0x400, "manager", fill=0)
            env.write(manager + 0x3B8, random_bytes(random_source, 0x40))
            env.put(manager, 0)
            display = display_object(env, random_source, 16, 0)
            env.put(display, 0)
            return {"this": manager, "display": display}

        yield call(f"create wrapper refused {count}", CREATE_SURFACE_WRAPPER, setup,
                   (lambda t: t["display"], random_source.randrange(1, 641), random_source.randrange(1, 481),
                    random_source.randrange(0, 1 << 32), random_source.randrange(0, 1 << 32)))


def create_wrapper_success_cases(random_source):
    """4bc960 with a stand-in DirectDraw object that creates the surface."""
    def make(label, *, depth=16, create_status=0, key=0xFFFFFFFF, flags=None, width=None, height=None, colorkey=0):
        width = random_source.randrange(2, 64) if width is None else width
        height = random_source.randrange(2, 48) if height is None else height
        flags = random_source.randrange(0, 1 << 32) if flags is None else flags

        def setup(env):
            manager = env.object(0x400, "manager", fill=0)
            env.put(manager + 0x3B8 + 0x18, 10)  # the surface list block size
            display = display_object(env, random_source, depth, 0)
            directdraw = env.object(4, "directdraw")
            methods = env.object(0x80, "directdraw-methods", fill=0)
            surface = env.object(4, "new-surface")
            surface_methods = env.object(0x90, "new-surface-methods", fill=0)
            pitch = random_source.randrange(width, 4 * width + 9)

            def describe(env, call):
                desc = call.arguments[1]
                env.put(desc + 0x10, pitch)
                env.put(desc + 0x54, depth)
                return 0

            def create(env, call):
                if create_status == 0:
                    env.put(call.arguments[2], surface)
                return create_status

            env.put(surface, surface_methods)
            env.put(surface_methods + 0x58, env.stub("IDirectDrawSurface::GetSurfaceDesc", "stdcall", 2, describe))
            env.put(surface_methods + 0x74, env.stub("IDirectDrawSurface::SetColorKey", "stdcall", 3,
                                                     returns(colorkey)))
            env.put(display, directdraw)
            env.put(directdraw, methods)
            env.put(methods + 0x18, env.stub("IDirectDraw::CreateSurface", "stdcall", 4, create))
            return {"this": manager, "display": display, "width": width, "height": height}

        return call(label, CREATE_SURFACE_WRAPPER, setup,
                    (lambda t: t["display"], lambda t: t["width"], lambda t: t["height"], flags, key))

    for depth in (8, 16, 24, 32, 12, 40):
        yield make(f"create wrapper depth {depth}", depth=depth)
    yield make("create wrapper with colour key", key=0x1234)
    yield make("create wrapper colour key fails", key=0, colorkey=FAILED)
    yield make("create wrapper creation fails", create_status=FAILED)
    yield make("create wrapper flags zero", flags=0)
    yield make("create wrapper flags all", flags=0xFFFFFFFF)
    for _ in range(3):
        yield make("create wrapper random", depth=random_source.choice((8, 16, 24, 32)),
                   key=random_source.choice((0xFFFFFFFF, random_source.randrange(0, 256))))


def script_file(env, data, *, handle=0x1234, short_by=0, length=None):
    """Script a readable file: CreateFileA, SetFilePointer, ReadFile and the close that follows."""
    size = len(data) if length is None else length

    def seek(env, call):
        _handle, distance, _high, method = call.arguments
        return {0: distance, 1: 0, 2: size}[method]

    def read(env, call):
        _handle, buffer, count, done, _overlapped = call.arguments
        got = max(0, min(count, len(data)) - short_by)
        env.write(buffer, data[:got])
        env.put(done, got)
        return 1

    script_strings(env)
    env.override(CREATE_FILE, returns(handle))
    env.override(SET_FILE_POINTER, seek)
    env.override(READ_FILE, read)
    env.override(CLOSE_HANDLE, returns(1))


def pcx_image(random_source, width, height, planes, extra=16):
    """A PCX file: window shorts at +4..+0xa, plane count at +0x41, literal pixels at +0x80, palette last."""
    data = bytearray(random_bytes(random_source, 0x80))
    data[4:12] = ((0).to_bytes(2, "little") + (0).to_bytes(2, "little") +
                  (width - 1).to_bytes(2, "little", signed=True) + (height - 1).to_bytes(2, "little", signed=True))
    data[0x41] = planes
    literal = bytes(random_source.randrange(1, 0xC0) for _ in range(width * height * planes + extra))
    return bytes(data) + literal + random_bytes(random_source, 0x300)


def pid_image(random_source, width, height, flags, extra=16):
    """A PID file: flags at +4, width at +8, height at +0xc, pixels at +0x20, palette last."""
    data = bytearray(random_bytes(random_source, 0x20))
    data[4:8] = flags.to_bytes(4, "little")
    data[8:12] = width.to_bytes(4, "little")
    data[12:16] = height.to_bytes(4, "little")
    literal = bytes(random_source.randrange(1, 0xC0) for _ in range(width * height + extra))
    return bytes(data) + literal + random_bytes(random_source, 0x300)


def file_loader(random_source, function, label, data, *, display_depth, paletted=0, surface_depth=None, width=8,
                height=3, create=1, lock=(0,), key=None, refuse_size=None, **file_options):
    """A case for one file loader: wrapper, display and a scripted file holding `data`."""
    surface_depth = display_depth if surface_depth is None else surface_depth
    flags = random_source.randrange(0, 1 << 32)

    def setup(env):
        tokens = build_wrapper(env, height=height, width=width, depth=surface_depth,
                               rowbytes=width * max(1, surface_depth // 8), pitch=width * 4 + 8, create=create,
                               lock=lock, extra=256)
        tokens["display"] = display_object(env, random_source, display_depth, paletted)
        tokens["path"] = cstring(env, "ART\\IMAGE.DAT", "path")
        script_file(env, data, **file_options)
        if refuse_size is not None:
            refused = refuse_size(len(data), width, height)

            def refuse(env, call):
                if call.arguments[0] == refused:
                    return 0
                return env.object(call.arguments[0], name="allocation")

            env.override(OPERATOR_NEW, refuse)
        return tokens

    arguments = [lambda t: t["display"], lambda t: t["path"], flags]
    if key is not None:
        arguments.append(key)
    return call(label, function, setup, tuple(arguments))


def bmp_file_cases(random_source):
    def make(label, bpp, display_depth, **options):
        width, height = options.pop("width", 5), options.pop("height", 3)
        data = bmp_image(random_source, width, height, bpp)
        if options.pop("odd_length", False):
            options["length"] = len(data) - 7
        return file_loader(random_source, LOAD_BMP, label, data, display_depth=display_depth, width=width,
                           height=height, **options)

    for bpp in (8, 24):
        yield make(f"bmp file {bpp} bit same depth", bpp, bpp)
    yield make("bmp file 8 bit on 16 bit", 8, 16)
    yield make("bmp file 24 bit on 32 bit", 24, 32)
    yield make("bmp file 24 bit on 8 bit", 24, 8, paletted=1)
    yield make("bmp file 24 bit on 8 bit unpaletted", 24, 8)
    yield make("bmp file 4 bit refused", 4, 8)
    yield make("bmp file creation fails", 8, 8, create=0)
    yield make("bmp file lock fails", 8, 8, lock=(FAILED,))
    yield make("bmp file empty", 8, 8, length=0)
    yield make("bmp file short read", 8, 8, short_by=1)
    yield make("bmp file short read by many", 8, 8, short_by=300)
    yield make("bmp file buffer allocation fails", 8, 8, refuse_size=lambda size, w, h: size)
    yield make("bmp file length differs from data", 8, 8, odd_length=True)
    yield make("bmp file random", random_source.choice((8, 24)), 24, width=random_source.randrange(1, 12),
               height=random_source.randrange(1, 5))


def pcx_file_cases(random_source):
    def make(label, planes, display_depth, **options):
        width, height = options.pop("width", 6), options.pop("height", 3)
        data = pcx_image(random_source, width, height, planes)
        return file_loader(random_source, LOAD_PCX, label, data, display_depth=display_depth, width=width,
                           height=height, **options)

    yield make("pcx 8 bit same depth", 1, 8)
    yield make("pcx 24 bit same depth", 3, 24)
    yield make("pcx 8 bit on 16 bit", 1, 16)
    yield make("pcx 8 bit on 24 bit", 1, 24)
    yield make("pcx 24 bit on 16 bit", 3, 16)
    yield make("pcx 24 bit on 8 bit palette", 3, 8, paletted=1)
    yield make("pcx 24 bit on 8 bit no palette", 3, 8)
    yield make("pcx 8 bit on 16 bit odd width", 1, 16, width=5)
    yield make("pcx 24 bit on 16 bit odd width", 3, 16, width=5)
    yield make("pcx bad planes", 2, 16)
    yield make("pcx creation fails", 1, 8, create=0)
    yield make("pcx creation fails converted", 1, 16, create=0)
    yield make("pcx conversion refused", 1, 16, surface_depth=5)
    yield make("pcx 24 bit conversion refused", 3, 16, surface_depth=5)
    yield make("pcx empty", 1, 8, length=0)
    yield make("pcx short read", 1, 8, short_by=2)
    yield make("pcx lock fails", 1, 8, lock=(FAILED,))
    yield make("pcx lock fails converted", 1, 16, lock=(FAILED,))
    yield make("pcx scratch allocation fails", 1, 16, refuse_size=lambda size, w, h: w * h)
    yield make("pcx file buffer allocation fails", 1, 8, refuse_size=lambda size, w, h: size)
    yield make("pcx random", random_source.choice((1, 3)), 16, width=2 * random_source.randrange(1, 6),
               height=random_source.randrange(1, 4))


def pid_file_cases(random_source):
    def make(label, pid_flags, display_depth, **options):
        width, height = options.pop("width", 8), options.pop("height", 3)
        data = pid_image(random_source, width, height, pid_flags)
        key = options.pop("key", random_source.randrange(0, 256))
        return file_loader(random_source, LOAD_PID, label, data, display_depth=display_depth, width=width,
                           height=height, key=key, **options)

    for pid_flags in (0, 1, 2, 4, 5, 6, 3):
        yield make(f"pid flags {pid_flags:#x} same depth", pid_flags, 8)
    for pid_flags in (0x80, 0x81, 0x84, 0x86):
        yield make(f"pid flags {pid_flags:#x} on 16 bit", pid_flags, 16)
    yield make("pid flags 0x80 on 8 bit", 0x80, 8)
    yield make("pid flags 0 on 16 bit with display palette", 0, 16, paletted=1)
    yield make("pid flags 1 on 24 bit with display palette", 1, 24, paletted=1)
    yield make("pid flags 0 on 16 bit without palette", 0, 16)
    yield make("pid width not multiple of 4", 0, 8, width=6)
    yield make("pid width 4", 0, 8, width=4, height=1)
    yield make("pid creation fails", 0, 8, create=0)
    yield make("pid creation fails converted", 0x80, 16, create=0)
    yield make("pid conversion refused", 0x81, 16, surface_depth=5)
    yield make("pid lock fails", 0, 8, lock=(FAILED,))
    yield make("pid lock fails converted", 0x80, 16, lock=(FAILED,))
    yield make("pid short read", 0, 8, short_by=3)
    yield make("pid short file with palette", 0x80, 16, length=0x2F0)
    yield make("pid scratch allocation fails", 0x80, 16, refuse_size=lambda size, w, h: w * h)
    yield make("pid file buffer allocation fails", 0, 8, refuse_size=lambda size, w, h: size)
    yield make("pid random", random_source.choice((0, 1, 0x80, 0x81)), random_source.choice((8, 16)),
               width=4 * random_source.randrange(1, 4), height=random_source.randrange(1, 4))


def dispatcher_file_cases(random_source):
    """4bfa70 with a readable file behind each extension."""
    def make(label, name, data, *, key, display_depth=8, width=8, height=3, **options):
        def setup(env):
            tokens = build_wrapper(env, height=height, width=width, depth=display_depth,
                                   rowbytes=width * max(1, display_depth // 8), pitch=width * 4 + 8, extra=256,
                                   **options)
            tokens["display"] = display_object(env, random_source, display_depth, 0)
            tokens["path"] = cstring(env, name, "path")
            script_file(env, data)
            return tokens

        return call(label, LOAD_BY_EXTENSION, setup,
                    (lambda t: t["display"], lambda t: t["path"], random_source.randrange(0, 1 << 32), key))

    for key in (-1 & 0xFFFFFFFF, 0, 0x55):
        yield make(f"dispatch bmp file key {key:#x}", "ART\\a.bmp", bmp_image(random_source, 8, 3, 8), key=key,
                   width=8)
        yield make(f"dispatch pcx file key {key:#x}", "ART\\a.PCX", pcx_image(random_source, 8, 3, 1), key=key)
        for pid_flags in (0, 1):
            yield make(f"dispatch pid file key {key:#x} flags {pid_flags}", "ART\\a.Pid",
                       pid_image(random_source, 8, 3, pid_flags), key=key)
    yield make("dispatch bmp file refused", "a.bmp", bmp_image(random_source, 4, 3, 4), key=3)
    yield make("dispatch pcx file refused", "a.pcx", pcx_image(random_source, 8, 3, 2), key=3)
    yield make("dispatch pid file refused", "a.pid", pid_image(random_source, 6, 3, 0), key=3)


def cases(random_source):  # noqa: F811
    yield from copy_rows_cases(random_source)
    yield from clear_cases(random_source)
    yield from resource_cases(random_source)
    yield from bmp_buffer_cases(random_source)
    yield from file_open_failure_cases(random_source)
    yield from dispatcher_cases(random_source)
    yield from create_wrapper_cases(random_source)
    yield from create_wrapper_success_cases(random_source)
    yield from bmp_file_cases(random_source)
    yield from pcx_file_cases(random_source)
    yield from pid_file_cases(random_source)
    yield from dispatcher_file_cases(random_source)
