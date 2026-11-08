"""Cases for level_one_batch_enemy_states_01: Level 1 shared enemy state callbacks, batch 1.

Coverage is enumerated, not sampled: every branch is reached by a fixed case.  The random source only fills
the bytes that no branch reads, and picks the value of fields whose exact value does not steer control flow."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import reallocate, returns

F_EDD0, F_FD10, F_FDC0, F_F030 = 0x43EDD0, 0x43FD10, 0x43FDC0, 0x43F030
F_F450, F_F540, F_F6E0, F_F720 = 0x43F450, 0x43F540, 0x43F6E0, 0x43F720
REALLOC = 0x4A9070

G_ANIM_STEP = 0x5430C4      # DAT_005430c4, time step handed to the animation stepper
G_NOW = 0x537210            # DAT_00537210, clock
G_COUNTER = 0x52713C        # DAT_0052713c
G_FLAG = 0x532C0C           # DAT_00532c0c
G_FLAG_ARG = 0x532C10       # DAT_00532c10
# the array object at 0x537698 (an MFC style array of strings) and the string trie at 0x537668
ARR = 0x537698
ARR_ERR, ARR_LO, ARR_HI, ARR_BASE, ARR_TEMPLATE = ARR + 4, ARR + 8, ARR + 0xC, ARR + 0x10, ARR + 0x14
ARR_STRIDE, ARR_INIT, ARR_COUNT = ARR + 0x18, ARR + 0x1C, ARR + 0x20
TRIE = 0x537668
TRIE_ROOT = TRIE + 0x18
G_ERR_TEXT = 0x544B4C
G_ERR_CODE = 0x544B14

OBJ_SIZE = 0x400
SCALE = 0x1C0


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

PRESETS_COMMON = [NONE, DIRECT(1), DECAY_SHORT(7, 3, 1), DECAY_LONG(2, 6, 1)]


# ---------------------------------------------------------------- object builder ------------------------------------
def build(rs, anim, **f):
    """setup() for one enemy object (size 0x400) with its scale object, owner object and vtable.
    f: x_cc, x138 (4 words), t220 (4 words), s8, s38, s40, state304, start3d8, delay3dc, start3e0, delay3e4, now,
    ptr38c, ptr3a0, flag, counter, d24, d20, d50, d68, d80, d98, string_index setup (via extra callback)."""
    body, scale_junk, owner_junk, vt_junk = junk(rs, OBJ_SIZE), junk(rs, SCALE), junk(rs, 0x150), junk(rs, 0x80)
    ftail = {k: (v if not callable(v) else v) for k, v in f.items()}

    def setup(env):
        obj = env.object(OBJ_SIZE, "enemy", data=body)
        scale = env.object(SCALE, "scale", data=scale_junk)
        owner = env.object(0x150, "owner", data=owner_junk)
        zed = env.object(0x40, "zed", data=junk(rs_inner, 0x40))
        vtbl = env.object(0x80, "vtable", data=vt_junk)
        slots = {}
        for slot, argc in ((0x44, 0), (0x48, 0), (0x6C, 1), (0x70, 1)):
            slots[slot] = env.stub(f"vtable+{slot:#x}", "thiscall", argc, returns(0x1000 + slot))
            env.put(vtbl + slot, slots[slot])
        env.put(obj, vtbl)
        env.put(obj + 0xC, owner)
        env.put(obj + 0x10, zed)
        env.put(obj + 0x12C, scale)
        env.put(scale + 0x190, anim["a8"])
        env.put(scale + 0x19C, anim["a14"], anim["a18"], anim["a1c"], anim["a20"], anim["a24"])
        env.put(G_ANIM_STEP, anim["step"])
        env.put(owner + 0xCC, ftail.get("x_cc", 0))
        env.write(owner + 0x138, words(*ftail.get("x138", (0x11, 0x22, 0x33, 0x44))))
        env.write(obj + 0x220, words(*ftail.get("t220", (0x1A1, 0x2B2, 0x3C3, 0x4D4))))
        env.put(scale + 8, ftail.get("s8", 0x10203040))
        env.put(scale + 0x38, ftail.get("s38", 0x55))
        env.put(scale + 0x40, ftail.get("s40", 0))
        env.put(obj + 0x20, ftail.get("d20", 0x777))
        env.put(obj + 0x24, ftail.get("d24", 0x888))
        env.put(obj + 0x304, ftail.get("state304", 0))
        env.put(obj + 0x3D8, ftail.get("start3d8", 100))
        env.put(obj + 0x3DC, ftail.get("delay3dc", 50))
        env.put(obj + 0x3E0, ftail.get("start3e0", 100))
        env.put(obj + 0x3E4, ftail.get("delay3e4", 50))
        env.put(G_NOW, ftail.get("now", 1000))
        env.put(G_COUNTER, ftail.get("counter", 0))
        env.put(G_FLAG, ftail.get("flag", 0))
        env.put(G_FLAG_ARG, 0x2468)
        for off, key, dflt in ((0x50, "d50", 1.5), (0x68, "d68", 2.5), (0x80, "d80", 3.5), (0x98, "d98", 4.5)):
            env.write(obj + off, dbl(ftail.get(key, dflt)))
        # a target for the start-effect fixture chain: object whose [+0x10] object has [+0x78] == 0
        for key, off in (("ptr38c", 0x38C), ("ptr3a0", 0x3A0)):
            if ftail.get(key):
                holder = env.object(0x30, key, data=junk(rs_inner, 0x30))
                inner = env.object(0x90, key + "-inner", fill=0)
                env.put(holder + 0x10, inner)
                env.put(inner + 0x10, env.object(0x90, key + "-target", fill=0))
                env.put(obj + off, holder)
            else:
                env.put(obj + off, 0)
        if "extra" in ftail:
            ftail["extra"](env, obj, scale, owner, zed)
        return {"obj": obj, "scale": scale, "owner": owner, "zed": zed, "vtbl": vtbl}

    rs_inner = rs
    return setup


def case(label, function, setup):
    return Case(label, function, setup, receiver=lambda t: t["obj"])


def label_of(anim):
    return anim["name"]


# ---------------------------------------------------------------- 0x43f540 support ----------------------------------
STRINGS = [b"a", b"b", b"c", b"b", b"a"]
LEAF_VALUES = {b"a": 0xA1A1A1A1, b"b": 0xB2B2B2B2}


def cstring(env, text, extra_ref=1):
    """An MFC style CString body: 12 byte header (refcount, length, capacity) then the characters."""
    block = env.object(12 + len(text) + 8, "string", fill=0)
    env.put(block, extra_ref, len(text), len(text) + 4)
    env.write(block + 12, text + b"\0")
    return block + 12


def leaf(env, key, value, bit=0):
    node = env.object(0x20, "trie-leaf", fill=0)
    env.put(node + 8, bit)
    env.put(node + 0xC, cstring(env, key))
    env.put(node + 0x10, value)
    return node


def trie(env, kind):
    """Install the string trie at 0x537668 (root pointer at 0x537680)."""
    env.put(TRIE + 4, 0)
    if kind == "empty":
        env.put(TRIE_ROOT, 0)
        return
    root = env.object(0x20, "trie-root", fill=0)
    if kind == "flat":
        env.put(root + 8, 0)
        env.put(root, leaf(env, b"b", LEAF_VALUES[b"b"]), leaf(env, b"a", LEAF_VALUES[b"a"]))
    elif kind == "deep":
        env.put(root + 8, 0)
        inner = env.object(0x20, "trie-inner", fill=0)
        env.put(inner + 8, 16)      # tests the second byte
        env.put(inner, leaf(env, b"ba", 0xD0D0D0D0, bit=16), leaf(env, b"bb", 0xD1D1D1D1, bit=16))
        env.put(root, leaf(env, b"b", LEAF_VALUES[b"b"]), leaf(env, b"a", LEAF_VALUES[b"a"]))
        env.put(root, inner)  # child 0 is the inner node
    elif kind == "short":
        env.put(root + 8, 99)       # bit index beyond the key: lookup gives up at once
        env.put(root, leaf(env, b"b", LEAF_VALUES[b"b"]), leaf(env, b"a", LEAF_VALUES[b"a"]))
    elif kind == "mismatch":
        env.put(root + 8, 0)
        env.put(root, leaf(env, b"bx", 0xE0E0E0E0), leaf(env, b"ax", 0xE1E1E1E1))
    elif kind == "dead":
        env.put(root + 8, 0)
        env.put(root, 0, 0)
    env.put(TRIE_ROOT, root)


def array_setup(rs, lo, hi, stride, index, trie_kind="flat", elapsed=(1000, 100, 50), strings=None, handler=None,
                grow_fail=False, fail_from=None, grow_lo_prefill=False, err_text=True):
    now, start, delay = elapsed

    def extra(env, obj, scale, owner, zed):
        count = hi - lo + 1
        base = env.object(max(1, count * stride), "array-base", fill=0)
        for i in range(count):
            text = (strings or STRINGS)[i % len(strings or STRINGS)]
            env.put(base + i * stride, cstring(env, text))
        env.put(ARR_LO, lo)
        env.put(ARR_HI, hi)
        env.put(ARR_BASE, base)
        env.put(ARR_STRIDE, stride)
        env.put(ARR_INIT, 0xDEAD0001)
        env.put(ARR_COUNT, 0xDEAD0002)
        cell = env.object(8, "template-cell", fill=0)
        env.put(cell, cstring(env, b"t", extra_ref=1))
        env.put(ARR_TEMPLATE, cell)
        err = env.object(0x40, "array-error", data=junk(rs_, 0x40))
        if handler is not None:
            env.put(err + 0xC, handler)
        else:
            env.put(err + 0xC, 4)
        env.put(ARR_ERR, err)
        env.put(G_ERR_TEXT, 0)
        env.put(G_ERR_CODE, 0xBEEF)
        env.put(obj + 0x24, index)
        env.put(obj + 0x10 + 0, zed)
        env.put(zed + 0x1C, 0xCAFE0001)
        trie(env, trie_kind)
        if grow_fail:
            env.override(REALLOC, reallocate(fail=True))

    rs_ = rs
    return build(rs, NONE, now=now, start3e0=start, delay3e4=delay, extra=extra)


# ---------------------------------------------------------------- cases ---------------------------------------------
def cases(random_source):
    rs = random_source

    # ---- 0x43edd0 and 0x43f6e0: owner check then a virtual call
    for fn, name in ((F_EDD0, "edd0"), (F_F6E0, "f6e0")):
        for cc in (0, 1, 2, 0xFFFFFFFF, 0x101, 0x80000001):
            for anim in PRESETS_COMMON:
                s8 = rs.getrandbits(32) | 0x44
                yield case(f"{name} cc={cc:#x} {anim['name']}", fn, build(rs, anim, x_cc=cc, s8=s8))
        for s8 in (0, 0xFFFFFFFF, 4, 0xFFFFFFFB, 0x80000004):
            yield case(f"{name} flags {s8:#x} fire", fn, build(rs, NONE, x_cc=1, s8=s8, d20=rs.getrandbits(32) | 1))

    # ---- 0x43f720
    for s8 in (0, 4, 0xFFFFFFFF, 0xFFFFFFFB, 0x80000004, 0x12345678, 0x0000000C):
        for d20 in (0, 2, 0xFFFFFFFF):
            yield case(f"f720 flags {s8:#x} state {d20:#x}", F_F720, build(rs, NONE, s8=s8, d20=d20))
    for _ in range(4):
        yield case("f720 random", F_F720, build(rs, NONE, s8=rs.getrandbits(32), d20=rs.getrandbits(32)))

    # ---- 0x43fd10 (equal -> negated value to vtable+0x70) and 0x43fdc0 (equal -> value to vtable+0x6c)
    values = [0.0, 0.4, 0.5, 0.6, 1.5, 2.5, -0.5, -1.5, -2.5, 123456.789, -7.25, 3.0, 2147483647.0, -2147483647.0,
              2147483648.0, -2147483648.0, 1e12, -1e12, 1.0e-300, float("inf"), float("nan"), 4294967296.5]
    pairs = []
    for v in (0.0, 1.0, -3.25, 1e300, 2.0 ** 40):
        pairs.append((v, v, "equal"))
    pairs += [(0.0, -0.0, "plus zero vs minus zero"), (1.0, 1.0 + 2.0 ** -52, "differ in last bit"),
              (1.0, 2.0, "less"), (2.0, 1.0, "greater"), (-1.0, 1.0, "sign differs"),
              (float("nan"), 1.0, "nan left"), (1.0, float("nan"), "nan right"),
              (float("nan"), float("nan"), "nan both"), (3.0, 3.0 + 2.0 ** 20, "differ in high bits")]
    for fn, name, partner, other in ((F_FD10, "fd10", 0x80, 0x98), (F_FDC0, "fdc0", 0x98, 0x80)):
        for x in values:
            def setup(env, x=x, partner=partner, other=other, rs=rs):
                pass
            for anim in (NONE, DIRECT(1)):
                if anim is NONE and x not in (0.5, -0.5, 1.5, 4294967296.5):
                    continue
                key_partner = "d80" if partner == 0x80 else "d98"
                key_other = "d98" if partner == 0x80 else "d80"
                yield case(f"{name} x50={x!r} {anim['name']}", fn,
                           build(rs, anim, d50=x, d68=7.75, **{key_partner: 7.75, key_other: 9.25}))
        for a, b, text in pairs:
            key_partner = "d80" if partner == 0x80 else "d98"
            key_other = "d98" if partner == 0x80 else "d80"
            yield case(f"{name} compare {text} {a!r} {b!r}", fn, build(rs, NONE, d50=2.75, d68=a, **{key_partner: b, key_other: a}))
        yield case(f"{name} only the other double equals", fn,
                   build(rs, NONE, d50=2.75, d68=6.5, **{("d80" if other == 0x80 else "d98"): 6.5,
                                                         ("d80" if partner == 0x80 else "d98"): 8.5}))
        for _ in range(6):
            x = rs.uniform(-1e6, 1e6)
            v = rs.uniform(-100, 100)
            key_partner = "d80" if partner == 0x80 else "d98"
            yield case(f"{name} random", fn, build(rs, NONE, d50=x, d68=v, **{key_partner: v}))

    # ---- 0x43f030
    rets = [(DIRECT(1), True), (COUNTDOWN(1, 1, 1), True), (COUNTDOWN(1, 1, 0), True), (COUNTDOWN(3, 1, 1), True),
            (DECAY_SHORT(7, 3, 1), True), (DECAY_LONG(2, 6, 1), True),
            (DIRECT(0), False), (DIRECT(2), False), (DIRECT(0xFFFFFFFF), False), (COUNTDOWN(3, 2, 1), False),
            (DECAY_SHORT(7, 3, 0), False), (DECAY_LONG(2, 6, 3), False)] + [(n, False) for n in NONE_TAILS]
    combos = [(0, 0), (1, 0), (0, 1), (1, 1)]
    s40_cycle = [2, 0, 3, 1, 0xFE, 0xFD]
    n = 0
    for anim, hits in rets:
        for counter in ((0, 1, 3) if hits else (0, 2)):
            for flag, ptr in (combos if hits else combos[:1] + combos[3:]):
                n += 1
                x138 = tuple(rs.getrandbits(32) | 1 for _ in range(4))
                t220 = tuple(rs.getrandbits(32) | 1 for _ in range(4))
                if n % 11 == 0:
                    t220 = (0x80000000, 0, 0x7FFFFFFF, 5)
                yield case(f"f030 {anim['name']} counter={counter} flag={flag} ptr={ptr}", F_F030,
                           build(rs, anim, counter=counter, flag=flag, ptr3a0=ptr, s40=s40_cycle[n % 6],
                                 x138=x138, t220=t220))
    for s40 in (0, 1, 2, 3, 0xFD, 0xFE, 0xFF):
        yield case(f"f030 negate swap s40={s40:#x}", F_F030,
                   build(rs, DIRECT(1), counter=2, s40=s40, t220=(0x01020304, 0x0A0B0C0D, 0x11121314, 0x21222324)))
    for _ in range(4):
        yield case("f030 random", F_F030, build(rs, DIRECT(1), counter=rs.randrange(1, 5), flag=rs.randrange(2),
                                                ptr3a0=rs.randrange(2), s40=rs.getrandbits(8),
                                                t220=tuple(rs.getrandbits(32) for _ in range(4))))

    # ---- 0x43f450
    for anim in (NONE, DIRECT(2), DECAY_SHORT(7, 3, 1)):
        for s38 in (0xFFFFFFFF, 0, 0xFFFFFFFE, 0x7FFFFFFF):
            for flag, ptr in combos:
                if s38 != 0xFFFFFFFF and (flag, ptr) != (1, 1):
                    continue
                yield case(f"f450 state0 s38={s38:#x} flag={flag} ptr={ptr} {anim['name']}", F_F450,
                           build(rs, anim, state304=0, s38=s38, flag=flag, ptr38c=ptr, s8=rs.getrandbits(32)))
    times = [("before delay", 1000, 960, 50), ("one short", 1000, 951, 50), ("exact", 1000, 950, 50),
             ("after", 1000, 900, 50), ("wrapped start", 100, 4000000000, 5), ("zero delay", 1000, 1000, 0),
             ("zero start", 20, 0, 21), ("zero start exact", 20, 0, 20), ("huge delay", 1000, 0, 0xFFFFFFFF)]
    for state in (1, 2):
        for text, now, start, delay in times:
            for anim in (NONE, DIRECT(2)):
                yield case(f"f450 state{state} {text} {anim['name']}", F_F450,
                           build(rs, anim, state304=state, now=now, start3d8=start, delay3dc=delay,
                                 s38=0xFFFFFFFF, s8=rs.getrandbits(32), start3e0=1, delay3e4=0xFFFFFFFF))
    for state in (3, 4, 0xFFFFFFFF, 0x100, 0x80000000, 0x80000001):
        yield case(f"f450 state {state:#x}", F_F450,
                   build(rs, NONE, state304=state, s38=0xFFFFFFFF, now=1000, start3d8=0, delay3dc=0, flag=1, ptr38c=1))
    for s8 in (0, 0x10000, 0xFFFFFFFF):
        yield case(f"f450 state1 flags {s8:#x}", F_F450, build(rs, NONE, state304=1, now=1000, start3d8=0, delay3dc=1, s8=s8))

    # ---- 0x43f540: array of strings, trie lookup
    times540 = [("not yet", 1000, 960, 50), ("one short", 1000, 951, 50), ("exact", 1000, 950, 50),
                ("after", 1000, 900, 50), ("wrapped", 100, 4000000000, 5), ("zero delay", 1000, 1000, 0)]
    for text, now, start, delay in times540:
        yield case(f"f540 time {text}", F_F540, array_setup(rs, 0, 4, 4, 2, elapsed=(now, start, delay)))
    for lo, hi in ((0, 5), (-4, 3), (7, 7), (0xA, 0x10)):
        for stride in (4, 12):
            for pos in (0, 1, 2, 99):
                index = lo + min(pos, hi - lo) if pos != 99 else hi
                yield case(f"f540 in range {lo}..{hi} stride {stride} index {index}", F_F540,
                           array_setup(rs, lo, hi, stride, index))
    for kind in ("empty", "flat", "deep", "short", "mismatch", "dead"):
        for index in (0, 1, 2, 3, 4):
            yield case(f"f540 trie {kind} index {index}", F_F540,
                       array_setup(rs, 0, 4, 8, index, trie_kind=kind))
    yield case("f540 trie deep two byte keys", F_F540,
               array_setup(rs, 0, 4, 4, 1, trie_kind="deep", strings=[b"ba", b"bb", b"bc", b"b", b"ba"]))
    yield case("f540 trie flat longer keys", F_F540,
               array_setup(rs, 0, 4, 4, 2, trie_kind="flat", strings=[b"abc", b"bcd", b"a", b"b", b"zzz"]))
    # grow up (index above the array)
    for lo, hi, index in ((0, 3, 4), (0, 3, 6), (-2, 2, 3), (5, 5, 6), (0, 0, 2), (1, 9, 12)):
        for trie_kind in ("flat", "empty"):
            yield case(f"f540 grow high {lo}..{hi} index {index} trie {trie_kind}", F_F540,
                       array_setup(rs, lo, hi, 4, index, trie_kind=trie_kind))
    yield case("f540 grow high stride 8 one slot", F_F540, array_setup(rs, 0, 3, 8, 4))
    # grow down (index below the array)
    for lo, hi, index in ((2, 6, 1), (2, 6, 0), (0, 3, -1), (0, 3, -3), (3, 3, 2), (-1, 4, -4)):
        for trie_kind in ("flat", "empty"):
            yield case(f"f540 grow low {lo}..{hi} index {index} trie {trie_kind}", F_F540,
                       array_setup(rs, lo, hi, 4, index, trie_kind=trie_kind))
    yield case("f540 grow low stride 8 one slot", F_F540, array_setup(rs, 2, 6, 8, 1))
    # Growth failure (0x43f5ba..0x43f5e2) is not reachable: 0x4db6e0 leaves EBP = NULL and calls 0x4dc680, which
    # dereferences [EBP+4] before control returns, so the original itself faults on every allocation failure.
