"""Raw heap lifecycle oracle; actual destructor bodies execute unchanged."""
import argparse,ctypes as C,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/actor-destruction-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');options=p.parse_args()
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['ActorDestruction.cpp','RatBombLogic.cpp','GenericEnemy.cpp','PlayerPhysics.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']],'-o',str(WORK/'libActorDestruction.dylib')],check=True)
lib=C.CDLL(str(WORK/'libActorDestruction.dylib'))
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('holderActorToken',C.c_uint32),('heldActorToken',C.c_uint32),('emptyStringToken',C.c_uint32)]
class Frame(C.Structure):_fields_=[('nowMilliseconds',C.c_uint32),('deltaMilliseconds',C.c_uint32)]
class SceneGlobals(C.Structure):_fields_=[('initializationFlags',C.c_uint32),('deletionArray',C.c_uint32*5),('reorderArray',C.c_uint32*5),('animation',Frame)]
lib.claw_actor_destruction_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_actor_destruction_entry.restype=C.c_uint32
lib.claw_actor_destroy.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32)];lib.claw_actor_destroy.restype=C.c_uint32
lib.claw_scene_actor_update.argtypes=[C.c_uint32,C.POINTER(SceneGlobals),C.c_uint32,Host,C.POINTER(C.c_uint32)]
class Enemy(C.Structure):_fields_=[(n,C.c_uint32*k)for n,k in [('actor',128),('primary',93),('secondary',93),('contact',93),('enemy',264)]]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',C.c_uint32),('nameToken',C.c_uint32),('name',C.c_char_p)]
class GenericContext(C.Structure):_fields_=[(x,C.c_uint32)for x in ['actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken']]+[(x,C.c_uint32*128)for x in ['playerActor','platformActor']]+[(x,C.c_uint32)for x in ['tick','animationDelta','levelWord','forcedRandom','hitMode']]+[('defaults',C.c_uint32*24),('virtualFunctions',C.c_uint32*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(C.c_uint32)),('bitWordCount',C.c_size_t),('emptyStringToken',C.c_uint32),('bitHandlerToken',C.c_uint32)]
class BombContext(C.Structure):_fields_=[('generic',GenericContext),('sequenceRegistryToken',C.c_uint32),('damageScale',C.c_float),('imageMinimum',C.c_int32),('imageMaximum',C.c_int32),('minimumImageToken',C.c_uint32),('imageHeader',C.c_uint32*16)]+[(n,C.c_uint32)for n in ['audioManagerAvailable','masterVolume','bounceSoundPoolToken','explosionSoundPoolToken','fault']]
class GenericCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*12),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Enemy),C.POINTER(GenericContext),C.POINTER(GenericCall),C.c_void_p)
lib.claw_rat_bomb_entry.argtypes=[C.POINTER(Enemy),C.POINTER(BombContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
m=OriginalV10(options.exe);u=m.u;u.mem_map(0,4096);m.executed.clear()
BASE,SIZE=0x1000000,0x10000;heap=(C.c_uint8*SIZE)();rng=random.Random(0x4c9c00)
A,L,S,K,E,E2,E3,PAYLOAD,STRING1,STRING2,BITS,HOLDER,HOLDER_L,VT=[BASE+i*0x1000 for i in range(1,15)]
CUSTOM,CUSTOM2,DEC=BASE+0xf100,BASE+0xf110,BASE+0xf120
SCENE_CALLBACK=BASE+0xf130
# Exact OS InterlockedDecrement adaptation, not a gameplay body replacement.
u.mem_write(DEC,b'\x8b\x44\x24\x04\xf0\xff\x08\x8b\x00\xc2\x04\x00');m.write_words(0x5469e8,[DEC])
imageViews={};events=[];live={};globals=Globals();native=True;policy=0;calls=event_count=0;currentScene=None;allocIndex=0
known={0x4c9be0,0x4c99a0,0x4c80c0,0x4c9b30,0x47cc80,0x4c9c00,0x4c99c0,0x4c80e0,0x4c9b50,0x4c8210,0x47cca0,0x4dbcd0,0x4f6584,0x48cf50,0x4c9a70,0x4c9e60,0x4c9e80}
def words(token,n):
 if native:
  return list((C.c_uint32*n).from_address(C.addressof(heap)+token-BASE))
 return m.read_words(token,n)
def put(token,values):
 if native:(C.c_uint32*len(values)).from_address(C.addressof(heap)+token-BASE)[:]=values
 else:m.write_words(token,values)
def snap():
 g=bytes(globals)if native else struct.pack('<3I',*m.read_words(0x53c9ac,2),m.read_words(0x52e1c8,1)[0]+12)
 memory=bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))
 sg=bytes(currentScene)if native and currentScene is not None else (struct.pack('<13I',m.read_words(0x5430d0,1)[0],*m.read_words(0x5430f0,5),*m.read_words(0x5430d8,5),*m.read_words(0x5430c8,1),*m.read_words(0x5430c4,1))if currentScene is not None else b'')
 return memory+g+sg,tuple(sorted(live.items()))
