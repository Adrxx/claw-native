"""Independent original-backed resource namespace cases."""
from clawparity.cases import Case


def string(env, value, name="string"):
    # Prefix backing is intentional: the original resource scanner reads s[-1]
    # for the empty path. Suffix bytes also distinguish accidental wide reads.
    return env.object(len(value) + 10, name, data=b"|" + value + b"\0\xa7\xb9\xc3\xd5\xe7\xf1\x93\x85") + 1


def node(env, value, table=0, bucket=0, following=0):
    p = env.object(32, "node", fill=0x91)
    env.put(p + 4, following + 4 if following else 0)
    env.put(p + 12, table, bucket, value)
    return p


def table(env, count, entries=()):
    t = env.object(8, "table")
    buckets = env.object(max(1, count) * 16, "buckets", fill=0x63)
    env.put(t, count, buckets)
    for i in range(max(1, count)):
        env.put(buckets + 16 * i + 8, 0)
    for index, values in entries:
        following = 0
        for value in reversed(values):
            following = node(env, value, t, index, following)
        env.put(buckets + 16 * index + 8, following + 4 if following else 0)
    return t


def embed(env, owner, offset, t):
    env.put(owner + offset, env.get(t), env.get(t + 4))


def named(env, name, size=84):
    p = env.object(size, "named payload", fill=0x37)
    env.put(p, string(env, name, "payload name"))
    return p


def namespace(env, names=(), resources=(), type_id=17):
    p = env.object(84, "namespace", fill=0x49)
    grouped = {}
    for name, child in names:
        grouped.setdefault(len(name) % 5, []).append(child)
    embed(env, p, 0x3c, table(env, 5, grouped.items()))
    ty = env.object(64, "resource type", fill=0x57)
    env.put(ty, type_id)
    grouped = {}
    for name, resource in resources:
        grouped.setdefault(len(name) % 19, []).append(resource)
    embed(env, ty, 0x24, table(env, 19, grouped.items()))
    embed(env, p, 0x44, table(env, 9, [(type_id % 9, [ty])]))
    return p


def base(env):
    env.put(0x540e88, 0)


