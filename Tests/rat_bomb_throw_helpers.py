import ctypes as C
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
import rat_bomb_helpers as h
GenericContext=h.GenericContext
class RatContext(GenericContext):
 _fields_=[('playerPrivate',C.c_uint32*78),('attackerToken',C.c_uint32),('attackerActor',C.c_uint32*128),('damageScale',C.c_float),('healthScale',C.c_float),('rangeScale',C.c_float),('imageMinimum',C.c_int32),('imageHeader',C.c_uint32*16),('soundPoolToken',C.c_uint32),('audioManagerAvailable',C.c_uint32),('masterVolume',C.c_uint32),('projectileToken',C.c_uint32),('projectileActor',C.c_uint32*128),('projectilePrimary',C.c_uint32*93),('projectileEnemy',C.c_uint32*264),('sequenceRegistryToken',C.c_uint32),('objectManagerToken',C.c_uint32),('projectileEnemyToken',C.c_uint32),('projectileActivateFunction',C.c_uint32),('projectileVisualActor',C.c_uint32*128),('fault',C.c_uint32)]
RATA,RATL,RATE=0x10a0000,0x10a1000,0x10a2000
bomb=rat=bomb_c=rat_c=None
base_host=h.host
h.u.hook_del(h.host_handle)
def rat_original_bytes():
 s=h.Enemy()
 for field,addr,n in [('actor',RATA,128),('primary',RATL,93),('enemy',RATE,264)]:getattr(s,field)[:]=h.m.read_words(addr,n)
 return bytes(s)
def original_hook(uc,address,size,user):
 if address==0x4c8da0:
  sp=h.u.reg_read(UC_X86_REG_ESP);args=tuple(h.m.read_words(sp+4,6));event=(address,h.u.reg_read(UC_X86_REG_ECX),args,b'RatBomb')
  h.original_events.append((event,bytes(h.snapshot())+rat_original_bytes()))
  h.m.write_words(h.A+0x4c,args[1:3]);h.m.write_words(h.A+0x64,[args[3]]);h.m.write_words(h.L+0x1c,[0]);h.returned(24,h.A);return
 if address in(0x47d7d0,0x47e050):
  if address==0x47d7d0 and h.m.read_words(h.u.reg_read(UC_X86_REG_ESP),1)[0]!=0x47d6db:return
  if address==0x47e050 and h.m.read_words(h.u.reg_read(UC_X86_REG_ESP),1)[0]!=0x47d746:return
  sp=h.u.reg_read(UC_X86_REG_ESP);args=(h.m.read_words(sp+4,1)[0],)if address==0x47d7d0 else ()
  event=(address,0 if address==0x47d7d0 else h.u.reg_read(UC_X86_REG_ECX),args,None)
  h.original_events.append((event,bytes(h.snapshot())+rat_original_bytes()));return
 before=len(h.original_events);rs=rat_original_bytes();base_host(uc,address,size,user)
 for n in range(before,len(h.original_events)):
  event,data=h.original_events[n];h.original_events[n]=(event,data+rs)

h.u.hook_add(UC_HOOK_CODE,original_hook)
h.lib.claw_rat_context_defaults.argtypes=[C.POINTER(RatContext)]
h.lib.claw_rat_entry.argtypes=[C.POINTER(h.Enemy),C.POINTER(RatContext),C.c_uint32,C.c_uint32,h.Dependency,C.c_void_p,C.POINTER(C.c_uint32)];h.lib.claw_rat_entry.restype=C.c_uint32

def sync_from_bomb():
 rat_c.projectileActor[:]=bomb.actor;rat_c.projectilePrimary[:]=bomb.primary;rat_c.projectileEnemy[:]=bomb.enemy;rat_c.projectileVisualActor[:]=bomb.actor

def sync_to_bomb():
 bomb.actor[:]=rat_c.projectileActor;bomb.primary[:]=rat_c.projectilePrimary;bomb.enemy[:]=rat_c.projectileEnemy

