"""Cases for light_blend_table: Palette blend table builder 0x4c6d90.

The receiver is an object whose growable pointer array starts at +4 (data +8, size +0xc, capacity +0x10,
grow step +0x14). The function appends a new 65536-byte table object to that array and fills the table with
nearest-palette indices. A success case costs about 1.5 s per side, so only a few run to completion; the
rest stop at an allocation failure before the table is filled.
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate

BLEND = 0x4C6D90
OPERATOR_NEW = 0x4F63EC
PALETTE_ADDRESS = 0x540000


def word(value):
    return value & 0xFFFFFFFF


def random_palette(random_source):
    """256 four-byte entries with random bytes; the fourth byte of an entry is never read."""
    return [random_source.getrandbits(32) for _ in range(256)]


def gradient_palette():
    return [(i) | ((255 - i) << 8) | (((i * 7) & 0xFF) << 16) | ((0xA0 + i) & 0xFF) << 24 for i in range(256)]


def duplicate_palette(random_source):
    """Few distinct colors repeated, so ties between equally near entries decide the result."""
    colors = [random_source.getrandbits(24) | (0x5A << 24) for _ in range(5)]
    return [colors[(i * 3 + i // 7) % 5] for i in range(256)]


def narrow_palette(random_source):
    """Colors close together, so many blended colors fall between entries."""
    base = [random_source.randrange(90, 160) for _ in range(3)]
    return [(base[0] + random_source.randrange(0, 40)) | ((base[1] + random_source.randrange(0, 40)) << 8) |
            ((base[2] + random_source.randrange(0, 40)) << 16) | (random_source.getrandbits(8) << 24) for _ in range(256)]


def receiver_state(random_source, size=None, capacity=None, grow=0, with_data=True):
    """Describe the receiver's array. size is the element count, capacity the allocated slots."""
    return {"size": size, "capacity": capacity, "grow": grow, "with_data": with_data}


def build(random_source, palette, array, w1, w2, new_hook=None):
    """setup() for one call. array is a dict from receiver_state."""
    head = [random_source.getrandbits(32) | 1 for _ in range(2)]
    size, capacity, grow = array["size"], array["capacity"], array["grow"]
    initial = [random_source.getrandbits(32) | 1 for _ in range(capacity or 0)]

    def setup(env):
        # The palette lives in unused zero-initialized global data: original-only runs call a Python hook on every
        # heap access, and the 65536 nearest-color searches read the palette hundreds of times each.
        pal = PALETTE_ADDRESS
        env.put(pal, *palette)
        data = 0
        if array["with_data"]:
            data = env.object(max(4, (capacity or 0) * 4), "pointer array", words=initial or [0])
        receiver = env.object(0x20, "receiver", words=[
            head[0], head[1], data, size, capacity, grow, random_source.getrandbits(32) | 1,
            random_source.getrandbits(32) | 1])
        if new_hook:
            new_hook(env)
        return {"receiver": receiver, "palette": pal, "data": data}

    return setup


def blend(label, setup, w1, w2, **options):
    return Case(label, BLEND, setup, receiver=lambda t: t["receiver"],
                arguments=(lambda t: t["palette"], word(w1), word(w2)), **options)


def fail_from(call_number):
    def hook(env):
        env.override(OPERATOR_NEW, allocate(fail_from_call=call_number))
    return hook


def cases(random_source):
    empty = receiver_state(random_source, 0, 0, 0, with_data=False)

    # Successful full tables: varied palettes, weights and receiver array states.
    # Each successful table costs about 1.5 s per side in a comparison but several seconds in cases-check
    # (heap and block callbacks), so only a few run to completion. Each one targets a different mistake:
    # weight order, byte wrap, negative divisor, negative weights, tie-breaking, array append and growth.
    full = [
        ("asymmetric 30/70, room in array", random_palette(random_source), receiver_state(random_source, 3, 10), 30, 70),
        ("sum 510 wraps bytes, array full", random_palette(random_source), receiver_state(random_source, 2, 2), 255, 255),
        ("negative sum, duplicate palette ties, empty array", duplicate_palette(random_source), empty, -30, -70),
        ("negative weight positive sum, grow step 7", narrow_palette(random_source), receiver_state(random_source, 4, 4, 7), -20, 120),
        ("weights over 100, gradient palette", gradient_palette(), receiver_state(random_source, 8, 8), 150, 50),
        ("random weights", random_palette(random_source), receiver_state(random_source, 6, 7, 2),
         random_source.randrange(1, 120), random_source.randrange(100, 250)),
    ]
    for label, palette, array, w1, w2 in full:
        yield blend(f"full table {label}", build(random_source, palette, array, w1, w2), w1, w2)

    # Cheap failure paths: the first or the second allocation fails, so the table is never filled.
    states = [
        empty,
        receiver_state(random_source, 3, 10),
        receiver_state(random_source, 4, 4, 5),
        receiver_state(random_source, 0, 8),
    ]
    weight_pairs = [(50, 50), (0, 0), (-1, 1), (100, 0), (7, 300), (-100, -100), (99, 1), (1, 98)]
    for number in (1, 2):
        for index, array in enumerate(states):
            for w1, w2 in weight_pairs:
                pal = random_palette(random_source) if (index + w1) % 2 else gradient_palette()
                yield blend(f"allocation {number} fails, array {index}, weights {w1}/{w2}",
                            build(random_source, pal, array, w1, w2, fail_from(number)), w1, w2)
    for _ in range(12):
        w1, w2 = random_source.randrange(-300, 300), random_source.randrange(-300, 300)
        size = random_source.randrange(0, 20)
        array = receiver_state(random_source, size, size + random_source.randrange(0, 5), random_source.randrange(0, 4))
        yield blend(f"random allocation 2 failure {w1}/{w2}",
                    build(random_source, random_palette(random_source), array, w1, w2, fail_from(2)), w1, w2)
