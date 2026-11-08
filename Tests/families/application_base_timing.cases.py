"""Independent original-only cases for application base records and clocks."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext

CONSTRUCTOR = 0x4B8240
BIND = 0x4B8280
RESET = 0x4B83A0
GLOBALS = 0x4B83D0
CLOCK = 0x546DF0
RETURN_PC = {CONSTRUCTOR: 0x4254C4, BIND: 0x425766,
             RESET: 0x4B826A, GLOBALS: 0x4B8271}


def scenario(rng, label, function, ticks, flag=0, window="valid", hwnd=1,
             owner_zero=False, large=False, live_fs=False):
    # Freeze the randomized input here; fixture execution has no shared state.
    record = bytes(rng.randrange(1, 256) for _ in range(0x134 if large else 0x28))
    window_bytes = bytes(rng.randrange(1, 256) for _ in range(0x24))
    globals_before = [rng.getrandbits(32) | 1 for _ in range(7)]
    registers = [rng.getrandbits(32) for _ in range(7)]
    flags = 2 | (rng.getrandbits(32) & 0x8D5)
    unused = rng.getrandbits(32)
    stack_pointer = 0x02003000 + 4 * rng.randrange(0, 0x100)
    stack_bytes = bytes(rng.randrange(256) for _ in range(0x200))

    def setup(env):
        base = env.object(len(record), "base-record", data=record)
        outer = env.object(0x30, "window-outer-owner", fill=0x97)
        q = env.object(len(window_bytes), "window-structural-input", data=window_bytes)
        env.put(q + 4, 0 if window == "zero-hwnd" else hwnd)
        env.put(q + 8, 0 if owner_zero else outer)
        env.put(0x541324, *globals_before)
        env.write(stack_pointer - 0x100, stack_bytes)
        fs = 0xFFFFFFFF
        if live_fs:
            fs = stack_pointer - 0x80
            env.put(fs, 0xFFFFFFFF, 0x4254C4, unused)
        source = NativeSourceContext()
        source.size = 72
        source.version = 1
        source.inputMask = source.outputMask = 0x7FF
        for name, value in zip(("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"), registers):
            setattr(source, name, value)
        source.ecx = base
        source.esp = stack_pointer
        source.eip = function
        source.eflags = flags
        source.fsHead = fs

        def clock(env, call):
            # The physical clock alone returns timeline values. Source performs
            # all object/global publication, captured by normal event snapshots.
            index = env.calls_so_far(CLOCK) - 1
            return ticks[min(index, len(ticks) - 1)]

        env.override(CLOCK, clock)
        return dict(base=base, q=0 if window == "null" else q, source=source)

    args = ((lambda t: t["q"], unused) if function == BIND else
            (flag,) if function == RESET else ())
    return Case(label, function, setup, receiver=lambda t: t["base"],
                arguments=args, source_context=lambda t: t["source"],
                source_return_pc=RETURN_PC[function])


def cases(random_source):
    timelines = ((0, 0), (1, 2), (0xFFFFFFFE, 1),
                 (0xFFFFFFFF, 0), (0x80000000, 0x80000000),
                 (0x7FFFFFFF, 0x80000000))
    for index, ticks in enumerate(timelines):
        yield scenario(random_source, f"construct timeline {index}", CONSTRUCTOR,
                       ticks, large=index % 2 == 0, live_fs=index % 2 == 1)
        yield scenario(random_source, f"bind timeline {index}", BIND, ticks,
                       hwnd=(1, 0xFFFFFFFF, 0x80000000)[index % 3],
                       owner_zero=index == 1, large=index % 2 == 1,
                       live_fs=index % 2 == 0)
    for invalid in ("null", "zero-hwnd"):
        for index in range(4):
            yield scenario(random_source, f"bind {invalid} CPU witness {index}",
                           BIND, (0x76543210,), window=invalid,
                           live_fs=index % 2 == 0)
    for index, flag in enumerate((0, 1, 2, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF,
                                  0x100, 0x10000)):
        for tick in (0, 0xFFFFFFFF, 0x80000001):
            yield scenario(random_source, f"reset {flag:08x} tick {tick:08x}",
                           RESET, (tick,), flag=flag, live_fs=index % 2 == 1)
    for tick in (0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF):
        yield scenario(random_source, f"global clock {tick:08x}", GLOBALS,
                       (tick,), live_fs=tick % 2 == 0)
    for index in range(16):
        tick = random_source.getrandbits(32)
        delta = random_source.randrange(0, 10000)
        function = (CONSTRUCTOR, BIND, RESET, GLOBALS)[index % 4]
        yield scenario(random_source, f"random CPU and time {index}", function,
                       (tick, (tick + delta) & 0xFFFFFFFF),
                       flag=random_source.getrandbits(32) if index % 3 else 0,
                       hwnd=random_source.getrandbits(32) | 1,
                       large=True, live_fs=index % 2 == 0)
