#!/usr/bin/env python3
"""Actual original body comparisons: crates, stack graph, keg-specific states."""
import breakable_object_runtime_helpers as h
h.prepare()
for f,args,recv,meaning in[(0x471530,[h.A],0,True),(0x4717e0,[h.A],0,True),(0x46f2a0,[h.A],h.E,True),(0x433130,[h.A],h.E,True),(0x48d6e0,[h.A,5000],h.E,True),(0x46fc60,[],h.E,True),(0x46fc90,[2],h.E,True),(0x46fa90,[],h.E,True),(0x46fc20,[],h.E,True),(0x434050,[],h.E,True),(0x433fb0,[],h.E,True),(0x46f5b0,[1],h.E,True)]:
 h.prepare()
 if f==0x434050:h.put(h.E,[0x50c77c])
 h.compare(f,args,recv,('smoke',hex(f)),meaning)
print('PASS initial roots',flush=True)
for f in(0x471530,0x471720,0x471750):
 for state in(0,1,5,10,29,30,31,1000,0xffffffff):
  for n in range(28):
   h.prepare();h.put(h.L+0x1c,[state]);h.put(h.L+0x64,[h.rng.choice([0,1])]);h.put(h.L+0x130,[h.rng.choice([0,1,17,18,19,500,0x80000000,0xffffffff])]);h.put(h.A+0x10c,[h.rng.choice([0,1,2,3,998,999,1000,0x80000000,0xffffffff])]);h.put(h.A+0x64,[h.rng.choice([0,1,1000,5000,0xffffffff])]);h.put(h.A+0x170,[h.rng.choice([0,h.IM])]);h.put(h.A+0x174,[h.rng.choice([0,h.IMAGE])]);h.put(h.A+0x1a4,[n%2]);h.put(h.A+0x19c,[n%3]);h.g.animationDelta=h.rng.choice([0,1,18,500,0x80000000,0xffffffff]);h.mutation=n%2
   h.compare(f,[h.A],label=('single-state',f,state,n))
for health in(0,1,2,3,999,0x80000000,0xffffffff):
 for n in range(64):
  h.prepare();h.put(h.A+0x10c,[health]);h.put(h.L+0x130,[h.rng.choice([0,0,0,1,500])]);h.put(h.L+0x64,[n%2]);h.put(h.ATT+0xd0,[h.rng.choice([0,4,20,32,0x200])]);h.put(h.A+0x16c,[h.rng.choice([0,1,2,3,4,0xffffffff])]);h.put(h.A+0x170,[h.rng.choice([0,h.IM])]);h.put(h.A+0x50,[h.rng.choice([0,240,0x80000000,0xffffffff])]);h.put(h.AM+0x30,[n%5==0]);h.g.audioEnabled=n%3!=0;h.missingResource=n%4==0;h.mutation=n%2
  h.compare(0x4717e0,[h.A],label=('single-hit',health,n))
for f in(0x46f2a0,0x433130):
 for n in range(160):
  h.prepare();h.missingResource=n%3==0;h.g.damageScale=h.rng.choice([-2,-0.5,0,0.2,1,1.5,2,1e20,float('inf'),float('nan')]);h.g.healthScale=h.rng.choice([-2,0,0.2,1,1.5,2,1e20,float('inf'),float('nan')]);h.put(h.A+0x50,[h.rng.getrandbits(32)])
  h.compare(f,[h.A],h.E,('constructor',f,n))
for f in(0x46f1e0,0x433070,0x48d560,0x48d620):
 for state in(0,1,5,29,30,1000,0xffffffff):
  for n in range(10):
   h.prepare();h.put(h.L+0x1c,[state]);h.put(h.L+0xf0,[h.rng.choice([0,1,32,61])for _ in range(8)]);h.put(h.A+0x100,[h.rng.choice([0,1,32,61])]);h.put(h.A+0x64,[h.rng.choice([0,1,5000])])
   h.compare(f,[h.A],label=('wrapper',f,state,n))
