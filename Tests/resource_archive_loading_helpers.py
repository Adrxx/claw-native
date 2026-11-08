"""Source resource lifecycle oracle; physical CRT/stdio are explicit services."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/resource-archive-loading-agent';U=C.c_uint32
sources=['ResourceArchiveLoadingRuntime','ResourceTableConstructionRuntime','ResourceNamespaceRuntime','ResourceDataRuntime','AudioPCMTransfer','AudioResourceRuntime','CArrayRuntime','AmbientAudioBackendRuntime','AudioEvents']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in sources],'-o',str(WORK/'libData.dylib')],check=True)
lib=C.CDLL(str(WORK/'libData.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Array(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('compose','handler','fault','newMode','threshold','heap','heapAlloc')]
class Context(C.Structure):_fields_=[('scene',Host),('allocator',C.POINTER(Array)),('maximum',U),('fault',U),('byteContext',C.c_void_p),('bytes',C.c_void_p)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*10),('mask',U),('bufferCount',U),('buffers',C.c_void_p*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_resource_table_construction_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000;RESOURCE,OWNER,OWNER2,STREAM,STREAM2,VT,TYPE,NAME,META,AUX=[BASE+0x100+i*0x100 for i in range(10)];ALLOC=BASE+0x10000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,0x1000);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
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
def raw():return (bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))+(C.string_at(ptr(0x510000),0x43000)if native else bytes(m.u.mem_read(0x510000,0x43000)))
def snap():return hashlib.sha256(raw()).digest()
CONTROL=OWNER;FOLDER=BASE+0x1000;OBJECT=BASE+0x1100;MAP=BASE+0x1200;NODE=BASE+0x1300
ordinal=0;failedOrdinal=-1;timeValue=1712345678;mutate=0;mutationTarget=0;timeLocal=0;allocations=[];live={};freed=[];captures=[];capture=False
assert hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest()=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
def state():return snap(),tuple(allocations),tuple(freed),tuple(sorted(live.items()))
def effect(f,t,a,local=None):
 global cursor,ordinal
 if f in(0x4f63ec,0x4a48e0):
  which=ordinal;ordinal+=1
  if mutate==1 and mutationTarget:write(mutationTarget,b'ChangedName\0')
  if mutate==2 and mutationTarget:put(mutationTarget,[CONTROL+0x80])
  if which==failedOrdinal:allocations.append((0,a[0]));return 0
  value=cursor;cursor+=(max(1,a[0])+3)&~3;assert cursor<BASE+SIZE;objects[value]=max(1,a[0]);live[value]=a[0];allocations.append((value,a[0]));return value
 if f in(0x4f6428,0x4a49b0):freed.append(a[0]);live.pop(a[0],None);return 0x12345678
 if f==0x4a3b10:
  if local is not None:local.value=timeValue
  if mutate==3 and mutationTarget:put(mutationTarget,[CONTROL+0x80])
  return timeValue
 if f==0x710000:
  if mutationTarget:put(mutationTarget,[MAP])
  return mutate
 raise AssertionError(('service',hex(f),hex(t),a))
@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=list(q.arguments[:q.count]);locals_=tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount));events.append((q.function,q.receiver,tuple(a),q.mask,locals_,state()))
  before=raw();local=U.from_address(q.buffers[0])if q.function==0x4a3b10 else None;value=effect(q.function,q.receiver,a,local)
  if capture:replayEvents.append((q.function,q.receiver,a,value,before,raw(),q.mask,locals_,tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount))))
  return value
 except Exception as e:errors.append(e);return 0
ABI={0x4f63ec:1,0x4f6428:1,0x4a48e0:1,0x4a49b0:1,0x4a3b10:1,0x710000:0}
def hook(uc,f,size,user):
 if f not in ABI:return
 if bool(ctx.allocator)and f in(0x4f63ec,0x4f6428):return
 sp=uc.reg_read(UC_X86_REG_ESP);a=list(m.read_words(sp+4,ABI[f]));t=uc.reg_read(UC_X86_REG_ECX)if f==0x710000 else 0
 mask=1 if f==0x4a3b10 else 0;locals_=(bytes(uc.mem_read(a[0],4)),)if mask else();normalized=[0]if mask else a;oevents.append((f,t,tuple(normalized),mask,locals_,state()));value=effect(f,t,normalized)
 if mask:uc.mem_write(a[0],pack(value))
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
serviceHook=m.u.hook_add(UC_HOOK_CODE,hook)
def reset(seed=0):
 global native,cursor,mutate,mutationTarget,failedOrdinal,ordinal,freed,allocations,live,objects,timeValue
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=0;ctx.allocator=C.POINTER(Array)();array.fault=0;cursor=ALLOC;mutate=0;mutationTarget=0;failedOrdinal=-1;ordinal=0;freed=[];allocations=[];live={};timeValue=1712345678;objects={FOLDER:76,CONTROL:72,OBJECT:44,MAP:8,NODE:24,NAME:128,META:128,VT:4}
 put(CONTROL+56,[0,0]);put(CONTROL+0x80+56,[0,0]);write(NAME,b'Root\0');write(META,b'child\0');put(0x540e88,[0]);put(0x510020,[0]);array.compose=1;array.handler=0;put(VT,[0x710000])
def compare(f,t,a,label,meaningful=True):
 global native,calls,snapshots,cursor,ordinal,freed,allocations,live,objects
 native=True;ctx.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);bi=bytes(image);initialLive=dict(live);old=(cursor,ordinal,freed[:],allocations[:],dict(live),dict(objects));args=(U*len(a))(*a);out=U();ok=lib.claw_resource_table_construction_entry(f,t,args,len(a),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=list(events);owned=(cursor,ordinal,freed[:],allocations[:],dict(live),dict(objects));native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,ordinal,freed,allocations,live,objects=old;actual=m.call(f,t,pack(*a),max_instructions=20000000);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+4*len(a),(label,'SP')
 assert raw()==expected,(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 if ev!=oevents:
  for i,(x,y)in enumerate(zip(ev,oevents)):
   if x!=y:print(label,'event',i,x[:5],y[:5],x[5]==y[5]);break
  raise AssertionError((label,'events',len(ev),len(oevents)))
 if meaningful:assert actual==out.value,(label,'EAX',hex(actual),hex(out.value))
 assert owned==(cursor,ordinal,freed,allocations,live,objects),(label,'serviceState')
 native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 if capture and f in(0x4b6600,0x4b69a0,0x4b6a60,0x4b66d0):captures.append((f,t,a,before,bytes(heap),bi,actual,dict(objects),list(replayEvents),initialLive))
 return out.value

class ArchiveContext(C.Structure):_fields_=[('table',C.POINTER(Context)),('headerToken',U),('maximum',U)]
HEADER=BASE+0x4000;FILEHANDLE=0x4567890;archive=ArchiveContext(C.pointer(ctx),HEADER,1000000)
lib.claw_resource_archive_loading_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(ArchiveContext),Dep,C.c_void_p,C.POINTER(U)]
rez=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(rez).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
baseReset=reset;baseEffect=effect;originalCompare=compare
fileData=rez;allowed=None;position=0;openResults=[];seekResults=[];readResults=[];closeResults=[];flushResults=[];retryResults=[];headerAlias=0;originalHeaderSeed=bytes(168)

def raw():
 b=bytearray(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)));b[HEADER-BASE:HEADER-BASE+168]=bytes(168)
 return bytes(b)+(C.string_at(ptr(0x510000),0x43000)if native else bytes(m.u.mem_read(0x510000,0x43000)))

def effect(f,t,a,local=None):
 global position
 if f==0x4f1d90:return openResults.pop(0)if openResults else FILEHANDLE
 if f==0x4a7840:position=a[1];return seekResults.pop(0)if seekResults else 0
 if f==0x4a7260:
  count=a[2];value=readResults.pop(0)if readResults else(count if allowed is None or(position,count)in allowed else 0);value=min(value,count,len(fileData)-position);data=fileData[position:position+value];position+=value
  if local is not None:C.memmove(local,data,len(data))
  else:write(a[0],data)
  return value
 if f==0x4a7ae0:return closeResults.pop(0)if closeResults else 0
 if f==0x4a7920:return flushResults.pop(0)if flushResults else 0
 if f in(0x4b7550,0x4b76b0):return 0 #Explicit unported writer/compactor test transport, not recovered.
 if f==0x710000:return retryResults.pop(0)if retryResults else 0
 return baseEffect(f,t,a,local)

@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=list(q.arguments[:q.count]);locals_=tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount));events.append((q.function,q.receiver,tuple(a),q.mask,locals_,state()));before=raw();local=U.from_address(q.buffers[0])if q.function==0x4a3b10 else q.buffers[0]if q.function==0x4a7260 and q.bufferCount else None;v=effect(q.function,q.receiver,a,local)
  if capture:replayEvents.append((q.function,q.receiver,a,v,before,raw(),q.mask,locals_,tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount))))
  return v
 except Exception as e:errors.append(e);return 0
ABI.update({0x4f1d90:2,0x4a7840:3,0x4a7260:4,0x4a7ae0:1,0x4a7920:1,0x4b7550:0,0x4b76b0:0})
#Replace inherited service hook; keep unchanged normal source42a680 retry.
for handle in list(m.u._hook_handles)if False else():pass
#The base helper hook registration is given an owned handle below.
m.u.hook_del(serviceHook)
def archiveHook(uc,f,size,user):
 global headerAlias
 if f==0x4b72e0:
  headerAlias=uc.reg_read(UC_X86_REG_ESP)-184;uc.mem_write(headerAlias,originalHeaderSeed)
 if f==0x42a680:oevents.append((f,uc.reg_read(UC_X86_REG_ECX),(),0,(),state()))
 if f not in ABI:return
 if bool(ctx.allocator)and f in(0x4f63ec,0x4f6428):return
 sp=uc.reg_read(UC_X86_REG_ESP);a=list(m.read_words(sp+4,ABI[f]));t=uc.reg_read(UC_X86_REG_ECX)if f in(0x710000,0x4b7550,0x4b76b0)else 0;mask=0;locals_=();normalized=a[:]
 if f==0x4a3b10:mask=1;locals_=(bytes(uc.mem_read(a[0],4)),);normalized=[0]
 if f==0x4a7260 and a[0]==headerAlias:mask=1;locals_=(bytes(uc.mem_read(a[0],168)),);normalized[0]=0
 oevents.append((f,t,tuple(normalized),mask,locals_,state()));value=effect(f,t,a)
 if f==0x4a3b10:uc.mem_write(a[0],pack(value))
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+(ABI[f]*4 if f in(0x710000,0x4b7550,0x4b76b0)else 0));uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,archiveHook)
priorEffect=effect
def effect(f,t,a,local=None):
 if f==0x42a680:return 0 #Existing recovered literal XOR EAX/RET leaf.
 return priorEffect(f,t,a,local)
def reset(seed=0):
 global fileData,allowed,position,openResults,seekResults,readResults,closeResults,flushResults,retryResults,headerAlias
 baseReset(seed);fileData=rez;allowed=None;position=0;openResults=[];seekResults=[];readResults=[];closeResults=[];flushResults=[];retryResults=[];headerAlias=0;objects[HEADER]=168;write(NAME,b'CLAW.REZ\0')

def invoke(f,t,a,common=False):
 args=(U*len(a))(*a);out=U();fn=lib.claw_resource_table_construction_entry if common else lib.claw_resource_archive_loading_entry;context=ctx if common else archive;ok=fn(f,t,args,len(a),C.byref(context),dep,None,C.byref(out));return ok,out.value

def compare(f,t,a,label,meaningful=True,common=False):
 global native,calls,snapshots,cursor,ordinal,freed,allocations,live,objects,position,openResults,seekResults,readResults,closeResults,flushResults,retryResults,originalHeaderSeed
 native=True;ctx.fault=0;events.clear();oevents.clear();errors.clear();replayEvents.clear();before=bytes(heap);originalHeaderSeed=before[HEADER-BASE:HEADER-BASE+168];bi=bytes(image);initialLive=dict(live);old=(cursor,ordinal,freed[:],allocations[:],dict(live),dict(objects),position,openResults[:],seekResults[:],readResults[:],closeResults[:],flushResults[:],retryResults[:]);ok,out=invoke(f,t,a,common);assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw();ev=events[:];owned=(cursor,ordinal,freed[:],allocations[:],dict(live),dict(objects),position,openResults[:],seekResults[:],readResults[:],closeResults[:],flushResults[:],retryResults[:]);native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,ordinal,freed,allocations,live,objects,position,openResults,seekResults,readResults,closeResults,flushResults,retryResults=old;actual=m.call(f,t,pack(*a),max_instructions=40000000);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4,(label,'SP')
 assert raw()==expected,(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:8])
 if ev!=oevents:
  for i,(x,y)in enumerate(zip(ev,oevents)):
   if x!=y:print(label,'event',i,x[:5],y[:5],x[5]==y[5]);break
  raise AssertionError((label,'events',len(ev),len(oevents)))
 if meaningful:assert actual==out,(label,'EAX',hex(actual),hex(out))
 assert owned==(cursor,ordinal,freed,allocations,live,objects,position,openResults,seekResults,readResults,closeResults,flushResults,retryResults),(label,'transportState')
 native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x510000-iBase,expected[SIZE:],0x43000);calls+=1;snapshots+=len(ev)+1
 if capture and not common:captures.append((f,t,a,before,bytes(heap),bi,actual,meaningful,dict(objects),list(replayEvents),initialLive))
 return out
prefixAddress=0;prefixObservedEvents=0;prefixes=0
def prefixHook(uc,address,size,user):
 if prefixAddress and address==prefixAddress and len(oevents)>=prefixObservedEvents:uc.emu_stop()
m.u.hook_add(UC_HOOK_CODE,prefixHook)
def comparePrefix(f,t,a,label,address):
 global native,prefixAddress,prefixObservedEvents,prefixes,cursor,ordinal,freed,allocations,live,objects,snapshots,position,openResults,seekResults,readResults,closeResults,flushResults,retryResults,originalHeaderSeed
 native=True;ctx.fault=0;events.clear();oevents.clear();errors.clear();before=bytes(heap);originalHeaderSeed=before[HEADER-BASE:HEADER-BASE+168];bi=bytes(image);old=(cursor,ordinal,freed[:],allocations[:],dict(live),dict(objects),position,openResults[:],seekResults[:],readResults[:],closeResults[:],flushResults[:],retryResults[:]);ok,out=invoke(f,t,a);assert not ok and ctx.fault==1 and not errors,(label,ctx.fault,errors);expected=raw();ev=events[:];native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,ordinal,freed,allocations,live,objects,position,openResults,seekResults,readResults,closeResults,flushResults,retryResults=old;prefixObservedEvents=len(ev);prefixAddress=address;m.u.mem_write(m.stack,pack(m.stop,*a));m.u.reg_write(UC_X86_REG_ECX,t);m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.emu_start(f,m.stop,count=40000000);assert m.u.reg_read(UC_X86_REG_EIP)==address,(label,hex(m.u.reg_read(UC_X86_REG_EIP)));prefixAddress=0;assert raw()==expected,(label,'heap');assert oevents==ev,(label,'events');native=True;C.memmove(C.addressof(heap),expected[:SIZE],SIZE);prefixes+=1;snapshots+=len(ev)+1
