#!/usr/bin/env python3
"""Whole ordinary item callbacks, CaptainClawHit awards, retained histories."""
import item_pickup_helpers as h
callbacks=[0x46fd10,0x470100,0x470d00,0x470f00,0x471100]
for n in range(64):
 h.prepare();h.itemContext.auxiliaryManagerToken=h.AUX if n%2 else 0;h.compare(0x405f80,[],('auxiliary-scene-check',n),receiver=h.AUX)
h.itemContext.auxiliaryManagerToken=h.AUX
for mutate in(0,1):
 h.mutate=mutate
 for fn in callbacks:
  for n in range(160):
   h.prepare();h.createdResult=h.rng.choice([0,h.GLITTER]);h.put(h.LOG+0x10,[fn],True);h.compare(fn,[h.ITEM],(mutate,hex(fn),n))
 for fn,nargs in((0x41d6f0,1),(0x41f850,2),(0x473ae0,1),(0x41ee60,4)):
  for n in range(128):
   h.prepare();h.put(h.ITEM+4,[h.rng.randrange(70)],True);h.put(h.LOG+0x168,[h.g.words[274+h.rng.randrange(66)]],True)
   args=[h.ITEM]if nargs==1 else[h.ITEM,h.PLAYER_PRIVATE]if nargs==2 else[h.PLAYER,h.PLAYER_LOGIC,h.PLAYER_PRIVATE,h.ITEM]
   if fn==0x41ee60:h.put(h.ITEM+0xfc,[0x26b0],True);h.put(h.ITEM+0x108,[h.rng.getrandbits(32)],True)
   h.compare(fn,args,(mutate,hex(fn),n))
 for kind in(0x40000,0x10000,0x800000,0x100000,0x200000,0x100):
  for n in range(128):
   h.prepare();h.put(h.ITEM+0xd0,[kind],True);h.put(h.ITEM+0xfc,[0x26b0 if kind==0x100 else h.rng.choice([0,1,20,100,0x80000000,0xffffffff])],True);h.put(h.ITEM+0x108,[h.rng.choice([0,5,10,0x7fffffff,0x80000000])],True);h.put(h.LOG+0x168,[h.g.words[274+h.rng.randrange(66)]],True);h.put(h.PLAYER+0x10c,[h.rng.choice([0,99,100,101,0x7fffffff,0x80000000,0xffffffff])],True);h.synchronize_player(True)
   h.compare(0x41ce80,[h.PLAYER],(mutate,'award',kind,n))
for row in h.profile['records']:
 fn={'TreasurePowerup':0x46fd10,'HealthPowerup':0x470d00,'AmmoPowerup':0x471100,'MagicPowerup':0x470f00}.get(row['logic'])
 if not fn:continue
 h.prepare();h.mutate=row['id']%2;h.createdResult=h.GLITTER;h.put(h.ITEM+0x170,[h.g.words[row['id']]],True);h.put(h.ITEM+0x174,[h.IMAGE],True);h.put(h.LOG+0x10,[fn],True);h.put(h.LOG+0x1c,[0],True)
 h.compare(fn,[h.ITEM],('actual-record-startup',row['id']))
 # Whole original and native actor-hit paths award the rebound ordinary item.
 if row['logic']=='HealthPowerup' and row['value']>100:
  before=h.snapshot(True);assert not h.lib.claw_item_pickup_award(h.ITEM,h.C.byref(h.itemContext),h.dependency,None);assert h.snapshot(True)==before
 else:h.compare(0x41ce80,[h.PLAYER],('actual-record-award',row['id']))
 for frame in range(5):h.itemContext.stageDelta=100;h.compare(fn,[h.ITEM],('actual-record-followup',row['id'],frame))
for row in h.profile['records']:
 fn={'TreasurePowerup':0x46fd10,'HealthPowerup':0x470d00,'AmmoPowerup':0x471100,'MagicPowerup':0x470f00}.get(row['logic'])
 if not fn or(row['logic']=='HealthPowerup'and row['value']>100):continue
 h.prepare();h.mutate=0;h.install_registry();h.put(h.ITEM+8,[0x40000],True);h.put(h.ITEM+0x164,[0],True);h.put(h.ITEM+0x170,[h.g.words[row['id']]],True);h.put(h.ITEM+0x174,[h.IMAGE],True);h.put(h.ITEM+0x4c,[100,200],True);h.put(h.ITEM+0x148,[0,0],True);h.put(h.LOG+0x10,[0x40e690],True);h.put(h.LOG+0x1c,[0],True);h.put(h.LOG+0x2c,[0]*4,True)
 h.compare(0x40e690,[h.ITEM],('Goodie-startup',row['id']))
 h.put(h.BASE+0x79000+0x184,[row['id']],True);h.put(h.BASE+0x79000+0x40,list(h.struct.unpack('<2I',h.struct.pack('<d',800.0))),True)
 for frame in range(5):
  h.put(h.ITEM+0xcc,[1],True);h.put(h.BASE+0x79000+0x58,list(h.struct.unpack('<2I',h.struct.pack('<d',350.0))),True)
  h.compare(0x40e690,[h.ITEM],('Goodie-bounce-rebind',row['id'],frame))
 assert h.get(h.LOG+0x10)[0]==fn
 h.compare(0x41ce80,[h.PLAYER],('Goodie-rebound-award',row['id']))
print(f'ItemPickupRuntime: {h.item_calls} whole original calls, {h.item_events} ordered full raw snapshot events, {len(h.m.executed)} original addresses; ordinary actual loot records and CaptainClawHit award graph.')
