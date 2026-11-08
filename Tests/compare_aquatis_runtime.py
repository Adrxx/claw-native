import aquatis_runtime_helpers as h
for n in range(12):
 h.capture=n<2;h.fresh();h.g.health=[.75,1,1.25][n%3];h.g.damage=[.75,1,1.25][n%3];h.compare(0x404990,('whole constructor',n),(h.A,),meaningful=True)
print('PASS constructors',h.calls,h.eventCount,flush=True)
for f in(0x404310,0x404e20,0x405fa0,0x405f60,0x405060,0x4050b0,0x4051a0,0x405240,0x4053d0,0x405440,0x4054c0,0x405540,0x4055e0,0x405740,0x405640,0x4057a0,0x4058b0,0x4059e0,0x405a60,0x405af0,0x405d50,0x405df0,0x405ed0):
 for n in range(30):
  h.capture=n<2;sid=h.aquatisFresh(['LS_IDLE','LS_SCARED','LS_HITHIGH','LS_SUPERFRENZY','LS_DEADACT1'][n%5]);h.g.tick=[1000,4000,0xffffffff][n%3];h.g.audioEnabled=n%2;h.randomValues=[[-2,-1,0,1,2,3,100,0x80000000][n%8]];h.put(h.A+0x40,[n%2*2]);h.put(h.A+0x16c,[[0,204,207][n%3]]);h.put(h.A+0x1a4,[n%2]);h.put(h.A+0x19c,[(n//2)%2]);h.put(h.OTHER+0xd0,[[4,0x20,0x2000000][n%3]]);h.put(h.E+0x18c,[2+n%2]);h.put(h.E+0x4b8,[n%2]);h.put(h.E+0x4b4,[(n//2)%2]);h.put(h.E+0x4a0,[n%2,(n//2)%2,n%6,n%4]);h.put(h.E+0x4c0,[(n//3)%2,(n//4)%2]);h.put(h.E+0x4ec,[(n//3)%2]);h.put(0x534878,[n%3]);h.put(h.PLAYER+0x10c,[n%3*100]);h.put(h.PP+20,[n%2]);h.compare(f,('whole state',hex(f),n),(sid,)if f==0x404310 else(n%2,)if f==0x404e20 else(h.SOUND if n%2 else 0,)if f==0x405f60 else(),meaningful=f==0x404e20)
print('PASS states',h.calls,h.eventCount,flush=True)
h.composeCommon=True
for n in range(6):
 h.capture=n<2;h.aquatisFresh();h.compare(0x404990,('joined CBoss/Human constructor',n),(h.A,),meaningful=True)
print('PASS joined constructor',h.calls,h.eventCount,flush=True)
for n in range(6):
 h.capture=n<2;h.aquatisFresh();inventory=h.realResources();row=h.retailRecord();h.compare(0x4041f0,('actual retail startup',n),(h.A,),receiver=0,meaningful=True);h.put(0x53c9c0,[2]);h.put(h.E+0x300,[h.get(h.E+0x300)[0]|4]);h.put(h.A+8,[h.get(h.A+8)[0]|16]);h.put(h.A+0xcc,[1]);h.compare(0x4041f0,('actual shared startup/reset',n),(h.A,),receiver=0,meaningful=True);assert h.get(h.E+0x4ec)[0]==1022 and h.get(h.L+28)[0]==h.stateIDs['LS_IDLE'];h.put(h.E+0x4ec,[0]);h.put(h.E+0x300,[0]);h.put(h.A+0xcc,[1]);h.realRandom=True;h.put(h.THREAD+20,[n+1])
 for tick in range(150):
  h.capture=tick%50==0;h.g.tick+=17;h.compare(0x4041f0,('retained finite actor-FSM/controller cleared1022',n,tick),(h.A,),receiver=0,meaningful=True)
print('PASS actual ANI/WWD histories',h.calls,h.eventCount,flush=True)
# Real-resource attack and frenzy retained through actual state completion.
attackHistories=[]
for mode in('high','low','frenzy','scared'):
 for facing in(2,3):
  h.capture=True;h.aquatisFresh();h.realResources();h.retailRecord();h.compare(0x4041f0,('real attack creation',mode,facing),(h.A,),receiver=0,meaningful=True);h.put(h.E+0x4ec,[0]);h.put(h.E+0x18c,[facing]);h.put(h.E+0x4b4,[0]);h.put(h.E+0x300,[h.get(h.E+0x300)[0]|4]);h.put(h.A+8,[h.get(h.A+8)[0]|16]);h.compare({'high':0x4055e0,'low':0x405740,'frenzy':0x4054c0,'scared':0x4053d0}[mode],('retained attack entry',mode,facing));markers=set();h.realRandom=True;h.put(h.THREAD+20,[123]);h.put(h.E+0x184,[0])
  for tick in range(500):
   h.capture=tick%80==0;h.g.tick+=17;h.compare(0x4041f0,('whole attack actor loop',mode,facing,tick),(h.A,),receiver=0,meaningful=True);markers.add(h.get(h.A+0x16c)[0])
   if h.get(h.L+28)[0]==h.stateIDs['LS_IDLE']:break
  assert h.get(h.L+28)[0]==h.stateIDs['LS_IDLE']
  if mode=='high':assert 204 in markers
  if mode=='low':assert 207 in markers
  attackHistories.append({'mode':mode,'facing':facing,'frames':tick+1,'markers':sorted(markers),'state':h.get(h.L+28)[0]})
print('PASS8 source retained attack/frenzy/scared',h.calls,h.eventCount,flush=True)
# Actual type4 hit election subtracts20, with source immunity and state gates;
# ordinary projectiles elect inherited hurt, preserving their explicit bodies.
deathHistories=[]
for n in range(6):
 h.capture=True;h.aquatisFresh();inventory=h.realResources();row=h.retailRecord();h.compare(0x4041f0,('real death creation',n),(h.A,),receiver=0,meaningful=True);h.put(h.E+0x4ec,[0]);h.put(h.E+0x300,[h.get(h.E+0x300)[0]|4]);h.put(h.A+8,[h.get(h.A+8)[0]|16]);h.compare(0x4050b0,('real initial idle',n));h.put(h.A+0x74,[h.OTHER]);h.put(h.OTHER+0xd0,[4]);h.put(h.E+0x184,[0]);h.put(h.E+0x18c,[2+n%2]);h.g.tick=10000
 for hit in range(5):
  h.capture=True;h.compare(0x405af0,('whole elected type4 hit',n,hit));assert h.get(h.A+0x10c)[0]==100-(hit+1)*20
  if hit<4:
   for tick in range(1000):
    h.capture=tick%150==0;h.g.tick+=17;h.compare(0x4041f0,('retained hit/frenzy recovery',n,hit,tick),(h.A,),receiver=0,meaningful=True)
    if h.get(h.L+28)[0]==h.stateIDs['LS_IDLE']and not h.get(h.E+0x4b4)[0]:break
   assert h.get(h.L+28)[0]==h.stateIDs['LS_IDLE']and not h.get(h.E+0x4b4)[0]
 assert h.get(h.L+28)[0]==h.stateIDs['LS_DEADACT1'];h.put(h.A+0x74,[0]);h.put(h.PLAYER+0x10c,[0 if n==5 else 100]);terminal=False
 for tick in range(500):
  h.capture=tick%100==0;h.g.tick+=17;h.compare(0x4041f0,('retained actual killfall/end request',n,tick),(h.A,),receiver=0,meaningful=True)
  if h.get(h.E+0x4a4)[0]:terminal=True;break
 assert terminal
 if n==5:assert h.get(h.E+0x4b8)[0]==1 and not any(e[0]==0x40e5c0 for e in h.events)
 else:assert h.get(h.E+0x4b8)[0]==0 and h.get(h.PL+28)[0]==5010 and any(e[0]==0x40e5c0 for e in h.events)and h.get(h.E+0x300)[0]&16
 deathHistories.append({'profile':n,'health':h.get(h.A+0x10c)[0],'hits':h.get(h.E+0x4a8)[0],'framesToTerminal':tick+1,'alive':h.get(h.E+0x4b8)[0],'request':n!=5})
 h.capture=True;h.compare(0x404e20,('actual destructor/alias clear',n),(1,),meaningful=True);assert h.get(0x534874)[0]==0
print('PASS6 terminal elected hit→death→request/gate',h.calls,h.eventCount,flush=True)
# Exact unsigned clock boundary profiles and unsupported shape diagnostics.
h.composeCommon=False
for now in(0,1,0x7fffffff,0x80000000,0xffffff00,0xffffffff):
 for base in(0,1,0xffffff00,0xffffffff):
  for duration in(0,1,4000,0xffffffff):
   h.capture=False;h.aquatisFresh();h.g.tick=now;h.put(h.E+0x4dc,[base,duration]);h.compare(0x405540,('frenzy timer wraps',now,base,duration))
for state in(29,30,1000):
 h.capture=True;h.aquatisFresh();h.put(h.L+28,[state]);h.compare(0x4041f0,('facade lifecycle',state),(h.A,),receiver=0,meaningful=True)
h.capture=False;h.aquatisFresh();h.put(h.L+28,[0]);h.allocated=0;h.unsafeCompare(0x4041f0,'null Aquatis private allocation',(h.A,),receiver=0)
report={'calls':h.calls,'events':h.eventCount,'addresses':len(h.m.executed),'unsafe':h.unsafeCases,'resources':inventory,'record':row,'attacks':attackHistories,'deaths':deathHistories,'corpus':h.dumpCorpus(),'scope':'Whole Aquatis boss/core, actual Level12 source record; dynamic Crack/Dynamite/Stalactite controller protocol and physical services explicit. Bounded reset handshake1022 release is declared fixture input, not inferred controller body.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print('PASS final Aquatis',h.calls,h.eventCount,len(h.m.executed),'corpus',len(h.corpusCases),'unsafe',len(h.unsafeCases),flush=True)
