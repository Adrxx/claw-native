"""Private save reader oracle composed with frozen writer/list/RNG/cache bodies."""
from pathlib import Path
base=Path(__file__).with_name('save_file_runtime_helpers.py').read_text()
base=base.replace("WORK=ROOT/'work/save-file-agent'","WORK=ROOT/'work/save-load-agent'")
base=base.replace("'SaveFileRuntime','ActorDestruction'","'SaveLoadRuntime','AmbientAudioBackendRuntime','CRTRandomRuntime','SaveFileRuntime','ActorDestruction'")
base=base.replace('0x546af8:5}','0x546af8:5,0x546afc:5,0x546af4:4,0x546a28:2,0x546a2c:1,0x546a10:2,0x546a7c:1,0x546ab8:1}')
base=base.replace('if address==0x4a7dc0:returned(0,TLS);return','')
base=base.replace('u.hook_add(UC_HOOK_CODE,hook)','baseHook=u.hook_add(UC_HOOK_CODE,hook)')
exec(compile(base,str(Path(__file__).with_name('save_file_runtime_helpers.py')),'exec'),globals())
u.hook_del(baseHook)
DIR=BASE+0xb000;ALLOCBASE=BASE+0xb0000
class LoadContext(C.Structure):_fields_=[('save',Context),('directoryScratchToken',U),('maximumTraversal',U),('fault',U)]
LoadDependency=C.CFUNCTYPE(U,C.POINTER(LoadContext),C.POINTER(Call),C.c_void_p)
class RNGGlobals(C.Structure):_fields_=[('tlsIndex',U)]
class RNGContext(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(RNGGlobals)),('fault',U)]
class RNGCall(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*2)]
RNGDependency=C.CFUNCTYPE(U,C.POINTER(RNGContext),C.POINTER(RNGCall),C.c_void_p)
lib.claw_save_load_entry.argtypes=[U,U,UP,U,C.POINTER(LoadContext),LoadDependency,C.c_void_p,UP];lib.claw_save_load_entry.restype=U
lib.claw_crt_random_entry.argtypes=[U,UP,U,C.POINTER(RNGContext),RNGDependency,C.c_void_p,UP];lib.claw_crt_random_entry.restype=U
lc=LoadContext();rg=RNGGlobals(0);rc=RNGContext();SIZES[DIR]=260;lc.directoryScratchToken=DIR
allocCursor=0;allocCount=0;failAt=None;allocationSpans={};readPolicy=0;readIndex=0;currentDirectory=b'C:\\CLAW';windowsDirectory=b'C:\\WINDOWS';driveType=3;lastError=112;seekFailure=False;fileAlive=False;fileReleaseReturn=0
LOAD={0x49b840,0x49b9a0,0x49b950,0x49b970,0x49bdb0,0x49be50,0x49bee0,0x49bf30,0x49a5a0,0x49a6d0,0x49a8f0,0x49a990,0x49ad50,0x49adc0,0x4d5330,0x423f00,0x4f7570,0x4f75f5,0x4f774d}
EXTERNAL.update({0x4f4f58:4,0x4a3cf0:2});CDECL.update({0x4f4f58,0x4a3cf0})
seed=bytearray(globalSeed);struct.pack_into('<I',seed,0x52edd8-GS,0);globalSeed=bytes(seed);u.mem_write(GS,globalSeed);C.memmove(C.addressof(image)+0x52edd8-IS,struct.pack('<I',0),4)
baseCanonical=canonical;baseSnapshot=snapshot;baseEffect=effect;baseEntry=entry;basePrepare=prepare;baseState=state;baseRestore=restore;baseCompare=compare

def canonical():
 b=bytearray(baseCanonical());b[DIR-BASE:DIR-BASE+260]=bytes(260)
 if currentRoot in(0x49b840,0x49b9a0,0x49bbc0)and not fileAlive:b[F-BASE:F-BASE+16]=bytes(16)
 return bytes(b)
def snapshot():return baseSnapshot()+(allocCursor,allocCount,tuple(sorted(allocationSpans.items())),readIndex,lastError)
@Lookup
def loadLookup(_,t,n):
 if ALLOCBASE<=t<BASE+SIZE:
  for start,size in allocationSpans.items():
   if start<=t<start+size:return C.addressof(heap)+t-BASE if t+n*4<=start+size else None
  return None
 if BUFFER<=t<BUFFER+0x40000:return C.addressof(heap)+t-BASE if t+n*4<=BASE+SIZE else None
 return lookup(None,t,n)
@ByteLookup
def loadBytes(_,t,n):
 if ALLOCBASE<=t<BASE+SIZE:
  for start,size in allocationSpans.items():
   if start<=t<start+size:return C.addressof(heap)+t-BASE if t+n<=start+size else None
  return None
 if BUFFER<=t<BUFFER+0x40000:return C.addressof(heap)+t-BASE if t+n<=BASE+SIZE else None
 return byteLookup(None,t,n)