for n in range(180):
 h.prepare();h.put(h.L+0xf0,[h.rng.choice([0,0,0,1,32,61])for _ in range(8)]);h.put(h.A+0x100,[h.rng.choice([0,1,32,61])]);h.put(h.A+0x64,[h.rng.choice([0,1,5000,0xffffffff])]);h.put(h.A+0x50,[h.rng.getrandbits(32)]);h.compare(0x48d6e0,[h.A,h.rng.choice([0,1000,5000,0xffffffff])],h.E,('stack-graph',n))
for f in(0x46fc60,0x46fc90,0x46fbe0,0x46fa90,0x46fc20,0x434050,0x433ed0,0x433f30,0x433f70,0x433fb0,0x434170,0x434180,0x46f5d0,0x433a00,0x46f5b0,0x4339e0):
 for n in range(64):
  h.prepare();h.put(h.E,[0x50c77c if f in(0x434050,0x434170,0x434180)else 0x50edd4]);h.put(h.E+0x400,[h.rng.choice([0,h.ALT]),h.rng.choice([0,h.ALT2]),h.rng.randrange(9),h.rng.choice([0,240,0xffffffff])]);h.put(h.ATT+0xd0,[h.rng.choice([0,4,20,32])]);h.put(h.E+0x1a0,[n%2]);h.put(h.A+0x40,[h.rng.choice([0,2,3])]);h.put(h.A+0x1a4,[n%2]);h.put(h.A+0x19c,[n%3]);h.put(h.A+0xcc,[h.rng.choice([0,1,7,8])]);h.put(h.A+0x174,[h.rng.choice([0,h.IMAGE])]);h.number(h.E+0x70,h.rng.choice([0,200,240,280]));h.number(h.E+0xa0,h.rng.choice([0,240,280]));h.number(h.E+0x58,h.rng.choice([-300,0,50,200,201,1000]));h.animationResult=n%2;h.mutation=n%2
  size=h.rng.choice([0,1,4,5,32,33,64]);h.put(h.E+0x2fc,[size]);h.put(h.E+0x300,[h.TABLE+0x200 if size>32 else h.rng.getrandbits(32)]);h.put(h.TABLE+0x200,[h.rng.getrandbits(32)]*2)
  args=[h.rng.choice([0,1,2,3,0xffffffff])]if f==0x46fc90 else[h.rng.getrandbits(32)]if f==0x433f70 else[h.rng.choice([0,1,2,255,256,257,0xffffffff])]if f in(0x46f5b0,0x4339e0)else[]
  h.compare(f,args,h.E,('private-method',f,n),f not in(0x434170,0x434180,0x46f5d0,0x433a00))
for f in(0x46f6a0,0x433ad0):
 for state in(9,10,11,12,13,14,0xffffffff,0x80000000):
  for n in range(8):
   h.prepare();h.compose=True
   # Out-of-range range-growth service deliberately points the new base to
   # a valid table interval by starting with caller supplied negative-index
   # padding. The descriptor itself remains unchanged by this service profile.
   h.compare(f,[state],h.E,('dispatch',f,state,n),False)
for f in(0x40f450,0x4735b0,0x40f540):
 for n in range(96):
  h.prepare();h.compose=True;h.loot.highLaunch=n%2;h.failCreation=n%7==0;h.loot.words[340]=n%3!=0
  if f==0x40f450:args=[h.SC,h.rng.randrange(62),h.rng.getrandbits(32),h.rng.getrandbits(32),5000,h.rng.getrandbits(32),h.rng.getrandbits(32)]
  elif f==0x4735b0:args=[h.SC,320,240,5000,h.rng.choice([0,1,32,61,62,0xffffffff])]
  else:
   h.put(h.A+0x100,[h.rng.choice([0,1,32,61,62,0xffffffff])]);h.put(h.L+0xf0,[h.rng.choice([0,1,32,61,62,0xffffffff])for _ in range(8)]);args=[h.A,320,240,5000]
  h.compare(f,args,label=('loot-wrapper',f,n),meaningful=f!=0x40f540)
