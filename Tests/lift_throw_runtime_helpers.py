"""Owned raw-token original oracle; finite resource/renderer transport is explicit."""
import ctypes as C,hashlib,json,random,struct,subprocess,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/lift-throw-agent'
sources=['LiftThrowRuntime','EnemyMotionAux','CommonEnemyEntries','HumanEnemy','HumanCombat','GenericEnemy','GenericEnemyStates','ActorResourceBindings','BreakableObjectRuntime','PlayerPhysics','ActorAnimationRuntime','AnimationEngine','AnimationOperations','SceneActorRuntime','WorldObjectRuntime','GameTiming','PlayerAttackInput','PlayerLocomotion','PlayerAirStates','PlayerEngine','CollisionResponse','TileCollision']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(ROOT/'Sources'/f'{x}.cpp')for x in sources],str(WORK/'creator-profile.cpp'),'-o',str(WORK/'libLiftThrowRuntime.dylib')],check=True)
U=C.c_uint32
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,U)for n in('playerToken','inputToken','stageDelta','animationDelta','tick','powerup','pixelScratch','audioEnabled','masterVolume','strongThrow')]+[('defaults',U*24)]
class Physics(C.Structure):_fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3)for n in('acceleration','velocity','position','minimum','maximum','delta')]+[('stopped',U),('unused',U)]+[(n,C.c_double*3)for n in('remainder','maximumDelta','maximumVelocity')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('physics',C.POINTER(Physics)),('attack',C.c_void_p),('enemyWordCount',U),('composeAnimation',U),('fault',U),('core',C.c_void_p)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000
A,L,P,TARGET,TL,E,SC,INPUT,IM,PTRS,SEQ,TABLE,SOUND,POOL,PLATFORM,VT=[BASE+0x1000+i*0x1000 for i in range(16)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();peStart,peEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(peEnd-peStart+1)).from_buffer_copy(bytes(m.u.mem_read(peStart,peEnd-peStart+1)));heap=(C.c_uint8*SIZE)();lowPage=(C.c_uint8*4096)();g=Globals();physics=Physics();c=Context();c.globals=C.pointer(g);c.physics=C.pointer(physics);c.enemyWordCount=260
lib=C.CDLL(str(WORK/'libLiftThrowRuntime.dylib'));lib.claw_lift_throw_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(U)];lib.claw_lift_throw_defaults.argtypes=[C.POINTER(Globals)];lib.claw_physics_construct.argtypes=[C.POINTER(Physics)]
rng=random.Random(0x41dc50);native_events=[];original_events=[];errors=[];tape=[];tapeDepth=0;replay=io.BytesIO();replayCases=0;replayFunctions=set();animationResult=0;moveMode=1;mutation=0;resizeResult=1;lookupResult=SEQ;calls=eventCount=0
GLOBAL_START,GLOBAL_SIZE=0x520000,0x30000;globalSeed=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):
 b=C.string_at(C.addressof(heap)+t-BASE,n*4)if native else bytes(m.u.mem_read(t,n*4));return list(struct.unpack('<'+'I'*n,b))
def raw(native):return bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))
def updates():return {0x544b14:bytes(core.words),0x53725c:pack(attack.difficulty),0x537218:pack(attack.damage100),0x537228:pack(attack.damage0),0x537e88:pack(g.playerToken),0x537204:pack(g.inputToken),0x53720c:pack(g.stageDelta),0x5430c4:pack(g.animationDelta),0x537210:pack(g.tick),0x534eac:pack(g.powerup),0x544e8c:pack(g.pixelScratch),0x532c0c:pack(g.audioEnabled),0x532c10:pack(g.masterVolume),0x537224:pack(g.strongThrow),0x534db8:bytes(physics)}
def globalsRaw(native):
 if not native:return bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
 b=bytearray(globalSeed)
 for t,v in updates().items():b[t-GLOBAL_START:t-GLOBAL_START+len(v)]=v
 return bytes(b)
def snapshot(native):return hashlib.sha256(raw(native)).digest(),hashlib.sha256(globalsRaw(native)).digest()
def sync():
 global globalSeed
 m.u.mem_write(BASE,bytes(heap))
 for t,b in updates().items():m.u.mem_write(t,b)
 m.u.mem_write(0x513e10,bytes(g.defaults));globalSeed=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
