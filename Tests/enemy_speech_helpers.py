"""Raw speech globals/heap oracle plus immutable whole humanoid fixtures."""
from pathlib import Path
source=Path(__file__).with_name('humanoid_strike_helpers.py').read_text().replace('work/humanoid-strike-agent','work/enemy-speech-agent')
source=source.replace('u.hook_add(UC_HOOK_CODE,host)\n\n# Runtime sequence','speech_old_hook=u.hook_add(UC_HOOK_CODE,host)\n\n# Runtime sequence')
source=source.replace("'HumanoidStrikeRuntime.cpp','ActorAnimationRuntime.cpp'","'EnemySpeechRuntime.cpp','SpeechActor.cpp','AudioEvents.cpp','ActorResourceBindings.cpp','ActorDestruction.cpp','WorldLootRuntime.cpp','HumanoidStrikeRuntime.cpp','ActorAnimationRuntime.cpp'")
exec(compile(source,str(Path(__file__).with_name('humanoid_strike_helpers.py')),'exec'),globals())
class SpeechGlobals(C.Structure):_fields_=[(name,C.c_uint32)for name in('managerToken','playerToken','audioManagerToken','clawBusy','clawActorToken','enemyBusy','enemyActorToken','speakerToken','stageDelta')]
class SpeechContext(C.Structure):_fields_=[('scene',SceneHost),('globals',C.POINTER(SpeechGlobals)),('nameHint',C.c_char_p),('fault',C.c_uint32)]
class SpeechCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p)]
SpeechDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(SpeechContext),C.POINTER(SpeechCall),C.c_void_p)
lib.claw_enemy_speech_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(SpeechContext),SpeechDependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_enemy_speech_entry.restype=C.c_uint32
lib.claw_enemy_speech_create.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(SpeechContext),SpeechDependency,C.c_void_p];lib.claw_enemy_speech_create.restype=C.c_uint32
lib.claw_world_loot_next_random.argtypes=[C.POINTER(C.c_uint32)];lib.claw_world_loot_next_random.restype=C.c_uint32
CL,CLL,EN,ENL,MANAGER,SOUND,POOL,IMAGE=[0x10d0000+i*0x1000 for i in range(8)];FRAMEARRAY=0x10d8000;CLMETA=0x10d9000;ENMETA=0x10da000
GLOBAL_ADDRS=(0x5371fc,0x537e88,0x532c0c,0x53c9a0,0x53c9a4,0x53c9a8,0x53c9ac,0x53c9b0,0x53720c)
globals=SpeechGlobals();speechContext=SpeechContext();playerLogic=(C.c_uint32*93)();containerWords=(C.c_uint32*11)();cursor=0x10f0000;allocIndex=0;failAlloc=0;created=[];speechPhase=False;speechMutation=0;soundFound=True;imageFound=True;metadataFound=True;speech_calls=speech_events=0
realSpeechRNG=False;RNG_TLS=0x10db000
from contextlib import contextmanager
from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_CS,UC_X86_REG_FS
u.mem_map(0x4000000,8192)
@contextmanager
def null_fault_scope():
 global zero_mapped
 cpu=u.context_save();u.mem_unmap(0,4096);zero_mapped=False;teb,gdt=0x4000000,0x4001000
 for selector,base,access in((8,0,0x9b),(16,0,0x93),(24,teb,0x93)):u.mem_write(gdt+selector,struct.pack('<HHBBBB',0xffff,base&0xffff,(base>>16)&255,access,0xcf,(base>>24)&255))
 u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for register,selector in((UC_X86_REG_SS,16),(UC_X86_REG_DS,16),(UC_X86_REG_ES,16),(UC_X86_REG_CS,8),(UC_X86_REG_FS,24)):u.reg_write(register,selector)
 m.write_words(teb,[0xdeadbeef])
 try:yield
 finally:u.context_restore(cpu);u.mem_map(0,4096);zero_mapped=True
speechSnapshots=serialized;humanoidDependency=dependency;humanoidHost=host;humanoidHook=strike_base_hook
# The last hook installed by strike helper is its current host; retain its
# handle explicitly when evaluating the source above.

