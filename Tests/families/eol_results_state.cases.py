"""Cases for eol_results_state: Results state methods and destructors.

Object graph (all offsets from the original disassembly):

    state S      +0 vtable (slot 0x18)   +4 P4   +0xc A   +0x34 cleared by 0x48f180
                 +0x154 W (listener, vtable slots 0/0x14/0x28/0x30)   +0x15c level
    A            +4 E   +0x28 B
    B            +0x10 string map (buckets +0x14, bucket count +0x18, count +0x1c, block chain +0x24)
                 +0x2c C (timed list owner)
    E -> +0x10 F -> +0x2c G -> +8 H (vtable slot 0x60)
    P4           +8 D (vtable slot 0x1c)  +0x30 Q  +0x68 current level  +0x6c
    Q            +4 R  +0x24 T (rectangle holder)
    R            +0x10 Sx (width +0x10, height +0x14, N2 +0x2c)  +0x14 M1 (N1 +0x2c)

Some paths reach imports that the specification has not declared yet (lstrlenA 0x5469e4,
InterlockedDecrement 0x5469e8, timeGetTime 0x546df0, SetRect 0x546d5c). Cases that need one are
generated only when the specification declares that address, and their setup installs the stand-in
with env.override. The EOL_RESULTS_SPEC environment variable names another specification file.
"""
import json
import os
import random
from pathlib import Path

from clawparity.cases import Case
from clawparity.fixtures import allocate, release

LSTRLEN = 0x5469E4
INTERLOCKED_DEC = 0x5469E8
TIME = 0x546DF0
SETRECT = 0x546D5C
OPERATOR_NEW = 0x4F63EC

GSTR = 0x53499C   # global CString pointer
GBUF = 0x534938   # global C string buffer (zero bytes in the image)
NILPTR = 0x52E1CC  # holds the pointer to the shared empty string data
LEVEL_CELLS = (0x5370C8, 0x5370CC, 0x5370D0, 0x5370D4)
DISTINCT_TIME = 0x1000

FN_DTOR, FN_LOADED, FN_INIT, FN_FINISH = 0x40B0B0, 0x40B140, 0x40B1F0, 0x40B300
FN_DELETING, FN_DESTRUCT = 0x429790, 0x4297B0


def declared():
    here = Path(__file__).resolve().parent if "__file__" in globals() else Path("families")
    path = os.environ.get("EOL_RESULTS_SPEC") or here / "eol_results_state.json"
    spec = json.loads(Path(path).read_text())
    return {int(key, 16) for key in spec.get("callees", {})}


# ---------------------------------------------------------------- stand-ins

def lstrlen_effect(env, call):
    return len(env.cstr(call.arguments[0]))


def interlocked_dec_effect(env, call):
    value = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
    env.put(call.arguments[0], value)
    return value


def time_effect(env, call):
    return DISTINCT_TIME + 0x35 * env.calls_so_far(call.function)


def set_rect_effect(env, call):
    env.put(call.arguments[0], *call.arguments[1:5])
    return 1


def install_imports(env):
    for address, effect in ((LSTRLEN, lstrlen_effect), (INTERLOCKED_DEC, interlocked_dec_effect),
                            (TIME, time_effect), (SETRECT, set_rect_effect)):
        if address in env.fixtures:
            env.override(address, effect)


def recorder(env, result=0, slots=6):
    """A stand-in that logs receiver and three arguments of each call in its own object."""
    log = env.object(16 * slots + 16, "stub-log", fill=0)

    def effect(env, call):
        number = env.calls_so_far(call.function)
        words = (list(call.arguments) + [0, 0, 0])[:3]
        env.put(log + 16 * min(number - 1, slots - 1), call.receiver or 0, *words)
        env.put(log + 16 * slots, number)
        if callable(result):
            return result(env, call, number)
        if isinstance(result, (list, tuple)):
            return result[min(number, len(result)) - 1]
        return result

    return effect


def vtable(env, slots, name="vtable"):
    """slots: {offset: (convention, argc, result)}; returns the table address."""
    table = env.object(0x100, name, fill=0)
    for offset, (convention, argc, result) in slots.items():
        env.put(table + offset, env.stub(f"{name}+{offset:#x}", convention, argc, recorder(env, result)))
    return table


