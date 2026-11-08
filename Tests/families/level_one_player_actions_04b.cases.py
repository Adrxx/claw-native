"""Cases for level_one_player_actions_04b: Observed Level 1 player actions batch 4b x87 returners.

The three entries return binary64 math in ST(0). Coverage is hand-picked and independent of the seed;
random_source only adds extra generic inputs.
"""
import itertools
import struct

from clawparity.cases import Case

ROOT_A, ROOT_B, SOLVE = 0x420AF0, 0x420B60, 0x420DD0
SIZE = 0x60


def words(x):
    """Low and high 32-bit words of a binary64 value (float, or int raw bits)."""
    raw = struct.pack("<Q", x) if isinstance(x, int) else struct.pack("<d", x)
    return struct.unpack("<II", raw)


NAN = 0x7FF8000000000000
SNAN = 0x7FF0000000000001
NEG_NAN = 0xFFF8123400000000
INF = float("inf")
DENORM = 0x0000000000000003
NEG_ZERO = 0x8000000000000000
BIG = 1.0e300


def fields(values):
    """Offsets 0x10..0x50 hold binary64 values; unspecified slots get distinct non-zero filler."""
    def setup(env):
        obj = env.object(SIZE, "object", fill=0)
        for index, offset in enumerate(range(0x08, 0x58, 8)):
            env.put(obj + offset, *words(1.0 + 0.0625 * (index + 1)))
        for offset, value in values.items():
            env.put(obj + offset, *words(value))
        return {"obj": obj}
    return setup


def call(label, function, values, arguments):
    flat = tuple(w for a in arguments for w in words(a))
    return Case(label, function, fields(values), receiver=lambda t: t["obj"], arguments=flat)


def quadratic_cases(function, factor_off, value_off, arg_off):
    factors = (0.0, NEG_ZERO, 1.5, -1.5, 0.3, NAN, INF, DENORM)
    values = (0.0, NEG_ZERO, 2.5, -2.5, NEG_NAN, -INF, DENORM)
    base = 0.75
    args = (base, base + 1.25, base - 3.75, base + 1e-3)
    for fi, factor in enumerate(factors):
        for vi, value in enumerate(values):
            for ai, arg in enumerate(args):
                if factor in (0.0, NEG_ZERO, NAN, INF, DENORM) and ai not in (0, 1):
                    continue
                yield call(f"{function:#x} f{fi} v{vi} a{ai}", function,
                           {factor_off: factor, value_off: value, arg_off: base}, (arg,))
    for value, factor, arg in ((SNAN, 1.5, 3.0), (3.5, SNAN, 3.0), (3.5, 1.5, SNAN), (BIG, BIG, BIG), (1.0, 2.0, -BIG)):
        yield call(f"{function:#x} special {value} {factor}", function,
                   {factor_off: factor, value_off: value, arg_off: base}, (arg,))
    # Discriminant sign sweep around the equality t*factor*... : many exact small rationals.
    for factor, value, arg in itertools.product((0.5, -2.0), (0.25, -1.0), (0.0, 1.0, 1.75, -1.0)):
        yield call(f"{function:#x} grid {factor} {value} {arg}", function,
                   {factor_off: factor, value_off: value, arg_off: base + 0.5}, (arg + 0.5,))


def solve(label, d, p, origin=(0.5, -1.25, 2.0)):
    values = {0x10: d[0], 0x18: d[1], 0x20: d[2], 0x40: origin[0], 0x48: origin[1], 0x50: origin[2]}
    arguments = tuple(origin[i] + p[i] if isinstance(p[i], float) else p[i] for i in range(3))
    flat = tuple(w for a in arguments for w in words(a))
    return Case(label, SOLVE, fields(values), receiver=lambda t: t["obj"], arguments=flat)


def cases(random_source):
    yield from quadratic_cases(ROOT_A, 0x10, 0x28, 0x40)
    yield from quadratic_cases(ROOT_B, 0x18, 0x30, 0x48)

    quadratic_dirs = ((1.0, 2.0, 3.0), (-1.5, 0.5, -2.0), (0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (2.0, -3.0, 0.0), (0.7, 0.7, 0.7))
    linear_dirs = ((0.3, -0.2, 0.1), (0.0, 0.25, 0.0), (-0.1, -0.2, 0.4), (0.6, 0.0, 0.0), (0.0, 0.0, 0.0), (0.2, 0.2, -0.2))
    points = ((1.0, 0.5, -2.0), (-3.0, 2.0, 1.0), (0.25, 4.0, 0.125), (-1.0, -1.0, -1.0), (7.0, -2.0, 3.0))
    for d in quadratic_dirs + linear_dirs:
        for p in points:
            yield solve(f"direction {d} point {p}", d, p)
    # Zero branch: point on the ray (parallel, forward), at the origin, and very close to it.
    for d in quadratic_dirs + linear_dirs[:4]:
        for t in (0.0, 2.5, 1.0e-9):
            yield solve(f"parallel {d} t={t}", d, tuple(t * c for c in d))
        yield solve(f"anti-parallel {d}", d, tuple(-1.5 * c for c in d))
    # Non-finite and signalling inputs.
    d = (1.0, 2.0, 3.0)
    for bad in (NAN, SNAN, NEG_NAN, INF, -INF, DENORM, BIG, -BIG):
        yield solve(f"bad point x {bad}", d, (bad, 1.0, 2.0))
        yield solve(f"bad point z {bad}", d, (1.0, 2.0, bad))
        yield solve(f"bad direction y {bad}", (1.0, bad if not isinstance(bad, int) else bad, 3.0), (1.0, 2.0, -3.0))
    for bad in (NAN, INF, DENORM, BIG):
        yield solve(f"bad linear direction {bad}", (bad, 0.1, 0.1), (1.0, 2.0, -3.0))
    yield solve("negative zero everywhere", (NEG_ZERO, NEG_ZERO, NEG_ZERO), (NEG_ZERO, NEG_ZERO, NEG_ZERO))
    yield solve("tiny direction", (1.0e-200, 2.0e-200, 3.0e-200), (1.0, 2.0, 3.0))
    # Boundary of the linear/quadratic split: |d|^2 * 0.25 against 0.1.
    for scale in (0.6324, 0.63245553, 0.6325, 0.6326, 0.64):
        yield solve(f"split boundary {scale}", (scale, 0.0, 0.0), (1.0, 2.0, -3.0))
    # Random extras.
    uniform = random_source.uniform
    for index in range(24):
        scale = 3.0 if index % 2 else 0.5
        d = tuple(uniform(-scale, scale) for _ in range(3))
        p = tuple(uniform(-8.0, 8.0) for _ in range(3))
        yield solve(f"random solve {index}", d, p, tuple(uniform(-4.0, 4.0) for _ in range(3)))
    for function, factor_off, value_off, arg_off in ((ROOT_A, 0x10, 0x28, 0x40), (ROOT_B, 0x18, 0x30, 0x48)):
        for index in range(8):
            yield call(f"{function:#x} random {index}", function,
                       {factor_off: uniform(-3, 3), value_off: uniform(-5, 5), arg_off: uniform(-2, 2)}, (uniform(-6, 6),))
