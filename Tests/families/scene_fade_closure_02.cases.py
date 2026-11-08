"""Cases for scene_fade_closure_02: Level 1 closure: scene fade and paper transition helpers."""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns

RAND = 0x4A3050
NEW = 0x4F63EC
DELETE = 0x4F6428
CSTRING_COPY = 0x4F6449
CSTRING_RELEASE = 0x4F6584
CFILE_CONSTRUCT = 0x4F72C9
CFILE_DESTRUCT = 0x4F7369
CFILE_OPEN = 0x4F7448
CFILE_CLOSE = 0x4F766E

FADE_CONSTRUCT = 0x4ED060
FADE_DELETE = 0x4ED080
FADE_DESTRUCT = 0x4ED0A0
FADE_SETUP = 0x4ED0B0
FADE_STEP = 0x4ED1A0
FADE_EXTENT = 0x4ED5D0
PERMUTE = 0x4EFB00
IS_PRIME = 0x4EFC40
PALETTE_TABLE = 0x4C62E0
LIST_LOAD = 0x4C7180
LOAD_FILE = 0x4C7780

LOG_SLOTS = 6


# ---- Small helpers --------------------------------------------------------------------

def junk_words(rng, count):
    return [rng.getrandbits(32) | 1 for _ in range(count)]


def junk_bytes(rng, count):
    return bytes(rng.randrange(1, 256) for _ in range(count))


def words_to_bytes(words):
    return struct.pack(f"<{len(words)}I", *[w & 0xFFFFFFFF for w in words])


