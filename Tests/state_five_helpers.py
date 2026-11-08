"""Whole pinned retail menu calls, raw heap/global snapshots and ordered addressed transports."""
import ctypes as C,struct,hashlib,random,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/state-five-agent';U=C.c_uint32
support=ROOT/'work/application-level-progression-agent/libProgressionFrozenSupport.dylib';out=WORK/'libStateFiveCurrent.dylib';source=ROOT/'Sources/StateFiveRuntime.cpp'
if not out.exists()or source.stat().st_mtime>out.stat().st_mtime:subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',str(source),str(support),str(ROOT/'work/application-level-progression-agent/libProgressionCurrent.dylib'),'-o',str(out)],check=True)
lib=C.CDLL(str(out))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('alloc','free','call')]+[('clock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('application','base','special','results','story','lifecycle','actors','paper')]+[(n,U)for n in('composeBase','composeShared','composeScene','maximumOperations','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('bufferSizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_state_five_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000
APP,OWNER,SC,WINDOW,FRAME,RES,PAL,INPUT,CONTAINER,RENDERER,IMAGES,SOUNDS,ANIS,GRAPHICS,FILE,DATA,SURFACE,FRONT,BACK,TARGET,FW,BW,TW,DD,DDVT,MUSIC,ITEM,PAGE,COIN1,COIN2,CURSOR,OVER1,OVER2,OVER3,META,ARRAY,IMAGE,OUTSTRING,OUTFRAME,STRING=[BASE+0x1000+i*0x1000 for i in range(40)]
VT,READY,IFRAME,RENDER,DRAW,ISLOST,RESTORE,IMGLOAD,IMGRESET=[BASE+0x90000]+[0x4000000+i*0x20 for i in range(8)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x4000000,4096);m.stack=0x200e000;m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();ctx=Context();ctx.maximumOperations=65536
rng=random.Random(0x45ace0);events=[];originalEvents=[];errors=[];calls=eventCount=0;freed=[];created=[];cursor=BASE+0x50000;mutations={};clockIndex=0;unsafeCases=[];corpus=[];capture=False;replays=[]
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
def raw(native):return bytes(heap)+C.string_at(ptr(0x520000),0x30000)if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
def text(t,native=True):return C.string_at(ptr(t&~3)+t%4).split(b'\0')[0]if native else bytes(m.u.mem_read(t,8192)).split(b'\0')[0]
def writebytes(t,b,native=True):
 if native:C.memmove(ptr(t&~3)+(t%4),b,len(b))
 else:m.u.mem_write(t,b)
@Lookup
def lookup(_,t,n):
 value=ptr(t,n)
 if not value:errors.append(('span',hex(t),n))
 return value
@Clock
def clock(_):return 123456
ctx.scene=Host(None,lookup,None,None,None,clock)
ABIS={};CDECL=set();NAMED={0x4b7dc0,0x4f62a8,0x4f6286,0x4b7f20,0x4b7cd0,0x4b68c0,0x4b67f0,0x4c7970,0x4c79e0,0x4c7900}
def abi(f,n=0,pop=None,cdecl=False):
 ABIS[f]=(n,0 if cdecl else n*4 if pop is None else pop)
 if cdecl:CDECL.add(f)
for f,n in [(0x4f6439,0),(0x4f6449,1),(0x4f6584,0),(0x4f66cc,1),(0x4f6a1d,0),(0x4f4c93,1),(0x4f6286,2),(0x4f62a8,1),(0x4df460,1),(0x4dd0c0,0),(0x4df480,0),(0x4df260,1),(0x4ed050,0),(0x4dd520,1),(0x4ddbc0,0),(0x4dd480,0),(0x4dd450,1),(0x4dd020,1),(0x4ded00,2),(0x4ded20,1),(0x4ded40,1),(0x4dd490,1),(0x4df630,0),(0x4dd030,0),(0x4dd800,3),(0x4dceb0,2),(0x4dd270,1),(0x4ddc30,0),(0x4dda50,0),(0x4ddb40,0),(0x4b3490,0),(0x42c0a0,0),(0x42ba10,1),(0x42ba70,2),(0x42bab0,0),(0x42bad0,0),(0x42c280,1),(0x42bbb0,0),(0x42bbe0,0),(0x42bbd0,0),(0x42bbf0,0),(0x42bc40,1),(0x42be30,1),(0x42d460,1),(0x42a710,1),(0x4b45f0,4),(0x48ffa0,4),(0x4caa90,0),(0x4caa20,1),(0x4c8da0,6),(0x4c7900,2),(0x4c7970,1),(0x4c79e0,2),(0x4b8910,2),(0x42abf0,0),(0x48f500,1),(0x48f470,1),(0x45dc90,1),(0x4bb870,0),(0x4b3e70,0),(0x4b3dc0,4),(0x4b3fe0,3),(0x4b3e30,0),(0x4bb990,6),(0x4bb910,6),(0x4b97c0,1),(0x4b98b0,1),(0x4bbd90,4),(0x4bbb70,0),(0x4b4b80,0),(0x4b9d80,5),(0x490370,0),(0x429e10,2),(0x4c92f0,1),(0x4b4b40,0),(0x4ca300,0),(0x4cdf40,0),(0x4c89e0,0),(0x4dce90,0),(0x48f180,0),(0x4f5d00,0),(0x4dccb0,0),(0x4ca930,0),(0x48f0d0,3),(0x42a000,1),(0x4b7f20,1),(0x4b68c0,1),(0x4b7cd0,1),(0x4b67f0,2),(0x4b61c0,0),(0x4ca440,3),(0x4ce0d0,3),(0x4dcdf0,7),(0x4b6230,0),(0x4b53f0,3),(0x4dd0d0,1),(0x45f100,2),(0x45f360,2),(0x45c880,1),(0x45cb90,1),(0x45fee0,1),(0x42b5d0,0),(0x42b140,1)]:abi(f,n)
for f,n in [(0x4a3ce0,1),(0x4f63ec,1),(0x4f6428,1),(0x4f2360,1),(0x4b8960,1),(0x45fbb0,5)]:abi(f,n,cdecl=True)
for f,n in [(0x546d50,4),(0x546d54,1),(0x546d5c,5),(0x546cd0,1)]:abi(f,n);CDECL.add(f)
for f,n in [(READY,0),(IFRAME,1),(RENDER,2),(DRAW,1),(ISLOST,1),(RESTORE,0),(IMGLOAD,3),(IMGRESET,0)]:abi(f,n)
CDECL.add(ISLOST)
NOOPS={f for f in ABIS}-{0x4f6439,0x4f6449,0x4f6584,0x4f66cc,0x4f6a1d,0x4f4c93,0x4f6286,0x4f62a8,0x4df460,0x4a3ce0,0x4f63ec,0x4f6428,0x4dd480,0x4dd450,0x4dd020,0x4df260,0x4df480,0x4df630,0x4ed050,0x4dd0c0,0x4ded20,0x4ded40,0x4dd520,0x4dda50,0x4ddb40,0x4dd490,0x4c8da0,0x48f0d0,0x546d54,0x546cd0,0x546d5c,0x4b67f0,0x4b61c0}
def allocated(n,native):
 global cursor
 value=cursor;cursor+=(n+15)&~15;assert cursor<BASE+0x88000;created.append((value,n));return value
def stringnew(payload,native):
 t=allocated(len(payload)+13,native);put(t,[1,len(payload),len(payload)],native);writebytes(t+12,payload+b'\0',native);return t+12
for f,n in[(0x4f65f2,1),(0x4de4d0,2),(0x4dec60,1),(0x42cdc0,1),(0x429ed0,3),(0x4b54f0,2),(0x4d4160,0),(0x4b7f00,2),(0x4bc520,5),(0x42a4f0,0),(0x4ecb40,0),(0x4ec050,2),(0x4ec9c0,3),(0x4b9c50,1),(0x4ec600,1),(0x4bc4f0,1)]:abi(f,n);NOOPS.add(f)
for f,n in[(0x4b5650,0),(0x4b55e0,1),(0x4a3920,3)]:abi(f,n,cdecl=True);NOOPS.add(f)
abi(0x40af20);NOOPS.add(0x40af20);abi(0x4000300);NOOPS.add(0x4000300)
dcValue=0;failCreation=0;rollResource=FILE;rollImage=IMAGE;rollFade=GRAPHICS+512
ready=1;missing=0;failAllocation=0;allocationIndex=0;dictionaryFound=1;dictionaryValue=META;itemCount=1;selected=0;currentPage=PAGE;selectionId=10001;flags=0;availability=1;fileexists=0;baseInit=1;parseResult=1;lost=0;surfaceReady=1;navigationMutates=True
# CString transport preserves reference counts and source by-value ownership.
def effect(f,t,a,native):
 global selected,allocationIndex
 if f==0x4ecb40:put(t,[1,0,0,0,50,1,1,0,0,0x52e1c4,0],native);return t
 if f==0x4f65f2:put(t,[stringnew(text(a[0],native),native)],native);return t
 if f==0x4f6439:put(t,[0x52e1c4],native);return t
 if f==0x4f6449:
  value=get(a[0],native=native)[0]
  if BASE<=value<BASE+SIZE:put(value-12,[get(value-12,native=native)[0]+1],native)
  put(t,[value],native);return t
 if f==0x4f6584:
  value=get(t,native=native)[0]
  if BASE<=value<BASE+SIZE:
   refs=get(value-12,native=native)[0];put(value-12,[refs-1],native)
   if refs==1:freed.append(value-12)
  return 0
 if f==0x4f66cc:
  effect(0x4f6584,t,(),native);put(t,[stringnew(text(a[0],native),native)],native);return t
 if f==0x4f6a1d:
  value=get(t,native=native)[0];payload=text(value,native);writebytes(value,payload.lower()+b'\0',native);return t
 if f==0x4f4c93:return text(get(t,native=native)[0],native).find(text(a[0],native))&0xffffffff
 if f==0x4a3ce0:
  import re
  v=re.match(rb'\s*([+-]?\d+)',text(a[0],native));return int(v[1])&0xffffffff if v else 0
 if f==0x4f6286:put(a[1],[dictionaryValue],native);return dictionaryFound
 if f==0x4f62a8:return ARRAY+(sum(text(a[0],native))%128)*4
 if f==0x4df460:put(a[0],[get(STRING,native=native)[0]],native);return a[0]
 if f==0x4000340:put(a[1],[dcValue],native);return 0
 if f==0x4f4f58:
  fmt=text(a[1],native).decode();payload=(fmt%tuple(a[2:])).encode();put(a[0],[stringnew(payload,native)],native);return 0
 if f==0x4f6920:
  old=get(t,native=native)[0];payload=text(old,native)+text(a[0],native);effect(0x4f6584,t,(),native);put(t,[stringnew(payload,native)],native);return t
 if f==0x4a3920:writebytes(a[0],b"_SCREENS_MENU\0",native);return 13
 if f==0x4b7dc0:return rollResource
 if f==0x4b7f00:return FILE
 if f==0x4bc520:return rollImage
 if f==0x4d4100:put(t+44,[a[0]],native);return 1
 if f==0x4d4160:put(t+44,[0],native);return 0
 if f==0x4ec050:return rollFade
 if f==0x4b5650:return 60
 if f==0x4f63ec:
  allocationIndex+=1;return 0 if failAllocation==allocationIndex else allocated(a[0],native)
 if f==0x4f6428:freed.append(a[0]);return 0
 if f==0x4c8da0:
  if failCreation:return 0
  actor=allocated(436,native);put(actor,[0,0,0],native);put(actor+76,list(a[1:4]),native);put(actor+0x174,[IMAGE],native);return actor
 if f==0x4dd480:return selected
 if f==0x4dd450:return ITEM if a[0]<itemCount else 0
 if f==0x4dd020:return PAGE if a[0]in(10000,11001,11002,15000)else ITEM-60
 if f==0x4dd0c0:return currentPage
 if f==0x4df630:return 0 if t==PAGE else itemCount
 if f==0x4df480:return itemCount
 if f==0x4df260:return ITEM-60 if a[0]<itemCount else 0
 if f==0x4ed050:return get(t+68,native=native)[0]
 if f==0x4ded20:put(a[0],[100,220],native);return 1
 if f==0x4ded40:put(a[0],[80,210,140,240],native);return 1
 if f==0x4dd520:selected=get(t if False else a[0]+20,native=native)[0]-selectionId;return 1
 if f==0x4dd490:selected=a[0];return 1
 if f in(0x4dda50,0x4ddb40):
  if navigationMutates:selected=(selected+(1 if f==0x4ddb40 else -1))%max(itemCount,1)
  return 1
 if f==0x48f0d0:put(t+4,[a[0],RES,SC,0,a[1],a[2]],native);return baseInit
 if f in(0x4b7f20,0x4b7cd0,0x4b68c0):return 0 if missing==a[0]else RES
 if f==0x4b67f0:return 0 if missing==a[0]else FILE
 if f==0x4b61c0:return 0 if missing==f else DATA
 if f==0x4dcdf0:return parseResult
 if f==0x546d54:return 0xffffffff
 if f==0x546cd0:put(a[0],[55,77],native);return 1
 if f==0x546d5c:put(a[0],a[1:],native);return 1
 if f==0x4000320:return PAL
 if f==READY:return ready
 if f==ISLOST:return lost
 if f==0x4ca930:return surfaceReady
 if f==0x490370:return 1
 if f in(0x42ba10,0x42ba70,0x42bab0,0x42bad0,0x42c280,0x42c0a0):return availability
 if f==0x4f2360:return fileexists
 if f in NOOPS:return 1
 raise AssertionError(('service',hex(f),hex(t),a))
LOCALRECEIVERS={0x4f6920,0x4f65f2,0x4ecb40,0x4f6439,0x4f6449,0x4f6584,0x4f66cc,0x4f6a1d,0x4f4c93}
LOCALARGS={0x546d30:[3],0x4000340:[1],0x4f4f58:[0],0x4a3920:[0],0x4b7dc0:[0],0x4ec050:[1],0x4f6449:[0],0x4f6286:[1],0x4df460:[0],0x4ded20:[0],0x4ded40:[0],0x546cd0:[0]}
@Dep
def dep(_,q,u):
 try:
  e=q.contents;f=e.function;t=e.receiver;a=list(e.arguments[:e.count]);buffers=[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)];before=raw(True);events.append((f,t,tuple(a),e.name,e.mask,tuple(buffers),hashlib.sha256(before).digest()));scratch=BASE+0xf0000;index=0;restore=[]
  if e.mask&256:
   t=scratch;scratch+=max(64,len(buffers[index]));restore.append((t,bytes(C.string_at(ptr(t),len(buffers[index])))));writebytes(t,buffers[index]);index+=1
  for j in range(e.count):
   if e.mask&(1<<j):
    a[j]=scratch;scratch+=64;restore.append((a[j],bytes(C.string_at(ptr(a[j]),len(buffers[index])))));writebytes(a[j],buffers[index]);index+=1
  value=effect(f,t,tuple(a),True)
  index=0
  if e.mask&256:C.memmove(e.buffers[index],ptr(t),e.bufferSizes[index]);index+=1
  for j in range(e.count):
   if e.mask&(1<<j):C.memmove(e.buffers[index],ptr(a[j]),e.bufferSizes[index]);index+=1
  for address,b in restore:writebytes(address,b)
  for address,v in mutations.get(f,[]):put(address,[v])
  if capture:
   after=raw(True);old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);patches=[(i,y)for i,(x,y)in enumerate(zip(old,new))if x!=y];replays.append((f,e.receiver,tuple(e.arguments[:e.count]),e.name or b'',e.mask,hashlib.sha256(before).digest(),value,patches,buffers,[C.string_at(e.buffers[i],e.bufferSizes[i])for i in range(e.buffersCount)]))
  return value
 except Exception as ex:errors.append(ex);ctx.fault=1;return 0

# Only explicit dependency endpoints intercepted; owned function instructions execute.
def hook(uc,f,size,user):
 if f not in ABIS:return
 sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];
 if f==0x4f4f58:n=5 if m.read_words(sp+8,1)[0]==0x5291c4 else 4
 a=tuple(m.read_words(sp+4,n));t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX);nt=t;na=list(a);mask=0;buffers=[]
 if f in LOCALRECEIVERS and m.stack-4096<t<m.stack+100:
  nt=0;mask=256;buffers.append(bytes(44)if f==0x4ecb40 else bytes(uc.mem_read(t,4))if f not in(0x4f6439,0x4f6449,0x4f65f2)else bytes(4))
 for j in LOCALARGS.get(f,[]):
  if m.stack-4096<a[j]<m.stack+100:
   na[j]=0;mask|=1<<j;size=16 if f==0x546d30 else 64 if f in(0x4a3920,0x4b7dc0)else 44 if f==0x4ec050 else 16 if f==0x4ded40 else 8 if f in(0x4ded20,0x546cd0)else 4;buffers.append(bytes(uc.mem_read(a[j],size))if f==0x4f6449 else bytes(uc.mem_read(a[j],size))if f in(0x4f4f58,0x546d30,0x4b7dc0,0x4ec050)else bytes(size))
 if f==0x4b7dc0 and buffers:buffers[0]=text(a[0],False)+b"\0";buffers[0]+=bytes(64-len(buffers[0]))
 name=text(a[0],False)if a and f in NAMED else None
 originalEvents.append((f,nt,tuple(na),name,mask,tuple(buffers),snap(False)));value=effect(f,t,a,False)
 for address,v in mutations.get(f,[]):put(address,[v],False)
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
class UnsafePrefix(Exception):pass
def nullAccess(uc,access,address,size,value,user):
 if address<4096 and bytes(uc.mem_read(uc.reg_read(UC_X86_REG_EIP),1))!=b'\x64':raise UnsafePrefix((hex(uc.reg_read(UC_X86_REG_EIP)),address,size))
