#!/usr/bin/env python3
import punk_rat_runtime_helpers as h
h.voids|={0x404dd0,0x404eb0,0x43e9e0,0x440e20,0x43f120,0x43f450,0x43efe0,0x43fcb0,0x43fd60,0x43f030,0x43f500,0x43f540}
for n in range(90):
 h.fresh();h.found=n%7!=0;h.g.healthScale=[1.,0.,-1.,.5,100.,float('nan')][n%6];h.g.tick=[0,1000,0x7fffffff,0x80000000,0xffffffff][n%5];h.put(h.A+0x108,[n%3]);h.put(h.A+0x148,[0 if n%2 else 123]);h.compare(0x4743f0,args=[h.A],label=('ctor',n),record=n<3);assert h.get(h.E+0x40c)==[0xabcdef01]
print('PASS constructors',h.calls,h.eventsCount,flush=True)
for n in range(120):
 for f in(0x474c50,0x474d00,0x474db0,0x474e10,0x474e60,0x414640,0x414660,0x414860,0x414a60):
  h.fresh();h.randomValues=[(0,9,10,99,100,0xffffffff,0x80000000)[n%7]];h.g.randomDisabled=n%3==0;h.g.audioEnabled=n%2;h.g.powerup=0x26b7 if n%5==0 else 0;h.mutation=n%2;h.put(h.A+64,[2*(n%2)]);h.number(h.E+0x68,(-1e20,300.25,float('nan'))[n%3]);h.number(h.E+0x80,(-1e20,300.25,float('nan'))[n%3]if n%2 else 900);h.number(h.E+0x98,(-1e20,300.25,float('nan'))[n%3]if n%2 else 900);h.put(h.CP+112,[n%2]);h.put(h.CHILD+0x148,[0x80000000 if n%3==0 else 700]);h.put(h.CP+56,[0x80000000,n,0xffffffff]);h.compare(f,h.CP if f in(0x414640,0x414660,0x414860,0x414a60)else h.E,label=('method',n,hex(f)))
for state in(0,29,30,1000):
 h.fresh();h.put(h.L+28,[state]);h.compare(0x474330,0,[h.A],('wrapper',state))
for n in range(20):
 h.fresh();h.compare(0x474710,label=('destructor',n));h.compare(0x4746f0,args=[n%2],label=('delete',n),record=n==0)
print('PASS methods',h.calls,h.eventsCount,flush=True)
# All28 retail records, original tiles, actual ANI until strike→fire→recoil→move.
rows=h.json.load(open(h.WORK/'inventory.json'))['records'];histories=[]
for ri,row in enumerate(rows):
 h.fresh();h.realResources(row['level']);h.retailRecord(row);h.retailWorld(row['level']);h.put(h.L+28,[0]);h.compare(0x474330,0,[h.A],('retail-start',row['level'],row['index']),record=ri in(0,8));assert h.get(h.E+0x14c)==[9]and h.get(h.E+0x150)==[0];assert h.get(h.E+0x40c)==[0xabcdef01];seen={};fired=False
 for frame in range(230):
  h.g.tick+=17;h.compare(0x474330,0,[h.A],('retail-frame',ri,frame),record=ri in(0,8)and frame in(0,120,150));state=h.get(h.L+28)[0];seen[state]=seen.get(state,0)+1
  fired|=h.get(h.CL+28)[0]==h.stateIDs['LS_FIRING']
 assert h.stateIDs['LS_STRIKE']in seen and h.stateIDs['LS_RECOIL']in seen and fired,('missing source lifecycle',ri,seen)
 # Actual typed damage, virtual hit/death entry, dead callback, cleanup and free.
 h.put(h.CHILD+0x104,[25]);h.put(h.CHILD+0xd0,[2]);h.put(h.A+0x74,[h.CHILD]);h.sharedStates.attackerToken=h.CHILD;h.sharedStates.attackerActor[:]=h.get(h.CHILD,128);h.put(h.PL+24,[h.PP]);h.put(h.PL+20,[h.PP]);h.put(h.PLAYER+108,[h.PL]);h.put(h.PP+232,[8]);h.sharedStates.playerPrivate[:]=h.get(h.PP,78);h.compare(0x43e9e0,label=('retail-elected-hit',ri),record=ri in(0,8));h.compare(0x43e9e0,label=('retail-dedup',ri));assert h.C.c_int32(h.get(h.A+0x10c)[0]).value==-23
 h.compare(0x474ec0,label=('retail-death',ri),record=ri in(0,8));assert h.get(h.L+28)==[h.stateIDs['LS_DEAD']];h.compare(0x474330,0,[h.A],('retail-terminal',ri));assert h.get(h.A+8)[0]&0x10000;h.put(h.L+28,[29]);h.compare(0x474330,0,[h.A],('retail-cleanup',ri));childflags=h.get(h.CHILD+8)[0];h.compare(0x4746f0,args=[1],label=('retail-free',ri),record=ri in(0,8));assert h.get(h.E+0x408)==[h.CHILD]and h.get(h.CHILD+8)==[childflags];histories.append({'level':row['level'],'index':row['index'],'states':seen,'cannonFire':fired,'terminalDelete':True})
 print('PASS retail',ri+1,'/',len(rows),flush=True)
h.fresh();h.created=0;h.put(h.L+28,[0]);h.failure(0x474330)
h.fresh();h.createdChild=0;h.failure(0x474bc0,h.E,[],1)
h.fresh();h.failure(0x4747e0,h.E,[0x7fffffff],1)
h.writeCorpus();report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','wholeCalls':h.calls,'fullSnapshots':h.eventsCount,'snapshotBytes':h.SIZE+h.GN,'executedAddresses':len(h.m.executed),'retailHistories':histories,'unsafePrefixes':h.prefixes,'sanitizerReplayCalls':h.replayCases,'assets':list({r['path']:r for r in h.assetProfile}.values()),'stateIDs':h.stateIDs};(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print('PASS PunkRat',h.calls,'wholecalls',h.eventsCount,'fullsnapshots',len(h.m.executed),'addresses',flush=True)
