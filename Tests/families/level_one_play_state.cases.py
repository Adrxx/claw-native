"""Cases for level_one_play_state: Level 1 Play state vtable slots and helpers."""
from random import Random

from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

F_RET0 = 0x429470
F_DTOR_DEL = 0x429480
F_DTOR = 0x4294A0
F_COPY_STR = 0x46A840
F_CLEAR = 0x46A870
F_LOAD = 0x46B8F0
F_PREP = 0x46BA80
F_DRAW_SETUP = 0x46BC00
F_TEXT = 0x46CA50
F_FLAGS = 0x46EF80
F_TEXTOUT = 0x48FCF0
F_BASE_DEL = 0x40AF60

NEW = 0x4F63EC
DELETE = 0x4F6428
DELETE_OBJECT = 0x54686C
SET_TEXT_COLOR = 0x546880
SET_BK_MODE = 0x546888
TEXT_OUT = 0x546890
INTERLOCKED_DEC = 0x5469E8
INTERLOCKED_INC = 0x5469EC
EMPTY_STRING_GLOBAL = 0x52E1C8
PLAY_VTABLE = 0x50C264

SCRIPTED = (0x546D54, 0x54691C, 0x5469E4, 0x5469E8, 0x5469EC, 0x546DF0, 0x546D5C, 0x546D58, 0x546D30, 0x54686C, 0x546D9C, 0x546CA4,
            0x546880, 0x546888, 0x546890)


def word_bytes(random_source, count):
    return bytes(random_source.randrange(1, 256) for _ in range(count))


def record_draw_text(env, call):
    """DrawTextA: keep the rectangle and the text it was given in a new heap object, so the comparison sees them."""
    text = env.cstr(call.arguments[1])
    env.object(24 + len(text), "draw-text-record", data=env.read(call.arguments[3], 16) + text + b"\0" * 8)
    return 0x2200 + len(text)


def record_text_out(env, call):
    """TextOutA: keep the string that was drawn."""
    text = env.cstr(call.arguments[3])
    env.object(8 + len(text), "text-out-record", data=text + b"\0" * 8)
    return 1


def default_scripted(env, results=None):
    """Every declared scripted import returns a recognisable value unless the case overrides it."""
    results = results or {}
    for address in SCRIPTED:
        env.override(address, results.get(address, returns(0x11000000 + (address & 0xFFFF))))
    for address, effect in ((0x546D30, record_draw_text), (TEXT_OUT, record_text_out)):
        if address not in results:
            env.override(address, effect)


def cstring(env, text, refs=1, name="cstring"):
    """A reference-counted MFC string: header (refs, length, capacity) then the bytes. Returns the data pointer."""
    body = text + b"\0"
    header = env.object(12 + len(body) + 4, name, fill=0)
    env.put(header, refs, len(text), len(body))
    env.write(header + 12, body)
    return header + 12


def empty_grid(env, name):
    """A grid whose search rectangle is empty (left edge past right edge), so the walker ends at once."""
    grid = env.object(0x80, name, fill=0)
    env.put(grid + 0x28, 1)
    env.put(grid + 0x30, 0)
    return grid


def walker_grid(env, name, items):
    """A 2x2 cell grid whose search rectangle is the whole grid. items: (cell, x, y, kind) with kind None for a
    node without an entity, 0 for an entity without a class record, or the class function address."""
    grid = env.object(0x80, name, fill=0)
    env.put(grid + 0xC, 2)
    env.put(grid + 0x30, 1)
    env.put(grid + 0x34, 1)
    cells = env.object(0x20, name + "-cells", fill=0)
    env.put(grid + 0x40, cells)
    for cell, x, y, kind in items:
        entity = 0
        if kind is not None:
            entity = env.object(0x180, name + "-entity", fill=0)
            env.put(entity + 8, 0x40 + x + 16 * y)
            env.put(entity + 0x40, 0x100)
            if kind:
                record = env.object(0x40, name + "-class", fill=0)
                env.put(record + 0x10, kind)
                env.put(entity + 0x6C, record)
        node = env.object(0x20, name + "-node", fill=0)
        env.put(node, env.get(cells + 8 * cell))
        env.put(node + 0x10, x, y, entity)
        env.put(cells + 8 * cell, node)
    return grid


