"""Blind whole graphics-record construction from pinned original instructions."""
from clawparity.cases import Case


def setup_record(data, offset, global_values):
    def setup(env):
        storage = env.object(len(data), 'patterned-record-and-canaries', data=data)
        env.put(0x5430c4, global_values[0], global_values[1])
        return storage + offset
    return setup


def cases(random_source):
    patterns = [bytes([fill]) * 92 for fill in (0, 0xff, 0xa5, 0x5a)]
    patterns += [bytes(range(92)), bytes(255-i for i in range(92))]
    patterns += [bytes(random_source.randrange(256) for _ in range(92)) for _ in range(32)]
    for index, data in enumerate(patterns):
        for offset in (0, 4, 16, 32):
            values = (random_source.getrandbits(32) | 1, random_source.getrandbits(32) | 1)
            yield Case(f'pattern{index}-offset{offset}', 0x4ce960,
                       setup_record(data, offset, values), receiver=lambda token: token,
                       compare_eax=True)
