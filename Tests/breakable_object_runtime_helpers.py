"""Private whole-source breakable oracle; raw service boundaries are explicit."""
import ctypes as C,hashlib,json,random,struct,subprocess,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/breakable-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in('BreakableObjectRuntime','WorldObjectRuntime','GenericEnemy','GenericEnemyStates','PlayerPhysics')],str(WORK/'shared-state-bridge.cpp'),'-o',str(WORK/'libBreakableObjectRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in('animationDelta','audioEnabled','audioPosition','crateImageChoice')]+[(n,C.c_float)for n in('damageScale','healthScale')]+[(n,C.c_uint32*10)for n in('kegStates','crateStates')]
class Loot(C.Structure):_fields_=[('words',C.c_uint32*341)]+[(n,C.c_uint32)for n in('itemCount','audioVolume','highLaunch','configurationWord')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('loot',C.POINTER(Loot)),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*12),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x60000
A,L,E,SC,ATT,IM,PTRS,IMAGE,AM,SR,SEQ,ROOTRESOURCE,TABLE,ALT,ALT2,AN,CONTAINER=[BASE+0x1000+i*0x1000 for i in range(17)]
NEWACTORS=BASE+0x20000;NEWBRAINS=BASE+0x40000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear();m.write_words(0x546d5c,[0x10ff080])
imageStart,imageEnd,_=next(x for x in u.mem_regions()if x[0]==0x400000)
image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(u.mem_read(imageStart,imageEnd-imageStart+1)))
heap=(C.c_uint8*SIZE)();g=Globals();loot=Loot();ctx=Context();ctx.globals=C.pointer(g);ctx.loot=C.pointer(loot)
lib=C.CDLL(str(WORK/'libBreakableObjectRuntime.dylib'));lib.claw_breakable_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_breakable_entry.restype=C.c_uint32
lib.claw_breakable_test_explode.argtypes=[C.POINTER(Context),C.c_uint32,Dependency,C.c_void_p];lib.claw_breakable_test_explode.restype=C.c_uint32
rng=random.Random(0x46f1e0);events=[];native=True;calls=eventCount=0;created=0;mutation=0;failAllocation=False;failCreation=False;missingResource=False;animationResult=0;compose=False;errors=[];selectedEntry=0;nativeCursor=0
mutableStart,mutableSize=0x520000,0x30000;imageSeed=bytes(u.mem_read(mutableStart,mutableSize))
GLOBAL_ADDRESSES=[0x5430c4,0x532c0c,0x532c10,0x52a194,0x5262b0,0x5262b4,0x537ea0,0x537308]
def put(t,v):
 data=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
 else:u.mem_write(t,data)
def get(t,n=1):
 if native:
  if BASE<=t and t+n*4<=BASE+SIZE:return list(struct.unpack_from('<'+'I'*n,heap,t-BASE))
  return list(struct.unpack_from('<'+'I'*n,image,t-imageStart))
 return m.read_words(t,n)
def number(t,v):
 data=struct.pack('<d',v)
 if native:C.memmove(C.addressof(heap)+t-BASE,data,8)
 else:u.mem_write(t,data)
def globalBytes():
 if not native:return bytes(u.mem_read(mutableStart,mutableSize))
 b=bytearray(imageSeed);raw=bytes(g)
 for i,address in enumerate(GLOBAL_ADDRESSES):
  start=24+(i-6)*40 if i>=6 else i*4;size=40 if i>=6 else 4;b[address-mutableStart:address-mutableStart+size]=raw[start:start+size]
 b[0x537ec8-mutableStart:0x537ec8-mutableStart+1364]=bytes(loot.words)
 for address,value in [(0x52a190,loot.itemCount),(0x53721c,loot.highLaunch)]:struct.pack_into('<I',b,address-mutableStart,value)
 return bytes(b)
