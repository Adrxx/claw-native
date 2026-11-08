#!/usr/bin/env python3
"""Complete original v1.0/native attack buffers, callback ordering, and histories."""
import ctypes as C
import struct
import attack_input_helpers as h

count=0
def check(s,t,entry,code=0,label='case'):
    global count
    h.compare(s,t,entry,(label,count),code);count+=1

def environment():
    h.marker=h.rng.randrange(8);h.targetToken=h.rng.choice([0,h.TARGET]);h.projectileToken=h.rng.choice([0,h.PROJECTILE])
    h.distance=h.rng.choice([-2147483648,-1,0,20,31,32,63,64,149,150,151,999999,2147483647])
    h.randomResults=[h.rng.randrange(32768)for _ in range(8)];h.liftResult=h.rng.choice([0,1])

# Every selector/entry/updater/helper executes the original body. External
# registry, audio, target query, RNG, creation, lift, and marker5 boundaries
# are recorded with receiver checks and exact original argument checks.
for entry in (0x41d850,0x41dd80,0x41de90,0x41c5a0,0x4170f0,0x41e660,0x417380):
    for case in range(6000):
        s,t=h.new();environment();check(s,t,entry,case%22,'random')
    print(f'{entry:08x}: 6000 comparisons passed',flush=True)

