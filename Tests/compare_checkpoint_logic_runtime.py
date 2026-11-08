#!/usr/bin/env python3
import checkpoint_logic_helpers as h
import random,json
rng=random.Random(0x422ef0)
for fn in(0x422ef0,0x423060,0x4232c0,0x4232e0):
 for mode in(0,1,5,6,23,29,31,0xffffffff):
  for image in(0,1):
   for stopped in(0,1):
    for skip in(0,1):
     h.setup(mode);h.g.skipNextSuper=skip;h.stopAnimation=stopped;h.put(h.A+0x174,[h.FRAME if image else 0]);h.put(h.L+0x1c,[mode]);h.compare(fn,('state/frame/ANI/skip',fn,mode,image,stopped,skip))
for existing in(0,1):
 for found in(0,1):
  for allocate in(0,1):
   for callback in(0,0x422ff0):
    for resources in(0,1):
     h.setup(existing);h.resourceFound=bool(found);h.allocationSuccess=bool(allocate);h.put(h.META+0x10,[callback]);h.put(h.A+0x78,[h.EXISTING if existing else 0]);h.put(h.EXISTING+0x14,[h.OUT if resources else 0,h.ASSOC if resources else 0]);h.compare(0x422ef0,('whole contact binding reset/failure',existing,found,allocate,callback,resources))
for fn in(0x422ef0,0x4232c0):
 for policy in(1,2):
  h.setup(policy);h.policy=policy;h.compare(fn,('mutable lookup/allocation boundaries',fn,policy))
h.setup();h.policy=5;h.put(h.A+0x78,[h.EXISTING]);h.put(h.EXISTING+0x14,[h.OUT,h.ASSOC]);h.compare(0x422ef0,'free boundary reloads source metadata/destructor')
for fn in(0x422ef0,0x4232c0):
 for code in(0,1,0xffffffff):
  h.setup();h.stopAnimation=1;h.animationCode=code;h.put(h.L+0x1c,[6]);h.compare(fn,('stopped animation with nonzero current code',fn,code))
for mode in(0,1,2,3,4,0xffffffff):
 h.setup();h.modeResult=mode;h.put(h.VT+0x10,[0x4000020]);h.put(h.L+0x10,[0x4232c0]);h.compare(0x4231a0,('actual virtual mode gate',mode))
for i in range(300):
 h.setup(i);h.put(h.A+0x4c,[rng.getrandbits(32),rng.getrandbits(32)]);h.g.timerRemaining=rng.getrandbits(32);h.g.timerBonus=rng.getrandbits(32);h.compare(0x422ff0,('full wrapping respawn publication/timer',i));assert h.words(h.PP+0x80)[0]==7
# The source contact retains the captured primary but re-reads callback identity
# after ANI service, and re-reads the bonus at the addition boundary.
h.setup();h.policy=3;h.context.composeSave=0;h.put(h.L+0x10,[0x4232c0]);h.compare(0x4231a0,'contact live callback and captured primary mutation')
for cb in(0x422ef0,0x4232c0,0x4232e0):
 for cstringLength in(0,1):
  for cheated in(0,1):
   for saved in(0,1):
    h.setup();h.put(h.L+0x10,[cb]);h.put(h.CSTR,[cstringLength]);h.put(h.CHEATS+0x128,[cheated]);h.saveResult=saved;h.context.composeSave=0;h.compare(0x4231a0,('super callback/CString/cheat/save gate',cb,cstringLength,cheated,saved))
print('PASS original controller/contact/binder/gates',flush=True)
# Whole shared save packer includes exact multiply wrap and sequential overlap.
for i in range(300):
 h.setup(i);h.put(h.COUNTS,[rng.getrandbits(32)for _ in range(10)]);h.compare(0x49a9d0,('source record score/time/calendar',i),(h.OUT,h.COUNTS,rng.getrandbits(32)))
for sourceOffset in(-24,-12,0,4,12,24,28,40):
 h.setup(sourceOffset);h.compare(0x49a9d0,('sequential overlapping count copy',sourceOffset),(h.OUT,h.OUT+sourceOffset,123))
for out,counts in((0,0),(0,h.COUNTS),(h.OUT,0)):
 h.setup();assert h.compare(0x49a9d0,('null pack return',out,counts),(out,counts,55))==0
h.setup();assert h.compare(0x49aa40,'null calendar return',(0,))==0
h.setup();h.compare(0x49aa40,'standalone full calendar record',(h.OUT,))
for position in((100,200),(0,0),(-1,-1),(0,1),(1,0),(0xffffffff,1),(0x80000000,0x80000000)):
 for kind in(0,1,2,3):
  for ownerFlags in(0,1):
   for cheated in(0,1):
    h.setup();h.put(h.CONFIG+0x168,[ownerFlags]);h.put(h.CHEATS+0x128,[cheated]);h.compare(0x46d620,('position/kind/cheat/endlevel save matrix',position,kind,ownerFlags,cheated),position+(kind,),receiver=h.CONFIG)
for field in('disabled','player','private','store'):
 h.setup()
 if field=='disabled':h.put(h.CONFIG+0x258,[1])
 elif field=='player':h.g.playerToken=0
 elif field=='private':h.put(h.PL+0x14,[0])
 else:h.put(h.MANAGER+0x64,[0])
 assert h.compare(0x46d620,('save null/disabled gates',field),(100,200,1),receiver=h.CONFIG)==0
h.setup();h.policy=4;h.compare(0x46d620,'mutable transport return ignored and level reread',(0,0,0),receiver=h.CONFIG)
print('PASS source save branches/record/calendar/overlap',flush=True)

