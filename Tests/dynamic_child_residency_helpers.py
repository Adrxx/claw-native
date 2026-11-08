"""Private original outer-frame oracle; frozen populated-grid fixture adapted."""
import argparse,ctypes as C,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/dynamic-child-residency-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');opts=p.parse_args()
SOURCES=['ActorInteractions','ElementalProjectileRuntime', 'PlayerProjectileRuntime', 'BulletLogic', 'GenericEnemy', 'GenericEnemyStates', 'PlayerPhysics', 'PlayerLocomotion', 'PlayerAirStates', 'PlayerInitialization', 'PlayerEngine', 'PlayerDamage', 'CollisionResponse', 'TileCollision', 'RawTileDescriptionRuntime', 'ActorAnimationRuntime', 'AnimationEngine', 'AnimationOperations', 'ActorResourceBindings', 'PickupPointsRuntime', 'ActorDestruction', 'SpriteGeometry', 'SceneActorRuntime', 'WorldObjectRuntime', 'GameTiming', 'PIDRaster', 'PIDSurfaceRaster', 'PIDBlitter', 'WorldFileRuntime', 'WorldPlaneRuntime', 'CArrayRuntime', 'SpatialGridRuntime', 'SceneCameraRuntime', 'LogicStateRegistry', 'PlayerRangedHelpersRuntime', 'GameFrameRuntime', 'FlareRuntime', 'GameImageRuntime', 'StackedActorLifecycleRuntime', 'PowerupObjectRuntime', 'ItemPickupRuntime', 'PlayerPowerupRuntime', 'PlayerInputDispatch', 'SinglePlayerSceneRuntime', 'AudioEvents', 'CRTRandomRuntime', 'WorldLootRuntime', 'AmbientAudioBackendRuntime']
LIBNAME='libDynamicChildResidency.dylib'
if not (WORK/LIBNAME).exists() or any((ROOT/'Sources'/f'{n}.cpp').stat().st_mtime>(WORK/LIBNAME).stat().st_mtime for n in SOURCES):
 subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in SOURCES],'-o',str(WORK/LIBNAME)],check=True)
lib=C.CDLL(str(WORK/LIBNAME))
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Args(C.Structure):_fields_=[('words',C.c_uint32*8),('count',C.c_uint32)]
lib.claw_spatial_grid_entry.argtypes=[C.c_uint32,C.c_uint32,Args,Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_spatial_grid_entry.restype=C.c_uint32
lib.claw_scene_actor_insert.argtypes=[C.c_uint32,C.c_uint32,Host,C.POINTER(C.c_uint32)]
m=OriginalV10(opts.exe);u=m.u;u.mem_map(0,4096);m.executed.clear();BASE,SIZE=0x1000000,0x60000;heap=(C.c_uint8*SIZE)();rng=random.Random(0x4d4890)
PLANE,GRID,PAR,WORLD,CONTAINER,RECT,PAIRS,RECORD=[BASE+i*0x1000 for i in range(1,9)]
LAYERS=[BASE+0x9000+i*0x100 for i in range(3)];ACTORS=[BASE+0xa000+i*0x200 for i in range(12)];LOGICS=[BASE+0xc000+i*0x200 for i in range(12)];CELLS=[BASE+0xe000+i*0x1000 for i in range(3)]
OWNER,MGR,CFG,WINDOW,DEVICE,INPUT,PLAYER,PL,PV,CAMERA,CL=[BASE+0x16000+i*0x1000 for i in range(11)]
ALLOC_START=BASE+0x22000;CALLBACK,OVERRIDE,RECT_SHIM,CLOCK_SERVICE,KEY_SERVICE=0x10fd000,0x10fd010,0x10fd020,0x10fd080,0x10fd090;VT=BASE+0x11500
# Exact pure SetRect memory shim; no UI or platform input is adapted here.
u.mem_write(RECT_SHIM,b'\x8b\x4c\x24\x04'+b''.join(b'\x8b\x44\x24'+bytes([8+i])+b'\x89\x41'+bytes([i])for i in(0,4,8,12))+b'\xb8\x01\0\0\0\xc2\x14\0')
m.write_words(0x546d5c,[RECT_SHIM])
native=True;events=[];nextAllocation=ALLOC_START;allocationIndex=0;failAllocation=-1;policy=0;recordIndex=0;calls=event_count=0;frameMode=False;sceneGlobals=None;stage=None;cameraGlobals=None;clockValue=1000;fullDestruction=False;staticSpans={};callbackErrors=[]
class DestructionGlobals(C.Structure):_fields_=[('holderActorToken',C.c_uint32),('heldActorToken',C.c_uint32),('emptyStringToken',C.c_uint32)]
destructionGlobals=DestructionGlobals(0,0,0x52e1c4)
lib.claw_actor_destruction_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(DestructionGlobals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
class Frame(C.Structure):_fields_=[('nowMilliseconds',C.c_uint32),('deltaMilliseconds',C.c_uint32)]
class SceneGlobals(C.Structure):_fields_=[('initializationFlags',C.c_uint32),('deletionArray',C.c_uint32*5),('reorderArray',C.c_uint32*5),('animation',Frame)]
class Stage(C.Structure):_fields_=[('stage',Frame),('accumulatedMilliseconds',C.c_uint32),('playerToken',C.c_uint32)]
cameraNames=['playerToken','inputDeviceToken','inputMappingToken','stageDelta','menuBlocked','animationNow','animationDelta','forcedX','forcedY','detachedMode','shakeUntil','detachedOwnerToken'];cameraAddresses=[0x537e88,0x537200,0x537204,0x53720c,0x537258,0x5430c8,0x5430c4,0x52be14,0x52be18,0x53c25c,0x53c260,0x53c264]
class CameraGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in cameraNames]
class PlatformCall(C.Structure):_fields_=[('importSlot',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('bufferToken',C.c_uint32),('buffer',C.POINTER(C.c_uint32)),('bufferWords',C.c_uint32)]
Platform=C.CFUNCTYPE(C.c_uint32,C.c_void_p,PlatformCall)
class CameraHost(C.Structure):_fields_=[('heap',Host),('platformContext',C.c_void_p),('platform',Platform)]
class Interaction(C.Structure):_fields_=[('token',C.c_uint32)]+[(n,C.c_uint32*count)for n,count in(('actor',128),('primary',93),('secondary',93),('contact',93))]
class InteractionCall(C.Structure):_fields_=[(n,C.c_uint32)for n in('function','actorToken','peerToken','logicToken','kind')]
InteractionDependency=C.CFUNCTYPE(None,C.POINTER(Interaction),C.c_size_t,C.POINTER(InteractionCall),C.c_void_p)
lib.claw_actor_interactions.argtypes=[C.POINTER(Interaction),C.c_size_t,InteractionDependency,C.c_void_p]
lib.claw_scene_stage_run.argtypes=[C.c_uint32,C.POINTER(Stage),C.POINTER(SceneGlobals),C.c_uint32,Host,C.POINTER(C.c_uint32)]
lib.claw_scene_camera_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(CameraGlobals),CameraHost,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
def words(t,n):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def cameraValue(n):
 if not native:return m.read_words(cameraAddresses[cameraNames.index(n)],1)[0]
 if n=='stageDelta':return stage.stage.deltaMilliseconds
 if n=='animationNow':return sceneGlobals.animation.nowMilliseconds
 if n=='animationDelta':return sceneGlobals.animation.deltaMilliseconds
 return getattr(cameraGlobals,n)
def snapshot():
 raw=bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))
 if frameMode:
  raw+=bytes(sceneGlobals)+bytes(stage)if native else struct.pack('<17I',m.read_words(0x5430d0,1)[0],*m.read_words(0x5430f0,5),*m.read_words(0x5430d8,5),*m.read_words(0x5430c8,1),*m.read_words(0x5430c4,1),*m.read_words(0x537208,3),m.read_words(0x537e88,1)[0])
  raw+=struct.pack('<12I',*[cameraValue(n)for n in cameraNames])
 return raw
