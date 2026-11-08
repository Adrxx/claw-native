"""Private save reader oracle composed with frozen writer/list/RNG/cache bodies."""
from pathlib import Path
base=Path(__file__).with_name('save_file_runtime_helpers.py').read_text()
base=base.replace("WORK=ROOT/'work/save-file-agent'","WORK=ROOT/'work/player-cache-application-agent'")
base=base.replace("'SaveFileRuntime','ActorDestruction'","'PlayerCacheApplicationRuntime','SaveLoadRuntime','AmbientAudioBackendRuntime','CRTRandomRuntime','SaveFileRuntime','ActorDestruction'")
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

# Additive application/selected-player oracle follows.
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
APP,FRAME,SCENE,HOLDER,SURFACE,SURFACECELL,VT,INPUT,PRIORNAME,AUTO=[BASE+0x20000+i*0x1000 for i in range(10)]
CONTROL=0x1234;DIALOG=0x5678;REFRESH=0x10fe000
class AppContext(C.Structure):_fields_=[('scene',Host),('saveLoad',C.c_void_p)]+[(n,U)for n in('automaticToken','composeSaveLoad','maximumOperations','fault')]
class RichCall(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_char_p),('mask',U),('buffersCount',U),('buffers',C.c_void_p*3),('sizes',U*3)]
AppDependency=C.CFUNCTYPE(U,C.POINTER(AppContext),C.POINTER(RichCall),C.c_void_p)
lib.claw_player_cache_application_entry.argtypes=[U,U,UP,U,C.POINTER(AppContext),AppDependency,C.c_void_p,UP]
lib.claw_player_cache_application_startup_span.argtypes=[U,U,C.POINTER(AppContext),AppDependency,C.c_void_p,UP]
ac=AppContext();ac.saveLoad=C.addressof(lc);ac.automaticToken=AUTO;ac.maximumOperations=65536
# Source automatic projections in the same declared buffer oracle, not extra
# source heap allocations. The actual source addresses are normalized per call.
for token,size in[(PRIORNAME,32),(AUTO,100),(AUTO+100,100),(AUTO+200,100),(AUTO+300,4)]:SIZES[token]=size
oldPutBytes=putBytes

def putBytes(t,b):
 if native and GS<=t<t+len(b)<=GS+GN:C.memmove(C.addressof(image)+t-IS,b,len(b))
 else:oldPutBytes(t,b)

def snapshot():return(hashlib.sha256(canonical()).digest(),hashlib.sha256(bytes(image[GS-IS:GS-IS+GN])if native else bytes(u.mem_read(GS,GN))).digest(),tuple(freed),tuple(sorted(live.items())),tuple(sorted(files.items())),tuple(sorted(handles.items())),cursor,openIndex,nextHandle,allocCursor,allocCount,tuple(sorted(allocationSpans.items())),readIndex,lastError)
APP_ENTRIES={0x42bf90,0x430ac0,0x42bbb0,0x42bbd0,0x42bbe0,0x42bbf0,0x42bb00,0x49b050,0x49b0c0,0x49c090,0x49b730}
ARITY={0x42bf90:1,0x430ac0:1,0x42bb00:2,0x49b050:1,0x49b0c0:1,0x49c090:3,0x49b730:4}
EXTERNAL.update({0x4b5e90:4,0x4b5f80:1,0x429e10:2,0x42abf0:0,0x4ca9e0:1,REFRESH:1,0x546d50:4,0x546d54:1,0x546d2c:5,0x546d40:2,0x546d34:2,0x546d3c:3,0x546d44:4})
CDECL.update({REFRESH,0x546d50,0x546d54,0x546d2c,0x546d40,0x546d34,0x546d3c,0x546d44})
# Keep source imports mapped to unique fixture slots while retaining real IAT
# identities in every recorded event. No registry/window API is executed.
for i,slot in enumerate(sorted(set(EXTERNAL)&set(CDECL)-{0x4f777f,0x4fc384,0x4fc242,0x4fc303,0x4a3040,0x4a3050,0x4f4f58,0x4a3cf0,REFRESH})):
 if slot>=0x546000:
  address=STUB+0x400+i*16;STUBS[address]=slot;IMPORTS[slot]=EXTERNAL[slot];m.write_words(slot,[address]);C.memmove(C.addressof(image)+slot-IS,struct.pack('<I',address),4);u.mem_write(address,b'\xc3')
