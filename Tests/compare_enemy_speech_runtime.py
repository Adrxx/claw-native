#!/usr/bin/env python3
import enemy_speech_helpers as h
for fn in(0x48ce40,0x48ceb0):
 for speaker in(0,h.A):
  for resource in(0,h.SOUND if fn==0x48ce40 else 0x529888):
   for actor in(0,h.EN):
    for busy in(0,1,0xffffffff):
     for force in(0,1,0xffffffff):
      s,c=h.prepared(force);h.globals.enemyActorToken=actor;h.globals.enemyBusy=busy;h.compare_speech(s,c,fn,('queues',fn,speaker,resource,actor,busy,force),(speaker,resource,force))
for fn in(0x48cc60,0x48c630):
 actor,logic=(h.EN,h.ENL)if fn==0x48cc60 else(h.CL,h.CLL)
 for mode in(0,1,5,15,29,1000,1001,0xffffffff):
  for enabled in(0,1):
   for audio in(0,1):
    for speaker in(0,h.A):
     s,c=h.prepared(mode);h.globals.speakerToken=speaker;h.globals.audioManagerToken=audio;h.extra_put(logic+0x1c,[mode]);h.extra_put(logic+0x130,[100]);h.extra_put(actor+0x184,[h.SOUND]);h.extra_put(h.MANAGER+0x118,[enabled]);h.compare_speech(s,c,fn,('actorstates',fn,mode,enabled,audio,speaker),(actor,))
print('PASS queue gates and both actor lifecycle profiles',flush=True)
for fn in(0x48cc60,0x48c630):
 actor,logic=(h.EN,h.ENL)if fn==0x48cc60 else(h.CL,h.CLL)
 for volume in(0,79,80,89,90,99,100,0x7fffffff,0x80000000,0xffffffff):
  for duration in(0,1,16,100,0xffffffff):
   s,c=h.prepared(volume);h.extra_put(actor+0x184,[h.SOUND]);h.extra_put(logic+0x1c,[1001]);h.extra_put(h.POOL+0x28,[duration]);h.extra_put(h.MANAGER+0x12c,[volume]);h.compare_speech(s,c,fn,('signed volume+duration',fn,volume,duration),(actor,))
 for image in(0,1):
  s,c=h.prepared(image);h.imageFound=bool(image);h.extra_put(logic+0x1c,[0]);h.compare_speech(s,c,fn,('missing image',fn,image),(actor,))
for mutation in(1,2,3,4):
 s,c=h.prepared(mutation);h.speechMutation=mutation
 if mutation==2:h.u.mem_unmap(0,4096);h.zero_mapped=False
 try:h.compare_speech(s,c,0x48ceb0,('name callback live globals/pointers',mutation),(h.A,0x529888,0),fault_expected=mutation==2)
 finally:
  if mutation==2:h.u.mem_map(0,4096);h.zero_mapped=True
for mutation,fn,actor,logic in((5,0x48cc60,h.EN,h.ENL),(6,0x48c630,h.CL,h.CLL)):
 s,c=h.prepared(mutation);h.speechMutation=mutation;h.extra_put(actor+0x184,[h.SOUND]);h.extra_put(logic+0x1c,[1001]);h.compare_speech(s,c,fn,('play callback preserves raw actor/global mutation',mutation),(actor,))
# Signed RNG remainder dispatch picks exactly one original player speech name.
for player in(0,h.P):
 for category in(0,2,32,33,0xffffffff):
  for value in(0,1,2,3,4,5,6,7,8,9,10,99,0x7fffffff,0x80000000,0xffffffff):
   s,c=h.prepared(value);h.globals.playerToken=player;h.random_results=[value];h.policy=h.mutate=0;h.compare_speech(s,c,0x420370,('death name route',player,category,value),(category,))
# Retain the source's real CRT LCG update, adapting only thread-local lookup.
for seed in(0,1,42,0x7fffffff,0x80000000,0xffffffff):
 s,c=h.prepared(seed);h.extra_put(h.RNG_TLS+0x14,[seed]);h.realSpeechRNG=True
 try:
  for step in range(8):h.compare_speech(s,c,0x420370,('whole source RNG retained name routing',seed,step),(2,))
 finally:h.realSpeechRNG=False
for mode in(5,15,1001):
 for speaker in(0,h.A,h.P):
  for elected in(0,h.A,h.P):
   s,c=h.prepared(mode);h.globals.speakerToken=speaker;h.extra_put(h.ENL+0x1c,[mode]);h.compare_speech(s,c,0x48cf50,('cancel registered speaker',mode,speaker,elected),(elected,));h.compare_speech(s,c,0x48cf90,('speaker identity equality',mode,speaker,elected),(elected,))
