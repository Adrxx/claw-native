"""Owned PunkRat whole-original oracle; physical child/audio transport explicit."""
import ctypes as C,struct,subprocess,hashlib,random,json,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/punk-rat-agent';U=C.c_uint32
SOURCES=['PunkRatRuntime','CommonEnemyEntries','HumanEnemy','GenericEnemy','GenericEnemyStates','ActorWrapperRuntime','ActorResourceBindings','ActorDestruction','ActorAnimationRuntime','AnimationEngine','AnimationOperations','PlayerPhysics','PlayerLocomotion','PlayerAirStates','PlayerEngine','PlayerInitialization','PlayerDamage','SpriteGeometry','PIDRaster','PIDSurfaceRaster','PIDBlitter','SceneActorRuntime','WorldObjectRuntime','GameTiming','LogicStateRegistry','WorldFileRuntime','WorldPlaneRuntime','CArrayRuntime','SpatialGridRuntime','SceneCameraRuntime','TileCollision','CollisionResponse']
sources=[ROOT/'Sources'/f'{n}.cpp'for n in SOURCES]
if not(WORK/'libPunkRat.dylib').exists()or any(p.stat().st_mtime>(WORK/'libPunkRat.dylib').stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(WORK/'libPunkRat.dylib')],check=True)
lib=C.CDLL(str(WORK/'libPunkRat.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',U),('nameToken',U),('name',C.c_char_p)]
class Generic(C.Structure):_fields_=[(n,U)for n in('actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken')]+[('playerActor',U*128),('platformActor',U*128)]+[(n,U)for n in('tick','animationDelta','levelWord','forcedRandom','hitMode')]+[('defaults',U*24),('virtualFunctions',U*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(U)),('bitWordCount',C.c_size_t),('emptyStringToken',U),('bitHandlerToken',U)]
class Bullet(C.Structure):_fields_=[('generic',C.POINTER(Generic)),('states',C.POINTER(State)),('stateCount',C.c_size_t),('scene',Host),('imageRegistryToken',U),('imageRootToken',U),('imageRootHeader',U*28),('imageFrames',C.POINTER(U)),('imageFrameOrigin',C.c_int32),('imageFrameCount',C.c_size_t),('imageLeafToken',U),('imageLeafHeader',U*10),('fault',U)]
class SharedStates(C.Structure):_fields_=[('attackerToken',U),('attackerActor',U*128),('playerPrivate',U*78),('strikeCounter',U),('audioEnabled',U),('audioPosition',U),('resources',C.c_void_p),('resourceCount',C.c_size_t)]
class Globals(C.Structure):_fields_=[(n,U)for n in('tick','animationDelta','randomDisabled','audioEnabled','masterVolume','powerup')]+[('healthScale',C.c_float)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('generic',C.POINTER(Generic)),('sharedStates',C.POINTER(SharedStates))]+[(n,U)for n in('composeAnimation','composeImages','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE,GS,GN=0x3000000,0x200000,0x520000,0x30000
A,L,E,SC,WORLD,PLAYER,PL,PP,SECONDARY,CONTACT,IMAGE,TABLE,LEAF,SEQ,SOUND,POOL,CHILD,CL,CP=[BASE+0x1000+i*0x1000 for i in range(19)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();generic=Generic();sharedStates=SharedStates();c=Context();c.globals=C.pointer(g);c.generic=C.pointer(generic);c.sharedStates=C.pointer(sharedStates)
lib.claw_punk_rat_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(Generic)]
rng=random.Random(0x474330);nativeEvents=[];originalEvents=[];errors=[];calls=eventsCount=0;found=True;created=E;createdChild=CHILD;randomValues=[123];randomIndex=0;mutation=0;resourceTokens={};stateIDs={};registry=None;currentFunction=0
GLOBAL_TOKENS=(0x537210,0x5430c4,0x541334,0x532c0c,0x532c10,0x534eac)
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def pointer(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(pointer(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(pointer(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def number(t,v,native=True):
 b=struct.pack('<d',v)
 if native:C.memmove(pointer(t,2),b,8)
 else:m.u.mem_write(t,b)
def text(t,native=True):return C.string_at(pointer(t&~3)+(t&3))if native else bytes(m.u.mem_read(t,256)).split(b'\0')[0]
def flush():
 for t,v in zip(GLOBAL_TOKENS,struct.unpack('<6I',bytes(g)[:24])):put(t,[v])
 C.memmove(pointer(0x5262b4),bytes(g)[24:],4)
def raw(native):
 if native:flush();return bytes(heap)+C.string_at(pointer(GS),GN)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(GS,GN))
@Lookup
def lookup(_,t,n):
 p=pointer(t,n)
 if not p:errors.append(('lookup',hex(t),n))
 return p
@Invoke
def sceneInvoke(_,e):
 q=Call();q.function=e.function;q.receiver=e.receiver;q.count=e.count;q.arguments[:e.count]=e.arguments[:e.count];return dependency(C.byref(c),C.byref(q),None)&0xffffffff
@Free
def free(_,t):
 q=Call();q.function=0x4f6428;q.count=1;q.arguments[0]=t;dependency(C.byref(c),C.byref(q),None)
c.scene=Host(None,lookup,Alloc(),free,sceneInvoke,Clock())
FAKE=0x4493c0
COUNTS={0x4f63ec:1,0x4f6428:1,0x4f6286:2,0x4c7970:1,0x4c7fa0:1,0x4c8060:1,0x4cbb60:4,0x4cd800:2,0x4cda10:4,0x4207f0:2,0x4a3050:0,0x4c8220:1,0x4c82a0:1,0x4dba00:1,0x4c8da0:6,0x4b45f0:4,0x4dc560:2,0x4a49b0:3,0x4dbd20:1,0x4db6e0:2,0x4db5f0:0,0x4db4d0:3,0x4a36f0:1,0x48cf50:1,FAKE:1,0x420370:1,0x4208e0:4,0x420a10:2,0x461a00:6}
CDECL={0x4f63ec,0x4f6428,0x4a3050,0x4a49b0,0x4db5f0,0x4a36f0,0x48cf50,0x420370,0x461a00,FAKE}
NAMED={0x4f6286,0x4c7970,0x4c7fa0,0x4c8060,0x4dba00}
def effect(f,t,a,name,native):
 global randomIndex
 if f==0x4f63ec:return created
 if f in(0x420370,0x4208e0,0x420a10,0x461a00,0x4f6428,0x4dc560,0x4a49b0,0x4dbd20,0x4db4d0,0x4a36f0,0x48cf50,0x4b45f0,0x43f120):return 0
 if f==0x4f6286:
  key=name or text(a[0],native);return resourceTokens.get(key,SOUND if t==SC+0x310 else SEQ)if found else 0
 if f in(0x4c7fa0,0x4c8060):return 0
 if f==0x4c7970:put(t+0x170,[IMAGE if found else 0],native);put(t+0x174,[LEAF if found else 0],native);return 1
 if f==0x4cbb60:put(a[0]+76,a[1:3],native);return 0
 if f==0x4cd800:return 0
 if f in(0x4cda10,0x4207f0):return 0
 if f==0x4a3050:v=randomValues[randomIndex%len(randomValues)];randomIndex+=1;return v
 if f==0x4c8220:put(t+8,[a[0]],native);return 0
 if f==0x4c82a0:
  if mutation:put(t+28,[0],native);put(t+36,[1],native)
  return 0
 if f==0x4dba00:return stateIDs[(name or text(a[0],native)).decode()]
 if f==0x4c8da0:
  if not createdChild:return 0
  put(CHILD+76,a[1:3],native);put(CHILD+100,[a[3]],native);put(CHILD+108,[CL],native);return CHILD
 if f==FAKE:
  put(CL+24,[CP],native);put(CP+12,[CHILD],native);put(CP+16,[CL],native);put(CP+44,[CHILD],native);put(CP+76,[resourceTokens.get(b'LEVEL_CANNON_FIRING',SEQ),0],native);put(CHILD+0x188,[0x513870,CHILD,0,0,0,0,1,0,0,0,0x3f800000],native);return 1
 
 if f==0x4db6e0:return 0
 if f==0x4db5f0:return 123
 raise AssertionError(('unexpected service',hex(f),hex(t),a,name))
@Dep
def dependency(_,ev,u):
 try:
  q=ev.contents;a=tuple(q.arguments[:q.count]);name=q.name or (text(a[0])if q.function in NAMED and a else None);normalized=()if q.function in NAMED else a;nativeEvents.append((q.function,q.receiver,normalized,name,raw(True)));return effect(q.function,q.receiver,a,name,True)
 except Exception as exc:errors.append(exc);return 0
def hook(uc,f,size,user):
 if f in(0x10fa000,0x10fa010,0x10fa020,0x10fa030):
  sp=uc.reg_read(UC_X86_REG_ESP);n={0x10fa000:1,0x10fa010:5,0x10fa020:3,0x10fa030:2}[f];a=m.read_words(sp+4,n);v=1
  if f==0x10fa000:m.write_words(a[0],[0]*4)
  elif f==0x10fa010:m.write_words(a[0],a[1:])
  elif f==0x10fa030:m.write_words(a[0],m.read_words(a[1],4))
  else:
   left,top,right,bottom=map(lambda x:C.c_int32(x).value,m.read_words(a[0],4));x,y=map(lambda x:C.c_int32(x).value,a[1:]);v=int(left<=x<right and top<=y<bottom)
  uc.reg_write(UC_X86_REG_EAX,v);uc.reg_write(UC_X86_REG_ESP,sp+4+n*4);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);return
 if f==0x4dc560 and currentFunction in(0x4743f0,0x474330):return
 if f not in COUNTS:return
 if realTileWorld is not None and f in(0x4207f0,0x4cda10,0x4cd800,0x4cbb60):
  sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,COUNTS[f]));parent=m.read_words(sp,1)[0]
  if f!=0x4207f0 or not(0x4cbb60<=parent<0x4cdd00):originalEvents.append((f,uc.reg_read(UC_X86_REG_ECX),a,None,raw(False)))
  return
 if c.composeAnimation and f in(0x4c8220,0x4c82a0,0x420a10):return
 if c.composeImages and f==0x4c7970:return
 n=COUNTS[f];sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,n));t=0 if f in CDECL else uc.reg_read(UC_X86_REG_ECX);name=text(a[0],False)if f in NAMED and a else None
 if f==0x4c8da0:name=text(a[4],False)
 originalEvents.append((f,t,()if f in NAMED else a,name,raw(False)));v=effect(f,t,a,name,False)
 if f==0x4f6286:m.write_words(a[1],[v]);v=bool(v)
 pop=0 if f in CDECL else n*4;uc.reg_write(UC_X86_REG_EAX,int(v)&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
class RegTable(C.Structure):_fields_=[('token',U),('kind',U),('words',U*12)]
class RegLiteral(C.Structure):_fields_=[('state',C.c_int32),('literalToken',U)]
class Reg(C.Structure):_fields_=[('nextId',U),('count',U),('tables',RegTable*96),('literalCount',U),('literals',RegLiteral*256),('errorGlobals',U*15)]
class RegContext(C.Structure):_fields_=[('heap',C.POINTER(C.c_uint8))]+[(n,U)for n in('heapBase','heapCapacity','heapUsed','emptyStringToken','metadataReceiverToken','metadataFunctionToken','errorLocation','fault')]
lib.claw_logic_state_context_defaults.argtypes=[C.POINTER(Reg),C.POINTER(RegContext)]
for n in('initialize','bootstrap'):getattr(lib,'claw_logic_state_'+n).argtypes=[C.POINTER(Reg),C.POINTER(RegContext),C.c_void_p,C.c_void_p]
registry=None;realStates=None;stateIDs={};nameTokens={}
registryBytes=0;stateViews=None

def states():
 global registry,registryBytes,stateViews
 rb=BASE+0x80000
 if registry is None:
  r=Reg();rc=RegContext(C.cast(pointer(rb),C.POINTER(C.c_uint8)),rb,0x80000,0,0,0,0,0,0);lib.claw_logic_state_context_defaults(C.byref(r),C.byref(rc));assert lib.claw_logic_state_initialize(C.byref(r),C.byref(rc),None,None)and not rc.fault;assert lib.claw_logic_state_bootstrap(C.byref(r),C.byref(rc),None,None)and not rc.fault;registryBytes=rc.heapUsed;registry=(C.string_at(pointer(rb),rc.heapUsed),[(t.token,list(t.words))for t in r.tables[:r.count]],list(r.errorGlobals))
 arena,tables,diagnostics=registry;C.memmove(pointer(rb),arena,len(arena))
 for t,words in tables:put(t,words)
 put(0x544b14,diagnostics);names=get(0x537698,9);common=get(0x537638,9);entries=[]
 for state in range(names[2],names[3]+1):
  token=get(names[4]+(state-names[2])*4)[0];label=text(token).decode();stateIDs[label]=state;fn=get(common[4]+(state-common[2])*common[6])[0]if common[2]<=state<=common[3]else 0;entries.append(State(state,fn,token,label.encode()))
 stateViews=(State*len(entries))(*entries);generic.states=stateViews;generic.stateCount=len(entries)
def fresh():
 global found,created,createdChild,randomValues,randomIndex,mutation,resourceTokens,realTileWorld
 realTileWorld=None;resourceTokens={};C.memmove(C.addressof(image),imageSeed,len(imageSeed));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);lib.claw_generic_enemy_context_defaults(C.byref(generic));generic.emptyStringToken=0x52e1c4;generic.playerToken=PLAYER;generic.playerActor[:]=[0]*128;generic.forcedRandom=0;C.memset(C.addressof(sharedStates),0,C.sizeof(sharedStates));g.tick=1000;g.animationDelta=17;g.randomDisabled=0;g.audioEnabled=0;g.masterVolume=83;g.powerup=0;g.healthScale=1;c.fault=0;c.composeImages=c.composeAnimation=0;found=True;created=E;createdChild=CHILD;randomValues=[123];randomIndex=0;mutation=0
 put(A,[0]*128);put(A,[0x5137f0]);put(A+8,[0x40000,SC]);put(A+76,[300,400]);put(A+100,[4000,0,L,SECONDARY]);put(A+120,[CONTACT]);put(A+0xdc,[10,10]);put(A+0x170,[IMAGE,LEAF]);put(A+0x188,[0x513870,A,SEQ,0,0,0,1,0,0,0,0x3f800000]);put(L,[0]*93);put(L+12,[SC,0x474330]);put(L+24,[E,2001]);put(SECONDARY,[0]*93);put(CONTACT,[0]*93);put(PLAYER,[0]*128);put(PLAYER+0x10c,[100]);put(0x537e88,[PLAYER]);put(E+8,[A,A,L,0,0,1001,2]);put(E,[0x50eee4]);put(E+0x2fc,[32,0x202]);put(E+0x1a4,[0x52e1c4,0x52e1c4]);put(E+0x128,[A,A,L]);put(E+0x184,[6]);put(E+0x404,[SOUND,CHILD,0xabcdef01]);put(SOUND+16,[POOL]);put(CHILD,[0]*128);put(CHILD+12,[SC]);put(CHILD+108,[CL]);put(CL,[0]*93);put(CL+16,[FAKE,0,CP,stateIDs.get('LS_HOME',2000)]);put(CP,[0]*31);put(CP+12,[CHILD,CL]);put(CP+44,[CHILD]);put(CP+76,[SEQ,SEQ]);put(CP+112,[0]);put(SC+8,[BASE+0x17000]);put(SC+16,[SC+0x100]);put(SC+36,[WORLD]);put(SC+40,[SC+0x300]);put(SC+44,[SC+0x200]);put(IMAGE+20,[TABLE]);put(IMAGE+100,[1,3]);put(TABLE,[0,LEAF,LEAF,LEAF]);put(LEAF+16,[12,8,6,4,0,0]);put(BASE+0x17000+20,[0]);put(0x532ba8,[0]);put(0x534938,[0]);put(0x533470,[32]);put(0x537204,[BASE+0x18000]);put(BASE+0x18000,[0]*4)
 for off in range(0x28,0x100,8):number(E+off,0)
 number(E+0x28,1);number(E+0x68,300);number(E+0x70,400);number(E+0x50,60)
 for off in(0x80,0x88,0x90):number(E+off,-1e9)
 for off in(0x98,0xa0,0xa8):number(E+off,1e9)
 for off in(0xe8,0xf0,0xf8):number(E+off,24)
 put(E+0x308,[1,SEQ,SEQ]);put(E+0x134,[SEQ]);put(E+0x350,[SEQ,SEQ]);put(E+0x344,[SEQ]);put(E+0x400,[SEQ]);put(E+0x118,[300,400]);states();put(0x546cdc,[0x10fa000]);put(0x546d5c,[0x10fa010]);put(0x546cd4,[0x10fa020]);put(0x546d58,[0x10fa030]);flush()
voids={0x4747e0,0x474710,0x474bc0,0x414a60,0x4c9e30,0x4063b0,0x43dfa0,0x404fc0,0x43fcb0,0x43fd60,0x43e9b0}
def compare(f,t=E,args=(),label=None,record=False):
 global calls,eventsCount,randomIndex,currentFunction,captureReplay
 captureReplay=record;caseTape.clear();currentFunction=f;c.fault=0;flush();before=bytes(heap);beforeImage=bytes(image);bg=bytes(g);nativeEvents.clear();originalEvents.clear();errors.clear();randomIndex=0;out=U();av=(U*len(args))(*args);assert lib.claw_punk_rat_entry(f,t,av,len(args),C.byref(c),dependency,None,C.byref(out))and not c.fault and not errors,(label,'native',c.fault,errors);expected=raw(True);ev=list(nativeEvents);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),beforeImage,len(image));C.memmove(C.addressof(g),bg,28);m.u.mem_write(BASE,before);m.u.mem_write(imageStart,beforeImage);randomIndex=0
 try:ret=m.call(f,t,pack(*args))
 except Exception as ex:print(label,'originalfault',hex(m.u.reg_read(UC_X86_REG_EIP)),[(hex(e[0]),e[1:4])for e in originalEvents[-5:]]);raise
 actual=raw(False)
 if actual!=expected:raise AssertionError((label,'fullbuffers',[(hex(BASE+i)if i<SIZE else hex(GS+i-SIZE),a,b)for i,(a,b)in enumerate(zip(actual,expected))if a!=b][:20]))
 if ev!=originalEvents:
  for i,(a,b)in enumerate(zip(ev,originalEvents)):
   if a!=b:print(label,'event',i,a[:4],b[:4],[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),x,y)for j,(x,y)in enumerate(zip(a[4],b[4]))if x!=y][:15]);break
  raise AssertionError((label,'events',len(ev),len(originalEvents)))
 if f not in voids:assert ret==out.value,(label,'EAX',ret,out.value)
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(pointer(GS),expected[SIZE:],GN);calls+=1;eventsCount+=len(ev)
 if record:writeReplay(f,t,args,out.value,before+beforeImage[GS-imageStart:GS+GN-imageStart],bg,expected)
 return ret

