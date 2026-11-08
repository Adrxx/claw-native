"""Pinned whole Katherine specialized-body oracle; raw/common/resource transports explicit."""
import ctypes as C,struct,random,json,subprocess,hashlib,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/katherine-agent';U=C.c_uint32
SOURCES=['KatherineRuntime','RauxRuntime','PickupPointsRuntime','ActorDestruction','ActorWrapperRuntime','ActorResourceBindings','ActorAnimationRuntime','AnimationEngine','AnimationOperations','SpriteGeometry','PIDRaster','PIDSurfaceRaster','PIDBlitter','PlayerProjectileRuntime','BulletLogic','SceneActorRuntime','WorldObjectRuntime','GameTiming','PlayerPhysics','PlayerLocomotion','PlayerAirStates','PlayerEngine','PlayerInitialization','PlayerDamage','TileCollision','RawTileDescriptionRuntime','CollisionResponse','LogicStateRegistry','GenericEnemy','GenericEnemyStates','HumanEnemy','HumanCombat','HumanoidStrikeRuntime','CommonEnemyEntries','EnemyMotionAux','RatLogic','WorldLootRuntime','WorldPlaneRuntime','WorldFileRuntime','CArrayRuntime','SceneCameraRuntime','SpatialGridRuntime','CRTRandomRuntime','EndLevelGemRuntime','PowerupObjectRuntime','ItemPickupRuntime','BouncingGoodieLogic','ActorInteractions','PlayerPowerupRuntime','StackedActorLifecycleRuntime','PlayerInputDispatch']
if not(WORK/'libKatherineRuntime.dylib').exists()or any((ROOT/'Sources'/f'{s}.cpp').stat().st_mtime>(WORK/'libKatherineRuntime.dylib').stat().st_mtime for s in SOURCES)or (WORK/'katherine_common_bridge.cpp').stat().st_mtime>(WORK/'libKatherineRuntime.dylib').stat().st_mtime:subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in SOURCES],str(WORK/'katherine_common_bridge.cpp'),'-o',str(WORK/'libKatherineRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libKatherineRuntime.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,U)for n in('manager','player','tick','animationDelta','powerup','audioEnabled','volume','jumpDisabled','boss')]+[(n,C.c_float)for n in('damageScale','healthScale','rangeScale')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals))]+[(n,U)for n in('composeAnimation','composeImages','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.katherine_test_animation.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),C.POINTER(U)]
lib.katherine_test_random.argtypes=[C.POINTER(Context),C.POINTER(U)]
lib.katherine_test_gem.argtypes=[C.POINTER(Context),Dep,C.c_void_p,U,C.POINTER(U)]
lib.katherine_test_common.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
lib.claw_katherine_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
class Physics(C.Structure):_fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3)for n in('acceleration','velocity','position','minimum','maximum','delta')]+[('stopped',U),('unused',U)]+[(n,C.c_double*3)for n in('remainder','maximumDelta','maximumVelocity')]
lib.claw_physics_construct.argtypes=[C.POINTER(Physics)]
BASE,SIZE,GS,GN=0x3000000,0x100000,0x520000,0x30000
A,L,E,SC,PLAYER,PL,PR,SECONDARY,CONTACT,IMAGE,IMAGE_TABLE,LEAF,SEQ,ANI_TABLE,ANI_RECORDS,SOUND,POOL,OTHER,OL,OP,CONTAINER,WORLD,THREAD=[BASE+0x1000+i*0x1000 for i in range(23)]
REG_BASE=BASE+0x40000;FAKE=0x10ff900
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g)
rng=random.Random(0x453d30);nativeEvents=[];originalEvents=[];errors=[];calls=eventsCount=0;found=True;created=E;randomValues=[0];randomIndex=0;queryValues=[1,0];queryIndex=0;animationResult=0;terrainResult=1;mutation=0;replay=io.BytesIO();replayCases=0;tape=[];capture=False;composeBodies=False;realRandom=False
COMPOSED={0x44d3c0,0x43dfa0,0x40e5c0,0x43d0f0,0x44c000,0x44d000,0x44c840,0x44cfd0,0x44e0c0,0x43e9c0,0x44f3c0,0x44f510,0x440e20,0x44edd0,0x44da20,0x43efe0,0x43f740,0x44d9f0,0x440c90,0x404dd0,0x4357a0,0x406310,0x43eee0,0x43ee10}
GLOBAL_TOKENS=(0x5371fc,0x537e88,0x537210,0x5430c4,0x534eac,0x532c0c,0x532c10,0x541334,0x5349dc)
COUNTS={0x44d3c0:1,0x43dfa0:0,0x4c8da0:6,0x43d0f0:2,0x10ff900:1,0x42df90:0,0x461a00:6,0x4b45f0:4,0x420370:1,0x420a10:2,0x48cf50:1,0x43eab0:0,0x4c7fa0:1,0x4c8060:1,0x4cbb60:4,0x4dbe10:2,0x4dbd60:1,0x44c000:1,0x4f63ec:1,0x4f6428:1,0x4f6286:1,0x4c7970:1,0x4c8220:1,0x4c82a0:1,0x4cd800:2,0x4dba00:1,0x4dbcd0:0,0x4f6584:0,0x44d000:1,0x4a3050:0,0x43e9c0:1,0x441030:1,0x4f6439:0,0x4a3810:2,0x44d9f0:0,0x440c90:0,0x44f3c0:0,0x44f510:0,0x404dd0:1,0x440e20:1,0x4357a0:0,0x406310:0,0x43eee0:3,0x43ee10:2,0x43f740:0,0x44da20:0,0x48ceb0:3,0x44edd0:0,0x4cda10:4,0x4207f0:2,0x4208e0:4,0x44c840:1,0x4db6e0:2,0x4db5f0:0,0x4db4d0:3,0x44e0c0:1,0x40e5c0:0,0x44cfd0:0,0x4bb030:0,0x4c96b0:0}
CDECL={0x10ff900,0x461a00,0x420370,0x48cf50,0x4f63ec,0x4f6428,0x4a3050,0x4a3810,0x48ceb0,0x4db5f0}

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0

