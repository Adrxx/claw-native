"""Original-driven launch service inputs and observable physical services."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns


def blank(env, *args, **kwargs):
    kwargs.setdefault("fill", 0)
    return env.object(*args, **kwargs)


def seeded(env, size, name, data):
    return blank(env, size, name, data=(data * ((size + len(data)-1)//len(data)))[:size])


def cases(random_source):
    noise = bytes(random_source.randrange(1, 256) for _ in range(73))
    # Palette translation: identity initialization, reserved slots, nearest RGB and ties.
    for mode in ('absent', 'missing-data', 'random', 'ties', 'exact'):
        palette = bytearray(random_source.randrange(256) for _ in range(1024))
        if mode == 'ties':
            for i in range(256):
                palette[i*4:i*4+3] = bytes((31, 61, 91))
        if mode == 'exact':
            for i in list(range(1, 10)) + list(range(245, 255)):
                j = 12 + i % 225
                palette[i*4:i*4+3] = palette[j*4:j*4+3]
        def setup(env, mode=mode, palette=bytes(palette)):
            root = seeded(env, 0x390, 'palette-owner', noise)
            resource = blank(env, 0x30, 'palette-resource')
            table = blank(env, 0x20, 'palette-table')
            colors = blank(env, 1024, 'rgb-colors', data=palette)
            env.put(root+0x2c, 0 if mode == 'absent' else resource)
            env.put(resource+0x10, table)
            env.put(table+0xc, 0 if mode == 'missing-data' else colors)
            return root
        yield Case('palette '+mode, 0x46db30, setup, receiver=lambda t:t)

    # Destruction re-reads the array and count after each virtual destructor.
    for count, mutate in ((-1, False), (0, False), (1, False), (4, False), (4, True)):
        def setup(env, count=count, mutate=mutate):
            root = seeded(env, 0x100, 'cleanup-owner', noise)
            array = blank(env, 24, 'owned-pointer-array')
            log = blank(env, 128, 'destruction-observation')
            vt = blank(env, 4, 'deletion-vtable')
            def destroy(env, call):
                n = env.calls_so_far(destroy_address)-1
                env.put(log+n*16, call.receiver, call.arguments[0], env.get(root+0xe4), env.get(root+0xe0))
                if mutate:
                    env.put(root+0xe4, 1)
                return 0x87654321
            destroy_address=env.stub('destroy', 'thiscall', 1, destroy)
            env.put(vt, destroy_address)
            objects = [blank(env, 16, 'owned-'+str(i), words=[vt, i+13, i+37, i+91]) for i in range(3)]
            env.put(array, objects[0], 0, objects[1], objects[2], 0, 0)
            env.put(root+0xe0, array, count, 6, 7)
            return root
        yield Case(f'cleanup count {count} mutation {mutate}', 0x42c060, setup, receiver=lambda t:t)

    for fn in (0x48f1e0, 0x48f370, 0x48f3e0):
        for missing in (0xc, 8, 0x20):
            def setup(env, missing=missing):
                root = seeded(env, 0x80, 'scene-owner', noise)
                env.put(root+8, 0x12345678, 0x23456789)
                env.put(root+0x20, 0x3456789a)
                env.put(root+missing, 0)
                return root
            yield Case(f'{fn:x} missing {missing:x}', fn, setup, receiver=lambda t:t, arguments=(0,0,0,0,0))

    for fn in (0x46dff0, 0x46e100):
        settings = [(0, 8, 'ok'), (-1, 8, 'ok'), (1, 8, 'ok'), (37,16,'ok'), (99,24,'ok'), (100,32,'ok'), (101,16,'ok'), (0x7fffffff,8,'ok'), (45,8,'no-screen'), (65,16,'no-surface')]
        if fn == 0x46e100:
            settings = [(100,8,'ok'), (100,8,'no-screen'), (100,8,'no-surface')]
        for value, depth, mode in settings:
            def setup(env, depth=depth, mode=mode):
                root = seeded(env, 0x80, 'progress-owner', noise)
                app = seeded(env, 0x100, 'progress-app', noise)
                services = blank(env, 0x30, 'services')
                display = blank(env, 0x30, 'display')
                screen = blank(env, 0x40, 'screen')
                surf = blank(env, 0xc0, 'surface')
                com = blank(env, 4, 'physical-surface')
                vt = blank(env, 0x80, 'surface-vtable')
                log = blank(env, 128, 'fill-observation')
                def fill(env, call):
                    env.write(log, env.read(call.arguments[1], 16) if call.arguments[1] else bytes(16))
                    env.write(log+16, env.read(call.arguments[5], 100))
                    env.put(log+116, call.arguments[4], call.arguments[2], call.arguments[3])
                    return 0
                env.put(vt+0x14, env.stub('fill', 'stdcall', 6, fill))
                env.put(com, vt)
                env.put(surf+8, com)
                env.put(root+4, app)
                env.put(app+0x78, depth)
                env.put(root+0xc, services)
                env.put(services+4, display)
                env.put(display+0x10, 0 if mode=='no-screen' else screen)
                env.put(screen+0x2c, 0 if mode=='no-surface' else surf)
                env.put(0x541368, 3, 2, 1)
                env.put(0x54135c, 11, 5)
                return root
            yield Case(f'{fn:x} {value} depth{depth} {mode}', fn, setup, receiver=lambda t:t, arguments=(value,) if fn==0x46dff0 else ())

    for batch, fail in ((False,False),(False,True),(True,False),(True,True)):
        payload = random_source.getrandbits(32)
        def setup(env, batch=batch, fail=fail):
            root = blank(env, 0x24, 'command-map-owner')
            buckets = blank(env, 17*4, 'command-buckets')
            nodes = blank(env, 16*80, 'free-command-nodes')
            for i in range(80):
                env.put(nodes+16*i, nodes+16*(i+1) if i<79 else 0)
            env.put(root+8, buckets, 17, 0, nodes, 0, 80)
            key = blank(env, 16, 'key', data=b'BatchCommand\0')
            env.override(0x5469e4,lambda env,call:len(env.cstr(call.arguments[0])))
            if fail:
                env.override(0x4f63ec, allocate(fail=True))
            return root,key
        yield Case('commands '+('batch' if batch else 'one')+(' allocation failure' if fail else ''), 0x4229c0 if batch else 0x422980, setup, receiver=lambda t:t[0], arguments=() if batch else (lambda t:t[1],payload,0x713abcde))

    for fn in (0x48f1e0,0x48f370,0x48f3e0):
        for mode, create, fade, alternate, flag in [('ok',0,0,0,0),('ok',1,0,0,0),('ok',1,1,0,1),('ok',1,0,1,7),('missing',1,0,0,1),('create-fail',1,0,0,1),('present-fail',1,0,0,0),('no-scene',0,1,0,0),('replace-scene',1,1,0,1)]:
            if fn==0x48f370 and mode not in ('ok','no-scene'):
                continue
            def setup(env, mode=mode):
                t=scene_setup(env, noise, mode)
                return t
            yield Case(f'{fn:x} scene {mode} {create}/{fade}/{alternate}/{flag}',fn,setup,receiver=lambda t:t['root'],arguments=(lambda t:t['name'],create,fade,alternate,flag))

    for path in ('', 'a', 'name.pcx', 'folder\\saved.claw', 'nullsurface.pcx'):
        for result in ((0,False),(0x8876021c,True),(0x80004005,False)) if len(path)>4 else ((0,False),):
            def setup(env,path=path,result=result):
                t=scene_setup(env,noise,'ok')
                string_services(env)
                app=blank(env, 0x100,'title-app')
                env.put(t['root']+4,app)
                if path=='nullsurface.pcx':
                    display=env.get(t['services']+4)
                    screen=env.get(display+0x10)
                    env.put(screen+0x2c,0)
                string=cstring(env,path.encode(),'saved-name')
                env.put(app+0xc0,string)
                def getdc(env,call):
                    n=env.calls_so_far(getdc_address)
                    env.put(call.arguments[1],0x3419 if result[1] or result[0]==0 else 0)
                    return result[0] if n==1 else 0
                getdc_address=env.stub('getdc','stdcall',2,getdc)
                env.put(t['com-vtable']+0x44,getdc_address)
                env.put(t['com-vtable']+0x68,env.stub('release-dc','stdcall',2,returns(0)))
                for a in (0x546888,0x546880,0x546d30):
                    env.override(a,returns(17))
                env.override(0x546df0,lambda env,call:env.calls_so_far(0x546df0)*300)
                return t
            yield Case(f'title {path} dc{result}',0x46f040,setup,receiver=lambda t:t['root'])

    for has_settings in (False, True):
        def setup(env, has_settings=has_settings):
            root=blank(env,0x20,'status-owner')
            app=blank(env,0x100,'status-app')
            settings=blank(env,0x20,'settings')
            services=blank(env,0x30,'status-services')
            display=blank(env,0x30,'status-display')
            screen=blank(env,0x40,'status-screen')
            viewport=blank(env,0x50,'status-viewport')
            env.put(root+4,app)
            env.put(app+0x38,settings if has_settings else 0)
            env.put(app+0x7c,640,480)
            env.put(app+0x30,services)
            env.put(services+4,display)
            env.put(display+0x10,screen)
            env.put(screen+0x10,640,480)
            env.put(services+0x24,viewport)
            def setrect(env,call):
                env.put(call.arguments[0],*call.arguments[1:])
                return 1
            env.override(0x546d5c,setrect)
            return root
        yield Case(f'status layout settings {has_settings}',0x46bb80,setup,receiver=lambda t:t)

    for current in (2,3):
        def setup(env,current=current):
            root=blank(env,0x200,'transition-app')
            scene=blank(env,0x800,'transition-scene')
            vt=blank(env,0x30,'transition-vtable')
            event=blank(env,64,'transition-observations')
            services=blank(env,0x300,'transition-services')
            manager=blank(env,0x40,'transition-resources')
            directory=blank(env,0x60,'empty-level-directory')
            buckets=blank(env,5*16,'empty-level-buckets')
            env.put(directory+0x40,buckets)
            env.put(manager+0x24,directory)
            env.put(scene+8,manager)
            env.put(scene+4,root)
            env.put(root+8,services)
            env.put(root+0x7c,640,480)
            env.put(root+0xc0,cstring(env,b'','empty-save'))
            env.put(root+0x2c,scene)
            env.put(scene,vt)
            env.put(vt+0x10,env.stub('current-scene','thiscall',0,returns(current)))
            def observe(env,call):
                n=env.get(event)
                env.put(event+4+n*12,call.receiver,call.arguments[0] if call.arguments else 0,env.get(root+0x2c))
                env.put(event,n+1)
                return 0
            env.put(vt+0x28,env.stub('leave-scene','thiscall',1,observe))
            env.put(vt,env.stub('destroy-scene','thiscall',1,observe))
            tls=blank(env,0x74,'thread-data')
            env.override(0x546b0c,returns(0x1234))
            env.override(0x546a7c,returns(tls))
            env.override(0x546ab8,returns(0))
            if current!=3:
                env.override(0x4f63ec,allocate(fail=True))
            return root
        yield Case(f'transition from {current} loader failure',0x429b70,setup,receiver=lambda t:t,arguments=(7,))

    yield Case('transition reload activates constructed generic scene',0x429b70,lambda env:success_setup(env,noise,scene_setup,blank,cstring,string_services),receiver=lambda t:t['root'],arguments=(1,))


def cstring(env, text, name):
    a=blank(env, len(text)+13,name,words=[20,len(text),len(text)],data=b'\x14\0\0\0'+len(text).to_bytes(4,'little')+len(text).to_bytes(4,'little')+text+b'\0')
    return a+12


def lookup_map(env, address, key, payload, modulus):
    buckets=blank(env, modulus*16,'lookup-buckets')
    node=blank(env, 24,'lookup-node')
    env.put(address+4,buckets)
    index=(len(key) if isinstance(key,bytes) else key)%modulus
    env.put(buckets+8+index*16,node+4)
    env.put(node+0x14,payload)


def scene_setup(env, noise, mode):
    root=seeded(env,0x800,'scene-owner',noise)
    services=blank(env, 0x40,'scene-services')
    display=blank(env, 0x30,'display-services')
    screen=blank(env, 0x40,'front-screen')
    back=blank(env, 0x40,'back-screen')
    surface=blank(env, 0xc0,'scene-surface')
    com=blank(env, 4,'scene-com')
    cvt=blank(env, 0x80,'scene-com-vtable')
    manager=blank(env, 0x80,'image-manager')
    mvt=blank(env, 0x80,'image-manager-vtable')
    present=blank(env, 0x40,'presenter')
    pvt=blank(env, 0x40,'present-vtable')
    image=blank(env, 0x30,'scene-image')
    ivt=blank(env, 0x40,'image-vtable')
    palette=blank(env, 0x30,'scene-palette')
    pcom=blank(env, 4,'palette-com')
    pcvt=blank(env, 0x30,'palette-com-vtable')
    colors=seeded(env,1024,'palette-colors',noise)
    saved=seeded(env,1024,'saved-colors',noise[::-1])
    observation=blank(env, 256,'scene-order-observations')
    def record(env,call):
        slot=env.get(observation)
        env.put(observation+4+slot*24,call.receiver,env.get(root+0x2c),env.get(manager+0x64),len(call.arguments),*(list(call.arguments[:2])+[0,0])[:2])
        env.put(observation,slot+1)
        return 0
    def create(env,call):
        record(env,call)
        env.write(observation+160,env.read(call.arguments[1],min(63,len(env.cstr(call.arguments[1]))+1)))
        return 0 if mode=='create-fail' else image
    def present_effect(env,call):
        record(env,call)
        return 0 if mode=='present-fail' else 0x12340000
    env.put(cvt+0x14,env.stub('clear-rect','stdcall',6,returns(0)))
    env.put(cvt+0x2c,env.stub('present-surface','stdcall',3,returns(0)))
    env.put(com,cvt)
    env.put(surface+8,com)
    env.put(screen+0x2c,surface)
    env.put(back+0x2c,surface)
    env.put(services+4,display)
    env.put(display+0x10,screen,back)
    env.put(services+0x18,manager)
    env.put(manager,mvt)
    env.put(mvt+0x30,env.stub('create-image','thiscall',3,create))
    env.put(present,pvt)
    env.put(pvt+0x30,env.stub('present-image','thiscall',1,present_effect))
    env.put(display+0x14,present)
    env.put(present+0x2c,surface)
    replacement=blank(env,0x30,'replacement-image')
    env.put(replacement,ivt)
    env.put(replacement+0x10,palette)
    def select(env,call):
        record(env,call)
        if mode=='replace-scene':
            env.put(root+0x2c,replacement)
        return 0
    env.put(ivt+0x34,env.stub('select-image','thiscall',0,select))
    env.put(image,ivt)
    env.put(image+0x10,palette)
    env.put(palette+4,pcom)
    env.put(palette+0xc,colors,saved)
    env.put(pcom,pcvt)
    def getpalette(env,call):
        if len(call.arguments)>4:
            env.write(call.arguments[4],env.read(colors,1024))
        return 0
    env.put(pcvt+0x10,env.stub('palette-get','stdcall',5,getpalette))
    env.put(pcvt+0x18,env.stub('palette-set','stdcall',5,returns(0)))
    name=blank(env, 24,'scene-name',data=b'LOADING\0')
    resource=blank(env, 0x40,'pcx-resource')
    env.put(resource,name)
    directory=blank(env, 0x60,'resource-directory')
    child=blank(env, 0x60,'screens-directory')
    childname=blank(env, 8,'screens-name',data=b'SCREENS\0')
    env.put(child,childname)
    lookup_map(env,directory+0x3c,b'SCREENS',child,5)
    typ=blank(env, 0x30,'pcx-type')
    env.put(typ,0x504358)
    lookup_map(env,child+0x44,0x504358,typ,9)
    lookup_map(env,typ+0x24,b'LOADING',resource,19)
    if mode=='missing':
        env.put(directory+0x40,blank(env, 5*16,'empty-buckets'))
    env.put(root+8,directory,services)
    env.put(root+0x20,directory)
    env.put(root+0x2c,0 if mode=='no-scene' else image)
    env.override(0x546df0,lambda env,call:env.calls_so_far(0x546df0)*1000)
    return {'root':root,'name':name,'com-vtable':cvt,'services':services,'directory':directory}


def string_services(env):
    def setrect(env,call):
        env.put(call.arguments[0],*call.arguments[1:])
        return 1
    env.override(0x546d5c,setrect)
    env.override(0x5469e4,lambda env,call:len(env.cstr(call.arguments[0])))
    for address,step in ((0x5469ec,1),(0x5469e8,-1)):
        def atomic(env,call,step=step):
            value=(env.get(call.arguments[0])+step)&0xffffffff
            env.put(call.arguments[0],value)
            return value
        env.override(address,atomic)


def success_setup(env, noise, scene_setup, blank, cstring, string_services):
    from clawparity.fixtures import returns
    t=scene_setup(env,noise,'ok')
    state=t['root']; services=t['services']
    image=env.get(state+0x2c); imanager=env.get(services+0x18)
    # Eliminate seeded unused pointers: state is an originally shaped empty instance.
    env.write(state,bytes(0x800))
    env.put(state+0xc,services)
    env.put(state+0x2c,0)
    app=blank(env,0x200,'success-app')
    svt=blank(env,0x30,'success-state-vtable')
    log=blank(env,256,'success-callback-observation')
    env.put(state,svt)
    env.put(svt+0xc,env.stub('state-mode-status','thiscall',0,returns(0)))
    env.put(svt+0x10,env.stub('state-mode','thiscall',0,returns(3)))
    def observe(env,call):
        n=env.get(log)
        env.put(log+4+n*12,call.receiver,call.arguments[0] if call.arguments else 0,env.get(app+0x2c))
        env.put(log,n+1)
        return 1
    env.put(svt+0x28,env.stub('state-leave','thiscall',1,observe))
    env.put(svt+0x24,env.stub('state-enter','thiscall',1,observe))
    env.put(app+0x2c,state)
    env.put(state+4,app)
    env.put(app+0x78,24,640,480)
    env.put(app+0xc0,cstring(env,b'','success-empty-save'))
    # app+30 zero avoids optional viewport conversion path. Real scene at state+c.
    env.put(app+0x124,1)
    window=blank(env,0x40,'success-window-owner'); env.put(window+4,0x12345678)
    env.put(app+4,window)
    env.put(0x5371fc,app)
    # Empty persistent preference/audio/input containers.
    music=blank(env,0x30,'empty-music-map'); env.put(music+8,17)
    env.put(app+0x50,music)
    pending=blank(env,0x30,'empty-pending-objects'); env.put(pending+0x20,10)
    env.put(app+0x5c,pending)
    controller=blank(env,0x74,'success-controller')
    device=blank(env,0x250,'success-input-device')
    env.put(controller,device); env.put(0x537204,controller)
    # Generic managers retain original map/list implementations for direct calls.
    sprite=blank(env,0x90,'empty-sprite-manager'); spvt=blank(env,0x80,'sprite-provider-vt')
    env.put(sprite,spvt); env.put(sprite+0x18,17)
    env.put(spvt+0x48,env.stub('empty-directory-images','thiscall',3,returns(0)))
    env.put(spvt+0x58,env.stub('empty-sprite-cleanup','thiscall',0,returns(0)))
    env.put(services+0x10,sprite)
    sound=blank(env,0x60,'empty-sound-manager'); env.put(sound+0x18,17)
    animation=blank(env,0x40,'empty-animation-manager'); env.put(animation+0x18,17)
    env.put(services+0x28,sound,animation)
    # World provider returns successful empty world input; no fixed load code stub.
    worldmanager=blank(env,0xe0,'empty-world-provider'); wvt=blank(env,0x80,'world-provider-vt')
    env.put(worldmanager,wvt)
    env.put(wvt+0x3c,env.stub('accept-empty-world-resource','thiscall',1,returns(1)))
    env.put(wvt+0x44,env.stub('empty-world-cleanup','thiscall',0,returns(0)))
    env.put(services+0x24,worldmanager)
    # Original actors/logic constructors execute with explicit empty callback input.
    objects=blank(env,0x40,'success-original-object-manager'); ovt=blank(env,0x80,'object-manager-vt')
    env.put(objects,ovt);env.put(objects+0xc,services)
    env.put(ovt+0x3c,env.stub('empty-object-cleanup','thiscall',0,returns(0)))
    free=blank(env,12*4,'actor-list-free-nodes')
    for i in range(4):env.put(free+i*12,free+(i+1)*12 if i<3 else 0)
    env.put(objects+0x20,free);env.put(objects+0x28,4)
    env.put(services+8,objects)
    registry=blank(env,0x40,'success-logic-registry')
    env.put(registry+0x18,17)
    buckets=blank(env,17*4,'success-logic-buckets');env.put(registry+0x14,buckets)
    def logic(env,call):
        # Callback consumes only explicit actor input; no game result is fabricated.
        n=env.get(log+200);env.put(log+204+n*8,call.arguments[0],len(call.arguments));env.put(log+200,n+1)
        return 1
    callback=env.stub('synthetic-empty-logic','cdecl',1,logic)
    for name in (b'CaptainClaw',b'CaptainClawScreenPosition'):
        descriptor=blank(env,0x14,'synthetic-logic-descriptor')
        env.put(descriptor+0x10,callback)
        key=cstring(env,name,'logic-key')
        h=0
        for ch in name:h=(h*33+(ch if ch<128 else ch-256))&0xffffffff
        h%=17
        node=blank(env,16,'logic-map-node')
        env.put(node,env.get(buckets+h*4),h,key,descriptor)
        env.put(buckets+h*4,node)
    env.put(services+0x14,registry)
    # REZ maps are physical input structures consumed by unchanged original lookup.
    def rezmap(address, pairs, modulus):
        b=blank(env,modulus*16,'success-rez-buckets')
        env.put(address,modulus,b)
        for key,payload in pairs:
            i=(len(key) if isinstance(key,bytes) else key)%modulus
            n=blank(env,24,'success-rez-node')
            env.put(n+4,env.get(b+8+i*16));env.put(n+0x14,payload)
            env.put(b+8+i*16,n+4)
    def directory(name):
        d=blank(env,0x60,'success-dir-'+name.decode())
        env.put(d,cstring(env,name,'directory-name'))
        rezmap(d+0x3c,[],5);rezmap(d+0x44,[],9)
        return d
    level=directory(b'LEVEL1');game=directory(b'GAME');archiveRoot=directory(b'')
    rezmap(archiveRoot+0x3c,[(b'LEVEL1',level)],5)
    children={name:directory(name) for name in (b'PALETTES',b'TILES',b'SOUNDS',b'IMAGES',b'ANIS',b'WORLDS')}
    rezmap(level+0x3c,list(children.items()),5)
    # state24 and28 share coherent empty provider directory set; music absent.
    rezmap(game+0x3c,[(n,children[n]) for n in (b'SOUNDS',b'IMAGES',b'ANIS')],5)
    def resource(d,typ,name):
        ty=blank(env,0x30,'success-resource-type');env.put(ty,typ)
        data=blank(env,0x40,'success-resource-'+name.decode());env.put(data,cstring(env,name,'resource-name'))
        rezmap(d+0x44,[(typ,ty)],9);rezmap(ty+0x24,[(name,data)],19)
        return data
    resource(children[b'PALETTES'],0x50414c,b'MAIN')
    resource(children[b'WORLDS'],0x575744,b'WORLD')
    archive=blank(env,0x48,'success-archive');env.put(archive+0x24,archiveRoot)
    env.put(state+8,archive);env.put(state+0x20,game,game,game)
    # Palette provider is already set up by scene_setup; root has no initial scene.
    env.put(env.get(imanager)+0x24,env.stub('palette-from-resource','thiscall',3,returns(image)))
    # Native API fixtures; caller must declare these imports in family specification.
    tls=blank(env,0x74,'success-thread-data')
    env.override(0x546b0c,returns(0));env.override(0x546a7c,returns(tls));env.override(0x546ab8,returns(0))
    env.override(0x546ccc,returns(1)) # UpdateWindow(HWND)
    env.override(0x546d54,returns(0xffffffff)) # ShowCursor(FALSE): now hidden
    env.override(0x546cac,returns(0)) # PeekMessageA: empty native queue
    env.override(0x546df0,lambda env,call:env.calls_so_far(0x546df0)*1000)
    string_services(env)
    t.update(root=app,state=state,callback_log=log)
    return t
