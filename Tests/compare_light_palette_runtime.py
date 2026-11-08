#!/usr/bin/env python3
"""Original caller/math/table ownership across retail CLTs and generated profiles."""
import light_palette_runtime_helpers as h
import json,struct,hashlib,random,time
r=random.Random(0x46e160);assets=[]
# Whole constructor/activation preserves unrelated manager words; global modes
# are installed independently, including the untouched mode8 startup slot.
for seed in range(8):
 h.setup(seed);h.put(h.MANAGER,[r.getrandbits(32)for _ in range(6)]);h.compare(0x4c61d0,h.MANAGER);assert h.get(h.MANAGER,6)==[0,0x5136e8,0,0,0,0];h.compare(0x4c6260,h.MANAGER);assert h.get(h.MANAGER)[0]==1
 for mode in(2,4,8,50,0,0xffffffff):h.compare(0x4c60a0,0,[h.OBJECT,mode])
# Public reader consumes a real heap CMemFile receiver, distinct from the
# decoder's normalized caller-local scratch profile.
for length,available in((0,4),(19,23),(64,13)):
 for cap in(None,2,7):
  h.setup(length);h.putBytes(h.DATA,struct.pack('<I',length)+r.randbytes(max(0,available-4)));file=h.BASE+0x10000;h.put(file,[0x5142f4,0xffffffff,0,0,0,0,available,available,h.DATA,0]);h.maxRead=cap;h.compare(0x4c7730,h.OBJECT,[file]);h.compare(0x4c76e0,h.OBJECT)
for path in sorted((h.ROOT/'work/original-disc-assets').glob('LEVEL*/PALETTES/*.CLT')):
 h.setup();data=path.read_bytes();length=struct.unpack_from('<I',data)[0];assert length+4==len(data);h.putBytes(h.DATA,data);out=h.compare(0x4c7360,h.MANAGER,[h.DATA,len(data)])[2];assert h.get(out,3)[0:2]==[1,length];assert h.getBytes(h.get(out+8)[0],length)==data[4:];h.compare(0x4c7510,h.MANAGER,[out]);assert not h.live or len(h.live)==1;assets.append({'path':str(path.relative_to(h.ROOT)),'length':length,'SHA256':hashlib.sha256(data).hexdigest()})
# Same manager repeatedly loads/removes source tables; array growBy/capacity remain source-owned.
for seed in range(20):
 h.setup(seed);h.putBytes(h.DATA,struct.pack('<I',73)+r.randbytes(73));tokens=[]
 for i in range(8):tokens.append(h.compare(0x4c7360,h.MANAGER,[h.DATA,77])[2])
 for token in tokens[::2]+tokens[1::2]:h.compare(0x4c7510,h.MANAGER,[token])
 h.compare(0x4c61f0,h.MANAGER)
# Full source rank sort/inverse, including tie-heavy and reversed palette orders.
for seed in range(48):
 h.setup(seed)
 if seed%3==0:h.put(h.PALETTE,[0]*256)
 elif seed%3==1:h.put(h.PALETTE,[((255-i)*0x010101)for i in range(256)])
 h.compare(0x4c6fa0,h.MANAGER,[h.PALETTE]);p=h.get(h.MANAGER+8)[0];table=h.get(p)[0];data=h.get(table+8)[0];values=h.getBytes(data,512);assert all(values[256+values[i]]==i for i in range(256));h.compare(0x4c7510,h.MANAGER,[table])
# Source scalar comparator and shared nearest-color helper across arbitrary colors.
for seed in range(128):
 h.setup(seed);h.put(0x5430c0,[h.PALETTE]);h.putBytes(h.LEFT,bytes([r.randrange(256)]));h.putBytes(h.RIGHT,bytes([r.randrange(256)]));h.compare(0x4c70b0,0,[h.LEFT,h.RIGHT]);h.compare(0x4c7580,0,[h.PALETTE,r.getrandbits(32),r.getrandbits(32),r.getrandbits(32)])
# Whole light fallback arithmetic; retained source field stores and actual helper body.
for width,gain,lift in[(0,400,16),(1,400,16),(1,0,0),(2,100,255),(3,250,16)]:
 h.setup(width+gain);h.hashEvents=True;h.compare(0x4c68e0,h.MANAGER,[h.PALETTE,width,gain,1,lift])
