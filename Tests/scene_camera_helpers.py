"""Original input/camera/viewport caller oracle; full raw word preservation."""
import argparse,ctypes as C,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/scene-camera-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');opts=p.parse_args()
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['SceneCameraRuntime.cpp','SpriteGeometry.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']],'-o',str(WORK/'libSceneCameraRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libSceneCameraRuntime.dylib'))
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class HeapHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
globalNames=['playerToken','inputDeviceToken','inputMappingToken','stageDelta','menuBlocked','animationNow','animationDelta','forcedX','forcedY','detachedMode','shakeUntil','detachedOwnerToken'];globalAddresses=[0x537e88,0x537200,0x537204,0x53720c,0x537258,0x5430c8,0x5430c4,0x52be14,0x52be18,0x53c25c,0x53c260,0x53c264]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in globalNames]
class PlatformCall(C.Structure):_fields_=[('importSlot',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('bufferToken',C.c_uint32),('buffer',C.POINTER(C.c_uint32)),('bufferWords',C.c_uint32)]
Platform=C.CFUNCTYPE(C.c_uint32,C.c_void_p,PlatformCall)
class Host(C.Structure):_fields_=[('heap',HeapHost),('platformContext',C.c_void_p),('platform',Platform)]
class Projection(C.Structure):_fields_=[(n,C.c_uint32)for n in ['flags','extentX','extentY','cameraX','cameraY','visibleEndX','visibleEndY','screenOffsetX','screenOffsetY']]
lib.claw_scene_camera_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_scene_camera_entry.restype=C.c_uint32
lib.claw_scene_camera_projection.argtypes=[C.c_uint32,HeapHost,C.POINTER(Projection),C.POINTER(C.c_uint32)];lib.claw_scene_camera_projection.restype=C.c_uint32
lib.claw_sprite_project.argtypes=[C.POINTER(Projection),C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
m=OriginalV10(opts.exe);u=m.u;u.mem_map(0,4096);m.executed.clear();BASE,SIZE=0x1000000,0x20000;heap=(C.c_uint8*SIZE)();rng=random.Random(0x486240)
OWNER,MGR,CFG,WINDOW,DEVICE,INPUT,PLAYER,PL,PV,CAMERA,L,CP,PAR,WORLD=[BASE+i*0x1000 for i in range(1,15)]
P0,P1,P2,TABLE,DET,CELL,DETPLAYER,RECT=[BASE+i*0x1000 for i in range(16,24)]
ALLOC=BASE+0x18000;OSBASE=0x10fd000;COPY=OSBASE+0x100;RNG=0x4a3050
slots=[0x546ce4,0x546cd0,0x546d9c,0x546de8,0x546c44,0x546d50];slotTargets={s:OSBASE+i*16 for i,s in enumerate(slots)}
# Exact pure CopyRect memory adapter; not input/UI behavior.
copyCode=b'\x8b\x4c\x24\x04\x8b\x54\x24\x08'+b''.join(b'\x8b\x42'+bytes([i])+b'\x89\x41'+bytes([i])for i in(0,4,8,12))+b'\xb8\x01\0\0\0\xc2\x08\0'
u.mem_write(COPY,copyCode);m.write_words(0x546d58,[COPY])
native=True;globals=Globals();sceneGlobals=None;stage=None;clockValue=1000;events=[];keyState={};randomValues=[0];randomIndex=0;policy=0;calls=event_count=0;joy=[0]*13
sizes={OWNER:474,MGR:80,CFG:80,WINDOW:16,DEVICE:146,INPUT:29,PLAYER:128,PL:93,PV:78,CAMERA:128,L:93,CP:5,PAR:64,WORLD:40,P0:45,P1:45,P2:45,DET:16,CELL:4,DETPLAYER:128}
def words(t,n):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=v
 else:m.write_words(t,v)
def setg(n,v):
 if native:setattr(globals,n,v&0xffffffff)
 else:m.write_words(globalAddresses[globalNames.index(n)],[v])
def getg(n):
 if native and stage is not None:
  if n=='stageDelta':return stage.stage.deltaMilliseconds
  if n=='animationNow':return sceneGlobals.animation.nowMilliseconds
  if n=='animationDelta':return sceneGlobals.animation.deltaMilliseconds
 return getattr(globals,n)if native else m.read_words(globalAddresses[globalNames.index(n)],1)[0]
def snap():
 raw=(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+struct.pack('<12I',*[getg(n)for n in globalNames])
 if sceneGlobals is not None:
  raw+=bytes(sceneGlobals)+bytes(stage)if native else struct.pack('<17I',m.read_words(0x5430d0,1)[0],*m.read_words(0x5430f0,5),*m.read_words(0x5430d8,5),*m.read_words(0x5430c8,1),*m.read_words(0x5430c4,1),*m.read_words(0x537208,3),m.read_words(0x537e88,1)[0])
 return raw
def log(e):events.append((e,snap()))
def fb(f):return struct.unpack('<I',struct.pack('<f',f))[0]
def fp(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def platformEffect(slot,args,buffer,token):
 if slot==0x546ce4:
  value=keyState.get(args[0],0);keyState[args[0]]=value&~1;return value
 if slot==0x546c44:return 1920 if args[0]==0 else 1080
 if slot==0x546cd0:
  buffer[0]=300;buffer[1]=0xfffffffe;return 1
 if slot==0x546de8:
  for i,v in enumerate(joy):buffer[i]=v
  return 0
 if policy==1 and slot==0x546d9c:
  setg('menuBlocked',getg('menuBlocked')^1)
 return 1
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
@Allocate
def allocate(_,n):log(('allocate',n));put(ALLOC,[0xfeed]*((n+3)//4));return ALLOC
@Free
def free(_,t):log(('free',t))
@Invoke
def invoke(_,call):
 global randomIndex
 args=tuple(call.arguments[:call.argumentCount])
 if call.function in(0x46c860,0x486240):
  for n in('stageDelta','animationNow','animationDelta'):setattr(globals,n,getg(n))
  fault=C.c_uint32();result=C.c_uint32();token=call.receiver if call.function==0x46c860 else args[0]
  assert lib.claw_scene_camera_entry(call.function,token,0,0,C.byref(globals),host,C.byref(fault),C.byref(result))and not fault.value
  return result.value
 log(('call',call.function,call.receiver,args))
 if call.function in(0x4d1fd0,0x4d2000,0x4c9390):return 0
 if call.function==RNG:
  value=randomValues[randomIndex%len(randomValues)];randomIndex+=1
  if policy==2:setg('animationDelta',getg('animationDelta')^1)
  return value&0xffffffff
 raise AssertionError(('unexpected gameplay service',call.function))
@Clock
def clock(_):log(('clock',));return clockValue
@Platform
def platform(_,call):
 args=tuple(call.arguments[:call.argumentCount]);log(('platform',call.importSlot,args,call.bufferToken,call.bufferWords));return platformEffect(call.importSlot,args,call.buffer,call.bufferToken)
heapHost=HeapHost(None,lookup,allocate,free,invoke,clock);host=Host(heapHost,None,platform)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def originalHook(uc,address,size,user):
 global randomIndex
 sp=u.reg_read(UC_X86_REG_ESP)
 if address in(0x4d1fd0,0x4d2000,0x4c9390):
  log(('call',address,u.reg_read(UC_X86_REG_ECX),()));
  if address!=0x4c9390:returned(0)
  return
 if address==OSBASE+0x200:log(('clock',));returned(0,clockValue);return
 if address==0x4f6428:log(('free',m.read_words(sp+4,1)[0]));returned(0);return
 if address==0x4f63ec:
  n=m.read_words(sp+4,1)[0];log(('allocate',n));m.write_words(ALLOC,[0xfeed]*((n+3)//4));returned(0,ALLOC);return
 if address==RNG:
  log(('call',RNG,0,()));value=randomValues[randomIndex%len(randomValues)];randomIndex+=1
  if policy==2:setg('animationDelta',getg('animationDelta')^1)
  returned(0,value);return
 if address not in slotTargets.values():return
 slot=slots[(address-OSBASE)//16];counts={0x546ce4:1,0x546cd0:1,0x546d9c:2,0x546de8:2,0x546c44:1,0x546d50:4};n=counts[slot];raw=m.read_words(sp+4,n);token=0;bufCount=0;buffer=None;args=tuple(raw)
 if slot==0x546cd0:args=();bufCount=2;buffer=[0]*2
 if slot==0x546de8:args=(raw[0],);token=raw[1];bufCount=13;buffer=m.read_words(token,13)
 log(('platform',slot,args,token,bufCount));ret=platformEffect(slot,args,buffer,token)
 if slot==0x546cd0:m.write_words(raw[0],buffer)
 if slot==0x546de8:m.write_words(token,buffer)
 returned(n*4,ret)
u.hook_add(UC_HOOK_CODE,originalHook)
def setup():
 global native,globals,keyState,policy,joy,sceneGlobals,stage
 native=True;sceneGlobals=stage=None;heap[:]=rng.randbytes(SIZE);globals=Globals(PLAYER,DEVICE,INPUT,rng.choice([0,1,16,18,35,0xffffffff]),rng.randrange(2),rng.randrange(1000),rng.choice([0,1,16,33,0xffffffff]),0xffffffff,0xffffffff,0,rng.choice([0,1000]),DET);policy=0
 put(OWNER+4,[MGR]);put(OWNER+0xc,[PAR]);put(OWNER+0x764,[rng.choice([0,1,16,35,0xffffffff])]);put(MGR+4,[WINDOW]);put(MGR+0x4c,[CFG]);put(WINDOW+4,[0x123]);put(CFG+0x30,[rng.randrange(2)])
 put(INPUT,[DEVICE]);put(INPUT+16,[1<<i for i in range(10)]);put(INPUT+14*4,list(range(90,104)));put(INPUT+4,[rng.getrandbits(32),0,rng.getrandbits(32)]);put(DEVICE+0x1cc,[rng.randrange(8)]);put(DEVICE+0x1d4,[rng.randrange(2),rng.randrange(2)]);put(DEVICE+0x40,[rng.randrange(20)]);put(DEVICE+0x1dc,list(range(60,72)))
 for offset in(0x230,0x234):put(DEVICE+offset,[rng.randrange(-30,31)&0xffffffff])
 put(DEVICE+0x238,[10,10,960,540]);put(DEVICE+0x220,[10,90,10,90]);joy=[rng.getrandbits(32)for _ in range(13)];joy[2]=rng.randrange(100);joy[3]=rng.randrange(100);joy[8]=rng.getrandbits(12)
 keyState={k:rng.choice([0,1,0x8000,0x8001,0xffff,0x7fff])for k in range(256)}
 put(CAMERA+0xc,[PAR]);put(CAMERA+0x6c,[L]);put(L+0x14,[CP]);put(L+0x1c,[rng.choice([0,24,26,0x138b,0x138c,0x22b8,55])]);put(CP,[rng.randrange(2000),rng.randrange(2000),rng.randrange(2000),rng.randrange(2000),rng.choice([0,1,33,0xffffffff])]);put(PLAYER+0x6c,[PL]);put(PL+0x14,[PV]);put(PL+0x1c,[rng.choice([24,26,0x138b,0x138c,55])]);put(PV+0x110,[rng.randrange(2)]);put(PLAYER+0x4c,[rng.randrange(-200,2000)&0xffffffff,rng.randrange(-200,2000)&0xffffffff]);put(PLAYER+0xcc,[rng.choice([1,3,4,8])]);put(PAR+0x24,[WORLD]);put(WORLD+0x38,[TABLE,3]);put(WORLD+0x5c,[P0,0]);put(TABLE,[P0,P1,P2]);put(DET+0x14,[CELL]);put(CELL,[DETPLAYER]);put(DETPLAYER+0x4c,[500,800]);put(RECT,[0,0,639,479])
 for i,t in enumerate((P0,P1,P2)):
  put(t+8,[rng.choice([0,1,4,8,12])]);put(t+0x10,[fb(rng.uniform(-100,3000)),fb(rng.uniform(-100,3000)),fb(rng.choice([0.25,0.5,1,1.25])),fb(rng.choice([0.25,0.5,1,1.25]))]);put(t+0x30,[rng.choice([320,640,1280,2048]),rng.choice([240,480,1024,2048])]);put(t+0x50,[0,0,639,479]);put(t+0x70,[640,480,320,240]);
 return globals

def compare(f,t,label,x=0,y=0):
 global native,globals,keyState,randomIndex,calls,event_count
 native=True;before=bytes(heap);oldg=bytes(globals);oldScene=bytes(sceneGlobals)if sceneGlobals is not None else None;oldStage=bytes(stage)if stage is not None else None;oldKeys=dict(keyState);events.clear();randomIndex=0;fault=C.c_uint32();result=C.c_uint32();rr=lib.claw_scene_stage_run(t,C.byref(stage),C.byref(sceneGlobals),x,heapHost,C.byref(fault))if f in(0x46ace0,0x46ad70)else lib.claw_scene_camera_entry(f,t,x,y,C.byref(globals),host,C.byref(fault),C.byref(result));assert rr and not fault.value,(label,'nativefault',fault.value)
 expected=snap();expectedEvents=list(events);expectedKeys=dict(keyState);u.mem_write(BASE,before)
 for i,a in enumerate(globalAddresses):m.write_words(a,[struct.unpack_from('<I',oldg,i*4)[0]])
 if oldScene:
  v=struct.unpack('<13I',oldScene);m.write_words(0x5430d0,v[:1]);m.write_words(0x5430f0,v[1:6]);m.write_words(0x5430d8,v[6:11]);m.write_words(0x5430c8,v[11:12]);m.write_words(0x5430c4,v[12:13]);v=struct.unpack('<4I',oldStage);m.write_words(0x537208,v[:3]);m.write_words(0x537e88,v[3:]);m.write_words(0x546df0,[OSBASE+0x200])
 m.write_words(0,[0x12345678]);m.write_words(0x546d58,[COPY]);u.mem_write(COPY,copyCode)
 for slot,target in slotTargets.items():m.write_words(slot,[target])
 keyState=oldKeys;randomIndex=0;native=False;events.clear();args=struct.pack('<I',t)if f in(0x486240,0x486d70)else struct.pack('<2I',x,y)if f==0x42d5f0 else struct.pack('<I',x)if f in(0x4d0c50,0x4b3430) else b''
 try:ret=m.call(f,t,args)
 except Exception:print('originalfault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 if snap()!=expected:
  actual=snap()
  for i in range(0,len(actual),4):
   a,b=struct.unpack_from('<I',actual,i)[0],struct.unpack_from('<I',expected,i)[0]
   if a!=b:print(label,hex(i),hex(a),hex(b))
  raise AssertionError((label,'whole raw buffers'))
 if f in(0x430ec0,0x431300,0x486240,0x486d70,0x486d30):assert ret==result.value,(label,'EAX',ret,result.value)
 if events!=expectedEvents:
  print(label,'original',[e for e,s in events]);print('native',[e for e,s in expectedEvents]);
  for i,(a,b)in enumerate(zip(events,expectedEvents)):
   if a!=b:print('mismatch',i,a[0],b[0],a[1]==b[1]);break
  raise AssertionError((label,'ordered full raw event snapshots'))
 assert keyState==expectedKeys,(label,'ordered platform key consumption')
 assert m.read_words(0,1)==[0x12345678]
 native=True;calls+=1;event_count+=len(events)

class Frame(C.Structure):_fields_=[('nowMilliseconds',C.c_uint32),('deltaMilliseconds',C.c_uint32)]
class SceneGlobals(C.Structure):_fields_=[('initializationFlags',C.c_uint32),('deletionArray',C.c_uint32*5),('reorderArray',C.c_uint32*5),('animation',Frame)]
class Stage(C.Structure):_fields_=[('stage',Frame),('accumulatedMilliseconds',C.c_uint32),('playerToken',C.c_uint32)]
lib.claw_scene_stage_run.argtypes=[C.c_uint32,C.POINTER(Stage),C.POINTER(SceneGlobals),C.c_uint32,HeapHost,C.POINTER(C.c_uint32)];lib.claw_scene_stage_run.restype=C.c_uint32
