"""Whole original Flip; real presentation/restore endpoints remain fixtures."""
import ctypes as C,hashlib,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/surface-flip-agent';WORK.mkdir(parents=True,exist_ok=True)
NAMES=['SurfaceFlipRuntime','SurfaceBlitRuntime','PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in NAMES],'-o',str(WORK/'libSurfaceFlip.dylib')],check=True)
U=C.c_uint32;Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class PCX(C.Structure):_fields_=[('scene',Host),('byteContext',C.c_void_p),('bytes',C.c_void_p),('image',C.c_void_p),('compose',U),('max',U),('fault',U)]
class Blit(C.Structure):_fields_=[('scene',Host),('pcx',C.c_void_p),('image',C.c_void_p),('max',U),('fault',U)]
class Context(C.Structure):_fields_=[('scene',Host),('blit',C.c_void_p),('max',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('mask',U),('bufferCount',U),('buffers',C.POINTER(U)*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x10000;IMAGE_START,IMAGE_SIZE=0x500000,0x48000
DST,SRC,DD,DD2,SD,SD2,DVT,DVT2,SVT,SVT2,PRIVATE,PRESENTED=[BASE+x for x in(0x1000,0x2000,0x3000,0x3100,0x3200,0x3300,0x4000,0x4100,0x4200,0x4300,0x4400,0x6000)]
OBJECTS=[(DST,188),(SRC,188),*[(t,4)for t in(DD,DD2,SD,SD2)],*[(t,48)for t in(DVT,DVT2,SVT,SVT2)],(PRIVATE,32),(PRESENTED,4)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x700000,0x1000);m.executed.clear();imageSeed=bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE));heap=(C.c_uint8*SIZE)();image=(C.c_uint8*IMAGE_SIZE)()
native=True;events=[];originalEvents=[];records=[];errors=[];sequence=[];index=0;restoreValue=1;mutation=None;capture=False;corpus=[];calls=snapshots=0
@Lookup
def lookup(_,t,n):
 if t%4:return 0
 if BASE<=t and t+4*n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_START<=t and t+4*n<=IMAGE_START+IMAGE_SIZE:return C.addressof(image)+t-IMAGE_START
 return 0
host=Host(None,lookup,None,None,None,None);ig=(U*288)();pcx=PCX(host,None,None,C.addressof(ig),1,65536,0);blit=Blit(host,C.addressof(pcx),C.addressof(ig),65536,0);context=Context(host,C.addressof(blit),65536,0)
lib=C.CDLL(str(WORK/'libSurfaceFlip.dylib'));lib.claw_surface_flip_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def raw():return bytes(heap)+bytes(image)if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE))
def get(t,n=1):return list(struct.unpack('<'+'I'*n,C.string_at(lookup(None,t,n),n*4)if native else m.u.mem_read(t,n*4)))
def put(t,v):
 b=pack(*v)
 if native:C.memmove(lookup(None,t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def effect(f,t,a):
 global index
 if f in(0x70002c,0x70012c):
  assert t==0 and a[2]==1;value=sequence[min(index,len(sequence)-1)]if sequence else 0;index+=1
  if not value:put(PRESENTED,[a[0]^a[1]^a[2]])
  if mutation:mutation(f,index)
  return value
 if f==0x7000b4:
  assert t==0 and a==[DST]
  if mutation:mutation(f,1)
  return restoreValue
 if f==0x7000e0:
  assert t==DST and not a
  if mutation:mutation(f,1)
  return restoreValue
 if f==0x4bd0a0:return 7 #The frozen restore body still returns0 after fallback.
 if f==0x4bd260:
  if mutation:mutation(f,1)
  return 0x12345678 #Diagnostic result cannot replace the saved Flip HRESULT.
 raise AssertionError((hex(f),hex(t),a))
def event(f,t,a):return(f,t,tuple(a),hashlib.sha256(raw()).digest())
@Dep
def dependency(_,p,user):
 q=p.contents;a=list(q.arguments[:q.count]);assert not q.mask and not q.bufferCount;before=raw();events.append(event(q.function,q.receiver,a))
 try:
  value=effect(q.function,q.receiver,a)
  if capture:records.append((q.function,q.receiver,a,value,hashlib.sha256(before).digest(),[(i,y)for i,(x,y)in enumerate(zip(before,raw()))if x!=y]))
  return value
 except Exception as ex:errors.append(ex);context.fault=1;return 0
COUNTS={0x70002c:(3,12,False),0x70012c:(3,12,False),0x7000b4:(1,0,False),0x7000e0:(0,0,True),0x4bd0a0:(0,0,False),0x4bd260:(3,0,False)}
def hook(u,f,size,user):
 if f not in COUNTS:return
 n,pop,thiscall=COUNTS[f];sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,n);t=u.reg_read(UC_X86_REG_ECX)if thiscall else 0;originalEvents.append(event(f,t,a));value=effect(f,t,a);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0,vt=0x5136c0):
 global native,index,sequence,restoreValue,mutation
 native=True;C.memmove(heap,random.Random(seed).randbytes(SIZE),SIZE);C.memmove(image,imageSeed,IMAGE_SIZE);index=0;sequence=[];restoreValue=1;mutation=None;context.fault=0
 put(DST,[vt]);put(SRC,[0x513588]);put(DST+8,[DD]);put(SRC+8,[SD]);put(DST+180,[0x7000b4]);put(DD,[DVT]);put(DD2,[DVT2]);put(SD,[SVT]);put(SD2,[SVT2]);put(PRIVATE+28,[0x7000e0])
 for vt,f in((DVT,0x70002c),(DVT2,0x70012c),(SVT,0x70002c),(SVT2,0x70012c)):put(vt+44,[f])
def compare(source,label=''):
 global native,index,calls,snapshots
 native=True;index=0;events.clear();originalEvents.clear();records.clear();errors.clear();context.fault=0;before=raw();bindings=[bytes(context),bytes(blit),bytes(pcx)];out=U();a=(U*1)(source)
 assert lib.claw_surface_flip_entry(0x4b98b0,DST,a,1,C.byref(context),dependency,None,C.byref(out))and not context.fault and not errors,(label,'native',context.fault,errors)
 expected=raw();expectedEvents=list(events);native=False;index=0;m.u.mem_write(BASE,before[:SIZE]);m.u.mem_write(IMAGE_START,before[SIZE:]);value=m.call(0x4b98b0,DST,pack(source));assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+8,(label,'RET4');assert raw()==expected,(label,'raw');assert originalEvents==expectedEvents,(label,'events');assert value==out.value,(label,'EAX',value,out.value);assert bindings==[bytes(context),bytes(blit),bytes(pcx)],(label,'borrowed bindings');native=True;calls+=1;snapshots+=len(events)+1
 if capture:corpus.append((source,out.value,before,expected,list(records)))
 return out.value
