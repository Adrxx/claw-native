"""Original-backed Booty story state and device boundary cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns, allocate


def physical(env):
    env.override(0x5469e4, lambda e, c: len(e.cstr(c.arguments[0])))
    def atomic(delta):
        def effect(e, c):
            a = c.arguments[0]
            v = (e.get(a) + delta) & 0xffffffff
            e.put(a, v)
            return v
        return effect
    env.override(0x5469e8, atomic(-1))
    env.override(0x5469ec, atomic(1))
    env.override(0x4a3050, returns(23))
    env.override(0x546df0,lambda e,c:1000*e.calls_so_far(c.function))
    env.override(0x546d50, returns(1))
    env.override(0x546ce4, returns(0))
    env.override(0x546d54, lambda e, c: (2 - e.calls_so_far(c.function)) & 0xffffffff)


def logic(state, level=3, timer=0, elapsed=17, index=0, enable=1, linked=True, slope=0.5, speed=20.0, x=0, target=100, countdown=0xffffffff, app=False, flags=0x5a,
          started=0, done=0, animation=0):
    def setup(env):
        physical(env)
        actor = env.object(0x240, 'actor', fill=0)
        obj = env.object(0x180, 'logic', fill=0)
        env.put(actor + 8, 0x42)
        env.put(actor + 0x40, flags)
        env.put(actor + 0x4c, x, 17)
        env.put(actor + 0x6c, obj)
        env.put(actor + 0x19c, animation)
        env.put(actor + 0x1a4, done)
        env.put(obj + 0x1c, state)
        env.put(obj + 0x2c, -40, target, -33, 144)
        env.put(obj + 0x64, enable, level)
        env.put(obj + 0x94, index)
        env.put(obj + 0xa4, started)
        env.put(obj + 0x130, timer, timer)
        env.write(obj + 0x140, struct.pack('<f', slope))
        env.write(obj + 0x160, struct.pack('<f', speed))
        if linked:
            child = env.object(0x180, 'linked-logic', fill=0x36)
            env.put(obj + 0x168, child)
        env.put(0x53720c, elapsed)
        env.put(0x523b50, countdown)
        env.put(0x5349a4, index)
        env.put(0x532c0c, 0)
        env.put(0x5430c4, elapsed)
        env.put(0x5371fc, 0)
        if app:
            registry = env.object(0x40, 'audio-registry', fill=0)
            env.put(registry + 0x18, 17)
            services = env.object(0x40, 'services', fill=0)
            env.put(services + 0x28, registry)
            application = env.object(0x48, 'application', fill=0)
            env.put(application + 0x30, services)
            env.put(0x5371fc, application)
        return {'actor': actor, 'logic': obj}
    return setup


def decoder(kind=0, size=64, resource=False):
    def setup(env):
        physical(env)
        surface = env.object(0xc0, 'surface', fill=0)
        env.put(surface + 0x14, 7, 11)
        palette = env.object(0x880, 'palette', fill=0)
        data = env.object(0x500, 'encoded-buffer', fill=0)
        env.put(data + 8, 3)
        if not resource:
            return {'receiver': surface, 'args': (palette, data, kind, size, 19)}
        owner = env.object(0x30, 'display-owner', fill=0)
        env.put(owner + 0x1c, palette)
        image = env.object(0x40, 'image', fill=0)
        env.put(image + 0xc, owner)
        env.put(image + 0x2c, surface)
        record = env.object(0x30, 'resource', fill=0)
        typ = env.object(4, 'type', words=[kind])
        backing = env.object(0x28, 'backing', fill=0)
        env.put(record + 8, typ)
        env.put(record + 0x14, size)
        env.put(record + 0x24, backing)
        if size:
            env.put(backing + 0x20, data)
        return {'receiver': image, 'args': (record,)}
    return setup


def basic_story(posted=0, countdown=1, mode=0, level=3):
    def setup(env):
        physical(env)
        story = env.object(0x180, 'story', fill=0)
        env.put(story, 0x50b544)
        env.put(story + 0x14, level)
        env.put(story + 0x154, 0, posted, env.get(0x52e1c8), 0, 0, env.get(0x52e1c8))
        wrapper = env.object(8, 'window-wrapper', fill=0)
        window = env.object(8, 'window', words=[0x19, 0x10203040])
        env.put(wrapper + 4, window)
        app = env.object(0x48, 'application', fill=0)
        env.put(app + 4, wrapper)
        services = env.object(0x40, 'services', fill=0)
        registry = env.object(0x40, 'audio-registry', fill=0)
        env.put(registry + 0x18, 17)
        env.put(services + 0x28, registry)
        env.put(app + 0x30, services)
        env.put(story + 4, app)
        env.put(0x5371fc, app)
        env.put(0x523b50, countdown)
        env.put(0x5349a0, mode)
        env.put(0x53499c, env.get(0x52e1c8))
        env.put(0x532c0c, 0)
        return {'receiver': story, 'app': app, 'services': services}
    return setup


def cases(random_source):
    yield Case('unused stdcall argument', 0x40bd50, arguments=(0xa5a5a5a5,))
    for key in (0, 0x1b, 0x20, 0xd, 0xffffffff, 0x11b):
        for posted in (0, 7):
            yield Case(f'key {key:x} posted {posted}', 0x40bf30, basic_story(posted), receiver=lambda t:t['receiver'], arguments=(key, 0x51425364))
    for countdown in (0, 1, 0xffffffff):
        for level in (3, 14):
            for mode in (0, 1):
                yield Case(f'voice lookup {countdown} {level} {mode}', 0x40bfd0, basic_story(countdown=countdown, level=level, mode=mode), receiver=lambda t:t['receiver'])
    for state in (0, 1, 5, 6, 0x232f, 0x2330, 0x2331, 0xffffffff):
        for level in (1, 3, 5, 7, 9, 11):
            yield Case(f'curl state {state:x} level {level}', 0x40c150, logic(state, level, timer=19, index=(level-1)//2), arguments=(lambda t:t['actor'],))
    for timer in (0, 16, 17, 18, 0x80000000, 0xffffffff):
        for enable in (0, 1):
            yield Case(f'curl wait {timer} enable {enable}', 0x40c150, logic(5, timer=timer, enable=enable), arguments=(lambda t:t['actor'],))
    for speed in (-200.0, -1.0, 0.0, 1.0, 200.0):
        for x in (-100, 0, 100, 150):
            yield Case(f'curl motion {speed} x{x}', 0x40c150, logic(0x2331, timer=19, speed=speed, x=x, app=True), arguments=(lambda t:t['actor'],))
    for state in (0, 1, 0x232b, 0x232d, 0x232e, 0x232f, 0x2330, 0x2331, 0x2332, 0x2333, 0xffffffff):
        for level in (1, 3, 5, 9, 11, 13, 0xffffffff):
            yield Case(f'map state {state:x} level{level}', 0x40c4f0, logic(state, enable=level, level=level, index=0, timer=19), arguments=(lambda t:t['actor'],))
    for timer in (0, 17, 18, 0x80000000):
        for linked in (False, True):
            yield Case(f'map linked timer{timer} link{linked}', 0x40c4f0, logic(0x232e, timer=timer, linked=linked), arguments=(lambda t:t['actor'],))
    for level in (-3, -1, 0, 1, 3, 5, 11, 13, 15, 17, 19, 0x7fffffff):
        yield Case(f'gem init level{level}', 0x40d1a0, logic(0, level=level), arguments=(lambda t:t['actor'],))
    for state in (1, 5, 0x232f, 0xffffffff):
        for timer in (0, 17, 18, 0xffffffff):
            for done in (0, 1):
                yield Case(f'gem update {state:x} timer{timer} done{done}', 0x40d1a0, logic(state, timer=timer, done=done, app=True), arguments=(lambda t:t['actor'],))
    for kind in (0, 1, 2, 3, 4, 5, 0xffffffff):
        for size in (0, 1, 64):
            yield Case(f'decoder type{kind} size{size}', 0x4b95b0, decoder(kind,size), receiver=lambda t:t['receiver'], arguments=tuple(lambda t,i=i:t['args'][i] for i in range(5)))
    for kind in (0, 0x424d50, 0x504358, 0x524944, 0x504944, 0xffffffff):
        for size in (0, 64):
            yield Case(f'resource type{kind:x} size{size}', 0x4d4190, decoder(kind,size,True), receiver=lambda t:t['receiver'], arguments=(lambda t:t['args'][0],))
    for _ in range(16):
        state = random_source.choice((0, 5, 0x232e, 0x2332, 0xffffffff))
        yield Case(f'random map {state:x} {_}', 0x40c4f0, logic(state, enable=random_source.randrange(1,15), index=random_source.randrange(-2,33), timer=random_source.randrange(0,50), elapsed=random_source.randrange(0,50)), arguments=(lambda t:t['actor'],))

    for stage in (0, 1, 2, 3):
        def display_setup(env, stage=stage):
            physical(env)
            display = env.object(0x40, 'display', fill=0)
            images = [env.object(0x40, f'image-{i}', fill=0) for i in range(3)]
            surfaces = [env.object(0xc0, f'surface-{i}', fill=0) for i in range(3)]
            vtable = 0x50e8e4
            for image, surface in zip(images, surfaces):
                env.put(image, vtable)
                env.put(image + 0x2c, surface)
                iface = env.object(4, 'directdraw-surface', fill=0)
                methods = env.object(0x90, 'directdraw-vtable', fill=0)
                env.put(iface, methods)
                env.put(surface + 8, iface)
                env.put(methods + 0x14, env.stub('DirectDraw.Blt', 'stdcall', 6, returns(0)))
                env.put(methods + 0x1c, env.stub('DirectDraw.BltFast', 'stdcall', 6, returns(0)))
            env.put(display + 0x10, *images)
            if stage == 0:
                env.put(display + 0x10, 0)
            elif stage == 1:
                env.put(images[0] + 0x2c, 0)
            elif stage == 2:
                env.put(images[1] + 0x2c, 0)
            return {'receiver': display, 'image': images[1], 'surface': surfaces[1]}
        yield Case(f'copy primary stage{stage}', 0x4ca9e0, display_setup, receiver=lambda t:t['receiver'], arguments=(lambda t:t['image'],))
    for selector in (0, 1, 2, 3, 0xffffffff):
        for present in (False, True):
            def display_select(env, present=present):
                physical(env)
                display = env.object(0x40, 'display', fill=0)
                surface = env.object(0xc0, 'surface', fill=0)
                env.put(surface + 8, env.object(4, 'type', words=[0]))
                env.put(surface + 0x14, 17, 29)
                image = env.object(0x40, 'image', fill=0)
                env.put(image, 0x50e8e4)
                if present:
                    env.put(display + 0x14, image, image)
                return {'receiver': display, 'surface': surface}
            yield Case(f'select target {selector} present{present}', 0x4ca900, display_select, receiver=lambda t:t['receiver'], arguments=(lambda t:t['surface'], selector))
    def display_null(env):
        physical(env)
        return {'receiver': env.object(0x40, 'display', fill=0)}
    yield Case('null back release', 0x4caa90, display_null, receiver=lambda t:t['receiver'])

    def audio_map(env, services, playing=False):
        registry = env.get(services + 0x28)
        buckets = env.object(4, 'audio-buckets', fill=0)
        env.put(registry + 0x14, buckets, 1)
        head = 0
        for name in ('BOOTY_GEM', 'BOOTY_AMMAKE', 'BOOTY_IMPACT3', 'BOOTY_CURLING1', 'BOOTY_FOOT2', 'BOOTY_FOOT3', 'BOOTY_AMULET', 'BOOTY_MAPLOOP', 'VOICE_CASE', ''):
            key = env.object(len(name) + 1, 'audio-key', data=name.encode() + b'\0')
            entry = env.object(0x20, 'audio-entry', fill=0)
            audio = env.object(0x40, 'audio-instance', fill=0)
            device_owner = env.object(0x80, 'audio-owner', fill=0)
            env.put(audio + 0x10, device_owner)
            if playing:
                env.put(device_owner + 0x78, 1)
                env.put(device_owner + 0x24,10)
                device = env.object(4, 'directsound-buffer', fill=0)
                methods = env.object(0x60, 'directsound-vtable', fill=0)
                env.put(device, methods)
                env.put(audio + 0xc, device)
                def status(e,c,state=playing.get(name,0) if isinstance(playing,dict) else 1):
                    e.put(c.arguments[1], state)
                    return 0
                env.put(methods + 0x24, env.stub('DirectSound.GetStatus', 'stdcall', 2, status))
                def volume(e,c):
                    e.put(c.arguments[1],0xfffff830)
                    return 0
                env.put(methods+0x18,env.stub('DirectSound.GetVolume','stdcall',2,volume))
                env.put(methods + 0x48, env.stub('DirectSound.Stop', 'stdcall', 1, returns(0)))
                for off, argc in ((0x30,4),(0x34,2),(0x38,2),(0x3c,2),(0x40,2),(0x44,2)):
                    env.put(methods + off, env.stub(f'DirectSound.method{off:x}', 'stdcall', argc, returns(0)))
            env.put(entry + 0x10, audio)
            node = env.object(0x10, 'audio-map-node', words=[head, 0x314159, key, entry])
            head = node
        env.put(buckets, head)

    for playing in (False, True):
        for state in (0x2330, 0x2331):
            def curl_audio(env, playing=playing, state=state):
                t = logic(state, timer=0, speed=200.0, x=100, app=True)(env)
                audio_map(env, env.get(env.get(0x5371fc) + 0x30), playing)
                env.put(0x532c0c, 1)
                return t
            yield Case(f'curl audio state{state:x} playing{playing}', 0x40c150, curl_audio, arguments=(lambda t:t['actor'],))
        for started in (0, 1):
            for mode in (0,1):
                def voice_audio(env, playing=playing, started=started, mode=mode):
                    t = basic_story(countdown=0, mode=mode)(env)
                    env.put(t['receiver'] + 0x154, started)
                    text = b'VOICE_CASE\0'
                    block = env.object(12 + len(text), 'voice-string', words=[1,len(text)-1,len(text)-1])
                    env.write(block + 12, text)
                    env.put(t['receiver'] + 0x168, block + 12)
                    audio_map(env, t['services'], playing)
                    env.put(0x532c0c, 0 if playing else 1)
                    return t
                yield Case(f'voice found playing{playing} started{started} mode{mode}', 0x40bfd0, voice_audio, receiver=lambda t:t['receiver'])
        for level in (3,17):
            for started in (0,1):
                def gem_audio(env, playing=playing, level=level, started=started):
                    t = logic(5, timer=0, level=level, started=started, app=True)(env)
                    audio_map(env, env.get(env.get(0x5371fc) + 0x30), playing)
                    env.put(0x532c0c, 0 if playing else 1)
                    return t
                yield Case(f'gem audio playing{playing} level{level} started{started}', 0x40d1a0, gem_audio, arguments=(lambda t:t['actor'],))

    def story_display(env, valid=True, width=0):
        t = basic_story()(env)
        services=t['services']
        env.put(t['receiver'] + 0xc, services)
        display=env.object(0x40,'display',fill=0)
        images=[]
        for i in range(3):
            im=env.object(0x40,f'image-{i}',fill=0)
            env.put(im,0x50e8e4)
            env.put(im+0xc,services)
            env.put(im+0x10,width,17)
            if valid:
                surf=env.object(0xc0,'surface',fill=0)
                iface=env.object(4,'directdraw-surface',fill=0)
                methods=env.object(0x90,'directdraw-vtable',fill=0)
                env.put(iface,methods)
                env.put(surf+8,iface)
                for off,argc in ((0x14,6),(0x1c,6),(0x2c,3),(0x60,1),(0x6c,1)):
                    env.put(methods+off,env.stub(f'DirectDraw.method{off:x}', 'stdcall',argc,returns(0)))
                env.put(im+0x2c,surf)
            images.append(im)
        env.put(display+0x10,*images)
        env.put(services+4,display)
        manager=env.object(0x100,'actor-manager',fill=0)
        env.put(manager,0x513c20)
        env.put(services+8,manager)
        t.update(display=display,images=images)
        return t
    for flags in (0,1,2,3,0x100):
        def destroy_setup(env):
            return story_display(env)
        yield Case(f'delete flags{flags}',0x40b600,destroy_setup,receiver=lambda t:t['receiver'],arguments=(flags,))
    for function in (0x40b620,0x40bc80,0x40bf80,0x40bca0):
        yield Case(f'story default direct{function:x}',function,story_display,receiver=lambda t:t['receiver'],arguments=(0x3141,) if function==0x40bca0 else ())
    for valid,width in ((True,11),(False,0)):
        def ds(env,valid=valid,width=width):
            return story_display(env,valid,width)
        for copy in (0,1,0x80000000):
            yield Case(f'back prepare valid{valid} width{width} copy{copy}',0x4caa20,ds,receiver=lambda t:t['display'],arguments=(copy,))
        yield Case(f'back release valid{valid}',0x4caa90,ds,receiver=lambda t:t['display'])
    for initialized in (0,1):
        def bed(env, initialized=initialized):
            t=story_display(env)
            env.put(t['receiver']+0x34,initialized)
            return t
        yield Case(f'story restore initialized{initialized}',0x40bed0,bed,receiver=lambda t:t['receiver'])
    def failed_init(env):
        t=story_display(env)
        root=env.object(0x50,'resource-root',fill=0)
        directory=env.object(0x80,'root-directory',fill=0)
        buckets=env.object(5*16,'directory-index',fill=0)
        env.put(root+0x24,directory)
        env.put(directory+0x40,buckets)
        env.put(t['app']+0x34,root)
        env.put(t['receiver']+0x20,directory)
        return t
    yield Case('initializer missing level directory',0x40b860,failed_init,receiver=lambda t:t['receiver'],arguments=(lambda t:t['app'],3,0x1234))
    yield Case('display restore missing image directory',0x40be60,failed_init,receiver=lambda t:t['receiver'])
    for x,target,speed in ((99,100,200.0),(101,100,-200.0)):
        yield Case(f'curl clamp {x}',0x40c150,logic(0x2331,x=x,target=target,speed=speed),arguments=(lambda t:t['actor'],))
    for index in (29,):
        for timer in (0,17):
            yield Case(f'last map footstep timer{timer}',0x40c4f0,logic(0x232c,timer=timer,index=index,app=True),arguments=(lambda t:t['actor'],))

    def actor_factory(env, services):
        manager=env.object(0x100,'actor-manager',fill=0)
        env.put(manager,0x513c20)
        env.put(manager+0xc,services)
        env.put(manager+0x28,10)
        env.put(services+8,manager)
        for offset in (0x10,0x14,0x2c):
            registry=env.object(0x100,'asset-registry',fill=0)
            env.put(registry+0x18,1)
            env.put(services+offset,registry)
        registry=env.get(services+0x14)
        buckets=env.object(4,'logic-buckets',fill=0)
        env.put(registry+0x14,buckets)
        head=0
        for name,fn in (('MapProgressLogic',0x40c4f0),('AmuletGemLogic',0x40d1a0),('MapPieceLogic',0x40c150)):
            key=env.object(len(name)+1,'logic-name',data=name.encode()+b'\0')
            template=env.object(0x20,'logic-template',fill=0)
            env.put(template+0x10,fn)
            node=env.object(0x10,'logic-node',words=[head,0,key,template])
            head=node
        env.put(buckets,head)
        return manager
    for index in (0,1,28):
        for disabled in (0,1):
            def map_next(env,index=index,disabled=disabled):
                t=logic(0x232c,index=index,timer=0,app=True)(env)
                services=env.get(env.get(0x5371fc)+0x30)
                actor_factory(env,services)
                registry=env.get(services+0x28)
                env.put(registry+0x30,disabled)
                audio_map(env,services,False)
                env.put(0x532c0c,1)
                return t
            yield Case(f'map creates next index{index} disabled{disabled}',0x40c4f0,map_next,arguments=(lambda t:t['actor'],))
    def gem_create(env):
        t=logic(5,level=13,timer=0,done=1,app=True)(env)
        actor_factory(env,env.get(env.get(0x5371fc)+0x30))
        return t
    yield Case('gem thirteen creates successor',0x40d1a0,gem_create,arguments=(lambda t:t['actor'],))
    def bmp_success(env):
        t=decoder(1,64)(env)
        surface=t['receiver']
        palette,data,kind,size,option=t['args']
        env.put(surface+0x14,1,1,4)
        env.put(surface+0xa8,1)
        env.put(palette+0x474,8)
        env.write(data+0xa,struct.pack('<I',54))
        env.write(data+0x12,struct.pack('<IIH',1,1,1))
        env.write(data+0x1c,struct.pack('<H',8))
        env.write(data+54,b'\x6d\x21\x32\x43')
        iface=env.object(4,'directdraw-surface',fill=0)
        methods=env.object(0x90,'directdraw-vtable',fill=0)
        env.put(iface,methods)
        env.put(surface+8,iface)
        pixels=env.object(4,'pixels',fill=0x55)
        def lock(e,c):
            e.put(surface+0x30,pixels)
            return 0
        env.put(methods+0x64,env.stub('DirectDraw.Lock','stdcall',5,lock))
        env.put(methods+0x80,env.stub('DirectDraw.Unlock','stdcall',2,returns(0)))
        return t
    yield Case('BMP successful one pixel decode',0x4b95b0,bmp_success,receiver=lambda t:t['receiver'],arguments=tuple(lambda t,i=i:t['args'][i] for i in range(5)))

    def graphics_manager(env, services):
        manager=env.object(0x880,'graphics-manager',fill=0)
        env.put(manager+0x3d0,10)
        env.put(manager+0x474,8)
        methods=env.object(0x90,'directdraw-vtable',fill=0)
        dd=env.object(4,'directdraw',words=[methods])
        def create(e,c):
            desc=e.object(0x6c,'surface-description',data=e.read(c.arguments[1],0x6c))
            interface=e.object(8,'directdraw-surface',words=[methods,desc])
            e.put(c.arguments[2],interface)
            return 0
        def describe(e,c):
            e.write(c.arguments[1],e.read(e.get(c.arguments[0]+4),0x6c))
            e.put(c.arguments[1]+0x54,8)
            e.put(c.arguments[1]+0x10,32)
            return 0
        env.put(methods+0x18,env.stub('DirectDraw.CreateSurface','stdcall',4,create))
        env.put(methods+0x58,env.stub('DirectDraw.GetSurfaceDesc','stdcall',2,describe))
        for off,argc in ((0x14,6),(0x1c,6),(0x60,1),(0x6c,1),(0x08,1)):
            env.put(methods+off,env.stub(f'DirectDraw.graphics{off:x}','stdcall',argc,returns(0)))
        env.put(manager,dd)
        env.put(services+0x1c,manager)
        return manager
    for copy in (0,1):
        def resized(env):
            t=story_display(env,False,11)
            graphics_manager(env,t['services'])
            # A real front surface supplies the source of the final blit.
            surf=env.object(0xc0,'front-source',fill=0)
            env.put(t['images'][1]+0x2c,surf)
            return t
        yield Case(f'back successful resize copy{copy}',0x4caa20,resized,receiver=lambda t:t['display'],arguments=(copy,))

    def directory(env,name,children=()):
        d=env.object(0x80,'directory-'+name,fill=0)
        key=env.object(len(name)+1,'directory-name',data=name.encode()+b'\0')
        env.put(d,key)
        table=env.object(80,'directory-buckets',fill=0)
        env.put(d+0x3c,5,table)
        env.put(d+0x44,5,env.object(80,'resource-buckets',fill=0))
        for child in children:
            childname=env.cstr(env.get(child))
            bucket=(len(childname)%5)*16+8
            node=env.object(0x18,'directory-node',fill=0)
            env.put(node+4,env.get(table+bucket))
            env.put(node+0x14,child)
            env.put(table+bucket,node+4)
        return d
    def full_story(level=3,stage=5):
        def setup(env):
            t=story_display(env)
            services=t['services']
            actor_factory(env,services)
            image_registry=env.get(services+0x10)
            env.put(image_registry,0x513b88)
            env.put(image_registry+0xc,services)
            env.put(image_registry+0x28,10)
            images=directory(env,'IMAGES')
            anis=directory(env,'ANIS')
            booty=directory(env,'BOOTY',([images] if stage>=3 else [])+([anis] if stage>=4 else []))
            states=directory(env,'STATES',[booty] if stage>=1 else [])
            claw=directory(env,'CLAW')
            lev=directory(env,f'LEVEL{level}')
            rootdir=directory(env,'ROOT',[states]+([claw] if stage>=2 else [])+[lev])
            root=env.object(0x50,'resource-root',fill=0)
            env.put(root+0x24,rootdir)
            env.put(t['app']+0x34,root)
            env.put(t['receiver']+8,root)
            env.put(t['receiver']+0x20,booty)
            env.put(0x5349a4,0)
            return t
        return setup
    for stage in range(6):
        yield Case(f'initializer resource stage{stage}',0x40b860,full_story(stage=stage),receiver=lambda t:t['receiver'],arguments=(lambda t:t['app'],3,0x5678))
    for level in (0,1,2,5,9,10,11,12,13,14,15):
        yield Case(f'initializer level{level}',0x40b860,full_story(level),receiver=lambda t:t['receiver'],arguments=(lambda t:t['app'],level,0x5678))
    for mode in (0,1):
        for enabled in (0,1):
            def start_audio(env,mode=mode,enabled=enabled):
                t=story_display(env)
                env.put(0x5349a0,mode)
                env.put(0x532c0c,enabled)
                audio_map(env,t['services'],False)
                return t
            yield Case(f'start audio mode{mode} enabled{enabled}',0x40bca0,start_audio,receiver=lambda t:t['receiver'],arguments=(0x7777,))
    yield Case('map countdown subtract',0x40c4f0,logic(0x232c,timer=18,index=29,app=True),arguments=(lambda t:t['actor'],))

    for countdown in (0,1,17,18,0x80000000,0xffffffff):
        for pressed in (0,1):
            for posted in (0,7):
                def tick(env,countdown=countdown,pressed=pressed,posted=posted):
                    t=story_display(env)
                    actor_factory(env,t['services'])
                    renderer=env.object(0x100,'renderer',fill=0)
                    env.put(renderer,0x513a70)
                    env.put(t['services']+0xc,renderer)
                    inputobj=env.object(0x248,'input',fill=0)
                    if pressed:
                        env.put(inputobj+0x1cc,1)
                        env.put(inputobj+0x1dc,0x20)
                        env.override(0x546ce4,returns(0x8000))
                    env.put(0x537200,inputobj)
                    env.put(0x5430d0,3)
                    env.put(0x53720c,17)
                    env.put(0x523b50,countdown)
                    env.put(t['receiver']+0x158,posted)
                    return t
                yield Case(f'tick countdown{countdown} pressed{pressed} posted{posted}',0x40bd60,tick,receiver=lambda t:t['receiver'])
    for valid in (False,True):
        def restore(env,valid=valid):
            t=full_story()(env)
            env.put(t['receiver']+0x34,1)
            # Palette object stays coherent, while its hardware interface is absent.
            image=env.object(0x40,'palette-image',fill=0)
            palette=env.object(0x480,'image-palette',fill=0)
            colors=env.object(0x400,'palette-colors',fill=0x35 if valid else 0x67)
            saved=env.object(0x400,'saved-palette-colors',fill=0x74)
            methods=env.object(0x20,'directdraw-palette-vtable',fill=0)
            iface=env.object(4,'directdraw-palette',words=[methods])
            env.put(methods+0x10,env.stub('DirectDrawPalette.GetEntries','stdcall',5,returns(0)))
            env.put(methods+0x18,env.stub('DirectDrawPalette.SetEntries','stdcall',5,returns(0)))
            env.put(palette+4,iface)
            env.put(palette+0xc,colors,saved)
            env.put(image,0x513d78)
            env.put(image+0xc,t['services'])
            env.put(image+0x10,palette)
            env.put(t['services']+0x18,env.object(0x68,'palette-registry',fill=0))
            env.put(t['receiver']+0x2c,image)
            return t
        yield Case(f'restore retained palette valid{valid}',0x40bed0,restore,receiver=lambda t:t['receiver'])
    for stage in (3,4):
        yield Case(f'restore directory stage{stage}',0x40be60,full_story(stage=stage),receiver=lambda t:t['receiver'])

    def background_busy(env):
        t=basic_story(countdown=0)(env)
        text=b'VOICE_CASE\0'
        block=env.object(12+len(text),'voice-string',words=[1,len(text)-1,len(text)-1])
        env.write(block+12,text)
        env.put(t['receiver']+0x154,1)
        env.put(t['receiver']+0x168,block+12)
        audio_map(env,t['services'],{'BOOTY_AMULET':1})
        bg=b'BOOTY_AMULET\0'
        block2=env.object(12+len(bg),'background-string',words=[1,len(bg)-1,len(bg)-1])
        env.write(block2+12,bg)
        env.put(0x53499c,block2+12)
        return t
    yield Case('background sound keeps countdown alive',0x40bfd0,background_busy,receiver=lambda t:t['receiver'])
    def lost_primary(env):
        t=full_story()(env)
        surface=env.get(t['images'][0]+0x2c)
        interface=env.get(surface+8)
        methods=env.get(interface)
        env.put(methods+0x60,env.stub('DirectDraw.IsLost','stdcall',1,returns(1)))
        env.put(methods+0x6c,env.stub('DirectDraw.Restore','stdcall',1,returns(1)))
        return t
    yield Case('restore primary device fails',0x40be60,lost_primary,receiver=lambda t:t['receiver'])

    def restore_incomplete_images(env):
        t=full_story()(env)
        registry=env.get(t['services']+0x10)
        key=env.object(6,'image-set-key',data=b'BOOTY\0')
        imageset=env.object(0x70,'image-set',fill=0)
        env.put(imageset,0x513cf8)
        env.put(imageset+0x14,env.object(4,'image-elements',words=[env.object(0x40,'retained-image',fill=0)]),1)
        env.put(imageset+0x64,0,0)
        node=env.object(0x10,'image-set-node',words=[0,0,key,imageset])
        buckets=env.object(4,'image-set-buckets',words=[node])
        env.put(registry+0x14,buckets,1)
        return t
    yield Case('restore image set has missing retained frame',0x40be60,restore_incomplete_images,receiver=lambda t:t['receiver'])

    # The initializer receives a previously used receiver. Every output starts
    # distinct from the value it is about to publish.
    for level in (1,2,3,9,10,11,12,13,14):
        for old_mode in (0,7):
            def reused_initialization(env,level=level,old_mode=old_mode):
                t=full_story(level)(env)
                olddir=directory(env,'PREVIOUS')
                env.put(t['receiver']+0x20,olddir,directory(env,'OLDCLAW'))
                env.put(t['receiver']+0x154,0x71425364,0x26374859)
                env.put(t['receiver']+0x160,env.object(0x80,'old-actor',fill=0x28),env.object(0x80,'old-actor-two',fill=0x71))
                env.put(0x5349a0,old_mode)
                env.put(0x523b50,0x12536789)
                def new_memory(e,c):
                    return e.object(c.arguments[0],'uninitialized-allocation',fill=0x46)
                env.override(0x4f63ec,new_memory)
                return t
            yield Case(f'reused initializer level{level} mode{old_mode}',0x40b860,reused_initialization,receiver=lambda t:t['receiver'],arguments=(lambda t:t['app'],level,0x16273849))

    # Keep back/front choices distinguishable even when both are present.
    for selector in (1,2,0xffffffff):
        def distinct_targets(env):
            physical(env)
            display=env.object(0x40,'display',fill=0)
            front=env.object(0x40,'front-image',fill=0)
            back=env.object(0x40,'back-image',fill=0)
            env.put(front,0x50e8e4)
            env.put(back,0x50e8e4)
            resource=env.object(0x30,'unsupported-resource',fill=0)
            env.put(resource+8,env.object(4,'unknown-image-type',words=[0x17432569]))
            env.put(display+0x14,front,back)
            return {'receiver':display,'resource':resource}
        yield Case(f'distinct front and back selection {selector}',0x4ca900,distinct_targets,receiver=lambda t:t['receiver'],arguments=(lambda t:t['resource'],selector))

    for _ in range(32):
        words=[random_source.randrange(1,0xffffffff) for i in range(8)]
        level=random_source.choice((1,3,5,7,9,11))
        state=random_source.choice((0,5,0x2330,0x2331))
        def textured_logic(env,words=words,level=level,state=state):
            t=logic(state,level=level,index=(level-1)//2,timer=words[0],elapsed=words[1],speed=(words[2]%10001-5000)/8,slope=(words[3]%701-350)/16,x=words[4]%401-200,target=words[5]%401-200,enable=words[6],countdown=words[7],app=True)(env)
            # These are real scalar fields used or overwritten by the states.
            env.put(t['logic']+0x2c,words[2],words[5],words[3],words[4])
            return t
        yield Case(f'seeded curl scalar state{state:x} {_}',0x40c150,textured_logic,arguments=(lambda t:t['actor'],))

    def successful_assets(env,services):
        # These are concrete original image-set and animation models. Their
        # elements are live objects with distinct data and independent arrays.
        for offset,names in ((0x10,('BOOTY_MAPPIECE_LEVEL013_GEMBLUE','BOOTY_MAPPIECE_LEVEL013_GEMRED','BOOTY_MAPPIECE')), (0x2c,('BOOTY_GEMB13','BOOTY_GEMR13','BOOTY_GEM2','BOOTY_GEM4'))):
            registry=env.get(services+offset)
            buckets=env.object(4,'populated-asset-buckets',fill=0)
            env.put(registry+0x14,buckets,1)
            head=0
            for i,name in enumerate(names):
                keyblock=env.object(12+len(name)+1,'asset-key',words=[1,len(name),len(name)])
                key=keyblock+12
                env.write(key,name.encode()+b'\0')
                asset=env.object(0x80,'asset-model',fill=0)
                if offset==0x10:
                    item=env.object(0x40,'sprite-image',fill=0x31+i)
                    env.put(item,0x50e8e4)
                    array=env.object(8,'sprite-elements',words=[0,item])
                    env.put(asset,0x513cf8)
                    env.put(asset+0x14,array,2)
                    env.put(asset+0x64,1,1)
                else:
                    frame=env.object(0x30,'animation-frame',fill=0)
                    env.put(frame+0xc,9)
                    env.put(frame+0x18,37+i,0x5123+i)
                    array=env.object(4,'animation-frames',words=[frame])
                    env.put(asset+0xc,array,1)
                node=env.object(0x10,'asset-node',words=[head,0,key,asset])
                head=node
            env.put(buckets,head)
    for level in (2,4,13):
        def initialized_assets(env,level=level):
            t=full_story(level)(env)
            successful_assets(env,t['services'])
            env.put(t['receiver']+0x154,11,22)
            env.put(0x5349a0,99)
            env.put(0x523b50,0x778899)
            return t
        yield Case(f'initializer successful animation level{level}',0x40b860,initialized_assets,receiver=lambda t:t['receiver'],arguments=(lambda t:t['app'],level,0x5678))
    def successor_assets(env):
        t=gem_create(env)
        services=env.get(env.get(0x5371fc)+0x30)
        successful_assets(env,services)
        return t
    yield Case('gem successor selects actual sprite and animation',0x40d1a0,successor_assets,arguments=(lambda t:t['actor'],))

    for enabled in (0,1,0x80000000):
        for mode in (0,1):
            def physical_audio(env,enabled=enabled,mode=mode):
                t=story_display(env)
                audio_map(env,t['services'],{'BOOTY_AMULET':0,'BOOTY_MAPLOOP':0})
                env.put(0x532c0c,enabled,37)
                env.put(0x5349a0,mode)
                return t
            yield Case(f'physical audio start enabled{enabled} mode{mode}',0x40bca0,physical_audio,receiver=lambda t:t['receiver'],arguments=(0x7788,))

    for kind in (0x424d50,0x504358,0x504944):
        def cached_resource(env,kind=kind):
            t=decoder(kind,64,True)(env)
            resource=t['args'][0]
            cached=env.object(0x500,'cached-resource-bytes',fill=0)
            env.put(cached+8,3)
            env.put(resource+0x18,cached)
            env.put(env.get(resource+0x24)+0x20,0)
            return t
        yield Case(f'cached image releases bytes type{kind:x}',0x4d4190,cached_resource,receiver=lambda t:t['receiver'],arguments=(lambda t:t['args'][0],))
    def valid_cached_bitmap(env):
        t=bmp_success(env)
        surface=t['receiver']
        palette,data,kind,size,option=t['args']
        image=env.object(0x40,'bitmap-image',fill=0)
        display_owner=env.object(0x30,'bitmap-display-owner',fill=0)
        env.put(display_owner+0x1c,palette)
        env.put(image+0xc,display_owner)
        env.put(image+0x2c,surface)
        record=env.object(0x30,'bitmap-resource',fill=0)
        env.put(record+8,env.object(4,'BMP-type',words=[0x424d50]))
        env.put(record+0x14,size,data)
        env.put(record+0x24,env.object(0x28,'cached-backing',fill=0))
        return {'receiver':image,'resource':record}
    yield Case('cached successful bitmap decoded and released',0x4d4190,valid_cached_bitmap,receiver=lambda t:t['receiver'],arguments=(lambda t:t['resource'],))

    def reused_logic_memory(e,c):
        size=c.arguments[0]
        return e.object(size,'reused-logic-allocation',fill=0x5b if size==0x174 else 0)
    for index in (0,1,28):
        def successor_reused(env,index=index):
            t=map_next(env,index=index,disabled=0)
            env.put(t['logic']+0x64,0x1728394a)
            env.put(t['logic']+0x130,0)
            env.override(0x4f63ec,reused_logic_memory)
            return t
        yield Case(f'map successor reused memory index{index}',0x40c4f0,successor_reused,arguments=(lambda t:t['actor'],))
    def gem_reused(env):
        t=successor_assets(env)
        env.override(0x4f63ec,reused_logic_memory)
        return t
    yield Case('gem successor reused logic storage',0x40d1a0,gem_reused,arguments=(lambda t:t['actor'],))

    # State zero's saturating wait and transition must not depend on a random
    # case selecting a small timer. Preserve both unsigned sides explicitly.
    for timer,elapsed in ((0,0),(0,17),(1,17),(16,17),(17,17),(18,17),(0x80000000,0x7fffffff),(0x7fffffff,0x80000000),(0xffffffff,17)):
        yield Case(f'map initial wait deterministic timer{timer} elapsed{elapsed}',0x40c4f0,logic(0,timer=timer,elapsed=elapsed),arguments=(lambda t:t['actor'],))

    # A previously played gem re-enters its initialization state. Its playback
    # latch and both neighboring scalar words have independent old contents.
    for level in (1,3,11,13,15,17,19):
        for old_played in (1,0x71524366):
            def gem_reset(env,level=level,old_played=old_played):
                t=logic(0,level=level,started=old_played,flags=0xa6)(env)
                env.put(t['logic']+0xa0,0x19283746,old_played,0x61728394)
                return t
            yield Case(f'gem reset stale playback level{level} flag{old_played}',0x40d1a0,gem_reset,arguments=(lambda t:t['actor'],))
    for enabled in (0,1,0x80000000):
        for started in (0,1):
            for level in (3,17):
                def gem_physical_sound(env,enabled=enabled,started=started,level=level):
                    t=logic(5,level=level,timer=0,started=started,app=True)(env)
                    services=env.get(env.get(0x5371fc)+0x30)
                    audio_map(env,services,{'BOOTY_GEM':0,'BOOTY_AMMAKE':0})
                    env.put(t['logic']+0xa0,0x41627384,started,0x192a3b4c)
                    env.put(0x532c0c,enabled,37)
                    return t
                yield Case(f'gem real sound enabled{enabled} started{started} level{level}',0x40d1a0,gem_physical_sound,arguments=(lambda t:t['actor'],))

    for count in (1,2):
        for function in (0x40bc80,0x40b620,0x40b600):
            def active_teardown(env,count=count):
                t=story_display(env)
                manager=env.get(t['services']+8)
                nodes=[]
                for i in range(count):
                    actor=env.object(0x1b4,'live-story-actor',fill=0)
                    obj=env.object(0x174,'live-story-logic',fill=0)
                    env.put(actor,0x5137f0)
                    env.put(actor+0xc,t['services'])
                    env.put(actor+0x6c,obj)
                    env.put(obj,0x513740)
                    node=env.object(12,'actor-list-node',words=[0,0,actor])
                    nodes.append(node)
                for i,node in enumerate(nodes):
                    env.put(node,nodes[i+1] if i+1<len(nodes) else 0,nodes[i-1] if i else 0)
                env.put(manager+0x14,nodes[0],nodes[-1],count)
                env.put(t['receiver']+0x34,0x17263548)
                return t
            yield Case(f'actual teardown {count} actors entry{function:x}',function,active_teardown,receiver=lambda t:t['receiver'],arguments=(1,) if function==0x40b600 else ())