def play_state(random_source, **fields):
    """A Level 1 Play state object with random non-zero contents and the controlled fields overwritten.
    All random draws happen here, so every run of the setup builds the same memory."""
    filler = word_bytes(random_source, 0x800)
    values = {name: fields.get(name, base + random_source.randrange(1, 0xFFFF))
              for name, base in (("m768", 0x1000), ("m76c", 0x2000), ("m770", 0x3000), ("m34", 0x4D2))}
    text = fields.get("string")
    if text is not None:
        text = (text[0], text[1])

    def setup(env):
        default_scripted(env, fields.get("scripted"))
        this = env.object(0x800, "play-state", data=filler)
        env.put(this, fields.get("vtable", PLAY_VTABLE))
        if fields.get("owner") is not None:
            owner = env.object(0x200, "owner", fill=0)
            env.put(owner + 0x50, env.object(0x100, "owner-50", fill=0))
            env.put(owner + 0x5C, env.object(0x100, "owner-5c", fill=0))
            env.put(owner + 0xC0, cstring(env, fields["owner"][0], fields["owner"][1]))
            env.put(this + 0x04, owner)
        else:
            env.put(this + 0x04, 0)
        env.put(this + 0x0C, 0)
        env.put(this + 0x768, values["m768"])
        env.put(this + 0x76C, values["m76c"])
        env.put(this + 0x770, values["m770"])
        env.put(this + 0x774, fields.get("m774", 0))
        env.put(this + 0x34, values["m34"])
        env.put(this + 0x250, cstring(env, text[0], text[1]) if text else EMPTY_STRING_GLOBAL)
        tokens = {"this": this}
        if fields.get("extra"):
            fields["extra"](env, this, tokens)
        return tokens
    return setup



def table(env, name, slots, size=0x100):
    """A vtable-like object: slots maps an offset to (convention, argc, effect)."""
    address = env.object(size, name, fill=0)
    for offset, (convention, argc, effect) in slots.items():
        env.put(address + offset, env.stub(f"{name}+{offset:#x}", convention, argc, effect))
    return address


def hash_of(text):
    value = 0
    for byte in text:
        value = (value * 33 + byte) & 0xFFFFFFFF
    return value


SCENE_DEFAULTS = {
    "geometry": (640, 480, 640, 480), "bpp": 0, "z30": 0, "a_present": True, "surface_lock": returns(0),
    "restore": returns(0), "set_entries": returns(0), "slot_a": returns(0), "slot_nn": None, "slot_q": returns(0),
    "flags": 0x20, "hashed": None, "full": False, "mode": (640, 480), "kind": returns(3), "level": 5, "registry_missing": (), "load_results": None,
    "cursor": None, "vslot": None, "z_c": 0, "pixels": (3, 8, 16),
}