@Allocate
def loadAllocate(_,n):
 global allocCursor,allocCount
 events.append((0x4f63ec,0,(n,),snapshot()));index=allocCount;allocCount+=1
 if failAllocate or index==failAt:return 0
 token=ALLOCBASE+allocCursor;allocCursor+=(n+15)&~15;assert ALLOCBASE+allocCursor<BASE+SIZE
 allocationSpans[token]=n;live[token]=True;return token
ctx.scene.lookup=loadLookup;ctx.scene.allocate=loadAllocate;ctx.lookupBytes=loadBytes;rc.host=ctx.scene;rc.globals=C.pointer(rg)
@RNGDependency
def rngDependency(c,e,_):
 q=e.contents;args=tuple(q.arguments[:q.argumentCount]);events.append((q.function,0,args,snapshot(),()))
 return effect(q.function,0,args)

def effect(f,t,args):
 global readIndex,lastError,fileAlive
 if f==0x4f777f:fileAlive=True
 if f in(0x4a3040,0x4a3050):
  if not native:return 0
  rc.fault=0;out=U();aa=(U*len(args))(*args);assert lib.claw_crt_random_entry(f,aa,len(args),C.byref(rc),rngDependency,None,C.byref(out));return out.value
 if f==0x546a7c:return TLS
 if f==0x546ab8:lastError=args[0];return 0
 if f==0x546b0c:return lastError
 if f==0x4a3cf0:
  a,b=text(args[0]).lower(),text(args[1]).lower();return(int(a>b)-int(a<b))&0xffffffff
 if f==0x546a28:putBytes(args[1],(currentDirectory+b'\0').ljust(254,b'\0'));return len(currentDirectory)if currentDirectory else 0
 if f==0x546a10:putBytes(args[0],(windowsDirectory+b'\0').ljust(254,b'\0'));return len(windowsDirectory)if windowsDirectory else 0
 if f==0x546a2c:return driveType
 if f==0x4f4f58:
  assert text(args[1])==b'%s\\%s';full=text(args[2])+b'\\'+text(args[3])
  # CString formatting is a declared result with ordinary assign ownership.
  putBytes(P,full+b'\0');return baseEffect(0x4f66cc,args[0],[P])
 if f==0x546af4:
  handle,distance,_,origin=args
  if seekFailure:return 0xffffffff
  name,pos,access=handles[handle];delta=distance if distance<0x80000000 else distance-0x100000000;value=(pos if origin==1 else len(files[name])if origin==2 else 0)+delta;handles[handle]=(name,value,access);return value&0xffffffff
 if f==0x546afc:
  handle,data,size,out,_=args;name,pos,access=handles[handle];amount=min(size,max(0,len(files[name])-pos));index=readIndex;readIndex+=1
  if readPolicy==1:amount=0
  elif readPolicy==2:amount=min(amount,7)
  elif readPolicy==3 and index==1:amount=min(amount,amount//2)
  putBytes(data,files[name][pos:pos+amount]);put(out,[amount]);handles[handle]=(name,pos+amount,access);return 0 if readPolicy==4 else 1
 return baseEffect(f,t,args)
@LoadDependency
def loadDependency(c,e,_):
 global fileAlive
 q=e.contents;args=tuple(q.arguments[:q.argumentCount])
 if q.function==0x4f777f:fileAlive=True
 scope=tuple(get(SEC,3))if q.function==0x546b00 else tuple(get(COUNT))if q.function in(0x546af8,0x546afc)else tuple(text(DIR))if q.function==0x546a2c else()
 events.append((q.function,q.receiver,args,snapshot(),scope))
 try:
  result=effect(q.function,q.receiver,args)
  if q.function==0x4f6584 and q.receiver==F+12:fileAlive=False
  if ctx.fault:c.contents.fault=ctx.fault
  return result
 except BaseException as error:errors.append(error);return 0
# Direct frozen writer calls also compose the same actual thread RNG.
@Dependency
def dependency(c,e,_):
 global fileAlive
 q=e.contents;args=tuple(q.arguments[:q.argumentCount])
 if q.function==0x4f777f:fileAlive=True
 events.append((q.function,q.receiver,args,snapshot(),tuple(get(SEC,3))if q.function==0x546b00 else tuple(get(COUNT))if q.function==0x546af8 else()))
 try:
  if q.function==0x4f777f:fileAlive=True
  result=effect(q.function,q.receiver,args)
  if q.function==0x4f6584 and q.receiver==F+12:fileAlive=False
  return result
 except BaseException as error:errors.append(error);return 0

def entry(f,t,args):
 ctx.fault=0
 if f not in LOAD:return baseEntry(f,t,args)
 lc.save=ctx;lc.fault=0;out=U();aa=(U*len(args))(*args);ok=lib.claw_save_load_entry(f,t,aa,len(args),C.byref(lc),loadDependency,None,C.byref(out));ctx.fault=lc.fault;return ok,out.value

def loadHook(uc,address,size,_):
 global sourceHalt,fileAlive,fileReleaseReturn
 if address==fileReleaseReturn:fileAlive=False;fileReleaseReturn=0
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f72c9 and currentRoot in(0x49b9a0,0x49b840):maps[F]=receiver;fileAlive=True
 if address==0x4f72c9 and currentRoot==0x49bbc0:maps[F]=receiver;fileAlive=True
 if address in(0x4f63ec,0x4f6428):
  arg=m.read_words(sp+4,1)[0]
  if address==0x4f63ec:result=loadAllocate(None,arg)
  else:free(None,arg);result=0
  returned(0,result);return
 if address==DEC:
  t=m.read_words(sp+4,1)[0];value=(get(t)[0]-1)&0xffffffff;put(t,[value]);returned(4,value);return
 if address not in STUBS and address not in EXTERNAL:return
 f=STUBS.get(address,address);n=IMPORTS[f]if address in STUBS else EXTERNAL[f];args=m.read_words(sp+4,n)
 if f==0x4f777f:maps[P]=args[0]
 if f==0x546b00:maps[SEC]=args[3]
 if f in(0x546af8,0x546afc):maps[COUNT]=args[3]
 if f==0x546a28:maps[DIR]=args[1]
 if f==0x546a10:maps[DIR]=args[0]
 args=tuple(normalize(x)for x in args);receiver=0 if address in STUBS or f in CDECL else normalize(receiver)
 scope=tuple(get(SEC,3))if f==0x546b00 else tuple(get(COUNT))if f in(0x546af8,0x546afc)else tuple(text(DIR))if f==0x546a2c else();events.append((f,receiver,args,snapshot(),scope))
 if f==0x4f6584 and receiver==F+12:fileReleaseReturn=m.read_words(sp,1)[0]
 if f in(0x4a3040,0x4a3050,0x4f6584,0x4a3cf0):return
 try:result=effect(f,receiver,args)
 except StopIteration:sourceHalt=True;uc.emu_stop();return
 returned(0 if f in(0x4a3040,0x4a3050,0x4a3cf0,0x4f4f58)else n*4,result)
u.hook_add(UC_HOOK_CODE,loadHook)

def prepare(count=0,nodes=None):
 global allocCursor,allocCount,failAt,allocationSpans,readPolicy,readIndex,currentDirectory,windowsDirectory,driveType,lastError,seekFailure,fileAlive,fileReleaseReturn
 basePrepare(count,nodes);allocCursor=allocCount=0;failAt=None;allocationSpans={};readPolicy=readIndex=0;fileAlive=False;fileReleaseReturn=0;currentDirectory=b'C:\\CLAW';windowsDirectory=b'C:\\WINDOWS';driveType=3;lastError=112;seekFailure=False;ctx.scene.allocate=loadAllocate;ctx.scene.lookup=loadLookup;ctx.lookupBytes=loadBytes;rg.tlsIndex=0;rc.host=ctx.scene
 # Raw source name/header gate prepared independently; empty manager may boot.
 if count==0:put(M+4,[0]);put(M+8,[0]);put(M+0x10,[0]);put(M+0x14,[0])
 u.mem_write(BASE,bytes(heap));u.mem_write(GS,globalSeed)
def state():return baseState()+(allocCursor,allocCount,allocationSpans.copy(),readIndex,lastError)
def restore(s):
 global allocCursor,allocCount,allocationSpans,readIndex,lastError
 baseRestore(s[:8]);allocCursor,allocCount,allocationSpans,readIndex,lastError=s[8:]

def compare(f,t,args=(),label=None):
 # Reuse exact complete-buffer/service oracle, adding meaningful new EAX.
 global native,events,calls,eventCount,maps,currentRoot,fileAlive,fileReleaseReturn
 fileAlive=False;fileReleaseReturn=0
 native=True;currentRoot=f;maps={};before=bytes(heap);old=state();events=[];ok,result=entry(f,t,args);assert ok,(hex(f),ctx.fault,label,errors);expected=canonical();ne=events[:];after=state();assert not errors,errors
 native=False;maps={};fileAlive=False;fileReleaseReturn=0;u.mem_write(BASE,before);u.mem_write(GS,globalSeed);restore(old);events=[]
 try:out=originalCall(f,t,args)
 except BaseException as error:raise AssertionError(('original',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events[-3:]))from error
 if ne!=events:
  at=next((i for i,(a,b)in enumerate(zip(ne,events))if a!=b),None);raise AssertionError(('events',hex(f),label,'first',at,[(hex(e[0]),e[2])for e in ne],[(hex(e[0]),e[2])for e in events]))
 if expected!=canonical():
  b=canonical();diff=[(hex(BASE+i),expected[i:i+4].hex(),b[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=b[i:i+4]];raise AssertionError(('heap',hex(f),label,diff[:15]))
 assert state()==after and bytes(u.mem_read(GS,GN))==globalSeed,('state/globals',hex(f),label)
 if f not in(0x49b950,0x49b970,0x49bf30,0x49ad50,0x49adc0,0x423f00,0x49c030,0x49c070,0x4f7369,0x4f766e,0x4f650f,0x49a720):assert out==result,('eax',hex(f),label,hex(out),hex(result))
 native=True;C.memmove(C.addressof(heap),expected,SIZE);maps={};calls+=1;eventCount+=len(ne);return result
