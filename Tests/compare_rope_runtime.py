#!/usr/bin/env python3
import rope_runtime_helpers as h
for fn in(0x4031c0,0x403ab0,0x403ac0,0x4035a0,0x403850,0x4038d0,0x465450):
 for n in range(24):
  h.prepare(n);h.g.tick=n*33;h.mutation=n%2
  args=[h.A]if fn==0x4031c0 else[2000]if fn==0x4035a0 else[h.NAME_CHARS]if fn==0x403850 else[]
  h.compare(fn,h.E,args,f'rope-body/{fn:x}/{n}',void=fn in(0x4035a0,0x403850))
 print('PASS',hex(fn),flush=True)
for fn in(0x4181c0,0x41ee60,0x415df0):
 for n in range(32):
  h.prepare(n);h.put(h.PR+0x134,[h.A]);h.put(h.PL+28,[5007]);h.put(h.PR,[n%2]);h.put(h.INPUT+4,[n%2,0,0xffffffff]);h.put(h.PR+0x114,[n%3]);h.pg.powerup=0x26bc if n%4==0 else 0;h.put(h.A+0xfc,[0x26af]);h.put(h.PL+0x130,[n%20]);h.g.cheat=n%5==0;h.g.ignoreHazards=n%3==0
  args=[h.PLAYER,h.PL,h.PR]+([h.A]if fn==0x41ee60 else[])if fn!=0x415df0 else[h.PLAYER]
  h.compare(fn,args=args,label=f'player/{fn:x}/{n}',void=fn!=0x415df0)
 print('PASS player',hex(fn),flush=True)
for period in(0,1,2,1500,1200,-1,-1500,0x7fffffff,0x80000000):
 for phase in(0,1,0xffffffff,0x7fffffff,0x80000000):
  h.prepare();h.put(h.A+0x148,[period]);h.put(h.L+0xbc,[phase]);h.compare(0x4031c0,h.E,[h.A],f'signed-period-and-wrapped-phase/{period}/{phase}')
for position in(0,1,59,60,61,119,120,239,-1,-120,0x7fffffff,4294967296.,float('nan'),float('inf')):
 h.prepare();h.number(h.E+0x88,position);h.put(h.PR+0x134,[h.A]);h.put(h.PL+28,[5007]);h.compare(0x4038d0,h.E,label=f'original-frame-index/{position}')
for state in(0,2000,29,30,1000):
 h.prepare();h.put(h.L+28,[state]);h.compare(0x403100,args=[h.A],label=f'registered-actor-dispatch/{state}')
for n in range(16):
 h.prepare(n);h.put(h.E+0x14,[h.FAKEA,h.FAKEA,2000]);h.compare(0x403850,h.E,[h.registryIdleToken],f'queued-callback-mutations/{n}',void=True)
print('PASS signed periods, full modulo image/geometry branches, registry heap names and callback mutations',flush=True)
for distance in(-0x80000000,-49,-48,-47,0,47,48,49):
 for motion in(1,3,4,8):
  for cooldown in(0,1):
   h.prepare();h.put(h.A+0xfc,[0x26af]);h.put(h.A+0xd0,[0x100]);h.put(h.PLAYER+0xcc,[motion]);h.put(h.PLAYER+80,[1200+27+16+distance]);h.put(h.PR+0x11c,[cooldown]);h.put(h.PR+0x134,[h.A]);h.put(h.PLAYER+0x74,[h.A]);h.compare(0x41ce80,args=[h.PLAYER],label=f'CaptainClawHit-grab-gates/{distance}/{motion}/{cooldown}')
