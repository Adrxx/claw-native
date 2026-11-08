"""Original CString-map oracle; CString/physical allocation transports are explicit."""
import ctypes as C,hashlib,random,struct,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/cstring-assignment-agent';U=C.c_uint32
libs=[ROOT/'work'/p for p in ('image-registry-agent/libImageRegistry.dylib','resource-archive-loading-agent/libData.dylib','scene-lifecycle-agent/libSceneLifecycle.dylib','player-fade-blend-agent/libPlayerFadeBlendRuntime.dylib')]
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/ImageControllerLoadingRuntime.cpp'),str(ROOT/'Sources/CStringAssignmentRuntime.cpp'),*[str(p)for p in libs],'-o',str(WORK/'libImageCacheJoin.dylib')],check=True)
lib=C.CDLL(str(WORK/'libImageCacheJoin.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Array(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('compose','handler','fault','newMode','threshold','heap','heapAlloc')]
class Pool(C.Structure):_fields_=[('scene',Host),('maximum',U),('fault',U)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('registry','names','data','archive','arrays','pools')]+[('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*10),('mask',U),('bufferCount',U),('buffers',C.c_void_p*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_image_controller_loading_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x200000;MAP,KEY,OUT,ALT,SECOND=BASE+0x1000,BASE+0x2000,BASE+0x2100,BASE+0x2200,BASE+0x3000;ALLOC=BASE+0x10000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,0x1000);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();array=Array();pool=Pool();native=True;cursor=ALLOC;events=[];oevents=[];errors=[];calls=snapshots=0;objects={};live={};freed=[];allocationOrdinal=0;failedOrdinal=-1;mutation=0;mutationTarget=0;captures=[];capture=False;replayEvents=[]

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if iBase<=t and t+n*4<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);array.scene=pool.scene=ctx.scene;array.compose=1;array.handler=0;ctx.arrays=C.addressof(array);ctx.pools=C.addressof(pool);ctx.maximum=100000

def read(t,n=4):return C.string_at(ptr(t&~3)+(t&3),n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(ptr(t&~3)+(t&3),b,len(b))if native else m.u.mem_write(t,b)
def put(t,*v):write(t,pack(*v))
def get(t):return struct.unpack('<I',read(t))[0]
def text(t):
 b=bytearray()
 for i in range(65536):
  v=read(t+i,1)[0]
  if not v:return bytes(b)
  b.append(v)
 raise AssertionError('unterminated')
def raw():return (bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))+(C.string_at(ptr(0x510000),0x43000)if native else bytes(m.u.mem_read(0x510000,0x43000)))
def state():return hashlib.sha256(raw()).digest(),tuple(sorted(live.items())),tuple(freed)
def alloc(n):
 global cursor,allocationOrdinal
 ordinal=allocationOrdinal;allocationOrdinal+=1
 if ordinal==failedOrdinal:return 0
 p=cursor;cursor+=(max(1,n)+3)&~3;assert cursor<BASE+SIZE;objects[p]=max(1,n);live[p]=n;return p

def release(p):
 global cursor
 size=live.pop(p,None);freed.append(p)
 if globals().get("loaded",False) and size is not None and cursor==p+((max(1,size)+3)&~3):cursor=p
def destroyCString(cell):
 data=get(cell)
 if data-12==get(0x52e1c8):return
 count=(get(data-12)-1)&0xffffffff;put(data-12,count)
 if count==0:release(data-12)
def clearMap(t):
 table=get(t+4)
 if table:
  for i in range(get(t+8)):
   p=get(table+i*4)
   while p:destroyCString(p+8);p=get(p)
  release(table);put(t+4,0)
 put(t+12,0);put(t+16,0);block=get(t+20)
 while block:nextBlock=get(block);release(block);block=nextBlock
 put(t+20,0)
def effect(f,t,a):
 if f in(0x4a48e0,0x4f63ec):
  if mutation==1 and mutationTarget:put(mutationTarget,9)
  return alloc(a[0])
 if f in(0x4a49b0,0x4f6428):release(a[0]);return 0x12345678
 if f==0x4a3810:
  x,y=text(a[0]),text(a[1]);return (x>y)-(x<y)
 if f==0x4f6433:return 0x52e1cc
 if f==0x5022b5:return BASE+0x6000
 if f==0x5469e4:return len(text(a[0]))
 if f==0x4f66cc:return sourceAssign(t,a[0])
 if f==0x4f6584:destroyCString(t);return 0
 if f==0x4f61a1:
  # Declared transport of frozen SceneLifecycle clear; body independently proved.
  clearMap(t);return 0
 raise AssertionError(('service',hex(f),hex(t),a))
@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=tuple(q.arguments[:q.count]);assert not q.mask and not q.bufferCount,(hex(q.function),q.mask,q.bufferCount,list(q.sizes))
  events.append((q.function,q.receiver,a,state()));before=raw() if capture else None;activeBefore=dict(live) if capture else None;value=effect(q.function,q.receiver,a)&0xffffffff
  if capture:replayEvents.append((q.function,q.receiver,a,value,before,raw(),activeBefore,dict(live)))
  return value
 except Exception as e:
  import traceback
  errors.append((hex(q.function),q.receiver,a,traceback.format_exc()));ctx.fault=1;return 0
ABI={0x710000:1,0x5022b5:0,0x4a48e0:1,0x4a49b0:1,0x4a3810:2,0x4f6433:0,0x4f6584:0,0x4f61a1:0}
THIS={0x4f66cc,0x4f6584,0x4f61a1}
def hook(uc,f,size,user):
 if f==0x710004:
  sp=uc.reg_read(UC_X86_REG_ESP);p=m.read_words(sp+4,1)[0];put(p,get(p)-1);uc.reg_write(UC_X86_REG_EAX,get(p));uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);return
 if f not in ABI:return
 sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,ABI[f]));t=uc.reg_read(UC_X86_REG_ECX)if f in THIS else 0;identity=0x5469e4 if f==0x710000 else f;oevents.append((identity,t,a,state()));v=effect(identity,t,a);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+(ABI[f]*4 if f in THIS or f==0x710000 else 0));uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def reset(seed=0):
 global native,cursor,objects,live,freed,allocationOrdinal,failedOrdinal,mutation,mutationTarget
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=array.fault=pool.fault=0;cursor=ALLOC;objects={MAP:28,SECOND:28,KEY:256,ALT:256,OUT:4,BASE+0x6000:116};live={};freed=[];allocationOrdinal=0;failedOrdinal=-1;mutation=mutationTarget=0
 for t in(MAP,SECOND):put(t,0x5105c4,0,17,0,0,0,10)
 put(BASE+0x6028,0);put(0x510020,0);put(0x52e1c8,0x52e1b8);put(0x52e1cc,0x52e1c4);put(0x52e1b8,0xffffffff,0,0);write(0x52e1c4,b'\0');write(KEY,b'KEY\0');write(ALT,b'key\0')
