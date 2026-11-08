"""Private hash-pinned whole original light-effect oracle and exact service adapters."""
import ctypes as C,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/flare-agent'
SOURCES=['FlareRuntime','GameImageRuntime','PIDRaster','PIDSurfaceRaster','PIDBlitter','StackedActorLifecycleRuntime','GenericEnemy','PowerupObjectRuntime','ItemPickupRuntime','PlayerPowerupRuntime','PlayerInputDispatch','PlayerDamage','SinglePlayerSceneRuntime','WorldFileRuntime','WorldPlaneRuntime','CArrayRuntime','SceneCameraRuntime','SpatialGridRuntime','SpriteGeometry','SceneActorRuntime','WorldObjectRuntime','GameTiming','PlayerLocomotion','PlayerAirStates','PlayerInitialization','PlayerEngine','PlayerPhysics','CollisionResponse','TileCollision','ActorAnimationRuntime','AnimationEngine','AnimationOperations','AudioEvents','ActorResourceBindings','CRTRandomRuntime','WorldLootRuntime','AmbientAudioBackendRuntime']
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in SOURCES],'-o',str(WORK/'libFlare.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',U),('nameToken',U),('name',C.c_char_p)]
class GenericContext(C.Structure):_fields_=[(x,U)for x in ['actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken']]+[(x,U*128)for x in ['playerActor','platformActor']]+[(x,U)for x in ['tick','animationDelta','levelWord','forcedRandom','hitMode']]+[('defaults',U*24),('virtualFunctions',U*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',UP),('bitWordCount',C.c_size_t),('emptyStringToken',U),('bitHandlerToken',U)]
class Loot(C.Structure):_fields_=[('words',U*341)]+[(x,U)for x in ['itemCount','audioVolume','highLaunch','configurationWord']]
class Context(C.Structure):_fields_=[('scene',Host),('animation',C.c_void_p),('images',C.c_void_p)]+[(x,U)for x in ['composeAnimation','composeFSM','composeEffects','maximumSteps','fault']]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*8),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(WORK/'libFlare.dylib'));lib.claw_flare_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_flare_entry.restype=U
lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(GenericContext)]
BASE,SIZE=0x1000000,0x100000;GS,GN=0x500000,0x50000
A,L,E,P,PL,PP,APP,SC,WORLD,CONFIG,INPUT,IMAGE,ROOTIMAGE,META,BOSS_A,BOSS_L,BOSS,FX,FXL,NAMES,FUNCS,NAME,SAVED,OTHER,OTHER_L=[BASE+0x1000+i*0x1000 for i in range(25)]
VT=BASE+0x30000;CUSTOM=BASE+0xfe000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);m.executed.clear();seedGlobals=bytes(u.mem_read(GS,GN));raw=(C.c_uint8*GN).from_buffer_copy(seedGlobals);heap=(C.c_uint8*SIZE)();loot=Loot();common=GenericContext();lib.claw_generic_enemy_context_defaults(C.byref(common));states=(State*1)(State(2000,0x43d070,NAME,b'LS_IDLE'));common.states=states;common.stateCount=1
native=True;events=[];errors=[];calls=snapshots=0;callbackCount=0;allocationCount=0;creationCount=0;prefixStop=0;sourceStopped=False;policy=0;creationNull=False;allocationNull=False;collisionResult=0;mode=3
aliases={0x52a190:'itemCount',0x532c10:'audioVolume',0x53721c:'highLaunch'}
PROFILE=BASE+0x62000
def address(t,n=1):
 if t==PROFILE and n==1:return C.addressof(loot)+Loot.configurationWord.offset
 if 0x537ec8<=t and t+n*4<=0x53841c:return C.addressof(loot)+t-0x537ec8
 if t in aliases and n==1:return C.addressof(loot)+getattr(Loot,aliases[t]).offset
 if GS<=t and t+n*4<=GS+GN:return C.addressof(raw)+t-GS
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 return None

def get(t,n=1):
 if not native:return m.read_words(t,n)
 a=address(t,n);assert a is not None,hex(t);return list((U*n).from_address(a))
