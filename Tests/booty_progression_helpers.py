"""Pinned whole-source default Booty oracle; named movie/UI transports explicit."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/booty-progression-agent';U=C.c_uint32
out=WORK/'libBooty.dylib';sources=list((ROOT/'Sources').glob('*.cpp'))
if not out.exists()or any((ROOT/"Sources"/p).stat().st_mtime>out.stat().st_mtime for p in ("BootyProgressionRuntime.cpp","SinglePlayerSceneRuntime.cpp")):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(out)],check=True)
lib=C.CDLL(str(out))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('alloc','free','call','clock')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('base',C.c_void_p)]+[(n,U)for n in('scratch','composeBase','maximumSteps','fault')]
class BaseContext(C.Structure):_fields_=[("host",Host),("globals",C.c_void_p),("camera",C.c_void_p)]+[(n,U)for n in("composeBase","composeLevel","composeCamera","composeSpatial","fault")]
baseGlobals=(U*21)();baseContext=BaseContext();baseContext.globals=C.addressof(baseGlobals)
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('bufferSizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_booty_progression_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x80000
APP,OWNER,CHILD,NEW,PREVIOUS,SC,WINDOW,RES,HOLDER,TARGET,PAL,EXTRA,SOUND,THREAD=[BASE+0x1000+i*0x1000 for i in range(14)];SCRATCH=BASE+0x20000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.stack=0x200e000;m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();globals=(U*97)();ctx=Context();ctx.globals=C.addressof(globals);ctx.scratch=SCRATCH;ctx.maximumSteps=65536
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
ctx.scene=Host(None,lookup,None,None,None,None);baseContext.host=ctx.scene;ctx.base=C.addressof(baseContext)
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
 if f==0x42b140:
  originalLocal=uc.reg_read(UC_X86_REG_ESP)-0x86a4;liveLocal=True;movieFinal=None;movieConstructed=movieData=False;uc.mem_write(originalLocal,bytes(uc.mem_read(SCRATCH,0x8694)));return
 if f==0x42b4b0 and liveLocal:movieConstructed=True
 if f==0x42d4a0 and liveLocal:movieData=True
 if f==0x42b42e:movieFinal=bytes(uc.mem_read(originalLocal,0x8694))
 if f not in ABIS or(ctx.composeBase and f in(0x40b5c0,0x48f0d0)):return
 sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=tuple(norm(x)for x in m.read_words(sp+4,n));t=0 if f in CDECL else norm(uc.reg_read(UC_X86_REG_ECX));text=name(a[0],False)if f==0x4b7f20 else None
 if ctx.composeBase and f in(0x4a3920,0x4b7f20):
  aa=list(a);destination=a[0];local=0x2000000<=destination<0x2010000
  if local:aa[0]=0
  originalEvents.append((f,t,tuple(aa),text,snap(False)))
  if f==0x4a3920:
   fmt=name(a[1],False).decode();v=a[2]if a[2]<0x80000000 else a[2]-0x100000000;b=(fmt%v).encode()+b"\0";uc.mem_write(destination,b);value=len(b)-1
  else:value=effect(f,t,a,text,False)
 else:originalEvents.append((f,t,a,text,snap(False)));value=effect(f,t,a,text,False)
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(level=1):
 global resource,movieExists,movieInit,movieOpen,allocation,previousPresent,resourceIndex,renderReady,liveLocal
 C.memmove(C.addressof(image),imageSeed,len(image));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);ctx.fault=0;ctx.composeBase=0;baseGlobals[10]=get(0x53ec44)[0];resource=3;movieExists=movieInit=movieOpen=renderReady=1;allocation=NEW;previousPresent=PREVIOUS;resourceIndex=0;liveLocal=False
 put(APP+4,[WINDOW]);put(WINDOW+4,[0x1234]);put(APP+0x2c,[OWNER,SC,RES]);put(APP+0x9c,[0]);put(APP+0x100,[BASE+0x10000]);C.memmove(ptr(BASE+0x10000),b'MOVIES.RPL\0',11);put(APP+0x120,[0]);put(APP+0x130,[0]);put(APP+0x44,[0]);put(OWNER,[0x50c0c4]);put(OWNER+4,[APP]);put(OWNER+20,[level]);put(OWNER+0x154,[CHILD,0]);put(CHILD,[0x50b43c]);put(CHILD+4,[APP,RES,SC,0,level,3]);put(CHILD+44,[PAL]);put(CHILD+52,[1]);put(CHILD+60,[PAL,PAL]);put(CHILD+0x154,[0]);put(PREVIOUS,[BASE+0xf000]);put(BASE+0xf010,[0x40af90]);put(PREVIOUS+0x258,[0,0]);put(SC+4,[HOLDER]);put(SC+24,[SC+0x300,PAL,EXTRA]);put(SC+40,[SOUND]);put(SOUND+44,[SOUND+0x100]);put(PAL,[PAL+0x200]);put(PAL+16,[PAL+0x300]);put(EXTRA+20,[0x445566]);put(HOLDER+16,[TARGET+0x400,TARGET+0x500,TARGET+0x600]);put(TARGET+0x42c,[TARGET]);put(TARGET+0x52c,[TARGET+0x200]);put(TARGET+8,[16]);put(TARGET+12,list(range(27)));put(0x546d50,[0x546d50]);put(0x52e1cc,[0x52e1c4]);put(0x537360,[42]);put(CHILD+0x34,[1]);put(HOLDER+0x10,[TARGET+0x400]);put(HOLDER+24,[0]);put(SC+0x1c,[PAL]);put(SC+0x20,[EXTRA])
def compare(f,label,args=(),receiver=CHILD,meaningful=True):
 global calls,eventCount,resourceIndex,liveLocal,currentFunction
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();resourceIndex=0;liveLocal=False;before=bytes(heap);bi=bytes(image);currentFunction=f;arr=(U*len(args))(*args);out=U();ok=lib.claw_booty_progression_entry(f,receiver,arr,len(args),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);resourceIndex=0;liveLocal=False;result=m.call(f,receiver,pack(*args));got=raw(False);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(args)*4,(label,"SP",hex(m.u.reg_read(UC_X86_REG_ESP)))
 if got!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x,y)for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if meaningful:assert result==out.value,(label,'EAX',result,out.value)
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);calls+=1;eventCount+=len(ev);return out.value

capture=False;corpus=[];replayEvents=[];unsafeCases=[]
originalDependency=dep
@Dep
def capturedDependency(c,q,u):
 e=q.contents;before=raw(True);buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)];value=originalDependency(c,q,u)
 if capture:
  after=raw(True);old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);patches=[(i,y)for i,(x,y)in enumerate(zip(old,new))if x!=y]
  replayEvents.append((events[-1][:4],e.mask,hashlib.sha256(before).digest(),value,patches,buffers,[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)]))
 return value
dep=capturedDependency
originalCompare=compare
def compare(f,label,args=(),receiver=CHILD,meaningful=True):
 before=bytes(heap);bi=bytes(image);compose=ctx.composeBase;replayEvents.clear();v=originalCompare(f,label,args,receiver,meaningful)
 if capture:corpus.append((f,receiver,args,compose,v,meaningful,before,bi[0x520000-imageStart:0x550000-imageStart],raw(True),list(replayEvents)))
 return v
def unsafe(f,label,args=(),receiver=CHILD):
 global resourceIndex,liveLocal
 from unicorn import UcError
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();resourceIndex=0;liveLocal=False;before=bytes(heap);bi=bytes(image);out=U();arr=(U*len(args))(*args);ok=lib.claw_booty_progression_entry(f,receiver,arr,len(args),C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault==2;expected=raw(True);ev=list(events)
 C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);resourceIndex=0;liveLocal=False
 try:m.call(f,receiver,pack(*args));raise AssertionError('expected original unsafe prefix')
 except UcError:pass
 assert raw(False)==expected and ev==originalEvents,(label,'prefix mismatch');unsafeCases.append(dict(function=hex(f),label=label,nativeFault=ctx.fault,events=len(ev)))
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000)
def saveCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as file:
  file.write(b'BOOT'+pack(imageStart,len(imageSeed),SIZE,len(corpus))+imageSeed)
  for f,t,a,compose,out,meaning,before,globalBefore,after,replays in corpus:
   file.write(pack(f,t,len(a),*list(a)+[0]*(3-len(a)),compose,out,int(meaning),len(replays))+before+globalBefore)
   for(ev,mask,digest,value,patches,buffers,outputs)in replays:
    ef,et,ea,name=ev;name=name or b'';file.write(pack(ef,et,len(ea),*list(ea)+[0]*(40-len(ea)),mask,value,len(name),len(patches),len(buffers))+digest+name)
    for p in patches:file.write(pack(*p))
    for b,v in zip(buffers,outputs):file.write(pack(len(b))+b+v)
   file.write(after)