def compare(f,t,a,label,meaningful=True):
 global native,calls,snapshots,cursor,objects,live,freed,allocationOrdinal
 native=True;ctx.fault=array.fault=pool.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal);args=(U*len(a))(*a);out=U();ok=lib.claw_image_controller_loading_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=events[:];owned=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,objects,live,freed,allocationOrdinal=old;actual=m.call(f,t,pack(*a),max_instructions=20000000);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4,(label,'ESP')
 assert raw()==expected,(label,'bytes',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 assert ev==oevents,(label,'events',[(x[:3],y[:3],x[3]==y[3])for x,y in zip(ev,oevents)if x!=y][:3],len(ev),len(oevents))
 if meaningful:assert out.value==actual,(label,'EAX',hex(out.value),hex(actual))
 assert owned==(cursor,objects,live,freed,allocationOrdinal),(label,'ownership')
 native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 if capture:captures.append((f,t,a,before,expected[:SIZE],bi,actual,meaningful,dict(objects),initialLive,list(replayEvents)))
 return out.value
# Optional frozen source composition views for real source-built REZ graphs.
class Registry(C.Structure):_fields_=[('scene',Host),('arrays',C.POINTER(Array)),('images',C.c_void_p),('imageHost',C.c_void_p),('fault',U),('eventNameBytes',U)]
class Names(C.Structure):_fields_=[('scene',Host),('maximum',U),('fault',U)]
class Data(C.Structure):_fields_=[('scene',Host),('allocator',C.POINTER(Array)),('maximum',U),('fault',U)]
class Table(C.Structure):_fields_=[('scene',Host),('allocator',C.POINTER(Array)),('maximum',U),('fault',U),('byteContext',C.c_void_p),('bytes',C.c_void_p)]
class Archive(C.Structure):_fields_=[('table',C.POINTER(Table)),('headerToken',U),('maximum',U)]
TableDep=C.CFUNCTYPE(U,C.POINTER(Table),C.POINTER(Call),C.c_void_p)
@TableDep
def tableDep(c,q,u):return dep(C.byref(ctx),q,u)
lib.claw_resource_table_construction_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Table),TableDep,C.c_void_p,C.POINTER(U)]
registry=Registry();names=Names();dataContext=Data();tableContext=Table();archive=Archive()
for c in(registry,names,dataContext,tableContext):c.scene=ctx.scene
registry.arrays=dataContext.allocator=tableContext.allocator=C.pointer(array);names.maximum=dataContext.maximum=tableContext.maximum=100000;archive.table=C.pointer(tableContext);archive.headerToken=BASE+0x4000
IMAGECONTROLLER=BASE+0x5000;SCENE=BASE+0x5100;CONTROL=BASE+0x5200;FOLDER=BASE+0x5300;DIRECTORYNAME=BASE+0x5400;SEPARATOR=BASE+0x5600
rez=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(rez).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
filePosition=0;imageLoads=[];loaded=False;restoring=False
oldEffect=effect