def put(t,v):
 if native:
  a=address(t,len(v));assert a is not None,hex(t);(U*len(v)).from_address(a)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def globalsImage():
 b=bytearray(raw);b[0x537ec8-GS:0x53841c-GS]=bytes(loot.words)
 for t,n in aliases.items():struct.pack_into('<I',b,t-GS,getattr(loot,n))
 return bytes(b)
def heapImage():
 b=bytearray(heap);struct.pack_into('<I',b,PROFILE-BASE,loot.configurationWord);return bytes(b)
def snapshot():return(heapImage(),globalsImage(),callbackCount,allocationCount,creationCount)if native else(bytes(u.mem_read(BASE,SIZE)),bytes(u.mem_read(GS,GN)),callbackCount,allocationCount,creationCount)
@Lookup
def lookup(_,t,n):return address(t,n)
@Allocate
def alloc(_,n):return effect(0x4f63ec,0,[n])
@Free
def free(_,t):effect(0x4f6428,0,[t])
@Clock
def clock(_):raise AssertionError('unexpected clock')
@Invoke
def invoke(_,e):return effect(e.function,e.receiver,list(e.arguments[:e.argumentCount]))
host=Host(None,lookup,alloc,free,invoke,clock);ctx=Context(host,None,None,0,1,0,65536,0)

def effect(f,t,args):
 global callbackCount,allocationCount,creationCount
 events.append(((f,t,tuple(args)),snapshot()));callbackCount+=1
 if f==0x4f63ec:allocationCount+=1;assert args==[0x4c];return 0 if allocationNull else E
 if f==0x4f6428:return 0
 if f==0x4c8da0:
  creationCount+=1
  if policy==4:put(BOSS+12,[OTHER]);put(OTHER+0x148,[900,1300])
  if creationNull:return 0
  id,x,y,z,name,flags=args;actor=A if name==0x522aac else FX;logic=L if actor==A else FXL
  put(actor+4,[id]);put(actor+8,[flags]);put(actor+0x4c,[x,y]);put(actor+0x64,[z]);put(logic+28,[0]);return actor
 if f in(0x4c7fa0,0x4c8060):return 0
 if f==0x4c7970:
  put(t+0x170,[ROOTIMAGE]);put(t+0x174,[IMAGE]);
  if policy==1:put(0x5371fc,[APP]);put(t+0x6c,[L])
  if policy==5:put(t+0x6c,[FXL])
  return 1
 if f==0x4dba00:return 2000
 if f==0x4cbb60:
  actor,x,y,_=args;put(actor+0x4c,[x+(2 if policy==2 else 0),y+(-3 if policy==2 else 0)]);return collisionResult
 if f==0x4f6974:return get(t)[0]
 if f==0x4db6e0:
  if registryGrow:
   at=NAMES+0x100 if t==0x537698 else FUNCS+0x100;put(t+8,[1990,2010,at]);put(at+20*4,[NAME if t==0x537698 else 0x458570]);put(t+28,[NAMES+0x200,2]if t==0x537698 else [0,0]);return at
  return 0
 if f==0x4db5f0:return 0x23
 if f==0x4db4d0:return 0
 if f==0x4f6439:put(t,[0x52e1c4]);return t
 if f==0x4a36f0:return 0
 if f==CUSTOM:return mode
 if f in(0x4c79e0,0x4c8220,0x4c82a0):
  if f==0x4c79e0:put(t+0x190,[SAVED])
  elif f==0x4c8220:put(t+8,[args[0]])
  return 0
 if f==0x40f6c0:put(t+0x118,args);return 0
 if f in(0x421010,0x420fc0,0x4b45f0):return 0
 raise AssertionError((hex(f),hex(t),args))
@Dependency
def dependency(c,e,_):
 try:q=e.contents;return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]))
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0

