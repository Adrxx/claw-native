"""Independent whole-source CRT section cases, with bounded physical owners."""
import ctypes
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Call, Halt, HarnessError
from clawparity.kernel import STACK_BASE, STACK_SIZE, Machine

specification_problems = []

INIT, ACQUIRE, RELEASE = 0x4a7b90, 0x4a7bc0, 0x4a7c40
TABLE = 0x52ed18
PCS = {INIT: 0x4a7bbb, ACQUIRE: 0x4af99b, RELEASE: 0x4a5877}


def context(function, seed, esp=0x02007000):
    c = NativeSourceContext()
    c.size, c.version, c.inputMask, c.outputMask, c.preserveMask = ctypes.sizeof(c), 1, 0x7ff, 0x7ff, 0x472
    for i, name in enumerate(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp')):
        setattr(c, name, (seed * (i + 3) + 0x1234567 * (i + 1)) & 0xffffffff)
    c.esp, c.eip, c.eflags, c.fsHead = esp, function, 2 | (seed & 0x8d5), 0xffffffff
    return c


def original(env, function, arguments=(), initial=False):
    """Run a real producer on a separate frame, preserving the suspended CPU/FS."""
    machine = env.machine
    saved, fs, backend = machine.uc.context_save(), machine.fs_head, env.backend
    source = context(function, 71, 0x02001000)
    if backend == 'native':
        call = Call(function, 0, 0, arguments, source.esp, source_context=source, source_return_pc=PCS[function])
        try:
            return env._bridge(call, source=source, source_convention='cdecl')
        finally:
            machine.uc.context_restore(saved)
            machine.fs_head = fs
    if initial:
        for region, base in (('heap', 0x03000000), ('image', env.program.base), ('stack', STACK_BASE)):
            machine.write(base, env._initial[region])
    peer = None
    if not initial:
        peer = Machine(env.program, 0x03000000, env.heap_bytes)
        peer.on_external = env._external
        for address in env.fixtures:
            if env.program.in_text(address):
                peer.intercept(address)
        for base, length in ((0x03000000, env.heap_bytes), (env.program.data_start, env.program.base + env.program.size - env.program.data_start), (STACK_BASE, STACK_SIZE)):
            peer.write(base, machine.read(base, length))
        env.machine = peer
    env.backend = 'machine'
    try:
        result = env.machine.call_source(function, source, PCS[function], 'cdecl', 0, 0, arguments)
        if not result.completed:
            raise HarnessError('separate original producer failed to return')
    finally:
        if peer is not None:
            for base, length in ((0x03000000, env.heap_bytes), (env.program.data_start, env.program.base + env.program.size - env.program.data_start), (STACK_BASE, STACK_SIZE)):
                machine.write(base, peer.read(base, length))
            env.machine = machine
        if initial:
            for region, base, length in (('heap', 0x03000000, env.heap_bytes), ('image', env.program.base, env.program.size), ('stack', STACK_BASE, STACK_SIZE)):
                env._initial[region][:] = machine.read(base, length)
        machine.uc.context_restore(saved)
        machine.fs_head, env.backend = fs, backend


def setup_for(function, index, seed, recursion=0, race=False, fail=False, stop=None, filename=True):
    def setup(env):
        control = env.object(64, 'physical section owner', fill=0)
        log = env.object(2048, 'physical observations', fill=0)
        env.put(control, 1, 0, 0, 0)
        # All source sections reside in the actual image or live malloc spans.
        def record(e, call):
            n = e.get(control + 4)
            e.put(log + n * 16, call.function, call.arguments[0] if call.arguments else 0,
                  call.source_return_pc, e.get(control))
            e.put(control + 4, n + 1)
            if e.side != 'setup' and stop == (call.function, e.calls_so_far(call.function)):
                raise Halt()
        def initialize(e, call):
            record(e, call)
            p = call.arguments[0]
            if e.get(p) == 0x43524954:
                raise HarnessError('duplicate physical section initialization')
            e.put(p, 0x43524954, 0, 0, 0xffffffff, 0, 0x24681357)
        def enter(e, call):
            record(e, call)
            p, thread = call.arguments[0], e.get(control)
            if e.get(p) != 0x43524954 or e.get(p + 4) not in (0, thread):
                raise HarnessError('invalid physical enter')
            e.put(p + 4, thread, e.get(p + 8) + 1)
        def leave(e, call):
            record(e, call)
            p = call.arguments[0]
            if e.get(p) != 0x43524954 or e.get(p + 4) != e.get(control) or not e.get(p + 8):
                raise HarnessError('invalid physical leave')
            depth = e.get(p + 8) - 1
            e.put(p + 4, e.get(control) if depth else 0, depth)
        def malloc(e, call):
            record(e, call)
            if fail and e.side != 'setup':
                return 0
            p = e.object((call.arguments[0] + 15) & ~15, 'owned CRT allocation', fill=0xa7)
            count = e.get(control + 16)
            e.put(control + 20 + count * 4, p)
            e.put(control + 16, count + 1)
            # The other thread runs before this first allocation returns; it
            # publishes exclusively through the actual acquire instructions.
            if race and e.side != 'setup' and not e.get(control + 8):
                e.put(control + 8, 1)
                e.put(control, 2)
                try:
                    original(e, ACQUIRE, (index,))
                    original(e, RELEASE, (index,))
                finally:
                    e.put(control, 1)
            return p
        def free(e, call):
            record(e, call)
            p = call.arguments[0]
            if p:
                owned = [e.get(control + 20 + i * 4) for i in range(e.get(control + 16))]
                if p not in owned or p not in e.spans:
                    raise HarnessError('free requires a live base from this CRT memory owner')
                e.release(p)
        def get_filename(e, call):
            record(e, call)
            if not filename:
                return 0
            data = b'C:\\Games\\Claw\\CLAW.EXE\0'
            e.write(call.arguments[1], data[:call.arguments[2]])
            return len(data) - 1
        def load(e, call):
            record(e, call)
            return 0
        def filter_registration(e, call):
            record(e, call)
            old = e.get(control + 12)
            e.put(control + 12, call.arguments[0])
            return old
        def exit_process(e, call):
            record(e, call)
            raise Halt()
        for address, effect in ((0x546aa4, initialize), (0x546aac, enter), (0x546a9c, leave),
                                (0x4a48e0, malloc), (0x4a49b0, free), (0x5469f4, get_filename),
                                (0x546a14, load), (0x546980, filter_registration), (0x546998, exit_process)):
            env.override(address, effect)
        env.write(STACK_BASE, bytes(((seed + i * 17) & 255 for i in range(STACK_SIZE))))
        if function != INIT:
            original(env, INIT, initial=True)
            for _ in range(recursion + (function == RELEASE)):
                original(env, ACQUIRE, (index,), initial=True)
        env.put(control + 4, 0)
        env.write(log, bytes(2048))
        source = context(function, seed)
        if seed & 1:
            chain = 0x0200d000
            env.put(chain, chain + 8, 0x4ad7e0, 0xffffffff, 0x4ad7e0)
            source.fsHead = chain
        return {'source': source}
    return setup


def cases(random_source):
    def emit(label, function, index=13, **kw):
        seed = random_source.getrandbits(32)
        return Case(label, function, setup_for(function, index, seed, **kw),
                    arguments=() if function == INIT else (index,), source_context=lambda t: t['source'],
                    source_return_pc=PCS[function], expect='halt' if kw.get('stop') or kw.get('fail') else 'return')
    yield emit('actual static initialization order', INIT)
    for index in (1, 9, 13, 17):
        for depth in (0, 1, 3):
            yield emit(f'warm acquire {index} depth {depth}', ACQUIRE, index, recursion=depth)
            yield emit(f'release {index} depth {depth + 1}', RELEASE, index, recursion=depth)
    yield emit('genuine lazy index 2', ACQUIRE, 2)
    yield emit('genuine competing original producer', ACQUIRE, 2, race=True)
    yield emit('competing allocation free prefix', ACQUIRE, 2, race=True, stop=(0x4a49b0, 1))
    for i in range(1, 5):
        yield emit(f'initialize stop {i}', INIT, stop=(0x546aa4, i))
    for service, occurrence in ((0x4a48e0, 1), (0x546aac, 1), (0x546aa4, 1), (0x546a9c, 1), (0x546aac, 2)):
        yield emit(f'lazy prefix {service:x}/{occurrence}', ACQUIRE, 2, stop=(service, occurrence))
    yield emit('warm enter prefix', ACQUIRE, stop=(0x546aac, 1))
    yield emit('warm leave prefix', RELEASE, stop=(0x546a9c, 1))
    for filename in (True, False):
        yield emit(f'actual fatal exit filename {filename}', ACQUIRE, 2, fail=True, filename=filename)
        for service in (0x5469f4, 0x546a14, 0x546980):
            yield emit(f'fatal physical prefix {service:x} filename {filename}', ACQUIRE, 2,
                       fail=True, filename=filename, stop=(service, 1))
    for i in range(24):
        index = random_source.choice((1, 9, 13, 17, 2))
        yield emit(f'random source acquire {i} index {index}', ACQUIRE, index, recursion=random_source.randrange(4))
