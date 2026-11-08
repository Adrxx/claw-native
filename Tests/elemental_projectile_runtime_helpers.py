"""Owned raw-heap weapon projectile oracle and explicit transport profile."""
import ctypes as C,struct,subprocess,hashlib,random,json,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/elemental-projectile-agent';U=C.c_uint32
sources=[ROOT/'Sources'/f'{n}.cpp' for n in ['ElementalProjectileRuntime','PlayerProjectileRuntime','BulletLogic','GenericEnemy','GenericEnemyStates','PlayerPhysics','PlayerLocomotion','PlayerAirStates','PlayerInitialization','PlayerEngine','PlayerDamage','CollisionResponse','TileCollision','RawTileDescriptionRuntime','ActorAnimationRuntime','AnimationEngine','AnimationOperations','ActorResourceBindings','PickupPointsRuntime','ActorDestruction','SpriteGeometry','SceneActorRuntime','WorldObjectRuntime','GameTiming','PIDRaster','PIDSurfaceRaster','PIDBlitter','WorldFileRuntime','WorldPlaneRuntime','CArrayRuntime','SpatialGridRuntime','SceneCameraRuntime','LogicStateRegistry','PlayerRangedHelpersRuntime']]
if not (WORK/'libElementalProjectile.dylib').exists()or any(p.stat().st_mtime>(WORK/'libElementalProjectile.dylib').stat().st_mtime for p in sources)or Path(__file__).stat().st_mtime>(WORK/'libElementalProjectile.dylib').stat().st_mtime:subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(WORK/'libElementalProjectile.dylib')],check=True)
lib=C.CDLL(str(WORK/'libElementalProjectile.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',U),('nameToken',U),('name',C.c_char_p)]
class Generic(C.Structure):_fields_=[(n,U)for n in('actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken')]+[('playerActor',U*128),('platformActor',U*128)]+[(n,U)for n in('tick','animationDelta','levelWord','forcedRandom','hitMode')]+[('defaults',U*24),('virtualFunctions',U*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(U)),('bitWordCount',C.c_size_t),('emptyStringToken',U),('bitHandlerToken',U)]
class Bullet(C.Structure):_fields_=[('generic',C.POINTER(Generic)),('states',C.POINTER(State)),('stateCount',C.c_size_t),('scene',Host),('imageRegistryToken',U),('imageRootToken',U),('imageRootHeader',U*28),('imageFrames',C.POINTER(U)),('imageFrameOrigin',C.c_int32),('imageFrameCount',C.c_size_t),('imageLeafToken',U),('imageLeafHeader',U*10),('fault',U)]
class Globals(C.Structure):_fields_=[(n,U)for n in('tick','animationDelta','magicDisabled','ownerToken','audioEnabled','masterVolume')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('bullet',C.POINTER(Bullet)),('composeAnimation',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x100000
A,L,E,SC,WORLD,PLANE,CELLS,ROWS,DESC,ROOTIMAGE,LEAF,FRAME,SEQ,SOUND,POOL,OWNER,FX,FXL,FLARE=[BASE+0x1000+i*0x1000 for i in range(19)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();generic=Generic();b=Bullet();c=Context();b.generic=C.pointer(generic);c.globals=C.pointer(g);c.bullet=C.pointer(b)
lib.claw_elemental_projectile_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(Generic)]
rng=random.Random(0x410900);animationResult=0;resource=1;allocation=1;collision=0;mode=8;mutation=0;randomWords=[];randomIndex=0;native_events=[];original_events=[];errors=[];calls=eventsCount=0
names=[('LS_IDLE',0x523148),('LS_FALLING',0x5236fc),('LS_EXPLODING',0x524418),('LS_STRIKE',0x52720c),('LS_DEAD',0x5234f4),('LS_JUMP',0x527204),('LS_MOVINGLEFT',0x5271f4),('LS_MOVINGRIGHT',0x5271e4),('LS_BOUNCE',0x5240b4),('LS_LIFTED',0x5271d8),('LS_THROWN',0x5271cc)]
states=(State*len(names))(*[State(2000+i,0,token,text.encode())for i,(text,token)in enumerate(names)]);generic.states=states;generic.stateCount=len(states);fall=(State*len(names))(*[State(2000+i,0x4742f0 if i==1 else 0,token,text.encode())for i,(text,token)in enumerate(names)]);b.states=fall;b.stateCount=len(fall)
TABLES=[0x538428,0x534ab0,0x534910,0x5375d8,0x537698];BACKS=[BASE+0x20000+i*0x1000 for i in range(5)]
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def pointer(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 raw=pack(*v)
 if native:C.memmove(pointer(t,len(v)),raw,len(raw))
 else:m.u.mem_write(t,raw)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(pointer(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def dbl(t,v,native=True):
 raw=struct.pack('<d',v)
 if native:C.memmove(pointer(t,2),raw,8)
 else:m.u.mem_write(t,raw)
def updates():return {0x537210:g.tick,0x5430c4:g.animationDelta,0x53724c:g.magicDisabled,0x5371fc:g.ownerToken,0x532c0c:g.audioEnabled,0x532c10:g.masterVolume}
def flush_globals():
 for t,v in updates().items():put(t,[v])
def raw(native):
 if native:flush_globals();return bytes(heap)+C.string_at(pointer(0x520000),0x30000)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snapshot(native):return raw(native)
@Lookup
def lookup(_,t,n):
 p=pointer(t,n)if not t%4 else 0
 if not p:errors.append(("lookup",hex(t),n))
 return p
c.scene=Host(None,lookup,Alloc(),Free(),Invoke(),Clock())
def cname(t):
 data=C.string_at(pointer(t),100)if imageStart<=t<=imageEnd else C.string_at(pointer(t),100)
 return data.split(b'\0')[0]
def effect(fn,t,args,name,native):
 global randomIndex
 if fn in(0x4c7fa0,0x4c8060):return 1
 if fn==0x4cbb60:
  put(args[0]+76,args[1:3],native);put(args[0]+204,[7 if get(args[0]+204,native=native)[0]==7 else mode],native);return collision
 if fn==0x4f6286:return (SEQ if t==SC+0x310 else ROOTIMAGE)if resource else 0
 if fn==0x4061b0:return SOUND if resource else 0
 if fn==0x4c8220:
  if mutation:put(t+8,[args[0]],native)
  return 0
 if fn==0x4c82a0:
  if mutation:put(A+420,[1],native);put(A+412,[0],native)
  return animationResult
 if fn==0x4dba00:return dict((n.encode(),2000+i)for i,(n,_)in enumerate(names))[name]
 if fn==0x4c8da0:
  if not allocation:return 0
  child=FLARE if name==b'Flare'else FX
  put(child+76,args[1:3],native);put(child+100,[args[3]],native);put(child+108,[FXL],native);return child
 if fn==0x4a3050:
  value=randomWords[randomIndex%len(randomWords)]if randomWords else 12345+randomIndex*13;randomIndex+=1;return value
 if fn==0x4f63ec:return E if allocation else 0
 if fn==0x4f6428:return 0
 if fn in(0x4b45f0,0x486e70,0x4a36f0,0x4db4d0,0x10ff100):return 0
 if fn==0x4db5f0:return 0x1234
 if fn==0x4db6e0:return 0
 raise AssertionError(('unexpected service',hex(fn),hex(t),args,name))
@Dep
def dependency(_,ev,user):
 try:
  e=ev.contents;a=tuple(e.arguments[:e.count]);native_events.append((e.function,e.receiver,()if e.function in(0x4f6286,0x4c7fa0,0x4c8060,0x4dba00,0x4061b0)else a,e.name or (cname(a[0])if e.function==0x4f6286 and a else None),snapshot(True)));return effect(e.function,e.receiver,a,e.name or (cname(a[0])if e.function==0x4f6286 and a else None),True)
 except Exception as exc:errors.append(exc);return 0
# Scene free is same explicitly observed original CRT delete boundary.
@Free
def free(_,t):native_events.append((0x4f6428,0,(t,),None,snapshot(True)))
c.scene.free=free
@Invoke
def sceneInvoke(_,e):
 native_events.append((e.function,e.receiver,tuple(e.arguments[:e.count]),None,snapshot(True)));return effect(e.function,e.receiver,tuple(e.arguments[:e.count]),None,True)
c.scene.call=sceneInvoke
abis={0x4f6286:(2,8),0x4c7fa0:(1,4),0x4c8060:(1,4),0x4cbb60:(4,16),0x4c8220:(1,4),0x4c82a0:(1,4),0x4dba00:(1,4),0x4c8da0:(6,24),0x4061b0:(1,4),0x4a3050:(0,0),0x4f63ec:(1,0),0x4f6428:(1,0),0x4b45f0:(4,16),0x4a36f0:(1,0),0x4db5f0:(0,0),0x4db6e0:(2,8),0x4db4d0:(3,12),0x10ff100:(1,0)}
def hook(uc,fn,size,user):
 if fn==0x486e70:return
 if fn not in abis:return
 n,pop=abis[fn];sp=uc.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,n));t=uc.reg_read(UC_X86_REG_ECX);name=None
 if fn in(0x4f6286,0x4c7fa0,0x4c8060,0x4dba00,0x4061b0):name=bytes(uc.mem_read(args[0],100)).split(b'\0')[0];normalized=()
 else:normalized=args
 if fn in(0x4a3050,0x4f63ec,0x4f6428,0x486e70,0x4a36f0,0x4db5f0,0x10ff100):t=0
 if fn==0x4c8da0:name=bytes(uc.mem_read(args[4],100)).split(b'\0')[0]
 original_events.append((fn,t,normalized,name,snapshot(False)));v=effect(fn,t,normalized,name,False)
 if fn==0x4f6286:m.write_words(args[1],[v]);v=1 if v else 0
 uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
transportHook=m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(kind=0):
 global generic,b,g,animationResult,collision,mode,resource,allocation,mutation,randomWords,imageMap,aniMap
 imageMap={};aniMap={};C.memmove(C.addressof(image),imageSeed,len(imageSeed));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);lib.claw_generic_enemy_context_defaults(C.byref(generic));g.tick=1000;g.animationDelta=17;g.ownerToken=OWNER;g.magicDisabled=0;g.audioEnabled=0;g.masterVolume=83;c.fault=b.fault=0;c.composeAnimation=0
 put(A,[0x5137f0]);put(A+8,[0x40000,SC]);put(A+76,[300,400]);put(A+100,[500,8,L,0]);put(A+120,[0]);put(A+128,[0]);put(A+204,[8]);put(A+320,[5,5]);put(A+0x148,[700,0]);put(A+0x158,[80]);put(A+0x170,[ROOTIMAGE,LEAF]);put(A+0x188,[0x513870,A,SEQ,0,0,0,1,0,0,0,0x3f800000]);put(A+0x190,[SEQ]);put(A+0x19c,[1]);put(A+0x1a4,[0]);put(L+12,[SC,0x40ff80,0,E,2001]);put(L+44,[0,0,0,0]);put(E,[[0x50b7bc,0x50b80c,0x50b844][kind]]);put(E+8,[A,A,L,0,0,1001,2,0]);put(E+296,[A,A,L,SEQ]);put(E+0x148,[SEQ]);put(E+0x150,[1,FLARE]);put(E+0x158,[0,2,1000,1250,1250]);put(E+0x170,[1,SEQ,SEQ,SOUND,0,0]);put(OWNER+0x124,[1]);put(SOUND+16,[POOL]);put(FXL+16,[0x10ff100]);put(SC+8,[SC+0x100]);put(SC+16,[SC+0x200]);put(SC+36,[WORLD]);put(SC+40,[SC+0x400]);put(SC+44,[SC+0x300]);put(WORLD+76,[DESC+0x100]);put(WORLD+92,[PLANE]);put(PLANE+32,[CELLS,ROWS]);put(PLANE+48,[1024,1024]);put(PLANE+140,[6,6]);put(ROWS,[i*16 for i in range(16)]);put(CELLS,[0]*256);put(DESC+0x100,[DESC]);put(DESC,[0x513980,64,64,0,0]);put(ROOTIMAGE+20,[FRAME]);put(ROOTIMAGE+100,[1,3]);put(FRAME,[LEAF]*8);put(LEAF+24,[7,5,1,0]);put(A+0x118,[0xfffffff9,0xfffffffc,6,4]);put(A+0x128,[0xfffffffa,0xfffffffc,7,4]);put(A+0x138,[0xfffffff9,0xfffffffc,6,4]);generic.tileManagerToken=WORLD;generic.sceneToken=SC
 for off in range(0x28,0x100,8):dbl(E+off,0)
 for off in(0x80,0x88,0x90):dbl(E+off,-1e9)
 for off in(0x98,0xa0,0xa8):dbl(E+off,1e9)
 for off in(0xe8,0xf0,0xf8):dbl(E+off,24)
 dbl(E+0x28,1);dbl(E+0x68,300);dbl(E+0x70,400);dbl(E+0x50,700 if kind<2 else 350);dbl(E+0x58,-400 if kind==2 else 0);dbl(E+0x40,2000 if kind==2 else 0);put(E+0xc8,[0,0]);put(E+0x120,[0,8 if kind==2 else 0]);put(E+0x164,[1250]);put(E+0x168,[1250]);put(E+0x150,[FLARE,0xabcdef01]);put(E+0x158,[0,2])
 for table,back in zip(TABLES,BACKS):put(table,[0,0,2000,2010,back,back+0x100,4,0,0]);put(back,[0]*11)
 put(BACKS[0]+4,[0x4742f0]);put(BACKS[1]+4,[0x410d60]);put(BACKS[2]+4,[0x4089d0]);put(BACKS[3]+4,[0x43b320,0x43b290]);nameTokens=[]
 for i,(text,literal)in enumerate(names):
  nt=BASE+0x2b000+i*64+12;encoded=text.encode()+b"\0";put(nt-12,[1,len(encoded)-1,len(encoded)-1]);C.memmove(pointer(nt),encoded,len(encoded));states[i].nameToken=nt;nameTokens.append(nt)
 put(BACKS[4],nameTokens);flush_globals();animationResult=collision=mutation=0;mode=8;resource=allocation=1;randomWords=[]
voids={0x411030,0x4114e0,0x411990,0x411cd0,0x410a80,0x408580,0x43ad20,0x408860,0x43b120,0x43b160,0x43b1a0,0x43b1e0,0x414010,0x408510,0x4c7970,0x456030,0x4c9e30,0x4c96b0,0x4741f0,0x474290,0x4742f0,0x473f40,0x4063b0,0x4dca10}
def compare(fn,t=E,args=(),label=None,record=False):
 global calls,eventsCount,randomIndex,captureReplay
 captureReplay=record;caseTape.clear()
 c.fault=b.fault=0;flush_globals();before=bytes(heap);beforeImage=bytes(image);beforeGlobals=bytes(g);randomIndex=0;native_events.clear();errors.clear();out=U();av=(U*len(args))(*args);ok=lib.claw_elemental_projectile_entry(fn,t,av,len(args),C.byref(c),dependency,None,C.byref(out));assert not errors,errors;assert ok and not c.fault,(label,hex(fn),'native',c.fault,b.fault)
 wanted=raw(True);events=list(native_events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),beforeImage,len(image));C.memmove(C.addressof(g),beforeGlobals,C.sizeof(g));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,beforeImage);randomIndex=0;original_events.clear();
 try:ret=m.call(fn,t,pack(*args))
 except UcError as exc:raise AssertionError((label,hex(fn),hex(m.u.reg_read(UC_X86_REG_EIP)),original_events[-3:]))from exc
 got=raw(False)
 if got!=wanted:
  differences=[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],wanted[i])for i in range(len(got))if got[i]!=wanted[i]];raise AssertionError((label,hex(fn),'heap/globals',differences[:24]))
 assert len(events)==len(original_events),(label,'event count',[(hex(e[0]),e[2],e[3])for e in events],[(hex(e[0]),e[2],e[3])for e in original_events])
 for i,(a,bx)in enumerate(zip(events,original_events)):assert a==bx,(label,hex(fn),'event',i,a,bx)
 if fn not in voids:assert ret==out.value,(label,hex(fn),'EAX',hex(ret),hex(out.value))
 C.memmove(C.addressof(heap),wanted[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,wanted[SIZE:],0x30000);calls+=1;eventsCount+=len(events)
 if record:writeReplay(fn,t,args,out.value,before+beforeImage[0x520000-imageStart:0x550000-imageStart],beforeGlobals,wanted)
 return ret
# Full source401000 bootstrap: actual allocated CString identity profile,
# complete class arrays and original global IDs are shared with the host.
class RegTable(C.Structure):_fields_=[('token',U),('kind',U),('words',U*12)]
class RegLiteral(C.Structure):_fields_=[('state',C.c_int32),('literalToken',U)]
class Reg(C.Structure):_fields_=[('nextId',U),('count',U),('tables',RegTable*96),('literalCount',U),('literals',RegLiteral*256),('errorGlobals',U*15)]
class RegContext(C.Structure):_fields_=[('heap',C.POINTER(C.c_uint8))]+[(n,U)for n in('heapBase','heapCapacity','heapUsed','emptyStringToken','metadataReceiverToken','metadataFunctionToken','errorLocation','fault')]
lib.claw_logic_state_context_defaults.argtypes=[C.POINTER(Reg),C.POINTER(RegContext)]
for n in('initialize','bootstrap'):getattr(lib,'claw_logic_state_'+n).argtypes=[C.POINTER(Reg),C.POINTER(RegContext),C.c_void_p,C.c_void_p]
registry=None;realStates=None;stateIDs={};nameTokens={}
oldFresh=fresh
def fresh(kind=0):
 global registry,realStates,states,fall
 oldFresh(kind);regBase=BASE+0x80000
 if registry is None:
  r=Reg();rc=RegContext(C.cast(pointer(regBase),C.POINTER(C.c_uint8)),regBase,0x80000,0,0,0,0,0,0);lib.claw_logic_state_context_defaults(C.byref(r),C.byref(rc));assert lib.claw_logic_state_initialize(C.byref(r),C.byref(rc),None,None)and not rc.fault;assert lib.claw_logic_state_bootstrap(C.byref(r),C.byref(rc),None,None)and not rc.fault;registry=(C.string_at(pointer(regBase),rc.heapUsed),[(t.token,list(t.words))for t in r.tables[:r.count]],list(r.errorGlobals))
 arena,tables,diagnostics=registry;C.memmove(pointer(regBase),arena,len(arena))
 for token,values in tables:put(token,values)
 put(0x544b14,diagnostics);table=get(0x537698,9);entries=[]
 for state in range(table[2],table[3]+1):
  token=get(table[4]+(state-table[2])*4)[0];name=C.string_at(pointer(token)).decode();stateIDs[name]=state;nameTokens[name]=token;entries.append(State(state,0,token,name.encode()))
 realStates=(State*len(entries))(*entries);generic.states=realStates;generic.stateCount=len(realStates);projectile=[];tab=get(0x538428,9)
 for e in entries:projectile.append(State(e.state,get(tab[4]+(e.state-tab[2])*tab[6])[0]if tab[2]<=e.state<=tab[3]else 0,e.nameToken,e.name))
 fall=(State*len(projectile))(*projectile);b.states=fall;b.stateCount=len(fall);put(L+28,[stateIDs['LS_FALLING']]);put(E+0x150,[FLARE,0xabcdef01]);flush_globals()
oldEffect=effect
def effect(fn,t,args,name,native):
 if fn==0x4dba00:return stateIDs[name.decode()]
 return oldEffect(fn,t,args,name,native)
class AniRecord(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
assetProfile=[];imageTokens={};aniTokens={}
def realResources(kind):
 import re
 imageTokens.clear();aniTokens.clear();name=['FIRESWORD','LIGHTNINGSWORD','ICESWORD'][kind];imageAt=BASE+0x40000;leafAt=BASE+0x43000
 for group,directory in(('GAME_BULLETS','GAME/IMAGES/BULLETS'),('GAME_PROJECTILES_'+name,'GAME/IMAGES/PROJECTILES/'+name)):
  rows=[];root=imageAt;table=root+0x100;imageAt+=0x1000
  for path in sorted((ROOT/'work/original-disc-assets'/directory).glob('*.PID')):
   data=path.read_bytes();ident=int(re.search(r'[0-9]+',path.stem)[0]);_,_,w,h,x,y=struct.unpack_from('<6I',data);geo=Geometry();lib.claw_sprite_set_geometry(C.byref(geo),w,h,x,y);put(leafAt+16,list(struct.unpack('<10I',bytes(geo)))[:6]);rows.append((ident,leafAt));leafAt+=64;profile={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'id':ident,'width':w,'height':h,'offsetX':x,'offsetY':y}
   if profile not in assetProfile:assetProfile.append(profile)
  assert rows;lo=min(i for i,_ in rows);hi=max(i for i,_ in rows);put(root+20,[table]);put(root+100,[lo,hi]);put(table,[0]*(hi+1))
  for ident,leaf in rows:put(table+ident*4,[leaf])
  imageTokens[group.encode()]=root
 path=ROOT/'work/original-disc-assets/GAME/ANIS'/f'{name}.ANI';data=path.read_bytes();sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;at=32+pl;seq=BASE+0x46000;table=seq+0x100;recordAt=BASE+0x46400;tokens=[];events=[]
 for i in range(count):
  buf=(C.c_uint8*(len(data)-at)).from_buffer_copy(data[at:]);rec=AniRecord();length=U();used=lib.claw_animation_decode_record(buf,len(buf),SOUND,C.byref(rec),C.byref(length));assert used;v=list(struct.unpack('<10I',bytes(rec)));put(recordAt,[0x513af0,v[0],*v[1:9],0,v[9]]);tokens.append(recordAt);recordAt+=48
  if length.value:events.append(data[at+20:at+20+length.value].decode())
  at+=used
 assert at==len(data);put(seq+12,[table,count]);put(table,tokens);aniTokens[('GAME_'+name).encode()]=seq;c.composeAnimation=1;profile={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'records':count,'events':events}
 if profile not in assetProfile:assetProfile.append(profile)
 return count
resourceEffect=effect
def effect(fn,t,args,name,native):
 if fn==0x4f6286 and imageTokens:return (aniTokens if t==SC+0x310 else imageTokens).get(name,0)if resource else 0
 if fn in(0x4208e0,0x4c88e0):return 0
 return resourceEffect(fn,t,args,name,native)
abis.update({0x4208e0:(4,16),0x4c88e0:(4,16)})
previousAnimationHook=hook
def hook(uc,fn,size,user):
 if c.composeAnimation and fn in(0x4c8220,0x4c82a0):return
 previousAnimationHook(uc,fn,size,user)
m.u.hook_del(transportHook);transportHook=m.u.hook_add(UC_HOOK_CODE,hook)
baseFresh=fresh
def fresh(kind=0):
 imageTokens.clear();aniTokens.clear();baseFresh(kind)
# Actual collision service on a deterministic tile world; scene actor list is
# explicitly empty here. Original4cbb60 executes its full tile helper graph.
class Description(C.Structure):_fields_=[(n,U)for n in('type','width','height','inside','outside')]+[(n,C.c_int32)for n in('left','top','right','bottom')]
class CollisionActor(C.Structure):_fields_=[(n,U)for n in('flags','x','y','mode','type','stepX','stepY','support','token','deltaX','deltaY','ml','mt','mr','mb','hl','ht','hr','hb')]
class World(C.Structure):_fields_=[('cells',C.POINTER(U)),('rows',C.POINTER(U)),('width',C.c_int32),('height',C.c_int32),('sx',U),('sy',U),('descriptions',C.POINTER(Description)),('count',U),('actors',C.POINTER(CollisionActor)),('actorCount',U),('maximumStepX',U),('maximumStepY',U)]
lib.claw_collision_move.argtypes=[C.POINTER(World),C.POINTER(CollisionActor),U,U,U]
collisionWorld=None

def installCollision(wall=False,wallColumn=8):
 global collisionWorld
 cells=[0]*256
 for x in range(16):cells[8*16+x]=1
 if wall:
  for y in range(8):cells[y*16+wallColumn]=1
 rows=[16*i for i in range(16)];descs=(Description*2)(Description(1,64,64,0,0,0,0,0,0),Description(1,64,64,1,0,0,0,0,0));cs=(U*256)(*cells);rs=(U*16)(*rows);collisionWorld=World(cs,rs,1024,1024,6,6,descs,2,None,0,64,64);collisionWorld.storage=cs,rs,descs
 put(CELLS,cells);put(ROWS,rows);put(DESC+0x100,[DESC,DESC+64]);put(DESC,[0x513980,64,64,0,0,0,0,0,0]);put(DESC+64,[0x513980,64,64,1,1,0,0,0,0]);put(WORLD+12,[SC]);put(SC+8,[BASE+0x17000]);put(BASE+0x17000+20,[0]);put(WORLD+100,[64,64]);put(A+0xdc,[10,10]);return collisionWorld
physicalEffect=effect
def effect(fn,t,args,name,native):
 if fn==0x4cbb60 and collisionWorld is not None and native:
  token=args[0];w=get(token,128);actor=CollisionActor(w[2],w[19],w[20],w[51],w[52],w[55],w[56],w[32],token,w[86],w[87],*w[70:74],*w[74:78]);v=lib.claw_collision_move(C.byref(collisionWorld),C.byref(actor),*args[1:]);put(token+8,[actor.flags]);put(token+76,[actor.x,actor.y]);put(token+0xcc,[actor.mode]);put(token+0x80,[actor.support]);put(token+0x158,[actor.deltaX,actor.deltaY]);return v
 return physicalEffect(fn,t,args,name,native)
collisionHook=hook
def hook(uc,fn,size,user):
 if fn==0x4cbb60 and collisionWorld is not None:
  sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,4));original_events.append((fn,uc.reg_read(UC_X86_REG_ECX),a,None,snapshot(False)));return
 collisionHook(uc,fn,size,user)
