#!/usr/bin/env python3
import lift_throw_runtime_helpers as h
for fn in(0x440420,0x440120,0x440710,0x440350,0x4407d0,0x4409d0,0x440410,0x4405b0,0x440260,0x440870,0x440a50):
 for n in range(32):
  h.prepare(n);h.mutation=n%2;h.g.animationDelta=[0,1,18,80,0xffffffff][n%5];h.compare(fn,receiver=h.E,label=f'inherited/{fn:x}/{n}')
 print(f'PASS inherited{fn:x}',flush=True)
for fn in(0x41dc50,0x41a850,0x41b1f0,0x41b280,0x41c4e0,0x4171d0):
 for n in range(96):
  h.prepare(n);h.mutation=n%2;h.put(h.P+8,[n%2,n%3]);h.put(h.INPUT+4,[h.rng.choice([0,2,0x20,0x22]),h.rng.choice([0,0x1000000,0x2000000,0x3000022]),0xffffffff]);h.g.stageDelta=h.rng.choice([0,1,18,99,100]);h.g.animationDelta=h.rng.choice([0,1,16,80]);h.put(h.P+0xf0,[h.rng.choice([0,1,399,400,100000]),h.rng.choice([0,1,2999,3000,0xffffffff])]);h.put(h.A+0x1a4,[n%3==0]);h.moveMode=4 if n%4==0 else 1;h.put(h.P+60,[h.rng.choice([0,8,9,10,18])]);h.put(h.E+0x2fc,[h.rng.choice([0,1,32,33,64])]);
  if h.get(h.E+0x2fc)[0]>32:h.put(h.E+0x300,[h.VT+0x400]);h.put(h.VT+0x400,[0,0])
  h.compare(fn,[h.A,h.L,h.P]+([h.TARGET]if fn==0x41dc50 else[]),label=f'player/{fn:x}/{n}',void=fn!=0x4171d0)
 print(f'PASS player{fn:x}',flush=True)
for seed in range(128):
 for pressed in(0,0x20,2,0x22,4,0x60):
  h.prepare(seed);h.put(h.P+300,[0]);h.put(h.P+48,[1]);h.put(h.A+80,[960]);h.put(h.INPUT+4,[pressed,h.rng.choice([0,0x4000000,0x5000000]),0xffffffff]);h.queryTarget=h.rng.choice([0,h.TARGET]);h.queryDistance=h.rng.choice([-1,0,31,63,64,149,150,151,999999]);h.randomValue=seed%4;h.put(h.TARGET+0x164,[h.rng.choice([0,1,5,0x401])]);h.compare(0x41d850,[h.A,h.L,h.P],label=f'joined-select-lift/{seed}/{pressed}')
