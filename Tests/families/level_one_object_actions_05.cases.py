"""Original-only cases for level_one_object_actions_05: Level 1 closure object action table entries."""
from clawparity.cases import Case
from clawparity.world import set_rect

SET_RECT_SLOT = 0x546D5C
G_FLOATS = (0x5262B0, 0x5262B4, 0x5262B8)
FUNCTIONS = (0x452D50, 0x452DB0, 0x452EA0, 0x452F80, 0x453070, 0x453150,
             0x453240, 0x453310, 0x453410, 0x453500, 0x453600, 0x4536F0)
RECORD_SIZE = 0x100


def scene(payload, floats):
    """setup(): a record full of distinct nonzero bytes, a scripted SetRect and preset float globals."""
    def setup(env):
        env.put(SET_RECT_SLOT, env.stub("SetRect", "stdcall", 5, set_rect))
        env.put(G_FLOATS[0], *floats)
        record = env.object(RECORD_SIZE, "record", data=payload)
        return {"record": record}
    return setup


def null_scene(floats):
    def setup(env):
        env.put(SET_RECT_SLOT, env.stub("SetRect", "stdcall", 5, set_rect))
        env.put(G_FLOATS[0], *floats)
        return {}
    return setup


def call(label, function, setup):
    return Case(label, function, setup, arguments=(lambda tokens: tokens.get("record", 0),))


def cases(random_source):
    for function in FUNCTIONS:
        name = f"{function:#x}"
        yield call(f"{name} null record", function, null_scene((0x11111111, 0x22222222, 0x33333333)))
        yield call(f"{name} null record zero floats", function, null_scene((0, 0, 0)))
        yield call(f"{name} record of zero bytes", function, scene(bytes(RECORD_SIZE), (0, 0, 0)))
        yield call(f"{name} record of ones", function,
                   scene(b"\xff" * RECORD_SIZE, (0xFFFFFFFF, 0x3F800000, 0xFFFFFFFF)))
        yield call(f"{name} counting record", function,
                   scene(bytes((index * 7 + 1) & 0xFF or 1 for index in range(RECORD_SIZE)),
                         (0xDEADBEEF, 0xCAFEBABE, 0x01020304)))
        for index in range(4):
            payload = bytes(random_source.randrange(1, 256) for _ in range(RECORD_SIZE))
            floats = tuple(random_source.randrange(0, 1 << 32) for _ in range(3))
            yield call(f"{name} random record {index}", function, scene(payload, floats))
