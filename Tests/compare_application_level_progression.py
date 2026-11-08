import hashlib,json
import application_level_progression_helpers as h
for level in range(1,15):
 for cmd in(0x8021,0x8036,0x8075):
  for mode in(0,2,3,5,8,10,0xffffffff):
   h.fresh(level);h.modeValues=[mode];h.compare(0x426e30,f'cmd{cmd:x}level{level}',(0,cmd,0))
for outcomes in([0]*14,[0,0,1],[1]):
 for level in range(1,15):
  h.fresh(level);h.modeValues=[3];h.levelOutcomes=outcomes;h.compare(0x429be0,'level-retry');assert h.levelIndex<=13
for ready in(0,1):
 for size in(0,1,2,0xffffffff):
  for current in(0,h.OWNER,h.PRIOR):
   for entered in(0,1):
    for recovered in(0,1):
     h.fresh();h.ready=ready;h.enterResult=entered;h.recoverResult=recovered;h.put(h.APP+44,[current]);h.put(h.APP+228,[size]);h.compare(0x429ac0,'restore-history')
for count in(0,1,2,0xffffffff):
 for token in(0,h.OWNER,h.PRIOR):
  h.fresh();h.put(h.APP+228,[count]);h.compare(0x42c010,'pop-history',(token,))
# core tally is part of the final complete suite
print('core PASS',h.calls,h.eventCount,'text',sum(0x401000<=a<=0x50adb5 for a in h.m.executed),'instrumented',len(h.m.executed))

for missing in(0,0x526a60,0x523734,0x52372c,0x526a58,0x5256a8,0x5254ec,0x525948,0x526a50):
 for base in(0,1):
  for dc in(0,0x123):
   for movie in(0,1):
    h.credits();h.missingResource=missing;h.baseInit=base;h.dcValue=dc;h.fileExists=movie;h.compare(0x435840,'credits-init',(h.APP,1,10),h.OWNER)
for f,args in((0x435f30,()),(0x436630,()),(0x4366c0,()),(0x435b80,()),(0x435e60,()),(0x436590,()),(0x435d10,()),(0x435d50,())):
 for toggle in(0,1,0xffffffff):
  for delta in(0,1,17,300,3000,19200,0x80000000,0xffffffff):
   for dc in(0,0x123):
    h.credits();h.dcValue=dc;h.put(h.OWNER+344,[0xaabbcc,300,3000,toggle]);h.put(0x53720c,[delta]);h.put(0x53735c,[delta&1]);h.put(h.OWNER+424,[1]);h.put(h.OWNER+432,[h.MOVIE]);h.put(h.MOVIE+32,[0x123]);h.compare(f,'credits-matrix',args,h.OWNER,f not in(0x4366c0,))
for f in(0x435a50,0x435af0):
 for mode in(range(15)):
  for movie in(0,1):
   h.credits();h.put(h.OWNER+424,[movie]);h.showCursorValues=[2,1,0,0xffffffff];h.compare(f,'credits-enter-depart',(mode,),h.OWNER)
for a in(0,13,27,32,37,0xffffffff):
 h.credits();h.compare(0x435da0,'credits-input',(a,0xdead),h.OWNER)
for x,y in((0,0),(99,99),(100,99),(99,100),(0xffffffff,0),(0,0xffffffff)):
 h.credits();h.compare(0x435de0,'credits-click',(0xbaff,x,y),h.OWNER)

for t in(3,8):
 for level in range(1,15):
  for fail in(0,1,2):
   for init in(0,1):
    for retained in(0,1):
     h.credits();h.put(h.OWNER,[h.OVT]);h.ctx.composeTransitions=1;h.constructType=t;h.modeValues=[10];h.put(h.APP+228,[retained]);h.allocationFail=fail;h.initResult=init
     if t==8:
      # Original Credits init gate is48f0d0; type5fallback remains explicit.
      h.baseInit=init;h.compare(0x426e30,'type8-failure',(0,0x8021,0))
     else:h.compare(0x429b70,'type3-failure',(level,))

# Directed callback mutation verifies saved tables versus freshly loaded owners.
for f,args,changes in[(0x429ac0,(),{h.DEPART:[(h.APP+44,0)]}),(0x429ac0,(),{h.ENTER:[(h.APP+44,h.OWNER)]}),(0x429be0,(),{0x4f650f:[(h.APP+44,h.PRIOR)]}),(0x429be0,(),{0x46aeb0:[(h.APP+44,h.PRIOR)]}),(0x429b70,(9,),{h.MODE:[(h.APP+44,h.PRIOR)]})]:
 h.fresh();h.modeValues=[3];h.mutations=changes;h.compare(f,'live-callback-aliases',args)
for old in(0,0x7fffffff,0x80000000,0xffffffff):
 h.fresh();h.modeValues=[3];h.put(h.OWNER+20,[old]);h.levelOutcomes=[0];h.compare(0x429be0,'signed-bounds');assert h.levelIndex<=14
