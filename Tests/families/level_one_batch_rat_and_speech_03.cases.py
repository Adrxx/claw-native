"""Cases for level_one_batch_rat_and_speech_03: Level 1 enemy speech and Wolvington helper, batch 3.

0x48ce40 and 0x48ceb0 are cdecl speech requests (owner, value-or-name, force) that read the globals 0x53c9ac (queue),
0x53c9a8 (busy flag) and 0x5371fc (chain to the name registry) and write 0x53c9b0. 0x4a1180 is a thiscall method of an
enemy actor. Every branch is reached by an explicit loop; the random source only varies the contents.
"""
from clawparity.cases import Case

M32 = 0xFFFFFFFF
SENTINEL = 0x80000000
F_VALUE, F_NAME, F_ADVANCE = 0x48CE40, 0x48CEB0, 0x4A1180
G_Q, G_BUSY, G_OWNER, G_ENV = 0x53C9AC, 0x53C9A8, 0x53C9B0, 0x5371FC
G_TRIE = 0x537668          # the table behind 0x4dba00, searched for LS_ADVANCE
ADVANCE_NAME = 0x527D94

NAME = b"LEVEL_RAT_SPEECH_0034"


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


def services(env, r, kind, name=NAME, value=None, buckets=3, busy=None, owner_old=None):
    """Globals for the requests. kind: ok, no-q, no-r. busy None keeps the flag clear. Returns tokens."""
    q = env.object(0x190, "service-q", words=words_of(r, 0x64))
    record = env.object(0x40, "service-r", words=words_of(r, 0x10))
    env.put(q + 0x6C, 0 if kind == "no-r" else record)
    env.put(G_Q, 0 if kind == "no-q" else q)
    env.put(G_BUSY, 0 if busy is None else busy)
    env.put(G_OWNER, r.randrange(1, 1 << 32) if owner_old is None else owner_old)
    value = r.randrange(1, 1 << 32) if value is None else value
    entries = {b"LEVEL_RAT": r.randrange(1, 1 << 32), b"LEVEL_RAT_SPEECH_003": r.randrange(1, 1 << 32),
               b"LEVEL_RAT_SPEECH_0035": r.randrange(1, 1 << 32)}
    if name is not None:
        entries[name] = value
    reg = registry(env, r, entries, buckets)
    x = env.object(0x40, "env-x", words=words_of(r, 0x10))
    y = env.object(0x40, "env-y", words=words_of(r, 0x10))
    env.put(G_ENV, x)
    env.put(x + 0x30, y)
    env.put(y + 0x28, reg)
    return {"q": q, "record": record, "value": value}


