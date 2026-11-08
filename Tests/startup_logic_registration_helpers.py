"""Original CString-map oracle; CString/physical allocation transports are explicit."""
import ctypes as C,hashlib,random,struct,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/startup-logic-registration-agent';U=C.c_uint32
libs=[ROOT/'work'/p for p in('image-controller-loading-agent/libLoading.dylib','scene-lifecycle-agent/libSceneLifecycle.dylib','booty-story-agent/libStory.dylib','surface-blit-agent/libSurfaceBlit.dylib','cstring-assignment-agent/libCString.dylib','player-fade-blend-agent/libPlayerFadeBlendRuntime.dylib')]
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/StartupLogicRegistrationRuntime.cpp'),str(ROOT/'Sources/WorldObjectRuntime.cpp'),str(ROOT/'Sources/LogicRegistry.cpp'),*[str(p)for p in libs],'-o',str(WORK/'libRegistration.dylib')],check=True)
lib=C.CDLL(str(WORK/'libRegistration.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Array(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('compose','handler','fault','newMode','threshold','heap','heapAlloc')]
class Pool(C.Structure):_fields_=[('scene',Host),('maximum',U),('fault',U)]
class LoadingContext(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('registry','names','data','archive','arrays','pools')]+[('maximum',U),('fault',U)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('dictionary','strings','lifecycle','destruction')]+[('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*10),('mask',U),('bufferCount',U),('buffers',C.c_void_p*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_startup_logic_registration_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x200000;MAP,KEY,OUT,ALT,SECOND=BASE+0x1000,BASE+0x2000,BASE+0x2100,BASE+0x2200,BASE+0x3000;ALLOC=BASE+0x10000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();loading=LoadingContext();ctx.dictionary=C.addressof(loading);array=Array();pool=Pool();native=True;cursor=ALLOC;events=[];oevents=[];errors=[];calls=snapshots=0;objects={};live=dict(objects);freed=[];allocationOrdinal=0;failedOrdinal=-1;mutation=0;mutationTarget=0;captures=[];capture=False;replayEvents=[];sideOrdinal=0;switchRegistry=False;mutateFactory=False

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:
  return C.addressof(heap)+t-BASE if any(p<=t and t+n*4<=p+size for p,size in live.items()) else 0
 if iBase<=t and t+n*4<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);loading.scene=ctx.scene;array.scene=pool.scene=ctx.scene;array.compose=1;array.handler=0;loading.arrays=C.addressof(array);loading.pools=C.addressof(pool);ctx.maximum=100000

def read(t,n=4):return C.string_at(C.addressof(heap)+t-BASE if BASE<=t<BASE+SIZE else C.addressof(image)+t-iBase,n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(C.addressof(heap)+t-BASE if BASE<=t<BASE+SIZE else C.addressof(image)+t-iBase,b,len(b))if native else m.u.mem_write(t,b)
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
 if f in sideFunctions:
  global sideOrdinal
  sideOrdinal+=1;put(BASE+0x8000,sideOrdinal,f)
  if switchRegistry and sideOrdinal==1:put(SCENE+20,REGISTRY2)
  return 0x567890ab
 if f in(0x4a48e0,0x4f63ec):
  if mutateFactory and a[0]==372:put(REGISTRY+28,0x7788)
  if mutation==1 and mutationTarget:put(mutationTarget,9)
  return alloc(a[0])
 if f in(0x4a49b0,0x4f6428):release(a[0]);return 0x12345678
 if f==0x4a3810:
  x,y=text(a[0]),text(a[1]);return (x>y)-(x<y)
 if f==0x5469e4:return len(text(a[0]))
 if f==0x5022b5:return BASE+0x6000
 if f==0x4f66cc:
  # Explicit owning CString assignment service, not a recovered leaf here.
  b=text(a[0]);destroyCString(t);header=alloc(12+len(b)+1);put(header,1,len(b),len(b));write(header+12,b+b'\0');put(t,header+12);return t
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
ABI={0x5022b5:0,0x4a48e0:1,0x4a49b0:1,0x4a3810:2,0x5469e4:1}
THIS=set()
def hook(uc,f,size,user):
 if f not in ABI:return
 sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,ABI[f]));t=uc.reg_read(UC_X86_REG_ECX)if f in THIS else 0;oevents.append((f,t,a,state()));v=effect(f,t,a);uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+(ABI[f]*4 if f in THIS else 0));uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def reset(seed=0):
 global native,cursor,objects,live,freed,allocationOrdinal,failedOrdinal,mutation,mutationTarget
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=loading.fault=array.fault=pool.fault=0;cursor=ALLOC;objects={MAP:28,SECOND:28,KEY:256,ALT:256,OUT:4,BASE+0x6000:116};live=dict(objects);freed=[];allocationOrdinal=0;failedOrdinal=-1;mutation=mutationTarget=0
 for t in(MAP,SECOND):put(t,0x5105c4,0,17,0,0,0,10)
 put(BASE+0x6028,0);put(0x510020,0);put(0x52e1c8,0x52e1b8);put(0x52e1cc,0x52e1c4);put(0x52e1b8,0xffffffff,0,0);write(0x52e1c4,b'\0');write(KEY,b'KEY\0');write(ALT,b'key\0')
def compare(f,t,a,label,meaningful=True):
 global native,calls,snapshots,cursor,objects,live,freed,allocationOrdinal,sideOrdinal
 native=True;ctx.fault=loading.fault=array.fault=pool.fault=strings.fault=lifecycle.fault=fade.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal,sideOrdinal);args=(U*len(a))(*a);out=U();ok=lib.claw_startup_logic_registration_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=events[:];owned=(cursor,dict(objects),dict(live),freed[:],allocationOrdinal,sideOrdinal);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,objects,live,freed,allocationOrdinal,sideOrdinal=old;actual=m.call(f,t,pack(*a),max_instructions=20000000);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+(0 if f==0x401000 else len(a)*4),(label,'ESP')
 assert raw()==expected,(label,'bytes',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 assert ev==oevents,(label,'events',[(x[:3],y[:3],x[3]==y[3])for x,y in zip(ev,oevents)if x!=y][:3],len(ev),len(oevents))
 if meaningful:assert out.value==actual,(label,'EAX',hex(out.value),hex(actual))
 assert owned==(cursor,objects,live,freed,allocationOrdinal,sideOrdinal),(label,'ownership')
 native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 if capture:captures.append((f,t,a,before,expected[:SIZE],bi,actual,meaningful,dict(objects),initialLive,list(replayEvents)))
 return out.value
# Optional frozen source composition views for real source-built REZ graphs.

program=json.loads((WORK/'program.json').read_text());sideFunctions={x['function']for x in program if not x['kind']};ABI.update({f:0 for f in sideFunctions})
SCENE=BASE+0x7000;REGISTRY=BASE+0x7100;REGISTRY2=BASE+0x7200;LOGIC=BASE+0x7400
class Lifecycle(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('display','graphics','audio','palette','world','image')]+[('maximum',U),('fault',U)]
class Fade(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p)]+[(n,U)for n in('descriptorWord','descriptorToken','maximum','fault')]
class Blend(C.Structure):_fields_=[('fade',C.POINTER(Fade))]+[(n,U)for n in('temporary','empty','capture')]
class Strings(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('lifecycle','allocation','arrays','byteContext','bytes')]+[('maximum',U),('fault',U)]
class Destruction(C.Structure):_fields_=[('holder',U),('held',U),('empty',U)]
lifecycle=Lifecycle();fade=Fade();blend=Blend();strings=Strings();destruction=Destruction();destruction.empty=get(0x52e1cc)
for c in(lifecycle,fade,strings):c.scene=ctx.scene;c.maximum=1000000
blend.fade=C.pointer(fade);strings.lifecycle=C.addressof(lifecycle);strings.allocation=C.addressof(blend);strings.arrays=C.addressof(array);ctx.strings=C.addressof(strings);ctx.lifecycle=C.addressof(lifecycle);ctx.destruction=C.addressof(destruction)
ByteLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
@ByteLookup
def bytesLookup(_,t,n):
 if BASE<=t and t+n<=BASE+SIZE:return C.addressof(heap)+t-BASE if any(p<=t and t+n<=p+s for p,s in live.items())else None
 if iBase<=t and t+n<=iEnd+1:return C.addressof(image)+t-iBase
 return None
