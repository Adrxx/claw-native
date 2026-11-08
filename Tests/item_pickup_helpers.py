"""Disjoint raw SceneActorHost oracle for ordinary item pickup graphs."""
from pathlib import Path
source=Path(__file__).with_name('world_loot_helpers.py').read_text()
source=source.replace("WORK=ROOT/'work/world-loot-agent'","WORK=ROOT/'work/item-pickup-agent'")
source=source.replace("('WorldLootRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp')","('BouncingGoodieLogic.cpp','GenericEnemy.cpp','ItemPickupRuntime.cpp','PlayerDamage.cpp','PlayerPhysics.cpp','WorldLootRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp')")
source=source.replace("str(WORK/'libWorldLootRuntime.dylib')","str(ROOT/'Tests/item_pickup_test_helpers.cpp'),str(WORK/'libWorldLootRuntime.dylib')")
# Extra test translation unit must precede -o rather than be an output argument.
source=source.replace("'-o',str(ROOT/'Tests/item_pickup_test_helpers.cpp'),str(WORK/'libWorldLootRuntime.dylib')","str(ROOT/'Tests/item_pickup_test_helpers.cpp'),'-o',str(WORK/'libWorldLootRuntime.dylib')")
source=source.replace("lib=C.CDLL(str(ROOT/'Tests/item_pickup_test_helpers.cpp'),str(WORK/'libWorldLootRuntime.dylib'))","lib=C.CDLL(str(WORK/'libWorldLootRuntime.dylib'))")
source=source.replace('u.hook_add(UC_HOOK_CODE,hook)','oldHook=u.hook_add(UC_HOOK_CODE,hook)')
exec(compile(source,str(Path(__file__).with_name('world_loot_helpers.py')),'exec'),globals())
# Frozen player ABI definitions, without executing its unrelated test/build code.
playerSource=Path(__file__).with_name('player_damage_helpers.py').read_text() if Path(__file__).with_name('player_damage_helpers.py').exists() else Path(__file__).with_name('player_damage_original.py').read_text()
a=playerSource.index('class Physics(');b=playerSource.index('class Rect(',a)
exec(playerSource[a:b],globals());Player=State
ITEM,LOG=OWNER,INV
PLAYER,PLAYER_LOGIC,PLAYER_PRIVATE,MANAGER,PLANE,TILEMAN,AUX,GLITTER,IMAGE=[BASE+0x70000+n*0x1000 for n in range(9)]
class ItemContext(C.Structure):_fields_=[('scene',Host),('loot',C.POINTER(Globals)),('player',C.POINTER(Player))]+[(n,C.c_uint32)for n in('playerToken','playerPrimaryToken','playerPrivateToken','managerToken','animationDelta','stageDelta','tick','audioEnabled','masterVolume','lastSoundTick','lastSoundToken','auxiliaryManagerToken','auxiliarySceneToken','composeCreation','fault')]
class ItemCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*8),('name',C.c_char_p)]
ItemDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(ItemContext),C.POINTER(ItemCall),C.c_void_p)
lib.claw_item_pickup_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(ItemContext),ItemDependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_item_pickup_award.argtypes=[C.c_uint32,C.POINTER(ItemContext),ItemDependency,C.c_void_p]
player=Player();itemContext=ItemContext(scene,C.pointer(g),C.pointer(player),PLAYER,PLAYER_LOGIC,PLAYER_PRIVATE,MANAGER,16,17,100,1,100,0,0,AUX,SC,0,0)
basePrepare=prepare;baseEffects=effects;baseHook=hook;baseSnapshot=snapshot
createdResult=GLITTER;auxiliaryResult=1;mutate=0;item_calls=item_events=0
literals={0x5240d8:b'GAME_CYCLE100',0x52a198:b'GAME_POWERUP',0x522950:b'PowerupGlitter',0x5235d0:b'GAME_DYNAMITE',0x5279b8:b'GAME_TREASURE_COINS'}

def synchronize_player(native):
 player.actor[:]=get(PLAYER,128,native);player.privateWords[:]=get(PLAYER_PRIVATE,78,native);player.logicState=get(PLAYER_LOGIC+0x1c,1,native)[0]

def snapshot(native):
 words=(itemContext.animationDelta,itemContext.stageDelta,itemContext.tick,itemContext.audioEnabled,itemContext.masterVolume,itemContext.lastSoundTick,itemContext.lastSoundToken,itemContext.auxiliaryManagerToken,itemContext.auxiliarySceneToken)if native else tuple(m.read_words(a,1)[0]for a in(0x5430c4,0x53720c,0x537210,0x532c0c,0x532c10,0x534ec0,0x534ec4,0x534874,0x5349dc))
 return (tuple(g.words)if native else tuple(m.read_words(GLOBALS_BASE,341)),g.itemCount if native else m.read_words(0x52a190,1)[0],words,bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))

