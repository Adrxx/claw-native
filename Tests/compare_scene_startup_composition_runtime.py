import scene_startup_composition_helpers as h
h.fresh();h.compare(0x4ce960,h.SCENE,[],'whole scene ctor',void=True);h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'whole joined startup');h.compare(0x4cefc0,h.SCENE,[],'whole readiness');h.compare(0x4ceef0,h.SCENE,[],'whole joined cleanup',void=True);print('PASS pilot',h.calls,h.snapshots,flush=True)
#The whole original constructor, eleven allocations, startup and teardown run;
#only actual physical endpoint identities are adapted by the oracle.
for seed in range(24):
 for flags in(0,1,2,4,5,8,12,16,18):
  h.fresh(seed^flags);h.compare(0x4ce960,h.SCENE,[],'scene ctor',void=True);h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],'source flags startup');h.compare(0x4cefc0,h.SCENE,[],'source readiness');h.compare(0x4ceef0,h.SCENE,[],'source cleanup',void=True);h.compare(0x4ceef0,h.SCENE,[],'repeated cleanup',void=True)
print('PASS ordinary',h.calls,h.snapshots,flush=True)
for where in('ddCreate','ddCoop','ddCaps','ddEnum','ddMode','ddFormat','surfaceCreate','surfaceDescribe','attached','dsCreate','dsCoop'):
 for hr in(1,0x80004005,0xffffffff):
  for flags in(0,1,4,8,12):
   h.fresh(hr^flags);h.compare(0x4ce960,h.SCENE,[],'failure ctor',void=True);h.failure={where:hr};h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],f'whole failed {where}');h.compare(0x4ceef0,h.SCENE,[],'failure cleanup',void=True)
print('PASS physical failures',h.calls,h.snapshots,flush=True)
#Raw sound-controller binding and readiness preserve old fields on rejected
#branches; force1 is the source caller, not a fabricated successful manager.
for parent in(0,h.SCENE):
 for manager in(0,h.DS):
  for available in(0,1,0xffffffff):
   for force in(0,1,0xffffffff):
    h.fresh(available^force);controller=h.BASE+0x9000;h.put(controller+12,[parent]);h.put(h.SCENE+32,[manager]);h.put(h.DS+120,[available]);h.compare(0x4ca280,controller,[force],'source sound binding');h.compare(0x4cf7e0,controller,[],'sound binding ready');h.compare(0x4f701d,controller,[],'CObject metadata')
print('PASS thin leaves',h.calls,h.snapshots,flush=True)
#Retained reinitialization uses source cleanup, never a fresh substitute graph.
for seed in range(12):
 h.fresh(seed);h.compare(0x4ce960,h.SCENE,[],'retained ctor',void=True)
 for flags in(1,4,0,16):
  h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],'retained source startup');h.compare(0x4cefc0,h.SCENE,[],'retained ready');h.compare(0x4ceef0,h.SCENE,[],'retained source clear',void=True)
 h.compare(0x4ce9c0,h.SCENE,[],'source scene destructor',void=True)
#Physical callbacks can mutate shared aliases; the recovered bodies reread
#them according to their source order, through live context/heap views.
for f in(0x700050,0x700030,0x4f4480,0x720018):
 for seed in range(8):
  h.fresh(seed);h.compare(0x4ce960,h.SCENE,[],'alias mutation ctor',void=True);h.mutations={f:[(0x541398,[h.DEVICE]),(0x54316c,[seed]),(0x543170,[seed+3]),(0x5430c8,[77]),(0x5430c4,[18])]};h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'source callback aliases');h.mutations={};h.compare(0x4ceef0,h.SCENE,[],'mutated cleanup',void=True)
print('PASS retained and aliases',h.calls,h.snapshots,flush=True)
for fail in range(1,19):
 h.fresh(fail);h.compare(0x4ce960,h.SCENE,[],'null allocation ctor',void=True);h.allocFailure=fail
 h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],f'original null allocation {fail}',unsafe=fail not in(14,18))
print('PASS null prefixes',h.calls,h.snapshots,flush=True)
#Supplied host/callback/context identities must survive both completion/fault.
import ctypes as C
views=(h.base,h.graphics,h.display,h.palette,h.audio,h.world,h.registry,h.life,h.collections)
for seed in range(8):
 h.fresh(seed);before=[bytes(v)for v in views];h.compare(0x4ce960,h.SCENE,[],'borrowed lifetime ctor',void=True);h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'borrowed lifetime startup');h.compare(0x4ceef0,h.SCENE,[],'borrowed lifetime cleanup',void=True);assert before==[bytes(v)for v in views]
print('VERIFIED',h.calls,h.snapshots,'instrumented',len(h.m.executed),flush=True)
