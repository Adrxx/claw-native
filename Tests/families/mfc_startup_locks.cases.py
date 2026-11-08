"""Physical version/critical-section models for the original startup locks."""
from clawparity.cases import Case
from clawparity.fixtures import halt

INIT, ACQUIRE, RELEASE = 0x502E47, 0x502E95, 0x502F05
INITIALIZED, DISABLED, MASTER, FLAGS, SECTIONS = 0x5408E8, 0x540A88, 0x540A90, 0x540AA8, 0x5408F0
VERSION, INITIALIZE, ENTER, LEAVE = 0x546ABC, 0x546AA4, 0x546AAC, 0x546A9C
MAGIC, OWNER = 0x43534543, 0x1379


def physical_setup(version, initialized, disabled, index, ready, depth, noise,
                   interleave=False, stop=None):
    def setup(env):
        env.put(INITIALIZED, initialized)
        env.put(DISABLED, disabled)
        # Distinct backed neighbor flags and records expose wrong index/width.
        for i in range(17):
            env.put(FLAGS + 4 * i, noise[i] | 1)
            env.put(SECTIONS + 24 * i, MAGIC, 0, 0, SECTIONS + 24 * i,
                    noise[i], noise[i] ^ 0xFFFFFFFF)
        env.put(MASTER, MAGIC if initialized else noise[17], 0, 0,
                MASTER, noise[17], noise[17] ^ 0xFFFFFFFF)
        env.put(FLAGS + 4 * index, ready)
        section = SECTIONS + index * 24
        if not ready:
            env.put(section, noise[index], noise[index] ^ 0x2468ACE0,
                    noise[index] ^ 0x13579BDF, section, noise[index],
                    noise[index] ^ 0xFFFFFFFF)
        else:
            env.put(section + 4, depth, OWNER if depth else 0)
        trace = env.object(1024, "physical service observations", fill=0)

        def record(e, call, kind, ptr=0):
            n = e.get(trace)
            e.put(trace, n + 1)
            e.put(trace + 4 + n * 48, kind, call.receiver, ptr,
                  e.get(INITIALIZED), e.get(DISABLED),
                  e.get(FLAGS + index * 4), e.get(MASTER), e.get(MASTER + 4),
                  e.get(ptr) if ptr else 0, e.get(ptr + 4) if ptr else 0,
                  e.get(ptr + 8) if ptr else 0, len(call.arguments))

        def version_call(e, call):
            record(e, call, 1)
            if stop == "version":
                return halt()(e, call)
            return version

        def initialize(e, call):
            ptr = call.arguments[0]
            record(e, call, 2, ptr)
            if stop == ("init-master" if ptr == MASTER else "init-numbered"):
                return halt()(e, call)
            e.put(ptr, MAGIC, 0, 0, ptr, 0xABCD0123, 0x9876FEDC)
            return noise[18]

        def enter(e, call):
            ptr = call.arguments[0]
            record(e, call, 3, ptr)
            if stop == ("enter-master" if ptr == MASTER else "enter-numbered"):
                return halt()(e, call)
            if interleave and ptr == MASTER:
                # Another thread completed initialization before this wait ended.
                e.put(section, MAGIC, 0, 0, section, 0xABCD0123, 0x9876FEDC)
                e.put(FLAGS + 4 * index, ready or 7)
            valid = e.get(ptr) == MAGIC and e.get(ptr + 8) in (0, OWNER)
            e.put(ptr + 4, (e.get(ptr + 4) + 1) & 0xFFFFFFFF)
            e.put(ptr + 8, OWNER if valid else 0xBAD00001)
            return noise[19]

        def leave(e, call):
            ptr = call.arguments[0]
            record(e, call, 4, ptr)
            if stop == ("leave-master" if ptr == MASTER else "leave-numbered"):
                return halt()(e, call)
            old = e.get(ptr + 4)
            valid = e.get(ptr) == MAGIC and old != 0 and e.get(ptr + 8) == OWNER
            new = (old - 1) & 0xFFFFFFFF
            e.put(ptr + 4, new)
            e.put(ptr + 8, (OWNER if new else 0) if valid else 0xBAD00002)
            return noise[20]

        for address, effect in ((VERSION, version_call), (INITIALIZE, initialize),
                                (ENTER, enter), (LEAVE, leave)):
            env.override(address, effect)
        return {}
    return setup


