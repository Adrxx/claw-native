"""Independent physical-source cases for the borrowed static lock object."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

ROOT = 0x4a2cf1
RETURN = 0x502c95
INITIALIZE = 0x546aa4
FIELDS = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp',
          'eip', 'eflags', 'fsHead')


def make_case(rng, index, mode, stopped=False, global_receiver=False):
    words = [rng.getrandbits(32) for _ in range(7)]
    words[6] = (0, 0xffffffff, words[6])[index % 3]
    flags = 2 | (rng.getrandbits(32) & 0x8d5)
    frame = (STACK_TOP, STACK_BASE + 0x1000, STACK_TOP - 0x174)[index % 3]
    stack = rng.randbytes(STACK_SIZE)
    poison = rng.randbytes(60)
    service_words = [rng.getrandbits(32) for _ in range(6)]
    service_result = rng.getrandbits(32)

    def setup(env):
        receiver = 0x540708 if global_receiver else env.object(60, 'borrowed lock receiver', data=poison)
        env.write(receiver, poison)
        journal = env.object(256, 'physical initialize observations', fill=0xc7)
        env.write(STACK_BASE, stack)
        head = 0xffffffff
        if index % 3:
            head = frame + 0x100
            env.put(head, head + 0x30 if index % 3 == 2 else 0xffffffff,
                    0x508bbc, words[0])
            if index % 3 == 2:
                env.put(head + 0x30, 0xffffffff, 0x508bbc, words[1])
        env.put(frame, RETURN)
        context = NativeSourceContext(72, 1, 0x7ff, 0x7ff, *words,
                                      frame, ROOT, flags, head, 0, 0, 0)
        context.ecx = receiver

        def initialize(e, call):
            state = call.source_context
            values = [getattr(state, name) for name in FIELDS]
            e.put(journal, e.calls_so_far(INITIALIZE), call.function,
                  call.receiver, call.stack_pointer, call.source_return_pc,
                  call.arguments[0], *values)
            e.write(journal + 80, e.read(receiver, 60))
            e.write(journal + 144, e.read(frame - 48, 52))
            if mode == 'all':
                e.put(call.arguments[0], *service_words)
            elif mode == 'partial':
                e.put(call.arguments[0], service_words[0])
                e.write(call.arguments[0] + 9, bytes([service_words[1] & 255]))
                e.put(call.arguments[0] + 20, service_words[5])
            elif mode == 'alias':
                e.put(call.arguments[0], *service_words)
                e.put(receiver, service_words[0])
                e.put(receiver + 28, service_words[1])
                e.put(receiver + 8, service_words[2])
            if stopped:
                raise Halt()
            return service_result

        env.override(INITIALIZE, initialize)
        return {'receiver': receiver, 'source': context}

    return Case(f'CPU {index} initialize {mode} stop {stopped} global {global_receiver}',
                ROOT, setup, receiver=lambda t: t['receiver'],
                source_context=lambda t: t['source'], source_return_pc=RETURN,
                expect='halt' if stopped else 'return')


def cases(random_source):
    for index in range(48):
        yield make_case(random_source, index, ('all', 'partial', 'none', 'alias')[index % 4],
                        global_receiver=index % 8 == 0)
    for index in range(12):
        yield make_case(random_source, index + 48,
                        ('all', 'partial', 'none', 'alias')[index % 4], stopped=True,
                        global_receiver=index % 4 == 0)