def log(e):events.append((e,snapshot()))
def fb(f):return struct.unpack('<I',struct.pack('<f',f))[0]
def allocateEffect(n):
 global nextAllocation,allocationIndex
 log(('allocate',n));allocationIndex+=1
 if policy==5 and n==0x70:
  put(PLANE+0x30,[2048,2048]);put(WORLD+0xb0,[8,8,16,16,32,32,80,80,160,160,240,240]);put(PAR+8,[RECT])
 if allocationIndex==failAllocation:return 0
 t=nextAllocation;nextAllocation+=(n+15)&~15;assert nextAllocation<=BASE+SIZE;return t
def dependency(fn,receiver,args):
 global recordIndex
 log(('call',fn,receiver,args))
 if fn==CALLBACK:
  actor=args[0];logic=words(actor+0x6c,1)[0]
  if policy==1:put(logic+0x1c,[177])
  if policy==2:put(actor+8,[words(actor+8,1)[0]|2])
  if policy==3:put(actor+0x98,[17,21])
  return 1
 if fn==OVERRIDE:return 1
 if fn==0x4c9be0:
  if policy==2:put(receiver+8,[words(receiver+8,1)[0]|2])
  return receiver
 if fn==0x4d17e0:
  recordIndex+=1
  return 0 if policy==4 and recordIndex==2 else 284+recordIndex*4
 raise AssertionError(('unknown dependency',hex(fn),hex(receiver),args))
@Lookup
def lookup(_,t,n):
 for start,count in ((BASE+0x13000,86),(BASE+0x14000,19)):
  if start<=t<start+0x1000 and t+n*4>start+count*4:return None
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if fullDestruction and 0x500000<=t and t+n*4<=0x520000:
  key=(t,n)
  if key not in staticSpans:staticSpans[key]=(C.c_uint32*n)(*m.read_words(t,n))
  return C.addressof(staticSpans[key])
 return None
