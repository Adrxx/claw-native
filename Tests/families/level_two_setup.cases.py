"""Cases for level_two_setup: Level 2 per-level setup."""
from clawparity.cases import Case

SETUP = 0x452CC0
SET_RECT = 0x546D5C
GLOBALS = (0x5262B0, 0x5262B4, 0x5262B8)
SIZE = 0xC8


def set_rect_effect(result):
    def effect(env, call):
        env.put(call.arguments[0], *call.arguments[1:5])
        return result
    return effect


def scene(salt, size=SIZE, result=1, globals_fill=None, inert_rect=False):
    """A nonzero object with distinct contents around every written offset."""
    def setup(env):
        data = bytes(((index * 37 + salt * 11 + (index >> 3)) & 0xFF) | 1 for index in range(size))
        obj = env.object(size, "level two object", data=data)
        # Distinct nonzero words directly at and around each written field and rectangle.
        for offset in (0x40, 0x44, 0x48, 0x54, 0x58, 0x5C, 0x60, 0x64, 0x68, 0x6C, 0x70, 0x74,
                       0x78, 0x7C, 0x80, 0x84, 0xAC, 0xB0, 0xB4, 0xB8, 0xBC):
            env.put(obj + offset, (0x9E3779B1 * (offset + salt + 1)) & 0xFFFFFFFF)
        for index, address in enumerate(GLOBALS):
            value = (0xA5A5A5A5 ^ (salt * 0x01010101) ^ (index * 0x10203)) & 0xFFFFFFFF
            if globals_fill is not None:
                value = globals_fill[index]
            env.put(address, value)
        if not inert_rect:
            env.override(SET_RECT, set_rect_effect(result))
        else:
            env.override(SET_RECT, lambda env, call: result)
        return {"object": obj}
    return setup


def null_scene(salt, globals_fill=None):
    def setup(env):
        for index, address in enumerate(GLOBALS):
            env.put(address, (0x5A5A5A5A + salt * 0x1111 + index) & 0xFFFFFFFF if globals_fill is None else globals_fill[index])
        env.override(SET_RECT, set_rect_effect(1))
        return {}
    return setup


def level(label, setup):
    return Case(label, SETUP, setup, arguments=(lambda tokens: tokens["object"],))


def cases(random_source):
    yield Case("null argument", SETUP, null_scene(1), arguments=(0,))
    yield Case("null argument, globals one", SETUP, null_scene(2, (0x3F800000,) * 3), arguments=(0,))
    yield Case("null argument, globals zero", SETUP, null_scene(3, (0, 0, 0)), arguments=(0,))
    for salt in range(1, 9):
        yield level(f"object salt {salt}", scene(salt))
    for result in (0, 1, 0xFFFFFFFF, 0x80004005):
        yield level(f"SetRect result {result:#x} is ignored", scene(5, result=result))
    for fill in ((0, 0, 0), (0x3F800000,) * 3, (0xFFFFFFFF,) * 3, (0x3F800000, 0, 0),
                 (0, 0x3F800000, 0), (0, 0, 0x3F800000), (1, 2, 3)):
        yield level(f"globals preset {fill}", scene(6, globals_fill=fill))
    yield level("exact-size object", scene(7, size=0xBC))
    yield level("rectangles not written by the fixture", scene(9, inert_rect=True))
    for index in range(40):
        size = random_source.choice((0xBC, 0xC0, 0xC8, 0x100, 0x200))
        yield level(f"random object {index}", scene(
            random_source.randrange(1, 4096), size=size,
            result=random_source.choice((0, 1, random_source.randrange(0, 1 << 32))),
            globals_fill=tuple(random_source.randrange(0, 1 << 32) for _ in range(3))))
    for index in range(10):
        yield Case(f"random null {index}", SETUP,
                   null_scene(index, tuple(random_source.randrange(0, 1 << 32) for _ in range(3))), arguments=(0,))