def effect(f,t,a):
 global filePosition
 if f==0x4a7840:filePosition=a[1];return 0
 if f==0x4a7260:
  n=a[1]*a[2];blob=rez[filePosition:filePosition+n];write(a[0],blob);filePosition+=len(blob);return len(blob)//a[1] if a[1] else 0
 if f in(0x4d2410,0x4d2540):
  # Original image wrapper and resource reads run. Physical codec/surface
  # initialization remains the existing registry's explicit service profile.
  blob=read(a[0],a[2]);imageLoads.append((get(t+4),a,hashlib.sha256(blob).hexdigest()));return 1
 if f==0x4ce8e0:put(t,0x50becc);release(t);return t
 if f==0x4d27a0:return 1
 return oldEffect(f,t,a)
ABI.update({0x4a7840:3,0x4a7260:4,0x4d2410:4,0x4d2540:3,0x4ce8e0:1,0x4d27a0:2});THIS.update({0x4d2410,0x4d2540,0x4ce8e0,0x4d27a0})
originalReset=reset

def reset(seed=0,joined=False):
 global filePosition,imageLoads,loaded
 originalReset(seed);filePosition=0;imageLoads=[];loaded=joined;put(0x5469e4,0x710000);put(0x5469e8,0x710004);cstring.fault=stringLifecycle.fault=stringFade.fault=0
 ctx.registry=ctx.names=ctx.data=ctx.archive=0
 if joined:
  ctx.registry=C.addressof(registry);ctx.names=C.addressof(names);ctx.data=C.addressof(dataContext);ctx.archive=C.addressof(archive)
  registry.fault=names.fault=dataContext.fault=tableContext.fault=0;registry.eventNameBytes=0
  put(IMAGECONTROLLER,0x513b88,0,0,SCENE);put(IMAGECONTROLLER+16,0x5105c4,0,17,0,0,0,10);put(SCENE+28,BASE+0x5700);put(CONTROL+12,0x7771);write(DIRECTORYNAME,b'IMAGES\0');write(SEPARATOR,b'_\0')
  objects.update({IMAGECONTROLLER:44,SCENE:60,CONTROL:72,FOLDER:76,DIRECTORYNAME:256,SEPARATOR:4})
# Extend paired comparison to include physical read cursor and payload events.
# Original helpers only adapt physical FILE/image endpoints, not table ordering.
oldCompare=compare

