#!/usr/bin/env python3
import game_frame_services_helpers as h
F=[0x4774f0,0x477840,0x478290,0x46c2c0,0x4224f0]
for seed in range(80):
 for fn in F:
  h.setup(seed,seed*17&255);h.policy=seed%13
  if fn==0x4774f0:h.put(h.OWNER+0xbf4,[seed%3]);h.put(h.OWNER+0xc04,[0 if seed%3==0 else h.PEER if seed%3==1 else 99])
  if fn==0x477840 and seed%4==0:h.put(h.OWNER+0xbf0,[0])
  if fn==0x478290:h.put(h.OWNER+0xbcc,[seed%4]);h.put(h.OWNER+0x794,[seed%2])
  if fn==0x4224f0:h.put(h.CFG+0xc,[seed%6]);h.put(h.CFG+0x20,[seed*39]);h.put(h.CFG+0x2c,[seed*233]);h.put(h.CFG+0x30,[seed%2])
  h.compare(fn,seed%2 if fn==0x478290 else seed*91)
print('PASS',h.calls//2,'whole original calls;',h.eventCount//2,'ordered full-buffer events;',len(h.m.executed),'original addresses')
# Directed boundary/alias checks with all untouched heap bytes retained.
directed=0
for timer in (0,1,17,18,19,10000,0xffffffff):
 for delta in (0,1,18,10000,0xffffffff):
  for equal in (False,True):
   h.setup(timer+delta);h.policy=0;h.globals.stageDelta=delta;h.put(h.OWNER+0xbf4,[0,timer]);h.globals.lastPose[:]=[689,4730,10,1]if equal else [0x80000000]*4;h.compare(0x4774f0);directed+=1
for count in (0,1,3,4,8,0xffffffff,0x80000000):
 for delta in (0,1,10000,10001,0xffffffff):
  h.setup(count);h.policy=0;h.put(h.CFG+0xc,[count]);h.put(h.CFG+0x20,[1000]);h.put(h.CFG+0x2c,[10000]);h.put(h.CFG+0x30,[1]);h.compare(0x4224f0,delta);directed+=1
for flags in range(256):
 h.setup(flags,flags);h.policy=flags%13;h.globals.overlayRect[0]=(-1 if flags%3==0 else 0 if flags%3==1 else 25)&0xffffffff;h.compare(0x46c2c0);directed+=1
for force in (0,1):
 for mode in (0,1,2,0xffffffff):
  for scores in ([0]*5,[-1]*5,[0x80000000,0x7fffffff,-1,0,1],[3,3,2,2,0]):
   h.setup(mode);h.policy=0;h.put(h.OWNER+0xbcc,[mode]);h.put(h.OWNER+0x794,[1]);
   for t,score in zip(h.ACTORS,scores):h.put(t+0xf8,[score])
   h.compare(0x478290,force);directed+=1
# Required no-peer profile preserves missing network backing when not read.
for enabled in (0,1):
 h.setup(enabled);h.policy=0;h.put(h.OWNER+0x784,[0]);h.put(h.OWNER+0x7ac,[enabled]);h.put(h.OWNER+0xbf0,[0]);h.compare(0x477840);directed+=1
# Retained chains: actual peer refresh/sorting + pose/receive + debug-message timers.
retained=0
for seed in range(32):
 h.setup(seed,0);h.policy=seed%13;h.put(h.CFG+0xc,[6]);h.put(h.CFG+0x20,[0]);h.put(h.OWNER+0xbf0,[0]);
 for tick in range(18):
  h.globals.stageDelta=[0,1,17,18,19,100,500,10000,0xffffffff][tick%9]
  h.put(h.PLAYER+0x4c,[689+tick,4730]);h.put(h.OWNER+0x794,[tick%3==0]);
  for fn,arg in ((0x4774f0,0),(0x477840,0),(0x478290,tick%4==0),(0x46c2c0,0),(0x4224f0,h.globals.stageDelta)):
   h.compare(fn,arg);retained+=1
print('FINAL PASS',h.calls//2,'complete original calls;',h.eventCount//2,'ordered full64KiB+globals snapshots;',len(h.m.executed),'original addresses;',directed,'directed;',retained,'retained calls')
# Whole ordinary original46ac30/428b60 composing original service bodies and
# real populated frozen stage/camera/list/grid, rather than a no-op grid fixture.
import game_frame_services_frame_helpers as j
joined=0
for delta in (0,1,18,19,36,99,100,0xffffffff):
 for fn in (0x46ac30,0x428b60):
  j.prepareJoined();j.stage.stage.deltaMilliseconds=delta;j.outerPolicy=1
  if fn==0x428b60:j.put(j.MGR+0x18,[0,0,0,900,0]);j.clockState.nowMilliseconds=(1000-delta)&0xffffffff
  j.compareOuter(fn,'joined services '+hex(fn)+' delta '+str(delta));joined+=1
for seed in range(8):
 j.prepareJoined();j.outerPolicy=1;j.put(j.MGR+0x18,[0,0,0,900,0])
 for tick in range(8):
  j.clockValue+=13+tick;j.compareOuter(0x428b60,'retained joined '+str(seed)+'/'+str(tick));joined+=1
print('JOINED PASS',joined,'complete ordinary-frame/manager calls;',j.event_count,'ordered384KiB+globals snapshots;',len(j.m.executed),'original addresses')
# Real state-table methods (not synthetic state selection): original helpers
# execute nested timer bodies before the explicit message text/font service.
virtual=0
for flags in (0,1,2,4,16,32,64,128,255):
 for count in (0,1,4):
  h.setup(flags,flags);h.policy=0;h.put(h.VT+0x10,[0x40af90]);h.put(h.VT+0x50,[0x4bb030]);h.put(h.VT+0x64,[0x46ca50]);h.put(h.CFG+0xc,[count]);h.put(h.CFG+0x20,[999]);h.compare(0x46c2c0);virtual+=1
for offset in (0,100,0xffffffff):
 h.setup(offset);h.policy=0;h.globals.overlayRect[:]=[offset,offset,640,480];h.compare(0x46ca50,123);virtual+=1
for fn in (0x40af90,0x4750d0,0x4750e0,0x4bb030):
 h.setup(fn);h.compare(fn);virtual+=1
print('FINAL TOTAL',h.calls//2+j.calls,'original complete calls;',h.eventCount//2+j.event_count,'ordered snapshots;',virtual,'real virtual/message-wrapper calls')
import json
report={'source_sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','helper_complete_calls':h.calls//2,'helper_ordered_full_snapshots':h.eventCount//2,'helper_original_addresses':len(h.m.executed),'joined_complete_calls':j.calls,'joined_ordered_full_snapshots':j.event_count,'joined_original_addresses':len(j.m.executed),'directed_cases':directed,'retained_helper_calls':retained,'virtual_wrapper_calls':virtual,'full_game_equivalence':False}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
