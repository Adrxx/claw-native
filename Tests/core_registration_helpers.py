"""Private complete-buffer oracle for original core/bitset lifecycle."""
import ctypes as C,hashlib,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EBP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/core-registration-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/CoreRegistration.cpp'),str(ROOT/'Sources/ActorDestruction.cpp'),'-o',str(WORK/'libCoreRegistration.dylib')],check=True)
BASE,SIZE,GBASE,OBJ,HANDLER,STRING=0x3000000,0x10000,0x544b14,0x3001000,0x3002000,0x3002100
HEAPFREE=0x10ff000
class Globals(C.Structure):_fields_=[('words',C.c_uint32*130)]+[(n,C.c_uint32)for n in('defaultBitCount','errorLocation','heapHandle','heapFreeFunction')]+[('freeScratchTokens',C.c_uint32*2)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class DestructionGlobals(C.Structure):_fields_=[('holderActorToken',C.c_uint32),('heldActorToken',C.c_uint32),('emptyStringToken',C.c_uint32)]
lib=C.CDLL(str(WORK/'libCoreRegistration.dylib'))
lib.claw_core_registration_defaults.argtypes=[C.POINTER(Globals)]
lib.claw_core_registration_initialize.argtypes=[C.POINTER(Globals),Host,C.POINTER(C.c_uint32)];lib.claw_core_registration_initialize.restype=C.c_uint32
lib.claw_core_registration_entry.argtypes=[C.c_uint32]*4+[C.POINTER(Globals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_core_registration_entry.restype=C.c_uint32
lib.claw_actor_destruction_entry.argtypes=[C.c_uint32]*3+[C.POINTER(DestructionGlobals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_actor_destruction_entry.restype=C.c_uint32
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear();rng=random.Random(0x4dc560)
g=Globals();buf=(C.c_uint8*SIZE)();scratch=(C.c_uint32*2)();fault=C.c_uint32();cursor=0x4000;allocation_sizes={};native_events=[];original_events=[];free_list=[];calls=0;events=0;fail_alloc=False;small_block=0;small_values=(0x1234,0x5678);callback_errors=[]
def snapshot(native):
 return (tuple(g.words)if native else tuple(m.read_words(GBASE,130)),g.defaultBitCount if native else m.read_words(0x533470,1)[0],g.heapHandle if native else m.read_words(0x545fc4,1)[0],hashlib.sha256(bytes(buf)if native else bytes(u.mem_read(BASE,SIZE))).digest(),tuple(free_list))
def put(token,values):C.memmove(C.addressof(buf)+token-BASE,struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values)),4*len(values))
def words(token,n):return list(struct.unpack_from('<'+'I'*n,bytes(buf),token-BASE))
@Lookup
def lookup(user,token,n):
 if BASE<=token and token+n*4<=BASE+SIZE:return C.addressof(buf)+token-BASE
 for i,t in enumerate(g.freeScratchTokens):
  if token==t and n==1:return C.addressof(scratch)+i*4
 return None

def alloc(n,native):
 global cursor
 if fail_alloc:return 0
 token=BASE+cursor;cursor+=(n+15)&~15
 if cursor>SIZE:raise AssertionError('owned oracle arena exhausted')
 allocation_sizes[token]=n;return token
@Allocate
def allocate(user,n):
 native_events.append(((0x4a48e0,0,(n,)),snapshot(True)))
 try:return alloc(n,True)
 except BaseException as e:callback_errors.append(e);return 0
@Free
def freed(user,t):free_list.append(t)
@Clock
def clock(user):return 0
@Invoke
def invoke(user,e):
 event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]));native_events.append((event,snapshot(True)))
 if e.function==0x4ab400:
  if small_block:scratch[:]=small_values
  return small_block
 if e.function in(0x4ab460,HEAPFREE):free_list.append(event[2][-1]);return 1
 if e.function in(0x4a49b0,0x4dc560):
  result=C.c_uint32();supported=lib.claw_core_registration_entry(e.function,e.receiver,e.arguments[0],e.arguments[1],C.byref(g),host,C.byref(fault),C.byref(result));assert supported and not fault.value;return result.value
 return 0
host=Host(None,lookup,allocate,freed,invoke,clock)
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);address=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,address)
observe_destructor=False
def hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if observe_destructor and address in(0x4a49b0,0x4dc560):
  n=1 if address==0x4a49b0 else 2;receiver=0 if n==1 else u.reg_read(UC_X86_REG_ECX);original_events.append(((address,receiver,tuple(m.read_words(sp+4,n))),snapshot(False)))
 config={0x4a48e0:(1,0),0x4a7bc0:(1,0),0x4a7c40:(1,0),0x4ab400:(3,0),0x4ab460:(3,0),HEAPFREE:(3,12),0x4db4d0:(3,12)}
 if address not in config:return
 n,pop=config[address];args=tuple(m.read_words(sp+4,n));receiver=u.reg_read(UC_X86_REG_ECX)if address==0x4db4d0 else 0
 original_events.append(((address,receiver,args),snapshot(False)));result=0
 if address==0x4a48e0:result=alloc(args[0],False)
 elif address==0x4ab400:
  if small_block:m.write_words(args[1],[small_values[0]]);m.write_words(args[2],[small_values[1]])
  result=small_block
 elif address in(0x4ab460,HEAPFREE):free_list.append(args[-1]);result=1
 returned(pop,result)
