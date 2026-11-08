"""Independent byte-domain palette and world-reset cases from the original packet."""
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW = 0x4F63EC
INSTALL = 0x4C60A0
PREPARE = 0x4C6FA0
COMPARE = 0x4C70B0
RESET = 0x4CB5F0
START = 0x46E160


def palette_setup(palette, count=0, capacity=0, fail=0, mutate=False):
    def setup(env):
        manager = env.object(32, 'palette-manager', fill=0x5a)
        data = env.object(1024, 'palette', data=palette)
        storage = env.object(max(4, capacity * 4), 'existing-palette-list', fill=0xb3) if capacity else 0
        env.put(manager + 4, 0x731924ab, storage, count, capacity, 0)
        observations = env.object(96, 'allocation-observations', fill=0)
        def alloc(env, call):
            n = env.calls_so_far(NEW)
            env.put(observations + (n - 1) * 24, call.arguments[0], env.get(manager + 8),
                    env.get(manager + 12), env.get(0x5430c0), env.get(data), n)
            if mutate and n == 2:
                env.write(data, palette[::-1])
            if n == fail:
                return 0
            return env.object(max(1, call.arguments[0]), 'allocation', fill=0xcc)
        env.override(NEW, alloc)
        return {'manager': manager, 'palette': data}
    return setup


def world_setup(first, second, mode='plain', seed=0):
    def setup(env):
        world = env.object(128, 'world', fill=0xa7)
        log = env.object(512, 'reset-callback-observations', fill=0)
        env.put(log, 0)
        def destroy(env, call):
            n = env.get(log)
            env.put(log + 4 + n * 36, call.receiver, call.arguments[0], env.get(world + 0x38),
                    env.get(world + 0x3c), env.get(world + 0x4c), env.get(world + 0x50),
                    env.get(world + 0x5c), env.get(world + 0x60), env.get(call.receiver + 4))
            env.put(log, n + 1)
            if mode == 'shrink' and n == 0:
                env.put(world + 0x3c, 1)
            if mode == 'second-shrink' and call.receiver == second_objects[0]:
                env.put(world + 0x50, 1)
            if mode == 'replace-next' and n == 0:
                env.put(first_storage + 4, first_objects[-1])
            return (seed ^ (n * 0x273b15)) & 0xffffffff
        vt = env.object(8, 'element-vtable', fill=0)
        env.put(vt + 4, env.stub('world-element deleting destructor', 'thiscall', 1, destroy))
        def elements(pattern, name):
            objects = []
            for i, present in enumerate(pattern):
                if present:
                    p = env.object(12, name + '-element', fill=0x8d)
                    env.put(p, vt, seed ^ ((i + 1) * 0x1234f), 0xcafe1000 + i)
                    objects.append(p)
                else:
                    objects.append(0)
            arr = env.object(max(4, len(objects) * 4), name + '-storage', fill=0x72)
            if objects:
                env.put(arr, *objects)
            return arr, objects
        first_storage, first_objects = elements(first, 'first')
        second_storage, second_objects = elements(second, 'second')
        env.put(world + 0x34, 0x2bb8da9, first_storage, len(first), len(first) + 3, 9)
        env.put(world + 0x48, 0x6ac149d, second_storage, len(second), len(second) + 5, 13)
        env.put(world + 0x5c, 0x1872b9af, 0x234baf19)
        return {'world': world}
    return setup