def ordinary_cases(random_source):
    noise = [random_source.getrandbits(32) for _ in range(21)]
    def case(label, function, *, version=4, initialized=1, disabled=0,
             index=0, ready=0, depth=0, interleave=False, stop=None):
        return Case(label, function,
                    physical_setup(version, initialized, disabled, index, ready,
                                   depth, noise, interleave, stop),
                    arguments=() if function == INIT else (index,),
                    expect="halt" if stop else "return")

    for version in (3, 4, 0x80000003, 0x80000004, 10, 0, 255,
                    0x80000000, 0x800000FF):
        yield case(f"cold version {version:08x}", INIT, version=version,
                   initialized=0, disabled=noise[0])
    for _ in range(8):
        version = random_source.getrandbits(32)
        yield case(f"random cold version {version:08x}", INIT, version=version,
                   initialized=0, disabled=noise[1])
    for initialized in (1, 7, 0x80000000, 0xFFFFFFFF):
        for disabled in (0, 1, noise[2] | 1):
            yield case(f"warm init {initialized:x} disabled {disabled:x}", INIT,
                       initialized=initialized, disabled=disabled)
    for index in range(17):
        yield case(f"new numbered section {index}", ACQUIRE, index=index)
        yield case(f"ready numbered section {index} recursive", ACQUIRE,
                   index=index, ready=noise[index] | 1, depth=2)
        yield case(f"physical interleaving section {index}", ACQUIRE,
                   index=index, interleave=True)
        for depth in (1, 3):
            yield case(f"release section {index} depth {depth}", RELEASE,
                       index=index, ready=1, depth=depth)
    for version in (3, 4, 0x80000003, 0x80000004):
        yield case(f"cold acquire version {version:08x}", ACQUIRE,
                   version=version, initialized=0, index=random_source.randrange(17))
    for function in (ACQUIRE, RELEASE):
        yield case(f"disabled {function:x}", function, disabled=noise[3] | 1,
                   index=16, ready=1, depth=1)
    for stop in ("version", "init-master"):
        yield case(f"cold initializer physical stop {stop}", INIT,
                   initialized=0, stop=stop)
        yield case(f"cold acquire physical stop {stop}", ACQUIRE,
                   initialized=0, index=16, stop=stop)
    for stop in ("enter-master", "init-numbered", "leave-master", "enter-numbered"):
        yield case(f"physical acquire stop {stop}", ACQUIRE, index=16, stop=stop)
    yield case("physical release stop while held", RELEASE, index=16,
               ready=1, depth=2, stop="leave-numbered")


# The source cases are independent of the translation: these are observations
# of genuine original instructions and synchronous physical service effects.
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, CONTEXT_FIELDS


