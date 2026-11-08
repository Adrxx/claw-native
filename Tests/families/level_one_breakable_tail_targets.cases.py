"""Cases for level_one_breakable_tail_targets: Level 1 breakable tail-jump bodies."""
import struct

from clawparity.cases import Case

PRELUDE = 0x433F30
SETTLE = 0x433FB0
GLOBAL_STEP = 0x5430C4
C_SUB = 0x50C838
C_FLOOR = 0x50C840
C_SCALE = 0x50C848
ANIMATOR = 0x188


def d(value):
    return struct.pack("<d", value)


def bits(pattern):
    return struct.unpack("<d", struct.pack("<Q", pattern))[0]


def make_prelude(rs, step=1, mode="early", counter=0, running=0, flags=None, hold=0):
    """Object with an animator at sub+0x188.

    mode: early (animator+8 == 0, callee returns at once), dec (counter nonzero, no restart),
    short (counter nonzero, restart set, step < counter), expire (step >= counter, then hold decides),
    idle (counter zero).
    """
    def setup(env):
        obj = env.object(0x420, "object", data=bytes(rs.randrange(1, 256) for _ in range(0x420)))
        sub = env.object(0x1C0, "sub", data=bytes(rs.randrange(1, 256) for _ in range(0x1C0)))
        env.put(obj + 0x12C, sub)
        env.put(sub + 8, rs.getrandbits(32) if flags is None else flags)
        a = sub + ANIMATOR
        env.put(a + 8, 0 if mode == "early" else rs.randrange(1, 1 << 30))
        env.put(a + 0x14, counter)
        env.put(a + 0x18, running)
        env.put(a + 0x1C, hold)
        env.put(a + 0x20, rs.randrange(1, 1 << 30))
        env.put(a + 0x24, rs.randrange(1, 1 << 30))
        env.put(GLOBAL_STEP, step)
        return {"obj": obj, "sub": sub}
    return setup


def prelude(label, setup):
    return Case(label, PRELUDE, setup, receiver=lambda t: t["obj"])


def make_settle(rs, ptr_mode="none", flag_int=None, selector=0, ival=None, cur=None, other=None,
                velocity=None, mode=None, flags=None, link_value=None):
    """ptr_mode: none, other (separate object), self (points at the object itself)."""
    def setup(env):
        obj = env.object(0x420, "object", data=bytes(rs.randrange(1, 256) for _ in range(0x420)))
        sub = env.object(0x1C0, "sub", data=bytes(rs.randrange(1, 256) for _ in range(0x1C0)))
        peer = env.object(0xB0, "peer", data=bytes(rs.randrange(1, 256) for _ in range(0xB0)))
        env.put(obj + 0x12C, sub)
        env.put(sub + 8, rs.getrandbits(32) if flags is None else flags)
        env.put(obj + 0xC8, rs.randrange(1, 1 << 30))
        env.put(obj + 0x404, selector)
        env.put(obj + 0x40C, rs.getrandbits(32) if ival is None else ival & 0xFFFFFFFF)
        env.put(obj + 0x400, {"none": 0, "other": peer, "self": obj}[ptr_mode])
        if cur is not None:
            env.write(obj + 0x70, d(cur))
        if other is not None:
            env.write(obj + 0xA0, d(other))
        if velocity is not None:
            env.write(obj + 0x58, d(velocity) if not isinstance(velocity, bytes) else velocity)
        return {"obj": obj, "sub": sub, "peer": peer}
    return setup


def settle(label, setup):
    return Case(label, SETTLE, setup, receiver=lambda t: t["obj"])