print('PASS whole elected CaptainClawHit→frozen41ee60 exact motion/distance/cooldown gates',flush=True)
for row in h.profile['records']:
 h.prepare(row['index']);h.actualRecord(row);h.compare(0x403100,args=[h.A],label=f'WWD/{row["level"]}/{row["index"]}/ctor');assert h.get(h.L+24)==[h.E]and h.get(h.L+28)==[2000]
 for tick in(0,33,67,101,250,500):h.g.tick=tick;h.compare(0x403100,args=[h.A],label=f'WWD/{row["level"]}/{row["index"]}/unheld-frame{tick}')
 h.put(h.PL+28,[4]);h.put(h.PLAYER+0xcc,[3]);h.put(h.PLAYER+0x74,[h.A]);h.put(h.PLAYER+80,[h.get(h.A+80)[0]+h.get(h.E+0x144)[0]+16]);h.put(h.PR+0x11c,[0]);h.put(h.PR+0x134,[0]);h.compare(0x41ce80,args=[h.PLAYER],label=f'WWD/{row["level"]}/{row["index"]}/elected-grab');assert h.get(h.PL+28)==[5007]
 for tick in(533,567,601,750,1000):
  h.g.tick=tick;h.compare(0x403100,args=[h.A],label=f'WWD/{row["level"]}/{row["index"]}/swing-rope{tick}');h.compare(0x415df0,args=[h.PLAYER],label=f'WWD/{row["level"]}/{row["index"]}/swing-player{tick}')
 h.put(h.INPUT+4,[1]);h.compare(0x415df0,args=[h.PLAYER],label=f'WWD/{row["level"]}/{row["index"]}/jump-release');assert h.get(h.PL+28)==[4]and h.get(h.PR+0x11c)==[482];h.compare(0x41ce80,args=[h.PLAYER],label=f'WWD/{row["level"]}/{row["index"]}/same-rope-cooldown');assert h.get(h.PL+28)==[4]
 h.compare(0x484d90,h.E,[1],label=f'WWD/{row["level"]}/{row["index"]}/private-delete')
print('PASS all137 original-disc AniRope WWD/real120PID headers retained startup→swing→grab→player→release→cooldown→destroy',flush=True)
for n in range(16):
 h.prepare(n);h.actualRecord(h.profile['records'][n]);h.actualAnimation();h.compare(0x403100,args=[h.A],label=f'actualANI/{n}/ctor');h.put(h.PLAYER+0x74,[h.A]);h.put(h.PLAYER+0xcc,[3]);h.put(h.PLAYER+80,[h.get(h.A+80)[0]+43]);h.compare(0x41ce80,args=[h.PLAYER],label=f'actualANI/{n}/grab')
 for tick in range(0,700,35):
  h.g.tick=tick;h.ani.animationDelta=35;h.g.stageDelta=17;h.compare(0x403100,args=[h.A],label=f'actualANI/{n}/rope/{tick}');h.compare(0x415df0,args=[h.PLAYER],label=f'actualANI/{n}/player/{tick}')
 h.put(h.INPUT+4,[1]);h.compare(0x415df0,args=[h.PLAYER],label=f'actualANI/{n}/release');assert h.get(h.PL+28)==[4]
print('PASS real retail SWING/JUMP ANI composed records, PID image tokens and asymmetric35/17ms retained swing/release',flush=True)
for n in range(24):
 h.prepare(n);h.composeHeld(n);h.compare(0x4181c0,args=[h.PLAYER,h.PL,h.PR],label=f'held-target-release/{n}',void=True);assert h.get(h.PR+0x12c)==[0]and h.get(h.TE+0x300)[0]&1
 h.prepare(n);h.composeHeld(n);h.put(h.INPUT+4,[0]);h.put(h.PLAYER+0xcc,[3]);h.put(h.PLAYER+80,[1243]);h.compare(0x41ce80,args=[h.PLAYER],label=f'held-target-grab-cleanup/{n}');assert h.get(h.PR+0x12c)==[0]
