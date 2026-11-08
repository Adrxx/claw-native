"""Whole pinned player ranged entries; complete borrowed heap/global oracle."""
import ctypes as C,struct,random,json,subprocess,hashlib,io
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/player-ranged-helpers-agent';U=C.c_uint32
SOURCES=['PlayerRangedHelpersRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming','PickupPointsRuntime','ActorDestruction','ActorAnimationRuntime','ActorResourceBindings','SpriteGeometry','AnimationEngine','AnimationOperations','PlayerPhysics','PlayerLocomotion','PlayerAirStates','PlayerEngine','PlayerInitialization','PlayerDamage','TileCollision','CollisionResponse','PIDRaster','PIDSurfaceRaster','PIDBlitter','PlayerProjectileRuntime','BulletLogic','GenericEnemy','GenericEnemyStates','RawTileDescriptionRuntime','WorldPlaneRuntime','WorldFileRuntime','CArrayRuntime','SpatialGridRuntime','SceneCameraRuntime','PlayerPoseStates','PlayerAttackInput']
LIB=WORK/'libPlayerRangedHelpers.dylib'
if not LIB.exists()or any((ROOT/'Sources'/f'{s}.cpp').stat().st_mtime>LIB.stat().st_mtime for s in SOURCES)or (WORK/'caller_bridge.cpp').stat().st_mtime>LIB.stat().st_mtime:subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib','-I',str(ROOT/'Sources'),*[str(ROOT/'Sources'/f'{s}.cpp')for s in SOURCES],str(WORK/'caller_bridge.cpp'),'-o',str(LIB)],check=True)
lib=C.CDLL(str(LIB))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('powerup',U),('masterVolume',U)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals))]+[(n,U)for n in('composeCreation','composeImages','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.ranged_test_caller.argtypes=[U,C.POINTER(U),C.POINTER(Context),Dep,C.c_void_p]
lib.ranged_test_animation.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),C.POINTER(U)]
lib.claw_player_ranged_helpers_entry.argtypes=[U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE,GS,GN=0x3000000,0x40000,0x520000,0x30000
A,L,P,SC,CONTAINER,SHOT,SL,SP,SOUND,POOL,IMAGE,TABLE,LEAF,METADATA,SEQ,ANI_TABLE,ANI_RECORDS=[BASE+0x1000+i*0x1000 for i in range(17)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g)
rng=random.Random(0x41cc60);nativeEvents=[];originalEvents=[];errors=[];calls=eventsCount=0;found=True;created=SHOT;mutation=0;allocateResult=SHOT;capture=False;tape=[];replay=io.BytesIO();replayCases=0;cancelFunction=0
composeAnimation=False
COUNTS={0x4cbb60:4,0x4c82a0:1,0x4c8220:1,0x420970:1,0x420a10:2,0x4c88e0:4,0x4f6428:1,0x4c8da0:6,0x4c7970:1,0x4f6286:2,0x4208e0:4,0x4c8be0:6,0x4f63ec:1,0x4d5240:2,0x4c8ba0:1,0x4c8b50:1,0x4c8ad0:3,0x4c8b10:2,0x4c8ae0:3}
CDECL={0x4f63ec,0x4f6428}
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def text(t,native=True):return C.string_at(ptr(t&~3)+(t&3))if native else bytes(m.u.mem_read(t,128)).split(b'\0')[0]
def flush():put(0x534eac,[g.powerup]);put(0x532c10,[g.masterVolume])
def raw(native):
 if native:flush();return bytes(heap)+C.string_at(ptr(GS),GN)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(GS,GN))
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('span',hex(t),n))
 return p
@Invoke
def sceneCall(_,q):
 e=Call();e.function=q.function;e.receiver=q.receiver;e.count=q.count;e.arguments[:q.count]=q.arguments[:q.count];return dependency(C.byref(ctx),C.pointer(e),None)&0xffffffff
host=Host(None,lookup,Allocate(),Free(),sceneCall,Clock());ctx.scene=host

