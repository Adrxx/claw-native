"""Cases for pause_menu_commands: Pause menu command callback and dispatcher.

Every case builds a complete, deterministic menu world.  Sound objects are "live": their
helper enable word is nonzero, so the sound helpers reach the stand-in vtable slots and each
sound request shows up as a compared event.  Nothing here depends on the random source for
coverage; random values only vary the object contents.
"""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, set_rect

# Owned functions
SHIM = 0x4505F0
DISPATCH = 0x450B50
H_59D9 = 0x450E00
H_AUDIO = 0x450ED0
H_DISPLAY = 0x451230
H_55F1 = 0x451410
H_5DC1 = 0x451530
CLEAR_SELECT = 0x451660
DISARM = 0x451210
APPLY_AUDIO = 0x4519F0
APPLY_DISPLAY = 0x4526F0
TOGGLE_FRONT = 0x42CDF0

# Fixtures
POST = 0x546D50
SETRECT = 0x546D5C
COPYRECT = 0x546D58
LSTRLEN = 0x5469E4
INTERLOCK_DEC = 0x5469E8
INTERLOCK_INC = 0x5469EC

# Globals
G_MENU = 0x53789C
G_MASTER = 0x532C0C
G_VOLUME = 0x532C10

KEY_SELECT = b"GAME_SELECT"
KEY_DISABLE = b"GAME_DISABLE"
KEY_1055 = b"GAME_1055"


def hash_key(key):
    value = 0
    for byte in key:
        value = (value * 0x21 + byte) & 0xFFFFFFFF
    return value


def lstrlen_effect(env, call):
    return len(env.cstr(call.arguments[0], 4096))


def increment_effect(env, call):
    value = (env.get(call.arguments[0]) + 1) & 0xFFFFFFFF
    env.put(call.arguments[0], value)
    return value


def decrement_effect(env, call):
    value = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
    env.put(call.arguments[0], value)
    return value


def copy_rect_effect(env, call):
    env.write(call.arguments[0], env.read(call.arguments[1], 16))
    return 1


def install_services(env, post=None):
    """Every scripted fixture gets a deterministic behavior."""
    env.override(POST, post or returns(1))
    env.override(SETRECT, set_rect)
    env.override(COPYRECT, copy_rect_effect)
    env.override(LSTRLEN, lstrlen_effect)
    env.override(INTERLOCK_INC, increment_effect)
    env.override(INTERLOCK_DEC, decrement_effect)


def status_effect(value):
    """Interface method (obj, &status): write the status word and report success."""
    def effect(env, call):
        env.put(call.arguments[1], value)
        return 0
    return effect


def make_sound(env, tag, live=True, playing=False, on_start=None):
    """A sound entry S: S+0x10 -> X (sample), X+0xc -> interface, X+0x10 -> Y (driver), voice V in X's list."""
    iface = env.object(0x20, f"{tag}-iface", fill=0)
    methods = env.object(0x60, f"{tag}-methods", fill=0)
    driver = env.object(0x84, f"{tag}-driver", fill=0)
    voice_iface = env.object(0x20, f"{tag}-voice-iface", fill=0)
    voice_methods = env.object(0x60, f"{tag}-voice-methods", fill=0)
    sample = env.object(0x40, f"{tag}-sample", fill=0)
    voice = env.object(0x40, f"{tag}-voice", fill=0)
    entry = env.object(0x18, f"{tag}-entry", fill=0)
    seed = (sum(tag.encode()) * 0x11) & 0xFFFF
    env.put(driver + 0x78, 0x100 + seed if live else 0)
    env.put(sample + 0x0C, iface)
    env.put(sample + 0x10, driver)
    env.put(sample + 0x14, 0x5000 + seed)
    env.put(sample + 0x18, 0x3300 + seed)
    env.put(sample + 0x1C, 0x77 + seed)
    env.put(sample + 0x20, 0x44 + seed)
    env.put(sample + 0x30, voice + 4, voice + 4)
    env.put(voice + 0x0C, voice_iface)
    env.put(voice + 0x10, driver)
    env.put(voice + 0x14, 0x1F5 + seed)
    env.put(voice + 0x18, 0x1111 + seed)
    env.put(voice + 0x30, 1)
    env.put(entry + 0x10, sample)
    env.put(iface, methods)
    env.put(voice_iface, voice_methods)
    for table, label, flag in ((methods, "sample", 1 if playing else 0), (voice_methods, "voice", 0)):
        env.put(table + 0x24, env.stub(f"{tag}-{label}-status", "stdcall", 2, status_effect(flag)))
        start = on_start if (label == "voice" and on_start is not None) else returns(0)
        env.put(table + 0x30, env.stub(f"{tag}-{label}-start", "stdcall", 4, start))
        env.put(table + 0x3C, env.stub(f"{tag}-{label}-frequency", "stdcall", 2, returns(0)))
        env.put(table + 0x40, env.stub(f"{tag}-{label}-pan", "stdcall", 2, returns(0)))
        env.put(table + 0x44, env.stub(f"{tag}-{label}-volume", "stdcall", 2, returns(0)))
        env.put(table + 0x48, env.stub(f"{tag}-{label}-stop", "stdcall", 1, returns(0)))
    return entry


