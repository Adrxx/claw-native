"""Screen dump validation, signed formatting, lifetime and reentrant fields."""
from clawparity.cases import Case

ENTRY = 0x495BE0
READ, WRITE = 0x4B5F30, 0x4B5E50
CTOR, FORMAT, DTOR, BMP = 0x4F6439, 0x4F4F58, 0x4F6584, 0x4B9E10


def setup_case(counter, result, fill, missing=None, stage=None, change=None):
    def setup(env):
        def obj(name):
            return env.object(0x80, name, fill=fill)
        settings, root = obj('settings'), obj('root')
        link, owner, surface = obj('link'), obj('owner'), obj('surface')
        writer, writer2 = obj('writer'), obj('other writer')
        proot, plink, palette = obj('palette root'), obj('palette link'), obj('palette')
        aroot, alink, apalette = obj('alternate root'), obj('alternate link'), obj('alternate palette')
        link2, owner2, surface2 = obj('other link'), obj('other owner'), obj('other surface')
        record = env.object(0x400, 'fixture observations', fill=0)
        initial = env.object(96, 'constructed string', data=b'constructed-but-unformatted\0')
        formatted = env.object(96, 'formatted filename', fill=0x6D)
        for address, value in ((root+0x30, link), (link+4, owner), (owner+0x10, surface),
                               (surface+0x2C, writer), (root+0x2C, proot),
                               (proot+0x2C, plink), (plink+0x10, palette),
                               (aroot+0x2C, alink), (alink+0x10, apalette),
                               (link2+4, owner2), (owner2+0x10, surface2),
                               (surface2+0x2C, writer2)):
            env.put(address, value)

        def snapshot(e, tag, call):
            index = e.get(record)
            slot = record + 4 + index * 48
            e.put(record, index+1)
            args = list(call.arguments) + [0, 0, 0]
            e.put(slot, tag, call.receiver, *args[:3], e.get(root+0x30),
                  e.get(root+0x2C), e.get(surface+0x2C), e.get(proot+0x2C),
                  e.get(plink+0x10), e.get(formatted))

        def mutate(e, boundary):
            if boundary != stage:
                return
            edits = {
                'writer': (surface+0x2C, writer2),
                'root chain': (root+0x30, link2),
                'cached surface': (owner+0x10, surface2),
                'palette root': (root+0x2C, aroot),
                'palette link': (proot+0x2C, alink),
                'palette value': (plink+0x10, apalette),
                'no palette root': (root+0x2C, 0),
                'no palette link': (proot+0x2C, 0),
                'zero palette': (plink+0x10, 0),
            }
            if change in edits:
                e.put(*edits[change])

        def read(e, call):
            snapshot(e, 1, call)
            e.write(record+0x280, e.cstr(call.arguments[0])+b'\0')
            mutate(e, 'read')
            return counter

        def write(e, call):
            snapshot(e, 2, call)
            e.write(record+0x2C0, e.cstr(call.arguments[0])+b'\0')
            mutate(e, 'write')
            return 0x87654321

        def construct(e, call):
            snapshot(e, 3, call)
            e.put(call.receiver, initial)
            mutate(e, 'construct')
            return 0x76543210

        def format_string(e, call):
            snapshot(e, 4, call)
            destination, pattern, value = call.arguments
            e.write(record+0x300, e.cstr(pattern)+b'\0')
            signed = value if value < 0x80000000 else value-0x100000000
            e.put(record+0x340, value)
            e.write(formatted, ('CLAW%04i.BMP' % signed).encode('ascii')+b'\0')
            e.put(destination, formatted)
            mutate(e, 'format')
            return 0

        def bmp(e, call):
            snapshot(e, 5, call)
            e.write(record+0x360, e.cstr(call.arguments[0])+b'\0')
            e.put(surface+0x2C, writer)
            return result

        def destroy(e, call):
            snapshot(e, 6, call)
            e.write(record+0x3A0, e.cstr(e.get(call.receiver))+b'\0')
            e.put(call.receiver, initial)
            return result ^ 0xFFFFFFFF

        for address, effect in ((READ, read), (WRITE, write), (CTOR, construct),
                                (FORMAT, format_string), (BMP, bmp), (DTOR, destroy)):
            env.override(address, effect)
        if missing == 'settings':
            settings = 0
        elif missing == 'root':
            return {'settings': settings, 'root': 0}
        else:
            absent = {'link': root+0x30, 'surface': owner+0x10,
                      'writer': surface+0x2C, 'palette root': root+0x2C,
                      'palette link': proot+0x2C, 'palette': plink+0x10}
            if missing in absent:
                env.put(absent[missing], 0)
        return {'settings': settings, 'root': root}
    return setup


def case(label, **options):
    return Case(label, ENTRY, setup_case(**options), arguments=(
        lambda t: t['settings'], lambda t: t['root']))


def cases(random_source):
    for missing in ('settings', 'root', 'link', 'surface', 'writer',
                    'palette root', 'palette link', 'palette', None):
        yield case(f'validation {missing}', counter=9, result=0x89ABCDEF,
                   fill=0xA7, missing=missing)
    counters = (0, 1, 8, 9, 98, 99, 998, 999, 9998, 9999, 10000,
                0x7FFFFFFE, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF)
    for counter in counters:
        for result in (0, 1, 0x80000000, 0xFFFFFFFF):
            yield case(f'counter {counter:08x} BMP result {result:08x}',
                       counter=counter, result=result, fill=0x59)
    changes = ('writer', 'root chain', 'cached surface', 'palette root', 'palette link',
               'palette value', 'no palette root', 'no palette link', 'zero palette')
    for stage in ('read', 'write', 'construct', 'format'):
        for change in changes:
            yield case(f'{stage} changes {change}', counter=0x7FFFFFFF,
                       result=0xBAD12345, fill=0xC3, stage=stage, change=change)
    for index in range(48):
        yield case(f'random {index}', counter=random_source.getrandbits(32),
                   result=random_source.getrandbits(32), fill=random_source.randrange(1, 256),
                   missing=random_source.choice((None, 'palette root', 'palette link', 'palette')),
                   stage=random_source.choice((None, 'read', 'write', 'construct', 'format')),
                   change=random_source.choice(changes))
