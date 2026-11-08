"""Whole original surface blit wrappers; physical endpoints are declared fixtures."""
import ctypes as C,hashlib,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/surface-blit-agent';WORK.mkdir(parents=True,exist_ok=True)
NAMES=['SurfaceBlitRuntime','PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in NAMES],'-o',str(WORK/'libSurfaceBlit.dylib')],check=True)
U=C.c_uint32
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Args(C.Structure):_fields_=[('words',U*5),('count',U),('destination',C.POINTER(U)),('source',C.POINTER(U))]
class Context(C.Structure):_fields_=[('scene',Host),('pcx',C.c_void_p),('image',C.c_void_p),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('mask',U),('bufferCount',U),('buffers',C.POINTER(U)*2),('sizes',U*2)]
class PCX(C.Structure):_fields_=[('scene',Host),('byteContext',C.c_void_p),('bytes',C.c_void_p),('image',C.c_void_p),('composeImage',U),('maximum',U),('fault',U)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x10000;IMAGE_START,IMAGE_SIZE=0x500000,0x48000
DST,SRC,DD,DD2,SD,SD2,DVT,DVT2,SVT,SVT2,DR,SR,PAIR,FX,DP,SP=[BASE+x for x in(0x1000,0x2000,0x3000,0x3100,0x3200,0x3300,0x4000,0x4100,0x4200,0x4300,0x5000,0x5100,0x5200,0x5300,0x6000,0x7000)]
OBJECTS=[(DST,188),(SRC,188),*[(t,4)for t in(DD,DD2,SD,SD2)],*[(t,120)for t in(DVT,DVT2,SVT,SVT2)],(DR,16),(SR,16),(PAIR,8),(FX,100),(DP,192),(SP,48)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x700000,0x1000);m.executed.clear()
imageSeed=bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE));heap=(C.c_uint8*SIZE)();image=(C.c_uint8*IMAGE_SIZE)()
native=True;events=[];originalEvents=[];errors=[];sequence=[];index=0;restoreValue=1;restoreCallback=0x7000b4;mutate=False;localMask=0;capture=False;corpus=[];records=[];calls=snapshots=0
@Lookup
def lookup(_,t,n):
 if t%4:return 0
 if BASE<=t and t+4*n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_START<=t and t+4*n<=IMAGE_START+IMAGE_SIZE:return C.addressof(image)+t-IMAGE_START
 return 0
host=Host(None,lookup,None,None,None,None);ig=(U*288)();pcx=PCX(host,None,None,C.addressof(ig),1,65536,0);context=Context(host,C.addressof(pcx),C.addressof(ig),65536,0)
lib=C.CDLL(str(WORK/'libSurfaceBlit.dylib'));lib.claw_surface_blit_entry.argtypes=[U,U,Args,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_surface_blit_entry.restype=U
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def raw():return bytes(heap)+bytes(image)if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE))
def get(t,n=1):return list(struct.unpack('<'+'I'*n,C.string_at(lookup(None,t,n),n*4)if native else m.u.mem_read(t,n*4)))
def put(t,v):
 b=pack(*v)
 if native:C.memmove(lookup(None,t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def effect(f,t,a,buffers):
 global index
 if f in(0x700014,0x70001c,0x700114,0x70011c):
  value=sequence[min(index,len(sequence)-1)]if sequence else 0;index+=1
  #Declared endpoint writes exercise complete heap comparison; not DD raster parity.
  if not value:put(DP,[a[0]^a[-1]^index])
  return value
 if f in(0x700074,0x700174):return sequence[0]if sequence else 0
 if f==0x7000b4:
  assert t==0 and a==[DST]
  if mutate:put(DST+8,[DD2]);put(SRC+8,[SD2]);put(DR,[2,3,10,9]);put(SR,[1,1,7,5])
  return restoreValue
 if f in(0x4bd260,0x4bd0a0):return 0
 raise AssertionError((hex(f),hex(t),a))
def event(f,t,a,mask,buffers):return (f,t,tuple(a),mask,tuple(bytes(b)for b in buffers),hashlib.sha256(raw()).digest())
@Dep
def dependency(_,p,user):
 q=p.contents;a=list(q.arguments[:q.count]);buffers=[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)];before=raw();events.append(event(q.function,q.receiver,a,q.mask,buffers))
 try:
  value=effect(q.function,q.receiver,a,buffers)
  if capture:records.append((q.function,q.receiver,a,q.mask,value,buffers,[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)],hashlib.sha256(before).digest(),[(i,y)for i,(x,y)in enumerate(zip(before,raw()))if x!=y]))
  return value
 except Exception as ex:errors.append(ex);context.fault=1;return 0
