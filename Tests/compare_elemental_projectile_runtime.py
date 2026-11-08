#!/usr/bin/env python3
import elemental_projectile_runtime_helpers as h
for kind,ctor in enumerate((0x410ec0,0x411370,0x411820)):
 for n in range(30):
  h.fresh(kind);h.g.magicDisabled=n%3==0;h.put(h.OWNER+0x124,[n%2]);h.resource=n%7!=0;h.allocation=n%11!=0;h.compare(ctor,args=[h.A],label=('ctor',kind,n))
 print('PASS',hex(ctor),flush=True)
for kind,(wrapper,dispatcher,flight)in enumerate(((0x410100,0x411030,0x411310),(0x4101c0,0x4114e0,0x4117c0),(0x410280,0x411990,0x411c70))):
 for n in range(60):
  h.fresh(kind);h.put(h.L+28,[[0,29,30,1000,h.stateIDs['LS_FALLING']][n%5]]);h.g.magicDisabled=n%2;h.put(h.OWNER+0x124,[n%3]);h.compare(wrapper,t=0,args=[h.A],label=('wrapper',kind,n))
  h.compare(dispatcher,args=[h.stateIDs['LS_FALLING']],label=('dispatch',kind,n))
  h.collision=0x10000 if n%2 else 0;h.mutation=n%3==0;h.compare(flight,label=('flight',kind,n));h.compare(0x411cd0,label=('cleanup',kind,n));h.compare(0x484d90,args=[n%2],label=('delete',kind,n));assert h.get(h.E+0x154)==[0xabcdef01]
 print('PASS family',kind,flush=True)
print('PASS elemental',h.calls,h.eventsCount,len(h.m.executed),flush=True)
for kind,flight in enumerate((0x411310,0x4117c0,0x411c70)):
 for i,velocity in enumerate((-1e20,-700.,-0.,0.,700.,1e20,float('nan'))):
  for position in(-1e20,-300.75,-0.,0.,300.75,1e20,float('nan')):
   h.fresh(kind);h.dbl(h.E+0x50,velocity);h.dbl(h.E+0x68,position);h.dbl(h.E+0x70,position);h.compare(flight,label=('ftol-offset',kind,i,position))
# Real original PID geometry and ANI groups retained through deferred wrappers,
# actual generic source scheduler, unequal stage/animation clocks and cleanup.
retained=0
for kind,callback in enumerate((0x410100,0x4101c0,0x410280)):
 for direction in(0,1):
  for gate in(0,1):
   h.fresh(kind);h.realResources(kind);h.put(h.A+0x170,[0]);h.put(h.A+0x148,[700 if direction else(-700)&0xffffffff,0]);h.g.magicDisabled=gate;h.put(h.L+28,[0]);h.compare(callback,0,[h.A],('retail-start',kind,direction,gate));assert h.get(h.E+0x154)==[0xabcdef01]
   for frame in range(65):
    h.g.tick+=17;h.g.animationDelta=[0,1,16,17,33,100][frame%6];h.compare(callback,0,[h.A],('retail-flight',kind,direction,gate,frame))
   h.put(h.L+28,[29]);h.compare(callback,0,[h.A],('retail-cleanup',kind,direction,gate))
   if not gate:assert h.get(h.FLARE+8)[0]&0x10000
   h.compare(0x484d90,args=[1],label=('retail-delete',kind,direction,gate));assert h.get(h.E+0x154)==[0xabcdef01];retained+=1