def request_cases(r):
    # 0x48ce40: value request
    arg_sets = [(p1, p2, p3) for p1 in (0, 1) for p2 in (0, 1) for p3 in (0, 1)]
    for kind in ("ok", "no-q", "no-r"):
        for busy in (0, 1):
            for p1, p2, p3 in arg_sets:
                def setup(env, kind=kind, busy=busy, p1=p1, p2=p2, p3=p3):
                    tokens = services(env, r, kind, busy=r.randrange(1, 1 << 32) if busy else 0)
                    tokens["p1"] = r.randrange(1, 1 << 32) if p1 else 0
                    tokens["p2"] = r.randrange(1, 1 << 32) if p2 else 0
                    tokens["p3"] = r.randrange(1, 1 << 32) if p3 else 0
                    return tokens
                yield Case(f"value q={kind} busy={busy} args={p1}{p2}{p3}", F_VALUE, setup,
                           arguments=(lambda t: t["p1"], lambda t: t["p2"], lambda t: t["p3"]))
    for p2 in (1, 0x7FFFFFFF, 0x80000000, M32):
        def setup(env, p2=p2):
            tokens = services(env, r, "ok", busy=7)
            tokens["p2"] = p2
            return tokens
        yield Case(f"value stored verbatim {p2:#x}", F_VALUE, setup,
                   arguments=(lambda t: 0xCAFE0001, lambda t: t["p2"], lambda t: M32))

    # 0x48ceb0: name request
    for kind in ("ok", "no-q", "no-r"):
        for busy in (0, 1):
            for p1 in (0, 1):
                for has_name in (0, 1):
                    for p3 in (0, 1):
                        def setup(env, kind=kind, busy=busy, p1=p1, has_name=has_name, p3=p3):
                            tokens = services(env, r, kind, busy=r.randrange(1, 1 << 32) if busy else 0)
                            tokens["p1"] = r.randrange(1, 1 << 32) if p1 else 0
                            tokens["name"] = env.object(len(NAME) + 4, "name", data=NAME + b"\0") if has_name else 0
                            tokens["p3"] = r.randrange(1, 1 << 32) if p3 else 0
                            return tokens
                        yield Case(f"name q={kind} busy={busy} p1={p1} name={has_name} p3={p3}", F_NAME, setup,
                                   arguments=(lambda t: t["p1"], lambda t: t["name"], lambda t: t["p3"]))
    for buckets in (1, 2, 3, 5, 7, 16):
        for name in (NAME, b"LEVEL_RAT_SPEECH_0035", b"LEVEL_RAT", b"A", b"\xe9\xff_high_bytes"):
            def setup(env, buckets=buckets, name=name):
                tokens = services(env, r, "ok", name=name, buckets=buckets)
                tokens["name"] = env.object(len(name) + 4, "name", data=name + b"\0")
                return tokens
            yield Case(f"name hit buckets={buckets} {name[:12]!r}", F_NAME, setup,
                       arguments=(lambda t: 0xBEEF0002, lambda t: t["name"], lambda t: 0))
    for lookup in (b"MISSING", b"LEVEL_RAT_SPEECH_003X", b"LEVEL_RAT_SPEECH_00", b"level_rat", b"X"):
        for buckets in (1, 4):
            def setup(env, lookup=lookup, buckets=buckets):
                tokens = services(env, r, "ok", name=None, buckets=buckets)
                tokens["name"] = env.object(len(lookup) + 4, "name", data=lookup + b"\0")
                return tokens
            yield Case(f"name miss {lookup!r} buckets={buckets}", F_NAME, setup,
                       arguments=(lambda t: 0xBEEF0003, lambda t: t["name"], lambda t: 0))
    for value in (0, 1, 0x80000000, M32):
        def setup(env, value=value):
            tokens = services(env, r, "ok", value=value)
            tokens["name"] = env.object(len(NAME) + 4, "name", data=NAME + b"\0")
            return tokens
        yield Case(f"name value {value:#x}", F_NAME, setup,
                   arguments=(lambda t: 0xBEEF0004, lambda t: t["name"], lambda t: 5))
    for _ in range(40):
        name = bytes(r.randrange(0x41, 0x5B) for _ in range(r.randrange(1, 24)))
        present = r.random() < 0.7
        owner = 0x10000000 | r.getrandbits(24)

        def setup(env, name=name, present=present, busy=r.random() < 0.5, p3=r.getrandbits(32) & r.getrandbits(32),
                  buckets=r.randrange(1, 12)):
            tokens = services(env, r, "ok", name=name if present else None, buckets=buckets,
                              busy=r.randrange(1, 1 << 32) if busy else 0)
            tokens["name"] = env.object(len(name) + 4, "name", data=name + b"\0")
            tokens["p3"] = p3
            return tokens
        yield Case(f"name random {name!r}", F_NAME, setup,
                   arguments=(lambda t, owner=owner: owner, lambda t: t["name"], lambda t: t["p3"]))


# ---------------------------------------------------------------------------------------------- 0x4a1180

def key_bit(name, bit):
    return (name[bit >> 3] >> (bit & 7)) & 1


def trie(env, r, kind):
    """Writes the root of the 0x4dba00 table at G_TRIE+0x18. Nodes: [child0, child1, bit, key, value]. Returns value."""
    key = env.cstr(ADVANCE_NAME)
    good = env.object(len(key) + 4, "key-good", data=key + b"\0")
    value = r.randrange(1, 1 << 32)

    def node(bit, keyptr, c0=0, c1=0, val=None):
        return env.object(0x14, "trie-node", words=[c0, c1, bit, keyptr, value if val is None else val])

    def mutated(position, delta):
        data = bytearray(key + b"\0")
        data[position] = (data[position] + delta) & 0xFF
        return env.object(len(data) + 2, "key-bad", data=bytes(data))

    root = 0
    if kind == "empty":
        root = 0
    elif kind == "bit-too-large":
        root = node(100, good)
    elif kind.startswith("self-"):
        bit = int(kind[5:])
        n = node(bit, good)
        env.put(n, n, n)
        root = n
    elif kind.startswith("null-"):
        bit = int(kind[5:])
        n = node(bit, good)
        env.put(n + 4 * key_bit(key, bit), 0)
        env.put(n + 4 * (1 - key_bit(key, bit)), n)
        root = n
    elif kind.startswith("two-"):  # root with one descent step, leaf matches
        b1, b2 = [int(x) for x in kind[4:].split("-")]
        leaf = node(b2, good)
        env.put(leaf, leaf, leaf)
        top = node(b1, mutated(0, 1))
        c = key_bit(key, b1)
        env.put(top + 4 * c, leaf)
        env.put(top + 4 * (1 - c), top)
        root = top
    elif kind.startswith("decoy-"):  # root back-edge reaches a node whose key differs at the given byte
        position = int(kind[6:])
        n = node(5, mutated(position, 1))
        env.put(n, n, n)
        root = n
    elif kind == "short-key":
        n = node(5, env.object(8, "short", data=key[:4] + b"\0"))
        env.put(n, n, n)
        root = n
    elif kind == "long-key":
        n = node(5, env.object(24, "long", data=key + b"XY\0"))
        env.put(n, n, n)
        root = n
    elif kind == "zero-value":
        n = node(5, good, val=0)
        env.put(n, n, n)
        root = n
        value = 0
    env.put(G_TRIE + 0x18, root)
    return value


