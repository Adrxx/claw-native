"""Cases for pause_menu_panels: Pause menu panel build and draw.

The three owned methods work on one pause menu panel object. Cases build the
whole object graph the original code walks (game state, owner, widget tree,
string map, DirectDraw surfaces) out of live heap objects, so the original
callees run unchanged. Imports that the specification declares as fixtures are
driven through env.override; cases that need an import the specification does
not declare are left out (see NEEDS).
"""
import json
import os
from collections import namedtuple
from pathlib import Path

from clawparity.cases import Case
from clawparity.fixtures import returns, set_rect

REBUILD = 0x451680
SLIDER = 0x4520F0
VOLUME = 0x452290

SET_RECT = 0x546D5C
GET_TICK_COUNT = 0x546A24
AIL_GET_VOLUME = 0x546E8C
AIL_SET_VOLUME = 0x546E6C

VOLUME_LEVEL = 0x532C10
SOUND_FLAG = 0x532C0C
MIDI_DRIVER = 0x54131C
HOOK_ROOT = 0x53C9FC

ROOT = 0x19C  # panel offset of the widget tree root (container 0x154 + 0x48)
GAME_CLICK_BUCKET = 0x6447C2DF  # hash of "GAME_CLICK" in the original string map

ID_SOUND, ID_MUSIC, ID_LEVEL = 0x5AA1, 0x5AA4, 0x5B06

_SPEC = json.loads((Path(__file__).parent / "pause_menu_panels.json").read_text())
_DECLARED = {int(address, 16) for address in _SPEC.get("callees", {})}


def declared(address):
    return address in _DECLARED


Geometry = namedtuple("Geometry", "w h x y gw gh")


def geometry(r):
    return Geometry(r.randrange(30, 300), r.randrange(10, 120), r.randrange(0, 400), r.randrange(0, 300),
                    r.randrange(4, 60), r.randrange(4, 40))


def put_node(env, base, ident, g, children=()):
    """A widget at `base`: id, glyph, position, size, and a child list (spec tuples (id, geometry, children))."""
    glyph = env.object(0x30, "glyph", fill=0)
    env.put(glyph + 0x14, g.gh)
    env.put(glyph + 0x18, g.gw)
    env.put(base + 0x50, ident)
    env.put(base + 0x3C + 0x40, glyph)
    env.put(base + 0x3C + 0x54, g.x, g.y)
    env.put(base + 0x3C + 0x5C, g.w, g.h)
    if children:
        array = env.object(4 * len(children), "child-array", fill=0)
        env.put(base + 0x20, len(children))
        env.put(base + 0x1C, array)
        for index, (child_id, child_geometry, grandchildren) in enumerate(children):
            child = env.object(0xA8, "widget", fill=0)
            env.put(array + 4 * index, child)
            put_node(env, child, child_id, child_geometry, grandchildren)


def surface(env, tag):
    """A game surface wrapper whose DirectDraw methods are stand-ins that succeed."""
    wrapper = env.object(0xA0, tag + "-surface", fill=0)
    iface = env.object(8, tag + "-iface", fill=0)
    methods = env.object(0x90, tag + "-methods", fill=0)
    env.put(wrapper + 8, iface)
    env.put(iface, methods)
    for slot, argc in ((0x14, 6), (0x2C, 3), (0x64, 5), (0x80, 2)):
        env.put(methods + slot, env.stub(f"{tag}-dd-{slot:#x}", "stdcall", argc, returns(0)))
    return wrapper


