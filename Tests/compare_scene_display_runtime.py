#!/usr/bin/env python3
import scene_display_helpers as H
from scene_display_helpers import *
prepare();compare(0x4ca6f0,HOLDER,[640,480,8,0],'wholeSourceDisplayStartup');compare(0x4cf730,HOLDER,[],'ready');compare(0x4ca8b0,HOLDER,[],'cleanup');compare(0x4cf780,HOLDER,[],'destructor')
print('PASS display initial',H.calls,H.eventCount,len(m.executed),flush=True)
#Whole init/cleanup chains, source flags, signed sizes and raw depth profiles.
for width,height,bits in [(320,240,8),(640,480,8),(640,480,0),(800,600,16),(640,480,24),(640,480,32),(0,480,8),(0xffffffff,480,8),(640,0,8),(640,0x80000000,8)]:
 for flags in(0,1,2,16,18):
  prepare(width^height^bits^flags);put(PARENT+52,[flags]);compare(0x4ca6f0,HOLDER,[width,height,bits,flags],('wholeInitializer',width,height,bits,flags));compare(0x4cf730,HOLDER,[],'readinessAfterInit');compare(0x4ca8b0,HOLDER,[],'retainedCleanup');compare(0x4cf780,HOLDER,[],'retainedDestructor')
print('PASS source display profiles',H.calls,H.eventCount,len(m.executed),flush=True)
#Physical failure outputs are declared profiles: COM may write output on error.
for where in('create','cooperative','caps','enumerate','setMode','display','surfaceCreate','attached','surfaceDescribe'):
 for hr in(1,0x80004005,0xffffffff):
  for prior in(0,0x12345678):
   prepare(hr^prior);H.g.device=0;put(PARENT+56,[prior]);H.failure={where:hr}
   if where=='surfaceCreate':H.createSurfaceFailure=hr
   if where=='attached':H.attachFailure=hr
   if where=='surfaceDescribe':H.descFailure=hr
   compare(0x4ca6f0,HOLDER,[640,480,8,0],('wholeFailureInit',where,hr,prior));compare(0x4ca8b0,HOLDER,[],'failureCleanup')
for mask in range(8):
 prepare(mask);put(HOLDER+16,[CHILD1 if mask&1 else 0,CHILD2 if mask&2 else 0,CHILD3 if mask&4 else 0]);compare(0x4cf730,HOLDER,[],'pointerOnlyReadiness');compare(0x4cf750,HOLDER,[],'exactType15')
#52-byte owned vs borrowed wrapper cleanup retains borrowed surface tokens.
for owned in(0,1,0x80000000,0xffffffff):
 for flags in(0,1,2,3,0xffffffff):
  prepare(owned^flags);compare(0x4ca6f0,HOLDER,[640,480,8,0],'ownedBorrowedStartup');token=get(HOLDER+20)[0];put(token+48,[owned]);compare(0x45fe40,token,[flags],('ownedBorrowedDeleting',owned,flags))
print('PASS source failures/ownership',H.calls,H.eventCount,len(m.executed),flush=True)
#Source pure dimension/readiness/destructor leaves with preserved seeded bytes.
for f in(0x4cabc0,0x4cacb0,0x4cac00,0x4cac40,0x4caca0,0x45fec0,0x4cabe0):
 for i in range(24):
  prepare(i);t=CHILD1;put(t+4,[i%3-1]);put(t+12,[PARENT if i&1 else 0]);put(t+16,[[0,1,0xffffffff,0x80000000][i%4]]);put(t+44,[DD_SURFACE if i&2 else 0]);args=[i-8,i-3]if f==0x4cac00 else[i-8,i-3,[8,16,24,32,7,0][i%6]]if f==0x4cac40 else[i%4]if f==0x4cabe0 else[];compare(f,t,[a&0xffffffff for a in args],('wholePureLeaf',hex(f),i))
#Real effect queue count transitions, signed underflow, readiness and capturednext.
for remaining in(0,1,2,5,0x7fffffff,0x80000000,0xffffffff):
 for ready in(0,1,0xffffffff):
  for mutation in('','next','lifetime'):
   prepare(remaining);H.ready=ready;H.mutate=mutation
   put(NODES,[NODES+16,0,CHILD1]);put(NODES+16,[0,NODES,CHILD2]);put(NODES+32,[0,NODES,CHILD3]);put(RENDERER+20,[NODES,NODES+16,2,0,0,10]);put(CHILD1+100,[remaining]);put(CHILD2+100,[remaining]);compare(0x4d63c0,RENDERER,[HOLDER,ARG2],('wholeQueueDrain',remaining,ready,mutation));
   if mutation!='next':compare(0x4d63c0,RENDERER,[HOLDER,ARG2],'retainedQueueDrain')