def float_word(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def is_prime(n):
    return n < 3 or all(n % d for d in range(2, n))


def next_prime(n):
    while not is_prime(n):
        n += 1
    return n


def order_size(span, generator):
    """How many words 0x4efb00 may write for this span: the first prime from the span up, else the generator."""
    if span <= 0:
        return 0
    found = span
    while found < 100000 and not is_prime(found):
        found += 1
    return generator if found >= 100000 else found


def make_log(env):
    """A heap object that keeps the receiver and arguments of the first calls of each stand-in."""
    return env.object(16 * LOG_SLOTS * 20, "fixture-log", fill=0)


def traced(log, number, effect=None, result=0):
    """Wrap a stand-in so that its receiver, arguments and call number survive in memory."""
    def run(env, call):
        count = env.calls_so_far(call.function)
        index = min(count, LOG_SLOTS) - 1
        arguments = tuple(call.arguments) + (0, 0, 0)
        env.put(log + (number * LOG_SLOTS + index) * 20, call.receiver, arguments[0], arguments[1], arguments[2], count)
        return effect(env, call) if effect else result
    return run


def scripted_rand(values):
    return lambda env, call: values[(env.calls_so_far(call.function) - 1) % len(values)]


def allocator(fail_sizes=()):
    """operator new: a live object of the requested size, 0 for the listed sizes."""
    def effect(env, call):
        if call.arguments[0] in fail_sizes:
            return 0
        return env.object(call.arguments[0], name="allocation")
    return effect


# ---- Surfaces and the fade object ------------------------------------------------------

def surface_object(env, rng, junk, pixels, height, width, pitch, bpp, label, lock_hook=None, unlock_hook=None, log=None, number=0):
    """A surface whose DirectDraw-style Lock and Unlock methods are stand-ins. Lock publishes the pixel pointer."""
    decoy = env.object(16, label + "-stale-pixels", fill=0xEE)
    surface = env.object(0xB4, label, data=junk)
    interface = env.object(8, label + "-interface", fill=0)
    methods = env.object(0x90, label + "-methods", data=junk[:0x90])

    def lock(env, call):
        env.put(surface + 0x30, pixels)
        if lock_hook:
            lock_hook(env)
        return 0

    def unlock(env, call):
        if unlock_hook:
            unlock_hook(env)
        return 0

    lock_effect = traced(log, number, lock) if log else lock
    unlock_effect = traced(log, number + 1, unlock) if log else unlock
    env.put(surface + 0x08, interface)
    env.put(surface + 0x14, height, width, pitch)
    env.put(surface + 0x30, decoy)
    env.put(surface + 0xAC, bpp)
    env.put(interface, methods)
    env.put(methods + 0x64, env.stub(label + "::Lock", "stdcall", 5, lock_effect))
    env.put(methods + 0x80, env.stub(label + "::Unlock", "stdcall", 2, unlock_effect))
    return surface


def fade_world(rng, width, height, span, previous, bpp, flag, two=True, same=False, hooks=None, rand_hook=None, bpp_b=None):
    """The fade object for 0x4ed1a0: two locked surfaces, the per-row bookkeeping arrays and the column order."""
    hooks = hooks or {}
    count = 4000
    rand_values = [rng.randrange(0, 0x8000) for _ in range(count)]
    perm = [rng.randrange(0, max(width, 1)) for _ in range(width + 4)]
    counters = [rng.randrange(0, width + 1) for _ in range(height + 3)]
    offsets = [rng.randrange(-3, span + 3) for _ in range(height + 3)]
    fractions = [float_word(rng.random() * 1.4) for _ in range(height + 3)]
    object_bytes = junk_bytes(rng, 0x5E1C + 4 * (width + 8))
    surface_junk = [junk_bytes(rng, 0xB4) for _ in range(3)]
    effective = bpp if 1 <= bpp <= 16 else 1
    pitch_a = width * effective + rng.randrange(0, 4)
    pitch_b = width * effective + rng.randrange(0, 4)
    pixels_a = junk_bytes(rng, pitch_a * (height + 3) + 8)
    pixels_b = junk_bytes(rng, pitch_b * (height + 3) + 8)
    pixels_c = junk_bytes(rng, pitch_b * (height + 3) + 8)

    def setup(env):
        log = make_log(env)
        this = env.object(len(object_bytes), "fade", data=object_bytes)
        tokens = {"this": this, "log": log}

        def patch(name):
            hook = hooks.get(name)
            return (lambda env_: hook(env_, tokens)) if hook else None

        buffer_a = env.object(len(pixels_a), "pixels-a", data=pixels_a)
        buffer_b = env.object(len(pixels_b), "pixels-b", data=pixels_b)
        buffer_c = env.object(len(pixels_c), "pixels-c", data=pixels_c)
        surface_a = surface_object(env, rng, surface_junk[0], buffer_a, height, width, pitch_a, bpp, "surface-a",
                                   patch("lock-a"), patch("unlock-a"), log, 0)
        surface_b = surface_a
        if not same:
            surface_b = surface_object(env, rng, surface_junk[1], buffer_b, height, width, pitch_b,
                                       bpp if bpp_b is None else bpp_b, "surface-b", patch("lock-b"), patch("unlock-b"), log, 2)
        surface_c = surface_object(env, rng, surface_junk[2], buffer_c, height, width, pitch_b, bpp, "surface-c",
                                   None, None, log, 4)
        tokens.update(surface_a=surface_a, surface_b=surface_b, surface_c=surface_c)
        env.put(this + 0x20, previous)
        env.put(this + 0x38, surface_a, surface_b if two else 0, flag)
        env.put(this + 0x4C, height, width, span)
        for index, value in enumerate(offsets):
            env.put(this + 0x5C + 4 * index, value)
        for index, value in enumerate(fractions):
            env.put(this + 0x3EDC + 4 * index, value)
        for index, value in enumerate(counters):
            env.put(this + 0x1F9C + 4 * index, value)
        for index, value in enumerate(perm):
            env.put(this + 0x5E1C + 4 * index, value)
        script = scripted_rand(rand_values)
        if rand_hook:
            plain = script

            def script(env_, call):
                if env_.calls_so_far(call.function) == 1:
                    rand_hook(env_, tokens)
                return plain(env_, call)
        env.override(RAND, script)
        return tokens

    return setup


def step_case(label, setup, step, function=FADE_STEP):
    return Case(label, function, setup, receiver=lambda t: t["this"], arguments=(step,))


# ---- Array manager used by 0x4c62e0 and 0x4c7180 -----------------------------------------

def manager_object(env, rng, size, capacity, grow_by=0, data=True):
    """A pointer array: data at +8, count at +0xc, capacity at +0x10, growth step at +0x14."""
    mgr = env.object(0x20, "manager", words=junk_words(rng, 8))
    slots = max(capacity, size, 1) + 1 if data else 0
    entries = env.object(slots * 4, "entries", words=junk_words(rng, slots)) if data else 0
    env.put(mgr + 8, entries, size, capacity, grow_by)
    return mgr, entries


MANAGER_STATES = [
    ("empty, no data", 0, 0, 0, False),
    ("size without data", 3, 3, 0, False),
    ("room left", 3, 9, 0, True),
    ("room for exactly one", 5, 6, 0, True),
    ("full, small default step", 2, 2, 0, True),
    ("full, step 4 (31 / 8)", 31, 31, 0, True),
    ("full, step 4 (32 / 8)", 32, 32, 0, True),
    ("full, default step 5", 40, 40, 0, True),
    ("full, explicit step 3", 10, 10, 3, True),
    ("capacity below size, explicit step too small", 10, 4, 2, True),
    ("full, explicit step 25", 7, 7, 25, True),
    ("full, step clamp edge below", 0x1FF8, 0x1FF8, 0, True),
    ("full, step clamp edge", 0x2000, 0x2000, 0, True),
    ("full, step clamped", 0x2008, 0x2008, 0, True),
]


# ---- 0x4c62e0: palette table ---------------------------------------------------------------

def palette_case(label, rng, state, columns, rows, percent, shade, fail_from=None, fail_first=False, bright=False):
    _, size, capacity, grow_by, data = state
    palette = junk_bytes(rng, 1024)
    if bright:
        palette = bytes(rng.randrange(200, 256) for _ in range(1024))
    seed = rng.getrandbits(32)

    def setup(env):
        log = make_log(env)
        mgr, entries = manager_object(env, random.Random(seed), size, capacity, grow_by, data)
        table = env.object(1024, "palette", data=palette)
        if fail_first:
            env.override(NEW, allocate(fail=True))
        elif fail_from:
            env.override(NEW, allocate(fail_from_call=fail_from))
        return {"this": mgr, "palette": table, "log": log, "entries": entries}

    return Case(label, PALETTE_TABLE, setup, receiver=lambda t: t["this"],
                arguments=(lambda t: t["palette"], columns, rows, percent, shade))


# ---- 0x4c7180 and 0x4c7780: list load ------------------------------------------------------

def read_effect(content):
    def effect(env, call):
        if env.calls_so_far(call.function) == 1:
            env.put(call.arguments[0], len(content))
        else:
            count = call.arguments[1]
            env.write(call.arguments[0], (content + bytes(count))[:count])
        return call.arguments[1]
    return effect


def file_services(env, log, content, opens=True, copy_name=True):
    """Stand-ins for the CFile and CString services; the file yields `content` after a four byte size."""
    vtable = env.object(0x80, "cfile-vtable", fill=0)
    reader = env.stub("CFile::Read", "thiscall", 2, traced(log, 8, read_effect(content)))
    env.put(vtable + 0x3C, reader)

    def construct(env, call):
        env.put(call.receiver, vtable)
        return call.receiver

    def copy(env, call):
        env.put(call.receiver, env.get(call.arguments[0]))
        return call.receiver

    env.override(CFILE_CONSTRUCT, traced(log, 0, construct))
    env.override(CFILE_DESTRUCT, traced(log, 1))
    env.override(CFILE_OPEN, traced(log, 2, result=1 if opens else 0))
    env.override(CFILE_CLOSE, traced(log, 3))
    env.override(CSTRING_RELEASE, traced(log, 4))
    env.override(CSTRING_COPY, traced(log, 5, copy))
    return vtable


def list_load_case(label, rng, state, length=None, opens=True, fail_sizes=(), file_name=None):
    _, size, capacity, grow_by, data = state
    length = length if length is not None else 1 + 2 * rng.randrange(0, 30)
    content = junk_bytes(rng, length)
    name = file_name or (b"data\\" + bytes(rng.randrange(97, 123) for _ in range(rng.randrange(3, 12))) + b".pal\0")
    seed = rng.getrandbits(32)

    def setup(env):
        log = make_log(env)
        mgr, entries = manager_object(env, random.Random(seed), size, capacity, grow_by, data)
        text = env.object(len(name), "file-name", data=name)
        file_services(env, log, content, opens)
        if fail_sizes:
            env.override(NEW, allocator(fail_sizes))
        return {"this": mgr, "text": text, "log": log, "entries": entries}

    return Case(label, LIST_LOAD, setup, receiver=lambda t: t["this"], arguments=(lambda t: t["text"],))


def load_file_case(label, rng, length=None, opens=True, old_data=False, fail=False, old_flag=None):
    length = length if length is not None else 1 + 2 * rng.randrange(0, 40)
    content = junk_bytes(rng, length)
    name = b"levels\\" + bytes(rng.randrange(97, 123) for _ in range(rng.randrange(2, 10))) + b".dat\0"
    old_words = junk_words(rng, 3)
    old_bytes = junk_bytes(rng, rng.randrange(1, 40))

    def setup(env):
        log = make_log(env)
        item = env.object(12, "list-item", words=old_words)
        if old_data:
            env.put(item + 8, env.object(len(old_bytes), "previous-data", data=old_bytes))
        else:
            env.put(item + 8, 0)
        if old_flag is not None:
            env.put(item, old_flag)
        text = env.object(len(name), "file-name", data=name)
        file_services(env, log, content, opens)
        if fail:
            env.override(NEW, allocate(fail=True))
        return {"this": item, "text": text, "log": log}

    return Case(label, LOAD_FILE, setup, receiver=lambda t: t["this"], arguments=(lambda t: t["text"],))


# ---- 0x4ed0b0: fade setup -----------------------------------------------------------------------

def setup_case(label, rng, width, height, percent, flag, use_a=True, use_b=True, default_a=True, default_b=True):
    prime = order_size(width, 1)
    rand_values = [rng.randrange(0, 0x8000) for _ in range(2000)]
    tail = max(prime, 1) + 8
    size = max(0x7D5C, 0x5E1C + 4 * tail) + 16
    object_bytes = junk_bytes(rng, size)
    descriptor = junk_words(rng, 6)
    surface_junk = [junk_bytes(rng, 0xB4) for _ in range(4)]

    def setup(env):
        this = env.object(size, "fade", data=object_bytes)
        descriptor_object = env.object(0x18, "descriptor", words=descriptor)

        def surface(index, h, w):
            token = env.object(0xB4, "surface", data=surface_junk[index])
            env.put(token + 0x14, h, w)
            return token

        own_a = surface(0, height, width)
        own_b = surface(1, height + 7, width + 3)
        default_surface_a = surface(2, height + 11, width + 5)
        default_surface_b = surface(3, height + 13, width + 9)
        env.put(this + 0x24, default_surface_a if default_a else 0)
        env.put(this + 0x28, default_surface_b if default_b else 0)
        env.put(descriptor_object + 4, own_a if use_a else 0, own_b if use_b else 0, flag, percent)
        env.override(RAND, scripted_rand(rand_values))
        return {"this": this, "descriptor": descriptor_object, "a": own_a, "b": own_b}

    return Case(label, FADE_SETUP, setup, receiver=lambda t: t["this"], arguments=(lambda t: t["descriptor"],))


# ---- 0x4efb00: column order --------------------------------------------------------------------

def permute_case(label, rng, low, high, generator, fail=False):
    words = order_size(high - low, generator) + 6
    sentinel = junk_words(rng, words)

    def setup(env):
        out = env.object(words * 4, "order", words=sentinel)
        if fail:
            env.override(NEW, allocate(fail=True))
        return {"out": out}

    return Case(label, PERMUTE, setup, arguments=(lambda t: t["out"], low, high, generator))


def cases(random_source):
    rng = random_source

    # ---- 0x4efc40
    def prime_case(value):
        return Case(f"is prime {value}", IS_PRIME, arguments=(value,))

    for value in [-3, 0, 1, 2, 3, 4, 9, 11, 25, 49, 97, 221, 7921, 65537]:
        yield prime_case(value)
    for _ in range(1):
        yield prime_case(rng.randrange(70, 3000))
    yield prime_case(0x80000000)
    yield prime_case(0xFFFFFFFF)

    # ---- 0x4efb00
    for span in [1, 2, 3, 4, 5, 8, 13, 31, 32, 48, 128]:
        low = rng.randrange(-30, 60)
        prime = next_prime(span)
        generator = rng.choice([1, 2, 3, rng.randrange(1, 4 * prime + 2)])
        if generator % prime == 0:
            generator += 1
        yield permute_case(f"order span {span}", rng, low, low + span, generator)
    for low in (-40, 5):
        yield permute_case(f"order from {low} span 19", rng, low, low + 19, 3)
    yield permute_case("order with generator one", rng, 4, 15, 1)
    for low, high in ((9, 9), (-3, -9), (0x7FFFFFFF, 0x7FFFFFFF)):
        yield permute_case(f"order empty range {low}..{high}", rng, low, high, 1)
    yield permute_case("order allocation fails", rng, 3, 20, 5, fail=True)
    yield permute_case("order allocation fails, span 1", rng, 3, 4, 5, fail=True)
    for span in (99999, 100001):
        yield permute_case(f"order beyond the search limit {span}", rng, 7, 7 + span, 1)
    yield permute_case("order beyond the search limit, generator zero", rng, 7, 100008, 0)
    for _ in range(3):
        span = rng.randrange(1, 130)
        prime = next_prime(span)
        generator = rng.randrange(1, 3 * prime)
        if generator % prime == 0:
            generator += 1
        low = rng.randrange(-60, 60)
        yield permute_case(f"order random span {span}", rng, low, low + span, generator)

    # ---- 0x4ed5d0
    def extent_case(label, height, span):
        def setup(env):
            this = env.object(0x80, "fade", data=junk_bytes(rng, 0x80))
            env.put(this + 0x4C, height)
            env.put(this + 0x54, span)
            return {"this": this}
        return Case(label, FADE_EXTENT, setup, receiver=lambda t: t["this"])

    for height, span in ((0, 0), (1, 0), (0, 1), (480, 120), (7, 11), (0x7FFFFFFF, 1), (0xFFFFFFFF, 1), (0x80000000, 0x80000000),
                         (3, 0xFFFFFFFD)):
        yield extent_case(f"extent {height:#x}+{span:#x}", height, span)
    for _ in range(1):
        yield extent_case("extent random", rng.getrandbits(32), rng.getrandbits(32))

    # ---- 0x4ed060, 0x4ed080 and 0x4ed0a0
    def fresh_object(size=0x6000, zero_tail=False):
        data = junk_bytes(rng, size)

        def setup(env):
            return {"this": env.object(size, "fade", data=data)}
        return setup

    for index in range(2):
        yield Case(f"construct over junk {index}", FADE_CONSTRUCT, fresh_object(0x6000 + 16 * index),
                   receiver=lambda t: t["this"])

    def built_object(size=0x6000, vtable=0x514228, junk_tail=True):
        tail = junk_bytes(rng, size - 0x60)
        words = [rng.getrandbits(32) | 1 for _ in range(4)]

        def setup(env):
            this = env.object(size, "fade", fill=0)
            env.put(this, vtable)
            env.put(this + 0x30, 1)
            if junk_tail:
                env.write(this + 0x60, tail)
                env.put(this + 0x38, *words)
                env.put(this + 0x4C, words[0], words[1])
            return {"this": this}
        return setup

    for index in range(3):
        yield Case(f"destruct built object {index}", FADE_DESTRUCT, built_object(0x6000 + 32 * index, junk_tail=index != 0),
                   receiver=lambda t: t["this"])
    yield Case("destruct plain object", FADE_DESTRUCT, built_object(0x6000, 0x5141D8, junk_tail=False),
               receiver=lambda t: t["this"])
    for flags in (0, 1, 2, 3, 0x101, 0xFFFFFFFF):
        yield Case(f"delete with flags {flags:#x}", FADE_DELETE, built_object(0x6000 + 16 * (flags & 7),
                                                                              junk_tail=bool(flags & 2)),
                   receiver=lambda t: t["this"], arguments=(flags,))

    # ---- 0x4ed0b0
    # Every call that gets past the early returns costs about a second (2000 random numbers), so the
    # varied inputs are carried by a limited set of runs; rejected descriptors are nearly free.
    for percent in (-1, 101, 0x7FFFFFFF, 0x80000000):
        yield setup_case(f"setup percent out of range {percent}", rng, rng.randrange(3, 40), rng.randrange(1, 24), percent, 1)
    yield setup_case("setup negative width", rng, -5, rng.randrange(1, 24), 50, 1)
    # (own a, own b, default a, default b) combinations that leave no first surface return early.
    for use_a, use_b, default_a, default_b in ((False, False, False, True), (False, False, False, False), (False, True, False, False),
                                               (False, True, False, True)):
        yield setup_case(f"setup surfaces own {use_a:d}{use_b:d} default {default_a:d}{default_b:d}", rng,
                         rng.randrange(2, 30), rng.randrange(1, 24), rng.randrange(0, 101), rng.choice([0, 1, 5]),
                         use_a, use_b, default_a, default_b)
    # Full runs: width, percent, flag and the surface choice all vary together.
    for width, percent, flag, surfaces in ((1, 0, 0, (True, True, True, True)),
                                           (2, 100, 1, (False, True, True, True)),
                                           (5, 50, 0xFFFFFFFF, (True, False, True, True)),
                                           (25, 50, 0xFFFFFFFF, (True, False, True, False)),
                                           (97, 7, 0, (False, False, True, False)),
                                           (99999, 33, 1, (True, True, False, False)),
                                           (100001, 77, 0x7FFFFFFF, (True, False, False, True)),
                                           (rng.randrange(3, 30), rng.randrange(1, 100), 2, (False, False, True, True)),
                                           (rng.randrange(3, 30), rng.randrange(0, 101), 0, (True, True, True, True))):
        yield setup_case(f"setup width {width} percent {percent} flag {flag:#x}", rng, width, rng.randrange(1, 24), percent, flag,
                         *surfaces)

    # ---- 0x4ed1a0
    def small(rng_):
        width = rng_.randrange(1, 10)
        height = rng_.randrange(2, 10)
        span = rng_.randrange(1, 13)
        return width, height, span

    for index in range(4):
        width, height, span = small(rng)
        step = rng.randrange(1, height + span + 3)
        previous = rng.choice([0, 0, rng.randrange(0, step + 3), rng.randrange(-3, step + 3)])
        bpp = rng.choice([1, 1, 1, 2, 3, 4, 4, 5, 7])
        two = rng.random() < 0.7
        flag = rng.choice([0, 0, 1, 1, 2, 0x80000000]) if two else rng.choice([1, 2])
        same = two and rng.random() < 0.05
        yield step_case(f"step random {index} w{width} h{height} g{span} s{step} p{previous} bpp{bpp} flag{flag}",
                        fade_world(rng, width, height, span, previous, bpp, flag, two, same), step)

    # Hand picked geometry: both clearing modes, wide steps, tiny and large spans.
    for flag in (0, 1):
        for width, height, span, step, previous in ((6, 6, 5, 3, 0), (6, 6, 5, 11, 0), (6, 6, 5, 12, 9), (9, 5, 2, 7, 2)):
            for bpp in (1, 4):
                yield step_case(f"step hand w{width} h{height} g{span} s{step} p{previous} bpp{bpp} flag{flag}",
                                fade_world(rng, width, height, span, previous, bpp, flag), step)
    # Zero step does nothing at all.
    for flag in (0, 1):
        yield step_case(f"step zero, flag {flag}", fade_world(rng, 5, 5, 4, 2, 2, flag), 0)
    # Pixel depth that cannot copy or clear anything.
    for bpp in (0, 0xFFFFFFFF):
        for flag in (0, 1):
            yield step_case(f"step bytes per pixel {bpp:#x} flag {flag}", fade_world(rng, 6, 6, 5, 0, bpp & 0xFFFFFFFF, flag), 11)
    # No second surface.
    for step in (12,):
        yield step_case(f"step single surface {step}", fade_world(rng, 6, 6, 5, 0, 1, 1, two=False), step)
        yield step_case(f"step single surface wide {step}", fade_world(rng, 9, 6, 5, 3, 4, 2, two=False), step)
    # A previous count at or past the step skips the lower rows.
    for previous in (6,):
        yield step_case(f"step previous {previous}", fade_world(rng, 5, 6, 4, previous, 2, 0), 6)
        yield step_case(f"step previous {previous} clear", fade_world(rng, 5, 6, 4, previous, 2, 1), 6)
    # The step is larger than the picture and than the span.
    yield step_case("step beyond the picture", fade_world(rng, 4, 4, 3, 0, 1, 0), 40)
    yield step_case("step beyond the picture, clear", fade_world(rng, 4, 4, 3, 0, 1, 1), 40)
    yield step_case("step exactly the height", fade_world(rng, 4, 4, 3, 0, 1, 0), 4)
    yield step_case("step exactly the span", fade_world(rng, 4, 4, 3, 0, 1, 0), 3)
    yield step_case("step one", fade_world(rng, 7, 6, 6, 0, 1, 0), 1)
    yield step_case("step one, clear", fade_world(rng, 7, 6, 6, 0, 1, 1), 1)
    yield step_case("step negative", fade_world(rng, 4, 4, 3, 0, 1, 1), 0xFFFFFFF0)

    # Stand-ins that change the object while the function works on it.
    def set_words(offset, value):
        return lambda env, tokens: env.put(tokens["this"] + offset, value(env, tokens) if callable(value) else value)

    yield step_case("lock of the first surface lowers the height",
                    fade_world(rng, 6, 6, 5, 0, 1, 0, hooks={"lock-a": set_words(0x4C, 5)}), 8)
    yield step_case("lock of the second surface lowers the span",
                    fade_world(rng, 7, 6, 6, 0, 1, 1, hooks={"lock-b": set_words(0x54, 4)}), 9)
    yield step_case("lock of the first surface lowers the width",
                    fade_world(rng, 8, 6, 5, 0, 2, 0, hooks={"lock-a": set_words(0x50, 5)}), 8)
    yield step_case("lock of the second surface lowers the pixel depth",
                    fade_world(rng, 6, 6, 5, 0, 4, 0, hooks={"lock-b": lambda env, t: env.put(t["surface_a"] + 0xAC, 2)}), 8)
    yield step_case("lock of the first surface clears the second surface",
                    fade_world(rng, 6, 6, 5, 0, 1, 1, hooks={"lock-a": set_words(0x3C, 0)}), 8)
    yield step_case("lock of the first surface installs a second surface",
                    fade_world(rng, 6, 6, 5, 0, 1, 1, two=False,
                               hooks={"lock-a": lambda env, t: env.put(t["this"] + 0x3C, t["surface_b"])}), 8)
    yield step_case("lock of the first surface switches the clearing mode",
                    fade_world(rng, 6, 6, 5, 0, 1, 0, hooks={"lock-a": set_words(0x40, 1)}), 8)
    yield step_case("unlock of the first surface clears the second surface",
                    fade_world(rng, 6, 6, 5, 0, 1, 1, hooks={"unlock-a": set_words(0x3C, 0)}), 8)
    yield step_case("unlock of the first surface swaps the second surface",
                    fade_world(rng, 6, 6, 5, 0, 1, 1, hooks={"unlock-a": lambda env, t: env.put(t["this"] + 0x3C, t["surface_c"])}), 8)
    yield step_case("unlock of the first surface installs the second surface",
                    fade_world(rng, 6, 6, 5, 0, 1, 1, two=False,
                               hooks={"unlock-a": lambda env, t: env.put(t["this"] + 0x3C, t["surface_c"])}), 8)
    yield step_case("first random number lowers the span",
                    fade_world(rng, 9, 7, 6, 0, 1, 1, rand_hook=lambda env, t: env.put(t["this"] + 0x54, 4)), 13)
    yield step_case("first random number lowers the height",
                    fade_world(rng, 9, 7, 6, 0, 1, 0, rand_hook=lambda env, t: env.put(t["this"] + 0x4C, 5)), 13)
    yield step_case("first random number raises the span",
                    fade_world(rng, 9, 7, 3, 0, 1, 1, rand_hook=lambda env, t: env.put(t["this"] + 0x54, 6)), 13)
    yield step_case("first random number changes the width",
                    fade_world(rng, 9, 7, 6, 0, 2, 0, rand_hook=lambda env, t: env.put(t["this"] + 0x50, 4)), 13)

    # ---- 0x4c62e0
    # The cost is proportional to (columns + rows): the manager-state branches all sit before the heavy
    # loop, so they are driven with an empty table size; a few one-unit runs reach each colour loop.
    small_state = ("room left", 3, 9, 0, True)
    for state in MANAGER_STATES:
        yield palette_case(f"palette empty list {state[0]}", rng, state, 0, 0, rng.randrange(-30, 140),
                           rng.randrange(-50, 300))
    yield palette_case("palette columns only", rng, small_state, 1, 0, rng.choice([100, 37, 140]), rng.randrange(0, 300))
    yield palette_case("palette rows only", rng, MANAGER_STATES[4], 0, 1, rng.randrange(20, 200), rng.randrange(20, 300))
    yield palette_case("palette columns only, bright colours saturate", rng, MANAGER_STATES[6], 1, 0, 1000, 1000, bright=True)
    yield palette_case("palette two rows, percent below range", rng, MANAGER_STATES[0], 0, 2, -30, 101)
    yield palette_case("palette first allocation fails", rng, small_state, 1, 1, 50, 50, fail_first=True)
    yield palette_case("palette table allocation fails", rng, small_state, 1, 1, 50, 50, fail_from=2)
    yield palette_case("palette table allocation fails, empty list", rng, MANAGER_STATES[0], 2, 1, 50, 50, fail_from=2)

    # ---- 0x4c7780
    for length in (1, 13, 127):
        yield load_file_case(f"load file {length} bytes", rng, length)
    for index in range(2):
        yield load_file_case(f"load file random {index}", rng)
    for index in range(2):
        yield load_file_case(f"load file over earlier data {index}", rng, old_data=True)
    for flag in (0, 1, 0x55AA):
        yield load_file_case(f"load file with flag {flag:#x}", rng, old_data=bool(flag & 1), old_flag=flag)
    for length in (1, 9):
        yield load_file_case(f"load file open fails {length}", rng, length, opens=False)
    yield load_file_case("load file open fails over earlier data", rng, opens=False, old_data=True)
    yield load_file_case("load file open fails with flag set", rng, opens=False, old_flag=1)
    yield load_file_case("load file allocation fails", rng, 9, fail=True)
    yield load_file_case("load file allocation fails over earlier data", rng, 9, old_data=True, fail=True)
    yield load_file_case("load file allocation fails with flag set", rng, 9, old_flag=1, fail=True)

    # ---- 0x4c7180
    for state in MANAGER_STATES:
        yield list_load_case(f"list load {state[0]}", rng, state)
    for state in MANAGER_STATES[:11:4]:
        yield list_load_case(f"list load, open fails, {state[0]}", rng, state, opens=False)
    for length in (1, 15, 61):
        yield list_load_case(f"list load {length} bytes", rng, MANAGER_STATES[2], length)
    for state in MANAGER_STATES[:5:2]:
        yield list_load_case(f"list load, data allocation fails, {state[0]}", rng, state, 9, fail_sizes=(9,))
    yield list_load_case("list load, data allocation fails, full list", rng, MANAGER_STATES[8], 9, fail_sizes=(9,))
    for _ in range(3):
        state = rng.choice(MANAGER_STATES[:11])
        yield list_load_case(f"list load random {state[0]}", rng, state, opens=rng.random() < 0.8)
