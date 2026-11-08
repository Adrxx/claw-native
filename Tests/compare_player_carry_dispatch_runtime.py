#!/usr/bin/env python3
import player_carry_dispatch_runtime_helpers as h
for state in(5000,5001):
 for n in range(128):
  h.prepareCarry(n,state);h.mutation=n%2;h.put(h.P+8,[n%2,n%3]);h.put(h.INPUT+4,[h.rng.choice([0,2,8,0x20,0x22,0x28]),h.rng.choice([0,0x1000000,0x2000000,0x3000022]),0xffffffff]);h.g.stageDelta=h.rng.choice([0,1,18,99,100]);h.g.animationDelta=h.rng.choice([0,1,16,80]);h.put(h.P+0xf0,[h.rng.choice([0,1,399,400,100000]),h.rng.choice([0,1,2999,3000,0xffffffff])]);h.put(h.A+0x1a4,[n%3==0]);h.moveMode=4 if n%4==0 else 1;h.put(h.P+60,[h.rng.choice([0,8,9,10,18])]);h.put(h.E+0x2fc,[h.rng.choice([0,1,32,33,64])]);h.put(h.P+248,[h.rng.choice([0,1,18,0xffffffff])]);h.put(h.P+284,[h.rng.choice([0,1,18,0xffffffff])]);h.put(h.L+0x130,[h.rng.choice([0,1,18,0xffffffff])]);h.carry.cheat=n%3==0;h.carry.ignoreHazards=n%5==0;h.put(h.A+8,[0x400080 if n%4==0 else 0x90 if n%4==1 else 0x80]);h.put(h.P+48,[h.rng.choice([0,1,3,0x7fffffff,0xffffffff])])
  if h.get(h.E+0x2fc)[0]>32:h.put(h.E+0x300,[h.VT+0x400]);h.put(h.VT+0x400,[0,0])
  h.compareCarry(f'whole-dispatch/{state}/{n}')
 print(f'PASS complete415df0 initial{state}',flush=True)
for state in(5000,5001):
 for mutation in range(1,4):
  for flags in(0x80,0x90,0x400080):
   h.prepareCarry(mutation,state);h.epilogueMutation=mutation;h.put(h.INPUT+4,[8,0,0xffffffff]);h.put(h.P+4,[0]);h.put(h.A+8,[flags]);h.compareCarry(f'callback-mutations/{state}/{mutation}/{flags:x}')
print('PASS live common-tail callbacks and signed clamp/clock/flags mutation ordering',flush=True)
print('PASS',h.carryCalls,h.carryEvents,flush=True)
records=h.json.loads((h.ROOT/'work/breakable-agent/level1-inventory.json').read_text())['records'];kegs=[r for r in records if r['strings'][1]=='PowderKeg'];assert len(kegs)==58
for row in kegs:
 h.prepareCarry(row['index'],5000);h.sourceKeg(row);h.put(h.A+76,[h.get(h.TARGET+76)[0]]);h.put(h.A+80,[h.get(h.TARGET+80)[0]+h.get(h.TARGET+0x124)[0]-60]);h.put(h.P+300,[0]);h.put(h.P+4,[0]);h.put(h.INPUT+4,[0x20,0,0xffffffff]);h.queryTarget=h.TARGET;h.queryDistance=0
 h.compare(0x41d850,[h.A,h.L,h.P],label=f'actual-keg/{row["index"]}/input-lift');assert h.get(h.L+28)==[5000]
 for phase in range(3):
  h.put(h.A+0x16c,[42 if phase==0 else 43]);h.compare(0x4405b0,receiver=h.E,label=f'actual-keg/{row["index"]}/lifting{phase}');h.put(h.P+8,[1,1]);h.animationResult=0;h.put(h.INPUT+4,[0,0x1000000 if phase%2 else 0x2000000,0xffffffff]);h.compareCarry(f'actual-keg/{row["index"]}/carry{phase}')
 h.put(h.INPUT+4,[2,0x22,0xffffffff]);h.compareCarry(f'actual-keg/{row["index"]}/throw-request');assert h.get(h.L+28)==[5001]
 for delta in(1,499,1500,1001):h.g.animationDelta=delta;h.compareCarry(f'actual-keg/{row["index"]}/charge{delta}')
 h.put(h.INPUT+8,[0]);h.animationResult=1;h.compareCarry(f'actual-keg/{row["index"]}/release');assert h.get(h.P+300)==[0]
 h.compare(0x440260,receiver=h.E,label=f'actual-keg/{row["index"]}/flight');h.compare(0x440350,receiver=h.E,label=f'actual-keg/{row["index"]}/restore')
