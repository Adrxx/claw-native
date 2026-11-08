#!/usr/bin/env python3
import super_powerup_runtime_helpers as h
for state in(0,5,29,30,1000,9000,0xffffffff):
 for n in range(100):
  h.fresh();h.put(h.L+28,[state]);h.put(h.A+100,[0 if n%2 else n]);h.put(h.A+0x174,[h.IMAGE if n%3 else 0]);h.put(h.A+400,[h.SEQ if n%2 else 0]);h.put(h.A+200,[h.GLITTER if n%2 else 0]);h.put(h.MANAGER+0x124,[n%3]);h.created=h.GLITTER if n%3 else 0;h.mutation=n%2;h.animation.delta=h.rng.getrandbits(32);h.loot.count=[0,1,62,0xffffffff][n%4]
  if n%3:h.put(h.A+0x170,[h.ROOTIMAGE+(n%62)*64])
  else:h.put(h.A+0x170,[h.ROOTIMAGE-64])
  h.compare(('callback',state,n))
print('PASS700 whole callback cases',flush=True)
for health in(0,1,50,99,100,101,0x7fffffff,0x80000000,0xffffffff):
 for amount in(0,1,100,0xffffffff,0x7fffffff):
  for audio in(0,1):
   h.fresh();h.put(h.A+0xd0,[0x200000]);h.put(h.A+0xfc,[amount]);h.put(h.L+0x168,[h.SOUND]);h.put(h.PLAYER+0x10c,[health]);h.items.audioEnabled=audio;h.compare(('award',health,amount,audio),True)
print('PASS90 whole CaptainClawHit health cases',flush=True)
print('PASS',h.calls,h.eventCount,len(h.m.executed),flush=True)
profiles=[]
for level in range(1,15):
 h.fresh();h.configureResources();p=h.Profile();h.lib.claw_elevator_initialize_profile(level,h.C.byref(p),h.SetRect(),None);h.loot.configuration=p.words[0];h.loot.words[340]=0;h.compare(('whole-lazy-initializer/source-level',level));profiles.append({'level':level,'sourceFirstWord':p.words[0],'lootCount':h.loot.count,'defaultHealth':h.get(h.A+0xfc)[0]})
assert all(p['sourceFirstWord']==p['level']for p in profiles)
print('PASS14 source452b00 profiles joined to actual4719e0',flush=True)
histories=[]
paths=[p for p in h.assets()if p.startswith('GAME/IMAGES/HEALTH/')and p.endswith('.PID')]
for path in paths:
 for glitterEnabled in(0,1):
  h.fresh();geo=h.bindPID(path);records=h.setupResources();h.ctx.composeAnimation=1;h.put(h.MANAGER+0x124,[glitterEnabled]);h.loot.words[0]=h.ROOTIMAGE;h.loot.words[66]=100;h.loot.words[274]=h.SOUND;h.compare(('actual-resource-start',path,glitterEnabled));effect=h.get(h.A+200)[0]
  for frame in range(20):
   h.animation.delta=[0,1,17,33,80][frame%5];h.items.tick+=17;h.compare(('actual-resource-tick',path,glitterEnabled,frame))
   if frame in(5,6):h.compare(('retained-source-award',path,frame),True)
  h.put(h.L+28,[29]);h.compare(('actual-resource-delete',path,glitterEnabled));assert not effect or h.get(effect+8)[0]&0x10000
  histories.append({'image':path,'glitterEnabled':glitterEnabled,'records':records,'health':h.get(h.PLAYER+0x10c)[0],'collected':bool(h.get(h.A+8)[0]&0x10000),'effect':effect,'geometry':geo})
print('PASS24 real PID/POWERUP.ANI retained animation→award→state29 histories',flush=True)
# Explicit service mutation verifies captured startup logic vs reloaded sound destination.
for n in range(16):
 h.fresh();h.mutation=2|(n&1);h.put(h.L+0x400+28,[0x12345678]);h.put(h.MANAGER+0x124,[n&1]);h.compare(('captured-primary-vs-reloaded-primary',n));assert h.get(h.L+28)[0]==5 and h.get(h.L+0x400+28)[0]==0x12345678
