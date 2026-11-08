"""Independent original-backed special-command cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

NEW = 0x4F63EC


def callback(env, name, argc=0, result=0, effect=None, convention="thiscall"):
    record = env.object(128, name + " observations", fill=0)
    def invoke(e, call):
        count = e.get(record)
        e.put(record, count + 1)
        at = record + 4 + (count % 3) * 36
        e.put(at, call.receiver, *call.arguments)
        if effect:
            effect(e, call)
        return result
    return env.stub(name, convention, argc, invoke)


def virtual(env, name, slots, size=0x100):
    obj = env.object(size, name, fill=0)
    table = env.object(0x100, name + " vtable", fill=0)
    env.put(obj, table)
    for off, argc, result in slots:
        env.put(table + off, callback(env, name + hex(off), argc, result))
    return obj


def interlocked_decrement(env, call):
    address = call.arguments[0]
    value = (env.get(address) - 1) & 0xFFFFFFFF
    env.put(address, value)
    return value


def base(env, predicate=0):
    state = virtual(env, "state", [(0xC, 0, predicate), (0x10, 0, 3)], 0x778)
    app = env.object(0x300, "application", fill=0)
    window = env.object(8, "window", words=[0x11111111, 0x2468ACE0])
    env.put(state + 4, app)
    env.put(app + 4, window)
    env.put(0x5371FC, app)
    env.put(0x537E88, 0)
    env.put(app + 0x7C, 640, 480)
    env.put(app + 0x68, 10)
    env.override(0x5469E8, interlocked_decrement)
    env.override(0x5469E4, lambda e,c: len(e.cstr(c.arguments[0])))
    env.override(0x546DF0, lambda e, c: (0x12340000 + 2000 * e.calls_so_far(c.function)) & 0xFFFFFFFF)
    env.override(0x546A24, lambda e, c: 5000 * e.calls_so_far(c.function))
    env.override(0x546D50, returns(0x1357))
    env.override(0x546824, returns(0))
    env.override(0x546DEC, returns(0))
    env.override(0x546CAC, returns(0))
    env.override(0x546D54, lambda e, c: (2 - e.calls_so_far(c.function)) & 0xFFFFFFFF)
    env.override(0x4A3050, returns(17))
    return {"state": state, "app": app, "window": window}


def player(env, score=0xF1234567, health=0x23456789, words=None):
    p = env.object(0x200, "player", fill=0)
    logic = env.object(0x80, "player logic", fill=0)
    data = env.object(0x138, "player data", words=words or [0xA5010000 + i * 0x10203 for i in range(78)])
    env.put(p + 0x6C, logic)
    env.put(logic + 0x14, data)
    env.put(p + 0xF8, score)
    env.put(p + 0x10C, health)
    return p, logic, data


def scene(env, tokens):
    s = env.object(0x40, "scene", fill=0)
    display = env.object(0x30, "display", fill=0)
    objects = virtual(env, "object service", [(0x24, 1, 0), (0x28, 1, 0), (0x3C, 0, 0)])
    interface = virtual(env, "display service", [(0x34, 2, 0)])
    manager = virtual(env, "scene service", [(0x58, 0, 0)])
    renderer = virtual(env, "renderer service", [(0x44, 0, 0)])
    sound = env.object(0x80, "sound manager", fill=0)
    resources = env.object(0x80, "scene resources", fill=0)
    env.put(renderer + 0x60, 0xFFFFFFFF)
    env.put(sound + 0x18, 1)
    env.put(s + 4, display, objects, interface, manager)
    env.put(s + 0x24, renderer, sound, resources)
    env.put(tokens["state"] + 0xC, s)
    env.put(tokens["app"] + 0x30, s)
    tokens.update(scene=s, display=display, objects=objects, interface=interface, manager=manager, renderer=renderer, sound=sound)
    return tokens


def teardown(env, app_present=True, scene_present=True, handles=True, predicate=0):
    t = base(env, predicate)
    app, st = t["app"], t["state"]
    if app_present:
        for off, size in [(0x50, 0x40), (0x58, 0x40), (0x5C, 0x40)]:
            env.put(app + off, env.object(size, "app service" + hex(off), fill=0))
        movie = env.object(0x80, "movie manager", fill=0)
        env.put(app + 0x3C, movie)
        env.put(movie + 0x44, 0xABCD1234)
        if handles:
            env.put(st + 0x150, 0x44556677)
            env.put(st + 0x768, 0x12345678, 0x89ABCDEF, 0x76543210)
    else:
        env.put(st + 4, 0)
    if scene_present:
        scene(env, t)
    return t


def result_setup(level, occupied, complete, score, previous, elapsed):
    def setup(env):
        t = base(env)
        st, app = t["state"], t["app"]
        options = env.object(0x130, "completion options", fill=0)
        env.put(app + 0x48, options)
        env.put(options + 0x128, complete)
        env.put(st + 0x14, level)
        env.put(st + 0x160, previous, 0xFFFFFFF0, 0xA0)
        if 1 <= level <= 14:
            env.put(st + 0x160 + level * 16, 0xFACEABCD, occupied, 0xB0)
        p, _, _ = player(env, score)
        env.put(0x537210, elapsed)
        t["player"] = p
        return t
    return setup


def surfaces(env, t, width=4, height=1):
    descriptors=[]
    for name in ("primary", "secondary"):
        surf=env.object(0xB0,name+" surface",fill=0)
        dev=env.object(4,name+" directdraw",fill=0)
        table=env.object(0x100,name+" directdraw methods",fill=0)
        env.put(dev,table)
        for off,argc in ((0x14,6),(0x2C,3),(0x64,5),(0x80,2)):
            env.put(table+off,callback(env,name+" physical draw "+hex(off),argc,0,convention="stdcall"))
        env.put(surf+8,dev)
        env.put(surf+0x30,env.object(64,name+" pixels",fill=0x35 if name=="primary" else 0xCA))
        env.put(surf+0x14,height,width,width)
        desc=env.object(0x30,name+" descriptor",fill=0)
        env.put(desc+0x10,width,height)
        env.put(desc+0x2C,surf)
        descriptors.append(desc)
    env.put(t["display"]+0x10,*descriptors)
    t["primary"],t["secondary"]=descriptors
    return t


def fade_setup(env, bypass=1, gradient=0):
    t=surfaces(env,scene(env,base(env)))
    mgr=env.object(0x28,"fader manager",fill=0)
    env.put(mgr+0x14,env.object(16,"fader array",fill=0),0,4)
    env.put(t["state"]+0x10,mgr)
    env.put(t["scene"]+0x1C,1)
    env.put(0x537238,bypass)
    return t


def rez_directory(env, name, children):
    obj=env.object(0x80,"REZ "+name,fill=0)
    text=env.object(len(name)+1,"REZ name "+name,data=name.encode()+b"\0")
    env.put(obj,text)
    table=env.object(5*16,"REZ hash "+name,fill=0)
    env.put(obj+0x40,table)
    for key,value in children.items():
        node=env.object(0x18,"REZ link "+key,fill=0)
        at=table+(len(key)%5)*16+8
        env.put(node+4,env.get(at))
        env.put(node+0x14,value)
        env.put(at,node+4)
    return obj


def initializer_setup(env, stage=4, large=0, viewport=True):
    t=scene(env,base(env))
    snd=rez_directory(env,"SOUNDS",{})
    booty=rez_directory(env,"BOOTY",{"SOUNDS":snd} if stage>=4 else {})
    states=rez_directory(env,"STATES",{"BOOTY":booty})
    clawdir=rez_directory(env,"CLAW",{})
    level=rez_directory(env,"LEVEL1",{})
    children={}
    if stage>=1:children["LEVEL1"]=level
    if stage>=2:children["STATES"]=states
    if stage>=3:children["CLAW"]=clawdir
    root=rez_directory(env,"ROOT",children)
    archive=env.object(0x28,"archive",fill=0);env.put(archive+0x24,root)
    app=t["app"];env.put(app+0x34,archive)
    env.put(app+0xE0,env.object(4,"previous states",words=[t["state"]]),1)
    env.put(app+0x130,large)
    if not viewport:
        env.put(app+0x7C,320,240);env.put(app+0x30,0)
    env.put(0x537200,env.object(0x250,"input service",fill=0))
    # Empty original audio map stays in the physical-service-free branch.
    env.put(t["sound"]+0x30,1)
    return t


def warp_sound(env):
    t=fade_setup(env)
    p,_,_=player(env);env.put(0x537E88,p);env.put(0x529FA0,765,432)
    snd=env.object(0x20,"warp sound",fill=0)
    node=env.object(0x10,"warp sound map association",fill=0)
    key=env.object(10,"warp sound key",data=b"GAME_WARP\0")
    table=env.object(4,"warp sound buckets",words=[node])
    env.put(node+8,key,snd)
    env.put(t["sound"]+0x14,table,1)
    env.put(0x532C0C,0)
    return t


def existing_cases(random_source):
    for mode in (0, 1, 2, 4, 0xFFFFFFFF):
        yield Case(f"initialize rejects mode {mode}", 0x40AC20, base, receiver=lambda t:t["state"], arguments=(0, 0x87654321, mode))
    for count in (0, 0xFFFFFFFF):
        def no_stack(env, count=count):
            t=base(env); env.put(t["app"]+0xE4,count); return t
        yield Case(f"initialize absent previous state {count}",0x40AC20,no_stack,receiver=lambda t:t["state"],arguments=(lambda t:t["app"],7,3))
    for child in (False, True):
        for result in (0, 1, 0xDEADBEEF):
            def setup(env, child=child, result=result):
                t=base(env)
                c=virtual(env,"activation child",[(0x24,1,result)]) if child else 0
                env.put(t["state"]+0x154,c); return t
            yield Case(f"activate child {child} return {result}",0x40B120,setup,receiver=lambda t:t["state"],arguments=(random_source.getrandbits(32),))
    for missing in ("player", "logic", "data", "state", "predicate", "record"):
        def setup(env, missing=missing):
            t=base(env); p,l,d=player(env)
            if missing=="player": p=0
            if missing=="logic": env.put(p+0x6C,0)
            if missing=="data": env.put(l+0x14,0)
            if missing in ("predicate","record"):
                kind=9 if missing=="predicate" else 3
                env.put(env.get(t["state"])+0x10, callback(env,"state type",0,kind))
                env.put(t["app"]+0x2C,t["state"])
                env.put(t["state"]+0x14,0)
            t["player"]=p; return t
        yield Case("snapshot missing "+missing,0x415D90,setup,arguments=(lambda t:t["player"],))
    for active in (0,1):
        for have_player in (0,1,2):
            def setup(env,active=active,have_player=have_player):
                t=base(env); env.put(t["app"]+0x30,active)
                if have_player:
                    p,l,d=player(env);env.put(0x537E88,p)
                    if have_player==1:env.put(l+0x14,0)
                env.put(0x5430C4,0xABCDEF01,0xABCDEF02)
                return t
            yield Case(f"timing scene {active} player {have_player}",0x42ABF0,setup,receiver=lambda t:t["app"])
    for predicate in (0,1,0xFFFFFFFF):
        for app in (False,True):
            for settings in (0,1,2):
                def setup(env,predicate=predicate,app=app,settings=settings):
                    t=base(env,predicate)
                    if not app:env.put(t["state"]+4,0)
                    if settings:
                        s=env.object(0x20,"registry settings",words=[settings-1]);env.put(s+0x18,0x2457);env.put(t["app"]+0x38,s)
                    env.put(t["app"]+0x68,0xFEED1234);env.put(0x525518,0xCAFE9876)
                    return t
                yield Case(f"layout {predicate} app{app} settings{settings}",0x46BBC0,setup,receiver=lambda t:t["state"])
    for app in (False,True):
        for sc in (False,True):
            for handles in (False,True):
                yield Case(f"teardown app{app} scene{sc} handles{handles}",0x46B7B0,lambda e,a=app,s=sc,h=handles:teardown(e,a,s,h),receiver=lambda t:t["state"])
    for x,y,present in ((0,5,True),(-1,5,True),(5,0,True),(5,-1,True),(5,7,False)):
        def setup(env,x=x,y=y,present=present):
            t=base(env);p,_,_=player(env);env.put(0x537E88,p if present else 0);env.put(0x529FA0,x&0xFFFFFFFF,y&0xFFFFFFFF);return t
        yield Case(f"warp guard {x},{y},{present}",0x46C630,setup,receiver=lambda t:t["state"])
    for level in (-1,0,1,2,14,15,0x7FFFFFFF):
        for occupied in (0,1,0x80000000,0xFFFFFFFF):
            for complete in (0,1):
                yield Case(f"record level{level} occupied{occupied} flag{complete}",0x46C7B0,result_setup(level,occupied,complete,random_source.getrandbits(32),random_source.getrandbits(32),random_source.getrandbits(32)),receiver=lambda t:t["state"],arguments=(lambda t:t["player"],))
    yield Case("record absent player",0x46C7B0,base,receiver=lambda t:t["state"],arguments=(0,))
    for level in (1,14):
        for finish in (0,1):
            def setup(env,level=level,finish=finish):
                t=teardown(env,True,False,False);env.put(t["state"]+0x14,level);env.put(t["state"]+0x258,1,finish);env.put(t["app"]+0x9C,1);env.put(t["app"]+0xA0,1);env.put(t["app"]+0x100,0);return t
            yield Case(f"finish mode level{level} flag{finish}",0x46C900,setup,receiver=lambda t:t["state"])
    for entry in (0x48FDA0,0x48FEB0):
        for stop in (0,1,2,3):
            def setup(env,stop=stop):
                t=scene(env,base(env)); manager=env.object(0x28, "fade manager", fill=0);env.put(t["state"]+0x10,manager if stop else 0)
                env.put(t["scene"]+0x1C,int(stop>1))
                first=env.object(0x30, "primary descriptor", fill=0);second=env.object(0x30, "secondary descriptor", fill=0)
                env.put(t["display"]+0x10,first,second)
                if stop>2:env.put(first+0x2C,env.object(0xB0, "primary surface", fill=0))
                return t
            if entry==0x48FEB0 and stop==3:continue
            yield Case(f"fade {entry:x} guard{stop}",entry,setup,receiver=lambda t:t["state"],arguments=(80,0x5AA,0))
    for _ in range(12):
        words=[random_source.getrandbits(32) for i in range(8)]
        def setup(env,words=words):return {"state":env.object(32,"descriptor with guards",words=words)}
        yield Case("five word initializer "+hex(words[0]),0x4ECC00,setup,receiver=lambda t:t["state"])

    def full_teardown(env):
        t=teardown(env)
        backend=env.object(0x80,"audio backend",fill=0)
        env.put(t["sound"]+0x2C,backend)
        mgr=env.object(0x40,"app manager",fill=0)
        empty=env.object(16,"empty string header",fill=0)
        env.put(mgr+0x1C,empty+12)
        env.put(t["app"]+0x4C,mgr)
        return t
    yield Case("teardown nonnull backend and manager",0x46B7B0,full_teardown,receiver=lambda t:t["state"])
    for entry in (0x48FDA0,0x48FEB0):
        for bypass in (0,1):
            for gradient in (0,100,101):
                yield Case(f"fade original factory {entry:x} bypass{bypass} gradient{gradient}",entry,lambda e,b=bypass:fade_setup(e,b),receiver=lambda t:t["state"],arguments=(gradient,80,0))
    for stage in range(5):
        for large in (0,1):
            yield Case(f"initialize resource stage{stage} large{large}",0x40AC20,lambda e,s=stage,l=large:initializer_setup(e,s,l),receiver=lambda t:t["state"],arguments=(lambda t:t["app"],1,3))
    yield Case("initialize viewport change refused",0x40AC20,lambda e:initializer_setup(e,1,0,False),receiver=lambda t:t["state"],arguments=(lambda t:t["app"],1,3))
    for disabled in (0,1):
        for sub in (0,1):
            def setup(env,disabled=disabled,sub=sub):
                t=fade_setup(env)
                p,_,_=player(env);env.put(0x537E88,p)
                env.put(0x529FA0,123,456)
                env.put(t["sound"]+0x30,disabled)
                if sub:env.put(t["renderer"]+0x5C,env.object(0xB4,"subrenderer",fill=0))
                return t
            yield Case(f"warp accepted sound{disabled} sub{sub}",0x46C630,setup,receiver=lambda t:t["state"])

    for mode in (0,1):
        for loading in (0,1):
            for palette in (0,1):
                def setup(env,mode=mode,loading=loading,palette=palette):
                    t=surfaces(env,teardown(env,True,True,False))
                    st,app=t["state"],t["app"]
                    env.put(st+0x14,14)
                    env.put(st+0x258,loading,1)
                    env.put(app+0x9C,mode)
                    env.put(app+0xA0,1)
                    logger=env.object(0x44,"logger",fill=0)
                    header=env.object(16,"logger empty string",fill=0)
                    env.put(logger+0x1C,header+12)
                    env.put(app+0x60,logger)
                    if palette:
                        owner=env.object(0x14,"palette owner",fill=0)
                        pal=env.object(0x20,"palette",fill=0)
                        dev=env.object(4,"physical palette",fill=0)
                        vtable=env.object(0x20,"physical palette methods",fill=0)
                        env.put(vtable+0x10,callback(env,"palette read",5,0,convention="stdcall"))
                        env.put(vtable+0x18,callback(env,"palette write",5,0,convention="stdcall"))
                        env.put(dev,vtable)
                        env.put(pal+4,dev)
                        env.put(pal+0xC,env.object(0x400,"palette entries",fill=0x73))
                        env.put(pal+0x10,env.object(0x400,"palette saved",fill=0x94))
                        env.put(owner+0x10,pal)
                        env.put(st+0x2C,owner)
                    return t
                yield Case(f"finish loading{loading} mode{mode} palette{palette}",0x46C900,setup,receiver=lambda t:t["state"])
    def failed_finish(env):
        t=teardown(env,True,False,False)
        env.put(t["state"]+0x258,1,0)
        host=virtual(env,"error notification",[(0x1C,2,0)],0x248)
        env.put(t["app"]+8,host)
        env.put(t["app"]+0xA0,0)
        env.override(NEW,allocate(fail=True))
        return t
    yield Case("finish factory allocation failure",0x46C900,failed_finish,receiver=lambda t:t["state"])
    yield Case("warp existing original sound lookup",0x46C630,warp_sound,receiver=lambda t:t["state"])
    for stage in (0,1,2):
        def setup(env,stage=stage):
            t=teardown(env,True,True,False)
            st=t["state"]
            if stage==0:
                table=env.get(t["manager"])
                env.put(table+0x58,callback(env,"scene release changes scene pointer",0,0,effect=lambda e,c:e.put(st+0xC,0)))
            elif stage==1:
                table=env.get(t["renderer"])
                env.put(table+0x44,callback(env,"renderer changes scene pointer",0,0,effect=lambda e,c:e.put(st+0xC,0)))
            else:
                table=env.get(st)
                env.put(table+0xC,callback(env,"predicate changes app",0,0,effect=lambda e,c:e.put(st+4,0)))
            return t
        yield Case(f"teardown callback pointer reload {stage}",0x46B7B0,setup,receiver=lambda t:t["state"])
    for begin in (False,True):
        def setup(env,begin=begin):
            t=fade_setup(env)
            p,_,_=player(env);env.put(0x537E88,p);env.put(0x529FA0,312,987)
            env.put(t["sound"]+0x30,1)
            sub=env.object(0xB4,"reloaded subrenderer",fill=0)
            renderer=t["renderer"]
            env.put(renderer+0x5C,sub if begin else 0)
            def replace(e,c):
                e.put(renderer+0x5C,0 if e.calls_so_far(c.function)==1 and begin else sub)
            env.put(env.get(t["objects"])+0x24,callback(env,"update swaps subrenderer",1,0,effect=replace))
            return t
        yield Case(f"warp updates swap subrenderer initially{begin}",0x46C630,setup,receiver=lambda t:t["state"])
    for level in (1,14):
        def setup(env,level=level):
            t=result_setup(level,0,1,17,0xFFFFFFF8,0x80000013)(env)
            t["player"]=t["state"]+0x6C
            return t
        yield Case(f"result aliased player score and total time {level}",0x46C7B0,setup,receiver=lambda t:t["state"],arguments=(lambda t:t["player"],))

    def immediate_cursor(env):
        t=initializer_setup(env)
        env.override(0x546D54,returns(0xFFFFFFFF))
        return t
    yield Case("initialize cursor already hidden",0x40AC20,immediate_cursor,receiver=lambda t:t["state"],arguments=(lambda t:t["app"],1,3))
    def child_failure(env):
        t=initializer_setup(env)
        archive=env.get(t["app"]+0x34)
        root=env.get(archive+0x24)
        buckets=env.get(root+0x40)
        def allocate_and_change_archive(e,c):
            result=e.object(c.arguments[0],"allocation")
            if c.arguments[0]==0x158:
                e.put(buckets+(len("CLAW")%5)*16+8,0)
            return result
        env.override(NEW,allocate_and_change_archive)
        return t
    yield Case("initialize original child rejects changed archive",0x40AC20,child_failure,receiver=lambda t:t["state"],arguments=(lambda t:t["app"],1,3))



def cases(random_source):
    for replace_scene in (False, True):
        def setup(env, replace_scene=replace_scene):
            t=teardown(env,True,True,False)
            original=t["scene"]
            # Application and state scene fields are independent original inputs.
            alternate=scene(env,dict(t))
            env.put(t["state"]+0xC,original,alternate["scene"])
            backend=env.object(0x80,"teardown audio backend",fill=0)
            node=env.object(0x38,"teardown audio clip",fill=0)
            engine=env.object(0x80,"teardown sound engine",fill=0)
            device=env.object(4,"teardown physical sound buffer",fill=0)
            methods=env.object(0x50,"teardown physical sound methods",fill=0)
            env.put(device,methods)
            env.put(methods+0x48,callback(env,"teardown DirectSound stop",1,0,convention="stdcall"))
            env.put(engine+0x78,1)
            env.put(node+0xC,device,engine)
            env.put(backend+4,node+4)
            env.put(backend+0x78,1)
            env.put(t["sound"]+0x2C,backend)
            if replace_scene:
                env.put(env.get(t["manager"])+0x58,callback(
                    env,"release selects second scene",effect=lambda e,c:e.put(t["state"]+0xC,alternate["scene"])))
            return t
        yield Case(f"teardown distinct application scene replace{replace_scene}",0x46B7B0,setup,receiver=lambda t:t["state"])

    for layout, rankings in ((0xFEDCBA98,0x13579BDF),(0,0xFFFFFFFF)):
        def setup(env,layout=layout,rankings=rankings):
            t=base(env,1)
            settings=env.object(0x20,"active settings",fill=0)
            env.put(settings,1);env.put(settings+0x18,0x37281904)
            env.put(t["app"]+0x38,settings)
            env.put(t["app"]+0x68,layout,layout^0xFFFFFFFF)
            env.put(0x525518,rankings,rankings^0xFFFFFFFF)
            record=env.object(64,"persisted registry words",fill=0x71)
            def write_registry(e,c):
                at=record+24*(e.calls_so_far(c.function)-1)
                e.put(at,c.arguments[0],c.arguments[2],c.arguments[3],c.arguments[5],e.get(c.arguments[4]))
                e.put(at+20,len(e.cstr(c.arguments[1])))
                return 0
            env.override(0x546824,write_registry)
            return t
        yield Case(f"layout observes registry payload {layout:x} {rankings:x}",0x46BBC0,setup,receiver=lambda t:t["state"])

    for large in (0,1):
        for removed in ("LEVEL1","STATES"):
            def setup(env,large=large,removed=removed):
                t=initializer_setup(env,4,large)
                root=env.get(env.get(t["app"]+0x34)+0x24)
                buckets=env.get(root+0x40)
                def dirty_child(e,c):
                    size=c.arguments[0]
                    child=e.object(size,"dirty original allocation",fill=0xA7 if size in (0x158,0x184) else 0)
                    if size==(0x184 if large else 0x158):
                        # Parent lookups completed; the unchanged child now sees
                        # either its base lookup fail or its first own lookup fail.
                        slot=buckets+(len(removed)%5)*16+8
                        link=e.get(slot)
                        while link:
                            directory=e.get(link+0x10)
                            if e.cstr(e.get(directory)).decode()==removed:
                                e.put(slot,e.get(link))
                                break
                            slot=link
                            link=e.get(link)
                    return child
                env.override(NEW,dirty_child)
                return t
            yield Case(f"initialize dirty child large{large} missing{removed}",0x40AC20,setup,receiver=lambda t:t["state"],arguments=(lambda t:t["app"],1,3))

    for disabled in (0,1,0x80000000):
        def setup(env,disabled=disabled):
            t=warp_sound(env)
            env.put(t["sound"]+0x30,disabled,disabled^0xFFFFFFFF)
            env.put(0x532C0C,1)
            env.put(0x532C10,37)
            # Existing original sample avoids device allocation. Its DirectSound
            # buffer is the physical boundary; all playback game helpers execute.
            engine=env.object(0x80,"sound engine",fill=0)
            env.put(engine+0x78,1)
            clip=env.object(0x40,"warp audio clip",fill=0)
            sample=env.object(0x34,"warp audio sample",fill=0)
            device=env.object(4,"DirectSound buffer",fill=0)
            methods=env.object(0x50,"DirectSound buffer methods",fill=0)
            env.put(device,methods)
            for off,argc in ((0x30,4),(0x3C,2),(0x40,2),(0x44,2)):
                env.put(methods+off,callback(env,"DirectSound warp "+hex(off),argc,0,convention="stdcall"))
            env.put(clip+0x10,engine)
            env.put(clip+0x18,22050,0,0)
            env.put(clip+0x30,sample+4,sample+4)
            env.put(sample+0xC,device,engine,0xA4,22050)
            env.put(sample+0x30,1)
            env.put(methods+0x24,callback(env,"DirectSound warp status",2,0,
                effect=lambda e,c:e.put(c.arguments[1],0),convention="stdcall"))
            table=env.get(t["sound"]+0x14)
            node=env.get(table)
            snd=env.get(node+0xC)
            env.put(snd+0x10,clip)
            return t
        yield Case(f"warp present sound physical playback disabled{disabled}",0x46C630,setup,receiver=lambda t:t["state"])

    yield from existing_cases(random_source)