@Allocate
def allocate(_,n):return allocateEffect(n)
@Free
def free(_,t):log(('free',t))
def baseInvoke(_,c):
 if fullDestruction and c.function==0x4c9be0:
  fault=C.c_uint32();result=C.c_uint32();assert lib.claw_actor_destruction_entry(c.function,c.receiver,c.arguments[0],C.byref(destructionGlobals),host,C.byref(fault),C.byref(result))and not fault.value;return result.value
 if frameMode:
  if c.function in(0x4d1fd0,0x4d2000):return nativeEntry(c.function,c.receiver)
  if c.function in(0x46c860,0x486240):
   for n in('stageDelta','animationNow','animationDelta'):setattr(cameraGlobals,n,cameraValue(n))
   fault=C.c_uint32();result=C.c_uint32();receiver=c.receiver if c.function==0x46c860 else c.arguments[0]
   assert lib.claw_scene_camera_entry(c.function,receiver,0,0,C.byref(cameraGlobals),cameraHost,C.byref(fault),C.byref(result))and not fault.value
   return result.value
  if c.function==0x4c9390:return interactions(c.receiver)
 return dependency(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]))
@Clock
def clock(_):log(('clock',));return clockValue
invoke=Invoke(baseInvoke)
host=Host(None,lookup,allocate,free,invoke,clock)
@Platform
def platform(_,c):log(('platform',c.importSlot,tuple(c.arguments[:c.argumentCount]),c.bufferToken,c.bufferWords));assert c.importSlot==0x546ce4;return 0
cameraHost=CameraHost(host,None,platform)
@InteractionDependency
def interactionCallback(actors,count,call,user):raise AssertionError('fixture has no eligible damage/contact masks')
def interactions(container):
 order=[];at=words(container+20,1)[0]
 while at:node=words(at,3);order.append(node[2]);at=node[0]
 records=(Interaction*len(order))()
 for i,t in enumerate(order):
  records[i].token=t;records[i].actor[:]=words(t,128);logic=records[i].actor[27]
  if logic:records[i].primary[:]=words(logic,93)
 assert lib.claw_actor_interactions(records,len(order),interactionCallback,None)
 for i,t in enumerate(order):
  put(t,list(records[i].actor));logic=records[i].actor[27]
  if logic:put(logic,list(records[i].primary))
 return 0
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def originalHook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4f63ec:returned(0,allocateEffect(m.read_words(sp+4,1)[0]))
 elif address==0x4f6428:log(('free',m.read_words(sp+4,1)[0]));returned(0)
 elif address==CLOCK_SERVICE:log(('clock',));returned(0,clockValue)
 elif address==KEY_SERVICE:log(('platform',0x546ce4,tuple(m.read_words(sp+4,1)),0,0));returned(4,0)
 elif address in(CALLBACK,OVERRIDE,0x4c9be0,0x4d17e0):
  if fullDestruction and address==0x4c9be0:return
  receiver=0 if address==CALLBACK else uc.reg_read(UC_X86_REG_ECX);args=tuple(m.read_words(sp+4,1));returned(4 if address!=CALLBACK else 0,dependency(address,receiver,args))
u.hook_add(UC_HOOK_CODE,originalHook)
def reset():
 global native,events,nextAllocation,allocationIndex,failAllocation,policy,recordIndex,frameMode,fullDestruction
 native=True;nextAllocation=ALLOC_START;allocationIndex=0;failAllocation=-1;policy=0;recordIndex=0;events=[];frameMode=False;fullDestruction=False
 seed=(C.c_uint32*(SIZE//4)).from_buffer(heap);seed[:]=[rng.getrandbits(32)for _ in range(SIZE//4)]
 put(PLANE,[0]*45);put(PLANE+0xc,[PAR]);put(PLANE+0x10,[fb(400),fb(300)]);put(PLANE+0x30,[1024,768]);put(PLANE+0xb0,[GRID]);put(PAR,[0]*12);put(PAR+8,[CONTAINER]);put(PAR+0x24,[WORLD]);put(WORLD,[0]*56);put(WORLD+0xb0,[128,128,256,128,256,256,640,480,800,600,1200,800]);put(RECT,[0,0,1023,767]);put(PAIRS,[128,128,256,128,256,256,640,480,800,600,1200,800]);put(CONTAINER,[0x513c20,0,0,PAR,0x5107bc,0,0,0,0,0,10]);put(GRID,[CONTAINER,*LAYERS,*([0]*24)]);put(GRID+0x10,[0,0,639,479,0,0,1199,799,0,0,799,599,320,240,400,300,600,400,0,0,1023,767,0xffffa932,0xffffa932]);put(VT,[0,0,0,0,0,OVERRIDE])
 for i,l in enumerate(LAYERS):
  put(l,[0x513db0,1,0,9,7,7,7,63,1023,767,0,0,1023,767,128,128,CELLS[i]+4]);put(CELLS[i],[63]+[0]*126)
 for i,a in enumerate(ACTORS):
  put(a,[0]*128);put(a,[0x5137f0,i,0x40000,PAR]);put(a+0x4c,[100+i*60,100+i*35]);put(a+0x64,[i*10,0,LOGICS[i]]);put(a+0x88,[0,0,0,0,100+i*60,100+i*35,a]);put(LOGICS[i],[0]*93);put(LOGICS[i]+0x10,[CALLBACK,0,0,24])
 return
def nativeEntry(fn,receiver,args=()):
 fault=C.c_uint32();result=C.c_uint32();v=Args((C.c_uint32*8)(*args),len(args));assert lib.claw_spatial_grid_entry(fn,receiver,v,host,C.byref(fault),C.byref(result))and not fault.value,(hex(fn),'nativefault',fault.value);return result.value
def insert(actor):
 f=C.c_uint32();lib.claw_scene_actor_insert(CONTAINER,actor,host,C.byref(f));assert not f.value
def compare(fn,receiver,label,args=(),returns=True):
 global native,events,nextAllocation,allocationIndex,recordIndex,calls,event_count
 native=True;before=snapshot();saved=(nextAllocation,allocationIndex,recordIndex);events=[];result=nativeEntry(fn,receiver,args);expected=snapshot();expectedEvents=list(events);after=(nextAllocation,allocationIndex,recordIndex)
 nextAllocation,allocationIndex,recordIndex=saved;events=[];native=False;u.mem_write(BASE,before);m.write_words(0,[0x12345678]);m.write_words(0x546d5c,[RECT_SHIM]);ret=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*[a&0xffffffff for a in args]))
 if snapshot()!=expected:
  actual=snapshot();diff=[(hex(BASE+i),hex(struct.unpack_from('<I',actual,i)[0]),hex(struct.unpack_from('<I',expected,i)[0]))for i in range(0,SIZE,4)if actual[i:i+4]!=expected[i:i+4]];print(label,'diff',diff[:40]);raise AssertionError((label,'wholeheap'))
 if returns:assert ret==result,(label,'return',ret,result)
 if events!=expectedEvents:
  print(label,'events original',[e for e,s in events],'native',[e for e,s in expectedEvents]);print([(i,a[0],b[0],a[1]==b[1])for i,(a,b)in enumerate(zip(events,expectedEvents))if a!=b][:5]);raise AssertionError((label,'orderedevents'))
 assert after==(nextAllocation,allocationIndex,recordIndex);assert m.read_words(0,1)==[0x12345678]
 native=True;calls+=1;event_count+=len(events)