m.u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,nullAccess)
def fresh():
 global rollResource,rollImage,rollFade,failCreation,cursor,selected,clockIndex,allocationIndex,ready,missing,failAllocation,dictionaryFound,dictionaryValue,itemCount,currentPage,selectionId,availability,fileexists,baseInit,parseResult,lost,surfaceReady,navigationMutates,mutations
 C.memmove(C.addressof(image),imageSeed,len(image));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);cursor=BASE+0x50000;selected=clockIndex=allocationIndex=0;ready=dictionaryFound=availability=baseInit=parseResult=surfaceReady=1;rollResource=FILE;rollImage=IMAGE;rollFade=GRAPHICS+512;failCreation=missing=failAllocation=fileexists=lost=0;dictionaryValue=META;itemCount=1;currentPage=PAGE;selectionId=10001;navigationMutates=True;mutations={};ctx.fault=0;freed.clear();created.clear()
 put(OWNER,[0x50c1e4,APP,RES,SC]);put(APP,[VT]);put(VT+12,[READY]);put(APP+4,[WINDOW,FRAME]);put(WINDOW+4,[0x1234]);put(APP+48,[SC]);put(APP+100,[RES]);writebytes(RES+20,b"Captain Claw\0");put(RES+4,[0]);put(APP+92,[GRAPHICS]);put(GRAPHICS+36,[0]);put(APP+252,[0x52e1c4]);put(APP+104,[5]);put(APP+16,[1,1]);put(APP+80,[MUSIC]);put(MUSIC+40,[0]);put(OWNER+16,[0]);put(OWNER+60,[0,0]);put(OWNER+32,[RES,0,0,PAL]);put(SC+4,[SURFACE,CONTAINER,RENDERER,IMAGES,0,GRAPHICS,GRAPHICS,SOUNDS,ANIS]);put(CONTAINER,[VT]);put(RENDERER,[VT]);put(IMAGES,[VT]);put(VT+36,[IFRAME,DRAW]);put(VT+48,[0x4000320,RENDER]);put(VT+72,[IMGLOAD,IMGLOAD,0,0,IMGRESET]);put(SURFACE+16,[TARGET,FRONT,BACK]);
 for obj,wrapper in((TARGET,TW),(FRONT,FW),(BACK,BW)):put(obj+44,[wrapper]);put(wrapper+8,[DD])
 put(DD,[DDVT]);put(DDVT+96,[ISLOST]);put(DDVT+68,[0x4000340]);put(DDVT+104,[0x4000360]);put(PAL,[DDVT]);put(DDVT+52,[0x4000300]);put(PAL+16,[RES]);put(RES+52,[0]);put(SC+40,[SOUNDS,ANIS]);put(SOUNDS+44,[0]);put(OWNER+0x258,[CURSOR,COIN1,COIN2,COIN1,OVER1,0,OVER1,OVER2,OVER3]);put(OWNER+0x254,[120000]);put(OWNER+0x27c,[80,220,140,442]);put(OWNER+0x28c,[0,0,0,0,10000,5,7,350]);put(OWNER+0x154,[0x50c23c]);put(ITEM+20,[selectionId]);put(ITEM+68,[0]);put(ITEM+80,[selectionId]);put(META+16,[RES,ARRAY]);put(RES+40,[1234]);put(META+100,[1,100]);put(ARRAY,[IMAGE]*128);put(IMAGE+8,[DD]);put(IMAGE+16,[18,24]);put(IMAGE+44,[0x123abc]);put(OUTSTRING,[0x52e1c4]);put(OUTFRAME,[0]);put(FILE+20,[20]);put(STRING,[STRING+32]);put(STRING+20,[1,20,20]);writebytes(STRING+32,b'1_main_foo\0');put(0x5371fc,[APP]);put(0x537b58,[OWNER]);put(0x537200,[INPUT]);put(INPUT+528,[0,0]);put(0x54132c,[17]);put(0x53720c,[17]);put(0x532c0c,[0]);put(0x532c10,[100]);put(0x525508,[1]);put(0x528a60,[350,30,1]);put(0x537b48,[0,0,0,0]);
 for f in(0x546888,0x546880,0x546d30,0x546d50,0x546d54,0x546d5c,0x546cd0):put(f,[f])
