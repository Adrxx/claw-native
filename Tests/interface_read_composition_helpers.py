"""Original IFC whole-call oracle with explicit physical image/path/CRT services."""
import ctypes as C,struct,hashlib,random,json,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/interface-read-composition-agent';U=C.c_uint32
sources=['InterfaceReadCompositionRuntime','InterfaceFileRuntime','CArrayRuntime','ActorDestruction']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in sources],'-o',str(WORK/'libInterface.dylib')],check=True)
lib=C.CDLL(str(WORK/'libInterface.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Context(C.Structure):_fields_=[('scene',Host),('arrays',C.c_void_p),('strings',C.c_void_p),('destruction',C.c_void_p)]+[(n,U)for n in('file','archive','scratch','maximum','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*10),('mask',U),('bufferCount',U),('buffers',C.c_void_p*3),('sizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_interface_read_composition_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x400000;MENU=BASE+0x100;DATA=BASE+0x1000;GRAPHICS=BASE+0x5000;VT=BASE+0x6000;IMAGE=BASE+0x7000;FILE=BASE+0x8000;ARCHIVE=BASE+0x8100;SCRATCH=BASE+0x8200;ALLOC=BASE+0x10000;TEB,GDT=0x10ed000,0x10ee000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.stack=0x200e000;m.u.mem_map(BASE,SIZE);m.u.mem_map(0x710000,4096);m.executed.clear();heap=(C.c_uint8*SIZE)();iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();events=[];oevents=[];errors=[];native=True;cursor=ALLOC;fileAlias=archiveAlias=0;originalLocal=[];calls=snapshots=0;allocations={};allocIndex=0;allocFailure=0;resolverCalls=0;resolverFailAt=0;sourceNames=[];nativeNames=[];localSeeds={};currentFunction=0;sourceFileFinal=sourceArchiveFinal=None;sourceStopped=False;capture=False;corpus=[];replays=[];freed=[];unsafeCases=[];now=123456;cursorPoint=(320,240)
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if iBase<=t and t+n*4<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);ctx.file=FILE;ctx.archive=ARCHIVE;ctx.scratch=SCRATCH;ctx.maximum=2000000
for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):m.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.write_words(TEB,[0xdeadbeef])
def get(t):return struct.unpack('<I',read(t,4))[0]
def put(t,v):write(t,pack(*v))
def read(t,n):return C.string_at(ptr(t&~3)+(t&3),n)if native else bytes(m.u.mem_read(t,n))
def write(t,b):C.memmove(ptr(t&~3)+(t&3),b,len(b))if native else m.u.mem_write(t,b)
def text(t):
 b=bytearray()
 while True:
  c=read(t,1)[0];t+=1
  if not c:return bytes(b)
  b.append(c)
def raw():
 b=bytearray(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))
 # Caller-owned automatic aliases are normalized separately; no native claim
 # that original stack constructors allocated persistent objects in this heap.
 b[SCRATCH-BASE:SCRATCH-BASE+4]=bytes(4)
 if currentFunction in(0x4dcdf0,0x4dcd10):
  for t,n in((FILE,40),(ARCHIVE,68)):b[t-BASE:t-BASE+n]=bytes(n)
 return bytes(b)+(C.string_at(ptr(0x520000),0x30000)if native else bytes(m.u.mem_read(0x520000,0x30000)))
def automatic():
 if currentFunction not in(0x4dcdf0,0x4dcd10):return ()
 if native:return (read(FILE,40),read(ARCHIVE,68))
 file=bytes(m.u.mem_read(fileAlias,40))if fileAlias else localSeeds[FILE];archive=bytearray(m.u.mem_read(archiveAlias,68))if archiveAlias else bytearray(localSeeds[ARCHIVE])
 if archiveAlias and struct.unpack_from('<I',archive,32)[0]==fileAlias:struct.pack_into('<I',archive,32,FILE)
 return file,bytes(archive)
def snap():return hashlib.sha256(raw()).digest()
def differences(before,after):
 changes=[]
 def walk(start,end):
  if before[start:end]==after[start:end]:return
  if end-start<=32:
   changes.extend((i,after[i])for i in range(start,end)if before[i]!=after[i]);return
  middle=(start+end)//2;walk(start,middle);walk(middle,end)
 walk(0,len(before));return changes
