#!/usr/bin/env python3
"""Original raw world file loading, ownership and startup graph oracle."""
import json
import world_file_runtime_helpers as g
actual=recordCoverage=0
for name,data in g.worlds():
 g.reset(data);g.compare(0x4cb200,g.WORLD,[g.RAW],name);actual+=1;recordCoverage+=g.recordCount
 print('PASS',name,'recordCount',g.recordCount,flush=True)
# Complete frozen spatial construction/record-caller composition on actualLevel1.
name,data=g.worlds()[0];g.reset(data);g.ctx.composeSpatial=1;g.compare(0x4cb200,g.WORLD,[g.RAW],name+'/composed-Spatial')
syntheticCalls=0
for i in range(16):
 data=g.synthetic(i,bool(i%2));g.reset(data)
 if i%4==0:g.ctx.arrays=g.C.POINTER(g.ArrayContext)()
 if i%5==0:g.resourceFail=True
 g.compare(0x4cb200,g.WORLD,[g.RAW],f'synthetic/{i}');g.compare(0x4cb5f0 if i%2 else 0x4cb180,g.WORLD,[],f'synthetic-clear/{i}');syntheticCalls+=2
for x,y in ((0,0),(0xffffffff,0xffffffff),(0x7fffffff,0x80000000),(689,4723)):
 data=bytearray(g.synthetic(77,False));g.struct.pack_into('<2I',data,720,x,y);g.reset(bytes(data));g.compare(0x4cb200,g.WORLD,[g.RAW],f'signed-start/{x}/{y}');syntheticCalls+=1
for case in range(5):
 data=bytearray(g.synthetic(8,True));g.reset(bytes(data))
 if case==0:g.allocationFailures=1
 if case==1:g.codecFail=True
 if case==2:g.put(g.RAW,[0x5f5])
 if case==3:
  plain=bytearray(g.synthetic(8,False));g.struct.pack_into('<I',plain,1524,159);g.reset(bytes(plain))
 if case==4:
  plain=bytearray(g.synthetic(8,False));table=g.struct.unpack_from('<I',plain,740)[0];g.struct.pack_into('<I',plain,table+32,4);g.reset(bytes(plain))
 g.compare(0x4cb200,g.WORLD,[g.RAW],f'ordinary-fail/{case}');g.compare(0x4cdd10,g.WORLD,[1],f'failure-delete/{case}');syntheticCalls+=2
for function in (0x4cb470,0x4cb5a0):
 for case in range(3):
  g.reset(g.synthetic(67,True))
  if case==1:g.resourceFail=True
  if case==2:g.allocationFailures=1
  g.compare(function,g.WORLD,[g.FILEFN],f'wrapper/{function:x}/{case}');g.compare(0x4cdd10,g.WORLD,[case],f'wrapper-delete/{function:x}/{case}');syntheticCalls+=2
for seed in range(12):
 g.reset();g.put(g.WORLD,[g.rng.getrandbits(32)for _ in range(56)]);g.compare(0x4cace0,g.WORLD,[g.PARENT,seed,seed*17],f'ctor/{seed}');g.compare(0x4cdd10,g.WORLD,[seed%2],f'ctor-delete/{seed}');syntheticCalls+=2
# Retain the actual native grid graph through reload and complete deletion.
name,data=g.worlds()[0];g.reset(data);g.ctx.composeSpatial=1
for history in range(2):g.compare(0x4cb200,g.WORLD,[g.RAW],f'actual-retained/{history}')
g.compare(0x4cdd10,g.WORLD,[1],'actual-grid-world-delete');syntheticCalls+=3
report={'calls':g.calls,'orderedFullHeapEvents':g.eventCount,'originalImageAddresses':len([a for a in g.m.executed if a<0x1000000]),'rawHeapBytes':g.SIZE,'actualOriginalWorlds':actual,'actualRawRecordCoverage':recordCoverage,'directedAndRetainedCalls':syntheticCalls}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
