"""Private raw graph oracle; original bodies execute from the hash-pinned EXE."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/powerup-object-agent'
sources=['PowerupObjectRuntime','ItemPickupRuntime','WorldLootRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','ActorResourceBindings','AnimationEngine','AnimationOperations','PlayerPowerupRuntime','PlayerInputDispatch','PlayerEngine','PlayerPhysics','GameImageRuntime','SpriteGeometry','PIDRaster','PIDSurfaceRaster','PIDBlitter',
    'PlayerDamage','PlayerInitialization','PlayerLocomotion','PlayerAirStates','CollisionResponse','TileCollision']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',
    *[str(ROOT/'Sources'/f'{name}.cpp')for name in sources],str(WORK/'image-effect-adapter.cpp'),
    '-o',str(WORK/'libPowerupObjectRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32)
Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32)
Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','powerup','remaining','expired','musicDisabled','cycleRemaining','cycleIndex')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000
A,L,P,MUSICOWNER,MUSICOWNER2,MUSIC,MUSIC2,LEVEL,POWER,THIRD,VT,IM,ARRAY,IMAGE,COMP,OLDGLITTER,NEWGLITTER,NEWLOGIC,PARENT,ACTORS=[BASE+0x1000+i*0x1000 for i in range(20)]
SUSPEND,RESUME,STOP=0x10ff100,0x10ff110,0x10ff120
GLOBALS=(0x5371fc,0x537e88,0x534eac,0x534ea8,0x534eb8,0x53c9c0,0x534ec8,0x534ecc)
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear()
lib=C.CDLL(str(WORK/'libPowerupObjectRuntime.dylib'))
lib.claw_player_powerup_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_player_powerup_entry.restype=C.c_uint32
lib.claw_powerup_test_image_effect.argtypes=[C.POINTER(Context),C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32)];lib.claw_powerup_test_image_effect.restype=C.c_uint32
heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g)
rng=random.Random(0x41f990);native_events=[];original_events=[];calls=events=0;mutation=0;created=NEWGLITTER;levelResult=LEVEL;powerResult=POWER;errors=[];effects=(C.c_uint32*4)();serial=0
GLOBAL_START,GLOBAL_SIZE=0x520000,0x24000
global_seed=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE));native_global_updates=None
def put(t,values,native=True):
    data=struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
    if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
    else:m.u.mem_write(t,data)
def get(t,n=1,native=True):
    data=C.string_at(C.addressof(heap)+t-BASE,n*4)if native else bytes(m.u.mem_read(t,n*4))
    return list(struct.unpack('<'+'I'*n,data))
def glob(index,native=True):return getattr(g,Globals._fields_[index][0])if native else m.read_words(GLOBALS[index],1)[0]
def setglob(index,value,native):
    if native:setattr(g,Globals._fields_[index][0],value)
    else:m.write_words(GLOBALS[index],[value])
def raw(native):return bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))
def global_raw(native):
    if not native:return bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
    data=bytearray(global_seed)
    for i,address in enumerate(GLOBALS):struct.pack_into('<I',data,address-GLOBAL_START,glob(i))
    if native_global_updates:
        for address,value in native_global_updates().items():data[address-GLOBAL_START:address-GLOBAL_START+len(value)]=value
    return bytes(data)
def snapshot(native):return tuple(glob(i,native)for i in range(8)),hashlib.sha256(raw(native)).digest(),hashlib.sha256(global_raw(native)).digest()
@Lookup
def lookup(user,token,count):
    if BASE<=token and token+count*4<=BASE+SIZE:return C.addressof(heap)+token-BASE
    return None
ctx.scene=Host(None,lookup,Allocate(),Free(),Invoke(),Clock())
def effect(fn,receiver,args,native):
    global serial
    if mutation and fn==0x4b54a0 and args==[0x524d80]:
        # Real setter reloads global manager after this service. Preserve
        # the original incoming receiver while moving future operations.
        setglob(0,MUSICOWNER2,native)
    if mutation==2 and fn==0x4b5bd0:
        setglob(2,0x26bd if receiver==POWER else 0x26bc,native)
        put(A+0xd4,[0x11111111],native)
    if fn==0x4b54a0:return levelResult if args[0]==0x524d80 else powerResult
    if fn==0x4b5bd0:return get(receiver+0x10,native=native)[0]
    if fn==0x4b5570:put(receiver+0x20,[get(receiver+0x20,native=native)[0]+1],native);return 0
    if fn in(SUSPEND,RESUME,STOP):
        put(receiver+0x18,[get(receiver+0x18,native=native)[0]+1],native)
        return 0
    if fn==0x48c8a0:
        put(PARENT+0x100,[args[0],args[1]],native)
        if mutation==2:setglob(4,0x24681357,native)
        return 1
    if fn==0x4c8da0:
        assert receiver==ACTORS and args==[1,100,100,0,0x5225a0,0]
        if created:
            put(created+0xc,[PARENT],native);put(created+0x6c,[NEWLOGIC],native)
            put(created+0x4c,[100,100],native)
        return created
    if fn==0x4c6130:
        if mutation==2:
            put(IM+0x68,[1],native)
            put(IMAGE+0x30,[0],native)
        if native:
            return lib.claw_powerup_test_image_effect(C.byref(ctx),receiver,*args,effects)
        return None # Execute the entire original compressed-effect body.
    raise AssertionError(('unexpected dependency',hex(fn),hex(receiver),args))
@Dependency
def dependency(context,call,user):
    c=call.contents;args=list(c.arguments[:c.argumentCount])
    event=(c.function,c.receiver,tuple(args),snapshot(True));native_events.append(event)
    try:return effect(c.function,c.receiver,args,True)or 0
    except Exception as e:errors.append(e);return 0
COUNTS={0x4b54a0:1,0x4b5bd0:0,0x4b5570:1,SUSPEND:0,RESUME:1,STOP:0,0x48c8a0:2,0x4c8da0:6,0x4c6130:2}
CDECL={0x48c8a0}
def hook(u,address,size,user):
    if address not in COUNTS:return
    sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,COUNTS[address])
    receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX)
    original_events.append((address,receiver,tuple(args),snapshot(False)))
    value=effect(address,receiver,args,False)
    if value is None:return
    u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in CDECL else COUNTS[address]*4))
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(old=0,remaining=0):
    global serial
    serial=0;ctx.fault=0;C.memset(C.addressof(heap),0xa5,SIZE)
    for token,count in((A,128),(L,93),(P,78),(MUSICOWNER,40),(MUSICOWNER2,40),(MUSIC,40),(MUSIC2,40),(LEVEL,24),(POWER,24),(VT,16),(IM,32),(IMAGE,16),(COMP,10),(NEWGLITTER,128),(NEWLOGIC,93)):
        put(token,[rng.getrandbits(32)for _ in range(count)])
    put(A+0xc,[PARENT]);put(PARENT+8,[ACTORS]);put(A+0x6c,[L]);put(L+0x14,[P])
    put(A+0x170,[IM]);put(A+0x174,[IMAGE]);put(P+0x130,[OLDGLITTER])
    put(MUSICOWNER+0x14,[rng.choice([0,1])]);put(MUSICOWNER+0x50,[MUSIC]);put(MUSICOWNER2+0x14,[1]);put(MUSICOWNER2+0x50,[MUSIC2])
    put(MUSIC+0x1c,[rng.choice([0,LEVEL,POWER,THIRD])]);put(MUSIC2+0x1c,[rng.choice([0,LEVEL,POWER,THIRD])])
    put(LEVEL,[VT]);put(POWER,[VT]);put(LEVEL+0x10,[rng.choice([0,1])]);put(POWER+0x10,[rng.choice([0,1])]);put(VT+0x28,[SUSPEND,RESUME,STOP])
    put(IM+0x14,[ARRAY]);put(IM+0x64,[0,3]);put(ARRAY,[IMAGE,0,IMAGE+0x100,IMAGE+0x200])
    put(IMAGE+0x30,[COMP]);put(IMAGE+0x100+0x30,[0]);put(IMAGE+0x200+0x30,[COMP+0x100])
    g.managerToken=MUSICOWNER;g.playerToken=A;g.powerup=old;g.remaining=remaining
    g.expired=rng.getrandbits(32);g.musicDisabled=rng.choice([0,1]);g.cycleRemaining=rng.choice([0,1,99,100,0xffffffff]);g.cycleIndex=rng.choice([0x34,0x35,0x36,0x37,0x65,0,0xffffffff])
    for i in range(4):effects[i]=rng.getrandbits(32)
    sync()
def sync():
    global global_seed
    m.u.mem_write(BASE,bytes(heap))
    for i,address in enumerate(GLOBALS):m.write_words(address,[glob(i)])
    m.write_words(0x5430b0,list(effects))
    global_seed=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
def compare(fn,args,label,receiver=0):
    global calls,events
    sync();native_events.clear();original_events.clear();errors.clear();ctx.fault=0
    values=(C.c_uint32*len(args))(*(x&0xffffffff for x in args));result=C.c_uint32()
    done=lib.claw_player_powerup_entry(fn,receiver,values,len(args),C.byref(ctx),dependency,None,C.byref(result))
    assert not errors,errors
    assert done==1 and ctx.fault==0,(label,'native fault',ctx.fault)
    original=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
    if fn in(0x41f990,0x41fc00,0x4ce7b0,0x448400):assert original==result.value,(label,'return',original,result.value)
    assert native_events==original_events,(label,'events',[(i,a,b)for i,(a,b)in enumerate(zip(native_events,original_events))if a!=b][:3],len(native_events),len(original_events))
    assert snapshot(True)==snapshot(False),(label,'whole snapshot',snapshot(True)[0],snapshot(False)[0])
    assert raw(True)==raw(False),(label,'raw heap bytes')
    assert global_raw(True)==global_raw(False),(label,'whole global image bytes')
    calls+=1;events+=len(native_events)

U=C.c_uint32
class Loot(C.Structure):_fields_=[('words',U*341)]+[(n,U)for n in('itemCount','audioVolume','highLaunch','configurationWord')]
class Items(C.Structure):_fields_=[('scene',Host),('loot',C.POINTER(Loot)),('player',C.c_void_p)]+[(n,U)for n in('playerToken','playerPrimaryToken','playerPrivateToken','managerToken','animationDelta','stageDelta','tick','audioEnabled','masterVolume','lastSoundTick','lastSoundToken','auxiliaryManagerToken','auxiliarySceneToken','composeCreation','fault')]
class Animation(C.Structure):_fields_=[('animationDelta',U),('audioPosition',U)]
class Physics(C.Structure):_fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3)for n in('acceleration','velocity','position','minimum','maximum','delta')]+[('stopped',U),('unused',U)]+[(n,C.c_double*3)for n in('remainder','maximumDelta','maximumVelocity')]
class ObjectArgs(C.Structure):_fields_=[('words',U*6),('count',U)]
class ObjectContext(C.Structure):_fields_=[('scene',Host),('loot',C.POINTER(Loot)),('items',C.POINTER(Items)),('powerups',C.POINTER(Context)),('physics',C.POINTER(Physics)),('animation',C.POINTER(Animation))]+[(n,U)for n in('inputToken','curseEnabled','warpX','warpY','composeAnimation','composeCreation','fault')]
class ObjectCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*6),('argumentCount',U),('name',C.c_char_p)]
ObjectDependency=C.CFUNCTYPE(U,C.POINTER(ObjectContext),C.POINTER(ObjectCall),C.c_void_p)
lib.claw_powerup_object_entry.argtypes=[U,U,ObjectArgs,C.POINTER(ObjectContext),ObjectDependency,C.c_void_p,C.POINTER(U)]
ITEM,IL,CONFIG,CONFIGVT,MAP,PLANE,INPUT,WINDOW,SOUND,SOUNDPOOL,CURSELIST,NODE,PAIR,NAME,ROOTS=[BASE+0x21000+i*0x1000 for i in range(15)]
MODE,CURSE_ACCEPT=0x10ff220,0x10ff240;POST=0x10ff260
loot=Loot();items=Items();physics=Physics();animation=Animation();oc=ObjectContext();modeValues=[3];modeIndex=0;curseAccepted=0;glitterFound=True;lookupFound=True;resourceRoots={};object_calls=object_events=0;replay=__import__('io').BytesIO();replayCases=0
PEBASE,PEEND,_=next(t for t in m.u.mem_regions()if t[0]==0x400000);pe=(C.c_uint8*(PEEND-PEBASE+1)).from_buffer_copy(bytes(m.u.mem_read(PEBASE,PEEND-PEBASE+1)))
@Lookup
def objectLookup(_,t,n):
 if t%4:return None
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if PEBASE<=t and t+n*4<=PEEND+1:return C.addressof(pe)+t-PEBASE
 return None
@Invoke
def sceneInvoke(_,e):
 args=list(e.arguments[:e.argumentCount]);native_events.append((e.function,e.receiver,tuple(args),snapshot(True)))
 try:return object_effect(e.function,e.receiver,args,True)or 0
 except BaseException as ex:errors.append(ex);oc.fault=1;return 0
@Allocate
def noAllocate(_,n):errors.append(('unexpected allocation',n));oc.fault=1;return 0
@Free
def noFree(_,t):errors.append(('unexpected free',t));oc.fault=1
@Clock
def noClock(_):errors.append('unexpected clock');oc.fault=1;return 0
objectHost=Host(None,objectLookup,noAllocate,noFree,sceneInvoke,noClock)
ctx.scene=objectHost;items.scene=objectHost;items.loot=C.pointer(loot);oc.scene=objectHost;oc.loot=C.pointer(loot);oc.items=C.pointer(items);oc.powerups=C.pointer(ctx);oc.physics=C.pointer(physics);oc.animation=C.pointer(animation);oc.inputToken=INPUT
profile=json.loads((ROOT/'Tests/world_loot_initializer_profile.json').read_text())
for row in profile['records'][:62]:resourceRoots.setdefault(row['image'],ROOTS+len(resourceRoots)*0x40)
resourceRoots.setdefault('GAME_MAPPIECE',ROOTS+len(resourceRoots)*0x40)
resourceRoots.setdefault('GAME_CURSE3',ROOTS+len(resourceRoots)*0x40)
PROFILE_TOKEN=BASE+0x3f000
def updates():
 pack=lambda *v:struct.pack('<'+'I'*len(v),*v)
 return {0x537960:pack(PROFILE_TOKEN),0x534db8:bytes(physics),0x537204:pack(INPUT),0x5430c4:pack(animation.animationDelta),0x53720c:pack(items.stageDelta),0x537210:pack(items.tick),0x532c0c:pack(items.audioEnabled),0x532c10:pack(items.masterVolume),0x534ec0:pack(items.lastSoundTick),0x534ec4:pack(items.lastSoundToken),0x534874:pack(items.auxiliaryManagerToken),0x5349dc:pack(items.auxiliarySceneToken),0x537ec8:bytes(loot.words),0x52a190:pack(loot.itemCount),0x52550c:pack(oc.curseEnabled),0x529fa0:pack(oc.warpX),0x529fa4:pack(oc.warpY)}
def original_updates():
 put(PROFILE_TOKEN,[loot.configurationWord])
 for t,b in updates().items():m.u.mem_write(t,b)
base_effect=effect
old_hook=hook
# Extend the old finite powerup physical transport, retaining its snapshots.
def object_effect(fn,receiver,args,native):
 global modeIndex
 if fn==MODE:value=modeValues[min(modeIndex,len(modeValues)-1)];modeIndex+=1;return value
 if fn==CURSE_ACCEPT:return curseAccepted
 if fn==0x4f6286:
  if mutation==4 and receiver==ROOTS+16:put(ITEM+0x170,[THIRD],native);put(ITEM+100,[777],native)
  token=args[0]
  if token==0x5279b8:return resourceRoots['GAME_TREASURE_COINS']
  if token==0x52a1ec:return resourceRoots['GAME_POWERUPS_EXTRALIFE']
  if token==0x52a07c:return resourceRoots['GAME_WARP']
  if receiver==ROOTS+0x400+16:return SOUND if lookupFound else 0
  if receiver==ROOTS+0x2000+16:return BASE+0x3d000
  if receiver==ROOTS+16:
   text=bytes(m.u.mem_read(token,150)).split(b'\0',1)[0].decode()
   resourceRoots.setdefault(text,ROOTS+len(resourceRoots)*0x40)
   return resourceRoots[text]
  if token==0x5246dc:return THIRD if lookupFound else 0
  raise AssertionError(('unknown image lookup',hex(token)))
 if fn in(0x4c79e0,0x4c8220,0x4c82a0):
  if mutation==3:put(ITEM+8,[get(ITEM+8,native=native)[0]|1],native);put(MUSICOWNER+0x124,[0],native)
  return 1
 if fn==0x4c8da0 and args[4]==0x522950:
  assert receiver==ACTORS
  if glitterFound:put(NEWGLITTER+12,[PARENT],native);put(NEWGLITTER+0x6c,[NEWLOGIC],native)
  return NEWGLITTER if glitterFound else 0
 if fn==0x4b45f0:
  if mutation==3:
   put(ITEM+0x108,[0],native)
   if native:items.lastSoundToken^=1
   else:m.write_words(0x534ec4,[m.read_words(0x534ec4,1)[0]^1])
  return 1
 if fn==0x546d50:return 1
 if fn==0x4b8960:return 0
 if fn==0x41c4e0:
  # Explicit armed-cleanup boundary only. Normal unarmed41c4e0 executes its
  # whole source body / composes the frozen native counterpart.
  assert get(P+300,native=native)[0];put(P+300,[0],native);return 0
 if fn in(0x403ab0,0x403ac0):return 100 if fn==0x403ab0 else 200
 return base_effect(fn,receiver,args,native)
effect=object_effect
@ObjectDependency
def objectDependency(c,event,_):
 e=event.contents;args=list(e.arguments[:e.argumentCount]);native_events.append((e.function,e.receiver,tuple(args),snapshot(True)))
 try:return object_effect(e.function,e.receiver,args,True)or 0
 except BaseException as ex:errors.append(ex);oc.fault=1;return 0
COUNTS.update({MODE:0,CURSE_ACCEPT:1,0x4c79e0:2,0x4c8220:1,0x4c82a0:1,0x4b45f0:4,0x4b8960:1,0x403ab0:0,0x403ac0:0})
CDECL.update((0x4b8960,))
m.u.mem_write(0x546d50,struct.pack('<I',POST))
def extraHook(u,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);receiver=u.reg_read(UC_X86_REG_ECX);args=[name];original_events.append((address,receiver,tuple(args),snapshot(False)));value=object_effect(address,receiver,args,False);m.write_words(out,[value]);u.reg_write(UC_X86_REG_EAX,int(bool(value)));u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+12)
 if address==POST:
  args=m.read_words(sp+4,4);original_events.append((0x546d50,0,tuple(args),snapshot(False)));object_effect(0x546d50,0,args,False);u.reg_write(UC_X86_REG_EAX,1);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+20)
 if address==0x41c4e0 and get(P+300,native=False)[0]:
  args=m.read_words(sp+4,3);original_events.append((address,0,tuple(args),snapshot(False)));object_effect(address,0,args,False);u.reg_write(UC_X86_REG_EAX,0);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4)
m.u.hook_add(UC_HOOK_CODE,extraHook)
def prepareObject(seed=0,callback=0x470430,imageName='GAME_WARP'):
 global native_global_updates,modeIndex,mutation
 mutation=0;prepare();modeIndex=0;ctx.scene=objectHost;oc.fault=0;oc.curseEnabled=1;oc.composeAnimation=oc.composeCreation=0;oc.warpX=oc.warpY=0;animation.animationDelta=16;animation.audioPosition=100
 for n in('playerToken','playerPrimaryToken','playerPrivateToken','managerToken','animationDelta','stageDelta','tick','audioEnabled','masterVolume','lastSoundTick','lastSoundToken','auxiliaryManagerToken','auxiliarySceneToken','composeCreation','fault'):setattr(items,n,0)
 items.playerToken=A;items.playerPrimaryToken=L;items.playerPrivateToken=P;items.managerToken=MUSICOWNER;items.animationDelta=items.stageDelta=16;items.tick=seed;items.audioEnabled=1;items.masterVolume=100
 put(MUSICOWNER+44,[CONFIG]);put(MUSICOWNER2+44,[CONFIG]);put(MUSICOWNER+0x124,[1]);put(MUSICOWNER+4,[WINDOW]);put(WINDOW+4,[0x12345]);put(CONFIG,[CONFIGVT]);put(CONFIGVT+16,[MODE]);put(CONFIGVT+0x58,[CURSE_ACCEPT]);put(CONFIG+0xbd4,[CURSELIST]);put(CONFIG+0xbcc,[0]);put(CURSELIST+4,[0]);put(ITEM,[0x5137f0]);put(ITEM+12,[PARENT]);put(ITEM+0x6c,[IL]);put(ITEM+76,[100,200]);put(ITEM+100,[0]);put(ITEM+8,[0x40000]);put(ITEM+0x164,[0]);put(ITEM+200,[0]);put(IL+0x16c,[0]);put(ITEM+0x190,[0]);put(ITEM+0x170,[resourceRoots.get(imageName,THIRD)]);put(ITEM+0x174,[IMAGE]);put(IMAGE+24,[20,30,4,8]);put(IL+16,[callback]);put(IL+28,[0]);put(ITEM+0x104,[0,0]);put(PARENT+16,[ROOTS]);put(PARENT+20,[ROOTS+0x2000]);put(PARENT+40,[ROOTS+0x400]);put(PARENT+44,[ROOTS+0x800]);put(PARENT+0x24,[MAP]);put(MAP+0x5c,[PLANE]);put(PLANE+0x84,[300,400]);put(SOUND+16,[SOUNDPOOL]);put(SOUNDPOOL+40,[750]);put(P+4,[0]);put(P+300,[0]);put(L+28,[4]);put(INPUT+12,[0xffffffff]);put(A+0xcc,[4]);put(A+0x148,[10,20]);put(P+60,[0]);put(A+0x74,[ITEM]);put(IL+0x168,[SOUND]);put(P+124,[3])
 for name,_ in Physics._fields_:
  if name in('stopped','unused'):setattr(physics,name,rng.getrandbits(32))
  elif name in('elapsed','timestep'):setattr(physics,name,rng.uniform(-10,10))
  else:getattr(physics,name)[:]=[rng.uniform(-10,10)for _ in range(3)]
 for i in range(341):loot.words[i]=rng.getrandbits(32)
 loot.words[340]=1;loot.itemCount=62;loot.configurationWord=0;put(PROFILE_TOKEN,[loot.configurationWord])
 for row in profile['records'][:62]:i=row['id'];loot.words[i]=resourceRoots[row['image']];loot.words[66+i]=row['value'];loot.words[132+i]=row['mask'];loot.words[274+i]=SOUND
 native_global_updates=updates;original_updates();sync()
def compareObject(fn,args,label,receiver=0,void=False,award=False):
 global object_calls,object_events,modeIndex,replayCases
 original_updates();sync();native_events.clear();original_events.clear();errors.clear();oc.fault=ctx.fault=items.fault=0;oldModeIndex=modeIndex;before=bytes(heap);beforeGlobal=global_raw(True);beforeState=replayState();values=ObjectArgs();values.count=len(args);values.words[:len(args)]=args;result=U();done=lib.claw_powerup_object_award(ITEM,C.byref(oc),objectDependency,None,C.byref(result)) if award else lib.claw_powerup_object_entry(fn,receiver,values,C.byref(oc),objectDependency,None,C.byref(result));assert done and not oc.fault and not errors,(label,'native',done,oc.fault,errors);expectedMode=modeIndex;modeIndex=oldModeIndex
 original=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
 if not void:assert original==result.value,(label,'result',original,result.value)
 assert modeIndex==expectedMode,(label,'mode getter order')
 assert native_events==original_events,(label,'events',[(i,x,y)for i,(x,y)in enumerate(zip(native_events,original_events))if x!=y][:4],len(native_events),len(original_events))
 assert raw(True)==raw(False),(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(True),raw(False)))if x!=y][:20]);assert global_raw(True)==global_raw(False),(label,'globals',[(hex(GLOBAL_START+i),x,y)for i,(x,y)in enumerate(zip(global_raw(True),global_raw(False)))if x!=y][:16]);assert not ctx.fault and not items.fault
 if not native_events and (object_calls%3==0 or fn not in replayFunctions or label.startswith('sanitizer/')):
  padded=list(args)+[0]*(6-len(args));replay.write(struct.pack('<12I',fn,receiver,len(args),*padded,result.value,int(void),int(award))+beforeState+replayState()+before+raw(True));replayCases+=1;replayFunctions.add(fn)
 assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+(8 if fn==0x436860 else 0),(label,'original return stack')
 object_calls+=1;object_events+=len(native_events);return result.value

lib.claw_powerup_object_award.argtypes=[U,C.POINTER(ObjectContext),ObjectDependency,C.c_void_p,C.POINTER(U)]
# Read-only REZ inventory; no claim that Python models the original transport.
def assets():
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';out={}
 def w(t):return struct.unpack_from('<I',blob,t)[0]
 def walk(at,size,path=()):
  end=at+size
  while at<end:
   kind,target,length=w(at),w(at+4),w(at+8);start=at+(16 if kind else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode()
   if kind:walk(target,length,path+(name,));at=nul+1
   else:ext=blob[at+20:at+24].split(b'\0')[0][::-1].decode();out['/'.join(path+(name+'.'+ext,))]=blob[target:target+length];at=nul+2
 walk(w(131),w(135));return out
class WorldState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class WorldContext(C.Structure):_fields_=[(n,U)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('width',C.c_int32),('height',C.c_int32),('registryToken',U),('layers',U*3),('entryToken',U),('callback',U),('flags',U)]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('text',C.c_char_p)]
class WorldInfo(C.Structure):_fields_=[('consumed',U),('created',U)]
WorldDependency=C.CFUNCTYPE(U,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDependency,C.c_void_p,C.POINTER(WorldInfo)]
@WorldDependency
def worldDependency(s,c,e,_):
 if e.contents.function==0x4f6286:return BASE+0x3d000
 if e.contents.function in(0x4c7970,0x4c7900,0x4f4630):return 0
 raise AssertionError(('unexpected raw record setup',hex(e.contents.function)))
def sourceRecord(record):
 v=record['words'];ss=record['strings'];data=struct.pack('<71I',*v)+b''.join(s.encode()+bytes(n-len(s))for s,n in zip(ss,v[1:5]));assert hashlib.sha256(data).hexdigest()==record['rawSHA256']
 state=WorldState((U*128)(*get(ITEM,128)),(U*93)(*get(IL,93)));c=WorldContext(PARENT,ITEM,IL,2,24576,6144,ROOTS+0x2000+16,(U*3)(0,0,0),BASE+0x3d000,0x470430 if ss[1]=='SpecialPowerup'else 0x470a20,2)
 info=WorldInfo();b=(C.c_uint8*len(data)).from_buffer_copy(data);assert lib.claw_world_object_load(b,len(data),C.byref(state),C.byref(c),worldDependency,None,C.byref(info))==len(data)and info.created
 put(ITEM,list(state.actor));put(IL,list(state.logic))
class BindingState(C.Structure):_fields_=[('actor',U*128),('secondary',U*93)]
class ImageBinding(C.Structure):_fields_=[('token',U),('minimum',C.c_int32),('maximum',C.c_int32),('first',C.c_int32),('images',C.POINTER(U)),('count',C.c_size_t)]
class BindingContext(C.Structure):_fields_=[('imageRegistry',U),('logicRegistry',U),('image',ImageBinding),('metadata',U),('callback',U),('flags',U),('destructor',U)]
class BindingCall(C.Structure):_fields_=[('function',U),('receiver',U),('argument',U),('name',C.c_char_p)]
BindingDependency=C.CFUNCTYPE(U,C.POINTER(BindingState),C.POINTER(BindingContext),C.POINTER(BindingCall),C.c_void_p)
lib.claw_actor_bind_default_image.argtypes=[C.POINTER(BindingState),C.POINTER(BindingContext),C.c_char_p,BindingDependency,C.c_void_p]
lib.claw_actor_bind_indexed_image.argtypes=lib.claw_actor_bind_default_image.argtypes[:3]+[C.c_int32]+lib.claw_actor_bind_default_image.argtypes[3:]
SEQ,PTRS,RECORDS,IMAGES,IMAGELEAVES=BASE+0x36000,BASE+0x36400,BASE+0x36800,BASE+0x38000,BASE+0x38400
resourceEvidence=[];boundRoot=0;decodeMode=False;decodedEvent=0;decodedCalls=0;bindingCalls=0
class Record(C.Structure):_fields_=[(n,U)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(Record),C.POINTER(U)]
@BindingDependency
def bindingDependency(s,c,e,_):
 native_events.append((0x4f6286,e.contents.receiver,(NAME,),snapshot(True)));return boundRoot
@Invoke
def animationInvoke(_,e):
 args=list(e.arguments[:e.argumentCount]);native_events.append((e.function,e.receiver,tuple(args),snapshot(True)));return object_effect(e.function,e.receiver,args,True)or 0
# Source raw ANI bodies execute under composition; suppress only the original
# finite hook's ANI keys, leaving all other transport hooks active.
COUNTS_before=dict(COUNTS)
def enableAnimation():
 oc.composeAnimation=1
 for f in(0x4c79e0,0x4c8220,0x4c82a0):COUNTS.pop(f,None)
def disableAnimation():
 oc.composeAnimation=0
 for f in(0x4c79e0,0x4c8220,0x4c82a0):COUNTS[f]=COUNTS_before[f]
previousObjectEffect=object_effect
def object_effect(fn,receiver,args,native):
 if fn==0x4f6286 and decodeMode:return decodedEvent
 if fn==0x4f6286 and receiver==ROOTS+0x800+16:return SEQ
 if fn in(0x4c88e0,0x4208e0):return 0
 return previousObjectEffect(fn,receiver,args,native)
effect=object_effect
COUNTS.update({0x4c88e0:4,0x4208e0:4})
def installANI(data):
 global decodeMode,decodedEvent,decodedCalls
 n=struct.unpack_from('<I',data,12)[0];pathlen=struct.unpack_from('<I',data,16)[0];assert 0<n<50;put(SEQ+12,[PTRS,n]);put(PTRS,[RECORDS+64*i for i in range(n)]);at=32+pathlen
 for i in range(n):
  flags=struct.unpack_from('<H',data,at)[0];decodedEvent=SOUND if flags&2 else 0;rec=Record();length=U();tail=data[at:];buf=(C.c_uint8*len(tail)).from_buffer_copy(tail);used=lib.claw_animation_decode_record(buf,len(tail),decodedEvent,C.byref(rec),C.byref(length));assert used
  token=RECORDS+64*i;put(token,[rng.getrandbits(32)for _ in range(12)]);sync();m.u.mem_write(BASE+0x3a000,tail);decodeMode=True
  try:m.call(0x4d76e0,token,struct.pack('<2I',PARENT+40,BASE+0x3a000))
  finally:decodeMode=False
  rawRecord=m.read_words(token,12)
  vals=[getattr(rec,k)for k,_ in Record._fields_];assert vals==[rawRecord[1]&0xffff]+rawRecord[2:10]+[rawRecord[11]];assert used==20+m.read_words(0x543174,1)[0]
  put(token,rawRecord);at+=used;decodedCalls+=1
 assert at==len(data)
def bindRealImages(name,imageID,assets,label):
 global boundRoot,bindingCalls
 import re
 prefix='GAME/IMAGES/'+name.removeprefix('GAME_').replace('_','/')+'/'
 files={p:b for p,b in assets.items()if p.startswith(prefix)and p.endswith('.PID')};assert files,(name,prefix)
 # FrozenImageRegistry4ce5e0 uses the first ASCII digit substring, none=>0.
 ids={int(match.group())if(match:=re.search(r'[0-9]+',p.rsplit('/',1)[1].split('.')[0]))else 0:p for p in files};first,last=min(ids),max(ids);assert last<100
 table=[0]*(last+1);profiles=[]
 for k,p in ids.items():
  t=IMAGELEAVES+64*k;table[k]=t;v=struct.unpack_from('<8I',files[p]);width,height,ox,oy=v[2:6];put(t+24,[width//2,height//2,ox,oy]);profiles.append({'path':p,'id':k,'width':width,'height':height,'offsetX':ox,'offsetY':oy,'SHA256':hashlib.sha256(files[p]).hexdigest()})
 boundRoot=resourceRoots[name];put(boundRoot+20,[IMAGES]);put(boundRoot+100,[first,last]);put(IMAGES,table);encoded=name.encode()+b'\0';heap[NAME-BASE:NAME-BASE+len(encoded)]=encoded
 c=BindingContext();c.imageRegistry=ROOTS+16;c.image=ImageBinding(0,first,last,0,C.cast(C.addressof(heap)+IMAGES-BASE,C.POINTER(U)),last+1);s=BindingState((U*128)(*get(ITEM,128)),(U*93)());original_updates();sync();before=bytes(heap);native_events.clear();original_events.clear()
 if imageID==0xffffffff:r=lib.claw_actor_bind_default_image(C.byref(s),C.byref(c),encoded,bindingDependency,None);fn=0x4c7970;args=[NAME]
 else:r=lib.claw_actor_bind_indexed_image(C.byref(s),C.byref(c),encoded,C.c_int32(imageID).value,bindingDependency,None);fn=0x4c7900;args=[NAME,imageID]
 assert r==1;put(ITEM,list(s.actor));m.call(fn,ITEM,struct.pack('<'+'I'*len(args),*args));assert raw(True)==raw(False)and native_events==original_events,(label,'whole original image binding');bindingCalls+=1;resourceEvidence.append({'name':name,'first':first,'last':last,'files':profiles})
# Original generic creator prefix4c98c0 plus caller's animation-derived stores.
from unicorn.x86_const import UC_X86_REG_EBX
ctorMode=False;ctorResult=IL;ctorAllocations=[];constructorCalls=0;unsafePrefixes=0
lib.claw_world_object_construct.argtypes=[C.POINTER(WorldState),C.POINTER(WorldContext),U]
lib.claw_world_object_initialize.argtypes=[C.POINTER(WorldState),C.POINTER(WorldContext),U,U,U]
def ctorHook(u,address,size,user):
 if not ctorMode or address!=0x4f63ec:return
 sp=u.reg_read(UC_X86_REG_ESP);n=m.read_words(sp+4,1)[0];ctorAllocations.append(n);assert n==0x174;u.reg_write(UC_X86_REG_EAX,ctorResult);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4)
m.u.hook_add(UC_HOOK_CODE,ctorHook)
def constructor(record,fail=False):
 global ctorMode,ctorResult,constructorCalls
 v=record['words'];fn=0x470430 if record['strings'][1]=='SpecialPowerup'else 0x470a20
 c=WorldContext(PARENT,ITEM,0 if fail else IL,2,24576,6144,ROOTS+0x2000+16,(U*3)(),BASE+0x3d000,fn,2);state=WorldState((U*128)(*get(ITEM,128)),(U*93)(*get(IL,93)));original_updates();sync();before=bytes(heap)
 lib.claw_world_object_construct(C.byref(state),C.byref(c),v[0]);put(ITEM,list(state.actor))
 if not fail:put(IL,list(state.logic))
 ctorMode=True;ctorResult=0 if fail else IL;ctorAllocations.clear()
 try:
  result=m.call(0x4c98c0,ITEM,struct.pack('<3I',PARENT,v[0],0));m.u.reg_write(UC_X86_REG_EBX,ITEM);m.u.emu_start(0x4d18a7,0x4d1905,count=1000)
 finally:ctorMode=False
 assert result==ITEM and ctorAllocations==[0x174] and m.u.reg_read(UC_X86_REG_EIP)==0x4d1905 and raw(True)==raw(False),('generic ctor prefix',v[0],fail)
 constructorCalls+=1
 if fail:return
 put(PARENT+0x24,[c.sceneDefaultType]);put(c.entryToken+8,[2,0,fn]);sync();r=lib.claw_world_object_initialize(C.byref(state),C.byref(c),*v[5:8]);put(ITEM,list(state.actor));put(IL,list(state.logic));original=m.call(0x4c9d40,ITEM,struct.pack('<4I',*v[5:8],c.entryToken));assert original==r==1 and raw(True)==raw(False),('generic init',v[0]);constructorCalls+=1

replayFunctions=set()
def replayState():
 return bytes(loot)+bytes(g)+bytes(items)[Items.playerToken.offset:Items.playerToken.offset+60]+bytes(physics)+bytes(animation)+bytes(oc)[ObjectContext.inputToken.offset:ObjectContext.inputToken.offset+28]
