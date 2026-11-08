"""Whole original AniRope oracle; raw state arenas and transports are explicit."""
import ctypes as C,struct,random,hashlib,json,subprocess,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/rope-agent';U=C.c_uint32
sources=['WorldPlaneRuntime','SpatialGridRuntime','SceneCameraRuntime','WorldFileRuntime','CArrayRuntime','PlayerAttackInput','RawTileDescriptionRuntime','LogicStateRegistry','RopeRuntime','ActorWrapperRuntime','StackedActorLifecycleRuntime','PlayerProjectileRuntime','BulletLogic','PowerupObjectRuntime','ItemPickupRuntime','WorldLootRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','ActorResourceBindings','AnimationEngine','AnimationOperations','PlayerPowerupRuntime','PlayerInputDispatch','PlayerEngine','PlayerPhysics','GameImageRuntime','SpriteGeometry','PIDRaster','PIDSurfaceRaster','PIDBlitter','PlayerDamage','PlayerInitialization','PlayerLocomotion','PlayerAirStates','CollisionResponse','TileCollision','LiftThrowRuntime','EnemyMotionAux','CommonEnemyEntries','HumanEnemy','HumanCombat','GenericEnemy','GenericEnemyStates','BreakableObjectRuntime']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in sources],'-o',str(WORK/'libRopeRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('user',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Physics(C.Structure):_fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3)for n in('acceleration','velocity','position','minimum','maximum','delta')]+[('stopped',U),('unused',U)]+[(n,C.c_double*3)for n in('remainder','maximumDelta','maximumVelocity')]
class PowerGlobals(C.Structure):_fields_=[(n,U)for n in('managerToken','playerToken','powerup','remaining','expired','musicDisabled','cycleRemaining','cycleIndex')]
class PowerContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(PowerGlobals)),('fault',U)]
class Animation(C.Structure):_fields_=[('animationDelta',U),('audioPosition',U)]
class ObjectContext(C.Structure):_fields_=[('scene',Host),('loot',C.c_void_p),('items',C.c_void_p),('powerups',C.POINTER(PowerContext)),('physics',C.POINTER(Physics)),('animation',C.POINTER(Animation))]+[(n,U)for n in('inputToken','curseEnabled','warpX','warpY','composeAnimation','composeCreation','fault')]
class Globals(C.Structure):_fields_=[(n,U)for n in('playerToken','tick','stageDelta','ignoreHazards','cheat','pixelScratch')]+[('defaults',U*4)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('powerups',C.POINTER(ObjectContext)),('lift',C.c_void_p),('composeAnimation',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*6),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x80000
A,L,E,SC,IM,FRAMES,PLAYER,PL,PR,INPUT,SEQ,ANI_TABLE,ANI_RECORDS,SR,POOL,TARGET,TL,TE=[BASE+0x1000+i*0x1000 for i in range(18)]
CLASS_DATA,NAME_DATA,NAME_CHARS,ALLOCATED,ALT_INPUT,ALT_L,ALT_PR=[BASE+0x20000+i*0x1000 for i in range(7)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();pg=PowerGlobals();p=Physics();ani=Animation();pc=PowerContext();oc=ObjectContext();c=Context();pc.globals=C.pointer(pg);oc.powerups=C.pointer(pc);oc.physics=C.pointer(p);oc.animation=C.pointer(ani);c.globals=C.pointer(g);c.powerups=C.pointer(oc)
lib=C.CDLL(str(WORK/'libRopeRuntime.dylib'));lib.claw_rope_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_rope_defaults.argtypes=[C.POINTER(Globals)];lib.claw_physics_construct.argtypes=[C.POINTER(Physics)]
rng=random.Random(0x403100);native_events=[];original_events=[];errors=[];tape=[];replay=io.BytesIO();replayCases=0;calls=eventsCount=0;allocation=E;lookupResult=2000;animationResult=0;mutation=0
GLOBAL_START,GLOBAL_SIZE=0x520000,0x30000
COUNTS={0x4f63ec:1,0x4f6428:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4dba00:1,0x4c82a0:1,0x4c79e0:2,0x4c8220:1,0x420a10:2,0x4a36f0:1,0x4db6e0:2,0x4db5f0:0,0x4db4d0:3,0x420910:1,0x4cd740:2,0x417c50:3}
CDECL={0x4f63ec,0x4f6428,0x4a36f0,0x4db5f0,0x417c50}
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def pointer(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 data=pack(*v)
 if native:C.memmove(pointer(t,len(v)),data,len(data))
 else:m.u.mem_write(t,data)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(pointer(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def number(t,v,native=True):
 data=struct.pack('<d',v)
 if native:C.memmove(pointer(t,2),data,8)
 else:m.u.mem_write(t,data)
def updates():return {0x537e88:pack(g.playerToken),0x537210:pack(g.tick),0x53720c:pack(g.stageDelta),0x537230:pack(g.ignoreHazards),0x537214:pack(g.cheat),0x544e8c:pack(g.pixelScratch),0x513e10:bytes(g.defaults),0x537204:pack(oc.inputToken),0x5430c4:pack(ani.animationDelta),0x534db8:bytes(p),0x5371fc:pack(pg.managerToken),0x534eac:pack(pg.powerup),0x534ea8:pack(pg.remaining),0x534eb8:pack(pg.expired),0x53c9c0:pack(pg.musicDisabled),0x534ec8:pack(pg.cycleRemaining),0x534ecc:pack(pg.cycleIndex)}
def flush():
 for t,b in updates().items():C.memmove(pointer(t,(len(b)+3)//4),b,len(b))
def raw(native):
 if native:flush();return bytes(heap)+C.string_at(pointer(GLOBAL_START),GLOBAL_SIZE)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
def snapshot(native):return raw(native)
@Lookup
def lookup(_,t,n):
 q=pointer(t,n)if t%4==0 else 0
 if not q:errors.append(('lookup',hex(t),n))
 return q
host=Host(None,lookup,Alloc(),Free(),Invoke(),Clock());c.scene=pc.scene=oc.scene=host
NAMES={0x522d54:b'LogicHit',0x522d48:b'LogicAttack',0x52313c:b'LEVEL_ROPE',0x523148:b'LS_IDLE',0x524d2c:b'CLAW_SWING',0x5246a8:b'CLAW_JUMP'}
def effect(fn,t,args,name,native):
 if mutation and fn in(0x4c7fa0,0x4c8060):
  put(A+0x6c,[L],native)
  if native:g.defaults[0]^=8
  else:put(0x513e10,[get(0x513e10,native=False)[0]^8],False)
 if fn==0x4f63ec:return allocation
 if fn==0x4f6428:return 0
 if fn in(0x4c7fa0,0x4c8060):return 1
 if fn==0x4c7970:put(t+0x170,[IM],native);return 1
 if fn==0x4dba00:return lookupResult
 if fn==0x4c82a0:
  if mutation:put(t-0x188+0x1a4,[1],native);put(t-0x188+0x19c,[0],native)
  return animationResult
 if fn in(0x4c79e0,0x4c8220,0x420a10):return 1
 if fn in(0x4a36f0,0x4db4d0,0x420910):return 0
 if fn==0x4db6e0:return 0
 if fn==0x4db5f0:return 0x1234
 if fn==0x4cd740:return 4
 if fn==0x417c50:put(args[1]+28,[5004],native);return 0
 raise AssertionError(('external',hex(fn),hex(t),args,name))
@Dep
def dependency(_,ev,user):
 e=ev.contents;args=list(e.arguments[:e.count]);native_events.append((e.function,e.receiver,tuple(args),e.name,snapshot(True)));before=bytes(heap)
 try:
  value=effect(e.function,e.receiver,args,e.name,True);after=bytes(heap);patches=[];pos=0
  while pos<SIZE:
   if before[pos]==after[pos]:pos+=1;continue
   start=pos
   while pos<SIZE and before[pos]!=after[pos]:pos+=1
   patches.append((start,after[start:pos]))
  tape.append((e.function,e.receiver,args,value,replayState(),patches));return value
 except BaseException as ex:errors.append(ex);c.fault=99;return 0
def returned(pop,value=0):
 sp=m.u.reg_read(UC_X86_REG_ESP);r=m.read_words(sp,1)[0];m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_EIP,r);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(u,address,size,user):
 if address not in COUNTS:return
 sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,COUNTS[address]);receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX);name=NAMES.get(args[0])if address in(0x4c7fa0,0x4c8060,0x4c7970,0x4dba00,0x4c79e0)else None;original_events.append((address,receiver,tuple(args),name,snapshot(False)));value=effect(address,receiver,args,name,False);returned(0 if address in CDECL else len(args)*4,value)
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(seed=0):
 global allocation,lookupResult,animationResult,mutation
 heap[:]=rng.randbytes(SIZE);C.memmove(C.addressof(image),imageSeed,len(imageSeed));lib.claw_rope_defaults(C.byref(g));assert bytes(g.defaults)==imageSeed[0x513e10-imageStart:0x513e20-imageStart];m.u.mem_write(0x513e10,bytes(g.defaults));g.playerToken=PLAYER;g.tick=0;g.stageDelta=18;g.ignoreHazards=g.cheat=0;g.pixelScratch=0x12345678;pg.managerToken=SC;pg.playerToken=PLAYER;pg.powerup=pg.remaining=pg.expired=pg.musicDisabled=pg.cycleRemaining=pg.cycleIndex=0;ani.animationDelta=16;ani.audioPosition=100;lib.claw_physics_construct(C.byref(p));c.scene=pc.scene=oc.scene=host;c.fault=oc.fault=pc.fault=0;c.composeAnimation=0;c.lift=None;oc.inputToken=INPUT;allocation=E;lookupResult=2000;animationResult=0;mutation=0
 put(A+0x6c,[L]);put(A+12,[SC]);put(L+24,[E,2000]);put(L+0xbc,[seed%3000]);put(A+0x148,[1500]);put(A+100,[0]);put(A+8,[0x80]);put(A+76,[1000,1200]);put(A+0x170,[IM]);put(IM+20,[FRAMES]);put(IM+100,[1,120]);put(FRAMES,[0]+[BASE+0x30000+i*0x40 for i in range(120)]);put(PLAYER+108,[PL]);put(PLAYER+12,[SC]);put(PL+20,[PR]);put(PL+28,[24]);put(PL+0x2c,[-10000,10000,-10000,10000]);put(PL+0x130,[0]);put(PR,[0,0,0,0]);put(PR+300,[0]);put(PR+0x134,[0]);put(PR+0x11c,[0]);put(PR+0x114,[0]);put(PR+0xf8,[0]);put(PR+248,[0]);put(PR+284,[0]);put(PR+60,[0]);put(INPUT+4,[0,0,0xffffffff]);put(PLAYER+76,[1000,1200]);put(PLAYER+8,[0x80]);put(PLAYER+0x174,[0]);put(PR+0x130,[0]);put(PLAYER+0xcc,[3]);put(PLAYER+0x40,[2]);put(PLAYER+0x118,[-16,-52,16,60]);put(PLAYER+0x128,[-15,-45,22,52]);put(PLAYER+0x138,[0x80000000,0,0,0]);put(SC+20,[0]);put(SC+36,[SC+0x100]);put(SC+40,[SR]);put(SC+44,[SR]);put(TARGET+108,[TL]);put(TL+24,[TE]);put(TE+32,[1]);put(TE+0x2fc,[32,1]);put(E,[0x50b03c]);put(E+12,[A,L,0,0,2001,2]);put(E+44,[A,L]);put(E+0x14,[0,0,1001]);put(E+0x140,[0,27]);q=Physics();lib.claw_physics_construct(C.byref(q));C.memmove(pointer(E+0x48,60),C.byref(q),C.sizeof(q));number(E+0x70,40);number(E+0x88,seed%120);put(0x534820,[0,SC+0x300,2000,2010,CLASS_DATA,CLASS_DATA+0x100,4,0,0xfeed]);put(CLASS_DATA,[0x4038d0]+[0]*10);put(0x537698,[0,SC+0x300,2000,2010,NAME_DATA,NAME_DATA+0x100,4,NAME_DATA,0]);put(NAME_DATA,[NAME_CHARS+0x100*n for n in range(11)]);put(0x544b4c,[0x543210]);
 for n in range(11):put(NAME_CHARS+0x100*n-12,[1,7,7]);C.memmove(pointer(NAME_CHARS+0x100*n,3),b'LS_IDLE\0',8)
 flush()
def sync():flush();m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GLOBAL_START,C.string_at(pointer(GLOBAL_START),GLOBAL_SIZE));m.u.mem_write(0x513e10,bytes(g.defaults));m.write_words(0,[0x12345678])
def replayState():return bytes(g)+bytes(pg)+bytes(p)+bytes(ani)+pack(oc.inputToken,c.composeAnimation)
def compare(fn,receiver=0,args=(),label='case',void=False,record=False):
 global calls,eventsCount,replayCases
 sync();native_events.clear();original_events.clear();errors.clear();tape.clear();c.fault=0;beforeHeap=bytes(heap);beforeImage=C.string_at(pointer(GLOBAL_START),GLOBAL_SIZE);beforeState=replayState();beforeG, beforePG=bytes(g),bytes(pg);v=(U*len(args))(*args);out=U();supported=lib.claw_rope_entry(fn,receiver,v,len(args),C.byref(c),dependency,None,C.byref(out));assert supported==1 and not c.fault and not errors,(label,'native',supported,c.fault,errors);afterG,afterPG=bytes(g),bytes(pg);C.memmove(C.addressof(g),beforeG,len(beforeG));C.memmove(C.addressof(pg),beforePG,len(beforePG));original=m.call(fn,receiver,pack(*args));C.memmove(C.addressof(g),afterG,len(afterG));C.memmove(C.addressof(pg),afterPG,len(afterPG))
 if not void:assert out.value==original,(label,'EAX',hex(out.value),hex(original))
 if native_events!=original_events:
  for n,(x,y)in enumerate(zip(native_events,original_events)):
   if x!=y:print(label,'event',n,x[:4],y[:4]);print('diff',[(hex(BASE+j)if j<SIZE else hex(GLOBAL_START+j-SIZE),a,b)for j,(a,b)in enumerate(zip(x[4],y[4]))if a!=b][:16]);break
  raise AssertionError((label,'full ordered service snapshots',len(native_events),len(original_events)))
 assert raw(True)==raw(False),(label,'complete final buffer',[(hex(BASE+j)if j<SIZE else hex(GLOBAL_START+j-SIZE),a,b)for j,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:20])
 if record or calls%37==0:
  replay.write(pack(fn,receiver,len(args),*(list(args)+[0]*(4-len(args))),out.value,int(void),len(tape))+beforeState+replayState()+beforeHeap+bytes(heap)+beforeImage+C.string_at(pointer(GLOBAL_START),GLOBAL_SIZE))
  for f,t,aa,value,state,patches in tape:
   replay.write(pack(f,t,len(aa),*(aa+[0]*(6-len(aa))),value,len(patches))+state)
   for offset,data in patches:replay.write(pack(offset,len(data))+data)
  replayCases+=1
 calls+=1;eventsCount+=len(native_events);return out.value
# Source-derived full401000 name/class fixture from frozen registry module.
# Physical arena policy is explicit; this task doesn't repeat its original oracle.
class RegTable(C.Structure):_fields_=[('token',U),('kind',U),('words',U*12)]
class RegLiteral(C.Structure):_fields_=[('state',C.c_int32),('literalToken',U)]
class Reg(C.Structure):_fields_=[('nextId',U),('count',U),('tables',RegTable*96),('literalCount',U),('literals',RegLiteral*256),('errorGlobals',U*15)]
class RegContext(C.Structure):_fields_=[('heap',C.POINTER(C.c_uint8))]+[(n,U)for n in('heapBase','heapCapacity','heapUsed','emptyStringToken','metadataReceiverToken','metadataFunctionToken','errorLocation','fault')]
lib.claw_logic_state_context_defaults.argtypes=[C.POINTER(Reg),C.POINTER(RegContext)]
for name in('initialize','bootstrap'):getattr(lib,'claw_logic_state_'+name).argtypes=[C.POINTER(Reg),C.POINTER(RegContext),C.c_void_p,C.c_void_p]
registryProfile=None;registryHeapUsed=0;registryIdleToken=0
REG_BASE=BASE+0x40000
basePrepare=prepare
def prepare(seed=0):
 global registryProfile,registryHeapUsed,registryIdleToken
 basePrepare(seed)
 if registryProfile is None:
  registry=Reg();rc=RegContext(C.cast(pointer(REG_BASE),C.POINTER(C.c_uint8)),REG_BASE,0x40000,0,0,0,0,0,0);lib.claw_logic_state_context_defaults(C.byref(registry),C.byref(rc));assert lib.claw_logic_state_initialize(C.byref(registry),C.byref(rc),None,None)==1 and not rc.fault;assert lib.claw_logic_state_bootstrap(C.byref(registry),C.byref(rc),None,None)==1 and not rc.fault,('source-derived registry fixture',rc.fault,rc.heapUsed)
  tables=[]
  for t in registry.tables[:registry.count]:tables.append((t.token,list(t.words)))
  registryProfile=(C.string_at(pointer(REG_BASE),rc.heapUsed),tables,list(registry.errorGlobals));registryHeapUsed=rc.heapUsed
 arena,tables,diagnostics=registryProfile;C.memmove(pointer(REG_BASE),arena,len(arena))
 for token,values in tables:put(token,values)
 put(0x544b14,diagnostics)
 table=get(0x537698,9);registryIdleToken=get(table[4]+(2000-table[2])*table[6])[0];assert registryIdleToken>=REG_BASE and registryIdleToken!=0x523148 and C.string_at(pointer(registryIdleToken),8)==b'LS_IDLE\0'
 flush()
class Items(C.Structure):_fields_=[('scene',Host),('loot',C.c_void_p),('player',C.c_void_p)]+[(n,U)for n in('playerToken','playerPrimaryToken','playerPrivateToken','managerToken','animationDelta','stageDelta','tick','audioEnabled','masterVolume','lastSoundTick','lastSoundToken','auxiliaryManagerToken','auxiliarySceneToken','composeCreation','fault')]
items=Items();items.scene=host;oc.items=C.addressof(items)
priorPrepareItems=prepare
def prepare(seed=0):
 priorPrepareItems(seed);items.scene=host;items.playerToken=PLAYER;items.playerPrimaryToken=PL;items.playerPrivateToken=PR;items.managerToken=SC;items.stageDelta=g.stageDelta;items.animationDelta=ani.animationDelta;items.tick=g.tick;items.fault=0;oc.items=C.addressof(items)
class WorldState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class WorldContext(C.Structure):_fields_=[(n,U)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('width',C.c_int32),('height',C.c_int32),('registry',U),('layers',U*3),('entry',U),('callback',U),('flags',U)]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('text',C.c_char_p)]
class WorldInfo(C.Structure):_fields_=[('consumed',U),('created',U)]
WorldDep=C.CFUNCTYPE(U,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDep,C.c_void_p,C.POINTER(WorldInfo)]
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
@WorldDep
def worldService(s,ctx,e,user):
 ev=e.contents
 if ev.function==0x4f6286:return ALLOCATED
 if ev.function in(0x4c7970,0x4c7900):s.contents.actor[0x170//4]=IM;s.contents.actor[0x174//4]=BASE+0x30000;s.contents.actor[0x16c//4]=1;return 1
 if ev.function==0x4f4630:return 1
 raise AssertionError(('WWD source fixture dependency',hex(ev.function)))
profile=json.loads((WORK/'wwd-profile.json').read_text());pidProfiles={r['level']:r for r in profile['resources']};loaderProfiles=0

def actualRecord(row):
 global loaderProfiles
 w=row['words'];ss=row['strings'];data=pack(*w)+b''.join(s.encode('latin1')+bytes(n-len(s))for s,n in zip(ss,w[1:5]));assert hashlib.sha256(data).hexdigest()==row['rawSHA256'];buf=(C.c_uint8*len(data)).from_buffer_copy(data);state=WorldState((U*128)(*get(A,128)),(U*93)(*get(L,93)));wc=WorldContext(SC,A,L,2,row['worldWidth'],row['worldHeight'],SC+0x900,(U*3)(SC+0xa00,SC+0xb00,SC+0xc00),ALLOCATED,0x403100,0);info=WorldInfo();assert lib.claw_world_object_load(buf,len(data),C.byref(state),C.byref(wc),worldService,None,C.byref(info))==len(data)and info.created;put(A,list(state.actor));put(L,list(state.logic));put(A+0x170,[IM]);put(L+28,[0]);put(IM+20,[FRAMES]);put(IM+100,[1,120]);put(FRAMES,[0]+[BASE+0x30000+i*0x40 for i in range(120)])
 for n,file in enumerate(pidProfiles[row['level']]['headers']):
  assert int(Path(file['name']).stem.removeprefix('FRAME'))==n+1;_,_,width,height,x,y,*_=file['header'];geom=Geometry();lib.claw_sprite_set_geometry(C.byref(geom),width,height,x,y);put(BASE+0x30000+n*0x40+16,[geom.width,geom.height,geom.halfWidth,geom.halfHeight,geom.offsetX,geom.offsetY])
 put(PL+0x2c,[50,row['worldWidth']-50,50,row['worldHeight']-50]);loaderProfiles+=1
FAKEA,FAKEB=0x10ff900,0x10ff910;COUNTS.update({FAKEA:0,FAKEB:0});priorQueuedEffect=effect

def effect(fn,t,args,name,native):
 if fn==FAKEA:put(E+0x14,[FAKEB],native);put(E+0x18,[FAKEA],native);number(E+0x48,123,native);return 0
 if fn==FAKEB:
  if native:g.tick=5000
  else:put(0x537210,[5000],False)
  number(E+0x70,30,native);return 0
 return priorQueuedEffect(fn,t,args,name,native)
# Actual retail player ANI records; resource dictionary is a physical bool/out
# transport normalized to the frozen resource-token adapter.
class AnimationRecord(C.Structure):_fields_=[(n,U)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AnimationRecord),C.POINTER(U)]
JUMP_SEQ,JUMP_TABLE,JUMP_RECORDS,DECODE_BYTES,PLAYER_IMAGE,PLAYER_FRAMES,PLAYER_LEAVES=BASE+0x27000,BASE+0x28000,BASE+0x29000,BASE+0x3d000,BASE+0x36000,BASE+0x37000,BASE+0x38000
aniDecodes=0;aniSourceHashes={};animationMode=False
oldAnimationEffect=effect

def effect(fn,t,args,name,native):
 if fn==0x4f6286:return SEQ if args[0]==0x524d2c else JUMP_SEQ if args[0]==0x5246a8 else 0
 if fn in(0x4c88e0,0x4208e0):return 0
 return oldAnimationEffect(fn,t,args,name,native)

# Install this first-class transport ahead of the ordinary hook's fallthrough.
def dictionaryHook(u,address,size,user):
 if address!=0x4f6286 or not animationMode:return
 sp=u.reg_read(UC_X86_REG_ESP);name,out=m.read_words(sp+4,2);receiver=u.reg_read(UC_X86_REG_ECX);hint=NAMES.get(name);original_events.append((address,receiver,(name,),hint,snapshot(False)));value=effect(address,receiver,[name],hint,False);m.write_words(out,[value]);returned(8,int(bool(value)))
m.u.hook_add(UC_HOOK_CODE,dictionaryHook)

def actualAnimation():
 global aniDecodes,animationMode
 animationMode=True;imageIDs=set()
 for name,seq,table,records in(('SWING',SEQ,ANI_TABLE,ANI_RECORDS),('JUMP',JUMP_SEQ,JUMP_TABLE,JUMP_RECORDS)):
  data=(ROOT/'work/original-disc-assets/CLAW/ANIS'/f'{name}.ANI').read_bytes();aniSourceHashes[name]=hashlib.sha256(data).hexdigest();count,pathLength=struct.unpack_from('<2I',data,12);pos=32+pathLength;put(seq+12,[table,count]);put(table,[records+i*64 for i in range(count)])
  for i in range(count):
   tail=data[pos:];buf=(C.c_uint8*len(tail)).from_buffer_copy(tail);rec=AnimationRecord();length=U();used=lib.claw_animation_decode_record(buf,len(tail),0,C.byref(rec),C.byref(length));assert used;token=records+i*64;sync();m.u.mem_write(DECODE_BYTES,tail);m.call(0x4d76e0,token,pack(SC+44,DECODE_BYTES));actual=m.read_words(token,12);assert [getattr(rec,n)for n,_ in AnimationRecord._fields_]==[actual[1]&0xffff]+actual[2:10]+[actual[11]];assert used==20+m.read_words(0x543174,1)[0];put(token,actual);put(0x543174,m.read_words(0x543174,1));pos+=used;aniDecodes+=1;imageIDs.add(rec.parameter)
  assert pos==len(data)
 put(PLAYER+0x170,[PLAYER_IMAGE]);put(PLAYER_IMAGE+20,[PLAYER_FRAMES]);put(PLAYER_IMAGE+100,[1,608]);put(PLAYER_FRAMES,[0]*609)
 for i,frame in enumerate(sorted(imageIDs)):
  assert 1<=frame<=608;path=ROOT/'work/original-disc-assets/CLAW/IMAGES'/f'FRAME{frame:03}.PID';header=struct.unpack_from('<6I',path.read_bytes());_,_,width,height,x,y=header;leaf=PLAYER_LEAVES+i*64;geom=Geometry();lib.claw_sprite_set_geometry(C.byref(geom),width,height,x,y);put(leaf+16,[geom.width,geom.height,geom.halfWidth,geom.halfHeight,geom.offsetX,geom.offsetY]);put(PLAYER_FRAMES+frame*4,[leaf])
 put(PLAYER+0x188,[0x513870,PLAYER,0,0,0,0,0,1,0,0,0x3f800000]);c.composeAnimation=oc.composeAnimation=1
 for fn in(0x4c79e0,0x4c8220,0x4c82a0,0x420a10):COUNTS.pop(fn,None)

basePrepareAnimation=prepare

def prepare(seed=0):
 global animationMode
 animationMode=False;basePrepareAnimation(seed);c.composeAnimation=oc.composeAnimation=0;COUNTS.update({0x4c79e0:2,0x4c8220:1,0x4c82a0:1,0x420a10:2})
class LiftGlobals(C.Structure):_fields_=[(n,U)for n in('playerToken','inputToken','stageDelta','animationDelta','tick','powerup','pixelScratch','audioEnabled','masterVolume','strongThrow')]+[('defaults',U*24)]
class LiftContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(LiftGlobals)),('physics',C.POINTER(Physics)),('attack',C.c_void_p),('enemyWordCount',U),('composeAnimation',U),('fault',U),('core',C.c_void_p)]
lg=LiftGlobals();lc=LiftContext();lc.scene=host;lc.globals=C.pointer(lg);lc.physics=C.pointer(p);lc.enemyWordCount=260
lib.claw_lift_throw_defaults.argtypes=[C.POINTER(LiftGlobals)]
baseReplayState=replayState

def replayState():return baseReplayState()+bytes(lg)+pack(bool(c.lift))

def composeHeld(seed):
 lib.claw_lift_throw_defaults(C.byref(lg));lc.scene=host;lc.physics=C.pointer(p);lc.fault=0;lc.composeAnimation=c.composeAnimation;lg.audioEnabled=1;lg.masterVolume=100;c.lift=C.addressof(lc);put(PLAYER+0x74,[A]);h=seed%3;put(PR+0x12c,[TARGET]);put(TE+32,[h]);put(TE+0x2fc,[32,seed%2]);put(TE+20,[0]);put(TL+28,[1000]);put(PR+4,[seed%2]);put(PR+0x124,[SEQ]);put(PR+0x134,[A]);put(PL+28,[5007]);put(INPUT+4,[1]);put(A+0xfc,[0x26af]);put(A+0xd0,[0x100])