@Lookup
def lookup(_,t,n):
 if t%4:return None
 if t+n*4<=4096:return C.addressof(lowPage)+t
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if peStart<=t and t+n*4<=peEnd+1:return C.addressof(image)+t-peStart
 return None
c.scene=Host(None,lookup,Allocate(),Free(),Invoke(),Clock())
def setGlobal(address,value,native):
 field={0x537224:'strongThrow',0x5430c4:'animationDelta'}[address]
 if native:setattr(g,field,value)
 else:m.write_words(address,[value])
def effect(fn,t,args,native):
 if mutation and fn in(0x4c8220,0x4c79e0):
  old=g.strongThrow if native else m.read_words(0x537224,1)[0];setGlobal(0x537224,old^1,native);put(TARGET+0x164,[get(TARGET+0x164,native=native)[0]^4],native)
 if fn==0x4dba00:return {0x5271d8:2009,0x5271cc:2010,0x527170:2017,0x5271b4:2012,0x527188:2015,0x52717c:2016,0x5234ec:2018,0x523148:2000}[args[0]]
 if fn in(0x4c79e0,0x4c8220):return 1
 if fn==0x4c82a0:return animationResult
 if fn==0x4cbb60:
  assert t==TABLE and len(args)==4;put(args[0]+76,args[1:3],native);put(args[0]+0xcc,[moveMode],native);return 0
 if fn in(0x4f6286,0x4061b0):return lookupResult
 if fn==0x4b45f0:return 1
 if fn in(0x4a48e0,0x4a9070):return TABLE+0x400 if resizeResult else 0
 if fn==0x4db4d0:return 0
 if fn==0x404f00:return 0 # Exact finite landing callback is explicitly forwarded.
 raise AssertionError(('unexpected external dependency',hex(fn),hex(t),args))
@Dependency
def dependency(_,ev,user):
 global tapeDepth
 e=ev.contents;a=list(e.arguments[:e.count]);native_events.append((e.function,e.receiver,tuple(a),snapshot(True)));top=tapeDepth==0;old=bytes(heap);tapeDepth+=1
 try:
  value=effect(e.function,e.receiver,a,True)or 0
  if top:
   patches=[];after=bytes(heap);pos=0
   while pos<SIZE:
    if old[pos]==after[pos]:pos+=1;continue
    begin=pos
    while pos<SIZE and old[pos]!=after[pos]:pos+=1
    patches.append((begin,after[begin:pos]))
   tape.append((e.function,e.receiver,a,value,replayState(),patches))
  return value
 except BaseException as ex:errors.append(ex);c.fault=1;return 0
 finally:tapeDepth-=1

