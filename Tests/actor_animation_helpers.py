"""Actual actor-animation caller graph with full raw-heap/event comparisons."""
import argparse,ctypes as C,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/actor-animation-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');options=p.parse_args()
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp']],'-o',str(WORK/'libActorAnimationRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libActorAnimationRuntime.dylib'))
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('animationDelta',C.c_uint32),('audioPosition',C.c_uint32)]
class Record(C.Structure):_fields_=[(x,C.c_uint32)for x in ['flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event']]
lib.claw_actor_animation_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_actor_animation_entry.restype=C.c_uint32
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(Record),C.POINTER(C.c_uint32)];lib.claw_animation_decode_record.restype=C.c_uint32
m=OriginalV10(options.exe);u=m.u;u.mem_map(0,4096);m.executed.clear()
BASE,SIZE=0x1000000,0x10000;heap=(C.c_uint8*SIZE)();rng=random.Random(0x4c79e0)
A,SC,SEQ,PTRS,RECORDS,IM,IMAGES,NAME,STANDALONE,ALT=[BASE+i*0x1000 for i in range(1,11)]
ANI=A+0x188;DATA=0x1010000
native=True;globals=Globals();events=[];lookupResult=SEQ;policy=0;calls=event_count=decodes=0;decoderMode=False;decodedEvent=0
rates=[0,0x3f800000,0x3f000000,0x40000000,0x3faaaaab,0xbf800000,0x7f800000,0x7fc00000,0x00800000,0x4f000000,0x3f7fffff]
def words(t,n):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=v
 else:m.write_words(t,v)
def snap():return (bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(globals)if native else struct.pack('<2I',m.read_words(0x5430c4,1)[0],m.read_words(0x532c10,1)[0]))
def name(t):
 if native:return bytes(heap[t-BASE:t-BASE+100]).split(b'\0')[0]
 return bytes(u.mem_read(t,100)).split(b'\0')[0]
def effect(fn,receiver,args):
 global globals
 if fn==0x4f6286:
  if policy==1:
   a=words(A,128);a[0x40//4]^=2;a[0x190//4]^=0xfeed;put(A,a)
   if native:globals.animationDelta=81
   else:m.write_words(0x5430c4,[81])
  return lookupResult
 if policy==2:
  # Audio may change its own external globals, not actor/ANI records.
  if native:globals.audioPosition^=1
  else:m.write_words(0x532c10,[m.read_words(0x532c10,1)[0]^1])
 if policy==3:
  a=words(A,128);a[2]^=1;put(A,a)
 return 0
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
@Allocate
def allocate(_,n):raise AssertionError('actor-animation wrappers do not allocate gameplay heap')
@Free
def free(_,t):raise AssertionError('actor-animation wrappers do not free gameplay heap')
@Invoke
def invoke(_,c):
 args=tuple(c.arguments[:c.argumentCount]);ev=(c.function,c.receiver,args,name(args[0])if c.function==0x4f6286 else None);events.append((ev,snap()));return effect(c.function,c.receiver,args)
@Clock
def clock(_):raise AssertionError('actor-animation wrappers do not read OS clocks')
host=Host(None,lookup,allocate,free,invoke,clock)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def original_hook(uc,address,size,user):
 if address not in(0x4f6286,0x4c88e0,0x4208e0):return
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f6286:
  token,out=m.read_words(sp+4,2)
  if decoderMode:m.write_words(out,[decodedEvent]);returned(8,int(bool(decodedEvent)));return
  args=(token,);ev=(address,receiver,args,name(token));events.append((ev,snap()));r=effect(address,receiver,args);m.write_words(out,[r]);returned(8,int(bool(r)));return
 args=tuple(m.read_words(sp+4,4));events.append(((address,receiver,args,None),snap()));returned(16,effect(address,receiver,args))
u.hook_add(UC_HOOK_CODE,original_hook)
def setup(count=4):
 global native,globals,lookupResult,policy
 native=True;heap[:]=rng.randbytes(SIZE);globals=Globals(rng.choice([0,1,16,80,0xffffffff]),rng.getrandbits(32));lookupResult=SEQ;policy=0
 put(A+0xc,[SC]);put(SC+0x28,[BASE+0xb000]);put(SC+0x2c,[BASE+0xc000]);put(SEQ+0xc,[PTRS,count]);put(PTRS,[RECORDS+i*0x40 for i in range(count)])
 put(IM+0x14,[IMAGES]);put(IM+0x64,[1,12]);put(IMAGES,[0]+[0x100d000+i*0x20 if rng.randrange(5)else 0 for i in range(12)])
 put(A+0x170,[IM]);put(A+0x16c,[rng.choice([1,2,11,12,0xffffffff])]);put(A+0x40,[rng.getrandbits(32)]);put(A+0x4c,[rng.getrandbits(32),rng.getrandbits(32)])
 for i in range(count):
  put(RECORDS+i*0x40,[rng.getrandbits(32),rng.getrandbits(32),rng.randrange(9),rng.choice(list(range(10))+[0x10009]),rng.randrange(4),rng.choice([0,1,2,11,12,0xffffffff]),rng.choice([0,1,16,80,0xffffffff]),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),BASE+0xd000 if rng.randrange(3)==0 else 0])
 for state in(ANI,STANDALONE):
  idx=rng.randrange(count);put(state+4,[A,SEQ,RECORDS+idx*0x40,idx,rng.choice([0,0,1,16,0xffffffff]),rng.randrange(2),rng.randrange(2),rng.getrandbits(32),rng.getrandbits(32),rng.choice(rates)])
 heap[NAME-BASE:NAME-BASE+15]=b'LEVEL_RAT_IDLE\0'
