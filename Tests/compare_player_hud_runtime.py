#!/usr/bin/env python3
import player_hud_runtime_helpers as h
for f in h.FUNCTIONS:
 for state in(0,5,11,29,31,0xffffffff):
  for n in range(8):
   h.fresh(f,state);h.put(h.MANAGER+0x68,[n%4,n%2]);h.g.initialScore=[0,999999,1000000,0xffffffff][n%4];h.sg.animationDelta=[0,1,17,500][n%4];h.g.powerupRemaining=[0,1,999,1000][n%4];h.put(h.PLAYER+0xf8,[n*100001]);h.put(h.PLAYER+0x10c,[n*20]);h.compare(f,('seeded-frame',hex(f),state,n))
 print('PASS',hex(f),flush=True)
print('PASS',h.calls,h.eventCount,len(h.m.executed),h.formatCalls,flush=True)
for score in(0,999999,1000000,2000000,0x7fffffff,0x80000000,0xffffffff):
 for lives in(0,1,9,10,11,0xffffffff,0x7fffffff):
  for threshold in(0,1000000,2000000,0x80000000):
   for audio in(0,1):
    h.fresh(0x4908b0,5);h.put(h.PLAYER+0xf8,[score]);h.put(h.PP+0x7c,[lives]);h.put(h.A+0xfc,[threshold]);h.g.audioEnabled=audio;h.compare(0x4908b0,('score/threshold/lives',score,lives,threshold,audio))
for health in(0,1,99,100,150,0x7fffffff,0x80000000,0xffffffff):
 for timer in(0,1,18,5000):
  for delta in(0,1,17,0xffffffff):
   h.fresh(0x490c50,5);h.put(h.PLAYER+0x10c,[health]);h.put(h.L+0x130,[timer]);h.sg.animationDelta=delta;h.compare(0x490c50,('health-heartbeat',health,timer,delta))
for weapon in(0,1,2,3,4,0xffffffff):
 for amount in(0,1,99,100,0x7fffffff,0x80000000,0xffffffff):
  h.fresh(0x490f80,5);h.put(h.PP+0x30,[weapon]);h.put(h.PP+0x70,[amount,amount,amount]);h.compare(0x490f80,('weapon-ammo',weapon,amount))
for f in h.FUNCTIONS:
 for mode in(0,1,2,3,4,6,99,100,0x80000000,0xffffffff):
  for request in(0,1,0xffffffff):
   h.fresh(f,5);h.put(h.MANAGER+0x68,[mode,request]);h.sg.left=0xffffffff;h.sg.top=0x80000000;h.sg.right=640;h.sg.bottom=0x7fffffff;h.mutation=1;h.compare(f,('bounds/mode/renderer-live-actor',hex(f),mode,request))
for mode in(3,4,6,0xffffffff):
 h.fresh(0x4912a0);h.put(h.VT+16,[h.GETMODE]);h.mode=mode;h.compare(0x4912a0,('lives-owner-mode',mode))
print('PASSdirected score/lives/health/ammo/mode/bounds cases',flush=True)
histories=[];inventory=[]
for f in h.FUNCTIONS:
 for status in(0,1,2,3,99):
  h.fresh(f);inventory=h.realResources();h.ctx.composeImages=h.ctx.composeAnimation=1;h.put(h.MANAGER+0x68,[status,0]);h.compare(f,('real-resource-init',hex(f),status))
  for frame in range(30):
   h.sg.animationDelta=[0,1,17,33,101,500][frame%6];h.g.powerupRemaining=[0,1,999,1000,30000,0xffffffff][frame%6];h.put(h.PLAYER+0xf8,[frame*250001]);h.put(h.PLAYER+0x10c,[100-(frame%7)*15]);h.put(h.PP+0x30,[frame%3+1]);h.put(h.PP+0x70,[frame%100,(frame*2)%100,(frame*3)%100]);h.compare(f,('real-resource-retained',hex(f),status,frame))
  histories.append({'callback':hex(f),'status':status,'primaryState':h.get(h.L+28)[0],'HUD':h.get(h.L+24)[0],'health':h.get(h.PLAYER+0x10c)[0],'lives':h.get(h.PP+0x7c)[0]})
