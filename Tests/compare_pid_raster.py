#!/usr/bin/env python3
"""Original compressed PID raster comparison; only DirectDraw lock/unlock adapted."""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10

class Info(C.Structure):
    _fields_=[('width',C.c_uint32),('height',C.c_uint32),('offsetX',C.c_int32),('offsetY',C.c_int32),('consumed',C.c_size_t)]
def packed(*x):return struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x))
def header(w,h,ox=0,oy=0,flags=32):return packed(10,flags,w,h,ox,oy,0,0)

p=argparse.ArgumentParser();p.add_argument('exe',type=Path);p.add_argument('library',type=Path);p.add_argument('--assets',type=Path);a=p.parse_args()
lib=C.CDLL(str(a.library.resolve()));decode=lib.claw_pid_decode_raster8
decode.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_size_t,C.c_size_t,C.POINTER(Info)];decode.restype=C.c_uint32
m=OriginalV10(a.exe);u=m.u
object_address,encoded_address,surface_address,destination_address,source_address=0x1000000,0x1020000,0x1001000,0x1002000,0x1003000
dd_address,vtable_address,unlock_adapter=0x1004000,0x1005000,0x10ef000
pixels_address=0x1080000;guard=64
m.write_words(surface_address+8,[dd_address]);m.write_words(dd_address,[vtable_address]);m.write_words(vtable_address+0x80,[unlock_adapter])
host_events=[]
def host_return(pop,result):
    sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
    u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
    if address not in (0x4b9730,unlock_adapter):return
    sp=u.reg_read(UC_X86_REG_ESP)
    if address==0x4b9730:
        assert u.reg_read(UC_X86_REG_ECX)==surface_address and m.read_words(sp+4,1)==[0]
        host_events.append('lock');host_return(4,pixels_address+guard)
    else:
        assert m.read_words(sp+4,2)==[dd_address,0]
        host_events.append('unlock');host_return(8,0)
u.hook_add(UC_HOOK_CODE,host)
rng=random.Random(1997);calls=0;decoded_pixels=0
def check(data,label,flips=True):
    global calls,decoded_pixels
    _,flags,w,h,ox,oy,*_=struct.unpack('<8I',data[:32]);assert flags&32
    pitch=w+rng.randrange(1,12);size=pitch*h
    native=(C.c_uint8*size)(*([0x79]*size));coverage=(C.c_uint8*size)(*([0x41]*size));source=(C.c_uint8*len(data)).from_buffer_copy(data);info=Info()
    assert decode(source,len(data),native,coverage,size,pitch,C.byref(info))==1,label
    assert info.width==w and info.height==h and info.offsetX==C.c_int32(ox).value and info.offsetY==C.c_int32(oy).value
    for y in range(h):
        assert bytes(native)[y*pitch+w:(y+1)*pitch]==bytes([0x79])*(pitch-w)
        assert bytes(coverage)[y*pitch+w:(y+1)*pitch]==bytes([0x41])*(pitch-w)
    u.mem_write(encoded_address,data[32:])
    raw=[0]*10;raw[1]=w;raw[2]=h;raw[3]=encoded_address;raw[4]=len(data)-32;raw[5]=1;raw[9]=1
    m.write_words(object_address,raw);m.write_words(surface_address+0x1c,[pitch])
    m.write_words(destination_address,[0,0,w-1,h-1]);m.write_words(source_address,[0,0,w-1,h-1])
    modes=[(0,0),(1,0),(0,1),(1,1)] if flips else [(0,0)]
    for fx,fy in modes:
        for seed in (0x9a,0xb5):
            before=bytes([seed])*(size+guard*2);u.mem_write(pixels_address,before);host_events.clear()
            result=m.call(0x4bffa0,object_address,packed(destination_address,surface_address,source_address,fx,fy))
            assert result==1 and host_events==['lock','unlock'],(label,fx,fy,'host contract')
            actual=bytes(u.mem_read(pixels_address,size+guard*2));expected=bytearray(before)
            for sy in range(h):
                dy=h-1-sy if fy else sy
                for sx in range(w):
                    # Exact original full-width horizontal body starts at width,
                    # not width-1: mirrored writes include one column to the right.
                    dx=w-sx if fx else sx;source_offset=sy*pitch+sx
                    if coverage[source_offset]:expected[guard+dy*pitch+dx]=native[source_offset]
            assert actual==expected,(label,fx,fy,'raster mismatch',[(j-guard,actual[j],expected[j])for j in range(len(expected))if actual[j]!=expected[j]][:12])
            assert raw==m.read_words(object_address,10),(label,'image object mutation')
            calls+=1
    decoded_pixels+=w*h
    return bytes(native),bytes(coverage),info

# Literal zero must overwrite a destination. Skipped transparency must retain it.
check(header(3,2,-7,9)+bytes([1,0,129,1,3,131]),'literal zero and transparent skip')
for first_word in (0,0x1869f,0xffffffff):
    check(packed(first_word)+header(3,2,-7,9)[4:]+bytes([1,0,129,1,3,131]),('opaque header word',first_word))
for index in range(2000):
    w,h=rng.randrange(1,40),rng.randrange(1,25);body=bytearray()
    for y in range(h):
        x=0
        while x<w:
            n=rng.randrange(1,min(127,w-x)+1)
            if rng.randrange(3)==0:body.append(128+n)
            else:body.append(n);body.extend(rng.randrange(256)for _ in range(n))
            x+=n
    check(header(w,h,rng.getrandbits(32),rng.getrandbits(32))+body,('generated',index))
print('PASS 2,000 generated compressed PID rasters plus literal-zero fixture: all four full-image flip modes, two background seeds, pitch padding and guard bytes; original pixel bodies execute',flush=True)
if a.assets:
    count=0
    for path in sorted(a.assets.rglob('*.PID')):
        data=path.read_bytes()
        if struct.unpack_from('<I',data,4)[0]&32:
            check(data,str(path));count+=1
    print(f'PASS all {count} actual compressed CLAW/Level 1 PIDs through original plain/horizontal/vertical/both pixel bodies',flush=True)

# Safe native behavior is a deliberate extension, not original malformed-input parity.
valid=header(3,1)+bytes([3,0,1,2])
for invalid in [b'',valid[:31],valid[:-1],header(3,1,flags=0)+valid[32:],header(0,1),header(3,1)+bytes([0]),header(3,1)+bytes([128]),header(3,1)+bytes([132]),header(3,1)+bytes([4,0,1,2,3])]:
    source=(C.c_uint8*len(invalid)).from_buffer_copy(invalid);out=(C.c_uint8*24)(*([0x99]*24));cov=(C.c_uint8*24)(*([0x77]*24));info=Info(123,456,7,8,999);before=bytes(info)
    assert decode(source,len(invalid),out,cov,24,6,C.byref(info))==0
    assert bytes(out)==bytes([0x99])*24 and bytes(cov)==bytes([0x77])*24 and bytes(info)==before
print('PASS unsupported/truncated/malformed native inputs reject without output mutation',flush=True)
assert {0x4bffa0,0x4c00b0,0x4c0450,0x4c0920,0x4c0cc0}<=m.executed
print(f'{calls} full original pixel calls; {decoded_pixels} source pixels; {len(m.executed)} original instruction addresses. Only DirectDraw lock 0x4b9730 and virtual unlock adapted; no pixel decoder/blitter stubs.',flush=True)
