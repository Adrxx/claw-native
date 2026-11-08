"""Composition-only adapters for frozen hit/initialization callers."""
import player_powerup_runtime_helpers as h
C=h.C
class Physics(C.Structure):
 _fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3)for n in('acceleration','velocity','position','minimum','maximum','delta')]+[('stopped',C.c_uint32),('unused',C.c_uint32)]+[(n,C.c_double*3)for n in('remainder','maximumDelta','maximumVelocity')]
class State(C.Structure):
 _fields_=[('actor',C.c_uint32*128),('privateWords',C.c_uint32*78)]+[(n,C.c_uint32)for n in('logicState','inputLatched','inputHeld','stageDelta','animationDelta','powerup','pixelScratch')]+[('physics',Physics),('weaponLogicStatus',C.c_int32),('weaponLogicCallback',C.c_uint32),('weaponDeleteCount',C.c_uint32),('weaponDeleteFlags',C.c_uint32)]+[(n,C.c_uint32)for n in('highJump','pixelScratchY','audioRegistryDisabled','audioPosition')]
class Input(C.Structure):_fields_=[(n,C.c_uint32)for n in('pressed','invulnerabilityTimer','minimumX','maximumX','minimumY','maximumY','ignoreHazards','cheat')]
class Initialization(C.Structure):
 _fields_=[('defaults',C.c_uint32*78)]+[(n,C.c_uint32)for n in('difficulty','worldWidth','worldHeight','startX','startY','checkpointX','checkpointY','privateToken','cachedX','cachedY','powerupRemaining','powerupAuxiliary','accumulator','accumulatorMinimum','accumulatorStep','imageOffsetsAdjusted')]+[('ladderImageTokens',C.c_uint32*7),('ladderImageWord24',C.c_uint32*7)]+[(n,C.c_uint32)for n in('configurationToken','resetObjectToken')]
class Damage(C.Structure):
 _fields_=[('attackerToken',C.c_uint32),('attackerActor',C.c_uint32*128)]+[(n,C.c_uint32)for n in('configurationToken','configurationWord764','logicWord20','infiniteLives','overlayMode','overlayOffsetY','windowToken','audioManagerAvailable','resolvedSoundPoolToken')]
Callback=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p)
h.lib.claw_player_hit.argtypes=[C.POINTER(State),C.POINTER(Damage),C.POINTER(Input),Callback,C.c_void_p];h.lib.claw_player_hit.restype=C.c_uint32
h.lib.claw_player_dispatch_initialization.argtypes=[C.POINTER(State),C.POINTER(Initialization),C.POINTER(Input),Callback,C.c_void_p];h.lib.claw_player_dispatch_initialization.restype=C.c_uint32
INPUT,CONFIG,CONFIGVT,MAP,PLANE,ITEM,REG=[h.BASE+0x21000+i*0x1000 for i in range(7)]
MODE=0x10ff180
state=initialization=input=damage=None;mode=0;phase='';base_effect=h.effect;caller_calls=0
def packed(*values):return h.struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
def global_updates():
 result={0x534db8:bytes(state.physics),0x53720c:packed(state.stageDelta),0x5430c4:packed(state.animationDelta),
  0x537230:packed(input.ignoreHazards),0x537214:packed(input.cheat)}
 if phase=='respawn':
  j=initialization
  result.update({0x52be14:packed(j.cachedX,j.cachedY),0x53c9f8:packed(j.accumulator),
    0x534eb0:packed(j.powerupAuxiliary),0x534c80:bytes(j.defaults)})
 return result
def push(s):
 h.put(h.A,list(s.actor));h.put(h.P,list(s.privateWords));h.put(h.L+0x1c,[s.logicState]);h.g.powerup=s.powerup
 h.put(h.L+0x130,[input.invulnerabilityTimer]);h.put(h.L+0x2c,[input.minimumX,input.maximumX,input.minimumY,input.maximumY])
 h.put(INPUT+4,[input.pressed,s.inputHeld,s.inputLatched])
 if phase=='hit':h.put(ITEM,list(damage.attackerActor))