def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def number(t,v,native=True):
 b=struct.pack('<d',v)
 if native:C.memmove(ptr(t,2),b,8)
 else:m.u.mem_write(t,b)
def text(t,native=True):
 if native:return C.string_at(ptr(t&~3)+(t&3))
 return bytes(m.u.mem_read(t,256)).split(b'\0')[0]
def flush():
 for t,v in zip(GLOBAL_TOKENS,struct.unpack('<9I',bytes(g)[:36])):put(t,[v])
 C.memmove(ptr(0x5262b0,3),bytes(g)[36:],12)
def raw(native):
 if native:flush();return bytes(heap)+C.string_at(ptr(GS),GN)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(GS,GN))
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('span',hex(t),n))
 return p
@Invoke
def sceneInvoke(_,q):
 e=Call();e.function=q.function;e.receiver=q.receiver;e.count=q.count;e.arguments[:q.count]=q.arguments[:q.count];return dependency(C.byref(ctx),C.byref(e),None)&0xffffffff
host=Host(None,lookup,Allocate(),Free(),sceneInvoke,Clock());ctx.scene=host

def effect(f,t,a,name,native):
 global randomIndex,queryIndex
 if f==0x44c000:
  for off in(8,12,0x128,0x12c,0x178,0x17c,0x190,0x194):put(t+off,[a[0]],native)
  for off in(16,0x130,0x180,0x198):put(t+off,[get(a[0]+108,native=native)[0]],native)
  put(t+20,[0,0,1001,2],native);put(t+0x2fc,[32,0],native);put(t+0x1a4,[0x52e1c4,0x52e1c4],native);return t
 if f==0x4f63ec:return created
 if f in(0x4f6428,0x4dbcd0,0x4f6584,0x4f6439):
  if f==0x4f6439:put(t,[0x52e1c4],native)
  return 0
 if f==0x10ff900:
  p=Physics();lib.claw_physics_construct(C.byref(p));p.acceleration[1]=2250;p.position[:]=[float(C.c_int32(get(E+0x450,native=native)[0]).value),float(C.c_int32(get(E+0x454,native=native)[0]).value),0.]
  target=BASE+0x1e000+0x28;b=bytes(p)
  if native:C.memmove(ptr(target,60),b,240)
  else:m.u.mem_write(target,b)
  return 0
 if f in(0x4b45f0,0x420370,0x48cf50,0x461a00,0x43d0f0,0x42df90):return 0
 if f==0x4c8da0:
  put(BASE+0x1c000+108,[BASE+0x1d000],native);put(BASE+0x1d000+16,[FAKE,0,BASE+0x1e000],native);return BASE+0x1c000
 if f==0x43eab0:return 1
 if f in(0x4c7fa0,0x4c8060):return 0
 if f==0x4cbb60:put(a[0]+76,[a[1],a[2]],native);return 0
 if f in(0x4dbe10,0x4dbd60):
  if f==0x4dbe10:put(t,[0,0,32,0],native)
  else:put(t+8,get(a[0]+8,2,native),native)
  return t
 if f==0x4f6286:
  if mutation==1:put(E+0x18c,[3],native)
  return (SOUND if t==SC+0x910 else SEQ) if found else 0
 if f==0x4c7970:put(t+0x170,[IMAGE]if found else[0],native);return int(found)
 if f==0x4c8220:put(t+8,[a[0]],native);return 0
 if f==0x4c82a0:
  if mutation==2:put(A+0x1a4,[1],native);put(A+0x19c,[0],native);put(A+0xcc,[1],native)
  return animationResult
 if f==0x4cd800:put(a[0]+80,[get(a[0]+80,native=native)[0]+3],native);return 0
 if f==0x4dba00:return stateIDs[(name if name is not None else text(a[0],native)).decode()]
 if f==0x4a3050 and realRandom:
  randomIndex+=1;out=U();assert native and lib.katherine_test_random(C.byref(ctx),C.byref(out));return out.value
 if f==0x4a3050:v=randomValues[randomIndex%len(randomValues)];randomIndex+=1;return v
 if f==0x4207f0:v=queryValues[queryIndex%len(queryValues)];queryIndex+=1;return v
 if f==0x4cda10:
  if mutation==3:put(PLAYER+76,[get(PLAYER+76,native=native)[0]+10],native)
  return terrainResult
 if f==0x441030:return get(0x537698+16,native=native)[0]+(a[0]-get(0x537698+8,native=native)[0])*4
 if f==0x4a3810:return (text(a[0],native)>text(a[1],native))-(text(a[0],native)<text(a[1],native))
 if f==0x43e9c0:return 0
 if f==0x44d000:
  if mutation==4:put(t+0x3c4,[50],native);put(t+0x184,[3],native);put(t+0x18c,[3],native)
  return 0
 if f==0x4db6e0:return 0
 if f==0x4db5f0:return 0x12345678
 if f in(0x4db4d0,0x44c840):return 0
 if f==0x44cfd0:put(get(t+12,native=native)[0]+8,[get(get(t+12,native=native)[0]+8,native=native)[0]|0x400000],native);return 0
 if f==0x44e0c0:put(get(t+12,native=native)[0]+0x10c,[0],native);return 0
 if f in(0x44d9f0,0x440c90,0x44f3c0,0x44f510,0x404dd0,0x440e20,0x4357a0,0x406310,0x43eee0,0x43ee10,0x43f740,0x44da20,0x48ceb0,0x44edd0,0x4208e0,0x40e5c0,0x4bb030,0x4c96b0):return 0
 raise AssertionError(('unadapted',hex(f),hex(t),a,name))