globalSeed=bytes(image[GS-IS:GS-IS+GN])
registry={};removed=[];posted=[];cursorValues=[0,0,0xffffffff];cursorIndex=0;dialogResult=0;listNames=[];listIndex=0xffffffff;listTextFailure=False;listAddFailure=False;controlResult=CONTROL;mutations={};sourceSpan=False;sourceJoined=False
oldEffect=effect

def effect(f,t,args):
 global cursorIndex,listNames,listIndex
 if f==0x4b5e90:
  key=args[0];value=registry.get(key,b'');putBytes(args[1],value+b'\0');put(args[2],[len(value)+1]);return bool(value)
 if f==0x4b5f80:removed.append(args[0]);registry.pop(args[0],None);return 1
 if f==0x546d50:posted.append(tuple(args));return 1
 if f==0x546d54:value=cursorValues[cursorIndex%len(cursorValues)];cursorIndex+=1;return value
 if f==0x546d2c:return dialogResult
 if f==0x546d40:return controlResult
 if f in(0x546d34,0x546d3c,0x429e10,0x42abf0,0x4ca9e0,REFRESH):return 1
 if f==0x546d44:
  handle,msg,wparam,lparam=args
  if msg==0x184:listNames=[];listIndex=0xffffffff;return 0
  if msg==0x180:
   if listAddFailure:return 0xffffffff
   listNames.append(text(lparam));return len(listNames)-1
  if msg==399:
   value=text(lparam);return listNames.index(value)if value in listNames else 0xffffffff
  if msg==0x186:listIndex=wparam;return 0
  if msg==0x188:return listIndex
  if msg==0x189:
   if listTextFailure or listIndex>=len(listNames):return 0xffffffff
   value=listNames[listIndex];putBytes(lparam,value+b'\0');return len(value)
 for address,value in mutations.get(f,[]):put(address,[value])
 return oldEffect(f,t,args)
# Need callback mutations after the elected service body, exactly as source.
baseAppEffect=effect

def effect(f,t,args):
 value=baseAppEffect(f,t,args)
 for address,v in mutations.get(f,[]):put(address,[v])
 return value

@AppDependency
def appDependency(c,e,_):
 global fileAlive
 q=e.contents;args=list(q.arguments[:q.count]);buffers=[C.string_at(q.buffers[i],q.sizes[i])for i in range(q.buffersCount)]
 if q.function==0x4f777f:fileAlive=True
 if q.function==0x4f63ec:return loadAllocate(None,args[0])
 if q.function==0x4f6428:free(None,args[0]);return 0
 if q.mask==8:
  assert q.function==0x546d44;args[3]=AUTO;putBytes(AUTO,buffers[0])
 args=tuple(args);scope=tuple(get(SEC,3))if q.function==0x546b00 else tuple(get(COUNT))if q.function in(0x546af8,0x546afc)else tuple(text(DIR))if q.function==0x546a2c else()
 events.append((q.function,q.receiver,args,snapshot(),scope))
 try:
  value=effect(q.function,q.receiver,args)
  if q.function==0x4f6584 and q.receiver==F+12:fileAlive=False
  if q.mask==8:C.memmove(q.buffers[0],C.addressof(heap)+AUTO-BASE,q.sizes[0])
  return value
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0
# Original hooks compose actual Save/Load/List/CRT bodies unchanged. Add only
# physical registry/window/scene boundaries; no gameplay body is stubbed here.
oldLoadHook=loadHook
# Registered callback points at the original function object, so code replace
# avoids double handling. A new callback delegates explicitly when necessary.
def inactiveHook(uc,address,size,_):pass
oldLoadHook.__code__=inactiveHook.__code__
# Recover unmodified hook code from immutable shared text in a private function.
sourceCode=Path(__file__).with_name('save_load_runtime_helpers.py').read_text();begin=sourceCode.index('def loadHook(');end=sourceCode.index('u.hook_add(UC_HOOK_CODE,loadHook)',begin);exec(sourceCode[begin:end].replace('def loadHook(','def savedLoadHook('),globals())