print(f'PASS {h.calls} whole original roots / {h.eventCount} ordered snapshots',flush=True)
for n in range(96):
 h.prepare();h.compose=True;h.mutation=n%2;h.g.audioEnabled=n%3!=0;h.animationResult=n%2
 h.compare(0x46fc60,[],h.E,('joined-keg-hit-explosion',n))
 assert h.get(h.A+0xd0)[0]==0x1000000 and h.get(h.A+0x164)[0]&0x2000
 h.mutation=0
 for frame in range(6):
  h.put(h.A+0x19c,[0 if frame==5 else frame+1]);h.animationResult=1 if frame in(2,5)else 0
  h.compare(0x46fa90,[],h.E,('retained-keg-explode',n,frame))
 assert h.get(h.A+8)[0]&0x10000
print(f'PASS {h.calls} source calls including joined hit→frozen shared explosion and retained frames',flush=True)
import breakable_object_level1_helpers as level
actual=level.records();inventory=[]
for row in actual:
 h.prepare();callback=level.install(row);h.compose=True
 h.compare(callback,[h.A],label=('actual-Level1-startup',row['index'],row['strings'][1]))
 spawned=h.created;inventory.append({k:row[k]for k in('plane','index','words','strings','rawSHA256')}|{'spawnedCrates':spawned})
 if callback in(0x471720,0x471750):
  for frame in range(8):
   if frame in(1,4):h.compare(0x4717e0,[h.A],label=('actual-single-hit',row['index'],frame))
   else:
    h.g.animationDelta=500 if frame==3 else 18;h.put(h.A+0x1a4,[1]);h.put(h.A+0x19c,[0 if frame>=5 else 1]);h.compare(callback,[h.A],label=('actual-single-retained',row['index'],frame))
 elif callback==0x46f1e0:
  h.compare(0x46fc60,[],h.E,label=('actual-keg-hit',row['index']))
  for frame in range(6):
   h.animationResult=1 if frame in(2,5)else 0;h.put(h.A+0x1a4,[1]);h.put(h.A+0x19c,[0 if frame==5 else 1]);h.compare(0x46fa90,[],h.E,label=('actual-keg-retained',row['index'],frame))
 else:
  for i in range(spawned):
   actor=h.NEWACTORS+i*0x1000;brain=h.get(h.get(actor+0x6c)[0]+0x18)[0]
   h.put(brain+0xc,[actor,h.get(actor+0x6c)[0]]);h.put(brain+0x12c,[actor]);h.number(brain+0x70,row['words'][6]-i*40);h.number(brain+0x58,300);h.put(brain,[0x50c77c]);h.put(brain+0x410,[h.SEQ]);h.put(actor+0x74,[h.ATT]);h.put(actor+0x174,[h.IMAGE]);h.put(actor+0x1a4,[1]);h.put(actor+0x19c,[1])
   for frame in range(3):h.compare(0x433fb0,[],brain,label=('actual-stack-fall',row['index'],i,frame))
   h.compare(0x434050,[],brain,label=('actual-stack-hit',row['index'],i))
   h.put(actor+0x19c,[0]);h.compare(0x433f30,[],brain,label=('actual-stack-finished',row['index'],i))
(h.WORK/'level1-inventory.json').write_text(h.json.dumps({'records':inventory},indent=2)+'\n')
print(f'PASS all114 actual Level1 WWD startup/retained crate/keg/stack graphs: {h.calls} calls / {h.eventCount} events',flush=True)
# Actual recovered62-item metadata; resource identities remain explicit service
# outputs. Every item goes through the real signed image getter and launch body.
lootProfile=h.json.loads((h.ROOT/'Tests/world_loot_initializer_profile.json').read_text())
for record in lootProfile['records']:
 for profile in range(3):
  h.prepare();h.compose=True;h.loot.highLaunch=profile%2;h.loot.itemCount=62
  for item in lootProfile['records']:
   token=h.BASE+0x50000+item['id']*0x100;h.loot.words[item['id']]=0 if not item['image'] or(profile==2 and item['id']%3==0)else token;h.loot.words[66+item['id']]=item['value'];h.loot.words[132+item['id']]=item['mask'];h.put(token+0x64,[1,3]);h.put(token+0x14,[h.PTRS])
  h.compare(0x473610,[record['id']],label=('actual62-image-index',record['id'],profile))
  h.compare(0x4735b0,[h.SC,320,240,5000,record['id']],label=('actual62-loot-create',record['id'],profile))
