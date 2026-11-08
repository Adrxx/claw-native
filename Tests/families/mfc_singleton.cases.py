"""Independent whole-body singleton cases using unchanged original factories."""
import ctypes
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_FIELDS

ROOT = 0x503420
FACTORIES = ((0x502369, 0x5022b4), (0x502bde, 0x4f8996), (0x502c0f, 0x4fa56e))
LOCK = 0x5408f0 + 16 * 24


def setup_case(factory, return_pc, mode, values, frame, initialized):
    def setup(env):
        owner = env.object(4, 'singleton-owner', fill=0)
        existing = env.object(0x1074, 'published-object', fill=values[0] & 255)
        replacement = env.object(0x1074, 'replacement-object', fill=values[1] & 255)
        tls = env.object(0x74, 'crt-thread-data', fill=0)
        physical = env.object(8, 'physical-thread-state', words=[values[2], 0])
        observation = env.object(64, 'lock-observation', fill=0)
        env.put(tls, values[3], 0xffffffff)
        env.put(0x52edd8, 7)
        env.put(0x5408e8, int(initialized))
        env.put(0x540a88, 0)
        env.put(0x540aa8 + 16 * 4, int(initialized))
        env.write(LOCK, bytes(24))
        env.write(0x540a90, bytes(24))
        if mode == 'warm':
            env.put(owner, existing)

        def initialize(e, call):
            e.write(call.arguments[0], bytes(24))
            return 0

        def enter(e, call):
            p = call.arguments[0]
            e.put(p, e.get(p) + 1)
            if p == LOCK:
                e.put(observation, e.get(owner), call.receiver, *call.arguments)
                if mode == 'second-check':
                    e.put(owner, existing)
            return values[4]

        def leave(e, call):
            p = call.arguments[0]
            e.put(p, e.get(p) - 1)
            if p == LOCK:
                e.put(observation + 16, e.get(owner), call.receiver, *call.arguments)
                if mode == 'fresh-owner':
                    e.put(owner, replacement)
            return values[5]

        def local_alloc(e, call):
            if mode == 'failure':
                return 0
            return e.object(call.arguments[1], 'local-allocation', fill=0)

        def last_error(e, call):
            return e.get(physical)

        def set_error(e, call):
            e.put(physical, call.arguments[0])
            return 0

        def tls_get(e, call):
            e.put(physical, 0)
            return tls if call.arguments[0] == 7 else 0

        def mapped(e, p, n):
            return (n == 0 or any(a <= p and p + n <= a + size for a, size in e.spans.items())
                    or STACK_BASE <= p <= p + n <= STACK_BASE + STACK_SIZE
                    or e.program.base <= p <= p + n <= e.program.base + e.program.size)

        env.override(0x546abc, lambda e, c: 0x00000005)
        env.override(0x546aa4, initialize)
        env.override(0x546aac, enter)
        env.override(0x546a9c, leave)
        env.override(0x546aa8, local_alloc)
        env.override(0x546b0c, last_error)
        env.override(0x546ab8, set_error)
        env.override(0x546a7c, tls_get)
        env.override(0x546a40, lambda e, c: int(not mapped(e, *c.arguments)))
        env.override(0x546984, lambda e, c: int(not mapped(e, *c.arguments)))
        env.override(0x546988, lambda e, c: int(not e.program.in_text(c.arguments[0])))
        context = NativeSourceContext()
        context.size = ctypes.sizeof(context)
        context.version = 1
        context.inputMask = context.outputMask = 0x7ff
        for name, value in zip(CONTEXT_FIELDS, values):
            setattr(context, name, value)
        context.ecx = owner
        context.esp = frame
        context.eip = ROOT
        context.eflags = 2 | (values[6] & 0x8d5)
        context.fsHead = 0xffffffff
        env.put(frame, return_pc, factory)
        return {'owner': owner, 'context': context}
    return setup


def cases(random_source):
    for factory, return_pc in FACTORIES:
        for mode in ('warm', 'success', 'failure', 'second-check', 'fresh-owner'):
            for variant in range(4):
                values = [random_source.getrandbits(32) for _ in CONTEXT_FIELDS]
                frame = STACK_TOP - variant * 0x100
                yield Case(f'{factory:x} {mode} context {variant}', ROOT,
                           setup_case(factory, return_pc, mode, values, frame, variant % 2),
                           receiver=lambda t: t['owner'], arguments=(factory,),
                           source_context=lambda t: t['context'], source_return_pc=return_pc,
                           expect='unhandled' if mode == 'failure' else 'return',
                           covers=(mode, 'full-source-context', f'factory-{factory:x}'))
