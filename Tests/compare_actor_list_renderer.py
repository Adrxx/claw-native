#!/usr/bin/env python3
"""Thin public export of frozen actor-list loop versus whole original4c91d0."""
import json
import plane_renderer_helpers as g
C=g.C
g.lib.claw_plane_renderer_actor_list.argtypes=[C.c_uint32,C.c_uint32,g.RendererHost,C.POINTER(C.c_uint32)]
calls=events=0
for i in range(64):
 g.reset();g.policy=i%5
 count=i%7
 g.put(g.SCENE+0x14,[g.NODES[0] if count else 0])
 for j in range(count):
  g.put(g.NODES[j],[g.NODES[j+1] if j+1<count else 0,g.NODES[j-1] if j else 0,g.ACTORS[j]])
  if (i+j)%4==0:g.put(g.ACTORS[j]+0x174,[0])
  if (i+j)%3==0:g.put(g.ACTORS[j],[g.VT])
 g.native=True;before=bytes(g.heap);g.events=[];g.graphicsCount=0;fault=C.c_uint32()
 assert g.lib.claw_plane_renderer_actor_list(g.SCENE,g.TARGET,g.host,C.byref(fault))==1 and fault.value==0
 expected=g.snapshot();expectedEvents=list(g.events)
 g.native=False;g.events=[];g.graphicsCount=0;g.u.mem_write(g.BASE,before);g.m.write_words(0,[0x12345678])
 g.m.call(0x4c91d0,g.SCENE,g.struct.pack('<I',g.TARGET))
 assert g.snapshot()==expected and g.events==expectedEvents,('original4c91d0',i)
 g.native=True;calls+=1;events+=len(expectedEvents)
print('PASS actor-list export',json.dumps({'wholeOriginalCalls':calls,'orderedFullSnapshots':events,'rawHeapBytes':g.SIZE,'originalAddresses':len(g.m.executed),'scope':'empty/1..6 actor chains, missing images, alternate actor draw and image virtuals; existing unchanged frozen body'}))
