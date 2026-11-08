"""Private original single-player startup graph oracle with explicit services."""
import ctypes as C,struct,random,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_ESI,UC_X86_REG_EBX,UC_X86_REG_EBP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/single-player-scene-agent';WORK.mkdir(exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['SinglePlayerSceneRuntime.cpp','WorldFileRuntime.cpp','WorldPlaneRuntime.cpp','CArrayRuntime.cpp','SceneCameraRuntime.cpp','SpatialGridRuntime.cpp','SpriteGeometry.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']],'-o',str(WORK/'libSinglePlayerSceneRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libSinglePlayerSceneRuntime.dylib'))
class ActorCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,ActorCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('words',C.c_uint32*21)]
GADDR=[0x538418,0x54316c,0x537210,0x53c9c0,0x5349dc,0x537e88,0x534ca4,0x52be14,0x52be18,0x537204,0x53ec44,0x537268,0x537214,0x537218,0x53721c,0x537220,0x537228,0x537224,0x53722c,0x537230,0x537264]
class Camera(C.Structure):_fields_=[('words',C.c_uint32*12)]
CADDR=[0x537e88,0x537200,0x537204,0x53720c,0x537258,0x5430c8,0x5430c4,0x52be14,0x52be18,0x53c25c,0x53c260,0x53c264]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*8),('localMask',C.c_uint32),('bufferCount',C.c_uint32),('buffers',C.c_void_p*3),('bufferBytes',C.c_uint32*3)]
class Context(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(Globals)),('camera',C.POINTER(Camera))]+[(n,C.c_uint32)for n in('composeBase','composeLevel','composeCamera','composeSpatial','fault')]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),Call,C.c_void_p)
lib.claw_single_player_scene_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_single_player_scene_entry.restype=C.c_uint32
lib.claw_single_player_scene_construct.argtypes=[C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p];lib.claw_single_player_scene_construct.restype=C.c_uint32
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);m.executed.clear();BASE,SIZE=0x1000000,0x100000;heap=(C.c_uint8*SIZE)();globals=Globals();camera=Camera();native=True;events=[];errors=[];calls=eventCount=inlineSpans=0;policy=0;failAt=-1;gateIndex=0;cursorIndex=0;constructed=False;nextAllocation=BASE+0x12000;allocationFailure=-1;allocationCount=0;initFailure=0;initCall=0;initCallFailure=-1;worldProfile=0;GRIDPLANE=BASE+0xe000
OWNER,MGR,SCENE,RESOURCE,PALETTE,PALETTE_HANDLE,PALETTE_COM,PCONT,ICONT,WORLD,SURFACE,DEVICE,DRAW,OUTPUT,ACTORS,ANICTRL,SOUND,MAP,PLAYER,LOGIC,INPUT,INPUTDEV,SAVE,OTHER,MUSIC,TRACK=[BASE+0x1000+i*0x800 for i in range(26)]
VT=BASE+0x100;PVT=BASE+0x200;CVT=BASE+0x300;IVT=BASE+0x400;WVT=BASE+0x500
PALCREATE,PALREAD,PALUSE,IMAGELOAD,WLOAD,WLOADFILE,PLAYERUPDATE=[0x10e0000+i*0x10 for i in range(7)]
IMPORTS={slot:0x10e0100+i*0x10 for i,slot in enumerate((0x546d54,0x546ccc,0x546ce4,0x546c44,0x546d9c,0x546df0))};REV={v:k for k,v in IMPORTS.items()}
for slot,fn in IMPORTS.items():m.write_words(slot,[fn])
def words(t,n=1):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def gv():return list(globals.words)if native else [m.read_words(a,1)[0]for a in GADDR]
def cg():
 if not native:return [m.read_words(a,1)[0]for a in CADDR]
 v=list(camera.words);g=gv();v[0]=g[5];v[2]=g[9];v[7]=g[7];v[8]=g[8];return v

def setg(i,v):
 if native:globals.words[i]=v&0xffffffff
 else:m.write_words(GADDR[i],[v])
