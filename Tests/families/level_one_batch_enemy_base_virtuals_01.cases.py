"""Cases for level_one_batch_enemy_base_virtuals_01: Level 1 shared enemy base virtual slots (hit, contact, damage handlers).

Every owned function is a method of a Level 1 enemy actor ("this"). Each case builds one actor with distinct non-zero
contents, a vtable whose used slots log (slot, receiver, argument, call order) into case memory, and the globals and
sub-objects the original callees read. Branch coverage comes from the explicit loops in cases(), never from random draws:
the random source only varies the contents around them. The random-number stand-in is scripted per case.

0x4b45f0 is only reached with an effect object whose chain ends in a zero word at +0x78, where it returns at once.
"""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import sequence

M32 = 0xFFFFFFFF
SENTINEL = 0x80000000
RAND, NEW = 0x4A3050, 0x4F63EC

F_DEATH, F_RELEASE, F_HIT, F_CONTACT, F_EXPLODE = 0x44DF60, 0x44CFD0, 0x44D460, 0x44D570, 0x44D5A0
F_PLAIN, F_STUN, F_AIM, F_HOME, F_SETTIME = 0x44D700, 0x44D730, 0x44D760, 0x44D9F0, 0x43E9C0
F_POLL, F_HITLOW, F_BURST = 0x43E9E0, 0x44F3C0, 0x440E20

G_TIME = 0x537210
G_PLAYER = 0x537E88
G_POWER = 0x534EAC
G_FX_ENABLE, G_FX_ARG = 0x532C0C, 0x532C10
G_TRIE = 0x537668
G_TABLE, G_TABLE_LIST, G_TABLE_COUNT = 0x537698, 0x5376B4, 0x5376B8
G_LOCALE = 0x540E00
LOCK = 0x4A7BC0
G_SVC_Q, G_SVC_OWNER = 0x53C9AC, 0x53C9B0

HOME, LOW, HIGH = b"LS_HOME", b"LS_HITLOW", b"LS_HITHIGH"
N_ENEMY, N_CLAW = b"GAME_ENEMYHIT", b"GAME_CLAWHIT"
N_SML, N_MED, N_BIG = b"GAME_SMLHITBURST", b"GAME_MEDHITBURST", b"GAME_BIGHITBURST"
N_FIRE, N_LIGHT, N_ICE = b"GAME_EXPLOS_FIRE", b"GAME_EXPLOS_LIGHTNING", b"GAME_EXPLOS_ICE"
N_FIRE_X, N_LIGHT_X, N_ICE_X = b"GAME_FIRESWORDEXPLOSION", b"GAME_LIGHTNINGEXPLOSION", b"GAME_ICESWORDEXPLOSION"
N_BURST, N_ANI = b"HitBurst", b"AniCycleNormal"
D_FIRE, D_ICE, D_NULL = b"GAME_FIREDEATH", b"GAME_ICEDEATH", b"GAME_NULL"

SLOT_ARGC = {0x28: 1, 0x2C: 1, 0x30: 1, 0x34: 1, 0x38: 1, 0x3C: 1, 0x40: 1, 0x44: 0, 0x5C: 1, 0x60: 0}
FX_OFFSETS = (0x414, 0x418, 0x41C, 0x390, 0x394, 0x398, 0x39C)


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def dbl(env, address, value):
    env.write(address, struct.pack("<d", value))


def registry(env, r, entries, buckets=5):
    """String table behind 0x4f6286, at owner+0x10 (+4 bucket array, +8 bucket count). Node: [next, 0, key, value]."""
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


def animation(env, r, count=None):
    """An animation resource read by 0x4c8220: +0xc array of frame pointers, +0x10 count (at least one)."""
    count = count or r.randrange(1, 4)
    frames = [env.object(0x30, "frame", words=words_of(r, 12)) for _ in range(count)]
    array = env.object(4 * count, "frame-array", words=frames)
    return env.object(0x30, "animation", words=[0, 0, 0, array, count] + words_of(r, 7))


def sprite_set(env, r, low=None, high=None):
    """A frame-set read by 0x4c7970: +0x64 first, +0x68 last, +0x14 table of frame values indexed by first."""
    low = r.randrange(0, 6) if low is None else low
    high = r.randrange(low, low + 4) if high is None else high
    table = env.object(0x40, "sprite-table", words=words_of(r, 16))
    obj = env.object(0x80, "sprite-set", words=words_of(r, 0x20))
    env.put(obj + 0x14, table)
    env.put(obj + 0x64, low & M32, high & M32)
    return obj


