"""Independent cases for the menu volume and complete palette services."""
from clawparity.cases import Case

VOLUME = 0x42CDC0
FADE = 0x42D590
CLOCK = 0x546DF0
GLOBAL_VOLUME = 0x532C10


def volume_setup(value, scene_flag, has_audio, seed, alias=None, nodes=False):
    def setup(env):
        app = env.object(0x180, "application", fill=0xA5)
        scene = env.object(0x30, "scene", fill=0x67)
        context = env.object(0x30, "audio context", fill=0x9B)
        audio = env.object(0x10, "audio", fill=0xD3)
        env.put(context + 0x2C, 0)
        env.put(audio, context, seed ^ 0x75A61329, 0x9374A5B6, 0)
        if alias == "scene reads application volume":
            scene = app + 0x104
        elif alias == "scene reads audio volume":
            scene = audio - 0x24
        env.put(app + 0x30, scene if scene_flag is not None else 0)
        env.put(app + 0x5C, audio if has_audio else 0)
        env.put(app + 0x12C, seed)
        if scene_flag is not None:
            env.put(scene + 0x28, scene_flag)
        env.put(GLOBAL_VOLUME, seed ^ 0xFE319CA7)
        if nodes:
            tail = env.object(12, "null audio payload node", words=[0, seed, 0])
            payload = env.object(0x10, "unchanged audio payload", fill=0x49)
            env.put(payload + 0xC, value)
            head = env.object(12, "equal audio payload node", words=[tail, seed ^ 0x5678, payload])
            env.put(audio + 0xC, head)
        return {"app": app}
    return setup


def palette_setup(pixels, base, step, get_status, set_status):
    def setup(env):
        palette = env.object(0x10, "palette", fill=0xB3)
        entries = env.object(1024, "palette entries", data=pixels)
        interface = env.object(4, "palette COM interface")
        vtable = env.object(0x1C, "palette COM vtable")
        observations = env.object(16 * 1048 + 4, "palette callback observations", fill=0)
        env.put(palette + 4, interface)
        env.put(palette + 0xC, entries)
        env.put(interface, vtable)
        for address in (0x54139C, 0x5413A0, 0x5413A4, 0x5413A8):
            env.put(address, 0)

        def record(env, call, kind):
            index = env.get(observations)
            destination = observations + 4 + index * 1048
            env.put(destination, kind, *call.arguments)
            env.write(destination + 24, env.read(entries, 1024))
            env.put(observations, index + 1)

        def get_entries(env, call):
            record(env, call, 1)
            env.write(call.arguments[4], pixels)
            return get_status

        def set_entries(env, call):
            record(env, call, 2)
            return set_status

        env.put(vtable + 0x10, env.stub("GetEntries", "stdcall", 5, get_entries))
        env.put(vtable + 0x18, env.stub("SetEntries", "stdcall", 5, set_entries))

        def clock(env, call):
            return (base + (env.calls_so_far(CLOCK) - 1) * step) & 0xFFFFFFFF

        env.override(CLOCK, clock)
        return {"palette": palette}
    return setup


def cases(random_source):
    values = [0, 1, 100, 0xFFFFFFFF, 0x80000000, 0x12345678]
    values += [random_source.getrandbits(32) for _ in range(4)]
    for value in values:
        for flag, audio in ((None, False), (None, True), (0, False), (0, True), (1, False), (0x80000000, True)):
            seed = random_source.getrandbits(32)
            yield Case(f"volume {value:#x} scene {flag} audio {audio}", VOLUME,
                       volume_setup(value, flag, audio, seed, nodes=audio),
                       receiver=lambda t: t["app"], arguments=(value,))
    for alias, value, flag in (("scene reads application volume", 0, 1),
                               ("scene reads application volume", 0x76543210, 0),
                               ("scene reads audio volume", 0x87654321, 0),
                               ("scene reads audio volume", 0, 0xABCDEF01)):
        yield Case(alias + f" {value:#x}", VOLUME,
                   volume_setup(value, flag, True, random_source.getrandbits(32), alias=alias),
                   receiver=lambda t: t["app"], arguments=(value,))

    colors = [(0, 0, 0), (255, 1, 128), (0x12345678, 0xFEDCBA09, 0xABCDEF31)]
    colors += [tuple(random_source.getrandbits(32) for _ in range(3)) for _ in range(3)]
    for index, color in enumerate(colors):
        for duration in (0, 10, 37):
            pixels = bytes(random_source.randrange(256) for _ in range(1024))
            base = 0xFFFFFFF5 if index % 2 else 23947
            yield Case(f"palette {index} duration {duration}", FADE,
                       palette_setup(pixels, base, 11, 0, 0),
                       receiver=lambda t: t["palette"], arguments=(*color, duration))
    for get_status, set_status in ((0x80004005, 0), (0, 0x88760001), (1, 1)):
        pixels = bytes(random_source.randrange(256) for _ in range(1024))
        yield Case(f"palette COM results {get_status:#x}/{set_status:#x}", FADE,
                   palette_setup(pixels, 8931, 13, get_status, set_status),
                   receiver=lambda t: t["palette"], arguments=(17, 93, 201, 25))