def snapshot():return(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+struct.pack('<21I',*gv())+struct.pack('<12I',*cg())+(bytes(imageFX)if native else bytes(u.mem_read(0x543108,100)))+(bytes(clockWords)if native else bytes(u.mem_read(0x541328,20)))
def blob(t,n):return C.string_at(t,n)if native else bytes(u.mem_read(t,n))
def writebuf(p,v):
 data=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(p,data,len(data))
 else:u.mem_write(p,data)
def strbuf(p):return blob(p,256).split(b'\0')[0]
def effect(fn,receiver,args,buffers):
 global gateIndex,cursorIndex,nextAllocation,allocationCount,initCall
 payload=()
 if fn==0x4b7f20 and args[0]==0:payload=(strbuf(buffers[0]),)
 if fn==0x4f6584 and receiver==0:payload=(blob(buffers[0],4),)
 events.append(((fn,receiver,tuple(args),payload),snapshot()))
 gated=fn in(0x4b7f20,0x4b7dc0,0x4b7cd0,PALCREATE,0x46e160,WLOAD,WLOADFILE,0x452b00,0x4c8da0)
 if gated:
  gateIndex+=1
  if gateIndex==failAt:return 0
 if fn==0x4f63ec:
  allocationCount+=1
  if allocationCount==allocationFailure:return 0
  token=nextAllocation;nextAllocation+=(args[0]+15)&~15;return token
 if fn in(0x4f5620,0x4f6118,0x4f5cbd):put(receiver,[0]*7);return 0
 if fn in(0x4bc120,0x4b4710):put(receiver,[0x513ab8]);return receiver
 if fn in(0x4bd250,0x4cfa60,0x4cdf20,0x4ca6f0,0x4b47e0,0x4ca280):
  initCall+=1
  if fn==initFailure or initCall==initCallFailure:return 0
  if fn==0x4ca6f0:put(receiver+0x10,[DEVICE,DRAW])
  return 1
 if fn==0x4f701d:return receiver
 if fn==0x4f6439:put(receiver,[0x534938]);return receiver
 if fn==0x4f6449:writebuf(buffers[0],[words(args[0])[0]]);return 0
 if fn==0x436e60:return 1 if policy!=1 else 0
 if fn==0x4f650f:put(words(receiver)[0]-8,[0]);return 0
 if fn==0x4f6584:return 0
 if fn==0x546d54:cursorIndex+=1;return (1-(cursorIndex%3))&0xffffffff
 if fn==0x4f6428:return 0
 if fn==0x4a3920:
  fmt=bytes(u.mem_read(args[1],256)).split(b'\0')[0].decode('ascii');i=args[2]if args[2]<0x80000000 else args[2]-0x100000000;s=(fmt%i).encode()+b'\0'
  if native:C.memmove(buffers[0],s,len(s))
  else:u.mem_write(buffers[0],s)
  return len(s)-1
 if fn==0x4b7f20:return RESOURCE
 if fn in(0x4b7dc0,0x4b7cd0):return MUSIC if args[0]==0x526a58 else RESOURCE
 if fn in(PALCREATE,0x4d4420):return PALETTE
 if fn==PALREAD:put(args[4],list(range(256)));return 0
 if fn==0x4c8da0:
  if args[4]==0x522e80:return PLAYER
  return OTHER
 if fn==PLAYERUPDATE:
  put(PLAYER+0x4c,[720,4720]);put(LOGIC+0x1c,[24]);return 1
 if fn in(WLOAD,WLOADFILE,0x4cb5a0,0x4cb470):put(receiver+0x5c,[GRIDPLANE if worldProfile else 0]);return 1
 if fn==0x42a450:writebuf(buffers[0],[640,1 if policy==2 else 0]);return 0
 if fn==0x48bfd0:return policy%2
 if fn==0x4b67f0:return 0 if policy==3 and args[0]in(0x529fcc,0x529fc4,0x529fb0)else TRACK
 if fn==0x4b61c0:return RESOURCE
 if fn==0x46e160:return 1
 if fn==0x452b00:return 1
 if fn==0x46dff0:
  if policy==4 and args[0]==75:put(OWNER+0x154,[0])
  if policy==5 and args[0]==65:put(MGR+0x9c,[1])
  return 1
 if fn==0x42a000:put(receiver+0x7c,[640,480]);return 1
 if fn in(0x4a3040,0x4bb870,0x4bb990,0x4bb910,0x4b97c0,0x4b98b0,PALUSE,IMAGELOAD,0x4cff40,0x546ccc,0x48f3e0,0x46f040,0x46db30,0x46e100,0x46b7b0,0x46bb80,0x4ca440,0x4ce0d0,0x42abf0,0x4cdcb0,0x42ae70,0x415ce0,0x46c790,0x46d8e0,0x4c8b90,0x4c8f60,0x4719e0,0x46caf0,0x46ef80,0x4b5340,0x4b53f0,0x4b8910,0x4b8960,0x4d46f0,0x546ce4,0x546d9c):return 1
 if fn==0x546df0:return clockValue
 if fn==0x546c44:return 640 if args[0]==0 else 480
 raise AssertionError(('unknown dependency',hex(fn),hex(receiver),args))
@Lookup
def lookup(_,t,n):
 if t==0x541328 and n<=5:return C.addressof(clockWords)
 if t==0x543108 and n<=25:return C.addressof(imageFX)
 if t==0x52e1cc and n==1:return C.addressof(emptyCell)
 if 0x500000<=t and t+4*n<0x546000:
  key=(t,n)
  if key not in staticSpans:staticSpans[key]=(C.c_uint32*n)(*m.read_words(t,n))
  return C.addressof(staticSpans[key])
 return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
@Dependency
def dependency(_,q,user):
 try:return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]),list(q.buffers[:q.bufferCount]))
 except Exception as e:errors.append(e);return 0
