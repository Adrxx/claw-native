"""Cases for level_one_closure_engine_misc_01: message drawing, single-frame message,
timer, music and registry helpers.

Every branch has deterministic cases; random_source only adds variation (string
contents, stale words, extra shapes), never coverage.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns

OPERATOR_NEW = 0x4F63EC
OPERATOR_DELETE = 0x4F6428
FREE = 0x4A49B0
LSTRLEN = 0x5469E4
INTERLOCKED_DECREMENT = 0x5469E8
INTERLOCKED_INCREMENT = 0x5469EC
DRAW_TEXT = 0x546D30
SELECT_OBJECT = 0x54691C
CFILE_CTOR = 0x4F72C9
CFILE_DTOR = 0x4F7369
CFILE_OPEN = 0x4F7448
CFILE_LENGTH = 0x4F774D
CFILE_READ = 0x4F7570

TEXT_BUFFER = 0x534EF8
SEPARATOR = 0x5250D8
SCREEN_RECT = 0x5370C8
TIMER_COUNT = 0x544D18
TIMER_TABLE = 0x544B98

U32 = 0xFFFFFFFF


def atomic(delta):
    def effect(env, call):
        address = call.arguments[0]
        value = (env.get(address) + delta) & U32
        env.put(address, value)
        return value
    return effect


def runtime_stand_ins(env):
    """Scripted C runtime / platform behavior shared by the original CString helpers."""
    env.override(LSTRLEN, lambda e, c: len(e.cstr(c.arguments[0])))
    env.override(INTERLOCKED_DECREMENT, atomic(-1))
    env.override(INTERLOCKED_INCREMENT, atomic(1))


def cstring(env, text, refs=1, name="CString"):
    """A MFC-style CString buffer: refs, length, allocated length, characters. Returns the data pointer."""
    raw = text.encode("latin-1")
    header = env.object(12 + len(raw) + 1, name, words=[refs & U32, len(raw), len(raw)])
    env.write(header + 12, raw + b"\0")
    return header + 12


# --------------------------------------------------------------------------------------
# 0x4226b0: draw the first N messages of a list into a device context
# --------------------------------------------------------------------------------------
DRAW = 0x4226B0


def message_list(env, texts, refs, link_nodes=True):
    """Singly linked list: node = [next, tag, CString data pointer]. Returns (head, nodes, strings)."""
    nodes, strings = [], []
    for index, text in enumerate(texts):
        string = cstring(env, text, refs[index % len(refs)], f"message text {index}")
        node = env.object(16, f"message node {index}", words=[0, 0x7000 + index, string, 0x1357 + index])
        # The CString pointer lives at node + 8 as a one-word CString object.
        nodes.append(node)
        strings.append(string)
    for index, node in enumerate(nodes[:-1]):
        env.put(node, nodes[index + 1])
    return (nodes[0] if nodes else 0), nodes, strings


def draw_setup(texts, count, font=0, old_font=0, refs=(1,), separator=None, stale=b"stale text from earlier draw",
               draw_result=0x31, extra_nodes_after=0, terminate_early=False):
    def setup(env):
        runtime_stand_ins(env)
        head, nodes, strings = message_list(env, texts, refs)
        owner = env.object(0x44, "message list", fill=0x6B)
        env.put(owner + 4, head, count if False else 0)
        env.put(owner + 0xC, count)
        env.put(owner + 0x34, font)
        rect = env.object(16, "draw rectangle", words=[0x11, 0x22, 0x333, 0x444])
        log = env.object(64, "gdi observations", fill=0)
        env.write(TEXT_BUFFER, stale + b"\0")
        if separator is not None:
            env.write(SEPARATOR, separator + b"\0")

        def select(e, call):
            n = e.calls_so_far(SELECT_OBJECT)
            e.put(log + 8 * (n - 1), call.arguments[0], call.arguments[1])
            return old_font if n == 1 else 0x7777

        def draw(e, call):
            rect_pointer = call.arguments[3]
            first, last = (e.get(rect_pointer), e.get(rect_pointer + 12)) if rect_pointer else (0, 0)
            e.put(log + 16, call.arguments[0], call.arguments[2], first, last,
                  call.arguments[4], len(e.cstr(call.arguments[1])))
            return draw_result

        env.override(SELECT_OBJECT, select)
        env.override(DRAW_TEXT, draw)
        return {"owner": owner, "rect": rect, "log": log, "nodes": nodes, "strings": strings}
    return setup


def draw_case(label, setup, limit, hdc=0x5AA5, fmt=0x2C, rect=True):
    return Case(label, DRAW, setup, receiver=lambda t: t["owner"],
                arguments=(limit & U32, hdc, (lambda t: t["rect"]) if rect else 0, fmt))


def cases(random_source):
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !?-"

    def word(length):
        return "".join(random_source.choice(letters) for _ in range(length))

    def rnd():
        return random_source.randrange(1, 2 ** 32)

    # ---- 0x4226b0 -------------------------------------------------------------------
    base_texts = ["alpha", "be", "gamma-ray", "d", "epsilon!"]
    # null device context, empty/negative list counts and non-positive limits all return 0
    yield draw_case("draw: null hdc", draw_setup(base_texts, 5), 5, hdc=0)
    for count in (0, -1, -7, 0x80000000):
        yield draw_case(f"draw: list count {count & U32:#x}", draw_setup(base_texts, count), 3)
    for limit in (0, -1, -100, 0x80000000):
        yield draw_case(f"draw: limit {limit & U32:#x}", draw_setup(base_texts, 5), limit)

    # limit versus stored count: limit smaller, equal, larger; one to five messages
    for count in (1, 2, 3, 5):
        for limit in (1, 2, 3, 4, 5, 6, 0x7FFFFFFF):
            texts = base_texts[:count]
            yield draw_case(f"draw: {count} nodes count {count} limit {limit}", draw_setup(texts, count), limit)
    # stored count larger than the real list: the walk meets the end of the list
    for count, limit in ((4, 4), (5, 3), (5, 5), (3, 9), (6, 6)):
        yield draw_case(f"draw: short list of 2, count {count} limit {limit}", draw_setup(base_texts[:2], count), limit)
    yield draw_case("draw: empty list with count 3", draw_setup([], 3), 3)
    # separator only between visible messages: boundary where limit - 1 == index
    for limit in (1, 2, 3):
        yield draw_case(f"draw: separator boundary limit {limit}", draw_setup(["xy", "pqr", "stuvw", "z"], 4), limit)

    # string lengths 0..12 so that each dword/byte tail of the string copy is exercised
    for length in range(0, 13):
        text = word(length)
        yield draw_case(f"draw: single string length {length}", draw_setup([text], 1, stale=b"S" * (length % 5 + 3)), 1)
        yield draw_case(f"draw: two strings, first length {length}",
                        draw_setup([text, word(13 - length)], 2), 2)
    for lengths in ((0, 0, 0), (0, 4, 0), (1, 0, 7), (8, 8, 8), (3, 12, 5, 6)):
        texts = [word(length) for length in lengths]
        yield draw_case(f"draw: lengths {lengths}", draw_setup(texts, len(texts)), len(texts))

    # custom separators of different lengths (the copy of the separator uses the same word/byte split)
    for separator in (b"", b"|", b"; ", b"---", b" <> ", b"=== sep ==="):
        yield draw_case(f"draw: separator {separator!r}", draw_setup(base_texts[:3], 3, separator=separator), 3)

    # stale text from an earlier call must be discarded
    yield draw_case("draw: stale buffer long", draw_setup(["new"], 1, stale=b"X" * 90), 1)
    yield draw_case("draw: stale buffer empty", draw_setup(["new"], 1, stale=b""), 1)

    # fonts: none; selected with no previous object; selected with a previous object restored afterwards
    for font, old in ((0, 0), (0, 0x6001), (0x1234, 0), (0x1234, 0x6001), (0x80000001, 0x80000002)):
        yield draw_case(f"draw: font {font:#x} previous {old:#x}", draw_setup(base_texts[:3], 3, font=font, old_font=old), 3)
    # null rectangle pointer and unusual formats pass straight through
    yield draw_case("draw: null rect", draw_setup(base_texts[:2], 2), 2, rect=False)
    for fmt in (0, 1, 0x25, 0xFFFFFFFF):
        yield draw_case(f"draw: format {fmt:#x}", draw_setup(base_texts[:2], 2, font=0x99, old_font=0x98), 2, fmt=fmt)
    for hdc in (1, 0xFFFFFFFF):
        yield draw_case(f"draw: hdc {hdc:#x}", draw_setup(base_texts[:2], 2, font=0x99, old_font=0x98), 2, hdc=hdc)

    # reference counts: shared strings stay alive (1, 2, 40); an unshared zero-count string is released
    for refs in ((1,), (2,), (40,), (0,), (0, 1, 3), (3, 0)):
        yield draw_case(f"draw: refs {refs}", draw_setup(base_texts[:4], 4, refs=refs), 4)
    # locked (negative reference count) strings are copied instead of shared
    for locked in ((-1,), (-1, 1), (1, -1), (-5,)):
        yield draw_case(f"draw: locked refs {locked}", draw_setup(base_texts[:3], 3, refs=locked), 3)

    # random shapes
    for number in range(40):
        size = random_source.randrange(1, 7)
        texts = [word(random_source.randrange(0, 15)) for _ in range(size)]
        count = random_source.randrange(1, 9)
        limit = random_source.randrange(-1, 9)
        refs = tuple(random_source.choice((0, 1, 2, 7)) for _ in range(random_source.randrange(1, 4)))
        font = random_source.choice((0, rnd()))
        old = random_source.choice((0, rnd()))
        sep = random_source.choice((None, None, word(random_source.randrange(0, 6)).encode()))
        yield draw_case(f"draw: random {number}", draw_setup(texts, count, font, old, refs, sep,
                                                              stale=word(random_source.randrange(0, 20)).encode()),
                        limit, hdc=rnd(), fmt=rnd())

    # ---- 0x491970 -------------------------------------------------------------------
    for case in message_screen_cases(random_source):
        yield case

    # ---- 0x490c00 -------------------------------------------------------------------
    for case in timer_start_cases(random_source):
        yield case

    # ---- 0x4b5720 -------------------------------------------------------------------
    for case in music_file_cases(random_source):
        yield case

    # ---- 0x4b3d50 / 0x4db6a0 / 0x4dbd00 --------------------------------------------
    for case in destructor_cases(random_source):
        yield case


# --------------------------------------------------------------------------------------
# 0x491970: single-frame message screen
# --------------------------------------------------------------------------------------
SCREEN = 0x491970


def name_hash(text):
    value = 0
    for byte in text.encode():
        value = (value * 0x21 + (byte if byte < 128 else byte - 256)) & U32
    return value


def screen_setup(state, key, lo=2, hi=6, present=True, empty_buckets=False, chain_first=False, buckets=17,
                 rect=(0x10, 0x20, 0x41, 0x56), no_bucket_array=False, seed=0x31):
    def setup(env):
        env.put(SCREEN_RECT, *[v & U32 for v in rect])
        owner = env.object(0x180, "message screen", fill=0xA3)
        phase = env.object(0x20, "screen phase", fill=0x5C)
        env.put(phase + 0x1C, state & U32)
        env.put(owner + 4, key & U32)
        env.put(owner + 8, 0x1200 + seed)
        env.put(owner + 0x6C, phase)
        env.put(owner + 0x4C, 0xAAAA0001, 0xBBBB0002)
        env.put(owner + 0x16C, 0xC0C0C0C1, 0xD0D0D0D2, 0xE0E0E0E3)
        table = env.object(0x30, "resource table owner", fill=0x2E)
        holder = env.object(0x20, "resource holder", fill=0x3F)
        env.put(owner + 0xC, holder)
        env.put(holder + 0x10, table)
        # the map is embedded at table + 0x10: [vtable, buckets, bucket count, ...]
        values = env.object(0x70, "message resource", fill=0x81)
        array = env.object(4 * (max(hi, 0) + 1), "message resource entries",
                           words=[0x70000000 + seed * 16 + i for i in range(max(hi, 0) + 1)])
        env.put(values + 0x14, array)
        env.put(values + 0x64, lo & U32, hi & U32)
        if no_bucket_array:
            env.put(table + 0x14, 0, buckets)
        else:
            bucket_array = env.object(4 * buckets, "map buckets", fill=0)
            env.put(table + 0x14, bucket_array, buckets)
            wanted = name_hash("GAME_MESSAGES")
            index = wanted % buckets
            other_key = cstring(env, "OTHER_MESSAGES", 1, "other key")
            real_key = cstring(env, "GAME_MESSAGES", 1, "real key")
            chain = []
            if present and not empty_buckets:
                chain.append(env.object(16, "map node", words=[0, wanted, real_key, values]))
            if (chain_first or not present) and not empty_buckets:
                chain.insert(0, env.object(16, "other map node", words=[0, name_hash("OTHER_MESSAGES"), other_key, 0x99999999]))
            for node, following in zip(chain, chain[1:]):
                env.put(node, following)
            if chain:
                env.put(bucket_array + 4 * index, chain[0])
            if not present:
                # occupy a neighbouring bucket too, so a wrong bucket index finds something
                env.put(bucket_array + 4 * ((index + 1) % buckets), chain[0] if chain else 0)
        return {"owner": owner, "phase": phase}
    return setup


def screen_case(label, setup):
    return Case(label, SCREEN, setup, arguments=(lambda t: t["owner"],))


def message_screen_cases(random_source):
    # state 5: only the flag is set; any other nonzero state does nothing; no map is read
    for state in (5, 1, 2, 3, 4, 6, 0x10, -1, 0x80000000, 0x100000005):
        yield screen_case(f"screen: state {state & U32:#x}", screen_setup(state & U32, 3))
    # state 0: set state 5, load the resource, then centre
    for key in (2, 3, 5, 6):
        yield screen_case(f"screen: new frame key {key} in range 2..6", screen_setup(0, key))
    for key in (1, 7, 0, -1, 0x7FFFFFFF, 0x80000000):
        yield screen_case(f"screen: new frame key {key & U32:#x} out of range 2..6", screen_setup(0, key))
    yield screen_case("screen: single-entry range", screen_setup(0, 4, lo=4, hi=4))
    yield screen_case("screen: range starts at zero", screen_setup(0, 0, lo=0, hi=3))
    yield screen_case("screen: collision chain", screen_setup(0, 3, chain_first=True))
    yield screen_case("screen: resource absent, chain of other key", screen_setup(0, 3, present=False))
    yield screen_case("screen: resource absent, empty bucket", screen_setup(0, 3, present=False, empty_buckets=True))
    yield screen_case("screen: map without buckets", screen_setup(0, 3, no_bucket_array=True))
    for buckets in (1, 2, 7, 29):
        yield screen_case(f"screen: {buckets} buckets", screen_setup(0, 3, buckets=buckets))
    # centring uses signed halves: odd, negative, large and zero extents
    for rect in ((0, 0, 0, 0), (0, 0, 1, 1), (0, 0, 3, 5), (10, 20, 11, 22), (-3, -5, 4, 8), (-10, -20, -5, -3),
                 (7, 9, 2, 4), (5, 5, 5, 5), (0x100, 0x80, 0x500, 0x380), (-1, -1, 0, 0), (0x7FFFFFF0, 0x7FFFFFF0, 0x7FFFFFFF, 0x7FFFFFFF)):
        yield screen_case(f"screen: rect {rect}", screen_setup(0, 3, rect=rect))
    for number in range(8):
        rect = tuple(random_source.randrange(-3000, 3000) for _ in range(4))
        lo = random_source.randrange(0, 5)
        hi = lo + random_source.randrange(0, 6)
        yield screen_case(f"screen: random {number}",
                          screen_setup(random_source.choice((0, 0, 5, 2)), random_source.randrange(-1, hi + 3), lo, hi,
                                       rect=rect, seed=random_source.randrange(1, 200)))


# --------------------------------------------------------------------------------------
# 0x490c00: start a timer-like service
# --------------------------------------------------------------------------------------
TIMER = 0x490C00


def timer_setup(flags, alt_flags=0x20, relocate=False, rewrite_flags=False, words=None):
    words = words or (0x1111, 0x2222, 0x3333)

    def setup(env):
        owner = env.object(0x30, "timer owner", fill=0x4D)
        state = env.object(0x180, "timer state", fill=0x6E)
        alternate = env.object(0x180, "alternate state", fill=0x7F)
        middle = env.object(0x20, "timer service holder", fill=0x42)
        service = env.object(0x20, "timer service", fill=0x24)
        vtable = env.object(0x40, "timer service methods", fill=0)
        log = env.object(48, "start observations", fill=0)
        env.put(owner + 0x1C, 0xAB, 0xCD)
        env.put(owner + 0x24, state)
        env.put(state + 0xC, middle)
        env.put(middle + 0xC, service)
        env.put(service, vtable)
        env.put(state + 0x40, flags)
        env.put(alternate + 0x40, alt_flags)
        env.put(state + 0x4C, words[0], words[1])
        env.put(state + 0x174, words[2])
        env.put(alternate + 0x4C, 0xF1, 0xF2)

        def start(e, call):
            e.put(log, call.receiver, call.arguments[0], call.arguments[1], call.arguments[2])
            if relocate:
                e.put(owner + 0x24, alternate)
            if rewrite_flags:
                e.put(state + 0x40, 0x60)
            return 0x5A5A

        env.put(vtable + 0x28, env.stub("timer service start", "thiscall", 3, start))
        return {"owner": owner, "state": state, "alternate": alternate, "log": log}
    return setup


def timer_start_cases(random_source):
    for flags in (0, 1, 2, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF, 0x12345670):
        yield Case(f"timer start: flags {flags:#x}", TIMER, timer_setup(flags), receiver=lambda t: t["owner"])
    yield Case("timer start: owner re-read after callback", TIMER, timer_setup(0x8, relocate=True),
               receiver=lambda t: t["owner"])
    yield Case("timer start: flags re-read after callback", TIMER, timer_setup(0x1, rewrite_flags=True),
               receiver=lambda t: t["owner"])
    yield Case("timer start: callback rewrites flags and state", TIMER, timer_setup(0x2, relocate=True, rewrite_flags=True),
               receiver=lambda t: t["owner"])
    for _ in range(4):
        words = tuple(random_source.randrange(1, 2 ** 32) for _ in range(3))
        yield Case("timer start: random words", TIMER,
                   timer_setup(random_source.randrange(0, 2 ** 32), random_source.randrange(0, 2 ** 32), words=words),
                   receiver=lambda t: t["owner"])


# --------------------------------------------------------------------------------------
# 0x4b5720: load a music file or forward the name
# --------------------------------------------------------------------------------------
MUSIC = 0x4B5720


def music_setup(name, length=16, open_result=1, read_delta=0, alloc_fail=False, data=None, result_direct=0x7001,
                result_loaded=0x7002, stale_buffer=0xDEAD0001, alloc_fail_always=False):
    def setup(env):
        owner = env.object(0x70, "music object", fill=0x93)
        vtable = env.object(0x48, "music object methods", fill=0)
        log = env.object(0x100, "music observations", fill=0)
        padding = b"\x2e" * (8 - (len(name) + 1) % 4)  # the original's string search reads whole words
        text = env.object(len(name) + 1 + len(padding), "music name", data=name + b"\0" + padding)
        payload = data if data is not None else bytes(((i * 37 + 11) ^ 0xA5) & 0xFF for i in range(max(length, 0) & 0xFFFF))
        env.put(owner, vtable)
        env.put(owner + 0x5C, stale_buffer)

        def forward(e, call):
            e.put(log, call.receiver, call.arguments[0], call.arguments[1], e.get(owner + 0x5C))
            return result_direct

        def load(e, call):
            e.put(log + 16, call.receiver, call.arguments[0], call.arguments[1], call.arguments[2], e.get(owner + 0x5C))
            e.write(log + 0x40, e.read(call.arguments[0], min(32, e.spans.get(call.arguments[0], 0))))
            return result_loaded

        env.put(vtable + 0x3C, env.stub("music forward name", "thiscall", 2, forward))
        env.put(vtable + 0x14, env.stub("music load data", "thiscall", 3, load))

        def construct(e, call):
            e.put(call.receiver, 0xC1C1C1C1, 0xC2C2C2C2, 0xC3C3C3C3, 0xC4C4C4C4)
            return call.receiver

        def destruct(e, call):
            n = e.calls_so_far(CFILE_DTOR)
            e.put(log + 0x80 + 24 * (n - 1), call.receiver, e.get(call.receiver), e.get(call.receiver + 12))
            return 0

        def opened(e, call):
            e.put(log + 0xE0, call.receiver, call.arguments[0], call.arguments[1], call.arguments[2])
            e.put(call.receiver + 4, 0xFEEDF00D)
            return open_result

        def read(e, call):
            e.write(call.arguments[0], payload[:call.arguments[1]])
            e.put(call.receiver + 8, call.arguments[1])
            return (call.arguments[1] + read_delta) & U32

        env.override(CFILE_CTOR, construct)
        env.override(CFILE_DTOR, destruct)
        env.override(CFILE_OPEN, opened)
        env.override(CFILE_LENGTH, returns(length & U32))
        env.override(CFILE_READ, read)
        if alloc_fail:
            env.override(OPERATOR_NEW, allocate(fail=True))
        return {"owner": owner, "text": text, "log": log}
    return setup


def music_case(label, setup, argument=0x4D55):
    return Case(label, MUSIC, setup, receiver=lambda t: t["owner"], arguments=(lambda t: t["text"], argument))


def music_file_cases(random_source):
    # names without the extension separator are forwarded to the virtual method
    for name in (b"", b"plainname", b"dir/track", b"no-dot-here_2", b"x"):
        yield music_case(f"music: name without dot {name!r}", music_setup(name), argument=random_source.randrange(0, 2 ** 32))
    # names with the separator at different places load the file
    for name in (b"track.xmi", b".", b".hidden", b"a.", b"dir.d/file.mid", b"x.y.z", b"MUSIC\\LEVEL1.XMI"):
        yield music_case(f"music: dotted name {name!r}", music_setup(name, length=24), argument=random_source.randrange(0, 2 ** 32))
    # open failure
    yield music_case("music: open fails", music_setup(b"a.xmi", open_result=0))
    # length boundaries: below 4 fails, 4 and up reads
    for length in (0, 1, 2, 3):
        yield music_case(f"music: length {length} is too short", music_setup(b"a.xmi", length=length))
    for length in (4, 5, 7, 8, 63, 300):
        yield music_case(f"music: length {length} loads", music_setup(b"b.xmi", length=length))
    # huge unsigned length: unsigned compare, then the allocation fails
    for length in (0x80000000, 0xFFFFFFFF, 0xFFFFFFF0):
        yield music_case(f"music: length {length:#x} allocation fails", music_setup(b"a.xmi", length=length, alloc_fail=True))
    yield music_case("music: allocation fails", music_setup(b"a.xmi", length=40, alloc_fail=True))
    yield music_case("music: allocation fails at minimum", music_setup(b"a.xmi", length=4, alloc_fail=True))
    # short, long and empty reads
    for delta in (-1, 1, 0xFFFFFFFF, 0x10000):
        yield music_case(f"music: read returns length{delta & U32:+#x}", music_setup(b"a.xmi", length=20, read_delta=delta))
    yield music_case("music: read returns zero", music_setup(b"a.xmi", length=20, read_delta=-20))
    # the loaded result passes through
    for result in (0, 1, 0x80004005, 0xFFFFFFFF):
        yield music_case(f"music: loader returns {result:#x}", music_setup(b"a.xmi", length=12, result_loaded=result))
    for result in (0, 0xFFFFFFFF):
        yield music_case(f"music: forwarder returns {result:#x}", music_setup(b"nodot", result_direct=result))
    # random payloads
    for number in range(8):
        length = random_source.randrange(4, 200)
        payload = bytes(random_source.randrange(0, 256) for _ in range(length))
        yield music_case(f"music: random payload {number}", music_setup(b"r%d.xmi" % number, length=length, data=payload,
                                                                        result_loaded=random_source.randrange(0, 2 ** 32),
                                                                        stale_buffer=random_source.randrange(1, 2 ** 32)),
                         argument=random_source.randrange(0, 2 ** 32))


# --------------------------------------------------------------------------------------
# 0x4b3d50, 0x4db6a0, 0x4dbd00: scalar-deleting destructors
# --------------------------------------------------------------------------------------
BASIC = 0x4B3D50
REGISTERED = 0x4DB6A0
BUFFERED = 0x4DBD00

FLAG_VALUES = (0, 1, 2, 3, 0xFFFFFFFE, 0xFFFFFFFF, 0x80000000, 0x80000001)


def timer_table(env, this, count, found_at):
    """Sorted registry table at TIMER_TABLE; `this` sits at index found_at (None: absent, then count entries all differ)."""
    env.put(TIMER_COUNT, count)
    for index in range(count):
        if found_at is None:
            key = this + 0x40 * (index - count // 2) + (0x20 if index >= count // 2 else -0x20)
        else:
            key = this + 0x40 * (index - found_at)
        env.put(TIMER_TABLE + 12 * index, key & U32, 0x9000 + index, 0xA000 + index)


def registered_setup(count=0, found_at=None, size_field=0x10, with_buffer=False, vtable=0x11223344):
    def setup(env):
        this = env.object(0x20, "registered object", fill=0x35)
        registry = env.object(16, "registry", words=[0x1111, 0x2222, 0x3333, 0x4444])
        buffer = env.object(0x80, "owned buffer", fill=0x91)
        env.put(this, vtable)
        env.put(this + 4, registry)
        env.put(this + 8, size_field & U32, buffer)
        timer_table(env, this, count, found_at)
        return {"this": this, "registry": registry, "buffer": buffer}
    return setup


def destructor_cases(random_source):
    for flags in FLAG_VALUES + (4, 6, 0x100, random_source.randrange(0, 2 ** 32) | 1, random_source.randrange(0, 2 ** 32) & ~1):
        def setup(env, flags=flags):
            this = env.object(0x18, "base object", fill=0x35)
            env.put(this, 0x0BAD0000 + (flags & 0xFFFF))
            env.put(this + 4, 0x7A7A7A7A)
            return {"this": this}
        yield Case(f"base destructor: flags {flags:#x}", BASIC, setup, receiver=lambda t: t["this"], arguments=(flags,))

    # registered object: registry table states
    shapes = [(0, None), (1, 0), (1, None), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2), (3, None), (4, None), (8, 4), (8, 7), (8, 0),
              (12, 5), (31, 15), (32, 31), (32, 0)]
    for count, found in shapes:
        for flags in (0, 1):
            yield Case(f"registered destructor: table {count} found {found} flags {flags}", REGISTERED,
                       registered_setup(count, found), receiver=lambda t: t["this"], arguments=(flags,))
    for flags in (2, 3, 0xFFFFFFFE, 0xFFFFFFFF, 0x80000000):
        yield Case(f"registered destructor: flags {flags:#x}", REGISTERED, registered_setup(5, 2),
                   receiver=lambda t: t["this"], arguments=(flags,))

    # buffered object: owned buffer freed only above 0x20 (unsigned compare)
    for size in (0, 1, 0x1F, 0x20, 0x21, 0x22, 0x100, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for flags in (0, 1):
            yield Case(f"buffered destructor: size {size:#x} flags {flags}", BUFFERED,
                       registered_setup(3, 1, size_field=size), receiver=lambda t: t["this"], arguments=(flags,))
    for count, found in ((0, None), (1, 0), (4, None), (6, 5), (9, 3)):
        yield Case(f"buffered destructor: table {count} found {found}", BUFFERED,
                   registered_setup(count, found, size_field=0x40), receiver=lambda t: t["this"], arguments=(1,))
    for number in range(10):
        count = random_source.randrange(0, 33)
        found = random_source.randrange(0, count) if count and random_source.randrange(0, 3) else None
        size = random_source.choice((0x10, 0x20, 0x21, random_source.randrange(0, 2 ** 32)))
        function = random_source.choice((REGISTERED, BUFFERED))
        yield Case(f"registry destructors: random {number}", function,
                   registered_setup(count, found, size_field=size, vtable=random_source.randrange(1, 2 ** 32)),
                   receiver=lambda t: t["this"], arguments=(random_source.randrange(0, 2 ** 32),))
