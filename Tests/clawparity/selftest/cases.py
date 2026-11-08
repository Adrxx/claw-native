"""Cases for the synthetic self-test program."""
from clawparity.cases import Case
from clawparity.fixtures import allocate

SUM, SCALED, BUFFER, ALLOCATE = 0x401000, 0x401010, 0x401030, 0x402000


def cases(random_source):
    for _ in range(20):
        words = [random_source.getrandbits(32) for _ in range(2)]
        yield Case("sum", SUM, lambda env, words=words: env.object(16, "pair", words=words + [0, 0]), receiver=lambda token: token)
    for _ in range(20):
        yield Case("scaled", SCALED, arguments=(random_source.getrandbits(32), random_source.getrandbits(32)))
    for count in (0, 1, 2, 7, 40):
        yield Case(f"buffer {count}", BUFFER, lambda env: env.object(4, "holder"), receiver=lambda token: token, arguments=(count,))

    def no_memory(env):
        env.override(ALLOCATE, allocate(fail=True))
        return env.object(4, "holder")

    yield Case("buffer allocation fails", BUFFER, no_memory, receiver=lambda token: token, arguments=(9,))
