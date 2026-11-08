"""Pinned unchanged-original config message draw oracle and explicit GDI/storage transports."""
import ctypes as C,struct,random,json,subprocess,hashlib,io
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/message-drawing-agent';U=C.c_uint32;UP=C.POINTER(U)
SOURCES=['MessageDrawingRuntime','GameFrameServices','PlayerDeathServices','ActorDestruction','PlayerStartupRuntime','SinglePlayerSceneRuntime','WorldFileRuntime','WorldPlaneRuntime','CArrayRuntime','SceneCameraRuntime','SpatialGridRuntime','SpriteGeometry','SceneActorRuntime','WorldObjectRuntime','GameTiming','PlayerLocomotion','PlayerAirStates','PlayerInitialization','PlayerEngine','PlayerPhysics','CollisionResponse','TileCollision','CheckpointLogicRuntime','ActorAnimationRuntime','AnimationEngine','AnimationOperations','AudioEvents','ActorResourceBindings','CRTRandomRuntime','WorldLootRuntime','AmbientAudioBackendRuntime']
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in SOURCES],'-o',str(WORK/'libMessageDrawingRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',C.c_void_p*4),('bufferBytes',U*4)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('emptyStringToken','composeStrings','textLimit','fault')]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),Call,C.c_void_p)
class FrameGlobals(C.Structure):_fields_=[('values',U*20)]
class FrameContext(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(FrameGlobals)),('composeMessages',U),('fault',U)]
FrameDep=C.CFUNCTYPE(U,C.POINTER(FrameContext),Call,C.c_void_p)
class StartupCall(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',C.c_void_p*3),('bufferBytes',U*3)]
class StartupContext(C.Structure):_fields_=[('scene',Host),('singlePlayer',C.c_void_p)]+[(n,U)for n in('composeCache','composeCamera','maximumPlanes','fault')]
StartupDep=C.CFUNCTYPE(U,C.POINTER(StartupContext),C.POINTER(StartupCall),C.c_void_p)
lib=C.CDLL(str(WORK/'libMessageDrawingRuntime.dylib'));lib.claw_message_drawing_entry.argtypes=[U,U,UP,U,UP,C.POINTER(Context),Dep,C.c_void_p,UP];lib.claw_message_drawing_defaults.argtypes=[C.POINTER(Context)];lib.claw_game_frame_service_entry.argtypes=[U,U,U,C.POINTER(FrameContext),FrameDep,C.c_void_p,UP];lib.claw_player_startup_entry.argtypes=[U,U,UP,U,C.POINTER(StartupContext),StartupDep,C.c_void_p,UP]
BASE,SIZE,GS,GN=0x3000000,0x20000,0x520000,0x30000
CONFIG,NODES,RECT,STRINGS,OWNER,APP,ALLOCATED=BASE+0x1000,BASE+0x2000,BASE+0x5000,BASE+0x6000,BASE+0x9000,BASE+0xa000,BASE+0x10000
RSTACK=0x2006000;SELECT,DRAW,CREATE,INCREMENT,DECREMENT=0x10ff400,0x10ff410,0x10ff420,0x10ff430,0x10ff440
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();start,end,_=next(r for r in m.u.mem_regions()if r[0]==0x400000);image=(C.c_uint8*(end-start+1)).from_buffer_copy(bytes(m.u.mem_read(start,end-start+1)));heap=(C.c_uint8*SIZE)();seedImage=bytes(image);rect=(U*4)();c=Context();fg=FrameGlobals();fc=FrameContext();sc=StartupContext();rng=random.Random(0x4226b0)
original_events=[];native_events=[];errors=[];calls=eventCount=0;oldFont=0xabcddcba;drawResult=64;mutation=0;selectCount=0;storageCount=0;freeCount=0;allocCount=0;fontResult=0x13571357;modeLocal=False;frameMode=False;tape=[];replay=io.BytesIO();replayCases=0

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def pointer(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if start<=t and t+n*4<=end+1:return C.addressof(image)+t-start
 return 0

def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(pointer(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(pointer(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def data(t,b,native=True):
 if native:C.memmove(pointer(t,(len(b)+3)//4),b,len(b))
 else:m.u.mem_write(t,b)
def string(t,native=True):
 out=bytearray()
 for i in range(65536):
  ch=C.string_at(pointer((t+i)&~3),4)[(t+i)&3]if native else m.u.mem_read(t+i,1)[0]
  if not ch:return bytes(out)
  out.append(ch)
 raise AssertionError('unbounded source string fixture')
@Lookup
def lookup(_,t,n):
 p=pointer(t,n)
 if not p:errors.append(('span',hex(t),n))
 return p
host=Host(None,lookup,Alloc(),Free(),Invoke(),Clock());c.scene=fc.host=sc.scene=host;fc.globals=C.pointer(fg)

def flush():
 put(0x53720c,[fg.values[0]]);put(0x5370c8,list(fg.values[4:8]))
def sync():
 flush();m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GS,C.string_at(pointer(GS),GN));m.u.mem_write(RSTACK,bytes(rect));m.write_words(0,[0x12345678]);m.u.mem_write(0x54691c,pack(SELECT));m.u.mem_write(0x546d30,pack(DRAW));m.u.mem_write(0x546918,pack(CREATE))
def raw(native):
 if native:flush();return bytes(heap)+C.string_at(pointer(GS),GN)+bytes(rect)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(GS,GN))+bytes(m.u.mem_read(RSTACK,16))
def normalize(e,native=True):
 return(e.function,e.receiver,tuple(e.arguments[:e.count]),e.localMask,tuple(C.string_at(e.buffers[i],e.bufferBytes[i])for i in range(e.bufferCount)),raw(native))

def effect(e,native=True):
 global selectCount,storageCount,freeCount,allocCount
 fn=e.function;args=list(e.arguments[:e.count]);local=e.localMask&256
 if fn==0x54691c:
  selectCount+=1
  if mutation==1 and selectCount==1:put(CONFIG+0x34,[0],native);data(0x534ef8,b'font-change\0',native)
  if mutation==2 and selectCount==1:put(CONFIG+12,[0],native)
  return oldFont if selectCount==1 else 0x11223344
 if fn==0x546d30:
  if e.localMask&8:
   p=e.buffers[0]
   if native:(U*4).from_address(p)[:]=[0xffffffff,0x80000000,321,123]
   else:m.u.mem_write(p,pack(0xffffffff,0x80000000,321,123))
  elif args[3]:put(args[3],[0xffffffff,0x80000000,321,123],native)
  if mutation==3:data(0x534ef8,b'DRAW changed\0',native);put(CONFIG+0x34,[0x99999999],native)
  return drawResult
 if fn==0x4f66cc:
  src=args[0];text=string(src,native);token=ALLOCATED+0x2000+storageCount*0x200;storageCount+=1;put(token-12,[1,len(text),len(text)],native);data(token,text+b'\0',native)
  if local:
   if native:U.from_address(e.buffers[0]).value=token
   else:put(e.buffers[0],[token],False)
  else:put(e.receiver,[token],native)
  if mutation==4:put(NODES,[0],native);put(CONFIG+12,[1],native);put(CONFIG+0x34,[0x24682468],native)
  return 0
 if fn==0x4f6428:freeCount+=1;return 0
 if fn==0x4f63ec:
  token=ALLOCATED+allocCount*0x1000;allocCount+=1;return token
 if fn==0x546918:return fontResult
 if fn==0x4f650f:put(e.receiver,[c.emptyStringToken],native);return 0
 if fn in(0x4f6449,0x4f6584):
  # Explicit CString transport for queue services/composition-off tests.
  def readCell(localIndex,token):return U.from_address(e.buffers[localIndex]).value if native else get(e.buffers[localIndex],native=False)[0]
  if fn==0x4f6449:
   source=readCell(0,0)if e.localMask&1 else get(args[0],native=native)[0];refs=get(source-12,native=native)[0];assert refs<0x80000000,'transport uses unlocked fixture only';put(source-12,[refs+1],native)
   if local:
    if native:U.from_address(e.buffers[e.bufferCount-1]).value=source
    else:put(e.buffers[e.bufferCount-1],[source],False)
   else:put(e.receiver,[source],native)
   return e.receiver
  token=readCell(0,0)if local else get(e.receiver,native=native)[0]
  if token!=c.emptyStringToken:refs=get(token-12,native=native)[0];put(token-12,[refs-1],native)
  return 0
 raise AssertionError(('transport',hex(fn),hex(e.receiver),args))
@Dep
def dependency(ctx,e,user):
 native_events.append(normalize(e));before=bytes(heap)
 try:
  result=effect(e);after=bytes(heap);patches=[];i=0
  while i<SIZE:
   if before[i]==after[i]:i+=1;continue
   first=i
   while i<SIZE and before[i]!=after[i]:i+=1
   patches.append((first,after[first:i]))
  tape.append((e.function,e.receiver,list(e.arguments[:e.count]),e.localMask,[C.string_at(e.buffers[i],e.bufferBytes[i])for i in range(e.bufferCount)],result,patches,C.string_at(pointer(GS),GN),bytes(rect)));return result
 except BaseException as ex:errors.append(ex);ctx.contents.fault=99;return 0
@StartupDep
def startupDependency(ctx,ev,user):
 q=ev.contents;e=Call();e.function=q.function;e.receiver=q.receiver;e.count=q.count;e.localMask=q.localMask;e.bufferCount=q.bufferCount;e.arguments[:]=q.arguments[:]
 for i in range(q.bufferCount):e.buffers[i]=q.buffers[i];e.bufferBytes[i]=q.bufferBytes[i]
 return dependency(C.pointer(c),e,user)
@FrameDep
def frameDependency(ctx,e,user):
 if e.function==0x4226b0:
  out=U();aa=(U*4)(*e.arguments[:4]);rr=C.cast(e.buffers[0],UP)if e.localMask&4 else None;done=lib.claw_message_drawing_entry(e.function,e.receiver,aa,4,rr,C.byref(c),dependency,None,C.byref(out));assert done and not c.fault;return out.value
 if e.function==0x4f53eb:
  # Frozen timer's outputCString is an automatic-storage pointer. Its queue
  # owner module accepts a raw token, so borrow a dedicated mapped local cell.
  temp=BASE+0x1f000;put(temp,[0]);args=(U*1)(temp);out=U();sc.fault=0;assert lib.claw_player_startup_entry(e.function,e.receiver,args,1,C.byref(sc),startupDependency,None,C.byref(out))and not sc.fault;U.from_address(e.buffers[0]).value=get(temp)[0];return 0
 return dependency(C.pointer(c),e,user)

def returned(pop,result=0):
 sp=m.u.reg_read(UC_X86_REG_ESP);ret=get(sp,native=False)[0];m.u.reg_write(UC_X86_REG_EAX,result&0xffffffff);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop);m.u.reg_write(UC_X86_REG_EIP,ret)
def hook(u,address,size,user):
 global selectCount,sourceStopped
 sp=u.reg_read(UC_X86_REG_ESP);e=Call();receiver=u.reg_read(UC_X86_REG_ECX)
 if address in(INCREMENT,DECREMENT):
  token=m.read_words(sp+4,1)[0];v=(m.read_words(token,1)[0]+(1 if address==INCREMENT else -1))&0xffffffff;m.write_words(token,[v]);returned(4,v);return
 if address in(SELECT,DRAW,CREATE):
  e.function={SELECT:0x54691c,DRAW:0x546d30,CREATE:0x546918}[address];n={SELECT:2,DRAW:5,CREATE:14}[address];aa=m.read_words(sp+4,n)
  if address==CREATE:e.count=0;e.bufferCount=1;e.buffers[0]=sp+4;e.bufferBytes[0]=56
  else:
   e.count=n;e.arguments[:n]=aa
   if address==DRAW:
    if aa[3]and not(BASE<=aa[3]<BASE+SIZE):e.localMask=8;e.arguments[3]=0;e.buffers[0]=aa[3];e.bufferBytes[0]=16;e.bufferCount=1
    e.buffers[e.bufferCount]=aa[1];e.bufferBytes[e.bufferCount]=len(string(aa[1],False))+1;e.bufferCount+=1
 elif address==0x4f66cc:
  e.function=address;e.count=1;e.arguments[0]=m.read_words(sp+4,1)[0];e.receiver=receiver
  if 0x2000000<=receiver<0x2010000:e.receiver=0;e.localMask=256;e.bufferCount=1;e.buffers[0]=receiver;e.bufferBytes[0]=4
  n=1
 elif address==0x4f650f:e.function=address;e.receiver=receiver;n=0
 elif address in(0x4f6428,0x4f63ec):e.function=address;e.count=1;e.arguments[0]=m.read_words(sp+4,1)[0];n=1
 elif address in(0x4f6449,0x4f6584)and(not c.composeStrings or(frameMode and not 0x4226b0<=m.read_words(sp,1)[0]<0x422810)):
  e.function=address;e.receiver=receiver;e.count=1 if address==0x4f6449 else 0;n=e.count
  if n:
   source=m.read_words(sp+4,1)[0];e.arguments[0]=source
   if 0x2000000<=source<0x2010000:e.arguments[0]=0;e.localMask|=1;e.buffers[0]=source;e.bufferBytes[0]=4;e.bufferCount=1
  if 0x2000000<=receiver<0x2010000:e.receiver=0;e.localMask|=256;e.buffers[e.bufferCount]=receiver;e.bufferBytes[e.bufferCount]=4;e.bufferCount+=1
 else:return
 # Copy original local payloads into temporary C buffers for normalized event
 # bytes, while retaining actual x86 local addresses for side effects.
 payload=[bytes(u.mem_read(e.buffers[i],e.bufferBytes[i]))for i in range(e.bufferCount)]
 if e.function==0x4f6449 and e.localMask&256:payload[-1]=bytes(4)
 original_events.append((e.function,e.receiver,tuple(e.arguments[:e.count]),e.localMask,tuple(payload),raw(False)));
 if stopService==e.function:sourceStopped=True;u.emu_stop();return
 result=effect(e,False);returned(0 if address in(0x4f6428,0x4f63ec)else n*4,result)
m.u.hook_add(UC_HOOK_CODE,hook)

def prepare(strings=(b'Game saved',),seed=0):
 global oldFont,drawResult,mutation,selectCount,storageCount,freeCount,allocCount,fontResult,modeLocal,frameMode
 heap[:]=rng.randbytes(SIZE);C.memmove(C.addressof(image),seedImage,len(seedImage));lib.claw_message_drawing_defaults(C.byref(c));c.scene=host;c.emptyStringToken=0x52e1c4;c.fault=0;fc.host=sc.scene=host;sc.composeCamera=sc.composeCache=0;sc.maximumPlanes=65536;sc.fault=0;fc.composeMessages=1;fc.fault=0;fg.values[:]=[0]*20;fg.values[0]=18;fg.values[4:8]=[0,0,640,480];rect[:]=[0,110,640,174];oldFont=0xabcddcba;drawResult=64;mutation=selectCount=storageCount=freeCount=allocCount=0;fontResult=0x13571357;modeLocal=frameMode=False
 put(CONFIG,[0x510224,NODES if strings else 0,NODES+(len(strings)-1)*12 if strings else 0,len(strings),0,0,10,0x52e1c4,0,2000,500,0,0,0x13571357]);put(OWNER+4,[APP]);put(APP+0x4c,[CONFIG]);put(RECT,list(rect))
 for i,s in enumerate(strings):token=STRINGS+i*0x200;assert len(s)<0x1e0;put(token-12,[1,len(s),len(s)]);data(token,s+b'\0');put(NODES+i*12,[NODES+(i+1)*12 if i+1<len(strings)else 0,NODES+(i-1)*12 if i else 0,token])
 put(0x54691c,[SELECT]);put(0x546d30,[DRAW]);put(0x546918,[CREATE]);put(0x5469ec,[INCREMENT]);put(0x5469e8,[DECREMENT]);flush()

def compare(args,local=False,label='draw',record=False):
 global calls,eventCount,replayCases,selectCount,storageCount,freeCount,allocCount,modeLocal
 modeLocal=local;sync();native_events.clear();original_events.clear();errors.clear();tape.clear();before=bytes(heap);beforeGlobals=C.string_at(pointer(GS),GN);beforeRect=bytes(rect);settings=(oldFont,drawResult,mutation);counts=(selectCount,storageCount,freeCount,allocCount);aa=(U*4)(*args);out=U();c.fault=0;done=lib.claw_message_drawing_entry(0x4226b0,CONFIG,aa,4,rect if local else None,C.byref(c),dependency,None,C.byref(out));assert done and not c.fault and not errors,(label,done,c.fault,errors);afterCounts=(selectCount,storageCount,freeCount,allocCount);selectCount,storageCount,freeCount,allocCount=counts;originalArgs=list(args)
 if local:originalArgs[2]=RSTACK
 actual=m.call(0x4226b0,CONFIG,pack(*originalArgs));selectCount,storageCount,freeCount,allocCount=afterCounts;assert actual==out.value,(label,'EAX',actual,out.value)
 if original_events!=native_events:
  for i,(x,y)in enumerate(zip(native_events,original_events)):
   if x!=y:print(label,'event',i,x[:5],y[:5]);print('state',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(x[5],y[5]))if a!=b][:10]);break
  raise AssertionError((label,'events',len(native_events),len(original_events)))
 assert raw(True)==raw(False),(label,'full state',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:10])
 if record or calls%17==0:
  replay.write(pack(*args,int(local),c.composeStrings,c.textLimit,c.emptyStringToken,out.value,len(tape))+before+bytes(heap)+beforeGlobals+C.string_at(pointer(GS),GN)+beforeRect+bytes(rect))
  for fn,t,argv,mask,buffers,result,patches,globalsAfter,rectAfter in tape:
   replay.write(pack(fn,t,len(argv),*(argv+[0]*(8-len(argv))),mask,len(buffers),result,len(patches)))
   for b in buffers:replay.write(pack(len(b))+b)
   replay.write(globalsAfter+rectAfter)
   for offset,b in patches:replay.write(pack(offset,len(b))+b)
  replayCases+=1
 calls+=1;eventCount+=len(native_events);return out.value
# Retained queue/timer integration borrows a local output word, never inserts a
# test-only cell into the game heap. CString copyCtor destination is output-only.
FRAME_OUT=0xffffe000;frameOut=U();baseLookup=lookup
@Lookup
def lookup(_,t,n):return C.addressof(frameOut)if t==FRAME_OUT and n==1 else baseLookup(_,t,n)
host.lookup=lookup
@Alloc
def allocate(_,n):e=Call();e.function=0x4f63ec;e.count=1;e.arguments[0]=n;return dependency(C.pointer(c),e,None)
@Free
def release(_,t):e=Call();e.function=0x4f6428;e.count=1;e.arguments[0]=t;dependency(C.pointer(c),e,None)
host.allocate=allocate;host.free=release
oldNormalize=normalize

def normalize(e,native=True):
 x=list(oldNormalize(e,native));payload=list(x[4])
 if e.function==0x4f6449 and e.localMask&256:payload[-1]=bytes(4)
 x[4]=tuple(payload);return tuple(x)
oldStartupDependency=startupDependency
@StartupDep
def startupDependency(ctx,ev,user):
 q=ev.contents;e=Call();e.function=q.function;e.receiver=q.receiver;e.count=q.count;e.localMask=q.localMask;e.bufferCount=q.bufferCount;e.arguments[:]=q.arguments[:]
 for i in range(q.bufferCount):e.buffers[i]=q.buffers[i];e.bufferBytes[i]=q.bufferBytes[i]
 if e.receiver==FRAME_OUT:e.receiver=0;e.localMask|=256;e.buffers[e.bufferCount]=C.addressof(frameOut);e.bufferBytes[e.bufferCount]=4;e.bufferCount+=1
 return dependency(C.pointer(c),e,user)
@FrameDep
def frameDependency(ctx,e,user):
 if e.function==0x4226b0:
  out=U();aa=(U*4)(*e.arguments[:4]);rr=C.cast(e.buffers[0],UP)if e.localMask&4 else None;done=lib.claw_message_drawing_entry(e.function,e.receiver,aa,4,rr,C.byref(c),dependency,None,C.byref(out));assert done and not c.fault;return out.value
 if e.function==0x4f53eb:
  frameOut.value=0;aa=(U*1)(FRAME_OUT);out=U();sc.fault=0;assert lib.claw_player_startup_entry(e.function,e.receiver,aa,1,C.byref(sc),startupDependency,None,C.byref(out))and not sc.fault;U.from_address(e.buffers[0]).value=frameOut.value;return 0
 return dependency(C.pointer(c),e,user)
# Same actual hook, with output-only pre-copy locals normalized. Do not intercept
# the message drawer's frozen CString bodies while composing queue services.
# Existing hook reads this dynamic condition through c.composeStrings/frameMode.

def compareController(fn,receiver,args=(),label='retained'):
 global calls,eventCount,selectCount,storageCount,freeCount,allocCount,frameMode
 frameMode=True;sync();native_events.clear();original_events.clear();errors.clear();tape.clear();counts=(selectCount,storageCount,freeCount,allocCount);a=(U*len(args))(*args);out=U();c.fault=fc.fault=sc.fault=0
 if fn in(0x4224f0,0x46ca50):done=lib.claw_game_frame_service_entry(fn,receiver,args[0],C.byref(fc),frameDependency,None,C.byref(out))
 else:done=lib.claw_player_startup_entry(fn,receiver,a,len(args),C.byref(sc),startupDependency,None,C.byref(out))
 assert done and not(c.fault or fc.fault or sc.fault)and not errors,(label,done,c.fault,fc.fault,sc.fault,errors)
 afterCounts=(selectCount,storageCount,freeCount,allocCount);selectCount,storageCount,freeCount,allocCount=counts;actual=m.call(fn,receiver,pack(*args));selectCount,storageCount,freeCount,allocCount=afterCounts
 if fn not in(0x4224f0,0x46ca50,0x4f5288):assert actual==out.value,(label,'EAX',actual,out.value)
 if native_events!=original_events:
  for i,(x,y)in enumerate(zip(native_events,original_events)):
   if x!=y:print(label,'event',i,x[:5],y[:5]);print('state',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(x[5],y[5]))if a!=b][:12]);break
  raise AssertionError((label,'ordered events',len(native_events),len(original_events)))
 assert raw(True)==raw(False),(label,'complete retained state',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:12]);calls+=1;eventCount+=len(native_events);return out.value
stopService=0;sourceStopped=False;aliasMode=False
baseEffect=effect

def effect(e,native=True):
 if stopService==e.function:raise RuntimeError('explicit transport cancellation')
 if aliasMode and e.function==0x4f6449 and get(e.arguments[0],native=native)==[0x534ef8]:
  if native:U.from_address(e.buffers[e.bufferCount-1]).value=0x534ef8
  else:put(e.buffers[e.bufferCount-1],[0x534ef8],False)
  return 0
 if aliasMode and e.function==0x4f6584 and e.localMask&256:
  token=U.from_address(e.buffers[0]).value if native else get(e.buffers[0],native=False)[0]
  if token==0x534ef8:return 0
 return baseEffect(e,native)
