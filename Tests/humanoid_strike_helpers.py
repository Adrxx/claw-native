"""Private strike oracle composing immutable Human/Soldier fixture definitions."""
from pathlib import Path
zero_mapped=True
source=Path(__file__).with_name('soldier_helpers.py').read_text().split('def compare_failure(kind):')[0]
source=source.replace('work/soldier-agent','work/humanoid-strike-agent')
source=source.replace("'GameTiming.cpp','HumanEnemy.cpp'","'GameTiming.cpp','HumanoidStrikeRuntime.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp','HumanEnemy.cpp'")
source=source.replace("('CommonEnemyEntries.cpp','SoldierLogic.cpp'","('HumanoidStrikeRuntime.cpp','CommonEnemyEntries.cpp','SoldierLogic.cpp'")
source=source.replace('u.hook_del(baseHook);u.hook_add(UC_HOOK_CODE,host)','u.hook_del(baseHook);strike_base_hook=u.hook_add(UC_HOOK_CODE,host)')
source=source.replace("exec(compile(source,str(Path(__file__).with_name('human_enemy_helpers.py'))", "source=source.replace('m.write_words(0,[0x12345678]);','m.write_words(0,[0x12345678]) if zero_mapped else None;')\nexec(compile(source,str(Path(__file__).with_name('human_enemy_helpers.py'))")
exec(compile(source,str(Path(__file__).with_name('soldier_helpers.py')),'exec'),globals())
# The new module's raw-argument ABI shares the existing pointer-view ABI.
class StrikeContext(C.Structure):_fields_=[('human',C.POINTER(HumanContext)),('scene',SceneHost),('sequenceName',C.c_char_p),('soundName',C.c_char_p),('composeAnimation',C.c_uint32),('fault',C.c_uint32)]
lib.claw_humanoid_strike_entry.argtypes=[C.POINTER(Enemy),C.POINTER(StrikeContext),C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_humanoid_strike_entry.restype=C.c_uint32
EXTRA_BASE,EXTRA_SIZE=0x10a0000,0x60000
RECT,ALT_ACTOR,ALT_PRIMARY=0x10e0000,0x10e1000,0x10e2000
extra=(C.c_uint8*EXTRA_SIZE)();sceneWords=(C.c_uint32*16)();currentState=None;strikeContext=None;phase=0;compose=0;strikeMutation=0;seqHint=b'LEVEL_OFFICER_STRIKE';soundHint=b'LEVEL_OFFICER_00340024';resourceTokens={};nextResource=0x10c0000;ANI_TABLE,ANI_RECORDS=0x10e3000,0x10e4000
oldSerialized=serialized;oldEffects=effects;oldSnapshot=snapshot;oldInstall=install;oldHost=host

def extra_put(t,values,native_side=True):
 data=struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
 if native_side:C.memmove(C.addressof(extra)+t-EXTRA_BASE,data,len(data))
 else:u.mem_write(t,data)
def extra_get(t,n=1,native_side=True):return list(struct.unpack('<'+'I'*n,C.string_at(C.addressof(extra)+t-EXTRA_BASE,n*4)))if native_side else m.read_words(t,n)
def serialized(s):return oldSerialized(s)+bytes(sceneWords)+bytes(extra)if native else oldSerialized(s)+bytes(u.mem_read(SC,64))+bytes(u.mem_read(EXTRA_BASE,EXTRA_SIZE))
RawLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32)
@RawLookup
def raw_lookup(_,t,n):
 if EXTRA_BASE<=t and t+n*4<=EXTRA_BASE+EXTRA_SIZE:return C.addressof(extra)+t-EXTRA_BASE
 if SC<=t and t+n*4<=SC+64:return C.addressof(sceneWords)+t-SC
 return None
sceneHost=SceneHost(None,C.cast(raw_lookup,Lookup),Allocate(),Free(),SceneDependency(),Clock())

def resource(name):
 global nextResource
 if name not in resourceTokens:
  resourceTokens[name]=nextResource;nextResource+=0x100
 return resourceTokens[name]
