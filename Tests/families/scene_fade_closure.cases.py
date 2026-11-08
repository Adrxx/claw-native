"""Cases for scene_fade_closure: Level 1 closure: player fade helpers and fade blend."""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

SERIALIZE = 0x4EC720
BASE_DELETING_DTOR = 0x4EC900
ARRAY_CTOR = 0x4ECC30
FADE_CTOR = 0x4ECC60
FADE_DELETING_DTOR = 0x4ECC90
FADE_DTOR = 0x4ECCB0
FADE_SETUP = 0x4ECD00
FREE_RECORDS = 0x4ECEF0
FADE_BLEND = 0x4ECF10
PLAIN_DELETING_DTOR = 0x423F10
ARRAY_DTOR = 0x4C7650
ARRAY_DELETING_DTOR = 0x4C76B0
OPERATOR_NEW = 0x4F63EC
OPERATOR_DELETE = 0x4F6428

ARRAY_VTABLE = 0x5136E8
FADE_VTABLE = 0x5141F0


def fork(rnd):
    return random.Random(rnd.getrandbits(64))


def nonzero_words(rnd, count):
    return [rnd.randrange(1, 1 << 32) for _ in range(count)]


def noise(rnd, count):
    return bytes(rnd.randrange(1, 256) for _ in range(count))


def pack_words(words):
    return struct.pack("<%dI" % len(words), *words)


# ---------------------------------------------------------------------------------------------
# 0x4ec720: serialize a growable array of dwords through an archive.
#
# Array: +4 data, +8 size, +0xc capacity, +0x10 grow-by.  Archive: +0x14 mode flags (bit 0 set =
# loading), +0x1c buffer size, +0x20 file, +0x24 current, +0x28 limit, +0x2c start.

def make_archive(env, rnd, mode, content, capacity=None, offset=0):
    """An archive whose buffer holds `content` after `offset` stale bytes; storing has `capacity` bytes."""
    capacity = len(content) if capacity is None else capacity
    total = offset + capacity
    buffer = env.object(total + 8, "archive-buffer", data=noise(rnd, total + 8))
    env.write(buffer + offset, content)
    methods = env.object(0x5C, "file-vtable")
    file = env.object(4, "file", words=[methods])
    for slot in (0x3C, 0x40, 0x58):
        env.put(methods + slot, env.stub("file-slot-%x" % slot, "thiscall", 2, returns(0)))
    archive = env.object(0x40, "archive", data=noise(rnd, 0x40))
    env.put(archive + 0x08, 0)
    env.put(archive + 0x14, mode)
    env.put(archive + 0x1C, total + 8)
    env.put(archive + 0x20, file)
    env.put(archive + 0x24, buffer + offset)
    env.put(archive + 0x28, buffer + offset + capacity)
    env.put(archive + 0x2C, buffer)
    return archive


def make_array(env, rnd, size, capacity, grow, data=True, stale=None):
    stale = size if stale is None else stale
    array = env.object(0x20, "array", data=noise(rnd, 0x20))
    pointer = 0
    if data:
        pointer = env.object(max(4, capacity * 4), "array-data", data=noise(rnd, max(4, capacity * 4)))
        env.write(pointer, pack_words(nonzero_words(rnd, min(size, capacity))))
    env.put(array + 0x00, ARRAY_VTABLE)
    env.put(array + 0x04, pointer)
    env.put(array + 0x08, size)
    env.put(array + 0x0C, capacity)
    env.put(array + 0x10, grow)
    return array, pointer


def count_prefix(count):
    return struct.pack("<H", count) if count < 0xFFFF else struct.pack("<HI", 0xFFFF, count)


def store_case(label, rnd, size, mode=0, capacity=None, offset=0, with_data=True):
    seed = rnd.getrandbits(64)

    def setup(env):
        rnd = random.Random(seed)
        array, pointer = make_array(env, rnd, size, size + 3, 7, data=with_data)
        need = len(count_prefix(size)) + 4 * size
        archive = make_archive(env, rnd, mode, b"", capacity=need + 5 if capacity is None else capacity, offset=offset)
        return {"array": array, "archive": archive, "data": pointer}
    return Case(label, SERIALIZE, setup, receiver=lambda t: t["array"], arguments=(lambda t: t["archive"],))


