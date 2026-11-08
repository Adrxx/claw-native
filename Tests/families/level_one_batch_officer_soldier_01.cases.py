"""Cases for level_one_batch_officer_soldier_01: Level 1 Officer and Soldier state callbacks, batch 1.

0x463020, 0x48b4b0 and 0x48ba00 are thiscall methods of an enemy actor. Every case builds one actor with
distinct random contents, a vtable whose used slots log their receiver, and the globals the original callees read.
Coverage comes from the explicit loops below, never from the random draws.
"""
import random

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

M32 = 0xFFFFFFFF
SENTINEL = 0x80000000
F_STATE_A, F_STATE_B, F_SPAWN = 0x463020, 0x48B4B0, 0x48BA00
RAND = 0x4A3050
NEW = 0x4F63EC
ACTOR_INIT_SLOT = 0x5137F0 + 0x28  # vtable the actor factory 0x4c8be0 installs before initialising

G_POWER = 0x534EAC       # compared with 0x26b7
G_PLAYER = 0x537E88      # pointer to the player
G_SVC_Q, G_SVC_BUSY, G_SVC_OWNER = 0x53C9AC, 0x53C9A8, 0x53C9B0
G_ENV = 0x5371FC         # chain to the name registry used by 0x48ceb0
G_SCALE = 0x5430C4
G_FX_ENABLE, G_FX_ARG = 0x532C0C, 0x532C10
G_TABLE = 0x537698       # table behind 0x441030
G_TABLE_LIST, G_TABLE_COUNT = 0x5376B4, 0x5376B8

OFFICER_NAME = b"LEVEL_OFFICER_00340024"
SENTINELS = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]


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


# ---------------------------------------------------------------------------------------------- the actor

def hook(env, vtable, log, slot, result=0, action=None):
    """A vtable method that logs its receiver and call number at log+slot*2, then optionally acts."""
    def effect(env, call):
        env.put(log + 2 * slot, call.receiver, env.calls_so_far(call.function))
        if action is not None:
            action(env, call)
        return result
    env.put(vtable + slot, env.stub(f"slot-{slot:x}", "thiscall", 0, effect))


def make_vtable(env, r, log, actions=None):
    vtable = env.object(0xB8, "vtable", words=words_of(r, 0x2E))
    actions = actions or {}
    for slot in (0x40, 0x4C, 0x50, 0x54, 0x5C, 0x8C, 0x94, 0xA0, 0xA8):
        hook(env, vtable, log, slot, result=slot)
    for slot in (0x44, 0x48, 0x58, 0x90, 0xA4):
        hook(env, vtable, log, slot, result=0x1000 + slot, action=actions.get(slot))
    return vtable


def make_sub(env, r, flag2, sent=(0, 0, 0), p38=None):
    """The sub-object at actor+0x12c: flag word at +0x40, mirrored pairs at +0x118/0x120, +0x128/0x130, +0x138/0x140."""
    sub = env.object(0x200, "sub", words=words_of(r, 0x80))
    flags = (r.getrandbits(32) & ~2) | (2 if flag2 else 0)
    env.put(sub + 0x40, flags & M32)
    for flag, offset in zip(sent, (0x118, 0x128, 0x138)):
        if flag:
            env.put(sub + offset, SENTINEL)
    if p38 is not None:
        env.put(sub + 0x38, p38 & M32)
    return sub


def make_actor(env, r, *, state, mode, flag2, sent, p38=None, actions=None, edit_flags=3):
    log = env.object(0x180, "log", fill=0)
    obj = env.object(0x480, "actor", words=words_of(r, 0x120))
    sub = make_sub(env, r, flag2, sent, p38)
    env.put(obj, make_vtable(env, r, log, actions))
    env.put(obj + 0x12C, sub)
    env.put(obj + 0x184, state & M32)
    env.put(obj + 0x18C, mode & M32)
    # 0x44edd0 reads a count at +0x2fc and a flag word at +0x300 (inline up to 0x20 entries, otherwise by pointer).
    flagword = r.getrandbits(32) | 4
    if edit_flags <= 0x20:
        env.put(obj + 0x2FC, edit_flags, flagword)
    else:
        target = env.object(8, "flag-words", words=[flagword, r.getrandbits(32)])
        env.put(obj + 0x2FC, edit_flags, target)
    return obj, sub, log


