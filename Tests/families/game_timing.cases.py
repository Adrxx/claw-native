"""Original-derived clock, countdown, pacing and reporting cases."""
from clawparity.cases import Case

UPDATE = 0x4B82F0
WAIT = 0x4B83F0
CLOCK = 0x546DF0
CURRENT = 0x541328
MASK = 0xFFFFFFFF


def timing_setup(words, globals_, timeline):
    """A physical clock script; observations never change timing state."""
    def setup(env):
        target = env.object(0x40, "timing receiver and sentinels", words=words)
        # Keep every initial field distinct, including globals overwritten by update.
        env.put(CURRENT, *globals_)
        stride = 4 + 0x40 + 20
        observations = env.object(4 + 64 * stride, "clock observations", fill=0)

        def clock(env, call):
            index = env.calls_so_far(call.function) - 1
            env.put(observations, index + 1)
            if index < 64:
                record = observations + 4 + index * stride
                env.put(record, len(call.arguments))
                env.write(record + 4, env.read(target, 0x40))
                env.write(record + 4 + 0x40, env.read(CURRENT, 20))
            return timeline[min(index, len(timeline) - 1)]

        env.override(CLOCK, clock)
        return target

    return setup


def update(label, random_source, *, old=1000, now=1017, countdown=37,
           reload=91, pacing=0, start=0x31415926, minimum=16,
           count=17, age=1999, timeline=None):
    words = [random_source.getrandbits(32) for _ in range(16)]
    words[6:11] = [0xD3517A29, pacing & MASK, count,
                    (now - age) & MASK, minimum]
    globals_ = [old, 0xAE732618, start, countdown, reload]
    script = [now] if timeline is None else timeline
    return Case(label, UPDATE, timing_setup(words, globals_, script),
                receiver=lambda target: target)


def wait(label, random_source, duration, timeline):
    words = [random_source.getrandbits(32) for _ in range(16)]
    globals_ = [random_source.getrandbits(32) for _ in range(5)]
    return Case(label, WAIT, timing_setup(words, globals_, timeline),
                arguments=(duration,))


