"""The scoped startup hook returns zero without using its receiver."""
from clawparity.cases import Case


STARTUP_ZERO_HOOK = 0x42A680


def patterned_storage(data, receiver_offset=0):
    def setup(env):
        application = env.object(len(data), "application", data=data)
        env.object(73, "neighbor", data=bytes((index * 29 + 11) & 0xFF for index in range(73)))
        return application + receiver_offset

    return setup


def cases(random_source):
    for receiver in (0, 1, 3, 0xDEADBEEF, 0x80000000, 0xFFFFFFFF):
        yield Case(
            f"raw receiver {receiver:#010x} is unused",
            STARTUP_ZERO_HOOK,
            setup=patterned_storage(bytes(range(1, 129))),
            receiver=receiver,
            compare_eax=True,
            covers=("zero return", "no dereference", "no memory changes", "no events"),
        )

    for index, data in enumerate((bytes([0xA5]) * 257, bytes([0xFF]) * 257, bytes(range(256)) + b"\x5a")):
        for offset in (0, 1, 128, 256):
            yield Case(
                f"pattern {index} receiver offset {offset} remains unchanged",
                STARTUP_ZERO_HOOK,
                setup=patterned_storage(data, offset),
                receiver=lambda address: address,
                compare_eax=True,
                covers=("zero return", "no memory changes", "no events"),
            )

    for index in range(12):
        data = bytes(random_source.randrange(1, 256) for _ in range(513))
        offset = random_source.randrange(len(data))
        yield Case(
            f"random application {index} receiver offset {offset}",
            STARTUP_ZERO_HOOK,
            setup=patterned_storage(data, offset),
            receiver=lambda address: address,
            compare_eax=True,
            covers=("zero return", "receiver independence", "no memory changes", "no events"),
        )
