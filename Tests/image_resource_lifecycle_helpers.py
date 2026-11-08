"""Whole missing image wrappers; explicit source-callee/platform boundaries."""
import ctypes as C,hashlib,random,struct,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/image-resource-lifecycle-agent';U=C.c_uint32
libs=[ROOT/'work'/p for p in('image-controller-loading-agent/libLoading.dylib','scene-lifecycle-agent/libSceneLifecycle.dylib','booty-story-agent/libStory.dylib','surface-blit-agent/libSurfaceBlit.dylib','cstring-assignment-agent/libCString.dylib','player-fade-blend-agent/libPlayerFadeBlendRuntime.dylib')]
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/ImageResourceLifecycleRuntime.cpp'),str(ROOT/'Sources/PCXCreationRuntime.cpp'),*[str(p)for p in libs],'-o',str(WORK/'libLife.dylib')],check=True)
lib=C.CDLL(str(WORK/'libLife.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('loading','images','display','story','pcx','blit','strings','lifecycle')]+[('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*10),('mask',U),('bufferCount',U),('buffers',C.c_void_p*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_image_resource_lifecycle_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x200000
IMAGE,SURFACE,ALT,COMP,COMPALT,RESOURCE,SCENE,GRAPHICS,DD,DDALT,DDVT,PAYLOAD,AUX,ALTBUFFER=tuple(BASE+x for x in(0x1000,0x2000,0x2100,0x3000,0x3100,0x4000,0x5000,0x6000,0x7000,0x7100,0x7200,0x8000,0x8100,0x8200))
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,4096);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();native=True;events=[];oevents=[];errors=[];calls=snapshots=0;objects={};live={};freed=[];capture=False;captures=[];replay=[];mutation=0;lost=restore=0;factory=SURFACE;kind=0x504358;resident=PAYLOAD;pixelResult=1;prefixAddress=0

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if iBase<=t and t+n*4<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);ctx.maximum=100000

def read(t,n=4):return C.string_at(ptr(t&~3)+(t&3),n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(ptr(t&~3)+(t&3),b,len(b))if native else m.u.mem_write(t,b)
def put(t,*v):write(t,pack(*v))
def get(t):return struct.unpack('<I',read(t))[0]
def raw():return (bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))+(C.string_at(ptr(0x510000),0x43000)if native else bytes(m.u.mem_read(0x510000,0x43000)))
def state():return hashlib.sha256(raw()).digest(),tuple(sorted(live.items())),tuple(freed)
def effect(f,t,a,q=None):
 if f==0x4f63ec:
  if not factory:return 0
  p=BASE+0x180000;objects[p]=max(1,a[0]);live[p]=a[0];return p
 if f in(0x4babe0,0x4bef50,0x4b9e90):return pixelResult
 if f==0x4b9990:put(t+184,int(a[0]!=0xffffffff));return 0
 if f==0x4bc670:
  if factory:live[factory]=objects[factory]
  return factory
 if f==0x4bc4f0:
  live.pop(a[0],None);freed.append(a[0])
  if mutation==1:put(IMAGE+48,COMPALT)
  return 0
 if f==0x4f6428:
  live.pop(a[0],None);freed.append(a[0])
  if mutation==2 and a[0]==PAYLOAD:put(COMP+32,ALTBUFFER)
  return 0x12345678
 if f==0x710000:
  if mutation==3:put(IMAGE+44,ALT)
  return lost
 if f==0x710004:return restore
 if f==0x4b61b0:return kind
 if f==0x4b61c0:return resident
 if f==0x4d2380:
  # Exact boundary for isolated restore wrapper; joined graph test replaces it
  # with actual frozen type/acquire/load/release and GameImage source bodies.
  put(IMAGE+44,SURFACE);put(IMAGE+16,30,20);return pixelResult
 if f==0x4b95b0:return pixelResult
 if f==0x4b99d0:return 0
 raise AssertionError(('service',hex(f),hex(t),a))
@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=tuple(q.arguments[:q.count]);assert not q.mask and not q.bufferCount
  events.append((q.function,q.receiver,a,state()));before=raw()if capture else None;owned=dict(live);value=effect(q.function,q.receiver,a,q)&0xffffffff
  if capture:replay.append((q.function,q.receiver,a,value,before,raw(),owned,dict(live)))
  return value
 except Exception as e:errors.append(str(e));ctx.fault=1;return 0
