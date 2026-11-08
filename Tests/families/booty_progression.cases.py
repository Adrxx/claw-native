"""Original-backed Booty controller cases; only physical imports are replaced."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def obj(env, size, name, fill=0xA7):
    return env.object(size, name, fill=fill)


def record(env, log, tag, call):
    at = env.get(log)
    env.put(log + 4 + at * 32, tag, call.receiver, len(call.arguments), *call.arguments[:5])
    env.put(log, at + 1)


def basic(env):
    target = obj(env, 0x200, "controller", 0)
    log = obj(env, 0x1000, "callback receipts", 0)
    env.override(0x546D50, returns(0xFEDCBA98))
    window = obj(env, 8, "window")
    owner = obj(env, 0x150, "owner", 0)
    env.put(window + 4, 0x13579BDF)
    env.put(owner + 4, window)
    env.put(target + 4, owner)
    return {"target": target, "owner": owner, "window": window, "log": log}


def cleanup(owner=True, resource=False, first=False, second=False, subsystem=False):
    def setup(env):
        t = basic(env); target = t["target"]
        parent = obj(env, 0x30, "resource owner", 0)
        middle = obj(env, 0x30, "subsystem owner", 0)
        env.put(parent + 0x28, middle)
        env.put(target + 0xC, parent if owner else 0)
        if subsystem:
            sound = obj(env, 0x80, "empty sound list", 0)
            env.put(middle + 0x2C, sound)
        env.put(target + 0x34, 0xF0123456)
        if resource:
            manager = obj(env, 0x68, "empty resource map", 0)
            value = obj(env, 16, "resource")
            env.put(manager + 0x64, value)
            env.put(parent + 0x18, manager)
            env.put(target + 0x2C, value)
        manager = obj(env, 0x3E0, "resource list manager", 0)
        env.put(parent + 0x1C, manager)
        nodes = []
        for slot, present in ((0x3C, first), (0x40, second)):
            if present:
                node = obj(env, 12, "list node", 0)
                value = obj(env, 8, "list resource")
                vt = obj(env, 4, "resource vtable")
                def destroy(env, call, slot=slot):
                    record(env, t["log"], slot, call)
                    return 0x81726354
                env.put(vt, env.stub("resource destructor", "thiscall", 1, destroy))
                env.put(value, vt, node)
                env.put(target + slot, value)
                nodes.append(node)
        if nodes:
            for i, node in enumerate(nodes):
                env.put(node, nodes[i+1] if i+1 < len(nodes) else 0, nodes[i-1] if i else 0)
            env.put(manager + 0x3BC, nodes[0], nodes[-1], len(nodes) + 2, 0)
        return t
    return setup


def movie_setup(name=b"", opened=0xFFFFFFFF, state=0, table=-1, descriptor=False, interface=False):
    def setup(env):
        t = basic(env); target=t["target"]
        filename=obj(env,len(name)+1,"movie filename",0); env.write(filename,name+b"\0")
        env.put(target+0x100,filename); env.put(target+0x9C,state)
        env.override(0x546A30,returns(opened))
        env.put(0x525520, *([table & 0xFFFFFFFF]*17))
        clock(env)
        resource=obj(env,0x24,"movie resource",0)
        child=obj(env,0x14,"graphics owner",0)
        graphics=obj(env,0x30,"graphics",0)
        handle=obj(env,4,"interface holder",0)
        desc=obj(env,0x78,"graphics descriptor") if descriptor else 0
        env.put(resource+4,child); env.put(child+0x10,graphics)
        env.put(graphics+0x2C,desc); env.put(resource+0x1C,handle)
        env.put(handle,obj(env,4,"opaque graphics interface") if interface else 0)
        env.put(target+0x30,resource)
        if desc: env.put(desc+8,0)  # original movie init rejects absent surface
        return t
    return setup


def clock(env):
    stamp=struct.pack("<8H",2020,6,1,15,12,34,56,0)
    env.write(0x540B70,stamp)
    env.put(0x540B68,0)
    def time(env,call):
        env.write(call.arguments[0],stamp)
        return 0
    env.override(0x546A34,time); env.override(0x5469B4,time)
    def timezone(env,call):
        env.write(call.arguments[0],bytes(172))
        return 0
    env.override(0x546A3C,timezone)
    def increment(env,call):
        result=(env.get(call.arguments[0])+1)&0xFFFFFFFF
        env.put(call.arguments[0],result)
        return result
    def decrement(env,call):
        result=(env.get(call.arguments[0])-1)&0xFFFFFFFF
        env.put(call.arguments[0],result)
        return result
    env.override(0x5469EC,increment); env.override(0x5469E8,decrement)
    thread=obj(env,0x74,"CRT thread",0)
    env.override(0x546A7C,returns(thread))
    env.override(0x5469E4,lambda env,call: len(env.cstr(call.arguments[0])))


def readiness(first, second, status=0, restore=0, mutate=False):
    def setup(env):
        t=basic(env); target=t["target"]
        for slot,present in ((0x10,first),(0x18,second)):
            if present:
                sub=obj(env,0x30,"readiness subsystem",0)
                wrapper=obj(env,12,"COM wrapper",0)
                com=obj(env,4,"COM object")
                vt=obj(env,0x70,"COM vtable",0)
                def query(env,call,slot=slot):
                    record(env,t["log"],slot,call)
                    if mutate: env.put(target+0x18,0)
                    return status
                def recover(env,call,slot=slot):
                    record(env,t["log"],slot+1,call)
                    return restore
                env.put(vt+0x60,env.stub("COM status","stdcall",1,query))
                env.put(vt+0x6C,env.stub("COM restore","stdcall",1,recover))
                env.put(com,vt); env.put(wrapper+8,com); env.put(sub+0x2C,wrapper)
                env.put(target+slot,sub)
        parent=obj(env,8,"readiness parent",0); env.put(parent+4,target)
        outer=obj(env,0x10,"readiness outer",0); env.put(outer+0xC,parent)
        t["outer"]=outer
        return t
    return setup


def transition(kind, seen=0, scene_type=3, flags=(0,0), swap=False):
    def setup(env):
        t=basic(env); target=t["target"]
        old=obj(env,0x260,"old child",0); vt=obj(env,0x2C,"old vtable",0)
        newvt=obj(env,0x2C,"replacement vtable",0)
        env.put(old,vt); env.put(target+0x154,old,seen)
        alternate=obj(env,0x260,"alternate child",0)
        final=obj(env,0x260,"child published during constructor",0)
        env.put(alternate,vt); env.put(final,newvt)
        def logmethod(tag, result=0):
            def effect(env,call):
                record(env,t["log"],tag,call)
                if swap and tag==0x104:
                    env.put(target+0x154,final)
                return result
            return effect
        for off,argc in ((0,1),(4,3),(0x24,1)):
            env.put(newvt+off,env.stub("new child callback","thiscall",argc,logmethod(0x100+off)))
        env.put(newvt+0x10,env.stub("new type","thiscall",0,logmethod(0x110,7)))
        def handoff(env,call):
            record(env,t["log"],0x28,call)
            env.put(env.get(target+0x154),newvt)
            return 0xDEADBEEF
        env.put(vt+0x28,env.stub("old handoff","thiscall",1,handoff))
        env.put(vt,env.stub("old destructor","thiscall",1,logmethod(0)))
        def gettype(env,call):
            record(env,t["log"],0x10,call)
            if swap: env.put(target+0x154,alternate)
            return kind
        env.put(vt+0x10,env.stub("old type","thiscall",0,gettype))
        if kind==2 and not seen:
            scene=obj(env,0x260,"current scene",0); scenevt=obj(env,0x14,"scene vtable",0)
            env.put(scene,scenevt); env.put(scene+0x258,*flags)
            env.put(scenevt+0x10,env.stub("scene type","thiscall",0,logmethod(0x210,scene_type)))
            array=obj(env,4,"scene array"); env.put(array,scene)
            env.put(t["owner"]+0xE0,array,1)
        return t
    return setup


# Build the original's five-bucket name map rather than replacing its lookup.
def name_map(env, entries, label):
    root=obj(env,0x80,label,0)
    buckets=obj(env,0x50,label+" buckets",0)
    env.put(root+0x40,buckets)
    heads={}
    for name,resource in entries:
        text=obj(env,len(name)+1,label+" key",0); env.write(text,name+b"\0")
        env.put(resource,text)
        bucket=len(name)%5
        node=obj(env,0x18,label+" map node",0)
        env.put(node+4,heads.get(bucket,0))
        env.put(node+0x14,resource)
        heads[bucket]=node+4
    for bucket,head in heads.items(): env.put(buckets+bucket*16+8,head)
    return root


def initializer(level_present, states_present, claw_present, level):
    def setup(env):
        t=basic(env)
        booty=name_map(env,[],"booty resource")
        states=name_map(env,[(b"BOOTY",booty)] if states_present else [],"states resource")
        levelobj=name_map(env,[],"level resource")
        clawobj=name_map(env,[],"claw resource")
        entries=[]
        if level_present: entries.append((f"LEVEL{level}".encode(),levelobj))
        if states_present: entries.append((b"STATES",states))
        if claw_present: entries.append((b"CLAW",clawobj))
        root=name_map(env,entries,"root resource map")
        resources=obj(env,0x28,"resource facade",0); env.put(resources+0x24,root)
        env.put(t["owner"]+0x34,resources)
        env.put(t["owner"]+0x30,0x11223344); env.put(t["owner"]+0x44,0x55667788)
        return t
    return setup


def active_surfaces(env):
    t=basic(env); target=t["target"]
    palette=obj(env,0x10,"palette",0)
    palettecom=obj(env,4,"palette COM"); pvt=obj(env,0x1C,"palette COM vtable",0)
    colors=obj(env,0x400,"palette colors",0xC3)
    def read(env,call):
        record(env,t["log"],0x310,call); return 0
    def write(env,call):
        record(env,t["log"],0x318,call); return 0
    env.put(pvt+0x10,env.stub("palette GetEntries","stdcall",5,read))
    env.put(pvt+0x18,env.stub("palette SetEntries","stdcall",5,write))
    env.put(palettecom,pvt); env.put(palette+4,palettecom); env.put(palette+0xC,colors)
    resource=obj(env,0x14,"palette owner",0); env.put(resource+0x10,palette)
    env.put(target+0x2C,resource)
    parent=obj(env,8,"surface owner",0); pair=obj(env,0x18,"surface pair",0)
    env.put(target+0xC,parent); env.put(parent+4,pair)
    for slot in (0x10,0x14):
        wrapper=obj(env,0x30,"surface wrapper",0); surface=obj(env,0xC,"surface",0)
        com=obj(env,4,"surface COM"); vt=obj(env,0x30,"surface COM vtable",0)
        def method(env,call,slot=slot):
            record(env,t["log"],0x400+slot,call); return 0
        env.put(vt+0x14,env.stub("surface Blt","stdcall",6,method))
        env.put(vt+0x2C,env.stub("surface Flip","stdcall",3,method))
        env.put(com,vt); env.put(surface+8,com); env.put(wrapper+0x2C,surface); env.put(pair+slot,wrapper)
    env.override(0x546DF0,lambda env,call: env.calls_so_far(0x546DF0)*1000)
    return t


def movie_physical(play="key", init=True, file_ok=True, stream_ok=True):
    def setup(env):
        t=movie_setup(b"movie.fec",0,1,1,True,True)(env)
        movie_address=obj(env,4,"observed movie receiver",0)
        resource=env.get(t["target"]+0x30)
        graphics=env.get(env.get(resource+4)+0x10)
        desc=env.get(graphics+0x2C)
        surface=obj(env,4,"DirectDraw surface COM")
        svt=obj(env,0x80,"surface methods",0)
        def surface_method(env,call):
            record(env,t["log"],0x550,call); return 0
        for off,argc in ((8,1),(0x14,6)):
            env.put(svt+off,env.stub("DirectDraw surface method","stdcall",argc,surface_method))
        env.put(svt+0x64,env.stub("surface Lock failure","stdcall",5,returns(0x80004005)))
        env.put(surface,svt)
        interface=env.get(env.get(resource+0x1C))
        ivt=obj(env,0x80,"DirectDraw methods",0)
        def create_surface(env,call):
            record(env,t["log"],0x518,call)
            env.put(movie_address,call.arguments[2]-0x1C)
            env.put(call.arguments[2],surface)
            return 0
        env.put(ivt+0x18,env.stub("IDirectDraw CreateSurface","stdcall",4,create_surface))
        env.put(interface,ivt)
        env.put(desc+8,surface if init else 0)
        env.put(desc+0x14,8,8)
        env.put(desc+0x60,32)
        env.override(0x546C7C,returns(0x778899))
        env.override(0x546914,returns(0))
        env.override(0x546C80,returns(1))
        env.override(0x546D54,returns(0))
        env.override(0x546AD0,returns(0))
        def copy_string(env,call):
            dst,src,n=call.arguments
            data=env.cstr(src)
            if isinstance(data,str): data=data.encode("latin-1")
            env.write(dst,data[:max(0,n-1)]+b"\0")
            return dst
        env.override(0x5469CC,copy_string)
        env.override(0x546B00,returns(0x1234 if file_ok else 0xFFFFFFFF))
        env.override(0x546A04,returns(1))
        cursor=obj(env,4,"physical file cursor",0)
        fec=bytearray(283)
        fec[:3]=b"FEC"
        struct.pack_into("<3I",fec,3,0,0,1)
        struct.pack_into("<H",fec,15+0x106,0x2B8)
        def read_file(env,call):
            _,dst,count,read,_=call.arguments
            pos=env.get(cursor)
            data=bytes(fec[pos:pos+count])
            env.write(dst,data); env.put(read,len(data)); env.put(cursor,pos+len(data))
            return 1
        def seek(env,call):
            _,offset,_,origin=call.arguments
            pos=(0 if origin==0 else env.get(cursor) if origin==1 else len(fec))+offset
            pos &= 0xFFFFFFFF
            env.put(cursor,pos)
            return pos
        env.override(0x546AFC,read_file); env.override(0x546AF4,seek)
        smack=obj(env,0x400,"Smack decoder handle",0)
        env.put(smack+4,2,2,1)
        env.override(0x546EBC,returns(0))
        env.override(0x546EC0,returns(0))
        env.override(0x546EA4,returns(smack if stream_ok else 0))
        env.override(0x546EB4,returns(0))
        env.override(0x546DF8,returns(0))
        env.override(0x546EA8,returns(1 if play=="wait" else 0))
        def peek(env,call):
            if play in ("wait","end") and env.calls_so_far(0x546CAC)==1:
                return 0
            env.put(call.arguments[0],0,0x100,0x20,0,1234,17,29)
            return 1
        env.override(0x546CAC,peek)
        return t
    return setup


def cases(random_source):
    for address,argc in ((0x40AF30,1),(0x40AF40,2),(0x40AF50,3),(0x4BB030,0),(0x4BD240,0),(0x4BD250,0),(0x4CE8B0,0)):
        yield Case(f"constant ABI {address:x}",address,arguments=tuple(random_source.getrandbits(32) for _ in range(argc)))
    for value in (0,1,0x80000000,random_source.getrandbits(32)):
        def setup(env,value=value):
            t=basic(env); env.put(t["target"]+0x34,value); return t
        yield Case(f"status word {value:x}",0x40AF20,setup,receiver=lambda t:t["target"])
    for address in (0x40AFC0,0x40B700,0x48F180):
        for options in ({},{"resource":True},{"first":True},{"second":True},{"first":True,"second":True},{"subsystem":True}):
            yield Case(f"cleanup {address:x} {options}",address,cleanup(**options),receiver=lambda t:t["target"])
    for flag in (0,1,2,0x100,0x101,0xFFFFFFFF):
        yield Case(f"delete low bit {flag:x}",0x40AFA0,cleanup(),receiver=lambda t:t["target"],arguments=(flag,))
    for present in (False,True):
        def setup(env,present=present):
            t=basic(env); env.put(t["target"]+4,obj(env,19,"owned storage") if present else 0); return t
        yield Case(f"small destructor {present}",0x42D4C0,setup,receiver=lambda t:t["target"])
    yield Case("small constructor",0x42D4A0,basic,receiver=lambda t:t["target"])
    def constructor(env):
        t=basic(env); env.write(t["target"],bytes([0x93])*0x200); clock(env); return t
    yield Case("movie members constructor and CRT time seed",0x42B4B0,constructor,receiver=lambda t:t["target"])
    for state in (0,1,0x80000000):
        def setup(env,state=state):
            t=basic(env); env.put(t["target"]+0x154,state); return t
        yield Case(f"post progression {state:x}",0x40B740,setup,receiver=lambda t:t["target"])
        for key in (0x1B,0x20,0xD,0,0x1001B,0xFFFFFFFF):
            yield Case(f"key {key:x} state {state:x}",0x40B7D0,setup,receiver=lambda t:t["target"],arguments=(key,random_source.getrandbits(32)))
    for result in (0,1,0x100,0x80000000):
        for field in (0,0x12345678):
            def setup(env,result=result,field=field):
                t=basic(env); vt=obj(env,16,"predicate vtable",0)
                def predicate(env,call):
                    record(env,t["log"],12,call); env.put(t["target"]+0x2C,field); return result
                env.put(vt+12,env.stub("predicate","thiscall",0,predicate)); env.put(t["target"],vt)
                env.put(t["target"]+0x2C,field^0xFFFFFFFF); return t
            for address in (0x40B7A0,0x40B7C0):
                yield Case(f"predicate {address:x} {result:x} {field:x}",address,setup,receiver=lambda t:t["target"])
    for first,second in ((False,False),(True,False),(False,True),(True,True)):
        for status,restore in ((0,0),(1,0),(1,1),(0x100,0x80000000)):
            for address in (0x4CA930,0x40B780):
                yield Case(f"readiness {address:x} {first} {second} {status} {restore}",address,readiness(first,second,status,restore),receiver=lambda t,a=address:t["outer"] if a==0x40B780 else t["target"])
    for kind,seen in ((0,0),(4,0),(0xFFFFFFFF,0),(1,0),(3,0),(2,1)):
        yield Case(f"transition type {kind} seen {seen}",0x40B330,transition(kind,seen),receiver=lambda t:t["target"])
    for st in (2,3):
        for flags in ((0,0),(1,0),(0,1),(0x80000000,7)):
            yield Case(f"scene transition {st} {flags}",0x40B330,transition(2,0,st,flags),receiver=lambda t:t["target"])
    for name,opened,state,index,table in ((b"",0,0,0,-1),(b"x",0xFFFFFFFF,0,0,-1),(b"x",0,1,0,-1),(b"x",0,0,-3,-1),(b"x",0,0,16,-1),(b"x",0,0,0,-1),(b"x",0,0,15,-1),(b"x",0,0,0,0)):
        yield Case(f"movie validation {name!r} {opened:x} {state} {index} {table}",0x42B140,movie_setup(name,opened,state,table),receiver=lambda t:t["target"],arguments=(index&0xFFFFFFFF,))
    def wrapper(env):
        t=movie_setup()(env)
        outer=obj(env,0x18,"movie wrapper",0)
        env.put(outer+4,t["target"]); env.put(outer+0x14,0xFFFFFFFF)
        t["outer"]=outer
        return t
    yield Case("movie wrapper rejects empty filename",0x40B720,wrapper,receiver=lambda t:t["outer"],arguments=(0xABCDEF01,))
    def inactive(env):
        t=basic(env); env.put(t["target"]+0x2C,0); return t
    yield Case("surface cleanup inactive",0x48D320,inactive,receiver=lambda t:t["target"],arguments=(0xFFFFFFFF,))
    for level in (1,-1,random_source.randrange(2,16)):
        for a,b,c in ((False,False,False),(True,False,False),(True,True,False),(True,True,True)):
            yield Case(f"original resource initializer {level} {a}{b}{c}",0x40B6A0,initializer(a,b,c,level),receiver=lambda t:t["target"],arguments=(lambda t:t["owner"],level&0xFFFFFFFF,0x89ABCDEF))
    yield Case("active surface cleanup repeats both original calls",0x48D320,active_surfaces,receiver=lambda t:t["target"],arguments=(0x10203040,))
    for state,index in ((1,-2),(0,0)):
        for desc,inter in ((False,False),(False,True),(True,False),(True,True)):
            yield Case(f"movie graphics guards {state} {desc} {inter}",0x42B140,movie_setup(b"x",0,state,0,desc,inter),receiver=lambda t:t["target"],arguments=(index&0xFFFFFFFF,))
    yield Case("ownerless resource cleanup",0x48F180,cleanup(owner=False),receiver=lambda t:t["target"])
    yield Case("readiness callback clears second subsystem before reload",0x4CA930,readiness(True,True,1,0,True),receiver=lambda t:t["target"])
    def absent_scene(env):
        t=transition(2)(env); env.put(t["owner"]+0xE4,0); return t
    yield Case("transition without active scene",0x40B330,absent_scene,receiver=lambda t:t["target"])
    for init,file_ok,stream_ok in ((False,True,True),(True,False,True),(True,True,False),(True,True,True)):
        yield Case(f"physical movie {init} {file_ok} {stream_ok}",0x42B140,movie_physical(init=init,file_ok=file_ok,stream_ok=stream_ok),receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,))
    def optional_graphics(env):
        t=movie_setup(b"x",0,1,0,True,True)(env)
        optional=obj(env,0x18,"optional movie graphics",0)
        env.put(optional+0x14,0x89ABCDEF)
        env.put(env.get(t["target"]+0x30)+0x20,optional)
        return t
    yield Case("movie optional graphics flags copied",0x42B140,optional_graphics,receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,))
    for mode in ("wait","end"):
        yield Case(f"movie playback {mode}",0x42B140,movie_physical(play=mode),receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,))
    for kind,seen in ((1,0),(3,0),(2,1)):
        yield Case(f"transition callbacks republish child {kind}",0x40B330,transition(kind,seen,swap=True),receiver=lambda t:t["target"])

    # Distinct words make dropped stores and neighboring-field reads observable.
    for trial in range(4):
        words=tuple(random_source.getrandbits(32) | 1 for _ in range(0x200//4))
        def dirty_constructor(env,words=words):
            t=basic(env)
            env.put(t["target"],*words)
            return t
        yield Case(f"small constructor distinct words {trial}",0x42D4A0,dirty_constructor,receiver=lambda t:t["target"])
        for level_present,states_present,claw_present in ((False,False,False),(True,False,False),(True,True,False),(True,True,True)):
            def dirty_initializer(env,words=words,a=level_present,b=states_present,c=claw_present):
                t=initializer(a,b,c,7)(env)
                env.put(t["target"],*words)
                return t
            yield Case(f"initializer preserves dirty fields {trial} {level_present}{states_present}{claw_present}",0x40B6A0,dirty_initializer,receiver=lambda t:t["target"],arguments=(lambda t:t["owner"],7,words[-1]))

    for index in (-0x80000000,-3,-2,-1,0,14,15,16,0x7FFFFFFF):
        for table in (-1,0,1):
            yield Case(f"movie signed index boundary {index} table {table}",0x42B140,movie_setup(b"x",0,0,table),receiver=lambda t:t["target"],arguments=(index&0xFFFFFFFF,))
    for state in (1,0x80000000,0xFFFFFFFF):
        yield Case(f"movie special index in nonzero state {state:x}",0x42B140,movie_setup(b"x",0,state,1),receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,))

    for kind,seen in ((1,0),(3,0),(2,1)):
        salt=random_source.getrandbits(32)|1
        def dirty_transition(env,kind=kind,seen=seen,salt=salt):
            t=transition(kind,seen,swap=True)(env)
            env.put(t["target"]+0x10,salt^0x13579BDF,salt,salt^0x2468ACE0)
            def allocate_dirty(env,call):
                memory=obj(env,call.arguments[0],"nonzero constructed child")
                for off in range(0,call.arguments[0]//4*4,4):
                    env.put(memory+off,(salt+off*0x10203)&0xFFFFFFFF)
                return memory
            env.override(0x4F63EC,allocate_dirty)
            return t
        yield Case(f"transition distinct constructor fields {kind}",0x40B330,dirty_transition,receiver=lambda t:t["target"])

    for flags in ((0,0),(0,1),(1,0),(1,1)):
        def message_reload(env,flags=flags):
            t=transition(2,0,3,flags)(env)
            env.put(0x537360,0x96ABCD71)
            replacement=obj(env,8,"replacement window",0)
            env.put(replacement+4,0x2468ACE1)
            def post(env,call):
                record(env,t["log"],0x650,call)
                env.put(t["log"]+0xE00,env.get(t["target"]+0x158),env.get(0x537360))
                env.put(t["owner"]+4,replacement)
                return 0
            env.override(0x546D50,post)
            return t
        yield Case(f"message publication and window reload {flags}",0x40B330,message_reload,receiver=lambda t:t["target"])

    for optional in (0,1,0x89ABCDEF):
        descriptor_words=tuple(random_source.getrandbits(32)|1 for _ in range(27))
        def distinct_movie(env,optional=optional,descriptor_words=descriptor_words):
            t=movie_physical()(env)
            resource=env.get(t["target"]+0x30)
            graphics=env.get(env.get(resource+4)+0x10)
            desc=env.get(graphics+0x2C)
            env.put(desc+0xC,*descriptor_words)
            env.put(desc+0x14,8,8)
            env.put(desc+0x60,32)
            extra=obj(env,0x18,"movie optional descriptor",0)
            env.put(extra+0x14,optional)
            env.put(resource+0x20,extra)
            env.put(t["target"]+0x120,optional)
            interface=env.get(env.get(resource+0x1C))
            methods=env.get(interface)
            surface=env.get(desc+8)
            def create(env,call):
                record(env,t["log"],0x518,call)
                env.write(t["log"]+0xC00,env.read(call.arguments[1],0x6C))
                env.put(call.arguments[2],surface)
                return 0
            env.put(methods+0x18,env.stub("CreateSurface copies descriptor receipt","stdcall",4,create))
            return t
        yield Case(f"movie distinct descriptor and optional flags {optional:x}",0x42B140,distinct_movie,receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,))

    # At 0x42b186 the argument is [esp+0x86c4], so the settled local
    # frame is entry ESP-0x86c0. At 0x42b29d the push and sub total
    # 0x70 bytes, so [esp+0x84] writes the result local at old esp+0x14.
    # Failures clear that word; successful playback returns the stored one.
    # Seed it independently from fields that the original explicitly clears.
    # Leave untouched pointer-like members zero so every case stays valid.
    for trial in range(3):
        local_offsets=(0x14,0x1C,0x20,0x28,0x2C,0x30,0x34,0x38,0x3C,
                       0x518,0x51C,0x520,0x524,0x534,0x538,0x53C,
                       0x540,0x544,0x548,0x54C,
                       0x550,0x554,0x558,0x684)
        seed=tuple((offset-0x86C0,
                    struct.pack("<I",random_source.getrandbits(32)|1))
                   for offset in local_offsets)
        for mode in ("key","wait","end"):
            yield Case(f"movie nonzero local words {trial} playback {mode}",
                       0x42B140,movie_physical(play=mode),
                       receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,),
                       initial_stack=seed)
        for init,file_ok,stream_ok in ((False,True,True),
                                       (True,False,True),
                                       (True,True,False)):
            yield Case(f"movie nonzero local words {trial} failure {init} {file_ok} {stream_ok}",
                       0x42B140,movie_physical(init=init,file_ok=file_ok,stream_ok=stream_ok),
                       receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,),
                       initial_stack=seed)
        yield Case(f"movie nonzero local words {trial} graphics absent",
                   0x42B140,movie_setup(b"x",0,1,0,False,False),
                   receiver=lambda t:t["target"],arguments=(0xFFFFFFFE,),
                   initial_stack=seed)

    # Successful physical rendering exposes the initialized local movie words
    # to the decoder. RGB masks are reported by DirectDraw, then interpreted
    # by unchanged 0x4f0f90; never inject the derived copy flags into the movie.
    formats=((32,(0xFF0000,0xFF00,0xFF)),
             (16,(0x7C00,0x3E0,0x1F)),
             (16,(0xF800,0x7E0,0x1F)),
             (16,(0xFC00,0x3E0,0x1F)),
             (16,(0x7C00,0x3E0,0x3F)))
    for depth,masks in formats:
        for restore_first in (False,True):
            descriptor_words=tuple(random_source.getrandbits(32)|1 for _ in range(27))
            pitch=random_source.randrange(13,30)
            pixel_bytes=bytes(random_source.getrandbits(8) for _ in range(pitch*3))
            decoded_bytes=bytes(random_source.getrandbits(8) for _ in range(24))
            local_offsets=(0x14,0x1C,0x20,0x28,0x2C,0x30,0x34,0x38,0x3C,
                           0x518,0x51C,0x520,0x524,0x534,0x538,0x53C,
                           0x540,0x544,0x548,0x54C,0x550,0x554,0x558,0x684)
            seed=tuple((offset-0x86C0,struct.pack("<I",random_source.getrandbits(32)|1))
                       for offset in local_offsets)
            def successful_render(env,depth=depth,masks=masks,restore_first=restore_first,
                                  descriptor_words=descriptor_words,pitch=pitch,
                                  pixel_bytes=pixel_bytes,decoded_bytes=decoded_bytes):
                t=movie_physical(play="end")(env)
                resource=env.get(t["target"]+0x30)
                graphics=env.get(env.get(resource+4)+0x10)
                desc=env.get(graphics+0x2C)
                env.put(desc+0xC,*descriptor_words)
                env.put(desc+0x14,7,11)
                env.put(desc+0x60,depth)
                interface=env.get(env.get(resource+0x1C))
                methods=env.get(interface)
                pixels=obj(env,len(pixel_bytes),"locked movie pixels",0)
                env.write(pixels,pixel_bytes)
                decoder=obj(env,0x400,"distinct 3 by 2 decoder handle",0)
                env.put(decoder+4,3,2,1)
                env.override(0x546EA4,returns(decoder))
                surface=env.get(desc+8)
                old_methods=env.get(surface)
                surface_methods=obj(env,0x84,"render surface methods",0)
                env.write(surface_methods,env.read(old_methods,0x80))
                env.put(surface,surface_methods)
                def display_mode(env,call):
                    record(env,t["log"],0x530,call)
                    env.put(call.arguments[1]+0x58,*masks)
                    return 0
                env.put(methods+0x30,env.stub("DirectDraw GetDisplayMode RGB masks","stdcall",2,display_mode))
                def lock(env,call):
                    record(env,t["log"],0x564,call)
                    if restore_first and env.calls_so_far(lock_stub)==1:
                        return 0x887601C2
                    descriptor=call.arguments[2]
                    env.put(descriptor+0x10,pitch)
                    env.put(descriptor+0x24,pixels)
                    return 0
                def restore(env,call):
                    record(env,t["log"],0x56C,call)
                    return 0
                def unlock(env,call):
                    record(env,t["log"],0x580,call)
                    env.write(t["log"]+0xA80,env.read(pixels,len(pixel_bytes)))
                    return 0x80004005 if restore_first else 0
                lock_stub=env.stub("movie Lock succeeds after optional restore","stdcall",5,lock)
                env.put(surface_methods+0x64,lock_stub)
                env.put(surface_methods+0x6C,env.stub("movie Restore","stdcall",1,restore))
                env.put(surface_methods+0x80,env.stub("movie Unlock pixel receipt","stdcall",2,unlock))
                def decoder_copy(env,call):
                    record(env,t["log"],0xEC4,call)
                    env.put(t["log"]+0xA00,call.receiver,*call.arguments)
                    return 0x13579BDF
                def decoder_frame(env,call):
                    record(env,t["log"],0xEC8,call)
                    env.write(pixels,decoded_bytes[:12])
                    env.write(pixels+pitch,decoded_bytes[12:])
                    return 0x2468ACE0
                def rectangles(env,call):
                    record(env,t["log"],0xEC0,call)
                    if env.calls_so_far(0x546EC0)==1:
                        env.put(call.arguments[0]+0x380,0,0,3,2)
                        return 1
                    return 0
                env.override(0x546EC4,decoder_copy)
                env.override(0x546EC8,decoder_frame)
                env.override(0x546EC0,rectangles)
                return t
            yield Case(f"movie decoder successful copy depth {depth} masks {masks} restore {restore_first}",
                       0x42B140,successful_render,receiver=lambda t:t["target"],
                       arguments=(0xFFFFFFFE,),initial_stack=seed)
