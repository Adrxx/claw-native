#!/usr/bin/env python3
import scene_lifecycle_helpers as H
from scene_lifecycle_helpers import *
for f,t in[(0x4ceef0,SCENE),(0x4ce9c0,SCENE),(0x4ce9a0,SCENE),(0x4cefc0,SCENE),(0x4cf0a0,PALETTE_CONTROLLER),(0x4cf160,IMAGE_CONTROLLER),(0x4cf940,LOGIC_CONTROLLER),(0x4cf9d0,ANIMATION_CONTROLLER),(0x4cf800,SOUND_CONTROLLER)]:
 prepare();compare(f,t,[1]if f in(0x4ce9a0,0x4cf0a0,0x4cf160,0x4cf940,0x4cf9d0,0x4cf800)else[],'emptyInitialBody')
for f,t in[(0x4d4370,PALETTE_CONTROLLER),(0x4d0240,IMAGE_CONTROLLER),(0x4d6290,LOGIC_CONTROLLER),(0x4cdf30,ANIMATION_CONTROLLER),(0x4cdf40,ANIMATION_CONTROLLER),(0x4ca300,SOUND_CONTROLLER),(0x4ca2e0,SOUND_CONTROLLER)]:
 prepare();H.mapFixture(t+16,1);compare(f,t,[],'wholeMapPayloadCleanup')
print('PASS initial lifecycle',H.calls,H.eventCount,len(m.executed),flush=True)
#Every finite controller/map destructor with owned key chains and three maps.
for f,t in [(0x4cf0c0,PALETTE_CONTROLLER),(0x4cf0a0,PALETTE_CONTROLLER),(0x4cf180,IMAGE_CONTROLLER),(0x4cf160,IMAGE_CONTROLLER),(0x4cf960,LOGIC_CONTROLLER),(0x4cf940,LOGIC_CONTROLLER),(0x4cf9f0,ANIMATION_CONTROLLER),(0x4cf9d0,ANIMATION_CONTROLLER),(0x4cf820,SOUND_CONTROLLER),(0x4cf800,SOUND_CONTROLLER)]:
 for i in range(20):
  prepare(i);H.mapFixture(t+16,1)
  if t==PALETTE_CONTROLLER:
   #Secondary/tertiary maps own keys, not duplicated payload destruction.
   put(t+44,[0x5105c4,0,17,0,0,0,10]);put(t+72,[0x5105c4,0,17,0,0,0,10])
  compare(f,t,[i%4]if f in(0x4cf0a0,0x4cf160,0x4cf940,0x4cf9d0,0x4cf800)else[],'wholeControllerDestruction')
#Wrapper-only actor/renderer destructors compose peer sourceclear and pool.
for f,t,vt in[(0x4cf8a0,CHILD1,0x513c20),(0x4cf8c0,CHILD1,0x513c20),(0x4cf280,CHILD1,0x513be8),(0x4cf2a0,CHILD1,0x513be8)]:
 for i in range(8):
  prepare(i);put(t,[vt,0,0,SCENE,0x5107bc,0,0,0,0,0,10]);compare(f,t,[i%4]if f in(0x4cf8a0,0x4cf280)else[],'wholeCollectionWrapper')
print('PASS controllers/wrappers',H.calls,H.eventCount,len(m.executed),flush=True)
#Retained actual default scene vtables/spans, then repeated cleanup/destruction.
for repeat in range(24):
 H.defaultScene();compare(0x4cefc0,SCENE,[],'defaultSceneNotReady');compare(0x4ceef0,SCENE,[],'wholeDefaultSceneCleanup');compare(0x4ceef0,SCENE,[],'repeatDefaultSceneCleanup');compare(0x4ce9a0,SCENE,[repeat%4],'defaultSceneDeleting')
print('PASS default scenes',H.calls,H.eventCount,len(m.executed),flush=True)
#All14 retailMAIN.PALs: whole source display→PAL load→controller→scene teardown.
for level in range(1,15):
 H.defaultScene();H.displayStartup();H.realPalette((ROOT/f'work/original-disc-assets/LEVEL{level}/PALETTES/MAIN.PAL').read_bytes());compare(0x4cefc0,SCENE,[],'retailPaletteSceneReady');compare(0x4ceef0,SCENE,[],'retailPaletteWholeSceneCleanup');compare(0x4ce9c0,SCENE,[],'retailPaletteRepeatDestruction')
print('PASS real PAL scene chains',H.calls,H.eventCount,len(m.executed),flush=True)
for repeat in range(12):
 H.actualFailedInitialization();compare(0x4ceef0,SCENE,[],'actualInitializerFailureCleanup');compare(0x4ce9a0,SCENE,[repeat%4],'actualInitializerFailureDeleting')
print('PASS actual initializer failure',H.calls,H.eventCount,len(m.executed),flush=True)
#Whole public map and CString sharing paths. Locked-copy remains exactservice.
for sourceRefs in(0,1,2,7):
 for targetRefs in(1,2,5):
  for same in(0,1):
   prepare(sourceRefs+targetRefs);put(STRING1,[sourceRefs,3,3,0x616263]);put(STRING2,[targetRefs,3,3,0x646566]);put(SCRATCH,[STRING1+12 if same else STRING2+12,STRING1+12]);compare(0x4f667d,SCRATCH,[SCRATCH+4],'sourceCStringSharedAssign');compare(0x4f64ba,SCRATCH,[],'sourceCStringReset')
