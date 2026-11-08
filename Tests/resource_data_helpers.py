"""Source resource lifecycle oracle; physical CRT/stdio are explicit services."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/resource-data-agent';U=C.c_uint32
sources=['ResourceDataRuntime','AudioPCMTransfer','AudioResourceRuntime','CArrayRuntime']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in sources],'-o',str(WORK/'libData.dylib')],check=True)
lib=C.CDLL(str(WORK/'libData.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Array(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('compose','handler','fault','newMode','threshold','heap','heapAlloc')]
class Context(C.Structure):_fields_=[('scene',Host),('allocator',C.POINTER(Array)),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*10)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_resource_data_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000;RESOURCE,OWNER,OWNER2,STREAM,STREAM2,VT,TYPE,NAME,META,AUX=[BASE+0x100+i*0x100 for i in range(10)];ALLOC=BASE+0x10000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,0x1000);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();array=Array();cursor=ALLOC;events=[];oevents=[];errors=[];native=True;calls=snapshots=0;mutation='';allocFail=False;seekResults=[];readResults=[];retryResults=[];freed=[];payload=b'';objects={};capture=False;replays=[];replayEvents=[]
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if iBase<=t and t+n*4<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);ctx.maximum=100000;array.scene=ctx.scene;array.handler=0;array.compose=1

def read(t,n=4):return C.string_at(ptr(t&~3)+(t&3),n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(ptr(t&~3)+(t&3),b,len(b))if native else m.u.mem_write(t,b)
def put(t,v):write(t,pack(*v))
def get(t):return struct.unpack('<I',read(t))[0]
def raw():return (bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))+(C.string_at(ptr(0x540000),0x10000)if native else bytes(m.u.mem_read(0x540000,0x10000)))
def snap():return hashlib.sha256(raw()).digest()
def effect(f,t,a):
 global cursor
 if f in(0x4f63ec,0x4a48e0):
  if mutation=='owner':put(RESOURCE+36,[OWNER2])
  if mutation=='nullOwner':put(RESOURCE+36,[0])
  if mutation=='length':put(RESOURCE+20,[16])
  if allocFail:return 0
  value=cursor;cursor+=(max(1,a[0])+3)&~3;assert cursor<BASE+SIZE
  if native:objects[value]=(max(1,a[0])+3)&~3
  return value
 if f==0x5022b5:return AUX
 if f in(0x4f6428,0x4a49b0):freed.append(a[0]);return 0x12345678
 if f==0x4a7840:return seekResults.pop(0)if seekResults else 0
 if f==0x4a7260:
  result=readResults.pop(0)if readResults else a[2];count=min(result,a[2]);data=payload[:count]if payload else bytes((a[3]+i)&255 for i in range(count));write(a[0],data)
  if mutation=='cache':put(RESOURCE+24,[AUX])
  return result
 if f==0x710000:
  put(STREAM+12,[99]);return retryResults.pop(0)if retryResults else 0
 raise AssertionError(('service',hex(f),hex(t),a))
@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=list(q.arguments[:q.count]);before=raw();events.append((q.function,q.receiver,tuple(a),hashlib.sha256(before).digest()));value=effect(q.function,q.receiver,a)
  if capture:replayEvents.append((q.function,q.receiver,a,value,before,raw()))
  return value
 except Exception as e:errors.append(e);return 0
ABI={0x4f63ec:1,0x4f6428:1,0x4a48e0:1,0x4a49b0:1,0x4a7840:3,0x4a7260:4,0x710000:0,0x5022b5:0}

def hook(uc,f,size,user):
 if f not in ABI:return
 if bool(ctx.allocator)and f in(0x4f63ec,0x4f6428):return
 sp=uc.reg_read(UC_X86_REG_ESP);n=ABI[f];a=list(m.read_words(sp+4,n));t=uc.reg_read(UC_X86_REG_ECX)if f==0x710000 else 0;oevents.append((f,t,tuple(a),snap()));value=effect(f,t,a);uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)

def reset(seed=0,length=64):
 global native,cursor,mutation,allocFail,seekResults,readResults,retryResults,freed,payload,objects
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=0;ctx.allocator=C.POINTER(Array)();array.fault=0;cursor=ALLOC;mutation='';allocFail=False;seekResults=[];readResults=[];retryResults=[];freed=[];payload=b'';objects={RESOURCE:96,OWNER:76,OWNER2:76,STREAM:44,STREAM2:44,VT:12,TYPE:44,NAME:256,META:256,AUX:256}
 put(RESOURCE,[0]*24);put(RESOURCE+8,[TYPE]);put(RESOURCE+20,[length]);put(RESOURCE+36,[OWNER]);put(RESOURCE+40,[1234]);put(OWNER,[0]*19);put(OWNER+24,[STREAM]);put(OWNER2,[0]*19);put(OWNER2+24,[STREAM2]);put(STREAM,[VT,0,0,17]);put(STREAM2,[VT,0,0,43]);put(VT+8,[0x710000]);put(TYPE,[0x504944]);put(0x510020,[0]);put(AUX+40,[0]);write(NAME,b'FRAME001\0');write(META,b'fixture\0')

def compare(f,t,a,label,allowDifference=False):
 global native,calls,snapshots,cursor,seekResults,readResults,retryResults,freed
 native=True;ctx.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);bi=bytes(image);old=(cursor,seekResults[:],readResults[:],retryResults[:],freed[:]);args=(U*len(a))(*a);out=U();ok=lib.claw_resource_data_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=list(events);owned=(cursor,seekResults[:],readResults[:],retryResults[:],freed[:]);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,seekResults,readResults,retryResults,freed=old;actual=m.call(f,t,pack(*a));assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+4*len(a),(label,'SP')
 equal=raw()==expected and ev==oevents and actual==out.value
 if allowDifference:
  report={'label':label,'equal':equal,'nativeEvents':[list(x[:3])for x in ev],'originalEvents':[list(x[:3])for x in oevents]};(WORK/'owner-reload-before-fix.json').write_text(json.dumps(report,indent=2));print(report,flush=True);return equal
 assert raw()==expected,(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:5]);assert ev==oevents,(label,'events',ev,oevents);assert actual==out.value,(label,'EAX',hex(actual),hex(out.value));assert owned==(cursor,seekResults,readResults,retryResults,freed),(label,'serviceState');native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x540000-iBase,expected[SIZE:],0x10000);calls+=1;snapshots+=len(ev)+1
 if capture:replays.append((f,t,a,before,bytes(heap),bi,actual,dict(objects),list(replayEvents),bool(ctx.allocator)))
 return actual
