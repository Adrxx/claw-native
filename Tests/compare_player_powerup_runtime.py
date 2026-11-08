#!/usr/bin/env python3
"""Whole original setter/reset/music/image/FX graphs and retained timers."""
import player_powerup_runtime_helpers as h
types=[0,1,0x26b6,0x26b7,0x26b8,0x26b9,0x26ba,0x26bb,0x26bc,0x26bd,0x26be,0x7fffffff,0x80000000,0xffffffff]
for mutation in(0,1,2):
 h.mutation=mutation
 for old in types:
  for new in types:
   for n in range(3):
    h.prepare(old,h.rng.choice([0,1,998999,999000,999001,0x80000000,0xfffffff0,0xffffffff]))
    h.created=h.rng.choice([0,h.NEWGLITTER]);h.levelResult=h.rng.choice([0,h.LEVEL]);h.powerResult=h.rng.choice([0,h.POWER])
    duration=h.rng.choice([0,1,15000,30000,999000,0x7fffffff,0x80000000,0xffffffff])
    h.compare(0x41f990,[h.A,h.L,h.P,new,duration],('setter',mutation,old,new,n))
print('PASS directed normal/reset/same-type/unsigned clock/music missing/status/mutation setter matrix',flush=True)
h.mutation=0;h.levelResult=h.LEVEL;h.powerResult=h.POWER
for n in range(128):
 h.prepare(h.rng.choice(types),h.rng.getrandbits(32));h.g.playerToken=h.rng.choice([0,h.A])
 h.compare(0x41fc00,[h.rng.choice(types),h.rng.getrandbits(32)],('player-wrapper',n))
for n in range(128):
 h.prepare();h.created=h.rng.choice([0,h.NEWGLITTER]);h.compare(0x448400,[h.rng.choice([0,h.A])],('GlitterMother-create',n))
for mutation in(0,2):
 h.mutation=mutation
 for n in range(128):
  h.prepare();h.put(h.IM+0x64,[h.rng.choice([-2,0,1,3,4]),h.rng.choice([0,1,3,5])])
  h.put(h.ARRAY-8,[h.IMAGE,h.IMAGE]);h.put(h.ARRAY+16,[0,0])
  h.compare(0x4ce7b0,[h.rng.choice([1,2,4,8,50,0xffffffff])],('image-range',mutation,n),receiver=h.IM)
for index in(0,0x34,0x35,0x36,0x37,0x65,0xffffffff):
 for remaining in(0,1,100,0x80000000,0xffffffff):
  for delta in(0,1,99,100,0x80000000,0xffffffff):
   h.prepare();h.g.cycleIndex=index;h.g.cycleRemaining=remaining
   h.compare(0x420070,[h.A,delta],('effect-cycle',index,remaining,delta))
for old in types:
 for n in range(32):
  h.prepare(old,h.rng.choice([0,1,17,100,999000,0xffffffff]));h.created=h.NEWGLITTER
  h.compare(0x41fc30,[h.A,h.L,h.P,h.rng.choice([0,1,17,100,999000,0xffffffff])],('composed-countdown',old,n))
for n in range(64):
 h.prepare();h.created=h.NEWGLITTER;h.mutation=n%3
 for frame in range(12):
  if frame in(0,3,6,9):
   h.compare(0x41f990,[h.A,h.L,h.P,h.rng.choice(types),h.rng.choice([0,15000,30000,0xffffffff])],('retained-select',n,frame))
  else:h.compare(0x41fc30,[h.A,h.L,h.P,h.rng.choice([0,18,100,30000,0xffffffff])],('retained-timer',n,frame))
