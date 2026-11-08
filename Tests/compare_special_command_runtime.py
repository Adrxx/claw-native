#!/usr/bin/env python3
import special_command_helpers as h
import json
h.setup();h.compare(0x46c630,'initial warp')
h.setup();h.compare(0x46c900,'initial end-level')
h.setup();h.compare(0x426e30,'805c',(0,0x805c,0),h.MANAGER)
h.setup();h.compare(0x426e30,'800e',(0,0x800e,0),h.MANAGER)
print('PASS initial command paths')
for x in(0,1,0x7fffffff,0x80000000,0xffffffff):
 for y in(0,1,0x7fffffff,0x80000000,0xffffffff):
  for player in(0,h.P):
   h.setup(x^y);h.g.warpX=x;h.g.warpY=y;h.g.playerToken=player;h.compare(0x46c630,('signed warp gates',x,y,player))
for bypass in(0,1,0xffffffff):
 for manager in(0,h.FADERM):
  for enabled in(0,1):
   for back in(0,h.BACK+0x400):
    for front in(0,h.FRONT+0x400):
     for available in(0,1):
      for f in(0x48feb0,0x48fda0):
       h.setup();h.g.fadeBypass=bypass;h.resource=bool(available);h.put(h.O+0x10,[manager]);h.put(h.SC+0x1c,[enabled]);h.put(h.BACK+0x2c,[back]);h.put(h.FRONT+0x2c,[front]);h.compare(f,('all fade admission/factory-null gates',f,bypass,manager,enabled,back,front,available),(80,1450,0))
for steps in(0,1,80,0xffffffff):
 for duration in(0,1,1450,0xffffffff):
  h.setup();h.g.fadeBypass=1;h.compare(0x48fda0,('source preserved packet/argument words',steps,duration),(steps,duration,0xffffffff))
for i in range(100):
 h.setup(i);h.g.clock[:]=[(i*0x10000003+j)&0xffffffff for j in range(5)];h.put(h.MANAGER+0x30,[i%2]);h.g.playerToken=0 if i%3==0 else h.P;h.put(h.PL+0x14,[0 if i%5==0 else h.PP]);h.compare(0x42abf0,('clock count/order reset omissions',i),(),h.MANAGER)
for policy in range(1,7):
 h.setup(policy);h.policy=policy;h.compare(0x46c630,('live callback mutation warp',policy))
 h.setup(policy);h.policy=policy;h.compare(0x46c900,('live callback mutation map',policy))
for modeSequence in([3],[4],[6],[0],[0,4],[0,0,6],[0,0,0],[3,3,3]):
 for command in(0x805c,0x800e):
  for owner in(0,h.O):
   h.setup();h.put(h.MANAGER+0x2c,[owner]);h.put(h.VT+0x10,[0x4000000]);h.modes=list(modeSequence);h.compare(0x426e30,('repeated mode probes',modeSequence,command,owner),(0,command,0),h.MANAGER)
for f in(0x42d420,0x42d440):
 for music in(0,h.SERVICE):
  for enabled in(0,1):
   h.setup();h.put(h.MANAGER+0x50,[music]);h.put(h.MANAGER+0x14,[enabled]);h.compare(f,('music gates',f,music,enabled),(),h.MANAGER)
for level in(0,1,14,15,0xffffffff):
 for completed in(0,1):
  for option in(0,1):
   for serial in(0,12345,0xffffffff):
    h.setup();h.put(h.O+0x14,[level]);h.put(h.OPTIONS+0x128,[option]);h.g.accumulatedTick=serial;h.put(h.O+0x170+4,[completed]);h.compare(0x46c7b0,('signed level gate/unsigned accounting',level,completed,option,serial),(h.P,))
for player in(0,h.P):
 for primary in(0,h.PL):
  for priv in(0,h.PP):
   h.setup();h.put(h.P+0x6c,[primary]);h.put(h.PL+0x14,[priv]);h.compare(0x415d90,('whole player copy gates',player,primary,priv),(player,),0)
for specialMode in(0,1):
 for lastLevel in(1,14):
  for completed in(0,1):
   for skipSave in(0,1):
    for scene in(0,h.SC):
     h.setup();h.put(h.MANAGER+0x9c,[specialMode]);h.put(h.O+0x14,[lastLevel]);h.put(h.O+0x258,[skipSave,completed]);h.put(h.O+12,[scene]);h.compare(0x46c900,('default/state10 vs timed/progression/end gates',specialMode,lastLevel,completed,skipSave,scene))
