"""Popup inputs built from the original object layouts and physical services."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def object_(env, size, name=None, **options):
    options.setdefault("fill", 0)
    return env.object(size, name, **options)

def string(env, text, refs=1):
    data = text.encode('ascii')
    block = object_(env,13 + len(data), 'CString header and text')
    env.put(block, refs, len(data), len(data))
    env.write(block + 12, data + b'\0')
    return block + 12


def platform(env, rect=(7, 11, 308, 214), resource=True):
    empty = string(env, '', -1)
    env.put(0x52e1c8, empty - 12, empty)
    env.put(0x540e88, 0)
    def atomic(delta):
        def effect(e, c):
            value = (e.get(c.arguments[0]) + delta) & 0xffffffff
            e.put(c.arguments[0], value)
            return value
        return effect
    env.override(0x5469e8, atomic(-1))
    env.override(0x5469ec, atomic(1))
    env.override(0x5469e4, lambda e,c: len(e.cstr(c.arguments[0])))
    def putrect(e,c):
        e.put(c.arguments[0], *c.arguments[1:])
        return 1
    env.override(0x546cdc, lambda e,c: (e.put(c.arguments[0],0,0,0,0) or 1))
    env.override(0x546d5c, putrect)
    env.override(0x546d58, lambda e,c: (e.write(c.arguments[0],e.read(c.arguments[1],16)) or 1))
    def offset(e,c):
        p,x,y=c.arguments
        e.put(p, e.get(p)+x,e.get(p+4)+y,e.get(p+8)+x,e.get(p+12)+y)
        return 1
    env.override(0x546b7c,offset)
    env.override(0x546d04,returns(1))
    env.override(0x546cd0,lambda e,c: (e.put(c.arguments[0],91,157) or 1))
    env.override(0x546cc0,lambda e,c: (e.put(c.arguments[1],*rect) or 1))
    env.override(0x546c44,returns(3))
    def empty_rect(e,c):
        p=c.arguments[0]
        signed=lambda v:v if v<0x80000000 else v-0x100000000
        return int(signed(e.get(p+8))<=signed(e.get(p)) or signed(e.get(p+12))<=signed(e.get(p+4)))
    env.override(0x546d4c,empty_rect)
    def union_rect(e,c):
        signed=lambda v:v if v<0x80000000 else v-0x100000000
        rectangles=[]
        for p in c.arguments[1:]:
            q=tuple(signed(e.get(p+i)) for i in (0,4,8,12))
            if q[0]<q[2] and q[1]<q[3]:
                rectangles.append(q)
        q=(min(r[0] for r in rectangles),min(r[1] for r in rectangles),max(r[2] for r in rectangles),max(r[3] for r in rectangles)) if rectangles else (0,0,0,0)
        e.put(c.arguments[0],*q)
        return int(bool(rectangles))
    env.override(0x546d94,union_rect)
    template=object_(env,24,'zero-control DLGTEMPLATE',data=struct.pack('<IIHhhhhHHH',0,0,0,0,0,101,73,0,0,0))
    env.override(0x546ac8,returns(0x9101 if resource else 0))
    env.override(0x546acc,returns(0x9102))
    env.override(0x546ac4,returns(template))
    env.override(0x546a54,returns(24))
    env.override(0x4fb7d8,returns(0))
    env.override(0x4f7b4e,lambda e,c: (e.put(c.receiver+0x1c,0x9201) or 1))
    env.override(0x4f8f44,lambda e,c: (e.put(c.receiver+0x1c,0) or 1))
    env.override(0x4f7b10,returns(0))
    for a in (0x4fcfff,0x4fd6db):
        env.override(a,lambda e,c: (e.put(c.receiver+4,c.arguments[0]) or int(c.arguments[0]!=0)))
    for a in (0x4fd067,0x4fd732):
        env.override(a,lambda e,c: (e.put(c.receiver+4,0) or 1))
    for a in (0x54687c,0x5468bc,0x54690c):
        env.override(a,returns(a+0x100000))
    env.override(0x546870,returns(1))
    env.override(0x546d20,returns(0x42678a))
    env.override(0x5468ec,returns(0x9911))
    env.override(0x5468e8,returns(1))
    def move(e,c):
        if c.arguments[3]:
            e.put(c.arguments[3],13,17)
        return 1
    env.override(0x5468e4,move)
    wrapper=object_(env,8,'selected GDI object',words=[0,0x9311])
    env.override(0x4fd150,returns(wrapper))
    return empty,wrapper


def directory(env,name='',children=()):
    d=object_(env,0x70,'archive directory '+name)
    env.put(d,string(env,name))
    buckets=object_(env,0x50,'directory buckets')
    env.put(d+0x40,buckets)
    for childname,child in children:
        slot=buckets+(len(childname)%5)*16+8
        node=object_(env,24,'directory node '+childname)
        env.put(node+4,env.get(slot))
        env.put(node+0x14,child)
        env.put(slot,node+4)
    return d


def cmap(env,at,entries):
    buckets=object_(env,4,'one hash bucket')
    env.put(at+4,buckets,1)
    for key,value in entries:
        node=object_(env,16,'map node',words=[env.get(buckets),0,string(env,key),value])
        env.put(buckets,node)


def base(env,fill=0):
    empty,wrapper=platform(env)
    obj=object_(env,0x304,'popup',fill=fill)
    env.put(obj+0x2ac,empty,empty)
    return obj,empty,wrapper


def construct(fill,a,b):
    def setup(env):
        obj,_,_=base(env,fill)
        return obj
    return Case(f'construct patterned {fill} {a:x}/{b:x}',0x4236c0,setup,receiver=lambda t:t,arguments=(a,b))


def selected(mode,fail=False,old=False):
    def setup(env):
        empty,_=platform(env)
        menu=object_(env,0x17c,'menu',fill=0x5b)
        app=object_(env,0xe8,'application')
        owner=object_(env,8,'application owner',words=[0,0x13579])
        env.put(app+4,owner)
        env.put(menu+4,app,0)
        env.put(menu+0x160,0)
        if old:
            log=object_(env,16,'prior popup deletion observation')
            def deletion(e,c):
                e.put(log,c.receiver,c.arguments[0],e.get(menu+0x160),e.get(menu+8))
                return 0x99
            vt=object_(env,4,'prior popup supplied vtable',words=[env.stub('previous popup destructor','thiscall',1,deletion)])
            prior=object_(env,4,'prior popup',words=[vt])
            env.put(menu+0x160,prior)
        if fail:
            def alloc(e,c):
                return 0 if e.calls_so_far(0x4f63ec)==1 else object_(e,max(1,c.arguments[0]),'allocation')
            env.override(0x4f63ec,alloc)
        return menu
    return Case(f'selected mode {mode:x} allocation-fail={fail} prior={old}',0x4399d0,setup,receiver=lambda t:t,arguments=(mode,))


def initialize(fail=-1,invalid=0,rect=(7,11,308,214),dims=(641,481),resource=True):
    def setup(env):
        empty,wrapper=platform(env,rect,resource)
        obj=object_(env,0x2bc,'popup')
        vt=object_(env,0x234,'supplied popup interface')
        log=object_(env,256,'callback state order')
        env.put(obj,vt)
        env.put(obj+0x2ac,string(env,'previous image'),string(env,'previous directory'))
        app=object_(env,0x100,'application dimensions')
        env.put(app+0x7c,*dims)
        env.put(0x5371fc,app)
        for index,slot in enumerate((0x21c,0x228,0x22c,0x230,0x220,0x224)):
            def callback(e,c,index=index):
                at=log+4+e.get(log)*32
                e.put(at,index,c.receiver,e.get(obj+0x2a0),e.get(obj+0x2a4),e.get(obj+0x294),e.get(obj+0x298),e.get(obj+0x2b4),e.get(0x52545c))
                e.put(log,e.get(log)+1)
                return 0 if index==fail else 0x71+index
            env.put(vt+slot,env.stub(f'popup callback {slot:x}','thiscall',0,callback))
        dc=object_(env,8,'physical screen DC',words=[0,0x9401])
        for slot,argc,result in ((4,0,dc),(8,1,1),(12,2,1),(16,0,1)):
            env.put(vt+slot,env.stub(f'popup drawing {slot:x}','thiscall',argc,returns(result)))
        dcvt=object_(env,0x34,'physical CDC interface')
        env.put(dcvt+0x30,env.stub('CDC select font','thiscall',1,returns(wrapper)))
        env.put(obj+0xd4,dcvt)
        env.put(obj+0xec,dcvt)
        name=string(env,'' if invalid==3 else 'DIALOG_'+str(abs(dims[0])))
        return obj,0 if invalid==1 else app,0 if invalid==2 else 0x9753,name
    return Case(f'popup initialize fail={fail} invalid={invalid} rect={rect} dims={dims} resource={resource}',0x423840,setup,receiver=lambda t:t[0],arguments=tuple(lambda t,i=i:t[i] for i in (1,2,3)))


def selectdir(states,missing=False,invalid=0,change=False):
    def setup(env):
        obj,_,_=base(env,0x63)
        context=object_(env,0x168,'menu context')
        state=object_(env,4,'state receiver')
        vt=object_(env,0x14,'state interface')
        log=object_(env,64,'state call observations')
        def stateid(e,c):
            i=e.get(log)
            e.put(log+4+i*8,c.receiver,e.get(obj+0x2a8))
            e.put(log,i+1)
            if change and i==0:
                replacement=object_(e,4,'replacement state receiver',words=[vt])
                e.put(context+0x164,replacement)
            return states[min(i,len(states)-1)]
        env.put(vt+0x10,env.stub('state identifier','thiscall',0,stateid))
        env.put(state,vt)
        env.put(context+0x164,state)
        dialogs=directory(env,'DIALOGS')
        statesdir=directory(env,'STATES',(('DIALOGS',dialogs),))
        game=directory(env,'GAME',(('DIALOGS',dialogs),))
        root=directory(env,'',() if missing else (('STATES',statesdir),('GAME',game)))
        manager=object_(env,0x28,'archive manager')
        env.put(manager+0x24,root)
        env.put(obj+0x2a0,0 if invalid==1 else context,0 if invalid==2 else manager,0x57575757)
        return obj
    return Case(f'directory states={states} missing={missing} invalid={invalid} change={change}',0x424b90,setup,receiver=lambda t:t)


def imagecase(low=1,high=1,value=0x81234,missing=0,change=False):
    def setup(env):
        obj,_,_=base(env,0x45)
        image=directory(env,'A')
        images=directory(env,'IMAGES',(('A',image),))
        root=directory(env,'',() if missing==3 else (('IMAGES',images),))
        context=object_(env,0x20,'image context')
        services=object_(env,0x20,'image services')
        manager=object_(env,0x30,'image manager')
        vt=object_(env,0x4c,'image load interface')
        meta=object_(env,0x6c,'image metadata')
        frames=object_(env,8,'frame pointer pair',words=[0xdecafbad,value])
        env.put(meta+0x14,frames)
        env.put(meta+0x64,low,high)
        env.put(obj+0x2a0,0 if missing==2 else context)
        env.put(obj+0x2a8,0 if missing==1 else root,string(env,'A'),string(env,'IMAGES_A'))
        env.put(context+12,services)
        env.put(services+16,manager)
        env.put(manager,vt)
        cmap(env,manager+16,() if missing==4 else (('A',meta),))
        log=object_(env,24,'image load observation')
        def load(e,c):
            e.put(log,c.receiver,*c.arguments,e.get(obj+0x29c),e.get(obj+0x2ac))
            if change:
                replacement=object_(e,0x30,'replacement manager')
                cmap(e,replacement+16,(('B',meta),))
                e.put(services+16,replacement)
                e.put(obj+0x2ac,string(e,'B'))
            return 0x8642
        env.put(vt+0x48,env.stub('image load callback','thiscall',3,load))
        return obj
    return Case(f'image bounds {low}/{high} value={value:x} missing={missing} changed={change}',0x424ca0,setup,receiver=lambda t:t)


def menu_early(no_state=False,mode=8):
    def setup(env):
        platform(env)
        menu=object_(env,0x17c,'menu',fill=0x3d)
        app=object_(env,0xe8,'application')
        manager=object_(env,0x28,'archive manager')
        env.put(manager+0x24,directory(env))
        env.put(app+0x34,manager)
        env.put(menu+0x164,0 if no_state else object_(env,4,'state token'))
        env.put(menu+0x158,mode)
        return menu,app
    return Case(f'menu early no-state={no_state}',0x438c40,setup,receiver=lambda t:t[0],arguments=(lambda t:t[1],7,0x41))


def menu_complete(cursor_state=0, cursor_frame=True, fallback=False, selection=3, background_failure=False, cursor_dims=(31,27), cursor_xy=(91,157)):
    def setup(env):
        platform(env,rect=(0,0,301,203))
        template_bytes=struct.pack('<IIHhhhhHHH',0,0,1,0,0,101,73,0,0,0)+struct.pack('<IIhhhhHHHH',0,0,1,1,20,10,0x40d,0xffff,0x82,0)+b'\0\0'
        template=object_(env,len(template_bytes),'message DLGTEMPLATE',data=template_bytes)
        env.override(0x546ac4,returns(template))
        env.override(0x546a54,returns(len(template_bytes)))
        env.override(0x546b10,lambda e,c:(e.write(c.arguments[0],e.cstr(c.arguments[1])+b'\0') or c.arguments[0]))
        env.override(0x546cd0,lambda e,c:(e.put(c.arguments[0],*cursor_xy) or 1))
        menu=object_(env,0x17c,'menu',fill=0x2a)
        app=object_(env,0x500,'application')
        owner=object_(env,8,'owner',words=[0,0x9871])
        services=object_(env,0x40,'services')
        env.put(app+4,owner)
        env.put(app+0x30,services)
        env.put(app+0x7c,641,481)
        env.put(0x5371fc,app)
        env.put(menu+0x158,selection)
        state=object_(env,4,'state')
        statevt=object_(env,0x18,'state interface')
        def stateid(e,c):
            return cursor_state if e.calls_so_far(statecall)>6 else 0
        statecall=env.stub('menu state identifier','thiscall',0,stateid)
        env.put(statevt+0x10,statecall)
        env.put(state,statevt)
        env.put(menu+0x164,0 if fallback else state)
        stack=object_(env,4,'application state stack',words=[state])
        env.put(app+0xe0,stack,1)
        leaf=directory(env,'MESSAGE')
        images=directory(env,'IMAGES',(('MESSAGE',leaf),))
        dialogs=directory(env,'DIALOGS',(('IMAGES',images),))
        states=directory(env,'STATES',(('DIALOGS',dialogs),))
        level=directory(env,'LEVEL7')
        root=directory(env,'',(('STATES',states),('LEVEL7',level)))
        archive=object_(env,0x28,'archive')
        env.put(archive+0x24,root)
        env.put(app+0x34,archive)
        ddvt=object_(env,0x80,'DirectDraw surface methods')
        dd=object_(env,4,'DirectDraw surface',words=[ddvt])
        env.put(ddvt+0x44,env.stub('DirectDraw GetDC','stdcall',2,lambda e,c:(e.put(c.arguments[1],0x9811) or 0)))
        env.put(ddvt+0x68,env.stub('DirectDraw ReleaseDC','stdcall',2,returns(0)))
        env.put(ddvt+0x14,env.stub('DirectDraw Blt','stdcall',6,returns(0)))
        surface=object_(env,0xbc,'image backing surface')
        env.put(surface+8,dd)
        frame=object_(env,0x40,'popup image frame')
        env.put(frame+0x10,301,203)
        env.put(frame+0x2c,surface)
        meta=object_(env,0x6c,'popup image metadata')
        frames=object_(env,8,'popup frames',words=[0,frame])
        env.put(meta+0x14,frames)
        env.put(meta+0x64,1,1)
        image_manager=object_(env,0x30,'image manager')
        imvt=object_(env,0x4c,'image manager interface')
        env.put(imvt+0x48,env.stub('resident image loading','thiscall',3,returns(1)))
        env.put(image_manager,imvt)
        cursor_meta=object_(env,0x6c,'cursor metadata')
        cursor_pixels=object_(env,0x30,'cursor frame')
        env.put(cursor_pixels+0x10,*cursor_dims)
        cursor_frames=object_(env,4,'cursor frames',words=[cursor_pixels])
        env.put(cursor_meta+0x14,cursor_frames)
        cmap(env,image_manager+16,[('MESSAGE',meta)]+([('MENU_CURSOR',cursor_meta),('GAME_CURSOR',cursor_meta)] if cursor_frame else []))
        env.put(services+0x10,image_manager)
        dcvt=object_(env,0x34,'physical DC methods')
        wrapper=object_(env,16,'physical DC',words=[dcvt,0x9811])
        env.override(0x4fcfe9,returns(wrapper))
        env.override(0x4fd1ac,returns(wrapper))
        renderer=object_(env,0x500,'renderer')
        env.put(services+0x1c,renderer)
        ddraw=object_(env,4,'DirectDraw interface')
        ddrawvt=object_(env,0x1c,'DirectDraw methods')
        env.put(ddraw,ddrawvt)
        env.put(renderer,0 if background_failure else ddraw)
        env.put(renderer+0x3b8+0x18,10)
        def create(e,c):
            e.put(c.arguments[2],dd)
            return 0
        env.put(ddrawvt+0x18,env.stub('DirectDraw CreateSurface','stdcall',4,create))
        def desc(e,c):
            e.put(c.arguments[1]+8,481,641,641*4)
            e.put(c.arguments[1]+0x54,32)
            return 0
        env.put(ddvt+0x58,env.stub('DirectDraw GetSurfaceDesc','stdcall',2,desc))
        display=object_(env,0x18,'display state')
        displayctx=object_(env,0x30,'display context')
        env.put(display+0x14,displayctx)
        env.put(displayctx+0x2c,surface)
        env.put(services+4,display)
        cursor_manager=object_(env,0x30,'cursor manager')
        env.put(cursor_manager+0xc,services)
        env.put(cursor_manager+0x28,10)
        env.put(services+8,cursor_manager)
        env.put(services+0x24,object_(env,32,'world context'))
        logic_manager=object_(env,0x30,'logic manager')
        logic=object_(env,0x20,'AniCycle logic')
        env.put(logic+0x10,object_(env,32,'AniCycle script bytes'))
        cmap(env,logic_manager+0x10,(('AniCycle',logic),))
        env.put(services+0x14,logic_manager)
        sequence_manager=object_(env,0x30,'sequence manager')
        cmap(env,sequence_manager+16,())
        env.put(services+0x2c,sequence_manager)
        return menu,app
    return Case(f'menu complete state={cursor_state} frame={cursor_frame} fallback={fallback} selection={selection} bgfail={background_failure} dims={cursor_dims} xy={cursor_xy}',0x438c40,setup,receiver=lambda t:t[0],arguments=(lambda t:t[1],7,0x41))


def cases(random_source):
    for fill,a,b in ((0xa7,0,0),(0x39,0x12345678,0x87654321),(random_source.randrange(1,256),random_source.getrandbits(32),random_source.getrandbits(32))):
        yield construct(fill,a,b)
    for mode in range(8):
        yield selected(mode)
        yield selected(mode,True,True)
    for mode in (8,0xffffffff,0x80000000):
        yield selected(mode,old=True)
    for invalid in (1,2,3):
        yield initialize(invalid=invalid)
    for fail in range(6):
        yield initialize(fail=fail)
    yield initialize(resource=False)
    yield initialize()
    for dims,rect in (((-641,-481),(8,10,-301,-205)),((1,0),(0,0,1,1)),((random_source.randrange(300,900),random_source.randrange(200,700)),(3,5,204,106))):
        yield initialize(dims=dims,rect=rect)
    for states in ((11,),(0,3),(0,0,4),(0,0,0)):
        yield selectdir(states)
        yield selectdir(states,missing=True)
    for invalid in (1,2):
        yield selectdir((0,),invalid=invalid)
    for missing in range(1,5):
        yield imagecase(missing=missing)
    for low,high,value in ((2,2,1),(1,0,1),(1,1,0),(1,1,0x81234),(-7,9,0x91513),(0x80000000,0x7fffffff,0x44551)):
        yield imagecase(low,high,value)
    yield imagecase(change=True)
    yield menu_early(True)
    yield menu_early()

    yield menu_complete()
    yield menu_complete(selection=8)

    for state in (0,11,3,4):
        yield menu_complete(cursor_state=state, cursor_frame=False, fallback=True)
    yield menu_complete(background_failure=True)

    yield menu_complete(cursor_state=11,cursor_dims=(-31,-27),cursor_xy=(0x7fffffff,0xffffffff))
    yield menu_complete(cursor_dims=(random_source.randrange(-101,102),random_source.randrange(-101,102)))

    yield selectdir((0,3),change=True)
