"""Disjoint EnemyMotionAux harness, reusing frozen snapshot fixture definitions."""
from pathlib import Path
source=Path(__file__).with_name('human_combat_helpers.py').read_text().split('def compare_null_create(element):')[0]
source=source.replace('\nu.hook_add(UC_HOOK_CODE,host)','\ncombatHook=u.hook_add(UC_HOOK_CODE,host)')
source=source.replace('work/human-combat-agent','work/enemy-motion-aux-agent').replace("'HumanCombat.cpp','SceneActorRuntime.cpp'","'EnemyMotionAux.cpp','HumanCombat.cpp','SceneActorRuntime.cpp'")
exec(compile(source,str(Path(__file__).with_name('human_combat_helpers.py')),'exec'),globals())
class AuxContext(C.Structure):_fields_=[('human',C.POINTER(HumanContext)),('world',C.POINTER(World)),('strongThrow',C.c_uint32),('fault',C.c_uint32)]
lib.claw_enemy_motion_aux_entry.argtypes=[C.POINTER(Enemy),C.POINTER(AuxContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_world_point_attribute.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_int32,C.c_int32,C.c_uint32,C.c_uint32,C.POINTER(Description),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32]
auxFresh=fresh;auxInstall=install;auxEffects=effects;auxHost=host;auxSerialized=serialized;auxWrite=write
ledgeResults={0:0,1:0}
strongThrow=0;pointIndex=0;pointResults=None;realPoints=False;auxView=None
world=install_world()

def fresh():
 s,c=auxFresh();s.actor[0x118//4:0x128//4]=[0xfffffff0,0xffffffe0,16,32];s.actor[0x128//4:0x138//4]=[0xfffffff0,0xffffffe0,16,0];s.enemy[0x260//4:0x270//4]=[0xfffffff0,0xffffffe0,16,0]
 s.enemy[0x1ac//4]=rng.choice([0,1,20,0x7fffffff,0x80000000,0xffffffff]);c.generic.playerActor[0x16c//4]=rng.choice([0,42,43]);c.sharedStates.playerPrivate[0]=rng.choice([0,1]);c.generic.animationDelta=rng.choice([0,16,0xffffffff]);s.actor[0x19c//4]=0;s.actor[0x1a4//4]=rng.choice([0,1]);s.enemy[0x2cc//4]=rng.choice([0,1]);c.generic.virtualFunctions[0x8c//4]=0x440120
 for off in(0x68,0x70,0x40,0x58):s.enemy[off//4:off//4+2]=struct.unpack('<2I',struct.pack('<d',rng.choice([-1000.0,-0.25,0.0,0.25,1.0,37.125,1000.0])))
 return s,c

def serialized(s):return auxSerialized(s)+struct.pack('<I',strongThrow)

def point(x,y):
 global pointIndex
 if pointResults is not None:result=pointResults[pointIndex%len(pointResults)];pointIndex+=1;return result
 return lib.claw_world_point_attribute(world.cells,world.rowOffsets,world.width,world.height,world.shiftX,world.shiftY,world.descriptions,world.descriptionCount,x,y,0,0)

def write(s):
 auxWrite(s);m.write_words(0x537224,[strongThrow])

def effects(s,event):
 global strongThrow
 f,receiver,args,name=event
 if mutate and f==0x4c8220:
  strongThrow^=1
  if native and auxView is not None:auxView.strongThrow=strongThrow
 if f==0x4207f0:return point(*args)
 return auxEffects(s,event)

def host(uc,address,size,user):
 if address in(0x440420,0x43eab0):return
 if address==0x10fb030:
  sp=u.reg_read(UC_X86_REG_ESP);dst,src=m.read_words(sp+4,2);m.write_words(dst,m.read_words(src,4));returned(8,1);return
 if address==0x4207f0:
  sp=u.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,2));s=snapshot();event=(address,u.reg_read(UC_X86_REG_ECX),args,None);events.append((event,serialized(s)))
  if realPoints:return
  returned(8,point(*args));return
 auxHost(uc,address,size,user)
# Replace the inherited combat callback; record actual original point calls.
# The human inherited handle was deleted by that fixture, so retain our handle.
# Its combat callback does not recognize4207f0/CopyRect and would otherwise
# duplicate virtual service returns. Delete the remaining callback by handle.
u.hook_del(combatHook)
u.hook_add(UC_HOOK_CODE,host)
def install(s,c):
 auxInstall(s,c);m.write_words(0x546d58,[0x10fb030]);m.write_words(0x537224,[strongThrow]);install_world(realPoints)

def compare(s,c,entry,label,arg=0):
 global current,native,random_index,pointIndex,calls,event_count,auxView,strongThrow
 before,bc=bytes(s),bytes(c);beforeStrong=strongThrow;current=c;native=True;events.clear();random_index=pointIndex=0
 hv=human_view(c);auxView=AuxContext(C.pointer(hv),C.pointer(world),strongThrow,0);result=C.c_uint32()
 assert lib.claw_enemy_motion_aux_entry(C.byref(s),C.byref(auxView),entry,arg,dependency,None,C.byref(result)) and not auxView.fault and not hv.fault,(label,'native fault',auxView.fault,hv.fault)
 expected,ee=serialized(s),list(events)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);strongThrow=beforeStrong;install(old,oc);native=False;events.clear();random_index=pointIndex=0
 try:ret=m.call(entry,E)
 except Exception:print('fault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 actual=serialized(snapshot())
 if actual!=expected:
  for index,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',index,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 assert ret==result.value,(label,'return',ret,result.value)
 if events!=ee:
  for index,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',index,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[x[0]for x in events]);print('native',[x[0]for x in ee]);raise AssertionError((label,'events'))
 if entry==0x43eab0:ledgeResults[ret]+=1
 calls+=1;event_count+=len(events);current=c;return s,c
