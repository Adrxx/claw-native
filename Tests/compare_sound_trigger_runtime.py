#!/usr/bin/env python3
import json,random
import sound_trigger_runtime_helpers as g
families={'SoundTrigger':0x48c1e0,'BigSoundTrigger':0x48c410,'SmallSoundTrigger':0x48c430,'HugeSoundTrigger':0x48c450,'TinySoundTrigger':0x48c470,'TallSoundTrigger':0x48c490,'WideSoundTrigger':0x48c4b0,'ClawDialogSoundTrigger':0x48c8f0,'ClawDialogBigSoundTrigger':0x48ca40,'ClawDialogSmallSoundTrigger':0x48ca60,'ClawDialogHugeSoundTrigger':0x48ca80,'ClawDialogTinySoundTrigger':0x48caa0,'ClawDialogTallSoundTrigger':0x48cac0,'ClawDialogWideSoundTrigger':0x48cae0,'AmbientSound':0x402cc0,'GlobalAmbientSound':0x402ca0,'SpotAmbientSound':0x402e20,'AmbientPosSound':0x402e00}
for seed in range(150):
 for name,f in families.items():
  g.setup(seed,f);r=random.Random(seed);g.put(g.L+28,[r.choice([0,5,11,23,30,1,29])]);g.put(g.A+0x108,[r.choice([0,1,2,0xffffffff,0xfffffffe,0x7fffffff])]);g.put(g.L+100,[r.choice([0,3])]);g.put(g.P+76,[r.choice([36,100,164,165,0xffffffff]),r.choice([136,200,264,265])]);g.globals.playerToken=0 if seed%11==0 else g.P;g.globals.audioManagerToken=0 if seed%13==0 else g.AUDIO
  g.compare(f,0,[g.A],f'{name}/{seed}')
print('PASS callback profiles',flush=True)

# Ambient object construction and retained real update/clear bodies.
for seed in range(120):
 for factory in (0x4022f0,0x402370,0x402400):
  g.setup(seed);r=random.Random(seed);g.put(g.RECT,[0,0,0,0]if seed%7==0 else [10,20,300,400]);args=[g.POOL if seed%11 else 0,100,g.RECT,seed%151,0]
  if factory==0x402400:args=[args[0],100,g.RECT,args[3],5,8,3,9,0]
  if seed%17==0:g.allocationFailures=[64 if factory==0x4022f0 else 72 if factory==0x402370 else 88]
  result=g.compare(factory,g.AMBIENT,args,f'factory/{factory:x}/{seed}')
  if result:
   for index,(x,y)in enumerate([(0,0),(10,20),(11,21),(299,399),(300,400),(1000,1000),(100,200)]):
    g.globals.stageDelta=[0,1,3,8,1000,0xffffffff,10][index];g.compare(0x4025c0,g.AMBIENT,[x,y],f'factory-tick/{factory:x}/{seed}/{index}',void=True)
   g.compare(0x402570,g.AMBIENT,[],f'factory-refresh/{factory:x}/{seed}',void=True)
   g.compare(0x402520,g.AMBIENT,[],f'factory-stop/{factory:x}/{seed}',void=True)
  g.compare(0x402270,g.AMBIENT,[],f'factory-cleanup/{factory:x}/{seed}',void=True)
print('PASS ambient creation/update/cleanup histories',flush=True)

# All actual Level1 records compose frozen WWD field construction and source
# auxiliary sound-name binding; namespace/physical sound ownership is explicit.
assets=g.assets();soundFiles={}
for path,payload in assets.items():
 for root,prefix in [('LEVEL1/SOUNDS/','LEVEL'),('CLAW/SOUNDS/','CLAW'),('GAME/SOUNDS/','GAME')]:
  if path.startswith(root)and path.endswith('.WAV'):soundFiles[prefix+'_'+path[len(root):-4].replace('/','_')]=(path,payload)