strings.bytes=C.cast(bytesLookup,C.c_void_p)
oldReset=reset

def reset(seed=0):
 global sideOrdinal,switchRegistry,mutateFactory
 oldReset(seed);sideOrdinal=0;switchRegistry=mutateFactory=False
 for c in(strings,lifecycle,fade):c.fault=0
 objects.update({SCENE:60,REGISTRY:44,REGISTRY2:44,LOGIC:372,BASE+0x8000:8});live.update(objects)
 put(SCENE+20,REGISTRY)
 for t in(REGISTRY,REGISTRY2):put(t,0x513b60,0,0,SCENE);put(t+16,0x5105c4,0,17,0,0,0,10)
 put(0x5469e4,0x710020);put(0x5469e8,0x710024);put(0x5469ec,0x710028)
# Atomic interlocked transport is scalar, not a new game source body.
m.u.mem_map(0x710000,4096)
def atomic(u,f,size,user):
 if f not in(0x710020,0x710024,0x710028):return
 sp=u.reg_read(UC_X86_REG_ESP);p=m.read_words(sp+4,1)[0]
 if f==0x710020:
  oevents.append((0x5469e4,0,(p,),state()));v=effect(0x5469e4,0,(p,))
 else:v=(get(p)+(1 if f==0x710028 else -1))&0xffffffff;put(p,v)
 u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_ESP,sp+8);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,atomic)
