"""Cases for gameplay_key_down: Gameplay key-down handler and cheat-code buffer."""
from clawparity.cases import Case
from clawparity.fixtures import returns

KEY_DOWN = 0x46BB30
CHEAT = 0x422E00
POST_MESSAGE = 0x546D50
CLOCK = 0x537208
ALPHABET = bytes(range(0x41, 0x6C))  # characters a key in 0x30..0x5a can produce (key + 0x11)


def string_hash(text):
    value = 0
    for byte in text:
        value = (value * 0x21 + (byte if byte < 0x80 else byte - 0x100)) & 0xFFFFFFFF
    return value


def build_map(env, c, size, entries, table=True):
    """Fill the CMapStringToPtr at c+4. entries: (key bytes, command or None, flags); later entries head their chain."""
    env.put(c + 0x04, 0x51A000)  # vtable stand-in
    env.put(c + 0x0C, size)
    env.put(c + 0x10, len(entries))
    if not table:
        env.put(c + 0x08, 0)
        return
    buckets = env.object(4 * size, "hash-table", fill=0)
    env.put(c + 0x08, buckets)
    for index, (key, command, flags) in enumerate(entries):
        text = env.object(len(key) + 1, "key-text", data=key + b"\0")
        entry = 0
        if command is not None:
            entry = env.object(8, "command", fill=0)
            env.put(entry, command & 0xFFFFFFFF, flags)
        assoc = env.object(16, "assoc", fill=0)
        slot = buckets + 4 * (string_hash(key) % size)
        env.put(assoc, env.get(slot), string_hash(key), text, entry)
        env.put(slot, assoc)


def cheat_object(env, rs, count, last, preload=b"", flag=0x77665544, entries=None, size=17, table=True, hwnd=0x00ABCD10):
    data = bytearray(rs.randrange(1, 256) for _ in range(0x12C))
    c = env.object(0x12C, "cheat", data=bytes(data))
    env.put(c, hwnd)
    env.override(POST_MESSAGE, returns(1))
    build_map(env, c, size, entries or [], table)
    env.write(c + 0x20, preload)
    env.put(c + 0x120, count & 0xFFFFFFFF, last & 0xFFFFFFFF, flag)
    return c


def cheat(label, rs, key, now, count=0, last=0, preload=b"", **options):
    def setup(env):
        return {"c": cheat_object(env, rs, count, last, preload, **options)}
    return Case(label, CHEAT, setup, receiver=lambda t: t["c"], arguments=(key & 0xFFFFFFFF, now & 0xFFFFFFFF))


def sequence_case(label, rs, text, entries, delta=100, last=0x20000, **options):
    """Typing the final character of `text` after the earlier ones are already buffered."""
    return cheat(label, rs, text[-1] - 0x11, last + delta, count=len(text) - 1, last=last, preload=text[:-1],
                 entries=entries, **options)


def rand_text(rs, length):
    return bytes(rs.choice(ALPHABET) for _ in range(length))


def key_down(label, rs, key, gate=0, count=0, entries=None, clock=None, **options):
    clock = rs.randrange(0, 1 << 32) if clock is None else clock
    last = options.pop("last", clock)

    def setup(env):
        c = cheat_object(env, rs, count, last, entries=entries, **options)
        app = env.object(0x4C, "app", data=bytes(rs.randrange(1, 256) for _ in range(0x4C)))
        wrapper = env.object(0x10, "window-wrapper", data=bytes(rs.randrange(1, 256) for _ in range(0x10)))
        hwnd = rs.randrange(1, 1 << 32)
        env.put(wrapper + 4, hwnd)
        env.put(app + 4, wrapper)
        env.put(app + 0x0C, gate)
        env.put(app + 0x48, c)
        this = env.object(8, "state", data=bytes(rs.randrange(1, 256) for _ in range(8)))
        env.put(this + 4, app)
        env.put(CLOCK, clock)
        return {"this": this, "c": c}

    return Case(label, KEY_DOWN, setup, receiver=lambda t: t["this"], arguments=(key & 0xFFFFFFFF, rs.randrange(0, 1 << 32)))