#Empty drain never reads either supplied pointer (actual source early exit).
prepare();compare(0x4d63c0,RENDERER,[0,0],'emptyNullArgs')
print('PASS source leaves/queues',H.calls,H.eventCount,len(m.executed),flush=True)
#Primary/base surface destructors and wrappers, actual bounded source bodies.
for f in(0x4bc810,0x4bc830,0x4bb060,0x4bb080):
 for borrowed in(0,1):
  for flags in(0,1,2,3):
   prepare(f^borrowed^flags);put(SURFACE,[0x5136c0 if f in(0x4bc810,0x4bc830)else 0x513588,0,DD_SURFACE]);put(SURFACE+120,[borrowed]);put(SURFACE+144,[0x51079c,0,0,0,0]);compare(f,SURFACE,[flags]if f in(0x4bc810,0x4bb060)else[],('primaryBaseSurfaceDelete',hex(f),borrowed,flags))
#Full descriptor copy uses forward original semantics even with overlap.
for f in(0x4b9150,0x4bfbd0):
 for offset in(0,4,12,16):
  prepare(f^offset);put(SURFACE,[0x513690,0,0]);put(SURFACE+144,[0x51079c,0,0,0,0]);compare(f,SURFACE,[MANAGER,SURFACE+offset],('forwardDescriptorAlias',hex(f),offset))
print('PASS surface deletes/copy',H.calls,H.eventCount,len(m.executed),flush=True)
#Cleanup rereads later holder slots after each virtual deleting callback.
for repeat in range(20):
 prepare(repeat);H.mutate='slots';put(HOLDER+16,[CHILD1,CHILD2,CHILD3]);compare(0x4ca8b0,HOLDER,[],'liveHolderSlotAliasing');assert H.deleteCount==[3,3]
#A readiness callback can overwrite a just-decremented effect lifetime. The
#source reads that word again after the callback when its result iszero.
oldEffect=H.effect;drawToken=[0,0]
def readinessMutation(f,r,a,native,buffers=()):
 i=0 if native else 1
 if f==0x720028:drawToken[i]=r
 if f==0x720014:put(drawToken[i]+100,[2],native)
 return oldEffect(f,r,a,native,buffers)
H.effect=readinessMutation
for repeat in range(16):
 prepare(repeat);H.ready=0;put(NODES,[0,0,CHILD1]);put(RENDERER+20,[NODES,NODES,1,0,0,10]);put(CHILD1+100,[1])
 for frame in range(4):compare(0x4d63c0,RENDERER,[HOLDER,ARG2],('retainedReadinessLifetimeWrites',repeat,frame))
H.effect=oldEffect
#Flag1 permits a null second auxiliary after allocation failure; initializer
#succeeds but pointer-only readiness remainsfalse. No success is invented.
prepare();H.allocFailure=3;compare(0x4ca6f0,HOLDER,[640,480,8,1],'skippedNullAuxiliaryInitializer');compare(0x4cf730,HOLDER,[],'skippedNullAuxiliaryNotReady');compare(0x4ca8b0,HOLDER,[],'skippedNullAuxiliaryCleanup')
#Original unchecked virtual dereference prefixes, with complete reached heap.
prefixes=0
for allocation,stop in[(1,0x4ca7e2),(2,0x4ca821),(3,0x4ca85c),(4,0x4bc8f6)]:
 prepare(allocation);H.allocFailure=allocation;H.sync();H.events[0].clear();H.events[1].clear();out=U();args=(U*4)(640,480,8,0)
 assert not lib.claw_scene_display_entry(0x4ca6f0,HOLDER,args,4,C.byref(H.display),H.displayDependency,None,C.byref(out)) and H.display.fault==1
 H.errors.clear();u=m.u;u.mem_write(m.stack,struct.pack('<5I',m.stop,640,480,8,0));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,HOLDER)
 def stopUnsafe(uc,address,size,user):
  if address==stop:uc.emu_stop()
 handle=u.hook_add(UC_HOOK_CODE,stopUnsafe);u.emu_start(0x4ca6f0,m.stop,count=1000000);u.hook_del(handle);assert u.reg_read(UC_X86_REG_EIP)==stop,(allocation,hex(u.reg_read(UC_X86_REG_EIP)))
 assert H.snapshot(True)==H.snapshot(False) and H.events[0]==H.events[1],('allocationPrefix',allocation)
 prefixes+=1;H.eventCount+=len(H.events[0])
report=dict(originalSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',wholeOriginalCalls=H.calls,stoppedUnsafePrefixes=prefixes,orderedFullSnapshots=H.eventCount,originalAddresses=len(m.executed),heapBytes=SIZE,globalsBytes=GLOBAL_SIZE,holderBytes=28,primaryBytes=48,auxiliaryBytes=52,surfaceBytes=188,boundaries='physical DD/COM/descriptors/allocator/diagnostic; queue child draw/delete callbacks remain source-address services, Story present/copy leaves frozen')
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS final',report,flush=True)
