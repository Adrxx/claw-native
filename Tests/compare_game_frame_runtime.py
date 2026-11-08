#!/usr/bin/env python3
"""Original ordinary/substep outer frames, real grid residency and manager gates."""
import json
import game_frame_helpers as g
directed=normal_residency=paused=retained=0
for fn in(0x46ac30,0x475dc0):
 for delta in(0,1,16,18,19,35,36,37,54,55,99,100,1000,0xffffffff):
  for policy in(0,1,2,3,4):
   g.prepareOuter(fn);g.outerPolicy=policy;g.stage.stage.deltaMilliseconds=delta;g.stage.stage.nowMilliseconds=1000;g.clockValue=1000;g.compareOuter(fn,('outer delta/callback mutations',hex(fn),delta,policy));directed+=1
   calls=[f for f,s in g.residency_calls];assert 0x4d1fd0 in calls
   effective_delta=37 if policy==4 and fn==0x475dc0 else delta
   parts=effective_delta//18+(effective_delta%18!=0)if 18<effective_delta<100 else 1
   assert calls.count(0x4d2000)==max(0,parts-2)+(policy!=3)
   if delta<=18 and policy==1:
    assert g.words(g.ACTORS[0]+0x94,1)[0]!=0,'real ordinary residency did not reinsert moved actor';normal_residency+=1
for callback in(0x46ac30,0x475dc0,g.OTHER_STATE):
 for gate in(0,1,0xffffffff):
  for counter in(0,1,2,0x7fffffff,0x80000000,0xffffffff):
   g.prepareOuter(callback);g.put(g.MGR+0xb0,[gate]);g.put(g.MGR+0x6c,[counter]);g.compareOuter(0x428b60,('manager publication/pause/postcallback counter',hex(callback),gate,counter));directed+=1
   assert g.stage.stage.nowMilliseconds==1000 and g.stage.stage.deltaMilliseconds==16 and g.stage.accumulatedMilliseconds==2016
   if gate:assert g.words(g.MGR+0x6c,1)==[counter]and not g.residency_calls;paused+=1
   else:
    expected=8 if callback==g.OTHER_STATE else counter-1 if 0<counter<0x80000000 else counter
    assert g.words(g.MGR+0x6c,1)==[expected]
for delta in(0,1,18,19,36,37,99,100):
 g.prepareOuter(0x475dc0);g.clockState.nowMilliseconds=1000-delta;g.compareOuter(0x428b60,('manager actual nested stage choice',delta));directed+=1
 assert g.stage.stage.deltaMilliseconds==delta
# A distinct animation sample occurs after stage publication; pacing reads are
# the actual frozen busy-poll body. Frame-rate reset publishes raw manager words
# before its extra clock service, all visible in full snapshots.
for fn in(0x46ac30,0x475dc0):
 g.prepareOuter(fn);g.put(g.MGR+0x1c,[1]);g.put(g.MGR+0x28,[10]);g.clockState.pacedFrameStart=995;g.clockSamples=list(range(1000,1100));g.compareOuter(0x428b60,('paced ordinary clocks',hex(fn)));directed+=1
 assert g.stage.stage.nowMilliseconds==1000 and g.sceneGlobals.animation.nowMilliseconds>1000
 g.prepareOuter(fn);g.put(g.MGR+0x24,[0]);g.clockSamples=[2100,2110,2120];g.compareOuter(0x428b60,('rate reset/read and stage-animation distinction',hex(fn)));directed+=1
 assert g.words(g.MGR+0x20,2)==[0,2110]and g.stage.stage.nowMilliseconds==2100 and g.sceneGlobals.animation.nowMilliseconds==2120
 g.prepareOuter(fn);g.clockState.nowMilliseconds=0xffffffe0;g.clockValue=16;g.compareOuter(0x428b60,('unsigned clock wrap/substeps',hex(fn)));directed+=1
 assert g.stage.stage.nowMilliseconds==16 and g.stage.stage.deltaMilliseconds==48
for history in range(12):
 g.prepareOuter(0x475dc0 if history%2 else 0x46ac30)
 for step in range(24):
  delta=[16,19,35,18,37,1,99,100][step%8];g.clockValue=(g.clockState.nowMilliseconds+delta)&0xffffffff;g.put(g.PLAYER+0x4c,[50+(step%10)*110,50+(step%7)*95]);g.put(g.PLAYER+0xcc,[8 if step%3==0 else 1]);g.outerPolicy=1 if step%5==0 else 0
  g.compareOuter(0x428b60,('retained moving actor/camera/grid manager frame',history,step));retained+=1
report={'completeOuterFrames':g.calls,'orderedFullHeapEvents':g.event_count,'rawHeapBytes':g.SIZE,'originalAddresses':len(g.m.executed),'directedCases':directed,'pausedPublishedFrames':paused,'ordinaryFramesWithMeasuredReinsertion':normal_residency,'retainedManagerFrames':retained,'scope':'Whole46ac30/475dc0/428b60; real frozen timing/stage/camera/input/spatial/list/interaction bodies, populated grids. Actor gameplay/render/present/UI/audio/extra gameplay helpers and platform clock/keys are explicit.'}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