print(f'PASS actual62 loot metadata/getter/launch variants: {h.calls} calls / {h.eventCount} events',flush=True)
# Failure prefixes stop before the original invalid dereference, never count as
# successful original returns. No heap/global transactional rollback invented.
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP
prefixCount=0
for fn,receiver,args,stop,allocation,creation in[(0x46f1e0,0,[h.A],0x46f23e,True,False),(0x433070,0,[h.A],0x4330ce,True,False),(0x48d560,0,[h.A],0x48d5c7,True,False),(0x48d620,0,[h.A],0x48d687,True,False),(0x48d6e0,h.E,[h.A,5000],0x48d7df,False,True)]:
 h.prepare();h.failAllocation=allocation;h.failCreation=creation;h.selectedEntry=fn;before=bytes(h.heap);bg=bytes(h.g);oldSeed=h.imageSeed;h.events=[]
 result=h.C.c_uint32();aa=(h.C.c_uint32*len(args))(*args)
 assert not h.lib.claw_breakable_entry(fn,receiver,aa,len(args),h.C.byref(h.ctx),h.dependency,None,h.C.byref(result))and h.ctx.fault==1
 expected=bytes(h.heap);eg=h.globalBytes();ne=list(h.events);h.native=False;h.u.mem_write(h.BASE,before);h.u.mem_write(h.mutableStart,oldSeed);h.syncGlobals();h.events=[]
 def prefixHook(u,address,size,_):
  if address==stop:u.emu_stop()
 hook=h.u.hook_add(UC_HOOK_CODE,prefixHook);h.u.mem_write(h.m.stack,h.struct.pack('<I',h.m.stop)+h.struct.pack('<'+'I'*len(args),*args));h.u.reg_write(UC_X86_REG_ESP,h.m.stack);h.u.reg_write(UC_X86_REG_ECX,receiver);h.u.emu_start(fn,h.m.stop,count=500000);h.u.hook_del(hook)
 assert h.u.reg_read(UC_X86_REG_EIP)==stop and bytes(h.u.mem_read(h.BASE,h.SIZE))==expected and h.globalBytes()==eg and h.events==ne,(hex(fn),'original prefix')
 h.native=True;prefixCount+=1
addresses={a for a in h.m.executed if 0x400000<=a<0x550000 and(a not in h.COUNTS or a in h.OWN)}
report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','completeCalls':h.calls,'orderedSnapshots':h.eventCount,'actualWWDRecords':len(actual),'failurePrefixes':prefixCount,'originalInstructionAddresses':[hex(a)for a in sorted(addresses)],'explicitServices':[hex(a)for a in sorted(set(h.COUNTS)-h.OWN)]}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n')
print(f'PASS FINAL {h.calls} complete original calls / {h.eventCount} whole-heap/global ordered snapshots / {len(addresses)} original addresses / {prefixCount} failure prefixes',flush=True)

# Unsupported entry and malformed argument domains are native safety checks.
h.prepare();before=bytes(h.heap);out=h.C.c_uint32(99)
assert not h.lib.claw_breakable_entry(0x46f7b0,0,None,0,h.C.byref(h.ctx),h.dependency,None,h.C.byref(out))and not h.ctx.fault and bytes(h.heap)==before
assert not h.lib.claw_breakable_entry(0x46f2a0,h.E,None,1,h.C.byref(h.ctx),h.dependency,None,h.C.byref(out))and h.ctx.fault==2 and bytes(h.heap)==before
print('PASS native unsupported/invalid ABI rejection, distinct from original parity',flush=True)