def prepareFrame():
 global frameMode,sceneGlobals,stage,cameraGlobals,clockValue
 reset();nativeEntry(0x4cb040,WORLD,(640,480));put(PLANE+0xb0,[0]);nativeEntry(0x4d1620,PLANE,(RECORD,0))
 for i,a in enumerate(ACTORS[:9]):
  put(a+8,[0x40000|[0,0x800000,0x1000000][i%3]]);nativeEntry(0x4d51a0,words(PLANE+0xb0,1)[0],(a,))
 put(OWNER,[0]*474);put(OWNER+4,[MGR]);put(OWNER+12,[PAR]);put(MGR,[0]*20);put(MGR+4,[WINDOW]);put(MGR+0x4c,[CFG]);put(CFG,[0]*13);put(WINDOW,[0,123]);put(DEVICE,[0]*146);put(INPUT,[0]*29);put(INPUT,[DEVICE]);put(PLAYER,[0]*128);put(PLAYER+0xc,[PAR]);put(PLAYER+0x4c,[400,300]);put(PLAYER+0x6c,[PL]);put(PL,[0]*93);put(PL+0x14,[PV]);put(PL+0x1c,[24]);put(PV,[0]*78);put(CAMERA,[0]*128);put(CAMERA,[0x5137f0,0,0,PAR]);put(CAMERA+0x64,[9999,0,CL]);put(CL,[0]*93);put(CL+0x10,[0x486240]);insert(CAMERA)
 put(WORLD+0x38,[BASE+0x11400,1]);put(BASE+0x11400,[PLANE]);put(WORLD+0x5c,[PLANE,0]);put(PLANE+8,[1]);put(PLANE+0x50,[0,0,639,479]);put(PLANE+0x70,[640,480,320,240]);
 clockValue=1000;sceneGlobals=SceneGlobals(3,(C.c_uint32*5)(0x5108fc,0,0,0,0),(C.c_uint32*5)(0x5108fc,0,0,0,0),Frame(984,16));stage=Stage(Frame(1000,16),2000,PLAYER);cameraGlobals=CameraGlobals(PLAYER,DEVICE,INPUT,16,0,984,16,0xffffffff,0xffffffff,0,0,0);frameMode=True
