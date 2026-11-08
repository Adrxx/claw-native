#!/usr/bin/env python3
"""Real original clipped 8-bit blitters; only DirectDraw lock/unlock adapted."""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
from original_v10 import OriginalV10

class Rect(C.Structure):
    _fields_=[(x,C.c_int32) for x in ('left','top','right','bottom')]
class Command(C.Structure):
    _fields_=[('destination',Rect),('source',Rect),('flipX',C.c_uint32),('flipY',C.c_uint32),('originalSourceRectAddress',C.c_uint32)]
class Info(C.Structure): _fields_=[('consumed',C.c_size_t),('writes',C.c_size_t)]
def packed(*x): return struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x))
def header(w,h,flags=32):return packed(10,flags,w,h,0,0,0,0)
p=argparse.ArgumentParser();p.add_argument('exe',type=Path);p.add_argument('library',type=Path);p.add_argument('--assets',type=Path);a=p.parse_args()
lib=C.CDLL(str(a.library.resolve()));native=lib.claw_pid_blit8
native.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Command),C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_size_t,C.c_size_t,C.POINTER(Info)];native.restype=C.c_uint32
m=OriginalV10(a.exe);u=m.u
image, encoded, surface, destination, source=0x1000000,0x1020000,0x1001000,0x1002000,0x1003000
dd,vtable,unlock,pixels=0x1004000,0x1005000,0x10ef000,0x1080000
u.mem_map(0,4096);u.mem_map(0x7ffff000,4096);u.mem_map(0xfffff000,4096)
m.write_words(surface+8,[dd]);m.write_words(dd,[vtable]);m.write_words(vtable+0x80,[unlock])
guard=128;events=[];write_offsets=set();write_bytes=0;current_size=0
def host_return(pop,result):
    sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
    u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
    if address==0x4b9730:
        sp=u.reg_read(UC_X86_REG_ESP)
        assert u.reg_read(UC_X86_REG_ECX)==surface and m.read_words(sp+4,1)==[0]
        events.append('lock');host_return(4,pixels+guard)
    elif address==unlock:
        sp=u.reg_read(UC_X86_REG_ESP);assert m.read_words(sp+4,2)==[dd,0]
        events.append('unlock');host_return(8,0)
def writes(uc,access,address,size,value,user):
    global write_bytes
    if pixels<=address<pixels+current_size+guard*2:
        assert address>=pixels+guard and address+size<=pixels+guard+current_size,('original writes outside usable buffer',hex(address),size)
        write_offsets.update(range(address-pixels-guard,address-pixels-guard+size));write_bytes+=size
u.hook_add(UC_HOOK_CODE,host);u.hook_add(UC_HOOK_MEM_WRITE,writes)
rng=random.Random(1997);calls=total_writes=rejected=0;branches=set()
def check(data,src,dst,fx,fy,label,source_address=source,expect_accept=True):
    global calls,current_size,total_writes,rejected,write_bytes
    _,flags,w,h,*_=struct.unpack('<8I',data[:32]);assert flags&32
    # A generous framebuffer keeps original clipping spills inside its capacity.
    pitch=w+29;rows=h+12;size=pitch*rows;current_size=size
    assert size+guard*2<unlock-pixels
    source_data=(C.c_uint8*len(data)).from_buffer_copy(data)
    out=(C.c_uint8*size)(*([0x9a]*size));cov=(C.c_uint8*size)(*([0x41]*size));info=Info(999,888)
    cmd=Command(Rect(*dst),Rect(*src),fx,fy,source_address)
    result=native(source_data,len(data),C.byref(cmd),out,cov,size,pitch,C.byref(info))
    assert result==int(expect_accept),(label,src,dst,fx,fy,'native rejects',result)
    if not result:
        assert bytes(out)==bytes([0x9a])*size and bytes(cov)==bytes([0x41])*size and (info.consumed,info.writes)==(999,888)
    u.mem_write(encoded,data[32:])
    raw=[0]*10;raw[1]=w;raw[2]=h;raw[3]=encoded;raw[4]=len(data)-32;raw[5]=1;raw[9]=1
    m.write_words(image,raw);m.write_words(surface+0x1c,[pitch]);m.write_words(destination,dst);m.write_words(source_address,src)
    before=bytes([0x9a])*(size+guard*2);u.mem_write(pixels,before);events.clear();write_offsets.clear();write_bytes=0
    original=m.call(0x4bffa0,image,packed(destination,surface,source_address,fx,fy))
    assert original==result,(label,'dispatch result')
    assert events==(['lock','unlock'] if result else []),(label,events)
    expected=bytearray(before);expected[guard:guard+size]=bytes(out)
    actual=bytes(u.mem_read(pixels,size+guard*2))
    assert actual==expected,(label,src,dst,fx,fy,'pixels differ',[(i-guard,actual[i],expected[i])for i in range(len(actual))if actual[i]!=expected[i]][:12])
    mask=bytearray([0x41])*size
    for offset in write_offsets:mask[offset]=1
    assert bytes(cov)==mask,(label,'write coverage differs')
    if result:
        assert info.writes==write_bytes,(label,'total literal write count',info.writes,write_bytes)
        total_writes+=write_bytes
        branches.add((bool(fx),bool(fy),src[0]==0,src[2]==w-1,src[1]>0))
    assert m.read_words(image,10)==raw and m.read_words(destination,4)==[v&0xffffffff for v in dst] and m.read_words(source_address,4)==[v&0xffffffff for v in src],(label,'receiver or rectangles mutated')
    assert bytes(u.mem_read(encoded,len(data)-32))==data[32:],(label,'encoded source mutated')
    calls+=1;rejected+=not result

