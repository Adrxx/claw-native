"""Private Soldier whole-instruction oracle with frozen fixture shapes."""
from pathlib import Path
source=Path(__file__).with_name('human_enemy_helpers.py').read_text()
source=source.replace("scratch=ROOT/'work/human-enemy-agent'","scratch=ROOT/'work/soldier-agent'")
source=source.replace("'HumanEnemy.cpp','OfficerLogic.cpp'","'CommonEnemyEntries.cpp','SoldierLogic.cpp','HumanCombat.cpp','EnemyMotionAux.cpp','SceneActorRuntime.cpp','GameTiming.cpp','HumanEnemy.cpp','OfficerLogic.cpp'")
source=source.replace('libHumanEnemy.dylib','libSoldierLogic.dylib')
source=source.replace("('privateTail',C.c_uint32*20)","('privateTail',C.c_uint32*24)")
source=source.replace('m.read_words(E+0x420,20)','m.read_words(E+0x420,24)').replace('range(20)','range(24)')
source=source.replace('lib.claw_officer_context_defaults(C.byref(c))','lib.claw_generic_enemy_context_defaults(C.byref(c.generic));c.damageScale=c.healthScale=c.rangeScale=1')
source=source.replace('u.hook_add(UC_HOOK_CODE,host)','baseHook=u.hook_add(UC_HOOK_CODE,host)')
exec(compile(source,str(Path(__file__).with_name('human_enemy_helpers.py')),'exec'),globals())
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.POINTER(C.c_uint32),C.c_void_p,C.c_uint32,C.c_uint32)
Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32)
SceneDependency=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall)
Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class SceneHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',SceneDependency),('readClock',Clock)]
class CombatContext(C.Structure):_fields_=[('human',C.POINTER(HumanContext)),('actorContainerToken',C.c_uint32),('scene',SceneHost),('fault',C.c_uint32)]
class AuxContext(C.Structure):_fields_=[('human',C.POINTER(HumanContext)),('world',C.POINTER(World)),('strongThrow',C.c_uint32),('fault',C.c_uint32)]
class SoldierContext(C.Structure):_fields_=[('human',C.POINTER(HumanContext)),('combat',C.POINTER(CombatContext)),('motion',C.POINTER(AuxContext)),('scene',SceneHost),('soldierStates',C.POINTER(State)),('soldierStateCount',C.c_size_t),('difficulty',C.c_uint32),('actorContainerToken',C.c_uint32),('bulletToken',C.c_uint32)]+[(n,C.POINTER(C.c_uint32))for n in('bulletActor','bulletPrimary','bulletPrivate')]+[('fault',C.c_uint32)]
lib.claw_soldier_context_defaults.argtypes=[C.POINTER(SoldierContext)]
lib.claw_soldier_entry.argtypes=[C.POINTER(Enemy),C.POINTER(SoldierContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_soldier_entry.restype=C.c_uint32
lib.claw_common_enemy_entry.argtypes=[C.POINTER(Enemy),C.POINTER(HumanContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]

# Execute the original entire401000, retaining copied CString tokens and raw
# Human/common/Soldier class arrays. Allocation/metadata/OS services are adapted.
registryNamespace={'__file__':str(ROOT/'Tests/compare_logic_state_registry.py'),'__name__':'soldier_registry_fixture'}
registrySource=(ROOT/'Tests/compare_logic_state_registry.py').read_text().split('def check(kind,label,*args):')[0]
registrySource=registrySource.replace("WORK=ROOT/'work/state-registry-agent'","WORK=ROOT/'work/soldier-agent'")
exec(compile(registrySource,'soldier_registry_fixture','exec'),registryNamespace)
q=registryNamespace;q['install'](q['state'],bytes(q['heap']))
for fn,kind,token,args in q['specs']:q['m'].call(fn,0,b'')
q['m'].call(0x401000,0,struct.pack('<I',q['SC']))
for table in(0x537698,0x53c328,0x537878,0x537638):q['m'].call(0x441030,table,struct.pack('<I',2000))
registryHeap=bytes(q['u'].mem_read(q['HEAP'],q['SIZE']));registryTables={t:q['m'].read_words(t,12)for t in q['tokens']}
lo,hi,data=q['m'].read_words(0x537698+8,3)
profile=[]
for id in [1000,*range(2000,hi+1)]:
 token=q['m'].read_words(data+(id-lo)*4,1)[0];profile.append((id,token,q['text'](token)))
names=[name for id,token,name in profile];ids={name:id for id,token,name in profile if name}
def class_view(table):
 low,high,p=q['m'].read_words(table+8,3)
 return (State*len(profile))(*[State(id,q['m'].read_words(p+(id-low)*4,1)[0]if low<=id<=high else 0,token,name)for id,token,name in profile])
states=class_view(0x537638);humanStates=class_view(0x537878);soldierStates=class_view(0x53c328)
assert {(x.state,x.function)for x in soldierStates if x.function}=={(ids[b'LS_IDLE'],0x48b730),(ids[b'LS_HOME'],0x48b4b0),(ids[b'LS_FIRING'],0x48ba00)}
u.mem_map(q['HEAP'],q['SIZE']);u.mem_write(q['HEAP'],registryHeap)
baseFresh=fresh;baseInstall=install;baseWrite=write;baseSnapshot=snapshot;baseSerialized=serialized;baseEffects=effects;baseHost=host
actorContainer=0x103a000;bulletCallback=0x40fec0
createResult=EF;allocationResult=E;animationResult=1;mutate=0;bitSetMode=None;strongThrow=0;bitBacking=(C.c_uint32*4)();bitToken=0x103b000
world=install_world();realPoints=False;realGround=False;realQueries=False;realMotion=False;queryReturns=[];finishAnimation=False;soldierView=None
import re
known={int(v,16)for name in('CommonEnemyEntries.cpp','SoldierLogic.cpp','HumanEnemy.cpp','GenericEnemy.cpp','GenericEnemyStates.cpp','EnemyMotionAux.cpp')for v in re.findall(r'case 0x([0-9a-f]+)',(ROOT/'Sources'/name).read_text())}
known|={0x48a980,0x48aa40,0x44d460,0x44d570,0x44d5a0,0x44d700,0x44d730,0x44f3c0,0x44f510}
unsupported=({x.function for table in(states,humanStates,soldierStates)for x in table}|set(m.read_words(0x50f774,43)))-known-{0}
humans={fn:({0x43ee10:2,0x43eee0:3}.get(fn,0),4*{0x43ee10:2,0x43eee0:3}.get(fn,0))for fn in unsupported}
def views(c):
 hv=human_view(c);hv.humanStates=humanStates;hv.humanStateCount=len(humanStates)
 combat=CombatContext(C.pointer(hv),actorContainer,SceneHost(),0)
 aux=AuxContext(C.pointer(hv),C.pointer(world),strongThrow,0)
 cx=SoldierContext(C.pointer(hv),C.pointer(combat),C.pointer(aux),SceneHost(),soldierStates,len(soldierStates),c.difficulty,actorContainer,c.effectToken,c.effectActor,c.effectPrimary,c.effectPrivate,0)
 return hv,combat,aux,cx
def fresh():
 global bitBacking
 s,c=baseFresh();hv,combat,aux,cx=views(c);lib.claw_soldier_context_defaults(C.byref(cx))
 s.enemy[0]=0x50f774;c.generic.states=states;c.generic.stateCount=len(states);c.generic.emptyStringToken=0x52e1c4
 s.primary[7]=ids[b'LS_IDLE'];s.enemy[9]=ids[b'LS_HOME'];s.enemy[7]=s.primary[7]
 s.primary[3]=SC
 s.enemy[0x194//4]=rng.choice([A,OTHER]);s.enemy[0x190//4]=A;s.enemy[0x198//4]=L
 s.actor[0x1a4//4]=0;s.actor[0x19c//4]=0;s.actor[0x190//4]=rng.getrandbits(32)
 c.effectActor[0x6c//4]=EFL;c.effectPrimary[0x18//4]=EFE;c.effectPrimary[0x10//4]=bulletCallback
 c.effectPrivate[0x12c//4]=EF;c.effectPrivate[0x128//4]=EF;c.effectActor[0x40//4]=rng.choice([0,2,8,10])
 c.effectToken=EF;c.difficulty=rng.randrange(3);c.generic.levelWord=rng.choice([0,0x26b7,0x26b8]);c.sharedStates.audioEnabled=0
 for off in(0x3b4,0x410,0x414,0x418,0x41c):s.enemy[off//4]=rng.choice([0,*[r.token for r in resourceViews]])
 for off in range(0x450,0x480,4):c.privateTail[(off-0x420)//4]=rng.getrandbits(32)
 c.privateTail[(0x450-0x420)//4]=rng.choice([0,1]);c.privateTail[(0x45c-0x420)//4]=rng.choice([0,500,0xfffffe0c,0xffffffff,0x80000000])
 c.generic.tick=rng.choice([0,1234,0x7fffffff,0x80000000,0xffffffff]);c.generic.animationDelta=rng.choice([0,16,0xffffffff]);c.generic.forcedRandom=rng.choice([0,1])
 bitBacking[:]=[rng.getrandbits(32)for _ in range(4)];c.generic.bitWords=bitBacking;c.generic.bitWordCount=4
 return s,c
def write(s):
 baseWrite(s);m.write_words(PL,current.generic.platformActor);m.write_words(0x1039000,current.sharedStates.playerPrivate)
 m.write_words(OTHER,current.sharedStates.attackerActor);m.write_words(0x52713c,[current.sharedStates.strikeCounter])
 m.write_words(bitToken,bitBacking);m.write_words(0x537210,[current.generic.tick]);m.write_words(0x5430c4,[current.generic.animationDelta]);m.write_words(0x534eac,[current.generic.levelWord]);m.write_words(0x541334,[current.generic.forcedRandom]);m.write_words(0x532c0c,[current.sharedStates.audioEnabled]);m.write_words(0x532c10,[current.sharedStates.audioPosition]);m.write_words(0x537224,[strongThrow])
def snapshot():
 s=baseSnapshot();current.generic.platformActor[:]=m.read_words(PL,128);current.sharedStates.playerPrivate[:]=m.read_words(0x1039000,78)
 bitBacking[:]=m.read_words(bitToken,4)
 for field,address in(('tick',0x537210),('animationDelta',0x5430c4),('levelWord',0x534eac),('forcedRandom',0x541334)):setattr(current.generic,field,m.read_words(address,1)[0])
 current.sharedStates.audioEnabled=m.read_words(0x532c0c,1)[0];current.sharedStates.audioPosition=m.read_words(0x532c10,1)[0]
 current.sharedStates.attackerActor[:]=m.read_words(OTHER,128);current.sharedStates.strikeCounter=m.read_words(0x52713c,1)[0]
 return s
def serialized(s):
 if native:current.otherActor[:]=current.sharedStates.attackerActor
 return baseSerialized(s)+bytes(current.generic.platformActor)+bytes(current.sharedStates.attackerActor)+bytes(current.sharedStates.playerPrivate)+bytes(bitBacking)+struct.pack('<8I',current.generic.tick,current.generic.animationDelta,current.generic.levelWord,current.generic.forcedRandom,current.sharedStates.audioEnabled,current.sharedStates.audioPosition,strongThrow,current.sharedStates.strikeCounter)
def effects(s,event):
 f,receiver,args,name=event
 if f==0x4dba00:return ids.get(name,0)
 if f==0x4f63ec:return allocationResult
 if f==0x4207f0:return point(*args)
 if f==0x4cda10 and realQueries:
  fault=C.c_uint32();value=lib.claw_collision_horizontal_clear(C.byref(world),*args,C.byref(fault));assert not fault.value;return value
 if f==0x4cbb60 and realMotion:
  actor=Actor();fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
  for name,offset in fields.items():setattr(actor,name,s.actor[offset//4])
  actor.token=A;actor.moveRect=Rect(*s.actor[0x118//4:0x128//4]);actor.hitRect=Rect(*s.actor[0x128//4:0x138//4]);value=lib.claw_collision_move(C.byref(world),C.byref(actor),*args[1:])
  for name,offset in fields.items():s.actor[offset//4]=getattr(actor,name)
  return value
 if f==0x4c8da0:
  if createResult:
   current.effectActor[0x4c//4:0x54//4]=args[1:3];current.effectActor[0x64//4]=args[3];current.effectActor[0x6c//4]=EFL
   current.effectPrimary[0x10//4]=bulletCallback;current.effectPrimary[0x18//4]=EFE
  return createResult
 if f==bulletCallback:
  current.effectPrimary[0x18//4]=EFE;current.effectPrivate[0x128//4]=current.effectPrivate[0x12c//4]=EF
 if f==0x4c82a0:
  returnValue=animationResult
  if finishAnimation:s.actor[0x1a4//4]=1;s.actor[0x19c//4]=0
 else:returnValue=baseEffects(s,event)
 if f==0x4dbd20:s.enemy[0x2fc//4]=32;s.enemy[0x300//4]|=1<<args[0]
 if f==0x4c7970 and receiver==A and bitSetMode is not None:
  s.enemy[0x2fc//4]=bitSetMode;s.enemy[0x300//4]=bitToken if bitSetMode>32 else 0
 if mutate:
  if f==0x4c8220:s.actor[0x190//4]^=0x456;current.generic.playerActor[0xcc//4]=5 if current.generic.playerActor[0xcc//4]!=5 else 1
  if f==0x4cda10:current.generic.playerActor[0x50//4]^=0x77
  if f==0x4c82a0:s.enemy[0x1a0//4]^=1;current.generic.tick^=0x80000000
  if f==bulletCallback:current.privateTail[(0x45c-0x420)//4]^=0xffffffff
 return returnValue
def point(x,y):return lib.claw_world_point_attribute(world.cells,world.rowOffsets,world.width,world.height,world.shiftX,world.shiftY,world.descriptions,world.descriptionCount,x,y,0,0)
lib.claw_world_point_attribute.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_int32,C.c_int32,C.c_uint32,C.c_uint32,C.POINTER(Description),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32]
lib.claw_collision_horizontal_clear.argtypes=[C.POINTER(World),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32)]
lib.claw_collision_move.argtypes=[C.POINTER(World),C.POINTER(Actor),C.c_uint32,C.c_uint32,C.c_uint32]
def host(uc,address,size,user):
 if address==0x4c7970 and not u.reg_read(UC_X86_REG_ECX):return
 if address in(0x43eab0,0x440420):return
 if address in queryReturns:queryReturns.remove(address)
 if(address==0x4cda10 and realQueries)or(address==0x4cbb60 and realMotion):
  sp=u.reg_read(UC_X86_REG_ESP);event=(address,u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,4)),None);s=snapshot();events.append((event,serialized(s)));queryReturns.append(m.read_words(sp,1)[0]);return
 if address==0x4f6439:
  receiver=u.reg_read(UC_X86_REG_ECX);m.write_words(receiver,[current.generic.emptyStringToken]);returned(0,receiver);return
 if address==0x4dbcd0 and u.reg_read(UC_X86_REG_ECX)!=E+0x2f4:return
 if address==0x4207f0:
  if queryReturns:return
  sp=u.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,2));s=snapshot();event=(address,u.reg_read(UC_X86_REG_ECX),args,None);events.append((event,serialized(s)))
  if realPoints:return
  returned(8,point(*args));return
 config={0x4c8da0:(6,24),bulletCallback:(1,0),0x461a00:(6,0),0x4dbd20:(1,4),0x4dbcd0:(0,0)}
 if address in config:
  sp=u.reg_read(UC_X86_REG_ESP);n,pop=config[address];event=(address,0 if address in(bulletCallback,0x461a00)else u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,n)),None);s=snapshot();events.append((event,serialized(s)));ret=effects(s,event);write(s);returned(pop,ret);return
 baseHost(uc,address,size,user)
u.hook_del(baseHook);u.hook_add(UC_HOOK_CODE,host)
def install(s,c):
 baseInstall(s,c)
 for token,words in registryTables.items():m.write_words(token,words)
 u.mem_write(q['HEAP'],registryHeap)
 m.write_words(0x50f774,c.generic.virtualFunctions[:43]);m.write_words(SC+8,[actorContainer]);m.write_words(0x52e1cc,[0x52e1c4]);write(s)
 for r in resourceViews:m.write_words(r.token+0x10,[r.controllerToken])
 if realGround or realPoints:install_world(realGround)
def compare(s,c,entry,label,arg=0,directCommon=False):
 global current,native,random_index,calls,event_count,soldierView,bitBacking
 before,bc,bb=bytes(s),bytes(c),bytes(bitBacking);current=c;native=True;events.clear();random_index=0;queryReturns.clear()
 hv,combat,aux,soldierView=views(c);result=C.c_uint32()
 support=lib.claw_common_enemy_entry(C.byref(s),C.byref(hv),entry,arg,dependency,None,C.byref(result))if directCommon else lib.claw_soldier_entry(C.byref(s),C.byref(soldierView),entry,arg,dependency,None,C.byref(result))
 assert support and not soldierView.fault and not hv.fault and not combat.fault and not aux.fault,(label,'native scope',soldierView.fault,hv.fault,combat.fault,aux.fault)
 expected,ee=serialized(s),list(events);newBB=bytes(bitBacking)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);C.memmove(C.addressof(bitBacking),bb,C.sizeof(bitBacking));install(old,oc);native=False;events.clear();random_index=0
 args=struct.pack('<I',A)if entry in(0x48aa40,0x48a980)else struct.pack('<I',arg)if entry in(0x48b0c0,0x48afd0,0x44d000,0x44e0c0,0x44d460,0x44d570,0x44d5a0,0x44d700,0x44d730,0x44d760,0x404e00,0x43f500)else b''
 try:ret=m.call(entry,E,args)
 except Exception:print('fault',label,hex(u.reg_read(UC_X86_REG_EIP)),m.read_words(u.reg_read(UC_X86_REG_ESP),8));raise
 actual=serialized(snapshot())
 if actual!=expected:
  for i,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',i,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 if entry not in(0x48b0c0,0x48aff0,0x405000,0x404e00,0x404e10,0x4dc830,0x44d000,0x44d3c0,0x44df60,0x44cfd0,0x44d460,0x44d570,0x44d5a0,0x44d700,0x44d730,0x44d760):assert ret==result.value,(label,'EAX',ret,result.value)
 if events!=ee:
  for i,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',i,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[x[0]for x in events]);print('native',[x[0]for x in ee]);raise AssertionError((label,'ordered snapshots'))
 assert m.read_words(0,1)==[0x12345678]
 for token,words in registryTables.items():assert m.read_words(token,12)==words,(label,'registry',hex(token))
 assert bytes(u.mem_read(q['HEAP'],q['SIZE']))==registryHeap,(label,'registry heap')
 C.memmove(C.addressof(bitBacking),newBB,C.sizeof(bitBacking));current=c;calls+=1;event_count+=len(ee);return s,c

def compare_failure(kind):
 global current,native,random_index,allocationResult,createResult,animationResult,policy,mutate
 from unicorn import UcError
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_CS,UC_X86_REG_FS
 policy=mutate=0;s,c=fresh();s.enemy[0x1a0//4]=0;s.primary[7]=0 if kind=='allocation'else ids[b'LS_FIRING'];allocationResult=0 if kind=='allocation'else E;createResult=0 if kind=='creation'else EF;animationResult=1
 before,bc=bytes(s),bytes(c);current=c;native=True;events.clear();random_index=0;hv,combat,aux,cx=views(c);result=C.c_uint32();fn=0x48a980 if kind=='allocation'else 0x48ba00
 status=lib.claw_soldier_entry(C.byref(s),C.byref(cx),fn,0,dependency,None,C.byref(result));assert cx.fault==2 and status==(0 if kind=='allocation'else 1)
 expected,ee=serialized(s),list(events);old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);install(old,oc);native=False;events.clear();random_index=0
 cpu=u.context_save();u.mem_unmap(0,4096);teb,gdt=0x10ed000,0x10ee000
 for selector,base,access in((8,0,0x9b),(16,0,0x93),(24,teb,0x93)):u.mem_write(gdt+selector,struct.pack('<HHBBBB',0xffff,base&0xffff,(base>>16)&255,access,0xcf,(base>>24)&255))
 u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for register,selector in((UC_X86_REG_SS,16),(UC_X86_REG_DS,16),(UC_X86_REG_ES,16),(UC_X86_REG_CS,8),(UC_X86_REG_FS,24)):u.reg_write(register,selector)
 m.write_words(teb,[0xdeadbeef])
 try:
  m.call(fn,E,struct.pack('<I',A)if kind=='allocation'else b'');raise AssertionError('original failed dependency unexpectedly returned')
 except UcError:
  assert u.reg_read(UC_X86_REG_EIP)==(0x48a9de if kind=='allocation'else 0x4c797c)
  assert serialized(snapshot())==expected and events==ee,(kind,'failure prefix')
 finally:u.context_restore(cpu);u.mem_map(0,4096);allocationResult=E;createResult=EF
 return len(ee)