def source_case(random_source, label, function, *, version=4, initialized=1,
                disabled=0, index=0, ready=0, mutation=None, stop=None,
                opaque_ebp=None, fs_alias=False):
    cpu_words = [random_source.getrandbits(32) for _ in range(7)]
    flags = (random_source.getrandbits(32) & 0x8D5) | 2
    frame = STACK_BASE + 0x10000 + 4 * random_source.randrange(1024)
    fs = frame + 0x200 if fs_alias else STACK_BASE + 0x400
    pattern = bytes(random_source.getrandbits(8) for _ in range(256))
    noises = [random_source.getrandbits(32) for _ in range(32)]
    if opaque_ebp is not None:
        cpu_words[6] = opaque_ebp
    # Register values can point into genuine guest saved-frame slots without
    # extending authority beyond the mapped stack backing.
    if mutation == "saved-alias":
        cpu_words[2:6] = [frame - 4, frame - 8, frame - 12, frame - 16]
    return_pc = {INIT: 0x502EA8, ACQUIRE: 0x503444, RELEASE: 0x503478}[function]

    def setup(env):
        env.write(STACK_BASE, pattern * (STACK_SIZE // len(pattern)))
        env.put(fs, 0xFFFFFFFF, 0x503454, 0)
        source = NativeSourceContext(72, 1, 0x7FF, 0x7FF, *cpu_words,
                                     frame, function, flags, fs, 0, 0, 0)
        env.put(frame, return_pc)
        if function != INIT:
            env.put(frame + 4, index)
        env.put(INITIALIZED, initialized)
        env.put(DISABLED, disabled)
        section = (SECTIONS + 24 * index) & 0xFFFFFFFF
        flag = (FLAGS + 4 * index) & 0xFFFFFFFF
        for i in range(17):
            ptr = SECTIONS + 24 * i
            env.put(ptr, MAGIC, 2, OWNER, ptr, noises[i], ~noises[i] & 0xFFFFFFFF)
            env.put(FLAGS + 4 * i, noises[i] | 1)
        env.put(MASTER, MAGIC, 0, 0, MASTER, noises[17], noises[18])
        # For wrapping indices 0x40000000+n, both multiplied spans map back
        # to the same original globals. Additional indices use backed image.
        if function != INIT and not disabled:
            env.put(section, MAGIC if ready else noises[19], 2 if ready else 0,
                    OWNER if ready else 0, section, noises[20], noises[21])
            env.put(flag, ready)
        trace = env.object(4096, "source physical CPU and frame observations", fill=0)

        def record(e, call, kind, ptr):
            n = e.get(trace)
            base = trace + 4 + n * 256
            e.put(trace, n + 1)
            ctx = call.source_context
            e.put(base, kind, call.function, call.receiver, call.receiver2,
                  call.stack_pointer, call.source_return_pc, len(call.arguments), ptr)
            # No fixture assertions: differences remain visible observations.
            e.put(base + 32, *(getattr(ctx, name) for name in CONTEXT_FIELDS))
            e.put(base + 76, e.get(call.stack_pointer),
                  e.get(INITIALIZED), e.get(DISABLED),
                  e.get(flag) if function != INIT and not disabled else 0,
                  e.get(ENTER), e.get(INITIALIZE), e.get(LEAVE))
            e.write(base + 104, e.read(call.stack_pointer - 16, 96))
            if ptr:
                e.write(base + 200, e.read(ptr, 24))

        def service(kind):
            def effect(e, call):
                ptr = call.arguments[0] if call.arguments else 0
                record(e, call, kind, ptr)
                site = ({0x502E60: "version", 0x502E8E: "init-master",
                         0x502ED2: "enter-master", 0x502EE8: "init-numbered",
                         0x502EF1: "leave-master", 0x502EFE: "enter-numbered",
                         0x502F23: "leave-numbered"}.get(call.source_return_pc))
                if stop == site:
                    return halt()(e, call)
                if mutation == "initialized-reload" and kind in (1, 2):
                    e.put(INITIALIZED, noises[22] | 0x100)
                if mutation == "argument-reload" and kind == 1:
                    e.put(frame + 4, 1)
                if mutation == "interleave" and site == "enter-master":
                    e.put(flag, 7)
                    e.put(section, MAGIC, 0, 0, section, noises[23], noises[24])
                if mutation == "cached-enter" and site == "enter-master":
                    # A different authentic import token remains valid; EBX
                    # must still call its previously loaded Enter identity.
                    e.put(ENTER, e.get(LEAVE))
                if kind == 2:
                    e.put(ptr, MAGIC, 0, 0, ptr, noises[25], noises[26])
                    if site == "init-numbered" and mutation in ("inc-wrap", "inc-high", "inc-one"):
                        e.put(flag, {"inc-wrap": 0xFFFFFFFF, "inc-high": 0x7FFFFFFF,
                                     "inc-one": 0x12345678}[mutation])
                if kind == 3:
                    e.put(ptr + 4, (e.get(ptr + 4) + 1) & 0xFFFFFFFF)
                    e.put(ptr + 8, OWNER)
                if kind == 4:
                    e.put(ptr + 4, (e.get(ptr + 4) - 1) & 0xFFFFFFFF)
                if mutation == "saved-alias" and site == "enter-numbered":
                    e.put(frame - 16, noises[27], noises[28], noises[29], noises[30])
                if mutation == "saved-init" and kind == 1:
                    # Physical call entry is T-8: its caller's saved ESI is T-4.
                    e.put(call.stack_pointer + 4, noises[31])
                return version if kind == 1 else noises[16 + kind]
            return effect

        for address, kind in ((VERSION, 1), (INITIALIZE, 2), (ENTER, 3), (LEAVE, 4)):
            env.override(address, service(kind))
        return {"source": source}

    return Case("source " + label, function, setup,
                arguments=() if function == INIT else (index,),
                source_context=lambda tokens: tokens["source"],
                source_return_pc=return_pc, expect="halt" if stop else "return")


def cases(random_source):
    yield from ordinary_cases(random_source)
    for version in (0, 1, 3, 4, 255, 0x80000000, 0x80000003,
                    0x80000004, 0x800000FF, 0xFFFFFF03, 0xFFFFFF04):
        for function in (INIT, ACQUIRE):
            yield source_case(random_source, f"cold {function:x} version {version:08x}",
                              function, version=version, initialized=0,
                              disabled=random_source.getrandbits(32), index=16,
                              opaque_ebp=0 if version & 1 else 0xFFFFFFFF)
    for initialized in (1, 7, 0x80000000, 0xFFFFFFFF):
        for disabled in (0, 1, 0x80000000, 0xFFFFFFFF):
            yield source_case(random_source, f"warm init {initialized:x}/{disabled:x}",
                              INIT, initialized=initialized, disabled=disabled)
    for function in (ACQUIRE, RELEASE):
        for index in (0, 16, 0xFFFFFFFF, 0x80000000):
            yield source_case(random_source, f"disabled opaque {function:x}/{index:x}",
                              function, disabled=0x80000001, index=index)
    for index in (0, 16, 32, 0x40000000, 0x80000001, 0xC0000010):
        for ready in (0, 1, 0xFFFFFFFF):
            yield source_case(random_source, f"acquire mapped modulo index {index:x}/{ready:x}",
                              ACQUIRE, index=index, ready=ready)
        yield source_case(random_source, f"release mapped modulo index {index:x}",
                          RELEASE, index=index, ready=1)
    for mutation in ("interleave", "inc-wrap", "inc-high", "inc-one",
                     "cached-enter", "saved-alias"):
        for index in (0, 16):
            yield source_case(random_source, f"{mutation} section {index}", ACQUIRE,
                              index=index, mutation=mutation, fs_alias=True)
    for function in (INIT, ACQUIRE):
        for mutation in ("initialized-reload", "saved-init"):
            yield source_case(random_source, f"cold {function:x} {mutation}", function,
                              initialized=0, mutation=mutation)
    yield source_case(random_source, "argument reloaded after owned initialization", ACQUIRE,
                      initialized=0, mutation="argument-reload")
    for function, stops in ((INIT, ("version", "init-master")),
                            (ACQUIRE, ("version", "init-master", "enter-master",
                                       "init-numbered", "leave-master", "enter-numbered")),
                            (RELEASE, ("leave-numbered",))):
        for stop in stops:
            yield source_case(random_source, f"physical halt {function:x} {stop}", function,
                              initialized=0 if stop in ("version", "init-master") else 1,
                              index=16, ready=1 if function == RELEASE else 0,
                              stop=stop, fs_alias=True)
    for i in range(12):
        function = (INIT, ACQUIRE, RELEASE)[i % 3]
        yield source_case(random_source, f"random full CPU {i}", function,
                          version=random_source.getrandbits(32),
                          initialized=i & 1, index=random_source.randrange(17),
                          ready=random_source.getrandbits(32) if i & 1 else 0)
