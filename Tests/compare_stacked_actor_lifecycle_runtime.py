#!/usr/bin/env python3
"""Whole original19-word lifecycle, ordered callback restoration and teardown."""
import ctypes as C,itertools,json,struct
import stacked_actor_lifecycle_helpers as h
for fn,args in[(0x456030,()),(0x484d90,(0,)),(0x484d90,(1,)),(0x484d90,(2,)),(0x484d90,(0x100,)),(0x484d90,(0x101,)),(0x484d90,(0xffffffff,)),(0x4c96b0,()),(0x4c9e30,(0xffffffff,)),(0x4bb030,()),(0x4041a0,(0,))]:
 for vt in[0x50f824,0x50f84c,0x50f874,0x50b064]:
  for seed in range(12):
   h.prepare();h.put(h.E,[vt]);h.compare(fn,h.E,args,('root',hex(fn),vt,seed))
for queued,cleanup,state,expected,policy in itertools.product([0,h.F1,h.F2,h.F3],[0,h.F1,h.F2],[0,1001,0x80000000,0xffffffff],[0,1001,0x80000000,0xffffffff],range(8)):
 if policy==4 and queued and cleanup==h.F2 and state==expected:continue
 h.prepare();h.policy=policy;h.put(h.E+0x14,[queued,cleanup,expected]);h.put(h.L+0x1c,[state]);h.compare(0x4041b0,h.E,[h.rng.getrandbits(32)],('callback',queued,cleanup,state,expected,policy))
print('PASS root/queued-callback mutation matrix',h.calls,h.eventCount,flush=True)
# Aliased primary state and restoration slots: original compares before the
# optional callback; current queued function is fetched only after that callback.
for primary in[h.E-4,h.E,h.E+4,h.E+0x2c,h.L,h.E2]:
 for cleanup in[h.F1,h.F2,h.F3]:
  for policy in [0,1,2,3,5,6,7]:
   h.prepare();h.policy=policy
   if primary<h.E:h.regions[h.E-4]=80
   h.put(h.E+0x10,[primary,h.F1,cleanup,1001]);state=h.get(primary+0x1c)[0];h.put(h.E+0x1c,[state]);h.compare(0x4041b0,h.E,[0x12345678],('alias',primary,cleanup,policy))
# Cleanup callbacks can destroy another stack or their own allocation before
# the outer source routine's remaining writes. Storage is retained after free
# for observation; this is source UAF ordering, not a safe reuse guarantee.
for target in[h.E,h.E2]:
 for queued in[h.F1,h.F3]:
  h.prepare();h.nestedTarget=target;h.put(h.E+0x14,[queued,h.F2,1001]);h.compare(0x4041b0,h.E,[h.A],('callback-destruction',target,queued));assert h.freed==[target]
# Whole generic actor→logic→19-word private deletion, plus pointer alias cases.
for attach in['ordinary','second','none']:
 for flag in[0,1,2,0x101,0xffffffff]:
  for seed in range(24):
   h.prepare();h.put(h.E,[0x50f824 if seed%2 else 0x50f84c]);h.put(h.E+0x14,[h.F1,h.F2,1001])
   if attach=='alias':h.put(h.A+0x70,[h.L])
   if attach=='second':h.put(h.A+0x70,[h.L2])
   if attach=='none':h.put(h.L+0x18,[0])
   h.compare(0x4c9be0,h.A,[flag],('joined-actor-logic-stack',attach,flag,seed))
   assert all(n<264 for t,n in h.requests if h.E<=t<h.E+76)