def services(env, r, kind, value=None):
    """Globals for the speech/sound requests 0x48ceb0 and 0x48ce40 (kinds: ok, no-q, busy, no-r, miss, zero)."""
    q = env.object(0x190, "service-q", words=words_of(r, 0x64))
    owner_record = env.object(0x40, "service-r", words=words_of(r, 0x10))
    env.put(q + 0x6C, 0 if kind == "no-r" else owner_record)
    env.put(G_SVC_Q, 0 if kind == "no-q" else q)
    env.put(G_SVC_BUSY, r.randrange(1, 1 << 32) if kind == "busy" else 0)
    env.put(G_SVC_OWNER, r.randrange(1, 1 << 32))
    value = r.randrange(1, 1 << 32) if value is None else value
    entries = {b"LEVEL_SOLDIER": r.randrange(1, 1 << 32), b"LEVEL_OFFICER": r.randrange(1, 1 << 32)}
    if kind != "miss":
        entries[OFFICER_NAME] = 0 if kind == "zero" else value
    registry_owner = registry(env, r, entries, r.choice((1, 3, 5, 7)))
    x = env.object(0x40, "env-x", words=words_of(r, 0x10))
    y = env.object(0x40, "env-y", words=words_of(r, 0x10))
    env.put(G_ENV, x)
    env.put(x + 0x30, y)
    env.put(y + 0x28, registry_owner)
    return q


# ---------------------------------------------------------------------------------------------- 0x463020

def setup_a(seed, *, state=1, mode=2, flag2=False, sent=(0, 0, 0), r1=0, r2=5, p38=0x55, svc="ok", id0=False,
            edit_flags=5, hook48=None):
    def setup(env):
        r = random.Random(seed)
        obj, sub, log = make_actor(env, r, state=state, mode=mode, flag2=flag2, sent=sent, p38=p38,
                                   edit_flags=edit_flags)
        if id0:
            env.put(obj + 0x0C, 0)
        services(env, r, svc)
        env.override(RAND, sequence(r1 & M32, r2 & M32))
        return {"obj": obj}
    return setup


def case_a(label, seed, **options):
    return Case(label, F_STATE_A, setup_a(seed, **options), receiver=lambda t: t["obj"])


# ---------------------------------------------------------------------------------------------- 0x48b4b0