ABI={0x4bc670:5,0x4bc4f0:1,0x4f6428:1,0x710000:1,0x710004:1,0x4b61b0:0,0x4b61c0:0,0x4d2380:2,0x4b95b0:5,0x4b99d0:0,0x4f63ec:1,0x4babe0:1,0x4bef50:4,0x4b9e90:4,0x4b9990:1}
THIS={0x4bc670,0x4bc4f0,0x4b61b0,0x4b61c0,0x4d2380,0x4b95b0,0x4b99d0,0x4babe0,0x4b9e90,0x4b9990}
def hook(u,f,size,user):
 if prefixAddress and f==prefixAddress:u.emu_stop();return
 if f not in ABI:return
 sp=u.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,ABI[f]));t=u.reg_read(UC_X86_REG_ECX)if f in THIS else 0;oevents.append((f,t,a,state()));v=effect(f,t,a);u.reg_write(UC_X86_REG_EAX,v&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+(ABI[f]*4 if f in THIS or f in(0x710000,0x710004,0x4bef50) else 0));u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0):
 global native,objects,live,freed,mutation,lost,restore,factory,kind,resident,pixelResult
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=0;objects={IMAGE:52,SURFACE:188,ALT:188,COMP:40,COMPALT:40,RESOURCE:96,SCENE:60,GRAPHICS:2180,DD:4,DDALT:4,DDVT:128,PAYLOAD:128,AUX:64,ALTBUFFER:64};live=dict(objects);freed=[];mutation=0;lost=restore=0;factory=SURFACE;kind=0x504358;resident=PAYLOAD;pixelResult=1
 for n in('loading','images','display','story','pcx','blit','strings','lifecycle'):setattr(ctx,n,0)
 put(IMAGE,0x513a70,9,0,SCENE);put(IMAGE+44,SURFACE,COMP);put(SCENE+28,GRAPHICS)
 put(SURFACE+8,DD);put(SURFACE+20,20,30);put(SURFACE+184,0);put(ALT+8,DDALT);put(DD,DDVT);put(DDALT,DDVT);put(DDVT+0x60,0x710000);put(DDVT+0x6c,0x710004)
 put(COMP+12,PAYLOAD);put(COMP+32,AUX);put(COMPALT+12,ALTBUFFER);put(COMPALT+32,0);put(RESOURCE+20,128);put(0x54316c,1);put(0x543170,0)

def compare(f,t,a,label,meaningful=True,unsafe=False):
 global native,calls,snapshots,objects,live,freed,prefixAddress
 native=True;ctx.fault=0;events.clear();oevents.clear();errors.clear();replay.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(dict(objects),dict(live),freed[:]);args=(U*len(a))(*a);out=U();ok=lib.claw_image_resource_lifecycle_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert (not ok and ctx.fault)if unsafe else(ok and not ctx.fault and not errors),(label,'native',ctx.fault,errors)
 expected=raw();ev=events[:];owned=(dict(objects),dict(live),freed[:]);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);objects,live,freed=old;actual=0
 prefixAddress=0x4d27da if unsafe else 0
 try:actual=m.call(f,t,pack(*a),max_instructions=10000000)
 except (UcError,AssertionError):assert unsafe and m.u.reg_read(UC_X86_REG_EIP)==prefixAddress,(label,'source prefix',hex(m.u.reg_read(UC_X86_REG_EIP)))
 else:assert not unsafe;assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4,(label,'SP')
 prefixAddress=0
 assert raw()==expected,(label,'bytes',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 assert ev==oevents,(label,'events',[(x[:3],y[:3],x[3]==y[3])for x,y in zip(ev,oevents)if x!=y][:3],len(ev),len(oevents))
 if meaningful and not unsafe:assert out.value==actual,(label,'EAX',hex(out.value),hex(actual))
 assert owned==(objects,live,freed),(label,'ownership');native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 if capture and not unsafe:captures.append((f,t,a,before,expected[:SIZE],bi,actual,meaningful,dict(objects),initialLive,list(replay)))
 return out.value
