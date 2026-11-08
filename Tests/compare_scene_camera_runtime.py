#!/usr/bin/env python3
"""Complete original scene input/camera functions and projection metadata."""
import ctypes as C,json
import scene_camera_helpers as g
for i in range(128):
 for f,t in[(0x430d30,g.INPUT),(0x430d80,g.INPUT),(0x4b3430,g.DEVICE)]:
  g.setup();g.put(g.DEVICE+0x1d0,[i%2]);g.compare(f,t,f'input-default/{f:x}/{i}',i)
for i in range(180):
 for f,t in[(0x46c860,g.OWNER),(0x430ec0,g.INPUT),(0x431300,g.INPUT),(0x4b3490,g.DEVICE),(0x4b3ab0,g.DEVICE),(0x486240,g.CAMERA),(0x486d70,g.CAMERA),(0x486d30,0),(0x42d5f0,g.WORLD),(0x4d0a60,g.P0),(0x4d0c50,g.P0)]:
  g.setup();g.policy=i%3;g.randomValues=[g.rng.getrandbits(32)for _ in range(3)]
  if i%3==0:g.globals.forcedX=g.rng.randrange(-100,2000)&0xffffffff;g.globals.forcedY=g.rng.randrange(-100,2000)&0xffffffff
  if i%4==0:g.globals.detachedMode=1
  g.compare(f,t,f'{f:x}/{i}',g.RECT if f==0x4d0c50 else g.rng.randrange(-500,4000)&0xffffffff,g.rng.randrange(-500,4000)&0xffffffff)
print(json.dumps({'calls':g.calls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed)}))
# Thresholds, world edges, death/hazard modes, forced target, shake strict< and
# detached cancellation predicates with retained input state.
for state in(0,24,26,0x138b,0x138c,0x22b8,55):
 for playerState in(24,26,0x138b,0x138c):
  for delta in(0,1,16,33,0xffffffff):
   g.setup();g.put(g.L+0x1c,[state]);g.put(g.PL+0x1c,[playerState]);g.globals.animationDelta=delta;g.globals.animationNow=10;g.globals.shakeUntil=11;g.randomValues=[0xffffffff,0x80000000,35]
   g.put(g.CP,[100,100,100,100,delta]);g.put(g.PLAYER+0x4c,[600,601]);g.compare(0x486240,g.CAMERA,f'directed-camera/{state}/{playerState}/{delta}')
for x in(-2048.5,-1.,0.,319.,320.,639.,640.,2048.5):
 for flags in(0,4,8,12):
  g.setup();g.put(g.P0+8,[flags]);g.put(g.P0+0x10,[g.fb(x),g.fb(x)]);g.put(g.P0+0x30,[320,240]);g.compare(0x4d0a60,g.P0,f'edge/{x}/{flags}')
for scenario in range(6):
 g.setup();g.globals.detachedMode=1
 if scenario==1:g.globals.detachedOwnerToken=0
 if scenario==2:g.put(g.DET+0x14,[0])
 if scenario==3:g.put(g.CELL,[0])
 if scenario==4:g.put(g.INPUT+8,[1])
 if scenario==5:g.put(g.INPUT+8,[0x1000000])
 g.compare(0x486240,g.CAMERA,f'detached/{scenario}')
# Normal and18ms-substep original frame graphs with the real camera scheduled
# through its actual generic actor/logic list. Spatial-grid services remain
# explicit; single camera actor has no eligible interaction peers.
CONTAINER,NODE=g.BASE+0xf000,g.BASE+0x19000
joined=0
for delta in(0,1,18,19,35,36,37,99):
 for step in range(12):
  g.setup();g.policy=0;g.randomValues=[17,18,19];g.put(g.CFG+0x30,[0]);g.put(g.OWNER+0x764,[0]);g.put(g.PAR+8,[CONTAINER]);g.put(CONTAINER,[0x513c20,0,0,g.PAR,0x5107bc,NODE,NODE,1,0,0,10]);g.put(NODE,[0,0,g.CAMERA]);g.put(g.CAMERA,[0x5137f0]);g.put(g.CAMERA+8,[0]);g.put(g.CAMERA+0xd4,[0]);g.put(g.L+0x10,[0x486240]);g.put(g.L+0x20,[0,0]);g.put(g.L+0x1c,[0 if step==0 else 24])
  g.stage=g.Stage(g.Frame(1000,delta),2000,g.PLAYER);g.sceneGlobals=g.SceneGlobals(3,(g.C.c_uint32*5)(0x5108fc,0,0,0,0),(g.C.c_uint32*5)(0x5108fc,0,0,0,0),g.Frame(900,16));g.globals.stageDelta=delta;g.globals.animationNow=900;g.globals.animationDelta=16;g.clockValue=1000;g.globals.shakeUntil=0
  f=0x46ad70 if 18<delta<100 else 0x46ace0;g.compare(f,g.OWNER,f'joined/{delta}/{step}',int(f==0x46ad70));joined+=1
