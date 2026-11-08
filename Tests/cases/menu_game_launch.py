"""Original-only menu command, profile and saved-game probes.

All game callees execute their original instructions. The only overrides are
physical imports declared by the reviewed specification.
"""
from clawparity.cases import Case
from clawparity.fixtures import returns

DISPATCH = 0x426E30


def profile(present=True, flags=0, count=1, name=b"Player"):
    def setup(env):
        app = env.object(0x100, "application", fill=0xA6)
        manager = env.object(0x20, "profile-manager", fill=0x51)
        data = env.object(0x2300, "profile", fill=0x37)
        env.put(app + 0x60, manager, data if present else 0)
        env.put(manager + 0xC, count)
        env.write(data + 0x14, name + b"\0")
        for kind, base in ((1, 0x2D4), (2, 0xD24), (3, 0x1774)):
            for level in range(15):
                env.put(data + base + level * 0xB0, (0xA5800000 | (level << 8) | (kind << 4) | (flags ^ ((level + kind) & 3))))
        return {"app": app}
    return setup


def file_setup(description=b"Level 7", size=0x5F4, read_count=0x5F4,
               opened=True, enabled=True, empty=False, null_path=False, null_output=False, refcount=2):
    def setup(env):
        app = env.object(0x100, "application", fill=0)
        system = env.object(0x50, "system", fill=0)
        env.put(0x5371FC, app)
        env.put(app + 0x30, system)
        env.put(system + 0x24, int(enabled))
        text = b"" if empty else b"save/slot3.sav"
        storage = env.object(0x80, "CString-path", fill=0xCE)
        env.put(storage, refcount, len(text), 0x70)
        env.write(storage + 12, text + b"\0")
        output = env.object(0x700, "description-output", fill=0xD9)
        observations = env.object(0x80, "file-observations", fill=0)

        def copy(env, call):
            dst, src, count = call.arguments
            value = env.cstr(src)
            if isinstance(value, str):
                value = value.encode("latin1")
            env.write(dst, value[:max(0, count - 1)] + b"\0")
            return dst

        def length(env, call):
            return len(env.cstr(call.arguments[0]))

        def interlocked(delta):
            def effect(env, call):
                ptr = call.arguments[0]
                value = (env.get(ptr) + delta) & 0xFFFFFFFF
                env.put(ptr, value)
                return value
            return effect

        def create(env, call):
            env.put(observations, *call.arguments)
            return 0xFFFFFFFF if not opened else 0x12345

        def read(env, call):
            handle, dst, requested, actual, overlapped = call.arguments
            env.put(observations + 0x20, *call.arguments)
            blob = bytearray((i * 29 + 71) & 255 for i in range(0x5F4))
            blob[:4] = size.to_bytes(4, "little")
            blob[16:16 + len(description) + 1] = description + b"\0"
            env.write(dst, bytes(blob[:min(requested, read_count)]))
            env.put(actual, read_count)
            return 1

        env.override(0x546AD0, returns(0))
        env.override(0x5469CC, copy)
        env.override(0x5469E4, length)
        env.override(0x5469E8, interlocked(-1))
        env.override(0x5469EC, interlocked(1))
        env.override(0x546B00, create)
        env.override(0x546AFC, read)
        env.override(0x546A04, returns(1))
        return {"path": 0 if null_path else storage + 12,
                "out": 0 if null_output else output, "app": app}
    return setup


