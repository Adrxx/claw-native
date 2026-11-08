"""Whole original vertical-flip oracle with exact byte views and explicit DD."""
import ctypes as C,hashlib,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/surface-transform-agent';U=C.c_uint32
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib','-I',str(ROOT/'Sources'),str(ROOT/'Sources/SurfaceTransformRuntime.cpp'),str(ROOT/'work/game-image-agent/libGameImageRuntime.dylib'),'-o',str(WORK/'libTransform.dylib')],check=True)
lib=C.CDLL(str(WORK/'libTransform.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
Bytes=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Globals(C.Structure):_fields_=[('delta',U),('fx',U*25),('flags',U),('key',U),('effects',U*4),('palette',U*256)]
class Context(C.Structure):_fields_=[('scene',Host),('byteContext',C.c_void_p),('bytes',Bytes),('images',C.POINTER(Globals)),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*8),('count',U),('destination',C.c_void_p),('source',C.c_void_p)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_surface_transform_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000;SURFACE=BASE+0x1000;DD=BASE+0x2000;VT=BASE+0x2100;PIXELS=BASE+0x10000;SCRATCH=BASE+0x90000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,4096);m.executed.clear();heap=(C.c_uint8*SIZE)();pe=(C.c_uint8*0x100).from_buffer_copy(m.u.mem_read(0x513600,0x100));ctx=Context();images=Globals();native=True;calls=snapshots=0;events=[];oevents=[];errors=[];free=[];live={};objects={};lock=0;allocation=True;lockResult=0;restore=1;unlockResult=0;compose=True;mutate=False;alias=0;captures=[];record=False;trace=[]
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def raw():return bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))
def read(t,n):return C.string_at(C.addressof(heap)+t-BASE,n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(C.addressof(heap)+t-BASE,b,len(b))if native else m.u.mem_write(t,b)
def put(t,*v):write(t,pack(*v))
def get(t):return struct.unpack('<I',read(t,4))[0]
def valid(t,n):return any(p<=t and t+n<=p+s for p,s in live.items())
@Lookup
def lookup(_,t,n):return (C.addressof(heap)+t-BASE if valid(t,n*4)else C.addressof(pe)+t-0x513600 if 0x513600<=t and t+n*4<=0x513700 else None) if t%4==0 else None
@Bytes
def byteLookup(_,t,n):return C.addressof(heap)+t-BASE if valid(t,n)else None
ctx.scene=Host(None,lookup,None,None,None,None);ctx.bytes=byteLookup;ctx.images=C.pointer(images);ctx.maximum=10000000

def state():return hashlib.sha256(raw()).digest(),tuple(sorted(live.items())),tuple(free)
def effect(f,t,a):
 if f==0x4b9730:return PIXELS if lockResult==0 else 0
 if f==0x710000:
  if not lockResult:put(SURFACE+48,PIXELS)
  return lockResult
 if f==0x4b9e60:return restore
 if f==0x4bd260:return 0
 if f==0x4f63ec:
  if mutate:put(SURFACE+20,3,2)
  if not allocation:return 0
  p=alias or SCRATCH
  if not alias:live[p]=a[0];objects[p]=a[0]
  return p
 if f==0x710004:return unlockResult
 if f==0x4f6428:
  free.append(a[0])
  if not alias:live.pop(a[0])
  return 0
 raise AssertionError((hex(f),t,a))
@Dep
def dep(c,p,u):
 try:
  q=p.contents;assert not q.destination and not q.source;a=tuple(q.arguments[:q.count]);events.append((q.function,q.receiver,a,state()));beforeEffect=raw()if record else None;activeBefore=dict(live);value=effect(q.function,q.receiver,a)&0xffffffff
  if record:trace.append((q.function,q.receiver,a,value,beforeEffect,raw(),activeBefore,dict(live)))
  return value
 except Exception as e:errors.append(str(e));ctx.fault=1;return 0
ABI={0x4b9730:1,0x4f63ec:1,0x4f6428:1,0x710000:5,0x710004:2,0x4b9e60:0,0x4bd260:3}
def hook(u,f,s,user):
 if f not in ABI or f==0x4b9730 and compose:return
 sp=u.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,ABI[f]));t=u.reg_read(UC_X86_REG_ECX)if f in(0x4b9730,0x4b9e60)else 0;oevents.append((f,t,a,state()));v=effect(f,t,a);u.reg_write(UC_X86_REG_EAX,v&0xffffffff);pop=ABI[f]*4 if f in(0x4b9730,0x4b9e60,0x710000,0x710004)else 0;u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(width,height,pitch=None,seed=0):
 global native,objects,live,free,allocation,lockResult,restore,unlockResult,compose,mutate,alias
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);ctx.fault=0;free=[];allocation=True;lockResult=0;restore=1;unlockResult=0;compose=True;mutate=False;alias=0
 pitch=pitch if pitch is not None else width;capacity=max(1,(max(0,height)-1)*max(0,pitch)+max(0,width));assert capacity<0x80000
 objects={SURFACE:188,DD:4,VT:132,PIXELS:capacity};live=dict(objects)
 put(SURFACE,0x513690);put(SURFACE+8,DD);put(SURFACE+20,height,width,pitch);put(SURFACE+48,PIXELS);put(DD,VT);put(VT+0x64,0x710000);put(VT+0x80,0x710004)
def compare(label,capture=False):
 global native,calls,snapshots,live,objects,free,record
 record=capture;trace.clear();native=True;ctx.images=C.pointer(images)if compose else C.POINTER(Globals)();ctx.fault=0;events.clear();oevents.clear();errors.clear();before=raw();initialLive=dict(live);initial=(dict(live),dict(objects),free[:]);out=U();ok=lib.claw_surface_transform_entry(0x4b99d0,SURFACE,None,0,C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,ctx.fault,errors);after=raw();ev=events[:];owned=(dict(live),dict(objects),free[:]);native=False;m.u.mem_write(BASE,before);live,objects,free=initial;m.call(0x4b99d0,SURFACE,max_instructions=10000000);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4,label;assert raw()==after,(label,'bytes');assert ev==oevents,(label,'events',len(ev),len(oevents));assert owned==(live,objects,free),(label,'ownership');native=True;C.memmove(C.addressof(heap),after,SIZE);calls+=1;snapshots+=1+len(ev)
 if capture:captures.append((before,after,initialLive,dict(objects),tuple(free),[(f,t,a)for f,t,a,_ in ev],(allocation,lockResult,restore,unlockResult,compose,mutate,alias),trace[:]))
