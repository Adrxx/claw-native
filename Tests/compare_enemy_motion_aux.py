#!/usr/bin/env python3
"""Original lifted/release/throw bodies and ledge scans with whole snapshots."""
import enemy_motion_aux_helpers as h
entries=[0x440420,0x440710,0x440350,0x440120,0x4407d0,0x4409d0,0x440410,0x4405b0,0x440260,0x440870,0x440a50]
for mutate in(0,1):
 h.mutate=mutate
 for entry in entries:
  for n in range(128):
   h.strongThrow=h.rng.choice([0,1,0xffffffff]);s,c=h.fresh();h.compare(s,c,entry,(mutate,hex(entry),n))
for n in range(256):
 s,c=h.fresh()
 for off in(0x68,0x70,0x40,0x58):s.enemy[off//4:off//4+2]=h.struct.unpack("<2I",h.struct.pack("<d",h.rng.uniform(-10000,10000)))
 h.compare(s,c,0x440420,("finitePhysics",n))
for n in range(384):
 h.mutate=n%2;h.pointResults=[h.rng.randrange(4)for _ in range(9)];s,c=h.fresh();s.actor[0x4c//4]=h.rng.choice([0,128,256,512,0xffffffff]);s.actor[0x50//4]=h.rng.choice([0,480,511,512,0xffffffff]);s.actor[0x124//4]=0
 h.compare(s,c,0x43eab0,('scriptedLedge',n))
h.pointResults=None;h.realPoints=True;h.world=h.install_world(True)
for n in range(512):
 s,c=h.fresh();s.actor[0x4c//4]=h.rng.randrange(h.world.width);s.actor[0x50//4]=h.rng.randrange(h.world.height);s.actor[0x124//4]=h.rng.choice([0,32,0xffffffff]);h.compare(s,c,0x43eab0,('Level1',n))
# Directed real Level1 surfaces and tile edges, including narrow supports.
candidates=[]
cols=h.world.width>>h.world.shiftX;rows=h.world.height>>h.world.shiftY
for row in range(rows):
 for col in range(cols):
  cell=h.world.cells[h.world.rowOffsets[row]+col]
  if cell in(0xffffffff,0xeeeeeeee):continue
  desc=h.world.descriptions[cell&0xffff]
  if desc.insideAttribute not in(1,2,3):continue
  for localX in(0,1,31,32,63):
   for localY in({0,desc.top} if desc.type==2 else {0}):
    x=(col<<h.world.shiftX)+localX;y=(row<<h.world.shiftY)+localY
    if h.point(x,y)in(1,2,3)and h.point(x,y-1)==0:candidates.append((x,y))
assert candidates
h.rng.shuffle(candidates)
for n,(x,y)in enumerate(candidates[:768]):
 s,c=h.fresh();s.actor[0x4c//4]=x;s.actor[0x50//4]=(y-1)&0xffffffff;s.actor[0x124//4]=0;h.compare(s,c,0x43eab0,('Level1-directed',n))
h.realPoints=False;h.world=h.install_world()
for chain in range(64):
 s,c=h.fresh();h.strongThrow=chain%2;h.mutate=chain%2
 for entry in(0x440420,0x4405b0,0x4407d0,0x440410,0x440870,0x440120,0x440260,0x440350,0x440420,0x440710,0x4409d0,0x440a50):h.compare(s,c,entry,('retainedLiftThrowDrop',chain,hex(entry)))
print(f'EnemyMotionAux: {h.calls} whole original calls, {h.event_count} ordered full snapshot events, {len(h.m.executed)} original addresses; actual401000 heap names, real Level1 original point queries, ledge results {h.ledgeResults}.')
