"""Cases for level_one_batch_human_enemy_virtuals_03: Level 1 human enemies: shared Soldier and Officer virtuals, batch 3."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns

F_44DBB0, F_44DE30, F_44DF10 = 0x44DBB0, 0x44DE30, 0x44DF10
F_4407D0, F_4409D0, F_440B20 = 0x4407D0, 0x4409D0, 0x440B20
F_440C90, F_440410, F_440120, F_440420 = 0x440C90, 0x440410, 0x440120, 0x440420
RAND, COPY_RECT = 0x4A3050, 0x546D58

STR_BOUNCE, STR_FLAILING, STR_DROPPED = 0x5240E8, 0x527170, 0x5271B4
STR_BLOCKHIGH, STR_BLOCKLOW, STR_THROWN, STR_LIFTED = 0x527188, 0x52717C, 0x5271CC, 0x5271D8

ANIM_SLOTS = (0x344, 0x36C, 0x37C, 0x380, 0x384, 0x388)

DEFAULTS = dict(
    counter=0, lives=3, a408=False, a3c0=False, a3bc=False, c0c=1, anim=True, leaf=None, bounce_leaf=True,
    flag=0, g7224=0, kind=3, h38=-1, g53c9ac=True, g53c9a8=0, w6c=True, v410=True, rand=0, d40=0.0,
    ie=7,
)


def dwords(value):
    return struct.unpack("<II", struct.pack("<d", value))


def copy_rect(env, call):
    env.write(call.arguments[0], env.read(call.arguments[1], 16))
    return 1


def make(rng, **kw):
    """Return setup(env) for one entity. All random contents are drawn now, so both runs see the same bytes."""
    opt = {**DEFAULTS, **kw}
    ent_words = [rng.randrange(1, 0x7FFF) for _ in range(0x118)]
    p_words = [rng.randrange(1, 0x7FFF) for _ in range(0x50)]
    h_words = [rng.randrange(1, 0x7FFF) for _ in range(0x70)]
    q_words = [rng.randrange(1, 0x7FFF) for _ in range(12)]
    o_words = [rng.randrange(1, 0x7FFF) for _ in range(0x60)]
    frame_vals = [rng.randrange(0x100, 0x7FFF) for _ in ANIM_SLOTS]
    glob = [rng.randrange(0x100, 0x7FFFF) for _ in range(8)]
    s_words = [rng.randrange(1, 0x7FFF) for _ in range(0x20)]
    doubles = [rng.uniform(-900.0, 900.0) for _ in range(6)]
    leaf_value = rng.randrange(0x1000, 0x7FFFFF)
    rect = [rng.randrange(-500, 500) for _ in range(4)]

    def setup(env):
        env.override(COPY_RECT, copy_rect)
        env.override(RAND, returns(opt["rand"]))
        vt = env.object(0xB0, "vtable", fill=0)
        log = env.object(0x40, "log", fill=0)
        env.put(vt + 0x90, env.stub("virtual-90", "thiscall", 1, returns(glob[0])))
        env.put(vt + 0xA8, env.stub("virtual-a8", "thiscall", 0, returns(glob[1])))
        env.put(vt + 0x5C, env.stub("virtual-5c", "thiscall", 1, returns(glob[2])))
        env.put(vt + 0x44, env.stub("virtual-44", "thiscall", 0, returns(glob[3])))

        player = env.object(0x140, "player", words=p_words, fill=0)
        env.put(player + 0x10C, opt["lives"] & 0xFFFFFFFF)
        env.put(player + 0x118, *[v & 0xFFFFFFFF for v in rect])
        state = env.object(0x30, "state", words=q_words, fill=0)
        owner = env.object(0x180, "anim-owner", words=o_words, fill=0)
        env.put(owner + 0x16C, 0, 0)
        hero = env.object(0x1C0, "hero", words=h_words, fill=0)
        env.put(hero + 0x18C, owner)
        env.put(hero + 0x38, opt["h38"] & 0xFFFFFFFF)

        ent = env.object(0x460, "entity", words=ent_words, fill=0)
        env.put(ent + 0x00, vt)
        env.put(ent + 0x0C, player)
        env.put(ent + 0x10, state)
        env.put(ent + 0x12C, hero)
        env.put(ent + 0x18C, opt["kind"])
        env.put(ent + 0x1AC, opt["ie"] & 0xFFFFFFFF)
        env.put(ent + 0x410, glob[4] if opt["v410"] else 0)
        env.put(ent + 0x424, opt["counter"] & 0xFFFFFFFF)
        for off, key in ((0x408, "a408"), (0x3C0, "a3c0"), (0x3BC, "a3bc")):
            if opt[key]:
                c = env.object(0x80, "c", fill=0)
                b = env.object(0x20, "b", fill=0)
                a = env.object(0x20, "a", fill=0)
                env.put(a + 0x10, b)
                env.put(b + 0x10, c)
                env.put(c + 0x78, 0)
                env.put(ent + off, a)
            else:
                env.put(ent + off, 0)
        for i, slot in enumerate(ANIM_SLOTS):
            if opt["anim"]:
                frame = env.object(0x80, "frame", fill=0)
                env.put(frame + 0x1C, frame_vals[i])
                arr = env.object(8, "frames", fill=0)
                env.put(arr, frame)
                an = env.object(0x20, "animation", fill=0)
                env.put(an + 0x10, 1)
                env.put(an + 0xC, arr)
                env.put(ent + slot, an)
            else:
                env.put(ent + slot, 0)
        # doubles read by the original arithmetic (finite on purpose)
        env.put(ent + 0x40, *dwords(opt["d40"]))
        env.put(ent + 0x50, *dwords(doubles[0]))
        env.put(ent + 0x58, *dwords(doubles[1]))
        env.put(ent + 0x70, *dwords(doubles[2]))
        env.put(ent + 0x68, *dwords(doubles[3]))

        # globals
        env.put(0x532C0C, opt["c0c"])
        env.put(0x532C10, glob[5])
        env.put(0x537210, glob[6])
        env.put(0x537224, opt["g7224"])
        env.put(0x5430C4, glob[7])
        target = env.object(0x80, "scene", words=s_words[:0x20], fill=0)
        mid = env.object(0x20, "scene-mid", words=s_words[:8], fill=0)
        cell = env.object(8, "flag-cell", fill=0)
        env.put(cell, opt["flag"])
        env.put(mid + 0x14, cell)
        env.put(target + 0x6C, mid)
        env.put(0x537E88, target)
        # the string-table lookup used by the original
        root = env.object(0x20, "trie-root", fill=0)
        leafnode = env.object(0x20, "trie-leaf", fill=0)
        leaf_address = opt["leaf"]
        if leaf_address is not None:
            env.put(root, leafnode, leafnode)
            env.put(root + 8, 0)
            env.put(leafnode + 8, 0)
            env.put(leafnode + 0xC, leaf_address)
            env.put(leafnode + 0x10, leaf_value)
            env.put(0x537668 + 0x18, root)
        else:
            env.put(0x537668 + 0x18, 0)
        # LS_BOUNCE lookup for 0x43fe60 goes through the same table; leaf string is decided by 'leaf'
        # service object used by 0x48ce40
        if opt["g53c9ac"]:
            gobj = env.object(0x1C0, "service", fill=0)
            wobj = env.object(0x40, "service-slot", fill=0)
            env.put(gobj + 0x6C, wobj if opt["w6c"] else 0)
            env.put(0x53C9AC, gobj)
        else:
            env.put(0x53C9AC, 0)
        env.put(0x53C9A8, opt["g53c9a8"])
        env.put(0x53C9B0, glob[3])
        return {"ent": ent, "hero": hero, "player": player}

    return setup


def case(label, function, rng, **kw):
    return Case(label, function, make(rng, **kw), receiver=lambda t: t["ent"])


def cases(random_source):
    rng = random_source
    D = [rng.uniform(0.5, 400.0) * rng.choice((-1, 1)) for _ in range(8)]
    # ---- 0x44dbb0: the hit-counter state machine
    n = 0
    for counter in (-4, -1, 0, 1):
        for a408 in (False, True):
            for c0c in (0, 1):
                for anim, leaf in ((True, STR_BOUNCE), (False, None)):
                    d40 = D[n % 8] if (n % 2) else 0.0
                    n += 1
                    yield case(f"hit counter {counter} a={a408} g={c0c} anim={anim} d40={d40:.1f}", F_44DBB0, rng,
                               counter=counter, a408=a408, c0c=c0c, anim=anim, leaf=leaf, d40=d40)
    for counter in (2,):
        for leaf in (None, STR_BOUNCE):
            yield case(f"counter 2 reaches 3 leaf={leaf}", F_44DBB0, rng, counter=counter, a408=True, c0c=1, leaf=leaf)
    for counter in (3, 4, 50):
        for lives in (-2, 0, 1, 9):
            for anim in (True, False):
                for leaf in (None, STR_BOUNCE):
                    yield case(f"counter {counter} lives {lives} anim={anim} leaf={leaf}", F_44DBB0, rng,
                               counter=counter, lives=lives, anim=anim, leaf=leaf)
    # ---- 0x44de30
    for g7224 in (0, 1):
        for flag in (0, 1):
            for ie in (0, 3, -2):
                for leaf in (None, STR_THROWN):
                    yield case(f"thrown wrapper g={g7224} flag={flag} ie={ie} leaf={leaf}", F_44DE30, rng,
                               g7224=g7224, flag=flag, ie=ie, leaf=leaf)
    # ---- 0x44df10
    for r in (0, 32, 33, 99, 132, 50):
        for h38 in (-1, 0, 5):
            for g53c9ac in (False, True):
                for g53c9a8 in (0, 7):
                    for v410 in (False, True):
                        for w6c in (True, False):
                            if not g53c9ac and (not w6c or g53c9a8):
                                continue
                            yield case(f"rand {r} h38 {h38} svc={g53c9ac}/{g53c9a8}/{w6c} v410={v410}", F_44DF10, rng,
                                       rand=r, h38=h38, g53c9ac=g53c9ac, g53c9a8=g53c9a8, v410=v410, w6c=w6c,
                                       leaf=STR_LIFTED if (r % 2) else None)
    # ---- 0x4407d0
    for flag in (0, 1):
        for leaf in (None, STR_FLAILING):
            for anim in (True, False):
                for _ in range(2):
                    yield case(f"flailing flag={flag} leaf={leaf} anim={anim}", F_4407D0, rng, flag=flag, leaf=leaf, anim=anim)
    # ---- 0x4409d0
    for leaf in (None, STR_DROPPED):
        for _ in range(4):
            yield case(f"dropped leaf={leaf}", F_4409D0, rng, leaf=leaf)
    # ---- 0x440b20 and 0x440c90
    for fn, leaf, name, off in ((F_440B20, STR_BLOCKHIGH, "block high", "a3c0"), (F_440C90, STR_BLOCKLOW, "block low", "a3bc")):
        for ptr in (False, True):
            for c0c in (0, 1):
                for kind in (3, 4, 0):
                    for lf in (None, leaf):
                        for anim in (True, False):
                            if anim is False and (lf is None or kind != 3):
                                continue
                            yield case(f"{name} ptr={ptr} g={c0c} kind={kind} leaf={lf} anim={anim}", fn, rng,
                                       c0c=c0c, kind=kind, leaf=lf, anim=anim, **{off: ptr})
        yield case(f"{name} pointer chain with other slot", fn, rng, a3c0=True, a3bc=True, kind=3, leaf=leaf)
    # ---- 0x440410
    for _ in range(4):
        yield case("set flag", F_440410, rng)
    # ---- 0x440120
    for g7224 in (0, 1):
        for flag in (0, 1):
            for ie in (0, 1, 5, -3, 40):
                for leaf in (None, STR_THROWN):
                    yield case(f"thrown g={g7224} flag={flag} ie={ie} leaf={leaf}", F_440120, rng,
                               g7224=g7224, flag=flag, ie=ie, leaf=leaf, anim=(ie != 40))
    # ---- 0x440420
    for d40 in (0.0, D[0], D[1], D[2]):
        for leaf in (None, STR_LIFTED):
            for _ in range(3):
                yield case(f"lifted d40={d40:.1f} leaf={leaf}", F_440420, rng, d40=d40, leaf=leaf)
