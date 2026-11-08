#!/usr/bin/env python3
"""Whole unchanged-v1.0 gem bodies; raw snapshots and ordered host services."""
import end_level_gem_runtime_helpers as h
import random,struct,json
r=random.Random(0x43d0f0)
# Full initialized construction, bounds, unsigned clock, callback and live collision.
for seed in range(96):
 h.setup(seed);h.put(0x537210,[r.choice([0,1,1000,0x7fffffff,0x80000000,0xffffffff])]);h.put(h.A+0x4c,[r.randrange(-3000,3001),r.randrange(-3000,3001)]);h.put(h.A+0x148,[r.randrange(-200,201),r.randrange(-200,201)]);h.put(h.L+0x2c,[r.choice([0,-100,100]),r.choice([0,1000,2000]),r.choice([0,-100,100]),r.choice([0,1000,2000])]);h.policy=seed%3;h.compare(0x43cb20,h.E,[h.A])
 h.compare(0x43d0f0,h.E,[r.randrange(-2000,2001),r.randrange(-2000,2001)]);h.compare(0x43d070,h.E)
# Wrapper branch and dynamic boss creator, target landing and rebind chain.
for seed in range(32):
 h.setup(seed);h.put(h.BOSS+0x458,[h.BASE+0x42000]);h.put(h.BASE+0x42000+16,[h.BASE+0x41000]);h.put(0x532c0c,[seed%2]);h.compare(0x40e5c0,h.BOSS);h.compare(0x40e5c0,h.BOSS)
 for frame in range(90):
  h.put(0x537210,[1000+(frame+1)*18]);h.compare(0x43ca60,0,[h.A])
  if h.get(h.L+28)[0]==5:break
 assert h.get(h.L+28)[0]==5,(seed,'no source landing')
 h.compare(0x4701b0,0,[h.A]);h.put(h.L+28,[29]);h.compare(0x4701b0,0,[h.A]);h.put(h.E,[0x50db2c]);h.compare(0x484d90,h.E,[seed%2])
# Inline target equation3D ordering, tiny/zero acceleration and large integers.
for seed in range(160):
 h.setup(seed);h.compare(0x43cb20,h.E,[h.A])
 for axis in range(3):h.number(h.E+0x38+axis*8,r.choice([0.,.01,100.,-100.,2250.]));h.number(h.E+0x68+axis*8,r.uniform(-1000,1000))
 h.compare(0x43d0f0,h.E,[r.choice([1,-1,2147483647,-2147483648,r.randrange(-3000,3001)]),r.choice([1,-1,2147483647,-2147483648,r.randrange(-3000,3001)])])