def effects(event,native):
 fn,receiver,args,name=event
 if fn==0x4f6286:return resources.get((2,args[0]),0)
 if fn==0x4c79e0:
  put(receiver+0x190,[0x12345678],native)
  if mutate:put(receiver+0x64,[0],native);put(MANAGER+0x124,[1],native)
 elif fn==0x4c8da0:
  if createdResult:put(createdResult+8,[args[-1],SC],native);put(createdResult+0x4c,args[1:3],native);put(createdResult+0x64,[args[3]],native)
  return createdResult
 elif fn==0x4dba00:return {0x5236fc:2001,0x5240e8:2008,0x5234f4:2004}[args[0]]
 elif fn==0x4f63ec:return BASE+0x79000
 elif fn==0x4cbb60:put(ITEM+0x4c,args[1:3],native);return 0
 elif fn==0x4c8220:put(receiver-0x188+0x190,[args[0]],native)
 elif fn==0x4c82a0:
  if mutate:put(receiver-0x188+0x164,[get(receiver-0x188+0x164,1,native)[0]^0x200],native)
 elif fn==0x4b45f0:
  if mutate:
   if native:itemContext.stageDelta^=0x80000000
   else:m.write_words(0x53720c,[m.read_words(0x53720c,1)[0]^0x80000000])
 elif fn==0x405f80:return auxiliaryResult
 elif fn==0x4719e0:
  if native:g.words[340]=1
  else:m.write_words(0x538418,[1])
 return 0
@ItemDependency
def dependency(ctx,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);native_events.append((event,snapshot(True)));return effects(event,True)

def hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);event=(address,u.reg_read(UC_X86_REG_ECX),(name,),None);original_events.append((event,snapshot(False)));r=effects(event,False);m.write_words(out,[r]);returned(8,int(bool(r)));return
 config={0x4c79e0:(2,8),0x4c82a0:(1,4),0x4c8da0:(6,24),0x4b45f0:(4,16),0x4737c0:(1,0),0x4719e0:(1,0),0x4c7fa0:(1,4),0x4c8060:(1,4),0x4dba00:(1,4),0x4f63ec:(1,0),0x4cbb60:(4,16),0x4c8220:(1,4)}
 if address not in config:return
 n,pop=config[address];event=(address,0 if address in(0x4737c0,0x4719e0,0x4f63ec)else u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,n)),None);original_events.append((event,snapshot(False)));returned(pop,effects(event,False))
u.hook_del(oldHook);u.hook_add(UC_HOOK_CODE,hook)

def prepare(seed=None):
 basePrepare(seed);itemContext.loot=C.pointer(g);itemContext.player=C.pointer(player);itemContext.fault=0
 itemContext.animationDelta=rng.choice([0,16,0xffffffff]);itemContext.stageDelta=rng.choice([0,17,400,0xffffffff]);itemContext.tick=rng.choice([0,0x80000000,0xffffffff,123]);itemContext.audioEnabled=rng.choice([0,1]);itemContext.masterVolume=rng.randrange(101);itemContext.lastSoundTick=rng.choice([0,itemContext.tick]);itemContext.lastSoundToken=0
 g.words[340]=rng.choice([0,1]);g.itemCount=62
 for row in profile['records']:
  n=row['id'];g.words[n]=resources[(2,next(x['literal']for x in profile['operations']if x.get('name')==row['image']and x.get('registry')==2))]if row['image'] else 0
  g.words[66+n]=row['value'];g.words[132+n]=row['mask'];g.words[274+n]=BASE+0x1d000+n*16 if row['sound'] else 0
  if row['sound']:put(g.words[274+n]+0x10,[BASE+0x1e000+n*16],True)
 for row in profile['records']:
  fn={'TreasurePowerup':0x46fd10,'HealthPowerup':0x470d00,'AmmoPowerup':0x471100,'MagicPowerup':0x470f00}.get(row['logic'],0);metadata=BASE+0x1c000+row['id']*32;g.words[208+row['id']]=metadata;put(metadata+0x10,[fn],True)
 put(SC+0x10,[IR],True);put(SC+8,[CT],True);put(SC+0x24,[TILEMAN],True);put(TILEMAN+0x5c,[PLANE],True);put(PLANE+0x84,[rng.getrandbits(32),rng.getrandbits(32)],True);put(MANAGER+0x124,[rng.randrange(2)],True)
 put(ITEM+0x6c,[LOG],True);put(ITEM+0xc,[SC],True);put(LOG+0x1c,[rng.choice([0,5,29,9000,9001,0xffffffff])],True);put(ITEM+0xc8,[rng.choice([0,GLITTER])],True);put(ITEM+0x64,[rng.choice([0,1000,0xffffffff])],True);put(ITEM+0x190,[rng.choice([0,0x10a8000])],True);put(ITEM+0x174,[rng.choice([0,IMAGE])],True);put(IMAGE+0x18,[0xfffffff0,0xffffffe0,16,32],True);put(ITEM+0x170,[g.words[rng.randrange(66)]],True)
 put(PLAYER+0x6c,[PLAYER_LOGIC],True);put(PLAYER_LOGIC+0x14,[PLAYER_PRIVATE],True);put(PLAYER_LOGIC+0x1c,[24],True);put(PLAYER+0x74,[ITEM],True);put(AUX+0xc,[rng.choice([0,SC])],True);put(AUX+0x4c8,[0x12345678],True);synchronize_player(True)

