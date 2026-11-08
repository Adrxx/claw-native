"""Private retained whole46aeb0 composition; original services remain explicit."""
from pathlib import Path
base=Path(__file__).with_name('single_player_scene_helpers.py').read_text()
base=base.replace("ROOT/'work/single-player-scene-agent'","ROOT/'work/world-startup-agent'")
start=base.index('subprocess.run(');end=base.index(',check=True)',start)+len(',check=True)');base=base[:start]+'pass # Library compiled by private player-startup helper.'+base[end:]
base=base.replace('libSinglePlayerSceneRuntime.dylib','libPlayerStartupRuntime.dylib').replace('u.hook_add(UC_HOOK_CODE,hook)','oldHook=u.hook_add(UC_HOOK_CODE,hook)')
exec(compile(base,str(Path(__file__).with_name('single_player_scene_helpers.py')),'exec'),globals())
u.hook_del(oldHook)
U=C.c_uint32;UP=C.POINTER(U);GS,GN=0x520000,0x30000
class StartupContext(C.Structure):_fields_=[('scene',Host),('singlePlayer',C.POINTER(Context))]+[(n,U)for n in('composeCache','composeCamera','maximumPlanes','fault')]
StartupDependency=C.CFUNCTYPE(U,C.POINTER(StartupContext),C.POINTER(Call),C.c_void_p)
class RNGGlobals(C.Structure):_fields_=[('tlsIndex',U)]
class RNGContext(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(RNGGlobals)),('fault',U)]
class RNGCall(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*2)]
RNGDependency=C.CFUNCTYPE(U,C.POINTER(RNGContext),C.POINTER(RNGCall),C.c_void_p)
lib.claw_player_startup_entry.argtypes=[U,U,UP,U,C.POINTER(StartupContext),StartupDependency,C.c_void_p,UP];lib.claw_player_startup_entry.restype=U
lib.claw_crt_random_entry.argtypes=[U,UP,U,C.POINTER(RNGContext),RNGDependency,C.c_void_p,UP]
TLS,RECORD,TABLE=BASE+0xf0000,BASE+0xf2000,BASE+0xf7000
PLANES=[BASE+0xf5000+i*0x800 for i in range(3)]
for i,slot in enumerate((0x546b0c,0x546a7c,0x546ab8)):
 fn=0x10e0300+i*16;REV[fn]=slot;m.write_words(slot,[fn])
seedRaw=bytes(u.mem_read(GS,GN));raw=(C.c_uint8*GN).from_buffer_copy(seedRaw);lastError=112
baseSetup=setup;baseSnapshot=snapshot;baseEffect=effect;baseLoad=load
for f in(0x415ce0,0x46c790,0x46d8e0,0x4a3040):META.pop(f)
META.update({0x546b0c:(0,0,0,False,True),0x546a7c:(1,1,0,False,True),0x546ab8:(1,1,0,False,True)})

def rawPut(t,v):
 if native:(U*len(v)).from_address(C.addressof(raw)+t-GS)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def rawGet(t,n=1):return list((U*n).from_address(C.addressof(raw)+t-GS))if native else m.read_words(t,n)
def snapshot():
 if native:
  for a,v in zip(GADDR,gv()):rawPut(a,[v])
  for a,v in zip(CADDR,cg()):rawPut(a,[v])
  C.memmove(C.addressof(raw)+0x543108-GS,imageFX,100);C.memmove(C.addressof(raw)+0x541328-GS,clockWords,20)
 return baseSnapshot()+(bytes(raw)if native else bytes(u.mem_read(GS,GN)))+struct.pack('<I',lastError)
@Lookup
def rawLookup(_,t,n):
 if GS<=t and t+n*4<=GS+GN:return C.addressof(raw)+t-GS
 return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
# SinglePlayer constructors still use their exact fixed scratch/global views;
# the new raw player module and its frozen camera/cache dependencies use rawLookup.
startupHost=Host(None,rawLookup,allocateHost,freeHost,invokeHost,readClock)
startup=StartupContext(startupHost,C.pointer(context),1,1,65536,0);rg=RNGGlobals(0);rc=RNGContext(startupHost,C.pointer(rg),0)
@RNGDependency
def rngDependency(c,e,_):q=e.contents;return effect(q.function,0,list(q.arguments[:q.argumentCount]),[])

