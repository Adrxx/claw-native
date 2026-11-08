"""Original popup templates and physical Windows geometry inputs."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

CONSTRUCT, INITIALIZE, NARROW, PARSE, FONTS, GEOMETRY = (
    0x4E1B20, 0x4E2090, 0x4E2160, 0x4E21A0, 0x4E25E0, 0x4E2670)


def word(value):
    return struct.pack('<H', value & 0xffff)


def resource_string(value):
    if isinstance(value, int):
        return word(0xffff) + word(value)
    if isinstance(value, bytes):
        return value
    return value.encode('utf-16le') + b'\0\0'


def template(style=0x10c00000, menu='', cls='', title='', font=None,
             items=(), width=153, height=97, tail=b''):
    if font is not None:
        style |= 0x40
    result = struct.pack('<IIHhhhh', style, 0x10204080, len(items), -7, 13, width, height)
    result += resource_string(menu) + resource_string(cls) + resource_string(title)
    if font is not None:
        result += word(font[0]) + resource_string(font[1])
    for index, item in enumerate(items):
        result += bytes([0xa7]) * (-len(result) % 4)
        kind, caption, extra, geometry, item_style = item
        result += struct.pack('<IIhhhhH', item_style, 0x31415900 + index,
                              *geometry, 0x8100 + index)
        result += resource_string(kind) + resource_string(caption)
        result += word(0 if extra is None else len(extra) + 2)
        if extra is not None:
            result += extra
    return result + tail


def item(kind=0x80, caption='Control', extra=None,
         geometry=(-3, 7, 19, 11), style=0x50010001):
    return kind, caption, extra, geometry, style


def physical(env, popup, data, *, resource_failure=None, create=1, thread=True,
             stock=(0x7101, 0x7102), metrics=(5, 7, 23),
             rect=(-37, 91, 404, 358), font_create=0x7301,
             attach_fail=0, cursor=0x7401, zero_allocation=False):
    resource = env.object(len(data), 'resource-template', data=data)
    thread_object = env.object(0x84, 'physical-thread')
    thread_vtable = env.object(0x80, 'physical-thread-vtable')
    parent_window = env.object(0x60, 'physical-parent-window')
    env.put(thread_object, thread_vtable)
    env.put(thread_vtable + 0x7c,
            env.stub('physical-thread-main-window', 'thiscall', 0, returns(parent_window)))
    env.override(0x4FB7D8, returns(thread_object if thread else 0))
    for address, result in ((0x546AC8, 0x6101), (0x546ACC, 0x6102), (0x546AC4, resource)):
        env.override(address, returns(0 if address == resource_failure else result))
    env.override(0x546A54, returns(len(data)))
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))

    def set_rect(e, c):
        e.put(c.arguments[0], *c.arguments[1:])
        return 1

    def offset_rect(e, c):
        address, x, y = c.arguments
        e.put(address, *(e.get(address + n * 4) + (x if n % 2 == 0 else y)
                         for n in range(4)))
        return 1

    def empty_rect(e, c):
        e.put(c.arguments[0], 0, 0, 0, 0)
        return 1

    def window_rect(e, c):
        e.put(c.arguments[1], *rect)
        return 1

    def create_dialog(e, c):
        if create:
            e.put(c.receiver + 0x1c, 0x6201)
        return create

    def delete_handle(e, c):
        e.put(c.receiver + 4, 0)
        if c.function == 0x4FD067:
            e.put(c.receiver + 8, 0)
        return 1

    def attach(e, c):
        if c.function == 0x4FCFFF and attach_fail and e.calls_so_far(c.function) == attach_fail:
            return 0
        e.put(c.receiver + 4, c.arguments[0])
        if c.function == 0x4FCFFF:
            e.put(c.receiver + 8, c.arguments[0])
        return int(c.arguments[0] != 0)

    def ncm(e, c):
        # cbSize stays as received; real NONCLIENTMETRICS output has distinct fields.
        e.put(c.arguments[2] + 4, 3, 17, 19, 21, 25)
        return 1

    env.override(0x546CDC, empty_rect)
    env.override(0x546D5C, set_rect)
    env.override(0x546B7C, offset_rect)
    env.override(0x546CC0, window_rect)
    env.override(0x546D04, ncm)
    env.override(0x4F7B4E, create_dialog)
    env.override(0x4F8F44, returns(1))
    env.override(0x4F7B10, returns(0))
    env.override(0x546C44, lambda e, c: {7: metrics[0], 8: metrics[1], 4: metrics[2]}[c.arguments[0]])
    env.override(0x5468BC, sequence(*stock))
    env.override(0x4FD732, delete_handle)
    env.override(0x4FD067, delete_handle)
    env.override(0x4FCFFF, attach)
    env.override(0x4FD6DB, attach)
    previous = env.object(8, 'previous-gdi-object', words=[0x5141a8, 0x7321])
    env.override(0x4FD150, returns(previous))
    env.override(0x54687C, returns(0x7501))
    env.override(0x54690C, returns(0x7601))
    env.override(0x546870, returns(1))
    env.override(0x546B60, returns(cursor))
    dc = env.object(16, 'physical-window-dc', words=[0x510444, 0x7701, 0x7701, 0])
    def dc_from_handle(e, c):
        e.put(dc + 4, c.arguments[0], c.arguments[0])
        return dc if c.arguments[0] else 0
    env.override(0x4FCFE9, dc_from_handle)
    env.override(0x4FD6C5, returns(previous))
    env.override(0x546D20, lambda e, c: 0x102030 + c.arguments[0] * 0x030201)
    env.override(0x54689C, returns(1))
    env.override(0x5468F0, lambda e, c: 0x8100 + e.calls_so_far(c.function))
    env.override(0x5468EC, lambda e, c: 0x8200 + e.calls_so_far(c.function))
    env.override(0x54691C, returns(0x8301))
    def move_to(e, c):
        if c.arguments[3]:
            e.put(c.arguments[3], 13, 29)
        return 1
    env.override(0x5468E4, move_to)
    env.override(0x5468E8, returns(1))

    def copy_string(e, c):
        destination, source, count = c.arguments
        if count:
            e.write(destination, e.cstr(source)[:count - 1] + b'\0')
        return destination

    env.override(0x5469CC, copy_string)
    env.override(0x546C7C, returns(0x7701))
    env.override(0x546894, returns(96))
    env.override(0x5468AC, returns(1))
    env.override(0x546C80, returns(1))
    env.override(0x5468A8, returns(font_create))
    if zero_allocation:
        def allocate(e, c):
            return 0 if c.arguments[0] == 0 else e.object(c.arguments[0], 'allocation')
        env.override(0x4F63EC, allocate)
    return resource


def setup_popup(data, *, fill=0xa6, face=None, geometry_items=(), style=None,
                width=153, height=97, cursor_enabled=0, cursor_count=0,
                cursor_callback=None, old_fields=False, **options):
    def setup(env):
        popup = env.object(0x278, 'popup', fill=fill)
        # Supply a previously constructed receiver, preserving sentinel gaps.
        env.put(popup, 0x513fc8, 0x13572468, 0)
        for offset in range(0x0c, 0x6c, 4):
            env.put(popup + offset, 0)
        env.put(popup + 0x0c, 0x10c00000 if style is None else style)
        env.write(popup + 0x14, word(len(geometry_items)))
        env.write(popup + 0x1a, word(width) + word(height))
        for offset, vtable in ((0xcc, 0x5141a8), (0xe4, 0x5141a8),
                               (0x104, 0x5141a8), (0x10c, 0x514190), (0x114, 0x514190)):
            env.put(popup + offset, vtable, 0)
        for offset in (0xd4, 0xec):
            env.put(popup + offset, 0x510444, 0, 0, 0)
        env.put(popup + 0xfc, 0, 0)
        env.put(popup + 0x11c, 0)
        env.put(popup + 0x130, 21, 25)
        env.put(popup + 0x50, cursor_enabled, cursor_count)
        if cursor_callback is not None:
            methods = env.object(0xd8, 'caller-popup-vtable', data=env.read(0x513fc8, 0xd8))
            observed = env.object(16, 'caller-cursor-observation')
            def cursor_effect(e, c):
                e.put(observed, c.receiver, c.arguments[0], e.get(c.receiver + 0x58),
                      e.get(c.receiver + 4))
                return cursor_callback
            env.put(methods + 0xd4, env.stub('caller-cursor-interface', 'thiscall', 1, cursor_effect))
            env.put(popup, methods)
        if old_fields:
            old_text = env.object(10, 'old-resource-string', data=b'Old value\0')
            env.put(popup + 0x20, 0x9101, old_text, 0x9202, old_text, old_text)
            env.write(popup + 0x34, word(0x17))
            env.put(popup + 0x38, old_text)
            env.put(popup + 0x68, popup + 0x6c)
        if face is not None:
            face_pointer = env.object(len(face) + 1, 'font-face', data=face + b'\0')
            env.put(popup + 0x38, face_pointer)
            env.write(popup + 0x34, word(13))
        if geometry_items:
            records = env.object(len(geometry_items) * 0x5c, 'controls', fill=0xb7)
            env.put(popup + 0x3c, records)
            for i, geometry in enumerate(geometry_items):
                env.write(records + i * 0x5c + 8, struct.pack('<hhhh', *geometry))
        resource = physical(env, popup, data, **options)
        return {'popup': popup, 'resource': resource}
    return setup


def popup_case(label, entry, data=None, **options):
    data = template() if data is None else data
    return Case(label, entry, setup_popup(data, **options),
                receiver=lambda t: t['popup'],
                arguments=(() if entry == FONTS else
                           ((0x1234, 0x5678) if entry == CONSTRUCT else
                            ((lambda t: t['resource']),))))


def cases(random_source):
    for index, units in enumerate(([], [65], [0x141, 0x2e9, 0xffff, 0x100, 0x77],
                                   [random_source.randrange(1, 65536) for _ in range(39)])):
        payload = b''.join(word(unit) for unit in units) + b'\0\0' + b'\xa5\x5a'
        def setup(env, payload=payload):
            return env.object(len(payload), 'wide-resource-string', data=payload)
        yield Case(f'narrow UTF16 low bytes {index}', NARROW, setup,
                   arguments=(lambda t: t,))
    def narrow_reentrant(env):
        source = env.object(12, 'changing-wide-string', data=b'A\0B\0C\0D\0\0\0ZZ')
        def allocate(e, c):
            result = e.object(c.arguments[0], 'allocation')
            e.write(source, b'\0\0')
            return result
        env.override(0x4F63EC, allocate)
        return source
    yield Case('narrow rereads source after allocation', NARROW, narrow_reentrant,
               arguments=(lambda t: t,))
    yield popup_case('constructor sentinel gaps and NCM output', CONSTRUCT)
    yield popup_case('constructor different nonzero contents', CONSTRUCT, fill=0x39)
    for failure in (0x546AC8, 0x546ACC, 0x546AC4):
        yield popup_case(f'parse physical resource failure {failure:x}', PARSE,
                         resource_failure=failure)
    yield popup_case('reject extended template signature', PARSE,
                     b'\xff\xff' + bytes(range(1, 32)))
    yield popup_case('empty header no font no thread', PARSE, thread=False, old_fields=True)
    yield popup_case('nonzero UTF16 unit with embedded narrow NUL header', PARSE,
                     template(menu=word(0x100) + word(0), cls='', title=''), old_fields=True)
    yield popup_case('empty array allocation returns null', PARSE, zero_allocation=True)
    yield popup_case('geometry create rejected after parsing', PARSE, create=0)
    yield popup_case('header ordinals', PARSE,
                     template(menu=0xf123, cls=0xa234, title='Caption', tail=b'\x51'))
    yield popup_case('header strings and font', PARSE,
                     template(menu='MenuName', cls='DialogClass', title='Caption\u0142',
                              font=(0x8123, 'Courier'), tail=b'\x25\x83\x97'))
    yield popup_case('header empty font face and high font size', PARSE,
                     template(menu='M', cls='C', font=(0xffff, '')))
    for kind in (0x80, 0x81, 0x83, 0x85):
        yield popup_case(f'focus class {kind:x} after excluded controls', PARSE,
                         template(items=(item(0x82), item(0x80, style=0x50010007),
                                         item(kind, 0xf167))))
    yield popup_case('no focus candidates preserves old target', PARSE,
                     template(items=(item(0x82), item('CustomWidget', ''),
                                     item(0x80, style=0x50010007))), old_fields=True)
    for length in range(8):
        extra = bytes(random_source.randrange(1, 256) for _ in range(length))
        yield popup_case(f'extra data {length} byte copy and next item alignment', PARSE,
                         template(menu='Odd', cls=0x9001, title='Even',
                                  items=(item('Widget', '', extra), item(0x81, 'Second')),
                                  tail=bytes(range(length % 4))))
    for style in (0, 8, 0x80000008):
        yield popup_case(f'stock font style {style:x}', FONTS, style=style)
    yield popup_case('first stock font missing', FONTS, stock=(0,))
    yield popup_case('second stock font missing', FONTS, stock=(0x7101, 0))
    yield popup_case('custom font physical creation', FONTS, face=b'Courier New')
    yield popup_case('custom font physical creation fails', FONTS, face=b'Tahoma', font_create=0)
    yield popup_case('geometry dialog creation fails', GEOMETRY, create=0)
    for style in (0, 0x400000, 0x800000, 0xc00000):
        yield popup_case(f'geometry style {style:x} no controls', GEOMETRY, style=style,
                         thread=False)
        yield popup_case(f'geometry style {style:x} signed controls', GEOMETRY, style=style,
                         geometry_items=((-9, 3, 17, 11), (37, -19, -13, 23),
                                         (-32768, 32767, 0, -1)))
    for width, height in ((-153, 97), (153, -97), (-32768, 32767), (1, -1)):
        yield popup_case(f'geometry signed template size {width}x{height}', GEOMETRY,
                         width=width, height=height,
                         geometry_items=((-32768, 32767, -1, 1), (1, -1, 32767, -32768)))
    for i in range(8):
        dimensions = (random_source.randrange(17, 300), random_source.randrange(19, 240))
        geometry = tuple(tuple(random_source.randrange(-250, 251) for _ in range(4))
                         for _ in range(3))
        yield popup_case(f'geometry randomized scale and signed coordinates {i}', GEOMETRY,
                         width=dimensions[0], height=dimensions[1], geometry_items=geometry,
                         rect=(-11, -29, random_source.randrange(311, 702),
                               random_source.randrange(311, 702)),
                         metrics=(random_source.randrange(1, 11), random_source.randrange(2, 13),
                                  random_source.randrange(17, 32)))
    yield popup_case('initialize resource failure', INITIALIZE, resource_failure=0x546AC8)
    yield popup_case('initialize font failure', INITIALIZE, stock=(0,))
    yield popup_case('initialize DC attachment failure', INITIALIZE, template(style=0), attach_fail=1)
    yield popup_case('initialize original descendants', INITIALIZE, template(style=0))

    yield popup_case('initialize second DC attachment failure', INITIALIZE,
                     template(style=0), attach_fail=2)
    yield popup_case('initialize empty null control array draw result', INITIALIZE,
                     template(style=0), zero_allocation=True)
    yield popup_case('initialize original cursor already visible', INITIALIZE,
                     template(style=0), cursor_enabled=1, cursor_count=1)
    yield popup_case('initialize supplied cursor interface returns failure', INITIALIZE,
                     template(style=0), cursor_enabled=1, cursor_callback=0)

    # A constructor must initialize raw storage, including fields that the
    # previously constructed receivers above already happen to have cleared.
    for poison in (0x39, 0xa6, 0xed):
        def raw_constructor(env, poison=poison):
            popup = env.object(0x278, 'unconstructed-popup',
                               data=bytes((poison + 37 * i) % 255 + 1
                                          for i in range(0x278)))
            physical(env, popup, template())
            return popup
        yield Case(f'constructor raw distinct storage {poison:x}', CONSTRUCT,
                   raw_constructor, receiver=lambda t: t,
                   arguments=(0x89abcdef, 0x76543210))

    # Windows heap allocation does not promise zero-filled storage. Poisoning
    # destinations exposes omitted record initialization and terminators. The
    # deliberately untouched record gap remains observable too.
    poisoned_templates = (
        ('empty header', template()),
        ('ordinal records', template(menu=0x9123, cls=0x9345, title='Dialog',
                                    items=(item(0x82, 0x9567), item(0x80, ''),
                                           item(0x81, 0x9789)))),
        ('string records', template(menu='Menu', cls='Class', title='Title',
                                   font=(29, 'Face'),
                                   items=(item('Widget', 'Caption', b'\x19\x83\x47\xd5\x2b'),
                                          item(0x85, '', b'')))),
        ('no focus', template(items=(item('Custom', ''),
                                    item(0x80, style=0x50010007)))),
    )
    for poison in (0x5b, 0xd3):
        for label, data in poisoned_templates:
            def poisoned_parser(env, data=data, poison=poison):
                tokens = setup_popup(data, old_fields=True)(env)
                env.put(tokens['popup'] + 0x64, 0x6a5b4c3d)
                def allocate(e, c):
                    return e.object(c.arguments[0], 'poisoned-allocation', fill=poison)
                env.override(0x4F63EC, allocate)
                return tokens
            yield Case(f'parse poisoned destinations {poison:x} {label}', PARSE,
                       poisoned_parser, receiver=lambda t: t['popup'],
                       arguments=(lambda t: t['resource'],))

    for units in ((), (0x141,), (0x241, 0x100, 0x3ff, 0x44)):
        payload = b''.join(word(unit) for unit in units) + word(0)
        def poisoned_narrow(env, payload=payload):
            source = env.object(len(payload), 'wide-source', data=payload)
            env.override(0x4F63EC, lambda e, c:
                         e.object(c.arguments[0], 'poisoned-narrow-buffer', fill=0xb9))
            return source
        yield Case(f'narrow poisoned buffer {len(units)} units', NARROW,
                   poisoned_narrow, arguments=(lambda t: t,))
