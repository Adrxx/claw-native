"""Original whole manager roots with physical COM and explicit callee seams."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/audio-manager-lifecycle-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{name}.cpp')for name in ('AudioManagerLifecycleRuntime','AudioEvents','AmbientAudioBackendRuntime','AudioPCMTransfer','AudioResourceRuntime')],'-o',str(WORK/'libAudioManagerLifecycleRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Scene(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Scene),('maximumTraversal',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6),('deviceMethod',C.c_uint32),('outputWord',C.POINTER(C.c_uint32))]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
class Resource(C.Structure):_fields_=[(n,C.c_uint32)for n in ('managerToken','deviceToken','deviceAvailable','resourceHead','resourceTail')]
class PCM(C.Structure):_fields_=[('resource',Resource),('fadeHead',C.c_uint32),('fadeTail',C.c_uint32)]
ObjectLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32)
Create=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32,C.POINTER(C.c_uint32))
Duplicate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32))
Get=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32))
Set=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32);Report=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32)
class ResourceHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',ObjectLookup),('allocate',Allocate),('createBuffer',Create),('duplicateBuffer',Duplicate),('get',Get),('set',Set),('report',Report)]
BytesLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32)
Seek=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32);Read=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32);Retry=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
class Regions(C.Structure):_fields_=[(n,C.c_uint32)for n in ('firstToken','firstBytes','secondToken','secondBytes')]
Lock=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Regions));Unlock=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,Regions);Release=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
class PCMHost(C.Structure):_fields_=[('resource',ResourceHost),('lookupBytes',BytesLookup),('free',Free),('seek',Seek),('read',Read),('retry',Retry),('lock',Lock),('unlock',Unlock),('release',Release)]
BASE,SIZE=0x3000000,0x30000;M,D,D2,DVT,BVT=[BASE+i*0x1000 for i in range(1,6)];P=BASE+0x6000;V=BASE+0xa000;B=BASE+0xc000;FA=BASE+0xe000
METHODS={0x10ff008:8,0x10ff018:0x18,0x10fe008:8,0x10fe048:0x48};m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
for address in METHODS:u.mem_write(address,b'\xc3')
IMAGE_START,IMAGE_END,_=next(v for v in u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(IMAGE_END-IMAGE_START+1)).from_buffer_copy(bytes(u.mem_read(IMAGE_START,IMAGE_END-IMAGE_START+1)))
GS,GN=0x520000,0x30000;seedGlobals=bytes(u.mem_read(GS,GN));globals=(C.c_uint8*GN)();heap=(C.c_uint8*SIZE)();rng=random.Random(0x4b47e0);ctx=Context();native=True;events=[];freed=[];errors=[];calls=eventCount=0;compose=False;mutation=0;createResult=coopResult=stopResult=0;releaseResult=7;createdDevice=D;activePCM=None;cursor=0x18000;resources=[];controls=[];guards=0;prefixStop=None;extraPhysical=None;extraNative=None;selectedEntry=0
lib=C.CDLL(str(WORK/'libAudioManagerLifecycleRuntime.dylib'));U=C.c_uint32;UP=C.POINTER(U)
lib.claw_audio_manager_lifecycle_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_audio_manager_lifecycle_entry.restype=U
lib.claw_ambient_audio_backend_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_ambient_audio_backend_entry.restype=U
lib.claw_audio_destroy_resource.argtypes=[C.POINTER(PCM),U,PCMHost,UP];lib.claw_audio_destroy_resource.restype=None

def put(t,v):
 data=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if not native:u.mem_write(t,data)
 else:C.memmove(C.addressof(heap if BASE<=t<BASE+SIZE else globals)+t-(BASE if BASE<=t<BASE+SIZE else GS),data,len(data))
def get(t,n=1):
 if not native:return m.read_words(t,n)
 buf,start=(heap,BASE)if BASE<=t and t+n*4<=BASE+SIZE else(globals,GS)if GS<=t and t+n*4<=GS+GN else(image,IMAGE_START)
 return list(struct.unpack_from('<'+'I'*n,buf,t-start))
def sync():
 if native and activePCM:put(M+4,[activePCM.resource.resourceHead,activePCM.resource.resourceTail,activePCM.fadeHead,activePCM.fadeTail])
def snapshot():
 sync();return(hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(bytes(globals)if native else bytes(u.mem_read(GS,GN))).digest(),tuple(freed),cursor)
@Lookup
def lookup(_,t,n):
 for buf,start,length in ((heap,BASE,SIZE),(globals,GS,GN),(image,IMAGE_START,IMAGE_END-IMAGE_START+1)):
  if start<=t and t+n*4<=start+length:return C.addressof(buf)+t-start
 return None
@ObjectLookup
def objectLookup(_,t):return lookup(None,t,14)
@Free
def free(_,t):events.append((0x4f6428,0,(t,),0,None,snapshot()));freed.append(t)
@Allocate
def allocate(_,n):
 global cursor
 events.append((0x4f63ec,0,(n,),0,None,snapshot()));t=BASE+cursor;cursor+=(n+15)&~15;assert cursor<SIZE;return t
ctx.scene=Scene(None,lookup,allocate,free,Invoke(),Clock())

def teardownFixture(manager,pool):
 # Explicit logical source-callee fixture, never counted as PCM recovery.
 nxt,prev=get(pool+4,2)
 if prev:put(prev,[nxt])
 else:put(manager+4,[nxt])
 if nxt:put(nxt+4,[prev])
 else:put(manager+8,[prev])
 freed.append(pool)
 if mutation==4:put(manager+0x14,[D2])
 if mutation==5:put(manager+0x78,[0])

def effect(f,receiver,args,method=0,out=None):
 if f==0x4f4480:
  if out:out[0]=createdDevice
  else:put(args[1],[createdDevice])
  if mutation==1:put(M+0x7c,[0xfeedface]);put(M+0x78,[0xabcdef])
  return createResult
 if f==0x4b4ed0:
  if mutation==2:put(M+0x14,[D2]);put(M+0x78,[9]);put(M+0x7c,[123])
  return 0
 if method:
  if method==0x18:
   if mutation==3:put(M+0x14,[D2]);put(M+0x7c,[0xface]);put(M+0x78,[8])
   return coopResult
  if method==8:
   if mutation==6:put(M+0x14,[D2]);put(M+0x7c,[789]);put(M+0x78,[1])
   if mutation==10:put(M+4,[P+0x304,P+0x304])
   return releaseResult
  if method==0x48:return stopResult
 if f==0x4b4ae0:
  if mutation!=9:teardownFixture(receiver,args[0])
  return 0
 if f==0x4b3e30:
  if mutation==7:put(receiver+4,[0])
  if mutation==8:put(M+0x78,[0])
  return 1
 raise AssertionError(('unrepresented service',hex(f),hex(receiver),args,method))
@Report
def report(_,line,value):events.append((0x4b4ed0,0,(0x53228c,line,value),0,None,snapshot()));effect(0x4b4ed0,0,[0x53228c,line,value])
@Release
def release(_,buffer):events.append((get(get(buffer)[0]+8)[0],0,(buffer,),8,None,snapshot()));return effect(0,0,[buffer],8)
pcmHost=PCMHost(ResourceHost(None,objectLookup,allocate,Create(),Duplicate(),Get(),Set(),report),BytesLookup(),free,Seek(),Read(),Retry(),Lock(),Unlock(),release)

def destroyComposed(manager,pool):
 global activePCM
 words=get(manager,32);activePCM=PCM(Resource(manager,words[5],words[30],words[1],words[2]),words[3],words[4]);fault=U();lib.claw_audio_destroy_resource(C.byref(activePCM),pool,pcmHost,C.byref(fault));assert not fault.value;sync();activePCM=None
@Dependency
def dependency(c,ev,_):
 e=ev.contents;args=list(e.arguments[:e.argumentCount]);initial=e.outputWord[0]if e.outputWord else None;events.append((e.function,e.receiver,tuple(args),e.deviceMethod,initial,snapshot()))
 try:
  if compose and e.function==0x4b4ae0:destroyComposed(e.receiver,args[0]);return 0
  if compose and e.function==0x4b3e30:
   aa=(U*len(args))(*args);out=U();ok=lib.claw_ambient_audio_backend_entry(e.function,e.receiver,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault;return out.value
  return effect(e.function,e.receiver,args,e.deviceMethod,e.outputWord)or 0
 except BaseException as error:errors.append(error);return 0

def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(uc,address,size,_):
 if extraPhysical and extraPhysical(uc,address,size,_):return
 if address not in METHODS and address not in(0x4f4480,0x4b4ed0,0x4b4ae0,0x4b3e30,0x4f6428,0x4f63ec):return
 if prefixStop is not None and len(events)>=prefixStop and address in(0x4b4ae0,0x4b3e30):uc.emu_stop();return
 sp=u.reg_read(UC_X86_REG_ESP);method=METHODS.get(address,0);count=3 if address==0x4f4480 or method==0x18 or address==0x4b4ed0 else 1 if method or address in(0x4b4ae0,0x4f6428,0x4f63ec)else 0;args=get(sp+4,count);receiver=u.reg_read(UC_X86_REG_ECX)if address in(0x4b4ae0,0x4b3e30)else 0;initial=get(args[1])[0]if address==0x4f4480 else None;events.append((address,receiver,tuple(args),method,initial,snapshot()))
 if compose and address in(0x4b4ae0,0x4b3e30):return
 if address==0x4f6428:freed.append(args[0]);returned(0);return
 if address==0x4f63ec:
  global cursor
  t=BASE+cursor;cursor+=(args[0]+15)&~15;assert cursor<SIZE;returned(0,t);return
 value=effect(address,receiver,args,method)
 returned(0 if address==0x4b4ed0 else count*4,value)
u.hook_add(UC_HOOK_CODE,hook)

def prepare(pools=0,voices=0,fades=0):
 global native,events,freed,errors,compose,mutation,createResult,coopResult,releaseResult,stopResult,createdDevice,activePCM,cursor,resources,controls,prefixStop
 native=True;prefixStop=None;C.memmove(C.addressof(globals),seedGlobals,GN);C.memset(C.addressof(heap),0xa5,SIZE);ctx.maximumTraversal=128;ctx.fault=0;compose=False;mutation=0;createResult=coopResult=stopResult=0;releaseResult=7;createdDevice=D;activePCM=None;cursor=0x18000;events=[];freed=[];errors=[]
 put(M,[rng.getrandbits(32)for _ in range(32)]);put(M,[0x513514]);put(M+4,[0,0,0,0]);put(M+0x14,[D]);put(M+0x78,[1,0x12345678]);put(D,[DVT]);put(D2,[DVT]);put(DVT+8,[0x10ff008]);put(DVT+0x18,[0x10ff018]);put(BVT+8,[0x10fe008]);put(BVT+0x48,[0x10fe048]);resources=[P+i*0x100 for i in range(pools)];controls=[FA+i*0x100 for i in range(fades)]
 for i,pool in enumerate(resources):
  array=[rng.getrandbits(32)for _ in range(14)];array[0]=0x51350c;array[1]=resources[i+1]+4 if i+1<pools else 0;array[2]=resources[i-1]+4 if i else 0;array[3]=B+i*0x100;array[4]=M;array[12]=V+i*0x800+4 if voices else 0;array[13]=V+i*0x800+(voices-1)*0x100+4 if voices else 0;put(pool,array);put(array[3],[BVT])
  for j in range(voices):
   v=V+i*0x800+j*0x100;av=[rng.getrandbits(32)for _ in range(14)];av[0]=0x513510;av[1]=v+0x100+4 if j+1<voices else 0;av[2]=v-0x100+4 if j else 0;av[3]=B+0x800+i*0x800+j*0x80;av[4]=M;av[12]=0;put(v,av);put(av[3],[BVT])
 if resources:put(M+4,[resources[0]+4,resources[-1]+4])
 for i,f in enumerate(controls):
  put(f,[0x513520,controls[i+1]+4 if i+1<fades else 0,controls[i-1]+4 if i else 0,1,resources[i%pools]if pools else 0xfeed,0,70,20,100,0])
 if controls:put(M+0xc,[controls[0]+4,controls[-1]+4])

def compare(f,receiver=M,args=(),label=None):
 global native,events,freed,cursor,calls,eventCount,selectedEntry
 native=True;selectedEntry=f;old=bytes(heap);og=bytes(globals);of=freed[:];oc=cursor;events=[];out=U();aa=(U*len(args))(*args);ok=extraNative(f,receiver,args,out)if extraNative and f in(0x4b4a20,)else lib.claw_audio_manager_lifecycle_entry(f,receiver,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,(hex(f),label,ok,ctx.fault,errors);expected=bytes(heap);eg=bytes(globals);ne=events[:];nf=freed[:];nc=cursor
 native=False;u.mem_write(BASE,old);u.mem_write(GS,og);freed=of;cursor=oc;events=[]
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(args),*args))
 except Exception as error:raise AssertionError(('original fault',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events[-2:]))from error
 actual=bytes(u.mem_read(BASE,SIZE));ag=bytes(u.mem_read(GS,GN));assert actual==expected,('heap',hex(f),label,[(hex(BASE+i),expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=actual[i:i+4]][:12]);assert ag==eg,('globals',hex(f),label,[(hex(GS+i),eg[i:i+4].hex(),ag[i:i+4].hex())for i in range(0,GN,4)if eg[i:i+4]!=ag[i:i+4]][:12]);assert events==ne,('events',hex(f),label,[(hex(e[0]),hex(e[1]),e[2:5])for e in ne],[(hex(e[0]),hex(e[1]),e[2:5])for e in events]);assert freed==nf and cursor==nc
 if f in(0x4b4710,0x4b4770,0x4b47e0,0x4b4a20):assert ret==out.value,('EAX',hex(f),label,ret,out.value)
 native=True;C.memmove(C.addressof(heap),actual,SIZE);C.memmove(C.addressof(globals),ag,GN);calls+=1;eventCount+=len(ne);return out.value
