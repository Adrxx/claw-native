"""Cases for level_one_batch_soldier_01: Level 1 Soldier state and destructor callbacks, batch 1.

Every function is a thiscall method of one enemy actor. Each case builds an actor of distinct random words, the
sub-object at +0x12c, the animation-state registry the sub-object reaches, the trie behind 0x537668 and the globals the
original callees read. Coverage comes from the explicit loops, never from the random draws; random_source only
supplies the data and a few extra mixed cases.
"""
import random

from clawparity.cases import Case

M32 = 0xFFFFFFFF
SENTINEL = 0x80000000

F_TICK, F_UPDATE, F_DELETING, F_DTOR = 0x48B670, 0x48B880, 0x48AFD0, 0x48AFF0
F_SET_1AC, F_DEC_10C = 0x404E00, 0x404E10
F_43F500, F_43FCB0, F_43FD60, F_43FE00 = 0x43F500, 0x43FCB0, 0x43FD60, 0x43FE00

DELETE, FREE, STRING_RELEASE = 0x4F6428, 0x4A49B0, 0x4F6584

G_TRIE = 0x537668          # the trie object 0x4dba00 searches; root at +0x18
G_MODE = 0x537964          # compared with 2
G_PLAYER = 0x537E88        # pointer; +0xcc compared with 5
G_CLOCK = 0x537210

KEY_TRIE_UPDATE = 0x524548
KEY_A1, KEY_2, KEY_B1 = 0x52C488, 0x5234B4, 0x52C408   # registry keys of 0x48b880
KEY_43F500, KEY_43FCB0, KEY_43FD60, KEY_43FE00 = 0x5271C0, 0x5271F4, 0x5271E4, 0x527218

ACTOR_SIZE = 0x4A0


def words_of(r, count):
    return [r.randrange(1, 1 << 32) for _ in range(count)]


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def registry(env, r, entries, buckets):
    """A string table as 0x4f6286 reads it, at owner+0x10. Nodes: [next, 0, key, value], plus decoys with near keys."""
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


def state_struct(env, r):
    """An animation state as 0x4c8220 reads it: +0x10 count > 0, +0xc table of pointers to frames with a word at +0x1c."""
    frame = env.object(0x40, "frame", words=words_of(r, 0x10))
    table = env.object(8, "frame-table", words=[frame, r.randrange(1, 1 << 32)])
    state = env.object(0x20, "anim-state", words=words_of(r, 8))
    env.put(state + 0xC, table)
    env.put(state + 0x10, r.randrange(1, 60))
    return state


def trie(env, r, mode, key):
    """The trie root at 0x537680 for one lookup of `key` by 0x4dba00. Returns the value a hit yields."""
    value = r.randrange(1, 1 << 32)
    # the trie's scratch fields hold distinct words so a missing or extra store shows
    env.put(G_TRIE + 0x1C, *words_of(r, 4))
    if mode == "empty":
        env.put(G_TRIE + 0x18, 0)
        return 0
    stored = key if mode in ("hit", "deep") else key[:-1] + bytes([key[-1] ^ 0x20])
    text = env.object(len(stored) + 4, "trie-key", data=stored + b"\0")
    bit = 0x1000 if mode == "deep" else 0
    node = env.object(0x14, "trie-node", words=[0, 0, bit, text, value])
    env.put(node, node, node)
    env.put(G_TRIE + 0x18, node)
    return value if mode == "hit" else 0


# ---------------------------------------------------------------------------------------------- the actor

