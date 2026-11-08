"""Ordinary whole palette fade bodies; clock/COM/allocator are explicit fixtures."""
import ctypes as C,hashlib,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/palette-fade-agent';WORK.mkdir(parents=True,exist_ok=True)
NAMES=['PaletteFadeRuntime','PaletteResourceRuntime','AmbientAudioBackendRuntime','AudioEvents']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in NAMES],'-o',str(WORK/'libPaletteFade.dylib')],check=True)
U=C.c_uint32;Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Palette(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('scratch',U),('lists',U),('max',U),('fault',U)]
class Context(C.Structure):_fields_=[('scene',Host),('palette',C.c_void_p),('max',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('mask',U),('bufferCount',U),('buffers',C.POINTER(U)*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x10000;IMAGE_START,IMAGE_SIZE=0x500000,0x48000
BACKEND,PAL,PAL2,PVT,PVT2,DD,DVT,HOLDER,DATA,BACKUP,TARGET,SAVED,ALT,PHYSICAL,ALLOC=[BASE+x for x in(0x1000,0x2000,0x2100,0x2200,0x2300,0x2400,0x2500,0x2600,0x4000,0x4400,0x4800,0x4c00,0x5000,0x5400,0x7000)]
OBJECTS=[(BACKEND,56),*[(t,4)for t in(PAL,PAL2,DD,HOLDER)],(PVT,28),(PVT2,28),(DVT,92),*[(t,1024)for t in(DATA,BACKUP,TARGET,SAVED,ALT,PHYSICAL)]]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x700000,0x1000);m.executed.clear();imageSeed=bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE));heap=(C.c_uint8*SIZE)();image=(C.c_uint8*IMAGE_SIZE)()
native=True;events=[];originalEvents=[];records=[];errors=[];clocks=[];clockIndex=setIndex=0;cursor=ALLOC;created=[];freed=[];hrGet=hrSet=hrWait=0;mutation=None;capture=False;corpus=[];calls=snapshots=0
@Lookup
def lookup(_,t,n):
 if t%4:return 0
 if BASE<=t and t+4*n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_START<=t and t+4*n<=IMAGE_START+IMAGE_SIZE:return C.addressof(image)+t-IMAGE_START
 return 0
host=Host(None,lookup,None,None,None,None);pg=U();palette=Palette(host,C.addressof(pg),0,1,1000000,0);context=Context(host,C.addressof(palette),1000000,0)
lib=C.CDLL(str(WORK/'libPaletteFade.dylib'));lib.claw_palette_fade_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def raw():return bytes(heap)+bytes(image)if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE))
def get(t,n=1):return list(struct.unpack('<'+'I'*n,C.string_at(lookup(None,t,n),4*n)if native else m.u.mem_read(t,4*n)))
def put(t,v):
 b=pack(*v)
 if native:C.memmove(lookup(None,t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def effect(f,t,a):
 global cursor,clockIndex,setIndex
 if f==0x4f63ec:
  token=cursor;cursor+=a[0];created.append((token,a[0]));return token
 if f==0x4f6428:freed.append(a[0]);return 0
 if f==0x546df0:
  assert clocks and clockIndex<len(clocks),('clock exhausted',clockIndex,clocks)
  value=clocks[clockIndex];clockIndex+=1
  if mutation:mutation(f,clockIndex)
  return value&0xffffffff
 if f in(0x700010,0x700110):
  if not hrGet:put(a[4],get(PHYSICAL,256))
  if mutation:mutation(f,1)
  return hrGet
 if f in(0x700018,0x700118):
  setIndex+=1
  if mutation:mutation(f,setIndex)
  return hrSet
 if f==0x700058:
  if mutation:mutation(f,1)
  return hrWait
 if f==0x4bd260:return 0
 raise AssertionError((hex(f),hex(t),a))
def event(f,t,a,buffers):return(f,t,tuple(a),tuple(bytes(b)for b in buffers),hashlib.sha256(raw()).digest(),tuple(created),tuple(freed))
@Dep
def dependency(_,p,user):
 q=p.contents;a=list(q.arguments[:q.count]);assert not q.mask;buffers=[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)];before=raw();events.append(event(q.function,q.receiver,a,buffers))
 try:
  value=effect(q.function,q.receiver,a)
  if capture:records.append((q.function,q.receiver,a,value,buffers,[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)],hashlib.sha256(before).digest(),[(i,y)for i,(x,y)in enumerate(zip(before,raw()))if x!=y]))
  return value
 except Exception as ex:errors.append(ex);context.fault=1;return 0
