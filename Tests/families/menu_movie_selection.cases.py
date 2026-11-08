"""Original-only normal-return movie selection cases; physical file open fails."""
from clawparity.cases import Case
from clawparity.fixtures import returns

SELECT, AVAILABLE, ELIGIBLE = 0x42B5D0, 0x42C0A0, 0x42C280


def setup_case(path=b"MOVIES/CLAW.FEC", available=True, player=True, flags=None,
               optional=False, descriptor=True, surface=True, hwnd=0x1234,
               option=0, table=None, reload=False, observe=False):
    def setup(env):
        app = env.object(0x124, "application", fill=0x91)
        text = 0 if path is None else env.object(len(path) + 1, "archive", data=path+b"\0")
        alternate = env.object(24, "alternate archive", data=b"ALT/CHANGED-MOVIE.FEC\0")
        records = env.object(0x2118, "player", fill=0xA6) if player else 0
        replacement = env.object(0x2118, "replacement player", fill=0x5B)
        for level in range(15):
            value = flags[level] if flags else 1
            if records:
                env.put(records + 0x1774 + level * 0xB0, value)
            env.put(replacement + 0x1774 + level * 0xB0, value ^ 1)
        env.put(app + 0x64, records)
        env.put(app + 0x100, text)
        env.put(app + 0x120, option)
        window = env.object(8, "window", fill=0x2B)
        env.put(window + 4, hwnd)
        env.put(app + 4, window)
        scene = env.object(0x24, "scene", fill=0x32)
        owner = env.object(0x14, "display owner", fill=0x43)
        target = env.object(0x30, "display target", fill=0x54)
        desc = env.object(0x78, "descriptor", fill=0x65)
        holder = env.object(4, "surface holder")
        first = env.object(4, "first surface")
        second = env.object(4, "second surface")
        vtable = env.object(0x90, "COM vtable")
        env.put(first, vtable)
        env.put(second, vtable)
        observations = env.object(256, "platform observations", fill=0)
        media_trace = env.object(16 * 0x560, "escaped media observations") if observe else 0

        def record_media(env, event):
            # 0x4f0a83 publishes media+0xfc to GetSystemPaletteEntries.
            # Keep the actual escaped alias, never derive it from entry ESP.
            media = env.get(observations + 128)
            index = env.get(observations + 132)
            destination = media_trace + index * 0x560
            env.put(destination, event, media)
            env.write(destination + 0x10, env.read(media, 0x534))
            # Media+0x8680 is the genuine embedded list constructed at 0x42b628.
            env.write(destination + 0x544, env.read(media + 0x8680, 0x14))
            env.put(observations + 132, index + 1)

        def palette_entries(env, call):
            env.put(observations + 128, call.arguments[3] - 0xFC)
            record_media(env, 1)
            return 0

        def blt(env, call):
            env.put(observations + 64, call.receiver, *call.arguments)
            if observe:
                record_media(env, 2)
            return 0

        env.put(vtable + 0x14, env.stub("surface Blt", "stdcall", 6, blt))
        env.put(desc + 8, second)
        # DDSURFACEDESC bit count is the 22nd copied dword.
        env.put(desc + 0x60, 32)
        env.put(holder, first if surface else 0)
        env.put(target + 0x2C, desc if descriptor else 0)
        env.put(owner + 0x10, target)
        extra = env.object(0x18, "optional display", fill=0x76)
        env.put(extra + 0x14, 0x3456)
        env.put(scene + 4, owner)
        env.put(scene + 0x1C, holder)
        env.put(scene + 0x20, extra if optional else 0)
        env.put(app + 0x30, scene)
        if table is not None:
            env.put(0x52552C, *table)

        def open_file(env, call):
            count = env.calls_so_far(0x546A30)
            env.put(observations, count, *call.arguments)
            if reload:
                env.put(app + 0x64, replacement)
                env.put(app + 0x100, alternate)
            return 7 if available else 0xFFFFFFFF

        def copy_string(env, call):
            dest, source, size = call.arguments
            if size:
                data = env.cstr(source)[:size-1]
                if isinstance(data, str):
                    data = data.encode()
                env.write(dest, data+b"\0")
            return dest

        def counter(delta):
            def effect(env, call):
                pointer = call.arguments[0]
                value = (env.get(pointer) + delta) & 0xFFFFFFFF
                env.put(pointer, value)
                return value
            return effect

        def cursor(env, call):
            env.put(observations + 32, *call.arguments)
            if observe:
                record_media(env, 3 + call.arguments[0])
            return 0

        env.override(0x546A30, open_file)
        env.override(0x4A3B10, returns(0x1256ABCD))
        env.override(0x4A3040, returns(0))
        env.override(0x5469E4, lambda env, call: len(env.cstr(call.arguments[0])))
        env.override(0x5469CC, copy_string)
        env.override(0x546B00, returns(0xFFFFFFFF))
        env.override(0x5469E8, counter(-1))
        env.override(0x5469EC, counter(1))
        env.override(0x546D54, cursor)
        if observe:
            env.override(0x546914, palette_entries)
        return {"app": app}
    return setup