COUNTS={0x4c79e0:2,0x4c8220:1,0x4c82a0:1,0x4cbb60:4,0x4dba00:1,0x4b45f0:4,0x4a48e0:1,0x4a9070:2,0x4db4d0:3,0x4061b0:1,0x404f00:0}
COPYRECT=0x10ff2a0;SETRECT=0x10ff2b0;m.u.mem_write(0x546d58,pack(COPYRECT));m.u.mem_write(0x546d5c,pack(SETRECT))
def returned(pop,value=0):
 sp=m.u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_EIP,ret);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(u,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX)
 if address==SETRECT:
  dst,*words=m.read_words(sp+4,5);m.write_words(dst,words);returned(20,1);return
 if address==COPYRECT:
  dst,src=m.read_words(sp+4,2);m.write_words(dst,m.read_words(src,4));returned(8,1);return
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);args=[name];original_events.append((address,t,tuple(args),snapshot(False)));value=effect(address,t,args,False);m.write_words(out,[value]);returned(8,int(bool(value)));return
 if address not in COUNTS:return
 n=COUNTS[address];args=m.read_words(sp+4,n);cdecl=address in(0x4a3050,0x48c8a0,0x4a48e0,0x4a9070);t=0 if cdecl else t;original_events.append((address,t,tuple(args),snapshot(False)));value=effect(address,t,args,False)
 if value is not None:returned(0 if cdecl else n*4,value)
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(seed=0):
 global animationResult,moveMode,mutation,resizeResult,lookupResult
 heap[:]=rng.randbytes(SIZE);lib.claw_lift_throw_defaults(C.byref(g));g.playerToken=A;g.inputToken=INPUT;g.stageDelta=g.animationDelta=18;g.tick=seed;g.powerup=0;g.pixelScratch=0x11223344;g.audioEnabled=1;g.masterVolume=100;g.strongThrow=seed%2;lib.claw_physics_construct(C.byref(physics));physics.acceleration[1]=2250;animationResult=seed%2;moveMode=1;mutation=0;resizeResult=1;lookupResult=SEQ;c.fault=0;c.composeAnimation=0;c.enemyWordCount=260
 put(A,[0x5137f0]);put(A+12,[SC]);put(A+108,[L]);put(L+20,[P]);put(L+28,[24]);put(A+76,[500,1000]);put(A+100,[400]);put(A+8,[0x80]);put(A+0x40,[0]);put(A+0xcc,[1]);put(A+0x118,[-16,-52,16,60]);put(A+0x128,[-15,-45,22,52]);put(A+0x138,[0x80000000,0,0,0]);put(A+0x170,[IM]);put(A+0x174,[SOUND]);put(IM+20,[PTRS]);put(IM+100,[1,120]);put(PTRS+44*4,[SOUND]);put(A+0x1a4,[0]);put(A+0x19c,[0]);put(A+0x80,[0]);put(P,[seed%2,0,0,0]);put(P+60,[0]);put(P+300,[TARGET]);put(P+0xd8,[-16,-52,16,60]);put(P+0xf0,[100000,0]);put(INPUT+4,[0,0,0xffffffff]);put(SC+36,[TABLE]);put(SC+40,[IM+0x400]);put(SC+44,[IM+0x800]);put(IM+0x400+48,[0]);put(SOUND+16,[POOL]);put(TARGET,[0x5137f0]);put(TARGET+12,[SC]);put(TARGET+108,[TL]);put(TL+24,[E]);put(TL+28,[1000]);put(TARGET+76,[500,1000]);put(TARGET+100,[300]);put(TARGET+8,[0x80]);put(TARGET+0x40,[0]);put(TARGET+0xcc,[1]);put(TARGET+0xd0,[0x200]);put(TARGET+0x164,[1]);put(TARGET+0x118,[-12,-12,12,20]);put(TARGET+0x128,[-12,-12,12,20]);put(TARGET+0x138,[0x80000000,0,0,0]);put(E,[0x50edd4]);put(E+12,[TARGET,TL]);put(E+0x12c,[TARGET]);put(E+0x260,[-12,-52,12,20]);put(E+0x270,[-12,-12,12,20]);put(E+0x1ac,[seed%34]);put(E+0x2b4,[-10,10,-105]);put(E+0x2c0,[-30,30,-70]);put(E+0x2cc,[0]);put(E+0x2fc,[32,0]);put(E+20,[0]);put(E+32,[1]);put(E+0x378,[SEQ,SEQ,SEQ]);put(PLATFORM+0x158,[1,-2]);
 for off,value in((0x50,0),(0x58,0),(0x60,0),(0x68,500),(0x70,1000),(0x40,2000)):C.memmove(C.addressof(heap)+E+off-BASE,struct.pack('<d',value),8)
 sync()