def cases(random_source):
    rs = random_source
    # ---- 0x433f30 -----------------------------------------------------------------------------
    for step in (0, 1, 3, 0x7FFFFFFF, 0xFFFFFFFF, rs.randrange(2, 1000)):
        yield prelude(f"prelude early return step {step:#x}", make_prelude(rs, step, "early"))
    # callee decrements by one when it is not running, whatever the step
    for counter in (1, 2, 9, 0x80000000):
        yield prelude(f"prelude counter {counter:#x} no restart",
                      make_prelude(rs, rs.randrange(1, 50), "dec", counter, running=0))
    # callee subtracts the step while below the counter
    for counter, step in ((2, 1), (10, 3), (100, 99), (0x12345, 0x1234), (7, 0)):
        yield prelude(f"prelude counter {counter} step {step} short",
                      make_prelude(rs, step, "short", counter, running=rs.randrange(1, 1 << 30)))
    # step reaches counter: counter cleared, hold set stops the callee
    for counter, step in ((1, 1), (5, 5), (5, 6), (3, 0xFFFFFFFF), (1, 9)):
        yield prelude(f"prelude counter {counter} step {step} expires, hold",
                      make_prelude(rs, step, "expire", counter, running=1, hold=rs.randrange(1, 1 << 30)))
    # idle counter with hold set: both tested words nonzero or zero in every combination
    yield prelude("prelude idle hold set: restart flag raised",
                  make_prelude(rs, 4, "idle", 0, running=0, hold=rs.randrange(1, 1 << 30), flags=0x1234ABCD))
    yield prelude("prelude idle hold set flag already raised",
                  make_prelude(rs, 4, "idle", 0, running=0, hold=1, flags=0x10000 | 0x0F0F0F0F))
    yield prelude("prelude idle hold set flags zero",
                  make_prelude(rs, 4, "idle", 0, running=0, hold=2, flags=0))
    yield prelude("prelude idle hold set flags all ones",
                  make_prelude(rs, 4, "idle", 0, running=0, hold=3, flags=0xFFFEFFFF))
    yield prelude("prelude early hold zero counter zero no flag",
                  make_prelude(rs, 1, "early", 0, 0, hold=0, flags=0x55555555))
    yield prelude("prelude early hold set counter zero",
                  make_prelude(rs, 1, "early", 0, 0, hold=5, flags=0x55555555))
    yield prelude("prelude early hold zero counter set",
                  make_prelude(rs, 1, "early", 6, 0, hold=0, flags=0xAAAA5555))
    yield prelude("prelude early hold set counter set",
                  make_prelude(rs, 1, "early", 6, 0, hold=6, flags=0xAAAA5555))
    for _ in range(6):
        yield prelude("prelude random idle",
                      make_prelude(rs, rs.getrandbits(32), "idle", 0, rs.getrandbits(32),
                                   hold=rs.randrange(1, 1 << 30)))

    # ---- 0x433fb0 -----------------------------------------------------------------------------
    def with_constants(builder):
        """Wrap a setup so builder(env, constants) can place values relative to the original constants."""
        def setup(env):
            constants = [struct.unpack("<d", env.read(a, 8))[0] for a in (C_SUB, C_FLOOR, C_SCALE)]
            return builder(env, constants)
        return setup

    def settle_case(label, ptr_mode="none", selector=0, ival=None, relation="equal", offset_from_floor=None,
                    velocity=1.0, cur=None, flags=None, velocity_bytes=None):
        def builder(env, constants):
            c_sub, c_floor, c_scale = constants
            current = cur if cur is not None else rs.uniform(-1000, 1000)
            if selector == 0:
                target = float(struct.unpack("<i", struct.pack("<I", (ival if ival is not None else 0) & 0xFFFFFFFF))[0])
            else:
                target = current
            if relation == "equal":
                if selector == 0:
                    current = target
                other = current
            elif relation == "ulp":
                other = bits(struct.unpack("<Q", d(current))[0] + 1)
            elif relation == "less":
                other = current - 1.5
            elif relation == "greater":
                other = current + 1.5
            elif relation == "nan":
                other = bits(0x7FF8000000000001)
            elif relation == "negzero":
                current, other = 0.0, -0.0
            if velocity_bytes is not None:
                vel = velocity_bytes
            elif offset_from_floor is not None:
                vel = d(c_floor + offset_from_floor)
            else:
                vel = d(velocity)
            tokens = make_settle(rs, ptr_mode=ptr_mode, selector=selector, ival=ival, cur=current,
                                 other=other, velocity=vel, flags=flags)(env)
            tokens["constants"] = constants
            return tokens
        return Case(label, SETTLE, with_constants(builder), receiver=lambda t: t["obj"])

    # selector (+0x404) zero: target taken from the integer at +0x40c
    for ival in (0, 1, -1, 7, 0x7FFFFFFF, -0x80000000, 123456, -98765, 0x01020304):
        yield settle_case(f"settle int target {ival} reached", selector=0, ival=ival, relation="equal", velocity=3.0)
    yield settle_case("settle int target mismatch", selector=0, ival=57, relation="greater")
    yield settle_case("settle int target mismatch low", selector=0, ival=-57, relation="less")
    # selector nonzero: +0xa0 is left alone
    for relation in ("equal", "ulp", "less", "greater", "nan", "negzero"):
        for selector in (1, 0x80000000):
            yield settle_case(f"settle selector {selector:#x} {relation}", selector=selector, relation=relation,
                              velocity=2.0)
    # linked peer: its +0xa0 receives current - constant
    for ptr_mode in ("other", "self"):
        for selector in (0, 3):
            for relation in ("equal", "less", "greater"):
                yield settle_case(f"settle {ptr_mode} link selector {selector} {relation}", ptr_mode=ptr_mode,
                                  selector=selector, ival=rs.randrange(-5000, 5000), relation=relation,
                                  cur=rs.uniform(-4000, 4000), velocity=1.25)
    # self link with selector set: the link write decides the comparison
    yield settle_case("settle self link, selector set, current compared with itself minus constant",
                      ptr_mode="self", selector=1, relation="less", velocity=4.0)
    # velocity against the floor constant, all orderings
    for name, off in (("just above floor", 1e-9), ("far above floor", 5.0), ("equals floor", 0.0),
                      ("just below floor", -1e-9), ("far below floor", -5.0)):
        yield settle_case(f"settle reached, velocity {name}", selector=1, relation="equal",
                          offset_from_floor=off)
    yield settle_case("settle reached, velocity zero", selector=1, relation="equal", velocity=0.0)
    yield settle_case("settle reached, velocity negative", selector=1, relation="equal", velocity=-3.5)
    yield settle_case("settle reached, velocity negative zero", selector=1, relation="equal",
                      velocity_bytes=d(-0.0))
    yield settle_case("settle reached, velocity nan", selector=1, relation="equal",
                      velocity_bytes=struct.pack("<Q", 0x7FF8000000000001))
    yield settle_case("settle reached, velocity infinity", selector=1, relation="equal", velocity=float("inf"))
    yield settle_case("settle reached, velocity big", selector=1, relation="equal", velocity=1e300)
    yield settle_case("settle reached, velocity denormal", selector=1, relation="equal",
                      velocity_bytes=struct.pack("<Q", 3))
    for _ in range(8):
        yield settle_case("settle reached, random velocity", selector=1, relation="equal",
                          velocity_bytes=d(rs.uniform(-100, 100)))
    # velocity words with distinct halves, to catch wrong clearing width
    yield settle_case("settle reached, velocity distinct words", selector=1, relation="equal",
                      velocity_bytes=struct.pack("<II", 0x89ABCDEF, 0x3FF00123))
    # flags: distinct starting bits, bit 1 handling in both branches
    for flags in (0, 2, 0xFFFFFFFF, 0xFFFFFFFD, 0x12345678, 0x80000002, 0x7FFFFFFD):
        yield settle_case(f"settle flags {flags:#x} mismatch", selector=1, relation="less", flags=flags)
        yield settle_case(f"settle flags {flags:#x} reached, stop", selector=1, relation="equal",
                          velocity=0.0, flags=flags)
        yield settle_case(f"settle flags {flags:#x} reached, decay", selector=1, relation="equal",
                          velocity=9.0, flags=flags)
    # random sweep
    for _ in range(40):
        relation = rs.choice(("equal", "less", "greater", "ulp"))
        yield settle_case("settle random", ptr_mode=rs.choice(("none", "other", "self")),
                          selector=rs.choice((0, 1)), ival=rs.randrange(-1 << 31, 1 << 31),
                          relation=relation, cur=rs.uniform(-1e4, 1e4),
                          velocity_bytes=d(rs.choice((0.0, rs.uniform(-10, 10), rs.uniform(0, 1e-3)))),
                          flags=rs.getrandbits(32))
