#!/usr/bin/env python3
"""Whole ordinary Bullet constructor/controller/full raw state oracle."""
import bullet_helpers as h
for fn in(0x473c50,0x4107c0,0x4741f0,0x474290,0x4742f0,0x473f40,0x484d90,0x456030,0x4dca10,0x4063b0,0x4c7970):
 for n in range(100):
  s,c=h.fresh();h.policy=0;h.mutate=n%2;h.resource_mode=n%3;h.animationResult=n%2
  arg=h.ids[b'LS_FALLING']if fn==0x473f40 else h.rng.choice([0x524130,0x52c4a0])if fn==0x4c7970 else h.rng.choice([0,1,0x100,0x101,0xffffffff])
  h.compare(s,c,fn,(hex(fn),n),arg)
 print('PASS100',hex(fn),flush=True)
for state in(0,29,30,1000,h.ids[b'LS_FALLING']):
 for n in range(24):
  s,c=h.fresh();h.policy=h.mutate=0;h.resource_mode=1;s.primary[7]=state;h.compare(s,c,0x40fec0,('wrapper',state,n))
print('PASS',h.calls,'whole original calls;',h.event_count,'ordered complete snapshots;',len(h.m.executed),'original instruction addresses',flush=True)
# Retain actual Level1 Soldier initialization and firing geometry, then execute
# Bullet callbacks at the actual allocated child token against original tiles.
import json,struct,zlib
h.policy=h.mutate=0;h.resource_mode=1;h.animationResult=0;h.finishAnimation=False;h.world=h.install_world(True);h.ground=h.realGround=h.realQueries=h.realMotion=h.realPoints=True
@h.ObjectDependency
def soldier_object_dependency(s,c,e,user):
 if e.contents.function==0x4f6286:c.contents.entryToken=0x10ff100;c.contents.entryCallback=0x48a980;c.contents.entryFlags=0;return 0x10ff100
 return 0