compoundHistories=[]
for status in(0,1,2,3,99):
 h.compoundSetup();h.put(h.MANAGER+0x68,[status,0]);root=h.compound(0x4c8f60,h.CONTAINER,(0,0,0,9999,0x52297c,0x200000),('whole-source-MultiStats-creator',status));assert root==h.sg.multiStats
 for frame in range(12):
  h.sg.animationDelta=[0,1,17,101][frame%4];h.g.powerupRemaining=[0,999,1000,30000][frame%4];h.put(h.PLAYER+0xf8,[frame*1500001]);h.put(h.PLAYER+0x10c,[100-frame*7]);h.put(h.PP+0x30,[frame%3+1]);h.compound(0x491ed0,0,(root,),('whole-HUD-retained-dispatch',status,frame));h.compound(0x4d3f20,root,(h.DISPLAY,),('whole-HUD-child-draw',status,frame),True)
 h.compound(0x4c9fc0,root,(1,),('whole-HUD-collection-destroy',status));compoundHistories.append({'status':status,'root':root,'finalLives':h.get(h.PP+0x7c)[0]})
print('PASS5 full MultiStats creation→all five frames→digits→draw→destruction histories',flush=True)
for f in h.FUNCTIONS:
 for n in range(8):
  h.fresh(f,5);h.put(h.L+24,[0]);h.compare(f,('missing-HUD-inert',hex(f),n))
for f in(0x490f80,0x490c50):
 for n in range(8):
  h.fresh(f);h.sg.player=0 if n%2 else h.PLAYER;h.put(h.PL+0x14,[0]);h.compare(f,('startup-player/private-gate',hex(f),n))
for f in h.FUNCTIONS:
 h.fresh(f);h.realResources();h.ctx.composeImages=h.ctx.composeAnimation=1;h.found=False;h.compare(f,('missing-resource-startup',hex(f)))
 for delta in(0,1,17):h.sg.animationDelta=delta;h.compare(f,('missing-resource-continuation',hex(f),delta))
h.compoundSetup();h.found=False;assert h.compound(0x4c8f60,h.CONTAINER,(0,0,0,9999,0x52297c,0x200000),('missing-MultiStats-metadata',0))==0
for f in h.FUNCTIONS:
 h.fresh(f);h.failAllocation=1;h.unsafeCompare(f,('HUD-allocation-null-prefix',hex(f)))
h.fresh(0x490c50,5);h.sg.player=0;h.put(h.L+0x130,[0]);h.unsafeCompare(0x490c50,('health-heartbeat-lost-player-prefix',))
print('PASS77 normal missing/gate cases and6 separately measured original unsafe prefixes',flush=True)
for lives in(0,1,2,9,10,11,0x7fffffff,0x80000000,0xffffffff):
 h.fresh(0x4912a0,5);h.put(h.PP+0x7c,[lives]);h.compare(0x4912a0,('lives-wrapping-display',lives))
for f in h.FUNCTIONS:
 h.fresh(f,5);newPlayer,newPrimary,newPrivate=h.BASE+0x2c000,h.BASE+0x2d000,h.BASE+0x2e000;h.put(newPlayer+108,[newPrimary]);h.put(newPrimary+0x14,[newPrivate]);h.put(newPlayer+0xf8,[2500000]);h.put(newPlayer+0x10c,[40]);h.put(newPrivate,[0]*78);h.put(newPrivate+0x30,[3]);h.put(newPrivate+0x70,[51,52,53,6]);h.sg.player=newPlayer;h.g.powerupRemaining=30000;h.compare(f,('live-player-alias-vs-cached-private',hex(f)))
print('PASS14 wrapping-life and live-player/cached-private alias cases',flush=True)
corpusCases=h.writeCorpus();print('PASS corpus captured',corpusCases,flush=True)
report={'sanitizerCorpusCases':corpusCases,'calls':h.calls,'events':h.eventCount,'addresses':len(h.m.executed),'originalFormatCalls':h.formatCalls,'heapBytes':h.SIZE,'globalBytes':0x30000,'histories':histories,'resources':inventory,'compoundHistories':compoundHistories,'unsafePrefixes':h.unsafeCases}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k not in('histories','resources','compoundHistories','unsafePrefixes')}),flush=True)