def all_modes(data,src,dst,label):
    for fx,fy in [(0,0),(1,0),(0,1),(1,1)]:check(data,src,dst,fx,fy,label)

# Multiple run boundaries matter: literal at zero, transparent middle, tails.
fixture=header(7,4)+bytes([2,0,1,130,3,2,3,4, 135, 1,5,1,6,2,7,8,131, 7,9,10,11,12,13,14,15])
for first_word in (0,0x1869f,0xffffffff):
    all_modes(packed(first_word)+fixture[4:],(0,0,6,3),(5,4,11,7),('opaque header word',first_word))
for top in range(4):
    for bottom in range(top,4):
        for left in range(7):
            for right in range(left,7):
                all_modes(fixture,(left,top,right,bottom),(5,4,11,4+bottom-top),('directed',left,top,right,bottom))
print('PASS directed complete source rectangle matrix on odd-sized mixed literal/transparent fixture',flush=True)
# Source pointer dependency in the BOTH top-skip path is an actual original bug.
for address in (4,37,0x7fffffe0,source):
    for top in (1,2,3):
        check(fixture,(0,top,6,3),(5,4,11,7-top),1,1,('source pointer',hex(address),top),address)
for index in range(700):
    w,h=rng.randrange(1,50),rng.randrange(1,20);body=bytearray()
    for y in range(h):
        x=0
        while x<w:
            n=rng.randrange(1,min(127,w-x)+1)
            if rng.randrange(3)==0:body.append(128+n)
            else:body.append(n);body.extend(rng.randrange(256)for _ in range(n))
            x+=n
    data=header(w,h)+body
    top=rng.randrange(h);bottom=rng.randrange(top,h);left=rng.randrange(w);right=rng.randrange(left,w)
    # Dest.right is deliberately independent: bodies ignore it. Negative X is
    # valid when its physical byte addresses still lie in the supplied buffer.
    dx=rng.randrange(-3,12);dy=rng.randrange(2,7);db=dy+bottom-top+rng.randrange(-1,2)
    all_modes(data,(left,top,right,bottom),(dx,dy,rng.randrange(-10,20),db),('generated',index))
print('PASS 700 generated clipped/offset draws, all four modes, negative/odd offsets and source-pointer probes',flush=True)
if a.assets:
    count=0
    for path in sorted(a.assets.rglob('*.PID')):
        data=path.read_bytes();flags,w,h=struct.unpack_from('<3I',data,4)
        if not flags&32:continue
        cases=[(0,0,w-1,h-1),(0,0,max(0,w//2),h-1),(min(1,w-1),0,w-1,h-1),
               (0,min(1,h-1),w-1,h-1),(w//3,h//3,max(w//3,w*2//3),max(h//3,h*2//3))]
        for src in cases:all_modes(data,src,(5,4,5+src[2]-src[0],4+src[3]-src[1]),str(path))
        count+=1
    print(f'PASS all {count} actual compressed CLAW/Level1 PIDs, five full/clipped rectangles each, all four modes',flush=True)
# Original dispatch rejects these four predicates; no lock/unlock/writes.
for src in [(-1,0,6,3),(0,0,7,3),(0,-1,6,3),(0,4,6,4)]:
    check(fixture,src,(5,4,11,7),0,0,('dispatch reject',src),expect_accept=False)
# Accepted source rectangles may be inverted: preserve original no-op outcomes.
for src in [(0,2,6,1),(1,2,1,2),(0,0,-1,-1),(9,2,6,1)]:all_modes(fixture,src,(5,4,11,7),('inverted',src))
for data in [b'',fixture[:31],fixture[:-1],header(7,4,0)+fixture[32:],header(7,1)+bytes([0]),header(7,1)+bytes([136])]:
    src=(C.c_uint8*len(data)).from_buffer_copy(data);out=(C.c_uint8*256)(*([0x99]*256));cov=(C.c_uint8*256)(*([0x77]*256));info=Info(123,456);cmd=Command(Rect(0,0,6,3),Rect(0,0,6,3),0,0,source)
    assert native(src,len(data),C.byref(cmd),out,cov,256,16,C.byref(info))==0
    assert bytes(out)==bytes([0x99])*256 and bytes(cov)==bytes([0x77])*256 and (info.consumed,info.writes)==(123,456)
# A valid image whose +1 mirror would write outside capacity rejects atomically.
data=header(1,1)+bytes([1,0]);src=(C.c_uint8*len(data)).from_buffer_copy(data);out=(C.c_uint8*1)(99);info=Info(123,456);cmd=Command(Rect(0,0,0,0),Rect(0,0,0,0),1,0,source)
assert native(src,len(data),C.byref(cmd),out,None,1,1,C.byref(info))==0 and out[0]==99 and (info.consumed,info.writes)==(123,456)
assert {0x4bffa0,0x4c00b0,0x4c0450,0x4c0920,0x4c0cc0}<=m.executed
assert len(branches)==32,('missing branch combinations',len(branches),branches)
addresses=m.executed-{0x4b9730,unlock,m.stop}
print(f'PASS {calls} real original dispatcher calls, {total_writes} byte writes, {rejected} original rejected draws, {len(addresses)} original instruction addresses; full buffers, coverage, guards, source/receiver/rect immutability. Only lock/unlock adapted.',flush=True)
