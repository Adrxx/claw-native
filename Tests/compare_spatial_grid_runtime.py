#!/usr/bin/env python3
"""Full original spatial construction, residency, activation and ownership."""
import json
import struct,zlib
import spatial_grid_helpers as g
for i in range(100):
 for fn,args in[(0x4cb040,(g.rng.getrandbits(32),g.rng.getrandbits(32))),(0x4cb0e0,(g.RECT,))]:
  g.reset();g.compare(fn,g.WORLD,f'world-defaults/{fn:x}/{i}',args)
for offset in range(0,40,4):
 g.reset();g.put(g.WORLD,list(range(1,13)));g.compare(0x4cb0e0,g.WORLD,f'viewport-alias/{offset}',(g.WORLD+offset,))
for i in range(20):
 g.reset();g.policy=5;g.compare(0x4d1620,g.PLANE,f'captured-before-allocation/{i}',(g.RECORD,i%4))
# Constructor log/pow original instruction outputs across powers and neighbors.
for n in(1,2,3,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129,255,256,257,511,512,513,1023,1024):
 g.reset();g.compare(0x4f4490,g.LAYERS[0],f'constructor/{n}',(0,0,31,23,n,n))
for i in range(50):
 g.reset();g.compare(0x4d4890,g.GRID,f'grid-ctor/{i}',(g.CONTAINER,g.RECT,*[g.PAIRS+j*8 for j in range(6)]))
for i in range(100):
 for fn,t,args,ret in[(0x4d1620,g.PLANE,(g.RECORD,i%5),True),(0x4d2050,g.PLANE,(),False),(0x4d4b00,g.GRID,(),False),(0x4d4a90,g.LAYERS[0],(i%2,),True),(0x4f45f0,g.LAYERS[0],(),False)]:
  g.reset();g.policy=i%5;g.compare(fn,t,f'lifecycle/{fn:x}/{i}',args,ret)
for i in range(150):
 g.reset();g.policy=i%4
 for j,actor in enumerate(g.ACTORS[:8]):
  flags=0x40000|[0,0x800000,0x1000000][j%3];g.put(actor+8,[flags]);g.nativeEntry(0x4d51a0,g.GRID,(actor,))
 x=g.rng.randrange(-400,1500)&0xffffffff;y=g.rng.randrange(-400,1200)&0xffffffff
 g.compare(0x4d4b50,g.GRID,f'activate/{i}',(x,y))
 g.compare(0x4d4b50,g.GRID,f'activate-cache/{i}',(x,y))
 g.compare(0x4d4d10,g.GRID,f'residency/{i}',(g.rng.randrange(2000),g.rng.randrange(1400)))
# Complete rectangle-query body: remove/no-remove, inclusive edges, reversed
# endpoints, cell-head/tail removal, ordered activation through explicit
# polymorphic override (so the no-remove path does not duplicate scene nodes).
for i in range(180):
 g.reset()
 for l in g.LAYERS:g.put(l,[g.VT])
 for j,a in enumerate(g.ACTORS[:10]):
  g.put(a+0x98,[g.rng.randrange(1024),g.rng.randrange(768)]);g.nativeEntry(0x4f4630,g.LAYERS[j%3],(a+0x88,))
 bounds=[g.rng.randrange(-500,1500)&0xffffffff for _ in range(4)]
 if i%3==0:bounds=[0,0,1023,767]
 g.compare(0x4f46b0,g.LAYERS[i%3],f'query/{i}',(*bounds,i%2))
for i in range(150):
 g.reset()
 for j,a in enumerate(g.ACTORS[:6]):
  g.put(a+8,[[0,0x800000,0x1000000,0x1800000][(i+j)%4]]);g.put(a+0x98,[g.rng.randrange(1024),g.rng.randrange(768)])
  g.compare(0x4d51a0,g.GRID,f'register-actor/{i}/{j}',(a,),False)
 g.reset()
 for j,a in enumerate(g.ACTORS[:6]):
  g.put(a+0x98,[100,100]);g.compare(0x4f4630,g.LAYERS[0],f'register-member/{i}/{j}',(a+0x88,))
 g.compare(0x4f4680,g.LAYERS[0],f'remove-member/{i}',(g.ACTORS[i%6]+0x88,),False)
# Flags, callback state restoration, saved next nodes, deletion and pool cleanup.
for flags in(0,2,0x40000,0x40002,0x40020,0xc0020,0x140000,0x840000,0x1840000,0x8c0020,0x1040020,0x40,0x80040):
 for policy in(0,1,2,3):
  for center in((400,300),(1023,767),(1500,1000),(-321,-221)):
   g.reset();g.policy=policy
   for i,a in enumerate(g.ACTORS[:3]):g.put(a+8,[flags]);g.put(a+0x4c,[0 if i==0 else 1023 if i==1 else 1300,767]);g.insert(a)
   g.compare(0x4d4d10,g.GRID,f'flags/{flags:x}/{policy}/{center}',tuple(v&0xffffffff for v in center))
