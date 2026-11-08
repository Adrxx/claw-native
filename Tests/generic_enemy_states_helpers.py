"""Owned extension of frozen common-enemy harness; only dependencies adapted."""
import ctypes as C,json,struct,subprocess
import compare_generic_enemy as g
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
ROOT=g.ROOT;scratch=ROOT/'work/generic-enemy-states-agent';scratch.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-O2','-dynamiclib',*[str(ROOT/'Sources'/name)for name in ['GenericEnemyStates.cpp','GenericEnemy.cpp','PlayerPhysics.cpp']],'-o',str(scratch/'libGenericEnemyStates.dylib')],check=True)
lib=C.CDLL(str(scratch/'libGenericEnemyStates.dylib'))
class Resource(C.Structure):_fields_=[('token',C.c_uint32),('controllerToken',C.c_uint32)]
class Extra(C.Structure):_fields_=[('attackerToken',C.c_uint32),('attackerActor',C.c_uint32*128),('playerPrivate',C.c_uint32*78),('strikeCounter',C.c_uint32),('audioEnabled',C.c_uint32),('audioPosition',C.c_uint32),('resources',C.POINTER(Resource)),('resourceCount',C.c_size_t)]
lib.claw_generic_enemy_state_entry.argtypes=[C.POINTER(g.Enemy),C.POINTER(g.Context),C.POINTER(Extra),C.c_uint32,C.c_uint32,g.Dependency,C.c_void_p];lib.claw_generic_enemy_state_entry.restype=C.c_uint32
lib.claw_generic_enemy_state_dispatch.argtypes=[C.POINTER(g.Enemy),C.POINTER(g.Context),C.POINTER(Extra),C.c_int32,g.Dependency,C.c_void_p];lib.claw_generic_enemy_state_dispatch.restype=C.c_uint32
VBASE=0x10fa000
AX,PLAYER_LOGIC,PLAYER_PRIVATE=0x1017000,0x1018000,0x1019000
resources=(Resource*8)(*[Resource(0x101a000+i*0x100,0x101c000+i*0x100)for i in range(8)])
profile=json.loads((ROOT/'work/generic-enemy-agent/shared-registrations.json').read_text())
g.names=[x['name'].encode()for x in profile['entries']]+[b'LS_TEST']
g.functions=[int(x['function'],16)for x in profile['entries']]+[0x10fe000]
g.states=(g.State*len(g.names))(*[g.State(i,f,g.STRINGS+64*i,name)for i,(name,f)in enumerate(zip(g.names,g.functions))])
original_effects=g.effects
extra=None;common_context=None;native=False;animation_result=0;random_results=[];random_index=0;calls=0;events=0
# Preserve complete extra input buffers and globals alongside the original
# actor/logic/enemy snapshots at every dependency boundary.
def read_extra():
 result=Extra.from_buffer_copy(bytes(extra));result.attackerActor[:]=g.m.read_words(AX,128);result.playerPrivate[:]=g.m.read_words(PLAYER_PRIVATE,78)
 result.strikeCounter=g.m.read_words(0x52713c,1)[0];result.audioEnabled=g.m.read_words(0x532c0c,1)[0];result.audioPosition=g.m.read_words(0x532c10,1)[0];return result
def write_extra(x):
 g.m.write_words(AX,x.attackerActor);g.m.write_words(PLAYER_PRIVATE,x.playerPrivate)
 g.m.write_words(0x52713c,[x.strikeCounter]);g.m.write_words(0x532c0c,[x.audioEnabled]);g.m.write_words(0x532c10,[x.audioPosition])
class Logs(list):
 def __init__(self,original):super().__init__();self.original=original
 def append(self,record):
  global extra
  if self.original:
   current=read_extra();C.memmove(C.byref(extra),C.byref(current),C.sizeof(Extra));value=bytes(current)
  else:value=bytes(extra)
  backing=()
  if common_context and common_context.bitWordCount:
   backing=tuple(g.m.read_words(g.BITS,common_context.bitWordCount))if self.original else tuple(common_context.bitWords[i]for i in range(common_context.bitWordCount))
  super().append((*record,value,backing))