def install(before_heap,before_globals,fields):
 u.mem_write(BASE,before_heap);m.write_words(GLOBALS_BASE,before_globals.words);m.write_words(0x52a190,[before_globals.itemCount]);m.write_words(0x5371fc,[MANAGER]);m.write_words(0x537e88,[PLAYER]);m.write_words(0x534874,[itemContext.auxiliaryManagerToken]);m.write_words(0x5349dc,[itemContext.auxiliarySceneToken]);m.write_words(0,[0x12345678])
 for a,v in zip((0x5430c4,0x53720c,0x537210,0x532c0c,0x532c10,0x534ec0,0x534ec4),fields):m.write_words(a,[v])

def compare(fn,args,label,receiver=0):
 global item_calls,item_events
 before=Globals.from_buffer_copy(bytes(g));bh=bytes(heap);fields=(itemContext.animationDelta,itemContext.stageDelta,itemContext.tick,itemContext.audioEnabled,itemContext.masterVolume,itemContext.lastSoundTick,itemContext.lastSoundToken);result=C.c_uint32();native_events.clear();original_events.clear();itemContext.fault=0
 if fn==0x40e690:support=lib.claw_item_test_goodie(BASE+0x79000,C.byref(itemContext),dependency,None);result.value=1
 elif fn==0x473660:support=lib.claw_item_test_rebind(args[0],args[1],C.byref(itemContext),dependency,None);result.value=1
 elif fn==0x41ce80:support=lib.claw_item_pickup_award(ITEM,C.byref(itemContext),dependency,None);result.value=1
 else:
  packed=(C.c_uint32*len(args))(*args)if args else None;support=lib.claw_item_pickup_entry(fn,receiver,packed,len(args),C.byref(itemContext),dependency,None,C.byref(result))
 assert support and not itemContext.fault,(label,'native scope',itemContext.fault)
 expected,ee=snapshot(True),list(native_events);new_heap=bytes(heap);new_globals=bytes(g);new_ctx=bytes(itemContext)
 install(bh,before,fields)
 try:ret=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*args))
 except Exception:print('fault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 actual=snapshot(False)
 if actual!=expected:
  if actual[:3]!=expected[:3]:print(label,'globals',actual[:3],expected[:3])
  for i,(a,b)in enumerate(zip(actual[3],expected[3])):
   if a!=b:print(label,'raw byte',hex(BASE+i),a,b)
  raise AssertionError((label,'all raw buffers/globals'))
 if fn not in(0x41d6f0,0x41f850,0x41ee60,0x470100):assert ret==result.value,(label,'EAX',ret,result.value)
 if original_events!=ee:
  for i,(a,b)in enumerate(zip(original_events,ee)):
   if a!=b:print(label,'event',i,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[x[0]for x in original_events]);print('native',[x[0]for x in ee]);raise AssertionError((label,'ordered full raw snapshots'))
 C.memmove(C.addressof(heap),new_heap,SIZE);C.memmove(C.addressof(g),new_globals,C.sizeof(g));C.memmove(C.addressof(itemContext),new_ctx,C.sizeof(itemContext));synchronize_player(True);item_calls+=1;item_events+=len(ee)

lib.claw_item_test_goodie.argtypes=[C.c_uint32,C.POINTER(ItemContext),ItemDependency,C.c_void_p]
lib.claw_item_test_rebind.argtypes=[C.c_uint32,C.c_int32,C.POINTER(ItemContext),ItemDependency,C.c_void_p]
def install_registry():
 nameData,functionData=BASE+0x7b000,BASE+0x7d000
 names=[0x52e1c4]*1009;functions=[0]*1009
 for id,token,name,fn in((2001,BASE+0x7e000,b'LS_FALLING',0x40f010),(2008,BASE+0x7e040,b'LS_BOUNCE',0x40f200),(2004,BASE+0x7e080,b'LS_DEAD',0x40f400)):
  names[id-1000]=token;functions[id-1000]=fn
  put(token-12,[1,len(name),len(name)],True);C.memmove(C.addressof(heap)+token-BASE,name+b'\0',len(name)+1)
 put(nameData,names,True);put(functionData,functions,True)
 m.write_words(0x537698+8,[1000,2008,nameData,0,4,0,0,0]);m.write_words(0x5349e0+8,[1000,2008,functionData,0,4,0,0,0]);m.write_words(0x513e10,[0xffc00000,0xc1dfffff,0xff800000,0x41dfffff,0x9999999a,0x3fb99999,0x4db6a0,0x4dbb50,0x4dbc80,0x4dbd00,0x4dc230,0,24,0,0xd2f1a9fc,0x3f50624d,0,0xbfe00000,0,0,0,0xc0000000,0x4dda50,0x4ddb40])
 m.write_words(0x50b68c,[0x484d90,0x4c9e30,0x40ebe0,0x4063b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0,0x40f2a0])
 put(SC+0x28,[SR],True);put(SC+0x2c,[LR],True)