assetProfile=[]
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
class AniRecord(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
def realResources(level):
 import re
 resourceTokens.clear();leaves=BASE+0x20000;root=IMAGE;table=TABLE;rows=[]
 for path in sorted((ROOT/f'work/original-disc-assets/LEVEL{level}/IMAGES/PUNKRAT').glob('*.PID')):
  b=path.read_bytes();ident=int(re.search(r'[0-9]+',path.stem)[0]);_,_,w,ht,x,y=struct.unpack_from('<6I',b);geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),w,ht,x,y);put(leaves+16,list(struct.unpack('<10I',bytes(geometry)))[:6]);rows.append((ident,leaves));assetProfile.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'id':ident,'width':w,'height':ht,'offsetX':x,'offsetY':y});leaves+=64
 assert len(rows)==16;minimum=min(i for i,_ in rows);maximum=max(i for i,_ in rows);put(root+20,[table]);put(root+100,[minimum,maximum]);put(table,[0]*(maximum+1))
 for ident,leaf in rows:put(table+ident*4,[leaf])
 resourceTokens[b'LEVEL_PUNKRAT']=root;group=BASE+0x24000;recordAt=BASE+0x28000
 paths=sorted((ROOT/f'work/original-disc-assets/LEVEL{level}/ANIS/PUNKRAT').glob('*.ANI'))+sorted((ROOT/f'work/original-disc-assets/LEVEL{level}/ANIS/CANNON').glob('*.ANI'))+[ROOT/'work/original-disc-assets/GAME/ANIS/NULL.ANI']
 for path in paths:
  b=path.read_bytes();sig,_,flags,count,pl=struct.unpack_from('<5I',b);assert sig==32;at=32+pl;seq=group;group+=0x200;pointers=[];eventNames=[];name=b'GAME_NULL'if path.name=='NULL.ANI'else('LEVEL_'+path.parent.name+'_'+path.stem).encode()
  for _ in range(count):
   tail=b[at:];buffer=(C.c_uint8*len(tail)).from_buffer_copy(tail);record=AniRecord();length=U();used=lib.claw_animation_decode_record(buffer,len(tail),SOUND,C.byref(record),C.byref(length));assert used;v=list(struct.unpack('<10I',bytes(record)));put(recordAt,[0x513af0,v[0],*v[1:9],0,v[9]]);pointers.append(recordAt);recordAt+=48
   if length.value:eventNames.append(tail[20:20+length.value].decode())
   at+=used
  assert at==len(b)and len(pointers)*4<=0x1c0;put(seq+12,[seq+0x40,count]);put(seq+0x40,pointers);resourceTokens[name]=seq;assetProfile.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'name':name.decode(),'records':count,'events':eventNames})
 assert recordAt<BASE+0x80000
 c.composeAnimation=c.composeImages=1;return assetProfile