def effect(fn,receiver,args,buffers):
 global lastError
 if fn==0x4a3040:
  assert native;out=U();aa=(U*len(args))(*args);rc.fault=0;assert lib.claw_crt_random_entry(fn,aa,len(args),C.byref(rc),rngDependency,None,C.byref(out));return out.value
 if fn in(0x546b0c,0x546a7c,0x546ab8):
  events.append(((fn,0,tuple(args),()),snapshot()))
  if fn==0x546b0c:return lastError
  if fn==0x546a7c:return TLS
  lastError=args[0];return 0
 value=baseEffect(fn,receiver,args,buffers)
 if fn in(WLOAD,WLOADFILE,0x4cb5a0,0x4cb470):put(receiver+0x5c,[PLANES[1]])
 return value
@StartupDependency
def startupDependency(c,e,_):
 try:q=e.contents;return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]),list(q.buffers[:q.bufferCount]))
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0
u.hook_add(UC_HOOK_CODE,hook)
def fword(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def setup(seed=0,saved=False):
 global lastError
 baseSetup(seed,saved);C.memmove(raw,seedRaw,GN);lastError=112
 put(TLS,[0]*29);put(TLS+0x14,[seed^0xdeadbeef]);rawPut(0x52edd8,[0]);rawPut(0x53725c,[seed%2]);rawPut(0x52c6e4,[seed*997]);put(MGR+0x64,[RECORD]);put(MGR+0xa8,[1]);put(MGR+0xd8,[seed%3]);put(RECORD,[0]*2450)
 for k in(1,2,3):
  for level in range(15):
   t=RECORD+{1:0x2d4,2:0xd24,3:0x1774}[k]+level*0xb0;put(t,[2,720+level*97,4720-level*31,0,1234567+level,seed]+[seed+i for i in range(38)])
 put(WORLD+0x38,[TABLE,3]);put(WORLD+0x5c,[0,1]);put(TABLE,PLANES)
 for i,p in enumerate(PLANES):
  put(p,[0]*86);put(p+8,[1 if i==1 else 0]);put(p+0x18,[fword([.125,1,1.75][i]),fword([.5,1,1.25][i])]);put(p+0x30,[24576,6144]);put(p+0x70,[640,480,320,240]);put(p+0x84,[320,240])
 startup.fault=0;snapshot()
def execute(args):
 global calls,eventCount
 events.clear();errors.clear()
 if native:
  out=U();aa=(U*len(args))(*args);assert lib.claw_player_startup_entry(0x46aeb0,OWNER,aa,len(args),C.byref(startup),startupDependency,None,C.byref(out));ret=out.value;assert not startup.fault,startup.fault;assert not errors,errors
 else:ret=m.call(0x46aeb0,OWNER,struct.pack('<2I',*args));assert u.reg_read(UC_X86_REG_ESP)==m.stack+12
 calls+=1;eventCount+=len(events);return snapshot(),list(events),ret,gateIndex,cursorIndex

def compare(args):
 global native,lastError,nextAllocation,allocationCount,gateIndex,cursorIndex
 native=True;initial=snapshot();allocation=(nextAllocation,allocationCount);savedError=lastError;gateIndex=cursorIndex=0;a=execute(args);native=False;u.mem_write(BASE,initial[:SIZE]);u.mem_write(GS,initial[SIZE+252:SIZE+252+GN]);m.write_words(0,[0x12345678]);lastError=savedError;gateIndex=cursorIndex=0;nextAllocation,allocationCount=allocation;b=execute(args)
 if a!=b:
  diff=[(hex(i),a[0][i:i+4].hex(),b[0][i:i+4].hex())for i in range(0,len(a[0]),4)if a[0][i:i+4]!=b[0][i:i+4]];print('diff',diff[:12]);print('events',[(i,x[0],y[0],x[1]==y[1])for i,(x,y)in enumerate(zip(a[1],b[1]))if x!=y][:6]);print('results',a[2:],b[2:]);raise AssertionError('joined level')
 native=True;C.memmove(heap,a[0][:SIZE],SIZE);C.memmove(C.byref(globals),a[0][SIZE:SIZE+84],84);C.memmove(C.byref(camera),a[0][SIZE+84:SIZE+132],48);C.memmove(imageFX,a[0][SIZE+132:SIZE+232],100);C.memmove(clockWords,a[0][SIZE+232:SIZE+252],20);C.memmove(raw,a[0][SIZE+252:SIZE+252+GN],GN);lastError=struct.unpack('<I',a[0][-4:])[0];return a
