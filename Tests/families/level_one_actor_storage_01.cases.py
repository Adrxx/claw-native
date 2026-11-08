"""Actor storage cases derived from the v1.0 instructions and supplied callbacks."""
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW = 0x4F63EC


def binding_setup(slot, word, mode="existing", result=0x71826354):
    def setup(env):
        owner = env.object(0x7C, "binding-owner", fill=0xA5)
        scene = env.object(0x40, "scene", fill=0xB6)
        metadata = env.object(0x20, "metadata", fill=0xC7)
        log = env.object(0x40, "callback-record", fill=0xD8)
        table = env.object(0x28, "selected-vtable", fill=0xE9)
        selected = env.object(0x174, "selected", fill=0x91)
        replacement = env.object(0x174, "replacement", fill=0x82)
        env.put(owner + 4, word)
        env.put(owner + 0xC, scene)
        env.put(owner + 0x70, 0)
        env.put(owner + 0x78, 0)
        env.put(metadata + 0x10, word ^ 0xF1E2D3C4)
        env.put(selected, table)
        env.put(replacement, table)

        def reset(env, call):
            env.put(log, call.receiver, env.get(owner + slot), env.get(metadata + 0x10))
            if mode == "clear":
                env.put(owner + slot, 0)
            if mode == "replace":
                env.put(owner + slot, replacement)
                env.put(metadata + 0x10, word ^ 0x1234ABCD)
            return word ^ 0x87654321

        def initialize(env, call):
            env.put(log + 0x10, call.receiver, *call.arguments, env.get(owner + slot))
            env.put(call.receiver + 0x30, word ^ 0xAA55AA55)
            return result

        env.put(table + 0x1C, env.stub("selected reset", "thiscall", 0, reset))
        env.put(table + 0x24, env.stub("selected initialize", "thiscall", 2, initialize))
        env.put(owner + slot, 0 if mode in ("allocate", "allocate-mutates", "fail") else selected)
        if mode in ("allocate", "allocate-mutates"):
            def new_binding(env, call):
                if mode == "allocate-mutates":
                    env.put(owner + 4, word ^ 0x579BDF13)
                    env.put(owner + 0xC, replacement)
                    env.put(metadata + 0x10, word ^ 0x2468ACE0)
                return env.object(call.arguments[0], "binding-allocation", fill=0x73)
            env.override(NEW, new_binding)
        if mode == "fail":
            env.override(NEW, allocate(fail=True))
        return dict(owner=owner, metadata=metadata, scene=scene, log=log)
    return setup


