"""Cases for pause_menu_widgets: Level 1 in-game pause menu: IFC widget callback 0x4529f0 and widget name lookup 0x4508d0."""
from clawparity.cases import Case

WIDGET_CALLBACK = 0x4529F0
NAME_LOOKUP = 0x4508D0

LSTRLEN = 0x5469E4
INTERLOCKED_DECREMENT = 0x5469E8
INTERLOCKED_INCREMENT = 0x5469EC

MENU_GLOBAL = 0x53789C
UI_GLOBAL = 0x5371FC
NIL_STRING_GLOBAL = 0x52E1C8  # holds the address of the shared empty-string header

SET_NAMES = {
    "main": b"GAME_INGAMEMENU_MAIN",
    "clawicide": b"GAME_INGAMEMENU_MAIN_CLAWICIDE",
    "options": b"GAME_INGAMEMENU_MAIN_OPTIONS",
    "audio": b"GAME_INGAMEMENU_MAIN_OPTIONS_AUDIO",
    "display": b"GAME_INGAMEMENU_MAIN_OPTIONS_DISPLAY",
    "endgame": b"GAME_INGAMEMENU_MAIN_ENDGAME",
}

# application offsets read by 0x4508d0
FLAG_OFFSETS = {"sound": 0x10, "music": 0x14, "voice": 0x118, "ambient": 0x11C, "front": 0x128, "movies": 0x120}


# ---- fixture effects -----------------------------------------------------------------------------

def interlocked(delta):
    def effect(env, call):
        pointer = call.arguments[0]
        value = (env.get(pointer) + delta) & 0xFFFFFFFF
        env.put(pointer, value)
        return value
    return effect


def string_length(env, call):
    return len(env.cstr(call.arguments[0], limit=4096))


def string_length_zero(env, call):
    return 0


def install(env, length=string_length):
    env.override(LSTRLEN, length)
    env.override(INTERLOCKED_DECREMENT, interlocked(-1))
    env.override(INTERLOCKED_INCREMENT, interlocked(1))
    empty = env.object(16, "shared-empty-header", words=[0xFFFFFFFF, 0, 0, 0])
    env.put(NIL_STRING_GLOBAL, empty)
    env.put(NIL_STRING_GLOBAL + 4, empty + 0xC)  # the empty CString object the default constructor copies


# ---- object builders -----------------------------------------------------------------------------

def hash_of(text):
    value = 0
    for byte in text:
        value = (value * 0x21 + (byte - 256 if byte >= 128 else byte)) & 0xFFFFFFFF
    return value


def cstring(env, text, refs=1, capacity=None):
    """An MFC string: a three word header (references, length, capacity), then the characters."""
    capacity = len(text) if capacity is None else capacity
    block = env.object(0x10 + capacity + 1, "cstring", fill=0)
    env.put(block, refs, len(text), capacity)
    env.write(block + 0xC, text + b"\0")
    return block + 0xC


def nil_string(env):
    return env.get(NIL_STRING_GLOBAL) + 0xC


def noise(random_source, count):
    return [random_source.randrange(0x100, 0x7FFF0000) for _ in range(count)]


def make_map(env, base, entries, buckets):
    """The string-to-value hash map the original reads: table at +4, bucket count at +8."""
    env.put(base + 8, buckets)
    slots = env.object(4 * buckets, "buckets", fill=0)
    for key, value in entries:
        key_block = env.object(len(key) + 1, "map-key", data=key + b"\0")
        slot = hash_of(key) % buckets
        node = env.object(16, "assoc", words=[env.get(slots + 4 * slot), hash_of(key), key_block, value])
        env.put(slots + 4 * slot, node)
    env.put(base + 4, slots)


def application(env, random_source, flags):
    """The application object [menu+4]: noise everywhere, then the six flags the lookup reads."""
    app = env.object(0x140, "application", words=noise(random_source, 0x50))
    for name, offset in FLAG_OFFSETS.items():
        env.put(app + offset, flags.get(name, 0))
    return app


def menu_object(env, random_source, flags):
    app = application(env, random_source, flags)
    words = noise(random_source, 8)
    words[1] = app
    return env.object(0x20, "menu", words=words), app


