"""Cases for level_one_batch_powerups_03: Level 1 claw pickup hit handler (0x41ee60)."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

FN = 0x41EE60

G_APP = 0x5371FC
G_MAP_ON, G_MAP_ARG = 0x532C0C, 0x532C10
G_DISPLAY = 0x534874
G_DISPLAY_OWNER = 0x5349DC
G_POW_KIND, G_POW_TIME = 0x534EAC, 0x534EA8
G_TAG_A, G_TAG_B, G_TAG_C = 0x534EC0, 0x534EC4, 0x537210
G_FLAGS_OBJ = 0x537204
G_BUSY = 0x53C9C0
G_ZERO_26AF = tuple(0x534E60 + 4 * i for i in range(6))
G_ZERO_26AE = (0x534DE8, 0x534DEC, 0x534DD0)
G_FIXED_26AE = 0x534DD4
G_PM_A, G_PM_B = 0x529FA0, 0x529FA4
G_SOUND_TABLE = 0x53C9A4

SET_BIT = 0x10000
MASK32 = 0xFFFFFFFF


def u32(value):
    return value & MASK32


def scene(rnd, kind, *, hit=None, p2=None, p3=None, claw=None, a=None, b=None, c=None, g=None,
          xkeys=(), ykeys=(), manager=False, r10=4, r58=1, bcc=1, tag=0, display=None,
          null_hit=False, lift=None, delay=0, clock=None):
    """setup() for one call of the handler.

    hit, p2, p3, claw, a, c are {offset: value} overrides of the random contents of those
    objects. xkeys / ykeys name the entries present in the two string tables. A callable value
    is called with the dictionary of objects created so far.
    """
    seeds = {name: bytes(rnd.getrandbits(8) for _ in range(size)) for name, size in (
        ("hit", 0x170), ("a", 0x180), ("b", 0x150), ("c", 0x60), ("claw", 0x1C0), ("p2", 0x40),
        ("p3", 0x340), ("display", 0x4D0))}
    p3_words = [(rnd.getrandbits(31) | 1) for _ in range(8)]
    claw_words = [(rnd.getrandbits(30) | 1) for _ in range(8)]
    hit_words = [(rnd.getrandbits(30) | 1) for _ in range(8)]
    rand_globals = {key: rnd.getrandbits(30) | 1 for key in (
        G_MAP_ARG, G_POW_TIME, G_TAG_A, G_TAG_B, G_TAG_C, G_DISPLAY_OWNER, *G_ZERO_26AF, *G_ZERO_26AE,
        G_FIXED_26AE, G_PM_A, G_PM_B)}
    hwnd = rnd.getrandbits(30) | 1
    log_default = rnd.getrandbits(30) | 1

    def string(env, text):
        return env.object(len(text) + 1, "string", data=text.encode() + b"\0")

    def table(env, owner, entries):
        """A bucket table at owner + 0x10 (one bucket, chain of nodes) holding name -> value."""
        node = 0
        for name, value in reversed(list(entries.items())):
            node = env.object(16, "node", words=[node, 0, string(env, name), value])
        buckets = env.object(4, "buckets", words=[node])
        env.put(owner + 0x14, buckets, 1)

    def animation(env, marker):
        frame = env.object(0x40, "frame", fill=0)
        env.put(frame + 0x1C, marker)
        array = env.object(8, "frames", words=[frame, 0])
        return env.object(0x40, "animation", words=[0, 0, 0, array, 1])

    def apply(env, t, base, fields):
        for offset, value in (fields or {}).items():
            env.put(base + offset, value(t) if callable(value) else value)

    def setup(env):
        t = {}
        t["hit"] = env.object(0x170, "hit", data=seeds["hit"])
        t["a"] = env.object(0x180, "hit-owner", data=seeds["a"])
        t["b"] = env.object(0x150, "hit-body", data=seeds["b"])
        t["c"] = env.object(0x60, "hit-bounds", data=seeds["c"])
        t["claw"] = env.object(0x1C0, "claw", data=seeds["claw"])
        t["p2"] = env.object(0x40, "actor-info", data=seeds["p2"])
        t["p3"] = env.object(0x340, "player", data=seeds["p3"])
        t["world"] = env.object(0x40, "world", fill=0)
        t["x"] = env.object(0x30, "table-owner-x", fill=0)
        t["y"] = env.object(0x30, "table-owner-y", fill=0)
        t["app"] = env.object(0x60, "app", fill=0)
        t["win"] = env.object(8, "window", words=[0, hwnd])
        t["flags"] = env.object(0x10, "flags", fill=0xFF)
        t["log"] = env.object(0x40, "log", fill=0)
        t["display"] = env.object(0x4D0, "display", data=seeds["display"])
        # the map piece and the stand-in objects its timing calls read
        reader = env.object(0x90, "reader", fill=0)
        piece_owner = env.object(0x40, "piece-owner", fill=0)
        env.put(piece_owner + 0x10, reader)
        env.put(piece_owner + 0x28, delay)
        if clock is not None:
            env.override(0x546DF0, sequence(*clock))
        piece = env.object(0x40, "piece", fill=0)
        env.put(piece + 0x10, piece_owner)
        t["piece"] = piece
        # tag object for 0x41d6f0
        tag_object = env.object(0x20, "tag", fill=0)
        tag_owner = env.object(0x90, "tag-owner", fill=0)
        env.put(tag_object + 0x10, tag_owner)
        env.put(tag_owner + 0x10, reader)

        tables_x = {"GAME_MAPPIECE": piece, "GAME_OTHER": 0x1111} if "GAME_MAPPIECE" in xkeys else {"GAME_OTHER": 0x1111}
        table(env, t["x"], tables_x)
        t["fall"] = animation(env, 0x1000 | (hit_words[0] & 0xFF))
        t["swing"] = animation(env, 0x2000 | (hit_words[1] & 0xFF))
        tables_y = {"CLAW_OTHER": 0x2222}
        if "CLAW_FALL" in ykeys:
            tables_y["CLAW_FALL"] = t["fall"]
        if "CLAW_SWING" in ykeys:
            tables_y["CLAW_SWING"] = t["swing"]
        table(env, t["y"], tables_y)

        env.put(t["world"] + 0x28, t["x"], t["y"])
        env.put(t["app"] + 4, t["win"])
        if manager:
            manager_object = env.object(0xBD0, "manager", fill=0)
            vtable = env.object(0x80, "manager-vtable", fill=0)

            def record(result):
                def effect(env, call):
                    slot = env.calls_so_far(call.function) - 1
                    env.put(t["log"] + 16 * slot, call.receiver, *call.arguments)
                    return result
                return effect

            env.put(vtable + 0x10, env.stub("manager-0x10", "thiscall", 0, record(r10)))
            env.put(vtable + 0x58, env.stub("manager-0x58", "thiscall", 1, record(r58)))
            env.put(manager_object, vtable)
            env.put(manager_object + 0xBCC, bcc)
            t["manager"] = manager_object
            env.put(t["app"] + 0x2C, manager_object)

        # hit
        env.put(t["hit"] + 0xFC, kind)
        env.put(t["hit"] + 0x6C, t["a"])
        env.put(t["hit"] + 8, hit_words[2] & ~SET_BIT)
        env.put(t["hit"] + 0x104, 0)
        env.put(t["hit"] + 0x108, 0)
        env.put(t["hit"] + 0x148, hit_words[3] & 0xFFFF, hit_words[4] & 0xFFFF)
        env.put(t["a"] + 0x18, t["b"])
        t["tag"] = tag_object if tag else 0
        env.put(t["a"] + 0x168, t["tag"])
        env.put(t["b"] + 0xC, t["c"])
        env.put(t["b"] + 0x140, hit_words[5] & 0xFF, hit_words[6] & 0xFF)
        env.put(t["c"] + 0x4C, hit_words[5] & 0xFFF, hit_words[6] & 0xFFF)
        # claw
        env.put(t["claw"] + 0xC, t["world"])
        env.put(t["claw"] + 8, claw_words[0] & ~0x90)
        env.put(t["claw"] + 0xCC, claw_words[1] & 0xFF)
        env.put(t["claw"] + 0xF8, claw_words[2] & 0xFFFF)
        # player
        if lift is None:
            env.put(t["p3"] + 0x12C, 0)
        env.put(t["p3"] + 4, 0)
        env.put(t["p3"] + 0x3C, p3_words[0] & 0xFF | 0x40)
        if lift is not None:
            v20, v2fc, indirect = lift
            body = env.object(0x310, "released-body", fill=0)
            env.put(body + 0x20, v20)
            env.put(body + 0x2FC, v2fc)
            env.put(body + 0x300, env.object(0x20, "bit-words", words=[0x10, 0x20]) if indirect else 0x30)
            owner = env.object(0x40, "released-owner", fill=0)
            env.put(owner + 0x18, body)
            released = env.object(0x80, "released", data=bytes(rnd.getrandbits(8) for _ in range(0x80)))
            env.put(released + 0x6C, owner)
            t["released"], t["body"] = released, body
            env.put(t["p3"] + 0x12C, released)
        # globals
        for address, value in rand_globals.items():
            env.put(address, value)
        env.put(G_APP, t["app"])
        env.put(G_MAP_ON, 0)
        env.put(G_BUSY, 0)
        env.put(G_SOUND_TABLE, 0)
        env.put(t["claw"] + 0x170, 0)
        t["extra"] = env.object(0x20, "extra", words=[0, 0, hit_words[7] & ~SET_BIT])
        env.put(G_FLAGS_OBJ, t["flags"])
        env.put(G_DISPLAY, 0)
        env.put(t["app"] + 0x14, 0)
        if display is not None:
            env.put(G_DISPLAY, t["display"])
            env.put(t["display"] + 0xC, rand_globals[G_DISPLAY_OWNER] if display else 1)
            env.put(t["display"] + 0x4C8, 0x7E57)
        apply(env, t, t["hit"], hit)
        apply(env, t, t["a"], a)
        apply(env, t, t["b"], b)
        apply(env, t, t["c"], c)
        apply(env, t, t["claw"], claw)
        apply(env, t, t["p2"], p2)
        apply(env, t, t["p3"], p3)
        for address, value in (g or {}).items():
            env.put(address, value(t) if callable(value) else value)
        if null_hit:
            t["hit"] = 0
        return t

    return setup


def call(label, rnd, kind, **options):
    setup = scene(rnd, kind, **options)
    return Case(label, FN, setup,
                arguments=(lambda t: t["claw"], lambda t: t["p2"], lambda t: t["p3"], lambda t: t["hit"]))


def cases(random_source):
    rnd = random_source
    # no hit, unknown kinds
    yield call("null hit", rnd, 0x26B0, null_hit=True)
    yield call("null hit with manager", rnd, 0x26B1, null_hit=True, manager=True)
    for kind in (0, 1, 0x26AC, 0x26BB, 0x26BC, 0x26BF, 0x26C0, 0x7FFF0000, 0xFFFFFFFF, 0xFFFFD953):
        yield call(f"kind {kind:#x} does nothing", rnd, kind)
    yield call("kind below range does not wrap into table", rnd, 0x26AC, manager=True)

    # 0x26ae: the claw falls or is dropped. PostMessageA has no stand-in, so hit +0x148/+0x14c are
    # never both positive.
    pairs = [(0, 0), (0, 77), (88, 0), (-5, 66), (77, -6), (-1, -1)]
    for state in (3, 0x19, 0, 5):
        for index, (px, py) in enumerate(pairs):
            yield call(f"26ae state {state} pair {px},{py}", rnd, 0x26AE,
                       p2={0x1C: state, 0x24: 0x1234}, hit={0x148: u32(px), 0x14C: u32(py), 0x108: index % 3},
                       p3={0: index & 1}, ykeys=("CLAW_FALL",))
    sets = (8, 9, 10, 0x12)
    others = (0, 7, 11, 0x11, 0x13, 0x48, u32(-8))
    for value in sets:
        for found in (True, False):
            yield call(f"26ae falling kind {value:#x} found {found}", rnd, 0x26AE,
                       p2={0x1C: 4}, p3={0x3C: value, 0: value & 1, 0x124: 0xBAD0},
                       hit={0x148: 0, 0x14C: 5, 0x108: 0},
                       ykeys=("CLAW_FALL",) if found else ("CLAW_SWING",))
    for value in others:
        for hit_extra in (0, 9):
            yield call(f"26ae state 4 player kind {value:#x}", rnd, 0x26AE,
                       p2={0x1C: 4}, p3={0x3C: value, 0: hit_extra & 1},
                       hit={0x148: 0, 0x14C: 0, 0x108: hit_extra},
                       ykeys=("CLAW_FALL",))
    yield call("26ae state 4 fall animation missing", rnd, 0x26AE, p2={0x1C: 4}, p3={0x3C: 5},
               hit={0x108: 3, 0x148: 0, 0x14C: 0})
    yield call("26ae state 4 negative flag word", rnd, 0x26AE, p2={0x1C: 4}, p3={0x3C: 5},
               hit={0x108: u32(-3), 0x148: 0, 0x14C: 0, 8: 0xFFFFFFFF}, ykeys=("CLAW_FALL",),
               claw={8: 0xFFFFFFFF})
    yield call("26ae state 4 player holds an animation to drop", rnd, 0x26AE, p2={0x1C: 4},
               p3={0x3C: 5, 4: 1, 0x124: lambda t: t["fall"]}, hit={0x108: 3, 0x148: 0, 0x14C: 0},
               ykeys=("CLAW_FALL",))
    yield call("26ae state 4 player holds an animation to drop, falling", rnd, 0x26AE, p2={0x1C: 4},
               p3={0x3C: 9, 4: 1, 0x124: lambda t: t["swing"]}, hit={0x108: 3, 0x148: 0, 0x14C: 0},
               ykeys=("CLAW_FALL",))

    # 0x26af: the claw grabs a ledge. Vertical distance is |claw.y - (box.y + body.y) - 0x10| < 0x30.
    def ledge(label, state=4, p3_flag=0, p3_owner=None, delta=0, wait=0, ykeys=("CLAW_SWING",), **extra):
        # claw +0x50 = box + body + 0x10 + delta, with box +0x50 = c and body +0x144 = b
        rnd_c = rnd.randrange(100, 4000)
        rnd_b = rnd.randrange(1, 90)
        claw_y = u32(rnd_c + rnd_b + 0x10 + delta)
        fields = {
            "claw": {0xCC: state, 0x50: claw_y, 0x4C: 0x5151, **extra.pop("claw", {})},
            "c": {0x50: rnd_c, 0x4C: rnd.randrange(50, 900)},
            "p3": {0x11C: p3_flag, 0x134: (lambda t: t["hit"]) if p3_owner == "hit" else (p3_owner or 0x4242),
                   0: wait, 0xF8: 0x7777},
        }
        fields["p3"].update(extra.pop("p3", {}))
        return call(label, rnd, 0x26AF, claw=fields["claw"], c=fields["c"], b={0x144: rnd_b, 0x140: rnd.randrange(1, 300)}, p3=fields["p3"],
                    hit={0x108: 0}, ykeys=ykeys, **extra)

    for delta in (-0x31, -0x30, -0x2F, -1, 0, 1, 0x2E, 0x2F, 0x30, 0x31, 0x1000, -0x1000):
        for facing in (0, 1):
            yield ledge(f"26af delta {delta:#x} facing {facing}", delta=delta, wait=facing)
    for state in (0, 1, 2, 3, 4, 5, 8, 0x13):
        yield ledge(f"26af claw state {state}", state=state)
    for p3_flag, owner in ((0, None), (0, "hit"), (1, None), (1, "hit"), (0x55, "hit"), (u32(-1), "hit")):
        yield ledge(f"26af held {p3_flag} owner {owner}", p3_flag=p3_flag, p3_owner=owner)
    yield ledge("26af swing missing", ykeys=())
    yield ledge("26af already holding swing, state 3", state=3, p3_flag=2, p3_owner=0x1)

    # 0x26b0: health pickup, clamped at 99.
    for amount in (u32(-4), 0, 1, 5, 40, 100, 500):
        for health in (0, 17, 94, 99):
            yield call(f"26b0 amount {amount:#x} health {health}", rnd, 0x26B0,
                       hit={0x108: amount}, p3={0x78: health, 0x7C: 3, 0xF8: 9}, tag=health & 1)
    for health, amount in ((98, 1), (98, 2), (99, 1), (0, 99), (0, 100), (1, 98), (1, 99)):
        yield call(f"26b0 exact sum {health}+{amount}", rnd, 0x26B0, hit={0x108: amount}, p3={0x78: health})
    for matches in (False, True):
        yield call(f"26b0 display present, owner matches {matches}", rnd, 0x26B0, display=matches,
                   hit={0x108: 7}, p3={0x78: 30})
    # tag refresh in the shared helper at 0x41d6f0, reached from several kinds
    for tag in (0, 1):
        for same_a in (False, True):
            for same_b in (False, True):
                for map_on in (0, 1):
                    yield call(f"26b0 tag {tag} sameA {same_a} sameB {same_b} map {map_on}", rnd, 0x26B0,
                               tag=tag, hit={0x108: 2}, p3={0x78: 5},
                               g={G_MAP_ON: map_on, G_TAG_A: 0x5000 if same_a else 0x5001, G_TAG_C: 0x5000,
                                  G_TAG_B: lambda t, same_b=same_b: t["tag"] if same_b else 0x777})

    # 0x26b1..0x26b6: the manager decides whether the pickup is taken.
    for kind in range(0x26B1, 0x26B7):
        yield call(f"{kind:#x} no manager", rnd, kind)
        yield call(f"{kind:#x} manager refuses", rnd, kind, manager=True, r58=0)
        yield call(f"{kind:#x} manager accepts", rnd, kind, manager=True, r58=rnd.randrange(1, 1 << 30),
                   tag=kind & 1)
    yield call("26b1 manager accepts, negative answer", rnd, 0x26B1, manager=True, r58=u32(-1))

    # 0x26b7, 0x26b8, 0x26b9, 0x26ba, 0x26bd: timed powerups. The helper at 0x41f990 is only run on
    # its short path (the powerup kind is already current), so the running total is observable.
    def powerup(label, kind, amount, time, extra=0, current=None, hold=0, **options):
        g = {G_POW_KIND: kind if current is None else current, G_POW_TIME: time}
        g.update(options.pop("g", {}))
        hit = {0x108: amount, 0x104: hold}
        hit.update(options.pop("hit", {}))
        return call(label, rnd, kind, hit=hit, g=g, **options)

    for kind in (0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BD):
        for amount in (u32(-9), 0, 1, 30000, 12345):
            for hold in (0, ) if kind in (0x26B7, 0x26BD) else (0, 1, u32(-4)):
                yield powerup(f"{kind:#x} amount {amount:#x} hold {hold}", kind, amount, rnd.randrange(1, 5000),
                              hold=hold, tag=hold & 1, p3={0x7C: 2})
        for time, amount in ((0xF3E58 - 100, 100), (0xF3E58 - 100, 99), (0xF3E58 - 100, 101), (0xF3E00, 0x5000),
                             (0xF3E58, 1)):
            yield powerup(f"{kind:#x} total {time:#x}+{amount:#x}", kind, amount, time)
    for kind in (0x26B8, 0x26B9, 0x26BA):
        for time in (0, 77, 0xF3E59):
            yield powerup(f"{kind:#x} already active, hold positive, time {time:#x}", kind, 400, time, hold=3)
            yield powerup(f"{kind:#x} already active, hold negative, time {time:#x}", kind, 400, time,
                          hold=u32(-3))
    # 0x26b8 runs the helper first; 0x26b9 and 0x26ba the same when not held. Held with a different current kind
    # would take the helper's long path, which needs the application tables and is left out.

    # The helper's long path: the current powerup kind differs, so the previous one is wound down first.
    for kind in (0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BD):
        for current in (0, 0x26B7, 0x26BC, 0x26BD):
            for hold in (0, ) if kind in (0x26B7, 0x26BD) else (1, u32(-4)):
                for carried in (0, 1):
                    if current != 0x26BC and carried:
                        continue
                    yield powerup(f"{kind:#x} replaces {current:#x} hold {hold} carried {carried}", kind,
                                  rnd.randrange(1, 9000), rnd.randrange(1, 5000), current=current, hold=hold,
                                  p3={0x130: (lambda t: t["extra"]) if carried else 0, 0x7C: 5},
                                  tag=carried)
    yield powerup("26b7 replaces a kind with the long-path total unchanged", 0x26B7, 7, 0xF3E00, current=0)
    yield powerup("26b8 replaces 26bc, clears the carried pickup, hold positive", 0x26B8, 9, 3, current=0x26BC,
                  hold=2, p3={0x130: lambda t: t["extra"]})

    # 0x26be: ammo-like counter, then the shared pickup helper at 0x473ae0.
    for count in (u32(-5), u32(-1), 0, 1, 8, 9, 10, 11, 500):
        yield call(f"26be counter {count:#x}", rnd, 0x26BE, p3={0x7C: count}, tag=count & 1,
                   hit={0x164: 0x55AA0000 | (count & 0xFF)})

    # The shared release helper at 0x41c4e0 with a held object.
    for v20, v2fc, indirect in ((5, 5, False), (0, 0x20, False), (u32(-1), 0x21, True), (3, 0x80, True)):
        yield call(f"26ae falling release {v20} {v2fc} {indirect}", rnd, 0x26AE, p2={0x1C: 4},
                   p3={0x3C: 5, 4: 1, 0x124: lambda t: t["fall"], 0x40: 0x33}, hit={0x108: 1, 0x148: 0, 0x14C: 0},
                   ykeys=("CLAW_FALL",), lift=(v20, v2fc, indirect))
        yield ledge(f"26af release {v20} {v2fc} {indirect}", delta=0, wait=v20 & 1, lift=(v20, v2fc, indirect))

    # 0x26ad: the map piece. PostMessageA is a fixture, so the posted window and message are compared.
    for map_on in (0, 1):
        for delay, clock in ((0, (500, 500)), (3, (1000, 1000, 1001, 1002, 1003)), (u32(-1), (7, 9)),
                             (50, (100, 100, 120, 149, 150))):
            for r10, bcc in ((4, 1), (4, 0), (3, 1), (5, 1), (4, 2)):
                yield call(f"26ad found map {map_on} delay {delay:#x} answer {r10} state {bcc}", rnd, 0x26AD,
                           xkeys=("GAME_MAPPIECE",), manager=True, r10=r10, bcc=bcc, delay=delay, clock=clock,
                           g={G_MAP_ON: map_on}, p2={0x24: 0x99, 0x1C: 6}, claw={0xF8: 1000 + bcc},
                           hit={0x108: 5})

    # 0x26ae with both extents positive: posts a window message and records the extents.
    for px, py in ((1, 1), (3, 4), (640, 480), (0x7FFFFFFF, 1), (1, 0x7FFFFFFF)):
        for state in (4, 0x19):
            for hold in (0, 6):
                yield call(f"26ae post {px},{py} state {state} hold {hold}", rnd, 0x26AE,
                           p2={0x1C: state}, hit={0x148: px, 0x14C: py, 0x108: hold},
                           p3={0x3C: 9 if hold else 5}, ykeys=("CLAW_FALL",))