def log(event):events.append((event,snap()))
def effects(fn,receiver,args):
 if fn in(CUSTOM,CUSTOM2):
  a=words(A,128);a[0x184//4]^=fn
  if policy==1 and receiver==S:a[0x6c//4]=E3
  if policy==2 and receiver==L:a[0x78//4]=0
  put(A,a);target=words(receiver,4);target[3]^=0xabcdef12;put(receiver,target);return receiver
 if fn==0x4dc560:
  if policy==3:
   b=words(args[0],4);b[1]^=0x1234;put(args[0],b)
  return 0
 return 0
@Lookup
def lookup(_,token,n):
 if BASE<=token and token+n*4<=BASE+SIZE:return C.addressof(heap)+token-BASE
 if 0x400000<=token<0x550000:
  key=(token,n)
  if key not in imageViews:imageViews[key]=(C.c_uint32*n)(*m.read_words(token,n))
  return C.addressof(imageViews[key])
 return None
@Allocate
def allocate(_,n):
 global allocIndex
 token=BASE+0xf400+allocIndex*0x200;allocIndex+=1;log(('allocate',n));put(token,[0]*((n+3)//4));live[token]=True;return token
@Free
def free(_,token):log(('free',token));live[token]=False
@Dependency
def bomb_dependency(s,c,event,user):
 put(c.contents.enemyToken,list(s.contents.enemy)[:92]);e=event.contents
 if e.function==0x4f6428:free(None,e.arguments[0]);return 0
 raise AssertionError(('unexpected Bomb destructor dependency',e.function))
@Invoke
def invoke(_,call):
 args=tuple(call.arguments[:call.argumentCount]);fn=call.function;receiver=call.receiver
 if fn in known:
  fault=C.c_uint32();result=C.c_uint32();assert lib.claw_actor_destruction_entry(fn,receiver,args[0]if args else 0,C.byref(globals),host,C.byref(fault),C.byref(result));assert not fault.value;return result.value
 if fn==0x484d90:
  s=Enemy();s.enemy[:92]=words(receiver,92);c=BombContext();c.generic.enemyToken=receiver;r=C.c_uint32()
  assert lib.claw_rat_bomb_entry(C.byref(s),C.byref(c),fn,args[0],bomb_dependency,None,C.byref(r))==1;put(receiver,list(s.enemy)[:92]);return r.value
 log(('call',fn,receiver,args))
 if fn==0x4a49b0:live[args[0]]=False
 return effects(fn,receiver,args)
@Clock
def clock(_):return 0
host=Host(None,lookup,allocate,free,invoke,clock)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def original_hook(uc,address,size,user):
 global allocIndex
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f63ec:
  n=m.read_words(sp+4,1)[0];token=BASE+0xf400+allocIndex*0x200;allocIndex+=1;log(('allocate',n));m.write_words(token,[0]*((n+3)//4));live[token]=True;returned(0,token);return
 if address==0x4f6428:
  token=m.read_words(sp+4,1)[0];log(('free',token));live[token]=False;returned(0);return
 cfg={SCENE_CALLBACK:(1,0),CUSTOM:(1,4),CUSTOM2:(1,4),0x4a49b0:(1,0),0x4dc560:(2,8),0x4a35f0:(1,0)}
 if address not in cfg:return
 n,pop=cfg[address];args=tuple(m.read_words(sp+4,n));receiver=0 if address in(0x4a49b0,0x4a35f0,SCENE_CALLBACK)else receiver
 log(('call',address,receiver,args))
 if address==0x4a49b0:live[args[0]]=False
 returned(pop,effects(address,receiver,args))
u.hook_add(UC_HOOK_CODE,original_hook)
def prepare(kind='rat'):
 global globals,native,live,currentScene,allocIndex
 native=True;heap[:]=rng.randbytes(SIZE);code=b'\x8b\x44\x24\x04\xf0\xff\x08\x8b\x00\xc2\x04\x00';heap[DEC-BASE:DEC-BASE+len(code)]=code;globals=Globals(HOLDER,E,0x52e1c4);currentScene=None;allocIndex=0
 put(A,[rng.getrandbits(32)for _ in range(128)]);put(A,[0x5137f0]);put(A+0x6c,[L,S,HOLDER]);put(A+0x78,[K])
 for i,t in enumerate((L,S,K,E3)):
  put(t,[rng.getrandbits(32)for _ in range(93)]);put(t,[0x513740]);put(t+0x14,[PAYLOAD+i*0x100,0]);put(t+0x18,[E if i==0 else E2 if i==1 else 0])
 put(E,[rng.getrandbits(32)for _ in range(264)]);put(E,[0x50f084 if kind=='rat'else 0x50f13c]);put(E+0x2f4,[0x513e34,0x513e28,rng.choice([0,1,32,33,64]),BITS]);put(E+0x1a4,[STRING1+12,STRING2+12]);put(STRING1,[rng.choice([1,2,0xffffffff]),5,5]);put(STRING2,[rng.choice([1,2,0xffffffff]),5,5]);put(E2,[rng.getrandbits(32)for _ in range(92)]);put(E2,[0x50f13c]);put(HOLDER+0x6c,[HOLDER_L]);put(HOLDER_L+0x1c,[15]);put(VT,[CUSTOM,CUSTOM2]);put(VT+0x20,[CUSTOM2,CUSTOM]);live={t:True for t in [A,L,S,K,E,E2,E3,PAYLOAD,PAYLOAD+0x100,PAYLOAD+0x200,PAYLOAD+0x300,STRING1,STRING2,BITS]}
 # Guards after every original actor/logic/private region remain in full heap.
 return globals

def compare(fn,receiver,label,arg=0,select=False):
 global native,live,globals,events,calls,event_count,allocIndex
 oldHeap=bytes(heap);oldGlobals=bytes(globals);oldLive=dict(live);oldScene=bytes(currentScene)if currentScene is not None else None;allocIndex=0;native=True;events.clear();fault=C.c_uint32();result=C.c_uint32()
 if fn==0x4c8fc0:lib.claw_scene_actor_update(receiver,C.byref(currentScene),0,host,C.byref(fault));rr=1
 elif select:rr=lib.claw_actor_destroy(receiver,arg,C.byref(globals),host,C.byref(fault));result.value=receiver
 else:rr=lib.claw_actor_destruction_entry(fn,receiver,arg,C.byref(globals),host,C.byref(fault),C.byref(result))
 assert rr and not fault.value,(label,'native fault',fault.value)
 expected=snap();expectedEvents=list(events);u.mem_write(BASE,oldHeap);m.write_words(0,[0x12345678]);m.write_words(0x53c9ac,list(struct.unpack('<2I',oldGlobals[:8])));m.write_words(0x52e1c8,[struct.unpack('<I',oldGlobals[8:])[0]-12]);m.write_words(0x5469e8,[DEC]);u.mem_write(DEC,b'\x8b\x44\x24\x04\xf0\xff\x08\x8b\x00\xc2\x04\x00');live=oldLive;allocIndex=0;native=False;events.clear()
 actualfn=m.read_words(m.read_words(receiver,1)[0]+4,1)[0]if select else fn
 args=struct.pack('<I',arg)if actualfn in(0x4c9be0,0x4c99a0,0x4c80c0,0x4c9b30,0x47cc80,0x48cf50,0x4c8fc0,0x4c9e60)else b''
 if oldScene:
  values=struct.unpack('<13I',oldScene);m.write_words(0x5430d0,values[:1]);m.write_words(0x5430f0,values[1:6]);m.write_words(0x5430d8,values[6:11]);m.write_words(0x5430c8,values[11:12]);m.write_words(0x5430c4,values[12:13])
 try:ret=m.call(actualfn,receiver,args)
 except Exception:print('original error',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 if snap()!=expected:
  actual=snap()[0];exp=expected[0]
  for i in range(0,len(actual),4):
   x,y=struct.unpack_from('<I',actual,i)[0],struct.unpack_from('<I',exp,i)[0]
   if x!=y:print(label,'offset',hex(i),hex(x),hex(y))
  raise AssertionError((label,'complete heap/globals/live'))
 if actualfn in(0x4c9be0,0x4c99a0,0x4c80c0,0x4c9b30,0x47cc80,0x4c9e60):assert ret==result.value,(label,'return receiver')
 if events!=expectedEvents:
  print(label,'original events',[x for x,b in events]);print('native events',[x for x,b in expectedEvents]);
  for i,(x,y)in enumerate(zip(events,expectedEvents)):
   if x!=y:print('mismatch at',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError((label,'ordered complete heap events'))
 assert m.read_words(0,1)==[0x12345678],(label,'SEH restored')
 calls+=1;event_count+=len(events);native=True
