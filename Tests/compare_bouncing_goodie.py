#!/usr/bin/env python3
"""Whole original BouncingGoodie spawn/state/pickup histories."""
import bouncing_goodie_helpers as h
entries=[0x40e750,0x40efa0,0x40f010,0x40f0e0,0x40f200,0x40f2a0,0x40f390,0x40f400,0x4736b0,0x4dc870,0x40ebe0,0x40e690,0x484d90]
for mutate in(0,1):
 h.mutate=mutate
 for entry in entries:
  for n in range(96):
   s,c=h.fresh();h.collisionResult=h.rng.choice([0,0x100000,0x800000,0x40000]);h.pickupMode=n%2
   if h.pickupMode and h.collisionResult==0x100000:h.collisionResult=0
   if entry==0x40e690:s.primary[7]=h.rng.choice([0,29,30,1000,h.ids[b'LS_FALLING'],h.ids[b'LS_BOUNCE']])
   h.compare(s,c,entry,(mutate,hex(entry),n),s.primary[7]if entry==0x40ebe0 else 0)
for chain in range(64):
 h.mutate=chain%2;h.pickupMode=0;h.collisionResult=0;s,c=h.fresh();s.primary[7]=0;h.compare(s,c,0x40e690,('spawn',chain))
 # Actual drop wrapper applies launch physics and loot ID AFTER startup.
 s.enemy[0x50//4:0x58//4]=h.struct.unpack('<2I',h.struct.pack('<d',50.0));s.enemy[0x58//4:0x60//4]=h.struct.unpack('<2I',h.struct.pack('<d',-350.0));s.enemy[0x40//4:0x48//4]=h.struct.unpack('<2I',h.struct.pack('<d',800.0));s.enemy[0x184//4]=chain%62
 for frame in range(12):
  c.generic.tick=(c.generic.tick+17)&0xffffffff;s.actor[0xcc//4]=1 if frame in(2,4,6,8)else 8;s.actor[0x164//4]=0x200 if frame==10 else 0
  h.compare(s,c,0x40e690,('retained',chain,frame))
h.freeMutation=True
for n in range(96):
 s,c=h.fresh();h.compare(s,c,0x484d90,('delete',n),n%2)
# All62 actual initializer records and four trailing zero slots, including
# duplicate/null image roots and first-match semantics.
import json
records=json.loads((h.ROOT/'Tests/world_loot_initializer_profile.json').read_text())['records']
for row in records:
 n=row['id'];h.loot.words[n]=0x10b4000+n*32 if row['image'] else 0;h.loot.words[66+n]=row['value'];h.loot.words[132+n]=row['mask'];h.loot.words[274+n]=0x10a4000+n*0x80 if row['sound'] else 0
for row in records:
 s,c=h.fresh();s.actor[0x170//4]=h.loot.words[row['id']];s.actor[0xd0//4]=1;h.compare(s,c,0x4736b0,('actualLootRecord',row['id'],row['image']))
h.compare_null_allocation()
print(f'BouncingGoodie: {h.calls} whole original calls, {h.event_count} ordered full snapshot events, {len(h.m.executed)} original addresses; actual401000 heap names.')