def application(state=1, pause=0, query=0, shutdown=0, mutate_state=None,
                world=True, dimensions=None, toggle=0, suppress=1, player=False, fail_allocation=False, audio_map=False, substate=0, transition_mode=0, helper=False, audio_controller=False, width=0, monolith=None, video_size=None, crc_error=False, swap_state=False, distinct_controls=False,
                named_profile=False, display_depth=0, audible=False, midi=False,
                audio_changes_global=False, display_head=False):
    def setup(env):
        app = env.object(0x200, "application", fill=0)
        state_object = env.object(0x1000, "state", fill=0)
        methods = env.object(0x100, "state-vtable", fill=0)
        window = env.object(0x20, "window", fill=0x76)
        engine = env.object(0x300, "engine", fill=0)
        resources = env.object(0x80, "resources", fill=0)
        audio = env.object(0x80, "audio", fill=0)
        observations = env.object(0x800, "callback-observations", fill=0)
        env.put(app + 4, window, engine, pause)
        env.put(app + 0x2C, state_object, resources if world else 0)
        env.put(app + 0xA0, shutdown)
        env.put(app + 0x9C, transition_mode)
        env.put(app + 0x78, display_depth, width)
        if distinct_controls:
            env.put(app + 0x94, 0x11223344, 0x55667788)
            env.put(app + 0xA4, 0x99AABBCC, 0xDDEEFF11, 0x22446688)
            env.put(app + 0xD4, 7, 11)
        if named_profile:
            profile_data = env.object(0x2300, "named-player-profile", fill=0x43)
            env.put(profile_data + 4, 0)
            env.write(profile_data + 0x14, b"Sample profile\0")
            env.put(app + 0x64, profile_data)
        env.put(app + 0x10, toggle, toggle)
        for address in (0x537214, 0x537218, 0x53721C, 0x537220, 0x537224,
                        0x537228, 0x53722C, 0x537230, 0x537264, 0x53726C):
            env.put(address, toggle)
        sound = env.object(0x80, "sound", fill=0)
        music = env.object(0x80, "music", fill=0)
        env.put(app + 0x50, music)
        env.put(app + 0xC0, 0x53EC90)
        env.put(app + 0x5C, sound)
        env.put(sound, audio)
        env.put(window + 4, 0x7319)
        env.put(resources + 0x28, audio)
        env.put(audio + 0x30, suppress)
        sprite_manager = env.object(0x50, "sprite-manager", fill=0)
        env.put(resources + 0x10, sprite_manager)
        env.put(sprite_manager + 0x18, 17)
        env.put(audio + 0x18, 17)
        env.put(0x532C0C, 0)
        sound_entry = 0
        if audio_map:
            buckets = env.object(4, "sound-map-buckets", fill=0)
            env.put(audio + 0x14, buckets, 1)
            chain = 0
            sound_entry = env.object(0x20, "sound-entry", fill=0)
            for text in (b"GAME_MAJORCHEAT", b"GAME_MINORCHEAT", b"DISABLE", b"GAME_MONOLITH"):
                key = env.object(len(text) + 1, "sound-key", data=text + b"\0")
                node = env.object(16, "sound-map-node", words=[chain, 0, key, sound_entry])
                chain = node
            env.put(buckets, chain)
        for address in (0x5371EC, 0x5371F0):
            env.put(address, 0x53EC90)
        if fail_allocation:
            def factory_allocation(env, call):
                if call.arguments[0] >= 0x150:
                    return 0
                return env.object(call.arguments[0], "transition-stack-allocation")
            env.override(0x4F63EC, factory_allocation)
        env.put(state_object, methods, app)
        env.put(0x5371FC, app)
        env.put(0x537E88, 0)
        env.put(0x537960, 0)
        if player:
            actor = env.object(0x120, "player", fill=0x65)
            actor_system = env.object(0x20, "player-system", fill=0)
            stats = env.object(0x80, "player-stats", fill=0xA3)
            env.put(actor + 0x6C, actor_system)
            env.put(actor_system + 0x14, stats)
            env.put(0x537E88, actor)
            env.put(actor + 0x10C, 0)
        if dimensions is not None:
            geometry = env.object(0xC0, "selected-video-mode", fill=0x39)
            env.put(geometry + 0xB4, *dimensions)
            env.put(0x537960, geometry)

        replacement = env.object(0x1000, "replacement-state", fill=0) if swap_state else 0

        def record(tag, value):
            def effect(env, call):
                index = env.get(observations)
                env.put(observations, index + 1)
                env.put(observations + 4 + index * 28, tag, call.receiver,
                        env.get(app + 0x2C), env.get(app + 0x98),
                        env.get(app + 0xA0), *(list(call.arguments) + [0, 0])[:2])
                if tag == 0x10 and swap_state and index == 0:
                    env.put(app + 0x2C, replacement)
                if tag == 0x10 and mutate_state is not None:
                    value_now = mutate_state[min(index, len(mutate_state) - 1)]
                else:
                    value_now = value
                if tag == 0x91 and audio_changes_global:
                    env.put(0x53726C, 0)
                return value_now
            return effect

        for offset, argc, value in ((0, 1, 0), (0x10, 0, state), (0x24, 1, 0),
                                     (0x28, 1, 0), (0x40, 0, query), (0x4C, 0, 0), (0x54, 0, 0)):
            env.put(methods + offset, env.stub(f"state-{offset:x}", "thiscall", argc,
                                               record(offset, value)))
        if swap_state:
            replacement_methods = env.object(0x100, "replacement-state-vtable", data=env.read(methods, 0x100))
            env.put(replacement, replacement_methods)
            env.put(replacement_methods + 0x10, env.stub("replacement-state-query", "thiscall", 0,
                                                         record(0x71, 5)))
        app_methods = env.object(0x40, "application-vtable", fill=0)
        env.put(app, app_methods)
        engine_methods = env.object(0x40, "engine-vtable", fill=0)
        env.put(engine, engine_methods)
        env.put(engine_methods + 0x1C, env.stub("engine-message", "thiscall", 2, record(0x1C, 0)))
        child = env.object(4, "nested-state", fill=0)
        child_methods = env.object(0x14, "nested-state-vtable", fill=0)
        env.put(child, child_methods)
        env.put(child_methods + 0x10, env.stub("nested-state-query", "thiscall", 0, record(0x15, substate)))
        env.put(state_object + 0x154, child, 0)
        if helper:
            display = env.object(0x20, "message-display", fill=0)
            env.put(display + 0x18, 10)
            env.put(app + 0x4C, display)
            if display_head:
                text_storage = env.object(64, "queued-CString", fill=0)
                text = b"Prior message"
                env.put(text_storage, 3, len(text), 51)
                env.write(text_storage + 12, text + b"\0")
                node = env.object(12, "queued-message-node", words=[0, 0, text_storage + 12])
                env.put(display + 4, node, node, 1)
        if audible:
            driver = env.object(0x80, "DirectSound-driver", fill=0)
            env.put(driver + 0x78, 1)
            source = env.object(0x38, "sample-source", fill=0)
            voice = env.object(0x34, "sample-voice", fill=0)
            interface = env.object(4, "IDirectSoundBuffer", fill=0)
            physical_methods = env.object(0x4C, "IDirectSoundBuffer-vtable", fill=0)
            env.put(interface, physical_methods)
            env.put(source + 0x10, driver, 0, 22050, 0, 0)
            env.put(source + 0x30, voice + 4, voice + 4)
            env.put(voice + 0xC, interface, driver, 0x30, 22050)
            env.put(voice + 0x30, 1)
            env.put(sound_entry + 0x10, source)
            env.put(0x532C0C, 1)
            env.put(0x532C10, 7)

            def status(env, call):
                env.put(call.arguments[1], 0)
                return record(0x90, 0)(env, call)

            env.put(physical_methods + 0x24, env.stub("IDirectSoundBuffer::GetStatus", "stdcall", 2, status))
            for offset, count, tag, name in ((0x3C, 2, 0x92, "SetVolume"),
                                             (0x40, 2, 0x93, "SetPan"),
                                             (0x44, 2, 0x94, "SetFrequency"),
                                             (0x30, 4, 0x91, "Play"),
                                             (0x48, 1, 0x95, "Stop")):
                env.put(physical_methods + offset, env.stub("IDirectSoundBuffer::" + name, "stdcall", count, record(tag, 0)))
        if midi:
            sequence_object = env.object(0x60, "MIDI-sequence-object", fill=0)
            env.put(sequence_object, 0x513528)
            env.put(sequence_object + 0x58, 0x193A)
            env.put(music + 0x1C, sequence_object, 0x3642)
            for address, tag, result in ((0x546E78, 0xA1, 0),
                                         (0x546E7C, 0xA2, 4),
                                         (0x546E84, 0xA3, 0),
                                         (0x546E88, 0xA4, 0),
                                         (0x546E90, 0xA5, 0)):
                env.override(address, record(tag, result))
        if helper:
            def strlen(env, call):
                return len(env.cstr(call.arguments[0]))
            def increment(delta):
                def effect(env, call):
                    ptr = call.arguments[0]
                    value = (env.get(ptr) + delta) & 0xFFFFFFFF
                    env.put(ptr, value)
                    return value
                return effect
            env.override(0x5469E4, strlen)
            env.override(0x5469E8, increment(-1))
            env.override(0x5469EC, increment(1))
        env.put(app_methods + 0xC, env.stub("application-active", "thiscall", 0, record(0xC, 0)))
        env.override(0x546D50, record(0x111, 1))
        env.override(0x546D44, record(0x112, 1))
        def cursor(env, call):
            count = env.calls_so_far(0x546D54)
            if call.arguments[0]:
                return min(-3 + count, 0)
            return 0xFFFFFFFF
        env.override(0x546D54, cursor)
        env.override(0x54681C, returns(2))
        env.override(0x546DF0, returns(0x173219))
        if audio_controller:
            controller = env.object(0x80, "sound-controller", fill=0)
            env.put(audio + 0x2C, controller)
        if monolith is not None:
            world_object = env.object(0xE0, "world", fill=0)
            layer = env.object(0xC0, "monolith-layer", fill=0)
            layer_table = env.object(4, "world-layers", words=[layer])
            env.put(world_object + 0x38, layer_table, 1)
            env.put(layer + 8, monolith)
            env.write(layer + 0xB4, b"MONOLITH\0")
            env.put(resources + 0x24, world_object)
            sprite = env.object(0x70, "monolith-sprite", fill=0)
            frame = env.object(0x40, "sprite-frame", fill=0)
            frame_table = env.object(4, "sprite-frames", words=[frame])
            env.put(sprite + 0x14, frame_table)
            buckets = env.object(4, "sprite-map-buckets", fill=0)
            env.put(sprite_manager + 0x14, buckets, 1)
            chain = 0
            for text in (b"GAME_MONOLITH", b"GAME_DEVHEADS"):
                key = env.object(len(text) + 1, "sprite-key", data=text + b"\0")
                chain = env.object(16, "sprite-map-node", words=[chain, 0, key, sprite])
            env.put(buckets, chain)
        if video_size is not None:
            video = env.object(0x40, "video", fill=0)
            primary = env.object(0x40, "primary-surface", fill=0)
            manager = env.object(0x68, "surface-manager", fill=0)
            world_object = env.object(0xE0, "world", fill=0)
            env.put(video + 0x10, primary)
            env.put(primary, 0x5138D8)
            video_context = env.object(0x3C, "video-context", fill=0)
            env.put(primary + 0xC, video_context)
            env.put(primary + 0x10, *video_size)
            env.put(resources + 4, video)
            env.put(resources + 0x18, manager)
            env.put(resources + 0x24, world_object)
        if crc_error:
            video = env.object(0x40, "video", fill=0)
            primary = env.object(0x40, "primary-surface", fill=0)
            secondary = env.object(0x40, "secondary-surface", fill=0)
            wrapper = env.object(0x30, "directdraw-surface-wrapper", fill=0)
            interface = env.object(4, "IDirectDrawSurface", fill=0)
            physical_methods = env.object(0x30, "IDirectDrawSurface-vtable", fill=0)
            env.put(interface, physical_methods)
            env.put(physical_methods + 0x2C, env.stub("IDirectDrawSurface::Flip", "stdcall", 3, record(0x2C, 0)))
            env.put(wrapper + 8, interface)
            env.put(primary + 0x2C, wrapper)
            env.put(video + 0x10, primary, secondary)
            env.put(resources + 4, video)
            env.put(state_object + 0xC, resources)
            directdraw = env.object(4, "IDirectDraw", fill=0)
            directdraw_methods = env.object(0x2C, "IDirectDraw-vtable", fill=0)
            env.put(directdraw, directdraw_methods)
            env.put(directdraw_methods + 0x28, env.stub("IDirectDraw::RestoreDisplayMode", "stdcall", 1, record(0x28, 0)))
            container = env.object(4, "directdraw-container", words=[directdraw])
            env.put(resources + 0x1C, container)
        return {"app": app}
    return setup


