"""Owned whole-original CRT RNG/TLS oracle with explicit Windows transport."""
import ctypes as C,hashlib,json,random,struct,subprocess,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/crt-random-agent'
sources=['CRTRandomRuntime','WorldLootRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in sources],'-o',str(WORK/'libCRTRandomRuntime.dylib')],check=True)
U=C.c_uint32
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('user',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('tlsIndex',U)]
class Context(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(Globals)),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*2)]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x10000;OS,A,B,CUSTOM=BASE+0x1000,BASE+0x2000,BASE+0x3000,BASE+0x4000
GLOBAL_START,GLOBAL_SIZE=0x520000,0x30000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.executed.clear();heap=(C.c_uint8*SIZE)();g=Globals();context=Context();context.globals=C.pointer(g)
lib=C.CDLL(str(WORK/'libCRTRandomRuntime.dylib'));lib.claw_crt_random_entry.argtypes=[U,C.POINTER(U),U,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(U)];lib.claw_crt_random_defaults.argtypes=[C.POINTER(Globals)];lib.claw_world_loot_next_random.argtypes=[C.POINTER(U)];lib.claw_world_loot_next_random.restype=U
rng=random.Random(0x4a3050);native_events=[];original_events=[];errors=[];tape=[];replay=io.BytesIO();replayCases=0;calls=eventCount=0;mutation=0;fatalStop=False;stopped=False
COUNTS={0x546b0c:0,0x546a7c:1,0x546a84:2,0x5469c0:0,0x546ab8:1,0x546a90:0,0x4adf50:2,0x4a49b0:1,0x4a7b90:0,0x4a4860:1}
# Synthetic executable gates resolve exact source IAT slots; no source bytes patched.
GATES={0x1100000+i*16:t for i,t in enumerate(x for x in COUNTS if x>=0x540000)}
m.u.mem_map(0x1100000,4096)
for gate,slot in GATES.items():m.write_words(slot,[gate])
GLOBAL_SEED=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(C.addressof(heap)+t-BASE,n*4)))if native else m.read_words(t,n)
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:m.u.mem_write(t,b)
def raw(native):return bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))
def globalsRaw(native):
 if not native:return bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
 b=bytearray(GLOBAL_SEED);b[0x52edd8-GLOBAL_START:0x52eddc-GLOBAL_START]=pack(g.tlsIndex);return bytes(b)
def snapshot(native):return raw(native),globalsRaw(native)
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if t%4==0 and BASE<=t and t+n*4<=BASE+SIZE else None
context.host=Host(None,lookup,Allocate(),Free(),Invoke(),Clock())
def setIndex(value,native):
 if native:g.tlsIndex=value
 else:m.write_words(0x52edd8,[value])
def transport(fn,args,native):
 # OS words: LastError,currentThread(1/2),TlsAllocResult,TlsSetResult,
 # callocResult,tlsValue1,tlsValue2,freeCount,freeLog[...].
 if mutation and fn in(0x546b0c,0x546a7c,0x4adf50,0x4a49b0):
  index=g.tlsIndex if native else m.read_words(0x52edd8,1)[0];setIndex(index+1,native)
 if fn==0x546b0c:return get(OS,native=native)[0]
 if fn==0x546a7c:
  thread=get(OS+4,native=native)[0];value=get(OS+20+(thread-1)*4,native=native)[0];put(OS,[0x7000+thread],native);return value
 if fn==0x546a84:
  thread=get(OS+4,native=native)[0];ok=get(OS+12,native=native)[0]
  if ok:put(OS+20+(thread-1)*4,[args[1]],native)
  put(OS,[0x8000+thread],native);return ok
 if fn==0x5469c0:return get(OS+4,native=native)[0]*0x11111111
 if fn==0x546ab8:put(OS,[args[0]],native);return 0x1234abcd # void return: caller overwrites it or exposes incidentalEAX
 if fn==0x546a90:put(OS,[0x9000],native);return get(OS+8,native=native)[0]
 if fn==0x4adf50:
  assert args==[1,0x74];value=get(OS+16,native=native)[0]
  if value:
   if native:C.memset(C.addressof(heap)+value-BASE,0,0x74)
   else:m.u.mem_write(value,bytes(0x74))
  return value
 if fn==0x4a49b0:
  n=get(OS+28,native=native)[0];put(OS+32+n*4,[args[0]],native);put(OS+28,[n+1],native)
  if mutation and args[0]!=A:put(A+0x50,[0x5312e8],native)
  return 0xf0f0f0f0
 if fn==0x4a7b90:return 0x55
 if fn==0x4a4860:
  assert args==[16]
  if fatalStop:
   if native:context.fault=99
   else:
    global stopped
    stopped=True;m.u.emu_stop()
  return 0x66
 raise AssertionError((hex(fn),args))