def noise(env, rng, address, size, keep=()):
    for offset in range(0, size, 4):
        if offset not in keep:
            env.put(address + offset, rng.randrange(1, 1 << 32))


# ---------------------------------------------------------------- strings and maps

def hash_key(key):
    value = 0
    for byte in key:
        value = (value * 33 + (byte if byte < 128 else byte - 256)) & 0xFFFFFFFF
    return value


def string_object(env, text, capacity=None, refcount=1, name="cstring"):
    capacity = max(len(text), 3 if capacity is None else capacity)
    block = env.object(12 + capacity + 1 + 3, name, fill=0)
    env.put(block, refcount, len(text), capacity)
    env.write(block + 12, text + b"\0")
    return block + 12


def build_map(env, base, entries, buckets, blocks=0, block_size=16):
    """Fill the map at `base`+0x10. entries: (key, value) with key bytes, or (None, value, bucket)."""
    table = env.object(4 * buckets, "buckets", fill=0) if buckets else 0
    nil = env.get(NILPTR)
    env.put(base + 0x14, table, buckets, len(entries))
    for entry in entries:
        key, value = entry[0], entry[1]
        if key is None:
            index, pointer = entry[2], nil
        else:
            index, pointer = hash_key(key) % buckets, string_object(env, key, name="key")
        slot = table + 4 * index
        assoc = env.object(16, "assoc", words=[env.get(slot), index, pointer, value], fill=0)
        env.put(slot, assoc)
    chain = 0
    for _ in range(blocks):
        chain = env.object(block_size, "block", words=[chain], fill=0)
    env.put(base + 0x24, chain)


# ---------------------------------------------------------------- the whole state

