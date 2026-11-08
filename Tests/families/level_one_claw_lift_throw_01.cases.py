"""Cases for level_one_claw_lift_throw_01: Level 1 Claw lift and throw states.

The world is one Claw actor, a state array ("P"), the held object with its body and bit set, a scene with two
name maps, an input block and a tile manager whose tile map is empty.  Every original callee runs on this world;
the only stand-ins are the held body's vtable slots (they record their receiver and argument into a log object)
and the allocator.  Coverage does not depend on the random seed: every sweep uses its own fixed-seed generator and
`random_source` only adds extra worlds at the end.
"""
import math
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, reallocate


def dirty_malloc(env, call):
    return env.object(call.arguments[0], name="allocation", fill=0xA7)


def dirty_realloc(env, call):
    pointer, size = call.arguments[0], call.arguments[1]
    if not pointer:
        return env.object(size, name="allocation", fill=0xA7)
    moved = env.object(size, name="allocation", fill=0xA7)
    env.write(moved, env.read(pointer, min(env.spans[pointer], size)))
    env.release(pointer)
    return moved


LIFT = 0x41A850
THROW = 0x41B1F0
HOLD = 0x41B280
START = 0x41DC50
SET_CALLBACK = 0x421010
SET_BIT = 0x4DBD20
RESIZE = 0x4DC6D0
MALLOC = 0x4A48E0
REALLOC = 0x4A9070

G_INPUT = 0x537204
G_DT = 0x5430C4
G_COUNT = 0x53720C
G_C0C = 0x532C0C
G_E58 = 0x534E58
G_E60 = 0x534E60
G_DB8 = 0x534DB8
G_DC0 = 0x534DC0

VEL = (0x534DE0, 0x534DE8, 0x534DF0)
POS = (0x534DF8, 0x534E00, 0x534E08)
ACC = (0x534DC8, 0x534DD0, 0x534DD8)
LO = (0x534E10, 0x534E18, 0x534E20)
HI = (0x534E28, 0x534E30, 0x534E38)
DEL = (0x534E40, 0x534E48, 0x534E50)
LIM = (0x534E78, 0x534E80, 0x534E88)
CLP = (0x534E90, 0x534E98, 0x534EA0)

NAN = (0, 0x7FF80000)
INF = (0, 0x7FF00000)
NINF = (0, 0xFFF00000)
INT_MIN = -0x80000000
INT_MAX = 0x7FFFFFFF
DIR_A = 0x1000000   # first direction bit of the input flags
DIR_B = 0x2000000   # second direction bit
NAMES = ("LIFTWALK", "LIFT2", "FALL", "THROW", "STAND", "LIFT", "DUCKLIFT")


def dwords(value):
    if isinstance(value, tuple):
        return value
    return struct.unpack("<II", struct.pack("<d", value))


