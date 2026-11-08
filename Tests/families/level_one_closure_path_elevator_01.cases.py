"""Cases for level_one_closure_path_elevator_01: Level 1 closure: Path elevator helpers.

Every branch has explicit cases; the random source only varies the contents.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

SUM = 0x468170
CONSUME = 0x4681C0
APPLY = 0x4682C0
FILL = 0x4683A0
COLLECT = 0x468540
APPEND = 0x468840
START = 0x468890
STEP = 0x4688F0
DELETING = 0x49F020
DESTROY = 0x49F040

PATH_SIZE = 0x108
LOW_GLOBALS = (0xF0, 0xF4, 0xF8, 0xFC, 0x100, 0x104, 0x108, 0x10C)


def word(rs, low=1):
    return rs.randrange(low, 0xFFFFFFFF)


def noise(rs, size):
    return bytes(rs.randrange(256) for _ in range(size))


def path_setup(rs, kinds=(), amounts=(), count=None, pad=0):
    """A path object: kinds at +0, amounts at +0x80, count at +0x100, everything else random."""
    n = len(kinds) if count is None else count
    content = bytearray(noise(rs, pad + PATH_SIZE))
    # slots past the used entries hold valid-looking kinds and amounts, so a loop that runs one step too far shows
    for i in range(n if 0 <= n < 32 else 32, 32):
        content[pad + 4 * i:pad + 4 * i + 4] = rs.choice((1, 2, 3, 4, 6, 7, 8, 9)).to_bytes(4, "little")
        content[pad + 0x80 + 4 * i:pad + 0x80 + 4 * i + 4] = rs.randrange(1, 100000).to_bytes(4, "little")
    for i, k in enumerate(kinds):
        content[pad + 4 * i:pad + 4 * i + 4] = (k & 0xFFFFFFFF).to_bytes(4, "little")
    for i, a in enumerate(amounts):
        content[pad + 0x80 + 4 * i:pad + 0x80 + 4 * i + 4] = (a & 0xFFFFFFFF).to_bytes(4, "little")
    content[pad + 0x100:pad + 0x104] = (n & 0xFFFFFFFF).to_bytes(4, "little")

    def setup(env):
        base = env.object(pad + PATH_SIZE, "path", data=bytes(content))
        return {"path": base + pad}

    return setup


def path_of(setup):
    return setup


# ---------------------------------------------------------------- 0x468170

def sum_cases(rs):
    for divisor in (0, 1, 2, 3, 7, 100, 1000, 0x10001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for kinds, amounts in (
            ((), ()),
            ((3,), (17,)),
            ((1, 2), (1234, 98765)),
            ((9, 8, 7, 6, 4), tuple(word(rs) for _ in range(5))),
        ):
            yield Case(f"sum d={divisor:#x} n={len(kinds)}", SUM, path_setup(rs, kinds, amounts),
                       receiver=lambda t: t["path"], arguments=(divisor,))
    full = tuple(word(rs) for _ in range(32))
    for divisor in (1, 3, 100, 0xFFFFFFFF):
        yield Case(f"sum full 32 d={divisor:#x}", SUM, path_setup(rs, (1,) * 32, full),
                   receiver=lambda t: t["path"], arguments=(divisor,))
    for count in (-1, -5, 0x80000000):
        yield Case(f"sum count {count} d=5", SUM, path_setup(rs, (1, 2), (11, 22), count=count, pad=0),
                   receiver=lambda t: t["path"], arguments=(5,))
    yield Case("sum zero amounts", SUM, path_setup(rs, (1, 2, 3), (0, 0, 0)),
               receiver=lambda t: t["path"], arguments=(9,))
    yield Case("sum wrap amounts", SUM, path_setup(rs, (1, 2), (0xFFFFFFFF, 0x10624DD3)),
               receiver=lambda t: t["path"], arguments=(0x12345,))


# ---------------------------------------------------------------- 0x4682c0

def apply_cases(rs):
    for kind in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0xFFFFFFFF, 0x80000000):
        for amount in (0, 7, 0x80000000, word(rs)):
            def setup(env, a=rs.randrange(1, 0xFFFFFFFF), b=rs.randrange(1, 0xFFFFFFFF)):
                pair = env.object(8, "pair", words=[a, b])
                return {"pair": pair}
            yield Case(f"apply kind={kind:#x} amount={amount:#x}", APPLY, setup,
                       arguments=(lambda t: t["pair"], kind & 0xFFFFFFFF, amount))


# ---------------------------------------------------------------- 0x4681c0

def consume_setup(rs, kinds, amounts, count=None):
    inner = path_setup(rs, kinds, amounts, count)

    def setup(env):
        tokens = inner(env)
        tokens["out"] = env.object(8, "out", words=[word(rs), word(rs)])
        return tokens

    return setup


_STACK_RS = []


def consume_case(label, setup, budget, divisor):
    # nonzero garbage in the three local slots below entry ESP, so a local that is not cleared shows
    garbage = bytes(_STACK_RS[0].randrange(1, 256) for _ in range(12))
    return Case(label, CONSUME, setup, receiver=lambda t: t["path"],
                arguments=(lambda t: t["out"], budget, divisor), initial_stack=((-12, garbage),))


def consume_cases(rs):
    layouts = [
        ("1x", (3,), (12345,)),
        ("2x", (1, 9), (4000, 5000)),
        ("3x", (7, 2, 4), (3000, 800, 12000)),
        ("4x", (6, 8, 3, 5), (1500, 2500, 3500, 4500)),
        ("6x", (1, 2, 3, 4, 6, 7), tuple(1000 * (i + 2) for i in range(6))),
        ("3k5", (5, 5, 0), (900, 1100, 1300)),
        ("big", (3, 1), (0xFFFFFFFF, 0x80000001)),
    ]
    for name, kinds, amounts in layouts:
        for divisor in (7, 1000):
            esi = [(a * 1000 & 0xFFFFFFFF) // divisor for a in amounts]
            half = esi[0] + (esi[1] if len(esi) > 1 else 0)
            budgets = {0, max(0, esi[0] - 1), esi[0], esi[0] + 1, half, sum(esi), sum(esi) + 1, 0xFFFFFFFF}
            for budget in sorted(budgets):
                if budget > 0xFFFFFFFF:
                    continue
                yield consume_case(f"consume {name} d={divisor} b={budget:#x}",
                                   consume_setup(rs, kinds, amounts), budget, divisor)
    # divisor zero, empty path, negative / zero count
    yield consume_case("consume divisor 0", consume_setup(rs, (1, 2), (10, 20)), 500, 0)
    yield consume_case("consume divisor 0 budget 0", consume_setup(rs, (1, 2), (10, 20)), 0, 0)
    yield consume_case("consume empty path", consume_setup(rs, (), ()), 500, 7)
    yield consume_case("consume negative count", consume_setup(rs, (1,), (10,), count=-3), 500, 7)
    # each kind through the partial branch and the exact branch
    for kind in range(0, 12):
        yield consume_case(f"consume partial kind {kind}", consume_setup(rs, (kind, 1), (5000, 5000)), 1234, 100)
        yield consume_case(f"consume whole kind {kind}", consume_setup(rs, (kind, 3), (1000, 2000)), 50000, 100)
    # random layouts; budget derived from the contents so branches stay chosen
    for i in range(8):
        n = 1 + i % 5
        kinds = tuple(rs.randrange(1, 10) for _ in range(n))
        amounts = tuple(rs.randrange(1, 100000) for _ in range(n))
        divisor = rs.randrange(1, 5000)
        esi = [a * 1000 // divisor for a in amounts]
        yield consume_case(f"consume random {i} partial", consume_setup(rs, kinds, amounts), esi[0] + 1 + sum(esi[1:2]) // 2 if n > 1 else esi[0] // 2 + 1, divisor)
        yield consume_case(f"consume random {i} whole", consume_setup(rs, kinds, amounts), sum(esi) + rs.randrange(1, 50), divisor)


# ---------------------------------------------------------------- 0x4683a0

def fill_cases(rs):
    for selector in (1, 2):
        for count in list(range(0, 35)) + [0x40, 0x7FFFFFFF]:
            yield Case(f"fill {selector} count {count}", FILL, path_setup(rs, (), (), count=count),
                       receiver=lambda t: t["path"], arguments=(selector,))
        for count in (-1, -2):
            yield Case(f"fill {selector} negative count {count}", FILL, path_setup(rs, (), (), count=count, pad=16),
                       receiver=lambda t: t["path"], arguments=(selector,))
    for selector in (0, 3, 4, 0xFFFFFFFF, 0x80000001, 0x100000001 & 0xFFFFFFFF):
        yield Case(f"fill selector {selector:#x} does nothing", FILL, path_setup(rs, (1,), (5,)),
                   receiver=lambda t: t["path"], arguments=(selector,))


# ---------------------------------------------------------------- 0x468540

OFFSETS = [(0x118, 0x11C), (0x120, 0x124), (0x128, 0x12C), (0x130, 0x134), (0x138, 0x13C),
           (0x140, 0x144), (0x54, 0x58), (0x5C, 0x60)]


def collect_setup(rs, count=0, skip=None, zero_second=None, third=0x13572468, values=None, globals_zero=None,
                  first_value=None, source_size=0x148):
    """Path being appended to, plus a source record with eight pairs of distinct values."""
    inner = path_setup(rs, (), (), count=count)

    def setup(env):
        tokens = inner(env)
        words = [word(rs) for _ in range(source_size // 4)]
        for index, (key, amount) in enumerate(OFFSETS):
            if first_value is not None and index == 0:
                words[key // 4] = first_value
            if skip == index:
                words[key // 4] = 0
            if zero_second == index:
                words[amount // 4] = 0
        words[0x6C // 4] = third  # zero would reach 0x468780, which reads unmapped address 0xf4 and faults
        tokens["source"] = env.object(source_size, "source", words=words)
        return tokens

    return setup


def collect_case(label, setup, source=lambda t: t["source"]):
    return Case(label, COLLECT, setup, receiver=lambda t: t["path"], arguments=(source,))


def collect_cases(rs):
    yield Case("collect null source", COLLECT, path_setup(rs, (1,), (2,)), receiver=lambda t: t["path"], arguments=(0,))
    yield collect_case("collect key 0x80000000", collect_setup(rs, first_value=0x80000000))
    yield collect_case("collect key zero", collect_setup(rs, skip=0))
    yield collect_case("collect key 0xffffffff", collect_setup(rs, first_value=0xFFFFFFFF))
    yield collect_case("collect pair 0 amount zero", collect_setup(rs, zero_second=0))
    for count in (32, 33, 0x7FFFFFFF):
        yield collect_case(f"collect pair 0 full {count}", collect_setup(rs, count=count))
    for stage in range(1, 8):
        yield collect_case(f"collect stage {stage} full", collect_setup(rs, count=32 - stage))
        yield collect_case(f"collect stage {stage} key zero", collect_setup(rs, skip=stage))
        yield collect_case(f"collect stage {stage} amount zero", collect_setup(rs, zero_second=stage))
    for count in (0, 1, 5, 18, 22):
        yield collect_case(f"collect plain start {count} then nonzero +6c", collect_setup(rs, count=count, third=word(rs)))
    yield collect_case("collect +6c one", collect_setup(rs, third=1))
    yield collect_case("collect +6c sign bit", collect_setup(rs, third=0x80000000))


# ---------------------------------------------------------------- 0x468840

def append_cases(rs):
    for count in (0, 1, 30, 31, 32, 33, 0x7FFFFFFF):
        for first, second in ((word(rs), word(rs)), (0, word(rs)), (word(rs), 0), (0, 0)):
            yield Case(f"append count {count} {first and 'k'}{second and 'a'}", APPEND, path_setup(rs, (), (), count=count),
                       receiver=lambda t: t["path"], arguments=(first, second))
    yield Case("append negative count", APPEND, path_setup(rs, (), (), count=-1, pad=16),
               receiver=lambda t: t["path"], arguments=(0x11111111, 0x22222222))
    yield Case("append sign bit values", APPEND, path_setup(rs, (), (), count=4),
               receiver=lambda t: t["path"], arguments=(0x80000000, 0xFFFFFFFF))


# ---------------------------------------------------------------- 0x468890

def start_setup(rs, kinds, amounts):
    inner = path_setup(rs, kinds, amounts)

    def setup(env):
        tokens = inner(env)
        tokens["tracker"] = env.object(0x20, "tracker", data=noise(rs, 0x20))
        tokens["actor"] = env.object(0x40, "actor", data=noise(rs, 0x40))
        return tokens

    return setup


def start_cases(rs):
    layouts = [((), ()), ((3,), (17,)), ((1, 2, 3), (1234, 98765, 4000)), ((9, 8), (0xFFFFFFFF, 12))]
    for kinds, amounts in layouts:
        for divisor in (0, 1, 100, 7, 0xFFFFFFFF):
            for extra in (0, 0x12345678):
                yield Case(f"start n={len(kinds)} d={divisor:#x} e={extra:#x}", START, start_setup(rs, kinds, amounts),
                           receiver=lambda t: t["tracker"],
                           arguments=(lambda t: t["actor"], lambda t: t["path"], divisor, extra))
    yield Case("start null actor", START, start_setup(rs, (1,), (5,)), receiver=lambda t: t["tracker"],
               arguments=(0, lambda t: t["path"], 50, 9))
    yield Case("start null path", START, start_setup(rs, (1,), (5,)), receiver=lambda t: t["tracker"],
               arguments=(lambda t: t["actor"], 0, 50, 9))
    yield Case("start both null", START, start_setup(rs, (1,), (5,)), receiver=lambda t: t["tracker"],
               arguments=(0, 0, 50, 9))


# ---------------------------------------------------------------- 0x4688f0

def step_setup(rs, kinds, amounts, period, divisor, offset, actor_words):
    inner = path_setup(rs, kinds, amounts)

    def setup(env):
        tokens = inner(env)
        actor = bytearray(noise(rs, 0x168))
        for position, value in actor_words.items():
            actor[position:position + 4] = (value & 0xFFFFFFFF).to_bytes(4, "little")
        tokens["actor"] = env.object(0x168, "actor", data=bytes(actor))
        words = [0, tokens["actor"], tokens["path"], divisor, period, offset]
        tokens["tracker"] = env.object(0x20, "tracker", words=[0x5A5A5A5A, tokens["actor"], tokens["path"], divisor,
                                                              period, offset, 0x1234, 0x4321])
        return tokens

    return setup


def step_cases(rs):
    kinds, amounts = (3, 1, 9, 6), (2000, 3000, 1500, 4000)
    deltas = [(0, 0), (30, 40), (-30, 50), (99, -99), (100, 0), (-100, 0), (0, 100), (0, -100), (99, 100),
              (-99, 99), (150, 5), (0x7FFFFFFF, 0), (0x80000000, 0), (0, 0x80000000), (1, 0xFFFFFFFF)]
    for period in (1, 7, 360, 0xFFFFFFFF):
        for offset in (0, 13, 0xFFFFFFFF):
            for argument in (0, 99, 0xFFFFFFFF):
                actor_words = {0x4C: 11111, 0x50: 22222, 0xE8: 11000, 0xEC: 22000, 0x158: word(rs), 0x15C: word(rs)}
                yield Case(f"step period {period:#x} offset {offset:#x} x {argument:#x}", STEP,
                           step_setup(rs, kinds, amounts, period, 100, offset, actor_words),
                           receiver=lambda t: t["tracker"], arguments=(argument,))
    # movement boundaries on the clamped velocity
    layouts = [
        ((3,), (10000,), 1, 100, 0),      # 3: x and y +; velocity depends on budget
        ((2,), (10000,), 0, 100, 0),
        ((1,), (10000,), 0, 100, 0),
        ((9,), (10000,), 0, 100, 0),
        ((4, 8), (5000, 5000), 0, 100, 0),
    ]
    for kinds_, amounts_, _, divisor, offset in layouts:
        for argument in (1, 99, 101, 5000):
            for base_x, base_y in ((500, 700), (0xFFFFFF00, 0x100)):
                actor_words = {0x4C: 100, 0x50: 200, 0xE8: base_x, 0xEC: base_y, 0x158: word(rs), 0x15C: word(rs)}
                yield Case(f"step velocity kinds {kinds_} x {argument} base {base_x:#x}", STEP,
                           step_setup(rs, kinds_, amounts_, 100000, divisor, offset, actor_words),
                           receiver=lambda t: t["tracker"], arguments=(argument,))
    # velocity just under and over the 100 limit on each axis, built from kind 3 and 7 and one amount
    for old_x, old_y in ((0, 0), (1, 1)):
        for target_x, target_y in ((99, 0), (100, 0), (-99, 0), (-100, 0), (0, 99), (0, 100), (0, -99), (0, -100), (99, 99), (-99, -99), (100, 100), (150, 20), (20, 150)):
            actor_words = {0x4C: old_x, 0x50: old_y, 0xE8: target_x, 0xEC: target_y, 0x158: word(rs), 0x15C: word(rs)}
            yield Case(f"step velocity {target_x} {target_y} from {old_x} {old_y}", STEP,
                       step_setup(rs, (), (), 100, 100, 0, actor_words),
                       receiver=lambda t: t["tracker"], arguments=(0,))
    # no period: nothing happens
    for period in (0,):
        yield Case("step no period", STEP, step_setup(rs, kinds, amounts, 0, 100, 0, {0x4C: 1, 0x50: 2}),
                   receiver=lambda t: t["tracker"], arguments=(0,))
    # random
    for _ in range(10):
        n = rs.randrange(1, 6)
        yield Case("step random", STEP,
                   step_setup(rs, tuple(rs.randrange(1, 10) for _ in range(n)), tuple(rs.randrange(1, 50000) for _ in range(n)),
                              rs.randrange(1, 5000), rs.randrange(1, 300), rs.randrange(0, 1000),
                              {0x4C: word(rs), 0x50: word(rs), 0xE8: word(rs), 0xEC: word(rs)}),
                   receiver=lambda t: t["tracker"], arguments=(rs.randrange(0, 100000),))


# ---------------------------------------------------------------- 0x49f040 / 0x49f020

def holder_setup(rs, member):
    def setup(env):
        tokens = {}
        tokens["member"] = env.object(16, "member", data=noise(rs, 16)) if member else 0
        words = [word(rs), word(rs), tokens["member"], word(rs), word(rs), word(rs)]
        tokens["this"] = env.object(0x20, "holder", words=words + [word(rs), word(rs)])
        return tokens

    return setup


def destroy_cases(rs):
    for member in (False, True, False, True):
        yield Case(f"destroy member {member}", DESTROY, holder_setup(rs, member), receiver=lambda t: t["this"])
    for flags in (0, 1, 2, 3, 0x10, 0x11, 0xFFFFFFFE, 0xFFFFFFFF, 0x80000001):
        for member in (False, True):
            yield Case(f"deleting flags {flags:#x} member {member}", DELETING, holder_setup(rs, member),
                       receiver=lambda t: t["this"], arguments=(flags,))


def cases(random_source):
    rs = random_source
    _STACK_RS[:] = [rs]
    for generator in (sum_cases, apply_cases, consume_cases, fill_cases, collect_cases, append_cases,
                      start_cases, step_cases, destroy_cases):
        for case in generator(rs):
            if case is not None:
                yield case