for switch in(0,1):
 for previous in(0,3,4,6,0xffffffff):
  for failure in(0,0x42bfd0,0x48f0d0,0x4b7f20,0x4b68c0,0x40b6a0,0x40d470,0x42af50):
   h.setup();h.put(h.O+0x14,[1]);h.put(h.MANAGER+0x130,[switch]);h.leafFailure=failure;h.showCounts=[1,0,-1];h.compare(0x40ac20,('Booty source option/resource/init failure',switch,previous,failure),(h.MANAGER,1,previous))
for retain in(0,1):
 for forcedBase in(0,1):
  for historyCount in(0,1,4):
   for capacity in(historyCount,max(1,historyCount+1)):
    h.setup();h.put(h.MANAGER+0xa0,[forcedBase]);h.put(h.MANAGER+0xdc,[0x5107bc,h.FDATA if historyCount else 0,historyCount,capacity,0]);h.put(h.VT,[0x4000080]);h.put(h.FDATA,[h.O]*max(1,historyCount));h.compare(0x428c40,('retained history resize/clear/base-only',retain,forcedBase,historyCount,capacity),(10,1,retain,0),h.MANAGER)
for failure in(1,2,3):
 h.setup();h.failAllocation=failure;cpu=h.null_page_off()
 try:h.compare(0x46c900,('allocation failure retained prefix',failure),fault_expected=failure in(1,3))
 finally:h.null_page_on(cpu)
for f in(0x4ecc00,0x4ec600):
 for count in(0,1,4):
  for match in(-1,0,3):
   h.setup();h.put(h.FADERM+0x18,[count]);h.put(h.FDATA,[h.FADER if i==match else h.FADER+0x100 for i in range(4)]);h.compare(f,('packet/fader retained list positions',f,count,match),(h.FADER,)if f==0x4ec600 else(),h.FADERM)
for command in(0x8023,):
 for failure in(0,0x428c40):
  h.setup();h.leafFailure=failure;h.compare(0x426e30,('source synchronous fallback exactstate5 service',failure),(0,command,0),h.MANAGER)
for scenario in('allocation','wrongmode','missingbooty'):
 h.setup();h.failAllocation=2 if scenario=='allocation' else 0
 if scenario=='wrongmode':h.put(h.VT+0x10,[0x4000000]);h.modes=[4]
 if scenario=='missingbooty':h.leafFailure=0x4b7f20
 h.compare(0x426e30,('map failed retained transition synchronousfallback',scenario),(0,0x800e,0),h.MANAGER);assert h.g.playerToken==0 and h.words(h.MANAGER+0x2c)[0]==0 and h.words(h.MANAGER+0xe4)[0]==1
 assert h.events[-1][0][:3]==(0x546d44,0,(0xabc,0x111,0x8023,0))
 h.compare(0x426e30,('retained state failure source8023 service',scenario),(0,0x8023,0),h.MANAGER)
print('PASS source gates, failures, mutations, clocks, captures, state10',flush=True)

profiles=json.loads((h.ROOT/'work/powerup-object-agent/level1-records.json').read_text());warps=[r for r in profiles if r['strings'][2]=='GAME_WARP'];assert len(warps)==8
h.callbacks['SpecialPowerup']=0x470430
raw={h.struct.unpack_from('<I',data)[0]:data for kind,index,data in h.records()if kind=='SpecialPowerup'}
histories=[]
for record in warps:
 h.setup(record['words'][0]);h.record_profile('SpecialPowerup',raw[record['words'][0]]);h.put(h.A+0xfc,[0x26ae]);h.put(h.PL+0x1c,[1]);h.put(h.P+12,[h.SC]);target=(record['words'][55],record['words'][56]);assert tuple(h.words(h.A+0x148,2))==target
 for cycle in range(4):
  h.g.warpX=h.g.warpY=0xffffffff;h.publish_warp(('actual WWD source publication',record['words'][0],cycle));assert(h.g.warpX,h.g.warpY)==target
  h.compare(0x426e30,('source posted805c dequeue real warp',record['words'][0],cycle),(0,0x805c,0),h.MANAGER);assert tuple(h.words(h.P+0x4c,2))==target and h.g.warpX==h.g.warpY==0xffffffff and h.words(h.PP+0x120)[0]==20000
  h.compare(0x426e30,('retained consumed command cannot rewarp',record['words'][0],cycle),(0,0x805c,0),h.MANAGER)
 histories.append({'WWDid':record['words'][0],'rawSHA256':record['rawSHA256'],'target':target,'cycles':4})
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.event_count,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'globalWords':97,'retailWarpRecords':len(warps),'sourcePublicationCalls':h.publication_calls,'retainedHistories':histories,'boundaries':'frame/spatial callbacks; physical fades/render/audio;save/file;Booty child UI/base resource binding;state5 fallback'}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k!='retainedHistories'})
