"""Cases for end_of_level_save: End-of-level save path entry."""
from clawparity.cases import Case
from clawparity.fixtures import halt, release, returns

SAVE = 0x49BBC0
NEW = 0x4F63EC
RAND = 0x4A3050
RAISE = 0x546958
GET_FULL_PATH = 0x546AD0
CREATE_FILE = 0x546B00
WRITE_FILE = 0x546AF8
CLOSE_HANDLE = 0x546A04
GET_LAST_ERROR = 0x546B0C
SET_LAST_ERROR = 0x546AB8
TLS_GET = 0x546A7C
LSTRLEN = 0x5469E4
LSTRCPYN = 0x5469CC
INTERLOCKED_DEC = 0x5469E8

RECORD = 0x2644


def cstring(env, value):
    p = env.object(12 + len(value) + 1, "CString")
    env.put(p, 1, len(value), len(value))
    env.write(p + 12, value + b"\0")
    return p + 12


def physical(env, create=None, write=None, close=1):
    """Scripted stand-ins for the operating-system imports. Everything observed goes into a log object."""
    tls = env.object(0x100, "CRT thread data", fill=0)
    errors = env.object(4, "last error", words=[0x57])
    log = env.object(0xC000, "write log", fill=0)
    env.put(log, 0)  # number of bytes logged so far

    env.override(TLS_GET, returns(tls))
    env.override(GET_LAST_ERROR, lambda e, c: e.get(errors))

    def set_error(e, c):
        e.put(errors, c.arguments[0])
        return 0
    env.override(SET_LAST_ERROR, set_error)
    env.override(LSTRLEN, lambda e, c: len(e.cstr(c.arguments[0])))

    def decrement(e, c):
        a = c.arguments[0]
        value = (e.get(a) - 1) & 0xFFFFFFFF
        e.put(a, value)
        return value
    env.override(INTERLOCKED_DEC, decrement)
    env.override(GET_FULL_PATH, returns(0))

    def copy_n(e, c):
        dst, src, count = c.arguments
        if count:
            e.write(dst, e.cstr(src)[:count - 1] + b"\0")
        return dst
    env.override(LSTRCPYN, copy_n)
    env.override(CLOSE_HANDLE, returns(close))
    # CreateFileA: calls_so_far counts the current call, so 1 is the first open (create) and 2 the second (write).
    env.override(CREATE_FILE, create or (lambda e, c: 0x1000 + e.calls_so_far(CREATE_FILE)))

    def write_file(e, c):
        handle, buffer, count, written, overlapped = c.arguments
        n = e.get(log)
        if n + count + 8 <= 0xC000 - 8:
            e.put(log + 4 + n, handle, count)
            e.write(log + 4 + n + 8, e.read(buffer, count))
            e.put(log, n + 8 + count)
        e.put(written, count)
        return 1
    env.override(WRITE_FILE, write or write_file)
    return log


def rand_stream(seed):
    """rand that depends only on the call number, so both sides see the same stream."""
    return lambda e, c: (e.calls_so_far(RAND) * 0x9E37 + seed) & 0x7FFF


def game(name=b"C:\\claw\\save.dat", count=1, records=1, fill_base=0x11, seed=0x5A5A, state=0xC3,
         limit=0x77, header=0xE0, head=True, extra_count=0, **os_options):
    """A save object with `records` list nodes, each holding a distinct 0x2644-byte payload."""
    def setup(env):
        log = physical(env, **os_options)
        this = env.object(0x80, "game", fill=0x6B)
        for i in range(0x20 // 4):
            env.put(this + 0x20 + i * 4, 0xA0A0A0A0 + i)  # header words, overwritten before use
        env.put(this + 0x1C, cstring(env, name))
        env.put(this + 0x0C, count)
        env.put(this + 0x40, limit)
        env.put(this + 0x44, state)
        nodes, payloads = [], []
        for i in range(records):
            node = env.object(12, "list node")
            record = env.object(RECORD + 4, "record")
            env.put(record, 0xDEAD0000 + i)
            env.write(record + 4, bytes(((fill_base + 31 * i + 7 * j + (j >> 8) * 13 + j * j) & 0xFF) for j in range(RECORD)))
            nodes.append(node)
            payloads.append(record)
        for i, node in enumerate(nodes):
            env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0, nodes[i - 1] if i else 0, payloads[i])
        env.put(this + 0x04, nodes[0] if (nodes and head) else 0)
        env.override(RAND, rand_stream(seed))
        return {"this": this, "log": log}
    return setup


def save(label, setup, **options):
    return Case(label, SAVE, setup, receiver=lambda t: t["this"], **options)


def cases(random_source):
    # Early exits.
    yield save("empty file name", game(name=b"", count=2))
    yield save("negative count", game(count=-1, records=1))
    yield save("zero count", game(count=0, records=0))
    for length in (1, 2, 0x7FFF, 0x80000000):
        def setup(env, length=length):
            tokens = game(count=0, records=0)(env)
            name = env.object(16, "name", fill=0x41)
            env.put(name + 4, length)
            env.put(tokens["this"] + 0x1C, name + 12)
            return tokens
        yield save(f"name length {length:#x} with count zero", setup)

    # Open failures.
    yield save("first open fails", game(count=2, records=2, create=lambda e, c: 0xFFFFFFFF))
    yield save("second open fails", game(count=2, records=2,
                                         create=lambda e, c: 0xFFFFFFFF if e.calls_so_far(CREATE_FILE) >= 2 else 0x1234))
    def halting(setup):
        def wrapped(env):
            tokens = setup(env)
            env.override(RAISE, halt())
            return tokens
        return wrapped
    yield save("first close fails", halting(game(count=1, records=1, close=0)), expect="halt")

    # Allocation failure and sizes passed to the allocator.
    def no_memory(env):
        tokens = game(count=2, records=2)(env)
        count = env.get(tokens["this"] + 0x0C)

        def allocate(e, c):
            if c.arguments[0] == count * RECORD:
                return 0
            return e.object(c.arguments[0], name="allocation")
        env.override(NEW, allocate)
        return tokens
    yield save("allocation fails", no_memory)

    # Successful saves.
    for records in (1, 2, 3):
        yield save(f"{records} nodes", game(count=records, records=records, fill_base=0x21 * records))
    yield save("count larger than the list", game(count=4, records=2, fill_base=0x43))
    yield save("count with empty list", game(count=3, records=0, fill_base=0x43))
    yield save("count 1 with one node, different generator state", game(count=1, records=1, seed=1, state=0x12345678, limit=0xFFFFFFFF))
    yield save("null list head with positive count", game(count=2, records=2, head=False))
    yield save("limit zero", game(count=2, records=2, limit=0, state=0))
    for _ in range(4):
        count = random_source.randrange(1, 4)
        yield save(f"random {count} nodes", game(
            name=bytes(random_source.randrange(65, 90) for _ in range(random_source.randrange(1, 20))),
            count=count, records=count, fill_base=random_source.randrange(256),
            seed=random_source.getrandbits(15), state=random_source.getrandbits(32), limit=random_source.getrandbits(32)))

    # Failures of the write itself.
    def short_write(e, c):
        handle, buffer, count, written, overlapped = c.arguments
        e.put(written, count - 1 if count > 1 else 0)
        return 1
    yield save("short write", halting(game(count=1, records=1, write=short_write)), expect="halt")

    def failed_write(e, c):
        e.put(c.arguments[3], 0)
        return 0
    yield save("failed write", halting(game(count=1, records=1, write=failed_write)), expect="halt")
