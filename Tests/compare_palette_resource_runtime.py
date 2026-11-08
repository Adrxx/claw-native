#!/usr/bin/env python3
import palette_resource_runtime_helpers as h
import json,hashlib,random,struct
r=random.Random(0x4d6620);assets=[];prefixes=0
for path in sorted((h.ROOT/'work/original-disc-assets').glob('LEVEL*/PALETTES/MAIN.PAL')):
 data=path.read_bytes();assert len(data)==768
 for flags in(0,1):
  h.setup(flags);h.putBytes(h.DATA,data);p=h.compare(0x4d4420,h.MANAGER,[h.RESOURCE,0,flags])[2];assert p;h.put(h.OWNER+44,[p]);backend=h.get(p+16)[0];base=h.getBytes(h.get(backend+12)[0],1024)
  if not flags:assert base==b''.join(data[i:i+3]+b'\0'for i in range(0,768,3))
  h.compare(0x46afe9,h.OWNER);assert h.getBytes(h.OWNER+0x360,1024)==h.physical[h.get(backend+4)[0]];h.compare(0x4bb870,backend);h.compare(0x4d6690,p);h.compare(0x4d47f0,p,[1]);assert not h.get(h.BACKEND+0x3d4+12)[0]
 for prefixLength in(0,7,32,257):
  h.setup(prefixLength);blob=r.randbytes(prefixLength)+data;h.putBytes(h.DATA,blob);h.compare(0x4d6620,h.OBJECT,[h.DATA,len(blob),0]);backend=h.get(h.OBJECT+16)[0];assert h.getBytes(h.get(backend+12)[0],1024)==b''.join(data[i:i+3]+b'\0'for i in range(0,768,3));h.compare(0x4d6670,h.OBJECT)
 assets.append({'path':str(path.relative_to(h.ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
print('PASS both whole source PAL routes/all14actualassets/physicalGetEntries/prefixsizes/lifecycle',flush=True)
#Source shortsize clean failure and complete failure cleanup/no inventedCOMRelease.
for size in(0,1,255,767):
 h.setup(size);assert h.compare(0x4d6620,h.OBJECT,[h.DATA,size,0])[2]==0;assert not h.get(h.OBJECT+16)[0]
for root,args in((0x4d4420,[h.RESOURCE,0,0]),(0x4d44f0,[h.DATA,h.NAME,0]),(0x4d6620,[h.DATA,768,0])):
 for failure in(1,0xffffffff):
  h.setup();h.hrCreate=failure;assert h.compare(root,h.MANAGER if root!=0x4d6620 else h.OBJECT,args)[2]==0;assert not h.live
h.setup();h.lockValue=0;assert h.compare(0x4d4420,h.MANAGER,[h.RESOURCE,0,0])[2]==0;assert not h.allocCount
for failed in(1,2):
 h.setup();h.allocationFail=failed;h.comparePrefix(0x4bcac0,h.BACKEND,[h.DATA,0x44],0x4bb115 if failed==1 else 0x4bb120,1);prefixes+=1
h.setup();h.allocationFail=3;p=h.compare(0x4bcac0,h.BACKEND,[h.DATA,0x44])[2];assert p and h.get(p+16)[0]==0;h.compare(0x4bb870,p);assert h.get(p+16)[0]
h.setup();h.allocationFail=1;h.comparePrefix(0x4d4420,h.MANAGER,[h.RESOURCE,0,0],0x4d4474,1);prefixes+=1
h.setup();h.putBytes(h.NAME,b'A'*80+b'\0');h.comparePrefix(0x4d4420,h.MANAGER,[h.RESOURCE,0,0],0x4d44c5,2);prefixes+=1
#All rawentry roots preserve existingbackend seed words7..10 and resourcealiases.
for f,args in((0x4bcb40,[h.QUAD,0x44]),(0x4bcac0,[h.DATA,0x44]),(0x4bcbc0,[h.DATA,768,0x44]),(0x4d44f0,[h.DATA,h.NAME,0]),(0x4d4570,[h.NAME,h.NAME,0])):
 h.setup()
 if f==0x4d4570:
  #Whole wrapper with explicit unrecovered file-loader callee; no claim of
  #file format/backend reconstruction from a callback adapter.
  p=h.compare(0x4bcac0,h.BACKEND,[h.DATA,0x44])[2];h.put(h.MAPSLOT+4,[p]);h.compare(f,h.MANAGER,args)
 else:h.compare(f,h.MANAGER if f==0x4d44f0 else h.BACKEND,args)
#Retained manager/list pools across25 resource allocations and mixeddestruction.
for seed in range(12):
 h.setup(seed);objects=[]
 for i in range(25):
  h.putBytes(h.DATA,r.randbytes(768));p=h.compare(0x4d4420,h.MANAGER,[h.RESOURCE,h.NAME,0])[2];objects.append(p)
 for p in objects[::2]+objects[1::2]:h.compare(0x4d47f0,p,[1])
 assert h.get(h.BACKEND+0x3d4+12)[0]==0
print('PASS heap/list/error/retained ownership and four stoppedunsafe prefixes',flush=True)
#Whole fill/set/get/display and actualphysicalHRESULT/clock trajectories.
for seed in range(90):
 h.setup(seed);h.putBytes(h.QUAD,r.randbytes(1024));p=h.compare(0x4bcb40,h.BACKEND,[h.QUAD,0x44])[2];h.put(h.OBJECT+16,[p]);start=r.randrange(256);count=r.randrange(257-start);hr=[0,1,0xffffffff][seed%3];h.hrSet=hr;h.hrGet=hr;h.hrAssign=hr;h.put(0x541374,[h.HOLDER if seed%2 else 0]);h.compare(0x4bb800,p,[start,count,h.QUAD,0xdeadbeef]);h.compare(0x4bb910,p,[start,count,r.getrandbits(32),r.getrandbits(32),r.getrandbits(32),seed]);h.compare(0x4bb870,p);h.compare(0x4d6690,h.OBJECT);h.put(h.TARGET+24,[16]);assert h.compare(0x4d6690,h.OBJECT)[2]==1
 duration=[0,1,10,11,18,100,256][seed%7];h.clockValues=[0xfffffff0,0xfffffff0,0xfffffff1,0xfffffffa,0,10,100,300,700];h.compare(0x4bb990,p,[start,count,r.getrandbits(32),r.getrandbits(32),r.getrandbits(32),duration]);h.compare(0x4bca10,h.BACKEND,[p])
#Systempalette success/failure DCorder, including explicit uninitializedlocalseed.
for size,reserved in((256,20),(256,0),(256,256),(128,20),(64,8),(0,0)):
 for stage in('success','dc','first','second','set'):
  h.setup();p=h.compare(0x4bcac0,h.BACKEND,[h.DATA,0x44])[2];h.putBytes(h.SCRATCH,r.randbytes(1024));h.capsSize=size;h.capsReserved=reserved
  if stage=='dc':h.dcValue=0
  if stage=='first':h.systemReturns=[0,1]
  if stage=='second':h.systemReturns=[1,0]
  if stage=='set':h.hrSet=1
  h.compare(0x4bbf60,p)
print('PASS wholepalette control/timedclocks/SystemPalette explicitphysicaltransport branches',flush=True)
report={'pairedCalls':h.calls//2,'orderedSnapshots':h.snapshots//2,'originalAddresses':len(h.m.executed-{h.m.stop,*h.services}),'unsafePrefixes':prefixes,'heapBytes':h.SIZE,'globalBytes':h.GN,'assets':assets};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k!='assets'})
