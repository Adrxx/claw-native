"""Unchanged original CString assignment; length/CRT heap/atomic transport explicit."""
import ctypes as C,hashlib,random,struct,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/cstring-assignment-agent';U=C.c_uint32
libs=[ROOT/'work'/p for p in('scene-lifecycle-agent/libSceneLifecycle.dylib','player-fade-blend-agent/libPlayerFadeBlendRuntime.dylib')]
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/CStringAssignmentRuntime.cpp'),*[str(p)for p in libs],'-o',str(WORK/'libCString.dylib')],check=True)
lib=C.CDLL(str(WORK/'libCString.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);ByteLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Array(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('compose','handler','fault','newMode','threshold','heap','heapAlloc')]
class Lifecycle(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('display','graphics','audio','palette','world','image')]+[('maximum',U),('fault',U)]
class Fade(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p)]+[(n,U)for n in('descriptorWord','descriptorToken','maximum','fault')]
class Blend(C.Structure):_fields_=[('fade',C.POINTER(Fade))]+[(n,U)for n in('temporary','empty','capture')]
class Context(C.Structure):_fields_=[('scene',Host),('lifecycle',C.POINTER(Lifecycle)),('allocation',C.POINTER(Blend)),('arrays',C.POINTER(Array)),('byteContext',C.c_void_p),('bytes',ByteLookup),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*4)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_cstring_assignment_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000;CELL,OTHER,INPUT,STORAGE,ALT,THREAD=BASE+0x1000,BASE+0x1100,BASE+0x2000,BASE+0x3000,BASE+0x4000,BASE+0x5000;ALLOC=BASE+0x10000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,0x1000);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();array=Array();lifecycle=Lifecycle();fade=Fade();blend=Blend();blend.fade=C.pointer(fade);ctx.lifecycle=C.pointer(lifecycle);ctx.allocation=C.pointer(blend);ctx.arrays=C.pointer(array)
native=True;cursor=ALLOC;objects={};live={};freed=[];events=[];oevents=[];errors=[];calls=snapshots=prefixes=0;ordinal=0;failedOrdinal=-1;mutation=0;captures=[];capture=False;replayEvents=[]
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n):
 if BASE<=t and uint(t)+n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if iBase<=t and uint(t)+n<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
def uint(v):return int(v)
def exact(t,n):
 if iBase<=t and t+n<=iEnd+1:return ptr(t,n)
 for p,size in objects.items():
  if((p<ALLOC and p not in(STORAGE,ALT))or p in live)and p<=t and t+n<=p+size:return ptr(t,n)
 return 0
@Lookup
def lookup(_,t,n):return exact(t,n*4)if not t%4 else 0
@ByteLookup
def bytesLookup(_,t,n):return exact(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);array.scene=lifecycle.scene=fade.scene=ctx.scene;ctx.bytes=bytesLookup;ctx.maximum=100000;array.compose=1;array.handler=0;ctx.byteContext=None

def read(t,n=4):return C.string_at(ptr(t,n),n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(ptr(t,len(b)),b,len(b))if native else m.u.mem_write(t,b)
def get(t):return struct.unpack('<I',read(t))[0]
def put(t,*v):write(t,pack(*v))
def text(t):
 out=bytearray()
 for i in range(65536):
  b=read(t+i,1)[0]
  if not b:return bytes(out)
  out.append(b)
 raise AssertionError('unterminated')
def raw():return (bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))+(C.string_at(ptr(0x510000,0x43000),0x43000)if native else bytes(m.u.mem_read(0x510000,0x43000)))
def state():return hashlib.sha256(raw()).digest(),tuple(sorted(live.items())),tuple(freed)
def effect(f,t,a):
 global cursor,ordinal
 if f==0x5469e4:
  length=len(text(a[0]))
  if mutation==1:put(CELL,ALT+12)
  if mutation==2:write(a[0],b'RENAMED\0')
  return length
 if f in(0x4a48e0,0x4f63ec):
  which=ordinal;ordinal+=1
  if mutation==3:write(INPUT,b'Changed\0')
  if which==failedOrdinal:return 0
  p=cursor;cursor+=(max(1,a[0])+3)&~3;assert cursor<BASE+SIZE;objects[p]=max(1,a[0]);live[p]=a[0];return p
 if f in(0x4a49b0,0x4f6428):
  freed.append(a[0]);live.pop(a[0],None)
  if mutation==4:put(0x52e1cc,ALT+12);put(0x52e1c8,ALT)
  if mutation==5:put(CELL,ALT+12)
  return 0x12345678
 if f==0x5022b5:return THREAD
 raise AssertionError(('service',hex(f),hex(t),a))
