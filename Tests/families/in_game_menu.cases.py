"""Cases for in_game_menu: In-game menu opened by Escape.

Every random value is drawn when the case list is generated, never inside a setup
function, so each setup rebuilds the identical memory image.  Coverage does not
depend on the seed: every branch is reached by an explicit parameter list, and the
random draws only change the contents of fields the code reads or copies.
"""
import random

from clawparity.cases import Case

M32 = 0xFFFFFFFF

# ---- owned functions
F_INIT = 0x44F880
F_ENTER = 0x44FAD0
F_FRAME = 0x450060
F_INPUT = 0x450610
F_LAYOUT = 0x451770
F_BANNER = 0x451900
F_SURFACE = 0x451C40
F_ENABLE = 0x451D50
F_HOTKEYS = 0x451F00
F_AUDIO = 0x4525A0
F_CLEAR = 0x46DD90
F_MASK = 0x46DDF0
F_ALIGN = 0x4DD5B0

# ---- imports (import table slots)
IAT_LSTRLEN = 0x5469E4
IAT_TICK = 0x546A24
IAT_METRICS = 0x546C44
IAT_PEEK = 0x546CAC
IAT_CURSOR_POS = 0x546CD0   # declared scripted fixture
IAT_KEYSTATE = 0x546CE4
IAT_POST = 0x546D50
IAT_SHOWCURSOR = 0x546D54
IAT_COPYRECT = 0x546D58     # declared scripted fixture
IAT_SETRECT = 0x546D5C      # declared scripted fixture
IAT_SETCURSOR = 0x546D9C
IAT_JOY = 0x546DE8

# ---- program globals
G_INPUT = 0x537200
G_INPUT_HOLDER = 0x537204
G_UI = 0x5371FC
G_DT = 0x53720C
G_DT_SOURCE = 0x537208
G_STEP = 0x5430C4
G_STEP_SOURCE = 0x5430C8
G_REPEAT_FIRST = 0x528A60
G_REPEAT_NEXT = 0x528A64
G_CURRENT_MENU = 0x53789C
G_SOUND_ON = 0x532C0C
G_SOUND_ID = 0x532C10
G_CURSOR_ACTOR = 0x537E88
G_FRAME_STEP = 0x54132C

# ---- shared vtables patched in the image
ACTOR_VTABLE = 0x5137F0
ACTOR_DELETE = ACTOR_VTABLE + 0x04
ACTOR_INIT = ACTOR_VTABLE + 0x28
ACTOR_DRAW = ACTOR_VTABLE + 0x2C
SURFACE_VTABLE = 0x513690
SURFACE_INIT = SURFACE_VTABLE + 0x2C

ID_MAIN = 0x59DA
ID_OPTIONS = 0x59DB
PAGES = (ID_MAIN, ID_OPTIONS)
AUDIO_NAME = b"GAME_INGAMEMENU_MAIN_OPTIONS_AUDIO"

# menu object (this) field offsets
MENU_SIZE = 0x2E0
CONTAINER = 0x154


def u(value):
    return value & M32


def s32(value):
    value &= M32
    return value - (1 << 32) if value & 0x80000000 else value


def obj(env, size, name, **options):
    options.setdefault("fill", 0)
    return env.object(size, name, **options)


def words_of(rr, count, high=False):
    return [rr.randrange(1, 1 << 32) | (0x01010101 if high else 0) for _ in range(count)]


def observe(env, log, tag, receiver, arguments, fields=()):
    """Append one row to the observation log.  Rows are compared with the rest of memory."""
    n = env.get(log)
    env.put(log, n + 1)
    row = log + 4 + (n % 120) * 48
    env.put(row, tag, receiver, len(arguments), *[a & M32 for a in arguments][:6])
    env.put(row + 36, *[f & M32 for f in fields][:3])


