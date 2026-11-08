"""Independent original PCM, resource and sound cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns

TRANSFER = 0x4B44F0
LOAD = 0x4B4A20
DESTROY = 0x4B4AE0
SOUND_LOAD = 0x4C8850
SOUND_UNLOAD = 0x4C88B0
NEW = 0x4F63EC
DELETE = 0x4F6428
SEEK = 0x4A7840
READ = 0x4A7260


def wave(payload, variant="valid"):
    fmt = struct.pack("<HHIIHHH", 1 if variant != "compressed" else 2,
                      1, 11025, 11025, 1, 8, 0)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if variant == "junk":
        chunks = b"JUNK\x03\0\0\0abc\0" + chunks
    if variant != "no-data":
        chunks += b"data" + struct.pack("<I", len(payload)) + payload
    if variant == "no-format":
        chunks = b"data" + struct.pack("<I", len(payload)) + payload
    return (b"FAIL" if variant == "bad-header" else b"RIFF") + struct.pack("<I", len(chunks) + 4) + b"WAVE" + chunks


def world(env, payload, *, available=1, first=5, second=7, lock_error=0,
          unlock_error=0, create_error=0, create_null=False, alias=None,
          reporter=False, create_disable=False, release_mutation=False,
          observe_stack=False):
    for address in (0x54130C, 0x541310, 0x541314, 0x541318):
        env.put(address, 0)
    env.put(0x541314, int(reporter))
    manager = env.object(0x7C, "audio-manager", fill=0)
    alternate = env.object(0x7C, "alternate-manager", fill=0)
    env.put(manager + 0x78, available)
    env.put(alternate + 0x78, 1)
    pool = env.object(0x38, "pool", fill=0)
    sound = env.object(0x14, "sound", fill=0)
    scene = env.object(0x24, "scene", fill=0)
    env.put(scene + 0x20, manager)
    env.put(sound + 0xC, scene, pool)
    env.put(pool, 0x51350C)
    env.put(pool + 0xC, 0, manager)
    env.put(manager + 4, pool + 4, pool + 4)
    source = env.object(max(64, len(payload)), "source", data=payload)
    one = env.object(max(64, first), "first-span", fill=0xB7)
    two = env.object(max(64, second), "second-span", fill=0xD3)
    log = env.object(256, "callback-observations", fill=0x81)
    stack_log = env.object(16, "stack-publication-observations", fill=0x93)
    vt = env.object(0x50, "buffer-vtable", fill=0)
    buffer = env.object(4, "buffer", words=[vt])
    replacement = env.object(4, "replacement-buffer", words=[vt])
    env.put(pool + 0xC, buffer)

    def lock(env, call):
        args = call.arguments
        env.put(log, call.receiver, *args)
        p1, n1, p2, n2 = args[3:7]
        if observe_stack:
            # Lock receives the address of the incoming transfer count word.
            # In loadPCM its parent third creator word is 28 bytes above it.
            env.put(stack_log, env.get(n1), env.get(n1 + 28))
        destination = one
        if alias == "first-count":
            destination = n1
        elif alias == "second-count":
            destination = n2
        elif alias == "buffer":
            destination = pool + 0xC
            env.put(source, replacement)
        env.put(p1, destination)
        env.put(n1, first)
        env.put(p2, two)
        env.put(n2, second)
        if alias == "manager":
            env.put(pool + 0x10, alternate)
        return lock_error

    def unlock(env, call):
        env.put(log + 0x30, call.receiver, *call.arguments)
        env.write(log + 0x50, env.read(one, 32))
        env.write(log + 0x70, env.read(two, 32))
        return unlock_error

    def release_buffer(env, call):
        env.put(log + 0x90, call.receiver, *call.arguments,
                env.get(pool + 0xC), env.get(sound + 0x10), env.get(manager + 4))
        if release_mutation:
            env.put(manager + 0x78, 0)
            env.put(sound + 0x10, replacement)
        return 0x76

    def get_buffer_property(env, call):
        env.put(call.arguments[1], 0x1337)
        return 0

    for offset in (0x18, 0x1C, 0x20):
        env.put(vt + offset, env.stub(f"buffer property {offset}", "stdcall", 2, get_buffer_property))
    env.put(vt + 8, env.stub("buffer release", "stdcall", 1, release_buffer))
    env.put(vt + 0x2C, env.stub("buffer lock", "stdcall", 8, lock))
    env.put(vt + 0x4C, env.stub("buffer unlock", "stdcall", 5, unlock))
    device_vt = env.object(16, "device-vtable", fill=0)
    device = env.object(4, "device", words=[device_vt])
    env.put(manager + 0x14, device)
    env.put(alternate + 0x14, device)

    def create(env, call):
        args = call.arguments
        env.put(log + 0xA8, call.receiver, *args)
        env.write(log + 0xC0, env.read(args[1], 20))
        env.write(log + 0xD8, env.read(env.get(args[1] + 16), 18))
        env.put(args[2], 0 if create_null else buffer)
        if create_disable:
            env.put(manager + 0x78, 0)
        return create_error

    env.put(device_vt + 12, env.stub("create buffer", "stdcall", 4, create))
    return dict(manager=manager, alternate=alternate, pool=pool, sound=sound,
                scene=scene, source=source, one=one, two=two, log=log,
                buffer=buffer, replacement=replacement, stack_log=stack_log)


def transfer_setup(payload, **options):
    return lambda env: world(env, payload, **options)


def load_setup(payload, variant="valid", **options):
    def setup(env):
        tokens = world(env, payload, **options)
        raw = wave(payload, variant)
        tokens["wave"] = env.object(len(raw) + 32, "wave", data=raw)
        return tokens
    return setup


def sound_setup(payload, mode="mapped", variant="valid", no_manager=False,
                seek_fail=False, short_read=False, retries=False,
                mutate_manager=False, mutate_release=False, **options):
    def setup(env):
        tokens = load_setup(payload, variant, **options)(env)
        file = env.object(0x2C, "resource-file", fill=0)
        container = env.object(0x24, "container", fill=0)
        stream_vt = env.object(12, "stream-vtable", fill=0)
        stream = env.object(16, "stream", words=[stream_vt])
        env.put(stream + 0xC, 0x12345678)
        raw = wave(payload, variant)
        env.put(file + 0x14, len(raw), 0)
        env.put(file + 0x24, container, 0x130)
        env.put(container + 0xC, 0x100)
        env.put(container + 0x18, stream)
        if mode == "mapped":
            backing = env.object(len(raw) + 0x60, "mapped-file", fill=0)
            env.write(backing + 0x30, raw)
            env.put(container + 0x20, backing)
        elif mode == "cached":
            env.put(file + 0x18, env.object(len(raw), "cached-file", data=raw))
        elif mode == "empty":
            env.put(file + 0x14, 0)
        if no_manager:
            env.put(tokens["scene"] + 0x20, 0)

        def seek(env, call):
            if mutate_manager:
                env.put(tokens["scene"] + 0x20, tokens["alternate"])
            if seek_fail or (retries and env.calls_so_far(SEEK) == 1):
                return 0xFFFFFFFF
            return 0

        def read(env, call):
            destination, element, count, handle = call.arguments
            env.write(destination, raw[:count])
            return count - 1 if short_read or (retries and env.calls_so_far(READ) == 1) else count

        def retry(env, call):
            env.put(stream + 0xC, env.get(stream + 0xC) + 0x101)
            return int(retries and env.calls_so_far(retry_address) <= 2)

        retry_address = env.stub("stream retry", "thiscall", 0, retry)
        env.put(stream_vt + 8, retry_address)
        env.override(SEEK, seek)
        env.override(READ, read)
        if mutate_release:
            def free(env, call):
                address = call.arguments[0]
                env.put(tokens["log"] + 0xF0, env.get(tokens["sound"] + 0x10))
                env.put(tokens["sound"] + 0x10, 0)
                env.release(address)
                return 0
            env.override(DELETE, free)
        tokens["file"] = file
        return tokens
    return setup


def concrete_cleanup(payload, *, voices=2, mutate=False, custom=False):
    def setup(env):
        t = world(env, payload)
        pool, manager, log = t["pool"], t["manager"], t["log"]
        nodes = [env.object(0x14, f"fade-{i}", fill=0) for i in range(3)]
        for i, node in enumerate(nodes):
            env.put(node, 0x513518, nodes[i + 1] + 4 if i < 2 else 0,
                    nodes[i - 1] + 4 if i else 0, i + 12,
                    pool if i != 1 else t["replacement"])
        env.put(manager + 0xC, nodes[0] + 4, nodes[-1] + 4)
        voice_objects = [env.object(0x2C, f"voice-{i}", fill=0) for i in range(voices)]
        voice_vt = env.object(12, "voice-buffer-methods", fill=0)
        voice_buffers = [env.object(4, f"voice-buffer-{i}", words=[voice_vt]) for i in range(voices)]
        for i, voice in enumerate(voice_objects):
            env.put(voice, 0x513510,
                    voice_objects[i + 1] + 4 if i + 1 < voices else 0,
                    voice_objects[i - 1] + 4 if i else 0, voice_buffers[i], manager)
        if voices:
            env.put(pool + 0x30, voice_objects[0] + 4, voice_objects[-1] + 4)

        def release_voice(env, call):
            index = env.calls_so_far(voice_release) - 1
            env.put(log + index * 24, call.receiver, call.arguments[0],
                    env.get(pool + 0x30), env.get(pool + 0x10),
                    env.get(manager + 0x78), env.get(pool + 0xC))
            if mutate:
                env.put(pool + 0x10, t["alternate"])
                # Disable the first manager only. A live reload must select
                # the still-available alternate for the remaining voice.
                env.put(manager + 0x78, 0)
            return 0

        voice_release = env.stub("voice release", "stdcall", 1, release_voice)
        env.put(voice_vt + 8, voice_release)

        def free(env, call):
            address = call.arguments[0]
            index = env.calls_so_far(DELETE) - 1
            env.put(log + 0x40 + index * 12, address, env.get(address),
                    env.get(address + 0xC))
            env.release(address)
            return 0
        env.override(DELETE, free)
        if custom:
            vtable = env.object(4, "custom-pool-vtable", fill=0)
            def deleting(env, call):
                env.put(log + 0xE0, call.receiver, call.arguments[0],
                        env.get(pool + 0xC), env.get(manager + 4), env.get(manager + 8))
                env.release(call.receiver)
                return 0
            env.put(vtable, env.stub("custom deleting destructor", "thiscall", 1, deleting))
            env.put(pool, vtable)
            env.put(pool + 0x30, 0, 0)
        return t
    return setup


def cases(random_source):
    payload = bytes(random_source.randrange(1, 256) for _ in range(48))
    for first, second in ((0, 0), (0, 1), (1, 0), (1, 3), (4, 4), (5, 7), (7, 9), (16, 17)):
        yield Case(f"split transfer {first}+{second}", TRANSFER,
                   transfer_setup(payload, first=first, second=second),
                   receiver=lambda t: t["pool"], arguments=(lambda t: t["source"], 47))
    for name, options in (("unavailable", dict(available=0)),
                          ("lock positive failure", dict(lock_error=1)),
                          ("lock HRESULT", dict(lock_error=0x80004005, reporter=True)),
                          ("unlock positive failure", dict(unlock_error=7)),
                          ("unlock HRESULT", dict(unlock_error=0x88780096, reporter=True)),
                          ("manager mutates", dict(alias="manager")),
                          ("buffer reloaded after copy", dict(alias="buffer", first=4, second=7))):
        yield Case(name, TRANSFER, transfer_setup(payload, **options),
                   receiver=lambda t: t["pool"], arguments=(lambda t: t["source"], 0xF00D))
    for alias in ("first-count", "second-count"):
        alias_data = struct.pack("<I", 2) + payload[4:]
        yield Case(f"copy aliases {alias} output", TRANSFER,
                   transfer_setup(alias_data, alias=alias, first=4, second=5),
                   receiver=lambda t: t["pool"], arguments=(lambda t: t["source"], 1))
    for variant in ("valid", "junk", "bad-header", "no-format", "no-data", "compressed"):
        yield Case(f"load PCM {variant}", LOAD, load_setup(payload, variant),
                   receiver=lambda t: t["manager"], arguments=(lambda t: t["wave"], 0x789ABCDE))
    for label, options in (("unavailable", dict(available=0)),
                           ("create fails", dict(create_error=0x80004005)),
                           ("create null buffer", dict(create_null=True)),
                           ("availability changes during creation", dict(create_disable=True)),
                           ("lock fails then cleanup", dict(lock_error=1)),
                           ("unlock fails then cleanup", dict(unlock_error=0x80070057))):
        yield Case(label, LOAD, load_setup(payload, **options),
                   receiver=lambda t: t["manager"], arguments=(lambda t: t["wave"], 0))
    yield Case("null PCM source", LOAD, load_setup(payload),
               receiver=lambda t: t["manager"], arguments=(0, 0xFFFFFFFF))
    yield Case("zero PCM data count", LOAD, load_setup(b""),
               receiver=lambda t: t["manager"], arguments=(lambda t: t["wave"], 19))
    for label, options in (("mapped", {}), ("cached", dict(mode="cached")),
                           ("allocated", dict(mode="allocated")),
                           ("empty", dict(mode="empty")),
                           ("missing manager", dict(mode="cached", no_manager=True)),
                           ("parse failure", dict(mode="cached", variant="bad-header")),
                           ("PCM failure", dict(mode="cached", lock_error=1)),
                           ("seek fails", dict(mode="allocated", seek_fail=True)),
                           ("short read", dict(mode="allocated", short_read=True)),
                           ("seek and read retry", dict(mode="allocated", retries=True)),
                           ("manager reloaded after file read", dict(mode="allocated", mutate_manager=True)),
                           ("result cached before file release", dict(mode="cached", mutate_release=True))):
        yield Case(f"sound load {label}", SOUND_LOAD, sound_setup(payload, **options),
                   receiver=lambda t: t["sound"], arguments=(lambda t: t["file"],))
    for function, name in ((DESTROY, "destroy"), (SOUND_UNLOAD, "unload")):
        for available in (0, 1):
            yield Case(f"{name} availability {available}", function,
                       transfer_setup(payload, available=available),
                       receiver=(lambda t: t["manager"]) if function == DESTROY else (lambda t: t["sound"]),
                       arguments=(lambda t: t["pool"],) if function == DESTROY else ())
        yield Case(f"{name} callback mutates availability and sound", function,
                   transfer_setup(payload, release_mutation=True),
                   receiver=(lambda t: t["manager"]) if function == DESTROY else (lambda t: t["sound"]),
                   arguments=(lambda t: t["pool"],) if function == DESTROY else ())
    def no_resource(env):
        t = world(env, payload)
        env.put(t["sound"] + 0x10, 0)
        return t
    yield Case("unload missing resource", SOUND_UNLOAD, no_resource, receiver=lambda t: t["sound"])
    def no_manager(env):
        t = world(env, payload)
        env.put(t["scene"] + 0x20, 0)
        return t
    yield Case("unload missing manager retains resource", SOUND_UNLOAD, no_manager, receiver=lambda t: t["sound"])

    for function in (DESTROY, SOUND_UNLOAD):
        for count, mutate, custom in ((1, False, False), (2, False, False),
                                      (2, True, False), (0, False, True)):
            yield Case(f"concrete cleanup {function:x} voices {count} mutate {mutate} custom {custom}",
                       function, concrete_cleanup(payload, voices=count, mutate=mutate, custom=custom),
                       receiver=(lambda t: t["manager"]) if function == DESTROY else (lambda t: t["sound"]),
                       arguments=(lambda t: t["pool"],) if function == DESTROY else ())
    def no_file_allocation(env):
        t = sound_setup(payload, mode="allocated")(env)
        env.override(NEW, returns(0))
        return t
    yield Case("sound file allocation fails", SOUND_LOAD, no_file_allocation,
               receiver=lambda t: t["sound"], arguments=(lambda t: t["file"],))

    yield Case("nested transfer count and creator input published before Lock", LOAD,
               load_setup(payload, observe_stack=True),
               receiver=lambda t: t["manager"], arguments=(lambda t: t["wave"], 0x6491A7D3))
    yield Case("sound nested load zero creator input published before Lock", SOUND_LOAD,
               sound_setup(payload, mode="cached", observe_stack=True),
               receiver=lambda t: t["sound"], arguments=(lambda t: t["file"],),
               initial_stack=((-12, struct.pack("<I", random_source.randrange(1, 0xFFFFFFFF))),))

    def parser_failure_publication(env):
        t = sound_setup(payload, mode="cached", variant="bad-header")(env)
        def free(env, call):
            # Sound's loadPCM entry is outer ESP-20. Its format output
            # remains at outer ESP-28 when release reaches operator delete.
            env.put(t["stack_log"], env.get(0x02008000 - 28))
            env.release(call.arguments[0])
            return 0
        env.override(DELETE, free)
        return t
    yield Case("failed nested parser publishes zero format before file release", SOUND_LOAD,
               parser_failure_publication, receiver=lambda t: t["sound"],
               arguments=(lambda t: t["file"],),
               initial_stack=((-28, struct.pack("<I", random_source.randrange(1, 0xFFFFFFFF))),))