def returned(pop,result):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop*4);u.reg_write(UC_X86_REG_EIP,ret)
services={0x4f63ec:(1,0,True),0x4f6428:(1,0,True),0x4c8da0:(6,6,False),0x4c7fa0:(1,1,False),0x4c8060:(1,1,False),0x4c7970:(1,1,False),0x4dba00:(1,1,False),0x4cbb60:(4,4,False),0x4f6974:(1,1,False),0x4db6e0:(2,2,False),0x4db5f0:(0,0,True),0x4db4d0:(3,3,False),0x4f6439:(0,0,False),0x4a36f0:(1,0,True),CUSTOM:(0,0,False),0x4c79e0:(2,2,False),0x4c8220:(1,1,False),0x4c82a0:(1,1,False),0x40f6c0:(4,4,False),0x421010:(2,2,False),0x420fc0:(1,1,False),0x4b45f0:(4,4,False)}
def hook(_,address,size,user):
 global sourceStopped
 if address==prefixStop:sourceStopped=True;u.emu_stop();return
 if address in services:
  n,pop,cdecl=services[address];returned(pop,effect(address,0 if cdecl else u.reg_read(UC_X86_REG_ECX),m.read_words(u.reg_read(UC_X86_REG_ESP)+4,n)))
u.hook_add(UC_HOOK_CODE,hook)
def number(t,v):put(t,struct.unpack('<2I',struct.pack('<d',v)))
registryGrow=False
def setup(seed=0):
 global native,callbackCount,allocationCount,creationCount,prefixStop,sourceStopped,policy,creationNull,allocationNull,collisionResult,mode,registryGrow
 native=True;r=random.Random(seed);C.memmove(heap,r.randbytes(SIZE),SIZE);C.memmove(raw,seedGlobals,GN);C.memset(C.byref(loot),0,C.sizeof(loot));loot.itemCount=62;loot.audioVolume=100;loot.words[340]=1;loot.words[31]=ROOTIMAGE;loot.words[66+31]=0x26ad;loot.words[132+31]=0x100;loot.words[208+31]=META;loot.words[274+31]=BASE+0x40000
 put(META+16,[0x4701b0]);put(ROOTIMAGE,[0]*40);put(ROOTIMAGE+0x24,struct.unpack('<3I',b'LEVEL_GEM\0\0\0'));put(IMAGE,[0]*16);put(IMAGE+24,[24,32,0,-4]);put(IMAGE+0x28,[BASE+0x41000]);put(BASE+0x41000+0x28,[250])
 for actor,logic in[(A,L),(P,PL),(FX,FXL),(BOSS_A,BOSS_L),(OTHER,OTHER_L)]:
  put(actor,[r.getrandbits(32)for _ in range(128)]);put(actor+12,[SC]);put(actor+0x6c,[logic]);put(actor+0x4c,[800,1100]);put(actor+0x64,[4000]);put(actor+0x80,[0]);put(actor+0xcc,[7]);put(actor+0x170,[ROOTIMAGE,IMAGE]);put(actor+0x190,[0]);put(actor+0x148,[0,0]);put(logic,[0]*93);put(logic+12,[SC]);put(logic+16,[0x43ca60 if actor==A else 0x4701b0]);put(logic+24,[E]);put(logic+28,[0])
 put(E,[r.getrandbits(32)for _ in range(84)]);put(PP,[0]*78);put(PL+20,[PP]);put(PL+28,[5010]);put(PP+4,[0]);put(PP+0x124,[SAVED]);put(PP+0x12c,[0]);put(P+0x74,[A]);put(P+0x10c,[100]);put(P+0xf8,[0]);put(P+0x104,[0]);put(P+0xd0,[2]);put(APP,[0]*77);put(APP+44,[CONFIG]);put(APP+0xc0,[SAVED]);put(SAVED-12,[1,0,0]);put(CONFIG,[0]*800);put(CONFIG,[VT]);put(VT+16,[CUSTOM]);put(APP+0x124,[0]);put(SC+8,[BASE+0x35000]);put(SC+0x24,[WORLD]);put(WORLD,[0]*56);put(WORLD+0x5c,[BASE+0x36000]);put(INPUT,[0,0,0,0xffffffff]);put(APP+4,[BASE+0x37000]);put(BASE+0x37000+4,[0x1234]);put(SC+0x28,[BASE+0x38000]);put(BOSS,[r.getrandbits(32)for _ in range(280)]);put(BOSS+12,[BOSS_A]);put(BOSS+0x12c,[BOSS_A]);put(BOSS+0x130,[BOSS_L]);put(BOSS+0x458,[0,0]);put(BOSS_A+0x148,[850,1200]);put(0x537960,[PROFILE]);put(0x537210,[1000]);put(0x537e88,[P]);put(0x5371fc,[APP]);put(0x537204,[INPUT]);put(0x532c0c,[1]);put(0x52be14,[0xffffffff,0xffffffff]);put(0x5430c4,[18]);put(0x537608,[0,0x544b4c,2000,2000,FUNCS,FUNCS+64,4,0,0]);put(FUNCS,[0x43d070]);put(FUNCS+64,[0]);put(0x537698,[0,0x544b4c,2000,2000,NAMES,NAMES+64,4,0,0]);put(NAMES,[NAME]);put(NAME-12,[1,7,7]);put(NAME,struct.unpack('<2I',b'LS_IDLE\0'));common.actorToken=A;common.primaryToken=L;common.enemyToken=E;common.sceneToken=SC;common.tileManagerToken=WORLD;common.tick=1000;ctx.composeCreation=ctx.composeAnimation=0;ctx.composeCommon=ctx.composeLoot=1;callbackCount=allocationCount=creationCount=prefixStop=0;sourceStopped=False;policy=0;creationNull=allocationNull=False;collisionResult=0;mode=3;registryGrow=False
