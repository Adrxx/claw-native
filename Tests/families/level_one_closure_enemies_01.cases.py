"""Cases for level_one_closure_enemies_01: Level 1 closure: Human enemy, Officer, Wolvington-shared and rope helpers."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

RAND = 0x4A3050
TRIE = 0x537668
RELEASE = 0x4F6584
COPY_RECT = 0x546D58

E_SIZE, A_SIZE, S_SIZE, B_SIZE = 0x460, 0x1C0, 0x180, 0x130


def junk(rng, size):
    return bytes(rng.getrandbits(8) | 1 for _ in range(size))


def odd(rng):
    return rng.getrandbits(31) | 1


def dbl(value):
    return struct.pack("<d", value)


def log_effect(log, tag, then=None):
    def effect(env, call):
        count = env.get(log)
        env.put(log, count + 1)
        env.put(log + 4 + 12 * count, tag, call.receiver, call.arguments[0] if call.arguments else 0)
        if then:
            then(env, call)
        return 0
    return effect


def animset(env, rng, mode, tag, flags=1):
    frame = env.object(0x40, "frame", data=junk(rng, 0x40))
    env.put(frame + 4, flags)
    env.put(frame + 8, 0)
    env.put(frame + 0xC, 0xA)
    env.put(frame + 0x10, mode)
    env.put(frame + 0x1C, tag)
    env.put(frame + 0x2C, 0)
    arr = env.object(8, "frames", words=[frame, 0])
    aset = env.object(0x20, "animset", data=junk(rng, 0x20))
    env.put(aset + 0xC, arr)
    env.put(aset + 0x10, 1)
    return aset


def install_trie(env, rng, known=("idle", "spring", "claw"), broken=()):
    keys = {"idle": b"LS_IDLE", "spring": b"LS_JUMPOFFSPRINGBOARD", "claw": b"LS_JUMPATCLAW"}
    values = {}
    leaves = {}
    for name, text in keys.items():
        text = text[:-1] + b"X" if name in broken else text
        key = env.object(len(text) + 1, "key", data=text + b"\0")
        values[name] = odd(rng)
        leaf = env.object(0x20, "leaf", fill=0)
        env.put(leaf + 8, 0)
        env.put(leaf + 0xC, key)
        env.put(leaf + 0x10, values[name])
        leaves[name] = leaf
    xnode = env.object(0x20, "xnode", fill=0)
    env.put(xnode, leaves["claw"], leaves["spring"], 57)
    root = env.object(0x20, "root", fill=0)
    env.put(root, xnode, leaves["idle"], 24)
    if "all" in known:
        env.put(TRIE + 0x18, 0)
    else:
        env.put(TRIE + 0x18, root)
    return values


def world(env, rng, mode=1, a8=0xFFFFFFFF, a40=0, slots=(1, 2, 3, 0), sets=(True, True, True, True),
          a38=None, trie=True, broken=(), gate="armed", rand_unused=False, bits=0):
    E = env.object(E_SIZE, "enemy", data=junk(rng, E_SIZE))
    B = env.object(B_SIZE, "b", data=junk(rng, B_SIZE))
    L = env.object(0x30, "l", data=junk(rng, 0x30))
    A = env.object(A_SIZE, "a", data=junk(rng, A_SIZE))
    S = env.object(S_SIZE, "s", data=junk(rng, S_SIZE))
    env.put(S + 0x40, 0x10 | bits)
    env.put(E + 0x0C, B)
    env.put(E + 0x10, L)
    env.put(E + 0x12C, A)
    env.put(E + 0x18C, mode)
    env.put(A + 8, a8)
    env.put(A + 0x38, odd(rng) if a38 is None else a38)
    env.put(A + 0x40, a40)
    env.put(A + 0x18C, S)
    env.put(A + 0x190, odd(rng))
    # animation sets in the four slots 0x344, 0x350, 0x33c, 0x378
    offsets = (0x344, 0x350, 0x33C, 0x378)
    sets_made = []
    for offset, mode_, present, n in zip(offsets, slots, sets, range(4)):
        value = animset(env, rng, mode_, 0x1000 + 0x111 * (n + 1) + rng.randrange(16), flags=(1, 5)[n & 1]) if present else 0
        env.put(E + offset, value)
        sets_made.append(value)
    values = install_trie(env, rng, known=() if trie else ("all",), broken=broken)
    # 0x48ce40 state
    W = env.object(0x190, "w", data=junk(rng, 0x190))
    V = env.object(0x30, "v", data=junk(rng, 0x30))
    env.put(W + 0x6C, V)
    env.put(0x53C9A8, 0)
    env.put(0x53C9AC, W)
    env.put(0x53C9B0, 0)
    if gate == "nowin":
        env.put(0x53C9AC, 0)
    elif gate == "busy":
        env.put(0x53C9A8, 1)
    elif gate == "novoice":
        env.put(W + 0x6C, 0)
    elif gate == "noparam":
        env.put(E + 0x420, 0)
    env.put(0x5430C4, odd(rng))
    env.put(0x537210, odd(rng))
    for off in (0x270, 0x274, 0x278, 0x27C, 0x344 - 0x344 + 0x124):
        pass
    return {"E": E, "B": B, "L": L, "A": A, "S": S, "W": W, "V": V, "sets": sets_made, "values": values}


def with_rand(env, *values):
    env.override(RAND, sequence(*values) if len(values) > 1 else returns(values[0]))


def enemy_case(label, function, rands=(0,), **options):
    def setup(env):
        pass
    return None


def make(label, function, builder, rands=(0,)):
    def setup(env):
        tokens = builder(env)
        with_rand(env, *rands)
        return tokens
    return Case(label, function, setup, receiver=lambda t: t["E"])


def cases(random_source):
    rng = random_source
    yield from step_cases(rng)
    yield from rtti_cases(rng)
    yield from simple_cases(rng)
    yield from idle_cases(rng)
    yield from spring_cases(rng)
    yield from destructor_cases(rng)
    yield from claw_cases(rng)
    yield from officer_cases(rng)


def step_cases(rng):
    def setup(first=True, second=True, same=True, rewrite=None):
        def build(env):
            log = env.object(4 + 12 * 8, "log", fill=0)
            level = env.object(0x30, "level", data=junk(rng, 0x30))
            token = env.object(0x30, "token", data=junk(rng, 0x30))
            state = 0x1000 + rng.randrange(0x100)
            env.put(level + 0x1C, state)
            callbacks = {}
            callbacks["other"] = env.stub("other", "thiscall", 0, log_effect(log, 0x33))
            if first:
                callbacks["first"] = env.stub("first", "thiscall", 0, log_effect(log, 0x11))
            if second:
                def change(env, call):
                    if rewrite == "first":
                        env.put(token + 0x14, callbacks["other"])
                callbacks["second"] = env.stub("second", "thiscall", 0, log_effect(log, 0x22, change))
            env.put(token + 0x10, level)
            env.put(token + 0x14, callbacks.get("first", 0))
            env.put(token + 0x18, callbacks.get("second", 0))
            env.put(token + 0x1C, state if same else state + 1 + rng.randrange(50))
            return {"token": token}
        return build
    for name, options in (
        ("both, state matches", {}),
        ("both, state differs", {"same": False}),
        ("first only", {"second": False}),
        ("second only: nothing runs", {"first": False}),
        ("neither", {"first": False, "second": False}),
        ("first replaced during second", {"rewrite": "first"}),
    ):
        yield Case(f"step {name}", 0x4041B0, setup(**options), receiver=lambda t: t["token"], arguments=(0x77,))


def rtti_cases(rng):
    def setup(size=8):
        def build(env):
            text = env.object(max(size, 1), "text", data=junk(rng, max(size, 1)))
            rtti = env.object(0x20, "rtti", data=junk(rng, 0x20))
            env.put(rtti + 0xC, text)
            vt = env.object(0x20, "vtable", data=junk(rng, 0x20))
            env.put(vt, rtti)  # [vtable - 4]
            this = env.object(0x10, "object", data=junk(rng, 0x10))
            env.put(this, vt + 4)
            return {"this": this}
        return build
    for size in (8, 9, 64):
        yield Case(f"rtti readable {size}", 0x4041A0, setup(size), receiver=lambda t: t["this"], arguments=(0x1234,))


def simple_cases(rng):
    flags = (0xFFFFFFFF, 0, 0xFFFFFFF6, 2, 4, 6)
    for i, a8 in enumerate(flags):
        for j, mode in enumerate((0, 2)):
            yield make(f"0x440c70 flags {a8:#x} mode {mode}", 0x440C70,
                       lambda env, a8=a8, mode=mode: world(env, rng, mode=mode, a8=a8))
    for function in (0x440350, 0x440710):
        for a8 in (0xFFFFFFFF, 0, 0x5A5A5A5E, 6):
            for slots in ((1, 2, 3, 0), (3, 1, 2, 2)):
                def build(env, a8=a8, slots=slots):
                    t = world(env, rng, a8=a8, slots=slots)
                    for o in (0x270, 0x274, 0x278, 0x27C):
                        env.put(t["E"] + o, odd(rng))
                    env.put(t["B"] + 0x124, odd(rng))
                    env.put(t["B"] + 0x50, odd(rng))
                    return t
                yield make(f"{function:#x} a8 {a8:#x} slots {slots}", function, build)
        yield make(f"{function:#x} no animation set", function,
                   lambda env: world(env, rng, sets=(False, True, True, True)))
        def wrap(env):
            t = world(env, rng)
            env.put(t["E"] + 0x27C, 0xFFFFFFF0)
            env.put(t["B"] + 0x124, 0x10)
            env.put(t["B"] + 0x50, 0x7FFFFFF0)
            return t
        yield make(f"{function:#x} wraparound", function, wrap)


def idle_cases(rng):
    for mode in (2, 0, 3):
        for a40 in (0, 2, 0xFFFFFFFD):
            for r in (0, 32, 33, 99):
                for a38 in (-1 & 0xFFFFFFFF, None):
                    def build(env, mode=mode, a40=a40, a38=a38):
                        t = world(env, rng, mode=mode, a40=a40, a38=a38)
                        for o in (0x138, 0x140):
                            env.put(t["E"] + o, odd(rng))
                        for o in (0x118, 0x120, 0x128, 0x130, 0x138, 0x140):
                            env.put(t["A"] + o, odd(rng))
                        return t
                    yield make(f"idle mode {mode} a40 {a40:#x} rand {r} a38 {a38}", 0x44F1B0, build, rands=(r,))
    for gate in ("nowin", "busy", "novoice", "noparam"):
        yield make(f"idle gate {gate}", 0x44F1B0, lambda env, gate=gate: world(env, rng, gate=gate, a38=5), rands=(10,))
    yield make("idle armed", 0x44F1B0, lambda env: world(env, rng, gate="armed", a38=5), rands=(10,))
    yield make("idle no trie", 0x44F1B0, lambda env: world(env, rng, trie=False), rands=(50,))
    yield make("idle broken key", 0x44F1B0, lambda env: world(env, rng, broken=("idle",)), rands=(50,))
    yield make("idle no animation", 0x44F1B0, lambda env: world(env, rng, sets=(True, False, True, True)), rands=(5,))
    for sentinel in (0x80000000,):
        def build(env):
            t = world(env, rng, mode=2, a40=0)
            for o in (0x118, 0x128, 0x138):
                env.put(t["A"] + o, sentinel)
            return t
        yield make("idle sentinel negation", 0x44F1B0, build, rands=(40,))
        def build2(env):
            t = world(env, rng, mode=0, a40=2)
            for o in (0x118, 0x128, 0x138):
                env.put(t["A"] + o, sentinel)
            return t
        yield make("idle sentinel restore", 0x44F1B0, build2, rands=(40,))


def spring_cases(rng):
    constants = [0.0, -0.0, 1.0, -1.0, 3.5, 1000.0, 1124999.0, 1125000.0, 1125001.0, 5e6, -77.25, float("nan"), float("inf")]
    for e40 in constants:
        for r in (49, 50):
            def build(env, e40=e40):
                t = world(env, rng, a8=0xFFFFFFFF)
                env.write(t["E"] + 0x40, dbl(e40))
                env.write(t["E"] + 0x70, dbl(rng.uniform(-500, 500)))
                env.write(t["E"] + 0x58, dbl(rng.uniform(-9, 9)))
                return t
            yield make(f"spring e40 {e40} rand {r}", 0x44F6E0, build, rands=(r,))
    for r in (0, 99, 12345):
        yield make(f"spring rand {r} random", 0x44F6E0, lambda env: (lambda t: (env.write(t["E"] + 0x40, dbl(rng.uniform(-1e6, 2e6))), t)[1])(world(env, rng)), rands=(r,))
    yield make("spring no trie", 0x44F6E0, lambda env: world(env, rng, trie=False), rands=(60,))
    yield make("spring broken key", 0x44F6E0, lambda env: world(env, rng, broken=("spring",)), rands=(60,))
    yield make("spring no animation", 0x44F6E0, lambda env: world(env, rng, sets=(True, True, False, True)), rands=(60,))


def destructor_cases(rng):
    def build(big=False, strings=True, nil=False):
        def b(env):
            E = env.object(E_SIZE, "enemy", data=junk(rng, E_SIZE))
            env.put(E, odd(rng))
            env.put(E + 0x2F4 + 8, 0x40 if big else 0x10)
            if big:
                env.put(E + 0x2F4 + 0xC, env.object(32, "bits", data=junk(rng, 32)))
            log = env.object(4 + 12 * 4, "release-log", fill=0)

            def record(env, call):
                count = env.get(log)
                env.put(log, count + 1)
                env.put(log + 4 + 12 * count, call.receiver, env.get(call.receiver), count)
                return 0
            env.override(RELEASE, record)
            for off in (0x1A4, 0x1A8):
                if nil:
                    env.put(E + off, env.get(0x52E1C8) + 0xC)
                else:
                    s = env.object(0x20, "string", data=junk(rng, 0x20))
                    env.put(s, 1)
                    env.put(E + off, s + 0xC)
            return {"E": E}
        return b
    for big in (False, True):
        for nil in (True, False):
            yield Case(f"destructor big {big} nil {nil}", 0x409F00, build(big, nil=nil), receiver=lambda t: t["E"])
            for flag in (0, 1, 0xFE, 0xFF):
                yield Case(f"scalar destructor big {big} nil {nil} flag {flag:#x}", 0x44C7C0, build(big, nil=nil),
                           receiver=lambda t: t["E"], arguments=(flag,))


def claw_cases(rng):
    def make_claw(label, dx, dy, vel, dz=0.0, mode=1, a40=0, count=0x40, e40c=True, flag=1,
                  fx=0.25, fy=0.5, bitptr=False, rand=None):
        def build(env):
            t = world(env, rng, mode=mode, a40=a40)
            E = t["E"]
            P = env.object(0x60, "player", data=junk(rng, 0x60))
            px, py = rng.randrange(-400, 400), rng.randrange(-400, 400)
            env.put(P + 0x4C, px & 0xFFFFFFFF, py & 0xFFFFFFFF) if False else None
            env.write(P + 0x4C, struct.pack("<i", px))
            env.write(P + 0x50, struct.pack("<i", py))
            env.put(0x537E88, P)
            env.write(E + 0x68, dbl(px + dx + fx))
            env.write(E + 0x70, dbl(py + dy + fy))
            env.write(E + 0x38, dbl(vel[0]))
            env.write(E + 0x40, dbl(vel[1]))
            env.write(E + 0x48, dbl(vel[2]))
            env.write(E + 0x78, dbl(dz))
            log = env.object(4 + 12 * 4, "log", fill=0)
            vt = env.object(0x60, "vtable", data=junk(rng, 0x60))
            env.put(vt + 0x48, env.stub("virtual", "thiscall", 0, log_effect(log, 0x44)))
            env.put(E, vt)
            env.put(E + 0x2FC, count)
            if count > 0x20:
                env.put(E + 0x300, env.object(8, "word", data=junk(rng, 8)))
            else:
                env.put(E + 0x300, odd(rng))
            Z = env.object(0x90, "z", data=junk(rng, 0x90))
            env.put(Z + 0x78, 0)
            Y = env.object(0x30, "y", data=junk(rng, 0x30))
            env.put(Y + 0x10, Z)
            X = env.object(0x30, "x", data=junk(rng, 0x30))
            env.put(X + 0x10, Y)
            env.put(E + 0x40C, X if e40c else 0)
            env.put(0x532C0C, flag)
            env.put(0x532C10, odd(rng))
            return t
        return Case(label, 0x44E120,
                    lambda env: (lambda t: (env.override(RAND, returns(0)), t)[1])(build(env)),
                    receiver=lambda t: t["E"])
    # far branch: three population classes
    for count in (0, 1, 2, 3, 0x20, 0x21, 0x80):
        yield make_claw(f"claw far count {count}", 1000, 0, (0.3, 0.2, 0.1), count=count)
    for dx, dy in ((250, 1), (-250, 1), (0, 251), (251, 0), (-200, 200), (65536 + 300, 0)):
        yield make_claw(f"claw boundary far {dx},{dy}", dx, dy, (0.3, 0.2, 0.1), count=5)
    for dx, dy in ((250, 0), (0, -250), (-176, 177), (65536, 0), (0, 0), (-3, 4)):
        yield make_claw(f"claw boundary near {dx},{dy}", dx, dy, (0.3, 0.2, 0.1))
    # near branch; floating point classes
    velocity = {
        "zero velocity": (0.0, 0.0, 0.0),
        "slow": (0.3, 0.2, 0.1),
        "fast": (3.0, 2.0, 1.0),
        "opposed": (-3.0, -2.0, -1.0),
    }
    for name, vel in velocity.items():
        for dx, dy, dz in ((-100, -20, 7.5), (100, 20, -7.5), (-9, 3, 0.0)):
            for mode in (2, 0):
                for a40 in (0, 2):
                    yield make_claw(f"claw near {name} {dx},{dy},{dz} mode {mode} a40 {a40}", dx, dy, vel, dz, mode, a40)
    for e40c in (False, True):
        for flag in (0, 1):
            yield make_claw(f"claw near e40c {e40c} flag {flag}", -50, 10, (1.0, 0.5, 0.25), 2.0, e40c=e40c, flag=flag)
    for i in range(12):
        vel = tuple(rng.uniform(-4, 4) for _ in range(3))
        yield make_claw(f"claw random near {i}", rng.randrange(-150, 150), rng.randrange(-100, 100), vel,
                        rng.uniform(-30, 30), mode=rng.choice((0, 2)), a40=rng.choice((0, 2)),
                        fx=rng.random(), fy=rng.random())
    for i in range(6):
        vel = tuple(rng.uniform(-0.5, 0.5) for _ in range(3))
        yield make_claw(f"claw random slow {i}", rng.randrange(-150, 0), rng.randrange(-100, 100), vel,
                        rng.uniform(-30, 30))
    for i in range(6):
        yield make_claw(f"claw random far {i}", rng.choice((-1, 1)) * rng.randrange(300, 3000), rng.randrange(-100, 100),
                        (1.0, 1.0, 1.0), count=rng.choice((0, 1, 2, 9, 0x21, 0x40)))


def officer_cases(rng):
    def build(env):
        t = world(env, rng)
        q = env.object(0x40, "q", data=junk(rng, 0x40))
        m0 = env.object(0x40, "m0", data=junk(rng, 0x40))
        env.put(t["A"] + 0xC, q)
        env.put(q + 0x28, m0)
        count = 7
        buckets = env.object(4 * count, "buckets", fill=0)
        for key in (b"LEVEL_OFFICER_00340017", b"LEVEL_OFFICER_00340018"):
            h = 0
            for c in key:
                h = (h * 33 + c) & 0xFFFFFFFF
            text = env.object(len(key) + 1, "key", data=key + b"\0")
            node = env.object(0x10, "node", fill=0)
            env.put(node, env.get(buckets + 4 * (h % count)), 0, text, odd(rng))
            env.put(buckets + 4 * (h % count), node)
        env.put(m0 + 0x14, buckets)
        env.put(m0 + 0x18, count)

        def copy_rect(env, call):
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            return 1
        env.override(COPY_RECT, copy_rect)
        return t
    for r in (0, 49, 50, 99):
        yield make(f"officer rand {r}", 0x463310, build, rands=(r, 10))
