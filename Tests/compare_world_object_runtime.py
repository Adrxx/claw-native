#!/usr/bin/env python3
"""Whole original4d17e0 loader comparison; explicit bounded host dependencies."""
import argparse
import collections
import ctypes as C
from pathlib import Path
import random
import struct
import subprocess
import zlib
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
from original_v10 import OriginalV10

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');p.add_argument('--world',type=Path,default=ROOT/'App/GameData/LEVEL1/WORLDS/WORLD.WWD');a=p.parse_args()
library=ROOT/'work/world-object-agent/libWorldObjectRuntime.dylib'
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/WorldObjectRuntime.cpp'),'-o',str(library)],check=True)
class State(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class Context(C.Structure):
    _fields_=[(x,C.c_uint32) for x in ('sceneToken','actorToken','logicToken','sceneDefaultType')]+[(x,C.c_int32) for x in ('worldWidth','worldHeight')]+[('registryToken',C.c_uint32),('layerTokens',C.c_uint32*3)]+[(x,C.c_uint32) for x in ('entryToken','entryCallback','entryFlags')]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('text',C.c_char_p)]
class Info(C.Structure):_fields_=[('consumed',C.c_uint32),('created',C.c_uint32)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(library));load=lib.claw_world_object_load
load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(State),C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(Info)];load.restype=C.c_uint32
m=OriginalV10(a.exe);u=m.u;u.mem_map(0,4096)
record,actor,logic,loader,scene,registry,map_object,spatial,entry=0x1000000,0x1002000,0x1003000,0x1004000,0x1005000,0x1006000,0x1007000,0x1008000,0x100c000
layers=[0x1009000,0x100a000,0x100b000];string_heap=0x1040000
def packed(*x):return struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x))
def string(address):
    data=bytes(u.mem_read(address,1024));return data.split(b'\0',1)[0]
