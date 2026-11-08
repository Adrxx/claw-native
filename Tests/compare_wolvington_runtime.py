#!/usr/bin/env python3
import wolvington_runtime_helpers as h
for n in range(30):
 h.capture=n<2;h.fresh();h.g.damage=h.g.health=h.g.range=[0,0.75,1,1.25,2,-1][n%6];h.found=n%3!=0
 h.compare(0x49fbf0,('whole-specialized-constructor/explicit-Human-boundary',n),(h.A,),meaningful=True)
print('PASS',h.calls,h.eventCount,len(h.m.executed),flush=True)

for f in(0x4a0140,0x4a0160,0x4a0740,0x4a0800,0x4a0960,0x4a0a90,0x4a0ae0,0x4a0b30,0x4a0c10,0x4a0ec0,0x4a0f40,0x4a0fd0,0x4a1020,0x4a10b0,0x4a10f0,0x4a1180,0x4a1250):
 for n in range(30):
  h.capture=n<2;h.fresh(h.stateIDs[['LS_IDLE','LS_HITLOW','LS_HITHIGH','LS_BOUNCE'][n%4]]);h.put(h.E+0x184,[n%7,0,2+n%2]);h.put(h.E+0x3c4,[[0,9,10,19,20,299,300,399,400,499,500,999,1000,0xffffffff][n%14]]);h.put(h.E+0x460,[n%2,n%13]);h.put(h.E+0x474,[h.SOUND]);h.put(h.PP,[n%2,1]);h.put(h.PP+60,[n%9]);h.put(h.E+0x400,[60,120]);h.put(h.A+0x40,[n%2*2]);h.randomValues=[n*5]
  h.compare(f,('specialized-body',hex(f),n),(n%2,)if f==0x4a0140 else(0x523148,)if f==0x4a0740 else(),meaningful=f==0x4a0140)
