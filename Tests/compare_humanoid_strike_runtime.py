#!/usr/bin/env python3
"""Exact multiargument strike helpers and retained original state updates."""
import humanoid_strike_helpers as h
for fn in(0x43ee10,0x43eee0):
 for resourceMode in(0,1,2):
  for mutation in range(5):
   for seed in range(4):
    s,c=h.prepared(seed);h.resource_mode=resourceMode;h.strikeMutation=mutation;h.policy=h.mutate=0
    args=(0x529aa0,h.RECT)+( (0x529888,)if fn==0x43eee0 else())
    h.seqHint=h.text(args[0]);h.soundHint=h.text(0x529888);h.compare_strike(s,c,fn,(hex(fn),resourceMode,mutation,seed),args)
    assert s.enemy[8]==1
for shift in(-12,-8,-4,0,4,8,12):
 s,c=h.prepared(shift);h.resource_mode=1;h.policy=h.mutate=0
 for i in range(8):s.enemy[(0x210+i*4)//4]=100+i
 h.seqHint=h.text(0x529aa0);h.compare_strike(s,c,0x43ee10,('overlapping rectangle',shift),(0x529aa0,h.E+0x220+shift))
s,c=h.prepared(430);h.resource_mode=1;h.policy=h.mutate=0;c.privateTail[4:8]=[123,456,789,1011];h.seqHint=h.text(0x529aa0);h.compare_strike(s,c,0x43ee10,'shared Human tail rectangle view',(0x529aa0,h.E+0x430))
# Whole original null rectangle failure after state transition, no fake return.
s,c=h.prepared(0);h.resource_mode=1;h.policy=h.mutate=0;h.seqHint=h.text(0x529aa0)
cpu=h.u.context_save();h.u.mem_unmap(0,4096);h.zero_mapped=False
try:h.compare_strike(s,c,0x43ee10,'null rectangle fault prefix',(0x529aa0,0),fault_expected=True)
finally:h.u.context_restore(cpu);h.u.mem_map(0,4096);h.zero_mapped=True
# Preserved source prefix for missing primary / attached actor identities.
for field in(0x10,0x12c):
 s,c=h.prepared(field);h.resource_mode=1;h.policy=h.mutate=0;s.enemy[field//4]=0;h.seqHint=h.text(0x529aa0);h.u.mem_unmap(0,4096);h.zero_mapped=False
 try:h.compare_strike(s,c,0x43ee10,('null identity fault prefix',field),(0x529aa0,h.RECT),fault_expected=True)
 finally:h.u.mem_map(0,4096);h.zero_mapped=True
# Shared strike counter and audio service order before rectangle stores.
for counter in(0,1,2,0x80000000,0xffffffff):
 for enabled in(0,1):
  for stopped,delay in((0,0),(1,0),(1,1)):
   s,c=h.prepared(counter);h.resource_mode=1;h.policy=h.mutate=0;h.animationResult=1;h.finishAnimation=False
   c.sharedStates.strikeCounter=counter;c.sharedStates.audioEnabled=enabled;s.enemy[0x3a0//4]=h.resourceViews[0].token;s.actor[0x1a4//4]=stopped;s.actor[0x19c//4]=delay
   h.compare_strike(s,c,0x43f030,('strike counter/audio/live stop',counter,enabled,stopped,delay))
print('PASS overloads/raw args/lookup fallback/sound/capture/aliasing/null rectangle',flush=True)
import struct,zlib,json
h.policy=h.mutate=0;h.resource_mode=1;h.world=h.install_world(True);h.ground=h.realGround=h.realQueries=h.realMotion=h.realPoints=True;h.random_results=[99,201,24,55]
raw=(h.ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
records=[]
for plane in range(struct.unpack_from('<I',raw,732)[0]):
 ph=struct.unpack_from('<40I',raw,offset+160*plane);pos=ph[35]
 for _ in range(ph[32]):
  words=struct.unpack_from('<71I',raw,pos);length=284+sum(words[1:5]);logic=raw[pos+284+words[1]:pos+284+words[1]+words[2]].split(b'\0')[0]
  if logic in(b'Officer',b'Soldier'):records.append((logic.decode(),raw[pos:pos+length]))
  pos+=length
assert len(records)==42
histories=[]
for index,(kind,record)in enumerate(records):
 s,c=h.prepared_officer(index)if kind=='Officer'else h.prepared(index)
 h.resource_mode=1;h.policy=h.mutate=0;h.compose=0;h.strikeMutation=0;h.initialize_record(s,record);s.primary[7]=0
 entry=0x462410 if kind=='Officer'else 0x48aa40
 h.compare_strike(s,c,entry,('actual42 full constructor',kind,index),args=(h.A,),entry_kind='officer'if kind=='Officer'else'soldier')
 h.image_profile(s,kind);h.compose=1;c.sharedStates.audioEnabled=0;c.sharedStates.strikeCounter=1;c.generic.animationDelta=17
 name=b'LEVEL_'+kind.upper().encode()+b'_STRIKE';sequence=h.load_ani(name,f'LEVEL1/ANIS/{kind.upper()}/STRIKE.ANI');s.enemy[0x310//4]=sequence;s.actor[0x1a4//4]=s.actor[0x19c//4]=0
 s.actor[0x138//4]=0x80000000;c.generic.tick=1000
 h.compare_strike(s,c,0x43efe0,('actual42 zeroarg strike entry',kind,index))
 assert s.primary[7]==h.ids[b'LS_STRIKE']and s.enemy[8]==1
 hitCount=0
 for frame in range(80):
  c.generic.tick+=17;h.compare_strike(s,c,0x43f030,('actual42 fullANI/shared strike update',kind,index,frame))
  if c.sharedStates.strikeCounter==0:hitCount+=1
  if s.enemy[8]==2:break
 assert s.enemy[8]==2 and c.sharedStates.strikeCounter==1 and hitCount>0,(kind,index,frame,s.enemy[8],hitCount)
 histories.append({'kind':kind,'record':index,'updates':frame+1,'state':s.primary[7],'attackRect':list(s.actor[0x138//4:0x148//4])})
report={'wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.event_count,'originalAddresses':len(h.m.executed),'extraHeapBytes':h.EXTRA_SIZE,'actualOfficerSoldierProfiles':len(records),'retainedStrikeANIHistories':len(histories),'originalANIRecordDecodes':h.ani_decodes,'allocationBodies':'none in overload helpers','failurePrefixes':3,'history':histories}
(h.scratch/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='history'}))