def compareFrame(fn,label):
 global native,events,nextAllocation,allocationIndex,recordIndex,calls,event_count
 native=True;before=bytes(heap);cg=bytes(cameraGlobals);sg=bytes(sceneGlobals);st=bytes(stage);saved=(nextAllocation,allocationIndex,recordIndex);events=[];fault=C.c_uint32();count=lib.claw_scene_stage_run(OWNER,C.byref(stage),C.byref(sceneGlobals),int(fn==0x46ad70),host,C.byref(fault));assert not fault.value,(label,'fault',fault.value);expected=snapshot();expectedEvents=list(events);after=(nextAllocation,allocationIndex,recordIndex)
 native=False;nextAllocation,allocationIndex,recordIndex=saved;events=[];u.mem_write(BASE,before);m.write_words(0,[0x12345678]);v=struct.unpack('<13I',sg);m.write_words(0x5430d0,v[:1]);m.write_words(0x5430f0,v[1:6]);m.write_words(0x5430d8,v[6:11]);m.write_words(0x5430c8,[v[11]]);m.write_words(0x5430c4,[v[12]]);v=struct.unpack('<4I',st);m.write_words(0x537208,v[:3]);m.write_words(0x537e88,v[3:]);
 for a,v in zip(cameraAddresses,struct.unpack('<12I',cg)):m.write_words(a,[v])
 # Shared stage/animation clocks override stale copied camera wrapper fields.
 v=struct.unpack('<13I',sg);m.write_words(0x5430c8,[v[11]]);m.write_words(0x5430c4,[v[12]]);m.write_words(0x53720c,[struct.unpack('<4I',st)[1]]);m.write_words(0x546df0,[CLOCK_SERVICE]);m.write_words(0x546ce4,[KEY_SERVICE]);m.write_words(0x546d5c,[RECT_SHIM]);ret=m.call(fn,OWNER)
 if snapshot()!=expected:
  actual=snapshot();diff=[(hex(BASE+i),hex(struct.unpack_from('<I',actual,i)[0]),hex(struct.unpack_from('<I',expected,i)[0]))for i in range(0,len(actual),4)if actual[i:i+4]!=expected[i:i+4]];print(label,'frame diff',diff[:40]);raise AssertionError((label,'fullframeheap'))
 if fn==0x46ad70:assert ret==count
 if events!=expectedEvents:
  print(label,'frame events original',[e for e,s in events],'native',[e for e,s in expectedEvents]);print([(i,a[0],b[0],a[1]==b[1])for i,(a,b)in enumerate(zip(events,expectedEvents))if a!=b][:5]);raise AssertionError((label,'fullframeevents'))
 assert after==(nextAllocation,allocationIndex,recordIndex);assert m.read_words(0,1)==[0x12345678];native=True;calls+=1;event_count+=len(events)

class WorldState(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class WorldContext(C.Structure):_fields_=[(n,C.c_uint32)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('worldWidth',C.c_int32),('worldHeight',C.c_int32),('registryToken',C.c_uint32),('layerTokens',C.c_uint32*3)]+[(n,C.c_uint32)for n in('entryToken','entryCallback','entryFlags')]
class WorldCall(C.Structure):_fields_=Call._fields_+[('text',C.c_char_p)]
class WorldInfo(C.Structure):_fields_=[('consumed',C.c_uint32),('created',C.c_uint32)]
WorldDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDependency,C.c_void_p,C.POINTER(WorldInfo)]
@WorldDependency
def profileDependency(state,context,event,user):
 s,c,e=state.contents,context.contents,event.contents
 if e.function==0x4f6286:
  assert e.text in(b'Rat',b'Officer');c.entryToken=BASE+0x11600;c.entryCallback=CALLBACK;c.entryFlags=0;return c.entryToken
 if e.function==0x4f4630:
  put(c.actorToken,list(s.actor));put(c.logicToken,list(s.logic));nativeEntry(0x4f4630,e.receiver,(e.arguments[0],));s.actor[:]=words(c.actorToken,128);s.logic[:]=words(c.logicToken,93)
 else:assert e.function in(0x4c7970,0x4c7900,0x4c79e0,0x4c7a40)
 return 1
def sourceProfile(data,index):
 actor,logic=ACTORS[index],LOGICS[index];grid=words(PLANE+0xb0,1)[0];layers=words(grid+4,3);state=WorldState();state.actor[:]=words(actor,128);state.logic[:]=words(logic,93);context=WorldContext(PAR,actor,logic,WORLD,24576,6144,0,(C.c_uint32*3)(*layers),0,CALLBACK,0);info=WorldInfo();raw=(C.c_uint8*len(data)).from_buffer_copy(data)
 assert lib.claw_world_object_load(raw,len(data),C.byref(state),C.byref(context),profileDependency,None,C.byref(info))==len(data)and info.created
 put(actor,list(state.actor));put(logic,list(state.logic))

# Complete outer callbacks: the frozen populated grid remains real. These
# services are the explicit renderer/audio/UI or extra gameplay boundaries.
class ClockState(C.Structure):_fields_=[(n,C.c_uint32)for n in('nowMilliseconds','deltaMilliseconds','pacedFrameStart','countdown','countdownReload')]
class GameContext(C.Structure):_fields_=[('host',CameraHost),('clock',C.POINTER(ClockState)),('stage',C.POINTER(Stage)),('actors',C.POINTER(SceneGlobals)),('camera',C.POINTER(CameraGlobals))]+[(n,C.c_uint32)for n in('composeStage','composeCamera','composeSpatial','fault')]
class GameCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4)]
GameDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(GameContext),C.POINTER(GameCall),C.c_void_p)
lib.claw_game_frame_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(GameContext),GameDependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_game_frame_entry.restype=C.c_uint32;lib.claw_game_frame_defaults.argtypes=[C.POINTER(GameContext)]
STATE_VT,RENDERER,RENDERER_VT,SURFACE,DEVICE_TARGET,OUTPUT,AUDIO=[BASE+0x11700+i*0x100 for i in range(7)]
PRESENT,OTHER_STATE=0x10fd100,0x10fd110
clockState=ClockState();gameContext=GameContext();outerPolicy=0;residency_calls=[];clockSamples=[];clockSampleIndex=0
oldSnapshot=snapshot;oldLog=log
def snapshot():return oldSnapshot()+(bytes(clockState)if native else struct.pack('<5I',*m.read_words(0x541328,5)))
def log(e):
 global clockSampleIndex,clockValue
 oldLog(e)
 if e==('clock',)and clockSamples:
  assert clockSampleIndex<len(clockSamples),'Scripted clock exhausted';clockValue=clockSamples[clockSampleIndex];clockSampleIndex+=1