h.object_dependency=soldier_object_dependency
raw=(h.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
records=[]
for plane in range(struct.unpack_from('<I',raw,732)[0]):
 ph=struct.unpack_from('<40I',raw,offset+160*plane);position=ph[35]
 for _ in range(ph[32]):
  words=struct.unpack_from('<71I',raw,position);size=284+sum(words[1:5]);logic=raw[position+284+words[1]:position+284+words[1]+words[2]].split(b'\0')[0]
  if logic==b'Soldier':records.append(raw[position:position+size])
  position+=size
assert len(records)==16
spawned=[];histories=[]
for index,record in enumerate(records):
 s,c=h.oldFresh();h.currentBullet=h.view(c);h.initialize_record(s,record);s.primary[7]=0;s.actor[0x70//4]=h.S;s.actor[0x78//4]=h.K;c.generic.tick=1000;c.generic.animationDelta=17;c.generic.forcedRandom=0;c.sharedStates.audioEnabled=0;h.animationResult=0
 h.rootHeader[5]=h.FRAME_DATA+16;h.rootHeader[25]=h.rootHeader[26]=1;h.leafHeader[6:10]=[6,5,0,0]
 h.jointSoldier=True;h.oldCompare(s,c,0x48a980,('actual16-Soldier-startup',index));h.jointSoldier=False
 c.generic.playerActor[0x4c//4]=(s.actor[0x4c//4]+(100 if index%2 else -100))&0xffffffff;c.generic.playerActor[0x50//4]=s.actor[0x50//4];c.generic.playerActor[0xcc//4]=5 if index%3==2 else 1;c.difficulty=index%3;c.privateTail[(0x470-0x420)//4]=0
 h.jointSoldier=True;h.oldCompare(s,c,0x48b670,('actual16-Soldier-firing-entry',index));h.jointSoldier=False
 h.animationResult=1;c.generic.tick+=17;h.compare_soldier_spawn(s,c,('actual16-spawn',index));assert c.effectPrimary[6]==h.EFE and c.effectPrivate[0]==0x50b714
 vx=struct.unpack('<d',bytes(c.effectPrivate)[0x50:0x58])[0];assert vx in(-500,500);assert c.effectActor[0x104//4]==10 and c.effectActor[0xd0//4]==0x40
 spawned.append(list(c.effectActor));start=list(c.effectActor[0x4c//4:0x54//4]);frames=0
 for frame in range(80):
  c.generic.tick+=17;h.compare_fx(s,c,0x40fec0,('actual16-flight',index,frame));frames+=1
  if c.effectActor[2]&0x10000:break
 h.compare_fx(s,c,0x484d90,('actual16-private-destroy',index),1)
 histories.append({'record':index,'launch':start,'vx':vx,'frames':frames,'end':list(c.effectActor[0x4c//4:0x54//4]),'delete':bool(c.effectActor[2]&0x10000)})
print('PASS16 actual Soldier→Bullet→Level1 flight histories',flush=True)
# Directed solid-wall flights expose the original one-frame collision/delete lag.
h.world=h.install_world();h.realGround=False;h.realMotion=h.realPoints=True
for row in range(3,8):h.world.cells[row*16+4]=1
wallHits=0
for direction in(-1,1):
 s,c=h.oldFresh();h.currentBullet=h.view(c);h.policy=h.mutate=0;h.animationResult=h.resource_mode=1;s.enemy[0x1a0//4]=0;s.actor[0x1a4//4]=s.actor[0x19c//4]=0;s.primary[3]=h.SC
 s.actor[0x4c//4]=400 if direction<0 else 130;s.actor[0x50//4]=338;c.generic.tick=1000;c.generic.forcedRandom=0
 c.privateTail[(0x454-0x420)//4]=0;c.privateTail[(0x458-0x420)//4]=-38;c.privateTail[(0x45c-0x420)//4]=direction*500
 h.compare_soldier_spawn(s,c,('wall-spawn',direction));hit=False
 for frame in range(80):
  was=c.effectPrivate[0x120//4]&0x10000;c.generic.tick+=17;h.compare_fx(s,c,0x40fec0,('wall-flight',direction,frame))
  now=c.effectPrivate[0x120//4]&0x10000
  if now and not was:assert not c.effectActor[2]&0x10000;hit=True
  if was:assert c.effectActor[2]&0x10000;break
 assert hit,('wall must collide',direction);wallHits+=1
 h.compare_fx(s,c,0x484d90,('wall-private-destroy',direction),1)
print('PASS2 actual collision→next-frame Delete→private destruction',flush=True)
# The original interaction election remains an external scene boundary. Feed
# the actually created Soldier actor to whole CaptainClawHit, comparing every
# player/damage/input/global buffer and ordered callback snapshot.
import bullet_player_hit_helpers as player
q,check,playerReport=player.install(h)
for record,actor in enumerate(spawned):
 for health in(1,9,10,11,100):
  for mode in(1,4,5,8):
   s,t,i=q['new']();t.attackerActor[:]=actor;s.actor[0x74//4]=t.attackerToken=q['ATTACKER'];s.actor[0x10c//4]=health;s.actor[0xcc//4]=mode
   s.privateWords[75]=s.privateWords[1]=s.privateWords[6]=0;s.logicState=24;s.powerup=0;i.cheat=0;i.invulnerabilityTimer=0;s.privateWords[31]=3
   q['gameMode']=record%5;q['marker']=record%4;q['randomResults']=[7,2,21];q['resolvedSound']=q['SOUND']if record%2 else 0
   check(s,t,i,('actual-created-Bullet-player-hit',record,health,mode));assert t.attackerActor[2]&0x10000
# Retain hurt/death player history; subsequent contact observes original gates.
for record,actor in enumerate(spawned):
 s,t,i=q['new']();t.attackerActor[:]=actor;s.actor[0x74//4]=t.attackerToken=q['ATTACKER'];s.actor[0x10c//4]=11;s.actor[0xcc//4]=1
 s.privateWords[75]=s.privateWords[1]=s.privateWords[6]=0;s.logicState=24;s.powerup=0;i.cheat=0;i.invulnerabilityTimer=0;s.privateWords[31]=3
 for hit in range(3):
  check(s,t,i,('retained-Bullet-player-hit',record,hit));s.animationDelta=s.stageDelta=17
failureEvents=h.compare_allocation_failure()
report={'failurePrefixes':1,'failurePrefixEvents':failureEvents,'calls':h.calls,'events':h.event_count,'originalAddresses':len(h.m.executed),'actualSoldierRecords':16,'solidWallChains':wallHits,'playerHit':playerReport,'playerHitAddresses':len(q['o'].executed),'histories':histories}
(h.scratch/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='histories'}),flush=True)