def blob(size, seed):
    """Distinct non-pointer filler, so a field the function reads that a case forgot to set shows up."""
    return b"".join(struct.pack("<I", (0x40000000 + (seed << 20) + i * 0x101 + seed) & 0xFFFFFFFF)
                    for i in range(size // 4))


def make_frame(env, ret, interval):
    frame = env.object(0x40, "anim-frame", data=blob(0x40, 11))
    env.put(frame + 0x04, 1)              # not a sound frame
    env.put(frame + 0x08, 0)              # no position command
    env.put(frame + 0x0C, 9)              # terminal frame: the animation engine stops here
    env.put(frame + 0x10, 0)
    env.put(frame + 0x18, interval)
    env.put(frame + 0x1C, ret)
    env.put(frame + 0x2C, 0)
    return frame


def make_seq(env, ret, interval):
    frame = make_frame(env, ret, interval)
    array = env.object(4, "anim-frames", words=[frame])
    seq = env.object(0x20, "anim-sequence", data=blob(0x20, 12))
    env.put(seq + 0x0C, array)
    env.put(seq + 0x10, 1)
    return seq


def make_map(env, at, entries):
    """A string map at `at`: +4 bucket table, +8 bucket count; node = next, ?, key, value."""
    count = 11
    table = env.object(4 * count, "buckets", fill=0)
    buckets = [0] * count
    for name, value in entries.items():
        text = ("CLAW_" + name).encode()
        key = env.object(len(text) + 1, "key", data=text + b"\0")
        h = 0
        for ch in text:
            h = (h * 0x21 + ch) & 0xFFFFFFFF
        node = env.object(16, "node", words=[buckets[h % count], 0x1234, key, value])
        buckets[h % count] = node
    env.put(table, *buckets)
    env.put(at + 4, table, count)


def make_bits(env, at, nbits, word, owner):
    """Bit set at `at`: +4 owner, +8 bit count, +0xc inline word (up to 32 bits) or pointer to the words."""
    env.put(at + 4, owner, nbits)
    if nbits > 0x20:
        words = (nbits + 31) // 32
        block = env.object(max(4, words * 4), "bit-words", data=blob(max(4, words * 4), 23))
        env.put(at + 0xC, block)
    else:
        env.put(at + 0xC, word)


def recorder(log, slot, result):
    def effect(env, call):
        n = env.calls_so_far(call.function)
        env.put(log + slot * 0x20 + 8 * ((n - 1) % 4), call.receiver,
                call.arguments[0] if call.arguments else 0xFEED0000 + n)
        return result
    return effect


def axis_defaults():
    g = {}
    for i in range(3):
        g[VEL[i]] = (10.1, -8.1, 12.1)[i]
        g[POS[i]] = (10.0, 20.0, 30.0)[i]
        g[ACC[i]] = (-3.0, 9.1, -6.6)[i]
        g[LIM[i]] = (1.25, 0.75, 2.5)[i]
        g[LO[i]] = (-400.0, -300.0, -200.0)[i]
        g[HI[i]] = (500.0, 350.0, 250.0)[i]
        g[CLP[i]] = 1e9
        g[DEL[i]] = (123.5, 456.25, 789.125)[i]
    g[G_E60] = 0.25
    g[G_DB8] = 3.5
    g[G_DC0] = 99.0
    return g


DEFAULTS = dict(
    in4=0, in8=0, inc=0xA5A5F00F, dt=16, count=16, e58=1, c0c=1, c10=0x1234,
    x=300, y=500, cflags=0, c40=0x5A5A0034, c64=7, state=7, partner=None, tm_limit=(0x3FFF, 0x3FFF),
    steps=(3, 4), rect=(-6, -20, 8, 4), flipvals=None, a8=False, a14=0, a18=0, a1c=0, a20=1, a24=1,
    a28=0x3F800000, a104=0x6D6D, c148=0x1111, c14c=0x2222, c16c=0x3333, c174=0x4444, c1b0=0x3F800000, c19c=None, c1a4=None,
    names=NAMES, rets={}, ivs={}, grunt=True, y30=0,
    P0=0, P1=0, P2=0, P3=0, P8=0x77, Pf=0, P10=0x55, prect=(31, 32, 33, 34), timer=100000, counter=0,
    P45=0x66, P46=0x88, P48=0x99, P3f=0xAA, P49=0, P4b=True, hflags=0, bits=(0, 0x5A5A5A5A), b20=1, b14=0x11223344,
    b50=(0x1357, 0x2468), c64h=3, c8h=0x10, q=None, g=None,
)


def build(env, c):
    t = {}
    log = env.object(0x100, "log", fill=0)
    inp = env.object(0x20, "input", data=blob(0x20, 1))
    env.put(inp + 4, c["in4"], c["in8"], c["inc"])
    env.put(G_INPUT, inp)
    env.put(G_DT, c["dt"])
    env.put(G_COUNT, c["count"])
    env.put(G_C0C, c["c0c"], c["c10"])
    env.put(G_E58, c["e58"])
    env.put(0x534E60, 0x9E3779B1, 0x85EBCA6B, 0xC2B2AE35, 0x27D4EB2F, 0x165667B1, 0xD3A2646C)
    env.override(MALLOC, dirty_malloc)
    env.override(REALLOC, dirty_realloc)
    values = axis_defaults()
    values.update(c["g"] or {})
    for address, value in values.items():
        env.put(address, *dwords(value))

    owner = env.object(0x20, "platform-owner", fill=0)
    scene = env.object(0x40, "scene", data=blob(0x40, 2))
    tm = env.object(0x80, "tile-manager", data=blob(0x80, 3))
    tiles = env.object(0x40, "tile-table", fill=0)
    tilemap = env.object(0xA0, "tile-map", data=blob(0xA0, 4))
    cells = env.object(4 * 16 * 16, "map-data", data=b"\xee" * (4 * 16 * 16))
    rows = env.object(4 * 16, "map-rows", words=[16 * r for r in range(16)])
    env.put(tilemap + 0x20, cells, rows)
    env.put(tilemap + 0x30, 128, 128)
    env.put(tilemap + 0x8C, 3, 3)
    env.put(tm + 0x0C, scene)
    env.put(tm + 0x4C, tiles)
    env.put(tm + 0x5C, tilemap)
    env.put(tm + 0x64, *c["tm_limit"])
    xs = env.object(0x40, "map-owner-x", data=blob(0x40, 5))
    ys = env.object(0x40, "map-owner-y", data=blob(0x40, 6))
    env.put(scene + 0x08, owner)
    env.put(scene + 0x24, tm, ys, xs)
    entries = {}
    for name in c["names"]:
        entries[name] = make_seq(env, c["rets"].get(name, 3), c["ivs"].get(name, 2))
    make_map(env, xs + 0x10, entries)
    grunt = {}
    if c["grunt"]:
        far = env.object(0x80, "grunt-far", data=blob(0x80, 7))
        env.put(far + 0x78, 0)
        mid = env.object(0x20, "grunt-mid", data=blob(0x20, 8))
        env.put(mid + 0x10, far)
        top = env.object(0x20, "grunt-top", data=blob(0x20, 9))
        env.put(top + 0x10, mid)
        grunt["GRUNTTHROW"] = top
    make_map(env, ys + 0x10, grunt)
    env.put(ys + 0x30, c["y30"])

    claw = env.object(0x1D0, "claw", data=blob(0x1D0, 10))
    p2 = env.object(0x40, "claw-extra", data=blob(0x40, 13))
    env.put(claw + 0x08, c["cflags"])
    env.put(claw + 0x0C, scene)
    env.put(claw + 0x40, c["c40"])
    env.put(claw + 0x4C, c["x"], c["y"])
    env.put(claw + 0x64, c["c64"])
    partner = 0
    if c["partner"] is not None:
        partner = env.object(0x180, "partner", data=blob(0x180, 14))
        env.put(partner + 0x158, *c["partner"])
    env.put(claw + 0x80, partner)
    env.put(claw + 0xCC, c["state"])
    env.put(claw + 0xDC, c["steps"][0])
    env.put(claw + 0xE0, c["steps"][1])
    env.put(claw + 0x104, c["a104"])
    flips = c["flipvals"] or [-6, -20, 8, 4, 11, 12, 13, 14, 21, 22, 23, 24]
    env.put(claw + 0x118, *c["rect"])
    env.put(claw + 0x128, *flips[4:8])
    env.put(claw + 0x138, *flips[8:12])
    env.put(claw + 0x148, c["c148"], c["c14c"])
    env.put(claw + 0x16C, c["c16c"])
    env.put(claw + 0x174, c["c174"])
    q = 0
    if c["q"] is not None:
        q = env.object(0x70, "claw-link", data=blob(0x70, 15))
        link = env.object(0xC0, "claw-link-target", data=blob(0xC0, 16))
        env.put(link + 0xB0, c["q"][2])
        env.put(q + 0x14, link)
        env.put(q + 0x64, c["q"][0])
        env.put(q + 0x68, c["q"][1])
    env.put(claw + 0x170, q)
    # the animation player embedded at claw + 0x188
    env.put(claw + 0x18C, claw)
    seq0 = make_seq(env, 4, 1) if c["a8"] else 0
    env.put(claw + 0x190, seq0)
    if c["a8"]:
        env.put(claw + 0x194, env.get(env.get(seq0 + 0x0C)))
    env.put(claw + 0x19C, c["a14"] if c["c19c"] is None else c["c19c"])
    env.put(claw + 0x1A0, c["a18"])
    env.put(claw + 0x1A4, c["a1c"] if c["c1a4"] is None else c["c1a4"])
    env.put(claw + 0x1A8, c["a20"], c["a24"])
    env.put(claw + 0x1B0, c["a28"])

    P = env.object(0x180, "state-array", data=blob(0x180, 17))
    env.put(P + 0x00, c["P0"], c["P1"], c["P2"], c["P3"])
    env.put(P + 0x20, c["P8"])
    env.put(P + 0x3C, c["Pf"])
    env.put(P + 0x40, c["P10"])
    env.put(P + 0xD8, *c["prect"])
    env.put(P + 0xF0, c["timer"], c["counter"])
    env.put(P + 0xFC, c["P3f"])
    env.put(P + 0x114, c["P45"], c["P46"])
    env.put(P + 0x120, c["P48"])
    seq49 = make_seq(env, 6, 1) if c["P49"] else 0
    env.put(P + 0x124, seq49)

    H = env.object(0x180, "held", data=blob(0x180, 18))
    link = env.object(0x40, "held-link", data=blob(0x40, 19))
    B = env.object(0x320, "held-body", data=blob(0x320, 20))
    C = env.object(0x80, "held-owner", data=blob(0x80, 21))
    vt = env.object(0xB0, "vtable", data=blob(0xB0, 22))
    for offset, argc, slot in ((0x80, 1, 0), (0x84, 0, 1), (0x88, 0, 2), (0xA0, 0, 3)):
        env.put(vt + offset, env.stub(f"body-slot-{offset:#x}", "thiscall", argc, recorder(log, slot, 0x1000 + slot)))
    env.put(H + 0x6C, link)
    env.put(H + 0x164, c["hflags"])
    env.put(link + 0x18, B)
    env.put(B + 0x00, vt)
    env.put(B + 0x0C, C)
    env.put(B + 0x14, c["b14"])
    env.put(B + 0x20, c["b20"])
    env.put(B + 0x50, *c["b50"])
    env.put(C + 0x08, c["c8h"])
    env.put(C + 0x64, c["c64h"])
    bits_owner = env.object(0x20, "bit-owner", fill=0)
    env.put(bits_owner + 0x0C, 4)
    make_bits(env, B + 0x2F4, c["bits"][0], c["bits"][1], bits_owner)
    env.put(P + 0x12C, H if c["P4b"] else 0)
    t.update(claw=claw, p2=p2, P=P, H=H, B=B, log=log, bits=B + 0x2F4, owner=bits_owner)
    return t


def merged(options):
    c = dict(DEFAULTS)
    c.update(options)
    return c


def lift(label, **options):
    c = merged(options)
    return Case(label, LIFT, lambda env: build(env, c),
                arguments=(lambda t: t["claw"], lambda t: t["p2"], lambda t: t["P"]))


def hold(label, **options):
    c = merged(options)
    return Case(label, HOLD, lambda env: build(env, c),
                arguments=(lambda t: t["claw"], lambda t: t["p2"], lambda t: t["P"]))


def throw(label, **options):
    c = merged(options)
    return Case(label, THROW, lambda env: build(env, c),
                arguments=(lambda t: t["claw"], lambda t: t["p2"], lambda t: t["P"]))


def start(label, **options):
    c = merged(options)
    return Case(label, START, lambda env: build(env, c),
                arguments=(lambda t: t["claw"], lambda t: t["p2"], lambda t: t["P"], lambda t: t["H"]))


def noise(rng, state4=False):
    """Fields that should not matter much but must be carried through unchanged or negated."""
    flips = [rng.choice([-1, 1]) * rng.randrange(1, 90) for _ in range(12)]
    if rng.random() < 0.35:
        flips[4] = INT_MIN
        flips[8] = INT_MIN
    left = INT_MIN if (not state4 and rng.random() < 0.3) else -rng.randrange(1, 30)
    out = dict(c40=rng.getrandbits(32), x=rng.randrange(-200, 900), y=rng.randrange(-100, 1200),
               flipvals=flips, rect=(left, -rng.randrange(8, 40), rng.randrange(4, 40), rng.randrange(2, 30)),
               prect=tuple(rng.randrange(-300, 300) for _ in range(4)), c64=rng.randrange(0, 60),
               c148=rng.getrandbits(32) | 1, c14c=rng.getrandbits(32) | 1, a104=rng.getrandbits(32) | 1,
               P45=rng.getrandbits(32) | 1, P46=rng.getrandbits(32) | 1, P48=rng.getrandbits(32) | 1,
               P3f=rng.getrandbits(32) | 1, P10=rng.getrandbits(32) | 1, P8=rng.getrandbits(32) | 1)
    return out


# ---- physics tables -------------------------------------------------------------------------------------
VS = {"IN": (10.0, -8.0, 12.0), "HI": (900.0, 600.0, 700.0), "LO": (-900.0, -600.0, -700.0)}
COMBOS = [(s, p, k) for s in ("IN", "HI", "LO") for p in ("MID", "OVER", "UNDER") for k in (0, 1)]


def axis_values(i, combo, acc=None):
    s, p, k = combo
    g = {VEL[i]: VS[s][i]}
    g[POS[i]] = {"MID": (10.0, 20.0, 30.0)[i], "OVER": (500.0, 350.0, 250.0)[i] + 5.0,
                 "UNDER": (-400.0, -300.0, -200.0)[i] - 5.0}[p]
    if k:
        g[CLP[i]] = -1000.0 if s == "LO" else 1.0
    if acc is not None:
        g[ACC[i]] = acc
    return g


def physics_world(combos, **extra):
    g = {}
    for i, combo in enumerate(combos):
        g.update(axis_values(i, combo))
    g.update(extra.pop("g", {}))
    options = dict(in8=DIR_A, P2=1, e58=0, g=g)
    options.update(extra)
    return options


def exact_world(velocity, limit, position, low=-1000.0, high=1000.0, accel=0.0, clamp=1e9, e60=0.0, axis=0):
    """dt is exactly 1.0 and the acceleration is zero, so the step equals the velocity and ties are exact."""
    g = {VEL[axis]: velocity, LIM[axis]: limit, POS[axis]: position, LO[axis]: low, HI[axis]: high,
         ACC[axis]: accel, CLP[axis]: clamp, G_E60: e60}
    return dict(in8=DIR_A, P2=1, e58=0, count=1000, g=g)


def cases(random_source):
    rng = random.Random(0x7A11F7)
    n = 0

    def label(text):
        nonlocal n
        n += 1
        return f"{text} #{n}"

    # ---- 0x41a850, part one: the direction inputs --------------------------------------------------------
    for in8 in (DIR_A, DIR_B, DIR_A | DIR_B):
        for p0 in (0, 1):
            for p3 in (0, 1):
                for de0 in (30.0, -30.0, 5.7, NAN):
                    if de0 is NAN and p3:
                        continue
                    yield lift(label(f"lift direction in8={in8:#x} p0={p0} p3={p3} de0={de0}"),
                               in8=in8, P2=1, P0=p0, P3=p3, g={VEL[0]: de0}, **noise(rng))
        yield lift(label(f"lift direction in8={in8:#x} p0=7"), in8=in8, P2=1, P0=7, P3=0, g={VEL[0]: 5.7}, **noise(rng))
        yield lift(label(f"lift direction in8={in8:#x} p0=7 p3=3"), in8=in8, P2=1, P0=7, P3=3, g={VEL[0]: 30.0}, **noise(rng))
    for in8 in (DIR_A, DIR_B):
        for bit1 in (0, 2):
            for p3 in (0, 1):
                yield lift(label(f"lift flag bit in8={in8:#x} c40={bit1} p3={p3}"), in8=in8, P2=1, P0=1 - (in8 == DIR_B),
                           P3=p3, g={VEL[0]: 7.7}, **dict(noise(rng), c40=0x5A5A5A58 | bit1))
    for in8, p2 in ((0, 0), (0, 1), (DIR_A, 0), (DIR_B, 0), (DIR_A | DIR_B, 0), (0x80000000 | 0x4000000, 1)):
        for p0, p3, de0 in ((0, 0, 7.7), (1, 1, -30.0)):
            yield lift(label(f"lift idle direction in8={in8:#x} p2={p2} p0={p0} p3={p3}"),
                       in8=in8, P2=p2, P0=p0, P3=p3, g={VEL[0]: de0}, **noise(rng))
    # ---- the animation player's answer -------------------------------------------------------------------
    anims = [
        ("absent", dict(a8=False)),
        ("count ret 1", dict(a8=True, a14=1, a18=0, a24=1, a1c=1)),
        ("count ret 5", dict(a8=True, a14=1, a18=0, a24=5, a1c=0)),
        ("count n3 ret 1", dict(a8=True, a14=3, a18=0, a24=1, a1c=7)),
        ("timed ret 1", dict(a8=True, a14=50, a18=1, a24=1, a1c=1)),
        ("timed ret 5", dict(a8=True, a14=50, a18=1, a24=5, a1c=1)),
        ("timed elapsed ret 1", dict(a8=True, a14=10, a18=1, a24=9, a20=1, a1c=1)),
        ("timed elapsed ret 5", dict(a8=True, a14=10, a18=1, a24=9, a20=5, a1c=1)),
        ("done ret 1", dict(a8=True, a14=0, a18=0, a24=9, a20=1, a1c=1)),
        ("done ret 5", dict(a8=True, a14=0, a18=1, a24=9, a20=5, a1c=1)),
    ]
    for name, anim in anims:
        for e58 in (0, 1):
            for in8 in (DIR_A, 0):
                if in8 == 0 and e58 == 0:
                    continue
                options = physics_world([("IN", "MID", 0)] * 3) if in8 else dict(P2=0)
                options.update(anim)
                options.update(e58=e58, in8=in8, dt=10)
                options.update(noise(rng))
                yield lift(label(f"lift animation {name} e58={e58} in8={in8:#x}"), **options)
    # lookups that succeed and return 1 or something else
    for walk_ret in (1, 8):
        for in8 in (DIR_A, DIR_B):
            for e58 in ((0, 1) if in8 == DIR_A else (0,)):
                options = physics_world([("IN", "MID", 0)] * 3, rets={"LIFTWALK": walk_ret}, ivs={"LIFTWALK": 0},
                                        P3=1, e58=e58)
                options["in8"] = in8
                if in8 == DIR_B:
                    options["g"] = dict(options["g"])
                options.update(noise(rng))
                yield lift(label(f"lift walk lookup ret {walk_ret} in8={in8:#x} e58={e58}"), **options)
    # names that are not in the map leave the player alone
    for in8 in (DIR_A, DIR_B):
        yield lift(label(f"lift no names in8={in8:#x}"), in8=in8, P2=1, P3=1, names=(), **noise(rng))
    # ---- the three axes of the integrator ------------------------------------------------------------------
    for j in range(len(COMBOS)):
        combos = [COMBOS[j], COMBOS[(j + 7) % 18], COMBOS[(j + 13) % 18]]
        yield lift(label(f"lift physics {combos[0]} {combos[1]} {combos[2]}"), **physics_world(combos), **noise(rng))
    for j in range(0):
        combos = [COMBOS[(5 * j + 2) % 18], COMBOS[(3 * j + 11) % 18], COMBOS[(7 * j + 4) % 18]]
        zero = {ACC[0]: 0.0, ACC[1]: 0.0, ACC[2]: 0.0}
        yield lift(label(f"lift physics no acceleration {combos[0]} {combos[1]} {combos[2]}"),
                   **physics_world(combos, g=zero), **noise(rng))
    # exact ties on every axis: step equals the limit, position equals a bound
    for axis in range(3):
        for velocity, limit in ((0.5, 0.5), (-0.5, 0.5), (0.5, 0.25), (-0.5, 0.25)):
            yield lift(label(f"lift tie axis {axis} v={velocity} lim={limit}"),
                       **exact_world(velocity, limit, 10.0, axis=axis), **noise(rng))
        for position, high in ((10.0, 10.5), (10.0, 10.25)):
            yield lift(label(f"lift tie axis {axis} pos={position} high={high}"),
                       **exact_world(0.5, 2.0, position, low=-10.5, high=high, axis=axis), **noise(rng))
        for position, low in ((-10.0, -10.5), (-10.0, -9.75)):
            yield lift(label(f"lift tie axis {axis} pos={position} low={low}"),
                       **exact_world(-0.5, 2.0, position, low=low, high=1000.0, axis=axis), **noise(rng))
        for clamp, velocity in ((0.5, 0.5), (0.5, 0.75), (-0.5, -0.5)):
            yield lift(label(f"lift tie axis {axis} clamp={clamp} v={velocity}"),
                       **exact_world(velocity, 5.0, 10.0, clamp=clamp, axis=axis), **noise(rng))
    # acceleration with exact binary values
    for axis in range(3):
        for accel in (2.0,):
            yield lift(label(f"lift exact acceleration axis {axis} a={accel}"),
                       **exact_world(1.5, 0.75, 10.0, accel=accel, axis=axis), **noise(rng))
    # not a number and infinity in the integrator
    for axis in range(3):
        for bad in (NAN, INF, NINF):
            options = physics_world([("IN", "MID", 0)] * 3)
            options["g"][VEL[axis]] = bad
            yield lift(label(f"lift physics axis {axis} velocity {bad}"), **options, **noise(rng))
    options = physics_world([("IN", "MID", 0)] * 3)
    options["g"][POS[1]] = NAN
    yield lift(label("lift physics y position nan"), **options, **noise(rng))
    options = physics_world([("IN", "MID", 0)] * 3)
    options["g"][LIM[2]] = NAN
    yield lift(label("lift physics z limit nan"), **options, **noise(rng))
    options = physics_world([("IN", "MID", 0)] * 3)
    options["g"][HI[0]] = NAN
    yield lift(label("lift physics x high bound nan"), **options, **noise(rng))
    # ---- the fractional position update -------------------------------------------------------------------
    targets = [0.0, -0.0, 0.5, -0.5, 1.0, -1.0, 2.75, -2.75, 3.9999, -3.9999, 0.999, -0.999, 7.0, -7.0, 4.5, -4.5,
               2.0 ** 31, -(2.0 ** 31), 1e10, -1e10, 2147483647.5]
    for target in targets:
        e60 = rng.choice([0.0, 0.75, -0.75, 0.999, -0.999, 0.5, -0.5])
        yield lift(label(f"lift position update step {target} frac {e60}"),
                   **exact_world(target, 1e12, 0.0, low=-1e12, high=1e12, e60=e60), **noise(rng))
    for k in range(4):
        target = rng.uniform(-25.0, 25.0)
        e60 = rng.uniform(-0.99, 0.99)
        yield lift(label(f"lift position update random {k}"),
                   **exact_world(target, 1e12, 0.0, low=-1e12, high=1e12, e60=e60), **noise(rng))
    # ---- a partner that carries the Claw -------------------------------------------------------------------
    for cflags in (0, 0x10, 0x30):
        for partner in (None, (13, -17), (-4000, 4001)):
            for e58 in (0, 1):
                options = physics_world([("IN", "MID", 0)] * 3) if e58 == 0 else {}
                options.update(cflags=cflags, partner=partner, e58=e58)
                if cflags == 0x20 and partner is None:
                    continue
                yield lift(label(f"lift partner flags={cflags:#x} {partner} e58={e58}"), **options, **noise(rng))
    # ---- falling: the state after the tile manager call is 4 ----------------------------------------------------
    for pf in (0, 1, 7, 8, 9, 10, 11, 0x11, 0x12, 0x13, 0x7FFFFFFF):
        for p0 in ((0, 1) if pf in (0, 8) else (pf & 1,)):
            yield lift(label(f"lift fall Pf={pf:#x} P0={p0}"), state=4, Pf=pf, P0=p0, P1=pf & 1, P49=bool(pf & 2),
                       **noise(rng, True))
    for p49 in (False, True):
        for names in (NAMES, ()):
            yield lift(label(f"lift fall FALL entry p49={p49} names={len(names)}"), state=4, Pf=9, P49=p49, names=names,
                       **noise(rng, True))
    for de0 in (0.0, -0.0, 7.5, -7.5, NAN, INF, NINF):
        for b20 in (INT_MIN, -1, 0, 1, 2):
            if de0 not in (7.5, -7.5, 0.0) and b20 != 1:
                continue
            yield lift(label(f"lift fall velocity {de0} body limit {b20}"), state=4, in8=DIR_A, P2=1, P3=0, e58=1,
                       Pf=0, g={VEL[0]: de0}, b20=b20, **noise(rng, True))
    for bits in ((0, 0x1), (1, 0xF0F0F0F1), (5, 0x0), (32, 0x80000000), (33, 0), (64, 0), (160, 0)):
        for pf in ((0, 8) if bits[0] in (0, 33) else (8,)):
            yield lift(label(f"lift fall bits {bits[0]} Pf={pf}"), state=4, Pf=pf, bits=bits, in8=DIR_A, P2=1,
                       g={VEL[0]: 5.0}, **noise(rng, True))
    for dx, partner in ((0, None), (9, (9, 0)), (-9, (-9, 0)), (0, (0, 30)), (5, (5, -30))):
        for flags in (0, 0x10):
            yield lift(label(f"lift fall moving {dx} {partner} flags {flags:#x}"), state=4, cflags=flags, partner=partner,
                       Pf=0, **noise(rng, True))
    # physics while falling
    for j in (0, 5, 11):
        combos = [COMBOS[j], COMBOS[(j + 7) % 18], COMBOS[(j + 13) % 18]]
        yield lift(label(f"lift fall physics {j}"), state=4, Pf=0, **physics_world(combos), **noise(rng, True))
    # ---- the second lift animation and the throw ---------------------------------------------------------------
    for c1a4 in (0, 5):
        for c19c in (0, 3):
            scenarios = [(0, 0, 0, 0.0), (0, 1, 0, 0.0), (0, 1, 1, 0.0)]
            for de0 in (0.0, -0.0, 7.5, NAN):
                for p3 in (0, 1):
                    if de0 in (-0.0, 7.5) and p3 or de0 is NAN and p3:
                        continue
                    scenarios.append((DIR_A, 1, p3, de0))
            scenarios.append((DIR_A, 0, 0, 7.5))
            for in8, p2, p3, de0 in scenarios:
                yield lift(label(f"lift second animation 1a4={c1a4} 19c={c19c} in8={in8:#x} p2={p2} p3={p3} de0={de0}"),
                           in8=in8, P2=p2, P3=p3, c1a4=c1a4, c19c=c19c, g={VEL[0]: de0}, **noise(rng))
    for in4 in (0, 1, 2, 0x20, 0x22, 0x40, 0xDD, 0x1F00):
        yield lift(label(f"lift throw input {in4:#x}"), in8=DIR_A, P2=1, P3=0, in4=in4, g={VEL[0]: 6.5},
                   q=(0x2C, 0x2C, 0xABC), **noise(rng))
    for in4 in (0x22, 0xFF):
        yield lift(label(f"lift throw input {in4:#x} idle"), in8=0, P2=0, in4=in4, **noise(rng))
    # ---- the throw timer ----------------------------------------------------------------------------------------
    for dt, timer in ((5, 6), (5, 5), (5, 4), (0, 0), (0, 1), (1, 0), (INT_MAX, 0x80000000), (0x80000000, INT_MAX),
                      (0xFFFFFFFF, 0xFFFFFFFE), (0xFFFFFFFE, 0xFFFFFFFF), (16, 100000), (0x80000000, 0x80000000)):
        yield lift(label(f"lift timer dt={dt:#x} timer={timer:#x}"), dt=dt, timer=timer, counter=0x1234,
                   P1=(dt & 1), P49=bool(timer & 1), **noise(rng))
    for bits in ((0, 0x1), (1, 0xF0F0F0F0), (5, 0), (31, 0x7FFFFFFF), (32, 0x80000000), (33, 0), (64, 0), (160, 0)):
        for b20 in (INT_MIN, -1, 0, 1, 2):
            if bits[0] != 0 and b20 not in (0, 1):
                continue
            yield lift(label(f"lift timer elapsed bits {bits[0]} body limit {b20}"), dt=10, timer=10, bits=bits, b20=b20,
                       P1=b20 & 1, P49=True, **noise(rng))
    yield lift(label("lift timer elapsed without names"), dt=10, timer=10, names=(), **noise(rng))
    # ---- 0x41b1f0, the throw -----------------------------------------------------------------------------------
    q_values = [None, (0x2C, 0x2C, 0xBEEF), (0x2D, 0x2C, 0xBEEF), (0x2B, 0x2C, 0xBEEF), (0x2C, 0x2B, 0xBEEF),
                (0x2C, 0x2D, 0xBEEF), (0, 0, 0xBEEF), (-1, INT_MAX, 0xBEEF), (INT_MIN, 100, 0xBEEF),
                (INT_MAX, INT_MAX, 0xBEEF), (0x2C, INT_MIN, 0xBEEF), (44, 44, 0), (-100, 45, 77), (30, 90, 0xFFFFFFFF),
                (100, 100, 5), (43, 45, 6)]
    for q in q_values:
        for names in (NAMES, ()):
            if names == () and q not in (None, (0x2C, 0x2C, 0xBEEF)):
                continue
            yield throw(label(f"throw link {q} names={len(names)}"), q=q, names=names, **noise(rng))
    # ---- 0x41b280, holding and releasing ------------------------------------------------------------------------
    for in8 in (0, DIR_A, DIR_B, DIR_A | DIR_B, 0x22 | DIR_A):
        for p0 in (0, 1):
            for p3d in ((0, 3000) if in8 & 0x22 else (3000,)):
                yield hold(label(f"hold direction in8={in8:#x} P0={p0} counter={p3d}"), in8=in8, P0=p0, counter=p3d,
                           **noise(rng))
    for in8, p0 in ((DIR_A, 1), (DIR_B, 0)):
        for bit1 in (0, 2):
            yield hold(label(f"hold flag bit in8={in8:#x} c40={bit1}"), in8=in8, P0=p0, counter=3000,
                       **dict(noise(rng), c40=0x5A5A5A58 | bit1))
    for pf in (0, 1, 7, 8, 9, 10, 11, 0x11, 0x12, 0x13):
        yield hold(label(f"hold fall Pf={pf:#x}"), state=4, Pf=pf, P1=pf & 1, P49=bool(pf & 2), **noise(rng, True))
    yield hold(label("hold fall without names"), state=4, Pf=9, names=(), **noise(rng, True))
    yield hold(label("hold fall p0 set"), state=4, Pf=2, P0=1, **noise(rng, True))
    for counter in (0, 1, 2999, 3000, 3001, 0x80000000, 0xFFFFFFFF):
        for in8 in (0x22, 0x02, 0x20, 0x04, 0x1000000):
            if counter in (1, 0x80000000) and in8 not in (0x22, 0x02):
                continue
            yield hold(label(f"hold counter {counter:#x} in8={in8:#x}"), in8=in8, counter=counter, dt=7, a8=True,
                       a14=1, a24=1, a1c=1, **noise(rng))
    for counter in (3000, 3001, 5999, 6000, 150000, 42949672, 42949673, 42949674, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield hold(label(f"hold release ratio counter {counter:#x}"), counter=counter, a8=True, a14=1, a24=1, a1c=1,
                   **noise(rng))
    for bits in ((0, 0x1), (1, 0xF0F0F0F0), (5, 0), (32, 0x80000000), (33, 0), (64, 0), (160, 0)):
        yield hold(label(f"hold release bits {bits[0]}"), counter=3000, bits=bits, a8=True, a14=1, a24=1, a1c=1,
                   **noise(rng))
    for y30 in (0, 7):
        for c0c in (0, 1, 9):
            for grunt in (True, False):
                if y30 and (c0c != 1 or not grunt):
                    continue
                yield hold(label(f"hold release grunt y30={y30} c0c={c0c} found={grunt}"), counter=3500, y30=y30,
                           c0c=c0c, c10=0xC10 + c0c, grunt=grunt, a8=True, a14=1, a24=1, a1c=1, **noise(rng))
    yield hold(label("hold release nothing held"), counter=3000, P4b=False, a8=True, a14=1, a24=1, a1c=1, **noise(rng))
    yield hold(label("hold animation other result"), counter=3000, a8=True, a14=1, a24=5, a1c=0, **noise(rng))
    yield hold(label("hold animation absent"), counter=3000, **noise(rng))
    for c1a4 in (0, 5):
        for a14 in (1, 3):
            for p0 in (0, 1):
                for held in (True, False):
                    if c1a4 == 0 and (a14 == 3 or p0 or not held):
                        continue
                    yield hold(label(f"hold stand 1a4={c1a4} n={a14} P0={p0} held={held}"), counter=3000, P0=p0,
                               P4b=held, a8=True, a14=a14, a24=(1 if held else 2), a1c=c1a4, a28=0x40490FDB,
                               names=NAMES if p0 else (), **noise(rng))
    for cflags in (0, 0x10, 0x30):
        for partner in (None, (21, -33)):
            yield hold(label(f"hold partner flags={cflags:#x} {partner}"), cflags=cflags, partner=partner, counter=0x7777,
                       in8=0x22, **noise(rng))
    # ---- 0x41dc50, picking up --------------------------------------------------------------------------------------
    for hflags in (0, 4, 0xFB, 0xFF, 1, 0x80):
        yield start(label(f"start held flags {hflags:#x}"), hflags=hflags, **noise(rng))
    for bits in ((0, 0x1), (1, 0xF0F0F0F1), (5, 0x0), (32, 0x80000000), (33, 0), (64, 0), (160, 0)):
        for c64h in (3, 0x1F):
            yield start(label(f"start bits {bits[0]} link {c64h}"),
                        **dict(noise(rng), bits=bits, c64h=c64h, c64=0x1E, c8h=0x10))
    yield start(label("start without names"), names=(), hflags=4, **noise(rng))
    yield start(label("start link flags kept"), **dict(noise(rng), c64h=9, c64=8, c8h=0x20000, bits=(5, 3)))
    # ---- 0x421010, set the callback ------------------------------------------------------------------------------------
    for limit_field in (INT_MIN, -1, 0, 1, 100, INT_MAX):
        arguments = {1, 0, limit_field, limit_field + 1, limit_field - 1}
        for argument in sorted(arguments):
            argument = (argument + 0x80000000) % 0x100000000 - 0x80000000
            c = merged(dict(b20=limit_field))
            callback = 0x4207A0 + rng.randrange(0, 0x1000)
            yield Case(label(f"callback limit {limit_field} argument {argument}"), SET_CALLBACK,
                       (lambda env, c=c: build(env, c)), receiver=lambda t: t["B"],
                       arguments=(callback, argument & 0xFFFFFFFF))
    # ---- 0x4dbd20, set a bit ----------------------------------------------------------------------------------------------
    def bit_case(text, nbits, word, bit):
        c = merged(dict(bits=(nbits, word)))
        return Case(label(f"set bit {text}"), SET_BIT, (lambda env, c=c: build(env, c)),
                    receiver=lambda t: t["bits"], arguments=(bit,))

    for nbits, word in ((0, 0), (5, 0xFFFF0000), (32, 0x12345678)):
        for bit in (0, 1, 31, 32, 64, 100):
            yield bit_case(f"inline {nbits} bit {bit}", nbits, word, bit)
    yield bit_case("inline 1 bit 0", 1, 0x80000000, 0)
    yield bit_case("inline 31 bit 255", 31, 1, 255)
    for nbits, bit in ((33, 0), (33, 31), (33, 32), (33, 40), (33, 63), (33, 64), (33, 100), (64, 64), (64, 95),
                       (64, 96), (64, 127), (64, 200), (96, 96), (96, 130), (96, 300), (65, 70), (65, 200), (160, 160),
                       (160, 400)):
        yield bit_case(f"pointer {nbits} bit {bit}", nbits, 0, bit)

    # ---- 0x4dc6d0, grow the bit set ----------------------------------------------------------------------------------------
    def grow_case(text, nbits, word, new):
        c = merged(dict(bits=(nbits, word)))
        return Case(label(f"grow {text}"), RESIZE, (lambda env, c=c: build(env, c)),
                    receiver=lambda t: t["bits"], arguments=(new,))

    for nbits, word in ((0, 0), (5, 0xA5A5A5A5), (32, 0x80000001)):
        for new in (1, 31, 32, 33, 64, 65, 200):
            yield grow_case(f"inline {nbits} to {new}", nbits, word, new)
    for nbits, news in ((33, (32, 33, 64, 65, 96, 200)), (64, (64, 65, 96, 97, 300)), (100, (100, 128, 129, 1000)),
                        (65, (65, 70, 96))):
        for new in news:
            yield grow_case(f"pointer {nbits} to {new}", nbits, 0, new)

    # malloc and realloc that fail.  The original then reads the caller's EBP, which holds the word count: ask for as
    # many words as the address of a live sentinel object minus four, so that the read lands on the sentinel.
    def failing(text, nbits, word, via_bit):
        c = merged(dict(bits=(nbits, word)))
        override = MALLOC if nbits <= 0x20 else REALLOC

        def setup(env):
            tokens = build(env, c)
            sentinel = env.object(16, "sentinel", words=[0x51, 0x52, 0x53, 0x54])
            tokens["words"] = sentinel - 4
            env.override(override, allocate(fail=True) if override == MALLOC else reallocate(fail=True))
            return tokens

        if via_bit:
            return Case(label(f"fail {text}"), SET_BIT, setup, receiver=lambda t: t["bits"],
                        arguments=(lambda t: (t["words"] * 32 - 1) & 0xFFFFFFFF,))
        return Case(label(f"fail {text}"), RESIZE, setup, receiver=lambda t: t["bits"],
                    arguments=(lambda t: (t["words"] * 32) & 0xFFFFFFFF,))

    yield failing("grow inline", 5, 7, False)
    yield failing("grow pointer", 64, 0, False)
    yield failing("set bit inline", 0, 0, True)
    yield failing("set bit pointer", 64, 0, True)

    # ---- worlds drawn from the case random source ------------------------------------------------------------------------------
    for k in range(3):
        combos = [random_source.choice(COMBOS) for _ in range(3)]
        flips = [random_source.choice([-1, 1]) * random_source.randrange(1, 90) for _ in range(12)]
        options = physics_world(combos, count=random_source.randrange(0, 60),
                                dt=random_source.randrange(0, 40), x=random_source.randrange(-100, 900),
                                y=random_source.randrange(-100, 900), c40=random_source.getrandbits(32),
                                flipvals=flips, rect=(flips[0], -10, 9, 3),
                                cflags=random_source.choice([0, 0x10]),
                                partner=random_source.choice([None, (random_source.randrange(-50, 50), 3)]),
                                state=random_source.choice([7, 4]), Pf=random_source.randrange(0, 20),
                                P0=random_source.randrange(0, 2), timer=random_source.randrange(0, 40))
        options["g"][G_E60] = random_source.uniform(-1.0, 1.0)
        options["g"][VEL[0]] = random_source.uniform(-400.0, 400.0)
        options["g"][ACC[0]] = random_source.uniform(-10.0, 10.0)
        yield lift(label(f"lift random world {k}"), **options)
    for k in range(3):
        yield hold(label(f"hold random world {k}"), counter=random_source.randrange(0, 20000),
                   in8=random_source.choice([0, 0x22, 0x1000000, 0x2000000]), P0=random_source.randrange(0, 2),
                   a8=True, a14=random_source.randrange(1, 3), a24=random_source.choice([1, 1, 5]), a1c=random_source.randrange(0, 3),
                   x=random_source.randrange(-100, 900), y=random_source.randrange(-100, 900))
