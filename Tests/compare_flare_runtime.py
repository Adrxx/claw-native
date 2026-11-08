#!/usr/bin/env python3
"""Whole original Flare/WolvingtonLFX source with complete raw effects."""
import flare_runtime_helpers as h
import random,struct,json
r=random.Random(0x457f00)
for seed in range(200):
 h.setup(seed);h.compare(0x458120,h.E,[h.A]);h.compare(0x4581c0,h.E);h.compare(0x458530,h.E);h.compare(0x458570,h.E);h.compare(0x458280,h.E,[2000])
for callback in(0x457f00,0x458010):
 for seed in range(64):
  h.setup(seed);h.put(h.L+28,[0]);h.allocationNull=False;h.lookupResult=h.SEQ if seed%3 else 0;h.put(h.CONFIG+0x768,[0 if seed%2 else h.BASE+0x70000]);h.ctx.composeEffects=1;h.put(0x5430b0,list(h.ig.compressedEffect));h.compare(callback,0,[h.A]);h.compare(callback,0,[h.A]);h.compare(0x4041b0,h.E,[h.NAME]);h.put(h.L+28,[r.choice([29,30,1000])]);h.compare(callback,0,[h.A]);h.compare(0x484d90,h.E,[seed%2])
# Pointer setter: signed range, empty/missing frames and zero no-op semantics.
for seed in range(160):
 h.setup(seed);first,last=r.choice([(0,0),(1,1),(0,4),(4,1),(1,4)]);h.put(h.ROOTIMAGE+100,[first,last]);h.put(h.TABLE,[0 if seed%2 else h.IMAGE,h.IMAGE,0,h.IMAGE+128,h.IMAGE]);h.put(h.IMAGE+128+48,[0 if seed%3 else h.COMP+64]);h.compare(0x4ce850,h.ROOTIMAGE,[0 if seed%7==0 else r.getrandbits(32)])
# Class fallback/error order and callback alias behavior remain explicit.
for state,fn in[(2000,0x458570),(2000,0),(1999,0),(2001,0),(0xffffffff,0)]:
 h.setup();h.put(h.FUNCS,[fn]);h.compare(0x458280,h.E,[state])
h.setup();h.policy=5;h.put(h.L+28,[0]);h.compare(0x457f00,0,[h.A]);assert h.get(h.L+24)[0]==h.E
# Real both GAME resources, records decoded by unchanged original4d76e0.
assets=[];retained=0
for callback,name in[(0x457f00,'FLARE'),(0x458010,'WOLVINGTONLFX')]:
 for profile in range(8):
  h.setup(profile);ani=h.ROOT/f'work/original-disc-assets/GAME/ANIS/LIGHTFX/{name}.ANI';pid=h.ROOT/f'work/original-disc-assets/GAME/IMAGES/LIGHTFX/{name}/FRAME001.PID';count=h.decodeFile(ani,pid);h.put(h.L+28,[0]);h.lookupResult=h.SEQ;h.put(h.CONFIG+0x768,[0 if profile%2 else h.BASE+0x71000]);h.compare(callback,0,[h.A])
  for frame in range(180):
   h.put(0x5430c4,[[0,1,18,33,200][frame%5]]);h.anim.animationDelta=h.get(0x5430c4)[0]
   if frame%47==0:h.put(h.A+0x1b0,[[0x3f800000,0x3f000000,0x40000000][profile%3]])
   # Parent projectile owns position, mirrored drawflags and deleted status.
   h.put(h.A+76,[800+frame*3,1100+profile]);h.put(h.A+64,[4000+profile]);h.compare(callback,0,[h.A]);retained+=1
  h.put(h.E+20,[0x458530,0x458570,2000]);h.compare(0x4041b0,h.E,[h.NAME]);h.put(h.L+28,[29]);h.compare(callback,0,[h.A]);h.put(h.L+28,[30]);h.compare(callback,0,[h.A]);h.compare(0x484d90,h.E,[profile%2])
 assets.append({'callback':hex(callback),'name':name,'ANI':str(ani.relative_to(h.ROOT)),'PID':str(pid.relative_to(h.ROOT)),'records':count})
for callback,stop in[(0x457f00,0x457fab),(0x458010,0x4580bb)]:
 h.setup();h.put(h.L+28,[0]);h.allocationNull=True;h.comparePrefix(callback,0,[h.A],stop);assert h.get(h.L+28)[0]==1000
# Composed empty/missing sequence follows original harmless early ANI return.
for callback,name in[(0x457f00,'FLARE'),(0x458010,'WOLVINGTONLFX')]:
 h.setup();ani=h.ROOT/f'work/original-disc-assets/GAME/ANIS/LIGHTFX/{name}.ANI';pid=h.ROOT/f'work/original-disc-assets/GAME/IMAGES/LIGHTFX/{name}/FRAME001.PID';h.decodeFile(ani,pid);h.lookupResult=0;h.put(h.L+28,[0]);h.compare(callback,0,[h.A]);h.compare(callback,0,[h.A]);h.put(h.A+0x18c,[0]);h.compare(0x458570,h.E)
# Name/class growth retains source constructor/getter and dispatch ordering.
h.setup();h.put(h.L+28,[2010]);h.registryGrow=True;h.compare(0x457f00,0,[h.A])
report={'pairedCalls':h.calls//2,'orderedPairedSnapshots':h.snapshots//2,'originalAddresses':len(h.m.executed),'actualGAME':assets,'retainedActualResourceFrames':retained,'sourceDecodedANIRecords':h.decodes,'unsafePrefixes':h.prefixes,'heapBytes':h.SIZE,'globalBytes':h.GN}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='actualGAME'}))