def setup_b(seed, *, state=1, mode=2, flag2=False, sent=(0, 0, 0), power=0, layout="pass", dx=60, dy=0, e38=0x77,
            p38=0x55, f450=0, mutate=None, svc="ok", home=False, id0=False, arg460=None, edit_flags=5, key=None):
    def setup(env):
        r = random.Random(seed)
        actions = {}
        obj, sub, log = None, None, None
        state_holder = {}

        def mutate_action(env, call):
            if mutate == "player-y":
                env.put(state_holder["player"] + 0x50, state_holder["ey"] + 0x200)
            elif mutate == "player-y-near":
                env.put(state_holder["player"] + 0x50, state_holder["ey"] + 1)
            elif mutate == "target-x":
                env.put(state_holder["target"] + 0x4C, state_holder["px"] + 0x100)
            elif mutate == "target-id":
                env.put(state_holder["target"] + 0x38, M32)
            elif mutate == "power":
                env.put(G_POWER, 0x26B7)
            elif mutate == "rows":
                env.put(state_holder["target"] + 0x50, state_holder["ey"] + 0x40)

        if mutate:
            actions[0x48] = mutate_action
        obj, sub, log = make_actor(env, r, state=state, mode=mode, flag2=flag2, sent=sent, p38=p38,
                                   actions=actions, edit_flags=edit_flags)
        # A tile map of 20 x 15 cells of 32 pixels, with one tile object per cell kind.
        results = [1, 0, 2]
        tile_objects = []
        for index, result in enumerate(results):
            methods = env.object(0x30, "tile-vtable", words=words_of(r, 12))

            def tile_effect(env, call, index=index, result=result):
                env.put(log + 0x100 + 12 * index, call.receiver, call.arguments[0], call.arguments[1])
                return result

            env.put(methods + 0x20, env.stub(f"tile-{index}", "thiscall", 2, tile_effect))
            tile_objects.append(env.object(8, "tile", words=[methods, r.getrandbits(32)]))
        tile_table = env.object(16, "tile-table", words=tile_objects + [r.getrandbits(32)])
        cells = []
        for cell in range(300):
            if layout == "free":
                cells.append((0xEEEEEEEE, M32)[cell % 2])
            elif layout == "pass":
                cells.append(0xAB010000 | (1 if cell % 3 else 0xFFFF & 1))
            elif layout == "block":
                cells.append(0xCD000000 | 0)
            elif layout == "two":
                cells.append(0x00EF0002)
            else:
                cells.append(r.choice((0xEEEEEEEE, M32, 0x11110000, 0x22220001, 0x33330002, 0x44440001)))
        array = env.object(4 * 300, "tile-cells", words=cells)
        rows = env.object(4 * 15, "tile-rows", words=[20 * row for row in range(15)])
        tilemap = env.object(0x98, "tilemap", words=words_of(r, 0x26))
        env.put(tilemap + 0x20, array, rows)
        env.put(tilemap + 0x30, 640, 480)
        env.put(tilemap + 0x8C, 5, 5)
        terrain = env.object(0x80, "terrain", words=words_of(r, 0x20))
        env.put(terrain + 0x4C, tile_table)
        env.put(terrain + 0x5C, tilemap)
        scene = env.object(0x40, "scene", words=words_of(r, 0x10))
        env.put(scene + 0x24, terrain)
        holder = env.object(0x40, "holder", words=words_of(r, 0x10))
        env.put(holder + 0x0C, scene)
        env.put(obj + 0x190, holder)
        # The target (actor+0x194) and the player.
        target = env.object(0x80, "target", words=words_of(r, 0x20))
        player = env.object(0x80, "player", words=words_of(r, 0x20))
        px = r.randrange(150, 450)
        ey = r.randrange(100, 350)
        env.put(target + 0x4C, (px - dx) & M32, ey)
        env.put(target + 0x38, e38 & M32)
        env.put(player + 0x4C, px, (ey + dy) & M32)
        env.put(obj + 0x194, target)
        env.put(G_PLAYER, player)
        env.put(G_POWER, 0x26B7 if power else r.choice((0, 1, 0x26B6, 0x26B8, M32)))
        state_holder.update(player=player, target=target, ey=ey, px=px)
        # actor+0x450 progress flag and the arguments of 0x48ce40.
        env.put(obj + 0x450, f450 & M32)
        if id0:
            env.put(obj + 0x0C, 0)
        if arg460 is not None:
            env.put(obj + 0x460, arg460)
        services(env, r, svc)
        # The table behind 0x441030 and the name it yields for 0x44da20.
        low = r.randrange(-3, 40)
        count = 7
        stride = 16
        records = env.object(count * stride, "records", words=words_of(r, count * 4))
        names = []
        for index in range(count):
            name = b"LS_HOME" if (index == 3 and home) else (key or b"LS_PLAIN%d" % index)
            text = env.object(len(name) + 4, "record-name", data=name + b"\0")
            env.put(records + index * stride, text)
            names.append(name)
        env.put(G_TABLE + 8, low & M32, (low + count - 1) & M32, records)
        env.put(G_TABLE + 0x18, stride)
        env.put(G_TABLE + 0x20, r.randrange(1, 1 << 32))
        env.put(G_TABLE_LIST, 0, 0)
        env.put(G_TABLE_COUNT, 0)
        holder10 = env.object(0x30, "key-holder", words=words_of(r, 12))
        env.put(holder10 + 0x1C, (low + 3) & M32)
        env.put(obj + 0x10, holder10)
        env.override(RAND, sequence(r.getrandbits(32), r.getrandbits(32), r.getrandbits(32)))
        return {"obj": obj}
    return setup


def case_b(label, seed, **options):
    return Case(label, F_STATE_B, setup_b(seed, **options), receiver=lambda t: t["obj"])


# ---------------------------------------------------------------------------------------------- 0x48ba00

