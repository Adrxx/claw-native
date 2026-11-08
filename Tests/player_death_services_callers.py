"""Only compose frozen fall/spike death and powerup bodies; no duplicate gameplay logic."""
import ast
import player_death_services_helpers as h
C=h.C
# Reuse the existing frozen oracle's ABI definitions without importing its
# build/run side effects or writing its private work directory.
nodes=ast.parse((h.ROOT/'Tests/player_damage_helpers.py').read_text()).body
types=[n for n in nodes if isinstance(n,ast.ClassDef)and n.name in('Physics','State','Input','Damage')]
exec(compile(ast.Module(body=types,type_ignores=[]),'frozen player damage ABI types','exec'),globals())
class PowerGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','powerup','remaining','expired','musicDisabled','cycleRemaining','cycleIndex')]
class PowerContext(C.Structure):_fields_=[('scene',h.Host),('globals',C.POINTER(PowerGlobals)),('fault',C.c_uint32)]
class PowerCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6),('name',C.c_char_p)]
PowerDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(PowerContext),C.POINTER(PowerCall),C.c_void_p)
Callback=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p)
h.lib.claw_player_powerup_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(PowerContext),PowerDependency,C.c_void_p,C.POINTER(C.c_uint32)];h.lib.claw_player_powerup_entry.restype=C.c_uint32
h.lib.claw_player_enter_fall_death.argtypes=[C.POINTER(State),C.POINTER(Damage),C.c_uint32,Callback,C.c_void_p]
h.lib.claw_player_enter_spike_death.argtypes=[C.POINTER(State),C.POINTER(Damage),Callback,C.c_void_p]
A,L,P,FX,INPUT,SC,REG,OVERLAY=[h.BASE+0x21000+i*0x1000 for i in range(8)]
state=damage=None;power=PowerGlobals();pctx=PowerContext();pctx.scene=h.ctx.scene;pctx.globals=C.pointer(power)
active=False;tempSeed=0;joinedCalls=0
def packed(*values):return h.struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
def extra():return {0x534db8:bytes(state.physics),0x534ea8:packed(power.remaining),0x534eac:packed(power.powerup),0x534eb8:packed(power.expired),0x53c9c0:packed(power.musicDisabled),0x534ec8:packed(power.cycleRemaining,power.cycleIndex)}
def push(s):
 h.put(A,list(s.actor));h.put(P,list(s.privateWords));h.put(L+0x1c,[s.logicState]);h.put(L+0x20,[damage.logicWord20]);h.put(INPUT+12,[s.inputLatched]);power.powerup=s.powerup
def pull(s):s.actor[:]=h.get(A,128);s.privateWords[:]=h.get(P,78);s.powerup=power.powerup
@Callback
def dependency(pointer,fn,a,b,c,user):
 live=pointer.contents;push(live);result=C.c_uint32()
 try:
  if fn in(0x41ebd0,0x4b7aa0):
   args=[]if fn==0x41ebd0 else[0];values=(C.c_uint32*len(args))(*args)
   assert h.lib.claw_player_death_service_entry(fn,h.g.managerToken if args else 0,values,len(args),C.byref(h.ctx),h.dependency,None,C.byref(result))
  elif fn==0x41f990:
   power.managerToken=h.g.managerToken;values=(C.c_uint32*5)(A,L,P,a,b)
   assert h.lib.claw_player_powerup_entry(fn,0,values,5,C.byref(pctx),PowerDependency(),None,C.byref(result))
  elif fn==0x4c79e0:
   call=h.Call();call.function=fn;call.receiver=A;call.argumentCount=2;call.arguments[:2]=[a,b]
   result.value=h.dependency(C.byref(h.ctx),C.byref(call),None)
  else:raise AssertionError(('unexpected death-caller dependency',hex(fn),a,b,c))
  pull(live);return result.value
 except Exception as e:h.errors.append(e);return 0
oldEffect=h.effects
def effects(fn,receiver,args,native,inputBuffer=None,outputBuffer=None):
 if fn==0x4c79e0:assert receiver==A and args[1]==1;return 0
 return oldEffect(fn,receiver,args,native,inputBuffer,outputBuffer)