def outerDependency(fn,receiver,args):
 log(('call',fn,receiver,args))
 if fn==0x4025c0:put(receiver+4,list(args));return 1
 if fn==0x4cb9b0:
  if outerPolicy==1:put(ACTORS[0]+0x4c,[9000,9000]);put(ACTORS[0]+0x98,[9000,9000])
  if outerPolicy==3:put(WORLD+0x5c,[0])
  return 1
 if fn==PRESENT:
  put(receiver+4,list(args));return 1
 if fn==0x46c2c0:
  if outerPolicy==2:put(MGR+0x6c,[3]);put(ACTORS[0]+8,[words(ACTORS[0]+8,1)[0]|2])
  return 1
 if fn==0x4b98b0:put(receiver,[args[0]]);return 1
 if fn==0x4774f0:
  if outerPolicy==4:
   if native:stage.stage.deltaMilliseconds=37
   else:m.write_words(0x53720c,[37])
  return 1
 if fn in(0x477840,0x478290,0x4224f0):return 1
 if fn==OTHER_STATE:put(MGR+0x6c,[9]);return 1
 raise AssertionError(('Unrepresented outer service',hex(fn),hex(receiver),args))
def baseGameDependency(_,e,user):
 e=e.contents
 if e.function==0x4c9390:return interactions(e.receiver)
 if e.function in(CALLBACK,OVERRIDE,0x4c9be0,0x4d17e0):return dependency(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]))
 return outerDependency(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]))
gameDependency=GameDependency(baseGameDependency)
def outerHook(uc,address,size,user):
 if address in(0x4d1fd0,0x4d2000):residency_calls.append((address,snapshot()));return
 if address not in(0x4025c0,0x4cb9b0,PRESENT,0x46c2c0,0x4b98b0,0x4774f0,0x477840,0x478290,0x4224f0,OTHER_STATE):return
 n=2 if address in(0x4025c0,0x4cb9b0,PRESENT)else 1 if address in(0x4b98b0,0x478290,0x4224f0)else 0;sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);args=tuple(m.read_words(sp+4,n));returned(n*4,outerDependency(address,receiver,args))
u.hook_add(UC_HOOK_CODE,outerHook)
def prepareOuter(fn=0x46ac30):
 global clockState,gameContext,outerPolicy,clockSamples,clockSampleIndex
 prepareFrame();outerPolicy=0;clockSamples=[];clockSampleIndex=0
 # Verified original Level1 main-plane extent, with actual default grid size
 # pairs from recovered world4cb040. This permits measured ordinary culling.
 put(PLANE+0x30,[24576,6144]);nativeEntry(0x4d1620,PLANE,(RECORD,0));grid=words(PLANE+0xb0,1)[0]
 for a in ACTORS[:9]:put(a+0x88,[0,0,0,0]);nativeEntry(0x4d51a0,grid,(a,))
 put(MGR,[0]*45);put(MGR+4,[WINDOW]);put(MGR+0x4c,[CFG]);put(MGR+0x5c,[AUDIO]);put(MGR+0x18,[0xffffffff,0,5,900,0]);put(MGR+0x2c,[OWNER]);put(MGR+0x6c,[2]);put(OWNER,[STATE_VT]);put(STATE_VT,[0]*6);put(STATE_VT+0x14,[fn]);put(PAR+4,[SURFACE]);put(PAR+0xc,[RENDERER]);put(SURFACE,[0]*7);put(SURFACE+0x10,[DEVICE_TARGET,123,8]);put(DEVICE_TARGET,[0]*12);put(DEVICE_TARGET+0x2c,[OUTPUT]);put(OUTPUT,[0]);put(RENDERER,[RENDERER_VT,0,0]);put(RENDERER_VT,[0]*14);put(RENDERER_VT+0x34,[PRESENT]);put(AUDIO,[0]*4)
 clockState=ClockState(984,16,0,10,25);gameContext=GameContext(cameraHost,C.pointer(clockState),C.pointer(stage),C.pointer(sceneGlobals),C.pointer(cameraGlobals),0,0,0,0);lib.claw_game_frame_defaults(C.byref(gameContext))
