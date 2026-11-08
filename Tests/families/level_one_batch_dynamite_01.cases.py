"""Cases for level_one_batch_dynamite_01: Level 1 player dynamite and dynamite states."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import sequence
from clawparity.world import animation, cstring, world

TICK_STEP = 0x5430C4
CLOCK = 0x537210
LIT_FLAG = 0x532C0C
LIT_VALUE = 0x532C10
MAX_UPDATE = 0x53C260
UPDATE_BASE = 0x541328
RAND = 0x4A3050
OPERATOR_NEW = 0x4F63EC

CONSTRUCT_BASE = 0x4084B0
UPDATE = 0x4089D0
CALLBACK = 0x43A850
CONSTRUCT = 0x43A910
ARM = 0x43B290
FUSE = 0x43B320
RAISE_MAX = 0x486E70

U32 = 0xFFFFFFFF
ANIMATOR = 0x188


def d(value):
    return struct.pack("<d", value)


def noise(random_source):
    return random_source.randrange(0x01010101, U32)


def scatter(env, random_source, base, size, skip=()):
    """Distinct non-zero words in a record, so that a store to a wrong offset changes the result."""
    for offset in range(0, size, 4):
        if offset not in skip:
            env.put(base + offset, noise(random_source))


# ---------------------------------------------------------------- animator
def animator(env, owner, seq, mode, value, delay=3, param=0, armed=0):
    """The owner's animation cursor at owner+0x188, steered through its cheap paths.

    Its +0x14 (delay) and +0x1c (finished) words are the owner's +0x19c and +0x1a4.
    mode "none": no sequence, so the cursor answers -1.
    mode "wait": a running delay without the repeat flag: answers +0x24, delay drops by one.
    mode "count": a running delay with the flag and param below it: answers +0x24.
    mode "done": delay expired (param >= delay) and cursor finished: answers +0x20, delay becomes 0.
    mode "done-zero": delay already 0 and cursor finished: answers +0x20.
    """
    a = owner + ANIMATOR
    env.put(a, 0x4C4C4C4C)
    env.put(a + 4, owner)
    env.put(a + 8, 0 if mode == "none" else seq)
    env.put(a + 0x0C, 0x1111)
    env.put(a + 0x10, 0)
    env.put(a + 0x1C, armed)
    env.put(a + 0x20, 0x5A5A5A5A, 0x6B6B6B6B)
    env.put(a + 0x28, 0x3F800000)
    if mode == "wait":
        env.put(a + 0x14, delay, 0)
        env.put(a + 0x24, value)
    elif mode == "count":
        env.put(a + 0x14, delay, 1)
        env.put(a + 0x24, value)
        env.put(TICK_STEP, min(param, delay - 1))
    elif mode == "done":
        env.put(a + 0x14, delay, 1)
        env.put(a + 0x1C, armed or 1)
        env.put(a + 0x20, value)
        env.put(TICK_STEP, delay + param)
    elif mode == "done-zero":
        env.put(a + 0x14, 0, 1)
        env.put(a + 0x1C, armed or 7)
        env.put(a + 0x20, value)
    else:
        env.put(a + 0x14, delay, 0)
    return a


def plain_world(env, random_source, owner_words=None, state_words=None, resources=None):
    return world(env, owner_words=owner_words, state_words=state_words, resources=resources)


def bare_instance(env, random_source, w, size=0x188, vtable=0):
    """A dynamite record filled by hand, for the entry points that run on an already built object."""
    this = env.object(size, "dynamite", fill=0)
    scatter(env, random_source, this, size)
    owner, state = w["owner"], w["state"]
    env.put(this, vtable)
    env.put(this + 0x0C, owner)
    env.put(this + 0x10, state)
    env.put(this + 0x12C, owner)
    env.put(this + 0x130, state)
    service = env.object(0x40, "level-object-service", fill=0x44)
    env.put(service + 8, owner)
    env.put(state + 0x0C, service)
    return this


def lay_out_owner(env, random_source, w, skip=()):
    owner = w["owner"]
    protected = {0x0C, 0x38, 0x6C}.union(skip)
    for offset in range(0x40, 0x200, 4):
        if offset not in protected and not (ANIMATOR <= offset < ANIMATOR + 0x2C):
            env.put(owner + offset, noise(random_source))


def seed_log(env):
    return env.object(0x800, "observations", fill=0)


def recorder(log, tag, snapshots=(), result=0, mutate=None):
    """A callback that appends what it saw to surviving memory and may change state behind the caller.

    Each entry is 0x40 bytes: tag, receiver, argument count, three arguments, then up to seven watched words.
    """
    def effect(env, call):
        index = env.get(log)
        at = log + 4 + index * 0x40
        arguments = list(call.arguments)[:3]
        env.put(at, tag, call.receiver, len(call.arguments), *(arguments + [0] * (3 - len(arguments))))
        for slot, address in enumerate(snapshots[:7]):
            env.put(at + 0x18 + 4 * slot, env.get(address))
        env.put(log, index + 1)
        if mutate:
            for address, value in mutate:
                env.put(address, value)
        return result
    return effect


# ------------------------------------------------------------ 0x486e70
def raise_max(old, base):
    def setup(env):
        env.put(MAX_UPDATE, old)
        env.put(UPDATE_BASE, base)
        return {}
    return setup


def raise_max_cases(random_source):
    for old, base, arg in ((5, 6, 7), (100, 1, 2), (13, 0, 13), (13, 0, 12), (13, 0, 14), (U32, 1, U32),
                           (0x80000000, 0x7FFFFFFF, 1), (0x7FFFFFFF, 1, 0x7FFFFFFF), (0, 0, 0), (1, U32, 1),
                           (U32, 0, U32), (0, U32, U32)):
        yield Case(f"raise max {old:#x} base {base:#x} by {arg:#x}", RAISE_MAX, raise_max(old, base), arguments=(arg,))
    for _ in range(12):
        yield Case("raise max random", RAISE_MAX, raise_max(noise(random_source), noise(random_source)),
                   arguments=(noise(random_source),))


# ------------------------------------------------------------- 0x43b290
def arm_setup(random_source, mode, value, flag, armed, delay, old_max, base, bits, param=0):
    def setup(env):
        w = plain_world(env, random_source, owner_words={8: bits})
        lay_out_owner(env, random_source, w, skip={8})
        owner = w["owner"]
        this = bare_instance(env, random_source, w)
        seq = animation(env, 40)
        env.put(TICK_STEP, param)
        animator(env, owner, seq, mode, value, delay, param, armed)
        env.put(this + 0x180, flag)
        env.put(MAX_UPDATE, old_max)
        env.put(UPDATE_BASE, base)
        return {"this": this, "owner": owner}
    return setup


def arm_cases(random_source):
    def make(label, *args, **kw):
        return Case(label, ARM, arm_setup(random_source, *args, **kw), receiver=lambda t: t["this"])

    for mode in ("wait", "count", "done", "done-zero"):
        for flag in (0, 1):
            for armed in (0, 0x12345):
                for delay in (1, 4):
                    yield make(f"arm {mode} flag {flag:#x} armed {armed:#x} delay {delay}", mode, 1, flag, armed,
                               delay, noise(random_source), noise(random_source) >> 4, noise(random_source),
                               param=random_source.randrange(0, 3))
    for mode, value in (("none", 1), ("wait", 0), ("wait", 2), ("count", U32), ("done", 3), ("done-zero", 0),
                        ("done-zero", 2), ("wait", 0x100000001 & U32)):
        for armed, delay in ((0, 1), (5, 6)):
            yield make(f"arm other {mode} {value:#x} armed {armed} delay {delay}", mode, value, 0, armed, delay,
                       noise(random_source), noise(random_source) >> 4, noise(random_source))
    # the global maximum: kept above, equal and below the new reach; and wrap-around
    for old, base in ((0x2000, 1), (0x1F5, 1), (0x1F4, 0), (0x1F4, 1), (0x1F3, 1), (0x1F4 + 0x1000, 0xFFFFE000),
                      (5, 0xFFFFFF00), (0, 0), (U32, 1), (U32, 0), (0x80000000, 0x7FFFFE0C), (0x7FFFFFFF, 0x80000000)):
        yield make(f"arm maximum {old:#x} base {base:#x}", "wait", 1, 0, noise(random_source), 2, old, base,
                   0x01020380)
    for bit in (0x80, 0x7F, 0xFF, 0, 0x100, 0xFFFFFF80, 0x80808080, 0x7F7F7F7F):
        yield make(f"arm owner flags {bit:#x}", "wait", 1, 0, 1, 2, 3, 4, bit)
    for _ in range(6):
        mode = random_source.choice(["none", "wait", "count", "done", "done-zero"])
        yield make(f"arm random {mode}", mode, random_source.choice([0, 1, 1, 2, noise(random_source)]),
                   random_source.choice([0, 0, noise(random_source)]),
                   random_source.choice([0, noise(random_source)]), random_source.randrange(1, 9),
                   noise(random_source), noise(random_source) >> 3, noise(random_source),
                   param=random_source.randrange(0, 12))


# ------------------------------------------------------------- 0x4089d0
NAN = struct.unpack("<d", struct.pack("<Q", 0x7FF8000000001234))[0]
NEG_NAN = struct.unpack("<d", struct.pack("<Q", 0xFFF8000000005678))[0]

DEFAULT_UPDATE = dict(
    elapsed="gt", clock=0x12345678, window=1000, cc=1, lit="lit", same=False, v=1.5, w=2.25, a=100.0, h=3.75,
    mode="wait", delay=3, param=1, m38=None, m34=None, tick=None, fuse=None,
)


def update_setup(random_source, **overrides):
    p = dict(DEFAULT_UPDATE)
    p.update(overrides)

    def setup(env):
        log = seed_log(env)
        resources = None
        f = p["fuse"]
        if f:
            logic = env.object(0x30, "glitter-logic", fill=0x6D)
            if f["hit"]:
                env.put(logic + 8, noise(random_source), noise(random_source), env.stub("glitter-logic", "cdecl", 1,
                                                                 recorder(log, 0x600, (), f["result"])))
                if f["hit"] == "no-method":
                    env.put(logic + 0x10, 0)
            resources = {"logic": {"GlitterBaby": logic}} if f["hit"] else {}
        w = plain_world(env, random_source, owner_words={0xC8: noise(random_source), 0xCC: p["cc"]},
                        resources=resources)
        lay_out_owner(env, random_source, w, skip={0xC8, 0xCC})
        owner = w["owner"]
        env.put(owner + 0xCC, p["cc"])
        vtable = env.object(0x40, "dynamite-vtable", fill=0)
        this = bare_instance(env, random_source, w, vtable=vtable)
        seq = animation(env, 40)
        animator(env, owner, seq, p["mode"], noise(random_source), p["delay"], p["param"], noise(random_source))
        if p["tick"] is not None:
            env.put(TICK_STEP, p["tick"])
        chain = env.object(0x20, "lit-a", fill=0x31)
        middle = env.object(0x20, "lit-b", fill=0x32)
        last = env.object(0x80, "lit-c", fill=0x33)
        env.put(last + 0x78, 0)
        env.put(chain + 0x10, middle)
        env.put(middle + 0x10, last)
        env.put(this + 0x154, 0 if p["lit"] == "none" else chain)
        env.put(LIT_FLAG, 0 if p["lit"] == "unlit" else 0x7A7A7A7A)
        env.put(LIT_VALUE, noise(random_source))
        # elapsed time against the fuse window, as unsigned differences
        clock = p["clock"]
        env.put(CLOCK, clock)
        spent = {"lt": p["window"] - 1, "eq": p["window"], "gt": p["window"] + 1,
                 "wrap": (clock - 0xFFFFFF00) & U32}[p["elapsed"]]
        env.put(this + 0x160, (clock - spent) & U32)
        env.put(this + 0x164, p["window"] if p["elapsed"] != "wrap" else 0x100)
        first = noise(random_source) & 0xFFFFFF
        env.put(this + 0x158, first)
        env.put(this + 0x15C, first if p["same"] else (first + 1 + random_source.randrange(0, 3)) & U32)
        env.write(this + 0x40, d(p["v"]))
        env.write(this + 0x50, d(p["h"]))
        env.write(this + 0x58, d(p["w"]))
        env.write(this + 0x70, d(p["a"]))
        env.write(this + 0xB8, d(-777.5))
        env.put(this + 0x60, 0x0BADF00D, 0x0DEADBEE)
        watch = (owner + 0xC8, owner + 0xCC, this + 0x154, this + 0x158, this + 0x15C, this + 0x160, LIT_FLAG)
        mutate38 = []
        mutate34 = []
        if p["m38"] is not None:
            mutate38.append((owner + 0xCC, p["m38"]))
        if p["m34"] == "unlight":
            mutate34.append((this + 0x154, 0))
        elif p["m34"] == "light":
            mutate34.append((this + 0x154, chain))
        elif p["m34"] == "lit-off":
            mutate34.append((LIT_FLAG, 0))
        elif p["m34"] == "lit-on":
            mutate34.append((LIT_FLAG, 0x5151))
        elif p["m34"] == "same":
            mutate34.append((this + 0x15C, first))
        elif p["m34"] == "differ":
            mutate34.append((this + 0x15C, (first + 9) & U32))
        elif p["m34"] == "bump":
            mutate34.append((this + 0x158, (first + 5) & U32))
        elif p["m34"] == "cc":
            mutate34.append((owner + 0xCC, 5))
        env.put(vtable + 0x30, env.stub("dynamite::fizzle", "thiscall", 0, recorder(log, 0x30, watch, 0x30303030)))
        env.put(vtable + 0x34, env.stub("dynamite::burn", "thiscall", 0, recorder(log, 0x34, watch, 0x34343434, mutate34)))
        env.put(vtable + 0x38, env.stub("dynamite::expire", "thiscall", 0, recorder(log, 0x38, watch, 0x38383838, mutate38)))
        env.put(vtable + 0x3C, noise(random_source))
        if f:
            env.put(this + 0x170, f["count"])
            env.write(this + 0x68, d(f["x"]))
            env.write(this + 0x70, d(f["y"]))
            env.put(owner + 0x118, f["lo_x"] & U32)
            env.put(owner + 0x120, f["hi_x"] & U32)
            env.put(owner + 0x11C, f["lo_y"] & U32)
            env.put(owner + 0x124, f["hi_y"] & U32)
            env.put(owner + 0x64, f["z"])
            env.put(owner + 0x10, 0, 0, 0, 0, 0, 0, f.get("block", 10))
            env.override(RAND, sequence(*f["rand"]))
            nodes = []
            for z, flag in f.get("list", ()):
                member = env.object(0x80, "listed-object", fill=0x35)
                env.put(member + 0x64, z)
                env.write(member + 0x0A, bytes([flag]))
                nodes.append(env.object(12, "list-node", fill=0))
                env.put(nodes[-1] + 8, member)
            for index, node in enumerate(nodes):
                env.put(node, nodes[index + 1] if index + 1 < len(nodes) else 0,
                        nodes[index - 1] if index else 0)
            if nodes:
                env.put(owner + 0x14, nodes[0], nodes[-1], len(nodes))

            def allocation(env_, call):
                index = env_.get(log)
                env_.put(log + 4 + index * 0x40, 0x400, call.receiver, call.arguments[0])
                env_.put(log, index + 1)
                return env_.object(call.arguments[0], name="allocation", fill=0xA5)

            env.override(OPERATOR_NEW, allocation)
        return {"this": this, "owner": owner, "log": log}
    return setup


def update_cases(random_source):
    def make(label, **kw):
        return Case(f"update {label}", UPDATE, update_setup(random_source, **kw), receiver=lambda t: t["this"])

    # control flow
    for cc in (0, 2, 0x80000001):
        for elapsed in ("lt", "gt", "wrap"):
            yield make(f"cc {cc:#x} elapsed {elapsed}", cc=cc, elapsed=elapsed, v=random_source.uniform(-9, 9))
    for elapsed in ("lt", "eq", "gt", "wrap"):
        for lit in ("none", "unlit", "lit"):
            for same in (False, True):
                yield make(f"elapsed {elapsed} lit {lit} same {same}", elapsed=elapsed, lit=lit, same=same,
                           v=random_source.uniform(0.5, 9), w=random_source.uniform(-9, 9),
                           a=random_source.uniform(-500, 500), h=random_source.uniform(-9, 9),
                           mode=random_source.choice(["wait", "count", "done", "none"]))
    # arithmetic branches
    zeros = (0.0, -0.0, NAN)
    values_v = zeros + (1.5, -3.25, 1e6)
    values_w = (0.0, -0.0, 0.5, -0.5, 7.0, -7.0, NAN, NEG_NAN)
    for v in values_v:
        for w in values_w:
            yield make(f"v {v!r} w {w!r}", v=v, w=w, a=random_source.uniform(-1000, 1000),
                       h=random_source.uniform(-9, 9))
    for a in (1e16, -1e16, 3e17, 2.0**53, 0.0, -0.5, 1e-300, 123456789.0625):
        for v, w in ((2.0, 0.5), (-4.0, -2.0)):
            yield make(f"a {a!r} v {v} w {w}", v=v, w=w, a=a)
    for _ in range(20):
        yield make("random arithmetic", v=random_source.choice([0.0, random_source.uniform(-50, 50)]),
                   w=random_source.uniform(-50, 50), a=random_source.uniform(-2000, 2000),
                   h=random_source.uniform(-50, 50), elapsed=random_source.choice(["lt", "gt", "eq"]),
                   same=random_source.random() < 0.4, lit=random_source.choice(["none", "unlit", "lit"]),
                   mode=random_source.choice(["wait", "count", "done", "done-zero", "none"]),
                   delay=random_source.randrange(1, 6), param=random_source.randrange(0, 4),
                   tick=random_source.randrange(0, 9), clock=noise(random_source))
    # a callback changes state the function reads again afterwards
    for m38 in (0, 1, 2, 8, 0x40):
        for cc in (1, 4):
            yield make(f"expire sets cc {m38} from {cc}", elapsed="gt", cc=cc, m38=m38, v=1.25, w=0.75)
    for m34 in ("unlight", "light", "lit-off", "lit-on", "same", "differ", "bump", "cc"):
        for lit, same in (("none", False), ("lit", True), ("unlit", False)):
            if True:
                yield make(f"burn {m34} lit {lit} same {same}", elapsed="lt", m34=m34, lit=lit, same=same,
                           v=random_source.uniform(1, 5), w=random_source.uniform(-5, 5))


# ------------------------------------------------------ 0x4084b0 and 0x43a910
LIT_KEY = "GAME_DYNAMITELIT"
HORZ_KEY = "GAME_DYNAMITEHORZ"
EXPLO_KEY = "GAME_DYNAMITEEXPLO"
BOOM_KEY = "GAME_KEGBOOM"


def sprite_sheet(env, random_source, first, last, frames=4, geometry=None):
    """A sprite resource whose frames carry distinct rectangles at +0x18 (x, y, width, height)."""
    resource = env.object(0x6C, "dynamite-sprite", fill=0)
    table = env.object(4 * frames, "dynamite-frames", fill=0)
    env.put(resource + 0x14, table)
    env.put(resource + 0x64, first, last)
    chosen = []
    for index in range(frames):
        frame = env.object(0x40, "dynamite-frame", fill=0x4B)
        rect = geometry if geometry is not None and index == first else (
            random_source.randrange(-300, 300), random_source.randrange(-300, 300),
            random_source.randrange(1, 90), random_source.randrange(1, 90))
        env.put(frame + 0x18, *(r & U32 for r in rect))
        env.put(table + 4 * index, frame)
        chosen.append(frame)
    return resource, chosen


def build_setup(random_source, owner_flags=0, x=None, y=None, lives=None, pose=None, clock=None,
                anims=(True, True, True), boom=True, sprite_mode="hit", stale_frame=False, fill=0x5C,
                first=1, last=2, geometry=None, collect=None, owner_noise=False):
    def setup(env):
        owner_words = {
            8: owner_flags,
            0x40: noise(random_source),
            0x4C: noise(random_source) if x is None else x,
            0x50: noise(random_source) if y is None else y,
            0x64: 0 if lives is None else lives,
            0x148: noise(random_source) & 0x3FF,
            0x14C: noise(random_source) & 0x3FF,
            0x158: noise(random_source) & 0xFF if pose is None else pose,
            0x164: noise(random_source),
            0xCC: noise(random_source),
            0xC8: noise(random_source),
        }
        state_words = {0x1C: noise(random_source), 0x2C: 0, 0x30: 0, 0x34: 0, 0x38: 0}
        sprites = {}
        animations = {}
        sounds = {}
        # distinct resource handles; they are only stored, never followed
        handles = [env.object(0x10, name, fill=0x70 + n) for n, name in enumerate(("lit", "horz", "explo", "boom"))]
        if anims[0]:
            animations[LIT_KEY] = animation(env, 30 + random_source.randrange(0, 90))
        if anims[1]:
            animations[HORZ_KEY] = handles[1]
        if anims[2]:
            animations[EXPLO_KEY] = handles[2]
        if boom:
            sounds[BOOM_KEY] = handles[3]
        sheet, frames = None, []
        if sprite_mode != "miss":
            lo, hi = (first, last) if sprite_mode == "hit" else (last + 1, last)
            sheet, frames = sprite_sheet(env, random_source, lo, hi, geometry=geometry)
            sprites[LIT_KEY] = sheet
        w = world(env, owner_words=owner_words, state_words=state_words,
                  resources={"sprites": sprites, "animations": animations, "sounds": sounds})
        owner = w["owner"]
        if owner_noise:
            for offset in range(0x80, 0x100, 4):
                if offset not in (0x80, 0xC8, 0xCC):
                    env.put(owner + offset, noise(random_source))
        if stale_frame:
            old = env.object(0x40, "stale-frame", fill=0x2D)
            env.put(old + 0x18, 11, 22, 33, 44)
            env.put(owner + 0x174, old)
        env.put(owner + 0x170, 0xDEAD5EED)
        env.put(owner + 0x16C, 0xDEAD5EEE)
        if clock is not None:
            env.put(CLOCK, clock)
        this = env.object(0x188, "new-dynamite", fill=fill)
        service = env.object(0x40, "level-object-service", fill=0)
        env.put(service + 8, owner)
        env.put(w["state"] + 0x0C, service)
        env.put(0x537E88, owner)
        return {"this": this, "owner": owner, "state": w["state"], "world": w["world"], "collision": w["collision"], "sheet": sheet,
                "frames": frames}
    return setup


def construct_cases(random_source):
    def make(function, label, **kw):
        return Case(f"{label}", function, build_setup(random_source, **kw), receiver=lambda t: t["this"],
                    arguments=(lambda t: t["owner"],))

    poses = (0, 1, U32, 5, 0xFFFFFFFD, 0x3FFFFFFF, 0x40000000, 0x7FFFFFFF, 0x80000000, 0xC0000000)
    for pose in poses:
        yield make(CONSTRUCT, f"construct pose {pose:#x}", pose=pose)
    for hits in range(16):
        flags = tuple(bool(hits & (1 << i)) for i in range(3))
        yield make(CONSTRUCT, f"construct animations {flags} sounds {bool(hits & 8)}", anims=flags,
                   boom=bool(hits & 8), pose=random_source.randrange(1, 60))
    for mode in ("hit", "miss", "empty"):
        for stale in (False, True):
            yield make(CONSTRUCT, f"construct sprite {mode} stale {stale}", sprite_mode=mode, stale_frame=stale,
                       pose=random_source.randrange(1, 60))
    for first, last in ((0, 0), (0, 3), (3, 2), (1, 1)):
        yield make(CONSTRUCT, f"construct frames {first}..{last}", first=first, last=last, pose=7)
    for lives in (0, 1, 0x137E, U32):
        yield make(CONSTRUCT, f"construct lives {lives:#x}", lives=lives, pose=3)
    for flags in (0, 0x20000, 0x40, 0x60, 0x80, 0x10000, 0x20, U32 & ~0x10):
        for lives in (0 if flags & 0x20000 else 9,):
            yield make(CONSTRUCT, f"construct flags {flags:#x} lives {lives}", owner_flags=flags, lives=lives, pose=2)
    for geometry in ((0, 0, 1, 1), (-5, -7, 40, 30), (100, 200, 17, 23), (0x7FFFFFF0, 3, 5, 5)):
        yield make(CONSTRUCT, f"construct frame rectangle {geometry}", geometry=geometry, first=2, last=2, pose=4)
    for fill in (0x00, 0xA7):
        yield make(CONSTRUCT, f"construct over fill {fill:#x}", fill=fill, pose=9)
        yield make(CONSTRUCT_BASE, f"base over fill {fill:#x}", fill=fill)
    for flags in (0x20000, 0x40, 0x10, U32):
        yield make(CONSTRUCT_BASE, f"base flags {flags:#x}", owner_flags=flags)
    for _ in range(8):
        yield make(CONSTRUCT, "construct random", x=noise(random_source), y=noise(random_source),
                   pose=random_source.choice([0, noise(random_source), random_source.randrange(-50, 50) & U32]),
                   lives=random_source.choice([0, 3, noise(random_source)]),
                   owner_flags=random_source.choice([0, noise(random_source) & ~0x10]),
                   anims=tuple(random_source.random() < 0.6 for _ in range(3)), boom=random_source.random() < 0.6,
                   sprite_mode=random_source.choice(["hit", "hit", "miss", "empty"]),
                   stale_frame=random_source.random() < 0.4, clock=noise(random_source),
                   fill=random_source.randrange(1, 256), first=random_source.randrange(0, 3),
                   last=random_source.randrange(0, 4))
        yield make(CONSTRUCT_BASE, "base random", x=noise(random_source), y=noise(random_source),
                   owner_flags=random_source.choice([0, noise(random_source) & ~0x10]), clock=noise(random_source),
                   fill=random_source.randrange(1, 256))


# ------------------------------------------------------------- 0x43a850
def terrain(env, random_source, w, log, width, height, shift_x, shift_y, tiles, result):
    """The collision plane the spawned dynamite consults for the tile under it.

    tiles lists tile words; the cell at each position is drawn from it. A tile id selects a handler whose
    method +0x20 records its two arguments in the log.
    """
    columns = ((width - 1) >> shift_x) + 1
    rows = ((height - 1) >> shift_y) + 1
    plane = env.object(0x100, "collision-plane", fill=0)
    row_table = env.object(4 * rows, "tile-rows", fill=0)
    cells = env.object(4 * rows * columns, "tile-cells", fill=0)
    for row in range(rows):
        env.put(row_table + 4 * row, row * columns)
        for column in range(columns):
            env.put(cells + 4 * (row * columns + column), random_source.choice(tiles))
    handlers = env.object(4 * 8, "tile-handlers", fill=0)
    for ident in range(8):
        vtable = env.object(0x30, "tile-handler-vtable", fill=0)
        handler = env.object(0x20, "tile-handler", words=[vtable], fill=0x3C)
        env.put(vtable, vtable)
        env.put(vtable + 0x20, env.stub(f"tile-handler-{ident}", "thiscall", 2,
                                        recorder(log, 0x500 + ident, (), result)))
        env.put(handlers + 4 * ident, handler)
    env.put(plane + 0x20, cells)
    env.put(plane + 0x24, row_table)
    env.put(plane + 0x30, width, height)
    env.put(plane + 0x8C, shift_x, shift_y)
    env.put(plane + 0x5C, 0)
    collision = w["collision"]
    env.put(collision + 0x5C, plane)
    env.put(collision + 0x4C, handlers)
    return plane


def registry_node(env, name, value):
    key = cstring(env, name, "registry-key")
    node = env.object(20, "registry-node", fill=0)
    env.put(node, node, node, 0, key, value)
    env.put(0x537668 + 0x18, node)


def callback_setup(random_source, command, existing=True, replace=False, request=None, plane=None, falling=None,
                   fail_alloc=False, **build):
    base = build_setup(random_source, **build)

    def setup(env):
        tokens = base(env)
        owner, state = tokens["owner"], tokens["state"]
        log = seed_log(env)
        if plane is not None:
            terrain(env, random_source, tokens, log, *plane)
        if falling is not None:
            registry_node(env, "LS_FALLING", falling)
        table = env.object(0x30, "callback-table", fill=0)
        object_record = env.object(0x80, "state-object", words=[table], fill=0x97)
        env.put(object_record + 0x10, state)
        env.put(state + 0x1C, command)
        env.put(state + 0x18, object_record if existing else 0)
        watch = (state + 0x18, state + 0x1C, owner + 0x6C)
        for offset in (4, 8, 0x0C, 0x1C, 0x20):
            tag = 0x100 + offset
            mutate = ()
            if replace and offset in (0x1C, 0x20):
                mutate = ((state + 0x18, 0x0BADC0DE), (state + 0x1C, 0x55))
            env.put(table + offset, env.stub(f"state-{offset:x}", "thiscall", 1 if offset in (4, 8, 0x0C) else 0,
                                             recorder(log, tag, watch, 0x7000 + offset, mutate)))
        if command not in (0, 0x1D, 0x1E, 0x3E8):
            entry = env.object(4, "numeric-state-name", words=[cstring(env, f"STATE_{command:08x}")])
            env.put(0x5376A0, command, command, entry, entry, 4, 0, 0)

        def allocation(env_, call):
            index = env_.get(log)
            env_.put(log + 4 + index * 0x40, 0x400, call.receiver, call.arguments[0], env_.get(state + 0x1C),
                     env_.get(state + 0x18))
            env_.put(log, index + 1)
            if fail_alloc:
                return 0
            return env_.object(call.arguments[0] if request is None else request, name="allocation", fill=0x5C)

        env.override(OPERATOR_NEW, allocation)
        tokens["log"] = log
        return tokens
    return setup


def callback_cases(random_source):
    def make(label, command, **kw):
        return Case(f"callback {label}", CALLBACK, callback_setup(random_source, command, **kw),
                    arguments=(lambda t: t["owner"],))

    geometry = (3, 4, 8, 10)
    tiles = ([2], [0x12340003], [0xEEEEEEEE], [U32], [0, 1, 2, 3, 4, 5, 6, 7], [0xEEEEEEEE, 5], [U32, 6])
    for index, tile in enumerate(tiles):
        for result in (1, 0, 2):
            yield make(f"create over tiles {index} result {result}", 0, pose=random_source.randrange(1, 40),
                       plane=(64, 48, 4, 4, tile, result), x=random_source.randrange(0, 64),
                       y=random_source.randrange(0, 40), geometry=geometry, falling=random_source.choice([None, 0x77]))
    for x, y in ((-5, 7), (7, -50), (-1, -1), (500, 7), (7, 500), (500, 500), (0, 0), (63, 37), (64, 38),
                 (0x80000000, 3), (0x7FFFFFFF, 0x7FFFFFFF)):
        yield make(f"create at {x},{y}", 0, pose=3, plane=(64, 48, 4, 4, [1, 2, 3], 1), x=x & U32, y=y & U32,
                   geometry=geometry, falling=0x51)
    for shift_x, shift_y in ((0, 0), (1, 2), (3, 3), (5, 2)):
        yield make(f"create shifts {shift_x},{shift_y}", 0, pose=1, plane=(37, 29, shift_x, shift_y, [3, 4], 1),
                   x=random_source.randrange(0, 37), y=random_source.randrange(0, 20), geometry=geometry)
    yield make("create no sprite", 0, sprite_mode="miss", anims=(False, True, False), boom=False, pose=3,
               plane=(64, 48, 4, 4, [1], 1), x=10, y=10)
    yield make("create without animation", 0, anims=(False, True, True), pose=3, plane=(64, 48, 4, 4, [1], 1),
               x=10, y=10, geometry=geometry)
    yield make("create over stale object", 0, existing=True, pose=0, plane=(64, 48, 4, 4, [1], 1), x=12, y=9,
               geometry=geometry)
    for command in (0x1D, 0x1E):
        yield make(f"dispatch {command:#x}", command)
        yield make(f"dispatch {command:#x} replaces state", command, replace=True)
    yield make("running 0x3e8 does nothing", 0x3E8)
    for command in (1, 2, 28, 31, 999, 1001, 0x80000000, U32, 0x3E7):
        yield make(f"release {command:#x}", command)
    for _ in range(3):
        yield make("release random", noise(random_source) | 0x40000)


FUSE_DEFAULT = dict(count=1, x=100.5, y=200.25, lo_x=-20, hi_x=30, lo_y=-10, hi_y=15, z=7, hit=True, result=0,
                    rand=(12345, 6789, 4242, 99))


def fuse_cases(random_source):
    def make(label, fuse=None, **kw):
        f = dict(FUSE_DEFAULT)
        f.update(fuse or {})
        kw.setdefault("cc", 2)
        return Case(f"fuse {label}", FUSE, update_setup(random_source, fuse=f, **kw), receiver=lambda t: t["this"])

    yield make("one spawn")
    for count in (0, 1, 2, 3, U32, 0x80000000, 5):
        yield make(f"count {count:#x}", dict(count=count, rand=[random_source.randrange(0, 0x7FFF) for _ in range(12)]))
    ranges = ((-20, 30), (5, 5), (5, 4), (0, -1), (7, 2), (-100, -100), (0x7FFFFFFF, 0x7FFFFFFF),
              (0x7FFFFFFF, 0x80000000), (0x80000000, 0x7FFFFFFF), (-0x7000, 0x7000), (3, 0x7FFFFFFE))
    rand_sets = ((0, 1, 2, 3), (0x7FFF, 0x4001, 77, 78), (U32, 0x80000000, 0x80000001, 5), (4, 4, 9, 9))
    for index, (lo, hi) in enumerate(ranges):
        rands = rand_sets[index % 4]
        yield make(f"x range {lo}..{hi} rand {rands[0]:#x}", dict(lo_x=lo, hi_x=hi, rand=rands, count=2))
        rands = rand_sets[(index + 1) % 4]
        yield make(f"y range {lo}..{hi} rand {rands[0]:#x}", dict(lo_y=lo, hi_y=hi, rand=rands, count=2))
    for x, y in ((0.0, 0.0), (-3.75, -8.5), (0.5, -0.5), (1e6 + 0.375, -1e6 - 0.625), (2e9, -2e9), (-0.0, 0.25)):
        yield make(f"position {x},{y}", dict(x=x, y=y, count=2,
                                            rand=[random_source.randrange(0, 0x7FFF) for _ in range(6)]))
    for z in (0, 1, 2, 0x137E, U32, 0x80000000):
        yield make(f"owner priority {z:#x}", dict(z=z))
    for entries in (((1, 0),), ((20, 0),), ((20, 2),), ((20, 0), (30, 0)), ((3, 0), (20, 2), (30, 0)),
                    ((4, 0), (5, 0)), ((7, 0),), ((8, 0), (6, 0)), ((20, 0xFF),), ((20, 1), (9, 0))):
        yield make(f"list {entries}", dict(list=entries, count=2, z=7,
                                            rand=[random_source.randrange(0, 0x7FFF) for _ in range(6)]))
    for cc in (1, 2, 8):
        for lit in ("none", "lit"):
            yield make(f"update cc {cc} lit {lit}", dict(count=2), cc=cc, lit=lit, elapsed="gt",
                       v=random_source.uniform(1, 4), w=random_source.uniform(-4, 4))
    for _ in range(10):
        yield make("random", dict(count=random_source.randrange(1, 4), x=random_source.uniform(-500, 500),
                                  y=random_source.uniform(-500, 500), lo_x=random_source.randrange(-300, 300),
                                  hi_x=random_source.randrange(-300, 300), lo_y=random_source.randrange(-300, 300),
                                  hi_y=random_source.randrange(-300, 300), z=random_source.randrange(0, 40),
                                  rand=[noise(random_source) & 0x7FFF for _ in range(8)]),
                   cc=random_source.choice([1, 2]), lit="none")


def cases(random_source):
    yield from raise_max_cases(random_source)
    yield from arm_cases(random_source)
    yield from update_cases(random_source)
    yield from construct_cases(random_source)
    yield from callback_cases(random_source)
    yield from fuse_cases(random_source)