def world(env, r, omit=()):
    """A scene with its context, three name tables and a logging service callback (the actor factory's inputs)."""
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    env.put(scene + 0xC, context)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for i in range(63):
        env.put(pool + i * 12, pool + (i + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    log = env.object(0x800, "observations", fill=0)
    fill = r.randrange(1, 256)
    env.override(NEW, lambda e, c: e.object(c.arguments[0], "allocation", fill=fill))

    def notify(env, call):
        actor = call.arguments[0]
        n = env.get(log)
        env.put(log, n + 1)
        row = log + 4 + (n % 20) * 40
        service = env.get(actor + 0x6C)
        env.put(row, call.receiver, actor, env.get(actor + 0x80), env.get(actor + 0x16C), env.get(actor + 0x170),
                env.get(actor + 0x174), env.get(service + 0x1C), env.get(actor + 8))
        return 0

    stub = env.stub("hit-burst-service-callback", "cdecl", 1, notify)
    a_names = [N_ENEMY, N_CLAW, N_FIRE, N_LIGHT, N_ICE]
    c_names = [N_SML, N_MED, N_BIG, N_FIRE_X, N_LIGHT_X, N_ICE_X]
    b_names = [N_BURST, N_ANI]
    a = {n: sprite_set(env, r) for n in a_names if n not in omit}
    c = {n: animation(env, r) for n in c_names if n not in omit}
    metas = {}
    for n in b_names:
        if n in omit:
            continue
        meta = env.object(0x18, "actor-metadata", words=words_of(r, 6))
        env.put(meta + 8, r.randrange(0, 4))
        env.put(meta + 0x10, stub)
        metas[n] = meta
    env.put(context + 0x10, registry(env, r, a))
    env.put(context + 0x14, registry(env, r, metas))
    env.put(context + 0x2C, registry(env, r, c))
    owner = env.object(0x20, "owner", words=words_of(r, 8))
    env.put(owner + 8, scene)
    return {"owner": owner, "scene": scene, "log": log}


def fx_object(env, r):
    """An effect holder for which 0x4b45f0 returns at once (the word at +0x78 two links down is zero)."""
    inner = env.object(0x90, "fx-inner", words=words_of(r, 0x24))
    env.put(inner + 0x78, 0)
    middle = env.object(0x40, "fx-middle", words=words_of(r, 0x10))
    env.put(middle + 0x10, inner)
    holder = env.object(0x40, "fx", words=words_of(r, 0x10))
    env.put(holder + 0x10, middle)
    return holder


def leaf(env, r, name, bit, value, bad):
    text = bad.get(name, name)
    key = env.object(len(text) + 4, "trie-key", data=text + b"\0")
    return env.object(0x14, "trie-leaf", words=[r.getrandbits(32), r.getrandbits(32), bit, key, value])


def trie(env, r, kind="full", bad=None):
    """The bit trie behind 0x4dba00 at 0x537668: root bit 33 splits HOME from the HIT names, bit 50 LOW from HIGH."""
    bad = bad or {}
    values = {n: r.randrange(1, 1 << 32) for n in (HOME, LOW, HIGH)}
    if kind == "empty":
        env.put(G_TRIE + 0x18, 0)
        return values
    if kind == "shallow":
        env.put(G_TRIE + 0x18, env.object(0x14, "trie-root", words=[0, 0, 200, 0, 0]))
        return values
    home = leaf(env, r, HOME, 33, values[HOME], bad)
    high = leaf(env, r, HIGH, 50, values[HIGH], bad)
    low = leaf(env, r, LOW, 50, values[LOW], bad)
    x = env.object(0x14, "trie-x", words=[high, low, 50, r.getrandbits(32), r.getrandbits(32)])
    root = env.object(0x14, "trie-root", words=[x, home, 33, r.getrandbits(32), r.getrandbits(32)])
    if kind == "null-low":
        env.put(x + 4, 0)
    elif kind == "null-high":
        env.put(x, 0)
    elif kind == "null-home":
        env.put(root + 4, 0)
    elif kind == "null-x":
        env.put(root, 0)
    env.put(G_TRIE + 0x18, root)
    return values


def vtable(env, r, log, acts):
    vt = env.object(0x80, "vtable", words=words_of(r, 0x20))
    for slot, argc in SLOT_ARGC.items():
        def effect(env, call, slot=slot):
            n = env.get(log)
            env.put(log, n + 1)
            args = list(call.arguments) + [0]
            env.put(log + 4 + 16 * (n % 30), slot, call.receiver, args[0], n)
            action = acts.get(slot)
            if action is not None:
                action(env, call)
            return 0x7000 + slot
        env.put(vt + slot, env.stub(f"slot-{slot:x}", "thiscall", argc, effect))
    return vt


def build(env, r, *, w1=True, w2=False, fx=None, mode=3, trie_kind="full", trie_bad=None, name=b"LS_PLAIN",
          listcount=0, anims=(True, True), rands=None, locale=0, fx_enable=1, death=None, omit=(), edit=None):
    t = {}
    log = env.object(0x200, "log", fill=0)
    acts = {}
    vt = vtable(env, r, log, acts)
    this = env.object(0x480, "enemy", words=words_of(r, 0x120))
    owner_entity = env.object(0x180, "owner-entity", words=words_of(r, 0x60))
    player_info = env.object(0x180, "player-info", words=words_of(r, 0x60))
    logic = env.object(0x30, "logic", words=words_of(r, 12))
    sub = env.object(0x1C0, "sub", words=words_of(r, 0x70))
    sub_y = env.object(0x40, "sub-y", words=words_of(r, 0x10))
    holder = env.object(0x40, "holder", words=words_of(r, 0x10))
    hit = env.object(0x150, "hit", words=words_of(r, 0x54))
    death_registry = registry(env, r, death or {}, r.choice((1, 3, 5, 7)))
    # The player chain read by 0x43e9e0 and 0x44d460.
    player_global = env.object(0x80, "player-global", words=words_of(r, 0x20))
    player_mid = env.object(0x80, "player-mid", words=words_of(r, 0x20))
    player_end = env.object(0x100, "player-end", words=words_of(r, 0x40))
    env.put(G_PLAYER, player_global)
    env.put(player_global + 0x6C, player_mid)
    env.put(player_mid + 0x14, player_end)
    env.put(player_end + 0x14, 0)
    ident = r.randrange(1, 1 << 32)
    env.put(player_end + 0xE8, ident)
    env.put(this + 0x19C, ident ^ r.randrange(1, 1 << 32) or 1)
    env.put(this, vt)
    env.put(this + 0xC, owner_entity)
    env.put(this + 0x10, logic)
    env.put(this + 0x12C, sub)
    env.put(this + 0x130, holder)
    env.put(this + 0x18C, mode & M32)
    env.put(sub + 0xC, sub_y)
    env.put(sub_y + 0x2C, death_registry)
    env.put(owner_entity + 8, r.getrandbits(32) & ~0x10000)
    env.put(owner_entity + 0x38, r.randrange(0, 0x7FFFFFFF))
    env.put(owner_entity + 0x74, player_info)
    env.put(owner_entity + 0x10C, 1)
    env.put(player_info + 0x164, 0)
    env.put(player_info + 0xD0, 2)
    env.put(this + 0x44C, 0)
    env.put(this + 0x3D0, r.getrandbits(32))
    env.put(this + 0x3D4, 0)
    env.put(G_TIME, r.getrandbits(32))
    env.put(G_LOCALE, locale)
    env.put(G_POWER, 0)
    env.put(G_FX_ENABLE, fx_enable)
    env.put(G_FX_ARG, r.randrange(1, 1 << 32))
    env.put(G_SVC_Q, 0)
    for offset in FX_OFFSETS:
        env.put(this + offset, fx_object(env, r) if (fx or {}).get(offset) else 0)
    env.put(this + 0x334, animation(env, r) if anims[0] else 0)
    env.put(this + 0x338, animation(env, r) if anims[1] else 0)
    dbl(env, this + 0x68, r.uniform(-300, 700))
    dbl(env, this + 0x70, r.uniform(-300, 700))
    env.put(owner_entity + 0x12C, r.randrange(-200, 100) & M32, r.randrange(100, 400) & M32)
    env.put(owner_entity + 0x134, r.randrange(100, 400) & M32)
    env.put(hit + 0x138, r.randrange(0, 0x7FFFFFFF))
    env.put(hit + 0x13C, r.randrange(-300, 500) & M32)
    env.put(hit + 0x144, r.randrange(-300, 500) & M32)
    env.put(hit + 0x50, r.randrange(-300, 500) & M32)
    # The table behind 0x441030 and the list behind 0x4f6439.
    low = r.randrange(-3, 40)
    records = env.object(7 * 16, "records", words=words_of(r, 28))
    for index in range(7):
        text = name if index == 3 else b"LS_PLAIN%d" % index
        env.put(records + index * 16, env.object(len(text) + 4, "record-name", data=text + b"\0"))
    env.put(G_TABLE + 8, low & M32, (low + 6) & M32, records)
    env.put(G_TABLE + 0x18, 16)
    env.put(G_TABLE + 0x20, r.randrange(1, 1 << 32))
    env.put(logic + 0x1C, (low + 3) & M32)
    if listcount:
        env.put(G_TABLE_LIST, env.object(4 * listcount + 4, "list", words=words_of(r, listcount + 1)))
    else:
        env.put(G_TABLE_LIST, 0)
    env.put(G_TABLE_COUNT, listcount)
    values = trie(env, r, trie_kind, trie_bad)
    t.update(this=this, A=owner_entity, Pl=player_info, L=logic, S=sub, Y=sub_y, Z=death_registry, H=holder, P=hit,
             p2=player_end, log=log, acts=acts, values=values, ident=ident)
    t["w1"] = world(env, r, omit) if w1 else None
    env.put(owner_entity + 0xC, t["w1"]["owner"] if w1 else 0)
    t["w2"] = world(env, r, omit) if w2 else None
    env.put(holder + 0xC, t["w2"]["owner"] if w2 else 0)
    script = rands if rands is not None else [r.getrandbits(32) for _ in range(6)]
    env.override(RAND, sequence(*script))
    if edit is not None:
        edit(env, t, r)
    return t


def make(seed, **options):
    def setup(env):
        return build(env, random.Random(seed), **options)
    return setup


def case(label, function, seed, argc=1, **options):
    return Case(label, function, make(seed, **options), receiver=lambda t: t["this"],
                arguments=((lambda t: t["P"],) if argc else ()))


# ------------------------------------------------------------------------------------------------ edit helpers

def edits(*parts):
    def edit(env, t, r):
        for part in parts:
            part(env, t, r)
    return edit


def burst_edit(x=None, y=None, p138=None, p13c=0, p144=0, p50=0, lo=0, hi=0, dead=False, done=False):
    """Inputs of 0x440e20: the two doubles, the hit descriptor words and the owner's clamp bounds."""
    def edit(env, t, r):
        if x is not None:
            dbl(env, t["this"] + 0x68, x)
        if y is not None:
            dbl(env, t["this"] + 0x70, y)
        env.put(t["P"] + 0x138, SENTINEL if p138 is None else p138 & M32)
        env.put(t["P"] + 0x13C, p13c & M32)
        env.put(t["P"] + 0x144, p144 & M32)
        env.put(t["P"] + 0x50, p50 & M32)
        env.put(t["A"] + 0x12C, lo & M32)
        env.put(t["A"] + 0x134, hi & M32)
        if dead:
            env.put(t["A"] + 0x38, M32)
        if done:
            env.put(t["A"] + 8, env.get(t["A"] + 8) | 0x10000)
    return edit


def poke(**fields):
    """Set words: keys 'this', 'A', 'P', 'Pl', 'L', 'S', 'p2' name the object, values map offset to word."""
    def edit(env, t, r):
        for owner, items in fields.items():
            for offset, value in items.items():
                env.put(t[owner] + offset, value & M32)
    return edit


def global_poke(**words):
    def edit(env, t, r):
        for address, value in words.items():
            env.put(int(address[1:], 16), value & M32)
    return edit


def grow_edit(where, k, second=0):
    """Make the table lookup of 0x441030 fall outside the table so that 0x4db6e0 grows it by k records.

    With second > 0 the first string compare's lock stand-in moves the table window so the next lookup grows it again."""
    def edit(env, t, r):
        low, high = env.get(G_TABLE + 8), env.get(G_TABLE + 0xC)
        env.put(t["L"] + 0x1C, ((high + k) if where == "above" else (low - k)) & M32)
        if second:
            def lock(env, call):
                if env.calls_so_far(call.function) == 1:
                    env.put(G_TABLE + 8, (env.get(G_TABLE + 8) + second) & M32, (env.get(G_TABLE + 0xC) + second) & M32)
                return 0
            env.override(LOCK, lock)
    return edit


def act(slot, fn):
    def edit(env, t, r):
        t["acts"][slot] = lambda e, c: fn(e, c, t)
    return edit


# ------------------------------------------------------------------------------------------------ the cases

RAND_PAIRS = [(0, 0), (8, 8), (4, 5), (9, 17), (M32, 1), (0x80000000, 0x7FFFFFFF), (-9 & M32, 0x12345678)]


def cases(random_source):
    rs = random_source

    def seed():
        return rs.getrandbits(32)

    # ---------------------------------------------------------------- 0x43e9c0
    for value in (0, 1, 300, 2000, 0x7FFFFFFF, 0x80000000, M32, rs.getrandbits(32)):
        yield Case(f"settime value {value:#x}", F_SETTIME, make(seed(), w1=False),
                   receiver=lambda t: t["this"], arguments=(value,))

    # ---------------------------------------------------------------- 0x43e9e0
    yield case("poll same id returns zero", F_POLL, seed(), argc=0, w1=False, edit=poke(this={0x19C: 0x1234}, p2={0xE8: 0x1234}))
    for window, delta in ((5, 0), (5, 4), (5, 5), (5, 6), (0, 0), (1, 0), (1, 1), (0x80000000, 0x7FFFFFFF),
                          (0x80000000, 0x80000000), (M32, M32 - 1), (M32, M32)):
        start = rs.getrandbits(32)

        def window_edit(env, t, r, window=window, delta=delta, start=start):
            env.put(G_TIME, (start + delta) & M32)
            env.put(t["this"] + 0x3D0, start)
            env.put(t["this"] + 0x3D4, window)
        yield case(f"poll window {window:#x} elapsed {delta:#x}", F_POLL, seed(), argc=0, w1=False, edit=window_edit)

    def wrapped(env, t, r):
        env.put(G_TIME, 3)
        env.put(t["this"] + 0x3D0, M32 - 1)
        env.put(t["this"] + 0x3D4, 6)
    yield case("poll clock wrapped", F_POLL, seed(), argc=0, w1=False, edit=wrapped)

    kinds = (0x10, 2, 0x1000, 0x20, 0x1000000, 0x2000000, 0, 1, 3, 0xF, 0x11, 0x12, 0x21, 0x1001, 0x1000001, 0x2000001,
             0x3000000, 0x80000000, M32, 0x100000, 0x10000000, 0x40)
    for kind in kinds:
        for count in (0, 3):
            yield case(f"poll kind {kind:#x} count {count}", F_POLL, seed(), argc=0, w1=False,
                       edit=poke(Pl={0xD0: kind}, A={0x10C: count}))
    for count in (-1, 1, 0x7FFFFFFF, 0x80000000):
        yield case(f"poll count {count & M32:#x}", F_POLL, seed(), argc=0, w1=False,
                   edit=poke(Pl={0xD0: 0x10}, A={0x10C: count}))
    yield case("poll count re-read after slot", F_POLL, seed(), argc=0, w1=False,
               edit=edits(poke(Pl={0xD0: 2}, A={0x10C: 5}), act(0x2C, lambda e, c, t: e.put(t["A"] + 0x10C, 0))))
    yield case("poll count re-read raised", F_POLL, seed(), argc=0, w1=False,
               edit=edits(poke(Pl={0xD0: 0x1000}, A={0x10C: 0}), act(0x40, lambda e, c, t: e.put(t["A"] + 0x10C, 9))))
    yield case("poll clamp stored before slot", F_POLL, seed(), argc=0, w1=False,
               edit=act(0x2C, lambda e, c, t: e.put(t["p2"] + 0xE8, 7)))

    # ---------------------------------------------------------------- 0x44cfd0
    for state in ("null-global", "different-id", "null-child", "wrong-kind", "matching", "zero-id"):
        for flags in (None, 0, 0x10000, "random"):
            def release_edit(env, t, r, state=state, flags=flags):
                outer = env.object(0x70, "global-owner", words=words_of(r, 0x1C))
                inner = env.object(0x134, "global-child", words=words_of(r, 0x4D))
                identity = t["A"]
                env.put(G_SVC_Q, 0 if state == "null-global" else outer)
                env.put(G_SVC_OWNER, 0 if state == "zero-id" else (identity ^ 1 if state == "different-id" else identity))
                env.put(outer + 0x6C, 0 if state == "null-child" else inner)
                env.put(inner + 0x1C, 16 if state == "wrong-kind" else 15)
                if flags is None:
                    env.put(t["this"] + 0x44C, 0)
                else:
                    effect = env.object(0x40, "effect", words=words_of(r, 0x10))
                    env.put(effect + 8, r.getrandbits(32) if flags == "random" else flags)
                    env.put(t["this"] + 0x44C, effect)
                    t["effect"] = effect
            yield case(f"release {state} effect {flags}", F_RELEASE, seed(), argc=0, w1=False, edit=release_edit)

    # ---------------------------------------------------------------- 0x44d9f0
    for kind in ("full", "empty", "shallow", "null-x", "null-home"):
        yield case(f"home trie {kind}", F_HOME, seed(), argc=0, w1=False, trie_kind=kind)
    for position, replacement in enumerate((b"XS_HOME", b"LX_HOME", b"LSXHOME", b"LS_XOME", b"LS_HXME", b"LS_HOXE", b"LS_HOMX",
                                            b"LS_HOMEX", b"LS_HOM", b"ls_home", b"LS_HOMF", b"LS_HOMD", b"MS_HOME", b"KS_HOME")):
        yield case(f"home key variant {position}", F_HOME, seed(), argc=0, w1=False, trie_bad={HOME: replacement})
    for _ in range(3):
        yield case("home random contents", F_HOME, seed(), argc=0, w1=False)

    # ---------------------------------------------------------------- 0x44f3c0
    fx_sets = (None, {0x414: True}, {0x41C: True}, {0x414: True, 0x41C: True})
    for index, fx in enumerate(fx_sets):
        for enable in (0, 1):
            for mode in (3, 0x80000003, 4):
                yield case(f"hitlow fx {index} enable {enable} mode {mode:#x}", F_HITLOW, seed(), argc=0, w1=False,
                           fx=fx, fx_enable=enable, mode=mode)
    for kind in ("empty", "shallow", "null-low", "null-x", "null-home", "null-high"):
        yield case(f"hitlow trie {kind}", F_HITLOW, seed(), argc=0, w1=False, trie_kind=kind)
    for bad in (b"LS_HITLOX", b"LS_HITLO", b"LS_HITLOWW", b"XS_HITLOW", b"ls_hitlow"):
        yield case(f"hitlow key {bad.decode()}", F_HITLOW, seed(), argc=0, w1=False, trie_bad={LOW: bad})
    yield case("hitlow no animation", F_HITLOW, seed(), argc=0, w1=False, anims=(False, True))
    yield case("hitlow only high animation", F_HITLOW, seed(), argc=0, w1=False, anims=(False, True), fx={0x414: True})
    yield case("hitlow locale on", F_HITLOW, seed(), argc=0, w1=False, locale=1)
    for count in (1, 2, 3):
        def anim_edit(env, t, r, count=count):
            env.put(t["this"] + 0x334, animation(env, r, count))
        yield case(f"hitlow animation of {count} frames", F_HITLOW, seed(), argc=0, w1=False, edit=anim_edit)

    # ---------------------------------------------------------------- 0x440e20
    jitters = RAND_PAIRS
    for index, (r1, r2) in enumerate(jitters):
        yield case(f"burst sentinel rands {index}", F_BURST, seed(), rands=[r1, r2],
                   edit=burst_edit(x=100.25, y=200.75))
    for x, y in ((0.0, 0.0), (0.9, -0.9), (-0.5, 0.5), (-1.5, -2.5), (123.99, 456.01), (-123.99, -456.01),
                 (2.5, 3.5), (1e6, -1e6), (-0.0, 0.1)):
        yield case(f"burst truncation {x} {y}", F_BURST, seed(), rands=[3, 6], edit=burst_edit(x=x, y=y))
    # Clamping: esi = (p13c + p144) / 2 + p50 against [lo + iy, hi + iy].
    clamp_cases = [
        ("inside", 10, 20, 7, 100, -50, 300), ("below", 10, 20, -400, 100, -50, 300), ("above", 10, 20, 900, 100, -50, 300),
        ("odd positive sum", 7, 8, 0, 0, -500, 500), ("odd negative sum", -7, -8, 0, 0, -500, 500),
        ("negative halves", -9, 2, 4, 0, -500, 500), ("at low", 0, 0, -50 + 10, 0, -50, 300),
        ("at high", 0, 0, 300 + 10, 0, -50, 300), ("inverted bounds below", 0, 0, 0, 0, 100, -100),
        ("inverted bounds above", 0, 0, 500, 0, 100, -100), ("large", 0x40000000, 0x3FFFFFFF, 3, 0, -9, 9),
        ("wraparound", 0x7FFFFFFF, 0x7FFFFFFF, 1, 0, -100, 100), ("zero span", 6, 6, 6, 0, 20, 20),
    ]
    for label, a, b, c, d, lo, hi in clamp_cases:
        for y in (10.9, -10.9):
            yield case(f"burst clamp {label} y {y}", F_BURST, seed(), rands=[2, 7],
                       edit=burst_edit(x=40.5, y=y, p138=0, p13c=a, p144=b, p50=c, lo=lo, hi=hi))
    for p138 in (0, 1, 0x7FFFFFFF, 0x80000001, M32):
        yield case(f"burst p138 {p138:#x}", F_BURST, seed(), rands=[1, 2],
                   edit=burst_edit(x=5.5, y=9.5, p138=p138, p13c=30, p144=50, p50=5, lo=-1000, hi=1000))
    yield case("burst sentinel with other words set", F_BURST, seed(), rands=[1, 2],
               edit=burst_edit(x=5.5, y=9.5, p13c=30, p144=50, p50=5, lo=-1000, hi=1000))
    for index in range(8):
        x, y = rs.uniform(-300, 700), rs.uniform(-300, 700)
        yield case(f"burst random {index}", F_BURST, seed(), rands=[rs.getrandbits(32), rs.getrandbits(32)],
                   edit=burst_edit(x=x, y=y, p138=rs.choice((0, 5, None)), p13c=rs.randrange(-400, 400),
                                   p144=rs.randrange(-400, 400), p50=rs.randrange(-300, 300), lo=rs.randrange(-300, 0),
                                   hi=rs.randrange(0, 300)))
    yield case("burst owner dead", F_BURST, seed(), rands=[3, 4], edit=burst_edit(x=1.5, y=2.5, dead=True))
    yield case("burst owner done", F_BURST, seed(), rands=[3, 4], edit=burst_edit(x=1.5, y=2.5, done=True))
    yield case("burst no HitBurst metadata", F_BURST, seed(), rands=[3, 4], omit=(N_BURST,), edit=burst_edit(x=1.5, y=2.5))
    yield case("burst no enemy hit frames", F_BURST, seed(), rands=[3, 4], omit=(N_ENEMY,), edit=burst_edit(x=1.5, y=2.5))
    yield case("burst without world", F_BURST, seed(), w1=False, rands=[3, 4], edit=burst_edit(x=1.5, y=2.5, dead=True))

    # ---------------------------------------------------------------- 0x44d760
    def aim(label, v, shooter, target, z, branch=None, slot=None):
        def edit(env, t, r):
            for offset, value in zip((0x38, 0x40, 0x48), v):
                dbl(env, t["this"] + offset, value)
            dbl(env, t["this"] + 0x68, shooter[0])
            dbl(env, t["this"] + 0x70, shooter[1])
            dbl(env, t["this"] + 0x78, z)
            inner = env.object(0x40, "target-inner", words=words_of(r, 0x10))
            env.put(inner + 0x2C, target[0] & M32, 0)
            env.put(inner + 0x34, target[1] & M32)
            env.put(t["P"] + 0x6C, inner)
            t["inner"] = inner
            if slot is not None:
                t["acts"][0x60] = lambda e, c: slot(e, c, t)
        return case(label, F_AIM, seed(), w1=False, edit=edit)

    # r = (target_x - shooter_x, target_y - shooter_y, -z) parallel to v: the speed term is zero.
    for k, v in ((2.0, (1.0, 2.0, 3.0)), (0.5, (-3.0, 1.0, 2.0)), (7.0, (0.25, -0.5, 0.125))):
        shooter = (100.0 - k * v[0], 50.0 - k * v[1])
        yield aim(f"aim parallel {k} {v}", v, shooter, (100, 50), -k * v[2])
    yield aim("aim target on shooter", (1.0, 2.0, 3.0), (100.0, 50.0), (100, 50), 0.0)
    yield aim("aim zero velocity", (0.0, 0.0, 0.0), (10.0, 20.0), (130, -40), 5.0)
    yield aim("aim negative z", (1.5, -2.5, 0.5), (-30.0, 22.0), (-100, 90), -17.0)
    # Distance around the 0.1 threshold: v = (1, 0, 0), r = (1000, b, 0), speed^2 = |r| - 1000.
    for b in (3.0, 4.0, 4.4, 4.5, 4.6, 5.0, 6.5):
        yield aim(f"aim threshold b {b}", (1.0, 0.0, 0.0), (0.0, -b), (1000, 0), 0.0)
    # Linear branch: |v|^2 / 4 within 0.1, i.e. |v|^2 <= 0.4.
    for index, v in enumerate(((0.3, -0.2, 0.1), (0.6, 0.0, 0.0), (0.0, 0.0, 0.62), (-0.1, 0.2, -0.3), (0.62, 0.0, 0.0),
                               (0.64, 0.0, 0.0), (1e-3, 2e-3, -3e-3))):
        yield aim(f"aim linear {index} {v}", v, (rs.uniform(-100, 100), rs.uniform(-100, 100)),
                  (rs.randrange(-500, 500), rs.randrange(-500, 500)), rs.uniform(-80, 80))
    for index in range(10):
        v = tuple(rs.uniform(-0.3, 0.3) for _ in range(3))
        yield aim(f"aim linear random {index}", v, (rs.uniform(-300, 300), rs.uniform(-300, 300)),
                  (rs.randrange(-600, 600), rs.randrange(-600, 600)), rs.uniform(-200, 200))
    # Quadratic branch.
    for index in range(22):
        v = tuple(rs.uniform(-9, 9) for _ in range(3))
        yield aim(f"aim quadratic random {index}", v, (rs.uniform(-300, 300), rs.uniform(-300, 300)),
                  (rs.randrange(-600, 600), rs.randrange(-600, 600)), rs.uniform(-200, 200))
    yield aim("aim quadratic unit", (1.0, 2.0, 3.0), (0.0, 0.0), (5, -1), -2.0)
    yield aim("aim quadratic negative velocity", (-4.0, -5.0, -6.0), (10.0, -10.0), (-20, 30), 8.0)

    def disturb(env, call, t):
        for offset in (0x38, 0x40, 0x48, 0x68, 0x70, 0x78):
            dbl(env, t["this"] + offset, 3.25 * (offset - 0x30))
        env.put(t["inner"] + 0x2C, 77)
        env.put(t["inner"] + 0x34, 99)
        env.put(t["this"] + 0x98, 0x11111111)
    yield aim("aim fields changed by the slot", (1.0, 2.0, 3.0), (3.0, 4.0), (500, 600), 7.0, slot=disturb)

    def zero_out(env, call, t):
        for offset in (0x38, 0x40, 0x48):
            dbl(env, t["this"] + offset, 0.0)
    yield aim("aim velocity cleared by the slot", (1.0, 2.0, 3.0), (3.0, 4.0), (500, 600), 7.0, slot=zero_out)

    def shrink(env, call, t):
        for offset in (0x38, 0x40, 0x48):
            dbl(env, t["this"] + offset, 0.25)
    yield aim("aim velocity shrunk by the slot", (5.0, 6.0, 7.0), (3.0, 4.0), (500, 600), 7.0, slot=shrink)

    # ---------------------------------------------------------------- 0x44d460
    names = (LOW, HIGH, b"LS_OTHER", b"LS_HITLOWX", b"LS_HITLO", b"ls_hitlow", b"LS_HITHIGHX", b"LS_HITHIG", b"", b"LS_HOME",
             b"LS_HITLOX", b"XS_HITHIGH")
    for name in names:
        for listcount in (0, 2):
            yield case(f"hit name {name.decode()} list {listcount}", F_HIT, seed(), name=name, listcount=listcount,
                       edit=edits(poke(p2={0x14: 0}), burst_edit(x=12.5, y=-33.5, p138=0, p13c=14, p144=9, p50=3,
                                                                  lo=-100, hi=250)))
    yield case("hit list of three", F_HIT, seed(), name=b"LS_PLAIN", listcount=3)
    yield case("hit list of one high", F_HIT, seed(), name=HIGH, listcount=1)
    yield case("hit locale on plain", F_HIT, seed(), name=b"LS_PLAIN", locale=1)
    yield case("hit locale on low", F_HIT, seed(), name=LOW, locale=1)
    every_fx = {0x418: True, 0x390: True, 0x394: True, 0x398: True, 0x39C: True}
    for rand3 in (0, 1, 2, 3, 4, 7, M32, M32 - 1, M32 - 2, M32 - 3, 0x80000000, 0x7FFFFFFF):
        yield case(f"hit high rand {rand3:#x}", F_HIT, seed(), name=b"LS_PLAIN", fx=every_fx,
                   rands=[1, 2, rand3, rand3], edit=poke(p2={0x14: 1}))
    for flag in (0, 0x80000000, 0x100, M32):
        yield case(f"hit plain flag {flag:#x}", F_HIT, seed(), name=b"LS_PLAIN", fx=every_fx,
                   rands=[1, 2, 0, 0], edit=poke(p2={0x14: flag}))
    for kind in (0, 1, 2, 3):
        only = {(0x390, 0x394, 0x398, 0x39C)[kind]: True}
        yield case(f"hit high only fx slot {kind}", F_HIT, seed(), name=b"LS_PLAIN", fx=only, rands=[5, 6, kind, 0],
                   edit=poke(p2={0x14: 1}))
        yield case(f"hit high no fx slot {kind}", F_HIT, seed(), name=b"LS_PLAIN", rands=[5, 6, kind, 0],
                   edit=poke(p2={0x14: 1}))
    for enable in (0, 1):
        yield case(f"hit high effects disabled {enable}", F_HIT, seed(), name=b"LS_PLAIN", fx_enable=enable,
                   fx={0x418: True, 0x390: True}, rands=[1, 2, 0, 0], edit=poke(p2={0x14: 1}))
        yield case(f"hit low effects disabled {enable}", F_HIT, seed(), name=b"LS_PLAIN", fx_enable=enable,
                   fx={0x414: True, 0x41C: True}, edit=poke(p2={0x14: 0}))
    yield case("hit slot changes hit words", F_HIT, seed(), name=b"LS_PLAIN",
               edit=edits(poke(p2={0x14: 0}), burst_edit(x=1.5, y=2.5, p138=0, p13c=2, p144=4, p50=6, lo=-9, hi=99),
                          act(0x28, lambda e, c, t: (e.put(t["P"] + 0x50, 400), e.put(t["P"] + 0x13C, 40)))))
    # The table grows when the key is outside it: 0x4db6e0 reports the grown record count through 0x5376b8, which the
    # loop in 0x44d460 reads. The new record's name word is then the constructed value 0x4f6439 stores.
    for where, k in (("above", 1), ("below", 1), ("below", 2), ("below", 3)):
        for flag in (0, 1):
            yield case(f"hit table grows {where} {k} chain {flag}", F_HIT, seed(), name=b"LS_PLAIN", rands=[1, 2, 3, 4],
                       edit=edits(poke(p2={0x14: flag}), grow_edit(where, k)))
    for second in (1, 2):
        for flag in (0, 1):
            yield case(f"hit table grows twice by {second} chain {flag}", F_HIT, seed(), name=b"LS_PLAIN", locale=1,
                       rands=[1, 2, 3, 4], edit=edits(poke(p2={0x14: flag}), grow_edit("below", 1, second)))
    yield case("hit time window recorded", F_HIT, seed(), name=b"LS_PLAIN", edit=poke(p2={0x14: 0}))
    yield case("hit trie without low", F_HIT, seed(), name=b"LS_PLAIN", trie_kind="null-low", edit=poke(p2={0x14: 0}))
    yield case("hit high trie without high", F_HIT, seed(), name=b"LS_PLAIN", trie_kind="null-high", edit=poke(p2={0x14: 1}))
    yield case("hit mode other", F_HIT, seed(), name=b"LS_PLAIN", mode=0, edit=poke(p2={0x14: 0}))
    yield case("hit mode other high", F_HIT, seed(), name=b"LS_PLAIN", mode=0, edit=poke(p2={0x14: 1}))

    # ---------------------------------------------------------------- 0x44d570, 0x44d700, 0x44d730
    for function, label in ((F_CONTACT, "contact"), (F_PLAIN, "plain"), (F_STUN, "stun")):
        for flags in (0, 0x10000, M32, 0xFFFEFFFF, 2):
            yield case(f"{label} hit flags {flags:#x}", function, seed(), edit=edits(
                burst_edit(x=9.5, y=-4.5, p138=0, p13c=20, p144=22, p50=1, lo=-200, hi=200), poke(P={8: flags})))
        for index, fx in enumerate(fx_sets):
            for mode in (3, 2):
                yield case(f"{label} fx {index} mode {mode}", function, seed(), fx=fx, mode=mode)
        yield case(f"{label} sentinel hit", function, seed())
        yield case(f"{label} owner dead", function, seed(), edit=burst_edit(x=1.5, y=2.5, dead=True))
        yield case(f"{label} slot rewrites hit", function, seed(), edit=edits(
            burst_edit(x=3.5, y=4.5, p138=0, p13c=6, p144=6, p50=6, lo=-300, hi=300),
            act(0x28, lambda e, c, t: (e.put(t["P"] + 0x138, SENTINEL), e.put(t["P"] + 8, 0x10000)))))
        yield case(f"{label} slot receives hit", function, seed(), edit=act(
            0x28, lambda e, c, t: dbl(e, t["this"] + 0x68, -77.75)))
        for kind in ("empty", "null-low"):
            yield case(f"{label} trie {kind}", function, seed(), trie_kind=kind)
        yield case(f"{label} without animations", function, seed(), anims=(False, False))
        yield case(f"{label} random 1", function, seed(), rands=[rs.getrandbits(32), rs.getrandbits(32)])
        yield case(f"{label} random 2", function, seed(), rands=[rs.getrandbits(32), rs.getrandbits(32)])

    # ---------------------------------------------------------------- 0x44d5a0
    for power in (0x26B8, 0x26B9, 0x26BA):
        for present_a in (True, False):
            for present_c in (True, False):
                omit = ()
                a_name = {0x26B8: N_FIRE, 0x26B9: N_LIGHT, 0x26BA: N_ICE}[power]
                c_name = {0x26B8: N_FIRE_X, 0x26B9: N_LIGHT_X, 0x26BA: N_ICE_X}[power]
                if not present_a:
                    omit += (a_name,)
                if not present_c:
                    omit += (c_name,)
                yield case(f"explode power {power:#x} sprites {int(present_a)} animation {int(present_c)}", F_EXPLODE, seed(),
                           w2=True, omit=omit, edit=edits(global_poke(**{"g534EAC": power}), poke(S={0x4C: 0x1234, 0x50: 0x4321, 0x64: 7})))
    for power in (0x26B7, 0x26BB, 0, M32, 0x26B8 ^ 0x100):
        yield case(f"explode power {power:#x} ignored", F_EXPLODE, seed(), w2=True, edit=global_poke(**{"g534EAC": power}))
    for power in (0x26B8, 0x26B9, 0x26BA, 0x26B7):
        def existing(env, t, r, power=power):
            env.put(G_POWER, power)
            effect = env.object(0x40, "old-effect", words=words_of(r, 0x10))
            env.put(t["this"] + 0x44C, effect)
        yield case(f"explode effect already present power {power:#x}", F_EXPLODE, seed(), w2=True, edit=existing)
    for index in range(6):
        power = (0x26B8, 0x26B9, 0x26BA)[index % 3]
        yield case(f"explode random {index}", F_EXPLODE, seed(), w2=True, fx=fx_sets[index % 4], mode=(3, 1)[index % 2],
                   rands=[rs.getrandbits(32), rs.getrandbits(32)],
                   edit=edits(global_poke(**{"g534EAC": power}),
                              poke(S={0x4C: rs.getrandbits(32), 0x50: rs.getrandbits(32), 0x64: rs.getrandbits(32)})))
    yield case("explode hit descriptor ordering", F_EXPLODE, seed(), w2=True, edit=edits(
        global_poke(**{"g534EAC": 0x26B8}), burst_edit(x=2.5, y=3.5, p138=0, p13c=3, p144=5, p50=7, lo=-50, hi=50),
        act(0x28, lambda e, c, t: e.put(t["P"] + 0x50, 77))))
    yield case("explode owner dead", F_EXPLODE, seed(), w2=True, edit=edits(
        global_poke(**{"g534EAC": 0x26B9}), burst_edit(x=2.5, y=3.5, dead=True)))
    yield case("explode inverted frame range", F_EXPLODE, seed(), w2=True, edit=global_poke(**{"g534EAC": 0x26BA}))

    # ---------------------------------------------------------------- 0x44df60
    def death_case(label, flags, fire, ice, null, **extra):
        entries = {}
        if fire is not None:
            entries[D_FIRE] = fire
        if ice is not None:
            entries[D_ICE] = ice
        if null is not None:
            entries[D_NULL] = null
        return case(label, F_DEATH, seed(), argc=0, w1=False, death=entries, edit=poke(Pl={0x164: flags}), **extra)

    values = (None, 0, 0x5151)
    for flags in (0x40000, 0x80000, 0x100000, 0x40000 | 0x80000, 0x80000 | 0x100000, 0x40000 | 0x100000, 0x1C0000):
        for fire in values:
            for ice in values:
                if flags not in (0x80000, 0x80000 | 0x100000) and ice is not None:
                    continue
                for null in (None, 0, 0x7777):
                    if flags in (0x80000,) and fire is not None:
                        continue
                    yield death_case(f"death flags {flags:#x} fire {fire} ice {ice} null {null}", flags, fire, ice, null)
    for flags in (0, 0x20000, 0x7FFFF, 0xFE00000, M32 & ~0x1C0000):
        yield death_case(f"death flags {flags:#x} none", flags, 0x11, 0x22, 0x33)
    yield death_case("death poll runs after lookup", 0x40000, 0x91, None, 0x92,)
    yield death_case("death only null hit", 0x40000, None, None, 0x93)
    yield death_case("death slot sees stored value", 0x100000, 0x94, 0x95, 0x96)