def cases(random_source):
    for function in (0x4b7f50, 0x4b8140):
        yield Case("null string hash", function, arguments=(0,))
        for length in (0, 1, 4, 5, 18, 19, 20, 38, 255, random_source.randrange(40, 180)):
            value = bytes(random_source.randrange(1, 256) for _ in range(length))
            def setup(env, value=value):
                base(env)
                return {"s": string(env, value)}
            yield Case(f"hash length {length}", function, setup, arguments=(lambda t: t["s"],))
    for function in (0x4b8060, 0x4b80d0):
        for value in (0, 1, 8, 9, 18, 19, 20, 0x7fffffff, 0x80000000, 0xffffffff, random_source.getrandbits(32)):
            yield Case(f"unsigned modulus {value:#x}", function, arguments=(value,))

    # Exact comparisons distinguish both byte positions, both ordering directions,
    # odd/even terminators, unsigned high bytes, and interior hash collisions.
    pairs = [(b"", b""), (b"a", b"a"), (b"ab", b"ab"), (b"abc", b"abc"),
             (b"ABcd", b"abcd"), (b"ax", b"ab"), (b"aa", b"ab"),
             (b"zbc", b"abc"), (b"\x81b", b"\x80b"), (b"abcx", b"abc"),
             (b"ab", b"abc"), (b"abc", b"ab")]
    for function, modulus in ((0x4b7f80, 19), (0x4b8170, 5)):
        for mode in (0, 1, 0xffffffff):
            for stored, query in pairs:
                for chain in (False, True):
                    def setup(env, stored=stored, query=query, chain=chain, modulus=modulus):
                        base(env)
                        payload = named(env, stored)
                        values = [named(env, b"different"), payload] if chain else [payload]
                        t = table(env, modulus, [(len(query) % modulus, values)])
                        return {"t": t, "s": string(env, query)}
                    yield Case(f"lookup {mode} {stored!r}/{query!r} chain {chain}", function, setup,
                               receiver=lambda t: t["t"], arguments=(lambda t: t["s"], mode))
            for query in (None, b"absent"):
                def setup(env, query=query, modulus=modulus):
                    base(env)
                    return {"t": table(env, modulus), "s": 0 if query is None else string(env, query)}
                yield Case(f"empty table lookup {query!r} mode {mode}", function, setup,
                           receiver=lambda t: t["t"], arguments=(lambda t: t["s"], mode))

    for query in (0, 1, 9, 0x80000000, 0xffffffff, random_source.getrandbits(32)):
        for kind in ("empty", "first", "second", "miss"):
            def setup(env, query=query, kind=kind):
                base(env)
                match = env.object(64, "type value", fill=0x79)
                other = env.object(64, "other type", fill=0x83)
                env.put(match, query)
                env.put(other, (query + 9) & 0xffffffff)
                values = {"empty": [], "first": [match], "second": [other, match], "miss": [other]}[kind]
                return {"t": table(env, 9, [(query % 9, values)])}
            yield Case(f"type lookup {query:#x} {kind}", 0x4b80e0, setup,
                       receiver=lambda t: t["t"], arguments=(query,))

    # Iterators expose every pointer adjustment and table index independently.
    for count, populated in ((0, ()), (1, ()), (5, ()), (5, (0,)), (5, (4,)), (5, (1, 4))):
        def setup(env, count=count, populated=populated):
            base(env)
            values = [env.object(32 + i * 4, "iterator payload", fill=0x31 + i) for i in range(5)]
            t = table(env, count, [(i, [values[i]]) for i in populated])
            return {"t": t}
        yield Case(f"first bucket {count} {populated}", 0x4d54c0, setup, receiver=lambda t: t["t"])
    for index in (0, 1, 4, 0xffffffff):
        for kind in ("next", "later", "exhausted", "empty"):
            def setup(env, index=index, kind=kind):
                base(env)
                value = env.object(44, "iterator value", fill=0xc1)
                t = table(env, 5, [(3, [value])] if kind == "later" else [])
                following = node(env, value, t, 1) if kind == "next" else 0
                n = node(env, value, t, index, following)
                return {"n": n}
            yield Case(f"next iterator {index:#x} {kind}", 0x4d5350, setup, receiver=lambda t: t["n"])
    for index in (0, 1, 4, 18):
        for populated in (False, True):
            def setup(env, index=index, populated=populated):
                base(env)
                v = env.object(28, "bucket result", fill=0x59)
                return {"t": table(env, 19, [(index, [v])] if populated else [])}
            yield Case(f"indexed bucket {index} {populated}", 0x4d54f0, setup,
                       receiver=lambda t: t["t"], arguments=(index,))

    for function, offset, next_iterator in ((0x4b68e0, 0x3c, False), (0x4b6920, 0x44, False),
            (0x4b6900, 0x24, True), (0x4b6940, 4, True), (0x4b6960, 0x1c, False), (0x4b6980, 0x48, True)):
        for populated in (False, True):
            def setup(env, offset=offset, populated=populated, next_iterator=next_iterator):
                base(env)
                owner = env.object(112, "iterator wrapper", fill=0x6b)
                value = env.object(36, "wrapper result", fill=0xab)
                t = table(env, 5, [(2, [value])] if populated else [])
                if next_iterator:
                    n = node(env, value, t, 0)
                    env.write(owner + offset, env.read(n, 24))
                else:
                    embed(env, owner, offset, t)
                return {"p": owner}
            yield Case(f"iterator wrapper {function:#x} {populated}", function, setup,
                       receiver=(lambda t: t["p"]) if function in (0x4b68e0, 0x4b6920) else 0,
                       arguments=() if function in (0x4b68e0, 0x4b6920) else (lambda t: t["p"],))

    for value in (0, 1, 0xffffffff, random_source.getrandbits(32)):
        def setup(env, value=value):
            p = env.object(64, "root getter", fill=0xbd)
            env.put(p + 0x24, value)
            return {"p": p}
        yield Case(f"root getter {value:#x}", 0x4b7540, setup, receiver=lambda t: t["p"])

    for query in (None, b"Folder", b"folder", b"missing", b""):
        def setup(env, query=query):
            base(env)
            child = named(env, b"Folder")
            root = namespace(env, [(b"Folder", child)])
            return {"p": root, "s": 0 if query is None else string(env, query)}
        yield Case(f"child wrapper {query!r}", 0x4b68c0, setup, receiver=lambda t: t["p"], arguments=(lambda t: t["s"],))
    for type_id in (17, 0xffffffff):
        for query in (None, b"Leaf", b"leaf", b"missing"):
            for hit_type in (True, False):
                def setup(env, query=query, type_id=type_id, hit_type=hit_type):
                    base(env)
                    resource = named(env, b"Leaf")
                    root = namespace(env, resources=[(b"Leaf", resource)], type_id=type_id)
                    return {"p": root, "s": 0 if query is None else string(env, query)}
                yield Case(f"resource wrapper {query!r} {hit_type} {type_id:#x}", 0x4b67f0, setup,
                           receiver=lambda t: t["p"], arguments=(lambda t: t["s"], type_id if hit_type else (type_id + 1) & 0xffffffff))

    directory_paths = [b"", b"F", b"Folder", b"/Folder", b"Folder/", b"Folder///", b"Folder/Child",
        b"Folder\\Child", b"Folder/:;[\\]^_`{|\x80Child", b"//Folder", b"missing/Child"]
    directory_paths += [bytes([c]) + b"Tail" for c in (0x1f, 0x20, 0x2e, 0x2f, 0x30, 0x39, 0x3a, 0x40, 0x41, 0x5a, 0x5b, 0x60, 0x61, 0x7a, 0x7b, 0x80)]
    for path in directory_paths:
        for function in (0x4b7cd0, 0x4b7f20):
            def setup(env, path=path, function=function):
                base(env)
                child = named(env, b"Child")
                embed(env, child, 0x3c, table(env, 5))
                folder = named(env, b"Folder")
                embed(env, folder, 0x3c, table(env, 5, [(0, [child])]))
                root = namespace(env, [(b"Folder", folder), (b"F", named(env, b"F"))])
                p = root
                if function == 0x4b7f20:
                    p = env.object(64, "archive", fill=0xdd)
                    env.put(p + 0x24, root)
                return {"p": p, "s": string(env, path)}
            yield Case(f"directory path {path!r}", function, setup, receiver=lambda t: t["p"], arguments=(lambda t: t["s"],))

    resource_paths = [b"", b"Leaf", b"/Leaf", b"//Leaf", b"Folder/Leaf", b"/Folder/Leaf", b"Folder///Leaf", b"missing/Leaf", b"Folder/", b"Folder///", b"F/Leaf"]
    resource_paths += [bytes([c]) + b"Leaf" for c in (0x1f, 0x20, 0x2e, 0x2f, 0x30, 0x39, 0x3a, 0x40, 0x41, 0x5a, 0x5b, 0x60, 0x61, 0x7a, 0x7b, 0x80)]
    resource_paths += [b"Folder/" + b"x" * n for n in (1, 2, 3, 4, 30, 31, 32, 33, 40, 80)]
    resource_paths += [b"/" + b"x" * n for n in (31, 32, 33, 63, 127, 255, 286)]
    for path in resource_paths:
        for function in (0x4b7dc0, 0x4b7f00):
            def setup(env, path=path, function=function):
                base(env)
                # The source's leaf local is 32 bytes before the directory local.
                # Long leaves are overwritten by the later directory copy.
                raw_leaf = path.rsplit(b"/", 1)[-1]
                resource_names = {b"Leaf", b"", raw_leaf, raw_leaf[:32] + b"Folder"}
                resources = [(s, named(env, s)) for s in sorted(resource_names)]
                folder = namespace(env, resources=resources)
                env.put(folder, string(env, b"Folder"))
                root = namespace(env, [(b"Folder", folder)], resources=resources)
                p = root
                if function == 0x4b7f00:
                    p = env.object(64, "resource archive", fill=0xe3)
                    env.put(p + 0x24, root)
                return {"p": p, "s": string(env, path)}
            yield Case(f"resource path {path[:40]!r} length {len(path)}", function, setup,
                       receiver=lambda t: t["p"], arguments=(lambda t: t["s"], 17))

    # Unseen seeds change both names and collision-chain placement, rather than
    # only scalar hashes. Decoy buckets make an incorrect modulus observable.
    for iteration in range(32):
        modulus = random_source.choice((5, 19))
        function = 0x4b8170 if modulus == 5 else 0x4b7f80
        query = bytes(random_source.choice(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
                      for _ in range(random_source.randrange(1, 100)))
        mode = random_source.choice((0, 1, 7))
        match = random_source.choice((False, True))
        position = random_source.randrange(1, 6)
        def setup(env, modulus=modulus, query=query, mode=mode, match=match, position=position):
            base(env)
            bucket = len(query) % modulus
            names = [bytes([(query[0] + i + 1) % 255 + 1]) + query[1:] for i in range(position)]
            if match:
                names.append(query.swapcase() if mode else query)
            entries = [(i, [named(env, b"decoy bucket " + bytes([65 + i]))])
                       for i in range(modulus) if i != bucket]
            entries.append((bucket, [named(env, n) for n in names]))
            return {"t": table(env, modulus, entries), "s": string(env, query)}
        yield Case(f"random collision {iteration} mode {mode} match {match}", function, setup,
                   receiver=lambda t: t["t"], arguments=(lambda t: t["s"], mode))

    for function in (0x4d54c0, 0x4d54f0, 0x4d5350, 0x4b80e0, 0x4b7f80, 0x4b8170):
        for mode in (0, 1):
            def setup(env, function=function, mode=mode):
                base(env)
                t = table(env, 19)
                # A nonzero link may decode to a null node.
                env.put(env.get(t + 4) + 8, 4)
                n = node(env, env.object(32, "unused value", fill=0x42), t, 0)
                env.put(n + 4, 4)
                if mode:
                    env.put(env.get(t + 4) + 24, 4)
                return {"p": n if function == 0x4d5350 else t, "s": string(env, b"")}
            args = (lambda t: t["s"], mode) if function in (0x4b7f80, 0x4b8170) else ((0,) if function in (0x4d54f0, 0x4b80e0) else ())
            yield Case(f"link four decodes null {function:#x} mode {mode}", function, setup,
                       receiver=lambda t: t["p"], arguments=args)

    for count in (0, 1):
        def setup(env, count=count):
            base(env)
            payload = env.object(40, "zero count first payload", fill=0xb1)
            return {"p": table(env, count, [(0, [payload])])}
        yield Case(f"do while populated count {count}", 0x4d54c0, setup, receiver=lambda t: t["p"])
    for index in (0x10000000, 0x10000001, 0x80000000, 0xffffffff):
        def setup(env, index=index):
            base(env)
            # Place the receiver's bucket pointer inside a backed allocation so
            # index -1 wraps to the preceding 16-byte bucket.
            storage = env.object(64, "wrapped buckets", fill=0x69)
            payload = env.object(40, "wrapped payload", fill=0x51)
            n = node(env, payload)
            env.put(storage + 8, n + 4)
            env.put(storage + 24, n + 4)
            env.put(storage + 40, n + 4)
            t = env.object(8, "wrapped table", words=[2, storage + 16])
            return {"p": t}
        yield Case(f"wrapped bucket index {index:#x}", 0x4d54f0, setup,
                   receiver=lambda t: t["p"], arguments=(index,))

    for leaf_length in (32, 33, 287):
        for directory_length in (2, 63):
            leaf = b"z" * leaf_length
            directory = b"Q" * directory_length
            path = directory + b"/" + leaf
            def setup(env, leaf=leaf, directory=directory, path=path):
                base(env)
                observed_leaf = leaf if len(leaf) < 32 else leaf[:32] + directory
                value = named(env, observed_leaf)
                child = namespace(env, resources=[(observed_leaf, value)])
                env.put(child, string(env, directory))
                root = namespace(env, [(directory, child)])
                return {"p": root, "s": string(env, path)}
            yield Case(f"overlap leaf {leaf_length} directory {directory_length}", 0x4b7dc0, setup,
                       receiver=lambda t: t["p"], arguments=(lambda t: t["s"], 17))

    # A 255-byte directory path has short individual recursive components and
    # reaches the last source-safe byte of the directory temporary.
    path = b"/".join([b"A"] * 128) + b"/Leaf"
    def setup_long_directory(env):
        base(env)
        result = named(env, b"Leaf")
        child = namespace(env, resources=[(b"Leaf", result)])
        for _ in range(128):
            env.put(child, string(env, b"A"))
            child = namespace(env, [(b"A", child)])
        return {"p": child, "s": string(env, path)}
    yield Case("directory temporary count 255 with 128 safe segments", 0x4b7dc0, setup_long_directory,
               receiver=lambda t: t["p"], arguments=(lambda t: t["s"], 17))