def compareOuter(fn,label,receiver=None):
 global native,events,nextAllocation,allocationIndex,recordIndex,calls,event_count,clockSampleIndex,clockValue
 if receiver is None:receiver=MGR if fn==0x428b60 else OWNER
 native=True;callbackErrors.clear();before=bytes(heap);cg=bytes(cameraGlobals);sg=bytes(sceneGlobals);st=bytes(stage);ck=bytes(clockState);saved=(nextAllocation,allocationIndex,recordIndex,clockSampleIndex,clockValue);events=[];residency_calls.clear();gameContext.fault=0;result=C.c_uint32();assert lib.claw_game_frame_entry(fn,receiver,C.byref(gameContext),gameDependency,None,C.byref(result))and not gameContext.fault,(label,'native fault',gameContext.fault);expected=snapshot();expectedEvents=list(events);after=(nextAllocation,allocationIndex,recordIndex,clockSampleIndex,clockValue)
 native=False;nextAllocation,allocationIndex,recordIndex,clockSampleIndex,clockValue=saved;events=[];u.mem_write(BASE,before);m.write_words(0,[0x12345678]);v=struct.unpack('<13I',sg);m.write_words(0x5430d0,v[:1]);m.write_words(0x5430f0,v[1:6]);m.write_words(0x5430d8,v[6:11]);m.write_words(0x5430c8,[v[11]]);m.write_words(0x5430c4,[v[12]]);v=struct.unpack('<4I',st);m.write_words(0x537208,v[:3]);m.write_words(0x537e88,v[3:]);m.write_words(0x541328,struct.unpack('<5I',ck))
 for a,v in zip(cameraAddresses,struct.unpack('<12I',cg)):m.write_words(a,[v])
 v=struct.unpack('<13I',sg);m.write_words(0x5430c8,[v[11]]);m.write_words(0x5430c4,[v[12]]);m.write_words(0x53720c,[struct.unpack('<4I',st)[1]]);m.write_words(0x546df0,[CLOCK_SERVICE]);m.write_words(0x546ce4,[KEY_SERVICE]);m.write_words(0x546d5c,[RECT_SHIM]);ret=m.call(fn,receiver)
 actual=snapshot()
 if actual!=expected:
  diff=[(hex(BASE+i),hex(struct.unpack_from('<I',actual,i)[0]),hex(struct.unpack_from('<I',expected,i)[0]))for i in range(0,len(actual),4)if actual[i:i+4]!=expected[i:i+4]];print(label,'outer diff',diff[:35]);raise AssertionError((label,'complete heap/globals'))
 if events!=expectedEvents:
  print(label,'outer calls original',[e for e,s in events],'native',[e for e,s in expectedEvents]);print([(i,a[0],b[0],a[1]==b[1])for i,(a,b)in enumerate(zip(events,expectedEvents))if a!=b][:4]);raise AssertionError((label,'ordered complete snapshots'))
 assert ret==result.value and u.reg_read(UC_X86_REG_ESP)==m.stack+4,(label,'eax/sp');assert not callbackErrors,callbackErrors;assert after==(nextAllocation,allocationIndex,recordIndex,clockSampleIndex,clockValue);assert m.read_words(0,1)==[0x12345678];native=True;calls+=1;event_count+=len(events);return ret

# Owned composition glue. This is a focused source scheduler profile: the
# Flare is parked at source state1000 so no resource/ANI adapters are needed.
class ProjectileGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('tick','animationDelta','magicDisabled','ownerToken','audioEnabled','masterVolume')]
class ProjectileContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(ProjectileGlobals)),('bullet',C.c_void_p),('composeAnimation',C.c_uint32),('fault',C.c_uint32)]
class ProjectileCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('count',C.c_uint32),('arguments',C.c_uint32*12),('name',C.c_char_p)]
ProjectileDependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(ProjectileContext),C.POINTER(ProjectileCall),C.c_void_p)
class FlareContext(C.Structure):_fields_=[('scene',Host),('animation',C.c_void_p),('images',C.c_void_p)]+[(n,C.c_uint32)for n in('composeAnimation','composeFSM','composeEffects','maximumSteps','fault')]
class FlareCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('count',C.c_uint32),('arguments',C.c_uint32*8),('name',C.c_char_p)]
FlareDependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(FlareContext),C.POINTER(FlareCall),C.c_void_p)
class Lifecycle(C.Structure):_fields_=[('scene',Host),('fault',C.c_uint32)]
lib.claw_elemental_projectile_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(ProjectileContext),ProjectileDependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_flare_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(FlareContext),FlareDependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_stacked_actor_lifecycle_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Lifecycle),C.POINTER(C.c_uint32)]
@ProjectileDependency
def unexpectedProjectile(c,e,u):callbackErrors.append(('unexpected projectile transport',hex(e.contents.function)));c.contents.fault=1;return 0
@FlareDependency
def unexpectedFlare(c,e,u):callbackErrors.append(('unexpected Flare transport',hex(e.contents.function)));c.contents.fault=1;return 0
def gameplay(fn,receiver,args):
 log(('call',fn,receiver,args));a=(C.c_uint32*len(args))(*args);out=C.c_uint32()
 if fn in(0x410100,0x411cd0):
  g=ProjectileGlobals();c=ProjectileContext(host,C.pointer(g),None,1,0)
  assert lib.claw_elemental_projectile_entry(fn,receiver,a,len(args),C.byref(c),unexpectedProjectile,None,C.byref(out))and not c.fault
 elif fn==0x457f00:
  c=FlareContext(host,None,None,0,0,0,65536,0)
  assert lib.claw_flare_entry(fn,receiver,a,len(args),C.byref(c),unexpectedFlare,None,C.byref(out))and not c.fault
 elif fn==0x484d90:
  c=Lifecycle(host,0);assert lib.claw_stacked_actor_lifecycle_entry(fn,receiver,a,len(args),C.byref(c),C.byref(out))and not c.fault
 else:raise AssertionError(hex(fn))
 return out.value
