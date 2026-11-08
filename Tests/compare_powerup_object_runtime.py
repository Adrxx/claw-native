#!/usr/bin/env python3
import powerup_object_runtime_helpers as h
for seed in range(80):
 for fn in(0x470430,0x470a20):
  h.modeValues=[3];h.prepareObject(seed,fn);h.put(h.IL+28,[h.rng.choice([0,5,29,9000,9001,1,0xffffffff])]);h.compareObject(fn,[h.ITEM],f'callback/{fn:x}/{seed}')
print('PASS initial callback profiles',flush=True)

# All special selector IDs use source raw words, not guessed public labels.
for old in(0,0x26b7,0x26b8,0x26b9,0x26ba,0x26bc,0x26bd):
 for power in range(0x26ad,0x26bf):
  for iteration in range(6):
   h.modeValues=[3];h.prepareObject(iteration);h.g.powerup=old;h.g.remaining=750;h.put(h.ITEM+0xfc,[power]);h.put(h.ITEM+0x108,[h.rng.choice([0,1,30000,0x80000000,0xffffffff])]);h.put(h.ITEM+0x104,[h.rng.choice([0,1,0xffffffff])]);h.put(h.ITEM+0x148,[400,500]);h.put(h.IL+0x168,[h.SOUND]);h.put(h.P+124,[h.rng.choice([-1,0,9,10,11,0x7fffffff])]);h.put(h.A+80,[220]);h.put(h.IL+24,[h.THIRD]);h.compareObject(0x41ee60,[h.A,h.L,h.P,h.ITEM],f'selector/{old:x}/{power:x}/{iteration}',void=True)
print('PASS selector type/duration/persistence/life matrix',flush=True)
# Retail singleplayer getter runs its original literal body, while mode4
# acceptance/cancel/resource outcomes remain a separate declared profile.
for modeSequence in([3],[4],[4,3]):
 for enabled in(0,1):
  for image in('GAME_POWERUPS_EXTRALIFE','GAME_WARP','GAME_CURSES_HEALTH','GAME_TREASURE_COINS'):
   for f in(0x470430,0x470a20):
    h.modeValues=modeSequence;h.prepareObject(44,f,image);h.oc.curseEnabled=enabled;h.compareObject(f,[h.ITEM],f'gates/{modeSequence}/{enabled}/{image}/{f:x}')
for f in(0x470430,0x470a20):
 h.modeValues=[3];h.prepareObject(111,f);h.put(h.CONFIG,[0x50c264]);h.compareObject(f,[h.ITEM],f'actual-singleplayer-vtable/{f:x}')
print('PASS mode gates and actual singleplayer vtable',flush=True)

for cfg in(0,1,13):
 h.modeValues=[3];h.prepareObject(456,0x470430,'GAME_MAPPIECE');h.loot.configurationWord=cfg;h.loot.words[340]=0
 h.compareObject(0x470430,[h.ITEM],f'lazy-original4719e0/config{cfg}')
 if cfg==1:assert h.get(h.ITEM+0xfc)==[0x26ad]
print('PASS whole lazy4719e0 configuration0/1/13',flush=True)

assets=h.assets();records=h.json.loads((h.WORK/'level1-records.json').read_text());assert len(records)==18
histories=0
for r in records:
 f=0x470430 if r['strings'][1]=='SpecialPowerup'else 0x470a20
 h.disableAnimation();h.modeValues=[3];h.prepareObject(r['index'],f,r['strings'][2]);h.sourceRecord(r);h.put(h.CONFIG,[0x50c264]);h.loot.configurationWord=1;h.loot.words[340]=0
 h.bindRealImages(r['strings'][2],r['words'][8],assets,f'actual/{r["index"]}')
 h.installANI(assets['GAME/ANIS/POWERUP.ANI']);h.enableAnimation()
 h.compareObject(f,[h.ITEM],f'actual/{r["index"]}/initialize')
 if f==0x470a20:
  assert h.get(h.ITEM+8)[0]&0x10000 and h.get(h.IL+28)==[0]
  continue
 assert h.get(h.IL+28)==[5];assert h.get(h.ITEM+0xfc)[0]in(0x26ad,0x26ae,0x26be)
 for tick in range(12):
  h.items.stageDelta=[0,1,16,33,99,100,18,250,400,500,1,16][tick];h.animation.animationDelta=[0,1,16,80,33,99,1,18,40,100,16,33][tick]
  if tick==3:
   h.put(h.A+0x74,[h.ITEM]);h.compareObject(0x41ce80,[h.A],f'actual/{r["index"]}/CaptainClawHit',award=True)
  h.compareObject(f,[h.ITEM],f'actual/{r["index"]}/tick{tick}');histories+=1