u.hook_add(UC_HOOK_CODE,hook)
def prepare(seed=None,count=0):
 global g,buf,scratch,cursor,allocation_sizes,fail_alloc,small_block
 if seed is None:seed=rng.getrandbits(32)
 local=random.Random(seed);g=Globals();g.words[:]=[local.getrandbits(32)for _ in range(130)];g.words[129]=count
 g.words[(0x544b68-GBASE)//4+1]=0;g.words[(0x544b50-GBASE)//4+1]=0;g.words[(0x544b18-GBASE)//4+1]=0;g.words[(0x544b80-GBASE)//4+1]=0
 lib.claw_core_registration_defaults(C.byref(g));g.errorLocation=local.getrandbits(32);g.heapHandle=0x12345678;g.heapFreeFunction=HEAPFREE
 buf=(C.c_uint8*SIZE).from_buffer_copy(local.randbytes(SIZE));scratch=(C.c_uint32*2)();cursor=0x4000;allocation_sizes={};fault.value=0;fail_alloc=False;small_block=0;free_list.clear()
 put(STRING,[0]);put(HANDLER,[0x4dc420,0,local.getrandbits(32),2,2,0x533474]);put(OBJ,[0x513e34,0x544b68,32,0])
 active=sorted(local.sample(range(0x3000000,0x3010000,16),count))
 for i,t in enumerate(active):g.words[33+i*3]=t;g.words[34+i*3]=local.getrandbits(32)or 1
 return active

def compare(fn,receiver,label,a=0,b=0,destructor=False,initialize=False):
 global cursor,allocation_sizes,calls,events,observe_destructor
 before=Globals.from_buffer_copy(bytes(g));old=bytes(buf);old_cursor=cursor;old_sizes=dict(allocation_sizes);old_frees=list(free_list);native_events.clear();callback_errors.clear();fault.value=0
 # Exact original private out-parameter locations for these bounded wrappers.
 delta=12 if destructor else 8 if fn==0x4f6428 else 0
 g.freeScratchTokens[:]=[m.stack-delta-4,m.stack-delta+4]
 result=C.c_uint32()
 if initialize:supported=lib.claw_core_registration_initialize(C.byref(g),host,C.byref(fault))
 elif destructor:supported=lib.claw_actor_destruction_entry(fn,receiver,a,C.byref(DestructionGlobals(0,0,0x52e1c4)),host,C.byref(fault),C.byref(result))
 else:supported=lib.claw_core_registration_entry(fn,receiver,a,b,C.byref(g),host,C.byref(fault),C.byref(result))
 assert supported and not fault.value and not callback_errors,(label,'native support/fault',supported,fault.value,callback_errors)
 expected=snapshot(True);expected_events=list(native_events);expected_heap=bytes(buf);next_cursor=cursor;next_sizes=dict(allocation_sizes);new_frees=list(free_list)
 cursor=old_cursor;allocation_sizes=old_sizes;free_list[:]=old_frees;m.write_words(GBASE,before.words);m.write_words(0x533470,[before.defaultBitCount]);m.write_words(0x545fc4,[before.heapHandle]);m.write_words(0x546964,[HEAPFREE]);u.mem_write(BASE,old);m.write_words(0,[0x12345678]);u.reg_write(UC_X86_REG_EBP,0x100a000);m.write_words(0x100a004,[before.errorLocation]);original_events.clear();observe_destructor=destructor
 if initialize:
  for function in(0x4db600,0x4dbb70,0x4dc160,0x4dc260,0x4dc380):m.call(function,0)
 else:
  nargs=2 if fn in(0x4dc560,0x4dbe10)else 1 if fn in(0x4dc3a0,0x4dc3d0,0x4db620,0x4dc7b0,0x4a49b0,0x4f6428)else 0
  value=m.call(fn,receiver,struct.pack('<'+'I'*nargs,*([a,b][:nargs])))
  if fn in(0x4dc3d0,0x4dc560,0x4db620,0x4dc180,0x4dc7b0,0x4dbe10):assert value==result.value,(label,'EAX',hex(value),hex(result.value))
 actual=snapshot(False)
 if actual!=expected:
  diffs=[(hex(GBASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(g.words,m.read_words(GBASE,130)))if x!=y];print(label,'globals',diffs[:20])
  diffs=[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(expected_heap,bytes(u.mem_read(BASE,SIZE))))if x!=y];print(label,'heap',diffs[:20]);raise AssertionError((label,'complete buffer mismatch'))
 if original_events!=expected_events:
  print(label,'event lengths',len(expected_events),len(original_events))
  for i,(x,y)in enumerate(zip(expected_events,original_events)):
   if x!=y:print('EVENT',i,x[0],y[0],'snapshots equal',x[1]==y[1]);break
  raise AssertionError((label,'ordered complete snapshot mismatch'))
 assert cursor==next_cursor and allocation_sizes==next_sizes and free_list==new_frees and m.read_words(0,1)==[0x12345678]
 cursor=next_cursor;allocation_sizes=next_sizes;free_list[:]=new_frees;calls+=1;events+=len(native_events);return result.value