@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=tuple(q.arguments[:q.count]);events.append((q.function,q.receiver,a,state()));before=raw()if capture else None;activeBefore=dict(live)if capture else None;value=effect(q.function,q.receiver,a)&0xffffffff
  if capture:replayEvents.append((q.function,q.receiver,a,value,before,raw(),activeBefore,dict(live)))
  return value
 except Exception as e:
  import traceback
  errors.append((hex(q.function),traceback.format_exc()));ctx.fault=1;return 0
ABI={0x4a48e0:1,0x4a49b0:1,0x5022b5:0,0x710000:1,0x710004:1}
def hook(uc,f,size,user):
 if f not in ABI:return
 sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,ABI[f]));identity=0x5469e4 if f==0x710000 else f
 if f==0x710004:put(a[0],get(a[0])-1);value=get(a[0])
 else:oevents.append((identity,0,a,state()));value=effect(identity,0,a)
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+(4 if f in(0x710000,0x710004)else 0));uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def reset(seed=0,refs=1,capacity=32,content=b'old'):
 global native,cursor,objects,live,freed,ordinal,failedOrdinal,mutation
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=array.fault=lifecycle.fault=fade.fault=0;cursor=ALLOC;objects={CELL:4,OTHER:4,INPUT:256,STORAGE:12+capacity+1,ALT:45,THREAD:116};live={STORAGE:12+capacity+1,ALT:45};freed=[];ordinal=0;failedOrdinal=-1;mutation=0
 put(CELL,STORAGE+12);put(OTHER,STORAGE+12);put(STORAGE,refs,len(content),capacity);write(STORAGE+12,content+b'\0');put(ALT,1,3,32);write(ALT+12,b'alt\0');write(INPUT,b'NewValue\0');put(THREAD+40,0);put(0x510020,0);put(0x52e1c8,0x52e1b8);put(0x52e1cc,0x52e1c4);put(0x52e1b8,0xffffffff,0,0);write(0x52e1c4,b'\0');put(0x5469e4,0x710000);put(0x5469e8,0x710004);blend.empty=0x52e1c4

def compare(f,t,a,label,meaningful=True):
 global native,calls,snapshots,cursor,objects,live,freed,ordinal
 native=True;ctx.fault=array.fault=lifecycle.fault=fade.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(cursor,dict(objects),dict(live),freed[:],ordinal);args=(U*len(a))(*a);out=U();ok=lib.claw_cstring_assignment_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=events[:];owned=(cursor,dict(objects),dict(live),freed[:],ordinal);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,objects,live,freed,ordinal=old;actual=m.call(f,t,pack(*a),max_instructions=10000000);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4,(label,'SP')
 assert raw()==expected,(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 assert ev==oevents,(label,'events',[(x[:3],y[:3],x[3]==y[3])for x,y in zip(ev,oevents)if x!=y][:4],len(ev),len(oevents))
 if meaningful:assert out.value==actual,(label,'EAX',hex(out.value),hex(actual))
 assert owned==(cursor,objects,live,freed,ordinal),(label,'ownership')
 native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 if capture:captures.append((f,t,a,before,expected[:SIZE],bi,actual,meaningful,dict(objects),initialLive,list(replayEvents)))
 return out.value
prefixAddress=0;prefixExpectedEvents=0

def prefixHook(uc,address,size,user):
 if prefixAddress and address==prefixAddress and len(oevents)>=prefixExpectedEvents:uc.emu_stop()
m.u.hook_add(UC_HOOK_CODE,prefixHook)
def prefix(f,t,a,address,label):
 global native,cursor,objects,live,freed,ordinal,prefixAddress,prefixExpectedEvents,prefixes,snapshots
 native=True;ctx.fault=array.fault=lifecycle.fault=fade.fault=0;events.clear();oevents.clear();errors.clear();before=bytes(heap);bi=bytes(image);old=(cursor,dict(objects),dict(live),freed[:],ordinal);args=(U*len(a))(*a);out=U();ok=lib.claw_cstring_assignment_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault in(1,2)and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=events[:];owned=(cursor,dict(objects),dict(live),freed[:],ordinal);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,objects,live,freed,ordinal=old;prefixExpectedEvents=len(ev);prefixAddress=address;m.write_words(m.stack,[m.stop,*a]);m.u.reg_write(UC_X86_REG_ECX,t);m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.emu_start(f,m.stop,count=1000000);assert m.u.reg_read(UC_X86_REG_EIP)==address,(label,hex(m.u.reg_read(UC_X86_REG_EIP)));prefixAddress=0;assert raw()==expected,(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8]);assert ev==oevents,(label,'events');assert owned==(cursor,objects,live,freed,ordinal),(label,'ownership');native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);prefixes+=1;snapshots+=len(ev)+1