def effect(f,t,a,name,native):
 if f==0x4c88e0:return 0
 if f==0x4cbb60:put(a[0]+76,a[1:3],native);put(a[0]+0xcc,[1],native);return 0
 if f==0x4f63ec:return {0x1b4:SHOT,0x174:SL,124:BASE+0x19000}[a[0]]
 if f==0x4f6428:return 0
 if f==0x4c8da0:
  if mutation&1:put(P,[0 if get(P,native=native)[0]else 1],native);put(P+0xe8,[get(P+0xe8,native=native)[0]+1],native);put(P+112,[get(P+112,native=native)[0]+1],native)
  return created
 if f==0x4c7970:
  put(t+0x170,[IMAGE if found else 0],native)
  if mutation&2:put(P+116,[get(P+116,native=native)[0]+1],native)
  return int(found)
 if f==0x4f6286:
  callbacks={b'PistolBullet':0x40ff80,b'MagicBullet':0x410040,b'Dynamite':0x43a850,b'FireBullet':0x410100,b'LightningBullet':0x4101c0,b'IceBullet':0x410280}
  if name in callbacks:put(METADATA+16,[callbacks[name]],native)
  if mutation&4:
   if native:g.masterVolume^=7
   else:put(0x532c10,[get(0x532c10,native=native)[0]^7],native)
  return (IMAGE if name==b'GAME_BULLETS'else METADATA if name in(b'PistolBullet',b'MagicBullet',b'Dynamite',b'FireBullet',b'LightningBullet',b'IceBullet')else SOUND)if found else 0
 if f==0x4208e0:return 0
 raise AssertionError(('unadapted',hex(f),hex(t),a,name))
@Dep
def dependency(_,ev,user):
 q=ev.contents;a=list(q.arguments[:q.count]);name=q.name
 if composeAnimation and q.function in(0x4c8220,0x4c82a0,0x420970,0x420a10):
  out=U();args=(U*len(a))(*a);assert lib.ranged_test_animation(q.function,q.receiver,args,len(a),C.byref(ctx),C.byref(out));return out.value
 if name is None and q.function in(0x4f6286,0x4c7970):name=text(a[0])
 nativeEvents.append((q.function,q.receiver,tuple(a),name,raw(True)));before=raw(True)if capture else None
 if cancelFunction==q.function:ctx.fault=77;return 0
 try:
  value=effect(q.function,q.receiver,a,name,True)
  if capture:tape.append((q.function,q.receiver,a,value,deltas(before,raw(True)),bytes(g),before))
  return value
 except BaseException as e:errors.append(e);ctx.fault=99;return 0
def returned(pop,value=0):
 sp=m.u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop);m.u.reg_write(UC_X86_REG_EIP,ret)
def hook(u,fn,size,user):
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX)
 if composeAnimation and fn in(0x4c8220,0x4c82a0,0x420970,0x420a10):return
 if fn not in COUNTS:return
 if ctx.composeCreation and fn in(0x4c8da0,0x4c8be0):return
 if ctx.composeImages and fn==0x4c7970:return
 a=m.read_words(sp+4,COUNTS[fn]);t=0 if fn in CDECL else t;name=text(a[4],False)if fn==0x4c8da0 else text(a[0],False)if fn in(0x4f6286,0x4c7970)else None;out=a[1]if fn==0x4f6286 else 0;normalized=a[:1]if fn==0x4f6286 else a
 originalEvents.append((fn,t,tuple(normalized),name,raw(False)))
 if cancelFunction==fn:u.emu_stop();return
 v=effect(fn,t,normalized,name,False)
 if fn==0x4f6286:m.write_words(out,[v]);returned(8,int(bool(v)))
 else:returned(0 if fn in CDECL else len(a)*4,v)
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(seed=0):
 global found,created,mutation,allocateResult,cancelFunction
 heap[:]=rng.randbytes(SIZE);C.memmove(C.addressof(image),imageSeed,len(imageSeed));g.powerup=[0,0x26b8,0x26b9,0x26ba,0x26bb][seed%5];g.masterVolume=100;ctx.scene=host;ctx.composeCreation=ctx.composeImages=ctx.fault=0;found=True;created=allocateResult=SHOT;mutation=cancelFunction=0
 put(A,[0x5137f0]);put(A+12,[SC]);put(A+76,[1000,2000]);put(A+100,[4000]);put(A+108,[L]);put(L+20,[P]);put(P,[0]*78);put(P,[seed%2]);put(P+0x54,[71,23]);put(P+112,[10,20,30]);put(P+0xe8,[42]);put(P+0x100,[500,50,2000]);put(CONTAINER,[0x513c20,0,0,SC,0x5107bc,0,0,0,0,0,10]);put(METADATA,[0,0,0,0,0x40ff80]);put(SC+20,[SC+0x800]);put(SC+36,[2]);put(SC+8,[CONTAINER]);put(SC+16,[SC+0x800]);put(SC+40,[SC+0x900]);put(SC+0x930,[0]);put(SHOT,[0x5137f0]);put(SHOT+12,[SC]);put(SHOT+108,[SL]);put(SL+24,[SP]);put(SOUND+16,[POOL]);put(IMAGE+20,[TABLE]);put(IMAGE+100,[1,5]);put(TABLE,[0,LEAF,0,LEAF,0,LEAF]);put(LEAF+16,[12,8,6,4,0,0]);flush()