def compare(fn,args=(),receiver=0,label='case',void=False):
 global calls,eventCount,replayCases
 sync();native_events.clear();original_events.clear();errors.clear();tape.clear();c.fault=0;beforeHeap=bytes(heap);beforeState=replayState();beforeCore=bytes(core);values=(U*len(args))(*args);result=U();beforeG=bytes(g);done=lib.claw_lift_throw_entry(fn,receiver,values,len(args),C.byref(c),dependency,None,C.byref(result));assert done and not c.fault and not errors,(label,'native',done,c.fault,errors);afterG=bytes(g);afterCore=bytes(core);C.memmove(C.addressof(g),beforeG,len(beforeG));C.memmove(C.addressof(core),beforeCore,len(beforeCore));original=m.call(fn,receiver,pack(*args));C.memmove(C.addressof(g),afterG,len(afterG));C.memmove(C.addressof(core),afterCore,len(afterCore))
 if not void:assert original==result.value,(label,'meaningful EAX',original,result.value)
 assert native_events==original_events,(label,'ordered events',[(i,x,y)for i,(x,y)in enumerate(zip(native_events,original_events))if x!=y][:4],len(native_events),len(original_events));assert raw(True)==raw(False),(label,'complete heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(True),raw(False)))if x!=y][:15]);assert globalsRaw(True)==globalsRaw(False),(label,'complete global image',[(hex(GLOBAL_START+i),x,y)for i,(x,y)in enumerate(zip(globalsRaw(True),globalsRaw(False)))if x!=y][:15])
 if fn not in replayFunctions or calls%29==0:
  replay.write(struct.pack('<19I',fn,receiver,len(args),*([x&0xffffffff for x in args]+[0]*(12-len(args))),result.value,int(void),c.enemyWordCount,c.composeAnimation)+beforeState+replayState()+beforeHeap+raw(True)+struct.pack('<I',len(tape)))
  for f,t,aa,v,states,patches in tape:
   replay.write(struct.pack('<15IQI',f,t,len(aa),*(aa+[0]*(12-len(aa))),v,len(patches))+states)
   for offset,data in patches:replay.write(struct.pack('<2I',offset,len(data))+data)
  replayCases+=1;replayFunctions.add(fn)
 calls+=1;eventCount+=len(native_events);return result.value

class Attack(C.Structure):_fields_=[(n,U)for n in('pressed','difficulty','damage100','damage0','targetToken')]+[('targetActor',U*128),('projectileToken',U),('projectileActor',U*128)]+[(n,U)for n in('repeat','spawnX','spawnY','spawnZ','spawnName','spawnFlags')]
attack=Attack();c.attack=C.addressof(attack);queryTarget=TARGET;queryDistance=0;randomValue=1
priorEffect=effect
def effect(fn,t,args,native):
 if fn==0x41d750:
  if native:attack.targetToken=queryTarget;attack.targetActor[:]=get(queryTarget,128)if queryTarget else attack.targetActor[:]
  return queryDistance&0xffffffff
 if fn==0x4a3050:return randomValue
 if fn==0x48c8a0:return 1
 return priorEffect(fn,t,args,native)
COUNTS.update({0x4a3050:0,0x48c8a0:2})
# Existing original hook is left installed; these addresses are not in COUNTS.
def queryHook(u,address,size,user):
 if address==0x41d750:
  sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,4);original_events.append((address,0,tuple(args[:3]),snapshot(False)));m.write_words(args[3],[queryTarget]);returned(0,queryDistance)
# Cdecl-only RNG and speech bypass the thiscall generic hook via count marker.
# Change old hook's convention rather than adding overlapping callbacks.
m.u.hook_add(UC_HOOK_CODE,queryHook)
class BreakableGlobals(C.Structure):_fields_=[(n,U)for n in('animationDelta','audioEnabled','audioPosition','crateImageChoice')]+[('damageScale',C.c_float),('healthScale',C.c_float),('kegStates',U*10),('crateStates',U*10)]
class BreakableContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(BreakableGlobals)),('loot',C.c_void_p),('fault',U)]
BreakableDependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(BreakableContext),C.POINTER(Call),C.c_void_p)
bg=BreakableGlobals();bc=BreakableContext();bc.scene=c.scene;bc.globals=C.pointer(bg);bg.damageScale=bg.healthScale=1
lib.claw_breakable_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(BreakableContext),BreakableDependency,C.c_void_p,C.POINTER(U)]
lib.claw_lift_throw_test_base.argtypes=[C.POINTER(Context),U,U]
baseProfile=None;creatorMode=False;creatorCalls=0
@BreakableDependency
def breakableDependency(_,ev,user):
 e=ev.contents;args=list(e.arguments[:e.count]);native_events.append((e.function,e.receiver,tuple(args),snapshot(True)))
 try:return effect(e.function,e.receiver,args,True)or 0
 except BaseException as ex:errors.append(ex);bc.fault=1;return 0