def setup_c(seed, *, kind="tick", ret=1, a=3, scale=2, tail=True, flag1a0=0, direction=5, flag2=False,
            sent=(0, 0, 0), found=True, first=2, last=9, swap_callback=False, fx_object=False, fx_enable=0,
            x_flag=False):
    def setup(env):
        r = random.Random(seed)
        obj, sub, log = make_actor(env, r, state=1, mode=2, flag2=False, sent=(0, 0, 0))
        env.put(G_SCALE, scale)
        # The animation state at sub+0x188 (0x4c82a0).
        base = sub + 0x188
        junk = words_of(r, 12)
        env.write(base, b"".join(w.to_bytes(4, "little") for w in junk))
        if kind == "none":
            env.put(base + 8, 0)
        else:
            env.put(base + 8, r.randrange(1, 1 << 32))
            env.put(base + 0x1C, r.randrange(1, 1 << 32) if tail or kind in ("run", "expire") else 0)
            if kind == "tick":
                env.put(base + 0x14, a, 0)
                env.put(base + 0x24, ret & M32)
            elif kind == "count":
                env.put(base + 0x14, a, r.randrange(1, 1 << 32))
                env.put(base + 0x24, ret & M32)
            elif kind == "expire":
                env.put(base + 0x14, a, r.randrange(1, 1 << 32))
                env.put(base + 0x20, ret & M32)
            elif kind == "run":
                env.put(base + 0x14, 0)
                env.put(base + 0x20, ret & M32)
        env.put(obj + 0x1A0, flag1a0 & M32)
        px = r.randrange(0x2000, 0x100000)
        py = r.randrange(0x2000, 0x100000)
        off_x, off_y = r.randrange(-0x1000, 0x1000), r.randrange(-0x1000, 0x1000)
        if x_flag:
            px, off_x = 0x1FFFF0, 0x10
        env.put(sub + 0x4C, px, py)
        env.put(sub + 0x64, r.randrange(-50, 50) & M32)
        env.put(obj + 0x454, off_x & M32, off_y & M32, direction & M32)
        # fx call is off limits: 0x4b45f0 reaches imports. Keep the guard false.
        fx = env.object(0x20, "fx", words=words_of(r, 8)) if fx_object else 0
        if fx_enable and fx:
            # 0x4b45f0 returns at once when the word at +0x78 of the object two links down is zero.
            inner = env.object(0x90, "fx-inner", words=words_of(r, 0x24))
            env.put(inner + 0x78, 0)
            middle = env.object(0x40, "fx-middle", words=words_of(r, 0x10))
            env.put(middle + 0x10, inner)
            env.put(fx + 0x10, middle)
        env.put(obj + 0x3B4, fx)
        env.put(G_FX_ENABLE, r.randrange(1, 1 << 32) if fx_enable else 0)
        env.put(G_FX_ARG, r.randrange(1, 1 << 32))
        # The scene behind actor+0x130 and the registries the factory reads.
        holder = env.object(0x40, "holder", words=words_of(r, 0x10))
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
        env.put(holder + 0x0C, world)
        env.put(obj + 0x130, holder)
        metadata = env.object(0x18, "metadata", words=words_of(r, 6))
        env.put(context + 0x14, registry(env, r, {b"Bullet": metadata, b"Bullets": r.randrange(1, 1 << 32)},
                                         r.choice((1, 3, 5, 7))))
        entries = {b"LEVEL_MUSKETBALLS": r.randrange(1, 1 << 32)}
        if found:
            entries[b"LEVEL_MUSKETBALL"] = resource(env, r, first, last)
        env.put(context + 0x10, registry(env, r, entries, r.choice((1, 3, 5, 7))))
        fill = r.randrange(1, 256)
        env.override(NEW, lambda e, c: e.object(c.arguments[0], "allocation", fill=fill))
        # The bullet's logic object: callback at +0x10, mover at +0x18, whose sub-object is at +0x12c.
        flags_k = (r.getrandbits(32) & ~2) | (2 if flag2 else 0)
        mover_k = env.object(0x160, "bullet-k", words=words_of(r, 0x58))
        env.put(mover_k + 0x40, flags_k & M32)
        for flag, offset in zip(sent, (0x118, 0x128, 0x138)):
            if flag:
                env.put(mover_k + offset, SENTINEL)
        mover = env.object(0x160, "bullet-mover", words=words_of(r, 0x58))
        env.put(mover + 0x12C, mover_k)
        other = env.object(0x160, "bullet-mover-2", words=words_of(r, 0x58))
        other_k = env.object(0x160, "bullet-k-2", words=words_of(r, 0x58))
        env.put(other + 0x12C, other_k)
        logic = env.object(0x40, "bullet-logic", words=words_of(r, 0x10))
        env.put(logic + 0x18, mover)

        def callback_effect(env, call):
            env.put(log + 0x150, call.receiver, call.arguments[0], env.calls_so_far(call.function))
            if swap_callback:
                env.put(logic + 0x18, other)
            return 0

        env.put(logic + 0x10, env.stub("service-callback", "cdecl", 1, callback_effect))
        f164, f40, priority = (r.randrange(0, 1 << 32) for _ in range(3))

        def init(env, call):
            actor = call.receiver
            env.put(actor + 0x164, f164)
            env.put(actor + 0x40, f40)
            env.put(actor + 0x64, priority)
            env.put(actor + 0x6C, logic)
            env.put(log + 0x160, call.receiver, *call.arguments)
            return 1

        env.put(ACTOR_INIT_SLOT, env.stub("actor-initializer", "thiscall", 4, init))
        return {"obj": obj, "mover": mover, "mover_k": mover_k}
    return setup


