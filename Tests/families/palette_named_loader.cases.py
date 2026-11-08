"""Original-driven filename, file-format, resource and factory controls."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

WRAPPER, FACTORY, DISPATCH = 0x4D6560, 0x4BCA40, 0x4BB180
BMP, PCX, PAL, EMBEDDED = 0x4BB2F0, 0x4BB470, 0x4BB620, 0x4BB740


def setup_case(rgb, name, *, fmt='resource', fail=None, status=0,
               flags=0x12345678, resource_flags=0, null_alloc=False,
               existing_tail=False, change_module=False, seek_result=137):
    def setup(env):
        env.put(0x540E88, 0)
        env.put(0x54139C, 0, 0, 0, 0)
        env.put(0x541390, 0x19302741)
        palette = env.object(0x38, 'palette', fill=0xA5)
        manager = env.object(0x400, 'manager', fill=0)
        resource = env.object(0x20, 'resource', fill=0xA6)
        context = env.object(0x20, 'context', fill=0xB7)
        filename = env.object(len(name) + 1, 'filename', data=name.encode('ascii') + b'\0')
        source = env.object(768, 'resource RGB', data=rgb)
        record = env.object(1100, 'physical API observations', fill=0)
        node = env.object(12, 'free list node', fill=0xD3)
        env.put(node, 0)
        env.put(manager + 0x3E4, node, 0, 1)
        if existing_tail:
            tail = env.object(12, 'existing list node', words=[0, 0, 0x728491A3])
            env.put(manager + 0x3D8, tail, tail, 1)
        methods = env.object(0x18, 'DirectDraw vtable', fill=0)
        directdraw = env.object(4, 'DirectDraw', words=[methods])
        opaque = env.object(4, 'created palette handle', words=[0x8392A1B4])
        env.put(manager, directdraw)
        env.put(context + 0x1C, manager)
        env.put(resource + 8, flags, context, 0xABCD1234)

        def create_palette(env, call):
            dd, passed_flags, entries, out, outer = call.arguments
            env.put(record, dd, passed_flags, out, outer,
                    env.get(resource + 8), env.get(resource + 0x10),
                    env.get(manager + 0x3E0))
            env.write(record + 32, env.read(entries, 1024))
            if not status:
                env.put(out, opaque)
            return status

        env.put(methods + 0x14, env.stub('IDirectDraw::CreatePalette', 'stdcall', 5, create_palette))

        def find(env, call):
            env.put(record + 1060, *call.arguments)
            if change_module:
                env.put(0x541390, 0x28416375)
            return 0 if fail == 'find' else 0x654321

        def load(env, call):
            env.put(record + 1072, *call.arguments)
            return 0 if fail == 'load' else 0x765432

        env.override(0x546AC8, find)
        env.override(0x546ACC, load)
        env.override(0x546AC4, returns(0 if fail == 'lock' else source))
        if null_alloc:
            env.override(0x4F63EC, allocate(fail=True))

        def copy_string(env, call):
            dst, src, bound = call.arguments
            text = env.cstr(src)
            if isinstance(text, str):
                text = text.encode('ascii')
            if bound:
                env.write(dst, text[:bound - 1] + b'\0')
            return dst

        def string_length(env, call):
            return len(env.cstr(call.arguments[0]))

        def decrement(env, call):
            address = call.arguments[0]
            value = (env.get(address) - 1) & 0xFFFFFFFF
            env.put(address, value)
            return value

        env.override(0x5469CC, copy_string)
        env.override(0x5469E4, string_length)
        env.override(0x5469E8, decrement)
        env.override(0x546B00, returns(0xFFFFFFFF if fail == 'open' else 0x789A))
        env.override(0x546AF4, returns(seek_result))
        bmp_colors = b''.join(bytes((rgb[i + 2], rgb[i + 1], rgb[i], (i // 3 * 17 + 61) & 255))
                              for i in range(0, 768, 3))
        chunks = (bytes((i * 11 + 39) & 255 for i in range(14)),
                  bytes((i * 23 + 71) & 255 for i in range(0x428)), bmp_colors) if fmt == 'bmp' else (rgb,)

        def read_file(env, call):
            index = env.calls_so_far(0x546AFC) - 1
            handle, dest, requested, actual, overlapped = call.arguments
            count = requested
            if fail == ('short', index):
                count = max(0, requested - 1)
            if fail == ('empty', index):
                count = 0
            # Extra backing supports behavior differences without fixture assertions.
            data = (chunks[min(index, len(chunks) - 1)] + bytes(4096))[:count]
            env.write(dest, data)
            env.put(actual, count)
            return 1

        env.override(0x546AFC, read_file)
        return dict(palette=palette, manager=manager, resource=resource,
                    filename=filename, directdraw=directdraw,
                    flags=flags, resource_flags=resource_flags)
    return setup


def entry(label, function, setup, *, initial_stack=()):
    if function == WRAPPER:
        return Case(label, function, setup, receiver=lambda t: t['resource'],
                    arguments=(lambda t: t['filename'], lambda t: t['resource_flags']))
    if function == FACTORY:
        return Case(label, function, setup, receiver=lambda t: t['manager'],
                    arguments=(lambda t: t['filename'], lambda t: t['flags']))
    return Case(label, function, setup, receiver=lambda t: t['palette'],
                arguments=(lambda t: t['directdraw'], lambda t: t['filename'], lambda t: t['flags']),
                initial_stack=initial_stack)


def cases(random_source):
    rgb = bytes(random_source.randrange(256) for _ in range(768))
    for function, fmt, name in ((BMP, 'bmp', 'odd-header.bmp'), (PCX, 'pcx', 'trailer.pcx'),
                                (PAL, 'pal', 'raw.pal'), (EMBEDDED, 'resource', 'RESOURCE')):
        yield entry(f'{fmt}: complete conversion', function, setup_case(rgb, name, fmt=fmt))
        yield entry(f'{fmt}: CreatePalette failure', function, setup_case(rgb, name, fmt=fmt, status=0x88760013))
        if fmt != 'resource':
            yield entry(f'{fmt}: failed open', function, setup_case(rgb, name, fmt=fmt, fail='open'))
            for index in range(3 if fmt == 'bmp' else 1):
                for kind in ('short', 'empty'):
                    yield entry(f'{fmt}: {kind} read {index}', function,
                                setup_case(rgb, name, fmt=fmt, fail=(kind, index)))
        else:
            for fail in ('find', 'load', 'lock'):
                yield entry(f'embedded: {fail} failure', function, setup_case(rgb, name, fail=fail))
    yield entry('embedded: module is reloaded after FindResource', EMBEDDED,
                setup_case(rgb, 'IDENT', change_module=True))
    for name, fmt in (('first.PAL.last.bMp', 'bmp'), ('first.BMP.last.pCx', 'pcx'),
                      ('first.PCX.last.PaL', 'pal'), ('plain', 'resource'),
                      ('first.bmp.other', 'resource'), ('empty.', 'resource'),
                      ('dir.bmp/palette', 'resource'), ('many.pcx.bmp.PAL', 'pal')):
        yield entry(f'dispatch {name}', DISPATCH, setup_case(rgb, name, fmt=fmt))
    for fail in ('find', 'load', 'lock'):
        yield entry(f'factory cleans failed {fail}', FACTORY, setup_case(rgb, 'IDENT', fail=fail))
    yield entry('factory null allocation still calls missing resource path', FACTORY,
                setup_case(rgb, 'IDENT', fail='find', null_alloc=True))
    yield entry('factory cleans allocations after COM error', FACTORY,
                setup_case(rgb, 'IDENT', status=0x887601C2))
    for tail in (False, True):
        yield entry(f'factory registers with existing tail {tail}', FACTORY,
                    setup_case(rgb, 'IDENT', existing_tail=tail))
    yield entry('wrapper clears old backend on failure and retains flags', WRAPPER,
                setup_case(rgb, 'IDENT', fail='find', flags=0xB6F052A8, resource_flags=1))
    for request in (0, 2, 1, 0xABCDEF01, 0x100):
        yield entry(f'wrapper request {request:#x}', WRAPPER,
                    setup_case(rgb, 'IDENT', flags=0xB6F052A8, resource_flags=request))
    yield entry('PCX ignores seek return offset', PCX,
                setup_case(rgb, 'trailer.pcx', fmt='pcx', seek_result=0x7FFFFFFE))

    yield entry('wrapper already has apply bit and preserves other flags', WRAPPER,
                setup_case(rgb, 'IDENT', flags=0xB6F052A9, resource_flags=1))

    for function, fmt, name, offset in ((EMBEDDED, 'resource', 'RESOURCE', -0x400),
                                        (PCX, 'pcx', 'trailer.pcx', -0x40C),
                                        (PAL, 'pal', 'raw.pal', -0x40C)):
        # Every prior alpha byte is nonzero, so omitting its zero store survives
        # through CreatePalette's recorded entries and the copied palette heap.
        scratch = bytes(random_source.randrange(1, 256) for _ in range(1024))
        yield entry(f'{fmt}: overwrite nonzero RGB0 scratch including alpha', function,
                    setup_case(rgb, name, fmt=fmt), initial_stack=((offset, scratch),))