# Repeated/late transition requests: source gates stay in force after admission.
for t in(3,8):
 for level in range(1,15):
  h.credits();h.put(h.OWNER,[h.OVT]);h.ctx.composeTransitions=1;h.constructType=t;h.modeValues=[10]
  h.compare(0x428c40,'retained-admission',(t,level,1,0));new=h.get(h.APP+44)[0];assert h.get(new)[0]==(0x50c264 if t==3 else 0x50c174);assert h.get(h.APP+228)[0]==2
  if t==8:
   h.compare(0x426e30,'late8021',(0,0x8021,0));assert h.get(h.APP+44)[0]==new
   for _ in range(3):h.dcValue=0x123;h.compare(0x435b80,'retained-Credits-frame',(),new)
  h.compare(0x426e30,'resume-retained',(0,0x8036,0));assert h.get(h.APP+44)[0]==h.OWNER;assert h.get(h.APP+228)[0]==1
for row in(('empty-current8021',0x426e30,(0,0x8021,0)),('empty-current-next',0x429be0,())):
 h.fresh();h.put(h.APP+44,[0]);h.unsafe(row[1],row[0],row[2])
h.fresh();h.put(h.APP+224,[0]);h.unsafe(0x42bfd0,'null-retained-history')
h.fresh();h.modeValues=[0,0,10];h.mutations={h.MODE:[(h.APP+44,0)]};h.unsafe(0x426e30,'mutated-current-null',(0,0x8021,0))
# Export representative true-oracle records for independent exact-size replay.
for trajectory in([0,0,0,0],[0xffffffff,0,1,0x80000000],[0x80000000,0xffffffff,0,1]):
 h.clockValues=trajectory;h.credits();h.put(h.OWNER,[h.OVT]);h.ctx.composeTransitions=1;h.constructType=8;h.modeValues=[10];h.compare(0x428c40,'clock-alias-lifetime',(8,1,0,0));h.compare(0x435b80,'clock-Credits-frame',(),h.get(h.APP+44)[0])
h.clockValues=[123456,123470,123471,123490]
for f,args,meaning in[(0x429710,(),False),(0x429740,(),False),(0x429720,(1,),True),(0x4295b0,(),True),(0x436560,(h.BASE+0x70000,),True),(0x42b520,(),False)]:
 h.credits();h.compare(f,'exported-small-body',args,h.APP if f==0x436560 else h.MOVIE if f==0x42b520 else h.OWNER,meaning)
for ready in(0,1):
 for playing in(0,1):
  h.credits();h.surfaceReady=ready;h.musicPlaying=playing;h.put(h.OWNER+344,[0,0,3000,1]);h.put(h.MUSICMAN+28,[h.MUSIC2]);h.compare(0x435b80,'restore-and-music-transport',(),h.OWNER)
  h.credits();h.surfaceReady=ready;h.musicPlaying=playing;h.put(h.OWNER+344,[0,0,0,1]);h.put(h.MUSICMAN+28,[h.MUSIC2]);h.compare(0x4366c0,'music-stop-rebind',(),h.OWNER,False)
h.capture=True
for level in range(1,15):
 for t in(3,8):
  h.credits();h.put(h.OWNER,[h.OVT]);h.ctx.composeTransitions=1;h.constructType=t;h.modeValues=[10];h.compare(0x428c40,'replay-admission',(t,level,level%2,0));assert h.get(h.get(h.APP+44)[0])[0]==(0x50c264 if t==3 else 0x50c174)
 for cmd in(0x8036,0x8075):
  h.fresh(level);h.modeValues=[3];h.compare(0x426e30,'replay-commands',(0,cmd,0))
for f in(0x435840,0x435f30,0x4361c0,0x436340,0x435b80,0x4359f0,0x4295c0):
 for profile in range(6):
  h.credits();h.dcValue=0x123 if profile%2 else 0;h.fileExists=profile%2;h.movieOpen=profile%3;h.put(h.OWNER+344,[0xabcdef,1,3000,profile%2]);h.put(0x53720c,[0xffffffff if profile==5 else 17]);h.put(0x53735c,[profile%2]);h.compare(f,'credits-replay',(h.APP,1,10)if f==0x435840 else(1,)if f==0x4295c0 else(),h.OWNER,f not in(0x4359f0,))
h.saveCorpus()
textAddresses=sum(0x401000<=a<=0x50adb5 for a in h.m.executed)
result=dict(originalSHA256=h.m.sha256 if hasattr(h.m,'sha256')else hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),wholeCalls=h.calls,orderedFullSnapshots=h.eventCount,snapshotBytes=h.SIZE+0x30000,originalMappedTextAddresses=textAddresses,totalInstrumentedAddresses=len(h.m.executed),unsafePrefixes=h.unsafeCases,exactSizedReplayCases=len(h.corpus),retailCreditsTextSHA256=hashlib.sha256((h.ROOT/'work/original-disc-assets/STATES/CREDITS/CREDITS.TXT').read_bytes()).hexdigest())
(h.WORK/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',json.dumps(result))
