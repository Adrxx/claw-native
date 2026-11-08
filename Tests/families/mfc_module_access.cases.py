"""Physical service models; every MFC constructor and throw remains original."""
from clawparity.cases import Case
from clawparity.fixtures import halt

GET = 0x50228F
ALLOC = 0x502F84
IMPORTS = (0x546A90, 0x546A7C, 0x546A84, 0x546AA4, 0x546AAC,
           0x546A9C, 0x546B1C, 0x546A8C, 0x5469C8, 0x546A88,
           0x5469C4, 0x546AA8, 0x546A80, 0x546958, 0x546ABC)


def physical(seed, *, warm=False, override=False, singleton=False,
             failure=None, version=10, tls_publish=True):
    def setup(env):
        # Persistent records hold service outputs, identities and observed frames.
        state = env.object(4096, "physical service state", fill=0)
        journal = env.object(16384, "physical event journal", fill=0)
        tls = state + 32
        globals_map = state + 256
        locals_map = state + 1280
        locks = state + 2304
        env.put(state, 0, 0, seed % 29 + 11)

        def record(env, call, result=0):
            n = env.get(state)
            slot = journal + n * 64
            env.put(slot, call.function, call.stack_pointer, call.receiver,
                    result, len(call.arguments), *call.arguments)
            env.put(slot + 40, env.get(0x53EC9C), env.get(0x53ECA0),
                    env.get(0x540AF0))
            env.put(state, n + 1)
            return result

        def local(env, call):
            flags, size = call.arguments
            count = env.get(state + 4) + 1
            env.put(state + 4, count)
            if failure == ("local", count):
                return record(env, call, 0)
            p = env.object(max(1, size), "physical local allocation", fill=0 if flags & 0x40 else (seed & 255) or 0xA7)
            env.put(locals_map + count * 12, p, size, flags)
            return record(env, call, p)

        def local_resize(env, call):
            old, size, flags = call.arguments
            if failure == "local-resize":
                return record(env, call, 0)
            old_size = next((env.get(locals_map + i * 12 + 4)
                             for i in range(1, env.get(state + 4) + 1)
                             if env.get(locals_map + i * 12) == old), 0)
            p = env.object(max(1, size), "resized physical local", fill=seed & 255)
            env.write(p, env.read(old, min(old_size, size)))
            env.release(old)
            count = env.get(state + 4) + 1
            env.put(state + 4, count)
            env.put(locals_map + count * 12, p, size, flags)
            return record(env, call, p)

        def global_alloc(env, call):
            flags, size = call.arguments
            if failure == "global":
                return record(env, call, 0)
            h = env.object(16, "physical movable handle", fill=0)
            p = env.object(max(1, size), "physical global data", fill=0xB7)
            n = env.get(state + 12)
            env.put(globals_map + n * 4, h)
            env.put(state + 12, n + 1)
            env.put(h, p, size, 0, flags)
            return record(env, call, h)

        def global_handle(env, call):
            p = call.arguments[0]
            h = next((env.get(globals_map + i * 4)
                      for i in range(env.get(state + 12))
                      if env.get(env.get(globals_map + i * 4)) == p), 0)
            return record(env, call, h)

        def global_lock(env, call):
            h = call.arguments[0]
            if not h:
                return record(env, call, 0)
            env.put(h + 8, env.get(h + 8) + 1)
            return record(env, call, env.get(h))

        def global_unlock(env, call):
            h = call.arguments[0]
            if h:
                env.put(h + 8, max(0, env.get(h + 8) - 1))
            return record(env, call, int(bool(h and env.get(h + 8))))

        def global_resize(env, call):
            h, size, flags = call.arguments
            if failure == "global-resize":
                return record(env, call, 0)
            p, old_size = env.get(h), env.get(h + 4)
            q = env.object(max(1, size), "moved physical global data", fill=0xC3)
            env.write(q, env.read(p, min(size, old_size)))
            env.release(p)
            env.put(h, q, size, env.get(h + 8), flags)
            return record(env, call, h)

        def tls_alloc(env, call):
            if failure == "tls":
                return record(env, call, 0xFFFFFFFF)
            idx = env.get(state + 8)
            env.put(state + 8, idx + 1)
            return record(env, call, idx)

        def tls_get(env, call):
            idx = call.arguments[0]
            return record(env, call, env.get(tls + idx * 4) if idx < 48 else 0)

        def tls_set(env, call):
            idx, p = call.arguments
            if tls_publish and idx < 48:
                env.put(tls + idx * 4, p)
            return record(env, call, int(tls_publish))

        def section(env, call):
            p = call.arguments[0]
            # Section identity and recursion are observable in the pointed OS record.
            if call.function == 0x546AA4:
                env.put(p, 0, 0, 0, 0, 0, 0)
            elif call.function == 0x546AAC:
                env.put(p, seed, env.get(p + 4) + 1)
            else:
                depth = max(0, env.get(p + 4) - 1)
                env.put(p, seed if depth else 0, depth)
            record(env, call)
            if failure == call.function:
                return halt()(env, call)
            return 0

        def raise_exception(env, call):
            record(env, call)
            env.write(journal + 16000, env.read(call.arguments[3], 12))
            return halt()(env, call)

        effects = (tls_alloc, tls_get, tls_set, section, section, section,
                   global_alloc, global_handle, global_unlock, global_resize,
                   global_lock, local, local_resize, raise_exception,
                   lambda e, c: record(e, c, version))
        for address, effect in zip(IMPORTS, effects):
            env.override(address, effect)

        if warm:
            # Explicit metadata input, not a claim about connected cold startup.
            idx = seed % 29 + 11
            manager = 0x540AF8
            container = env.object(16, "metadata TLS container", words=[0x511A64, 0, 3, 0])
            values = env.object(12, "metadata values", fill=0)
            thread = env.object(0x118, "metadata thread", fill=0x6D)
            env.put(thread, 0x5101EC, 0)
            module = env.object(0x1074, "metadata module override", fill=0x91)
            env.put(module, 0x51020C)
            if override:
                env.put(thread + 4, module)
            env.put(values + 4, thread)
            env.put(container + 12, values)
            env.put(manager, idx, 32, 2, 2, 0, container, 4)
            env.put(manager + 28, 0, 0, 0, 0, 0, 0)
            env.put(0x540AF0, manager)
            env.put(0x53EC9C, 1)
            env.put(tls + idx * 4, container)
            if singleton:
                env.put(0x53ECA0, module)
        return {"state": state, "journal": journal}
    return setup


