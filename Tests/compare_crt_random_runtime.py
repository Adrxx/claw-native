#!/usr/bin/env python3
import crt_random_runtime_helpers as h
seeds=[0,1,0x1b3cf,0x7fffffff,0x80000000,0xffffffff]+[h.rng.getrandbits(32)for _ in range(128)]+[1<<bit for bit in range(32)]
for seed in seeds:
 h.prepare(seed^0xa5a5a5a5);h.compare(0x4a3040,[seed],f'srand/{seed:x}',seed in seeds[:6]);assert h.get(h.A+0x14)==[seed]
 for n in range(32):
  old=h.get(h.A+0x14)[0];value=h.compare(0x4a3050,label=f'wrapped-rand/{seed:x}/{n}');assert h.get(h.A+0x14)==[(old*214013+2531011)&0xffffffff]and value==h.get(h.A+0x14)[0]>>16&0x7fff
print('PASS all32bit seed classes and retained signed/wrapping rand histories',flush=True)
for fn in(0x4a3040,0x4a3050,0x4a7dc0):
 for mutation in(0,1):
  h.prepare(0);h.put(h.OS+20,[0]);h.mutation=mutation;h.compare(fn,[0x80000000]if fn==0x4a3040 else[],f'lazy-TLS/{fn:x}/{mutation}',True);assert h.get(h.A+0x50)==[0x5312e8]and h.get(h.A) == [0x11111111]
for seed in seeds[:6]:
 h.prepare(seed);h.compare(0x4a7da0,[h.CUSTOM],f'initializer-preserved29words/{seed:x}',True)
for allocated in(0xffffffff,0,7):
 for allocation in(0,h.A):
  for tlsSet in(0,1):
   h.prepare();h.g.tlsIndex=0xffffffff;h.put(h.OS+8,[allocated,tlsSet,allocation]);h.compare(0x4a7d40,label=f'TLS-init/{allocated:x}/{allocation:x}/{tlsSet}',record=True)
print('PASS source init/getter defaults and allocation/TLS-index failures',flush=True)
for mutation in(0,1):
 for thread in(0,h.A):
  for values in((),(0x24,),(0x24,0x28,0x30,0x38,0x40,0x44)):
   for locale in(0,0x5312e8,h.CUSTOM):
    h.prepare();h.mutation=mutation;h.put(h.A+0x50,[locale])
    for n,off in enumerate(values):h.put(h.A+off,[h.CUSTOM+16*n])
    h.compare(0x4a7e40,[thread],f'cleanup/{mutation}/{thread:x}/{values}/{locale:x}',True)
h.prepare();h.g.tlsIndex=0xffffffff;h.compare(0x4a7e40,[h.A],'cleanup-noTLS-index',True)
h.prepare();h.put(h.OS+20,[0]);h.compare(0x4a7e40,[0],'cleanup-empty-current-thread',True)
for fn in(0x4a3040,0x4a3050,0x4a7dc0):
 for allocation in(0,h.A):
  h.prepare();h.put(h.OS+12,[0,allocation,0]);h.compare(fn,[0x1b3cf]if fn==0x4a3040 else[],f'returning-fatal-transport/{fn:x}/{allocation:x}',True) if allocation or fn==0x4a7dc0 else None
print('PASS exact cleanup/fatal-return service ordering without invented reclamation',flush=True)
# One shared raw pointer used directly by the frozen WorldLoot RNG between
# whole original rand calls; multiple independent threads retain distinct state.
for n in range(96):
 h.prepare(n);h.compare(0x4a3040,[0x1b3cf],f'joined-thread-seed/{n}',n==0)
 for tick in range(8):
  h.put(h.OS+4,[1+(tick%2)]);h.compare(0x4a3050,label=f'thread-switch/{n}/{tick}')
  token=h.A if tick%2==0 else h.B;old=h.get(token+0x14)[0];value=h.lib.claw_world_loot_next_random(h.C.cast(h.C.addressof(h.heap)+token+0x14-h.BASE,h.C.POINTER(h.U)));h.m.call(0x4a3050,0);assert h.get(token+0x14)==h.get(token+0x14,native=False)and value==((old*214013+2531011)&0xffffffff)>>16&0x7fff
