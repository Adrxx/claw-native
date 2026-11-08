"""Blind original application construction: real allocator and thread policy."""
import ctypes
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, HarnessError, HEAP_BASE
from clawparity.kernel import STACK_BASE, STACK_SIZE

specification_problems = []
FACTORY, CONSTRUCTOR = 0x423450, 0x4254A0


def scenario(rng, root, index, ticks, exhausted=False):
    contents = bytes(rng.randrange(1, 256) for _ in range(0x134))
    stack = bytes(rng.randrange(256) for _ in range(0x400))
    registers = [rng.getrandbits(32) for _ in range(7)]
    flags = 2 | (rng.getrandbits(32) & 0x8d5)
    frame = 0x02003000 + 16 * rng.randrange(32)
    fill = rng.randrange(1, 256)

    def setup(env):
        control = env.object(64, 'physical service control', fill=0)
        records = env.object(0x4000, 'physical allocation and handle records', fill=0)
        tls = env.object(128, 'physical thread slots', fill=0)
        locks = env.object(1024, 'physical critical section identities', fill=0)
        receiver = env.object(0x134, 'distinct application receiver', data=contents)
        witness = env.object(512, 'physical service observations', fill=0)
        # Metadata is itself surviving memory, so each comparison side starts
        # with identical physical service identities and allocation lifetime.
        def allocate(e, n, zero=False, kind=1):
            p = e.object(n, 'physical backing', fill=0 if zero else fill)
            i = e.get(control + 4)
            e.put(records + i * 16, p, n, kind, 0)
            e.put(control + 4, i + 1)
            return p
        def find(e, p):
            for i in range(e.get(control + 4)):
                q = records + i * 16
                if e.get(q) == p:
                    return q
            raise HarnessError('unknown physical allocation')
        def log(e, c, result):
            n = e.get(control + 24)
            if n < 12:
                args = tuple(c.arguments) + (0, 0, 0, 0)
                e.put(witness + n * 40, c.function, c.receiver, *args[:4], result,
                      e.get(control), e.get(control + 16), e.get(control + 20))
            e.put(control + 24, n + 1)
            return result
        def service(address):
            def effect(e, c):
                a = c.arguments
                if address == 0x546950: r = 0x1001
                elif address == 0x54694c: r = 1
                elif address == 0x546960:
                    r = 0 if e.get(control) else allocate(e, a[2], bool(a[1] & 8))
                elif address == 0x546964:
                    find(e, a[2]); e.release(a[2]); r = 1
                elif address == 0x546990:
                    p, n, mode, protection = a
                    if e.get(control): r = 0
                    elif mode == 0x2000: r = allocate(e, n, True, 2)
                    else:
                        r = 0
                        for i in range(e.get(control + 4)):
                            q = records + 16 * i
                            b, size = e.get(q), e.get(q + 4)
                            if e.get(q + 8) == 2 and b <= p and p + n <= b + size:
                                e.write(p, bytes(n)); r = p; break
                        if not r: raise HarnessError('commit outside physical reserve')
                elif address == 0x546954:
                    find(e, a[0]); e.release(a[0]); r = 1
                elif address in (0x546aa4, 0x546aac, 0x546a9c):
                    p = a[0]; slot = None
                    for i in range(e.get(control + 8)):
                        if e.get(locks + 8 * i) == p: slot = locks + 8 * i
                    if address == 0x546aa4:
                        i = e.get(control + 8); slot = locks + 8 * i
                        e.put(slot, p, 0); e.put(control + 8, i + 1)
                    elif slot is None: raise HarnessError('unknown physical lock')
                    else: e.put(slot + 4, (e.get(slot + 4) + (1 if address == 0x546aac else -1)) & 0xffffffff)
                    r = 0
                elif address == 0x546df0:
                    i = e.get(control + 16); r = ticks[i % len(ticks)]
                    e.put(control + 16, i + 1)
                elif address == 0x546a90:
                    r = e.get(control + 12); e.put(control + 12, r + 1); e.put(tls + 4 * r, 0)
                elif address == 0x546a7c: r = e.get(tls + 4 * a[0])
                elif address == 0x546a84: e.put(tls + 4 * a[0], a[1]); r = 1
                elif address in (0x546aa8, 0x546b1c):
                    r = allocate(e, a[1], bool(a[0] & 0x40), 3 if address == 0x546b1c else 1)
                elif address in (0x546a80, 0x546a88):
                    old, n, f = a; q = find(e, old); size = e.get(q + 4)
                    r = allocate(e, n, bool(f & 0x40), e.get(q + 8))
                    e.write(r, e.read(old, min(n, size))); e.release(old)
                elif address in (0x5469c4, 0x546a8c):
                    q = find(e, a[0]); r = a[0]
                    if address == 0x5469c4: e.put(q + 12, e.get(q + 12) + 1)
                elif address == 0x5469c8:
                    q = find(e, a[0]); n = e.get(q + 12); e.put(q + 12, max(0, n - 1)); r = int(n > 1)
                elif address == 0x546abc: r = 4
                else: raise HarnessError('undeclared physical service')
                return log(e, c, r)
            return effect
        for address in (0x546950,0x54694c,0x546960,0x546964,0x546990,0x546954,
                        0x546aa4,0x546aac,0x546a9c,0x546df0,0x546a90,0x546a7c,
                        0x546a84,0x546aa8,0x546b1c,0x546a80,0x546a88,0x5469c4,
                        0x546a8c,0x5469c8,0x546abc):
            env.override(address, service(address))
        if root == FACTORY:
            for region, base in (('heap', HEAP_BASE), ('image', env.program.base), ('stack', STACK_BASE)):
                env.machine.write(base, env._initial[region])
            env.backend, env.side, env._source_graph = 'machine', 'setup', True
            env._source_budget = ctypes.c_uint64(2000000)
            def call(pc, args=()):
                r = env.machine.call(pc, 0, 0, args, stack_pointer=0x02001000)
                if not r.completed: raise HarnessError('real setup producer did not return')
                return r.eax
            if call(0x4ab120) != 1: raise HarnessError('real heap bootstrap failed')
            call(0x4a7b90)
            if exhausted:
                # Explicit nondefault policy, created by the real TLS/thread path.
                prior = call(0x4f63d8, (0,))
                if prior != 0x4f63d0: raise HarnessError('unexpected original default handler')
                env.put(control, 1)
                for n in range(512):
                    if call(0x4a48e0, (0x134,)) == 0: break
                else: raise HarnessError('real small heap did not exhaust')
                env.put(control + 20, n)
            heap = env.read(HEAP_BASE, env.heap_bytes)
            image = env.read(env.program.data_start, env.program.size - env.data_offset)
            env.backend, env.side, env._source_graph = 'initial', 'setup', False
            env.write(HEAP_BASE, heap); env.write(env.program.data_start, image)
        env.put(control + 16, 0); env.put(control + 24, 0)
        env.write(frame - 0x300, stack)
        fs = 0xffffffff
        if index % 2:
            fs = frame + 0x200
            env.put(fs, 0xffffffff, 0x504b4b, registers[0])
        source = NativeSourceContext()
        source.size, source.version = 72, 1
        source.inputMask = source.outputMask = 0x7ff
        for name, value in zip(('eax','ebx','ecx','edx','esi','edi','ebp'), registers): setattr(source,name,value)
        source.ecx = receiver
        source.esp, source.eip, source.eflags, source.fsHead = frame, root, flags, fs
        return dict(receiver=receiver, source=source)
    return Case(f'{"factory null policy" if exhausted else "factory" if root == FACTORY else "constructor holes"} {index}',
                root, setup, receiver=lambda t:t['receiver'], source_context=lambda t:t['source'],
                source_return_pc=0x4b8b5b if root == FACTORY else 0x42348a)


def cases(random_source):
    timelines = [(0,0), (1,2), (0xffffffff,0), (0x80000000,0x7fffffff),
                 (0x7fffffff,0x80000000), (0xfffffffe,1)]
    timelines += [(random_source.getrandbits(32), random_source.getrandbits(32)) for _ in range(6)]
    for i, ticks in enumerate(timelines):
        yield scenario(random_source, CONSTRUCTOR, i, ticks)
    for i, ticks in enumerate(timelines[:4]):
        yield scenario(random_source, FACTORY, i, ticks)
    for i in range(2):
        yield scenario(random_source, FACTORY, i, timelines[i], exhausted=True)