def effect(f,t,a,buffers):
 global cursor,allocIndex,resolverCalls
 if f==0x4f63ec:
  allocIndex+=1
  if allocIndex==allocFailure:return 0
  p=cursor;cursor+=(max(1,a[0])+3)&~3;assert cursor<BASE+SIZE
  if native:allocations[p]=max(1,a[0])
  return p
 if f==0x4f6428:freed.append(a[0]);return 0
 if f==0x4fc139:
  # CFile physical filename/stat endpoint, profile empty filename.
  if native:C.memmove(buffers[1],pack(0x52e1c4),4)
  else:m.u.mem_write(buffers[1],pack(0x52e1c4))
  return 0 # original void caller ignores object-pointer result.
 if f==0x710000:
  data=a[0];n=text(data);resolverCalls+=1
  (nativeNames if native else sourceNames).append(n)
  if data!=0x52e1c4:put(data-12,[get(data-12)-1])
  return IMAGE if n and resolverCalls!=resolverFailAt else 0
 if f==0x710010:return now
 if f==0x710014:
  (C.memmove if native else m.u.mem_write)(buffers[0],pack(*cursorPoint),8)if native else m.u.mem_write(buffers[0],pack(*cursorPoint))
  return 1
 if f==0x710018:
  b=C.string_at(buffers[0],16)if native else bytes(m.u.mem_read(buffers[0],16));l,t,r,b=struct.unpack('<4i',b);x,y=(struct.unpack('<i',pack(v))[0]for v in a[1:]);return int(l<=x<r and t<=y<b)
 if f in(0x4b9ce0,0x71001c,0x4bc4f0):return 0
 if f==0x4fe675:return 0
 raise AssertionError(('service',hex(f),hex(t),a))
@Dep
def dep(c,qp,u):
 try:
  q=qp.contents;a=list(q.arguments[:q.count]);buffers=list(q.buffers[:q.bufferCount]);before=raw();ev=(q.function,q.receiver,tuple(a),q.mask,tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)),snap(),automatic());events.append(ev);value=effect(q.function,q.receiver,a,buffers)
  if capture:replays.append((q.function,q.receiver,tuple(a),q.mask,tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)),ev[4],ev[5],value,differences(before,raw())))
  return value
 except Exception as e:errors.append(e);return 0

def ret(pop,value=0):sp=m.u.reg_read(UC_X86_REG_ESP);m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop);m.u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
def hook(u,f,size,user):
 global fileAlias,archiveAlias,sourceFileFinal,sourceArchiveFinal,sourceStopped
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX)
 if f in(0x4dcd97,0x4dcdd2):sourceArchiveFinal=automatic()[1]
 if f==0x4dce77:sourceFileFinal=automatic()[0]
 if f==0x4ff5f9:fileAlias=t;u.mem_write(t,localSeeds[FILE])
 if f==0x4fda33:archiveAlias=t;u.mem_write(t,localSeeds[ARCHIVE])
 if f==0x4ddc4d:u.mem_write(u.reg_read(UC_X86_REG_EAX),bytes(8))
 if f==0x710004:ret(4,len(text(m.read_words(sp+4,1)[0])));return
 if f in(0x710008,0x71000c):
  p=m.read_words(sp+4,1)[0];v=(get(p)+(1 if f==0x710008 else -1))&0xffffffff;put(p,[v]);ret(4,v);return
 n={0x4f63ec:1,0x4f6428:1,0x4fc139:1,0x710000:1,0x710010:0,0x710014:1,0x710018:3,0x71001c:2,0x4b9ce0:5,0x4fe675:2,0x4bc4f0:1}.get(f)
 if n is None:return
 a=list(m.read_words(sp+4,n));receiver=t if f in(0x4fc139,0x4bc4f0)else 0;mask=0;buf=[];sizes=[]
 if f==0x710014:mask=1;buf=[a[0]];sizes=[8];a[0]=0
 if f==0x710018:mask=1;buf=[a[0]];sizes=[16];a[0]=0
 if f==0x4b9ce0:receiver=t;mask=5;buf=[a[0],a[2]];sizes=[16,16];a[0]=a[2]=0
 if f==0x4fc139:mask=257;buf=[receiver,a[0]];sizes=[40,4];receiver=0;a[0]=0
 oevents.append((f,receiver,tuple(a),mask,tuple(bytes(u.mem_read(p,n))for p,n in zip(buf,sizes)),snap(),automatic()));value=effect(f,receiver,a,buf)
 if f==0x4fe675:sourceStopped=True;u.emu_stop();return
 ret({0x4fc139:4,0x710014:4,0x710018:12,0x71001c:8,0x4b9ce0:20,0x4bc4f0:4}.get(f,0),value)
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0,filename='CLAW.IFC'):
 global native,cursor,allocIndex,allocFailure,resolverCalls,resolverFailAt,fileAlias,archiveAlias,sourceNames,nativeNames,allocations
 native=True;C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));ctx.fault=0;cursor=ALLOC;allocIndex=allocFailure=resolverCalls=resolverFailAt=0;fileAlias=archiveAlias=0;sourceNames=[];nativeNames=[];localSeeds={};currentFunction=0;sourceFileFinal=sourceArchiveFinal=None;allocations={MENU:256,DATA:16384,GRAPHICS:64,VT:160,IMAGE:188,FILE:40,ARCHIVE:68,SCRATCH:4};put(GRAPHICS,[VT]);put(VT,[0]*40);put(IMAGE+20,[20,30]);put(0x5469e4,[0x710004]);put(0x5469ec,[0x710008]);put(0x5469e8,[0x71000c]);put(0x546a24,[0x710010]);put(0x546cd0,[0x710014]);put(0x546cd4,[0x710018]);data=(ROOT/f'Original/retail-assets/STATES/MENU/{filename}').read_bytes();write(DATA,data);allocations[DATA]=len(data);return len(data)

