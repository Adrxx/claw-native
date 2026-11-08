#!/usr/bin/env python3
import graphics_manager_lifecycle_helpers as H
from graphics_manager_lifecycle_helpers import *
prepare();compare(0x4bc220,MANAGER,[0x12345,0,640,480,8,17],'initial graphics startup');compare(0x4bc400,MANAGER,[1],'teardown');compare(0x4bc1b0,MANAGER,[],'destructor')
prepare();H.g.device=0;compare(0x4bc220,MANAGER,[0x12345,0x98765,640,480,0,17],'created display profile')
for w,h,bits in [(800,600,16),(640,480,8),(320,200,8),(640,480,32),(640,400,8)]:
 descriptor=[0]*27;descriptor[0]=108;descriptor[2]=h;descriptor[3]=w;descriptor[21]=bits;H.modes.append(descriptor)
compare(0x4bcc50,MANAGER,[],'whole enumeration and unsigned mode ordering');compare(0x4bc1b0,MANAGER,[],'enum destructor')
print('PASS initial graphics',H.calls,H.eventCount,len(m.executed),flush=True)
#Sticky first error, exact HRESULT(!=0) and signed size admission.
for shared in(0,DEVICE):
 for where in('create','cooperative','caps','enumerate','setMode','display'):
  for hr in(1,0x80004005,0xffffffff):
   for previous in(0,0x12345678):
    prepare(previous^hr);H.g.device=shared;put(MANAGER+0x880,[previous]);H.failure={where:hr}
    compare(0x4bc220,MANAGER,[0x12345,0x98765,640,480,0,17],('startupFailureSticky',shared,where,hr,previous));compare(0x4bc400,MANAGER,[1],'failureTeardown')
for width,height,bits in[(0,480,0),(640,0,8),(0xffffffff,480,32),(640,0x80000000,16),(640,480,8),(640,480,16),(640,480,24),(640,480,32)]:
 prepare();compare(0x4bc220,MANAGER,[0x12345,0,width,height,bits,0],('signedSizeAndDepth',width,height,bits))
#Preserved nominal array/list destructor fields and source free(nullptr).
for f,t,n in[(0x4f551d,ARRAY,5),(0x4f5192,NODES,7)]:
 for count in(0,1,4):
  prepare(count);put(t,[0x51079c,0,count,13,7]if n==5 else[0x51000c,0,0,0,0,0,10]);compare(f,t,[],'rawDestructorPreservation')
#The source comparator is unsigned and prioritizes width, height then depth.
for a,b in[(0,0),(0xffffffff,0),(0x80000000,0x7fffffff),(640,800),(800,640)]:
 for field in(8,12,0x54):
  prepare();put(SCRATCH,[0]*54);put(SCRATCH+field,[a]);put(SCRATCH+108+field,[b]);compare(0x4bcde0,MANAGER,[SCRATCH,SCRATCH+108],('unsignedComparator',field,a,b))
prepare();compare(0x4bc0e0,0,[],'actualGlobalArrayInitializer')
print('PASS graphics matrix',H.calls,H.eventCount,len(m.executed),flush=True)
#Retained real PAL construction → default188-byte surface → mode/reset cleanup.
for level in range(1,15):
 prepare(level);compare(0x4bc220,MANAGER,[0x12345,0,640,480,8,17],'retainedStartup')
 raw=(ROOT/f'work/original-disc-assets/LEVEL{level}/PALETTES/MAIN.PAL').read_bytes();assert len(raw)==768
 H.createPalette(raw,('sourcePAL',level));H.insertSurface();compare(0x4bd1c0,MANAGER,[640,480,8],'retainedFormatReset');compare(0x4bc400,MANAGER,[level%2],('retainedFullListsTeardown',level));compare(0x4bc1b0,MANAGER,[],'retainedSecondDestructor')
print('PASS real palettes/lifetimes',H.calls,H.eventCount,len(m.executed),flush=True)
#Source format conversion is first set-bit and wrapping8-minus-popcount;
#zero/discontiguous/full32-bit masks are legal observed raw inputs.
oldEffect=H.effect;customMasks=[0,0,0];displayBits=8

