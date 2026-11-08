"""Shared input construction for the two original duration initializers."""

from clawparity.cases import Case


def profile_cases(random_source, entry, first_offset):
    """Exercise initialization, preserved values, wrapping sums and aliasing."""
    second_offset = first_offset + 4

    def make_case(label, first, second, destination="separate"):
        # Make neighboring fields distinct so incorrect offsets or store widths
        # leave observable differences in the surviving heap image.
        source_words = [random_source.randrange(1, 0x100000000) for _ in range(128)]
        target_words = [random_source.randrange(1, 0x100000000) for _ in range(40)]

        def setup(env):
            source = env.object(0x200, "duration-input", words=source_words)
            if destination == "separate":
                target = env.object(0xA0, "duration-output", words=target_words)
            elif destination == "same":
                target = source
            elif destination == "first":
                target = source + first_offset - 0x4C
            else:
                target = source + second_offset - 0x4C
            env.put(source + first_offset, first, second)
            return {"source": source, "target": target}

        return Case(
            label,
            entry,
            setup,
            arguments=(lambda tokens: tokens["source"], lambda tokens: tokens["target"]),
        )

    # All four zero/nonzero branch combinations are deterministic for every seed.
    # Include signed boundaries and additions that wrap to zero or carry out.
    values = (0, 1, 1500, 0x7FFFFFFF, 0x80000000, 0xFFFFFA24, 0xFFFFFFFF)
    for first in values:
        for second in values:
            yield make_case(f"values {first:08x} {second:08x}", first, second)

    for index in range(8):
        first = random_source.randrange(1, 0x100000000)
        second = random_source.randrange(1, 0x100000000)
        yield make_case(f"random preserved values {index}", first, second)

    # The output can overlap either input field. This exposes incorrect store
    # order, including storing the sum before defaulting the second duration.
    for destination in ("same", "first", "second"):
        for first, second in ((0, 0), (0, 0xFFFFFFFF), (0x80000000, 0), (17, 29)):
            yield make_case(
                f"alias {destination} {first:08x} {second:08x}", first, second, destination
            )