def build(env, seed, level=5, p4_same=False, wobj=True, wret=(0x11, 0x22, 0x33, 0x44), hmode="obj", h60=0,
          s18=0, dobj=True, cmode="none", nodes=((0, 0),), entries=(), buckets=3, blocks=0, chain=True,
          gtext=b"", gmode="nil", glen=3, gcap=15, sjunk=True, jret=0, iret=(0,), rret=1, a_null=False,
          timers=((1, 3),), timer_stamp=0, buffer=None, fail_alloc=False):
    rng = random.Random(seed)
    install_imports(env)
    if fail_alloc:
        env.override(OPERATOR_NEW, allocate(fail=True))
    state = env.object(0x170, "state", fill=0)
    p4 = env.object(0x80, "p4", fill=0)
    noise(env, rng, p4, 0x80, keep=(0x30, 0x68, 0x6C, 8))
    a = env.object(0x40, "a", fill=0)
    noise(env, rng, a, 0x40, keep=(4, 0x28))
    b = env.object(0x80, "b", fill=0)
    tokens = {"s": state, "p4": p4, "a": a, "b": b}

    # -- S
    if sjunk:
        noise(env, rng, state, 0x160, keep=(0, 4, 0xC, 0x2C, 0x3C, 0x40, 0x34, 0x154, 0x15C))
    vt = vtable(env, {0x18: ("thiscall", 0, s18)}, "state-vtable")
    env.put(state, vt)
    env.put(state + 4, p4)
    env.put(state + 0xC, 0 if a_null else a)
    env.put(state + 0x34, rng.randrange(1, 1 << 32))
    env.put(state + 0x15C, level)

    # -- W
    wslot = state + 0x154
    if wobj:
        wvt = vtable(env, {0: ("thiscall", 1, wret[0]), 0x14: ("thiscall", 0, wret[1]),
                           0x28: ("thiscall", 1, wret[2]), 0x30: ("thiscall", 2, wret[3])}, "w-vtable")
        w = env.object(0x20, "w", fill=0)
        env.put(w, wvt, 0x77, 0x88)
        env.put(wslot, w)
        tokens["w"] = w
    decoy = env.object(0x20, "decoy", fill=0)
    env.put(decoy, vtable(env, {o: ("thiscall", 2, 0xDEC0DE) for o in (0, 0x14, 0x28, 0x30)}, "decoy-vtable"))
    env.put(state + 0x150, decoy)
    env.put(state + 0x158, decoy)

    # -- P4 and the display chain
    d = 0
    if dobj:
        d = env.object(0x20, "d", fill=0)
        env.put(d, vtable(env, {0x1C: ("thiscall", 2, 0)}, "d-vtable"))
    env.put(p4 + 8, d)
    clamp = 10 if level >= 10 else 1 if level < 2 else level
    env.put(p4 + 0x68, clamp if p4_same else (clamp % 9) + 1 if clamp < 10 else 3)
    env.put(p4 + 0x6C, rng.randrange(3, 99))
    q = env.object(0x50, "q", fill=0)
    r = env.object(0x40, "r", fill=0)
    sx = env.object(0x40, "sx", fill=0)
    m1 = env.object(0x40, "m1", fill=0)
    t = env.object(0x60, "t", fill=0)
    n1 = env.object(0x20, "n1", fill=0)
    n2 = env.object(0x20, "n2", fill=0)
    j = env.object(8, "j", fill=0)
    i = env.object(8, "i", fill=0)
    env.put(p4 + 0x30, q)
    env.put(q + 4, r)
    env.put(q + 0x24, t)
    env.put(r + 0x10, sx)
    env.put(r + 0x14, m1)
    env.put(sx + 0x10, rng.randrange(200, 1400), rng.randrange(200, 900))
    env.put(sx + 0x2C, n2)
    env.put(m1 + 0x2C, n1)
    env.put(n1, vtable(env, {0x1C: ("thiscall", 0, 1)}, "n1-vtable"))
    env.put(n1 + 8, j)
    env.put(j, vtable(env, {0x14: ("stdcall", 6, jret)}, "j-vtable"))
    env.put(n2, vtable(env, {0x1C: ("thiscall", 0, rret)}, "n2-vtable"))
    env.put(n2 + 8, i)
    env.put(i, vtable(env, {0x2C: ("stdcall", 3, iret)}, "i-vtable"))
    tokens.update(q=q, r=r, sx=sx, t=t)

    # -- E, F, G, H
    e = env.object(0x20, "e", fill=0)
    noise(env, rng, e, 0x20, keep=(0x10,))
    f = env.object(0x40, "f", fill=0)
    noise(env, rng, f, 0x40, keep=(0x2C,))
    g = env.object(0x10, "g", fill=0)
    noise(env, rng, g, 0x10, keep=(8,))
    env.put(a + 4, e)
    env.put(e + 0x10, f)
    env.put(f + 0x2C, g)
    if hmode == "obj":
        h = env.object(8, "h", fill=0)
        env.put(h, vtable(env, {0x60: ("stdcall", 1, h60)}, "h-vtable"))
        env.put(g + 8, h)
    else:
        env.put(g + 8, 0)

    # -- B, C
    env.put(a + 0x28, b)
    c = 0
    if cmode != "none":
        c = env.object(0x90, "c", fill=0)
        env.put(b + 0x2C, c)
        tokens["c"] = c
    if cmode in ("empty", "list"):
        env.put(c + 0x78, 1)
    if cmode == "list":
        previous = 0
        first = 0
        for kids, kret in nodes:
            node = env.object(0x40, "node", fill=0)
            yn = env.object(0x90, "yn", fill=0)
            env.put(yn + 0x78, 1)
            on = env.object(8, "on", fill=0)
            env.put(on, vtable(env, {0x48: ("stdcall", 1, kret)}, "node-vtable"))
            env.put(node + 0xC, on)
            env.put(node + 0x10, yn)
            if previous:
                env.put(previous + 4, node + 4)
                env.put(node + 8, previous + 4)
            else:
                first = node
            previous = node
            child_prev = 0
            for _ in range(kids):
                child = env.object(0x40, "child", fill=0)
                yc = env.object(0x90, "yc", fill=0)
                env.put(yc + 0x78, 1)
                oc = env.object(8, "oc", fill=0)
                env.put(oc, vtable(env, {0x48: ("stdcall", 1, 0)}, "child-vtable"))
                env.put(child + 0xC, oc)
                env.put(child + 0x10, yc)
                if child_prev:
                    env.put(child_prev + 4, child + 4)
                else:
                    env.put(node + 0x30, child + 4)
                child_prev = child
        env.put(c + 4, first + 4)
    if cmode == "timer":
        env.put(c + 0x78, 1)
        env.put(c + 0x7C, timer_stamp)
        previous = 0
        for node_result, _ in timers:
            node = env.object(0x20, "timed", fill=0)
            env.put(node, vtable(env, {0: ("thiscall", 1, node_result)}, "timed-vtable"))
            if previous:
                env.put(previous + 4, node + 4)
                env.put(node + 8, previous + 4)
            else:
                env.put(c + 0xC, node + 4)
            previous = node
        env.put(c + 0x10, previous + 4)

    # -- the map
    if callable(entries):
        entries = entries(env, rng)
    if entries is not None:
        build_map(env, b, entries, buckets, blocks)

    # -- globals
    nil = env.get(NILPTR)
    if buffer is not None:
        env.write(GBUF, buffer + b"\0")
    if gmode == "nil":
        env.put(GSTR, nil)
    elif gmode == "unique":
        env.put(GSTR, string_object(env, bytes(range(65, 65 + glen)), capacity=gcap, name="global-string"))
    elif gmode == "text":
        env.put(GSTR, string_object(env, gtext, name="global-key"))
    elif gmode == "empty":
        env.put(GSTR, string_object(env, b"", capacity=3, name="global-empty"))
    elif gmode == "shared":
        env.put(GSTR, string_object(env, bytes(range(65, 65 + glen)), capacity=gcap, refcount=2, name="global-shared"))
    for cell in LEVEL_CELLS:
        env.put(cell, rng.randrange(1, 1 << 32))
    return tokens