def load_case(label, rnd, count, size, capacity, grow, mode=1, data=True, offset=0, prefix=None):
    seed = rnd.getrandbits(64)

    def setup(env):
        rnd = random.Random(seed)
        array, pointer = make_array(env, rnd, size, capacity, grow, data=data)
        content = (count_prefix(count) if prefix is None else prefix) + pack_words(nonzero_words(rnd, count))
        archive = make_archive(env, rnd, mode, content, offset=offset)
        return {"array": array, "archive": archive, "data": pointer}
    return Case(label, SERIALIZE, setup, receiver=lambda t: t["array"], arguments=(lambda t: t["archive"],))


def serialize_cases(rnd):
    # Storing: the mode test looks only at bit 0 of the flags word.
    for mode in (0, 2, 0x10, 0xFFFFFFFE, 0x80000000):
        yield store_case("store 5 words, mode %#x" % mode, rnd, 5, mode=mode)
    for size in (0, 1, 2, 3, 8, 33):
        yield store_case("store %d words" % size, rnd, size)
    yield store_case("store 0 words from a null array", rnd, 0, with_data=False)
    for offset in (1, 6, 13):
        yield store_case("store 4 words after %d stale bytes" % offset, rnd, 4, offset=offset)
    for size in (rnd.randrange(9, 300) for _ in range(6)):
        yield store_case("store %d random words" % size, rnd, size)
    # Storing in an archive whose buffer is exactly large enough, and one that needs the file.
    yield store_case("store 4 words exactly filling the buffer", rnd, 4, capacity=2 + 16)
    yield store_case("store 6 words overflowing the buffer", rnd, 6, capacity=2 + 8)
    yield store_case("store 6 words with a tiny buffer", rnd, 6, capacity=3)

    # Loading: the mode flag is bit 0 set.
    for mode in (1, 3, 0x11, 0xFFFFFFFF, 0x80000001):
        yield load_case("load 4 words, mode %#x" % mode, rnd, 4, 2, 6, 3, mode=mode)
    # Count 0, with and without existing storage.
    yield load_case("load 0 into an empty array", rnd, 0, 0, 0, 5, data=False)
    yield load_case("load 0 into an array with garbage fields and no storage", rnd, 0, 7, 9, 5, data=False)
    yield load_case("load 0 frees existing storage", rnd, 0, 3, 8, 5)
    yield load_case("load 0 frees a one-slot storage", rnd, 0, 1, 1, 0)
    # No storage yet: allocate and zero it (the data is then read over it).
    for count in (1, 2, 3, 7, 40):
        yield load_case("load %d into an array without storage" % count, rnd, count, 5, 9, 4, data=False)
    # Fits in the capacity.
    for count, size, capacity in ((1, 0, 4), (4, 0, 4), (3, 3, 8), (4, 3, 8), (8, 3, 8), (2, 5, 8), (1, 5, 5),
                                  (5, 5, 5), (6, 4, 9), (9, 4, 9), (3, 8, 8)):
        yield load_case("load %d with size %d and capacity %d" % (count, size, capacity), rnd, count, size, capacity, 2)
    # Needs more room: explicit grow-by.
    for count, size, capacity, grow in ((5, 3, 4, 1), (5, 3, 4, 2), (5, 3, 4, 3), (12, 3, 4, 8), (12, 3, 4, 9),
                                        (12, 3, 4, 10), (9, 4, 4, 5), (9, 4, 4, 6), (30, 0, 4, 100), (30, 2, 3, 1)):
        yield load_case("load %d into size %d capacity %d grow %d" % (count, size, capacity, grow), rnd, count,
                        size, capacity, grow)
    # Needs more room: automatic growth, size / 8 clamped to [4, 0x400].
    for size, count in ((0, 6), (1, 6), (8, 12), (23, 30), (24, 40), (31, 40), (32, 50), (33, 50), (47, 60),
                        (64, 100), (200, 260), (8191, 8195), (8192, 8200), (8199, 8205), (8200, 8300),
                        (8208, 8300), (9000, 9100), (12000, 12100), (16384, 17000)):
        capacity = size
        yield load_case("load %d into full array of size %d, automatic growth" % (count, size), rnd, count, size,
                        capacity, 0)
    yield load_case("automatic growth with spare capacity beyond size", rnd, 20, 5, 6, 0)
    yield load_case("automatic growth, new count just above the increment", rnd, 13, 16, 16, 0)
    yield load_case("automatic growth, new count equals the increment", rnd, 20, 16, 16, 0)
    yield load_case("automatic growth, new count just below the increment", rnd, 19, 16, 16, 0)
    for _ in range(6):
        size = rnd.randrange(0, 90)
        capacity = size + rnd.randrange(0, 4)
        count = capacity + rnd.randrange(1, 80)
        grow = rnd.choice((0, 0, rnd.randrange(1, 60)))
        yield load_case("load %d random into size %d capacity %d grow %d" % (count, size, capacity, grow), rnd,
                        count, size, capacity, grow)
    # The count is stored as a word, with 0xffff escaping to a following dword (the heap is too small for
    # a full 0xffff-word array, so only the escape encoding of a small count can be exercised).
    yield load_case("count escaped but small", rnd, 6, 2, 3, 0, prefix=struct.pack("<HI", 0xFFFF, 6))
    yield load_case("load after stale bytes in the buffer", rnd, 5, 2, 3, 2, offset=9)