def case_c(label, seed, **options):
    return Case(label, F_SPAWN, setup_c(seed, **options), receiver=lambda t: t["obj"])


# ---------------------------------------------------------------------------------------------- the cases

def cases(random_source):
    rs = random_source

    def seed():
        return rs.getrandbits(32)

    # ---- 0x463020 -------------------------------------------------------------------------------------------
    # Which way the facing flag flips, for every combination of mode, flag and sentinel pair.
    for mode in (2, 1, 3, 0, M32):
        for flag2 in (False, True):
            for sent in SENTINELS:
                yield case_a(f"A mode {mode:#x} flag {int(flag2)} sentinels {sent}", seed(), mode=mode, flag2=flag2,
                             sent=sent, r1=seed(), r2=5)
    # State range check around 0..4, with the sound request attempted or not.
    for state in (-0x80000000, -2, -1, 0, 1, 2, 3, 4, 5, 6, 100, 0x7FFFFFFF, 0x80000001, M32 - 1):
        for edit_flags in (3, 0x20, 0x21, 0x40):
            if 0 <= state <= 4 and edit_flags != 3:
                continue
            if edit_flags in (0x20, 0x40) and state not in (-1, 5):
                continue
            for r2 in (5, 50):
                if r2 == 50 and edit_flags != 3:
                    continue
                yield case_a(f"A state {state:#x} out {edit_flags:#x} rand {r2}", seed(), state=state,
                             edit_flags=edit_flags, r1=seed(), r2=r2)
    # The random threshold (signed remainder by 100 against 0x21) and every way the request can be refused.
    thresholds = (0, 1, 31, 32, 33, 34, 99, 100, 132, 133, 0x7FFFFFFF, M32, M32 - 31, M32 - 32, M32 - 99, M32 - 100,
                  0x80000000, 0x80000001, 0x80000063)
    for r2 in thresholds:
        for svc in ("ok", "no-q", "busy", "no-r", "miss", "zero"):
            if svc != "ok" and r2 not in (0, 32, 33, M32):
                continue
            yield case_a(f"A rand {r2:#x} service {svc}", seed(), r1=0x1234567, r2=r2, svc=svc, state=2)
    for r2 in (5, 32, 33):
        for p38 in (M32, M32 - 1, 0, 0x80000000):
            yield case_a(f"A rand {r2} target {p38:#x}", seed(), r2=r2, p38=p38, state=1, r1=seed())
        yield case_a(f"A rand {r2} no actor id", seed(), r2=r2, id0=True, state=0, r1=seed())
    for _ in range(14):
        yield case_a("A random", seed(), state=rs.randrange(-1, 7), mode=rs.choice((2, 2, 0, 1, 3)),
                     flag2=rs.random() < 0.5, sent=rs.choice(SENTINELS), r1=seed(), r2=seed(),
                     p38=rs.choice((M32, 0x55, rs.getrandbits(32))), svc=rs.choice(("ok", "ok", "miss", "busy")),
                     id0=rs.random() < 0.1, edit_flags=rs.choice((3, 0x10, 0x21, 0x30)))

    # ---- 0x48b4b0 -------------------------------------------------------------------------------------------
    for mode in (2, 1, 3, 0, M32):
        for flag2 in (False, True):
            for sent in SENTINELS if mode in (2, 1) else SENTINELS[::7]:
                yield case_b(f"B mode {mode:#x} flag {int(flag2)} sentinels {sent}", seed(), mode=mode, flag2=flag2,
                             sent=sent, state=1, layout="mixed")
    for state in (0, 1, 2, 3, 4, 5, 6, 7, -1, 0x80000000):
        for power in (0, 1):
            for layout in (("free", "pass", "block", "two", "mixed") if state in (0, 1, 2) else ("free", "block")):
                yield case_b(f"B state {state:#x} power {power} terrain {layout}", seed(), state=state, power=power,
                             layout=layout, f450=0 if state != 0 else 1)
    # Vertical window of +-0x32 around the target, with the clear and the blocked terrain.
    for state in (0, 2, 5):
        for dy in (-0x33, -0x32, -0x31, 0, 0x31, 0x32, 0x33):
            for layout in ("pass", "free", "mixed"):
                yield case_b(f"B state {state} dy {dy} terrain {layout}", seed(), state=state, dy=dy, layout=layout)
    for state in (0, 1, 2, 5):
        for e38 in (M32, 0, M32 - 1):
            for dy in (0, 0x40):
                yield case_b(f"B state {state} target id {e38:#x} dy {dy}", seed(), state=state, e38=e38, dy=dy)
    for p38 in (M32, 0, 7):
        for f450 in (0, 1, 7, 0x80000000):
            for dy in (0, 0x50):
                yield case_b(f"B launch p38 {p38:#x} f450 {f450:#x} dy {dy}", seed(), state=0, p38=p38, f450=f450,
                             dy=dy)
    for svc in ("no-q", "busy", "no-r"):
        yield case_b(f"B launch service {svc}", seed(), state=1, svc=svc, f450=0)
    yield case_b("B launch no actor id", seed(), state=1, id0=True, f450=0)
    yield case_b("B launch no argument", seed(), state=1, arg460=0, f450=0)
    # Horizontal span: left of, over, right of the player, and wide.
    for dx in (-200, -33, -1, 0, 1, 31, 32, 33, 200):
        for layout in ("mixed", "block"):
            yield case_b(f"B span dx {dx} terrain {layout}", seed(), state=1, dx=dx, layout=layout)
    # The second distance test comes after the first handler and sees what that handler changed.
    for mutate in ("player-y", "player-y-near", "target-x", "target-id", "power", "rows"):
        for layout in ("pass", "mixed"):
            for dy in ((0, 0x30)[:1] if layout == "pass" else (0x30,)):
                yield case_b(f"B handler changes {mutate} terrain {layout} dy {dy}", seed(), state=0, mutate=mutate,
                             layout=layout, dy=dy, f450=1)
    # The handler 0x44da20 does its work only when the name of the entry is the home one.
    for state in (5, 6, 7, -1):
        for layout in ("block", "pass"):
            for mode in (2, 0):
                if mode == 0 and layout == "block":
                    continue
                yield case_b(f"B home key state {state} terrain {layout} mode {mode}", seed(), state=state,
                             layout=layout, home=True, mode=mode, dy=0x80 if layout == "block" else 0)
    for _ in range(12):
        yield case_b("B random", seed(), state=rs.randrange(-1, 8), mode=rs.choice((2, 2, 0, 1)),
                     flag2=rs.random() < 0.5, sent=rs.choice(SENTINELS), power=rs.random() < 0.3,
                     layout=rs.choice(("free", "pass", "block", "two", "mixed")), dx=rs.randrange(-150, 150),
                     dy=rs.randrange(-0x45, 0x45), e38=rs.choice((M32, 0x77, rs.getrandbits(32))),
                     p38=rs.choice((M32, 0x55)), f450=rs.choice((0, 0, 1, rs.getrandbits(32))),
                     edit_flags=rs.choice((3, 0x21)))

    # ---- 0x48ba00 -------------------------------------------------------------------------------------------
    # Animation outcomes: which one returns 1 and spawns, and whether the end-of-clip callback follows.
    spawners = (
        ("tick", dict(kind="tick", a=1, tail=True)),
        ("tick-no-tail", dict(kind="tick", a=1, tail=False)),
        ("tick-running", dict(kind="tick", a=6, tail=True)),
        ("count", dict(kind="count", a=9, scale=4, tail=True)),
        ("expire", dict(kind="expire", a=2, scale=5, tail=True)),
        ("expire-exact", dict(kind="expire", a=3, scale=3, tail=True)),
        ("run", dict(kind="run", tail=True)),
    )
    for name, options in spawners:
        for direction in (7, 0, -9):
            yield case_c(f"C {name} direction {direction}", seed(), ret=1, direction=direction, **options)
    for direction in (M32, 1, 0x7FFFFFFF, 0x80000000, -0x12345):
        yield case_c(f"C direction {direction:#x}", seed(), kind="tick", a=1, ret=1, direction=direction)
    for flag2 in (False, True):
        for sent in SENTINELS:
            yield case_c(f"C mirror flag {int(flag2)} sentinels {sent}", seed(), kind="tick", a=1, ret=1,
                         direction=-3, flag2=flag2, sent=sent)
            if sent not in ((0, 0, 0), (1, 1, 1), (1, 0, 1), (0, 1, 0)):
                continue
            yield case_c(f"C mirror flag {int(flag2)} sentinels {sent} callback swaps", seed(), kind="tick",
                         a=2, ret=1, direction=-1, flag2=flag2, sent=sent, swap_callback=True)
    for ret in (0, 2, 3, M32, 0x80000001):
        for name, options in spawners:
            if name in ("tick", "run", "expire"):
                yield case_c(f"C {name} returns {ret:#x}", seed(), ret=ret, **options)
    yield case_c("C animation missing", seed(), kind="none")
    yield case_c("C animation missing no clip", seed(), kind="none", flag1a0=1)
    for name, options in spawners:
        yield case_c(f"C {name} already spawned", seed(), ret=1, flag1a0=1, **options)
    yield case_c("C already spawned high bit", seed(), ret=1, flag1a0=0x80000000, kind="tick", a=4)
    for found, first, last in ((True, 0, 15), (True, 15, 15), (True, 3, 2), (True, 9, 3), (True, 0, 0),
                               (False, 2, 9)):
        yield case_c(f"C resource found {found} range {first}..{last}", seed(), ret=1, kind="tick", a=1,
                     found=found, first=first, last=last)
    yield case_c("C position flag 0x200000", seed(), ret=1, kind="tick", a=1, x_flag=True)
    yield case_c("C position flag 0x200000 mirrored", seed(), ret=1, kind="tick", a=1, x_flag=True, direction=-4,
                 swap_callback=True)
    yield case_c("C effect object without enable", seed(), ret=1, kind="tick", a=1, fx_object=True)
    for ret in (1, 1, 0):
        for direction in (3, -3):
            yield case_c(f"C effect call ret {ret} direction {direction}", seed(), ret=ret, kind="tick", a=1,
                         direction=direction, fx_object=True, fx_enable=1)
    yield case_c("C effect call animation missing", seed(), kind="none", fx_object=True, fx_enable=1)
    yield case_c("C effect enabled without object", seed(), ret=1, kind="tick", a=1, fx_enable=1)
    yield case_c("C effect object without spawn", seed(), ret=0, kind="tick", a=1, fx_object=True)
    yield case_c("C effect object animation missing", seed(), kind="none", fx_object=True)
    for scale in (0, 1, 2, 7, 0x7FFFFFFF, M32):
        yield case_c(f"C counter scale {scale:#x}", seed(), kind="count", a=5, scale=scale, ret=1)
    for _ in range(12):
        name, options = rs.choice(spawners)
        yield case_c("C random", seed(), ret=rs.choice((1, 1, 0, 2)), direction=rs.randrange(-30, 30),
                     flag2=rs.random() < 0.5, sent=rs.choice(SENTINELS), swap_callback=rs.random() < 0.3,
                     flag1a0=rs.choice((0, 0, 0, 1)), found=rs.random() < 0.8, first=rs.randrange(0, 8),
                     last=rs.randrange(0, 15), **options)