def compare(fn,label='case',args=None,record=False):
 global calls,eventsCount,capture
 if args is None:args=[A,L,P]
 capture=record;ctx.fault=0;flush();m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GS,C.string_at(ptr(GS),GN));m.write_words(0,[0x12345678]);nativeEvents.clear();originalEvents.clear();errors.clear();tape.clear();before=raw(True);bg=bytes(g);v=(U*len(args))(*args);out=U();ok=lib.claw_player_ranged_helpers_entry(fn,v,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ok,ctx.fault,errors);ng=bytes(g);ct=list(tape);C.memmove(C.addressof(g),bg,8);ret=m.call(fn,0,pack(*args));C.memmove(C.addressof(g),ng,8)
 assert ret==out.value,(label,'EAX',ret,out.value)
 if nativeEvents!=originalEvents:
  for i,(x,y)in enumerate(zip(nativeEvents,originalEvents)):
   if x!=y:print(label,'event',i,x[:4],y[:4]);print('diff',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(x[4],y[4]))if a!=b][:14]);break
  raise AssertionError((label,'events',len(nativeEvents),len(originalEvents)))
 assert raw(True)==raw(False),(label,'completebuffers',[(hex(BASE+j)if j<SIZE else hex(GS+j-SIZE),a,b)for j,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:14]);calls+=1;eventsCount+=len(nativeEvents)
 if record:writeReplay(fn,args,out.value,before,bg,raw(True),ct)
 return out.value

def deltas(before,after):
 old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);return [(i,v)for i,(u,v)in enumerate(zip(old,new))if u!=v]
def emitPatches(patches):
 replay.write(pack(len(patches)))
 for i,v in patches:replay.write(pack(i,v))
def writeReplay(fn,args,out,before,bg,after,caseTape):
 global replayCases
 replay.write(pack(fn,out,ctx.composeCreation,ctx.composeImages,len(caseTape),*args));replay.write(bg);replay.write(before);shadow=before
 for f,t,a,v,post,gbytes,pre in caseTape:
  replay.write(pack(f,t,len(a),v&0xffffffff,*a));emitPatches(deltas(shadow,pre));emitPatches(post);replay.write(gbytes);shadow=bytearray(pre)
  for i,value in post:struct.pack_into('<I',shadow,i*4,value)
  shadow=bytes(shadow)
 emitPatches(deltas(shadow,after));replayCases+=1
def writeCorpus():
 out=WORK/'replay.bin';out.write_bytes(pack(0x524e4745,replayCases,BASE,SIZE,GS,GN,imageStart,len(imageSeed))+imageSeed+replay.getvalue());return out