h.disableAnimation()
print(f'PASS all18 actualLevel1 records/source image bindings/ANI decode, {histories} retained ticks and CaptainClawHit',flush=True)
for r in records:
 for fail in(False,True):
  h.prepareObject(r['index']);h.constructor(r,fail)
print('PASS 18 source generic constructor/derived caller+init and safe primary allocation failures',flush=True)
for iteration in range(80):
 h.modeValues=[4];h.prepareObject(iteration,0x470a20,'GAME_CURSES_HEALTH');h.glitterFound=bool(iteration%2);h.lookupFound=bool(iteration%3)
 h.put(h.CURSELIST+4,[h.NODE]);h.put(h.NODE,[h.NODE+32,0,h.PAIR]);h.put(h.NODE+32,[0,h.NODE,h.PAIR+16]);h.put(h.PAIR,[100,201]);h.put(h.PAIR+16,[100,200 if iteration%2 else 201])
 h.compareObject(0x470a20,[h.ITEM],f'multiplayer-curse/{iteration}/init')
 for tick in range(3):h.compareObject(0x470a20,[h.ITEM],f'multiplayer-curse/{iteration}/tick{tick}')
 h.put(h.IL+28,[29]);glitter=h.get(h.ITEM+200)[0];h.compareObject(0x470a20,[h.ITEM],f'multiplayer-curse/{iteration}/delete');assert h.get(h.ITEM+200)==[glitter]
 h.compareObject(0x436860,[100,200],f'CPtrList-coordinate-scan/{iteration}',receiver=h.CURSELIST)
h.glitterFound=h.lookupFound=True
for life in(-1,0,9,10,11,0x7fffffff,0x80000000,0xffffffff):
 for audio in(0,1):
  h.modeValues=[3];h.prepareObject(life&0xffff);h.put(h.P+124,[life]);h.items.audioEnabled=audio;h.put(h.ITEM+0xfc,[0x26be]);h.put(h.ITEM+0xd0,[0x100]);h.compareObject(0x41ce80,[h.A],f'ExtraLife-hit/{life}/{audio}',award=True);assert h.get(h.P+124)[0]==((life+1)&0xffffffff if h.C.c_int32(life).value<10 else life&0xffffffff)
for oldStatus in(0,8,9,10,18):
 for armed in(0,h.THIRD):
  for x,y in((100,200),(0,200),(100,0),(0x80000000,0xffffffff)):
   h.prepareObject(8);h.put(h.ITEM+0xfc,[0x26ae]);h.put(h.ITEM+0x148,[x,y]);h.put(h.P+60,[oldStatus]);h.put(h.P+300,[armed]);h.compareObject(0x41ee60,[h.A,h.L,h.P,h.ITEM],f'warp/{oldStatus}/{armed}/{x}/{y}',void=True)
for distance in(-0x80000000,-49,-48,-47,0,47,48,49):
 for facing in(0,1):
  h.prepareObject(4);h.put(h.ITEM+0xfc,[0x26af]);h.put(h.P+0x11c,[0]);h.put(h.A+80,[200+16+distance]);h.put(h.P,[facing]);h.compareObject(0x41ee60,[h.A,h.L,h.P,h.ITEM],f'rope/{distance}/{facing}',void=True)
for typ in(0x26b7,0x26b8,0x26b9,0x26ba,0x26bd):
 for persistent in(0,1):
  h.prepareObject(22);h.g.powerup=0;h.g.remaining=0;h.put(h.ITEM+0xfc,[typ]);h.put(h.ITEM+0x108,[150]);h.put(h.ITEM+0x104,[persistent]);h.put(h.ITEM+0xd0,[0x100]);h.compareObject(0x41ce80,[h.A],f'powerup-hit/{typ}/{persistent}',award=True)
  for delta in(0,1,99,50,1,30000):h.compare(0x41fc30,[h.A,h.L,h.P,delta],f'joined-expiry/{typ}/{persistent}/{delta}')
  assert h.g.powerup==0 and h.g.remaining==0
print('PASS directed curse/list/deletion, signed life cap, warp/rope and hit→powerup→expiry/reset histories',flush=True)
for seed in range(64):
 for f in(0x470430,0x470a20):
  h.prepareObject(seed,f);h.put(h.IL+28,[h.rng.choice([0,5,29,9000,9001])]);h.put(h.ITEM+200,[h.NEWGLITTER]);h.put(h.ITEM+0x174,[0]);h.put(h.ITEM+0x190,[h.rng.choice([0,h.SEQ])]);h.put(h.IL+0x16c,[0]);h.lookupFound=h.glitterFound=bool(seed%2);h.items.stageDelta=h.rng.choice([0,1,399,400,0x80000000,0xffffffff]);h.animation.animationDelta=h.rng.choice([0,17,93,0xffffffff]);h.compareObject(f,[h.ITEM],f'nullable-resources/{f:x}/{seed}')