events=[];allocations=[];cstring_events=[];config={};heap_cursor=string_heap;original_created=False
def portable(address,receiver,args=(),text=None):return(address,receiver,tuple(args),text)
def mutate(a,l,function):
    # Audited dependency mutations establish ordering; these do not claim to
    # recover image/sound/destructor/spatial implementations.
    if function in (0x4c7970,0x4c7900):a[0x174//4]=0x12345678;a[2]^=0x80;a[0xdc//4]=33
    elif function==0x4c79e0:a[0x178//4]=0x87654321;l[0xf0//4]=0xfedcba98
    elif function==0x4c7a40:a[2]^=0x100;a[0x40//4]=7
    elif function==0x4c9be0:a[0x68//4]=0xdeadbeef
    elif function==0x4f4630:a[0x90//4]=0x1200;a[0x94//4]=0x1300;l[0x60//4]=0x1400
@Dependency
def dependency(state,context,event,user):
    event=event.contents;c=context.contents
    text=event.text if event.text is not None else None
    events.append(portable(event.function,event.receiver,event.arguments[:event.argumentCount],text))
    if event.function==0x4f6286:
        c.entryFlags=config['flags'];c.entryCallback=config['callback'];return entry if config['found'] else 0
    mutate(state.contents.actor,state.contents.logic,event.function);return 1

def host_return(pop,result):
    sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
    u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
    global heap_cursor,original_created
    if address not in (0x4f63ec,0x4f65f2,0x4f6584,0x4f6286,0x4c7970,0x4c7900,0x4c79e0,0x4c7a40,0x4c9be0,0x4f4630):return
    sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
    if address==0x4f63ec:
        count=m.read_words(sp+4,1)[0];allocations.append(count)
        assert count in (0x1b4,0x174);host_return(0,actor if count==0x1b4 else logic);return
    if address==0x4f65f2:
        text=string(m.read_words(sp+4,1)[0]);result=heap_cursor+12;heap_cursor+=len(text)+32
        m.write_words(result-12,[1,len(text),len(text)]);u.mem_write(result,text+b'\0');m.write_words(receiver,[result]);cstring_events.append(('create',text));host_return(4,receiver);return
    if address==0x4f6584:
        text=string(m.read_words(receiver,1)[0]);cstring_events.append(('destroy',text));host_return(0,0);return
    if address==0x4f6286:
        name,out=m.read_words(sp+4,2);events.append(portable(address,receiver,(),string(name)))
        assert receiver==map_object+16
        m.write_words(out,[entry if config['found'] else 0]);host_return(8,int(config['found']));return
    text=None;args=();pop=4
    if address in (0x4c7970,0x4c7a40):text=string(m.read_words(sp+4,1)[0])
    elif address in (0x4c7900,0x4c79e0):ptr,arg=m.read_words(sp+4,2);text=string(ptr);args=(arg,);pop=8
    elif address==0x4c9be0:args=tuple(m.read_words(sp+4,1))
    elif address==0x4f4630:
        args=tuple(m.read_words(sp+4,1));assert receiver in layers and args==(actor+0x88,);original_created=True
    events.append(portable(address,receiver,args,text))
    aw=m.read_words(actor,128);lw=m.read_words(logic,93);mutate(aw,lw,address);m.write_words(actor,aw);m.write_words(logic,lw)
    host_return(pop,1)
u.hook_add(UC_HOOK_CODE,host)
rng=random.Random(1997);calls=0
def make_record(words,strings):
    words=list(words);parts=[x if isinstance(x,bytes) else x.encode()for x in strings]
    words[1:5]=list(map(len,parts));return packed(*words)+b''.join(parts)
def check(data,label,flags=0,callback=0x415df0,found=True,width=24576,height=6144):
    global calls,heap_cursor,original_created
    seed_a=[rng.getrandbits(32)for _ in range(128)];seed_l=[rng.getrandbits(32)for _ in range(93)]
    state=State((C.c_uint32*128)(*seed_a),(C.c_uint32*93)(*seed_l))
    c=Context(scene,actor,logic,2,width,height,map_object+16,(C.c_uint32*3)(*layers),0,callback,flags)
    config.update(flags=flags,callback=callback,found=found);source=(C.c_uint8*len(data)).from_buffer_copy(data);info=Info(123,456);events.clear()
    result=load(source,len(data),C.byref(state),C.byref(c),dependency,None,C.byref(info));expected_events=list(events)
    m.write_words(actor,seed_a);m.write_words(logic,seed_l);u.mem_write(record,data)
    m.write_words(loader+12,[scene]);m.write_words(loader+0x30,[width,height]);m.write_words(loader+0xb0,[spatial])
    m.write_words(scene+0x24,[2]);m.write_words(scene+0x14,[map_object]);m.write_words(spatial+4,layers)
    m.write_words(entry+8,[flags,0,callback]);heap_cursor=string_heap;events.clear();allocations.clear();cstring_events.clear();original_created=False
    original=m.call(0x4d17e0,loader,packed(record))
    assert original==result,(label,'return',original,result)
    assert events==expected_events,(label,'ordered dependencies',events,expected_events)
    assert m.read_words(actor,128)==list(state.actor),(label,'actor buffer',[(i*4,hex(x),hex(y))for i,(x,y)in enumerate(zip(m.read_words(actor,128),state.actor))if x!=y])
    assert m.read_words(logic,93)==list(state.logic),(label,'logic buffer',[(i*4,hex(x),hex(y))for i,(x,y)in enumerate(zip(m.read_words(logic,93),state.logic))if x!=y])
    assert info.consumed==original and info.created==original_created,(label,'info')
    assert allocations==[0x1b4,0x174],(label,'allocation sizes')
    lengths=struct.unpack_from('<4I',data,4);pos=284;strings=[]
    for n in lengths:strings.append(data[pos:pos+n].split(b'\0',1)[0]);pos+=n
    assert cstring_events==[('create',x)for x in strings]+[('destroy',x)for x in strings[::-1]],(label,'CString lifetime/order')
    assert bytes(u.mem_read(record,len(data)))==data,(label,'record mutation')
    calls+=1

for index in range(1500):
    words=[rng.getrandbits(32)for _ in range(71)]
    words[5]=rng.randrange(24576);words[6]=rng.randrange(6144)
    if index%3==0:
        for start in (19,23,27,31):words[start]=words[start+2]=0
    if index%5==0:words[69]=words[70]=0
    words[8]=0xffffffff if index%2 else rng.getrandbits(32)
    strings=[b'name\0ignored',b'Logic',b'' if index%3 else b'IMAGE_SET',b'' if index%7 else b'SOUND']
    check(make_record(words,strings),('generated',index),rng.randrange(4))
print('PASS 1,500 generated records: full actor/logic buffers and ordered lookup/image/sound/spatial dependencies',flush=True)
words=[0]*71;words[5]=100;words[6]=200;words[8]=0xffffffff
for label,x,y,name,found,callback in [('x negative',-1,200,'Logic',True,1),('x edge',24576,200,'Logic',True,1),
    ('y negative',100,-1,'Logic',True,1),('y edge',100,6144,'Logic',True,1),('empty logic',100,200,'',True,1),
    ('unknown logic',100,200,'Missing',False,1),('zero callback',100,200,'Logic',True,0)]:
    probe=list(words);probe[5]=x;probe[6]=y;check(make_record(probe,['',name,'IMAGE','SOUND']),label,3,callback,found)
print('PASS out-of-world/empty/missing logic skips and zero-callback initialization failure',flush=True)

# Independent raw WWD parsing gives exact object bytes; no reserialization of
# Swift strings or reference gameplay implementation enters these comparisons.
world=a.world.read_bytes()
# Header offsets verified against current format parser: count/planes at732/736.
plane_count,planes_offset=struct.unpack_from('<2I',world,732)
if struct.unpack_from('<I',world,8)[0]&2:world=world[:planes_offset]+zlib.decompress(world[planes_offset:])
logic_counts=collections.Counter();object_count=0
for plane in range(plane_count):
    base=planes_offset+plane*160;count=struct.unpack_from('<I',world,base+128)[0];position=struct.unpack_from('<I',world,base+140)[0]
    for i in range(count):
        lengths=struct.unpack_from('<4I',world,position+4);end=position+284+sum(lengths);data=world[position:end]
        start=284+lengths[0];name=data[start:start+lengths[1]].split(b'\0',1)[0].decode()
        check(data,('actual',plane,i,name),flags=i%4)
        logic_counts[name]+=1;object_count+=1;position=end
assert object_count==1479,(plane_count,planes_offset,object_count)
print(f'PASS all {object_count} raw Level1 records /{len(logic_counts)} logic names with explicit supplied lookup metadata; no object callback execution claimed',flush=True)

for invalid in [b'',make_record(words,['','Logic','',''])[:283],make_record(words,['','Logic','',''])[:-1],packed(*([0,1024]+[0]*69))+b'x'*1024]:
    state=State((C.c_uint32*128)(*([99]*128)),(C.c_uint32*93)(*([77]*93)));c=Context(scene,actor,logic,2,24576,6144,map_object+16,(C.c_uint32*3)(*layers),0,1,0);info=Info(123,456);before=bytes(state);source=(C.c_uint8*len(invalid)).from_buffer_copy(invalid);events.clear()
    assert load(source,len(invalid),C.byref(state),C.byref(c),dependency,None,C.byref(info))==0
    assert bytes(state)==before and (info.consumed,info.created)==(123,456) and events==[]
required={0x4d17e0,0x4c98c0,0x4c9d40,0x4c81f0,0x4c7df0,0x4d5800,0x4c8160,0x4d51a0}
assert required<=m.executed
adapters={0x4f63ec,0x4f65f2,0x4f6584,0x4f6286,0x4c7970,0x4c7900,0x4c79e0,0x4c7a40,0x4c9be0,0x4f4630,m.stop}
print(f'PASS {calls} full original4d17e0 calls /{len(m.executed-adapters)} original instruction addresses, complete preserved buffers and native malformed-input atomic rejection',flush=True)
