"""Original-driven recursive archive, write and interface helper cases."""
from clawparity.cases import Case
from clawparity.fixtures import returns
import struct


def tree(env,at,values=(),node_offsets=None):
    table=env.object(1024,'tree bucket table',fill=0)
    env.put(at,64,table)
    nodes=[]
    for index,value in enumerate(values):
        node=value+node_offsets if isinstance(node_offsets,int) else env.object(24,'tree node',fill=0)
        env.put(node,0,0,0,at,0,value)
        nodes.append(node)
    if nodes:
        env.put(table+8,nodes[0]+4)
        for left,right in zip(nodes,nodes[1:]):env.put(left+4,right+4)
    return nodes


def archive(env):
    a=env.object(72,'archive',fill=0)
    v=env.object(12,'archive methods',fill=0)
    env.put(v+8,env.stub('archive retry','thiscall',0,returns(0)))
    env.put(a,v)
    env.put(a+12,0x1234)
    env.put(a+0x1c,0x1357)
    env.override(0x4a7840,returns(0))
    log=env.object(16384,'written stream observations',fill=0)
    def fwrite(env,call):
        at=env.get(log);size=call.arguments[1]*call.arguments[2]
        env.put(log+4+at,call.arguments[3],size)
        env.write(log+12+at,env.read(call.arguments[0],size))
        env.put(log,at+8+size)
        return call.arguments[2]
    env.override(0x4a73e0,fwrite)
    env.override(0x4a3b10,returns(0x12345678))
    return a


def directory(env,a,name=b'ROOT',children=()):
    d=env.object(0x4c,'directory',fill=0)
    n=env.object(len(name)+1,'directory name',data=name+b'\0')
    env.put(d,n)
    env.put(d+0x14,0x76543210)
    env.put(d+0x18,a)
    tree(env,d+0x3c,children,0x24)
    tree(env,d+0x44)
    return d


def cstring(env,data):
    p=env.object(12+len(data)+1,'CString bytes',fill=0)
    env.put(p,1,len(data),len(data))
    env.write(p+12,data+b'\0')
    def increment(env,call):
        p=call.arguments[0];n=(env.get(p)+1)&0xffffffff;env.put(p,n);return n
    def decrement(env,call):
        p=call.arguments[0];n=(env.get(p)-1)&0xffffffff;env.put(p,n);return n
    env.override(0x5469ec,increment);env.override(0x5469e8,decrement)
    return p+12


