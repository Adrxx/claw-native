"""Pinned unchanged-source resize oracle; explicit physical DD/CRT adapters."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/scene-display-resize-agent';U=C.c_uint32
assert hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest()=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
libpath=WORK/'libResize.dylib'
names=['SceneDisplayResizeRuntime','SceneDisplayRuntime','SinglePlayerSceneRuntime','WorldFileRuntime','SpatialGridRuntime','SceneCameraRuntime','WorldPlaneRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster','GraphicsManagerLifecycleRuntime','GraphicsManagerConstructionRuntime','PaletteResourceRuntime','AmbientAudioBackendRuntime','CArrayRuntime','SoundTriggerLogicRuntime','EnemySpeechRuntime','SpeechActor','AudioEvents','ActorResourceBindings','ActorDestruction','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','AnimationEngine','AnimationOperations']
sources=[ROOT/'Sources'/f'{n}.cpp'for n in names]
if not libpath.exists()or any(p.stat().st_mtime>libpath.stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(libpath)],check=True)
lib=C.CDLL(str(libpath))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class GraphicsGlobals(C.Structure):_fields_=[('device',U),('cooperative',U),('shifts',U*3),('reductions',U*3)]
class GraphicsContext(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('palette',C.c_void_p),('maximum',U),('fault',U)]
class DisplayContext(C.Structure):_fields_=[('scene',Host),('graphics',C.c_void_p),('image',C.c_void_p),('maximum',U),('fault',U)]
class Context(C.Structure):_fields_=[('scene',Host),('display',C.c_void_p),('graphics',C.c_void_p),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('mask',U),('bufferCount',U),('buffers',C.c_void_p*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_scene_display_resize_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x40000
PARENT,HOLDER,AUX,PRIMARY,MANAGER,OLD,NEW,DEVICE,DD,VT,DDVT,BLOCK=[BASE+0x1000+i*0x1000 for i in range(12)]
FRONT=BASE+0xd000
NODE=BLOCK+4;ALLOC=BASE+0x10000;TEB,GDT=0x10ed000,0x10ee000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x700000,0x1000);m.u.mem_map(0x710000,0x1000);m.executed.clear();m.stack=0x200e000
imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();rng=random.Random(0x4d4280)
ctx=Context();gg=GraphicsGlobals();gc=GraphicsContext();dc=DisplayContext();events=[];originalEvents=[];errors=[];calls=snapshotCount=0
allocCursor=allocBase=ALLOC;allocIndex=allocIndexBase=allocFail=0;physicalWidth=640;physicalHeight=480;physicalDepth=8;modeResult=0;displayResult=0;factoryResult=NEW;ready=1;mutation='';joined=False;buffers=[];originalBuffers=[]
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('missing',hex(t),n))
 return p
ctx.scene=Host(None,lookup,None,None,None,None);ctx.maximum=100000
ctx.display=ctx.graphics=0;gc.scene=dc.scene=ctx.scene;gc.globals=C.addressof(gg);gc.maximum=dc.maximum=100000

def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def publish():
 if not ctx.graphics:return
 put(0x541398,[gg.device]);put(0x541374,[gg.cooperative]);put(0x54135c,list(gg.shifts)+list(gg.reductions))
def importGlobals():
 if not ctx.graphics:return
 gg.device=get(0x541398)[0];gg.cooperative=get(0x541374)[0];gg.shifts[:]=get(0x54135c,3);gg.reductions[:]=get(0x541368,3)
def raw(native):
 if native:publish();return bytes(heap)+C.string_at(ptr(0x520000),0x30000)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
def physicalSurface(t,w,h,bpp,native):
 put(t+8,[DD],native);put(t+20,[h,w],native);put(t+132,[w,h],native);put(t+164,[bpp],native)

def effect(f,t,a,native):
 global allocCursor,allocIndex,physicalWidth,physicalHeight,physicalDepth
 if f==0x4f63ec:
  allocIndex+=1
  if allocIndex==allocFail:return 0
  token=allocCursor;allocCursor+=(a[0]+3)&~3;assert allocCursor<BASE+SIZE;return token
 if f==0x4f6428:return 0
 if f==0x4bc4f0:
  if a[0]:put(a[0]+40,[0xdecafeca],native)
  if mutation=='typeAfterDelete':put(AUX+4,[2],native)
  return 0
 if f in(0x4bcf80,0x4bc670,0x4bc890):
  if mutation=='typeAfterAttach'and f==0x4bcf80:put(AUX+4,[2],native)
  return factoryResult
 if f==0x4bd1c0:
  if mutation=='flagsAfterMode':put(PARENT+52,[2],native)
  physicalWidth,physicalHeight,physicalDepth=a
  return modeResult
 if f==0x700054:
  if mutation=='flagsAfterMode':put(PARENT+52,[2],native)
  physicalWidth,physicalHeight,physicalDepth=a[1:];return modeResult
 if f==0x700030:
  desc=[0]*27;desc[0]=108;desc[2]=physicalHeight;desc[3]=physicalWidth;desc[21]=physicalDepth;desc[22:25]=[0xff0000,0xff00,0xff]
  if native:C.memmove(buffers[0],pack(*desc),108)
  else:m.u.mem_write(originalBuffers[0],pack(*desc))
  return displayResult
 if f==0x710030:
  if native:C.memmove(buffers[1],pack(DD),4)
  else:m.u.mem_write(originalBuffers[1],pack(DD))
  if mutation=='typeAfterAttach':put(AUX+4,[2],native)
  return displayResult
 if f==0x700018:
  descriptor=get(a[1],27,native=native)
  if descriptor[1]&4:physicalWidth=descriptor[3]
  if descriptor[1]&2:physicalHeight=descriptor[2]
  if descriptor[1]&0x1000:physicalDepth=descriptor[21]
  put(a[2],[DD],native);return displayResult
 if f==0x710074:return 0
 if f==0x710058:
  desc=[0]*27;desc[0]=108;desc[1]=7;desc[2]=physicalHeight;desc[3]=physicalWidth;desc[4]=physicalWidth;desc[21]=physicalDepth;put(a[1],desc,native);return displayResult
 if f==0x710008:return 0
 if f==0x4b9180:physicalSurface(t,a[1],a[2],a[3],native);return ready
 if f==0x4b9380:physicalSurface(t,physicalWidth,physicalHeight,physicalDepth,native);return ready
 if f==0x4b9990:return 1
 if f==0x4bc490:put(a[0]+4,[0x12345678],native);return 0
 if f in(0x4bc5f0,0x4bc810):return t
 if f==0x700014:return ready
 if f==0x4bd260:return 0
 raise AssertionError(('service',hex(f),hex(t),a))

@Dep
def dep(_,qp,u):
 global buffers
 try:
  q=qp.contents;a=list(q.arguments[:q.count]);buffers=list(q.buffers[:q.bufferCount]);before=[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)];events.append((q.function,q.receiver,tuple(a),q.mask,tuple(before),snap(True)));value=effect(q.function,q.receiver,a,True);importGlobals();return value
 except Exception as e:errors.append(e);return 0
ABIS={0x4bc4f0:(1,4),0x4bcf80:(2,8),0x4bc670:(5,20),0x4bc890:(1,4),0x4bd1c0:(3,12),0x700014:(0,0),0x4f63ec:(1,0),0x4f6428:(1,0),0x4b9180:(5,20),0x4b9380:(1,4),0x4b9990:(1,4),0x4bc490:(1,4),0x4bc5f0:(1,4),0x4bc810:(1,4),0x4bd260:(3,0),0x700054:(4,16),0x700030:(2,8),0x710030:(3,12),0x710058:(2,8),0x710008:(1,4),0x700018:(4,16),0x710074:(3,12)}
CDECL={0x4f63ec,0x4f6428,0x4bd260,0x700054,0x700030,0x710030,0x710058,0x710008,0x700018,0x710074}
imageGlobals=(U*288)();currentFunction=0

def hook(uc,f,size,u):
 global allocCursor,allocIndex,originalBuffers
 if f==currentFunction:allocCursor=allocBase;allocIndex=allocIndexBase
 if f not in ABIS:return
 if ctx.display and f in(0x4bc4f0,0x4bcf80,0x4bc670,0x4bc890,0x4bc810):return
 if ctx.graphics and f in(0x4bd1c0,0x4bc5f0):return
 if ctx.display and dc.image and f in(0x4b9180,0x4b9380,0x4b9990,0x4bc490):return
 sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=list(m.read_words(sp+4,n));t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX);mask=0;originalBuffers=[]
 if f==0x700030:originalBuffers=[a[1]];a[1]=0;mask=2
 elif f==0x710030:originalBuffers=a[1:3];a[1:3]=[0,0];mask=6
 elif f==0x710074:originalBuffers=[a[2]];a[2]=0;mask=4
 # SetAt/GetDisplayMode local descriptors are initialized source bytes.
 before=[bytes(uc.mem_read(p,108 if f==0x700030 else 8 if f==0x710074 else 4))for p in originalBuffers]
 originalEvents.append((f,t,tuple(a),mask,tuple(before),snap(False)));value=effect(f,t,a,False);uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):m.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.write_words(TEB,[0xdeadbeef])

def fresh(kind=2,width=640,height=480,depth=8,compose=False):
 global allocCursor,allocBase,allocIndex,allocIndexBase,allocFail,physicalWidth,physicalHeight,physicalDepth,modeResult,displayResult,factoryResult,ready,mutation,joined
 C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);C.memmove(C.addressof(image),imageSeed,len(image));ctx.fault=gc.fault=dc.fault=0;ctx.display=ctx.graphics=0;joined=compose;allocCursor=allocBase=ALLOC;allocIndex=allocIndexBase=allocFail=0;physicalWidth,physicalHeight,physicalDepth=width,height,depth;modeResult=displayResult=0;factoryResult=NEW;ready=1;mutation=''
 put(PARENT,[0]*15);put(PARENT+4,[HOLDER]);put(PARENT+28,[MANAGER]);put(PARENT+52,[0]);put(HOLDER+16,[PRIMARY,AUX]);put(AUX,[0x50e8e4,kind,0,PARENT,width,height,depth]);put(PRIMARY,[0x5138d8,0,0,PARENT,width,height,depth]);put(AUX+44,[OLD,1]);put(PRIMARY+44,[OLD]);put(OLD,[0x513588]);put(OLD+4,[NODE]);put(OLD+8,[DD]);put(OLD+120,[1]);put(OLD+144,[0x51079c,0,0,0,0]);put(NEW,[VT]);put(VT+20,[0x700014]);put(MANAGER,[DEVICE]);put(MANAGER+0x880,[0]);put(MANAGER+0x3b8,[0x51000c,NODE,NODE,1,0,BLOCK,10]);put(BLOCK,[0]);put(NODE,[0,0,OLD]);put(DEVICE,[VT]);put(VT+0x30,[0x700030]);put(VT+0x54,[0x700054]);put(DD,[DDVT]);put(DDVT+0x30,[0x710030]);put(DDVT+0x58,[0x710058]);put(DDVT+8,[0x710008]);gg.device=DEVICE;gg.cooperative=MANAGER;gg.shifts[:]=[7,8,9];gg.reductions[:]=[1,2,3];put(0x541398,[gg.device]);put(0x541374,[gg.cooperative]);put(0x54135c,list(gg.shifts)+list(gg.reductions))
 if kind:put(PRIMARY+44,[FRONT]);put(FRONT+8,[DD])
 if compose:ctx.display=C.addressof(dc);ctx.graphics=C.addressof(gc);dc.graphics=C.addressof(gc);dc.image=C.addressof(imageGlobals);C.memset(imageGlobals,0,C.sizeof(imageGlobals));put(MANAGER+0x474,[depth]);put(VT+0x18,[0x700018]);put(DDVT+0x74,[0x710074])
 return AUX if kind else PRIMARY

def compare(f,p,args,label):
 global allocBase,allocIndexBase,currentFunction,calls,snapshotCount,physicalWidth,physicalHeight,physicalDepth
 currentFunction=f;ctx.fault=0;events.clear();originalEvents.clear();errors.clear();allocBase=allocCursor;allocIndexBase=allocIndex;before=bytes(heap);bi=bytes(image);bg=bytes(gg);physical=(physicalWidth,physicalHeight,physicalDepth);a=(U*3)(*args);out=U();ok=lib.claw_scene_display_resize_entry(f,p,a,3,C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events)
 C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(gg),bg,len(bg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);physicalWidth,physicalHeight,physicalDepth=physical;actual=m.call(f,p,pack(*args));assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+16,(label,'SP')
 got=raw(False)
 if got!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x[:5],y[:5],x[5]==y[5])for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 assert actual==out.value,(label,'EAX',actual,out.value);C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);importGlobals();calls+=1;snapshotCount+=len(ev);return actual
unsafeCases=[]
def unsafe(f,p,args,label):
 global allocBase,allocIndexBase,currentFunction,physicalWidth,physicalHeight,physicalDepth
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();currentFunction=f;allocBase=allocCursor;allocIndexBase=allocIndex;before=bytes(heap);bi=bytes(image);bg=bytes(gg);physical=(physicalWidth,physicalHeight,physicalDepth);a=(U*3)(*args);out=U();ok=lib.claw_scene_display_resize_entry(f,p,a,3,C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault in(1,2),(label,'expectedfault',ok,ctx.fault,errors);expected=raw(True);ev=list(events)
 C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(gg),bg,len(bg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);physicalWidth,physicalHeight,physicalDepth=physical
 try:m.call(f,p,pack(*args));raise AssertionError('expected original unchecked fault')
 except UcError:pass
 assert raw(False)==expected and ev==originalEvents,(label,'prefix',len(ev),len(originalEvents));unsafeCases.append({'label':label,'fault':ctx.fault,'events':len(ev),'originalFaultAddress':hex(m.u.reg_read(UC_X86_REG_EIP))});return ctx.fault
# Exact-size sanitizer replay material, captured only from paired passing calls.
capture=False;corpus=[];replayEvents=[];allocations={}
observedEffect=effect

def effect(f,t,a,native):
 value=observedEffect(f,t,a,native)
 if native and f==0x4f63ec and value:allocations[value]=(a[0]+3)//4
 return value
observedDep=dep
@Dep
def recordedDep(c,q,u):
 e=q.contents;before=raw(True);bb=[C.string_at(e.buffers[i],e.sizes[i])for i in range(e.bufferCount)];value=observedDep(c,q,u)
 if capture:
  old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(before)//4),raw(True));patches=[(i,y)for i,(x,y)in enumerate(zip(old,new))if x!=y];replayEvents.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.mask,hashlib.sha256(before).digest(),value,patches,bb,[C.string_at(e.buffers[i],e.sizes[i])for i in range(e.bufferCount)]))
 return value
dep=recordedDep
observedFresh=fresh

def fresh(kind=2,width=640,height=480,depth=8,compose=False):allocations.clear();return observedFresh(kind,width,height,depth,compose)
observedCompare=compare

def compare(f,p,args,label):
 before=bytes(heap);gi=C.string_at(ptr(0x520000),0x30000);bg=bytes(gg);flags=[int(bool(ctx.display)),int(bool(ctx.graphics))];objects=dict(allocations);replayEvents.clear();v=observedCompare(f,p,args,label)
 if capture:corpus.append((f,p,args,flags,bg,before,gi,raw(True),v,list(replayEvents),objects))
 return v

def saveCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as file:
  file.write(b'RSIZ'+pack(imageStart,len(imageSeed),SIZE,len(corpus))+imageSeed)
  for f,p,a,flags,bg,before,gi,after,out,replays,objects in corpus:
   file.write(pack(f,p,*a,*flags,out,len(replays),len(objects))+bg+before+gi)
   for item in objects.items():file.write(pack(*item))
   for ef,et,ea,mask,digest,value,patches,buffers,outputs in replays:
    file.write(pack(ef,et,len(ea),*list(ea)+[0]*(8-len(ea)),mask,value,len(patches),len(buffers))+digest)
    for patch in patches:file.write(pack(*patch))
    for b,v in zip(buffers,outputs):file.write(pack(len(b))+b+v)
   file.write(after)
