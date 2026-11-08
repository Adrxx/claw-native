"""Cases for level_one_batch_glitter_01: Level 1 glitter mother and baby logic."""
from clawparity.cases import Case
from clawparity.fixtures import sequence

MOTHER = 0x448440
SPARKLE = 0x4485A0
RAND = 0x4A3050
GLOBAL_ENV = 0x5371FC  # pointer whose target holds a flag at +0x124
GLOBAL_STEP = 0x5430C4  # animation step passed to the animation advance

STR_BABY = b"GlitterBaby\0"
STR_SPARKLE = b"GAME_SPARKLE\0"
STR_GLITTER = b"GAME_GLITTER1\0"


def bucket_of(key, count):
    value = 0
    for byte in key.rstrip(b"\0"):
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & 0xFFFFFFFF
    return value % count


def hash_map(env, base, entries, count=7):
    """Fill the string-keyed map embedded at `base` (buckets pointer at +4, bucket count at +8).
    entries: list of (key bytes, value). Same-bucket keys chain, newest first."""
    buckets = env.object(4 * count, "buckets", fill=0)
    for key, value in entries:
        slot = bucket_of(key, count)
        text = env.object(len(key), "key", data=key)
        node = env.object(16, "node", fill=0)
        env.put(node, env.get(buckets + 4 * slot), 0, text, value)
        env.put(buckets + 4 * slot, node)
    env.put(base + 4, buckets, count)


def animation(env, first, last, size=0x180):
    """An animation record: first frame at +100, last at +0x68, frame table pointer at +0x14."""
    table = env.object(4 * (last + 2 if last >= 0 else 1) + 4, "frames", words=[0xA0000 + i * 0x111 for i in range(last + 3 if last >= 0 else 1)])
    record = env.object(size, "animation", fill=0)
    env.put(record + 0x14, table)
    env.put(record + 100, first)
    env.put(record + 0x68, last)
    return record


def frame_set(env, count, elements=1):
    """A frame set for the animation player: count at +0x10, element table pointer at +0xc."""
    items = [env.object(0x40, "element", words=[0x11 * (i + 1) + 3 * j for j in range(16)]) for i in range(max(elements, 1))]
    table = env.object(4 * len(items), "elements", words=items)
    record = env.object(0x40, "frameset", fill=0)
    env.put(record + 0x0C, table)
    env.put(record + 0x10, count)
    return record


def sparkle_setup(state, *, sparkle=True, glitter=True, anim_range=(3, 9), counter=0, flag=0, running=0, step=1,
                  stepping=0, animset=True, a_flags=0, extra_maps=True, count_a=7, count_b=5, count_c=11, set_count=2):
    def setup(env):
        actor = env.object(0x200, "actor", fill=0)
        state_obj = env.object(0x40, "state", fill=0)
        owner = env.object(0x80, "owner", fill=0)
        records = []
        if sparkle:
            records.append((STR_SPARKLE, animation(env, *anim_range)))
        if extra_maps:
            records.append((b"GAME_OTHER\0", animation(env, 1, 2)))
        sp_map = env.object(0x40, "sparkle-map", fill=0)
        hash_map(env, sp_map + 0x10, records, count_a)
        gl_records = []
        glitter_set = frame_set(env, set_count)
        if glitter:
            gl_records.append((STR_GLITTER, glitter_set))
        if extra_maps:
            gl_records.append((b"GAME_ELSE\0", frame_set(env, 1)))
        gl_map = env.object(0x40, "glitter-map", fill=0)
        hash_map(env, gl_map + 0x10, gl_records, count_b)
        env.put(owner + 0x10, sp_map)
        env.put(owner + 0x2C, gl_map)
        env.put(actor + 0x08, a_flags)
        env.put(actor + 0x0C, owner)
        env.put(actor + 0x6C, state_obj)
        env.put(state_obj + 0x1C, state)
        player = actor + 0x188
        if animset:
            env.put(player + 0x08, frame_set(env, 3, 2))
        env.put(player + 0x14, counter)
        env.put(player + 0x18, running)
        env.put(player + 0x1C, flag)
        env.put(player + 0x20, 0x321)
        env.put(player + 0x24, 0x654)
        env.put(GLOBAL_STEP, step)
        return {"actor": actor, "state": state_obj}
    return setup