def pull(s):
 s.actor[:]=h.get(h.A,128);s.privateWords[:]=h.get(h.P,78);s.powerup=h.g.powerup
 if phase=='hit':damage.attackerActor[:]=h.get(ITEM,128)
 if phase=='respawn':initialization.powerupRemaining=h.g.remaining
def caller_effect(fn,receiver,args,native):
 if fn==0x4c7900:
  assert receiver==h.A and args==[0x523734,11]
  h.put(h.A+0x170,[h.IM],native);h.put(h.A+0x16c,[11],native);h.put(h.A+0x174,[h.IMAGE],native);return 0
 if fn==0x4cd800:
  assert receiver==MAP and args==[h.A,0]
  h.put(h.A+0x50,[h.get(h.A+0x50,native=native)[0]+7],native);return 0
 if fn==0x4c79e0:
  assert receiver==h.A and args==[0x5246d0,1];return 0
 if fn==MODE:assert receiver==CONFIG and args==[];return mode
 if fn==0x420910:assert receiver==REG;return 1
 if fn in(0x41d6f0,0x41f850,0x473ae0):
  assert receiver==0 and args[0]==ITEM
  h.put(ITEM+0x18,[h.get(ITEM+0x18,native=native)[0]+1],native)
  return 0
 if fn==0x41ee60:
  # Out-of-scope Special/Curse/EndOfLevel bodies remain exact services.
  assert receiver==0 and args==[h.A,h.L,h.P,ITEM];return 0
 return base_effect(fn,receiver,args,native)
h.effect=caller_effect
h.COUNTS.update({0x4c7900:2,0x4cd800:2,0x4c79e0:2,MODE:0,0x420910:1,0x41d6f0:1,0x41f850:2,0x473ae0:1,0x41ee60:4})
h.CDECL.update((0x41d6f0,0x41f850,0x473ae0,0x41ee60))
@Callback
def caller_dependency(pointer,fn,a,b,c,user):
 live=pointer.contents;push(live)
 try:
  if fn in(0x41f990,0x41fc30,0x4bc110):
   args=[h.A,h.L,h.P,a,b]if fn==0x41f990 else[h.A,h.L,h.P,a]if fn==0x41fc30 else[]
   values=(C.c_uint32*len(args))(*args);result=C.c_uint32()
   assert h.lib.claw_player_powerup_entry(fn,h.g.managerToken if fn==0x4bc110 else 0,values,len(args),C.byref(h.ctx),h.dependency,None,C.byref(result))
   pull(live);return result.value
  receiver=0;args=[]
  if fn in(0x4c7900,0x4c79e0):receiver=h.A;args=[a,b]
  elif fn==0x4cd800:receiver=MAP;args=[h.A,a]
  elif fn==0x10:fn=MODE;receiver=CONFIG
  elif fn==0x420910:receiver=REG;args=[a]
  elif fn in(0x41d6f0,0x473ae0):args=[a]
  elif fn==0x41f850:args=[a,h.P]
  elif fn==0x41ee60:args=[h.A,h.L,h.P,a]
  else:raise AssertionError(('unexpected caller dependency',hex(fn),a,b,c))
  call=h.Call();call.function=fn;call.receiver=receiver;call.argumentCount=len(args);call.arguments[:len(args)]=args
  result=h.dependency(C.byref(h.ctx),C.byref(call),None);pull(live);return result
 except Exception as e:h.errors.append(e);return 0
