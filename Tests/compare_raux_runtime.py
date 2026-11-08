#!/usr/bin/env python3
import raux_runtime_helpers as h
for n in range(30):
 h.capture=n%5==0;h.fresh();h.g.damage=h.g.health=h.g.range=[0,0.75,1,1.25,2,-1][n%6];h.found=n%3!=0;h.compare(0x47e2d0,('whole-constructor/explicit-common-service',n),(h.A,),meaningful=True)
print('PASS30 specialized constructors with explicit common boundary',flush=True)
for f in(0x40e1b0,0x40e560,0x47eeb0,0x40e5b0,0x40e580,0x47f020,0x47f0c0,0x47f160,0x47f290,0x47f600,0x47f680,0x47f6b0,0x47e810):
 for n in range(20):
  h.capture=n%5==0;h.fresh(2000);h.put(h.E+0x184,[n%7,0,2+n%2]);h.randomValues=[n%5,50];h.g.tick=n*500;h.put(h.A+0x40,[n%2*2]);h.compare(f,('specialized-method',hex(f),n),meaningful=f in(0x40e580,0x47f020,0x47f0c0,0x47f160,0x47f290,0x47f600,0x47f680,0x47f6b0))
print('PASS',h.calls,h.eventCount,len(h.m.executed),flush=True)