COUNTS={0x700014:(6,24),0x700114:(6,24),0x70001c:(6,24),0x70011c:(6,24),0x700074:(3,12),0x700174:(3,12),0x7000b4:(1,0),0x4bd260:(3,0),0x4bd0a0:(0,0)}
def hook(u,f,size,user):
 global index
 if f not in COUNTS:return
 n,pop=COUNTS[f];sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,n);mask=0;buffers=[]
 if f in(0x700014,0x700114):mask=((localMask&1)<<1)|((localMask&4)<<1)
 elif f in(0x70001c,0x70011c):mask=(localMask&8)<<1
 elif f in(0x700074,0x700174):mask=4 if currentFunction==0x4b9990 else(localMask&2)<<1
 for j in range(n):
  if mask&(1<<j):buffers.append(bytes(u.mem_read(a[j],8 if f in(0x700074,0x700174)else 16)));a[j]=0
 originalEvents.append(event(f,0,a,mask,buffers));value=effect(f,0,a,buffers)
 u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0):
 global native,index,sequence,restoreValue,restoreCallback,mutate
 native=True;C.memmove(heap,random.Random(seed).randbytes(SIZE),SIZE);C.memmove(image,imageSeed,IMAGE_SIZE);sequence=[];index=0;restoreValue=1;restoreCallback=0x7000b4;mutate=False;context.fault=0
 put(DST,[0x513690]);put(SRC,[0x513690]);put(DST+8,[DD]);put(SRC+8,[SD]);put(DST+180,[restoreCallback]);put(SRC+180,[0]);put(DST+20,[12,16,16]);put(SRC+20,[6,8,8]);put(DST+164,[8]);put(SRC+164,[8]);put(DD,[DVT]);put(DD2,[DVT2]);put(SD,[SVT]);put(SD2,[SVT2])
 for vt,base in((DVT,0x700000),(DVT2,0x700100),(SVT,0x700000),(SVT2,0x700100)):
  put(vt+0x14,[base+0x14]);put(vt+0x1c,[base+0x1c]);put(vt+0x74,[base+0x74])
 put(DR,[1,2,9,8]);put(SR,[0,0,8,6]);put(PAIR,[0,0]);put(FX,[100,0]+[0]*23)
def compare(f,a,mask=0,label='',void=False):
 global native,index,localMask,currentFunction,calls,snapshots
 native=True;index=0;localMask=mask;currentFunction=f;events.clear();originalEvents.clear();errors.clear();records.clear();context.fault=0;before=raw();contexts=[bytes(context),bytes(pcx)];args=Args();args.count=len(a)
 for j,v in enumerate(a):args.words[j]=v
 if mask&1:args.destination=C.cast(lookup(None,a[0],4),C.POINTER(U));args.words[0]=0
 sourceIndex=2 if f==0x4b9ce0 else 3 if f==0x4b9d80 else 1
 if mask&(1<<sourceIndex):args.source=C.cast(lookup(None,a[sourceIndex],2 if f==0x4b9950 else 4),C.POINTER(U));args.words[sourceIndex]=0
 out=U();ok=lib.claw_surface_blit_entry(f,DST,args,C.byref(context),dependency,None,C.byref(out));assert ok and not context.fault and not errors,(label,'native',context.fault,errors);expected=raw();expectedEvents=list(events);native=False;index=0;m.u.mem_write(BASE,before[:SIZE]);m.u.mem_write(IMAGE_START,before[SIZE:]);value=m.call(f,DST,pack(*a))
 assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4,(label,'SP')
 assert raw()==expected,(label,'memory')
 assert expectedEvents==originalEvents,(label,'events',expectedEvents,originalEvents)
 if not void:assert value==out.value,(label,'EAX',hex(value),hex(out.value))
 assert contexts==[bytes(context),bytes(pcx)],(label,'borrowed contexts')
 native=True;calls+=1;snapshots+=len(events)+1
 if capture:corpus.append((f,DST,args.words[:],args.count,mask,label,out.value,not void,before,expected,list(records),a))
 return out.value
