"""Human shared controllers versus actual original complete buffers/events."""
import struct
import human_enemy_helpers as h
entries=[0x44bc60,0x44c000,0x44c840,0x44d000,0x44d3c0,0x44edd0,0x44df10,0x44df60,0x44e0c0,0x44d9f0,0x44cfd0,0x44f840,0x44f6e0,0x44e120,0x44d760,0x44ebb0,0x4a1180]+[f for _,f,_ in h.humanRegistrations]
for entry in entries:
 for n in range(180):
  s,c=h.fresh();h.policy=n%2;h.clear_path=n%2;h.ledge=n%2;h.random_results=[h.rng.randrange(-1000,33000)for _ in range(10)];h.resource_mode=n%3
  arg=2000+h.rng.randrange(len(h.names))if entry==0x44c840 else h.rng.choice([0x52720c,0x5234f4,h.STRINGS+64*h.rng.randrange(len(h.names))])if entry==0x44d000 else h.rng.randrange(4)if entry==0x44e0c0 else h.OTHER if entry==0x44d760 else 0
  if entry in(0x44bc60,0x44c000):c.generic.tick=h.rng.choice([0,1,16000,0x7fffffff,0x80000000,0xffffffff])
  h.compare(s,c,entry,(hex(entry),n),arg)
 print('PASS180',hex(entry),flush=True)
# Retained constructor/home/registered-state/pre/post histories, keeping all
# enemy/tail/effect/platform buffers from one step to the next.
for chain in range(64):
 s,c=h.fresh();h.policy=chain%2;h.clear_path=chain%2;h.ledge=0;h.random_results=[0,55,201,421,300];h.resource_mode=1
 h.compare(s,c,0x44c000,('chain-ctor',chain));h.compare(s,c,0x44d9f0,('chain-home',chain))
 for step in range(6):
  c.generic.tick=(c.generic.tick+17)&0xffffffff
  h.compare(s,c,0x44d000,('chain-pre',chain,step),h.STRINGS+64*h.names.index(b'LS_HOME'))
  h.compare(s,c,0x44c840,('chain-dispatch',chain,step),s.primary[7])
  h.compare(s,c,0x44d3c0,('chain-post',chain,step))
# Constructor scales are real global float loads; compare after callbacks at
# negative, zero, fractional and large finite values.
for n in range(96):
 s,c=h.fresh();h.policy=n%2;c.damageScale=h.rng.choice([-2,0,0.1,0.5,2,100]);c.healthScale=h.rng.choice([-2,0,0.1,0.5,2,100]);c.rangeScale=h.rng.choice([-2,0,0.1,0.5,2,100]);h.compare(s,c,0x44c000,('scaled-constructor',n))
# Original registration401000 copies every nonempty CString name. The native
# name data token must be distinct from the original literal pointer. Compare
# both direct literal calls and copied-registry name calls against original.
for literal in(0x52720c,0x527204,0x527da0,0x5234f4,0x5271d8,0x5271cc,0x5271b4):
 for copied in(False,True):
  s,c=h.fresh();h.policy=0;h.clear_path=0;h.ledge=0;c.generic.forcedRandom=1;s.enemy[0x300//4]=0x202;s.enemy[0x184//4]=6;c.privateTail[(0x440-0x420)//4]=0;c.privateTail[(0x444-0x420)//4]=0
  h.compare(s,c,0x44d000,('literal-vs-copied',hex(literal),copied),h.STRINGS if copied else literal)
  assert bool(s.actor[0x164//4]&1)==copied
# Queued callbacks execute before shared post and can overwrite the queued
# slot/current state. Full snapshots preserve the actual ordering.
for n in range(96):
 s,c=h.fresh();h.policy=n%2;h.random_results=[n,101];s.enemy[5]=0x44d9f0;s.enemy[6]=0x44edd0;s.enemy[7]=s.primary[7]if n%2 else s.primary[7]+1
 h.compare(s,c,0x44d3c0,('queued-post',n))
# Audio pools are explicit leaf services, while sound selection, both audio
# calls and deletion/loot ordering execute in the Human state bodies.
for entry in(0x44dd30,0x44de50,0x44e0c0,0x44e120):
 for n in range(96):
  s,c=h.fresh();h.policy=n%2;h.clear_path=0;h.ledge=0;c.sharedStates.audioEnabled=1;c.sharedStates.audioPosition=h.rng.randrange(101)
  for j,offset in enumerate((0x38c,0x390,0x394,0x398,0x39c,0x3a4,0x3a8,0x3ac,0x3b0,0x40c,0x410,0x414,0x418,0x41c)):s.enemy[offset//4]=h.resourceViews[j].token
  c.privateTail[(0x428-0x420)//4]=c.generic.tick;c.privateTail[(0x42c-0x420)//4]=0;s.enemy[9]=2000+h.names.index(b'LS_TEST')
  h.compare(s,c,entry,('audio-state',hex(entry),n),n%4 if entry==0x44e0c0 else 0)
print('PASS',h.calls,'complete original calls;',h.event_count,'ordered full-snapshot events;',len([a for a in h.m.executed if 0x400000<=a<0x547000]),'original-image instruction addresses')