TRIES = (["empty", "bit-too-large", "short-key", "long-key", "zero-value"]
         + [f"self-{b}" for b in (0, 1, 2, 7, 8, 40, 79, 87)]
         + [f"null-{b}" for b in (1, 6, 33)]
         + [f"two-{a}-{b}" for a, b in ((0, 1), (3, 4), (2, 70), (10, 11), (30, 60))]
         + [f"decoy-{p}" for p in (0, 1, 2, 5, 9)])


def actor(env, r, *, mode, flag2, sent, trie_kind="self-5", tail="ptr", value400=None):
    obj = env.object(0x420, "actor", words=words_of(r, 0x108))
    sub = env.object(0x200, "sub", words=words_of(r, 0x80))
    flags = (r.getrandbits(32) & ~2) | (2 if flag2 else 0)
    env.put(sub + 0x40, flags)
    for flag, offset in zip(sent, (0x118, 0x128, 0x138)):
        if flag:
            env.put(sub + offset, SENTINEL)
    # values the mirror swaps must be distinct and small enough to tell apart
    inner = env.object(0x40, "inner", words=words_of(r, 0x10))
    env.put(obj + 0x10, inner)
    env.put(obj + 0x12C, sub)
    env.put(obj + 0x18C, mode)
    env.put(obj + 0x400, r.randrange(1, 1 << 32) if value400 is None else value400)
    if tail == "null":
        env.put(obj + 0x308, 0)
    else:
        element = env.object(0x40, "element", words=words_of(r, 0x10))
        table = env.object(16, "element-table", words=[element, r.getrandbits(32), r.getrandbits(32), r.getrandbits(32)])
        param = env.object(0x40, "frames", words=words_of(r, 0x10))
        env.put(param + 0xC, table)
        env.put(param + 0x10, r.randrange(1, 5) if tail == "ptr" else 1)
        env.put(obj + 0x308, param)
    trie(env, r, trie_kind)
    return {"obj": obj, "sub": sub}


def advance_cases(r):
    values = (None, 0, 1, 0x7FFFFFFF, 0x80000000, M32, 0x12345678)
    n = 0
    for mode in (2, 3, 0, 1, 5, 0x7FFFFFFF, M32):
        for flag2 in (0, 1):
            for sent in [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]:
                v = values[n % len(values)]
                kind = TRIES[n % len(TRIES)]
                n += 1
                yield Case(f"advance mode={mode:#x} flag2={flag2} sentinels={sent} trie={kind}", F_ADVANCE,
                           lambda env, mode=mode, flag2=flag2, sent=sent, v=v, kind=kind:
                           actor(env, r, mode=mode, flag2=flag2, sent=sent, trie_kind=kind, value400=v),
                           receiver=lambda t: t["obj"])
    for kind in TRIES:
        for tail in ("ptr", "null"):
            yield Case(f"advance trie={kind} tail={tail}", F_ADVANCE,
                       lambda env, kind=kind, tail=tail: actor(env, r, mode=3, flag2=0, sent=(0, 0, 0),
                                                              trie_kind=kind, tail=tail, value400=0x80000000),
                       receiver=lambda t: t["obj"])
    for value in (0, 1, 0x7FFFFFFF, 0x80000000, M32, 0xFFFFFFFE):
        for mode in (2, 3, 4):
            yield Case(f"advance value400={value:#x} mode={mode}", F_ADVANCE,
                       lambda env, value=value, mode=mode: actor(env, r, mode=mode, flag2=1, sent=(1, 0, 1),
                                                                 value400=value),
                       receiver=lambda t: t["obj"])
    for _ in range(40):
        yield Case("advance random", F_ADVANCE,
                   lambda env, mode=r.choice((2, 3, 2, 3, 0, 9)), flag2=r.getrandbits(1),
                   sent=tuple(r.getrandbits(1) for _ in range(3)), kind=r.choice(TRIES),
                   tail=r.choice(("ptr", "null")): actor(env, r, mode=mode, flag2=flag2, sent=sent,
                                                          trie_kind=kind, tail=tail),
                   receiver=lambda t: t["obj"])


def cases(random_source):
    yield from request_cases(random_source)
    yield from advance_cases(random_source)
