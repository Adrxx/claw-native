#!/usr/bin/env python3
import katherine_runtime_helpers as h
for fn in(0x453df0,0x4542f0,0x454310,0x4543e0,0x4547c0,0x4548c0,0x454a10,0x454b90,0x454c20,0x454cb0,0x4550e0,0x455230,0x455280,0x4552d0,0x455350,0x455360,0x4553a0,0x40f780):
 for n in range(12):
  h.prepare(n);args=[h.A]if fn==0x453df0 else[n%2]if fn==0x4542f0 else[h.stateIDs['LS_IDLE']]if fn==0x4543e0 else[h.nameTokens['LS_IDLE']]if fn==0x4547c0 else[h.OTHER]if fn==0x4548c0 else[h.SEQ,n%2]if fn==0x455360 else[0x523148]if fn==0x4553a0 else[0x528354]if fn==0x40f780 else[];receiver=h.E+0x128 if fn in(0x455360,0x40f780)else h.E
  h.compare(fn,receiver,args,f'whole/{fn:x}/{n}',void=fn in(0x454310,0x4543e0,0x4547c0,0x4548c0,0x4550e0,0x455360,0x4553a0),record=n==0)
 print('PASS',hex(fn),flush=True)
# Directed branch boundaries preserve signed clock/config/RNG bits, raw names.
for i in range(480):
 h.prepare(i);h.randomValues=[[-2147483648,-201,-101,-3,-2,-1,0,1,4,5,9,10,49,50,99,100,200,201,32767,2147483647][i%20]]*5;h.found=i%7!=0;h.mutation=i%5;h.put(h.E+0x3c4,[[-1,0,199,200,399,400,499,500,599,600,0x80000000,0x7fffffff][i%12]]);h.put(h.E+0x184,[i%9]);h.put(h.PR+4,[i%2]);h.put(h.E+0x20,[i%4]);h.put(h.A+56,[0xffffffff if i%3==0 else 0]);h.put(h.PR+20,[i%2]);h.queryValues=[[1,0],[0,2,0],[0,0,3,0],[0,0,0],[1,1]][i%5];h.terrainResult=i%4!=0;h.put(h.A+0x1a4,[i%2]);h.put(h.A+0x19c,[i%3]);h.g.jumpDisabled=i%2
 fn=[0x4547c0,0x454a10,0x4548c0,0x454c20,0x454cb0,0x4552d0][i%6]
 args=[([0x527204,0x528454,0x52720c,h.nameTokens['LS_JUMP'],h.nameTokens['LS_FLIP3'],h.nameTokens['LS_STRIKE'],h.nameTokens['LS_IDLE']][i%7])]if fn==0x4547c0 else[h.OTHER]if fn==0x4548c0 else[]
 if fn==0x4548c0:h.put(h.L+28,[h.stateIDs[['LS_IDLE','LS_HITLOW','LS_HITHIGH'][i%3]]]);h.put(0x5376b4,[h.BASE+0x30000]);h.put(0x5376b8,[i%3])
 h.compare(fn,args=args,label=f'directed/{i}',void=fn in(0x4547c0,0x4548c0))
for i in range(72):
 h.prepare(i);h.g.damageScale=h.g.healthScale=h.g.rangeScale=[-100,-1,-0.0,0.01,1,1.99,2,100,float('nan')][i%9];h.found=i%2!=0;h.compare(0x453df0,args=[h.A],label=f'scales/{i}')
print('PASS directed',h.calls,h.eventsCount,flush=True)

# Numeric edge profiles cover the specialized left inlined target and actual
# right420dd0 call, with signed zero retained in the complete physics buffer.
import itertools,json,hashlib
for i,(side,acc,pos)in enumerate(itertools.product((2,3),(-2000.,-0.,0.,.1,2000.),(-0.,0.,.1))):
 h.prepare();h.composeBodies=False;h.number(h.E+0x38,acc);h.number(h.E+0x40,0.);h.number(h.E+0x48,0.);h.number(h.E+0x78,pos);h.put(h.E+0x18c,[side]);h.compare(0x454cb0,label=f'numeric/{i}',record=i<2)
# Legal source TLS histories; originalrand executes unchanged instructions.
for seed in(0,1,0x1b3cf,0xffffffff):
 h.prepare();h.realRandom=True;h.put(h.THREAD+20,[seed])
 for f in(0x4547c0,0x454a10,0x454cb0,0x454c20,0x4552d0):h.compare(f,args=[h.nameTokens['LS_IDLE']]if f==0x4547c0 else[],label=f'TLS/{seed}/{f:x}',void=f==0x4547c0)
