#!/usr/bin/env python3
import single_player_scene_helpers as h
for seed in range(3):
 for fn,args in (('construct',()),(0x40b5c0,()),(0x42aa50,()),(0x42af50,()),(0x48f0d0,(h.MGR,1,0)),(0x46aeb0,(1,1)),(0x46a6d0,(h.MGR,1,0))):
  h.setup(seed);h.policy=seed;h.failAt=-1;h.compare(fn,args)
print('PASS',h.calls//2,'whole original calls',h.eventCount//2,'ordered full snapshots')
# Every finite resource/creation failure gate, retaining pre-failure writes.
directed=0
for seed in range(24):
 for saved in (False,True):
  for fn in (0x48f0d0,0x46a6d0,0x46aeb0):
   h.setup(seed,saved);h.policy=seed%6;h.failAt=-1
   if fn==0x46aeb0:h.put(h.OWNER+0x14,[2 if seed%2 else 1])
   if seed%3==0:h.put(h.MGR+0x7c,[800,600])
   if seed%4==0:h.put(h.OWNER+0x2c,[h.PALETTE])
   if seed%5==0:h.put(h.MGR+0x9c,[1]);h.put(h.MGR+0x124,[1])
   args=(h.MGR,1,seed)if fn!=0x46aeb0 else(2 if seed%2 else 1,seed)
   h.compare(fn,args);directed+=1
for saved in (False,True):
 for gate in range(1,26):
  h.setup(gate,saved);h.policy=0;h.failAt=gate;h.compare(0x46a6d0,(h.MGR,1,0));directed+=1
# Whole seeded untouched constructor and base-initializer buffers.
for seed in range(200):
 h.setup(seed);h.policy=seed%6;h.failAt=-1
  # Use deterministic nonzero untouched owner words; constructor writes only
 # its observed subset and one byte at+4c.
 import random
 h.put(h.OWNER,[random.Random(seed+i).getrandbits(32)for i in range(478)])
 h.compare('construct');h.compare(0x48f0d0,(h.MGR,(seed%14)+1,seed));directed+=2
# Retained initialization/reinitialization histories preserve derived154 latch,
# replace palette ownership, clear defaults only on first startup, and retain
# failure-side effects before the next initialization attempt.
retained=0
for seed in range(24):
 h.setup(seed);h.policy=seed%6;h.failAt=-1;h.compare('construct');retained+=1
 for step in range(9):
  h.failAt=7 if step%3==1 else -1;h.put(h.MGR+0x9c,[step%2]);h.put(h.MGR+0x124,[step%3]);h.compare(0x46a6d0,(h.MGR,(step%14)+1,step));retained+=1
print('FINAL',h.calls//2,'complete original calls;',h.eventCount//2,'ordered full1MiB+63globals snapshots;',len(h.m.executed),'original addresses;',directed,'directed cases;',retained,'retained calls')
sceneCases=0
for seed in range(50):
 for fn,args in ((0x4ce960,()),(0x45fde0,(h.SCENE,seed,seed*3)),(0x4cace0,(h.SCENE,seed,seed*3)),(0x4cea10,(123,640,480,8,1))):
  h.setup(seed);h.policy=0;h.failAt=-1;h.compare(fn,args);sceneCases+=1
print('SCENE PASS',sceneCases)
collectionCases=0
for seed in range(100):
 for fn in (0x4f5620,0x4f6118,0x4f5cbd):
  h.setup(seed);h.policy=0;h.failAt=-1;h.compare(fn,(seed if seed%3 else 0xffffffff,));collectionCases+=1
sceneFailureCases=0
for oldError in (0,1234):
 for flags in (0,1,4,8,12):
  for gate in range(1,10):
   h.setup(gate);h.policy=0;h.failAt=-1;h.initCallFailure=gate;h.put(h.SCENE+0x38,[oldError]);h.compare(0x4cea10,(123,640,480,8,flags));sceneFailureCases+=1
print('FINAL TOTAL',h.calls//2,'complete original calls;',h.eventCount//2,'ordered snapshots;',len(h.m.executed),'original addresses;',collectionCases,'exact collection ctor calls;',sceneFailureCases,'scene-init failure cases')
managerCases=0
for seed in range(100):
 for fn in (0x4254a0,0x4b8240,0x4bd250,0x4cdf20,0x4cfa60):
  h.setup(seed);h.policy=0;h.failAt=-1;h.clockValue=(seed*997)&0xffffffff;h.compare(fn);managerCases+=1
print('APPLICATION TOTAL',h.calls//2,'complete original calls;',h.eventCount//2,'ordered full snapshots;',len(h.m.executed),'original addresses;',managerCases,'manager/probe/image reset calls')
# Explicit finite surface/audio/sound failure services, including prior error
# preservation and audio optional/required/disabled flag combinations.
actualFailureProfiles=0
for oldError in (0,1234):
 for flags in (0,1,4,8,12):
  for fn in (0x4ca6f0,0x4b47e0,0x4ca280):
   h.setup(fn);h.policy=0;h.failAt=-1;h.initFailure=fn;h.put(h.SCENE+0x38,[oldError]);h.compare(0x4cea10,(123,640,480,8,flags));actualFailureProfiles+=1
# Joined application/scene/state ctor + complete level entry. The actual REZ,
# physical surface/music objects and WWD loader are declared service profiles;
# both implementations retain the same constructed graph between calls.
joined=0
for seed in range(12):
 h.setup(seed);h.policy=seed%6;h.failAt=-1
 h.compare(0x4254a0);h.compare(0x4ce960);h.compare(0x4cea10,(123,640,480,8,1));h.compare('construct');joined+=4
 # These bindings are supplied by the enclosing actual application-loader
 # boundaries; no claim that4254a0 populates a window/REZ/config itself.
 h.put(h.MGR+4,[h.DEVICE]);h.put(h.MGR+0x30,[h.SCENE,h.MAP]);h.put(h.MGR+0x44,[h.OTHER,h.OTHER]);h.put(h.MGR+0x50,[h.OTHER]);h.put(h.MGR+0x7c,[640,480])
 h.compare(0x46a6d0,(h.MGR,1,0));joined+=1
print('JOINED TOTAL',h.calls//2,'complete original calls;',h.eventCount//2,'ordered snapshots;',len(h.m.executed),'original addresses;',joined,'retained joined ctor/init calls;',actualFailureProfiles,'explicit surface/audio/sound profiles')
# Populated real frozen grid activation/reinsertion in whole original level
# startup. Fixture preparation uses recovered grid/object/list constructors;
# actual startup must execute4d2030 and4d1fd0, not a zero-plane boundary.
import ctypes as C
class GridArgs(C.Structure):_fields_=[('words',C.c_uint32*8),('count',C.c_uint32)]
h.lib.claw_spatial_grid_entry.argtypes=[C.c_uint32,C.c_uint32,GridArgs,h.Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
def spatial(fn,t,args=()):
 fault=C.c_uint32();result=C.c_uint32();raw=GridArgs((C.c_uint32*8)(*args),len(args));assert h.lib.claw_spatial_grid_entry(fn,t,raw,h.host,C.byref(fault),C.byref(result))and not fault.value,(hex(fn),fault.value);return result.value
populated=0
for seed in range(6):
 h.setup(seed);h.policy=0;h.failAt=-1;h.compare(0x4ce960);h.compare(0x4cea10,(123,640,480,8,1));h.compare('construct');populated+=3
 world=h.words(h.SCENE+0x24)[0];h.put(h.GRIDPLANE,[0]*86);h.put(h.GRIDPLANE+0xc,[h.SCENE]);h.put(h.GRIDPLANE+8,[1]);h.put(h.GRIDPLANE+0x30,[24576,6144]);h.put(h.GRIDPLANE+0x50,[0,0,639,479]);h.put(h.GRIDPLANE+0x70,[640,480,320,240]);h.put(h.GRIDPLANE+0x84,[320,240]);h.put(world+0x5c,[h.GRIDPLANE]);spatial(0x4d1620,h.GRIDPLANE,(h.RESOURCE,0));grid=h.words(h.GRIDPLANE+0xb0)[0]
 for i in range(9):
  actor=h.BASE+0xf000+i*0x200;logic=h.BASE+0x11000+i*0x40;h.put(actor,[0]*128);h.put(actor,[0x5137f0,i,0x40000,h.SCENE]);h.put(actor+0x4c,[100+i*35,100+i*21]);h.put(actor+0x64,[i,0,logic]);h.put(logic,[0]*16);h.put(logic+0x10,[h.PLAYERUPDATE,0,0,24]);h.put(actor+0x98,[100+i*35,100+i*21,actor]);spatial(0x4d51a0,grid,(actor,))
 h.worldProfile=1;h.compare(0x46a6d0,(h.MGR,1,0));populated+=1
print('POPULATED TOTAL',h.calls//2,'complete original calls;',h.eventCount//2,'ordered full1MiB+63globals snapshots;',len(h.m.executed),'original addresses;',populated,'joined populated graph calls')
# Separate unsafe original null-allocation witnesses. These are not normal
# return comparisons: native diagnosis must preserve the same prefix writes
# and service order as the actual original access fault.
from unicorn import UcError,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX
nullProbe=False;nullWitness=None
def nullReadWitness(uc,address,size,user):
 global nullWitness
 if nullProbe and address in(0x4ced35,0x4ced58,0x4ced7b,0x4ced9e,0x4cedc1,0x4cede4,0x4cee10,0x4cee3d)and uc.reg_read(UC_X86_REG_ECX)==0:
  nullWitness=address;uc.emu_stop()
h.u.hook_add(UC_HOOK_CODE,nullReadWitness)
unsafe=0
for allocation in (1,2,3,4,5,6,7,9):
 h.setup(allocation);h.policy=0;h.failAt=-1;h.allocationFailure=allocation
 before=(bytes(h.heap),bytes(h.globals),bytes(h.camera),bytes(h.imageFX),bytes(h.clockWords));raw=(C.c_uint32*5)(123,640,480,8,1);result=C.c_uint32();h.events.clear();h.errors.clear()
 assert h.lib.claw_single_player_scene_entry(0x4cea10,h.SCENE,raw,5,C.byref(h.context),h.dependency,None,C.byref(result));assert h.context.fault==1 and not h.errors
 expected=h.snapshot();expectedEvents=list(h.events);h.native=False;h.C.memmove(h.imageFX,before[3],100);h.C.memmove(h.clockWords,before[4],20);h.load(*before[:3]);h.nextAllocation=h.BASE+0x12000;h.allocationCount=0;h.events.clear()
 nullProbe=True;nullWitness=None
 try:h.m.call(0x4cea10,h.SCENE,h.struct.pack('<5I',123,640,480,8,1));raise AssertionError('Original unexpectedly returned safely')
 except (UcError,AssertionError):assert nullWitness is not None,'No observed unchecked original null read'
 nullProbe=False
 assert expected==h.snapshot()and expectedEvents==h.events;unsafe+=1;h.native=True
import json
report={'source_sha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','normal_entry_calls':(h.calls-h.inlineSpans)//2,'inlined_owner_ctor_spans':h.inlineSpans//2,'total_normal_comparisons':h.calls//2,'ordered_full_snapshots':h.eventCount//2,'heap_bytes':h.SIZE,'global_words':63,'original_addresses':len(h.m.executed),'directed_startup_cases':directed,'retained_startup_calls':retained,'joined_application_scene_calls':joined,'joined_populated_scene_calls':populated,'unsafe_null_allocation_witnesses':unsafe,'full_winmain_recovery':False,'full_game_equivalence':False}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('VERIFIED',json.dumps(report))