h.effects=effects;h.COUNTS[0x4c79e0]=2
def notify_hook(u,address,size,user):
 global active
 if active and address==0x41ebd0:
  h.tempOriginal=u.reg_read(h.UC_X86_REG_ESP)-0x204;h.m.write_words(h.tempOriginal,[tempSeed])
h.m.u.hook_add(h.UC_HOOK_CODE,notify_hook)
def compare(fn,notice,label):
 global state,damage,tempSeed,active,joinedCalls
 h.prepare();h.put(h.MANAGER+0x14,[0]);h.put(h.MANAGER2+0x14,[0]);h.put(h.VT+0x10,[0x40af90 if h.mode==3 else 0x4750d0])
 state=State();damage=Damage()
 state.actor[:]=[h.rng.getrandbits(32)for _ in range(128)];state.privateWords[:]=[h.rng.getrandbits(32)for _ in range(78)]
 state.actor[0xc//4]=SC;state.actor[0x6c//4]=L;state.actor[0x170//4]=0;state.actor[0x64//4]=h.rng.choice([4000,8500]);state.privateWords[75]=0;state.privateWords[1]=0;state.privateWords[0x130//4]=FX
 state.logicState=24;state.inputLatched=h.rng.getrandbits(32);state.audioRegistryDisabled=1;damage.logicWord20=h.rng.getrandbits(32)
 for name,_ in Physics._fields_:
  if name in('stopped','unused'):setattr(state.physics,name,h.rng.getrandbits(32))
  elif name in('elapsed','timestep'):setattr(state.physics,name,h.rng.uniform(-100,100))
  else:getattr(state.physics,name)[:]=[h.rng.uniform(-100,100)for _ in range(3)]
 power.managerToken=h.g.managerToken;power.playerToken=A;power.powerup=h.rng.choice([0,0x26bc,0x26bd]);power.remaining=h.rng.choice([0,15000,999001,0xffffffff]);power.expired=h.rng.getrandbits(32);power.musicDisabled=0;power.cycleRemaining=0;power.cycleIndex=0x34;state.powerup=power.powerup
 h.put(L+0x14,[P]);h.put(SC+0x28,[REG]);h.put(REG+0x30,[1]);h.put(OVERLAY+0x44,[0]);h.m.write_words(0x537204,[INPUT]);h.m.write_words(0x537960,[OVERLAY])
 push(state);h.additionalGlobals=extra
 for address,value in extra().items():h.m.u.mem_write(address,value)
 h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();h.ctx.fault=pctx.fault=0;tempSeed=h.get(h.SCRATCH)[0];h.tempOriginal=h.m.stack-0x204
 #Normal notification-disabled falls never touch this adapted local.
 h.m.write_words(h.tempOriginal,[tempSeed]);beforeVoice=bytes(h.heap)[h.VOICEPOOL-h.BASE:h.VOICEPOOL-h.BASE+1024]
 if fn==0x417b00:h.lib.claw_player_enter_fall_death(C.byref(state),C.byref(damage),notice,dependency,None)
 else:h.lib.claw_player_enter_spike_death(C.byref(state),C.byref(damage),dependency,None)
 assert not h.errors,h.errors
 push(state);active=True
 try:h.m.call(fn,0,packed(A,L,P,notice)if fn==0x417b00 else packed(A,L,P))
 finally:active=False
 assert h.ctx.fault==pctx.fault==0
 assert h.native_events==h.original_events,(label,'callbacks',[(i,a[:4],b[:4],a[4][2],b[4][2])for i,(a,b)in enumerate(zip(h.native_events,h.original_events))if a!=b][:3],len(h.native_events),len(h.original_events))
 assert h.raw(True)==h.raw(False),(label,'heap bytes',[(i,a,b)for i,(a,b)in enumerate(zip(h.raw(True),h.raw(False)))if a!=b][:8])
 assert h.globals_raw(True)==h.globals_raw(False),(label,'globals bytes',[(hex(0x528000+i),a,b)for i,(a,b)in enumerate(zip(h.globals_raw(True),h.globals_raw(False)))if a!=b][:8])
 assert beforeVoice==bytes(h.heap)[h.VOICEPOOL-h.BASE:h.VOICEPOOL-h.BASE+1024],(label,'voice mutation')
 joinedCalls+=1;h.calls+=1;h.events+=len(h.native_events)
