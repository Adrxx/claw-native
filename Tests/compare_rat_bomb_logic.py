#!/usr/bin/env python3
"""Hash-pinned original RatBomb complete callback/physics/state snapshots."""
import rat_bomb_helpers as h
if __name__=='__main__':
 for entry in(0x47e1d0,0x406240,0x484d90,0x456030,0x473c50,0x47d890,0x4741f0,0x47e050,0x47df20,0x47e180,0x47dfc0,0x4742f0,0x47db20,0x473f40,0x47d7d0):
  for n in range(100):
   s,c=h.fresh();h.policy=n%2;h.marker=n%3;h.collision=h.rng.choice([0,0x10000,0x800000,0x40000,0x80000]);s.actor[0x1a4//4]=n%2;s.actor[0x19c//4]=n%3;s.enemy[0x168//4]=n%2;s.enemy[0x148//4]=n%2;s.enemy[0x164//4]=0x1020500 if h.policy else 0;s.enemy[5]=s.enemy[6]=0
   if entry==0x47d7d0:s.primary[7]=[0,29,30,1000,2000,2001][n%6]
   if entry in(0x47e1d0,0x406240,0x484d90,0x456030,0x473c50,0x47d890,0x47d7d0):
    s.actor[0x148//4]=n%3*250;s.actor[0x14c//4]=n%2*100
    for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=0
   h.compare(s,c,entry,(hex(entry),n),2000+n%2)
  print('PASS100',hex(entry),'full snapshots/events',flush=True)
 print('PASS',h.total,'original calls;',h.event_total,'ordered full-snapshot dependencies;',len(h.m.executed),'instruction addresses')
 directed=0
 for velocity in(-500.,-.25,-0.,0.,.25,500.,float('nan')):
  for render in(0,2):
   for sentinel in(0,0x80000000):
    s,c=h.fresh();h.policy=0;h.marker=0;h.store(s.enemy,0x50,velocity);s.actor[0x40//4]=render
    for o in(0x118,0x128,0x138):s.actor[o//4]=sentinel;s.actor[(o+8)//4]=0x80000000
    h.compare(s,c,0x47e050,('activate',velocity,render,sentinel));directed+=1
 for image in(0,h.IMAGE):
  for minimum,maximum in((0,0),(3,3),(5,4)):
   s,c=h.fresh();h.policy=0;c.imageMinimum=minimum;c.imageMaximum=maximum;s.actor[0x170//4]=h.IMAGE_MANAGER;s.actor[0x174//4]=image
   h.compare(s,c,0x47e1d0,('minimum-image',image,minimum,maximum));directed+=1
   h.compare(s,c,0x406240,('image-hitrect',image,minimum,maximum));directed+=1
 # Explosion entry can occur twice in the same falling update; both restart
 # ANI and sound and capture state. Preserve both dependency snapshots.
 for floor in(1,2,8):
  for collision in(0,0x10000,0x18000):
   for audio in(0,1):
    s,c=h.fresh();h.policy=0;h.marker=1;s.actor[0xcc//4]=floor;s.enemy[0x120//4]=collision;s.enemy[0x164//4]=0x1020500;c.audioManagerAvailable=audio
    h.compare(s,c,0x47e180,('double-impact',floor,collision,audio));directed+=1
 for marker in(0,1,2,0xffffffff):
  for seen in(0,1,0xffffffff):
   for complete in(0,1):
    s,c=h.fresh();h.policy=0;h.marker=marker;s.enemy[0x168//4]=seen;s.actor[0x1a4//4]=complete;s.actor[0x19c//4]=0
    s.actor[0x138//4]=0x80000000;s.actor[0x13c//4]=0x7fffffff;s.actor[0x140//4]=0x7fffffff;s.actor[0x144//4]=0xffffffff
    h.compare(s,c,0x47dfc0,('marker-expand',marker,seen,complete));directed+=1
 for scale in(0.,-1.,.5,1.,1e9,float('inf'),float('-inf'),float('nan')):
  for depth in(0,4990,12345):
   s,c=h.fresh();h.policy=1;h.marker=0;h.collision=0;c.damageScale=scale;s.actor[0x64//4]=depth;s.actor[0x148//4]=0;s.actor[0x14c//4]=0
   h.compare(s,c,0x47d890,('scale-depth',scale,depth));directed+=1
 chains=0
 # Recovered live flight/impact against actual original CD tile data. The
 # Rat launch payload is applied only AFTER immediate initializer activation.
 h.world=h.install_world(True);h.realCollision=True;h.policy=1;h.marker=0
 for history in range(24):
  s,c=h.fresh();c.tick=100;c.animationDelta=16;c.audioManagerAvailable=1;s.primary[7]=0
  s.actor[0x4c//4]=689;s.actor[0x50//4]=4600-history*3;s.actor[0x148//4]=s.actor[0x14c//4]=0;s.actor[0xdc//4]=s.actor[0xe0//4]=10;s.actor[0x1a4//4]=1;s.actor[0x19c//4]=1
  for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=0
  h.compare(s,c,0x47d7d0,('flight-init',history));chains+=1
  # Rat's original south throw:250px/s initial Y,1500px/s² gravity. East/west
  # throws have horizontal ±500, zero Y and gravity; all use the same API.
  h.store(s.enemy,0x50,(-500.,0.,500.)[history%3]);h.store(s.enemy,0x58,250. if history%3==1 else 0.);h.store(s.enemy,0x40,1500. if history%3==1 else 0.)
  h.compare(s,c,0x47e050,('rat-launch-activate',history));chains+=1
  for frame in range(64):
   c.tick+=16;c.animationDelta=(11,17,23)[frame%3]
   if frame==45:s.actor[0xcc//4]=1
   h.marker=1 if frame==46 else 0
   if frame==48:s.actor[0x19c//4]=0
   h.compare(s,c,0x47d7d0,('flight',history,frame));chains+=1
 print('PASS',directed,'directed cases;',chains,'retained flight/impact/explosion calls;',h.total,'total complete originals;',h.event_total,'full-snapshot events;',len(h.m.executed),'instruction addresses')
 # Whole original Rat47d660 really calls the recovered RatBomb initializer,
 # then writes launch fields and activates it. Creation remains an explicit
 # logged object-manager service; both actor/private graphs are compared.
 import rat_bomb_throw_helpers as throws
 joined=0;joined_events=0;joined_ticks=0;automatic_impacts=0
 h.realCollision=False
 for n in range(18):
  s,c,event_count=throws.check(n);joined+=1;joined_events+=event_count
  h.realCollision=True
  for frame in range(64):
   c.tick+=16;c.animationDelta=(11,17,23)[frame%3]
   if n%3!=1 and frame==45:s.enemy[0x120//4]|=0x10000
   h.marker=1 if frame==48 else 0
   if frame==50:s.actor[0x19c//4]=0
   if n%3==1 and s.primary[7]==2001:automatic_impacts+=1
   joined_events+=throws.tick(n,frame);joined_ticks+=1
  h.realCollision=False
 assert automatic_impacts>0,'no true tile impacts reached'
 print('PASS',joined_ticks,'retained actual Rat-launched flight/impact/explosion calls;',automatic_impacts,'automatic south-throw explosion frames')
 print('PASS',joined,'whole Rat throw -> actual RatBomb initializer -> launch activation comparisons;',joined_events,'ordered combined actor/logic/private snapshots')

 print('PASS FINAL',h.total+joined+joined_ticks,'complete originals;',h.event_total+joined_events,'ordered complete-snapshot events;',len(h.m.executed),'original instruction addresses')
