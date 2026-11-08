#!/usr/bin/env python3
"""Whole original Human combat entries with full retained snapshots/events."""
import human_combat_helpers as h
entries=[0x44d460,0x44d570,0x44d5a0,0x44d700,0x44d730,0x44f3c0,0x44f510]
for mutate in(0,1):
 h.mutate=mutate
 for entry in entries:
  for n in range(160):
   h.random_results=[h.rng.choice([0,1,2,3,4,0x7fffffff,0x80000000,0xfffffffc,0xffffffff])for _ in range(3)]
   s,c=h.fresh();h.compare(s,c,entry,(mutate,hex(entry),n))
for n in range(384):
 h.mutate=n%2;h.random_results=[n,0xffffffff,0x80000000]
 s,c=h.fresh();c.generic.virtualFunctions[0x28//4]=0x404dd0
 c.sharedStates.attackerActor[0x104//4]=h.rng.getrandbits(32)
 s.actor[0x10c//4]=h.rng.choice([0,1,0x7fffffff,0x80000000,0xffffffff])
 h.compare(s,c,entries[n%5],("actualDamage",n))
for chain in range(96):
 h.mutate=chain%2;h.random_results=[chain,0xffffffff,0x80000000,7]
 s,c=h.fresh()
 for frame in range(20):s,c=h.compare(s,c,entries[(chain+frame)%len(entries)],('chain',chain,frame))
for chain in range(64):
 h.mutate=chain%2;h.random_results=[chain,0xffffffff,0x80000000,7]
 s,c=h.fresh();c.generic.virtualFunctions[0x28//4]=0x404dd0
 for frame in range(12):
  h.compare(s,c,0x44d460,('hit-state-chain-attack',chain,frame))
  entry=0x44f660 if s.primary[7]==h.ids[b'LS_HITHIGH'] else 0x44f490
  h.compare(s,c,entry,('hit-state-chain-update',chain,frame))
for element in(0x26b8,0x26b9,0x26ba):h.compare_null_create(element)
print(f'HumanCombat: {h.calls} whole original calls, {h.event_count} ordered full snapshot events, {len(h.m.executed)} original addresses; actual401000 copied heap names.')
