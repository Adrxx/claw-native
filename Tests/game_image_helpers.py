"""Private raw image wrapper oracle with whole-heap/ordered service evidence."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/game-image-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/GameImageRuntime.cpp'),str(ROOT/'Sources/SpriteGeometry.cpp'),str(ROOT/'Sources/PIDSurfaceRaster.cpp'),str(ROOT/'Sources/PIDBlitter.cpp'),'-o',str(WORK/'libGameImageRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libGameImageRuntime.dylib'));U=C.c_uint32
class Args(C.Structure):_fields_=[('words',U*8),('count',U)]
class Globals(C.Structure):_fields_=[('animationDelta',U),('directDrawFX',U*25),('surfaceLoadFlags',U),('surfaceColorKey',U),('compressedEffect',U*4),('embeddedPalette',U*256)]
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class SceneHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*8),('argumentCount',U),('destination',C.POINTER(U)),('source',C.POINTER(U))]
Service=C.CFUNCTYPE(U,C.c_void_p,Call)
class Host(C.Structure):_fields_=[('heap',SceneHost),('serviceContext',C.c_void_p),('service',Service)]
lib.claw_game_image_entry.argtypes=[U,U,Args,C.POINTER(Globals),Host,C.POINTER(U),C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000;ACTOR,IMAGE,TARGET,PARENT,WORLD,PLANE,HOLDER=[BASE+i*0x1000 for i in range(1,8)];COPY=0x10fd030
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.write_words(0x546d58,[COPY]);m.executed.clear()
heap=(C.c_uint8*SIZE)();g=Globals();rng=random.Random(0x4d2890);native=True;events=[];eventCount=calls=0;policy=0
RAW,MANAGER,DISPLAY,DD,DISPLAYVT,DDVT,NODE,TABLE,PIXELS=[BASE+i for i in (0x10000,0x8000,0x9000,0xa000,0xb000,0xc000,0xd000,0xe000,0x80000)]
CREATE,DESCRIBE,LOCK,KEY,UNLOCK=[0x10fd040+i*16 for i in range(5)]
cursor=BASE+0x40000;loading=False;current={};freeList=[];pixelDraw=False
regions=[(0x5430c4,1),(0x543108,25),(0x54316c,1),(0x543170,1),(0x5430b0,4),(0x5427b0,256)]
def globalBytes():return bytes(g)if native else b''.join(bytes(u.mem_read(t,n*4))for t,n in regions)
def snapshot():return hashlib.sha256((bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+globalBytes()).digest()
def log(e):events.append((e,snapshot()))
def words(t,n):return list((U*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(U*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def gs(i,v):
 if native:g.directDrawFX[i]=v
 else:m.write_words(0x543108+i*4,[v])
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if t%4==0 and BASE<=t and t+n*4<=BASE+SIZE else None
@Allocate
def allocate(_,n):
 global cursor
 assert loading;log(('malloc',n));token=cursor;cursor+=(n+15)&~15;assert cursor<PIXELS;return token
@Free
def free(_,t):log(('free',t));freeList.append(t)
@Invoke
def invoke(_,c):raise AssertionError('unexpected heap call')
@Clock
def clock(_):raise AssertionError('unexpected clock')
scene=SceneHost(None,lookup,allocate,free,invoke,clock)
def descriptor(t):
 put(t,[0]*27)
 for off,value in ((0,108),(4,7),(8,current['h']),(12,current['w']),(16,current['pitch']),(36,PIXELS),(72,32),(76,32),(84,8)):put(t+off,[value])
class PixelRect(C.Structure):_fields_=[(x,C.c_int32)for x in ('left','top','right','bottom')]
class PixelCommand(C.Structure):_fields_=[('destination',PixelRect),('source',PixelRect),('flipX',U),('flipY',U),('originalSourceRectAddress',U)]
class PixelInfo(C.Structure):_fields_=[('consumed',C.c_size_t),('writes',C.c_size_t)]
lib.claw_pid_blit8.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(PixelCommand),C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_size_t,C.c_size_t,C.POINTER(PixelInfo)]
def nativeEntry(f,receiver,args):
 a=Args();a.count=len(args);a.words[:len(args)]=args;fault=U();result=U();assert lib.claw_game_image_entry(f,receiver,a,C.byref(g),host,C.byref(fault),C.byref(result))and not fault.value;return result.value
def effect(fn,recv,args,dst,src):
 if fn in(CREATE,DESCRIBE,LOCK,KEY,UNLOCK,0x4f51c5,0x4bd260,0x4bc5f0,0x4bc740,0x4f582f,0x4ce8e0):
  log(('service',fn,recv,args,tuple(src)if src is not None else None))
  if fn==CREATE:
   obj,desc,result,aggregation=args;assert obj==DISPLAY and aggregation==0;assert words(desc,4)==[108,7,current['h'],current['w']]
   if current.get('createFail'):return 0x80004005
   put(result,[DD]);return 0
  if fn==DESCRIBE:assert args[0]==DD;descriptor(args[1]);return 0
  if fn==LOCK:assert args[0]==DD and args[1]==0 and args[3:]==(1,0);descriptor(args[2]);return current.get('lockFail',0)
  if fn==KEY:assert args==(DD,8,0) and src[0]==src[1];return current.get('keyFail',0)
  if fn==UNLOCK:assert args==(DD,0);return 0
  if fn==0x4f51c5:put(NODE,[0,0,args[0]]);put(recv,[NODE,NODE,1,0,0,10]);return NODE
  if fn==0x4bc740:
   if current.get('fileFail'):return 0
   token=BASE+0xf000;put(token,[0]*47);put(token+0x14,[current['h'],current['w']]);put(token+0xb8,[current.get('keyEnabled',0)]);return token
  if fn==0x4f582f:
   index,value=args;put(words(recv+4,1)[0]+index*4,[value]);put(recv+8,[max(words(recv+8,1)[0],index+1)]);return 0
  return 0
 log((hex(fn),recv,args,tuple(dst)if dst is not None and fn!=0x546d58 else None,tuple(src)if src is not None else None))
 if fn==0x4bffa0 and pixelDraw:
  if not native:return 0
  c=words(recv,10);assert c[5]==1
  if C.c_int32(src[0]).value<0 or C.c_int32(src[2]).value>C.c_int32(c[1]-1).value or C.c_int32(src[1]).value<0 or C.c_int32(src[1]).value>C.c_int32(c[2]-1).value:return 0
  pixels=nativeEntry(0x4b9730,args[1],[0]);assert pixels
  data=struct.pack('<8I',10,32,c[1],c[2],0,0,0,0)+bytes(heap[c[3]-BASE:c[3]-BASE+c[4]])
  command=PixelCommand(PixelRect(*dst),PixelRect(*src),args[3],args[4],m.stack)
  source=(C.c_uint8*len(data)).from_buffer_copy(data);capacity=current['pitch']*current['h'];coverage=(C.c_uint8*capacity)();info=PixelInfo()
  output=C.cast(C.addressof(heap)+pixels-BASE,C.POINTER(C.c_uint8))
  assert lib.claw_pid_blit8(source,len(data),C.byref(command),output,coverage,capacity,current['pitch'],C.byref(info)),('pixel blitter rejection',c,dst,src)
  nativeEntry(0x4bb0e0,args[1],[]);return 1
 if fn==0x546d58:
  dst[:]=src[:]
  if policy==2:
   put(IMAGE+0x28,[0x10,BASE+0x7800,BASE+0x7900]);put(TARGET+0x2c,[BASE+0x7a00]);put(ACTOR+0x10,[99,100]);put(ACTOR+0x4c,[800,900])
   dst[0]+=1;dst[1]+=2
 else:
  if policy==1:
   if dst is not None:dst[0]+=3;dst[1]+=4;dst[2]+=5;dst[3]+=6
   if src is not None:src[0]+=7;src[1]+=8
  elif policy==3:
   put(ACTOR+0x18,[0xdead]*9);put(ACTOR+0x40,[0x1234,0x5555,0x6666]);gs(1,0xfedc)
 return 0x88760001
@Service
def service(_,c):
 dst=[c.destination[i]for i in range(4)]if c.destination else None;src=[c.source[i]for i in range(2 if c.function==KEY else 4)]if c.source else None
 value=effect(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]),dst,src)
 if dst is not None:
  for i,x in enumerate(dst):c.destination[i]=x
 if src is not None:
  for i,x in enumerate(src):c.source[i]=x
 return value
host=Host(scene,None,service)
def returned(pop,result):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 if address==0x4f63ec:
  returned(0,allocate(None,m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)[0]));return
 if address==0x4f6428:
  free(None,m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)[0]);returned(0,0);return
 if address in(CREATE,DESCRIBE,LOCK,KEY,UNLOCK,0x4f51c5,0x4bd260,0x4bc5f0,0x4bc740,0x4f582f,0x4ce8e0):
  counts={CREATE:4,DESCRIBE:2,LOCK:5,KEY:3,UNLOCK:2,0x4f51c5:1,0x4bd260:3,0x4bc5f0:1,0x4bc740:3,0x4f582f:2,0x4ce8e0:1};sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,counts[address]);recv=u.reg_read(UC_X86_REG_ECX);src=None
  if address in(CREATE,DESCRIBE,LOCK,KEY,UNLOCK,0x4bd260):recv=0
  if address==KEY:src=m.read_words(args[2],2);args[2]=0
  value=effect(address,recv,tuple(args),None,src);returned(0 if address==0x4bd260 else counts[address]*4,value);return
 if address not in(COPY,0x4b9d80,0x4b9ce0,0x4bffa0):return
 sp=u.reg_read(UC_X86_REG_ESP);recv=u.reg_read(UC_X86_REG_ECX);a=m.read_words(sp+4,2 if address==COPY else 5);dt=st=0
 if address==COPY:fn=0x546d58;recv=0;dt,st=a;args=(0,0)
 elif address==0x4b9d80:fn=address;st=a[3];args=(a[0],a[1],a[2],0,a[4])
 elif address==0x4b9ce0:fn=address;dt,st=a[0],a[2];args=(0,a[1],0,a[3],a[4])
 else:fn=address;dt,st=a[0],a[2];args=(0,a[1],0,a[3],a[4])
 dst=m.read_words(dt,4)if dt else None;src=m.read_words(st,4)if st else None
 if address==0x4bffa0 and pixelDraw:
  assert 0<m.read_words(sp+12,1)[0]<0x7fffffff
  effect(fn,recv,args,dst,src);return
 result=effect(fn,recv,args,dst,src)
 if dt:m.write_words(dt,dst)
 if st:m.write_words(st,src)
 returned(8 if address==COPY else 20,result)
u.hook_add(UC_HOOK_CODE,hook)
def reset():
 global native,g,events,policy,cursor,loading,current,freeList,pixelDraw
 cursor=BASE+0x40000;loading=False;current={};freeList=[];pixelDraw=False;native=True;events=[];policy=0;pattern=rng.randbytes(4096);C.memmove(C.addressof(heap),pattern*(SIZE//4096),SIZE);g=Globals.from_buffer_copy(rng.randbytes(C.sizeof(Globals)));g.animationDelta=18
 put(IMAGE,[0x513a70,42,0,PARENT,127,135,63,67,(-7)&0xffffffff,9,0x11,BASE+0x7800,0])
 put(ACTOR+8,[0x40000]);put(ACTOR+0x10,[3,(-4)&0xffffffff]);put(ACTOR+0x3c,[HOLDER,0,18,50,400,300,0x80000000,0,0,0]);put(HOLDER+0x5c,[PLANE]);put(PARENT+0x24,[WORLD]);put(WORLD+0x10,[0,0,639,479]);put(TARGET+0x10,[640,480]);put(TARGET+0x2c,[BASE+0x7a00]);put(PLANE+8,[0]);put(PLANE+0x30,[24576,6144,64,64,80,100,719,579,0,0])
def compare(fn,receiver,args,label):
 global native,events,calls,eventCount,cursor,freeList
 initialCursor=cursor;initialFree=freeList[:]
 before=bytes(heap);gb=bytes(g);arguments=Args();arguments.count=len(args);arguments.words[:len(args)]=args;fault=U();result=U();events=[]
 assert lib.claw_game_image_entry(fn,receiver,arguments,C.byref(g),host,C.byref(fault),C.byref(result))==1 and fault.value==0,(label,fault.value)
 expected=snapshot();expectedEvents=events[:];expectedHeap=bytes(heap);expectedG=bytes(g);expectedCursor=cursor;expectedFree=freeList[:]
 native=False;cursor=initialCursor;freeList=initialFree[:];u.mem_write(BASE,before);offset=0
 for t,n in regions:u.mem_write(t,gb[offset:offset+n*4]);offset+=n*4
 events=[];machineResult=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*args));actual=snapshot()
 assert events==expectedEvents,(label,'events',[(a[0],b[0],a[1]==b[1])for a,b in zip(expectedEvents,events)],len(events),len(expectedEvents))
 assert actual==expected,(label,'final',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(SIZE//4),expectedHeap),struct.unpack('<'+'I'*(SIZE//4),u.mem_read(BASE,SIZE))))if x!=y],expectedG.hex(),globalBytes().hex())
 assert cursor==expectedCursor and freeList==expectedFree,(label,'heap ownership')
 if fn not in(0x4d2890,0x4b9990,0x4bb0e0,0x4bc490,0x4c6130):assert machineResult==result.value,(label,'return',machineResult,result.value)
 native=True;events=expectedEvents;calls+=1;eventCount+=len(events)
 return result.value

def loadingFixture(data):
 global loading,current
 reset();loading=True;flags,width,height=struct.unpack_from('<3I',data,4);current={'w':width,'h':height,'pitch':width+4};put(PARENT+0x1c,[MANAGER]);put(PARENT+4,[HOLDER]);put(HOLDER+0x10,[TARGET]);put(TARGET+0x18,[8]);put(MANAGER,[0]*600);put(MANAGER,[DISPLAY]);put(MANAGER+0x474,[8]);put(DISPLAY,[DISPLAYVT]);put(DISPLAYVT+0x18,[CREATE]);put(DD,[DDVT]);
 for offset,f in ((0x58,DESCRIBE),(0x64,LOCK),(0x74,KEY),(0x80,UNLOCK)):put(DDVT+offset,[f])
 put(IMAGE+0x30,[0]);g.surfaceLoadFlags=0;g.surfaceColorKey=0;C.memmove(C.addressof(heap)+RAW-BASE,data,len(data));assert len(data)<0x20000
 return flags,width,height

def pixelTarget():
 global pixelDraw,current
 pixelDraw=True;current={'w':640,'h':480,'pitch':656};surface=BASE+0xf800;put(surface,[0]*47);put(surface,[0x513690,0,DD]);descriptor(surface+0xc);put(surface+0xa4,[8]);put(TARGET+0x2c,[surface]);return surface
