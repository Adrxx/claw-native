"""Cases for help_state: Help screen state (F1 and in-game Help)."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns, sequence, store_words  # noqa: F401

# Owned functions.
INIT, DESTROY, ENTER, FADE, UPDATE, REDRAW, RESUME, KEY, MOUSE = (
    0x449870, 0x449930, 0x449940, 0x4499D0, 0x449A60, 0x449B30, 0x449B70, 0x449BD0, 0x449C10)

# Declared fixtures.
RAND = 0x4A3050
OPERATOR_NEW = 0x4F63EC
SET_CURSOR = 0x546CD8
POST_MESSAGE = 0x546D50
SHOW_CURSOR = 0x546D54
PEEK_MESSAGE = 0x546CAC
TIME_GET_TIME = 0x546DF0
KEY_STATE = 0x546CE4

INPUT_GLOBAL = 0x537200
HASH_MODE = 0x540E88
VERTICAL_BLANK = 0x541374
SCREEN_TYPE = 0x504358  # the resource type id the screen lookups ask for


# ---------------------------------------------------------------------------
# Resource tree, built the way the independent resource_namespace cases build it.
# ---------------------------------------------------------------------------
def string(env, value, name="string"):
    # One byte of prefix backing: the resource scanner reads s[-1] for an empty path.
    return env.object(len(value) + 10, name, data=b"|" + value + b"\0\xa7\xb9\xc3\xd5\xe7\xf1\x93\x85") + 1


def chain_node(env, value, tbl=0, bucket=0, following=0):
    p = env.object(32, "bucket node", fill=0x91)
    env.put(p + 4, following + 4 if following else 0)
    env.put(p + 12, tbl, bucket, value)
    return p


def table(env, count, entries=()):
    t = env.object(8, "table")
    buckets = env.object(max(1, count) * 16, "buckets", fill=0x63)
    env.put(t, count, buckets)
    for i in range(max(1, count)):
        env.put(buckets + 16 * i + 8, 0)
    for index, values in entries:
        following = 0
        for value in reversed(values):
            following = chain_node(env, value, t, index, following)
        env.put(buckets + 16 * index + 8, following + 4 if following else 0)
    return t


def embed(env, owner, offset, t):
    env.put(owner + offset, env.get(t), env.get(t + 4))


def named(env, name, size=84):
    p = env.object(size, "named payload", fill=0x37)
    env.put(p, string(env, name, "payload name"))
    return p


def dirnode(env, name, children=(), resources=(), type_id=SCREEN_TYPE):
    """A directory: named child directories (table at +0x3c) and typed resources (type table at +0x44)."""
    p = named(env, name)
    grouped = {}
    for child_name, child in children:
        grouped.setdefault(len(child_name) % 5, []).append(child)
    embed(env, p, 0x3C, table(env, 5, grouped.items()))
    ty = env.object(64, "resource type", fill=0x57)
    env.put(ty, type_id)
    grouped = {}
    for resource_name, resource in resources:
        grouped.setdefault(len(resource_name) % 19, []).append(resource)
    embed(env, ty, 0x24, table(env, 19, grouped.items()))
    embed(env, ty, 0x1C, table(env, 5))
    types = table(env, 9, [(type_id % 9, [ty])])
    embed(env, p, 0x44, types)
    env.write(ty + 4, env.read(chain_node(env, ty, types, type_id % 9, 0), 24))
    return p


def screen_resource(env, name, picture):
    """A resource whose bytes are `picture`: the original reads it as a bitmap header."""
    res = named(env, name, 0x40)
    block = env.object(0x40, "resource block", fill=0)
    data = env.object(len(picture) + 16, "resource bytes", fill=0)
    env.write(data, picture)
    env.put(block + 0x20, data)
    env.put(res + 0x14, len(picture), 0, 0, 0, block, 0)  # size, no buffer, ..., block at +0x24, offset
    return res


# ---------------------------------------------------------------------------
# Scripted fixtures.
# ---------------------------------------------------------------------------
def clock(*values):
    """timeGetTime: the listed readings in order, then the last one plus 1000 per extra reading."""
    def effect(env, call):
        n = env.calls_so_far(call.function) - 1
        if n < len(values):
            return values[n] & 0xFFFFFFFF
        return (values[-1] + 1000 * (n - len(values) + 1)) & 0xFFFFFFFF
    return effect


def keys(pressed):
    """GetAsyncKeyState: the listed result for the key codes in `pressed`, otherwise 0."""
    return lambda env, call: pressed.get(call.arguments[0], 0)


def counts(*values):
    """ShowCursor / PeekMessageA: the listed results, then the last one."""
    return sequence(*[x & 0xFFFFFFFF for x in values])


def defaults(env, v, overrides=None):
    """Every scripted fixture needs an effect in every case."""
    table_ = {
        RAND: returns(v["rand"]),
        SET_CURSOR: returns(v["cursor"]),
        POST_MESSAGE: returns(v["post"]),
        SHOW_CURSOR: counts(-1),
        PEEK_MESSAGE: returns(0),
        TIME_GET_TIME: clock(v["time"]),
        KEY_STATE: returns(0),
    }
    table_.update(overrides or {})
    for address, effect in table_.items():
        env.override(address, effect)
    env.put(HASH_MODE, 0)
    env.put(VERTICAL_BLANK, 0)


def scalars(rnd):
    """Random scalars a case needs, drawn when the case is generated so both sides see the same ones."""
    return {
        "hwnd": rnd.getrandbits(31) | 0x10000,
        "rand": rnd.getrandbits(32),
        "cursor": rnd.getrandbits(32) | 1,
        "post": rnd.getrandbits(32),
        "time": rnd.randrange(1000, 90000),
        "junk": rnd.getrandbits(32),
        "size": (rnd.randrange(300, 1200), rnd.randrange(300, 900)),
        "level": rnd.randrange(1, 60),
        "extra": rnd.getrandbits(32),
        "pic": (rnd.randrange(8, 25), rnd.randrange(4, 11)),
    }


# ---------------------------------------------------------------------------
# The object web the Help state works on.
# ---------------------------------------------------------------------------
def com(env, name, methods):
    """A COM object whose vtable holds the given stubs: methods is {byte offset: (argc, effect)}."""
    table_ = env.object(0x90, name + " vtable", fill=0)
    for offset, (argc, effect) in methods.items():
        env.put(table_ + offset, env.stub(f"{name}+{offset:#x}", "stdcall", argc, effect))
    obj = env.object(16, name, fill=0)
    env.put(obj, table_)
    return obj


def thiscall_table(env, name, methods, size=0x80):
    """A vtable of thiscall stubs: methods is {byte offset: (argc, effect)}. Returns the table."""
    table_ = env.object(size, name + " vtable", fill=0)
    for offset, (argc, effect) in methods.items():
        env.put(table_ + offset, env.stub(f"{name}+{offset:#x}", "thiscall", argc, effect))
    return table_


def effect_of(value):
    return value if callable(value) else returns(value)


def surface_wrapper(env, v, name, lost=0, restore=0, flip=0, blt=0, no_interface=False):
    """A surface wrapper Q: +8 is the COM surface, +0x14/+0x18 its size."""
    if no_interface:
        iface = 0
    else:
        iface = com(env, name + " interface", {
            0x14: (6, effect_of(blt)),
            0x2C: (3, effect_of(flip)),
            0x60: (1, effect_of(lost)),
            0x6C: (1, effect_of(restore)),
        })
    q = env.object(0xC0, name, fill=0)
    env.put(q + 8, iface)
    env.put(q + 0x14, v["size"][0], v["size"][1])
    return q


def display(env, v, name, p2_load=1, **q_options):
    """A display D with its two page wrappers P1 and P2. Returns (d, p1, p2, q1, q2)."""
    q1 = surface_wrapper(env, v, name + " primary", **q_options)
    q2 = surface_wrapper(env, v, name + " back", **q_options)
    p1 = env.object(0x40, name + " page 1", fill=0)
    p2vt = thiscall_table(env, name + " page 2", {0x30: (1, effect_of(p2_load))})
    p2 = env.object(0x40, name + " page 2", fill=0)
    env.put(p2, p2vt)
    env.put(p1 + 0x2C, q1)
    env.put(p2 + 0x2C, q2)
    d = env.object(0x40, name, fill=0)
    env.put(d + 0x10, p1, p2, 0)
    return d, p1, p2, q1, q2


def palette(env, v, active=0, duration=700, started=4000, last=0xFFFF, start_index=3, count=0x10,
            source=True, set_entries=0, hook=None):
    """The palette object PL. Its COM palette's GetEntries and SetEntries succeed."""
    set_effect = hook if hook is not None else returns(set_entries)
    pal = com(env, "palette", {0x10: (5, returns(0)), 0x18: (5, set_effect)})
    pl = env.object(0x40, "palette state", fill=0)
    bufs = []
    for index in range(4):
        buf = env.object(0x400, f"palette buffer {index}", fill=0)
        env.write(buf, bytes((v["junk"] * (k + 3) + index * 17 + k // 3 + (k * k >> 3)) & 0xFF for k in range(0x400)))
        bufs.append(buf)
    env.put(pl + 4, pal)
    env.put(pl + 0xC, bufs[0])
    env.put(pl + 0x10, bufs[1])
    env.put(pl + 0x14, bufs[2] if source else 0)
    env.put(pl + 0x18, bufs[3])
    env.put(pl + 0x1C, 0x55AA33CC)
    env.put(pl + 0x20, duration, started, last, start_index, count, active)
    return pl


def screen_image(env, pl, f_calls=1):
    """F, the screen image: a vtable (+0x34 is the one the original calls) and the palette at +0x10."""
    vt = thiscall_table(env, "image", {0x34: (0, returns(f_calls))})
    f = env.object(0x40, "image", fill=0)
    env.put(f, vt)
    env.put(f + 0x10, pl)
    return f


def resource_tree(env, v, o):
    """Archive R holding STATES_HELP (SCREENS with the HELP picture, SOUNDS), CLAW and LEVEL nodes."""
    picture = bytearray(0x90)
    for k in range(len(picture)):
        picture[k] = (v["junk"] >> (k % 24)) & 0xFF
    picture[0x41] = o.get("picture_planes", 0)
    if o.get("deep"):
        w, h = v["pic"]
        picture = bytearray(0x80 + w * h)
        for k in range(len(picture)):
            picture[k] = ((v["junk"] >> (k % 24)) * 7 + k) & 0x7F
        picture[4:12] = bytes([0, 0, 0, 0, (w - 1) & 0xFF, (w - 1) >> 8, (h - 1) & 0xFF, (h - 1) >> 8])
        picture[0x41] = 1
    if o.get("screen", True):
        screens = dirnode(env, b"SCREENS", resources=[(b"HELP", screen_resource(env, b"HELP", bytes(picture)))])
    else:
        screens = dirnode(env, b"SCREENS", resources=[(b"OTHER", screen_resource(env, b"OTHER", bytes(picture)))])
    children = []
    if o.get("screens_dir", True):
        children.append((b"SCREENS", screens))
    if o.get("sounds_dir", True):
        children.append((b"SOUNDS", dirnode(env, b"SOUNDS")))
    help_node = dirnode(env, b"HELP", children=children)
    claw_node = dirnode(env, b"CLAW")
    root_children = []
    # a name is split at every character that is not a letter, digit or one of " !\"#$%&'()*+,-." (so
    # STATES_HELP is the directory STATES and, inside it, HELP)
    states = dirnode(env, b"STATES", children=[(b"HELP", help_node)] if o.get("help_node", True) else [])
    if o.get("states_dir", True):
        root_children.append((b"STATES", states))
    if o.get("claw_node", True):
        root_children.append((b"CLAW", claw_node))
    for n in o.get("levels", ()):
        name = b"LEVEL%d" % n
        root_children.append((name, dirnode(env, name)))
    root = dirnode(env, b"ROOT", children=root_children)
    r = env.object(0x30, "archive", fill=0x5A)
    env.put(r + 0x24, root)
    return r, help_node, claw_node


def deep_graphics(env, v, t, o):
    """Let the surface creation of the original succeed: DirectDraw hands out one surface that reports the size
    of the picture and a pixel block the picture is decoded into."""
    w, h = v["pic"]
    pitch = w + 4
    pixels = env.object(pitch * h + 16, "pixels", fill=0)

    def describe(env, call):
        desc = call.arguments[1]
        env.put(desc + 8, h, w, pitch)
        env.put(desc + 0x54, 8)
        return 0

    def lock(env, call):
        env.put(call.arguments[2] + 0x24, pixels)
        return 0

    surface = com(env, "dd surface", {0x14: (6, returns(0)), 0x58: (2, describe), 0x64: (5, lock),
                                      0x80: (2, returns(0))})

    def create(env, call):
        env.put(call.arguments[2], surface)
        return 0

    dd = com(env, "direct draw", {0x18: (4, create)})
    g1 = t["g1"]
    env.put(g1, dd)
    env.put(g1 + 0x474, 8)
    env.put(g1 + 0x3B8 + 0x18, 5)
    paper = env.object(0x40, "paper", fill=0)
    env.put(paper + 0x14, v["size"][0] + 3, v["size"][1] + 5)  # not the size of the screen
    t["paper"] = paper
    t["surface"] = surface
    t["pixels"] = pixels


def build(env, v, **o):
    """The whole web. Every option is optional."""
    t = {"v": v}
    pl = palette(env, v, active=o.get("active", 0), duration=o.get("duration", 700),
                 started=o.get("started", 4000), last=o.get("last", 0xFFFF),
                 start_index=o.get("start_index", 3), count=o.get("count", 0x10), source=o.get("source", True),
                 set_entries=o.get("set_entries", 0), hook=o.get("palette_hook"))
    f = screen_image(env, pl) if o.get("f", True) else 0
    t["pl"], t["f"] = pl, f
    d, p1, p2, q1, q2 = display(env, v, "display", p2_load=o.get("load", 1),
                                lost=o.get("lost", 0), restore=o.get("restore", 0),
                                flip=o.get("flip", 0), blt=o.get("blt", 0),
                                no_interface=o.get("no_interface", False))
    if o.get("d_extra"):
        # a third page wrapper at D+0x18, as 0x4ca930 checks it
        q3 = surface_wrapper(env, v, "third", lost=o.get("lost3", 0), restore=o.get("restore3", 0))
        p3 = env.object(0x40, "page 3", fill=0)
        env.put(p3 + 0x2C, q3)
        env.put(d + 0x18, p3)
        t["p3"] = p3
    if o.get("p1_null"):
        env.put(d + 0x10, 0)
    t.update(d=d, p1=p1, p2=p2, q1=q1, q2=q2)
    # sound manager
    m = env.object(0x40, "sound manager", fill=0)
    ll = 0
    if o.get("sound_list") is not None:
        ll = env.object(0x90, "sound list", fill=0)
        env.put(ll + 0x7C, o.get("sound_clock", 5))
        if o["sound_list"] == "element":
            evt = thiscall_table(env, "sound element", {0: (1, returns(o.get("element_result", 1)))})
            element = env.object(16, "sound element", fill=0)
            env.put(element, evt)
            env.put(ll + 0xC, element + 4)
            t["element"] = element
    if o.get("sound_active"):
        # the list is live and holds one buffer, so the original polls its status (a COM call)
        if not ll:
            ll = env.object(0x90, "sound list", fill=0)
        owner = env.object(0x90, "sound owner", fill=0)
        env.put(owner + 0x78, 1)
        buf = com(env, "sound buffer", {0x48: (1, returns(0))})
        entry = env.object(0x40, "sound entry", fill=0)
        env.put(entry + 0xC, buf, owner)
        env.put(ll + 4, entry + 4)
        env.put(ll + 0x78, 1)
        t["entry"] = entry
    env.put(m + 0x2C, ll, o.get("sound_flag", 0))
    t["m"], t["l"] = m, ll
    # graphics services
    gfx_vt = thiscall_table(env, "graphics", {0x30: (3, returns(f))})
    gfx = env.object(0x80, "graphics", fill=0)
    env.put(gfx, gfx_vt)
    g1 = env.object(0x400, "graphics manager", fill=0)
    g = env.object(0x70, "game", fill=0)
    env.put(g + 4, d)
    env.put(g + 0x18, gfx)
    env.put(g + 0x1C, g1)
    env.put(g + 0x28, m)
    t.update(g=g, gfx=gfx, g1=g1)
    if o.get("deep"):
        deep_graphics(env, v, t, o)
    # resources
    r, help_node, claw_node = resource_tree(env, v, o)
    t.update(r=r, help=help_node, claw=claw_node)
    # application
    w = env.object(16, "window", words=[v["junk"], v["hwnd"], v["junk"] ^ 1, v["junk"] ^ 2])
    xvt = thiscall_table(env, "app extra", {0x1C: (2, returns(0))})
    x = env.object(0x250, "app extra", fill=0)
    env.put(x, xvt)
    env.put(x + 0x244, v["junk"] | 0x80000000)
    a = env.object(0x90, "application", fill=0)
    env.put(a + 4, w, x)
    env.put(a + 0x7C, 0x280, 0x1E0)
    env.put(a + 0x30, g, r)
    env.put(a + 0x44, 0x66554433)
    t.update(w=w, x=x, a=a)
    # the state object
    svt = thiscall_table(env, "state", {0x0C: (0, effect_of(o.get("resume_ok", 1))),
                                        0x18: (0, effect_of(o.get("restore_state", 1)))})
    s = env.object(0x160, "help state", fill=0)
    env.put(s, svt)
    env.put(s + 4, a, r, g)
    env.put(s + 0x10, 0 if o.get("ui_null") else 0x77665544)
    env.put(s + 0x20, help_node, claw_node)
    env.put(s + 0x2C, f)
    env.put(s + 0x34, o.get("s34", 0))
    if o.get("deep"):
        env.put(s + 0x40, t["paper"])
    if o.get("s_junk"):
        # leave the vtable alone, fill the rest with a pattern the init has to overwrite
        env.write(s + 4, bytes((v["extra"] >> (k % 24)) & 0xFF | 0x40 for k in range(0x15C)))
    t["s"] = s
    # the global input object
    i = env.object(0x250, "input", fill=0)
    env.put(i + 0x1CC, o.get("input_flags", 1))
    for slot in range(12):
        env.put(i + 0x1DC + 4 * slot, key_code(v, slot))
    env.put(i + 0x1D4, o.get("joy_enable", 0))
    env.put(i + 0x20C, o.get("held", 0))
    env.put(INPUT_GLOBAL, i)
    t["i"] = i
    return t


def key_code(v, slot):
    """The virtual-key code stored in input slot `slot` (slot 0 is at I+0x1dc)."""
    return 0x31 + slot * 5 + (v["junk"] & 3)


def make(label, function, v, args=(), overrides=None, post=None, **options):
    """One case on the Help state S. `overrides` maps a fixture address to a function of the tokens."""
    overrides = overrides or {}

    def setup(env):
        t = build(env, v, **options)
        defaults(env, v, {address: effect(t) for address, effect in overrides.items()})
        if post:
            post(env, t)
        return t

    return Case(label, function, setup, receiver=lambda t: t["s"], arguments=args)


def at(key):
    return lambda t: t[key]


def cases(random_source):
    rnd = random_source

    # ---- 0x449bd0: the key handler -------------------------------------------------------------
    for key in (0x1B, 0x20, 0x0D, 0x1A, 0x1C, 0x1F, 0x21, 0x0C, 0x0E, 0x0A, 0x41, 0x11B, 0x120, 0x10D,
                0, 0xFFFFFFFF, 0x80000000, rnd.getrandbits(32), rnd.randrange(0x100, 0x10000)):
        v = scalars(rnd)
        yield make(f"key {key:#x}", KEY, v, args=(key, v["junk"]))

    # ---- 0x449c10: the mouse handler -----------------------------------------------------------
    for _ in range(4):
        v = scalars(rnd)
        yield make("mouse", MOUSE, v, args=(rnd.getrandbits(32), rnd.getrandbits(32), rnd.getrandbits(32)))

    # ---- 0x449930: destroy (a tail jump to the base cleanup) ---------------------------------
    for label, g_present, f_present in (("game and image", True, True), ("game only", True, False),
                                        ("image only", False, True), ("neither", False, False)):
        v = scalars(rnd)

        def post(env, t, g_present=g_present, f_present=f_present):
            env.put(t["s"] + 0xC, t["g"] if g_present else 0)
            env.put(t["s"] + 0x2C, t["f"] if f_present else 0)
            env.put(t["s"] + 0x3C, 0 if g_present else 0x1234)
            env.put(t["s"] + 0x40, 0)
        if g_present and f_present:
            continue  # the base cleanup would release the image through the MFC list code
        yield make(f"destroy: {label}", DESTROY, v, post=post, s34=v["junk"] | 1)

    # ---- 0x4499d0: palette fade and two flips ------------------------------------------------------
    fade_args = [0xFFFFFFFF, 0x80000000, 0xFFFFFFF0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 0x10B,
                 0x7FFFFFFF, rnd.randrange(14, 1000), rnd.randrange(-100, 0)]
    for arg in fade_args:
        for f_present in (True, False):
            v = scalars(rnd)
            t0 = v["time"]
            yield make(f"fade arg {arg:#x} image {f_present}", FADE, v, args=(arg & 0xFFFFFFFF,),
                       overrides={TIME_GET_TIME: lambda t, t0=t0: clock(t0, t0 + 250, t0 + 499, t0 + 500)},
                       f=f_present)
    # the display chain is read again after every call
    for arg in (3, 4, 11):
        for mode in ("game", "display"):
            v = scalars(rnd)
            t0 = v["time"]
            box = {}

            def blt(env, call, box=box, mode=mode):
                if env.calls_so_far(call.function) == 1:
                    t = box["t"]
                    if mode == "game":
                        env.put(t["s"] + 0xC, t["g2"])
                    else:
                        env.put(t["g"] + 4, t["d2"])
                return 0

            def setup(env, v=v, t0=t0, box=box, blt=blt):
                t = build(env, v, blt=blt)
                d2 = display(env, v, "second display")[0]
                g2 = env.object(0x70, "second game", fill=0)
                env.put(g2 + 4, d2)
                env.put(g2 + 0x18, t["gfx"])
                env.put(g2 + 0x1C, t["g1"])
                env.put(g2 + 0x28, t["m"])
                t["d2"], t["g2"] = d2, g2
                box["t"] = t
                defaults(env, v, {TIME_GET_TIME: clock(t0, t0 + 250, t0 + 499, t0 + 500)})
                return t
            yield Case(f"fade arg {arg} display re-read ({mode})", FADE, setup,
                       receiver=lambda t: t["s"], arguments=(arg,))

    # ---- 0x449a60: per-frame update ----------------------------------------------------------------
    def keyed(slot, result=0x8000):
        return lambda t: keys({key_code(t["v"], slot): result})

    u = 0
    # surface checks
    for label, opts in (
            ("surface missing, restore ok", dict(no_interface=True, restore_state=1)),
            ("surface missing, restore fails", dict(no_interface=True, restore_state=0)),
            ("surface fine", dict(lost=0)),
            ("surface lost, restore ok", dict(lost=1, restore_state=1)),
            ("surface lost, restore fails", dict(lost=0x887601C2, restore_state=0)),
            ("restore result is not 1", dict(lost=1, restore_state=0x40000000)),
            ):
        v = scalars(rnd)
        yield make(f"update: {label}", UPDATE, v, **opts)
    # the fade step
    t0 = 4000
    for label, opts, readings in (
            ("fade running", dict(active=1, duration=700, started=t0), (t0 + 300,)),
            ("fade running, no source buffer", dict(active=1, duration=700, started=t0, source=False), (t0 + 301,)),
            ("fade running, same step as last", dict(active=1, duration=700, started=t0, last=300), (t0 + 300,)),
            ("fade over", dict(active=1, duration=700, started=t0), (t0 + 700,)),
            ("fade long over", dict(active=1, duration=500, started=t0), (t0 + 9000,)),
            ("fade over, no source buffer", dict(active=1, duration=700, started=t0, source=False), (t0 + 701,)),
            ("fade not active", dict(active=0), (t0 + 300,)),
            ("no image", dict(f=False), (t0 + 300,)),
            ):
        v = scalars(rnd)
        yield make(f"update: {label}", UPDATE, v, overrides={TIME_GET_TIME: lambda t, r=readings, v=v: clock(*r, v["time"])}, **opts)
    # the image is replaced while the fade step runs
    for replacement in ("inactive palette", "active palette"):
        v = scalars(rnd)

        def post(env, t, replacement=replacement):
            pl2 = palette(env, v, active=1 if replacement == "active palette" else 0, duration=900, started=100)
            t["f2"] = screen_image(env, pl2)

        def hook(t):
            def effect(env, call):
                env.put(t["s"] + 0x2C, t["f2"])
                return 0
            return effect

        def setup(env, v=v, post=post, hook=hook, replacement=replacement):
            t = build(env, v, active=1, duration=700, started=t0)
            post(env, t)
            pal = env.get(t["pl"] + 4)
            env.put(env.get(pal) + 0x18, env.stub("palette swap", "stdcall", 5, hook(t)))
            defaults(env, v, {TIME_GET_TIME: clock(t0 + 300, v["time"])})
            return t
        yield Case(f"update: image replaced by {replacement} during the fade", UPDATE, setup,
                   receiver=lambda t: t["s"])
    # sounds
    for label, opts in (
            ("no sound list", dict()),
            ("sound list", dict(sound_list="empty")),
            ("sound list with an element", dict(sound_list="element", sound_clock=7)),
            ("sound list with an element, clock ahead", dict(sound_list="element", sound_clock=2 ** 31)),
            ):
        v = scalars(rnd)
        yield make(f"update: {label}", UPDATE, v, overrides={TIME_GET_TIME: lambda t, v=v: clock(v["time"], v["time"] + 5)}, **opts)
    # the input poll
    for slot in range(12):
        for held in (0, 1 << ((slot - 4) % 8)):
            for joy in (0, 1):
                v = scalars(rnd)
                yield make(f"update: key slot {slot} held {held:#x} joystick {joy}", UPDATE, v,
                           overrides={KEY_STATE: keyed(slot)}, held=held, joy_enable=joy)
    for label, pressed in (("all slots", list(range(12))), ("slots 4-11", list(range(4, 12))),
                           ("slots 0-3", [0, 1, 2, 3]), ("slots 0, 5", [0, 5]), ("none", [])):
        v = scalars(rnd)
        yield make(f"update: pressed {label}", UPDATE, v,
                   overrides={KEY_STATE: (lambda t, p=pressed: keys({key_code(t["v"], s): 0x8000 for s in p}))})
    v = scalars(rnd)
    yield make("update: key reports the repeat bit only", UPDATE, v,
               overrides={KEY_STATE: (lambda t: keys({key_code(t["v"], s): 1 for s in range(12)}))})
    v = scalars(rnd)
    yield make("update: key reports a high bit", UPDATE, v,
               overrides={KEY_STATE: (lambda t: keys({key_code(t["v"], s): 0xFFFF8000 for s in range(12)}))})
    v = scalars(rnd)
    yield make("update: input disabled", UPDATE, v,
               overrides={KEY_STATE: (lambda t: keys({key_code(t["v"], s): 0x8000 for s in range(12)}))}, input_flags=0)

    for second, first_pressed in ((0x1, False), (0, True), (0x80, False), (0x1000000, False)):
        v = scalars(rnd)

        def post(env, t, second=second):
            i2 = env.object(0x250, "second input", fill=0)
            env.put(i2 + 0x210, second)
            t["i2"] = i2

        def poll(t, first_pressed=first_pressed):
            def effect(env, call):
                if env.calls_so_far(call.function) == 1:
                    env.put(INPUT_GLOBAL, t["i2"])
                if first_pressed and call.arguments[0] == key_code(t["v"], 4):
                    return 0x8000
                return 0
            return effect
        yield make(f"update: input object replaced during the poll ({second:#x}, pressed {first_pressed})", UPDATE, v,
                   overrides={KEY_STATE: poll}, post=post)

    # ---- 0x449b30: redraw ----------------------------------------------------------------------------
    for label, opts in (
            ("normal", dict()),
            ("page 2 refuses the picture", dict(load=0)),
            ("page 2 accepts with other value", dict(load=0x12345678)),
            ("display cannot be restored", dict(lost=1, restore=0x887601C2)),
            ("display restored", dict(lost=1, restore=0)),
            ("display lost, restored on retry", dict(lost=1, restore=lambda env, call: 1 if env.calls_so_far(call.function) == 1 else 0)),
            ("third page present", dict(d_extra=True)),
            ("third page lost", dict(d_extra=True, lost3=1)),
            ("third page cannot be restored", dict(d_extra=True, lost3=1, restore3=1)),
            ("no state resources", dict(screens_dir=False)),
            ("picture missing", dict(screen=False)),
            ):
        for variant in ("", "no archive", "no node"):
            v = scalars(rnd)

            def post(env, t, variant=variant):
                if variant == "no archive":
                    env.put(t["s"] + 8, 0)
                elif variant == "no node":
                    env.put(t["s"] + 0x20, 0)
            yield make(f"redraw: {label} {variant}", REDRAW, v, post=post, **opts)

    # ---- 0x449b70: resume ---------------------------------------------------------------------------
    cursor_counts = {
        "negative at once": (-1,),
        "zero then negative": (0, -1),
        "three then negative": (5, 2, 0, -4),
        "huge positive then huge negative": (0x7FFFFFFF, 0x80000000),
        "one then minus one": (1, 0xFFFFFFFF),
    }
    for label, resume_ok, f_present, counts_key, variant in (
            ("resume refuses", 0, True, "negative at once", ""),
            ("resume returns other value", 0x55, True, "zero then negative", ""),
            ("no image", 1, False, "negative at once", ""),
            ("normal", 1, True, "negative at once", ""),
            ("normal, slow cursor", 1, True, "three then negative", ""),
            ("normal, huge counts", 1, True, "huge positive then huge negative", ""),
            ("normal, cursor 1", 1, True, "one then minus one", ""),
            ("normal, cursor 0", 1, True, "zero then negative", ""),
            ("picture missing", 1, True, "negative at once", "no picture"),
            ("no archive", 1, True, "negative at once", "no archive"),
            ("no node", 1, True, "negative at once", "no node"),
            ("palette was fading", 1, True, "negative at once", "fading"),
            ("palette was fading, no source", 1, True, "negative at once", "fading no source"),
            ):
        v = scalars(rnd)
        t0 = v["time"]

        def post(env, t, variant=variant):
            if variant == "no archive":
                env.put(t["s"] + 8, 0)
            elif variant == "no node":
                env.put(t["s"] + 0x20, 0)
            elif variant == "no picture":
                env.put(t["s"] + 0x20, t["claw"])

        opts = {}
        if variant == "fading":
            opts = dict(active=1, duration=300, started=t0 - 100)
        elif variant == "fading no source":
            opts = dict(active=1, duration=300, started=t0 - 100, source=False)
        yield make(f"resume: {label}", RESUME, v, post=post, resume_ok=resume_ok, f=f_present,
                   overrides={SHOW_CURSOR: lambda t, c=cursor_counts[counts_key]: counts(*c),
                              TIME_GET_TIME: lambda t, t0=t0: clock(t0, t0 + 100, t0 + 249, t0 + 250, t0 + 260)}, **opts)

    # ---- 0x449940: enter -----------------------------------------------------------------------------
    enter_args = list(range(0, 13)) + [0xFFFFFFFF, 0xFFFFFFFE, 0x80000000, 0x80000002, 100, rnd.randrange(13, 1000)]
    for arg in enter_args:
        for variant in ("", "no ui", "no picture", "no screens"):
            v = scalars(rnd)
            opts = {}
            if variant == "no ui":
                opts["ui_null"] = True
            elif variant == "no picture":
                opts["screen"] = False
            elif variant == "no screens":
                opts["screens_dir"] = False
            if variant and arg not in (2, 3, 5, 9):
                continue
            yield make(f"enter {arg:#x} {variant}", ENTER, v, args=(arg & 0xFFFFFFFF,), **opts)
    # the original creates the screen surfaces for real, so the arguments reach the palette fade
    for arg in list(range(0, 13)) + [0xFFFFFFFF, 0x80000000, 100, rnd.randrange(13, 1000)]:
        v = scalars(rnd)
        t0 = v["time"]
        yield make(f"enter deep {arg:#x}", ENTER, v, args=(arg & 0xFFFFFFFF,), deep=True,
                   overrides={TIME_GET_TIME: lambda t, t0=t0: clock(t0, t0 + 250, t0 + 499, t0 + 500, t0 + 501)})
    for label, c in (("negative at once", (-1,)), ("zero then negative", (0, -1)), ("three then negative", (7, 3, 1, 0, -2)),
                     ("huge", (0x7FFFFFFF, 0x80000000)), ("one", (1, 0xFFFFFFFF))):
        for arg in (2, 3):
            v = scalars(rnd)
            yield make(f"enter {arg} cursor counts {label}", ENTER, v, args=(arg,),
                       overrides={SHOW_CURSOR: lambda t, c=c: counts(*c)})

    # ---- a few random arguments ------------------------------------------------------------------------
    for _ in range(6):
        arg = rnd.getrandbits(32)
        v = scalars(rnd)
        t0 = v["time"]
        yield make(f"enter random {arg:#x}", ENTER, v, args=(arg,), deep=rnd.random() < 0.5,
                   overrides={SHOW_CURSOR: lambda t, c=tuple(rnd.randrange(-3, 4) for _ in range(3)): counts(*c, -1),
                              TIME_GET_TIME: lambda t, t0=t0: clock(t0, t0 + 250, t0 + 499, t0 + 500, t0 + 501)})
        v = scalars(rnd)
        yield make(f"fade random {arg:#x}", FADE, v, args=(rnd.choice([3, 4, 11, arg]),),
                   overrides={TIME_GET_TIME: lambda t, t0=t0: clock(t0, t0 + 250, t0 + 499, t0 + 500)})

    # ---- 0x449870: init -------------------------------------------------------------------------------
    def init(label, level, a3, peek=(0,), **opts):
        v = scalars(rnd)
        signed = level - 2 ** 32 if level >= 2 ** 31 else level
        levels = opts.pop("levels", tuple({signed, signed + 1, signed - 1, 100 - signed}))
        return make(f"init: {label}", INIT, v, args=(at("a"), level & 0xFFFFFFFF, a3),
                    overrides={PEEK_MESSAGE: lambda t, peek=peek: counts(*peek)},
                    levels=levels, s_junk=True, **opts)

    for level in (1, 2, 9, 10, 99, 0, 0xFFFFFFF9, rnd.randrange(3, 60), rnd.randrange(100, 100000)):
        yield init(f"level {level:#x}", level, rnd.getrandbits(32))
    yield init("no level node", 7, rnd.getrandbits(32), levels=(6, 8, 77))
    yield init("no level node at all", 3, rnd.getrandbits(32), levels=())
    yield init("no help node", 4, rnd.getrandbits(32), help_node=False)
    yield init("no claw node", 4, rnd.getrandbits(32), claw_node=False)
    yield init("no sounds directory", 4, rnd.getrandbits(32), sounds_dir=False)
    yield init("no sounds directory, sound list", 4, rnd.getrandbits(32), sounds_dir=False, sound_list="empty")
    yield init("sound list", 4, rnd.getrandbits(32), sound_list="empty")
    yield init("live sound list", 4, rnd.getrandbits(32), sound_active=True)
    yield init("live sound list, sounds loaded already", 4, rnd.getrandbits(32), sound_active=True, sound_flag=1)
    yield init("live sound list, no sounds directory", 4, rnd.getrandbits(32), sound_active=True, sounds_dir=False)
    yield init("sound list, sounds loaded already", 4, rnd.getrandbits(32), sound_list="empty", sound_flag=1)
    yield init("sounds loaded already", 4, rnd.getrandbits(32), sound_flag=1)
    yield init("drain one message", 5, rnd.getrandbits(32), peek=(1, 0))
    yield init("drain three messages", 5, rnd.getrandbits(32), peek=(7, 3, 1, 0))
    yield init("drain until the limit", 5, rnd.getrandbits(32), peek=(1,))
    yield init("no screens either", 6, rnd.getrandbits(32), screens_dir=False)