print('PASS live shared seed alias and independent switched-thread histories',flush=True)
print('PASS',h.calls,h.eventCount,flush=True)
unsafePrefixes=fatalPrefixes=callerPrefixes=0
for fn in(0x4a3040,0x4a3050):
 h.prepare();h.put(h.OS+16,[0,0]);h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();r=h.U(0xabcd);a=(h.U*1)(0x1b3cf);assert not h.lib.claw_crt_random_entry(fn,a if fn==0x4a3040 else None,1 if fn==0x4a3040 else 0,h.C.byref(h.context),h.dependency,None,h.C.byref(r))and h.context.fault==1 and r.value==0xabcd
 try:h.m.call(fn,0,h.pack(0x1b3cf)if fn==0x4a3040 else b'');raise AssertionError('expected original null-thread dereference')
 except h.UcError:pass
 assert h.raw(True)==h.raw(False)and h.globalsRaw(True)==h.globalsRaw(False)and h.native_events==h.original_events;unsafePrefixes+=1
for fn in(0x4a3040,0x4a3050,0x4a7dc0):
 for allocated in(0,h.A):
  h.prepare();h.put(h.OS+12,[0,allocated,0]);h.fatalStop=True;h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();r=h.U(0xabcd);a=(h.U*1)(0x1b3cf);assert not h.lib.claw_crt_random_entry(fn,a if fn==0x4a3040 else None,1 if fn==0x4a3040 else 0,h.C.byref(h.context),h.dependency,None,h.C.byref(r))and h.context.fault==99 and r.value==0xabcd
  try:h.m.call(fn,0,h.pack(0x1b3cf)if fn==0x4a3040 else b'');raise AssertionError('expected explicit fatal service stop')
  except AssertionError as e:assert str(e)=='Original routine exceeded instruction bound'and h.stopped
  assert h.raw(True)==h.raw(False)and h.globalsRaw(True)==h.globalsRaw(False)and h.native_events==h.original_events;fatalPrefixes+=1
h.prepare();old=(h.raw(True),h.g.tlsIndex);r=h.U(123);assert not h.lib.claw_crt_random_entry(0x425730,None,0,h.C.byref(h.context),h.dependency,None,h.C.byref(r))and r.value==123 and old==(h.raw(True),h.g.tlsIndex)
assert not h.lib.claw_crt_random_entry(0x4a3040,None,0,h.C.byref(h.context),h.dependency,None,h.C.byref(r))and h.context.fault==2 and old==(h.raw(True),h.g.tlsIndex)
print('PASS unmapped original thread and exact fatal service prefixes/unsupported guards',flush=True)
# Actual caller instruction prefixes: capture state at real srand entry, then
# compare the whole recovered RNG body against that observed source frame.
# Caller bodies remain unported; no guessed native startup helper is added.
h.m.u.mem_map(0,4096)
TIMEGATE,TICKGATE=0x1100800,0x1100810;h.m.write_words(0x546df0,[TIMEGATE]);h.m.write_words(0x546a24,[TICKGATE]);h.GLOBAL_SEED=bytes(h.m.u.mem_read(h.GLOBAL_START,h.GLOBAL_SIZE))
OWNER=h.BASE+0x7000;APP=h.BASE+0x8000
trace=None;capture=None;sourcePrefix=[];clockValues=(0,0)
def sourceHook(u,address,size,user):
 global capture
 if trace is None:return
 sp=u.reg_read(h.UC_X86_REG_ESP)
 if address in(TIMEGATE,TICKGATE):
  sourcePrefix.append(0x546df0 if address==TIMEGATE else 0x546a24);h.returned(0,clockValues[0 if address==TIMEGATE else 1]);return
 if address==0x4b8280:
  sourcePrefix.append(address);h.returned(8,1);return
 if address==0x4a3040:
  capture=(h.raw(False),h.globalsRaw(False),h.m.read_words(sp+4,1)[0]);h.original_events.clear();return
 if address in(0x42579a,0x46af0e):u.emu_stop()