def setup_with(seed, **options):
    return lambda env: build(env, seed, **options)


def state_of(tokens):
    return tokens["s"]


def case(label, function, seed, arguments=(), **options):
    return Case(label, function, setup_with(seed, **options), receiver=state_of, arguments=arguments)


# ---------------------------------------------------------------- 0x40b300 and 0x40b1f0 and 0x40b140

def finish_cases(rng):
    for ret in (0, 1, 0xFFFFFFFF, 0x80004005, rng.randrange(2, 1 << 32), rng.randrange(2, 1 << 32)):
        for a1, a2 in ((0, 0), (1, 2), (rng.randrange(1 << 32), rng.randrange(1 << 32))):
            yield case(f"finish with listener ret {ret:#x} args {a1:#x},{a2:#x}", FN_FINISH, rng.randrange(1 << 30),
                       (a1, a2), wret=(1, 2, 3, ret), cmode="none")
    for a1, a2 in ((0, 0), (5, 6), (rng.randrange(1 << 32), rng.randrange(1 << 32))):
        yield case(f"finish without listener {a1:#x}", FN_FINISH, rng.randrange(1 << 30), (a1, a2), wobj=False,
                   a_null=True)
        yield case(f"finish without listener, chain {a2:#x}", FN_FINISH, rng.randrange(1 << 30), (a1, a2),
                   wobj=False)


def init_cases(rng):
    yield case("init without listener", FN_INIT, rng.randrange(1 << 30), wobj=False, a_null=True)
    yield case("init without listener, graph present", FN_INIT, rng.randrange(1 << 30), wobj=False)
    for hmode, h60 in (("null", 0), ("obj", 0), ("obj", 1), ("obj", 0xFFFFFFFF), ("obj", rng.randrange(2, 1 << 32))):
        for s18 in (0, 1, 0x80004005, rng.randrange(2, 1 << 32)):
            for dobj in (True, False):
                for cmode in ("none", "idle"):
                    yield case(f"init h={hmode}/{h60:#x} s18={s18:#x} d={dobj} c={cmode}", FN_INIT,
                               rng.randrange(1 << 30), hmode=hmode, h60=h60, s18=s18, dobj=dobj, cmode=cmode,
                               wret=(1, rng.randrange(1 << 32), 3, 4))
    if TIME in declared():
        for stamp in (0, DISTINCT_TIME + 0x35 - 1, 0xFFFFFFFF):
            for results in ((1,), (0,), (1, 0, 1)):
                yield case(f"init timed list {results} stamp {stamp:#x}", FN_INIT, rng.randrange(1 << 30),
                           hmode="obj", h60=0, cmode="timer", timers=tuple((x, 0) for x in results),
                           timer_stamp=stamp)


def key_sets(rng):
    """(label, key text, entries, buckets, target index or None)."""
    words = [b"results", b"bonus", b"level", b"sound", b"music", b"Tiles", b"tiles", b"a", b"ab", b"abc", b"abd",
             b"Ab", b"zz", b"\xe9clair", b"long_key_with_many_characters_in_it"]
    for count, buckets in ((1, 1), (3, 1), (4, 3), (6, 7), (9, 17), (5, 2)):
        picks = rng.sample(words, count)
        yield f"{count} keys / {buckets} buckets", picks, buckets