priorLiftEffect=effect
def effect(fn,t,args,native):
 if fn==0x46fbe0:
  if not native:return None # Observe the whole original virtual override.
  bg.animationDelta=g.animationDelta;bg.audioEnabled=g.audioEnabled;bg.audioPosition=g.masterVolume;result=U();assert lib.claw_breakable_entry(fn,t,None,0,C.byref(bc),breakableDependency,None,C.byref(result))and not bc.fault;return result.value
 if fn==0x4332f0:
  # Declared source-backed full generic constructor profile, independently
  # recovered/tested in GenericEnemy. The outer constructor remains original.
  assert creatorMode and baseProfile is not None
  before,after=baseProfile
  for i in range(0,SIZE,4):
   if before[i:i+4]!=after[i:i+4]:
    if native:C.memmove(C.addressof(heap)+i,after[i:i+4],4)
    else:m.u.mem_write(BASE+i,after[i:i+4])
  return t
 if fn==0x4c7970:put(t+0x16c,[1,IM,SOUND],native);return 1
 if fn==0x4062e0:return SEQ
 if fn==0x4209d0:put(t+0x16c,[args[0]],native);return 0
 if fn==0x40f6c0:put(t+0x118,args,native);return 0
 if fn==0x406240:put(t+0x128,[-20,-16,20,24],native);return 0
 if fn==0x4cd800:return 0 # Explicit placement service; no retail ground claim.
 return priorLiftEffect(fn,t,args,native)
COUNTS.update({0x46fbe0:0,0x4332f0:1,0x4c7970:1,0x4062e0:1,0x4209d0:1,0x40f6c0:4,0x406240:0,0x4cd800:2})
# The generic old hook resolves effect dynamically; nullable return means execute.
class WorldState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class WorldContext(C.Structure):_fields_=[(n,U)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('width',C.c_int32),('height',C.c_int32),('registry',U),('layers',U*3),('entry',U),('callback',U),('flags',U)]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('name',C.c_char_p)]
WorldDependency=C.CFUNCTYPE(U,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
class WorldInfo(C.Structure):_fields_=[('consumed',U),('created',U)]
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDependency,C.c_void_p,C.POINTER(WorldInfo)]
@WorldDependency
def worldDependency(s,ctx,e,_):
 if e.contents.function==0x4f6286:return BASE+0x3d000
 if e.contents.function in(0x4c7970,0x4c7900,0x4f4630):return 0
 raise AssertionError(('unexpected source WWD fixture boundary',e.contents.function))
def sourceKeg(record):
 global baseProfile,creatorMode,creatorCalls
 v=record['words'];ss=record['strings'];data=pack(*v)+b''.join(s.encode()+bytes(n-len(s))for s,n in zip(ss,v[1:5]));assert hashlib.sha256(data).hexdigest()==record['rawSHA256'];state=WorldState((U*128)(*get(TARGET,128)),(U*93)(*get(TL,93)));ctx=WorldContext(SC,TARGET,TL,2,24576,6144,BASE+0x3d800,(U*3)(0,0,0),BASE+0x3d000,0x46f1e0,2);info=WorldInfo();src=(C.c_uint8*len(data)).from_buffer_copy(data);assert lib.claw_world_object_load(src,len(data),C.byref(state),C.byref(ctx),worldDependency,None,C.byref(info))==len(data)and info.created;put(TARGET,list(state.actor));put(TL,list(state.logic));put(TL+24,[E]);put(TARGET+0x170,[IM]);put(TARGET+0x174,[SOUND]);before=bytes(heap);assert lib.claw_lift_throw_test_base(C.byref(c),TARGET,E);after=bytes(heap);heap[:]=before;baseProfile=(before,after)
 bg.animationDelta=g.animationDelta;bg.audioEnabled=g.audioEnabled;bg.audioPosition=g.masterVolume;bg.damageScale=bg.healthScale=1;bc.fault=0;creatorMode=True;sync();native_events.clear();original_events.clear();errors.clear();oldG=bytes(g);result=U();args=(U*1)(TARGET);assert lib.claw_breakable_entry(0x46f2a0,E,args,1,C.byref(bc),breakableDependency,None,C.byref(result))and not bc.fault and not errors,errors;afterG=bytes(g);C.memmove(C.addressof(g),oldG,len(oldG));original=m.call(0x46f2a0,E,pack(TARGET));C.memmove(C.addressof(g),afterG,len(afterG));creatorMode=False
 assert result.value==original==E and raw(True)==raw(False)and globalsRaw(True)==globalsRaw(False)and native_events==original_events,('whole derived source creator',record['index'],[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(True),raw(False)))if x!=y][:12],[(hex(e[0]),e[2])for e in native_events],[(hex(e[0]),e[2])for e in original_events]);creatorCalls+=1