staticSpans={}
imageFX=(C.c_uint32*25)();clockWords=(C.c_uint32*5)();clockValue=1000
emptyCell=C.c_uint32(m.read_words(0x52e1cc,1)[0])
@Clock
def readClock(_):return effect(0x546df0,0,[],[])
@Allocate
def allocateHost(_,n):return effect(0x4f63ec,0,[n],[])
@Free
def freeHost(_,t):effect(0x4f6428,0,[t],[])
@Invoke
def invokeHost(_,call):return effect(call.function,call.receiver,list(call.arguments[:call.argumentCount]),[])
host=Host(None,lookup,allocateHost,freeHost,invokeHost,readClock);context=Context(host,C.pointer(globals),C.pointer(camera),1,1,1,1,0)
# Full argument/cleanup metadata, verified against original calls/returns.
# (count,cleanup,mask,temporary receiver,cdecl/COM/import)
META={0x4f6428:(1,0,0,False,True),0x4d4420:(3,3,0,False,False),0x4cff40:(3,3,0,False,False),0x4cb5a0:(1,1,0,False,False),0x4cb470:(1,1,0,False,False),0x546df0:(0,0,0,False,True),0x4f63ec:(1,0,0,False,True),0x4bc120:(0,0,0,False,False),0x4b4710:(0,0,0,False,False),0x4ca6f0:(4,4,0,False,False),0x4b47e0:(2,2,0,False,False),0x4ca280:(1,1,0,False,False),0x4f701d:(1,1,0,False,False),0x42a000:(1,1,0,False,False),0x4f6449:(1,1,0,True,False),0x436e60:(1,0,0,False,True),0x4f650f:(0,0,0,False,False),0x4f6584:(0,0,0,True,False),0x4a3920:(3,0,1,False,True),0x4b7f20:(1,1,0,False,False),0x4b7dc0:(2,2,0,False,False),0x4b7cd0:(1,1,0,False,False),0x546d54:(1,1,0,False,True),0x546ccc:(1,1,0,False,True),0x4a3040:(1,0,0,False,True),PALCREATE:(3,3,0,False,False),PALREAD:(5,5,0,False,True),PALUSE:(0,0,0,False,False),IMAGELOAD:(3,3,0,False,False),WLOAD:(1,1,0,False,False),WLOADFILE:(1,1,0,False,False),PLAYERUPDATE:(1,0,0,False,True),0x4bb870:(0,0,0,False,False),0x4bb990:(6,6,0,False,False),0x4bb910:(6,6,0,False,False),0x4b97c0:(1,1,0,False,False),0x4b98b0:(1,1,0,False,False),0x46db30:(0,0,0,False,False),0x48f3e0:(5,5,0,False,False),0x46f040:(0,0,0,False,False),0x46e100:(0,0,0,False,False),0x46b7b0:(0,0,0,False,False),0x46dff0:(1,1,0,False,False),0x46bb80:(0,0,0,False,False),0x46e160:(0,0,0,False,False),0x4ca440:(3,3,0,False,False),0x4ce0d0:(3,3,0,False,False),0x42abf0:(0,0,0,False,False),0x4cdcb0:(0,0,0,False,False),0x42ae70:(0,0,0,False,False),0x452b00:(1,0,0,False,True),0x4c8da0:(6,6,0,False,False),0x415ce0:(0,0,0,False,True),0x46c790:(0,0,0,False,False),0x46d8e0:(0,0,0,False,False),0x4c8b90:(4,4,0,False,False),0x4c8f60:(6,6,0,False,False),0x4719e0:(1,0,0,False,True),0x42a450:(1,1,1,False,False),0x46caf0:(0,0,0,False,False),0x46ef80:(0,0,0,False,False),0x48bfd0:(0,0,0,False,True),0x4b5340:(0,0,0,False,False),0x4b67f0:(2,2,0,False,False),0x4b61c0:(0,0,0,False,False),0x4b53f0:(3,3,0,False,False),0x4b8910:(2,2,0,False,False),0x4b8960:(1,0,0,False,True),0x4d46f0:(1,1,0,False,False),0x546ce4:(1,1,0,False,True),0x546c44:(1,1,0,False,True),0x546d9c:(2,2,0,False,True)}
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+4*pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 if constructed and address==0x428dce:u.reg_write(UC_X86_REG_ESP,m.stack+4);u.reg_write(UC_X86_REG_EIP,m.stop);return
 fn=REV.get(address,address)
 if address==SETRECT:
  sp=uc.reg_read(UC_X86_REG_ESP);v=m.read_words(sp+4,5);m.write_words(v[0],v[1:]);returned(5,1);return
 if fn not in META:return
 argc,pop,mask,localReceiver,cdecl=META[fn];sp=uc.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,argc);receiver=0 if cdecl else uc.reg_read(UC_X86_REG_ECX);buffers=[]
 if fn==0x4a3920 and args[0]>=BASE and args[0]<BASE+SIZE:mask=0;buffers=[args[0]]
 elif fn==0x4b7f20 and 0x2000000<=args[0]<0x2010000:mask=1
 for i in range(argc):
  if mask&(1<<i):buffers.append(args[i]);args[i]=0
 if localReceiver:buffers.append(receiver);receiver=0
 if fn==PALREAD:buffers.append(args[4])
 result=effect(fn,receiver,args,buffers);returned(pop,result)