def speech_snapshot(s):return speechSnapshots(s)+(bytes(globals)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRS))+(bytes(playerLogic)if native else bytes(u.mem_read(0x1038000,372)))+(bytes(containerWords)if native else bytes(u.mem_read(actorContainer,44)))
@RawLookup
def speech_lookup(_,t,n):
 if currentState is not None:
  for token,count,array in((A,128,currentState.actor),(L,93,currentState.primary),(P,128,current.generic.playerActor)):
   if token<=t and t+n*4<=token+count*4:return C.addressof(array)+t-token
 if 0x1038000<=t and t+n*4<=0x1038000+372:return C.addressof(playerLogic)+t-0x1038000
 if actorContainer<=t and t+n*4<=actorContainer+44:return C.addressof(containerWords)+t-actorContainer
 return raw_lookup(None,t,n)

def allocation(n):
 global cursor,allocIndex
 allocIndex+=1
 if failAlloc==allocIndex:return 0
 t=cursor;cursor+=max(0x400,(n+15)&~15);assert cursor<0x10fa000;created.append(t)if n==0x1b4 else None;return t
@Allocate
def speech_allocate(_,n):events.append(((0x4f63ec,0,(n,),None),speech_snapshot(currentState)));return allocation(n)
@Free
def speech_free(_,t):events.append(((0x4f6428,0,(t,),None),speech_snapshot(currentState)))
@SceneDependency
def speech_scene_call(_,e):return speech_effect((e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),{0x5223cc:b'ClawDialogSound',0x5223b8:b'EnemyDialogSound'}.get(e.arguments[0])),True,log=True)
speechHost=SceneHost(None,C.cast(speech_lookup,Lookup),speech_allocate,speech_free,speech_scene_call,Clock())

def set_global(field,value,native_side):
 if native_side:setattr(globals,field,value)
 else:m.write_words(GLOBAL_ADDRS[[name for name,_ in SpeechGlobals._fields_].index(field)],[value])
def global_value(field,native_side):return getattr(globals,field)if native_side else m.read_words(GLOBAL_ADDRS[[name for name,_ in SpeechGlobals._fields_].index(field)],1)[0]
def speech_effect(event,native_side,log=False):
 fn,receiver,args,label=event
 if log:events.append((event,speech_snapshot(currentState)))
 if fn==0x4f6286:
  if args[0]==0x5223cc:return CLMETA if metadataFound else 0
  if args[0]==0x5223b8:return ENMETA if metadataFound else 0
  if args[0]==0x52c580:return IMAGE if imageFound else 0
  if speechMutation==1:set_global('enemyActorToken',CL,native_side)
  if speechMutation==2:extra_put(EN+0x6c,[0],native_side)
  if speechMutation==3:set_global('enemyBusy',1,native_side)
  if speechMutation==4:set_global('clawBusy',1,native_side)
  return SOUND if soundFound else 0
 if fn==0x4a3050:
  if realSpeechRNG:
   assert native_side;events.append(((0x4a7dc0,0,(),None),speech_snapshot(currentState)));return lib.claw_world_loot_next_random(C.cast(C.addressof(extra)+RNG_TLS+0x14-EXTRA_BASE,C.POINTER(C.c_uint32)))
  return effects(currentState,event)
 if fn==0x4b45f0:
  if speechMutation==5:extra_put(EN+0x184,[0],native_side);set_global('enemyBusy',123,native_side)
  if speechMutation==6:extra_put(CL+0x184,[0],native_side);set_global('clawBusy',123,native_side)
  return 1
 return 0
@SpeechDependency
def speech_dependency(c,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);events.append((event,speech_snapshot(currentState)));return speech_effect(event,True)

# Dispatch required services from suspended frozen Human/Officer/Soldier bodies.
@Dependency
def dependency(s,g,e,user):
 e=e.contents
 if e.function in(0x420370,0x48ce40,0x48ceb0,0x48cf50,0x48cf90):
  speechContext.nameHint=e.name;args=(C.c_uint32*e.argumentCount)(*e.arguments[:e.argumentCount]);result=C.c_uint32()
  assert lib.claw_enemy_speech_entry(e.function,e.receiver,args,e.argumentCount,C.byref(speechContext),speech_dependency,None,C.byref(result))
  return result.value
 return humanoidDependency(s,g,C.pointer(e),user)

# Install only one current hook (the imported frozen hooks have been removed).
for handle in (strike_base_hook,):
 try:u.hook_del(handle)
 except Exception:pass