class AniRecord(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
assetProfile=[]
def playerANI(file):
 global composeAnimation
 path=ROOT/'work/original-disc-assets/CLAW/ANIS'/file;b=path.read_bytes();sig,_,flags,count,pl=struct.unpack_from('<5I',b);assert sig==32;at=32+pl;records=[];tokens=[]
 for i in range(count):
  buf=(C.c_uint8*(len(b)-at)).from_buffer_copy(b[at:]);rec=AniRecord();length=U();used=lib.claw_animation_decode_record(buf,len(buf),SOUND,C.byref(rec),C.byref(length));assert used;v=list(struct.unpack('<10I',bytes(rec)));token=ANI_RECORDS+i*48;put(token,[0x513af0,v[0],*v[1:9],0,v[9]]);tokens.append(token);records.append(v);at+=used
 assert at==len(b);put(SEQ+12,[ANI_TABLE,count]);put(ANI_TABLE,tokens);put(A+0x170,[BASE+0x1a000]);put(BASE+0x1a000+20,[BASE+0x1b000]);put(BASE+0x1a000+100,[0,950]);put(BASE+0x1b000,[LEAF]*951);put(A+0x188,[0x513870,A,SEQ,tokens[0],0,0,1,0,records[0][6],records[0][6],0x3f800000]);put(0x5430c4,[17]);put(0x53720c,[17]);put(BASE+0x1e000,[0]*4);put(0x537204,[BASE+0x1e000]);put(L+28,[26]);put(P+4,[1]);put(A+0x1a4,[0]);put(A+0xcc,[1]);put(A+8,[0]);put(A+0x148,[0,0]);composeAnimation=True
 profile={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'records':count,'markers':sorted(set(x[6]for x in records))};assetProfile.append(profile);return profile

def compareCaller(fn,label):
 global calls,eventsCount
 ctx.fault=0;flush();m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GS,C.string_at(ptr(GS),GN));m.write_words(0,[0x12345678]);nativeEvents.clear();originalEvents.clear();errors.clear();args=(U*3)(A,L,P);assert lib.ranged_test_caller(fn,args,C.byref(ctx),dependency,None)and not ctx.fault and not errors,(label,ctx.fault,errors);ng=bytes(g);m.call(fn,0,pack(A,L,P));C.memmove(C.addressof(g),ng,8)
 assert raw(True)==raw(False),(label,'completebuffers',[(hex(BASE+i)if i<SIZE else hex(GS+i-SIZE),x,y)for i,(x,y)in enumerate(zip(raw(True),raw(False)))if x!=y][:18]);assert nativeEvents==originalEvents,(label,'events',[(hex(e[0]),e[1:4])for e in nativeEvents],[(hex(e[0]),e[1:4])for e in originalEvents]);calls+=1;eventsCount+=len(nativeEvents)
def nullPageOff():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 saved=m.u.context_save();teb,gdt=0x10ed000,0x10ee000
 def desc(base,access):return struct.pack('<I',0xffff|(base&0xffff)<<16)+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 m.u.mem_write(gdt+8,desc(0,0x9b));m.u.mem_write(gdt+16,desc(0,0x93));m.u.mem_write(gdt+24,desc(teb,0x93));m.u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for r in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(r,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.u.mem_write(teb,pack(0));m.u.mem_unmap(0,4096);return saved

def failure(fn,label,fault):
 global eventsCount,capture
 capture=False;flush();m.u.mem_write(BASE,bytes(heap));m.u.mem_write(GS,C.string_at(ptr(GS),GN));nativeEvents.clear();originalEvents.clear();errors.clear();args=(U*3)(A,L,P);out=U();ctx.fault=0;assert not lib.claw_player_ranged_helpers_entry(fn,args,3,C.byref(ctx),dependency,None,C.byref(out))and ctx.fault==fault,(label,ctx.fault,errors);ng=bytes(g);expected=raw(True);saved=nullPageOff();failed=False
 try:
  try:m.call(fn,0,pack(A,L,P))
  except UcError:failed=True
  except AssertionError:
   assert cancelFunction;failed=True
  assert failed,(label,'original unexpectedly completed');assert expected==raw(False),(label,'unsafe prefix buffers');assert nativeEvents==originalEvents,(label,'unsafe prefix events');eventsCount+=len(nativeEvents)
 finally:m.u.mem_map(0,4096);m.u.context_restore(saved);C.memmove(C.addressof(g),ng,8)
