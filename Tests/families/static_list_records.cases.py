"""Independent original cases for static lists, scalar records and message publication."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

TWINS = (0x4a13f4, 0x4a141e, 0x4a2e53, 0x4a2e7d)
THUNKS = ((0x50254b, 0x52e490), (0x5028dc, 0x52e540),
          (0x502b05, 0x52e5a8), (0x502b52, 0x52e5e0))
PC = 0x4a5896


def source(env, function, receiver, seed, preserve=0):
    frame = STACK_TOP - (seed % 4) * 0x1000
    pattern = bytes(((i * 37 + seed * 13) & 255) for i in range(256))
    env.write(STACK_BASE, pattern * (STACK_SIZE // 256))
    head = 0xffffffff if seed % 2 else STACK_BASE + 0x100
    if head != 0xffffffff:
        env.put(head, 0xffffffff, PC, 0xabcdef01)
    values = [((seed + 1) * 0x1234567 + i * 0x87654321) & 0xffffffff for i in range(7)]
    values[2] = receiver
    return NativeSourceContext(72, 1, 0x7ff, 0x7ff, *values, frame, function,
                               (0x2, 0x47, 0x892, 0x8d7)[seed % 4], head,
                               preserve, 0, 0)


def record_setup(function, seed, size):
    def setup(env):
        block = env.object(size + 48, 'poisoned record and guards',
                           data=bytes(((i * 29 + seed * 19 + 7) & 255) for i in range(size + 48)))
        receiver = block + (4, 12, 20)[seed % 3]
        return dict(receiver=receiver, source=source(env, function, receiver, seed,
                    0x472 if function == 0x4fb15d else 0))
    return setup


def physical(env, seed, fail=None, tls=0, existing_global=None):
    """Physical resource state is surviving memory, never captured mutable Python state."""
    state = env.object(4096, 'physical services and observations', fill=0)
    env.put(state, 7, tls, 1 if existing_global else 0, 0)
    if existing_global:
        env.put(state + 128, *existing_global)
    # Metadata table entries: handle, data, size, locks. Separate movable identities.
    def observe(e, c):
        n = e.get(state + 12)
        at = state + 512 + 96 * n
        ctx = c.source_context
        e.put(at, c.function, c.receiver, c.stack_pointer, c.source_return_pc,
              len(c.arguments), *(tuple(c.arguments) + (0,) * (4-len(c.arguments))))
        e.write(at + 36, e.read(c.stack_pointer, min(32, STACK_BASE + STACK_SIZE-c.stack_pointer)))
        if ctx is not None:
            e.put(at + 68, ctx.eax, ctx.ecx, ctx.edx, ctx.eflags, ctx.fsHead)
        e.put(state + 12, n + 1)
    def alloc(e, flags, size, movable=False):
        p = e.object(max(1, size), 'physical allocation', fill=0 if flags & 0x40 else 0xa9)
        if not movable:
            return p
        h = e.object(4, 'movable handle', words=[p])
        n = e.get(state + 8)
        e.put(state + 128 + n * 16, h, p, size, 0)
        e.put(state + 8, n + 1)
        return h
    def meta(e, value):
        for i in range(e.get(state + 8)):
            a = state + 128 + 16*i
            if value in (e.get(a), e.get(a+4)):
                return a
        return 0
    def effect(e, c):
        observe(e, c)
        f, a = c.function, c.arguments
        if f == 0x546958:
            raise Halt()
        if f == 0x546a90:
            return 0xffffffff if fail == 'tls-index' else e.get(state)
        if f == 0x546a7c:
            return e.get(state+4) if a[0] == e.get(state) else 0
        if f == 0x546a84:
            if fail == 'tls-publish':
                return 0
            if a[0] == e.get(state):
                e.put(state+4, a[1])
                return 1
            return 0
        if f == 0x546abc:
            return 0x80000003 if seed % 5 == 4 else 0x00000006
        if f == 0x546aa4:
            e.put(a[0], 0, 0xffffffff, 0, 0, 0, 0)
            return 0
        if f in (0x546aac, 0x546a9c):
            # Windows CRITICAL_SECTION owner / recursion fields.
            p = a[0]
            depth = e.get(p+8)
            if f == 0x546aac:
                e.put(p+8, depth+1, 0x17)
            else:
                e.put(p+8, (depth-1)&0xffffffff, 0x17 if depth > 1 else 0)
            return 0
        if f == 0x546aa8:
            if fail == 'local' or (fail == 'tls-array' and a[0] == 0):
                return 0
            return alloc(e, a[0], a[1])
        if f == 0x546a80:
            if fail == 'local-grow':
                return 0
            p = alloc(e, 0, a[1])
            # Old sizes are read from coherent container capacity, not a guessed output.
            oldsize = e.get(tls+8)*4 if tls else 0
            e.write(p, e.read(a[0], min(oldsize, a[1])))
            e.release(a[0])
            return p
        if f == 0x546b1c:
            return 0 if fail == 'global' else alloc(e, a[0], a[1], True)
        if f == 0x546a8c:
            m = meta(e, a[0])
            return e.get(m) if m else 0
        if f == 0x5469c8:
            m = meta(e, a[0])
            if m:
                e.put(m+12, max(0, e.get(m+12)-1))
            return 0
        if f == 0x5469c4:
            m = meta(e, a[0])
            if not m:
                return 0
            e.put(m+12, e.get(m+12)+1)
            return e.get(m+4)
        if f == 0x546a88:
            m = meta(e, a[0])
            if fail == 'global-grow':
                return 0
            p = alloc(e, a[2], a[1])
            e.write(p, e.read(e.get(m+4), min(e.get(m+8), a[1])))
            e.release(e.get(m+4))
            e.put(m+4, p, a[1], 0)
            e.put(a[0], p)
            return a[0]
        raise RuntimeError('undeclared physical service')
    for f in (0x546a90,0x546a7c,0x546a84,0x546aa4,0x546aac,0x546a9c,
              0x546b1c,0x546a8c,0x5469c8,0x546a88,0x5469c4,0x546aa8,
              0x546a80,0x546958,0x546abc):
        env.override(f, effect)
    return state


def list_setup(function, seed, mode='warm', fail=None, node=0):
    def setup(env):
        module = env.object(0x1074, 'module', fill=0x6d)
        oldhead = env.object(24, 'old runtime class', fill=0x9b)
        older = env.object(24, 'older runtime class', fill=0xc3)
        env.put(oldhead+20, older)
        env.put(older+20, 0)
        env.put(module+0x1c, oldhead if seed % 3 else 0, 20)
        record = env.object(0x118, 'thread record', fill=0)
        env.put(record+4, module if mode == 'warm' else 0)
        container = env.object(16, 'TLS container', fill=0)
        array = env.object(16, 'TLS value array', words=[0,record,0,0])
        env.put(container, 0x511a64, 0, 4, array)
        manager = env.object(64, 'TLS manager', fill=0)
        env.put(manager, 7, 32, 2, 2, 0, container, 4)
        env.put(manager+28, 0,0xffffffff,0,0,0,0)
        if mode == 'cold':
            env.put(0x540af0, 0)
            env.put(0x53ec9c, 0)
        else:
            env.put(0x540af0, manager)
            env.put(0x53ec9c, 1)
        env.put(0x53eca0, 0)
        env.put(0x5408e8, 0 if seed % 2 else 1)
        env.put(0x540a88, 0)
        env.put(0x540aa8, 0 if seed % 2 else 1)
        env.put(0x540a90, 0,0xffffffff,0,0,0,0)
        env.put(0x5408f0, 0,0xffffffff,2 if seed % 3 == 2 else 0,
                0x17 if seed % 3 == 2 else 0,0,0)
        existing_global = None
        if mode == 'slot-grow':
            table = env.object(256, 'full physical movable slot table', fill=0)
            for offset in range(0, 256, 8):
                env.put(table+offset, 1, 0)
            handle = env.object(4, 'existing movable handle', words=[table])
            existing_global = (handle, table, 256, 1)
            env.put(manager+4, 32, 32, 32, table)
            env.put(0x53ec9c, 0)
        if mode == 'tls-grow':
            env.put(container+8, 1)
            env.put(record+4, 0)
        if mode == 'tls-empty':
            # Original SetValue prepends the new container at +4 of the old TLS head.
            env.put(container+4, env.object(16, 'older TLS head', fill=0))
        physical(env, seed, fail, 0 if mode in ('cold','tls-empty') else container,
                 existing_global)
        target = node or env.object(40, 'class node and guards', fill=0x85)
        # Static thunk nodes are mapped globals. Preserve all non-link bytes as poison.
        env.write(target, bytes(((seed*17 + i*11 + 3)&255) for i in range(24)))
        env.put(target+20, older)
        receiver = (0, 0xffffffff, 0x53edd8, module)[seed % 4] if function == 0x4f709b else 0
        return dict(node=target, receiver=receiver,
                    source=source(env, function, receiver, seed))
    return setup


def cases(random_source):
    scalars = (0,1,0xffffffff,0xfffffffe,0x80000000,0x7fffffff,0x5555aaaa,0xaaaa5555)
    for f in TWINS:
        for i in range(16):
            a = scalars[i] if i < 8 else random_source.getrandbits(32)
            b = (61474,61476,61475,61473,0,1,0xffffffff,0x80000000)[i] if i < 8 else random_source.getrandbits(32)
            yield Case(f'typed {f:x} {i}', f, record_setup(f,i+16*random_source.randrange(64),0x98),
                       receiver=lambda t:t['receiver'], arguments=(a,b),
                       source_context=lambda t:t['source'], source_return_pc=PC)
    for f,size in ((0x4f8371,60),(0x4fb15d,8)):
        for i in range(16):
            a = scalars[i] if i < 8 else random_source.getrandbits(32)
            yield Case(f'record {f:x} {i}', f, record_setup(f,i+16*random_source.randrange(64),size),
                       receiver=lambda t:t['receiver'], arguments=(a,),
                       source_context=lambda t:t['source'], source_return_pc=PC)
    for i,a in enumerate(scalars):
        yield Case(f'base ordinary {i}',0x4fb15d,record_setup(0x4fb15d,i,8),
                   receiver=lambda t:t['receiver'],arguments=(a,))
    for i in range(10):
        value = (0,0xc000,0xc001,0xffff,0x12345678)[i%5]
        def setup(env,i=i,value=value):
            observed = env.object(128, 'message physical observations', fill=0xa5)
            env.put(0x5406fc, 0xbad0cafe ^ i)
            def publish(e,c):
                e.put(observed,c.receiver,c.arguments[0],c.stack_pointer,c.source_return_pc)
                e.write(observed+16,e.read(c.arguments[0],21))
                e.write(observed+40,e.read(c.stack_pointer,24))
                s=c.source_context
                if s is not None:
                    e.put(observed+64,s.eax,s.ebx,s.ecx,s.edx,s.esi,s.edi,s.ebp,s.eflags,s.fsHead)
                return value
            env.override(0x546c2c,publish)
            return dict(source=source(env,0x4f8222,0,i))
        yield Case(f'publisher {i}',0x4f8222,setup,source_context=lambda t:t['source'],source_return_pc=PC)
    for f,node in ((0x4f709b,0),*THUNKS):
        for i in range(8):
            mode = ('warm','module-cold','cold')[i%3]
            yield Case(f'class list {f:x} {mode} {i}',f,list_setup(f,i,mode,node=node),
                       receiver=(lambda t:t['receiver']) if f == 0x4f709b else 0,
                       arguments=((lambda t:t['node']),) if f == 0x4f709b else (),
                       source_context=lambda t:t['source'],source_return_pc=PC)
    yield Case('TLS publication physical failure leaves TLS empty',0x4f709b,
               list_setup(0x4f709b,23,'cold','tls-publish'),receiver=lambda t:t['receiver'],
               arguments=(lambda t:t['node'],),source_context=lambda t:t['source'],
               source_return_pc=PC)
    for i,(f,node) in enumerate(THUNKS):
        yield Case(f'thunk physical allocation Halt {f:x}',f,
                   list_setup(f,31+i,'cold','local',node=node),
                   source_context=lambda t:t['source'],source_return_pc=PC,expect='halt')
    for i,mode in enumerate(('slot-grow','tls-grow','tls-empty')):
        for j in range(2):
            yield Case(f'physical growth {mode} {j}',0x4f709b,
                       list_setup(0x4f709b,i*2+j+11,mode),receiver=lambda t:t['receiver'],
                       arguments=(lambda t:t['node'],),source_context=lambda t:t['source'],
                       source_return_pc=PC)
    for i,(mode,fail) in enumerate((('cold','tls-index'),('cold','local'),
            ('cold','global'),('cold','tls-array'),('slot-grow','global-grow'),
            ('tls-grow','local-grow'))):
        yield Case(f'cold physical failure {fail}',0x4f709b,
                   list_setup(0x4f709b,i,mode,fail),receiver=lambda t:t['receiver'],
                   arguments=(lambda t:t['node'],),source_context=lambda t:t['source'],
                   source_return_pc=PC,expect='halt')
