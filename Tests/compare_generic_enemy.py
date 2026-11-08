#!/usr/bin/env python3
"""Hash-pinned original common enemy routines, complete snapshots and events."""
import argparse,ctypes as C,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');options=p.parse_args()
scratch=ROOT/'work/generic-enemy-agent';scratch.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-O2','-dynamiclib',str(ROOT/'Sources/GenericEnemy.cpp'),str(ROOT/'Sources/PlayerPhysics.cpp'),'-o',str(scratch/'libGenericEnemy.dylib')],check=True)
class Enemy(C.Structure):_fields_=[(n,C.c_uint32*k)for n,k in [('actor',128),('primary',93),('secondary',93),('contact',93),('enemy',264)]]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',C.c_uint32),('nameToken',C.c_uint32),('name',C.c_char_p)]
class Context(C.Structure):_fields_=[(x,C.c_uint32)for x in ['actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken']]+[(x,C.c_uint32*128)for x in ['playerActor','platformActor']]+[(x,C.c_uint32)for x in ['tick','animationDelta','levelWord','forcedRandom','hitMode']]+[('defaults',C.c_uint32*24),('virtualFunctions',C.c_uint32*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(C.c_uint32)),('bitWordCount',C.c_size_t),('emptyStringToken',C.c_uint32),('bitHandlerToken',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*12),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Enemy),C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(scratch/'libGenericEnemy.dylib'))
for name in ['construct','tick','pre','post','motion']:
 f=getattr(lib,'claw_generic_enemy_'+name);f.argtypes=[C.POINTER(Enemy),C.POINTER(Context),Dependency,C.c_void_p];f.restype=C.c_uint32
