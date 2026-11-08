#!/usr/bin/env python3
"""Original complete state0/reset23 callback versus portable initialization."""
import ctypes as C
import player_initialization_helpers as h

count=0
def check(s,j,i,label,constructor=False):
    global count
    h.compare(s,j,i,(label,count),constructor);count+=1

for constructor in (True,False):
    for n in range(6000):
        s,j,i=h.new();h.gameMode=h.rng.choice([0,1,4,0xffffffff]);h.imageManager=h.rng.choice([0,h.IMAGE_MANAGER]);h.groundDelta=h.rng.choice([-100,-1,0,1,7,100]);h.hazard=h.rng.choice([1,4])
        check(s,j,i,'constructor'if constructor else 'full-callback',constructor)
    print(f'{"defaults"if constructor else "new-level/reset"}: 6000 complete comparisons passed',flush=True)

# Original constructor defaults, then the complete state0 callback, repeatedly
# followed by reset23. Retains saved words, ammo, physics untouched by reset,
# ground-position saved spawn, checkpoint fallback, and resource adjustments.
chains=0
for history in range(256):
    s,j,i=h.new();s.logicState=0;j.difficulty=history%2;h.gameMode=(0,4)[history%2];h.imageManager=h.IMAGE_MANAGER;h.hazard=1;h.groundDelta=7
    j.startX=689;j.startY=4723;j.worldWidth=24576;j.worldHeight=6144;j.accumulatorMinimum=history;j.accumulatorStep=h.rng.choice([0,1,7,0xffffffff]);i.pressed=0;i.cheat=0;i.ignoreHazards=1
    check(s,j,i,'chain-defaults',True);chains+=1
    check(s,j,i,'chain-start');chains+=1
    for reset in range(8):
        s.logicState=23;j.checkpointX=0xffffffff if reset%2 else 900;j.checkpointY=4800 if reset%3 else 0xffffffff
        s.privateWords[28]=reset;s.privateWords[29]=reset+2;s.privateWords[30]=reset+1
        s.privateWords[1]=reset%2;s.privateWords[75]=h.W if reset%3 else 0;s.privateWords[0]=reset%2
        s.stageDelta=(0,1,16,0xffffffff)[reset%4];s.animationDelta=(17,0)[reset%2]
        check(s,j,i,'chain-reset');chains+=1
    s.logicState=0;check(s,j,i,'chain-reinitialize');chains+=1

# Saved-state inventory gate preserves words34..43 when word9 !=0 and clears
# them when0, even after copying all78 arbitrary saved/default words.
for saved in (0,1,0xffffffff):
    for checkpoint in ((0xffffffff,1),(1,0xffffffff),(0xffffffff,0xffffffff),(900,4800)):
        s,j,i=h.new();s.logicState=0;j.defaults[9]=saved;j.checkpointX,j.checkpointY=checkpoint
        h.gameMode=0;h.imageManager=h.IMAGE_MANAGER;h.hazard=1;check(s,j,i,'directed-saved')

# Common loader baseline + global physics constructor + new-game defaults +
# full original callback with real Level1 tile placement. The generic loader
# baseline has independent original4d17e0 comparisons in its owning suite;
# this integration asserts state0 against the exact original callback.
h.world=h.install_world(True);h.realGround=True;h.hazard=1;levelOne=0
for n in range(128):
    s,j,i=h.new();runtime=h.ObjectRuntime()
    runtime.actor[:]=s.actor[:]
    for k in range(93):runtime.logic[k]=h.rng.getrandbits(32)
    context=h.ObjectContext(h.SC,h.A,h.L,h.M,h.world.width,h.world.height,0,(C.c_uint32*3)(0,0,0),0x101b000,0x415df0,n%3)
    h.lib.claw_world_object_construct(C.byref(runtime),C.byref(context),0)
    assert h.lib.claw_world_object_initialize(C.byref(runtime),C.byref(context),689,4723,4000)==1
    s.actor[:]=runtime.actor[:];s.logicState=runtime.logic[0x1c//4];j.privateToken=runtime.logic[0x14//4]
    h.lib.claw_physics_construct(C.byref(s.physics));j.worldWidth=h.world.width;j.worldHeight=h.world.height;j.startX=689;j.startY=4723
    j.difficulty=n%2;j.resetObjectToken=0;j.configurationToken=h.CONFIG;i.pressed=0;i.cheat=0;i.ignoreHazards=1;i.invulnerabilityTimer=0
    h.gameMode=0;h.imageManager=h.IMAGE_MANAGER
    check(s,j,i,'level1-defaults',True);check(s,j,i,'level1-real-ground');levelOne+=1
    assert (s.actor[0x4c//4],s.actor[0x50//4])==(689,4730),'Level1 ground spawn'
    assert (s.privateWords[19],s.privateWords[20])==(689,4730),'Saved spawn is ground position'
    assert s.privateWords[12]==1 and s.privateWords[18]==100,'Initial weapon/health'
    assert s.actor[0xdc//4]==10 and s.actor[0xe0//4]==10,'Original loader collision probes'
    assert tuple(s.physics.acceleration)==(0,2250,0)and tuple(s.physics.velocity)==(0,0,0),'Initial physics'
    assert s.physics.maximumDelta[0]==32 and s.physics.maximumDelta[1]==32 and tuple(s.physics.maximumVelocity)==(1000,1000,1000),'Initial limits'

# Unsupported states must remain completely unchanged and invoke no adapter.
rejections=0
for logic in (1,4,8,9,24,25,26,27,5000,5002,5003,0xffffffff):
    s,j,i=h.new();s.logicState=logic;h.initialization=j;h.input=i;h.nativeEvents.clear();before=(bytes(s),bytes(j),bytes(i))
    assert h.lib.claw_player_dispatch_initialization(C.byref(s),C.byref(j),C.byref(i),h.dependency,None)==0
    assert before==(bytes(s),bytes(j),bytes(i))and not h.nativeEvents;rejections+=1

print(f'PASS: {count} full original/native buffer and ordered full-snapshot event comparisons; {chains} chained calls; {levelOne} original Level1 ground-placement startup integrations; {rejections} unchanged-state rejections; {len(h.o.executed)} original instruction addresses.')
