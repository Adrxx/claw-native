#!/usr/bin/env python3
"""Complete original generic state/death/hit comparisons."""
import generic_enemy_states_helpers as h
entries=[0x404f00,0x404ed0,0x43e9c0,0x43f120,0x43f030,0x43f450,0x43f720,0x43f6e0,0x43ff60,0x440070,0x4405b0,0x440260,0x43f540,0x440a50,0x43f980,0x43fc20,0x440be0,0x440d50,0x440870,0x4dc830,0x4dc850,0x43e9e0,0x404dd0,0x404eb0,0x440e20,0x43f640,0x43fe60,0x43f740,0x43ffa0]
for entry in entries:
 for n in range(200):
  s,c,x=h.fresh();h.g.policy=n%4;h.animation_result=n%2;h.random_results=[h.g.rng.getrandbits(32)for _ in range(4)];h.g.tile_values=[1,0] if n%3==0 else [h.g.rng.randrange(5)for _ in range(4)]
  argument=h.g.rng.randrange(5)if entry==0x43f120 else h.AX if entry in(0x404dd0,0x404eb0,0x440e20)else h.g.rng.getrandbits(32)
  h.compare(s,c,x,entry,(hex(entry),n),argument)
 print('PASS200',hex(entry),'complete buffers/globals/events',flush=True)
print(f'PASS {h.calls} original full calls; {h.events} ordered full-snapshot events; {len(h.g.m.executed)} original instruction addresses')

# All19 exact registered callback identities dispatch through the new layer or
# frozen common core, executing original43d490 and actual callback bodies.
for index,name in enumerate(h.g.names[:-1]):
 for n in range(20):
  s,c,x=h.fresh();h.g.policy=n%4;h.animation_result=n%2;h.random_results=[0,77,0x80000001,0xffffffff]
  h.compare(s,c,x,0,('registered-dispatch',name,n),dispatch=index)
print('PASS all19 registered common state dispatches',flush=True)

# Complete generic LogicHit -> original typed damage wrapper -> particle
# coordinates/RNG -> death entry -> death update, retaining all buffers.
chains=0
for kind in(0,2,0x10,0x20,0x1000,0x1000000,0x2000000):
 for health in(-1,0,1,5):
  for rng_values in([0,0],[24,25],[25,99],[0x80000000,0xffffffff]):
   s,c,x=h.fresh();h.g.policy=0;h.animation_result=1;h.random_results=rng_values
   x.playerPrivate[0xe8//4]=1;s.enemy[0x19c//4]=0;s.enemy[0x3d4//4]=0
   x.attackerActor[0xd0//4]=kind;x.attackerActor[0x104//4]=5;s.actor[0x10c//4]=health&0xffffffff
   s.actor[0x38//4]=0;s.enemy[0x18c//4]=3;s.enemy[0x304//4]=4
   c.virtualFunctions[0x14//4]=0x43e9e0;c.virtualFunctions[0x28//4]=0x404dd0
   for slot in(0x2c,0x30,0x34,0x38,0x3c):c.virtualFunctions[slot//4]=0x404eb0
   c.virtualFunctions[0x40//4]=0x4c9e30;c.virtualFunctions[0x5c//4]=0x43f120
   h.compare(s,c,x,0x4dc830,('chain-hit',kind,health,rng_values));chains+=1
   # A duplicate shot must pass through LogicHit but leave all state unchanged.
   h.compare(s,c,x,0x4dc830,('chain-duplicate',kind,health,rng_values));chains+=1
   s.actor[0x38//4]=0xffffffff
   h.compare(s,c,x,0x43f450,('chain-death',kind,health,rng_values));chains+=1
print('PASS',chains,'retained generic hit/death calls',flush=True)

# Delayed hit gating consumes the shot ID before rejecting damage. A later
# duplicate remains rejected even after its cooldown expires.
for elapsed in(0,99,100,101,0xffffffff):
 s,c,x=h.fresh();h.g.policy=0;h.animation_result=0;h.random_results=[50]
 x.playerPrivate[0xe8//4]=2;s.enemy[0x19c//4]=1;s.enemy[0x3d0//4]=(c.tick-elapsed)&0xffffffff;s.enemy[0x3d4//4]=100
 c.virtualFunctions[0x28//4]=0x404dd0;c.virtualFunctions[0x2c//4]=0x404eb0;c.virtualFunctions[0x5c//4]=0x43f120
 x.attackerActor[0xd0//4]=2
 h.compare(s,c,x,0x43e9e0,('consume-before-cooldown',elapsed))
 c.tick+=200;h.compare(s,c,x,0x43e9e0,('duplicate-after-expiry',elapsed))

# Mode1/2 death delay uses unsigned wrap and expires at equality; mode3 delete
# is immediate in its entry. Record bit0 toggle/bit4 set on larger backing too.
for size in(32,64):
 for mode in(0,1,2,3,4,0xffffffff):
  for elapsed in(0,999,1000,1001,0xffffffff):
   s,c,x=h.fresh();h.g.policy=3;h.animation_result=1;h.random_results=[25,99]
   backing=(h.C.c_uint32*2)(0xdeadbeef,0x12345678)
   if size==64:c.bitWords=backing;c.bitWordCount=2;s.enemy[0x300//4]=h.g.BITS
   s.enemy[0x2fc//4]=size
   h.compare(s,c,x,0x43f120,('death-mode',size,mode,elapsed),mode)
   c.tick=(c.tick+elapsed)&0xffffffff
   h.compare(s,c,x,0x43f450,('death-expiry',size,mode,elapsed))

# Undersized/nonconstructed death bitsets and unknown entries are explicit
# unchanged-input native rejections, rather than simulated allocator behavior.
for entry in(0x43f120,0x12345678):
 s,c,x=h.fresh();s.enemy[0x2fc//4]=4;before=bytes(s),bytes(x);h.g.native_events.clear()
 assert h.lib.claw_generic_enemy_state_entry(h.C.byref(s),h.C.byref(c),h.C.byref(x),entry,0,h.dependency,None)==0
 assert (bytes(s),bytes(x))==before and not h.g.native_events
print(f'PASS total {h.calls} complete original calls; {h.events} ordered full-snapshot actor/logic/enemy/attacker/player/global events; {len(h.g.m.executed)} original instruction addresses')