def cases(random_source):
    for size in (0, 1, 2, 3, 7, 16, 255, 256, 4212, 16384):
        yield Case(f"checked local size {size}", ALLOC, physical(size + 61), arguments=(size,))
    for i in range(10):
        size = random_source.randrange(1, 24576)
        yield Case(f"random checked local {i}", ALLOC, physical(random_source.randrange(1, 100000)), arguments=(size,))
    yield Case("checked local fails through original throw", ALLOC,
               physical(71, failure=("local", 1)), arguments=(137,), expect="halt")
    for version in (10, 0x80000003, 0x80000004):
        yield Case(f"cold real constructors version {version:#x}", GET, physical(93, version=version))
    yield Case("cold publication service refuses TLS", GET, physical(89, tls_publish=False))
    for i in range(6):
        seed = random_source.randrange(1, 100000)
        yield Case(f"metadata existing thread override {i}", GET, physical(seed, warm=True, override=True))
        yield Case(f"metadata thread singleton fallback {i}", GET, physical(seed, warm=True, singleton=True))
        yield Case(f"metadata thread cold singleton constructor {i}", GET, physical(seed, warm=True))
    for failure in ("tls", "global", ("local", 1), ("local", 2), ("local", 3), ("local", 4), 0x546AA4, 0x546AAC):
        yield Case(f"cold physical failure {failure}", GET, physical(77, failure=failure), expect="halt")


