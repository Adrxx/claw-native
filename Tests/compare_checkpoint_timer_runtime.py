#!/usr/bin/env python3
import checkpoint_timer_helpers as h
import random,json
rng=random.Random(0x491b30)
for state in(0,1,5,6,23,29,31,0xffffffff):
 for health in(0,1,100,0xffffffff):
  for player in(0,h.P):
   for hud in(0,h.HUD):
    h.setup(state);h.g.playerToken=player;h.put(h.P+0x10c,[health]);h.put(h.L+0x1c,[state]);h.put(h.L+0x18,[hud]);h.compare(0x491b30,('timer states/player/health/HUD',state,health,player,hud))
for i in range(300):
 h.setup(i);h.g.remaining=rng.getrandbits(32);h.g.stageDelta=rng.getrandbits(32);h.put(h.L+0x1c,[1]);h.compare(0x491b30,('unsigned cap/decrement/display',i))
for remaining in(0,1,499,500,501,999,1000,1499,1500,34999,35000,999000,999001,0xffffffff):
 for delta in(0,1,16,499,500,999,1000,35000,0xffffffff):
  h.setup(delta);h.g.remaining=remaining;h.g.stageDelta=delta;h.put(h.L+0x1c,[1]);h.compare(0x491b30,('rounding/expiry exact edges',remaining,delta))
for state in(0,5,29,0xffffffff):
 for mode in(0,1,2,99,100,0xffffffff):
  for resize in(0,1):
   h.setup();h.put(h.L+0x1c,[state]);h.put(h.L+0x18,[h.HUD]);h.put(h.MANAGER+0x68,[mode,resize]);h.compare(0x4919f0,('digit status-mode/resizing/lifetime',state,mode,resize))
for horizontal in(0,1,2,3,4):
 for vertical in(0,3,4,5,6):
  for mode in(0,2,100,0xffffff9d):
   h.setup();h.g.left=0xfffffff1;h.g.top=0xfffffff8;h.g.right=640;h.g.bottom=481;args=(h.A,mode,99,horizontal,0xfffffff0,vertical,15);h.compare(0x490760,('HUD full init anchor/signed midpoint',horizontal,vertical,mode),args,receiver=h.HUD)
for policy in(2,3):
 h.setup();h.policy=policy;h.put(h.L+0x1c,[1]);h.put(h.MANAGER+0x68,[0]);h.g.remaining=0 if policy==3 else 1234;h.g.stageDelta=0;h.compare(0x491b30,('live render/post receiver mutations',policy))
for deleted in(0,1,2,3,0xff):
 h.setup();h.compare(0x40db30,('source HUD vtable reset/free',deleted),(deleted,),receiver=h.HUD)
h.setup();h.compare(0x40db50,'whole HUD base destructor',(),receiver=h.HUD)
h.setup();h.compare(0x490c40,'whole group constructor',(),receiver=h.HUD+0x28)
for modeSequence in(([3],[4],[6],[0],[3,0],[0,4],[0,0,6],[0,0,0])):
 for player in(0,h.P):
  for health in(0,100,0xffffffff):
   h.setup();h.virtualModes=list(modeSequence);h.g.playerToken=player;h.put(h.P+0x10c,[health]);h.put(h.VT+16,[0x4000020]);h.compare(0x426e30,('source dequeued expiry command mode/health',modeSequence,player,health),(0,0x8063,0),receiver=h.MANAGER)
for player in(0,h.P):
 for health in(0,1,0xffffffff):
  h.setup();h.put(h.P+0x10c,[health]);h.compare(0x41f490,('whole kill helper null/health',player,health),(player,))
print('PASS whole timer/digit/HUD/cap/clock/expiry command matrices',flush=True)
# Actual hierarchical construction, metadata callbacks, allocation/list event
# prefixes and initial digit binding with original retail PID geometries.
for count in(-1,0,1,3,9,10,11):
 for value in(-12345,-1,0,35,999,0x7fffffff,0xffffffff):
  h.setup(count);h.context.composeImages=h.context.composeHierarchy=1;h.real_resources();args=(h.STATS,h.A,value,count,11,40,0,0x52c700);h.compare(0x490590,('whole number creation clamp/sentinel/value',count,value),args,receiver=h.HUD+0x28)
