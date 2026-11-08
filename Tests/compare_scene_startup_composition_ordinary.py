"""Ordinary-only whole-scene QA; physical endpoints remain declared fixtures."""
import gzip,struct
import scene_startup_composition_helpers as h

# Capture a finite representative set for separately allocated sanitizer replay.
h.fresh();h.compare(0x4ce960,h.SCENE,[],'whole scene ctor',void=True);h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'whole joined startup');h.compare(0x4cefc0,h.SCENE,[],'whole readiness');h.compare(0x4ceef0,h.SCENE,[],'whole joined cleanup',void=True);print('PASS pilot',h.calls,h.snapshots,flush=True)
#The whole original constructor, eleven allocations, startup and teardown run;
#only actual physical endpoint identities are adapted by the oracle.
for seed in range(24):
 for flags in(0,1,2,4,5,8,12,16,18):
  h.capture=seed==0 and flags in(0,1,4,8,12,16,18);h.fresh(seed^flags);h.compare(0x4ce960,h.SCENE,[],'scene ctor',void=True);h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],'source flags startup');h.compare(0x4cefc0,h.SCENE,[],'source readiness');h.compare(0x4ceef0,h.SCENE,[],'source cleanup',void=True);h.compare(0x4ceef0,h.SCENE,[],'repeated cleanup',void=True)
print('PASS ordinary',h.calls,h.snapshots,flush=True)
for where in('ddCreate','ddCoop','ddCaps','ddEnum','ddMode','ddFormat','surfaceCreate','surfaceDescribe','attached','dsCreate','dsCoop'):
 for hr in(1,0x80004005,0xffffffff):
  for flags in(0,1,4,8,12):
   h.capture=where in('ddCreate','ddCoop','ddMode','ddFormat','dsCreate','dsCoop') and hr==0x80004005 and flags==8;h.fresh(hr^flags);h.compare(0x4ce960,h.SCENE,[],'failure ctor',void=True);h.failure={where:hr};h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],f'whole failed {where}');h.compare(0x4ceef0,h.SCENE,[],'failure cleanup',void=True)
print('PASS physical failures',h.calls,h.snapshots,flush=True)
#Raw sound-controller binding and readiness preserve old fields on rejected
#branches; force1 is the source caller, not a fabricated successful manager.
h.capture=False
for parent in(0,h.SCENE):
 for manager in(0,h.DS):
  for available in(0,1,0xffffffff):
   for force in(0,1,0xffffffff):
    h.fresh(available^force);controller=h.BASE+0x9000;h.put(controller+12,[parent]);h.put(h.SCENE+32,[manager]);h.put(h.DS+120,[available]);h.compare(0x4ca280,controller,[force],'source sound binding');h.compare(0x4cf7e0,controller,[],'sound binding ready');h.compare(0x4f701d,controller,[],'CObject metadata')
print('PASS thin leaves',h.calls,h.snapshots,flush=True)
#Retained reinitialization uses source cleanup, never a fresh substitute graph.
for seed in range(12):
 h.capture=seed==0;h.fresh(seed);h.compare(0x4ce960,h.SCENE,[],'retained ctor',void=True)
 for flags in(1,4,0,16):
  h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],'retained source startup');h.compare(0x4cefc0,h.SCENE,[],'retained ready');h.compare(0x4ceef0,h.SCENE,[],'retained source clear',void=True)
 h.compare(0x4ce9c0,h.SCENE,[],'source scene destructor',void=True)
#Physical callbacks can mutate shared aliases; the recovered bodies reread
#them according to their source order, through live context/heap views.
h.capture=False
for f in(0x700050,0x700030,0x4f4480,0x720018):
 for seed in range(8):
  h.fresh(seed);h.compare(0x4ce960,h.SCENE,[],'alias mutation ctor',void=True);h.mutations={f:[(0x541398,[h.DEVICE]),(0x54316c,[seed]),(0x543170,[seed+3]),(0x5430c8,[77]),(0x5430c4,[18])]};h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'source callback aliases');h.mutations={};h.compare(0x4ceef0,h.SCENE,[],'mutated cleanup',void=True)
print('PASS retained and aliases',h.calls,h.snapshots,flush=True)
#Supplied host/callback/context identities must survive both completion/fault.
import ctypes as C
views=(h.base,h.graphics,h.display,h.palette,h.audio,h.world,h.registry,h.life,h.collections)
for seed in range(8):
 h.fresh(seed);before=[bytes(v)for v in views];h.compare(0x4ce960,h.SCENE,[],'borrowed lifetime ctor',void=True);h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'borrowed lifetime startup');h.compare(0x4ceef0,h.SCENE,[],'borrowed lifetime cleanup',void=True);assert before==[bytes(v)for v in views]


# The optional third display wrapper is deliberately unused under source flag1.
for seed in range(4):
 h.capture=seed==0;h.fresh(seed);h.compare(0x4ce960,h.SCENE,[],'optional allocation ctor',void=True);h.allocFailure=14
 assert h.compare(0x4cea10,h.SCENE,[123,640,480,8,1],'optional allocation omitted')==1
 assert h.allocationIndex==17 and len(h.created)==16 and h.get(h.SCENE+56)==[0]
 assert h.compare(0x4cefc0,h.SCENE,[],'optional allocation readiness')==0
 h.compare(0x4ceef0,h.SCENE,[],'optional allocation cleanup',void=True)
# A failed DirectSoundCreate does not write through its failed output token.
# The original returns before accessing an absent audio manager in this path.
base_effect=h.effect
def ordinary_effect(f,t,a,buffers):
 if f==0x4f4480 and a[1]==20 and h.failure.get('dsCreate',0):return h.failure['dsCreate']
 return base_effect(f,t,a,buffers)
h.effect=ordinary_effect
for seed in range(4):
 for flags in(1,8):
  h.capture=seed==0;h.fresh(seed);h.compare(0x4ce960,h.SCENE,[],'audio allocation ctor',void=True);h.allocFailure=11;h.failure={'dsCreate':0x80004005}
  assert h.compare(0x4cea10,h.SCENE,[123,640,480,8,flags],'audio allocation/device unavailable')==(0 if flags&8 else 1)
  assert h.get(h.SCENE+32)==[0] and h.get(h.SCENE+56)==[1009 if flags&8 else 0]
  h.compare(0x4ceef0,h.SCENE,[],'audio allocation cleanup',void=True)
print('PASS ordinary allocation returns',h.calls,h.snapshots,flush=True)
p=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
with gzip.open(h.WORK/'ordinary-sanitizer-replay.bin.gz','wb')as out:
 out.write(b'SCMP'+p(h.SIZE,h.IMAGE_START,h.IMAGE_SIZE,len(h.corpus)))
 for f,t,a,label,value,meaningful,before,image,expected,created,events in h.corpus:
  out.write(p(f,t,len(a),value,meaningful,len(created),len(events))+p(*a)+before+image)
  for token,n in created:out.write(p(token,n))
  for f,t,a,mask,value,buffers,outputs,digest,changes in events:
   out.write(p(f,t,len(a),mask,value,len(buffers),len(changes))+p(*a)+digest)
   for b,v in zip(buffers,outputs):out.write(p(len(b))+b+v)
   for i,v in changes:out.write(p(i,v))
  out.write(expected)
print('VERIFIED ordinary-only',h.calls,'whole calls',h.snapshots,'ordered snapshots')
print('CORPUS',len(h.corpus),'calls',sum(len(x[-1])for x in h.corpus),'callback snapshots',flush=True)