def sequence_effect(items):
    def effect(env, call, number):
        error, value = items[min(number, len(items)) - 1]
        env.put(call.arguments[1], value)
        return error
    return effect


def make_chain(env, rng, items, flag, links, o18=None):
    """Value object Z -> X (+0x10) with O (+0xc) and Y (+0x10); links: tags of the nodes in Y's list."""
    z = env.object(0x20, "value", fill=0)
    noise(env, rng, z, 0x20, keep=(0x10,))
    x = env.object(0x40, "x", fill=0)
    noise(env, rng, x, 0x40, keep=(0xC, 0x10))
    o = env.object(8, "o", fill=0)
    slots = {0x24: ("stdcall", 2, sequence_effect(items))}
    if o18 is not None:
        slots[0x18] = ("stdcall", 2, o18)
    env.put(o, vtable(env, slots, "o-vtable"))
    y = env.object(0x90, "y", fill=0)
    env.put(y + 0x78, flag)
    env.put(x + 0xC, o)
    env.put(x + 0x10, y)
    env.put(z + 0x10, x)
    previous = 0
    for tag, owner_is_x in links:
        node = env.object(0x20, "list-node", fill=0)
        env.put(node + 0xC, tag)
        env.put(node + 0x10, x if owner_is_x else y)
        if previous:
            env.put(previous + 4, node + 4)
            env.put(node + 8, previous + 4)
        else:
            env.put(y + 0xC, node + 4)
        previous = node
    if previous:
        env.put(y + 0x10, previous + 4)
    return z


def loaded_setup(seed, key, picks, buckets, kinds, items, flag=1, links=(), no_table=False, fail_alloc=True,
                 o18=None, **options):
    def setup(env):
        tokens = build(env, seed, entries=None, gmode="none", fail_alloc=fail_alloc, **options)
        rng = random.Random(seed ^ 0x5A5A)
        entries = []
        for pick, kind in zip(picks, kinds):
            if kind == "chain":
                value = make_chain(env, rng, items, flag, links, o18)
                tokens["z"] = value
            elif kind == "null":
                value = 0
            else:
                value = env.object(0x20, "other", fill=0)
                noise(env, rng, value, 0x20)
            entries.append((pick, value))
        build_map(env, tokens["b"], entries, buckets)
        if no_table:
            env.put(tokens["b"] + 0x14, 0, 5, 0)
        env.put(GSTR, string_object(env, key, name="key") if key is not None else env.get(NILPTR))
        return tokens
    return setup