def dispatch(label, setup, command, parameter=0):
    return Case(label, DISPATCH, setup, receiver=lambda t: t["app"],
                arguments=(0x6789, command, parameter))


def cases(random_source):
    query_inputs = [(False, 0, level) for level in (-1, 0, 1, 2, 14, 15)]
    query_inputs += [(True, flags, level) for flags in (0, 1, 2, 3)
                     for level in (1, 2, 14)]
    query_inputs += [(True, random_source.randrange(4, 16), level)
                     for level in (-2147483648, 0, 7, 15, 2147483647)]
    for present, flags, level in query_inputs:
        yield Case(f"level {level} profile {present} flags {flags}", 0x42BA10,
                   profile(present, flags), receiver=lambda t: t["app"], arguments=(level,))
        for checkpoint in (-1, 0, 1, 2, 3, 4):
            yield Case(f"checkpoint {level}/{checkpoint} profile {present} flags {flags}",
                       0x42BA70, profile(present, flags), receiver=lambda t: t["app"],
                       arguments=(level, checkpoint))
    for present in (False, True):
        for count in (-1, 0, 1, 2, 7, 0x7FFFFFFF):
            yield Case(f"profile count {count} present {present}", 0x42BAB0,
                       profile(present, count=count), receiver=lambda t: t["app"])
        for name in (b"Player", b"player", b"PLAYER", b"Player2", b"", b"Sample", b"PlaYer "):
            yield Case(f"profile name {name!r} present {present}", 0x42BAD0,
                       profile(present, name=name), receiver=lambda t: t["app"])

    for null_path, null_output in ((True, False), (False, True)):
        yield Case(f"description null {null_path}/{null_output}", 0x4CD530,
                   file_setup(null_path=null_path, null_output=null_output),
                   arguments=(lambda t: t["path"], lambda t: t["out"]))
    for empty, enabled in ((True, True), (False, False)):
        yield Case(f"saved level empty {empty} enabled {enabled}", 0x436E60,
                   file_setup(empty=empty, enabled=enabled), arguments=(lambda t: t["path"],))
    for options in ({"opened": False}, {"read_count": 0}, {"read_count": 0x5F3},
                    {"size": 0x5F5}, {"size": 0xFFFFFFFF}):
        for function in (0x4CD530, 0x436E60):
            yield Case(f"saved {function:x} {options}", function, file_setup(**options),
                       arguments=((lambda t: t["path"], lambda t: t["out"]) if function == 0x4CD530
                                  else (lambda t: t["path"],)))
    for description in (b"", b"Level 1", b"chapter14 checkpoint2", b"no digits here", b"-17", b"foo 0000098 tail",
                        b"\xff\x80\x7fX0", b"stage 2147483647", b"stage 2147483648"):
        for function in (0x4CD530, 0x436E60):
            yield Case(f"saved {function:x} description {description!r}", function,
                       file_setup(description=description, size=random_source.choice((0, 1, 0x5F3, 0x5F4))),
                       arguments=((lambda t: t["path"], lambda t: t["out"]) if function == 0x4CD530
                                  else (lambda t: t["path"],)))

    # Exercise guarded ordinary commands and both unknown-command dispatch tables.
    guarded = (0x8005, 0x8007, 0x800A, 0x800E, 0x801B, 0x801C, 0x8021,
               0x8022, 0x8024, 0x8025, 0x8026, 0x802A, 0x802B, 0x802C,
               0x8038, 0x8039, 0x803A, 0x803C, 0x803D, 0x8042, 0x805C,
               0x8062, 0x8063, 0x807C, 0x807D, 0x8082, 0x8083, 0x8084, 0x8085)
    for command in guarded:
        yield dispatch(f"guarded command {command:x}", application(), command)
    for command in (0, 0x8004, 0x800B, 0x8043, 0x8048, 0x80AC, 0xFFFFFFFF, 0x18043):
        yield dispatch(f"unrecognized command {command:x}", application(), command)
    for shutdown in (0, 1):
        yield dispatch(f"quit shutdown {shutdown}", application(shutdown=shutdown), 0x8008)
    for state in (3, 4, 6):
        yield dispatch(f"state callback54 state {state}", application(state), 0x805C)
        for query in (0, 7):
            yield dispatch(f"send message state {state} query {query}", application(state, query=query), 0x800E)
    for dimensions in (None, (-1, 480), (640, 0), (640, 480), (1, 1)):
        yield dispatch(f"selected geometry {dimensions}", application(3, dimensions=dimensions), 0x80AA)
    for state in (1, 4):
        yield dispatch(f"global display toggle state {state}", application(state), 0x8082)
    for command in range(0x8050, 0x8057):
        yield dispatch(f"saved slot guarded {command:x}", application(1), command)

    for command in (0x8043, 0x8044, 0x8045, 0x8046, 0x8047, 0x8049, 0x804A,
                    0x804B, 0x804C, 0x804D, 0x804E, 0x804F, 0x805B, 0x8064,
                    0x8065, 0x8066, 0x8068, 0x806A, 0x806C, 0x806E, 0x806F,
                    0x8071, 0x8072, 0x8076, 0x8077, 0x8078, 0x8079, 0x807A,
                    0x807B, 0x8086, 0x8087, 0x8088, 0x8089, 0x808A, 0x808B,
                    0x808D, 0x808E, 0x8091, 0x8092, 0x8093):
        yield dispatch(f"fallback command {command:x}", application(3), command)
    for command in (0x8043, 0x8047, 0x8049, 0x804A, 0x804B, 0x804C, 0x804D,
                    0x804E, 0x804F, 0x8068, 0x806A, 0x806E, 0x806F, 0x8071,
                    0x8072, 0x808B):
        yield dispatch(f"toggle off {command:x}", application(3, toggle=0xFFFFFFFF), command)
    for command in (0x8044, 0x8045, 0x8046, 0x806C):
        yield dispatch(f"player mutation {command:x}", application(3, player=True), command)
    for toggle in (0, 1):
        yield dispatch(f"sound toggle {toggle}", application(toggle=toggle), 0x8009)
    for command in (0x8059, 0x8095):
        yield dispatch(f"helper early {command:x}", application(), command)

    for command in (0x8005, 0x8006, 0x800D, 0x8021, 0x8023, 0x8025, 0x8027,
                    0x8035, 0x807E, 0x807F, 0x8080, 0x8090, 0x80AB):
        for failure in (False, True):
            yield dispatch(f"transition {command:x} allocation failure {failure}",
                           application(2, shutdown=0 if failure else 1, fail_allocation=failure),
                           command, 7)
    for command in (0x8044, 0x8045, 0x8046, 0x806C, 0x807A):
        yield dispatch(f"empty audio map {command:x}", application(3, suppress=0), command)

    for command in range(0x809C, 0x80AA):
        for failure in (False, True):
            yield dispatch(f"level command {command:x} failure {failure}",
                           application(3, shutdown=0 if failure else 1, fail_allocation=failure,
                                       mutate_state=(3, 1)), command)
    for command, state in ((0x8007, 3), (0x800A, 3), (0x800F, 4), (0x801B, 6),
                           (0x801C, 6), (0x802A, 6), (0x8036, 1), (0x8039, 5),
                           (0x803A, 3), (0x803C, 4), (0x803D, 4), (0x8041, 3),
                           (0x8042, 6), (0x8063, 3), (0x8075, 1), (0x807C, 10),
                           (0x8083, 4), (0x8084, 3)):
        yield dispatch(f"complement primary {command:x} state {state}",
                       application(state, player=command in (0x803C, 0x803D), world=command != 0x801B), command)
    for toggle in (0, 1):
        yield dispatch(f"music toggle {toggle}", application(3, toggle=toggle), 0x800A)
    for command in (0x8022, 0x8026):
        for suppress in (0, 1):
            yield dispatch(f"disable command {command:x} suppress {suppress}",
                           application(2, suppress=suppress), command)
    for state in (9, 13, 15, 14, 8):
        yield dispatch(f"dialog blocked in state {state}", application(state), 0x8035)
    for command in (0x8005, 0x8021):
        for state in (5, 10, 13):
            yield dispatch(f"state guard {command:x} state {state}", application(state, shutdown=1), command)
    for command in (0x8048, 0, 0xFFFFFFFF, 0x18044, 0x180AA):
        yield dispatch(f"fallback full word {command:x}", application(3), command)

    for refcount in (1, 2, 0x7FFFFFFF):
        yield Case(f"saved path reference count {refcount}", 0x436E60,
                   file_setup(empty=True, refcount=refcount), arguments=(lambda t: t["path"],))
    for index in range(8):
        description = bytes(random_source.randrange(65, 91) for _ in range(index * 31))
        yield Case(f"random saved description {index}", 0x4CD530,
                   file_setup(description=description),
                   arguments=(lambda t: t["path"], lambda t: t["out"]))

    for command in (0x8043, 0x8044, 0x8045, 0x8046, 0x8047, 0x8049, 0x804A,
                    0x804B, 0x804C, 0x804D, 0x804E, 0x804F, 0x805B, 0x8064,
                    0x8065, 0x8066, 0x8068, 0x806A, 0x806C, 0x806E, 0x806F,
                    0x8071, 0x8072, 0x807A, 0x807B, 0x808B, 0x808D, 0x808E,
                    0x8091, 0x8092, 0x8093):
        yield dispatch(f"found sound command {command:x}",
                       application(3, suppress=0, audio_map=True), command)
    for command in (0x8022, 0x8026):
        yield dispatch(f"disable found {command:x}", application(2, suppress=0, audio_map=True), command)
    yield dispatch("nested state completed", application(10, substate=2), 0x807C)
    yield dispatch("alternate transition", application(2, shutdown=1, transition_mode=1), 0x8006)
    yield dispatch("dead player repeat death", application(3, player=True), 0x8063)
    yield dispatch("empty message display", application(4, helper=True), 0x8083)
    yield dispatch("controls guard", application(4), 0x8041)
    yield dispatch("previous resolution guard", application(6), 0x802B)
    for state in (2, 5):
        yield dispatch(f"browser launch state {state}", application(state), 0x8038)

    yield dispatch("strong enemy off", application(3, toggle=1), 0x808B)
    yield dispatch("clear enemy list", application(3), 0x808F)
    yield dispatch("screenshot no path", application(), 0x8070)
    yield dispatch("restore resolution missing world", application(6, world=False), 0x802C)
    yield dispatch("alternate transition failed allocation", application(2, transition_mode=1, fail_allocation=True), 0x8006)
    yield dispatch("sound controller present", application(audio_controller=True), 0x8009)
    yield dispatch("low resolution failure missing world", application(3, world=False, width=641), 0x8076)
    for command in (0x8086, 0x8087):
        for monolith in (0, 2):
            yield dispatch(f"sprite cheat {command:x} layer {monolith}",
                           application(3, monolith=monolith, toggle=1, audio_map=True, suppress=0), command)

    yield dispatch("low resolution already matches primary surface", application(3, width=641, video_size=(320, 200)), 0x8076)

    yield dispatch("CRC mismatch reported", application(4, crc_error=True, fail_allocation=True), 0x8085)
    yield dispatch("clear enemy list sound found", application(3, suppress=0, audio_map=True), 0x808F)

    yield dispatch("low mode fails then existing 640x480 restores", application(3, width=641, video_size=(640, 480)), 0x8076)

    yield dispatch("query callback replaces active state before next query",
                   application(1, shutdown=1, swap_state=True), 0x8005)

    # Distinguish reset destinations from neighboring control words and make
    # game helper calls publish messages or physical playback observations.
    for command in (0x8062, 0x807E):
        yield dispatch(f"nonzero control reset {command:x}",
                       application(2, distinct_controls=True, fail_allocation=True), command)
    yield dispatch("named profile score upload publishes request",
                   application(5, named_profile=True), 0x8039)
    yield dispatch("named profile score upload guarded outside menu",
                   application(1, named_profile=True), 0x8039)
    yield dispatch("pop existing queued message", application(4, helper=True, display_head=True), 0x8083)
    for depth in (8, 16, 24, 32):
        yield dispatch(f"formatted resolution depth {depth}",
                       application(3, helper=True, display_depth=depth, width=641), 0x8079)
    for toggle in (0, 1):
        yield dispatch(f"MIDI toggle original playback {toggle}", application(3, toggle=toggle, midi=True), 0x800A)
    for command in (0x8043, 0x8044, 0x8045, 0x8046, 0x8047, 0x8049,
                    0x804A, 0x804B, 0x804C, 0x804D, 0x804E, 0x804F,
                    0x806A, 0x806C, 0x806E, 0x8071, 0x8072, 0x808B):
        yield dispatch(f"audible cheat original playback {command:x}",
                       application(3, helper=True, audio_map=True, suppress=0, audible=True), command)
    yield dispatch("playback changes strong enemy global before reload",
                   application(3, helper=True, audio_map=True, suppress=0, audible=True,
                               audio_changes_global=True), 0x808B)
