#!/usr/bin/env python3
"""Original world loot tables, drop wrapper, RNG and true scene composition."""
import ctypes as C,json,struct,zlib,subprocess,sys
import world_loot_helpers as t
for cfg in(0,1,2,13,14,0xffffffff):
 for policy in(0,1,2):
  for seed in range(3):
   t.prepare(seed);t.g.configurationWord=cfg;t.put(t.CFG,[cfg]);t.policy=policy
   t.compare('initialize',('table bootstrap',cfg,policy,seed));t.compare('initialize',('repeated bootstrap',cfg,policy,seed))
   assert t.g.itemCount==62 and t.g.words[340]==1
for count in(-1,0,1,61,62,66):
 t.prepare();t.g.itemCount=count&0xffffffff
 for id in(-0x80000000,-1,0,1,31,61,62,65,66,0x7fffffff):t.compare('name',('literal identity',count,id),id)
for compose in(0,1):
 for slot_count in(-1,0,1,2,9,16):
  for declared in(-0x80000000,-3,0,1,2,9,0x40000001):
   for launch in(0,1,0xffffffff):
    t.prepare();t.context.composeCreation=compose;t.g.highLaunch=launch;t.put(t.INV+0x24,[slot_count,declared]);t.put(t.INV+0x2c,[1,0,2,61,62,65,0xffffffff,7,0,8,9,10,11,12,13,14])
    t.compare('drop',('slot/fan/RNG/inherited/creator',compose,slot_count,declared,launch))
for seed in range(40):
 t.prepare(seed);t.policy=3;t.context.composeCreation=seed%2;t.g.highLaunch=seed%2;t.put(t.INV+0x24,[1,1]);t.put(t.INV+0x2c,[1,2,3])
 t.compare('drop',('mutable callback history',seed));t.policy=0
 for actor in t.actors:
  for item in(-1,1,61,62,66):t.compare('rebind',('logic selection',seed,actor,item),actor,item)
# Original v1.0 CD Level1 object records, with inventory slots mapped by the
# frozen exact WWD loader and GenericEnemy inventory wrapper. No edited assets.
raw=(t.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();planes,offset=struct.unpack_from('<2I',raw,732)
if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
records=[]
for plane in range(planes):
 base=offset+plane*160;count=struct.unpack_from('<I',raw,base+128)[0];pos=struct.unpack_from('<I',raw,base+140)[0]
 for n in range(count):
  w=struct.unpack_from('<71I',raw,pos);end=pos+284+sum(w[1:5]);name=raw[pos+284+w[1]:pos+284+w[1]+w[2]].split(b'\0')[0]
  if name in(b'Rat',b'Officer',b'Soldier'):records.append((name.decode(),w))
  pos=end
t.prepare(1);t.g.configurationWord=1;t.put(t.CFG,[1]);t.compare('initialize','CD Level1 inventory table');template=bytes(t.g)
actual_items=0
for name,w in records:
 t.prepare(w[0]);t.g=t.Globals.from_buffer_copy(template);t.put(t.CFG,[t.g.configurationWord]);t.context.composeCreation=1
 ids=[w[i]for i in(35,37,36,38,39,41,40,42,15)];declared=sum(x!=0 for x in ids)
 t.put(t.INV+0x24,[9,declared]);t.put(t.INV+0x2c,ids);t.put(t.SOURCE+0x4c,w[5:7]);t.put(t.SOURCE+0x100,[w[15]]);t.put(t.SOURCE+0x148,w[55:57]);t.put(t.SOURCE+0xfc,[w[14]])
 t.compare('drop',('actual CD Level1 enemy inventory',name,w[0]));assert len(t.actors)==declared;actual_items+=declared
report={'completeOperations':t.calls,'orderedCompleteSnapshots':t.event_count,'TLSArgumentReturnSnapshots':t.tls_count,'originalAddresses':len(t.m.executed),'rawGlobalWords':341,'rawHeapBytes':t.SIZE,'actualLevel1Enemies':len(records),'actualLevel1DropItems':actual_items,'scope':'Whole4719e0/42df90/473630/473660 plus composed4c8da0; image/audio/actual pickup callbacks and resource lookup bodies explicit.'}
(t.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
subprocess.run([sys.executable,str(t.ROOT/'Tests/world_loot_death_chain.py')],check=True)
