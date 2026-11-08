#!/usr/bin/env python3
"""Original scenery callbacks, retained resource animation and actual WWD profiles."""
import collections,ctypes as C,json,re,struct
import scenery_logic_runtime_helpers as g
families={'DoNothing':0x461730,'DoNothingNormal':0x461750,'FrontCandy':0x461770,'BehindCandy':0x4617d0,'GooCoverup':0x461830,'GooBubble':0x461870,'FrontAniCandy':0x4618e0,'BehindAniCandy':0x461970}
for case in range(500):
 for name,f in families.items():
  g.setup(4);g.policy=case%3;g.put(g.L+0x1c,[g.rng.choice([0,0,1,5,23,0xffffffff])]);g.put(g.A+0x64,[g.rng.choice([0,0,1,0xffffffff,0x80000000])]);g.put(g.SETTINGS+0x124,[g.rng.choice([0,1,2,0xffffffff])])
  if case%2:g.put(g.A+0x190,[0])
  if case%7==0:g.lookupResult=0
  g.compareScenery(f,f'{name}/{case}')
print('PASS 4,000 original callback profiles with full actor/logic/ANI/image/settings/global buffers',flush=True)

for f in (0x461870,0x4618e0,0x461970):
 for compose in (0,1):
  g.setup(3);g.context.composeAnimation=compose;g.put(g.L+0x1c,[0]);g.put(g.A+0x190,[0]);g.put(g.A+0x64,[0]);g.policy=4
  g.compareScenery(f,f'directed/order/{f:x}/{compose}')
  if compose:assert g.words(g.A+0x64,1)==[123] and g.words(g.L+0x1c,1)==[99]
  for state in (1,5,23,0xffffffff):
   g.setup(3);g.context.composeAnimation=compose;g.put(g.L+0x1c,[state]);g.compareScenery(f,f'directed/nonzero/{f:x}/{compose}/{state}')

assets=g.assetFiles();records,counts=g.actualLevel1(assets);chosen=[r for r in records if r[3][1] in families];assert len(chosen)==594
cycle=assets['GAME/ANIS/CYCLE100.ANI'];assetReport=[];histories=0
for plane,index,v,ss,raw in chosen:
 name=ss[1];f=families[name];g.setup(4);g.policy=0
 g.constructor(v[0],v[5],v[6],v[7],f)
 # The actor constructor/inline caller initialization and image-binding bodies
 # execute in the original; the resource dictionary resolves this actual set.
 imagePrefix='LEVEL1/IMAGES/'+ss[2].removeprefix('LEVEL_')+'/'
 imageFiles={p:b for p,b in assets.items()if p.startswith(imagePrefix)and p.endswith('.PID')}
 assert imageFiles or ss[2]=='LEVEL_CANDELABRASINGLE',(ss[2],index)
 # Filename→ID enumeration is a declared resource-service profile, matching
 # the host adapter; that retail directory-enumeration body is not recovered.
 imageIDs=sorted(int(match.group()) if (match:=re.search(r'\d+$',p.rsplit('/',1)[1].split('.')[0])) else 0 for p in imageFiles)
 # SKULL.PID has no suffix: ID0 is an explicit fixture assignment, not a
 # claim about original retail filename→ID registration.
 g.bindImages(ss[2],imageIDs or [0],v[8],f'WWD/{index}/source-image-binding',missing=not imageFiles)
 aniName=ss[3]
 aniPath='LEVEL1/ANIS/MANICLES/MANICAL.ANI' if aniName=='LEVEL_MANICALS_MANICAL' else 'LEVEL1/ANIS/HAND/HAND1.ANI' if aniName=='LEVEL_HAND_HAND1' else 'GAME/ANIS/CYCLE100.ANI'
 g.installANI(assets[aniPath]);g.put(g.A+0x190,[0])
 if aniName in ('LEVEL_MANICALS_MANICAL','LEVEL_HAND_HAND1'):
  encoded=aniName.encode()+b'\0';g.heap[g.NAME-g.BASE:g.NAME-g.BASE+len(encoded)]=encoded
  g.compare(0x4c79e0,g.A,f'WWD/{index}/source-named-ANI',g.NAME,0)
 g.put(g.A+8,[g.words(g.A+8,1)[0]|0x40000|v[10]]);g.put(g.A+0x40,[v[11]])
 g.compareScenery(f,f'WWD/{plane}/{index}/initialize')
 for tick in range(12):
  g.globals.animationDelta=[0,1,16,33,99,100,500,0xffffffff][tick%8]
  g.compareScenery(f,f'WWD/{plane}/{index}/tick/{tick}');histories+=1
 g.destroy(f'WWD/{plane}/{index}/delete')
 assetReport.append({'logic':name,'imageSet':ss[2],'inputANI':aniName,'fixtureANI':aniPath,'imageIDs':imageIDs,'imageLookupAvailable':bool(imageFiles),'imageIDProfile':'explicit0 for suffix-less file; numeric-suffix otherwise, retail enumeration unproved','originalPixelResources':{p:g.hashlib.sha256(b).hexdigest()for p,b in imageFiles.items()}})
print('PASS 594 source constructor/init→scenery→actual ANI/image identities→deletion histories',flush=True)

# Explicit constructor allocation outcomes: source constructor allocates primary
# logic, not the scenery callbacks. Frozen constructor receives that outcome.
for fail in (False,True):
 for i in range(16):g.setup(2);g.constructor(i,689,4723,0,0x461970,fail=fail)
for f in (0x461870,0x4618e0,0x461970):
 g.setup(2);g.constructor(1,100,100,0,f);g.lookupResult=0;g.compareScenery(f,f'directed/missing-ANI/{f:x}/init')
 for tick in range(4):g.compareScenery(f,f'directed/missing-ANI/{f:x}/{tick}')

(g.WORK/'sanitizer-replay.bin').write_bytes(g.replay.getvalue())
g.replay.close()
report={'completeSceneryAndComposedCalls':g.calls,'baseConstructorInlineCallerInitializationProfiles':g.constructorCalls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'decodedOriginalRecords':g.decodes,'rawHeapBytes':g.SIZE,'actualLevel1Records':len(records),'chosenLevel1Records':len(chosen),'actualFamilyCounts':{n:counts[n]for n in families},'retainedActualScenerySteps':histories,'sanitizerReplayCases':g.replayCases,'actualResourceProfiles':list({json.dumps(r,sort_keys=True):r for r in assetReport}.values()),'externalServices':['4f6286 registry name lookup with caller-owned profile','4c88e0/4208e0 physical audio','4f63ec primary allocation outcome','4f6428 physical free']}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='actualResourceProfiles'}),flush=True)
