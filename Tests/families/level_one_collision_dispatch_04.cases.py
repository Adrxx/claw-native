"""Cases for level_one_collision_dispatch_04: Level 1 registry search, velocity flip and attack-state shim.

Every branch is covered by hand-built cases, independent of the random seed; random cases only add on top.
"""
from clawparity.cases import Case
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP
from clawparity.env import NativeSourceContext

FLIP = 0x406120
SEARCH = 0x4DC3D0
SHIM = 0x4DC850
RETURN_ENTRY = 0x4DB5F0
TABLE = 0x544B98
COUNT = 0x544D18
STRIDE = 12
MAX_ENTRIES = 32
MASK = 0xFFFFFFFF
MIN_INT = 0x80000000


def signed(value):
    value &= MASK
    return value - (1 << 32) if value & MIN_INT else value


# ---------------------------------------------------------------- 0x406120

def flip_object(x, y, size=0x140):
    def setup(env):
        obj = env.object(size, "actor", fill=0)
        for offset in range(0, size, 4):
            env.put(obj + offset, 0x5A000000 + offset)
        env.put(obj + 0x118, x & MASK)
        env.put(obj + 0x120, y & MASK)
        return {"obj": obj}
    return setup


def flip_case(label, x, y):
    return Case(label, FLIP, flip_object(x, y), receiver=lambda t: t["obj"])


# ---------------------------------------------------------------- 0x4dc3d0

def registry(keys, receiver_plus4=0x7777AAAA):
    """Global table of 12-byte entries (key, two distinct payload words) and its count."""
    def setup(env):
        obj = env.object(16, "searcher", fill=0)
        env.put(obj, 0x11112222)
        env.put(obj + 4, receiver_plus4)
        env.put(obj + 8, 0x33334444)
        env.put(obj + 12, 0x55556666)
        for index, key in enumerate(keys):
            base = TABLE + index * STRIDE
            env.put(base, key & MASK, 0xA0000000 + index, 0xB0000000 + index * 3)
        env.put(COUNT, len(keys) & MASK)
        return {"obj": obj}
    return setup


def registry_count(count, keys):
    """Count that is not len(keys): empty, negative or larger than the populated prefix."""
    base_setup = registry(keys)

    def setup(env):
        tokens = base_setup(env)
        env.put(COUNT, count & MASK)
        return tokens
    return setup


def search(label, keys, key, setup=None):
    return Case(label, SEARCH, setup or registry(keys), receiver=lambda t: t["obj"], arguments=(key & MASK,))


def sorted_keys(count, start, step):
    return [start + step * index for index in range(count)]


def key_queries(keys, step=3):
    """Every hit, every gap, below the first, above the last."""
    queries = [(f"hit[{i}]", key) for i, key in enumerate(keys)]
    queries.append(("below", keys[0] - 1))
    queries.append(("above", keys[-1] + 1))
    queries.extend((f"gap{i}", keys[i] + 1) for i in range(len(keys) - 1) if keys[i + 1] - keys[i] > 1)
    return queries


# ---------------------------------------------------------------- 0x4dc850

def shim_object(vtable_slot_value=None, receiver_value=None, result=0, extra_slots=True):
    def setup(env):
        record = env.object(16, "record", fill=0)
        env.put(record, 0xDEAD0001, 0xDEAD0002)

        def method(env, call):
            env.put(record, call.receiver, env.calls_so_far(call.function), 0xC0DE0000 + len(call.arguments))
            return result

        target = env.stub("attack state method", "thiscall", 0, method)
        other = env.stub("other method", "thiscall", 0, lambda env, call: env.put(record + 12, 0xBAD0BAD0) or 0)
        vtable = env.object(0x40, "vtable", fill=0)
        for slot in range(0, 0x40, 4):
            env.put(vtable + slot, other if extra_slots else 0)
        env.put(vtable + 0x18, target)
        receiver = env.object(0x20, "state receiver", fill=0)
        env.put(receiver, vtable)
        for offset in range(4, 0x20, 4):
            env.put(receiver + offset, 0x6C000000 + offset)
        middle = env.object(0x30, "middle", fill=0)
        for offset in range(0, 0x30, 4):
            env.put(middle + offset, 0x4D000000 + offset)
        env.put(middle + 0x18, receiver)
        subject = env.object(0x80, "subject", fill=0)
        for offset in range(0, 0x80, 4):
            env.put(subject + offset, 0x53000000 + offset)
        env.put(subject + 0x6C, middle)
        return {"subject": subject, "record": record, "receiver": receiver}
    return setup