from unicorn.x86_const import UC_X86_REG_EBP
class Core(C.Structure):_fields_=[('words',U*130)]+[(n,U)for n in('defaultBitCount','errorLocation','heapHandle','heapFreeFunction')]+[('scratch',U*2)]
core=Core();c.core=C.addressof(core);core.errorLocation=0x12345678;core.words[:]=m.read_words(0x544b14,130);core.words[14]=0x533418
#4dc680 executes its actual caller-frame read. Fixture supplies that frame.
FRAME=BASE+0x3e000;m.u.reg_write(UC_X86_REG_EBP,FRAME)
priorSync=sync
def sync():
 put(FRAME+4,[core.errorLocation]);m.u.reg_write(UC_X86_REG_EBP,FRAME);priorSync()

def replayState():return bytes(g)+bytes(physics)+bytes(attack)+bytes(core)
class AnimationRecord(C.Structure):_fields_=[(n,U)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AnimationRecord),C.POINTER(U)]
aniDecodes=0
ANI_TABLE,ANI_RECORDS,ANI_BYTES=BASE+0x21000,BASE+0x22000,BASE+0x28000
def actualLiftANI():
 global aniDecodes
 data=(ROOT/'App/GameData/ANIS/LIFT.ANI').read_bytes();assert data==sourceLiftANI();assert len(data)<8192;count=struct.unpack_from('<I',data,12)[0];pathLength=struct.unpack_from('<I',data,16)[0];assert 0<count<100;put(SEQ+12,[ANI_TABLE,count]);put(ANI_TABLE,[ANI_RECORDS+64*i for i in range(count)]);at=32+pathLength
 for i in range(count):
  tail=data[at:];buf=(C.c_uint8*len(tail)).from_buffer_copy(tail);record=AnimationRecord();nameLength=U();used=lib.claw_animation_decode_record(buf,len(tail),SEQ,C.byref(record),C.byref(nameLength));assert used
  token=ANI_RECORDS+64*i;put(token,[rng.getrandbits(32)for _ in range(12)]);sync();m.u.mem_write(ANI_BYTES,tail);m.call(0x4d76e0,token,pack(SC+44,ANI_BYTES));rawRecord=m.read_words(token,12);assert [getattr(record,n)for n,_ in AnimationRecord._fields_]==[rawRecord[1]&0xffff]+rawRecord[2:10]+[rawRecord[11]];assert used==20+m.read_words(0x543174,1)[0];put(token,rawRecord);at+=used;aniDecodes+=1
 assert at==len(data);put(IM+20,[PTRS]);put(IM+100,[1,157]);put(PTRS,[0]+[SOUND]*157);put(A+0x188,[0x513870,A,0,0,0,0,0,1,0,0,0x3f800000]);c.composeAnimation=1
 for fn in(0x4c79e0,0x4c8220,0x4c82a0):COUNTS.pop(fn,None)
def scriptedAnimation():
 c.composeAnimation=0;COUNTS.update({0x4c79e0:2,0x4c8220:1,0x4c82a0:1})
priorAnimationEffect=effect
def effect(fn,t,args,native):
 if fn in(0x4c88e0,0x4208e0):return 0
 return priorAnimationEffect(fn,t,args,native)
COUNTS.update({0x4c88e0:4,0x4208e0:4})

_sourceLift=None
def sourceLiftANI():
 global _sourceLift
 if _sourceLift is not None:return _sourceLift
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
 def w(t):return struct.unpack_from('<I',blob,t)[0]
 def walk(at,size,path=()):
  global _sourceLift
  end=at+size
  while at<end:
   k,target,n=w(at),w(at+4),w(at+8);start=at+(16 if k else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode()
   if k:walk(target,n,path+(name,));at=nul+1
   else:
    ext=blob[at+20:at+24].split(b'\0')[0][::-1].decode();p='/'.join(path+(name+'.'+ext,));at=nul+2
    if p=='CLAW/ANIS/LIFT.ANI':_sourceLift=blob[target:target+n]
 walk(w(131),w(135));assert _sourceLift is not None;return _sourceLift