def make_map(env, entries, buckets=7, decoys=True):
    """A string map {key: value} laid out as the original's hash map: [+4] bucket array, [+8] bucket count."""
    area = env.object(0x20, "string-map", fill=0)
    table = env.object(buckets * 4, "buckets", fill=0)
    env.put(area + 4, table, buckets, len(entries))
    for key, value in entries.items():
        slot = hash_key(key) % buckets
        text = env.object(len(key) + 1, "key", data=key + b"\0")
        node = env.object(0x10, "node", fill=0)
        env.put(node, env.get(table + slot * 4), 0xABC0 + slot, text, value)
        env.put(table + slot * 4, node)
    if decoys:
        for slot in range(buckets):
            text = env.object(8, "decoy", data=b"DECOY_%d\0" % slot)
            node = env.object(0x10, "decoy-node", fill=0)
            env.put(node, env.get(table + slot * 4), 0xDEC0 + slot, text, 0xDEAD0000 + slot)
            env.put(table + slot * 4, node)
    return area


AUDIO_PAGE = b"GAME_INGAMEMENU_MAIN_OPTIONS_AUDIO"
DISPLAY_PAGE = b"GAME_INGAMEMENU_MAIN_OPTIONS_DISPLAY"


def make_page(env, tag, seed):
    """A menu page record: min index at +100, max at +0x68, item table at +0x14; item value at +0x2c is a frame."""
    page = env.object(0x80, f"{tag}-page", fill=0)
    items = env.object(41 * 4, f"{tag}-items", fill=0)
    env.put(page + 100, 0)
    env.put(page + 0x68, 40)
    env.put(page + 0x14, items)
    for index in range(41):
        item = env.object(0x30, f"{tag}-item{index}", fill=0)
        frame = env.object(0x30, f"{tag}-frame{index}", fill=0)
        env.put(frame + 0x14, seed + index * 3 + 1)
        env.put(frame + 0x18, seed + 700 - index * 5)
        env.put(item + 0x2C, frame)
        env.put(items + index * 4, item)
    return page


def make_controls(env, menu, ids, seed):
    """Control tree under menu+0x154: root at menu+0x19c with one child node per id."""
    root = menu + 0x19C
    env.put(menu + 0x1EC, 0x1)
    if not ids:
        env.put(menu + 0x1BC, 0)
        return {}
    nodes = env.object(len(ids) * 4, "ctl-children", fill=0)
    env.put(menu + 0x1B8, nodes)
    env.put(menu + 0x1BC, len(ids))
    made = {}
    for position, ident in enumerate(ids):
        node = env.object(0xB0, f"ctl-{ident:#x}", fill=0)
        frames = env.object(8 * 4, f"ctl-{ident:#x}-slots", fill=0)
        for slot in range(8):
            frame = env.object(0x30, f"ctl-{ident:#x}-slot{slot}", fill=0)
            env.put(frame + 0x14, 1 + slot * 7 + seed)
            env.put(frame + 0x18, 2 + slot * 5 + seed)
            env.put(frames + slot * 4, frame)
        env.put(node + 0x40, frames, 8)
        env.put(node + 0x50, ident)
        env.put(node + 0x7C, 0x7C7C)
        env.put(node + 0x80, o_flags(ident, seed))
        env.put(node + 0x98, 0x9898, 0x9999)
        env.put(nodes + position * 4, node)
        made[ident] = node
    return made


def o_flags(ident, seed):
    return (ident * 5 + seed) & 0x3F


def make_surface(env, tag):
    """A surface-like object whose +8 is an interface with Blt (0x14) and Restore-like (0x2c) stand-ins."""
    surface = env.object(0xC0, f"{tag}-surface", fill=0)
    iface = env.object(0x20, f"{tag}-surface-iface", fill=0)
    table = env.object(0x80, f"{tag}-surface-methods", fill=0)
    env.put(surface + 8, iface)
    env.put(iface, table)
    env.put(table + 0x14, env.stub(f"{tag}-blt", "stdcall", 6, returns(0)))
    env.put(table + 0x2C, env.stub(f"{tag}-restore", "stdcall", 3, returns(0)))
    env.put(table + 0x58, env.stub(f"{tag}-desc", "stdcall", 2, returns(0)))
    return surface


def make_engine(env, tag):
    """The graphics engine reached through B+0x1c: a DirectDraw interface that creates surfaces, and a pointer list."""
    engine = env.object(0x480, f"{tag}-engine", fill=0)
    ddraw = env.object(0x20, f"{tag}-ddraw", fill=0)
    ddraw_table = env.object(0x80, f"{tag}-ddraw-methods", fill=0)
    created = env.object(0x20, f"{tag}-created", fill=0)
    created_table = env.object(0x80, f"{tag}-created-methods", fill=0)
    env.put(engine, ddraw)
    env.put(ddraw, ddraw_table)
    env.put(created, created_table)
    env.put(created_table + 0x14, env.stub(f"{tag}-created-blt", "stdcall", 6, returns(0)))
    env.put(created_table + 0x58, env.stub(f"{tag}-created-desc", "stdcall", 2, returns(0)))

    def create_surface(env, call):
        env.put(call.arguments[2], created)
        return 0
    env.put(ddraw_table + 0x18, env.stub(f"{tag}-create-surface", "stdcall", 4, create_surface))
    env.put(engine + 0x3B8 + 0x18, 10)
    return engine


