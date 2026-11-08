#!/usr/bin/env python3
"""Compare bounded original instruction blocks, with no nested calls or stubs.
Addresses are supplied explicitly: verify docs/animation-operations.md first.
"""
import argparse,ctypes,hashlib,random,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser(); p.add_argument('exe',type=Path); p.add_argument('library',type=Path)
p.add_argument('--reference',choices=['v1.0','crazyhook'],default='v1.0')
a=p.parse_args(); b=a.exe.read_bytes()
profiles={'v1.0':('350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',0x4c82a0,0x4c8487,0x4c84f7,0x4c8305,4,12,0x4c,0x50,[2,5,6,8,9]),'crazyhook':('33cf6e2663823f073d769c3d05a1ad5e13e3e4993ad2cb6822617737395004c6',0x4c8550,0x4c873c,0x4c87ac,0x4c85ad,16,24,0x5c,0x60,[5,8,9,12,13])}
expected,entry,mstart,mend,dend,owner,rec,xoff,yoff,fields=profiles[a.reference]
assert hashlib.sha256(b).hexdigest()==expected,'Unverified binary; do not reuse addresses'
pe=struct.unpack_from('<I',b,60)[0]; n=struct.unpack_from('<H',b,pe+6)[0]; opt=struct.unpack_from('<H',b,pe+20)[0]
base,size=struct.unpack_from('<I',b,pe+52)[0],struct.unpack_from('<I',b,pe+80)[0]
u=Uc(UC_ARCH_X86,UC_MODE_32); u.mem_map(base,(size+4095)&~4095)
for i in range(n):
 o=pe+24+opt+40*i; _,va,rs,ro=struct.unpack_from('<4I',b,o+8)
 if rs:u.mem_write(base+va,b[ro:ro+rs])
u.mem_map(0x1000000,0x10000); u.mem_map(0x2000000,0x10000)
actor,state,record,stack,stop=0x1000000,0x1001000,0x1002000,0x2008000,0x200f000
def boundary(uc,address,size,user):
 if address in (stop,dend): uc.emu_stop()
u.hook_add(UC_HOOK_CODE,boundary)
lib=ctypes.CDLL(str(a.library.resolve())); ptr=ctypes.POINTER(ctypes.c_uint32)
move=lib.claw_animation_movement; move.argtypes=[ptr,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32]
delay=lib.claw_animation_delay; delay.argtypes=[ptr,ctypes.c_uint32,ptr]; delay.restype=ctypes.c_uint32
rng=random.Random(1997)
def w(addr,arr):u.mem_write(addr,struct.pack('<'+'I'*len(arr),*arr))
def read(addr,count):return list(struct.unpack('<'+'I'*count,u.mem_read(addr,4*count)))
# Stop at the first instruction following each recovered slice.
for case in range(1200):
 mode=[0,1,2,3,4,0xffffffff][case%6]; dx,dy=[rng.getrandbits(32) for _ in range(2)]
 values=[rng.getrandbits(32) for _ in range(128)]
 normalized=values[:]; normalized[0x4c//4]=values[xoff//4];normalized[0x50//4]=values[yoff//4]
 native=(ctypes.c_uint32*128)(*normalized);move(native,mode,dx,dy)
 w(actor,values);w(state+owner,[actor]);w(state+rec,[record]);w(record+0x10,[mode]);w(record+0x20,[dx,dy])
 u.reg_write(UC_X86_REG_ESI,state);u.reg_write(UC_X86_REG_EBP,0);u.reg_write(UC_X86_REG_ESP,stack)
 u.emu_start(mstart,mend,count=100)
 expected_actor=values[:]
 for offset in [0x10,0x14]: expected_actor[offset//4]=native[offset//4]
 expected_actor[xoff//4]=native[0x4c//4];expected_actor[yoff//4]=native[0x50//4]
 assert read(actor,128)==expected_actor,(case,mode)
for case in range(1200):
 values=[rng.getrandbits(32) for _ in range(32)]
 values[fields[0]]=[0,record][case%2];values[fields[1]]=[0,1,10,0xffffffff][case%4];values[fields[2]]=[0,1][case//4%2]
 tick=[0,1,9,10,11,0xffffffff,rng.getrandbits(32)][case%7]
 normalized=values[:]
 for dst,src in zip([2,5,6,8,9],fields): normalized[dst]=values[src]
 native=(ctypes.c_uint32*32)(*normalized); ready=ctypes.c_uint32()
 result=delay(native,tick,ctypes.byref(ready));w(state,values);w(stack,[stop,tick]);u.reg_write(UC_X86_REG_ECX,state);u.reg_write(UC_X86_REG_ESP,stack)
 u.emu_start(entry,dend,count=100)
 reached=u.reg_read(UC_X86_REG_EIP)==dend
 assert reached==bool(ready.value)
 expected_state=values[:]
 for src,dst in zip([2,5,6,8,9],fields): expected_state[dst]=native[src]
 assert read(state,32)==expected_state,case
 if not reached: assert u.reg_read(UC_X86_REG_EAX)==result
print('PASS: 1200 movement + 1200 delay-prefix cases; no callees stubbed; bounded blocks only')
print('Input SHA-256:',hashlib.sha256(b).hexdigest())
