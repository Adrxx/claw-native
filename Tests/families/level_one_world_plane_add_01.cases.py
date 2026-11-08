"""Cases for level_one_world_plane_add_01: Level 1 world add-plane."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns  # noqa: F401

ADD_PLANE = 0x4CB7B0
OPERATOR_NEW = 0x4F63EC
PLANE_VTABLE = 0x513D40
SLOT_INIT = PLANE_VTABLE + 0x28
SLOT_DESTROY = PLANE_VTABLE + 4


def world(index, capacity=None, grow_by=0, plane_flags=0, init_result=1, field_c=0x11223344, shrink_to=None,
          bump_index_to=None, start_slot=0x5C5C5C5C, prior_5c=0x0A0B0C0D, prior_60=0x0E0F1011, slots=None):
    """setup() for one world whose plane list currently holds `index` entries."""
    if capacity is None:
        capacity = index + 4
    capacity = max(capacity, index)

    def setup(env):
        this = env.object(0x80, "world", fill=0)
        data = env.object(max(4, capacity * 4), "plane-list")
        for i in range(capacity):
            env.put(data + 4 * i, (slots[i] if slots else 0xA0000000 + i * 0x101))
        env.put(this + 0x0C, field_c)
        env.put(this + 0x10, 0x31, 0x32, 0x33, 0x34)
        env.put(this + 0x34, 0x77, data, index, capacity, grow_by)
        env.put(this + 0x5C, prior_5c, prior_60)
        env.put(this + 0x40, 0xDEAD0001, 0xDEAD0002)
        log = env.object(64, "log", fill=0)

        def init(env, call):
            obj = call.receiver
            env.put(log, call.receiver, call.arguments[0], call.arguments[1], call.arguments[2],
                    env.get(this + 0x3C), env.get(obj + 4), env.get(obj + 0xC))
            if plane_flags:
                env.put(obj + 8, plane_flags)
            if shrink_to is not None:
                env.put(this + 0x3C, shrink_to)
            if bump_index_to is not None:
                env.put(this + 0x3C, bump_index_to)
            return init_result

        def destroy(env, call):
            env.put(log + 0x20, call.receiver, call.arguments[0], env.calls_so_far(SLOT_DESTROY))
            return 0x66

        env.put(SLOT_INIT, env.stub("plane::Init", "thiscall", 3, init))
        env.put(SLOT_DESTROY, env.stub("plane::Destroy", "thiscall", 1, destroy))
        return {"this": this, "data": data, "log": log}

    return setup


def add(label, setup, a1=0x11110001, a2=0x22220002, a3=0x33330003, **options):
    return Case(label, ADD_PLANE, setup, receiver=lambda t: t["this"], arguments=(a1, a2, a3), **options)


def cases(random_source):
    for index in (0, 1, 2, 5, 17):
        for flags in (0, 1, 2, 3, 0x80, 0xFF, 0x100):
            yield add(f"index {index} flags {flags:#x}", world(index, plane_flags=flags))
    # exactly full list, one slot spare, and growth cases
    for index, capacity in ((0, 0), (0, 1), (3, 3), (3, 4), (4, 4), (9, 9), (1023, 1023)):
        for grow_by in (0, 1, 7, 64):
            for flags in (0, 1):
                yield add(f"index {index} capacity {capacity} grow {grow_by} flags {flags}",
                          world(index, capacity, grow_by, flags))
    for result in (0, 1, 2, 0x80000000, 0xFFFFFFFF):
        yield add(f"init returns {result:#x}", world(3, plane_flags=1, init_result=result))
    yield add("init fails with flag set does not publish", world(6, plane_flags=1, init_result=0))
    yield add("init fails at full capacity", world(4, 4, 3, init_result=0))
    yield add("index shrinks during init is re-read", world(6, plane_flags=1, shrink_to=2))
    yield add("index grows during init is re-read", world(2, 12, plane_flags=1, bump_index_to=11))
    yield add("index zero during init, flag set", world(5, plane_flags=1, shrink_to=0))
    for _ in range(40):
        index = random_source.randrange(0, 40)
        capacity = index + random_source.randrange(0, 9)
        flags = random_source.randrange(0, 256)
        yield add(f"random index {index} capacity {capacity} flags {flags:#x}",
                  world(index, capacity, random_source.choice((0, 0, 1, 3, 16)), flags, init_result=random_source.choice((0, 1, 5)),
                        field_c=random_source.getrandbits(32) | 1,
                        prior_5c=random_source.getrandbits(32), prior_60=random_source.getrandbits(32)),
                  a1=random_source.getrandbits(32), a2=random_source.getrandbits(32), a3=random_source.getrandbits(32))
