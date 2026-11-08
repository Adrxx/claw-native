"""Differential checks of original climbing and long-fall landing updates."""
import ctypes as C
import air_state_helpers as h

def state():
    s=h.new()
    s.actor[0x118//4:0x128//4]=[(-16)&0xffffffff,(-52)&0xffffffff,16,60]
    s.actor[0x128//4:0x138//4]=[(-15)&0xffffffff,(-45)&0xffffffff,22,52]
    s.actor[0x19c//4]=h.rng.choice([0,0,1,0xffffffff]);s.actor[0x1a4//4]=h.rng.choice([0,1,2])
    s.privateWords[26]=h.rng.choice([0,0,0,s.actor[0x50//4]+h.rng.randrange(-60,60)])&0xffffffff
    s.privateWords[11]=h.rng.choice([0,2,5,8])
    s.inputHeld=h.rng.choice([0,1,0x1000000,0x2000000,0x3000000,0x4000000,0x8000000,0xc000000])
    return s

for entry,name in ((0x41bb70,'climb'),(0x4198d0,'land')):
    for case in range(5000):
        h.collisionMode=h.o.mode=h.rng.choice([1,2,3,4,6,7])
        h.platform=(h.rng.randint(-20,20)&0xffffffff,h.rng.randint(-20,20)&0xffffffff)
        s=state();h.pressed=h.rng.choice([0,0,1])
        top=(s.actor[0x50//4]+s.actor[0x11c//4])&0xffffffff
        edge=(top+h.rng.choice([0,1,16,50,112,113]))&0xffffffff
        h.point=lambda x,y:3 if ((y-edge)&0xffffffff)<30 else 0
        h.compare(s,entry,case)
    print(f'PASS 5000 original/native {name} updates; complete actor/private/physics/input/logic/weapon fields and ordered dependency arguments',flush=True)

# Directed image bands, idle suppression, landing completion, and clock behavior.
h.pressed=0;h.collisionMode=h.o.mode=6;h.point=lambda x,y:0
for distance,image in ((0,389),(16,389),(17,388),(33,388),(34,387),(50,387),(51,386),(67,386),(68,385),(84,385),(85,384),(101,384),(102,383),(120,383)):
    s=state();s.privateWords[75]=s.privateWords[1]=0;s.privateWords[26]=1000;s.actor[0x50//4]=(1000-60+distance)&0xffffffff;s.stageDelta=0;s.inputHeld=0;s.physics.remainder[1]=0
    h.compare(s,0x41bb70,('image',distance));assert (0x4209d0,image,0,0)in h.nativeEvents
    assert not any(e[0]==0x4c82a0 for e in h.nativeEvents)
h.collisionMode=h.o.mode=1
for held,logic in ((0,24),(0x1000000,9),(0x2000000,8),(0x3000000,8)):
    s=state();s.actor[0x1a4//4]=1;s.actor[0x19c//4]=0;s.inputHeld=held
    h.compare(s,0x4198d0,('land complete',held));assert s.logicState==logic
print('PASS directed ladder image bands/animation suppression and completed landing direction priority',flush=True)

# Chained physics and full tile collision: animation/resource dependencies stay logged stubs.
h.o.realCollision=True;seen=set()
for history in range(32):
    h.nativeWorld=h.install_world();s=h.State();h.lib.claw_physics_construct(C.byref(s.physics))
    s.physics.maximumDelta[0]=s.physics.maximumDelta[1]=32;s.physics.maximumVelocity[:]=[1000.]*3
    s.actor[8//4]=0x80;s.actor[0x4c//4]=288;s.actor[0x50//4]=350;s.actor[0xdc//4]=s.actor[0xe0//4]=8;s.actor[0xd0//4]=2
    s.actor[0x118//4:0x128//4]=[(-16)&0xffffffff,(-52)&0xffffffff,16,60];s.actor[0x128//4:0x138//4]=[(-15)&0xffffffff,(-45)&0xffffffff,22,52]
    s.actor[0xcc//4]=6;s.logicState=27;s.audioRegistryDisabled=1
    for tick in range(240):
        s.stageDelta=[0,1,7,16,33,80,200][(history+tick)%7];s.animationDelta=[1,7,17,80][tick%4]
        s.inputHeld=[0x4000000,0x8000000,0][(tick//40+history)%3];h.pressed=1 if tick in (80,180) else 0
        if tick in (80,180):
            s.logicState=27;s.actor[0xcc//4]=6;s.actor[0x4c//4]=288;s.actor[0x50//4]=350;s.privateWords[26]=0;s.physics.acceleration[1]=0
        if tick in (120,220):s.logicState=5002;s.actor[0xcc//4]=1;s.actor[0x1a4//4]=1;s.actor[0x19c//4]=0
        entry={27:0x41bb70,5002:0x4198d0,4:0x41b630,25:0x418b40,24:0x4171d0,8:0x4183e0,9:0x418790}.get(s.logicState)
        assert entry is not None,('unsupported chain logic',s.logicState)
        h.compare(s,entry,(history,tick));seen.add(s.logicState)
print(f'PASS 7680 scripted chained transitions with full original point/movement/physics bodies, states {sorted(seen)}',flush=True)
print(f'{len(h.o.executed)} original instruction addresses. Generated calls stub collision/point sampling; chained calls execute both. Animation/registry/audio/weapon dependency bodies remain explicitly stubbed.')