# Original legitimate negative count skips record loop; allocation failures at
# each constructor allocation, preserving already-allocated objects/words.
for fn,t,args in[(0x4d4890,g.GRID,(g.CONTAINER,g.RECT,*[g.PAIRS+j*8 for j in range(6)])),(0x4f4490,g.LAYERS[0],(0,0,63,63,128,128)),(0x4d1620,g.PLANE,(g.RECORD,0xffffffff))]:
 g.reset();g.compare(fn,t,f'negative-or-success/{fn:x}',args)
 for failure in range(1,7 if fn==0x4d4890 else 2 if fn==0x4f4490 else 8):
  if fn==0x4d1620 and failure==1:continue # original dereferences null grid
  g.reset();g.failAllocation=failure;g.compare(fn,t,f'alloc-fail/{fn:x}/{failure}',args)
# Original startup always-active extraction and dormant destructor walk.
for i in range(120):
 for fn,t in[(0x4d2030,g.PLANE),(0x4d4c40,g.GRID),(0x4d50e0,g.GRID)]:
  g.reset();g.policy=i%4
  for j,a in enumerate(g.ACTORS[:10]):
   g.put(a+8,[0x40000|([0,0x800000,0x1000000][j%3])|(2 if (i+j)%3==0 else 0)]);g.put(g.LOGICS[j]+8,[4 if (i+j)%4==0 else 0]);g.nativeEntry(0x4d51a0,g.GRID,(a,))
  g.compare(fn,t,f'startup-or-dormant-delete/{fn:x}/{i}')
ITERATOR=g.BASE+0x11440
for i in range(80):
 g.reset()
 for j,a in enumerate(g.ACTORS[:10]):g.nativeEntry(0x4f4630,g.LAYERS[0],(a+0x88,))
 if i%2:g.compare(0x4f48a0,ITERATOR,f'iterator-range/{i}',(g.LAYERS[0],0,0,1023,767,i%3==0))
 else:g.compare(0x4f4860,ITERATOR,f'iterator-all/{i}',(g.LAYERS[0],i%3==0))
 for j in range(11):g.compare(0x4f49c0,ITERATOR,f'iterator-next/{i}/{j}')
for bits in(0,0x80000000,0x3f800000,0x3fffffff,0x4effffff,0x4f000000,0xcf000000,0x7f800000,0xff800000,0x7fc00000,0x5f000000):
 for fn in(0x4d1fd0,0x4d2000):
  g.reset();g.put(g.PLANE+0x10,[bits,bits]);g.compare(fn,g.PLANE,f'wrapper-ftol/{fn:x}/{bits:x}')
# Confirm the original iterator's actual nonadvancing branch, without treating
# its instruction-bound stop as a normal return or inventing filtered parity.
g.reset();g.nativeEntry(0x4f4630,g.LAYERS[0],(g.ACTORS[0]+0x88,));before=bytes(g.heap);args=(g.LAYERS[0],110,110,120,120,0);fault=g.C.c_uint32();result=g.C.c_uint32();request=g.Args((g.C.c_uint32*8)(*args),len(args));assert g.lib.claw_spatial_grid_entry(0x4f48a0,ITERATOR,request,g.host,g.C.byref(fault),g.C.byref(result))and fault.value==2
g.native=False;g.u.mem_write(g.BASE,before);g.m.write_words(0,[0x12345678])
try:g.m.call(0x4f48a0,ITERATOR,struct.pack('<6I',*args));raise AssertionError('original nonmatching iterator unexpectedly returned')
except AssertionError as error:assert str(error)=='Original routine exceeded instruction bound'
assert 0x4f4a26<=g.u.reg_read(g.UC_X86_REG_EIP)<=0x4f4a50;g.native=True
# Full original generic actor/primary deleting bodies, composed with frozen
# ActorDestruction, rather than the earlier deliberate polymorphic adapters.
destructionChains=0
for i in range(80):
 g.reset();g.fullDestruction=True
 for j,a in enumerate(g.ACTORS[:6]):
  g.put(g.LOGICS[j],[0x513740]);g.put(a+8,[0xc0040 if i%2 else 0x80040]);g.insert(a)
 g.compare(0x4d4d10,g.GRID,f'full-deleting-residency/{i}',(1500,1000));destructionChains+=1
 g.reset();g.fullDestruction=True
 for j,a in enumerate(g.ACTORS[:9]):g.put(g.LOGICS[j],[0x513740]);g.put(a+8,[0x40000|[0,0x800000,0x1000000][j%3]]);g.nativeEntry(0x4d51a0,g.GRID,(a,))
 g.compare(0x4d50e0,g.GRID,f'full-dormant-destruction/{i}');g.compare(0x4d4b00,g.GRID,f'retained-grid-free/{i}',returns=False);destructionChains+=1