def case(label, function, **options):
    argument = options.pop("level", None)
    stack = options.pop("stack", ())
    return Case(label, function, setup_case(**options), receiver=lambda t: t["app"],
                arguments=() if argument is None else (argument,), initial_stack=stack)


def cases(random_source):
    stack = (
        (-0x86A4, random_source.getrandbits(0x550 * 8).to_bytes(0x550, "little")),
        (-0x24, random_source.getrandbits(0x14 * 8).to_bytes(0x14, "little")),
    )
    for path in (None, b"", b"CLAW.FEC", b"disc/MOVIES/archive with spaces.FEC"):
        for available in (False, True):
            yield case(f"archive {path!r} available {available}", AVAILABLE, path=path, available=available)
    yield case("eligibility null player", ELIGIBLE, player=False, level=0)
    yield case("eligibility archive missing", ELIGIBLE, available=False, level=0)
    for level in (0, 1, 2, 14, 15, -1, -0x80000000, 0x7FFFFFFF):
        for flag in (0, 1, 2, 3, 0x80000000, 0xFFFFFFFF):
            yield case(f"eligibility level {level} flags {flag:#x}", ELIGIBLE, level=level, flags=[flag]*15)
    yield case("eligibility reloads player after availability", ELIGIBLE, level=2, reload=True)
    yield case("selection missing archive", SELECT, stack=stack, available=False)
    yield case("selection null archive", SELECT, stack=stack, path=None)
    yield case("selection absent descriptor", SELECT, stack=stack, descriptor=False)
    yield case("selection absent first surface optional present", SELECT, stack=stack, surface=False, optional=True)
    yield case("selection init failure zero HWND", SELECT, stack=stack, hwnd=0)
    yield case("selection positive loop stops on first ineligible", SELECT, stack=stack, flags=[0]*15, table=list(range(11,24)))
    yield case("selection all nonpositive loop slots", SELECT, stack=stack, table=[0,-1,-2,0,-0x80000000,0,-99,0,0,-3,0,-4,0])
    for option in (0, 1, 2, 0x80000000, 0xFFFFFFFF):
        flags = [(random_source.getrandbits(32)|1) for _ in range(15)]
        table = [random_source.randrange(3,200) for _ in range(13)]
        yield case(f"selection full endpoint option {option:#x}", SELECT, stack=stack, option=option, flags=flags, table=table, optional=bool(option))
    for stop in (3,7,14):
        flags = [1]*15
        flags[stop] = 2
        table = [0,-1,8,11,0,16,18,0,21,22,23,24,25]
        yield case(f"selection skip slots level stop {stop}", SELECT, stack=stack, flags=flags, table=table)
    yield case("selection availability reloads player and archive", SELECT, stack=stack, reload=True, flags=[0]*15, table=list(range(10,23)), option=9)
    yield case("selection records escaped media initialization and cleanup", SELECT,
               stack=stack, observe=True, table=[0]*13)
    yield case("selection records escaped media with full queue", SELECT,
               stack=stack, observe=True, optional=True, option=7,
               flags=[random_source.getrandbits(32)|1 for _ in range(15)],
               table=list(range(41,54)))