# Strike helper installed its final hook without retaining a handle. During
# source evaluation replace that line with a retained handle (see top loader).
u.hook_del(speech_old_hook)
def speech_hook(uc,address,size,user):
 if address in(0x48cc60,0x48c630,0x48ce40,0x48ceb0,0x420370,0x48cf50,0x48cf90,0x48c820,0x48c8a0):return
 if speechPhase and address in(0x4c8da0,0x4c8be0):return
 if address==0x4c7970 and( u.reg_read(UC_X86_REG_ECX)in(CL,EN)or u.reg_read(UC_X86_REG_ECX)in created):return
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
 if address==0x4f6286 and(speechPhase or 0x48c8a0<=ret<=0x48c8f0 or 0x48ceb0<=ret<=0x48cf50 or 0x4c7970<=ret<=0x4c79d0):
  token,out=m.read_words(sp+4,2);label=text(token);event=(address,u.reg_read(UC_X86_REG_ECX),(token,),label);s=snapshot();events.append((event,speech_snapshot(s)));value=speech_effect(event,False);write(s);m.write_words(out,[value]);returned(8,int(bool(value)));return
 if address==0x4b45f0 and speechPhase:
  event=(address,u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,4)),None);s=snapshot();events.append((event,speech_snapshot(s)));returned(16,speech_effect(event,False));return
 if address==0x4a3050 and speechPhase:
  event=(address,0,(),None);s=snapshot();events.append((event,speech_snapshot(s)))
  if not realSpeechRNG:returned(0,speech_effect(event,False))
  return
 if address==0x4a7dc0 and speechPhase and realSpeechRNG:
  events.append(((address,0,(),None),speech_snapshot(snapshot())));returned(0,RNG_TLS);return
 if address in(0x4f63ec,0x4f6428)and speechPhase:
  arg=m.read_words(sp+4,1)[0];s=snapshot();events.append(((address,0,(arg,),None),speech_snapshot(s)));returned(0,allocation(arg)if address==0x4f63ec else 0);return
 humanoidHost(uc,address,size,user)
u.hook_add(UC_HOOK_CODE,speech_hook)

old_prepared=prepared

def prepared(seed=1):
 global globals,speechContext,playerLogic,containerWords,cursor,allocIndex,failAlloc,created,speechMutation,soundFound,imageFound,metadataFound
 s,c=old_prepared(seed);globals=SpeechGlobals(MANAGER,P,1,0,CL,0,EN,A,16);speechContext=SpeechContext(speechHost,C.pointer(globals),b'LEVEL_OFFICER_00340024',0)
 playerLogic=(C.c_uint32*93)();playerLogic[5]=0x1039000;containerWords=(C.c_uint32*11)();containerWords[0]=0x513c20;containerWords[3]=SC;containerWords[4]=0x5107bc;containerWords[10]=10;cursor=0x10f0000;allocIndex=failAlloc=0;created=[];speechMutation=0;soundFound=imageFound=metadataFound=True
 extra_put(CL+0xc,[SC]);extra_put(CL+0x6c,[CLL]);extra_put(CLL+0x1c,[5]);extra_put(EN+0xc,[SC]);extra_put(EN+0x6c,[ENL]);extra_put(ENL+0x1c,[5]);extra_put(MANAGER+0x30,[SC]);extra_put(MANAGER+0x118,[1]);extra_put(MANAGER+0x12c,[80]);extra_put(SOUND+0x10,[POOL]);extra_put(POOL+0x28,[100]);extra_put(IMAGE+0x14,[FRAMEARRAY]);extra_put(IMAGE+0x64,[0,1]);extra_put(FRAMEARRAY,[0x123400,0x123404]);extra_put(CLMETA,[0,197,0,0,0x48c630]);extra_put(ENMETA,[0,198,0,0,0x48cc60]);return s,c