# Exact save-cache bodies, complete receiver bytes and alias-sensitive copies.
for level in(-1,0,1,7,14,15,0x80000000):
 for kind in(0,1,2,3,4):
  h.setup(level);h.compare(0x49ae60,('cache signed level/kind routing',level,kind),(level,kind),receiver=h.SAVE)
  for source in(0,h.OUT):
   h.compare(0x49a860,('cache full44 copy/kind flags',level,kind,source),(level,source,kind),receiver=h.SAVE)
for level in(-1,0,1,7,14,15,0x80000000):
 for score in(0,1,0x80000000,0xffffffff):
  for elapsed in(0,1,0xffffffff):
   for relative in(-1,0,1):
    h.setup(score);target=h.SAVE+0x21c4+68*(level if 0<=level<15 else 0);h.put(h.OUT+4,[score,elapsed]);h.put(target+4,[(score+relative)&0xffffffff,elapsed]);h.compare(0x49a800,('best score unsigned/tie-time',level,score,elapsed,relative),(level,h.OUT),receiver=h.SAVE)
for kind in(1,2,3):
 target=h.SAVE+(0x2d4,0xd24,0x1774)[kind-1]
 for offset in(-12,0,4,12):
  h.setup(offset);h.compare(0x49a860,('cache overlapping REP word order',kind,offset),(0,target+offset,kind),receiver=h.SAVE)
for seed in range(10):
 h.setup(seed);h.compare(0x49a720,('all45 record reset preserves completion bit',seed),(),receiver=h.SAVE)
for position in((0,0),(123,456)):
 for kind in(1,2,3):
  for flags in(0,1):
   h.setup();h.context.composeSaveCache=1;h.put(h.CONFIG+0x168,[flags]);h.compare(0x46d620,('full owner save→real cache',position,kind,flags),position+(kind,),receiver=h.CONFIG)
print('PASS exact cache routing/copy/best-score/reset/composed save',flush=True)

histories=[]
for kind,index,data in h.records():
 h.setup(index);h.record_profile(kind,data);h.context.composeSaveCache=1;h.compare(0x49a720,('actual nine source cache initialization',kind,index),(),receiver=h.SAVE);fn=h.callbacks[kind];h.compare(fn,('actual nine source startup/contactallocation',kind,index));assert h.words(h.L+0x1c)[0]==5 and h.words(h.A+0x78)[0]==h.CONTACT
 contact=h.words(h.CONTACT+0x10)[0];h.put(h.P+0x4c,[h.words(h.A+0x4c)[0]+12,h.words(h.A+0x50)[0]-16]);h.g.tick=0xfffffff0;h.compare(contact,('actual nine elected source contact→respawn/save',kind,index));assert h.words(h.CONFIG+0x44,2)==[h.words(h.A+0x4c)[0],(h.words(h.A+0x50)[0]-32)&0xffffffff];assert h.words(h.PP+0x80)[0]==7
 seen={h.words(h.L+0x1c)[0]}
 for frame in range(50):
  h.g.animationDelta=50;h.g.tick=(h.g.tick+50)&0xffffffff;h.compare(fn,('actual nine originalRISE/WAVE ANI lifetime',kind,index,frame));seen.add(h.words(h.L+0x1c)[0])
 assert seen=={1,6},(kind,index,seen)
 # Original contact has no local dedup. A second elected contact repeats its
 # publication/bonus/save. Whether4c9390 elects it is a separate source layer.
 before=h.g.timerRemaining;h.compare(contact,('actual nine re-elected contact',kind,index));assert h.g.timerRemaining==(before+25000)&0xffffffff
 h.put(h.L+0x1c,[29]);h.compare(fn,('actual nine deferred destructor state is inert',kind,index));histories.append({'kind':kind,'record':index,'states':sorted(seen),'sensorPosition':h.words(h.A+0x4c,2),'respawnPosition':h.words(h.CONFIG+0x44,2),'attackRect':h.words(h.A+0x138,4),'contact':contact})
assert len(histories)==9 and sum(x['kind']=='Checkpoint'for x in histories)==7
for kind,index,data in h.records():
 if kind=='Checkpoint':continue
 h.setup(index);h.record_profile(kind,data);h.g.skipNextSuper=1;h.compare(h.callbacks[kind],('saved super one-shot deletion startup',kind,index));assert h.g.skipNextSuper==0 and h.words(h.A+8)[0]&0x10000 and h.words(h.A+0x78)[0]==0
# Missing raw identities stop at matching original fault prefixes, no fake return.
for fn,field in((0x422ef0,'primary'),(0x422ff0,'owner'),(0x4231a0,'player'),(0x49aa40,'out')):
 h.setup()
 if field=='primary':h.put(h.A+0x6c,[0])
 elif field=='owner':h.put(h.MANAGER+0x2c,[0])
 elif field=='player':h.g.playerToken=0;h.put(h.L+0x10,[0x4232c0])
 args=(0xdead0000,)if field=='out'else(h.A,)
 h.u.mem_unmap(0,4096)
 try:h.compare(fn,('missing identity prefix',fn,field),args,fault_expected=True)
 finally:h.u.mem_map(0,4096)
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.event_count,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'globalWords':34,'actualWWDProfiles':len(histories),'originalANIRecordDecodes':h.decoder_calls,'scope':'9-world-actor checkpoint closure and real cache; TimerHUD491b30/file49bbc0/UI remain explicit','history':histories}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='history'}))
