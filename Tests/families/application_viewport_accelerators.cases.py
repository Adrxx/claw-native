"""Cases for application_viewport_accelerators: Application viewport size accelerator commands."""
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

DECREASE = 0x429E30
INCREASE = 0x429E70
READY = 0x42AFD0

# Sequences of the three state queries made by the original state test (0x42a630).
STATES = {
    "3": (3,),
    "4": (0, 4),
    "6": (0, 0, 6),
    "other": (0, 0, 0),
    "7": (7, 7, 7),
    "neg": (-3, 9, 5),
}


LOST = 0x887601C2
FAIL = 0x80004005


def surface(env, name, blit=0, flip=0, restore=0):
    """A surface object whose DirectDraw Blt and Flip and its restore method are stand-ins."""
    target = env.object(0x40, name, fill=0x9C)
    interface = env.object(16, name + "-directdraw", fill=0x3D)
    com = env.object(0x60, name + "-directdraw-vtable", fill=0xB9)
    methods = env.object(0x40, name + "-vtable", fill=0xA7)
    env.put(target, methods)
    env.put(target + 8, interface)
    env.put(interface, com)
    blit_effect = sequence(*blit) if isinstance(blit, tuple) else returns(blit)
    flip_effect = sequence(*flip) if isinstance(flip, tuple) else returns(flip)
    restore_effect = sequence(*restore) if isinstance(restore, tuple) else returns(restore)
    env.put(com + 0x14, env.stub(name + " Blt", "stdcall", 6, blit_effect))
    env.put(com + 0x2C, env.stub(name + " Flip", "stdcall", 3, flip_effect))
    env.put(methods + 0x1C, env.stub(name + " restore", "thiscall", 0, restore_effect))
    return target


def viewport(state="3", level=5, mode=0, has_state=True, has_scene=True, deep=True, seed=0, width=640,
             height=480, clip_count=0, blit=0, flip=0, restore=0, bare=False):
    """setup() for one application object with a state object and a scene chain."""

    def setup(env):
        this = env.object(0x90, "application", fill=0)
        for offset in range(0, 0x90, 4):
            # bare: the words around +0x2c are zero, so only the exact offset decides the tests
            if not (bare and 0x20 <= offset < 0x40):
                env.put(this + offset, 0x11110000 + seed * 0x101 + offset)
        env.put(this + 0x0C, mode)
        env.put(this + 0x68, level)
        env.put(this + 0x6C, 0x77 + seed)
        env.put(this + 0x2C, 0)
        env.put(this + 0x30, 0)
        # Reporting options off: the original reporter still runs on a failing status.
        env.put(0x54139C, 0, 0, 0, 0)
        tokens = {"this": this}
        if has_state:
            state_object = env.object(16, "state-object", fill=0x5A)
            methods = env.object(0x40, "state-vtable", fill=0x6B)
            env.put(state_object, methods)
            env.put(methods + 0x10, env.stub("state-query", "thiscall", 0, sequence(*STATES[state])))
            env.put(this + 0x2C, state_object)
        if has_scene:
            scene = env.object(0x40, "scene", fill=0x3C)
            env.put(this + 0x30, scene)
            if deep:
                clip = env.object(0x40, "clip", fill=0x2D)
                holder = env.object(0x40, "holder", fill=0x4E)
                dims = env.object(0x40, "dims", fill=0x1F)
                fill_owner = env.object(0x40, "fill-owner", fill=0x61)
                env.put(scene + 0x04, holder)
                env.put(scene + 0x24, clip)
                env.put(clip + 0x3C, clip_count)
                env.put(holder + 0x10, dims)
                env.put(holder + 0x14, fill_owner)
                env.put(dims + 0x10, width, height)
                env.put(fill_owner + 0x2C, surface(env, "fill-surface", blit=blit, restore=restore))
                env.put(dims + 0x2C, surface(env, "flip-surface", flip=flip, restore=restore))
                tokens.update(clip=clip, holder=holder, dims=dims)
        return tokens

    return setup