def build(env, tree=(), root_id=0xFFFF, a10=1, a14=1, a50=1, a30=True, a5c=False, a68=5, g30=0,
          click="found", sound=1, level=40, midi=0, midi_volume=0x30, missing=(), a7c=640, a80=480,
          a9c=0, no_registry=False, redraw=True, hooks=None, f298=0, children=None, selected=0,
          ticks=1000, geometry_root=None, live_voice=True, old=None):
    """A pause menu panel with every pointer the three methods read backed by a live object."""
    this = env.object(0x2C0, "panel", fill=0)
    game = env.object(0x140, "game", fill=0)
    inner = env.object(0x40, "game-inner", fill=0)
    inner_ptr = env.object(0x40, "game-inner-ptr", fill=0)
    dims = env.object(0x30, "screen-dims", fill=0)
    rects = env.object(0x50, "clip-list", fill=0)
    mgr = env.object(0x40, "manager", fill=0)
    owner = env.object(0x60, "owner", fill=0)
    reg = env.object(0x80, "registry-owner", fill=0)
    shell = env.object(0x40, "shell", fill=0)
    shell_v = env.object(0x40, "shell-v", fill=0)
    shell_u = env.object(0x40, "shell-u", fill=0)
    shell_t = env.object(0x40, "shell-t", fill=0)
    # game state read through this+4
    env.put(game + 0x10, a10)
    env.put(game + 0x14, a14)
    env.put(game + 0x50, a50)
    env.put(game + 0x68, a68)
    env.put(game + 0x7C, a7c)
    env.put(game + 0x80, a80)
    env.put(game + 0x9C, a9c)
    if a5c:
        listener = env.object(0x20, "volume-listener", fill=0)
        env.put(listener, env.object(0x40, "listener-class", fill=0))
        env.put(game + 0x5C, listener)
    env.put(game + 0x30, inner)
    env.put(inner + 0x28, 1 if a30 else 0)
    env.put(inner + 4, inner_ptr)
    env.put(inner + 0x24, rects)
    env.put(inner_ptr + 0x10, dims)
    env.put(dims + 0x10, 640)
    env.put(dims + 0x14, 480)
    # owner read through this+0xc
    env.put(this + 4, game)
    env.put(this + 0xC, owner)
    env.put(owner + 4, shell)
    env.put(owner + 8, mgr)
    env.put(owner + 0x1C, env.object(0x480, "graphics-manager", fill=0))
    env.put(shell + 0x10, shell_v)
    env.put(shell + 0x14, shell_u)
    env.put(shell + 0xC, shell_t)
    env.put(shell_v + 0x2C, surface(env, "v"))
    env.put(shell_u + 0x2C, surface(env, "u"))
    if not no_registry:
        env.put(owner + 0x28, reg)
    env.put(reg + 0x30, g30)
    env.put(reg + 0x2C, 0 if g30 else 0x2C2C)
    env.put(reg + 0x34, 0 if g30 else 0x3434)
    # click sound lookup: string map at reg+0x10 (+4 table, +8 bucket count)
    env.put(reg + 0x18, 7)
    if click != "empty":
        table = env.object(4 * 7, "map-table", fill=0)
        env.put(reg + 0x14, table)
        node = env.object(0x10, "map-node", fill=0)
        if click == "found":
            env.put(node + 8, env.object(16, "key", data=b"GAME_CLICK\0"))
            sound_obj = env.object(0x80, "click-sound", fill=0)
            env.put(node + 0xC, sound_obj)
            voice = env.object(0x60, "click-voice", fill=0)
            env.put(sound_obj + 0x10, voice)
            device = env.object(0x90, "click-device", fill=0)
            env.put(voice + 0x10, device)
            if live_voice:
                # a playable voice: the click allocates a sound instance and drives the buffer
                env.put(device + 0x78, 1)
                direct_sound = env.object(8, "click-direct-sound", fill=0)
                ds_methods = env.object(0x20, "click-direct-sound-methods", fill=0)
                env.put(direct_sound, ds_methods)
                env.put(ds_methods + 0x14, env.stub("click-duplicate", "stdcall", 3, returns(0)))
                env.put(device + 0x14, direct_sound)
                buffer = env.object(8, "click-buffer", fill=0)
                methods = env.object(0x50, "click-buffer-methods", fill=0)
                env.put(buffer, methods)
                for slot, argc in ((0x18, 2), (0x1C, 2), (0x20, 2), (0x30, 4), (0x3C, 2), (0x40, 2), (0x44, 2)):
                    env.put(methods + slot, env.stub(f"click-buffer-{slot:#x}", "stdcall", argc, returns(0)))
                env.put(voice + 0xC, buffer)
                env.put(voice + 0x18, 0x40)
                env.put(voice + 0x1C, 0x2B00)
                env.put(voice + 0x20, 0x55)
        else:
            env.put(node + 8, env.object(16, "other-key", data=b"OTHER\0"))
        env.put(table + 4 * (GAME_CLICK_BUCKET % 7), node)
    env.put(SOUND_FLAG, sound)
    env.put(VOLUME_LEVEL, level)
    env.put(MIDI_DRIVER, midi)
    panels = {}
    for offset in (0x258, 0x25C, 0x260, 0x264, 0x268, 0x26C):
        panels[offset] = env.object(0x60, f"panel-{offset:#x}", words=[0x1111 * (offset & 0xFF) + 7 * i for i in range(24)])
        env.put(this + offset, panels[offset])
    for offset in missing:
        env.put(this + offset, 0)
    if old is not None:
        env.put(this + 0x260, old_widget(env, owner, old))
    put_node(env, this + ROOT, root_id, geometry_root or Geometry(120, 30, 17, 23, 9, 7), tree)
    env.put(this + 0x298, f298)
    if redraw:
        x = env.object(0x40, "redraw-owner", fill=0)
        y = env.object(0x90, "redraw-format", fill=0)
        env.put(this + 0x274, x)
        env.put(x + 4, y)
        env.put(x + 0xC, owner)
        env.put(y + 0x78, 32)
    hook_root = 0
    if hooks is not None:
        hook_root = env.object(0x1C0, "hook-root", fill=0)
        log = env.object(0x40, "hook-log", fill=0)
        previous = 0
        for index in range(hooks):
            target = env.object(0x80, "hook-target", fill=0)
            vtable = env.object(0x20, "hook-vtable", fill=0)
            env.put(target + 0x6C, vtable)

            def note(env, call, log=log):
                env.put(log + 4 * (env.calls_so_far(call.function) - 1), call.arguments[0])
                return 0

            env.put(vtable + 0x10, env.stub(f"hook-{index}", "cdecl", 1, note))
            link = env.object(0x10, "hook-link", fill=0)
            env.put(link + 8, target)
            env.put(link, previous)
            previous = link
        env.put(hook_root + 0x1B8, previous)
    env.put(HOOK_ROOT, hook_root)
    if children is not None:
        container = this + 0x154
        array = env.object(4 * 8, "children", fill=0)
        env.put(container + 0xC, array)
        env.put(container + 0x10, len(children))
        env.put(container + 0x1C, selected)
        env.put(container + 0x30, ticks)
        env.put(container + 0x34, 500)
        for index, g in enumerate(children):
            child = env.object(0xA8, "menu-item", fill=0)
            glyph = env.object(0x30, "item-glyph", fill=0)
            env.put(glyph + 0x14, g.gh)
            env.put(glyph + 0x18, g.gw)
            env.put(child + 0x5C, g.w, g.h)
            env.put(child + 0x54, g.x, g.y)
            env.put(child + 0x40, glyph)
            env.put(child + 0x64, index & 1)
            env.put(array + 4 * index, child)
    imports(env, ticks, midi_volume)
    return {"this": this, "game": game, "panels": panels}


