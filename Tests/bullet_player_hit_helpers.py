"""Bullet→CaptainClawHit composition using the frozen whole-body damage oracle."""
from pathlib import Path
import ctypes as C
source=Path(__file__).with_name('player_damage_helpers.py').read_text()
source=source.replace('work/player-damage-agent','work/bullet-agent').replace('libPlayerDamage.dylib','libBulletPlayerHit.dylib')
source=source.replace("str(ROOT/'Sources/TileCollision.cpp'),'-o'","str(ROOT/'Sources/TileCollision.cpp'),*[str(ROOT/'Sources'/name)for name in ('BulletLogic.cpp','GenericEnemy.cpp','WorldObjectRuntime.cpp','SceneActorRuntime.cpp','GameTiming.cpp')],'-o'")
namespace={'__file__':str(Path(__file__).with_name('player_damage_helpers.py')),'__name__':'bullet_player_hit_fixture'}
exec(compile(source,namespace['__file__'],'exec'),namespace)
def install(h):
 q=namespace;f=q['lib'].claw_bullet_player_hit
 f.argtypes=[C.POINTER(h.Enemy),C.POINTER(h.BulletContext),C.POINTER(q['State']),C.POINTER(q['Damage']),C.POINTER(q['Input']),q['Callback'],C.c_void_p];f.restype=C.c_uint32
 result={'calls':0,'events':0,'privatePreserved':0}
 def hit(sp,tp,ip,dependency,user):
  s=C.cast(sp,C.POINTER(q['State']));t=C.cast(tp,C.POINTER(q['Damage']));i=C.cast(ip,C.POINTER(q['Input']))
  b=h.Enemy();b.actor[:]=t.contents.attackerActor;b.primary[:]=[h.rng.getrandbits(32)for _ in b.primary];b.enemy[:]=[h.rng.getrandbits(32)for _ in b.enemy];before=bytes(b.primary)+bytes(b.enemy)
  g=h.GenericContext();g.actorToken=q['ATTACKER'];x=h.BulletContext();x.generic=C.pointer(g)
  boundaryChecks=[]
  @q['Callback']
  def observed(pp,fn,a,c,d,u):
   boundaryChecks.append(list(b.actor)==list(t.contents.attackerActor));return dependency(pp,fn,a,c,d,u)
  value=f(C.byref(b),C.byref(x),s,t,i,observed,user);assert all(boundaryChecks)
  assert list(b.actor)==list(t.contents.attackerActor);assert bytes(b.primary)+bytes(b.enemy)==before
  result['privatePreserved']+=1;return value
 q['lib'].claw_player_hit=hit
 def check(s,t,i,label):
  q['compare'](s,t,i,0x41ce80,label);result['calls']+=1;result['events']+=len(q['o'].events)
 return q,check,result
