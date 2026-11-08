"""Independent original lifecycle inputs and external service observations."""
from clawparity.cases import Case
from clawparity.fixtures import allocate


def cases(random_source):
    noise = bytes(random_source.randrange(1, 256) for _ in range(0x160))
    duration = random_source.randrange(1001, 5000)

    def setup(**options):
        def build(env):
            s = env.object(0x160, 'state', data=noise)
            o = env.object(0xa0, 'owner', fill=0)
            c = env.object(0x2c, 'services', fill=0)
            g = env.object(0x1c, 'graphics', fill=0)
            m = env.object(0x34, 'sound-manager', fill=0)
            rm = env.object(0x28, 'resource-manager', fill=0)
            log = env.object(4096, 'external-observations', fill=0)
            display = env.object(4, 'cursor-display-count', words=[options.get('cursor', 2)], fill=0)
            def record(env, call, result=0):
                n = env.get(log)
                env.put(log + 4 + n * 48, call.receiver, len(call.arguments), *call.arguments)
                env.put(log + 4 + n * 48 + 32, env.get(s), env.get(s+0x34), env.get(s+0x154), env.get(s+0xc))
                env.put(log, n + 1)
                return result
            def cursor(env, call):
                count = (env.get(display) + (1 if call.arguments[0] else -1)) & 0xffffffff
                env.put(display, count)
                record(env, call)
                return count
            env.override(0x546d54, cursor)
            env.override(0x546d50, lambda e, call: record(e, call, options.get('post', 1)))
            env.override(0x546ce4, lambda e, call: record(e, call, options.get('key_status', 0x8000) if options.get('key') and call.arguments[0] == options.get('key_code', 0x41) else 0))
            def clock(env, call):
                return record(env, call, (10000 + 1000 * env.calls_so_far(0x546df0)) & 0xffffffff)
            env.override(0x546df0, clock)
            for address, delta in ((0x5469e8, -1), (0x5469ec, 1)):
                def interlock(env, call, delta=delta):
                    value = (env.get(call.arguments[0]) + delta) & 0xffffffff
                    env.put(call.arguments[0], value)
                    return value
                env.override(address, interlock)
            env.put(s, 0x50c2d4, o, rm, c, 0)
            env.put(s + 0x2c, 0)
            env.put(s + 0x34, options.get('initialized', 1))
            env.put(s + 0x3c, 0, 0)
            env.put(s + 0x154, options.get('countdown', 2000))
            env.put(c + 4, g)
            env.put(c + 0x28, m)
            env.put(m + 0x18, 17)
            env.put(o + 0x30, c, rm)
            env.put(o + 0x7c, 640, 480)
            env.put(o + 0x9c, options.get('alternate', 0))
            window = env.object(8, 'window', words=[0x71345678, 0x1234abcd], fill=0)
            msg = env.object(0x248, 'message-owner', fill=0x7b)
            env.put(o + 4, window, msg if not options.get('error') else 0)
            inp = env.object(0x248, 'input', fill=0)
            env.put(inp + 0x1cc, 1 if options.get('key') else 0)
            env.put(inp + 0x1dc, *range(0x41, 0x4d))
            env.put(inp + 0x20c, options.get('previous_input', 0))
            env.put(inp + 0x1d4, options.get('extended_buttons', 0))
            env.put(0x537200, inp)
            env.put(0x53720c, options.get('elapsed', 1))
            env.put(0x532c0c, options.get('audio', 0))
            env.put(0x540e88, 0)
            def surface(label):
                w = env.object(0x100, label+'-wrapper', fill=0x25)
                vt = env.object(0x90, label+'-COM-vtable', fill=0)
                com = env.object(4, label+'-COM', words=[vt], fill=0)
                env.put(w + 8, com)
                env.put(w + 0x14, 480, 640, 640)
                env.put(w + 0x7c, 0, 0, 640, 480)
                for off, argc in ((0x14,6),(0x2c,3),(0x60,1),(0x6c,1)):
                    value = options.get('lost', 0) if off == 0x60 else options.get('restore', 0) if off == 0x6c else 0
                    env.put(vt+off, env.stub(label+str(off),'stdcall',argc,lambda e, call, value=value: record(e, call, value)))
                return w
            w0, w1 = surface('primary'), surface('secondary')
            r0, r1 = env.object(0x30,'renderer-primary', fill=0), env.object(0x30,'renderer-secondary', fill=0)
            env.put(r0+0x2c,w0)
            env.put(r1+0x2c,w1)
            env.put(g+0x10,r0,r1,0)
            if options.get('device'):
                d = env.object(0x80,'sound-device', fill=0)
                env.put(m+0x2c,d)
            else:
                d = env.object(0x80,'title-sound-device', fill=0)
            env.put(d+0x78, 1 if options.get('playing') else 0)
            if options.get('title'):
                vt = env.object(0x50, 'sound-buffer-vtable', fill=0)
                com = env.object(4, 'sound-buffer-COM', words=[vt], fill=0)
                b = env.object(0x2c, 'title-sound-instance', fill=0)
                a = env.object(0x14, 'title-sound-wrapper', fill=0)
                env.put(b+0xc, com, d)
                env.put(b+0x28,options.get('duration', duration))
                env.put(a+0x10,b)
                def status(env, call):
                    k=env.calls_so_far(env.get(vt+0x24))
                    env.put(call.arguments[1], 1 if options.get('playing') and k <= options.get('status_play_count', 1) else 0)
                    return record(env, call)
                env.put(vt+0x24,env.stub('GetStatus','stdcall',2,status))
                def volume(env, call):
                    env.put(call.arguments[1],0)
                    return record(env,call)
                env.put(vt+0x18,env.stub('GetVolume','stdcall',2,volume))
                for off,argc in ((0x48,1),(0x30,4),(0x34,2),(0x3c,2),(0x40,2),(0x44,2),(0x14,4),(0x0c,3)):
                    env.put(vt+off,env.stub('sound-COM'+str(off),'stdcall',argc,record))
                text = env.object(18,'TITLE-CString',words=[1,5,5],data=None)
                env.write(text+12,b'TITLE\0')
                h=0
                for byte in b'TITLE': h=(h*33+byte)&0xffffffff
                buckets=env.object(17*4,'sound-map-buckets', fill=0)
                node=env.object(16,'sound-map-node',words=[0,h%17,text+12,a], fill=0)
                env.put(buckets+4*(h%17),node)
                env.put(m+0x14,buckets)
            def directory(name):
                text=env.object(len(name)+1,name+'-name',data=name.encode()+b'\0')
                a=env.object(0x4c,name+'-directory', fill=0)
                buckets=env.object(5*16,name+'-child-buckets', fill=0)
                types=env.object(9*16,name+'-type-buckets', fill=0)
                env.put(a,text)
                env.put(a+0x3c,5,buckets,9,types)
                return a,buckets
            def child(parent, name, obj):
                buckets=parent[1]
                off=(len(name)%5)*16+8
                old=env.get(buckets+off)
                n=env.object(24,name+'-directory-node', fill=0)
                env.put(n+4,old)
                env.put(n+0x14,obj[0])
                env.put(buckets+off,n+4)
            root=directory('ROOT')
            level_name='LEVEL'+str(options.get('level', 1))
            level=directory(level_name); states=directory('STATES'); attract=directory('ATTRACT'); claw=directory('CLAW'); sounds=directory('SOUNDS'); screens=directory('SCREENS')
            for name,obj in ((level_name,level),('STATES',states),('CLAW',claw)):
                if options.get('missing') != name: child(root,name,obj)
            if options.get('missing') != 'ATTRACT': child(states,'ATTRACT',attract)
            if options.get('missing') != 'SOUNDS': child(attract,'SOUNDS',sounds)
            child(attract,'SCREENS',screens)
            env.put(rm+0x24,root[0])
            env.put(s+0x20,attract[0])
            if options.get('pcx'):
                import struct
                tag=0x504358
                typ=env.object(0x2c,'PCX-type',fill=0)
                names=env.object(19*16,'PCX-name-buckets',fill=0)
                env.put(typ,tag)
                env.put(typ+0x24,19,names)
                typenode=env.object(24,'PCX-type-node',fill=0)
                env.put(typenode+0x14,typ)
                env.put(env.get(screens[0]+0x48)+(tag%9)*16+8,typenode+4)
                resource=env.object(0x2c,'TITLE-PCX-resource',fill=0)
                name=env.object(6,'PCX-TITLE-name',data=b'TITLE\0')
                archive=env.object(0x24,'loaded-resource-archive',fill=0)
                data=bytearray(130)
                data[0:4]=bytes([10,5,1,8])
                struct.pack_into('<HHHH',data,4,0,0,1,0)
                data[0x41]=1
                struct.pack_into('<H',data,0x42,2)
                data[128:]=bytes(options.get('pixels', (0x37, 0x92)))
                pixels=env.object(2,'rendered-PCX-pixels',fill=0x6a)
                loaded=env.object(len(data),'loaded-PCX-bytes',data=bytes(data))
                env.put(resource,name)
                env.put(resource+8,typ)
                env.put(resource+0x14,len(data),loaded)
                env.put(resource+0x24,archive)
                namenode=env.object(24,'TITLE-PCX-name-node',fill=0)
                env.put(namenode+0x14,resource)
                env.put(names+(5%19)*16+8,namenode+4)
                manager=env.object(0x880,'surface-manager',fill=0)
                env.put(manager+0x474,8)
                env.put(c+0x1c,manager)
                env.put(r1,0x50e8e4)
                env.put(r1+0xc,c)
                env.put(w1+0x14,1,2,2)
                env.put(w1+0x7c,0,0,2,1)
                env.put(w1+0x30,pixels)
                methods=env.get(env.get(w1+8))
                def lock(env,call):
                    env.put(call.arguments[2]+8,1,2,2)
                    env.put(call.arguments[2]+0x24,pixels)
                    return record(env,call)
                env.put(methods+0x64,env.stub('PCX surface Lock','stdcall',5,lock))
                env.put(methods+0x80,env.stub('PCX surface Unlock','stdcall',2,record))
            if options.get('palette'):
                p=env.object(0x14,'palette-wrapper', fill=0)
                q=env.object(0x10,'palette', fill=0)
                com=env.object(4,'palette-COM', fill=0)
                vt=env.object(0x20,'palette-COM-vtable', fill=0)
                entries=env.object(1024,'palette-entries',data=bytes(random_source.randrange(1,256) for _ in range(1024)))
                env.put(p+0x10,q)
                env.put(q+4,com)
                env.put(q+0xc,entries)
                env.put(com,vt)
                def getentries(env,call):
                    env.write(call.arguments[4],env.read(entries+call.arguments[2]*4,call.arguments[3]*4))
                    return record(env,call)
                def setentries(env,call):
                    env.write(entries+call.arguments[2]*4,env.read(call.arguments[4],call.arguments[3]*4))
                    return record(env,call)
                env.put(vt+0x10,env.stub('GetEntries','stdcall',5,getentries))
                env.put(vt+0x18,env.stub('SetEntries','stdcall',5,setentries))
                env.put(s+0x2c,p)
            if options.get('no_services'): env.put(s+0xc,0)
            if options.get('allocation_failure'): env.override(0x4f63ec,allocate(fail=True))
            return dict(s=s,o=o)
        return build
    def case(label,fn,args=(),**options):
        return Case(label,fn,setup(**options),receiver=lambda t:t['s'],arguments=args)
    for missing in ('LEVEL1','STATES','ATTRACT','CLAW','SOUNDS',None):
        yield Case('initialize '+str(missing),0x408b30,setup(missing=missing),receiver=lambda t:t['s'],arguments=(lambda t:t['o'],1,0x5abccdef))
    yield Case('initialize empty sound allocation fails',0x408b30,setup(allocation_failure=True),receiver=lambda t:t['s'],arguments=(lambda t:t['o'],1,0xa35111))
    yield Case('initialize cursor already hidden',0x408b30,setup(cursor=0xffffffff),receiver=lambda t:t['s'],arguments=(lambda t:t['o'],1,0x82934501))
    for device in (False,True):
        yield case('cleanup device '+str(device),0x408bf0,device=device)
    yield case('destructor',0x429410,device=True)
    for flag in (0,1,0xabcdef00,0x12345681):
        yield case('delete flags '+hex(flag),0x4293f0,(flag,))
    for arg in (0,2,3,4,5,6,7,8,9,10,0xffffffff):
        yield case('enter no TITLE '+hex(arg),0x408c20,(arg,))
    yield case('enter cursor already hidden',0x408c20,(2,),cursor=0xfffffffa)
    yield case('enter alternate',0x408c20,(5,),alternate=1)
    for audio in (0,1):
        yield case('enter TITLE audio '+str(audio),0x408c20,(2,),title=True,audio=audio)
    for arg in (0,3,4): yield case('leave no TITLE '+str(arg),0x408d30,(arg,))
    yield case('enter TITLE actual playback',0x408c20,(5,),title=True,audio=1,playing=True)
    yield case('leave TITLE stopped',0x408d30,(2,),title=True)
    yield case('leave TITLE plays once',0x408d30,(2,),title=True,playing=True)
    yield case('leave TITLE loops no device',0x408d30,(2,),title=True,playing=True,status_play_count=3,allocation_failure=True)
    yield case('leave TITLE loops device',0x408d30,(2,),title=True,playing=True,status_play_count=3,device=True)
    yield case('leave palette fade',0x408d30,(3,),palette=True)
    for remaining,elapsed in ((0,0),(1,0),(1,1),(1,2),(0x80000000,0x7fffffff),(0xffffffff,0x80000000)):
        for alternate in (0,1):
            yield case('update countdown '+hex(remaining)+'/'+hex(elapsed)+' alt '+str(alternate),0x408e20,countdown=remaining,elapsed=elapsed,alternate=alternate)
    yield case('update action keyboard while waiting',0x408e20,key=True,key_code=0x45,countdown=2000)
    yield case('update TITLE stopped',0x408e20,title=True)
    yield case('update TITLE playing',0x408e20,title=True,playing=True)
    yield case('update sound tick',0x408e20,device=True)
    yield case('update restoration failure',0x408e20,lost=1,restore=0x80004005,error=True)
    yield case('restore fails',0x408f50,lost=1,restore=0x80004005)
    yield case('restore title resource miss',0x408f50)
    yield case('restore PCX cursor already hidden',0x408f50,pcx=True,cursor=0xfffffffc)
    yield case('restore loaded PCX succeeds',0x408f50,pcx=True)
    yield case('update restoration loaded PCX',0x408e20,pcx=True,lost=1)
    yield case('present inactive',0x408fa0,initialized=0,palette=True)
    yield case('present no palette',0x408fa0)
    yield case('present no services',0x408fa0,palette=True,no_services=True)
    yield case('present success',0x408fa0,palette=True)
    yield case('present cursor already hidden',0x408fa0,palette=True,cursor=0xffffffff)

    # Fixed matrices keep branch coverage independent of the random seed.
    for level in (0,2,3,4,5,6,7,8,9,10,11,12,13,14):
        for missing in (None,'LEVEL'+str(level)):
            yield Case(f'initialize level {level} missing {missing}',0x408b30,
                       setup(level=level,missing=missing),receiver=lambda t:t['s'],
                       arguments=(lambda t:t['o'],level,0x12340000+level))
    for arg in (1,2,3,4,5,6,7,8,9,10,0x7fffffff,0x80000000,0xfffffffe):
        for alternate,title,audio in ((0,False,0),(0,True,0),(0,True,1),(2,True,1),(0xffffffff,False,0)):
            yield case(f'enter matrix {arg:#x} alt {alternate:#x} title {title} audio {audio}',
                       0x408c20,(arg,),alternate=alternate,title=title,audio=audio,
                       countdown=0xa1b2c3d4,duration=0x10203040)
    for title_duration in (0,1,2999,3000,0x7fffffff,0x80000000,0xffffffff):
        for audio in (0,1):
            yield case(f'enter duration {title_duration:#x} audio {audio}',0x408c20,(2,),
                       title=True,audio=audio,duration=title_duration,countdown=0x5a4b3c2d)

    countdowns=((0,1),(2,1),(0x7fffffff,0x80000000),(0x80000000,0x80000000),
                (0x80000001,0x80000000),(0xfffffffe,0xffffffff),
                (0xffffffff,0),(0xffffffff,0xfffffffe),(0xffffffff,0xffffffff))
    for remaining,elapsed in countdowns:
        for alternate in (0,1,0x80000000):
            for title,playing in ((False,False),(True,False),(True,True)):
                for key in (False,True):
                    yield case(f'update matrix {remaining:#x}/{elapsed:#x} alt {alternate:#x} title {title} playing {playing} key {key}',
                               0x408e20,countdown=remaining,elapsed=elapsed,alternate=alternate,
                               title=title,playing=playing,key=key,key_code=0x45,post=0)

    # Directional keys occupy masked-out high bits. Action keys occupy low
    # bits, and a fresh action edge requests a command while the timer runs.
    for key_index in range(12):
        bit=(1 << (28+key_index)) if key_index < 4 else (1 << (key_index-4))
        for key_status in (1,0x8000,0x8001):
            for previous in (0,bit):
                yield case(f'update key {key_index} status {key_status:#x} previous {previous:#x}',
                           0x408e20,countdown=0x76543210,elapsed=0,key=True,
                           key_code=0x41+key_index,key_status=key_status,previous_input=previous,
                           extended_buttons=1)
    for alternate in (1,0xffffffff):
        yield case(f'update action posts alternate {alternate:#x}',0x408e20,
                   countdown=5000,elapsed=1,key=True,key_code=0x45,alternate=alternate)

    for flag in (2,3,0x80,0x81,0xff,0x100,0x101,0x80000000,0x80000001,0xfffffffe,0xffffffff):
        yield case(f'delete unrelated flag bits {flag:#x}',0x4293f0,(flag,),device=True)
    for cursor_count in (0,1,3,7,0xfffffffe,0xffffff80):
        yield Case(f'initialize cursor count {cursor_count:#x}',0x408b30,
                   setup(cursor=cursor_count),receiver=lambda t:t['s'],
                   arguments=(lambda t:t['o'],1,0xa1b2c3d4))
        for initialized in (0,1,2,0xffffffff):
            yield case(f'present cursor {cursor_count:#x} initialized {initialized:#x}',
                       0x408fa0,palette=True,cursor=cursor_count,initialized=initialized)
        yield case(f'restore rendered cursor {cursor_count:#x}',0x408f50,
                   pcx=True,cursor=cursor_count,pixels=(0x21,0xa7))
    for post in (0,1,0xffffffff):
        for alternate in (0,1,0xffffffff):
            yield case(f'update post result {post:#x} alternate {alternate:#x}',0x408e20,
                       countdown=0,post=post,alternate=alternate)
    for _ in range(24):
        remaining=random_source.randrange(0x100000000)
        elapsed=random_source.randrange(0x100000000)
        yield case(f'random unsigned countdown {remaining:#x}/{elapsed:#x}',0x408e20,
                   countdown=remaining,elapsed=elapsed,alternate=random_source.choice((0,1,0xffffffff)))
