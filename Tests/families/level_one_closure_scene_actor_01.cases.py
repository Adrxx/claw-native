"""Cases for level_one_closure_scene_actor_01: Level 1 closure: Scene actor and world object helpers.

Coverage of the structured cases does not depend on the random seed; the seeded draws only vary the
filler words and the extra random geometry.
"""
import random
import struct

from clawparity.cases import Case
from clawparity.fixtures import release, returns

DRAW_BOTH = 0x4C7A90      # copies the 9-word block, then blits the previous rect back
DRAW_REGION = 0x4C7AE0    # blits union / two rects / one rect
DRAW_NOTIFY = 0x4C7CD0    # same decisions, but calls the owned no-op 0x4d56c0
FLAG_NONZERO = 0x4C80A0
CONSTANT_NINE = 0x4C80B0
RELEASE_ACTOR = 0x4C81B0
DELETING = 0x4C97C0
RESET_FULL = 0x4C97E0
RESET_SHORT = 0x4C9810
ALL_READY = 0x4C9890
FLAG_180 = 0x4C9BC0
RESET_ALL = 0x4C9D80
BOTH_READY = 0x4CF080
NOOP = 0x4D56C0

INTERSECT_RECT = 0x546CE0
UNION_RECT = 0x546D94
OPERATOR_DELETE = 0x4F6428
SURFACE_LOST = 0x887601C2
NEG1 = 0xFFFFFFFF
MIN32 = 0x80000000


# ---- the two scripted Win32 rectangle services -------------------------------------------------------------

def _rect(env, address):
    return struct.unpack("<4i", env.read(address, 16))


def _empty(rect):
    return rect[2] <= rect[0] or rect[3] <= rect[1]


def intersect_rect(env, call):
    out, first, second = call.arguments
    a, b = _rect(env, first), _rect(env, second)
    result = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    if _empty(result):
        env.write(out, struct.pack("<4i", 0, 0, 0, 0))
        return 0
    env.write(out, struct.pack("<4i", *result))
    return 1


def union_rect(env, call):
    out, first, second = call.arguments
    a, b = _rect(env, first), _rect(env, second)
    if _empty(a) and _empty(b):
        result, answer = (0, 0, 0, 0), 0
    elif _empty(a):
        result, answer = b, 1
    elif _empty(b):
        result, answer = a, 1
    else:
        result, answer = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])), 1
    env.write(out, struct.pack("<4i", *result))
    return answer


def rect_services(env):
    env.override(INTERSECT_RECT, intersect_rect)
    env.override(UNION_RECT, union_rect)


# ---- object builders ---------------------------------------------------------------------------------------