# ---------------------------------------------------------------------------------------------
# Constructors and destructors.

def array_ctor_case(rnd, label):
    seed = rnd.getrandbits(64)

    def setup(env):
        rnd = random.Random(seed)
        return {"object": env.object(0x20, "array", data=noise(rnd, 0x20))}
    return Case(label, ARRAY_CTOR, setup, receiver=lambda t: t["object"])


def make_element(env, rnd, with_buffer=True):
    element = env.object(12, "element", data=noise(rnd, 12))
    if with_buffer:
        length = rnd.randrange(4, 40)
        buffer = env.object(length, "element-buffer", data=noise(rnd, length))
        env.put(element, 1, length, buffer)
    else:
        env.put(element, 0, rnd.randrange(1, 99), 0)
    return element


def make_fade(env, rnd, elements=3, held=None, owns=1, flag=1, records=False, with_list=True, buffered=None,
              record_words=0):
    """A fade object in a state the destructors can walk.  `held` is the index of the element in +0x1c,
    None for a pointer that is not in the list, 0 for no pointer."""
    fade = env.object(0x5C, "fade", data=noise(rnd, 0x5C))
    pointers = []
    data = 0
    if with_list:
        for index in range(elements):
            use_buffer = True if buffered is None else buffered[index % len(buffered)]
            pointers.append(make_element(env, rnd, with_buffer=use_buffer))
        data = env.object(max(4, 4 * (elements + 2)), "element-list", data=noise(rnd, 4 * (elements + 2) + 4))
        env.put(data, *pointers) if pointers else None
    env.put(fade + 0x00, 0x13572468)
    env.put(fade + 0x04, flag)
    env.put(fade + 0x08, 0x2468ACE1)
    env.put(fade + 0x0C, data)
    env.put(fade + 0x10, elements if with_list else 0)
    env.put(fade + 0x14, elements + 2)
    stranger = 0
    if held is None:
        stranger = make_element(env, rnd)
        env.put(fade + 0x1C, stranger)
    elif held is False:
        env.put(fade + 0x1C, 0)
    else:
        env.put(fade + 0x1C, pointers[held])
    env.put(fade + 0x30, owns)
    record = 0
    if records:
        record = env.object(max(16, record_words * 4), "records", data=noise(rnd, max(16, record_words * 4)))
    env.put(fade + 0x50, record)
    return {"object": fade, "pointers": pointers, "data": data, "record": record, "stranger": stranger}


