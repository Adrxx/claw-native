"""State-five cases derived from the pinned original instructions."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns
import hashlib
from pathlib import Path
import struct


def asset(path, digest):
    data = (Path(__file__).resolve().parents[2] / path).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Original asset hash mismatch: " + path)
    return data


def platform(env):
    for address in (0x546d50, 0x546880, 0x546d30, 0x546888, 0x546cac,
                    0x546cb4, 0x546cb8, 0x546d9c, 0x546ce4, 0x546de8,
                    0x546e6c, 0x546ca4, 0x546a08, 0x546ca8, 0x546cb0,
                    0x546830, 0x546aac, 0x546aa4, 0x546a9c, 0x546ab8):
        env.override(address, returns(0))
    for address in (0x5469a0, 0x546b38, 0x546a84):
        env.override(address, returns(1))
    env.override(0x546d54, lambda e, c: 0 if c.arguments[0] else 0xffffffff)
    env.override(0x546a30, returns(0xffffffff))
    env.override(0x546a24, lambda e, c: 12345 + 250 * e.calls_so_far(c.function))
    env.override(0x546df0, lambda e, c: 12345 + 250 * e.calls_so_far(c.function))
    env.override(0x546e8c, returns(63))
    env.override(0x546b0c, returns(0))
    env.override(0x546d48, returns(2))
    env.override(0x546d2c, returns(2))
    env.override(0x546a20, returns(0))
    env.override(0x54682c, returns(2))
    env.override(0x546834, returns(2))
    env.override(0x5469c0, returns(23))
    tls = env.object(0x400, "CRT thread state", fill=0)
    env.override(0x546a7c, returns(tls))

    def interlocked(delta):
        def effect(e, call):
            pointer = call.arguments[0]
            value = (e.get(pointer) + delta) & 0xffffffff
            e.put(pointer, value)
            return value
        return effect
    env.override(0x5469e8, interlocked(-1))
    env.override(0x5469ec, interlocked(1))
    env.override(0x5469e4, lambda e, c: len(e.cstr(c.arguments[0])))
    def bounded_copy(e, c):
        destination, source, count = c.arguments
        if count:
            e.write(destination, e.cstr(source)[:count - 1] + b"\0")
        return destination
    env.override(0x5469cc, bounded_copy)

    def rectangle(e, c):
        e.put(c.arguments[0], *c.arguments[1:])
        return 1
    env.override(0x546d5c, rectangle)
    env.override(0x546d58, lambda e, c: (e.write(c.arguments[0], e.read(c.arguments[1], 16)) or 1))

    def cursor(e, c):
        e.put(c.arguments[0], 319, 217)
        return 1
    env.override(0x546cd0, cursor)
    env.override(0x546cd4, returns(0))

    def directory(e, c):
        e.write(c.arguments[1], b"C:\\CLAW\0")
        return 7
    env.override(0x546a28, directory)


def text(env, value, refs=5):
    data = value.encode("latin-1")
    block = env.object(len(data) + 13, "CString storage")
    env.put(block, refs, len(data), len(data))
    env.write(block + 12, data + b"\0")
    return block + 12


def base(env):
    platform(env)
    state = env.object(0x340, "state-five", fill=0)
    app = env.object(0x400, "application", fill=0)
    window = env.object(16, "window", fill=0)
    scene = env.object(0x280, "scene", fill=0)
    context = env.object(0x80, "context", fill=0)
    sound = env.object(0x60, "sound manager", fill=0)
    music = env.object(0x60, "music manager", fill=0)
    profile = env.object(0x2300, "profile", fill=0)
    env.put(state + 4, app)
    env.put(state, 0x50c1e4)
    app_vtable = env.object(0x40, "application vtable", fill=0)
    env.put(app_vtable + 0xc, 0x40af20)
    env.put(app, app_vtable)
    env.put(state + 0x154, 0x513e68)
    env.put(app + 4, window, scene)
    env.put(window + 4, 0x1248)
    env.put(app + 0x30, context)
    env.put(context + 0x28, sound)
    env.put(app + 0x50, music)
    env.put(app + 0x64, profile)
    env.put(app + 0x60, env.object(0x40, "profile metadata", fill=0))
    env.put(app + 0x68, 5)
    env.put(app + 0x100, text(env, ""))
    env.put(state + 0x29c, 10000)
    env.put(state + 0x2b4, 17)  # CString hash table bucket count.
    env.put(state + 0x2c4, 10)
    env.put(sound + 0x18, 17)
    env.put(state + 0x170, 0xffffffff)  # Current flat menu index.
    env.put(state + 0x1ec, 0xfedcba98)  # Root resource ID, distinct from action IDs.
    env.put(0x537b58, 0)
    env.put(0x5371fc, app)
    env.put(0x537e88, 0)
    env.put(0x54131c, 0)
    env.put(0x532c0c, 1, 40)
    env.put(0x525508, 0)
    env.put(state + 0xfc, text(env, "player profile"))
    env.put(app + 0xfc, text(env, "application profile"))
    env.put(0x53c9bc, env.get(0x52e1cc))
    for off in (0x1a8, 0x1b0, 0x1f0, 0x1f4, 0x1f8, 0x1fc,
                0x200, 0x204, 0x208, 0x20c):
        env.put(state + off, env.get(0x52e1cc))
    return {"state": state, "app": app, "window": window, "scene": scene,
            "context": context, "sound": sound, "music": music, "profile": profile}


def setup(changes=None, nodes=(), selected=False, flat=False):
    def prepare(env):
        t = base(env)
        state = t["state"]
        entries = []
        for index, (identity, flags) in enumerate(nodes):
            node = env.object(0xc0, "menu node", fill=0)
            image = env.object(0x40, "menu image", fill=0)
            env.put(node + 0x50, identity)
            env.put(node + 0xc, text(env, f"entry-{identity:x}"))
            env.put(node + 0x14, text(env, f"entry-{identity:x}"))
            env.put(node + 0x7c, image)
            variants = env.object(32, "menu image variants", words=[image] * 8)
            env.put(node + 0x40, variants)
            env.put(node + 0x80, flags)
            env.put(node + 0x90, 101 + index * 71, 211 + index * 37,
                    31 + index * 3, 19 + index * 5)
            env.put(image + 0x14, 13 + index, 17 + index)
            entries.append(node)
        if entries:
            vector = env.object(len(entries) * 4, "menu node vector", words=entries)
            env.put(state + 0x1b8, vector, len(entries))
            if flat:
                visual_vector = env.object(len(entries) * 4, "flat widget vector",
                                           words=[node + 0x3c for node in entries])
                env.put(state + 0x160, visual_vector, len(entries))
                env.put(state + 0x170, 0)
            if selected:
                env.put(state + 0x24c, state + 0x19c)
        t["nodes"] = entries
        for offset in (0x25c, 0x260, 0x270, 0x274, 0x278):
            child = env.object(0x1c0, "child actor", fill=0)
            env.put(child, 0x5137f0)
            env.put(child + 8, 0x59040020 ^ offset)
            env.put(state + offset, child)
            t[offset] = child
        # These children are deliberately absent unless a case requests them.
        for offset in (0x25c, 0x260, 0x270, 0x274, 0x278):
            env.put(state + offset, 0)
        if changes:
            changes(env, t)
        return t
    return prepare


def entry(label, address, arguments=(), prepare=None):
    return Case(label, address, prepare or setup(),
                receiver=lambda t: t["state"], arguments=arguments)


def surface_context(env, t):
    display = env.object(0x80, "display", fill=0)
    image = env.object(0x50, "image", fill=0)
    wrapper = env.object(0xc0, "surface wrapper", fill=0)
    interface = env.object(4, "DirectDraw surface")
    vt = env.object(0x90, "DirectDraw methods", fill=0)
    env.put(interface, vt)
    env.put(wrapper + 8, interface)
    env.put(image + 0x2c, wrapper)
    env.put(t["state"] + 0xc, t["context"])
    env.put(t["context"] + 4, display)
    env.put(display + 0x14, image)
    env.put(vt + 0x44, env.stub("IDirectDrawSurface::GetDC", "stdcall", 2,
                              lambda e, c: (e.put(c.arguments[1], 0) or 0)))
    env.put(vt + 0x1c, env.stub("IDirectDrawSurface::BltFast", "stdcall", 6, returns(0)))
    t.update(display=display, image=image, wrapper=wrapper, interface=interface)


def mapping(env, address, pairs):
    count = 17
    buckets = env.object(count * 4, "hash buckets", fill=0)
    env.put(address + 4, buckets, count, len(pairs))
    for key, value in pairs:
        encoded = key.encode("latin-1")
        hashed = 0
        for byte in encoded:
            hashed = (hashed * 33 + (byte if byte < 128 else byte - 256)) & 0xffffffff
        slot = buckets + hashed % count * 4
        node = env.object(16, "hash node", words=[env.get(slot), hashed % count,
                                                  text(env, key), value])
        env.put(slot, node)


def com_surface_methods(env):
    # Register once during setup. Per-surface state lives in guest memory so
    # neither execution can change the other's callback state or identities.
    def description(e, interface, pointer):
        metadata = e.get(interface) + 0x84
        width, height, pixels = (e.get(metadata + offset) for offset in (0, 4, 8))
        e.write(pointer, bytes(108))
        e.put(pointer, 108, 0x100f, height, width, width)
        e.put(pointer + 0x24, pixels)
        e.put(pointer + 0x48, 32, 0x20)
        e.put(pointer + 0x54, 8)

    def get_description(e, call):
        description(e, call.arguments[0], call.arguments[1])
        return 0

    def lock(e, call):
        description(e, call.arguments[0], call.arguments[2])
        return 0

    def no_dc(e, call):
        e.put(call.arguments[1], 0)
        return 0
    methods = [
        (0x58, env.stub("IDirectDrawSurface::GetSurfaceDesc", "stdcall", 2, get_description)),
        (0x64, env.stub("IDirectDrawSurface::Lock", "stdcall", 5, lock)),
        (0x80, env.stub("IDirectDrawSurface::Unlock", "stdcall", 2, returns(0))),
        (0x44, env.stub("IDirectDrawSurface::GetDC", "stdcall", 2, no_dc)),
    ]
    for offset, name, argc in ((8, "Release", 1), (0x14, "Blt", 6),
                               (0x1c, "BltFast", 6), (0x60, "IsLost", 1),
                               (0x2c, "Flip", 3),
                               (0x68, "ReleaseDC", 2), (0x6c, "Restore", 1),
                               (0x74, "SetColorKey", 3), (0x7c, "SetPalette", 2)):
        methods.append((offset, env.stub("IDirectDrawSurface::" + name, "stdcall", argc, returns(0))))
    return tuple(methods)


def com_surface(env, width, height, methods=None):
    if methods is None:
        methods = com_surface_methods(env)
    pixels = env.object(max(1, width * height), "DirectDraw pixels", fill=0x5d)
    interface = env.object(4, "DirectDraw surface")
    vt = env.object(0x90, "DirectDraw methods", fill=0)
    env.put(interface, vt)
    # Unused tail words retain physical surface metadata without another
    # allocation or a mutable Python closure shared by the two executions.
    env.put(vt + 0x84, width, height, pixels)
    for offset, function in methods:
        env.put(vt + offset, function)
    return interface


def surface_manager(env, t):
    manager = env.object(0x900, "surface manager", fill=0)
    directdraw = env.object(4, "DirectDraw")
    vt = env.object(0x80, "DirectDraw methods", fill=0)
    env.put(directdraw, vt)
    env.put(manager, directdraw)
    env.put(manager + 0x474, 8)
    env.put(manager + 0x878, 1)
    env.put(manager + 0x3d0, 16)
    env.put(manager + 0x3ec, 16)
    surface_methods = com_surface_methods(env)
    palette_methods = (
        (8, env.stub("IDirectDrawPalette::Release", "stdcall", 1, returns(0))),
        (0x10, env.stub("IDirectDrawPalette::GetEntries", "stdcall", 5,
                       lambda e, c: (e.write(c.arguments[4], bytes([0x3d]) * (c.arguments[3] * 4)) or 0))),
        (0x18, env.stub("IDirectDrawPalette::SetEntries", "stdcall", 5, returns(0))),
    )

    def create(e, call):
        description, output = call.arguments[1:3]
        width, height = e.get(description + 0xc), e.get(description + 8)
        e.put(output, com_surface(e, width, height, surface_methods))
        return 0
    env.put(vt + 0x18, env.stub("IDirectDraw::CreateSurface", "stdcall", 4, create))
    def create_palette(e, call):
        palette = e.object(4, "DirectDraw palette")
        methods = e.object(0x20, "DirectDraw palette methods", fill=0)
        e.put(palette, methods)
        for offset, function in palette_methods:
            e.put(methods + offset, function)
        e.put(call.arguments[3], palette)
        return 0
    env.put(vt + 0x14, env.stub("IDirectDraw::CreatePalette", "stdcall", 5, create_palette))
    env.put(t["context"] + 0x1c, manager)
    t["surface_manager"] = manager


def actor_context(env, t):
    surface_context(env, t)
    manager = env.object(0x50, "actor manager", fill=0)
    logic = env.object(0x50, "logic registry", fill=0)
    images = env.object(0x50, "image registry", fill=0)
    animations = env.object(0x50, "animation registry", fill=0)
    env.put(manager + 0xc, t["context"])
    env.put(manager + 0x28, 16)
    env.put(t["context"] + 8, manager)
    env.put(t["context"] + 0x10, images, logic)
    env.put(t["context"] + 0x28, t["sound"], animations)
    env.put(images + 0x18, 17)
    env.put(animations + 0x18, 17)
    pairs = []
    for name in ("DoNothing", "AniCycle", "MenuClaw", "SimpleAnimation", "MenuSparkle"):
        descriptor = env.object(0x20, "logic descriptor", fill=0)
        env.put(descriptor + 0x10, 0x4bc110)
        pairs.append((name, descriptor))
    mapping(env, logic + 0x10, pairs)
    t.update(manager=manager, images=images, logic=logic, animations=animations)


def resource_context(env, t):
    actor_context(env, t)
    frames = env.object(65 * 4, "image frames", words=[t["image"]] * 65)
    group = env.object(0x70, "image group", fill=0)
    env.put(group + 0x14, frames)
    env.put(group + 0x64, 0, 64)
    env.put(t["wrapper"] + 0x14, 40, 51)
    env.put(t["image"] + 0x10, 640, 480, 8)
    names = ("MENU_MAIN", "MENU_MAIN_SINGLEPLAYER", "MENU_MAIN_SINGLEPLAYER_LEVELS",
             "MENU_MAIN_SINGLEPLAYER_LOAD_CHECKPOINTS", "MENU_MAIN_SINGLEPLAYER_LOAD",
             "MENU_MAIN_SINGLEPLAYER_NEW", "MENU_MAIN_SINGLEPLAYER_SAVE",
             "MENU_MAIN_MULTIPLAYER", "MENU_MAIN_MULTIPLAYER_GAMELOBBY",
             "MENU_MAIN_REPLAYMOVIES", "MENU_MAIN_OPTIONS", "MENU_MAIN_OPTIONS_EDIT",
             "MENU_MAIN_OPTIONS_DIFFICULTY", "MENU_MAIN_OPTIONS_AUDIO",
             "MENU_MAIN_OPTIONS_DISPLAY", "MENU_MAIN_QUIT", "MENU_CURSOR", "MENU_CLAW",
             "MENU_COINS")
    mapping(env, t["images"] + 0x10, [(name, group) for name in names])
    t.update(resource_frames=frames, resource_group=group)
    env.put(t["app"] + 0x30, t["context"])
    env.put(0x537b58, t["state"])
    for off in (0x25c, 0x260, 0x270, 0x274, 0x278):
        env.put(t[off] + 0xc, t["context"])


def distinct_resource_frames(env, t):
    # Original 0x45f940 selects the actual indexed frame and returns +0x2c.
    # Distinct frames and surfaces expose index/argument mistakes even when
    # each resource is otherwise a valid image with the same dimensions.
    for index in range(65):
        frame = env.object(0x50, f"distinct resource frame {index}",
                           data=env.read(t["image"], 0x50))
        wrapper = env.object(0xc0, f"distinct resource surface {index}",
                             data=env.read(t["wrapper"], 0xc0))
        env.put(frame + 0x2c, wrapper)
        env.put(t["resource_frames"] + index * 4, frame)


def sound_context(env, t, playing=False):
    resource_context(env, t)
    records = []
    for key in ("SELECT", "CLICK", "DISABLE", "INTRO", "UNROLL", "MENUBED",
                "1055", "CRKNGTEST"):
        record = env.object(0x30, "sound resource", fill=0)
        sound = env.object(0x60, "sound object", fill=0)
        pool = env.object(0x90, "sound pool", fill=0)
        env.put(record + 0x10, sound)
        env.put(sound + 0x10, pool)
        env.put(sound + 0x28, 13)
        if playing and key in ("MENUBED", "1055", "CRKNGTEST"):
            interface = env.object(4, "DirectSound buffer")
            vt = env.object(0x60, "DirectSound methods", fill=0)
            env.put(interface, vt)
            env.put(sound + 0xc, interface)
            env.put(pool + 0x78, 1)
            env.put(vt + 0x24, env.stub("IDirectSoundBuffer::GetStatus", "stdcall", 2,
                                      lambda e, c: (e.put(c.arguments[1], 1) or 0)))
            env.put(vt + 0x48, env.stub("IDirectSoundBuffer::Stop", "stdcall", 1, returns(0)))
            env.put(vt + 0x18, env.stub("IDirectSoundBuffer::GetVolume", "stdcall", 2,
                                      lambda e, c: (e.put(c.arguments[1], -1200) or 0)))
            env.put(vt + 0x3c, env.stub("IDirectSoundBuffer::SetVolume", "stdcall", 2, returns(0)))
        records.append((key, record))
    mapping(env, t["sound"] + 0x10, records)
    t["sound_records"] = dict(records)


def retiring_actors(env, t):
    actor_context(env, t)
    actors = []
    for off in (0x258, 0x264, 0x25c, 0x260):
        actor = env.object(0x1c0, "retiring actor", fill=0)
        env.put(actor, 0x5137f0)
        env.put(actor + 8, 0x80904020 ^ off)
        env.put(actor + 0xc, t["context"])
        env.put(t["state"] + off, actor)
        actors.append(actor)
    sparkles = []
    for index in range(15):
        actor = env.object(0x1c0, "retiring sparkle", fill=0)
        env.put(actor, 0x5137f0)
        env.put(actor + 8, 0x30140002 ^ index)
        env.put(actor + 0xc, t["context"])
        actors.append(actor)
        sparkles.append(actor)
    env.put(t["state"] + 0x26c, env.object(60, "sparkle vector", words=sparkles))
    positions = [env.object(12, "actor list position", fill=0) for _ in actors]
    for index, actor in enumerate(actors):
        env.put(positions[index], positions[index + 1] if index + 1 < len(positions) else 0,
                positions[index - 1] if index else 0, actor)
        env.put(actor + 0x68, positions[index])
    env.put(t["manager"] + 0x14, positions[0], positions[-1], len(positions))
    for off in (0x268, 0x270, 0x274, 0x278):
        child = env.object(0x54, "unlinked child", fill=0x49)
        env.put(t["state"] + off, child)


def resource_index(env, address, buckets_count, pairs):
    buckets = env.object(buckets_count * 16, "resource index buckets", fill=0)
    env.put(address, buckets_count, buckets)
    for key, obj, link_offset in pairs:
        bucket = (key if isinstance(key, int) else len(key)) % buckets_count
        node = obj + link_offset
        slot = buckets + 8 + bucket * 16
        env.put(node, 0, env.get(slot), 0, address, bucket, obj)
        env.put(slot, node + 4)


def directory(env, name, directories=(), files=()):
    obj = env.object(0x60, "resource directory " + name, fill=0)
    env.put(obj, text(env, name))
    resource_index(env, obj + 0x3c, 5, [(n, a, 0x24) for n, a in directories])
    groups = []
    for extension in sorted(set(ext for _, ext, _ in files)):
        group = env.object(0x40, "resource type group", fill=0)
        code = int.from_bytes(extension.encode("ascii"), "big")
        env.put(group, code)
        relevant = [(n, a) for n, ext, a in files if ext == extension]
        resource_index(env, group + 0x1c, 19, [(n, a, 0x48) for n, a in relevant])
        # Direct lookup uses its separate name index; its link records are
        # independent of the file's iteration membership.
        table = env.object(19 * 16, "file name index", fill=0)
        env.put(group + 0x24, 19, table)
        for n, a in relevant:
            bucket = len(n) % 19
            slot = table + 8 + bucket * 16
            node = env.object(24, "file name link", words=[0, env.get(slot), 0, group + 0x24, bucket, a])
            env.put(slot, node + 4)
        groups.append((code, group, 4))
    resource_index(env, obj + 0x44, 9, groups)
    return obj


def resident_file(env, name, extension, data):
    file = env.object(0x70, "resident file " + name, fill=0)
    payload = env.object(len(data), "resident asset bytes", data=data)
    archive = env.object(0x30, "resident archive", fill=0)
    file_type = env.object(4, "resource extension", words=[int.from_bytes(extension.encode("ascii"), "big")])
    env.put(file, text(env, name))
    env.put(file + 8, file_type)
    env.put(file + 0x14, len(data))
    env.put(file + 0x24, archive)
    env.put(archive + 0x20, payload)
    return file


def resident_resources(env, t, include_ifc=False, include_screen=False):
    resource_context(env, t)
    surface_manager(env, t)
    pcx = bytearray(128)
    pcx[0:4] = bytes((10, 5, 1, 8))
    struct.pack_into("<4H", pcx, 4, 0, 0, 63, 63)
    pcx[65] = 1
    struct.pack_into("<H", pcx, 66, 64)
    pcx.extend(bytes((0xff, 0x37, 0x37)) * 64)
    pcx.extend(bytes((12,)) + bytes(range(256)) * 3)
    menu_screen = resident_file(env, "MENU", "PCX", bytes(pcx))
    paper_screen = resident_file(env, "PAPER", "PCX", bytes(pcx))
    screens = directory(env, "SCREENS", files=[("MENU", "PCX", menu_screen)] if include_screen else [])
    paper_screens = directory(env, "SCREENS", files=[("PAPER", "PCX", paper_screen)])
    roller_dir = directory(env, "ROLLER", directories=[("SCREENS", paper_screens)])
    sounds = directory(env, "SOUNDS")
    images = directory(env, "IMAGES")
    anis = directory(env, "ANIS")
    chord = resident_file(env, "CHORD", "XMI", bytes(4))
    music = directory(env, "MUSIC", files=[("CHORD", "XMI", chord)])
    files = []
    if include_ifc:
        raw = asset("work/original-disc-assets/STATES/MENU/CLAW.IFC",
                    "e371e28c41aeb8245d33942bb1cb2cbec64c043df63f9968a6873c8e1403c345")
        original_ifc = resident_file(env, "CLAW", "IFC", raw)
        files.append(("CLAW", "IFC", original_ifc))
    menu = directory(env, "MENU", directories=[("SCREENS", screens), ("SOUNDS", sounds),
                                               ("IMAGES", images), ("ANIS", anis), ("MUSIC", music)], files=files)
    states = directory(env, "STATES", directories=[("MENU", menu), ("ROLLER", roller_dir)])
    level = directory(env, "LEVEL1")
    root = directory(env, "ROOT", directories=[("STATES", states), ("LEVEL1", level)])
    resources = env.object(0x40, "resource manager", fill=0)
    env.put(resources + 0x24, root)
    env.put(t["app"] + 0x34, resources)
    env.put(t["state"] + 8, resources)
    env.put(t["state"] + 0x20, menu)
    env.put(t["state"] + 0x19c, 0x513ed8)
    t.update(resources=resources, menu_directory=menu, sound_directory=sounds,
             image_directory=images, animation_directory=anis)


def render_context(env, t):
    resource_context(env, t)
    surface_manager(env, t)
    env.put(t["manager"], 0x513c20)
    env.put(t["images"], 0x513b88)
    env.put(t["logic"], 0x513b60)
    env.put(t["animations"], 0x513ad8)
    for key in ("images", "logic", "animations", "sound"):
        env.put(t[key] + 0xc, t["context"])
        env.put(t[key] + 0x28, 10)
    if not env.get(t["state"] + 0x20):
        image_directory = directory(env, "IMAGES")
        env.put(t["state"] + 0x20, directory(env, "MENU", directories=[("IMAGES", image_directory)]))
    renderer = env.object(0x40, "renderer", fill=0)
    env.put(renderer, 0x513be8)
    env.put(renderer + 0xc, t["context"])
    env.put(t["context"] + 0xc, renderer)
    roller_manager = env.object(0x68, "roller manager", fill=0)
    env.put(roller_manager, 0x513b28)
    env.put(roller_manager + 0xc, t["context"])
    env.put(t["context"] + 0x18, roller_manager)
    for offset in (0x18, 0x34, 0x50):
        env.put(roller_manager + offset, 17)
    for offset in (0x28, 0x44, 0x60):
        env.put(roller_manager + offset, 10)
    env.put(t["wrapper"], 0x513690)
    env.put(t["wrapper"] + 0x14, 64, 64, 64)
    env.put(t["wrapper"] + 0xa4, 8)
    env.put(t["wrapper"] + 0xac, 1)
    env.put(t["image"], 0x50e8e4)
    env.put(t["image"] + 0xc, t["context"])
    env.put(t["image"] + 0x10, 64, 64, 16)
    env.put(t["display"] + 0x10, t["image"])
    back = env.object(0x50, "back image", fill=0)
    env.put(back, 0x50e8e4)
    env.put(back + 0xc, t["context"])
    env.put(back + 0x10, 64, 64, 16)
    env.put(back + 0x2c, t["wrapper"])
    env.put(t["display"] + 0x18, back)
    env.put(t["display"] + 0xc, t["context"])
    env.put(t["state"] + 0x34, 1)
    vt = env.get(t["interface"])
    for offset, name, argc in ((8, "Release", 1), (0x14, "Blt", 6),
                               (0x2c, "Flip", 3),
                               (0x60, "IsLost", 1), (0x6c, "Restore", 1)):
        env.put(vt + offset, env.stub("IDirectDrawSurface::" + name, "stdcall", argc, returns(0)))
    def observe_blt(e, call):
        record = e.object(156, "observed DirectDraw Blt", fill=0)
        e.put(record, *call.arguments)
        if call.arguments[1]:
            e.write(record + 24, e.read(call.arguments[1], 16))
        if call.arguments[3]:
            e.write(record + 40, e.read(call.arguments[3], 16))
        if call.arguments[5]:
            e.write(record + 56, e.read(call.arguments[5], 100))
        return 0
    env.put(vt + 0x14, env.stub("IDirectDrawSurface::Blt", "stdcall", 6, observe_blt))
    palette = env.object(0x40, "palette object", fill=0)
    palette_interface = env.object(4, "DirectDraw palette")
    palette_vt = env.object(0x20, "DirectDraw palette methods", fill=0)
    env.put(palette_interface, palette_vt)
    entries = env.object(1024, "palette entries", fill=0x2c)
    saved = env.object(1024, "saved palette", fill=0x75)
    env.put(palette + 4, palette_interface)
    env.put(palette + 0xc, entries, saved)
    env.put(palette_vt + 0x10, env.stub("IDirectDrawPalette::GetEntries", "stdcall", 5,
                                     lambda e, c: (e.write(c.arguments[4], bytes([0x3d]) * (c.arguments[3] * 4)) or 0)))
    env.put(palette_vt + 0x18, env.stub("IDirectDrawPalette::SetEntries", "stdcall", 5, returns(0)))
    roller = env.object(0x40, "roller", fill=0)
    env.put(roller, 0x513d78)
    env.put(roller + 0xc, t["context"], palette)
    env.put(t["state"] + 0x2c, roller)
    t.update(roller=roller, palette=palette, renderer=renderer, roller_manager=roller_manager)
    env.put(0x5430d0, 3)
    env.put(0x5430d8, 0, 0, 0, 0)
    env.put(0x5430f0, 0, 0, 0, 0)
    env.put(0x537200, env.object(0x260, "idle input", fill=0))


def cases(random_source):
    # Signed range checks and distinct message payloads.
    for level in (-0x80000000, -1, 0, 1, 2, 14, 15, 0x7fffffff):
        for fn in (0x42b990, 0x42b9c0):
            args = (level,) if fn == 0x42b990 else (level, random_source.getrandbits(32))
            yield Case(f"level dispatch {fn:x} {level}", fn, setup(),
                       receiver=lambda t: t["app"], arguments=args)
    for _ in range(10):
        values = tuple(random_source.getrandbits(32) for _ in range(3))
        yield entry("constructor fields", 0x45fde0, values)

    # Exact early-return paths, without replacing the original game callees.
    for fn in (0x45b130, 0x45b240, 0x45e0e0, 0x45e1b0, 0x45e7c0,
               0x45e880, 0x45ce60):
        yield entry(f"empty state {fn:x}", fn)
    yield entry("initialization without parent", 0x45ace0, (0, 0x34, 0x58))
    for fn in (0x45b8c0, 0x45b960, 0x45b9a0):
        def reject(env, t):
            vt = env.object(0x80, "state vtable", fill=0)
            env.put(vt + 0xc, 0x40af20)
            env.put(t["state"], vt)
        yield entry(f"readiness rejected {fn:x}", fn, prepare=setup(reject))

    for fn, offset in ((0x45e370, 0x28c), (0x45e5c0, 0x290)):
        for mask in (0, 1, 2, 4, 8, 15, 0xf0000000, random_source.getrandbits(32)):
            def dirty(env, t, off=offset, bits=mask):
                env.put(t["state"] + off, bits)
            yield entry(f"dirty mask {fn:x} {mask:x}", fn, prepare=setup(dirty))
    for fn in (0x45ef30, 0x45eff0):
        for arg in (0, 1, 0x2713, 0x2af9, 0x2afa, 0xffffffff):
            yield entry(f"empty menu {fn:x} {arg:x}", fn, (arg,))
    for arg in (0, 0x2713, 0x2af9, 0x2afa, 0xffffffff):
        yield Case(f"empty column layout {arg:x}", 0x45fa80, setup(),
                   receiver=lambda t: t["state"] + 0x154, arguments=(arg,))
    for fn in (0x45f100, 0x45f360):
        for direction in (0, 1, 2, 3):
            for identity in (0x3459, 0x345c, 0x34c0, 0x1234):
                yield entry(f"missing slider {fn:x} {direction} {identity:x}", fn,
                            (direction, identity))
    for fn, arg in ((0x45dc90, 10000), (0x45e990, 0x53)):
        yield entry(f"empty activation {fn:x}", fn, (arg,) if fn == 0x45dc90 else (arg, 0xabcdef))
    for flag in (0, 1):
        yield entry(f"sound absent {flag}", 0x45f490,
                    (lambda t: t["sound_name"], flag),
                    setup(lambda e, t: t.update(sound_name=text(e, "CLICK"))))
    for movie in (0, 15000, 0x3aa4, 0xffffffff):
        def deferred(env, t, value=movie):
            env.put(t["state"] + 0x294, 1, value)
        yield entry(f"invalid deferred movie {movie:x}", 0x45e040, prepare=setup(deferred))

    # Action switch defaults and local-only/post-message branches.
    defaults = (0x45c420, 0x45c4a0, 0x45c580, 0x45c610, 0x45c6f0,
                0x45c7c0, 0x45c800, 0x45c880, 0x45cb90, 0x45cfa0,
                0x45d000, 0x45d070, 0x45d0f0, 0x45d150, 0x45d3b0)
    for fn in defaults:
        yield entry(f"unknown action {fn:x}", fn, (0xffffffff,), setup(actor_context))
    for action in (0, 10000, 11000, 0x2aff, 12000, 0x2ee5, 13000, 0x32cf,
                   14000, 0x36b3, 15000, 0x3aa4, 0xffffffff):
        yield entry(f"unhandled routing {action:x}", 0x45c240, (action, 1))
    for action in (10001, 0x3459, 0xffffffff):
        yield entry(f"disabled routing {action:x}", 0x45c240, (action, 0))
    for fn, actions in ((0x45c420, (0x2715, 0x2717)),
                        (0x45c580, (0x2ee1, 0x2ee3)),
                        (0x45c610, (0x32c9, 0x32cb)),
                        (0x45cfa0, (0x36b1,)),
                        (0x45c800, (15000, 15001, 0x3aa2, 0x3aa4))):
        for action in actions:
            yield entry(f"action {fn:x} {action:x}", fn, (action,))
    for command in (0, 1, 0x8035, 0x7fffffff, 0xffffffff):
        yield entry(f"command signed check {command:x}", 0x45c3d0, (0x2715, command, 0))
    for enabled in (0, 1):
        def publish(env, t, yes=enabled):
            env.put(0x537b58, t["state"] if yes else 0)
        yield Case(f"global callback {enabled}", 0x45fa50, setup(publish), arguments=(0xffffffff, 1))
    yield Case("null surface draw", 0x45fbb0, setup(), arguments=(0, 13, 27, 389, 433))

    # Dirty child flags survive and distinguish OR from assignment and wrong offsets.
    for flags in (0, 1, 0x80000400, random_source.getrandbits(32)):
        def children(env, t, bits=flags):
            for offset in (0x270, 0x274, 0x278):
                env.put(t["state"] + offset, t[offset])
                env.put(t[offset] + 0x40, bits ^ offset)
        yield entry(f"hide all sliders {flags:x}", 0x45db40, (0x2714,), setup(children))
    for action in (0, 0x2713, 0x2af9, 0x2afa, 0x2bc1, 0x32cc, 0x32cd, 0xffffffff):
        yield entry(f"empty menu layout {action:x}", 0x45d500, (action,))
        yield entry(f"empty paired menu layout {action:x}", 0x45d720, (action,))
    yield entry("no heading for unknown action", 0x45d750, (0xffffffff,),
                setup(lambda e, t: e.put(t["state"] + 0xc, t["context"])))

    for key in ("missing", "", "Sound", "\xff\x80"):
        def lookup(env, t, name=key):
            t["key"] = text(env, name)
        yield entry(f"accelerator absent {key!r}", 0x45ef00,
                    (lambda t: t["key"],), setup(lookup))
    for value in ("", "unknown", "123", "001_optionsaudio_sound"):
        def string_arg(env, t, s=value):
            t["arg"] = text(env, s)
        yield Case(f"image lookup without global {value}", 0x45f940,
                   setup(string_arg), arguments=(lambda t: t["arg"],))
    yield entry("profile name copy", 0x45cd60,
                (lambda t: t["output"],),
                setup(lambda e, t: t.update(output=e.object(4, "CString result"))))

    # A CString is passed by value, including the physical incoming argument
    # word destroyed by the original parser. Parsing and all string helpers run.
    paths = ("main", "singleplayer", "singleplayernew", "singleplayerload",
             "singleplayerloadsub", "singleplayersave", "multiplayer",
             "multiplayergamelobby", "replay", "options", "optionsedit",
             "optionsdifficulty", "optionsaudio_sound", "optionsaudio_music",
             "optionsaudio_voice", "optionsaudio_ambient", "optionsdisplay_depth",
             "optionsdisplay_detail", "optionsdisplay_front", "optionsdisplay_movies",
             "quit", "unrecognized")
    for path in paths:
        for bits in (0, 1):
            def parser(env, t, p=path, b=bits):
                t["input"] = text(env, "017_" + p + "_")
                t["output"] = env.object(4, "parsed CString", words=[env.get(0x52e1cc)])
                t["number"] = env.object(4, "parsed integer", words=[0xa5a5a5a5])
                for off in (0x10, 0x14, 0x118, 0x11c, 0x120, 0x124, 0x128):
                    env.put(t["app"] + off, b)
                env.put(t["app"] + 0x78, 8 if b else 16)
            yield entry(f"parse {path} settings {bits}", 0x45be10,
                        (lambda t: t["input"], lambda t: t["output"], lambda t: t["number"]),
                        setup(parser))
    for prefix in ("", "000", "031", "036", "-1", "2147483647"):
        def numeric(env, t, p=prefix):
            t["input"] = text(env, p + "_optionsaudio_sound")
            t["output"] = env.object(4, "parsed CString", words=[env.get(0x52e1cc)])
            t["number"] = env.object(4, "parsed integer")
        yield entry(f"parse integer {prefix}", 0x45be10,
                    (lambda t: t["input"], lambda t: t["output"], lambda t: t["number"]),
                    setup(numeric))

    # Found menu entries are real recursive resource-tree nodes. No lookup
    # fixture stands in for the original 0x4dd020 / 0x4df200 bodies.
    for direction in (0, 1, 2, 3):
        for volume in (0, 1, 7, 8, 39, 72, 79, 80):
            for enabled in (0, 1):
                def slider(env, t, v=volume, on=enabled):
                    env.put(t["state"] + 0x270, t[0x270])
                    env.put(t["app"] + 0x10, on)
                    env.put(0x532c10, v)
                yield entry(f"sound slider {direction} {volume} {enabled}", 0x45f100,
                            (direction, 0x3459), setup(slider, ((0x3459, 1),)))
    for direction in (0, 1, 2, 3):
        for enabled in (0, 1):
            def music_slider(env, t, on=enabled):
                env.put(t["state"] + 0x274, t[0x274])
                env.put(t["app"] + 0x14, on)
            yield entry(f"music slider at maximum {direction} {enabled}", 0x45f100,
                        (direction, 0x345c), setup(music_slider, ((0x345c, 1),)))
    for identity in (0x3458, 0x345a, 0x345b, 0x345d, 0x34bf, 0x34c1):
        for fn in (0x45f100, 0x45f360):
            yield entry(f"found non-slider {fn:x} {identity:x}", fn, (1, identity),
                        setup(nodes=((identity, 1),)))
    for detail in (1, 2, 5, 9, 10):
        def unchanged_detail(env, t, d=detail):
            env.put(t["app"] + 0x68, d)
            env.put(t["state"] + 0x278, t[0x278])
        yield entry(f"detail slider unchanged {detail}", 0x45f360, (0, 0x34c0),
                    setup(unchanged_detail, ((0x34c0, 1),)))
    for action in (0, 0x2b5d, 0x2b6b, 0x2bc1, 0x2bcf, 0x3a99):
        def coin_children(env, t):
            env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
            env.put(t["state"] + 0x27c, 73, 101, 509, 571)
        yield entry(f"coin cursor {action:x}", 0x45ef30, (action,),
                    setup(coin_children, ((action, 1),), flat=True))
    for fn in (0x45f100, 0x45f360):
        yield entry(f"recursive missing lookup {fn:x}", fn, (1, 0x1234),
                    setup(nodes=((0x3459, 1), (0x345c, 1), (0x34c0, 1))))

    for fn in (0x45b050, 0x429530):
        yield entry(f"empty complete teardown {fn:x}", fn)
    for flags in (0, 1, 2, 3):
        yield entry(f"state delete flags {flags}", 0x429510, (flags,))
    for key in (0, 13, 27, 32, 37, 38, 39, 40, 0xffffffff):
        yield entry(f"empty key dispatch {key}", 0x45ba50, (key, 0xa15824))
    yield entry("empty mouse selection", 0x45bd90, (3, 17, 31))
    def empty_input(env, t):
        device = env.object(0x260, "input device", fill=0)
        env.put(0x537200, device)
    yield entry("idle input", 0x45bbc0, prepare=setup(empty_input))
    for action in (0, 3, 4, 14, 15, 0xffffffff):
        yield entry(f"deactivation {action}", 0x45b540, (action,))
    for action in (0, 2, 5, 8, 9, 13, 0xffffffff):
        yield entry(f"activation {action}", 0x45b3f0, (action,))
    for fn in (0x45cd90, 0x45ce80):
        yield entry(f"refresh empty controls {fn:x}", fn)
    def audio_context(env, t):
        env.put(t["state"] + 0xc, t["context"])
        env.put(t["context"] + 0x28, t["sound"])
    yield entry("refresh empty audio controls", 0x45cee0, prepare=setup(audio_context))
    for fail in (False, True):
        def sparkles(env, t, no_memory=fail):
            audio_context(env, t)
            env.override(0x4f63ec, allocate(fail=no_memory))
        yield entry(f"sparkle vector allocation fail {fail}", 0x45e8f0, prepare=setup(sparkles))
    for fn in (0x45d410, 0x45d3f0):
        yield entry(f"unknown menu full transition {fn:x}", fn, (0xffffffff,), setup(surface_context))
    yield Case("GetDC returns no DC", 0x45fbb0, setup(surface_context),
               arguments=(lambda t: t["wrapper"], 37, 59, 431, 593))
    def blit_source(env, t):
        surface_context(env, t)
        t["source"] = env.object(0x50, "source image", fill=0x8b)
        source_surface = env.object(16, "source surface", fill=0)
        env.put(source_surface + 8, 0x8912)
        env.put(t["source"] + 0x2c, source_surface)
        env.put(t["state"] + 0x2c, t["wrapper"])
    yield entry("copy image surface", 0x45fee0, (lambda t: t["source"],), setup(blit_source))
    def deferred_return(env, t):
        env.put(t["state"] + 0x294, 1, 0)
        env.put(t["state"] + 0x254, 4567)
        env.put(0x54132c, 123)
    yield entry("frame defers movie work", 0x45b650, prepare=setup(deferred_return))
    def accelerators(env, t):
        addresses = (0x529188, 0x52917c, 0x52916c, 0x528100, 0x529164, 0x5280f8,
                     0x52915c, 0x529150, 0x529144, 0x529130, 0x529124, 0x529114,
                     0x5280c8, 0x529108, 0x5290fc, 0x5290f0, 0x5290e4, 0x5290d8,
                     0x5290cc, 0x5290c0, 0x5290b4, 0x5290a8, 0x52909c, 0x52908c,
                     0x52907c, 0x52906c, 0x52905c, 0x526fc4, 0x52904c, 0x52903c,
                     0x529034, 0x529028, 0x529014, 0x529004, 0x528ff4, 0x528fec,
                     0x528fd8, 0x528fcc, 0x528fc0, 0x528fb8, 0x528fa8, 0x528f98,
                     0x528f88, 0x528f78, 0x528f6c, 0x5280e0, 0x5280d8, 0x5280d0,
                     0x528f68, 0x528f60, 0x528f58, 0x528f50, 0x525704, 0x5256fc,
                     0x5256f4, 0x52570c, 0x528f48, 0x528f40, 0x5280c0, 0x5280b8,
                     0x5280b0, 0x52700c, 0x527024)
        mapping(env, t["state"] + 0x2ac,
                [(env.cstr(a).decode("latin-1"), 0xa5293e17 ^ a) for a in addresses])
    yield entry("populate every accelerator", 0x45ea80, prepare=setup(accelerators))
    for action in (10000, 0x2711, 0x2712, 0x2713, 0x2714, 0x2716,
                   0x2af9, 0x2afa, 0x2afc, 0x2bc1, 0x2bce, 0x2ee2,
                   0x32c9, 0x32ca, 0x32cc, 0x32cd):
        yield entry(f"construct heading {action:x}", 0x45d750, (action,), setup(actor_context))
    for fn in (0x45b240, 0x45e8f0):
        yield entry(f"construct actors {fn:x}", fn, prepare=setup(actor_context))

    # Route each open interval into its original action body.
    for action in (10001, 11001, 0x2b5d, 0x2bc1, 0x1b58b, 0x2c89,
                   12001, 0x2fa9, 15001, 13001, 0x332d, 0x3391,
                   0x345c, 0x34be, 14001):
        yield entry(f"routed action {action:x}", 0x45c240, (action, 1), setup(actor_context))
    for fn, actions in ((0x45c4a0, range(0x2af9, 0x2aff)),
                        (0x45c580, (0x2ee2, 0x2ee4)),
                        (0x45c610, (0x32ca, 0x32cc, 0x32cd, 0x32ce)),
                        (0x45c6f0, range(0x332d, 0x3332)),
                        (0x45c7c0, (0x3391,)), (0x45c800, (0x3aa3,)),
                        (0x45cfa0, (0x36b2,)), (0x45d000, (0x2fa9, 0x2faa)),
                        (0x45d070, (0x2b5d, 0x2b5e, 0x2b6a, 0x2b6b)),
                        (0x45d0f0, (0x2bc1, 0x2bce, 0x2bcf)),
                        (0x45d3b0, (0x2c89,))):
        for action in actions:
            def action_context(env, t, target=fn):
                actor_context(env, t)
                if target == 0x45c6f0:
                    env.put(t["app"] + 0x30, 0)
            yield entry(f"action branch {fn:x} {action:x}", fn, (action,), setup(action_context))
    for level in range(14):
        for slot in range(4):
            action = 0x1b58b + level * 10 + slot
            yield entry(f"save selection level {level+1} slot {slot}", 0x45d150,
                        (action,), setup(actor_context))
    for action in (10000, 0x2712, 0x2713, 0x2714, 0x2716, 0x2afc,
                   0x2bc1, 0x2ee2, 0x32c9, 0x32ca, 0x32cc, 0x32cd):
        yield entry(f"menu bounds {action:x}", 0x45d500, (action,),
                    setup(nodes=((0x3459, 1), (0x345c, 1)), flat=True))
    for direction in (0, 1, 2, 3):
        for raw in (0, 1, 7, 19, 63, 70, 120, 127):
            def music_volume(env, t, value=raw):
                env.put(0x54131c, 0x12345678)
                env.override(0x546e8c, returns(value))
                env.put(t["app"] + 0x14, 1)
                env.put(t["state"] + 0x274, t[0x274])
            yield entry(f"music quantization {direction} {raw}", 0x45f100,
                        (direction, 0x345c), setup(music_volume, ((0x345c, 1),)))
    for direction, detail in ((2, 1), (1, 10), (1, 5), (2, 5), (3, 5)):
        def detail_change(env, t, d=detail):
            surface_context(env, t)
            env.put(t["app"] + 0x68, d)
            env.put(t["state"] + 0x278, t[0x278])
            env.put(t["context"] + 4, t["display"])
            env.put(t["display"] + 0x10, t["image"])
            env.put(t["image"] + 0x10, 640, 480)
            viewport = env.object(0x50, "viewport", fill=0)
            env.put(t["context"] + 0x24, viewport)
        yield entry(f"detail change {direction} {detail}", 0x45f360,
                    (direction, 0x34c0), setup(detail_change, ((0x34c0, 1),)))
    for easy in (0, 4):
        for version in (0, 7):
            def draw_text(env, t, mode=easy, build=version):
                surface_context(env, t)
                env.write(t["profile"] + 0x14, b"Distinct player\0")
                env.put(t["profile"] + 4, mode)
                env.put(0x53ec3c, build)
                vt = env.get(t["interface"])
                env.put(vt + 0x44, env.stub("IDirectDrawSurface::GetDC", "stdcall", 2,
                                           lambda e, c: (e.put(c.arguments[1], 0x5678) or 0)))
                env.put(vt + 0x68, env.stub("IDirectDrawSurface::ReleaseDC", "stdcall", 2, returns(0)))
                draws = env.object(4 * 256, "observed DrawText calls", fill=0x6b)
                def observe_draw(e, call):
                    record = draws + (e.calls_so_far(call.function) - 1) * 256
                    e.put(record, *call.arguments)
                    e.write(record + 20, e.read(call.arguments[3], 16))
                    label = e.cstr(call.arguments[1])
                    e.put(record + 36, len(label))
                    e.write(record + 40, label + b"\0")
                    return 0
                env.override(0x546d30, observe_draw)
            yield Case(f"profile overlay {easy} {version}", 0x45fbb0, setup(draw_text),
                       arguments=(lambda t: t["wrapper"], 37, 59, 431, 593))
    for mask in (0, 1, 2, 4, 8, 15):
        for fn, offset, ids in ((0x45e370, 0x28c, (0x3459, 0x345a, 0x345b, 0x345c)),
                                 (0x45e5c0, 0x290, (0x34bd, 0x34be, 0x34bf, 0x34c1))):
            def dirty_nodes(env, t, bits=mask, off=offset):
                resource_context(env, t)
                env.put(t["state"] + off, bits)
            yield entry(f"dirty real controls {fn:x} {mask:x}", fn,
                        prepare=setup(dirty_nodes, tuple((i, 1) for i in ids)))
    for flags in (0, 2, 4, 0x20, 0x26):
        for fn, page, ids in ((0x45e7c0, 0x32cc, (0x3459, 0x345c)),
                              (0x45e880, 0x32cd, (0x34c0,))):
            def highlighted(env, t, p=page):
                resource_context(env, t)
                env.put(t["state"] + 0x29c, p)
                for off in (0x270, 0x274, 0x278):
                    env.put(t["state"] + off, t[off])
            yield entry(f"slider graphic {fn:x} {flags:x}", fn,
                        prepare=setup(highlighted, tuple((i, flags) for i in ids)))
    def ready_display(env, t):
        resource_context(env, t)
        back = env.object(0x40, "back image", fill=0)
        env.put(back, 0x50e8e4)
        env.put(back + 0xc, t["context"])
        env.put(t["display"] + 0x18, back)
        env.put(t["state"] + 0x34, 1)
        env.put(t["image"] + 0x10, 0, 0)
    yield entry("reload background with invalid geometry", 0x45b880, prepare=setup(ready_display))
    yield entry("ready no roller", 0x45b960, prepare=setup(ready_display))
    def heading_old(env, t):
        actor_context(env, t)
        env.put(t["state"] + 0x268, t[0x270])
    yield entry("retire old heading", 0x45d750, (0xffffffff,), setup(heading_old))
    def old_sparkles(env, t):
        actor_context(env, t)
        old = env.object(60, "old sparkle vector", words=[t[0x270] if i % 2 else 0 for i in range(15)])
        env.put(t["state"] + 0x26c, old)
    yield entry("replace mixed sparkle table", 0x45e8f0, prepare=setup(old_sparkles))
    for page, first, count in ((0x2713, 0x3a99, 10), (0x2af9, 0x2b5d, 14),
                                (0x2afa, 0x2bc1, 14)):
        for index in (0, count // 2 - 1, count // 2, count - 1, count, count + 1):
            def columns(env, t):
                parent, child = t["nodes"]
                vector = env.object(8, "nested menu vector", words=[0, child])
                env.put(parent + 0x1c, vector, 2)
            yield Case(f"column layout {page:x} index {index}", 0x45fa80,
                       setup(columns, ((page, 1), (first + index, 1))),
                       receiver=lambda t: t["state"] + 0x154, arguments=(page,))
    for flags in (0, 0x20):
        for key in (0, 0x53, 0x5a):
            def accelerator_search(env, t):
                mapping(env, t["state"] + 0x2ac, [("entry-3459", 0x53)])
            yield entry(f"accelerator search {flags} {key}", 0x45e990,
                        (key, 0x13579bdf), setup(accelerator_search, ((0x3459, flags),),
                                              selected=True, flat=True))
    for first in (0x2b5d, 0x2bc1, 0x3a99, 0x3459, 0x345c, 0x34c0, 0x1234):
        for direction in (0, 1):
            def navigate(env, t):
                resource_context(env, t)
                env.put(t["state"] + 0x270, t[0x270], t[0x274], t[0x278])
                env.put(t["app"] + 0x10, 1, 1)
                env.put(t["display"] + 0x10, t["image"])
                env.put(t["context"] + 0x24, env.object(0x50, "viewport", fill=0))
            yield entry(f"navigation {first:x} {direction}", 0x45eff0, (direction,),
                        setup(navigate, ((first, 1), (first + 7, 1), (first + 5, 0x20)), flat=True))
    for bits in (0, 1):
        for action in range(0x3459, 0x345e):
            def audio_toggle(env, t, b=bits):
                resource_context(env, t)
                ambient = env.object(0x40, "ambient controller", fill=0)
                env.put(ambient, t["sound"])
                env.put(ambient + 0x24, b)
                env.put(t["app"] + 0x5c, ambient)
                for off in (0x10, 0x14, 0x118, 0x11c):
                    env.put(t["app"] + off, b)
            yield entry(f"audio toggle {action:x} {bits}", 0x45c880, (action,),
                        setup(audio_toggle, tuple((i, 1) for i in range(0x3459, 0x345d))))
        for action in range(0x34bd, 0x34c3):
            def display_toggle(env, t, b=bits):
                resource_context(env, t)
                env.override(0x546a30, returns(1 if b else 0xffffffff))
                for off in (0x120, 0x124, 0x128):
                    env.put(t["app"] + off, b)
            yield entry(f"display toggle {action:x} {bits}", 0x45cb90, (action,),
                        setup(display_toggle, tuple((i, 1) for i in range(0x34bd, 0x34c2))))
    for page in (0x32cc, 0x32cd):
        for flags in (0, 0x20):
            def visibility(env, t, p=page):
                resource_context(env, t)
                env.put(t["state"] + 0x29c, p)
                for off in (0x270, 0x274, 0x278):
                    env.put(t["state"] + off, t[off])
                    env.put(t[off] + 0x40, 0x81004002 ^ off)
            yield entry(f"slider visibility {page:x} {flags:x}", 0x45db40, (page,),
                        setup(visibility, ((0x3459, flags), (0x345c, flags), (0x34c0, flags))))
    for playing in (False, True):
        for bits in (0, 1):
            for action in range(0x3459, 0x345d):
                def found_audio(env, t, b=bits, p=playing):
                    sound_context(env, t, p)
                    ambient = env.object(0x40, "ambient controller", fill=0)
                    env.put(ambient, t["sound"])
                    env.put(ambient + 0x24, b)
                    env.put(t["app"] + 0x5c, ambient)
                    for off in (0x10, 0x14, 0x118, 0x11c):
                        env.put(t["app"] + off, b)
                yield entry(f"found audio {action:x} {bits} {playing}", 0x45c880,
                            (action,), setup(found_audio, tuple((i, 1) for i in range(0x3459, 0x345d))))
    for enabled in (0, 1):
        for wait in (0, 1):
            def found_sound(env, t, on=enabled):
                sound_context(env, t)
                env.put(0x532c0c, on)
                t["key"] = text(env, "CLICK")
            yield entry(f"play named sound {enabled} {wait}", 0x45f490,
                        (lambda t: t["key"], wait), setup(found_sound))
    for sound_found in (False, True):
        for music_found in (0, 1):
            def audio_refresh(env, t, found=sound_found, music=music_found):
                sound_context(env, t) if found else actor_context(env, t)
                env.put(t["music"] + 0x28, music)
                env.put(t["app"] + 0x10, 1)
            yield entry(f"audio availability {sound_found} {music_found}", 0x45cee0,
                        prepare=setup(audio_refresh))
    def directory_fails(env, t):
        actor_context(env, t)
        env.override(0x546b38, returns(0))
        env.override(0x546b0c, returns(3))
    yield entry("custom directory unavailable", 0x45c4a0, (0x2afb,), setup(directory_fails))
    def image_missing(env, t):
        resource_context(env, t)
        t["arg"] = text(env, "001_main_")
        env.put(t["images"] + 0x14, 0)  # Well-formed empty resource map.
    yield Case("image group unavailable", 0x45f940, setup(image_missing),
               arguments=(lambda t: t["arg"],))
    yield entry("remove every retiring actor", 0x45b130, prepare=setup(retiring_actors))
    for page in (0x32cc, 0x32cd):
        def transition_selected(env, t):
            resource_context(env, t)
            env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
            env.put(t["state"] + 0x270, t[0x270], t[0x274], t[0x278])
        yield entry(f"selected page transition {page:x}", 0x45d410, (page,),
                    setup(transition_selected, ((0x3459, 1), (0x345c, 1), (0x34c0, 1)), flat=True))
    for key in (13, 27, 32, 37, 38, 39, 40):
        def selected_keys(env, t):
            resource_context(env, t)
            env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
        yield entry(f"selected keyboard {key}", 0x45ba50, (key, 0x98765432),
                    setup(selected_keys, ((0x2b5d, 1), (0x2b64, 1)), selected=True, flat=True))
    for held in (False, True):
        for direction in range(5):
            for delay, elapsed in ((0, 1), (1, 2), (5, 1)):
                def polling(env, t, h=held, d=direction, wait=delay, step=elapsed):
                    resource_context(env, t)
                    device = env.object(0x260, "keyboard input", fill=0)
                    env.put(device + 0x1cc, 1)
                    env.put(device + 0x1dc, *range(100, 112))
                    bit = (0x10000000 << d) if d < 4 else 1
                    env.put(device + 0x20c, bit if h else 0)
                    env.put(0x537200, device)
                    env.put(0x53720c, step)
                    env.put(t["state"] + 0x2a8, wait)
                    env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
                    env.override(0x546ce4,
                                 lambda e, c, k=100+d: (0x8000 if c.arguments[0] == k else 0))
                yield entry(f"physical input {direction} held {held} delay {delay}/{elapsed}",
                            0x45bbc0, prepare=setup(polling, ((0x2b5d, 1), (0x2b64, 1)), flat=True))
    for page in (10000, 0x2711):
        def mouse_select(env, t, p=page):
            resource_context(env, t)
            env.put(t["state"] + 0x29c, p)
            env.put(t["state"] + 0x170, 1)
            env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
            env.override(0x546cd4, returns(1))
        yield entry(f"physical mouse selects {page:x}", 0x45bd90, (0x201, 0, 0),
                    setup(mouse_select, ((0x2b5d, 1), (0x2b64, 1)), flat=True))
    for fn in (0x45b8c0, 0x45b9a0, 0x45b960, 0x45e0e0, 0x45e1b0, 0x45b650):
        def complete_render(env, t):
            render_context(env, t)
            env.put(t["state"] + 0x254, 10000)
            env.put(0x54132c, 7)
        yield entry(f"retail rendering {fn:x}", fn, prepare=setup(complete_render))
    for fn in (0x45b3f0, 0x45b540):
        for action in (0, 3, 8, 14):
            def roller_action(env, t):
                sound_context(env, t, playing=True)
                render_context(env, t)
                env.put(0x525508, 1)
                env.override(0x546d54, lambda e, c: (1 if e.calls_so_far(c.function) < 3 else 0xffffffff))
            yield entry(f"roller action {fn:x} {action}", fn, (action,), setup(roller_action))
    for action in range(0x3a99, 0x3aa4):
        for available in (0, 1):
            def movie_work(env, t, a=action, yes=available):
                env.put(t["state"] + 0x294, 1, a)
                env.put(t["app"] + 0x9c, 1)
                if yes and a != 0x3a99:
                    env.put(t["app"] + 0x100, text(env, "movies.smk"))
                    env.override(0x546a30, returns(1))
            yield entry(f"movie request {action:x} available {available}", 0x45e040,
                        prepare=setup(movie_work))
    for width, height in ((17, 23), (-3, -5), (0, 1)):
        def cursor_image(env, t, w=width, h=height):
            resource_context(env, t)
            env.put(t["image"] + 0x10, w, h)
        yield entry(f"cursor image dimensions {width}/{height}", 0x45b240,
                    prepare=setup(cursor_image))
    def sound_controller(env, t):
        resource_context(env, t)
        env.put(t["app"] + 0x10, 1)
        env.put(t["sound"] + 0x2c, env.object(0x90, "inactive music controller", fill=0))
    yield entry("disable existing music controller", 0x45c880, (0x3459,), setup(sound_controller))
    def cleanup_context(env, t):
        render_context(env, t)
        env.put(t["images"] + 0x14, 0)
        env.put(t["images"] + 0x1c, 0)
        env.put(t["state"] + 0x2c, 0)
        env.put(t["context"] + 0x28, t["sound"])
        env.put(t["sound"] + 0x2c, env.object(0x90, "inactive sound controller", fill=0))
        for off in (0x268, 0x270, 0x274, 0x278):
            env.put(t["state"] + off, t[0x270] if off == 0x268 else t[off])
    yield entry("complete service cleanup", 0x45b050, prepare=setup(cleanup_context))
    for with_screen in (False, True):
        def resident_transition(env, t, yes=with_screen):
            resident_resources(env, t, include_screen=yes)
            render_context(env, t)
            # All game surfaces and transition bodies remain original. A
            # resident palette keeps this path off unrelated color-table I/O.
            env.put(t["display"] + 0x10, t["image"])
            env.put(t["wrapper"], 0x513690)
            env.put(t["wrapper"] + 0x14, 64, 64, 64)
            env.put(t["wrapper"] + 0xa4, 8)
            env.put(t["wrapper"] + 0xac, 1)
            transition = env.object(0x30, "transition manager", fill=0)
            env.put(t["state"] + 0x10, transition)
            env.put(0x537238, 1)
        yield entry(f"resident transition screen {with_screen}", 0x45dc90,
                    (0xffffffff,), setup(resident_transition))
    def initialize_empty_resources(env, t):
        resident_resources(env, t, include_ifc=True)
        render_context(env, t)
        env.put(t["app"] + 0x7c, 640, 480)
    yield entry("initialization with resident directory graph", 0x45ace0,
                (lambda t: t["app"], 1, 0), setup(initialize_empty_resources))
    def unavailable_interface_images(env, t):
        initialize_empty_resources(env, t)
        env.put(t["images"] + 0x14, 0)
        env.put(t["images"] + 0x1c, 0)
    yield entry("interface loading fails without its required images", 0x45ace0,
                (lambda t: t["app"], 1, 0), setup(unavailable_interface_images))
    def portal_disappears(env, t):
        actor_context(env, t)
        def registry_key(e, call):
            if e.calls_so_far(call.function) > 4:
                return 2
            e.put(call.arguments[7], 0x7321)
            e.put(call.arguments[8], 1)
            return 0
        def query(e, call):
            e.put(call.arguments[3], 1)
            e.write(call.arguments[4], b"C:\\Portal\0")
            e.put(call.arguments[5], 10)
            return 0
        env.override(0x546834, registry_key)
        env.override(0x54682c, query)
        env.override(0x546a30, returns(1))
    yield entry("portal discovery changes before second lookup", 0x45d000,
                (0x2fa9,), setup(portal_disappears))
    def escape_parent(env, t):
        render_context(env, t)
        parent = env.object(0xc0, "parent menu", fill=0)
        env.put(parent + 0x50, 0xffffffff)
        env.put(t["state"] + 0x1ac, parent)
        env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
    yield entry("escape to populated parent", 0x45ba50, (27, 0x19283746),
                setup(escape_parent, ((0x2b5d, 1), (0x2b64, 1)), selected=True, flat=True))
    for attract in (0, 1):
        def expired(env, t, toggle=attract):
            render_context(env, t)
            env.put(t["state"] + 0x254, 0)
            env.put(0x54132c, 7)
            env.put(0x528a68, toggle)
            env.put(t["app"] + 0x100, text(env, "movie.smk"))
            env.put(t["app"] + 0x9c, 1)
            env.override(0x546a30, returns(1))
        yield entry(f"expired frame attract {attract}", 0x45b650, prepare=setup(expired))
    def lost_surface(env, t):
        render_context(env, t)
        env.put(t["state"] + 0x254, 12345)
        env.put(t["state"] + 0x34, 0)
        env.put(t["app"] + 8, 0)
        vt = env.get(t["interface"])
        env.put(vt + 0x60, env.stub("IDirectDrawSurface::IsLost", "stdcall", 1, returns(1)))
    yield entry("lost surface cannot restore", 0x45b650, prepare=setup(lost_surface))
    def frame_children(env, t):
        render_context(env, t)
        env.put(t["state"] + 0x254, 12345)
        env.put(t["state"] + 0x258, t[0x270])
        env.put(t["state"] + 0x2a0, 13, 29)
        env.put(t["palette"] + 0x34, 1)
        env.put(t["sound"] + 0x2c, env.object(0x90, "inactive sound controller", fill=0))
    yield entry("frame advances active palette and cursor", 0x45b650, prepare=setup(frame_children))
    for fn, playing in ((0x45b3f0, False), (0x45e0e0, True), (0x45e1b0, False)):
        def existing_music(env, t, on=playing):
            sound_context(env, t, playing=on)
            render_context(env, t)
        yield entry(f"existing music {fn:x} playing {playing}", fn,
                    (8,) if fn == 0x45b3f0 else (), setup(existing_music))
    def paint_fails(env, t):
        render_context(env, t)
        env.put(t["state"] + 4, 0)
    yield entry("paint has no application", 0x45b9a0, prepare=setup(paint_fails))
    for missing, lost in ((False, False), (True, False), (False, True)):
        def restoring(env, t, absent=missing, error=lost):
            render_context(env, t)
            env.override(0x546d54, lambda e, c: 1 if e.calls_so_far(c.function) < 3 else 0xffffffff)
            if absent:
                env.put(t["state"] + 0x20, directory(env, "MENU"))
            if error:
                vt = env.get(t["interface"])
                for off in (0x60, 0x6c):
                    env.put(vt + off, env.stub("DirectDraw failure", "stdcall", 1, returns(1)))
        yield entry(f"restore display missing {missing} lost {lost}", 0x45b8c0, prepare=setup(restoring))
    def stale_image(env, t):
        render_context(env, t)
        child = directory(env, "CURSOR")
        images = directory(env, "IMAGES", directories=[("CURSOR", child)])
        menu = directory(env, "MENU", directories=[("IMAGES", images)])
        env.put(t["state"] + 0x20, menu)
        frames = env.object(4, "stale frame vector", words=[t["image"]])
        group = env.object(0x70, "stale retail image group", fill=0)
        env.put(group, 0x513cf8)
        env.put(group + 0x14, frames, 1)
        env.put(group + 0x64, 0, 0)
        mapping(env, t["images"] + 0x10, [("MENU_CURSOR", group)])
    yield entry("restore has fewer resident image frames", 0x45b8c0, prepare=setup(stale_image))
    for mode in (0, 1):
        for old_roller in (False, True):
            def complete_transition(env, t, timer_mode=mode, had_roller=old_roller):
                resident_resources(env, t, include_screen=True)
                render_context(env, t)
                env.put(t["wrapper"] + 8, com_surface(env, 64, 64))
                env.put(t["wrapper"] + 0xa8, 64)
                env.put(t["state"] + 0x10, env.object(0x30, "transition manager", fill=0))
                env.put(0x537238, timer_mode)
                env.put(t["state"] + 0x25c, t[0x25c], t[0x260])
                if not had_roller:
                    env.put(t["state"] + 0x2c, 0)
            yield entry(f"complete transition mode {mode} existing roller {old_roller}",
                        0x45dc90, (0xffffffff,),
                        setup(complete_transition, ((0x3459, 1),), flat=True))
    def fader_geometry_mismatch(env, t):
        resident_resources(env, t, include_screen=True)
        render_context(env, t)
        env.put(t["state"] + 0x10, env.object(0x30, "transition manager", fill=0))
        env.put(t["wrapper"] + 0x14, 8, 8, 8)
        paper = env.object(0xbc, "existing different paper surface", fill=0)
        env.put(paper + 0x14, 8, 8, 8)
        env.put(t["state"] + 0x40, paper)
    yield entry("fader rejects unlike source dimensions", 0x45dc90,
                (0xffffffff,), setup(fader_geometry_mismatch))

    # Successful image choices must not all resolve to the same surface.
    for index in (1, 2, 17, 31, 63, 64):
        def indexed_image(env, t, selected=index):
            resource_context(env, t)
            distinct_resource_frames(env, t)
            t["arg"] = text(env, f"{selected:03d}_main_")
        yield Case(f"distinct successful image index {index}", 0x45f940,
                   setup(indexed_image), arguments=(lambda t: t["arg"],))
    for enabled in (0, 1):
        for fn, offset, ids in ((0x45e370, 0x28c, (0x3459, 0x345a, 0x345b, 0x345c)),
                               (0x45e5c0, 0x290, (0x34bd, 0x34be, 0x34bf, 0x34c1))):
            def distinct_updates(env, t, on=enabled, dirty=offset):
                resource_context(env, t)
                distinct_resource_frames(env, t)
                for node in t["nodes"]:
                    env.put(node + 0x44, 8)
                env.put(t["state"] + dirty, 15)
                env.put(t["app"] + 0x10, on, 1 - on)
                env.put(t["app"] + 0x118, 1 - on, on, 1 - on, on, 1 - on)
                env.put(t["app"] + 0x78, 8 if on else 16)
            yield entry(f"distinct widget surfaces {fn:x} settings {enabled}", fn,
                        prepare=setup(distinct_updates, tuple((i, 1) for i in ids)))

    # One setting at a time differs from its neighbors, unlike the all-on /
    # all-off controls above. Numeric output exposes the selected option word.
    for option, offset in (("sound", 0x10), ("music", 0x14),
                           ("voice", 0x118), ("ambient", 0x11c),
                           ("movies", 0x120), ("detail", 0x124), ("front", 0x128)):
        for enabled in (0, 1):
            def distinct_option(env, t, name=option, target=offset, on=enabled):
                for off in (0x10, 0x14, 0x118, 0x11c, 0x120, 0x124, 0x128):
                    env.put(t["app"] + off, 1 - on)
                env.put(t["app"] + target, on)
                kind = "audio" if target in (0x10, 0x14, 0x118, 0x11c) else "display"
                t["input"] = text(env, "017_options" + kind + "_" + name)
                t["output"] = env.object(4, "distinct parsed CString", words=[env.get(0x52e1cc)])
                t["number"] = env.object(4, "distinct parsed index", words=[0x6b7c8d9e])
            yield entry(f"independent option {option} {enabled}", 0x45be10,
                        (lambda t: t["input"], lambda t: t["output"], lambda t: t["number"]),
                        setup(distinct_option))

    def sound_action(env, t):
        sound_context(env, t)
        env.put(t["app"] + 0x30, 0)
    yield Case("difficulty action plays without waiting over nonzero stack", 0x45c6f0,
               setup(sound_action), receiver=lambda t: t["state"], arguments=(0x332e,),
               initial_stack=((-128, bytes([0x6d]) * 128),))

    def holder_list(env, t):
        holder = env.object(0x34, "original receiving surface holder", fill=0)
        env.put(holder, 0x50e8e4)
        env.put(holder + 0xc, t["context"])
        node = env.object(12, "actor manager holder link", words=[0, 0, holder])
        env.put(t["manager"] + 0x14, node, node, 1)
        t["observing_holder"] = holder
    def populated_redraw(env, t):
        render_context(env, t)
        holder_list(env, t)
    yield entry("redraw forwards surface to real holder list", 0x45e1b0,
                prepare=setup(populated_redraw))

    def populated_transition(env, t):
        resident_resources(env, t, include_screen=True)
        render_context(env, t)
        holder_list(env, t)
        env.put(t["state"] + 0x10, env.object(0x30, "transition manager", fill=0))
        env.put(0x537238, 1)
        def allocated_holder_bytes(e, call):
            result = e.object(call.arguments[0], "allocation", fill=0)
            if call.arguments[0] == 0x34:
                # The real holder constructor leaves this word untouched.
                e.put(result + 0x18, 47)
            return result
        env.override(0x4f63ec, allocated_holder_bytes)
    yield entry("transition forwards created holder to real child", 0x45dc90,
                (0xffffffff,), setup(populated_transition))

    def pixel_effect(env, t):
        render_context(env, t)
        env.put(t["state"] + 0x254, 12345)
        env.put(0x54132c, 7)
        for offset in (0x14, 0x18):
            frame = env.get(t["display"] + offset)
            wrapper = env.object(0xc0, "distinct renderer surface", data=env.read(t["wrapper"], 0xc0))
            env.put(wrapper + 8, com_surface(env, 64, 64))
            env.put(frame + 0x2c, wrapper)
        back = env.get(t["display"] + 0x18)
        env.put(back + 0xc, 0)  # Original readiness returns false; retain effect.
        effect = env.object(0x6c, "original pixel effect", fill=0)
        env.put(effect, 0x513c90)
        env.put(effect + 0x4c, 3, 5)
        env.put(effect + 0x64, 5, 0xa7)
        node = env.object(12, "renderer effect link", words=[0, 0, effect])
        env.put(t["renderer"] + 0x14, node, node, 1)
    yield entry("frame pixel effect touches both distinct surfaces", 0x45b650,
                prepare=setup(pixel_effect))
