"""Cases for pause_menu_input: Pause menu key, pointer and command handlers.

Every branch is reached by a fixed list of scenarios, not by the random source. The random source only
varies values (coordinates, positions, string contents, tick bases) inside scenarios.

Imports that the specification does not declare yet (GetTickCount, GetCursorPos, PtInRect, SetRect,
timeGetTime, InterlockedIncrement, InterlockedDecrement) are used only when the specification declares them,
so the file stays runnable before and after the coordinator adds them.
"""
import json
from pathlib import Path

from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns

KEY_HANDLER = 0x450460
POINTER_HANDLER = 0x450850
COMMAND_WITH_FLAGS = 0x450C50
COMMAND = 0x450CF0
ITEM_SCAN = 0x451E10
KEY_LOOKUP = 0x452050
SLIDER_STEP = 0x452080

POST_MESSAGE = 0x546D50
GET_TICK = 0x546A24
GET_CURSOR = 0x546CD0
PT_IN_RECT = 0x546CD4
SET_RECT = 0x546D5C
TIME_GET = 0x546DF0
INTERLOCKED_DECREMENT = 0x5469E8
INTERLOCKED_INCREMENT = 0x5469EC

UI_GLOBAL = 0x5371FC
SOUND_ENABLED = 0x532C0C
SOUND_ARGUMENT = 0x532C10
LOCALE_FLAG = 0x540E00
MIDI_HANDLE = 0x54131C

SELECT_CODE = 0x4E21
BACK_CODE = 0x4E24


def _declared():
    try:
        spec = json.loads(Path(__file__).with_name("pause_menu_input.json").read_text())
        return {int(address, 16) for address in spec.get("callees", {})}
    except Exception:
        return set()


DECLARED = _declared()


def has(*addresses):
    return all(address in DECLARED for address in addresses)


CSTRING_IMPORTS = has(INTERLOCKED_DECREMENT, INTERLOCKED_INCREMENT)
TICK_IMPORT = has(GET_TICK)
CURSOR_IMPORTS = has(GET_TICK, GET_CURSOR, PT_IN_RECT)
SET_RECT_IMPORT = has(SET_RECT)
TIME_IMPORT = has(TIME_GET)


def signed(value):
    value &= 0xFFFFFFFF
    return value - (1 << 32) if value & 0x80000000 else value


# ---- fixture effects -----------------------------------------------------------------------------

def interlocked(delta):
    def effect(env, call):
        pointer = call.arguments[0]
        value = (env.get(pointer) + delta) & 0xFFFFFFFF
        env.put(pointer, value)
        return value
    return effect


def tick_clock(base, step):
    return lambda env, call: (base + step * (env.calls_so_far(call.function) - 1)) & 0xFFFFFFFF


def tick_list(values):
    return lambda env, call: values[min(env.calls_so_far(call.function), len(values)) - 1] & 0xFFFFFFFF


def cursor_at(x, y):
    def effect(env, call):
        env.put(call.arguments[0], x, y)
        return 1
    return effect


def point_in_rect(env, call):
    rect = [signed(env.get(call.arguments[0] + 4 * index)) for index in range(4)]
    x, y = signed(call.arguments[1]), signed(call.arguments[2])
    return int(rect[0] <= x < rect[2] and rect[1] <= y < rect[3])


def set_rect(env, call):
    env.put(call.arguments[0], *call.arguments[1:5])
    return 1


# ---- object builders -----------------------------------------------------------------------------

def hash_of(text):
    value = 0
    for byte in text:
        value = (value * 0x21 + (byte - 256 if byte >= 128 else byte)) & 0xFFFFFFFF
    return value


def cstring(env, text, references=1):
    """An MFC string: a three word header, then the characters."""
    block = env.object(0x10 + len(text) + 1, "cstring", fill=0)
    env.put(block, references, len(text), len(text))
    env.write(block + 0xC, text + b"\0")
    return block + 0xC


def make_map(env, base, entries, buckets, table=True):
    """The string-to-value hash map the original reads: table at +4, bucket count at +8."""
    env.put(base + 8, buckets)
    if not table:
        return
    slots = env.object(4 * buckets, "buckets", fill=0)
    for key, value in entries:
        key_block = env.object(len(key) + 1, "map-key", data=key + b"\0")
        slot = hash_of(key) % buckets
        node = env.object(16, "assoc", words=[env.get(slots + 4 * slot), hash_of(key), key_block, value])
        env.put(slots + 4 * slot, node)
    env.put(base + 4, slots)


