#!/usr/bin/env python3
"""Compare sprite geometry with hash-pinned original instructions, with logged host adapters.

Pixel decoding/blitting is deliberately outside this test. Full geometry routines
execute; only the surface/compressed pixel blitters and Windows CopyRect are
adapted. Metadata loading has separately labeled resource/decode adapters.
"""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
from original_v10 import OriginalV10

U = C.c_uint32
class Rect(C.Structure):
    _fields_ = [(n,U) for n in ('left','top','right','bottom')]
class Geometry(C.Structure):
    _fields_ = [(n,U) for n in ('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surfaceToken','compressedToken','surfaceKind')]
class Projection(C.Structure):
    _fields_ = [(n,U) for n in ('flags','extentX','extentY','cameraX','cameraY','visibleEndX','visibleEndY','screenOffsetX','screenOffsetY')]
class Actor(C.Structure):
    _fields_ = [(n,U) for n in ('flags','x','y','displacementX','displacementY','renderFlags','blinkRemaining','blinkInterval')] + [('clip',Rect),('drawX',U),('drawY',U),('drawn',Rect)] + [(n,U) for n in ('drawWidth','drawHeight','drawStatus')]
class Context(C.Structure):
    _fields_ = [(n,U) for n in ('width','height','surfaceToken','animationDelta','directDrawFlip')] + [('worldClip',Rect),('projection',Projection)]
class Command(C.Structure):
    _fields_ = [(n,U) for n in ('kind','receiverToken','sourceToken','surfaceKind','flipX','flipY')] + [('destination',Rect),('source',Rect)]
def words(value): return list(struct.unpack('<'+'I'*(C.sizeof(value)//4),bytes(value)))
def make(cls, values): return cls.from_buffer_copy(struct.pack('<'+'I'*len(values),*(x&0xffffffff for x in values)))
def signed(x): return x if x < 0x80000000 else x-0x100000000
def packed(*x): return struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x))

p=argparse.ArgumentParser();p.add_argument('exe',type=Path);p.add_argument('library',type=Path);p.add_argument('--assets',type=Path);args=p.parse_args()
lib=C.CDLL(str(args.library.resolve()))
lib.claw_sprite_relative_bounds.argtypes=[C.POINTER(Geometry),C.POINTER(Rect)]
lib.claw_sprite_relative_bounds.restype=U
lib.claw_sprite_project.argtypes=[C.POINTER(Projection),C.POINTER(U),C.POINTER(U)]
lib.claw_sprite_prepare_draw.argtypes=[C.POINTER(Geometry),C.POINTER(Actor),C.POINTER(Context),C.POINTER(Command)]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
m=OriginalV10(args.exe);u=m.u
actor_address,image_address,viewport_address=0x1000000,0x1001000,0x1002000
owner_address,world_address,holder_address,projection_address=0x1003000,0x1004000,0x1005000,0x1006000
rect_address,copy_adapter=0x1007000,0x10ef000
m.write_words(0x546d58,[copy_adapter])
blits=[];copies=[]
def host_return(pop,result=1):
    sp=u.reg_read(UC_X86_REG_ESP)
    ret=m.read_words(sp,1)[0]
    u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
    if address not in (0x4b9d80,0x4b9ce0,0x4bffa0,copy_adapter): return
    sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,5);receiver=u.reg_read(UC_X86_REG_ECX)
    if address==copy_adapter:
        dst,src=a[:2];rect=m.read_words(src,4);copies.append((dst,src,rect))
        assert src >= m.stack-512 and src < m.stack
        assert rect==m.read_words(world_address+16,4)
        m.write_words(dst,rect);host_return(8)
    elif address==0x4b9d80:
        x,y,source,rect,kind=a;source_rect=m.read_words(rect,4)
        blits.append([1,receiver,source,kind,0,0,x,y,x+source_rect[2]-source_rect[0],y+source_rect[3]-source_rect[1],*source_rect])
        host_return(20)
    elif address==0x4b9ce0:
        dst,source,src,flags,fx=a
        assert flags==0x8800 and fx==0x543108
        flip=m.read_words(0x54310c,1)[0]
        blits.append([2,receiver,source,m.read_words(image_address+0x28,1)[0],int(bool(flip&2)),int(bool(flip&4)),*m.read_words(dst,4),*m.read_words(src,4)])
        host_return(20)
    else:
        dst,surface,src,fx,fy=a;assert fx in(0,1) and fy in(0,1)
        blits.append([3,receiver,surface,0,fx,fy,*m.read_words(dst,4),*m.read_words(src,4)])
        host_return(20)