cdecl={0x457f00,0x458010,0x4dc870}
meaningful={0x457f00,0x458010,0x458120,0x484d90,0x458530,0x458570,0x4ce850}
def execute(f,t,args=(),allowFault=False):
 global calls,snapshots
 events.clear();errors.clear()
 if native:
  aa=(U*len(args))(*[a&0xffffffff for a in args]);out=U();assert lib.claw_flare_entry(f,t,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));ret=out.value
  if not allowFault:assert not ctx.fault,(hex(f),ctx.fault,errors);assert not errors,errors
 else:
  ret=m.call(f,t,struct.pack('<'+'I'*len(args),*(a&0xffffffff for a in args)));assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(0 if f in cdecl else len(args)*4),(hex(f),hex(u.reg_read(UC_X86_REG_ESP)))
 calls+=1;snapshots+=len(events);return snapshot(),list(events),ret if f in meaningful else 0

def restore(s):
 global callbackCount,allocationCount,creationCount
 if native:
  C.memmove(heap,s[0],SIZE);loot.configurationWord=struct.unpack_from('<I',s[0],PROFILE-BASE)[0];C.memmove(raw,s[1],GN);C.memmove(C.addressof(loot),s[1][0x537ec8-GS:0x53841c-GS],341*4)
  for t,n in aliases.items():setattr(loot,n,struct.unpack_from('<I',s[1],t-GS)[0])
 else:u.mem_write(BASE,s[0]);u.mem_write(GS,s[1])
 callbackCount,allocationCount,creationCount=s[2:]

def compare(f,t,args=()):
 global native
 native=True;before=snapshot();a=execute(f,t,args);native=False;restore(before);b=execute(f,t,args)
 if a!=b:
  for z,(x,y)in enumerate(zip(a[0][:2],b[0][:2])):
   diff=[(hex((BASE if z==0 else GS)+i),x[i:i+4].hex(),y[i:i+4].hex())for i in range(0,len(x),4)if x[i:i+4]!=y[i:i+4]];print('diff',hex(f),z,diff[:16])
  print('events',[q[0]for q in a[1]],[q[0]for q in b[1]]);print('results',a[2],b[2]);
  for i,(x,y)in enumerate(zip(a[1],b[1])):
   if x!=y:
    print('first event difference',i,x[0],y[0]);
    for z in range(2):
     dx=[hex((BASE if z==0 else GS)+j)for j in range(0,len(x[1][z]),4)if x[1][z][j:j+4]!=y[1][z][j:j+4]];print('event words',z,dx[:20])
    break
  raise AssertionError(hex(f))
 native=True;restore(a[0]);return a
