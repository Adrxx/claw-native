"""Cases for level_one_claw_rope_01: Level 1 Claw rope states."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

GET_X = 0x403AB0
GET_Y = 0x403AC0
FLIP_BOX = 0x418080
ENTER = 0x4181C0

GATE_PTR = 0x537204
ANIM_STEP_GLOBAL = 0x5430C4
MODE_GLOBAL = 0x534EAC
PHYS = 0x534DB8
SENTINEL = 0x80000000
MASK = 0xFFFFFFFF


def u32(value):
    return value & MASK


def word(rng):
    """A distinct-looking 32-bit word, never the sentinel."""
    while True:
        value = rng.randrange(0, 1 << 32)
        if value != SENTINEL:
            return value


def small(rng):
    return rng.randrange(-3000, 3000) & MASK


def table_hash(text):
    value = 0
    for char in text.encode("ascii"):
        signed = char - 256 if char >= 128 else char
        value = (value * 0x21 + signed) & MASK
    return value


def animation(env, rng, frames=2):
    """An animation record: +0x10 frame count, +0xc frame pointer array, frame+0x1c start value."""
    array = env.object(4 * frames, "frames")
    for index in range(frames):
        frame = env.object(0x30, "frame", fill=0)
        env.put(frame + 0x1C, 0x100 + 7 * index + rng.randrange(0, 90))
        env.put(array + 4 * index, frame)
    record = env.object(0x30, "animation", fill=0)
    env.put(record + 0x0C, array)
    env.put(record + 0x10, frames)
    return record


def build_pair(env, rng, x_off, y_off, ptr_off=0x0C, ptr_target_off=0x4C):
    """An object X with X+0xc -> Y; returns X with distinct values for the four summed fields."""
    y = env.object(0x70, "inner", fill=0)
    x = env.object(0x160, "outer", fill=0)
    env.put(x + ptr_off, y)
    env.put(y + 0x4C, word(rng))
    env.put(y + 0x50, word(rng))
    env.put(x + 0x140, word(rng))
    env.put(x + 0x144, word(rng))
    return x, y


def getter_case(label, function, a, b):
    def setup(env):
        x = env.object(0x160, "outer", fill=0)
        y = env.object(0x70, "inner", fill=0)
        env.put(x + 0x0C, y)
        env.put(y + 0x4C, a)
        env.put(y + 0x50, b)
        env.put(x + 0x140, (b * 3 + 1) & MASK)
        env.put(x + 0x144, (a * 5 + 7) & MASK)
        return {"x": x}

    return Case(label, function, setup, receiver=lambda t: t["x"])


def box_case(label, rng, flag, sentinels=(False, False, False), flag_word=None, flags=None):
    values = [word(rng) for _ in range(6)]

    def setup(env):
        owner = env.object(0x200, "owner", fill=0)
        state = env.object(0x140, "state", fill=0)
        extra = env.object(0x20, "extra", fill=0)
        env.put(owner + 0x40, word(rng) if flags is None else flags)
        pairs = [(0x118, 0x120), (0x128, 0x130), (0x138, 0x140)]
        for index, (first, second) in enumerate(pairs):
            env.put(owner + first, SENTINEL if sentinels[index] else values[2 * index])
            env.put(owner + second, values[2 * index + 1] if not sentinels[index] else word(rng))
        env.put(owner + 0x11C, word(rng))
        env.put(owner + 0x124, word(rng))
        env.put(state, flag)
        env.put(state + 0x114, word(rng))  # state[0x45] before the store of 0x5dc
        env.put(state + 4, word(rng))
        env.put(state + 0x7C, word(rng))
        return {"owner": owner, "state": state, "extra": extra}

    return Case(
        label,
        FLIP_BOX,
        setup,
        arguments=(lambda t: t["owner"], lambda t: t["extra"], lambda t: t["state"]),
    )


def enter_setup(
    rng,
    flag,
    gate,
    has_cursor,
    anim_pending,
    big_mode,
    state45,
    found,
    anim_rec,
    w20,
    bitset_big=False,
    step=None,
    gate_flags_hi=None,
    anim_variant=0,
    decoy=False,
    mode_value=None,
    alias=None,
):
    def setup(env):
        owner = env.object(0x220, "owner", fill=0)
        state = env.object(0x140, "state", fill=0)
        link = env.object(0x20, "link", fill=0)
        gate_obj = env.object(0x20, "gate", fill=0)
        anim_obj = animation(env, rng, 3)  # the owner's own animation, for the early-out path of the first step

        # player chain: state[0x4d] -> +0x6c -> +0x18 -> X
        x, _y = build_pair(env, rng, 0x140, 0x144)
        mid = env.object(0x80, "mid", fill=0)
        top = env.object(0x80, "top", fill=0)
        env.put(top + 0x6C, mid)
        env.put(mid + 0x18, x)
        env.put(state + 4 * 0x4D, top)

        # owner animation sub-object at +0x188 (first call: step by the global)
        sub = owner + 0x188
        if anim_variant == 1:  # counter above the step: only counts down
            env.put(sub + 8, anim_obj)
            env.put(sub + 0x14, 90 + rng.randrange(0, 50))
            env.put(sub + 0x18, 1)
            env.put(sub + 0x24, word(rng))
        elif anim_variant == 2:  # no loop flag: counter decrements by one
            env.put(sub + 8, anim_obj)
            env.put(sub + 0x14, 5 + rng.randrange(0, 50))
            env.put(sub + 0x18, 0)
            env.put(sub + 0x24, word(rng))
        elif anim_variant == 3:  # counter zero and animation paused
            env.put(sub + 8, anim_obj)
            env.put(sub + 0x14, 0)
            env.put(sub + 0x18, 1)
            env.put(sub + 0x1C, 1)
            env.put(sub + 0x20, word(rng))
            env.put(sub + 0x24, word(rng))
        elif anim_variant == 4:  # counter not above the step: expires into the paused path
            env.put(sub + 8, anim_obj)
            env.put(sub + 0x14, 3)
            env.put(sub + 0x18, 1)
            env.put(sub + 0x1C, 1)
            env.put(sub + 0x20, word(rng))
            env.put(sub + 0x24, word(rng))
        env.put(ANIM_STEP_GLOBAL, 3 + rng.randrange(0, 40) if step is None else step)

        env.put(owner + 8, word(rng) | 0x10)
        env.put(owner + 0x4C, word(rng))
        env.put(owner + 0x50, word(rng))
        env.put(owner + 0xCC, word(rng))
        env.put(owner + 0x118, word(rng))
        env.put(owner + 0x128, word(rng))
        env.put(owner + 0x148, word(rng))
        env.put(owner + 0x14C, word(rng))

        # name table lookup of CLAW_JUMP: owner+0xc -> +0x2c -> (+0x10 is the table)
        info = env.object(0x40, "info", fill=0)
        tables = env.object(0x40, "tables", fill=0)
        env.put(owner + 0x0C, info)
        env.put(info + 0x2C, tables)
        buckets_count = 7
        buckets = env.object(4 * buckets_count, "buckets", fill=0)
        env.put(tables + 0x10 + 4, buckets)
        env.put(tables + 0x10 + 8, buckets_count)
        jump = animation(env, rng, 2)
        index = table_hash("CLAW_JUMP") % buckets_count
        if found:
            name = env.object(16, "name", data=b"CLAW_JUMP\0")
            node = env.object(0x10, "node", fill=0)
            env.put(node + 8, name)
            env.put(node + 0xC, jump)
            head = node
            if decoy:
                other_name = env.object(16, "name2", data=b"CLAW_JUMQ\0")
                other = env.object(0x10, "node2", fill=0)
                env.put(other + 8, other_name)
                env.put(other + 0xC, animation(env, rng, 1))
                env.put(other, node)
                head = other
            env.put(buckets + 4 * index, head)
        elif decoy:
            other_name = env.object(16, "name2", data=b"CLAW_JUMQ\0")
            other = env.object(0x10, "node2", fill=0)
            env.put(other + 8, other_name)
            env.put(other + 0xC, animation(env, rng, 1))
            env.put(buckets + 4 * index, other)

        # gate global
        env.put(GATE_PTR, gate_obj)
        gate_low = (gate & 0xFF) | ((word(rng) & 0xFFFFFF00) if gate_flags_hi is None else gate_flags_hi)
        env.put(gate_obj + 4, gate_low)
        env.put(gate_obj + 0xC, MASK if rng.randrange(2) else (word(rng) | 0x03000000))

        # state
        env.put(state, flag)
        env.put(state + 4, 1 if anim_pending else 0)
        env.put(state + 4 * 8, word(rng))
        env.put(state + 4 * 0xF, word(rng))
        env.put(state + 4 * 0x17, word(rng))
        env.put(state + 4 * 0x18, word(rng))
        env.put(state + 4 * 0x19, word(rng))
        env.put(state + 4 * 0x43, word(rng))
        env.put(state + 4 * 0x45, state45)
        env.put(state + 4 * 0x46, word(rng))
        env.put(state + 4 * 0x47, word(rng))
        env.put(state + 4 * 0x49, animation(env, rng, 2) if anim_rec else 0)

        # cursor object: state[0x4b] -> +0x6c -> +0x18 -> W
        w = env.object(0x330, "cursor", fill=0)
        env.put(w + 0x20, w20)
        env.put(w + 0x14, word(rng))
        set_base = w + 0x2F4
        if bitset_big:
            bits = env.object(8, "bits")
            env.put(bits, word(rng))
            env.put(bits + 4, word(rng))
            env.put(set_base + 8, 0x40)
            env.put(set_base + 0xC, bits)
        else:
            env.put(set_base + 8, 0x20)
            env.put(set_base + 0xC, word(rng))
        if has_cursor:
            cmid = env.object(0x80, "cmid", fill=0)
            ctop = env.object(0x80, "ctop", fill=0)
            env.put(ctop + 0x6C, cmid)
            env.put(cmid + 0x18, w)
            env.put(state + 4 * 0x4B, ctop)

        # original-side globals the function stores to or the physics helper reads
        env.put(MODE_GLOBAL, (0x26BC if big_mode else rng.randrange(0, 0x26BC)) if mode_value is None else mode_value)
        env.put(PHYS + 0x10, 0, 0x3FF00000 + rng.randrange(0, 0x100000))
        env.put(PHYS + 0x20, 0, 0x3FE00000 + rng.randrange(0, 0x100000))
        env.put(PHYS + 0x50, 0, 0x40000000 + rng.randrange(0, 0x100000))
        env.put(PHYS + 0x40, rng.randrange(0, 1 << 32), 0x40000000)
        env.put(PHYS + 0x48, rng.randrange(0, 1 << 32), 0x40100000)
        for off in (0x18, 0x1C, 0x28, 0x2C, 0x30, 0x34):
            env.put(PHYS + off, 0x10000000 + word(rng) % 0x30000000)
        for off in (0x68, 0x70):
            env.put(PHYS + off, word(rng))
        if alias is not None:
            kind, offset = alias
            link = (owner if kind == "owner" else state) + offset - 0x1C
        return {"owner": owner, "link": link, "state": state}

    return setup


def cases(random_source):
    """Yield Case objects."""
    rng = random_source

    # The two getters: distinct values per field, wraparound and sign boundaries.
    corner = [(0, 0), (1, 1), (0x7FFFFFFF, 1), (0xFFFFFFFF, 1), (0x80000000, 0x80000000), (0xFFFFFFF8, 0x14), (0x7FFFFFFF, 0x7FFFFFFF)]
    for index, (a, b) in enumerate(corner):
        yield getter_case(f"x getter corner {index}", GET_X, a, b)
        yield getter_case(f"y getter corner {index}", GET_Y, a, b)
    for index in range(20):
        a, b = word(rng), word(rng)
        yield getter_case(f"x getter random {index}", GET_X, a, b)
        yield getter_case(f"y getter random {index}", GET_Y, a, b)

    # Flip box: flag clear, then every sentinel combination with the flag set.
    yield box_case("box flag clear", rng, 0)
    yield box_case("box flag clear sentinel", rng, 0, (True, True, True))
    for flag in (1, 0x100, MASK):
        for mask in range(8):
            sentinels = tuple(bool(mask & (1 << bit)) for bit in range(3))
            yield box_case(f"box flag {flag:#x} sentinels {mask:03b}", rng, flag, sentinels)
    yield box_case("box existing flags clear", rng, 1, flags=0)
    yield box_case("box existing flags set", rng, 1, flags=MASK)
    yield box_case("box existing flags two", rng, 1, flags=2)
    for index in range(12):
        sentinels = tuple(bool(rng.randrange(2)) for _ in range(3))
        yield box_case(f"box random {index}", rng, word(rng) | 1, sentinels)

    # Entering the jump state.
    enter_args = (lambda t: t["owner"], lambda t: t["link"], lambda t: t["state"])

    def enter(label, **options):
        return Case(label, ENTER, enter_setup(rng, **options), arguments=enter_args)

    base = dict(
        flag=0, gate=1, has_cursor=True, anim_pending=True, big_mode=False, state45=0,
        found=True, anim_rec=True, w20=0,
    )
    # gate closed: nothing but the first animation step and the position updates happen
    for flag in (0, 1, 0x55):
        for gate in (0, 2, 0xFE, 0x80):
            for variant in (0, 2):
                yield enter(f"gate {gate:#x} flag {flag} v{variant}", **{**base, "flag": flag, "gate": gate, "anim_variant": variant})
    # every animation step variant under an open gate
    for variant in range(5):
        for flag in (0, 1):
            yield enter(f"animation variant {variant} flag {flag}", **{**base, "flag": flag, "anim_variant": variant})
    # full product over the open-gate branches
    for flag in (0, 1):
        for has_cursor in (False, True):
            for pending in (False, True):
                for big_mode in (False, True):
                    for state45 in (0, 0x1234):
                        for found in (False, True):
                            yield enter(
                                f"open flag {flag} cursor {has_cursor} pending {pending} big {big_mode} s45 {state45:#x} found {found}",
                                **{**base, "flag": flag, "has_cursor": has_cursor, "anim_pending": pending,
                                   "big_mode": big_mode, "state45": state45, "found": found},
                            )
    # pending animation without a record
    for flag in (0, 1):
        yield enter(f"pending without record flag {flag}", **{**base, "flag": flag, "anim_rec": False})
    # the cursor gate threshold and bit set layouts
    for w20 in (0, 1, 2, 0xFFFFFFFF):
        for big in (False, True):
            yield enter(f"cursor w20 {w20:#x} big bitset {big}", **{**base, "w20": w20, "bitset_big": big})
    # name table decoys
    for found in (False, True):
        yield enter(f"decoy found {found}", **{**base, "found": found, "decoy": True})
    for mode in (0x26BB, 0x26BC, 0x26BD, 0):
        for s45 in (0, 0xFFFFFFFF):
            yield enter(f"mode {mode:#x} s45 {s45:#x}", **{**base, "state45": s45, "mode_value": mode})
    # gate bit mixes
    for hi in (0, 0xFFFFFF00, 0x100, 0xAA00):
        yield enter(f"gate high bits {hi:#x} open", **{**base, "gate_flags_hi": hi})
        yield enter(f"gate high bits {hi:#x} closed", **{**base, "gate": 0, "gate_flags_hi": hi})
    # random extras
    for index in range(24):
        yield enter(
            f"random enter {index}",
            flag=rng.randrange(0, 3), gate=rng.randrange(0, 4), has_cursor=bool(rng.randrange(2)),
            anim_pending=bool(rng.randrange(2)), big_mode=bool(rng.randrange(2)),
            state45=rng.randrange(0, 3) * word(rng) & MASK, found=bool(rng.randrange(2)),
            anim_rec=bool(rng.randrange(2)), w20=rng.randrange(0, 3), bitset_big=bool(rng.randrange(2)),
            anim_variant=rng.randrange(0, 5), decoy=bool(rng.randrange(2)),
        )

    # the second argument aliasing fields the function or its callees also touch: store order becomes visible
    alias_base = dict(base, flag=0)
    for offset in (0x8, 0x4C, 0x50, 0xCC, 0x118, 0x11C, 0x120, 0x124, 0x128, 0x12C, 0x130, 0x134,
                   0x148, 0x14C, 0x190, 0x194, 0x19C, 0x1A0, 0x1A4, 0x1A8, 0x1AC, 0x1B0):
        for flag in (0, 1):
            yield enter(f"link aliases owner+{offset:#x} flag {flag}", **{**alias_base, "flag": flag, "alias": ("owner", offset)})
    for index in (0, 1, 8, 0xF, 0x17, 0x18, 0x19, 0x43, 0x45, 0x46, 0x47, 0x49, 0x4B):
        for state45 in (0, 0x1234):
            yield enter(f"link aliases state[{index:#x}] s45 {state45:#x}", **{**alias_base, "state45": state45, "alias": ("state", 4 * index)})
