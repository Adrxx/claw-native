#!/usr/bin/env python3
"""Whole original tile calls, all shipped records, aliases and raw mask faults."""
import hashlib, json, random, struct
import raw_tile_description_runtime_helpers as g

actualRecords=actualWorlds=0; kinds={}; directed=0
for level,records in g.actualRecords():
 for i,record in enumerate(records):
  g.reset(level*10000+i); t=g.construct(record,f'LEVEL{level}/{i}/factory'); assert t
  kind,_,width,height=struct.unpack_from('<4I',record); kinds[kind]=kinds.get(kind,0)+1
  g.query(0x1c,[],f'LEVEL{level}/{i}/type',t);g.query(0x24,[],f'LEVEL{level}/{i}/advance',t)
  x,y=[(0,0),(width//2,height//2),(width-1,height-1),(-1,-1),(width,height)][i%5]
  attr=g.query(0x20,[x,y],f'LEVEL{level}/{i}/point',t)
  for slot in range(0x28,0x48,4):
   a=[x,y,g.OUT,g.OUT+5] if slot%8==0 else [x,y,attr,g.OUT+5]
   g.query(slot,a,f'LEVEL{level}/{i}/{slot:x}',t)
  g.compare(0x4d5330,t,[1],f'LEVEL{level}/{i}/delete',frozen=True);actualRecords+=1
 actualWorlds+=1;print(f'PASS LEVEL{level}: {len(records)} whole constructor/query/delete histories',flush=True)

# All descriptor fields seeded independently, including signed malformed bounds.
rng=random.Random(0x4d5c80)
for case in range(2000):
 g.reset(case);kind=1 if case%3==0 else 2
 values=[rng.getrandbits(32) for _ in range(9)]; values[0]=0x513980 if kind==1 else 0x5139c8
 if case%2:values[1:3]=[8,12];values[5:9]=[2,3,5,9]
 g.put(g.DESC,values)
 x,y=(rng.getrandbits(32),rng.getrandbits(32)) if case%2==0 else (rng.randrange(-2,12),rng.randrange(-2,16))
 g.query(0x20,[x,y],f'signed/{case}/point')
 for slot in range(0x28,0x48,4):
  out=g.DESC+4*(3+case%6) if case%4==0 else g.OUT+(case%3)
  target=values[3+case%2] if case%2 else rng.getrandbits(32)
  g.query(slot,[x,y,out,out if case%5==0 else g.OUT+8] if slot%8==0 else [x,y,target,out],f'signed/{case}/{slot:x}')
 directed+=1

# Real original type3 construction. Width/height asymmetry comes from original
# shift calculation (height) and equality check (width), not a format guess.
for width,height in [(1,1),(2,3),(4,4),(8,8),(8,12),(16,17),(4,8),(3,3),(8,4)]:
 for mode in range(4):
  g.reset(width*100+height*10+mode)
  mask=bytes([17]*(width*height)) if mode==0 else bytes((x%4 if mode==1 else x//width%4 if mode==2 else x*71)&255 for x in range(width*height))
  t=g.construct(g.rawDescription(3,width,height,mask=mask),f'mask-ctor/{width}/{height}/{mode}')
  if not t:directed+=1;continue
  assert g.words(t+12)[0]==(height.bit_length()-1)
  assert g.query(0x1c,[],f'mask-type/{width}/{height}/{mode}',t)==3
  assert g.query(0x24,[],f'mask-advance/{width}/{height}/{mode}',t)==16+width*height
  for x,y in [(0,0),(width-1,height-1),(width//2,height//2),(-1,0),(width,0),(0,-1),(0,height)]:
   g.query(0x20,[x,y],f'mask/{width}/{height}/{mode}/point/{x}/{y}',t)
   for slot in range(0x28,0x48,4):
    target=(mask[(y*width+x)%(width*height)] if mode%2 else 256)
    g.query(slot,[x,y,g.OUT+1,g.OUT+6] if slot%8==0 else [x,y,target,g.OUT+6],f'mask/{width}/{height}/{mode}/{slot:x}/{x}/{y}',t)
  g.compare(0x4cde70,t,[1],f'mask-delete/{width}/{height}/{mode}',frozen=True);directed+=1

# Shifts are x86 masked to5bits; vertical scan step is width even where its
# value differs from1<<shift. Cancel large signed values in wrapping indexes.
for case in range(700):
 g.reset(case+8000);shift=rng.randrange(0,64);width=rng.randrange(1,33);height=rng.randrange(1,25)
 x,y=(rng.randrange(-2,width+2),rng.randrange(-2,height+2))
 if shift%32>7:y=0
 g.put(g.DESC,[0x513a10,width,height,shift,width*height,g.MASK])
 if case%6==0:g.write(g.MASK-128,bytes([case&255])*8192)
 g.query(0x20,[x,y],f'shift/{case}/point')
 # Large shift vertical moves can still be entirely readable: use y0 here.
 if shift%32>7:y=0
 for slot in range(0x28,0x48,4):
  out=g.MASK+(case%4) if case%3==0 else g.OUT+case%4
  target=[0,255,256,0xffffffff,rng.randrange(256)][case%5]
  g.query(slot,[x,y,out,out if case%7==0 else g.OUT+8] if slot%8==0 else [x,y,target,out],f'shift/{case}/{slot:x}')
 directed+=1

# Nonzero high shifts and huge signed x values can cancel to a readable raw
# index. A one-byte match stops target scans despite the unusual coordinates.
for shift in range(64):
 for y in (1,2,0xffffffff):
  g.reset(shift*100+y%100);g.put(g.DESC,[0x513a10,8,8,shift,64,g.MASK])
  x=(64-((y<<(shift&31))&0xffffffff))&0xffffffff
  g.write(g.MASK+63,bytes([31,41,51]));assert g.query(0x20,[x,y],f'wrapped-shift/{shift}/{y}')==41
  for slot,step in ((0x2c,-1),(0x34,-8),(0x3c,1),(0x44,8)):
   target=g.read(g.MASK+64+step,1)[0]
   g.query(slot,[x,y,target,g.OUT],f'wrapped-shift/{shift}/{y}/{slot:x}')
  directed+=1

# Each rectangular transition rereads the attribute after storing coordinate.
for slot,x,y,candidate in ((0x28,7,3,5),(0x30,3,7,5),(0x38,0,3,2),(0x40,3,0,2)):
 g.reset(slot);g.put(g.DESC,[0x5139c8,8,8,9,77,2,2,5,5])
 assert g.query(slot,[x,y,g.DESC+16,g.OUT],f'alias-rectangle/{slot:x}')==1
 assert g.words(g.OUT)[0]==candidate
 directed+=1

# Coordinate output aliases the mask-token word; successful transition must
# reload that changed token for its attribute output (cached token gives1).
g.reset(3);g.put(g.DESC,[0x513a10,8,8,0,64,g.MASK]);g.write(g.MASK-1,bytes([1,0,77,88]));x=g.MASK+3;y=(-x)&0xffffffff
assert g.query(0x28,[x,y,g.DESC+20,g.OUT],'alias-mask-token')==1
assert g.words(g.DESC+20)[0]==g.MASK+2 and g.words(g.OUT)[0]==77

# Retained chained mask mutations and direction scans; no buffer reset between
# steps, plus shared output pointers and unaligned byte-mask storage.
for chain in range(64):
 g.reset(10000+chain);g.put(g.DESC,[0x513a10,8,12,3,96,g.MASK+1])
 for tick in range(12):
  x,y=(tick*3+chain)%8,(tick+chain)%12
  slot=0x28+4*(tick%8);out=g.MASK+1+(tick*7)%80 if tick%3==0 else g.OUT+tick%4
  g.query(slot,[x,y,out,g.OUT+8] if slot%8==0 else [x,y,(tick*19)&255,out],f'chain/{chain}/{tick}')
  g.query(0x20,[x,y],f'chain/{chain}/{tick}/point')
 directed+=1

# Raw arithmetic has no coordinate clamps. Failures preserve stores completed
# before the actual unmapped access; they are not converted into valid zeros.
g.reset(4);g.put(g.DESC,[0x513a10,8,8,3,64,0x6000000]);g.failure(0x4cdef0,g.DESC,[0,0],'missing-mask-point')
g.failure(0x4d5900,g.DESC,[0,0,g.OUT,g.OUT+4],'transition-initial-read-before-gate')
# Target left scans have no initial mask read atx0, so even invalidmask returns0.
assert g.query(0x2c,[0,0,5,g.OUT],'target-no-initial-read')==0
g.reset(5);g.put(g.DESC,[0x513a10,8,8,0,64,g.MASK]);g.write(g.MASK-1,b'\x01\x00');x=g.MASK+3;y=(-x)&0xffffffff
# First output switches the mask token to readable address, but subsequent raw
# index still selects mapped bytes here. Invalid attribute-output diagnoses
# the original write fault after the coordinate store.
g.failure(0x4d5900,g.DESC,[x,y,g.DESC+20,0x6000000],'partial-coordinate-store')
g.failure(0x4d5ce0,0x6000000,[4,4,0,g.OUT],'missing-rectangle')

# Unsupported entry/slot and wrong ABI args are explicit native diagnostics.
for f,a in [(0xdeadbeef,[]),(0x4cdef0,[]),(0x4cddd0,[1,2])]:
 fault=g.U();result=g.U();assert g.lib.claw_raw_tile_entry(f,g.DESC,g.args(a),g.host,g.C.byref(fault),g.C.byref(result))==0 and fault.value==2
assert g.lib.claw_raw_tile_function(0x513a10,0x18)==0
assert not g.imageWrites,g.imageWrites
assert hashlib.sha256(bytes(g.u.mem_read(g.imageStart,g.imageEnd-g.imageStart+1))).digest()==g.imageBefore
g.replay.close()
report={'completeOriginalCalls':g.calls,'orderedCompleteHeapServiceSnapshots':g.eventCount,'heapBytesPerComparison':g.SIZE,'originalInstructionAddresses':len([a for a in g.m.executed if a<0x1000000]),'originalImageGlobalWrites':len(g.imageWrites),'actualWorlds':actualWorlds,'actualDescriptions':actualRecords,'actualKinds':kinds,'directedSeedProfilesAndChains':directed,'originalFaultComparisons':g.faults,'functionCalls':{hex(f):n for f,n in sorted(g.functions.items())},'exactOriginalStackPopProfiles':len(g.originalSP),'sanitizerReplayCases':g.replayCases,'dependencyAdapters':['4f63ec physical allocation; seeded raw arena','4f6428 physical free; retains readable bytes for oracle']}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