def make_world(env, **o):
    """Build the whole menu graph. Returns tokens."""
    live = o.get("live", True)
    install_services(env, o.get("post"))
    t = {}
    entries = {}
    ctx = {}
    hook = o.get("hook", ())

    def fire(env, call):
        if hook and env.calls_so_far(call.function) == 1:
            for target, offset, value in hook:
                env.put(ctx[target] + offset, ctx[value] if isinstance(value, str) else value)
        return 0

    for key, name in ((KEY_SELECT, "select"), (KEY_DISABLE, "disable"), (KEY_1055, "p1055")):
        if o.get(f"has_{name}", True):
            entries[key] = make_sound(env, name, live=o.get(f"live_{name}", live),
                                      playing=(name == "p1055" and o.get("playing", False)),
                                      on_start=fire if name == "select" else None)
    seed = o.get("seed", 3)
    if o.get("ui", False):
        entries[AUDIO_PAGE] = make_page(env, "audio", 100 + seed)
        entries[DISPLAY_PAGE] = make_page(env, "display", 300 + seed)
    menu = env.object(0x300, "menu", fill=0)
    app = env.object(0x140, "app", fill=0)
    hwnd_obj = env.object(0x10, "hwnd-holder", fill=0)
    env.put(hwnd_obj + 4, o.get("hwnd", 0x1234ABCD))
    dev = env.object(0x30, "dev", fill=0)
    eng = env.object(0x38, "engine", fill=0)
    emap = make_map(env, entries, buckets=o.get("buckets", 7), decoys=o.get("decoys", True))
    env.write(eng + 0x10, env.read(emap, 0x20))
    env.put(eng + 0x30, o.get("mute", 0))
    env.put(dev + 0x28, eng)
    env.put(dev + 0x24, 0)
    # UI string table: 0x5371fc -> R, R+0x30 -> X, X+0x10 -> eng (map at eng+0x10)
    root = env.object(0x40, "ui-root", fill=0)
    xo = env.object(0x20, "ui-x", fill=0)
    env.put(xo + 0x10, eng)
    env.put(root + 0x30, xo)
    env.put(0x5371FC, root)
    # music
    music = env.object(0x40, "music", fill=0)
    music_iface = env.object(0x20, "music-iface", fill=0)
    music_methods = env.object(0x40, "music-methods", fill=0)
    env.write(music_iface, struct.pack("<I", music_methods))
    env.put(music_methods + 0x24, env.stub("music-slot-24", "thiscall", 2, returns(0x31)))
    env.put(music_methods + 0x28, env.stub("music-slot-28", "thiscall", 0, returns(0x32)))
    env.put(music_methods + 0x30, env.stub("music-slot-30", "thiscall", 0, returns(0x33)))
    env.put(music + 0x1C, music_iface if o.get("music_live", True) else 0)
    env.put(music + 0x20, 0x600D)
    # callback list holder G
    holder_h = env.object(0x40, "G-owner", fill=0)
    holder = env.object(0x30, "G", fill=0)
    env.put(holder, holder_h)
    env.put(holder + 0x24, o.get("g_active", 0))
    env.put(holder + 0x28, 0xA11CE)
    env.put(holder + 0x2C, 0xB0B)
    if o.get("g_items", False):
        nodes = []
        for index in range(2):
            item = env.object(0x20, f"G-item{index}", fill=0)
            item_vt = env.object(0x10, f"G-item{index}-vt", fill=0)
            sub = env.object(0x20, f"G-item{index}-sub", fill=0)
            sub_y = env.object(0x84, f"G-item{index}-sub-driver", fill=0)
            sub_iface = env.object(0x20, f"G-item{index}-sub-iface", fill=0)
            sub_vt = env.object(0x60, f"G-item{index}-sub-vt", fill=0)
            env.put(sub_y + 0x78, 1)
            env.put(sub + 0x10, sub_y)
            env.put(sub + 0xC, sub_iface)
            env.put(sub_iface, sub_vt)
            env.put(sub_vt + 0x48, env.stub(f"G-item{index}-stop", "stdcall", 1, returns(0)))
            env.put(item_vt + 4, env.stub(f"G-item{index}-notify", "stdcall", 3, returns(0)))
            env.put(item, item_vt)
            env.put(item + 4, sub if index == 0 else 0)
            env.put(item + 0x14, 0x99 + index)
            node = env.object(0x10, f"G-node{index}", fill=0)
            env.put(node + 8, item)
            nodes.append(node)
        env.put(nodes[0], nodes[1])
        env.put(holder + 0xC, nodes[0])
    # B and friends
    b_obj = 0
    if o.get("has_b", True):
        b_obj = env.object(0x30, "B", fill=0)
        b4 = env.object(0x20, "B4", fill=0)
        b4_14 = env.object(0x40, "B4-14", fill=0)
        if o.get("engine", False):
            env.put(b4_14 + 0x2C, make_surface(env, "b4"))
            env.put(b_obj + 0x1C, make_engine(env, "main"))
        else:
            env.put(b4_14 + 0x2C, 0xCAFE)
        env.put(b4 + 0x14, b4_14)
        b4_c = env.object(0x40, "B4-c", fill=0)
        env.put(b4_c + 0x34, o.get("b4_flag", 0))
        env.put(b4 + 0xC, b4_c)
        env.put(b_obj + 4, b4)
        env.put(b_obj + 8, env.object(0x40, "B8", fill=0))
        bx = env.object(0x40, "BX", fill=0)
        by = env.object(0x84, "BY", fill=0)
        if o.get("by_live", False):
            env.put(by + 0x78, 1)
            wnode = env.object(0x40, "BY-voice", fill=0)
            w_driver = env.object(0x84, "BY-voice-driver", fill=0)
            w_iface = env.object(0x20, "BY-voice-iface", fill=0)
            w_vt = env.object(0x60, "BY-voice-vt", fill=0)
            env.put(w_driver + 0x78, 1)
            env.put(wnode + 0xC, w_iface)
            env.put(wnode + 0x10, w_driver)
            env.put(w_iface, w_vt)
            env.put(w_vt + 0x48, env.stub("BY-voice-stop", "stdcall", 1, returns(0)))
            env.put(by + 4, wnode + 4)
        env.put(bx + 0x2C, by if o.get("has_y", True) else 0)
        env.put(b_obj + 0x28, bx)
    # app
    vt = env.object(0x20, "app-vtable", fill=0)
    env.put(vt + 0xC, env.stub("app-slot-c", "thiscall", 0, returns(o.get("app_slot", 0))))
    env.put(app, vt)
    env.put(app + 4, hwnd_obj)
    env.put(app + 0x0C, o.get("a_0c", 0))
    env.put(app + 0x10, o.get("a_audio", 1))
    env.put(app + 0x14, o.get("a_music", 1))
    env.put(app + 0x30, dev)
    env.put(app + 0x50, music)
    env.put(app + 0x5C, holder)
    env.put(app + 0x68, o.get("a_68", 5))
    env.put(app + 0x7C, o.get("a_7c", 640))
    env.put(app + 0x80, o.get("a_80", 480))
    env.put(app + 0x9C, o.get("a_9c", 0))
    env.put(app + 0x118, o.get("a_voice", 1))
    env.put(app + 0x11C, o.get("a_ambient", 1))
    env.put(app + 0x120, o.get("a_movies", 1))
    env.put(app + 0x128, o.get("a_front", 1))
    if o.get("dev24") is not None:
        count, flag_values = o["dev24"]
        d24 = env.object(0x50, "dev24", fill=0)
        flag_array = env.object(max(4, len(flag_values) * 4), "dev24-array", fill=0)
        for index, value in enumerate(flag_values):
            flag_object = env.object(0x20, f"dev24-flags{index}", fill=0)
            env.put(flag_object + 8, value)
            env.put(flag_array + index * 4, flag_object)
        env.put(d24 + 0x3C, count)
        env.put(d24 + 0x38, flag_array)
        env.put(dev + 0x24, d24)
    if o.get("slot_writes") is not None:
        env.put(vt + 0xC, env.stub("app-slot-c-writes", "thiscall", 0,
                                   lambda env, call: (env.put(call.receiver + 0x128, o["slot_writes"]), o.get("app_slot", 0))[1]))
    # menu
    env.put(menu + 4, app)
    env.put(menu + 0xC, b_obj)
    env.put(menu + 0x290, o.get("flags_audio", 0))
    env.put(menu + 0x294, o.get("flags_display", 0))
    env.put(menu + 0x298, 0x5555)
    env.put(menu + 0x2A8, o.get("m_2a8", 0))
    if o.get("engine", False):
        q = env.object(0x20, "Q", fill=0)
        q1 = env.object(0x90, "Q1", fill=0)
        r4 = env.object(0x40, "R4", fill=0)
        env.put(r4 + 0x2C, make_surface(env, "r5"))
        b4 = env.get(b_obj + 4)
        env.put(b4 + 0x10, r4)
        env.put(q + 4, q1)
        env.put(q + 0xC, b_obj)
        env.put(menu + 0x274, q)
    make_controls(env, menu, o.get("ctl_ids", ()), seed)
    if o.get("one_id") is not None:
        env.put(menu + 0x1EC, o["one_id"])
        frames = env.object(8 * 4, "root-slots", fill=0)
        for slot in range(8):
            frame = env.object(0x30, f"root-slot{slot}", fill=0)
            env.put(frame + 0x14, 11 + slot * 7)
            env.put(frame + 0x18, 12 + slot * 5)
            env.put(frames + slot * 4, frame)
        env.put(menu + 0x1DC, frames, 8)
        env.put(menu + 0x21C, o.get("one_flags", 0x0D))
    # globals
    env.put(G_MENU, menu)
    env.put(G_MASTER, o.get("master", 1))
    env.put(G_VOLUME, o.get("volume", 37))
    t.update(menu=menu, app=app, holder=holder, hwnd_obj=hwnd_obj, dev=dev, eng=eng, b=b_obj, music=music)
    if o.get("swap_app", False) or hook:
        app2 = env.object(0x140, "app2", fill=0)
        env.write(app2, env.read(app, 0x140))
        hold2 = env.object(0x10, "hwnd-holder2", fill=0)
        env.put(hold2 + 4, 0x7777EEEE)
        env.put(app2 + 4, hold2)
        env.put(app2 + 0x9C, 0 if o.get("a_9c", 0) else 1)
        holder2 = env.object(0x30, "G2", fill=0)
        env.write(holder2, env.read(holder, 0x30))
        env.put(holder2 + 0x24, 0 if o.get("g_active", 0) else 1)
        env.put(app2 + 0x5C, holder2)
        env.put(app2 + 0x118, 0 if o.get("a_voice", 1) else 1)
        env.put(app2 + 0x11C, 0 if o.get("a_ambient", 1) else 1)
        env.put(app2 + 0x120, 7)
        env.put(app2 + 0x10, 6)
        ctx.update(menu=menu, app=app, app2=app2, holder=holder, holder2=holder2)

        if o.get("swap_app", False):
            def swap(env, call):
                if env.calls_so_far(call.function) == 1:
                    env.put(menu + 4, app2)
                return 1
            env.override(POST, swap)
    ctx.update(menu=menu, app=app, holder=holder)
    return t