def old_widget(env, owner, where):
    """The widget at this+0x260 that 0x451900 retires: flagged, unlinked from its list, destroyed by its virtual destructor."""
    widget = env.object(0x80, "old-widget", words=[0x7000 + i for i in range(32)])
    holder = env.object(0x20, "old-holder", fill=0)
    lists = env.object(0x40, "old-lists", fill=0)
    vtable = env.object(0x10, "old-vtable", fill=0)
    log = env.object(0x10, "old-log", fill=0)

    def destroy(env, call):
        env.put(log, call.receiver, call.arguments[0])
        return 0

    env.put(vtable + 4, env.stub("old-widget-destructor", "thiscall", 1, destroy))
    env.put(widget, vtable)
    env.put(widget + 8, 0x20)
    env.put(widget + 0xC, holder)
    env.put(holder + 8, lists)
    nodes = [env.object(0x10, "list-node", words=[0, 0, 0x100 + i, 0]) for i in range(3)]
    for index, node in enumerate(nodes):
        env.put(node, nodes[index + 1] if index < 2 else 0)
        env.put(node + 4, nodes[index - 1] if index else 0)
    # list at lists+0x10: +4 head, +8 tail, +0xc count, +0x10 free list, +0x14 block chain
    count = 3
    target = {"middle": nodes[1], "head": nodes[0], "tail": nodes[2]}.get(where)
    if where == "sole":
        target = nodes[0]
        env.put(target, 0)
        count = 1
        env.put(lists + 0x14, target)
        env.put(lists + 0x18, target)
        env.put(lists + 0x24, env.object(0x20, "list-block", fill=0))
    else:
        env.put(lists + 0x14, nodes[0])
        env.put(lists + 0x18, nodes[2])
    env.put(lists + 0x1C, count)
    env.put(lists + 0x20, 0)
    env.put(widget + 0x68, target)
    return widget