print('PASS retained',retained,h.calls,h.eventsCount,flush=True)
# Original source ranged marker emits all three distinct families. Factory
# transport initializes raw actor fields; registry/constructors run unchanged.
launches=0;collisionHistories=0
for kind,callback in enumerate((0x410100,0x4101c0,0x410280)):
 for direction in(0,1):
  h.fresh(kind);h.realResources(kind);h.launch(kind,direction);assert h.get(h.A+0x164)==[[0x40000,0x100000,0x80000][kind]|8];h.compare(callback,0,[h.A],('source-marker-start',kind,direction),record=True);assert h.get(h.A+0x104)==[25];assert h.get(h.A+0x164)==[[0x40000,0x100000,0x80000][kind]|8|0x2000]
  for frame in range(4):
   h.g.tick+=17;h.compare(callback,0,[h.A],('source-marker-flight',kind,direction,frame),record=frame<2)
  h.put(h.L+28,[29]);h.compare(callback,0,[h.A],('source-marker-cleanup',kind,direction),record=True);h.compare(0x484d90,args=[1],label=('source-marker-delete',kind,direction),record=True);launches+=1
  h.fresh(kind);h.realResources(kind);h.installCollision(True,8 if direction else 2);h.put(h.L+28,[0]);h.put(h.A+0x170,[0]);h.put(h.A+0x148,[700 if direction else(-700)&0xffffffff,0]);h.compare(callback,0,[h.A],('tile-collision-start',kind,direction))
  for frame in range(150):
   h.g.tick+=17;h.compare(callback,0,[h.A],('tile-collision-flight',kind,direction,frame))
   if h.get(h.A+8)[0]&0x10000:break
  assert h.get(h.A+8)[0]&0x10000,('no tile/world delete',kind,direction,frame);h.put(h.L+28,[29]);h.compare(callback,0,[h.A],('tile-collision-cleanup',kind,direction));h.compare(0x484d90,args=[1],label=('tile-collision-delete',kind,direction));collisionHistories+=1
for kind,callback in enumerate((0x410100,0x4101c0,0x410280)):
 h.fresh(kind);h.allocation=0;h.put(h.L+28,[0]);h.failure(callback)
 # A failed optional Flare allocation is legal and retains a null child.
 h.fresh(kind);h.allocation=0;h.compare((0x410ec0,0x411370,0x411820)[kind],args=[h.A],label=('null-optional-flare',kind));assert h.get(h.E+0x150)==[0]
# Actual cdecl scheduler boundary, original source class registry and no extra VT.
for kind,vt in enumerate((0x50b7bc,0x50b80c,0x50b844)):
 h.fresh(kind);h.realResources(kind);h.put(h.L+28,[0]);h.put(h.A+0x170,[0]);h.compare((0x410100,0x4101c0,0x410280)[kind],0,[h.A],('scheduler-start',kind));h.compare(0x4dc870,0,[h.E],('cdecl-scheduler',kind),record=True)
 for slot in range(0,48,4):assert h.lib.claw_elemental_projectile_function(vt,slot)==h.get(vt+slot)[0]
 assert h.lib.claw_elemental_projectile_function(vt,48)==0
# All11 IDs in the actual initialized class range preserve class fallback
# and inherited deletion packets. Out-of-range dynamic growth stays transport.
for kind,dispatcher in enumerate((0x411030,0x4114e0,0x411990)):
 for state in range(2000,2011):
  h.fresh(kind);h.compare(dispatcher,args=[state],label=('registry-dispatch',kind,state))
# Failed array growth plus a returning diagnostics transport reaches original
# invalid default pointer1; this is an unsafe prefix, never successful dispatch.
for kind,dispatcher in enumerate((0x411030,0x4114e0,0x411990)):
 h.fresh(kind);h.failure(dispatcher,h.E,[2011],1)
h.writeCorpus()
report={'originalSHA256':h.m.__class__.__module__,'wholeCalls':h.calls,'fullSnapshots':h.eventsCount,'snapshotBytes':h.SIZE+0x30000,'executedAddresses':len(h.m.executed),'unsafePrefixes':h.prefixes,'resourceHistories':retained,'sourceRangedHistories':launches,'realTileHistories':collisionHistories,'sanitizerReplayCalls':h.replayCases,'assets':h.assetProfile,'stateIDs':h.stateIDs}
report['originalSHA256']='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n')
print('PASS ElementalProjectile',h.calls,'wholecalls',h.eventsCount,'fullsnapshots',len(h.m.executed),'addresses',h.prefixes,'prefixes',flush=True)
