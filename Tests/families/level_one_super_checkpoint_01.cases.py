"""Cases for level_one_super_checkpoint_01: Level 1 super checkpoint attack.

Deterministic cases come first and reach every branch on their own; random
cases are added on top and never decide coverage.
"""
from clawparity.cases import Case
from clawparity.fixtures import sequence

CRC = 0x49BF70
INIT = 0x49BFB0
STEP = 0x49C000
CRYPT = 0x49C030
CRYPT_WRAP = 0x49C070
RAND = 0x4A3050
POLY_TABLE = 0x52D780
OBJECT_SIZE = 0x60
LARGE = 0x1000000


def mask32(value):
    return value & 0xFFFFFFFF


def lfsr_object(env, bound, mask, poly, state, seed=0x1234567):
    """A 0x60 byte object with distinct non-zero contents around the generator fields."""
    obj = env.object(OBJECT_SIZE, "generator", fill=0)
    words = [0x11111111 * (i % 7 + 1) + i for i in range(OBJECT_SIZE // 4)]
    env.put(obj, *words)
    env.put(obj + 0x44, seed)
    env.put(obj + 0x48, bound, mask, poly, state)
    return obj


# ---- checksum -------------------------------------------------------------

def crc_case(label, data, length=None, null=False):
    def setup(env):
        buf = env.object(max(1, len(data)), "data", data=bytes(data) if data else b"\x00")
        return {"buf": buf}
    n = len(data) if length is None else length
    return Case(label, CRC, setup, arguments=((lambda t: 0) if null else (lambda t: t["buf"]), n))


def crc_cases(rs):
    yield crc_case("crc null buffer", b"\x01\x02\x03", null=True)
    yield crc_case("crc null buffer zero length", b"", length=0, null=True)
    yield crc_case("crc zero length", b"\x55\xaa", length=0)
    yield crc_case("crc nonnull zero length distinct", b"\xde\xad\xbe\xef", length=0)
    for n in range(1, 9):
        yield crc_case(f"crc ascending {n}", bytes(range(1, n + 1)))
    yield crc_case("crc all byte values", bytes(range(256)))
    yield crc_case("crc all byte values reversed", bytes(range(255, -1, -1)))
    yield crc_case("crc prefix only", bytes(range(10, 30)), length=7)
    yield crc_case("crc length one of many", b"\x7f\x80\x81\x82", length=1)
    yield crc_case("crc zeros", bytes(16))
    yield crc_case("crc 0xff", b"\xff" * 16)
    yield crc_case("crc high bytes", bytes([0x80 + i for i in range(40)]))
    yield crc_case("crc order sensitive a", b"\x01\x02\x03\x04\x05")
    yield crc_case("crc order sensitive b", b"\x05\x04\x03\x02\x01")
    for i in range(16):
        n = rs.randrange(1, 120)
        yield crc_case(f"crc random {i}", bytes(rs.randrange(256) for _ in range(n)))


# ---- generator initialisation --------------------------------------------

def init_case(label, bound, rand_value, seed_fill=0):
    def setup(env):
        obj = env.object(OBJECT_SIZE, "generator", fill=0)
        env.put(obj, *[0x01010101 * (i % 9 + 1) + 3 * i for i in range(OBJECT_SIZE // 4)])
        env.override(RAND, sequence(rand_value))
        return {"obj": obj}
    return Case(label, INIT, setup, receiver=lambda t: t["obj"], arguments=(bound,))


INIT_BOUNDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 15, 16, 17, 31, 32, 33, 100, 255, 256, 257, 0x7FFF, 0x8000,
               0xFFFF, 0x10000, 0xFFFFFF, LARGE, LARGE + 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF]
INIT_RANDS = [0, 1, 0x7FFF, 0xFFFFFFFF]


def init_cases(rs):
    for bound in INIT_BOUNDS:
        for r in INIT_RANDS:
            yield init_case(f"init bound {bound:#x} rand {r:#x}", bound, r)
    for k in range(0, 31):
        yield init_case(f"init power {k}", 1 << k, 0x2468ACE + k)
        yield init_case(f"init power {k} minus one", (1 << k) - 1, 0x13579BD + k)
    for r in (0x1FFFFFD, 0x1FFFFFE, 0x1FFFFFF, 0x2000000, 0x2000001, 0x7FFFFFFF, 0x80000000):
        yield init_case(f"init large rand {r:#x}", LARGE, r)
    for i in range(30):
        yield init_case(f"init random {i}", rs.randrange(0, 1 << rs.randrange(1, 33)), rs.getrandbits(31))


# ---- generator step -------------------------------------------------------

def step_case(label, bound, k, state, seed=0x1234567):
    def setup(env):
        mask = mask32(2 << k)
        poly = env.get(POLY_TABLE + 4 * k)
        return {"obj": lfsr_object(env, bound, mask, poly, state, seed)}
    return Case(label, STEP, setup, receiver=lambda t: t["obj"])


def step_cases(rs):
    # exhaustive small generators: every state, bound at the bottom, middle and top of the range
    for k in (1, 2, 3, 4):
        top = (2 << k) - 1
        for bound in sorted({1 << k, (1 << k) + 1, top - 1, top}):
            for state in range(1, top + 1):
                yield step_case(f"step k{k} bound {bound} state {state}", bound, k, state)
    yield step_case("step bound zero state zero", 0, 3, 0)
    yield step_case("step state zero", 12, 3, 0)
    yield step_case("step state at mask", 12, 3, 0xF)
    yield step_case("step state above mask", 12, 3, 0x1F)
    for k in (8, 12, 20, 24):
        mask = 2 << k
        for state in (1, mask - 1, 1 << k, (1 << k) + 1, 0x2A5 % (mask - 1) + 1):
            yield step_case(f"step k{k} state {state:#x}", (1 << k) + 7, k, state)
    for i in range(20):
        k = rs.randrange(1, 25)
        top = (2 << k) - 1
        yield step_case(f"step random {i}", rs.randrange(1 << k, top + 1), k, rs.randrange(1, top + 1), rs.getrandbits(32))


# ---- stream cipher --------------------------------------------------------

def crypt_case(label, function, data, rand_value, seed, count=None):
    def setup(env):
        buf = env.object(max(1, len(data)), "data", data=bytes(data) if data else b"\x00")
        obj = env.object(OBJECT_SIZE, "generator", fill=0)
        env.put(obj, *[0x03030303 * (i % 5 + 1) + 7 * i for i in range(OBJECT_SIZE // 4)])
        env.put(obj + 0x44, seed)
        env.override(RAND, sequence(rand_value))
        return {"obj": obj, "buf": buf}
    n = len(data) if count is None else count
    return Case(label, function, setup, receiver=lambda t: t["obj"], arguments=(lambda t: t["buf"], n))


CRYPT_RANDS = [0, 1, 0x1FFFFFE, 0x1FFFFFF, 0x7FFFFFFF, 0xFFFFFFFF, 0x31337, 0xCAFEBABE]


def crypt_cases(rs):
    for function, name in ((CRYPT, "crypt"), (CRYPT_WRAP, "wrap")):
        yield crypt_case(f"{name} zero length", function, b"\x10\x20\x30", 0x555, 0x99, count=0)
        yield crypt_case(f"{name} zero seed", function, b"\x10\x20\x30", 0x556, 0)
        for r in CRYPT_RANDS:
            yield crypt_case(f"{name} 1 byte rand {r:#x}", function, b"\xA5", r, 0x1111 + r % 97)
            yield crypt_case(f"{name} 16 bytes rand {r:#x}", function, bytes(range(0x30, 0x40)), r, 0xDEADBEEF)
        yield crypt_case(f"{name} zero data", function, bytes(40), 0x2468AC, 7)
        yield crypt_case(f"{name} 0xff data", function, b"\xff" * 40, 0x2468AC, 7)
        yield crypt_case(f"{name} partial length", function, bytes(range(1, 40)), 0x13579, 3, count=11)
        yield crypt_case(f"{name} 300 bytes", function, bytes((i * 7 + 3) & 0xFF for i in range(300)), 0x7A7A7A, 0xABCD)
        for i in range(12):
            n = rs.randrange(1, 100)
            yield crypt_case(f"{name} random {i}", function, bytes(rs.randrange(256) for _ in range(n)),
                             rs.getrandbits(32), rs.getrandbits(32))


def cases(random_source):
    yield from crc_cases(random_source)
    yield from init_cases(random_source)
    yield from step_cases(random_source)
    yield from crypt_cases(random_source)
