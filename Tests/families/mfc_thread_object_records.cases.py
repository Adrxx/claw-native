"""Independent original thread-record cases, including physical source frames."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext

BASE, RESET, CONSTRUCT = 0x4F6A9A, 0x50354D, 0x503510
CURSOR = 0x546CD0
LOW, SIZE = 0x01FF0000, 0x20000
FIELDS = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eip', 'eflags', 'fsHead')
RETURN = {BASE: 0x503526, RESET: 0x50353E, CONSTRUCT: 0x502597}
# Independently counted lowest writes: PUSH 1; saved ESI/EDI + arg + CALL;
# compiler registration + locals + base PUSH + nested cursor CALL respectively.
HEADROOM = {BASE: 4, RESET: 16, CONSTRUCT: 44}


def build(function, payload, stack, registers, flags, offset, frame, chain, point, result, source):
    def setup(env):
        allocation = env.object(0x100, 'record-and-canaries', data=payload)
        receiver = allocation + 0x20 + offset
        context = None
        if source:
            env.write(LOW, stack)
            head = 0xffffffff
            for index in range(chain):
                slot = LOW + 0x18000 + index * 16
                env.put(slot, head, 0x508ca4, 0xffffffff)
                head = slot
            context = NativeSourceContext(72, 1, 0x7ff, 0x7ff,
                registers[0], registers[1], receiver, registers[2], registers[3], registers[4],
                registers[5], frame, function, flags, head, 0x472, 0, 0)
            env.put(frame, RETURN[function])
            observation = env.object(SIZE + 0x200, 'physical-cursor-observation', fill=0xAD)
        else:
            observation = env.object(0x200, 'ordinary-cursor-observation', fill=0xAD)

        def cursor(env, call):
            # EAX is the declared service result. All other volatile CPU fields
            # are preserved by this fixture policy, on TRUE and FALSE alike.
            # FALSE explicitly leaves the POINT bytes unchanged.
            env.put(observation, call.function, call.receiver, call.receiver2,
                    call.arguments[0], call.stack_pointer, call.source_return_pc)
            env.write(observation + 0x20, env.read(allocation, 0x100))
            if call.source_context is not None:
                physical = call.source_context
                env.put(observation + 0x120, *(getattr(physical, name) for name in FIELDS))
                env.write(observation + 0x150, bytes(physical))
                env.write(observation + 0x200, env.read(LOW, SIZE))
            if result:
                env.put(call.arguments[0], *point)
            return result

        env.override(CURSOR, cursor)
        return {'receiver': receiver, 'source': context}
    return setup


def cases(random_source):
    points = ((0, 0), (1, -1), (-1, 1), (-0x80000000, 0x7fffffff),
              (0x7fffffff, -0x80000000), (-32768, 65535), (0x12345678, -123456789))
    for function in (BASE, RESET, CONSTRUCT):
        for index in range(32):
            payload = bytes(random_source.randrange(1, 256) for _ in range(0x100))
            pattern = bytes(random_source.randrange(256) for _ in range(257))
            stack = (pattern * (SIZE // len(pattern) + 1))[:SIZE]
            registers = [random_source.getrandbits(32) for _ in range(6)]
            registers[5] = (0, 0xffffffff, 0x80000001, random_source.getrandbits(32))[index % 4]
            flags = (2, 0x8d7, 0x47, 0x892)[index % 4]
            # Includes the exact physical minimum as well as one-word extra
            # room and arbitrary unaligned frame locations across the backing.
            frame = (LOW + HEADROOM[function], LOW + HEADROOM[function] + 4,
                     LOW + SIZE - 4, LOW + 0x8000 + index * 52)[index % 4]
            point = points[index % len(points)] if index < 28 else tuple(random_source.getrandbits(32) for _ in range(2))
            result = (0, 1, 0x80000000, 0xffffffff)[index % 4]
            yield Case(f'source {function:x} {index} headroom {frame-LOW}', function,
                build(function, payload, stack, registers, flags, index % 4, frame,
                      index % 4, point, result, True), receiver=lambda t: t['receiver'],
                source_context=lambda t: t['source'], source_return_pc=RETURN[function])
        if function != CONSTRUCT:
            for index in range(12):
                payload = bytes(random_source.randrange(1, 256) for _ in range(0x100))
                yield Case(f'ordinary {function:x} {index}', function,
                    build(function, payload, b'', (), 2, index % 4, 0, 0,
                          points[index % len(points)], (0, 1, 0xffffffff)[index % 3], False),
                    receiver=lambda t: t['receiver'])