def cases(random_source):
    for selector in (0, 1, 2, 3, 4, 5, 8, 9, 49, 50, 51, 0xffffffff, 0x80000000):
        value = random_source.getrandbits(32)
        def install_setup(env, value=value):
            env.put(0x5430b0, 0x319acb74, 0x472acb81, 0xa78310b2, 0xb7123fd2)
        yield Case(f'install selector {selector}', INSTALL, install_setup, arguments=(value, selector))

    palettes = [
        ('ascending-gray', bytes(v for i in range(256) for v in (i, i, i, 0x79))),
        ('descending-gray', bytes(v for i in range(256) for v in (255-i, 255-i, 255-i, 0x61))),
        ('all-equal', bytes((91, 91, 91, 0x80)) * 256),
        ('paired-equal', bytes(v for i in range(256) for v in (i//2, i//2, i//2, i))),
        ('channel-order', bytes(v for i in range(256) for v in (i, (i*73)&255, 255-i, (i*17)&255))),
        ('random', bytes(random_source.randrange(256) for _ in range(1024))),
    ]
    for label, palette in palettes:
        for count, capacity in ((0, 0), (2, 7), (3, 3)):
            yield Case(f'prepare {label} list {count}/{capacity}', PREPARE,
                       palette_setup(palette, count, capacity), receiver=lambda t:t['manager'],
                       arguments=(lambda t:t['palette'],))
    for fail in (1, 2):
        yield Case(f'prepare allocation failure {fail}', PREPARE,
                   palette_setup(palettes[-1][1], fail=fail), receiver=lambda t:t['manager'],
                   arguments=(lambda t:t['palette'],))
    yield Case('palette re-read after payload allocation', PREPARE,
               palette_setup(palettes[-1][1], mutate=True), receiver=lambda t:t['manager'],
               arguments=(lambda t:t['palette'],))

    pairs = [((0,0,0,0),(255,255,255,255)), ((255,255,255,0),(0,0,0,255)),
             ((91,91,91,0),(91,91,91,255)), ((255,0,0,7),(0,255,0,3)),
             ((0,0,255,4),(255,0,0,9)), ((1,0,0,0),(0,0,0,0)),
             ((0,1,0,0),(0,0,0,0)), ((0,0,1,0),(0,0,0,0))]
    pairs += [(tuple(random_source.randrange(256) for _ in range(4)),
               tuple(random_source.randrange(256) for _ in range(4))) for _ in range(24)]
    for i, (a,b) in enumerate(pairs):
        def setup(env,a=a,b=b):
            palette=env.object(1024,'comparison-palette',fill=0xe3)
            env.write(palette+4*17,bytes(a)); env.write(palette+4*231,bytes(b))
            left=env.object(4,'left-index',data=bytes((17,0x7b,0x9c,0xef)))
            right=env.object(4,'right-index',data=bytes((231,0xf8,0x3b,0x5d)))
            env.put(0x5430c0,palette)
            return {'left':left,'right':right}
        yield Case(f'luminance pair {i}',COMPARE,setup,
                   arguments=(lambda t:t['left'],lambda t:t['right']))
    for first,second,mode in (([],[],'plain'),([False],[False],'plain'),
                              ([True,False,True],[False,True,True],'plain'),
                              ([True,True,True],[True,True],'shrink'),
                              ([True,False,True],[True,True,True],'second-shrink'),
                              ([True,True,True],[True],'replace-next')):
        yield Case(f'reset {first}/{second} {mode}', RESET,
                   world_setup(first,second,mode,random_source.getrandbits(32)), receiver=lambda t:t['world'])

    for depth,missing in ((16,False),(32,False),(8,True)):
        def setup(env,depth=depth,missing=missing):
            state=env.object(0x780,'startup-state',fill=0x91)
            display=env.object(0x80,'display',fill=0)
            env.put(display+0x78,depth); env.put(display+0x58,0 if missing else 0x12345678)
            env.put(state+4,display)
            return {'state':state}
        yield Case(f'startup depth {depth} missing {missing}', START,setup,receiver=lambda t:t['state'])

    # Resource services are real game lookups and parsers. Only CMemFile transport
    # and heap allocation are physical stand-ins; serialized CLT bytes are input.
    plans = [
        ('valid','valid',0), ('empty','valid',1), ('missing','valid',1),
        ('valid','empty',3), ('valid','missing',3),
        ('valid','valid',5), ('valid','valid',6),
        ('valid','valid',(2,3)), ('valid','valid',(4,5)),
        ('clear-average','valid',0),
    ]
    for light, average, fail_n in plans:
        yield Case(f'startup resources {light}/{average} fail allocation {fail_n}', START,
                   startup_setup(light,average,fail_n,random_source.getrandbits(32)),
                   receiver=lambda t:t['state'])


def startup_setup(light, average, fail_n, seed):
    def setup(env):
        state=env.object(0x780,'startup-state',fill=0x91)
        display=env.object(0x80,'display',fill=0)
        manager=env.object(32,'startup-palette-manager',fill=0)
        storage=env.object(32,'startup-palette-storage',fill=0x5b)
        env.put(manager+4,0x132abc47,storage,0,8,0)
        env.put(display+0x78,8); env.put(display+0x58,manager)
        env.put(state+4,display)
        # Uniform RGB makes genuine fallback table construction bounded while
        # nonzero auxiliary bytes distinguish palette stride and alpha handling.
        env.write(state+0x360,bytes((0,0,0,0x6d))*256)
        observations=env.object(4096,'startup-service-observations',fill=0)
        env.put(observations,0)
        def observe(env,kind,*words):
            n=env.get(observations)
            env.put(observations+4+n*40,kind,*words,
                    env.get(state+0x768),env.get(state+0x76c),env.get(state+0x770))
            env.put(observations,n+1)
        def alloc(env,call):
            n=env.calls_so_far(NEW)
            observe(env,1,n,call.arguments[0],env.get(manager+12))
            if n in (fail_n if isinstance(fail_n, tuple) else (fail_n,)):
                return 0
            if light == 'clear-average' and n == 5:
                env.put(state+0x76c,0)
            return env.object(max(1,call.arguments[0]),'startup-allocation',fill=0xc7)
        env.override(NEW,alloc)
        # One namespace directory named PALETTES, containing a CLT type table.
        root=env.object(0x60,'root-namespace',fill=0)
        directory=env.object(0x60,'palette-namespace',fill=0)
        type_object=env.object(0x34,'CLT-type',fill=0)
        env.put(type_object,0x434c54)
        def chain_map(receiver,offset,entries,buckets):
            array=env.object(buckets*16,'lookup-buckets',fill=0)
            env.put(receiver+offset+4,array)
            heads={}
            for key,value in entries:
                node=env.object(24,'lookup-node',fill=0)
                env.put(node+4,heads.get(key,0))
                env.put(node+20,value)
                heads[key]=node+4
            for key,node in heads.items():
                env.put(array+8+16*key,node)
        dirname=env.object(9,'directory-name',data=b'PALETTES\0')
        env.put(directory,dirname)
        chain_map(root,0x3c,[(8%5,directory)],5)
        chain_map(directory,0x44,[(0x434c54%9,type_object)],9)
        entries=[]
        for name,mode in ((b'LIGHT',light),(b'AVERAGE',average)):
            if mode=='missing':
                continue
            resource=env.object(0x30,'resource-'+name.decode(),fill=0)
            resource_name=env.object(len(name)+1,'resource-name',data=name+b'\0')
            owner=env.object(0x30,'resource-owner',fill=0)
            env.put(resource,resource_name)
            env.put(resource+0x24,owner)
            if mode in ('valid','clear-average'):
                payload=bytes(((seed>>8)&255, seed&255, 0x7a,0xd1))
                serialized=env.object(8,'serialized-CLT',data=(4).to_bytes(4,'little')+payload)
                env.put(resource+0x14,8,serialized)
            entries.append((len(name)%19,resource))
        chain_map(type_object,0x24,entries,19)
        env.put(state+0x1c,root)
        vt=env.object(64,'memory-file-vtable',fill=0)
        def read(env,call):
            dest,size=call.arguments
            start=env.get(call.receiver+8)
            source=env.get(call.receiver+4)
            length=env.get(call.receiver+12)
            copied=min(size,max(0,length-start))
            observe(env,4,call.receiver,size,start)
            env.write(dest,env.read(source+start,copied))
            env.put(call.receiver+8,start+copied)
            return copied
        env.put(vt+0x3c,env.stub('CMemFile Read','thiscall',2,read))
        def construct(env,call):
            observe(env,2,call.receiver,call.arguments[0])
            env.put(call.receiver,vt,0,0,0,0,0,0,0,0,0)
            return call.receiver
        def attach(env,call):
            source,length,grow=call.arguments
            observe(env,3,call.receiver,length,grow)
            env.put(call.receiver+4,source,0,length)
            return 0
        def destroy(env,call):
            observe(env,5,call.receiver,env.get(call.receiver+8))
            return 0
        env.override(0x4ff5f9,construct)
        env.override(0x4ff645,attach)
        env.override(0x4ff682,destroy)
        return {'state':state}
    return setup
