"""Cases for end_of_level_checkpoint_timer: End-of-level checkpoint timer entries.

All coverage is deterministic; random_source only varies contents and values.
"""
from clawparity.cases import Case
from clawparity.fixtures import release, returns, sequence  # noqa: F401

SCALAR_DELETING = 0x40DB30
SCALAR_BODY = 0x40DB50
STATE_QUERY = 0x42A630
OWNER_DELETING = 0x4C9FC0
OWNER_BODY = 0x4C9FE0
LIST_BODY = 0x4D3EB0

OWNER_SIZE = 0x1F0
CHILD_FIELDS = (0x6C, 0x70, 0x78)
JUNK_FIELDS = (0x00, 0x20, 0x38, 0x4C, 0xAC, 0xC4, 0x168, 0x16C, 0x170, 0x174, 0x188)


def words(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


# ---------------------------------------------------------------- 0x40db30 / 0x40db50

def scalar_object(random_source):
    def setup(env):
        return {"obj": env.object(0x30, "scalar", words=words(random_source, 12))}
    return setup


# ---------------------------------------------------------------- 0x42a630

def state_object(random_source, results, retarget=None, null=False):
    """Object whose +0x2c member answers slot 0x10 from `results`; `retarget` swaps the member after call 1."""
    def setup(env):
        obj = env.object(0x40, "timer", words=words(random_source, 16))
        if null:
            env.put(obj + 0x2C, 0)
            return {"obj": obj}
        vtable = env.object(0x20, "vtable", words=words(random_source, 8))
        member = env.object(0x10, "member", words=[vtable, 1, 2, 3])
        env.put(obj + 0x2C, member)
        if retarget is None:
            slot = env.stub("member::state", "thiscall", 0, sequence(*results))
        else:
            other_vtable = env.object(0x20, "vtable2", words=words(random_source, 8))
            other = env.object(0x10, "member2", words=[other_vtable, 4, 5, 6])
            other_slot = env.stub("member2::state", "thiscall", 0, sequence(*retarget))

            def first(env, call):
                env.put(obj + 0x2C, other)
                return results[0]
            slot = env.stub("member::state", "thiscall", 0, first)
            env.put(other_vtable + 0x10, other_slot)
        env.put(vtable + 0x10, slot)
        return {"obj": obj}
    return setup


# ---------------------------------------------------------------- 0x4d3eb0 / 0x4c9fe0

def make_list(env, random_source, kinds, vtable, plans=None):
    """Chain of nodes [next, junk, object]; kinds are 'null' or 'obj'. Returns (head, children)."""
    nodes = [env.object(0x10, f"node{index}", words=[0, random_source.randrange(1, 1 << 32), 0, 7])
             for index in range(len(kinds))]
    children = []
    for index, node in enumerate(nodes):
        if index + 1 < len(nodes):
            env.put(node, nodes[index + 1])
        if kinds[index] == "obj":
            child = env.object(0x10, f"listchild{index}", words=[vtable, index + 1, 2, 3])
            env.put(node + 8, child)
            children.append(child)
        else:
            children.append(0)
    return (nodes[0] if nodes else 0), children


def child_vtable(env, plan):
    """Shared vtable whose slot 4 is a thiscall stub that applies plan[receiver] = [(address, value)...]."""
    vtable = env.object(0x10, "child-vtable", words=[0, 0, 0, 0])

    def destroy(env, call):
        for address, value in plan.get(call.receiver, ()):
            env.put(address, value)
        owner = plan.get("owner")
        if owner:
            # Dirty every member the destructor rewrites, so a missing store in a later section is visible.
            for offset in JUNK_FIELDS:
                env.put(owner + offset, ((call.receiver * 0x9E3779B1 + offset) & 0xFFFFFFFF) ^ 0x5A5AA5A5)
        return 0
    env.put(vtable + 4, env.stub("child::destroy", "thiscall", 1, destroy))
    return vtable


def list_owner(random_source, kinds, head_free_list=0, size=OWNER_SIZE):
    def setup(env):
        plan = {}
        vtable = child_vtable(env, plan)
        owner = env.object(size, "list-owner", words=words(random_source, size // 4))
        head, children = make_list(env, random_source, kinds, vtable)
        env.put(owner + 0x1B4, *words(random_source, 6))
        env.put(owner + 0x1B8, head)
        env.put(owner + 0x1B4 + 0x14, head_free_list)
        return {"obj": owner, "children": children, "vtable": vtable, "plan": plan}
    return setup


def full_owner(random_source, present, refill=(), listed=("obj", "null", "obj"), free_list=0, arm_block=False):
    """Owner with children in slots 0x6c/0x70/0x78 where `present` says so.

    refill: pairs (slot, [(field, present)...]) meaning the destroy of that slot's initial child
    stores new children into the given fields, so that later sections see them."""
    def setup(env):
        plan = {}
        vtable = child_vtable(env, plan)
        owner = env.object(OWNER_SIZE, "owner", words=words(random_source, OWNER_SIZE // 4))
        plan["owner"] = owner
        head, listed_children = make_list(env, random_source, listed, vtable)
        env.put(owner + 0x1B4 + 0x14, free_list)
        env.put(owner + 0x1B8, head)
        slots = {}
        for field, here in zip(CHILD_FIELDS, present):
            child = env.object(0x10, f"child{field:x}", words=[vtable, field, 9, 8]) if here else 0
            env.put(owner + field, child)
            slots[field] = child
        extra = []
        for slot, stores in refill:
            writes = []
            for field, here in stores:
                child = env.object(0x10, f"refill{slot:x}-{field:x}", words=[vtable, field, 6, 5]) if here else 0
                writes.append((owner + field, child))
                extra.append(child)
            for target in (slots.get(slot),):
                if target:
                    plan.setdefault(target, []).extend(writes)
            for child in listed_children:
                pass
        if arm_block:
            # Each destroyed slot child hands the block list a live block; operator delete then runs
            # (digesting all memory) inside the original base-class cleanup 0x4f565f.
            for field in CHILD_FIELDS:
                if slots[field]:
                    block = env.object(0x40, f"block{field:x}", words=[0] + words(random_source, 15))
                    plan.setdefault(slots[field], []).append((owner + 0x1C8, block))
        return {"obj": owner, "children": slots, "plan": plan, "vtable": vtable, "listed": listed_children}
    return setup


def owner_with_cascade(random_source, drops=(), arm_block=False):
    """Children destroyed in one section arm the slots that the next section reads.

    Stage s children A (0x6c), B (0x70), C (0x78): B_s arms A_(s+1), C_s arms B_(s+1) and A_(s+1) arms
    C_(s+1).  `drops` lists (stage, name) arms that are left out."""
    def setup(env):
        plan = {}
        vtable = child_vtable(env, plan)
        owner = env.object(OWNER_SIZE, "owner", words=words(random_source, OWNER_SIZE // 4))
        plan["owner"] = owner
        env.put(owner + 0x1B4 + 0x14, 0)
        env.put(owner + 0x1B8, 0)
        kids = [{name: env.object(0x10, f"s{stage}{name}", words=[vtable, stage, ord(name), 4])
                 for name in "ABC"} for stage in range(3)]
        slot = {"A": 0x6C, "B": 0x70, "C": 0x78}
        for name in "ABC":
            env.put(owner + slot[name], kids[0][name])
        for stage in range(3):
            if stage < 2:
                for source, target in (("B", "A"), ("C", "B")):
                    if (stage, target) not in drops:
                        plan.setdefault(kids[stage][source], []).append((owner + slot[target], kids[stage + 1][target]))
            if stage >= 1 and (stage, "C") not in drops:
                plan.setdefault(kids[stage]["A"], []).append((owner + 0x78, kids[stage]["C"]))
        if arm_block:
            for stage in range(3):
                for name in "ABC":
                    block = env.object(0x40, f"block{stage}{name}", words=[0] + words(random_source, 15))
                    plan.setdefault(kids[stage][name], []).append((owner + 0x1C8, block))
        return {"obj": owner}
    return setup


def cases(random_source):
    # ---- 0x40db30: scalar deleting destructor
    for flag in (0, 1, 2, 3, 0x80, 0xFF, 0x100, 0x101, 0xFFFFFFFE, 0xFFFFFFFF):
        yield Case(f"scalar deleting flag {flag:#x}", SCALAR_DELETING, scalar_object(random_source),
                   receiver=lambda t: t["obj"], arguments=(flag,))
    for _ in range(4):
        flag = random_source.randrange(0, 1 << 32)
        yield Case(f"scalar deleting random flag {flag:#x}", SCALAR_DELETING, scalar_object(random_source),
                   receiver=lambda t: t["obj"], arguments=(flag,))

    # ---- 0x40db50: scalar destructor body
    for index in range(4):
        yield Case(f"scalar body {index}", SCALAR_BODY, scalar_object(random_source), receiver=lambda t: t["obj"])

    # ---- 0x42a630: state query
    yield Case("state: no member", STATE_QUERY, state_object(random_source, (), null=True),
               receiver=lambda t: t["obj"])
    values = (3, 4, 6, 5)
    for a in values:
        for b in values:
            for c in values:
                yield Case(f"state results {a},{b},{c}", STATE_QUERY, state_object(random_source, (a, b, c)),
                           receiver=lambda t: t["obj"])
    for results in ((0,), (0xFFFFFFFF,), (0x103,), (0x104, 0x106), (7, 0x10000006, 6),
                     (2, 0xFFFFFFFC, 4), (0, 0, 0), (0x80000003, 3, 3)):
        yield Case(f"state odd results {results}", STATE_QUERY, state_object(random_source, results),
                   receiver=lambda t: t["obj"])
    for results, retarget in (((7, 7, 7), (3,)), ((7, 7, 7), (4, 6)), ((3,), (3,)), ((5, 5), (4,)),
                              ((5, 5), (6, 6)), ((5,), (5, 5))):
        yield Case(f"state member replaced {results}->{retarget}", STATE_QUERY,
                   state_object(random_source, results, retarget=retarget), receiver=lambda t: t["obj"])

    # ---- 0x4d3eb0: list destroyer
    for kinds in ((), ("null",), ("obj",), ("obj", "obj"), ("null", "obj"), ("obj", "null"),
                  ("null", "null"), ("obj", "obj", "obj", "obj"), ("obj", "null", "obj", "null", "obj")):
        yield Case(f"list {'-'.join(kinds) or 'empty'}", LIST_BODY, list_owner(random_source, kinds),
                   receiver=lambda t: t["obj"])

    # ---- 0x4c9fe0: owner destructor body
    for mask in range(8):
        present = tuple(bool(mask >> bit & 1) for bit in range(3))
        yield Case(f"owner body slots {mask:03b}", OWNER_BODY, full_owner(random_source, present),
                   receiver=lambda t: t["obj"])
    for listed in ((), ("obj",), ("null", "obj", "obj", "null")):
        yield Case(f"owner body list {'-'.join(listed) or 'empty'}", OWNER_BODY,
                   full_owner(random_source, (True, True, True), listed=listed), receiver=lambda t: t["obj"])
    for drops in ((), ((1, "A"),), ((1, "B"),), ((1, "C"),), ((2, "A"),), ((2, "B"),), ((2, "C"),),
                  ((1, "A"), (2, "A")), ((1, "B"), (2, "B")), ((1, "C"), (2, "C")),
                  ((1, "A"), (1, "B")), ((2, "A"), (2, "B")), ((1, "B"), (1, "C")), ((2, "B"), (2, "C"))):
        yield Case(f"owner cascade drops {drops}", OWNER_BODY, owner_with_cascade(random_source, drops),
                   receiver=lambda t: t["obj"])
    # refills: a child destroyed in one section re-arms slots seen by the following sections
    for first in range(8):
        for second in (0, 3, 5, 6, 7):
            present = (True, True, True)
            refill = (
                (0x78, [(0x6C, bool(second & 1)), (0x70, bool(second & 2)), (0x78, False)]),
                (0x6C, [(0x70, bool(first & 1))]),
            )
            yield Case(f"owner refill {first}/{second}", OWNER_BODY,
                       full_owner(random_source, present, refill=refill), receiver=lambda t: t["obj"])

    # a live block list in the base-class cleanup makes operator delete run mid-destructor
    for mask in range(1, 8):
        present = tuple(bool(mask >> bit & 1) for bit in range(3))
        yield Case(f"owner body blocks slots {mask:03b}", OWNER_BODY,
                   full_owner(random_source, present, arm_block=True), receiver=lambda t: t["obj"])
    yield Case("owner cascade with blocks", OWNER_BODY, owner_with_cascade(random_source, (), arm_block=True),
               receiver=lambda t: t["obj"])
    for drops in (((1, "A"),), ((2, "B"),), ((1, "C"), (2, "C"))):
        yield Case(f"owner cascade blocks drops {drops}", OWNER_BODY,
                   owner_with_cascade(random_source, drops, arm_block=True), receiver=lambda t: t["obj"])
    for flag in (0, 1):
        yield Case(f"owner deleting with blocks flag {flag}", OWNER_DELETING,
                   full_owner(random_source, (True, True, False), arm_block=True),
                   receiver=lambda t: t["obj"], arguments=(flag,))

    # ---- 0x4c9fc0: owner deleting destructor
    for flag in (0, 1, 2, 3, 0x100, 0x101, 0xFFFFFFFE, 0xFFFFFFFF):
        yield Case(f"owner deleting flag {flag:#x}", OWNER_DELETING, full_owner(random_source, (True, False, True)),
                   receiver=lambda t: t["obj"], arguments=(flag,))
    for flag in (0, 1):
        yield Case(f"owner deleting empty flag {flag}", OWNER_DELETING,
                   full_owner(random_source, (False, False, False), listed=()),
                   receiver=lambda t: t["obj"], arguments=(flag,))
