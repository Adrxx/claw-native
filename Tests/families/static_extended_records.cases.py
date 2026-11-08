"""Blind cases derived from the five original instruction bodies."""
import ctypes
from clawparity.cases import Case
from clawparity.env import NativeSourceContext

ROOT = 0x440F30
PC = 0x43D404


def source(env, function, receiver, args, words, flags, index):
    stack = 0x2006000 - 0x100 * (index % 8)
    # Backed inherited caller frame, distinct from the active constructor frame.
    caller = stack + 0x200
    chain = stack + 0x300
    env.put(caller, caller + 0x40, PC)
    env.put(caller + 0x40, caller + 0x80, PC)
    env.put(chain, 0xFFFFFFFF, 0x506228)
    env.put(stack, PC, *args)
    env.write(stack - 0x180, bytes((x * 29 + index * 7 + 3) & 255 for x in range(0x180)))
    context = NativeSourceContext()
    context.size = ctypes.sizeof(context)
    context.version = 1
    context.inputMask = context.outputMask = 0x7FF
    context.preserveMask = 0x472
    context.eax, context.ebx, context.ecx, context.edx = words[:4]
    context.esi, context.edi = words[4:6]
    if receiver:
        context.ecx = receiver
    context.ebp, context.esp, context.eip = caller, stack, function
    context.eflags, context.fsHead = flags, chain
    return context


def cases(random_source):
    def entropy():
        return [random_source.getrandbits(32) | 1 for _ in range(12)]

    ranges = [(0, 0), (2000, 2010), (-7, -7), (-9, -3), (-3, 3),
              (0x7FFFFFFE, 0x7FFFFFFF), (-0x80000000, -0x7FFFFFFF),
              (-0x80000000, 0x7FFFFFFF)]
    ranges += [(start, start + random_source.randrange(0, 24))
               for start in (random_source.randrange(-20000, 20000) for _ in range(24))]
    ranges += [(0, 0), (2000, 2010), (-8, 8), (31, 35), (5, 4), (10, 2), (-1, -2), (1, 0)]
    for index, (first, last) in enumerate(ranges):
        words = entropy()
        flags = 2 | (random_source.getrandbits(12) & 0x8D5)
        failed = 32 <= index < 36

        def setup(env, first=first, last=last, index=index, words=words, flags=flags, failed=failed):
            envelope = env.object(68, 'range envelope', data=b''.join(w.to_bytes(4, 'little') for w in (words * 2)[:17]))
            receiver = envelope + 12
            env.put(0x52E1CC, words[8])
            for offset in range(0, 0x50, 4):
                env.put(0x544B18 + offset, words[(offset // 4) % len(words)])
            env.put(0x544B4C, 0 if index % 2 == 0 else words[7])
            env.put(0x544B5C, 4)  # Explicit genuine returning diagnostic unit policy.
            env.put(0x544B14, words[9])

            def malloc(env, call):
                if failed:
                    return 0
                return env.object(max(1, call.arguments[0]), 'exact physical malloc', fill=0xB7)

            env.override(0x4A48E0, malloc)
            return {'receiver': receiver, 'source': source(env, ROOT, receiver,
                    (first & 0xFFFFFFFF, last & 0xFFFFFFFF), words, flags, index)}

        yield Case(f'range {index}: {first}..{last} null={failed}', ROOT, setup,
                   receiver=lambda t: t['receiver'], arguments=(first & 0xFFFFFFFF, last & 0xFFFFFFFF),
                   source_context=lambda t: t['source'], source_return_pc=PC)

    for root, target in ((0x453CC0, 0x5379B8), (0x453D00, 0x5379A8),
                         (0x45ACB0, 0x537B48), (0x4F54EA, 0)):
        for index in range(16):
            words = entropy()
            flags = 2 | (random_source.getrandbits(12) & 0x8D5)
            sourced = index % 2 == 1

            def setup(env, root=root, target=target, index=index, words=words, flags=flags):
                for base in (0x5379A0, 0x537B40):
                    env.put(base, *(words * 2)[:24])
                if target:
                    receiver = 0
                elif index >= 12:
                    # A legal receiver aliases neighboring image record storage.
                    receiver = 0x5379AC + (index % 3) * 4
                else:
                    envelope = env.object(56, 'zero record envelope', data=b''.join(w.to_bytes(4, 'little') for w in (words * 2)[:14]))
                    receiver = envelope + (4 if index % 3 else 12)
                return {'receiver': receiver,
                        'source': source(env, root, receiver, (), words, flags, index)}

            yield Case(f'{root:x} {index} source={sourced}', root, setup,
                       receiver=(lambda t: t['receiver']) if not target else 0,
                       source_context=(lambda t: t['source']) if sourced else None,
                       source_return_pc=PC if sourced else 0)
