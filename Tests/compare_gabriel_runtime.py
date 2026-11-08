#!/usr/bin/env python3
import gabriel_runtime_helpers as h
for n in range(20):
 h.capture=n<2;h.fresh();h.g.level=8;h.g.health=[0,.75,1,1.25,2,-1][n%6];h.found=n%3!=0;h.compare(0x443ab0,('complete-Gabriel-constructor/declared-Human',n),(h.A,),meaningful=True)
print('PASS constructors',h.calls,h.eventCount,len(h.m.executed),flush=True)

for f in(0x444120,0x445950,0x444140,0x4441b0,0x4441f0,0x4442c0,0x444330,0x4444d0,0x4445d0,0x4446f0,0x444760,0x444850,0x444960,0x444aa0,0x444b70,0x444c20,0x444d00,0x444d90,0x444f80,0x445090,0x4452d0,0x4455b0,0x445600,0x445660,0x4456c0,0x445720,0x445810,0x446130):
 for n in range(20):
  h.capture=n<2;h.fresh(h.stateIDs[['LS_IDLE','LS_CANNONHIT','LS_BLOCKED','LS_STARTUP'][n%4]]);h.g.level=8;h.put(h.A+0x1a4,[n%2]);h.put(h.A+0x19c,[0]);h.put(h.A+0x16c,[[0,401,900][n%3]]);h.put(h.A+0x40,[n%2*2]);h.put(h.A+0x74,[h.OTHER if n%4 else 0]);h.put(h.OTHER+0xd0,[[4,0x20,0x40,0x2000000][n%4]]);h.put(h.E+0x18c,[2+n%2]);h.put(h.PP+0xe8,[n+1]);h.put(h.E+0x19c,[0]);h.put(h.E+0x514,[n%6]);h.put(h.E+0x524,[n%3]);h.put(h.E+0x520,[(n//2)%2]);h.put(h.E+0x534,[(n//3)%2]);h.randomValues=[n%4,n%3];h.mutation=n%4;h.put(h.A+0xcc,[n%2]);h.compare(f,('whole-boss-state',hex(f),n),(n%2,)if f==0x444120 else(n*25-475,)if f==0x446130 else(),meaningful=f==0x444120)
print('PASS boss states',h.calls,h.eventCount,len(h.m.executed),flush=True)
for f in(0x4452d0,0x446130):
 for n in range(500):
  h.capture=n<2;h.fresh(h.stateIDs['LS_IDLE']);h.g.level=8
  for off in(0x38,0x40,0x48):h.number(h.E+off,h.rng.choice([0.0,.001,-.001,20.125,2000.,-2000.]))
  for off in(0x68,0x70,0x78):h.number(h.E+off,h.rng.uniform(-10000,50000))
  h.put(h.E+0x52c,[h.rng.randrange(-10000,50000),h.rng.randrange(-10000,50000)]);h.compare(f,('complete-inline-solver',hex(f),n),(n-250,)if f==0x446130 else())
print('PASS source inline solver comparisons',h.calls,h.eventCount,len(h.m.executed),flush=True)
h.composeCommon=True
for n in range(10):
 h.capture=n<2;h.fresh();h.g.level=8;h.compare(0x443ab0,('complete-constructor/joined-CBoss-Human',n),(h.A,),meaningful=True)
for n in range(6):
 h.capture=n<2;h.fresh();h.g.level=8;inventory=h.realResources();h.retailRecord();h.compare(0x443290,('retail-created-boss',n),(h.A,),receiver=0,meaningful=True);h.put(0x53c9c0,[2]);h.realRandom=True;h.put(h.THREAD+20,[n+1]);h.put(h.A+0xcc,[1]);h.put(h.A+8,[h.get(h.A+8)[0]|16]);h.put(h.E+0x300,[h.get(h.E+0x300)[0]|4]);h.put(h.E+0x534,[0])
 for tick in range(120):
  h.capture=tick<8 or tick==119;h.g.tick+=17;h.compare(0x443290,('retained-retail-whole-FSM',n,tick),(h.A,),receiver=0,meaningful=True)
print('PASS joined retail boss',h.calls,h.eventCount,len(h.m.executed),flush=True)
# Source hit election and death phases retained on the actual Gabriel row.
for n in range(4):
 h.capture=n<2;h.fresh();h.g.level=8;inventory=h.realResources();h.retailRecord();h.compare(0x443290,('retail-death-create',n),(h.A,),receiver=0,meaningful=True);h.put(h.E+0x520,[0]);h.put(h.OTHER+0xd0,[0x40]);h.g.tick=10000
 for hit in range(5):
  h.capture=n<2;h.put(h.A+0x74,[h.OTHER]);h.compare(0x444d90,('retained-cannon-hit-election',n,hit));h.put(h.A+0x74,[0])
  for tick in range(160):
   h.capture=n<2 and tick%40==0;h.g.tick+=17;h.compare(0x444b70,('retained-cannon-hit-health',n,hit,tick))
   if h.get(h.L+28)[0]!=h.stateIDs['LS_CANNONHIT']:break
  assert h.get(h.A+0x10c)[0]==100-(hit+1)*20
 for tick in range(400):
  h.capture=n<2 and tick%80==0;h.g.tick+=17;h.compare(0x445090,('retained-death-act1',n,tick))
  if h.get(h.L+28)[0]==h.stateIDs['LS_DEADACT2']:break
 assert h.get(h.L+28)[0]==h.stateIDs['LS_DEADACT2'];h.capture=True;h.put(h.A+0xcc,[1]);h.compare(0x4455b0,('retained-death-ground-signal',n))
 for tick in range(160):
  h.capture=n<2 and tick%80==0;h.g.tick+=17;h.compare(0x445660,('retained-death-act3',n,tick))
  if h.get(h.L+28)[0]==h.stateIDs['LS_DEADACT4']:break
 assert h.get(h.L+28)[0]==h.stateIDs['LS_DEADACT4'];h.mutation=0
 for tick in range(1200):
  h.capture=n<2 and tick%80==0;h.g.tick+=17;h.compare(0x445720,('retained-gem-restoration-request',n,tick))
  if h.get(h.E+0x520)[0]:break
 assert h.get(h.PL+28)[0]==5010 and h.get(h.E+0x520)[0]==1 and any(e[0]==0x40e5c0 for e in h.events);h.capture=True;h.put(h.L+28,[29]);h.compare(0x443290,('retail-source-cleanup29',n),(h.A,),receiver=0,meaningful=True);h.compare(0x444120,('retail-original-destructor',n),(1,),meaningful=True)
print('PASS retained boss hit/death requests',h.calls,h.eventCount,len(h.m.executed),flush=True)
# Bounded wrappers and source class selectors keep unresolved child bodies explicit.
h.capture=False;h.composeCommon=False
for name in h.registryStates:
 h.fresh(h.stateIDs[name.decode()]);h.compare(0x4433b0,('actual-class-dispatch',name.decode()),(h.stateIDs[name.decode()],))
for state in(29,30,1000):
 h.fresh(state);h.compare(0x443290,('whole-retail-facade',state),(h.A,),receiver=0,meaningful=True)
for f in(0x4452d0,0x446130):
 h.fresh();
 for off in(0x38,0x40,0x48,0x68,0x70,0x78):h.number(h.E+off,0.0)
 h.put(h.E+0x52c,[0,100]);h.compare(f,('zero-distance/signed-zero',hex(f)),(0,)if f==0x446130 else())
h.fresh();h.allocated=0;h.unsafeCompare(0x443290,'source-null-boss-allocation',(h.A,),receiver=0)
h.fresh();h.put(h.E+0x534,[0]);h.put(h.E+0x510,[0]);h.put(h.A+0x16c,[401]);h.created=0;h.unsafeCompare(0x4445d0,'source-null-multibomb-creation')
report={'calls':h.calls,'events':h.eventCount,'addresses':len(h.m.executed),'unsafe':h.unsafeCases,'resources':inventory,'record':next(r for r in h.json.load(open(h.WORK/'records.json'))if r['strings'][1]=='Gabriel'),'corpus':h.dumpCorpus(),'scope':'Complete Gabriel boss/core; cannon/bomb specialized constructors/FSM/lifetime are explicit next closure.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n')
print('PASS final Gabriel core',h.calls,h.eventCount,len(h.m.executed),'corpus',len(h.corpusCases),'unsafe',len(h.unsafeCases),flush=True)