@Dep
def dependency(_,ev,user):
 q=ev.contents;a=list(q.arguments[:q.count])
 if ctx.composeAnimation and q.function in(0x4c8220,0x4c82a0,0x420a10):
  out=U();args=(U*len(a))(*a);assert lib.katherine_test_animation(q.function,q.receiver,args,len(a),C.byref(ctx),C.byref(out));return out.value
 if composeBodies and q.function==0x40e5c0:
  out=U();assert lib.katherine_test_gem(C.byref(ctx),dependency,None,q.receiver,C.byref(out));return out.value
 if composeBodies and q.function in COMPOSED:
  out=U();args=(U*len(a))(*a)
  if lib.katherine_test_common(q.function,q.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
 name=q.name if q.function in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060) else None
 if name is None and q.function in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060):name=text(a[0])
 nativeEvents.append((q.function,q.receiver,() if composeBodies and q.function in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060) else tuple(a),name,raw(True)));before=raw(True) if capture else None
 try:
  value=effect(q.function,q.receiver,a,name,True)
  if capture:
   after=raw(True);beforeWords=struct.unpack('<'+'I'*(len(before)//4),before);afterWords=struct.unpack('<'+'I'*(len(after)//4),after);patches=[(i,v)for i,(u,v)in enumerate(zip(beforeWords,afterWords))if u!=v];tape.append((q.function,q.receiver,a,value,patches,bytes(g),before))
  return value&0xffffffffffffffff
 except BaseException as e:errors.append(e);ctx.fault=99;return 0

def returned(pop,value=0):
 sp=m.u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop);m.u.reg_write(UC_X86_REG_EIP,ret)
SETRECT,COPYRECT,POINTRECT,EMPTYRECT=0x10ff810,0x10ff820,0x10ff830,0x10ff840

def hook(u,fn,size,user):
 global randomIndex
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if realRandom and fn==0x4a7dc0:returned(0,THREAD);return
 if realRandom and fn==0x4a3050:originalEvents.append((fn,0,(),None,raw(False)));randomIndex+=1;return
 if fn==POINTRECT:
  rect,x,y=m.read_words(sp+4,3);l,t,r,b=map(lambda v:C.c_int32(v).value,get(rect,4,False));x,y=C.c_int32(x).value,C.c_int32(y).value;returned(12,int(l<=x<r and t<=y<b));return
 if fn==EMPTYRECT:dest=m.read_words(sp+4,1)[0];put(dest,[0]*4,False);returned(4,1);return
 if realTileWorld is not None and fn in(0x4207f0,0x4cda10,0x4cd800,0x4cbb60):
  args=m.read_words(sp+4,COUNTS[fn]);parent=m.read_words(sp,1)[0]
  if fn!=0x4207f0 or not(0x4cbb60<=parent<0x4cdd00):originalEvents.append((fn,receiver,tuple(args),None,raw(False)))
  return
 if ctx.composeAnimation and fn in(0x4c8220,0x4c82a0,0x420a10):return
 if ctx.composeImages and fn==0x4c7970:return
 if fn==SETRECT:dest,*v=m.read_words(sp+4,5);m.write_words(dest,v);returned(20,1);return
 if fn==COPYRECT:dest,src=m.read_words(sp+4,2);m.write_words(dest,m.read_words(src,4));returned(8,1);return
 if composeBodies and fn in COMPOSED:return
 if composeBodies and fn==0x4dbcd0 and not(BASE<=receiver<BASE+SIZE):returned(0,0);return
 if composeBodies and fn in(0x4dbe10,0x4dbd60,0x4f6439):
  a=m.read_words(sp+4,COUNTS[fn]);effect(fn,receiver,a,None,False);returned(len(a)*4,receiver);return
 if fn not in COUNTS:return
 a=m.read_words(sp+4,COUNTS[fn]);t=0 if fn in CDECL else receiver;name=text(a[0],False)if fn in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060)else None
 if fn==0x4f6286:a=m.read_words(sp+4,2);output=a[1];a=a[:1]
 if composeBodies and fn in(0x441030,0x4a3810) and not(0x4548c0<=m.read_words(sp,1)[0]<0x454a10):
  value=effect(fn,t,a,name,False);returned(0 if fn in CDECL else len(a)*4,value);return
 originalEvents.append((fn,t,() if composeBodies and fn in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060) else tuple(a),name,raw(False)));value=effect(fn,t,a,name,False)
 if fn==0x4f6286:m.write_words(output,[value]);returned(8,int(bool(value)))
 else:returned(0 if fn in CDECL else len(a)*4,value)