# Original image-manager metadata and pure effect setter composition.
class ImageGlobals(C.Structure):_fields_=[('animationDelta',U),('directDrawFX',U*25),('surfaceLoadFlags',U),('surfaceColorKey',U),('compressedEffect',U*4),('embeddedPalette',U*256)]
class Animation(C.Structure):_fields_=[('animationDelta',U),('audioPosition',U)]
ig=ImageGlobals();anim=Animation();COMP=BASE+0x50000;TABLE=BASE+0x51000;SEQ=BASE+0x52000;SEQTABLE=BASE+0x53000;RECORDS=BASE+0x54000;DATA=BASE+0x55000
oldSetup=setup

def setup(seed=0):
 oldSetup(seed);ctx.composeAnimation=ctx.composeEffects=0;ctx.composeFSM=1;put(0x537ac0,[0,0x544b4c,2000,2000,FUNCS,FUNCS+64,4,0,0]);put(FUNCS,[0x458570]);put(L+16,[0x457f00]);put(E,[0x50e6fc]);put(E+8,[A,A,L]);put(E+20,[0,0,1001,2]);put(E+40,[A,A,L]);put(E+72,[SEQ]);put(L+28,[2000]);put(CONFIG+0x768,[0]);put(ROOTIMAGE+20,[TABLE]);put(ROOTIMAGE+100,[1,1]);put(TABLE,[0,IMAGE]);put(IMAGE+48,[COMP]);put(COMP,[0]*10);put(SEQ+12,[SEQTABLE,1]);put(SEQTABLE,[RECORDS]);put(RECORDS,[0,0,0,0,0,0,10,0,0,0,0,0]);ig.compressedEffect[:]=[0x516b90,0x516bd0,0x516c10,0x516c50];ctx.images=C.cast(C.pointer(ig),C.c_void_p)
oldEffect=effect

def effect(f,t,args):
 global callbackCount
 if f in(0x4f6286,0x4ce7b0,0x4c6130):
  events.append(((f,t,tuple(args)),snapshot()));callbackCount+=1
  if f==0x4f6286:return lookupResult
  if f==0x4ce7b0:return 1
  return 0
 return oldEffect(f,t,args)
lookupResult=SEQ;services[0x4ce7b0]=(1,1,False)
for f in(0x4c8220,0x4c82a0):services.pop(f)

def extraHook(_,address,size,user):
 if address==0x4f6286:
  name,out=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,2);value=effect(address,u.reg_read(UC_X86_REG_ECX),[name]);m.write_words(out,[value]);returned(2,int(bool(value)))
 elif address in(0x4c8220,0x4c82a0)and not ctx.composeAnimation:returned(1,effect(address,u.reg_read(UC_X86_REG_ECX),m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)))
 elif address==0x4ce7b0 and ctx.composeEffects:return # Execute frozen whole original body.
 elif address==0x4c6130 and not ctx.composeEffects:returned(2,effect(address,u.reg_read(UC_X86_REG_ECX),m.read_words(u.reg_read(UC_X86_REG_ESP)+4,2)))
u.hook_add(UC_HOOK_CODE,extraHook)
# The initial hook consults this mutable map; no transport suppression when composed.
oldExecute=execute

def execute(f,t,args=(),allowFault=False):
 if ctx.composeEffects:services.pop(0x4ce7b0,None)
 else:services[0x4ce7b0]=(1,1,False)
 return oldExecute(f,t,args,allowFault)
class Record(C.Structure):_fields_=[(n,U)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(Record),UP];lib.claw_animation_decode_record.restype=U
decoderMode=False;decodedEvent=0;decodes=0
# Normalize stack-local out pointers at the resource lookup boundary.
def decodeHook(_,address,size,user):
 if address==0x4f6286 and decoderMode:
  _,out=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,2);m.write_words(out,[decodedEvent]);returned(2,int(bool(decodedEvent)))
