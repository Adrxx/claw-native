#!/usr/bin/env python3
"""Full pinned v1.0 bodies; declared file/world/player transports are in helper."""
import ctypes as C, hashlib, json, struct
import menu_game_launch_helpers as h

for command in (0x807e,0x807f):
 for level in (0,1,2,14,15,0xffffffff,0x80000000):
  for result in (0,1,0x80000000):
   h.fresh(level);h.launchResult=result
   h.compare(0x426e30,f'router/{command:x}/{level:x}/{result:x}',(0xdeadbeef,command,14))
   assert h.get(h.APP+0xa8)[0]==(0 if command==0x807e and not result else 1)
   if not result:assert h.events[-1][0:3]==(0x429e10,h.APP,(0x8005,0x6ab if command==0x807e else 0x6ac))

levels=(0,1,2,7,14,15,0x7fffffff,0x80000000,0xffffffff)
for level in levels:
 for selected in (0,h.STORE):
  for flags in (0,1,2,3,0x80000000,0xffffffff):
   h.fresh(level);h.put(h.APP+100,[selected]);h.put(h.CACHE,[flags]);h.recordFlags=flags
   h.compare(0x42ba10,f'unlocked/{level:x}/{selected:x}/{flags:x}',(level,))
   for kind in (0,1,2,3,0xffffffff):
    h.compare(0x42ba70,f'checkpoint/{level:x}/{selected:x}/{flags:x}/{kind:x}',(level,kind))
for selected in (0,h.STORE):
 for count in (0,1,2,3,0x7fffffff,0x80000000,0xffffffff):
  h.fresh();h.put(h.APP+100,[selected]);h.put(h.STORE_MANAGER+12,[count]);h.compare(0x42bab0,f'player-count/{selected:x}/{count:x}')
 for name in (b'Player',b'player',b'',b'Sample',b'Player1'):
  h.fresh();h.put(h.APP+100,[selected]);h.writebytes(h.STORE+20,name+b'\0',True);h.compare(0x42bad0,f'player-name/{selected:x}/{name!r}')
for level in range(1,15):
 for kind in (0,1,2,3,0xffffffff):
  h.startProfile(level,1);h.ctx.composeProgression=0
  h.compare(0x42ba70,f'real-cache/{level}/{kind:x}',(level,kind))
  h.compare(0x42ba10,f'real-unlock/{level}/{kind:x}',(level,))

def title(value,size=1524):
 h.filePayload=h.pack(size,0,0,0)+value+b'\0'+bytes(1507-len(value))
for value in (b'Claw Level 1',b'LEVEL14',b'no digits',b'',b' -14tail',b'0zero',b'999999999',b'\xff\x8012',b'2'*255):
 for opened,read,header in ((1,1524,1524),(0,1524,1524),(1,1523,1524),(1,0,1524),(1,1524,1525),(1,1524,0xffffffff),(1,1524,0)):
  h.fresh();title(value,header);h.fileOpen=opened;h.fileReadCount=read
  h.compare(0x436e60,f'saved/{value!r}/{opened}/{read}/{header:x}',(h.SAVEDPATH+12,),receiver=0)
  assert h.get(h.SAVEDPATH)[0]==0
  h.compare(0x4cd530,f'header/{value!r}/{opened}/{read}/{header:x}',(h.SAVEDPATH+12,h.TITLEOUT),receiver=0)
for empty,world in ((1,1),(0,0),(1,0)):
 h.fresh();h.put(h.SAVEDPATH+4,[0 if empty else 10]);h.put(h.SC+36,[h.EXTRA if world else 0]);assert h.compare(0x436e60,f'saved-empty/{empty}/{world}',(h.SAVEDPATH+12,),receiver=0)==0xffffffff
for path,out in ((0,h.TITLEOUT),(h.SAVEDPATH+12,0),(0,0)):
 h.fresh();assert h.compare(0x4cd530,'null-header',(path,out),receiver=0)==0

# Source creation/retention/failed allocation and callback gates. A body-return
# zero is not synthesized as a successful reload by the host adapter.
for mode in (3,5,10):
 for command in (0x807e,0x807f):
  for outcome in (0,1,0x80000000):
   h.fresh(4);h.ctx.composeProgression=1;h.modeValues=[mode];h.levelOutcomes=[outcome];h.transitionOutcomes=[outcome]
   h.compare(0x426e30,f'composed-router/{mode}/{command:x}/{outcome:x}',(0,command,4))
for failure in (0,1,2):
 for initialized in (0,1):
  h.fresh(3);h.constructType=3;h.ctx.composeProgression=1;h.progression.composeTransitions=1;h.allocationFail=failure;h.initResult=initialized
  h.compare(0x426e30,f'new-owner/{failure}/{initialized}',(0,0x807f,3))

