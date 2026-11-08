"""Original tile/world renderer oracle; hash complete raw heaps at every event."""
import argparse,ctypes as C,hashlib,json,random,struct,subprocess,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/plane-renderer-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');opts=p.parse_args()
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['PlaneRenderer.cpp','WorldPlaneRuntime.cpp','SceneCameraRuntime.cpp','SpriteGeometry.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']],'-o',str(WORK/'libPlaneRenderer.dylib')],check=True)
lib=C.CDLL(str(WORK/'libPlaneRenderer.dylib'))
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class SceneHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class GraphicsCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('rectangleToken',C.c_uint32),('rectangle',C.POINTER(C.c_uint32))]
Graphics=C.CFUNCTYPE(C.c_uint32,C.c_void_p,GraphicsCall)
class RendererHost(C.Structure):_fields_=[('scene',SceneHost),('graphicsContext',C.c_void_p),('graphics',Graphics)]
lib.claw_plane_renderer_draw.argtypes=[C.c_uint32,C.c_uint32,RendererHost,C.POINTER(C.c_uint32)]
lib.claw_plane_renderer_world.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,RendererHost,C.POINTER(C.c_uint32)]
class WorldPlaneContext(C.Structure):_fields_=[('scene',SceneHost),('fault',C.c_uint32)]
class WorldPlaneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p)]
PlaneDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(WorldPlaneContext),C.POINTER(WorldPlaneCall),C.c_void_p)
lib.claw_world_plane_construct.argtypes=[C.c_uint32]*4+[C.POINTER(WorldPlaneContext)]
lib.claw_world_plane_load.argtypes=[C.c_uint32]*4+[C.POINTER(WorldPlaneContext),PlaneDependency,C.c_void_p]
class CameraGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('playerToken','inputDeviceToken','inputMappingToken','stageDelta','menuBlocked','animationNow','animationDelta','forcedX','forcedY','detachedMode','shakeUntil','detachedOwnerToken')]
class CameraHost(C.Structure):_fields_=[('heap',SceneHost),('platformContext',C.c_void_p),('platform',C.c_void_p)]
lib.claw_scene_camera_entry.argtypes=[C.c_uint32]*4+[C.POINTER(CameraGlobals),CameraHost,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
BASE,SIZE=0x3000000,0x140000;PLANE=[BASE+0x1000+i*0x1000 for i in range(3)];TARGET,RECEIVER,WORLD,PAR,SCENE,RECT,PLANES=[BASE+i*0x1000 for i in range(4,11)];MANAGERS=[BASE+0xb000+i*0x100 for i in range(3)];TABLES=[BASE+0xc000+i*0x1000 for i in range(3)];TILES=[BASE+0x10000+i*0x1000 for i in range(3)];ROWS=[BASE+0x13000+i*0x100 for i in range(3)];SETS=[BASE+0x14000+i*0x100 for i in range(3)];IMAGES=[BASE+0x15000+i*0x1000 for i in range(3)];ACTORS=[BASE+0x18000+i*0x200 for i in range(6)];NODES=[BASE+0x19000+i*0x20 for i in range(6)];VT=BASE+0x1a000;RAW=BASE+0x20000;ALLOC_START=BASE+0xc0000
ACTOR_SERVICE,IMAGE_SERVICE,SCENE_SERVICE=0x10fd000,0x10fd010,0x10fd020
m=OriginalV10(opts.exe);u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear();heap=(C.c_uint8*SIZE)();rng=random.Random(0x4d0d50);native=True;events=[];calls=event_count=0;policy=0;graphicsCount=0;currentPlane=PLANE[0];cursor=ALLOC_START;loading=False
def words(t,n):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def write(t,b):C.memmove(C.addressof(heap)+t-BASE,b,len(b))if native else u.mem_write(t,b)
def snapshot():return hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest()
def log(e):events.append((e,snapshot()))
def fb(f):return struct.unpack('<I',struct.pack('<f',f))[0]
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if t%4==0 and BASE<=t and t+n*4<=BASE+SIZE else None
@Allocate
def allocate(_,n):
 global cursor
 assert loading,'renderer does not allocate';t=cursor;cursor+=(n+15)&~15;assert cursor<=BASE+SIZE;return t
@Free
def free(_,t):raise AssertionError('renderer does not free')
def dependency(fn,receiver,args):
 log(('call',fn,receiver,args))
 if fn in(0x4d2890,IMAGE_SERVICE):
  actor=args[0];put(actor+0x30,[0xfeed0000|graphicsCount])
  if policy==2:
   node=words(actor+0x68,1)[0]
   if node:put(node,[0])
  return 1
 if fn in(ACTOR_SERVICE,SCENE_SERVICE):return 1
 raise AssertionError(('unknown scene call',hex(fn),hex(receiver),args))
@Invoke
def invoke(_,c):return dependency(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]))
@Clock
def clock(_):raise AssertionError('renderer does not read clocks')
sceneHost=SceneHost(None,lookup,allocate,free,invoke,clock)
def graphicsEffect(fn,receiver,args,rect,token):
 global graphicsCount
 log(('graphics',fn,receiver,args,tuple(rect),token));graphicsCount+=1
 if policy==1:rect[0]=(rect[0]+1)&0xffffffff;rect[3]=(rect[3]-1)&0xffffffff
 elif policy==2 and graphicsCount==1:put(currentPlane+0x38,[65]);put(currentPlane+0x3c,[65])
 elif policy==3:
  if graphicsCount==1:put(currentPlane+0x50,[words(currentPlane+0x50,1)[0]+3]);put(currentPlane+0x60,[1,2,61,62])
 elif policy==4 and graphicsCount==1:put(TARGET+0x2c,[RECEIVER+0x100]);put(MANAGERS[0]+0x64,[0]);put(IMAGES[0]+0x28,[0x10])
 return 0x88760001 if policy==1 else 0