def compare(f,t,label,a=0,b=0):
 global native,globals,calls,event_count
 native=True;oldHeap=bytes(heap);oldGlobals=bytes(globals);events.clear();fault=C.c_uint32();result=C.c_uint32()
 rr=lib.claw_actor_animation_entry(f,t,a,b,C.byref(globals),host,C.byref(fault),C.byref(result));assert rr and not fault.value,(label,'native fault',fault.value)
 expected=snap();expectedEvents=list(events);u.mem_write(BASE,oldHeap);m.write_words(0,[0x12345678]);m.write_words(0x5430c4,[struct.unpack_from('<I',oldGlobals,0)[0]]);m.write_words(0x532c10,[struct.unpack_from('<I',oldGlobals,4)[0]]);native=False;events.clear()
 args=struct.pack('<2I',a,b)if f in(0x4c79e0,0x420a10)else struct.pack('<I',a)if f in(0x4c7a40,0x4c8220,0x4c8260,0x4c82a0,0x420970)else b''
 try:ret=m.call(f,t,args)
 except Exception:print('original fault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 if snap()!=expected:
  actual=snap()
  for i in range(0,len(actual),4):
   x,y=struct.unpack_from('<I',actual,i)[0],struct.unpack_from('<I',expected,i)[0]
   if x!=y:print(label,hex(i),hex(x),hex(y))
  raise AssertionError((label,'full actor/animation/record/image/guard buffers'))
 if f in(0x4c79e0,0x4c7a40,0x4c82a0,0x4c8210):assert ret==result.value,(label,'meaningful EAX',hex(ret),hex(result.value))
 if events!=expectedEvents:
  print(label,'original',[e for e,s in events]);print('native',[e for e,s in expectedEvents]);
  for i,(x,y)in enumerate(zip(events,expectedEvents)):
   if x!=y:print('boundary mismatch',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError((label,'ordered full buffer events'))
 assert m.read_words(0,1)==[0x12345678]
 native=True;calls+=1;event_count+=len(events)
def decode(data,event,index):
 global native,decoderMode,decodedEvent,decodes
 native=True;record=Record();length=C.c_uint32();buf=(C.c_uint8*len(data)).from_buffer_copy(data);used=lib.claw_animation_decode_record(buf,len(data),event,C.byref(record),C.byref(length));assert used
 token=RECORDS+index*0x40;seed=words(token,12);u.mem_write(DATA,data);m.write_words(token,seed);decoderMode=True;decodedEvent=event
 try:m.call(0x4d76e0,token,struct.pack('<2I',BASE+0xb000,DATA))
 finally:decoderMode=False
 raw=m.read_words(token,12);vals=[record.flags]+[getattr(record,k)for k,_ in Record._fields_[1:-1]]+[record.event]
 assert vals==[raw[1]&0xffff]+raw[2:10]+[raw[11]];assert used==20+m.read_words(0x543174,1)[0]
 put(token,raw);decodes+=1;return used