def destructor_cases(rnd):
    for index in range(3):
        yield array_ctor_case(rnd, "array constructor over noise %d" % index)

    def fade_ctor(env, seed=rnd.getrandbits(64)):
        rnd = random.Random(seed)
        return {"object": env.object(0x5C, "fade", data=noise(rnd, 0x5C))}
    for index in range(3):
        yield Case("fade constructor over noise %d" % index, FADE_CTOR, fade_ctor, receiver=lambda t: t["object"])

    # Plain deleting destructor: only bit 0 of the low byte decides the delete.
    for flags in (0, 1, 2, 3, 0xFE, 0xFF, 0x100, 0x101, 0xFFFFFF00, 0xFFFFFF01, rnd.randrange(0, 1 << 32)):
        def plain(env, seed=rnd.getrandbits(64)):
            rnd = random.Random(seed)
            return {"object": env.object(0x20, "plain", data=noise(rnd, 0x20))}
        yield Case("plain deleting destructor flags %#x" % flags, PLAIN_DELETING_DTOR, plain,
                   receiver=lambda t: t["object"], arguments=(flags,))

    # Array destructor and its deleting form.
    for pointer in (False, True):
        def array_dtor(env, pointer=pointer, seed=rnd.getrandbits(64)):
            rnd = random.Random(seed)
            obj = env.object(0x20, "array", data=noise(rnd, 0x20))
            buffer = env.object(rnd.randrange(8, 60), "array-data", data=noise(rnd, 8)) if pointer else 0
            env.put(obj + 4, buffer)
            return {"object": obj}
        yield Case("array destructor, data %s" % ("present" if pointer else "absent"), ARRAY_DTOR, array_dtor,
                   receiver=lambda t: t["object"])
        for flags in (0, 1, 2, 3, 0x100, 0x101, 0xFF):
            yield Case("array deleting destructor flags %#x, data %s" % (flags, "present" if pointer else "absent"),
                       ARRAY_DELETING_DTOR, array_dtor, receiver=lambda t: t["object"], arguments=(flags,))

    # Records released by the fade tail.
    for present in (False, True):
        def free_records(env, present=present, seed=rnd.getrandbits(64)):
            rnd = random.Random(seed)
            obj = env.object(0x5C, "fade", data=noise(rnd, 0x5C))
            record = env.object(32, "records", data=noise(rnd, 32)) if present else 0
            env.put(obj + 0x50, record)
            return {"object": obj}
        yield Case("free records, %s" % ("present" if present else "absent"), FREE_RECORDS, free_records,
                   receiver=lambda t: t["object"])

    # The base destructor chain, through the base deleting destructor.
    shapes = [
        ("no held item", dict(held=False)),
        ("held item not owned", dict(held=1, owns=0)),
        ("held item, owned, first in list", dict(held=0)),
        ("held item, owned, middle of list", dict(held=1)),
        ("held item, owned, last in list", dict(held=2)),
        ("held item, owned, element without buffer", dict(held=1, buffered=[True, False, True])),
        ("held item, owned, only element", dict(held=0, elements=1)),
        ("held item owned but not in list", dict(held=None)),
        ("held item owned, empty list", dict(held=None, elements=0)),
        ("held item owned, no list storage", dict(held=None, with_list=False, elements=0)),
        ("list flag clear", dict(held=False, flag=0)),
        ("list flag clear, held item owned", dict(held=1, flag=0)),
        ("list flag set, elements without buffers", dict(held=False, buffered=[False])),
        ("list flag set, mixed elements", dict(held=False, elements=5, buffered=[True, False])),
        ("list flag set, empty list", dict(held=False, elements=0)),
        ("list flag set, no storage", dict(held=False, with_list=False, elements=0)),
        ("list flag two", dict(held=False, flag=2)),
        ("held item owned, one element and flag clear", dict(held=0, elements=1, flag=0)),
        ("owns flag two", dict(held=2, owns=2)),
    ]
    for name, options in shapes:
        for flags in (0, 1):
            def base(env, options=options, seed=rnd.getrandbits(64)):
                rnd = random.Random(seed)
                return make_fade(env, rnd, **options)
            yield Case("base deleting destructor, %s, flags %d" % (name, flags), BASE_DELETING_DTOR, base,
                       receiver=lambda t: t["object"], arguments=(flags,))
    for flags in (2, 3, 0x100, 0x101, 0xFF):
        def base_flags(env, seed=rnd.getrandbits(64)):
            rnd = random.Random(seed)
            return make_fade(env, rnd, held=1)
        yield Case("base deleting destructor flags %#x" % flags, BASE_DELETING_DTOR, base_flags,
                   receiver=lambda t: t["object"], arguments=(flags,))

    # The fade destructor and its deleting form, which add the record release.
    for name, options in shapes[:9] + shapes[10:14]:
        for records in (False, True):
            def fade_dtor(env, options=options, records=records, seed=rnd.getrandbits(64)):
                rnd = random.Random(seed)
                return make_fade(env, rnd, records=records, **options)
            yield Case("fade destructor, %s, records %s" % (name, records), FADE_DTOR, fade_dtor,
                       receiver=lambda t: t["object"])
            for flags in (0, 1):
                yield Case("fade deleting destructor, %s, records %s, flags %d" % (name, records, flags),
                           FADE_DELETING_DTOR, fade_dtor, receiver=lambda t: t["object"], arguments=(flags,))
    for flags in (2, 3, 0x100, 0x101, 0xFF):
        def fade_flags(env, seed=rnd.getrandbits(64)):
            rnd = random.Random(seed)
            return make_fade(env, rnd, held=0, records=True)
        yield Case("fade deleting destructor flags %#x" % flags, FADE_DELETING_DTOR, fade_flags,
                   receiver=lambda t: t["object"], arguments=(flags,))