def imports(env, ticks, midi_volume):
    for address, effect in ((SET_RECT, set_rect), (GET_TICK_COUNT, returns(ticks)),
                            (AIL_GET_VOLUME, returns(midi_volume)), (AIL_SET_VOLUME, returns(0))):
        if address in _DECLARED:
            env.override(address, effect)


def make(function, label, arguments, needs=(), **options):
    """A case for one owned method, or None when it needs an import the specification does not declare."""
    if not all(declared(address) for address in needs):
        return None
    return Case(label, function, lambda env: build(env, **options),
                receiver=lambda tokens: tokens["this"], arguments=arguments,
                covers=tuple(f"needs {address:#x}" for address in needs))


def cases(random_source):
    only = os.environ.get("ONLY")
    for case in _cases(random_source):
        if case is not None and (only is None or only in case.label):
            yield case


def _cases(random_source):
    yield from volume_cases(random_source)
    yield from slider_cases(random_source)
    yield from rebuild_cases(random_source)


def one(r, ident, *deeper):
    """A tree holding widget `ident`, found at the root's child level or `deeper` levels down behind decoys."""
    node = [(ident, geometry(r), [])]
    for decoy in reversed(deeper):
        node = [(decoy, geometry(r), node)]
    return [(0x1, geometry(r), [])] + node


def full_tree(r):
    return [(ID_SOUND, geometry(r), []), (0x77, geometry(r), [(ID_MUSIC, geometry(r), []), (ID_LEVEL, geometry(r), [])])]


