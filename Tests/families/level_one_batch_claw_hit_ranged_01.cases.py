"""Cases for level_one_batch_claw_hit_ranged_01: Level 1 Claw hit reactions and ranged helpers."""
import random

from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

M32 = 0xFFFFFFFF
NEW = 0x4F63EC
RAND = 0x4A3050
ACTOR_INIT_SLOT = 0x5137F0 + 0x28  # vtable the actor factory 0x4c8be0 installs before initialising

F_405F80, F_41C9F0, F_41CAB0, F_41CB80, F_41DD80, F_41E660, F_4207A0 = (
    0x405F80, 0x41C9F0, 0x41CAB0, 0x41CB80, 0x41DD80, 0x41E660, 0x4207A0)

G_FLAG, G_VALUE = 0x534874, 0x5349DC
G_POWER, G_CHEAT, G_MODE_A, G_MODE_B = 0x534EAC, 0x53725C, 0x537218, 0x537228


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def registry(env, r, entries, buckets):
    """A string table as 0x4f6286 reads it, embedded at owner+0x10. Nodes: [next, 0, key, value], with decoys."""
    owner = env.object(0x40, "registry-owner", words=words_of(r, 0x10))
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(owner + 0x10 + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if r.random() < 0.5 else node)
    return owner


def resource(env, r, first, last):
    """An animation resource for 0x4c7970: +0x14 word table, +0x64 first, +0x68 last."""
    table = env.object(4 * 16, "frame-words", words=words_of(r, 16))
    obj = env.object(0x80, "resource", words=words_of(r, 0x20))
    env.put(obj + 0x14, table)
    env.put(obj + 0x64, first & M32)
    env.put(obj + 0x68, last & M32)
    return obj


def seeds(random_source, count):
    return [random_source.getrandbits(32) for _ in range(count)]


# ---------------------------------------------------------------------------------------------- 0x405f80

def setup_405f80(flag, same, seed):
    def setup(env):
        r = random.Random(seed)
        value = r.randrange(1, 1 << 32)
        obj = env.object(0x30, "object", words=words_of(r, 12))
        env.put(obj + 0xC, value)
        env.put(G_FLAG, flag)
        other = {"same": value, "plus": (value + 1) & M32, "minus": (value - 1) & M32,
                 "zero": 0, "random": r.randrange(1, 1 << 32)}[same]
        env.put(G_VALUE, other)
        return {"obj": obj}
    return setup


# ---------------------------------------------------------------------------------------------- 0x4207a0

def setup_4207a0(seed, decoys=True):
    def setup(env):
        r = random.Random(seed)
        obj = env.object(0x40, "object", words=words_of(r, 16))
        vtable = env.object(0x140, "vtable", words=words_of(r, 0x50))
        marker = r.randrange(1, 1 << 32)

        def slot(env, call):
            env.put(call.receiver + 0x10, marker, call.receiver, call.arguments[0] if call.arguments else 0)
            return marker

        env.put(obj, vtable)
        if decoys:
            for offset in (0x8C, 0x90, 0x98, 0x9C, 0x94 - 0x20, 0x94 + 0x20):
                env.put(vtable + offset, env.stub(f"decoy-{offset:x}", "thiscall", 0, returns(offset)))
        env.put(vtable + 0x94, env.stub("slot-94", "thiscall", 0, slot))
        return {"obj": obj}
    return setup


# ---------------------------------------------------------------------------------------------- 0x41e660

def setup_41e660(*, flags_bit0=True, bit400=True, busy=0, mode=1, face=0, dx=0, dy=0, seed=0, wide=False):
    """dx = claw x - target x, dy = (claw h - target y - target h + claw y)."""
    def setup(env):
        r = random.Random(seed)
        span = 1 << 30 if wide else 3000
        x4 = r.randrange(-span, span)
        x1 = (x4 + dx) & M32
        y1, h1, y4 = (r.randrange(-3000, 3000) for _ in range(3))
        h4 = (h1 - y4 + y1 - dy) & M32
        claw = env.object(0x140, "claw", words=words_of(r, 0x50))
        target = env.object(0x180, "target", words=words_of(r, 0x60))
        state = env.object(0x20, "state", words=words_of(r, 8))
        env.put(claw + 0x4C, x1)
        env.put(claw + 0x50, y1 & M32)
        env.put(claw + 0xCC, mode & M32)
        env.put(claw + 0x124, h1 & M32)
        env.put(target + 0x4C, x4 & M32)
        env.put(target + 0x50, y4 & M32)
        env.put(target + 0x124, h4)
        junk = r.randrange(0, 1 << 32) & ~0x401
        env.put(target + 0x164, junk | (1 if flags_bit0 else 0) | (0x400 if bit400 else 0))
        env.put(state, face, busy)
        return {"claw": claw, "target": target, "state": state, "junk": r.randrange(1, 1 << 32)}
    return setup


