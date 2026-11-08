"""Equal-factor exit of unchanged 0x420af0: ST(0) is the +0x28 binary64."""
import struct
from clawparity.cases import Case

MOTION = 0x420af0
# Binary64 bit patterns returned through ST(0), including values whose load
# changes SW (signaling NaN sets IE) and the binary64 extremes.
RESULTS = (0x0000000000000000, 0x8000000000000000, 0x3ff0000000000000, 0xc004000000000000,
           0x0000000000000001, 0x800fffffffffffff, 0x7fefffffffffffff, 0x7ff0000000000000,
           0xfff0000000000000, 0x7ff8000000000000, 0x7ff0000000000001, 0xfff4000000000123,
           0x3fb999999999999a, 0x400921fb54442d18)
FACTORS = (0x0000000000000000, 0x8000000000000000)  # both equal the 0.0 constant


def motion(factor, result, filler):
    data = bytearray(struct.pack('<Q', filler) * 10)
    data[0x10:0x18] = struct.pack('<Q', factor)
    data[0x28:0x30] = struct.pack('<Q', result)
    return lambda env: env.object(0x50, 'motion', data=bytes(data))


def cases(random_source):
    for index, result in enumerate(RESULTS):
        for factor in FACTORS:
            filler = random_source.getrandbits(64)
            elapsed = struct.unpack('<2I', struct.pack('<d', random_source.uniform(-50.0, 50.0)))
            yield Case(f'equal factor {factor:#x} result {result:#018x}', MOTION, motion(factor, result, filler),
                       receiver=lambda token: token, arguments=elapsed, covers=(f'result_{index}',))
