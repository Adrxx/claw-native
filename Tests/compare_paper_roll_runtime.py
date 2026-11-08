#!/usr/bin/env python3
import paper_roll_runtime_helpers as H
from paper_roll_runtime_helpers import *
prepare();compare(0x4ee880,EFFECT,[],'ctor');compare(0x4ee9a0,EFFECT,[DESC],'init');compare(0x4efac0,EFFECT,[],'max')
for s in[0,1,2,7,40,80]:compare(0x4eecc0,EFFECT,[s],('step',s))
print('PASS initial',H.calls,H.events,flush=True)
for direction in(0,1,2):
 for mode in(1,2,3):
  for bpp in(1,2,3,4):
   for w,h,r in[(37,3,3),(128,5,13),(321,4,40)]:
    prepare(w,h,bpp,direction,pad=7,radius=r,mode=mode,lit=(bpp==1))
    compare(0x4ee880,EFFECT,[],'matrixCtor');assert compare(0x4ee9a0,EFFECT,[DESC],('matrixInit',mode,direction,bpp,w,r))==1
    maximum=compare(0x4efac0,EFFECT,[],'maximum')
    for step in sorted({0,1,maximum//3,maximum//2,maximum-1,maximum}):compare(0x4eecc0,EFFECT,[step],('retainedPixels',mode,direction,bpp,w,r,step))
    compare(0x4ee8c0,EFFECT,[1],'cleanup')
print('PASS matrix',H.calls,H.events,flush=True)
for fn,args in[(0x48f500,[150]),(0x48f740,[0x526a50,0,0,0,150]),(0x48f740,[0x526a50,1,25,40,150])]:
 for bypass in(0,1):
  prepare(320,5,1,0,pad=3);g.bypass=bypass;compare(fn,OWNER,args,('wholeWrapper',hex(fn),bypass,args))
print('PASS wrappers',H.calls,H.events,flush=True)
#Actual retail roller CLT; source loader's already verified length word/payload
#boundary is honored. PCX bytes are ONLY read from prior unchanged-original
#captures; the unfinished codec is neither linked, rerun, nor claimed complete.
retail=[]
for line in(ROOT/'work/pcx-image-agent/retail-manifest.txt').read_text().splitlines():
 w,h,planes,pad,input,golden=line.split()
 if input.endswith('STATES/ROLLER/SCREENS/PAPER.PCX')or input.endswith('STATES/CREDITS/SCREENS/CREDITS.PCX'):
  assert (int(w),int(h),int(planes))==(640,480,1);raw=Path(golden).read_bytes();stride=640+int(pad);retail.append((input,b''.join(raw[y*stride:y*stride+640]for y in range(480))))
assert len(retail)==2
clt=(ROOT/'work/original-disc-assets/STATES/ROLLER/PALETTES/ROLLER.CLT').read_bytes();assert struct.unpack_from('<I',clt)[0]==16384
for direction in(0,1):
 prepare(640,480,1,direction,pad=0,lit=1)
 for input,pixels in retail:C.memmove(C.addressof(heap)+(PIXELCAP if input.endswith('PAPER.PCX')else PIXEL1)-BASE,pixels,len(pixels))
 C.memmove(C.addressof(heap)+PALETTEPIX-BASE,clt[4:],16384)
 compare(0x4ec050,MANAGER,[0,DESC],('actual640Factory',direction))
 for step in[0,1,79,80,119,120,199,239,240]:compare(0x4eecc0,EFFECT,[step],('retailRetained',direction,step))
 compare(0x4ec600,MANAGER,[EFFECT],('actualCleanup',direction))
print('PASS retail',H.calls,H.events,flush=True)
#Getter readiness, cached path, acquired table and failure ownership.
for profile in('cached','inactive','noManager','noResources','noFile','noPayload','loadFailure','loadSuccess'):
 prepare();put(APP+0x8c,[TABLE if profile=='cached'else 0]);put(APP+0x34,[NAMESPACE]);H.getterFailure=int(profile=='inactive');H.payloadFailure=int(profile=='noPayload');H.paletteLoadFailure=int(profile=='loadFailure');H.resourceFailure=int(profile=='noFile')
 if profile=='noManager':put(APP+0x58,[0])
 if profile=='noResources':put(APP+0x34,[0])
 compare(0x42a4f0,APP,[],('rollerGetter',profile))
 H.getterFailure=H.payloadFailure=H.paletteLoadFailure=0
for mode in(0,1,2,3,4,0xffffffff):
 for radius in(0,1,40,100):
  prepare(128,3,1,0,radius=radius,mode=mode);compare(0x4ee880,EFFECT,[],'invalidCtor');compare(0x4ee9a0,EFFECT,[DESC],('admission',mode,radius));compare(0x4ee8c0,EFFECT,[1],'admissionCleanup')
for field in(4,8,12):
 prepare();put(EFFECT+0x24,[0,0]);put(DESC+field,[0]);compare(0x4ee9a0,EFFECT,[DESC],('missingSurface',field))
prepare();compare(0x4ee9a0,EFFECT,[0],'nullDescriptor')
for tag in(0,2,3,0xffffffff):
 prepare();put(DESC,[tag]);compare(0x4ec050,MANAGER,[0,DESC],('invalidFactoryTag',tag))
for flags in(0,1,2,3,0xffffffff):
 prepare();compare(0x4ee880,EFFECT,[],'deletingCtor');compare(0x4ee8c0,EFFECT,[flags],('deleteFlags',flags))
for branch in('noManager','noGraphics','noTarget','noFile','noPayload','noSurface','copyFailure','badPaperWidth','badPaperHeight','paletteFailure'):
 for fn,args in[(0x48f500,[150]),(0x48f740,[0x526a50,0,0,0,150])]:
  prepare(320,5);put(OWNER+64,[0]);put(OWNER+44,[0]);H.payloadFailure=0
  if branch=='noManager':put(OWNER+16,[0])
  if branch=='noGraphics':put(PARENT+28,[0])
  if branch=='noTarget':put(IMAGE0+44,[0])
  if branch=='noFile':H.resourceFailure=1
  if branch=='noPayload':H.payloadFailure=1
  if branch=='noSurface':H.surfaceFailure=1
  if branch=='copyFailure':H.copyFailure=1
  if branch=='paletteFailure':H.paletteFailure=1
  if branch=='badPaperWidth':put(SURFACE1+24,[319])
  if branch=='badPaperHeight':put(SURFACE1+20,[4])
  compare(fn,OWNER,args,('wrapperFailure',branch,hex(fn)))
  H.payloadFailure=0
print('PASS failure paths',H.calls,H.events,flush=True)
for direction in(0,1):
 for alias in(0,1,3,7):
  prepare(320,5,3,direction,pad=7);H.pixelMappings={SURFACE0:PIXEL0,SURFACE1:PIXEL0+alias,CAPTURE:PIXELCAP};compare(0x4ee880,EFFECT,[],'aliasCtor');compare(0x4ee9a0,EFFECT,[DESC],'aliasInit')
  for step in[0,1,20,20,40,3,80]:compare(0x4eecc0,EFFECT,[step],('retainedAliasReverse',direction,alias,step))
  H.pixelMappings=None
#Untested unsafe domains must stop at the reached source write; do not claim
#the native missing-span guard is an original allocation-failure return.
prepare();H.allocationFailureOrdinal=0;H.comparePrefix(0x4ec050,MANAGER,[0,DESC],'nullEffectStore',1,0x4ecb08)
prepare();compare(0x4ee880,EFFECT,[],'curveFailureCtor');H.allocationFailureOrdinal=0;H.comparePrefix(0x4ee9a0,EFFECT,[DESC],'nullCurveWrite',1,0x4eeb13)
print('PASS final',H.calls,H.events,H.prefixes,flush=True)
report=dict(originalSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',wholeOriginalCalls=H.calls,orderedFullSnapshots=H.events,unsafePrefixes=H.prefixes,instrumentedTextAddresses=len([a for a in m.executed if 0x401000<=a<0x50adb5]),totalInstrumentedAddresses=len(m.executed),retail=[dict(path=str(Path(p).relative_to(ROOT)),pixelSHA256=hashlib.sha256(b).hexdigest())for p,b in retail],rollerCLTSHA256=hashlib.sha256(clt).hexdigest(),boundaries='physical DD/resource/PCX/CString/optional generated table calls explicit; prior PCX original captures reused read-only, codec remains unfinished')
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
for fn,t,a in[(0x4ecb40,DESC,[]),(0x4ec050,MANAGER,[0,0])]:
 prepare();compare(fn,t,a,'sourceDefaultDescriptor')
 if fn==0x4ec050:compare(0x4ec600,MANAGER,[EFFECT],'defaultFactoryCleanup')
prepare();put(DESC+4,[0]);put(MANAGER,[0]);compare(0x4ec050,MANAGER,[0,DESC],'failedFactoryInitializationDiagnostic')
for direction in(0,1):
 prepare(320,5,1,direction,lit=1);compare(0x4ec050,MANAGER,[0,DESC],'joinedRunnerFactory');H.clockSequence=[100,100,100,101,101,125,130,175,200,260,310,400,500];compare(0x4ec9c0,EFFECT,[200,20,0],'joinedRepeatedClockRunner');compare(0x4ec600,MANAGER,[EFFECT],'joinedRunnerCleanup');H.clockSequence=None
for gate in(0,1):
 prepare(320,5);H.lookupResult=RESOURCE;enabled.value=gate;compare(0x48f500,OWNER,[150],('rollupSoundGate',gate));enabled.value=1
print('PASS final closure',H.calls,H.events,H.prefixes,flush=True)
report.update(wholeOriginalCalls=H.calls,orderedFullSnapshots=H.events,unsafePrefixes=H.prefixes,instrumentedTextAddresses=len([a for a in m.executed if 0x401000<=a<0x50adb5]),totalInstrumentedAddresses=len(m.executed))
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
