"""Hash-pinned full raw-heap SuperPowerup and existing pickup compositions."""
import ctypes as C,struct,subprocess,hashlib,random,json,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/super-powerup-agent';U=C.c_uint32
sources=list((ROOT/'Sources').glob('*.cpp'))
if not(WORK/'libSuperPowerup.dylib').exists()or any(p.stat().st_mtime>(WORK/'libSuperPowerup.dylib').stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(WORK/'libSuperPowerup.dylib')],check=True)
lib=C.CDLL(str(WORK/'libSuperPowerup.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Loot(C.Structure):_fields_=[('words',U*341)]+[(n,U)for n in('count','volume','highLaunch','configuration')]
class Physics(C.Structure):_fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3)for n in('acceleration','velocity','position','minimum','maximum','delta')]+[('stopped',U),('unused',U)]+[(n,C.c_double*3)for n in('remainder','maximumDelta','maximumVelocity')]
class Player(C.Structure):_fields_=[('actor',U*128),('private',U*78)]+[(n,U)for n in('logic','latched','held','stageDelta','animationDelta','powerup','scratch')]+[('physics',Physics),('weaponLogicStatus',C.c_int32)]+[(n,U)for n in('weaponLogicCallback','weaponDeleteCount','weaponDeleteFlags','highJump','scratchY','audioDisabled','volume')]
class Items(C.Structure):_fields_=[('scene',Host),('loot',C.POINTER(Loot)),('player',C.POINTER(Player))]+[(n,U)for n in('playerToken','playerPrimaryToken','playerPrivateToken','managerToken','animationDelta','stageDelta','tick','audioEnabled','masterVolume','lastSoundTick','lastSoundToken','auxiliaryManager','auxiliaryScene','composeCreation','fault')]
class Animation(C.Structure):_fields_=[('delta',U),('volume',U)]
class Context(C.Structure):_fields_=[('scene',Host),('items',C.POINTER(Items)),('animation',C.POINTER(Animation))]+[(n,U)for n in('composeAnimation','composeCreation','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000;A,L,SC,MANAGER,IMAGE,ROOTIMAGE,FRAMES,SEQ,RECORDS,GLITTER,PLAYER,PL,PP,SOUND,POOL,GLITTERL=[BASE+0x1000+i*0x1000 for i in range(16)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();loot=Loot();items=Items();animation=Animation();player=Player();ctx=Context();ctx.items=C.pointer(items);ctx.animation=C.pointer(animation);items.loot=C.pointer(loot);items.player=C.pointer(player)
lib.claw_super_powerup_entry.argtypes=[U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_super_powerup_award.argtypes=[U,C.POINTER(Context),Dep,C.c_void_p]
rng=random.Random(0x471330);nativeEvents=[];originalEvents=[];errors=[];calls=eventCount=0;found=True;created=GLITTER;mutation=0;animationResult=0;composeLoot=False

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 data=pack(*v)
 if native:C.memmove(ptr(t,len(v)),data,len(data))
 else:m.u.mem_write(t,data)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def updateGlobals():
 put(0x537ec8,list(loot.words));put(0x52a190,[loot.count]);put(0x5371fc,[items.managerToken]);put(0x537210,[items.tick]);put(0x5430c4,[animation.delta]);put(0x532c0c,[items.audioEnabled]);put(0x532c10,[items.masterVolume]);put(0x534ec0,[items.lastSoundTick,items.lastSoundToken]);put(0x537960,[BASE+0x1e000]);put(BASE+0x1e000,[loot.configuration])
def raw(native):
 if native:updateGlobals();return bytes(heap)+C.string_at(ptr(0x520000),0x30000)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)if not t%4 else 0
 if not p:errors.append(('lookup',hex(t),n))
 return p
@Invoke
def sceneCall(_,e):
 args=tuple(e.arguments[:e.count]);name=C.string_at(ptr(args[0])).split(b'\0')[0]if e.function in(0x4f6286,0x4061b0)else None
 nativeEvents.append((e.function,e.receiver,args,name,snap(True)));return effect(e.function,e.receiver,args,name,True)
ctx.scene=Host(None,lookup,Alloc(),Free(),sceneCall,Clock());items.scene=ctx.scene
@Dep
def dependency(_,e,user):
 try:
  e=e.contents;a=tuple(e.arguments[:e.count]);name=e.name
  if name is None and e.function in(0x4f6286,0x4061b0):name=C.string_at(ptr(a[0])).split(b'\0')[0]
  nativeEvents.append((e.function,e.receiver,a,name,snap(True)));return effect(e.function,e.receiver,a,name,True)or 0
 except Exception as exc:errors.append(exc);return 0
literalNames={0x52a198:b'GAME_POWERUP',0x522950:b'PowerupGlitter'}
# Every frozen loot initialization service supplies exact real resource-name
# identity. Unique deterministic resource identities are explicit transport.
resourceTokens={};resourceMetadata={}
def effect(fn,t,args,name,native):
 if fn==0x4c79e0:
  put(t+400,[SEQ if found else 0],native)
  if mutation&1:put(t+8,[get(t+8,native=native)[0]^0x400],native)
  if mutation&2:put(t+108,[L+0x400],native)
  return int(found)
 if fn==0x4c82a0:
  if mutation&1:put(A+420,[1],native);put(A+412,[0],native)
  return animationResult
 if fn==0x4c8da0:
  if created:put(created+76,args[1:3],native);put(created+100,[args[3]],native);put(created+108,[GLITTERL],native)
  if mutation&1:put(A+0xd0,[1],native)
  return created
 if fn==0x4f6286:
  if mutation&4:put(A+0xd0,[1],native)
  if name in resourceTokens:return resourceTokens[name]
  return SEQ if found else 0
 if fn==0x4061b0:
  if mutation&4:put(A+0xd0,[1],native)
  return resourceTokens.get(name,0)
 if fn==0x4b45f0:return 0
 if fn==0x4719e0:raise AssertionError('original loot initialization must execute, not be replaced')
 raise AssertionError(('unexpected',hex(fn),hex(t),args,name))
abis={0x4c79e0:(2,8),0x4c82a0:(1,4),0x4c8da0:(6,24),0x4f6286:(2,8),0x4061b0:(1,4),0x4b45f0:(4,16)}
def hook(uc,fn,size,user):
 if fn not in abis:return
 if ctx.composeAnimation and fn in(0x4c79e0,0x4c82a0):return
 n,pop=abis[fn];sp=uc.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,n));t=uc.reg_read(UC_X86_REG_ECX);name=None;norm=args
 if fn in(0x4c79e0,0x4f6286,0x4061b0):name=bytes(uc.mem_read(args[0],200)).split(b'\0')[0]
 if fn in(0x4f6286,0x4061b0):norm=(args[0],)
 if fn==0x4c8da0:name=bytes(uc.mem_read(args[4],100)).split(b'\0')[0]
 originalEvents.append((fn,t,norm,name,snap(False)));value=effect(fn,t,norm,name,False)or 0
 if fn==0x4f6286:m.write_words(args[1],[value]);value=int(bool(value))
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)