def formatEffect(f,r,a,native,buffers=()):
 if f==0x700030:
  output=[0]*27;output[0]=108;output[21]=displayBits;output[22:25]=customMasks
  if native:buffers[0][:]=output
  else:put(a[1],output,False)
  return H.failure.get('display',0)
 return oldEffect(f,r,a,native,buffers)
H.effect=formatEffect
for i in range(80):
 prepare(i);customMasks[:]=[random.Random(i+j*100).getrandbits(32)for j in range(3)]if i>5 else[[0,0,0],[0xff0000,0xff00,0xff],[0xf800,0x7e0,0x1f],[0xffffffff,1,0x80000000],[0x55555555,0xaaaaaaaa,0],[0x12340000,0x10204080,0xff]][i]
 for j in range(3):H.g.shifts[j]=i*37+j;H.g.reductions[j]=0xbeef+j
 put(MANAGER,[DEVICE]);compare(0x4bd0c0,MANAGER,[],('wholeFormatMasks',i))
H.effect=oldEffect
#Whole surface cleanup: borrowed DD, children, nested slots and flag-controlled delete.
for borrowed in(0,1,3,0xffffffff):
 for deleteFlags in(0,1,2,3):
  prepare(borrowed^deleteFlags);put(SURFACE,[0x513690,0,DD_SURFACE]);put(SURFACE+0x78,[borrowed]);put(SURFACE+0x90,[0x51079c,0,0,0,11]);compare(0x4bc5f0,SURFACE,[deleteFlags],('borrowedSurfaceDeleting',borrowed,deleteFlags))
#Mode enumeration preserves duplicates and exact sorting/count/callback ownership.
for n in(0,1,2,5,9):
 prepare(n)
 H.modes=[]
 for j in range(n):
  row=[0]*27;row[0]=108;row[2]=[480,600,0xffffffff][j%3];row[3]=[640,800,640][j%3];row[21]=[8,32,8][j%3];H.modes.append(row)
 compare(0x4bc220,MANAGER,[0x12345,0,640,480,8,17],'modeInventoryStartup');compare(0x4bcc50,MANAGER,[],'modeRetainedReenumeration');compare(0x4bc1b0,MANAGER,[],'modeFullDestruction')
print('PASS extra graphics',H.calls,H.eventCount,len(m.executed),flush=True)
#Callback mutations exercise captured next nodes, live array counts and alias order.
oldEffect=H.effect;trigger=0;kind='';seen=[0,0]
def mutationEffect(f,r,a,native,buffers=()):
 i=0 if native else 1
 if f==trigger:
  seen[i]+=1
  if kind=='capturedNext':
   put(NODES,[0],native);put(r+0xb4,[0x1234+seen[i]],native)
  elif kind=='shrinkingCount' and seen[i]==1:put(SURFACE+0x98,[1],native)
  elif kind=='liveModes' and seen[i]==1:put(MANAGER+0x3f8,[1],native)
  elif kind=='paletteAlias':
   if native:H.g.cooperative=0xface1234
   else:put(0x541374,[0xface1234],False)
  elif kind=='diagnosticSticky':put(MANAGER+0x880,[0xdead1234],native)
  elif kind=='releaseRebind':put(MANAGER,[DD_SURFACE],native)
 if f==0x720000:return r
 return oldEffect(f,r,a,native,buffers)
