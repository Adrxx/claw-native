#!/usr/bin/env python3
"""Original whole-root, service ordering and composed impact lifetimes."""
import ctypes as C,itertools,json,struct
import impact_particle_runtime_helpers as h

def composed(assets=False):
 h.prepare();h.ctx.composeCreation=h.ctx.composeAnimation=1;h.mode=1;h.realRNG=True
 if assets:h.installAssets()

# Finite branch inventory and preservation of all nonparticipating raw words.
for fn,states in ((0x461a90,[0,5,1,4,6,29,99,0xffffffff,0x80000000]),(0x461bc0,[0,5,1,4,6,29,99,0xffffffff,0x80000000])):
 for state,stopped,index in itertools.product(states,[0,1,2,0xffffffff],[0,1,5,0xffffffff]):
  h.prepare();h.put(h.L+0x1c,[state]);h.put(h.A+0x1a4,[stopped]);h.put(h.A+0x19c,[index]);h.compare(fn,[h.A],label=('branches',hex(fn),state,stopped,index))
for source,flags,draw in itertools.product([0,h.SOURCE],[0,0x10000,0x21,0xffffffff],[0,1,0xffffffff,0x80000000]):
 for fn in(0x461a00,0x461a90):
  h.prepare();h.put(h.SOURCE+8,[flags]);h.put(h.SOURCE+0x38,[draw]);h.put(h.A+0x80,[source]);args=[h.SC,350,270,4001,0,source]if fn==0x461a00 else[h.A];h.compare(fn,args,label=('source-gates',hex(fn),source,flags,draw))
for value in [0,1,2,3,4,5,6,0x7fff,0x7fffffff,0x80000000,0x80000001,0xfffffffd,0xfffffffe,0xffffffff]:
 h.prepare();h.randomWord=value;h.compare(0x461a90,[h.A],label=('signed-remainder-adapter',value))
for style,missing in itertools.product([0,1,2,0xffffffff],[False,True]):
 h.prepare();h.missingCreation=missing;h.compare(0x461a00,[h.SC,0xffffffff,0x80000000,0x7fffffff,style,h.SOURCE],label=('style-create',style,missing))
for scene,missing in itertools.product([0,h.SC],[False,True]):
 h.prepare();h.missingCreation=missing;h.compare(0x461c40,[scene,0,0xffffffff,0x80000000],label=('splash-create',scene,missing))
# Callback services can mutate cached pointers/positions; source keeps its
# pre-call source+logic identities and does not restart validation afterward.
for fn in(0x461a00,0x461a90,0x461bc0):
 for state in(0,5):
  h.prepare();h.mode=4;h.put(h.L+0x1c,[state]);h.compare(fn,[h.SC,350,270,4001,1,h.SOURCE]if fn==0x461a00 else[h.A],label=('mutating-services',hex(fn),state))
for i in range(800):
 h.prepare();h.randomWord=h.rng.getrandbits(32);h.mode=h.rng.choice([0,0,4]);fn=h.rng.choice([0x461a00,0x461c40,0x461a90,0x461bc0]);h.put(h.L+0x1c,[h.rng.choice([0,0,5,5,h.rng.getrandbits(32)])]);h.put(h.A+8,[h.rng.getrandbits(32)]);h.put(h.A+0x158,[h.rng.getrandbits(32),h.rng.getrandbits(32)]);h.put(h.A+0x4c,[h.rng.getrandbits(32),h.rng.getrandbits(32)]);h.put(h.SOURCE+0x4c,[h.rng.getrandbits(32),h.rng.getrandbits(32)]);h.put(h.A+0x19c,[h.rng.getrandbits(32)]);h.put(h.A+0x1a4,[h.rng.randrange(3)])
 args=[h.SC,h.rng.getrandbits(32),h.rng.getrandbits(32),h.rng.getrandbits(32)]if fn in(0x461a00,0x461c40)else[h.A]
 if fn==0x461a00:args+=[h.rng.getrandbits(32),h.SOURCE]
 h.compare(fn,args,label=('seeded',i))
print('PASS branch and service matrix',h.calls,flush=True)

