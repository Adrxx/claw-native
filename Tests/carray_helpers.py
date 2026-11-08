"""Original-instruction CArray oracle, with physical allocator boundaries explicit."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/carray-agent';WORK.mkdir(exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/CArrayRuntime.cpp'),'-o',str(WORK/'libCArrayRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_uint32)for n in('composeAllocator','globalNewHandler','fault','crtNewMode','smallBlockThreshold','heapHandle','heapAllocFunction')]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x600000
ARRAY,MODULE,DATA=BASE+0x1000,BASE+0x2000,BASE+0x4000
HANDLER,HEAP_ALLOC=0x10fd000,0x10fe000
GLOBALS=[0x510020,0x540fe8,0x5312d4,0x545fc4,0x546960]
heap=(C.c_uint8*SIZE)();context=Context();cursor=0x20000;policy=0;mallocFailures=0;smallFailures=0;handlerResult=1;allocationCalls=0;currentArray=ARRAY;original_events=[];native_events=[];errors=[];calls=events=0;unsafe=False
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
lib=C.CDLL(str(WORK/'libCArrayRuntime.dylib'));lib.claw_carray_entry.argtypes=[C.c_uint32]*5+[C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_carray_entry.restype=C.c_uint32;lib.claw_carray_defaults.argtypes=[C.POINTER(Context)]
def get(t,n=1,native=True):return list(struct.unpack_from('<'+'I'*n,bytes(heap),t-BASE))if native else m.read_words(t,n)
def write(t,b,native=True):
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def put(t,values,native=True):write(t,struct.pack('<'+'I'*len(values),*(x&0xffffffff for x in values)),native)
def snapshot(native):
 return (hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),tuple(getattr(context,n)for n in('globalNewHandler','crtNewMode','smallBlockThreshold','heapHandle','heapAllocFunction'))if native else tuple(m.read_words(a,1)[0]for a in GLOBALS))
@Lookup
def lookup(user,t,n):return C.addressof(heap)+t-BASE if t%4==0 and BASE<=t and t+4*n<=BASE+SIZE else None
def allocate_raw(n):
 global cursor
 if n>SIZE//2:return 0
 token=BASE+cursor;cursor+=max(16,(n+15)&~15);assert cursor<=SIZE;return token
def effect(event,native):
 global mallocFailures,smallFailures,allocationCalls
 f,receiver,args=event
 if f in(0x4f63ec,0x4a48e0,HEAP_ALLOC,0x4ab4c0):
  allocationCalls+=1
  if f==0x4ab4c0 and smallFailures:smallFailures-=1;return 0
  if mallocFailures:mallocFailures-=1;return 0
  if policy==2 and currentArray:
   size=get(currentArray+8,native=native)[0]
   if size>2:put(currentArray+8,[2],native)
   put(currentArray+0x10,[17],native)
  n=args[0]*16 if f==0x4ab4c0 else args[2]if f==HEAP_ALLOC else args[0]
  return allocate_raw(n)
 if f in(0x4f6428,0x4a49b0):
  if args[0]:put(args[0],[0xdeaddead],native)
  if policy==2 and currentArray:put(currentArray+0x10,[7],native)
  return 0x12345678
 if f==0x5022b5:return MODULE
 if f in(HANDLER,0x4ad350):
  if policy==4:
   if native:context.globalNewHandler=HANDLER
   else:m.write_words(0x510020,[HANDLER])
  return handlerResult
 if f in(0x4a7bc0,0x4a7c40):return 0x99887766
 raise AssertionError(('Unrepresented service',event))
@Dependency
def dependency(ctx,e,user):
 try:
  e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]));native_events.append((event,snapshot(True)));return effect(event,True)
 except BaseException as exc:errors.append(exc);return 0
@Allocate
def allocate(user,n):native_events.append(((0x4f63ec,0,(n,)),snapshot(True)));return effect((0x4f63ec,0,(n,)),True)
@Free
def free(user,t):raise AssertionError('Unexpected direct scene.free')
@Invoke
def invoke(user,e):
 event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]));native_events.append((event,snapshot(True)));return effect(event,True)
@Clock
def clock(user):return 0
context.scene=Host(None,lookup,allocate,free,invoke,clock)
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 if address in(0x4f63ec,0x4f6428)and context.composeAllocator:return
 if address==0x4a48e0 and context.composeAllocator!=1:return
 if address not in(0x4f63ec,0x4f6428,0x4a48e0,0x4a49b0,0x5022b5,HANDLER,0x4ad350,0x4a7bc0,0x4a7c40,0x4ab4c0,HEAP_ALLOC):return
 n=0 if address==0x5022b5 else 3 if address==HEAP_ALLOC else 1;sp=u.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,n));event=(address,0,args);original_events.append((event,snapshot(False)));value=effect(event,False);returned(12 if address==HEAP_ALLOC else 0,value)
u.hook_add(UC_HOOK_CODE,hook)
class UnsafeOriginal(Exception):pass
def memory_hook(uc,access,address,size,value,user):
 if unsafe and address<0x1000:raise UnsafeOriginal((address,size,hex(u.reg_read(UC_X86_REG_EIP))))
u.hook_add(UC_HOOK_MEM_WRITE,memory_hook)
def prepare(seed=0):
 global cursor,policy,mallocFailures,smallFailures,handlerResult,allocationCalls,currentArray,unsafe
 rng=random.Random(seed);write(BASE,rng.randbytes(SIZE));cursor=0x20000;policy=mallocFailures=smallFailures=allocationCalls=0;handlerResult=1;currentArray=ARRAY;unsafe=False
 context.composeAllocator=0;context.fault=0;lib.claw_carray_defaults(C.byref(context));context.heapHandle=0xabcddcba;context.heapAllocFunction=HEAP_ALLOC;put(MODULE+0x28,[HANDLER]);put(ARRAY,[0x5108fc,DATA,4,8,0])
def native_entry(f,receiver,args):
 result=C.c_uint32();values=list(args)+[0]*(3-len(args));assert lib.claw_carray_entry(f,receiver,*values,C.byref(context),dependency,None,C.byref(result))==1;assert not errors;return result.value
def compare(f,receiver,label,args=(),expect_fault=0):
 global cursor,mallocFailures,smallFailures,handlerResult,allocationCalls,calls,events,unsafe
 before=bytes(heap);before_globals=snapshot(True)[1];old=(cursor,mallocFailures,smallFailures,allocationCalls);native_events.clear();original_events.clear();errors.clear();context.fault=0
 result=native_entry(f,receiver,args);assert context.fault==expect_fault,(label,context.fault,expect_fault,errors)
 expected=bytes(heap);expected_globals=snapshot(True)[1];next_state=(cursor,mallocFailures,smallFailures,allocationCalls);expected_events=list(native_events)
 u.mem_write(BASE,before);m.write_words(0,[0x12345678])
 for a,v in zip(GLOBALS,before_globals):m.write_words(a,[v])
 cursor,mallocFailures,smallFailures,allocationCalls=old
 sp=m.stack;packed=list(args);u.mem_write(sp,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(packed),*(x&0xffffffff for x in packed)));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,receiver);unsafe=bool(expect_fault)
 faulted=False
 try:u.emu_start(f,m.stop,count=3000000)
 except UnsafeOriginal:faulted=True
 unsafe=False
 assert faulted==bool(expect_fault),(label,'original unsafe access witness',faulted)
 if not faulted:
  assert u.reg_read(UC_X86_REG_EIP)==m.stop,(label,'original instruction bound')
  cleanup=8 if f in(0x4f582f,0x4f5915)else 12 if f in(0x4d03b0,0x4d0450,0x4cb7b0)else 0
  assert u.reg_read(UC_X86_REG_ESP)==sp+4+cleanup,(label,'callee stack cleanup')
  assert u.reg_read(UC_X86_REG_EAX)==result,(label,'machine eax',u.reg_read(UC_X86_REG_EAX),result)
 actual=bytes(u.mem_read(BASE,SIZE))
 if actual!=expected:
  diffs=[(i,expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if actual[i:i+4]!=expected[i:i+4]];print('DIFF',label,diffs[:20]);raise AssertionError((label,'complete heap'))
 assert snapshot(False)[1]==expected_globals and original_events==expected_events,(label,'globals/ordered complete callbacks')
 if not faulted:assert m.read_words(0,1)==[0x12345678]
 assert (cursor,mallocFailures,smallFailures,allocationCalls)==next_state
 calls+=1;events+=len(expected_events);return result

def plane_composition():
 """Compose frozen plane bodies with actual CArray bodies, no array shim."""
 global native_entry,currentArray,cursor
 from world_plane_assets import worlds
 bridge_source=r'''
#include "CArrayRuntime.h"
#include "WorldPlaneRuntime.h"
struct Bridge {ClawCArrayContext* array;ClawCArrayDependency arrayDependency;
 ClawWorldPlaneDependency other;void* user;};
static uint32_t dependency(ClawWorldPlaneContext* c,const ClawWorldPlaneCall* e,void* user){
 auto* b=static_cast<Bridge*>(user);
 if(e->function==0x4f582f){uint32_t result=0;
  claw_carray_entry(0x4f582f,e->receiver,e->arguments[0],e->arguments[1],0,
   b->array,b->arrayDependency,b->user,&result);c->fault=b->array->fault;return result;}
 return b->other(c,e,b->user);
}
extern "C" uint32_t carray_test_world_add(uint32_t w,uint32_t r,uint32_t base,
 ClawWorldPlaneContext* plane,ClawCArrayContext* array,ClawCArrayDependency a,
 ClawWorldPlaneDependency other,void* user){
 Bridge b{array,a,other,user};return claw_world_plane_add(w,r,base,0,plane,dependency,&b);
}
'''
 (WORK/'plane-bridge.cpp').write_text(bridge_source)
 subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib','-I'+str(ROOT/'Sources'),str(WORK/'plane-bridge.cpp'),*[str(ROOT/'Sources'/x)for x in('CArrayRuntime.cpp','WorldPlaneRuntime.cpp','SceneCameraRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp')],'-o',str(WORK/'libCArrayPlane.dylib')],check=True)
 class PlaneContext(C.Structure):_fields_=[('scene',Host),('fault',C.c_uint32)]
 class PlaneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p)]
 PlaneDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(PlaneContext),C.POINTER(PlaneCall),C.c_void_p)
 SCENE,WORLD,IR,RESOURCE,IMAGES,IMAGE=BASE+0x3000,BASE+0x4000,BASE+0x5000,BASE+0x6000,BASE+0x7000,BASE+0x8000
 RAW=BASE+0x100000;COPYRECT=0x10fc000;planeContext=PlaneContext(context.scene,0)
 def other_effect(e,native):
  f,receiver,args=e
  if f==0x4f6286:return RESOURCE
  if f==0x4d1620:put(receiver+0xb0,[BASE+0xa000],native);return 1
  if f==0x4d2210:put(receiver+8,[get(receiver+8,native=native)[0]|0x10000],native);return 0
  raise AssertionError(e)
 @PlaneDependency
 def other(ctx,p,user):
  try:
   p=p.contents;args=(p.name,)if p.function==0x4f6286 else tuple(p.arguments[:p.argumentCount]);e=(p.function,p.receiver,args);native_events.append((e,snapshot(True)));return other_effect(e,True)
  except BaseException as exc:errors.append(exc);return 0
 joined=C.CDLL(str(WORK/'libCArrayPlane.dylib'));joined.carray_test_world_add.argtypes=[C.c_uint32]*3+[C.POINTER(PlaneContext),C.POINTER(Context),Dependency,PlaneDependency,C.c_void_p];joined.carray_test_world_add.restype=C.c_uint32
 old_native=native_entry
 def native(f,receiver,args):
  if f!=0x4cb7b0:return old_native(f,receiver,args)
  planeContext.fault=0;value=joined.carray_test_world_add(receiver,args[0],args[1],C.byref(planeContext),C.byref(context),dependency,other,None);context.fault=planeContext.fault;return value
 def original_hook(uc,address,size,user):
  if address not in(COPYRECT,0x4f6286,0x4d1620,0x4d2210):return
  sp=u.reg_read(UC_X86_REG_ESP)
  if address==COPYRECT:
   out,inp=m.read_words(sp+4,2);u.mem_write(out,bytes(u.mem_read(inp,16)));returned(8,1);return
  if address==0x4f6286:
   name,out=m.read_words(sp+4,2);text=bytes(u.mem_read(name,128)).split(b'\0',1)[0];e=(address,u.reg_read(UC_X86_REG_ECX),(text,));original_events.append((e,snapshot(False)));v=other_effect(e,False);m.write_words(out,[v]);returned(8,int(bool(v)));return
  n=1 if address==0x4d2210 else 2;e=(address,u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,n)));original_events.append((e,snapshot(False)));returned(n*4,other_effect(e,False))
 handle=u.hook_add(UC_HOOK_CODE,original_hook);m.write_words(0x546d58,[COPYRECT]);native_entry=native
 start_calls,start_events=calls,events;input_worlds=worlds();total_words=0
 try:
  for path,raw,count,start,digest in input_worlds:
   prepare(int(path.split('/')[0][5:]));currentArray=0;cursor=0x400000;put(SCENE+0x10,[IR]);put(WORLD+0xc,[SCENE]);put(WORLD+0x10,[0,0,639,479]);native_entry(0x4f58ab,WORLD+0x34,());put(RESOURCE+0x14,[IMAGES,2]);put(RESOURCE+0x64,[0,1]);put(IMAGES,[IMAGE,0]);put(IMAGE+0x10,[64,64]);write(RAW,raw)
   for index in range(count):
    record=RAW+start+index*160;compare(0x4cb7b0,WORLD,('joined real CArray/world plane',path,index),(record,RAW,WORLD+0x10));words=get(record,40);total_words+=words[24]*words[25]
   assert get(WORLD+0x3c)==[count]
   table=get(WORLD+0x38)[0];assert get(table,count)[get(WORLD+0x60)[0]]==get(WORLD+0x5c)[0]
 finally:native_entry=old_native;u.hook_del(handle)
 report={'joinedOriginalPlaneAdds':calls-start_calls,'joinedCompleteSnapshots':events-start_events,'actualWorlds':len(input_worlds),'tileWords':total_words,'scope':'Retained real4cb7b0/4d0450/4f582f/4f5915/4d0a60; logical allocator, image lookup, grid/object initialization and CopyRect explicit.'}
 (WORK/'plane-composition-proof.json').write_text(json.dumps(report,indent=2)+'\n');return report

def host_fallback():
 """Verify the shared raw SceneActorHost.call ABI without a rich callback."""
 global native_entry
 old=native_entry;null=Dependency()
 def native(f,receiver,args):
  result=C.c_uint32();padded=list(args)+[0]*(3-len(args));assert lib.claw_carray_entry(f,receiver,*padded,C.byref(context),null,None,C.byref(result))==1;return result.value
 start_calls,start_events=calls,events;native_entry=native
 try:
  prepare();compare(0x4f58ab,ARRAY,'scene.call constructor');compare(0x4f582f,ARRAY,'scene.call first allocation',(0,999));compare(0x4f582f,ARRAY,'scene.call grow/copy/free',(14,333));compare(0x4f5915,ARRAY,'scene.call release',(0,0xffffffff))
 finally:native_entry=old
 report={'completeOperations':calls-start_calls,'orderedCompleteSnapshots':events-start_events,'scope':'Original raw SceneActorHost.call fallback without a rich dependency.'}
 (WORK/'host-fallback-proof.json').write_text(json.dumps(report,indent=2)+'\n');return report