def case_41e660(label, **options):
    return Case(label, F_41E660, setup_41e660(**options),
                arguments=(lambda t: t["claw"], lambda t: t["junk"], lambda t: t["state"], lambda t: t["target"]))


# ---------------------------------------------------------------------------------------------- bullets and dynamite

def shooter(env, r, *, present, face, ammo_slot, ammo, bullets=None, fail_registry=False, position=None, rand_x=None):
    """A claw, its state, the scene with a free-node pool and the context's name registries.

    present: names found in the context registry (+0x14). bullets: None, 'in' or 'out' for the GAME_BULLETS entry (+0x10).
    The actor initialiser at 0x5137f8+0x28 is replaced so that the real factory 0x4c8be0 runs around it.
    """
    claw = env.object(0x1B0, "claw", words=words_of(r, 0x6C))
    state = env.object(0x130, "claw-state", words=words_of(r, 0x4C))
    world = env.object(0x60, "world", words=words_of(r, 0x18))
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for i in range(63):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    env.put(scene + 0x0C, context)
    env.put(world + 0x08, scene)
    env.put(claw + 0x0C, world)
    x, y, z = position if position is not None else (r.randrange(-900, 900), r.randrange(-900, 900), r.randrange(-50, 50))
    env.put(claw + 0x4C, x & M32)
    env.put(claw + 0x50, y & M32)
    env.put(claw + 0x64, z & M32)
    env.put(state, face)
    env.put(state + 4 * 0x15, r.randrange(1, 400))
    env.put(state + 4 * 0x16, r.randrange(-300, 300) & M32)
    env.put(state + 4 * ammo_slot, ammo & M32)
    env.put(state + 4 * 0x3A, r.randrange(1, 1 << 32))
    env.put(state + 4 * 0x40, r.randrange(0, 1 << 32), r.randrange(1, 1 << 32), r.randrange(1, 1 << 32))

    metadata = {}
    entries = {}
    for name in present:
        metadata[name] = env.object(0x18, "metadata", words=words_of(r, 6))
        entries[name] = metadata[name]
    for name in (b"OtherBullet", b"PistolBullets", b"Dynamit"):
        if name not in entries:
            entries[name] = r.randrange(1, 1 << 32)
    env.put(context + 0x14, registry(env, r, entries, r.choice((3, 5, 7))))
    bullets_entries = {}
    if bullets == "in":
        bullets_entries[b"GAME_BULLETS"] = resource(env, r, r.randrange(0, 12), 15)
    elif bullets == "out":
        bullets_entries[b"GAME_BULLETS"] = resource(env, r, 9, r.randrange(0, 9))
    bullets_entries[b"GAME_BULLET"] = r.randrange(1, 1 << 32)
    env.put(context + 0x10, registry(env, r, bullets_entries, r.choice((3, 5, 7))))

    fill = r.randrange(1, 256)
    env.override(NEW, lambda e, c: e.object(c.arguments[0], "allocation", fill=fill))
    callback = env.stub("service-callback", "cdecl", 1, returns(0))
    f164, f40, priority = (r.randrange(0, 1 << 32) for _ in range(3))

    def init(env, call):
        actor = call.receiver
        env.put(actor + 0x164, f164)
        env.put(actor + 0x40, f40)
        env.put(actor + 0x64, priority)
        env.put(env.get(actor + 0x6C) + 0x10, callback)
        return 1

    env.put(ACTOR_INIT_SLOT, env.stub("actor-initializer", "thiscall", 4, init))
    return {"claw": claw, "state": state, "scene": scene, "junk": r.randrange(1, 1 << 32)}


def bullet_case(label, function, name, ammo_slot, seed, *, found=True, face=0, ammo=3, bullets=None, position=None):
    def setup(env):
        r = random.Random(seed)
        return shooter(env, r, present=(name,) if found else (), face=face, ammo_slot=ammo_slot, ammo=ammo,
                       bullets=bullets, position=position)
    return Case(label, function, setup,
                arguments=(lambda t: t["claw"], lambda t: t["junk"], lambda t: t["state"]))


