"""Cases for level_one_batch_respawn_01: Level 1 respawn controller and command siblings."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

RESPAWN = 0x46BE40
RESTART = 0x46C110
MARK_FLAGGED = 0x46E2D0
TAIL_A = 0x46F1C0  # jumps to 0x4d1fd0
TAIL_B = 0x46F1D0  # jumps to 0x4d2000
SET_POSITION = 0x42D5C0

PLAYER_GLOBAL = 0x537E88
CIRCLE_KEY = b"GAME_CIRCLEFADE\0"
FLAG_KEY = b"GAME_FLAGWAVE\0"
SCRATCH_FLAG = 0x534EB4  # set to 1 by 0x46c110 when a state field is nonzero
TIME_SLOT = 0x546DF0
SPEED_GLOBAL = 0x53725C  # read by 0x415ce0 (called by 0x46c110)
OTHER_GLOBALS = (0x52C6E4, 0x532C10, 0x532C0C)

W, H = 200, 150  # screen size fields of the first state helper


def u32(value):
    return value & 0xFFFFFFFF


def f32(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


# ---------------------------------------------------------------------------
# A Python model of the wrap/clamp arithmetic, used only to choose inputs.

def wrap_axis(v, enabled, size, limit, left):
    if enabled:
        if v < 0:
            v += size
        elif size <= v:
            v -= size
        if size <= limit and v < left and v <= limit - size:
            v += size
    return v


# ---------------------------------------------------------------------------
# World builder

DEFAULTS = dict(
    glob=True,           # the global player pointer is set
    active=1,            # state +0x2c
    player_flags=0,      # byte at player +0x40
    px=-5, py=-50,       # player +0x4c / +0x50
    q_present=True,      # player +0x6c
    r_present=True,      # q +0x14
    layer_present=True,  # u +0x24
    y_present=True,      # layer +0x5c
    ywrap=12,            # flag bits 4 (x) and 8 (y) of the respawn sprite
    ycfg_x=(10, 100, 100),   # size, limit, left
    ycfg_y=(10, 100, 100),
    yoff=(0, 0),         # added to respawn offsets: (Y+0x50 - Y+0x40, Y+0x54 - Y+0x44)
    z2="match",          # None, "match", "mismatch" : respawn sprite +0xb0
    containers="empty",  # layout of the three containers hanging off +0xb0
    items=(),            # list of (flags_164, flags_8) hung off the second object
    map="full",          # scene map: none (no buckets), empty (one empty bucket), full
    circle_hit=False,    # the map holds a GAME_CIRCLEFADE entry
    flag_hit=False,      # the map holds a GAME_FLAGWAVE entry
    decoy=False,         # an unrelated entry sits first in the bucket
    zflag=0,             # +0x30 of the scene object
    s44=-1,              # state +0x44
    a9c=0,               # first helper +0x9c
    a30=0,               # first helper +0x30 (timing branch, kept off)
    r120=7,
    nspr=0, idx=-1,
    sprite_flags=(2,),
    speed=0,
    fx=(),               # ((method, call number, action), ...) with method in q, v24 and action in clear, swap
    link_none=False,     # state +0xc is zero
    v_minus=False,       # the stacker pointer is -0x10
    layer_flag=0,        # layer +8
    r_x=40, r_y=30, r_count=5,
)


def build_lookup(env, scene, mode, circle_hit, flag_hit, decoy):
    """Hash map hanging off scene+0x10: buckets at +0x14, bucket count at +0x18 (one bucket)."""
    if mode == "none":
        env.put(scene + 0x14, 0, 1)
        return
    buckets = env.object(16, "buckets", fill=0)
    env.put(scene + 0x14, buckets, 1)
    chain = []
    if decoy:
        chain.append((b"NOT_THE_KEY\0", 0x5555))
    if circle_hit:
        chain.append((CIRCLE_KEY, 0))
    if flag_hit:
        chain.append((FLAG_KEY, 0))
    nodes = []
    for key, _ in chain:
        value = env.object(0x40, "map-value", fill=0)
        env.put(value, 0x11111111, 0x22222222, 0x33333333, 0x44444444)
        text = env.object(len(key), "key", data=key)
        node = env.object(0x20, "node", fill=0)
        env.put(node + 8, text, value)
        nodes.append(node)
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0)
    if nodes:
        env.put(buckets, nodes[0])


def sprite(env, flags, name, serial):
    obj = env.object(0x200, name, fill=0)
    env.put(obj + 8, flags)
    env.put(obj + 0x10, f32(5.5 + serial), f32(3.25 + serial), f32(0.5 + serial / 8), f32(0.75 - serial / 16))
    env.put(obj + 0x30, 64 + serial, 48 + serial)
    env.put(obj + 0x70, 8 + serial, 6 + serial)
    env.put(obj + 0x78, 3 + serial, 2 + serial)
    return obj


def _world(env, rs, **options):
    o = dict(DEFAULTS, **options)
    t = {}
    log = env.object(0x200, "log", fill=0)
    t["log"] = log

    def record(base, receiver_slot=True):
        def effect(env, call):
            n = env.calls_so_far(call.function)
            slot = base + 16 * (n - 1) if n <= 8 else base + 16 * 7
            env.put(slot, call.receiver, *(list(call.arguments) + [0, 0])[:2])
            return 0x7000 + n
        return effect

    player = env.object(0x80, "player", fill=0)
    queue = env.object(0x40, "queue", fill=0)
    rec = env.object(0x140, "record", fill=0)
    state = env.object(0x270, "state", fill=0)
    helper_a = env.object(0x100, "helper-a", fill=0)
    helper_b = env.object(0x40, "helper-b", fill=0)
    link = env.object(0x40, "links", fill=0)
    stacker = env.object(0x40, "stacker", fill=0)
    stack_vt = env.object(0x80, "stacker-vtable", fill=0)
    mover = env.object(0x40, "mover", fill=0)
    mover_vt = env.object(0x80, "mover-vtable", fill=0)
    layer = env.object(0x80, "layer", fill=0)
    scene = env.object(0x40, "scene", fill=0)
    sprites_array = env.object(64, "sprite-array", fill=0)
    t.update(player=player, queue=queue, rec=rec, state=state, a=helper_a, b=helper_b, link=link,
             stacker=stacker, mover=mover, layer=layer, scene=scene)

    if o["glob"]:
        env.put(PLAYER_GLOBAL, player)
    else:
        env.put(PLAYER_GLOBAL, 0)
    env.put(player + 0x40, o["player_flags"])
    env.put(player + 0x4C, u32(o["px"]), u32(o["py"]))
    env.put(player + 0x6C, queue if o["q_present"] else 0)
    env.put(queue + 0x1C, 0x5A5A5A5A)
    env.put(queue + 0x14, rec if o["r_present"] else 0)
    env.put(rec + 0x4C, u32(o["r_x"]), u32(o["r_y"]))
    env.put(rec + 0x80, o["r_count"])
    env.put(rec + 0x120, o["r120"])

    env.put(state + 4, helper_a)
    env.put(state + 0xC, link)
    env.put(state + 0x10, 0)
    env.put(state + 0x2C, o["active"])
    env.put(state + 0x44, u32(o["s44"]))
    env.put(state + 0x160, *[0xC0DE0000 + i for i in range(0x3C)])
    env.put(helper_a + 0x7C, W, H)
    env.put(helper_a + 0x9C, o["a9c"])
    env.put(helper_a + 0x30, o["a30"])
    env.put(helper_b + 0x14, 0xB014, 0xB018)
    env.put(link + 4, helper_b)
    env.put(link + 8, stacker)
    env.put(link + 0xC, mover)
    env.put(link + 0x24, layer if o["layer_present"] else 0)
    env.put(link + 0x28, scene)

    env.put(stacker, stack_vt)

    def with_fx(method, base_effect):
        plan = {number: action for name, number, action in o["fx"] if name == method}

        def effect(env, call):
            result = base_effect(env, call)
            action = plan.get(env.calls_so_far(call.function))
            if action == "clear":
                env.put(layer + 0x5C, 0)
            elif action == "swap":
                env.put(layer + 0x5C, t["y_alt"])
            return result
        return effect

    env.put(queue + 0x10, env.stub("player-queue-method", "cdecl", 1, with_fx("q", record(log))))
    env.put(stack_vt + 0x24, env.stub("stacker-method-24", "thiscall", 1, with_fx("v24", record(log + 0x80))))
    env.put(stack_vt + 0x28, env.stub("stacker-method-28", "thiscall", 1, record(log + 0x100)))
    env.put(mover, mover_vt)
    env.put(mover_vt + 0x34, env.stub("mover-method-34", "thiscall", 2, record(log + 0x140)))

    # scene object and its two lookups
    env.put(scene + 0x30, o["zflag"])
    build_lookup(env, scene, o["map"], o["circle_hit"], o["flag_hit"], o["decoy"])

    # layer
    env.put(layer + 8, o["layer_flag"])
    env.put(layer + 0x38, sprites_array)
    for i in range(8):
        flags = o["sprite_flags"][i % len(o["sprite_flags"])] | 2
        env.put(sprites_array + 4 * i, sprite(env, flags, "layer-sprite", i + 1))
    env.put(layer + 0x3C, o["nspr"])
    env.put(layer + 0x60, u32(o["idx"]))

    def make_respawn(flags, xcfg, ycfg, serial):
        y = sprite(env, flags, "respawn-sprite", serial)
        env.put(y + 0x30, xcfg[0])
        env.put(y + 0x34, ycfg[0])
        env.put(y + 0x48, xcfg[1])
        env.put(y + 0x4C, ycfg[1])
        env.put(y + 0x40, xcfg[2])
        env.put(y + 0x44, ycfg[2])
        env.put(y + 0x50, u32(xcfg[2] + o["yoff"][0]))
        env.put(y + 0x54, u32(ycfg[2] + o["yoff"][1]))
        env.put(y + 0x84, 0x8484)
        env.put(y + 0x88, 0x8888)
        return y

    if o["y_present"]:
        y = make_respawn(o["ywrap"], o["ycfg_x"], o["ycfg_y"], 0)
        y_alt = make_respawn(o["ywrap"] ^ 4, o["ycfg_x"], o["ycfg_y"], 20)
        t["y"], t["y_alt"] = y, y_alt
        env.put(layer + 0x5C, y)
        for target in (y, y_alt):
            if o["z2"]:
                z2 = env.object(0x100, "container-owner", fill=0)
                inner = env.object(0x40, "owner-body", fill=0)
                env.put(z2, inner)
                fx, fy = struct.unpack("<ff", struct.pack("<II", env.get(target + 0x10), env.get(target + 0x14)))
                if o["z2"] == "match":
                    env.put(z2 + 0x68, int(fx), int(fy))
                else:
                    env.put(z2 + 0x68, int(fx) + 3, u32(int(fy) - 2))
                containers = []
                for k in range(3):
                    c = env.object(0x80, f"container-{k}", fill=0)
                    env.put(c + 0x28, 10, 0, 3, 3)  # first rectangle word beyond the limit: empty iteration
                    containers.append(c)
                env.put(z2 + 4, *containers)
                env.put(target + 0xB0, z2)
    else:
        t["y"] = 0
        t["y_alt"] = 0
        env.put(layer + 0x5C, 0)

    # flagged-object list hanging off the stacker (+0x14)
    nodes = []
    for item_flags in o["items"]:
        node = env.object(0x10, "list-node", fill=0)
        if item_flags is not None:
            item = env.object(0x180, "list-item", fill=0)
            env.put(item + 8, item_flags[1])
            env.put(item + 0x164, item_flags[0])
            env.put(node + 8, item)
        nodes.append(node)
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0)
    if nodes:
        env.put(stacker + 0x14, nodes[0])
    if o["v_minus"]:
        env.put(link + 8, u32(-0x10))
    if o["link_none"]:
        env.put(state + 0xC, 0)
    env.put(SPEED_GLOBAL, o["speed"])
    env.put(0x532C0C, 0)  # 0x4208e0 returns at once while this is zero
    env.put(0x532C10, 0x4C0FFEE0 | o["r120"] & 0xF)
    env.put(0x52C6E4, 0x600DF00D)
    # 0x42abf0 (reached by both controllers) reads timeGetTime, a declared scripted fixture
    env.override(TIME_SLOT, lambda e, c: 0x12345)
    return t


def world(env, rs, **options):
    return _world(env, rs, **options)


SEED = [None]


def call(label, function, **options):
    return Case(label, function, lambda env: world(env, SEED[0], **options), receiver=lambda t: t["state"])


def respawn(label, **options):
    return call(label, RESPAWN, **options)


def restart(label, **options):
    return call(label, RESTART, **options)


CFG = {"pass": (10, 100, 100), "short-limit": (10, 5, 100), "past-left": (10, 100, 0), "past-limit": (10, 12, 100)}
WRAPS = {"none": 0, "x": 4, "y": 8, "both": 12}


def cases(random_source):
    SEED[0] = rs = random_source

    # --- 0x46be40 -------------------------------------------------------------------------------------------
    yield respawn("respawn: no player", glob=False)
    yield respawn("respawn: no player and inactive", glob=False, active=0)
    yield respawn("respawn: inactive", active=0)
    yield respawn("respawn: active flag is a high bit", active=0x80000000)
    for r_present in (False, True):
        for fx in ((), (("q", 1, "clear"),), (("q", 1, "swap"),)):
            yield respawn(f"respawn: no respawn sprite r={r_present} fx={fx}", y_present=False, r_present=r_present, fx=fx)

    # wrap and clamp arithmetic, x axis
    for name, cfg in CFG.items():
        for pf in (0, 2):
            for px in (-45, -5, 5, 35, 45):
                yield respawn(f"respawn: x {name} px={px} flags={pf}", ycfg_x=cfg, player_flags=pf, px=px, py=37)
    for pf in (0, 2):
        for px in (-29, -27, 1, 3):
            yield respawn(f"respawn: x past-limit edge px={px} flags={pf}", ycfg_x=CFG["past-limit"], player_flags=pf, px=px, py=37)
    # y axis
    for name, cfg in CFG.items():
        for py in (-60, -50, -40, 37, 50):
            yield respawn(f"respawn: y {name} py={py}", ycfg_y=cfg, px=5, py=py)
    for py in (-54, -52, 34, 36):
        yield respawn(f"respawn: y past-limit edge py={py}", ycfg_y=CFG["past-limit"], px=5, py=py)
    # wrap flags off
    for name, wrap in WRAPS.items():
        for px, py in ((-5, -50), (45, 50), (5, 37)):
            yield respawn(f"respawn: wrap {name} {px},{py}", ywrap=wrap, px=px, py=py)
    # clamp of the final coordinates
    for yo in (-500, -40, -35, -34, -33, 0, 150, 164, 165, 166, 500):
        yield respawn(f"respawn: x offset {yo}", ywrap=0, px=5, py=37, yoff=(yo, 0))
        yield respawn(f"respawn: y offset {yo}", ywrap=0, px=5, py=37, yoff=(0, yo))
    yield respawn("respawn: both offsets below", ywrap=0, yoff=(-500, -500))
    yield respawn("respawn: both offsets above", ywrap=0, yoff=(500, 500))

    # the two named lookups on the scene
    for zflag in (0, 1, 0x100):
        for map_mode in ("none", "empty", "full"):
            for circle_hit in (False, True):
                for flag_hit in (False, True):
                    for decoy in (False, True):
                        if map_mode != "full" and (circle_hit or flag_hit or decoy):
                            continue
                        for s44 in (-1, 0):
                            if zflag and (circle_hit or decoy or s44 == 0):
                                continue
                            yield respawn(f"respawn: scene z={zflag} map={map_mode} circle={circle_hit} flag={flag_hit} decoy={decoy} s44={s44}",
                                          zflag=zflag, map=map_mode, circle_hit=circle_hit, flag_hit=flag_hit, decoy=decoy, s44=s44)
    for s44 in (1, 0x7FFFFFFF, 0xFFFFFFFE, 0x10000FFFF):
        yield respawn(f"respawn: s44={s44:#x}", s44=s44 & 0xFFFFFFFF, flag_hit=True, circle_hit=True)

    # containers, flagged list and virtual-call side effects
    for z2 in (None, "match", "mismatch"):
        for fx in ((), (("v24", 1, "clear"),), (("v24", 1, "swap"),), (("v24", 2, "clear"),), (("q", 1, "clear"),), (("q", 1, "swap"),)):
            yield respawn(f"respawn: z2={z2} fx={fx}", z2=z2, fx=fx)
    for items in (((0x2000, 0),), ((0, 0),), ((0x2000, 0x5),), ((0x1FFF, 0x10000),), (None,),
                  ((0x2000, 1), (0, 2), None, (0x2000, 3)), ((0xFFFF, 0), (0x4000, 0))):
        yield respawn(f"respawn: items {items}", items=items)
    for nspr, idx in ((0, -1), (1, 0), (3, 1), (5, 4), (8, 7)):
        yield respawn(f"respawn: layer sprites {nspr} idx {idx}", nspr=nspr, idx=idx)
    yield respawn("respawn: timing helper flag set is not reached with zero", a30=0, r_present=True, r120=0x99)

    # randomized geometry
    for n in range(40):
        pick = lambda seq: seq[rs.randrange(len(seq))]
        cfg_x = pick(list(CFG.values()))
        cfg_y = pick(list(CFG.values()))
        yield respawn(f"respawn: random {n}", ycfg_x=cfg_x, ycfg_y=cfg_y, ywrap=pick([0, 4, 8, 12, 12, 12]),
                      px=rs.randrange(-120, 260), py=rs.randrange(-120, 260), player_flags=pick([0, 2, 0xFD, 0xFF]),
                      yoff=(rs.randrange(-300, 300), rs.randrange(-300, 300)), r_x=rs.randrange(-1000, 1000),
                      r_y=rs.randrange(-1000, 1000), s44=pick([-1, 0, 5]), zflag=pick([0, 0, 1]),
                      circle_hit=bool(rs.randrange(2)), flag_hit=bool(rs.randrange(2)), decoy=bool(rs.randrange(2)),
                      r120=rs.randrange(1, 1 << 30), z2=pick([None, "match", "mismatch"]),
                      items=pick([(), ((0x2000, rs.randrange(1 << 20)),), ((rs.randrange(1 << 16), 0), (0x2000, 7))]))

    # --- 0x46c110 -------------------------------------------------------------------------------------------
    yield restart("restart: no player", glob=False)
    yield restart("restart: no queue", q_present=False)
    yield restart("restart: no record", r_present=False)
    for a9c in (0, 1, 0xFFFF0000):
        yield restart(f"restart: helper flag {a9c:#x}", a9c=a9c)
    for nspr in (0, 1, 2, 3, 5, 8):
        for idx in (-1, 0, 1, 2, 4, 7):
            if nspr == 0 and idx not in (-1, 0, 7):
                continue
            yield restart(f"restart: sprites {nspr} skip {idx}", nspr=nspr, idx=idx,
                          sprite_flags=((2, 3, 6, 7, 10, 11, 14, 15) if nspr > 3 else (2, 7, 11)))
    for speed in (0, 1, 0x80000000):
        yield restart(f"restart: speed global {speed:#x}", speed=speed)
    for r_count in (0, 1, 0x7FFFFFFF, 0xFFFFFFFF, 0x80000000):
        yield restart(f"restart: counter {r_count:#x}", r_count=r_count)
    for r_x, r_y in ((40, 30), (0, 0), (-7, 13), (1000, -1000), (3, 3), (-1, -1), (100000, 50000)):
        for wrap in (0, 4, 8, 12):
            yield restart(f"restart: record position {r_x},{r_y} wrap {wrap}", r_x=r_x, r_y=r_y, ywrap=wrap | 0,
                          nspr=2, idx=0)
    for z2 in (None, "match", "mismatch"):
        for fx in ((), (("q", 1, "clear"),), (("q", 2, "clear"),), (("q", 2, "swap"),), (("v24", 1, "clear"),),
                   (("v24", 1, "swap"),), (("v24", 2, "clear"),), (("v24", 2, "swap"),)):
            yield restart(f"restart: z2={z2} fx={fx}", z2=z2, fx=fx, nspr=1, idx=-1)
    for n in range(30):
        pick = lambda seq: seq[rs.randrange(len(seq))]
        yield restart(f"restart: random {n}", nspr=rs.randrange(0, 9), idx=rs.randrange(-1, 8),
                      sprite_flags=tuple(pick([2, 3, 6, 7, 10, 11, 14, 15]) for _ in range(8)),
                      ywrap=pick([0, 4, 8, 12, 15, 1]), r_x=rs.randrange(-5000, 5000), r_y=rs.randrange(-5000, 5000),
                      r_count=rs.randrange(1 << 32), a9c=pick([0, rs.randrange(1, 1 << 32)]), speed=pick([0, 1]),
                      z2=pick([None, "match", "mismatch"]))

    # --- 0x46e2d0 -------------------------------------------------------------------------------------------
    flagged = (
        (), (None,), ((0x2000, 0),), ((0, 0),), ((0x2000, 0x10),), ((0x2000, 0x10000),), ((0xFFFFDFFF, 0xFFFFFFFF),),
        ((0x2000, 1), (0x2000, 2), (0x2000, 4)), ((0x2000, 1), None, (0, 8), (0x2001, 16), (0x4000, 32)),
        ((0x20, 0x100), (0x2000, 0x100), (0x1000, 0x200)),
    )
    yield call("mark: no links", MARK_FLAGGED, link_none=True)
    yield call("mark: stacker minus sixteen", MARK_FLAGGED, v_minus=True, items=((0x2000, 1),))
    for items in flagged:
        for z2 in (None, "match"):
            yield call(f"mark: items {items} z2={z2}", MARK_FLAGGED, items=items, z2=z2)
    yield call("mark: no layer", MARK_FLAGGED, layer_present=False, items=((0x2000, 1),))
    yield call("mark: no respawn sprite", MARK_FLAGGED, y_present=False, items=((0x2000, 1),))
    for n in range(12):
        items = tuple((rs.randrange(1 << 16) | (rs.randrange(2) << 13), rs.randrange(1 << 20)) if rs.randrange(5) else None
                      for _ in range(rs.randrange(0, 6)))
        yield call(f"mark: random {n}", MARK_FLAGGED, items=items, z2=rs.choice([None, "match"]))

    # --- 0x46f1c0 and 0x46f1d0 ------------------------------------------------------------------------------
    for address, name in ((TAIL_A, "tail-a"), (TAIL_B, "tail-b")):
        for y_present in (False, True):
            for z2 in (None, "match", "mismatch"):
                if not y_present and z2:
                    continue
                for wrap in (0, 12):
                    yield Case(f"{name}: sprite={y_present} z2={z2} wrap={wrap}", address,
                               lambda env, y_present=y_present, z2=z2, wrap=wrap: world(env, rs, y_present=y_present, z2=z2, ywrap=wrap),
                               receiver=lambda t: t["layer"])

    # --- 0x42d5c0 -------------------------------------------------------------------------------------------
    values = (0, 1, -1, 7, 63, 64, 65, -64, -65, 200, 1000, -1000, 4000)
    for flags in range(16):
        for n in range(6):
            a = values[(flags + n * 5) % len(values)]
            b = values[(flags * 3 + n * 7 + 2) % len(values)]
            if n == 5:
                a, b = rs.randrange(-3000, 3000), rs.randrange(-3000, 3000)
            yield Case(f"position: flags {flags:#x} args {a},{b}", SET_POSITION,
                       lambda env, flags=flags: world(env, rs, ywrap=flags | 2),
                       receiver=lambda t: t["y"], arguments=(u32(a), u32(b)))

    # Readability mutation controls: distinguish the two period fields and the
    # inclusive upper-bound path at 0x46bec0 / 0x46beea (and the later sweep).
    for px, py in ((-45, -60), (-29, -54), (35, 37), (45, 50)):
        yield respawn(f"respawn: distinct wrap periods {px},{py}",
                      ycfg_x=(13, 31, 24), ycfg_y=(19, 42, 30), px=px, py=py)
    yield respawn("respawn: horizontal upper bound equals period",
                  ycfg_x=(10, 10, 100), px=-40, py=37)
    yield respawn("respawn: vertical upper bound equals period",
                  ycfg_y=(10, 10, 100), px=5, py=-65)

    def active_screen_service(env):
        tokens = world(env, rs)
        wrapper = env.object(0x30, "screen-service-wrapper", fill=0)
        interface = env.object(0x10, "screen-service-interface", fill=0)
        methods = env.object(0x40, "screen-service-methods", fill=0)
        env.put(tokens["a"] + 0x14, 1)
        env.put(tokens["a"] + 0x50, wrapper)
        env.put(wrapper + 0x1C, interface)
        env.put(interface, methods)
        # 0x42d420 -> 0x4b55a0 dispatches +0x28; 0x42d440 ->
        # 0x4b55b0 dispatches +0x2c with argument zero. Both remain real callees.
        env.put(methods + 0x28, env.stub("screen-service-begin", "thiscall", 0, returns(0x281)))
        env.put(methods + 0x2C, env.stub("screen-service-end", "thiscall", 1, returns(0x2C1)))
        return tokens

    yield Case("respawn: active screen service preserves begin/end order", RESPAWN,
               active_screen_service, receiver=lambda t: t["state"])

    def camera_command_list(env):
        tokens = world(env, rs)
        owner = env.get(tokens["y"] + 0xB0)
        inner = env.get(owner)
        node = env.object(0x10, "camera-owner-list-node", fill=0)
        actor = env.object(0x180, "camera-owner-list-actor", fill=0)
        env.put(inner + 0x14, node)
        env.put(node + 8, actor)
        env.put(actor + 8, 0x40000)
        env.put(actor + 0x4C, 42, 43)
        env.put(actor + 0x98, 0xC0DE0098, 0xC0DE009C)
        # Original 0x4d2000 -> 0x4d4d10 clamps actor coordinates to these
        # bounds and publishes them at actor+0x98/+0x9c before virtual +0x24.
        # Wide owner half-extents keep the node in its original list.
        # Sibling 0x4d1fd0 -> 0x4d4b50 only refreshes indexed containers.
        env.put(owner + 0x40, 1000, 1000)
        env.put(owner + 0x58, 0, 0, 100, 100)
        return tokens

    yield Case("respawn: camera update command precedes indexed refresh", RESPAWN,
               camera_command_list, receiver=lambda t: t["state"])