def lookup_case(label, random_source, text, flags=None, refs=1, dest="nil", dest_refs=1, preset=None,
                length=string_length):
    """One call of 0x4508d0 on a CString argument."""
    flags = flags or {}
    preset = random_source.randrange(0x1000, 0x7FFFF000) if preset is None else preset

    def setup(env):
        install(env, length)
        menu, app = menu_object(env, random_source, flags)
        argument = cstring(env, text, refs=refs)
        out = env.object(4, "index", words=[preset])
        if dest == "nil":
            held = nil_string(env)
        elif dest == "own":
            held = cstring(env, b"OLD-DESTINATION-NAME-WITH-ROOM", refs=dest_refs, capacity=64)
        elif dest == "shared":
            held = cstring(env, b"OLD", refs=dest_refs, capacity=3)
        else:
            held = cstring(env, b"", refs=dest_refs, capacity=40)
        name = env.object(4, "name-slot", words=[held])
        return {"menu": menu, "argument": argument, "out": out, "name": name, "app": app}

    return Case(label, NAME_LOOKUP, setup, receiver=lambda t: t["menu"],
                arguments=(lambda t: t["argument"], lambda t: t["name"], lambda t: t["out"]))


def widget_world(env, random_source, flags, sets, buckets, decoys=True, null_names=()):
    """Everything 0x4529f0 reads: menu global, application global, name map, image sets and frames."""
    menu, app = menu_object(env, random_source, flags)
    env.put(MENU_GLOBAL, menu)
    ui = env.object(0x60, "ui", words=noise(random_source, 0x18))
    holder = env.object(0x40, "ui-holder", words=noise(random_source, 0x10))
    owner = env.object(0x40, "map-owner", words=noise(random_source, 0x10))
    env.put(UI_GLOBAL, ui)
    env.put(ui + 0x30, holder)
    env.put(holder + 0x10, owner)
    entries = []
    if decoys:
        entries += [(b"GAME_INGAMEMENU_MAI", 0x7001), (b"GAME_INGAMEMENU_MAIN_", 0x7002), (b"game_ingamemenu_main", 0x7003)]
    results = {}
    for key, spec in sets.items():
        name = SET_NAMES[key]
        if spec is None:
            entries.append((name, 0))
            continue
        low, high, frames = spec
        array = env.object(4 * max(high + 1, 1) + 8, "frame-array", words=noise(random_source, max(high + 1, 1) + 2))
        for index, frame_value in frames.items():
            if frame_value is None:
                env.put(array + 4 * index, 0)
            else:
                frame = env.object(0x40, "frame", words=noise(random_source, 16))
                env.put(frame + 0x2C, frame_value)
                env.put(array + 4 * index, frame)
        image_set = env.object(0x80, "image-set", words=noise(random_source, 0x20))
        env.put(image_set + 0x14, array)
        env.put(image_set + 0x64, low, high)
        entries.append((name, image_set))
        results[key] = image_set
    random_source.shuffle(entries)
    make_map(env, owner + 0x10, entries, buckets)
    return {"menu": menu, "app": app, "ui": ui}


def widget_case(label, random_source, text, sets, buckets=7, flags=None, refs=1, length=string_length, decoys=True):
    def setup(env):
        install(env, length)
        tokens = widget_world(env, random_source, flags or {}, sets, buckets, decoys)
        tokens["argument"] = cstring(env, text, refs=refs)
        return tokens

    return Case(label, WIDGET_CALLBACK, setup, arguments=(lambda t: t["argument"],))


def frames_for(random_source, low, high, null_at=()):
    """A frame table with a distinct non-zero value in +0x2c of every frame, 0 at the given indexes."""
    return {index: (None if index in null_at else random_source.randrange(0x100, 0x7FFFFFF0))
            for index in range(max(low, 0), high + 1)}


# ---- cases ---------------------------------------------------------------------------------------

def flag_sets(random_source, names, count=None):
    """Every on/off combination of the named flags, with a distinct non-zero value for "on"."""
    combos = []
    for bits in range(1 << len(names)):
        combos.append({name: (random_source.randrange(2, 0xFFFFFFF0) if bits >> i & 1 else 0)
                       for i, name in enumerate(names)})
    if count is not None:
        random_source.shuffle(combos)
        combos = combos[:count]
    return combos