_baseEffect=effect
def effect(f,t,a,name,native):
 if f==0x4f6286 and resourceTokens:
  key=name if name is not None else text(a[0],native);return resourceTokens.get(key,SOUND if t==SC+0x310 else 0) if found else 0
 if f==0x4c88e0:return 0
 return _baseEffect(f,t,a,name,native)
COUNTS[0x4c88e0]=4;COUNTS[0x4208e0]=4
class WorldState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class WorldContext(C.Structure):_fields_=[(n,U)for n in('scene','actor','logic','defaultType','width','height','registry')]+[('layers',U*3)]+[(n,U)for n in('entry','callback','flags')]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('text',C.c_char_p)]
WorldDep=C.CFUNCTYPE(U,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDep,C.c_void_p,C.POINTER(U)]
@WorldDep
def worldDep(s,c,e,user):
 if e.contents.function==0x4f6286:return BASE+0x1e000
 if e.contents.function in(0x4c7970,0x4c7900):s.contents.actor[0x170//4]=resourceTokens[b'LEVEL_PUNKRAT'];return 1
 if e.contents.function==0x4f4630:return 1
 raise AssertionError(('worldprofile',hex(e.contents.function)))
def retailRecord(row):
 w=row['words'];b=pack(*w)+b''.join(v.encode().ljust(n,b'\0')for v,n in zip(row['strings'],w[1:5]));assert len(b)==284+sum(w[1:5]);buffer=(C.c_uint8*len(b)).from_buffer_copy(b);s=WorldState();s.actor[:]=get(A,128);s.logic[:]=get(L,93);c=WorldContext(SC,A,L,2,row['worldWidth'],row['worldHeight'],SC+0x120,(U*3)(SC+0x500,SC+0x600,SC+0x700),0,0x474330,0);out=(U*2)();assert lib.claw_world_object_load(buffer,len(b),C.byref(s),C.byref(c),worldDep,None,out)==len(b)and out[1]==1;put(A,s.actor);put(L,s.logic);put(A+112,[SECONDARY]);put(A+120,[CONTACT]);put(PP,[0]*78);return row

class Description(C.Structure):_fields_=[(n,U)for n in('type','width','height','inside','outside')]+[(n,C.c_int32)for n in('left','top','right','bottom')]
class CollisionActor(C.Structure):_fields_=[(n,U)for n in('flags','x','y','mode','type','stepX','stepY','support','token','deltaX','deltaY','ml','mt','mr','mb','hl','ht','hr','hb')]
class CollisionWorld(C.Structure):_fields_=[('cells',C.POINTER(U)),('rows',C.POINTER(U)),('width',C.c_int32),('height',C.c_int32),('sx',U),('sy',U),('descriptions',C.POINTER(Description)),('count',U),('actors',C.POINTER(CollisionActor)),('actorCount',U),('maximumStepX',U),('maximumStepY',U)]
lib.claw_world_point_attribute.argtypes=[C.POINTER(U),C.POINTER(U),C.c_int32,C.c_int32,U,U,C.POINTER(Description),U,U,U,U,U]
lib.claw_collision_horizontal_clear.argtypes=[C.POINTER(CollisionWorld),U,U,U,U,C.POINTER(U)]
lib.claw_collision_move.argtypes=[C.POINTER(CollisionWorld),C.POINTER(CollisionActor),U,U,U]
lib.claw_collision_place_on_ground.argtypes=[C.POINTER(CollisionWorld),C.POINTER(CollisionActor)]
realTileWorld=None

def retailWorld(level):
 import zlib
 global realTileWorld
 path=ROOT/f'work/original-disc-assets/LEVEL{level}/WORLDS/WORLD.WWD';raw=path.read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
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
 plane,cellMemory,rowMemory,descPointers,descMemory,actorList=BASE+0x19000,BASE+0x100000,BASE+0x1b0000,BASE+0x1b2000,BASE+0x1c0000,BASE+0x1b000
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
 nativeEvents.append((0x4f6428,0,(t,),None,raw(True)))
 if captureReplay:
  state=raw(True);caseTape.append((0x4f6428,0,(t,),0,state,[],bytes(g)))
c.scene.free=free
def patches(rows):
 replay.write(pack(len(rows)))
 for i,v in rows:replay.write(pack(i,v))
def writeReplay(fn,t,args,out,before,globalsBefore,after):
 global replayCases
 replay.write(pack(fn,t,out,c.composeAnimation,c.composeImages,len(caseTape),len(args),*args));replay.write(globalsBefore);replay.write(before);shadow=before
 for f,receiver,a,value,pre,post,gbytes in caseTape:
  # Native packets to leaf resource transports retain their literal arguments;
  # the normal differential separately checks names and source packet order.
  replay.write(pack(f,receiver,len(a),value,*a));patches(deltas(shadow,pre));patches(post);replay.write(gbytes);shadow=bytearray(pre)
  for i,v in post:struct.pack_into('<I',shadow,i*4,v)
  shadow=bytes(shadow)
 patches(deltas(shadow,after));replayCases+=1
def writeCorpus():
 path=WORK/'replay.bin';path.write_bytes(pack(0x50554e4b,replayCases,BASE,SIZE,0x520000,0x30000,imageStart,len(imageSeed))+imageSeed+replay.getvalue());return path


def nullPageOff():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 saved=m.u.context_save();teb,gdt=0x10ed000,0x10ee000
 def desc(base,access):return struct.pack('<I',0xffff|(base&0xffff)<<16)+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 m.u.mem_write(gdt+8,desc(0,0x9b));m.u.mem_write(gdt+16,desc(0,0x93));m.u.mem_write(gdt+24,desc(teb,0x93));m.u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for r in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(r,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.u.mem_write(teb,pack(0));m.u.mem_unmap(0,4096);return saved
prefixes=0
def failure(f,t=0,args=None,expectedFault=2):
 global prefixes,eventsCount,currentFunction,captureReplay
 currentFunction=f;captureReplay=False;c.fault=0;flush();before=bytes(heap);bi=bytes(image);bg=bytes(g);m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);nativeEvents.clear();originalEvents.clear();errors.clear();args=[A]if args is None else args;av=(U*len(args))(*args);out=U();assert not lib.claw_punk_rat_entry(f,t,av,len(args),C.byref(c),dependency,None,C.byref(out))and c.fault==expectedFault,(f,c.fault,errors);wanted=raw(True);events=list(nativeEvents);C.memmove(C.addressof(g),bg,28);saved=nullPageOff()
 try:
  failed=False
  try:m.call(f,t,pack(*args))
  except UcError:failed=True
  assert failed and raw(False)==wanted and originalEvents==events,('unsafe-prefix',hex(f));prefixes+=1;eventsCount+=len(events)
 finally:m.u.mem_map(0,4096);m.u.context_restore(saved)