def effects(s,event):
 fn,receiver,args,name=event
 if fn==0x4f6286:
  value=resource(name)if resource_mode==1 or(resource_mode==2 and name==b'GAME_NULL')else 0
  if strikeMutation==1:
   # The rectangle has been copied; later image lookup mutation must not
   # retroactively change it. Actor sequence is saved after the lookup.
   s.enemy[0x220//4]^=0xfeed;s.actor[0x190//4]=0xfeed1234
  if strikeMutation==2 and name!=b'GAME_NULL':
   s.enemy[0x12c//4]=ALT_ACTOR
  if strikeMutation==3:
   current.sequenceRegistryToken^=0x100
   sceneWords[11]^=0x100
   if not native:m.write_words(SC+0x2c,[sceneWords[11]])
  return value
 if fn==0x4dba00:
  if strikeMutation==4:s.enemy[0x10//4]=ALT_PRIMARY
  return ids[name]
 return oldEffects(s,event)
@Dependency
def dependency(s,g,e,user):
 e=e.contents
 if e.function in(0x43ee10,0x43eee0):
  result=C.c_uint32();arguments=(C.c_uint32*e.argumentCount)(*e.arguments[:e.argumentCount])
  assert lib.claw_humanoid_strike_entry(s,C.byref(strikeContext),e.function,arguments,e.argumentCount,dependency,None,C.byref(result))
  return result.value
 event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);events.append((event,serialized(s.contents)));return effects(s.contents,event)

u.hook_del(strike_base_hook)
def host(uc,address,size,user):
 if address in(0x43ee10,0x43eee0):return
 if address in(0x4c8220,0x4c82a0)and compose:return
 if phase in(0x43ee10,0x43eee0)and address in(0x4f6286,0x4dba00):
  sp=u.reg_read(UC_X86_REG_ESP);nameToken=m.read_words(sp+4,1)[0];name=text(nameToken);event=(address,u.reg_read(UC_X86_REG_ECX),(nameToken,),name);s=snapshot();events.append((event,serialized(s)));value=effects(s,event);write(s)
  if address==0x4f6286:m.write_words(m.read_words(sp+8,1)[0],[value]);returned(8,int(bool(value)))
  else:returned(4,value)
  return
 oldHost(uc,address,size,user)
u.hook_add(UC_HOOK_CODE,host)

# Runtime sequence headers are resource transport outputs. Actual ANI record
# bytes are decoded by frozen decoder, checked against original4d76e0 below.
class AnimationRecord(C.Structure):_fields_=[(n,C.c_uint32)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(AnimationRecord),C.POINTER(C.c_uint32)];lib.claw_animation_decode_record.restype=C.c_uint32
ani_decodes=0

def load_ani(name,path):
 global ani_decodes
 data=(ROOT/'App/GameData'/path).read_bytes();count,pathLength=struct.unpack_from('<2I',data,12);position=32+pathLength;sequence=resource(name)
 extra_put(sequence+0xc,[ANI_TABLE,count]);extra_put(ANI_TABLE,[ANI_RECORDS+i*0x40 for i in range(count)])
 # One fixture sequence at a time; other ctor resource roots stay opaque.
 for index in range(count):
  remaining=data[position:];buf=(C.c_uint8*len(remaining)).from_buffer_copy(remaining);record=AnimationRecord();length=C.c_uint32();used=lib.claw_animation_decode_record(buf,len(remaining),0,C.byref(record),C.byref(length));assert used
  token=ANI_RECORDS+index*0x40;seed=extra_get(token,12);m.write_words(token,seed);u.mem_write(0x10e8000,remaining);m.call(0x4d76e0,token,struct.pack('<2I',0,0x10e8000));raw=m.read_words(token,12)
  assert [getattr(record,n)for n,_ in AnimationRecord._fields_]==[raw[1]&0xffff]+raw[2:10]+[raw[11]]
  extra_put(token,raw);position+=used;ani_decodes+=1
 assert position==len(data)
 return sequence

def prepared(seed=1):
 global current,currentState,extra,sceneWords,strikeMutation,compose,phase,resourceTokens,nextResource
 s,c=fresh();current=c;currentState=s;extra=(C.c_uint8*EXTRA_SIZE).from_buffer_copy(random.Random(seed).randbytes(EXTRA_SIZE));sceneWords=(C.c_uint32*16)();sceneWords[2]=actorContainer;sceneWords[5]=c.generic.soundRegistryToken-16;sceneWords[9]=c.generic.tileManagerToken;sceneWords[10]=c.generic.soundRegistryToken-16;sceneWords[11]=c.sequenceRegistryToken-16
 strikeMutation=compose=phase=0;resourceTokens={};nextResource=0x10c0000
 s.enemy[4]=L;s.enemy[0x12c//4]=A;s.enemy[3]=A;s.actor[0xc//4]=SC
 for res in resourceViews:extra_put(res.token+0x10,[res.controllerToken])
 extra_put(RECT,[-20,-25,20,25]);extra_put(ALT_ACTOR+0xc,[SC]);extra_put(ALT_ACTOR+0x190,[0xabc123]);extra_put(ALT_PRIMARY+0x1c,[1234])
 policy=mutate=0
 return s,c

def compare_strike(s,c,fn,label,args=(),entry_kind='strike',fault_expected=False):
 global current,currentState,native,random_index,calls,event_count,strikeContext,phase
 phase=fn;current=c;currentState=s;native=True;random_index=0;events.clear();before,bc,bb,be,bs=bytes(s),bytes(c),bytes(bitBacking),bytes(extra),bytes(sceneWords)
 hv,combat,aux,cx=views(c);strikeContext=StrikeContext(C.pointer(hv),sceneHost,seqHint,soundHint,compose,0);result=C.c_uint32();argv=(C.c_uint32*len(args))(*(a&0xffffffff for a in args))
 if entry_kind=='strike':status=lib.claw_humanoid_strike_entry(C.byref(s),C.byref(strikeContext),fn,argv,len(args),dependency,None,C.byref(result))
 elif entry_kind=='soldier':status=lib.claw_soldier_entry(C.byref(s),C.byref(cx),fn,args[0]if args else 0,dependency,None,C.byref(result))
 elif entry_kind=='human':status=lib.claw_human_enemy_entry(C.byref(s),C.byref(hv),fn,args[0]if args else 0,dependency,None,C.byref(result))
 elif entry_kind=='officer':status=lib.claw_officer_entry(C.byref(s),C.byref(c),fn,args[0]if args else 0,dependency,None,C.byref(result))
 assert status and bool(strikeContext.fault)==fault_expected,(label,'scope',strikeContext.fault,hv.fault,cx.fault)
 expected,ee=serialized(s),list(events);newExtra=bytes(extra);newScene=bytes(sceneWords);newBB=bytes(bitBacking)
 old,oc=Enemy.from_buffer_copy(before),type(c).from_buffer_copy(bc);C.memmove(C.addressof(extra),be,len(be));C.memmove(C.addressof(sceneWords),bs,len(bs));C.memmove(C.addressof(bitBacking),bb,len(bb));install(old,oc);u.mem_write(EXTRA_BASE,be);u.mem_write(SC,bs);native=False;events.clear();random_index=0
 ret=None;failed=False
 try:ret=m.call(fn,E,struct.pack('<'+'I'*len(args),*(a&0xffffffff for a in args)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'original fault',failed)
 actual=serialized(snapshot())
 if expected!=actual:
  print(label,'diff',[(i,hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('complete state/extra heap')
 if events!=ee:
  for i,(a,b)in enumerate(zip(ee,events)):
   if a!=b:print(label,'event',i,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('counts',len(ee),len(events));raise AssertionError('ordered full snapshots')
 if not fault_expected and fn in(0x43ee10,0x43eee0):assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(args)*4,(label,'thiscall RET argument cleanup')
 if not fault_expected and entry_kind=='strike':assert ret==result.value==0,(label,'meaningful EAX',ret,result.value)
 assert bytes(u.mem_read(q['HEAP'],q['SIZE']))==registryHeap
 for token,words in registryTables.items():assert m.read_words(token,12)==words
 C.memmove(C.addressof(extra),newExtra,len(newExtra));C.memmove(C.addressof(sceneWords),newScene,len(newScene));C.memmove(C.addressof(bitBacking),newBB,len(newBB));current=c;native=True;calls+=1;event_count+=len(ee)
 return s,c
# Officer's actual allocation has20 tailwords. Soldier has24. Keep contexts
# separate while the pointer-view Human ABI is shared.
class OfficerContext(C.Structure):_fields_=[(name,C.c_uint32*20 if name=='privateTail'else typ)for name,typ in Context._fields_]
lib.claw_officer_context_defaults.argtypes=[C.c_void_p];lib.claw_officer_entry.argtypes=[C.POINTER(Enemy),C.c_void_p,C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
# Common raw snapshot reader accommodates either source allocation size.
def baseSnapshot():
 s=Enemy()
 for name in sizes:getattr(s,name)[:]=m.read_words(addresses[name],sizes[name])
 current.privateTail[:]=m.read_words(E+0x420,len(current.privateTail));current.generic.playerActor[:]=m.read_words(P,128)
 for field,token,count in extraBuffers:getattr(current,field)[:]=m.read_words(token,count)
 return s

def prepared_officer(seed=1):
 global current
 s,c=prepared(seed);officer=OfficerContext()
 for name,typ in OfficerContext._fields_:
  if issubclass(typ,C.Array):getattr(officer,name)[:]=list(getattr(c,name))[:C.sizeof(typ)//C.sizeof(typ._type_)]
  else:setattr(officer,name,getattr(c,name))
 lib.claw_officer_context_defaults(C.byref(officer));officer.generic.states=states;officer.generic.stateCount=len(states);officer.generic.emptyStringToken=0x52e1c4
 officer.patrolStates=humanStates;officer.patrolStateCount=len(humanStates);officer.officerStates=officerStatesExact;officer.officerStateCount=len(officerStatesExact);s.enemy[0]=0x50ea0c;current=officer;return s,officer
q['m'].call(0x441030,0x537ba0,struct.pack('<I',2000))
registryHeap=bytes(q['u'].mem_read(q['HEAP'],q['SIZE']));registryTables={t:q['m'].read_words(t,12)for t in q['tokens']};officerStatesExact=class_view(0x537ba0)

baseDependency=dependency
@Dependency
def dependency(s,g,e,user):
 global strikeContext
 event=e.contents;fn=event.function
 if event.receiver==E:
  result=C.c_uint32();hv=human_view(current);hv.humanStates=humanStates;hv.humanStateCount=len(humanStates)
  if fn in(0x43ee10,0x43eee0,0x43efe0,0x43f030):
   strikeContext.human=C.pointer(hv);arguments=(C.c_uint32*event.argumentCount)(*event.arguments[:event.argumentCount])
   return lib.claw_humanoid_strike_entry(s,C.byref(strikeContext),fn,arguments,event.argumentCount,dependency,None,C.byref(result))and result.value
  if isinstance(current,OfficerContext)and lib.claw_officer_entry(s,C.byref(current),fn,event.arguments[0]if event.argumentCount else 0,dependency,None,C.byref(result)):return result.value
  if lib.claw_human_enemy_entry(s,C.byref(hv),fn,event.arguments[0]if event.argumentCount else 0,dependency,None,C.byref(result)):return result.value
 if compose and fn in(0x4c8220,0x4c82a0):
  anim=AnimationGlobals(current.generic.animationDelta,current.sharedStates.audioPosition);fault=C.c_uint32();value=C.c_uint32();assert lib.claw_actor_animation_entry(fn,event.receiver,event.arguments[0],0,C.byref(anim),animationHost,C.byref(fault),C.byref(value))and not fault.value
  return value.value
 return baseDependency(s,g,e,user)
# Pointer-view aliasing for composed frozen ANI services initiated by frozen
# Officer/Human bodies; the strike module uses the equivalent native alias host.
@RawLookup
def animation_lookup(_,t,n):
 for token,count,array in((A,128,currentState.actor),(L,93,currentState.primary),(E,264,currentState.enemy)):
  if token<=t and t+n*4<=token+count*4:return C.addressof(array)+t-token
 return raw_lookup(None,t,n)
@SceneDependency
def animation_call(_,call):
 args=tuple(call.arguments[:call.argumentCount]);event=(call.function,call.receiver,args,None);events.append((event,serialized(currentState)));return effects(currentState,event)
animationHost=SceneHost(None,C.cast(animation_lookup,Lookup),Allocate(),Free(),animation_call,Clock())
class AnimationGlobals(C.Structure):_fields_=[('animationDelta',C.c_uint32),('audioPosition',C.c_uint32)]
lib.claw_actor_animation_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(AnimationGlobals),SceneHost,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]

# Match the actual post-constructor image namespace numeric span. Pixels remain
# opaque resource outputs; selector writes use the source27-word root ABI.
def image_profile(s,kind):
 import re
 directory=ROOT/'App/GameData/LEVEL1/IMAGES'/kind
 ids=[int(re.search(r'(\d+)$',p.stem).group(1))for p in directory.glob('*.PID')]
 low,high=min(ids),max(ids);root=s.actor[0x170//4];assert EXTRA_BASE<=root<EXTRA_BASE+EXTRA_SIZE
 extra_put(root+0x14,[0x10e6000]);extra_put(root+0x64,[low,high]);extra_put(0x10e6000,[0x10e9000+i*4 for i in range(high+1)])