def case(label, function, setup):
    return Case(label, function, setup, receiver=lambda tokens: tokens["this"])


def reaches_set_rect(function, level):
    """The original calls the SetRect import (no stand-in) when the new zoom level is 10 or more."""
    return (function == DECREASE and level - 1 >= 10) or (function == INCREASE and 9 <= level < 10)


def cases(random_source):
    for function, name in ((DECREASE, "decrease"), (INCREASE, "increase")):
        yield case(f"{name}: no state object", function, viewport(has_state=False))
        yield case(f"{name}: no scene", function, viewport(has_scene=False))
        yield case(f"{name}: neither", function, viewport(has_state=False, has_scene=False))
        for state in STATES:
            for level in (-2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 40):
                if reaches_set_rect(function, level):
                    continue
                yield case(f"{name}: state {state} level {level}", function,
                           viewport(state, level, seed=level & 7))
        for level in (2, 5, 8):
            for dims in ((1, 1), (2, 3), (321, 217), (1024, 768), (800, 7), (13, 1000)):
                if reaches_set_rect(function, level):
                    continue
                yield case(f"{name}: level {level} size {dims}", function,
                           viewport("3", level, width=dims[0], height=dims[1], seed=level))
        for blit in (0, FAIL, LOST, (LOST, 0), (0, FAIL), (FAIL, LOST)):
            for flip in (0, FAIL, LOST, (LOST, 0), (0, LOST), (LOST, FAIL)):
                for restore in (0, 1):
                    if restore and LOST in (blit if isinstance(blit, tuple) else (blit,)):
                        continue  # the original's Blt retry then dereferences a null source surface
                    level = random_source.randrange(2, 9)
                    yield case(f"{name}: blit {blit} flip {flip} restore {restore}", function,
                               viewport(random_source.choice(("3", "4", "6")), level,
                                        blit=blit, flip=flip, restore=restore,
                                        width=random_source.randrange(2, 1500),
                                        height=random_source.randrange(2, 1100)))
        for count in (-1, 0):
            yield case(f"{name}: clip count {count}", function, viewport("6", 4, clip_count=count))
        for _ in range(16):
            level = random_source.randrange(-1, 13)
            if reaches_set_rect(function, level):
                continue
            yield case(f"{name}: random level {level}", function, viewport(
                random_source.choice(("3", "4", "6", "other")), level,
                seed=random_source.randrange(0, 200), width=random_source.randrange(2, 1200),
                height=random_source.randrange(2, 900)))
    for function in (DECREASE, INCREASE):
        for state in ("3", "4", "6"):
            for level in (3, 6):
                yield case(f"bare {function:#x} state {state} level {level}", function,
                           viewport(state, level, bare=True))
        yield case(f"bare {function:#x} no scene", function, viewport("3", 4, bare=True, has_scene=False))
        yield case(f"bare {function:#x} no state", function, viewport("3", 4, bare=True, has_state=False))
    for state in STATES:
        yield case(f"bare ready {state}", READY, viewport(state, bare=True))
        yield case(f"bare ready {state} no scene", READY, viewport(state, bare=True, has_scene=False))
    for state in STATES:
        for mode in (0, 1, 0x80000000, 0x100):
            yield case(f"ready: state {state} mode {mode:#x}", READY, viewport(state, mode=mode))
        yield case(f"ready: no state object, state {state}", READY, viewport(state, has_state=False))
    yield case("ready: no state object, no scene", READY, viewport(has_state=False, has_scene=False))
    yield case("ready: no scene", READY, viewport("4", has_scene=False))
    for _ in range(10):
        yield case("ready: random", READY, viewport(random_source.choice(list(STATES)),
                                                   mode=random_source.choice((0, random_source.randrange(1, 1 << 32))),
                                                   seed=random_source.randrange(0, 200)))
