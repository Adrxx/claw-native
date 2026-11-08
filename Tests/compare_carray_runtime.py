#!/usr/bin/env python3
"""Whole original pointer CArray, CRT front-ends and retained loader composition."""
import random,json
import carray_helpers as t
rng=random.Random(12317);directed=0
for seed in range(64):
 t.prepare(seed);t.compare(0x4f58ab,t.ARRAY,('constructor preserves raw surroundings',seed))
for mode in range(3):
 for old,count,capacity,grow in[(0,0,0,0),(0,1,0,0),(1,1,1,0),(4,3,8,0),(4,5,8,0),(4,9,8,0),(16,33,16,0),(63,67,63,0),(8191,8192,8191,0),(8192,8193,8192,0),(20000,20001,20000,0),(3,100,8,1),(4,9,8,32),(3,10,8,0xffffffff),(3,9,8,0x80000000),(3,10,8,0x7fffffff),(3,0xffffffff,8,0),(3,0x80000000,8,0)]:
  for explicit in(0xffffffff,0,1,4,0xfffffff9):
   t.prepare(count^grow^explicit);t.context.composeAllocator=mode;t.put(t.ARRAY,[0xdeadbeef,t.DATA if capacity else 0,old,capacity,grow]);t.compare(0x4f5915,t.ARRAY,('signed/growth/tail/header',mode,old,count,capacity,grow,explicit),(count,explicit));directed+=1
 for index in(-2,-1,0,3,4,7,8,31):
  t.prepare(index);t.context.composeAllocator=mode;t.compare(0x4f582f,t.ARRAY,('signed SetAtGrow/no shift',mode,index),(index,rng.getrandbits(32)));directed+=1
 for seed in range(12):
  t.prepare(seed);t.context.composeAllocator=mode;t.policy=2;t.compare(0x4f582f,t.ARRAY,('allocation/free mutations',mode,seed),(12,0xabcdef01));directed+=1
for history in range(32):
 t.prepare(history);t.context.composeAllocator=history%3;t.compare(0x4f58ab,t.ARRAY,('retained constructor',history))
 for step in range(48):
  if step%13==0:t.compare(0x4f5915,t.ARRAY,('retained release',history,step),(0,0xffffffff))
  elif step%11==0:t.compare(0x4f5915,t.ARRAY,('retained shrink',history,step),(1,0xffffffff))
  elif step%7==0:t.compare(0x4f5915,t.ARRAY,('retained explicit grow',history,step),(step//2,5))
  else:t.compare(0x4f582f,t.ARRAY,('retained append/overwrite',history,step),(step,rng.getrandbits(32)))
# The original helpers execute byte-at-a-time/word copy paths; native uses
# recovered memset/memmove memory semantics over aligned host spans.
for n in(0,1,2,3,4,5,7,8,15,16,31,32,33,64,129):
 for dst,src in[(t.DATA,t.DATA),(t.DATA+1,t.DATA),(t.DATA,t.DATA+1),(t.DATA+3,t.DATA+7),(t.DATA+5,t.DATA+200)]:
  t.prepare(n);t.compare(0x4a4a80,0,('overlap and byte alignment',n,dst,src),(dst,src,n));t.compare(0x4a4a20,0,('fill low byte/alignment',n,dst),(dst,0xabcdef12,n));directed+=2
for mode in(1,2):
 for failed in(0,1,2,4):
  for answer in(0,1):
   t.prepare(failed);t.context.composeAllocator=mode;t.mallocFailures=failed;t.handlerResult=answer
   # Mode2 failure counter applies to both small-block and HeapAlloc services;
   # any ensuing handler body/retry is logged exactly.
   t.compare(0x4f63ec,0,('ordinary wrapper retries/refusal',mode,failed,answer),(64,));directed+=1
 for failed in(1,2,4):
  t.prepare();t.context.composeAllocator=mode;t.policy=4;t.mallocFailures=failed;t.compare(0x4f63ec,0,('global handler changes across retry',mode,failed),(1024,));directed+=1
for f in(0x4a48e0,0x4a4900,0x4a4950):
 for n in(0,1,15,16,17,479,480,481,1024,0xffffffe0,0xffffffe1,0xffffffff):
  for small_fail in(0,1):
   t.prepare(n);t.context.composeAllocator=2;t.smallFailures=small_fail;t.compare(f,0,('CRT sizes/small-block/fallback',hex(f),n,small_fail),(n,0)if f==0x4a4900 else(n,));directed+=1
for failed in(1,2,4):
 t.prepare();t.context.composeAllocator=2;t.context.crtNewMode=1;t.mallocFailures=failed;t.compare(0x4a48e0,0,('CRT new-mode retries',failed),(1024,));directed+=1
# Native null diagnostics are measured against the first actual original
# write through null, not labeled as safe normal-return original behavior.
for mode in range(3):
 for data in(0,t.DATA):
  t.prepare();t.context.composeAllocator=mode;t.put(t.ARRAY,[0x5108fc,data,4 if data else 0,4 if data else 0,0]);t.mallocFailures=10;t.handlerResult=0;t.compare(0x4f5915,t.ARRAY,('unsafe null original witness/native fault',mode,data),(9,0xffffffff),2);directed+=1
joined=t.plane_composition()
fallback=t.host_fallback()
report={'completeOperations':t.calls,'normalReturnOperations':t.calls-6,'unsafeNullAccessWitnesses':6,'orderedCompleteSnapshots':t.events,'originalAddresses':len(t.m.executed),'rawHeapBytes':t.SIZE,'directedCases':directed,'retainedArrayHistories':32,'retainedArrayCalls':32*49,'joinedPlanes':joined,'hostFallback':fallback,'scope':'Whole4f58ab/4f582f/4f5915; whole4f63ec wrapper and4a48e0/4a4900/4a4950 branches; actual memset/memmove. Physical allocator, lock/module-thread/handler/free services explicit; null-fault witnesses separate.'}
(t.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