records=json.loads((g.WORK/'level1-records.json').read_text());assert len(records)==81;histories=0;resourceReport=[]
for record in records:
 name=record['strings'][1];f=families[name];flags=4 if name=='GlobalAmbientSound'else 1 if name=='AmbientSound'else 0 if name in('SpotAmbientSound','AmbientPosSound')else 2;g.setup(record['index'],f);g.sourceRecord(record,f,flags);soundName=record['strings'][3];found=soundName in soundFiles
 g.bindSound(soundName,found,f'WWD/{record["index"]}/sound-binding')
 if found:
  path,payload=soundFiles[soundName];# Source pool metadata profile supplied by frozen AudioResource duration rule.
  at=12;fmt=None;dataBytes=0
  while at+8<=len(payload):
   size=int.from_bytes(payload[at+4:at+8],'little')
   if payload[at:at+4]==b'fmt ':fmt=payload[at+8:at+8+size]
   if payload[at:at+4]==b'data':dataBytes=size
   at+=8+size+(size&1)
  assert fmt and dataBytes;rate=int.from_bytes(fmt[8:12],'little');duration=((dataBytes*1000)&0xffffffff)//rate;g.put(g.POOL+40,[duration])
  resourceReport.append({'requested':soundName,'path':path,'duration':duration,'payloadSHA256':g.hashlib.sha256(payload).hexdigest()})
 else:resourceReport.append({'requested':soundName,'missing':True})
 g.compare(f,0,[g.A],f'WWD/{record["index"]}/init')
 x,y=g.words(g.A+76,2)
 for tick,(px,py)in enumerate([(x,y),(x,y),(x+5000,y+5000),(x,y),(x,y),(x+64,y+64),(x+65,y+65),(x,y)]):
  g.put(g.P+76,[px,py]);g.globals.stageDelta=[0,1,16,1000,0xffffffff,100,500,8][tick]
  if tick==3:g.put(g.PP+0x80,[g.words(g.PP+0x80)[0]+1])
  if tick==4:g.globals.clawBusy=1
  if tick==7:g.globals.clawBusy=0
  g.compare(f,0,[g.A],f'WWD/{record["index"]}/actor/{tick}');g.compare(0x4025c0,g.AMBIENT,[px,py],f'WWD/{record["index"]}/ambient/{tick}',void=True);histories+=1
 if name=='SpotAmbientSound':g.put(g.L+28,[30]);g.compare(f,0,[g.A],f'WWD/{record["index"]}/cancel')
 g.compare(0x402270,g.AMBIENT,[],f'WWD/{record["index"]}/ambient-teardown',void=True)
print('PASS all81 actual Level1 record histories',flush=True)

# Callback metadata, charge asymmetry, busy queue acceptance and wrapped bounds.
for helper in (0x48c4d0,0x48cb00):
 for seed in range(80):
  g.setup(seed,random.Random(seed).choice(list(families.values())+[0xffffffff]));g.compare(helper,0,[g.A,g.L],f'directed/rectangle/{helper:x}/{seed}',void=True)
for f in (0x48c1e0,0x48c8f0):
 for charge in(0,1,2,0xffffffff,0xfffffffe,0x80000000,0x7fffffff):
  for busy in(0,1):
   g.setup(charge,f);g.put(g.L+28,[5]);g.put(g.A+0x108,[charge]);g.globals.clawBusy=busy;g.compare(f,0,[g.A],f'directed/charge-busy/{f:x}/{charge}/{busy}')
for mutation in(1,2,3):
 g.setup(77);g.mutation=mutation;g.put(g.L+28,[5]);g.compare(0x48c1e0,0,[g.A],f'directed/mutation-trigger/{mutation}')
 g.setup(78,0x402e20);g.mutation=mutation;g.compare(0x402e20,0,[g.A],f'directed/mutation-spot-init/{mutation}');g.compare(0x4025c0,g.AMBIENT,[100,200],f'directed/mutation-spot-update/{mutation}',void=True);g.put(g.L+28,[30]);g.compare(0x402e20,0,[g.A],f'directed/mutation-spot-cancel/{mutation}')
for x,y in((0x7fffffff,0),(0x80000000,0xffffffff),(0xffffffff,0xffffffff),(0x7fffffc0,0x80000020)):
 g.setup(81);g.put(g.A+76,[x,y]);g.put(g.P+76,[x,y]);g.put(g.L+28,[5]);g.compare(0x48c1e0,0,[g.A],'directed/wrapped-trigger')
# Sparse/failed list insertion is a declared service outcome: the source does
# not invent rollback/deletion for an object that has no list node.
g.setup(88,0x402e20);g.listFailure=True;g.compare(0x402e20,0,[g.A],'directed/null-list-node');g.put(g.L+28,[30]);g.compare(0x402e20,0,[g.A],'directed/null-list-node-cancel')
for seed in range(100):
 g.setup(seed);r=random.Random(seed);obj=g.ALLOC;g.put(obj,[0x50b01c,g.POOL,100,70,100,0]);g.put(obj+64,[r.choice([0,100,0x80000000,0xffffffff,0x7fffffff]),r.choice([0,200,0x80000000,0xffffffff])]);g.compare(0x402ac0,obj,[r.choice([0,100,0xffffffff,0x80000000]),r.choice([0,200,0x7fffffff]),0],f'directed/positional-wrap/{seed}',void=True)
