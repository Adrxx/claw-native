"""Cases for level_one_batch_enemy_states_02: Level 1 shared enemy state callbacks, batch 2.

Coverage is enumerated, not sampled: every branch is reached by a fixed case.  The random source only fills
the bytes that no branch reads and picks the value of fields whose exact value does not steer control flow."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns

F_F980, F_FC20, F_FF60, F_0070, F_0260 = 0x43F980, 0x43FC20, 0x43FF60, 0x440070, 0x440260
F_05B0, F_0870, F_0A50, F_0BE0, F_0D50 = 0x4405B0, 0x440870, 0x440A50, 0x440BE0, 0x440D50

G_ANIM_STEP = 0x5430C4      # DAT_005430c4, time step handed to the animation stepper
G_NOW = 0x537210            # DAT_00537210, clock
G_PLAYER = 0x537E88         # DAT_00537e88, pointer to the player-like object

OBJ_SIZE = 0x400
SCALE = 0x1C0
NAN = float("nan")


def dbl(x):
    return struct.pack("<d", x)


def words(*values):
    return struct.pack("<%dI" % len(values), *[v & 0xFFFFFFFF for v in values])


def junk(rs, n):
    return bytes(rs.randrange(1, 256) for _ in range(n))


# ---------------------------------------------------------------- animation presets ----------------------------------
# The animation stepper at A = scale + 0x188 is original code.  Each preset fixes A so it returns a known value and
# leaves a known A.  fields: a8, a14, a18, a1c, a20, a24 and the time step.
def preset(name, a8=0, a14=0, a18=0, a1c=0, a20=0, a24=0, step=3):
    return dict(name=name, a8=a8, a14=a14, a18=a18, a1c=a1c, a20=a20, a24=a24, step=step)


NONE = preset("none", a14=0x31, a1c=0x32, a20=0x33, a24=0x34)             # a8 == 0: returns -1, nothing else read
DIRECT = lambda r: preset(f"direct {r:#x}", a8=0x77, a14=0, a1c=1, a20=r, a24=0x5151)
COUNTDOWN = lambda n, r, a1c: preset(f"countdown {n} -> {r:#x} a1c={a1c}", a8=0x77, a14=n, a18=0, a1c=a1c, a20=0x4242, a24=r)
DECAY_SHORT = lambda n, p, r: preset(f"decay {n} step {p}", a8=0x77, a14=n, a18=1, a1c=1, a20=0x4343, a24=r, step=p)
DECAY_LONG = lambda n, p, r: preset(f"decay {n} step {p} expired", a8=0x77, a14=n, a18=1, a1c=1, a20=r, a24=0x4444, step=p)
NONE_TAILS = [preset(f"none a14={a14} a1c={a1c}", a14=a14, a1c=a1c, a20=0x33, a24=0x34)
              for a14 in (0, 9) for a1c in (0, 1)]

PRESETS_SMALL = [NONE, DIRECT(1), DECAY_SHORT(7, 3, 1)]
PRESETS_STEP = [NONE, DIRECT(1), DIRECT(0), DIRECT(2), COUNTDOWN(3, 1, 1), COUNTDOWN(1, 1, 0), DECAY_SHORT(7, 3, 1),
                DECAY_LONG(2, 6, 1)]

# replacement animations (the object handed to the stepper's reset routine): kind -> (frame +4, +0xC, +0x18)
ANIM_KINDS = {"null": None, "plain": (0, 6, 0), "hold": (1, 6, 5), "stop": (3, 9, 2)}


# ---------------------------------------------------------------- object builder ------------------------------------
def build(rs, anim, **f):
    """setup() for one enemy object (size 0x400), its scale object, owner, player object and vtable."""
    body, scale_junk, owner_junk = junk(rs, OBJ_SIZE), junk(rs, SCALE), junk(rs, 0x150)
    inner_junk, vt_junk, g_junk = junk(rs, 0x100), junk(rs, 0x100), junk(rs, 0x200)

    def make_anim(env, kind):
        spec = ANIM_KINDS[kind]
        if spec is None:
            return 0
        frame = env.object(0x40, "frame", fill=0)
        env.put(frame + 4, spec[0])
        env.put(frame + 0xC, spec[1])
        env.put(frame + 0x18, spec[2])
        env.put(frame + 0x1C, 0x5A5A0000 + spec[1])
        arr = env.object(8, "frame-array", fill=0)
        env.put(arr, frame)
        obj = env.object(0x20, "animation", fill=0)
        env.put(obj + 0xC, arr)
        env.put(obj + 0x10, 1)
        return obj

    def setup(env):
        obj = env.object(OBJ_SIZE, "enemy", data=body)
        scale = env.object(SCALE, "scale", data=scale_junk)
        owner = env.object(0x150, "owner", data=owner_junk)
        inner = env.object(0x100, "stepper-owner", data=inner_junk)
        vtbl = env.object(0x100, "vtable", data=vt_junk)
        player = env.object(0x200, "player", data=g_junk)
        p1 = env.object(0x20, "player-p1", fill=0)
        p2 = env.object(8, "player-p2", fill=0)
        for slot in (0x44, 0x78, 0x8C):
            stub = env.stub(f"vtable+{slot:#x}", "thiscall", 0, returns(0x1000 + slot))
            env.put(vtbl + slot, stub)
        env.put(obj, vtbl)
        env.put(obj + 0xC, owner)
        env.put(obj + 0x12C, scale)
        # stepper state
        env.put(scale + 0x18C, inner)
        env.put(scale + 0x190, anim["a8"])
        env.put(scale + 0x19C, anim["a14"], anim["a18"], anim["a1c"], anim["a20"], anim["a24"])
        env.put(G_ANIM_STEP, anim["step"])
        # player object chain
        env.put(G_PLAYER, player)
        env.put(player + 0x16C, f.get("g16c", 0x2A))
        env.put(player + 0x4C, f.get("g4c", 0x1234))
        env.put(player + 0x50, f.get("g50", 0x4321))
        env.put(player + 0x6C, p1)
        env.put(p1 + 0x14, p2)
        env.put(p2, f.get("p2", 0))
        # owner / scale / object fields
        env.put(owner + 0xCC, f.get("cc", 1))
        env.put(scale + 8, f.get("s8", 0xA5C3E17B))
        env.put(scale + 0x40, f.get("s40", 0))
        env.write(scale + 0x118, words(*f.get("sc118", (0x11, 0x22, 0x33, 0x44))))
        env.write(scale + 0x128, words(*f.get("sc128", (0x55, 0x66, 0x77, 0x88))))
        env.write(scale + 0x138, words(*f.get("sc138", (0x99, 0xAA, 0xBB, 0xCC))))
        env.put(obj + 0x20, f.get("state", 0x777))
        env.write(obj + 0x50, dbl(f.get("x50", 1.5)))
        env.write(obj + 0x68, dbl(f.get("d68", 2.5)))
        env.write(obj + 0x70, dbl(f.get("d70", 3.5)))
        env.put(obj + 0x118, f.get("i118", 0x1357))
        env.put(obj + 0x120, f.get("i120", 0))
        env.write(obj + 0x138, words(*f.get("o138", (0x1AB, 0x2CD, 0x3EF, 0x4F1))))
        env.put(obj + 0x18C, f.get("i18c", 3))
        env.put(obj + 0x1A0, f.get("i1a0", 0))
        env.write(obj + 0x220, words(*f.get("t220", (0x1A1, 0x2B2, 0x3C3, 0x4D4))))
        env.write(obj + 0x270, words(*f.get("t270", (0x71, 0x72, 0x73, 0x74))))
        env.put(obj + 0x280, f.get("i280", 100))
        env.put(obj + 0x2B4, f.get("i2b4", 40))
        env.put(obj + 0x2B8, f.get("i2b8", 50))
        env.put(obj + 0x2BC, f.get("i2bc", 60))
        env.put(obj + 0x2C0, f.get("i2c0", 70))
        env.put(obj + 0x2C4, f.get("i2c4", 80))
        env.put(obj + 0x2C8, f.get("i2c8", 90))
        env.put(obj + 0x2CC, f.get("i2cc", 0))
        env.put(obj + 0x378, make_anim(env, f.get("anim378", "plain")))
        env.put(obj + 0x380, make_anim(env, f.get("anim380", "plain")))
        env.put(obj + 0x3F0, f.get("t3f0", 100))
        env.put(obj + 0x3F4, f.get("t3f4", 50))
        env.put(G_NOW, f.get("now", 1000))
        return {"obj": obj, "scale": scale, "owner": owner, "vtbl": vtbl, "player": player}

    return setup


def case(label, function, setup):
    return Case(label, function, setup, receiver=lambda t: t["obj"])


# ---------------------------------------------------------------- 0x43f980 / 0x43fc20 ---------------------------------
def compare_cases(rs, fn, name):
    """Both functions have the same body: fire the virtual call on a position/velocity comparison."""
    x50s = [(-2.5, "neg"), (-0.0, "negzero"), (0.0, "zero"), (3.25, "pos"), (NAN, "nan")]
    rels = [("below", -2.0), ("equal", 0.0), ("above", 2.0), ("just above", 0.5), ("nan", NAN)]
    for x50, xname in x50s:
        for rname, delta in rels:
            for eq118 in (False, True):
                i280 = 100
                d68 = i280 + delta
                if eq118 and (d68 != d68 or d68 != int(d68)):
                    continue
                i118 = int(d68) if eq118 else 0x2222
                yield case(f"{name} x50 {xname} d68 {rname} eq118={eq118}", fn,
                           build(rs, NONE, x50=x50, d68=d68, i280=i280, i118=i118,
                                 i120=rs.getrandbits(32) & 0xFFFEFFFF))
    for x50, xname in x50s:
        yield case(f"{name} x50 {xname} flag 0x10000 only", fn,
                   build(rs, NONE, x50=x50, d68=500.5, i280=100, i118=0x2222, i120=0x10000))
    for flags in (0xFFFFFFFF, 0x0000FFFF, 0xFFFEFFFF, 0x80010000, 0x00020000):
        yield case(f"{name} flags {flags:#x}", fn,
                   build(rs, NONE, x50=2.0, d68=500.5, i280=100, i118=0x2222, i120=flags))
    # wide signed range of the integer operand
    for i280 in (0x7FFFFFFF, -0x80000000):
        for delta in (-1.0, 0.0, 1.0):
            for x50 in (-9.0, 9.0):
                d68 = float(i280) + delta
                yield case(f"{name} i280={i280} delta {delta} x50 {x50}", fn,
                           build(rs, NONE, x50=x50, d68=d68, i280=i280 & 0xFFFFFFFF, i118=0x2222))
    # animation stepper variants do not change the comparison but reach different stepper paths
    for anim in PRESETS_SMALL[1:] + [DIRECT(0xFFFFFFFF), DECAY_LONG(2, 6, 1)]:
        for x50, d68 in ((-1.0, 99.0), (1.0, 101.0), (1.0, 99.0), (-1.0, 101.0)):
            yield case(f"{name} {anim['name']} x50={x50} d68={d68}", fn,
                       build(rs, anim, x50=x50, d68=d68, i280=100, i118=0x2222))
    for _ in range(2):
        yield case(f"{name} random", fn,
                   build(rs, NONE, x50=rs.uniform(-100, 100), d68=rs.uniform(-100, 300), i280=rs.randrange(-50, 250),
                         i118=rs.getrandbits(31), i120=rs.getrandbits(32)))


# ---------------------------------------------------------------- cases ---------------------------------------------
def cases(random_source):
    rs = random_source

    yield from compare_cases(rs, F_F980, "f980")
    yield from compare_cases(rs, F_FC20, "fc20")

    # ---- 0x43ff60: owner gate then a virtual call at +0x78
    for cc in (1, 0, 2, 0xFFFFFFFF, 0x101, 0x80000001):
        for anim in PRESETS_SMALL + [DECAY_LONG(2, 6, 1)]:
            yield case(f"ff60 cc={cc:#x} {anim['name']}", F_FF60, build(rs, anim, cc=cc))

    # ---- 0x440070: take the throw vector once, then raise a flag when the animation has ended
    ended = [DIRECT(1), COUNTDOWN(1, 1, 1), COUNTDOWN(3, 1, 1), DECAY_SHORT(7, 3, 1), DECAY_LONG(2, 6, 1)]
    notone = [NONE, DIRECT(0), DIRECT(2), DIRECT(0xFFFFFFFF), COUNTDOWN(3, 2, 1), COUNTDOWN(1, 1, 0)] + NONE_TAILS
    for anim in ended + notone:
        for i1a0 in (0, 0x7F000001):
            for s40 in (0, 2):
                yield case(f"0070 {anim['name']} i1a0={i1a0:#x} s40={s40}", F_0070,
                           build(rs, anim, i1a0=i1a0, s40=s40, s8=rs.getrandbits(32) & 0xFFFEFFFF,
                                 t220=tuple(rs.getrandbits(32) | 1 for _ in range(4))))
    for s40 in (1, 3, 0xFD, 0xFF, 0xFFFFFFFF, 0x82, 0x100):
        yield case(f"0070 s40={s40:#x}", F_0070, build(rs, DIRECT(1), s40=s40, s8=0, t220=(0x01020304, 0x0A0B0C0D, 0x11121314, 0x21222324)))
    for t220 in ((0x80000000, 0, 0x7FFFFFFF, 5), (0, 0x80000000, 5, 0x80000000), (1, 2, 3, 4)):
        for s40 in (0, 2):
            yield case(f"0070 t220 {t220[0]:#x} s40={s40}", F_0070, build(rs, DIRECT(1), s40=s40, t220=t220))
    for s8 in (0, 0x10000, 0xFFFFFFFF, 0xFFFEFFFF):
        yield case(f"0070 s8={s8:#x} ended", F_0070, build(rs, DIRECT(1), i1a0=5, s8=s8))
        yield case(f"0070 s8={s8:#x} NONE a14=0 a1c=1", F_0070, build(rs, NONE_TAILS[1], i1a0=5, s8=s8))

    # ---- 0x440260: restart the animation, reset the throw vector, move the owner
    for cc in (1,):
        for anim in PRESETS_STEP:
            for kind in ("null", "plain", "hold", "stop"):
                yield case(f"0260 cc=1 {anim['name']} anim {kind}", F_0260,
                           build(rs, anim, cc=cc, anim380=kind, s8=rs.getrandbits(32),
                                 t270=tuple(rs.getrandbits(32) | 1 for _ in range(4)),
                                 x50=rs.uniform(1, 99)))
    for cc in (0, 2, 0xFFFFFFFF, 0x101, 0x80000001):
        for anim in (NONE, DIRECT(1)):
            yield case(f"0260 cc={cc:#x} {anim['name']}", F_0260, build(rs, anim, cc=cc))
    for t270 in ((0, 0, 0, 0), (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x80000001), (5, 6, 7, 0xFFFFFFF0)):
        yield case(f"0260 t270 {t270[3]:#x}", F_0260, build(rs, DIRECT(1), t270=t270))
    for s8 in (0, 0xFFFFFFFF, 2, 4, 6):
        yield case(f"0260 s8={s8:#x}", F_0260, build(rs, NONE, s8=s8))

    # ---- 0x4405b0: gated by the player state 0x2a / 0x2b
    for p2 in (0, 7):
        for s40 in (0, 2):
            for kind in ("null", "plain", "hold", "stop"):
                for anim in (NONE, DIRECT(1)):
                    yield case(f"05b0 0x2a p2={p2} s40={s40} anim {kind} {anim['name']}", F_05B0,
                               build(rs, anim, g16c=0x2A, p2=p2, s40=s40, anim378=kind, s8=rs.getrandbits(32),
                                     o138=tuple(rs.getrandbits(32) | 1 for _ in range(4)),
                                     t270=tuple(rs.getrandbits(32) | 1 for _ in range(4)),
                                     sc118=tuple(rs.getrandbits(32) | 1 for _ in range(4)),
                                     sc128=tuple(rs.getrandbits(32) | 1 for _ in range(4)),
                                     sc138=tuple(rs.getrandbits(32) | 1 for _ in range(4))))
    # the three negate helpers each skip a value of 0x80000000
    guards = [("sc118", (0x80000000, 0x22, 0x33, 0x44)), ("sc118", (0x11, 0x22, 0x33, 0x80000000)),
              ("sc128", (0x80000000, 0x66, 0x77, 0x88)), ("sc128", (0x55, 0x66, 0x77, 0x80000000)),
              ("sc138", (0x80000000, 0xAA, 0xBB, 0xCC)), ("sc138", (0x99, 0xAA, 0xBB, 0x80000000))]
    for key, value in guards:
        for p2, s40 in ((0, 0), (7, 2)):
            yield case(f"05b0 guard {key} {value[0]:#x},{value[3]:#x} p2={p2}", F_05B0,
                       build(rs, NONE, g16c=0x2A, p2=p2, s40=s40, **{key: value}))
    for g4c, g50, i2c0, i2c4, i2c8 in ((0x7FFFFFFF, 0x7FFFFFFF, 1, 1, 1), (-5 & 0xFFFFFFFF, -9 & 0xFFFFFFFF, 2, 3, 4),
                                       (0x1000, 0x2000, 0x80000000, 0x80000000, 0x80000000), (0, 0, 0, 0, 0)):
        for p2 in (0, 1):
            yield case(f"05b0 position g4c={g4c:#x} p2={p2}", F_05B0,
                       build(rs, DIRECT(1), g16c=0x2A, p2=p2, s40=2 if p2 == 0 else 0, g4c=g4c, g50=g50,
                             i2c0=i2c0, i2c4=i2c4, i2c8=i2c8))
    for g16c in (0x2B, 0x29, 0x2C, 0, 0xFFFFFFFF, 0x2A2A, 0x1000002B):
        for anim in (NONE, DIRECT(1)):
            yield case(f"05b0 state {g16c:#x} {anim['name']}", F_05B0, build(rs, anim, g16c=g16c, p2=1, s40=2))

    # ---- 0x440870
    for p2 in (0, 3):
        for s40 in (0, 2):
            for i2cc in (0, 1, 0xFFFFFFFF, 0x80000000):
                for anim in (NONE, DIRECT(1)):
                    yield case(f"0870 p2={p2} s40={s40} i2cc={i2cc:#x} {anim['name']}", F_0870,
                               build(rs, anim, p2=p2, s40=s40, i2cc=i2cc, s8=rs.getrandbits(32),
                                     o138=tuple(rs.getrandbits(32) | 1 for _ in range(4)),
                                     i2b4=rs.randrange(1, 1000), i2b8=rs.randrange(1, 1000),
                                     i2bc=rs.randrange(1, 1000)))
    for key, value in guards:
        for p2, s40 in ((0, 0), (3, 2)):
            yield case(f"0870 guard {key} {value[0]:#x},{value[3]:#x} p2={p2}", F_0870,
                       build(rs, NONE, p2=p2, s40=s40, **{key: value}))
    for g4c, g50, i2b4, i2b8, i2bc in ((0x7FFFFFFF, 0x7FFFFFFF, 1, 1, 1), (-5 & 0xFFFFFFFF, -9 & 0xFFFFFFFF, 2, 3, 4),
                                       (0x1000, 0x2000, 0x80000000, 0x80000000, 0x80000000), (0, 0, 0, 0, 0)):
        for p2, i2cc in ((0, 0), (0, 1), (5, 0), (5, 1)):
            yield case(f"0870 position g4c={g4c:#x} p2={p2} i2cc={i2cc}", F_0870,
                       build(rs, DIRECT(1), p2=p2, s40=2 if p2 == 0 else 0, g4c=g4c, g50=g50, i2b4=i2b4, i2b8=i2b8,
                             i2bc=i2bc, i2cc=i2cc))
    for o138 in ((0x80000000, 1, 0x80000000, 2), (0, 0, 0, 0), (0x7FFFFFFF, 1, 0xFFFFFFFF, 2)):
        for p2, s40 in ((0, 0), (2, 2)):
            yield case(f"0870 o138 {o138[0]:#x} p2={p2}", F_0870, build(rs, NONE, p2=p2, s40=s40, o138=o138))

    # ---- 0x440a50: owner clears the throw vector, then the timer ends the state
    times = [("before", 1000, 960, 50), ("one short", 1000, 951, 50), ("exact", 1000, 950, 50),
             ("after", 1000, 900, 50), ("wrapped start", 100, 4000000000, 5), ("zero delay", 1000, 1000, 0),
             ("zero start", 20, 0, 21), ("zero start exact", 20, 0, 20), ("huge delay", 1000, 0, 0xFFFFFFFF),
             ("clock below start", 10, 20, 5)]
    for cc in (1, 0):
        for text, now, start, delay in times:
            for anim in (NONE, DIRECT(1)):
                yield case(f"0a50 cc={cc} {text} {anim['name']}", F_0A50,
                           build(rs, anim, cc=cc, now=now, t3f0=start, t3f4=delay, s8=rs.getrandbits(32),
                                 t270=tuple(rs.getrandbits(32) | 1 for _ in range(4)), x50=rs.uniform(1, 99)))
    for cc in (2, 0xFFFFFFFF, 0x101):
        for text, now, start, delay in times[::3]:
            yield case(f"0a50 cc={cc:#x} {text}", F_0A50, build(rs, NONE, cc=cc, now=now, t3f0=start, t3f4=delay))
    for s8 in (0, 0xFFFFFFFF, 1, 2, 4, 7):
        yield case(f"0a50 s8={s8:#x} fire", F_0A50, build(rs, NONE, cc=1, now=1000, t3f0=900, t3f4=50, s8=s8))
    for t270 in ((0, 0, 0, 0), (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x80000001)):
        yield case(f"0a50 t270 {t270[3]:#x}", F_0A50, build(rs, NONE, cc=1, now=1000, t3f0=900, t3f4=50, t270=t270))

    # ---- 0x440be0 and 0x440d50: same body, reload at the end of the animation or count down x50
    tails = [NONE_TAILS[0], NONE_TAILS[1], NONE_TAILS[2], NONE_TAILS[3], DIRECT(1), COUNTDOWN(1, 1, 1),
             COUNTDOWN(3, 1, 1), DECAY_SHORT(7, 3, 1), COUNTDOWN(2, 1, 0)]
    for fn, name in ((F_0BE0, "0be0"), (F_0D50, "0d50")):
        for anim in tails:
            for x50 in (0.0, 2.5, -1e10, NAN):
                for i18c in (3, 0, 0x103):
                    if anim not in (NONE_TAILS[0], NONE_TAILS[1], DIRECT(1)) and (x50, i18c) not in ((2.5, 3), (2.5, 0)):
                        continue
                    yield case(f"{name} {anim['name']} x50={x50!r} i18c={i18c:#x}", fn,
                               build(rs, anim, x50=x50, i18c=i18c, s8=rs.getrandbits(32), state=rs.getrandbits(32) | 5))
        for x50 in (-0.0, 1e-300, 1e300, 100.125, -7.75, float("inf")):
            for i18c in (3, 4):
                yield case(f"{name} x50={x50!r} i18c={i18c}", fn, build(rs, NONE_TAILS[0], x50=x50, i18c=i18c))
        for s8 in (0, 0xFFFFFFFF, 4, 0xFFFFFFFB):
            yield case(f"{name} s8={s8:#x} fire", fn, build(rs, DIRECT(1), s8=s8))