# Suppress the ordinary transport branch during the source record parser only.
oldExtraHook=extraHook
# Existing extraHook is registered first; give it a decoder-aware effect result.
sourceEffect=effect

def effect(f,t,args):
 if f==0x4f6286 and decoderMode:return decodedEvent
 return sourceEffect(f,t,args)

def decodeFile(path,pid):
 global native,decoderMode,decodedEvent,decodes
 native=True;data=path.read_bytes();sig,_,flags,count,pathLength=struct.unpack_from('<5I',data);assert sig==32 and count>0;offset=32+pathLength;put(SEQ+12,[SEQTABLE,count]);put(SEQTABLE,[RECORDS+i*64 for i in range(count)])
 header=struct.unpack_from('<8I',pid.read_bytes());width,height,originX,originY=header[2:6];put(IMAGE+16,[width,height,width//2,height//2,originX,originY,0x11]);put(IMAGE+48,[COMP]);put(ROOTIMAGE+20,[TABLE]);put(ROOTIMAGE+100,[1,1]);put(TABLE,[0,IMAGE]);put(A+0x16c,[1]);put(A+0x174,[IMAGE]);put(A+0x188,[0,A,0,0,0,0,0,0,0,0,0x3f800000]);put(SC+44,[BASE+0x66000])
 for i in range(count):
  record=Record();length=U();event=BASE+0x67000 if struct.unpack_from('<H',data,offset)[0]&2 else 0;buffer=(C.c_uint8*(len(data)-offset)).from_buffer_copy(data[offset:]);used=lib.claw_animation_decode_record(buffer,len(buffer),event,C.byref(record),C.byref(length));assert used;token=RECORDS+i*64;u.mem_write(DATA,data[offset:]);m.write_words(token,get(token,12));decoderMode=True;decodedEvent=event
  try:m.call(0x4d76e0,token,struct.pack('<2I',BASE+0x66000,DATA))
  finally:decoderMode=False
  words=m.read_words(token,12);assert [getattr(record,n)for n,_ in Record._fields_]==[words[1]&0xffff]+words[2:10]+[words[11]];assert used==20+m.read_words(0x543174,1)[0];put(token,words);decodes+=1;offset+=used
 assert offset==len(data);ctx.animation=C.cast(C.pointer(anim),C.c_void_p);ctx.composeAnimation=ctx.composeEffects=1;anim.animationDelta=get(0x5430c4)[0];anim.audioPosition=100;put(0x5430b0,list(ig.compressedEffect));return count
# Frozen ANI audio boundary; physical transport has no gameplay mutations here.
baseEffect=effect

def effect(f,t,args):
 global callbackCount
 if f in(0x4c88e0,0x4208e0):events.append(((f,t,tuple(args)),snapshot()));callbackCount+=1;return 0
 return baseEffect(f,t,args)

def audioHook(_,address,size,user):
 if address in(0x4c88e0,0x4208e0):returned(4,effect(address,u.reg_read(UC_X86_REG_ECX),m.read_words(u.reg_read(UC_X86_REG_ESP)+4,4)))
u.hook_add(UC_HOOK_CODE,audioHook)
prefixes=0

def comparePrefix(f,t,args,stop):
 global native,prefixStop,sourceStopped,prefixes
 native=True;before=snapshot();a=execute(f,t,args,True);assert ctx.fault==1 and not errors,(ctx.fault,errors);native=False;restore(before);events.clear();sourceStopped=False;prefixStop=stop
 try:m.call(f,t,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
 except AssertionError:assert sourceStopped and u.reg_read(UC_X86_REG_EIP)==stop
 else:raise AssertionError('original unsafe prefix returned')
 assert a[0]==snapshot() and a[1]==events,(hex(f),'prefix mismatch');native=True;restore(a[0]);prefixStop=0;prefixes+=1