# Direct finite entry branches not necessarily selected by retail records.
for seed in range(80):
 g.setup(seed);obj=g.ALLOC;r=random.Random(seed);pool=0 if seed%4==0 else g.POOL;point=0 if seed%3==0 else g.RECT
 g.compare(0x402610,obj,[pool,r.getrandbits(32),r.getrandbits(32),point,r.getrandbits(32)],f'directed/base-initialize/{seed}')
 g.compare(0x402a60,obj,[pool,100,70,point,100],f'directed/spot-initialize/{seed}')
 g.compare(0x4022d0,obj,[0],f'directed/object-destructor/{seed}')
 g.compare(0x402240,g.AMBIENT,[0 if seed%4==0 else g.AUDIO,r.getrandbits(32)],f'directed/manager-initialize/{seed}')
 for helper in(0x402840,0x4028c0):
  g.setup(seed);g.put(obj,[0x50b004,g.POOL,100,r.getrandbits(32),r.getrandbits(32),seed%2]);g.compare(helper,obj,[r.getrandbits(32),seed%3*1000,seed%2],f'directed/fade-helper/{helper:x}/{seed}',void=True)
# Refresh re-reads current manager center for each object. Explicit voice
# service mutation changes it between the two source virtual updates.
g.setup(110);a=[g.POOL,100,g.RECT,100,0];g.compare(0x4022f0,g.AMBIENT,a,'two-object-first');g.compare(0x4022f0,g.AMBIENT,a,'two-object-second');g.put(g.AMBIENT+40,[100,200]);g.mutation=3;g.compare(0x402570,g.AMBIENT,[],'directed/two-object-refresh-live-center',void=True)
for seed in range(64):
 g.constructManager(seed);g.compare(0x402240,g.AMBIENT,[g.AUDIO,70],f'directed/source-manager-profile/{seed}')
 g.compare(0x4f5133,g.AMBIENT+8,[seed],f'directed/CPtrList-constructor/{seed}')
# Source dialog trigger→frozen speech queue→scheduled play→busy→expiry,
# preserving the same raw actor/primary buffers and shared busy aliases.
for seed in range(32):
 g.setup(seed,0x48ca60);g.put(g.MANAGER+0x118,[1]);g.put(g.MANAGER+0x12c,[70]);g.put(g.POOL+40,[750]);g.compare(0x48ca60,0,[g.A],f'joined-speech/{seed}/trigger-init');g.compare(0x48c630,0,[g.CL],f'joined-speech/{seed}/idle');g.compare(0x48ca60,0,[g.A],f'joined-speech/{seed}/queue');g.compare(0x48c630,0,[g.CL],f'joined-speech/{seed}/scheduled-play')
 for tick in range(5):
  g.globals.stageDelta=[0,1,749,1,16][tick];g.compare(0x48c630,0,[g.CL],f'joined-speech/{seed}/speech/{tick}');g.compare(0x48ca60,0,[g.A],f'joined-speech/{seed}/trigger/{tick}')
for present,logic,busy,playerMode in((0,1,0,4),(1,0,0,4),(1,1,1,4),(1,1,0,28),(1,1,0,31),(1,1,0,5004),(1,1,0,4)):
 g.setup(177,0x48c8f0);g.put(g.L+28,[5]);g.globals.clawActorToken=g.CL if present else 0;g.globals.clawBusy=busy;g.put(g.CL+0x6c,[g.SL if logic else 0]);g.put(g.PL+28,[playerMode]);g.compare(0x48c8f0,0,[g.A],f'directed/queue-gates/{present}/{logic}/{busy}/{playerMode}')
# Meaningful unsafe prefixes: charge mutation precedes the missing player's
# private checkpoint read; synthetic out-of-domain RNG exposes signed-idiv trap.
g.setup(90);g.put(g.L+28,[5]);g.put(g.PL+20,[0]);g.failure(0x48c1e0,0,[g.A],'unsafe-player-private',0x48c2ff,1)
g.setup(91);g.randomWords=[0x80000000];g.failure(0x402400,g.AMBIENT,[g.POOL,100,g.RECT,100,0,1,0,0xfffffffe,0],'unsafe-signed-rng-division',0x4024b8,3)
g.replayWriter.close();(g.WORK/'sanitizer-replay.bin.gz').write_bytes(g.replay.getvalue())
report={'completeOriginalCalls':g.calls,'orderedFullHeapEvents':g.eventCount,'rawHeapBytes':g.SIZE,'originalInstructionAddresses':len([x for x in g.m.executed if x<0x1000000 and x not in g.ADAPTERS]),'unsafeOriginalPrefixes':g.unsafePrefixes,'sanitizerWholeHeapReplays':g.replayCases,'sourceManagerConstructorBlocks':g.constructorBlocks,'joinedTriggerSpeechHistories':32,'actualLevel1Records':81,'retainedActualSteps':histories,'actualFamilyCounts':dict(g.collections.Counter(r['strings'][1]for r in records)),'actualSoundProfiles':resourceReport,'externalServices':['declared exact resource-name transport / source4c7a40 binding','physical allocation/free','CPtrList AddTail/remove/clear','voice play/stop/fade/volume/pan and manager flush','CRT RNG value source']}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='actualSoundProfiles'}),flush=True)