# ---------------------------------------------------------------------------------------------
# Surfaces for the fade setup and the blend.

SURFACE_VTABLE = 0x513690


def make_surface(env, rnd, width, height, pitch=None, lock_null=None, lock_status=0, name="surface"):
    """A surface with stand-in Lock/Unlock/Blt.  `lock_null(call_number)` makes Lock publish a null pointer."""
    pitch = max(width, 0) if pitch is None else pitch
    capacity = max(8, pitch * max(height, 1) + 8)
    pixels = env.object(capacity, name + "-pixels", data=noise(rnd, capacity))
    surface = env.object(188, name, data=noise(rnd, 188))
    interface = env.object(4, name + "-interface")
    methods = env.object(0x84, name + "-methods")

    def lock(env, call):
        number = env.calls_so_far(call.function)
        env.put(surface + 0x30, 0 if lock_null is not None and lock_null(number) else pixels)
        return lock_status

    env.put(surface, SURFACE_VTABLE)
    env.put(surface + 0x08, interface)
    env.put(surface + 0x14, height, width, pitch)
    env.put(surface + 0x30, pixels)
    env.put(interface, methods)
    env.put(methods + 0x14, env.stub(name + "-Blt", "stdcall", 6, returns(0)))
    env.put(methods + 0x64, env.stub(name + "-Lock", "stdcall", 5, lock))
    env.put(methods + 0x80, env.stub(name + "-Unlock", "stdcall", 2, returns(0)))
    return {"surface": surface, "pixels": pixels, "interface": interface, "methods": methods}


def fade_object(env, rnd, source, destination, defaults, arg_flags=(True, True), list_prefill=False):
    fade = env.object(0x5C, "fade", data=noise(rnd, 0x5C))
    env.put(fade + 0x00, FADE_VTABLE)
    env.put(fade + 0x04, 0)
    env.put(fade + 0x08, ARRAY_VTABLE)
    env.put(fade + 0x0C, 0)
    env.put(fade + 0x10, 0)
    env.put(fade + 0x14, 0)
    env.put(fade + 0x18, 0)
    return fade


def setup_case(label, rnd, width, height, explicit_destination=True, explicit_source=True, item=True,
               pitch=None, lock_null=None, palette=False, fail_from=None, prefill_list=False, scale_pixels=None):
    seed = rnd.getrandbits(64)

    def setup(env):
        rnd = random.Random(seed)
        source = make_surface(env, rnd, width, height, pitch=pitch, lock_null=lock_null, name="source")
        other = make_surface(env, rnd, width + 3, height + 2, name="other")
        destination = env.object(188, "destination", data=noise(rnd, 188))
        other_destination = env.object(188, "other-destination", data=noise(rnd, 188))
        fade = fade_object(env, rnd, source, destination, None)
        env.put(fade + 0x24, other_destination if explicit_destination else destination)
        env.put(fade + 0x28, other["surface"] if explicit_source else source["surface"])
        if prefill_list:
            data = env.object(4, "list-data", data=noise(rnd, 4))
            env.put(fade + 0x0C, data)
            env.put(fade + 0x10, 1)
            env.put(fade + 0x14, 1)
        argument = env.object(0x20, "fade-arguments", data=noise(rnd, 0x20))
        env.put(argument + 0x04, destination if explicit_destination else 0)
        env.put(argument + 0x08, source["surface"] if explicit_source else 0)
        holder = 0
        if palette:
            colours = env.object(1100, "palette", data=noise(rnd, 1100))
            holder = env.object(0x20, "palette-holder", data=noise(rnd, 0x20))
            env.put(holder + 0x0C, colours)
            env.put(argument + 0x10, holder)
            env.put(argument + 0x14, 0)
        else:
            env.put(argument + 0x10, 0xDEAD0010)
            env.put(argument + 0x14, env.object(12, "item", data=noise(rnd, 12)) if item else 0)
        if fail_from is not None:
            env.override(OPERATOR_NEW, allocate(fail_from_call=fail_from))
        return {"fade": fade, "argument": argument, "source": source}
    return Case(label, FADE_SETUP, setup, receiver=lambda t: t["fade"], arguments=(lambda t: t["argument"],))


