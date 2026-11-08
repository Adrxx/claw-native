"""Original-only inputs for the menu window record initializer."""
from clawparity.cases import Case

INITIALIZE = 0x4B8410


def record_input(payload, prefix, allocations):
    def setup(env):
        # Different receiver addresses distinguish returning this from a constant.
        for index in range(allocations):
            env.object(13 + index, f"unrelated-{index}", fill=0x79)
        backing = env.object(len(payload), "guarded-window-record", data=payload)
        return backing + prefix

    return setup


def cases(random_source):
    # Poison initialized fields, the untouched +8 word and both neighboring regions.
    for index, gap in enumerate((0, 1, 0xFFFFFFFF, 0x80000000, 0x12345678, 0xA5B6C7D8)):
        prefix = 8
        payload = bytearray(range(0x21, 0x21 + 32))
        payload[prefix + 8:prefix + 12] = gap.to_bytes(4, "little")
        yield Case(
            f"preserve gap {gap:#x} and guards",
            INITIALIZE,
            record_input(bytes(payload), prefix, index),
            receiver=lambda target: target,
            compare_eax=True,
        )

    for index in range(20):
        # Exercise aligned and unaligned receivers, with nonzero random sentinels.
        prefix = 4 + index % 8
        payload = bytes(random_source.randrange(1, 256) for _ in range(prefix + 16 + 11))
        yield Case(
            f"random poisoned record {index}",
            INITIALIZE,
            record_input(payload, prefix, index % 5),
            receiver=lambda target: target,
            compare_eax=True,
        )