def volume_cases(r):
    def V(label, step, ident=ID_SOUND, needs=(), **o):
        o.setdefault("root_id", ident)
        o.setdefault("geometry_root", geometry(r))
        return make(VOLUME, label, (step, ident), needs, **o)

    for offset in (0x264, 0x268, 0x4, 0xC):
        yield V(f"volume gate: panel field {offset:#x} is null", 1, missing=(offset,))
    yield V("volume: widget absent", 1, root_id=0x99, tree=one(r, 0x98))
    for ident in (0x5AA0, 0x5AA2, 0x5AA3, 0x5AA5, 0x15AA1, 0x15AA4, 0x5AA1 ^ 0x100, 0x5AA4 ^ 0x100):
        yield V(f"volume: id {ident:#x} is ignored", 1, ident)
    for depth, decoys in (("root", None), ("child", ()), ("grandchild", (0x5,)), ("great-grandchild", (0x5, 0x6))):
        for ident in (ID_SOUND, ID_MUSIC):
            options = {"root_id": ident} if decoys is None else {"root_id": 0x99, "tree": one(r, ident, *decoys)}
            yield V(f"volume: {ident:#x} found at {depth}", 2, ident, level=36, **options)
    # sound effects volume
    for level in (0, 3, 4, 5, 8, 40, 72, 76, 79, 80, -5, 100):
        for step in (0, 1, 2, 3):
            yield V(f"sound level {level} step {step}", step, level=level)
    for level in (0, 40, 80):
        for step in (0, 1, 2, 3, -1, 9):
            yield V(f"sound level {level} step {step} without game flag", step, a10=0, level=level)
    for _ in range(16):
        yield V("sound random", r.randrange(-1, 4), level=r.randrange(0, 81), a68=r.randrange(1, 10))
    for level, step in ((40, 1), (5, 2), (80, 1), (0, 2)):
        yield V(f"sound {level}/{step}: level not stored by game", step, level=level, a30=False)
        yield V(f"sound {level}/{step}: listener present", step, level=level, a5c=True)
        yield V(f"sound {level}/{step}: no registry", step, level=level, no_registry=True)
        yield V(f"sound {level}/{step}: click suppressed", step, level=level, g30=3)
        for click in ("empty", "other", "found"):
            for sound in (0, 1):
                yield V(f"sound {level}/{step}: click {click} sound {sound}", step, level=level, click=click, sound=sound)
    # music volume
    for step in (0, 1, 2, 3):
        yield V(f"music no driver step {step}", step, ID_MUSIC)
        yield V(f"music no driver step {step} without game flag", step, ID_MUSIC, a14=0)
        yield V(f"music no driver step {step} without music", step, ID_MUSIC, a50=0)
        yield V(f"music no driver step {step} neither flag", step, ID_MUSIC, a14=0, a50=0)
    yield V("music: gate param 7", 7, ID_MUSIC, a14=0)
    needs = (AIL_GET_VOLUME, AIL_SET_VOLUME)
    drivers = [-5, 0, 1, 3, 6, 7, 9, 13, 16, 20, 25, 38, 64, 70, 100, 120, 126, 127, 200]
    drivers += [r.randrange(1, 127) for _ in range(8)]
    for volume in drivers:
        for step in (0, 1, 2, 3):
            yield V(f"music driver {volume} step {step}", step, ID_MUSIC, needs, midi=0x1234, midi_volume=volume)
    for click in ("empty", "other", "found"):
        for sound in (0, 1):
            yield V(f"music driver click {click} sound {sound}", 2, ID_MUSIC, needs, midi=0x4321, midi_volume=64,
                    click=click, sound=sound)
    yield V("music driver click suppressed", 2, ID_MUSIC, needs, midi=0x4321, midi_volume=64, g30=1)
    yield V("music driver without game flag", 1, ID_MUSIC, needs, midi=0x4321, midi_volume=64, a14=0)
    yield V("music driver without music", 1, ID_MUSIC, needs, midi=0x4321, midi_volume=64, a50=0)


def clamp_level(level, step):
    return min(10, max(1, level + (-1 if step == 2 else 1 if step == 1 else 0)))


def slider_cases(r):
    def S(label, step, level, ident=ID_LEVEL, **o):
        needs = (SET_RECT,) if clamp_level(level, step) == 10 and level != 10 else ()
        o.setdefault("root_id", ident)
        o.setdefault("geometry_root", geometry(r))
        return make(SLIDER, label, (step, ident), needs, a68=level, **o)

    for level in (-3, 0, 1, 2, 5, 9, 10, 11, 15):
        for step in (0, 1, 2, 3, -1):
            yield S(f"slider level {level} step {step}", step, level)
    for _ in range(14):
        yield S("slider random", r.randrange(0, 4), r.randrange(0, 13))
    for ident in (0x5B05, 0x5B07, 0x15B06, 0x5B06 ^ 0x100):
        yield S(f"slider: id {ident:#x} is ignored", 1, 4, ident)
    yield S("slider: widget absent", 1, 4, root_id=0x99, tree=one(r, 0x98))
    yield S("slider: widget at child level", 1, 4, root_id=0x99, tree=one(r, ID_LEVEL))
    yield S("slider: widget two levels down", 2, 4, root_id=0x99, tree=one(r, ID_LEVEL, 0x5))
    for level, step in ((4, 1), (7, 2), (3, 0)):
        yield S(f"slider {level}/{step}: click suppressed", step, level, g30=2)
        for click in ("empty", "other", "found"):
            for sound in (0, 1):
                yield S(f"slider {level}/{step}: click {click} sound {sound}", step, level, click=click, sound=sound)
        for hooks in (None, 0, 1, 3):
            yield S(f"slider {level}/{step}: hooks {hooks}", step, level, hooks=hooks)
        yield S(f"slider {level}/{step}: pending state other", step, level, f298=0x1234)