def snapshot():return (hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(globalBytes()).digest(),created)
@Lookup
def lookup(_,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return None
@Allocate
def allocate(_,n):
 events.append((0x4f63ec,0,(n,),snapshot()));return 0 if failAllocation else E
@Free
def free(_,t):events.append((0x4f6428,0,(t,),snapshot()))
ctx.scene=Host(None,lookup,allocate,free,Invoke(),Clock())
COUNTS={0x4332f0:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4209d0:1,0x40f6c0:4,0x406240:0,0x4dbd20:1,0x4cd800:2,0x4dba00:1,0x406290:0,
0x4c7fa0:1,0x4c8060:1,0x4c8da0:6,0x40f680:1,0x4c82a0:1,0x4c79e0:2,0x40f540:4,0x4735b0:5,0x4a3050:0,0x4f6286:2,0x4b45f0:4,0x4dc870:1,0x43f120:1,
0x4c8220:1,0x42df90:0,0x486e70:1,0x43d490:1,0x4db6e0:2,0x4dbcd0:0,0x4f6584:0,0x4f63ec:1,0x4f6428:1,0x4c96b0:0,0x405000:0,0x43e9b0:0,0x43ffa0:0,0x4719e0:1,0x473610:1,0x40f450:7,0x433f30:0,0x433fb0:0,0x433ed0:0,0x4717e0:1,
0x10ff000:1,0x10ff010:0,0x10ff020:0}
CDECL={0x4dc870,0x40f540,0x4735b0,0x4a3050,0x486e70,0x4f63ec,0x4f6428,0x4719e0,0x473610,0x40f450,0x10ff000}
OWN={0x473610,0x4717e0,0x40f450,0x40f540,0x4735b0,0x433f30,0x433fb0,0x433ed0}
def effect(f,receiver,args):
 global created
 if compose and f==0x43ffa0:
  if not native:return None
  assert lib.claw_breakable_test_explode(C.byref(ctx),receiver,dependency,None);return 0
 if compose and f in OWN:return entry(f,receiver,args)if native else None
 if f==0x4f63ec:return 0 if failAllocation else E
 if f==0x4332f0:
  # Declared base constructor boundary: a shared-service result, not a
  # guessed recovery of4332f0. Exact generic body is separately frozen.
  a=args[0];l=get(a+0x6c)[0];put(receiver+0xc,[a,l]);put(receiver+0x128,[a,a,l]);put(receiver+0x2f4,[0x50b14c,0x544b68,8,0]);number(receiver+0x70,float(struct.unpack('<i',struct.pack('<I',get(a+0x50)[0]))[0]));return receiver
 if f==0x4c7970:put(receiver+0x16c,[1,IM,IMAGE]);return 1
 if f==0x4062e0 or f==0x4061b0:return 0 if missingResource and args[0]!=0x5234b4 else SEQ
 if f==0x4209d0:put(receiver+0x16c,[args[0]]);return 0
 if f==0x40f6c0:put(receiver+0x118,args);return 0
 if f==0x406240:put(receiver+0x128,[0xffffffec,0xfffffff0,20,24]);return 0
 if f==0x406290:put(receiver+0x128,[1,2,3,4]);return 0
 if f==0x4dbd20:
  bit=args[0];put(receiver+8,[max(get(receiver+8)[0],bit+1)]);put(receiver+12,[get(receiver+12)[0]|1<<(bit&31)]);return 0
 if f==0x4dba00:return {0x523148:71,0x5266f8:72,0x5271b4:73,0x526700:74,0x524418:75}[args[0]]
 if f==0x4c7fa0:put(receiver+0x70,[L+0x400]);return 1
 if f==0x4c8060:put(receiver+0x78,[L+0x800]);return 1
 if f==0x4c8da0:
  if failCreation:return 0
  token=NEWACTORS+created*0x1000;l=token+0x400;created+=1
  put(token+0xc,[SC]);put(token+0x4c,args[1:3]);put(token+0x64,[args[3]]);put(token+0x6c,[l]);put(l+0xc,[SC]);put(l+0x10,[0x10ff000]);return token
 if f==0x10ff000:
  a=args[0];l=get(a+0x6c)[0];index=(a-NEWACTORS)//0x1000;put(l+0x18,[NEWBRAINS+index*0x500]);put(l+0x1c,[1000]);return 1
 if f==0x40f680:return get(PTRS+args[0]*4)[0]
 if f==0x4c82a0:
  if mutation:put(receiver+0x14,[get(receiver+0x14)[0]^0x17]);put(receiver+0x1c,[animationResult])
  return animationResult
 if f==0x4c79e0:put(receiver+0x190,[SEQ]);return 1
 if f==0x4a3050:return get(AN)[0]
 if f==0x4f6286:return 0 if missingResource else ROOTRESOURCE
 if f==0x4b45f0:
  if mutation:put(ATT+0x104,[get(ATT+0x104)[0]+1])
  return 0
 if f==0x4c8220:put(receiver+8,[args[0]]);return 1
 if f==0x4db6e0:
  descriptor=g.kegStates if receiver==0x537ea0 else g.crateStates
  if native:descriptor[2]=args[0];descriptor[3]=(args[0]+3)&0xffffffff
  else:m.write_words(receiver+8,[args[0],args[0]+3])
  return TABLE
 if f==0x4dbcd0:put(receiver+8,[0]);return 0
 if f==0x4f6584:put(receiver,[0x52e1c4]);return 0
 if f==0x4719e0:
  if native:loot.words[340]=1
  else:m.write_words(0x538418,[1])
  return 0
 if f==0x473610:return IM if args[0]%3 else 0
 return 0
@Dependency
def dependency(c,event,_):
 e=event.contents;args=list(e.arguments[:e.argumentCount]);events.append((e.function,e.receiver,tuple(args),snapshot()))
 try:return effect(e.function,e.receiver,args)or 0
 except BaseException as error:errors.append(error);return 0

def entry(f,receiver,args):
 out=C.c_uint32();args=(C.c_uint32*len(args))(*args);ok=lib.claw_breakable_entry(f,receiver,args,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok,(hex(f),ctx.fault);return out.value

def returned(pop,value):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_EIP,get(sp)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(uc,address,size,_):
 if address==get(0x546d5c)[0]: # SetRect pure platform adapter, no service event.
  sp=u.reg_read(UC_X86_REG_ESP);a=get(sp+4,5);put(a[0],a[1:]);returned(20,1);return
 if address not in COUNTS or address==selectedEntry:return
 if compose and address==0x40f450:
  parent=get(u.reg_read(UC_X86_REG_ESP))[0]
  if 0x40f540<=parent<0x40f680 or 0x4735b0<=parent<0x473610:return
 sp=u.reg_read(UC_X86_REG_ESP);args=get(sp+4,COUNTS[address]);receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX)
 originalArgs=args[:1]if address==0x4f6286 else args
 events.append((address,receiver,tuple(originalArgs),snapshot()))
 value=effect(address,receiver,originalArgs)
 if value is None:return
 if address==0x4f6286:put(args[1],[value]);value=1 if value else 0
 returned(0 if address in CDECL else len(args)*4,value)
u.hook_add(UC_HOOK_CODE,hook)

def syncGlobals():
 raw=bytes(g)
 for i,address in enumerate(GLOBAL_ADDRESSES):
  start=24+(i-6)*40 if i>=6 else i*4;size=40 if i>=6 else 4;u.mem_write(address,raw[start:start+size])
 u.mem_write(0x537ec8,bytes(loot.words));m.write_words(0x52a190,[loot.itemCount]);m.write_words(0x53721c,[loot.highLaunch])
def prepare():
 global native,created,mutation,failAllocation,failCreation,missingResource,animationResult,compose,imageSeed
 native=True;created=0;ctx.fault=0;mutation=0;failAllocation=False;failCreation=False;missingResource=False;animationResult=0;compose=False
 C.memset(C.addressof(heap),0xa5,SIZE)
 for t,n in [(A,128),(L,93),(E,264),(ATT,128),(IM,40),(SC,32),(ALT,264),(ALT2,264)]:put(t,[rng.getrandbits(32)for _ in range(n)])
 put(A+0xc,[SC]);put(A+0x6c,[L,0,ATT]);put(A+0x4c,[320,240]);put(A+0x64,[0]);put(A+0x16c,[1,IM,IMAGE]);put(A+0x40,[0]);put(A+0x1a4,[1]);put(A+0x19c,[1]);put(A+0x10c,[2]);put(A+0x100,[1]);put(ATT+0xd0,[32]);put(L+0xc,[SC,0x471720]);put(L+0x18,[E,0]);put(L+0x64,[0]);put(L+0xf0,[0]*8);put(L+0x130,[0]);put(SC+8,[CONTAINER]);put(SC+0x24,[0x303e000,AM,AM]);put(AM+0x30,[0]);put(ROOTRESOURCE+0x10,[SR]);put(IM+0x64,[1,3]);put(IM+0x14,[PTRS]);put(PTRS,[0,IMAGE,IMAGE+0x100,IMAGE+0x200,0]);put(IMAGE+0x18,[21,25,7,9]);put(AN,[rng.randrange(0,32768)]);put(SEQ+0x10,[SR]);put(E+0x3b8,[SEQ]);put(E+0x368,[SEQ]);
 put(E,[0x50edd4]);put(E+0xc,[A,L]);put(E+0x128,[A,A,L]);put(E+0x2f4,[0x50b14c,0x544b68,8,0]);put(E+0x1a0,[0]);put(E+0x400,[0,0,0,240]);number(E+0x70,240);number(E+0xa0,240);number(E+0x58,0)
 for t in(ALT,ALT2):put(t+0x400,[0,0,0,240])
 g.animationDelta=18;g.audioEnabled=1;g.audioPosition=73;g.crateImageChoice=rng.randrange(20);g.damageScale=1;g.healthScale=1
 for table in(g.kegStates,g.crateStates):table[:]=[0,0,10,13,TABLE,TABLE+0x100,4,0,0xfeed,0]
 put(TABLE,[0,0x433f30,0x433fb0,0x433ed0]);loot.itemCount=62;loot.highLaunch=0;loot.audioVolume=g.audioPosition;loot.configurationWord=0
 for i in range(341):loot.words[i]=0
 for i in range(66):loot.words[i]=IM if i%4 else 0
 loot.words[340]=1
 u.mem_write(BASE,bytes(heap));syncGlobals();imageSeed=bytes(u.mem_read(mutableStart,mutableSize))

def compare(f,args=(),receiver=0,label=None,meaningful=True):
 global native,events,calls,eventCount,created,selectedEntry,imageSeed
 native=True;before=bytes(heap);beforeG=bytes(g);beforeLoot=bytes(loot);beforeCreated=created
 events=[];selectedEntry=f;out=entry(f,receiver,args);ne=list(events);expected=bytes(heap);expectedGlobal=globalBytes();endCreated=created
 assert not errors,errors
 native=False;created=beforeCreated;u.mem_write(BASE,before);u.mem_write(mutableStart,imageSeed)
 # Retained native globals may differ from the original PE initial image.
 C.memmove(C.addressof(g),beforeG,len(beforeG));C.memmove(C.addressof(loot),beforeLoot,len(beforeLoot));syncGlobals();events=[]
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
 except BaseException as error:raise AssertionError(('original failure',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events[-2:]))from error
 oe=list(events);actual=bytes(u.mem_read(BASE,SIZE));actualGlobal=bytes(u.mem_read(mutableStart,mutableSize))
 assert ne==oe,('event mismatch',hex(f),label,[(hex(e[0]),hex(e[1]),e[2])for e in ne],[(hex(e[0]),hex(e[1]),e[2])for e in oe])
 if expected!=actual:
  diff=[(hex(BASE+i),expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=actual[i:i+4]];raise AssertionError(('heap mismatch',hex(f),label,diff[:20]))
 assert expectedGlobal==actualGlobal,('global mismatch',hex(f),label,[(hex(mutableStart+i),expectedGlobal[i:i+4].hex(),actualGlobal[i:i+4].hex())for i in range(0,mutableSize,4)if expectedGlobal[i:i+4]!=actualGlobal[i:i+4]][:15])
 assert created==endCreated
 if meaningful:assert ret==out,('EAX mismatch',hex(f),hex(ret),hex(out),label)
 native=True;C.memmove(C.addressof(heap),actual,SIZE);C.memmove(C.addressof(g),beforeG,len(beforeG));C.memmove(C.addressof(loot),beforeLoot,len(beforeLoot))
 for i,address in enumerate(GLOBAL_ADDRESSES):
  start=24+(i-6)*40 if i>=6 else i*4;size=40 if i>=6 else 4;C.memmove(C.addressof(g)+start,actualGlobal[address-mutableStart:address-mutableStart+size],size)
 C.memmove(C.addressof(loot.words),actualGlobal[0x537ec8-mutableStart:0x537ec8-mutableStart+1364],1364)
 loot.itemCount=m.read_words(0x52a190,1)[0];loot.highLaunch=m.read_words(0x53721c,1)[0];imageSeed=actualGlobal
 calls+=1;eventCount+=len(ne)