# Retain actual named generic construction and both source speech lifetimes.
for profile in(0,1):
 s,c=h.prepared(profile);h.compare_speech(s,c,0x4c8da0,('source startup creator',profile),create_profile=profile)
 actor=h.created[0];logic=h.extra_get(actor+0x6c)[0];fn=0x48cc60 if profile else 0x48c630
 h.compare_speech(s,c,fn,('source startup registration',profile),(actor,));h.compare_speech(s,c,fn,('source startup idle',profile),(actor,))
 queue=0x48ce40 if profile else 0x48c820;args=(h.A,h.SOUND,0)if profile else(h.SOUND,0)
 assert h.compare_speech(s,c,queue,('retained queue',profile),args)==1
 h.compare_speech(s,c,fn,('retained play begin',profile),(actor,))
 assert h.extra_get(logic+0x1c)[0]==15
 # First play does not set busy until subsequent state15 follow visit.
 assert (h.globals.enemyBusy if profile else h.globals.clawBusy)==0
 assert h.compare_speech(s,c,queue,('accepted prebusy replacement',profile),args)==1
 h.compare_speech(s,c,fn,('replacement play',profile),(actor,));h.globals.stageDelta=0;h.compare_speech(s,c,fn,('busy follow',profile),(actor,))
 assert h.compare_speech(s,c,queue,('busy rejection',profile),args)==0
 forced=(*args[:-1],1);assert h.compare_speech(s,c,queue,('force replacement',profile),forced)==1
 h.compare_speech(s,c,fn,('force starts',profile),(actor,));h.globals.stageDelta=100;h.compare_speech(s,c,fn,('duration expiry',profile),(actor,));h.compare_speech(s,c,fn,('idle clears busy/speaker',profile),(actor,))
 h.extra_put(logic+0x1c,[29]);h.compare_speech(s,c,fn,('source deregistration',profile),(actor,))
print('PASS retained genericcreation/registration→queue→play/replacement/busy/force/expiry/deregister',flush=True)

# Failed name/resource resolution never queues a sound. Null actor allocations
# in the source factory use the frozen SceneActor diagnostic policy; list node
# exhaustion retains its stores before the original bad-pointer dereference.
for fn,args in((0x48ceb0,(h.A,0x529888,0)),(0x48c8a0,(0x524e04,0))):
 s,c=h.prepared(fn);h.soundFound=False;assert h.compare_speech(s,c,fn,('missing sound',fn),args)==0
for profile in(0,1):
 s,c=h.prepared(profile);h.metadataFound=False;assert h.compare_speech(s,c,0x4c8da0,('missing callback metadata',profile),create_profile=profile)==0
 for failure in(1,2):
  s,c=h.prepared(failure);h.failAlloc=failure
  with h.null_fault_scope():h.compare_speech(s,c,0x4c8da0,('allocator failure prefix',profile,failure),create_profile=profile,fault_expected=True)
for delta in(0,1,16,100,0x80000000,0xffffffff):
 for timer in(0,1,16,100,0x80000000,0xffffffff):
  for deleted in(0,1):
   s,c=h.prepared(timer);h.globals.stageDelta=delta;s.actor[2]=0x10000 if deleted else 0;h.extra_put(h.ENL+0x1c,[15]);h.extra_put(h.ENL+0x130,[timer]);h.extra_put(h.EN+0x184,[h.SOUND]);h.compare_speech(s,c,0x48cc60,('unsigned timer/speaker deletion',delta,timer,deleted),(h.EN,))
for mode in(0,28,5004,5005,0xffffffff):
 for force in(0,1):
  s,c=h.prepared(mode);h.playerLogic[7]=mode;h.compare_speech(s,c,0x48c820,('player queue death gate',mode,force),(h.SOUND,force))
print('PASS resource failures/allocator prefixes/unsigned expiry/deleted owner/player death gates',flush=True)