SETRECT=0x10e0200
m.write_words(0x546d5c,[SETRECT])
u.hook_add(UC_HOOK_CODE,hook)
def setup(seed=0,saved=False):
 global native,gateIndex,cursorIndex,nextAllocation,allocationCount,allocationFailure,initFailure,initCall,initCallFailure,worldProfile
 worldProfile=0
 initCall=0;initCallFailure=-1
 nextAllocation=BASE+0x12000;allocationCount=0;allocationFailure=-1;initFailure=0
 native=True;gateIndex=cursorIndex=0;r=random.Random(seed);C.memmove(heap,r.randbytes(SIZE),SIZE)
 put(OWNER,[0]*478);put(OWNER,[0x50c264]);put(OWNER+4,[MGR]);put(OWNER+8,[MAP]);put(OWNER+0xc,[SCENE]);put(OWNER+0x24,[RESOURCE,RESOURCE,0,0]);put(OWNER+0x154,[1]);put(MGR,[0]*81);put(MGR+4,[DEVICE]);put(DEVICE,[0,123]);put(MGR+0x30,[SCENE,MAP]);put(MGR+0x44,[OTHER,OTHER]);put(MGR+0x50,[OTHER]);put(MGR+0x7c,[640,480]);put(MGR+0xc0,[SAVE+12]);put(SAVE,[1,7 if saved else 0,32]);put(SCENE,[0]*12);put(SCENE+4,[SURFACE,ACTORS,0,ICONT,0,PCONT]);put(SCENE+0x24,[WORLD,SOUND,ANICTRL]);put(SURFACE+0x10,[DEVICE,DRAW]);put(DEVICE+0x2c,[OUTPUT]);put(DRAW+0x2c,[OUTPUT]);put(PCONT,[PVT]);put(PVT+0x24,[PALCREATE]);put(PALETTE,[VT]);put(VT+0x34,[PALUSE]);put(PALETTE+0x10,[PALETTE_HANDLE]);put(PALETTE_HANDLE+4,[PALETTE_COM]);put(PALETTE_COM,[CVT]);put(CVT+0x10,[PALREAD]);put(ICONT,[IVT]);put(IVT+0x48,[IMAGELOAD]);put(WORLD,[WVT]);put(WVT+0x3c,[WLOAD]);put(WVT+0x40,[WLOADFILE]);put(WORLD+0x5c,[0]);put(PLAYER+0x6c,[LOGIC]);put(LOGIC+0x10,[PLAYERUPDATE]);put(INPUT,[0]*29);put(INPUT,[INPUTDEV]);put(INPUTDEV,[0]*146);put(INPUTDEV+0x1cc,[1]);put(INPUTDEV+0x1dc,list(range(12)));put(TRACK+0x14,[256]);globals.words[:]=[r.getrandbits(32)for _ in range(21)];globals.words[5]=PLAYER;globals.words[9]=INPUT;globals.words[10]=42;camera.words[:]=[0]*12;camera.words[9]=3;camera.words[11]=OTHER;imageFX[:]=[r.getrandbits(32)for _ in range(25)];clockWords[:]=[r.getrandbits(32)for _ in range(5)]
 return bytes(heap),bytes(globals),bytes(camera)