@Dependency
def dependency(_,e,user):
 ev=e.contents;args=list(ev.arguments[:ev.count]);native_events.append((ev.function,ev.receiver,tuple(args),snapshot(True)));before=bytes(heap)
 try:
  value=transport(ev.function,args,True);after=bytes(heap);patches=[];pos=0
  while pos<SIZE:
   if before[pos]==after[pos]:pos+=1;continue
   begin=pos
   while pos<SIZE and before[pos]!=after[pos]:pos+=1
   patches.append((begin,after[begin:pos]))
  tape.append((ev.function,ev.receiver,args,value,g.tlsIndex,patches));return value
 except BaseException as ex:errors.append(ex);context.fault=98;return 0

def returned(pop,value):
 sp=m.u.reg_read(UC_X86_REG_ESP);address=m.read_words(sp,1)[0];m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_EIP,address);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(u,address,size,user):
 fn=GATES.get(address,address)
 if fn not in COUNTS:return
 args=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,COUNTS[fn]);original_events.append((fn,0,tuple(args),snapshot(False)));value=transport(fn,args,False)
 if not stopped:returned(COUNTS[fn]*4 if fn>=0x540000 else 0,value)
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(seed=0):
 global mutation,fatalStop,stopped
 heap[:]=rng.randbytes(SIZE);g.tlsIndex=7;context.fault=0;mutation=0;fatalStop=stopped=False
 put(OS,[0x12345678,1,7,1,A,A,B,0]+[0]*32);put(A+0x14,[seed]);put(B+0x14,[seed^0x87654321]);put(A+0x50,[0x5312e8]);put(B+0x50,[0x5312e8])
 for t in(A,B):
  for off in(0x24,0x28,0x30,0x38,0x40,0x44):put(t+off,[0])

def sync():m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GLOBAL_START,GLOBAL_SEED);m.write_words(0x52edd8,[g.tlsIndex])
def compare(fn,args=(),label='case',record=False):
 global calls,eventCount,replayCases
 sync();native_events.clear();original_events.clear();errors.clear();tape.clear();context.fault=0;before=bytes(heap);beforeIndex=g.tlsIndex;values=(U*len(args))(*args);result=U(0xabcdef12);done=lib.claw_crt_random_entry(fn,values,len(args),C.byref(context),dependency,None,C.byref(result));assert done==1 and not context.fault and not errors,(label,'native',done,context.fault,errors);afterIndex=g.tlsIndex;g.tlsIndex=beforeIndex;original=m.call(fn,0,pack(*args));g.tlsIndex=afterIndex
 assert result.value==original,(label,'EAX inclvoid incidental',hex(result.value),hex(original))
 assert native_events==original_events,(label,'ordered complete snapshot',[(j,x[:3],y[:3])for j,(x,y)in enumerate(zip(native_events,original_events))if x!=y][:8],len(native_events),len(original_events))
 assert raw(True)==raw(False)and globalsRaw(True)==globalsRaw(False),(label,'complete state',[(hex(BASE+j),v,w)for j,(v,w)in enumerate(zip(raw(True),raw(False)))if v!=w][:12],g.tlsIndex,m.read_words(0x52edd8,1)[0])
 if record or calls%113==0:
  replay.write(pack(fn,len(args),*(list(args)+[0]*(1-len(args))),result.value,beforeIndex,afterIndex,len(tape))+before+bytes(heap))
  for f,t,aa,v,index,patches in tape:
   replay.write(pack(f,t,len(aa),*(aa+[0]*(2-len(aa))),v,index,len(patches)))
   for offset,data in patches:replay.write(pack(offset,len(data))+data)
  replayCases+=1
 calls+=1;eventCount+=len(native_events);return result.value