COUNTS={0x4f63ec:(1,0),0x4f6428:(1,0),0x546df0:(0,0),0x700010:(5,20),0x700110:(5,20),0x700018:(5,20),0x700118:(5,20),0x700058:(3,12),0x4bd260:(3,0)}
def hook(u,f,size,user):
 if f not in COUNTS:return
 n,pop=COUNTS[f];sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,n);buffers=[]
 if f in(0x700010,0x700110,0x700018,0x700118)and a[3]:buffers=[bytes(u.mem_read(a[4],a[3]*4))]
 originalEvents.append(event(f,0,a,buffers));value=effect(f,0,a);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0):
 global native,cursor,hrGet,hrSet,hrWait,mutation,clockIndex,setIndex,clocks
 native=True;C.memmove(heap,random.Random(seed).randbytes(SIZE),SIZE);C.memmove(image,imageSeed,IMAGE_SIZE);cursor=ALLOC;created.clear();freed.clear();hrGet=hrSet=hrWait=0;mutation=None;clocks=[];clockIndex=setIndex=0;context.fault=0;palette.fault=0;pg.value=HOLDER
 put(BACKEND,[0,PAL,0,DATA,BACKUP,0,SAVED,0,750,1000,0,0,256,0]);put(PAL,[PVT]);put(PAL2,[PVT2]);put(DD,[DVT]);put(HOLDER,[DD]);put(PVT+16,[0x700010]);put(PVT+24,[0x700018]);put(PVT2+16,[0x700110]);put(PVT2+24,[0x700118]);put(DVT+88,[0x700058]);put(0x541374,[HOLDER]);put(0x546df0,[0x546df0])
def compare(f,a,label='',void=False):
 global native,cursor,clockIndex,setIndex,calls,snapshots
 native=True;clockIndex=setIndex=0;events.clear();originalEvents.clear();records.clear();errors.clear();context.fault=0;before=raw();start=(cursor,list(created),list(freed));bindings=[bytes(context),bytes(palette)];out=U();arguments=(U*len(a))(*a)
 assert lib.claw_palette_fade_entry(f,BACKEND,arguments,len(a),C.byref(context),dependency,None,C.byref(out))and not context.fault and not errors,(label,'native',context.fault,errors)
 expected=raw();expectedEvents=list(events);end=(cursor,list(created),list(freed),clockIndex,setIndex);native=False;cursor=start[0];created[:]=start[1];freed[:]=start[2];clockIndex=setIndex=0;m.u.mem_write(BASE,before[:SIZE]);m.u.mem_write(IMAGE_START,before[SIZE:]);value=m.call(f,BACKEND,pack(*a),max_instructions=10000000)
 assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4,(label,'SP')
 assert raw()==expected,(label,'raw',[(hex(BASE+i if i<SIZE else IMAGE_START+i-SIZE),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:12])
 assert originalEvents==expectedEvents,(label,'events',[(x[:4],y[:4],x[4:]==y[4:])for x,y in zip(expectedEvents,originalEvents)],len(expectedEvents),len(originalEvents))
 if not void:assert value==out.value,(label,'EAX',value,out.value)
 assert end==(cursor,list(created),list(freed),clockIndex,setIndex),(label,'ownership/time')
 assert bindings==[bytes(context),bytes(palette)],(label,'borrowed bindings');native=True;calls+=1;snapshots+=len(events)+1
 if capture:corpus.append((f,BACKEND,a,out.value,not void,before,expected,start[1],list(records)))
 return out.value