def setup_cases(rnd):
    for dst in (False, True):
        for src in (False, True):
            yield setup_case("setup, destination %s, source %s" % (dst, src), rnd, 3, 2, dst, src)
    for width, height in ((1, 1), (2, 3), (3, 2), (5, 4), (1, 7), (8, 1), (4, 4), (7, 5), (6, 6)):
        yield setup_case("setup, %dx%d" % (width, height), rnd, width, height)
    for width, height in ((rnd.randrange(1, 10), rnd.randrange(1, 10)) for _ in range(6)):
        yield setup_case("setup, random %dx%d" % (width, height), rnd, width, height,
                         bool(rnd.randrange(2)), bool(rnd.randrange(2)))
    for width, height in ((3, 0), (0, 3), (0, 0), (1, 0), (0, 1)):
        yield setup_case("setup, degenerate %dx%d" % (width, height), rnd, width, height)
    yield setup_case("setup, pitch wider than the width", rnd, 4, 3, pitch=9)
    yield setup_case("setup, pitch narrower than the width", rnd, 5, 3, pitch=2)
    yield setup_case("setup, every lock publishes a null pointer", rnd, 3, 3, lock_null=lambda n: True)
    yield setup_case("setup, odd locks publish a null pointer", rnd, 3, 3, lock_null=lambda n: n % 2 == 1)
    yield setup_case("setup, even locks publish a null pointer", rnd, 3, 3, lock_null=lambda n: n % 2 == 0)
    yield setup_case("setup, first lock publishes a null pointer", rnd, 3, 3, lock_null=lambda n: n == 1)
    yield setup_case("setup, last lock publishes a null pointer", rnd, 3, 3, lock_null=lambda n: n == 9)
    yield setup_case("setup, palette surface allocation fails", rnd, 2, 2, palette=True, fail_from=1)
    yield setup_case("setup, palette pixel allocation fails", rnd, 2, 2, palette=True, fail_from=2)
    yield setup_case("setup, palette allocation fails, defaults used", rnd, 2, 2, False, False, palette=True,
                     fail_from=1)


def blend_case(label, rnd, records, argument, scale=1.0, half=(3, 2), size=(8, 6), pitch=None, item=True,
               source_dims=None, record_words=None):
    seed = rnd.getrandbits(64)
    width, height = size
    source_width, source_height = source_dims if source_dims else (len(records), 1)

    def setup(env):
        rnd = random.Random(seed)
        source = make_surface(env, rnd, source_width, source_height, name="source")
        destination = make_surface(env, rnd, width, height, pitch=pitch, name="destination")
        fade = env.object(0x5C, "fade", data=noise(rnd, 0x5C))
        env.put(fade + 0x00, FADE_VTABLE)
        count = max(len(records), source_width * source_height, 1)
        data = bytearray()
        for first, second, third, shade in records:
            data += struct.pack("<fffI", first, second, third, (rnd.randrange(1, 1 << 24) << 8) | shade)
        data += noise(rnd, 16 * count - len(data))
        table = env.object(16 * count, "records", data=bytes(data))
        stored = env.object(12, "item", data=noise(rnd, 12))
        env.put(stored + 8, env.object(8, "item-data", data=noise(rnd, 8)) if item else 0)
        env.put(fade + 0x1C, stored)
        env.put(fade + 0x38, source["surface"])
        env.put(fade + 0x3C, destination["surface"])
        env.put(fade + 0x4C, struct.unpack("<I", struct.pack("<f", scale))[0])
        env.put(fade + 0x50, table)
        env.put(fade + 0x54, half[0])
        env.put(fade + 0x58, half[1])
        return {"fade": fade}
    return Case(label, FADE_BLEND, setup, receiver=lambda t: t["fade"], arguments=(argument,))


def aim(x, y, depth, scale, fraction=0.5, shade=1):
    """A record whose projection lands `x` columns right and `y` rows up of the centre."""
    q = depth / scale + 1.0
    first = (x * q + (fraction if x >= 0 else -fraction))
    second = (y * q + (fraction if y >= 0 else -fraction))
    return (first, second, 0.0, shade)


