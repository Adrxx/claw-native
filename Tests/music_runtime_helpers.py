"""Original XMIDI wrapper/controller oracle, explicit DLL/MFC/OS transport."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/music-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',str(ROOT/'Sources/MusicRuntime.cpp'),str(ROOT/'Sources/ActorDestruction.cpp'),str(ROOT/'Sources/SpecialCommandRuntime.cpp'),str(ROOT/'Sources/GameTiming.cpp'),'-o',str(WORK/'libMusicRuntime.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);BytesLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Scene(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('midiDriver',U),('resourceOrdinal',U),('instance',U)]
class Context(C.Structure):_fields_=[('scene',Scene),('lookupBytes',BytesLookup),('globals',C.POINTER(Globals)),('maximumTraversal',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*6),('transport',U),('outputCount',U),('outputs',UP)]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
class Destruction(C.Structure):_fields_=[('holderActorToken',U),('heldActorToken',U),('emptyStringToken',U)]
BASE,SIZE=0x3000000,0x100000;M,R,R2,NAME,KEY,SLOTS=[BASE+i*0x1000 for i in range(1,7)];DATA,CACHE=BASE+0x10000,BASE+0x40000;TEMP=0x99900000;tempWord=U();DRIVER=0x60000000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
IMAGE_START,IMAGE_END,_=next(x for x in u.mem_regions()if x[0]==0x400000);image=(C.c_uint8*(IMAGE_END-IMAGE_START+1)).from_buffer_copy(bytes(u.mem_read(IMAGE_START,IMAGE_END-IMAGE_START+1)))
heap=(C.c_uint8*SIZE)();ctx=Context();g=Globals();ctx.globals=C.pointer(g);native=True;rng=random.Random(0x4b58a0);events=[];freed=[];errors=[];cursor=0x80000;allocCalls=0;failAllocation=None;names={};handles={};nextHandle=0;volume=127;status=4;dllResults={};mutation=0;prefixStop=None;calls=eventCount=0;selectedEntry=0;mapOrder=[];failureLookup=False;assetProfiles=[];extraNative=None;extraSource=None
GS,GN=0x520000,0x30000;seedGlobals=bytes(u.mem_read(GS,GN))
lib=C.CDLL(str(WORK/'libMusicRuntime.dylib'));lib.claw_music_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_music_entry.restype=U
lib.claw_actor_destruction_entry.argtypes=[U,U,U,C.POINTER(Destruction),Scene,UP,UP];lib.claw_actor_destruction_entry.restype=U
COUNTS={0x546e68:0,0x546e6c:2,0x546e70:0,0x546e74:3,0x546e78:1,0x546e7c:1,0x546e80:1,0x546e84:1,0x546e88:2,0x546e8c:1,0x546e90:1,0x546e94:1,0x546e98:3,0x546e9c:1,0x546ac8:3,0x546acc:2,0x546ac4:1,0x546a54:2}
STUBS={0x10fc000+i*16:slot for i,slot in enumerate(COUNTS)}
for address,slot in STUBS.items():u.mem_write(address,b'\xc3');m.write_words(slot,[address])
u.mem_write(0x10fb000,b'\xc3');m.write_words(0x5469e8,[0x10fb000]);seedGlobals=bytes(u.mem_read(GS,GN))

def put(t,v):
 data=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
 else:u.mem_write(t,data)
def putBytes(t,data):
 if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
 else:u.mem_write(t,data)
def get(t,n=1):
 if not native:return m.read_words(t,n)
 if BASE<=t and t+n*4<=BASE+SIZE:return list(struct.unpack_from('<'+'I'*n,heap,t-BASE))
 return list(struct.unpack_from('<'+'I'*n,image,t-IMAGE_START))
def text(t):
 if not t:return b''
 if native:return bytes(heap[t-BASE:t-BASE+4096]).split(b'\0')[0]if BASE<=t<BASE+SIZE else bytes(image[t-IMAGE_START:t-IMAGE_START+4096]).split(b'\0')[0]
 return bytes(u.mem_read(t,4096)).split(b'\0')[0]
def globalBytes():
 if not native:return bytes(u.mem_read(GS,GN))
 buf=bytearray(seedGlobals);struct.pack_into('<3I',buf,0x54131c-GS,g.midiDriver,g.resourceOrdinal,g.instance);return bytes(buf)
def snapshot():return(hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(globalBytes()).digest(),tuple(freed),cursor,allocCalls,tuple(sorted(names.items())),tuple(sorted(handles.items())),nextHandle,volume)
@Lookup
def lookup(_,t,n):
 if t==TEMP and n<=1:return C.addressof(tempWord)
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_START<=t and t+n*4<=IMAGE_END+1:return C.addressof(image)+t-IMAGE_START
 return None
@BytesLookup
def byteLookup(_,t,n):
 if BASE<=t and t+n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_START<=t and t+n<=IMAGE_END+1:return C.addressof(image)+t-IMAGE_START
 return None
@Free
def free(_,t):events.append((0x4f6428,0,(t,),0,(),snapshot()));freed.append(t)
def allocateBody(n):
 global allocCalls,cursor
 index=allocCalls;allocCalls+=1
 if index==failAllocation:return 0
 token=BASE+cursor;cursor+=(n+15)&~15;assert cursor<SIZE;return token
@Allocate
def allocate(_,n):events.append((0x4f63ec,0,(n,),0,(),snapshot()));return allocateBody(n)
ctx.scene=Scene(None,lookup,allocate,free,Invoke(),Clock());ctx.lookupBytes=byteLookup

def currentDriver():return g.midiDriver if native else m.read_words(0x54131c,1)[0]
def setGlobal(offset,value):
 if native:setattr(g,('midiDriver','resourceOrdinal','instance')[offset//4],value&0xffffffff)
 else:m.write_words(0x54131c+offset,[value&0xffffffff])
def effect(f,receiver,args,transport=0,outputs=None):
 global nextHandle,volume
 if f==0x4f62a8:
  name=text(args[0]);slot=names.get(name)
  if slot is None:slot=SLOTS+len(names)*0x100;names[name]=slot;put(receiver+0xc,[len(names)])
  return slot
 if f==0x4f6286:
  value=0 if failureLookup else get(names[text(args[0])])[0]if text(args[0])in names else 0
  if outputs is not None:outputs[0]=value
  if mutation==1:put(M+0x20,[0x56789])
  return int(bool(value))
 if f==0x4f5e1e:
  position=args[0];index=0 if position==0xffffffff else position;ordered=list(names.values());assert index<len(ordered)
  outputs[0]=index+1 if index+1<len(ordered)else 0;outputs[1]=KEY+12;outputs[2]=get(ordered[index])[0];put(KEY,[get(KEY)[0]+1])
  if mutation==7:outputs[0]=position;outputs[2]=0
  return 0
 if f==0x4f61a1:
  names.clear();put(receiver+4,[0]);put(receiver+0xc,[0]);put(receiver+0x10,[0]);put(receiver+0x14,[0]);return 0
 if f==0x4f6584:
  tempWord.value=args[0];fault=U();out=U();assert lib.claw_actor_destruction_entry(f,TEMP,0,C.byref(Destruction(0,0,0x52e1c4)),ctx.scene,C.byref(fault),C.byref(out));assert not fault.value;return 0
 if f==0x4a3920:
  signed=args[2]if args[2]<0x80000000 else args[2]-0x100000000;assert text(args[1])==b'MIDI%i';putBytes(args[0],b'MIDI'+str(signed).encode()+b'\0');return 0
 if f in COUNTS:
  result=dllResults.get(f,0)
  if f==0x546e74:
   value=dllResults.get('driver',DRIVER)
   if outputs is not None:outputs[0]=value
   else:setGlobal(0,value)
  elif f==0x546e9c:
   nextHandle+=1;result=dllResults.get(f,0x70000000+nextHandle*0x100);handles[result]=(0,0,0)
  elif f==0x546e98:result=dllResults.get(f,1);handles[args[0]]=(int(bool(result)),0,args[1])
  elif f==0x546e94:handles.pop(args[0],None)
  elif f==0x546e7c:
   result=dllResults.get(f,handles.get(args[0],(0,2,0))[1]if status is None else status)
   if mutation==2:put(R+0x58,[0])
   if mutation==3:put(R+0x44,[0xffffffff])
  elif f==0x546e6c:volume=args[1]
  elif f==0x546e8c:result=dllResults.get(f,volume)
  elif f==0x546e90:
   old=handles.get(args[0],(1,0,0));handles[args[0]]=(old[0],4,old[2])
   if mutation==4:put(R+0x58,[0x7000ff00])
  elif f==0x546e78:
   old=handles.get(args[0],(1,0,0));handles[args[0]]=(old[0],2,old[2])
   if mutation==5:put(M+0x1c,[R2]);put(M+0x20,[0x9876])
   if mutation==8:put(M+0x1c,[0])
  elif f in(0x546e84,0x546e80):
   old=handles.get(args[0],(1,0,0));handles[args[0]]=(old[0],8 if f==0x546e84 else 4,old[2])
  elif f==0x546e68:handles.clear()
  elif f==0x546ac8:result=dllResults.get(f,0x80001000)
  elif f==0x546acc:result=dllResults.get(f,0x80002000)
  elif f==0x546ac4:result=dllResults.get(f,DATA)
  elif f==0x546a54:result=dllResults.get(f,64)
  if mutation==6 and f==0x546e94:put(R+0x5c,[CACHE+0x100]);put(R+0x58,[0x7000ff00])
  return result
 raise AssertionError(('unrepresented music transport',hex(f),hex(receiver),args,transport))
@Dependency
def dependency(c,ev,_):
 e=ev.contents;args=list(e.arguments[:e.argumentCount]);outs=list(e.outputs[:e.outputCount]);events.append((e.function,e.receiver,tuple(args),e.transport,tuple(outs),snapshot()))
 try:return effect(e.function,e.receiver,args,e.transport,e.outputs)or 0
 except BaseException as error:errors.append(error);return 0

def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(uc,address,size,_):
 global allocCalls,cursor
 if extraSource and extraSource(uc,address,size,_):return
 if address==0x10fb000:
  token=get(u.reg_read(UC_X86_REG_ESP)+4)[0];value=(get(token)[0]-1)&0xffffffff;put(token,[value]);returned(4,value);return
 if address not in STUBS and address not in(0x4f63ec,0x4f6428,0x4f62a8,0x4f6286,0x4f5e1e,0x4f61a1,0x4f6584,0x4a3920):return
 if prefixStop is not None and len(events)>=prefixStop and address==0x4f5e1e:uc.emu_stop();return
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);f=STUBS.get(address,address);transport=0;outs=[]
 if address in STUBS:args=get(sp+4,COUNTS[f]);receiver=0;outs=[currentDriver()]if f==0x546e74 else[]
 elif f==0x4f6286:args=get(sp+4,2);outToken=args.pop();transport=1;outs=get(outToken)
 elif f==0x4f5e1e:
  raw=get(sp+4,3);outs=[get(token)[0]for token in raw];args=[outs[0]];transport=2
 elif f==0x4f6584:args=get(receiver);receiver=0;transport=3
 else:args=get(sp+4,3 if f==0x4a3920 else 1 if f in(0x4f63ec,0x4f6428,0x4f62a8)else 0);receiver=receiver if f in(0x4f62a8,0x4f61a1)else 0
 events.append((f,receiver,tuple(args),transport,tuple(outs),snapshot()))
 if f==0x4f6584:return # Execute actual original CString destructor/free body.
 if f==0x4f63ec:returned(0,allocateBody(args[0]));return
 if f==0x4f6428:freed.append(args[0]);returned(0);return
 result=effect(f,receiver,args,transport,outs)
 if f==0x4f6286:put(outToken,outs)
 if f==0x4f5e1e:
  for token,value in zip(raw,outs):put(token,[value])
 if f==0x546e74:setGlobal(0,outs[0])
 returned(COUNTS[f]*4 if address in STUBS else 8 if f==0x4f6286 else 12 if f==0x4f5e1e else 4 if f==0x4f62a8 else 0,result)
u.hook_add(UC_HOOK_CODE,hook)

def prepare():
 global native,events,freed,errors,cursor,allocCalls,failAllocation,names,handles,nextHandle,volume,status,dllResults,mutation,prefixStop,failureLookup
 native=True;events=[];freed=[];errors=[];cursor=0x80000;allocCalls=0;failAllocation=None;names={};handles={};nextHandle=0;volume=127;status=4;dllResults={};mutation=0;prefixStop=None;failureLookup=False;C.memset(C.addressof(heap),0xa5,SIZE);ctx.maximumTraversal=128;ctx.fault=0;g.midiDriver=DRIVER;g.resourceOrdinal=0;g.instance=0x12340000
 put(M,[0x5105c4,0,17,0,0,0,10,0,0x11111111,0x12340000,1]);put(KEY,[1,6,6]);putBytes(KEY+12,b'shared\0');putBytes(NAME,b'PLAY\0');putBytes(DATA,rng.randbytes(256))
 for t in(R,R2):
  put(t,[rng.getrandbits(32)for _ in range(24)]);put(t,[0x513528]);putBytes(t+4,b'PLAY\0');put(t+0x44,[0,0,0x11111111,100,100,0x70000100,0]);handles[0x70000100]=(1,4,DATA)

MEANINGFUL={0x4b52a0,0x4b53f0,0x4b54a0,0x4b54f0,0x4b5570,0x4b55a0,0x4b55b0,0x4b55d0,0x4b55e0,0x4b5650,0x4b56a0,0x4b56b0,0x4b58a0,0x4b59c0,0x4b5a80,0x4b5ad0,0x4b5b00,0x4b5b40,0x4b5b90,0x4b5bd0}
def compare(f,receiver,args=(),label=None):
 global native,events,freed,cursor,allocCalls,names,handles,nextHandle,volume,calls,eventCount,selectedEntry
 native=True;selectedEntry=f;old=bytes(heap);og=globalBytes();state=(freed[:],cursor,allocCalls,names.copy(),handles.copy(),nextHandle,volume);events=[];out=U();aa=(U*len(args))(*args);ok=extraNative(f,receiver,args,out)if extraNative and f in(0x42d420,0x42d440)else lib.claw_music_entry(f,receiver,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,(hex(f),label,ok,ctx.fault,errors);expected=bytes(heap);eg=globalBytes();ne=events[:];after=(freed[:],cursor,allocCalls,names.copy(),handles.copy(),nextHandle,volume)
 native=False;u.mem_write(BASE,old);u.mem_write(GS,og);freed,cursor,allocCalls,names,handles,nextHandle,volume=state;events=[]
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
 except Exception as error:raise AssertionError(('original',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events[-2:]))from error
 actual=bytes(u.mem_read(BASE,SIZE));ag=globalBytes();assert actual==expected,('heap',hex(f),label,[(hex(BASE+i),expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=actual[i:i+4]][:15]);assert ag==eg,('globals',hex(f),label,[(hex(GS+i),eg[i:i+4].hex(),ag[i:i+4].hex())for i in range(0,GN,4)if eg[i:i+4]!=ag[i:i+4]][:12]);assert events==ne,('events',hex(f),label,[(hex(e[0]),hex(e[1]),e[2:5])for e in ne],[(hex(e[0]),hex(e[1]),e[2:5])for e in events]);assert(freed,cursor,allocCalls,names,handles,nextHandle,volume)==after
 if f in MEANINGFUL:assert ret==out.value,('EAX',hex(f),label,ret,out.value)
 native=True;C.memmove(C.addressof(heap),actual,SIZE);g.midiDriver,g.resourceOrdinal,g.instance=struct.unpack_from('<3I',ag,0x54131c-GS);calls+=1;eventCount+=len(ne);return out.value

def installAsset(file):
 data=file.read_bytes();assert len(data)<0x30000;putBytes(DATA,data);assetProfiles.append({'path':str(file.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()});return len(data)