def filler(rng, size):
    """Distinct non-zero words so that a wrong offset or width changes the result."""
    return struct.pack(f"<{size // 4}I", *(rng.getrandbits(32) | 0x00010001 for _ in range(size // 4)))


def make_object(env, rng, size, name, fields=None):
    token = env.object(size, name)
    env.write(token, filler(rng, size))
    for offset, value in (fields or {}).items():
        env.put(token + offset, value)
    return token


def surfaces(env, rng, actor, blts=(), restore=1, null_source=False, mutate=None):
    """Destination and source surface wrappers with stand-in Blt / BltFast / Restore methods that log what they see."""
    log = env.object(16 + 64 * 8, "blit-log", fill=0)

    def record(kind, rects):
        def effect(env, call):
            count = env.get(log)
            words = [kind, call.receiver] + list(call.arguments) + [0] * (6 - len(call.arguments))
            for pointer in rects(call.arguments) if call.arguments else ():
                words.extend(struct.unpack("<4I", env.read(pointer, 16)))
            words += [0] * (16 - len(words))
            if count < 8:
                env.write(log + 16 + 64 * count, struct.pack("<16I", *words[:16]))
            env.put(log, count + 1)
            if kind == 3:
                return restore
            index = env.calls_so_far(call.function) - 1
            if mutate is not None and kind == 1 and index == 0:
                env.put(actor + 0xA4, *mutate[:2])
                env.put(actor + 0xBC, *mutate[2:])
            return blts[index] if index < len(blts) else 0
        return effect

    blt = env.stub("IDirectDrawSurface::Blt", "stdcall", 6, record(1, lambda a: (a[1], a[3])))
    fast = env.stub("IDirectDrawSurface::BltFast", "stdcall", 6, record(2, lambda a: (a[4],)))
    lost = env.stub("DirectDrawSurface::Restore", "thiscall", 0, record(3, lambda a: ()))
    interface = env.object(8, "dest-interface", words=[env.object(0x28, "dest-vtable", fill=0)])
    methods = env.get(interface)
    env.put(methods + 0x14, blt)
    env.put(methods + 0x1C, fast)
    wrapper_methods = env.object(0x28, "wrapper-vtable", fill=0)
    env.put(wrapper_methods + 0x1C, lost)
    destination_wrapper = make_object(env, rng, 16, "dest-wrapper", {0: wrapper_methods, 8: interface})
    source_wrapper = make_object(env, rng, 16, "source-wrapper", {8: make_object(env, rng, 8, "source-interface")})
    destination = make_object(env, rng, 0x40, "dest-surface", {0x2C: destination_wrapper})
    source = make_object(env, rng, 0x40, "source-surface", {0x2C: 0 if null_source else source_wrapper})
    return {"destination": destination, "source": source, "log": log}


def draw_actor(env, rng, flag_a, flag_b, rect_a, rect_b):
    """Actor with a primary block at +0x18..+0x3b and a mirrored previous block at +0xa4..+0xc7."""
    actor = make_object(env, rng, 0x1A0, "actor")
    env.put(actor + 0x18, rng.randrange(-300, 300), rng.randrange(-300, 300))
    env.put(actor + 0x20, *rect_a)
    env.put(actor + 0x30, rng.randrange(1, 400), rng.randrange(1, 400), flag_a)
    env.put(actor + 0xA4, rng.randrange(-300, 300), rng.randrange(-300, 300))
    env.put(actor + 0xAC, *rect_b)
    env.put(actor + 0xBC, rng.randrange(1, 400), rng.randrange(1, 400), flag_b)
    return actor


def draw_case(label, function, flag_a, flag_b, rect_a, rect_b, seed, **surface_options):
    def setup(env):
        rng = random.Random(seed)
        rect_services(env)
        actor = draw_actor(env, rng, flag_a, flag_b, rect_a, rect_b)
        tokens = surfaces(env, rng, actor, **surface_options)
        tokens["actor"] = actor
        return tokens
    arguments = (lambda t: t["destination"], lambda t: t["source"])
    if function != DRAW_BOTH:
        arguments += (seed | 0x40000000,)  # the third stack argument is never read
    return Case(label, function, setup, receiver=lambda t: t["actor"], arguments=arguments)


RECT_CONFIGS = {
    "partial overlap": ((10, 20, 50, 60), (30, 40, 90, 100)),
    "overlap swapped": ((30, 40, 90, 100), (10, 20, 50, 60)),
    "disjoint": ((0, 0, 10, 10), (100, 100, 150, 160)),
    "touching edge": ((0, 0, 10, 10), (10, 0, 20, 10)),
    "touching bottom": ((0, 0, 10, 10), (0, 10, 10, 25)),
    "contained": ((0, 0, 100, 100), (20, 30, 40, 50)),
    "negative": ((-50, -40, -5, -3), (-30, -20, 10, 10)),
    "identical": ((5, 6, 77, 88), (5, 6, 77, 88)),
    "empty first": ((40, 40, 20, 20), (0, 0, 100, 100)),
    "empty second": ((0, 0, 100, 100), (40, 40, 40, 90)),
    "both zero": ((0, 0, 0, 0), (0, 0, 0, 0)),
    "extreme": ((-0x7FFFFF00, -5, 0x7FFFFFF0, 5), (-9, -0x7FFFFF00, 9, 0x7FFFFFF0)),
}
FLAGS = (NEG1, 0, 5)


def random_rect(rng):
    left, top = rng.randrange(-200, 200), rng.randrange(-200, 200)
    return (left, top, left + rng.randrange(-20, 120), top + rng.randrange(-20, 120))


def draw_cases(random_source):
    for function, name in ((DRAW_REGION, "region"), (DRAW_NOTIFY, "notify")):
        for flag_a in FLAGS:
            for flag_b in FLAGS:
                for config, (rect_a, rect_b) in RECT_CONFIGS.items():
                    yield draw_case(f"{name} a={flag_a:#x} b={flag_b:#x} {config}", function, flag_a, flag_b,
                                    rect_a, rect_b, random_source.getrandbits(32))
        for index in range(24):
            rng = random.Random(random_source.getrandbits(32))
            yield draw_case(f"{name} random both active {index}", function, rng.getrandbits(32) | 1,
                            rng.getrandbits(32) & 0x7FFFFFFF, random_rect(rng), random_rect(rng),
                            random_source.getrandbits(32))
    # Blt result handling in 0x4c7ae0 (through the original wrapper 0x4b9ce0): lost surface, restore, retry.
    for config in ("partial overlap", "disjoint"):
        rect_a, rect_b = RECT_CONFIGS[config]
        for blts, restore in (((SURFACE_LOST, 0, SURFACE_LOST, 0), 1), ((SURFACE_LOST, SURFACE_LOST), 0), ((0, SURFACE_LOST, 0), 1)):
            yield draw_case(f"region {config} blt {blts!r} restore {restore}", DRAW_REGION, 3, 4, rect_a, rect_b,
                            random_source.getrandbits(32), blts=blts, restore=restore)
    for flag_a, flag_b in ((3, NEG1), (NEG1, 4)):
        yield draw_case(f"region single rect lost surface {flag_a:#x}/{flag_b:#x}", DRAW_REGION, flag_a, flag_b,
                        (1, 2, 30, 40), (5, 6, 70, 80), random_source.getrandbits(32), blts=(SURFACE_LOST, 0), restore=1)
    for flag_a, flag_b in ((3, 4), (3, NEG1), (NEG1, 4)):
        for config in ("partial overlap", "disjoint"):
            rect_a, rect_b = RECT_CONFIGS[config]
            yield draw_case(f"region without source surface {flag_a:#x}/{flag_b:#x} {config}", DRAW_REGION, flag_a,
                            flag_b, rect_a, rect_b, random_source.getrandbits(32), null_source=True)
    # The first blit changes the geometry that the second blit reads afterwards.
    for config in ("disjoint", "negative"):
        rect_a, rect_b = RECT_CONFIGS[config]
        yield draw_case(f"region geometry changes during first blit {config}", DRAW_REGION, 1, 2, rect_a, rect_b,
                        random_source.getrandbits(32), mutate=(0x1111, 0x2222, 0x33, 0x44))
    # 0x4c7a90
    for flag in (NEG1, 0, 1, 0x7FFFFFFF, MIN32):
        for blts, restore in (((), 1), ((SURFACE_LOST, 0), 1), ((SURFACE_LOST,), 0)):
            yield draw_case(f"copy block flag {flag:#x} blt {blts!r} restore {restore}", DRAW_BOTH, flag, 7,
                            (11, 22, 33, 44), (55, 66, 77, 88), random_source.getrandbits(32), blts=blts,
                            restore=restore)
    for index in range(30):
        rng = random.Random(random_source.getrandbits(32))
        yield draw_case(f"copy block random {index}", DRAW_BOTH, rng.choice((NEG1, rng.getrandbits(32))),
                        rng.getrandbits(32), random_rect(rng), random_rect(rng), random_source.getrandbits(32))


# ---- single-object helpers ---------------------------------------------------------------------------------

def object_case(label, function, seed, fields, size=0x1A0, arguments=()):
    def setup(env):
        return {"object": make_object(env, random.Random(seed), size, "object", fields(env) if callable(fields) else fields)}
    return Case(label, function, setup, receiver=lambda t: t["object"], arguments=arguments)


def word_values(random_source):
    return (0, 1, 2, 0xFF, 0x100, 0x10000, 0x80000000, NEG1, random_source.getrandbits(32) | 1,
            random_source.getrandbits(32) | 1)


def simple_cases(random_source):
    for value in word_values(random_source):
        yield object_case(f"flag at +0x10 = {value:#x}", FLAG_NONZERO, random_source.getrandbits(32), {0x10: value})
        yield object_case(f"flag at +0x180 = {value:#x}", FLAG_180, random_source.getrandbits(32), {0x180: value})
    yield Case("constant nine", CONSTANT_NINE)
    yield Case("constant nine with stray receiver", CONSTANT_NINE, receiver=0x1234)
    for index in range(3):
        yield object_case(f"full reset {index}", RESET_FULL, random_source.getrandbits(32), {})
        yield object_case(f"short reset {index}", RESET_SHORT, random_source.getrandbits(32), {})
        yield Case(f"no-op with arguments {index}", NOOP, receiver=random_source.getrandbits(32),
                   arguments=tuple(random_source.getrandbits(32) for _ in range(3)))
    yield object_case("full reset of already reset object", RESET_FULL, 5, {0: 0x50BECC, 4: NEG1, 8: 0, 0xC: 0, 0x20: MIN32, 0x38: NEG1, 0x4C: MIN32})
    yield object_case("short reset of already reset object", RESET_SHORT, 6, {0x4C: MIN32, 0x20: MIN32, 0x38: NEG1})

    # 0x4c9890: all four conditions; 0x4cf080: its last two.
    for field_6c in (0, 1):
        for field_68 in (0, 1):
            for field_c in (0, 1):
                for field_4 in (NEG1, 0, 1):
                    seed = random_source.getrandbits(32)
                    nonzero = lambda: random_source.getrandbits(32) | 1
                    fields = {0x6C: nonzero() if field_6c else 0, 0x68: nonzero() if field_68 else 0,
                              0xC: nonzero() if field_c else 0, 4: field_4}
                    yield object_case(f"all-ready 6c={field_6c} 68={field_68} c={field_c} 4={field_4:#x}", ALL_READY, seed, fields)
    for field_c in (0, 1, 0x7FFFFFFF, NEG1):
        for field_4 in (NEG1, 0, 1, MIN32, 0x7FFFFFFF):
            yield object_case(f"both-ready c={field_c:#x} 4={field_4:#x}", BOTH_READY, random_source.getrandbits(32),
                              {0xC: field_c, 4: field_4})
    for _ in range(6):
        yield object_case("both-ready random", BOTH_READY, random_source.getrandbits(32), {})
        yield object_case("all-ready random", ALL_READY, random_source.getrandbits(32), {})


# ---- 0x4c81b0, 0x4c97c0, 0x4c9d80 --------------------------------------------------------------------------

def child(env, rng, slot, stub_name, result, effect=None):
    """An object whose vtable slot `slot` is a stand-in virtual method."""
    stub = env.stub(stub_name, "thiscall", 1, effect or returns(result))
    methods = env.object(16, "vtable", words=[0x1000, 0x2000, 0x3000, 0x4000])
    env.put(methods + slot, stub)
    return make_object(env, rng, 16, stub_name, {0: methods})


def release_actor_case(label, seed, has_buffer, has_child, flag, retarget=False, child_result=0):
    def setup(env):
        rng = random.Random(seed)
        actor = make_object(env, rng, 0x30, "actor", {0x10: flag})
        buffer = env.object(24, "buffer", fill=0x5A) if has_buffer else 0
        owned = child(env, rng, 0, "deleting-destructor", child_result) if has_child else 0
        env.put(actor + 0x14, buffer)
        env.put(actor + 0x18, owned)
        if retarget:
            replacement = child(env, rng, 0, "replacement-destructor", 0x77)

            def delete_and_swap(env, call):
                if call.arguments[0]:
                    env.release(call.arguments[0])
                env.put(actor + 0x18, replacement)
                return 0
            env.override(OPERATOR_DELETE, delete_and_swap)
        return {"object": actor}
    return Case(label, RELEASE_ACTOR, setup, receiver=lambda t: t["object"])


def release_cases(random_source):
    for has_buffer in (False, True):
        for has_child in (False, True):
            for flag in (0, 1, 0xDEADBEEF):
                yield release_actor_case(f"release actor buffer={has_buffer} child={has_child} flag={flag:#x}",
                                         random_source.getrandbits(32), has_buffer, has_child, flag,
                                         child_result=random_source.getrandbits(32))
    yield release_actor_case("delete callback replaces the owned child", random_source.getrandbits(32), True, True, 3,
                             retarget=True)
    yield release_actor_case("delete callback installs a child on an empty slot", random_source.getrandbits(32), True,
                             False, 3, retarget=True)


def deleting_case(label, seed, flags):
    def setup(env):
        return {"object": make_object(env, random.Random(seed), 0x60, "deleted-object")}
    return Case(label, DELETING, setup, receiver=lambda t: t["object"], arguments=(flags,))


def deleting_cases(random_source):
    for flags in (0, 1, 2, 3, 0xFE, 0xFF, 0x100, 0x101, 0xFFFFFF00, 0xFFFFFF01, 0xFFFFFFFE, 0xFFFFFFFF):
        yield deleting_case(f"deleting destructor flags {flags:#x}", random_source.getrandbits(32), flags)
    for _ in range(6):
        yield deleting_case("deleting destructor random flags", random_source.getrandbits(32), random_source.getrandbits(32))


def reset_all_case(label, seed, present, order_effects=(), results=(0, 0, 0)):
    """present: which of the objects at +0x6c, +0x70 and +0x78 exist. order_effects: ('field', value-kind) per child."""
    def setup(env):
        rng = random.Random(seed)
        actor = make_object(env, rng, 0x188, "actor")
        spare = child(env, rng, 4, "spare-destructor", 0x99)
        children = []
        for index, offset in enumerate((0x6C, 0x70, 0x78)):
            effect = None
            for target, kind in order_effects:
                if target == index:
                    effect = swap_effect(actor, spare, kind)
            children.append(child(env, rng, 4, f"destructor-{offset:#x}", results[index], effect) if present[index] else 0)
        for offset, value in zip((0x6C, 0x70, 0x78), children):
            env.put(actor + offset, value)
        return {"object": actor}
    return Case(label, RESET_ALL, setup, receiver=lambda t: t["object"])


def swap_effect(actor, spare, kind):
    """A destructor that rewrites the pointers read after it, or the slot being cleared."""
    def effect(env, call):
        if kind == "next-null":
            env.put(actor + 0x70, 0)
        elif kind == "next-spare":
            env.put(actor + 0x70, spare)
        elif kind == "last-null":
            env.put(actor + 0x78, 0)
        elif kind == "last-spare":
            env.put(actor + 0x78, spare)
        elif kind == "both-spare":
            env.put(actor + 0x70, spare)
            env.put(actor + 0x78, spare)
        elif kind == "self-field":
            env.put(actor + 0x6C, spare)
            env.put(actor + 0xC4, 0x5151)
        return 0x31
    return effect


def reset_all_cases(random_source):
    for mask in range(8):
        present = tuple(bool(mask & bit) for bit in (1, 2, 4))
        yield reset_all_case(f"reset all present={mask:03b}", random_source.getrandbits(32), present,
                             results=tuple(random_source.getrandbits(32) for _ in range(3)))
    for kind in ("next-null", "next-spare", "last-null", "last-spare", "both-spare", "self-field"):
        for present in ((True, True, True), (True, True, False), (True, False, True)):
            yield reset_all_case(f"reset all first destructor {kind} present={present}", random_source.getrandbits(32),
                                 present, order_effects=((0, kind),))
    for kind in ("last-null", "last-spare", "next-spare"):
        yield reset_all_case(f"reset all second destructor {kind}", random_source.getrandbits(32), (True, True, True),
                             order_effects=((1, kind),))
    yield reset_all_case("reset all third destructor writes its own slot", random_source.getrandbits(32), (True, True, True),
                         order_effects=((2, "self-field"),))


def cases(random_source):
    yield from draw_cases(random_source)
    yield from simple_cases(random_source)
    yield from release_cases(random_source)
    yield from deleting_cases(random_source)
    yield from reset_all_cases(random_source)