def load(h,g,c):
 global gateIndex,cursorIndex,initCall
 initCall=0
 gateIndex=cursorIndex=0
 if native:C.memmove(heap,h,SIZE);C.memmove(C.byref(globals),g,len(g));C.memmove(C.byref(camera),c,len(c))
 else:
  u.mem_write(BASE,h);[m.write_words(a,[v])for a,v in zip(GADDR,struct.unpack('<21I',g))]
  for i,(a,v)in enumerate(zip(CADDR,struct.unpack('<12I',c))):
   if i not in(0,2,7,8):m.write_words(a,[v])
  u.mem_write(0x543108,bytes(imageFX));u.mem_write(0x541328,bytes(clockWords));m.write_words(0,[0x12345678])
def receiver(fn):return MGR if fn in(0x42af50,0x4254a0,0x4b8240)else SCENE if fn in(0x4ce960,0x4cea10)else WORLD if fn==0x4cace0 else OTHER if fn in(0x45fde0,0x4f5620,0x4f6118,0x4f5cbd)else OWNER

def execute(fn,args=()):
 global constructed,calls,eventCount,inlineSpans
 events.clear();errors.clear()
 if native:
  result=C.c_uint32()
  if fn=='construct':ret=lib.claw_single_player_scene_construct(OWNER,C.byref(context),dependency,None)
  else:
   raw=(C.c_uint32*len(args))(*args);assert lib.claw_single_player_scene_entry(fn,receiver(fn),raw,len(args),C.byref(context),dependency,None,C.byref(result));ret=result.value
  assert not context.fault,context.fault;assert not errors,errors
 else:
  if fn=='construct':
   constructed=True;u.reg_write(UC_X86_REG_ESI,OWNER);u.reg_write(UC_X86_REG_EBX,0);u.reg_write(UC_X86_REG_EBP,1);m.call(0x428d81,OWNER);constructed=False;ret=OWNER
  else:ret=m.call(fn,receiver(fn),struct.pack('<'+'I'*len(args),*args))
  assert m.read_words(0,1)==[0x12345678]
  if fn!='construct':assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(args)*4
 calls+=1;inlineSpans+=fn=='construct';eventCount+=len(events);return snapshot(),list(events),ret if fn not in(0x40b5c0,0x42aa50,0x45fde0)else 0,gateIndex,cursorIndex

def compare(fn,args=()):
 global native,nextAllocation,allocationCount
 native=True;beforeFX=bytes(imageFX);beforeClock=bytes(clockWords);beforeAllocation=(nextAllocation,allocationCount);h,g,c=bytes(heap),bytes(globals),bytes(camera);load(h,g,c);a=execute(fn,args);afterAllocation=(nextAllocation,allocationCount);native=False;C.memmove(imageFX,beforeFX,100);C.memmove(clockWords,beforeClock,20);load(h,g,c);nextAllocation,allocationCount=beforeAllocation;b=execute(fn,args)
 if a!=b:
  diffs=[(hex(BASE+i),a[0][i:i+4].hex(),b[0][i:i+4].hex())for i in range(0,len(a[0]),4)if a[0][i:i+4]!=b[0][i:i+4]]
  print('diff',fn,policy,failAt,diffs[:15]);print('calls native',[x[0]for x in a[1]]);print('calls original',[x[0]for x in b[1]]);print('eventdifferences',[(i,x[0],y[0],x[1]==y[1])for i,(x,y)in enumerate(zip(a[1],b[1]))if x!=y][:3]);raise AssertionError((fn,a[2:],b[2:]))
 assert afterAllocation==(nextAllocation,allocationCount)
 native=True;C.memmove(heap,a[0][:SIZE],SIZE);C.memmove(C.byref(globals),a[0][SIZE:SIZE+84],84);C.memmove(C.byref(camera),a[0][SIZE+84:SIZE+132],48);C.memmove(imageFX,a[0][SIZE+132:SIZE+232],100);C.memmove(clockWords,a[0][SIZE+232:],20);return a