def world(**options):
    def setup(env):
        return make_world(env, **options)
    return setup


def call(label, function, setup, *arguments, **kw):
    return Case(label, function, setup, receiver=lambda t: t["menu"], arguments=arguments, **kw)


def on_app(label, function, setup, **kw):
    return Case(label, function, setup, receiver=lambda t: t["app"], **kw)


def on_holder(label, function, setup, **kw):
    return Case(label, function, setup, receiver=lambda t: t["holder"], **kw)


SOUND_STATES = (
    ("sound on", {}),
    ("muted", {"mute": 0x100}),
    ("master off", {"master": 0}),
    ("no select", {"has_select": False, "has_disable": False}),
)

ALL_UI = (0x5AA1, 0x5AA2, 0x5AA3, 0x5AA4, 0x5B05, 0x5B07)


def cases(random_source):
    rnd = random_source
    def gen():
        # ---- shim 0x4505f0 -------------------------------------------------
        for command, flag in ((0x59D9, 1), (0x5AA1, 7), (0x5B06, 1), (0x55F1, 0xFFFFFFFF), (0x59DC, 0), (0x4E21, 3)):
            yield Case(f"shim {command:#x}/{flag}", SHIM, world(hwnd=rnd.randrange(1, 1 << 30), seed=rnd.randrange(1, 9)),
                       arguments=(command, flag))

        # ---- dispatcher 0x450b50, disable path ---------------------------
        for name, state in SOUND_STATES:
            for flag_cmd in (0, 0x5AA1):
                yield call(f"dispatch disable {name} cmd {flag_cmd:#x}", DISPATCH, world(**state, volume=rnd.randrange(1, 60)),
                           flag_cmd, 0)
        yield call("dispatch disable no GAME_DISABLE but select", DISPATCH, world(has_disable=False), 1, 0)
        yield call("dispatch disable dead driver", DISPATCH, world(live_disable=False), 1, 0)
        yield call("dispatch disable no decoys single bucket", DISPATCH, world(decoys=False, buckets=1), 1, 0)

        # ---- dispatcher ranges --------------------------------------------
        ranges = ((0x4E21, 0x4E25), (0x55F1, 0x55F2), (0x59D9, 0x59DC), (0x5AA1, 0x5AA5), (0x5B05, 0x5B08), (0x5DC1, 0x5DC2))
        for low, high in ranges:
            for command in (low - 1, low, high, high + 1):
                if command in (0x4E24, 0x4E25):
                    continue
                for flag in (1, 0x80000000):
                    yield call(f"dispatch range {command:#x} flag {flag:#x}", DISPATCH,
                               world(ui=True, ctl_ids=ALL_UI, engine=True, seed=rnd.randrange(1, 9)), command, flag)
        for command in (0, 1, 0x4E20, 0x7FFFFFFF, 0xFFFFFFFF, 0x4E26, 0x55F0, 0x55F3, 0x59D8, 0x59DD, 0x5AA0, 0x5AA6, 0x5B04, 0x5B09, 0x5DC0, 0x5DC3):
            yield call(f"dispatch outside {command:#x}", DISPATCH, world(), command, 1)
        for command in (0x4E21, 0x4E22, 0x4E23):
            for name, state in SOUND_STATES:
                yield call(f"dispatch {command:#x} {name}", DISPATCH, world(**state, hwnd=rnd.randrange(1, 1 << 30)), command, 1)

        # ---- 0x450e00 ------------------------------------------------------
        yield call("59d9 post", H_59D9, world(hwnd=rnd.randrange(1, 1 << 30)), 0x59D9)
        yield call("59d9 post swap", H_59D9, world(), 0x59D9)
        for command in (0x59DA, 0x59DB, 0x59DC):
            for name, state in SOUND_STATES:
                yield call(f"{command:#x} {name}", H_59D9, world(**state, volume=rnd.randrange(1, 60), a_68=rnd.randrange(1, 11)), command)
        for command in (0x59D8, 0x59DD, 0, 0xFFFFFFFF):
            yield call(f"59d9 handler outside {command:#x}", H_59D9, world(), command)
        yield call("59db with page controls", H_59D9, world(ui=True, ctl_ids=ALL_UI), 0x59DB)
        yield call("59da with page controls", H_59D9, world(ui=True, ctl_ids=ALL_UI, a_68=0), 0x59DA)
        yield call("59da with large a68", H_59D9, world(a_68=11), 0x59DA)
        yield call("59dc a9c set", H_59D9, world(a_9c=4), 0x59DC)

        # ---- 0x451660 and 0x451210 --------------------------------------------
        for command in (0x2710, 0x4E23):
            for a9c in (0, 1, 3):
                yield call(f"clear selection {command:#x} a9c {a9c}", CLEAR_SELECT, world(a_9c=a9c), command)
        for active in (0, 1, 0x40):
            for items in (False, True):
                yield on_holder(f"disarm active {active} items {items}", DISARM, world(g_active=active, g_items=items))

        # ---- 0x42cdf0 --------------------------------------------------------
        for front in (0, 1, 2):
            for slot in (0, 1):
                yield on_app(f"toggle front {front} slot {slot}", TOGGLE_FRONT, world(a_front=front, app_slot=slot))

        # ---- 0x451410 --------------------------------------------------------
        for command in (0x55F1, 0x55F2):
            for name, state in SOUND_STATES:
                yield call(f"{command:#x} {name}", H_55F1, world(**state, hwnd=rnd.randrange(1, 1 << 30), volume=rnd.randrange(1, 60)), command)
        yield call("55f1 app swapped between posts", H_55F1, world(swap_app=True), 0x55F1)
        for command in (0x55F0, 0x55F3, 0):
            yield call(f"55f1 outside {command:#x}", H_55F1, world(), command)

        # ---- 0x451530 --------------------------------------------------------
        for command in (0x5DC1, 0x5DC2):
            for name, state in SOUND_STATES:
                yield call(f"{command:#x} {name}", H_5DC1, world(**state, hwnd=rnd.randrange(1, 1 << 30), volume=rnd.randrange(1, 60)), command)
        for a9c in (0, 1, 0x80):
            yield call(f"5dc1 a9c {a9c}", H_5DC1, world(a_9c=a9c), 0x5DC1)
        yield call("5dc1 app swapped a9c 0", H_5DC1, world(swap_app=True, a_9c=0), 0x5DC1)
        yield call("5dc1 app swapped a9c 1", H_5DC1, world(swap_app=True, a_9c=2), 0x5DC1)
        for command in (0x5DC0, 0x5DC3, 0):
            yield call(f"5dc1 outside {command:#x}", H_5DC1, world(), command)

        # ---- 0x450ed0 ----------------------------------------------------
        for has_b in (False, True):
            for has_y in (False, True):
                if not has_b and not has_y:
                    continue
                for a_audio in (0, 1, 6):
                    for by_live in (False, True):
                        yield call(f"5aa1 b={has_b} y={has_y} audio={a_audio} live={by_live}", H_AUDIO,
                                   world(has_b=has_b, has_y=has_y, a_audio=a_audio, by_live=by_live, g_items=by_live,
                                         flags_audio=rnd.randrange(0, 1 << 16) & ~0xF, master=(a_audio + int(by_live) + int(has_b)) % 3,
                                         volume=rnd.randrange(1, 60), ui=True, ctl_ids=ALL_UI if a_audio else (),
                                         seed=rnd.randrange(1, 9)), 0x5AA1)
        for name, state in SOUND_STATES:
            yield call(f"5aa1 {name}", H_AUDIO, world(**state, a_audio=0, ui=True, one_id=0x5AA2), 0x5AA1)
            yield call(f"5aa1 {name} on", H_AUDIO, world(**state, a_audio=0, ui=True, one_id=0x5AA3, g_active=1), 0x5AA1)
        yield call("5aa1 with only first node 5aa2", H_AUDIO, world(a_audio=0, ui=True, one_id=0x5AA2, one_flags=0x2A), 0x5AA1)
        yield call("5aa1 with only first node 5aa3", H_AUDIO, world(a_audio=0, ui=True, one_id=0x5AA3, one_flags=0x15), 0x5AA1)

        for a_voice in (0, 1, 3):
            for playing in (False, True):
                for has in (False, True):
                    for master in (0, 1):
                        yield call(f"5aa2 voice={a_voice} playing={playing} has={has} master={master}", H_AUDIO,
                                   world(a_voice=a_voice, playing=playing, has_p1055=has, master=master,
                                         flags_audio=rnd.randrange(0, 1 << 16) & ~0xF, ui=True, ctl_ids=ALL_UI, seed=rnd.randrange(1, 9)), 0x5AA2)
        for name, state in SOUND_STATES[1:]:
            yield call(f"5aa2 {name}", H_AUDIO, world(**state, a_voice=0, playing=True), 0x5AA2)
        yield call("5aa2 dead driver playing", H_AUDIO, world(live_p1055=False, playing=True, a_voice=0), 0x5AA2)
        yield call("5aa2 dead driver on", H_AUDIO, world(live_p1055=False, a_voice=0), 0x5AA2)

        for ambient in (0, 1, 2):
            for active in (0, 1):
                for items in (False, True):
                    yield call(f"5aa3 ambient={ambient} active={active} items={items}", H_AUDIO,
                               world(a_ambient=ambient, g_active=active, g_items=items, flags_audio=rnd.randrange(0, 1 << 16) & ~0xF,
                                     ui=True, ctl_ids=ALL_UI, seed=rnd.randrange(1, 9)), 0x5AA3)
        for name, state in SOUND_STATES[1:]:
            yield call(f"5aa3 {name}", H_AUDIO, world(**state, a_ambient=0), 0x5AA3)

        for a_0c in (0, 1, 3):
            for music in (0, 1, 2):
                for live_music in (False, True):
                    yield call(f"5aa4 a0c={a_0c} music={music} live={live_music}", H_AUDIO,
                               world(a_0c=a_0c, a_music=music, music_live=live_music, flags_audio=rnd.randrange(0, 1 << 16) & ~0xF,
                                     ui=True, ctl_ids=ALL_UI, seed=rnd.randrange(1, 9)), 0x5AA4)
        for name, state in SOUND_STATES[1:]:
            yield call(f"5aa4 {name}", H_AUDIO, world(**state, a_music=1), 0x5AA4)

        for name, state in SOUND_STATES:
            yield call(f"5aa5 {name}", H_AUDIO, world(**state, volume=rnd.randrange(1, 60), flags_audio=0x55), 0x5AA5)
        for command in (0x5AA0, 0x5AA6, 0, 0xFFFFFFFF):
            yield call(f"5aa1 handler outside {command:#x}", H_AUDIO, world(), command)

        # ---- 0x451230 ----------------------------------------------------
        for command in (0x5B05, 0x5B06, 0x5B07, 0x5B08):
            for name, state in SOUND_STATES:
                yield call(f"{command:#x} {name}", H_DISPLAY,
                           world(**state, a_movies=(command + len(name)) % 2, a_front=(command // 2 + len(name)) % 2, volume=rnd.randrange(1, 60),
                                 flags_display=rnd.randrange(0, 1 << 12) & ~3, ui=True, engine=True, ctl_ids=ALL_UI, seed=rnd.randrange(1, 9)), command)
        for command in (0x5B04, 0x5B09, 0, 0xFFFFFFFF):
            yield call(f"display outside {command:#x}", H_DISPLAY, world(), command)
        yield Case("display null app 5b05", H_DISPLAY, world_without_app, receiver=lambda t: t["menu"], arguments=(0x5B05,))
        yield Case("display null app outside", H_DISPLAY, world_without_app, receiver=lambda t: t["menu"], arguments=(0,))

        # ---- apply functions ------------------------------------------------
        for flags in (0, 1, 2, 4, 8, 3, 5, 9, 6, 10, 12, 15, 0x10, 0xF0, 0x1F, 0xFFFFFFF0, 0xFFFFFFFF):
            yield call(f"apply audio flags {flags:#x}", APPLY_AUDIO,
                       world(ui=True, ctl_ids=ALL_UI, flags_audio=flags, a_audio=flags & 1, a_music=(flags >> 1) & 1,
                             a_voice=(flags >> 2) & 1, a_ambient=(flags >> 3) & 1, seed=rnd.randrange(1, 9)))
        for flags in (0, 1, 2, 4, 8, 3, 0x10, 0xFFFFFFFC, 0xFFFFFFFF):
            yield call(f"apply audio flags {flags:#x} no controls", APPLY_AUDIO, world(ui=True, flags_audio=flags))
        for flags in (0, 1, 2, 3, 4, 0x10, 0xFFFFFFFC, 0xFFFFFFFF):
            yield call(f"apply display flags {flags:#x}", APPLY_DISPLAY,
                       world(ui=True, ctl_ids=ALL_UI, flags_display=flags, a_front=flags & 1, a_movies=(flags >> 1) & 1,
                             seed=rnd.randrange(1, 9)))
        for flags in (0, 1, 2, 3, 0x10, 0xFFFFFFFF):
            yield call(f"apply display flags {flags:#x} no controls", APPLY_DISPLAY, world(ui=True, flags_display=flags))

        # ---- state changed behind the function's back ------------------------
        vol = lambda: rnd.randrange(1, 60)
        swap_menu = (("menu", 4, "app2"),)
        for hook_name, hook in (("app swap", swap_menu), ("voice flip", (("app", 0x118, 0),)),
                                ("voice on", (("app", 0x118, 5),)), ("holder swap", (("app", 0x5C, "holder2"),)),
                                ("ambient flip", (("app", 0x11C, 0),)), ("movies set", (("app", 0x120, 0),)),
                                ("a0c set", (("app", 0xC, 1),)), ("audio set", (("app", 0x10, 0),)),
                                ("music set", (("app", 0x14, 0),))):
            yield call(f"5aa1 hook {hook_name}", H_AUDIO, world(hook=hook, a_audio=1, volume=vol(), g_items=True), 0x5AA1)
            yield call(f"5aa2 hook {hook_name}", H_AUDIO, world(hook=hook, a_voice=1, volume=vol(), playing=True), 0x5AA2)
            yield call(f"5aa2 hook {hook_name} off", H_AUDIO, world(hook=hook, a_voice=0, volume=vol()), 0x5AA2)
            yield call(f"5aa3 hook {hook_name}", H_AUDIO, world(hook=hook, a_ambient=0, volume=vol(), g_items=True), 0x5AA3)
            yield call(f"5aa3 hook {hook_name} on", H_AUDIO, world(hook=hook, a_ambient=1, volume=vol(), g_items=True), 0x5AA3)
            yield call(f"5aa4 hook {hook_name}", H_AUDIO, world(hook=hook, a_music=1, volume=vol()), 0x5AA4)
            yield call(f"5aa4 hook {hook_name} off", H_AUDIO, world(hook=hook, a_music=0, volume=vol()), 0x5AA4)
        for hook_name, hook in (("app swap", swap_menu), ("movies set", (("app", 0x120, 0),)), ("front set", (("app", 0x128, 0),))):
            for command in (0x5B05, 0x5B07):
                yield call(f"{command:#x} hook {hook_name}", H_DISPLAY, world(hook=hook, engine=True, volume=vol(), ui=True, ctl_ids=ALL_UI),
                           command)

        # ---- 0x42cdf0 with the display object ------------------------------
        for count, flags in ((4, (1, 2, 0, 3)), (3, (0, 0, 0)), (3, (1, 1, 1)), (1, (0,)), (0, ()), (2, (2, 2)), (5, (0, 0, 0, 0, 0))):
            for front in (0, 1):
                yield on_app(f"toggle front dev24 count {count} flags {flags} front {front}", TOGGLE_FRONT,
                             world(a_front=front, app_slot=1, dev24=(count, flags)))
        yield on_app("toggle front slot rewrites flag", TOGGLE_FRONT, world(a_front=1, app_slot=0, slot_writes=0x77))
        yield on_app("toggle front slot rewrites flag live", TOGGLE_FRONT, world(a_front=0, app_slot=1, slot_writes=0x78, dev24=(1, (0,))))
        for command in (0x5B05,):
            yield call("5b05 toggles front with slot", H_DISPLAY, world(engine=True, app_slot=1, dev24=(1, (0,)), a_front=0), command)

        # ---- more command boundaries ---------------------------------------------
        for low, high in ranges:
            for command in (low + 0x10000, high | 0x80000000, (low - 1) & 0xFFFF, low ^ 0x100):
                yield call(f"dispatch far {command:#x}", DISPATCH, world(), command, 1)
        for flag in (0x100, 0xFFFFFFFF, 2):
            yield call(f"dispatch flag {flag:#x} to range", DISPATCH, world(), 0x59DC, flag)
        for flag in (0x100,):
            yield call(f"dispatch flag {flag:#x} to disable", DISPATCH, world(), 0x59DC, flag)
        for command in (0x59D9, 0x5AA1, 0x5B05, 0x55F1, 0x5DC1, 0x4E21):
            yield call(f"dispatch random volume {command:#x}", DISPATCH,
                       world(ui=True, ctl_ids=ALL_UI, engine=True, volume=vol(), a_audio=rnd.randrange(0, 4), hwnd=rnd.randrange(1, 1 << 30)),
                       command, 1)
        for fn, base, size in ((H_59D9, 0x59D9, 4), (H_AUDIO, 0x5AA1, 5), (H_DISPLAY, 0x5B05, 4), (H_55F1, 0x55F1, 2), (H_5DC1, 0x5DC1, 2)):
            for command in (base + size, base | 0x80000000, base + size + 0x10000):
                yield call(f"handler {fn:#x} far outside {command:#x}", fn, world(), command)

    yield from gen()


def world_without_app(env):
    tokens = make_world(env)
    env.put(tokens["menu"] + 4, 0)
    return tokens
