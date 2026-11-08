#!/usr/bin/env python3
"""Run the original v1.0 updater and all its math/image/record helpers.
Only the two external sound dispatch routines are stubbed; their calls are checked.
"""
import argparse,ctypes,hashlib,random,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('exe',type=Path);p.add_argument('library',type=Path);p.add_argument('--cases',type=int,default=5000);p.add_argument('--assets',type=Path);a=p.parse_args()
b=a.exe.read_bytes();assert hashlib.sha256(b).hexdigest()=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
pe=struct.unpack_from('<I',b,60)[0];n=struct.unpack_from('<H',b,pe+6)[0];opt=struct.unpack_from('<H',b,pe+20)[0]
base,size=struct.unpack_from('<I',b,pe+52)[0],struct.unpack_from('<I',b,pe+80)[0]
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,(size+4095)&~4095)
for i in range(n):
 o=pe+24+opt+40*i;_,va,rs,ro=struct.unpack_from('<4I',b,o+8)
 if rs:u.mem_write(base+va,b[ro:ro+rs])
u.mem_map(0x1000000,0x20000);u.mem_map(0x2000000,0x10000)
actor,state,seq,records,recordPointers,imageSet,imagePointers=0x1000000,0x1001000,0x1002000,0x1003000,0x1004000,0x1005000,0x1006000
stack,stop=0x2008000,0x200f000
U32=ctypes.c_uint32;I32=ctypes.c_int32
class Record(ctypes.Structure):_fields_=[(x,U32) for x in ['flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event']]
class State(ctypes.Structure):_fields_=[('recordIndex',I32)]+[(x,U32) for x in ['remaining','timed','stopped','code','previousCode']]+[('rate',ctypes.c_float),('hasSequence',U32)]
class Actor(ctypes.Structure):_fields_=[(x,U32) for x in ['imageID','imageToken','flags','x','y','moveX','moveY']]
class Event(ctypes.Structure):_fields_=[(x,U32) for x in ['event','position','spatial','dispatched']]
library=ctypes.CDLL(str(a.library.resolve()));fn=library.claw_animation_update
fn.argtypes=[ctypes.POINTER(State),ctypes.POINTER(Actor),ctypes.POINTER(Record),U32,ctypes.POINTER(U32),I32,I32,U32,U32,ctypes.POINTER(Event)];fn.restype=U32
calls=[];executed=set()
def read(addr,n):return list(struct.unpack('<'+'I'*n,u.mem_read(addr,4*n)))
def w(addr,arr):u.mem_write(addr,struct.pack('<'+'I'*len(arr),*arr))
def hook(uc,address,size,user):
 executed.add(address)
 if address==stop:uc.emu_stop()
 if address in [0x4c88e0,0x4208e0]:
  sp=uc.reg_read(UC_X86_REG_ESP);calls.append((uc.reg_read(UC_X86_REG_ECX),read(sp+4,4),1 if address==0x4c88e0 else 0))