def cases(random_source):
    for entry, slot in ((0x4C7F20, 0x70), (0x4C7FE0, 0x78)):
        for mode in ("existing", "clear", "replace", "fail", "allocate-mutates"):
            for word in (0, 1, 0x80000000, 0xFFFFFFFF, random_source.getrandbits(32)):
                yield Case(f"{slot:x} {mode} {word:08x}", entry,
                           binding_setup(slot, word, mode, random_source.getrandbits(32)),
                           receiver=lambda t: t["owner"], arguments=(lambda t: t["metadata"],))
        yield Case(f"{slot:x} null metadata preserves selected", entry,
                   binding_setup(slot, random_source.getrandbits(32)),
                   receiver=lambda t: t["owner"], arguments=(0,))

    for entry, slot in ((0x4C7F20, 0x70), (0x4C7FE0, 0x78)):
        for callback in (0, 1, random_source.getrandbits(32)):
            def setup(env, slot=slot, callback=callback):
                tokens = binding_setup(slot, random_source.getrandbits(32), "allocate")(env)
                env.put(tokens["metadata"] + 0x10, callback)
                return tokens
            yield Case(f"{slot:x} new binding callback {callback:x}", entry, setup,
                       receiver=lambda t: t["owner"], arguments=(lambda t: t["metadata"],))

    for entry, slot in ((0x4C7FA0, 0x70), (0x4C8060, 0x78)):
        for lookup in ("miss", "hit", "null"):
            def setup(env, slot=slot, lookup=lookup):
                tokens = binding_setup(slot, random_source.getrandbits(32), "replace")(env)
                add_registry(env, tokens, lookup)
                return tokens
            yield Case(f"{slot:x} named {lookup}", entry, setup,
                       receiver=lambda t: t["owner"], arguments=(lambda t: t["name"],),
                       initial_stack=((-4, random_source.getrandbits(32).to_bytes(4, "little")),))

    scenarios = [
        ("empty", 0, []),
        ("head", 5, [(9, 0), (12, 0)]),
        ("middle", 5, [(-10, 0), (0, 0), (9, 0)]),
        ("tail", 15, [(-10, 0), (0, 0), (9, 0)]),
        ("equal stable", 5, [(5, 0), (5, 0), (6, 0)]),
        ("flag skip", 5, [(9, 0x20000), (10, 0)]),
        ("all flagged", 5, [(9, 0x20000), (10, 0x20000)]),
        ("signed minimum", 0x80000000, [(0xFFFFFFFF, 0), (0x7FFFFFFF, 0)]),
        ("signed maximum", 0x7FFFFFFF, [(0x80000000, 0), (0xFFFFFFFF, 0)]),
        ("negative equal", 0xFFFFFFFF, [(0x80000000, 0), (0xFFFFFFFF, 0), (0, 0)]),
    ]
    for i in range(12):
        depths = sorted(random_source.randrange(-20, 21) for _ in range(5))
        scenarios.append((f"random {i}", random_source.randrange(-20, 21),
                          [(depth, random_source.choice((0, 0x20000, 0xFFFFFFFF))) for depth in depths]))
    for label, depth, nodes in scenarios:
        for flags in (0, 0x200000, random_source.getrandbits(32)):
            yield Case(f"create {label} flags {flags:x}", 0x4C8A20,
                       creator_setup(depth, nodes, random_source.getrandbits(32), flags,
                                     metadata_flags=random_source.choice((0, 1, 2, 3, 0x80000000))),
                       receiver=lambda t: t["owner"],
                       arguments=(lambda t: t["id"], depth & 0xFFFFFFFF, lambda t: t["metadata"], flags))
    for entry in (0x4C8A20, 0x4C8B90):
        for fail in (False, True):
            def setup(env, fail=fail):
                tokens = creator_setup(0x87654321, [(0, 0)], random_source.getrandbits(32),
                                       0x200000, fail=fail)(env)
                add_registry(env, tokens, "hit")
                return tokens
            yield Case(f"creator {entry:x} {'failure' if fail else 'success'}", entry, setup,
                       receiver=lambda t: t["owner"],
                       arguments=(lambda t: t["id"], 0x87654321,
                                  (lambda t: t["name"]) if entry == 0x4C8B90 else (lambda t: t["metadata"]),
                                  0x200000),
                       initial_stack=((-4, b"\x91\xa2\xb3\xc4"),))


    # Readability mutation controls: keep the original case stream above intact.
    # The original stores +0x4c before requesting the primary holder allocation.
    # Its later initializer overwrites that word, so preserve this service-time
    # observation in independent memory instead of checking only final actor bytes.
    def observe_primary_allocation(env):
        tokens = creator_setup(5, [], 0x13579BDF, 0)(env)

        def allocate_and_observe(env, call):
            allocation_number = env.calls_so_far(NEW)
            if allocation_number == 2:
                actor = env.get(tokens["log"])
                env.put(tokens["log"] + 0x20,
                        env.get(actor + 0x4C), env.get(actor), env.get(actor + 0x68),
                        env.get(actor + 0x90), env.get(actor + 0x94),
                        env.get(actor + 0xA0), env.get(actor + 0xAC), env.get(actor + 0xC4))
            token = env.object(call.arguments[0], "observed-allocation", fill=0x6D)
            if allocation_number == 1:
                env.put(tokens["log"], token)
            return token

        env.override(NEW, allocate_and_observe)
        return tokens

    yield Case("create observes sentinel before primary allocation", 0x4C8A20,
               observe_primary_allocation, receiver=lambda t: t["owner"],
               arguments=(lambda t: t["id"], 5, lambda t: t["metadata"], 0))

    # Every bit except 0x20000 must leave an existing greater-depth actor
    # eligible as the insertion position. The dense mask catches any added bit
    # in the named skip-mask constant independently of the random seed.
    for old_flags in (0x1, 0xFFFDFFFF):
        yield Case(f"create unrelated depth flags {old_flags:08x}", 0x4C8A20,
                   creator_setup(5, [(9, old_flags), (10, 0)], 0x2468ACE0, 0),
                   receiver=lambda t: t["owner"],
                   arguments=(lambda t: t["id"], 5, lambda t: t["metadata"], 0))


