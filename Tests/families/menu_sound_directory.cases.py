"""Real resource iterators, CString map and sound creation; physical audio fixtures."""
import struct
from clawparity.cases import Case
NEW = 0x4F63EC


def scene(tree, prefix=None, disabled=0, fail_size=0, fail_nth=0, duplicate=(), mutate=False, samples=b'\x13\x57\x91\xd4\x28\x6b\xa9', malformed=False, audio_enabled=1):
    def setup(env):
        def string(value):
            return env.object(len(value)+1, 'string', data=value+b'\0')
        def table(address, values, offset):
            buckets = env.object(16, 'resource buckets', fill=0)
            env.put(address, 1, buckets)
            env.put(buckets+8, values[0]+offset+4 if values else 0)
            for i, value in enumerate(values):
                env.put(value+offset, 0, values[i+1]+offset+4 if i+1<len(values) else 0, 0, address, 0, value)
        wave = b'RIFF'+struct.pack('<I',36+len(samples))+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,1,11025,11025,1,8)+b'data'+struct.pack('<I',len(samples))+samples
        if malformed:
            wave = b'NOPE' + wave[4:]
        data = env.object(len(wave), 'RIFF PCM', data=wave)
        archive = env.object(36, 'mapped archive', fill=0)
        env.put(archive+0x20,data)
        types = {kind: env.object(4,kind,words=[value]) for kind,value in [('wav',0x574156),('other',0x504944)]}
        def directory(spec, name):
            children, group_specs = spec
            result = env.object(0x4c, 'directory', fill=0)
            env.put(result,string(name))
            child_objects = [directory(subtree,subname) for subname,subtree in children]
            groups = []
            for entries in group_specs:
                group = env.object(0x24,'group',fill=0)
                resources = []
                for entry_name,kind in entries:
                    entry = env.object(0x60,'resource',fill=0)
                    env.put(entry,string(entry_name))
                    env.put(entry+8,types[kind])
                    env.put(entry+0x14,len(wave))
                    env.put(entry+0x24,archive)
                    resources.append(entry)
                table(group+0x1c,resources,0x48)
                groups.append(group)
            table(result+0x3c,child_objects,0x24)
            table(result+0x44,groups,4)
            return result
        root = directory(tree,b'ROOT')
        audio = env.object(0x7c,'audio manager',fill=0)
        env.put(audio+0x78,audio_enabled)
        parent = env.object(0x24,'parent',fill=0)
        env.put(parent+0x20,audio)
        manager = env.object(52,'initialized sound manager',fill=0)
        env.put(manager,0x513b00)
        env.put(manager+0xc,parent)
        env.put(manager+0x10,0x510054,0,17,0,0,0,10)
        env.put(manager+0x30,disabled)
        buckets = env.object(68,'CString map buckets',fill=0)
        env.put(manager+0x14,buckets)
        for name,value in duplicate:
            hashed = 0
            for byte in name:
                hashed = (hashed*33+byte)&0xffffffff
            bucket = buckets+(hashed%17)*4
            node = env.object(16,'existing association',words=[env.get(bucket),hashed%17,string(name),value])
            env.put(bucket,node)
        record = env.object(256,'audio observations',fill=0)
        buffer_methods = env.object(0x50,'buffer methods',fill=0)
        ds_methods = env.object(0x10,'DirectSound methods',fill=0)
        ds = env.object(4,'DirectSound',words=[ds_methods])
        env.put(audio+0x14,ds)
        def property_get(value):
            def effect(env,call):
                env.put(call.arguments[1],value)
                return 0
            return effect
        for offset,value in [(0x20,11025),(0x1c,0xffffff91),(0x18,0x73)]:
            env.put(buffer_methods+offset,env.stub('DirectSound property '+str(offset),'stdcall',2,property_get(value)))
        def create(env,call):
            index = env.get(record)
            size = env.get(call.arguments[1]+8)
            buffer = env.object(4,'DirectSound buffer',words=[buffer_methods])
            env.put(call.arguments[2],buffer)
            env.put(record,index+1)
            env.put(record+4+index*12,call.arguments[0],size,env.get(manager+0x1c))
            return 0
        def lock(env,call):
            count = call.arguments[2]
            first = max(1,count//2)
            left = env.object(first,'PCM first',fill=0xc7)
            right = env.object(count-first or 1,'PCM second',fill=0x39)
            env.put(call.arguments[3],left)
            env.put(call.arguments[4],first)
            env.put(call.arguments[5],right)
            env.put(call.arguments[6],count-first)
            return 0
        def unlock(env,call):
            env.put(record+224,call.arguments[0],call.arguments[2],call.arguments[4])
            return 0
        env.put(ds_methods+0xc,env.stub('IDirectSound::CreateSoundBuffer','stdcall',4,create))
        env.put(buffer_methods+0x2c,env.stub('IDirectSoundBuffer::Lock','stdcall',8,lock))
        env.put(buffer_methods+0x4c,env.stub('IDirectSoundBuffer::Unlock','stdcall',5,unlock))
        def sprintf(env,call):
            value = b''.join(env.cstr(a) for a in call.arguments[2:])
            env.write(call.arguments[0],value+b'\0')
            return len(value)
        env.override(0x4a3920,sprintf)
        env.override(0x5469e4,lambda env,call:len(env.cstr(call.arguments[0])))
        def allocate(env,call):
            size = call.arguments[0]
            index = env.calls_so_far(NEW)
            if (fail_size and size==fail_size) or (fail_nth and index==fail_nth):
                return 0
            if mutate and index==1:
                env.put(manager+0x30,1)
            return env.object(size,'allocation',fill=0xa5)
        env.override(NEW,allocate)
        return dict(manager=manager,directory=root,prefix=0 if prefix is None else string(prefix),separator=string(b'::'))
    return setup


def load(label,tree,**options):
    return Case(label,0x4ca440,scene(tree,**options),receiver=lambda t:t['manager'],arguments=(lambda t:t['directory'],lambda t:t['prefix'],lambda t:t['separator']))


def cases(random_source):
    empty = ([],[])
    wavs = ([],[[(b'A','wav'),(b'BELL','wav'),(b'skip','other')],[],[(b'LONGER','wav')]])
    nested = ([(b'X',([(b'DEEP',wavs)],[[(b'INNER','wav')]])),(b'WIDE',wavs)],[[(b'ROOTSND','wav')]])
    yield load('disabled nonzero',empty,disabled=0xffffffff)
    yield load('scratch allocation fails',empty,fail_size=256)
    yield load('empty directory',empty)
    yield load('empty groups and non-WAV entries',([],[[],[(b'NO','other')],[]]))
    for prefix in (None,b'',b'ROOTPREFIX'):
        yield load('resources prefix '+repr(prefix),wavs,prefix=prefix)
        yield load('recursive prefix '+repr(prefix),nested,prefix=prefix)
    yield load('duplicates skip nonzero values',wavs,duplicate=((b'A',0x13579),(b'BELL',0x97531)))
    yield load('zero map value permits creation',wavs,duplicate=((b'A',0),))
    yield load('entry allocation fails',wavs,fail_size=20)
    yield load('invalid RIFF creation failure',wavs,malformed=True)
    yield load('audio unavailable creation failure',wavs,audio_enabled=0)
    yield load('hash collision retains unequal key',wavs,duplicate=((b'R',0x24681),))
    yield load('descendant allocation fails',nested,fail_nth=2)
    yield load('disabled changes during allocation',nested,mutate=True)
    repeated = ([(b'SAME',([],[[(b'SND','wav'),(b'SND','wav')]])),(b'SAME',([],[[(b'SND','wav')]]))],[[(b'SAME','wav')]])
    yield load('recursive duplicate publication',repeated,prefix=b'P')
    for width in (0,2,3,4,31,255):
        yield load('name copy width '+str(width),([],[[(b'N'*width,'wav')]]))
    for index in range(8):
        name = bytes(random_source.randrange(65,91) for _ in range(random_source.randrange(1,25)))
        pcm = bytes(random_source.randrange(256) for _ in range(random_source.randrange(1,48)))
        yield load('random resource '+str(index),([],[[(name,'wav'),(name,'wav')]]),prefix=b'S' if index&1 else None,samples=pcm)