def loaded_cases(rng):
    for p in (0, 1, 0xDEADBEEF, rng.randrange(1 << 32)):
        yield case(f"loaded without listener {p:#x}", FN_LOADED, rng.randrange(1 << 30), (p,), wobj=False,
                   a_null=True, gmode="nil")
    yield case("loaded without listener graph", FN_LOADED, rng.randrange(1 << 30), (0x1234,), wobj=False)
    for gmode in ("nil", "empty"):
        for ret in (0, 1, rng.randrange(2, 1 << 32)):
            yield case(f"loaded empty key {gmode} ret {ret:#x}", FN_LOADED, rng.randrange(1 << 30),
                       (rng.randrange(1 << 32),), gmode=gmode, wret=(1, 2, ret, 4), entries=((b"x", 5),), buckets=1)
    sequences = {
        "first even": [(0, 2)],
        "first error": [(5, 1)],
        "first error code": [(0x80004005, 0)],
        "enter then leave": [(0, 1), (0, 0)],
        "enter, error": [(0, 1), (7, 0)],
        "one iteration": [(0, 1), (0, 1), (0, 0)],
        "two iterations": [(0, 3), (0, 5), (0, 0xFFFFFFF1), (0, 8)],
        "three iterations": [(0, 1), (0, 1), (0, 1), (0, 1), (0, 2)],
        "loop error": [(0, 1), (0, 1), (9, 1)],
        "long loop": [(0, 1)] * 7 + [(0, 0)],
    }
    link_sets = {"no list": (), "list": ((1, True),), "foreign list": ((1, False),),
                 "mixed list": ((1, False), (1, True), (1, False), (1, True), (1, True))}
    for name, items in sequences.items():
        for cmode in ("none", "idle"):
            for flag in (1, 0x80000000):
                for links_name, links in link_sets.items():
                    yield Case(f"loaded {name} c={cmode} flag={flag:#x} {links_name}", FN_LOADED,
                               loaded_setup(rng.randrange(1 << 30), b"results", [b"results"], 3, ["chain"], items,
                                            flag, links, cmode=cmode),
                               receiver=state_of, arguments=(rng.randrange(1 << 32),))
    for cmode in ("none", "idle"):
        yield Case(f"loaded flag 0 c={cmode}", FN_LOADED,
                   loaded_setup(rng.randrange(1 << 30), b"results", [b"results"], 3, ["chain"], [(0, 1), (0, 0)], 0,
                                ((1, True),), cmode=cmode), receiver=state_of, arguments=(5,))
    words = [b"results", b"bonus", b"level", b"sound", b"music", b"Tiles", b"tiles", b"a", b"ab", b"abc", b"abd",
             b"Ab", b"zz", b"\xe9clair", b"long_key_with_many_characters_in_it"]
    items = [(0, 1), (0, 1), (0, 0)]
    for count, buckets in ((1, 1), (3, 1), (4, 3), (6, 7), (9, 17), (5, 2), (2, 2)):
        for round_ in range(3):
            picks = rng.sample(words, count)
            for target in range(count):
                kinds = ["other"] * count
                kinds[target] = "chain"
                yield Case(f"loaded lookup {count} keys/{buckets} buckets target {target} r{round_}", FN_LOADED,
                           loaded_setup(rng.randrange(1 << 30), picks[target], picks, buckets, kinds, items, 1,
                                        ((1, True),)),
                           receiver=state_of, arguments=(rng.randrange(1 << 32),))
            kinds = ["other"] * count
            yield Case(f"loaded missing {count} keys/{buckets} buckets r{round_}", FN_LOADED,
                       loaded_setup(rng.randrange(1 << 30), b"missing-key", picks, buckets, kinds, items),
                       receiver=state_of, arguments=(rng.randrange(1 << 32),))
            kinds = ["null"] * count
            yield Case(f"loaded null value {count} keys/{buckets} buckets r{round_}", FN_LOADED,
                       loaded_setup(rng.randrange(1 << 30), picks[0], picks, buckets, kinds, items),
                       receiver=state_of, arguments=(rng.randrange(1 << 32),))
    yield Case("loaded key without bucket array", FN_LOADED,
               loaded_setup(4242, b"results", [], 1, [], items, no_table=True), receiver=state_of, arguments=(79,))
    if TIME in declared():
        for o18 in (1, 0x80004005):
            for links_name, links in link_sets.items():
                for name in ("enter then leave", "two iterations"):
                    yield Case(f"loaded scheduled with new node o18={o18:#x} {name} {links_name}", FN_LOADED,
                               loaded_setup(rng.randrange(1 << 30), b"results", [b"results"], 3, ["chain"],
                                            sequences[name], 1, links, fail_alloc=False, o18=o18),
                               receiver=state_of, arguments=(rng.randrange(1 << 32),))
        for results in ((1,), (0,), (1, 0, 1)):
            for stamp in (0, 0xFFFFFFFF):
                yield Case(f"loaded timed list {results} stamp {stamp:#x}", FN_LOADED,
                           loaded_setup(rng.randrange(1 << 30), b"results", [b"results"], 3, ["chain"],
                                        [(0, 1), (0, 1), (0, 1), (0, 0)], 1, ((1, True),), cmode="timer",
                                        timers=tuple((x, 0) for x in results), timer_stamp=stamp),
                           receiver=state_of, arguments=(80,))


# ---------------------------------------------------------------- 0x40b0b0, 0x4297b0, 0x429790

def dtor_entries(count, buckets, nulls=False):
    def make(env, rng):
        result = []
        for index in range(count):
            if nulls and index % 2 == 1:
                value = 0
            else:
                value = env.object(0x10, "map-value", fill=0)
                env.put(value, vtable(env, {4: ("thiscall", 1, 0)}, "value-vtable"), rng.randrange(1, 1 << 32))
            result.append((None, value, rng.randrange(buckets) if index >= buckets else index))
        return result
    return make


