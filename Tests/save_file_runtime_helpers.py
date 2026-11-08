"""Original save-byte/CPtrList/CFile oracle; physical file transport is explicit."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_ESI,UC_X86_REG_EBX,UC_X86_REG_EBP,UC_X86_REG_EDI
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/save-file-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in('SaveFileRuntime','ActorDestruction','WorldLootRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming','CheckpointLogicRuntime','ActorAnimationRuntime','AnimationEngine','AnimationOperations','AudioEvents','ActorResourceBindings','SpriteGeometry')],'-o',str(WORK/'libSaveFileRuntime.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);ByteLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host),('lookupBytes',ByteLookup)]+[(n,U)for n in('emptyStringToken','fileScratchToken','pathScratchToken','securityScratchToken','countScratchToken','maximumTraversal','maximumSteps','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*8)]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
class ADGlobals(C.Structure):_fields_=[('holderActorToken',U),('heldActorToken',U),('emptyStringToken',U)]
class CPGlobals(C.Structure):_fields_=[('words',U*34)]
class CPContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(CPGlobals))]+[(n,U)for n in('composeAnimation','composeContactBinding','composeSave','composeSaveCache','fault')]
class CPCall(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*4),('name',C.c_char_p),('localMask',U),('bufferCount',U),('buffers',UP*2),('bufferWords',U*2)]
CPDependency=C.CFUNCTYPE(U,C.POINTER(CPContext),C.POINTER(CPCall),C.c_void_p)
CP={0x49a720,0x49a800,0x49a860,0x49ae60}
BASE,SIZE=0x3000000,0x100000;M,F,P,SEC,COUNT,STR,TLS,ERR,DATA,NODES=[BASE+i*0x1000 for i in range(1,11)];RECORDS=BASE+0x10000;BUFFER=BASE+0x30000;CSTR=BASE+0x80000
GS,GN=0x520000,0x30000;m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear();STUB=0x10fc000;DEC=0x10fcf00
IMPORTS={0x546b00:7,0x546b0c:0,0x546a04:1,0x546af8:5}
STUBS={STUB+i*16:slot for i,slot in enumerate(IMPORTS)}
for at,slot in STUBS.items():u.mem_write(at,b'\xc3');m.write_words(slot,[at])
u.mem_write(DEC,b'\xc3');m.write_words(0x5469e8,[DEC]);globalSeed=bytes(u.mem_read(GS,GN));IS,IE,_=next(x for x in u.mem_regions()if x[0]==0x400000);image=(C.c_uint8*(IE-IS+1)).from_buffer_copy(bytes(u.mem_read(IS,IE-IS+1)))
heap=(C.c_uint8*SIZE)();ctx=Context();lib=C.CDLL(str(WORK/'libSaveFileRuntime.dylib'));lib.claw_save_file_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_save_file_entry.restype=U
lib.claw_save_file_initialize_manager.argtypes=[U,C.POINTER(Context)];lib.claw_save_file_initialize_manager.restype=U
lib.claw_checkpoint_entry.argtypes=[U,U,UP,U,C.POINTER(CPContext),CPDependency,C.c_void_p,UP];lib.claw_checkpoint_entry.restype=U
lib.claw_actor_destruction_entry.argtypes=[U,U,U,C.POINTER(ADGlobals),Host,UP,UP];lib.claw_world_loot_next_random.argtypes=[UP];lib.claw_world_loot_next_random.restype=U
native=True;rng=random.Random(0x49bbc0);events=[];freed=[];live={};files={};handles={};cursor=0;openIndex=0;nextHandle=0;failOpen=None;failAllocate=False;writePolicy=0;closeFailure=False;mutation=0;errors=[];calls=eventCount=0;maps={};boundaries={};sourceHalt=False;prefix=False;currentRoot=0
OWN={0x49bbc0,0x49bf70,0x49bfb0,0x49c000,0x49c030,0x49c070,0x4f72c9,0x4f7369,0x4f7448,0x4f75aa,0x4f766e,0x4f650f}
EXTERNAL={0x4f777f:2,0x4f66cc:1,0x4f64ba:0,0x4fc384:1,0x4fc242:2,0x4fc303:3,0x4a3040:1,0x4a3050:0,0x4f6584:0}
CDECL={0x4f777f,0x4fc384,0x4fc242,0x4fc303,0x4a3040,0x4a3050}
SIZES={F:16,P:260,SEC:12,COUNT:4}

def actual(t,n):
 if not native:
  for logical,physical in maps.items():
   if logical<=t and t+n<=logical+SIZES[logical]:return physical+t-logical
 return t
def putBytes(t,b):
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(actual(t,len(b)),b)
def put(t,v):putBytes(t,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
def get(t,n=1):
 if not native:return m.read_words(actual(t,n*4),n)
 if BASE<=t and t+n*4<=BASE+SIZE:return list(struct.unpack_from('<'+'I'*n,heap,t-BASE))
 return list(struct.unpack_from('<'+'I'*n,image,t-IS))
def readBytes(t,n):
 if not native:return bytes(u.mem_read(actual(t,n),n))
 if BASE<=t and t+n<=BASE+SIZE:return bytes(heap[t-BASE:t-BASE+n])
 return bytes(image[t-IS:t-IS+n])
def text(t):return readBytes(t,260).split(b'\0')[0]if t else b''
def canonical():
 b=bytearray(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))
 for logical,size in SIZES.items():
  if logical in(P,SEC,COUNT):b[logical-BASE:logical-BASE+size]=bytes(size) # undefined caller path padding excluded
  elif logical in maps:b[logical-BASE:logical-BASE+size]=readBytes(logical,size)
 return bytes(b)
def snapshot():return(hashlib.sha256(canonical()).digest(),hashlib.sha256(globalSeed if native else bytes(u.mem_read(GS,GN))).digest(),tuple(freed),tuple(sorted(live.items())),tuple(sorted(files.items())),tuple(sorted(handles.items())),cursor,openIndex,nextHandle)
@Lookup
def lookup(_,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:
  if BUFFER<=t<BUFFER+0x40000 and t+n*4>BUFFER+boundaries.get(BUFFER,0):return None
  return C.addressof(heap)+t-BASE
 if IS<=t and t+n*4<=IE+1:return C.addressof(image)+t-IS
 return None
@ByteLookup
def byteLookup(_,t,n):
 if BASE<=t and t+n<=BASE+SIZE:
  if BUFFER<=t<BUFFER+0x40000 and t+n>BUFFER+boundaries.get(BUFFER,0):return None
  return C.addressof(heap)+t-BASE
 if IS<=t and t+n<=IE+1:return C.addressof(image)+t-IS
 return None
@Free
def free(_,t):events.append((0x4f6428,0,(t,),snapshot()));freed.append(t);live[t]=False
@Allocate
def allocate(_,n):
 events.append((0x4f63ec,0,(n,),snapshot()))
 if mutation==1:put(M+0xc,[2])
 if failAllocate:return 0
 boundaries[BUFFER]=n;live[BUFFER]=True;return BUFFER
ctx.scene=Host(None,lookup,allocate,free,Invoke(),Clock());ctx.lookupBytes=byteLookup;ctx.emptyStringToken=0x52e1c4;ctx.fileScratchToken=F;ctx.pathScratchToken=P;ctx.securityScratchToken=SEC;ctx.countScratchToken=COUNT

def releaseString(field):
 s=get(field)[0]
 if s!=ctx.emptyStringToken:
  header=s-12;refs=(get(header)[0]-1)&0xffffffff;put(header,[refs])
  if refs==0 or refs&0x80000000:free(None,header)
def effect(f,t,args):
 global cursor,openIndex,nextHandle
 if f==0x4f777f:putBytes(args[0],(b'C:\\CLAW\\'+text(args[1])).ljust(260,b'\0'));return 1
 if f==0x4f66cc:
  value=text(args[0]);releaseString(t);head=CSTR+cursor*0x200;cursor+=1;put(head,[1,len(value),len(value)]);putBytes(head+12,value+b'\0');put(t,[head+12]);live[head]=True;return t
 if f==0x4f64ba:releaseString(t);put(t,[ctx.emptyStringToken]);return 0
 if f==0x4f6584:
  if native:
   fault=U();out=U();assert lib.claw_actor_destruction_entry(f,t,0,C.byref(ADGlobals(0,0,ctx.emptyStringToken)),ctx.scene,C.byref(fault),C.byref(out));assert not fault.value
  return 0
 if f==0x4a3040:put(TLS+0x14,[args[0]]);return 0
 if f==0x4a3050:
  word=U(get(TLS+0x14)[0]);result=lib.claw_world_loot_next_random(C.byref(word));put(TLS+0x14,[word.value]);return result
 if f==0x546b00:
  name=text(args[0]);index=openIndex;openIndex+=1
  if index==failOpen:return 0xffffffff
  if args[4]==2:files[name]=b''
  elif name not in files:return 0xffffffff
  nextHandle+=1;token=0x70000000+nextHandle*0x100;handles[token]=(name,0,args[1]);return token
 if f==0x546b0c:return 112
 if f==0x546a04:
  if not closeFailure:handles.pop(args[0],None)
  return 0 if closeFailure else 1
 if f==0x546af8:
  handle,data,size,count,_=args;name,pos,access=handles[handle];actualSize=size if writePolicy==0 else max(0,size-1)if writePolicy==1 else 0;buf=files[name];incoming=readBytes(data,actualSize);files[name]=buf[:pos]+incoming+buf[pos+actualSize:];
  if mutation==2:put(M+0x44,[0x10203040])
  handles[handle]=(name,pos+actualSize,access);put(count,[actualSize]);return 0 if writePolicy==2 else 1
 if f==0x4fc384:return 5
 if f in(0x4fc242,0x4fc303):
  if prefix:
   if native:ctx.fault=3
   else:raise StopIteration('source exception boundary')
  return 0
 raise AssertionError(('unrepresented service',hex(f),hex(t),args))
@Dependency
def dependency(c,ev,_):
 e=ev.contents;f=e.function;t=e.receiver;args=tuple(e.arguments[:e.argumentCount]);events.append((f,t,args,snapshot(),tuple(get(SEC,3))if f==0x546b00 else tuple(get(COUNT))if f==0x546af8 else ()))
 try:return effect(f,t,args)
 except BaseException as error:errors.append(error);return 0

def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def normalize(t):
 for logical,physical in maps.items():
  if physical<=t<physical+SIZES[logical]:return logical+t-physical
 return t
def hook(uc,address,size,_):
 global sourceHalt
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f72c9 and currentRoot==0x49bbc0:maps[F]=receiver
 if address==DEC:
  t=m.read_words(sp+4,1)[0];value=(get(t)[0]-1)&0xffffffff;put(t,[value]);returned(4,value);return
 if address==0x4a7dc0:returned(0,TLS);return
 if address in(0x4f63ec,0x4f6428):
  arg=m.read_words(sp+4,1)[0]
  if address==0x4f63ec:result=allocate(None,arg)
  else:free(None,arg);result=0
  returned(0,result);return
 if address not in STUBS and address not in EXTERNAL:return
 f=STUBS.get(address,address);n=IMPORTS[f]if address in STUBS else EXTERNAL[f];args=m.read_words(sp+4,n)
 if f==0x4f777f:maps[P]=args[0]
 if f==0x546b00:maps[SEC]=args[3]
 if f==0x546af8:maps[COUNT]=args[3]
 args=tuple(normalize(t)for t in args);receiver=0 if address in STUBS or f in CDECL else normalize(receiver)
 events.append((f,receiver,args,snapshot(),tuple(get(SEC,3))if f==0x546b00 else tuple(get(COUNT))if f==0x546af8 else ()))
 if f in(0x4a3040,0x4a3050,0x4f6584):return # complete original RNG/release instructions execute
 try:result=effect(f,receiver,args)
 except StopIteration:sourceHalt=True;uc.emu_stop();return
 returned(0 if f in(0x4a3040,0x4a3050)else n*4,result)
u.hook_add(UC_HOOK_CODE,hook)

def originalCall(f,t,args):
 u.mem_write(m.stack,struct.pack('<'+'I'*(len(args)+1),m.stop,*args));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,t);u.emu_start(f,m.stop,count=10000000);assert u.reg_read(UC_X86_REG_EIP)==m.stop,('source did not return',hex(u.reg_read(UC_X86_REG_EIP)));return u.reg_read(UC_X86_REG_EAX)
def entry(f,t,args):
 aa=(U*len(args))(*args);out=U()
 if f in CP:
  g=CPGlobals();c=CPContext(ctx.scene,C.pointer(g),0,0,0,0,0);ok=lib.claw_checkpoint_entry(f,t,aa,len(args),C.byref(c),CPDependency(),None,C.byref(out));ctx.fault=c.fault;return ok,out.value
 ok=lib.claw_save_file_entry(f,t,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));return ok,out.value

def prepare(count=1,nodes=None):
 global native,events,freed,live,files,handles,cursor,openIndex,nextHandle,failOpen,failAllocate,writePolicy,closeFailure,mutation,maps,boundaries,sourceHalt,prefix
 native=True;events=[];freed=[];errors.clear();live={};files={b'CLAW.USR':b'OLD-SAVE'};handles={};cursor=openIndex=nextHandle=0;failOpen=None;failAllocate=False;writePolicy=0;closeFailure=False;mutation=0;maps={};boundaries={};sourceHalt=prefix=False;ctx.maximumTraversal=ctx.maximumSteps=0;ctx.fault=0
 C.memset(C.addressof(heap),0xa5,SIZE);put(M,[rng.getrandbits(32)for _ in range(22)]);assert lib.claw_save_file_initialize_manager(M,C.byref(ctx));put(STR,[1,8,8]);putBytes(STR+12,b'CLAW.USR\0');put(M+0x1c,[STR+12]);put(M+0xc,[count]);put(M+0x40,[2]);put(TLS+0x14,[rng.getrandbits(32)]);put(F,[0x510844,0xffffffff,0,ctx.emptyStringToken]);nodes=count if nodes is None else nodes
 put(M+4,[NODES if nodes else 0]);put(M+8,[NODES+(nodes-1)*16 if nodes else 0])
 for i in range(nodes):
  put(NODES+i*16,[NODES+(i+1)*16 if i+1<nodes else 0,NODES+(i-1)*16 if i else 0,RECORDS+i*0x3000]);put(RECORDS+i*0x3000,[0x50feac]+[rng.getrandbits(32)for _ in range(0x991)])
 put(DATA,[rng.getrandbits(32)for _ in range(64)]);u.mem_write(BASE,bytes(heap));u.mem_write(GS,globalSeed)

def state():return(freed[:],live.copy(),files.copy(),handles.copy(),cursor,openIndex,nextHandle,boundaries.copy())
def restore(s):
 global freed,live,files,handles,cursor,openIndex,nextHandle,boundaries
 freed,live,files,handles,cursor,openIndex,nextHandle,boundaries=s

def compare(f,t,args=(),label=None):
 global native,events,calls,eventCount,maps,currentRoot
 native=True;currentRoot=f;maps={};before=bytes(heap);old=state();events=[];ok,result=entry(f,t,args);assert ok,(hex(f),ctx.fault,label,errors);expected=canonical();ne=events[:];after=state();assert not errors,errors
 native=False;maps={};u.mem_write(BASE,before);u.mem_write(GS,globalSeed);restore(old);events=[]
 try:out=originalCall(f,t,args)
 except BaseException as error:raise AssertionError(('original',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events[-2:]))from error
 assert not sourceHalt and not errors
 if ne!=events:
  for i,(x,y)in enumerate(zip(ne,events)):
   if x!=y:print('FIRST SNAPSHOT',i,x[3],y[3],flush=True);break
  raise AssertionError(('events',hex(f),label,[(hex(x[0]),hex(x[1]),x[2])for x in ne],[(hex(x[0]),hex(x[1]),x[2])for x in events]))
 if expected!=canonical():
  b=canonical();diff=[(hex(BASE+i),expected[i:i+4].hex(),b[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=b[i:i+4]];raise AssertionError(('heap',hex(f),label,diff[:12]))
 assert bytes(u.mem_read(GS,GN))==globalSeed and state()==after,('globals/files/lifetime',hex(f),label)
 if f in(0x49bbc0,0x49bf70,0x49bfb0,0x49c000,0x4f72c9,0x4f7448,0x49a800,0x49a860,0x49ae60):assert out==result,('eax',hex(f),label,hex(out),hex(result))
 native=True;C.memmove(C.addressof(heap),expected,SIZE);maps={};calls+=1;eventCount+=len(ne);return result
