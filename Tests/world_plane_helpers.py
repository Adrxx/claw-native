"""Private full-heap original-instruction oracle and explicit service fixtures."""
import ctypes as C,struct,hashlib,json,random,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/world-plane-agent';WORK.mkdir(exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f)for f in('WorldPlaneRuntime.cpp','SceneCameraRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp')],'-o',str(WORK/'libWorldPlaneRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x600000
PLANE,SCENE,WORLD,IMAGE_REG,RESOURCE,IMAGE,IMAGES,ARRAY,TABLE,RECT,RECORD=[BASE+0x1000+i*0x1000 for i in range(11)]
WORLD_BASE=BASE+0x20000;ALLOC_BASE=0x300000;heap=(C.c_uint8*SIZE)();context=Context();cursor=ALLOC_BASE;native_events=[];original_events=[];errors=[];policy=0;lookup_number=0;native_allocations=[];original_allocations=[];calls=events=0
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
lib=C.CDLL(str(WORK/'libWorldPlaneRuntime.dylib'))
for n,k in(('construct',4),('load',4),('tile_size',3),('add',4)):
 f=getattr(lib,'claw_world_plane_'+n);f.argtypes=[C.c_uint32]*k+[C.POINTER(Context)]+([]if n in('construct','tile_size')else[Dependency,C.c_void_p]);f.restype=C.c_uint32
def get(t,n=1,native=True):return list(struct.unpack_from('<'+'I'*n,bytes(heap),t-BASE))if native else m.read_words(t,n)
def put(t,values,native=True):
 b=struct.pack('<'+'I'*len(values),*(x&0xffffffff for x in values));write(t,b,native)
def write(t,b,native=True):
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def snapshot(native):
 # Every byte of the seeded raw host heap, not only modeled fields.
 return hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest()
@Lookup
def lookup(user,t,n):return C.addressof(heap)+t-BASE if t%4==0 and BASE<=t and t+4*n<=BASE+SIZE else None
def alloc(n,native):
 global cursor
 token=BASE+cursor;cursor+=max(0x400,(n+15)&~15);assert cursor<=SIZE,(n,cursor)
 (native_allocations if native else original_allocations).append((token,n));return token
@Allocate
def allocate(user,n):native_events.append(((0x4f63ec,0,(n,),None),snapshot(True)));return alloc(n,True)
@Free
def free(user,t):raise AssertionError('Unexpected free adapter')
@Invoke
def invoke(user,event):raise AssertionError('Unexpected camera/scene service')
@Clock
def clock(user):return 0
def effect(event,native):
 global lookup_number
 fn,receiver,args,name=event
 if fn==0x4f6286:
  lookup_number+=1
  if policy==2 and lookup_number==1:put(RECORD+0x70,[99,37],native);put(RECORD+0x68,[-701,993],native)
  return 0 if policy==1 and lookup_number%2 else RESOURCE
 if fn==0x4f582f:
  index,value=args;array=ARRAY if receiver==PLANE+0x9c or receiver>=BASE+ALLOC_BASE and receiver<BASE+SIZE else TABLE
  if struct.unpack('<i',struct.pack('<I',index))[0]<0:return 0
  put(array+index*4,[value],native);put(receiver+4,[array,max(get(receiver+8,native=native)[0],index+1),256,1],native);return 0
 if fn==0x4d1620:
  if policy==3:return 0
  put(receiver+0xb0,[BASE+0x15000],native);return 1
 if fn==0x4d2210:put(receiver+8,[get(receiver+8,native=native)[0]|0x10000],native);return 0
 raise AssertionError(('Unrepresented service',event))
@Dependency
def dependency(ctx,e,user):
 try:
  e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);native_events.append((event,snapshot(True)));return effect(event,True)
 except BaseException as exc:errors.append(exc);return 0