def sparkle(label, setup):
    return Case(label, SPARKLE, setup, arguments=(lambda t: t["actor"],))


def mother_setup(state, *, anim=True, bounds=(10, 40, 20, 60), origin=(300, 500), first=4, doubled=1, hit=False, baby_ok=True, others=(), a_flags=0,
                 rands=(1, 2, 3, 4, 5, 6, 7, 8), nbuckets=7, script=None):
    """bounds = (x low, x high, y low, y high) at +0x118, +0x120, +0x11c, +0x124."""
    def setup(env):
        actor = env.object(0x80, "actor", fill=0)
        state_obj = env.object(0x180, "state", fill=0)
        owner = env.object(0x40, "owner", fill=0)
        template = env.object(0x40, "template", fill=0)
        holder = env.object(0x40, "holder", fill=0)
        flag_block = env.object(0x130, "environment", fill=0)
        entries = [(b"Other\0", 0x7001)]
        if hit:
            baby = env.object(0x40, "baby-template", fill=0, words=[0, 0, 0x5150, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            log = env.object(0x80, "callback-log", fill=0)

            def observe(env, call, log=log):
                slot = log + 16 * (env.calls_so_far(call.function) - 1)
                actor = call.arguments[0]
                env.put(slot, actor, call.receiver, env.get(actor + 0x4C), env.get(actor + 0x50))
                return 0x1234

            callback = env.stub("spawn-callback", "cdecl", 1, observe)
            env.put(baby + 0x10, callback if baby_ok else 0)
            entries.append((STR_BABY, baby))
        hash_map(env, holder + 0x10, entries, nbuckets)
        env.put(owner + 0x08, template)
        env.put(template + 0x0C, owner)
        env.put(owner + 0x14, holder)
        env.put(owner + 0x24, 0x8123)
        spare = env.object(0x30, "free-nodes", fill=0)
        env.put(spare, spare + 12, 0, 0, spare + 24, 0, 0, 0, 0, 0)
        env.put(template + 0x20, spare)
        env.put(template + 0x28, 4)
        previous = 0
        for z, flags in others:
            member = env.object(0x80, "member", fill=0)
            env.put(member + 100, z)
            env.put(member + 10, flags)
            node = env.object(12, "node", fill=0)
            env.put(node, 0, previous, member)
            if previous:
                env.put(previous, node)
            else:
                env.put(template + 0x14, node)
            previous = node
        if previous:
            env.put(template + 0x18, previous)
        env.put(actor + 0x08, a_flags)
        env.put(actor + 0x0C, owner)
        env.put(actor + 0x40, ((a_flags << 7) | (a_flags >> 25)) & 0xFFFFFFFF)
        env.put(actor + 0x6C, state_obj)
        env.put(state_obj + 0x1C, state)
        env.put(state_obj + 0x20, 0x77)
        if anim:
            record = env.object(0x180, "anim", fill=0)
            env.put(record + 0x4C, *origin)
            env.put(record + 0x64, first)
            env.put(record + 0x118, bounds[0], bounds[2], bounds[1], bounds[3])
            env.put(state_obj + 0x170, record)
        env.put(GLOBAL_ENV, flag_block)
        env.put(flag_block + 0x124, doubled)
        env.override(RAND, sequence(*rands))
        return {"actor": actor, "state": state_obj}
    return setup


def mother(label, setup):
    return Case(label, MOTHER, setup, arguments=(lambda t: t["actor"],))


def mother_setup_hooked(state, hook_call=None, hook=None, **options):
    """Like mother_setup, but the rand stand-in also runs hook(env, tokens) when it is called for the hook_call-th time."""
    base = mother_setup(state, **options)
    rands = options.get("rands", (1, 2, 3, 4, 5, 6, 7, 8))

    def setup(env):
        tokens = base(env)

        def rand(env, call):
            number = env.calls_so_far(call.function)
            if number == hook_call:
                hook(env, tokens)
            return rands[min(number, len(rands)) - 1]

        env.override(RAND, rand)
        return tokens
    return setup


RECORD_FIELDS = (0x4C, 0x50, 0x118, 0x11C, 0x120, 0x124, 0x64)


def mutate_field(offset, value):
    def hook(env, tokens):
        env.put(env.get(tokens["state"] + 0x170) + offset, value)
    return hook


def swap_record(env, tokens):
    record = env.object(0x180, "replacement", fill=0)
    env.put(record + 0x4C, 1000, 2000)
    env.put(record + 0x64, 77)
    env.put(record + 0x118, 5, 9, 15, 25)
    env.put(tokens["state"] + 0x170, record)


def cases(random_source):
    rnd = random_source
    # ---- sparkle (0x4485a0)
    for sparkle_found in (True, False):
        for glitter_found in (True, False):
            for anim_range in ((3, 9), (5, 5), (9, 3), (1, 2), (0, 0)):
                for flags in (0, 0x21, 0xFFFFFFDE, 0x80010000):
                    if (anim_range[0] + 2 * flags) % 3:
                        continue
                    yield sparkle(f"sparkle start found={sparkle_found},{glitter_found} range={anim_range} flags={flags:#x}",
                                  sparkle_setup(0, sparkle=sparkle_found, glitter=glitter_found, anim_range=anim_range, a_flags=flags,
                                                count_a=rnd.choice((1, 3, 7)), count_b=rnd.choice((1, 5, 8)), set_count=rnd.randrange(1, 4)))
    yield sparkle("sparkle start single bucket maps", sparkle_setup(0, count_a=1, count_b=1))
    for state in (1, 2, 4, 6, 9, 10, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x100, 0x10000):
        yield sparkle(f"sparkle ignores state {state:#x}", sparkle_setup(state, flag=1, a_flags=rnd.getrandbits(32)))
    for flag in (0, 1, 0x80000000, 0x100):
        for counter in (0, 1, 2, 3, 9, 0x100):
            for running in (0, 1, 0x40):
                for step in (0, 1, 2, 3, 9, 0x100, 0x7FFFFFFF):
                    if (counter * 7 + running + step) % 5:
                        continue
                    if flag == 0 and (counter == 0 or (running and step >= counter)):
                        continue  # would enter the full animation advance
                    yield sparkle(f"sparkle advance flag={flag:#x} counter={counter} running={running} step={step}",
                                  sparkle_setup(5, flag=flag, counter=counter, running=running, step=step, a_flags=rnd.getrandbits(32)))
    # forced coverage grid, independent of the random thinning above
    for flag, counter, running, step in ((1, 0, 0, 1), (1, 1, 0, 1), (1, 1, 1, 1), (1, 2, 1, 1), (1, 3, 1, 2), (1, 3, 1, 3), (1, 3, 1, 9),
                                         (0, 1, 0, 1), (0, 5, 1, 2), (0x80000000, 1, 0, 1), (5, 4, 1, 4)):
        yield sparkle(f"sparkle advance fixed {flag:#x},{counter},{running},{step}",
                      sparkle_setup(5, flag=flag, counter=counter, running=running, step=step, a_flags=0x0F0F0F0F))
    for counter in (0, 1, 7):
        for flag in (0, 1):
            yield sparkle(f"sparkle advance without animation set counter={counter} flag={flag}",
                          sparkle_setup(5, animset=False, counter=counter, flag=flag))
    for _ in range(6):
        yield sparkle("sparkle random advance", sparkle_setup(5, flag=rnd.choice((1, 2, 0x4000)), counter=rnd.randrange(1, 40), running=rnd.randrange(0, 3),
                                                             step=rnd.randrange(0, 50), a_flags=rnd.getrandbits(32), anim_range=(rnd.randrange(0, 5), rnd.randrange(5, 12))))

    # ---- mother (0x448440)
    for anim in (True, False):
        for flags in (0, 0x1, 0x40, 0xFFFFFFFF, 0x12345678):
            yield mother(f"mother start anim={anim} flags={flags:#x}", mother_setup(0, anim=anim, hit=True, a_flags=flags))
    for state in (1, 3, 5, 9, 11, 0xF, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x10A, 0x100000000 - 10):
        yield mother(f"mother ignores state {state:#x}", mother_setup(state, hit=True, a_flags=rnd.getrandbits(32)))
    fixed = (
        ((10, 40, 20, 60), (300, 500)),
        ((0, 0, 0, 0), (7, 9)),
        ((-30, -5, -50, -1), (100, 200)),
        ((-8, 8, -3, 3), (-20, -40)),
        ((12, 11, 30, 29), (5, 6)),          # zero-width ranges: the parity branch
        ((12, 11, 5, 40), (5, 6)),
        ((5, 40, 31, 30), (5, 6)),
        ((20, 3, 4, 9), (50, 60)),            # negative x range
        ((3, 5, 40, 2), (50, 60)),            # negative y range
        ((100, 300, 7, 7), (0, 0)),
    )
    sequences = ((1, 2, 3, 4), (5, 4, 3, 2), (0, 0, 0, 0), (1, 1, 1, 1), (0x7FFF, 0x7FFE, 0x7FFD, 0x7FFC), (6, 13, 22, 31), (2, 7, 12, 17),
                 (0x80000005, 0x80000006, 0xFFFFFFFD, 0xFFFFFFF0))
    for doubled in (1, 0, 2, 0x80000000):
        for index, (bounds, origin) in enumerate(fixed):
            for number, rands in enumerate(sequences):
                if (index + number + doubled) % 3:
                    continue
                yield mother(f"mother spawn bounds#{index} rands#{number} doubled={doubled:#x}",
                             mother_setup(10, bounds=bounds, origin=origin, doubled=doubled, hit=True, rands=rands,
                                          first=[4, 0, -3, 99, 0x7FFFFFFE, 17][(index + number) % 6]))
    for index, (bounds, origin) in enumerate(fixed):
        yield mother(f"mother spawn parity even #{index}", mother_setup(10, bounds=bounds, origin=origin, hit=True, rands=(2, 4, 6, 8)))
        yield mother(f"mother spawn parity odd #{index}", mother_setup(10, bounds=bounds, origin=origin, hit=True, rands=(1, 3, 5, 7)))
        yield mother(f"mother spawn parity mixed #{index}", mother_setup(10, bounds=bounds, origin=origin, hit=True, rands=(1, 2, 2, 1)))
        yield mother(f"mother spawn parity mixed2 #{index}", mother_setup(10, bounds=bounds, origin=origin, hit=True, rands=(2, 1, 1, 2)))
    # lookups
    for buckets in (1, 2, 7, 64):
        for key_hit in (True, False):
            yield mother(f"mother lookup buckets={buckets} hit={key_hit}", mother_setup(10, hit=key_hit, nbuckets=buckets, rands=(3, 5, 8, 13)))
    # list ordering
    lists = (((1, 0),), ((5, 0),), ((6, 0),), ((100, 0),), ((100, 2),), ((5, 2),), ((1, 0), (2, 0), (3, 0)), ((9, 0), (2, 0), (3, 0)),
             ((9, 2), (2, 0), (3, 0)), ((1, 2), (2, 2), (3, 2)), ((1, 0), (9, 2), (7, 0)), ((0, 0), (0, 0)))
    for number, others in enumerate(lists):
        for first in (4, 8):
            yield mother(f"mother spawn list#{number} first={first}", mother_setup(10, hit=True, others=others, first=first, rands=(4, 9, 16, 25)))
    # a value the callee changes behind the function's back
    for call_number in (1, 2, 3, 4):
        for offset in RECORD_FIELDS:
            yield mother(f"mother rand #{call_number} rewrites record +{offset:#x}",
                         mother_setup_hooked(10, call_number, mutate_field(offset, 0x1234 + offset + call_number), hit=True,
                                             rands=(7, 11, 13, 17)))
        yield mother(f"mother rand #{call_number} swaps record", mother_setup_hooked(10, call_number, swap_record, hit=True, rands=(7, 11, 13, 17)))
    for call_number in (1, 2):
        for offset in RECORD_FIELDS:
            yield mother(f"mother single pass rand #{call_number} rewrites +{offset:#x}",
                         mother_setup_hooked(10, call_number, mutate_field(offset, 0x4321 + offset), hit=True, doubled=0, rands=(7, 11)))
    for _ in range(40):
        low_x, low_y = rnd.randrange(-100, 100), rnd.randrange(-100, 100)
        yield mother("mother random spawn",
                     mother_setup(10, bounds=(low_x, low_x + rnd.randrange(-1, 80), low_y, low_y + rnd.randrange(-1, 80)),
                                  origin=(rnd.randrange(-500, 2000), rnd.randrange(-500, 2000)), first=rnd.randrange(-5, 300),
                                  doubled=rnd.choice((0, 1, rnd.getrandbits(32))), hit=True,
                                  rands=tuple(rnd.randrange(0, 0x8000) for _ in range(4))))
