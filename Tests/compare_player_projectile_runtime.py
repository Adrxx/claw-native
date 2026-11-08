#!/usr/bin/env python3
import player_projectile_runtime_helpers as h
for f,kind in[(0x410870,0),(0x410900,1),(0x4084b0,2),(0x43a910,2),(0x408860,2),(0x408870,2),(0x4089d0,2),(0x410d60,1),(0x414010,1),(0x43b120,2),(0x43b160,2),(0x43b1a0,2),(0x43b1e0,2),(0x43b210,2),(0x43b290,2),(0x43b320,2),(0x408510,2),(0x410a80,1),(0x408580,2),(0x43ad20,2)]:
 for n in range(80):
  h.fresh(kind);h.g.audioEnabled=n%2;h.g.magicDisabled=n%3==1;h.put(h.OWNER+0x124,[n%3]);h.resource=n%4!=0;h.animationResult=n%4;h.mutation=n%2;h.g.tick=[1000,2249,2250,0xffffffff][n%4];h.g.animationDelta=[0,17,33,0xffffffff][n%4];h.put(h.A+204,[1 if n%3==0 else 8]);h.put(h.E+0x158,[n%4]);h.put(h.E+0x180,[n%3==0]);h.put(h.E+0x150,[n%4]if kind==1 else[h.SEQ]);h.put(h.E+0x170,[n%3]);h.put(h.DESC+12,[n%3]);h.put(h.A+0x158,[(n%9-4)*50]);h.dbl(h.E+88,[0,300,-300][n%3]);h.dbl(h.E+64,[0,2000,-2000][n%3]);h.randomWords=[0,1,2147483647,0xffffffff,0x80000000]
  args=(h.A,)if f in(0x410870,0x410900,0x4084b0,0x43a910)else(2001,)if f in(0x410a80,0x408580,0x43ad20)else()
  h.compare(f,args=args,label=(hex(f),n))
 print('PASS80',hex(f),flush=True)
print('PASS',h.calls,'complete calls',h.eventsCount,'ordered complete snapshots',len(h.m.executed),'instruction addresses',flush=True)
for f,kind in[(0x40ff80,0),(0x410040,1),(0x43a850,2)]:
 for state in(0,29,30,1000,2001,2002):
  for n in range(12):
   h.fresh(kind);h.put(h.L+28,[state]);h.g.tick=1000+n*83;h.g.animationDelta=n*3;h.put(h.OWNER+0x124,[n%2]);h.g.magicDisabled=n%2;h.g.audioEnabled=n%2;h.resource=n%3!=0
   h.compare(f,t=0,args=(h.A,),label=('wrapper',hex(f),state,n))
 print('PASS72 wrapper',hex(f),flush=True)
# Actual disc ANI/PID geometry profiles retain constructor → ordinary frame
# scheduler → flight → fuse/impact → explosion → private destruction.
histories=[]
for kind,wrapper in enumerate((0x40ff80,0x410040,0x43a850)):
 for profile in range(8):
  h.fresh(kind);h.installImages();h.installANI();h.c.composeAnimation=1;h.put(h.L+28,[0]);h.put(h.A+0x170,[0]);h.g.tick=1000;h.g.magicDisabled=profile%2;h.g.audioEnabled=profile%2;h.g.animationDelta=17;h.put(h.A+0x158,[(-1 if profile%2 else 1)*(profile+1)*25]);h.compare(wrapper,t=0,args=(h.A,),label=('real-resource-start',kind,profile));steps=0;markers=0
  for frame in range(110):
   h.g.tick+=17;h.g.animationDelta=[13,17,29][frame%3]
   if kind<2 and frame==25:h.put(h.E+0x120,[0x10000])
   if kind==2 and profile in(2,3)and frame in(10,30,50):h.put(h.A+204,[1])
   h.compare(wrapper,t=0,args=(h.A,),label=('real-resource-flight',kind,profile,frame));steps+=1
   if h.get(h.A+8)[0]&0x10000:break
  end=h.get(h.A+76,2);state=h.get(h.L+28)[0];deleted=bool(h.get(h.A+8)[0]&0x10000)
  h.compare(0x484d90,args=(1,),label=('real-resource-private-destroy',kind,profile));histories.append({'kind':kind,'profile':profile,'steps':steps,'end':end,'state':state,'delete':deleted})
 print('PASS8 retained actual resources',hex(wrapper),flush=True)