def rebuild_cases(r):
    needs_for = lambda children: (SET_RECT, GET_TICK_COUNT) if children else (SET_RECT,)

    def R(label, param, children=(), **o):
        o.setdefault("geometry_root", geometry(r))
        o.setdefault("missing", (0x260,))
        if "children" not in o:
            o["children"] = list(children)
        return make(REBUILD, label, (param,), needs_for(o["children"]), **o)

    items = lambda n: [geometry(r) for _ in range(n)]
    params = (0x59DB, 0x59DA, 0x59D9, 0x59DC, 0, 0x1234, 0x7FFFFFFF)
    for param in params:
        for count, selected in ((0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (3, 2), (3, 3), (2, -1), (2, 7)):
            yield R(f"rebuild {param:#x} items {count} selected {selected}", param, items(count), selected=selected)
    for param in params:
        for flag in (0, 1):
            yield R(f"rebuild {param:#x} flag {flag}", param, items(2), a9c=flag, a7c=r.randrange(300, 900), a80=r.randrange(200, 700))
    for param in (0x59DB, 0x59DA, 0x1234):
        yield R(f"rebuild {param:#x}: full tree", param, items(2), tree=full_tree(r))
        yield R(f"rebuild {param:#x}: full tree, no items", param, tree=full_tree(r))
        yield R(f"rebuild {param:#x}: sound only", param, items(1), tree=one(r, ID_SOUND))
        yield R(f"rebuild {param:#x}: music only", param, items(1), tree=one(r, ID_MUSIC))
        yield R(f"rebuild {param:#x}: level only", param, items(1), tree=one(r, ID_LEVEL))
        yield R(f"rebuild {param:#x}: nested", param, items(1), tree=one(r, ID_SOUND, 0x5, 0x6))
    for where in ("middle", "head", "tail", "sole"):
        for param in (0x59DB, 0x59DA, 0x1234):
            yield R(f"rebuild {param:#x}: retire old widget at {where}", param, items(1), tree=full_tree(r), missing=(), old=where)
    for level in (0, 1, 33, 80):
        yield R(f"rebuild 0x59db level {level}", 0x59DB, items(2), tree=full_tree(r), level=level, a68=1 + level % 10)
    yield R("rebuild 0x59db level 100", 0x59DB, items(2), tree=full_tree(r), level=100)
    yield R("rebuild 0x59db without music", 0x59DB, items(2), tree=full_tree(r), a50=0)
    yield R("rebuild 0x59db sound off", 0x59DB, items(2), tree=full_tree(r), sound=0)
    yield R("rebuild 0x59db no registry", 0x59DB, items(2), tree=full_tree(r), no_registry=True)
    yield R("rebuild 0x59da level 9", 0x59DA, items(2), tree=full_tree(r), a68=9)
    yield R("rebuild 0x59da level 10", 0x59DA, items(2), tree=full_tree(r), a68=10)
    yield R("rebuild 0x59da level 1", 0x59DA, items(2), tree=full_tree(r), a68=1)
    needs = (AIL_GET_VOLUME, AIL_SET_VOLUME)
    for volume in (0, 20, 64, 127):
        if all(declared(a) for a in needs):
            yield R(f"rebuild 0x59db driver {volume}", 0x59DB, items(2), tree=full_tree(r), midi=0x1234, midi_volume=volume)