NUMBERS = [b"0", b"7", b"-3", b"  9", b"2147483648", b"12abc"]
IMPORTANT = [b"31", b"36"]


def lookup_cases(random_source):
    plain = [b"main", b"clawicide", b"options", b"optionsaudio", b"optionsdisplay", b"endgame"]
    for number in NUMBERS:
        for token in plain:
            text = number + b"_" + token + b"_"
            yield lookup_case(f"{token} after {number!r}", random_source, text)
    yield lookup_case("bare _main_", random_source, b"_main_")
    yield lookup_case("upper case is folded", random_source, b"12_MAIN_")
    yield lookup_case("mixed case clawicide", random_source, b"5_ClawIcide_")
    yield lookup_case("mixed case optionsaudio", random_source, b"9_OptionsAudio_Sound", flags={"sound": 5})
    yield lookup_case("mixed case optionsdisplay", random_source, b"9_OPTIONSDISPLAY_Front")
    yield lookup_case("mixed case endgame", random_source, b"9_EndGame_")
    # search order: the earlier test wins when several tokens are present
    ordered = [b"main", b"clawicide", b"options", b"optionsaudio", b"optionsdisplay", b"endgame"]
    for i, first in enumerate(ordered):
        for second in ordered[i + 1:]:
            yield lookup_case(f"{first} wins over {second}", random_source, b"21_" + first.join([b"_", b"_"]) + second.join([b"_", b"_"]))
    # no match
    for text in (b"", b"5_main", b"5main_", b"5_clawicide", b"5_option_", b"5_optionsaudi_", b"5_optionsdisplay",
                 b"5_end_game_"):
        yield lookup_case(f"no match {text!r}", random_source, text)
    for refs in (2, 0x7FFFFFFF):
        yield lookup_case(f"shared argument refs {refs}", random_source, b"8_options_", refs=refs)
    yield lookup_case("locked argument is copied by length", random_source, b"8_endgame_", refs=0xFFFFFFFF)
    yield lookup_case("locked argument, no match", random_source, b"8_nothing_", refs=0xFFFFFFFF)
    yield lookup_case("locked empty argument", random_source, b"", refs=0xFFFFFFFF)
    # destination string states
    for dest in ("nil", "own", "shared", "empty"):
        for dest_refs in (1, 2):
            if dest == "nil" and dest_refs == 2:
                continue
            for token in (b"main", b"optionsaudio"):
                yield lookup_case(f"destination {dest} refs {dest_refs} {token}", random_source,
                                  b"13_" + token + b"_", dest=dest, dest_refs=dest_refs)
    for dest in ("nil", "own", "shared"):
        yield lookup_case(f"destination {dest} kept when nothing matches", random_source, b"13_x_", dest=dest)
    # the audio sub-tests
    sub_texts = [b"", b"_sound", b"_music", b"_voice", b"_ambient", b"_sound_music", b"_ambient_voice_music_sound",
                 b"_music_sound", b"_front", b"_soundx", b"_Ambient"]
    for sub in sub_texts:
        for number in (b"13", b"-1", b"31", b"36"):
            flags = flag_sets(random_source, ["sound", "music", "voice", "ambient"], count=1)
            for flag_values in flags:
                label = ",".join(f"{k}={'on' if v else 'off'}" for k, v in flag_values.items())
                yield lookup_case(f"audio {number!r}{sub!r} {label}", random_source,
                                  number + b"_optionsaudio_" + sub, flags=flag_values)
    for sub in (b"_sound", b"_music", b"_voice", b"_ambient"):
        for flag_values in flag_sets(random_source, ["sound", "music", "voice", "ambient"], count=4):
            yield lookup_case(f"audio sub {sub!r} all flag combinations", random_source,
                              b"17_optionsaudio_" + sub + b"_", flags=flag_values)
    for number in (b"31", b"36"):
        for sub in (b"_sound", b"_music", b"_voice", b"_ambient"):
            yield lookup_case(f"audio {number!r} skips {sub!r}", random_source, number + b"_optionsaudio_" + sub)
    yield lookup_case("audio overflow wraps", random_source, b"2147483647_optionsaudio_sound")
    # the display sub-tests
    display_subs = [b"", b"_front", b"_movies", b"_front_movies", b"_Movies", b"_sound"]
    for sub in display_subs:
        for number in (b"13", b"-1"):
            for flag_values in flag_sets(random_source, ["front", "movies", "sound", "ambient"], count=2):
                label = ",".join(f"{k}={'on' if v else 'off'}" for k, v in flag_values.items())
                yield lookup_case(f"display {number!r}{sub!r} {label}", random_source,
                                  number + b"_optionsdisplay_" + sub, flags=flag_values)
    # flags are not consulted outside their branches
    for token in (b"main", b"clawicide", b"options", b"endgame"):
        for flag_values in flag_sets(random_source, ["sound", "music", "voice", "ambient", "front", "movies"], count=1):
            yield lookup_case(f"flags ignored for {token}", random_source,
                              b"4_" + token + b"_sound_music_voice_ambient_front_movies", flags=flag_values)
    # random strings
    alphabet = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"
    tokens = [b"_main_", b"_clawicide_", b"_options_", b"_optionsaudio_", b"_optionsdisplay_", b"_endgame_",
              b"_sound", b"_music", b"_voice", b"_ambient", b"_front", b"_movies"]
    for n in range(40):
        pieces = [bytes([alphabet[random_source.randrange(len(alphabet))] for _ in range(random_source.randrange(0, 6))])
                  for _ in range(random_source.randrange(1, 5))]
        chosen = [random_source.choice(tokens) for _ in range(random_source.randrange(0, 4))]
        parts = pieces + chosen
        random_source.shuffle(parts)
        text = str(random_source.randrange(-50, 200)).encode() + b"".join(parts)
        flag_values = flag_sets(random_source, list(FLAG_OFFSETS), count=1)[0]
        yield lookup_case(f"random {n}", random_source, text, flags=flag_values,
                          refs=random_source.choice([1, 1, 1, 2, 0xFFFFFFFF]),
                          dest=random_source.choice(["nil", "own", "shared", "empty"]),
                          dest_refs=random_source.choice([1, 2]))
    yield lookup_case("long argument", random_source, b"3" + b"x" * 300 + b"_optionsaudio_" + b"y" * 200 + b"_voice")