def fresh():
 global found,created,mutation,animationResult
 C.memmove(C.addressof(image),imageSeed,len(imageSeed));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);C.memset(C.addressof(loot),0,C.sizeof(loot));C.memset(C.addressof(items),0,C.sizeof(items));C.memset(C.addressof(player),0,C.sizeof(player));items.scene=ctx.scene;items.loot=C.pointer(loot);items.player=C.pointer(player);ctx.fault=items.fault=ctx.composeAnimation=ctx.composeCreation=0;loot.count=62;loot.words[340]=1;items.managerToken=MANAGER;items.playerToken=PLAYER;items.playerPrimaryToken=PL;items.playerPrivateToken=PP;items.tick=1000;items.lastSoundTick=999;items.animationDelta=17;items.audioEnabled=1;items.masterVolume=83;animation.delta=17;animation.volume=83
 put(A,[0x5137f0]);put(A+4,[0,0x1000000,SC]);put(A+76,[400,500]);put(A+100,[0,0,L,0,0,0]);put(A+200,[0]);put(A+0x170,[ROOTIMAGE,IMAGE]);put(A+0x190,[0]);put(L,[0x513820]);put(L+12,[SC,0x471330,0,0,0]);put(MANAGER+0x124,[1]);put(SC+8,[SC+0x100]);put(SC+40,[SC+0x200]);put(SC+44,[SC+0x300]);put(IMAGE+24,[13,16,2,0xfffffffe]);put(ROOTIMAGE+20,[FRAMES]);put(ROOTIMAGE+100,[1,4]);put(FRAMES,[IMAGE]*16);put(A+0x188,[0x513848,A,0,0,0,0,0,0,0,1,0x3f800000]);put(GLITTER+8,[0x40000]);put(GLITTERL+16,[0x10ff100]);put(PLAYER,[0]*128);put(PLAYER+108,[PL]);put(PLAYER+116,[A]);put(PLAYER+0x10c,[50]);put(PP,[0]*78);put(PL+12,[SC,0x415df0,PP,0,24]);put(SOUND+16,[POOL]);found=True;created=GLITTER;mutation=animationResult=0
 for i in range(62):loot.words[i]=ROOTIMAGE+i*64;loot.words[66+i]=(i+1)*5;loot.words[132+i]=0x10000;loot.words[274+i]=SOUND
 updateGlobals()