def play_scene(random_source, **options):
    """A Play state wired to a display, palette, message frame and surfaces, all reached through stubs."""
    opt = dict(SCENE_DEFAULTS)
    opt.update(options)
    seed = random_source.randrange(1 << 32)
    timeline = opt.pop("timeline", (1000, 1100, 1300))
    scripted = dict(opt.pop("scripted", {}))
    scripted.setdefault(0x546DF0, sequence(*timeline))
    scripted.setdefault(0x5469E4, returns(0))

    def extra(env, this, tokens):
        rng = Random(seed)
        z = env.object(0x100, "display", fill=0)
        env.put(z + 0x30, opt["z30"])
        env.put(z + 0x78, opt["bpp"])
        env.put(z + 0x7C, *opt["geometry"])
        env.put(this + 4, z)

        entries = env.object(0x400, "palette-entries", data=word_bytes(rng, 0x400))
        backup = env.object(0x400, "palette-backup", data=word_bytes(rng, 0x400))
        pattern = word_bytes(rng, 0x400)

        def get_entries(env, call):
            env.write(call.arguments[4], pattern)
            return 0

        palette_com = env.object(4, "palette-com", fill=0)
        env.put(palette_com, table(env, "palette-methods", {0x10: ("stdcall", 5, get_entries),
                                                           0x18: ("stdcall", 5, opt["set_entries"])}))
        palette = env.object(0x40, "palette", fill=0)
        env.put(palette + 4, palette_com)
        env.put(palette + 0xC, entries)
        env.put(palette + 0x10, backup)
        owner = env.object(0x80, "palette-owner", fill=0)
        env.put(owner, table(env, "palette-owner-methods", {0x34: ("thiscall", 0, opt["slot_a"])}))
        env.put(owner + 0x10, palette)
        env.put(this + 0x2C, owner if opt["a_present"] else 0)

        frame = env.object(0x40, "frame", fill=0)
        env.put(this + 0xC, frame)
        shared = env.object(0x40, "frame-shared", fill=0)
        surface_com = env.object(4, "surface-com", fill=0)
        env.put(surface_com, table(env, "surface-methods", {0x2C: ("stdcall", 3, opt["surface_lock"]),
                                                            0x60: ("stdcall", 1, opt.get("is_lost", returns(0))),
                                                            0x6C: ("stdcall", 1, opt.get("is_busy", returns(0)))}))
        surface = env.object(0x40, "surface", fill=0)
        env.put(surface, table(env, "surface-owner-methods", {0x1C: ("thiscall", 0, opt["restore"])}))
        env.put(surface + 8, surface_com)
        primary = env.object(0x40, "primary", fill=0)
        env.put(primary + 0x2C, surface)
        back_surface = env.object(0x40, "back-surface", fill=0)
        back_com = env.object(4, "back-com", fill=0)
        env.put(back_com, table(env, "back-methods", {0x14: ("stdcall", 6, opt.get("blit", returns(0))),
                                                      0x64: ("stdcall", 5, returns(0)),
                                                      0x80: ("stdcall", 2, returns(0))}))
        env.put(back_surface + 8, back_com)
        rows, row_bytes, pitch = opt["pixels"]
        env.put(back_surface + 0x14, rows, row_bytes, pitch)
        env.put(back_surface + 0x30, env.object(max(rows * pitch, 4), "pixels", data=word_bytes(rng, max(rows * pitch, 4))))
        back = env.object(0x40, "back", fill=0)
        env.put(back + 0x2C, back_surface)
        extra_surface = env.object(0x40, "extra-surface", fill=0)
        extra_com = env.object(4, "extra-com", fill=0)
        env.put(extra_com, table(env, "extra-methods", {0x60: ("stdcall", 1, opt.get("is_lost2", returns(0))),
                                                        0x6C: ("stdcall", 1, opt.get("is_busy2", returns(0)))}))
        env.put(extra_surface + 8, extra_com)
        extra_holder = env.object(0x40, "extra", fill=0)
        env.put(extra_holder + 0x2C, extra_surface)
        env.put(shared + 0x10, primary)
        env.put(shared + 0x14, back)
        env.put(shared + 0x18, extra_holder)
        env.put(frame + 4, shared)

        # +8: the stand-in message frame; +0xc: the fade target; +0x18: the object that records the palette owner
        slot_nn = opt["nn_factory"](this) if opt.get("nn_factory") else opt["slot_nn"] or returns(0)
        fade = env.object(0x40, "fade-target", fill=0)
        env.put(fade, table(env, "fade-target-methods", {0x34: ("thiscall", 2, slot_nn)}))
        env.put(frame + 0xC, fade)
        env.put(frame + 0x18, env.object(0x80, "recorder", fill=0))

        hashed = opt["hashed"]
        buckets = 31
        map_owner = env.object(0x40, "map-owner", fill=0)
        env.put(map_owner + 0x10 + 8, buckets)
        if hashed is not None:
            key = b"SingleFrameMessage\0"
            entry = env.object(0x10, "map-entry", fill=0)
            env.put(entry + 4, hash_of(key[:-1]))
            env.put(entry + 8, cstring(env, key[:-1], 1))
            descriptor = env.object(0x40, "frame-descriptor", fill=0)
            env.put(descriptor + 8, opt.get("descriptor_flags", 0x1357))
            env.put(descriptor + 0x10, env.stub("frame-factory", "cdecl", 1, opt.get("factory", returns(0x24680))))
            env.put(entry + 0xC, descriptor)
            slots = env.object(buckets * 4, "map-buckets", fill=0)
            env.put(slots + 4 * (hash_of(key[:-1]) % buckets), entry)
            env.put(map_owner + 0x10 + 4, slots)
        runtime = env.object(0x40, "runtime", fill=0)
        env.put(runtime + 0x14, map_owner)
        message = env.object(0x80, "message-frame", fill=0)
        env.put(message, table(env, "message-frame-methods", {0x28: ("thiscall", 1, opt["slot_q"])}))
        env.put(message + 0xC, runtime)
        env.put(message + 0x10 + 0x18, 10)  # the pointer list's block size
        env.put(frame + 8, message)

        layers = env.object(0x80, "layers", fill=0)
        env.put(layers + 8, opt["flags"])
        env.put(layers + 0x60, 0xFFFFFFFF)
        env.put(frame + 0x24, layers)

        if opt["full"]:
            zz = env.object(0x80, "display-surfaces", fill=0)
            env.put(zz + 4, shared)
            env.put(zz + 0x24, env.object(0x100, "display-layers", fill=0))
            env.put(primary + 0x10, *opt["mode"])
            kind_owner = env.object(0x20, "display-kind", fill=0)
            env.put(kind_owner, table(env, "display-kind-methods", {0x10: ("thiscall", 0, opt["kind"])}))
            env.put(z + 0x2C, kind_owner)
            env.put(z + 0x30, zz)
            env.put(z + 0x68, opt["level"])
            env.put(z + 0xC, opt["z_c"])
            env.put(0x5371FC, z)
            holder = env.object(0x240, "device-settings", fill=0)
            env.put(holder + 0x20C, 0x11, 0x22, 0x33)
            env.put(holder + 0x1CC, 0)
            globalobj = env.object(0x80, "device-global", data=word_bytes(rng, 0x80))
            env.put(globalobj, holder)
            env.put(0x537204, globalobj)
            names = {"tiles": (0x1C, b"TILES"), "images2": (0x28, b"IMAGES"), "images3": (0x24, b"IMAGES"),
                     "images1": (0x1C, b"IMAGES")}
            registries = {}
            for key, (offset, name) in names.items():
                if offset not in registries:
                    registries[offset] = (env.object(0x60, "registry", fill=0), env.object(5 * 16 + 8, "registry-buckets", fill=0), {})
                reg, buckets_array, used = registries[offset]
                env.put(reg + 0x40, buckets_array)
                env.put(this + offset, reg)
                if key in opt["registry_missing"]:
                    continue
                label = cstring(env, name, 1)
                entry = env.object(0x20, "registry-entry", fill=0)
                env.put(entry, label)
                node = env.object(0x20, "registry-node", fill=0)
                env.put(node + 0x14, entry)
                env.put(buckets_array + 16 * (len(name) % 5) + 8, node + 4)
            loader = env.object(0x40, "loader", fill=0)
            env.put(loader, table(env, "loader-methods", {0x4C: ("thiscall", 3, opt["load_results"] or returns(0))}))
            env.put(frame + 0x10, loader)
            if opt["cursor"] is not None:
                env.override(0x546D54, opt["cursor"])
            if opt["vslot"] is not None:
                vt = env.object(0x100, "play-vtable", data=env.read(PLAY_VTABLE, 0x100))
                env.put(vt + 0x4C, env.stub("play-vtable+0x4c", "thiscall", 0, opt["vslot"]))
                env.put(this, vt)
        tokens.update({"display": z, "owner": owner})

    return play_state(random_source, extra=extra, scripted=scripted, **{k: v for k, v in options.items()
                                                                       if k in ("m34",)})


