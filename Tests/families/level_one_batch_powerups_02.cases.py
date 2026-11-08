"""Cases for level_one_batch_powerups_02: Level 1 claw hit box setup and powerup lookup."""
from clawparity.cases import Case

HITBOX = 0x417050
LOOKUP = 0x436860


def hitbox_case(label, flag, random_source):
    def setup(env):
        words = [random_source.randrange(1, 1 << 32) for _ in range(0x140 // 4)]
        obj = env.object(0x140, "claw", words=words)
        ptr = env.object(4, "flag", words=[flag])
        return {"obj": obj, "ptr": ptr}

    return Case(label, HITBOX, setup, arguments=(lambda t: t["obj"], lambda t: t["ptr"]))


def lookup_case(label, entries, query, random_source, head_present=True, same_node=False):
    """entries: list of (k1, k2); the list is walked in order. query: (a, b)."""
    def setup(env):
        this = env.object(16, "list", fill=0)
        for i in range(4):
            env.put(this + 4 * i, random_source.randrange(1, 1 << 32))
        records = [env.object(12, f"record{i}", words=[k1, k2, random_source.randrange(1, 1 << 32)])
                   for i, (k1, k2) in enumerate(entries)]
        nodes = [env.object(12, f"node{i}", fill=0) for i in range(len(entries))]
        for i, node in enumerate(nodes):
            env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0)
            env.put(node + 4, random_source.randrange(1, 1 << 32))
            env.put(node + 8, records[i])
        env.put(this + 4, nodes[0] if nodes and head_present else 0)
        return {"this": this, "records": records}

    return Case(label, LOOKUP, setup, receiver=lambda t: t["this"], arguments=query)


def cases(random_source):
    for flag in (0, 1, 2, 0x80000000, 0xFFFFFFFF, 0x100, 0x10000):
        for rep in range(3):
            yield hitbox_case(f"hitbox flag {flag:#x} #{rep}", flag, random_source)
    for _ in range(20):
        yield hitbox_case("hitbox random flag", random_source.randrange(0, 1 << 32), random_source)

    yield lookup_case("empty list", [], (3, 4), random_source)
    yield lookup_case("empty list zero query", [], (0, 0), random_source)
    base = [(11, 21), (12, 22), (13, 23), (14, 24)]
    for idx, (a, b) in enumerate(base):
        yield lookup_case(f"match position {idx}", base, (a, b), random_source)
    yield lookup_case("no match", base, (99, 98), random_source)
    yield lookup_case("first key only matches", base, (12, 99), random_source)
    yield lookup_case("second key only matches", base, (99, 23), random_source)
    yield lookup_case("keys swapped", base, (22, 12), random_source)
    yield lookup_case("first key matches in several, second picks", [(5, 1), (5, 2), (5, 3)], (5, 3), random_source)
    yield lookup_case("second key matches in several, first picks", [(1, 7), (2, 7), (3, 7)], (2, 7), random_source)
    yield lookup_case("duplicate returns first", [(8, 9), (6, 6), (8, 9)], (8, 9), random_source)
    yield lookup_case("zero keys match", [(1, 2), (0, 0)], (0, 0), random_source)
    yield lookup_case("negative keys", [(0xFFFFFFFF, 0x80000000), (3, 4)], (0xFFFFFFFF, 0x80000000), random_source)
    yield lookup_case("single match", [(1, 2)], (1, 2), random_source)
    yield lookup_case("single miss", [(1, 2)], (2, 1), random_source)
    for _ in range(40):
        n = random_source.randrange(1, 9)
        entries = [(random_source.randrange(0, 6), random_source.randrange(0, 6)) for _ in range(n)]
        if random_source.randrange(2):
            query = random_source.choice(entries)
        else:
            query = (random_source.randrange(0, 8), random_source.randrange(0, 8))
        yield lookup_case(f"random list of {n}", entries, query, random_source)
