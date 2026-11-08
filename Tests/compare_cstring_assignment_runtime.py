#!/usr/bin/env python3
import cstring_assignment_helpers as g
for refs in(-3,-1,0,1,2,3,0x7fffffff):
 for capacity in(0,3,7,8,9,32):
  for payload in(b'',b'A',b'ABCDE',b'NewValue',b'A\x80\xffZ'):
   g.reset(refs=refs,capacity=max(capacity,3));g.put(g.STORAGE+8,capacity);g.write(g.INPUT,payload+b'\0');g.capture=refs in(1,2) and capacity in(3,9) and payload in(b'A',b'ABCDE')
   g.compare(0x4f66cc,g.CELL,[g.INPUT],(refs,capacity,payload));g.capture=False
print('PASS ordinary',g.calls,g.snapshots,flush=True)
for refs in(-1,0,1,2,3):
 g.reset(refs=refs);g.compare(0x4f66cc,g.CELL,[0],('null',refs))
 g.reset(refs=refs);g.compare(0x4f655b,g.CELL,[8],('prepare',refs),False)
for count in(0,1,2,3,4,5,8):
 g.reset(capacity=32);g.compare(0x4f6650,g.CELL,[count,g.INPUT],('explicit-length',count),False)
for refs in(1,2,3):
 for offset in(0,1,2):
  g.reset(refs=refs,content=b'AliasText');g.compare(0x4f66cc,g.CELL,[g.STORAGE+12+offset],('alias',refs,offset))
print('PASS direct/alias',g.calls,g.snapshots,flush=True)
for mutation in range(1,6):
 g.reset(capacity=3);g.mutation=mutation;g.compare(0x4f66cc,g.CELL,[g.INPUT],('callback-mutation',mutation))
print('PASS mutation',g.calls,g.snapshots,flush=True)
# Retained source cell operations, including valid shared-input copy-on-write.
for seed in range(24):
 g.reset(seed,refs=2,capacity=32,content=b'shared-start');g.capture=seed<2
 for payload in(b'A',b'ABCDE',b'LONGER RETAINED NAME',b'',b'A\x80\xffZ',b'REBIND'):
  g.write(g.INPUT,payload+b'\0');g.compare(0x4f66cc,g.CELL,[g.INPUT],('retained',seed,payload))
 g.capture=False
# Exact odd string capacities and source-pointer offsets inside declared input.
for length in(1,2,3,4,5,6,7,8,15,16,17,31,32,33,63,64,65,127,128,129,254,255):
 g.reset(capacity=3);g.write(g.INPUT,b'Q'*length+b'\0');g.capture=length<=17
 g.compare(0x4f66cc,g.CELL,[g.INPUT],('exact-new-allocation',length));g.capture=False
for offset in(0,1,2,3):
 g.reset();g.write(g.INPUT,b'Prefix_' + b'DATA\0');g.compare(0x4f6650,g.CELL,[4,g.INPUT+7+offset],('unaligned-source',offset),False)
# The source can fault or use freed data: native safety stops preserve prefixes.
g.reset(capacity=3);g.failedOrdinal=0;g.prefix(0x4f66cc,g.CELL,[g.INPUT],0x4f649e,'null-allocation-header-store')
g.reset(content=b'OLD_ALIAS');g.put(g.STORAGE+8,0);g.prefix(0x4f66cc,g.CELL,[g.STORAGE+12],0x4a4a80,'released-input-before-copy')
g.reset();g.objects[g.CELL-12]=16;g.put(g.CELL-12,1,4,4);g.put(g.CELL,g.CELL);g.write(g.INPUT,b'ABCD\0');g.prefix(0x4f6650,g.CELL,[4,g.INPUT],0x4f666f,'copy-overwrites-receiver-pointer')
g.reset();g.prefix(0x4f6650,g.CELL,[0xffffffff,g.INPUT],0x4a4a80,'unbounded-count-before-copy')
print('PASS final',g.calls,g.snapshots,g.prefixes,flush=True)
# Native ABI validation, with no claim that invalid stack arity is an original exit.
g.reset();out=g.U(0x12345678)
assert not g.lib.claw_cstring_assignment_entry(0x12345678,g.CELL,None,0,g.C.byref(g.ctx),g.dep,None,g.C.byref(out)) and out.value==0x12345678 and not g.ctx.fault
assert not g.lib.claw_cstring_assignment_entry(0x4f66cc,g.CELL,None,0,g.C.byref(g.ctx),g.dep,None,g.C.byref(out)) and g.ctx.fault==2
import json,gzip,struct
report=dict(wholeOriginalCalls=g.calls,orderedFullSnapshots=g.snapshots,unsafePrefixes=g.prefixes,textAddresses=len([a for a in g.m.executed if 0x401000<=a<0x50adb5]),totalAddresses=len(g.m.executed),sanitizerCases=len(g.captures),heapBytes=g.SIZE,globalBytes=0x43000,limit='exact CString assignment+prepare+frozen release/allocation/copy; lstrlen/CRT heap and atomic physical transport explicit')
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
with gzip.open(g.WORK/'sanitizer-corpus.bin.gz','wb')as target:
 target.write(g.pack(len(g.captures)))
 for f,t,a,before,after,img,result,meaningful,objects,initialLive,events in g.captures:
  target.write(g.pack(f,t,len(a),*(a+[0]*4)[:4],result,int(meaningful),len(objects),len(events)));target.write(before);target.write(after);target.write(img)
  for token,size in objects.items():target.write(g.pack(token,size,int((token<g.ALLOC and token not in(g.STORAGE,g.ALT)) or token in initialLive)))
  shadow=before+img[0x510000-g.iBase:0x553000-g.iBase]
  for f,t,a,result,bef,aft,activeBefore,activeAfter in events:
   patchesBefore=[(i,v)for i,(x,v)in enumerate(zip(shadow,bef))if x!=v];patchesAfter=[(i,v)for i,(x,v)in enumerate(zip(bef,aft))if x!=v]
   changes=[(p,int(p in activeAfter))for p in set(activeBefore)|set(activeAfter)if(p in activeBefore)!=(p in activeAfter)]
   target.write(g.pack(f,t,len(a),*(list(a)+[0]*4)[:4],result,len(patchesBefore),len(patchesAfter),len(changes)))
   for patches in(patchesBefore,patchesAfter):
    for at,v in patches:target.write(struct.pack('<IB',at,v))
   for p,state in changes:target.write(g.pack(p,state))
   shadow=aft
print('PASS corpus',len(g.captures),flush=True)