def sound_value(env, tag, enabled=True, nodes=1):
    """A map value whose +0x10 is a sound manager with free buffers, every COM call stubbed."""
    methods = env.object(0x50, "buffer-methods", fill=0)
    env.put(methods + 0x24, env.stub(f"GetStatus{tag}", "stdcall", 2, returns(0)))
    env.put(methods + 0x30, env.stub(f"Play{tag}", "stdcall", 4, returns(0)))
    env.put(methods + 0x3C, env.stub(f"SetFrequency{tag}", "stdcall", 2, returns(0)))
    env.put(methods + 0x40, env.stub(f"SetPan{tag}", "stdcall", 2, returns(0)))
    env.put(methods + 0x44, env.stub(f"SetVolume{tag}", "stdcall", 2, returns(0)))
    device = env.object(0x80, "sound-device", fill=0)
    env.put(device + 0x78, 1 if enabled else 0)
    manager = env.object(0x40, "sound-manager", fill=0)
    blocks = []
    for index in range(nodes):
        buffer = env.object(4, "buffer", words=[methods])
        node = env.object(0x38, "sound-node", fill=0)
        env.put(node + 0x0C, buffer)
        env.put(node + 0x10, device)
        env.put(node + 0x14, 0x80 + tag + index)
        env.put(node + 0x18, 22050 + 100 * tag + index)
        env.put(node + 0x30, 1 + index)
        blocks.append(node)
    for index, node in enumerate(blocks):
        env.put(node + 4, blocks[index + 1] + 4 if index + 1 < len(blocks) else 0,
                blocks[index - 1] + 4 if index else 0)
    env.put(manager + 0x10, device)
    env.put(manager + 0x18, 0x1100 + tag, 0x2200 + tag, 0x3300 + tag)
    env.put(manager + 0x30, blocks[0] + 4, blocks[-1] + 4)
    value = env.object(0x20, "sound-value", fill=0)
    env.put(value + 0x10, manager)
    return value


def sound_context(env, spec, tag):
    """The object whose +0x30 flag gates the sound and whose map at +0x10 holds GAME_CLICK / GAME_SELECT."""
    spec = spec or {}
    context = env.object(0x40, "sound-context", fill=0)
    entries = [(b"GAME_DECOY", 0x7001 + tag), (b"GAME_CLICK_", 0x7002 + tag), (b"GAME_SELEC", 0x7003 + tag)]
    for name, key in (("click", b"GAME_CLICK"), ("select", b"GAME_SELECT")):
        state = spec.get(name, "on")
        if state == "absent":
            continue
        if state == "null":
            entries.append((key, 0))
        else:
            entries.append((key, sound_value(env, tag * 4 + (0 if name == "click" else 1), enabled=(state == "on"),
                                             nodes=spec.get("nodes", 1))))
    make_map(env, context + 0x10, entries, spec.get("buckets", 5), table=spec.get("table", True))
    env.put(context + 0x30, spec.get("flag", 0))
    return context


def image(env, width, height):
    return env.object(0x20, "image", words=[0x11, 0x22, 0x33, 0x44, 0x55, height, width, 0x77])