def compare(f,t,args,label,void=False,unsafe=False):
 global native,cursor,allocIndex,resolverCalls,calls,snapshots,localSeeds,currentFunction,sourceFileFinal,sourceArchiveFinal,sourceStopped
 currentFunction=f;sourceStopped=False;sourceFileFinal=sourceArchiveFinal=None;native=True;ctx.fault=0;events.clear();oevents.clear();errors.clear();replays.clear();freed.clear();before=bytes(heap);bi=bytes(image);localSeeds={t:before[t-BASE:t-BASE+n]for t,n in((FILE,40),(ARCHIVE,68))};old=(cursor,allocIndex,resolverCalls);a=(U*len(args))(*args);out=U();ok=lib.claw_interface_read_composition_entry(f,t,a,len(args),C.byref(ctx),dep,None,C.byref(out));assert (not ok and ctx.fault in(1,2))if unsafe else(ok and not ctx.fault and not errors),(label,'native',ctx.fault,errors);expected=raw();ev=list(events);owned=(cursor,allocIndex,resolverCalls);dead=list(freed);freed.clear();native=False;m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);cursor,allocIndex,resolverCalls=old;actual=0
 try:actual=m.call(f,t,pack(*args),max_instructions=10000000)
 except UcError:
  assert unsafe,(label,'unexpected original fault',hex(m.u.reg_read(UC_X86_REG_EIP)))
 except AssertionError:
  assert unsafe and sourceStopped,(label,'unexpected source bound/assertion',hex(m.u.reg_read(UC_X86_REG_EIP)))
 else:assert unsafe==sourceStopped,(label,'source completion',sourceStopped)
 if unsafe:unsafeCases.append(dict(function=hex(f),label=label,address=hex(m.u.reg_read(UC_X86_REG_EIP)),fault=int(ctx.fault),events=len(ev)))
 if not unsafe:assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+4*len(args),(label,'SP')
 if raw()!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:20]))
 if ev!=oevents:raise AssertionError((label,'events',len(ev),len(oevents),next(((i,x[:5],y[:5],x[5]==y[5])for i,(x,y)in enumerate(zip(ev,oevents))if x!=y),None)))
 if f==0x4dcdf0 and not unsafe:
  assert C.string_at(ptr(FILE),40)==sourceFileFinal,(label,'fileAutomaticFinal')
  assert C.string_at(ptr(ARCHIVE),68)==sourceArchiveFinal,(label,'archiveAutomaticFinal',struct.unpack('<17I',read(ARCHIVE,68)),struct.unpack('<17I',sourceArchiveFinal))
 if not void and not unsafe:assert actual==out.value,(label,'EAX',hex(actual),hex(out.value))
 assert owned==(cursor,allocIndex,resolverCalls)and dead==freed,(label,'services');native=True;calls+=1;snapshots+=len(ev)+1
 if capture and not unsafe:corpus.append((f,t,args,label,out.value,not void,before,bi[0x520000-iBase:0x550000-iBase],raw(),dict(allocations),list(replays),read(FILE,40),read(ARCHIVE,68)))
 return out.value