# Execute the original allocator/registration/list/binder/ANI bodies, not
# callback substitutes. Allocation bytes retain seed ownership explicitly.
for i in range(48):
 composed();h.put(h.TLS+0x14,[h.rng.getrandbits(32)]);h.missingLogic=i%7==0;h.missingImage=i%7==1;h.missingANI=i%7==2
 fn=0x461a00 if i%2 else 0x461c40;args=[h.SC,h.rng.getrandbits(32),h.rng.getrandbits(32),h.rng.getrandbits(32)]
 if fn==0x461a00:args+=[i%3,h.SOURCE]
 h.compare(fn,args,label=('whole-creation',i))
 if h.created:
  a=h.created[-1];callback=0x461a90 if fn==0x461a00 else 0x461bc0
  if fn==0x461c40:h.compare(callback,[a],label=('deferred-splash-init',i))
  h.compare(callback,[a],label=('whole-first-frame',i))

trajectories=[]
for family,delta,style,seed in itertools.product(['HitBurst','Splash'],[1,17,18,60],[0,1],[1,7]):
 composed(True);h.ctx.animation.animationDelta=delta;h.put(h.TLS+0x14,[seed]);fn=0x461a00 if family=='HitBurst'else 0x461c40;args=[h.SC,0xffffffff,0x80000000,4001]
 if family=='HitBurst':args+=[style,h.SOURCE]
 h.compare(fn,args,label=('retained-create',family,delta,style,seed));a=h.created[-1];callback=0x461a90 if family=='HitBurst'else 0x461bc0
 if family=='Splash':h.compare(callback,[a],label=('retained-init',family,delta,style,seed))
 # A zero animation delta genuinely holds the pending delay on later frames.
 for idle in range(3):
  saved=h.ctx.animation.animationDelta;h.ctx.animation.animationDelta=0;h.compare(callback,[a],label=('retained-zero-delta',family,idle));h.ctx.animation.animationDelta=saved
 for frame in range(700):
  h.put(h.SOURCE+0x4c,[(320+frame*0x7fffffff)&0xffffffff,(240-frame*0x80000001)&0xffffffff]);r=h.compare(callback,[a],label=('retained-animation',family,delta,style,seed,frame))
  if not r:break
 assert not r and h.get(a+8)[0]&0x10000 and frame<699
 sequence=h.get(a+0x190)[0];h.compare(0x4c9be0,[1],receiver=a,label=('retained-generic-destructor',family,delta,style,seed))
 trajectories.append({'family':family,'delta':delta,'style':style,'seed':seed,'frames':frame+1,'sequence':hex(sequence),'finalActor':hex(a)})
print('PASS actual ANI retained lifetimes',h.calls,flush=True)

# A resolved ANI and missing Level1 Splash image set still advances/stops.
# Missing ANI leaves selection untouched and does not supply invented frames.
for family,imageMissing,aniMissing in itertools.product(['HitBurst','Splash'],[False,True],[False,True]):
 composed(True);h.missingImage=imageMissing;h.missingANI=aniMissing;fn=0x461a00 if family=='HitBurst'else 0x461c40;args=[h.SC,350,270,4001]
 if family=='HitBurst':args+=[0,h.SOURCE]
 h.compare(fn,args,label=('retained-missing-create',family,imageMissing,aniMissing));a=h.created[-1];callback=0x461a90 if family=='HitBurst'else 0x461bc0
 if family=='Splash':h.compare(callback,[a],label=('retained-missing-init',family,imageMissing,aniMissing))
 for frame in range(48):h.compare(callback,[a],label=('retained-missing-update',family,imageMissing,aniMissing,frame))
 h.compare(0x4c9be0,[1],receiver=a,label=('retained-missing-destructor',family,imageMissing,aniMissing))

