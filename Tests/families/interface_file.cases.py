"""Original-backed interface trees, widgets, menu state and archives."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

NEW = 0x4F63EC
TICK = 0x546A24


def physical(env, tick=1000):
    env.override(TICK, returns(tick))
    def bounded_copy(e,c):
        dst,src,count=c.arguments
        if count:
            text=e.cstr(src)[:count-1]
            if isinstance(text,str):text=text.encode("latin-1")
            e.write(dst,text+b"\0")
        return dst
    env.override(0x5469CC,bounded_copy)
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))
    def increment(e, c):
        a = c.arguments[0]
        value = (e.get(a) + 1) & 0xffffffff
        e.put(a, value)
        return value
    def decrement(e, c):
        a = c.arguments[0]
        value = (e.get(a) - 1) & 0xffffffff
        e.put(a, value)
        return value
    env.override(0x5469EC, increment)
    env.override(0x5469E8, decrement)
    env.override(0x546CD0, lambda e, c: (e.put(c.arguments[0], 41, 53) or 1))
    env.override(0x546CD4, returns(0))


def string(env, value=b"", refs=7):
    a = env.object(13 + len(value), "CString header and text")
    env.put(a, refs, len(value), len(value))
    env.write(a + 12, value + b"\0")
    return a + 12


def record(env, name, argc=0, convention="thiscall", result=0, mutate=None):
    log = env.object(96, name + " receipt", fill=0xA3)
    def effect(e, call):
        e.put(log, e.calls_so_far(call.function), call.receiver, *call.arguments)
        if mutate:
            mutate(e, call)
        return result
    return env.stub(name, convention, argc, effect)


def widget(env, index=0, flags=1):
    w = env.object(0x70, "widget", fill=0x6D)
    images = []
    for n in range(8):
        image = env.object(0x30, "distinct image", fill=0x71 + n)
        env.put(image + 0x14, 11 + (7 - n) * 3 + index, 17 + (n % 3) * 5 + index)
        images.append(image)
    table = env.object(32, "eight states", words=images)
    env.put(w + 4, table, 8, 8, 0)
    env.put(w + 0x14, 103 + index)
    for n in range(8):
        env.put(w + 0x18 + n * 4, string(env, bytes([65 + n, 97 + index])))
    env.put(w + 0x38, 0, 0, images[0], flags, 0, 0, 0)
    env.put(w + 0x54, 21 + index * 3, 35 + index * 7, 61 + index, 73 + index, 0, 80 + index)
    return w


def tree(env, depth=1, count=3, index=0):
    t = env.object(0xB0, "interface tree", fill=0x39)
    methods = env.object(16, "tree vtable")
    env.put(methods, record(env, "tree load", 5, result=1), record(env, "tree close"), record(env, "tree serialize", 1))
    env.put(t, methods, 0, 0, string(env, b"path"), 0, string(env, b"description"))
    children = [tree(env, depth - 1, 2, index * 3 + n + 1) for n in range(count)] if depth else []
    array = env.object(max(4, len(children)*4), "child pointers", words=children)
    env.put(t + 0x1C, array, len(children), len(children), 0, 0x7139)
    # Inline widget storage shares the source layout.
    w = widget(env, index)
    env.write(t + 0x3C, env.read(w, 0x70))
    env.put(t + 0x50, 103 + index)
    env.put(t + 0x34, env.object(36, "node extra storage", fill=0x28), 9)
    env.put(t + 0xA4, 0x12, 0x34, 0x56)
    return t


def menu_setup(count=3, selected=0, disabled=(), pressed=0, skip=0, tick=1000):
    def setup(env):
        physical(env, tick)
        m = env.object(0x110, "menu", fill=0x59)
        methods = env.object(32, "menu vtable")
        for off, argc in ((0x10,0),(0x14,0),(0x18,0),(0x1C,2)):
            env.put(methods + off, record(env, "menu callback %x" % off, argc))
        items = [widget(env, n, 0x21 if n in disabled else 0x15) for n in range(count)]
        array = env.object(max(4, count * 4), "menu widgets", words=items)
        env.put(m, methods, 1, 0, array, count, count, 0, selected, skip, pressed, selected, 900, 900, 400, 0, 641, 481, 0)
        env.put(m + 0xF8, 0, 1)
        return dict(obj=m, items=items, array=array, external=widget(env, 7))
    return setup


def tree_setup(depth=1, count=3):
    def setup(env):
        physical(env)
        return dict(obj=tree(env, depth, count))
    return setup


def widget_setup(flags=1):
    def setup(env):
        physical(env)
        return dict(obj=widget(env, flags=flags), out=env.object(32, "output canary", fill=0xC7))
    return setup


def case(label, address, setup, *arguments, **kw):
    return Case(label, address, setup, receiver=lambda t: t["obj"], arguments=arguments, **kw)


def archive(env, data=None):
    a = env.object(0x44, "CArchive", fill=0)
    buffer = env.object(4096, "archive buffer", data=data or b"", fill=0xD1)
    env.put(a + 0x14, 1 if data is not None else 0)
    env.put(a + 0x24, buffer, buffer + 4096, buffer)
    return a


def cases(random_source):
    yield Case("empty global hook", 0x4BC110)
    yield Case("constant callback", 0x4E5B50, arguments=(0x519, 0x761))
    for address in (0x4DD180, 0x4DDE80, 0x4DEF70):
        def setup(env):
            physical(env)
            return dict(obj=env.object(0x110, "constructor poison", fill=0x9B))
        yield case("constructor %x" % address, address, setup)
    for address in (0x4DD0C0,0x4DD480,0x4DF630,0x4ED050):
        for value in (0, 1, 0xFFFFFFFF, random_source.getrandbits(32)):
            def setup(env, value=value):
                physical(env)
                return dict(obj=env.object(0x110, "field witnesses", words=[value ^ (n*0x13579) for n in range(68)]))
            yield case("field %x value %x" % (address,value),address,setup)
    for address in (0x4DECE0,0x4DED20,0x4DED40):
        yield case("geometry %x" % address,address,widget_setup(),lambda t:t["out"])
    yield case("set signed coordinates",0x4DED00,widget_setup(),0xFFFFFFF9,random_source.getrandbits(32))
    for flags in range(64):
        yield case("state bits %x" % flags,0x4DEC60,widget_setup(),flags | 0xAC000000)
    for address in (0x4DD240,0x4DD420,0x4DD1C0):
        for present in (False,True):
            def setup(env,present=present):
                t=menu_setup(0)(env)
                env.put(t["obj"]+4,int(present))
                env.put(t["obj"]+0xC,env.object(24,"owned array",fill=0x7D) if present else 0)
                return t
            yield case("array cleanup %x %s"%(address,present),address,setup)
    for index in (-1,0,1,2,3,0x7fffffff):
        yield case("indexed widget %d"%index,0x4DD450,menu_setup(),index)
        yield case("select %d"%index,0x4DD490,menu_setup(disabled=(1,)),index)
    for count in (0,1,3):
        yield case("select by pointer %d"%count,0x4DD520,menu_setup(count),lambda t:t["items"][-1] if t["items"] else t["external"])
        for axis in (-1,0,1,2):
            for ends in ((-23,101),(101,-23),(17,17)):
                yield case("layout %d %d %s"%(count,axis,ends),0x4DD800,menu_setup(count),axis,*ends)
    for address in (0x4DDA50,0x4DDAC0,0x4DDB40):
        for selected in (0,1,2):
            for skip in (0,1):
                for pressed in (0,1):
                    yield case("navigate %x %d %d %d"%(address,selected,skip,pressed),address,menu_setup(selected=selected,skip=skip,pressed=pressed,disabled=(0,2),tick=950))
    for address in (0x4DDBC0,0x4DDCE0,0x4DDC30):
        for count in (0,1,3):
            for pressed in (0,1):
                for tick in (900,980,981,1000,1401,0xFFFFFFFF):
                    yield case("input timer %x %d %d %d"%(address,count,pressed,tick),address,menu_setup(count,pressed=pressed,tick=tick))
    for kind in (0,1,0x8BADF00D):
        def setup(env, kind=kind):
            t=tree_setup(0)(env)
            if kind:
                env.put(0x02008000 - 0x10, 0x9135C7AB ^ kind)
            return t
        yield case("factory kind %x"%kind,0x4DF2B0,setup,kind)
    for address in (0x4DF200,0x4DD020,0x4DCEB0):
        for target in (103,104,105,999):
            def setup(env,address=address):
                physical(env)
                if address==0x4DF200:
                    return dict(obj=tree(env,2,2))
                m=env.object(0x110,"menu with embedded tree",fill=0)
                t=tree(env,2,2)
                env.write(m+0x48,env.read(t,0xB0))
                return dict(obj=m)
            for enable in ((0,1) if address==0x4DCEB0 else (None,)):
                args=(target,) if enable is None else (target,enable)
                yield case("search %x %d %s"%(address,target,enable),address,setup,*args)
    for address in (0x4DF270,0x4DF620):
        yield case("tree state %x"%address,address,tree_setup(2,2),random_source.getrandbits(32))
    yield case("raw child index",0x4DF260,tree_setup(),2)
    yield case("copy description",0x4DF460,tree_setup(),lambda t:t["obj"]+0xAC)
    for address in (0x4DF180,0x4DF040,0x4DDF70,0x4DCCB0):
        def setup(env,address=address):
            physical(env)
            t=tree(env,0)
            if address==0x4DDF70:
                return dict(obj=t+0x3C)
            if address==0x4DCCB0:
                m=env.object(0x110,"menu destructor",fill=0)
                env.write(m+0x48,env.read(t,0xB0))
                return dict(obj=m)
            return dict(obj=t)
        yield case("destructor %x"%address,address,setup)
    def construct(env):
        physical(env)
        return dict(obj=env.object(0x110,"menu constructor",fill=0x9A))
    yield case("menu constructor geometry",0x4DCC40,construct,641,479)
    for address in (0x4DD270,0x4DE790):
        yield case("draw disabled %x"%address,address,menu_setup(0) if address==0x4DD270 else widget_setup(),0)
    for mode in (0,1):
        def setup(env, mode=mode):
            t=widget_setup()(env)
            if mode:
                data=b"\0"*8+(0x7193).to_bytes(4,"little")
            else:
                data=None
            t["archive"]=archive(env,data)
            return t
        yield case("widget archive %d"%mode,0x4DEB50,setup,lambda t:t["archive"])
    for mode in (0,1):
        def setup(env,mode=mode):
            t=tree_setup(0)(env)
            data=(0x1234).to_bytes(4,"little")+b"\0"*9+(0xA9).to_bytes(4,"little")+b"\0\0" if mode else None
            t["archive"]=archive(env,data)
            return t
        yield case("tree archive %d"%mode,0x4DF490,setup,lambda t:t["archive"])
    for address in (0x4DE450,0x4DE4D0):
        if address==0x4DE450:
            yield case("unloaded widget dispose",address,widget_setup())
        else:
            for index in (-1,0,3,7,8):
                yield case("replace image %d"%index,address,widget_setup(),lambda t:t["obj"],index)
    for manager in (0,1):
        def setup(env):
            t=widget_setup()(env)
            env.put(t["obj"]+8,0,0)
            return t
        yield case("load manager %d"%manager,0x4DE0E0,setup,0,0,0,0)
    yield case("child count direct",0x4DF480,tree_setup())
    for address in (0x4DCF10,0x4DCF00,0x4DD030,0x4DD0D0,0x4DD0E0,0x4DCE90):
        for count in (0,1,3):
            for enabled in (0,1):
                def setup(env,count=count,enabled=enabled,address=address):
                    t=menu_setup(count)(env)
                    root=tree(env,1,count)
                    env.write(t["obj"]+0x48,env.read(root,0xB0))
                    env.put(t["obj"]+0xF8,t["obj"]+0x48,enabled if count or address!=0x4DD0E0 else 0)
                    env.put(t["obj"]+0x44,enabled)
                    t["root"]=t["obj"]+0x48
                    return t
                args=(lambda t:t["root"], enabled) if address==0x4DCF10 else ((0x91387,) if address==0x4DD0D0 else ())
                yield case("controller tree %x %d %d"%(address,count,enabled),address,setup,*args)
    for address in (0x4DD2C0,0x4DF2B0):
        for count,capacity,growth in ((0,0,0),(0,5,0),(1,1,0),(2,2,1),(2,2,-9),(33,33,0),(8200,8200,0),(3,9,2)):
            def setup(env,address=address,count=count,capacity=capacity,growth=growth):
                physical(env)
                obj=env.object(0xB0,"append container",fill=0x9A)
                values=[0x12345671+n*0x7531 for n in range(max(1,capacity))]
                storage=env.object(max(4,capacity*4),"existing append storage",words=values) if capacity else 0
                offset=0xC if address==0x4DD2C0 else 0x1C
                env.put(obj+offset,storage,count,capacity,growth)
                return dict(obj=obj,item=env.object(8,"new element",fill=0xD3))
            yield case("append %x %d %d %d"%(address,count,capacity,growth),address,setup,(lambda t:t["item"]) if address==0x4DD2C0 else 0)
    yield Case("append null argument does not touch receiver",0x4DD2C0,receiver=0,arguments=(0,))
    for result in (0,1):
        for address in (0x4DCD10,0x4DCDF0):
            def setup(env,result=result):
                t=menu_setup(0)(env)
                root=tree(env,0)
                env.write(t["obj"]+0x48,env.read(root,0xB0))
                methods=env.object(12,"initializer methods")
                env.put(methods,record(env,"node initializer",5,result=result),record(env,"node close"),record(env,"archive registration",1))
                env.put(t["obj"]+0x48,methods)
                f=env.object(0x28,"CFile",fill=0)
                vt=env.object(0x60,"CFile vtable",fill=0)
                env.put(f,vt)
                env.put(vt+0x20,record(env,"file name",1,mutate=lambda e,c:e.put(c.arguments[0],string(e))))
                env.put(vt+0x58,record(env,"file buffer",4,result=0))
                env.put(vt+0x30,record(env,"file seek",2,result=0))
                env.put(vt+0x2C,record(env,"file length",0,result=0))
                t["file"]=f
                t["data"]=env.object(64,"memory file data",fill=0xBA)
                return t
            args=(0x55,lambda t:t["file"],0x11,0x22,0x33,0x44) if address==0x4DCD10 else (0x55,lambda t:t["data"],64,0x11,0x22,0x33,0x44)
            yield case("controller load %x %d"%(address,result),address,setup,*args)
    for pattern in ((1,1,1,1,1,1,1,1),(1,0,0,1,0,0,0,0),(0,1,1,1,1,1,1,1),(1,1,1,0,1,1,1,1)):
        def setup(env,pattern=pattern):
            t=widget_setup()(env)
            env.put(t["obj"]+4,0,0,0,0)
            images=[env.object(0x20,"callback image",fill=0) for _ in range(8)]
            for n,p in enumerate(images):
                env.put(p+0x14,17+(n%3)*7,23+(7-n)*5)
            def image(e,c):
                n=e.calls_so_far(c.function)-1
                return images[n] if pattern[n] else 0
            t["create"]=env.stub("image factory CString by value","cdecl",1,image)
            return t
        yield case("image callback pattern %s"%(pattern,),0x4DE0E0,setup,0x71,lambda t:t["create"],0x39,0x83)
    for flags in (0x01,0x05,0x15,0x21,0x35):
        for address in (0x4DDC30,0x4DDCE0,0x4DD520):
            def setup(env,flags=flags,address=address):
                t=menu_setup(3,pressed=1 if address==0x4DDCE0 else 0,tick=2000,skip=1)(env)
                for w in t["items"]:
                    env.put(w+0x44,flags)
                env.override(0x546CD4,returns(1))
                return t
            args=(lambda t:t["items"][2],) if address==0x4DD520 else ()
            yield case("state variation %x %x"%(address,flags),address,setup,*args)
    for address in (0x4DE450,0x4DE4D0):
        for ownership in (0,1):
            def setup(env,ownership=ownership):
                t=widget_setup()(env)
                provider=env.object(0x400,"image provider",fill=0)
                link=env.object(16,"provider image link",fill=0)
                env.put(provider+0x3BC,link,link,2)
                image=env.get(env.get(t["obj"]+4))
                env.put(image+4,link)
                vt=env.object(8,"image destructor methods")
                env.put(vt,record(env,"image delete",1))
                env.put(image,vt)
                env.put(t["obj"]+0x38,env.object(32,"image ownership",fill=1),ownership)
                env.put(t["obj"]+0x48,provider)
                t["replacement"]=env.get(env.get(t["obj"]+4)+4)
                return t
            args=(lambda t:t["replacement"],0) if address==0x4DE4D0 else ()
            yield case("owned resource cleanup %x %d"%(address,ownership),address,setup,*args)
    for address in (0x4DE790,0x4DD270):
        def setup(env,address=address):
            t=menu_setup(3)(env) if address==0x4DD270 else widget_setup()(env)
            destination=env.object(16,"destination surface")
            interface=env.object(4,"physical surface")
            vt=env.object(0x18,"surface methods")
            env.put(destination+8,interface)
            env.put(interface,vt)
            env.put(vt+0x14,record(env,"DirectDraw blit",6,"stdcall",0))
            t["destination"]=destination
            targets=t["items"] if address==0x4DD270 else [t["obj"]]
            for w in targets:
                env.put(w+0x64,1)
            if address==0x4DD270:
                env.put(t["array"]+4,0)
            return t
        yield case("draw original surface %x"%address,address,setup,lambda t:t["destination"])
    for address in (0x4DEB50,0x4DF490):
        for mode in (0,1):
            for refill in (0,1):
                def setup(env,address=address,mode=mode,refill=refill):
                    t=widget_setup()(env) if address==0x4DEB50 else tree_setup(1,2)(env)
                    obj=t["obj"]
                    w=obj if address==0x4DEB50 else obj+0x3C
                    for n in range(8):env.put(w+0x18+n*4,string(env))
                    if address==0x4DF490:
                        env.put(obj+0x14,string(env))
                        data=(0x317).to_bytes(4,"little")+b"\0"*9+(0xA9).to_bytes(4,"little")+(2).to_bytes(2,"little")+b"\0"*4+(0x710).to_bytes(4,"little")+b"\0"*9+(0xB1).to_bytes(4,"little")+b"\0\0"+b"\0"*4+(0x711).to_bytes(4,"little")+b"\0"*9+(0xB2).to_bytes(4,"little")+b"\0\0"
                    else:data=b"\0"*8+(0x279).to_bytes(4,"little")
                    a=archive(env,data if mode else None)
                    buffer=env.get(a+0x24)
                    env.put(a+0x1C,4096)
                    if refill:env.put(a+0x28,buffer+(8 if address==0x4DEB50 else 4))
                    file=env.object(4,"archive physical file")
                    vt=env.object(0x44,"archive physical vtable")
                    env.put(file,vt)
                    env.put(vt+0x30,record(env,"archive seek",2))
                    env.put(vt+0x40,record(env,"archive write",2))
                    def read(e,c):
                        e.write(c.arguments[0],b"\0"*c.arguments[1])
                        return c.arguments[1]
                    env.put(vt+0x3C,env.stub("archive read","thiscall",2,read))
                    env.put(a+0x20,file)
                    t["archive"]=a
                    return t
                yield case("archive branches %x %d %d"%(address,mode,refill),address,setup,lambda t:t["archive"])
    for address in (0x4DF180,0x4DF040):
        def setup(env,address=address):
            t=tree_setup(1,2)(env)
            env.put(t["obj"]+4,1 if address==0x4DF040 else 0)
            return t
        yield case("recursive close %x"%address,address,setup)
    def owned_array_only(env):
        t=menu_setup(0)(env)
        env.put(t["obj"]+0xC,env.object(12,"owned uninitialized array",fill=0x45))
        return t
    yield case("destructor array without initialized flag",0x4DD1C0,owned_array_only)
    for result in (0,1):
        for count in (0,2):
            def setup(env,result=result,count=count):
                t=tree_setup(1,count)(env)
                obj=t["obj"]
                env.put(obj+0x40,0,0,0,0)
                images=[env.object(0x20,"loaded image",fill=0) for _ in range(8)]
                for n,p in enumerate(images):env.put(p+0x14,n+17,29-n)
                def create(e,c):return images[(e.calls_so_far(c.function)-1)%8]
                t["create"]=env.stub("node image factory","cdecl",1,create)
                if not result and count:
                    child=env.get(env.get(obj+0x1C))
                    env.put(env.get(child),record(env,"child init failure",5,result=0))
                return t
            yield case("initialize tree %d %d"%(result,count),0x4DF0E0,setup,0x761 if result else 0,lambda t:t["create"],0,0,0)
    def empty_provider(env):
        t=widget_setup()(env)
        env.put(t["obj"]+4,0,0,0,0)
        for n in range(8):env.put(t["obj"]+0x18+n*4,string(env))
        return t
    yield case("provider empty image names",0x4DE0E0,empty_provider,0x7183,0,0,0)
    for preferred in (False,True):
        def setup(env,preferred=preferred):
            t=menu_setup(3)(env)
            parent=tree(env,1,3)
            child=env.get(env.get(parent+0x1C))
            env.put(child+0x10,parent)
            if preferred:
                w=env.get(env.get(parent+0x1C)+4)+0x3C
                env.put(w+0x44,5)
            env.put(t["obj"]+0xF8,child)
            return t
        yield case("parent navigation preferred %s"%preferred,0x4DD030,setup)
    def activate_children(env):
        t=menu_setup(3)(env)
        root=tree(env,2,3)
        env.put(t["obj"]+0xF8,root)
        return t
    yield case("activation opens child submenu",0x4DD0E0,activate_children)
    def uninitialized_array(env):
        t=owned_array_only(env)
        env.put(t["obj"]+4,0)
        return t
    yield case("base destructor owns array independently",0x4DD1C0,uninitialized_array)
    def initialize_decorated(env):
        t=tree_setup(0)(env)
        obj=t["obj"]
        env.put(obj+0x40,0,0,0,0)
        images=[env.object(0x20,"decoration image",fill=0) for _ in range(8)]
        for n,p in enumerate(images):env.put(p+0x14,19+n,27-n)
        def create(e,c):return images[(e.calls_so_far(c.function)-1)%8]
        t["create"]=env.stub("decoration images","cdecl",1,create)
        description=env.get(obj+0x14)
        def increment_and_release_decorations(e,c):
            a=c.arguments[0]
            if a==description-12:
                bitmap=e.get(obj+0x74)
                e.write(bitmap,b"\0"*32)
            value=(e.get(a)+1)&0xffffffff
            e.put(a,value)
            return value
        env.override(0x5469EC,increment_and_release_decorations)
        return t
    yield case("decoration reloads bitmap after description callback",0x4DF0E0,initialize_decorated,0x761,lambda t:t["create"],1,0,0)
    def reloaded_append(env):
        t=menu_setup(2)(env)
        alternate=env.object(24,"allocation callback replacement",words=[0x19375A,0xC81E2F,0x779921,0xAB925C,0x9187,0x9162])
        env.put(t["obj"]+0x14,2)
        def allocate_and_change(e,c):
            result=e.object(c.arguments[0],"allocated grow storage",fill=0x73)
            e.put(t["obj"]+0xC,alternate,1)
            return result
        env.override(NEW,allocate_and_change)
        return t
    yield case("append rereads count and storage after allocator",0x4DD2C0,reloaded_append,0x752981)
    for n in range(20):
        count=random_source.randrange(1,6)
        flags=random_source.getrandbits(32)
        selected=random_source.randrange(count)
        x=random_source.randrange(-250,250)
        y=random_source.randrange(-250,250)
        tick=random_source.getrandbits(32)
        def setup(env,count=count,flags=flags,selected=selected,tick=tick,x=x,y=y):
            t=menu_setup(count,selected=selected,tick=tick)(env)
            for i,w in enumerate(t["items"]):
                env.put(w+0x44,flags^(i*0x13))
                env.put(w+0x54,x+i*7,y-i*11,31+i*9,43+i*13)
            return t
        yield case("random menu state %d"%n,0x4DDCE0,setup)
        yield case("random menu spacing %d"%n,0x4DD800,setup,n%2,x,y)
    def parent_without_children(env):
        t=menu_setup(0)(env)
        parent=tree(env,0)
        current=tree(env,0)
        env.put(current+0x10,parent)
        env.put(t["obj"]+0xF8,current)
        return t
    yield case("parent has no widgets",0x4DD030,parent_without_children)
    for mode in (0,1):
        for split in (0,17,19):
            def setup(env,mode=mode,split=split):
                t=tree_setup(1,2)(env)
                obj=t["obj"]
                env.put(obj+0x14,string(env))
                for n in range(8):env.put(obj+0x54+n*4,string(env))
                # root type, empty description, eight empty names, widget id,
                # child count, child kind, then a complete leaf archive.
                leaf=(0x1729).to_bytes(4,"little")+b"\0"*9+(0x5197).to_bytes(4,"little")+b"\0\0"
                payload=(0x7361).to_bytes(4,"little")+b"\0"*9+(0x9183).to_bytes(4,"little")+b"\x01\0"+b"\0"*4+leaf
                a=archive(env)
                raw=env.get(a+0x24)
                begin=raw+16
                env.write(begin,payload)
                env.put(a+0x14,mode)
                env.put(a+0x1C,4000)
                env.put(a+0x24,begin,begin+split,raw)
                state=env.object(4,"physical file cursor",words=[split])
                file=env.object(4,"segmented archive file")
                vt=env.object(0x44,"segmented archive methods")
                env.put(file,vt)
                def read(e,c):
                    offset=e.get(state)
                    size=c.arguments[1]
                    data=payload[offset:offset+size]
                    e.write(c.arguments[0],data+b"\0"*(size-len(data)))
                    e.put(state,offset+size)
                    return size
                env.put(vt+0x3C,env.stub("segmented archive read","thiscall",2,read))
                env.put(vt+0x40,record(env,"segmented archive write",2))
                env.put(a+0x20,file)
                t["archive"]=a
                return t
            yield case("archive exact field refill %d %d"%(mode,split),0x4DF490,setup,lambda t:t["archive"])
    # Spare capacities and neighboring fields deliberately differ from live counts.
    for address in (0x4DD450,0x4DD490,0x4DD520,0x4DD800,0x4DDCE0,0x4DD270):
        def setup(env,address=address):
            t=menu_setup(2,tick=1300)(env)
            spare=[widget(env,8+n,0x35 if n%2 else 0x21) for n in range(4)]
            array=env.object(24,"live and spare widget slots",words=t["items"]+spare)
            env.put(t["obj"]+0xC,array,2,6,3)
            env.put(t["obj"]+0x28,1,0x9173,900,400)
            t["array"]=array
            return t
        args={0x4DD450:(2,),0x4DD490:(1,),0x4DD520:(lambda t:t["items"][1],),0x4DD800:(1,-19,143),0x4DDCE0:(),0x4DD270:(0,)}[address]
        yield case("distinct controller count capacity %x"%address,address,setup,*args)
    for address in (0x4DF200,0x4DF270,0x4DF0E0):
        def setup(env,address=address):
            t=tree_setup(1,2)(env)
            obj=t["obj"]
            children=[env.get(env.get(obj+0x1C)+n*4) for n in range(2)]
            spare=[tree(env,0,index=20+n) for n in range(3)]
            env.put(obj+0x1C,env.object(20,"node live and spare slots",words=children+spare),2,5,7)
            if address==0x4DF0E0:
                child=children[1]
                env.put(env.get(child),record(env,"second child stops initializer",5,result=0))
            return t
        args=(999,) if address==0x4DF200 else ((0x71839ABC,) if address==0x4DF270 else (0x812,0,0,0,0))
        yield case("distinct node count capacity %x"%address,address,setup,*args)
    for flags in (1,5,0x15,0x21,0x35):
        for delta in (79,80,81,399,400,401):
            def setup(env,flags=flags,delta=delta):
                t=menu_setup(1,pressed=1,tick=900+delta)(env)
                env.put(t["items"][0]+0x44,flags)
                env.put(t["obj"]+0x28,0x7139)
                return t
            yield case("timer exact boundary %x %d"%(flags,delta),0x4DDCE0,setup)
    for index in range(8):
        def setup(env,index=index):
            t=widget_setup()(env)
            env.put(t["obj"]+0xC,13,7)
            # Distinct positive and negative dimensions independently set maxima.
            arr=env.get(t["obj"]+4)
            for n in range(8):
                env.put(env.get(arr+n*4)+0x14,(31-n*9)&0xffffffff,(n*7-15)&0xffffffff)
            replacement=env.object(0x20,"unique replacement dimensions",fill=0x3C)
            env.put(replacement+0x14,113,127)
            t["replacement"]=replacement
            return t
        yield case("replace state image %d"%index,0x4DE4D0,setup,lambda t:t["replacement"],index)
    for mode in (0,1):
        def setup(env,mode=mode):
            t=widget_setup()(env)
            for n in range(8):
                text=bytes([65+n])*(n+1)
                env.put(t["obj"]+0x18+n*4,string(env,text))
            payload=b"".join(bytes([n+1])+bytes([117-n])*(n+1) for n in range(8))+(0x798135AC).to_bytes(4,"little")
            t["archive"]=archive(env,payload if mode else None)
            return t
        yield case("archive eight distinct string lengths %d"%mode,0x4DEB50,setup,lambda t:t["archive"])
    # Rectangle pointers name transient source stack storage. Persist their
    # values so ordinary-ABI stack scratch differences remain observable.
    for n in range(6):
        width=random_source.randrange(13,79)
        height=random_source.randrange(81,149)
        boxwidth=random_source.randrange(151,211)
        boxheight=random_source.randrange(213,279)
        x=random_source.randrange(-300,0)
        y=random_source.randrange(1,300)
        def setup(env,width=width,height=height,boxwidth=boxwidth,boxheight=boxheight,x=x,y=y):
            t=widget_setup()(env)
            w=t["obj"]
            image=env.get(w+0x40)
            env.put(image+0x14,height,width)
            env.put(w+0x54,x,y,boxwidth,boxheight,1,0x39)
            env.put(w+0x48,0x57)
            destination=env.object(16,"observed drawing destination",fill=0xA7)
            interface=env.object(4,"observed physical surface")
            vt=env.object(0x18,"observed surface methods")
            receipt=env.object(96,"physical blit argument and rectangle receipt",fill=0xE3)
            env.put(destination+8,interface)
            env.put(interface,vt)
            def blit(e,c):
                e.put(receipt,c.receiver,*c.arguments)
                e.write(receipt+32,e.read(c.arguments[1],16))
                e.write(receipt+48,e.read(c.arguments[3],16))
                e.put(receipt+64,e.get(w+0x54),e.get(w+0x58),e.get(w+0x5C),e.get(w+0x60),e.get(image+0x14),e.get(image+0x18))
                return 0
            env.put(vt+0x14,env.stub("physical blit preserving rectangles","stdcall",6,blit))
            t["destination"]=destination
            return t
        yield case("drawing preserves centered rectangles %d"%n,0x4DE790,setup,lambda t:t["destination"])
    for address in (0x4DDA50,0x4DDAC0,0x4DDBC0):
        for pressed_index in (0,1,2,0x7913):
            def setup(env,address=address,pressed_index=pressed_index):
                t=menu_setup(3,selected=2,skip=1,disabled=(1,),pressed=0,tick=905)(env)
                env.put(t["obj"]+0x24,0,pressed_index,899,897,0x9751)
                return t
            yield case("navigation and press neighboring witnesses %x %d"%(address,pressed_index),address,setup)
    for ownership in (0,1):
        for image_present in (False,True):
            def setup(env,ownership=ownership,image_present=image_present):
                t=widget_setup()(env)
                provider=env.object(0x400,"cleanup distinct provider",fill=0)
                link=env.object(16,"cleanup image link",fill=0)
                env.put(provider+0x3BC,link,link,2)
                arr=env.get(t["obj"]+4)
                image=env.get(arr)
                env.put(image+4,link)
                methods=env.object(8,"cleanup image methods")
                env.put(methods,record(env,"cleanup delete observed",1))
                env.put(image,methods)
                env.put(arr,image if image_present else 0,0,0,0,0,0,0,0)
                env.put(t["obj"]+0x38,env.object(32,"cleanup bitmap",fill=0x17),ownership,0)
                env.put(t["obj"]+0x48,provider,0,0x7159)
                # Positive count, a different nonzero capacity and growth.
                env.put(t["obj"]+8,8,13,7)
                return t
            yield case("cleanup ownership and current image differ %d %s"%(ownership,image_present),0x4DE450,setup)