m.u.hook_add(UC_HOOK_CODE,hook)
# Source-derived complete registry; actual CString names and raw class arenas.
class RegTable(C.Structure):_fields_=[('token',U),('kind',U),('words',U*12)]
class RegLiteral(C.Structure):_fields_=[('state',C.c_int32),('literalToken',U)]
class Reg(C.Structure):_fields_=[('nextId',U),('count',U),('tables',RegTable*96),('literalCount',U),('literals',RegLiteral*256),('errorGlobals',U*15)]
class RegContext(C.Structure):_fields_=[('heap',C.POINTER(C.c_uint8))]+[(n,U)for n in('heapBase','heapCapacity','heapUsed','emptyStringToken','metadataReceiverToken','metadataFunctionToken','errorLocation','fault')]
lib.claw_logic_state_context_defaults.argtypes=[C.POINTER(Reg),C.POINTER(RegContext)]
for n in('initialize','bootstrap'):getattr(lib,'claw_logic_state_'+n).argtypes=[C.POINTER(Reg),C.POINTER(RegContext),C.c_void_p,C.c_void_p]
registry=None;stateIDs={};nameTokens={};registryBytes=0

def prepare(seed=0):
 global registry,stateIDs,nameTokens,registryBytes,found,created,randomValues,randomIndex,queryValues,queryIndex,animationResult,terrainResult,mutation,realTileWorld
 resourceTokens.clear();realTileWorld=None
 heap[:]=rng.randbytes(SIZE);C.memmove(C.addressof(image),imageSeed,len(imageSeed));g.manager=SC;g.player=PLAYER;g.tick=seed*33;g.animationDelta=18;g.powerup=0;g.audioEnabled=1;g.volume=100;g.jumpDisabled=g.boss=0;g.damageScale=g.healthScale=g.rangeScale=1;ctx.scene=host;ctx.composeImages=ctx.composeAnimation=ctx.fault=0;found=True;created=E;randomValues=[seed];randomIndex=queryIndex=0;queryValues=[1,0];animationResult=0;terrainResult=1;mutation=0
 if registry is None:
  r=Reg();rc=RegContext(C.cast(ptr(REG_BASE),C.POINTER(C.c_uint8)),REG_BASE,0x40000,0,0,0,0,0,0);lib.claw_logic_state_context_defaults(C.byref(r),C.byref(rc));assert lib.claw_logic_state_initialize(C.byref(r),C.byref(rc),None,None)and not rc.fault;assert lib.claw_logic_state_bootstrap(C.byref(r),C.byref(rc),None,None)and not rc.fault;registryBytes=rc.heapUsed;registry=(C.string_at(ptr(REG_BASE),rc.heapUsed),[(t.token,list(t.words))for t in r.tables[:r.count]],list(r.errorGlobals))
 b,tables,diagnostics=registry;C.memmove(ptr(REG_BASE),b,len(b))
 for token,values in tables:put(token,values)
 put(0x544b14,diagnostics);nt=get(0x537698,9)
 for state in range(nt[2],nt[3]+1):token=get(nt[4]+(state-nt[2])*4)[0];name=text(token).decode();stateIDs[name]=state;nameTokens[name]=token
 put(A,[0x5137f0]);put(A+12,[SC]);put(A+108,[L,SECONDARY,0,CONTACT]);put(A+76,[1000,2000]);put(A+8,[0x80]);put(A+0x80,[0]);put(A+0x148,[0,0]);put(A+64,[0]);put(A+56,[0]);put(A+0xcc,[1]);put(A+0x10c,[100]);put(A+0x104,[10]);put(A+0x118,[-15,-50,15,50]);put(A+0x128,[-15,-40,15,40]);put(A+0x138,[0x80000000,0,0,0]);put(A+0x170,[IMAGE,LEAF]);put(A+0x16c,[1]);put(A+0x188,[0x513870,A,SEQ,ANI_RECORDS,0,0,0,0,0,0,0x3f800000]);put(A+0x1a4,[0]);put(A+0x19c,[0]);put(A+400,[SEQ]);put(L+24,[E,stateIDs['LS_IDLE']]);put(L+20,[E]);put(E,[0x50e2a4]);effect(0x44c000,E,[A],None,True);put(E,[0x50e2a4]);put(E+0x184,[seed%7]);put(E+0x18c,[2+seed%2]);put(E+0x3c4,[seed*40]);put(E+0x350,[SEQ]);put(E+0x460,[SEQ,SEQ,SEQ,0,0,0xabcdef01]);put(E+0x450,[1000,2000,SOUND,0]);put(SOUND+16,[POOL]);put(E+0x20,[2]);p=Physics();lib.claw_physics_construct(C.byref(p));p.acceleration[1]=2250;p.position[:]=[1000,2000,0];C.memmove(ptr(E+0x28,60),C.byref(p),240);put(SC+8,[CONTAINER]);put(SC+16,[SC+0x800]);put(SC+36,[WORLD]);put(SC+40,[SC+0x900]);put(SC+44,[SC+0xa00]);put(WORLD+0x38,[24576,7680]);put(PLAYER+108,[PL]);put(PL+20,[PR]);put(PL+28,[24]);put(PLAYER+76,[1100,2000]);put(PLAYER+0x10c,[100]);put(PR,[seed%2,0,0,0]);put(PR+20,[0]);put(IMAGE+20,[IMAGE_TABLE]);put(IMAGE+100,[1,950]);put(IMAGE_TABLE,[0]+[LEAF]*950);put(LEAF+16,[64,100,32,50,0,0]);put(SEQ+12,[ANI_TABLE,1]);put(ANI_TABLE,[ANI_RECORDS]);put(ANI_RECORDS,[0x512000,0,0,0,0,0,75,0,0,0,0,0]);put(0x52e1cc,[0x52e1c4]);put(0x546d5c,[SETRECT]);put(0x546d58,[COPYRECT]);put(0x546cd4,[POINTRECT]);put(0x546cdc,[EMPTYRECT]);put(0x533470,[32]);put(0x544d18,[0]);put(0x53c9c0,[0]);put(0x5376b8,[0]);flush()