h.realRandom=False
# Retained actual retail record, real Level4 cells and source-derived registry
# names. Landing election in the class-only history is explicit; fulltick
# below also executes the original collision and inherited motion graph.
assetInventory=[];worldProfile=None
for seed in range(8):
 h.prepare(seed);h.composeBodies=True;assetInventory=h.realResources();h.retailRecord();worldProfile=h.retailWorld();h.randomValues=[seed*5];h.compare(0x453d30,0,[h.A],label=f'chain{seed}/ctor',record=seed==0);h.put(0x53c9c0,[2]);h.compare(0x4543e0,args=[h.stateIDs['LS_STARTUP']],label=f'chain{seed}/startup',void=True,record=seed==0)
 h.put(h.PLAYER+76,[h.get(h.A+76)[0]+(100 if seed%2 else-100)]);h.put(h.PLAYER+80,h.get(h.A+80));h.put(h.E+0x18c,[2+seed%2]);h.compare(0x454cb0,label=f'chain{seed}/jump',record=seed==0)
 for frame in range(15):
  h.g.tick+=17;h.g.animationDelta=17;h.compare(0x4543e0,args=[h.get(h.L+28)[0]],label=f'chain{seed}/air/{frame}',void=True,record=seed==0 and frame==0)
 h.put(h.A+0xcc,[1]);h.compare(0x4543e0,args=[h.get(h.L+28)[0]],label=f'chain{seed}/land',void=True,record=seed==0)
 for frame in range(80):
  h.g.tick+=17;h.g.animationDelta=17;h.compare(0x4543e0,args=[h.get(h.L+28)[0]],label=f'chain{seed}/flip/{frame}',void=True,record=seed==0 and frame in(0,12,79))
 h.put(h.OTHER,h.get(h.A,128));h.put(h.OTHER+108,[h.OL]);h.put(h.OL,h.get(h.L,93));h.put(h.OL+20,[h.OP]);h.put(h.OP,[0]*78);h.put(h.OTHER+0x104,[10]);h.put(h.E+0x3c4,[700]);h.put(h.L+28,[h.stateIDs['LS_IDLE']]);h.compare(0x4548c0,args=[h.OTHER],label=f'chain{seed}/hit',void=True,record=seed==0)
 h.put(h.A+0x10c,[10]);h.put(h.L+28,[h.stateIDs['LS_IDLE']]);h.compare(0x4548c0,args=[h.OTHER],label=f'chain{seed}/fatal-hit',void=True,record=seed==0);assert h.get(h.A+0x10c)==[0]
 h.compare(0x40e660,args=[0],label=f'chain{seed}/death',record=seed==0);assert h.get(h.PL+28)==[5010]and h.get(h.E+0x45c)==[1]
 h.compare(0x40e660,args=[0],label=f'chain{seed}/death-repeat',record=seed==0);assert h.get(h.E+0x45c)==[1]
 h.put(h.L+28,[29]);h.compare(0x453d30,0,[h.A],label=f'chain{seed}/cleanup',record=seed==0);assert h.g.boss==0
 h.compare(0x4542f0,args=[1],label=f'chain{seed}/delete',record=seed==0)
print('PASS retail retained',h.calls,h.eventsCount,flush=True)
for seed in range(4):
 h.prepare(seed);h.composeBodies=True;h.realResources();h.retailRecord();h.retailWorld();h.compare(0x453d30,0,[h.A],label=f'tick{seed}/ctor');h.put(0x53c9c0,[2]);h.put(h.PLAYER+76,[18600]);h.put(h.PLAYER+80,[1769]);h.put(h.E+0x410,[h.SOUND]);h.put(h.E+0x14,[0]);h.put(h.E+0x18,[0]);h.put(h.E+0x2fc,[32,0]);h.put(h.E+0x1d4,[0]);h.put(h.A+0x80,[0]);h.randomValues=[seed*10]
 for frame in range(150):
  h.g.tick+=17;h.g.animationDelta=17;h.compare(0x453d30,0,[h.A],label=f'tick{seed}/{frame}',record=seed==0 and frame in(0,1,10,20,100))
print('PASS complete retail tick',h.calls,h.eventsCount,flush=True)
# Controller startup, no-op and lifecycle states from the original callback.
for state in(0,29,30,1000):
 h.prepare();h.composeBodies=False;h.put(h.L+28,[state]);h.compare(0x453d30,0,[h.A],label=f'callback-state/{state}',record=True)
# Actual original nullallocation prefix: primary is1000 before unchecked
# vtable read. Native stops safely with the same reached raw stores/events.
h.prepare();h.created=0;h.put(h.L+28,[0]);h.flush();h.m.u.mem_write(h.BASE,bytes(h.heap));h.m.u.mem_write(h.GS,h.C.string_at(h.ptr(h.GS),h.GN));h.m.write_words(0,[0x12345678]);h.nativeEvents.clear();h.originalEvents.clear();h.errors.clear();out=h.U();args=(h.U*1)(h.A);assert not h.lib.claw_katherine_entry(0x453d30,0,args,1,h.C.byref(h.ctx),h.dependency,None,h.C.byref(out))and h.ctx.fault==1
saved=h.nullPageOff()
try:h.m.call(0x453d30,0,h.pack(h.A));raise AssertionError('original allocation null unexpectedly completed')
except h.UcError:pass
h.m.u.mem_map(0,4096);h.m.u.context_restore(saved)
assert h.raw(True)==h.raw(False)and h.nativeEvents==h.originalEvents;assert h.get(h.L+28)==[1000];prefixes=1
corpus=h.writeCorpus();report={'sourceSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.eventsCount,'executedOriginalAddresses':len(h.m.executed),'replayCases':h.replayCases,'unsafePrefixes':prefixes,'retailRecords':1,'retainedHistories':8,'completeFrameHistories':4,'pidHeaders':44,'aniGroups':19,'world':worldProfile,'rawBytesPerSnapshot':h.SIZE+h.GN,'corpus':str(corpus.relative_to(h.ROOT))};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');(h.WORK/'asset-profile.json').write_text(json.dumps(assetInventory,indent=2)+'\n');print('PASS Katherine',json.dumps(report),flush=True)
