"""Cases for conveyor_belt: ConveyorBelt object logic."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

LOGIC = 0x431320
OPERATOR_NEW = 0x4F63EC


def belt(state, key=2, lo=1, hi=5, stride=0x10, speed=None, flag64=None):
    """setup(): an object whose +0x6c block holds `state` at +0x1c and a child with stand-in virtual methods."""
    def setup(env):
        block = env.object(0x100, "state-block", words=[0x11111111 + i * 0x01010101 & 0x7FFFFFFF for i in range(64)])
        owner = env.object(0x200, "belt-object", words=[0x22222222 + i * 0x00010203 for i in range(128)])
        game = env.object(0x40, "game", words=[0x55555555 + i * 0x00020301 for i in range(16)])
        window = env.object(0x40, "window", words=[0x66666666 + i * 0x00030201 for i in range(16)])
        names = env.object(0x40, "attribute-names", words=[0x77777777 + i * 0x00040302 for i in range(16)])
        env.put(owner + 0x0C, game)
        env.put(game + 0x14, window)
        env.put(game + 0x2C, names)
        env.put(window + 0x14, 0, 1)  # empty string map: no buckets, one slot
        env.put(names + 0x14, 0, 1)
        env.put(owner + 0x170, 0xFFFFFFDC)  # animation name address 0: the empty CString, no Win32 import
        env.put(owner + 0x174, 0)
        env.put(owner + 0x190, 0)  # animation player has no sequence
        env.put(0x537680, 0)  # ES_IDLE tree empty
        if speed is not None:
            env.put(block + 0xBC, speed)
        if flag64 is not None:
            env.put(owner + 0x64, flag64)

        vtable = env.object(0x80, "child-vtable")
        child = env.object(0x58, "child", words=[0x33333333 + i for i in range(22)])
        env.put(child, vtable)
        env.put(child + 0x10, owner)
        env.put(owner + 0x6C, block)
        env.put(block + 0x1C, state)
        table = env.object(0x100, "lookup-table", words=[0x44444444 + i * 0x01000101 for i in range(64)])
        for entry in range(0, 0x100 - 0x10 + 1, 0x10):
            text = env.object(0x20, "text", data=b"\x01\0\0\0\x03\0\0\0\x10\0\0\0abc\0")
            env.put(table + entry, text + 12)
        env.put(owner + 0x1C, key)
        env.put(0x5376A0, lo, hi, table)
        env.put(0x5376B0, stride)
        env.put(0x5376B8, 0)
        env.put(block + 0x18, child)
        for offset in (0x04, 0x08, 0x0C, 0x10, 0x1C, 0x20):
            def method(env, call, offset=offset):
                env.put(call.receiver + 0x54, 0xA0 + offset)  # visible side effect
                return 0x1000 + offset
            env.put(vtable + offset, env.stub(f"child-method-{offset:#x}", "thiscall", 0 if offset in (0x10, 0x1C, 0x20) else 1, method))
        return {"owner": owner, "block": block, "child": child, "vtable": vtable}
    return setup


def logic(label, setup, **options):
    return Case(label, LOGIC, setup, arguments=(lambda t: t["owner"],), **options)


def cases(random_source):
    yield logic("state 0x1d calls vtable +0x20", belt(0x1D))
    yield logic("state 0x1e calls vtable +0x1c", belt(0x1E))
    yield logic("state 1000 does nothing", belt(1000))
    for state in (1, 2, 0x1C, 0x1F, 0x20, 999, 1001, 0x3E9, 0xFFFFFFFF, 0x80000000, 0x10000):
        yield logic(f"state {state:#x} falls to default handler", belt(state))
    for _ in range(12):
        yield logic("random state", belt(random_source.choice([0x1D, 0x1E, 1000, random_source.randrange(1, 0x100000000)])))
    yield logic("state 0 constructs", belt(0))
    for speed in (0, 1, 0x12C, 0x12D, 0x7FFFFFFF, -1, -0x12C, -0x12D, 0x80000000, 77, -77):
        yield logic(f"state 0 constructs with speed {speed}", belt(0, speed=speed & 0xFFFFFFFF))
    for flag in (0, 1, 2):
        yield logic(f"state 0 constructs with flag {flag}", belt(0, flag64=flag))
    for _ in range(6):
        yield logic("state 0 random", belt(0, speed=random_source.randrange(0, 0x100000000), flag64=random_source.choice([0, 1, 5])))

    # 00431387 calls the new child before 0043138a publishes it in the
    # entry block. Make the callback observe and alter that publication slot.
    for replace_block in (False, True):
        marker = random_source.randrange(1, 0x100000000)

        def observing_setup(env, replace_block=replace_block, marker=marker):
            tokens = belt(0, speed=73, flag64=1)(env)
            original_block = tokens["block"]
            alternate = env.object(0x100, "alternate-state-block", fill=0x5A)
            env.put(alternate + 0xBC, 29)

            def initialize(env, call):
                # The callback sees the pre-publication child, then replaces
                # it. The owned function must overwrite this marker on return.
                env.put(call.receiver + 0x54, env.get(original_block + 0x18))
                env.put(original_block + 0x18, marker)
                if replace_block:
                    env.put(tokens["owner"] + 0x6C, alternate)
                return 0xC001CAFE

            env.put(0x50C6BC + 0x10, env.stub("observe-child-publication", "thiscall", 0, initialize))
            return tokens

        yield logic(f"initialize callback alters publication slot; replace block {replace_block}", observing_setup)