@Graphics
def graphics(_,c):
 rect=[c.rectangle[i]for i in range(4)];result=graphicsEffect(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]),rect,c.rectangleToken)
 for i,v in enumerate(rect):c.rectangle[i]=v
 return result
host=RendererHost(sceneHost,None,graphics)
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def originalHook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP);receiver=uc.reg_read(UC_X86_REG_ECX)
 if address in(0x4b9d80,0x4b9ce0):
  a=m.read_words(sp+4,5);ptr=a[3]if address==0x4b9d80 else a[0];rect=m.read_words(ptr,4);args=(a[0],a[1],a[2],a[4])if address==0x4b9d80 else(a[1],a[2],a[3],a[4]);value=graphicsEffect(address,receiver,args,rect,ptr if BASE<=ptr<BASE+SIZE else 0);m.write_words(ptr,rect);returned(20,value)
 elif address in(0x4d2890,IMAGE_SERVICE,ACTOR_SERVICE,SCENE_SERVICE):
  count=2 if address in(0x4d2890,IMAGE_SERVICE)else 1;returned(count*4,dependency(address,receiver,tuple(m.read_words(sp+4,count))))
u.hook_add(UC_HOOK_CODE,originalHook)
def reset(width=64,height=64,viewWidth=640,viewHeight=480):
 global native,events,policy,graphicsCount,currentPlane,cursor,loading
 native=True;events=[];policy=0;graphicsCount=0;currentPlane=PLANE[0];cursor=ALLOC_START;loading=False;pattern=rng.randbytes(4096);C.memmove(C.addressof(heap),pattern*(SIZE//4096),SIZE)
 put(TARGET,[0]*12);put(TARGET+0x2c,[RECEIVER]);put(RECEIVER,[0]*16);put(WORLD,[0]*56);put(WORLD+0x38,[PLANES,3]);put(WORLD+0x5c,[PLANE[1],1]);put(PLANES,PLANE);put(PAR,[0]*12);put(PAR+8,[SCENE]);put(PAR+0x24,[WORLD]);put(SCENE,[0x513c20,0,0,PAR,0x5107bc,NODES[0],NODES[-1],6,0,0,10]);put(RECT,[0,0,viewWidth-1,viewHeight-1]);put(VT,[0]*32);put(VT+0x2c,[ACTOR_SERVICE]);put(VT+0x38,[IMAGE_SERVICE]);put(VT+0x28,[SCENE_SERVICE])
 cols,rows=16,12
 for i,p in enumerate(PLANE):
  put(p,[0]*86);put(p,[0x513d40,i,0,PAR]);put(p+0x20,[TILES[i],ROWS[i],cols,rows,cols*width,rows*height,width,height]);put(p+0x40,[0,0,viewWidth-1,viewHeight-1,0,0,viewWidth-1,viewHeight-1,0,0,width,height,viewWidth,viewHeight,viewWidth//2,viewHeight//2,[-999,0,9000][i],0,0]);put(p+0x8c,[(width.bit_length()-1),(width.bit_length()-1)]);put(p+0xa0,[SETS[i],3]);put(p+0xf4,[100]+[0]*24);put(SETS[i],MANAGERS);put(ROWS[i],[j*cols for j in range(rows)]);put(TILES[i],[rng.randrange(16)|(rng.randrange(3)<<16)for _ in range(cols*rows)])
 for i,t in enumerate(MANAGERS):
  put(t,[0]*27);put(t,[0x513abc]);put(t+0x14,[TABLES[i],16]);put(t+0x64,[0,15]);put(TABLES[i],[IMAGES[i]+j*64 for j in range(16)])
  for j in range(16):put(IMAGES[i]+j*64,[0x513a70,j,0,PAR,width,height,width//2,height//2,0,0,0x11,RECEIVER+0x1000+i*0x1000+j*16,0,0,0,0])
 for i,a in enumerate(ACTORS):
  put(a,[0]*128);put(a,[0x5137f0,i,0,PAR]);put(a+0x64,[[-2000,-999,0,100,9000,10000][i],NODES[i]]);put(a+0x174,[IMAGES[0]+i*64]);put(NODES[i],[NODES[i+1]if i<5 else 0,NODES[i-1]if i else 0,a])
def compare(fn,t,label):
 global native,events,graphicsCount,calls,event_count
 native=True;before=bytes(heap);events=[];graphicsCount=0;fault=C.c_uint32();result=lib.claw_plane_renderer_draw(t,TARGET,host,C.byref(fault))if fn==0x4d0d50 else lib.claw_plane_renderer_world(t,TARGET,SCENE,host,C.byref(fault));assert result and not fault.value,(label,'nativefault',fault.value);expected=snapshot();expectedEvents=list(events);expectedCount=graphicsCount
 native=False;events=[];graphicsCount=0;u.mem_write(BASE,before);m.write_words(0,[0x12345678]);args=(TARGET,)if fn==0x4d0d50 else(TARGET,SCENE);m.call(fn,t,struct.pack('<'+'I'*len(args),*args))
 if snapshot()!=expected:
  actual=bytes(u.mem_read(BASE,SIZE));want=bytes(heap);print(label,'wholeheap differences',[(hex(BASE+i),hex(struct.unpack_from('<I',actual,i)[0]),hex(struct.unpack_from('<I',want,i)[0]))for i in range(0,SIZE,4)if actual[i:i+4]!=want[i:i+4]][:30]);raise AssertionError((label,'wholeheap'))
 if events!=expectedEvents:
  print(label,'events original',[e for e,s in events[:20]],'native',[e for e,s in expectedEvents[:20]]);print([(i,a[0],b[0],a[1]==b[1])for i,(a,b)in enumerate(zip(events,expectedEvents))if a!=b][:10]);assert False,(label,'ordered fullheap event hashes',len(events),len(expectedEvents))
 assert graphicsCount==expectedCount;assert m.read_words(0,1)==[0x12345678];native=True;calls+=1;event_count+=len(events)
 return expectedEvents

@PlaneDependency
def planeDependency(context,event,user):
 e=event.contents;args=tuple(e.arguments[:e.argumentCount])
 if e.function==0x4f6286:
  name=e.name.decode();names=('BACK','ACTION','FRONT')
  if name not in names:context.contents.fault=1;return 0
  return MANAGERS[names.index(name)]
 if e.function==0x4f582f:
  array=e.receiver-0x9c+0x400;index,value=args;put(array+index*4,[value]);put(e.receiver+4,[array,index+1,index+1,0]);return 0
 if e.function==0x4d1620:return 1 # Declared object/grid boundary; not renderer input.
 raise AssertionError(('unexpected plane dependency',e.function,args))
def actualLevel1():
 global loading,cursor
 reset();raw=(ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();count,start=struct.unpack_from('<2I',raw,732)
 if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:start]+zlib.decompress(raw[start:])
 write(RAW,raw);assert RAW+len(raw)<ALLOC_START;imageCursor=BASE+0x15000
 for i,group in enumerate(('BACK','ACTION','FRONT')):
  files=list((ROOT/'Original/cd-assets/LEVEL1/TILES'/group).glob('*.PID'));ids=[int(f.stem)for f in files];table=TABLES[i];put(table,[0]*512);put(MANAGERS[i],[0]*27);put(MANAGERS[i]+0x14,[table,max(ids)+1]);put(MANAGERS[i]+0x64,[min(ids),max(ids)])
  for file in sorted(files,key=lambda f:int(f.stem)):
   data=file.read_bytes();flags,width,height,dx,dy=struct.unpack_from('<5I',data,4);assert not flags&0x20;token=imageCursor;imageCursor+=64;put(token,[0x513a70,int(file.stem),0,PAR,width,height,width//2,height//2,dx,dy,0x11,RECEIVER+0x1000+i*0x10000+int(file.stem)*16,0,0,0,0]);put(table+int(file.stem)*4,[token])
 assert imageCursor<ACTORS[0]
 loading=True;c=WorldPlaneContext(sceneHost,0)
 for i,plane in enumerate(PLANE):
  assert lib.claw_world_plane_construct(plane,PAR,i,0,C.byref(c))==plane
  assert lib.claw_world_plane_load(plane,RAW+start+i*160,RAW,RECT,C.byref(c),planeDependency,None)==1 and not c.fault
 loading=False;put(WORLD+0x38,[PLANES,3]);put(WORLD+0x5c,[PLANE[1],1]);put(WORLD+0x10,[0,0,639,479])
 for a in ACTORS:put(a+0x174,[0]) # Actual tile fixture does not invent actor images.
 return raw
def follow(x,y):
 g=CameraGlobals();h=CameraHost(sceneHost,None,None);fault=C.c_uint32();result=C.c_uint32();assert lib.claw_scene_camera_entry(0x42d5f0,WORLD,x&0xffffffff,y&0xffffffff,C.byref(g),h,C.byref(fault),C.byref(result))and not fault.value
