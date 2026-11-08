"""Cases for stalactite: Stalactite object logic.

The entry point (0x48e4a0) reads the state of the owner's block (owner+0x6c, state at +0x1c) and
acts on the child object at block+0x18:
  0x1d  virtual call, slot 0x20
  0x1e  virtual call, slot 0x1c
  0x3e8 nothing
  0     build the child with the original constructor 0x48e990, then call its slot 0x10
  other call the original 0x4dc870 on the child (string table lookup through globals)

The constructor runs as original code over the owner, so the owner is a small world of string
maps that always miss (bucket pointer 0, bucket count non-zero).
"""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

ENTRY = 0x48E4A0
OPERATOR_NEW = 0x4F63EC

# Globals read by 0x4dc870 (the child's string table).
TABLE_LOW = 0x5376A0
TABLE_HIGH = 0x5376A4
TABLE_BASE = 0x5376A8
TABLE_STRIDE = 0x5376B0
TABLE_COUNT = 0x5376B8


def child_with_slots(env, slots):
    """A child object whose vtable holds recording stand-ins in the given slots."""
    child = env.object(0x40, "child", fill=0)
    vtable = env.object(0x40, "child-vtable", fill=0)
    env.put(child, vtable)
    for offset, argc, value in slots:
        env.put(vtable + offset, env.stub(f"child::slot{offset:#x}", "thiscall", argc, returns(value)))
    return child, vtable


def logic(state, slots=((0x10, 0, 0x87), (0x1C, 0, 0x93), (0x20, 0, 0x97)), block_size=0x30):
    """setup(): an owner, its state block and a child with a vtable of stand-ins."""
    def setup(env):
        owner = env.object(0x80, "owner", fill=0)
        block = env.object(block_size, "state-block", fill=0)
        child, vtable = child_with_slots(env, slots)
        env.put(owner + 0x6C, block)
        env.put(block + 0x1C, state)
        env.put(block + 0x18, child)
        return {"owner": owner, "block": block, "child": child, "vtable": vtable}
    return setup


def lookup(state, index, low, high, refcount=1, stride=4):
    """setup(): the default branch. The child's index (child+0x10 -> +0x1c) selects a CString slot."""
    def setup(env):
        owner = env.object(0x80, "owner", fill=0)
        block = env.object(0x30, "state-block", fill=0)
        child, vtable = child_with_slots(env, ((0x04, 1, 0x41), (0x08, 1, 0x42), (0x0C, 1, 0x43)))
        record = env.object(0x30, "child-record", fill=0)
        env.put(record + 0x1C, index)
        env.put(child + 0x10, record)
        slots = env.object(max(1, (high - low + 1)) * stride + 16, "string-slots", fill=0)
        for number in range(low, high + 1):
            text = env.object(12 + 16, f"string-{number}", fill=0x61 + number % 20)
            env.put(text, refcount, 3, 5 + number % 7)
            env.put(slots + (number - low) * stride, text + 12)
        env.put(TABLE_LOW, low)
        env.put(TABLE_HIGH, high)
        env.put(TABLE_BASE, slots)
        env.put(TABLE_STRIDE, stride)
        env.put(TABLE_COUNT, 0xDEAD)
        env.put(owner + 0x6C, block)
        env.put(block + 0x1C, state)
        env.put(block + 0x18, child)
        return {"owner": owner, "block": block, "child": child}
    return setup


def world(random_source, flags=0, mode=None, want_extent=False, bucket_count=7, words=None, tweak=None):
    """setup(): the full world the original constructor 0x48e990 needs, state 0."""
    rnd = random_source

    def setup(env):
        def small():
            return rnd.randrange(0, 600) if words is None else words()

        owner = env.object(0x1A8, "owner", fill=0)
        block = env.object(0x120, "state-block", fill=0)
        parent = env.object(0x40, "owner-parent", fill=0)
        names = env.object(0x20, "name-map", fill=0)
        tiles = env.object(0x70, "tile-rules", fill=0)
        env.put(names + 0x14, 0)
        env.put(names + 0x18, bucket_count)
        for field in (0x10, 0x14, 0x28, 0x2C):
            env.put(parent + field, names)
        env.put(parent + 0x24, tiles)
        env.put(tiles + 0x64, rnd.randrange(0, 40) if mode != "narrow" else 0, rnd.randrange(0, 40) if mode != "narrow" else 0)
        if mode == "negative":
            env.put(tiles + 0x64, 0xFFFFFFFE, 0xFFFFFFFD)
        env.put(owner + 0x0C, parent)
        env.put(owner + 0x14, names)
        env.put(owner + 0x6C, block)
        env.put(owner + 0x08, flags)
        env.put(owner + 0x4C, small())
        env.put(owner + 0x50, small())
        env.put(owner + 0x148, small())
        env.put(owner + 0x14C, small())
        env.put(owner + 0x100, small())
        env.put(owner + 0xCC, rnd.randrange(0, 10))
        for field in (0x2C, 0x30, 0x34, 0x38, 0xB8, 0xF0, 0xF4, 0xF8, 0xFC, 0x100, 0x104, 0x108, 0x10C):
            env.put(block + field, small() if rnd.random() < 0.8 else 0)
        env.put(block + 0x1C, 0)
        child, vtable = child_with_slots(env, ((0x10, 0, 0x87),))
        env.put(block + 0x18, child)  # replaced by the constructor
        extent = None
        if want_extent:
            extent = env.object(0x40, "extent", fill=0)
            env.put(extent + 0x18, small(), small(), small(), small())
            env.put(owner + 0x174, extent)
        pusher = None
        if flags & 0x10:
            pusher = env.object(0x170, "pusher", fill=0)
            env.put(pusher + 0x158, rnd.randrange(0, 20), rnd.randrange(0, 20))
            env.put(owner + 0x80, pusher)
        if tweak:
            tweak(env, owner, block)
        return {"owner": owner, "block": block, "child": child, "extent": extent, "pusher": pusher}
    return setup