def make_actor(env, r, *, mode=2, flag2=False, sent=(0, 0, 0), arg_offset=None, arg_state=False, entries=None,
               buckets=3):
    """Actor with obj10 at +0x10, sub-object at +0x12c, registry reached through sub+0xc -> +0x2c."""
    actor = env.object(ACTOR_SIZE, "actor", words=words_of(r, ACTOR_SIZE // 4))
    obj10 = env.object(0x40, "actor-10", words=words_of(r, 0x10))
    sub = env.object(0x200, "sub", words=words_of(r, 0x80))
    flags = (r.getrandbits(32) & ~2) | (2 if flag2 else 0)
    env.put(sub + 0x40, flags & M32)
    for flag, offset in zip(sent, (0x118, 0x128, 0x138)):
        if flag:
            env.put(sub + offset, SENTINEL)
    holder = env.object(0x40, "sub-holder", words=words_of(r, 0x10))
    owner = registry(env, r, entries or {}, buckets)
    env.put(holder + 0x2C, owner)
    env.put(sub + 0x0C, holder)
    env.put(actor + 0x10, obj10)
    env.put(actor + 0x12C, sub)
    env.put(actor + 0x18C, mode & M32)
    if arg_offset is not None:
        env.put(actor + arg_offset, state_struct(env, r) if arg_state else 0)
    return actor, sub


def update_setup(seed, *, mode=2, flag2=False, sent=(0, 0, 0), g_mode=2, cc=5, present=(1, 1, 1), trie_mode="hit",
                 now=None, last=None, interval=None):
    def setup(env):
        r = random.Random(seed)
        entries = {}
        for address, there in zip((KEY_A1, KEY_2, KEY_B1), present):
            if there:
                entries[env.cstr(address)] = state_struct(env, r)
        actor, sub = make_actor(env, r, mode=mode, flag2=flag2, sent=sent, entries=entries,
                                buckets=r.choice((1, 3, 5, 7)))
        player = env.object(0x100, "player", words=words_of(r, 0x40))
        env.put(player + 0xCC, cc & M32)
        env.put(G_PLAYER, player)
        env.put(G_MODE, g_mode & M32)
        trie(env, r, trie_mode, env.cstr(KEY_TRIE_UPDATE))
        env.put(G_CLOCK, r.randrange(1, 1 << 32) if now is None else now)
        if last is not None:
            env.put(actor + 0x46C, last, interval)
        return {"actor": actor, "sub": sub}
    return setup


def update(label, seed, **options):
    return Case(label, F_UPDATE, update_setup(seed, **options), receiver=lambda t: t["actor"])


# ---------------------------------------------------------------------------------------------- destructor

def dtor_setup(seed, *, capacity=33, registry_mode="empty"):
    def setup(env):
        r = random.Random(seed)
        actor = env.object(ACTOR_SIZE, "actor", words=words_of(r, ACTOR_SIZE // 4))
        log = env.object(0x2000, "surviving-observations", fill=0)
        nested = actor + 0x2F4
        registry_object = env.object(12, "registry", words=words_of(r, 3))
        buffer = env.object(48, "capacity-buffer", fill=0xAC)
        env.put(nested + 4, registry_object, capacity, buffer)
        env.put(0x544D18, 0)
        if registry_mode != "empty":
            identities = [nested - 8, nested, nested + 8]
            if registry_mode == "miss":
                identities = [nested - 8, nested + 4, nested + 8]
            env.put(0x544D18, 3)
            for i, identity in enumerate(identities):
                env.put(0x544B98 + i * 12, identity, *words_of(r, 2))

        def observe(env, kind, receiver, arguments):
            index = env.get(log)
            at = log + 4 + index * (ACTOR_SIZE + 24)
            env.put(at, kind, receiver, len(arguments), *(tuple(arguments) + (0, 0))[:2])
            env.write(at + 24, env.read(actor, ACTOR_SIZE))
            env.put(log, index + 1)

        results = words_of(r, 3)

        def string_release(env, call):
            observe(env, 0x5701, call.receiver, call.arguments)
            return results[0]

        def free(env, call):
            observe(env, 0xF4EE, call.receiver, call.arguments)
            if call.arguments[0]:
                env.release(call.arguments[0])
            return results[1]

        def delete(env, call):
            observe(env, 0xDE1E, call.receiver, call.arguments)
            if call.arguments[0]:
                env.release(call.arguments[0])
            return results[2]

        env.override(STRING_RELEASE, string_release)
        env.override(FREE, free)
        env.override(DELETE, delete)
        return {"actor": actor}
    return setup


# ---------------------------------------------------------------------------------------------- simple setters

def plain_setup(seed, *, key=None, trie_mode="hit", arg_offset=None, arg_state=False, clock=None, dword_10c=None):
    def setup(env):
        r = random.Random(seed)
        actor, sub = make_actor(env, r, arg_offset=arg_offset, arg_state=arg_state)
        if key is not None:
            trie(env, r, trie_mode, env.cstr(key))
        env.put(G_CLOCK, r.randrange(1, 1 << 32) if clock is None else clock)
        if dword_10c is not None:
            env.put(sub + 0x10C, dword_10c)
            env.put(actor + 0x0C, sub)
        return {"actor": actor, "sub": sub}
    return setup


def cases(random_source):
    seed = lambda: random_source.getrandbits(32)  # noqa: E731

    # ---- 0x48b880: every combination of the actor mode, the sub-object flag and the three sentinel pairs
    for mode in (2, 1):
        for flag2 in (False, True):
            for sent in [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]:
                yield update(f"update mode {mode} flag2 {flag2} sentinels {sent}", seed(), mode=mode, flag2=flag2,
                             sent=sent)
    for mode in (0, 3, 0x80000002, M32):
        for flag2 in (False, True):
            yield update(f"update other mode {mode:#x} flag2 {flag2}", seed(), mode=mode, flag2=flag2,
                         sent=(1, 0, 1) if flag2 else (0, 1, 0))

    # ---- both globals, with every subset of the three registry keys present
    for g_mode, cc in ((2, 5), (2, 4), (0, 5), (3, 5), (0, 0), (0x80000002, 5), (2, 0x80000005), (1, 6)):
        for mask in range(8):
            present = tuple((mask >> i) & 1 for i in range(3))
            yield update(f"update globals {g_mode:#x}/{cc:#x} keys {present}", seed(), g_mode=g_mode, cc=cc,
                         present=present, mode=2 if mask & 1 else 0, flag2=bool(mask & 2),
                         sent=(mask & 1, (mask >> 1) & 1, (mask >> 2) & 1))

    # ---- the trie lookup: hit, empty, wrong key, node beyond the key
    for trie_mode in ("hit", "empty", "mismatch", "deep"):
        for g_mode in (2, 0):
            yield update(f"update trie {trie_mode} globals {g_mode}", seed(), trie_mode=trie_mode, g_mode=g_mode,
                         mode=2 if g_mode else 1)

    # ---- a few mixed draws
    for _ in range(20):
        r = random.Random(seed())
        yield update("update mixed", r.getrandbits(32), mode=r.choice((2, 2, 0, 1, M32)),
                     flag2=r.random() < 0.5, sent=tuple(r.getrandbits(1) for _ in range(3)),
                     g_mode=r.choice((2, 2, 0, 3)), cc=r.choice((5, 5, 0, 4)),
                     present=tuple(r.getrandbits(1) for _ in range(3)),
                     trie_mode=r.choice(("hit", "empty", "mismatch", "deep")))

    # ---- 0x48b670: the unsigned interval test
    stamps = [
        (1000, 400, 500), (1000, 500, 500), (1000, 501, 500), (1000, 1000, 0), (0, 5, 500), (5, 5, 1),
        (100, 0, M32), (0, 1, M32), (0x80000000, 0, 0x7FFFFFFF), (0x7FFFFFFF, M32, 0x80000000),
        (0x80000000, 1, 0x7FFFFFFF), (0x80000001, 1, 0x80000001), (7, 7, 0), (0, 0, 1), (M32, 0, M32),
        (M32, 0, 0xFFFFFFFE), (0, M32, 1), (0, M32, 2),
    ]
    for i, (now, last, interval) in enumerate(stamps):
        mode, flag2 = [(2, False), (2, True), (1, True), (1, False)][i % 4]
        yield Case(f"tick now {now:#x} last {last:#x} interval {interval:#x}", F_TICK,
                   update_setup(seed(), mode=mode, flag2=flag2, sent=(i & 1, (i >> 1) & 1, (i >> 2) & 1),
                                now=now, last=last, interval=interval),
                   receiver=lambda t: t["actor"])
    for _ in range(12):
        r = random.Random(seed())
        now, last, interval = r.getrandbits(32), r.getrandbits(32), r.getrandbits(32)
        yield Case("tick random", F_TICK,
                   update_setup(r.getrandbits(32), now=now, last=last, interval=interval,
                                mode=r.choice((2, 1)), flag2=r.random() < 0.5),
                   receiver=lambda t: t["actor"])
        small = r.randrange(1, 1000)
        yield Case("tick random near", F_TICK,
                   update_setup(r.getrandbits(32), now=(last + small) & M32, last=last, interval=small + r.choice((-1, 0, 1))),
                   receiver=lambda t: t["actor"])

    # ---- 0x48aff0 and 0x48afd0: destructors, with capacity either side of 0x20 and the three registry states
    capacities = (0, 1, 31, 32, 33, 0x7FFFFFFF, 0x80000000, M32)
    for capacity in capacities:
        for registry_mode in ("empty", "found", "miss"):
            yield Case(f"destructor capacity {capacity:#x} registry {registry_mode}", F_DTOR,
                       dtor_setup(seed(), capacity=capacity, registry_mode=registry_mode),
                       receiver=lambda t: t["actor"])
    flag_values = (0, 1, 2, 3, 0x100, 0x101, 0xFFFFFFFE, M32, 0x80000000, 0x80000001)
    for flags in flag_values:
        for capacity, registry_mode in ((33, "found"), (5, "empty"), (0x20, "miss")):
            yield Case(f"deleting destructor flags {flags:#x} capacity {capacity:#x} registry {registry_mode}",
                       F_DELETING, dtor_setup(seed(), capacity=capacity, registry_mode=registry_mode),
                       receiver=lambda t: t["actor"], arguments=(flags,))

    # ---- 0x404e00 and 0x404e10
    for value in (0, 1, M32, 0x80000000, 0x7FFFFFFF) + tuple(random_source.getrandbits(32) for _ in range(8)):
        yield Case(f"store +0x1ac {value:#x}", F_SET_1AC, plain_setup(seed()), receiver=lambda t: t["actor"],
                   arguments=(value,))
    for value in (0, 1, 3, 4, 5, 0x10, 0x7FFFFFFF, 0x80000000, 0x80000003, M32) + \
            tuple(random_source.getrandbits(32) for _ in range(8)):
        yield Case(f"decrement +0x10c by four from {value:#x}", F_DEC_10C, plain_setup(seed(), dword_10c=value),
                   receiver=lambda t: t["actor"])

    # ---- 0x43f500, 0x43fcb0, 0x43fd60, 0x43fe00
    args = (0, 1, 2, 0x7FFFFFFF, 0x80000000, 0x80000001, M32, 0xFFFFFF00, 12345, 0xDEADBEEF) + \
        tuple(random_source.getrandbits(32) for _ in range(6))
    for trie_mode in ("hit", "empty", "mismatch", "deep"):
        for value in args if trie_mode == "hit" else args[:3] + args[4:5]:
            yield Case(f"0x43f500 trie {trie_mode} argument {value:#x}", F_43F500,
                       plain_setup(seed(), key=KEY_43F500, trie_mode=trie_mode),
                       receiver=lambda t: t["actor"], arguments=(value,))
    for function, key, offset in ((F_43FCB0, KEY_43FCB0, 0x354), (F_43FD60, KEY_43FD60, 0x354),
                                  (F_43FE00, KEY_43FE00, 0x314)):
        for trie_mode in ("hit", "empty", "mismatch", "deep"):
            for arg_state in (False, True):
                if function == F_43FE00:
                    yield Case(f"{function:#x} trie {trie_mode} state {arg_state}", function,
                               plain_setup(seed(), key=key, trie_mode=trie_mode, arg_offset=offset,
                                           arg_state=arg_state),
                               receiver=lambda t: t["actor"])
                    continue
                for value in (args if trie_mode == "hit" and arg_state else args[:2] + args[4:5]):
                    yield Case(f"{function:#x} trie {trie_mode} state {arg_state} argument {value:#x}", function,
                               plain_setup(seed(), key=key, trie_mode=trie_mode, arg_offset=offset,
                                           arg_state=arg_state),
                               receiver=lambda t: t["actor"], arguments=(value,))