def appHook(uc,address,size,_):
 global sourceJoined
 if sourceSpan and address in(0x4266e0,0x426886):sourceJoined=address==0x4266e0;uc.emu_stop();return
 f=STUBS.get(address,address)
 if f==0x4b5e90:
  sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,4);row={0x52560c:AUTO,0x5255fc:AUTO+100,0x5255f0:AUTO+200}[args[0]];maps[row]=args[1];maps[AUTO+300]=args[2]
 if f==0x49bee0 and sourceSpan:
  arg=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)[0]
  if m.stack-0x1000<arg<m.stack+0x1000 and not any(p==arg for p in maps.values()):maps[PRIORNAME]=arg
 if f==0x546d44:
  args=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,4)
  if args[1]==0x189:maps[AUTO]=args[3]
 savedLoadHook(uc,address,size,_)
u.hook_add(UC_HOOK_CODE,appHook)
# Make savedLoadHook resolve current shared globals; its globals mapping was a
# copy, so refresh references before each oracle invocation.
def syncHook():savedLoadHook.__globals__.update(globals())
oldPrepare=prepare

def prepare(count=0,nodes=None):
 global registry,removed,posted,cursorIndex,cursorValues,dialogResult,listNames,listIndex,listTextFailure,listAddFailure,controlResult,mutations,sourceSpan,sourceJoined
 oldPrepare(count,nodes);lc.save=ctx;ac.scene=ctx.scene;ac.composeSaveLoad=1;ac.fault=0;put(APP,[0x50bee4,FRAME,FRAME]);put(FRAME+4,[0x1122]);put(FRAME+12,[0x3344]);put(APP+0x30,[SCENE]);put(APP+0x38,[M]);put(APP+0x60,[M,RECORDS]);put(SCENE+4,[HOLDER]);put(HOLDER+20,[1]);put(SCENE+28,[SURFACECELL]);put(SURFACECELL,[SURFACE]);put(SURFACE,[VT]);put(VT+40,[REFRESH]);put(0x5371fc,[APP]);put(0x537204,[INPUT]);put(0x53725c,[1]);put(0x53ebe0,[0]);put(0x53ebec,[CONTROL]);putBytes(PRIORNAME,bytes(32));putBytes(AUTO,bytes(304));registry={};removed=[];posted=[];cursorIndex=0;cursorValues=[0,0,0xffffffff];dialogResult=0;listNames=[];listIndex=0xffffffff;listTextFailure=listAddFailure=False;controlResult=CONTROL;mutations={};sourceSpan=sourceJoined=False

def extraState():return(registry.copy(),removed[:],posted[:],cursorIndex,listNames[:],listIndex)
def extraRestore(v):
 global registry,removed,posted,cursorIndex,listNames,listIndex
 registry,removed,posted,cursorIndex,listNames,listIndex=v