def shim_case(label, **options):
    return Case(label, SHIM, shim_object(**options), arguments=(lambda t: t["subject"],))


# ---------------------------------------------------------------- 0x4db5f0

# Real instruction-after-CALL addresses of 0x4db5f0 in the original, spread across the program.
RETURN_PCS = (
    0x403600, 0x406D1D, 0x40876B, 0x40E46B, 0x40FDB4, 0x4115BA, 0x412124, 0x4136C0,
    0x414582, 0x421619, 0x43276A, 0x4384C2, 0x43F5C5, 0x445E06, 0x448FEB, 0x454440,
    0x4563BA, 0x45843B, 0x462B50, 0x465E8A, 0x4740FB, 0x47E940, 0x484930, 0x488B9B,
)
FRAME_OFFSETS = (0, 0x40, 0x2000, 0x6000)
EAX_VALUES = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xDEADBEEF)


def return_setup(random_source, eax, ebp, frame_offset):
    pattern = bytes(random_source.randrange(256) for _ in range(1024))
    stack = pattern * (STACK_SIZE // len(pattern))
    frame = STACK_TOP - frame_offset
    fs = random_source.choice((0xFFFFFFFF, STACK_BASE + 0x100, STACK_BASE + 0x200))
    flags = 2 | random_source.choice((0, 1, 4, 0x40, 0x80, 0x800))

    def setup(env):
        env.write(STACK_BASE, stack)
        source = NativeSourceContext()
        source.size, source.version = 72, 1
        source.inputMask = source.outputMask = 0x5C1
        source.preserveMask = 0
        source.eax, source.ebp = eax, ebp
        source.esp, source.eip = frame, RETURN_ENTRY
        source.eflags, source.fsHead = flags, fs
        return {"source": source}
    return setup


def return_case(label, random_source, return_pc, eax, ebp, frame_offset):
    return Case(label, RETURN_ENTRY, return_setup(random_source, eax, ebp, frame_offset),
                source_context=lambda tokens: tokens["source"], source_return_pc=return_pc)



# ---------------------------------------------------------------- cases

def cases(random_source):
    # --- velocity flip: sentinel skips, otherwise exchange and negate (distinct values expose wrong offsets / signs)
    for x, y in ((1, 2), (5, -7), (-3, 9), (0, 0), (0, 4), (6, 0), (-1, -1), (0x7FFFFFFF, 3),
                 (3, MIN_INT), (MIN_INT + 1, 2), (0x12345678, 0x0ABCDEF1), (MASK, 1)):
        yield flip_case(f"flip {signed(x)} {signed(y)}", x, y)
    for y in (0, 1, -1, 99, 0x7FFFFFFF, MIN_INT):
        yield flip_case(f"flip sentinel x, y={signed(y)}", MIN_INT, y)
    for _ in range(25):
        yield flip_case("flip random", random_source.getrandbits(32), random_source.getrandbits(32))
    for _ in range(5):
        yield flip_case("flip random sentinel", MIN_INT, random_source.getrandbits(32))

    # --- registry search, hand-built over table sizes (hit, miss, first, last, middle, below, above)
    yield search("empty table, key 0", [], 0)
    yield search("empty table, key 5", [], 5)
    yield search("empty table, negative key", [], -5)
    for count in (-1, -2, -100, MIN_INT + 1):
        yield search(f"negative count {signed(count)}", [10, 20, 30], 20, registry_count(count, [10, 20, 30]))
    yield search("count zero with populated table", [10, 20, 30], 20, registry_count(0, [10, 20, 30]))
    for count in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
        keys = sorted_keys(count, 100, 3)
        for name, key in key_queries(keys):
            yield search(f"n={count} {name}", keys, key)
    for count in (15, 16, 17, 31, 32):
        keys = sorted_keys(count, 7000, 5)
        picks = {0, count - 1, count // 2, count // 2 - 1, count // 2 + 1, count // 4, (3 * count) // 4}
        for index in sorted(picks):
            yield search(f"n={count} hit[{index}]", keys, keys[index])
        for name, key in (("below", keys[0] - 1), ("above", keys[-1] + 1), ("gap-mid", keys[count // 2] + 1),
                          ("gap-first", keys[0] + 1), ("gap-last", keys[-2] + 1)):
            yield search(f"n={count} {name}", keys, key)
    # negative and sign-boundary keys; subtraction wraps, so the original's SF test sees overflow
    negative = [-1000, -50, -7, -1, 0, 1, 40, 900]
    for name, key in key_queries(negative):
        yield search(f"negative keys {name}", negative, key)
    wide = [MIN_INT, MIN_INT + 1, -2, 0, 2, 0x7FFFFFFE, 0x7FFFFFFF]
    for index, key in enumerate(wide):
        yield search(f"extreme keys hit[{index}]", wide, key)
    for key in (MIN_INT, 0x7FFFFFFF, MIN_INT + 1, 0x40000000, 0xC0000000, MASK, 1):
        yield search(f"extreme keys query {key:#x}", wide, key)
        yield search(f"two extreme keys query {key:#x}", [MIN_INT, 0x7FFFFFFF], key)
        yield search(f"one extreme key query {key:#x}", [0x7FFFFFFF], key)
        yield search(f"one min key query {key:#x}", [MIN_INT], key)
    # duplicates and unsorted tables (search is still deterministic)
    dup = [4, 4, 4, 4, 4, 4, 4]
    for key in (3, 4, 5):
        yield search(f"duplicate keys query {key}", dup, key)
    for keys in ([9, 2, 7, 4, 1, 8, 3], [50, 40, 30, 20, 10], [5, 1], [1, 9, 1, 9, 1, 9]):
        for key in (1, 2, 4, 5, 7, 9, 10, 100):
            yield search(f"unsorted {keys} query {key}", keys, key)
    # a count that exceeds the populated prefix still reads the table slots in place (all 32 slots populated)
    full = sorted_keys(MAX_ENTRIES, 200, 4)
    yield search("count smaller than populated table", full, full[20], registry_count(21, full))
    yield search("count smaller, key beyond count", full, full[25], registry_count(21, full))
    # receiver +4 starts with different garbage (the store always overwrites it)
    for garbage in (0, MASK, 0x13572468):
        yield search(f"receiver garbage {garbage:#x}", [3, 6, 9, 12], 9, registry([3, 6, 9, 12], garbage))
        yield search(f"receiver garbage {garbage:#x} miss", [3, 6, 9, 12], 10, registry([3, 6, 9, 12], garbage))
    # random tables and keys
    for _ in range(80):
        count = random_source.randrange(0, MAX_ENTRIES + 1)
        keys = sorted(random_source.sample(range(-5000, 5000), count))
        key = random_source.choice(keys) if keys and random_source.random() < 0.5 else random_source.randrange(-5200, 5200)
        yield search(f"random n={count} key={key}", keys, key)
    for _ in range(40):
        count = random_source.randrange(1, MAX_ENTRIES + 1)
        keys = sorted(random_source.getrandbits(32) for _ in range(count))
        keys = sorted(set(keys))
        key = random_source.choice(keys) if random_source.random() < 0.5 else random_source.getrandbits(32)
        yield search(f"random wide n={len(keys)} key={key:#x}", keys, key)
    for _ in range(20):
        count = random_source.randrange(1, MAX_ENTRIES + 1)
        keys = [random_source.getrandbits(32) for _ in range(count)]
        yield search(f"random unsorted n={count}", keys, random_source.choice((keys[0], random_source.getrandbits(32))))

    # --- attack-state shim: virtual call, receiver recorded, return always 1
    yield shim_case("shim virtual call result 0", result=0)
    yield shim_case("shim virtual call result 1", result=1)
    yield shim_case("shim virtual call result 0xffffffff", result=MASK)
    yield shim_case("shim virtual call result nonzero", result=0x12345678)
    yield shim_case("shim empty other vtable slots", result=7, extra_slots=False)
    for _ in range(4):
        yield shim_case("shim random result", result=random_source.getrandbits(32))

    # --- diagnostic return PC (pop eax; push eax; ret): every real call site, varying register and stack state
    for index, pc in enumerate(RETURN_PCS):
        yield return_case(f"return site {pc:#x}", random_source, pc,
                          random_source.getrandbits(32), random_source.getrandbits(32) or 1,
                          FRAME_OFFSETS[index % len(FRAME_OFFSETS)])
    for index, eax in enumerate(EAX_VALUES):
        for pc in (RETURN_PCS[index], RETURN_PCS[index + 8], RETURN_PCS[index + 16]):
            yield return_case(f"return eax {eax:#x} site {pc:#x}", random_source, pc, eax, 0x12345678 + index, 0x100 * index)
    for index, ebp in enumerate((0, 1, 0xFFFFFFFF, 0x80000000)):
        yield return_case(f"return ebp {ebp:#x}", random_source, RETURN_PCS[index * 5], 0xA5A5A5A5, ebp,
                          FRAME_OFFSETS[index])