report={'calls':h.calls,'orderedFullSnapshots':h.eventsCount,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'globalBytes':0x30000,'resourceProfiles':h.assets,'histories':histories}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k not in('histories','resourceProfiles')}),flush=True)
fireHistories=[]
for weapon in(1,2,3):
 for direction in(0,1):
  for charge in(0,500,1000,1500):
   h.fire(weapon,direction,charge);h.c.composeAnimation=1;wrapper=(0x40ff80,0x410040,0x43a850)[weapon-1];h.compare(wrapper,t=0,args=(h.A,),label=('fire→actual-start',weapon,direction,charge));h.g.tick+=17;h.compare(wrapper,t=0,args=(h.A,),label=('fire→flight',weapon,direction,charge));fireHistories.append({'weapon':weapon,'facing':direction,'charge':charge,'damage':h.get(h.A+0x104)[0],'type':h.get(h.A+0xd0)[0],'ammo':h.get(h.PLAYERPRIVATE+28*4,3),'state':h.get(h.L+28)[0]})
print('PASS24 whole ANI marker2→41c5a0→source projectile initialization/flight',flush=True)
collisionHistories=[]
for kind,wrapper in enumerate((0x40ff80,0x410040,0x43a850)):
 for direction in(-1,1):
  h.fresh(kind);h.installImages();h.installANI();h.c.composeAnimation=1;h.realCollision=True;h.put(h.WORLD+12,[h.SC]);h.put(h.SC+0x100+20,[0]);h.put(h.WORLD+100,[64,64]);h.put(h.A+220,[10,10]);h.put(h.DESC+0x100,[h.DESC,h.DESC+0x40]);h.put(h.DESC+0x40,[0x513980,64,64,1]);h.put(h.CELLS,[1 if (i//16>=8 or i%16==7)else 0 for i in range(256)]);h.put(h.A+76,[300 if direction>0 else 600,480]);h.put(h.A+0x148,[direction*700,0]);h.put(h.A+0x158,[direction*200]);h.put(h.A+0x170,[0]);h.put(h.L+28,[0]);h.compare(wrapper,t=0,args=(h.A,),label=('real-wall-start',kind,direction));steps=0;firstCollision=None
  for frame in range(180):
   h.g.tick+=17;h.g.animationDelta=17;previous=h.get(h.E+0x120)[0];h.compare(wrapper,t=0,args=(h.A,),label=('real-wall-flight',kind,direction,frame));steps+=1;mask=h.get(h.E+0x120)[0]
   if firstCollision is None and mask&0x10000:firstCollision=frame
   if h.get(h.A+8)[0]&0x10000:break
  collisionHistories.append({'kind':kind,'direction':direction,'steps':steps,'firstTileCollision':firstCollision,'end':h.get(h.A+76,2),'delete':bool(h.get(h.A+8)[0]&0x10000),'state':h.get(h.L+28)[0]});h.compare(0x484d90,args=(1,),label=('real-wall-destroy',kind,direction));h.realCollision=False
print('PASS6 retained whole original collision/physics/ANI/fuse chains',flush=True)
failureEvents=[]
for fn,stop in[(0x40ff80,0x40ffde),(0x410040,0x41009e),(0x43a850,0x43a8ae)]:failureEvents.append(h.failure(fn,stop,True))
for fn,stop in[(0x410d60,0x410e69),(0x43b320,0x43b429)]:failureEvents.append(h.failure(fn,stop))
print('PASS5 explicitly separate unsafe prefixes',flush=True)
report.update({'calls':h.calls,'orderedFullSnapshots':h.eventsCount,'originalAddresses':len(h.m.executed),'fireHistories':fireHistories,'collisionHistories':collisionHistories,'unsafePrefixes':5,'unsafePrefixEvents':sum(failureEvents)})
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k not in('histories','resourceProfiles','fireHistories','collisionHistories')}),flush=True)
actualFire=[]
for weapon,path in[(1,'CLAW/ANIS/PISTOL.ANI'),(2,'CLAW/ANIS/MAGIC.ANI'),(3,'CLAW/ANIS/POSTDYNAMITE.ANI')]:
 for facing in(0,1):
  h.fire(weapon,facing,1000,prepareOnly=True);h.playerANI(path);h.c.composeAnimation=1
  frames=0
  while not h.get(h.PLAYERPRIVATE+16)[0] and frames<80:
   h.fireStep(weapon,facing,1000);frames+=1;h.g.tick+=17
  assert h.get(h.PLAYERPRIVATE+16)[0],('actual ANI marker2 missing',path,facing)
  wrapper=(0x40ff80,0x410040,0x43a850)[weapon-1];h.compare(wrapper,t=0,args=(h.A,),label=('actualClaw-marker→projectile',weapon,facing));actualFire.append({'path':path,'facing':facing,'framesToFire':frames,'ammo':h.get(h.PLAYERPRIVATE+112,3)})