def widget_cases(random_source):
    def full_sets(low=1, high=40, null_at=()):
        sets = {}
        for key in SET_NAMES:
            sets[key] = (low, high, frames_for(random_source, low, high, null_at))
        return sets

    keyed = [("main", b"_main_"), ("clawicide", b"_clawicide_"), ("options", b"_options_"),
             ("audio", b"_optionsaudio_"), ("display", b"_optionsdisplay_"), ("endgame", b"_endgame_")]
    for key, token in keyed:
        for index in (1, 17, 40):
            for buckets in (1, 7):
                yield widget_case(f"{key} index {index} buckets {buckets}", random_source,
                                  str(index).encode() + token, full_sets(), buckets=buckets)
        yield widget_case(f"{key} is the only set present", random_source, b"12" + token,
                          {key: (1, 20, frames_for(random_source, 1, 20))})
        yield widget_case(f"{key} not in the map", random_source, b"12" + token, {}, buckets=5)
        yield widget_case(f"{key} maps to null", random_source, b"12" + token, {key: None})
        yield widget_case(f"{key} maps to null among other sets", random_source, b"12" + token,
                          dict(full_sets(), **{key: None}))
        yield widget_case(f"{key} shared argument", random_source, b"12" + token, full_sets(), refs=3)
        yield widget_case(f"{key} locked argument", random_source, b"12" + token, full_sets(), refs=0xFFFFFFFF)
    # index bounds
    for low, high in ((1, 10), (5, 5), (-4, 6)):
        frames = frames_for(random_source, low, high)
        for index in (low - 1, low, high, high + 1, 2):
            if index == 0:
                continue
            yield widget_case(f"bounds {low}..{high} index {index}", random_source, f"{index}_main_".encode(),
                              {"main": (low, high, frames)})
    for index in (0, -7, 2147483648):
        yield widget_case(f"index {index} not positive", random_source, f"{index}_clawicide_".encode(), full_sets())
    yield widget_case("no digits means index 0", random_source, b"_clawicide_", full_sets())
    yield widget_case("text before the digits means index 0", random_source, b"w9_clawicide_", full_sets())
    yield widget_case("index 2147483647 beyond the high bound", random_source, b"2147483647_options_", full_sets())
    # frames
    for null_at in ((5,), tuple(range(1, 41))):
        for index in (3, 5):
            yield widget_case(f"null frames {null_at[:3]} index {index}", random_source, f"{index}_endgame_".encode(),
                              full_sets(null_at=null_at))
    # no name match means the 0x4508d0 result is zero and the lookup is not attempted
    for text in (b"", b"3_main", b"3_nothing_", b"_"):
        yield widget_case(f"no pattern {text!r}", random_source, text, full_sets())
    # sub-patterns select the audio set; a flagged option moves the index by one
    for sub in (b"_sound", b"_music", b"_voice", b"_ambient"):
        for index in (5, 31, 36):
            for flag_values in flag_sets(random_source, ["sound", "music", "voice", "ambient"], count=1):
                yield widget_case(f"audio {index}{sub!r}", random_source, f"{index}_optionsaudio_".encode() + sub,
                                  full_sets(1, 45), flags=flag_values)
    for sub in (b"_front", b"_movies", b"_front_movies"):
        for flag_values in flag_sets(random_source, ["front", "movies"]):
            yield widget_case(f"display 7{sub!r}", random_source, b"7_optionsdisplay_" + sub, full_sets(1, 45),
                              flags=flag_values)
    # the index moved past the bounds by a flag
    for sub, flag in ((b"_sound", "sound"), (b"_music", "music"), (b"_voice", "voice"), (b"_ambient", "ambient")):
        yield widget_case(f"flag clear pushes index past high {flag}", random_source, b"10_optionsaudio_" + sub,
                          {"audio": (1, 10, frames_for(random_source, 1, 10))}, flags={})
        yield widget_case(f"flag set keeps index at high {flag}", random_source, b"10_optionsaudio_" + sub,
                          {"audio": (1, 10, frames_for(random_source, 1, 10))}, flags={flag: 0x1234})
        yield widget_case(f"flag clear moves index off zero {flag}", random_source, b"0_optionsaudio_" + sub,
                          {"audio": (1, 10, frames_for(random_source, 1, 10))}, flags={})
        yield widget_case(f"flag set leaves index zero {flag}", random_source, b"0_optionsaudio_" + sub,
                          {"audio": (1, 10, frames_for(random_source, 1, 10))}, flags={flag: 0x1234})
    # the name length check: a zero-length copy is an empty name
    for text in (b"4_main_",):
        yield widget_case(f"empty name from lstrlenA 0 {text!r}", random_source, text, full_sets(), length=string_length_zero)
    # random worlds
    for n in range(40):
        key, token = random_source.choice(keyed)
        low = random_source.randrange(-3, 8)
        high = low + random_source.randrange(0, 25)
        null_at = tuple(i for i in range(max(low, 0), high + 1) if random_source.randrange(4) == 0)
        sets = {k: (low, high, frames_for(random_source, low, high, null_at)) for k in SET_NAMES
                if random_source.randrange(5)}
        index = random_source.randrange(-3, high + 4)
        prefix = f"{index}".encode()
        suffix = b"" if key != "audio" else random_source.choice([b"", b"_sound", b"_music", b"_voice", b"_ambient"])
        flag_values = flag_sets(random_source, list(FLAG_OFFSETS), count=1)[0]
        yield widget_case(f"random {n}", random_source, prefix + token + suffix, sets,
                          buckets=random_source.randrange(1, 20), flags=flag_values,
                          refs=random_source.choice([1, 1, 2, 0xFFFFFFFF]))


def cases(random_source):
    yield from lookup_cases(random_source)
    yield from widget_cases(random_source)