def build(env, o):
    """One pause menu, its option list, item list, key map, sound contexts and the objects they point at."""
    tokens = {}
    menu = env.object(0x300, "menu", fill=0)
    S = menu + 0x154
    if o.get("uniform"):
        images = [image(env, 34, 14) for i in range(8)]
    else:
        images = [image(env, 30 + 7 * i, 12 + 3 * i) for i in range(8)]
    theme = env.object(0x20, "theme", words=images)
    tokens.update(M=menu, S=S, theme=theme, images=images)

    # option list: S + 0 vtable, +0xc array, +0x10 count, +0x1c current, +0x20 pointer lock, +0x24 key lock
    count = o.get("count", 3)
    controls = []
    types = o.get("types", [0] * count)
    cflags = o.get("cflags", [0] * count)
    geometry = o.get("geometry", [(10 + 40 * i, 20 + 30 * i, 60 + 8 * i, 40 + 6 * i) for i in range(count)])
    for index in range(count):
        block = o["controls"][index] if o.get("controls") and o["controls"][index] else None
        if block is None:
            block = env.object(0xB0, "control", fill=0)
        x, y, w, h = geometry[index]
        env.put(block + 0x04, theme)
        env.put(block + 0x14, types[index])
        env.put(block + 0x40, images[index % 8])
        env.put(block + 0x44, cflags[index])
        env.put(block + 0x54, x, y, w, h)
        env.put(block + 0x68, o.get("control_delay", 40) + index)
        controls.append(block)
    tokens["controls"] = controls
    array = env.object(4 * max(count, 1) + 4, "control-array", fill=0)
    for index, block in enumerate(controls):
        env.put(array + 4 * index, block)
    methods = env.object(0x20, "list-methods", fill=0)
    move_up, move_down = o.get("up"), o.get("down")
    names = {}
    for slot, name, effect in ((0, "Up", move_up), (4, "Down", move_down), (0x10, "Activated", o.get("activated")),
                               (0x14, "Pressed", o.get("pressed")), (0x18, "Released", None)):
        names[name] = env.stub(f"List{name}", "thiscall", 0, effect or returns(0))
        env.put(methods + slot, names[name])
    env.put(S, methods)
    env.put(S + 0x0C, array)
    env.put(S + 0x10, o.get("count_field", count))
    env.put(S + 0x1C, o.get("cur", 1))
    env.put(S + 0x20, o.get("hover_lock", 0))
    env.put(S + 0x24, o.get("key_lock", 0))
    env.put(S + 0x28, o.get("saved", 2))
    env.put(S + 0x2C, o.get("press_tick", 1000))
    env.put(S + 0x30, o.get("last_tick", 900))
    env.put(S + 0x34, o.get("hold", 50))

    # item list reached through S + 0xf8
    items = []
    if o.get("items") is not None:
        item_specs = o["items"]
        for spec in item_specs:
            if spec is None:
                items.append(0)
                continue
            text, flags, references = spec
            block = env.object(0xB0, "list-item", fill=0)
            env.put(block + 0x14, cstring(env, text, references))
            env.put(block + 0x40, theme)
            env.put(block + 0x7C, images[3])
            env.put(block + 0x80, flags)
            items.append(block)
        item_array = env.object(4 * len(items) + 4, "item-array", fill=0)
        for index, block in enumerate(items):
            env.put(item_array + 4 * index, block)
        list_object = env.object(0x40, "item-list", fill=0)
        env.put(list_object + 0x1C, item_array)
        env.put(list_object + 0x20, o.get("item_count", len(items)))
        env.put(S + 0xF8, list_object)
        tokens["list_object"] = list_object
    tokens["items"] = items
    if o.get("link_items"):
        # make a pointer-list entry point at the embedded control of the item, so the scan can select it
        for position, item_index in o["link_items"].items():
            env.put(array + 4 * position, items[item_index] + 0x3C)
            tokens["controls"][position] = items[item_index] + 0x3C

    # slider panels
    tokens["panels"] = []
    for offset in (0x254, 0x258, 0x25C, 0x264, 0x268, 0x26C):
        if o.get("panels", True):
            panel = env.object(0x60, "panel", fill=0)
            env.put(panel + 0x4C, 0xAAAA0000 + offset, 0xBBBB0000 + offset)
            env.put(menu + offset, panel)
            tokens["panels"].append(panel)
    env.put(menu + 0x274, 0)
    env.put(menu + 0x2A8, o.get("flag_2a8", 0))
    env.put(menu + 0x298, o.get("last_command", 0x1357))

    # application objects: window handle, sound contexts, settings
    window = env.object(0x10, "window", words=[0, o.get("hwnd", 0x00130042), 0, 0])
    holder = env.object(0x100, "application", fill=0)
    env.put(holder + 0x04, window)
    env.put(holder + 0x10, o.get("opt10", 0), o.get("opt14", 0))
    env.put(holder + 0x50, o.get("opt50", 0))
    env.put(holder + 0x68, o.get("level", 5))
    env.put(holder + 0x7C, 640, 480)
    env.put(holder + 0x9C, o.get("opt9c", 0))
    menu_context = sound_context(env, o.get("menu_sound"), 1)
    holder_path = env.object(0x40, "path-a", fill=0)
    holder_inner = env.object(0x40, "path-b", fill=0)
    env.put(holder_path + 0x28, menu_context)
    env.put(holder_inner + 0x28, menu_context)
    env.put(holder + 0x30, holder_path)
    env.put(menu + 0x04, holder)
    family = env.object(0x40, "family", fill=0)
    inner = env.object(0x40, "inner", fill=0)
    inner2 = env.object(0x40, "inner2", fill=0)
    env.put(inner + 0x14, inner2)
    env.put(inner2 + 0x2C, 0x4040)
    env.put(family + 0x04, inner)
    env.put(family + 0x08, 0x5050)
    family_context = sound_context(env, o.get("family_sound"), 2)
    env.put(family + 0x28, family_context)
    env.put(menu + 0x0C, family)
    # the key handler reaches its sound context through a global
    ui_context = sound_context(env, o.get("ui_sound"), 3)
    ui_inner = env.object(0x40, "ui-inner", fill=0)
    env.put(ui_inner + 0x28, ui_context)
    ui = env.object(0x40, "ui", fill=0)
    env.put(ui + 0x30, ui_inner)
    env.put(UI_GLOBAL, ui)
    env.put(SOUND_ENABLED, o.get("sound", 1))
    env.put(SOUND_ARGUMENT, o.get("volume", 3))
    env.put(LOCALE_FLAG, o.get("locale", 0))
    env.put(MIDI_HANDLE, 0)
    tokens.update(menu_context=menu_context, ui_context=ui_context, family_context=family_context,
                  holder=holder, family=family, window=window)

    # key to command map at M + 0x2b4
    entries = list(o.get("keymap", []))
    make_map(env, menu + 0x2B4, entries, o.get("buckets", 7), table=o.get("table", True))

    # slider hierarchy for 0x452080's neighbours: S + 0x48 holds children matched by id at +0x50
    children = o.get("children")
    if children:
        child_blocks = []
        for ident in children:
            block = env.object(0xB0, "child", fill=0)
            env.put(block + 0x50, ident)
            env.put(block + 0x40, theme)
            env.put(block + 0x7C, images[2])
            env.put(block + 0x90, 100, 50, 80, 20)
            child_blocks.append(block)
        child_array = env.object(4 * len(child_blocks) + 4, "child-array", fill=0)
        for index, block in enumerate(child_blocks):
            env.put(child_array + 4 * index, block)
        env.put(S + 0x64, child_array)
        env.put(S + 0x68, len(child_blocks))
        env.put(S + 0x98, 0x7E7E)
        tokens["children"] = child_blocks

    # fixtures
    env.override(POST_MESSAGE, returns(o.get("post_result", 1)))
    if TICK_IMPORT:
        env.override(GET_TICK, o.get("tick") or tick_clock(o.get("tick_base", 1100), o.get("tick_step", 30)))
    if has(GET_CURSOR):
        env.override(GET_CURSOR, cursor_at(*o.get("cursor", (0, 0))))
    if has(PT_IN_RECT):
        env.override(PT_IN_RECT, o.get("hit") or point_in_rect)
    if CSTRING_IMPORTS:
        env.override(INTERLOCKED_DECREMENT, interlocked(-1))
        env.override(INTERLOCKED_INCREMENT, interlocked(1))
    if SET_RECT_IMPORT:
        env.override(SET_RECT, set_rect)
    if TIME_IMPORT:
        env.override(TIME_GET, tick_clock(o.get("time_base", 5000), o.get("time_step", 170)))
    return tokens