print('PASS6 actual CLAW ANI→marker2→full original41c5a0→projectile chains',flush=True)
report.update({'calls':h.calls,'orderedFullSnapshots':h.eventsCount,'originalAddresses':len(h.m.executed),'actualClawFire':actualFire,'resourceProfiles':h.assets})
for now in(0,1,0x7fffffff,0x80000000,0xffffff00,0xffffffff):
 for deadline in(0,1,0x7fffffff,0x80000000,0xffffff00,0xffffffff):
  for duration in(0,1,500,0x7fffffff,0x80000000,0xffffffff):
   h.fresh();h.put(0x541328,[now]);h.put(0x53c260,[deadline]);h.compare(0x486e70,t=0,args=(duration,),label=('pulse',now,deadline,duration));assert h.get(0x53c260)[0]==max(deadline,(now+duration)&0xffffffff)
h.fresh();h.put(0x53c260,[0])
for n in range(250):
 h.put(0x541328,[h.rng.getrandbits(32)]);h.compare(0x486e70,t=0,args=(h.rng.getrandbits(32),),label=('retained-pulse',n))
print('PASS216 directed and250 retained exact486e70 deadline updates',flush=True)
report.update({'calls':h.calls,'orderedFullSnapshots':h.eventsCount,'originalAddresses':len(h.m.executed),'pulseCalls':466})
for fn,kind in[(0x410d60,1),(0x43b320,2)]:
 h.fresh(kind);off=0x150 if kind==1 else 0x170;h.put(h.E+off,[3]);h.countMutationOffset=off;h.compare(fn,label=('live-sparkle-count',fn));h.countMutationOffset=None;assert h.get(h.E+off)[0]==1
for fn,kind,table in[(0x410a80,1,0x534ab0),(0x408580,2,0x534910),(0x43ad20,2,0x5375d8)]:
 for growth in(False,True):
  h.fresh(kind);h.registryGrowth=growth;h.put(h.get(table+20)[0],[0x4bb030]);h.compare(fn,args=(2300,),label=('source-registry-growth/diagnostic',fn,growth));h.registryGrowth=False
for kind in(0,1,2):
 for dx,dy in((-5,0),(0,7),(4,-9),(0,0)):
  h.fresh(kind);h.put(h.A+8,[0x40010]);h.put(h.A+128,[h.FLARE]);h.put(h.FLARE+344,[dx,dy]);h.put(h.A+204,[1]);h.compare(0x4dca10,label=('supporting-platform-motion',kind,dx,dy))
print('PASS20 mutable callback counts/registry growth/diagnostic/platform profiles',flush=True)
report.update({'calls':h.calls,'orderedFullSnapshots':h.eventsCount,'originalAddresses':len(h.m.executed),'liveFieldProfiles':20})
divisionEvents=[]
for fn,stop in[(0x410d60,0x410dcd),(0x43b320,0x43b38d)]:divisionEvents.append(h.failure(fn,stop,division=True))
for fn,kind in[(0x410d60,1),(0x43b320,2)]:
 for randomValue in(0,1,0xffffffff):
  h.fresh(kind);h.put(h.A+0x118,[2]);h.put(h.A+0x120,[1]);h.randomWords=[randomValue];h.compare(fn,label=('zero-width-random',fn,randomValue))
print('PASS2 signed-division unsafe prefixes and6 zero-width source branches',flush=True)
report.update({'calls':h.calls,'orderedFullSnapshots':h.eventsCount,'originalAddresses':len(h.m.executed),'unsafePrefixes':7,'unsafePrefixEvents':sum(failureEvents)+sum(divisionEvents)})
h.replay.write(h.pack(0));h.replay.close();report['sanitizerReplayCases']=h.replayCases;(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print('Recorded',h.replayCases,'complete sanitizer inputs/expected heaps/explicit transport effects',flush=True)