print('PASS expanded',h.calls,h.eventCount,len(h.m.executed),flush=True)
for n in range(50):
 h.capture=n<2;h.fresh();h.put(h.A+0x1a4,[n%2]);h.put(h.E+0x1a0,[(n//2)%2]);h.put(h.E+0x460,[n%2,0,(n%2)*130-65,n%3*15-20,n%2*600-300]);h.put(h.GP+300,[h.GEM]);h.put(h.GEM+0x40,[0]);h.put(h.GP+0x138,[0xffffffff,0xffffffff,1,1]);h.put(h.GEM+0x118,[0xffffffff,0xffffffff,1,1]);h.put(h.GEM+0x128,[0xffffffff,0xffffffff,1,1]);h.put(h.GEM+0x138,[0xffffffff,0xffffffff,1,1]);h.compare(0x4a0cf0,('original-magic-emitter-with-created-child-service',n))
print('PASS emitter',h.calls,h.eventCount,len(h.m.executed),flush=True)
for n in range(60):
 h.capture=n<2;h.fresh();h.put(h.A+0x164,[n]);h.put(h.MANAGER+0x124,[n%2]);h.put(0x53724c,[(n//2)%2]);h.compare(0x411cf0,('whole-bullet-specialized-ctor/common-adapter',n),(h.A,),meaningful=True)
for n in range(80):
 h.capture=n<2;h.fresh();h.put(h.E+0x150,[n%4,0]);h.put(h.A+0x118,[[0xffffffff,0xffffffff,1,1],[10,10,10,10],[0,0,0xfffffffe,0xfffffffe]][n%3]);h.randomValues=[n*29,32767];h.compare(0x412150,('bullet-sparkle/count/remainders',n),meaningful=True)
print('PASS bullet leaves',h.calls,h.eventCount,len(h.m.executed),flush=True)
h.composeCommon=True
for n in range(20):
 h.capture=n<2;h.fresh();h.g.damage=h.g.health=h.g.range=[0.75,1,1.25,2][n%4];h.compare(0x49fbf0,('joined-Human-CBoss-constructor',n),(h.A,),meaningful=True)
for n in range(6):
 h.capture=n<2;h.fresh();h.g.level=6;inventory=h.realResources();h.retailRecord();h.compare(0x49fb30,('retail-callback-create',n),(h.A,),receiver=0,meaningful=True);h.put(0x53c9c0,[2]);h.put(h.A+8,[h.get(h.A+8)[0]|16]);h.put(h.A+0xcc,[1]);h.put(h.E+0x300,[h.get(h.E+0x300)[0]|4]);h.realRandom=True;h.put(h.THREAD+20,[n+1])
 for tick in range(120):
  h.capture=tick<12 or tick==119;h.g.tick+=17;h.compare(0x49fb30,('retail-retained-fsm',n,tick),(h.A,),receiver=0,meaningful=True)
print('PASS joined retail histories',h.calls,h.eventCount,len(h.m.executed),flush=True)

# Full original specialized registries and source default/fallback election.
h.composeCommon=False
for f,table,fnbase,state,body in ((0x4a0230,h.RCLASS,h.CLASSFN,'LS_HOME',0x4a0960),(0x411e70,0x534ad8,h.BASE+0x2b000,'LS_FALLING',0x412150)):
 for n in range(32):
  h.capture=n<2;h.fresh();h.put(h.E+0x150,[0,0]);ident=h.stateIDs[state];h.put(fnbase+(ident-2000)*4,[body if n%2 else 0]);h.compare(f,('registry-double-lookup-or-inherited',hex(f),n),(ident,))
for n in range(80):
 h.capture=n<2;h.fresh(h.stateIDs['LS_HOME']);h.put(h.E+0x18c,[2+n%2]);h.put(h.A+0x40,[n%2*2]);h.put(h.A+0x38,[0xffffffff if n%3==0 else 0]);h.randomValues=[0,32,33,99,100,0xffffffff,0x80000000,0x7fffffff][n%8:n%8+1];h.compare(0x44f1b0,('whole-inherited-idle',n))
h.composeCommon=True
for f in(0x49fb30,0x410340):
 h.composeCommon=f==0x410340
 for state in(1000,29,30):
  h.capture=True;h.fresh(state);h.put(h.E+0x154,[0]);h.put(h.E,[0x50ff2c if f==0x49fb30 else 0x50b87c]);h.compare(f,('wrapper-lifecycle',hex(f),state),(h.A,),receiver=0,meaningful=True)
# Actual image/ANI transport, original specialized bullet startup followed by
# whole shared Flare creator; deferred actor creation remains an explicit service.
h.composeCommon=True
for n in range(12):
 h.capture=True;h.fresh();h.g.level=6;inventory=h.realResources();h.put(h.L+16,[0x410340,0,h.E,0]);h.put(h.MANAGER+0x124,[n%2]);h.put(0x53724c,[(n//2)%2]);h.compare(0x410340,('real-bullet-full-creator',n),(h.A,),receiver=0,meaningful=True)
 if h.get(h.E+0x154)[0]:
  h.put(h.GL+28,[0]);h.put(h.GEM+0x188,[0x513870,h.GEM,0,0,0,0,1,0,0,0,0x3f800000]);h.compare(0x458010,('real-shared-Flare-initialize',n),(h.GEM,),receiver=0,meaningful=True)
 h.put(h.OTHER+108,[h.OTHER+0x200]);h.put(h.OTHER+0x210,[0x4000020]);h.number(h.E+0x50,[-300,0,300][n%3]);h.realRandom=True;h.put(h.THREAD+20,[n+1])
 for tick in range(30):
  h.capture=tick<4 or tick==29;h.g.tick+=17;h.compare(0x410340,('real-bullet-retained-flight',n,tick),(h.A,),receiver=0,meaningful=True)
 h.put(h.E+0x120,[0x10000]);h.compare(0x412150,('real-flight-source-collision-flag',n));h.put(h.L+28,[29]);h.compare(0x410340,('real-bullet-state29',n),(h.A,),receiver=0,meaningful=True);h.put(h.L+28,[30]);h.compare(0x410340,('real-bullet-state30',n),(h.A,),receiver=0,meaningful=True)
h.composeCommon=False
for n in range(16):
 h.capture=n<2;h.fresh();h.put(h.E+0x150,[1,0]);h.put(h.A+0x118,[0xffffffff,0xffffffff,0xfffffffe,0xfffffffe]);h.randomValues=[n%2];h.compare(0x412150,('source-zero-width-sparkle-choice',n))
h.capture=False;h.composeCommon=False
for f in(0x49fb30,0x410340):
 h.fresh();h.allocated=0;h.unsafeCompare(f,('source-null-allocator',hex(f)),(h.A,),receiver=0)
h.fresh();h.put(h.E+0x150,[1,0]);h.created=0;h.unsafeCompare(0x412150,'source-null-sparkle-creator')
h.fresh();h.put(h.E+0x150,[1,0]);h.put(h.A+0x118,[0,0,0xfffffffe,0xfffffffe]);h.randomValues=[0x80000000];h.unsafeCompare(0x412150,'source-signed-divide-overflow')
report={'calls':h.calls,'events':h.eventCount,'executedAddresses':len(h.m.executed),'unsafe':h.unsafeCases,'resources':inventory,'sanitizerCorpus':h.dumpCorpus()}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n')
print('PASS Wolvington',h.json.dumps({k:v for k,v in report.items()if k not in('resources','unsafe')},sort_keys=True),'unsafePrefixes',len(h.unsafeCases),flush=True)