g.native_events=Logs(False);g.original_events=Logs(True)
def effects(s,event):
 global random_index
 f,receiver,args,name=event
 if f==0x4c82a0:result=animation_result
 elif f==0x4a3050:
  result=random_results[random_index%len(random_results)]if random_results else 0;random_index+=1
 elif VBASE<=f<VBASE+0x100:
  result=0;s.enemy[0x328//4]^=f
  if g.policy==2:s.primary[7]=(s.primary[7]+1)%len(g.names);s.enemy[7]=s.primary[7]
 else:result=original_effects(s,event)
 if g.policy==3:
  s.enemy[0x404//4]^=f
  if f==0x4c82a0:
   s.actor[0x1a4//4]^=1;s.actor[0x19c//4]=0;extra.playerPrivate[0]^=1
  elif f in(0x4dba00,0x4b45f0,0x4208e0):
   extra.audioEnabled^=1;s.actor[0x40//4]^=2
  elif f==0x4a3050:
   extra.attackerActor[0xd0//4]^=2;s.enemy[0x18c//4]^=1
  elif VBASE<=f<VBASE+0x100:
   s.actor[2]^=4;extra.strikeCounter^=1;s.enemy[8]^=4
 if not native:write_extra(extra)
 return result
g.effects=effects
@g.Dependency
def dependency(s,c,e,user):
 value=e.contents;event=(value.function,value.receiver,tuple(value.arguments[:value.argumentCount]),value.name)
 g.native_events.append((event,bytes(s.contents)));return effects(s.contents,event)
def host(uc,address,size,user):
 if address not in (0x420370,0x4208e0,0x420a10,0x4b45f0,0x461a00)and not VBASE<=address<VBASE+0x100:return
 sp=g.u.reg_read(UC_X86_REG_ESP);receiver=g.u.reg_read(UC_X86_REG_ECX)
 configuration={0x420370:(1,0,0),0x4208e0:(4,16,receiver),0x420a10:(2,8,receiver),0x4b45f0:(4,16,receiver),0x461a00:(6,0,0)}
 if VBASE<=address<VBASE+0x100:
  slot=(address-VBASE)*4;has_arg=slot in(0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x5c,0x6c,0x70)
  configuration[address]=(1 if has_arg else 0,4 if has_arg else 0,receiver)
 n,pop,receiver=configuration[address];event=(address,receiver,tuple(g.m.read_words(sp+4,n)),None);s=g.snapshot();g.original_events.append((event,bytes(s)));result=effects(s,event);g.write(s);g.returned(pop,result)
g.u.hook_add(UC_HOOK_CODE,host)
def fresh():
 s,c=g.fresh();x=Extra();x.attackerToken=AX;x.resources=resources;x.resourceCount=len(resources)
 x.attackerActor[:]=[g.rng.getrandbits(32)for _ in range(128)];x.playerPrivate[:]=[g.rng.getrandbits(32)for _ in range(78)]
 x.playerPrivate[0]=g.rng.randrange(2);x.playerPrivate[0xe8//4]=g.rng.randrange(4);x.strikeCounter=g.rng.randrange(3);x.audioEnabled=g.rng.randrange(2);x.audioPosition=g.rng.getrandbits(32)
 s.actor[0x74//4]=AX;s.primary[0x18//4]=g.E
 s.enemy[0x19c//4]=g.rng.randrange(4);s.enemy[0x3d0//4]=max(0,c.tick-100);s.enemy[0x3d4//4]=g.rng.choice([0,100,101])
 s.enemy[0x3d8//4]=s.enemy[0x3e0//4]=s.enemy[0x3f0//4]=max(0,c.tick-1000)
 s.enemy[0x3dc//4]=s.enemy[0x3e4//4]=s.enemy[0x3f4//4]=g.rng.choice([0,999,1000,1001])
 s.enemy[0x24//4]=g.rng.randrange(len(g.names));s.enemy[0x304//4]=g.rng.randrange(5)
 for o in(0x1a4,0x19c):s.actor[o//4]=g.rng.randrange(2)
 s.actor[0x40//4]=g.rng.choice([0,2,8,10]);s.actor[0x10c//4]=g.rng.choice([-1,0,1,10])&0xffffffff
 x.attackerActor[0x104//4]=g.rng.choice([0,1,5,100,0xffffffff]);x.attackerActor[0xd0//4]=g.rng.choice([2,0x10,0x20,0x1000,0x1000000,0x2000000,0])
 x.attackerActor[0x50//4]=g.rng.randrange(-500,501)&0xffffffff
 for o in(0x138,0x13c,0x144):x.attackerActor[o//4]=g.rng.randrange(-50,51)&0xffffffff
 if g.rng.randrange(3)==0:x.attackerActor[0x138//4]=0x80000000
 for i,o in enumerate([0x38c,0x3a0,0x3a4,0x3a8,0x3ac,0x3b0,0x3b8]):s.enemy[o//4]=resources[i].token if g.rng.randrange(2)else 0
 for slot in(0x14,0x18,0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x44,0x5c,0x78,0x8c):c.virtualFunctions[slot//4]=VBASE+slot//4
 c.playerActor[0x16c//4]=g.rng.choice([0,42,43]);s.enemy[0x1a0//4]=g.rng.randrange(2);s.enemy[0x18c//4]=g.rng.choice([2,3])
 for o in(0x118,0x128,0x138):
  if g.rng.randrange(3)==0:s.actor[o//4]=0x80000000
 return s,c,x
def install(s,c,x):
 g.install(s,c);write_extra(x);g.m.write_words(g.P+0x6c,[PLAYER_LOGIC]);g.m.write_words(PLAYER_LOGIC+0x14,[PLAYER_PRIVATE])
 for view in resources:g.m.write_words(view.token+0x10,[view.controllerToken])
def compare(s,c,x,entry,label,arg=0,dispatch=None):
 global extra,common_context,native,random_index,calls,events
 before=bytes(s);old_x=bytes(x);extra=x;common_context=c;old_backing=tuple(c.bitWords[i]for i in range(c.bitWordCount));native=True;g.native_events.clear();g.tile_index=0;random_index=0
 if dispatch is None:result=lib.claw_generic_enemy_state_entry(C.byref(s),C.byref(c),C.byref(x),entry,arg,dependency,None)
 else:result=lib.claw_generic_enemy_state_dispatch(C.byref(s),C.byref(c),C.byref(x),dispatch,dependency,None)
 assert result==1,(label,'native rejection');expected=bytes(s);expected_x=bytes(x);expected_events=list(g.native_events);expected_backing=tuple(c.bitWords[i]for i in range(c.bitWordCount))
 for i,v in enumerate(old_backing):c.bitWords[i]=v
 C.memmove(C.byref(x),old_x,C.sizeof(x));install(g.Enemy.from_buffer_copy(before),c,x);native=False;g.original_events.clear();g.tile_index=0;random_index=0
 actual_entry=0x43d490 if dispatch is not None else entry
 if dispatch is not None:args=struct.pack('<I',dispatch)
 elif entry in(0x4dc830,0x4dc850):args=struct.pack('<I',g.A)
 elif entry in(0x43f120,0x43e9c0,0x404dd0,0x404eb0,0x440e20):args=struct.pack('<I',arg)
 else:args=b''
 try:g.m.call(actual_entry,g.E,args)
 except Exception:print('original failure',label,hex(g.u.reg_read(UC_X86_REG_EIP)));raise
 actual=bytes(g.snapshot());actual_x=bytes(read_extra())
 if c.bitWordCount:assert tuple(g.m.read_words(g.BITS,c.bitWordCount))==expected_backing,(label,"complete bit backing")
 if actual!=expected or actual_x!=expected_x:
  for name in g.sizes:
   values=g.m.read_words(g.addresses[name],g.sizes[name]);want=getattr(s,name);diff=[(hex(i*4),hex(a),hex(b))for i,(a,b)in enumerate(zip(values,want))if a!=b]
   if diff:print(label,name,diff[:30])
  if actual_x!=expected_x:print('extra mismatch',label,[(hex(i),a,b)for i,(a,b)in enumerate(zip(actual_x,expected_x))if a!=b][:20])
  raise AssertionError((label,'complete buffers/global mismatch'))
 if list(g.original_events)!=expected_events:
  print(label,'original',[(r[0])for r in g.original_events]);print('native',[(r[0])for r in expected_events])
  for i,(a,b)in enumerate(zip(g.original_events,expected_events)):
   if a!=b:print('first event mismatch',i,a[0],b[0]);break
  raise AssertionError((label,'ordered complete-snapshot events mismatch'))
 C.memmove(C.byref(x),expected_x,C.sizeof(x))
 for i,v in enumerate(expected_backing):c.bitWords[i]=v
 calls+=1;events+=len(expected_events)