h.lookupFound=h.glitterFound=True
for seed in range(32):
 h.prepareObject(seed);h.put(h.P,[seed%2]);h.compareObject(0x417050,[h.A,h.P],f'sanitizer/actual-hit-rect/{seed}',void=True);h.compareObject(0x4170b0,[h.A],f'sanitizer/actual-move-rect/{seed}',void=True);h.compareObject(0x40af90,[],f'sanitizer/singleplayer-mode/{seed}',receiver=h.CONFIG)
print('PASS nullable resources/ANI/creator outcomes, wrapped timers and exact rectangle entries',flush=True)
for policy in(3,4):
 for seed in range(16):
  for f in(0x470430,0x470a20):
   h.prepareObject(seed,f,'GAME_TREASURE_COINS');h.modeValues=[4];h.mutation=policy;h.compareObject(f,[h.ITEM],f'reentrant-resource/{policy}/{seed}/{f:x}')
for typ in(0x26ad,0x26b7,0x26b8,0x26b9,0x26ba,0x26bd,0x26be):
 h.prepareObject(44);h.mutation=3;h.put(h.ITEM+0xfc,[typ]);h.put(h.ITEM+0x108,[30000]);h.put(h.ITEM+0x104,[1]);h.compareObject(0x41ee60,[h.A,h.L,h.P,h.ITEM],f'reentrant-audio/{typ}',void=True)
h.mutation=0
print('PASS reentrant ANI/image lookup/audio mutation and post-service item reads',flush=True)
from unicorn import UcError
for slot in(0x6c,0x174):
 h.prepareObject(42);h.put(h.ITEM+slot,[0x7000000]);h.original_updates();h.sync();h.native_events.clear();h.original_events.clear();a=h.ObjectArgs();a.count=1;a.words[0]=h.ITEM;r=h.U();h.oc.fault=0
 done=h.lib.claw_powerup_object_entry(0x470430,0,a,h.C.byref(h.oc),h.objectDependency,None,h.C.byref(r));assert done==0 and h.oc.fault==1
 try:h.m.call(0x470430,0,h.struct.pack('<I',h.ITEM));raise AssertionError('invalid original graph unexpectedly returned')
 except UcError:pass
 assert h.raw(True)==h.raw(False)and h.global_raw(True)==h.global_raw(False)and h.native_events==h.original_events,('unsafe original prefix',slot);h.unsafePrefixes+=1
h.prepareObject(0);before=h.raw(True);a=h.ObjectArgs();r=h.U(123);h.oc.fault=0
assert not h.lib.claw_powerup_object_entry(0x41ebd0,0,a,h.C.byref(h.oc),h.objectDependency,None,h.C.byref(r))and not h.oc.fault and h.raw(True)==before and r.value==123
a.count=6;assert not h.lib.claw_powerup_object_entry(0x470430,0,a,h.C.byref(h.oc),h.objectDependency,None,h.C.byref(r))and h.oc.fault==2 and h.raw(True)==before
import gzip
(h.WORK/'replay.bin.gz').write_bytes(gzip.compress(h.replay.getvalue(),compresslevel=6))
adapted=(set(h.COUNTS)-{0x4c6130})|{0x4f6286,0x4f63ec,h.POST,0x41c4e0};addresses={a for a in h.m.executed-adapted-{h.m.stop}if 0x400000<=a<0x550000}
report={'completeObjectAndSelectorCalls':h.object_calls,'wholePowerupTimerCalls':h.calls,'genericConstructorCallerAndInitializationProfiles':h.constructorCalls,'orderedCompleteHeapGlobalEvents':h.object_events+h.events,'sourceImageBindingCalls':h.bindingCalls,'actualANIRecordDecodes':h.decodedCalls,'originalInstructionAddresses':len(addresses),'heapBytes':h.SIZE,'globalImageBytes':h.GLOBAL_SIZE,'actualLevel1Objects':18,'retainedActualSpecialTicks':histories,'unsafeOriginalFaultPrefixes':h.unsafePrefixes,'sanitizerReplayCases':h.replayCases,'resourceProfiles':list({h.json.dumps(v,sort_keys=True):v for v in h.resourceEvidence}.values()),'originalAddresses':[hex(a)for a in sorted(addresses)],'adaptedServices':[hex(a)for a in sorted(adapted)],'level1ConfigurationWord':1,'actualLevel1CurseRejections':8,'scope':'Whole registered Special470430/Curse470a20, selector41ee60 and finite helper bodies; original resource/platform/rope/multiplayer transports explicit.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n');print(h.json.dumps({k:v for k,v in report.items()if k not in('resourceProfiles','originalAddresses')}),flush=True)