for f in(0x47ece0,0x47eef0):
 for n in range(240):
  h.fresh(h.stateIDs[['LS_IDLE','LS_HITLOW','LS_HITHIGH'][n%3]])
  h.put(h.E+0x184,[n%8,0,[0,2,3][n%3]]);h.put(h.E+0x20,[n%4]);h.put(h.E+0x3c4,[[0,99,100,199,200,499,500,0xffffffff][n%8]])
  h.put(h.PP,[n%2,(n//2)%2,0,0,0,n%2]);h.randomValues=[n%3,[0,98,99,100,2147483647,0xffffffff][n%6]];h.mutation=n%2
  if n%7==0:h.put(0x5376b4,[h.NAMEOBJECTS,3])
  h.compare(f,('pre-hit-directed',hex(f),n),(0x523148,)if f==0x47ece0 else(h.OTHER,))
for state in [h.stateIDs[n]for n in('LS_IDLE','LS_HOME','LS_STARTUP','LS_JUMPOVER','LS_HITHIGH','LS_HITLOW','LS_STRIKE')]:
 for n in range(20):
  h.fresh(state);h.put(0x53c9c0,[n%3]);h.put(h.E+0x184,[n%7,0,2+n%2]);h.randomValues=[n%5,50];h.compare(0x47e8e0,('source-class-dispatch',state,n),(state,),meaningful=True)
for state in (0,29,30,1000,h.stateIDs['LS_IDLE']):
 for n in range(20):
  h.fresh(state);h.found=n%3!=0;h.compare(0x47e210,('whole-callback',state,n),(h.A,),receiver=0,meaningful=True)
for n in range(30):
 h.fresh();h.put(h.PL+28,[n%7]);h.put(h.PLAYER+0x10c,[[0,1,100,0xffffffff][n%4]]);h.compare(0x40e660,('boss-death/gem-service',n),(n%4,))
print('PASS expanded',h.calls,h.eventCount,len(h.m.executed),flush=True)

h.capture=False;h.composeCommon=True
for n in range(20):
 h.fresh();h.g.damage=h.g.health=h.g.range=[0.75,1,1.25,2][n%4]
 h.compare(0x47e2d0,('joined-frozen-Human-constructor',n),(h.A,),meaningful=True)
print('PASS joined constructors',h.calls,h.eventCount,len(h.m.executed),flush=True)

for n in range(500):
 h.composeCommon=False;h.capture=n%25==0;h.fresh();h.put(h.E+0x18c,[2+n%2]);h.queryValues=[[1,0],[0,2,0],[0,0,3,0],[0,0,0],[1,1]][n%5]
 for off in(0x38,0x40,0x48):h.number(h.E+off,h.rng.choice([0.0,0.001,-0.001,20.125,2000.0,-2000.0]))
 for off in(0x68,0x70,0x78):h.number(h.E+off,h.rng.uniform(-10000,30000))
 h.compare(0x47f290,('jump-solver/signedzero/queries',n),meaningful=True)
h.composeCommon=True;histories=[]
for n in range(12):
 h.capture=True;h.fresh();inventory=h.realResources();row=h.retailRecord();h.compare(0x47e210,('retail-whole-create',n),(h.A,),receiver=0,meaningful=True);h.capture=False
 h.put(0x53c9c0,[2]);h.realRandom=True;h.put(h.THREAD+20,[n+1]);h.g.tick=1017
 h.compare(0x47e210,('retail-startup/source-random',n),(h.A,),receiver=0,meaningful=True)
 visited=[]
 for tick in range(160):
  h.capture=tick%20==0;h.g.tick+=17;h.compare(0x47e210,('retained-full-FSM',n,tick),(h.A,),receiver=0,meaningful=True);visited.append(h.get(h.L+28)[0])
 # Source grounded/contact signals are supplied by the declared collision transport.
 h.capture=True;h.put(h.A+0xcc,[1]);h.put(h.E+0x3c4,[250]);h.compare(0x47f290,('retail-jump-over-entry',n),meaningful=True)
 for tick in range(12):
  h.capture=tick%4==0;h.g.tick+=17
  if tick==10:h.put(h.A+0xcc,[1])
  h.compare(0x47e210,('retained-jump-land',n,tick),(h.A,),receiver=0,meaningful=True)
 h.capture=True;h.put(h.E+0x3c4,[250]);h.put(h.OTHER+0x104,[10]);h.put(h.OTHER+0x164,[0]);h.put(h.OTHER+0xd0,[4]);h.put(h.E+0x19c,[0xffffffff]);h.put(h.PP+20,[n%2]);h.compare(0x47eef0,('retail-hit-health',n),(h.OTHER,));h.compare(0x40e660,('retail-common-death',n),(n%4,));h.compare(0x47eeb0,('retail-boss-health-reset',n));h.put(h.L+28,[29]);h.compare(0x47e210,('retail-cleanup-29',n),(h.A,),receiver=0,meaningful=True);h.compare(0x47e7f0,('retail-private-delete',n),(1,),meaningful=True)
 histories.append({'record':row['index'],'frames':172,'states':sorted(set(visited)),'seed':n+1})
ownStateHistories=[]
for name in('LS_IDLE','LS_HOME','LS_HITLOW','LS_HITHIGH','LS_JUMPOVER'):
 h.fresh();h.realResources();h.retailRecord();h.capture=False;h.compare(0x47e210,('own-state-create',name),(h.A,),receiver=0);h.put(h.A+8,[h.get(h.A+8)[0]|0x10]);h.put(h.A+0xcc,[1]);h.put(h.E+0x300,[h.get(h.E+0x300)[0]|4]);h.put(h.L+28,[h.stateIDs[name]]);h.realRandom=True;h.put(h.THREAD+20,[1]);visited=[]
 for tick in range(60):
  h.capture=tick%10==0;h.g.tick+=17;h.compare(0x47e210,('grounded-own-state-history',name,tick),(h.A,),receiver=0,meaningful=True);visited.append(h.get(h.L+28)[0])
 ownStateHistories.append({'initial':name,'frames':60,'states':sorted(set(visited)),'support':'declared source-grounded flags10/mode1'})
for n in range(40):
 h.fresh();h.realResources();h.retailRecord();h.capture=False;h.compare(0x47e210,('typed-hit-create',n),(h.A,),receiver=0);h.capture=n%5==0;h.put(h.OTHER+8,[n*0x100000]);h.compare(0x4a07e0,('source-typed-hit-block-adapter',n),(h.OTHER,))
h.capture=False;h.composeCommon=False;h.realRandom=False
for state in(0,29,30):
 h.fresh(state)
 if state==0:h.allocated=0
 else:h.put(h.L+24,[0])
 h.unsafeCompare(0x47e210,('original-null-prefix',state),(h.A,),receiver=0)
count=h.dumpCorpus();report={'calls':h.calls,'events':h.eventCount,'addresses':len(h.m.executed),'heapBytes':h.SIZE,'globalBytes':0x30000,'sanitizerCorpusCases':count,'retailHistories':histories,'ownStateHistories':ownStateHistories,'resources':inventory,'unsafePrefixes':h.unsafeCases}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print('PASS final',h.calls,h.eventCount,len(h.m.executed),'corpus',count,'unsafe',len(h.unsafeCases),flush=True)