def compare(label,award=False):
 global calls,eventCount
 ctx.fault=items.fault=0;updateGlobals();before=bytes(heap);bi=bytes(image);bl=bytes(loot);bit=bytes(items);ba=bytes(animation);bp=bytes(player);nativeEvents.clear();errors.clear();out=U()
 ok=lib.claw_super_powerup_award(A,C.byref(ctx),dependency,None)if award else lib.claw_super_powerup_entry(A,C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,ctx.fault,errors);expected=raw(True);ev=list(nativeEvents);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(loot),bl,C.sizeof(loot));C.memmove(C.addressof(items),bit,C.sizeof(items));C.memmove(C.addressof(animation),ba,C.sizeof(animation));C.memmove(C.addressof(player),bp,C.sizeof(player));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);originalEvents.clear();result=m.call(0x41ce80 if award else 0x471330,0,pack(PLAYER if award else A));got=raw(False)
 if expected!=got:raise AssertionError((label,'full buffers',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if expected[i]!=got[i]][:24]))
 assert ev==originalEvents,(label,'events',ev,originalEvents)
 if not award:assert result==out.value,(label,'return',result,out.value)
 C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000);loot.words[:]=get(0x537ec8,341);loot.count=get(0x52a190)[0];items.lastSoundTick,items.lastSoundToken=get(0x534ec0,2);calls+=1;eventCount+=len(ev);return result
class Profile(C.Structure):_fields_=[('words',U*48),('selected',U),('level',U),('scales',U*3)]
SetRect=C.CFUNCTYPE(U,C.POINTER(Profile),U,C.POINTER(U),C.c_void_p)
lib.claw_elevator_initialize_profile.argtypes=[U,C.POINTER(Profile),SetRect,C.c_void_p]
resourceTokens={};_assets=None
def assets():
 global _assets
 if _assets is not None:return _assets
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';_assets={}
 def w(t):return struct.unpack_from('<I',blob,t)[0]
 def walk(t,n,path=()):
  end=t+n
  while t<end:
   k,target,size=w(t),w(t+4),w(t+8);start=t+(16 if k else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode()
   if k:walk(target,size,path+(name,));t=nul+1
   else:
    ext=blob[t+20:t+24].split(b'\0')[0][::-1].decode();p='/'.join(path+(name+'.'+ext,));t=nul+2;_assets[p]=blob[target:target+size]
 walk(w(131),w(135));return _assets
class Record(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(Record),C.POINTER(U)];lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
resourceProfiles=[]
def setupResources(group='GAME_HEALTH/MEDKIT'):
 data=assets()['GAME/ANIS/POWERUP.ANI'];sig,unused,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;put(SEQ+12,[FRAMES+0x200,count]);put(FRAMES+0x200,[RECORDS+i*48 for i in range(count)]);at=32+pl
 for i in range(count):
  record=Record();length=U();tail=data[at:];buf=(C.c_uint8*len(tail)).from_buffer_copy(tail);used=lib.claw_animation_decode_record(buf,len(tail),0,C.byref(record),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(record)));put(RECORDS+i*48,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);at+=used
 assert at==len(data)
 resourceTokens[b'GAME_POWERUP']=SEQ;put(A+0x188,[0x513848,A,0,0,0,0,0,0,0,1,0x3f800000])
 return count
previousEffect=effect
def effect(fn,t,args,name,native):
 if fn in(0x4c88e0,0x4208e0):return 0
 return previousEffect(fn,t,args,name,native)
abis.update({0x4c88e0:(4,16),0x4208e0:(4,16)})
def configureResources():
 # Identity allocation is declared transport, separated from actual resource bytes.
 import re
 source=(ROOT/'Sources/WorldLootRuntime.cpp').read_text();names=re.findall(r'\{0x2,.*?,"([^"]+)"\}',source)
 for n,name in enumerate(dict.fromkeys(names)):resourceTokens[name.encode()]=BASE+0x20000+n*64
 put(SC+16,[SC+0x400]);put(SC+20,[SC+0x500]);put(SC+40,[SC+0x200]);put(SC+44,[SC+0x300])
def bindPID(path):
 data=assets()[path];_,_,w,ht,ox,oy=struct.unpack_from('<6I',data);geo=Geometry();lib.claw_sprite_set_geometry(C.byref(geo),w,ht,ox,oy);put(IMAGE+16,list(struct.unpack('<10I',bytes(geo)))[:6]);return {'path':path,'width':w,'height':ht,'offsetX':C.c_int32(ox).value,'offsetY':C.c_int32(oy).value}