print('PASS all58 actual Level1 Keg source creators→lift→complete dispatcher carry/charge/release→enemy flight/restore',flush=True)
# Completely different, deliberately separated clocks and unsigned terminal values.
for state in(5000,5001):
 for delta in(0,1,18,99,0x80000000,0xffffffff):
  for flags in(0x80,0x90,0x400080):
   h.prepareCarry(delta,state);h.g.stageDelta=delta;h.g.animationDelta=1;h.put(h.A+8,[flags]);h.put(h.P+0xf0,[0xffffffff,3000]);h.put(h.P+8,[1,1]);h.put(h.INPUT+4,[8,0,0]);h.put(h.L+0x130,[0xffffffff]);h.put(h.P+248,[0x80000000]);h.put(h.P+284,[delta]);h.compareCarry(f'unsigned-boundaries/{state}/{delta:x}/{flags:x}')
print('PASS unsigned stage/animation clock separation through common tail',flush=True)
# Guard exact prefix when original scene-root dereference is unmapped.
h.prepareCarry(1,5000);h.put(h.P+8,[0,0]);h.put(h.P+4,[0]);h.put(h.INPUT+4,[8,0,0]);h.epilogueMutation=4;h.animationResult=0;h.put(h.A+0x1a4,[0]);h.loadPlayer();h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();result=h.lib.claw_player_dispatch_carry(h.C.byref(h.player),h.C.byref(h.inputs),h.C.byref(h.carry),h.dependency,h.carryDependency,None);assert result==1 and h.carry.fault==1
try:h.m.call(0x415df0,0,h.pack(h.A));raise AssertionError('expected unmapped original scene-root fault')
except h.UcError:pass
assert h.raw(True)==h.raw(False)and h.globalsRaw(True)==h.globalsRaw(False)and h.native_events==h.original_events
h.prepareCarry(1,24);h.loadPlayer();old=(bytes(h.player),bytes(h.inputs),h.raw(True));assert h.lib.claw_player_dispatch_carry(h.C.byref(h.player),h.C.byref(h.inputs),h.C.byref(h.carry),h.dependency,h.carryDependency,None)==0;assert old==(bytes(h.player),bytes(h.inputs),h.raw(True))
# Explicit external-service cancellation preserves the complete reached prefix.
# Stop the original at the same adapted call, without claiming normal completion.
@h.CarryDependency
def cancelled(ctx,event,user):
 value=h.carryDependency(ctx,event,user)
 if event.contents.function==0x41fc30:h.put(h.A+8,[0x400080]);ctx.contents.fault=99
 return value
stopTransport=False
def stopHook(u,address,size,user):
 if stopTransport and address==0x41fc30:h.put(h.A+8,[0x400080],False);u.emu_stop()
h.m.u.hook_add(h.UC_HOOK_CODE,stopHook)
h.prepareCarry(1,5000);h.put(h.P+8,[0,0]);h.put(h.INPUT+4,[0,0,0]);h.loadPlayer();h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();assert h.lib.claw_player_dispatch_carry(h.C.byref(h.player),h.C.byref(h.inputs),h.C.byref(h.carry),h.dependency,cancelled,None)==1 and h.carry.fault==99
stopTransport=True
try:
 h.m.call(0x415df0,0,h.pack(h.A));raise AssertionError('expected explicit service stop before original completion')
except AssertionError as error:assert str(error)=='Original routine exceeded instruction bound'
finally:stopTransport=False
assert h.raw(True)==h.raw(False)and h.globalsRaw(True)==h.globalsRaw(False)and h.native_events==h.original_events
assert not any(e[0]==0x417c50 for e in h.native_events)
import gzip
(h.WORK/'carry-replay.bin.gz').write_bytes(gzip.compress(h.carryReplay.getvalue(),compresslevel=6))
addresses={x for x in h.m.executed-set(h.COUNTS)-{0x4f6286,0x41d750,h.COPYRECT,h.SETRECT,h.m.stop,0x420910,0x41fc30,0x4cd740,0x417c50}if 0x400000<=x<0x550000}
report={'completeDispatcherCalls':h.carryCalls,'completeComposedLiftEnemyCalls':h.calls,'originalDerivedKegCreators':h.creatorCalls,'orderedFullSnapshots':h.carryEvents+h.eventCount,'heapBytes':h.SIZE,'globalBytes':h.GLOBAL_SIZE,'actualLevel1Kegs':58,'actualLevel1KegHistories':58,'originalUnsafePrefixes':1,'externalServiceCancellationPrefixes':1,'sanitizerReplayCases':h.carryReplayCases,'originalInstructionAddressCount':len(addresses),'originalInstructionAddresses':[hex(x)for x in sorted(addresses)],'externalCommonTail':['420910','41fc30','4cd740','417c50'],'scope':'Complete415df0 only initial5000/5001 plus frozen LiftThrow and common input epilogue. Exact resource/animation/audio/collision/elected-target services are finite explicit adapters; retail Keg raw WWD/source constructors are retained, generic base construction is source fixture transport.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k!='originalInstructionAddresses'}),flush=True)
