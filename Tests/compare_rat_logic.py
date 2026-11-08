#!/usr/bin/env python3
"""Original v1.0 Rat complete actor/logic/brain buffers and ordered calls."""
import rat_helpers as h
if __name__=='__main__':
 for entry in (0x4357a0,0x406310,0x405000,0x47d150,0x47d4b0,0x47d540,0x47d5d0,0x47d780,0x47d2f0,0x47d1b0,0x47d470,0x47d490,0x47d660,0x47cd70,0x47c910,0x47c850):
  for n in range(100):
   s,c=h.fresh();h.policy=n%2;h.query_value=n%2;h.marker=n%3;h.collision=0;h.random_value=h.rng.randrange(32768);h.tile_values=[1,0]
   s.actor[0x1a4//4]=n%2;s.actor[0x19c//4]=n%3;s.enemy[0x1a0//4]=n%3
   s.enemy[0x400//4]=0x1020c00 if h.policy else 0
   s.enemy[0x24//4]=2000+n%len(h.names);s.enemy[0x418//4]=(c.tick-1000)&0xffffffff;s.enemy[0x41c//4]=1000
   if entry==0x47cd70:arg=2000+n%len(h.names)
   else:arg=0
   if entry==0x47c850:s.primary[7]=[0,29,30,1000,0,2004,2017,2019,2000][n%9]
   if entry in(0x47c910,0x47c850):
    s.actor[0x148//4]=n%2*60;s.actor[0x14c//4]=0
    for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=0
   h.compare(s,c,entry,(hex(entry),n),arg)
  print('PASS100',hex(entry),'full snapshots/events',flush=True)
 print('PASS',h.total,'original calls;',h.event_total,'ordered complete-snapshot dependencies;',len(h.m.executed),'original instruction addresses')
 # Directed geometry sentinels and signed wrapping; wrapper rectangles mirror
 # even when INT_MIN whereas all three actor rectangles skip that sentinel.
 directed=0
 for f in(0x4357a0,0x406310,0x405000):
  for left in(0,1,0x7fffffff,0x80000000,0xffffffff):
   for render in(0,2,0x80000002):
    s,c=h.fresh();h.policy=0;s.actor[0x40//4]=render
    for o in(0x118,0x128,0x138):s.actor[o//4]=left;s.actor[(o+8)//4]=0x80000000
    s.enemy[0x138//4]=left;s.enemy[0x140//4]=0x80000000
    s.enemy[0x210//4]=left;s.enemy[0x218//4]=0x80000000
    h.compare(s,c,f,('mirror-edge',f,left,render));directed+=1
 # Independently trigger horizontal cooldown and vertical randomized throw.
 for powerup in(0,0x26b7):
  for facing in(2,3):
   for py in(-50,-49,-1,0,1,49,50):
    for elapsed in(0,1,999,1000,1001,0xffffffff):
     s,c=h.fresh();h.policy=0;h.query_value=1;h.marker=0;c.levelWord=powerup;c.tick=25;c.forcedRandom=1
     s.actor[0x4c//4]=0;s.actor[0x50//4]=0;s.actor[0x38//4]=0;s.enemy[0x18c//4]=facing
     h.store(s.enemy,0x68,0.);h.store(s.enemy,0x70,0.);c.playerActor[0x4c//4]=0;c.playerActor[0x50//4]=py&0xffffffff
     s.enemy[0x418//4]=(c.tick-elapsed)&0xffffffff;s.enemy[0x41c//4]=1000
     h.compare(s,c,0x47d2f0,('cooldown',powerup,facing,py,elapsed));directed+=1
 for forced in(0,1):
  for value in(0,1,98,99,100,0x7fffffff,0x80000000,0xffffffff):
   for x in(-40,-39,0,39,40):
    s,c=h.fresh();h.policy=0;h.query_value=1;h.marker=0;h.random_value=value;c.levelWord=0;c.forcedRandom=forced
    s.actor[0x4c//4]=0;s.actor[0x50//4]=0;s.actor[0x38//4]=0;s.enemy[0x18c//4]=2;s.enemy[0x2e4//4]=99
    h.store(s.enemy,0x68,0.);h.store(s.enemy,0x70,-0.25);c.playerActor[0x4c//4]=x&0xffffffff;c.playerActor[0x50//4]=10
    s.enemy[0x418//4]=c.tick;s.enemy[0x41c//4]=1000
    h.compare(s,c,0x47d2f0,('vertical-throw',forced,value,x));directed+=1
 # Exact 53-bit multiplication of float globals, with truncation/wrap and the
 # unsigned minimum99 rule; does not infer difficulty settings.
 for scale in(0.,-1.,.5,1.,9.9,10.,100.,1e9,float('inf'),float('-inf'),float('nan')):
  for image in(0,1):
   s,c=h.fresh();h.policy=image;h.collision=0;h.marker=0;c.damageScale=c.healthScale=c.rangeScale=scale
   s.actor[0x148//4]=0;s.actor[0x14c//4]=0
   for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=0
   h.compare(s,c,0x47c910,('scale',scale,image));directed+=1
 # Repeated marker1 creates one bomb until count wraps back to0. Test both
 # horizontal and vertical payloads and completion/home entry ordering.
 for marker in(0,1,2):
  for count in(0,1,0xffffffff):
   for done in(0,1):
    for vx in(0,500,0xfffffe0c):
     s,c=h.fresh();h.policy=0;h.marker=marker;s.enemy[0x1a0//4]=count;s.enemy[0x404//4]=vx;s.enemy[0x408//4]=250;s.enemy[0x40c//4]=1500
     s.actor[0x1a4//4]=done;s.actor[0x19c//4]=0;s.enemy[0x400//4]=0
     h.compare(s,c,0x47d660,('projectile',marker,count,done,vx));directed+=1
 # Common projectile wrapper may alias the visual actor to the projectile.
 for vx in(500,0xfffffe0c):
  s,c=h.fresh();h.policy=0;h.marker=1;s.enemy[0x1a0//4]=0;s.enemy[0x404//4]=vx;s.actor[0x1a4//4]=0
  c.projectileEnemy[0x12c//4]=h.BOMB;c.projectileVisualActor[:]=c.projectileActor
  h.compare(s,c,0x47d660,('projectile-visual-alias',vx));directed+=1
 # Retain entire actor/logic/enemy snapshots through initialization, patrol,
 # throw entry, marker-driven creation, completion, and shared FSM ticks.
 chains=0
 for history in range(32):
  s,c=h.fresh();h.policy=1;h.marker=0;h.query_value=0;h.collision=0;h.tile_values=[1,0];h.random_value=history;c.forcedRandom=1;c.tick=100
  s.primary[7]=0;s.primary[0x64//4]=0;s.actor[0x148//4]=0;s.actor[0x14c//4]=0;s.actor[2]=0;s.actor[0x1a4//4]=1;s.actor[0x19c//4]=1
  for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=0
  h.compare(s,c,0x47c850,('chain-init',history));chains+=1
  for step in range(16):
   c.tick+=16;c.animationDelta=(5,11,17,23)[step%4]
   if step==5:
    h.query_value=1;c.levelWord=0;c.playerActor[0x4c//4]=s.actor[0x4c//4];c.playerActor[0x50//4]=s.actor[0x50//4];s.actor[0x38//4]=0
   if step==6:h.marker=1
   if step==8:h.marker=0;s.actor[0x19c//4]=0
   if step==9:h.query_value=0;s.actor[0x19c//4]=1
   h.compare(s,c,0x47c850,('chain-tick',history,step));chains+=1
 print('PASS',directed,'directed cases;',chains,'retained-chain calls;',h.total,'total original calls;',h.event_total,'ordered full-snapshot events;',len(h.m.executed),'original instruction addresses')
 # Actual Level1 Rat WWD coordinates/bounds, with the original and native
 # recovered ground-placement body executing against original CD tile data.
 import struct,zlib
 raw=(h.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();plane_count,plane_offset=struct.unpack_from('<2I',raw,732)
 if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:plane_offset]+zlib.decompress(raw[plane_offset:])
 rats=[]
 for plane in range(plane_count):
  base=plane_offset+160*plane;count=struct.unpack_from('<I',raw,base+128)[0];pos=struct.unpack_from('<I',raw,base+140)[0]
  for _ in range(count):
   w=struct.unpack_from('<71I',raw,pos);lens=w[1:5];name=raw[pos+284+lens[0]:pos+284+lens[0]+lens[1]].split(b'\0',1)[0]
   if name==b'Rat':rats.append(raw[pos:pos+284+sum(lens)])
   pos+=284+sum(lens)
 assert len(rats)==12
 h.world=h.install_world(True);h.realGround=True;h.policy=1;h.marker=0;h.collision=0;h.query_value=0
 for i,data in enumerate(rats):
  s,c=h.fresh();h.initialize_record(s,data);h.compare(s,c,0x47c850,('actual-Level1-Rat',i))
 print('PASS all12 actual Level1 Rat records with original tile ground-placement;',h.total,'total complete original calls;',h.event_total,'full-snapshot events;',len(h.m.executed),'instruction addresses')
