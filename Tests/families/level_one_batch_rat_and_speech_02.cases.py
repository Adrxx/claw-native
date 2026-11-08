"""Cases for level_one_batch_rat_and_speech_02: Level 1 Rat states, batch 2.

Every observed callback is recorded in a call log held in case memory, so the
comparison judges the order, receiver, arguments and the object state at the
moment of each call. Coverage does not depend on the random seed: the grids
below are deterministic and `random_source` only adds extra variety.
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

SOUND_START = 0x47D150
STEP = 0x47D1B0
TRY_ATTACK = 0x47D2F0
LEFT = 0x47D470
RIGHT = 0x47D490
BOMB = 0x47D660

REALLOC = 0x4A9070
RAND = 0x4A3050

G_DELTA = 0x5430C4
G_MODE = 0x534EAC
G_PLAYER = 0x537E88
G_CLOCK = 0x537210
G_NORAND = 0x541334
G_SOUND_ON = 0x532C0C
G_SOUND_ARG = 0x532C10
G_EMPTY_STRING = 0x52E1CC
TRIE = 0x537668
TABLE = 0x537698

LOG_ROWS = 24
MASK = 0xFFFFFFFF
INT_MIN = 0x80000000


def dbl(value):
    return struct.unpack("<II", struct.pack("<d", value))


def text(env, string, name="string"):
    return env.object(len(string) + 4, name, data=string.encode() + b"\0", fill=0)


def recorder(log, watch, result=0):
    """An effect that appends the call and a snapshot of watched words to the call log."""
    def effect(env, call):
        n = env.get(log)
        env.put(log, n + 1)
        row = log + 4 + (n % LOG_ROWS) * 64
        args = list(call.arguments)[:4]
        args += [0] * (4 - len(args))
        env.put(row, call.function, call.receiver, *args)
        env.put(row + 24, *[env.get(a) for a in watch])
        return result
    return effect


def rat(**o):
    """setup() for one Rat object with everything the owned functions reach."""
    def setup(env):
        g = lambda key, default: o.get(key, default)
        fill = g("fill", 0x5A)
        t = {}
        R = env.object(0x440, "rat", fill=fill)
        E = env.object(0x200, "rat-actor", fill=fill ^ 0x33)
        A = E + 0x188
        S = env.object(0x40, "rat-sound-owner", fill=fill ^ 0x11)
        V = env.object(0x100, "rat-vtable", fill=0)
        log = env.object(4 + 64 * LOG_ROWS, "call-log", fill=0)
        t.update(R=R, E=E, A=A, log=log, V=V, S=S)
        watch = [R + 0x24, R + 0x50, R + 0x54, R + 0x418, R + 0x41C, R + 0x1A0, E + 0x40,
                 A + 0x14, 0x5376B8, TRIE + 0x1C]
        for offset, argc in ((0x44, 0), (0x6C, 1), (0x70, 1), (0xA8, 0), (0xAC, 0), (0xB0, 0)):
            env.put(V + offset, env.stub(f"rat-vcall-{offset:x}", "thiscall", argc,
                                         recorder(log, watch, offset * 3 + 1)))
        env.put(R, V)
        env.put(R + 0x10, S)
        env.put(R + 0x12C, E)
        env.put(R + 0x24, g("id", 0x1234))
        env.put(S + 0x1C, g("old_value", 0x0BADF00D))
        env.put(R + 0x50, *dbl(g("r50", 37.6)))
        env.put(R + 0x68, *dbl(g("r68", 100.0)))
        env.put(R + 0x70, *dbl(g("r70", 250.0)))
        env.put(R + 0x80, *dbl(g("r80", 100.0)))
        env.put(R + 0x98, *dbl(g("r98", 100.0)))
        env.put(R + 0x18C, g("state", 1))
        env.put(R + 0x1A0, g("counter", 0))
        env.put(R + 0x2E4, g("chance", 50))
        env.put(R + 0x2FC, g("bits_count", 2))
        env.put(R + 0x300, g("bits_word", 0x6C))
        env.put(R + 0x400, g("owner", 0))
        env.put(R + 0x404, g("v404", 0))
        env.put(R + 0x408, g("v408", 0))
        env.put(R + 0x40C, g("v40c", 0))
        env.put(R + 0x410, g("v410", 0))
        env.put(R + 0x414, g("v414", 0))
        env.put(R + 0x418, g("r418", 0))
        env.put(R + 0x41C, g("r41c", 0))
        env.put(R + 0x138, g("r138", 11))
        env.put(R + 0x140, g("r140", 23))
        for offset, key, default in ((0x40, "eflags", 0), (0x118, "e118", 5), (0x120, "e120", 7),
                                     (0x128, "e128", INT_MIN), (0x130, "e130", 13),
                                     (0x138, "e138", 17), (0x140, "e140", 19)):
            env.put(E + offset, g(key, default))
        env.put(E + 0x4C, g("ex", 1000))
        env.put(E + 0x50, g("ey", 2000))
        env.put(E + 0x64, g("epri", 9))
        env.put(A + 8, g("a8", 0))
        env.put(A + 0x14, g("a14", 0))
        env.put(A + 0x18, g("a18", 0))
        env.put(A + 0x1C, g("a1c", 0))
        env.put(A + 0x20, g("a20", 0))
        env.put(A + 0x24, g("a24", 0))
        env.put(G_DELTA, g("delta", 0x21))
        env.put(G_MODE, g("mode", 0))
        env.put(G_CLOCK, g("clock", 10000))
        env.put(G_NORAND, g("norand", 0))
        # The player and the tile checker used by the attack test.
        px, py, dx, dy = g("px", 200), g("py", 300), g("dx", 232), g("dy", 310)
        P = env.object(0x60, "target", fill=fill ^ 0x44)
        D = env.object(0x60, "player", fill=fill ^ 0x55)
        env.put(P + 0x4C, px, py)
        env.put(P + 0x38, g("p38", 7))
        env.put(D + 0x4C, dx, dy)
        env.put(G_PLAYER, D)
        env.put(R + 0x194, P)
        Q = env.object(0x20, "tile-owner", fill=fill ^ 0x66)
        Z = env.object(0x30, "tile-context", fill=fill ^ 0x77)
        T = env.object(0x70, "tile-checker", fill=fill ^ 0x88)
        M = env.object(0xA0, "tile-map", fill=fill ^ 0x99)
        cells = 16
        data = env.object(cells * cells * 4, "tile-data", fill=0xFF)
        rows = env.object(cells * 4, "tile-rows", words=[r * cells for r in range(cells)])
        blocking = env.object(0x40, "blocking-tile", fill=0x12)
        passing = env.object(0x40, "passing-tile", fill=0x21)
        bvt = env.object(0x40, "blocking-vtable", fill=0)
        pvt = env.object(0x40, "passing-vtable", fill=0)
        table = env.object(16, "tile-object-table", words=[0, blocking, passing, 0])
        env.put(blocking, bvt)
        env.put(passing, pvt)
        probe = [R + 0x24]
        env.put(bvt + 0x20, env.stub("tile-block", "thiscall", 2, recorder(log, probe, 1)))
        env.put(pvt + 0x20, env.stub("tile-pass", "thiscall", 2, recorder(log, probe, 0)))
        env.put(M + 0x30, 512, 512)
        env.put(M + 0x20, data, rows)
        env.put(M + 0x8C, 5)
        env.put(M + 0x90, 5)
        env.put(T + 0x5C, M)
        env.put(T + 0x4C, table)
        env.put(Z + 0x24, T)
        env.put(Q + 0xC, Z)
        env.put(R + 0x190, Q)
        for x, y, value in g("tiles", ()):
            cx = min(max(x, 0), 511) >> 5
            cy = min(max(y, 0), 511) >> 5
            env.put(data + (cy * cells + cx) * 4, value)
        env.override(RAND, sequence(*g("rands", (5,))))
        if "sound" in o:
            _sound_setup(env, o["sound"], R, g("sound_arg", 0x600DCAFE))
        if "table" in o:
            _table_setup(env, **o["table"])
        if o.get("spawn"):
            t.update(_spawn_setup(env, R, E, log, watch, **o["spawn_options"]))
        return t
    return setup


def _sound_setup(env, kind, R, sound_arg):
    """The LS_HOME lookup structure at 0x537668 and the optional owner chain."""
    env.put(G_SOUND_ON, kind.get("on", 1))
    env.put(G_SOUND_ARG, sound_arg)
    env.put(TRIE + 0x1C, 0x11111111)
    env.put(TRIE + 0x20, 0x22222222)
    env.put(TRIE + 0x28, 0x33333333)
    env.put(TRIE + 0x04, 0x44444444)
    nodes = kind.get("nodes")
    env.put(TRIE + 0x18, nodes(env) if nodes else 0)
    if kind.get("owner"):
        C = env.object(0x90, "owner-service", fill=0x31)
        env.put(C + 0x78, 0)
        B = env.object(0x20, "owner-link", fill=0x32)
        env.put(B + 0x10, C)
        A = env.object(0x20, "owner", fill=0x33)
        env.put(A + 0x10, B)
        env.put(R + 0x400, A)


def trie_node(env, left, right, bit, key, value):
    k = text(env, key, "trie-key") if isinstance(key, str) else key
    return env.object(0x14, "trie-node", words=[left, right, bit, k, value])


def _table_setup(env, lo, hi, size, strings, fail=False, default="LS_MOVINGRIGHT",
                 cleared=None, grown_string=None):
    """The growable element table at 0x537698 used by the step function."""
    count = hi - lo + 1
    data = env.object(count * size, "table-data", fill=0x6B)
    for index in range(count):
        env.put(data + index * size, text(env, strings[index], f"element-string-{index}"))
    errors = env.object(0x20, "table-errors", fill=0x4E)
    env.put(errors + 0xC, 4)
    default_element = env.object(8, "table-default-element", words=[text(env, default, "default-string"), 0])
    env.put(TABLE + 0x4, errors)
    env.put(TABLE + 0x8, lo, hi, data, default_element, size)
    env.put(TABLE + 0x1C, 0x0A0B0C0D, 0x0E0F1011)
    env.put(0x544B4C, 0x00512345)
    env.put(G_EMPTY_STRING, text(env, grown_string if grown_string is not None else "", "grown-string"))
    if fail:
        env.override(REALLOC, returns(0))


def _spawn_setup(env, R, E, log, watch, found=True, callback=True, priorities=(), flags=(),
                 count_nodes=64):
    """The scene, its name map and the RatBomb actor metadata used by the spawn."""
    t = {}
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    env.put(scene + 12, context)
    pool = env.object(count_nodes * 12, "list-node-pool", fill=0)
    for i in range(count_nodes - 1):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, count_nodes)
    nodes = []
    for i, priority in enumerate(priorities):
        actor = env.object(0x1B4, f"queued-actor-{i}", fill=0x63 + i)
        node = env.object(12, f"queued-node-{i}", fill=0)
        env.put(actor + 0x64, priority, node, 0)
        env.put(actor + 8, flags[i] if flags else 0)
        nodes.append((node, actor))
    for i, (node, actor) in enumerate(nodes):
        env.put(node, nodes[i + 1][0] if i + 1 < len(nodes) else 0,
                nodes[i - 1][0] if i else 0, actor)
    env.put(scene + 0x14, nodes[0][0] if nodes else 0, nodes[-1][0] if nodes else 0, len(nodes))
    carrier = env.object(0x20, "scene-carrier", fill=0x77)
    middle = env.object(0x20, "scene-middle", fill=0x78)
    env.put(carrier + 0xC, middle)
    env.put(middle + 8, scene)
    env.put(R + 0x130, carrier)
    # The spawned object's logic block, filled in by the creation callback.
    W = env.object(0x140, "spawned-logic", fill=0x3C)
    X = env.object(0x180, "spawned-physics", fill=0x4D)
    WV = env.object(0x40, "spawned-logic-vtable", fill=0)
    env.put(W, WV)
    env.put(W + 0x12C, X)
    env.put(X + 0x164, 0x00010001)
    wwatch = [W + 0x40, W + 0x44, W + 0x50, W + 0x54, W + 0x58, W + 0x5C, X + 0x164, R + 0x1A0]
    env.put(WV + 0x28, env.stub("spawned-logic-start", "thiscall", 0, recorder(log, wwatch, 5)))
    metadata = env.object(0x18, "actor-metadata", fill=0)
    observed = env.object(4 + 32 * 4, "created-actor-observations", fill=0)
    record = recorder(log, watch + wwatch[:4], 0x77)

    def created(env, call):
        actor = call.arguments[0]
        service = env.get(actor + 0x6C)
        env.put(service + 0x18, W)
        n = env.get(observed)
        env.put(observed, n + 1)
        env.put(observed + 4 + 32 * (n % 4), actor, service, env.get(actor + 8), env.get(actor + 0x64),
                env.get(actor + 0x4C), env.get(actor + 0x68), env.get(service + 0x10), env.get(scene + 0x14))
        return record(env, call)

    env.put(metadata + 8, 0x2)
    env.put(metadata + 0x10, env.stub("metadata-notify", "cdecl", 1, created) if callback else 0)
    manager = env.object(0x30, "metadata-manager", fill=0)
    buckets = env.object(4, "map-buckets", fill=0)
    env.put(context + 0x14, manager)
    env.put(manager + 0x14, buckets, 1)
    if found:
        key = text(env, "RatBomb", "map-key")
        node = env.object(16, "map-node", fill=0)
        env.put(node, 0, 0, key, metadata)
        env.put(buckets, node)
    t.update(scene=scene, W=W, X=X, metadata=metadata)
    return t


def case(label, function, **options):
    return Case(label, function, rat(**options), receiver=lambda t: t["R"])


# ---------------------------------------------------------------------------
# Value tables shared by the grids.

def attack_base(**more):
    base = dict(px=200, py=300, dx=232, dy=310, r70=310.0, r68=232.0, clock=10000, r418=0, r41c=0)
    base.update(more)
    return base


def cases(random_source):
    # ----- 0x47d150: restart in LS_HOME ------------------------------------
    home = "LS_HOME"
    sound_off = dict(on=0)

    def leaf(env, key=home, value=0x12345678, bit=2):
        return trie_node(env, 0, 0, bit, key, value)

    def head(left, right, bit):
        return lambda env: trie_node(env, left(env) if left else 0, right(env) if right else 0, bit, "head", 0)

    def one_level(bit, side, key=home, value=0x12345678, leaf_bit=2):
        def build(env):
            child = leaf(env, key, value, leaf_bit)
            return trie_node(env, child if side == 0 else 0, child if side == 1 else 0, bit, "head", 0)
        return build

    def two_level(bit1, bit2, key=home, value=0x7ACE5EED, null_end=False, deep_bit=None):
        # LS_HOME bit 3 is set (right); bit 20 is set (right); bit 22 is clear (left).
        def build(env):
            c = leaf(env, key, value, bit2 - 1)
            inner_bit = deep_bit if deep_bit is not None else bit2
            inner = trie_node(env, c if inner_bit == 22 else 0, 0 if inner_bit == 22 else (0 if null_end else c),
                              inner_bit, "inner", 0)
            return trie_node(env, 0, inner, bit1, "head", 0)
        return build

    tries = [
        ("empty", None),
        ("head bit beyond string", lambda env: trie_node(env, 0, 0, 64, "far", 0x1111)),
        ("head bit at string end", lambda env: trie_node(env, 0, 0, 63, home, 0x2222)),
        ("right leaf match", one_level(3, 1)),
        ("left leaf match", one_level(0, 0)),
        ("right leaf null", lambda env: trie_node(env, 0, 0, 3, "head", 0)),
        ("leaf differs first byte", one_level(3, 1, "ZS_HOME")),
        ("leaf differs second byte", one_level(3, 1, "LZ_HOME")),
        ("leaf differs third byte", one_level(3, 1, "LS-HOME")),
        ("leaf differs last byte", one_level(3, 1, "LS_HOMF")),
        ("leaf longer", one_level(3, 1, "LS_HOMEX")),
        ("leaf shorter", one_level(3, 1, "LS_HOM")),
        ("leaf equal bit above head", one_level(3, 1, home, 0x3141, 3)),
        ("two level match", two_level(3, 20)),
        ("two level left match", two_level(3, 22)),
        ("two level mismatch", two_level(3, 20, "LS_HOMX")),
        ("two level null", two_level(3, 20, null_end=True)),
        ("two level inner beyond string", two_level(3, 20, deep_bit=70)),
    ]
    for label, nodes in tries:
        yield case(f"start {label}", SOUND_START, sound=dict(on=1, nodes=nodes, owner=True),
                   old_value=0x10000 + 7 * len(label))
    for owner in (False, True):
        for on in (0, 1, 0x100):
            yield case(f"start sound={on:#x} owner={owner}", SOUND_START,
                       sound=dict(on=on, nodes=tries[3][1], owner=owner), old_value=0x7000 + on)

    # ----- 0x47d2f0: the attack test ---------------------------------------
    yield case("attack gate mode 0x26b7", TRY_ATTACK, **attack_base(mode=0x26B7))
    for mode in (0x26B6, 0x26B8, 0, MASK):
        yield case(f"attack mode {mode:#x}", TRY_ATTACK, **attack_base(mode=mode, dy=300, r70=300.0))
    for delta in (-51, -50, -49, -1, 0, 1, 49, 50, 51):
        for p38 in ((7, MASK, 0) if delta in (0, 49, -49) else (7,)):
            yield case(f"attack y window {delta} p38={p38:#x}", TRY_ATTACK,
                       **attack_base(dy=300 + delta, r70=float(300 + delta), p38=p38))
    # Tile blocking: starts, middle, final, direction and equal columns.
    tile_sets = {
        "none": (),
        "start blocks": ((200, 300, 1),),
        "start passes": ((200, 300, 2),),
        "end blocks": ((232, 300, 1),),
        "end passes": ((232, 300, 2),),
        "high bits block": ((232, 300, 0x10001),),
        "high bits pass": ((200, 300, 0xABCD0002),),
        "unset marker": ((200, 300, 0xEEEEEEEE), (232, 300, 0xEEEEEEEE)),
        "other row blocks": ((200, 332, 1), (232, 332, 1), (200, 268, 1), (232, 268, 1)),
        "other column blocks": ((168, 300, 1), (264, 300, 1)),
    }
    for label, tiles in tile_sets.items():
        for px, dx in ((200, 232), (232, 200), (200, 200), (-40, 40), (600, 40)):
            if px not in (200, 232) and label not in ("none", "start blocks", "end blocks"):
                continue
            moved = tuple((x - 200 + px if x == 200 else x - 232 + dx, y, v) for x, y, v in tiles) \
                if (px, dx) not in ((200, 232),) else tiles
            yield case(f"attack tiles {label} {px}->{dx}", TRY_ATTACK,
                       **attack_base(px=px, dx=dx, tiles=moved))
    for step in (64, 96, 128):
        yield case(f"attack middle tile {step}", TRY_ATTACK,
                   **attack_base(px=200, dx=200 + step * 2, tiles=((200 + step, 300, 1),)))
        yield case(f"attack middle passing tile {step}", TRY_ATTACK,
                   **attack_base(px=200 + step * 2, dx=200, tiles=((200 + step, 300, 2),)))
    # Flip direction.
    for state in (1, 2, 0, 3):
        for eflags in (0, 2, 0xFF, 0xFD):
            for sentinel in (False, True):
                e = dict(e118=INT_MIN if sentinel else 0x1234, e128=0x2345, e138=INT_MIN if sentinel else 0x3456,
                         e120=0x4567, e130=0x5678, e140=0x6789)
                yield case(f"attack flip state {state} flags {eflags:#x} sentinel {sentinel}", TRY_ATTACK,
                           **attack_base(state=state, eflags=eflags, **e))
    # First branch: close in y by rounded float, with the cooldown.
    for r70 in (310.0, 309.5, 310.4, 359.49, 359.5, 359.6, 360.0, 260.5, 260.51, 260.4, 260.0, 259.6,
                -1e12, 1e12, 2147483647.0, -2147483648.0, 3e9, float("nan")):
        for state in (1, 2):
            yield case(f"attack first branch r70={r70!r} state {state}", TRY_ATTACK,
                       **attack_base(r70=r70, state=state, r68=232.0))
    for clock, r418, r41c in ((10000, 9000, 1000), (10000, 9000, 1001), (10000, 9000, 999), (5, 10, 3),
                              (5, 10, 0xFFFFFFF0), (5, 10, MASK), (0, 0, 0), (0, 0, 1), (MASK, 0, MASK),
                              (MASK, 1, MASK), (3000, 1, 2000)):
        yield case(f"attack cooldown {clock}/{r418}/{r41c}", TRY_ATTACK,
                   **attack_base(clock=clock, r418=r418, r41c=r41c, dy=310))
    # Second branch: close in x, target above the player, chance roll.
    rolls = (0, 37, 99, 100, 12345, 0x7FFF, MASK, (-250) & MASK, (-99) & MASK, (-100) & MASK)
    for roll in rolls:
        signed = roll - (1 << 32) if roll & INT_MIN else roll
        remainder = abs(signed) % 100 * (-1 if signed < 0 else 1)
        for chance in (remainder, remainder + 1, remainder - 1):
            yield case(f"attack roll {signed} chance {chance}", TRY_ATTACK,
                       **attack_base(r70=200.0, r68=232.0, chance=chance & MASK, rands=(roll, 7)))
    for dxdiff in (-41, -40, -39, 0, 39, 40, 41):
        yield case(f"attack second branch dx {dxdiff}", TRY_ATTACK,
                   **attack_base(r70=200.0, r68=232.0 + dxdiff, chance=100, rands=(3,)))
    for r70 in (309.0, 309.9999, 310.0, 310.0001, 311.0, -5.0, float("nan"), 1e30):
        yield case(f"attack second branch above r70={r70!r}", TRY_ATTACK,
                   **attack_base(r70=r70, r68=232.0, chance=100, rands=(3,)))
    for norand in (0, 1, 0x100, MASK):
        yield case(f"attack norand {norand:#x}", TRY_ATTACK,
                   **attack_base(r70=200.0, norand=norand, chance=100, rands=(3,)))
    for r68 in (232.4, 232.6, -232.5, 271.5, 191.5, 192.5, 1e12, float("nan")):
        yield case(f"attack second branch r68={r68!r}", TRY_ATTACK,
                   **attack_base(r70=200.0, r68=r68, chance=100, rands=(3,)))
    # A cooldown that fails falls through to the second branch.
    yield case("attack cooldown fails then chance", TRY_ATTACK,
               **attack_base(r70=310.0, r41c=MASK, r418=1, chance=100, rands=(3,)))
    yield case("attack cooldown fails then no chance", TRY_ATTACK,
               **attack_base(r70=310.0, r41c=MASK, r418=1, chance=0, rands=(3,)))
    for _ in range(16):
        dy = random_source.randrange(250, 350)
        dx = random_source.randrange(60, 460)
        px = random_source.randrange(60, 460)
        yield case(f"attack random {dx}/{px}/{dy}", TRY_ATTACK, **attack_base(
            px=px, dx=dx, dy=dy, py=random_source.randrange(250, 350),
            state=random_source.choice((1, 2)), eflags=random_source.choice((0, 2)),
            r70=random_source.uniform(dy - 80, dy + 80), r68=random_source.uniform(dx - 60, dx + 60),
            chance=random_source.randrange(0, 100), rands=(random_source.getrandbits(32),),
            clock=random_source.getrandbits(32), r418=random_source.getrandbits(32),
            r41c=random_source.choice((0, random_source.getrandbits(8), random_source.getrandbits(32))),
            tiles=((random_source.randrange(0, 500), random_source.randrange(0, 500), random_source.choice((1, 2))),),
            fill=random_source.randrange(1, 250)))

    # ----- 0x47d470 and 0x47d490: attack test, else movement ---------------
    for function, equal_key, name in ((LEFT, "r80", "left"), (RIGHT, "r98", "right")):
        yield case(f"{name} attack happens", function, **attack_base())
        for mode in (0x26B7,):
            for equal in (True, False):
                kwargs = dict(mode=mode, r68=100.0, r50=37.6 if equal else -12.25)
                kwargs[equal_key] = 100.0 if equal else 100.000001
                yield case(f"{name} gate {equal}", function, **kwargs)
        for r50 in (37.6, -37.6, 0.0, 0.5, 1.5, 2.5, -0.5, 1e12, float("nan")):
            kwargs = dict(mode=0x26B7, r68=64.0, r50=r50)
            kwargs[equal_key] = 64.0
            yield case(f"{name} movement r50={r50!r}", function, **kwargs)
        for r68, other in ((0.0, -0.0), (-0.0, 0.0), (float("nan"), float("nan")), (1e300, 1e300),
                           (5e-324, 0.0)):
            kwargs = dict(mode=0x26B7, r68=r68, r50=12.5)
            kwargs[equal_key] = other
            yield case(f"{name} movement compare {r68!r}/{other!r}", function, **kwargs)
        yield case(f"{name} blocked then attack", function,
                   **attack_base(tiles=((200, 300, 1),)))
        yield case(f"{name} y out of window", function, **attack_base(dy=400, mode=0))
        yield case(f"{name} anim running", function, **attack_base(dy=400), a8=1, a14=3, a24=7)
        for _ in range(6):
            kwargs = dict(mode=0x26B7, r68=random_source.uniform(-1e4, 1e4),
                          r50=random_source.uniform(-1e4, 1e4), fill=random_source.randrange(1, 250))
            kwargs[equal_key] = kwargs["r68"] if random_source.random() < 0.5 else random_source.uniform(-1e4, 1e4)
            yield case(f"{name} random movement", function, **kwargs)

    # ----- 0x47d1b0: step, bit test then animation table -------------------
    table = lambda **kw: dict(lo=10, hi=14, size=4, strings=["a0", "LS_MOVINGRIGHT", "a2", "LS_MOVINGLEFT", "ab"], **kw)
    for count, word, expected in ((0, 0xFFFFFFFF, "below"), (1, MASK, "below"), (2, MASK, "below"),
                                  (3, 0x4, "inline"), (3, 0xFFFFFFFB, "inline"), (0x20, 0x4, "inline"),
                                  (0x20, 0xFFFFFFFB, "inline"), (0x20, 0x5, "inline"), (0x20, 0x2, "inline"),
                                  (0x20, 0x8, "inline"), (0x20, 0x6D, "inline"),
                                  (0x21, 0x4, "pointer"), (0x21, 0xFFFFFFFB, "pointer"),
                                  (0x80, 0x1, "pointer"), (MASK, 0x44, "pointer")):
        for mode, strings_id in ((0x26B7, 11), (0, 13)):
            yield _step_case(f"step bits count {count:#x} word {word:#x} mode {mode:#x} id {strings_id}",
                             count, word, expected, mode, strings_id, table)
    yield from _step_table_cases(random_source, table)

    # ----- 0x47d660: drop a RatBomb -----------------------------------------
    yield from _bomb_cases(random_source)


def _step_case(label, count, word, expected, mode, element_id, table):
    def setup(env):
        t = rat(bits_count=count, bits_word=word, mode=mode, id=element_id, a8=0,
                dy=300, px=200, dx=232, py=300, r70=300.0, table=table())(env)
        if expected == "pointer":
            if count > 0x20:
                holder = env.object(8, "bit-word-holder", words=[word, 0x55])
                env.put(t["R"] + 0x300, holder)
        return t
    return Case(label, STEP, setup, receiver=lambda t: t["R"])


def _step_table_cases(random_source, table):
    ones = dict(bits_count=1)
    strings = ["a0", "LS_MOVINGRIGHT", "a2", "LS_MOVINGLEFT", "LS_MOVINGRIGHT"]
    # In-range lookups.
    for lo, hi, size in ((10, 14, 4), (10, 14, 8), (10, 14, 12), (0, 4, 16), (-3, 1, 4)):
        for index in range(5):
            for pad in (("", "x") if index in (0, 4) else ("",)):
                element = lo + index
                names = [s + pad if pad and i != index else s for i, s in enumerate(strings)]
                yield Case(f"step in range {lo}..{hi} size {size} id {element} {pad!r}", STEP,
                           rat(id=element & MASK, table=dict(lo=lo, hi=hi, size=size, strings=names),
                               a8=0, **ones), receiver=lambda t: t["R"])
    # Names that are close to LS_MOVINGRIGHT.
    for name in ("LS_MOVINGRIGHT", "LS_MOVINGRIGHT ", "LS_MOVINGRIGH", "LS_MOVINGLEFT", "", "ls_movingright",
                 "LS_MOVINGRIGHU", "MS_MOVINGRIGHT", "LS_MOVINGRIGHT\x7f"):
        yield Case(f"step name {name!r}", STEP,
                   rat(id=12, table=dict(lo=10, hi=14, size=4, strings=["q", "r", name, "s", "t"]),
                       **ones), receiver=lambda t: t["R"])
    # Growing the table upward and downward.
    for hi_extra, size in ((1, 4), (1, 8), (1, 12), (2, 4), (3, 4), (5, 4)):
        for text_value in ("", "LS_MOVINGRIGHT"):
            yield Case(f"step grow up by {hi_extra} size {size} init {text_value!r}", STEP,
                       rat(id=14 + hi_extra, table=dict(lo=10, hi=14, size=size, strings=strings,
                                                       grown_string=text_value), **ones),
                       receiver=lambda t: t["R"])
    for lo_extra, size in ((1, 4), (1, 8), (1, 12), (2, 4), (3, 4), (5, 4)):
        for text_value in ("", "LS_MOVINGRIGHT"):
            yield Case(f"step grow down by {lo_extra} size {size} init {text_value!r}", STEP,
                       rat(id=10 - lo_extra, table=dict(lo=10, hi=14, size=size, strings=strings,
                                                       grown_string=text_value), **ones),
                       receiver=lambda t: t["R"])
    for _ in range(12):
        lo = random_source.randrange(-20, 20)
        span = random_source.randrange(1, 8)
        size = random_source.choice((4, 8, 12, 16))
        element = lo + random_source.randrange(-3, span + 3)
        names = [random_source.choice(("LS_MOVINGRIGHT", "LS_MOVINGLEFT", "LS_WALK", "")) for _ in range(span)]
        grow = element < lo or element > lo + span - 1
        if grow and size != 4 and abs(element - lo) > 1 and not (lo <= element <= lo + span - 1):
            size = 4
        yield Case(f"step random {lo}+{span} size {size} id {element}", STEP,
                   rat(id=element & MASK, table=dict(lo=lo, hi=lo + span - 1, size=size, strings=names,
                                                    grown_string=random_source.choice(("", "LS_MOVINGRIGHT"))),
                       fill=random_source.randrange(1, 250), **ones),
                   receiver=lambda t: t["R"])


def _bomb_cases(random_source):
    ints = (dict(v404=0, v408=-1234567 & MASK, v40c=77, v410=-5 & MASK, v414=9),
            dict(v404=3, v408=0x7FFFFFFF, v40c=0x80000000, v410=13, v414=-17 & MASK),
            dict(v404=MASK, v408=-2 & MASK, v40c=-3 & MASK, v410=1, v414=2),
            dict(v404=0x40000000, v408=1, v40c=0, v410=-1000 & MASK, v414=1000))
    anim_spawn = dict(a8=1, a14=1, a18=0, a20=5, a24=1)
    spawn = dict(spawn=True)

    def bomb(label, ints_index=0, spawn_options=None, **options):
        merged = dict(ints[ints_index])
        merged.update(options)
        merged["spawn"] = True
        merged["spawn_options"] = spawn_options or {}
        return Case(label, BOMB, rat(**merged), receiver=lambda t: t["R"])

    for index in range(len(ints)):
        for ey, epri in ((2000, 9), (-7 & MASK, 0), (5, 1), (0x7FFFFFF0, 0x7FFFFFFF)):
            yield bomb(f"bomb spawn ints {index} ey {ey:#x} pri {epri:#x}", index, ey=ey, epri=epri,
                       **anim_spawn)
    # The animation return value and counter decide whether a bomb is dropped.
    for counter in (0, 1, 2, MASK):
        yield bomb(f"bomb counter {counter:#x}", 0, counter=counter, **anim_spawn)
        yield bomb(f"bomb counter {counter:#x} flagged", 1, counter=counter, **anim_spawn)
    for returned in (0, 2, 3, MASK, 0x10001):
        yield bomb(f"bomb anim returns {returned:#x}", 1, **dict(anim_spawn, a24=returned))
    yield bomb("bomb anim missing", 1, a8=0, a14=1, a24=1)
    yield bomb("bomb anim ticking", 1, a8=1, a14=3, a18=0, a24=1)
    yield bomb("bomb anim ticking delta", 0, a8=1, a14=100, a18=1, a24=1, delta=0x21)
    yield bomb("bomb anim ticking delta expires", 0, a8=1, a14=20, a18=1, a24=1, a20=1, a1c=1, delta=0x21)
    yield bomb("bomb anim idle with a result", 1, a8=1, a14=0, a18=0, a1c=1, a20=1)
    yield bomb("bomb anim idle with other result", 1, a8=1, a14=0, a18=0, a1c=1, a20=2)
    # The finishing test on the animation block: a14 reaches zero while a1c is set.
    for a1c in (0, 1, 0x80000000):
        for a8, a14, a20, a24 in ((0, 0, 0, 0), (0, 5, 0, 0), (1, 1, 1, 1), (1, 2, 1, 1), (1, 0, 1, 1), (1, 0, 2, 1)):
            if a8 and not a14 and not a1c:
                continue
            yield bomb(f"bomb finish a1c {a1c:#x} a8 {a8} a14 {a14} a20 {a20}", 0, a8=a8, a14=a14, a18=0,
                       a1c=a1c, a20=a20, a24=a24)
    # Insertion into the scene list among queued actors.
    for priorities, flags in (((), ()), ((3, 5), (0, 0)), ((20, 30), (0, 0)), ((1, 2, 3), (0, 0, 0)),
                              ((3, 20), (0, 0x20000)), ((5, 5, 5), (0, 0x20000, 0)),
                              ((-9, -7), (0, 0)), ((0x7FFFFFFF, 0x7FFFFFFF), (0, 0)),
                              ((8, 8), (0x20000, 0x20000))):
        for epri in (1, 9, 6, 0, 0x80000000):
            yield bomb(f"bomb queue {priorities} flags {flags} epri {epri:#x}", 1,
                       spawn_options=dict(priorities=priorities, flags=flags), epri=epri,
                       **anim_spawn)
    for _ in range(10):
        yield bomb("bomb random", random_source.randrange(len(ints)),
                   spawn_options=dict(priorities=tuple(sorted(random_source.randrange(-50, 50) for _ in range(random_source.randrange(0, 4))))),
                   ex=random_source.getrandbits(32), ey=random_source.getrandbits(32),
                   epri=random_source.getrandbits(32), counter=random_source.choice((0, 1, random_source.getrandbits(32))),
                   v404=random_source.choice((0, random_source.getrandbits(32))),
                   v408=random_source.getrandbits(32), v40c=random_source.getrandbits(32),
                   v410=random_source.getrandbits(32), v414=random_source.getrandbits(32),
                   fill=random_source.randrange(1, 250), a8=1, a14=random_source.choice((1, 2)), a18=0,
                   a1c=random_source.choice((0, 1)), a20=random_source.choice((1, 2)),
                   a24=random_source.choice((1, 1, 2)))