# Optional ambient source mode. Existing ordinary cases above remain independent.
_ordinary_cases = cases
_CPU_FIELDS = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp',
               'esp', 'eip', 'eflags', 'fsHead')


def source_allocation(size, registers, frame, old_ebp, chain, fail, return_pc, pattern):
    def setup(env):
        from clawparity.env import NativeSourceContext

        # Pattern every byte of the bounded stack, not just the active frame.
        env.write(0x01FF0000, pattern * (0x20000 // len(pattern)))
        journal = env.object(512, 'source physical CPU journal', fill=0xAD)
        witness = env.object(64, 'source allocation ownership witness', fill=0x73)
        before = env.object(47, 'source preceding canary', fill=0xC5)
        fs_head = 0xFFFFFFFF
        if chain:
            tail = 0x01FF0020
            env.put(tail, 0xFFFFFFFF, 0x508525, 0xFFFFFFFF)
            middle = 0x01FF0040
            env.put(middle, tail, 0x508539, 0x12345678)
            fs_head = 0x01FF0060
            env.put(fs_head, middle, 0x508525, 0x87654321)
        source = NativeSourceContext(size=72, version=1, inputMask=0x7FF,
                                     outputMask=0x7FF, preserveMask=0x472,
                                     eax=registers[0], ebx=registers[1], ecx=registers[2],
                                     edx=registers[3], esi=registers[4], edi=registers[5],
                                     ebp=old_ebp, esp=frame, eip=ALLOC,
                                     eflags=registers[6], fsHead=fs_head)

        def record(e, call, slot):
            # Values are evidence for comparison, never fixture assertions.
            ctx = call.source_context
            e.put(journal + slot, call.function, call.stack_pointer,
                  call.source_return_pc, call.receiver, call.receiver2,
                  len(call.arguments), *call.arguments)
            e.put(journal + slot + 48, *(getattr(ctx, name) for name in _CPU_FIELDS))
            e.put(journal + slot + 96, *(getattr(ctx, name) for name in
                  ('size', 'version', 'inputMask', 'outputMask', 'preserveMask',
                   'reserved0', 'reserved1')))

        def local(e, call):
            record(e, call, 0)
            flags, requested = call.arguments
            if fail:
                e.put(witness, 0, requested, flags, before)
                return 0
            allocation = e.object(max(1, requested), 'source live aligned LocalAlloc',
                                  fill=0 if flags & 0x40 else 0xBC)
            after = e.object(53, 'source following canary', fill=0xE9)
            e.put(witness, allocation, requested, flags, before, after)
            return allocation

        def raise_exception(e, call):
            record(e, call, 160)
            e.write(journal + 320, e.read(call.arguments[3], 12))
            return halt()(e, call)

        env.override(0x546AA8, local)
        env.override(0x546958, raise_exception)
        return {'source': source}
    return Case(f'source allocation size={size:#x} frame={frame:#x} ebp={old_ebp:#x} '
                f'FS={int(chain)} failure={int(fail)} pc={return_pc:#x} regs={registers}',
                ALLOC, setup, arguments=(size,),
                source_context=lambda tokens: tokens['source'], source_return_pc=return_pc,
                expect='halt' if fail else 'return')


def cases(random_source):
    yield from _ordinary_cases(random_source)
    # Read original bytes only through the hash-checking program loader.
    from clawparity.program import claw
    program = claw()
    def original_bytes(address, count):
        section = next(s for s in program.sections
                       if s.address <= address and address + count <= s.address + len(s.data))
        return section.data[address - section.address:address - section.address + count]
    # Both continuations follow actual CALL 502f84 in the pinned factories.
    assert original_bytes(0x502345, 5) == bytes.fromhex('e83a0c0000')
    assert original_bytes(0x50237A, 5) == bytes.fromhex('e8050c0000')

    patterns = (bytes(range(256)), bytes(reversed(range(256))))
    raw = ((0, 1, 0xFFFFFFFF, 0x80000000, 0x13579BDF, 0x2468ACE0, 0x2),
           (0xFFFFFFFF, 0x80000001, 0xA55AA55A, 0xDEADBEEF, 0, 1, 0x8D7))
    ebps = (0, 1, 0xFFFFFFFF, 0x12345679, 0x02008000, 0x01FF0103, 0x0200FF11)
    frames = (0x01FF0100, 0x02008000, 0x0200FF80)
    for i, ebp in enumerate(ebps):
        for j, frame in enumerate(frames):
            for chain in (False, True):
                for fail in (False, True):
                    size = (0, 1, 3, 0x118, 0x1074, 0x3FFF, 0x6000)[i]
                    yield source_allocation(size, raw[(i+j) % 2], frame, ebp, chain,
                                            fail, (0x50234A, 0x50237F)[j % 2], patterns[i % 2])
    for i, size in enumerate((0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF)):
        yield source_allocation(size, raw[i % 2], frames[i % 3], ebps[i], bool(i % 2),
                                True, (0x50234A, 0x50237F)[i % 2], patterns[i % 2])
    for i in range(32):
        registers = tuple(random_source.getrandbits(32) for _ in range(6)) + (
            0x2 | (random_source.getrandbits(12) & 0x8D5),)
        fail = bool(i % 2)
        size = random_source.getrandbits(32) if fail else random_source.randrange(0, 24577)
        frame = (random_source.randrange(0x01FF0100, 0x0200FFC0) & ~3)
        yield source_allocation(size, registers, frame, random_source.getrandbits(32),
                                bool(i % 3), fail, (0x50234A, 0x50237F)[i % 2],
                                bytes(random_source.randrange(256) for _ in range(256)))


# Blind getter extension; the complete preceding corpus remains intact.
_previous_cases = cases


def source_getter(seed, mode, frame, registers, ebp, flags, pc, pattern, chain,
                  value=0, alias=0):
    def setup(env):
        from clawparity.env import NativeSourceContext
        env.write(0x01FF0000, pattern * (0x20000 // len(pattern)))
        warm = mode != 'cold' and mode != 'thread-failure'
        failure = ('local', 1) if mode in ('thread-failure', 'module-failure') else None
        tokens = physical(seed, warm=warm, singleton=mode not in
                          ('cold', 'thread-failure', 'module-failure', 'warm-cold', 'new-slot'),
                          failure=failure)(env)
        state = tokens['state']
        journal = env.object(16384, 'getter full physical CPU witnesses', fill=0xD3)
        counter = env.object(4, 'getter witness count', fill=0)
        idx = seed % 29 + 11
        container = env.get(state + 32 + idx * 4) if warm else 0
        values = env.get(container + 12) if container else 0
        thread = env.get(values + 4) if values else 0
        if mode == 'new-slot':
            env.put(values + 4, 0)
        elif mode == 'override':
            env.put(thread + 4, value)
        elif mode == 'alias':
            env.put(values + 4, frame + alias)
        # The service legally chooses a different logical thread's container.
        alternate = 0
        if mode == 'alternate-thread':
            alternate = env.object(16, 'second logical thread container',
                                   words=[0x511A64, 0, 3, 0])
            alternate_values = env.object(12, 'second logical thread values', fill=0)
            alternate_thread = env.object(0x118, 'second logical thread record', fill=0x87)
            env.put(alternate_thread, 0x5101EC, value)
            env.put(alternate_values + 4, alternate_thread)
            env.put(alternate + 12, alternate_values)
        # Record the original physical import state without fixture assertions.
        # Reuse the existing physical effect through its registered callable.
        for address in IMPORTS:
            effect = env._case_overrides[address]
            def observed(e, call, original=effect):
                n = e.get(counter)
                slot = journal + n * 256
                ctx = call.source_context
                e.put(slot, call.function, call.stack_pointer, call.source_return_pc,
                      call.receiver, len(call.arguments), *call.arguments)
                e.put(slot + 64, *(getattr(ctx, name) for name in _CPU_FIELDS))
                e.write(slot + 112, e.read(frame - 32, 48))
                e.put(counter, n + 1)
                if call.function == 0x546A7C and mode == 'reload':
                    e.put(thread + 4, value)
                result = original(e, call)
                if call.function == 0x546A7C and alternate:
                    result = alternate
                e.put(slot + 160, result)
                return result
            env.override(address, observed)
        head = 0xFFFFFFFF
        if chain:
            head = 0x0200FFB0
            env.put(head, 0xFFFFFFFF, 0x508525, 0xFFFFFFFF)
        source = NativeSourceContext(size=72, version=1, inputMask=0x7FF,
                                     outputMask=0x7FF, preserveMask=0x400,
                                     eax=registers[0], ebx=registers[1], ecx=registers[2],
                                     edx=registers[3], esi=registers[4], edi=registers[5],
                                     ebp=ebp, esp=frame, eip=GET, eflags=flags, fsHead=head)
        return {'source': source}
    return Case(f'getter source {mode} seed={seed} F={frame:#x} PC={pc:#x} '
                f'value={value:#x} alias={alias} flags={flags:#x} EBP={ebp:#x}',
                GET, setup, source_context=lambda t: t['source'], source_return_pc=pc,
                expect='halt' if mode in ('thread-failure', 'module-failure') else 'return')


def cases(random_source):
    yield from _previous_cases(random_source)
    from clawparity.program import claw
    program = claw()
    def original_bytes(address, count):
        section = next(s for s in program.sections
                       if s.address <= address and address + count <= s.address + len(s.data))
        return section.data[address - section.address:address - section.address + count]
    for address, raw in ((0x5022B5, 'e8d5ffffff'), (0x4A176D, 'e81d0b0600'),
                         (0x4F6B21, 'e869b70000')):
        assert original_bytes(address, 5) == bytes.fromhex(raw)
    modes = ('cold', 'warm-cold', 'warm', 'override', 'alias', 'new-slot',
             'reload', 'alternate-thread', 'thread-failure', 'module-failure')
    values = (1, 2, 3, 0x80, 0x80000000, 0xFFFFFFFF, 0x80000001, 0x7FFFFFFF)
    for i in range(100):
        mode = modes[i % len(modes)]
        registers = tuple(random_source.getrandbits(32) for _ in range(6))
        frame = (0x01FF1800, 0x02007C00, 0x0200FC00)[i % 3]
        pattern = bytes(random_source.randrange(256) for _ in range(256))
        yield source_getter(random_source.randrange(1, 100000), mode, frame,
                            registers, (0, 0xFFFFFFFF, random_source.getrandbits(32))[i % 3],
                            2 | (random_source.getrandbits(12) & 0x8D5),
                            (0x5022BA, 0x4A1772, 0x4F6B26)[i % 3], pattern, bool(i % 2),
                            values[(i // 10) % len(values)], (-8, -12, -16)[(i // 10) % 3])
    # Reload zero must choose the cached singleton, while nearby nonzero words
    # choose the override and exercise TEST's signed/parity/zero boundaries.
    for i, value in enumerate((0, 1, 2, 3, 0x80, 0x80000000, 0xFFFFFFFF)):
        yield source_getter(291 + i, 'reload', 0x02007C00,
                            tuple(random_source.getrandbits(32) for _ in range(6)),
                            0xFFFFFFFF, (2, 0x8D7)[i % 2],
                            (0x5022BA, 0x4A1772, 0x4F6B26)[i % 3],
                            bytes(random_source.randrange(256) for _ in range(256)),
                            bool(i % 2), value)