def pistol(label, seed, **options):
    return bullet_case(label, F_41C9F0, b"PistolBullet", 0x1C, seed, **options)


def magic(label, seed, **options):
    return bullet_case(label, F_41CAB0, b"MagicBullet", 0x1D, seed, **options)


def dynamite_case(label, seed, *, found=True, face=0, ammo=3, low=0, base=None, high=None, position=None):
    """Dynamite power: 200 * (current - low) / (high - low), clamped to 0..200 and negated when facing left."""
    def setup(env):
        r = random.Random(seed)
        tokens = shooter(env, r, present=(b"Dynamite",) if found else (), face=face, ammo_slot=0x1E, ammo=ammo,
                         position=position)
        state = tokens["state"]
        b = r.randrange(-100000, 100000) if base is None else base
        env.put(state + 4 * 0x40, (b + low) & M32, b & M32, (b + high) & M32)
        return tokens
    return Case(label, F_41CB80, setup,
                arguments=(lambda t: t["claw"], lambda t: t["junk"], lambda t: t["state"]))


# ---------------------------------------------------------------------------------------------- 0x41dd80

def setup_41dd80(seed, *, busy=0, move=1, kind=4, ammo=(3, 3, 3), face=0, extra_names=False):
    def setup(env):
        r = random.Random(seed)
        claw = env.object(0x1C0, "claw", words=words_of(r, 0x70))
        other = env.object(0x40, "other", words=words_of(r, 0x10))
        state = env.object(0x140, "claw-state", words=words_of(r, 0x50))
        world = env.object(0x60, "world", words=words_of(r, 0x18))
        entries = {}
        if extra_names:
            entries[b"CLAW_POSTDYNAMITE"] = r.randrange(1, 1 << 32)
            entries[b"CLAW_DUCKPOSTDYNAMITE"] = r.randrange(1, 1 << 32)
        env.put(world + 0x2C, registry(env, r, entries, r.choice((3, 5))))
        env.put(claw + 0x0C, world)
        env.put(other + 0x1C, kind & M32)
        env.put(state, face)
        env.put(state + 4, busy)
        env.put(state + 4 * 0x0C, move & M32)
        env.put(state + 4 * 0x1C, *[a & M32 for a in ammo])
        for address in (G_POWER, G_CHEAT, G_MODE_A, G_MODE_B):
            env.put(address, 0)
        env.override(RAND, returns(99))
        return {"claw": claw, "other": other, "state": state}
    return setup


def case_41dd80(label, seed, **options):
    return Case(label, F_41DD80, setup_41dd80(seed, **options),
                arguments=(lambda t: t["claw"], lambda t: t["other"], lambda t: t["state"]))


# ---------------------------------------------------------------------------------------------- the cases

