"""Private whole original saved-player startup oracle; no frozen helper writes."""
import ctypes as C,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/world-startup-agent'
SOURCES=['PlayerStartupRuntime','SinglePlayerSceneRuntime','WorldFileRuntime','WorldPlaneRuntime','CArrayRuntime','SceneCameraRuntime','SpatialGridRuntime','SpriteGeometry','SceneActorRuntime','WorldObjectRuntime','GameTiming','PlayerLocomotion','PlayerAirStates','PlayerInitialization','PlayerEngine','PlayerPhysics','CollisionResponse','TileCollision','CheckpointLogicRuntime','ActorAnimationRuntime','AnimationEngine','AnimationOperations','AudioEvents','ActorResourceBindings','CRTRandomRuntime','WorldLootRuntime','AmbientAudioBackendRuntime']
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in SOURCES],'-o',str(WORK/'libPlayerStartupRuntime.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',C.c_void_p*3),('bufferBytes',U*3)]
class Context(C.Structure):_fields_=[('scene',Host),('singlePlayer',C.c_void_p)]+[(n,U)for n in('composeCache','composeCamera','maximumPlanes','fault')]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(WORK/'libPlayerStartupRuntime.dylib'));lib.claw_player_startup_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_player_startup_entry.restype=U
BASE,SIZE=0x1000000,0x100000;GS,GN=0x520000,0x30000
OWNER,APP,SCENE,WORLD,TABLE,RECORD=BASE+0x1000,BASE+0x2000,BASE+0x3000,BASE+0x4000,BASE+0x5000,BASE+0x10000
PLANES=[BASE+0x6000+i*0x800 for i in range(3)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;m.executed.clear();u.mem_map(0,4096)
seedGlobals=bytes(u.mem_read(GS,GN));raw=(C.c_uint8*GN).from_buffer_copy(seedGlobals);heap=(C.c_uint8*SIZE)();native=True;events=[];errors=[];calls=snapshots=0;callbackMode=0;callbackCount=0;prefixStop=0;sourceStopped=False

def get(t,n=1):return list((U*n).from_address(C.addressof(raw)+t-GS if GS<=t<GS+GN else C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(U*len(v)).from_address(C.addressof(raw)+t-GS if GS<=t<GS+GN else C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def snapshot():return(bytes(heap),bytes(raw),callbackCount)if native else(bytes(u.mem_read(BASE,SIZE)),bytes(u.mem_read(GS,GN)),callbackCount)
@Lookup
def lookup(_,t,n):
 if GS<=t and t+n*4<=GS+GN:return C.addressof(raw)+t-GS
 return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
@Allocate
def alloc(_,n):raise AssertionError(('unexpected allocation',n))
@Free
def free(_,t):raise AssertionError(('unexpected free',t))
@Clock
def clock(_):raise AssertionError('unexpected clock')
@Invoke
def invoke(_,e):raise AssertionError(('unexpected ordinary call',hex(e.function)))
host=Host(None,lookup,alloc,free,invoke,clock);ctx=Context(host,None,1,1,65536,0)

def effect(f,t,args):
 global callbackCount
 events.append(((f,t,tuple(args)),snapshot()));callbackCount+=1
 if f==0x49ae60:
  level,kind=args
  if kind<1 or kind>3 or level>=15:return 0
  return t+{1:0x2d4,2:0xd24,3:0x1774}[kind]+level*0xb0
 if f==0x4d0a60:
  put(t+0x84,[int(struct.unpack('<f',struct.pack('<I',get(t+0x10)[0]))[0])&0xffffffff,int(struct.unpack('<f',struct.pack('<I',get(t+0x14)[0]))[0])&0xffffffff])
  if callbackMode==1 and callbackCount==1:put(WORLD+0x5c,[PLANES[2]])
  if callbackMode==2 and callbackCount==1:put(WORLD+0x60,[0]);put(WORLD+0x3c,[1])
  if callbackMode==3 and callbackCount==1:put(RECORD+0x1774+0xb0+0x10,[0x80000000])
  return 0
 raise AssertionError((hex(f),hex(t),args))
@Dependency
def dependency(c,e,_):
 try:q=e.contents;return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]))
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0

def returned(pop,result):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop*4);u.reg_write(UC_X86_REG_EIP,ret)
def hook(_,address,size,user):
 global sourceStopped
 if address==prefixStop:sourceStopped=True;u.emu_stop();return
 if address==0x4d0a60 and not ctx.composeCamera:returned(0,effect(address,u.reg_read(UC_X86_REG_ECX),[]))
 if address==0x49ae60 and not ctx.composeCache:returned(2,effect(address,u.reg_read(UC_X86_REG_ECX),m.read_words(u.reg_read(UC_X86_REG_ESP)+4,2)))