u.hook_add(UC_HOOK_CODE,hook)
# Execute the actual CRT precision initializer, with its unmodified helpers.
# 0x4a5730 calls 0x4a3080 through input pointer 0x52e978; that reaches 0x4a7ef0.
# It changes precision to 53 bits. Round-to-nearest/masked exceptions are the
# harness's initial environment, not evidence from an actual Windows launch.
w(stack,[stop]);u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_FPCW,0x37f)
u.emu_start(0x4a7ef0,stop,count=1000)
originalControlWord=u.reg_read(UC_X86_REG_FPCW)
assert originalControlWord&0x0f3f==0x023f,hex(originalControlWord)
print(f'PASS: original CRT precision initializer executes without stubs; 53-bit precision, control word {originalControlWord:#06x}')
for address in [0x4c88e0,0x4208e0]:u.mem_write(address,b'\xc2\x10\x00')
rng=random.Random(1997)
def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
rates=[0,0x3f800000,0x3f000000,0x40000000,0x3faaaaab,0xbf800000,0x7f800000,0x7fc00000,0x00800000,0x4f000000,0x3f7fffff]
commands=list(range(11))+[0x10000,0x10009,0xffff]
for case in range(a.cases):
 count=rng.randint(1,8);idx=rng.randrange(count);first,last=1,rng.randint(2,120)
 images=[0]+[rng.getrandbits(32) if rng.randrange(6) else 0 for _ in range(last)]
 recs=[]
 for i in range(count):
  eventID=0x100a000+i*0x40 if rng.randrange(4)==0 else 0
  recs.append(Record(rng.getrandbits(4),rng.randrange(9),rng.choice(commands),rng.randrange(5),rng.choice([0,1,first,last,0xffffffff,rng.getrandbits(32)]),rng.choice([0,1,16,80,0xffffffff,rng.getrandbits(32)]),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),eventID))
  r=recs[-1];w(records+i*0x40,[0,r.flags,r.imageCommand,r.controlCommand,r.movementCommand,r.parameter,r.duration,r.code,r.dx,r.dy,0,r.event])
 # Ensure every ordinary command has direct coverage independent of randomness.
 recs[idx].imageCommand=case%9;recs[idx].controlCommand=commands[case%len(commands)];recs[idx].movementCommand=case%5
 r=recs[idx];w(records+idx*0x40,[0,r.flags,r.imageCommand,r.controlCommand,r.movementCommand,r.parameter,r.duration,r.code,r.dx,r.dy,0,r.event])
 rateBits=rates[case%len(rates)] if case<2000 else rng.getrandbits(32);rate=struct.unpack('<f',struct.pack('<I',rateBits))[0]
 s=State(idx,rng.choice([0,0,0,1,16,0xffffffff]),rng.randrange(2),int(case%29==0),rng.getrandbits(32),rng.getrandbits(32),rate,int(case%31!=0))
 act=Actor(rng.choice([first,last,first+1,last-1,0xffffffff,rng.getrandbits(32)]),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32))
 originalActor=[rng.getrandbits(32) for _ in range(128)]
 for off,value in [(0x16c,act.imageID),(0x174,act.imageToken),(0x170,imageSet),(0x40,act.flags),(0x4c,act.x),(0x50,act.y),(0x10,act.moveX),(0x14,act.moveY)]:originalActor[off//4]=value
 originalState=[rng.getrandbits(32) for _ in range(32)]
 for off,value in [(4,actor),(8,seq if s.hasSequence else 0),(12,records+idx*0x40),(16,idx),(20,s.remaining),(24,s.timed),(28,s.stopped),(32,s.code),(36,s.previousCode),(40,bits(s.rate))]:originalState[off//4]=value
 w(actor,originalActor);w(state,originalState);w(seq+12,[recordPointers,count]);w(recordPointers,[records+i*0x40 for i in range(count)])
 w(imageSet+0x14,[imagePointers]);w(imageSet+0x64,[first,last]);w(imagePointers,images)
 delta=rng.choice([0,1,16,80,0xffffffff,rng.getrandbits(32)]);globalPos=rng.getrandbits(32);w(0x532c10,[globalPos]);w(stack,[stop,delta])
 nativeRecords=(Record*count)(*recs);nativeImages=(U32*len(images))(*images);event=Event()
 result=fn(ctypes.byref(s),ctypes.byref(act),nativeRecords,count,nativeImages,first,last,delta,globalPos,ctypes.byref(event))
 u.reg_write(UC_X86_REG_ECX,state);u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_FPCW,originalControlWord);calls.clear()
 u.emu_start(0x4c82a0,stop,count=4000)
 expectedActor=originalActor[:]
 for off,value in [(0x16c,act.imageID),(0x174,act.imageToken),(0x40,act.flags),(0x4c,act.x),(0x50,act.y),(0x10,act.moveX),(0x14,act.moveY)]:expectedActor[off//4]=value
 expectedState=originalState[:]
 for off,value in [(12,records+s.recordIndex*0x40),(16,s.recordIndex&0xffffffff),(20,s.remaining),(24,s.timed),(28,s.stopped),(32,s.code),(36,s.previousCode),(40,bits(s.rate))]:expectedState[off//4]=value
 actualState=read(state,32);actualActor=read(actor,128)
 if actualState!=expectedState or actualActor!=expectedActor or u.reg_read(UC_X86_REG_EAX)!=result:
  print('FAIL',case,'record',{k:getattr(r,k) for k,_ in Record._fields_},'rateBits',hex(rateBits))
  print('state diffs',[(hex(i*4),hex(x),hex(y)) for i,(x,y) in enumerate(zip(actualState,expectedState)) if x!=y])
  print('actor diffs',[(hex(i*4),hex(x),hex(y)) for i,(x,y) in enumerate(zip(actualActor,expectedActor)) if x!=y]);raise AssertionError((case,u.reg_read(UC_X86_REG_EAX),result))
 assert calls==([(event.event,[event.position,0,0,0],event.spatial)] if event.dispatched else []),(case,calls,bytes(event))
print(f'PASS: {a.cases} original v1.0 updater cases, entire actor/state buffers and event dispatch agree')
print('Only audio bodies stubbed; original image helpers, sequence lookup, reset helpers and x87 conversion execute')
print('Original instructions reached:',len(executed))

# Compare native decoding with the original ANI record loader. Registry lookup
# is stubbed, but its exact name bytes and the resolved token are checked.
decoder=library.claw_animation_decode_record
decoder.argtypes=[ctypes.POINTER(ctypes.c_uint8),U32,U32,ctypes.POINTER(Record),ctypes.POINTER(U32)];decoder.restype=U32
fileData,registry=0x1010000,0x1009000
lookupCalls=[];lookupToken=0
def lookup_hook(uc,address,size,user):
 if address==0x4f6286:
  sp=uc.reg_read(UC_X86_REG_ESP);namePtr,out=read(sp+4,2)
  name=bytearray()
  while (value:=uc.mem_read(namePtr+len(name),1)[0]):name.append(value)
  lookupCalls.append((bytes(name),uc.reg_read(UC_X86_REG_ECX)));w(out,[lookupToken])
u.hook_add(UC_HOOK_CODE,lookup_hook)
u.mem_write(0x4f6286,b'\xc2\x08\x00')
def decode_compare(data,token,case):
 global lookupToken
 lookupToken=token
 u.mem_write(fileData,data);before=[rng.getrandbits(32) for _ in range(12)];w(records,before)
 w(stack,[stop,registry,fileData]);u.reg_write(UC_X86_REG_ECX,records);u.reg_write(UC_X86_REG_ESP,stack)
 lookupCalls.clear();u.emu_start(0x4d76e0,stop,count=4000)
 original=read(records,12);extra=read(0x543174,1)[0]
 native=Record();length=U32();buffer=(ctypes.c_uint8*len(data)).from_buffer_copy(data)
 consumed=decoder(buffer,len(data),token,ctypes.byref(native),ctypes.byref(length))
 assert consumed==20+extra,(case,consumed,extra)
 values=[native.flags]+[getattr(native,k) for k,_ in Record._fields_[1:-1]]+[native.event]
 assert values==[original[1]&0xffff]+original[2:10]+[original[11]],(case,values,original)
 assert original[0]==before[0] and original[1]>>16==before[1]>>16 and original[10]>>16==before[10]>>16
 expectedName=data[20:20+extra-1] if extra else None
 assert lookupCalls==([(expectedName,registry+0x10)] if extra else []),(case,lookupCalls,expectedName)
 assert length.value==(extra-1 if extra else 0)
 return native,consumed
for case in range(2000):
 words=[rng.getrandbits(16) for _ in range(10)]
 if case<16:words[0]=case
 name=b'CLAW_EVENT_'+str(case).encode()
 data=struct.pack('<10H',*words)+(name+b'\0' if words[0]&2 else b'')
 decode_compare(data,rng.getrandbits(32),case)
# Bounded rejection is a native safety extension; malformed original files are
# not executed because the original loader reads past their end.
for data in [b'',b'\0'*19,struct.pack('<10H',2,*([0]*9))+b'unterminated']:
 buffer=(ctypes.c_uint8*len(data)).from_buffer_copy(data);record=Record();length=U32()
 assert decoder(buffer,len(data),123,ctypes.byref(record),ctypes.byref(length))==0
print('PASS: 2000 original ANI record decodes; signed fields, flag bits, names and resolved tokens agree')

if a.assets:
 paths=sorted((a.assets/'CLAW/ANIS').glob('*.ANI'))
 imageIDs=[int(path.stem[5:]) for path in (a.assets/'CLAW/IMAGES').glob('FRAME*.PID')]
 first,last=min(imageIDs),max(imageIDs);images=[0]*(last+1)
 for id in imageIDs:images[id]=id+1
 nativeImages=(U32*len(images))(*images);traces=0;decodedCount=0
 for path in paths:
  data=path.read_bytes();signature,unused,flags,count,pathLength=struct.unpack_from('<5I',data)
  assert signature==32 and count>0
  offset=32+pathLength;recs=[]
  for index in range(count):
   record,consumed=decode_compare(data[offset:],index+1,f'{path.name}:{index}')
   recs.append(record);offset+=consumed;decodedCount+=1
  assert offset==len(data),(path,offset,len(data))
  for i,r in enumerate(recs):w(records+i*0x40,[0,r.flags,r.imageCommand,r.controlCommand,r.movementCommand,r.parameter,r.duration,r.code,r.dx,r.dy,0,r.event])
  w(seq+12,[recordPointers,count]);w(recordPointers,[records+i*0x40 for i in range(count)])
  w(imageSet+0x14,[imagePointers]);w(imageSet+0x64,[first,last]);w(imagePointers,images)
  nativeRecords=(Record*count)(*recs)
  for schedule in ([16]*300,[0,1,33,80,500,7,13,200]*40):
   s=State(0,0,0,0,recs[0].code,recs[0].code,1,1);act=Actor(first,images[first],2,689,4723,0,0)
   originalActor=[rng.getrandbits(32) for _ in range(128)]
   for off,value in [(0x16c,act.imageID),(0x174,act.imageToken),(0x170,imageSet),(0x40,act.flags),(0x4c,act.x),(0x50,act.y),(0x10,act.moveX),(0x14,act.moveY)]:originalActor[off//4]=value
   originalState=[rng.getrandbits(32) for _ in range(32)]
   for off,value in [(4,actor),(8,seq),(12,records),(16,0),(20,0),(24,0),(28,0),(32,s.code),(36,s.previousCode),(40,bits(s.rate))]:originalState[off//4]=value
   w(actor,originalActor);w(state,originalState)
   for tick,delta in enumerate(schedule):
    event=Event();result=fn(ctypes.byref(s),ctypes.byref(act),nativeRecords,count,nativeImages,first,last,delta,123,ctypes.byref(event))
    w(0x532c10,[123]);w(stack,[stop,delta]);u.reg_write(UC_X86_REG_ECX,state);u.reg_write(UC_X86_REG_ESP,stack);u.reg_write(UC_X86_REG_FPCW,originalControlWord);calls.clear()
    u.emu_start(0x4c82a0,stop,count=4000)
    for off,value in [(0x16c,act.imageID),(0x174,act.imageToken),(0x40,act.flags),(0x4c,act.x),(0x50,act.y),(0x10,act.moveX),(0x14,act.moveY)]:originalActor[off//4]=value
    for off,value in [(12,records+s.recordIndex*0x40),(16,s.recordIndex&0xffffffff),(20,s.remaining),(24,s.timed),(28,s.stopped),(32,s.code),(36,s.previousCode),(40,bits(s.rate))]:originalState[off//4]=value
    assert read(actor,128)==originalActor and read(state,32)==originalState and u.reg_read(UC_X86_REG_EAX)==result,(path.name,tick,delta)
    assert calls==([(event.event,[event.position,0,0,0],event.spatial)] if event.dispatched else []),(path.name,tick,calls)
    traces+=1
 print(f'PASS: {decodedCount} records from {len(paths)} CD-rip ANI files; {traces} chained original updater steps')
 print('Asset version identity and original game scheduling remain unverified; audio/registry bodies are stubbed')