def cases(random_source):
    # Saturation, equality, and reload are independent of reporting and pacing.
    for delta in (0, 1, 17, 0x7FFFFFFF, 0x80000000, MASK):
        now = (0xFFFFFFF8 + delta) & MASK
        for countdown in (0, 1, 17, 0x80000000, MASK):
            yield update(f"countdown {countdown:#x}, delta {delta:#x}",
                         random_source, old=0xFFFFFFF8, now=now,
                         countdown=countdown, reload=0xF0E1D2C3,
                         age=73)
    for reload in (0, 1, 0x80000000, MASK):
        yield update(f"zero countdown reload {reload:#x}", random_source,
                     countdown=0, reload=reload)

    # Only signed-positive enable words permit any pacing clock reads.
    for enable in (0, MASK, 0x80000000, 0x80000001, 0x7FFFFFFF, 1, 2):
        timeline = [1017, 0x456789AB] if 0 < enable < 0x80000000 else [1017]
        yield update(f"signed pacing enable {enable:#x}", random_source,
                     pacing=enable, start=0, timeline=timeline)
    for start, sample, minimum in (
        (1000, 1000, 0), (1000, 1016, 16), (1000, 1017, 16),
        (0xFFFFFFF8, 8, 16), (0x80000000, 0x80000010, 16),
        (MASK, 0, 1), (1, 0x80000001, 0x80000000),
        (1, 0, 16), (MASK, 0x7FFFFFFE, 0x7FFFFFFF),
    ):
        yield update(f"pacing elapsed {start:#x}->{sample:#x}, minimum {minimum:#x}",
                     random_source, pacing=1, start=start, minimum=minimum,
                     timeline=[1017, sample, 0x6789ABCD])

    # Exercise the nested owned wait with zero/equality polling and wrapped deadline.
    for start, elapsed_sample, minimum, wait_samples in (
        (1000, 1005, 16, [1010, 1010, 1020, 1021, 1022]),
        (1000, 1000, 1, [1000, 1001, 1001, 1002]),
        (0xFFFFFFF8, 0, 16, [MASK - 3]),
        (0x80000000, 0x80000001, 0x80000000, [0x90000000]),
        (1, 1, MASK, [7]),
    ):
        yield update(f"paced wait {start:#x}, minimum {minimum:#x}", random_source,
                     pacing=1, start=start, minimum=minimum,
                     timeline=[1017, elapsed_sample, *wait_samples, 0xA1234567])

    # Distinguish logical shift after modulo increment from widened or signed math.
    for now in (0, 37, 0x80000000, MASK):
        for age in (1999, 2000, 2001, 0x80000000, MASK):
            count = (0, 1, 0x7FFFFFFF, 0xFFFFFFFE, MASK)[
                (now + age) % 5]
            yield update(f"report at {now:#x}, age {age:#x}, count {count:#x}",
                         random_source, now=now, count=count, age=age,
                         timeline=[now, 0xABCDEF23])
    for count in (0, 1, 2, 3, 0x7FFFFFFE, 0x7FFFFFFF, 0x80000000,
                  0xFFFFFFFE, MASK):
        yield update(f"report count boundary {count:#x}", random_source,
                     count=count, age=2000, timeline=[1017, 0x87654321])
    # Pacing publication is visible at reset-rate's additional clock call.
    yield update("paced wait then reporting reset", random_source,
                 pacing=1, start=1000, minimum=20, count=MASK, age=2000,
                 timeline=[1017, 1010, 1011, 1021, 1022, 1023, 1099])

    for duration, timeline in (
        (0, [0, 0, 0, 1]),
        (0, [0x80000000, 0x80000000, 0x80000001]),
        (1, [100, 100, 101, 101, 102]),
        (17, [100, 101, 116, 117, 117, 118]),
        (0x80000000, [0, 0x7FFFFFFF, 0x80000000, 0x80000001]),
        (0xFFFFFFFE, [0, 0x80000000, 0xFFFFFFFE, MASK]),
        (32, [0xFFFFFFF0]),
        (MASK, [1]),
        (0x80000000, [0x80000000]),
    ):
        yield wait(f"wait duration {duration:#x} clock {timeline[0]:#x}",
                   random_source, duration, timeline)

    for index in range(32):
        now = random_source.getrandbits(32)
        delta = random_source.getrandbits(32)
        count = random_source.getrandbits(32)
        countdown = random_source.choice((0, delta, random_source.getrandbits(32)))
        age = random_source.choice((1999, 2000, 2001, random_source.getrandbits(32)))
        yield update(f"random countdown and report {index}", random_source,
                     old=(now - delta) & MASK, now=now, countdown=countdown,
                     reload=random_source.getrandbits(32), count=count, age=age,
                     pacing=random_source.choice((0, MASK, 0x80000000)),
                     timeline=[now, random_source.getrandbits(32)])

        start = random_source.randrange(1, 0x7FFF0000)
        elapsed = random_source.randrange(0, 100)
        minimum = elapsed + random_source.randrange(1, 100)
        first_wait = start + elapsed + random_source.randrange(0, 10)
        deadline = first_wait + minimum - elapsed
        final_start = deadline + random_source.randrange(2, 100)
        yield update(f"random positive pacing {index}", random_source,
                     now=now, pacing=random_source.randrange(1, 0x80000000),
                     start=start, minimum=minimum, count=count, age=age,
                     timeline=[now, start + elapsed, first_wait,
                               deadline - 1, deadline, deadline + 1, final_start,
                               random_source.getrandbits(32)])

        duration = random_source.randrange(0, 0x10000)
        first = random_source.randrange(0, 0xFFFE0000)
        deadline = first + duration
        yield wait(f"random direct polling {index}", random_source, duration,
                   [first, first, deadline, deadline,
                    deadline + random_source.randrange(1, 100)])