def compareApp(f,t,args=(),label='',span=False):
 global native,events,maps,currentRoot,calls,eventCount,sourceSpan,sourceJoined
 native=True;currentRoot=0x49b840 if span else f;maps={};events=[];errors.clear();ac.fault=0;before=bytes(heap);bi=bytes(image);old=state();oldExtra=extraState();out=U();aa=(U*len(args))(*args)
 if span:ok=lib.claw_player_cache_application_startup_span(t,args[0],C.byref(ac),appDependency,None,C.byref(out))
 else:ok=lib.claw_player_cache_application_entry(f,t,aa,len(args),C.byref(ac),appDependency,None,C.byref(out))
 assert ok and not ac.fault and not errors,('native',hex(f),label,ac.fault,errors)
 expected=canonical();eg=bytes(image[GS-IS:GS-IS+GN]);ne=list(events);after=state();afterExtra=extraState();native=False;maps={};u.mem_write(BASE,before);u.mem_write(GS,bi[GS-IS:GS-IS+GN]);restore(old);extraRestore(oldExtra);events=[];syncHook();u.mem_write(m.stack-0x1000,bytes(0x2000));sourceSpan=span;sourceJoined=False
 if span:
  sp=m.stack;u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EBP,t);u.reg_write(UC_X86_REG_ESI,0);u.mem_write(sp+0x44,readBytes(args[0],32));maps[PRIORNAME]=sp+0x44;u.emu_start(0x426546,0x426886,count=1000000);value=int(sourceJoined)
 else:
  value=m.call(f,t,struct.pack('<'+'I'*len(args),*args));pop=0 if f in(0x49b050,0x49b0c0)else len(args)*4;assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+pop
 if ne!=events:raise AssertionError(('events',hex(f),label,len(ne),len(events),next(((i,a,b)for i,(a,b)in enumerate(zip(ne,events))if a!=b),None)))
 if expected!=canonical():
  got=canonical();raise AssertionError(('heap',hex(f),label,[(hex(BASE+i),expected[i:i+4].hex(),got[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=got[i:i+4]][:20]))
 assert eg==bytes(u.mem_read(GS,GN)),('globals',hex(f),label)
 assert state()==after and extraState()==afterExtra,('ownership',hex(f),label)
 if f not in(0x42bf90,0x42bbb0,0x42bbd0,0x42bbe0,0x42bbf0)or span:assert out.value==value,('eax',hex(f),label,out.value,value)
 native=True;C.memmove(C.addressof(heap),expected,SIZE);C.memmove(C.addressof(image)+GS-IS,eg,GN);restore(after);extraRestore(afterExtra);maps={};sourceSpan=False;calls+=1;eventCount+=len(ne);return out.value

class UnsafePrefix(Exception):pass
def nullRead(uc,access,address,size,value,_):
 if address<4096 and bytes(uc.mem_read(uc.reg_read(UC_X86_REG_EIP),1))!=b'\x64':raise UnsafePrefix((hex(uc.reg_read(UC_X86_REG_EIP)),address,size))
u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,nullRead)
def unsafeAllocation(index):
 global native,maps,currentRoot,events,sourceSpan
 prepare();files.clear();failAtOld=index
 globals()['failAt']=failAtOld;native=True;currentRoot=0x49b840;before=bytes(heap);bi=bytes(image);old=state();x=extraState();events=[];out=U();ok=lib.claw_player_cache_application_startup_span(APP,PRIORNAME,C.byref(ac),appDependency,None,C.byref(out));assert not ok and ac.fault==2;expected=canonical();eg=bytes(image[GS-IS:GS-IS+GN]);ne=list(events);after=state();native=False;maps={};events=[];u.mem_write(BASE,before);u.mem_write(GS,bi[GS-IS:GS-IS+GN]);restore(old);extraRestore(x);syncHook();u.mem_write(m.stack-0x1000,bytes(0x2000));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_EBP,APP);u.reg_write(UC_X86_REG_ESI,0);u.mem_write(m.stack+0x44,bytes(32));maps[PRIORNAME]=m.stack+0x44;sourceSpan=True
 try:u.emu_start(0x426546,0x426886,count=1000000)
 except UnsafePrefix:pass
 else:raise AssertionError('expected original null allocation prefix')
 assert canonical()==expected and bytes(u.mem_read(GS,GN))==eg and events==ne and state()==after
 native=True;sourceSpan=False
