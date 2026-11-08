#!/usr/bin/env python3
"""Complete original damage/death buffers, event snapshots, and chained histories."""
import ctypes as C
import player_damage_helpers as h

count=0
def check(s,t,i,entry,label,notice=0):
    global count
    h.compare(s,t,i,entry,(label,count),notice);count+=1

def environment():
    h.gameMode=h.rng.choice([0,1,4,0xffffffff]);h.marker=h.rng.choice([0,1,2,3]);h.randomResults=[h.rng.randrange(32768)for _ in range(9)]
    h.resolvedSound=h.rng.choice([0,h.SOUND]);h.collectReturn=h.rng.choice([0,1]);h.collisionMode=h.rng.choice([1,2,3,4,5,8]);h.hazard=h.rng.choice([1,4]);h.platform=(h.rng.getrandbits(32),h.rng.getrandbits(32))

for entry in (0x41ce80,0x417b00,0x417c50,0x41c030,0x41c2b0,0x41c440,0x415df0):
    for n in range(6000):
        s,t,i=h.new();environment()
        if entry==0x415df0:s.logicState=h.rng.choice([28,31,5004,5005])
        check(s,t,i,entry,'random',n%2)
    print(f'{entry:08x}: 6000 complete comparisons passed',flush=True)

# All hit categories, damage signs and health thresholds. This includes
# health/ammo/treasure pickup branches, carried-enemy suppression, projectile
# persistence/destruction and virtual destruction, and specialtype40 hint.
for kind in (0,4,0x10,0x40,0x100,0x10000,0x40000,0x100000,0x200000,0x800000,0x1000000):
    for flags in (0,0x10,0x20,0x30):
        for health in (0,1,99,100,0xffffffff,0x80000000,0x7fffffff):
            for amount in (0,1,100,0xffffffff,0x80000000,0x7fffffff):
                s,t,i=h.new();environment();s.actor[0x74//4]=t.attackerToken=h.ATTACKER;t.attackerActor[0xd0//4]=kind;t.attackerActor[0x164//4]=flags;t.attackerActor[0x104//4]=amount;s.actor[0x10c//4]=health
                t.attackerActor[0xfc//4]=0x26bf if kind==0x40 else amount;s.privateWords[75]=0;s.logicState=24
                t.configurationToken=0 if (flags&0x10)else h.CONFIG;check(s,t,i,0x41ce80,'directed-hit')

# Fall updater converts the same physics Y delta twice. Threshold800 and
# private6 once-only guard determine posting; spike posting needs animation
# completion. Post results distinguish signed lives1 versus<=0, mode4 and
# infinite-lives behavior, without inventing host respawn processing.
for logic in (5004,5005):
    for lives in (0,1,2,9,0xffffffff,0x80000000,0x7fffffff):
        for mode in (0,4):
            for infinite in (0,1):
                for guard in (0,1):
                    s,t,i=h.new();environment();s.logicState=logic;s.privateWords[31]=lives;s.privateWords[6]=guard;s.privateWords[16]=801
                    t.infiniteLives=infinite;h.gameMode=mode;s.actor[0x1a4//4]=1;s.actor[0x19c//4]=0;s.stageDelta=0;s.physics.stopped=1
                    check(s,t,i,0x415df0,'directed-death-post')

# Common epilogue invokes the recovered spike entry directly for hazard flags
# or supported foot attribute4, except when already in5004/5005. These calls
# run both original/new spike bodies, rather than adapting the transition away.
for logic in (28,31,5004,5005):
    for flags in (0,0x10,0x400000,0x400010):
        for ignore in (0,1):
            for attribute in (1,4):
                s,t,i=h.new();environment();s.logicState=logic;s.actor[8//4]=flags;s.privateWords[75]=0
                s.actor[0x1a4//4]=0;s.actor[0x19c//4]=1;i.ignoreHazards=ignore;i.cheat=0;h.hazard=attribute
                check(s,t,i,0x415df0,'directed-hazard-entry')

# Real original CRT RNG body with only the OS/TLS context accessor adapted.
# Persistent shared stream is checked after every chained callback.
h.realRandom=True;chains=0
for history in range(256):
    s,t,i=h.new();environment();h.nativeRandomSeed=h.rng.getrandbits(32);h.gameMode=history%5;h.platform=(0,0);h.resolvedSound=h.SOUND;h.collisionMode=1;h.hazard=1
    s.actor[0x74//4]=t.attackerToken=h.ATTACKER;t.attackerActor[0xd0//4]=4;t.attackerActor[0x164//4]=0;t.attackerActor[0x104//4]=7;s.actor[0x10c//4]=100;s.privateWords[75]=0;s.privateWords[1]=0;s.privateWords[6]=0;s.privateWords[31]=history%4+1;s.logicState=24
    s.actor[0x1a4//4]=0;s.actor[0x19c//4]=1;i.pressed=0;i.cheat=0;i.ignoreHazards=1
    for hit in range(15):
        check(s,t,i,0x41ce80,'chain-hit');chains+=1
        if s.logicState==31:
            h.marker=1;check(s,t,i,0x415df0,'chain-hurt-marker');chains+=1
            s.actor[0x1a4//4]=1;s.actor[0x19c//4]=0;check(s,t,i,0x415df0,'chain-hurt-complete');chains+=1
            s.actor[0x1a4//4]=0;s.actor[0x19c//4]=1
    assert s.logicState==5004 and s.actor[0x10c//4]==0
    for tick in range(12):
        s.stageDelta=33;s.animationDelta=17;s.physics.minimum[:]=[-2147483647.]*3;s.physics.maximum[:]=[2147483646.]*3;s.physics.maximumDelta[:]=[32,32,2147483646];s.physics.maximumVelocity[:]=[1000]*3;s.physics.stopped=0
        check(s,t,i,0x415df0,'chain-fall-death');chains+=1
    s.privateWords[16]=801;check(s,t,i,0x415df0,'chain-post');chains+=1
    check(s,t,i,0x415df0,'chain-post-guard');chains+=1
h.realRandom=False

# Full recovered hurt body chained through the actual original Level1 movement
# resolver. Scene object list is empty and all tile callbacks execute normally.
h.world=h.install_world(True);h.realCollision=True;realHurt=0
for n in range(128):
    s,t,i=h.new();environment();s.logicState=31;s.actor[0x4c//4]=689;s.actor[0x50//4]=4730;s.actor[0xdc//4]=10;s.actor[0xe0//4]=10;s.actor[0xd0//4]=2;s.actor[0xcc//4]=1;s.actor[0x80//4]=0;s.actor[8//4]=0x80;s.actor[0x1a4//4]=0;s.actor[0x19c//4]=1;s.actor[0x148//4]=200 if n%2 else 0xffffff38
    s.actor[0x118//4:0x128//4]=[0xfffffff0,0xffffffcc,16,60];s.actor[0x128//4:0x138//4]=[0xffffffea,0xffffffd3,15,52];h.marker=1;s.animationDelta=17
    check(s,t,i,0x41c030,'level1-real-hurt');realHurt+=1
h.realCollision=False

# Native scope guard for states owned by other portable modules.
rejections=0
for logic in (0,1,4,8,9,23,24,25,26,27,5000,5002,5003,0xffffffff):
    s,t,i=h.new();s.logicState=logic;h.damage=t;h.input=i;h.nativeEvents.clear();before=(bytes(s),bytes(t),bytes(i))
    assert h.lib.claw_player_dispatch_damage(C.byref(s),C.byref(t),C.byref(i),h.dependency,None)==0
    assert before==(bytes(s),bytes(t),bytes(i))and not h.nativeEvents;rejections+=1

print(f'PASS: {count} full original/native buffers and ordered complete event snapshots; {chains} chained calls with original CRT RNG; {realHurt} real Level1 hurt/movement comparisons; {rejections} unchanged-state rejections; {len(h.o.executed)} original instruction addresses.')