def dtor_variants(rng):
    base = {"gmode": "nil", "buffer": b""}
    levels = [-7, 0, 1, 2, 3, 5, 8, 9]
    if SETRECT in declared():
        levels += [10, 11, 500]
    yield "plain", dict(base)
    yield "plain no listener", dict(base, wobj=False)
    for level in levels:
        for same in (False, True):
            yield f"level {level} same={same}", dict(base, level=level, p4_same=same)
    for cmode in ("none", "idle", "empty", "list"):
        yield f"c={cmode}", dict(base, cmode=cmode, nodes=((0, 0), (1, 0), (0, 0)) if cmode == "list" else ((0, 0),))
    yield "list with children", dict(base, cmode="list", nodes=((2, 0), (0, 0), (1, 1)))
    for count, buckets, blocks, nulls in ((1, 1, 0, False), (3, 3, 1, False), (4, 2, 2, True), (7, 5, 3, True),
                                          (2, 4, 1, True)):
        yield f"map {count}/{buckets} blocks {blocks}", dict(base, entries=dtor_entries(count, buckets, nulls),
                                                             buckets=buckets, blocks=blocks)
    yield "map with blocks only", dict(base, entries=(), buckets=0, blocks=3)
    yield "map empty with table", dict(base, entries=(), buckets=4, blocks=1)
    for jret, iret, rret in ((0, (0,), 1), (0x80004005, (0x80004005,), 0), (0, (0x887601C2, 0), 1),
                             (0, (0x887601C2, 0x80004005), 1), (0, (0x887601C2,), 0)):
        yield f"display returns {jret:#x}/{iret}/{rret}", dict(base, jret=jret, iret=iret, rret=rret)
    for ret in (0, 1, 0x80004005):
        yield f"listener returns {ret}", dict(base, wret=(ret, ret, ret, ret))
    yield "full", dict(base, level=4, cmode="list", nodes=((1, 0), (0, 0)), entries=dtor_entries(5, 3, True), buckets=3,
                       blocks=2)
    if LSTRLEN in declared():
        for text in (b"x", b"results state", b"0123456789" * 6):
            yield f"buffer from nil {len(text)}", dict(base, buffer=text)
        for glen, gcap, text in ((3, 15, b""), (3, 15, b"hello"), (20, 20, b"x" * 20), (1, 3, b"abc"), (12, 12, b"")):
            yield f"unique global {glen}/{gcap} buffer {len(text)}", dict(base, gmode="unique", glen=glen, gcap=gcap,
                                                                        buffer=text)
        if INTERLOCKED_DEC in declared():
            yield "global too small", dict(base, gmode="unique", glen=2, gcap=3, buffer=b"longer than capacity")
            yield "global shared", dict(base, gmode="shared", glen=4, gcap=15, buffer=b"")
            yield "global shared and too small", dict(base, gmode="shared", glen=4, gcap=5, buffer=b"0123456789")


def dtor_cases(rng):
    if LSTRLEN not in declared():
        return
    for label, options in dtor_variants(rng):
        yield case(f"destroy {label}", FN_DTOR, rng.randrange(1 << 30), **options)


def destruct_cases(rng):
    if LSTRLEN not in declared():
        return
    for label, options in dtor_variants(rng):
        if label.startswith(("level", "map")) and rng.random() < 0.5:
            continue
        yield case(f"destruct {label}", FN_DESTRUCT, rng.randrange(1 << 30), **options)


def deleting_cases(rng):
    if LSTRLEN not in declared():
        return
    flags = (0, 1, 2, 3, 0x100, 0x101, 0xFFFFFF00, 0xFFFFFFFF, rng.randrange(1 << 32), rng.randrange(1 << 32) | 1,
             rng.randrange(1 << 32) & ~1)
    variants = [("plain", {}), ("full", dict(level=4, cmode="list", nodes=((1, 0), (0, 0)),
                                             entries=dtor_entries(3, 2, True), buckets=2, blocks=1)),
                ("no listener", dict(wobj=False))]
    for flag in flags:
        for label, options in variants:
            yield case(f"deleting {label} flag {flag:#x}", FN_DELETING, rng.randrange(1 << 30), (flag,),
                       gmode="nil", buffer=b"", **options)


def cases(random_source):
    rng = random.Random(random_source.randrange(1 << 62))
    yield from finish_cases(rng)
    yield from init_cases(rng)
    yield from loaded_cases(rng)
    yield from dtor_cases(rng)
    yield from destruct_cases(rng)
    yield from deleting_cases(rng)