def string_map(env, entries, buckets=1):
    """An object whose +0x10 is a string hash map (the original's CMapStringToPtr)."""
    holder = obj(env, 0x40, "map-owner")
    table = obj(env, 4 * buckets + 4, "map-buckets")
    env.put(holder + 0x14, table, buckets)
    heads = [0] * buckets
    for key, value in reversed(entries):
        hashed = 0
        for byte in key:
            hashed = (hashed * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
        slot = hashed % buckets
        key_pointer = obj(env, len(key) + 4, "map-key", data=key + b"\0")
        node = obj(env, 0x10, "map-node")
        env.put(node, heads[slot], 0, key_pointer, value)
        heads[slot] = node
    for slot, head in enumerate(heads):
        env.put(table + 4 * slot, head)
    return holder


def counted_stub(env, name, convention, argc, effect):
    """A stub whose effect also learns how many times it has been called (this call included)."""
    cell = [0]
    cell[0] = env.stub(name, convention, argc, lambda e, c: effect(e, c, e.calls_so_far(cell[0])))
    return cell[0]


def counted(env, effect):
    """An effect that also learns how many times the fixture has been called (this call included)."""
    return lambda e, c: effect(e, c, e.calls_so_far(c.function))


def cstring(env, text):
    """A CString: a header of refcount, length and capacity, then the text."""
    data = text.encode("ascii")
    block = obj(env, 13 + len(data), "CString")
    env.put(block, 1, len(data), len(data))
    env.write(block + 12, data + b"\0")
    return block + 12


def directory(env, name, children=()):
    """One directory of the archive: its own name at +0, children in a five bucket table."""
    d = obj(env, 0x70, "archive-directory-" + name)
    env.put(d, cstring(env, name))
    buckets = obj(env, 0x50, "directory-buckets")
    env.put(d + 0x40, buckets)
    for child_name, child in children:
        slot = buckets + (len(child_name) % 5) * 16 + 8
        node = obj(env, 24, "directory-node-" + child_name)
        env.put(node + 4, env.get(slot))
        env.put(node + 0x14, child)
        env.put(slot, node + 4)
    return d


def new_list(env, base, nodes_data=(), pool=24, extra_free=None):
    """A CPtrList at `base` holding `nodes_data` in order.  Returns the node addresses.
    Layout from base: +4 head, +8 tail, +0xc count, +0x10 free list, +0x14 blocks, +0x18 block size."""
    nodes = [obj(env, 12, "list-node") for _ in nodes_data]
    for i, node in enumerate(nodes):
        env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0, nodes[i - 1] if i else 0, nodes_data[i])
    env.put(base + 4, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
    block = obj(env, 4 + pool * 12, "list-node-block")
    first = block + 4
    for i in range(pool - 1):
        env.put(first + i * 12, first + (i + 1) * 12)
    env.put(base + 0x10, first)
    env.put(base + 0x14, block)
    env.put(base + 0x18, pool)
    return nodes


def frame_object(env, rr, width, height):
    frame = obj(env, 0x40, "image-frame", words=words_of(rr, 16))
    env.put(frame + 0x10, width, height)
    return frame


def resource(env, rr, first, last, count, width=40, height=22):
    """An image resource: +0x64 first index, +0x68 last index, +0x14 an array of frames."""
    res = obj(env, 0x80, "image-resource", words=words_of(rr, 32))
    frames = obj(env, 4 * 64, "image-frames")
    for index in range(min(count, 64)):
        env.put(frames + 4 * index, frame_object(env, rr, width + index, height + 2 * index))
    env.put(res + 0x14, frames)
    env.put(res + 0x64, first, last)
    return res


def animation(env, rr):
    first = obj(env, 0x40, "animation-frame", words=words_of(rr, 16))
    frames = obj(env, 8, "animation-frames")
    env.put(frames, first)
    anim = obj(env, 0x40, "animation", words=words_of(rr, 16))
    env.put(anim + 0x0C, frames)
    env.put(anim + 0x10, 1)
    return anim


# ----------------------------------------------------------------------------
# Default option set.  Everything random is drawn here, at generation time.
# ----------------------------------------------------------------------------

def draw(r, **over):
    o = {
        "seed": r.getrandbits(32),
        # application
        "width": r.choice([640, 800, 1024, 641, 801]),
        "height": r.choice([480, 600, 768, 481, 601]),
        "bpp": 16,
        "a9c": 1, "a10": r.randrange(1, 9), "e28": r.randrange(1, 9),
        "z30": 0, "select": True, "level": r.randrange(1, 14),
        "resource": False, "loader": 0, "loader_ok": False,
        # run time
        "dt": r.randrange(1, 60), "repeat_first": r.randrange(5, 500), "repeat_next": r.randrange(5, 300),
        "sound_on": 1, "sound_id": r.randrange(1, 1 << 31),
        "cursor": (r.randrange(0, 900), r.randrange(0, 700)),
        "copy": "faithful", "setrect": "faithful",
        "lives": r.choice([1, 2, 5]), "cursor_actor": True,
        # menu
        "ids": (0x59DB, 0x5AA1, 0x5AA2, 0x5AA3, 0x5AA4, 0x5B05, 0x5B06, 0x5B07, 0x4E21),
        "index": 0, "flag_of": {},
        "state": 3,
        "actors": 0,            # bit set of existing actors 0x254..0x26c
        "page": 10000, "m2a0": 0, "m29c": r.randrange(1, 4000), "m2a4": r.randrange(1, 900),
        "m2a8": 0, "m298": 10000,
        "step": r.randrange(1, 90),
        "map": "full",          # hotkey map: full | empty
        "keys": {}, "joy": None, "input_flags": 1, "prev": 0, "ipad_extra": 0,
        "peek": (1, 1, 0), "cursor_seq": (1, 0, -1), "tick": r.randrange(1000, 90000),
        "restore": False, "blt_status": 0,
        "old_surface": True, "surface_ok": True,
        "k_move": "wrap", "rows": 3, "wbytes": 16, "pitch": 16, "pixel_ptr": True, "lock_status": (0,),
        "engine_flag": 0, "press": (), "click": True, "flip_iface": True, "flip_status": 0, "owner": True, "state_ptr": True, "scene_prio": (50, 100, 150), "scene_flags": (0,), "scene_actors": 0,
        "cursor_empty": False, "cursor_global": True, "new_rect": (3, 5, 320, 200), "joy_axes": None,
    }
    o.update(over)
    return o


ACTOR_SLOTS = (0x254, 0x258, 0x25C, 0x260, 0x264, 0x268, 0x26C)

HOTKEY_KEYS = (b"Return to Game", b"End Life", b"Options", b"Help", b"End Game", b"Yes", b"No", b"Controls",
               b"Display", b"Audio", b"Back", b"Sound", b"Ambient", b"Voice", b"Music", b"Front", b"Game",
               b"Movies")


def key_codes(rr):
    return [0x30 + 3 * i + rr.randrange(0, 3) for i in range(12)]


# ----------------------------------------------------------------------------
# The world
# ----------------------------------------------------------------------------

def world(env, o):
    rr = random.Random(o["seed"])
    w = {}
    log = obj(env, 0x4000, "observations")
    w["log"] = log

    # ---------------- the images of the actor classes: delete, initialize, draw
    def actor_delete(e, c):
        observe(e, log, 0xD1, c.receiver, c.arguments, (e.get(c.receiver + 8), e.get(c.receiver + 0x68), e.get(c.receiver + 0x40)))
        return 0
    env.put(ACTOR_DELETE, env.stub("actor-delete", "thiscall", 1, actor_delete))

    def service_callback(e, c):
        a = c.arguments[0]
        observe(e, log, 0xD2, c.receiver, c.arguments, (e.get(a + 0x4C), e.get(a + 0x50), e.get(a + 0x40)))
        return 0
    callback = env.stub("actor-service-callback", "cdecl", 1, service_callback)
    w["callback"] = callback

    def actor_init(e, c):
        actor = c.receiver
        service = e.get(actor + 0x6C)
        e.put(actor + 0x64, c.arguments[2])
        e.put(actor + 0x180, c.arguments[3])
        e.put(actor + 0x4C, c.arguments[0], c.arguments[1])
        if service:
            e.put(service + 0x10, callback)
        observe(e, log, 0xD3, actor, c.arguments, (e.get(actor + 0x68), e.get(actor + 0x1B * 4), e.get(actor + 0x58)))
        return 1
    env.put(ACTOR_INIT, env.stub("actor-init", "thiscall", 4, actor_init))

    def actor_draw(e, c):
        observe(e, log, 0xD4, c.receiver, c.arguments, (e.get(c.receiver + 0x4C), e.get(c.receiver + 0x50), e.get(c.receiver + 0x40)))
        return 0
    env.put(ACTOR_DRAW, env.stub("actor-draw", "thiscall", 1, actor_draw))

    # ---------------- imports
    env.override(IAT_LSTRLEN, lambda e, c: len(e.cstr(c.arguments[0])))

    def lstrcpyn(e, c):
        dst, src, count = c.arguments
        text = e.cstr(src)[:max(count - 1, 0)] if isinstance(e.cstr(src), (bytes, bytearray)) else e.cstr(src).encode()[:max(count - 1, 0)]
        if count > 0:
            e.write(dst, bytes(text) + b"\0")
        return dst
    env.override(0x5469CC, lstrcpyn)

    def tick(e, c, n):
        return (o["tick"] + 977 * n) & M32
    env.override(IAT_TICK, counted(env, tick))

    def metrics(e, c):
        observe(e, log, 0xE1, 0, c.arguments)
        return 640 + 160 * (c.arguments[0] & 1)
    env.override(IAT_METRICS, metrics)

    def peek(e, c, n):
        observe(e, log, 0xE2, 0, c.arguments)
        return o["peek"][min(n, len(o["peek"])) - 1]
    env.override(IAT_PEEK, counted(env, peek))

    def post(e, c):
        observe(e, log, 0xE3, 0, c.arguments)
        return 1
    env.override(IAT_POST, post)

    def showcursor(e, c, n):
        observe(e, log, 0xE4, 0, c.arguments)
        return o["cursor_seq"][min(n, len(o["cursor_seq"])) - 1] & M32
    env.override(IAT_SHOWCURSOR, counted(env, showcursor))

    def setcursor(e, c):
        observe(e, log, 0xE5, 0, c.arguments)
        return 1
    env.override(IAT_SETCURSOR, setcursor)

    keys = dict(o["keys"])

    def keystate(e, c):
        return keys.get(c.arguments[0], 0)
    env.override(IAT_KEYSTATE, keystate)

    def joystick(e, c):
        info = c.arguments[1]
        j = o["joy"] or (0, 0, 0)
        e.put(info + 8, j[0], j[1])
        e.put(info + 0x20, j[2])
        return 0
    env.override(IAT_JOY, joystick)

    def cursor_pos(e, c):
        e.put(c.arguments[0], *o["cursor"])
        return 1
    env.override(IAT_CURSOR_POS, cursor_pos)

    def copy_rect(e, c):
        values = [e.get(c.arguments[1] + 4 * i) for i in range(4)]
        if o["copy"] == "shifted":
            values = [values[0] + 3, values[1] + 5, values[2] - 7, values[3] - 11]
        e.put(c.arguments[0], *[v & M32 for v in values])
        return 1
    env.override(IAT_COPYRECT, copy_rect)

    def set_rect(e, c):
        values = list(c.arguments[1:5])
        if o["setrect"] == "shifted":
            values = [values[0] + 2, values[1] + 4, values[2] - 6, values[3] - 8]
        e.put(c.arguments[0], *[v & M32 for v in values])
        return 1
    env.override(IAT_SETRECT, set_rect)

    # ---------------- direct draw style interfaces
    def lock(e, c, n):
        observe(e, log, 0xF1, c.arguments[0], c.arguments[1:], ())
        seq = o["lock_status"]
        return seq[min(n, len(seq)) - 1] & M32

    def unlock(e, c):
        observe(e, log, 0xF2, c.arguments[0], c.arguments[1:], ())
        return 0

    def blit(e, c):
        observe(e, log, 0xF3, c.arguments[0], c.arguments[1:], (e.get(c.arguments[1]), e.get(c.arguments[1] + 4), e.get(c.arguments[1] + 8)))
        return o["blt_status"] & M32

    surf_iface = obj(env, 4, "back-surface-interface")
    surf_vt = obj(env, 0x90, "back-surface-vtable")
    env.put(surf_iface, surf_vt)
    env.put(surf_vt + 0x14, env.stub("IDirectDrawSurface::Blt", "stdcall", 6, blit))
    env.put(surf_vt + 0x64, counted_stub(env, "IDirectDrawSurface::Lock", "stdcall", 5, lock))
    env.put(surf_vt + 0x80, env.stub("IDirectDrawSurface::Unlock", "stdcall", 2, unlock))

    def target_restore(e, c):
        observe(e, log, 0xF4, c.receiver, c.arguments)
        return 1 if o["restore"] else 0

    surface_vt = obj(env, 0x30, "surface-owner-vtable")
    env.put(surface_vt + 0x1C, env.stub("surface-restore", "thiscall", 0, target_restore))
    bpp = o["bpp"]
    rows, wbytes, pitch = o["rows"], o["wbytes"], o["pitch"]
    if bpp == 8:
        per_row = ((wbytes + ((wbytes >> 31) & 3)) >> 2) if wbytes >= 0 else ((wbytes + 3) >> 2)
    else:
        per_row = int(wbytes / 2)
    per_row = max(per_row, 0)
    pixel_size = max(8, (max(rows, 1) - 1) * max(pitch, 0) + 4 * per_row)
    pixel_size = (pixel_size + 3) & ~3
    pixels = obj(env, pixel_size, "pixels", words=[rr.getrandbits(32) for _ in range(pixel_size // 4)])
    w["pixels"] = pixels
    target = obj(env, 0x80, "back-surface", words=words_of(rr, 32))
    env.put(target, surface_vt)
    env.put(target + 8, surf_iface)
    env.put(target + 0x14, rows & M32, wbytes & M32, pitch & M32)
    env.put(target + 0x30, pixels if o["pixel_ptr"] else 0)
    w["target"] = target
    front = obj(env, 0x80, "front-surface", words=words_of(rr, 32))
    env.put(front, surface_vt)
    env.put(front + 8, surf_iface)

    # the flip interface
    def flip(e, c):
        observe(e, log, 0xF5, c.arguments[0], c.arguments[1:], ())
        return 0

    def flip_status(e, c):
        observe(e, log, 0xF6, c.arguments[0], c.arguments[1:], ())
        return o.get("flip_status", 0)
    flip_iface = obj(env, 4, "flip-interface")
    flip_vt = obj(env, 0x70, "flip-vtable")
    env.put(flip_iface, flip_vt)
    env.put(flip_vt + 0x2C, env.stub("IDirectDrawSurface::Flip", "stdcall", 3, flip))
    env.put(flip_vt + 0x60, env.stub("IDirectDraw::GetFlipStatus", "stdcall", 1, flip_status))
    device_vt = obj(env, 0x30, "device-vtable")
    env.put(device_vt + 0x1C, env.stub("device-restore", "thiscall", 0, target_restore))
    device = obj(env, 0x20, "device", words=words_of(rr, 8))
    env.put(device, device_vt)
    env.put(device + 8, flip_iface if o["flip_iface"] else 0)

    # ---------------- engine, screen
    graphics = obj(env, 0x40, "graphics", words=words_of(rr, 16))
    env.put(graphics + 0x2C, device)
    screen = obj(env, 0x40, "screen", words=words_of(rr, 16))
    env.put(screen + 0x2C, target)
    engine = obj(env, 0x40, "engine", words=words_of(rr, 16))
    side = obj(env, 0x60, "engine-side", words=words_of(rr, 24))
    env.put(side + 0x34, o["engine_flag"])
    env.put(engine + 0x0C, side)
    env.put(engine + 0x10, graphics)
    env.put(engine + 0x14, screen)

    # ---------------- layers, scene
    layers = obj(env, 0x70, "layers", words=words_of(rr, 28))
    env.put(layers + 8, 0)
    env.put(layers + 0x3C, 0)
    env.put(layers + 0x60, M32)
    scene = obj(env, 0x50, "scene", words=words_of(rr, 20))

    def scene_draw(e, c):
        observe(e, log, 0xD5, c.receiver, c.arguments)
        return 0
    scene_vt = obj(env, 0x50, "scene-vtable")
    env.put(scene_vt + 0x28, env.stub("scene-draw", "thiscall", 1, scene_draw))
    env.put(scene, scene_vt)
    scene_nodes = []
    existing = []
    for i in range(o.get("scene_actors", 0)):
        a = obj(env, 0x1B4, "scene-actor-%d" % i, words=words_of(rr, 0x6D))
        env.put(a, ACTOR_VTABLE)
        env.put(a + 8, 0)
        env.put(a + 0x64, o["scene_prio"][i % len(o["scene_prio"])] & M32)
        env.write(a + 0xA, bytes([o["scene_flags"][i % len(o["scene_flags"])]]))
        service = obj(env, 0x174, "scene-actor-service", words=words_of(rr, 0x5D))
        env.put(service + 0x10, callback)
        env.put(a + 0x6C, service)
        existing.append(a)
    scene_nodes = new_list(env, scene + 0x10, existing, pool=64)
    for a, node in zip(existing, scene_nodes):
        env.put(a + 0x68, node)

    # ---------------- surfaces
    manager = obj(env, 0x420, "surface-manager", words=words_of(rr, 0x108))
    old_surface = 0
    if o["old_surface"]:
        old_surface = obj(env, 0xBC, "previous-banner", words=words_of(rr, 0x2F))
        old_vt = obj(env, 8, "previous-banner-vtable")

        def old_delete(e, c):
            observe(e, log, 0xB1, c.receiver, c.arguments, (e.get(manager + 0x3BC), e.get(manager + 0x3C0), e.get(manager + 0x3C4)))
            return 0
        env.put(old_vt, env.stub("previous-banner-delete", "thiscall", 1, old_delete))
        env.put(old_surface, old_vt)
        other = obj(env, 0xBC, "other-banner", words=words_of(rr, 0x2F))
        nodes = new_list(env, manager + 0x3B8, [other, old_surface] if o.get("surface_order", 0) else [old_surface, other], pool=24)
        env.put(old_surface + 4, nodes[1] if o.get("surface_order", 0) else nodes[0])
        env.put(other + 4, nodes[0] if o.get("surface_order", 0) else nodes[1])
    else:
        new_list(env, manager + 0x3B8, [], pool=24)
    w["old_surface"] = old_surface

    def surface_init(e, c):
        a = c.arguments
        observe(e, log, 0xB2, c.receiver, a, (e.get(manager + 0x3BC), e.get(manager + 0x3C4), e.get(c.receiver + 4)))
        e.put(c.receiver + 0x7C, *[v & M32 for v in o["new_rect"]])
        e.put(c.receiver + 0x78, 0x31415926)
        e.put(c.receiver + 8, surf_iface)
        return 1 if o["surface_ok"] else 0
    env.put(SURFACE_INIT, env.stub("surface-init", "thiscall", 6, surface_init))

    def surface_delete(e, c):
        observe(e, log, 0xB3, c.receiver, c.arguments, (e.get(c.receiver + 4), e.get(c.receiver + 0x7C)))
        return 0
    env.put(SURFACE_VTABLE, env.stub("surface-delete", "thiscall", 1, surface_delete))

    # ---------------- resources of the scene context
    images = string_map(env, [
        (b"GAME_CURSOR", resource(env, rr, 5 if o["cursor_empty"] else 0, 3 if o["cursor_empty"] else 20, 21)),
        (b"GAME_TREASURE_COINS", resource(env, rr, 0, 12, 13)),
        (b"GAME_INGAMEMENU_MAIN_CLAWICIDE", resource(env, rr, 0, 9, 10, 100, 40)),
        (b"GAME_INGAMEMENU_MAIN_ENDGAME", resource(env, rr, 0, 9, 10, 110, 44)),
        (AUDIO_NAME, resource(env, rr, 0, 60, 48, 20, 8)),
    ], o.get("image_buckets", 3))
    names = string_map(env, [
        (b"AniCycle", obj(env, 0x18, "metadata-anicycle", words=words_of(rr, 6))),
        (b"SimpleAnimation", obj(env, 0x18, "metadata-simple", words=words_of(rr, 6))),
        (b"DoNothing", obj(env, 0x18, "metadata-nothing", words=words_of(rr, 6))),
    ], o.get("name_buckets", 2))
    animations = string_map(env, [
        (b"GAME_CURSOR", animation(env, rr)),
        (b"GAME_CYCLE100", animation(env, rr)),
    ], 2)
    sound_value = obj(env, 0x30, "select-sound")
    sound_inner = obj(env, 0x30, "select-sound-inner")
    sound_leaf = obj(env, 0x90, "select-sound-leaf", words=words_of(rr, 36))
    env.put(sound_value + 0x10, sound_inner)
    env.put(sound_inner + 0x10, sound_leaf)
    env.put(sound_leaf + 0x78, 0)
    click_value = obj(env, 0x30, "click-sound")
    click_inner = obj(env, 0x30, "click-sound-inner")
    click_leaf = obj(env, 0x90, "click-sound-leaf", words=words_of(rr, 36))
    env.put(click_value + 0x10, click_inner)
    env.put(click_inner + 0x10, click_leaf)
    env.put(click_leaf + 0x78, 0)
    sound_entries = [(b"GAME_SELECT", sound_value) if o["select"] else (b"GAME_SELECT_NOT", sound_value),
                     (b"GAME_CLICK", click_value) if o["click"] else (b"GAME_CLICK_NOT", click_value)]
    sounds = string_map(env, sound_entries, 2)
    env.put(sounds + 0x30, o["z30"])

    context = obj(env, 0x60, "context", words=words_of(rr, 24))
    env.put(context + 4, engine)
    env.put(context + 8, scene)
    env.put(context + 0x10, images)
    env.put(context + 0x14, names)
    env.put(context + 0x1C, manager)
    env.put(context + 0x24, layers)
    env.put(context + 0x28, sounds)
    env.put(context + 0x2C, animations)
    env.put(context + 0x34, 0)
    env.put(scene + 0x0C, context)
    w["context"] = context

    # ---------------- archive for the level lookup
    level_dir = directory(env, "LEVEL%d" % o["level"])
    root = directory(env, "root", [("LEVEL%d" % o["level"], level_dir)])
    archive = obj(env, 0x40, "archive", words=words_of(rr, 16))
    env.put(archive + 0x24, root)

    # ---------------- application
    window = obj(env, 8, "window", words=[0, 0x4455])
    app = obj(env, 0x120, "application", words=words_of(rr, 72))
    owner = obj(env, 8, "application-owner")
    owner_vt = obj(env, 0x30, "application-owner-vtable")

    def owner_post(e, c):
        observe(e, log, 0xA1, c.receiver, c.arguments)
        return 0
    env.put(owner_vt + 0x1C, env.stub("application-notify", "thiscall", 2, owner_post))
    env.put(owner, owner_vt)
    env.put(app + 4, window)
    env.put(app + 8, owner if o["owner"] else 0)
    env.put(app + 0x10, o["a10"])
    env.put(app + 0x30, context)
    env.put(app + 0x34, archive)
    env.put(app + 0x44, rr.randrange(1, 1 << 32))
    extra = obj(env, 0x40, "application-extra")
    env.put(extra + 0x28, o["e28"])
    env.put(app + 0x50, extra)
    env.put(app + 0x78, bpp, o["width"], o["height"])
    env.put(app + 0x9C, o["a9c"])
    # the state stack: the active state is the last entry
    state = obj(env, 0x300, "game-state", words=words_of(rr, 0xC0))
    state_vt = obj(env, 0x40, "state-vtable")
    env.put(state_vt + 0x10, env.stub("state-kind", "thiscall", 0, lambda e, c: o["state"]))
    env.put(state, state_vt)
    env.put(state + 4, app)
    env.put(state + 0xC, context)
    env.put(state + 0x2C, 0)
    stack = obj(env, 16, "state-stack", words=[0x11111111, state, 0x22222222, 0x33333333])
    env.put(app + 0xE0, stack)
    env.put(app + 0xE4, 2)
    w["state"] = state
    w["stack"] = stack
    w["app"] = app

    if o["resource"]:
        # the interface description resource: a memory file the loader reads
        raw = obj(env, 0x40, "interface-bytes", words=words_of(rr, 16))
        stream = obj(env, 0x30, "resource-stream", words=words_of(rr, 12))
        env.put(stream + 0x20, 0)
        res = obj(env, 0x40, "interface-resource", words=words_of(rr, 16))
        env.put(res + 0x14, 0x40)
        env.put(res + 0x18, raw)
        env.put(res + 0x24, stream)
        env.put(app + 0xF0, res)
    else:
        env.put(app + 0xF0, 0)

    # ---------------- input managers
    inp = obj(env, 0x260, "input", words=words_of(rr, 0x98))
    codes = key_codes(rr)
    env.put(inp + 0x1CC, o["input_flags"])
    for index, code in enumerate(codes):
        env.put(inp + 0x1DC + 4 * index, code)
    env.put(inp + 0x20C, o["prev"])
    env.put(inp + 0x210, 0xA5A5A5A5)
    env.put(inp + 0x214, 0x5A5A5A5A)
    env.put(inp + 0xD4, o.get("pad_present", 1))      # [0x35]: unrelated word
    env.put(inp + 0x1D4, o.get("buttons_extra", 1))   # [0x75]
    env.put(inp + 0x1D8, 0)                           # [0x76]
    env.put(inp + 0x40, o.get("pad_buttons", 12))     # [0x10]
    env.put(inp + 0x220, 0x3000, 0xC000, 0x3000, 0xC000)   # joystick dead zones [0x88..0x8b]
    w["codes"] = codes
    # key states by code
    for index in o["press"]:
        keys[codes[index]] = 0x8001
    holder = obj(env, 0x80, "input-holder", words=words_of(rr, 32))
    env.put(holder, inp)
    env.put(G_INPUT, inp)
    env.put(G_INPUT_HOLDER, holder)
    w["input"] = inp

    # ---------------- cursor actor global
    cursor_owner = obj(env, 0x80, "cursor-owner", words=words_of(rr, 32))
    cursor_inner = obj(env, 0x20, "cursor-inner", words=words_of(rr, 8))
    cursor_image = obj(env, 0x90, "cursor-image", words=words_of(rr, 36))
    env.put(cursor_image + 0x7C, o["lives"])
    env.put(cursor_inner + 0x14, cursor_image if o["cursor_actor"] else 0)
    env.put(cursor_owner + 0x6C, cursor_inner)
    env.put(G_CURSOR_ACTOR, cursor_owner if o["cursor_global"] else 0)

    env.put(G_UI, app)
    env.put(G_DT, o["dt"])
    env.put(G_DT_SOURCE, o["dt"] + 7)
    env.put(G_STEP, 0x1357)
    env.put(G_STEP_SOURCE, 0x2468)
    env.put(G_REPEAT_FIRST, o["repeat_first"])
    env.put(G_REPEAT_NEXT, o["repeat_next"])
    env.put(G_SOUND_ON, o["sound_on"])
    env.put(G_SOUND_ID, o["sound_id"])
    env.put(G_FRAME_STEP, o["step"])
    env.put(G_CURRENT_MENU, 0x7777)

    # ---------------- the menu itself
    menu = obj(env, MENU_SIZE, "menu", words=words_of(rr, MENU_SIZE // 4))
    vtable = obj(env, 0x40, "menu-vtable")
    env.put(menu, vtable)

    def menu_ready(e, c):
        observe(e, log, 0xC1, c.receiver, c.arguments, (e.get(menu + 0x2A0), e.get(menu + 0x298), e.get(menu + 0x254)))
        return o.get("ready", 1)
    env.put(vtable + 0x18, env.stub("menu-ready", "thiscall", 0, menu_ready))
    env.put(menu + 4, app)
    env.put(menu + 8, archive)
    env.put(menu + 0xC, context)
    env.write(menu + 0x154, bytes(0x100))
    env.write(menu + 0x254, bytes(0x60))
    w["menu"] = menu

    # actors
    def make_actor(slot_name, flags_extra=0):
        a = obj(env, 0x1B4, "menu-actor-" + slot_name, words=words_of(rr, 0x6D))
        env.put(a, ACTOR_VTABLE)
        env.put(a + 0xC, context)
        env.put(a + 8, 0)
        env.put(a + 0x40, flags_extra)
        env.put(a + 0x4C, rr.randrange(1, 1 << 31), rr.randrange(1, 1 << 31))
        service = obj(env, 0x174, "menu-actor-service", words=words_of(rr, 0x5D))
        env.put(service + 0x10, callback)
        env.put(a + 0x6C, service)
        frame = frame_object(env, rr, 30 + rr.randrange(0, 40, 2), 20 + rr.randrange(0, 30, 2))
        env.put(a + 0x174, frame)
        env.put(a + 0x170, 0)
        return a
    present = o["actors"]
    for bit, slot in enumerate(ACTOR_SLOTS):
        if present & (1 << bit):
            a = make_actor(hex(slot), o.get("actor_flags", rr.randrange(0, 4)))
            env.put(menu + slot, a)
            # a node in the scene list so that it can be removed
            if slot == 0x260:
                node = new_list_node(env, scene, a)
                env.put(a + 0x68, node)
        else:
            env.put(menu + slot, 0)
    # banner surface
    env.put(menu + 0x270, old_surface)
    env.put(menu + 0x274, state if o["state_ptr"] else 0)
    env.put(menu + 0x278, *[rr.randrange(1, 1 << 30) for _ in range(4)])
    env.put(menu + 0x288, rr.randrange(1, 1000), rr.randrange(1, 1000))
    env.put(menu + 0x290, 0, 0)
    env.put(menu + 0x298, o["m298"], o["m29c"], o["m2a0"], o["m2a4"], o["m2a8"])
    env.put(menu + 0x2AC, rr.randrange(1, 40), rr.randrange(1, 40))

    # hotkey map
    env.put(menu + 0x2B4, 0x50BECC, 0, 17, 0, 0, 0, 10)
    if o["map"] == "full":
        build_hotkey_map(env, menu + 0x2B4, rr)

    # the menu container
    build_container(env, menu, o, rr, w)
    return w


def new_list_node(env, scene, actor):
    """Append a node for `actor` to the scene list (head, tail, count at +0x14..+0x1c)."""
    head, tail, count = env.get(scene + 0x14), env.get(scene + 0x18), env.get(scene + 0x1C)
    node = obj(env, 12, "scene-node")
    env.put(node, 0, tail, actor)
    if tail:
        env.put(tail, node)
    else:
        env.put(scene + 0x14, node)
    env.put(scene + 0x18, node)
    env.put(scene + 0x1C, count + 1)
    return node


def build_hotkey_map(env, base, rr):
    """Insert every key of the hotkey table so that the original finds them (no string allocation)."""
    table = obj(env, 17 * 4, "hotkey-buckets")
    env.put(base + 4, table, 17)
    heads = [0] * 17
    for key in HOTKEY_KEYS:
        hashed = 0
        for byte in key:
            hashed = (hashed * 0x21 + byte) & M32
        slot = hashed % 17
        key_pointer = obj(env, len(key) + 4, "hotkey-key", data=key + b"\0")
        node = obj(env, 0x10, "hotkey-node")
        env.put(node, heads[slot], slot, key_pointer, rr.randrange(1, 1 << 32))
        heads[slot] = node
    for slot, head in enumerate(heads):
        env.put(table + 4 * slot, head)
    env.put(base + 0xC, len(HOTKEY_KEYS))


def build_container(env, menu, o, rr, w):
    """The widget container at menu+0x154: an item array, a tree of nodes and two vtables."""
    k = menu + CONTAINER
    log = w["log"]
    ids = list(o["ids"])
    nodes = []
    for index, ident in enumerate(ids):
        node = obj(env, 0x100, "widget-node-%x" % ident, words=words_of(rr, 64))
        sub = node + 0x3C
        table = obj(env, 0x30, "widget-images", words=[rr.randrange(1, 1 << 32) for _ in range(12)])
        env.put(sub + 4, table)
        env.put(sub + 0x14, ident)
        flags = o["flag_of"].get(ident) if ident in o["flag_of"] else rr.randrange(0, 0x40)
        env.put(sub + 0x44, flags)
        env.put(sub + 0x54, rr.randrange(5, 600), rr.randrange(5, 400))
        env.put(sub + 0x5C, rr.randrange(10, 300), rr.randrange(10, 120))
        env.put(sub + 0x64, 0)
        env.put(node + 0x20, 0)
        env.put(node + 0x1C, 0)
        nodes.append(node)
    items = obj(env, 4 * len(ids) + 4, "widget-items")
    for index, node in enumerate(nodes):
        env.put(items + 4 * index, node + 0x3C)
    children = obj(env, 4 * len(ids) + 4, "widget-children")
    for index, node in enumerate(nodes):
        env.put(children + 4 * index, node)
    count = len(ids)
    env.put(k + 0xC, items)
    env.put(k + 0x10, count)
    env.put(k + 0x1C, o["index"] % max(count, 1))
    env.put(k + 0x20, 0)
    env.put(k + 0x24, 0)
    env.put(k + 0x28, 0)
    env.put(k + 0x2C, 0)
    env.put(k + 0x30, o.get("k_last", 0), o.get("k_interval", 0))
    env.put(k + 0x64, children)
    env.put(k + 0x68, count)
    env.put(k + 0x98, 0x1234)
    w["items"] = items
    w["nodes"] = nodes
    w["container"] = k

    vt = obj(env, 0x40, "container-vtable")

    def move(delta):
        def effect(e, c):
            idx = e.get(k + 0x1C)
            if o["k_move"] == "out":
                e.put(k + 0x1C, e.get(k + 0x10) + 2)
            else:
                e.put(k + 0x1C, (idx + delta) % max(e.get(k + 0x10), 1))
            observe(e, log, 0xC2, c.receiver, c.arguments, (idx, delta))
            return 0
        return effect
    env.put(vt, env.stub("container-previous", "thiscall", 0, move(-1)))
    env.put(vt + 4, env.stub("container-next", "thiscall", 0, move(1)))

    def noop(tag):
        def effect(e, c):
            observe(e, log, tag, c.receiver, c.arguments, (e.get(k + 0x1C), e.get(k + 0x24), e.get(k + 0x28)))
            return 0
        return effect
    env.put(vt + 0x14, env.stub("container-slot-14", "thiscall", 0, noop(0xC3)))
    env.put(vt + 0x18, env.stub("container-slot-18", "thiscall", 0, noop(0xC4)))
    env.put(k, vt)

    # the loader entry points of the tree root (embedded at k+0x48)
    root_vt = obj(env, 0x20, "tree-vtable")

    def loader_prepare(e, c):
        observe(e, log, 0xC5, c.receiver, c.arguments)
        return 0

    def loader_load(e, c):
        observe(e, log, 0xC6, c.receiver, c.arguments)
        return 1 if o["loader_ok"] else 0
    env.put(root_vt, env.stub("tree-load", "thiscall", 5, loader_load))
    env.put(root_vt + 8, env.stub("tree-prepare", "thiscall", 1, loader_prepare))
    env.put(k + 0x48, root_vt)


# ----------------------------------------------------------------------------
# Cases
# ----------------------------------------------------------------------------

def menu_of(t):
    return t["menu"]


def container_of(t):
    return t["container"]


def case(label, address, o, args=(), receiver=menu_of, **kw):
    def setup(env, o=o):
        return world(env, o)
    return Case(label, address, setup, receiver=receiver, arguments=args, **kw)


def hotkey_cases(r):
    for variant in ("full", "empty"):
        for n in range(2):
            yield case("hotkeys %s #%d" % (variant, n), F_HOTKEYS, draw(r, map=variant))


def align_cases(r):
    for mode in range(0, 8):
        for count in (0, 1, 2, 3, 5):
            ids = tuple(0x6000 + i for i in range(count))
            value = r.choice([r.randrange(-500, 900), 0, r.randrange(0, 1 << 31)])
            yield case("align mode %d x%d" % (mode, count), F_ALIGN, draw(r, ids=ids), args=(mode, u(value)), receiver=container_of)
    for mode in (0x80000000, 0xFFFFFFFF, 6):
        yield case("align unknown mode %x" % mode, F_ALIGN, draw(r, ids=(0x61, 0x62, 0x63)), args=(mode, r.randrange(1, 900)), receiver=container_of)


def enable_cases(r):
    for select in (True, False):
        for a10 in (0, 1):
            for e28 in (0, 1):
                yield case("enable select=%s a10=%d e28=%d" % (select, a10, e28), F_ENABLE,
                           draw(r, select=select, a10=r.randrange(1, 99) if a10 else 0, e28=r.randrange(1, 99) if e28 else 0,
                                flag_of={0x59DB: r.randrange(0, 0x80), 0x5AA1: r.randrange(0, 0x80), 0x5AA2: r.randrange(0, 0x80)}))
    yield case("enable no widgets", F_ENABLE, draw(r, ids=(0x61, 0x62)))
    yield case("enable flags set", F_ENABLE, draw(r, flag_of={i: 0xFF for i in (0x59DB, 0x5AA1, 0x5AA2, 0x5AA3, 0x5AA4)}))
    yield case("enable flags clear", F_ENABLE, draw(r, a10=0, flag_of={i: 0 for i in (0x59DB, 0x5AA1, 0x5AA2, 0x5AA3, 0x5AA4)}))


def audio_cases(r):
    for page in (ID_MAIN, ID_OPTIONS, 10000, 0x4E21):
        for present in range(8):
            actors = 0
            for bit in range(3):
                if present & (1 << bit):
                    actors |= 1 << (4 + bit)      # 0x264, 0x268, 0x26c
            for bits in (0x20, 0x00):
                flags = {0x5B06: bits | r.choice([0, 6]), 0x5AA1: bits | r.choice([0, 2, 4]), 0x5AA4: bits | r.choice([0, 6])}
                if page in PAGES or bits == 0:
                    yield case("audio page %x actors %d flags %x" % (page, present, bits), F_AUDIO,
                               draw(r, actors=actors, flag_of=flags, m298=r.choice([page, ID_MAIN, ID_OPTIONS])), args=(page,))
    yield case("audio options mixed flags", F_AUDIO,
               draw(r, actors=0x70, flag_of={0x5B06: 0x00, 0x5AA1: 0x20, 0x5AA4: 0x02}, m298=ID_OPTIONS), args=(ID_OPTIONS,))
    yield case("audio options second off", F_AUDIO,
               draw(r, actors=0x70, flag_of={0x5B06: 0x00, 0x5AA1: 0x02, 0x5AA4: 0x00}, m298=ID_OPTIONS), args=(ID_OPTIONS,))
    yield case("audio no widgets main", F_AUDIO, draw(r, actors=0x70, ids=(0x61,), m298=ID_MAIN), args=(ID_MAIN,))
    yield case("audio no widgets options", F_AUDIO, draw(r, actors=0x70, ids=(0x61,), m298=ID_OPTIONS), args=(ID_OPTIONS,))
    yield case("audio options page mismatch", F_AUDIO,
               draw(r, actors=0x70, flag_of={0x5B06: 0x20, 0x5AA1: 0x20, 0x5AA4: 0x20}, m298=ID_MAIN), args=(ID_OPTIONS,))
    yield case("audio main page mismatch", F_AUDIO,
               draw(r, actors=0x70, flag_of={0x5B06: 0x20, 0x5AA1: 0x20, 0x5AA4: 0x20}, m298=ID_OPTIONS), args=(ID_MAIN,))


def layout_cases(r):
    for page in (0x4E22, 0x4E25, ID_MAIN, 0x4E23, ID_OPTIONS, 10000, 0x59DC, 0x4E24, 0x4E21, 0, 0xFFFFFFFF):
        for a9c in (0, 1):
            for copy in ("faithful",):
                count = r.choice([0, 1, 2, 3, 4])
                ids = tuple(0x6100 + i for i in range(count))
                yield case("layout %x a9c=%d x%d" % (page, a9c, count), F_LAYOUT,
                           draw(r, a9c=a9c, ids=ids), args=(page,))
    # the left and right extremes: item widths against the rectangle
    for variant in range(6):
        count = r.choice([1, 2, 3, 5])
        ids = tuple(0x6200 + i for i in range(count))
        yield case("layout widths #%d" % variant, F_LAYOUT,
                   draw(r, ids=ids, width=r.choice([200, 640, 1024]), height=r.choice([300, 480, 777]),
                        setrect=r.choice(["faithful", "shifted"])), args=(r.choice([0x4E22, 0x59DA, ID_OPTIONS, 10000]),))
    for height in (0, 1, 2, 100, 479, 480, 481, 1000, 4097):
        yield case("layout height %d" % height, F_LAYOUT, draw(r, height=height, ids=(0x6300, 0x6301)), args=(0x4E22,))
    for width in (0, 1, 3, 4, 5, 7, 1023):
        yield case("layout width %d" % width, F_LAYOUT, draw(r, width=width, ids=(0x6300, 0x6301)), args=(ID_MAIN,))


def mask_cases(r):
    geometries = [(3, 16, 16), (1, 4, 4), (2, 8, 12), (4, 12, 32), (5, 9, 20), (2, 3, 8), (3, 0, 8), (0, 8, 8),
                  (2, -8, 8), (2, -1, 8), (1, 5, 5), (6, 40, 64), (3, 17, 40)]
    for bpp in (8, 16):
        for rows, wbytes, pitch in geometries:
            yield case("mask %d-bit %dx%d pitch %d" % (bpp, rows, wbytes, pitch), F_MASK,
                       draw(r, bpp=bpp, rows=rows, wbytes=wbytes, pitch=pitch))
        for rows, wbytes, pitch in [(r.randrange(1, 12), r.randrange(0, 70), r.randrange(0, 90)) for _ in range(6)]:
            yield case("mask %d-bit random %dx%d pitch %d" % (bpp, rows, wbytes, pitch), F_MASK,
                       draw(r, bpp=bpp, rows=rows, wbytes=wbytes, pitch=max(pitch, 0)))
        yield case("mask %d-bit no pixel pointer" % bpp, F_MASK, draw(r, bpp=bpp, pixel_ptr=False))
        yield case("mask %d-bit surface lost then restored" % bpp, F_MASK,
                   draw(r, bpp=bpp, lock_status=(0x887601C2, 0), restore=True))
        yield case("mask %d-bit surface lost, restore fails" % bpp, F_MASK,
                   draw(r, bpp=bpp, lock_status=(0x887601C2, 0), restore=False))
    for bpp in (0, 4, 15, 24, 32):
        yield case("mask %d-bit does nothing" % bpp, F_MASK, draw(r, bpp=bpp))


def clear_cases(r):
    for bpp in (8, 16, 24):
        for flag in (0, 2):
            for blt in (0, 0x887601C2):
                yield case("clear %d-bit engine flag %d blt %x" % (bpp, flag, blt), F_CLEAR,
                           draw(r, bpp=bpp, engine_flag=flag, blt_status=blt, restore=blt != 0))
    yield case("clear 16-bit odd rows", F_CLEAR, draw(r, bpp=16, rows=5, wbytes=22, pitch=48))
    yield case("clear 8-bit odd rows", F_CLEAR, draw(r, bpp=8, rows=5, wbytes=22, pitch=48))


def surface_cases(r):
    for old in (True, False):
        for ok in (True, False):
            for order in (0, 1):
                if not old and order:
                    continue
                yield case("surface old=%s ok=%s order=%d" % (old, ok, order), F_SURFACE,
                           draw(r, old_surface=old, surface_ok=ok, surface_order=order, new_rect=tuple(r.randrange(0, 400) for _ in range(4))))
    for variant in range(10):
        left, top = r.randrange(-50, 300), r.randrange(-50, 300)
        rect = (left, top, left + r.randrange(0, 700), top + r.randrange(0, 500))
        yield case("surface rect #%d" % variant, F_SURFACE,
                   draw(r, new_rect=rect, width=r.randrange(0, 1200), height=r.randrange(0, 900),
                        copy=r.choice(["faithful", "shifted"]), old_surface=r.choice([True, False])))
    yield case("surface odd dimensions", F_SURFACE, draw(r, new_rect=(0, 0, 101, 77), width=641, height=481))
    yield case("surface negative rect", F_SURFACE, draw(r, new_rect=(-20, -9, 31, 15), width=640, height=480))
    yield case("surface only copy shifted", F_SURFACE, draw(r, new_rect=(10, 20, 301, 201), copy="shifted"))


def banner_cases(r):
    for page in (0x4E22, 0x4E25, 10000, 0, ID_MAIN, 0x4E23):
        for present in (False, True):
            for lives in (1, 2, 7):
                if page != 0x4E22 and lives != 2:
                    continue
                yield case("banner %x existing=%s lives=%d" % (page, present, lives), F_BANNER,
                           draw(r, actors=0x08 if present else 0, lives=lives, scene_actors=r.randrange(0, 3)), args=(page,))
    yield case("banner clawicide no cursor global", F_BANNER, draw(r, cursor_global=False, actors=0x08), args=(0x4E22,))
    yield case("banner clawicide no cursor image", F_BANNER, draw(r, cursor_actor=False), args=(0x4E22,))
    yield case("banner clawicide lives zero", F_BANNER, draw(r, lives=0), args=(0x4E22,))
    yield case("banner clawicide lives negative", F_BANNER, draw(r, lives=-3), args=(0x4E22,))
    yield case("banner endgame insert before", F_BANNER,
               draw(r, scene_actors=3, scene_prio=(50, 20000, 30000), actors=0x08), args=(0x4E25,))
    yield case("banner clawicide insert middle", F_BANNER,
               draw(r, scene_actors=3, scene_prio=(100, 0x270E, 20000)), args=(0x4E22,))
    yield case("banner endgame blocked by flag", F_BANNER,
               draw(r, scene_actors=3, scene_prio=(20000, 30000, 40000), scene_flags=(2, 0, 2)), args=(0x4E25,))
    yield case("banner endgame all lower", F_BANNER,
               draw(r, scene_actors=3, scene_prio=(1, 2, 3)), args=(0x4E25,))


NEUTRAL = tuple(0x6001 + i for i in range(9))
DIRECTION = (0x10000000, 0x20000000, 0x40000000, 0x80000000)


def input_cases(r):
    base = dict(ids=NEUTRAL, actors=0x06, index=3)
    # single direction keys, each with every sound outcome
    for idx in range(4):
        yield case("input key %d" % idx, F_INPUT, draw(r, press=(idx,), **base))
    for z30, click, sound in ((0, True, 1), (0, True, 0), (0, False, 1), (1, True, 1)):
        for idx in (0, 3):
            yield case("input key %d sound z30=%d click=%s on=%d" % (idx, z30, click, sound), F_INPUT,
                       draw(r, press=(idx,), z30=z30, click=click, sound_on=sound, **base))
    for pressed in ((3, 2), (2, 0), (0, 1), (1, 3), (0, 2), (3, 0, 1), (1, 2, 3), (0, 1, 2, 3)):
        yield case("input keys %s" % (pressed,), F_INPUT, draw(r, press=pressed, **base))
    # the item keys
    for idx in range(4, 12):
        yield case("input action key %d" % idx, F_INPUT, draw(r, press=(idx,), **base))
    for pressed in ((4, 5), (11, 4, 7), (0, 6), (3, 9), (1, 10), (2, 8, 5), tuple(range(4, 12))):
        yield case("input action keys %s" % (pressed,), F_INPUT, draw(r, press=pressed, **base))
    # joystick
    center = 0x8000
    for label, joy in (("left", (0x1000, center, 0)), ("right", (0xF000, center, 0)), ("up", (center, 0x1000, 0)),
                       ("down", (center, 0xF000, 0)), ("center", (center, center, 0)), ("button", (center, center, 1)),
                       ("confirm", (center, center, 0x100)), ("confirm and left", (0x1000, center, 0x100)),
                       ("all buttons", (center, center, 0x1FF))):
        yield case("input joystick %s" % label, F_INPUT, draw(r, input_flags=2, joy=joy, **base))
    yield case("input joystick confirm with keys", F_INPUT, draw(r, input_flags=3, joy=(center, center, 0x100), press=(5,), **base))
    yield case("input joystick confirm held", F_INPUT, draw(r, input_flags=2, joy=(center, center, 0x100), prev=0x100, **base))
    yield case("input joystick confirm no extra buttons", F_INPUT,
               draw(r, input_flags=2, joy=(center, center, 0x100), buttons_extra=0, **base))
    yield case("input joystick confirm few buttons", F_INPUT,
               draw(r, input_flags=2, joy=(center, center, 0x100), pad_buttons=4, **base))
    # nothing pressed
    yield case("input idle", F_INPUT, draw(r, **base))
    # held keys: the repeat timer
    for idx in range(4):
        mask = DIRECTION[idx]
        for label, dt, timer in (("timer runs", 7, 100), ("timer expires", 100, 7), ("timer exact", 40, 40), ("timer zero", 9, 0)):
            yield case("input held %d %s" % (idx, label), F_INPUT,
                       draw(r, press=(idx,), prev=mask, dt=dt, m2a4=timer, **base))
    yield case("input held and action key", F_INPUT, draw(r, press=(3, 6), prev=DIRECTION[3], **base))
    yield case("input held up while down new", F_INPUT, draw(r, press=(0, 1), prev=DIRECTION[0], dt=50, m2a4=3, **base))
    yield case("input held two directions", F_INPUT, draw(r, press=(2, 3), prev=DIRECTION[2] | DIRECTION[3], dt=50, m2a4=3, **base))
    # no index change, no item
    yield case("input one item cannot move", F_INPUT, draw(r, press=(3,), ids=(0x6001,), actors=0x06, index=0))
    yield case("input no items", F_INPUT, draw(r, press=(3,), ids=(), actors=0x06, index=0))
    yield case("input moves out of range", F_INPUT, draw(r, press=(3,), k_move="out", **base))
    yield case("input moves out of range with held key", F_INPUT, draw(r, press=(2,), k_move="out", **base))
    yield case("input repeat right then left items", F_INPUT, draw(r, press=(3,), prev=DIRECTION[3], dt=60, m2a4=2, **base))
    for variant in range(6):
        pressed = tuple(sorted(r.sample(range(12), r.randrange(0, 5))))
        prev = r.choice([0] + [m for m in DIRECTION])
        yield case("input random #%d" % variant, F_INPUT,
                   draw(r, press=pressed, prev=prev, dt=r.randrange(1, 30), m2a4=r.randrange(0, 40), **base))


def frame_cases(r):
    full = 0x7F
    base = dict(ids=NEUTRAL, actors=full)
    for flip in (0, 1):
        for ready in (0, 1):
            yield case("frame flip=%d ready=%d" % (flip, ready), F_FRAME, draw(r, flip_status=flip, ready=ready, **base))
    yield case("frame no flip interface not ready", F_FRAME, draw(r, flip_iface=False, ready=0, **base))
    yield case("frame not ready no owner", F_FRAME, draw(r, flip_status=1, ready=0, owner=False, **base))
    yield case("frame already finished", F_FRAME, draw(r, m2a0=r.randrange(1, 9), **base))
    yield case("frame finished while not ready", F_FRAME, draw(r, m2a0=1, flip_status=1, ready=0, **base))
    for actors in (0, 0x7E, 0x7D, 0x7B, 0x77, 0x6F, 0x5F, 0x3F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x25, 0x5A):
        yield case("frame actors %02x" % actors, F_FRAME, draw(r, actors=actors, ids=NEUTRAL, m298=r.choice([ID_MAIN, ID_OPTIONS, 10000])))
    for step, timer in ((5, 100), (100, 5), (50, 50), (1, 2), (0, 0), (0, 1), (0xFFFFFFFF, 3), (3, 0xFFFFFFFF)):
        yield case("frame timer step=%x left=%x" % (step, timer), F_FRAME, draw(r, step=step, m29c=timer, **base))
    yield case("frame without timer", F_FRAME, draw(r, a9c=0, step=1, m29c=1000, **base))
    yield case("frame without timer expired", F_FRAME, draw(r, a9c=0, step=1000, m29c=1, **base))
    for z30, select, on in ((0, True, 1), (0, True, 0), (0, False, 1), (5, True, 1)):
        yield case("frame expires z30=%d select=%s on=%d" % (z30, select, on), F_FRAME,
                   draw(r, step=900, m29c=10, z30=z30, select=select, sound_on=on, **base))
    for copy in ("faithful", "shifted"):
        for cursor in ((0, 0), (17, 29), (900, 700), (0xFFFF, 3)):
            yield case("frame copy=%s cursor=%s" % (copy, cursor), F_FRAME, draw(r, copy=copy, cursor=cursor, **base))
    for page in (ID_MAIN, ID_OPTIONS, 10000, 0, 0x4E21):
        yield case("frame page %x" % page, F_FRAME, draw(r, m298=page, flag_of={0x5B06: 0x20, 0x5AA1: 0x20, 0x5AA4: 0x02}, **base))
    yield case("frame with a key press", F_FRAME, draw(r, press=(3,), index=2, **base))
    yield case("frame with a held key", F_FRAME, draw(r, press=(0,), prev=DIRECTION[0], dt=5, m2a4=1, **base))


def enter_cases(r):
    full = 0x7F
    for param in (0xD, 9, 1, 5, 0, 0x10, 0xFFFFFFFF):
        yield case("enter %x" % param, F_ENTER, draw(r, ids=NEUTRAL, actors=0), args=(param,))
    for param in (9, 1):
        for actors in (0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x7F, 0x7E, 0x75, 0x4B):
            yield case("enter %d actors %02x" % (param, actors), F_ENTER, draw(r, ids=NEUTRAL, actors=actors), args=(param,))
    for param in (9, 1):
        for state_ptr in (True, False):
            for bpp in (8, 16, 24):
                if param == 1 and bpp != 16:
                    continue
                yield case("enter %d state=%s bpp=%d" % (param, state_ptr, bpp), F_ENTER,
                           draw(r, ids=NEUTRAL, actors=0x10, state_ptr=state_ptr, bpp=bpp), args=(param,))
    for z30, select, on, click in ((0, True, 1, True), (0, True, 0, True), (0, False, 1, True), (1, True, 1, True)):
        yield case("enter 1 sound z30=%d select=%s on=%d" % (z30, select, on), F_ENTER,
                   draw(r, ids=NEUTRAL, actors=0, z30=z30, select=select, sound_on=on), args=(1,))
    for cursor_empty in (False, True):
        yield case("enter cursor image empty=%s" % cursor_empty, F_ENTER, draw(r, ids=NEUTRAL, actors=0, cursor_empty=cursor_empty), args=(1,))
    for cursor in ((0, 0), (400, 300), (1023, 767)):
        yield case("enter cursor %s" % (cursor,), F_ENTER, draw(r, ids=NEUTRAL, actors=0, cursor=cursor), args=(9,))
    for peek, show in (((0,), (-1,)), ((1, 1, 0), (2, 1, 0, -1)), ((1,) * 70 + (0,), (0, -1)), ((1, 0), (5, 4, 3, 2, 1, 0, -2))):
        yield case("enter peek %d show %s" % (len(peek), show), F_ENTER, draw(r, ids=NEUTRAL, actors=0, peek=peek, cursor_seq=show), args=(9,))
    for size in ((640, 480), (800, 600), (1, 1), (0, 0), (1023, 767), (1920, 1080)):
        yield case("enter size %s" % (size,), F_ENTER, draw(r, ids=NEUTRAL, actors=0, width=size[0], height=size[1]), args=(9,))
    for count in (0, 1, 2, 5):
        yield case("enter %d widgets" % count, F_ENTER, draw(r, ids=tuple(0x6400 + i for i in range(count)), actors=0), args=(9,))
    yield case("enter scene already has actors", F_ENTER, draw(r, ids=NEUTRAL, actors=0, scene_actors=3, scene_prio=(100, 0x270E, 20000)), args=(9,))
    yield case("enter scene actors lower", F_ENTER, draw(r, ids=NEUTRAL, actors=0, scene_actors=3, scene_prio=(1, 2, 3)), args=(1,))
    yield case("enter shifted rectangles", F_ENTER, draw(r, ids=NEUTRAL, actors=0, setrect="shifted"), args=(9,))
    yield case("enter negative left edge", F_ENTER, draw(r, ids=NEUTRAL, actors=0, width=-300, height=200), args=(9,))


def init_case(label, o, level=None, extra=None, r=None):
    """Call the initializer with the level number the archive was built for (or a different one)."""
    number = o["level"] if level is None else level
    return case(label, F_INIT, o, args=(lambda t: t["app"], number, o["seed"] % 977 if extra is None else extra))


def init_cases(r):
    base = dict(ids=NEUTRAL)
    for state in (3, 4, 5, 0, 1, 2, 0xFFFFFFFF):
        yield init_case("init state %x" % state, draw(r, state=state, **base))
    yield init_case("init resource loader fails", draw(r, resource=True, loader_ok=False, **base))
    yield init_case("init resource loader fails at level 1", draw(r, resource=True, loader_ok=False, level=1, **base))
    for level in (1, 2, 9, 13):
        yield init_case("init level %d" % level, draw(r, level=level, **base))
    yield init_case("init level missing", draw(r, level=5, **base), level=6)
    yield init_case("init level zero missing", draw(r, level=5, **base), level=0)
    yield init_case("init level missing with resource", draw(r, level=5, resource=True, **base), level=7)
    for ok in (True, False):
        for old in (True, False):
            yield init_case("init surface ok=%s old=%s" % (ok, old), draw(r, surface_ok=ok, old_surface=old, **base))
    for size in ((640, 480), (801, 601), (2, 2), (1025, 769), (0, 0), (1, 1)):
        yield init_case("init size %s" % (size,), draw(r, width=size[0], height=size[1], **base))
    for flags in (0, 1, 4, 5):
        yield init_case("init input flags %d" % flags, draw(r, input_flags=flags, **base))
    for count in (0, 1, 3, 9):
        yield init_case("init %d widgets" % count, draw(r, ids=tuple(0x6500 + i for i in range(count))))
    yield init_case("init hotkeys missing", draw(r, map="empty", **base))
    yield init_case("init sound off", draw(r, sound_on=0, **base))
    yield init_case("init shifted rectangles", draw(r, setrect="shifted", copy="shifted", **base))
    yield init_case("init all ids present", draw(r))


def cases(random_source):
    r = random_source
    yield from hotkey_cases(r)
    yield from align_cases(r)
    yield from enable_cases(r)
    yield from audio_cases(r)
    yield from layout_cases(r)
    yield from mask_cases(r)
    yield from clear_cases(r)
    yield from surface_cases(r)
    yield from banner_cases(r)
    yield from input_cases(r)
    yield from frame_cases(r)
    yield from enter_cases(r)
    yield from init_cases(r)
