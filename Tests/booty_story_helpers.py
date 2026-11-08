"""Pinned whole-source default Booty oracle; named movie/UI transports explicit."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/booty-story-agent';U=C.c_uint32
assert hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest()=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
assert hashlib.sha256((ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes()).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
out=WORK/'libStory.dylib';sources=list((ROOT/'Sources').glob('*.cpp'))
if not out.exists()or any((ROOT/"Sources"/p).stat().st_mtime>out.stat().st_mtime for p in ("BootyStoryRuntime.cpp","BootyProgressionRuntime.cpp")):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(out)],check=True)
lib=C.CDLL(str(out))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('alloc','free','call','clock')]
class Context(C.Structure):_fields_=[('scene',Host),('progression',C.c_void_p)]+[(n,U)for n in('composeProgression','composeAnimation','composeCreation','maximumSteps','fault','composeFrame')]+[('composeImages',U),('display',C.c_void_p),('results',C.c_void_p)]
class BaseContext(C.Structure):_fields_=[("host",Host),("globals",C.c_void_p),("camera",C.c_void_p)]+[(n,U)for n in("composeBase","composeLevel","composeCamera","composeSpatial","fault")]
baseGlobals=(U*21)();baseContext=BaseContext();baseContext.globals=C.addressof(baseGlobals)
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('bufferSizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_booty_story_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x80000
APP,OWNER,CHILD,NEW,PREVIOUS,SC,WINDOW,RES,HOLDER,TARGET,PAL,EXTRA,SOUND,THREAD=[BASE+0x1000+i*0x1000 for i in range(14)];SCRATCH=BASE+0x20000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.stack=0x200e000;m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();globals=(U*97)();ctx=Context();ctx.globals=C.addressof(globals);ctx.scratch=SCRATCH;ctx.maximumSteps=65536
rng=random.Random(0x40b330);events=[];originalEvents=[];errors=[];calls=eventCount=0;originalLocal=0;liveLocal=False;movieFinal=None;movieConstructed=False;movieData=False;currentFunction=0;resource=1;movieExists=1;movieInit=1;movieOpen=1;palettePresent=1;allocation=NEW;previousPresent=PREVIOUS;resourceIndex=0;renderReady=1
ABIS={0x4a3920:(3,0),0x48f0d0:(3,12),0x40b5c0:(0,0),0x4b7f20:(1,4),0x546d50:(4,16),0x4b4b40:(0,0),0x4d46f0:(1,4),0x4bc4f0:(1,4),0x4d56d0:(0,0),0x4d4240:(0,0),0x4bb990:(6,24),0x4b97c0:(1,4),0x4b98b0:(1,4),0x48c190:(1,0),0x4f0000:(31,124),0x4f02e0:(6,24),0x4f0380:(3,12),0x4f0120:(0,0),0x4efcd0:(0,0),0x4f57f8:(0,0),0x4f7369:(0,0),0x4f72c9:(0,0),0x4f57c5:(0,0),0x4a3b10:(1,0),0x4a3040:(1,0),0x4f63ec:(1,0),0x4f6439:(0,0),0x4f6428:(1,0),0x42bfd0:(0,0),0x40d470:(3,12),0x40dca0:(1,4),0x40dcb0:(1,4),0x40b020:(1,4),0x40b860:(3,12),0x40bca0:(1,4),0x40b600:(1,4),0x40bd50:(1,4),0x429e10:(2,8)}
CDECL=(0x4a3920,0x48c190,0x4a3b10,0x4a3040,0x4f63ec,0x4f6428,0x546d50)
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def norm(t):return SCRATCH+t-originalLocal if liveLocal and originalLocal<=t<originalLocal+0x8694 else t
def originalToken(t):return originalLocal+t-SCRATCH if liveLocal and SCRATCH<=t<SCRATCH+0x8694 else t
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(originalToken(t),b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(originalToken(t),n*4)))
def raw(native):
 if native:return bytes(heap)+C.string_at(ptr(0x520000),0x30000)
 b=bytearray(m.u.mem_read(BASE,SIZE))
 if liveLocal and movieConstructed:
  n=0x8694 if movieData else 0x8690;b[SCRATCH-BASE:SCRATCH-BASE+n]=(movieFinal if movieFinal is not None else m.u.mem_read(originalLocal,n))[:n]
 return bytes(b)+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('span',hex(t),n))
 return p
ctx.scene=Host(None,lookup,None,None,None,None);baseContext.host=ctx.scene;ctx.progression=0
def name(t,native):
 if native:return C.string_at(ptr(t&~3)+t%4).split(b'\0')[0]
 return bytes(m.u.mem_read(t,100)).split(b'\0')[0]
def effect(f,t,a,n,native):
 global resourceIndex
 if f==0x48f0d0:
  put(t+4,[a[0],get(a[0]+0x34,native=native)[0],get(a[0]+0x30,native=native)[0],0,a[1],a[2]],native);put(t+52,[1],native);return 1
 if f==0x40b5c0:
  put(t,[0x50b4ec],native)
  for o in(4,8,12,0x1c,0x20,0x24,0x2c,0x30,0x3c,0x40,0x34,0x18,0x150):put(t+o,[0],native)
  put(t+0x4c,[get(t+0x4c,native=native)[0]&0xffffff00],native);return 0
 if f==0x4a3920:return 0
 if f==0x4b7f20:resourceIndex+=1;return RES if resource and resourceIndex!=resource else 0
 if f==0x48c190:return movieExists
 if f==0x4f0000:put(t+4,[0x12345678],native);return movieInit
 if f==0x4f02e0:put(t+0x18,[a[1]],native);return movieOpen
 if f==0x4f0380:put(t+0x20,[0x55555555],native);return 0
 if f in(0x4f0120,0x4efcd0,0x4f57f8,0x4f7369,0x4f72c9,0x4f57c5):return 0
 if f==0x4a3b10:return 123456
 if f==0x4a3040:put(THREAD+20,[a[0]],native);return 0
 if f==0x4f63ec:return allocation
 if f==0x4f6439:put(t,[get(0x52e1cc,native=native)[0]],native);return t
 if f in(0x4f6428,0x546d50,0x4b4b40,0x4d46f0,0x4bc4f0,0x4bb990,0x4b97c0,0x4b98b0,0x429e10):return 0
 if f in(0x4d56d0,0x4d4240):return renderReady
 if f==0x42bfd0:return previousPresent
 if f in(0x40d470,0x40b860):put(t+4,[a[0],RES,SC,0,a[1],a[2]],native);put(t+52,[1],native);return 1
 if f in(0x40dca0,0x40bca0,0x40dcb0,0x40bd50):return 1
 if f in(0x40b020,0x40b600):put(t,[0x50b4ec],native);return t
 raise AssertionError(('service',hex(f),hex(t),a,n))
@Dep
def dep(_,q,u):
 try:
  e=q.contents;a=tuple(e.arguments[:e.count]);n=e.name or(C.string_at(e.buffers[0]).split(b"\0")[0]if e.function==0x4b7f20 and not a[0] else name(a[0],True)if e.function==0x4b7f20 else None)
  if e.function==0x4a3920:
   fmt=name(a[1],True).decode();v=a[2]if a[2]<0x80000000 else a[2]-0x100000000;b=(fmt%v).encode()+b"\0";events.append((e.function,e.receiver,a,None,snap(True)));C.memmove(e.buffers[0],b,len(b));return len(b)-1
  events.append((e.function,e.receiver,a,n,snap(True)));return effect(e.function,e.receiver,a,n,True)
 except Exception as e:errors.append(e);return 0

def hook(uc,f,size,u):
 global originalLocal,liveLocal,movieFinal,movieConstructed,movieData
 if False:
  originalLocal=uc.reg_read(UC_X86_REG_ESP)-0x86a4;liveLocal=True;movieFinal=None;movieConstructed=movieData=False;uc.mem_write(originalLocal,bytes(uc.mem_read(SCRATCH,0x8694)));return
 if False:movieConstructed=True
 if False:movieData=True
 if False:movieFinal=bytes(uc.mem_read(originalLocal,0x8694))
 if f not in ABIS or(False):return
 sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=tuple(norm(x)for x in m.read_words(sp+4,n));t=0 if f in CDECL else norm(uc.reg_read(UC_X86_REG_ECX));text=name(a[0],False)if f==0x4b7f20 else None
 if False:
  aa=list(a);destination=a[0];local=0x2000000<=destination<0x2010000
  if local:aa[0]=0
  originalEvents.append((f,t,tuple(aa),text,snap(False)))
  if f==0x4a3920:
   fmt=name(a[1],False).decode();v=a[2]if a[2]<0x80000000 else a[2]-0x100000000;b=(fmt%v).encode()+b"\0";uc.mem_write(destination,b);value=len(b)-1
  else:value=effect(f,t,a,text,False)
 else:originalEvents.append((f,t,a,text,snap(False)));value=effect(f,t,a,text,False)
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def baseFresh(level=1):
 global resource,movieExists,movieInit,movieOpen,allocation,previousPresent,resourceIndex,renderReady,liveLocal
 C.memmove(C.addressof(image),imageSeed,len(image));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);ctx.fault=0;ctx.composeBase=0;baseGlobals[10]=get(0x53ec44)[0];resource=3;movieExists=movieInit=movieOpen=renderReady=1;allocation=NEW;previousPresent=PREVIOUS;resourceIndex=0;liveLocal=False
 put(APP+4,[WINDOW]);put(WINDOW+4,[0x1234]);put(APP+0x2c,[OWNER,SC,RES]);put(APP+0x9c,[0]);put(APP+0x100,[BASE+0x10000]);C.memmove(ptr(BASE+0x10000),b'MOVIES.RPL\0',11);put(APP+0x120,[0]);put(APP+0x130,[0]);put(APP+0x44,[0]);put(OWNER,[0x50c0c4]);put(OWNER+4,[APP]);put(OWNER+20,[level]);put(OWNER+0x154,[CHILD,0]);put(CHILD,[0x50b43c]);put(CHILD+4,[APP,RES,SC,0,level,3]);put(CHILD+44,[PAL]);put(CHILD+52,[1]);put(CHILD+60,[PAL,PAL]);put(CHILD+0x154,[0]);put(PREVIOUS,[BASE+0xf000]);put(BASE+0xf010,[0x40af90]);put(PREVIOUS+0x258,[0,0]);put(SC+4,[HOLDER]);put(SC+24,[SC+0x300,PAL,EXTRA]);put(SC+40,[SOUND]);put(SOUND+44,[SOUND+0x100]);put(PAL,[PAL+0x200]);put(PAL+16,[PAL+0x300]);put(EXTRA+20,[0x445566]);put(HOLDER+16,[TARGET+0x400,TARGET+0x500,TARGET+0x600]);put(TARGET+0x42c,[TARGET]);put(TARGET+0x52c,[TARGET+0x200]);put(TARGET+8,[16]);put(TARGET+12,list(range(27)));put(0x546d50,[0x546d50]);put(0x52e1cc,[0x52e1c4]);put(0x537360,[42]);put(CHILD+0x34,[1]);put(HOLDER+0x10,[TARGET+0x400]);put(HOLDER+24,[0]);put(SC+0x1c,[PAL]);put(SC+0x20,[EXTRA])
def compare(f,label,args=(),receiver=CHILD,meaningful=True):
 global calls,eventCount,resourceIndex,liveLocal,currentFunction
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();resourceIndex=0;liveLocal=False;before=bytes(heap);bi=bytes(image);currentFunction=f;arr=(U*len(args))(*args);out=U();ok=lib.claw_booty_story_entry(f,receiver,arr,len(args),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);resourceIndex=0;liveLocal=False;result=m.call(f,receiver,pack(*args));got=raw(False);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+((len(args)*4)if f not in(0x40c150,0x40c4f0,0x40d1a0)else 0),(label,"SP",hex(m.u.reg_read(UC_X86_REG_ESP)))
 if got!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x,y)for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if meaningful:assert result==out.value,(label,'EAX',result,out.value)
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);calls+=1;eventCount+=len(ev);return out.value
A,L,A2,L2=BASE+0x17000,BASE+0x18000,BASE+0x19000,BASE+0x1a000
busyValues=[0];busyIndex=0;soundFound=1;created=A2
ABIS.update({0x4f6286:(2,8),0x4f65f2:(1,4),0x4f66cc:(1,4),0x4f6584:(0,0),0x4b3e70:(0,0),0x4b3e30:(0,0),0x4b3dc0:(4,16),0x4b45f0:(4,16),0x4c82a0:(1,4),0x4c7900:(2,8),0x4c79e0:(2,8),0x4c8da0:(6,24)})
oldEffect=effect
nativeCell=None;originalCell=None

def effect(f,t,a,n,native):
 global busyIndex
 if f in(0x4f65f2,0x4f66cc):
  if native:C.memmove(nativeCell,pack(a[0]),4)
  else:m.u.mem_write(originalCell,pack(a[0]))
  return a[0]
 if f==0x4f6584:return 0
 if f==0x4f6286:
  value=SOUND if soundFound else 0
  if native:C.memmove(nativeCell,pack(value),4)
  else:m.u.mem_write(originalCell,pack(value))
  return int(value!=0)
 if f==0x4b3e70:value=busyValues[min(busyIndex,len(busyValues)-1)];busyIndex+=1;return value
 if f in(0x4b3e30,0x4b3dc0,0x4b45f0,0x4c7900,0x4c79e0):return 1
 if f==0x4c82a0:return get(t+32,native=native)[0]
 if f==0x4c8da0:return created
 return oldEffect(f,t,a,n,native)
@Dep
def dep(_,q,u):
 global nativeCell
 try:
  e=q.contents;a=tuple(e.arguments[:e.count]);nativeCell=e.buffers[0] if e.buffersCount else None;text=e.name or(name(a[0],True)if e.function==0x4f6286 else None);events.append((e.function,e.receiver,a,text,snap(True)));return effect(e.function,e.receiver,a,text,True)
 except Exception as ex:errors.append(ex);return 0

def actorHook(uc,f,size,u):
 global originalCell,busyIndex
 if f in(0x40c150,0x40c4f0,0x40d1a0):busyIndex=0
 if f not in ABIS:return
 sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=list(m.read_words(sp+4,n));t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX);text=name(a[0],False)if f==0x4f6286 else None
 if f in(0x4f65f2,0x4f66cc,0x4f6584):originalCell=t;t=0
 if f==0x4f6286:originalCell=a[1];a[1]=0
 originalEvents.append((f,t,tuple(a),text,snap(False)));v=effect(f,t,a,text,False);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
# Replace inherited hook; all current entries are actor callbacks.
m.u.hook_del(nextHook:=m.u.hook_add(UC_HOOK_CODE,lambda *a:None))
# Recreate original machine cleanly to avoid two service hooks.
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.stack=0x200e000;m.executed.clear();m.u.hook_add(UC_HOOK_CODE,actorHook)
from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_FS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_CS
TEB,GDT=0x10ed000,0x10ee000
for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):
 m.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.write_words(TEB,[0xdeadbeef])
def fresh(level=1,state=0,delta=16):
 global busyIndex,busyValues,soundFound,created
 baseFresh(level);busyIndex=0;busyValues=[0];soundFound=1;created=A2;ctx.composeAnimation=ctx.composeCreation=ctx.composeProgression=0
 put(A,[0x5137f0]);put(A+12,[SC]);put(A+64,[0]);put(A+108,[L]);put(A+0x188,[0x513810,A,0,0,0,0,1,0,0,0,0x3f800000]);put(A+0x1a4,[1]);put(A+0x19c,[0]);put(L,[0x513744]);put(L+28,[state]);put(L+100,[level,level]);put(L+148,[0]);put(L+164,[0]);put(L+304,[2000,5000]);put(L+320,[0x3f800000]);put(L+352,[0x438c0000]);put(L+360,[L2]);put(A2+108,[L2]);put(A2+64,[0]);put(L2+100,[0]);put(SOUND+16,[SOUND+0x100]);put(0x5371fc,[APP]);put(0x53720c,[delta]);put(0x5430c4,[delta]);put(0x532c0c,[1]);put(0x532c10,[100]);put(0x523b50,[0xffffffff]);put(0x5349a0,[0]);put(0x5349a4,[0]);put(SC+8,[SC+0x200]);put(SC+0x200+48,[0])
oldCompare=compare
def compare(f,label,args=None,receiver=0,meaningful=True):
 global busyIndex
 busyIndex=0
 # Both backends consume the same explicit audio query sequence.
 beforeEffect=effect
 result=oldCompare(f,label,(A,) if args is None else args,receiver,meaningful)
 return result
# Controller comparison transports, including exact automatic CString cells.
CDECL=CDECL+(0x4f4f58,0x546d54,)
ABIS.update({0x4b7cd0:(1,4),0x4cff40:(3,12),0x4d0120:(3,12),0x4ce0d0:(3,12),0x4f6974:(1,4),0x4f695c:(1,4),0x4f6920:(1,4),0x4f667d:(1,4),0x4f4f58:(4,0),0x546d54:(1,4),0x48ffa0:(4,16),0x4ca9e0:(1,4),0x4b9c50:(1,4),0x4caa90:(0,0),0x4caa20:(1,4),0x4d4160:(0,0),0x4d4000:(2,8),0x4cacb0:(0,0),0x4b3fe0:(3,12),0x4b3490:(0,0),0x4c8fc0:(1,4),0x4d63c0:(2,8),0x4c91d0:(1,4),0x4b9d80:(5,20),0x48f470:(1,4),0x4c89e0:(0,0)})
stringAt=BASE+0x50000;nativeCells=[];originalCells=[];cursorCalls=0
resourceFailure=0;creationFailure=0;creationCalls=0
oldActorEffect=effect

def bytesName(t,native=True):return name(t,native)if t else b''
def cellRead(native,index=0):return struct.unpack('<I',C.string_at(nativeCells[index],4)if native else m.u.mem_read(originalCells[index],4))[0]
def cellWrite(v,native,index=0):
 if native:C.memmove(nativeCells[index],pack(v),4)
 else:m.u.mem_write(originalCells[index],pack(v))
def storeString(b,native):
 global stringAt
 t=stringAt;stringAt+=0x100;assert stringAt<BASE+0x55000;bb=b+b'\0'
 if native:C.memmove(ptr(t),bb,len(bb))
 else:m.u.mem_write(t,bb)
 return t

def effect(f,t,a,n,native):
 global cursorCalls,creationCalls,resourceIndex
 if f==0x4f6439:cellWrite(0x52e1c4,native);return 0
 if f==0x4f4f58:
  fmt=bytesName(a[1],native).decode();values=(bytesName(a[2],native).decode(),a[3])if'%s' in fmt else(a[2],);b=(fmt%values).encode();cellWrite(storeString(b,native),native);return 0
 if f in(0x4f65f2,0x4f66cc):
  if t:put(t,[a[0]],native)
  else:cellWrite(a[0],native)
  return 0
 if f==0x4f6974:return cellRead(native)
 if f==0x4f695c:cellWrite(storeString(bytesName(cellRead(native,1),native)+bytesName(cellRead(native,0),native),native),native,1);return 0
 if f==0x4f6920:
  value=get(t,native=native)[0]if t else cellRead(native);v=storeString(bytesName(value,native)+bytesName(a[0],native),native)
  if t:put(t,[v],native)
  else:cellWrite(v,native)
  return 0
 if f==0x4f667d:
  if t:put(t,[cellRead(native)],native)
  else:cellWrite(cellRead(native,0),native,1)
  return 0
 if f==0x4f6584:return 0
 if f in(0x4b7f20,0x4b7cd0):resourceIndex+=1;return 0 if resourceIndex==resourceFailure else RES
 if f==0x546d54:cursorCalls+=1;return (0xffffffff if cursorCalls%3==0 else 0)
 if f==0x4c8da0:
  creationCalls+=1;tkn=0 if creationCalls==creationFailure else A if creationCalls==1 else A2
  if tkn:put(tkn+108,[L if tkn==A else L2],native)
  return tkn
 if f==0x48ffa0:put(t+44,[PAL],native);return 1
 if f==0x4d4160:put(t+44,[0],native);return 0
 if f==0x4d4000:put(t+16,list(a),native);put(t+44,[TARGET+0x100],native);return 1
 if f==0x4cacb0:return int(bool(get(t+44,native=native)[0])and get(t+16,native=native)[0]>0 and get(t+12,native=native)[0]!=0 and get(t+4,native=native)[0]!=0xffffffff)
 if f==0x4b9c50:return 0
 if f in(0x4cff40,0x4d0120,0x4ce0d0,0x4b3fe0,0x4b3490,0x4c8fc0,0x4d63c0,0x4c91d0,0x4b9d80,0x48f470,0x4c89e0):return 1
 return oldActorEffect(f,t,a,n,native)

@Dep
def dep(_,q,u):
 global nativeCell,nativeCells
 try:
  e=q.contents;a=list(e.arguments[:e.count]);nativeCells=list(e.buffers[:e.buffersCount]);nativeCell=nativeCells[0]if nativeCells else None
  text=e.name or(bytesName(a[0],True)if e.function in(0x4f6286,0x4b7f20,0x4b7cd0)and a[0]else None)
  events.append((e.function,e.receiver,tuple(a),text,snap(True)));return effect(e.function,e.receiver,a,text,True)
 except Exception as ex:errors.append(ex);return 0

# New machine: exactly one hook, proper FS/TEB, and actual source vtable entries.
def controllerHook(uc,f,size,u):
 global originalCell,originalCells,busyIndex,stringAt,cursorCalls,creationCalls
 if f==currentFunction:busyIndex=cursorCalls=creationCalls=0;stringAt=BASE+0x50000
 if f not in ABIS:return
 # Owned trio surface bodies execute unchanged, rather than transport adapters.
 if f in(0x4ca9e0,0x4caa90,0x4caa20,0x40b860,0x40bca0,0x40bd60,0x40bf80,0x40bfd0,0x40be60,0x40bed0,0x40bd50,0x40bf30,0x40bc80,0x40b620,0x40b600):return
 sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f]
 if f==0x4f4f58:
  fmt=bytesName(m.read_words(sp+8,1)[0],False);n=4 if b'%s' in fmt else 3
 a=list(m.read_words(sp+4,n));t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX);text=bytesName(a[0],False)if f in(0x4f6286,0x4b7f20,0x4b7cd0)and a[0]else None;originalCells=[]
 if f==0x4f6286:originalCells=[a[1]];a[1]=0
 elif f==0x4f4f58:originalCells=[a[0]];a[0]=0
 elif f in(0x4f695c,0x4f667d):
  originalCells=[a[0]];a[0]=0
  if 0x2000000<=t<0x2010000:originalCells.append(t);t=0
 elif f in(0x4f6439,0x4f65f2,0x4f66cc,0x4f6584,0x4f6974,0x4f6920)and 0x2000000<=t<0x2010000:originalCells=[t];t=0
 originalCell=originalCells[0]if originalCells else None
 originalEvents.append((f,t,tuple(a),text,snap(False)));v=effect(f,t,a,text,False);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
# Remove all old hooks by rebuilding the private emulator.
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.stack=0x200e000;m.executed.clear();m.u.hook_add(UC_HOOK_CODE,controllerHook)
for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):m.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.write_words(TEB,[0xdeadbeef])
actorFresh=fresh

def fresh(level=1,state=0,delta=16):
 global cursorCalls,stringAt,creationCalls,resourceFailure,creationFailure
 actorFresh(level,state,delta);cursorCalls=creationCalls=resourceFailure=creationFailure=0;stringAt=BASE+0x50000;ctx.composeFrame=0
 put(CHILD,[0x50b544]);put(CHILD+0x15c,[0x523c6c]);put(CHILD+0x168,[0x523c58]);put(SC+8,[SC+0x200]);put(SC+12,[SC+0x300]);put(SC+16,[SC+0x400]);put(SC+44,[SC+0x500]);put(SC+0x200,[0x513c20]);put(SC+0x300,[0x513be8]);put(SC+0x400,[0x513b88]);put(TARGET+0x500,[0x50e8e4]);put(TARGET+0x500+4,[1]);put(TARGET+0x500+12,[SC]);put(TARGET+0x500+16,[640,480]);put(TARGET+0x600,[0x50e8e4]);put(TARGET+0x600+4,[2]);put(TARGET+0x600+12,[SC]);put(TARGET+0x600+16,[640,480]);put(HOLDER+24,[TARGET+0x600]);put(0x546d54,[0x546d54]);put(0x537200,[BASE+0x14000]);put(BASE+0x14000+0x210,[0]);put(CHILD+32,[RES]);put(CHILD+0x158,[0]);put(0x53499c,[0x523ce8])
currentCompare=compare

def compare(f,label,args=None,receiver=None,meaningful=True):
 global stringAt,cursorCalls,creationCalls
 stringAt=BASE+0x50000;cursorCalls=creationCalls=0
 return currentCompare(f,label,(A,)if args is None and f in(0x40c150,0x40d1a0,0x40c4f0)else()if args is None else args,0 if receiver is None and f in(0x40c150,0x40d1a0,0x40c4f0)else CHILD if receiver is None else receiver,meaningful)
class ProgressionContext(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('base',C.c_void_p)]+[(n,U)for n in('scratch','composeBase','maximumSteps','fault')]
progression=ProgressionContext();progression.scene=ctx.scene;progression.globals=C.addressof(globals);progression.scratch=SCRATCH;progression.maximumSteps=65536;ctx.progression=C.addressof(progression)
controllerFresh=fresh

def fresh(level=1,state=0,delta=16):controllerFresh(level,state,delta);ctx.composeProgression=1;ctx.progression=C.addressof(progression)
# Source ANI/image cores composed against actual canonical BOOTY bytes.
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
class AniRecord(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
resourceTokens={};resourceInventory=[];joinedResources=False

def realResources():
 global joinedResources
 import re
 joinedResources=True;resourceTokens.clear();resourceInventory.clear();leafAt=BASE+0x60000;rootAt=BASE+0x30000;tableAt=BASE+0x32000;recordAt=BASE+0x3c000;aniAt=BASE+0x38000
 assetRoot=ROOT/'Original/retail-assets/STATES/BOOTY';groups={}
 for path in sorted(x for x in (assetRoot/'IMAGES/MAPPIECE').rglob('*') if x.suffix in('.PID','.PCX')):
  rel=path.relative_to(assetRoot/'IMAGES');nm=('BOOTY_'+str(rel.parent).replace('/','_')).encode();data=path.read_bytes();ident=int(re.search(r'[0-9]+',path.stem)[0]);
  if path.suffix=='.PID':_,_,w,ht,x,y=struct.unpack_from('<6I',data)
  else:
   xmin,ymin,xmax,ymax=struct.unpack_from('<4H',data,4);w=xmax-xmin+1;ht=ymax-ymin+1;x=y=0 # Declared physical PCX surface geometry; source4d2410 format2 uses zero offsets.
  g=Geometry();lib.claw_sprite_set_geometry(C.byref(g),w,ht,x,y);put(leafAt+16,list(struct.unpack('<10I',bytes(g)))[:6]);groups.setdefault(nm,[]).append((ident,leafAt));resourceInventory.append({'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(data).hexdigest(),'id':ident});leafAt+=64
 for nm,rows in groups.items():
  mini=min(r[0]for r in rows);maxi=max(r[0]for r in rows);put(rootAt+20,[tableAt]);put(rootAt+100,[mini,maxi]);put(tableAt,[0]*(maxi+1))
  for i,t in rows:put(tableAt+i*4,[t])
  resourceTokens[nm]=rootAt;rootAt+=108;tableAt+=(maxi+1)*4
 assert rootAt<BASE+0x32000 and tableAt<BASE+0x38000 and leafAt<BASE+SIZE
 for path in sorted((assetRoot/'ANIS').glob('GEM*.ANI')):
  data=path.read_bytes();sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;at=32+pl;root=aniAt;table=root+32;aniAt+=0x200;pointers=[]
  for i in range(count):
   tail=data[at:];b=(C.c_uint8*len(tail)).from_buffer_copy(tail);rec=AniRecord();length=U();used=lib.claw_animation_decode_record(b,len(tail),SOUND,C.byref(rec),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(rec)));put(recordAt,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);pointers.append(recordAt);recordAt+=48;at+=used
  assert at==len(data) and len(pointers)*4<=0x1e0;put(root+12,[table,count]);put(table,pointers);resourceTokens[('BOOTY_'+path.stem).encode()]=root;resourceInventory.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'records':count})
 assert aniAt<BASE+0x3c000 and recordAt<BASE+0x50000
 ctx.composeImages=ctx.composeAnimation=1
 return resourceInventory
resourceEffect=effect

def effect(f,t,a,n,native):
 if joinedResources and f==0x4f6286:
  value=resourceTokens.get(n, SOUND if t not in(SC+0x410,SC+0x510)else 0)
  if len(a)==1:return value
  cellWrite(value,native);return int(value!=0)
 if f in(0x4c88e0,0x4208e0):return 0
 return resourceEffect(f,t,a,n,native)
ABIS.update({0x4c88e0:(4,16),0x4208e0:(4,16)})
@Dep
def dep(_,q,u):
 global nativeCell,nativeCells
 try:
  e=q.contents;a=list(e.arguments[:e.count]);nativeCells=list(e.buffers[:e.buffersCount]);nativeCell=nativeCells[0]if nativeCells else None
  text=e.name or(bytesName(a[0],True)if e.function in(0x4f6286,0x4b7f20,0x4b7cd0)and a[0]else None)
  aa=a+[0]if e.function==0x4f6286 and len(a)==1 else a
  events.append((e.function,e.receiver,tuple(aa),text,snap(True)));return effect(e.function,e.receiver,a,text,True)
 except Exception as ex:errors.append(ex);return 0
priorControllerHook=controllerHook

def controllerHook(uc,f,size,u):
 if ctx.composeAnimation and f in(0x4c79e0,0x4c82a0):return
 if ctx.composeImages and f==0x4c7900:return
 priorControllerHook(uc,f,size,u)
# Existing registered callback captures global function name at invocation time.
priorFresh=fresh

def fresh(level=1,state=0,delta=16):
 global joinedResources
 priorFresh(level,state,delta);joinedResources=False;ctx.composeImages=0;ctx.display=ctx.results=0
# Rebuild with the final adaptive hook, avoiding earlier service interceptors.
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.stack=0x200e000;m.executed.clear();m.u.hook_add(UC_HOOK_CODE,controllerHook)
for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):m.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.write_words(TEB,[0xdeadbeef])
joinedCreation=False;allocCursor=allocBase=BASE+0x22000;allocations=[];nativeAllocations=[]
metadata={b'MapPieceLogic':BASE+0x1b000,b'AmuletGemLogic':BASE+0x1b020,b'MapProgressLogic':BASE+0x1b040}
creationEffect=effect

def effect(f,t,a,n,native):
 global allocCursor
 if joinedCreation and f==0x4f63ec:
  token=allocCursor;allocCursor+=(a[0]+3)&~3;assert allocCursor<BASE+0x30000;nativeAllocations.append((token,a[0]))if native else allocations.append((token,a[0]));return token
 if joinedCreation and f==0x4f6286 and t==SC+0x610:
  token=metadata.get(n,0)
  if len(a)==1:return token
  cellWrite(token,native);return int(bool(token))
 return creationEffect(f,t,a,n,native)

def realCreation():
 global joinedCreation,allocCursor,allocBase
 joinedCreation=True;ctx.composeCreation=1;allocCursor=allocBase=BASE+0x22000
 put(SC+0x200,[0x513c20,0,0,SC,0x5107bc,0,0,0,0,0,10]);put(SC+20,[SC+0x600]);put(SC+36,[0]);
 for i,(nm,t)in enumerate(metadata.items()):put(t,[0,0,0,0,{b'MapPieceLogic':0x40c150,b'AmuletGemLogic':0x40d1a0,b'MapProgressLogic':0x40c4f0}[nm]])
originalControllerHook=controllerHook

def controllerHook(uc,f,size,u):
 global allocCursor
 if f==currentFunction:allocCursor=allocBase
 if ctx.composeCreation and f==0x4c8da0:return
 originalControllerHook(uc,f,size,u)
preJoinedCompare=compare

def compare(f,label,args=None,receiver=None,meaningful=True):
 global allocBase
 allocBase=allocCursor;nativeAllocations.clear();allocations.clear();v=preJoinedCompare(f,label,args,receiver,meaningful);assert nativeAllocations==allocations,(label,nativeAllocations,allocations);return v
preJoinedFresh=fresh

def fresh(level=1,state=0,delta=16):
 global joinedCreation,allocCursor,allocBase
 preJoinedFresh(level,state,delta);joinedCreation=False;allocCursor=allocBase=BASE+0x22000
# Rebuild exactly one final hook and proper FS descriptor.
def rebuildMachine():
 global m
 m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.stack=0x200e000;m.executed.clear();m.u.hook_add(UC_HOOK_CODE,controllerHook)
 for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):m.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
 m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
 for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.write_words(TEB,[0xdeadbeef])
rebuildMachine()
class DisplayContext(C.Structure):_fields_=[('scene',Host),('graphics',C.c_void_p),('image',C.c_void_p),('maximumOperations',U),('fault',U)]
displayContext=DisplayContext(ctx.scene,None,None,65536,0)
Clock=C.CFUNCTYPE(U,C.c_void_p);clockNow=0
@Clock
def clock(_):
 events.append((0x546df0,0,(),None,snap(True)));return clockNow
ctx.scene.clock=C.cast(clock,C.c_void_p).value
ABIS.update({0x546df0:(0,0),0x4d2890:(2,8),0x4a35f0:(1,0)})
CDECL=CDECL+(0x546df0,0x4a35f0)
frameEffect=effect

def effect(f,t,a,n,native):
 if f==0x546df0:return clockNow
 if f in(0x4d2890,0x4a35f0):return 0
 return frameEffect(f,t,a,n,native)

def realFrame():
 ctx.composeFrame=1;ctx.display=C.addressof(displayContext);put(SC+0x300+20,[0]);put(0x5430d0,[3]);put(0x5430d8,[0x5108fc,0,0,0,0]);put(0x5430f0,[0x5108fc,0,0,0,0]);put(0x5430c8,[0]);put(0x546df0,[0x546df0]);
 for nm,t in resourceTokens.items():
  if nm.startswith(b'BOOTY_MAPPIECE'):
   lo,hi=get(t+100,2)
   for i in range(lo,hi+1):
    leaf=get(get(t+20)[0]+i*4)[0]
    if leaf:put(leaf,[0x513a70])
frameControllerHook=controllerHook

def controllerHook(uc,f,size,u):
 if ctx.composeFrame and f in(0x4c8fc0,0x4c91d0):return
 if ctx.display and f in(0x4d63c0,0x4cacb0):return
 frameControllerHook(uc,f,size,u)
rebuildMachine()
class NumberContext(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p)]+[(n,U)for n in('composeAnimation','composeImages','composeHierarchy','composeFormatting','fault')]
class ResultsContext(C.Structure):_fields_=[('scene',Host),('progression',C.c_void_p),('numbers',C.c_void_p),('actors',C.c_void_p)]+[(n,U)for n in('composeBase','composeNumbers','composeScene','composeAnimation','composeImages','maximumSteps','fault')]
numberGlobals=(U*13)();numberContext=NumberContext(ctx.scene,C.addressof(numberGlobals),0,0,1,0,0)
resultsContext=ResultsContext(ctx.scene,C.addressof(progression),C.addressof(numberContext),None,0,1,0,0,0,65536,0)

def realCleanup():
 ctx.results=C.addressof(resultsContext);put(0x53c9ac,[0,0]);put(0x52e1cc,[0x52e1c4])
cleanupControllerHook=controllerHook

def controllerHook(uc,f,size,u):
 if ctx.results and f in(0x4c89e0,0x48ffa0,0x48f470):return
 cleanupControllerHook(uc,f,size,u)
rebuildMachine()
# Shared source palette/setup bodies with explicit physical PCX/palette transport.
ABIS.update({0x4b7dc0:(2,8),0x4d4420:(3,12),0x4d6690:(0,0),0x4bb870:(0,0),0x4bb910:(6,24),0x4bbd90:(4,16),0x4bbd20:(0,0),0x4bb8c0:(1,4),0x4ca900:(2,8),0x4d4190:(1,4),0x4b95b0:(5,20),0x4b61b0:(0,0),0x4b61c0:(0,0),0x4b6230:(0,0),0x4bdda0:(3,12),0x4bebc0:(3,12),0x4bf680:(4,16)})
bitmapType=0x504358;bitmapData=BASE+0x10000;bitmapResult=1;screenFound=1;paletteFound=1;screenInventory=[]
paletteEffect=effect

def effect(f,t,a,n,native):
 if f==0x4a3920:
  fmt=bytesName(a[1],native).decode();v=bytesName(a[2],native).decode()if'%s' in fmt else C.c_int32(a[2]).value;b=(fmt%v).encode()+b'\0'
  if native:C.memmove(nativeCells[0],b,len(b))
  else:m.u.mem_write(originalCells[0],b)
  return len(b)-1
 if f==0x4b7dc0:return RES if screenFound else 0
 if f==0x4d4420:
  if not paletteFound:return 0
  put(PAL,[0x513d78],native);put(PAL+12,[SC,PAL+0x300],native);put(PAL+0x310,[0x1234],native);return PAL
 if f in(0x4d6690,0x4bb870,0x4bb910,0x4bbd90,0x4bbd20,0x4bb8c0):return 1
 if f==0x4b61b0:return bitmapType
 if f==0x4b61c0:return bitmapData
 if f==0x4b6230:return 0
 if f in(0x4bdda0,0x4bebc0,0x4bf680):return bitmapResult
 return paletteEffect(f,t,a,n,native)

@Dep
def dep(_,q,u):
 global nativeCell,nativeCells
 try:
  e=q.contents;a=list(e.arguments[:e.count]);nativeCells=list(e.buffers[:e.buffersCount]);nativeCell=nativeCells[0]if nativeCells else None
  text=e.name or(bytesName(a[0],True)if e.function in(0x4f6286,0x4b7f20,0x4b7cd0)and a[0]else None)
  aa=a+[0]if e.function==0x4f6286 and len(a)==1 else a
  events.append((e.function,e.receiver,tuple(aa),text,snap(True)));return effect(e.function,e.receiver,a,text,True)
 except Exception as ex:errors.append(ex);return 0
paletteControllerHook=controllerHook

def controllerHook(uc,f,size,u):
 global originalCells
 if f in(0x4ca900,0x4d4190,0x4b95b0):return
 if f in(0x4a3920,0x4b7dc0,0x4d4420):
  sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=list(m.read_words(sp+4,n));t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX);originalCells=[];text=None
  if f==0x4a3920:originalCells=[a[0]];a[0]=0;text=bytesName(a[1],False)
  elif f==0x4b7dc0:originalCells=[a[0]];text=bytesName(a[0],False);a[0]=0
  elif f==0x4d4420:originalCells=[a[1]];text=bytesName(a[1],False);a[1]=0
  originalEvents.append((f,t,tuple(a),text,snap(False)));v=effect(f,t,a,text,False);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);return
 paletteControllerHook(uc,f,size,u)

def realPalette(level):
 global bitmapType,bitmapData,bitmapResult,screenFound,paletteFound
 realCleanup();ctx.display=0;bitmapType=0x504358;bitmapData=BASE+0x10000;bitmapResult=screenFound=paletteFound=1
 manager=SC+0x700;put(SC+24,[manager]);put(manager,[SC+0x800]);put(SC+0x830,[0x4d4420]);put(PAL,[0x513d78]);put(PAL+12,[SC,PAL+0x300]);put(PAL+0x310,[0x1234]);put(TARGET+0x400+24,[16]);
 title=bytesName(get(CHILD+0x15c)[0]);path=ROOT/'Original/retail-assets/STATES/BOOTY/SCREENS'/f'{title.decode()}.PCX';data=path.read_bytes();screenInventory.append({'level':level,'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()});put(RES+20,[len(data)])
rebuildMachine()
# Exact-size sanitizer corpus. Physical CRT free storage is retained in this
# transport profile, matching the oracle; ownership ordering is still recorded.
capture=False;corpus=[];replayEvents=[];allAllocations={}
observedEffect=effect

def effect(f,t,a,n,native):
 value=observedEffect(f,t,a,n,native)
 if native and f==0x4f63ec and value:allAllocations[value]=(a[0]+3)//4
 return value
observedDep=dep
@Dep
def capturedDep(c,q,u):
 e=q.contents;before=raw(True);buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)];value=observedDep(c,q,u)
 if capture:
  old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(before)//4),raw(True));patches=[(i,v)for i,(b,v)in enumerate(zip(old,new))if b!=v];nm=events[-1][3]
  replayEvents.append(((e.function,e.receiver,tuple(e.arguments[:e.count]),nm),e.mask,hashlib.sha256(before).digest(),value,patches,buffers,[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)]))
 return value
dep=capturedDep
@Clock
def clock(_):
 digest=snap(True);events.append((0x546df0,0,(),None,digest))
 if capture:replayEvents.append(((0x546df0,0,(),None),0,digest,clockNow,[],[],[]))
 return clockNow
ctx.scene.clock=C.cast(clock,C.c_void_p).value
recordedFresh=fresh

def fresh(level=1,state=0,delta=16):recordedFresh(level,state,delta);allAllocations.clear()
recordedCompare=compare

def compare(f,label,args=None,receiver=None,meaningful=True):
 aa=(A,)if args is None and f in(0x40c150,0x40d1a0,0x40c4f0)else()if args is None else args;tt=0 if receiver is None and f in(0x40c150,0x40d1a0,0x40c4f0)else CHILD if receiver is None else receiver
 before=bytes(heap);gi=C.string_at(ptr(0x520000),0x30000);flags=[ctx.composeProgression,ctx.composeAnimation,ctx.composeCreation,ctx.composeFrame,ctx.composeImages,int(bool(ctx.display)),int(bool(ctx.results))];objects=dict(allAllocations);replayEvents.clear();v=recordedCompare(f,label,args,receiver,meaningful)
 if capture:corpus.append((f,tt,aa,flags,v,meaningful,before,gi,raw(True),list(replayEvents),objects))
 return v

def saveCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as file:
  file.write(b'STRY'+pack(imageStart,len(imageSeed),SIZE,len(corpus))+imageSeed)
  for f,t,a,flags,out,meaning,before,gi,after,replays,objects in corpus:
   header=[f,t,len(a),*list(a)+[0]*(5-len(a)),*flags,out,int(meaning),len(replays),len(objects),0,0,0,0,0];assert len(header)==24;file.write(pack(*header)+before+gi)
   for item in objects.items():file.write(pack(*item))
   for(ev,mask,digest,value,patches,buffers,outputs)in replays:
    ef,et,ea,nm=ev;nm=nm or b'';file.write(pack(ef,et,len(ea),*list(ea)+[0]*(40-len(ea)),mask,value,len(nm),len(patches),len(buffers))+digest+nm)
    for p in patches:file.write(pack(*p))
    for b,v in zip(buffers,outputs):file.write(pack(len(b))+b+v)
   file.write(after)
allocationIndex=allocationBase=allocationFail=0
failureEffect=effect

def effect(f,t,a,n,native):
 global allocationIndex
 if joinedCreation and f==0x4f63ec:
  allocationIndex+=1
  if allocationIndex==allocationFail:return 0
 return failureEffect(f,t,a,n,native)
failureControllerHook=controllerHook

def controllerHook(uc,f,size,u):
 global allocationIndex
 if f==currentFunction:allocationIndex=allocationBase
 failureControllerHook(uc,f,size,u)
rebuildMachine()
failureFresh=fresh

def fresh(level=1,state=0,delta=16):
 global allocationIndex,allocationBase,allocationFail
 failureFresh(level,state,delta);allocationIndex=allocationBase=allocationFail=0
failureCompare=compare

def compare(f,label,args=None,receiver=None,meaningful=True):
 global allocationBase
 allocationBase=allocationIndex;return failureCompare(f,label,args,receiver,meaningful)
unsafeCases=[]
def unsafe(f,label,args,receiver=CHILD):
 global allocBase,allocCursor,allocationBase,allocationIndex,currentFunction,cursorCalls,creationCalls,resourceIndex,stringAt
 from unicorn import UcError
 allocBase=allocCursor;allocationBase=allocationIndex;ctx.fault=0;events.clear();originalEvents.clear();errors.clear();resourceIndex=cursorCalls=creationCalls=0;stringAt=BASE+0x50000;before=bytes(heap);bi=bytes(image);currentFunction=f;out=U();arr=(U*len(args))(*args);ok=lib.claw_booty_story_entry(f,receiver,arr,len(args),C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault in(1,2),(label,ok,ctx.fault,errors);expected=raw(True);ev=list(events)
 C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);resourceIndex=cursorCalls=creationCalls=0;stringAt=BASE+0x50000;allocCursor=allocBase;allocationIndex=allocationBase
 try:m.call(f,receiver,pack(*args));raise AssertionError('expected original unsafe read/write')
 except UcError:pass
 assert raw(False)==expected and ev==originalEvents,(label,'unsafe prefix',len(ev),len(originalEvents));unsafeCases.append({'label':label,'function':hex(f),'fault':ctx.fault,'events':len(ev)})
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000)