# Player restoration, savedANI/attachedactor branches and no-op guards.
for seed in range(64):
 h.setup(seed);h.put(h.PP,[seed%2]);h.put(h.PP+4,[(seed//2)%2]);h.put(h.PP+0x12c,[h.OTHER if seed%3==0 else 0]);h.put(h.OTHER_L+24,[h.BASE+0x45000]);h.compare(0x4205b0,0)
 h.compare(0x4205b0,0)
for guard in(0,1,24,5010,0xffffffff):
 h.setup();h.put(h.PL+28,[guard]);h.compare(0x4205b0,0)
h.setup();h.put(0x537e88,[0]);h.compare(0x4205b0,0)
h.setup();h.put(h.P+0x6c,[0]);h.compare(0x4205b0,0)
# Pickup callback varies config/type/roots, glitter allocation and animation states.
for seed in range(96):
 h.setup(seed);h.mode=[3,4][seed%2];h.put(h.CONFIG+20,[[0,1,13,2][(seed//2)%4]]);h.put(h.SAVED-8,[(seed//8)%2]);h.put(h.APP+0x124,[(seed//16)%2]);h.put(h.A+0x64,[0 if seed%3==0 else 3000]);h.put(h.A+0xd0,[1]);h.put(h.A+0x170,[h.ROOTIMAGE if seed%5 else h.ROOTIMAGE+128]);h.put(h.A+0x174,[h.IMAGE if seed%7 else 0]);h.creationNull=seed%11==0;h.compare(0x4701b0,0,[h.A]);h.compare(0x4701b0,0,[h.A]);h.put(h.L+28,[29]);h.compare(0x4701b0,0,[h.A]);h.put(h.L+28,[r.choice([1,30,1000,0xffffffff])]);h.compare(0x4701b0,0,[h.A])
# Derived dispatch range/error/fallback and absent callback are real services.
for state,fn in[(2000,0x43d070),(2000,0),(1999,0),(2001,0),(0xffffffff,0)]:
 h.setup();h.compare(0x43cb20,h.E,[h.A]);h.put(h.FUNCS,[fn]);h.compare(0x43cdc0,h.E,[state])
# Actual five WWD placements, plus actual ANI records decoded by source4d76e0.
inv=json.loads((h.WORK/'inventory.json').read_text());actual=[]
for row in inv['records']:
 for profile in range(4):
  h.setup(row['level']);w=row['words'];h.put(h.A+0x4c,[w[5],w[6]]);h.put(h.A+0x64,[w[7]]);h.put(h.A+8,[w[9]|0x40000]);h.put(h.A+0xd0,[1]);h.put(h.CONFIG+20,[row['level']]);h.put(h.APP+0x124,[profile%2]);h.mode=3;h.resourceMode='animation';h.lookupResult=h.SEQ
  path=h.ROOT/'work/original-disc-assets/GAME/ANIS/POWERUP.ANI';images=[int(p.stem[7:])for p in(h.ROOT/'work/original-disc-assets/GAME/IMAGES/MAPPIECE').glob('MAPFRAG*.PID')];count=h.decodeFile(path,images);h.compare(0x4701b0,0,[h.A])
  for tick in range(80):
   delta=[0,1,18,50,200][tick%5];h.put(0x5430c4,[delta]);h.anim.animationDelta=delta;h.compare(0x4701b0,0,[h.A])
  h.mode=3 if profile<2 else 4;h.put(h.CONFIG+0xbcc,[profile%2]);h.put(h.A+0xfc,[0x26ad]);h.put(h.A+0xd0,[0x100]);h.compareAward();h.compare(0x4701b0,0,[h.A]);h.put(h.L+28,[29]);h.compare(0x4701b0,0,[h.A])
 actual.append({'level':row['level'],'plane':row['plane'],'index':row['index'],'worldSHA256':row['worldSHA256'],'ANI':str(path.relative_to(h.ROOT)),'recordCount':count,'actualImageIDs':images})
# Shared loot initializer whole source through the callback's first-use branch.
for seed in range(3):
 h.setup(seed);h.loot.words[340]=0;h.loot.configurationWord=[0,1,13][seed];h.resourceMode='loot';h.lookupResult=0;h.put(h.SC+0x10,[h.BASE+0x60000]);h.put(h.SC+0x14,[h.BASE+0x61000]);h.compare(0x4701b0,0,[h.A])
# Verified unchecked source fault prefixes preserve already committed latch/state.
h.setup();h.creationNull=True;h.comparePrefix(0x40e5c0,h.BOSS,[],0x40e60f);assert h.get(h.BOSS+0x45c)[0]==1
h.setup();h.allocationNull=True;h.comparePrefix(0x43ca60,0,[h.A],0x43cabe);assert h.get(h.L+28)[0]==1000
# Normal zero target performs restore/rebind before storing target/velocity.
h.setup();h.compare(0x43cb20,h.E,[h.A]);h.compare(0x43d0f0,h.E,[0,0]);assert h.get(h.L+28)[0]==5
# Original0/29/30/1000 wrapper branches and exact base no-ops.
for state in(0,29,30,1000):
 h.setup();h.compare(0x43cb20,h.E,[h.A]);h.put(h.L+28,[state]);h.compare(0x43ca60,0,[h.A])
for f,a in[(0x4c96b0,[]),(0x4bb030,[]),(0x4c9e30,[h.NAME]),(0x456030,[])]:
 h.setup();h.compare(f,h.E,a)
# Reentrant external services exercise fresh versus cached source aliases.
h.setup();h.policy=4;h.compare(0x40e5c0,h.BOSS);assert h.get(h.E+0x148,2)==[900,1300]
h.setup();h.policy=5;h.compare(0x4701b0,0,[h.A]);assert h.get(h.L+28)[0]==5 and h.get(h.A+0x6c)[0]==h.FXL
# Name-array growth creates both pending CString cells; class growth dispatches.
h.setup();h.compare(0x43cb20,h.E,[h.A]);h.put(h.L+28,[2010]);h.registryGrow=True;originalStates=h.states;grown=(h.State*1)(h.State(2010,0x43d070,h.NAME,b'LS_IDLE'));h.common.states=grown;h.compare(0x43ca60,0,[h.A]);h.common.states=originalStates
report={'pairedCalls':h.calls//2,'nativeAndOriginalInvocations':h.calls,'orderedPairedFullSnapshots':h.snapshots//2,'originalAddresses':len(h.m.executed),'actualWWDProfiles':actual,'sourceDecodedANIRecords':h.decodes,'unsafePrefixes':h.prefixes,'heapBytes':h.SIZE,'globalBytes':h.GN}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='actualWWDProfiles'}))
