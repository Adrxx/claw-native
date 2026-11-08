"""Whole ordinary Bullet instructions, using frozen raw fixture definitions."""
from pathlib import Path
source=Path(__file__).with_name('soldier_helpers.py').read_text().split('def compare_failure(kind):')[0]
source=source.replace('work/soldier-agent','work/bullet-agent')
source=source.replace("'CommonEnemyEntries.cpp','SoldierLogic.cpp'","'BulletLogic.cpp','PlayerDamage.cpp','CommonEnemyEntries.cpp','SoldierLogic.cpp'")
source=source.replace('for table in(0x537698,0x53c328,0x537878,0x537638)','for table in(0x538428,0x537698,0x53c328,0x537878,0x537638)')
source=source.replace('u.hook_del(baseHook);u.hook_add(UC_HOOK_CODE,host)','u.hook_del(baseHook);soldierHook=u.hook_add(UC_HOOK_CODE,host)')
exec(compile(source,str(Path(__file__).with_name('soldier_helpers.py')),'exec'),globals())
class BulletContext(C.Structure):_fields_=[('generic',C.POINTER(GenericContext)),('projectileStates',C.POINTER(State)),('projectileStateCount',C.c_size_t),('scene',SceneHost),('imageRegistryToken',C.c_uint32),('imageRootToken',C.c_uint32),('imageRootHeader',C.c_uint32*28),('imageFrames',C.POINTER(C.c_uint32)),('imageFrameOrigin',C.c_int32),('imageFrameCount',C.c_size_t),('imageLeafToken',C.c_uint32),('imageLeafHeader',C.c_uint32*10),('fault',C.c_uint32)]
lib.claw_bullet_context_defaults.argtypes=[C.POINTER(BulletContext)]
lib.claw_bullet_entry.argtypes=[C.POINTER(Enemy),C.POINTER(BulletContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_bullet_entry.restype=C.c_uint32
assert [e[0]for e in q['original_events']if e[0][3]==b'Bullet']==[(q['META'],q['REG'],(0x40fec0,0x522e0c,0),b'Bullet')]
projectileStates=class_view(0x538428);assert[(x.state,x.function)for x in projectileStates if x.function]==[(ids[b'LS_FALLING'],0x4742f0)]
ROOT_IMAGE,LEAF_IMAGE,FRAME_DATA,IMAGE_REGISTRY=0x10d0000,0x10d1000,0x10d2000,0x10d3000
frames=(C.c_uint32*16)(*[LEAF_IMAGE]*16)
rootHeader=(C.c_uint32*28)();leafHeader=(C.c_uint32*10)();currentBullet=None
oldFresh=fresh;oldWrite=write;oldSnapshot=snapshot;oldSerialized=serialized;oldEffects=effects;oldHost=host;oldInstall=install;oldCompare=compare
jointSoldier=False;ownerState=None
def view(c):
 x=BulletContext();x.generic=C.pointer(c.generic);x.projectileStates=projectileStates;x.projectileStateCount=len(projectileStates)
 x.imageRegistryToken=IMAGE_REGISTRY;x.imageRootToken=ROOT_IMAGE;x.imageRootHeader[:]=rootHeader
 x.imageFrames=frames;x.imageFrameOrigin=-4;x.imageFrameCount=16;x.imageLeafToken=LEAF_IMAGE;x.imageLeafHeader[:]=leafHeader
 return x
def fresh():
 global currentBullet
 s,c=oldFresh();currentBullet=view(c);lib.claw_bullet_context_defaults(C.byref(currentBullet))
 s.enemy[0]=0x50b714;s.primary[7]=ids[b'LS_FALLING'];s.enemy[7]=s.primary[7];s.actor[2]=0x40000;s.actor[0xcc//4]=8
 s.actor[0x170//4]=rng.choice([0,ROOT_IMAGE]);s.actor[0x174//4]=rng.choice([0,LEAF_IMAGE]);s.actor[0x80//4]=0;s.enemy[0x148//4]=rng.choice([0,0x10a0000]);s.enemy[0x120//4]=rng.getrandbits(32)
 for n in range(28):rootHeader[n]=rng.getrandbits(32)
 rootHeader[5]=FRAME_DATA+16;rootHeader[25]=rng.choice([-2,-1,0,1,3])&0xffffffff;rootHeader[26]=rng.choice([-3,-1,0,2,3])&0xffffffff
 for n in range(10):leafHeader[n]=rng.getrandbits(32)
 leafHeader[6:10]=[6,5,0,0]
 currentBullet.imageRootHeader[:]=rootHeader;currentBullet.imageLeafHeader[:]=leafHeader
 return s,c
def write(s):
 oldWrite(s)
 if currentBullet is not None:m.write_words(ROOT_IMAGE,currentBullet.imageRootHeader);m.write_words(LEAF_IMAGE,currentBullet.imageLeafHeader)
 m.write_words(FRAME_DATA,frames);m.write_words(SC+0x10,[IMAGE_REGISTRY-0x10])
def snapshot():
 s=oldSnapshot()
 if currentBullet is not None:currentBullet.imageRootHeader[:]=m.read_words(ROOT_IMAGE,28);currentBullet.imageLeafHeader[:]=m.read_words(LEAF_IMAGE,10)
 return s
def serialized(s):return oldSerialized(s)+(bytes(currentBullet.imageRootHeader)+bytes(currentBullet.imageLeafHeader)+bytes(frames)if currentBullet is not None else b'')
def effects(s,event):
 global mutate
 fn,receiver,args,name=event
 if fn==0x4cbb60 and args[0]==EF:
  if realMotion:
   actor=Actor();fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
   for n,o in fields.items():setattr(actor,n,current.effectActor[o//4])
   actor.token=EF;actor.moveRect=Rect(*current.effectActor[0x118//4:0x128//4]);actor.hitRect=Rect(*current.effectActor[0x128//4:0x138//4]);value=lib.claw_collision_move(C.byref(world),C.byref(actor),*args[1:])
   for n,o in fields.items():current.effectActor[o//4]=getattr(actor,n)
  else:current.effectActor[0x4c//4:0x54//4]=args[1:3];value=0
  if native:s.actor[:]=current.effectActor
  return value
 if fn==0x4f63ec and jointSoldier and args==(0x150,):return EFE
 if fn==0x4c8da0 and jointSoldier:
  saved=mutate;mutate=0
  try:value=oldEffects(s,event)
  finally:mutate=saved
  if value:
   current.effectActor[2]=args[5];current.effectActor[3]=SC;current.effectActor[0x80//4]=0;current.effectActor[0xdc//4]=current.effectActor[0xe0//4]=10
   current.effectActor[0x164//4]=current.effectActor[0xfc//4]=0;current.effectActor[0x148//4]=current.effectActor[0x14c//4]=0;current.effectActor[0x170//4]=current.effectActor[0x174//4]=0
   current.effectPrimary[7]=0;current.effectPrimary[0x2c//4:0x3c//4]=[0,0,0,0]
  return value
 if fn==0x4f6286 and name in(b'GAME_BULLETS',b'LEVEL_MUSKETBALL'):
  if mutate:currentBullet.imageRootHeader[25]=1;currentBullet.imageRootHeader[26]=3;currentBullet.imageLeafHeader[6]^=1
  return ROOT_IMAGE if resource_mode==1 or(resource_mode==2 and name==b'GAME_BULLETS')else 0
 if fn==0x4c82a0 and mutate:s.enemy[0x120//4]^=0x10000
 saved=mutate;mutate=0
 try:return oldEffects(s,event)
 finally:mutate=saved
def host(uc,address,size,user):
 if address==0x40fec0:return
 if address==0x4c7970 and(not jointSoldier or u.reg_read(UC_X86_REG_ECX)==EF):return
 oldHost(uc,address,size,user)
u.hook_del(soldierHook);u.hook_add(UC_HOOK_CODE,host)
def install(s,c):
 oldInstall(s,c);write(s)
 if realMotion:m.write_words(0x1040000,list(world.cells[:(world.width>>world.shiftX)*(world.height>>world.shiftY)]))
def compare(s,c,fn,label,arg=0):
 global current,native,currentBullet,random_index,calls,event_count
 before,bc=bytes(s),bytes(c);current=c;currentBullet=view(c);native=True;events.clear();random_index=0;result=C.c_uint32()
 initialCx=bytes(currentBullet);support=lib.claw_bullet_entry(C.byref(s),C.byref(currentBullet),fn,arg,dependency,None,C.byref(result));assert support and not currentBullet.fault,(label,'native scope',currentBullet.fault)
 expected,ee=serialized(s),list(events);newCx=bytes(currentBullet)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);currentBullet=BulletContext.from_buffer_copy(initialCx);currentBullet.generic=C.pointer(oc.generic);install(old,oc);native=False;events.clear();random_index=0
 args=struct.pack('<I',A)if fn in(0x473c50,0x4107c0,0x40fec0)else struct.pack('<I',arg)if fn in(0x473f40,0x484d90,0x4c7970)else b''
 try:ret=m.call(fn,A if fn==0x4c7970 else E,args)
 except Exception:print('fault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 actual=serialized(snapshot())
 if actual!=expected:
  for n,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',n,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 if fn not in(0x4741f0,0x473f40,0x456030,0x4c7970,0x4dca10,0x4063b0,0x4dc870,0x4bb030,0x4c9e30,0x4c96b0):assert ret==result.value,(label,'EAX',ret,result.value)
 if events!=ee:
  for n,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',n,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[e[0]for e in events]);print('native',[e[0]for e in ee]);raise AssertionError((label,'ordered snapshots'))
 for token,words in registryTables.items():assert m.read_words(token,12)==words,(label,'registry',hex(token))
 assert bytes(u.mem_read(q['HEAP'],q['SIZE']))==registryHeap and m.read_words(0,1)==[0x12345678]
 current=c;currentBullet=BulletContext.from_buffer_copy(newCx);currentBullet.generic=C.pointer(c.generic);rootHeader[:]=currentBullet.imageRootHeader;leafHeader[:]=currentBullet.imageLeafHeader;calls+=1;event_count+=len(ee)
 return s,c

def sync_fx(b):
 current.effectActor[:]=b.actor;current.effectPrimary[:]=b.primary;current.effectPrivate[:]=b.enemy[:92]
def run_fx(fn,arg=0):
 global currentBullet
 b=Enemy();b.actor[:]=current.effectActor;b.primary[:]=current.effectPrimary;b.enemy[:92]=current.effectPrivate
 g=GenericContext.from_buffer_copy(bytes(current.generic));g.actorToken,g.primaryToken,g.enemyToken=EF,EFL,EFE;cx=view(current);cx.generic=C.pointer(g);currentBullet=cx;lib.claw_bullet_context_defaults(C.byref(cx));result=C.c_uint32()
 @Dependency
 def fx_dependency(ptr,gptr,event,user):
  event=event.contents;sync_fx(ptr.contents);entry=(event.function,event.receiver,tuple(event.arguments[:event.argumentCount]),event.name)
  events.append((entry,serialized(ownerState)));value=effects(ptr.contents,entry);sync_fx(ptr.contents);return value
 status=lib.claw_bullet_entry(C.byref(b),C.byref(cx),fn,arg,fx_dependency,None,C.byref(result));assert status and not cx.fault,('fx scope',hex(fn),cx.fault);sync_fx(b);return result.value
@Dependency
def soldier_dependency(ptr,gptr,event,user):
 global ownerState
 ownerState=ptr.contents;e=event.contents
 if e.function==0x40fec0:return run_fx(0x40fec0)
 if e.function==0x4c7970 and e.receiver==EF and e.name==b'LEVEL_MUSKETBALL':return run_fx(0x4c7970,0x52c4a0)
 event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);events.append((event,serialized(ptr.contents)));return effects(ptr.contents,event)
def compare_soldier_spawn(s,c,label):
 global current,native,currentBullet,random_index,calls,event_count,ownerState,jointSoldier
 jointSoldier=True;ownerState=s;before,bc=bytes(s),bytes(c);current=c;currentBullet=view(c);initialCx=bytes(currentBullet);native=True;events.clear();random_index=0
 hv,combat,aux,cx=views(c);result=C.c_uint32();assert lib.claw_soldier_entry(C.byref(s),C.byref(cx),0x48ba00,0,soldier_dependency,None,C.byref(result))and not cx.fault
 expected,ee=serialized(s),list(events);newCx=bytes(currentBullet)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);currentBullet=BulletContext.from_buffer_copy(initialCx);currentBullet.generic=C.pointer(oc.generic);install(old,oc);native=False;events.clear();random_index=0
 m.call(0x48ba00,E);actual=serialized(snapshot())
 if actual!=expected:
  for n,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',n,hex(a),hex(b))
  raise AssertionError((label,'whole Soldier→Bullet buffers'))
 if events!=ee:
  for n,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',n,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[e[0]for e in events]);print('native',[e[0]for e in ee]);raise AssertionError((label,'whole Soldier→Bullet events'))
 for token,words in registryTables.items():assert m.read_words(token,12)==words,(label,'registry',hex(token))
 assert bytes(u.mem_read(q['HEAP'],q['SIZE']))==registryHeap,(label,'registry heap')
 current=c;currentBullet=BulletContext.from_buffer_copy(newCx);rootHeader[:]=currentBullet.imageRootHeader;leafHeader[:]=currentBullet.imageLeafHeader;calls+=1;event_count+=len(ee);jointSoldier=False;return s,c

def compare_fx(s,c,fn,label,arg=0):
 global current,native,currentBullet,random_index,calls,event_count,ownerState,jointSoldier
 jointSoldier=True;ownerState=s;before,bc=bytes(s),bytes(c);current=c;currentBullet=view(c);initialCx=bytes(currentBullet);native=True;events.clear();random_index=0;queryReturns.clear()
 run_fx(fn,arg);expected,ee=serialized(s),list(events);newCx=bytes(currentBullet)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);currentBullet=BulletContext.from_buffer_copy(initialCx);currentBullet.generic=C.pointer(oc.generic);install(old,oc);native=False;events.clear();random_index=0;queryReturns.clear()
 args=struct.pack('<I',EF)if fn==0x40fec0 else struct.pack('<I',arg)if fn==0x484d90 else b''
 m.call(fn,EFE,args);actual=serialized(snapshot())
 if actual!=expected:
  for n,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',n,hex(a),hex(b))
  raise AssertionError((label,'whole FX buffers'))
 if events!=ee:
  for n,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',n,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[e[0]for e in events]);print('native',[e[0]for e in ee]);raise AssertionError((label,'whole FX events'))
 for token,words in registryTables.items():assert m.read_words(token,12)==words,(label,'registry',hex(token))
 assert bytes(u.mem_read(q['HEAP'],q['SIZE']))==registryHeap,(label,'registry heap')
 current=c;currentBullet=BulletContext.from_buffer_copy(newCx);rootHeader[:]=currentBullet.imageRootHeader;leafHeader[:]=currentBullet.imageLeafHeader;calls+=1;event_count+=len(ee);jointSoldier=False;return s,c

def compare_allocation_failure():
 global current,native,currentBullet,random_index,allocationResult,policy,mutate,jointSoldier
 from unicorn import UcError
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_CS,UC_X86_REG_FS
 policy=mutate=0;jointSoldier=False;s,c=fresh();s.primary[7]=0;allocationResult=0
 before,bc=bytes(s),bytes(c);current=c;currentBullet=view(c);initialCx=bytes(currentBullet);native=True;events.clear();random_index=0;result=C.c_uint32()
 assert not lib.claw_bullet_entry(C.byref(s),C.byref(currentBullet),0x40fec0,0,dependency,None,C.byref(result));assert currentBullet.fault==2 and s.primary[7]==1000
 expected,ee=serialized(s),list(events);old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);currentBullet=BulletContext.from_buffer_copy(initialCx);currentBullet.generic=C.pointer(oc.generic);install(old,oc);native=False;events.clear();random_index=0
 cpu=u.context_save();u.mem_unmap(0,4096);teb,gdt=0x10ed000,0x10ee000
 for selector,base,access in((8,0,0x9b),(16,0,0x93),(24,teb,0x93)):u.mem_write(gdt+selector,struct.pack('<HHBBBB',0xffff,base&0xffff,(base>>16)&255,access,0xcf,(base>>24)&255))
 u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for register,selector in((UC_X86_REG_SS,16),(UC_X86_REG_DS,16),(UC_X86_REG_ES,16),(UC_X86_REG_CS,8),(UC_X86_REG_FS,24)):u.reg_write(register,selector)
 m.write_words(teb,[0xdeadbeef])
 try:
  m.call(0x40fec0,E,struct.pack('<I',A));raise AssertionError('zero allocation unexpectedly returned')
 except UcError:
  assert u.reg_read(UC_X86_REG_EIP)==0x40ff1e;assert serialized(snapshot())==expected and events==ee,('allocation failure prefix')
 finally:u.context_restore(cpu);u.mem_map(0,4096);allocationResult=E
 return len(ee)
