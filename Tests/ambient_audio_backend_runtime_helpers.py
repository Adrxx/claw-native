"""Private source ambient backend oracle; only physical COM/clock/heap seams adapt."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/ambient-audio-backend-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/AmbientAudioBackendRuntime.cpp'),*[str(ROOT/'Sources'/s)for s in('SoundTriggerLogicRuntime.cpp','EnemySpeechRuntime.cpp','SpeechActor.cpp','AudioEvents.cpp','ActorResourceBindings.cpp','ActorDestruction.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp')],'-o',str(WORK/'libAmbientAudioBackendRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host),('maximumTraversal',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6),('bufferMethod',C.c_uint32),('outputWord',C.POINTER(C.c_uint32))]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(WORK/'libAmbientAudioBackendRuntime.dylib'));lib.claw_ambient_audio_backend_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_ambient_audio_backend_entry.restype=C.c_uint32
lib.claw_audio_volume_table.argtypes=[C.c_uint32];lib.claw_audio_volume_table.restype=C.c_int32
BASE,SIZE=0x3000000,0x30000
VOICE,VOICE2,MANAGER,BUFFER,BUFFER2,VT,LIST,CONTROL,CONTROL2=[BASE+0x1000+i*0x1000 for i in range(9)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
CLOCK=0x10ffe00;m.write_words(0x546df0,[CLOCK]);m.write_words(0x541178,[lib.claw_audio_volume_table(i)for i in range(101)])
imageStart,imageEnd,_=next(v for v in u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(u.mem_read(imageStart,imageEnd-imageStart+1)))
heap=(C.c_uint8*SIZE)();ctx=Context();ctx.maximumTraversal=128
native=True;rng=random.Random(0x4b4d80);events=[];errors=[];cursor=0x10000;freed=[];clockValues=[100];clockIndex=0;failures={};mutation=0;failAlloc=False;calls=eventCount=0;selectedEntry=0
GLOBAL_START,GLOBAL_SIZE=0x520000,0x30000
seedGlobals=bytes(u.mem_read(GLOBAL_START,GLOBAL_SIZE));extraGlobals=None;nativeOverride=None
def put(t,v):
 b=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def get(t,n=1):
 if not native:return m.read_words(t,n)
 if BASE<=t and t+n*4<=BASE+SIZE:return list(struct.unpack_from('<'+'I'*n,heap,t-BASE))
 return list(struct.unpack_from('<'+'I'*n,image,t-imageStart))
def globalBytes():
 if not native:return bytes(u.mem_read(GLOBAL_START,GLOBAL_SIZE))
 b=bytearray(seedGlobals)
 if extraGlobals:extraGlobals(b)
 return bytes(b)
def snapshot():return (hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(globalBytes()).digest(),cursor,tuple(freed),clockIndex)
@Lookup
def lookup(_,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return None

def alloc(n):
 global cursor
 if failAlloc:return 0
 t=BASE+cursor;cursor+=(n+15)&~15;assert cursor<SIZE;return t
@Allocate
def allocate(_,n):events.append((0x4f63ec,0,(n,),0,None,snapshot()));return alloc(n)
@Free
def free(_,t):events.append((0x4f6428,0,(t,),0,None,snapshot()));freed.append(t)
ctx.scene=Host(None,lookup,allocate,free,Invoke(),Clock())
METHODS={0x10ff000+off:off for off in(0x18,0x24,0x30,0x3c,0x40,0x44,0x48)}
def effect(fn,args,method,out):
 global clockIndex
 if fn==0x546df0:
  value=clockValues[min(clockIndex,len(clockValues)-1)];clockIndex+=1;return value
 if not method:return 0
 buffer=args[0];error=failures.get(method,0)
 if method in(0x18,0x24):out[0]=get(buffer+(4 if method==0x18 else 16))[0]
 elif not error:
  if method==0x30:put(buffer+16,[get(buffer+16)[0]|1])
  elif method==0x48:put(buffer+16,[get(buffer+16)[0]&~1])
  else:put(buffer+{0x3c:4,0x40:8,0x44:12}[method],[args[1]])
 if mutation==1 and method==0x3c:put(VOICE+0x14,[get(VOICE+0x14)[0]^0x200]);put(VOICE+0x18,[11025])
 if mutation==2 and method==0x3c:put(MANAGER+0x78,[0])
 if mutation==3 and method==0x24:put(VOICE+0xc,[BUFFER2])
 return error
@Dependency
def dependency(c,event,_):
 e=event.contents;args=list(e.arguments[:e.argumentCount]);initial=e.outputWord[0]if e.outputWord else None;events.append((e.function,e.receiver,tuple(args),e.bufferMethod,initial,snapshot()))
 try:return effect(e.function,args,e.bufferMethod,e.outputWord)
 except BaseException as error:errors.append(error);return 0

def returned(pop,value):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(uc,address,size,_):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4f63ec:
  args=get(sp+4);events.append((address,0,tuple(args),0,None,snapshot()));returned(0,alloc(args[0]));return
 if address==0x4f6428:
  t=get(sp+4)[0];events.append((address,0,(t,),0,None,snapshot()));freed.append(t);returned(0,0);return
 if address==CLOCK:events.append((0x546df0,0,(),0,None,snapshot()));returned(0,effect(0x546df0,[],0,None));return
 if address==0x4b4ed0:args=get(sp+4,3);events.append((address,0,tuple(args),0,None,snapshot()));returned(0,0);return
 if address not in METHODS:return
 method=METHODS[address];count=2 if method in(0x18,0x24,0x3c,0x40,0x44)else 4 if method==0x30 else 1;args=get(sp+4,count);out=(C.c_uint32*1)(*get(args[1]))if method in(0x18,0x24)else None
 logical=args[:1]if out is not None else args;events.append((address,0,tuple(logical),method,out[0]if out is not None else None,snapshot()));value=effect(address,logical,method,out)
 if out is not None:put(args[1],[out[0]])
 returned(count*4,value)
u.hook_add(UC_HOOK_CODE,hook)

def prepare():
 global native,cursor,freed,clockValues,clockIndex,failures,mutation,failAlloc
 native=True;cursor=0x10000;freed=[];clockValues=[100];clockIndex=0;failures={};mutation=0;failAlloc=False;ctx.fault=0;C.memset(C.addressof(heap),0xa5,SIZE)
 for token,n in((VOICE,14),(VOICE2,14),(MANAGER,32),(BUFFER,20),(BUFFER2,20),(LIST,7),(CONTROL,10),(CONTROL2,10)):put(token,[rng.getrandbits(32)for _ in range(n)])
 put(VOICE+0xc,[BUFFER,MANAGER,0x20,22050]);put(VOICE2+0xc,[BUFFER2,MANAGER,0x20,22050]);put(MANAGER+0xc,[0,0]);put(MANAGER+0x78,[1,0]);put(BUFFER,[VT,0,0,22050,1]);put(BUFFER2,[VT,0,0,22050,1]);put(VT,[0]*20)
 for fn,method in METHODS.items():put(VT+method,[fn])
 put(LIST,[0x50babc,0,0,0,0,0,10]);put(CONTROL,[0x513520,0,0,1,VOICE,0,0,100,1000,100]);put(CONTROL2,[0x513520,0,0,1,VOICE2,1,0,100,1000,100]);u.mem_write(BASE,bytes(heap));u.mem_write(GLOBAL_START,seedGlobals)

def compare(fn,args=(),receiver=0,label=None,void=False):
 global native,events,cursor,freed,clockIndex,calls,eventCount,selectedEntry
 native=True;before=bytes(heap);beforeGlobals=globalBytes();old=(cursor,freed[:],clockIndex);events=[];out=C.c_uint32();aa=(C.c_uint32*len(args))(*args);selectedEntry=fn;ok=nativeOverride(fn,receiver,args,out)if nativeOverride else lib.claw_ambient_audio_backend_entry(fn,receiver,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,('native',label,hex(fn),ok,ctx.fault,errors)
 expected=bytes(heap);expectedGlobals=globalBytes();ne=list(events);after=(cursor,freed[:],clockIndex);native=False;u.mem_write(BASE,before);u.mem_write(GLOBAL_START,beforeGlobals);cursor,freed,clockIndex=old;events=[]
 try:ret=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*(a&0xffffffff for a in args)))
 except BaseException as error:raise AssertionError(('original',label,hex(fn),hex(u.reg_read(UC_X86_REG_EIP)),events[-3:]))from error
 actual=bytes(u.mem_read(BASE,SIZE));assert actual==expected,('heap',label,hex(fn),[(hex(BASE+i),expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=actual[i:i+4]][:20]);assert events==ne,('events',label,hex(fn),[(hex(x[0]),x[2],x[3],x[4])for x in ne],[(hex(x[0]),x[2],x[3],x[4])for x in events]);assert (cursor,freed,clockIndex)==after
 assert bytes(u.mem_read(GLOBAL_START,GLOBAL_SIZE))==expectedGlobals,('globals',label,hex(fn))
 if not void:assert ret==out.value,('EAX',label,hex(fn),hex(ret),hex(out.value))
 native=True;C.memmove(C.addressof(heap),actual,SIZE);calls+=1;eventCount+=len(ne);return out.value