report={'calls':g.calls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'joinedNormalSubstepFrames':joined,'rawHeapBytesCompared':g.SIZE}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
# Retained complete frame histories, switching modes/forced targets/death while
# input latch and actual five-word camera allocation survive successive frames.
retained=0
for history in range(10):
 g.setup();g.policy=0;g.randomValues=[17,18,19];g.put(g.CFG+0x30,[0]);g.put(g.OWNER+0x764,[0]);g.put(g.PAR+8,[CONTAINER]);g.put(CONTAINER,[0x513c20,0,0,g.PAR,0x5107bc,NODE,NODE,1,0,0,10]);g.put(NODE,[0,0,g.CAMERA]);g.put(g.CAMERA,[0x5137f0]);g.put(g.CAMERA+8,[0]);g.put(g.CAMERA+0xd4,[0]);g.put(g.L+0x10,[0x486240]);g.put(g.L+0x20,[0,0]);g.put(g.L+0x1c,[0]);g.stage=g.Stage(g.Frame(1000,16),2000,g.PLAYER);g.sceneGlobals=g.SceneGlobals(3,(g.C.c_uint32*5)(0x5108fc,0,0,0,0),(g.C.c_uint32*5)(0x5108fc,0,0,0,0),g.Frame(984,16));g.globals.stageDelta=16;g.globals.animationNow=984;g.globals.animationDelta=16;g.globals.shakeUntil=0
 for step in range(12):
  delta=[16,19,35,18,37,1][step%6];g.stage.stage.nowMilliseconds+=delta;g.stage.stage.deltaMilliseconds=delta;g.stage.accumulatedMilliseconds+=delta;g.clockValue=g.stage.stage.nowMilliseconds;g.put(g.PLAYER+0x4c,[100+step*75,200+step*100]);g.put(g.PLAYER+0xcc,[[1,3,4,8][step%4]]);g.put(g.PL+0x1c,[26 if step==7 else 0x138b if step==8 else 24]);g.put(g.PV+0x110,[0]);g.globals.forcedX=1700 if step in(3,4)else 0xffffffff;g.globals.forcedY=1900 if step in(3,4)else 0xffffffff
  if step==6:g.globals.shakeUntil=g.clockValue+100
  f=0x46ad70 if 18<delta<100 else 0x46ace0;g.compare(f,g.OWNER,f'retained-frame/{history}/{step}',int(f==0x46ad70));retained+=1
# Exact projection fields feed frozen4c96d0; no percentage/centering inference.
projections=0
for i in range(100):
 g.setup();g.compare(0x42d5f0,g.WORLD,f'projection/world/{i}',g.rng.randrange(3000),g.rng.randrange(3000));out=g.Projection();fault=g.C.c_uint32();assert g.lib.claw_scene_camera_projection(g.P0,g.heapHost,g.C.byref(out),g.C.byref(fault))and not fault.value
 old=bytes(g.heap);x,y=g.C.c_uint32(g.rng.getrandbits(32)),g.C.c_uint32(g.rng.getrandbits(32));originalX,originalY=x.value,y.value;g.lib.claw_sprite_project(g.C.byref(out),g.C.byref(x),g.C.byref(y));px=g.BASE+0x1a000;g.u.mem_write(g.BASE,old);g.m.write_words(px,[originalX,originalY]);g.m.call(0x4c96d0,g.P0,g.struct.pack('<2I',px,px+4));assert g.m.read_words(px,2)==[x.value,y.value];projections+=1
# Original renderer caller witness: real42ce90 instructions reach virtual init
# with640/480 in both valid bit-depth modes. Renderer failure exits before any
# unrelated resource bootstrap. Native module does not claim this UI body.
RENDERER,VT=g.BASE+0x1b000,g.BASE+0x1b100
OPEN,CLOSE=g.OSBASE+0x300,g.OSBASE+0x310;rendererEvents=[]
def rendererHook(uc,a,size,user):
 if a not in(OPEN,CLOSE,0x42c0b0):return
 sp=uc.reg_read(g.UC_X86_REG_ESP);n=5 if a==OPEN else 1 if a==0x42c0b0 else 0;args=tuple(g.m.read_words(sp+4,n));rendererEvents.append((a,uc.reg_read(g.UC_X86_REG_ECX),args));g.returned(n*4,0)
g.u.hook_add(g.UC_HOOK_CODE,rendererHook)
viewportWitnesses=[]
for mode in(8,16):
 for flag in(0,1):
  g.setup();g.u.mem_write(g.BASE,bytes(g.heap));g.m.write_words(0,[0x12345678]);g.m.write_words(g.MGR+0x30,[RENDERER]);g.m.write_words(g.MGR+0x34,[0]);g.m.write_words(g.MGR+0x5c,[0]);g.m.write_words(g.MGR+0x78,[0]);g.m.write_words(RENDERER,[VT]);g.m.write_words(VT+0x18,[OPEN,CLOSE]);g.m.write_words(0x537234,[flag]);rendererEvents.clear();g.native=False
  assert g.m.call(0x42ce90,g.MGR,g.struct.pack('<I',mode))==0
  event=next(e for e in rendererEvents if e[0]==OPEN);assert event[2]==(0x123,640,480,mode,5 if flag else 1),event;viewportWitnesses.append({'mode':mode,'flag':flag,'arguments':list(event[2])})
g.native=True
report={'calls':g.calls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'joinedNormalSubstepFrames':joined,'retainedNormalSubstepFrames':retained,'projectionComparisons':projections,'renderer640x480Witnesses':viewportWitnesses,'rawHeapBytesCompared':g.SIZE}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