def cases(random_source):
    rs = random_source

    # 0x405f80: flag and the compared word.
    for flag in (0, 1, 0x80000000, 0xFFFFFFFF, rs.randrange(2, 1 << 31)):
        for same in ("same", "plus", "minus", "zero", "random"):
            yield Case(f"405f80 flag {flag:#x} {same}", F_405F80, setup_405f80(flag, same, rs.getrandbits(32)),
                       receiver=lambda t: t["obj"])
    for _ in range(6):
        yield Case("405f80 random", F_405F80,
                   setup_405f80(rs.choice((0, 1, rs.getrandbits(32) or 1)), rs.choice(("same", "random", "plus")),
                                rs.getrandbits(32)),
                   receiver=lambda t: t["obj"])

    # 0x4207a0: jump through vtable slot 0x94, with decoys in the neighbouring slots.
    for index in range(6):
        yield Case(f"4207a0 thunk {index}", F_4207A0, setup_4207a0(rs.getrandbits(32), decoys=index % 3 != 2),
                   receiver=lambda t: t["obj"])

    # 0x41e660: reach test. Every comparison is hit on both sides of its boundary.
    edge = (-0x15, -0x14, -0x13, -1, 0, 1, 0x13, 0x14, 0x15)
    for bit400 in (False, True):
        edx = 0 if bit400 else 0x14
        for face in (0, 1):
            for dx in edge:
                for dy in (0, 20, -20, 21, -21):
                    if dy != 0 and dx not in (-edx - 1, -edx, edx, edx + 1, 0):
                        continue
                    yield case_41e660(f"41e660 face {face} 400={bit400} dx {dx} dy {dy}", bit400=bit400, face=face,
                                      dx=dx, dy=dy, seed=rs.getrandbits(32), mode=1 + (dx & 1))
    for dx in (-0x29, -0x28, -0x27, 0x27, 0x28, 0x29, -1000, 1000):
        for face in (0, 1):
            yield case_41e660(f"41e660 far dx {dx} face {face}", bit400=True, face=face, dx=dx, dy=3,
                              seed=rs.getrandbits(32), mode=2)
            yield case_41e660(f"41e660 far dx {dx} face {face} short", bit400=False, face=face, dx=dx, dy=-3,
                              seed=rs.getrandbits(32), mode=1)
    for dy in (-0x40, -22, -19, -1, 1, 19, 22, 0x40, 0x7FFFFF):
        yield case_41e660(f"41e660 vertical {dy}", dy=dy, seed=rs.getrandbits(32), face=0)
        yield case_41e660(f"41e660 vertical {dy} facing", dy=dy, seed=rs.getrandbits(32), face=1, dx=3)
    for mode in (0, 3, 4, 0x10001, 0x10002, 0xFFFFFFFF, 0x80000001):
        yield case_41e660(f"41e660 mode {mode:#x}", mode=mode, seed=rs.getrandbits(32), dx=0, dy=0)
    for busy in (1, 2, 0x80000000, 0xFFFFFFFF):
        yield case_41e660(f"41e660 busy {busy:#x}", busy=busy, seed=rs.getrandbits(32), dx=0, dy=0)
    for bit400 in (False, True):
        yield case_41e660(f"41e660 no flag 1 400={bit400}", flags_bit0=False, bit400=bit400,
                          seed=rs.getrandbits(32), dx=0, dy=0)
    for wide in (True,):
        for dx in (-0x15, 0, 0x15):
            for face in (0, 1):
                yield case_41e660(f"41e660 large coordinates dx {dx} face {face}", wide=True, dx=dx, dy=0, face=face,
                                  seed=rs.getrandbits(32), bit400=False)
    for _ in range(24):
        dx, dy = rs.randrange(-60, 60), rs.randrange(-40, 40)
        yield case_41e660("41e660 random", bit400=rs.random() < 0.5, face=rs.randrange(0, 3), dx=dx, dy=dy,
                          seed=rs.getrandbits(32), mode=rs.choice((1, 2, 1, 2, 0, 3)), busy=rs.choice((0, 0, 0, 1)),
                          flags_bit0=rs.random() < 0.9)

    # 0x41c9f0: pistol bullet.
    for face in (0, 1, 0x7FFF0000):
        for ammo in (-3, 0, 1, 2, 0x7FFFFFFF):
            for bullets in (None, "in", "out"):
                if face == 0x7FFF0000 and bullets != "in":
                    continue
                yield pistol(f"pistol face {face:#x} ammo {ammo} bullets {bullets}", rs.getrandbits(32), face=face,
                             ammo=ammo, bullets=bullets)
    for face in (0, 1):
        for ammo in (0, 5):
            yield pistol(f"pistol missing resource face {face} ammo {ammo}", rs.getrandbits(32), found=False,
                         face=face, ammo=ammo, bullets="in")
    for position in ((0, 0, 0), (-1, -1, -1), (0x200000, 0, 5), (0x100000, 7, 0x7FFFFFFF)):
        yield pistol(f"pistol position {position}", rs.getrandbits(32), position=position, bullets="in", ammo=9)
    for _ in range(12):
        yield pistol("pistol random", rs.getrandbits(32), found=rs.random() < 0.85, face=rs.choice((0, 1, 2)),
                     ammo=rs.randrange(-2, 30), bullets=rs.choice((None, "in", "out")))

    # 0x41cab0: magic bullet.
    for face in (0, 1, 0x7FFF0000):
        for ammo in (-3, 0, 1, 2, 0x7FFFFFFF):
            yield magic(f"magic face {face:#x} ammo {ammo}", rs.getrandbits(32), face=face, ammo=ammo)
    for face in (0, 1):
        for ammo in (0, 5):
            yield magic(f"magic missing resource face {face} ammo {ammo}", rs.getrandbits(32), found=False,
                        face=face, ammo=ammo)
    for position in ((0, 0, 0), (-1, -1, -1), (0x200000, 0, 5), (0x100000, 7, 0x7FFFFFFF)):
        yield magic(f"magic position {position}", rs.getrandbits(32), position=position, ammo=9)
    for _ in range(12):
        yield magic("magic random", rs.getrandbits(32), found=rs.random() < 0.85, face=rs.choice((0, 1, 2)),
                    ammo=rs.randrange(-2, 30))

    # 0x41cb80: dynamite. Fraction n/d scaled by 200, truncated, clamped to 0..200, negated when facing left.
    fractions = ((0, 7), (1, 1), (1, 2), (1, 200), (1, 201), (199, 200), (200, 200), (201, 200), (399, 400),
                 (400, 401), (401, 400), (2, 3), (3, 7), (-5, 10), (5, -10), (-5, -10), (-3, 7), (7, -3), (-2, -3),
                 (0, 0), (5, 0), (-5, 0), (100, 1000), (1000, 100), (123456, 654321), (-123456, 654321),
                 (9000000, 3), (-9000000, -3))
    for n, d in fractions:
        for face in (0, 1):
            yield dynamite_case(f"dynamite {n}/{d} face {face}", rs.getrandbits(32), face=face, low=n, high=d,
                                ammo=rs.randrange(1, 9), base=rs.randrange(-100000, 100000))
    for ammo in (0, 1, -1, 0x80000000, 0x7FFFFFFF, 0xFFFFFFFF):
        yield dynamite_case(f"dynamite ammo {ammo:#x}", rs.getrandbits(32), face=1, low=50, high=100, ammo=ammo)
    for face in (0, 1):
        yield dynamite_case(f"dynamite missing face {face}", rs.getrandbits(32), found=False, face=face, low=30,
                            high=60)
    for position in ((0, 0, 0), (-1, -1, -1), (0x200000, 0, 5)):
        yield dynamite_case(f"dynamite position {position}", rs.getrandbits(32), position=position, low=10, high=20)
    for _ in range(12):
        yield dynamite_case("dynamite random", rs.getrandbits(32), found=rs.random() < 0.85,
                            face=rs.choice((0, 1, 2)), low=rs.randrange(-300, 600), high=rs.randrange(-300, 600),
                            ammo=rs.randrange(-1, 20))

    # 0x41dd80: choose the action from the move and the kind of the held weapon.
    kinds = (4, 0x19, 0x1A, 0x1B, 0, 1, 3, 0x18, 5, 0x80000004)
    for move in (1, 2, 3):
        for kind in kinds:
            for ammo in ((0, 0, 0), (4, 5, 6)):
                yield case_41dd80(f"41dd80 move {move} kind {kind:#x} ammo {ammo}", rs.getrandbits(32), move=move,
                                  kind=kind, ammo=ammo, face=rs.choice((0, 1)), extra_names=rs.random() < 0.5)
    for move in (0, 4, 0xB, 0xC, 0xD, 0x12, 0x100, 0x80000001, 0xFFFFFFFF):
        yield case_41dd80(f"41dd80 other move {move:#x}", rs.getrandbits(32), move=move, kind=4)
        yield case_41dd80(f"41dd80 other move {move:#x} kind 0x1a", rs.getrandbits(32), move=move, kind=0x1A)
    for move in (1, 2, 3):
        for busy in (1, 2, 0x80000000):
            yield case_41dd80(f"41dd80 busy {busy:#x} move {move}", rs.getrandbits(32), busy=busy, move=move, kind=4)
    for face in (0, 1, 7):
        for move, kind in ((1, 4), (2, 0x1A), (3, 5), (3, 0x19), (1, 9)):
            for ammo in ((-1, 2, -3), (2, -1, 3), (1, 1, 1)):
                yield case_41dd80(f"41dd80 face {face} move {move} kind {kind:#x} ammo {ammo}", rs.getrandbits(32),
                                  face=face, move=move, kind=kind, ammo=ammo, extra_names=True)
    for _ in range(24):
        yield case_41dd80("41dd80 random", rs.getrandbits(32), move=rs.choice((1, 2, 3, 3, 2, 1, 0, 4)),
                          kind=rs.choice(kinds), busy=rs.choice((0, 0, 0, 1)), face=rs.choice((0, 1)),
                          ammo=tuple(rs.randrange(-2, 9) for _ in range(3)), extra_names=rs.random() < 0.5)
