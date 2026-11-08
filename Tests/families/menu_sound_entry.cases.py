"""Original sound construction, real PCM loading and CString publication."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate

CREATE = 0x4CA3B0
DELETE = 0x4CA670
DESTROY = 0x4CA690
NEW = 0x4F63EC
FREE = 0x4F6428


def setup_create(mode, key=b'menu-click', disabled=0, mutate=False, dictionary='empty', samples=b'\x13\x97\x42\xe1\x0a\x6d\xf8\x25'):
    def setup(env):
        manager = env.object(64, 'sound-manager', fill=0)
        scene = env.object(48, 'scene', fill=0)
        pcm = env.object(128, 'pcm-manager', fill=0)
        resource = env.object(48, 'resource-file', fill=0)
        owner = env.object(40, 'archive-owner', fill=0)
        name = env.object(len(key) + 1, 'name', data=key + b'\0')
        record = env.object(512, 'physical-observations', fill=0)
        env.put(manager + 0xC, scene)
        env.put(manager + 0x18, 1)  # one bucket deliberately forces collision traversal
        env.put(manager + 0x28, 4)  # map block size
        env.put(manager + 0x30, disabled)
        env.put(scene + 0x20, 0 if mode == 'no-scene-audio' else pcm)
        env.put(resource + 0x24, owner)
        env.put(pcm + 0x78, 0 if mode == 'pcm-disabled' else 1)
        fmt = struct.pack('<HHIIHHH', 1, 1, 8000, 8000, 1, 8, 0)
        wave = b'RIFF' + struct.pack('<I', 4 + 8 + len(fmt) + 8 + len(samples)) + b'WAVEfmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(samples)) + samples
        data = env.object(len(wave), 'riff-wave', data=wave)
        env.put(resource + 0x14, 0 if mode == 'acquire-fails' else len(wave))
        if mode != 'acquire-fails':
            if mode == 'temporary':
                env.put(resource + 0x18, data)
            else:
                env.put(owner + 0xC, 0x1230)
                env.put(owner + 0x20, data)
                env.put(resource + 0x28, 0x1230)
        if mode == 'bad-wave':
            env.write(data, b'NOPE')
        if dictionary != 'empty':
            buckets = env.object(4, 'buckets', fill=0)
            association = env.object(16, 'old-association', fill=0)
            old_key = key if dictionary == 'existing' else b'other-key'
            old_name = env.object(len(old_key) + 1, 'old-key', data=old_key + b'\0')
            old_value = env.object(20, 'old-value-retained', fill=0xA7)
            env.put(association, 0, 0, old_name, old_value)
            env.put(buckets, association)
            env.put(manager + 0x14, buckets)
            env.put(manager + 0x1C, 1)
        allocated = env.object(20, 'entry-allocation', fill=0xD3)
        replacement = env.object(48, 'replacement-scene', fill=0)
        env.put(replacement + 0x20, pcm)

        def new(env, call):
            size = call.arguments[0]
            count = env.calls_so_far(NEW)
            env.put(record + 4 * count, size)
            if count == 1:
                if mode == 'allocation-fails':
                    return 0
                if mutate:
                    env.put(manager + 0xC, replacement)
                    # This is also the actual map association count.
                    env.put(manager + 0x1C, 0x51)
                return allocated
            return env.object(size, 'dependency-allocation', fill=0xB9)

        def free(env, call):
            address = call.arguments[0]
            at = record + 256 + 24 * (env.calls_so_far(FREE) - 1)
            env.put(at, address, env.get(manager + 0x1C), env.get(allocated), env.get(allocated + 4), env.get(allocated + 0xC), env.get(allocated + 0x10))
            env.release(address)
            return 0

        env.override(NEW, new)
        env.override(FREE, free)
        env.override(0x5469E4, lambda env, call: len(env.cstr(call.arguments[0])))
        device = env.object(4, 'directsound-device', fill=0)
        device_vtable = env.object(16, 'device-vtable', fill=0)
        buffer = env.object(4, 'directsound-buffer', fill=0)
        buffer_vtable = env.object(80, 'buffer-vtable', fill=0)
        output = env.object(len(samples) + 8, 'physical-pcm-buffer', fill=0xE7)
        env.put(pcm + 0x14, device)
        env.put(device, device_vtable)
        env.put(buffer, buffer_vtable)

        def create_buffer(env, call):
            device_arg, desc, out, outer = call.arguments
            env.put(record + 64, call.receiver, device_arg, outer, env.get(manager + 0x1C), env.get(allocated), env.get(allocated + 4), env.get(allocated + 8), env.get(allocated + 0xC), env.get(allocated + 0x10))
            env.write(record + 104, env.read(desc, 20))
            env.write(record + 124, env.read(env.get(desc + 16), 18))
            env.put(out, 0 if mode == 'null-com-buffer' else buffer)
            return 0

        def get_value(value):
            def effect(env, call):
                env.put(call.arguments[1], value)
                return 0
            return effect

        def lock(env, call):
            obj, offset, length, p1, n1, p2, n2, flags = call.arguments
            env.put(record + 144, obj, offset, length, flags, env.get(allocated + 0x10))
            split = len(samples) // 2
            env.put(p1, output)
            env.put(n1, split)
            env.put(p2, output + split)
            env.put(n2, len(samples) - split)
            return 0

        def unlock(env, call):
            env.put(record + 168, *call.arguments, env.get(allocated + 0x10), env.get(manager + 0x1C))
            return 0

        env.put(device_vtable + 12, env.stub('IDirectSound::CreateSoundBuffer', 'stdcall', 4, create_buffer))
        env.put(buffer_vtable + 0x20, env.stub('IDirectSoundBuffer::GetFrequency', 'stdcall', 2, get_value(8000)))
        env.put(buffer_vtable + 0x1C, env.stub('IDirectSoundBuffer::GetPan', 'stdcall', 2, get_value(0x123)))
        env.put(buffer_vtable + 0x18, env.stub('IDirectSoundBuffer::GetVolume', 'stdcall', 2, get_value(0xFFFFF830)))
        env.put(buffer_vtable + 0x2C, env.stub('IDirectSoundBuffer::Lock', 'stdcall', 8, lock))
        env.put(buffer_vtable + 0x4C, env.stub('IDirectSoundBuffer::Unlock', 'stdcall', 5, unlock))
        return {'manager': manager, 'resource': resource, 'name': name}
    return setup


def setup_destroy(resource_state, words):
    def setup(env):
        sound = env.object(24, 'sound', words=words)
        scene = env.object(48, 'scene', fill=0)
        pcm = env.object(128, 'pcm', fill=0)
        resource = env.object(56, 'loaded-pcm', fill=0)
        observations = env.object(64, 'cleanup-observations', fill=0)
        env.put(sound + 0xC, scene)
        env.put(sound + 0x10, 0 if resource_state == 'none' else resource)
        env.put(scene + 0x20, 0 if resource_state == 'no-manager' else pcm)
        # Disabled PCM service deliberately retains the resource, while unload clears sound+16.
        env.put(pcm + 0x78, 1 if resource_state == 'active' else 0)
        if resource_state == 'active':
            interface = env.object(4, 'live-directsound-buffer', fill=0)
            vtable = env.object(12, 'live-buffer-vtable', fill=0)
            env.put(interface, vtable)
            env.put(resource, 0x51350C)
            env.put(resource + 0xC, interface, pcm)
            env.put(pcm + 4, resource + 4, resource + 4)
            def com_release(env, call):
                env.put(observations + 32, call.receiver, call.arguments[0])
                env.write(observations + 40, env.read(sound, 24))
                return 0
            env.put(vtable + 8, env.stub('IDirectSoundBuffer::Release', 'stdcall', 1, com_release))
        def free(env, call):
            env.put(observations, call.arguments[0])
            env.write(observations + 4, env.read(sound, 24))
            env.release(call.arguments[0])
            return 0
        env.override(FREE, free)
        return {'sound': sound}
    return setup


def cases(random_source):
    for disabled in (1, 0x80000000, 0xFFFFFFFF):
        yield Case(f'disabled {disabled:#x}', CREATE, setup_create('acquire-fails', disabled=disabled), receiver=lambda t: t['manager'], arguments=(lambda t: t['name'], lambda t: t['resource']))
    for mode in ('allocation-fails', 'acquire-fails', 'no-scene-audio', 'pcm-disabled', 'bad-wave', 'null-com-buffer', 'temporary', 'success'):
        yield Case(mode, CREATE, setup_create(mode), receiver=lambda t: t['manager'], arguments=(lambda t: t['name'], lambda t: t['resource']))
    for dictionary in ('existing', 'collision'):
        yield Case('dictionary ' + dictionary, CREATE, setup_create('success', dictionary=dictionary), receiver=lambda t: t['manager'], arguments=(lambda t: t['name'], lambda t: t['resource']))
    yield Case('allocator changes owner and scene before initialization', CREATE, setup_create('success', mutate=True), receiver=lambda t: t['manager'], arguments=(lambda t: t['name'], lambda t: t['resource']))
    for index in range(5):
        samples = bytes(random_source.randrange(256) for _ in range(random_source.randrange(1, 25)))
        key = bytes(random_source.randrange(65, 91) for _ in range(random_source.randrange(1, 32)))
        yield Case(f'random publication {index}', CREATE, setup_create('success', key=key, samples=samples, dictionary=('empty', 'existing', 'collision')[index % 3]), receiver=lambda t: t['manager'], arguments=(lambda t: t['name'], lambda t: t['resource']))
    for state in ('none', 'no-manager', 'disabled-pcm', 'active'):
        words = [random_source.getrandbits(32) for _ in range(6)]
        yield Case('destroy ' + state, DESTROY, setup_destroy(state, words), receiver=lambda t: t['sound'])
        for flags in (0, 1, 2, 0x100, 0x101, 0xFFFFFFFE, 0xFFFFFFFF):
            yield Case(f'delete {state} flags {flags:#x}', DELETE, setup_destroy(state, words), receiver=lambda t: t['sound'], arguments=(flags,))