m.u.hook_del(transportHook);transportHook=m.u.hook_add(UC_HOOK_CODE,hook)
resetCollision=fresh
def fresh(kind=0):
 global collisionWorld
 collisionWorld=None;resetCollision(kind);put(A+0xd0,[0x2000000,4,0]);put(A+0x104,[25])

class RangeGlobals(C.Structure):_fields_=[('powerup',U),('masterVolume',U)]
class RangeContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(RangeGlobals)),('composeCreation',U),('composeImages',U),('fault',U)]
RangeDep=C.CFUNCTYPE(C.c_uint64,C.POINTER(RangeContext),C.POINTER(Call),C.c_void_p)
lib.claw_player_ranged_helpers_entry.argtypes=[U,C.POINTER(U),U,C.POINTER(RangeContext),RangeDep,C.c_void_p,C.POINTER(U)]
launchEffect=effect
def effect(fn,t,args,name,native):
 if fn==0x4c8da0 and name in(b'FireBullet',b'LightningBullet',b'IceBullet'):
  put(A+0xd0,[0x2000000,0,0],native);put(A+0x104,[0],native);put(A+0x148,[0,0],native);put(A+0x164,[0],native);put(A+0x170,[0,0],native);put(A+76,args[1:3],native);put(A+100,[args[3]],native);put(A+8,[args[5]],native);put(A+108,[L],native);put(L+28,[0],native);return A
 if fn==0x4f6286 and name in(b'CLAW_FIRESWORD',b'CLAW_LIGHTSWORD',b'CLAW_ICESWORD'):return SOUND
 return launchEffect(fn,t,args,name,native)