def compare(fn,receiver=E,args=(),label='case',void=False,record=False):
 global calls,eventsCount,replayCases,randomIndex,queryIndex,capture
 capture=record
 flush();m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GS,C.string_at(ptr(GS),GN));m.write_words(0,[0x12345678]);nativeEvents.clear();originalEvents.clear();errors.clear();tape.clear();ctx.fault=0;before=raw(True);beforeG=bytes(g);ri,qi=randomIndex,queryIndex;args=(U*len(args))(*args);out=U();done=lib.claw_katherine_entry(fn,receiver,args,len(args),C.byref(ctx),dependency,None,C.byref(out));assert done and not ctx.fault and not errors,(label,done,ctx.fault,errors);afterG=bytes(g);afterIndexes=randomIndex,queryIndex;caseTape=list(tape);C.memmove(C.addressof(g),beforeG,len(beforeG));randomIndex,queryIndex=ri,qi;original=m.call(fn,receiver,pack(*args));C.memmove(C.addressof(g),afterG,len(afterG));randomIndex,queryIndex=afterIndexes
 if not void:assert out.value==original,(label,'EAX',hex(out.value),hex(original))
 if nativeEvents!=originalEvents:
  for i,(x,y)in enumerate(zip(nativeEvents,originalEvents)):
   if x!=y:print(label,'event',i,x[:4],y[:4]);print('state',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(x[4],y[4]))if a!=b][:16]);break
  raise AssertionError((label,'events',len(nativeEvents),len(originalEvents)))
 assert raw(True)==raw(False),(label,'complete state',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:20]);calls+=1;eventsCount+=len(nativeEvents)
 if record:
  writeReplay(fn,receiver,list(args),out.value,void,before,beforeG,raw(True),caseTape)
 return out.value
