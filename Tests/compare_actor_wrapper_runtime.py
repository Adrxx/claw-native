#!/usr/bin/env python3
import actor_wrapper_runtime_helpers as h
import random,struct,json,hashlib
rng=random.Random(0x406240)
for i in range(500):
 h.setup(i);h.put(h.F+0x18,[rng.getrandbits(32)for _ in range(4)])
 for f in(0x406240,0x406290):h.compare(f,h.A,[],('full raw geometry arithmetic',i,f))
for f in(0x406240,0x406290):
 for image in(0,h.F,*[h.A+offset for offset in range(0xf0,0x145,4)]):
  h.setup();h.put(h.A+0x174,[image]);h.compare(f,h.A,[],('live alias/null geometry',f,image))
for words in((0,0,0,0),(0xffffffff,0x80000000,0x7fffffff,1),(-31,-32,30,29)):
 h.setup();h.compare(0x40f6c0,h.A,words,('raw rect setter',words))
for root in(0,h.ROOTIMAGE):
 for minimum,maximum in((-9,9),(0,0),(9,-9),(-2147483648,-2147483648),(2147483647,-2147483648)):
  for index in(-10,-9,-1,0,1,8,9,10,0x7fffffff,0x80000000,0xffffffff):
   # INT_MIN/INT_MAX absolute-ID tables wrap into the same mapped4*id word.
   h.setup();h.put(h.A+0x170,[root]);h.put(h.ROOTIMAGE+0x64,[minimum,maximum]);h.compare(0x4209d0,h.A,[index],('signed range/gaps/null root/wrapped table',root,minimum,maximum,index))
for f,receiver in((0x4061b0,h.REG),(0x4062e0,h.WRAPPER)):
 for output in(0,h.F,0xffffffff):
  for originalBool in(0,1,0xffffffff):
   for name in(0,h.NAME,0x52a104):
    for policy in(0,1,2,3):
     h.setup();h.output=output;h.dictionaryBool=originalBool;h.policy=policy;assert h.compare(f,receiver,[name],('dictionary independent output/bool/callee mutations',f,output,originalBool,name,policy))==output
 h.setup();h.legacy=True;h.output=h.F;h.dictionaryBool=0;h.compare(f,receiver,[h.NAME],('existing SceneHost resolvedtoken adapter',f))
print('PASS raw geometry, signed absolute image table, exact dictionary outputs',flush=True)
for f in(0x406240,0x406290):
 for missing in(h.A+0x174,h.F+0x20,h.F+0x18,h.F+0x24,h.F+0x1c):
  h.setup();h.fault_prefix(f,h.A,[],missing,('ordered geometry read failure',f,missing))
 for offset,address in(((0x128,0x406251),(0x12c,0x40625d),(0x130,0x40626e),(0x134,0x40627e))if f==0x406240 else((0x118,0x4062a1),(0x11c,0x4062ad),(0x120,0x4062be),(0x124,0x4062ce))):
  h.setup();h.store_prefix(f,h.A,[],h.A+offset,address,('ordered rectangle store prefix',f,offset))
for missing in(h.A+0x170,h.ROOTIMAGE+0x64,h.ROOTIMAGE+0x68,h.ROOTIMAGE+0x14,h.TABLE+4):
 h.setup();h.fault_prefix(0x4209d0,h.A,[1],missing,('indexed read failure',missing))
for missing in(h.WRAPPER+4,h.A+12,h.SC+0x2c):
 h.setup();h.fault_prefix(0x4062e0,h.WRAPPER,[h.NAME],missing,('ANI receiver-chain failure',missing))
# All25 actual retail powder-keg/crate PID headers, through real signed image
# tables, repeated retained selection→geometry updates and null table gaps.
for kind in('POWDERKEG','CRATES'):
 h.setup();ids=h.retail_images(kind);h.put(h.ROOTIMAGE+0x64,[min(ids),max(ids)])
 for cycle in range(3):
  for index in ids:
   h.compare(0x4209d0,h.A,[index],('retained retail image selection',kind,cycle,index));h.compare(0x406240,h.A,[],('retained retail hit bounds',kind,cycle,index));h.compare(0x406290,h.A,[],('retained retail move bounds',kind,cycle,index))
 h.put(h.TABLE+ids[0]*4,[0]);h.compare(0x4209d0,h.A,[ids[0]],('source actual table gap',kind));before=h.words(h.A+0x118,8);h.compare(0x406240,h.A,[],('gap preserves hitbounds',kind));h.compare(0x406290,h.A,[],('gap preserves movebounds',kind));assert h.words(h.A+0x118,8)==before
for f,receiver,args in((0x406240,0,[]),(0x406290,0,[]),(0x4062e0,0,[h.NAME]),(0x4209d0,h.A,[1])):
 h.setup()
 if f==0x4209d0:h.put(h.ROOTIMAGE+0x14,[0])
 cpu=h.null_page_off()
 try:h.compare(f,receiver,args,('actual original null-pointer exception prefix',f),fault=True)
 finally:h.null_page_on(cpu)
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.eventCount,'stoppedReadStorePrefixes':h.prefixCount,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'retailPIDHeaders':len(h.profiles),'retainedCyclesPerHeader':3,'profiles':h.profiles,'boundaries':'4f6286 dictionary internals/storage and selected PID transport; numeric bounds compose frozen4061e0'}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k!='profiles'})