u.hook_add(UC_HOOK_CODE,hook)
def fword(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def setup(seed=0):
 global native,callbackCount,callbackMode,prefixStop,sourceStopped
 native=True;r=random.Random(seed);C.memmove(heap,r.randbytes(SIZE),SIZE);C.memmove(raw,seedGlobals,GN)
 put(OWNER,[r.getrandbits(32)for _ in range(478)]);put(OWNER+4,[APP]);put(OWNER+0xc,[SCENE]);put(OWNER+0x14,[2]);put(APP,[r.getrandbits(32)for _ in range(77)]);put(APP+0x64,[RECORD]);put(APP+0xa8,[1]);put(APP+0xd8,[0]);put(SCENE+0x24,[WORLD]);put(WORLD,[0]*56);put(WORLD+0x38,[TABLE,3]);put(WORLD+0x5c,[PLANES[1],1]);put(TABLE,PLANES)
 for i,p in enumerate(PLANES):
  put(p,[r.getrandbits(32)for _ in range(86)]);put(p+8,[1 if i==1 else 0]);put(p+0x18,[fword([.125,1,1.75][i]),fword([.5,1,1.25][i])]);put(p+0x30,[24576,6144]);put(p+0x70,[640,480,320,240]);put(p+0x84,[320,240])
 put(RECORD,[r.getrandbits(32)for _ in range(2450)])
 for k in(1,2,3):
  for level in range(15):
   t=RECORD+{1:0x2d4,2:0xd24,3:0x1774}[k]+level*0xb0;put(t,[2,720+level*97,4720-level*31,0,1234567+level,seed]+[r.getrandbits(32)for _ in range(38)])
 put(0x53725c,[seed%2]);put(0x52c6e4,[seed*997]);ctx.composeCache=ctx.composeCamera=1;ctx.maximumPlanes=65536;ctx.singlePlayer=None;callbackCount=callbackMode=prefixStop=0;sourceStopped=False

def execute(f,t,args=()):
 global calls,snapshots
 events.clear();errors.clear()
 if native:
  aa=(U*len(args))(*args);out=U();assert lib.claw_player_startup_entry(f,t,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));ret=out.value;assert not ctx.fault,ctx.fault;assert not errors,errors
 else:
  ret=m.call(f,t,struct.pack('<'+'I'*len(args),*(a&0xffffffff for a in args)));assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(args)*4
 calls+=1;snapshots+=len(events);return snapshot(),list(events),ret if f not in(0x415ce0,0x46c790)else 0

def compare(f,t,args=()):
 global native,callbackCount
 native=True;before=snapshot();a=execute(f,t,args);native=False;u.mem_write(BASE,before[0]);u.mem_write(GS,before[1]);callbackCount=before[2];b=execute(f,t,args)
 if a!=b:
  for z,(x,y)in enumerate(zip(a[0][:2],b[0][:2])):
   diff=[(hex((BASE if z==0 else GS)+i),x[i:i+4].hex(),y[i:i+4].hex())for i in range(0,len(x),4)if x[i:i+4]!=y[i:i+4]];print('diff',hex(f),z,diff[:12])
  print('events',[q[0]for q in a[1]],[q[0]for q in b[1]]);print('results',a[2],b[2]);raise AssertionError(hex(f))
 native=True;C.memmove(heap,a[0][0],SIZE);C.memmove(raw,a[0][1],GN);callbackCount=a[0][2];return a