@RangeDep
def rangedDependency(_,e,u):return dependency(C.byref(c),e,u)
def launch(kind,direction):
 global calls,eventsCount
 player,primary,private=BASE+0x50000,BASE+0x51000,BASE+0x52000;put(player,[0]*128);put(player+12,[SC]);put(player+76,[300,400]);put(player+100,[500]);put(private,[0]*78);put(private,[direction]);put(private+84,[95,15]);put(private+232,[47]);put(SC+0x430,[0]);put(0x534eac,[0x26b8+kind]);flush_globals();before=bytes(heap);imageBefore=bytes(image);native_events.clear();original_events.clear();errors.clear();rg=RangeGlobals(0x26b8+kind,g.masterVolume);rc=RangeContext(c.scene,C.pointer(rg),0,0,0);args=(U*3)(player,primary,private);out=U();assert lib.claw_player_ranged_helpers_entry(0x41cc60,args,3,C.byref(rc),rangedDependency,None,C.byref(out))and not rc.fault and not errors;wanted=raw(True);events=list(native_events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),imageBefore,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,imageBefore);original_events.clear();ret=m.call(0x41cc60,0,pack(player,primary,private));assert ret==out.value==1;assert raw(False)==wanted and original_events==events;C.memmove(C.addressof(heap),wanted[:SIZE],SIZE);C.memmove(pointer(0x520000),wanted[SIZE:],0x30000);calls+=1;eventsCount+=len(events);return player,primary,private