# Original resource lookup failure is normal: no animation frames are invented.
for n in range(12):
 h.fresh();h.ctx.composeAnimation=1;h.found=False;h.resourceTokens.pop(b'GAME_POWERUP',None);h.put(h.MANAGER+0x124,[n&1]);h.compare(('missing-POWERUP-ANI/start',n))
 for delta in(0,1,17,0xffffffff):h.animation.delta=delta;h.compare(('missing-POWERUP-ANI/tick',n,delta))
 h.put(h.L+28,[29]);h.compare(('missing-POWERUP-ANI/delete',n))
# Sound dedup uses the exact global sound token and absolute tick pair.
for health in(50,100,101,0x80000000):
 h.fresh();h.put(h.A+0xd0,[0x200000]);h.put(h.A+0xfc,[100]);h.put(h.L+0x168,[h.SOUND]);h.put(h.PLAYER+0x10c,[health]);h.items.audioEnabled=1
 for tick,sound in((1000,h.SOUND),(1000,h.SOUND),(1001,h.SOUND),(1001,h.SOUND+64),(1001,0),(0xffffffff,h.SOUND),(0,h.SOUND)):
  h.items.tick=tick;h.put(h.L+0x168,[sound]);h.put(h.SOUND+64+16,[h.POOL]);h.compare(('retained-cache-health',health,tick,sound),True)
print('PASS116 captured-primary/resource-failure/cache boundary calls',flush=True)
matchedProfiles=[]
for level in range(1,15):
 for group,path in((b'GAME_HEALTH_POTION1','GAME/IMAGES/HEALTH/POTION1/HEALTH1.PID'),(b'GAME_HEALTH_POTION2','GAME/IMAGES/HEALTH/POTION2/HEALTH2.PID'),(b'GAME_HEALTH_POTION3','GAME/IMAGES/HEALTH/POTION3/HEALTH3.PID')):
  h.fresh();h.configureResources();h.bindPID(path);h.setupResources();h.ctx.composeAnimation=1;p=h.Profile();h.lib.claw_elevator_initialize_profile(level,h.C.byref(p),h.SetRect(),None);h.loot.configuration=p.words[0];h.loot.words[340]=0;h.put(h.A+0x170,[h.resourceTokens[group]])
  # Physical sound object metadata is an explicit transport fixture.
  h.put(h.resourceTokens[b'GAME_MILK']+16,[h.POOL])
  root=h.resourceTokens[group];h.put(root+20,[h.FRAMES]);h.put(root+100,[1,4])
  h.compare(('source-health-group/lazy-start',level,group));value=h.get(h.A+0xfc)[0];index=h.get(h.A+4)[0];h.compare(('source-health-group/tick',level,group));h.compare(('source-health-group/award',level,group),True);h.put(h.L+28,[29]);h.compare(('source-health-group/delete',level,group))
  matchedProfiles.append({'level':level,'imageGroup':group.decode(),'sourceRow':index,'sourceHealthAmount':value,'playerHealthAfter':h.get(h.PLAYER+0x10c)[0]})
assert sorted(set(p['sourceHealthAmount']for p in matchedProfiles))==[10,15,25]
print('PASS42 exact lazy-table potion-group→animation→health→cleanup histories (168 calls)',flush=True)
for level in(1,13):
 h.fresh();h.configureResources();h.loot.configuration=level;h.loot.words[340]=0;h.put(h.A+0x170,[h.resourceTokens[b'GAME_HEALTH_POTION1']]);h.mutation=4;h.compare(('resource-service-mutated-type-mask',level));assert h.get(h.A+0xd0)[0]==0x10000
print('PASS2 source resource-service type substitution branches',flush=True)
report={'calls':h.calls,'events':h.eventCount,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'globalBytes':0x30000,'retailInventory':h.json.load(open(h.WORK/'inventory.json')),'levelProfiles':profiles,'histories':histories,'matchedProfiles':matchedProfiles}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k not in('retailInventory','levelProfiles','histories','matchedProfiles')}),flush=True)
