#!/usr/bin/env python3
"""Soldier and bounded common entries versus original v1.0 instructions."""
import json,struct,zlib
import soldier_helpers as h
soldier=[0x48aa40,0x48b0c0,0x48b4b0,0x48b670,0x48b6b0,0x48b730,0x48b880,0x48ba00,0x48aff0,0x48afd0,0x405000]
common=[0x43ed70,0x43efe0,0x43fe00,0x43f500,0x404e00,0x404e10,0x44de30,0x440c70,0x440b20,0x440c90,0x44dbb0,0x43fa10]
for fn in soldier+common:
 for n in range(72):
  s,c=h.fresh();h.policy=n%2;h.mutate=n%2;h.resource_mode=n%3;h.clear_path=n%2;h.random_results=[h.rng.choice([0,1,4,5,20,40,41,99,100,0x7fffffff,0x80000000,0xffffffff]),h.rng.getrandbits(32)]
  h.animationResult=h.rng.choice([0,1,2]);s.actor[0x1a4//4]=h.rng.randrange(2);s.actor[0x19c//4]=h.rng.randrange(2)
  c.damageScale=h.rng.choice([-1,0,0.5,1,1.25,10]);c.healthScale=h.rng.choice([-1,0,0.5,1,1.25,10]);c.rangeScale=h.rng.choice([-1,0,0.5,1,4,10]);c.sharedStates.audioEnabled=0
  if fn==0x44de30:c.generic.levelWord=0;c.generic.playerActor[0x16c//4]=42;c.sharedStates.playerPrivate[0]=0
  if fn in(0x440b20,0x440c90):s.enemy[0x3bc//4]=s.enemy[0x3c0//4]=h.resourceViews[n%16].token;c.sharedStates.audioEnabled=n%2
  if fn==0x44dbb0:c.privateTail[(0x424-0x420)//4]=h.rng.choice([0,1,2,3,0x7fffffff,0xffffffff]);s.enemy[0x408//4]=h.resourceViews[n%16].token
  if fn==0x48ba00:s.enemy[0x1a0//4]=n%2;c.sharedStates.audioEnabled=n%2
  arg=h.rng.choice([0,1,0x100,0x101,0xffffffff])if fn==0x48afd0 else h.rng.choice([h.ids[b'LS_HOME'],h.ids[b'LS_IDLE'],h.ids[b'LS_FIRING'],h.ids[b'LS_DEAD']])if fn==0x48b0c0 else h.rng.getrandbits(32)
  h.compare(s,c,fn,(hex(fn),n),arg)
 print('PASS72',hex(fn),flush=True)
for mode in(0,29,30,1000):
 for n in range(16):
  s,c=h.fresh();h.policy=h.mutate=0;h.resource_mode=1;h.animationResult=0;s.primary[7]=mode;h.compare(s,c,0x48a980,('wrapper',mode,n))
for size in(0,8,9,32,33,64):
 s,c=h.fresh();h.policy=h.mutate=0;h.bitSetMode=size;h.compare(s,c,0x48aa40,('constructor-bit8',size))
h.bitSetMode=None;h.world=h.install_world();h.realPoints=True
for direction in(2,3):
 for rv in(0,1,40,41,0x7fffffff,0x80000000,0xfffffffd,0xffffffff):
  s,c=h.fresh();h.policy=h.mutate=0;h.random_results=[rv];s.enemy[0x18c//4]=direction;s.actor[0x50//4]=511;s.actor[0x124//4]=0;c.generic.playerActor[0x4c//4]=384
  s.enemy[0x80//4:0x88//4]=h.struct.unpack('<2I',h.struct.pack('<d',-100000.0));s.enemy[0x98//4:0xa0//4]=h.struct.unpack('<2I',h.struct.pack('<d',100000.0))
  h.compare(s,c,0x43fa10,('move-ahead-real-floor',direction,rv));assert(s.primary[7]==h.ids[b'LS_MOVEAHEAD'])==(not(direction==2 and rv in(40,0x7fffffff)))
h.world=h.install_world(True);h.ground=h.realGround=h.realQueries=h.realMotion=h.realPoints=True;h.policy=h.mutate=0;h.resource_mode=1;h.random_results=[99,201,24,55]
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
history=[];lootHandoffs=0
for index,record in enumerate(records):
 s,c=h.fresh();h.initialize_record(s,record);s.primary[7]=0;s.actor[0x70//4]=h.S;s.actor[0x78//4]=h.K;c.generic.tick=1000;c.generic.animationDelta=17;c.generic.forcedRandom=0;h.animationResult=0;h.finishAnimation=False;c.sharedStates.audioEnabled=0
 c.generic.playerActor[0x4c//4]=s.actor[0x4c//4]+3000;c.generic.playerActor[0x50//4]=s.actor[0x50//4];c.otherActor[:]=c.sharedStates.attackerActor
 h.compare(s,c,0x48a980,('actual16-startup',index));initial=(s.actor[0x4c//4],s.actor[0x50//4],s.actor[2],s.primary[7])
 for tick in(1017,2000,5000):c.generic.tick=tick;h.compare(s,c,0x48a980,('actual16-idle',index,tick))
 c.generic.playerActor[0x4c//4]=s.actor[0x4c//4]+100;c.generic.playerActor[0x50//4]=s.actor[0x50//4];c.generic.playerActor[0xcc//4]=5 if index%2 else 1;c.difficulty=index%3
 c.privateTail[(0x470-0x420)//4]=0;h.compare(s,c,0x48b670,('actual16-firing-entry',index))
 h.animationResult=1;c.generic.tick+=17;h.compare(s,c,0x48a980,('actual16-fire',index));assert s.enemy[0x1a0//4]==1
 h.animationResult=0;h.finishAnimation=True;c.generic.tick+=17;h.compare(s,c,0x48a980,('actual16-firing-complete',index));h.finishAnimation=False
 # Typed original projectile hit and death retain the Soldier/private/scene
 # views. The verified death body calls the exact WorldLoot handoff once.
 c.sharedStates.attackerActor[0x104//4]=2;c.sharedStates.attackerActor[0xd0//4]=0x10;c.sharedStates.attackerActor[0x138//4]=0x80000000;c.sharedStates.playerPrivate[5]=0;c.sharedStates.playerPrivate[0xe8//4]=1;s.actor[0x74//4]=h.OTHER;s.enemy[0x194//4]=h.A;s.actor[0x1a4//4]=s.actor[0x19c//4]=0
 h.compare(s,c,0x4dc830,('actual16-whole-hit',index));health=s.actor[0x10c//4]
 h.compare(s,c,0x4dc830,('actual16-duplicate-hit',index));assert s.actor[0x10c//4]==health
 shot=1
 while h.C.c_int32(s.actor[0x10c//4]).value>0:
  shot+=1;assert shot<=4;c.sharedStates.playerPrivate[0xe8//4]=shot;c.generic.tick+=401
  h.compare(s,c,0x4dc830,('actual16-retained-hit',index,shot));lootHandoffs+=sum(event[0][0]==0x42df90 for event in h.events)
 assert s.primary[7]==h.ids[b'LS_DEAD']
 # Re-entering a different original death mode must retain bit4's loot gate.
 h.compare(s,c,0x44e0c0,('actual16-death-mode1',index),1);assert not any(event[0][0]==0x42df90 for event in h.events)
 for elapsed in(999,1000,1001):c.generic.tick=s.enemy[0x3d8//4]+elapsed;h.compare(s,c,0x48a980,('actual16-death-update',index,elapsed))
 history.append({'index':index,'startup':initial,'finalState':s.primary[7],'delete':bool(s.actor[2]&0x10000)})
prefixEvents=sum(h.compare_failure(kind)for kind in('allocation','creation'))
assert lootHandoffs==16,lootHandoffs
report={'calls':h.calls,'events':h.event_count,'failurePrefixes':2,'failurePrefixEvents':prefixEvents,'originalAddresses':len(h.m.executed),'actualSoldierRecords':len(records),'actualLootHandoffs':lootHandoffs,'explicitCommonBoundaries':[hex(x)for x in sorted(h.unsupported)],'history':history}
(h.scratch/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='history'}),flush=True)
