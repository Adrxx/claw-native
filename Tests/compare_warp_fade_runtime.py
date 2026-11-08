#!/usr/bin/env python3
import warp_fade_runtime_helpers as H
from warp_fade_runtime_helpers import *
prepare();compare(0x4ed060,EFFECT,[],'ctor');compare(0x4ed0b0,EFFECT,[DESC],'init');compare(0x4ed5d0,EFFECT,[],'max')
for s in [0,1,2,3,7,20,25,27]:compare(0x4ed1a0,EFFECT,[s],f'step{s}')
compare(0x4ed0a0,EFFECT,[],'baseDestructor');compare(0x4ed080,EFFECT,[1],'deleting')
print('PASS initial wholewarp',H.calls,H.events,len(m.executed),flush=True)

#Source fild/fmul literals checked directly against immutable image.
assert struct.unpack('<f',bytes(m.u.mem_read(0x514240,4)))[0]==1.5707950592041015625
for direction in(0,1):
 for bpp in(1,2,3,4):
  for w,h,percent in[(1,1,15),(2,3,80),(17,13,1),(32,25,15),(61,39,100)]:
   prepare(w,h,bpp,direction,pad=7,percent=percent,seed=w*h)
   compare(0x4ed060,EFFECT,[],'matrixCtor');compare(0x4ed0b0,EFFECT,[DESC],('matrixInit',w,h,percent,direction,bpp));maximum=get(EFFECT+0x54)[0]+h
   for step in sorted({0,1,maximum//3,maximum//2,maximum,maximum+2}):compare(0x4ed1a0,EFFECT,[step],('retainedPixels',w,h,percent,direction,bpp,step))
   compare(0x4ed080,EFFECT,[direction],'matrixCleanup')
print('PASS pixel matrix',H.calls,H.events,len(m.executed),flush=True)

for direction in(0,1):
 prepare(31,23,1,direction,percent=80)
 compare(0x4ec050,MANAGER,[2,DESC],'sourceFactory')
 H.clockSequence=[100,100,100,120,120,150,180,200,250,300,350,400,500]
 compare(0x4ec9c0,EFFECT,[200,0,0],'wholeRunnerRepeatedClock')
 compare(0x4ec600,MANAGER,[EFFECT],'registeredCleanup')
 H.clockSequence=None
print('PASS factoryrunner',H.calls,H.events,len(m.executed),flush=True)

#Finite source failures and real prime/permutation helper semantics.
for percent in[0,1,99,100,101,0xffffffff]:
 prepare(17,13,1,0,percent=percent)
 compare(0x4ed060,EFFECT,[],'percentCtor');compare(0x4ed0b0,EFFECT,[DESC],('signedPercentAdmission',percent))
for primary,secondary in[(0,0),(0,SURFACE1),(SURFACE0,0),(SURFACE0,SURFACE1)]:
 prepare();put(EFFECT+0x24,[0,0]);put(DESC+4,[primary,secondary]);compare(0x4ed0b0,EFFECT,[DESC],('nullSurfaceAdmission',primary,secondary))
for tag in[0,1,2,3,0xffffffff]:
 prepare();put(DESC,[tag]);compare(0x4ec050,MANAGER,[2,DESC],('factoryDescriptorTag',tag))
prepare(0,13);compare(0x4ed060,EFFECT,[],'zeroWidthCtor');H.comparePrefix(0x4ed0b0,EFFECT,[DESC],'zeroWidthSourceDivFault',2,0x4ed160)
prepare();H.allocationFailureOrdinal=0;H.comparePrefix(0x4ec050,MANAGER,[2,DESC],'nullObjectUnsafeStore',1,0x4ecb08)
for failure in[1,2]:
 prepare();H.allocationFailureOrdinal=failure;compare(0x4ec050,MANAGER,[2,DESC],('sourceAllocationFailure',failure))
for flags in[0,1,2,3,0xffffffff]:
 prepare();compare(0x4ed060,EFFECT,[],'deleteCtor');compare(0x4ed080,EFFECT,[flags],('deleteFlags',flags))
for n in[0,1,2,3,4,17,31,641,0xffffffff]:
 prepare();compare(0x4efc40,0,[n],('wholePrimePredicate',n))
for low,high,initial in[(0,1,1),(0,2,1),(0,3,1),(0,13,1),(1,17,1),(0,100,1),(100,100,1),(19,3,1)]:
 prepare();compare(0x4efb00,0,[PERM+0x1000,low,high,initial],('wholePermutation',low,high,initial))
print('PASS edges',H.calls,H.events,len(m.executed),'prefixes',H.prefixes,flush=True)

#Same original shared clock, surfaces and aliases through retained histories.

for start,duration,wait,pump in[(0,1,0,1),(16777217,100,20,1),(0xfffff000,200,0,0),(0x80000000,200,0,0)]:
 prepare(17,13,1,0,percent=80);compare(0x4ed060,EFFECT,[],'clockCtor');compare(0x4ed0b0,EFFECT,[DESC],'clockInit');H.clockStart=start;H.clockDelta=512 if start>=0x80000000 else 17;H.clockSequence=None;compare(0x4ec9c0,EFFECT,[duration,wait,pump],('runnerFloatClock',start,duration,wait,pump))
#Wrap and stopped wall clock do not manufacture completion: exact prefixes.
for times in [[100],[0xfffffff0,0xfffffff0,0xfffffff0,5,10,15]]:
 prepare(17,13,1,1,percent=80);compare(0x4ed060,EFFECT,[],'stalledCtor');compare(0x4ed0b0,EFFECT,[DESC],'stalledInit');H.clockSequence=times;ctx.maximumClockReads=12
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();out=C.c_uint32();argv=(C.c_uint32*3)(200,0,0)
 assert not lib.claw_warp_fade_entry(0x4ec9c0,EFFECT,argv,3,C.byref(warp),dependency,None,C.byref(out))and ctx.fault==2
 #Stop before source clock call number13; all12 observed imports execute.
 def stop(u,address,size,user):
  if address==0x4eca42 and len([e for e in oe if e[0]==0x546a24])>=12:u.emu_stop()
 handle=m.u.hook_add(UC_HOOK_CODE,stop);m.u.mem_write(m.stack,struct.pack('<IIII',m.stop,200,0,0));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,EFFECT);m.u.emu_start(0x4ec9c0,m.stop,count=30000000);m.u.hook_del(handle)
 assert m.u.reg_read(UC_X86_REG_EIP)==0x4eca42;assert ne==oe;assert raw(True)==raw(False);assert globalsRaw(True)==globalsRaw(False);H.prefixes+=1;H.events+=len(ne);ctx.maximumClockReads=10000;H.clockSequence=None
print('PASS clocks',H.calls,H.events,len(m.executed),'prefixes',H.prefixes,flush=True)

for offset in[0,1,3,7]:
 for direction in[0,1]:
  prepare(32,25,3,direction,pad=7,percent=80)
  H.pixelMappings={SURFACE0:PIXEL0,SURFACE1:PIXEL0+offset,CAPTURE:PIXELCAP}
  compare(0x4ed060,EFFECT,[],'aliasCtor');compare(0x4ed0b0,EFFECT,[DESC],'aliasInit')
  maximum=get(EFFECT+0x54)[0]+25
  for step in[1,7,7,maximum//2,3,maximum]:compare(0x4ed1a0,EFFECT,[step],('shiftedAliasRepeatedReverse',direction,offset,step))
  H.pixelMappings=None
#Unequal source pitch, zero-byte pixels and source-only clear override.
for bpp in[0,1,4]:
 prepare(32,25,bpp,0,pad=9,percent=15);put(SURFACE1+0x1c,[32*bpp+13]);compare(0x4ed060,EFFECT,[],'strideCtor');compare(0x4ed0b0,EFFECT,[DESC],'strideInit')
 for step in[1,3,13,28]:compare(0x4ed1a0,EFFECT,[step],('sourceStrideBpp',bpp,step))
print('PASS aliases',H.calls,H.events,len(m.executed),flush=True)

profiles=[]
for direction in(0,1):
 prepare(640,480,1,direction,pad=0,percent=80,seed=111567)
 raw=(ROOT/'work/original-disc-assets/LEVEL1/PALETTES/MAIN.PAL').read_bytes();assert len(raw)==768
 #A byte-identical representative indexed old/new frame payload. The resource
 #is provenance/input only; source blits do not read RGB or palette entries.
 frame=bytes((raw[(i*17)%768]^(i%256))for i in range(640*480))
 C.memmove(C.addressof(heap)+PIXEL0-BASE,frame,len(frame));C.memmove(C.addressof(heap)+PIXEL1-BASE,frame[::-1],len(frame))
 compare(0x4ec050,MANAGER,[2,DESC],('640x480factory',direction))
 maximum=get(EFFECT+0x54)[0]+480
 for step in[0,1,17,maximum//2,maximum-1,maximum]:compare(0x4ed1a0,EFFECT,[step],('640x480retained',direction,step))
 compare(0x4ec600,MANAGER,[EFFECT],('640x480cleanup',direction))
 profiles.append(dict(clearFlag=direction,paletteSHA256=hashlib.sha256(raw).hexdigest(),frameSHA256=hashlib.sha256(frame).hexdigest(),maximum=maximum))
print('PASS source640x480',H.calls,H.events,len(m.executed),profiles,flush=True)

report=dict(originalSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',wholeOriginalCalls=H.calls,stoppedUnsafePrefixes=H.prefixes,orderedFullSnapshots=H.events,originalAddresses=len(m.executed),heapBytes=SIZE,globalsBytes=0x1c000,allocationBytes=0x7d5c,actualViewportProfiles=profiles,boundaries='physical locks/unlocks/clock/TLS transport; exact shared CRT and frozen runner/carray/string/palette lifetime are composed; representative PAL-derived indexed frame, not full retail scene')
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS final',report,flush=True)