print('PASS frozen attack/input selector→whole lift and target-gate histories',flush=True)
for count in(0,1,32,33,64):
 for index in(0,1,31,32,63):
  for outcome in(0,1):
   h.prepare(1);h.resizeResult=outcome;h.put(h.E+0x2fc,[count]);h.put(h.E+0x300,[h.VT+0x400 if count>32 else 0]);h.put(h.VT+0x400,[0,0,0,0]);h.compare(0x420fc0,[index],h.E+0x2f4,f'bit-set/{count}/{index}/{outcome}',void=True)
   if (index//32+1)>=h.get(h.E+0x2fc)[0]//32:h.compare(0x4dbd20,[index],h.E+0x2f4,f'bit-grow-boundary/{count}/{index}/{outcome}')
for status in(-1,0,1,2,0x7fffffff,0x80000000):
 for threshold in(-1,0,1,2,0xffffffff):
  h.prepare();h.put(h.E+32,[status]);h.compare(0x421010,[0x4207a0,threshold],h.E,f'callback-install/{status}/{threshold}',void=True)
for fn in(0x440b20,0x440c90,0x4207a0):
 for n in range(32):
  h.prepare(n);h.put(h.E+0x3bc,[h.SOUND,h.SOUND]);h.put(h.E+0x384,[h.SEQ,h.SEQ]);h.put(h.E+0x18c,[n%4]);h.compare(fn,receiver=h.E,label=f'common-helper/{fn:x}/{n}',void=fn==0x4207a0)
print('PASS exact transition/bit-mask/release helpers and declared resize outcomes',flush=True)
records=h.json.loads((h.ROOT/'work/breakable-agent/level1-inventory.json').read_text())['records'];kegs=[r for r in records if r['strings'][1]=='PowderKeg'];assert len(kegs)==58
for row in kegs:
 h.prepare(row['index']);h.sourceKeg(row);h.put(h.A+76,[h.get(h.TARGET+76)[0]]);h.put(h.A+80,[h.get(h.TARGET+80)[0]+h.get(h.TARGET+0x124)[0]-60]);h.put(h.P+300,[0]);h.put(h.P+4,[0]);h.put(h.INPUT+4,[0x20,0,0xffffffff]);h.queryTarget=h.TARGET;h.queryDistance=0
 h.compare(0x41d850,[h.A,h.L,h.P],label=f'actual-keg/{row["index"]}/input-lift');assert h.get(h.L+28)==[5000]
 for phase in range(3):
  h.put(h.A+0x16c,[42 if phase==0 else 43]);h.compare(0x4405b0,receiver=h.E,label=f'actual-keg/{row["index"]}/lifting{phase}');h.put(h.P+8,[1,1]);h.animationResult=0;h.put(h.INPUT+4,[0,0x1000000 if phase%2 else 0x2000000,0xffffffff]);h.compare(0x41a850,[h.A,h.L,h.P],label=f'actual-keg/{row["index"]}/carry{phase}',void=True)
 h.put(h.INPUT+4,[2,0x22,0xffffffff]);h.compare(0x41a850,[h.A,h.L,h.P],label=f'actual-keg/{row["index"]}/throw-request',void=True);assert h.get(h.L+28)==[5001]
 for delta in(1,499,1500,1001):h.g.animationDelta=delta;h.compare(0x41b280,[h.A,h.L,h.P],label=f'actual-keg/{row["index"]}/charge{delta}',void=True)
 h.put(h.INPUT+8,[0]);h.animationResult=1;h.compare(0x41b280,[h.A,h.L,h.P],label=f'actual-keg/{row["index"]}/release',void=True);assert h.get(h.P+300)==[0]
 h.compare(0x440260,receiver=h.E,label=f'actual-keg/{row["index"]}/flight');h.compare(0x440350,receiver=h.E,label=f'actual-keg/{row["index"]}/restore')
print('PASS all58 actual source PowderKeg creator/input→lift→carry→charge→throw→restore histories',flush=True)
for weight in(0,1,20,0x7fffffff,0x80000000,0xffffffff):
 for facing in(0,1):
  for strong in(0,1):
   h.prepare();h.put(h.E+0x1ac,[weight]);h.put(h.P,[facing]);h.g.strongThrow=strong;h.compare(0x440120,receiver=h.E,label=f'wrapped-throw/{weight}/{facing}/{strong}')
for n in range(128):
 h.prepare(n);h.physics.velocity[0]=h.rng.uniform(-500,500);h.physics.acceleration[0]=h.rng.uniform(-4000,4000);h.physics.position[0]=h.rng.uniform(-10000,10000);h.physics.minimum[0]=-2500;h.physics.maximum[0]=2500;h.physics.maximumDelta[0]=h.rng.choice([0,1,24,64]);h.physics.maximumVelocity[0]=h.rng.choice([0,30,300]);h.g.stageDelta=h.rng.choice([0,1,18,99,0x80000000,0xffffffff]);h.g.animationDelta=h.rng.choice([0,1,18,99]);h.animationResult=0;h.put(h.INPUT+8,[0]);h.compare(0x41a850,[h.A,h.L,h.P],label=f'physics-limits-and-separated-clocks/{n}',void=True)
print('PASS wrapped signed throw strength and retained full physics limits/separate clocks',flush=True)
for history in range(8):
 h.prepare(history);h.put(h.P+300,[0]);h.actualLiftANI();h.compare(0x41dc50,[h.A,h.L,h.P,h.TARGET],label=f'actual-CLAW-LIFT-ANI/{history}/entry',void=True)
 for frame in range(12):
  h.g.stageDelta=[0,1,18,33,100][frame%5];h.g.animationDelta=[1,16,33,80][frame%4];h.put(h.INPUT+4,[0,0,0xffffffff]);h.compare(0x41a850,[h.A,h.L,h.P],label=f'actual-CLAW-LIFT-ANI/{history}/frame{frame}',void=True)
 h.scriptedAnimation()
print('PASS actual CLaw LIFT ANI decoded by original record body and retained raw animation bridge',flush=True)
unsafePrefixes=0
# Safe native guard for an originally unmapped large-bitset backing.
h.prepare(0);h.put(h.E+0x2fc,[64,0x7000000]);h.sync();h.native_events.clear();h.original_events.clear();r=h.U();a=(h.U*1)(1);assert not h.lib.claw_lift_throw_entry(0x420fc0,h.E+0x2f4,a,1,h.C.byref(h.c),h.dependency,None,h.C.byref(r))and h.c.fault==1
try:h.m.call(0x420fc0,h.E+0x2f4,h.pack(1));raise AssertionError('expected original invalid backing fault')
except h.UcError:pass
assert h.raw(True)==h.raw(False)and h.globalsRaw(True)==h.globalsRaw(False);unsafePrefixes+=1
# Original resize failure's EBP is wordCount: without a mapped low page its
#4dc680 diagnostic read faults before544b14/handler stores. No retail page0 claim.
h.prepare(0);h.resizeResult=0;h.put(h.E+0x2fc,[0]);h.core.words[0]=0xabcdef01;h.sync();h.native_events.clear();h.original_events.clear();oldLookup=h.c.scene.lookup;h.c.scene.lookup=h.Lookup(lambda _,t,n:None if t<4096 else h.lookup(_,t,n));h.c.fault=0;assert not h.lib.claw_lift_throw_entry(0x420fc0,h.E+0x2f4,a,1,h.C.byref(h.c),h.dependency,None,h.C.byref(r))and h.c.fault==1
h.m.u.mem_unmap(0,4096)
try:h.m.call(0x420fc0,h.E+0x2f4,h.pack(1));raise AssertionError('expected original diagnostic low-page fault')
except h.UcError:pass
finally:h.m.u.mem_map(0,4096);h.c.scene.lookup=oldLookup
assert h.raw(True)==h.raw(False)and h.globalsRaw(True)==h.globalsRaw(False)and h.native_events==h.original_events;unsafePrefixes+=1
h.prepare();before=h.raw(True);values=(h.U*1)(0);h.c.fault=0;r=h.U(123);assert not h.lib.claw_lift_throw_entry(0x41ebd0,0,None,0,h.C.byref(h.c),h.dependency,None,h.C.byref(r))and not h.c.fault and h.raw(True)==before and r.value==123
assert not h.lib.claw_lift_throw_entry(0x41dc50,0,values,1,h.C.byref(h.c),h.dependency,None,h.C.byref(r))and h.c.fault==2 and h.raw(True)==before
import gzip
(h.WORK/'replay.bin.gz').write_bytes(gzip.compress(h.replay.getvalue(),compresslevel=6))
addresses={x for x in h.m.executed-set(h.COUNTS)-{0x4f6286,0x41d750,h.COPYRECT,h.SETRECT,h.m.stop}if 0x400000<=x<0x550000}
report={'completeCalls':h.calls,'derivedKegConstructorCalls':h.creatorCalls,'orderedCompleteSnapshots':h.eventCount,'heapBytes':h.SIZE,'globalBytes':h.GLOBAL_SIZE,'originalAddresses':len(addresses),'unsafeOriginalPrefixes':unsafePrefixes,'actualLevel1Kegs':58,'actualClawLiftANIDecodes':h.aniDecodes,'actualClawLiftANIHistories':8,'sanitizerReplays':h.replayCases,'originalInstructionAddresses':[hex(x)for x in sorted(addresses)],'externalFunctions':[hex(x)for x in sorted(h.COUNTS)],'scope':'Exact raw player lift/throw/cleanup plus frozen enemy/helper/selector composition. Resource/audio/collision/RNG/target/CRT/handler boundaries explicit. Actual source-derived base constructor fixture is a declared composition service at4332f0, not a new original binary proof of that body.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k!='originalInstructionAddresses'}),flush=True)
