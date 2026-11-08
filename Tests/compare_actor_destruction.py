#!/usr/bin/env python3
"""Original actor/logic destruction, raw heap ownership and ordered services."""
import ctypes as C,json
import actor_destruction_helpers as g
for i in range(180):
 for f,t in[(0x4c9be0,g.A),(0x4c9c00,g.A),(0x4c99a0,g.A),(0x4c99c0,g.A),(0x4c9a70,g.A),(0x4c9e60,g.A),(0x4c9e80,g.A),(0x4c80c0,g.L),(0x4c80e0,g.L),(0x47cc80,g.E),(0x47cca0,g.E),(0x4dbcd0,g.E+0x2f4),(0x4f6584,g.E+0x1a4),(0x4c9b30,g.A+0x188),(0x4c9b50,g.A+0x188),(0x4c8210,g.A+0x188),(0x48cf50,0)]:
  g.prepare('rat'if i%2 else'bomb');g.policy=i%4
  if i%3==0:g.put(g.A+0x6c,[0,0,0]);g.put(g.A+0x78,[0])
  if i%5==0:g.put(g.L+0x14,[0,0]);g.put(g.L+0x18,[0])
  if i%7==0:g.put(g.E+0x1a4,[g.globals.emptyStringToken,g.globals.emptyStringToken])
  if i%4==1:
   g.put(g.S,[g.VT]);g.put(g.E3+0x18,[0]);g.put(g.E3+0x14,[0])
  if i%4==2:g.put(g.L,[g.VT+0x20])
  if i%9==0:g.globals.holderActorToken=0
  if i%9==1:g.put(g.HOLDER+0x6c,[0])
  if i%9==2:g.put(g.HOLDER_L+0x1c,[14])
  g.compare(f,t,f'{f:x}/{i}',g.rng.choice([0,1,2,0x100,0x101,0xffffffff])if f!=0x48cf50 else g.rng.choice([g.E,0,g.E2]))
# Actual virtual actor entry selection, retained reset-to-destruction chains.
for i in range(150):
 g.prepare();g.policy=i%4
 g.put(g.A,[g.rng.choice([0x5137f0,0x513770])]);g.compare(0,g.A,f'virtual/{i}',0,select=True)
 g.compare(0x4c9c00,g.A,f'retained-empty/{i}')
 g.put(g.A,[0x5137f0]);g.compare(0,g.A,f'retained-final-free/{i}',1,select=True)
# Genuine deferred scene deletion with generic actor->logic->Rat/Bomb chains.
for i in range(100):
 g.prepare('rat'if i%2 else'bomb');g.policy=0
 container=g.BASE;node=g.BASE+0xf200;block=g.BASE+0xf1f0
 g.put(container,[0x513c20,0,0,g.HOLDER,0x5107bc,node,node,1,0,block,10]);g.put(node,[0,0,g.A]);g.put(block,[0]);g.live[block]=True
 g.put(g.A+0x68,[node]);g.put(g.A+8,[0x10000 if i%3 else 0x90000]);g.put(g.L+0x10,[g.SCENE_CALLBACK]);g.put(g.L+0x20,[g.rng.choice([0,1,16,17]),0]);g.put(g.A+0x70,[0]);g.put(g.A+0x78,[0])
 g.currentScene=g.SceneGlobals(3,(g.C.c_uint32*5)(0x5108fc,0,0,0,0),(g.C.c_uint32*5)(0x5108fc,0,0,0,0),g.Frame(1000,16))
 g.compare(0x4c8fc0,container,f'scene-joined/{i}')
 assert g.words(container+5*4,5)==[0,0,0,0,0]
 assert not g.live[g.A] and not g.live[g.L] and not g.live[g.E] and not g.live[block]
report={'joinedSceneDeletions':100,'calls' :g.calls,'orderedHeapEvents':g.event_count,'originalAddresses':len(g.m.executed),'rawHeapBytesCompared':g.SIZE}
(g.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