# Source asset transport, raw original-disc headers and ANI records; retail
# enumeration/binding remains a named dictionary service, never inferred pixels.
resourceTokens={};assetProfile=[]
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
class AniRecord(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
def realResources():
 import re
 resourceTokens.clear();assetProfile.clear();leaves=BASE+0x20000;root=IMAGE;table=IMAGE_TABLE;rows=[]
 for path in sorted((ROOT/'work/original-disc-assets/LEVEL4/IMAGES/KATHERINE').glob('*.PID')):
  b=path.read_bytes();ident=int(re.search(r'[0-9]+',path.stem)[0]);_,_,w,ht,x,y=struct.unpack_from('<6I',b);geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),w,ht,x,y);put(leaves+16,list(struct.unpack('<10I',bytes(geometry)))[:6]);rows.append((ident,leaves));assetProfile.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'id':ident,'width':w,'height':ht,'offsetX':x,'offsetY':y});leaves+=64
 assert len(rows)==44;minimum=min(i for i,_ in rows);maximum=max(i for i,_ in rows);put(root+20,[table]);put(root+100,[minimum,maximum]);put(table,[0]*(maximum+1))
 for ident,leaf in rows:put(table+ident*4,[leaf])
 resourceTokens[b'LEVEL_KATHERINE']=root;group=BASE+0x24000;recordAt=BASE+0x28000
 paths=sorted((ROOT/'work/original-disc-assets/LEVEL4/ANIS/KATHERINE').glob('*.ANI'))+[ROOT/'work/original-disc-assets/GAME/ANIS/NULL.ANI']
 for path in paths:
  b=path.read_bytes();sig,_,flags,count,pl=struct.unpack_from('<5I',b);assert sig==32;at=32+pl;seq=group;group+=0x200;pointers=[];eventNames=[];name=b'GAME_NULL'if path.name=='NULL.ANI'else('LEVEL_KATHERINE_'+path.stem).encode()
  for _ in range(count):
   tail=b[at:];buffer=(C.c_uint8*len(tail)).from_buffer_copy(tail);record=AniRecord();length=U();used=lib.claw_animation_decode_record(buffer,len(tail),SOUND,C.byref(record),C.byref(length));assert used;v=list(struct.unpack('<10I',bytes(record)));put(recordAt,[0x513af0,v[0],*v[1:9],0,v[9]]);pointers.append(recordAt);recordAt+=48
   if length.value:eventNames.append(tail[20:20+length.value].decode())
   at+=used
  assert at==len(b)and len(pointers)*4<=0x1c0;put(seq+12,[seq+0x40,count]);put(seq+0x40,pointers);resourceTokens[name]=seq;assetProfile.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'name':name.decode(),'records':count,'events':eventNames})
 assert recordAt<REG_BASE
 ctx.composeAnimation=ctx.composeImages=1;return assetProfile
_baseEffect=effect
def effect(f,t,a,name,native):
 if f==0x4f6286 and resourceTokens:
  key=name if name is not None else text(a[0],native);return resourceTokens.get(key,SOUND if t==SC+0x910 else 0) if found else 0
 if f==0x4c88e0:return 0
 return _baseEffect(f,t,a,name,native)
