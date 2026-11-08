"""Pinned original full application dispatch and retained-owner transition oracle."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/application-level-progression-agent';U=C.c_uint32
sources=list((ROOT/'Sources').glob('*.cpp'));support=WORK/'libProgressionFrozenSupport.dylib';out=WORK/'libProgressionCurrent.dylib'
# Frozen source support library is built once; worker-only source rebuild is fast.
# The support library holds every module, this family's included: later modules call this family's entry, so
# leaving it out no longer links (changed 2026-10-12). The library under test is still built from this
# family's own source and is the one the comparison calls.
if not support.exists()or any(p.stat().st_mtime>support.stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(support)],check=True)
source=ROOT/'Sources/ApplicationLevelProgressionRuntime.cpp'
if not out.exists()or source.stat().st_mtime>out.stat().st_mtime:subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',str(source),str(support),'-o',str(out)],check=True)
lib=C.CDLL(str(out))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('alloc','free','call')]+[('clock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('application','progression','results','story','singlePlayer','special','lifecycle','arrays')]+[(n,U)for n in('composeTransitions','composeSinglePlayer','composeBooty','composeLifecycle','maximumOperations','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('bufferSizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_application_level_progression_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000
APP,OWNER,PRIOR,NEW,SC,WINDOW,RES,SURFACE,PAL,INPUT,KEY,PLAYER,PRIMARY,PRIVATE,HISTORY,FRAME,EXTRA=[BASE+0x1000+i*0x1000 for i in range(17)]
AVT,OVT,PVT,MUTVT=BASE+0x20000,BASE+0x21000,BASE+0x22000,BASE+0x23000
READY,MODE,DEPART,DELETE,ENTER,RECOVER,CREATEINIT,EXTRAMODE=0x4000020,0x4000040,0x4000060,0x4000080,0x40000a0,0x40000c0,0x40000e0,0x4000100
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x4000000,4096);m.stack=0x200e000;m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();ctx=Context();ctx.maximumOperations=65536;application=(U*13)();ctx.application=C.addressof(application)
rng=random.Random(0x429be0);events=[];originalEvents=[];errors=[];calls=eventCount=0;freed=[];created=[];cursor=BASE+0x30000;clockIndex=0;clockValues=[123456,123470,123471,123490];ready=1;modeValues=[10];modeIndex=0;priorMode=3;levelOutcomes=[1];levelIndex=0;initResult=enterResult=recoverResult=1;allocationFail=0;allocationIndex=0;transitionOutcomes=[1];transitionIndex=0;mutations={};lastCaller=0;unsafeCases=[]
ALIASES=(0x537e88,0x532c10,0x537204,0x537200,0x541328,0x54132c,0x541330,0x541334,0x541338,0x537208,0x53720c,0x5430c8,0x5430c4)
ABIS={READY:(0,0),MODE:(0,0),EXTRAMODE:(0,0),DEPART:(1,4),DELETE:(1,4),ENTER:(1,4),RECOVER:(0,0),CREATEINIT:(3,12),0x428c40:(4,16),0x42abf0:(0,0),0x46aeb0:(2,8),0x4f650f:(0,0),0x4f6439:(0,0),0x4f6584:(0,0),0x4f6449:(1,4),0x4f66cc:(1,4),0x40b5c0:(0,0),0x4296f0:(4,16),0x4f63ec:(1,0),0x4f6428:(1,0),0x4a4a80:(3,0),0x546d50:(4,16),0x546df0:(0,0),0x431300:(0,0),0x4b3ab0:(0,0),0x429e10:(2,8),0x4dcc40:(2,8),0x4f5cbd:(1,4),0x546d5c:(5,20)}
CDECL=(0x4f63ec,0x4f6428,0x4a4a80,0x546d50,0x546df0)
STATEVT={0x50c174:8,0x50c264:3,0x50c1e4:5,0x50b4ec:0}
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def raw(native):return bytes(heap)+C.string_at(ptr(0x520000),0x30000)if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
def text(t,native=True):
 if native:return C.string_at(ptr(t&~3)+t%4).split(b'\0')[0]
 return bytes(m.u.mem_read(t,16384)).split(b'\0')[0]
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('span',hex(t),n))
 return p
def readClock(native):
 global clockIndex
 value=clockValues[clockIndex%len(clockValues)];clockIndex+=1;events.append((0x546df0,0,(),None,0,(),snap(True)))if native else originalEvents.append((0x546df0,0,(),None,0,(),snap(False)));return value
@Clock
def clock(_):return readClock(True)
ctx.scene=Host(None,lookup,None,None,None,clock)
def allocated(n,native):
 global cursor
 value=cursor;cursor+=(n+15)&~15;assert cursor<BASE+SIZE;created.append((value,n));return value
# Boundary methods deliberately expose mutation/order and configurable actual outcomes.
def effect(f,t,a,n,native):
 global modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex
 if f==READY:return ready
 if f in(MODE,EXTRAMODE):
  if t==PRIOR:return priorMode
  value=modeValues[modeIndex%len(modeValues)];modeIndex+=1;return value
 if f in(DEPART,0x46ab30):return 1
 if f in(DELETE,0x429480,0x429510):
  if a[0]&1:freed.append(t)
  return t
 if f in(ENTER,0x46a8d0,0x45b3f0):return enterResult
 if f==RECOVER:return recoverResult
 if f in(CREATEINIT,0x46a6d0,0x45ace0):put(t+4,[a[0],RES,SC,0,a[1],a[2]],native);return initResult
 if f==0x428c40:
  value=transitionOutcomes[transitionIndex%len(transitionOutcomes)];transitionIndex+=1;return value
 if f==0x46aeb0:
  value=levelOutcomes[levelIndex%len(levelOutcomes)];levelIndex+=1;put(t+20,[a[0]],native);return value
 if f==0x4f650f:put(t,[0x52e1c4],native);return 0
 if f==0x4f6439:put(t,[0x52e1c4],native);return t
 if f==0x4f6449:
  value=get(a[0],native=native)[0]
  if BASE<=value<BASE+SIZE:
   refs=get(value-12,native=native)[0]
   if refs!=0xffffffff:put(value-12,[refs+1],native)
  put(t,[value],native);return t
 if f==0x4f6584:
  value=get(t,native=native)[0]
  if BASE<=value<BASE+SIZE:
   refs=get(value-12,native=native)[0]
   if refs!=0xffffffff:
    put(value-12,[refs-1],native)
    if refs==1:freed.append(value-12)
  return 0
 if f==0x40b5c0:
  put(t,[0x50b4ec],native)
  for off in(4,8,12,0x1c,0x20,0x24,0x2c,0x30,0x3c,0x40,0x34,0x18,0x150):put(t+off,[0],native)
  value=get(t+0x4c,native=native)[0];put(t+0x4c,[value&0xffffff00],native);return 0
 if f==0x4296f0:put(t,a,native);return t
 if f==0x4f63ec:
  allocationIndex+=1;return 0 if allocationFail==allocationIndex else allocated(a[0],native)
 if f==0x4f6428:freed.append(a[0]);return 0
 if f==0x4a4a80:
  b=C.string_at(ptr(a[1]),a[2])if native else bytes(m.u.mem_read(a[1],a[2]))
  if native:C.memmove(ptr(a[0]),b,len(b))
  else:m.u.mem_write(a[0],b)
  return a[0]
 if f in(0x546d50,0x42abf0,0x431300,0x4b3ab0,0x429e10):return 0
 if f==0x4dcc40:put(t,[0x50be98,a[0],a[1]],native);return t
 if f==0x4f5cbd:put(t,[0x510054,0,17,0,0,0,a[0]],native);return t
 if f==0x546d5c:put(a[0],a[1:],native);return 1
 if f in(0x40af90,0x4c9bd0,0x4295b0):return{0x40af90:3,0x4c9bd0:5,0x4295b0:8}[f]
 if f==0x48f0d0:put(t+4,[a[0],RES,SC,0,a[1],a[2]],native);return baseInit
 if f==0x4b7f20:return 0 if missingResource==a[0] else RES
 if f in(0x4b68c0,0x4b7cd0):return 0 if missingResource==a[0] else RES
 if f==0x4b67f0:return 0 if missingResource==a[0] else FILE
 if f==0x4b61c0:return 0 if missingFile else DATA
 if f==0x4f66cc:
  old=get(t,native=native)[0]
  if BASE<=old<BASE+SIZE:
   refs=get(old-12,native=native)[0]
   if refs!=0xffffffff:
    put(old-12,[refs-1],native)
    if refs==1:freed.append(old-12)
  payload=text(a[0],native);value=allocated(len(payload)+13,native);put(value,[1,len(payload),len(payload)],native)
  if native:C.memmove(ptr(value+12),payload+b'\0',len(payload)+1)
  else:m.u.mem_write(value+12,payload+b'\0')
  put(t,[value+12],native);return t
 if f==0x4fd6db:put(t+4,[a[0]],native);return 1
 if f==0x54688c:return 0xabc
 if f==0x546d30:
  if drawMutation:put(a[3],drawMutation,native)
  return drawHeight
 if f==GETDC:put(a[1],[dcValue],native);return 0
 if f==0x546d54:
  result=showCursorValues[showCursorIndex%len(showCursorValues)];showCursorIndex+=1;return result
 if f==0x546cd4:return int(0<=a[1]<100 and 0<=a[2]<100)
 if f==0x4a3050:
  value=randomValues[randomIndex%len(randomValues)];randomIndex+=1;return value
 if f==0x4b54a0:return 0 if missingMusic else MUSIC1 if a[0]==0x526a50 else MUSIC2
 if f==0x4b5bd0:return musicPlaying
 if f==0x4f65f2:put(t,[a[0]],native);return t
 if f==0x48c190:return fileExists
 if f==0x42b4b0:put(t,[0x50e698],native);return t
 if f==0x42d4a0:put(t,[0x511190,0,0],native);return t
 if f==0x4f0000:put(t,[a[0]],native);return movieInit
 if f==0x4f02e0:put(t+32,[0x76543],native);return movieOpen
 if f==0x4f0610:return movieFrame
 if f==0x4ca930:return surfaceReady
 if f==0x40af20:return 1
 if f in(NOOPS)or f in(0x46a870,0x4f06e0,0x4efcd0,0x4f57f8,0x4f7369):return 1
 if f==0x42d4c0:put(t,[0x50c364],native);put(t,[0x50becc],native);return 0
 raise AssertionError(('service' ,hex(f),hex(t),a,n))
@Dep
def dep(_,q,u):
 try:
  e=q.contents;a=tuple(e.arguments[:e.count]);f=e.function;t=e.receiver;n=e.name;buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)];events.append((f,t,a,n,e.mask,tuple(buffers),snap(True)))
  if e.mask==256:
   value=0
   if f in(0x4f6449,0x4f65f2):
    token=get(a[0])[0]if f==0x4f6449 else a[0]
    if f==0x4f6449 and BASE<=token<BASE+SIZE:
     refs=get(token-12)[0]
     if refs!=0xffffffff:put(token-12,[refs+1])
    C.cast(e.buffers[0],C.POINTER(U))[0]=token
   elif f==0x4f6584:
    token=C.cast(e.buffers[0],C.POINTER(U))[0]
    if BASE<=token<BASE+SIZE:
     refs=get(token-12)[0]
     if refs!=0xffffffff:
      put(token-12,[refs-1])
      if refs==1:freed.append(token-12)
  elif f==GETDC:C.cast(e.buffers[0],C.POINTER(U))[0]=dcValue;value=0
  elif f==0x546cd4:value=int(0<=a[1]<100 and 0<=a[2]<100)
  elif f==0x546d30 and e.mask==8:value=drawHeight
  else:value=effect(f,t,a,n,True)
  for address,v in mutations.get(f,[]):put(address,[v])
  return value
 except Exception as ex:errors.append(ex);return 0

def hook(uc,f,size,user):
 global lastCaller
 if f not in ABIS:return
 if ctx.composeTransitions and f in(0x428c40,0x42abf0):return
 if ctx.composeTransitions and constructType==3 and f in(0x40b5c0,0x4f6439):return
 sp=uc.reg_read(UC_X86_REG_ESP);lastCaller=m.read_words(sp,1)[0];n,pop=ABIS[f];a=tuple(m.read_words(sp+4,n));t=0 if f in CDECL or f in GDI or f in(ATTACHDC,LOSTDC,GETDC,RELEASEDC) else uc.reg_read(UC_X86_REG_ECX)
 if f==0x546df0:
  value=readClock(False)
 else:
  eventT=t;eventA=list(a);mask=0;buffers=[]
  if f in(0x4f6449,0x4f65f2,0x4f6584)and m.stack-1024<t<m.stack:
   eventT=0;mask=256;buffers=[bytes(uc.mem_read(t,4))]
   if f in(0x4f6449,0x4f65f2):buffers=[bytes(4)] # native value-initialized local
  if f==GETDC:eventA[1]=0;mask=2;buffers=[bytes(uc.mem_read(a[1],4))]
  if f==0x546cd4:eventA[0]=0;mask=1;buffers=[bytes(uc.mem_read(a[0],16))]
  if f==0x546d30 and m.stack-1024<a[3]<m.stack:eventA[3]=0;mask=8;buffers=[bytes(uc.mem_read(a[3],16))]
  name=text(a[0],False)if a and f in NAMED else None
  originalEvents.append((f,eventT,tuple(eventA),name,mask,tuple(buffers),snap(False)));value=effect(f,t,a,None,False)
  for address,v in mutations.get(f,[]):put(address,[v],False)
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
class UnsafePrefix(Exception):pass
def nullAccess(uc,access,address,size,value,user):
 if address<4096 and bytes(uc.mem_read(uc.reg_read(UC_X86_REG_EIP),1))!=b'\x64':raise UnsafePrefix((hex(uc.reg_read(UC_X86_REG_EIP)),address,size))
m.u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,nullAccess)
def fresh(level=1):
 global cursor,clockIndex,ready,modeIndex,modeValues,priorMode,levelIndex,levelOutcomes,initResult,enterResult,recoverResult,allocationFail,allocationIndex,transitionIndex,transitionOutcomes,mutations
 C.memmove(C.addressof(image),imageSeed,len(image));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);ctx.fault=0;ctx.composeTransitions=ctx.composeSinglePlayer=ctx.composeBooty=ctx.composeLifecycle=0;cursor=BASE+0x30000;clockIndex=modeIndex=levelIndex=allocationIndex=transitionIndex=0;ready=initResult=enterResult=recoverResult=1;priorMode=3;modeValues=[10];levelOutcomes=[1];transitionOutcomes=[1];allocationFail=0;mutations={};freed.clear();created.clear()
 put(APP,[AVT]);put(AVT+12,[READY]);put(APP+4,[WINDOW,FRAME]);put(WINDOW+4,[0x1234]);put(APP+44,[OWNER,SC,RES]);put(APP+0xa0,[0]);put(APP+192,[0x52e1c4]);put(APP+256,[0x52e1c4]);put(APP+0xdc,[0x51079c,HISTORY,1,4,0]);put(HISTORY,[PRIOR,OWNER,0,0]);put(OWNER,[OVT]);put(PRIOR,[PVT]);
 for vt in(OVT,PVT,MUTVT):put(vt,[DELETE,CREATEINIT,0,READY,MODE,0,0,RECOVER,0,ENTER,DEPART])
 put(OWNER+4,[APP,RES,SC,0,level]);put(PRIOR+4,[APP,RES,SC,0,level]);put(OWNER+0x25c,[0]);put(OWNER+0x258,[0]);put(PRIOR+0x25c,[0]);put(PRIOR+0x258,[0]);put(FRAME+580,[0]);put(SC+4,[SURFACE]);put(SC+24,[PAL]);put(INPUT+524,[0]);put(KEY+12,[0]);put(PLAYER+108,[PRIMARY]);put(PRIMARY+20,[PRIVATE]);put(PRIVATE+288,[0]);put(0x5371fc,[APP]);put(0x537e88,[PLAYER]);put(0x532c10,[100]);put(0x537204,[KEY]);put(0x537200,[INPUT]);put(0x541328,[1000,17,17,200,3]);put(0x537208,[1000,17]);put(0x5430c8,[1000,17]);put(0x546df0,[0x546df0]);put(0x546d50,[0x546d50]);put(0x52e1cc,[0x52e1c4]);application[:]=[get(a)[0]for a in ALIASES]
def compare(f,label,args=(),receiver=APP,meaningful=True):
 global calls,eventCount,cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();freed.clear();created.clear();before=bytes(heap);bi=bytes(image);bapp=bytes(application);state=(cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex);out=U();a=(U*len(args))(*args);ok=lib.claw_application_level_progression_entry(f,receiver,a,len(args),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events);dead=list(freed);born=list(created);final=(cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(application),bapp,len(bapp));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex=state;freed.clear();created.clear();value=m.call(f,receiver,pack(*args));assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(args)*4,(label,'SP',hex(m.u.reg_read(UC_X86_REG_ESP)));got=raw(False)
 if got!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x[:6],y[:6],x[-1].hex(),y[-1].hex())for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if meaningful:assert value==out.value,(label,'EAX',hex(value),hex(out.value))
 assert dead==freed and born==created,(label,'ownership');C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);application[:]=[get(t)[0]for t in ALIASES];cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex=final;calls+=1;eventCount+=len(ev);return out.value

# Credits physical-boundary profile; allocations/field ownership remain original.
FILE,DATA,FRONT,BACK,TARGET,FW,BW,TW,DD,DDVT,MUSICMAN,MUSIC1,MUSIC2,MUSICVT,MOVIE,PATH=[BASE+0x40000+i*0x1000 for i in range(16)]
DATA=BASE+0x60000
GETDC,RELEASEDC,LOSTDC,ATTACHDC,STOP,PLAY,PAUSE,SCENEFRAME,RENDER,SCENEDRAW=[0x4000120+i*0x20 for i in range(10)]
NAMED=(0x4f6286,0x4b7f20,0x4b7cd0,0x4b68c0,0x4b67f0,0x4f66cc,0x4f65f2,0x4b54a0,0x4b54f0,0x4c7970,0x4c79e0)
GDI=(0x54688c,0x546d30,0x546d5c,0x546d54,0x546cd4,0x546cd8,0x546888,0x546884,0x546880)
NOOPS=(0x42a000,0x4ca440,0x4b53f0,0x4b6230,RELEASEDC,LOSTDC,ATTACHDC,STOP,PLAY,PAUSE,0x4b5570,0x4ca300,0x4b5340,0x4f0120,0x42b520,0x48f180,0x4fd732,0x48ffa0,0x4caa90,0x4caa20,0x4bb990,0x4b97c0,0x4b98b0,0x48f500,0x48f740,0x48f470,0x4bbb70,0x4b4b40,0x4b4b80,0x4b3490,SCENEFRAME,RENDER,SCENEDRAW,0x4b9d80,0x4b54f0,0x546888,0x546884,0x546880,0x546cd8)
for f,n in[(0x48f0d0,3),(0x42a000,1),(0x4b7f20,1),(0x4b68c0,1),(0x4b7cd0,1),(0x4b67f0,2),(0x4b61c0,0),(0x4ca440,3),(0x4b53f0,3),(0x4b6230,0),(0x4fd6db,1),(0x4b54a0,1),(0x4b5bd0,0),(0x4b5570,1),(0x4ca300,0),(0x4b5340,0),(0x4f0120,0),(0x42b520,0),(0x48f180,0),(0x4fd732,0),(0x48ffa0,4),(0x4caa90,0),(0x4caa20,1),(0x4bb990,6),(0x4b97c0,1),(0x4b98b0,1),(0x48f500,1),(0x48f740,5),(0x48f470,1),(0x4ca930,0),(0x4f65f2,1),(0x4a3050,0),(0x48c190,1),(0x42b4b0,0),(0x42d4a0,0),(0x4f0000,31),(0x4f02e0,6),(0x4f0610,2),(0x4f06e0,0),(0x4bbb70,0),(0x4b4b40,0),(0x4b4b80,0),(0x4b3490,0),(0x4b9d80,5),(0x4b54f0,2),(0x40af20,0),(0x42d4c0,0),(0x4efcd0,0),(0x4f57f8,0),(0x4f7369,0),(GETDC,2),(RELEASEDC,2),(LOSTDC,1),(ATTACHDC,2),(STOP,0),(PLAY,1),(PAUSE,0),(SCENEFRAME,1),(RENDER,2),(SCENEDRAW,1),(0x54688c,4),(0x546d30,5),(0x546d54,1),(0x546cd4,3),(0x546cd8,1),(0x546888,2),(0x546884,2),(0x546880,2)]:ABIS[f]=(n,0 if f in(0x4a3050,0x48c190)else n*4)
# Caller actual4b9d80 = five words; dictionary/query string copied before event.
CDECL += (0x4a3050,0x48c190)
baseInit=1;missingResource=0;missingFile=0;missingMusic=0;musicPlaying=0;dcValue=0;drawHeight=600;drawMutation=[];fileExists=0;movieInit=movieOpen=movieFrame=surfaceReady=1;randomIndex=showCursorIndex=0;randomValues=[1,0x1234,0xffffffff];showCursorValues=[0xffffffff]
def credits():
 global baseInit,missingResource,missingFile,missingMusic,musicPlaying,dcValue,drawHeight,drawMutation,fileExists,movieInit,movieOpen,movieFrame,surfaceReady,randomIndex,showCursorIndex,randomValues,showCursorValues
 fresh();baseInit=1;missingResource=missingFile=missingMusic=musicPlaying=dcValue=fileExists=0;drawHeight=600;drawMutation=[];movieInit=movieOpen=movieFrame=surfaceReady=1;randomIndex=showCursorIndex=0;randomValues=[1,0x1234,0xffffffff];showCursorValues=[0xffffffff]
 put(OWNER,[0x50c174]);put(OWNER+4,[APP,RES,SC]);put(OWNER+32,[RES,RES,0,PAL]);put(OWNER+340,[0,0,0,0,0]);put(OWNER+360,[50,480,590,1080]);put(OWNER+376,[50,480,590,1080]);put(OWNER+392,[0x50c1cc,0,0x52e1c4,19200,0,0]);put(OWNER+416,[0,0x40390000,0,12,0]);put(SC+4,[SURFACE]);put(SC+8,[EXTRA,NEW]);put(EXTRA,[MUTVT]);put(NEW,[MUTVT]);put(MUTVT+36,[SCENEFRAME,SCENEDRAW]);put(MUTVT+52,[RENDER]);put(SURFACE+16,[TARGET,FRONT,BACK]);
 for obj,wrapper in((TARGET,TW),(FRONT,FW),(BACK,BW)):
  put(obj+44,[wrapper]);put(wrapper+8,[DD]);put(wrapper+12,[rng.getrandbits(32)for _ in range(27)])
 put(DD,[DDVT]);put(DDVT+68,[GETDC]);put(DDVT+104,[RELEASEDC]);put(DDVT+96,[LOSTDC]);put(DDVT+124,[ATTACHDC]);put(PAL+16,[RES]);put(RES+52,[0]);put(SC+40,[EXTRA]);put(EXTRA+44,[0]);payload=(ROOT/'work/original-disc-assets/STATES/CREDITS/CREDITS.TXT').read_bytes();put(FILE+20,[len(payload)]);C.memmove(ptr(DATA),payload,len(payload));put(APP+80,[MUSICMAN]);put(MUSICMAN+28,[0]);
 for obj in(MUSIC1,MUSIC2):put(obj,[MUSICVT])
 put(MUSICVT+40,[PAUSE,PLAY,STOP]);put(MOVIE+0x8680,[0x50c364,0,0,0,0]);put(APP+288,[1]);put(PATH,[1,11,11]);C.memmove(ptr(PATH+12),b'credits.avi\0',12);put(APP+256,[PATH+12]);put(SC+28,[PAL,0]);put(PAL,[DD]);put(0x537360,[0]);put(0x53735c,[0]);put(INPUT+528,[0]);
 for f in GDI:put(f,[f])
 return OWNER
# Borrowed constructor-only SinglePlayer context; full loading is a named service
# until the real frozen source level initializer is elected by a native owner.
class Single(C.Structure):_fields_=[('host',Host),('globals',C.c_void_p),('camera',C.c_void_p)]+[(n,U)for n in('composeBase','composeLevel','composeCamera','composeSpatial','fault')]
singleGlobals=(U*21)();single=Single();single.globals=C.addressof(singleGlobals);ctx.singlePlayer=C.addressof(single)
ABIS.update({0x46a6d0:(3,12),0x46a8d0:(1,4),0x46a870:(0,0),0x46ab30:(1,4),0x40af90:(0,0),0x4c9bd0:(0,0),0x429480:(1,4),0x45ace0:(3,12),0x45b3f0:(1,4),0x429510:(1,4)})

constructType=8
# Whole-call records are exported for an independent exact-sized ASAN replay.
capture=False;corpus=[];replayEvents=[];initialDependency=dep
@Dep
def recordedDependency(c,q,u):
 e=q.contents;before=raw(True);buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)];value=initialDependency(c,q,u)
 if capture:
  after=raw(True);old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);patches=[(i,y)for i,(x,y)in enumerate(zip(old,new))if x!=y];replayEvents.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.name or b'',e.mask,hashlib.sha256(before).digest(),value,patches,buffers,[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)]))
 return value
dep=recordedDependency
initialReadClock=readClock
def readClock(native):
 before=raw(True)if native and capture else None;value=initialReadClock(native)
 if before is not None:replayEvents.append((0x546df0,0,(),b'',0,hashlib.sha256(before).digest(),value,[],[],[]))
 return value
initialCompare=compare
def compare(f,label,args=(),receiver=APP,meaningful=True):
 before=bytes(heap);bi=bytes(image);compose=ctx.composeTransitions;replayEvents.clear();v=initialCompare(f,label,args,receiver,meaningful)
 if capture:corpus.append((f,receiver,args,compose,v,meaningful,before,bi[0x520000-imageStart:0x550000-imageStart],raw(True),list(replayEvents)))
 return v
def saveCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as file:
  file.write(b'APGZ'+pack(imageStart,len(imageSeed),SIZE,len(corpus))+imageSeed)
  for f,t,a,compose,out,meaning,before,globalBefore,after,replays in corpus:
   file.write(pack(f,t,len(a),*list(a)+[0]*(4-len(a)),compose,out,int(meaning),len(replays))+before+globalBefore)
   for ef,et,ea,name,mask,digest,value,patches,buffers,outputs in replays:
    file.write(pack(ef,et,len(ea),*list(ea)+[0]*(40-len(ea)),mask,value,len(name),len(patches),len(buffers))+digest+name)
    for patch in patches:file.write(pack(*patch))
    for b,v in zip(buffers,outputs):file.write(pack(len(b))+b+v)
   file.write(after)
def unsafe(f,label,args=(),receiver=APP):
 global calls,eventCount,cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();before=bytes(heap);bi=bytes(image);bapp=bytes(application);state=(cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex);out=U();a=(U*len(args))(*args);ok=lib.claw_application_level_progression_entry(f,receiver,a,len(args),C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault in(1,2),(label,'native fault',ctx.fault,errors);expected=raw(True);ev=list(events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(application),bapp,len(bapp));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);cursor,clockIndex,modeIndex,levelIndex,allocationIndex,transitionIndex,randomIndex,showCursorIndex=state
 try:m.call(f,receiver,pack(*args));raise AssertionError('original returned from unsafe path')
 except(UnsafePrefix,UcError):pass
 assert expected==raw(False),(label,'heap-prefix');assert ev==originalEvents,(label,'event-prefix',len(ev),len(originalEvents));unsafeCases.append(dict(function=hex(f),label=label,events=len(ev)));calls+=1;eventCount+=len(ev)

ABIS.pop(0x42b520,None) # whole owned destructor must execute original instructions
