#!/usr/bin/env python3
import player_startup_runtime_helpers as h
for seed in range(20):
 h.setup(seed);h.compare(0x415ce0,0);h.compare(0x46c790,h.OWNER);h.compare(0x46d8e0,h.OWNER)
print('PASS first defaults / owner reset / saved binding',h.calls//2)
for level in(-2147483648,-1,0,1,2,14,15,16,2147483647):
 for kind in(-1,0,1,2,3,4,2147483647):
  h.setup(level^kind);h.compare(0x49af30,h.RECORD,(level,kind));h.compare(0x49af90,h.RECORD,(level,kind))
print('PASS whole source checkpoint selectors',h.calls//2)
print('PASS',h.calls//2,h.snapshots//2,len([a for a in h.m.executed if 0x400000<=a<0x500000]))
# Complete source gates, latch consumption and exact signed/unsigned coordinates.
for seed in range(60):
 for gate in range(7):
  h.setup(seed)
  if gate==0:h.put(h.APP+0xa8,[0])
  if gate==1:h.put(h.APP+0x64,[0])
  if gate==2:h.put(h.OWNER+0x14,[0xffffffff])
  if gate==3:h.put(h.OWNER+0x14,[1])
  if gate==4:h.put(h.OWNER+0x14,[15]);h.put(h.APP+0xd8,[1]);h.put(h.RECORD+0x2d4+14*0xb0,[2])
  if gate==5:h.put(h.APP+0xd8,[3])
  if gate==6:h.put(h.RECORD+0x1774+0xb0,[0])
  h.compare(0x46d8e0,h.OWNER)
coords=[0,1,319,720,6143,24575,16777217,0x7fffffff,0x80000000,0xffffffff]
for x in coords:
 for y in coords:
  h.setup(x^y);t=h.RECORD+0x1774+0xb0;h.put(t+4,[x,y]);h.compare(0x46d8e0,h.OWNER)
# Signed threshold rounding, including negative scores and million boundaries.
for score in[0,1,999999,1000000,1000001,1999999,2147483647,0xffffffff,0xfff0bdc1,0x80000000]:
 h.setup(score);h.put(h.RECORD+0x1774+0xb0+0x10,[score]);h.compare(0x46d8e0,h.OWNER)
# All45 source slots. Loader level15 can admit bits but must fail the second
# actual selector; kind0 previous-level paths retain the actual level0 slot.
for level in range(16):
 for kind in range(4):
  h.setup(level*4+kind);h.put(h.OWNER+0x14,[level]);h.put(h.APP+0xd8,[kind]);h.compare(0x46d8e0,h.OWNER)
# Original integer->x87 multiply->single store, all main/layer indices, wrapping,
# actual24000-wide viewport profiles and unusual finite scale values.
scales=[0,.01,.125,.5,1,1.3333333730697632,1.75,-.75,32]
for seed in range(90):
 h.setup(seed)
 for i,p in enumerate(h.PLANES):
  h.put(p+8,[1 if(seed+i)%4==0 else ((seed+i)%4)*4]);h.put(p+0x18,[h.fword(scales[(seed+i)%len(scales)]),h.fword(scales[(seed+i*3)%len(scales)])])
 index=seed%3;h.put(h.WORLD+0x5c,[h.PLANES[index],index]);h.compare(0x46d8e0,h.OWNER)
print('PASS gates, unsigned save flag / signed camera / full45-slot selectors / float clamp',h.calls//2)
# Deliberately explicit callback mode proves cached record/main-center aliases
# and live layer count/index reloads through the actual native service boundary.
for seed in range(30):
 for mode in range(4):
  h.setup(seed);h.ctx.composeCamera=0;h.callbackMode=mode;h.compare(0x46d8e0,h.OWNER)
for level in range(1,17):
 for kind in range(4):
  h.setup(level+kind);h.ctx.composeCache=0;h.compare(0x49af30,h.RECORD,(level,kind));h.compare(0x49af90,h.RECORD,(level,kind));h.put(h.OWNER+0x14,[level]);h.put(h.APP+0xd8,[kind]);h.compare(0x46d8e0,h.OWNER)
# Retained actual first defaults + clear + saved bind + second consumed-latch
# no-op; globals and complete owner/record/plane buffers are carried forward.
for seed in range(40):
 h.setup(seed)
 for step in range(6):
  h.compare(0x415ce0,0);h.compare(0x46c790,h.OWNER);h.put(h.APP+0xa8,[1]);h.put(h.OWNER+0x14,[2+step]);h.put(h.APP+0xd8,[step%3]);h.compare(0x46d8e0,h.OWNER);h.compare(0x46d8e0,h.OWNER)
print('PASS retained source defaults/reset/bind/rebind and aliases',h.calls//2,h.snapshots//2)
# Complete frozen level entry with all three newly recovered startup helpers
# and the real shared CRT getter/srand body. Physical/group/actor/HUD creation
# remains an exact service fixture; this does not measure retail draw count.
import player_startup_level_helpers as l
for seed in range(8):
 l.setup(seed);l.policy=seed%6;l.failAt=-1;l.compare((2+seed,seed));l.compare((3+seed,0))
print('PASS joined whole46aeb0 defaults/save-binding/shared-srand',l.calls//2,l.eventCount//2)
# Hash-guarded actual14 retail worlds: input adaptation uses their verified
# frozenWorldPlane factor bits, flags and extents, checked against WWD records.
import json,struct
from world_plane_assets import worlds
profiles=json.loads((h.ROOT/'work/world-plane-agent/actual-world-plane-profiles.json').read_text())
actual=0
for path,raw,count,start,digest in worlds():
 ps=[p for p in profiles if p['world']==path];assert len(ps)==count
 for kind in(0,1,2):
  for edge in range(3):
   level=int(path.split('/')[0][5:]);h.setup(level*10+edge);h.put(h.OWNER+0x14,[level]);h.put(h.APP+0xd8,[kind])
   for i,p in enumerate(ps):
    q=struct.unpack_from('<40I',raw,start+i*160);assert p['recordFlags']==q[2]and p['runtimeExtents']==[q[22]*q[24],q[23]*q[25]]and p['payloadSHA256']==digest
    t=h.PLANES[i];h.put(t+8,[q[2]]);h.put(t+0x18,[int(x,16)for x in p['factorBits']]);h.put(t+0x30,p['runtimeExtents'])
   main=[i for i,p in enumerate(ps)if p['recordFlags']&1][-1];h.put(h.WORLD+0x5c,[h.PLANES[main],main]);h.put(h.WORLD+0x3c,[count])
   x,y=struct.unpack_from('<2I',raw,720)
   if edge==1:x,y=1,1
   if edge==2:x,y=ps[main]['runtimeExtents'][0]+123,ps[main]['runtimeExtents'][1]+123
   if level>=1:
    slotLevel=level-1 if kind==0 else level;slotKind=3 if kind==0 else kind;t=h.RECORD+{1:0x2d4,2:0xd24,3:0x1774}[slotKind]+slotLevel*0xb0;h.put(t+4,[x,y])
   h.compare(0x46d8e0,h.OWNER);actual+=1
print('PASS all14 actual world/42-plane flags/factors/extents/start and edge profiles',actual)
# Three separately classified prefixes: original unchecked null plane read,
# invalid infinity domain before frozen clamp, and bounded traversal stop.
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EBP
prefixes=0
for mode in range(3):
 h.setup(mode)
 if mode==0:h.put(h.WORLD+0x5c,[0]);address=0x46da04;expected=1
 elif mode==1:h.put(h.PLANES[1]+8,[0]);h.put(h.PLANES[1]+0x18,[h.fword(3.4028234663852886e38),h.fword(1)]);address=0x4d0a60;expected=2
 else:h.ctx.maximumPlanes=1;address=0x46da46;expected=4
 before=h.snapshot();h.events.clear();h.errors.clear();out=h.U();assert h.lib.claw_player_startup_entry(0x46d8e0,h.OWNER,None,0,h.C.byref(h.ctx),h.dependency,None,h.C.byref(out))and h.ctx.fault==expected
 a=h.snapshot();h.native=False;h.u.mem_write(h.BASE,before[0]);h.u.mem_write(h.GS,before[1]);h.callbackCount=before[2];h.sourceStopped=False
 def halt(u,at,size,_):
  if at==address and(mode!=2 or u.reg_read(UC_X86_REG_EBP)==1):h.sourceStopped=True;u.emu_stop()
 hook=h.u.hook_add(h.UC_HOOK_CODE,halt);h.u.mem_write(h.m.stack,struct.pack('<I',h.m.stop));h.u.reg_write(UC_X86_REG_ECX,h.OWNER);h.u.reg_write(UC_X86_REG_ESP,h.m.stack);h.u.emu_start(0x46d8e0,h.m.stop,count=500000);h.u.hook_del(hook)
 assert h.sourceStopped and a==h.snapshot(),(mode,a[2],h.snapshot()[2]);h.native=True;prefixes+=1
print('PASS stopped null/float-domain/bounded-loop prefixes',prefixes)
report={'completeOriginalCalls':h.calls//2+l.calls//2,'orderedCompleteSnapshots':h.snapshots//2+l.eventCount//2,'sourceImageAddresses':len({a for a in h.m.executed|l.m.executed if 0x400000<=a<0x500000}),'standaloneCalls':h.calls//2,'joinedWholeLevelCalls':l.calls//2,'actualWorldProfiles':actual,'actualWorlds':14,'actualPlanes':42,'stoppedPrefixes':prefixes,'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','scope':'New first-start binding/reset/selectors; frozen defaults/cache/camera/whole46aeb0/CRT composed. Physical resource/player/HUD/world-loader/startup setup services explicit.'}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
import player_startup_message_helpers as msg
messageCalls=0
for seed in range(20):
 for block in(1,3,10):
  msg.setup(seed,block);msg.compare(0x4f5249,msg.LIST,(block,));messageCalls+=1
  timers=h.get(msg.LIST+0x20,6)
  for step in range(12):msg.compare(0x422370,msg.LIST,(msg.MSG,step%4));messageCalls+=1
  msg.compare(0x42af70,h.APP,(0x5253a8,));messageCalls+=1;assert h.get(msg.LIST+0x20,6)==timers
  msg.compare(0x4f5288,msg.LIST);messageCalls+=1
for count in(0,1,7,8,0x7fffffff,0x80000000,0xffffffff):
 for flags in(0,1,2,3,4,5,6,7,0x100,0xffffffff):
  msg.setup(count);h.put(msg.LIST+0xc,[count]);msg.compare(0x422370,msg.LIST,(msg.MSG,flags));messageCalls+=1
for pointer in(0,msg.MSG,msg.MSG+1):
 msg.setup();msg.write(msg.MSG,b'\0\0');msg.compare(0x422370,0xffffffff,(pointer,7));messageCalls+=1
msg.setup();h.put(h.APP+0x4c,[0]);msg.compare(0x42af70,h.APP,(0xffffffff,));messageCalls+=1
for seed in range(20):
 msg.setup(seed)
 for step in range(8):msg.compare(0x4f5382 if step%2 else 0x4f53b7,msg.LIST,(msg.MSG,));messageCalls+=1
 msg.compare(0x4f5288,msg.LIST);messageCalls+=1
 # NewNode is independently recovered; its dangling node is intentionally
 # not inserted by this entry. Full pool/list buffer still compares.
 msg.compare(0x4f52f0,msg.LIST,(0x12345678,0x87654321));messageCalls+=1
print('PASS source checkpoint message enqueue/list lifecycle, timer preservation',messageCalls)
report.update(completeOriginalCalls=h.calls//2+l.calls//2,orderedCompleteSnapshots=h.snapshots//2+l.eventCount//2,sourceImageAddresses=len({a for a in h.m.executed|l.m.executed if 0x400000<=a<0x500000}),messageCalls=messageCalls)
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
# Message allocation and service failures are separately stopped prefixes,
# including original zero-block-size null-node fallthrough; never fake success.
messagePrefixes=0
for mode in range(4):
 msg.setup(mode,0 if mode==1 else 10)
 if mode==0:msg.allocationFailure=True;address=0x4f5ac1
 elif mode==1:address=0x4f532b
 elif mode==2:msg.faultService=0x4f66cc;address=0x4f66cc
 else:
  msg.compare(0x422370,msg.LIST,(msg.MSG,0));msg.faultService=0x4f6584;address=0x4f6584
 before=msg.state();h.events.clear();out=h.U();aa=(h.U*1)(msg.MSG);assert h.lib.claw_player_startup_entry(0x42af70,h.APP,aa,1,h.C.byref(h.ctx),msg.dependency,None,h.C.byref(out))and h.ctx.fault in(1,99)
 a=msg.state();events=list(h.events);h.native=False;h.u.mem_write(h.BASE,before[0][0]);h.u.mem_write(h.GS,before[0][1]);h.callbackCount=before[0][2];msg.nodeCursor,msg.stringCursor=before[1:3];msg.live=dict(before[3]);h.events.clear();stopped=[False]
 def halt(u,at,size,_):
  if at==address:
   # The existing adapter hook executes before this observer for the two
   # CString calls; capture after its physical storage effects and stop.
   stopped[0]=True;u.emu_stop()
 observer=h.u.hook_add(h.UC_HOOK_CODE,halt);h.u.mem_write(h.m.stack,struct.pack('<2I',h.m.stop,msg.MSG));h.u.reg_write(UC_X86_REG_ECX,h.APP);h.u.reg_write(UC_X86_REG_ESP,h.m.stack);h.u.emu_start(0x42af70,h.m.stop,count=500000);h.u.hook_del(observer)
 assert stopped[0]and a==msg.state()and events==h.events,mode;h.native=True;messagePrefixes+=1
print('PASS message null-allocation/zero-block/assignment/destructor prefixes',messagePrefixes)
report['stoppedPrefixes']+=messagePrefixes
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
remainingMessageCalls=0
for seed in range(12):
 for policy in range(3):
  msg.setup(seed);msg.fontPolicy=policy;msg.compare(0x4222a0,msg.LIST,(5000+seed,2000+seed));remainingMessageCalls+=1
  assert h.get(msg.LIST+0x34)[0]==(0 if policy==2 else 0x76543210)
for count in range(1,13):
 for block in(1,3,10):
  msg.setup(count,block)
  for n in range(count):msg.compare(0x422370,msg.LIST,(msg.MSG,(n%2)*2));remainingMessageCalls+=1
  for n in range(count):
   out=msg.MSG+512;h.put(out,[0xdeadbeef]);msg.compare(0x4f53eb,msg.LIST,(out,));remainingMessageCalls+=1
   assert msg.text(h.get(out)[0])==b'Your game has been saved'
   # Caller-owned output CString destructor is explicit, as in4224f0.
   msg.effect(0x4f6584,out,[])
  assert h.get(msg.LIST+0xc)[0]==0 and all(not v[2]for v in msg.live.values())
for seed in range(12):
 msg.setup(seed);node=msg.compare(0x4f52f0,msg.LIST,(0,0))[2];remainingMessageCalls+=1;msg.compare(0x4f5359,msg.LIST,(node,));remainingMessageCalls+=1
print('PASS config font fallback / retained RemoveHead refcounts/pool / FreeNode',remainingMessageCalls)
report.update(completeOriginalCalls=h.calls//2+l.calls//2,orderedCompleteSnapshots=h.snapshots//2+l.eventCount//2,sourceImageAddresses=len({a for a in h.m.executed|l.m.executed if 0x400000<=a<0x500000}),messageCalls=h.calls//2-2268)
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
# Actual inlined application config construction42614c..42616b, after its
# successful56-byte allocation. This is a span, not whole425730 boot replay.
from unicorn.x86_const import UC_X86_REG_EDI,UC_X86_REG_ESI
constructorSpans=0
for seed in range(12):
 msg.setup(seed);before=msg.state();msg.compare(0x4f5249,msg.LIST,(10,));h.put(msg.LIST+0x1c,h.get(0x52e1cc));h.put(msg.LIST+0x30,[0,0]);a=msg.state();h.native=False;h.u.mem_write(h.BASE,before[0][0]);h.u.mem_write(h.GS,before[0][1]);msg.nodeCursor,msg.stringCursor=before[1:3];msg.live=dict(before[3]);msg.fontCalls=before[4];h.callbackCount=before[0][2];h.events.clear();stopped=[False]
 def halt(u,at,size,_):
  if at==0x42616b:stopped[0]=True;u.emu_stop()
 observer=h.u.hook_add(h.UC_HOOK_CODE,halt);h.u.reg_write(UC_X86_REG_ESP,h.m.stack);h.u.reg_write(UC_X86_REG_EDI,msg.LIST);h.u.reg_write(UC_X86_REG_ESI,0);h.u.emu_start(0x42614c,h.m.stop,count=500000);h.u.hook_del(observer);assert stopped[0]and a==msg.state();h.native=True;constructorSpans+=1
print('PASS exact inlined config constructor spans',constructorSpans)
report.update(completeOriginalCalls=h.calls//2+l.calls//2,orderedCompleteSnapshots=h.snapshots//2+l.eventCount//2,sourceImageAddresses=len({a for a in h.m.executed|l.m.executed if 0x400000<=a<0x500000}),messageCalls=h.calls//2-2268,configurationConstructorSpans=constructorSpans,scope='Exact startup/save binding/reset/selectors and message queue/init/dequeue; frozen defaults/cache/camera/whole46aeb0/CRT/pools composed. Physical resource/gameplay/graphics/CString/font transport explicit.')
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
