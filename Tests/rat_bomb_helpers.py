#!/usr/bin/env python3
"""Hash-pinned original common enemy routines, complete snapshots and events."""
import argparse,ctypes as C,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');options=p.parse_args()
scratch=ROOT/'work/rat-bomb-agent';scratch.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-O2','-dynamiclib',str(ROOT/'Sources/RatBombLogic.cpp'),str(ROOT/'Sources/RatLogic.cpp'),str(ROOT/'Sources/WorldObjectRuntime.cpp'),str(ROOT/'Sources/GenericEnemy.cpp'),str(ROOT/'Sources/PlayerPhysics.cpp'),str(ROOT/'Sources/CollisionResponse.cpp'),str(ROOT/'Sources/TileCollision.cpp'),'-o',str(scratch/'libRatBomb.dylib')],check=True)
class Enemy(C.Structure):_fields_=[(n,C.c_uint32*k)for n,k in [('actor',128),('primary',93),('secondary',93),('contact',93),('enemy',264)]]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',C.c_uint32),('nameToken',C.c_uint32),('name',C.c_char_p)]
class GenericContext(C.Structure):_fields_=[(x,C.c_uint32)for x in ['actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken']]+[(x,C.c_uint32*128)for x in ['playerActor','platformActor']]+[(x,C.c_uint32)for x in ['tick','animationDelta','levelWord','forcedRandom','hitMode']]+[('defaults',C.c_uint32*24),('virtualFunctions',C.c_uint32*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(C.c_uint32)),('bitWordCount',C.c_size_t),('emptyStringToken',C.c_uint32),('bitHandlerToken',C.c_uint32)]
class Context(GenericContext):
 _fields_=[('sequenceRegistryToken',C.c_uint32),('damageScale',C.c_float),('imageMinimum',C.c_int32),('imageMaximum',C.c_int32),('minimumImageToken',C.c_uint32),('imageHeader',C.c_uint32*16),('audioManagerAvailable',C.c_uint32),('masterVolume',C.c_uint32),('bounceSoundPoolToken',C.c_uint32),('explosionSoundPoolToken',C.c_uint32),('fault',C.c_uint32)]
class Rect(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('left','top','right','bottom')]
class Actor(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('flags','x','y','mode','type','stepX','stepY','supportToken','token','deltaX','deltaY')]+[('moveRect',Rect),('hitRect',Rect)]
class Description(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('type','width','height','insideAttribute','outsideAttribute')]+[(n,C.c_int32)for n in ('left','top','right','bottom')]
class World(C.Structure):
    _fields_=[('cells',C.POINTER(C.c_uint32)),('rowOffsets',C.POINTER(C.c_uint32)),('width',C.c_int32),('height',C.c_int32),('shiftX',C.c_uint32),('shiftY',C.c_uint32),('descriptions',C.POINTER(Description)),('descriptionCount',C.c_uint32),('actors',C.POINTER(Actor)),('actorCount',C.c_uint32),('maximumStepX',C.c_uint32),('maximumStepY',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*12),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Enemy),C.POINTER(GenericContext),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(scratch/'libRatBomb.dylib'))
for name in ['construct','tick','pre','post','motion']:
 f=getattr(lib,'claw_generic_enemy_'+name);f.argtypes=[C.POINTER(Enemy),C.POINTER(GenericContext),Dependency,C.c_void_p];f.restype=C.c_uint32
lib.claw_generic_enemy_entry.argtypes=[C.POINTER(Enemy),C.POINTER(GenericContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p];lib.claw_generic_enemy_entry.restype=C.c_uint32
lib.claw_generic_enemy_dispatch.argtypes=[C.POINTER(Enemy),C.POINTER(GenericContext),C.c_int32,Dependency,C.c_void_p];lib.claw_generic_enemy_dispatch.restype=C.c_uint32
lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(GenericContext)]
lib.claw_rat_bomb_context_defaults.argtypes=[C.POINTER(Context)]
for name in ['construct','tick']:
 f=getattr(lib,'claw_rat_bomb_'+name);f.argtypes=[C.POINTER(Enemy),C.POINTER(Context),Dependency,C.c_void_p];f.restype=C.c_uint32