H.effect=mutationEffect
for repeat in range(12):
 prepare(repeat);kind='capturedNext';trigger=0x720000;seen[:]=[0,0]
 put(PALETTE,[H.PALVT]);put(H.PALVT,[0x720000]);put(SURFACE,[H.PALVT])
 put(NODES,[NODES+16,0,SURFACE]);put(NODES+16,[0,NODES,PALETTE]);put(MANAGER+0x3bc,[NODES,NODES+16,2,0,0,10])
 compare(0x4bc4b0,MANAGER,[],'capturedNextMutation');assert seen==[2,2]
 prepare(repeat);kind='shrinkingCount';trigger=0x720000;seen[:]=[0,0]
 put(PALETTE,[H.PALVT]);put(H.PALVT,[0x720000]);put(SURFACE+0x90,[0x51079c,ARRAY,3,3,0]);put(ARRAY,[PALETTE,PALETTE,PALETTE]);put(SURFACE+8,[0])
 compare(0x4b9540,SURFACE,[],'childCountReread');assert seen==[1,1]
 prepare(repeat);kind='liveModes';trigger=0x4f6428;seen[:]=[0,0]
 put(MANAGER+0x3f0,[0x51079c,ARRAY,3,3,0]);put(ARRAY,[SCRATCH,SCRATCH+108,SCRATCH+216]);compare(0x4bc400,MANAGER,[0],'modeCountReread')
 prepare(repeat);kind='paletteAlias';trigger=0x4f6428;seen[:]=[0,0]
 #Actual existing palette body has owned raw byte storage and no COM Release.
 put(PALETTE,[0]*14);put(PALETTE+0xc,[DATA]);put(NODES,[0,0,PALETTE]);put(MANAGER+0x3d8,[NODES,NODES,1,0,0,10]);compare(0x4bc9d0,MANAGER,[],'paletteCooperativeAlias');assert H.g.cooperative==0xface1234
 prepare(repeat);kind='diagnosticSticky';trigger=0x4bd260;seen[:]=[0,0];H.failure={'cooperative':1}
 compare(0x4bc220,MANAGER,[0,0,640,480,8,17],'diagnosticOwnsStickyError');assert get(MANAGER+0x880)[0]==0xdead1234
 prepare(repeat);kind='releaseRebind';trigger=0x700008;seen[:]=[0,0];put(MANAGER,[DEVICE]);compare(0x4bc400,MANAGER,[0],'releaseThenSourceZero');assert get(MANAGER)[0]==0
H.effect=oldEffect
#Stop the original before its unchecked null dereference/copy. This proves
#reached stores/events, not a fabricated successful allocation-error behavior.
prefixes=0
for branch in ('modeAllocation','nullCreatedDevice'):
 prepare();stop=0x4bcdb7 if branch=='modeAllocation' else 0x4bc25c
 f=0x4bcda0 if branch=='modeAllocation' else 0x4bc220
 argv=[SCRATCH,0] if branch=='modeAllocation' else[0,0,640,480,8,17]
 if branch=='modeAllocation':H.allocFailure=1;put(SCRATCH,[0]*27)
 else:
  H.g.device=0
  def nullCreate(fn,r,a,native,buffers=()):
   if fn==0x546850:put(a[1],[0],native);return 0
   return oldEffect(fn,r,a,native,buffers)
  H.effect=nullCreate
 H.sync();H.events[0].clear();H.events[1].clear();out=U();args=(U*len(argv))(*argv)
 assert not lib.claw_graphics_manager_lifecycle_entry(f,MANAGER,args,len(argv),C.byref(H.context),H.dependency,None,C.byref(out)) and H.context.fault==1
 H.errors.clear()
 u=m.u;u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(argv),*argv));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,MANAGER)
 def stopUnsafe(uc,address,size,user):
  if address==stop:uc.emu_stop()
 handle=u.hook_add(UC_HOOK_CODE,stopUnsafe)
 u.emu_start(f,m.stop,count=100000);u.hook_del(handle);assert u.reg_read(UC_X86_REG_EIP)==stop,(branch,hex(u.reg_read(UC_X86_REG_EIP)))
 assert H.snapshot(True)==H.snapshot(False) and H.events[0]==H.events[1],branch
 prefixes+=1;H.eventCount+=len(H.events[0]);H.effect=oldEffect
for count in(0,1,3,7):
 prepare(count);put(0x541378,[0x51079c,ARRAY,count,count+3,17]);compare(0x4bc100,0,[],'wholeGlobalModeArrayDestructor')
print('PASS mutations/prefixes',H.calls,prefixes,H.eventCount,len(m.executed),flush=True)
report=dict(originalSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',wholeOriginalCalls=H.calls,stoppedUnsafePrefixes=prefixes,orderedFullSnapshots=H.eventCount,originalAddresses=len(m.executed),heapBytes=SIZE,globalsBytes=GLOBAL_SIZE,managerBytes=2180,realPALProfiles=14,boundaries='physical DirectDraw/COM/descriptors/allocator/diagnostic and unknown polymorphic deletions; original mode callback/array/list/palette/surface bodies compose')
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS final',report,flush=True)