for facing in (0,1,0xffffffff):
    for code in (0,2,11,17,19,0xffffffff):
        s,t=h.new();environment();s.privateWords[0]=facing;s.actor[0x138//4]=0x80000000
        check(s,t,0x41de90,code,'directed-rectangle-sentinel')
    s,t=h.new();s.logicState=5000;check(s,t,0x417380,label='directed-lift-guard')

# Simultaneous inputs; selected weapon; all original ground, air, duck modes;
# pressed versus held; active attacks suppress new selection before any query.
for logic in (4,8,9,24,25,26,27,5002,5003):
    for weapon in (0,1,2,3,4):
        for pressed in (0,2,4,0x20,0x40,0x80,0x100,0x1e6):
            for held in (0,0x1e6,0x4000000,0x5000000):
                s,t=h.new();environment();s.logicState=logic;s.privateWords[1]=0;s.privateWords[12]=weapon;t.pressed=pressed;s.inputHeld=held
                s.actor[0xcc//4]=1;s.actor[0x4c//4]=500;s.actor[0x50//4]=1000;s.actor[0x124//4]=60
                t.targetActor[0x4c//4]=500;t.targetActor[0x50//4]=1000;t.targetActor[0x124//4]=60;t.targetActor[0x164//4]=1
                h.targetToken=h.TARGET;h.distance=31;check(s,t,0x41d850,label='directed-input')

# Charge interpolation, unsigned countdown wrap, launch failure, ammo guards,
# repeat, release, auto-release, and end-of-animation cleanup.
for weapon in (1,2,3):
    for ammo in (0,1,0xffffffff):
        for charge in (0,49,50,51,1999,2000,2001,0xffffffff):
            for success in (0,h.PROJECTILE):
                s,t=h.new();environment();s.privateWords[1]=1;s.privateWords[4]=0;s.privateWords[12]=weapon
                s.privateWords[28]=ammo;s.privateWords[29]=ammo;s.privateWords[30]=ammo;s.privateWords[64]=charge;s.privateWords[65]=50;s.privateWords[66]=2000
                s.actor[0x1a4//4]=0;h.marker=2;h.projectileToken=success;check(s,t,0x41c5a0,label='directed-launch')

# Original 0x41d750 scans the actual linked object list without an adapted
# target-query result. Tie order, wrapping edges, vertical limits, and filters.
nearest=0;h.o.realTargetQuery=True
for case in range(6000):
    s,t=h.new();h.prepare(s,t);n=h.rng.randrange(9);candidates=(h.Candidate*n)()
    h.o.write_words(h.OBJECTS+0x14,[0x1010000 if n else 0]);selected={}
    for i in range(n):
        b=candidates[i];b.token=0x1020000+i*0x1000
        for j in range(128):b.actor[j]=h.rng.getrandbits(32)
        b.actor[0xd0//4]=h.rng.choice([4,0x200,0x20,0]);b.actor[0x50//4]=(s.actor[0x50//4]+h.rng.choice([-100,-99,-1,0,1,99,100,0x80000000]))&0xffffffff
        b.actor[0x4c//4]=(s.actor[0x4c//4]+h.rng.randint(-200,200))&0xffffffff
        b.actor[0x128//4]=h.rng.randint(-60,0)&0xffffffff;b.actor[0x130//4]=h.rng.randint(0,60);b.actor[0x164//4]=h.rng.choice([0,1,0x400,0x401])
        h.o.write_words(b.token,b.actor);h.o.write_words(0x1010000+i*16,[0x1010000+(i+1)*16 if i+1<n else 0,0,b.token]);selected[b.token]=list(b.actor)
    beforeActor=list(s.actor);beforePrivate=list(s.privateWords);beforeTarget=list(t.targetActor)
    result=h.o.call(0x41d750,0,struct.pack('<IIII',h.A,h.L,h.P,0x100f000));token=h.o.read_words(0x100f000,1)[0]
    actual=h.lib.claw_player_nearest_attack_target(C.byref(s),C.byref(t),candidates,n)
    assert actual==C.c_int32(result).value and t.targetToken==token,(case,'nearest',result,actual,token,t.targetToken)
    assert list(t.targetActor)==(selected[token]if token else beforeTarget),(case,'nearest snapshot')
    assert list(s.actor)==beforeActor and list(s.privateWords)==beforePrivate,(case,'nearest mutations')
    nearest+=1
h.o.realTargetQuery=False

# Original 0x4207b0 uses signed remainder and its zero-span coin-flip branch.
rangeCount=0
for case in range(3000):
    s,t=h.new();h.prepare(s,t);h.attack=t;h.nativeEvents.clear();h.randomIndex=0
    lower=h.rng.getrandbits(32);upper=h.rng.choice([lower,(lower-1)&0xffffffff,(lower+2)&0xffffffff,h.rng.getrandbits(32)])
    h.randomResults=[h.rng.randrange(32768)]
    result=h.o.call(0x4207b0,0,struct.pack('<II',lower,upper));actual=h.lib.claw_player_attack_random_range(C.byref(s),lower,upper,h.dependency,None)
    assert result==actual and h.nativeEvents==h.o.events,(case,'range',result,actual)
    rangeCount+=1

# Persistent histories retain private charge, repeat, ammo, latched input and
# restore tokens across entry/update/cleanup, with alternating delta sources.
chainCount=0
for history in range(256):
    s,t=h.new();environment();s.privateWords[75]=0;s.privateWords[1]=0;s.actor[0x1a4//4]=0
    s.privateWords[0]=history%2;s.privateWords[12]=history%3+1;s.logicState=(24,4,26)[history%3];t.pressed=4
    h.randomResults=[0,29,30,24,25,34,35,32767];h.targetToken=0
    for cycle in range(3):
        check(s,t,0x41d850,label='chain-selector');chainCount+=1
        if cycle==0 and history%3==0:
            check(s,t,0x417380,label='chain-stop-to-attack');chainCount+=1
        for marker in (1,2,3,2,4,4,5):
            h.marker=marker;h.projectileToken=h.PROJECTILE if (history+marker)%2 else 0
            s.stageDelta=(0,17,80,2001,0xffffffff)[(history+marker)%5];s.animationDelta=(1,16,33)[marker%3];s.inputHeld=0x104 if marker==4 and cycle%2 else 0
            check(s,t,0x41c5a0,label='chain-marker');chainCount+=1
        s.actor[0x1a4//4]=1;s.actor[0x19c//4]=0;h.marker=0;check(s,t,0x41c5a0,label='chain-complete');chainCount+=1
        s.actor[0x1a4//4]=0

print(f'PASS: {count} complete buffer/event comparisons including {chainCount} chained calls; {nearest} real object-list queries; {rangeCount} real range helpers; {len(h.o.executed)} original instruction addresses.')