def cases(random_source):
    # 0x429470: stdcall, returns zero whatever the argument
    for value in (0, 1, 0xFFFFFFFF, 0x80000000, random_source.randrange(1, 1 << 32)):
        yield Case(f"zero stub arg {value:#x}", F_RET0, arguments=(value,))

    def this_of(tokens):
        return tokens["this"]

    strings = [None, (b"", 1), (b"level one", 1), (b"x" * 33, 5), (word_bytes(random_source, 9), 2)]
    # 0x4294a0 / 0x429480 / 0x40af60 / 0x46a870 over the string and handle variants
    for index, text in enumerate(strings):
        for handle in (0, 0x70001234 + random_source.randrange(0, 0xFFFF)):
            tag = f"string {index} handle {'set' if handle else 'clear'}"
            yield Case("destructor " + tag, F_DTOR, play_state(random_source, string=text, m774=handle), receiver=this_of)
            yield Case("clear " + tag, F_CLEAR, play_state(random_source, string=text, m774=handle), receiver=this_of)
            for flags in (0, 1, 2, 3, 0xFFFFFFFE, random_source.randrange(0, 1 << 32)):
                yield Case(f"deleting destructor flags {flags:#x} {tag}", F_DTOR_DEL,
                           play_state(random_source, string=text, m774=handle), receiver=this_of, arguments=(flags,))
    for flags in (0, 1, 2, 3, 0xFFFFFFFE, 0x80000001, random_source.randrange(0, 1 << 32)):
        yield Case(f"base destructor flags {flags:#x}", F_BASE_DEL, play_state(random_source), receiver=this_of,
                   arguments=(flags,))
    for owner in ((b"", 1), (b"owner text", 1), (b"shared owner", 3), (word_bytes(random_source, 20), 1)):
        yield Case(f"clear with owner string {owner[0][:4]!r} refs {owner[1]}", F_CLEAR,
                   play_state(random_source, owner=owner, string=(b"s", 1), m774=0x7777), receiver=this_of)

    # 0x46a840: copy-construct the CString at +0xc0 into the caller's holder
    def with_copy_source(refs, text, holder_word):
        def extra(env, this, tokens):
            env.put(this + 0xC0, cstring(env, text, refs))
            tokens["holder"] = env.object(8, "holder", words=[holder_word, 0x99999999])
        return play_state(random_source, extra=extra, scripted={0x5469E4: returns(len(text))})

    for refs, text in ((1, b"copy me"), (0, b"zero refs"), (7, b"shared text" * 3), (0x7FFFFFFF, b"max"),
                       (-1, b"locked text"), (-2, b"")):
        yield Case(f"copy string refs {refs}", F_COPY_STR, with_copy_source(refs, text, (0xDEAD0000 + refs) & 0xFFFFFFFF),
                   receiver=this_of, arguments=(lambda tokens: tokens["holder"],))

    # 0x46ef80: mark every list entry whose flags carry 0x2000 with 0x10000, then walk the chain to the walker
    def with_world(nodes, chain, b_override=None, a_present=True, x_present=True, grids=None):
        """nodes: list of (flags164, flags8) or None for a node without an object.
        chain: how deep the +0x24 / +0x5c / +0xb0 chain goes (0 to 3)."""
        fills = [word_bytes(random_source, 0x180) for _ in range(len(nodes) + 4)]

        def extra(env, this, tokens):
            if not a_present:
                env.put(this + 0x0C, 0)
                return
            a = env.object(0x40, "world", data=fills[0][:0x40])
            env.put(this + 0x0C, a)
            if b_override is not None:
                env.put(a + 8, b_override)
            else:
                b = env.object(0x40, "world-list", data=fills[1][:0x40])
                env.put(a + 8, b)
                head = 0
                objects = []
                for position, entry in reversed(list(enumerate(nodes))):
                    obj = 0
                    if entry is not None:
                        obj = env.object(0x180, "entity", data=fills[4 + position])
                        env.put(obj + 8, entry[1])
                        env.put(obj + 0x164, entry[0])
                        objects.append(obj)
                    node = env.object(12, "node", words=[head, 0x55555555, obj])
                    head = node
                env.put(b + 0x10 + 4, head)
                tokens["entities"] = objects
            x = 0
            if chain >= 1 and x_present:
                x = env.object(0x80, "x", data=fills[2][:0x80])
                y = 0
                if chain >= 2:
                    y = env.object(0xC0, "y", data=fills[3][:0xC0])
                    z = 0
                    if chain >= 3:
                        z = env.object(0x20, "z", fill=0)
                        env.put(z + 4, walker_grid(env, "z4", grids[0]) if grids else empty_grid(env, "z4"))
                        env.put(z + 8, walker_grid(env, "z8", grids[1]) if grids else empty_grid(env, "z8"))
                        env.put(z + 0xC, walker_grid(env, "z12", grids[2]) if grids else empty_grid(env, "z12"))
                    env.put(y + 0xB0, z)
                env.put(x + 0x5C, y)
            env.put(a + 0x24, x)
        return play_state(random_source, extra=extra)

    flag_pool = [0x2000, 0, 0xFFFFDFFF, 0xFFFFFFFF, 0x4000, 0x2001, 0x1FFF]
    yield Case("flags: no world", F_FLAGS, with_world([], 0, a_present=False), receiver=this_of)
    yield Case("flags: list base wraps to zero", F_FLAGS, with_world([], 0, b_override=0xFFFFFFF0), receiver=this_of)
    yield Case("flags: empty list, no chain", F_FLAGS, with_world([], 0), receiver=this_of)
    for chain in (0, 1, 2, 3):
        yield Case(f"flags: three entries chain {chain}", F_FLAGS,
                   with_world([(0x2000, 0x10), (0x1000, 0x20), None, (0x2000 | 0x80, 0x40000000)], chain), receiver=this_of)
    for round_index in range(6):
        entries = []
        for _ in range(random_source.randrange(1, 7)):
            if random_source.randrange(0, 6) == 0:
                entries.append(None)
            else:
                entries.append((random_source.choice(flag_pool) | (random_source.randrange(0, 1 << 32) & 0xFFFF0000),
                                random_source.randrange(0, 1 << 32)))
        yield Case(f"flags: random world {round_index}", F_FLAGS, with_world(entries, random_source.randrange(0, 4)),
                   receiver=this_of)

    # 0x48fcf0: draw text through the surface's device context
    def with_surface(hdc, chain=4, release_result=0):
        """chain: 0 no +0xc object, 1 no +4, 2 no +0x2c, 4 complete."""
        seed = random_source.randrange(1 << 32)
        def extra(env, this, tokens):
            rng = Random(seed)
            if chain < 1:
                env.put(this + 0x0C, 0)
                return
            a = env.object(0x20, "a", data=word_bytes(rng, 0x20))
            env.put(this + 0x0C, a)
            b = env.object(0x20, "b", data=word_bytes(rng, 0x20)) if chain >= 2 else 0
            env.put(a + 4, b)
            if not b:
                return
            c = env.object(0x40, "c", data=word_bytes(rng, 0x40))
            env.put(b + 0x10, c)
            e = env.object(0x20, "e", data=word_bytes(rng, 0x20)) if chain >= 3 else 0
            env.put(c + 0x2C, e)
            if not e:
                return
            d = env.object(8, "d")
            table = env.object(0x80, "d-table", data=word_bytes(rng, 0x80))
            env.put(e + 8, d)
            env.put(d, table)

            def get_dc(env, call):
                env.put(call.arguments[1], hdc)
                return 0

            env.put(table + 0x44, env.stub("GetDC", "stdcall", 2, get_dc))
            env.put(table + 0x68, env.stub("ReleaseDC", "stdcall", 2, returns(release_result)))
        return play_state(random_source, extra=extra, scripted={SET_BK_MODE: returns(0x1234), SET_TEXT_COLOR: returns(0x5678),
                                                                 0x5469E4: returns(0)})

    def text_case(label, text_value, hdc, chain=4, **options):
        surface = with_surface(hdc, chain)

        def setup(env):
            tokens = surface(env)
            tokens["text"] = env.object(len(text_value) + 4, "text", data=text_value + b"\0\0\0\0")
            return tokens

        return Case(label, F_TEXTOUT, setup, receiver=this_of,
                    arguments=(options.get("x", 0x11), options.get("y", 0x22), lambda tokens: tokens["text"],
                               options.get("color", 0x00A1B2C3), options.get("mode", 2)))

    yield text_case("text out draws", b"Level One", 0xABCD1234)
    yield text_case("text out empty string", b"", 0xABCD1235, x=0, y=0, color=0, mode=0)
    for _ in range(4):
        text_value = word_bytes(random_source, random_source.randrange(1, 70)).replace(b"\0", b"a")
        yield text_case("text out random", text_value, random_source.randrange(1, 1 << 32),
                        x=random_source.randrange(0, 1 << 32), y=random_source.randrange(0, 1 << 32),
                        color=random_source.randrange(0, 1 << 32), mode=random_source.randrange(0, 1 << 32))
    yield text_case("text out no device context", b"nodc", 0)
    yield text_case("text out no surface object", b"chain", 0x777, chain=2)
    yield Case("text out null text", F_TEXTOUT, with_surface(0x555), receiver=this_of, arguments=(1, 2, 0, 3, 4))

    # 0x46ca50: advance the message list's timers, then draw its first line into the window rectangle
    def with_messages(count, line, timer_state, globals_values, tag, font=0, select=None):
        seed = random_source.randrange(1 << 32)
        """timer_state: (+0x2c elapsed, +0x30 active, +0x20 age, +0x24 limit, +0x28 limit)."""
        def extra(env, this, tokens):
            rng = Random(seed)
            owner = env.object(0x80, "owner", data=word_bytes(rng, 0x80))
            env.put(this + 4, owner)
            t = env.object(0x80, "messages", fill=0)
            env.put(owner + 0x4C, t)
            env.put(t + 0x0C, count)
            env.put(t + 0x2C, timer_state[0])
            env.put(t + 0x30, timer_state[1])
            env.put(t + 0x20, timer_state[2])
            env.put(t + 0x24, timer_state[3])
            env.put(t + 0x28, timer_state[4])
            env.put(t + 0x1C, EMPTY_STRING_GLOBAL)
            env.put(t + 0x34, font)
            if line is not None:
                node = env.object(12, "message", words=[0, 0, cstring(env, line, 1)])
                env.put(t + 4, node)
            for address, value in zip((0x53720C, 0x5370C8, 0x5370CC, 0x5370D0), globals_values):
                env.put(address, value)
            tokens["messages"] = t
        return play_state(random_source, extra=extra,
                          scripted={0x5469E4: returns(len(line or b"")), 0x54691C: select or returns(0x5151)})

    for count, line in ((1, b"Welcome"), (2, b"two lines"), (3, b"x" * 90), (1, b""), (2, None), (0, b"hidden"), (-1, b"neg")):
        gvals = [random_source.randrange(1, 40) for _ in range(1)] + [random_source.randrange(1, 1 << 30) for _ in range(3)]
        yield Case(f"messages count {count} line {line!r}"[:60], F_TEXT,
                   with_messages(count, line, (5, 0, 7, 0x100000, 0x100000), gvals, "a"), receiver=this_of,
                   arguments=(random_source.randrange(1, 1 << 32),))
    for elapsed, active in ((1, 1), (0x2700, 1), (0x2710, 1), (0xFFFFF000, 1), (0x2711, 0)):
        gvals = [random_source.randrange(1, 40)] + [random_source.randrange(1, 1 << 30) for _ in range(3)]
        yield Case(f"messages timer {elapsed:#x} active {active}", F_TEXT,
                   with_messages(2, b"timed", (elapsed, active, 3, 0x100000, 0x100000), gvals, "b"), receiver=this_of,
                   arguments=(0x1000 + elapsed,))
    yield Case("messages null device context", F_TEXT,
               with_messages(2, b"nodc", (5, 0, 7, 0x100000, 0x100000), [3, 70, 80, 90], "c"), receiver=this_of, arguments=(0,))

    # 0x46b8f0: only the early exit is reachable. Past it the original calls ShowCursor (0x546d54), which the
    # specification does not declare, so a case that gets that far stops with a harness error.
    one = returns(1)
    for label, options in (
            ("primary surface lost and busy", {"is_lost": one, "is_busy": one}),
            ("primary surface lost and busy, extra clean", {"is_lost": one, "is_busy": one, "is_lost2": one}),
            ("extra surface lost and busy", {"is_lost2": one, "is_busy2": one}),
            ("both surfaces lost and busy", {"is_lost": one, "is_busy": one, "is_lost2": one, "is_busy2": one}),
            ):
        yield Case("load: " + label, F_LOAD, play_scene(random_source, **options), receiver=this_of)

    # 0x46ba80: bring the scene back and fade the palette in
    def zero_owner_slot(this):
        def effect(env, call):
            env.put(this + 0x2C, 0)
            return 0
        return effect

    yield Case("prepare: full path", F_PREP, play_scene(random_source), receiver=this_of)
    yield Case("prepare: not ready", F_PREP, play_scene(random_source, m34=0), receiver=this_of)
    yield Case("prepare: no palette owner", F_PREP, play_scene(random_source, a_present=False), receiver=this_of)
    yield Case("prepare: owner vanishes during the call", F_PREP, play_scene(random_source, nn_factory=zero_owner_slot),
               receiver=this_of)
    for index, geometry in enumerate(((640, 480, 800, 600), (640, 480, 640, 600), (640, 480, 800, 480), (640, 480, 641, 481))):
        yield Case(f"prepare: display mode differs {index}", F_PREP, play_scene(random_source, geometry=geometry),
                   receiver=this_of)
    yield Case("prepare: surface lost then restored", F_PREP,
               play_scene(random_source, surface_lock=sequence(0x887601C2, 0), restore=returns(1)), receiver=this_of)
    yield Case("prepare: surface lost, restore refused", F_PREP,
               play_scene(random_source, surface_lock=returns(0x887601C2), restore=returns(0)), receiver=this_of)
    yield Case("prepare: fast timer", F_PREP, play_scene(random_source, timeline=(5000, 5300)), receiver=this_of)

    # 0x46bc00: build the message frame and fade
    yield Case("rebuild: no registered frame", F_DRAW_SETUP, play_scene(random_source), receiver=this_of)
    yield Case("rebuild: surface lost then restored", F_DRAW_SETUP,
               play_scene(random_source, surface_lock=sequence(0x887601C2, 0), restore=returns(1)), receiver=this_of)
    for flags, bpp, pixels in ((1, 0, (3, 8, 16)), (2, 16, (3, 8, 16)), (0, 8, (4, 12, 12)), (3, 16, (1, 4, 8)),
                               (1, 8, (2, 8, 12)), (2, 32, (2, 8, 8))):
        yield Case(f"rebuild: frame found flags {flags} depth {bpp}", F_DRAW_SETUP,
                   play_scene(random_source, hashed=1, descriptor_flags=flags, bpp=bpp, pixels=pixels), receiver=this_of)
    yield Case("rebuild: factory callback result ignored", F_DRAW_SETUP,
               play_scene(random_source, hashed=1, bpp=16, factory=returns(0)), receiver=this_of)
    for font, select in ((0x6001, returns(0x5151)), (0x6002, returns(0)), (0x6003, sequence(0x7001, 0x7002))):
        yield Case(f"messages font {font:#x}", F_TEXT,
                   with_messages(2, b"fonted", (5, 0, 7, 0x100000, 0x100000), [3, 70, 80, 90], "d", font=font, select=select),
                   receiver=this_of, arguments=(0xABC000 + font,))
    yield Case("messages font without lines", F_TEXT,
               with_messages(0, b"none", (5, 0, 7, 0x100000, 0x100000), [3, 70, 80, 90], "e", font=0x6004),
               receiver=this_of, arguments=(0xABC123,))

    # 0x46b8f0 in full: every early exit and the complete load
    cursor_a, cursor_b = returns(-1 & 0xFFFFFFFF), sequence(2, 1, 0, -1 & 0xFFFFFFFF)
    for label, options in (
            ("registry TILES missing", {"registry_missing": ("tiles",)}),
            ("first load fails", {"load_results": sequence(0xFFFFFFFF)}),
            ("registry IMAGES (+0x28) missing", {"registry_missing": ("images2",)}),
            ("second load fails", {"load_results": sequence(0, 0xFFFFFFFF)}),
            ("registry IMAGES (+0x24) missing", {"registry_missing": ("images3",)}),
            ("third load fails", {"load_results": sequence(0, 0, 0xFFFFFFFF)}),
            ("registry IMAGES (+0x1c) missing", {"registry_missing": ("images1",)}),
            ("fourth load fails", {"load_results": sequence(0, 0, 0, 0xFFFFFFFF)}),
            ):
        yield Case("load: " + label, F_LOAD, play_scene(random_source, full=True, cursor=cursor_b, **options),
                   receiver=this_of)
    cursor_c = sequence(2, 0xFFFFFFFF, 3, 0, 0xFFFFFFFF)
    for cursor in (cursor_a, cursor_b, cursor_c):
        for level in (0, 5, 10, 12):
            for z_c, vslot in ((0, None), (0x1234, None), (0x1234, returns(0)), (0x1234, returns(1))):
                yield Case(f"load: complete level {level} frame {z_c:#x}", F_LOAD,
                           play_scene(random_source, full=True, cursor=cursor, level=level, z_c=z_c, vslot=vslot),
                           receiver=this_of)

    # 0x42a060 succeeds when the display already runs in the requested mode
    for index, (geometry, kind) in enumerate((((640, 480, 800, 600), returns(3)), ((640, 480, 800, 600), returns(4)),
                                               ((640, 480, 800, 600), returns(5)), ((320, 240, 640, 480), returns(3)),
                                               ((640, 480, 640, 600), returns(4)), ((640, 480, 800, 480), returns(5)))):
        yield Case(f"prepare: display mode change accepted {index}", F_PREP,
                   play_scene(random_source, full=True, geometry=geometry, mode=geometry[2:], kind=kind, cursor=returns(0xFFFFFFFF),
                              timeline=(1000, 1010, 1020, 1100, 1400)),
                   receiver=this_of)

    # 0x46ef80: the walker calls the callback for every entity found in the three grids
    classes = (0x461970, 0x4618E0, 0x461770, 0x4617D0, 0x461771, 0x4619, 0)
    for index in range(4):
        grids = []
        for _ in range(3):
            items = []
            for _ in range(random_source.randrange(0, 5)):
                kind = random_source.choice(classes + (None,))
                items.append((random_source.randrange(0, 4), random_source.randrange(0, 2), random_source.randrange(0, 2), kind))
            grids.append(items)
        yield Case(f"flags: walker random {index}", F_FLAGS,
                   with_world([(0x2000, 0x10), (0x1000, 0x20)], 3, grids=grids), receiver=this_of)
    every = [[(cell, cell % 2, cell // 2, kind) for cell, kind in enumerate((0x461970, 0x4618E0, 0x461770, 0x4617D0))],
             [(0, 0, 0, None), (3, 1, 1, 0), (3, 0, 1, 0x461771)], [(1, 1, 0, 0x4617D0), (1, 1, 0, 0x4618E0)]]
    yield Case("flags: walker every class", F_FLAGS, with_world([(0x2000, 0x10)], 3, grids=every), receiver=this_of)
