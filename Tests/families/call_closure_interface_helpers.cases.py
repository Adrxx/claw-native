"""Original-backed interface array, control construction and GDI lifecycle cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns

NEW = 0x4f63ec


def cstring(env, text, refs=1):
    data = text + b'\0'
    token = env.object(12+len(data), 'CString data', words=[refs, len(text), len(text)], fill=0)
    env.write(token+12, data)
    return token+12


def common(env):
    env.override(0x5469e4, lambda e,c: len(e.cstr(c.arguments[0])))
    def increment(e,c):
        value = (e.get(c.arguments[0])+1)&0xffffffff
        e.put(c.arguments[0],value)
        return value
    def decrement(e,c):
        value = (e.get(c.arguments[0])-1)&0xffffffff
        e.put(c.arguments[0],value)
        return value
    env.override(0x5469ec,increment)
    env.override(0x5469e8,decrement)
    env.override(0x4f2190,returns(1))
    def intersect(e,c):
        out,a,b=c.arguments
        vals=[]
        for i in range(4):
            x,y=e.get(a+4*i),e.get(b+4*i)
            x=x-(1<<32) if x&0x80000000 else x
            y=y-(1<<32) if y&0x80000000 else y
            vals.append(max(x,y) if i<2 else min(x,y))
        valid=vals[0]<vals[2] and vals[1]<vals[3]
        e.put(out,*[v&0xffffffff for v in (vals if valid else [0,0,0,0])])
        return int(valid)
    env.override(0x546ce0,intersect)
    # CString's immortal empty storage is an original image global.


def dialog_setup(kind=0x83,flags=0,fail_small=0,ascent=11,duplicate=1,mutate=False):
    def setup(env):
        common(env)
        receiver=env.object(0x12c,'dialog',fill=0x59)
        methods=env.object(0xd8,'dialog vtable',fill=0)
        dc_methods=env.object(0x34,'DC vtable',fill=0)
        dc=env.object(12,'DC',words=[dc_methods,0x88220011,0x77330022])
        oldfont=env.object(8,'old font',words=[0x31415926,0x27182818])
        log=env.object(64,'callback record',fill=0)
        controls=env.object(max(1,duplicate)*0x5c,'controls',fill=0x6d)
        env.put(receiver,methods)
        env.write(receiver+0x14,struct.pack('<H',duplicate))
        env.put(receiver+0x3c,controls)
        env.put(receiver+0x64,0x43217654)
        env.put(receiver+0x128,13)
        for i in range(duplicate):
            t=controls+i*0x5c
            env.put(t,flags)
            env.write(t+0x12,struct.pack('<H',kind if i==0 else 0x80))
            if i:env.put(t,1)
            env.put(t+0x1c,cstring(env,b'Original text '+bytes([65+i])))
            env.put(t+0x28,17+i,29+i,137+i,199+i)
        def getdc(e,c):
            e.put(log,e.get(log)+1,c.receiver)
            return dc
        def selectfont(e,c):
            e.put(log+12,c.receiver,c.arguments[0])
            return oldfont
        def release_dc(e,c):
            e.put(log+24,c.receiver,c.arguments[0])
            return 1
        def metrics(e,c):
            e.write(c.arguments[1],b'\0'*60)
            e.put(c.arguments[1],23,ascent,7,3,19)
            if mutate:e.put(receiver+0x128,21)
            return 1
        env.put(methods+4,env.stub('get dialog DC','thiscall',0,getdc))
        env.put(methods+8,env.stub('release dialog DC','thiscall',1,release_dc))
        env.put(dc_methods+0x30,env.stub('select dialog font','thiscall',1,selectfont))
        env.override(0x546900,metrics)
        def allocate(e,c):
            if c.arguments[0]==4 and fail_small and e.calls_so_far(NEW)==fail_small:return 0
            return e.object(c.arguments[0],'allocated control',fill=0xa7)
        env.override(NEW,allocate)
        return {'receiver':receiver,'controls':controls,'log':log}
    return setup


def gdi_setup(function,initial=0,attach_dc=1,attach_bitmap=1,null_dc=False,mutate=False,rect=(7,11,61,73),old_present=None,dc_neighbor=None):
    def setup(env):
        common(env)
        receiver=env.object(0x12c,'bitmap dialog',fill=0x4b)
        methods=env.object(0xd8,'bitmap dialog vtable',fill=0)
        dc_methods=env.object(0x34,'embedded DC vtable',fill=0)
        dc=env.object(12,'acquired DC',words=[dc_methods,0x22117733,0x32435678])
        old=env.object(8,'old selected object',words=[0x12345678,0x8abc6789])
        log=env.object(128,'callback trace',fill=0)
        env.put(receiver,methods)
        env.put(receiver+0x6c,*rect)
        env.put(receiver+0xcc,0x61001100,0x61001111)
        env.put(receiver+0xd4,dc_methods,initial)
        env.put(receiver+0xec,dc_methods,initial)
        selected=bool(initial&1) if old_present is None else old_present
        env.put(receiver+0xfc,old if selected else 0)
        env.put(receiver+0x100,old if selected else 0)
        if dc_neighbor is not None:
            env.put(receiver+0xdc,dc_neighbor)
            env.put(receiver+0xf4,dc_neighbor)
        env.put(receiver+0x104,0x778899aa,initial)
        def record(e,c,index):
            e.put(log+index,c.receiver,*c.arguments)
            return 1
        def getdc(e,c):
            record(e,c,0)
            return 0 if null_dc else dc
        def release_dc(e,c):
            record(e,c,16)
            if mutate:e.put(receiver+0x6c,3,5,31,43)
            return 0
        env.put(methods+4,env.stub('GetDC','thiscall',0,getdc))
        env.put(methods+8,env.stub('ReleaseDC','thiscall',1,release_dc))
        env.put(methods+0xc,env.stub('draw background','thiscall',2,lambda e,c:record(e,c,32)))
        env.put(methods+0x10,env.stub('paint','thiscall',0,lambda e,c:record(e,c,48)))
        env.put(methods+0xd4,env.stub('set cursor visible','thiscall',1,lambda e,c:record(e,c,64)))
        env.put(dc_methods+0x30,env.stub('select font','thiscall',1,lambda e,c:(record(e,c,80),old)[1]))
        env.override(0x4fd067,lambda e,c:(e.put(c.receiver+4,0),1)[1])
        env.override(0x4fd732,lambda e,c:(e.put(c.receiver+4,0),1)[1])
        env.override(0x54687c,returns(0x10102020))
        env.override(0x54690c,returns(0x30304040))
        env.override(0x546b60,returns(0x50506060))
        env.override(0x4fcfff,lambda e,c:(e.put(c.receiver+4,c.arguments[0]) if attach_dc else None,attach_dc)[1])
        env.override(0x4fd6db,lambda e,c:(e.put(c.receiver+4,c.arguments[0]) if attach_bitmap else None,attach_bitmap)[1])
        env.override(0x4fd150,returns(old))
        env.override(0x546870,returns(1))
        def offset(e,c):
            pointer,x,y=c.arguments
            e.put(pointer,(e.get(pointer)+x)&0xffffffff,(e.get(pointer+4)+y)&0xffffffff,
                  (e.get(pointer+8)+x)&0xffffffff,(e.get(pointer+12)+y)&0xffffffff)
            return 1
        env.override(0x546b7c,offset)
        return {'receiver':receiver,'log':log}
    return setup


def append_setup(count,capacity,growth=0,array=True,text=b'',status=1):
    def setup(env):
        common(env)
        receiver=env.object(0x4c,'interface array',fill=0x37)
        data=env.object(max(4,4*max(count,capacity)),'image array',fill=0x91) if array else 0
        env.put(receiver+4,data,count,capacity,growth)
        argument=cstring(env,text)
        env.override(0x4f2190,returns(status))
        return {'receiver':receiver,'argument':argument}
    return setup


def rendering_setup(mask,arg1,arg2,text=b''):
    def setup(env):
        common(env)
        receiver=env.object(0x54,'renderer',fill=0x62)
        present=env.object(32,'presence',words=[(1<<i) if mask&(1<<i) else 0 for i in range(8)])
        surfaces=[]
        for i in range(8):
            surface=env.object(0xbc,'text destination',fill=0)
            env.put(surface+0x14,29+i,47+i,2*(47+i))
            if text:
                pixels=env.object(2*(47+i)*(29+i),'rendered pixels',fill=0x32+i)
                methods=env.object(0x84,'rendered surface methods',fill=0)
                interface=env.object(4,'rendered surface interface',words=[methods])
                env.put(surface+8,interface)
                def lock(e,c,target=surface,pixel=pixels):
                    e.put(target+0x30,pixel)
                    return 0
                env.put(methods+0x64,env.stub('text destination lock','stdcall',5,lock))
                env.put(methods+0x80,env.stub('text destination unlock','stdcall',2,returns(0)))
            surfaces.append(surface)
        array=env.object(32,'destinations',words=surfaces)
        # Empty strings still exercise copy/refcount/destruction, but no glyphs.
        string=cstring(env,text)
        fonts=[]
        for i in range(4):
            font=env.object(16,'font',fill=0)
            metric=env.object(2048,'glyph metrics',fill=0)
            env.put(font+4,256 if text else 0)
            env.put(font+0xc,metric)
            if text:
                glyph=env.object((i+1)*(i+2),'glyph pixels',data=bytes([255,128,1,0]*((i+1)*(i+2)//4+1))[:(i+1)*(i+2)])
                glyphs=env.object(1024,'glyph pointer table',words=[glyph]*256)
                env.put(font+8,glyphs)
                env.write(metric,struct.pack('<II',i+1,i+2)*256)
            fonts.append(font)
        for a,v in zip((0x541368,0x54135c,0x54136c,0x541360,0x541370),(3,11,2,5,3)):env.put(a,v)
        env.put(receiver+4,array)
        env.put(receiver+0x38,present)
        env.put(receiver+0x4c,fonts[0],fonts[1])
        return {'receiver':receiver,'string':string,'arg1':fonts[2] if arg1 else 0,'arg2':fonts[3] if arg2 else 0}
    return setup


def loaded_image_setup(shifts=(3,11,2,5,3),existing=0):
    def setup(env):
        tokens=append_setup(existing,existing,0,existing!=0,b'RESOURCE_IMAGE',0)(env)
        receiver=tokens['receiver']
        manager=env.object(0x880,'graphics manager',fill=0)
        device=env.object(4,'DirectDraw device',fill=0)
        device_table=env.object(0x1c,'DirectDraw methods',fill=0)
        surface=env.object(4,'DirectDraw surface',fill=0)
        table=env.object(0x84,'surface methods',fill=0)
        pixels=env.object(8,'surface pixels',data=b'abcdefgh')
        bitmap=env.object(1072,'DIB resource',fill=0)
        env.put(bitmap,40,3,2)
        env.write(bitmap+12,struct.pack('<HH',1,8))
        env.write(bitmap+1064,b'XYZ0abc1')
        env.put(manager,device)
        env.put(manager+0x474,8)
        env.put(manager+0x3d0,4)
        env.put(receiver+0x48,manager)
        env.put(device,device_table)
        env.put(surface,table)
        def create(e,c):
            e.put(c.arguments[2],surface)
            return 0
        def description(e,c):
            p=c.arguments[1]
            e.write(p,b'\0'*108)
            e.put(p,108,7,2,3,4)
            e.put(p+0x24,pixels)
            e.put(p+0x54,8)
            return 0
        env.put(device_table+0x18,env.stub('CreateSurface','stdcall',4,create))
        env.put(table+0x58,env.stub('GetSurfaceDesc','stdcall',2,description))
        env.put(table+0x64,env.stub('Lock','stdcall',5,description))
        key_record=env.object(12,'observed DDCOLORKEY',fill=0x73)
        def set_color_key(e,c):
            pair=c.arguments[2]
            e.put(key_record,c.arguments[1],e.get(pair),e.get(pair+4))
            return 0
        env.put(table+0x74,env.stub('SetColorKey','stdcall',3,set_color_key))
        env.put(table+0x80,env.stub('Unlock','stdcall',2,returns(0)))
        env.override(0x546ac8,returns(0x61000001))
        env.override(0x546acc,returns(0x61000002))
        env.override(0x546ac4,returns(bitmap))
        for a,v in zip((0x541368,0x54135c,0x54136c,0x541360,0x541370),shifts):env.put(a,v)
        return tokens
    return setup


def cases(random_source):
    for value in (0,1,0xffffffff,0x81524376,random_source.getrandbits(32)):
        def setup(env,value=value):
            p=env.object(0x30,'kind object',fill=0x65)
            env.put(p+0x2c,value)
            return {'receiver':p}
        yield Case('kind field '+hex(value),0x4df250,setup,receiver=lambda t:t['receiver'])
    for function in (0x4e2f70,0x4e3090,0x4e31f0):
        for initial in (0,1,0x55aa0020):
            for mutate in (False,True):
                yield Case(f'GDI {function:x} initial {initial:x} mutate {mutate}',function,
                           gdi_setup(function,initial=initial,mutate=mutate),receiver=lambda t:t['receiver'])
        if function!=0x4e31f0:
            for initial,neighbor in ((0,0x74562301),(1,0)):
                yield Case(f'GDI handle and adjacent field differ {function:x}/{initial}/{neighbor:x}',function,
                           gdi_setup(function,initial=initial,old_present=True,dc_neighbor=neighbor),receiver=lambda t:t['receiver'])
            for dc,bmp,null in ((0,1,False),(1,0,False),(0,1,True)):
                yield Case(f'GDI failure {function:x} {dc}/{bmp}/{null}',function,
                           gdi_setup(function,attach_dc=dc,attach_bitmap=bmp,null_dc=null),receiver=lambda t:t['receiver'])
    for kind in (0,0x7f,0x80,0x81,0x82,0x83,0x84,0x85,0x86,0xffff):
        for flags in (0,1,3,0x100,0x400,0x800,0x1000,0x1f03):
            yield Case(f'control {kind:x} flags {flags:x}',0x4e29a0,dialog_setup(kind,flags),receiver=lambda t:t['receiver'])
    yield Case('empty dialog',0x4e29a0,dialog_setup(duplicate=0),receiver=lambda t:t['receiver'])
    yield Case('multiple controls',0x4e29a0,dialog_setup(0x85,0x1f01,duplicate=3,mutate=True,ascent=17),receiver=lambda t:t['receiver'])
    for kind,index in ((0x81,1),(0x85,1),(0x85,6)):
        yield Case(f'CString allocation fails {kind:x}/{index}',0x4e29a0,dialog_setup(kind,3,fail_small=index),receiver=lambda t:t['receiver'])
    for count,capacity,growth,array in ((0,0,0,False),(0,4,0,True),(2,5,0,True),(3,3,0,True),(32,32,0,True),(8200,8200,0,True),(3,3,1,True),(3,3,9,True),(5,2,0,True),(9,3,2,True)):
        for text in (b'',b'missing image.bmp'):
            yield Case(f'append {count}/{capacity}/{growth}/{array}/{bool(text)}',0x4de560,
                       append_setup(count,capacity,growth,array,text),receiver=lambda t:t['receiver'],arguments=(lambda t:t['argument'],))
    for shifts in ((3,11,2,5,3),(0,0,0,0,0),(35,43,34,37,35)):
        for existing in (0,2):
            yield Case(f'load image {shifts}/{existing}',0x4de560,loaded_image_setup(shifts,existing),
                       receiver=lambda t:t['receiver'],arguments=(lambda t:t['argument'],))
    for arg1,arg2 in ((0,0),(1,0),(0,1),(1,1)):
        yield Case(f'nonempty eight-way text {arg1}/{arg2}',0x4de830,rendering_setup(0xff,arg1,arg2,b'Ab'),
                   receiver=lambda t:t['receiver'],arguments=(lambda t:t['string'],lambda t:t['arg1'],lambda t:t['arg2']))
    for mask in (0,0xff,1,2,4,8,16,32,64,128):
        for arg1,arg2 in ((0,0),(1,0),(0,1),(1,1)):
            yield Case(f'eight-way text {mask:x}/{arg1}/{arg2}',0x4de830,rendering_setup(mask,arg1,arg2),
                       receiver=lambda t:t['receiver'],arguments=(lambda t:t['string'],lambda t:t['arg1'],lambda t:t['arg2']))