# No generic context owns the speech scalars; compare and retain all of them.
def compare_speech(s,c,fn,label,args=(),create_profile=None,fault_expected=False):
 global native,current,currentState,speechPhase,random_index,cursor,allocIndex,created,speech_calls,speech_events
 if fn in(0x48ceb0,0x48c8a0):speechContext.nameHint=text(args[1 if fn==0x48ceb0 else 0])if args[1 if fn==0x48ceb0 else 0]else None
 current=c;currentState=s;c.sharedStates.audioEnabled=globals.audioManagerToken;native=True;speechPhase=True;before,bc,be,bs,bg,bp,bw=bytes(s),bytes(c),bytes(extra),bytes(sceneWords),bytes(globals),bytes(playerLogic),bytes(containerWords);oldCursor,oldIndex,oldCreated=cursor,allocIndex,list(created);events.clear();random_index=0;speechContext.fault=0;result=C.c_uint32();a=(C.c_uint32*len(args))(*(v&0xffffffff for v in args))
 if create_profile is None:assert lib.claw_enemy_speech_entry(fn,0,a,len(args),C.byref(speechContext),speech_dependency,None,C.byref(result))
 else:result.value=lib.claw_enemy_speech_create(actorContainer,create_profile,C.byref(speechContext),speech_dependency,None)
 assert bool(speechContext.fault)==fault_expected,(label,'nativefault',speechContext.fault)
 expected,ee=speech_snapshot(s),list(events);nextCursor,nextIndex,nextCreated=cursor,allocIndex,list(created);nextExtra,nextScene,nextGlobals,nextPlayer,nextContainer=bytes(extra),bytes(sceneWords),bytes(globals),bytes(playerLogic),bytes(containerWords)
 old,oc=Enemy.from_buffer_copy(before),type(c).from_buffer_copy(bc);install(old,oc);u.mem_write(EXTRA_BASE,be);u.mem_write(SC,bs);u.mem_write(0x1038000,bp);u.mem_write(actorContainer,bw)
 for token,(field,_)in zip(GLOBAL_ADDRS,SpeechGlobals._fields_):m.write_words(token,[getattr(SpeechGlobals.from_buffer_copy(bg),field)])
 cursor,allocIndex,created=oldCursor,oldIndex,oldCreated;native=False;events.clear();random_index=0;failed=False
 try:ret=m.call(fn,actorContainer if create_profile is not None else 0,struct.pack('<6I',0,0,0,1000,0x5223b8 if create_profile else 0x5223cc,0x40000)if create_profile is not None else struct.pack('<'+'I'*len(args),*(v&0xffffffff for v in args)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'originalfault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'fault',failed)
 actual=speech_snapshot(snapshot())
 if actual!=expected:
  print(label,'diff',[(i,hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('fullspeech buffers/globals')
 if events!=ee:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],'snapshot',x[1]==y[1]);break
  print(len(ee),len(events));raise AssertionError('speech fullsnapshot order')
 if not failed and fn not in(0x420370,0x48cf50):assert ret==result.value,(label,'EAX',ret,result.value)
 assert cursor==nextCursor and allocIndex==nextIndex and created==nextCreated
 for target,data in((extra,nextExtra),(sceneWords,nextScene),(globals,nextGlobals),(playerLogic,nextPlayer),(containerWords,nextContainer)):C.memmove(C.addressof(target),data,len(data))
 current=c;currentState=s;native=True;speechPhase=False;speech_calls+=1;speech_events+=len(ee);return result.value

# All ordinary humanoid dependency callbacks now compare the extended speech
# globals and raw registered dialog actors as well as their old full fixture.
serialized=speech_snapshot
caller_install=install;callerBefore=None
def install(s,c):
 caller_install(s,c)
 if callerBefore is not None:
  bg,bp,bw=callerBefore
  for token,(field,_)in zip(GLOBAL_ADDRS,SpeechGlobals._fields_):m.write_words(token,[getattr(SpeechGlobals.from_buffer_copy(bg),field)])
  u.mem_write(0x1038000,bp);u.mem_write(actorContainer,bw)
def compare_caller(s,c,fn,label,args=(),entry_kind='human'):
 global callerBefore,currentState
 c.sharedStates.audioEnabled=globals.audioManagerToken;currentState=s;speechContext.nameHint=b'LEVEL_OFFICER_00340024';speechContext.fault=0
 callerBefore=(bytes(globals),bytes(playerLogic),bytes(containerWords))
 try:compare_strike(s,c,fn,label,args,entry_kind)
 finally:callerBefore=None;currentState=s
 assert not speechContext.fault,(label,'speech bridge fault',speechContext.fault)