def blend_cases(rnd):
    # Every cell of a margin around an 8x6 destination, with a centre of (3, 2), so that the strict
    # bounds on all four sides are exercised.
    span_x = range(-3 - 1, 8 - 3 + 2)
    span_y = range(-2 - 1, 6 - 2 + 2)
    for scale, depth, argument in ((1.0, 3.0, 100), (2.0, 5.0, 7), (0.5, 2.0, 0)):
        records = []
        for y in span_y:
            for x in span_x:
                first, second, _, _ = aim(x, y, depth, scale, shade=len(records) % 250 + 1)
                records.append((first, second, argument + depth, len(records) % 250 + 1))
        yield blend_case("blend grid scale %s depth %s" % (scale, depth), rnd, records, argument, scale=scale)
    # Same grid with a wider pitch than width and a different centre.
    records = []
    for y in range(-3, 6):
        for x in range(-4, 8):
            first, second, _, _ = aim(x, y, 3.0, 1.0)
            records.append((first, second, 50 + 3.0, len(records) % 250 + 1))
    yield blend_case("blend grid with pitch and centre", rnd, records, 50, half=(4, 3), size=(8, 6), pitch=11)
    # Depth tests: at or below one the record is skipped.
    for depth in (-5.0, 0.0, 0.5, 0.999, 1.0, 1.001, 1.5, 2.0):
        first, second, _, _ = aim(1, 1, max(depth, 1.5), 1.0)
        yield blend_case("blend depth %s" % depth, rnd, [(first, second, 20 + depth, 77)], 20, half=(3, 3))
    # Truncation towards zero for fractions on either side of the centre.
    for fraction in (0.0, 0.25, 0.75, 0.9999):
        records = [aim(x, y, 3.0, 1.0, fraction, shade=40 + index) + () for index, (x, y) in
                   enumerate(((2, 1), (-2, 1), (2, -1), (-2, -1), (1, 1), (-1, -1)))]
        records = [(a, b, 10 + 3.0, s) for a, b, _, s in records]
        yield blend_case("blend fraction %s" % fraction, rnd, records, 10, half=(4, 3))
    # Unsigned 32-bit argument.
    for argument, base in ((0xFFFFFFF0, 4294967296.0), (0x80000000, 2147483648.0 + 128.0), (0x7FFFFFFF, 2147483648.0),
                           (0xFFFFFF00, 4294967296.0)):
        first, second, _, _ = aim(1, 1, base - argument, 1.0)
        yield blend_case("blend unsigned argument %#x" % argument, rnd, [(first, second, base, 90)], argument,
                         half=(3, 3))
    # Random records.
    for index in range(6):
        scale = rnd.choice((0.5, 1.0, 1.5, 2.0, 4.0))
        argument = rnd.randrange(0, 1000)
        count = rnd.randrange(1, 40)
        records = []
        for _ in range(count):
            depth = rnd.choice((0.5, 1.0, 1.5, 2.0, 3.0, 7.0, 12.0))
            first, second, _, _ = aim(rnd.randrange(-6, 7), rnd.randrange(-5, 6), max(depth, 1.5), scale,
                                      rnd.choice((0.0, 0.25, 0.5, 0.75)))
            records.append((first, second, argument + depth, rnd.randrange(1, 256)))
        yield blend_case("blend random %d" % index, rnd, records, argument, scale=scale,
                         half=(rnd.randrange(0, 7), rnd.randrange(0, 6)))
    # Degenerate shapes.
    yield blend_case("blend without records", rnd, [], 5, source_dims=(0, 4))
    yield blend_case("blend without item data", rnd, [aim(1, 1, 3.0, 1.0)[:2] + (8.0, 5)] * 3, 5, item=False)
    yield blend_case("blend without item data and no records", rnd, [], 5, item=False, source_dims=(0, 0))
    yield blend_case("blend one record", rnd, [aim(0, 1, 3.0, 1.0)[:2] + (8.0, 200)], 5)
    yield blend_case("blend zero width destination", rnd, [aim(0, 1, 3.0, 1.0)[:2] + (8.0, 200)], 5, size=(0, 3))
    yield blend_case("blend narrow destination", rnd, [aim(0, 0, 3.0, 1.0)[:2] + (8.0, 200)] * 2, 5, size=(1, 1),
                     half=(0, 1))


def cases(random_source):
    rnd = random_source
    yield from serialize_cases(rnd)
    yield from destructor_cases(rnd)
    yield from setup_cases(rnd)
    yield from blend_cases(rnd)
