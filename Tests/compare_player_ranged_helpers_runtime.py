#!/usr/bin/env python3
import player_ranged_helpers_runtime_helpers as h
for fn in(0x41c9f0,0x41cab0,0x41cb80,0x41cc60):
 for n in range(400):
  h.prepare(n);h.g.powerup=[0,0x26b8,0x26b9,0x26ba,0x26bb,0xffffffff][n%6];h.found=n%7!=0;h.created=0 if n%11==0 and fn!=0x41cc60 else h.SHOT;h.mutation=n%8;h.put(h.P+112,[[0,1,0xffffffff,0x80000000,0x7fffffff][n%5]]*3);h.put(h.P+0x100,[[0,49,50,51,500,2000,0xffffffff,0x80000000][n%8],50,[0,50,51,2000,0xffffffff,0x80000000][n%6]]);h.put(h.SC+0x930,[n%2]);h.compare(fn,label=f'whole/{fn:x}/{n}',args=[h.A,n*47,h.P],record=n<3)
 print('PASS',hex(fn),flush=True)
print('PASS ranged',h.calls,h.eventsCount,len(h.m.executed))
# Joined actual named creator allocates source1b4 actor/174 primary, inserts it,
# and leaves its true registered callback deferred (40000 has no200000 bit).
for fn in(0x41c9f0,0x41cab0,0x41cb80,0x41cc60):
 for n in range(24):
  h.prepare(n);h.ctx.composeCreation=h.ctx.composeImages=1;h.found=n%7!=0;h.g.powerup=[0x26b8,0x26b9,0x26ba][n%3]
  if fn==0x41cc60 and not h.found:continue
  h.compare(fn,label=f'joined/{fn:x}/{n}',record=n<2)
for n in range(12):
 h.prepare(n);h.ctx.composeImages=1;h.found=n%2==0;h.put(h.IMAGE+100,[-1 if n%3==0 else 0 if n%3==1 else 1,5]);h.compare(0x41c9f0,label=f'images/{n}',record=n<2)
# Raw aliased creation result is an explicit allocator profile. All stores and
# live rereads still agree with original when the created actor is the player.
for fn in(0x41c9f0,0x41cab0,0x41cb80,0x41cc60):
 for n in range(8):
  h.prepare(n);h.created=h.A;h.g.powerup=0x26b8;h.mutation=n;h.compare(fn,label=f'alias/{fn:x}/{n}')
# Exact retail ANI records elect emission, deduplication, optional source seek
# and both standing/duck marker5. Collision election is an explicit grounded
# transport; these caller tests do not claim physical whole-level acceptance.
histories=0;observedNames=set()
for direction in(0,1):
 for file,weapon,fn in(('DUCKPISTOL.ANI',1,0x419fd0),('DUCKMAGIC.ANI',2,0x419fd0),('DUCKPOSTDYNAMITE.ANI',3,0x419fd0),('DUCKPOWERUPSWIPE.ANI',0,0x419fd0),('POWERUPSWIPE.ANI',0,0x41c5a0)):
  h.prepare(direction);h.ctx.composeCreation=h.ctx.composeImages=1;h.g.powerup=0x26b8;h.playerANI(file);h.put(h.P+48,[weapon]);h.put(h.P+60,[14 if weapon==1 else 15 if weapon==2 else 16 if weapon==3 else 7]);h.put(h.P+108,[2]);h.put(h.P+32,[0]);h.put(h.L+28,[26 if fn==0x419fd0 else 24]);h.capture=False
  for frame in range(140):
   if weapon==1:h.put(h.BASE+0x1e000+4,[0x40])
   h.compareCaller(fn,f'ANI/{direction}/{file}/{frame}')
   for event in h.nativeEvents:
    if event[0]==0x4f6286 and event[3]in(b'PistolBullet',b'MagicBullet',b'Dynamite',b'FireBullet'):observedNames.add(event[3].decode())
   if not h.get(h.P+4)[0]:break
  if weapon==1:assert h.get(h.P+112)[0]<10 and h.get(h.P+0xe8)[0]>42
  if weapon==2:assert h.get(h.P+116)==[19]
  if weapon==3:assert h.get(h.P+120)==[29]
  histories+=1
h.composeAnimation=False
# Original trap and unchecked element-allocation paths, with physical FS/TEB
# distinct from the null page. No fake normal success is accepted.
prefixes=0
for powerup in(0x26b8,0x26b9,0x26ba):
 h.prepare();h.g.powerup=powerup;h.created=0;h.failure(0x41cc60,f'element-null/{powerup:x}',1);prefixes+=1
h.prepare();h.put(h.P+0x100,[0x10000000,0,0xffffffff]);h.failure(0x41cb80,'signed-idiv-overflow',2);prefixes+=1
for fn,stop in((0x41c9f0,0x4c8da0),(0x41c9f0,0x4c7970),(0x41cc60,0x4f6286),(0x41cc60,0x4208e0)):
 h.prepare(1);h.cancelFunction=stop;h.failure(fn,f'cancel/{fn:x}/{stop:x}',77);prefixes+=1
h.writeCorpus()
import json
report={'sourceSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','wholeOriginalCalls':h.calls,'orderedFullSnapshots':h.eventsCount,'executedOriginalAddresses':len(h.m.executed),'rawBytesPerSnapshot':h.SIZE+h.GN,'realANIHistories':histories,'observedSourceEmissionNames':sorted(observedNames),'unsafePrefixes':prefixes,'sanitizerReplayCases':h.replayCases};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');(h.WORK/'asset-profile.json').write_text(json.dumps(h.assetProfile,indent=2)+'\n');print('PASS PlayerRangedHelpers',json.dumps(report),flush=True)