lib.claw_rat_bomb_entry.argtypes=[C.POINTER(Enemy),C.POINTER(Context),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_rat_bomb_entry.restype=C.c_uint32
m=OriginalV10(options.exe);u=m.u;u.mem_map(0,4096);m.executed.clear()
A,L,S,K,E,P,PL,SC,T,R=[0x1001000+i*0x1000 for i in range(10)]
VT,FUNCTIONS,STRINGS,STRING_OBJECTS,EMPTY,BITS=0x1010000,0x1011000,0x1012000,0x1013000,0x1014000,0x1015000
names=[b'LS_FALLING',b'LS_EXPLODING',b'LS_TEST']
functions=[0x4742f0,0,0x10fe000]
states=(State*len(names))(*[State(2000+i,f,STRINGS+64*i,n)for i,(n,f)in enumerate(zip(names,functions))])
virtuals=m.read_words(0x50f13c,12)+[0]*52
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
  if realCollision:
   v=Actor();fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
   for name,offset in fields.items():setattr(v,name,s.actor[offset//4])
   v.token=1;v.moveRect=Rect(*s.actor[0x118//4:0x128//4]);v.hitRect=Rect(*s.actor[0x128//4:0x138//4])
   rr=lib.claw_collision_resolve(C.byref(world),C.byref(v),args[1],args[2],args[3])
   for name,offset in fields.items():s.actor[offset//4]=getattr(v,name)
   return rr
  s.actor[0x4c//4]=(args[1]+(2 if policy==1 else 0))&0xffffffff
  s.actor[0x50//4]=(args[2]+(-3 if policy==1 else 0))&0xffffffff
  return collision
 if f==0x4207f0:
  result=tile_values[tile_index%len(tile_values)]if tile_values else 0;tile_index+=1;return result
 if f==0x4a3050:return random_value
 if f==0x4dba00:return 2000+names.index(name)
 if f==0x4f6286:return 0x1020000+names_resource.index(name)*0x100 if policy==1 else 0
 if f==0x4c7970:
  s.actor[0x170//4]=IMAGE_MANAGER if policy==1 else 0;return 0
 if f==0x40f680:return IMAGE if policy==1 else 0
 if f==0x4c82a0:return marker
 if f==0x4b45f0:return 0
 if f==0x4f63ec:return E
 if VIRTUAL_BASE<=f<VIRTUAL_BASE+0x100 or f==0x10fe000:
  s.enemy[0x328//4]^=f
  if policy==2:
   s.primary[7]=(s.primary[7]+1)%len(names)
   s.enemy[0x1c//4]=s.primary[7]
  return 0
 return 0
names_resource=[b'LEVEL_RATBOMB_FALL',b'LEVEL_RATBOMB_FALLEASTWEST',b'LEVEL_RATBOMB_EXPLODE',b'LEVEL_RATBOMB_BOUNCE',b'GAME_BOINKJR',b'GAME_BOMBEXP']
IMAGE_MANAGER,IMAGE,R2,OBJ= [0x1030000+i*0x1000 for i in range(4)]
query_value=marker=0
realGround=False;realCollision=False;collisionReturn=None;world=None
lib.claw_collision_place_on_ground.argtypes=[C.POINTER(World),C.POINTER(Actor)];lib.claw_collision_place_on_ground.restype=C.c_uint32
lib.claw_collision_resolve.argtypes=[C.POINTER(World),C.POINTER(Actor),C.c_uint32,C.c_uint32,C.c_uint32];lib.claw_collision_resolve.restype=C.c_uint32
@Dependency
def dependency(s,c,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name)
 native_events.append((event,bytes(s.contents)));return effects(s.contents,event)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
 u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
 global tile_index,collisionReturn
 if collisionReturn==address:collisionReturn=None
 if collisionReturn is not None and address!=0x4cbb60 and address not in(0x10fb000,0x10fb010,0x10fb020):return
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x10fb030:
  rect,dx,dy=m.read_words(sp+4,3);left,top,right,bottom=m.read_words(rect,4);values=[(left-dx)&0xffffffff,(top-dy)&0xffffffff,(right+dx)&0xffffffff,(bottom+dy)&0xffffffff];m.write_words(rect,values);returned(12,1);return
 if address==0x10fb000:
  rect=m.read_words(sp+4,1)[0];m.write_words(rect,[0]*4);returned(4,1);return
 if address==0x10fb010:
  rect,*values=m.read_words(sp+4,5);m.write_words(rect,values);returned(20,1);return
 if address==0x10fb020:
  rect,x,y=m.read_words(sp+4,3);left,top,right,bottom=[C.c_int32(v).value for v in m.read_words(rect,4)]
  x,y=C.c_int32(x).value,C.c_int32(y).value;returned(12,int(left<=x<right and top<=y<bottom));return
 if address in (0x4c7fa0,0x4c8060,0x4c7970):
  name=text(m.read_words(sp+4,1)[0]);event=(address,receiver,(),name);original_events.append((event,bytes(snapshot())));
  if address==0x4c7970:
   ss=snapshot();effects(ss,event);write(ss);returned(4,1)
  return
 if address==0x4dba00:
  name=text(m.read_words(sp+4,1)[0]);event=(address,receiver,(),name);s=snapshot();original_events.append((event,bytes(s)));result=effects(s,event);write(s);returned(4,result);return
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);name=text(name)
  if name in (b'LogicHit',b'LogicAttack'):m.write_words(out,[0]);returned(8,0);return
  event=(address,receiver,(),name);s=snapshot();original_events.append((event,bytes(s)));result=effects(s,event);write(s);m.write_words(out,[result]);returned(8,1 if result else 0);return
 config={0x4cbb60:(4,16),0x4207f0:(2,8),0x4a3050:(0,0),0x4c82a0:(1,4),0x4c8220:(1,4),0x4a36f0:(1,0),0x48cf50:(1,0),0x40f680:(1,4),0x4b45f0:(4,16),0x4cd800:(2,8),0x4cda10:(4,16),0x4f63ec:(1,0),0x4f6428:(1,0),0x43f120:(1,4),0x404f00:(0,0)}
 if VIRTUAL_BASE<=address<VIRTUAL_BASE+0x100:
  slot=(address-VIRTUAL_BASE)*4;config[address]=(1 if slot in(4,8,12,0x5c,0x6c,0x70)else 0,4 if slot in(4,8,12,0x5c,0x6c,0x70)else 0)
 if address==0x10fe000:config[address]=(0,0)
 if address not in config:return
 n,pop=config[address];args=tuple(m.read_words(sp+4,n));receiver=0 if address in(0x4a3050,0x4a36f0,0x48cf50,0x4f63ec,0x4f6428)else receiver
 event=(address,receiver,args,None);s=snapshot();original_events.append((event,bytes(s)));
 if address==0x4cd800 and realGround:return
 if address==0x4cbb60 and realCollision:
  collisionReturn=m.read_words(sp,1)[0];return
 result=effects(s,event);write(s)
 returned(pop,result)
host_handle=u.hook_add(UC_HOOK_CODE,host)
rng=random.Random(4332)
def fresh():
 s=Enemy();c=Context()
 for name in sizes:getattr(s,name)[:]=[rng.getrandbits(32)for _ in range(sizes[name])]
 c.actorToken,c.primaryToken,c.secondaryToken,c.contactToken,c.enemyToken=A,L,S,K,E
 c.sceneToken,c.tileManagerToken,c.soundRegistryToken,c.playerToken=SC,T,R,P
 c.tick=rng.randrange(0,10000);c.animationDelta=rng.randrange(0,40);c.levelWord=rng.choice([0,0x26b7]);c.forcedRandom=rng.randrange(2);c.hitMode=rng.randrange(3)
 lib.claw_rat_bomb_context_defaults(C.byref(c));c.emptyStringToken=EMPTY;c.states=states;c.stateCount=len(states)
 c.virtualFunctions[:]=virtuals
 # Preserve genuine Rat vtable overrides. Shared hurt remains explicit.
 c.virtualFunctions[8//4]=0x47db20
 s.actor[0x6c//4]=L;s.actor[0x70//4]=S;s.actor[0x78//4]=K;s.actor[0xc//4]=SC;s.actor[0x80//4]=PL
 s.enemy[0]=0x50f13c;s.enemy[2]=s.enemy[3]=s.enemy[0x128//4]=s.enemy[0x12c//4]=s.enemy[0x190//4]=s.enemy[0x194//4]=A;s.enemy[4]=s.enemy[0x130//4]=s.enemy[0x198//4]=L
 s.enemy[0x2fc//4]=32;s.enemy[0x300//4]=rng.randrange(32);s.enemy[5]=s.enemy[6]=0
 s.primary[0xc//4]=SC;s.primary[0x18//4]=E;s.primary[7]=2000+rng.randrange(len(names));s.enemy[7]=2000+rng.randrange(len(names))
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
 c.sequenceRegistryToken=R2;c.imageMinimum=3;c.imageMaximum=3;c.minimumImageToken=IMAGE;c.imageHeader[6]=11;c.imageHeader[7]=12;c.imageHeader[8]=7;c.imageHeader[9]=9
 c.audioManagerAvailable=rng.randrange(2);c.masterVolume=rng.randrange(101);c.bounceSoundPoolToken=0x10ff000;c.explosionSoundPoolToken=0x10ff010
 s.actor[0x170//4]=0;s.actor[0x174//4]=0
 # Unused portable tail is deliberately arbitrary, including the CEnemy guard.
 s.enemy[0x2fc//4]=rng.getrandbits(32)
 return s,c
def install(s,c):
 m.write_words(0x546cdc,[0x10fb000]);m.write_words(0x546d5c,[0x10fb010]);m.write_words(0x546cd4,[0x10fb020])
 write(s);m.write_words(0x50f13c,c.virtualFunctions[:12]);
 if s.enemy[0x2fc//4]>32:m.write_words(BITS,[c.bitWords[i]for i in range(c.bitWordCount)])
 m.write_words(P,c.playerActor);m.write_words(PL,c.platformActor)
 m.write_words(SC+0x24,[T,R-0x10]);m.write_words(SC+0x14,[R-0x10]);m.write_words(SC+0x28,[R-0x10]);m.write_words(SC+0x2c,[R2-0x10]);m.write_words(SC+8,[OBJ])
 m.write_words(IMAGE_MANAGER+0x64,[c.imageMinimum,c.imageMaximum]);m.write_words(IMAGE_MANAGER+0x14,[0x1038000]);m.write_words(0x1038000+4*(c.imageMinimum&0xff),[c.minimumImageToken]);m.write_words(IMAGE,c.imageHeader)
 m.write_words(0x532c0c,[c.audioManagerAvailable]);m.write_words(0x532c10,[c.masterVolume])
 for n in names_resource:m.write_words(0x1020000+names_resource.index(n)*0x100+0x10,[c.bounceSoundPoolToken if n==b'GAME_BOINKJR'else c.explosionSoundPoolToken])
 u.mem_write(0x5262b0,struct.pack('<f',c.damageScale))
 m.write_words(0x546d24,[0x10fb030])
 m.write_words(0,[0x12345678])
 m.write_words(0x53c118+8,[1000,2000+len(names)-1,0x1017000,0,4,0,0,0]);m.write_words(0x1017000,[0]*1000+[0x47e180,0x47dfc0,0])
 m.write_words(0x537e88,[P]);m.write_words(0x537210,[c.tick]);m.write_words(0x5430c4,[c.animationDelta]);m.write_words(0x534eac,[c.levelWord]);m.write_words(0x541334,[c.forcedRandom]);m.write_words(0x537960,[0x1016000]);m.write_words(0x1016000+0x44,[c.hitMode]);m.write_words(0x513e10,c.defaults)
 m.write_words(0x52e1cc,[c.emptyStringToken]);m.write_words(0x533470,[32]);u.mem_write(0x534938,b'\0')
 m.write_words(0x538428+8,[1000,2000+len(names)-1,FUNCTIONS,0,4,0,0,0])
 m.write_words(FUNCTIONS,[0]*1000+functions)
 m.write_words(0x537698+8,[1000,2000+len(names)-1,STRING_OBJECTS,0,4,0,0,0])
 m.write_words(STRING_OBJECTS,[EMPTY]*1000);m.write_words(EMPTY-12,[1,0,0]);u.mem_write(EMPTY,b'\0')
 for i,n in enumerate(names):
  token=STRINGS+64*i;m.write_words(STRING_OBJECTS+4*(1000+i),[token]);m.write_words(token-12,[1,len(n),len(n)]);u.mem_write(token,n+b'\0')
def compare(s,c,entry,label,arg=0):
 global tile_index,total,event_total,current_context
 current_context=c;before=bytes(s);before_c=bytes(c);native_events.clear();tile_index=0;result=C.c_uint32()
 if entry==0x47d890:rr=lib.claw_rat_bomb_construct(C.byref(s),C.byref(c),dependency,None)
 elif entry==0x47d7d0:rr=lib.claw_rat_bomb_tick(C.byref(s),C.byref(c),dependency,None)
 else:rr=lib.claw_rat_bomb_entry(C.byref(s),C.byref(c),entry,arg,dependency,None,C.byref(result))
 assert rr and not c.fault,(label,'native rejection',c.fault)
 expected=bytes(s);expected_events=list(native_events)
 old=Enemy.from_buffer_copy(before);old_c=Context.from_buffer_copy(before_c);install(old,old_c);current_context=old_c;original_events.clear();tile_index=0
 args=struct.pack('<I',A)if entry in (0x47d890,0x47d7d0,0x473c50)else struct.pack('<I',arg)if entry in(0x47db20,0x473f40,0x4063b0,0x4c9e30,0x484d90) else b''
 receiver=A if entry in(0x406150,0x406180,0x47e1d0,0x406240)else E
 try:ret=m.call(entry,receiver,args)
 except Exception:
  print('FAIL original',label,hex(u.reg_read(UC_X86_REG_EIP)),m.read_words(u.reg_read(UC_X86_REG_ESP),8));raise
 actual=bytes(snapshot())
 if actual!=expected:
  for name in sizes:
   diff=[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(m.read_words(addresses[name],sizes[name]),getattr(s,name)))if x!=y]
   if diff:print(label,name,diff[:25])
  raise AssertionError((label,'complete buffer mismatch'))
 assert m.read_words(0,1)==[0x12345678],(label,'SEH head not restored')
 if entry not in(0x406150,0x406180,0x47e1d0,0x406240,0x4741f0,0x47db20,0x473f40,0x4c96b0,0x4c9e30,0x4dca10,0x4063b0,0x456030):assert ret==(E if entry in(0x47d890,0x473c50) else 1 if entry==0x47d7d0 else result.value),(label,'EAX',ret,result.value)
 if original_events!=expected_events:
  print(label,'original events',[x for x,y in original_events]);print('native events',[x for x,y in expected_events])
  for index,(x,y)in enumerate(zip(original_events,expected_events)):
   if x!=y:print('first mismatch',index,x[0],y[0]);break
  raise AssertionError((label,'ordered complete-snapshot events mismatch'))
 total+=1;event_total+=len(original_events)

def install_world(levelOne=False):
    import zlib
    columns,rows=16,12
    cells=[0]*(columns*rows)
    for x in range(columns):cells[8*columns+x]=1
    for x in (8,9):cells[8*columns+x]=0
    for y in range(3,8):cells[y*columns+4]=3
    cells[8*columns+2]=4
    descriptions=[Description(1,64,64,i,0,0,0,0,0)for i in range(5)]
    if levelOne:
        raw=(ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes()
        offset=struct.unpack_from('<I',raw,736)[0]
        if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
        for i in range(struct.unpack_from('<I',raw,732)[0]):
            ph=struct.unpack_from('<40I',raw,offset+160*i)
            if ph[2]&1:
                columns,rows=ph[24:26];assert ph[22:24]==(64,64)
                cells=list(struct.unpack_from('<'+'I'*(columns*rows),raw,ph[33]));break
        descOffset=struct.unpack_from('<I',raw,740)[0];count=struct.unpack_from('<I',raw,descOffset+8)[0];pos=descOffset+32
        descriptions=[]
        for _ in range(count):
            kind,unknown,width,height=struct.unpack_from('<4I',raw,pos)
            if kind==1:
                descriptions.append(Description(kind,width,height,struct.unpack_from('<I',raw,pos+16)[0],0,0,0,0,0));pos+=20
            else:
                assert kind==2
                outside,inside=struct.unpack_from('<2I',raw,pos+16)
                descriptions.append(Description(kind,width,height,inside,outside,*struct.unpack_from('<4i',raw,pos+24)));pos+=40
    offsets=[x*columns for x in range(rows)]
    owner,actorList,plane,descPtrs,descData,cellData,rowData=0x1090000,0x1092000,0x1091000,0x1081000,0x1070000,0x1040000,0x1080000
    m.write_words(T+0xc,[owner]);m.write_words(owner+8,[actorList]);m.write_words(actorList+0x14,[0])
    m.write_words(T+0x4c,[descPtrs]);m.write_words(T+0x5c,[plane]);m.write_words(T+0x64,[64,64])
    m.write_words(plane+0x20,[cellData,rowData]);m.write_words(plane+0x30,[columns*64,rows*64]);m.write_words(plane+0x8c,[6,6])
    m.write_words(cellData,cells);m.write_words(rowData,offsets)
    for i,d in enumerate(descriptions):m.write_words(descData+i*0x40,[0x513980 if d.type==1 else 0x5139c8,d.width,d.height,d.insideAttribute if d.type==1 else d.outsideAttribute,d.insideAttribute,d.left,d.top,d.right,d.bottom])
    m.write_words(descPtrs,[descData+i*0x40 for i in range(len(descriptions))])
    cs,rs,ds=(C.c_uint32*len(cells))(*cells),(C.c_uint32*len(offsets))(*offsets),(Description*len(descriptions))(*descriptions)
    world=World(cs,rs,columns*64,rows*64,6,6,ds,len(descriptions),None,0,64,64);world.storage=(cs,rs,ds)
    return world