def add_registry(env, tokens, lookup):
    registry = env.object(0x40, "registry", fill=0xA9)
    name = env.object(16, "lookup-name", data=b"STORAGE\0")
    buckets = env.object(17 * 4, "registry-buckets", fill=0)
    entry = env.object(16, "registry-entry", fill=0xBA)
    # CMapStringToPtr hashes signed bytes by h = 33*h + c, modulo table size.
    key_hash = 0
    for c in b"STORAGE":
        key_hash = (33 * key_hash + c) & 0xFFFFFFFF
    env.put(tokens["scene"] + 0x14, registry)
    env.put(registry + 0x14, buckets, 17)
    env.put(entry, 0, key_hash % 17, name, 0 if lookup == "null" else tokens["metadata"])
    if lookup != "miss":
        env.put(buckets + 4 * (key_hash % 17), entry)
    tokens["name"] = name


def creator_setup(depth, nodes, actor_id, flags, metadata_flags=0, fail=False):
    def setup(env):
        owner = env.object(0x2C, "actor-container", fill=0xA7)
        scene = env.object(0x40, "actor-scene", fill=0xB8)
        metadata = env.object(0x20, "actor-metadata", fill=0xC9)
        log = env.object(0x40, "publication-callback-log", fill=0xDA)
        free = env.object(12, "free-list-node", fill=0xEB)
        env.put(free, 0)
        env.put(owner + 0xC, scene)
        env.put(owner + 0x10, 0, 0, 0, len(nodes), free, 0, 4)
        previous = 0
        for index, (old_depth, old_flags) in enumerate(nodes):
            actor = env.object(0x168, f"existing-actor-{index}", fill=0x9D)
            env.put(actor + 8, old_flags)
            env.put(actor + 0x64, old_depth & 0xFFFFFFFF)
            node = env.object(12, f"existing-node-{index}", words=[0, previous, actor])
            if previous:
                env.put(previous, node)
            else:
                env.put(owner + 0x14, node)
            previous = node
        env.put(owner + 0x18, previous)

        def published(env, call):
            actor = call.arguments[0]
            env.put(log, call.receiver, actor, env.get(actor + 0x68),
                    env.get(owner + 0x14), env.get(owner + 0x18), env.get(owner + 0x1C),
                    env.get(actor + 0x6C), env.get(actor + 0x64))
            env.put(actor + 0x154, actor_id ^ 0x89ABCDEF)
            return actor_id ^ 0x78563412

        callback = env.stub("published actor", "cdecl", 1, published)
        env.put(metadata + 8, metadata_flags)
        env.put(metadata + 0x10, 0 if fail else callback)
        # Nonzero per-allocation bytes expose omitted constructors and zero stores.
        def new_object(env, call):
            return env.object(call.arguments[0], "allocation", fill=0x6D)
        env.override(NEW, new_object)
        return dict(owner=owner, scene=scene, metadata=metadata, id=actor_id, log=log)
    return setup
