#!/usr/bin/env python3
"""Original plane constructors/loaders, arithmetic, full heaps and histories."""
import json,struct,random
import world_plane_helpers as t
from world_plane_assets import worlds
rng=random.Random(5331);directed=0
for seed in range(80):
 t.prepare(seed);t.compare('construct',('constructor preserves seeded words',seed),t.PLANE,t.SCENE,rng.getrandbits(32),rng.getrandbits(32))
 for width,height in[(0,0),(1,3),(48,32),(63,128),(64,96),(0x80000000,0xffffffff),(0x7fffffff,0x40000001)]:
  t.put(t.PLANE+0x28,[rng.getrandbits(32),rng.getrandbits(32)]);t.compare('tile_size',('width-based shifts/wrapped extents',seed,width,height),t.PLANE,width,height);directed+=1
for flags in(0,1,4,8,12,16,17,20,24,28,0x40000):
 for percent in(-0x80000000,-301,-1,0,1,37,45,99,100,101,0x7fffffff):
  w=t.prepare(flags^percent);w[2]=flags;w[28:30]=[percent,-percent if percent!=-0x80000000 else percent];w[26:28]=[701,-993];t.put(t.RECORD,w);t.write(t.RECORD+16,b'PlaneName\0')
  # Large wrapped centers must stay inside the frozen clamp's bounded loop
  # profile. Bit1/nonwrap preserve the extreme factor arithmetic independently.
  if abs(percent)>1000:w[26:28]=[0,0];t.put(t.RECORD+0x68,[0,0])
  t.compare('load',('flags/factors/initial centers',flags,percent),t.PLANE,t.RECORD,t.WORLD_BASE,t.RECT);directed+=1
for policy in(0,1,2,3):
 for seed in range(18):
  w=t.prepare(seed);t.policy=policy;w[2]=seed%2;w[30]=rng.getrandbits(32);w[36]=rng.getrandbits(32);t.put(t.RECORD,w);t.write(t.RECORD+16,b'Mutable resource history\0')
  if seed%3==0:t.put(t.RECT,[0x80000000,0,639,479]);t.put(t.WORLD+0x10,[0x80000000,0,639,479]);t.put(t.PLANE+0x70,[640,480,320,240])
  if seed%3==1:t.put(t.RECT,[31,47,348,285]);t.put(t.WORLD+0x10,[31,47,348,285])
  t.compare('load',('services/sentinel/nonorigin/failure',policy,seed),t.PLANE,t.RECORD,t.WORLD_BASE,t.RECT);directed+=1
  t.compare('add',('world append and selected main',policy,seed),t.WORLD,t.RECORD,t.WORLD_BASE,0xabcdef12);directed+=1
for seed in range(12):
 t.prepare(seed);t.put(t.RECORD,[rng.randrange(160)]);assert t.compare('load','invalid header',t.PLANE,t.RECORD,t.WORLD_BASE,t.RECT)==0
 assert t.compare('add','invalid header deleting-destructor boundary',t.WORLD,t.RECORD,t.WORLD_BASE,seed)==0;directed+=2
# Name scanning treats each byte as signed, accepts0x30..0x7f and skips
# punctuation/non-ASCII before strings. Lookup output and CArray insertions
# are explicit fixtures and their full ordered states are compared.
for data,count in[(b'!@ 0FIRST\0/SECOND\0',2),(b'\x80\xff!!A_B\0',1),(b'\0\0\0',3),(b'ABCDE\0\0',2),(b'A\x7fB\0',1)]:
 t.prepare();t.put(t.RECORD+0x7c,[count]);t.write(t.WORLD_BASE+0x200,data);t.compare('load',('signed image-set scanning',data),t.PLANE,t.RECORD,t.WORLD_BASE,t.RECT);directed+=1
actual_worlds=worlds();profiles=[];actual_planes=0;tile_words=0
for path,raw,count,start,digest in actual_worlds:
 t.prepare(int(path.split('/')[0][5:]));t.write(t.WORLD_BASE,raw);tokens=[]
 for index in range(count):
  record=t.WORLD_BASE+start+index*160;words=struct.unpack_from('<40I',raw,start+index*160)
  token=t.compare('add',('actual original world plane',path,index),t.WORLD,record,t.WORLD_BASE,0);assert token;tokens.append(token);actual_planes+=1;tile_words+=words[24]*words[25]
  p=t.get(token,86)
  assert p[2]==words[2]and p[0x80//4]==words[36]and p[0x144//4]==words[30]
  profiles.append({'world':path,'payloadSHA256':digest,'index':index,'recordFlags':words[2],'movementPercent':[struct.unpack('<i',struct.pack('<I',x))[0]for x in words[28:30]],'tileGeometry':list(words[22:26]),'z':struct.unpack('<i',struct.pack('<I',words[36]))[0],'factorBits':[hex(p[6]),hex(p[7])],'runtimeExtents':p[12:14],'initialCenters':[hex(p[4]),hex(p[5])]})
 main=[i for i in range(count)if struct.unpack_from('<I',raw,start+i*160+8)[0]&1][-1]
 assert t.get(t.WORLD+0x3c)[0]==count and t.get(t.WORLD+0x5c,2)==[tokens[main],main]
# Last flags1 entry wins without sorting by z; actual insertion order is retained.
t.prepare(9)
for i,flags in enumerate((1,0,1,4,1)):
 t.put(t.RECORD+8,[flags]);t.put(t.RECORD+0x90,[100-i]);token=t.compare('add',('retained main overwrite/order',i),t.WORLD,t.RECORD,t.WORLD_BASE,0)
 if flags&1:assert t.get(t.WORLD+0x5c,2)==[token,i]
assert t.get(t.WORLD+0x3c)[0]==5
report={'completeOperations':t.calls,'orderedCompleteSnapshots':t.events,'rawHeapBytes':t.SIZE,'originalAddresses':len(t.m.executed),'directedCases':directed,'actualWorlds':len(actual_worlds),'actualPlanes':actual_planes,'actualTileWords':tile_words,'scope':'Whole4d03b0/4d0450/4d0cd0/4cb7b0 with real frozen4d0a60. Image lookup/CArray insertion/grid object initialization/deleting destructor/CopyRect and REZ+decompression remain declared adapters.'}
(t.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');(t.WORK/'actual-world-plane-profiles.json').write_text(json.dumps(profiles,indent=2)+'\n');print(json.dumps(report),flush=True)