# Real retail headers and plane shape; the world loader, palette and player
# creation/update leaves stay explicitly profiled in the ordered service log.
for level in range(1,15):
 for kind in (0,1,2,3):
  h.startProfile(level,kind);h.constructType=3
  h.compare(0x426e30,f'full-world/{level}/{kind}',(0,0x807e if kind else 0x807f,level))
  assert h.get(h.APP+44)[0]!=h.OWNER
  assert h.get(h.APP+0xa8)[0]==0
  assert h.get(0x537e88)[0]==h.PLAYER
  assert h.get(h.PRIMARY+28)[0]==24 # declared source-player update transport
  if kind in(1,2):assert h.get(0x534cc4)[0]==1234567+level
  h.compare(0x4cd530,f'retail-header/{level}/{kind}',(h.SAVEDPATH+12,h.TITLEOUT),receiver=0)
fatalGates=toleratedGates=0
for gate in range(1,24):
 h.startProfile(1);h.constructType=3;h.failedGate=gate
 h.compare(0x426e30,f'full-load-failed-gate/{gate}',(0,0x807f,1))
 assert h.gates>=gate
 if any(e[0]==0x429e10 for e in h.events):fatalGates+=1
 else:toleratedGates+=1
assert (fatalGates,toleratedGates)==(21,2)
for level in range(1,15):
 h.startProfile(level);h.constructType=3;h.put(h.APP+0xc0,[h.SAVEDPATH+12])
 h.compare(0x426e30,f'saved-header-selects-level/{level}',(0,0x807f,15-level))
 assert h.get(h.get(h.APP+44)[0]+20)[0]==level
 assert h.get(h.SAVEDPATH)[0]==1 # copied by-value argument destroyed, app reference retained
for level in(1,7,14):
 h.startProfile(level,2);h.constructType=3
 h.mutations={h.PLAYERUPDATE:[(0x537210,0xfffffffd),(0x53ec44,0x7788),(0x52be14,0xffffff80),(0x52be18,0x7fffffff)],0x546df0:[]}
 h.compare(0x426e30,f'live-alias-mutation/{level}',(0,0x807e,level))
# Reuse a live mode3 owner: no nativelevel increment or repeated construction.
for level in (1,4,14):
 h.startProfile(level,2);h.constructType=3
 h.compare(0x426e30,f'retained-create/{level}',(0,0x807e,level))
 for repeat in range(3):
  h.put(h.APP+0xa8,[repeat&1]);h.put(h.APP+0xd8,[1+(repeat&1)]);h.put(h.APP+0xd4,[level])
  h.compare(0x426e30,f'retained-reload/{level}/{repeat}',(0,0x807e,level))

# Public admission/ABI guards: preserve full command and separate coverage.
for command in (0x1807e,0xffff807f,0x807c,0):
 h.fresh();args=(h.U*3)(0,command,1);out=h.U(0xabcdef);assert not h.lib.claw_menu_game_launch_entry(0x426e30,h.APP,args,3,C.byref(h.ctx),h.dep,None,C.byref(out));assert not h.ctx.fault and out.value==0xabcdef
for fn,count in ((0x426e30,2),(0x42ba10,0),(0x42bab0,1),(0x436e60,0),(0x4cd530,1)):
 h.fresh();out=h.U();args=(h.U*3)(0,0,0);assert not h.lib.claw_menu_game_launch_entry(fn,h.APP,args,count,C.byref(h.ctx),h.dep,None,C.byref(out));assert h.ctx.fault==3
unsafe=0
for fn,args,configure in ((0x42bab0,(),lambda:h.put(h.APP+96,[0])),(0x426e30,(0,0x807f,1),lambda:(h.put(h.APP+44,[0]),setattr(h.ctx,'composeProgression',1)))):
 h.fresh();configure();h.events.clear();h.originalEvents.clear();h.errors.clear();before=h.raw(True);a=(h.U*len(args))(*args);out=h.U()
 assert not h.lib.claw_menu_game_launch_entry(fn,h.APP,a,len(args),C.byref(h.ctx),h.dep,None,C.byref(out));assert h.ctx.fault==2
 native=h.raw(True);ev=list(h.events);h.m.u.mem_write(h.BASE,before[:h.SIZE]);h.m.u.mem_write(0x520000,before[h.SIZE:])
 try:h.m.call(fn,h.APP,h.pack(*args))
 except h.UnsafePrefix:pass
 else:raise AssertionError('original unsafe prefix was not reached')
 assert h.raw(False)==native and h.originalEvents==ev;unsafe+=1
executed=sorted(h.m.executed);mapped=[x for x in executed if 0x401000<=x<=0x50adb5]
result={'originalSha256':hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'wholeCalls':h.calls,'fullSnapshots':h.eventCount,'mappedTextAddresses':len(mapped),'totalInstrumentedAddresses':len(executed),'unsafePrefixes':unsafe,'retailWorlds':14,'fullLaunchProfiles':56,'injectedFailureGates':23,'sourceFatalInjectedGates':fatalGates,'sourceToleratedInjectedGates':toleratedGates,'sourceOwnedEntries':7,'sourceHashes':{str(p):hashlib.sha256((h.ROOT/p).read_bytes()).hexdigest()for p in('Sources/MenuGameLaunchRuntime.h','Sources/MenuGameLaunchRuntime.cpp')},'limits':['world/palette/player callback are named transports','full camera/spatial loading not composed','resource/media/window/filesystem endpoints explicit']}
(h.WORK/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',json.dumps(result))
