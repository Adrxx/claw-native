"""Disjoint HumanCombat oracle harness; frozen fixture definitions are read-only."""
from pathlib import Path
source=Path(__file__).with_name('human_enemy_helpers.py').read_text()
source=source.replace("scratch=ROOT/'work/human-enemy-agent'","scratch=ROOT/'work/human-combat-agent'")
source=source.replace("'HumanEnemy.cpp','OfficerLogic.cpp'","'HumanCombat.cpp','SceneActorRuntime.cpp','GameTiming.cpp','HumanEnemy.cpp','OfficerLogic.cpp'")
source=source.replace('libHumanEnemy.dylib','libHumanCombat.dylib')
source=source.replace('u.hook_add(UC_HOOK_CODE,host)','inheritedHook=u.hook_add(UC_HOOK_CODE,host)')
exec(compile(source,str(Path(__file__).with_name('human_enemy_helpers.py')),'exec'),globals())
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.POINTER(C.c_uint32),C.c_void_p,C.c_uint32,C.c_uint32)
Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32)
SceneDependency=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall)
Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class SceneHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',SceneDependency),('readClock',Clock)]
class CombatContext(C.Structure):_fields_=[('human',C.POINTER(HumanContext)),('actorContainerToken',C.c_uint32),('scene',SceneHost),('fault',C.c_uint32)]
lib.claw_human_combat_entry.argtypes=[C.POINTER(Enemy),C.POINTER(CombatContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
# Execute the actual original entire401000 once with its original CString bodies.
# Only allocation, metadata, strlen/Interlocked services are adapted.
registryNamespace={'__file__':str(ROOT/'Tests/compare_logic_state_registry.py'),'__name__':'combat_registry_fixture'}
registrySource=(ROOT/'Tests/compare_logic_state_registry.py').read_text().split('def check(kind,label,*args):')[0]
registrySource=registrySource.replace("WORK=ROOT/'work/state-registry-agent'","WORK=ROOT/'work/human-combat-agent'")
exec(compile(registrySource,'combat_registry_fixture','exec'),registryNamespace)
q=registryNamespace
q['install'](q['state'],bytes(q['heap']))
for f,k,t,a in q['specs']:q['m'].call(f,0,b'')
q['m'].call(0x401000,0,struct.pack('<I',q['SC']))
registryHeap=bytes(q['u'].mem_read(q['HEAP'],q['SIZE']));registryTables={t:q['m'].read_words(t,12)for t in q['tokens']}
lo,hi,data=q['m'].read_words(0x537698+8,3)
profile=[]
for id in range(2000,hi+1):
 token=q['m'].read_words(data+(id-lo)*4,1)[0];name=q['text'](token)
 profile.append((id,token,name))
names=[x[2]for x in profile];ids={name:id for id,token,name in profile}
states=(State*len(profile))(*[State(id,0,token,name)for id,token,name in profile])
u.mem_map(q['HEAP'],q['SIZE']);u.mem_write(q['HEAP'],registryHeap)
originalCombatInstall=install
originalCombatFresh=fresh
oldSnapshot=snapshot
oldSerialized=serialized
oldWrite=write
oldEffects=effects
oldHost=host
mutate=0
actorContainer=0x103a000
createResult=EF

def fresh():
 s,c=originalCombatFresh();s.primary[3]=SC;c.generic.states=states;c.generic.stateCount=len(states);s.primary[7]=rng.choice([ids[b'LS_IDLE'],ids[b'LS_HITLOW'],ids[b'LS_HITHIGH'],ids[b'LS_DEAD']]);c.privateTail[(0x44c-0x420)//4]=rng.choice([0,EF]);c.sharedStates.attackerActor[:]=c.otherActor
 c.sharedStates.attackerActor[0x138//4]=rng.choice([0x80000000,0]);c.sharedStates.attackerActor[0x13c//4]=rng.getrandbits(32);c.sharedStates.attackerActor[0x144//4]=rng.getrandbits(32)
 c.sharedStates.audioEnabled=rng.choice([0,1]);c.sharedStates.playerPrivate[5]=rng.choice([0,1]);c.generic.tick=rng.choice([0,0x80000000,0xffffffff,27]);c.generic.levelWord=rng.choice([0,0x26b8,0x26b9,0x26ba,0x26bb]);c.sharedStates.audioPosition=rng.getrandbits(32)
 for o in(0x390,0x394,0x398,0x39c,0x414,0x418,0x41c):s.enemy[o//4]=rng.choice([0,*[x.token for x in resourceViews]])
 return s,c

def write(s):
 oldWrite(s);m.write_words(OTHER,current.sharedStates.attackerActor);m.write_words(0x1039000,current.sharedStates.playerPrivate);m.write_words(0x532c0c,[current.sharedStates.audioEnabled]);m.write_words(0x532c10,[current.sharedStates.audioPosition]);m.write_words(0x537210,[current.generic.tick]);m.write_words(0x534eac,[current.generic.levelWord])

def snapshot():
 s=oldSnapshot();current.sharedStates.attackerActor[:]=m.read_words(OTHER,128);current.sharedStates.playerPrivate[:]=m.read_words(0x1039000,78);current.sharedStates.audioEnabled=m.read_words(0x532c0c,1)[0];current.sharedStates.audioPosition=m.read_words(0x532c10,1)[0];current.generic.tick=m.read_words(0x537210,1)[0];current.generic.levelWord=m.read_words(0x534eac,1)[0];return s

def serialized(s):
 return bytes(s)+bytes(current.privateTail)+bytes(current.generic.playerActor)+b''.join(bytes(getattr(current,f))for f,a,n in extraBuffers if f!='otherActor')+bytes(current.sharedStates.attackerActor)+bytes(current.sharedStates.playerPrivate)+struct.pack('<4I',current.sharedStates.audioEnabled,current.sharedStates.audioPosition,current.generic.tick,current.generic.levelWord)

def effects(s,event):
 f,receiver,args,name=event
 if f==0x4dba00:return ids[name]
 if f==0x4c8da0:return createResult
 if f==0x4c7970 and receiver==EF:
  current.effectActor[0x170//4]=0x10b0000
 elif f==0x4c79e0:
  current.effectActor[0x190//4]^=0x89;current.effectActor[0x198//4]=args[0]
 if mutate:
  if f==0x4c8220:current.sharedStates.audioEnabled^=1;s.enemy[0x18c//4]=3 if s.enemy[0x18c//4]!=3 else 2;s.actor[0x190//4]^=0x456
  if f==0x4b45f0:current.sharedStates.audioPosition^=0x82;current.sharedStates.audioEnabled^=1
  if f==0x461a00:current.sharedStates.playerPrivate[5]^=1;current.generic.tick^=0x80000000
 return oldEffects(s,event)

def host(uc,address,size,user):
 if address==0x4c7970 and u.reg_read(UC_X86_REG_ECX)==0:return
 if address in(0x4c8da0,0x461a00,0x4c79e0):
  sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);n,pop={0x4c8da0:(6,24),0x461a00:(6,0),0x4c79e0:(2,8)}[address];args=tuple(m.read_words(sp+4,n));name=None
  if address==0x461a00:receiver=0
  if address==0x4c79e0:name=text(args[0]);args=(args[1],)
  event=(address,receiver,args,name);s=snapshot();events.append((event,serialized(s)));result=effects(s,event);write(s);returned(pop,result);return
 oldHost(uc,address,size,user)
# Install a single hook so every service executes exactly once.
u.hook_del(inheritedHook)
u.hook_add(UC_HOOK_CODE,host)

def install(s,c):
 originalCombatInstall(s,c)
 for token,words in registryTables.items():m.write_words(token,words)
 u.mem_write(q['HEAP'],registryHeap);m.write_words(SC+8,[actorContainer]);write(s)

def compare(s,c,entry,label,arg=OTHER):
 global current,native,random_index,calls,event_count
 before,bc=bytes(s),bytes(c);current=c;native=True;events.clear();random_index=0
 hv=human_view(c);cx=CombatContext(C.pointer(hv),actorContainer,SceneHost(),0);result=C.c_uint32()
 if entry in(0x44f490,0x44f660):support=lib.claw_human_enemy_entry(C.byref(s),C.byref(hv),entry,0,dependency,None,C.byref(result))
 else:support=lib.claw_human_combat_entry(C.byref(s),C.byref(cx),entry,arg,dependency,None,C.byref(result))
 assert support and not cx.fault and not hv.fault,(label,'native scope',cx.fault,hv.fault)
 expected=serialized(s);ee=list(events)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);install(old,oc);native=False;events.clear();random_index=0
 try:ret=m.call(entry,E,struct.pack('<I',arg)if entry not in(0x44f3c0,0x44f510,0x44f490,0x44f660)else b'')
 except Exception:
  print('fault',label,hex(u.reg_read(UC_X86_REG_EIP)),m.read_words(u.reg_read(UC_X86_REG_ESP),8));raise
 actual=serialized(snapshot())
 if actual!=expected:
  for index,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',index,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 if entry in(0x44f3c0,0x44f510):assert ret==result.value
 if events!=ee:
  for index,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',index,a[0],b[0],'snap',a[1]==b[1]);break
  print('original',[x[0]for x in events]);print('native',[x[0]for x in ee]);raise AssertionError((label,'events'))
 calls+=1;event_count+=len(events);current=c;return s,c

def compare_null_create(element):
 global current,native,random_index,calls,event_count,createResult
 from unicorn import UcError
 s,c=fresh();c.generic.levelWord=element;c.privateTail[(0x44c-0x420)//4]=0;s.primary[7]=ids[b'LS_IDLE']
 before,bc=bytes(s),bytes(c);createResult=0;current=c;native=True;events.clear();random_index=0
 hv=human_view(c);cx=CombatContext(C.pointer(hv),actorContainer,SceneHost(),0);result=C.c_uint32()
 assert lib.claw_human_combat_entry(C.byref(s),C.byref(cx),0x44d5a0,OTHER,dependency,None,C.byref(result)) and cx.fault==2
 expected,ee=serialized(s),list(events)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);install(old,oc);native=False;events.clear();random_index=0
 cpu=u.context_save();u.mem_unmap(0,4096)
 try:
  m.call(0x44d5a0,E,struct.pack('<I',OTHER));raise AssertionError('original null creator unexpectedly returned')
 except UcError:
  assert u.reg_read(UC_X86_REG_EIP)==0x4c797c
  assert serialized(snapshot())==expected and events==ee
 finally:
  u.context_restore(cpu);u.mem_map(0,4096);createResult=EF
 calls+=1;event_count+=len(events)