lib.claw_generic_enemy_entry.argtypes=[C.POINTER(Enemy),C.POINTER(Context),C.c_uint32,C.c_uint32,Dependency,C.c_void_p];lib.claw_generic_enemy_entry.restype=C.c_uint32
lib.claw_generic_enemy_dispatch.argtypes=[C.POINTER(Enemy),C.POINTER(Context),C.c_int32,Dependency,C.c_void_p];lib.claw_generic_enemy_dispatch.restype=C.c_uint32
lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(Context)]
m=OriginalV10(options.exe);u=m.u;u.mem_map(0,4096);m.executed.clear()
A,L,S,K,E,P,PL,SC,T,R=[0x1001000+i*0x1000 for i in range(10)]
VT,FUNCTIONS,STRINGS,STRING_OBJECTS,EMPTY,BITS=0x1010000,0x1011000,0x1012000,0x1013000,0x1014000,0x1015000
names=[b'LS_MOVINGLEFT',b'LS_MOVINGRIGHT',b'LS_FALLING',b'LS_DEAD',b'LS_HOME',b'LS_TEST']
functions=[0x43fd10,0x43fdc0,0x43edd0,0,0,0x10fe000]
states=(State*len(names))(*[State(i,f,STRINGS+64*i,n)for i,(n,f)in enumerate(zip(names,functions))])
virtuals=m.read_words(0x50b16c,64)
# Generic vtable override hooks use private sentinel callbacks, preserving the
# original dispatch ABI while testing mutations across pre/state/post ordering.
VIRTUAL_BASE=0x10fd000
original_events=[];native_events=[];policy=0;collision=0;tile_values=[];tile_index=0;random_value=0;total=0;event_total=0
current_context=None
sizes={'actor':128,'primary':93,'secondary':93,'contact':93,'enemy':264}
addresses={'actor':A,'primary':L,'secondary':S,'contact':K,'enemy':E}
def text(a):return bytes(u.mem_read(a,128)).split(b'\0')[0]
def load(buffer,o):return struct.unpack_from('<d',bytes(buffer),o)[0]
def store(buffer,o,v):
 b=struct.pack('<d',v);buffer[o//4:o//4+2]=struct.unpack('<2I',b)
def snapshot():
 s=Enemy()
 for name in sizes:getattr(s,name)[:]=m.read_words(addresses[name],sizes[name])
 return s
def write(s):
 for name in sizes:m.write_words(addresses[name],getattr(s,name))
def effects(s,event):
 global tile_index
 f,receiver,args,name=event
 if f==0x4cbb60:
  s.actor[0x4c//4]=(args[1]+(2 if policy==1 else 0))&0xffffffff
  s.actor[0x50//4]=(args[2]+(-3 if policy==1 else 0))&0xffffffff
  return collision
 if f==0x4207f0:
  result=tile_values[tile_index%len(tile_values)]if tile_values else 0;tile_index+=1;return result
 if f==0x4a3050:return random_value
 if f==0x4dba00:return names.index(name)
 if f==0x4f6286:return 0x1020000+names_resource.index(name)*0x100 if policy==1 else 0
 if VIRTUAL_BASE<=f<VIRTUAL_BASE+0x100 or f==0x10fe000:
  s.enemy[0x328//4]^=f
  if policy==2:
   s.primary[7]=(s.primary[7]+1)%len(names)
   s.enemy[0x1c//4]=s.primary[7]
  return 0
 return 0
names_resource=[b'GAME_SPLASH',b'GAME_HIT1',b'GAME_HIT2',b'GAME_HIT3',b'GAME_HIT4',b'GAME_PURELEASE1']
@Dependency
def dependency(s,c,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name)
 native_events.append((event,bytes(s.contents)));return effects(s.contents,event)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
 u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
 global tile_index
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x10fb000:
  rect=m.read_words(sp+4,1)[0];m.write_words(rect,[0]*4);returned(4,1);return
 if address==0x10fb010:
  rect,*values=m.read_words(sp+4,5);m.write_words(rect,values);returned(20,1);return
 if address==0x10fb020:
  rect,x,y=m.read_words(sp+4,3);left,top,right,bottom=[C.c_int32(v).value for v in m.read_words(rect,4)]
  x,y=C.c_int32(x).value,C.c_int32(y).value;returned(12,int(left<=x<right and top<=y<bottom));return
 if address in (0x4c7fa0,0x4c8060):
  name=text(m.read_words(sp+4,1)[0]);event=(address,receiver,(),name);original_events.append((event,bytes(snapshot())));return
 if address==0x4dba00:
  name=text(m.read_words(sp+4,1)[0]);event=(address,receiver,(),name);s=snapshot();original_events.append((event,bytes(s)));result=effects(s,event);write(s);returned(4,result);return
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);name=text(name)
  if name in (b'LogicHit',b'LogicAttack'):m.write_words(out,[0]);returned(8,0);return
  event=(address,receiver,(),name);s=snapshot();original_events.append((event,bytes(s)));result=effects(s,event);write(s);m.write_words(out,[result]);returned(8,1 if result else 0);return
 config={0x4cbb60:(4,16),0x4207f0:(2,8),0x4a3050:(0,0),0x4c82a0:(1,4),0x4c8220:(1,4),0x4a36f0:(1,0),0x48cf50:(1,0)}
 if VIRTUAL_BASE<=address<VIRTUAL_BASE+0x100:
  slot=(address-VIRTUAL_BASE)*4;config[address]=(1 if slot in(4,8,12,0x5c,0x6c,0x70)else 0,4 if slot in(4,8,12,0x5c,0x6c,0x70)else 0)
 if address==0x10fe000:config[address]=(0,0)
 if address not in config:return
 n,pop=config[address];args=tuple(m.read_words(sp+4,n));receiver=0 if address in(0x4a3050,0x4a36f0,0x48cf50)else receiver
 event=(address,receiver,args,None);s=snapshot();original_events.append((event,bytes(s)));result=effects(s,event);write(s);returned(pop,result)
u.hook_add(UC_HOOK_CODE,host)
rng=random.Random(4332)
def fresh():
 s=Enemy();c=Context()
 for name in sizes:getattr(s,name)[:]=[rng.getrandbits(32)for _ in range(sizes[name])]
 c.actorToken,c.primaryToken,c.secondaryToken,c.contactToken,c.enemyToken=A,L,S,K,E
 c.sceneToken,c.tileManagerToken,c.soundRegistryToken,c.playerToken=SC,T,R,P
 c.tick=rng.randrange(0,10000);c.animationDelta=rng.randrange(0,40);c.levelWord=rng.choice([0,0x26b7]);c.forcedRandom=rng.randrange(2);c.hitMode=rng.randrange(3)
 lib.claw_generic_enemy_context_defaults(C.byref(c));c.emptyStringToken=EMPTY;c.states=states;c.stateCount=len(states)
 c.virtualFunctions[:]=virtuals
 for slot in(0x44,0x48,0x5c,0x6c,0x70):c.virtualFunctions[slot//4]=VIRTUAL_BASE+slot//4
 c.virtualFunctions[8//4]=0x43d490
 s.actor[0x6c//4]=L;s.actor[0x70//4]=S;s.actor[0x78//4]=K;s.actor[0xc//4]=SC;s.actor[0x80//4]=PL
 s.enemy[0]=VT;s.enemy[2]=s.enemy[3]=s.enemy[0x128//4]=s.enemy[0x12c//4]=s.enemy[0x194//4]=A;s.enemy[4]=s.enemy[0x198//4]=L
 s.enemy[0x2fc//4]=32;s.enemy[0x300//4]=rng.randrange(32);s.enemy[5]=s.enemy[6]=0
 s.primary[7]=rng.randrange(len(names));s.enemy[7]=rng.randrange(len(names))
 s.actor[2]=rng.choice([0,0x10]);s.actor[0xcc//4]=rng.choice([1,2,7]);s.actor[0x38//4]=rng.choice([0,0xffffffff]);s.actor[0x4c//4]=rng.randrange(-500,500)&0xffffffff;s.actor[0x50//4]=rng.randrange(-500,500)&0xffffffff
 for o in(0x118,0x120,0x124):s.actor[o//4]=rng.randrange(-30,31)&0xffffffff
 for o in(0x4c,0x50,0x124):c.playerActor[o//4]=rng.randrange(-600,601)&0xffffffff
 for o in(0x158,0x15c):c.platformActor[o//4]=rng.randrange(-3,4)&0xffffffff
 # Valid, finite embedded physics. Preserve arbitrary fields outside it.
 for o in range(0x28,0x118,8):store(s.enemy,o,0)
 store(s.enemy,0x28,float(c.tick)*0.001-0.016)
 for o in(0x38,0x40,0x48):store(s.enemy,o,rng.choice([0.,-100.,100.,2250.]))
 for o in(0x50,0x58,0x60):store(s.enemy,o,rng.uniform(-100,100))
 for axis in range(3):
  store(s.enemy,0x68+axis*8,float(C.c_int32(s.actor[(0x4c+axis*4)//4]).value)if axis<2 else 0.)
  store(s.enemy,0x80+axis*8,-1000.);store(s.enemy,0x98+axis*8,1000.)
  store(s.enemy,0xe8+axis*8,24.);store(s.enemy,0x100+axis*8,1000.)
 s.enemy[0xc8//4]=rng.randrange(2);s.enemy[0x124//4]=rng.randrange(4)
 for o in range(0x28c,0x2b4,8):s.enemy[o//4]=rng.randrange(0,500);s.enemy[(o+4)//4]=rng.randrange(0,100)
 s.enemy[0x188//4]=rng.randrange(2);s.enemy[0x3c8//4]=max(0,c.tick-600);s.enemy[0x3cc//4]=500
 return s,c
def install(s,c):
 m.write_words(0x546cdc,[0x10fb000]);m.write_words(0x546d5c,[0x10fb010]);m.write_words(0x546cd4,[0x10fb020])
 write(s);m.write_words(VT,c.virtualFunctions);
 if s.enemy[0x2fc//4]>32:m.write_words(BITS,[c.bitWords[i]for i in range(c.bitWordCount)])
 m.write_words(P,c.playerActor);m.write_words(PL,c.platformActor)
 m.write_words(SC+0x24,[T,R-0x10]);m.write_words(SC+0x14,[R-0x10]);m.write_words(SC+0x28,[R-0x10])
 m.write_words(0x537e88,[P]);m.write_words(0x537210,[c.tick]);m.write_words(0x5430c4,[c.animationDelta]);m.write_words(0x534eac,[c.levelWord]);m.write_words(0x541334,[c.forcedRandom]);m.write_words(0x537960,[0x1016000]);m.write_words(0x1016000+0x44,[c.hitMode]);m.write_words(0x513e10,c.defaults)
 m.write_words(0x52e1cc,[c.emptyStringToken]);m.write_words(0x533470,[32]);u.mem_write(0x534938,b'\0')
 m.write_words(0x537638+8,[0,len(names)-1,FUNCTIONS,0,4,0,0,0])
 m.write_words(FUNCTIONS,functions)
 m.write_words(0x537698+8,[0,len(names)-1,STRING_OBJECTS,0,4,0,0,0])
 for i,n in enumerate(names):
  token=STRINGS+64*i;m.write_words(STRING_OBJECTS+4*i,[token]);m.write_words(token-12,[1,len(n),len(n)]);u.mem_write(token,n+b'\0')
def compare(s,c,entry,label,arg=0):
 global tile_index,total,event_total
 before=bytes(s);native_events.clear();tile_index=0
 if entry==0x4332f0:result=lib.claw_generic_enemy_construct(C.byref(s),C.byref(c),dependency,None)
 elif entry==0x4dc870:result=lib.claw_generic_enemy_tick(C.byref(s),C.byref(c),dependency,None)
 else:result=lib.claw_generic_enemy_entry(C.byref(s),C.byref(c),entry,arg,dependency,None)
 assert result==1,(label,'native rejection');expected=bytes(s);expected_events=list(native_events);old=Enemy.from_buffer_copy(before);install(old,c);original_events.clear();tile_index=0
 args=struct.pack('<I',A)if entry==0x4332f0 else struct.pack('<I',E)if entry==0x4dc870 else struct.pack('<I',arg)if entry in (0x43d490,0x404fc0,0x4063b0,0x43fcb0,0x43fd60)else b''
 try:m.call(entry,E,args)
 except Exception:
  print("FAIL original",label,hex(u.reg_read(UC_X86_REG_EIP)),m.read_words(u.reg_read(UC_X86_REG_ESP),8));raise
 actual=bytes(snapshot())
 if actual!=expected:
  for name in sizes:
   actual_words=m.read_words(addresses[name],sizes[name]);expected_words=getattr(s,name)
   diff=[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(actual_words,expected_words))if x!=y]
   if diff:print(label,name,diff[:25])
  raise AssertionError((label,'complete buffer mismatch'))
 if original_events!=expected_events:
  print(label,'original events',[(x,len(y))for x,y in original_events]);print('native events',[(x,len(y))for x,y in expected_events])
  for index,(x,y)in enumerate(zip(original_events,expected_events)):
   if x!=y:print('first mismatch',index,x[0],y[0]);break
  raise AssertionError((label,'ordered complete-snapshot events mismatch'))
 total+=1;event_total+=len(original_events)

if __name__=='__main__':
 for entry in (0x4332f0,0x4dca10,0x43e420,0x43dfa0,0x404fc0,0x4063b0,0x43fd10,0x43fdc0,0x43edd0,0x43fcb0,0x43fd60,0x4bb030,0x43e9b0,0x43d490,0x4dc870):
  for n in range(200):
   s,c=fresh();policy=n%3;collision=rng.choice([0,0x800000,0x40000,0x80000,0x100000,0x1c0000]);random_value=rng.randrange(0x7fffffff);tile_values=[rng.randrange(5)for _ in range(4)]
   if entry==0x4332f0:
    s.actor[0x148//4]=rng.randrange(-100,101)&0xffffffff;s.actor[0x14c//4]=rng.randrange(-100,101)&0xffffffff
    for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=rng.choice([0,-400,400])&0xffffffff
   if entry==0x4063b0 and n%2:s.enemy[5]=0x10fe000;s.enemy[6]=0x10fe000;s.enemy[7]=s.primary[7]
   compare(s,c,entry,(hex(entry),n),rng.randrange(len(names)))
  print('PASS200',hex(entry),'complete buffers/events',flush=True)
 print(f'PASS {total} complete original calls; {event_total} ordered dependency events with complete snapshots; {len(m.executed)} original instruction addresses')

 # Directed endpoint callbacks and signed walk-start speeds, including the
 # original INT_MIN unary-negation wrap. These activate rarely reached paths.
 directed=0
 for entry in(0x43fcb0,0x43fd60):
  for speed in(0,1,60,0x7fffffff,0x80000000,0xffffffff):
   s,c=fresh();policy=0;collision=0;compare(s,c,entry,('signed-start',entry,speed),speed);directed+=1
 for entry,bound in((0x43fd10,0x80),(0x43fdc0,0x98)):
  for y in(-100.75,-1.25,0.,1.25,100.75):
   s,c=fresh();policy=2;store(s.enemy,bound,load(s.enemy,0x68));store(s.enemy,0x70,y)
   compare(s,c,entry,('endpoint',entry,y));directed+=1
 # Sensing selects inner regions first and follows Win32 right/bottom-exclusive
 # point inclusion, independently of the inclusive actor-interaction boxes.
 for x in(-401,-400,-301,-300,-201,-200,-101,-100,-1,0,1,99,100,199,200,299,300,399,400):
  for y in(-50,-49,0,49,50):
   s,c=fresh();policy=0;c.levelWord=0;s.enemy[0x300//4]=0;s.actor[0x38//4]=0
   store(s.enemy,0x68,0);store(s.enemy,0x70,0);store(s.enemy,0x80,-1000);store(s.enemy,0x98,1000)
   for i in range(5):s.enemy[(0x28c+i*8)//4]=400-i*100;s.enemy[(0x290+i*8)//4]=50
   c.playerActor[0x4c//4]=x&0xffffffff;c.playerActor[0x50//4]=y&0xffffffff
   compare(s,c,0x43e420,('sense-edge',x,y));directed+=1
 for elapsed in(0,1,499,500,501,0xffffffff):
  s,c=fresh();policy=0;c.levelWord=0;s.enemy[0x300//4]=0;s.actor[0x38//4]=0
  c.playerActor[0x4c//4]=1000000;c.playerActor[0x50//4]=1000000
  s.enemy[0x188//4]=1;s.enemy[0x3cc//4]=500;s.enemy[0x3c8//4]=(c.tick-elapsed)&0xffffffff
  compare(s,c,0x43e420,('unsigned-delay',elapsed));directed+=1
 # Separate complete FSM proof with controlled pre/state/post overrides; each
 # changes primary state. The engine must continue using its captured old ID.
 for old_state in range(len(names)):
  s,c=fresh();policy=2;s.primary[7]=old_state
  for slot in(4,8,12):c.virtualFunctions[slot//4]=VIRTUAL_BASE+slot//4
  compare(s,c,0x4dc870,('captured-state',old_state));directed+=1
 # Queued cleanup is tested both with matching/nonmatching captured state and
 # with null cleanup callbacks; state-transition callback is still mandatory.
 for cleanup in(0,0x10fe000):
  for same in(False,True):
   s,c=fresh();policy=2;s.enemy[5]=0x10fe000;s.enemy[6]=cleanup
   s.enemy[7]=s.primary[7]if same else(s.primary[7]+1)%len(names)
   compare(s,c,0x4063b0,('queued',cleanup,same));directed+=1
 # Retain complete buffers across common walk-start -> update/post ticks.
 # Resource/collision/animation adapters remain exactly logged dependencies.
 chains=0
 for history in range(32):
  s,c=fresh();policy=0;collision=0;tile_values=[0]
  c.tick=100;s.actor[2]=0;s.actor[0xcc//4]=2
  compare(s,c,0x4332f0,('chain-base',history));chains+=1
  s.enemy[0]=VT;s.enemy[0x2fc//4]=32;s.enemy[0x300//4]=0;c.forcedRandom=1
  for slot in(0x6c,0x70):c.virtualFunctions[slot//4]=0x43fcb0 if slot==0x6c else 0x43fd60
  compare(s,c,0x43fcb0 if history%2 else 0x43fd60,('chain-start',history),60);chains+=1
  for step in range(16):
   c.tick+=16;compare(s,c,0x4dc870,('chain-tick',history,step));chains+=1
 for count in(0,1,2,3,4,5,32,33,64):
  for bits_value in(0,1,2,4,8,16,31):
   for entry in(0x43e420,0x43dfa0):
    s,c=fresh();policy=0;collision=0;tile_values=[0];s.enemy[0x2fc//4]=count
    backing=(C.c_uint32*2)(bits_value,0x12345678);c.bitWords=backing;c.bitWordCount=2
    s.enemy[0x300//4]=BITS if count>32 else bits_value
    compare(s,c,entry,('bit-storage',count,bits_value,entry));directed+=1
    if count>32:assert m.read_words(BITS,2)==list(backing),'bit backing preserved'
 print(f'PASS {directed} directed cases and {chains} retained-buffer chain calls; total {total} complete original calls; {event_total} ordered full-snapshot events; {len(m.executed)} original instruction addresses')