@h.Dependency
def dependency(s,c,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name)
 if e.function==0x47e050:sync_to_bomb()
 h.native_events.append((event,bytes(bomb)+bytes(rat)))
 if e.function==0x4c8da0:
  args=event[2];bomb.actor[0x4c//4]=args[1];bomb.actor[0x50//4]=args[2];bomb.actor[0x64//4]=args[3];bomb.primary[7]=0;sync_from_bomb();return h.A
 if e.function==0x47d7d0:
  assert event[2]==(h.A,)
  result=h.lib.claw_rat_bomb_tick(C.byref(bomb),C.byref(bomb_c),dependency,None);sync_from_bomb();return result
 if e.function==0x47e050:
  result=C.c_uint32();assert h.lib.claw_rat_bomb_entry(C.byref(bomb),C.byref(bomb_c),0x47e050,0,dependency,None,C.byref(result));sync_from_bomb();return result.value
 return h.effects(bomb,event)

def check(index):
 global bomb,rat,bomb_c,rat_c
 bomb,bomb_c=h.fresh();rat=h.Enemy();rat_c=RatContext();h.lib.claw_rat_context_defaults(C.byref(rat_c))
 rat_c.actorToken=RATA;rat_c.primaryToken=RATL;rat_c.enemyToken=RATE;rat_c.sceneToken=h.SC;rat_c.tileManagerToken=h.T;rat_c.objectManagerToken=h.OBJ;rat_c.projectileToken=h.A;rat_c.projectileEnemyToken=h.E;rat_c.projectileActivateFunction=0x47e050
 rat.actor[3]=h.SC;rat.actor[0x6c//4]=RATL;rat.actor[0x4c//4]=689;rat.actor[0x50//4]=4600;rat.actor[0x64//4]=4000;rat.actor[0x1a4//4]=0;rat.actor[0x19c//4]=1
 rat.primary[3]=h.SC;rat.primary[0x18//4]=RATE;rat.primary[7]=2019;rat.enemy[0]=0x50f084;rat.enemy[3]=rat.enemy[0x12c//4]=rat.enemy[0x190//4]=rat.enemy[0x194//4]=RATA;rat.enemy[4]=rat.enemy[0x130//4]=RATL
 vx=(-500,0,500)[index%3];rat.enemy[0x404//4]=vx&0xffffffff;rat.enemy[0x408//4]=250 if vx==0 else 0;rat.enemy[0x40c//4]=1500 if vx==0 else 0;rat.enemy[0x410//4]=(1 if vx==0 else -13 if vx<0 else 13)&0xffffffff;rat.enemy[0x414//4]=(-12 if vx==0 else -22)&0xffffffff
 bomb.actor[0xdc//4]=bomb.actor[0xe0//4]=10;bomb.actor[0x148//4]=bomb.actor[0x14c//4]=0;bomb.primary[0x10//4]=0x47d7d0;bomb_c.tick=100;bomb_c.animationDelta=(5,11,17)[index%3]
 for o in(0x2c,0x30,0x34,0x38):bomb.primary[o//4]=0
 bomb.actor[0x1a4//4]=1;bomb.actor[0x19c//4]=1;rat_c.animationDelta=bomb_c.animationDelta;h.policy=1;h.marker=1;h.current_context=bomb_c;h.realCollision=False;sync_from_bomb()
 old_bomb=bytes(bomb);old_bomb_c=bytes(bomb_c);old_rat=bytes(rat);h.native_events.clear();result=C.c_uint32()
 assert h.lib.claw_rat_entry(C.byref(rat),C.byref(rat_c),0x47d660,0,dependency,None,C.byref(result))==1 and result.value==0
 sync_to_bomb();expected_bomb=bytes(bomb);expected_rat=bytes(rat);events=list(h.native_events)
 h.install(h.Enemy.from_buffer_copy(old_bomb),h.Context.from_buffer_copy(old_bomb_c));old=h.Enemy.from_buffer_copy(old_rat)
 for field,addr in [('actor',RATA),('primary',RATL),('enemy',RATE)]:h.m.write_words(addr,getattr(old,field))
 h.original_events.clear();h.current_context=h.Context.from_buffer_copy(old_bomb_c);ret=h.m.call(0x47d660,RATE,b'')
 assert ret==0 and bytes(h.snapshot())==expected_bomb and rat_original_bytes()==expected_rat,(index,'combined full-buffer mismatch')
 assert h.original_events==events,(index,'combined ordered snapshot event mismatch',[(x,len(y))for x,y in h.original_events],[(x,len(y))for x,y in events])
 assert h.m.read_words(0,1)==[0x12345678]
 # Continue using the ordinary whole-bomb comparison while retaining its
 # original initialized actor/private state and exact Rat launch payload.
 return bomb,bomb_c,len(events)
def tick(index,frame):
 global bomb,bomb_c
 old_bomb=bytes(bomb);old_context=bytes(bomb_c);old_rat=bytes(rat)
 h.native_events.clear();h.current_context=bomb_c
 assert h.lib.claw_rat_bomb_tick(C.byref(bomb),C.byref(bomb_c),dependency,None)==1 and not bomb_c.fault
 expected=bytes(bomb);events=list(h.native_events)
 h.install(h.Enemy.from_buffer_copy(old_bomb),h.Context.from_buffer_copy(old_context));old=h.Enemy.from_buffer_copy(old_rat)
 for field,addr in [('actor',RATA),('primary',RATL),('enemy',RATE)]:h.m.write_words(addr,getattr(old,field))
 h.original_events.clear();h.current_context=h.Context.from_buffer_copy(old_context)
 assert h.m.call(0x47d7d0,h.E,struct.pack('<I',h.A))==1
 assert bytes(h.snapshot())==expected and rat_original_bytes()==old_rat,(index,frame,'combined retained full graph mismatch')
 assert h.original_events==events,(index,frame,'combined retained events mismatch')
 assert h.m.read_words(0,1)==[0x12345678]
 return len(events)