def cases(random_source):
    rs = random_source

    # Filtered keys: outside 0x30..0x5a the buffer is cleared
    for key in (0, 1, 0x0D, 0x11, 0x1B, 0x20, 0x25, 0x26, 0x27, 0x28, 0x2F, 0x5B, 0x60, 0x7F, 0xFF, 0x100,
                0x80000000, 0xFFFFFFFF, 0xFFFFFFD0):
        yield cheat(f"key {key:#x} clears buffer", rs, key, 5000, count=rs.randrange(1, 40), last=4900)
    for key in (0x2F, 0x5B):
        yield cheat(f"key {key:#x} clears a full buffer", rs, key, 5000, count=200, last=4900)

    # Accepted keys: every value of the range appends key + 0x11 as a byte
    for key in range(0x30, 0x5B):
        yield cheat(f"key {key:#x} appends", rs, key, 6000 + key, count=rs.randrange(0, 4), last=6000, preload=rand_text(rs, 3))

    # Timeout boundary (unsigned compare of last + 0x5dc against now)
    for delta in (0, 1, 0x5DB, 0x5DC, 0x5DD, 0x5DE, 0x10000):
        yield cheat(f"delta {delta:#x}", rs, 0x41, 0x30000 + delta, count=3, last=0x30000, preload=b"abc")
    for last, now in ((0xFFFFFFFF, 0x10), (0xFFFFFA24, 0xFFFFFFFF), (0xFFFFFA24, 0x0), (0xFFFFFA23, 0xFFFFFFFF), (0x80000000, 0x7FFFFFFF),
                      (0x7FFFFA24, 0x80000000), (0x7FFFFFFF, 0x80000000), (0, 0xFFFFFFFF), (0xFFFFFFFF, 0xFFFFFFFF)):
        yield cheat(f"wrap last {last:#x} now {now:#x}", rs, 0x44, now, count=3, last=last, preload=b"xyz")

    # Count boundary: more than 200 resets, 200 keeps (writes at 0x20 + 200)
    for count in (0, 1, 4, 5, 6, 100, 198, 199, 200, 201, 202, 1000, 0xFFFFFFFF):
        yield cheat(f"count {count:#x} inside timeout", rs, 0x55, 7000, count=count, last=7000 - 50, preload=rand_text(rs, 8))
        yield cheat(f"count {count:#x} timed out", rs, 0x55, 70000, count=count, last=7000, preload=rand_text(rs, 8))

    # Fewer than five keys never reaches the lookup
    for count in range(0, 5):
        yield cheat(f"short buffer {count + 1}", rs, rs.randrange(0x30, 0x5B), 9000, count=count, last=8990, preload=rand_text(rs, count),
                    entries=[(rand_text(rs, 5), 0x1234, 0)])

    # Lookup: five or more keys
    word = rand_text(rs, 5)
    other = bytes(b + 1 if b < 0x6B else b - 1 for b in word)
    yield sequence_case("not found, empty map without table", rs, word, [], table=False)
    yield sequence_case("not found, empty table", rs, word, [])
    yield sequence_case("not found, other word", rs, word, [(other, 0x2001, 0)])
    yield sequence_case("not found, prefix key", rs, word, [(word[:-1], 0x2002, 0), (word[1:], 0x2003, 0)])
    yield sequence_case("not found, longer key", rs, word, [(word + b"a", 0x2004, 0)])
    yield sequence_case("not found, chain of decoys", rs, word, [(other, 0x2005, 0), (word[:-1], 0x2006, 0)], size=1)
    yield sequence_case("found: posts command, flag set", rs, word, [(word, 0x4321, 0)])
    yield sequence_case("found: posts command, bit 0 set keeps flag", rs, word, [(word, 0x4322, 1)])
    for flags in (2, 3, 0x80, 0xFE, 0xFF, 0x100, 0x101):
        yield sequence_case(f"found: flag byte {flags:#x}", rs, word, [(word, 0x4323, flags)])
    for command in (1, 2, 0x7FFFFFFF, 0x8000, 0x80000000, 0xFFFFFFFF, 0):
        yield sequence_case(f"found: command {command:#x}", rs, word, [(word, command, 0)])
    yield sequence_case("found: stored value is null", rs, word, [(word, None, 0)])
    yield sequence_case("found behind decoy in a chain", rs, word, [(word, 0x5001, 0), (other, 0x5002, 0), (word[:-1], 0x5003, 0)], size=1)
    yield sequence_case("found ahead of decoy in a chain", rs, word, [(other, 0x5004, 0), (word, 0x5005, 0)], size=1)
    yield sequence_case("found in a larger table", rs, word, [(rand_text(rs, 5), 0x5006 + i, 0) for i in range(12)] + [(word, 0x5100, 0)], size=7)
    yield sequence_case("found when the buffer was just reset by timeout", rs, word, [(word[-1:] * 5, 0x5200, 0)], delta=0x10000)
    for length in (5, 6, 9, 17, 40):
        text = rand_text(rs, length)
        yield sequence_case(f"found length {length}", rs, text, [(text, 0x6000 + length, 0), (rand_text(rs, length), 0x6100, 0)])
    # a long buffer whose tail the map does not know: no match, buffer kept
    yield sequence_case("found only with the whole buffer", rs, rand_text(rs, 12), [(word, 0x6200, 0)])
    # a match sitting at the 200th byte
    long_text = rand_text(rs, 201)
    yield sequence_case("found at count 200", rs, long_text, [(long_text, 0x6300, 0)])
    yield sequence_case("not found at count 200", rs, long_text, [])
    yield sequence_case("count 200 timed out leaves one key", rs, long_text, [(long_text[-1:], 0x6400, 0)], delta=0x20000)
    for _ in range(40):
        length = rs.randrange(5, 14)
        text = rand_text(rs, length)
        entries = [(rand_text(rs, rs.randrange(3, 14)), rs.randrange(-3, 1 << 16), rs.randrange(0, 256)) for _ in range(rs.randrange(0, 8))]
        if rs.random() < 0.6:
            entries.insert(rs.randrange(0, len(entries) + 1), (text, rs.randrange(-2, 1 << 16), rs.randrange(0, 256)))
        yield sequence_case(f"random sequence {length}", rs, text, entries, delta=rs.choice((0, 5, 0x5DC, 0x5DD, 0x9999)),
                            last=rs.randrange(0, 1 << 32), size=rs.choice((1, 3, 17)), hwnd=rs.randrange(1, 1 << 32))
    for _ in range(25):
        yield cheat("random key stream", rs, rs.randrange(0x20, 0x70), rs.randrange(0, 1 << 32), count=rs.randrange(0, 8),
                    last=rs.randrange(0, 1 << 32), preload=rand_text(rs, 8), entries=[(rand_text(rs, 5), 1, 0)])

    # Gameplay key-down handler
    for gate in (1, 2, 0x80, 0x100, 0x80000000, 0xFFFFFFFF):
        for key in (0x1B, 0x41, 0x25):
            yield key_down(f"gate {gate:#x} key {key:#x}", rs, key, gate=gate, count=3, preload=b"abc")
    for key in (0, 0x1A, 0x1B, 0x1C, 0x20, 0x25, 0x26, 0x27, 0x28, 0x11, 0x2F, 0x30, 0x41, 0x5A, 0x5B, 0xFF, 0x11B, 0x80000000, 0xFFFFFFFF):
        yield key_down(f"open gate key {key:#x}", rs, key, count=rs.randrange(0, 4), preload=rand_text(rs, 3))
    for clock in (0, 1, 0x5DC, 0xFFFFFFFF, 0x80000000):
        yield key_down(f"clock {clock:#x} timed out", rs, 0x41, count=3, clock=clock, last=(clock - 0x1000) & 0xFFFFFFFF, preload=b"abc")
        yield key_down(f"clock {clock:#x} fresh", rs, 0x41, count=3, clock=clock, last=(clock - 5) & 0xFFFFFFFF, preload=b"abc")
    word = rand_text(rs, 5)
    for flags in (0, 1):
        yield key_down(f"cheat posts through the handler flags {flags}", rs, word[-1] - 0x11, clock=40000, last=39900, count=4,
                       preload=word[:-1], entries=[(word, 0x7001, flags)])
    for _ in range(25):
        yield key_down("random handler call", rs, rs.choice((0x1B, 0x1B, rs.randrange(0, 0x100), rs.randrange(0, 1 << 32))),
                       gate=rs.choice((0, 0, 0, rs.randrange(0, 1 << 32))), count=rs.randrange(0, 8), preload=rand_text(rs, 8),
                       entries=[(rand_text(rs, 5), 3, 0)])
