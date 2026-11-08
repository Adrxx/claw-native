"""Hash-pinned whole source stack lifecycle oracle; physical callbacks explicit."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/stacked-actor-lifecycle-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/StackedActorLifecycleRuntime.cpp'),str(ROOT/'Sources/ActorDestruction.cpp'),'-o',str(WORK/'libStackedActorLifecycle.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,Call);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host),('fault',U)]
class ADGlobals(C.Structure):_fields_=[('holderActorToken',U),('heldActorToken',U),('emptyStringToken',U)]
BASE,SIZE=0x3000000,0x100000;E,L,A,L2,A2,E2=[BASE+i*0x1000 for i in range(1,7)]
F1,F2,F3,CONT=[0x10fc000+i*0x100 for i in range(4)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
for t in(F1,F2,F3,CONT):u.mem_write(t,b'\xc3')
GS,GN=0x520000,0x30000;globalSeed=bytes(u.mem_read(GS,GN))
IS,IE,_=next(x for x in u.mem_regions()if x[0]==0x400000);image=(C.c_uint8*(IE-IS+1)).from_buffer_copy(bytes(u.mem_read(IS,IE-IS+1)))
heap=(C.c_uint8*SIZE)();rng=random.Random(0x4041b0);ctx=Context();lib=C.CDLL(str(WORK/'libStackedActorLifecycle.dylib'))
lib.claw_stacked_actor_lifecycle_entry.argtypes=[U,U,UP,U,C.POINTER(Context),UP];lib.claw_stacked_actor_lifecycle_entry.restype=U
lib.claw_actor_destruction_entry.argtypes=[U,U,U,C.POINTER(ADGlobals),Host,UP,UP];lib.claw_actor_destruction_entry.restype=U
native=True;events=[];live={};regions={};freed=[];policy=0;calls=eventCount=0;errors=[];nestedTarget=0;prefixStop=False;requests=[]
AD={0x4c9be0,0x4c9c00,0x4c99c0,0x4c80c0,0x4c80e0,0x4c8210}

def put(t,v):
 b=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def get(t,n=1):
 if native:
  if BASE<=t and t+n*4<=BASE+SIZE:return list(struct.unpack_from('<'+'I'*n,heap,t-BASE))
  return list(struct.unpack_from('<'+'I'*n,image,t-IS))
 return m.read_words(t,n)
def snapshot():return(hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(globalSeed if native else bytes(u.mem_read(GS,GN))).digest(),tuple(sorted(live.items())),tuple(freed))
@Lookup
def lookup(_,t,n):
 requests.append((t,n))
 if BASE<=t and t+n*4<=BASE+SIZE:
  # Allocations are exact; checking the parent does not assume264-word enemy.
  for start,size in regions.items():
   if start<=t<start+size:
    return C.addressof(heap)+t-BASE if t+n*4<=start+size else None
  return None
 if IS<=t and t+n*4<=IE+1:return C.addressof(image)+t-IS
 return None
@Free
def free(_,t):events.append((0x4f6428,0,(t,),snapshot()));freed.append(t);live[t]=False

def effect(f,t,args):
 if f==0x4a36f0:return 0x51f310
 assert f in(F1,F2,F3),(hex(f),hex(t),args)
 assert not args
 if policy==1 and f==F2:put(t+0x14,[F3]);put(t+0x18,[F1]);put(t+0x1c,[0xabcdef])
 elif policy==2 and f==F2:put(t+0x10,[L2]);put(L2+0x1c,[0x321]);put(t+0x1c,[0x321]);put(t+0x14,[F3])
 elif policy==3 and f==F1:put(t+0x14,[F3]);put(t+0x18,[F3]);put(t+0x1c,[0])
 elif policy==4 and f==F2:put(t+0x14,[0])
 elif policy==5 and f==F2:put(t+0x14,[F2]);put(t+0x18,[F2])
 elif policy==6:put(t+0x48,[get(t+0x48)[0]^f]);put(t+0x1c,[0xffffffff])
 elif policy==7 and f==F2:put(t+0x14,[F3]);put(t+0x18,[F3]);put(t+0x1c,[0x321])
 return 0

def entry(f,t,args=()):
 out=U()
 if f in AD:
  fault=U();ok=lib.claw_actor_destruction_entry(f,t,args[0]if args else 0,C.byref(ADGlobals(0,0,0x52e1c4)),ctx.scene,C.byref(fault),C.byref(out));ctx.fault=fault.value
 else:
  aa=(U*len(args))(*args);ok=lib.claw_stacked_actor_lifecycle_entry(f,t,aa,len(args),C.byref(ctx),C.byref(out))
 return ok,out.value
@Invoke
def invoke(_,ev):
 try:
  args=tuple(ev.arguments[:ev.argumentCount]);f=ev.function;t=ev.receiver
  if f in AD or f==0x484d90:
   ok,out=entry(f,t,args);assert ok,(hex(f),ctx.fault);return out
  events.append((f,t,args,snapshot()));result=effect(f,t,args)
  if f==F2 and nestedTarget:
   ok,_=entry(0x484d90,nestedTarget,[1]);assert ok
  return result
 except BaseException as error:errors.append(error);return 0
ctx.scene=Host(None,lookup,Alloc(),free,invoke,Clock())

def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_EIP,get(sp)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(uc,address,size,_):
 if address==0 and prefixStop:uc.emu_stop();return
 if address not in(F1,F2,F3,0x4f6428,0x4a36f0):return
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f6428:free(None,get(sp+4)[0]);returned(0);return
 args=(get(sp+4)[0],)if address==0x4a36f0 else();receiver=0 if args else t
 events.append((address,receiver,args,snapshot()));result=effect(address,receiver,args)
 if address==F2 and nestedTarget:
  u.mem_write(sp-8,struct.pack('<2I',CONT,1));u.reg_write(UC_X86_REG_ESP,sp-8);u.reg_write(UC_X86_REG_ECX,nestedTarget);u.reg_write(UC_X86_REG_EIP,0x484d90);return
 returned(0,result)
u.hook_add(UC_HOOK_CODE,hook)

def prepare():
 global native,events,live,freed,regions,policy,nestedTarget,prefixStop
 native=True;events=[];freed=[];errors.clear();requests.clear();policy=0;nestedTarget=0;prefixStop=False;ctx.fault=0
 C.memset(C.addressof(heap),0xa5,SIZE);regions={E:76,L:372,A:512,E2:76,L2:372,A2:512};live={t:True for t in regions}
 for t,size in regions.items():put(t,[rng.getrandbits(32)for _ in range(size//4)])
 for t,l,a in[(E,L,A),(E2,L2,A2)]:
  put(t,[0x50f824]);put(t+8,[a,a,l,0,0,1001]);put(l,[0x513740]);put(l+0x10,[0,0,t,1001]);put(a,[0x5137f0]);put(a+0x6c,[l,0]);put(a+0x78,[0])
 u.mem_write(BASE,bytes(heap));u.mem_write(GS,globalSeed)

def compare(f,t,args=(),label=None):
 global native,events,live,freed,calls,eventCount
 native=True;before=bytes(heap);state=(live.copy(),freed[:]);events=[];ok,out=entry(f,t,args);assert ok,(hex(f),label,ctx.fault,errors)
 expected=bytes(heap);ne=events[:];after=(live.copy(),freed[:]);assert not errors,errors
 native=False;u.mem_write(BASE,before);u.mem_write(GS,globalSeed);live,freed=state;events=[]
 try:ret=m.call(f,t,struct.pack('<'+'I'*len(args),*args))
 except BaseException as error:raise AssertionError(('original failure',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events))from error
 assert bytes(u.mem_read(BASE,SIZE))==expected,('heap',hex(f),label)
 assert bytes(u.mem_read(GS,GN))==globalSeed,('globals',hex(f),label)
 assert events==ne and(live,freed)==after,('events/lifetime',hex(f),label,events,ne)
 if f in(0x484d90,0x4bb030,0x4c9be0,0x4c80c0):assert ret==out,('eax',hex(f),label,hex(ret),hex(out))
 native=True;C.memmove(C.addressof(heap),expected,SIZE);calls+=1;eventCount+=len(ne)
 return out