def compare(f,t,a,label,meaningful=True,common=False):
 global native,calls,snapshots,cursor,objects,live,freed,allocationOrdinal,filePosition,imageLoads
 if not loaded:return oldCompare(f,t,a,label,meaningful)
 native=True;ctx.fault=array.fault=pool.fault=registry.fault=names.fault=dataContext.fault=tableContext.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal,filePosition,imageLoads[:]);args=(U*len(a))(*a);out=U()
 if common:ok=lib.claw_resource_table_construction_entry(f,t,args,len(a),C.byref(tableContext),tableDep,None,C.byref(out));fault=tableContext.fault
 else:ok=lib.claw_image_controller_loading_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));fault=ctx.fault
 assert ok and not fault and not errors,(label,'native',fault,errors);expected=raw();ev=events[:];owned=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal,filePosition,imageLoads[:]);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,objects,live,freed,allocationOrdinal,filePosition,imageLoads=old;actual=m.call(f,t,pack(*a),max_instructions=20000000)
 assert raw()==expected,(label,'bytes',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 assert ev==oevents,(label,'events',[(x[:3],y[:3],x[3]==y[3])for x,y in zip(ev,oevents)if x!=y][:3],len(ev),len(oevents))
 if meaningful:assert out.value==actual,(label,'EAX',hex(out.value),hex(actual))
 assert owned==(cursor,objects,live,freed,allocationOrdinal,filePosition,imageLoads),(label,'transport')
 native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 return out.value
prefixAddress=0;prefixCount=0

def prefixHook(uc,address,size,user):
 if prefixAddress and address==prefixAddress:uc.emu_stop()
m.u.hook_add(UC_HOOK_CODE,prefixHook)
def prefix(f,t,a,address,label):
 global native,cursor,objects,live,freed,allocationOrdinal,prefixAddress,prefixCount,snapshots
 native=True;ctx.fault=array.fault=pool.fault=0;events.clear();oevents.clear();errors.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal);args=(U*len(a))(*a);out=U();ok=lib.claw_image_controller_loading_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault in(1,2) and not errors,(label,'nativeFault',ctx.fault,errors);expected=raw();ev=events[:];owned=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,objects,live,freed,allocationOrdinal=old;prefixAddress=address;m.write_words(m.stack,[m.stop,*a]);m.u.reg_write(UC_X86_REG_ECX,t);m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.emu_start(f,m.stop,count=1000000);assert m.u.reg_read(UC_X86_REG_EIP)==address,(label,hex(m.u.reg_read(UC_X86_REG_EIP)));prefixAddress=0;assert raw()==expected,(label,'heap');assert ev==oevents,(label,'events');assert owned==(cursor,objects,live,freed,allocationOrdinal),(label,'ownership');native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);prefixCount+=1;snapshots+=len(ev)+1

class StringLifecycle(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('display','graphics','audio','palette','world','image')]+[('maximum',U),('fault',U)]
class StringFade(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p)]+[(n,U)for n in('descriptorWord','descriptorToken','maximum','fault')]
class StringBlend(C.Structure):_fields_=[('fade',C.POINTER(StringFade))]+[(n,U)for n in('temporary','empty','capture')]
ByteLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class StringContext(C.Structure):_fields_=[('scene',Host),('lifecycle',C.POINTER(StringLifecycle)),('allocation',C.POINTER(StringBlend)),('arrays',C.POINTER(Array)),('byteContext',C.c_void_p),('bytes',ByteLookup),('maximum',U),('fault',U)]
class StringCall(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*4)]
StringDep=C.CFUNCTYPE(U,C.POINTER(StringContext),C.POINTER(StringCall),C.c_void_p)
stringLifecycle=StringLifecycle();stringFade=StringFade();stringBlend=StringBlend();cstring=StringContext();stringLifecycle.scene=stringFade.scene=cstring.scene=ctx.scene;stringBlend.fade=C.pointer(stringFade);cstring.lifecycle=C.pointer(stringLifecycle);cstring.allocation=C.pointer(stringBlend);cstring.arrays=C.pointer(array)
@ByteLookup
def byteLookup(_,t,n):return ptr(t&~3,((t&3)+n+3)//4)+(t&3) if ptr(t&~3,((t&3)+n+3)//4)else 0
cstring.bytes=byteLookup
@StringDep
def stringDep(c,qp,u):
 q=qp.contents;a=tuple(q.arguments[:q.count]);events.append((q.function,q.receiver,a,state()));return effect(q.function,q.receiver,a)&0xffffffff
lib.claw_cstring_assignment_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(StringContext),StringDep,C.c_void_p,C.POINTER(U)]
def sourceAssign(t,textToken):
 # Native dispatch is frozen ImageController -> new source assignment. This
 # service entry itself is not logged: the original actually executes it too.
 if events and events[-1][0]==0x4f66cc:events.pop()
 cstring.fault=stringLifecycle.fault=stringFade.fault=0;out=U();a=(U*1)(textToken)
 assert lib.claw_cstring_assignment_entry(0x4f66cc,t,a,1,C.byref(cstring),stringDep,None,C.byref(out))and not cstring.fault
 return out.value
