#!/usr/bin/env python3
import scene_fade_runtime_helpers as h
h.prepare();h.compare(0x4ed060,h.EFFECT,[],'whole ctor');h.compare(0x4ed0b0,h.EFFECT,[h.DESC],'whole init');h.compare(0x4ed1a0,h.EFFECT,[1],'first step');h.compare(0x4ed1a0,h.EFFECT,[10],'later step');h.compare(0x4ed5d0,h.EFFECT,[],'maxsteps');h.compare(0x4ec9c0,h.EFFECT,[1450,0,0],'whole source runner');h.compare(0x4ed080,h.EFFECT,[1],'delete');print('PASS initial type2 graph')
for dimensions in((1,1),(2,2),(3,5),(31,23),(127,101),(640,480)):
 for direction in(0,1):
  h.prepare(*dimensions,direction=direction);h.clockDelta=200 if dimensions==(640,480) else 25;h.compare(0x4ec050,h.MANAGER,[2,h.DESC],('factory dimensions/direction',dimensions,direction));h.compare(0x4ec9c0,h.EFFECT,[1450,17,1],('retained real type2 runner',dimensions,direction));h.compare(0x4ec600,h.MANAGER,[h.EFFECT],('completed source removal',dimensions,direction))
for w in(1,2,3,4,17,31,64,127,640,1999):
 h.prepare();h.compare(0x4efb00,0,[h.EFFECT+0x5e1c,0,w,1],('whole source permutation',w))
for v in(0,1,2,3,4,5,7,9,11,31,64,640,1999,0xffffffff):
 h.prepare();h.compare(0x4efc40,0,[v],('whole source prime predicate',v))
for percent in(0,1,15,80,100,101,0xffffffff):
 h.prepare(percent=percent);h.compare(0x4ed0b0,h.EFFECT,[h.DESC],('band percent exact edges',percent))
for bpp in(0,1,2,3,4):
 for direction in(0,1):
  h.prepare(bpp=bpp,direction=direction);h.compare(0x4ed0b0,h.EFFECT,[h.DESC],('initial per-pixel-byte profile',bpp,direction))
  for step in(0,1,2,7,15,23,41):h.compare(0x4ed1a0,h.EFFECT,[step],('retained per-pixel row/multibyte/padding',bpp,direction,step))
for percent in(101,0xffffffff):
 h.prepare(percent=percent);h.compare(0x4ec050,h.MANAGER,[2,h.DESC],('factory invalid descriptor diagnostics',percent))
print('PASS type2 shape, factory, permutation, pixels, completed lifetimes')

for duration in(1,17,1450):
 for delay in(0,1,50):
  for pump in(0,1):
   h.prepare();h.clockDelta=200;h.compare(0x4ed0b0,h.EFFECT,[h.DESC],('duration trajectory init',duration,delay,pump));h.compare(0x4ec9c0,h.EFFECT,[duration,delay,pump],('clock/delay/verticalblank',duration,delay,pump))
for duration in(0,1450):h.stalled(duration,100,'zero-duration/frozen-clock prefix '+str(duration))
for failure in(1,2):
 h.prepare();h.failAllocation=failure;cpu=h.null_page_off()
 try:h.compare(0x4ec050,h.MANAGER,[2,h.DESC],('source allocation failure prefix',failure),fault=failure==1)
 finally:h.null_page_on(cpu)
for descriptor in(0,h.DESC):
 h.prepare();h.put(h.DESC,[2]);h.compare(0x4ec050,h.MANAGER,[2,descriptor],('null/default or mismatched init tag',descriptor))
print('PASS clocks, bounded stalled prefixes, allocation and descriptor failures',flush=True)

for mutation in(1,2,3,4):
 h.prepare();h.compare(0x4ed0b0,h.EFFECT,[h.DESC],('callback mutation init',mutation));h.mutation=mutation
 h.compare(0x4ed1a0,h.EFFECT,[7],('live source RNG receiver fields',mutation));h.mutation=0
 h.compare(0x4ed1a0,h.EFFECT,[11],('retained mutated source field histories',mutation))
 h.mutation=4;h.clockDelta=200;h.compare(0x4ec9c0,h.EFFECT,[1450,0,1],('source verticalblank callback mutates live DD identity',mutation))
for case in('array','cstring'):
 h.prepare(percent=101 if case=='cstring' else 80)
 if case=='array':h.put(h.MANAGER+0x14,[0,0,0])
 h.failAllocation=2 if case=='cstring' else 3;cpu=h.null_page_off()
 try:h.compare(0x4ec050,h.MANAGER,[2,h.DESC],('CArray/diagnostic allocation failure prefix',case),fault=True)
 finally:h.null_page_on(cpu)
import json
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.events,'originalAddresses':len(h.m.executed),'heapBytes':h.SIZE,'globalBytes':0x1c000,'retainedCompletedProfiles':12,'stalledPrefixes':h.prefixCount,'objectBytes':0x7d5c,'objectWords':8023,'boundaries':'DirectDraw lock/unlock/verticalblank +clock;CString atomicdecrement adapter;CRT thread lookup/allocation; no invented eventpump/presentation'}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
