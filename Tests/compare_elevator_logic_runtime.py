#!/usr/bin/env python3
import elevator_logic_helpers as h
import random,json
rng=random.Random(0x49e2a0)
for fn in(0x49e2a0,0x49cdd0,0x49daf0,0x49db10,0x49db30,0x49db50,0x49db70):
 for direction in range(11):
  for level in(1,10):
   for found in(0,1):
    h.setup(direction);h.resourceFound=bool(found);h.put(h.L+0x10,[fn]);h.put(h.A+0x110,[direction]);h.put(h.CONFIG+0x14,[level]);h.compare(fn,('init profiles',fn,direction,level,found))
for mode in(5,29,1,1000,1001,0xffffffff):
 for flags in(0,1,2,0x100,0x102,0x1000,0x1002,0x1102):
  for support in(0,1):
   for changed in(0,1):
    h.setup(mode);h.put(h.L+0x1c,[mode]);h.put(h.L+0x64,[7]);h.put(h.A+0x164,[flags]);h.put(h.P+8,[0x10 if support else 0]);h.put(h.PP+0x80,[8 if changed else 7]);h.compare(0x49cdd0,('support/reset/oneway/idle',mode,flags,support,changed))
for index in range(500):
 h.setup(index);h.g.animationDelta=rng.choice([0,1,16,99,1000,0x7fffffff,0x80000000,0xffffffff]);h.put(h.L+0x1c,[rng.choice([1000,1001])]);h.put(h.A+0x4c,[rng.getrandbits(32),rng.getrandbits(32)]);h.put(h.L+0x2c,[rng.getrandbits(32)for _ in range(4)]);h.put(h.A+0x148,[rng.getrandbits(32),rng.getrandbits(32)]);h.compare(0x49cdd0,('wrapping capped motion',index))
for index in range(500):
 h.setup(index);h.g.tick=rng.getrandbits(32);h.put(h.L+0x1c,[1]);h.put(h.L+0x3c,[rng.getrandbits(32)for _ in range(6)]);h.put(h.A+0x148,[rng.getrandbits(32),rng.getrandbits(32)]);h.compare(0x49e2a0,('absolute wrapping/signed no-motion',index))
for index in range(400):
 h.setup(index);h.put(h.L+0xc8,[rng.choice([0,1,2,21,200,0x80000000,0xffffffff]),rng.choice([0,1,2,21,200,0x80000000,0xffffffff])]);h.put(h.A+0x110,[rng.randrange(11)]);h.put(h.L+0x2c,[rng.getrandbits(32)for _ in range(4)]);h.put(h.A+0x148,[rng.choice([0,125,0x7fffffff,0x80000000,0xfffffffe]),rng.choice([0,125,0x7fffffff,0x80000000,0xfffffffe])]);h.compare(0x49e060,('phase extents/signed division',index),(h.A,h.L))
for fn in(0x49e2a0,0x49cdd0):
 for policy in(1,2,3):
  h.setup(policy);h.policy=policy;h.put(h.CONFIG+0x14,[10]);h.compare(fn,('lookup live mutation',fn,policy))
print('PASS complete startup/controller/generated unsigned/signed arithmetic/support/reset matrices',flush=True)
# Whole original x86 arithmetic trap and invalid identity prefixes. These are
# diagnostics, not a fabricated successful return or platform movement.
h.setup(1);h.put(h.A+0x4c,[0x10000000]);h.put(h.L+0x2c,[0,0x10000001]);h.put(h.A+0x148,[0xffffffff]);h.compare(0x49e060,'signed IDIV overflow prefix',(h.A,h.L),fault_expected=True)
for fn in(0x49e2a0,0x49daf0,0x49db10):
 for field in('player','manager','defaults','primary','frame'):
  if field=='player'and fn==0x49e2a0:continue
  h.setup(fn)
  if field in('player','manager','defaults'):setattr(h.g,field+'Token',0)
  if field=='primary':h.put(h.A+0x6c,[0])
  if field=='frame':h.put(h.A+0x174,[0xdead0000])
  h.u.mem_unmap(0,4096)
  try:h.compare(fn,('missing identity prefix',fn,field),fault_expected=True)
  finally:h.u.mem_map(0,4096)
print('PASS arithmetic trap and missing heap identity prefixes',flush=True)
for policy in(0,1,2):
 h.profilePolicy=policy
 for level in(0,-1,0x80000000,*range(1,16),0x7fffffff,2,1):h.compare_profile(level,('whole source profile/retained replacement/SetRect policy',policy,level))
sourceProfiles=[]
h.profilePolicy=0
for level in range(1,15):
 h.compare_profile(level,('all14 source rectangle profiles',level));sourceProfiles.append({'level':level,'words':list(h.levelProfile.words),'scaleWords':list(h.levelProfile.scaleWords)})
(h.WORK/'verified-level-profiles.json').write_text(json.dumps(sourceProfiles,indent=2)+'\n')
h.default_source='whole original452b00→452c50 Level1 profile, frozen source48word init'
histories=[]
for kind,index,data in h.records():
 h.setup(index);h.source_defaults(1);h.record_profile(kind,data);fn=h.callbacks[kind];h.compare(fn,('actual31 WWD startup',kind,index));initial=h.words(h.A+0x4c,2);h.put(h.P+8,[0x10]);h.put(h.P+0x80,[h.A])
 path=[]
 for frame in range(96):
  h.g.tick=frame*37;h.g.animationDelta=37;h.compare(fn,('actual31 retained supported movement',kind,index,frame));path.append(h.words(h.A+0x4c,2))
 h.put(h.P+8,[0]);h.compare(fn,('actual31 player dismount',kind,index));h.put(h.PP+0x80,[8]);h.compare(fn,('actual31 checkpoint serial reset',kind,index));h.compare(fn,('actual31 source reinitialize after reset',kind,index));h.put(h.L+0x1c,[29]);h.compare(fn,('actual31 deletion-state callback',kind,index))
 histories.append({'kind':kind,'record':index,'initial':initial,'final':h.words(h.A+0x4c,2),'changedPositions':sum(a!=initial for a in path),'wrapperMode':h.g.wrapperMode,'moveRect':h.words(h.A+0x118,4),'hitRect':h.words(h.A+0x128,4)})
assert len(histories)==31
report={'wholeOriginalCalls':h.calls+h.profile_calls,'orderedFullSnapshots':h.event_count+h.profile_events,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'actualWWDProfiles':len(histories),'frozenWorldObjectLoads':h.loaderCalls,'supportedUpdates':96*31,'defaultsProfile':h.default_source,'allSourceLevelProfiles':14,'profileInitializationCalls':h.profile_calls,'history':histories}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='history'}))