context.scene=Host(None,lookup,allocate,free,invoke,clock)
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def text(t):return bytes(u.mem_read(t,128)).split(b'\0',1)[0]
def hook(uc,address,size,user):
 if address not in(0x10fe000,0x4f63ec,0x4f6286,0x4f582f,0x4d1620,0x4d2210):return
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x10fe000:
  out,inp=m.read_words(sp+4,2);u.mem_write(out,bytes(u.mem_read(inp,16)));returned(8,1);return
 if address==0x4f63ec:
  args=tuple(m.read_words(sp+4,1));original_events.append(((address,0,args,None),snapshot(False)));returned(0,alloc(args[0],False));return
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);event=(address,u.reg_read(UC_X86_REG_ECX),(),text(name));original_events.append((event,snapshot(False)));v=effect(event,False);m.write_words(out,[v]);returned(8,int(bool(v)));return
 if address in(0x4f582f,0x4d1620,0x4d2210):
  n=1 if address==0x4d2210 else 2;event=(address,u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,n)),None);original_events.append((event,snapshot(False)));v=effect(event,False);returned(n*4,v)
u.hook_add(UC_HOOK_CODE,hook);m.write_words(0x546d58,[0x10fe000])
def prepare(seed=0,record=None):
 global cursor,policy,lookup_number
 rng=random.Random(seed);data=rng.randbytes(SIZE);write(BASE,data);cursor=ALLOC_BASE;policy=lookup_number=0;context.fault=0;native_allocations.clear();original_allocations.clear()
 put(SCENE+0x10,[IMAGE_REG]);put(WORLD+0xc,[SCENE]);put(WORLD+0x10,[0,0,639,479]);put(WORLD+0x34,[0x5108fc,TABLE,0,256,1]);put(RECT,[0,0,639,479]);put(PLANE+0xc,[SCENE]);put(PLANE+0x9c,[0x5108fc,ARRAY,0,256,1]);put(PLANE+0x18,[0x3f800000,0x3f800000])
 put(RESOURCE+0x14,[IMAGES,3]);put(RESOURCE+0x64,[0,2]);put(IMAGES,[0,IMAGE,0]);put(IMAGE+0x10,[48,32])
 w=[0]*40;w[0]=160;w[2]=1;w[22:30]=[64,64,4,3,689,4723,100,100];w[30:37]=[0x12345678,2,1,0x100,0x200,0x300,7]
 if record is not None:w=list(record)
 put(RECORD,w);write(RECORD+16,b'MAIN\0');put(WORLD_BASE+0x100,list(range(12)));write(WORLD_BASE+0x200,b'LEVEL_TEST_A\0LEVEL_TEST_B\0')
 return w
def original_call(f,receiver,args):
 u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,receiver);u.emu_start(f,m.stop,count=15000000);assert u.reg_read(UC_X86_REG_EIP)==m.stop,'Original instruction bound';return u.reg_read(UC_X86_REG_EAX)
def compare(kind,label,*args):
 global cursor,lookup_number,calls,events
 before=bytes(heap);old_cursor=cursor;old_lookup=lookup_number;native_events.clear();original_events.clear();native_allocations.clear();original_allocations.clear();errors.clear();context.fault=0
 result=getattr(lib,'claw_world_plane_'+kind)(*args,C.byref(context),*(()if kind in('construct','tile_size')else(dependency,None)))
 assert not context.fault and not errors,(label,context.fault,errors)
 expected=bytes(heap);expected_cursor=cursor;expected_lookup=lookup_number;expected_events=list(native_events);expected_allocations=list(native_allocations)
 u.mem_write(BASE,before);m.write_words(0,[0x12345678]);cursor=old_cursor;lookup_number=old_lookup
 f={'construct':0x4d03b0,'tile_size':0x4d0cd0,'load':0x4d0450,'add':0x4cb7b0}[kind]
 value=original_call(f,args[0],args[1:]);actual=bytes(u.mem_read(BASE,SIZE))
 assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(8 if kind=='tile_size'else 12),(label,'actual callee stack cleanup')
 if actual!=expected:
  diffs=[(i,expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if actual[i:i+4]!=expected[i:i+4]];print('DIFF',label,diffs[:25]);raise AssertionError((label,'complete raw heap'))
 if original_events!=expected_events:
  for i,(a,b)in enumerate(zip(original_events,expected_events)):
   if a!=b:print('EVENT',label,i,a,b);break
  raise AssertionError((label,'ordered complete event snapshots',len(original_events),len(expected_events)))
 assert kind=='tile_size'or value==result,(label,'eax',value,result)
 assert original_allocations==expected_allocations and m.read_words(0,1)==[0x12345678]
 assert cursor==expected_cursor and lookup_number==expected_lookup
 calls+=1;events+=len(expected_events);return result