h.m.u.hook_add(h.UC_HOOK_CODE,sourceHook)
def caller(entry,receiver,args,expectedSeed,label):
 global trace,capture,callerPrefixes
 trace=entry;capture=None;sourcePrefix.clear();h.sync();h.native_events.clear();h.original_events.clear()
 try:h.m.call(entry,receiver,h.pack(*args));raise AssertionError('expected caller prefix stop')
 except AssertionError as e:assert str(e)=='Original routine exceeded instruction bound'
 finally:trace=None
 assert capture is not None and capture[2]==expectedSeed,(label,'source actualseed',capture)
 originalAfter=h.raw(False);originalGlobals=h.globalsRaw(False);originalEvents=list(h.original_events);h.heap[:]=capture[0];priorSeed=h.GLOBAL_SEED;h.GLOBAL_SEED=capture[1];h.g.tlsIndex=h.struct.unpack_from('<I',capture[1],0x52edd8-h.GLOBAL_START)[0];h.context.fault=0;h.native_events.clear();h.errors.clear();values=(h.U*1)(expectedSeed);r=h.U();assert h.lib.claw_crt_random_entry(0x4a3040,values,1,h.C.byref(h.context),h.dependency,None,h.C.byref(r))and not h.context.fault and not h.errors
 assert h.raw(True)==originalAfter and h.globalsRaw(True)==originalGlobals and h.native_events==originalEvents,(label,'whole srand in captured original caller frame')
 h.GLOBAL_SEED=priorSeed;callerPrefixes+=1
for n,clockValues in enumerate(((0,0),(1,1),(0xffffffff,1),(0xffffffff,0xffffffff),(0x80000000,0x80000000),(0x7fffffff,0x80000000))):
 for lazy in(0,1):
  h.prepare(n);h.put(h.OS+20,[0 if lazy else h.A]);h.m.write_words(0,[0x12345678]);caller(0x425730,APP,[0x76543210,0x11223344],((sum(clockValues))&0xffffffff)>>1,f'application-clock-seed/{n}/{lazy}');assert sourcePrefix==[0x4b8280,0x546df0,0x546a24]
for n in range(8):
 h.prepare(n);h.put(OWNER+4,[APP]);h.put(h.OS+20,[0 if n%2 else h.A]);h.m.write_words(0,[0x12345678]);caller(0x46aeb0,OWNER,[n,0],0x1b3cf,f'retail-level-seed/{n}');assert not sourcePrefix
print('PASS actual application and level-start instruction prefixes/source seed order',flush=True)
# Golden output is original-executed, then used by the independent Swift ABI smoke.
h.prepare();h.compare(0x4a3040,[0x1b3cf],'retail-seed-golden',True);golden=[h.compare(0x4a3050,label=f'retail-golden/{i}',record=True)for i in range(16)]
(h.WORK/'retail-random-golden.json').write_text(h.json.dumps({'seed':0x1b3cf,'values':golden,'finalSeed':h.get(h.A+0x14)[0]},indent=2)+'\n')
import gzip
(h.WORK/'replay.bin.gz').write_bytes(gzip.compress(h.replay.getvalue(),compresslevel=6))
addresses={a for a in h.m.executed-set(h.COUNTS)-set(h.GATES)-{h.m.stop,0x4b8280,TIMEGATE,TICKGATE}if 0x400000<=a<0x550000}
report={'wholeCRTRandomCalls':h.calls,'sharedWorldLootAliasStateChecks':96*8,'completeOrderedSnapshots':h.eventCount,'wholeHeapBytes':h.SIZE,'wholeGlobalBytes':h.GLOBAL_SIZE,'originalCallerSeedPrefixes':callerPrefixes,'originalNullThreadPrefixes':unsafePrefixes,'fatalTransportStoppedPrefixes':fatalPrefixes,'originalAddresses':len(addresses),'sanitizerReplayCases':h.replayCases,'originalInstructionAddresses':[hex(a)for a in sorted(addresses)],'transport':'WindowsTLS/GetLastError/GetCurrentThreadId and CRTcalloc/free/lockInit/fatal are exact raw service adapters; fatal returning profiles deliberately exercise source fallthrough and are not claimed retail termination.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k!='originalInstructionAddresses'}),flush=True)