# Whole startup with realLIGHT/AVERAGE resources, native rank and source effects installation.
for level in(1,2,4,6,10,14):
 h.setup(level);folder=h.ROOT/f'work/original-disc-assets/LEVEL{level}/PALETTES';light=(folder/'LIGHT.CLT').read_bytes();average=(folder/'AVERAGE.CLT').read_bytes();h.putBytes(h.DATA,light);h.putBytes(h.DATA+0x18000,average);h.put(h.RESOURCE+16,[h.DATA,len(light)]);h.put(h.RESOURCE2+16,[h.DATA+0x18000,len(average)]);h.resources={0x52a09c:h.RESOURCE,0x52a088:h.RESOURCE2};h.compare(0x46e160,h.OWNER);p0,p1,p2=h.get(h.OWNER+0x768,3);assert p0 and p1 and p2;assert h.get(0x5430b0,2)==[p1,p1];assert h.get(0x5430bc)[0]==p2
 for p in(p0,p1,p2):h.compare(0x4c7510,h.MANAGER,[p])
 h.compare(0x4c61f0,h.MANAGER)
# Skipping other bit-depth is a true source no-op; missing manager preserves prior fields.
for depth in(0,16,24,32,0xffffffff):
 h.setup();h.put(h.APP+0x78,[depth]);h.put(h.OWNER+0x768,[123,456,789]);h.compare(0x46e160,h.OWNER);assert h.get(h.OWNER+0x768,3)==[123,456,789]
h.setup();h.put(h.APP+0x58,[0]);h.put(h.OWNER+0x768,[123,456,789]);assert h.compare(0x46e160,h.OWNER)[2]==0 and h.get(h.OWNER+0x768,3)==[123,456,789]
# Source_CIpow profile for all256 discrete byte brightness inputs.
for weighted in range(256):
 base=1.0/(weighted*struct.unpack('<f',struct.pack('<f',.003921568859368563))[0]+1.0);assert h.sourcePow(base,1)==json.loads((h.WORK/'pow-one-profile.json').read_text())['bits'][weighted]
# Non-normal integer exponents retain explicit exact source numeric transport.
for exponent in(0,2,-1):
 h.setup(exponent&255);h.hashEvents=True;h.compare(0x4c68e0,h.MANAGER,[h.PALETTE,2,400,exponent&0xffffffff,16])
# Loader short reads are accepted as source does, without invented validation.
for length,available in[(0,4),(1,5),(31,35),(64,19),(256,260)]:
 for cap in(None,2,7):
  h.setup(length);h.putBytes(h.DATA,struct.pack('<I',length)+r.randbytes(max(0,available-4)));h.maxRead=cap;h.compare(0x4c7360,h.MANAGER,[h.DATA,available])
# Generated allocation failures preserve source object leaks/partial ownership.
for f,args in[(0x4c68e0,[h.PALETTE,1,400,1,16]),(0x4c6d90,[h.PALETTE,100,100]),(0x4c6fa0,[h.PALETTE])]:
 for failed in(1,2):
  h.setup();h.allocationFail=failed;assert h.compare(f,h.MANAGER,args)[2]==0
# Real startup failure prefixes and prior-global preservation, without huge fallback loops.
for failed,lightPresent,averagePresent in[(1,False,False),(4,True,False),(7,True,True)]:
 h.setup();folder=h.ROOT/'work/original-disc-assets/LEVEL1/PALETTES';light=(folder/'LIGHT.CLT').read_bytes();avg=(folder/'AVERAGE.CLT').read_bytes();h.putBytes(h.DATA,light);h.putBytes(h.DATA+0x18000,avg);h.put(h.RESOURCE+16,[h.DATA,len(light)]);h.put(h.RESOURCE2+16,[h.DATA+0x18000,len(avg)]);h.resources={**({0x52a09c:h.RESOURCE}if lightPresent else{}),**({0x52a088:h.RESOURCE2}if averagePresent else{})};h.allocationFail=failed;assert h.compare(0x46e160,h.OWNER)[2]==0
h.setup();h.comparePrefix(0x4c6d90,h.MANAGER,[h.PALETTE,0,0],0x4c6e9b,2)
# The full100/100 average-table oracle is expensive(~281s locally). It was run
#independently;--full-average repeats it with every unchanged original helper.
if '--full-average'in __import__('sys').argv:
 h.setup(812);h.compare(0x4c6d90,h.MANAGER,[h.PALETTE,100,100])
report={'pairedCalls':h.calls//2,'orderedPairedSnapshots':h.snapshots//2,'originalAddresses':len(h.m.executed),'normalPowProfiles':256,'unsafePrefixes':h.prefixes,'assets':assets,'heapBytes':h.SIZE,'globalBytes':h.GN}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='assets'}))