def run(label, setup):
    return Case(label, ENTRY, setup, arguments=(lambda t: t["owner"],))


def cases(random_source):
    yield run("state 0x1d calls slot 0x20", logic(0x1D))
    yield run("state 0x1e calls slot 0x1c", logic(0x1E))
    yield run("state 1000 does nothing", logic(0x3E8))
    for _ in range(4):
        state = random_source.randrange(0x1F, 0x3E8)
        yield run(f"state {state:#x} is not special", lookup(state, 5, 3, 9))
    for state in (1, 2, 0x1C, 0x1F, 0x3E9, 0xFFFFFFFF, 0x80000000):
        yield run(f"state {state:#x} uses the string table", lookup(state, 6, 4, 8))
    yield run("string table first entry", lookup(7, 4, 4, 8))
    yield run("string table last entry", lookup(7, 8, 4, 8))
    yield run("string table single entry", lookup(9, 3, 3, 3))
    yield run("string table wide stride", lookup(0x20, 11, 10, 14, stride=8))
    for state in (0x1D, 0x1E):
        yield run(f"state {state:#x} with a larger block", logic(state, block_size=0x120))
    for state in (0x1D, 0x1E, 0x3E8):
        yield run(f"state {state:#x} leaves the child alone", logic(state, slots=((0x1C, 0, 5), (0x20, 0, 6))))

    yield run("state 0 builds the child", world(random_source))
    for _ in range(10):
        yield run("state 0 random world", world(random_source))
    yield run("state 0 with an extent", world(random_source, want_extent=True))
    yield run("state 0 with the push flag", world(random_source, flags=0x10))
    yield run("state 0 with the push flag and extent", world(random_source, flags=0x10, want_extent=True))
    yield run("state 0 with another flag", world(random_source, flags=0x400000))
    yield run("state 0 with negative tolerances", world(random_source, mode="negative"))
    yield run("state 0 with narrow tolerances", world(random_source, mode="narrow"))
    yield run("state 0 one bucket", world(random_source, bucket_count=1))
    yield run("state 0 zeroed counters", world(random_source, words=lambda: 0))

    def large(env, owner, block):
        env.put(owner + 0x4C, 100000)
        env.put(owner + 0x50, 70000)

    yield run("state 0 large coordinates", world(random_source, tweak=large))

    def zero_allocation(setup):
        def wrapped(env):
            tokens = setup(env)
            env.override(OPERATOR_NEW, lambda env, call: env.object(call.arguments[0], name="allocation", fill=0))
            return tokens
        return wrapped

    yield run("state 0 with zeroed allocation", zero_allocation(world(random_source)))

    def initializing_callback(setup, change_owner_block=False):
        def wrapped(env):
            tokens = setup(env)
            alternate = env.object(0x120, "alternate-state-block", fill=0x5B)
            replacement, _ = child_with_slots(env, ((0x10, 0, 0xC7),))
            witness = env.object(12, "initialization-witness", fill=0xA7)

            def initialize(env, call):
                # Record the state visible to initialization, then change the
                # pending child so the final publication has observable work.
                env.put(witness, env.get(tokens["block"] + 0x18),
                        env.get(tokens["block"] + 0x1C), call.receiver)
                env.put(tokens["block"] + 0x18, replacement)
                if change_owner_block:
                    env.put(tokens["owner"] + 0x6C, alternate)
                return 0x80004005

            env.put(0x50F8A4 + 0x10,
                    env.stub("constructed-child::initialize", "thiscall", 0, initialize))
            return tokens
        return wrapped

    yield run("initialization changes pending child before publication",
              initializing_callback(world(random_source)))
    yield run("initialization changes owner block; publication uses original block",
              initializing_callback(world(random_source), change_owner_block=True))

    def allocation_changes_owner_block(setup):
        def wrapped(env):
            tokens = setup(env)
            alternate = env.object(0x120, "allocation-alternate-block", fill=0)
            env.write(alternate, env.read(tokens["block"], 0x120))

            def allocate_and_redirect(env, call):
                env.put(tokens["owner"] + 0x6C, alternate)
                return env.object(call.arguments[0], name="allocation", fill=0x6D)

            env.override(OPERATOR_NEW, allocate_and_redirect)
            return tokens
        return wrapped

    yield run("allocation redirects owner block; entry retains original block",
              allocation_changes_owner_block(world(random_source)))
