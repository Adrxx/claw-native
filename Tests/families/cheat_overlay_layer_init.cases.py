"""Cases for the debug overlay layer initializer 0x4d0800."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate

INIT = 0x4D0800
OPERATOR_NEW = 0x4F63EC
COPY_RECT = 0x546D58
SENTINEL = 0x80000000
OBJECT_SIZE = 0x140
NAME_OFFSET = 0xB4

TILES = [(1, 1), (2, 4), (3, 5), (8, 8), (16, 32), (0, 0), (-4, -8), (64, 1), (1000, 7), (1 << 20, 3), (255, 256)]
SIZES = [(0, 0), (1, 1), (3, 2), (5, 4), (8, 1), (2, 9), (13, 7), (0, 3), (6, 0)]
RECTS = [
    (0, 0, 9, 9), (10, 20, 50, 41), (-5, -7, 4, 2), (3, 3, 3, 3), (0, 0, 0, 0), (5, 5, 4, 4),
    (-20, -20, -1, -1), (100, 200, 1123, 711), (7, 1, 14, 6), (-3, 4, 8, -9), (1, 2, 2, 3),
]
FLAG_SETS = (0, 4, 8, 12)


def clean(value):
    return value & 0xFFFFFFFF


def make(random_source, w, h, tw, th, p6, p7, rect, name, flags=0, new_effect=None, copy_note=True):
    """setup() for one initializer call. Object, rectangle, and name are filled with distinct non-zero bytes."""
    seed = random_source.randrange(1 << 30)

    def setup(env):
        rng = type(random_source)(seed)
        data = bytes(rng.randrange(1, 256) for _ in range(OBJECT_SIZE))
        layer = env.object(OBJECT_SIZE, "layer", data=data)
        env.put(layer + 8, flags)
        # Scroll offsets the first rectangle recomputation reads before the function zeroes them: keep them finite.
        env.put(layer + 0x10, *struct.unpack("<2I", struct.pack("<2f", rng.uniform(-300, 300), rng.uniform(-300, 300))))
        log = env.object(128, "log", fill=0)
        rect_address = env.object(16, "rect", data=bytes(rng.randrange(1, 256) for _ in range(16)))
        env.put(rect_address, *[clean(v) for v in rect])
        name_address = 0
        if name is not None:
            payload = name + b"\0"
            name_address = env.object(len(payload), "name", data=payload)

        def copy_rect(env, call):
            index = env.calls_so_far(COPY_RECT)
            dest, source = call.arguments[0], call.arguments[1]
            words = [env.get(source + 4 * i) for i in range(4)]
            env.put(dest, *words)
            env.put(log + 0x40 + 12 * (index % 4), dest, source, index)
            return 1

        def default_new(env, call):
            index = env.calls_so_far(OPERATOR_NEW)
            block = env.object(max(1, call.arguments[0]), "allocation")
            env.put(log + 4 * (index % 8), call.arguments[0])
            env.put(log + 0x20 + 4 * (index % 8), block)
            return block

        env.override(COPY_RECT, copy_rect)
        env.override(OPERATOR_NEW, new_effect(layer, log) if new_effect else default_new)
        return {"layer": layer, "rect": rect_address, "name": name_address, "log": log}

    return setup


def init(label, setup, w, h, tw, th, p6, p7, **options):
    def args(tokens):
        return (w, h, tw, th, p6, p7, tokens["rect"], tokens["name"])

    return Case(label, INIT, setup, receiver=lambda t: t["layer"],
                arguments=tuple((lambda t, i=i: args(t)[i]) for i in range(8)), **options)


def signed32(value):
    value &= 0xFFFFFFFF
    return value - (1 << 32) if value & 0x80000000 else value


def build(random_source, label, w, h, tw, th, p6, p7, rect, name, flags=0, new_effect=None):
    # The original's wrap loops never end for a nonpositive wrap span, so wrap flags need a positive span.
    if signed32(tw * w) <= 0:
        flags &= ~4
    if signed32(th * h) <= 0:
        flags &= ~8
    setup = make(random_source, w, h, tw, th, p6, p7, rect, name, flags, new_effect)
    return init(label, setup, clean(w), clean(h), clean(tw), clean(th), clean(p6), clean(p7))


def cases(random_source):
    r = random_source
    # Geometry grid with an ordinary rectangle: tile sizes and layer sizes.
    for tw, th in TILES:
        for w, h in SIZES:
            yield build(r, f"grid tile {tw}x{th} layer {w}x{h}", w, h, tw, th,
                        r.randrange(-500, 500), r.randrange(-500, 500), RECTS[(w + h + th) % len(RECTS)], b"MPLITH")
    # Rectangle variants crossed with the wrap flags, both paths of the sentinel.
    for flags in FLAG_SETS:
        for index, rect in enumerate(RECTS):
            w, h = SIZES[(index + flags) % len(SIZES)]
            tw, th = TILES[(index * 3 + flags) % len(TILES)]
            yield build(r, f"rect {rect} flags {flags}", w, h, tw, th, 1 + index, -index, rect, b"MPLOGO", flags)
        for left_pad in range(3):
            yield build(r, f"sentinel left flags {flags} #{left_pad}", 4 + left_pad, 3, 8, 16, 7, 9,
                        (SENTINEL, r.randrange(-50, 50), r.randrange(-50, 50), r.randrange(-50, 50)),
                        b"NOLITH", flags)
    # Name copy: every length around the dword boundaries, and no name at all.
    for length in range(0, 41):
        name = bytes(r.randrange(65, 91) for _ in range(length))
        yield build(r, f"name length {length}", 3, 2, 4, 4, 11, 13, RECTS[length % len(RECTS)], name)
    yield build(r, "no name", 3, 2, 4, 4, 11, 13, RECTS[1], None)
    yield build(r, "no name sentinel", 3, 2, 4, 4, 11, 13, (SENTINEL, 1, 2, 3), None)
    # Scale factors from the two integer arguments.
    for p6, p7 in ((0, 0), (1, 1), (-1, -1), (100, -100), (123456, 7), (-9999999, 31337), (0x7FFFFFFF, -0x80000000)):
        yield build(r, f"scale {p6} {p7}", 2, 2, 4, 4, p6, p7, RECTS[2], b"MPMONOLITH")
    # Callee results the function reads back afterwards.
    def first_allocation_fails(layer, log):
        def effect(env, call):
            index = env.calls_so_far(OPERATOR_NEW)
            env.put(log + 4 * (index % 8), call.arguments[0])
            if index == 1:
                return 0
            return env.object(max(1, call.arguments[0]), "allocation")
        return effect

    def second_allocation_fails(layer, log):
        def effect(env, call):
            index = env.calls_so_far(OPERATOR_NEW)
            env.put(log + 4 * (index % 8), call.arguments[0])
            if index == 2:
                return 0
            return env.object(max(1, call.arguments[0]), "allocation")
        return effect

    def shrink_after_first(layer, log):
        def effect(env, call):
            index = env.calls_so_far(OPERATOR_NEW)
            env.put(log + 4 * (index % 8), call.arguments[0])
            if index == 1:
                env.put(layer + 0x2C, 2)
                env.put(layer + 0x28, 9)
            return env.object(max(1, call.arguments[0]), "allocation")
        return effect

    def grow_after_first(layer, log):
        def effect(env, call):
            index = env.calls_so_far(OPERATOR_NEW)
            env.put(log + 4 * (index % 8), call.arguments[0])
            if index == 1:
                env.put(layer + 0x2C, 6)
            return env.object(max(1, call.arguments[0]), "allocation")
        return effect

    for name, effect in (("first allocation fails", first_allocation_fails),
                         ("height shrinks after first allocation", shrink_after_first),
                         ("height grows after first allocation", grow_after_first)):
        for rect in (RECTS[1], (SENTINEL, 0, 0, 0)):
            yield build(r, f"{name} rect {rect[0]}", 5, 4, 8, 8, 3, 4, rect, b"MPLITH", 12, new_effect=effect)
    # A null row table is only legal when no row is filled (the fill loop would fault on it).
    for rect in (RECTS[1], (SENTINEL, 0, 0, 0)):
        yield build(r, f"second allocation fails, no rows, rect {rect[0]}", 5, 0, 8, 8, 3, 4, rect, b"MPLITH", 12,
                    new_effect=second_allocation_fails)
    yield build(r, "zero-size layer allocates zero", 0, 0, 8, 8, 3, 4, RECTS[1], b"MPLITH")
    # Random inputs.
    for n in range(90):
        w, h = r.randrange(0, 40), r.randrange(0, 30)
        tw, th = r.choice([r.randrange(-5, 300), 1 << r.randrange(0, 12), r.randrange(0, 70000)]), r.randrange(-5, 300)
        left = r.randrange(-300, 300)
        top = r.randrange(-300, 300)
        rect = (left, top, left + r.randrange(-10, 400), top + r.randrange(-10, 400))
        if r.randrange(6) == 0:
            rect = (SENTINEL,) + rect[1:]
        name = bytes(r.randrange(1, 256) for _ in range(r.randrange(0, 45))) if r.randrange(8) else None
        yield build(r, f"random {n}", w, h, tw, th, r.randrange(-2 ** 31, 2 ** 31), r.randrange(-2 ** 31, 2 ** 31),
                    rect, name, r.choice(FLAG_SETS))
