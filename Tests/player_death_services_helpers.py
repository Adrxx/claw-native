"""Private whole original death-service oracle with explicit CRT/UI/network adapters."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/player-death-services-agent'
sources=['PlayerDeathServices','ActorDestruction','GameFrameServices','PlayerPowerupRuntime','PlayerInputDispatch','PlayerEngine','PlayerPhysics','PlayerDamage','PlayerLocomotion','PlayerAirStates','CollisionResponse','TileCollision']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib','-ffp-contract=off',
 *[str(ROOT/'Sources'/f'{name}.cpp')for name in sources],str(WORK/'probe-adapter.cpp'),
 '-o',str(WORK/'libPlayerDeathServices.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('managerToken',C.c_uint32),('emptyStringToken',C.c_uint32)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('temporaryStringToken',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('buffers',C.POINTER(C.c_uint8)*2),('bufferBytes',C.c_uint32*2)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000
MANAGER,MANAGER2,OWNER,OWNER2,VT,CLIENT,CLIENT2,NET,APP,UI,PACKET,PACKET2,NAME,CLONE,EMPTY,MESSAGE,TLS,VOICEPOOL,SCRATCH=[BASE+0x1000+i*0x1000 for i in range(19)]
MODE,INCREMENT,DECREMENT=0x10ff100,0x10ff110,0x10ff120
ALLOCATION=BASE+0x19000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.executed.clear()
m.write_words(0x5469ec,[INCREMENT]);m.write_words(0x5469e8,[DECREMENT])
lib=C.CDLL(str(WORK/'libPlayerDeathServices.dylib'));lib.claw_player_death_service_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_player_death_service_entry.restype=C.c_uint32
lib.claw_death_test_probe.argtypes=[C.c_uint32,C.c_uint32,Host];lib.claw_death_test_probe.restype=C.c_uint32
heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g);ctx.temporaryStringToken=SCRATCH
rng=random.Random(0x41ebd0);native_events=[];original_events=[];native_frees=[];original_frees=[];errors=[];calls=events=0;mode=1;randomValue=0;resolvedClient=CLIENT;allocateResult=ALLOCATION;mutation=0;tempOriginal=SCRATCH;globalSeed=b'';additionalGlobals=None
def put(t,values,native=True):
 data=struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
 if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
 else:m.u.mem_write(t,data)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(C.addressof(heap)+t-BASE,n*4)if native else bytes(m.u.mem_read(t,n*4))))
def put_bytes(t,data,native=True):
 if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
 else:m.u.mem_write(t,data)
def string(t,native=True):
 data=C.string_at(C.addressof(heap)+t-BASE,4096)if native else bytes(m.u.mem_read(t,4096))
 return data.split(b'\0',1)[0]
def globals_raw(native):
 if not native:return bytes(m.u.mem_read(0x528000,0x1c000))
 data=bytearray(globalSeed);struct.pack_into('<I',data,0x5371fc-0x528000,g.managerToken)
 if additionalGlobals:
  for address,value in additionalGlobals().items():data[address-0x528000:address-0x528000+len(value)]=value
 return bytes(data)
def raw(native):
 data=bytearray(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))
 data[SCRATCH-BASE:SCRATCH-BASE+4]=b'\0'*4 #Separate explicit adapted local CString comparison.
 return bytes(data)
def snapshot(native):return hashlib.sha256(raw(native)).digest(),hashlib.sha256(globals_raw(native)).digest(),get(SCRATCH if native else tempOriginal,native=native)[0],tuple(native_frees if native else original_frees)
@Lookup
def lookup(user,t,n):return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
@Allocate
def allocate(user,n):native_events.append((0x4f63ec,0,(n,),None,snapshot(True)));return allocateResult
@Free
def free(user,t):native_events.append((0x4f6428,0,(t,),None,snapshot(True)));native_frees.append(t)
ctx.scene=Host(None,lookup,allocate,free,Invoke(),Clock())
def effects(fn,receiver,args,native,inputBuffer=None,outputBuffer=None):
 if fn in(0x40af90,0x4750d0):return lib.claw_death_test_probe(fn,receiver,ctx.scene)if native else None
 if fn==MODE:
  if mutation==1:
   if native:g.managerToken=MANAGER2
   else:m.write_words(0x5371fc,[MANAGER2])
  return mode
 if fn==0x4a3050:return randomValue
 if fn==0x4e0c60:
  if mutation==2:put(OWNER+0xbc8,[PACKET2],native)
  return resolvedClient
 if fn==0x4f63ec:return allocateResult
 if fn==0x4f6428:(native_frees if native else original_frees).append(args[0]);return 0
 if fn==0x4f66cc:
  text=string(args[0],native);put(CLONE,[1,len(text),len(text)],native);put_bytes(CLONE+12,text+b'\0',native);put(receiver,[CLONE+12],native);return receiver
 if fn==0x4a3920:
  text=string(args[2],native)+(b' 'if args[1]==0x524acc else b': ')+inputBuffer
  assert len(text)<256,('formatter outside bounded stack domain',len(text))
  outputBuffer(text+b'\0')
  if mutation==2:put(receiver if receiver else OWNER+0xbc8,[PACKET2],native)
  return len(text)
 if fn==0x422370:
  if mutation==2:put(OWNER+0x784,[CLIENT2],native)
  put_bytes(UI+0x100,inputBuffer+b'\0',native);return 0
 if fn==0x4e0d70:
  assert args[3]==len(string(args[2]+8,native))+9
  put(NET+0x100,args,native);return 0
 raise AssertionError(('unknown service',hex(fn),hex(receiver),args))
@Dependency
def dependency(context,call,user):
 c=call.contents;args=list(c.arguments[:c.argumentCount]);inputBuffer=None;outputBuffer=None
 if c.function==0x4a3920:
  inputBuffer=C.string_at(c.buffers[1]).split(b'\0',1)[0]
  outputBuffer=lambda data:C.memmove(c.buffers[0],data,len(data))
 elif c.function==0x422370:inputBuffer=C.string_at(c.buffers[0]).split(b'\0',1)[0]
 native_events.append((c.function,c.receiver,tuple(args),inputBuffer,snapshot(True)))
 try:return effects(c.function,c.receiver,args,True,inputBuffer,outputBuffer)
 except Exception as e:errors.append(e);return 0
COUNTS={MODE:0,0x4a3050:0,0x4e0c60:1,0x4f63ec:1,0x4f6428:1,0x4f66cc:1,0x4a3920:4,0x422370:2,0x4e0d70:4}
CDECL={0x4a3050,0x4f63ec,0x4f6428,0x4a3920}
def hook(u,address,size,user):
 if address in(INCREMENT,DECREMENT):
  sp=u.reg_read(UC_X86_REG_ESP);token=m.read_words(sp+4,1)[0];value=(m.read_words(token,1)[0]+(1 if address==INCREMENT else -1))&0xffffffff;m.write_words(token,[value]);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+8);return
 if address not in COUNTS:return
 sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,COUNTS[address]);receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX);originalReceiver=receiver;originalArgs=list(args);inputBuffer=None;outputBuffer=None
 if address==0x4f66cc and receiver==tempOriginal:receiver=SCRATCH
 if address==0x4a3920:
  inputBuffer=string(originalArgs[3],False);outputBuffer=lambda data:m.u.mem_write(originalArgs[0],data)
  args[0]=0
  if not BASE<=args[3]<BASE+SIZE:args[3]=0
 elif address==0x422370:
  inputBuffer=string(args[0],False);args[0]=0
 original_events.append((address,receiver,tuple(args),inputBuffer,snapshot(False)))
 if address in(0x40af90,0x4750d0):return #Execute actual original probe bodies.
 if address==0x4f66cc and originalReceiver==tempOriginal and tempOriginal!=SCRATCH:
  value=effects(address,SCRATCH,args,False,inputBuffer,outputBuffer);m.write_words(tempOriginal,get(SCRATCH,native=False));m.write_words(SCRATCH,[0xa5a5a5a5])
 else:value=effects(address,originalReceiver,args,False,inputBuffer,outputBuffer)
 u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in CDECL else COUNTS[address]*4))
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(name=b'Captain Claw',refs=1):
 C.memset(C.addressof(heap),0xa5,SIZE);ctx.fault=0;g.managerToken=MANAGER;g.emptyStringToken=EMPTY+12
 for t,n in((OWNER,800),(OWNER2,800),(MANAGER,64),(MANAGER2,64),(CLIENT,20),(CLIENT2,20),(VOICEPOOL,256)):
  put(t,[rng.getrandbits(32)for _ in range(n)])
 for i in range(8):
  voice=VOICEPOOL+0x40+i*0x38;put(voice+0xc,[BASE+0x20000+i*0x100,VOICEPOOL,1,44100]);put(voice+0x24,[44100])
 put(MANAGER+0x2c,[OWNER]);put(MANAGER2+0x2c,[OWNER2]);put(OWNER,[VT]);put(OWNER2,[VT]);put(VT+0x10,[MODE])
 for owner in(OWNER,OWNER2):put(owner+4,[APP]);put(owner+0x780,[NET,CLIENT,0x12345678]);put(owner+0xbc8,[PACKET])
 put(APP+0x4c,[UI]);put(CLIENT+8,[NAME+12]);put(CLIENT2+8,[NAME+12]);put(CLIENT+0x18,[rng.choice([0,ALLOCATION]),1024]);put(CLIENT2+0x18,[ALLOCATION,1024])
 put(NAME,[refs,len(name),len(name)]);put_bytes(NAME+12,name+b'\0');put(EMPTY,[0xffffffff,0,0,0]);put_bytes(MESSAGE,b'ordinary notification\0')
 native_frees.clear();original_frees.clear();sync()
def sync():
 global globalSeed
 m.u.mem_write(BASE,bytes(heap));m.write_words(0x5371fc,[g.managerToken]);m.write_words(0x52e1c8,[g.emptyStringToken-12,g.emptyStringToken]);globalSeed=bytes(m.u.mem_read(0x528000,0x1c000))
def compare(fn,args,label,receiver=0):
 global calls,events,tempOriginal
 sync();tempOriginal=m.stack-0x204 if fn==0x41ebd0 else m.stack-0x104 if fn==0x479f10 else SCRATCH
 if tempOriginal!=SCRATCH:m.write_words(tempOriginal,get(SCRATCH))
 native_events.clear();original_events.clear();errors.clear();ctx.fault=0;beforeVoice=bytes(heap)[VOICEPOOL-BASE:VOICEPOOL-BASE+1024]
 values=(C.c_uint32*len(args))(*(x&0xffffffff for x in args));result=C.c_uint32()
 assert lib.claw_player_death_service_entry(fn,receiver,values,len(args),C.byref(ctx),dependency,None,C.byref(result)),(label,ctx.fault)
 assert not errors,errors
 original=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
 if fn not in(0x41ebd0,0x4b7aa0):assert original==result.value,(label,'result',original,result.value)
 assert native_events==original_events,(label,'events',[(i,a[:4],b[:4],a[4][2],b[4][2])for i,(a,b)in enumerate(zip(native_events,original_events))if a!=b][:4],len(native_events),len(original_events))
 assert snapshot(True)==snapshot(False),(label,'snapshot',snapshot(True)[2],snapshot(False)[2])
 assert raw(True)==raw(False),(label,'complete heap bytes',[(i,a,b)for i,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:12])
 assert globals_raw(True)==globals_raw(False),(label,'complete globals')
 assert beforeVoice==bytes(heap)[VOICEPOOL-BASE:VOICEPOOL-BASE+1024],(label,'unexpected voice mutation')
 calls+=1;events+=len(native_events)