h.mutation=0;h.prepare();h.compare(0x4bc110,[],('single-RET-complete',),receiver=h.MUSICOWNER)
import player_powerup_caller_helpers as joined
profile=h.json.loads((h.ROOT/'Tests/world_loot_initializer_profile.json').read_text())
for row in profile['records'][:62]:
 for n in range(3):
  h.mutation=n%3;h.created=h.rng.choice([0,h.NEWGLITTER]);h.levelResult=h.LEVEL;h.powerResult=h.POWER
  joined.prepare(h.rng.choice(types),h.rng.choice([0,15000,999000,0xffffffff]),'hit')
  joined.damage.attackerActor[0xd0//4]=row['mask'];joined.damage.attackerActor[0xfc//4]=row['value']
  joined.damage.attackerActor[0x108//4]=h.rng.choice([0,1,15000,30000,0x80000000,0xffffffff])
  joined.state.actor[0x10c//4]=h.rng.choice([1,99,100])
  joined.compare(('actual-loot-hit',row['id'],n))
  if row['id']in(22,23):assert h.g.powerup==0x26bc and joined.damage.attackerActor[8//4]&0x10000
for old in types:
 for n in range(12):
  h.mutation=n%3;h.created=h.NEWGLITTER;joined.mode=h.rng.choice([0,4])
  joined.prepare(old,h.rng.choice([0,1,999000,0xffffffff]),'respawn')
  joined.compare(('state23-reset',old,n))
  assert h.g.powerup==0
for n in range(24):
 h.mutation=0;h.created=h.NEWGLITTER;h.levelResult=h.LEVEL;h.powerResult=h.POWER
 joined.prepare(0,0,'hit');row=profile['records'][22+n%2]
 joined.damage.attackerActor[0xfc//4]=row['value'];joined.damage.attackerActor[0x108//4]=0
 joined.compare(('retained-Catnip-award',row['id'],n))
 for frame in range(8):
  h.compare(0x41fc30,[h.A,h.L,h.P,18 if frame<4 else h.rng.choice([1000,15000,30000])],('retained-Catnip-timer',n,frame))
 joined.pull(joined.state);joined.phase='respawn';joined.state.logicState=23
 for address,value in joined.global_updates().items():h.m.u.mem_write(address,value)
 joined.compare(('retained-Catnip-state23',n))
 assert h.g.powerup==0 and joined.state.privateWords[0x130//4]==0
print(f'PASS {joined.caller_calls} joined actual62-loot CaptainClawHit and state23 respawn calls, whole powerup setter/timer bodies composed',flush=True)
assert {0x41f990,0x41fc00,0x41fc30,0x4ce7b0,0x448400,0x420070,0x4bc110,0x4c6130}<=h.m.executed
addresses=h.m.executed-(set(h.COUNTS)-{0x4c6130})-{h.m.stop}
addresses={a for a in addresses if 0x400000<=a<0x550000}
print(f'PASS {h.calls} whole original calls / {h.events} ordered full heap+globals events / {len(addresses)} original instruction addresses; 256KiB complete heaps +112KiB global image, raw actor128/private78/logic93, frozen timer/image-effect composition.',flush=True)
(h.WORK/'coverage.json').write_text(h.json.dumps({'calls':h.calls,'events':h.events,
 'joinedCallerCalls':joined.caller_calls,'originalInstructionAddresses':[hex(a)for a in sorted(addresses)],
 'adaptedServices':[hex(a)for a in sorted(set(h.COUNTS)-{0x4c6130})]},indent=2)+'\n')
# Bounded host rejections are deliberately separate from valid original parity.
before=h.raw(True);result=h.C.c_uint32(123);h.ctx.fault=0
assert not h.lib.claw_player_powerup_entry(0x41ebd0,0,None,0,h.C.byref(h.ctx),h.dependency,None,h.C.byref(result))
assert h.ctx.fault==0 and result.value==0 and h.raw(True)==before
assert not h.lib.claw_player_powerup_entry(0x41f990,0,None,5,h.C.byref(h.ctx),h.dependency,None,h.C.byref(result))
assert h.ctx.fault==2 and h.raw(True)==before
print('PASS unsupported/body and malformed-ABI rejection checks, distinct from original parity',flush=True)
