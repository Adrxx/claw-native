"""Original actor construction, initialization and WWD publication cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW = 0x4F63EC


def salted(env, size, name, salt):
    return env.object(size, name, data=bytes(((salt + i * 37) % 255) + 1 for i in range(size)))


def leaf_setup(size, salt, failure=False):
    def setup(env):
        target = salted(env, size, "receiver", salt)
        scene = salted(env, 0x30, "scene", salt + 13)
        if failure:
            env.override(NEW, allocate(fail=True))
        return {"target": target, "scene": scene}
    return setup


def actor_setup(flags, status=1, mutate=False, concrete=False, alias=False):
    def setup(env):
        actor = salted(env, 0x1B4, "actor", 61)
        scene = salted(env, 0x30, "scene", 27)
        logic = salted(env, 0x174, "logic", 103)
        other = salted(env, 0x174, "replacement logic", 191)
        metadata = (actor + (0xF0 if alias == "initial stores" else 0x178)
                    if alias else salted(env, 0x20, "metadata", 73))
        receipt = env.object(0x30, "callback receipt", fill=0)
        env.put(actor + 0x0C, scene)
        env.put(actor + 0x6C, logic)
        env.put(metadata + 8, flags)
        env.put(metadata + 0x10, 0x1234ABCD)
        env.put(other + 8, flags)
        if concrete:
            env.put(logic, 0x513740)
        else:
            table = env.object(0x28, "caller supplied logic table", fill=0)
            def callback(env, call):
                env.put(receipt, call.receiver, *call.arguments,
                        env.get(actor + 0x4C), env.get(actor + 0xF0),
                        env.get(actor + 0x180), env.get(actor + 0x190))
                if mutate:
                    env.put(actor + 0x4C, 0x12345678, 0x87654321)
                    env.put(actor + 0x6C, other)
                    env.put(actor + 8, 0x204)
                    env.put(logic + 8, flags ^ 3)
                return status
            env.put(table + 0x24, env.stub("caller logic initialize", "thiscall", 2, callback))
            env.put(logic, table)
            env.put(logic + 8, flags)
        return {"target": actor, "metadata": metadata}
    return setup


def manager(env, name, entries):
    result = env.object(0x30, name, fill=0)
    buckets = env.object(4, name + " buckets", fill=0)
    head = 0
    for key, value in entries:
        text = env.object(len(key) + 8, name + " key", data=key + b"\0" * 8)
        head = env.object(0x10, name + " node", words=[head, 0x2740, text, value])
    env.put(buckets, head)
    env.put(result + 0x14, buckets, 1)
    return result


def loader_setup(words, strings, found=True, callback=True, fail_actor=False,
                 image_found=False, populated=False, mutate_header=False):
    def setup(env):
        env.put(0x540E00, 0)
        env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))
        def decrement(e, c):
            value = (e.get(c.arguments[0]) - 1) & 0xFFFFFFFF
            e.put(c.arguments[0], value)
            return value
        env.override(0x5469E8, decrement)
        scene = env.object(0x30, "scene", fill=0)
        plane = env.object(0xB4, "plane", fill=0)
        metadata = salted(env, 0x20, "logic resource", 93)
        env.put(metadata + 8, words[10] & 3)
        env.put(metadata + 0x10, 0x99887766 if callback else 0)
        logic_manager = manager(env, "logic manager", [(strings[1], metadata)] if found and strings[1] else [])
        image_entries = []
        if image_found:
            frames = env.object(16, "frames", words=[0x11100011, 0x22200022, 0x33300033, 0x44400044])
            image = env.object(0x6C, "image resource", fill=0)
            env.put(image + 0x14, frames)
            env.put(image + 0x64, 1, 3)
            image_entries = [(strings[2], image)]
        images = manager(env, "image manager", image_entries)
        animations = manager(env, "animation manager", [])
        alt_animations = manager(env, "alternate animation manager", [])
        env.put(scene + 0x10, images, logic_manager)
        env.put(scene + 0x24, 0xABCD1234, alt_animations, animations)
        collection = env.object(0x10, "collection", fill=0)
        for index in range(3):
            grid = env.object(0x44, "spatial grid", fill=0)
            cells = env.object(8, "cell table", fill=0)
            env.put(grid + 0x0C, 1)
            env.put(grid + 0x14, 8, 8)
            env.put(grid + 0x40, cells)
            if populated:
                previous = env.object(0x20, "existing spatial link", fill=0)
                env.put(cells, previous, previous)
                env.put(previous + 0x0C, cells)
            env.put(collection + 4 + index * 4, grid)
        env.put(plane + 0x0C, scene)
        env.put(plane + 0x30, 100, 80)
        env.put(plane + 0xB0, collection)
        header = env.object(0x11C + sum(len(s) for s in strings), "WWD header", words=words,
                            data=None)
        cursor = header + 0x11C
        for text in strings:
            env.write(cursor, text)
            cursor += len(text)
        def allocator(e, c):
            if fail_actor and c.arguments[0] == 0x1B4:
                return 0
            result = salted(e, c.arguments[0], "allocation", 47)
            if mutate_header and c.arguments[0] == 0x1B4:
                e.put(header, 0x11111111, 0, 0, 0, 0, 99, 79, 0x22222222, 3)
                e.put(header + 0x2C, 0x12344321)
            return result
        env.override(NEW, allocator)
        return {"target": plane, "header": header}
    return setup


def cases(random_source):
    for function, size, count in ((0x4C9690, 0x24, 0), (0x4C96C0, 0x1C, 0),
                                  (0x4C9780, 0x58, 3), (0x4C9830, 0x20, 3),
                                  (0x4C98C0, 0xC8, 3), (0x4C9BA0, 0x10, 0),
                                  (0x4C81F0, 0x2C, 1)):
        for iteration in range(3):
            values = [random_source.getrandbits(32) for _ in range(count)]
            yield Case(f"salted leaf {function:x} {iteration}", function,
                       leaf_setup(size, random_source.randrange(255)), receiver=lambda t: t["target"], arguments=values)
    yield Case("nested logic allocation fails", 0x4C98C0, leaf_setup(0xC8, 45, True),
               receiver=lambda t: t["target"], arguments=(0x18273849, 0xAABBCCDD, 0xFF001122))
    for callback in (0, 1, 0xFEEBA123):
        yield Case(f"logic callback {callback:x}", 0x4C8160, leaf_setup(0x170, 31),
                   receiver=lambda t: t["target"], arguments=(callback, random_source.getrandbits(32)))
    yield Case("null callback does not dereference null receiver", 0x4C8160, arguments=(0, 0x444))
    for alias in (False, True):
        def position(env, alias=alias):
            t = leaf_setup(0x100, 99)(env)
            env.put(t["target"] + 0xC, t["target"] + 0x20 if alias else t["scene"])
            return t
        yield Case(f"position scene alias {alias}", 0x4D5800, position,
                   receiver=lambda t: t["target"], arguments=(0xFFFFF123, 0x8ABCDEF0))
    for function in (0x4C7DF0, 0x4C9D40):
        for flags in (0, 1, 2, 3, 0x80000002):
            for mutate in (False, True):
                yield Case(f"actor {function:x} flags {flags:x} mutate {mutate}", function,
                           actor_setup(flags, mutate=mutate), receiver=lambda t: t["target"],
                           arguments=(0xFFFFFA12, 0x123456, 0x87654321, lambda t: t["metadata"]))
        yield Case(f"actor {function:x} callback failure", function, actor_setup(3, status=0),
                   receiver=lambda t: t["target"], arguments=(3, 5, 7, lambda t: t["metadata"]))
        yield Case(f"actor {function:x} metadata aliases initial stores", function, actor_setup(2, alias="initial stores"),
                   receiver=lambda t: t["target"], arguments=(19, 29, 39, lambda t: t["metadata"]))
        yield Case(f"actor {function:x} metadata aliases animation", function, actor_setup(2, alias=True),
                   receiver=lambda t: t["target"], arguments=(19, 29, 39, lambda t: t["metadata"]))
        yield Case(f"actor {function:x} pinned concrete logic", function, actor_setup(2, concrete=True),
                   receiver=lambda t: t["target"], arguments=(19, 29, 39, lambda t: t["metadata"]))
    yield Case("loader null header", 0x4D17E0, arguments=(0,))
    base = [random_source.getrandbits(32) for _ in range(71)]
    base[:10] = [0xABC321, 3, 4, 5, 3, 12, 23, 0x87654321, 2, 0x1234]
    base[10] = 0
    texts = (b"abc", b"Move", b"Image", b"Ani")
    variants = [("normal", {}, {}), ("allocation failure", {}, {"fail_actor": True}),
                ("initialization failure", {}, {"callback": False}),
                ("resource missing", {}, {"found": False}),
                ("image found", {}, {"image_found": True}),
                ("first image frame", {8: 0xFFFFFFFF}, {"image_found": True}),
                ("image miss first frame", {8: 0xFFFFFFFF}, {}),
                ("live header after allocation", {}, {"mutate_header": True}),
                ("populated spatial", {}, {"populated": True})]
    for label, updates, options in variants:
        words = base.copy()
        for index, value in updates.items():
            words[index] = value
        yield Case("loader " + label, 0x4D17E0, loader_setup(words, texts, **options),
                   receiver=lambda t: t["target"], arguments=(lambda t: t["header"],))
    for x, y in ((-1, 2), (100, 2), (2, -1), (2, 80), (0, 0), (99, 79)):
        words = base.copy()
        words[5:7] = [x & 0xFFFFFFFF, y & 0xFFFFFFFF]
        yield Case(f"loader coordinate {x} {y}", 0x4D17E0, loader_setup(words, texts),
                   receiver=lambda t: t["target"], arguments=(lambda t: t["header"],))
    for length in (0, -1, 1, 4, 5):
        words = base.copy()
        words[1:5] = [length & 0xFFFFFFFF] * 4
        strings = tuple(bytes([65 + i]) * max(0, length) for i in range(4))
        yield Case(f"loader string length {length}", 0x4D17E0, loader_setup(words, strings),
                   receiver=lambda t: t["target"], arguments=(lambda t: t["header"],))
    for first, second in ((0, 0), (0, 7), (7, 0)):
        for flags in (0, 1, 2, 3):
            words = base.copy()
            for a, b in ((23, 25), (19, 21), (31, 33), (27, 29)):
                words[a], words[b] = first, second
            words[10] = flags
            words[69:71] = [0, 0] if not flags else [0x80000000, 0xFFFFFFFF]
            yield Case(f"loader pairs {first} {second} flags {flags}", 0x4D17E0, loader_setup(words, texts),
                       receiver=lambda t: t["target"], arguments=(lambda t: t["header"],))

    for strings in ((b"", b"Move", b"", b""),
                    (b"a" * 1023, b"Move", b"", b"Ani"),
                    (b"a\0b", b"Move", b"Image", b"")):
        words = base.copy()
        words[1:5] = [len(text) for text in strings]
        yield Case(f"loader optional strings lengths {[len(text) for text in strings]}",
                   0x4D17E0, loader_setup(words, strings), receiver=lambda t: t["target"],
                   arguments=(lambda t: t["header"],))
    for defaults in ((0, 0xFFFFFFFF), (0x80000000, 0)):
        words = base.copy()
        words[69:71] = defaults
        yield Case(f"loader independent default overrides {defaults}", 0x4D17E0,
                   loader_setup(words, texts), receiver=lambda t: t["target"],
                   arguments=(lambda t: t["header"],))
