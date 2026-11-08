"""Whole source scene/controller/map lifecycles with explicit physical transport."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/scene-lifecycle-agent'
names=['SceneLifecycleRuntime','AudioManagerLifecycleRuntime','SceneDisplayRuntime','SinglePlayerSceneRuntime','WorldFileRuntime','SpatialGridRuntime','SceneCameraRuntime','WorldPlaneRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster','GraphicsManagerLifecycleRuntime','GraphicsManagerConstructionRuntime','PaletteResourceRuntime','AmbientAudioBackendRuntime','CArrayRuntime','SoundTriggerLogicRuntime','EnemySpeechRuntime','SpeechActor','AudioEvents','ActorResourceBindings','ActorDestruction','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','AnimationEngine','AnimationOperations']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in names],'-o',str(WORK/'libSceneLifecycle.dylib')],check=True)
U=C.c_uint32
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('clock',Clock)]
class Globals(C.Structure):_fields_=[('device',U),('cooperative',U),('shifts',U*3),('reductions',U*3)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('palette',C.c_void_p),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',C.POINTER(U)*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000
MANAGER,DEVICE,VT,ARRAY,SURFACE,NODES,PALETTE,DD_SURFACE,DD_VT,SCRATCH=[BASE+0x1000+i*0x1000 for i in range(10)]
HEAP_START=BASE+0x10000;nextAllocation=[HEAP_START,HEAP_START];allocated=[{},{}];freed=[[],[]]
GLOBAL_START,GLOBAL_SIZE=0x500000,0x48000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x700000,0x1000);m.u.mem_map(0x710000,0x1000);m.u.mem_map(0x720000,0x1000);m.executed.clear();static=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE));image=(C.c_uint8*GLOBAL_SIZE).from_buffer_copy(static);heap=(C.c_uint8*SIZE)();g=Globals();context=Context();events=[[],[]];calls=eventCount=0;seed=b'';failure={};modes=[];allocFailure=0;allocationCount=[0,0];mutation=0;errors=[]
@Lookup
def lookup(_,t,n):
 if t%4==0 and BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if t%4==0 and GLOBAL_START<=t and t+n*4<=GLOBAL_START+GLOBAL_SIZE:return C.addressof(image)+t-GLOBAL_START
 errors.append(('span',hex(t),n));return None
context.scene=Host(None,lookup,Allocate(),Free(),Invoke(),Clock());context.globals=C.pointer(g);context.maximum=1000000
lib=C.CDLL(str(WORK/'libSceneLifecycle.dylib'));lib.claw_graphics_manager_lifecycle_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_graphics_manager_lifecycle_entry.restype=U

def get(t,n=1,native=True):
 if native:
  p=lookup(None,t,n);assert p,hex(t);return list((U*n).from_address(p))
 return m.read_words(t,n)
def put(t,v,native=True):
 b=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:
  p=lookup(None,t,len(v));assert p,hex(t);C.memmove(p,b,len(b))
 else:m.u.mem_write(t,b)
def globalBytes(native):
 if not native:return bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
 b=bytearray(bytes(image));struct.pack_into('<I',b,0x541398-GLOBAL_START,g.device);struct.pack_into('<I',b,0x541374-GLOBAL_START,g.cooperative);struct.pack_into('<6I',b,0x54135c-GLOBAL_START,*g.shifts,*g.reductions);return bytes(b)
def snapshot(native):return hashlib.sha256(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(globalBytes(native)).digest(),tuple(sorted(allocated[0 if native else 1].items())),tuple(freed[0 if native else 1])
def record(f,r,a,native,mask=0,buffers=()):events[0 if native else 1].append(((f,r,tuple(a),mask,tuple(buffers)),snapshot(native)))

def sourceCall(f,r,args):
 saved=m.u.context_save();stack=m.stack;m.stack=m.u.reg_read(UC_X86_REG_ESP)-0x1000
 try:return m.call(f,r,struct.pack('<'+'I'*len(args),*args),max_instructions=1000000)
 finally:m.stack=stack;m.u.context_restore(saved)

def effect(f,r,a,native,buffers=()):
 i=0 if native else 1
 if f==0x4f63ec:
  allocationCount[i]+=1
  if allocationCount[i]==allocFailure:return 0
  token=nextAllocation[i];nextAllocation[i]+=(a[0]+15)&~15;assert nextAllocation[i]<BASE+SIZE;allocated[i][token]=a[0];return token
 if f==0x4f6428:
  if a[0]:allocated[i].pop(a[0],None)
  freed[i].append(a[0]);return 0
 if f==0x546850:put(a[1],[DEVICE],native);return failure.get('create',0)
 if f==0x700050:return failure.get('cooperative',0)
 if f==0x70002c:
  put(a[1]+4,[0x08000000],native);return failure.get('caps',0)
 if f==0x700054:return failure.get('setMode',0)
 if f==0x700030:
  output=[0]*27;output[0]=108;output[21]=8;output[22:25]=[0xff0000,0xff00,0xff]
  if native:
   dest=buffers[0];dest[:]=output
  else:put(a[1],output,False)
  return failure.get('display',0)
 if f==0x700020:
  for data in modes:
   put(SCRATCH,data,native)
   if native:
    out=U();argv=(U*2)(SCRATCH,0);assert lib.claw_graphics_manager_lifecycle_entry(0x4bcda0,0,argv,2,C.byref(context),dependency,None,C.byref(out))
   else:assert sourceCall(a[4],0,[SCRATCH,0])==1
  return failure.get('enumerate',0)
 if f in(0x70004c,0x700008,0x710008):return failure.get('release',0)
 if f==0x4bd260:return 0
 raise AssertionError((hex(f),hex(r),a))
@Dep
def dependency(_,ep,user):
 q=ep.contents;a=list(q.arguments[:q.count]);normalized=[];live=[]
 for j in range(q.bufferCount):normalized.append(tuple(q.buffers[j][:q.sizes[j]//4]));live.append((U*(q.sizes[j]//4)).from_address(C.addressof(q.buffers[j].contents)))
 record(q.function,q.receiver,a,True,q.localMask,normalized)
 try:return effect(q.function,q.receiver,a,True,live)
 except Exception as error:errors.append(error);return 0
COUNTS={0x4f63ec:(1,0),0x4f6428:(1,0),0x4bd260:(3,0),0x700050:(3,12),0x70002c:(3,12),0x700054:(4,16),0x700030:(2,8),0x700020:(5,20),0x70004c:(1,4),0x700008:(1,4),0x710008:(1,4),0x720000:(1,4)}
CREATE=0x10fe000;m.write_words(0x546850,[CREATE]);COUNTS[CREATE]=(3,12)
static=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))

def hook(u,address,size,user):
 if address not in COUNTS:return
 n,pop=COUNTS[address];sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,n);f=0x546850 if address==CREATE else address;r=u.reg_read(UC_X86_REG_ECX) if address in(0x720000,0x720028,0x720004,0x720014) else 0;mask=0;buffers=[]
 if f==0x700014:
  buffers=[tuple(get(a[2],256,False))]
  if 0x2000000<=a[2]<0x2010000:a[2]=0;mask=4
 if f==0x710030:buffers=[tuple(get(a[1],1,False)),tuple(get(a[2],1,False))];originals=a[1:3];a[1:3]=[0,0];mask=6
 if f==0x700030:buffers=[tuple(get(a[1],27,False))];orig=a[1];a[1]=0;mask=2
 record(f,r,a,False,mask,buffers)
 if f==0x700030:a[1]=orig
 if f==0x710030:a[1:3]=originals
 v=effect(f,r,a,False);u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
m.u.hook_add(UC_HOOK_CODE,hook)

def prepare(number=0):
 global heap,g,context,allocated,freed,failure,modes,allocFailure,mutation
 heap=(C.c_uint8*SIZE).from_buffer_copy(random.Random(number).randbytes(SIZE));C.memmove(C.addressof(image),static,GLOBAL_SIZE);g=Globals(DEVICE,0,(U*3)(0,0,0),(U*3)(0,0,0));context.globals=C.pointer(g);context.fault=0;errors.clear();nextAllocation[:]=[HEAP_START,HEAP_START];allocated=[{},{}];freed=[[],[]];allocationCount[:]=[0,0];failure={};modes=[];allocFailure=mutation=0
 put(DEVICE,[VT]);put(VT+8,[0x700008]);put(VT+0x20,[0x700020]);put(VT+0x2c,[0x70002c,0x700030]);put(VT+0x4c,[0x70004c,0x700050,0x700054]);put(DD_SURFACE,[DD_VT]);put(DD_VT+8,[0x710008])
 #Source static initializer4bc0e0 is independently tested below; global
 #array is a live mutable image span and not a context-owned duplicate.
 put(0x541378,[0x51079c,0,0,0,0]);ctor(0x4bc120,MANAGER)

def sync():
 m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GLOBAL_START,globalBytes(True));nextAllocation[1]=nextAllocation[0];allocated[1]=dict(allocated[0]);freed[1]=list(freed[0]);allocationCount[:]=[0,0];context.fault=0

def ctor(f,t):
 out=U();assert lib.claw_graphics_manager_lifecycle_entry(f,t,None,0,C.byref(context),dependency,None,C.byref(out))and not context.fault


class DisplayContext(C.Structure):_fields_=[('scene',Host),('graphics',C.POINTER(Context)),('image',C.POINTER(U)),('maximum',U),('fault',U)]
DisplayDep=C.CFUNCTYPE(U,C.POINTER(DisplayContext),C.POINTER(Call),C.c_void_p)
imageGlobals=(U*288)();display=DisplayContext(context.scene,C.pointer(context),imageGlobals,1000000,0)
lib.claw_scene_display_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(DisplayContext),DisplayDep,C.c_void_p,C.POINTER(U)]
lib.claw_scene_display_entry.restype=U
HOLDER,PARENT,RENDERER,ARG2,CHILD1,CHILD2,CHILD3,CHILDVT,ARGVT=[BASE+0x200+i*0x100 for i in range(9)]
COUNTS.update({0x700018:(4,16),0x710058:(2,8),0x710030:(3,12),0x720028:(2,8),0x720004:(1,4),0x720014:(0,0)})
baseEffect=effect;ready=0;drawCount=[0,0];deleteCount=[0,0];attachFailure=0;descFailure=0;createSurfaceFailure=0;mutate=''
def effect(f,r,a,native,buffers=()):
 i=0 if native else 1
 if f==0x700018:put(a[2],[DD_SURFACE],native);return createSurfaceFailure
 if f==0x710058:
  desc=[0]*27;desc[0]=108;desc[1]=7;desc[2]=480;desc[3]=640;desc[4]=640;desc[21]=8;put(a[1],desc,native);return descFailure
 if f==0x710030:
  if native:buffers[1][0]=DD_SURFACE
  else:put(a[2],[DD_SURFACE],False)
  return attachFailure
 if f==0x720028:
  drawCount[i]+=1
  if mutate=='next':put(NODES,[NODES+32],native)
  if mutate=='lifetime':put(r+100,[3],native)
  return drawCount[i]
 if f==0x720014:return ready
 if f==0x720004:
  deleteCount[i]+=1
  if mutate=='slots':put(HOLDER+20,[CHILD3],native)
  return r
 return baseEffect(f,r,a,native,buffers)
#Extend original physical/local and thiscall event normalization.
#The original hook uses this module's live effect profile and ABI table.
@DisplayDep
def displayDependency(_,ep,user):
 q=ep.contents;a=list(q.arguments[:q.count]);live=[];normalized=[]
 for j in range(q.bufferCount):live.append((U*(q.sizes[j]//4)).from_address(C.addressof(q.buffers[j].contents)));normalized.append(tuple(live[-1]))
 record(q.function,q.receiver,a,True,q.localMask,normalized)
 try:return effect(q.function,q.receiver,a,True,live)
 except Exception as error:errors.append(error);return 0
basePrepare=prepare

def prepare(number=0):
 global ready,attachFailure,descFailure,createSurfaceFailure,mutate
 basePrepare(number);display.scene=context.scene;display.graphics=C.pointer(context);display.fault=0;ready=attachFailure=descFailure=createSurfaceFailure=0;mutate='';drawCount[:]=[0,0];deleteCount[:]=[0,0]
 put(PARENT,[0]*15);put(PARENT+4,[HOLDER]);put(PARENT+28,[MANAGER]);put(PARENT+48,[0x12345,0]);put(HOLDER,[0x513c68,0,0,PARENT,0,0,0]);put(VT+0x18,[0x700018]);put(DD_VT+0x30,[0x710030]);put(DD_VT+0x58,[0x710058])
 put(CHILDVT+4,[0x720004]);put(CHILDVT+40,[0x720028]);put(ARGVT+20,[0x720014]);put(ARG2,[ARGVT]);put(RENDERER,[0x513be8,0,0,PARENT,0x51000c,0,0,0,0,0,10])
 for t in (CHILD1,CHILD2,CHILD3):put(t,[CHILDVT]);put(t+100,[1])


class LifecycleCall(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',C.POINTER(U)*3),('sizes',U*3)]
class LifecycleContext(C.Structure):_fields_=[('scene',Host),('display',C.POINTER(DisplayContext)),('graphics',C.POINTER(Context)),('audio',C.c_void_p),('palette',C.c_void_p),('world',C.c_void_p),('image',C.POINTER(U)),('maximum',U),('fault',U)]
LifecycleDep=C.CFUNCTYPE(U,C.POINTER(LifecycleContext),C.POINTER(LifecycleCall),C.c_void_p)
lifecycle=LifecycleContext(context.scene,C.pointer(display),C.pointer(context),None,None,None,imageGlobals,1000000,0)
lib.claw_scene_lifecycle_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(LifecycleContext),LifecycleDep,C.c_void_p,C.POINTER(U)]
lib.claw_scene_lifecycle_entry.restype=U
SCENE=PARENT;PALETTE_CONTROLLER=BASE+0xb000;IMAGE_CONTROLLER=BASE+0xc000;LOGIC_CONTROLLER=BASE+0xd000;ANIMATION_CONTROLLER=BASE+0xe000;SOUND_CONTROLLER=BASE+0xf000
BUCKETS=BASE+0x30000;ASSOC1=BASE+0x30100;ASSOC2=BASE+0x30120;ASSOC3=BASE+0x30140;STRING1=BASE+0x30200;STRING2=BASE+0x30300;STRING3=BASE+0x30400;PLEX=BASE+0x30500
COUNTS[0x720004]=(1,4);COUNTS[0x720014]=(0,0)
DEC,INC=0x10fd000,0x10fd100
m.u.mem_write(DEC,b'\x8b\x44\x24\x04\xf0\xff\x08\x8b\x00\xc2\x04\x00');m.u.mem_write(INC,b'\x8b\x44\x24\x04\xf0\xff\x00\x8b\x00\xc2\x04\x00');m.write_words(0x5469e8,[DEC]);m.write_words(0x5469ec,[INC]);static=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
@LifecycleDep
def lifecycleDependency(_,ep,user):
 q=ep.contents;a=list(q.arguments[:q.count]);normalized=[];live=[]
 for j in range(q.bufferCount):normalized.append(tuple(q.buffers[j][:q.sizes[j]//4]));live.append((U*(q.sizes[j]//4)).from_address(C.addressof(q.buffers[j].contents)))
 record(q.function,q.receiver,a,True,q.localMask,normalized)
 try:return effect(q.function,q.receiver,a,True,live)
 except Exception as error:errors.append(error);return 0
oldPrepare=prepare

def mapFixture(token,variant=0):
 put(token,[0x5105c4,0,17,0,0,0,10])
 if not variant:return
 put(token+4,[BUCKETS,5,3,0,PLEX,10]);put(BUCKETS,[ASSOC1,0,ASSOC3,0,0]);put(ASSOC1,[ASSOC2,0,STRING1+12,CHILD1]);put(ASSOC2,[0,0,STRING2+12,0]);put(ASSOC3,[0,2,STRING3+12,CHILD2]);put(PLEX,[0]);
 for header in(STRING1,STRING2,STRING3):put(header,[1,3,3,0x616263])

def prepare(number=0):
 oldPrepare(number);lifecycle.scene=context.scene;lifecycle.display=C.pointer(display);lifecycle.graphics=C.pointer(context);lifecycle.fault=0
 for t,vt in[(PALETTE_CONTROLLER,0x513b28),(IMAGE_CONTROLLER,0x513b88),(LOGIC_CONTROLLER,0x513b60),(ANIMATION_CONTROLLER,0x513ad8),(SOUND_CONTROLLER,0x513b00)]:
  put(t,[vt,0,0,SCENE]);mapFixture(t+16)
 for offset in(44,72):mapFixture(PALETTE_CONTROLLER+offset)
 put(PALETTE_CONTROLLER+100,[0x12345678]);put(SOUND_CONTROLLER+44,[0x12345678])
 put(SCENE,[0x513ab8]+[0]*14)

def compare(f,t,a,label):
 global calls,eventCount
 sync();events[0].clear();events[1].clear();errors.clear();lifecycle.fault=0;result=U();argv=(U*len(a))(*a);drawCount[:]=[0,0];deleteCount[:]=[0,0]
 assert lib.claw_scene_lifecycle_entry(f,t,argv,len(a),C.byref(lifecycle),lifecycleDependency,None,C.byref(result)),(label,lifecycle.fault,context.fault,errors)
 assert not errors,errors
 source=m.call(f,t,struct.pack('<'+'I'*len(a),*a),max_instructions=10000000)
 assert snapshot(True)==snapshot(False),(label,'wholeheapglobalslife',snapshot(True)==snapshot(False))
 if events[0]!=events[1]:
  for i,(x,y)in enumerate(zip(*events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError((label,'order',len(events[0]),len(events[1])))
 if f in(0x4ce9a0,0x4cefc0,0x4cf0a0,0x4cf160,0x4cf150,0x4cf940,0x4cf930,0x4cf9d0,0x4cf800,0x4f667d,0x4cf8a0,0x4cf280):assert source==result.value,(label,'EAX',source,result.value)
 pops={0x4ce9a0:4,0x4cf0a0:4,0x4cf160:4,0x4cf940:4,0x4cf9d0:4,0x4cf800:4,0x4f5e1e:12,0x4f667d:4,0x4cf8a0:4,0x4cf280:4}.get(f,0);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+pops
 calls+=1;eventCount+=len(events[0]);return result.value

#Read-only stable peer library: its public4c89e0/4c89f0 and numbersRemoveAll
#execute the recovered source bodies, not a guessed empty-list adapter.
import shutil
peerLibrary=WORK/'libFrozenResults.dylib'
if not peerLibrary.exists():shutil.copyfile(ROOT/'work/booty-results-agent/libResults.dylib',peerLibrary)
resultsLib=C.CDLL(str(peerLibrary))
class ResultsContext(C.Structure):_fields_=[('scene',Host),('progression',C.c_void_p),('numbers',C.c_void_p),('actors',C.c_void_p)]+[(n,U)for n in('composeBase','composeNumbers','composeScene','composeAnimation','composeImages','maximum','fault')]
class ResultsCall(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('bufferSizes',U*3)]
ResultsDep=C.CFUNCTYPE(U,C.POINTER(ResultsContext),C.POINTER(ResultsCall),C.c_void_p)
class NumberContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(U))]+[(n,U)for n in('composeAnimation','composeImages','composeHierarchy','composeFormatting','fault')]
numberGlobals=(U*13)();numberContext=NumberContext(context.scene,numberGlobals,0,0,0,0,0);resultsContext=ResultsContext(context.scene,None,C.cast(C.pointer(numberContext),C.c_void_p),None,0,1,0,0,0,1000000,0)
resultsLib.claw_booty_results_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(ResultsContext),ResultsDep,C.c_void_p,C.POINTER(U)];resultsLib.claw_booty_results_entry.restype=U
@ResultsDep
def resultsDependency(_,ep,user):
 q=ep.contents;a=list(q.arguments[:q.count]);record(q.function,q.receiver,a,True,q.mask,[tuple((U*(q.bufferSizes[i]//4)).from_address(q.buffers[i]))for i in range(q.buffersCount)])
 try:return effect(q.function,q.receiver,a,True)
 except Exception as error:errors.append(error);return 0
rawLifecycleDependency=lifecycleDependency
@LifecycleDep
def lifecycleDependency(cp,ep,user):
 q=ep.contents
 if q.function in(0x4c89e0,0x4c89f0):
  resultsContext.scene=context.scene;numberContext.scene=context.scene;resultsContext.fault=numberContext.fault=0;out=U()
  assert resultsLib.claw_booty_results_entry(q.function,q.receiver,q.arguments,q.count,C.byref(resultsContext),resultsDependency,None,C.byref(out)) and not resultsContext.fault,(q.function,resultsContext.fault,errors)
  return out.value
 return rawLifecycleDependency(cp,ep,user)

#Optional frozen audio/world contexts for whole real default scene slots.
class AudioContext(C.Structure):_fields_=[('scene',Host),('maximum',U),('fault',U)]
class AudioCall(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*6),('deviceMethod',U),('output',C.POINTER(U))]
AudioDep=C.CFUNCTYPE(U,C.POINTER(AudioContext),C.POINTER(AudioCall),C.c_void_p)
audioContext=AudioContext(context.scene,1000000,0);lifecycle.audio=C.cast(C.pointer(audioContext),C.c_void_p)
class ArrayContext(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('compose','handler','fault','newMode','threshold','heapHandle','heapAlloc')]
class WorldContext(C.Structure):_fields_=[('scene',Host),('arrays',C.POINTER(ArrayContext)),('spatial',U),('fault',U)]
class WorldArgs(C.Structure):_fields_=[('words',U*4),('count',U)]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('name',C.c_char_p),('size',C.POINTER(U)),('temporary',C.POINTER(U))]
WorldDep=C.CFUNCTYPE(U,C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
arrays=ArrayContext(context.scene);worldContext=WorldContext(context.scene,C.pointer(arrays),0,0);lifecycle.world=C.cast(C.pointer(worldContext),C.c_void_p)
lib.claw_world_file_entry.argtypes=[U,U,WorldArgs,C.POINTER(WorldContext),WorldDep,C.c_void_p,C.POINTER(U)];lib.claw_audio_manager_lifecycle_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(AudioContext),AudioDep,C.c_void_p,C.POINTER(U)]
AUDIO=BASE+0x8600;WORLD=BASE+0x8700;CONTAINER=BASE+0x8900;REAL_RENDERER=BASE+0x8a00
postPrepare=prepare

def prepare(number=0):
 postPrepare(number);audioContext.scene=worldContext.scene=arrays.scene=context.scene;audioContext.fault=worldContext.fault=arrays.fault=0
 H=Host

def defaultScene():
 prepare();put(SCENE+4,[HOLDER,CONTAINER,REAL_RENDERER,IMAGE_CONTROLLER,LOGIC_CONTROLLER,PALETTE_CONTROLLER,MANAGER,AUDIO,WORLD,SOUND_CONTROLLER,ANIMATION_CONTROLLER])
 put(HOLDER,[0x513c68,0,0,SCENE,0,0,0]);put(CONTAINER,[0x513c20,0,0,SCENE,0x5107bc,0,0,0,0,0,10]);put(REAL_RENDERER,[0x513be8,0,0,SCENE,0x5107bc,0,0,0,0,0,10]);put(AUDIO,[0x513514]+[0]*31)
 out=U();wa=WorldArgs((U*4)(SCENE,0,0,0),3);assert lib.claw_world_file_entry(0x4cace0,WORLD,wa,C.byref(worldContext),WorldDep(),None,C.byref(out)) and not worldContext.fault

class PaletteGlobals(C.Structure):_fields_=[('cooperative',U)]
class PaletteContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(PaletteGlobals)),('scratch',U),('compose',U),('maximum',U),('fault',U)]
PaletteDep=C.CFUNCTYPE(U,C.POINTER(PaletteContext),C.POINTER(Call),C.c_void_p)
pg=PaletteGlobals();pc=PaletteContext(context.scene,C.pointer(pg),0,1,1000000,0);lifecycle.palette=C.cast(C.pointer(pc),C.c_void_p)
lib.claw_palette_resource_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(PaletteContext),PaletteDep,C.c_void_p,C.POINTER(U)]
PAL_WRAPPER=BASE+0x30800;PAL_INTERFACE=BASE+0x30900;PAL_VTABLE=BASE+0x30a00;PAL_DATA=BASE+0x31000
COUNTS[0x700014]=(5,20)
oldEffect=effect

def effect(f,r,a,native,buffers=()):
 if f==0x700014:put(a[3],[PAL_INTERFACE],native);return 0
 return oldEffect(f,r,a,native,buffers)
@PaletteDep
def paletteDependency(_,ep,user):
 q=ep.contents;a=list(q.arguments[:q.count]);normalized=[tuple(q.buffers[i][:q.sizes[i]//4])for i in range(q.bufferCount)];record(q.function,q.receiver,a,True,q.localMask,normalized);return effect(q.function,q.receiver,a,True)
oldPrepare2=prepare

def prepare(number=0):
 oldPrepare2(number);pc.scene=context.scene;pc.fault=0;pg.cooperative=g.cooperative

def displayStartup():
 global calls,eventCount
 sync();events[0].clear();events[1].clear();out=U();a=(U*4)(640,480,8,0);assert lib.claw_scene_display_entry(0x4ca6f0,HOLDER,a,4,C.byref(display),displayDependency,None,C.byref(out)) and out.value==1
 assert m.call(0x4ca6f0,HOLDER,struct.pack('<4I',640,480,8,0))==out.value
 assert snapshot(True)==snapshot(False)and events[0]==events[1]
 calls+=1;eventCount+=len(events[0])

def realPalette(raw):
 global calls,eventCount
 put(VT+0x14,[0x700014]);put(PAL_INTERFACE,[PAL_VTABLE]);put(PAL_WRAPPER,[0x513d78,0,0,SCENE,0]);put(PAL_DATA,list(struct.unpack('<192I',raw)));sync();events[0].clear();events[1].clear();out=U();pc.fault=0;pg.cooperative=g.cooperative;a=(U*2)(PAL_DATA,0)
 assert lib.claw_palette_resource_entry(0x4d65a0,PAL_WRAPPER,a,2,C.byref(pc),paletteDependency,None,C.byref(out)) and not pc.fault
 assert m.call(0x4d65a0,PAL_WRAPPER,struct.pack('<2I',PAL_DATA,0))==out.value
 if snapshot(True)!=snapshot(False)or events[0]!=events[1]:
  print('paletteMemory',[(hex(BASE+i),hex(heap[i]),hex(x))for i,x in enumerate(bytes(m.u.mem_read(BASE,SIZE)))if heap[i]!=x][:16]);print('palGlobal',[(hex(GLOBAL_START+i),hex(a),hex(b))for i,(a,b)in enumerate(zip(globalBytes(True),globalBytes(False)))if a!=b][:16]);print('palEvents',[(i,a[0],b[0],a[1]==b[1])for i,(a,b)in enumerate(zip(*events))if a!=b][:2]);raise AssertionError(('realPaletteLoad',len(events[0]),len(events[1])))
 calls+=1;eventCount+=len(events[0]);mapFixture(PALETTE_CONTROLLER+16,1);put(ASSOC1+12,[PAL_WRAPPER]);put(ASSOC3+12,[0])
#Actual source4cea10 failure produces ownership fixtures. Initialization itself
#stays frozen and is not claimed as a new native implementation here.
COUNTS[0x4cb040]=(2,8)
oldEffect2=effect

def effect(f,r,a,native,buffers=()):
 if f==0x4cb040:return 0
 return oldEffect2(f,r,a,native,buffers)

def actualFailedInitialization():
 prepare();sync();events[1].clear();assert m.call(0x4cea10,SCENE,struct.pack('<5I',0x12345,640,480,8,0),max_instructions=3000000)==0
 assert get(SCENE+56,1,False)[0]==1007
 C.memmove(C.addressof(heap),bytes(m.u.mem_read(BASE,SIZE)),SIZE);C.memmove(C.addressof(image),bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE)),GLOBAL_SIZE)
 g.device=get(0x541398,1,False)[0];g.cooperative=get(0x541374,1,False)[0];g.shifts[:]=get(0x54135c,3,False);g.reductions[:]=get(0x541368,3,False)
 nextAllocation[0]=nextAllocation[1];allocated[0]=dict(allocated[1]);freed[0]=list(freed[1])
