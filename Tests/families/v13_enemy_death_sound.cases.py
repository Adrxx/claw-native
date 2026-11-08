"""v1.3 death and sound cases derived from pinned original instructions."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

DEATH, DIRECT, NAMED, CREATE = 0x440130, 0x421BB0, 0x421C00, 0x4CAE00
RAND, NEW, FREE, BACKEND = 0x4A595B, 0x4FCAEA, 0x4FCB13, 0x4B3DA0
ENABLE, VOLUME, TICK = 0x53098C, 0x530990, 0x5AAFDC


def install_sound(env, last, interval):
    sound = env.object(28, 'sound-resource', fill=0xC7)
    pool = env.object(20, 'backend-pool', fill=0x81)
    env.put(sound + 0x10, pool, last, interval)
    return sound


def sound_setup(last=100, interval=10, now=110, enabled=1, result=1,
                named=False, disabled=0, missing=False, null=False, seed=0):
    def setup(env):
        sound = install_sound(env, last, interval)
        env.put(ENABLE, enabled)
        env.put(VOLUME, 53 ^ seed)
        env.put(TICK, now)
        log = env.object(64, 'play-observations', fill=0)
        def play(env, call):
            env.put(log, call.receiver, *call.arguments, env.get(sound + 0x14), env.get(sound + 0x18))
            return result
        env.override(BACKEND, play)
        t = {'this':sound}
        if named:
            manager = env.object(56, 'name-manager', fill=0)
            query = env.object(12, 'query', data=b'SFX_DEATH\0')
            buckets = env.object(4, 'buckets', fill=0)
            key = env.object(12, 'stored-key', data=b'SFX_DEATH\0')
            tail = env.object(16, 'matching-association', words=[0, 0x12345678, key, 0 if null else sound])
            collision_key = env.object(20, 'collision-key', data=b'OTHER_COLLISION\0')
            head = env.object(16, 'collision-association', words=[0 if missing else tail, 0x98765432, collision_key, 0x12])
            env.put(buckets, head)
            env.put(manager + 0x14, buckets, 1)
            env.put(manager + 0x30, disabled)
            t.update(this=manager, name=query)
        return t
    return setup


def death_setup(rs, count=32, bits=0x5A000001, rand=25, facing=3, sound=True,
                enabled=1, last=100, interval=10, now=110, category=0x1234,
                bounce=0, current=2, maximum=5, tree=True):
    seed = rs.getrandbits(28)
    def setup(env):
        enemy = env.object(0x440, 'enemy', fill=0xA5)
        owner = env.object(0x120, 'actor', fill=0)
        record = env.object(0x40, 'state-record', fill=0x63)
        sprite = env.object(0x200, 'sprite', fill=0x79)
        aux = env.object(0x100, 'actor-auxiliary', fill=0)
        env.put(enemy + 0x10, owner, record)
        env.put(enemy + 0x154, sprite)
        env.put(owner + 0x74, category)
        env.put(owner + 0x84, aux)
        env.put(aux + 0xE8, 7)
        env.put(sprite + 8, seed & ~0x10080)
        env.put(enemy + 0x1B4, facing)
        env.put(enemy + 0x31C, 0, 0, count)
        if count > 32:
            heap_bits = env.object(16, 'heap-state-bits', words=[bits, seed ^ 0xAABBCCDD, seed ^ 0x33445566, 0xFADE1234])
            env.put(enemy + 0x328, heap_bits)
        else:
            env.put(enemy + 0x328, bits)
        # The unchanged animation selector reads an actual first list element.
        element = env.object(48, 'animation-element', fill=0x31)
        array = env.object(8, 'animation-array', words=[element, 0])
        header = env.object(40, 'animation-list', fill=0)
        env.put(header + 0xC, array, 1)
        env.put(header + 0x20, seed ^ 0x13579)
        env.put(enemy + 0x39C, header)
        for offset in (0x3CC, 0x3D0, 0x3D4, 0x3D8):
            env.put(enemy + offset, install_sound(env,last,interval) if sound else 0)
        env.put(ENABLE, enabled)
        env.put(VOLUME, seed ^ 0x2A)
        env.put(TICK, now)
        env.put(0x535928, seed ^ 0x4D)
        env.put(0x5365D4, 0)
        env.put(0x535958, bounce)
        env.put(0x535DA0, current, maximum)
        env.put(0x53595C, seed)
        message_owner = env.object(84, 'message-owner', fill=0)
        env.put(0x535910, message_owner)
        if tree:
            raw = env.cstr(0x52152C)
            if isinstance(raw,str): raw=raw.encode('latin1')
            key = env.object(len(raw)+4,'state-key',data=raw+b'\0'*4)
            node = env.object(20,'state-tree-node',fill=0)
            env.put(node,node,node,0,key,seed ^ 0x6A)
            env.put(0x5ACD00 + 0x18,node)
        else:
            env.put(0x5ACD00 + 0x18,0)
        env.override(RAND, returns(rand))
        observations=env.object(128,'death-play-observations',fill=0)
        def play(env,call):
            index=env.calls_so_far(BACKEND)-1
            env.put(observations+index*32,call.receiver,*call.arguments,env.get(enemy+0x328),env.get(enemy+0x32C))
            return 1
        env.override(BACKEND,play)
        return {'this':enemy}
    return setup

def setup_create(mode, key=b'menu-click', disabled=0, mutate=False, dictionary='empty', interval=19, samples=b'\x13\x97\x42\xe1\x0a\x6d\xf8\x25'):
    def setup(env):
        # Initialize the original CString 64-character native allocation pool.
        env.put(0x53D430, 0x50, 4, 0, 0)
        manager = env.object(64, 'sound-manager', fill=0)
        scene = env.object(48, 'scene', fill=0)
        pcm = env.object(256, 'pcm-manager', fill=0)
        resource = env.object(64, 'resource-file', fill=0)
        owner = env.object(80, 'archive-owner', fill=0)
        name = env.object(len(key) + 8, 'name', data=key + b'\0' * 8)
        record = env.object(512, 'physical-observations', fill=0)
        env.put(manager + 0xC, scene)
        env.put(manager + 0x18, 1)  # one bucket deliberately forces collision traversal
        env.put(manager + 0x28, 4)  # map block size
        env.put(manager + 0x30, disabled, interval)
        env.put(scene + 0x20, 0 if mode == 'no-scene-audio' else pcm)
        env.put(resource + 0x10, owner)
        env.put(pcm + 0x78, 0 if mode == 'pcm-disabled' else 1)
        fmt = struct.pack('<HHIIHHH', 1, 1, 8000, 8000, 1, 8, 0)
        wave = b'RIFF' + struct.pack('<I', 4 + 8 + len(fmt) + 8 + len(samples)) + b'WAVEfmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(samples)) + samples
        data = env.object(len(wave), 'riff-wave', data=wave)
        env.put(resource + 0xC, 0 if mode == 'acquire-fails' else len(wave))
        if mode != 'acquire-fails':
            if mode == 'temporary':
                env.put(resource + 0x38, data)
            else:
                env.put(owner + 0xC, 0x1230)
                env.put(owner + 0x48, data)
                env.put(resource + 0x14, 0x1230)
        if mode == 'bad-wave':
            env.write(data, b'NOPE')
        if dictionary != 'empty':
            buckets = env.object(4, 'buckets', fill=0)
            association = env.object(16, 'old-association', fill=0)
            old_key = key if dictionary == 'existing' else b'other-key'
            old_name = env.object(len(old_key) + 8, 'old-key', data=old_key + b'\0' * 8)
            old_value = env.object(20, 'old-value-retained', fill=0xA7)
            env.put(association, 0, 0, old_name, old_value)
            env.put(buckets, association)
            env.put(manager + 0x14, buckets)
            env.put(manager + 0x1C, 1)
        allocated = env.object(28, 'entry-allocation', fill=0xD3)
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
        env.override(0x50C318, lambda env, call: len(env.cstr(call.arguments[0])))
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
            env.put(manager + 0x34, interval ^ 0x6A)
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
        def get_caps(env, call):
            env.put(call.arguments[1] + 4, 0xE0, len(samples), 0, 0)
            return 0
        env.put(buffer_vtable + 0xC, env.stub('IDirectSoundBuffer::GetCaps', 'stdcall', 2, get_caps))
        env.put(buffer_vtable + 0x20, env.stub('IDirectSoundBuffer::GetFrequency', 'stdcall', 2, get_value(8000)))
        env.put(buffer_vtable + 0x1C, env.stub('IDirectSoundBuffer::GetPan', 'stdcall', 2, get_value(0x123)))
        env.put(buffer_vtable + 0x18, env.stub('IDirectSoundBuffer::GetVolume', 'stdcall', 2, get_value(0xFFFFF830)))
        env.put(buffer_vtable + 0x2C, env.stub('IDirectSoundBuffer::Lock', 'stdcall', 8, lock))
        env.put(buffer_vtable + 0x4C, env.stub('IDirectSoundBuffer::Unlock', 'stdcall', 5, unlock))
        return {'manager': manager, 'resource': resource, 'name': name}
    return setup


def cases(random_source):
    rs=random_source
    boundaries=((0,0,0),(100,0,100),(100,1,100),(100,1,101),
                (100,10,109),(100,10,110),(100,10,111),
                (0xFFFFFFFE,4,1),(0xFFFFFFFE,4,2),(0xFFFFFFFE,4,3),
                (0,0xFFFFFFFF,0xFFFFFFFE),(0,0xFFFFFFFF,0xFFFFFFFF),
                (0x80000000,0x80000000,0),(0x80000000,0x80000001,0))
    for named in (False,True):
        fn=NAMED if named else DIRECT
        for last,interval,now in boundaries:
            for result in (0,1):
                yield Case(f'sound named={named} last={last:x} interval={interval:x} now={now:x} result={result}',fn,
                           sound_setup(last,interval,now,result=result,named=named,seed=rs.getrandbits(16)),
                           receiver=lambda t:t['this'],arguments=(lambda t:t['name'],) if named else (0x12345,0xABCDEF01,0x7FFFFFFF,0xFFFFFFFF))
        yield Case(f'sound named={named} disabled globally',fn,sound_setup(enabled=0,named=named),receiver=lambda t:t['this'],arguments=(lambda t:t['name'],) if named else (1,2,3,4))
    for options in ({'disabled':1},{'missing':True},{'null':True}):
        yield Case(f'named guard {options}',NAMED,sound_setup(named=True,**options),receiver=lambda t:t['this'],arguments=(lambda t:t['name'],))
    for count in (0,1,4,5,32,33):
        for bits in (0,1,0x10,0x11,0xA6F01235):
            for bounce in (0,1):
                yield Case(f'death mode0 count={count} bits={bits:x} bounce={bounce}',DEATH,death_setup(rs,count=count,bits=bits,bounce=bounce),receiver=lambda t:t['this'],arguments=(0,))
    for mode in (1,2,3,4,0xFFFFFFFF):
        for count in (0,5,33):
            for sound in (False,True):
                yield Case(f'death mode={mode} count={count} sound={sound}',DEATH,death_setup(rs,count=count,sound=sound),receiver=lambda t:t['this'],arguments=(mode,))
    for opts in ({'rand':0},{'rand':24},{'rand':-1},{'facing':0},{'category':0x2134},{'tree':False},{'sound':False},{'enabled':0},{'current':6,'maximum':5},{'current':0x7FFFFFFF,'maximum':5}):
        yield Case(f'death mode0 branch {opts}',DEATH,death_setup(rs,bounce=1,bits=0x11,**opts),receiver=lambda t:t['this'],arguments=(0,))
    for last,interval,now in boundaries:
        yield Case(f'death inline guard {last:x}/{interval:x}/{now:x}',DEATH,death_setup(rs,last=last,interval=interval,now=now),receiver=lambda t:t['this'],arguments=(1,))
    for disabled in (1,0xFFFFFFFF):
        yield Case(f'create disabled {disabled}',CREATE,setup_create('acquire-fails',disabled=disabled),receiver=lambda t:t['manager'],arguments=(lambda t:t['name'],lambda t:t['resource']))
    for mode in ('allocation-fails','acquire-fails','no-scene-audio','pcm-disabled','bad-wave','null-com-buffer','temporary','success'):
        yield Case('create '+mode,CREATE,setup_create(mode),receiver=lambda t:t['manager'],arguments=(lambda t:t['name'],lambda t:t['resource']))
    for dictionary in ('empty','existing','collision'):
        for interval in (0,1,0xFFFFFFFF):
            yield Case(f'create dictionary={dictionary} interval={interval}',CREATE,setup_create('success',dictionary=dictionary,interval=interval),receiver=lambda t:t['manager'],arguments=(lambda t:t['name'],lambda t:t['resource']))
    yield Case('create allocator mutation',CREATE,setup_create('success',mutate=True),receiver=lambda t:t['manager'],arguments=(lambda t:t['name'],lambda t:t['resource']))