print('PASS alias/lifetime/generic source teardown histories',h.calls,h.eventCount,flush=True)
# All22 actual Level1 stacked records through the frozen complete constructor.
# Constructor oracle scaffolding is reused privately; scene child-init and binder
# transports remain declared service profiles, not reconstructed child gameplay.
import stacked_actor_constructor_helpers as ctor
import stacked_actor_level1_helpers as level
rows=[r for r in level.records()if r['strings'][1]in('FrontStackedCrates','BackStackedCrates')];assert len(rows)==22
save=(h.E,h.L,h.A);inventory=[]
for row in rows:
 ctor.prepare();callback=level.install(row);ctor.compose=True;ctor.compare(callback,[ctor.A],label=('stack-source-startup',row['index'],row['strings'][1]))
 h.prepare();h.E,h.L,h.A=ctor.E,ctor.L,ctor.A
 C.memmove(C.addressof(h.heap),bytes(ctor.heap),ctor.SIZE);h.regions={h.E:76,h.L:372,h.A:512};h.live={t:True for t in h.regions};h.freed=[]
 h.compare(0x4041b0,h.E,[h.A],('actual-initial-empty-post',row['index']))
 h.put(h.E+0x14,[h.F1,h.F2,1000]);h.compare(0x4041b0,h.E,[h.A],('actual-retained-restoration',row['index']))
 # Primary-logic deleting wrapper is the actual owner of its19-word parent.
 h.compare(0x4c80c0,h.L,[1],('actual-primary-stack-delete',row['index']));assert h.freed==[h.E,h.L]
 inventory.append({k:row[k]for k in('plane','index','strings','rawSHA256')}|{'spawnedCrates':ctor.created})
h.E,h.L,h.A=save
(h.WORK/'level1-stacks.json').write_text(json.dumps(inventory,indent=2)+'\n')
print('PASS all22 actual Level1 frozen constructors + retained post + generic logic teardown',h.calls,h.eventCount,flush=True)
# No-op roots do not read even an invalid receiver. Base/destructor do; failed
# queued spans reproduce the complete original write/service prefix.
prefixes=0
for fn,t,args,kind in[(0x456030,0xdead0000,[],'bad-receiver'),(0x4041b0,h.E,[0],'missing-primary'),(0x4041b0,h.E,[0],'cleared-queue'),(0x4041a0,h.E,[0],'rtti-service')]:
 h.prepare()
 if kind=='missing-primary':h.put(h.E+0x10,[0xdead0000,h.F1,h.F2,1001])
 if kind=='cleared-queue':h.policy=4;h.put(h.E+0x14,[h.F1,h.F2,1001])
 if kind=='rtti-service':continue # explicit transport tested with normal return above
 before=bytes(h.heap);state=(h.live.copy(),h.freed[:]);h.events=[]
 if kind=='cleared-queue':
  # A zero callback is an invalid entry service, represented as missing body.
  old=h.invoke
  @h.Invoke
  def checked(_,ev):
   if not ev.function:h.ctx.fault=1;return 0
   return old(None,ev)
  h.ctx.scene.call=checked
 ok,_=h.entry(fn,t,args);assert not ok and h.ctx.fault==1,(kind,ok,h.ctx.fault);expected=bytes(h.heap);ne=h.events[:];after=(h.live.copy(),h.freed[:])
 if kind=='cleared-queue':h.ctx.scene.call=old
 h.native=False;h.u.mem_write(h.BASE,before);h.u.mem_write(h.GS,h.globalSeed);h.live,h.freed=state;h.events=[];h.prefixStop=True
 try:h.m.call(fn,t,struct.pack('<'+'I'*len(args),*args))
 except Exception:pass
 else:raise AssertionError(('original prefix returned',kind))
 assert bytes(h.u.mem_read(h.BASE,h.SIZE))==expected and h.events==ne and(h.live,h.freed)==after,('prefix',kind)
 h.native=True;prefixes+=1
for f,args in[(0x4c96b0,[]),(0x4c9e30,[1]),(0x4bb030,[])]:h.prepare();h.compare(f,0xdead0000,args,('no-read-invalid-receiver',hex(f)))
h.prepare();out=h.U();assert not h.lib.claw_stacked_actor_lifecycle_entry(0x4041b0,h.E,None,0,C.byref(h.ctx),C.byref(out))and h.ctx.fault==2
assert not h.lib.claw_stacked_actor_lifecycle_entry(0x12345678,h.E,None,0,C.byref(h.ctx),C.byref(out))and not h.ctx.fault
report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','completeCalls':h.calls,'orderedSnapshots':h.eventCount,'failurePrefixes':prefixes,'originalInstructionAddresses':[hex(a)for a in sorted(a for a in h.m.executed|ctor.m.executed if 0x400000<=a<0x500000)],'actualStackRecords':len(rows),'composedConstructorCalls':ctor.calls,'composedConstructorSnapshots':ctor.eventCount,'heapBytesCompared':h.SIZE,'globalBytesCompared':h.GN}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',h.calls,'whole originals /',h.eventCount,'ordered full snapshots /',len(report['originalInstructionAddresses']),'original addresses /',prefixes,'prefixes',flush=True)