# Actual WWD profiles, actual constructor bodies and real Level1 tile queries.
# Actor/player placement and collision election are explicit fixture inputs;
# registry lookup transports resources and physical audio remains a leaf.
import struct,zlib,json
h.world=h.install_world(True);h.ground=h.realGround=h.realQueries=h.realMotion=h.realPoints=True
raw=(h.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
records=[]
for plane in range(struct.unpack_from('<I',raw,732)[0]):
 ph=struct.unpack_from('<40I',raw,offset+160*plane);pos=ph[35]
 for _ in range(ph[32]):
  words=struct.unpack_from('<71I',raw,pos);length=284+sum(words[1:5]);logic=raw[pos+284+words[1]:pos+284+words[1]+words[2]].split(b'\0')[0]
  if logic in(b'Officer',b'Soldier'):records.append((logic.decode(),raw[pos:pos+length]))
  pos+=length
assert len(records)==42
histories=[]
for index,(kind,record)in enumerate(records):
 s,c=h.prepared_officer(index)if kind=='Officer'else h.prepared(index)
 h.resource_mode=1;h.policy=h.mutate=0;h.compose=0;h.random_results=[99,0];h.initialize_record(s,record);s.primary[7]=0
 h.compare_caller(s,c,0x462410 if kind=='Officer'else 0x48aa40,('actual42 source ctor',kind,index),(h.A,),entry_kind='officer'if kind=='Officer'else'soldier')
 h.image_profile(s,kind);s.enemy[0x184//4]=0;s.actor[0x38//4]=0;h.extra_put(h.ENL+0x1c,[5]);h.globals.enemyBusy=0;h.globals.enemyActorToken=h.EN
 for token in h.resourceTokens.values():h.extra_put(token+0x10,[h.POOL])
 fn=0x463020 if kind=='Officer'else 0x48b4b0
 h.compare_caller(s,c,fn,('actual42 HOME queue',kind,index),entry_kind='officer'if kind=='Officer'else'soldier')
 assert h.extra_get(h.ENL+0x1c)[0]==1001,(kind,index,'HOME did not queue')
 selected=h.extra_get(h.EN+0x184)[0];assert selected
 h.compare_speech(s,c,0x48cc60,('actual42 begin voice',kind,index),(h.EN,));h.globals.stageDelta=16
 h.compare_speech(s,c,0x48cc60,('actual42 speaker follow',kind,index),(h.EN,));assert h.globals.enemyBusy==1 and h.globals.speakerToken==h.A
 # Repeat a source queue attempt while the shared dialog actor is busy.
 if kind=='Soldier':c.privateTail[(0x450-0x420)//4]=0
 h.compare_caller(s,c,fn,('actual42 HOME while busy',kind,index),entry_kind='officer'if kind=='Officer'else'soldier')
 assert h.extra_get(h.ENL+0x1c)[0]==15
 h.compare_speech(s,c,0x48cf50,('actual42 speaker cancellation',kind,index),(h.A,));h.compare_speech(s,c,0x48cc60,('actual42 cancelled expiry',kind,index),(h.EN,));h.compare_speech(s,c,0x48cc60,('actual42 idle reset',kind,index),(h.EN,))
 # Actual typed-death caller invokes420370, which selects/queues Claw's line.
 h.random_results=[0,index%10];s.actor[0x74//4]=h.OTHER;c.sharedStates.attackerActor[0xd0//4]=2 if index%2 else 32;c.otherActor[:]=c.sharedStates.attackerActor;h.globals.clawBusy=0;h.globals.clawActorToken=h.CL;h.extra_put(h.CLL+0x1c,[5]);h.playerLogic[7]=0
 h.compare_caller(s,c,0x44e0c0,('actual42 death→Claw speech',kind,index),(0,),entry_kind='human')
 assert h.extra_get(h.CLL+0x1c)[0]==1001
 h.compare_speech(s,c,0x48c630,('actual42 Claw voice begin',kind,index),(h.CL,));h.globals.stageDelta=100;h.compare_speech(s,c,0x48c630,('actual42 Claw voice expiry',kind,index),(h.CL,));h.compare_speech(s,c,0x48c630,('actual42 Claw voice idle',kind,index),(h.CL,))
 histories.append({'record':index,'kind':kind,'queuedSoundToken':selected,'npcTimerDuration':100,'deathChoice':index%10})
report={'wholeOriginalCalls':h.speech_calls+h.calls,'orderedFullSnapshots':h.speech_events+h.event_count,'originalAddresses':len(h.m.executed),'extraHeapBytes':h.EXTRA_SIZE,'actualOfficerProfiles':sum(k=='Officer'for k,r in records),'actualSoldierProfiles':sum(k=='Soldier'for k,r in records),'retainedCallerHistories':len(histories),'realCRTLCGRetainedSteps':48,'physicalAudio':'4b45f0 explicit adapter','rng':'directed caller choices and48 whole original4a3050 steps with explicit TLS adapter','history':histories}
(h.scratch/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='history'}))