COUNTS[0x4c88e0]=4
class WorldState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class WorldContext(C.Structure):_fields_=[(n,U)for n in('scene','actor','logic','defaultType','width','height','registry')]+[('layers',U*3)]+[(n,U)for n in('entry','callback','flags')]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('text',C.c_char_p)]
WorldDep=C.CFUNCTYPE(U,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDep,C.c_void_p,C.POINTER(U)]
@WorldDep
def worldDep(s,c,e,user):
 if e.contents.function==0x4f6286:return 0x302c000
 if e.contents.function in(0x4c7970,0x4c7900):s.contents.actor[0x170//4]=resourceTokens[b'LEVEL_KATHERINE'];return 1
 if e.contents.function==0x4f4630:return 1
 raise AssertionError(('worldprofile',hex(e.contents.function)))
def retailRecord():
 row=json.load(open(WORK/'wwd-records.json'))['records'][0];w=row['words'];b=pack(*w)+b''.join(v.encode().ljust(n,b'\0')for v,n in zip(row['strings'],w[1:5]));assert len(b)==284+sum(w[1:5]);buffer=(C.c_uint8*len(b)).from_buffer_copy(b);s=WorldState();s.actor[:]=get(A,128);s.logic[:]=get(L,93);c=WorldContext(SC,A,L,2,row['worldWidth'],row['worldHeight'],SC+0x120,(U*3)(SC+0x500,SC+0x600,SC+0x700),0,0x453d30,0);out=(U*2)();assert lib.claw_world_object_load(buffer,len(b),C.byref(s),C.byref(c),worldDep,None,out)==len(b)and out[1]==1;put(A,s.actor);put(L,s.logic);put(A+112,[SECONDARY]);put(A+120,[CONTACT]);put(PR,[0]*78);return row
class Description(C.Structure):_fields_=[(n,U)for n in('type','width','height','inside','outside')]+[(n,C.c_int32)for n in('left','top','right','bottom')]
class CollisionActor(C.Structure):_fields_=[(n,U)for n in('flags','x','y','mode','type','stepX','stepY','support','token','deltaX','deltaY','ml','mt','mr','mb','hl','ht','hr','hb')]
class CollisionWorld(C.Structure):_fields_=[('cells',C.POINTER(U)),('rows',C.POINTER(U)),('width',C.c_int32),('height',C.c_int32),('sx',U),('sy',U),('descriptions',C.POINTER(Description)),('count',U),('actors',C.POINTER(CollisionActor)),('actorCount',U),('maximumStepX',U),('maximumStepY',U)]
lib.claw_world_point_attribute.argtypes=[C.POINTER(U),C.POINTER(U),C.c_int32,C.c_int32,U,U,C.POINTER(Description),U,U,U,U,U]
lib.claw_collision_horizontal_clear.argtypes=[C.POINTER(CollisionWorld),U,U,U,U,C.POINTER(U)]
lib.claw_collision_move.argtypes=[C.POINTER(CollisionWorld),C.POINTER(CollisionActor),U,U,U]
lib.claw_collision_place_on_ground.argtypes=[C.POINTER(CollisionWorld),C.POINTER(CollisionActor)]
realTileWorld=None

def retailWorld():
 import zlib
 global realTileWorld
 path=ROOT/'work/original-disc-assets/LEVEL4/WORLDS/WORLD.WWD';raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==json.load(open(WORK/'wwd-records.json'))['worldSHA256'];offset=struct.unpack_from('<I',raw,736)[0]
 if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
 for i in range(struct.unpack_from('<I',raw,732)[0]):
  ph=struct.unpack_from('<40I',raw,offset+160*i)
  if ph[2]&1:
   columns,rows=ph[24:26];assert ph[22:24]==(64,64);cells=list(struct.unpack_from('<'+'I'*(columns*rows),raw,ph[33]));break
 at=struct.unpack_from('<I',raw,740)[0];count=struct.unpack_from('<I',raw,at+8)[0];at+=32;ds=[]
 for _ in range(count):
  kind,_,w,height=struct.unpack_from('<4I',raw,at)
  if kind==1:ds.append(Description(kind,w,height,struct.unpack_from('<I',raw,at+16)[0],0,0,0,0,0));at+=20
  else:
   assert kind==2;outside,inside=struct.unpack_from('<2I',raw,at+16);ds.append(Description(kind,w,height,inside,outside,*struct.unpack_from('<4i',raw,at+24)));at+=40
 offsets=[columns*i for i in range(rows)];cs=(U*len(cells))(*cells);rs=(U*len(offsets))(*offsets);descriptions=(Description*len(ds))(*ds);realTileWorld=CollisionWorld(cs,rs,columns*64,rows*64,6,6,descriptions,len(ds),None,0,64,64);realTileWorld.storage=cs,rs,descriptions
 plane,cellMemory,rowMemory,descPointers,descMemory,actorList=BASE+0x19000,BASE+0x80000,BASE+0xb0000,BASE+0xb2000,BASE+0xc0000,BASE+0x1b000
 put(WORLD+12,[SC]);put(SC+8,[actorList]);put(actorList+20,[0]);put(WORLD+76,[descPointers]);put(WORLD+92,[plane]);put(WORLD+100,[64,64]);put(plane+32,[cellMemory,rowMemory]);put(plane+48,[columns*64,rows*64]);put(plane+140,[6,6]);put(cellMemory,cells);put(rowMemory,offsets)
 for i,d in enumerate(ds):put(descMemory+i*64,[0x513980 if d.type==1 else 0x5139c8,d.width,d.height,d.inside if d.type==1 else d.outside,d.inside,d.left,d.top,d.right,d.bottom])
 put(descPointers,[descMemory+i*64 for i in range(len(ds))]);return {'columns':columns,'rows':rows,'descriptions':count}
_preTileEffect=effect
def effect(f,t,a,name,native):
 if realTileWorld is not None and native:
  if f==0x4cbb60:
   actor=a[0];w=get(actor,128);c=CollisionActor(w[2],w[19],w[20],w[51],w[52],w[55],w[56],w[32],actor,w[86],w[87],*w[70:74],*w[74:78]);v=lib.claw_collision_move(C.byref(realTileWorld),C.byref(c),*a[1:]);put(actor+8,[c.flags]);put(actor+76,[c.x,c.y]);put(actor+0xcc,[c.mode]);put(actor+0x80,[c.support]);put(actor+0x158,[c.deltaX,c.deltaY]);return v
  if f==0x4207f0:return lib.claw_world_point_attribute(realTileWorld.cells,realTileWorld.rows,realTileWorld.width,realTileWorld.height,6,6,realTileWorld.descriptions,realTileWorld.count,*a,0,0)
  if f==0x4cda10:
   fault=U();v=lib.claw_collision_horizontal_clear(C.byref(realTileWorld),*a,C.byref(fault));assert not fault.value;return v
  if f==0x4cd800:
   actor=a[0];w=get(actor,128);c=CollisionActor(w[2],w[19],w[20],w[51],w[76],w[32],w[33],w[32],actor,w[86],w[87],*w[70:74],*w[74:78]);v=lib.claw_collision_place_on_ground(C.byref(realTileWorld),C.byref(c));put(actor+80,[c.y]);return v
 return _preTileEffect(f,t,a,name,native)
def deltas(before,after):
 old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);return [(i,v)for i,(u,v)in enumerate(zip(old,new))if u!=v]
