"""Whole pinned retail results bodies; raw heap, retained counters and exact slot services."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/booty-results-agent';U=C.c_uint32
out=WORK/'libResults.dylib';sources=list((ROOT/'Sources').glob('*.cpp'))
if not out.exists()or any(p.stat().st_mtime>out.stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(out)],check=True)
lib=C.CDLL(str(out))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('alloc','free','call','clock')]
class Context(C.Structure):_fields_=[('scene',Host),('progression',C.c_void_p),('numbers',C.c_void_p),('actors',C.c_void_p)]+[(n,U)for n in('composeBase','composeNumbers','composeScene','composeAnimation','composeImages','maximumSteps','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('bufferSizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_booty_results_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x80000
APP,OWNER,CHILD,NEW,PREVIOUS,SC,WINDOW,RES,HOLDER,TARGET,PAL,EXTRA,SOUND,THREAD=[BASE+0x1000+i*0x1000 for i in range(14)]
ACTOR,PRIMARY,PRIVATE,GROUP,IMAGE,TABLE,CONTAINER,INPUT=[BASE+0x11000+i*0x1000 for i in range(8)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.stack=0x200e000;m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();ctx=Context();ctx.maximumSteps=100000
rng=random.Random(0x498930);events=[];originalEvents=[];errors=[];calls=eventCount=0;allocationCursor=BASE+0x30000;resource=1;createFail=0;allocationFail=0;allocationIndex=createIndex=0;randomIndex=0;randomValues=[0];queryValues=[0xffffffff];queryIndex=0;ready=1;resourceIndex=0;paintMutation=False;callbackMutation=0;freed=[];unhandled=[];currentFunction=0;lastCaller=0
OWNED=[0x40d470,0x40dc50,0x40dca0,0x40dcb0,0x40dc10,0x40b040,0x40b020,0x40e020,0x40e040,0x40dd50,0x40de90,0x40df00,0x40df60,0x4903c0,0x499c30,0x40db10,0x40db60,0x4c89e0,0x4c89f0,0x490370,0x48ffa0,0x48f470,0x4995d0,0x499170,0x499450,0x499630,0x4997c0,0x4998c0,0x499cd0,0x499d60,0x498f90,0x498930]
ABIS={0x48f0d0:(3,12),0x4b7f20:(1,4),0x4b7cd0:(1,4),0x4b7dc0:(2,8),0x4f6286:(2,8),0x4f6439:(0,0),0x4f65f2:(1,4),0x4f66cc:(1,4),0x4f6920:(1,4),0x4f667d:(1,4),0x4f6584:(0,0),0x4f63ec:(1,0),0x4f6428:(1,0),0x4c8da0:(6,24),0x4c7970:(1,4),0x4c7900:(2,8),0x4c79e0:(2,8),0x4c82a0:(1,4),0x490760:(7,28),0x4b45f0:(4,16),0x4b3dc0:(4,16),0x4208e0:(4,16),0x4a3050:(0,0),0x4ce0d0:(3,12),0x4b3490:(0,0),0x45fbb0:(4,16),0x4b98b0:(1,4),0x4b97c0:(1,4),0x4b9d80:(5,20),0x546d50:(4,16),0x546d54:(1,4),0x4ca930:(0,0),0x4ca9e0:(1,4),0x4caa90:(0,0),0x4caa20:(1,4),0x4bb990:(6,24),0x4cdf40:(0,0),0x48f180:(0,0),0x4f5172:(0,0),0x4d46f0:(1,4),0x4bb870:(0,0),0x4bb910:(6,24),0x4bbd90:(4,16),0x4bbd20:(0,0),0x4bb8c0:(1,4),0x4ca900:(2,8),0x40af20:(0,0),0x484d90:(1,4),0x4c9be0:(1,4),0x546cb4:(2,8),0x546cb8:(2,8),0x4a3920:(3,0),0x4f4f58:(0,0)}
SERVICES={0x4000020:(3,12),0x4000040:(3,12),0x4000060:(0,0),0x4000080:(1,4),0x40000a0:(2,8),0x40000c0:(1,4),0x40000e0:(0,0),0x4000100:(0,0),0x4000120:(0,0),0x4000140:(3,12)}
ABIS.update(SERVICES);m.u.mem_map(0x4000000,4096)
CDECL={0x4f63ec,0x4f6428,0x4a3050,0x4a3920,0x4f4f58,0x546cb4,0x546cb8,0x546d50,0x546d54}
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def text(t,native=True):
 if native:return C.string_at(ptr(t&~3)+t%4).split(b'\0')[0]
 return bytes(m.u.mem_read(t,200)).split(b'\0')[0]
def writeBytes(t,b,native=True):
 if native:C.memmove(ptr(t&~3)+t%4,b,len(b))
 else:m.u.mem_write(t,b)
def raw(native):return(bytes(heap)+C.string_at(ptr(0x520000),0x30000))if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('span',hex(t),n))
 return p
ctx.scene=Host(None,lookup,None,None,None,None)
def alloc(n,native):
 global allocationCursor
 t=allocationCursor;allocationCursor+=((n+15)//16)*16
 assert allocationCursor<BASE+SIZE
 return t
# CString allocation/copy and release are explicit MFC transports with complete heap bytes.
def string(b,native):
 t=alloc(12+len(b)+1,native);put(t,[1,len(b),len(b)],native);writeBytes(t+12,b+b'\0',native);return t+12
def effect(f,t,a,n,native):
 global resourceIndex,allocationIndex,createIndex,randomIndex,queryIndex
 if f==0x48f0d0:put(t+4,[a[0],get(a[0]+52,native=native)[0],get(a[0]+48,native=native)[0],0,a[1],a[2]],native);put(t+52,[1],native);return ready
 if f==0x4b7f20:resourceIndex+=1;return RES if resource and resourceIndex!=resource else 0
 if f==0x4b7cd0:return RES if resource else 0
 if f==0x4b7dc0:return RES if resource else 0
 if f==0x4f6439:put(t,[get(0x52e1cc,native=native)[0]],native);return t
 if f in(0x4f65f2,0x4f66cc):put(t,[string(text(a[0],native),native)],native);return t
 if f==0x4f6920:put(t,[string(text(get(t,native=native)[0],native)+text(a[0],native),native)],native);return t
 if f==0x4f667d:put(t,[get(a[0],native=native)[0]],native);return t
 if f==0x4f6584:return 0
 if f==0x4f63ec:
  allocationIndex+=1
  return 0 if allocationFail==allocationIndex else alloc(a[0],native)
 if f==0x4f6428:freed.append(a[0]);return 0
 if f==0x4c8da0:
  createIndex+=1
  if createFail==createIndex:return 0
  actor=alloc(436,native);logic=alloc(372,native);put(actor,[0x5137f0],native);put(actor+8,[0,SC],native);put(actor+76,[a[1],a[2]],native);put(actor+100,[a[3]],native);put(actor+108,[logic,0,0,0,0],native);put(actor+392,[0,actor,0,0,0,0,0,0,0,0,0],native);put(logic,[0x513740,actor,0,SC],native);put(logic+16,[{b'SimpleAnimation':0x498f40,b'TreasureCounter':0x498930,b'TreasureLogic':0x498f90,b'StatusNumberDigit':0x4919f0}.get(text(a[4],native),0),0],native);put(logic+24,[0,0,0],native);put(logic+104,[0],native);return actor
 if f in(0x4c7970,0x4c7900):put(t+364,[a[1]if f==0x4c7900 else 0,IMAGE,IMAGE+0x400],native);return 1
 if f==0x4c79e0:put(t+392,[1,t,0,0,0,0,0,0,0,0,0],native);return 1
 if f==0x4c82a0:
  if callbackMutation:put(get(t+4,native=native)[0]+200,[callbackMutation],native)
  return 0
 if f==0x490760:
  # Original whole HUD is composed later; exact stores for transport fixture.
  for i,v in enumerate([a[0],a[3],0,a[5],a[6],a[1],a[2],0]):put(t+i*4,[v],native)
  return 1
 if f==0x4f6286:
  result=IMAGE if text(a[0],native).startswith(b'BOOTY_TREASURE_COINS')else SOUND if resource else 0
  if len(a)>1 and a[1]:put(a[1],[result],native)
  return result
 if f==0x4a3050:v=randomValues[randomIndex%len(randomValues)];randomIndex+=1;return v
 if f==0x546d54:v=queryValues[queryIndex%len(queryValues)];queryIndex+=1;return v
 if f in(0x4000020,0x4000040,0x4000140):return PAL if ready else 0
 if f==0x4000060:return 1
 if f==0x4000080:return 0
 if f==0x40000a0:return 0
 if f==0x40000c0:return 0
 if f==0x40000e0:return 0
 if f==0x4000100:return 0
 if f==0x4000120:return 0
 if f in(0x4ca930,0x4ca900):return ready
 if f==0x40af20:return get(t+52,native=native)[0]
 if f in(0x484d90,0x4c9be0):
  if a and a[0]&1:freed.append(t)
  return t
 if f==0x4f5172:put(t+4,[0,0,0],native);return 0
 if f in(0x546cb4,0x546cb8):return 1
 if f in(0x4b45f0,0x4b3dc0,0x4208e0,0x4ce0d0,0x4b3490,0x45fbb0,0x4b98b0,0x4b97c0,0x4b9d80,0x546d50,0x4ca9e0,0x4caa90,0x4caa20,0x4bb990,0x4cdf40,0x48f180,0x4d46f0,0x4bb870,0x4bb910,0x4bbd90,0x4bbd20,0x4bb8c0):return 0
 raise AssertionError(('service',hex(f),hex(t),a,n))
def formatting(f,a,native):
 fmt=text(a[1],native)
 values=[]
 for v in a[2:]:
  if b'%s'in fmt and not values:values.append(text(v,native))
  else:values.append(v if v<0x80000000 else v-0x100000000)
 return fmt%tuple(values)
@Dep
def dep(_,q,u):
 try:
  e=q.contents;a=tuple(e.arguments[:e.count]);n=e.name;f=e.function;t=e.receiver;buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)]
  # Uninitialized stack bytes aren't observable input to printf/GDI; normalize only initialized CString cells.
  logged=(f,t,a,n,e.mask,tuple(buffers if f in(0x4f6584,0x4f6920,0x4f667d,0x546cb8)else []),snap(True));events.append(logged)
  if f==0x546cb4:
   C.memmove(e.buffers[0],pack(*range(16)),64)
   if paintMutation:put(WINDOW+4,[0x5555])
   return 1
  if f in(0x4a3920,0x4f4f58):
   b=formatting(f,a,True)
   if f==0x4a3920:C.memmove(e.buffers[0],b+b'\0',len(b)+1)
   else:cell=string(b,True);C.memmove(e.buffers[0],pack(cell),4)
   return len(b)
  if e.mask&256:
   cell=struct.unpack('<I',C.string_at(e.buffers[0],4))[0]
   if f==0x4f6439:cell=get(0x52e1cc)[0]
   elif f==0x4f65f2:cell=string(text(a[0]),True)
   elif f==0x4f6920:cell=string(text(cell)+text(a[0]),True)
   elif f!=0x4f6584:raise AssertionError(('local',hex(f)))
   C.memmove(e.buffers[0],pack(cell),4);return 0
  if e.mask==1 and f==0x4f667d:
   put(t,[struct.unpack('<I',C.string_at(e.buffers[0],4))[0]]);return t
  return effect(f,t,a,n,True)
 except Exception as ex:errors.append(ex);return 0

def hook(uc,f,size,u):
 global allocationCursor,lastCaller
 if f not in ABIS or f in(0x484d90,0x4c9be0)or(ctx.composeNumbers and f in(0x490760,0x40db30,0x40db50,0x4919f0,0x4f5172))or(ctx.composeImages and f in(0x4c7970,0x4c7900))or(ctx.composeAnimation and f in(0x4c79e0,0x4c82a0)):return
 sp=uc.reg_read(UC_X86_REG_ESP);lastCaller=m.read_words(sp,1)[0];n,pop=ABIS[f];t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX)
 if f in(0x4a3920,0x4f4f58):
  if f==0x4f4f58:
   fmt=m.read_words(sp+8,1)[0];n=4 if fmt==0x523cc8 else 3
  a=tuple(m.read_words(sp+4,n))
 else:a=tuple(m.read_words(sp+4,n))
 textname=None;mask=0;buffers=[];aa=list(a);tt=t
 if f in(0x4f6439,0x4f65f2,0x4f6920,0x4f6584)and 0x2000000<=t<0x2010000:
  tt=0;mask=256;buffers=[bytes(uc.mem_read(t,4))];
 if f==0x4f667d and 0x2000000<=a[0]<0x2010000:
  mask=1;buffers=[bytes(uc.mem_read(a[0],4))];aa[0]=0;
 if f in(0x4a3920,0x4f4f58):
  mask=1;aa[0]=0;tt=0;textname=text(a[1],False)
 if f==0x4f6286:aa=aa[:1]
 if f==0x4b7dc0 and 0x2000000<=a[0]<0x2010000:mask=1;aa[0]=0;textname=text(a[0],False)
 if f==0x4000040 and 0x2000000<=a[1]<0x2010000:mask=2;aa[1]=0;textname=text(a[1],False)
 if f in(0x546cb4,0x546cb8):mask=2;aa[1]=0;buffers=[bytes(uc.mem_read(a[1],64))]
 if f in(0x4b7f20,0x4b7cd0,0x4f6286,0x4f65f2,0x4f66cc,0x4f6920,0x4c7970,0x4c7900,0x4c79e0):textname=text(a[0],False)
 originalEvents.append((f,tt,tuple(aa),textname,mask,tuple(buffers if f in(0x4f6584,0x4f6920,0x4f667d,0x546cb8)else []),snap(False)))
 if f==0x546cb4:
  uc.mem_write(a[1],pack(*range(16)));value=1
  if paintMutation:put(WINDOW+4,[0x5555],False)
 elif f in(0x4a3920,0x4f4f58):
  b=formatting(f,a,False)
  if f==0x4a3920:uc.mem_write(a[0],b+b'\0')
  else:uc.mem_write(a[0],pack(string(b,False)))
  value=len(b)
 else:
  value=effect(f,t,a,textname,False)
  
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(level=1):
 global allocationCursor,resource,createFail,allocationFail,allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex,ready,callbackMutation,randomValues,queryValues
 C.memmove(C.addressof(image),imageSeed,len(image));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);allocationCursor=BASE+0x30000;resource=3;createFail=allocationFail=0;allocationIndex=createIndex=randomIndex=queryIndex=resourceIndex=0;ready=1;callbackMutation=0;randomValues=[0];queryValues=[0xffffffff];ctx.fault=0;ctx.composeBase=ctx.composeNumbers=ctx.composeScene=ctx.composeAnimation=ctx.composeImages=0
 put(APP+4,[WINDOW]);put(WINDOW+4,[0x1234]);put(APP+48,[SC,RES]);put(APP+156,[0]);put(APP+304,[0]);put(CHILD,[0x50b494]);put(CHILD+4,[APP,RES,SC,0,level,1]);put(CHILD+32,[RES,RES]);put(CHILD+44,[PAL]);put(CHILD+52,[1]);put(CHILD+340,[0,0]);put(CHILD+348,[0]*9);put(CHILD+384,[0x52e1c4]);put(SC+4,[HOLDER,CONTAINER,SC+0x500,SC+0x600]);put(SC+24,[SC+0x700]);put(SC+40,[SOUND,SC+0x800]);put(CONTAINER,[CONTAINER+0x300]);put(CONTAINER+0x33c,[0x4c89f0]);put(SC+0x500,[SC+0x900]);put(SC+0x934,[0x40000a0]);put(CONTAINER+0x324,[0x4000080,0x40000c0]);put(SC+0x600,[SC+0xa00]);put(SC+0xa48,[0x4000020,0x4000140]);put(SC+0xa58,[0x40000e0]);put(SC+0x700,[SC+0xb00]);put(SC+0xb30,[0x4000040]);put(PAL,[PAL+0x200]);put(PAL+0x234,[0x4000060]);put(PAL+16,[PAL+0x300]);put(PAL+0x310,[PAL+0x400]);put(HOLDER+16,[TARGET,TARGET+0x100,TARGET+0x200]);put(TARGET+44,[TARGET+0x500]);put(TARGET+0x12c,[TARGET+0x600]);put(TARGET+0x22c,[TARGET+0x700]);put(SOUND+48,[0]);put(SOUND+16,[SOUND+0x200]);put(IMAGE+100,[0,9]);put(IMAGE+20,[TABLE]);put(TABLE,[IMAGE+0x400+i*4 for i in range(10)]);put(SOUND+16,[SOUND+0x200]);put(INPUT+528,[0]);put(0x537200,[INPUT]);put(0x5371fc,[APP]);put(0x53499c,[0x52e1c4]);put(0x5349a0,[0]);put(0x5349a8,[0]);put(0x53cac4,[0]*6);put(0x534cc4,[123456]);put(0x534d08,[0]*9);put(0x5381e0,[0]*9);put(0x532c0c,[1,75]);put(0x53720c,[16]);put(0x5430c4,[16]);put(0x546d50,[0x546d50]);put(0x546d54,[0x546d54]);put(0x546cb4,[0x546cb4]);put(0x546cb8,[0x546cb8]);put(0x52e1cc,[0x52e1c4]);put(CONTAINER+16,[0x5107bc,0,0,0,0,0,10]);put(ACTOR,[0x5137f0]);put(ACTOR+8,[0,SC]);put(ACTOR+76,[0,0]);put(ACTOR+100,[9998]);put(ACTOR+108,[PRIMARY,0,0,0,0]);put(ACTOR+364,[0,IMAGE,IMAGE+0x400]);put(ACTOR+392,[0,ACTOR,0,0,0,0,0,0,0,0,0]);put(PRIMARY,[0x513740,ACTOR,0,SC,0x498930,0,PRIVATE,0]);put(PRIMARY+104,[0]);put(PRIMARY+172,[0]);put(PRIVATE,[0x50b5bc]);put(PRIVATE+40,[0x50b5cc]);put(PRIVATE+96,[0]*22);put(PRIVATE+140,[0,0,0,1,1,160,55]);writeBytes(CHILD+0x500,b'01AMULET\0');put(CHILD+384,[CHILD+0x500]);put(CHILD+0x4f8,[8]);freed.clear()
def compare(f,label,args=(),receiver=CHILD,meaningful=True,cdecl=False):
 global calls,eventCount,resourceIndex,allocationCursor,allocationIndex,createIndex,randomIndex,queryIndex,currentFunction
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();freed.clear();before=bytes(heap);bi=bytes(image);cursor=allocationCursor;indices=(allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex);currentFunction=f;arr=(U*len(args))(*args);out=U();ok=lib.claw_booty_results_entry(f,receiver,arr,len(args),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events);nativeFreed=list(freed);afterCursor=allocationCursor;afterIndices=(allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);allocationCursor=cursor;allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex=indices;freed.clear();result=m.call(f,receiver,pack(*args));got=raw(False);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+(0 if cdecl else len(args)*4),(label,'SP',hex(m.u.reg_read(UC_X86_REG_ESP)))
 if got!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x[:6],y[:6],x[6].hex(),y[6].hex())for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if meaningful:assert result==out.value,(label,'EAX',hex(result),hex(out.value))
 assert freed==nativeFreed and allocationCursor==afterCursor
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex=afterIndices;calls+=1;eventCount+=len(ev);return out.value
class NumberGlobals(C.Structure):_fields_=[(n,U)for n in('manager','player','delta','animation','remaining','initial','expired','multi','left','top','right','bottom','audio')]
class NumberContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(NumberGlobals))]+[(n,U)for n in('composeAnimation','composeImages','composeHierarchy','composeFormatting','fault')]
numberGlobals=NumberGlobals();numberContext=NumberContext();numberContext.globals=C.pointer(numberGlobals);ctx.numbers=C.addressof(numberContext)
def enableNumbers():
 ctx.composeNumbers=1;numberGlobals.manager=APP;numberGlobals.left=numberGlobals.top=0;numberGlobals.right=640;numberGlobals.bottom=480;put(0x5370c8,[0,0,640,480]);put(APP+104,[0,0]);numberContext.fault=0
# Immutable retail PID/ANI bytes: filesystem/name enumeration is an explicit transport.
assetTokens={};assetInventory=[];assetMode=False
class AniRecord(C.Structure):_fields_=[('control',U),('ticks',U),('image',U),('moveX',U),('moveY',U),('flags',U),('code',U),('subtype',U),('unknown',U),('sound',U)]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
def enableAssets():
 global assetMode
 import re
 assetMode=True;assetTokens.clear();assetInventory.clear();root=BASE+0x60000;table=BASE+0x64000;leaf=BASE+0x70000
 folder=ROOT/'work/original-disc-assets/STATES/BOOTY';groups={}
 for path in sorted((folder/'IMAGES').rglob('*.PID')):
  if 'MAPPIECE'in path.parts:continue
  data=path.read_bytes();group=path.parent.relative_to(folder/'IMAGES').as_posix();match=re.search(r'[0-9]+$',path.stem);ident=int(match.group())if match else int(re.search(r'[0-9]+',path.stem).group());groups.setdefault(group,[]).append((ident,path,data))
 for group,rows in groups.items():
  minimum=min(v[0]for v in rows);maximum=max(v[0]for v in rows);put(root+20,[table]);put(root+100,[minimum,maximum]);put(table,[0]*(maximum+1));name=('BOOTY_'+group.replace('/','_')).encode();assetTokens[name]=root
  for ident,path,data in rows:
   put(table+ident*4,[leaf]);sig,flags,w,height,x,y=struct.unpack_from('<6I',data);put(leaf+16,[w,height,x,y]);assetInventory.append(dict(path=path.relative_to(ROOT/'work/original-disc-assets').as_posix(),id=ident,sha256=hashlib.sha256(data).hexdigest(),width=w,height=height));leaf+=48
  root+=128;table+=((maximum+1)*4+15)//16*16
 recordAt=BASE+0x78000;groupAt=BASE+0x68000
 for path in sorted((folder/'ANIS').glob('CYCLE*.ANI')):
  data=path.read_bytes();sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;at=32+pl;token=groupAt;pointers=[]
  for i in range(count):
   tail=data[at:];b=(C.c_uint8*len(tail)).from_buffer_copy(tail);rec=AniRecord();length=U();used=lib.claw_animation_decode_record(b,len(tail),SOUND,C.byref(rec),C.byref(length));assert used;values=list(struct.unpack('<10I',bytes(rec)));put(recordAt,[0x513af0,values[0],*values[1:9],0,values[9]]);pointers.append(recordAt);recordAt+=48;at+=used
  assert at==len(data);put(token+12,[token+0x40,count]);put(token+0x40,pointers);assetTokens[('BOOTY_'+path.stem).encode()]=token;assetInventory.append(dict(path=path.relative_to(ROOT/'work/original-disc-assets').as_posix(),sha256=hashlib.sha256(data).hexdigest(),frames=count));groupAt+=256
 assert leaf<BASE+0x78000 and recordAt<BASE+SIZE and table<BASE+0x68000
 ctx.composeImages=ctx.composeAnimation=1
_previousEffect=effect
def effect(f,t,a,n,native):
 if f==0x4f6286 and assetMode:
  key=text(a[0],native);value=assetTokens.get(key,SOUND if resource else 0)
  if len(a)>1 and a[1]:put(a[1],[value],native)
  return value
 return _previousEffect(f,t,a,n,native)
_previousFresh=fresh
def fresh(level=1):
 global assetMode
 assetMode=False;_previousFresh(level);put(0x53c9ac,[0,0])
class UnsafePrefix(Exception):pass
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
def nullAccess(uc,access,address,size,value,user):
 if address<4096:
  pc=uc.reg_read(UC_X86_REG_EIP)
  if bytes(uc.mem_read(pc,1))!=b'\x64':raise UnsafePrefix((hex(pc),address,size))
m.u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,nullAccess)
unsafeCases=[]
def unsafe(f,label,args=(),receiver=CHILD):
 global calls,eventCount,allocationCursor,allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();before=bytes(heap);bi=bytes(image);cursor=allocationCursor;indices=(allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex);arr=(U*len(args))(*args);out=U();ok=lib.claw_booty_results_entry(f,receiver,arr,len(args),C.byref(ctx),dep,None,C.byref(out));assert not ok and ctx.fault==2,(label,ok,ctx.fault,errors);expected=raw(True);ev=list(events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);allocationCursor=cursor;allocationIndex,createIndex,randomIndex,queryIndex,resourceIndex=indices
 try:m.call(f,receiver,pack(*args));raise AssertionError('original returned from unsafe path')
 except(UnsafePrefix,UcError):pass
 assert expected==raw(False),(label,'heap-prefix');assert ev==originalEvents,(label,'event-prefix',len(ev),len(originalEvents),next(((i,x[:6],y[:6])for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None));unsafeCases.append(dict(function=hex(f),label=label,events=len(ev)));calls+=1;eventCount+=len(ev)
capture=False;corpus=[];replayEvents=[];initialDependency=dep
@Dep
def recordedDependency(c,q,u):
 e=q.contents;before=raw(True);buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)];value=initialDependency(c,q,u)
 if capture:
  after=raw(True);old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);patches=[(i,y)for i,(x,y)in enumerate(zip(old,new))if x!=y];replayEvents.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.name or b'',e.mask,hashlib.sha256(before).digest(),value,patches,buffers,[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)]))
 return value
dep=recordedDependency
initialCompare=compare
def compare(f,label,args=(),receiver=CHILD,meaningful=True,cdecl=False):
 before=bytes(heap);bi=bytes(image);compose=(ctx.composeNumbers,ctx.composeAnimation,ctx.composeImages);replayEvents.clear();v=initialCompare(f,label,args,receiver,meaningful,cdecl)
 if capture:corpus.append((f,receiver,args,compose,v,meaningful,before,bi[0x520000-imageStart:0x550000-imageStart],raw(True),list(replayEvents)))
 return v
def saveCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as file:
  file.write(b'BREZ'+pack(imageStart,len(imageSeed),SIZE,len(corpus))+imageSeed)
  for f,t,a,compose,out,meaning,before,globalBefore,after,replays in corpus:
   file.write(pack(f,t,len(a),*list(a)+[0]*(7-len(a)),*compose,out,int(meaning),len(replays))+before+globalBefore)
   for ef,et,ea,name,mask,digest,value,patches,buffers,outputs in replays:
    file.write(pack(ef,et,len(ea),*list(ea)+[0]*(40-len(ea)),mask,value,len(name),len(patches),len(buffers))+digest+name)
    for patch in patches:file.write(pack(*patch))
    for b,v in zip(buffers,outputs):file.write(pack(len(b))+b+v)
   file.write(after)