# Exact native service tape for finite sanitizer replays. Each complete before
# and after span is captured, with only storage encoding reduced to word deltas.
captureReplay=False;caseTape=[];replay=io.BytesIO();replayCases=0
finalEffect=effect
def deltas(before,after):
 old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after)
 return [(i,v)for i,(u,v)in enumerate(zip(old,new))if u!=v]
def effect(fn,t,args,name,native):
 pre=raw(True)if native and captureReplay else None
 value=finalEffect(fn,t,args,name,native)
 if pre is not None:caseTape.append((fn,t,args,value,pre,deltas(pre,raw(True)),bytes(g)))
 return value
# Free invokes no mutation but remains an exact source event.
@Free
def free(_,t):
 native_events.append((0x4f6428,0,(t,),None,snapshot(True)))
 if captureReplay:
  state=raw(True);caseTape.append((0x4f6428,0,(t,),0,state,[],bytes(g)))
c.scene.free=free
def patches(rows):
 replay.write(pack(len(rows)))
 for i,v in rows:replay.write(pack(i,v))
def writeReplay(fn,t,args,out,before,globalsBefore,after):
 global replayCases
 replay.write(pack(fn,t,out,c.composeAnimation,len(caseTape),len(args),*args));replay.write(globalsBefore);replay.write(before);shadow=before
 for f,receiver,a,value,pre,post,gbytes in caseTape:
  # Native packets to leaf resource transports retain their literal arguments;
  # the normal differential separately checks names and source packet order.
  replay.write(pack(f,receiver,len(a),value,*a));patches(deltas(shadow,pre));patches(post);replay.write(gbytes);shadow=bytearray(pre)
  for i,v in post:struct.pack_into('<I',shadow,i*4,v)
  shadow=bytes(shadow)
 patches(deltas(shadow,after));replayCases+=1