u.hook_add(UC_HOOK_CODE,host)
rng=random.Random(1997)

for i in range(5000):
    raw=[rng.getrandbits(32) for _ in range(128)]
    geometry=make(Geometry,[rng.getrandbits(32)for _ in range(10)])
    output=make(Rect,[rng.getrandbits(32)for _ in range(4)])
    original=words(output);raw[0x174//4]=0 if i%7==0 else image_address
    iw=[rng.getrandbits(32)for _ in range(128)]
    iw[0x18//4:0x28//4]=[geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY]
    m.write_words(actor_address,raw);m.write_words(image_address,iw);m.write_words(rect_address,original)
    result=m.call(0x4061e0,actor_address,packed(rect_address))
    native=lib.claw_sprite_relative_bounds(None if i%7==0 else C.byref(geometry),C.byref(output))
    assert native==result and words(output)==m.read_words(rect_address,4),(i,'relative bounds')
    assert raw==m.read_words(actor_address,128) and iw==m.read_words(image_address,128)
print('PASS 5,000 full original relative-bounds calls, including null-image preservation, no callees')

for i in range(5000):
    raw=[rng.getrandbits(32)for _ in range(32)]
    projection=make(Projection,[rng.getrandbits(32)for _ in range(9)])
    raw[8//4]=projection.flags
    for offset,field in [(0x30,'extentX'),(0x34,'extentY'),(0x40,'cameraX'),(0x44,'cameraY'),(0x48,'visibleEndX'),(0x4c,'visibleEndY'),(0x50,'screenOffsetX'),(0x54,'screenOffsetY')]: raw[offset//4]=getattr(projection,field)
    x,y=U(rng.getrandbits(32)),U(rng.getrandbits(32))
    m.write_words(projection_address,raw);m.write_words(rect_address,[x.value,y.value])
    m.call(0x4c96d0,projection_address,packed(rect_address,rect_address+4))
    lib.claw_sprite_project(C.byref(projection),C.byref(x),C.byref(y))
    assert[x.value,y.value]==m.read_words(rect_address,2),(i,'plane projection')
    assert raw==m.read_words(projection_address,32)
print('PASS 5,000 full original plane-projection calls with complete input buffers preserved, no callees')

actor_fields={0x8:'flags',0x10:'displacementX',0x14:'displacementY',0x40:'renderFlags',0x44:'blinkRemaining',0x48:'blinkInterval',0x4c:'x',0x50:'y',0x18:'drawX',0x1c:'drawY',0x30:'drawWidth',0x34:'drawHeight',0x38:'drawStatus'}
def compare_draw(g,a,c,label):
    global blits,copies
    before=[rng.getrandbits(32)for _ in range(128)];iw=[rng.getrandbits(32)for _ in range(128)]
    for offset,field in actor_fields.items(): before[offset//4]=getattr(a,field)
    before[0x20//4:0x30//4]=words(a.drawn);before[0x54//4:0x64//4]=words(a.clip)
    before[0x3c//4]=holder_address
    for offset,field in [(0x10,'width'),(0x14,'height'),(0x18,'halfWidth'),(0x1c,'halfHeight'),(0x20,'offsetX'),(0x24,'offsetY'),(0x28,'surfaceKind'),(0x2c,'surfaceToken')]:iw[offset//4]=getattr(g,field)
    iw[0x30//4]=g.compressedToken if g.compressed else 0;iw[0xc//4]=owner_address
    m.write_words(actor_address,before);m.write_words(image_address,iw)
    vr=[rng.getrandbits(32)for _ in range(128)];vr[4:6]=[c.width,c.height];vr[0x2c//4]=c.surfaceToken;m.write_words(viewport_address,vr)
    m.write_words(owner_address+0x24,[world_address]);m.write_words(world_address+0x10,words(c.worldClip))
    m.write_words(holder_address+0x5c,[projection_address])
    pr=[rng.getrandbits(32)for _ in range(32)];pr[2]=c.projection.flags
    for offset,field in [(0x30,'extentX'),(0x34,'extentY'),(0x40,'cameraX'),(0x44,'cameraY'),(0x48,'visibleEndX'),(0x4c,'visibleEndY'),(0x50,'screenOffsetX'),(0x54,'screenOffsetY')]:pr[offset//4]=getattr(c.projection,field)
    m.write_words(projection_address,pr)
    m.write_words(0x5430c4,[c.animationDelta]);m.write_words(0x54310c,[c.directDrawFlip])
    blits=[];copies=[]
    m.call(0x4d2890,image_address,packed(actor_address,viewport_address))
    command=Command();lib.claw_sprite_prepare_draw(C.byref(g),C.byref(a),C.byref(c),C.byref(command))
    expected=before[:]
    for offset,field in actor_fields.items():expected[offset//4]=getattr(a,field)
    expected[0x20//4:0x30//4]=words(a.drawn)
    actual=m.read_words(actor_address,128)
    assert expected==actual,(label,'actor mismatch',[(hex(k*4),hex(v),hex(actual[k]))for k,v in enumerate(expected)if v!=actual[k]])
    assert iw==m.read_words(image_address,128) and vr==m.read_words(viewport_address,128) and pr==m.read_words(projection_address,32),(label,'mutated unrelated buffer')
    assert c.directDrawFlip==m.read_words(0x54310c,1)[0],(label,'global flip')
    got=[words(command)] if command.kind else []
    assert got==blits,(label,'blit mismatch',got,blits)
    return command

for i in range(10000):
    width,height=rng.randint(1,257),rng.randint(1,257)
    g=Geometry(width,height,width//2,height//2,rng.randint(-130,130)&0xffffffff,rng.randint(-130,130)&0xffffffff,i%2,0x1010000,0x1011000,0x10+(i%3==0))
    a=make(Actor,[rng.getrandbits(32)for _ in range(C.sizeof(Actor)//4)])
    a.flags=(rng.getrandbits(32)&~0x40000)|(0x40000 if i%3==0 else 0)
    a.x=rng.randint(-200,1200)&0xffffffff;a.y=rng.randint(-200,1000)&0xffffffff
    a.displacementX=rng.randint(-40,40)&0xffffffff;a.displacementY=rng.randint(-40,40)&0xffffffff
    a.renderFlags=(rng.getrandbits(32)&~15)|(i%16)
    a.blinkRemaining=rng.randrange(1000);a.blinkInterval=rng.randrange(1000)
    a.clip=Rect(0x80000000,0,0,0) if i%4==0 else Rect(rng.randint(-100,500)&0xffffffff,rng.randint(-100,400)&0xffffffff,rng.randint(500,1100),rng.randint(400,900))
    c=Context();c.width=800;c.height=600;c.surfaceToken=0x1012000;c.animationDelta=rng.randrange(1000);c.directDrawFlip=rng.getrandbits(32)
    c.worldClip=Rect(10,20,789,579)
    c.projection=Projection(rng.getrandbits(32),1536,7680,rng.randrange(1700),rng.randrange(8000),rng.randrange(3000),rng.randrange(9000),13,23)
    compare_draw(g,a,c,('generated',i))
print('PASS 10,000 full original draw dispatcher calls: 8 compressed/surface flip paths, hide/blink, clipping, projected wrapping; complete actor/image/viewport/projection buffers and logged blit arguments')

for compressed in (0,1):
    for flags,expected in [(0,[95,103,97,107]),(2,[103,103,105,107]),(4,[95,93,97,97]),(6,[103,93,105,97])]:
        g=Geometry(3,5,1,2,(-7)&0xffffffff,9,compressed,0x1010000,0x1011000,0x11)
        a=Actor();a.x=100;a.y=100;a.displacementX=3;a.displacementY=(-4)&0xffffffff;a.renderFlags=flags;a.clip.left=0x80000000
        c=Context();c.width=800;c.height=600;c.surfaceToken=0x1012000
        command=compare_draw(g,a,c,('odd dimensions',compressed,flags))
        assert words(a.drawn)==expected,('odd origin',compressed,flags,words(a.drawn))
print('PASS directed odd-size image: original 3x5 draw origins in all flip combinations, signed PID offsets and actor displacements')

if args.assets:
    paths=sorted(args.assets.rglob('*.PID'));checked=0
    for path in paths:
        data=path.read_bytes();signature,flags,w,h,ox,oy=struct.unpack_from('<6I',data)
        assert signature==10
        for flip in (0,2,4,6):
            g=Geometry(w,h,w//2,h//2,ox,oy,int(bool(flags&32)),0x1010000,0x1011000,0x11)
            a=Actor();a.x=400;a.y=300;a.renderFlags=flip;a.clip.left=0x80000000
            c=Context();c.width=800;c.height=600;c.surfaceToken=0x1012000
            c.worldClip=Rect(0,0,799,599)
            compare_draw(g,a,c,(str(path),flip));checked+=1
    print(f'PASS {len(paths)} actual CD-rip PID headers / {checked} flip calls through full original renderer geometry (pixel blits adapted)')

    # Real compressed image setup, original ctor/header/raw-data copying unmodified.
    # At 8 bpp this only needs a logged CRT allocation adapter; no pixel decoder stub.
    u.mem_map(0,4096) # original SEH FS:0 slot, required by 0x4d25e0.
    heap_base=0x1040000;heap_cursor=heap_base;allocations=[]
    def allocate(uc,address,size,user):
        global heap_cursor
        if address!=0x4f63ec:return
        count=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)[0]
        allocations.append(count)
        result=heap_cursor;heap_cursor+=(count+15)&~15
        assert count>0 and heap_cursor<0x10e0000
        u.mem_write(result,bytes(count));host_return(0,result)
    u.hook_add(UC_HOOK_CODE,allocate)
    compressed_count=0
    for path in paths:
        data=path.read_bytes();signature,flags,w,h,ox,oy=struct.unpack_from('<6I',data)
        if not flags&32:continue
        assert not flags&64,'Lighting setup requires another adapter'
        heap_cursor=heap_base;allocations.clear()
        iw=[rng.getrandbits(32)for _ in range(128)];iw[3]=owner_address
        m.write_words(image_address,iw);u.mem_write(0x1020000,data)
        m.write_words(owner_address+4,[0x1008000]);m.write_words(0x1008000+0x10,[0x1009000]);m.write_words(0x1009000+0x18,[8])
        result=m.call(0x4d25e0,image_address,packed(0x1020000,len(data)))
        assert result==1 and allocations==[40,len(data)-32]
        g=make(Geometry,[rng.getrandbits(32)for _ in range(10)])
        initial=words(g);lib.claw_sprite_set_geometry(C.byref(g),w,h,ox,oy)
        after=m.read_words(image_address,128)
        expected=iw[:]
        expected[4:10]=words(g)[:6];expected[10]=0x11;expected[12]=heap_base
        assert expected==after,(path,'complete image setup buffer')
        assert words(g)[6:]==initial[6:],'Geometry field helper changed tokens/kind'
        stored=m.read_words(heap_base,10)
        assert stored[1:3]==[w,h] and stored[4]==len(data)-32
        assert bytes(u.mem_read(stored[3],len(data)-32))==data[32:],(path,'original encoded pixel copy')
        compressed_count+=1
    print(f'PASS {compressed_count} complete original compressed PID setups at 8 bpp: geometry stores and original encoded-data copying, only CRT allocation adapted')
required={0x4061e0,0x4c96d0,0x4d2890,0x4d2bb0,0x4d2e10,0x4d3080,0x4d32e0,0x4d3550,0x4d3790,0x4d3a00}
assert required<=m.executed,('missing paths',required-m.executed)
print(f'{len(m.executed)} original instruction addresses reached; draw adapters: surface blits 0x4b9d80/0x4b9ce0, compressed pixel blit 0x4bffa0, Windows CopyRect; separate loader adapter: CRT allocation 0x4f63ec')
