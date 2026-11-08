#!/usr/bin/env python3
"""Actual original plane tile loops, live rectangles and world z dispatch."""
import json
from unicorn import UC_ERR_READ_UNMAPPED
import plane_renderer_helpers as g
for i in range(120):
 g.reset();g.policy=i%5;left=g.rng.randrange(300);top=g.rng.randrange(200);g.put(g.PLANE[0]+0x40,[left,top,left+639,top+479]);g.currentPlane=g.PLANE[0];g.compare(0x4d0d50,g.PLANE[0],f'generated/{i}')
for i in range(80):
 g.reset();g.policy=i%5;g.put(g.WORLD+8,[i%2]);g.put(g.WORLD+0x60,[i%4-1]);g.compare(0x4cb9b0,g.WORLD,f'world/{i}')
for width,height in((1,1),(63,63),(64,64),(65,65),(127,127),(128,128),(640,480)):
 g.reset(viewWidth=width,viewHeight=height);g.compare(0x4d0d50,g.PLANE[0],f'small-viewport/{width}/{height}')
for sentinel in(0xffffffff,0xeeeeeeee):
 for policy in range(5):
  g.reset();g.policy=policy;g.put(g.TILES[0],[sentinel]*192);g.compare(0x4d0d50,g.PLANE[0],f'sentinel/{sentinel:x}/{policy}')
for i in range(40):
 g.reset();g.policy=i%5;g.put(g.TILES[0],[0xffffffff if j%3==0 else 0xeeeeeeee if j%3==1 else ((j%16)|((j%3)<<16))for j in range(192)]);g.put(g.PLANE[0]+0x40,[960,704,1599,1183]);g.put(g.PLANE[0]+8,[[0,4,8,12][i%4]]);g.put(g.PLANE[0]+0x60,[2,3,61,60]);g.compare(0x4d0d50,g.PLANE[0],f'wrapped-filled-cropped/{i}')
for i in range(12):
 g.reset();g.put(g.PLANE[0]+8,[2|i*4]);g.put(g.PLANE[0]+0x20,[0,0]);g.compare(0x4d0d50,g.PLANE[0],f'no-draw-before-pointers/{i}')
for i in range(40):
 g.reset();g.put(g.WORLD+8,[i%2]);g.put(g.ACTORS[i%6],[g.VT]);g.put(g.ACTORS[(i+1)%6]+0x174,[0]);g.put(g.IMAGES[0]+((i+2)%6)*64,[g.VT]);
 if i%4==0:g.put(g.SCENE,[g.VT])
 g.compare(0x4cb9b0,g.WORLD,f'polymorphic-dispatch/{i}')
# Original dereferences null on a missing/range-rejected image. An unmapped
# Windows-null-page adapter observes the real fault rather than pretending it
# was a normal original return; native reports its bounded graph fault.
invalid=0
for case in range(3):
 g.reset();g.put(g.TILES[0],[16 if case==0 else 0]+[0xffffffff]*191)
 if case==1:g.put(g.TABLES[0],[0])
 if case==2:g.put(g.SETS[0],[0])
 before=bytes(g.heap);fault=g.C.c_uint32();assert not g.lib.claw_plane_renderer_draw(g.PLANE[0],g.TARGET,g.host,g.C.byref(fault))and fault.value==1
 assert not g.lib.claw_plane_renderer_draw(g.PLANE[0],g.TARGET,g.host,None)
 g.native=False;g.u.mem_write(g.BASE,before);g.u.mem_unmap(0,4096)
 try:g.m.call(0x4d0d50,g.PLANE[0],g.struct.pack('<I',g.TARGET));raise AssertionError('expected original null graph read')
 except g.UcError as error:assert error.errno==UC_ERR_READ_UNMAPPED
 finally:g.u.mem_map(0,4096);g.native=True
 invalid+=1
actual=0
for x,y in((320,240),(400,500),(689,789),(1300,1000),(24575,6143),(0,0),(-500,-500)):
 g.actualLevel1();g.follow(x,y)
 for i,plane in enumerate(g.PLANE):g.currentPlane=plane;g.compare(0x4d0d50,plane,f'Level1/{i}/{x}/{y}');actual+=1
retained=0
for history in range(4):
 g.actualLevel1();g.put(g.WORLD+8,[history%2])
 for step in range(16):
  g.follow(320+step*1543,240+step*317);g.compare(0x4cb9b0,g.WORLD,f'retained-Level1-world/{history}/{step}');retained+=1
report={'calls':g.calls,'orderedFullHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'rawHeapBytes':g.SIZE,'actualLevel1PlaneCalls':actual,'retainedActualLevel1WorldCalls':retained,'originalInvalidImageFaultWitnesses':invalid}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