def writeCorpus():
 path=WORK/'replay.bin';path.write_bytes(pack(0x454c454d,replayCases,BASE,SIZE,0x520000,0x30000,imageStart,len(imageSeed))+imageSeed+replay.getvalue());return path

def nullPageOff():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 saved=m.u.context_save();teb,gdt=0x10ed000,0x10ee000
 def desc(base,access):return struct.pack('<I',0xffff|(base&0xffff)<<16)+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 m.u.mem_write(gdt+8,desc(0,0x9b));m.u.mem_write(gdt+16,desc(0,0x93));m.u.mem_write(gdt+24,desc(teb,0x93));m.u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for r in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(r,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.u.mem_write(teb,pack(0));m.u.mem_unmap(0,4096);return saved
prefixes=0
def failure(fn,t=0,args=None,fault=2):
 global captureReplay,prefixes,eventsCount
 captureReplay=False;flush_globals();before=bytes(heap);beforeImage=bytes(image);bg=bytes(g);m.u.mem_write(BASE,before);m.u.mem_write(imageStart,beforeImage);c.fault=0;native_events.clear();original_events.clear();errors.clear();args=[A]if args is None else args;av=(U*len(args))(*args);out=U();assert not lib.claw_elemental_projectile_entry(fn,t,av,len(args),C.byref(c),dependency,None,C.byref(out))and c.fault==fault,(fn,c.fault);wanted=raw(True);events=list(native_events);C.memmove(C.addressof(g),bg,24);saved=nullPageOff()
 try:
  failed=False
  try:m.call(fn,t,pack(*args))
  except UcError:failed=True
  assert failed and raw(False)==wanted and original_events==events,('unsafe-prefix',hex(fn));prefixes+=1;eventsCount+=len(events)
 finally:m.u.mem_map(0,4096);m.u.context_restore(saved)