def compare(f,label,args=(),receiver=OWNER,meaningful=True,cdecl=False,unsafe=False):
 global calls,eventCount,cursor,selected,clockIndex,allocationIndex
 ctx.fault=0;events.clear();originalEvents.clear();errors.clear();freed.clear();created.clear();before=bytes(heap);bi=bytes(image);state=(cursor,selected,clockIndex,allocationIndex);out=U();a=(U*len(args))(*args);replays.clear();ok=lib.claw_state_five_entry(f,receiver,a,len(args),C.byref(ctx),dep,None,C.byref(out));assert (not ok and ctx.fault in(1,2))if unsafe else(ok and not ctx.fault and not errors),(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events);dead=list(freed);born=list(created);final=(cursor,selected,clockIndex,allocationIndex);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);cursor,selected,clockIndex,allocationIndex=state;freed.clear();created.clear()
 try:
  value=m.call(f,receiver,pack(*args));assert not unsafe,(label,'original unsafe returned');assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+(0 if cdecl else len(args)*4),(label,'SP',hex(m.u.reg_read(UC_X86_REG_ESP)))
 except(UnsafePrefix,UcError):
  if not unsafe:raise
  value=0;unsafeCases.append(dict(function=hex(f),label=label,events=len(ev)))
 got=raw(False)
 if got!=expected:raise AssertionError((label,'heap',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x[:6],y[:6],x[-1].hex(),y[-1].hex())for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if meaningful and not unsafe:assert value==out.value,(label,'EAX',hex(value),hex(out.value))
 assert dead==freed and born==created,(label,'ownership',dead,freed,born,created);C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);cursor,selected,clockIndex,allocationIndex=final;calls+=1;eventCount+=len(ev)
 if capture and not unsafe:corpus.append((f,receiver,args,cdecl,out.value,meaningful,before,bi[0x520000-imageStart:0x550000-imageStart],raw(True),list(replays)))
 return out.value

for f in(0x45dc90,0x45fee0,0x45f100,0x45f360):ABIS.pop(f,None)

abi(0x4b5650);CDECL.discard(0x4b5650);abi(0x4b55e0,1);CDECL.discard(0x4b55e0)

for f in(0x45c880,0x45cb90):ABIS.pop(f,None)
for f,n in[(0x402570,0),(0x402520,0),(0x4b3d80,0),(0x42cdf0,0)]:abi(f,n);NOOPS.add(f)
abi(0x48c190,1,cdecl=True);NOOPS.add(0x48c190)

for f,n in[(0x4d4100,1),(0x4b7dc0,2),(0x4000320,3)]:abi(f,n);NOOPS.add(f)

ABIS.pop(0x45fbb0,None)
for f,n in[(0x546888,2),(0x546880,2),(0x546d30,5),(0x4000340,2),(0x4000360,2),(0x4f6920,1)]:abi(f,n);NOOPS.add(f)
for f in(0x546888,0x546880,0x546d30,0x4000340,0x4000360):CDECL.add(f)
abi(0x4f4f58,4,cdecl=True);NOOPS.add(0x4f4f58)