def prepare(old,remaining,kind):
 global state,initialization,input,damage,phase
 phase=kind;h.prepare(old,remaining)
 state=State();state.actor[:]=h.get(h.A,128);state.privateWords[:]=h.get(h.P,78)
 state.logicState=23 if phase=='respawn'else 24;state.stageDelta=h.rng.choice([0,18,100,0xffffffff]);state.animationDelta=18;state.powerup=h.g.powerup
 state.inputHeld=h.rng.getrandbits(32);state.inputLatched=h.rng.getrandbits(32)
 for name,_ in Physics._fields_:
  if name in('stopped','unused'):setattr(state.physics,name,h.rng.getrandbits(32))
  elif name in('elapsed','timestep'):setattr(state.physics,name,h.rng.uniform(-100,100))
  else:getattr(state.physics,name)[:]=[h.rng.uniform(-100,100)for _ in range(3)]
 state.privateWords[75]=0;state.privateWords[1]=0;state.privateWords[19]=100;state.privateWords[20]=200
 input=Input(0,0,50,5000,50,10000,1,0)
 initialization=Initialization();j=initialization;j.privateToken=h.P;j.cachedX=5;j.cachedY=7;j.powerupRemaining=h.g.remaining;j.powerupAuxiliary=0x12345678
 j.accumulator=h.rng.getrandbits(32);j.accumulatorMinimum=h.rng.getrandbits(32);j.accumulatorStep=h.rng.getrandbits(32)
 j.checkpointX=h.rng.choice([0xffffffff,300]);j.checkpointY=h.rng.choice([0xffffffff,400]);j.configurationToken=CONFIG
 j.defaults[:]=[h.rng.getrandbits(32)for _ in range(78)]
 damage=Damage();damage.attackerToken=ITEM;damage.attackerActor[:]=[h.rng.getrandbits(32)for _ in range(128)]
 damage.attackerActor[0xd0//4]=0x10000;damage.attackerActor[0xfc//4]=15000;damage.attackerActor[0x108//4]=0
 state.actor[0x74//4]=ITEM
 h.put(h.MUSICOWNER+0x2c,[CONFIG]);h.put(h.MUSICOWNER2+0x2c,[CONFIG]);h.put(CONFIG,[CONFIGVT]);h.put(CONFIGVT+0x10,[MODE]);h.put(CONFIG+0x44,[j.checkpointX,j.checkpointY])
 h.put(h.PARENT+0x24,[MAP]);h.put(h.PARENT+0x28,[REG]);h.put(MAP+0x5c,[PLANE]);h.put(PLANE+0x30,[5050,10050]);h.put(PLANE+0x84,[100,200])
 h.m.write_words(0x537204,[INPUT]);h.m.write_words(0x5349dc,[0]);h.m.write_words(0x52c6e4,[j.accumulatorMinimum]);h.m.write_words(0x52c6ec,[j.accumulatorStep])
 h.native_global_updates=global_updates;push(state)
 for address,value in global_updates().items():h.m.u.mem_write(address,value)
def compare(label):
 global caller_calls,state
 push(state);h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();h.ctx.fault=0
 h.native_global_updates=global_updates
 if phase=='hit':native=h.lib.claw_player_hit(C.byref(state),C.byref(damage),C.byref(input),caller_dependency,None);fn=0x41ce80
 else:native=h.lib.claw_player_dispatch_initialization(C.byref(state),C.byref(initialization),C.byref(input),caller_dependency,None);fn=0x415df0
 assert not h.errors,h.errors
 push(state);original=h.m.call(fn,0,packed(h.A))
 assert h.ctx.fault==0,(label,'native fault',h.ctx.fault)
 assert h.native_events==h.original_events,(label,'callback mismatch',[(i,hex(a[0]),hex(b[0]),a[3][0],b[3][0])for i,(a,b)in enumerate(zip(h.native_events,h.original_events))if a!=b][:4],len(h.native_events),len(h.original_events))
 assert h.snapshot(True)==h.snapshot(False),(label,'whole snapshots',h.snapshot(True)[0],h.snapshot(False)[0])
 assert h.raw(True)==h.raw(False),(label,'whole heap mismatch',[(i,a,b)for i,(a,b)in enumerate(zip(h.raw(True),h.raw(False)))if a!=b][:12])
 assert h.global_raw(True)==h.global_raw(False),(label,'whole globals mismatch',[(hex(h.GLOBAL_START+i),a,b)for i,(a,b)in enumerate(zip(h.global_raw(True),h.global_raw(False)))if a!=b][:12])
 if phase=='respawn':assert native==original==1
 caller_calls+=1;h.calls+=1;h.events+=len(h.native_events)