def cases(random_source):
    for base in (0,1,0x10000001,0xfffffff0,random_source.getrandbits(32)):
        for index in (0,1,2,0x3fffffff,0x40000000,0xffffffff):
            def setup(env,base=base):return env.object(8,'slot owner',words=[0xdeadbeef,base])
            yield Case(f'slot base{base:x} index{index:x}',0x4deda0,setup,receiver=lambda t:t,arguments=(index,))
    for count in (0,1,2,5):
        for query in (0,1,0xffff,0x10000,0xffffffff,0x2a):
            def setup(env,count=count):
                d=env.object(64,'dialog',fill=0)
                rows=env.object(max(1,count)*0x5c,'records',fill=0xa7)
                env.write(d+0x14,struct.pack('<H',count));env.put(d+0x3c,rows)
                for index in range(count):env.write(rows+index*0x5c+0x10,struct.pack('<H',(0,0x2a,0xffff,0x2a,1)[index]))
                return d
            yield Case(f'dialog count{count} query{query:x}',0x4e2110,setup,receiver=lambda t:t,arguments=(query,))
    for value in (0,1,0x80000000,0xffffffff,random_source.getrandbits(32)):
        yield Case(f'global surface {value:x}',0x4cf010,arguments=(value,))
    for count in (0,1,4,7,16,31):
        for seeks,writes,retries in (((0,),(),()),((1,),(),(0,)),((1,1,0),(),(1,1)),((0,),(0,),(0,)),((0,),(0,0),(1,1))):
            def setup(env,count=count,seeks=seeks,writes=writes,retries=retries):
                a=archive(env);data=env.object(192,'write bytes',data=bytes((i*73+19)&255 for i in range(192)))
                log=env.object(512,'retry observations',fill=0)
                def seek(env,call):
                    n=env.calls_so_far(0x4a7840)-1
                    return seeks[min(n,len(seeks)-1)]
                def write(env,call):
                    n=env.calls_so_far(0x4a73e0)-1
                    env.put(log+48,call.arguments[0],call.arguments[1],call.arguments[2],call.arguments[3])
                    env.write(log+80,env.read(call.arguments[0],call.arguments[1]*call.arguments[2]))
                    return writes[n] if n<len(writes) else call.arguments[2]
                def retry(env,call):
                    n=env.calls_so_far(call.function)-1
                    env.put(log+n*8,call.receiver,env.get(a+12))
                    env.put(a+12,0x45670000+n)
                    return retries[n] if n<len(retries) else 0
                env.put(env.get(a)+8,env.stub('retry write failure','thiscall',0,retry))
                env.override(0x4a7840,seek);env.override(0x4a73e0,write)
                return a,data
            yield Case(f'write {count} seeks{seeks} writes{writes} retries{retries}',0x4b7b40,setup,receiver=lambda t:t[0],arguments=(0x31415,count,lambda t:t[1]))
    for depth in (0,1,2):
        for siblings in (1,2):
            def setup(env,depth=depth,siblings=siblings):
                a=archive(env)
                kids=[]
                for i in range(siblings if depth else 0):
                    leaves=[directory(env,a,b'LEAF')] if depth==2 else []
                    kids.append(directory(env,a,b'CHILD'+bytes([65+i]),leaves))
                d=directory(env,a,children=kids)
                out=env.object(8,'layout outputs',words=[0xabc,0xdef])
                return d,out
            yield Case(f'recursive layout depth{depth} siblings{siblings}',0x4b6bd0,setup,receiver=lambda t:t[0],arguments=(lambda t:t[1],lambda t:t[1]+4))
    def empty_copy(env):
        a=archive(env);return directory(env,a,b'DEST'),directory(env,a,b'SOURCE')
    yield Case('copy empty archive',0x4b7950,empty_copy,receiver=0x76543210,arguments=(lambda t:t[0],lambda t:t[1]))
    for data in (b'',b'Claw',b'odd label'):
        for width,height in ((0,0),(31,19),(-3,-7)):
            def setup(env,data=data,width=width,height=height):
                text=cstring(env,data);surface=env.object(0x1c,'target surface',fill=0)
                env.put(surface+0x14,height,width)
                return text,surface
            yield Case(f'label null font {data!r} {width}x{height}',0x4dea30,setup,arguments=(lambda t:t[0],lambda t:t[1],0,0x937b21))

    for size,count,children in ((0,0,0),(1,0,1),(3,1,0),(4,2,0),(7,3,2),(17,1,0)):
        def setup(env,size=size,count=count,children=children):
            a=archive(env);dest=directory(env,a,b'DEST')
            sub=[directory(env,a,b'CHILD'+bytes([65+i])) for i in range(children)]
            source=directory(env,a,b'SOURCE',sub)
            buckets=[]
            for bi in range(2):
                bucket=env.object(0x2c,'source file bucket',fill=0);env.put(bucket,10+bi)
                files=[]
                for fi in range(2):
                    f=env.object(0x60,'source file',fill=0)
                    name=env.object(8,'file name',data=bytes([65+bi,65+fi])+b'.DAT\0')
                    desc=env.object(8,'description',data=b'notes!\0')
                    data=env.object(max(1,size),'source file bytes',data=bytes((i*31+fi*17+bi*53)&255 for i in range(max(1,size))))
                    meta=env.object(4*(count+1),'source metadata',words=[0x12340000+73*i+fi for i in range(count+1)])
                    env.put(f,name,0x1111+fi,bucket,desc,0x10203040+fi,size,data,count,meta,source,0x123)
                    files.append(f)
                tree(env,bucket+0x1c,files,0x48);tree(env,bucket+0x24)
                buckets.append(bucket)
            tree(env,source+0x44,buckets,4)
            return dest,source
        yield Case(f'copy files size{size} metadata{count} children{children}',0x4b7950,setup,receiver=0x76543210,arguments=(lambda t:t[0],lambda t:t[1]))
    for text,width,height,color in ((b'A',31,19,0xff0000),(b'AB',32,20,0x00ff00),(b'CAB',7,5,0x123456),(b'A',-3,-7,0x00ff00),(b'AB',-3,19,0x4172a3)):
        def setup(env,text=text,width=width,height=height):
            string=cstring(env,text)
            target=env.object(0xbc,'label surface',fill=0)
            pixels=env.object(8192,'label pixels',fill=0x62)+2048
            iface=env.object(4,'DirectDraw interface',fill=0)
            methods=env.object(132,'DirectDraw methods',fill=0)
            observation=env.object(64,'surface lock observations',fill=0)
            def lock(env,call):
                rect=call.arguments[2]
                env.put(rect+0x24,pixels)
                env.put(observation,env.get(target+0x14),env.get(target+0x18))
                return 0
            env.put(methods+100,env.stub('font target Lock','stdcall',5,lock))
            env.put(methods+128,env.stub('font target Unlock','stdcall',2,returns(0)))
            env.put(iface,methods);env.put(target,0x513690);env.put(target+8,iface)
            env.put(target+0x14,height,width,128);env.put(target+0x30,pixels)
            font=env.object(16,'font',fill=0)
            glyphs=env.object(2048,'glyph dimensions',fill=0)
            pointers=env.object(1024,'glyph pointers',fill=0)
            for ch in range(256):
                gw=1+(ch%3);gh=2+(ch%2)
                bitmap=env.object(64,'glyph alpha',data=bytes(([255,0,128,255,200,99,255,255]*8)))
                env.put(glyphs+ch*8,gw,gh);env.put(pointers+ch*4,bitmap)
            env.put(font,0,256,pointers,glyphs)
            def intersect(env,call):
                dst,left,right=call.arguments
                x1,y1,x2,y2=struct.unpack('<iiii',env.read(left,16));a,b,c,d=struct.unpack('<iiii',env.read(right,16))
                out=(max(x1,a),max(y1,b),min(x2,c),min(y2,d))
                env.write(dst,struct.pack('<iiii',*out));return int(out[0]<out[2] and out[1]<out[3])
            env.override(0x546ce0,intersect)
            for address,value in ((0x54135c,11),(0x541360,5),(0x541368,3),(0x54136c,2),(0x541370,3)):env.put(address,value)
            return string,target,font
        yield Case(f'centered glyph label {text!r} {width}x{height} color{color:x}',0x4dea30,setup,arguments=(lambda t:t[0],lambda t:t[1],lambda t:t[2],color))
    for phase in (0,1,2,3):
        def setup(env,phase=phase):
            owner=env.object(0x80,'image collection',fill=0)
            name=env.object(32,'resource name',data=b'CLAW_IMAGE\0')
            bitmap=env.object(1088,'resource bitmap',fill=0)
            env.put(bitmap,40,3,2)
            env.write(bitmap+14,struct.pack('<H',16))
            env.override(0x546ac8,returns(0 if phase==0 else 0x1234))
            env.override(0x546acc,returns(0 if phase==1 else 0x4567))
            env.override(0x546ac4,returns(0 if phase==2 else bitmap))
            return owner,name
        yield Case(f'image wrapper failure phase{phase}',0x4bc990,setup,receiver=lambda t:t[0],arguments=(lambda t:t[1],0x100,0xffffffff))
    for flags,color in ((0,0xffffffff),(1,0),(0x2000,0x1234),(0x40000000,0x87654321),(0xfffff7bf,0xffffffff)):
        def setup(env,flags=flags):
            owner=env.object(0x400,'successful image collection',fill=0)
            env.put(owner+0x3d0,10)
            ddraw=env.object(4,'DirectDraw',fill=0);dv=env.object(28,'DirectDraw methods',fill=0)
            surface=env.object(4,'created DirectDraw surface',fill=0);sv=env.object(132,'surface methods',fill=0)
            env.put(owner,ddraw);env.put(ddraw,dv);env.put(surface,sv)
            pixels=env.object(128,'created image pixels',fill=0xc3)
            observed=env.object(128,'image creation observations',fill=0)
            def create(env,call):
                iface,desc,out,outer=call.arguments
                env.put(observed,env.get(desc+0x68),env.get(desc+8),env.get(desc+12),iface,outer)
                env.put(out,surface);return 0
            def describe(env,call):
                desc=call.arguments[1];env.put(desc+8,2,3,8);env.put(desc+0x54,8);env.put(desc+0x24,pixels);return 0
            def lock(env,call):env.put(call.arguments[2]+0x24,pixels);return 0
            env.put(dv+24,env.stub('DirectDraw CreateSurface','stdcall',4,create))
            env.put(sv+88,env.stub('GetSurfaceDesc','stdcall',2,describe))
            env.put(sv+100,env.stub('image Lock','stdcall',5,lock))
            env.put(sv+128,env.stub('image Unlock','stdcall',2,returns(0)))
            def key(env,call):
                env.put(observed+32,call.arguments[0],call.arguments[1],env.get(call.arguments[2]),env.get(call.arguments[2]+4));return 0
            env.put(sv+116,env.stub('image SetColorKey','stdcall',3,key))
            name=env.object(32,'resource name',data=b'CLAW_IMAGE\0')
            bitmap=env.object(1200,'eight bit bitmap resource',fill=0)
            env.put(bitmap,40,3,2);env.write(bitmap+14,struct.pack('<H',8))
            env.write(bitmap+1064,bytes(range(32)))
            env.override(0x546ac8,returns(0x1234));env.override(0x546acc,returns(0x4567));env.override(0x546ac4,returns(bitmap))
            return owner,name
        yield Case(f'image successful flags{flags:x} key{color:x}',0x4bc990,setup,receiver=lambda t:t[0],arguments=(lambda t:t[1],flags,color))