print('PASS composed frozen held-target queue/bitset and saved animation cleanup across grab/release',flush=True)
for tick in(0,0x7fffffff,0x80000000,0xffffffff):
 for previous in(0,1,-1,4294967.295):
  h.prepare();h.g.tick=tick;h.number(h.E+0x48,previous);h.compare(0x403850,h.E,[h.registryIdleToken],f'unsigned-tick/{tick:x}/elapsed{previous}',void=True)
print('PASS unsigned full32bit tick and previous elapsed profiles',flush=True)
# Exact reached prefixes where the native safety guard prevents an original
# invalid pointer/table access; these are distinct from completed whole calls.
prefixes=0
for kind in('allocation-null','missing-held-rope','negative-table-index'):
 h.prepare();fn=0x403100;receiver=0;args=[h.A];stop=None
 if kind=='allocation-null':h.put(h.L+28,[0]);h.allocation=0;stop=0x40315e
 if kind=='missing-held-rope':fn=0x4181c0;args=[h.PLAYER,h.PL,h.PR];h.put(h.PR+0x134,[0]);stop=0x41820e
 if kind=='negative-table-index':fn=0x4038d0;receiver=h.E;args=[];h.number(h.E+0x88,-2);stop=0x4039b8
 h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();out=h.U(0xabcd);a=(h.U*len(args))(*args);assert not h.lib.claw_rope_entry(fn,receiver,a,len(args),h.C.byref(h.c),h.dependency,None,h.C.byref(out))and h.c.fault==(2 if kind=='negative-table-index'else 1)and out.value==0xabcd
 seen=[]
 def stopHook(u,at,size,user):
  if at==stop:seen.append(at);u.emu_stop()
 hookID=h.m.u.hook_add(h.UC_HOOK_CODE,stopHook)if stop else None
 try:
  h.m.call(fn,receiver,h.pack(*args));raise AssertionError('expected original unsafe prefix')
 except h.UcError:assert stop is None
 except AssertionError as e:assert stop and seen==[stop]and str(e)=='Original routine exceeded instruction bound'
 finally:
  if hookID:h.m.u.hook_del(hookID)
 assert h.raw(True)==h.raw(False)and h.native_events==h.original_events,kind;prefixes+=1
for state in(1999,2011,0x80000000,0x7fffffff):
 h.prepare();h.put(0x534820+20,[h.CLASS_DATA+0x100]);h.put(h.CLASS_DATA+0x100,[0]);h.compare(0x4035a0,h.E,[state],f'class-missing-state/{state}',void=True)
h.prepare();before=h.raw(True);out=h.U(123)
assert not h.lib.claw_rope_entry(0x415df0,0,(h.U*1)(h.PLAYER),1,h.C.byref(h.c),h.dependency,None,h.C.byref(out))and out.value==123 and before==h.raw(True)
assert not h.lib.claw_rope_entry(0x403100,0,None,0,h.C.byref(h.c),h.dependency,None,h.C.byref(out))and h.c.fault==2 and before==h.raw(True)
import gzip,json
(h.WORK/'rope-replay.bin.gz').write_bytes(gzip.compress(h.replay.getvalue()));verification={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','wholeCalls':h.calls,'orderedFullSnapshots':h.eventsCount,'distinctOriginalInstructions':len(h.m.executed),'retailWWDRows':len(h.profile['records']),'actualWWDLoaderProfiles':h.loaderProfiles,'retailANIRecordDecodeCalls':h.aniDecodes,'retailANIHashes':h.aniSourceHashes,'sourceRegistryHeapBytes':h.registryHeapUsed,'guardedOriginalPrefixes':prefixes,'replayCases':h.replayCases,'heapBytes':h.SIZE,'globalBytes':h.GLOBAL_SIZE,'replayStateBytes':len(h.replayState()),'retailPIDHeaders':sum(len(r['headers'])for r in h.profile['resources']),'physicalBoundaries':'allocator/resources/dictionary/audio, explicit hazard/election; retained player placement synthetic'};(h.WORK/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('PASS',verification,flush=True)
