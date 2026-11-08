#!/usr/bin/env python3
"""Full original Officer snapshots. HumanEnemy bodies remain explicit adapters."""
import ctypes as C,json
import officer_helpers as g
for i in range(250):
 g.policy=i%3;g.resource_mode=i%3;g.random_results=[g.rng.choice([0,1,19,20,32,33,49,50,99,100,0xffffffff,0x80000000]),g.rng.getrandbits(32)]
 for f in(0x462410,0x462ef0,0x463020,0x463120,0x4631e0,0x463310,0x405000,0x462a00,0x462a20,0x462af0):
  s,c=g.fresh();c.damageScale=g.rng.choice([0,0.5,1,1.25,5,-1]);c.healthScale=g.rng.choice([0,0.5,1,1.25,5,-1]);c.rangeScale=g.rng.choice([0,1,1.98,2,10,-1]);c.difficulty=g.rng.randrange(3)
  g.compare(s,c,f,f'{f:x}/{i}',arg=g.rng.choice([0,1,0x100,0x101])if f==0x462a00 else 2000+i%3 if f==0x462af0 else 0x52720c)
for state in(0,29,30,1000,2000,2001,2002):
 for i in range(40):
  g.policy=i%3;g.resource_mode=i%3;s,c=g.fresh();s.primary[7]=state;g.compare(s,c,0x462350,f'wrapper/{state}/{i}')
# Directed signed RNG, sentinel rectangle and timer-boundary cases.
for rv in [0,1,19,20,32,33,49,50,99,100,0xffffffff,0xfffffffd,0x80000000]:
 for region in range(-1,9):
  g.policy=0;g.random_results=[rv,0xffffffff];s,c=g.fresh();s.enemy[0x184//4]=region&0xffffffff
  c.generic.tick=4000;c.privateTail[(0x468-0x420)//4]=0;c.privateTail[(0x46c-0x420)//4]=4000
  c.privateTail[(0x458-0x420)//4]=3000;c.privateTail[(0x45c-0x420)//4]=1000
  for f in(0x463020,0x463120,0x4631e0):g.compare(s,c,f,f'directed/{rv:x}/{region}/{f:x}')
# Actual26 Level1 WWD records, real original shared-Human fixture, then whole
# Officer startup and repeated native Officer idle ticks on original tile map.
import struct,zlib
raw=(g.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
records=[]
for plane in range(struct.unpack_from('<I',raw,732)[0]):
 ph=struct.unpack_from('<40I',raw,offset+160*plane);pos=ph[35]
 for _ in range(ph[32]):
  words=struct.unpack_from('<71I',raw,pos);size=284+sum(words[1:5]);logic=raw[pos+284+words[1]:pos+284+words[1]+words[2]]
  if logic.split(b'\0',1)[0]==b'Officer':records.append(raw[pos:pos+size])
  pos+=size
assert len(records)==26,len(records)
g.world=g.install_world(True);g.ground=True;g.policy=0;g.resource_mode=1;g.random_results=[99,99]
fixture_records=[]
for index,record in enumerate(records):
 s,c=g.fresh();g.initialize_record(s,record);g.original_human_fixture(s,c)
 # Restore startup actor/logic because the actual Human base is supplied only
 # when the verified whole Officer wrapper calls its constructor dependency.
 g.initialize_record(s,record);s.primary[7]=0;s.actor[0x70//4]=g.S;s.actor[0x78//4]=g.K
 before_y=s.actor[0x50//4];g.compare(s,c,0x462350,f'actual26/{index}/startup')
 fixture_records.append({'index':index,'x':s.actor[0x4c//4],'recordY':before_y,'groundY':s.actor[0x50//4],'flags':s.actor[2],'state':s.primary[7],'health':s.actor[0x10c//4]})
 for tick in(1000,3999,4000,5000,0xfffffffe,1):
  c.generic.tick=tick;g.compare(s,c,0x462350,f'actual26/{index}/idle/{tick}')
 g.humanBase=None
assert any(x['recordY']!=x['groundY']for x in fixture_records)
report={'calls':g.calls,'events':g.event_count,'originalAddresses':len(g.m.executed),'actualOfficerRecords':len(records),'originalHumanFixtureCalls':g.humanReferenceCalls,'originalHumanReferenceAddresses':len(g.humanExecuted),'humanNative':False,'actualGround':fixture_records}
(g.scratch/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='actualGround'}))
