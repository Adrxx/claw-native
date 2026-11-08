#!/usr/bin/env python3
import peg_logic_helpers as h
import random,json
rng=random.Random(0x49d860)
for fn in(0x49d860,0x49d620,0x49e4e0,0x49e7b0,0x49e7d0,0x49e7f0):
 for mode in(0,1,5,23,29,1002,1003,1004,1005,1006,1007,1111,0xffffffff):
  for gate in(0,1):
   for support in(0,1):
    for stopped in(0,1):
     h.setup(mode);h.g.gate=gate;h.stopAnimation=stopped;h.put(h.L+0x10,[fn]);h.put(h.L+0x1c,[mode]);h.put(h.L+0x64,[6]);h.put(h.L+0x4c,[3000]);h.put(h.L+0xbc,[0]);h.put(h.P+8,[0x10 if support else 0]);h.compare(fn,('states/gate/support/ANI',fn,mode,gate,support,stopped))
for i in range(500):
 h.setup(i);h.put(h.L+0x4c,[rng.choice([1,2,1500,3000,0x80000000,0xffffffff])]);h.put(h.L+0xbc,[rng.getrandbits(32)]);h.put(h.A+0x148,[rng.getrandbits(32)]);h.g.tick=rng.getrandbits(32);h.compare(0x49e4b0,('wrap modulo+signed gate',i),(h.A,h.L,h.g.tick))
for fn in(0x49d860,0x49d620):
 for found in(0,1):
  for disabled in(0,1):
   for audio in(0,1):
    h.setup(fn);h.resourceFound=bool(found);h.g.audioManagerToken=audio;h.put(h.REG+0x30,[disabled]);h.put(h.L+0x1c,[1002]);h.compare(fn,('audio resource gates',fn,found,disabled,audio))
for fn in(0x49d860,0x49e4e0):
 for policy in(1,2):
  h.setup(policy);h.context.composeAnimation=1;h.load_sequences();h.policy=policy;h.compare(fn,('source lookup mutations',fn,policy))
print('PASS whole Peg bodies/state/gate/support/modulo/resource matrices',flush=True)
# Faults preserve the original preceding writes; no fake modulo success.
h.setup(0);h.put(h.L+0x4c,[0]);h.compare(0x49e4b0,'DIV zero prefix',(h.A,h.L,123),fault_expected=True)
for fn in(0x49d860,0x49d620,0x49e4e0):
 for identity in('defaults','primary','image'):
  h.setup(fn)
  if identity=='defaults':h.g.defaultsToken=0
  elif identity=='primary':h.put(h.A+0x6c,[0])
  else:h.put(h.A+0x170,[0xdead0000])
  h.u.mem_unmap(0,4096)
  try:h.compare(fn,('missing identity prefix',fn,identity),fault_expected=True)
  finally:h.u.mem_map(0,4096)
for frame in(0,1):
 for disabled in(0,1):
  h.setup(frame);h.put(h.COLLISION+0x5c,[h.PLANE if frame else 0]);h.put(h.REG+0x30,[disabled]);h.compare(0x4ca610,('complete spatial-name gate',frame,disabled),(0x528a3c,456,0,0),receiver=h.REG)
print('PASS division/missing-identity prefixes and complete spatial-name wrapper',flush=True)

histories=[]
for kind,index,data in h.records():
 h.setup(index);h.record_profile(kind,data);fn=h.callbacks[kind];h.compare(fn,('actual120 startup+retailANI',kind,index));seen={h.words(h.L+0x1c)[0]};h.put(h.P+8,[0x10]);h.put(h.P+0x80,[h.A])
 if kind=='CrumblingPeg':
  h.compare(fn,('actual64 support arms source delay',index));assert h.words(h.L+0x1c)[0]==1002 and h.words(h.L+0x20)[0]==25
  # Callback election and clearing primary20 are declared source scheduler
  # inputs. Full4c8fc0 is separately verified; this controller does not consume
  # that delay itself. No fabricated platform timer enters the native module.
  h.put(h.L+0x20,[0]);h.compare(fn,('actual64 elected after25ms',index))
  for frame in range(40):
   h.g.animationDelta=50;h.g.tick+=50;h.compare(fn,('actual64 source forward ANI',index,frame));seen.add(h.words(h.L+0x1c)[0])
   if h.words(h.L+0x1c)[0]==23:break
  assert h.words(h.L+0x1c)[0]==23 and h.words(h.A+0x40)[0]&1 and h.words(h.A+0xd0)[0]==1
  h.compare(fn,('actual64 no reset on equal word',index));h.put(h.PP+0x80,[6]);h.compare(fn,('actual64 no reset on lower signed word',index));assert h.words(h.L+0x1c)[0]==23
  h.put(h.PP+0x80,[8]);h.compare(fn,('actual64 greater reset word',index));assert h.words(h.L+0x1c)[0]==0
  h.compare(fn,('actual64 source reinitialization',index));assert h.words(h.L+0x1c)[0]==5 and h.words(h.A+0x40)[0]&1==0
 else:
  frozen=h.words(h.A+0x108)[0]==1
  for frame in range(170):
   h.g.animationDelta=50;h.g.tick=frame*50;h.compare(fn,('actual56 source toggle clock+ANI',kind,index,frame));seen.add(h.words(h.L+0x1c)[0])
  if frozen:assert seen=={5}
  else:assert {1002,1003,1004,1005,1006,1007}<=seen,(kind,index,seen)
 h.put(h.L+0x1c,[29]);h.compare(fn,('actual120 deletion callback',kind,index));histories.append({'kind':kind,'record':index,'visitedStates':sorted(seen),'type':h.words(h.A+0xd0)[0],'hitRect':h.words(h.A+0x128,4),'delay':h.words(h.A+0x148,2),'phaseOffset':h.words(h.L+0xbc)[0]})
assert len(histories)==120
# Source NoRespawn lifetime with a real crumbling image/record profile, but
# explicitly selected alternate registered callback (no Level1 WWD instance).
kind,index,data=next(v for v in h.records()if v[0]=='CrumblingPeg');h.setup(index);h.record_profile(kind,data);h.put(h.L+0x10,[0x49d620]);h.compare(0x49d620,'NoRespawn source startup on real resource profile');h.put(h.L+0x1c,[1111]);h.compare(0x49d620,'NoRespawn scripted arm1111');h.put(h.L+0x20,[0]);h.compare(0x49d620,'NoRespawn post-delay sound')
for frame in range(40):
 h.g.animationDelta=50;h.compare(0x49d620,('NoRespawn actual ANI→Delete',frame))
 if h.words(h.A+8)[0]&0x10000:break
assert h.words(h.A+8)[0]&0x10000
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.event_count,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'actualWWDProfiles':len(histories),'actualCrumblingPegProfiles':sum(x['kind']=='CrumblingPeg'for x in histories),'actualToggleProfiles':sum(x['kind']!='CrumblingPeg'for x in histories),'startupFrozenToggleProfiles':sum(x['kind']!='CrumblingPeg'and x['visitedStates']==[5]for x in histories),'originalANIRecordDecodes':h.decoder_calls,'scheduler':'explicit callback election/primary delay clearing, frozen full scene separately verified','history':histories}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='history'}))