for method in(0x4f61a1,0x4f61f3,0x4f5d00):
 for size in(0,1,5,17):
  prepare(size);H.mapFixture(LOGIC_CONTROLLER+16);put(LOGIC_CONTROLLER+24,[size]);compare(method,LOGIC_CONTROLLER+16,[],'rawEmptyMapSizePreserved')
for position in(0xffffffff,ASSOC1,ASSOC2,ASSOC3):
 prepare(position);H.mapFixture(LOGIC_CONTROLLER+16,1);put(SCRATCH,[position,get(0x52e1cc)[0],0]);compare(0x4f5e1e,LOGIC_CONTROLLER+16,[SCRATCH,SCRATCH+4,SCRATCH+8],'wholeMapIteration');compare(0x4f64ba,SCRATCH+4,[],'iterationKeyRelease')
#Each partial ownership prefix, preserving remaining scene words, models
#allocation/initialization interruption without inventing successful resources.
for mask in range(256):
 prepare(mask);offsets=(40,32,4,8,12,16,20,24,44,36);put(CHILDVT,[0x720004,0x720004]);put(CHILD1,[CHILDVT])
 for i,off in enumerate(offsets):
  if mask&(1<<(i%8)):put(SCENE+off,[CHILD1])
 compare(0x4ceef0,SCENE,[],'partialOwnershipMask');compare(0x4ce9c0,SCENE,[],'partialRepeatDestruction')
print('PASS map/string/partial ownership',H.calls,H.eventCount,len(m.executed),flush=True)
#Rebinding later ownership and guarded recursive cleanup use actual caller
#bodies; no callback-independent extra pass or stopAll is inserted.
oldEffect=H.effect;policy='';entered=[False,False]
def lifecycleMutation(f,r,a,native,buffers=()):
 i=0 if native else 1
 if f==0x720004:
  if policy=='later':put(SCENE+44,[CHILD3],native)
  if policy=='reentrant'and not entered[i]:
   entered[i]=True;put(SCENE+40,[0],native)
   if native:
    out=U();assert lib.claw_scene_lifecycle_entry(0x4ceef0,SCENE,None,0,C.byref(H.lifecycle),H.lifecycleDependency,None,C.byref(out))
   else:H.sourceCall(0x4ceef0,SCENE,[])
 return oldEffect(f,r,a,native,buffers)
H.effect=lifecycleMutation
for policy in('later','reentrant'):
 for repeat in range(20):
  H.defaultScene();put(CHILDVT+4,[0x720004]);put(SCENE+40,[CHILD1]);put(SCENE+44,[CHILD2]);entered[:]=[False,False];compare(0x4ceef0,SCENE,[],('callbackLifeOrder',policy,repeat));compare(0x4ceef0,SCENE,[],'callbackRepeatCleanup')
H.effect=oldEffect
print('PASS alias/reentrant cleanup',H.calls,H.eventCount,len(m.executed),flush=True)
#Unsafe profiles are compared only up to the precise original dereference;
#native diagnostics are not represented as original successful outcomes.
unsafeCount=0
for method,receiver,args,stop in[(0x4f5e1e,LOGIC_CONTROLLER+16,[SCRATCH,SCRATCH+4,SCRATCH+8],0x4f5e46),(0x4ceef0,SCENE,[],0x4cef02)]:
 prepare();put(SCRATCH,[0xffffffff,get(0x52e1cc)[0],0])
 if method==0x4f5e1e:
  put(LOGIC_CONTROLLER+16,[0x5105c4,BUCKETS,5,1,0,0,10]);put(BUCKETS,[0]*5)
 else:put(SCENE+40,[CHILD1]);put(CHILD1,[0])
 sync();events[0].clear();events[1].clear();hit=[]
 def stopUnsafe(u,address,size,user):
  if address==stop:hit.append(address);u.emu_stop()
 handle=m.u.hook_add(UC_HOOK_CODE,stopUnsafe)
 try:
  try:m.call(method,receiver,struct.pack('<'+'I'*len(args),*args),max_instructions=100000)
  except AssertionError:
   assert hit==[stop], 'Unexpected original failure outside unsafe prefix'
 finally:m.u.hook_del(handle)
 assert hit==[stop]
 out=U();argv=(U*len(args))(*args)
 assert not lib.claw_scene_lifecycle_entry(method,receiver,argv,len(args),C.byref(H.lifecycle),H.lifecycleDependency,None,C.byref(out)) and H.lifecycle.fault==1
 assert snapshot(True)==snapshot(False) and events[0]==events[1]
 unsafeCount+=1
textAddresses=sum(0x401000<=a<0x50adb5 for a in m.executed)
report={'originalSHA256':hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'wholeCalls':H.calls,'unsafePrefixes':unsafeCount,'orderedSnapshots':H.eventCount,'instrumentedTextAddresses':textAddresses,'totalInstrumentedAddresses':len(m.executed),'heapBytes':SIZE,'globalBytes':GLOBAL_SIZE,'actualRetailPALs':14}
(WORK/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS frozen lifecycle',json.dumps(report,sort_keys=True),flush=True)
