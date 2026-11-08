"""Original whole PCX entries; physical DirectDraw, allocation and file bytes are transport."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/pcx-image-agent';WORK.mkdir(exist_ok=True)
NAMES=['PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in NAMES],'-o',str(WORK/'libPCXImage.dylib')],check=True)
U=C.c_uint32
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('clock',Clock)]
Bytes=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Context(C.Structure):_fields_=[('scene',Host),('byteContext',C.c_void_p),('bytes',Bytes),('image',C.POINTER(U)),('composeImage',U),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('destination',C.POINTER(U)),('source',C.POINTER(U))]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x400000;SURFACE,MANAGER,DEVICE,VT,DATA,PIXELS,TEMP,PALETTE=[BASE+x for x in(0x1000,0x2000,0x3000,0x3100,0x10000,0x100000,0x200000,0x300000)]
GLOBAL_START,GLOBAL_SIZE=0x500000,0x48000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0x700000,0x1000);m.executed.clear()
#Keep original execution exact. For large retail bodies remove per-instruction
#Python tracing; selected small/directed calls still instrument real .text.
for handle in list(m.u._callbacks):m.u.hook_del(handle)
def stop(u,address,size,user):u.emu_stop()
m.u.hook_add(UC_HOOK_CODE,stop,begin=m.stop,end=m.stop)
static=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE));globalsImage=(C.c_uint8*GLOBAL_SIZE).from_buffer_copy(static);heap=(C.c_uint8*SIZE)();image=(U*288)();events=[[],[]];allocated=[{},{}];freed=[[],[]];calls=eventCount=0;errors=[];status={};restore=1;lockCount=[0,0];allocFailure=0;lockMutation=None
baseSeed=random.Random(721).randbytes(SIZE)
@Lookup
def lookup(_,t,n):
 if not(t%4)and BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if not(t%4)and GLOBAL_START<=t and t+n*4<=GLOBAL_START+GLOBAL_SIZE:return C.addressof(globalsImage)+t-GLOBAL_START
 return 0
@Bytes
def byteLookup(_,t,n):
 if BASE<=t and t+n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if GLOBAL_START<=t and t+n<=GLOBAL_START+GLOBAL_SIZE:return C.addressof(globalsImage)+t-GLOBAL_START
 return 0
host=Host(None,lookup,Allocate(),Free(),Invoke(),Clock());context=Context(host,None,byteLookup,image,1,100000000,0)
lib=C.CDLL(str(WORK/'libPCXImage.dylib'));lib.claw_pcx_image_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_pcx_image_entry.restype=U

def write(t,data,native=True):
 data=bytes(data)
 if native:
  dest=byteLookup(None,t,len(data));assert dest,hex(t);C.memmove(dest,data,len(data))
 else:m.u.mem_write(t,data)
def put(t,words,native=True):write(t,struct.pack('<'+'I'*len(words),*(v&0xffffffff for v in words)),native)
def read(t,n,native=True):
 if native:return C.string_at(byteLookup(None,t,n),n)
 return bytes(m.u.mem_read(t,n))
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,read(t,n*4,native)))
def snapshot(native):return hashlib.sha256(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(bytes(globalsImage)if native else bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))).digest(),tuple(sorted(allocated[0 if native else 1].items())),tuple(freed[0 if native else 1])
def effect(f,r,a,native):
 i=0 if native else 1
 if f==0x4f63ec:
  if allocFailure:return 0
  allocated[i][TEMP]=a[0];return TEMP
 if f==0x4f6428:allocated[i].pop(a[0],None);freed[i].append(a[0]);return 0
 if f==0x700064:
  lockCount[i]+=1
  if lockMutation:lockMutation(native,lockCount[i])
  value=status.get('lock',0)if lockCount[i]==1 else status.get('retry',0)
  if not value:put(SURFACE+48,[PIXELS],native)
  return value
 if f==0x700080:return status.get('unlock',0)
 if f==0x7000b4:return restore
 if f==0x4bd0a0:return 0
 if f==0x4bd260:return 0
 if f in(0x4b9b00,0x4b9fa0,0x4ba150,0x4ba3f0,0x4ba890):return status.get('unportedConversion',0)
 raise AssertionError((hex(f),hex(r),a))
@Dep
def dependency(_,p,user):
 q=p.contents;a=list(q.arguments[:q.count]);assert not q.destination and not q.source
 events[0].append(((q.function,q.receiver,tuple(a)),snapshot(True)))
 try:return effect(q.function,q.receiver,a,True)
 except Exception as error:errors.append(error);return 0
COUNTS={0x4f63ec:(1,0,False),0x4f6428:(1,0,False),0x700064:(5,20,False),0x700080:(2,8,False),0x7000b4:(1,0,False),0x4bd0a0:(0,0,False),0x4bd260:(3,0,False),0x4b9b00:(2,8,True),0x4b9fa0:(3,12,True),0x4ba150:(2,8,True),0x4ba3f0:(2,8,True),0x4ba890:(3,12,True)}
def hook(u,address,size,user):
 n,pop,thiscall=COUNTS[address];sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,n);r=u.reg_read(UC_X86_REG_ECX)if thiscall else 0
 events[1].append(((address,r,tuple(a)),snapshot(False)));v=effect(address,r,a,False);u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
for address in COUNTS:m.u.hook_add(UC_HOOK_CODE,hook,begin=address,end=address)

def prepare(width=8,height=3,planes=1,depth=None,padding=0):
 global heap,allocated,freed,status,restore,allocFailure,lockMutation
 heap=(C.c_uint8*SIZE).from_buffer_copy(baseSeed);C.memmove(C.addressof(globalsImage),static,GLOBAL_SIZE);allocated=[{},{}];freed=[[],[]];status={};restore=1;allocFailure=0;lockMutation=None;context.fault=0;lockCount[:]=[0,0]
 depth=depth if depth is not None else planes*8;pixelBytes=1 if depth==8 else 2 if depth==16 else 3 if depth==24 else 4
 put(SURFACE,[0x513690,0,DEVICE]+[0]*44);put(SURFACE+20,[height,width,width*pixelBytes+padding]);put(SURFACE+164,[depth]);put(SURFACE+48,[PIXELS]);put(MANAGER+0x474,[depth]);put(MANAGER+0x878,[1]);put(DEVICE,[VT]);put(VT+0x64,[0x700064]);put(VT+0x80,[0x700080]);put(SURFACE+180,[0x7000b4])
 put(MANAGER+0x478,list(struct.unpack('<256I',random.Random(width*31+height).randbytes(1024))))
 return depth

def pcx(width,height,planes=1,number=0):
 rng=random.Random(number);b=bytearray(rng.randbytes(128));struct.pack_into('<4h',b,4,0,0,width-1,height-1);b[65]=planes;struct.pack_into('<H',b,66,width)
 for y in range(height):
  for p in range(planes):
   x=0
   while x<width:
    count=min(rng.randint(1,8),width-x);value=rng.randrange(256)
    if count>1 or value>=192:b+=bytes((0xc0|count,value))
    else:b.append(value)
    x+=count
 b+=rng.randbytes(768);return bytes(b)

def sync():m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GLOBAL_START,bytes(globalsImage));allocated[1]=dict(allocated[0]);freed[1]=list(freed[0]);lockCount[:]=[0,0]
def compare(f,t,args,label,trace=True):
 global calls,eventCount
 sync();events[0].clear();events[1].clear();errors.clear();context.fault=0;out=U();a=(U*len(args))(*args)
 assert lib.claw_pcx_image_entry(f,t,a,len(args),C.byref(context),dependency,None,C.byref(out)),(label,context.fault,errors)
 assert not errors,errors
 h=m.u.hook_add(UC_HOOK_CODE,m.hook,begin=0x401000,end=0x50adb4)if trace else None
 try:v=m.call(f,t,struct.pack('<'+'I'*len(args),*args),max_instructions=500000000)
 finally:
  if h:m.u.hook_del(h)
 assert out.value==v,(label,'EAX',out.value,v)
 assert snapshot(True)==snapshot(False),(label,'fullheapglobals',snapshot(True)==snapshot(False))
 if events[0]!=events[1]:
  for i,(x,y)in enumerate(zip(*events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError((label,'orderedSnapshots',len(events[0]),len(events[1])))
 expectedPop={0x4bebc0:12,0x4babe0:4,0x4bad30:4,0x4bef50:16,0x4bf070:16,0x4b9e90:16,0x4ba580:12,0x4ba2d0:12,0x4bb0f0:4}.get(f,0)
 assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+expectedPop
 calls+=1;eventCount+=len(events[0]);return out.value