# Resolved image manager with gaps and restricted bounds retains original
# out-of-range image-token0 behavior; no controller changes its lifetime.
for family in ['HitBurst','Splash']:
 composed(True);h.put(h.IM+0x64,[2,4]);h.put(h.IM3+0x64,[2,5]);h.put(h.IMAGES+8,[0]);h.put(h.IMAGES3+12,[0]);fn=0x461a00 if family=='HitBurst'else 0x461c40;args=[h.SC,350,270,4001]
 if family=='HitBurst':args+=[0,h.SOURCE]
 h.compare(fn,args,label=('retained-restricted-image-create',family));a=h.created[-1];callback=0x461a90 if family=='HitBurst'else 0x461bc0
 if family=='Splash':h.compare(callback,[a],label=('retained-restricted-image-init',family))
 for frame in range(48):h.compare(callback,[a],label=('retained-restricted-image-update',family,frame))
 h.compare(0x4c9be0,[1],receiver=a,label=('retained-restricted-image-destructor',family))

# Sorted/equal-depth scene insertion, repeated retained creators, RNG stream,
# invalidation of source before the animation's natural terminal record.
for history in range(8):
 composed(True);actors=[]
 for ordinal in range(12):
  z=[0,4001,4001,0xffffffff,0x80000000,0x7fffffff][ordinal%6];style=ordinal%3
  h.compare(0x461a00,[h.SC,100+ordinal,200-ordinal,z,style,h.SOURCE],label=('retained-many-create',history,ordinal));actors.append(h.created[-1])
 for frame in range(7):
  h.ctx.animation.animationDelta=[1,0,18,60,0,17,18][frame];h.put(h.SOURCE+0x4c,[0xffffffff-frame,0x80000000+frame])
  if frame==5:h.put(h.SOURCE+8,[0x10000])
  for ordinal,a in enumerate(actors):h.compare(0x461a90,[a],label=('retained-many-update',history,frame,ordinal))
 assert all(h.get(a+8)[0]&0x10000 for a in actors)

# Four exact invalid-memory/service prefixes, deliberately not counted as
# successful original calls. The native boundary stops instead of crashing.
failurePrefixes=0
for fn,args,mutation in[(0x461a00,[0xdead0000,350,270,4001,0,h.SOURCE],None),(0x461a90,[h.A],(h.A+0x80,0xdead0000)),(0x461a90,[h.A],(h.A+0x6c,0xdead0000)),(0x461bc0,[h.A],(h.A+0x6c,0xdead0000))]:
 h.prepare()
 if mutation:h.put(mutation[0],[mutation[1]])
 old=bytes(h.heap);h.events=[];out=C.c_uint32();aa=(C.c_uint32*len(args))(*args);ok=h.lib.claw_impact_particle_entry(fn,0,aa,len(args),C.byref(h.ctx),h.dependency,None,C.byref(out));assert not ok and h.ctx.fault==1;expected=bytes(h.heap);ev=list(h.events);h.native=False;h.u.mem_write(h.BASE,old);h.events=[]
 try:h.m.call(fn,0,struct.pack('<'+'I'*len(args),*args))
 except Exception:pass
 else:raise AssertionError(('invalid source unexpectedly returned',hex(fn)))
 assert bytes(h.u.mem_read(h.BASE,h.SIZE))==expected and h.events==ev
 h.native=True;failurePrefixes+=1
# ABI rejection / unsupported address has no silent source execution claim.
h.prepare();out=C.c_uint32();assert not h.lib.claw_impact_particle_entry(0x461a00,0,None,0,C.byref(h.ctx),h.dependency,None,C.byref(out))and h.ctx.fault==2
h.prepare();assert not h.lib.claw_impact_particle_entry(0x123456,0,None,0,C.byref(h.ctx),h.dependency,None,C.byref(out))and not h.ctx.fault
report={'calls':h.calls,'events':h.eventCount,'instructions':len(h.m.executed),'decodedRecords':h.decodes,'failurePrefixes':failurePrefixes,'trajectories':trajectories,'assets':list({x['path']:x for x in h.assetProfiles}.values()),'exeSha256':h.m.sha256 if hasattr(h.m,'sha256')else '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',h.calls,'complete original calls /',h.eventCount,'ordered full snapshot events /',len(h.m.executed),'original instruction addresses /',h.decodes,'real ANI records /',failurePrefixes,'failure prefixes',flush=True)