# Actual default world constructor witness (not a port of whole world startup).
g.reset();g.u.mem_write(g.BASE,bytes(g.heap));g.m.write_words(0,[0x12345678]);g.native=False;g.m.call(0x4cace0,g.WORLD,g.struct.pack('<3I',g.PAR,123,456));assert g.words(g.WORLD+0xb0,12)==[500,250,1000,1000,250,125,1600,1200,2560,1920,768,576];g.native=True
joined=0
for delta in(0,1,18,19,35,36,37,99):
 for step in range(6):
  g.prepareFrame();g.stage.stage.deltaMilliseconds=delta;g.clockValue=1000;g.cameraGlobals.stageDelta=delta;g.compareFrame(0x46ad70 if 18<delta<100 else 0x46ace0,f'joined/{delta}/{step}');joined+=1
retained=0
for history in range(8):
 g.prepareFrame()
 for step in range(16):
  delta=[16,19,35,18,37,1,99,100][step%8];g.stage.stage.nowMilliseconds+=delta;g.stage.stage.deltaMilliseconds=delta;g.stage.accumulatedMilliseconds+=delta;g.clockValue=g.stage.stage.nowMilliseconds;g.cameraGlobals.stageDelta=delta
  g.put(g.PLAYER+0x4c,[100+step*130,100+step*40]);g.put(g.PLAYER+0xcc,[8 if step%3==0 else 1]);g.compareFrame(0x46ad70 if 18<delta<100 else 0x46ace0,f'retained/{history}/{step}');retained+=1
# Actual CD Level1 Rat/Officer raw records populate the already recovered
# generic loader. Resource bodies and named gameplay callbacks are explicit
# adapters here; grid bodies, list membership and residency writes are real.
raw=(g.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();planes,offset=struct.unpack_from('<2I',raw,732)
if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
records=[]
for plane in range(planes):
 base=offset+160*plane;count=struct.unpack_from('<I',raw,base+128)[0];pos=struct.unpack_from('<I',raw,base+140)[0]
 for _ in range(count):
  w=struct.unpack_from('<71I',raw,pos);length=284+sum(w[1:5]);name=raw[pos+284+w[1]:pos+284+w[1]+w[2]].split(b'\0')[0]
  if name in(b'Rat',b'Officer'):records.append(raw[pos:pos+length])
  pos+=length
assert len(records)==38
actualCalls=0;activatedProfiles=set()
for start in range(0,len(records),12):
 g.reset();g.nativeEntry(0x4cb040,g.WORLD,(640,480));g.put(g.PLANE+0x30,[24576,6144]);g.put(g.PLANE+0xb0,[0]);g.compare(0x4d1620,g.PLANE,f'actual-Level1-grid-construction/{start}',(g.RECORD,0));grid=g.words(g.PLANE+0xb0,1)[0];cellCounts=[g.words(layer+0x1c,1)[0]for layer in g.words(grid+4,3)];assert cellCounts==[4608,576,18432]
 for i,data in enumerate(records[start:start+12]):g.sourceProfile(data,i)
 count=len(records[start:start+12])
 for step in range(24):
  center=g.words(g.ACTORS[step%count]+0x4c,2);g.put(g.PLANE+0x10,[g.fb(float(center[0])+.9),g.fb(float(center[1])+.9)]);g.compare(0x4d1fd0,g.PLANE,f'Level1/activate/{start}/{step}')
  at=g.words(g.CONTAINER+20,1)[0]
  while at:
   node=g.words(at,3);activatedProfiles.add(start+g.ACTORS.index(node[2]));at=node[0]
  # Opposite in-world center returns out-of-range actors to their real cells.
  far=[24575 if center[0]<12288 else 0,6143 if center[1]<3072 else 0];g.put(g.PLANE+0x10,[g.fb(float(far[0])),g.fb(float(far[1]))]);g.compare(0x4d2000,g.PLANE,f'Level1/residency/{start}/{step}');actualCalls+=2
assert len(activatedProfiles)==38
report={'calls':g.calls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'rawHeapBytes':g.SIZE,'joinedNormalSubstepFrames':joined,'retainedNormalSubstepFrames':retained,'originalWorldDefaultsWitness':True,'actualLevel1RatOfficerRecords':len(records),'actualLevel1ProfilesActivated':len(activatedProfiles),'retainedActualLevel1SpatialCalls':actualCalls,'fullGenericDestructionChains':destructionChains,'actualLevel1CellCounts':cellCounts,'originalNonmatchingIteratorNonterminationWitness':True}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