def world(**options):
    def setup(env):
        return build(env, options)
    return setup


def menu_of(tokens):
    return tokens["M"]


def case(label, function, arguments=(), **options):
    return Case(label, function, world(**options), receiver=menu_of, arguments=arguments)


def mover(target):
    def effect(env, call):
        env.put(call.receiver + 0x1C, target)
        return 0
    return effect


# ---- the cases -----------------------------------------------------------------------------------

DEFAULT_KEYS = (0x0E, 0x10, 0x11, 0x1A, 0x1C, 0x24, 0x29, 0x41, 0x5A, 0xFF, 0x100, 0x80000000, 0xFFFFFFFF, 0, 1, 0x0C)
ALL_SWITCH_KEYS = tuple(range(0x0D, 0x29))


def cases(random_source):
    r = random_source
    yield from lookup_cases(r)
    yield from slider_cases(r)
    yield from command_cases(r)
    yield from scan_cases(r)
    yield from dispatch_cases(r)
    yield from key_handler_cases(r)
    yield from pointer_cases(r)


def pick_text(r, length=None):
    length = length or r.randrange(3, 12)
    return bytes(r.choice(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghij0123456789") for _ in range(length))


# 0x452050 ---------------------------------------------------------------------------------------
def lookup_cases(r):
    def lookup(label, key, entries, **options):
        def setup(env):
            tokens = build(env, dict(options, keymap=entries))
            tokens["key"] = env.object(len(key) + 1, "lookup-key", data=key + b"\0")
            return tokens
        return Case(label, KEY_LOOKUP, setup, receiver=menu_of, arguments=(lambda t: t["key"],))

    names = [b"RESUME", b"OPTIONS", b"SAVE", b"LOAD", b"QUIT", b"HELP", b"RETURN", b"VOLUME", b"MUSIC", b"BRIGHT"]
    values = [0x5A01, 0x5B02, 0x5C03, 0x5D04, 0x5E05, 0x5F06, 0x6007, 0x6108, 0x6209, 0x630A]
    table = list(zip(names, values))
    for buckets in (1, 2, 7, 17):
        for index in (0, 3, 9):
            yield lookup(f"hit {names[index].decode()} in {buckets} buckets", names[index], table, buckets=buckets)
    for buckets in (1, 7):
        yield lookup(f"miss in {buckets} buckets", b"UNKNOWN", table, buckets=buckets)
    yield lookup("miss on empty map", b"RESUME", [], buckets=7)
    yield lookup("miss with no table", b"RESUME", table, buckets=7, table=False)
    yield lookup("hit whose value is zero", b"ZERO", [(b"ZERO", 0), (b"OTHER", 9)], buckets=3)
    yield lookup("prefix is not a match", b"RESUM", table, buckets=1)
    yield lookup("longer key is not a match", b"RESUMED", table, buckets=1)
    yield lookup("empty key", b"", [(b"", 0x1234), (b"X", 5)], buckets=2)
    yield lookup("empty key miss", b"", table, buckets=2)
    # signed characters change the hash
    for key in (b"\x80ABC", b"AB\xff\xfeCD", b"\xe9\xe8\xe7"):
        yield lookup(f"high bytes {key!r} hit", key, table + [(key, 0x9999)], buckets=11)
        yield lookup(f"high bytes {key!r} miss", key, table, buckets=11)
    # long keys overflow 32 bits, then reduce as unsigned
    for length in (13, 31, 64):
        key = pick_text(r, length)
        yield lookup(f"long key {length} hit", key, table + [(key, 0xA0A0 + length)], buckets=13)
    for buckets in (3, 6007):
        key = pick_text(r, 40)
        yield lookup(f"large unsigned hash modulo {buckets}", key, table + [(key, 0x4242)], buckets=buckets)
    # multibyte locale: the compare goes through the locked locale branch
    for key in (b"RESUME", b"\x81\x40AB", b"MISSING"):
        yield lookup(f"locale on {key!r}", key, table + [(b"\x81\x40AB", 0x3131)], buckets=5, locale=1)
    for _ in range(12):
        picked = [(pick_text(r), r.randrange(1, 1 << 30)) for _ in range(r.randrange(1, 9))]
        key = r.choice(picked)[0] if r.random() < 0.6 else pick_text(r)
        yield lookup("random lookup", key, picked, buckets=r.randrange(1, 12))


# 0x452080 ---------------------------------------------------------------------------------------
def slider_cases(r):
    def slider(label, flag, types, cur, **options):
        return case(label, SLIDER_STEP, (flag,), count=len(types), types=types, cur=cur, **options)

    for flag in (0, 1, 2, 0xFFFFFFFF):
        for kind in (0, 0x5AA0, 0x5AA5, 0x5B04, 0x5B08, 0xFFFFFFFF):
            yield slider(f"flag {flag:#x} outside range type {kind:#x}", flag, [kind, 0x1111, 0x2222], 0)
    for flag in (0, 1, 2, 7):
        for kind in (0x5AA1, 0x5AA2, 0x5AA3, 0x5AA4, 0x5B05, 0x5B06, 0x5B07):
            yield slider(f"flag {flag} type {kind:#x} guard fails", flag, [0x99, kind, 0x98], 1, panels=False)
    for cur in (-1, 3, 4, 0x7FFFFFFF, 0xFFFFFFFF):
        yield slider(f"index {cur} outside the list", 1, [0x5AA1, 0x5AA4, 0x5B06], cur)
    yield case("empty list", SLIDER_STEP, (1,), count=0, cur=0)
    yield case("count field zero with array", SLIDER_STEP, (1,), count=3, count_field=0, types=[0x5AA1] * 3, cur=0)

    # volume slider (0x5aa1): moves the global volume in steps of 8, clamped to 0..0x50
    for flag in (0, 1, 2):
        for volume in (0, 4, 8, 40, 76, 79, 80, 120):
            yield slider(f"volume slider flag {flag} volume {volume}", flag, [0x5AA1, 0x5AA4, 0x5B06], 0,
                         volume=volume, children=[0x5AA1], opt10=r.randrange(1, 9))
    for volume in (4, 40):
        yield slider(f"volume slider needs the option", 1, [0x5AA1], 0, volume=volume, children=[0x5AA1], opt10=0)
    yield slider("volume slider no click sound", 1, [0x5AA1], 0, volume=40, children=[0x5AA1], opt10=1,
                 family_sound={"click": "absent"})
    yield slider("volume slider sound flag", 1, [0x5AA1], 0, volume=40, children=[0x5AA1], opt10=1,
                 family_sound={"flag": 1})
    yield slider("volume slider click sound off", 1, [0x5AA1], 0, volume=40, children=[0x5AA1], opt10=1,
                 family_sound={"click": "off"})
    yield slider("volume slider sound disabled", 1, [0x5AA1], 0, volume=40, children=[0x5AA1], opt10=1, sound=0)
    # music slider (0x5aa4)
    for flag in (0, 1, 2):
        for option in (0, 3):
            yield slider(f"music slider flag {flag} option {option}", flag, [0x5AA4], 0, children=[0x5AA4],
                         opt14=option, opt50=1)
    yield slider("music slider without its option", 1, [0x5AA4], 0, children=[0x5AA4], opt14=3, opt50=0)
    # level slider (0x5b06): only moves that clamp to the current level avoid the redraw chain
    for flag, level in ((0, 10), (1, 1), (2, 1), (7, 1)):
        yield slider(f"level slider flag {flag} level {level}", flag, [0x5B06, 0x5B05], 0, level=level,
                     children=[0x5B06])
    yield slider("level slider other child", 1, [0x5B06], 0, level=4, children=[0x5B05])
    yield slider("level slider no child", 1, [0x5B07], 0, level=4)


# 0x450c50 ---------------------------------------------------------------------------------------
def command_cases(r):
    def command(label, code, wparam, flag, **options):
        return case(label, COMMAND_WITH_FLAGS, (code, wparam, flag), **options)

    sound_states = (
        ("both sounds", {}),
        ("select absent", {"select": "absent"}),
        ("select value null", {"select": "null"}),
        ("select sound disabled", {"select": "off"}),
        ("context flag set", {"flag": 1}),
        ("context flag high", {"flag": 0x80000000}),
        ("no table", {"table": False}),
    )
    for name, state in sound_states:
        for wparam in (0, 0x8036, 0x123456):
            yield command(f"{name} wparam {wparam:#x}", 0x1234, wparam, 0, menu_sound=state, volume=r.randrange(0, 40))
    for wparam in (0xFFFFFFFF, 0x80000000, 0xFFFFFFFE, 1, 0x7FFFFFFF):
        yield command(f"wparam {wparam:#x}", 0x1234, wparam, 0)
    yield command("sound switched off", 0x1234, 5, 0, sound=0)
    yield command("sound argument large", 0x1234, 5, 0, volume=0x24)
    yield command("sound argument zero", 0x1234, 5, 0, volume=0)
    yield command("two sound nodes", 0x1234, 5, 0, menu_sound={"nodes": 2})
    for post in (0, 1, 0xFFFFFFFF):
        yield command(f"post result {post}", 0x1234, 3, 0, post_result=post)
    # with the flag the panel layout runs
    if SET_RECT_IMPORT:
        yield command("flag set, generic code", 0x1234, 0, 1, count=0)
        yield command("flag set and wparam", 0x1234, 4, 1, count=0)
        for code in (0x4E20, 0x4E26, 0x59D9, 0x59DC, 0, 0xFFFFFFFF, 0x59DA, 0x59DB, 0x4E23):
            yield command(f"flag set code {code:#x}", code, 0x20, 1, count=0)


# 0x451e10 ---------------------------------------------------------------------------------------
def scan_cases(r):
    codes = {b"RESUME": 0x5A01, b"OPTIONS": 0x5B02, b"QUIT": 0x5C03, b"ZERO": 0}
    keymap = list(codes.items())

    def scan(label, code, items, **options):
        return case(label, ITEM_SCAN, (code, r.randrange(0, 1 << 32)), items=items, keymap=keymap, **options)

    yield case("no item list", ITEM_SCAN, (0x5A01, 1), keymap=keymap)
    yield case("empty item list", ITEM_SCAN, (0x5A01, 2), keymap=keymap, items=[], count=2)
    yield case("item count zero", ITEM_SCAN, (0x5A01, 2), keymap=keymap, items=[(b"RESUME", 0, 1)], item_count=0)
    yield case("item count negative", ITEM_SCAN, (0x5A01, 2), keymap=keymap, items=[(b"RESUME", 0, 1)],
               item_count=0xFFFFFFFF)
    yield case("only null items", ITEM_SCAN, (0x5A01, 3), keymap=keymap, items=[None, None])
    if CSTRING_IMPORTS:
        yield scan("no item matches", 0x5A01, [(b"OPTIONS", 0, 1), None, (b"QUIT", 0, 1)])
        yield scan("unknown names never equal a nonzero code", 0x5A01, [(b"NOPE", 0, 1), (b"MISSING", 0, 1)])
        yield scan("unknown name equals zero code", 0, [(b"NOPE", 0x20, 1), (b"QUIT", 0, 1)], link_items={0: 0})
        yield scan("fresh string released after the scan", 0x5A01, [(b"OPTIONS", 0, 0), (b"QUIT", 0, 0)])
        yield scan("last string released", 0x1, [(b"OPTIONS", 0, 0), (b"QUIT", 0, 1), (b"UNKNOWN", 0, 0)])
        yield scan("string count of two", 0x5A01, [(b"OPTIONS", 0, 2)])
        yield scan("string count of three at the end", 0x5A01, [(b"OPTIONS", 0, 3)])
        for flags in (0x20, 0x21, 0x2F, 0xFFFFFFFF):
            yield scan(f"matching item flags {flags:#x}", 0x5A01, [(b"OPTIONS", 0, 1), (b"RESUME", flags, 1)],
                       link_items={1: 1})
        yield scan("matching disabled item with reference count zero", 0x5A01, [(b"RESUME", 0x20, 0)],
                   link_items={0: 0})
    if CSTRING_IMPORTS and TICK_IMPORT:
        for flags in (0, 1, 0x10, 0x1F, 0x40, 0x8000, 0xFFFFFFDF):
            yield scan(f"matching item flags {flags:#x}", 0x5A01, [(b"OPTIONS", 0, 1), (b"RESUME", flags, 1)],
                       link_items={1: 1}, cur=0)
        yield scan("first item matches", 0x5A01, [(b"RESUME", 0, 1), (b"OPTIONS", 0, 1)], link_items={0: 0}, cur=2)
        yield scan("last of five matches", 0x5B02, [(b"RESUME", 0, 1), (b"QUIT", 0, 1), None, (b"QUIT", 0, 1),
                                                    (b"OPTIONS", 0x10, 1)], link_items={2: 4}, cur=1, count=3)
        yield scan("match not present in the option list", 0x5A01, [(b"RESUME", 0, 1)], cur=1)
        yield scan("two items match, first wins", 0x5C03, [(b"QUIT", 0, 1), (b"QUIT", 0x10, 1)],
                   link_items={0: 0, 2: 1}, cur=1)
        yield scan("zero code matches first unknown", 0, [(b"NOPE", 0, 1), (b"RESUME", 0, 1)],
                   link_items={0: 0}, cur=1)
        yield scan("matching with key lock", 0x5B02, [(b"OPTIONS", 0, 1)], link_items={0: 0}, key_lock=1)
        yield scan("matching with key lock and later clock", 0x5B02, [(b"OPTIONS", 0x10, 1)], link_items={0: 0},
                   key_lock=1, tick=tick_list([2000, 2001, 2002, 2003]))


# 0x450cf0 ---------------------------------------------------------------------------------------
def dispatch_cases(r):
    def dispatch(label, code, **options):
        return case(label, COMMAND, (code,), **options)

    states = (("both sounds", {}), ("no select", {"select": "absent"}), ("flag", {"flag": 1}),
              ("disabled", {"select": "off"}), ("null value", {"select": "null"}))
    for name, state in states:
        yield dispatch(f"select code, {name}", SELECT_CODE, menu_sound=state)
    yield dispatch("select code, sound off", SELECT_CODE, sound=0)
    yield dispatch("select code, flag already set", SELECT_CODE, flag_2a8=0x77777777)
    yield dispatch("select code, post fails", SELECT_CODE, post_result=0)
    if TIME_IMPORT:
        for name, state in states:
            yield dispatch(f"back code, {name}", BACK_CODE, menu_sound=state)
        yield dispatch("back code, sound off", BACK_CODE, sound=0)
        yield dispatch("back code slow clock", BACK_CODE, time_step=600)
        yield dispatch("back code fast clock", BACK_CODE, time_step=30)
        yield dispatch("back code wrapping clock", BACK_CODE, time_base=0xFFFFFF00, time_step=100)
    if SET_RECT_IMPORT:
        for code in (0x1234, 0x4E20, 0x4E26, 0x59D9, 0, 0xFFFFFFFF, 0x14E21, 0x59DA, 0x59DB, 0x4E23):
            yield dispatch(f"other code {code:#x}", code, count=0)


# 0x450460 ---------------------------------------------------------------------------------------
def key_handler_cases(r):
    def key(label, code, extra=None, **options):
        if extra is None:
            extra = r.randrange(0, 1 << 32)
        return case(label, KEY_HANDLER, (code, extra), **options)

    for code in ALL_SWITCH_KEYS:
        count = 3 if TICK_IMPORT or code not in (0x0D, 0x20) else 0
        yield key(f"key {code:#x}", code, up=mover(2), down=mover(0), count=count)
    for code in DEFAULT_KEYS:
        yield key(f"key {code:#x} with no list", code)
    for code in (0x0D, 0x20):
        yield key(f"key {code:#x} empty list", code, count=0, cur=0)
    if TICK_IMPORT:
        for code in (0x0D, 0x20):
            yield key(f"key {code:#x} stale index", code, count=2, cur=7)
            yield key(f"key {code:#x} key locked", code, count=3, cur=1, key_lock=1)
            for flags in (0, 0x20, 0x10, 0x30):
                yield key(f"key {code:#x} item flags {flags:#x}", code, count=3, cur=1, cflags=[1, flags, 2])
            yield key(f"key {code:#x} key locked, waiting", code, count=3, cur=1, key_lock=1,
                      tick=tick_list([1050, 1100, 1200]))
    # escape
    yield key("escape without items", 0x1B)
    yield key("escape with items", 0x1B, items=[(b"A", 0, 1)])
    yield key("escape with items, sound off", 0x1B, items=[(b"A", 0, 1)], sound=0)
    yield key("escape with items, no select sound", 0x1B, items=[(b"A", 0, 1)], menu_sound={"select": "absent"})
    yield key("escape with items, flag", 0x1B, items=[(b"A", 0, 1)], menu_sound={"flag": 3})
    # left and right keys
    for code in (0x25, 0x27):
        yield key(f"key {code:#x} plain control", code, count=2, types=[0, 0], cur=0)
        yield key(f"key {code:#x} volume control", code, count=2, types=[0x5AA1, 0], cur=0, children=[0x5AA1],
                  opt10=1, volume=40)
        yield key(f"key {code:#x} music control", code, count=2, types=[0x5AA4, 0], cur=0, children=[0x5AA4],
                  opt14=3, opt50=1)
        yield key(f"key {code:#x} level control", code, count=2, types=[0x5B06, 0], cur=0, children=[0x5B06],
                  level=1 if code == 0x25 else 10)
        yield key(f"key {code:#x} no control", code, count=0, cur=0)
    # up and down
    for code in (0x26, 0x28):
        moves = {"unchanged": 1, "next": 2, "first": 0, "negative": 0xFFFFFFFF, "past end": 9}
        for name, target in moves.items():
            effect = mover(target)
            variants = [("", {})]
            if name in ("next", "first", "unchanged"):
                variants += [(" flag", {"flag": 5}), (" no click", {"click": "absent"}),
                             (" click value null", {"click": "null"}), (" sound disabled", {"click": "off"})]
            for label_extra, sound in variants:
                yield key(f"key {code:#x} moves {name}{label_extra}", code, up=effect, down=effect, count=3, cur=1,
                          ui_sound=sound)
        yield key(f"key {code:#x} global sound off", code, up=mover(2), down=mover(2), sound=0)
        yield key(f"key {code:#x} two sound nodes", code, up=mover(0), down=mover(0), ui_sound={"nodes": 2})
        for volume in (0, 1, 12, 80):
            yield key(f"key {code:#x} volume {volume}", code, up=mover(2), down=mover(2), volume=volume)
    for _ in range(10):
        count = r.randrange(1, 6)
        yield key("random move", r.choice((0x26, 0x28)), up=mover(r.randrange(0, count + 2)),
                  down=mover(r.randrange(0, count + 2)), count=count, cur=r.randrange(0, count),
                  geometry=[(r.randrange(-50, 400), r.randrange(-50, 400), r.randrange(1, 90), r.randrange(1, 60))
                            for _ in range(count)])
    # default keys search the item list
    codes = [(b"RESUME", 0x5A01), (b"QUIT", 0x5C03)]
    if CSTRING_IMPORTS:
        yield key("default key, items without match", 0x41, items=[(b"QUIT", 0, 1), None], keymap=codes)
        yield key("default key, unknown names", 0x41, items=[(b"NOPE", 0, 1)], keymap=codes)
        yield key("default key, matching disabled item", 0x5A01, items=[(b"RESUME", 0x20, 1)], keymap=codes,
                  link_items={0: 0}, cur=2)
    if CSTRING_IMPORTS and TICK_IMPORT:
        yield key("default key matching an item code", 0x5A01, items=[(b"RESUME", 0, 1)], keymap=codes,
                  link_items={0: 0}, cur=2)
        yield key("default key matching, index unchanged", 0x5A01, items=[(b"RESUME", 0, 1)], keymap=codes,
                  link_items={1: 0}, cur=1)
        yield key("default key matching zero", 0, items=[(b"NOPE", 0, 1)], keymap=codes, link_items={0: 0}, cur=2)


# 0x450850 ---------------------------------------------------------------------------------------
def rectangle(geometry, index):
    """The hit rectangle the original computes for a control when every image is 34 by 14."""
    x, y, w, h = geometry[index]
    left = int((w - 34) / 2) + x
    top = int((h - 14) / 2) + y
    return left, top, left + 34, top + 14


def pointer_cases(r):
    def pointer(label, **options):
        return case(label, POINTER_HANDLER,
                    (r.randrange(0, 1 << 32), r.randrange(0, 1 << 32), r.randrange(0, 1 << 32)), **options)

    for count, cur in ((0, 0), (3, 0xFFFFFFFF), (3, 3), (3, 0x7FFFFFFF)):
        yield pointer(f"key lock set, {count} controls, index {cur:#x}", key_lock=1, count=count, cur=cur)
    if not CURSOR_IMPORTS:
        return
    geometry = [(10, 20, 100, 50), (200, 20, 100, 50), (10, 120, 100, 50)]
    boxes = [rectangle(geometry, i) for i in range(3)]

    def at(index, dx, dy):
        left, top, right, bottom = boxes[index]
        return (left + dx if dx >= 0 else right + dx + 1, top + dy if dy >= 0 else bottom + dy + 1)

    base = dict(count=3, geometry=geometry, uniform=True)
    for target in range(3):
        for cur in range(3):
            yield pointer(f"cursor over control {target}, current {cur}", cursor=at(target, 6, 5), cur=cur, **base)
    for name, point in (("nothing", (5000, 5000)), ("negative", (-5, -5)), ("origin", (0, 0)),
                        ("left of first", (boxes[0][0] - 1, boxes[0][1] + 3)),
                        ("right of first", (boxes[0][2], boxes[0][1] + 3)),
                        ("above first", (boxes[0][0] + 3, boxes[0][1] - 1)),
                        ("below first", (boxes[0][0] + 3, boxes[0][3]))):
        yield pointer(f"cursor over {name}", cursor=point, cur=1, **base)
    yield pointer("cursor on the top left corner of the third", cursor=(boxes[2][0], boxes[2][1]), cur=0, **base)
    yield pointer("cursor on the last pixel of the third", cursor=(boxes[2][2] - 1, boxes[2][3] - 1), cur=0, **base)
    for cflags in ([0x20, 0, 0], [0, 0x20, 0], [0x20, 0x20, 0x20], [0x10, 0x10, 0], [0, 0x21, 0], [0, 0x0F, 0]):
        for locked in (0, 1):
            yield pointer(f"hover lock {locked} flags {cflags}", cursor=at(1, 6, 5), cur=0, cflags=cflags,
                          hover_lock=locked, **base)
    yield pointer("hover lock on the current control", cursor=at(0, 6, 5), cur=0, cflags=[0x20, 0, 0], hover_lock=1,
                  **base)
    for last, now_ticks in ((900, [1100, 1130, 1160]), (900, [920, 940, 960]), (900, [951, 960, 970]),
                            (900, [950, 960, 970]), (900, [1000, 1000, 1000]), (0xFFFFFF00, [20, 40, 60])):
        yield pointer(f"hold time from {last:#x}", cursor=at(2, 6, 5), cur=0, last_tick=last,
                      tick=tick_list(now_ticks), **base)
    for flags in (0, 0x10, 0x30):
        yield pointer(f"current control flags {flags:#x}", cursor=at(1, 6, 5), cur=0, cflags=[flags, 0, 0], **base)
    yield pointer("empty list", cursor=(30, 40), count=0, cur=0)
    # the selection callbacks leave the index outside the list, so the selected control is missing
    for name, effect in (("activation", {"activated": mover(0xFFFFFFFF)}), ("activation past end", {"activated": mover(9)}),
                         ("press", {"pressed": mover(0xFFFFFFFF)}), ("press past end", {"pressed": mover(7)})):
        yield pointer(f"{name} leaves no selected control", cursor=at(1, 6, 5), cur=0, **effect, **base)
    for _ in range(12):
        count = r.randrange(1, 6)
        geo = [(r.randrange(-30, 300), r.randrange(-30, 300), r.randrange(1, 90), r.randrange(1, 60))
               for _ in range(count)]
        point = (r.randrange(-30, 300), r.randrange(-30, 300))
        yield pointer("random pointer", cursor=point, count=count, cur=r.randrange(0, count), geometry=geo,
                      cflags=[r.choice((0, 0x10, 0x20, 0x30)) for _ in geo], hover_lock=r.choice((0, 1)))
    for _ in range(8):
        count = 4
        geo = [(r.randrange(0, 300), r.randrange(0, 300), r.randrange(40, 90), r.randrange(20, 60))
               for _ in range(count)]
        target = r.randrange(count)
        left, top, right, bottom = rectangle(geo, target)
        yield pointer("random pointer inside a control", cursor=(r.randrange(left, right), r.randrange(top, bottom)),
                      count=count, cur=r.randrange(0, count), geometry=geo, uniform=True,
                      cflags=[r.choice((0, 0x10, 0x20, 0x30)) for _ in geo], hover_lock=r.choice((0, 1)))
