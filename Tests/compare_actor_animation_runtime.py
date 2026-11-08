#!/usr/bin/env python3
"""Complete animation callers using the actual original updater and real ANI."""
import ctypes as C,json,struct
import actor_animation_helpers as g
for i in range(500):
 for f,t in[(0x4c8210,g.ANI),(0x4c8220,g.ANI),(0x4c8260,g.ANI),(0x4c82a0,g.ANI),(0x4c79e0,g.A),(0x4c7a40,g.A),(0x420a10,g.A),(0x4c82a0,g.STANDALONE)]:
  g.setup(g.rng.randrange(1,9));g.policy=i%3
  if i%5==0:g.lookupResult=0
  if i%7==0:g.put(t+8,[0])if t in(g.ANI,g.STANDALONE)else None
  a=g.NAME if f in(0x4c79e0,0x4c7a40)else g.rng.choice([0,g.SEQ])if f in(0x4c8220,0x420a10)else g.rng.choice([0,1])if f==0x4c8260 else g.rng.choice([0,1,16,80,0xffffffff])
  g.compare(f,t,f'{f:x}/{i}',a,g.rng.randrange(2))
# Directed raw fields: exact countdown readiness, reset retention, rate and
# event snapshot boundaries (including arbitrary nonzero timed/stopped words).
for remaining in(0,1,16,17,0xffffffff):
 for timed in(0,1,2,0xffffffff):
  for stopped in(0,1,0x80000000):
   for eager in(0,1):
    g.setup(2);g.put(g.ANI+4,[g.A,g.SEQ,g.RECORDS,0,remaining,timed,stopped,77,88,0x3f800000]);g.put(g.RECORDS,[0x12345678,6,3,0,2,2,0,99,3,5,0xffff,0x100d000]);g.policy=2
    g.compare(0x4c82a0,g.ANI,f'directed/update/{remaining}/{timed}/{stopped}/{eager}',16)
    g.compare(0x4c8260,g.ANI,f'directed/reset/{remaining}/{timed}/{stopped}/{eager}',eager)
# Real Rat/RatBomb files, including zero-duration BOUNCE and GAME_NULL.
files=sorted((g.ROOT/'Original/cd-assets/LEVEL1/ANIS/RAT').glob('*.ANI'))+sorted((g.ROOT/'Original/cd-assets/LEVEL1/ANIS/RATBOMB').glob('*.ANI'))+[g.ROOT/'App/GameData/GAME/ANIS/NULL.ANI']
assets=[];trace=0
for path in files:
 data=path.read_bytes();sig,unused,flags,count,pathLength=struct.unpack_from('<5I',data);assert sig==32 and 0<count<60
 g.setup(count);offset=32+pathLength;zero=0
 imageName=path.parent.name if path.parent.name in('RAT','RATBOMB')else 'RAT'
 imageFiles=list((g.ROOT/'Original/cd-assets/LEVEL1/IMAGES'/imageName).glob('FRAME*.PID'))
 imageIDs=sorted(int(p.stem[5:])for p in imageFiles);first,last=min(imageIDs),max(imageIDs);table=[0]*(last+1)
 for imageID in imageIDs:table[imageID]=0x100d000+imageID*0x20
 g.put(g.IM+0x64,[first,last]);g.put(g.IMAGES,table);g.put(g.A+0x16c,[first]);g.put(g.A+0x174,[table[first]])
 for index in range(count):
  flags=struct.unpack_from('<H',data,offset)[0];event=0x100d000+index*0x20 if flags&2 else 0;offset+=g.decode(data[offset:],event,index);zero+=int(g.words(g.RECORDS+index*0x40+24,1)[0]==0)
 assert offset==len(data)
 g.compare(0x420a10,g.A,f'{path.name}/select',g.SEQ,0)
 for tick in range(220):
  if tick%53==0:g.compare(0x4c8260,g.ANI,f'{path.name}/reset/{tick}',tick%2)
  # Externally tuning rate/timed/stop are direct original field inputs.
  if tick%37==0:g.put(g.ANI+40,[g.rates[tick%len(g.rates)]])
  g.compare(0x4c82a0,g.ANI,f'{path.name}/step/{tick}',[0,1,16,33,80,500,0xffffffff][tick%7]);trace+=1
 assets.append({'file':str(path.relative_to(g.ROOT)),'records':count,'zeroDurationRecords':zero,'imageSetFixture':imageName,'actualImageIDs':imageIDs})
assert any(x['file'].endswith('BOUNCE.ANI')and x['zeroDurationRecords']for x in assets)
assert any(x['file'].endswith('NULL.ANI')and x['zeroDurationRecords']for x in assets)
# Explicit native-only bounded rejection, never compare invalid original deref.
g.setup(1);g.put(g.ANI+4,[g.A,g.SEQ,g.RECORDS,0,0,0,0,1,1,0x3f800000]);g.put(g.RECORDS+44,[0x100d000]);g.policy=3
fault=C.c_uint32();result=C.c_uint32();assert g.lib.claw_actor_animation_entry(0x4c82a0,g.ANI,16,0,C.byref(g.globals),g.host,C.byref(fault),C.byref(result))==1 and fault.value==3
report={'calls':g.calls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'originalDecodedRecords':g.decodes,'actualANI':assets,'retainedActualFileSteps':trace,'rawHeapBytesCompared':g.SIZE}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='actualANI'}))