def emitPatches(patches):
 replay.write(pack(len(patches)))
 for i,v in patches:replay.write(pack(i,v))
def writeReplay(fn,receiver,args,out,void,before,beforeG,after,caseTape):
 global replayCases
 replay.write(pack(fn,receiver,len(args),out,int(void),ctx.composeAnimation,ctx.composeImages,int(composeBodies),len(caseTape)));replay.write(pack(*args));replay.write(beforeG);replay.write(before);shadow=before
 for f,t,a,v,post,gbytes,pre in caseTape:
  replay.write(pack(f,t,len(a),v&0xffffffff));replay.write(pack(*a));emitPatches(deltas(shadow,pre));emitPatches(post);replay.write(gbytes);shadow=bytearray(pre)
  for i,value in post:struct.pack_into('<I',shadow,i*4,value)
  shadow=bytes(shadow)
 emitPatches(deltas(shadow,after));replayCases+=1

def writeCorpus():
 out=WORK/'replay.bin';out.write_bytes(pack(0x4b415448,replayCases,BASE,SIZE,GS,GN,imageStart,len(imageSeed))+imageSeed+replay.getvalue());return out
def nullPageOff():
 # Separate physical Windows TEB/FS from address0, so allocation failures fault
 # at the actual null receiver rather than the emulation's SEH scratch cell.
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 saved=m.u.context_save();teb,gdt=0x10ed000,0x10ee000
 def descriptor(base,access):return struct.pack('<I',0xffff|(base&0xffff)<<16)+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 m.u.mem_write(gdt+8,descriptor(0,0x9b));m.u.mem_write(gdt+16,descriptor(0,0x93));m.u.mem_write(gdt+24,descriptor(teb,0x93));m.u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.u.mem_write(teb,pack(0));m.u.mem_unmap(0,4096);return saved