oldInvoke=baseInvoke
@Invoke
def invoke(_,e):
 try:
  if e.function in(0x410100,0x457f00,0x484d90):return gameplay(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]))
  return oldInvoke(_,e)
 except BaseException as error:callbackErrors.append(repr(error));return 0

host.call=invoke
oldGameDependency=baseGameDependency
@GameDependency
def gameDependency(c,e,u):
 try:
  q=e.contents
  if q.function in(0x410100,0x457f00,0x484d90):return gameplay(q.function,q.receiver,tuple(q.arguments[:q.argumentCount]))
  if q.function==0x4c9be0:return invoke(None,Call(q.function,q.receiver,(C.c_uint32*4)(*q.arguments),q.argumentCount))
  return oldGameDependency(c,e,u)
 except BaseException as error:callbackErrors.append(repr(error));c.contents.fault=1;return 0

def gameplayHook(uc,address,size,user):
 if address not in(0x410100,0x457f00,0x484d90):return
 n=1;receiver=0 if address!=0x484d90 else uc.reg_read(UC_X86_REG_ECX)
 log(('call',address,receiver,tuple(m.read_words(uc.reg_read(UC_X86_REG_ESP)+4,n))))
u.hook_add(UC_HOOK_CODE,gameplayHook)
PARENT,CHILD=ACTORS[9:11];PARENT_LOGIC,CHILD_LOGIC=LOGICS[9:11]
PARENT_PRIVATE,CHILD_PRIVATE=BASE+0x13000,BASE+0x14000

def activeActors():
 at=words(CONTAINER+20,1)[0];out=[]
 while at:n=words(at,3);out.append(n[2]);at=n[0]
 return out

def prepareChild(center=781,childX=1601,childY=4755,childFlags=0x40000,childFirst=True):
 global fullDestruction
 prepareOuter();fullDestruction=True
 # Drop all unrelated dormant members; no camera callback mutates the plane.
 grid=words(PLANE+0xb0,1)[0]
 for l in words(grid+4,3):
  p=words(l,17);put(p[16],[0]*(p[7]*2));put(l+8,[0])
 put(CL+16,[CALLBACK]);put(PLANE+0x10,[fb(center),fb(4730)]);put(PLANE+0x84,[center,4730]);put(PLAYER+76,[center,4730])
 for actor,logic,private,vt,fn,z,flags,x,y,size in((PARENT,PARENT_LOGIC,PARENT_PRIVATE,0x50b7bc,0x410100,1501,0xc0000,1581,4755,86),(CHILD,CHILD_LOGIC,CHILD_PRIVATE,0x50e6fc,0x457f00,1500 if childFirst else 1502,childFlags,childX,childY,19)):
  put(actor,[0]*128);put(actor,[0x5137f0,0,flags,PAR]);put(actor+76,[x,y]);put(actor+100,[z,0,logic]);put(actor+136,[0,0,0,0,x,y,actor]);put(logic,[0]*93);put(logic,[0x513740]);put(logic+16,[fn,0,private,1000]);put(private,[0]*size);put(private,[vt]);put(private+8,[actor,actor,logic]);insert(actor)
 put(PARENT_PRIVATE+0x12c,[PARENT,PARENT_LOGIC]);put(PARENT_PRIVATE+0x150,[CHILD]);put(CHILD_PRIVATE+40,[CHILD,CHILD,CHILD_LOGIC]);put(PARENT+8,[words(PARENT+8,1)[0]|0x10000])
 # Native shared cameras are transported without changing source clock aliases.
 gameContext.host=cameraHost;gameContext.host.heap=host
 return grid

def setCenter(x,y=4730):
 put(PLANE+16,[fb(x),fb(y)]);put(PLANE+0x84,[x,y]);put(PLAYER+76,[x,y])
def advance(delta=16):
 stage.stage.deltaMilliseconds=delta;stage.stage.nowMilliseconds+=delta;stage.accumulatedMilliseconds+=delta
 sceneGlobals.animation.deltaMilliseconds=delta;sceneGlobals.animation.nowMilliseconds+=delta
 cameraGlobals.stageDelta=delta;cameraGlobals.animationDelta=delta;cameraGlobals.animationNow=sceneGlobals.animation.nowMilliseconds
 clockState.nowMilliseconds+=delta;clockState.deltaMilliseconds=delta