for failure in range(1,10):
 h.setup(failure);h.context.composeImages=h.context.composeHierarchy=1;h.real_resources();h.failAllocation=failure;cpu=h.null_page_off()
 # Creation actor allocation failure returns normally; null logic/node/HUD
 # allocation enters an actual original invalid-memory path with prior writes.
 expected=failure in(1,3,4,6,7,9)
 # Exact classification is checked by prefix, independently of allocation type.
 try:
  # First:timerHUD, thenchildActor,childLogic,listBlock,childHUD,childActor,...
  expected=failure not in(2,6,9)
  h.compare(0x491b30,('complete allocation failure prefix',failure),fault_expected=expected)
 finally:h.null_page_on(cpu)
for callback in(0,0x4919f0):
 for found in(0,1):
  h.setup();h.resourceFound=bool(found);h.context.composeHierarchy=1;h.put(h.DIGMETA+0x10,[callback]);h.compare(0x4d3e50,('named hierarchy missing metadata/callback',callback,found),(0,0,0,10000,0x522994,0),receiver=h.STATS)
print('PASS actual child allocation/numbers/failure graph',flush=True)

histories=[]
for screenMode in(0,1,2,3,99):
 h.setup(screenMode);h.context.composeHierarchy=h.context.composeImages=h.context.composeAnimation=1;h.real_resources();h.put(h.MANAGER+0x68,[screenMode,0])
 # Actual46aeb0 MultiStats creation profile, including immediate callback and
 # allfive named source children; non-timer HUD callbacks remain logged leaves.
 parent=h.compare(0x4c8f60,('real MultiStats creator profile',screenMode),(0,0,0,9999,0x52297c,0x200000),receiver=h.CONTAINER);assert parent==h.g.multiStatsToken and h.words(parent)[0]==0x513830
 timer=h.create_timer(('actual source named CheckpointTimer startup',screenMode));primary=h.words(timer+0x6c)[0];assert h.g.remaining==35000
 seen={h.words(primary+0x1c)[0]}
 for frame in range(80):
  h.g.stageDelta=499 if frame%2 else 501;h.g.animationDelta=16;h.compare(0x491b30,('retained real source timer/rounding',screenMode,frame),(timer,));seen.add(h.words(primary+0x1c)[0])
  h.compare(0x4d3ef0,('actual MultiStats retained child dispatch',screenMode,frame),(),receiver=parent)
  h.compare(0x4d3f20,('actual MultiStats retained child drawing order',screenMode,frame),(h.DISPLAY,),receiver=parent)
  if h.words(primary+0x1c)[0]==31:break
 assert h.g.remaining==0 and h.g.expired==1 and 31 in seen
 h.compare(0x426e30,('actual timer posted8063 drained',screenMode),(0,0x8063,0),receiver=h.MANAGER);assert h.words(h.P+0x10c)[0]==0
 h.compare(0x491b30,('actual timer observes death',screenMode),(timer,));assert h.words(primary+0x1c)[0]==5
 h.put(h.P+0x10c,[100]);h.compare(0x491b30,('elected source revival resumes timer',screenMode),(timer,));assert h.g.remaining==35000 and h.g.expired==0 and h.words(primary+0x1c)[0]==1
 hud=h.words(primary+0x18)[0];histories.append({'mode':screenMode,'parent':parent,'hud':hud,'digits':h.words(hud+0x34,3),'states':sorted(seen|{5}),'remainingAfterRevival':h.g.remaining})
 h.compare(0x40db30,('actual retained timer HUD teardown',screenMode),(1,),receiver=hud)
 h.put(primary+0x18,[0]);h.compare(0x4c9fc0,('actual collection children/source teardown',screenMode),(1,),receiver=parent)
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.event_count,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'globalWords':13,'originalFormattingCalls':h.originalFormattingCalls,'retainedCreatorProfiles':len(histories),'parentProfile':'46aeb0→4c8f60(MultiStats,0,0,0,9999,200000), timer4c8da0 gatedmanager9c','physicalServices':'renderer/PostMessage transport,417b00 via frozen PlayerDamage, other MultiStats HUD callbacks','histories':histories}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='histories'}))
