"""Compare complete original CaptainClaw callback branches with explicit adapters."""
import ctypes as C
import struct
import input_dispatch_helpers as h
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_ECX
from original_v10 import OriginalV10

class Input(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('pressed','invulnerabilityTimer','minimumX','maximumX','minimumY','maximumY','ignoreHazards','cheat')]
h.lib.claw_player_dispatch_input.argtypes=[C.POINTER(h.State),C.POINTER(Input),h.Callback,C.c_void_p]
h.lib.claw_player_dispatch_input.restype=C.c_uint32
THREE=(0x4171d0,0x419030,0x417dd0,0x417f20,0x4183e0,0x418790,0x41d850,0x417380,0x417590,
       0x41b630,0x418b40,0x419fd0,0x41bb70,0x4198d0,0x41a490,0x419c80,0x41c4e0,0x41f4c0,0x4170f0,0x417480,0x417c50)
responses={};observations=[];mutateHelpers=False;realHelpers=set()
changes={0x4171d0:24,0x417dd0:9,0x417f20:8,0x417590:4,0x417930:25,0x4170f0:27,0x417c50:5005}

def value(entry,a=0,b=0,c=0):
    if entry==0x4cd1c0:return int(((a-edgeOffset)&0xffffffff)<4) if teeterProbe else 0
    return responses.get(entry,0)

class Original(h.Original):
    def hook(self,u,entry,size,user):
        if entry in realHelpers:return super().hook(u,entry,size,user)
        if entry in (0x41f990,0x4bc110,0x4c6130,0x420070):
            OriginalV10.hook(self,u,entry,size,user);sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
            n={0x41f990:5,0x4bc110:0,0x4c6130:2,0x420070:2}[entry];args=self.read_words(sp+4,n)
            if entry==0x41f990:assert args==[h.A,h.L,h.P,0,0];values=[0,0,0]
            elif entry==0x4c6130:assert args==[2,0];values=[receiver,*args]
            elif entry==0x420070:assert args[0]==h.A;values=[args[1],0,0]
            else:values=[0,0,0]
            self.events.append((entry,*values));u.reg_write(UC_X86_REG_EAX,0);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(n*4 if entry==0x4c6130 else 0));return
        if entry not in THREE+(0x417930,0x41fc30,0x41e710,0x41e790,0x4bb030,0x4cd1c0,0x4cd740,0x420910,0x4a3050,0x48c8a0):
            return super().hook(u,entry,size,user)
        OriginalV10.hook(self,u,entry,size,user)
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);n=3 if entry in THREE else 0;calleePop=False
        if entry in (0x417930,0x41fc30):n=4
        elif entry in (0x41e710,0x41e790,0x420910):n=1;calleePop=entry==0x420910
        elif entry in (0x4cd1c0,0x4cd740,0x48c8a0):n=2;calleePop=entry!=0x48c8a0
        args=self.read_words(sp+4,n)
        if entry in THREE:assert args==[h.A,h.L,h.P];values=[0,0,0]
        elif entry in (0x417930,0x41fc30):assert args[:3]==[h.A,h.L,h.P];values=[args[3],0,0]
        elif entry in (0x41e710,0x41e790):assert args==[h.A];values=[0,0,0]
        elif entry==0x420910:assert receiver==h.R;values=args+[0,0]
        elif entry in (0x4cd1c0,0x4cd740):assert receiver==h.M and args[0]==h.A;values=[args[1],0,0]
        elif entry==0x48c8a0:values=args+[0]
        else:values=[0,0,0]
        self.events.append((entry,*values))
        result=value(entry,*values)
        if mutateHelpers and entry in changes:self.write_words(h.L+0x1c,[changes[entry]])
        u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(n*4 if calleePop else 0))

o=Original();h.o=o
oldDependency=h.dependency
@h.Callback
def dependency(ptr,entry,a,b,c,context):
    observations.append((entry,ptr.contents.logicState,ptr.contents.actor[0x4c//4],ptr.contents.actor[0x50//4]))
    if entry in realHelpers:
        if entry==0x41f4c0:h.lib.claw_player_update_jump_hold(ptr);return 0
        if entry==0x41e710:return h.lib.claw_player_left_ledge(ptr,dependency,None)
        if entry==0x41e790:return h.lib.claw_player_right_ledge(ptr,dependency,None)
        if entry==0x417480:return h.lib.claw_player_enter_teeter(ptr,dependency,None)&0xffffffff
    if entry in THREE+(0x417930,0x41fc30,0x41e710,0x41e790,0x4bb030,0x4cd1c0,0x4cd740,0x420910,0x4a3050,0x48c8a0):
        h.nativeEvents.append((entry,a,b,c))
        if mutateHelpers and entry in changes:ptr.contents.logicState=changes[entry]
        return value(entry,a,b,c)
    if entry in (0x41f990,0x4bc110,0x4c6130,0x420070):h.nativeEvents.append((entry,a,b,c));return 0
    return oldDependency(ptr,entry,a,b,c,context)

teeterProbe=False;edgeOffset=16
def check(s,i,label):
    h.pressed=i.pressed;h.prepare(s)
    o.write_words(h.A+0x6c,[h.L]);o.write_words(h.L+0x14,[h.P]);o.write_words(h.L+0x130,[i.invulnerabilityTimer]);o.write_words(h.L+0x2c,[i.minimumX,i.maximumX,i.minimumY,i.maximumY])
    o.write_words(0x537230,[i.ignoreHazards]);o.write_words(0x537214,[i.cheat])
    before=h.State.from_buffer_copy(s);h.nativeEvents.clear();observations.clear()
    original=o.call(0x415df0,0,struct.pack('<I',h.A));actual=h.lib.claw_player_dispatch_input(C.byref(s),C.byref(i),dependency,None)
    assert original==actual==1,(label,'return')
    expected=o.read_words(h.A,128);expected[3]=before.actor[3];expected[0x6c//4]=before.actor[0x6c//4]
    assert list(s.actor)==expected,(label,'actor',[(hex(j*4),hex(x),hex(y))for j,(x,y)in enumerate(zip(s.actor,expected))if x!=y])
    assert list(s.privateWords)==o.read_words(h.P,78),(label,'private',[(j,x,y)for j,(x,y)in enumerate(zip(s.privateWords,o.read_words(h.P,78)))if x!=y])
    assert bytes(s.physics)==o.u.mem_read(0x534db8,C.sizeof(h.Physics)),(label,'physics',[(j,x,y)for j,(x,y)in enumerate(zip(bytes(s.physics),o.u.mem_read(0x534db8,C.sizeof(h.Physics))))if x!=y][:8])
    assert s.logicState==o.read_words(h.L+0x1c,1)[0],(label,'logic')
    assert s.inputLatched==o.read_words(h.I+0xc,1)[0],(label,'latched')
    assert s.pixelScratch==o.read_words(0x544e8c,1)[0]and s.pixelScratchY==o.read_words(0x544e88,1)[0],(label,'scratch')
    assert i.invulnerabilityTimer==o.read_words(h.L+0x130,1)[0],(label,'invulnerability')
    assert h.nativeEvents==o.events,(label,'events',h.nativeEvents,o.events)

def state(logic):
    s=h.new();s.logicState=logic
    s.actor[0x118//4:0x128//4]=[(-16)&0xffffffff,(-52)&0xffffffff,16,60]
    s.actor[0x128//4:0x138//4]=[(-15)&0xffffffff,(-45)&0xffffffff,22,52]
    s.privateWords[1]=h.rng.choice([0,0,1]);s.privateWords[8]=h.rng.choice([0,1]);s.privateWords[12]=h.rng.getrandbits(32)
    s.inputHeld=h.rng.choice([0,1,0x1000000,0x2000000,0x3000000,0x4000000,0x8000000,0xc000000,0x3000001])
    return s

for logic in (4,8,9,24,25,26,27,5002,5003,5006):
    for case in range(1000):
        s=state(logic);responses={entry:h.rng.choice([0,1])for entry in (0x41d850,0x41e710,0x41e790,0x4bb030)}
        responses[0x4a3050]=h.rng.getrandbits(32);responses[0x4cd740]=h.rng.choice([0,4]);teeterProbe=h.rng.choice([False,True]);edgeOffset=16
        h.collisionMode=o.mode=h.rng.choice([1,2,3,4,6,7]);h.platform=(h.rng.randint(-20,20)&0xffffffff,h.rng.randint(-20,20)&0xffffffff)
        i=Input(h.rng.choice([0,1,8,9,0x1000000,0x2000000,0x3000000,0x3000001]),h.rng.choice([0,1,20,200]),(-100)&0xffffffff,100,(-100)&0xffffffff,100,h.rng.choice([0,1]),h.rng.choice([0,1]))
        mutateHelpers=case%2==0
        check(s,i,(logic,case))
    print(f'PASS 1000 complete original CaptainClaw callback branches from logic {logic}; adapted helpers, full inline physics/geometry and complete buffers/events',flush=True)
class Powerup(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('remaining','expired','overlaySequenceToken')]
h.lib.claw_player_update_jump_hold.argtypes=[C.POINTER(h.State)]
for name in ('left_ledge','right_ledge','enter_teeter'):
    getattr(h.lib,'claw_player_'+name).argtypes=[C.POINTER(h.State),h.Callback,C.c_void_p]
h.lib.claw_player_update_powerup_timer.argtypes=[C.POINTER(h.State),C.POINTER(Powerup),C.c_uint32,h.Callback,C.c_void_p]
realHelpers={0x41f4c0,0x41e710,0x41e790,0x417480,0x41fc30};mutateHelpers=False
for entry in sorted(realHelpers):
    for case in range(2000):
        s=state(24);s.inputHeld=h.rng.choice([0,1]);s.privateWords[70]=h.rng.choice([0,1,25,250,0xffffffff]);s.privateWords[24]=h.rng.getrandbits(32);s.privateWords[25]=h.rng.getrandbits(32)
        h.prepare(s);before=h.State.from_buffer_copy(s);h.nativeEvents.clear();o.events=[]
        responses[0x4a3050]=h.rng.getrandbits(32);responses[0x48c8a0]=h.rng.getrandbits(32);teeterProbe=h.rng.choice([False,True]);edgeOffset=h.rng.choice([(-16)&0xffffffff,16])
        if entry==0x41fc30:
            p=Powerup(h.rng.choice([0,1,33,1000]),h.rng.getrandbits(32),h.rng.choice([0,0x100f000]));s.powerup=h.rng.choice([0,0x26bc,0x26b7,0x26bd]);o.write_words(0x534eac,[s.powerup]);o.write_words(0x534ea8,[p.remaining]);o.write_words(0x534eb8,[p.expired]);o.write_words(h.A+0x174,[0x100e000 if s.actor[0x174//4] else 0]);o.write_words(0x100e030,[p.overlaySequenceToken])
            expectedReturn=o.call(entry,0,struct.pack('<4I',h.A,h.L,h.P,s.stageDelta));h.lib.claw_player_update_powerup_timer(C.byref(s),C.byref(p),s.stageDelta,dependency,None)
            assert p.remaining==o.read_words(0x534ea8,1)[0]and p.expired==o.read_words(0x534eb8,1)[0],(entry,case,'powerup context')
        else:
            expectedReturn=o.call(entry,0,struct.pack('<I',h.A)if entry in (0x41e710,0x41e790)else struct.pack('<3I',h.A,h.L,h.P))
            if entry==0x41f4c0:h.lib.claw_player_update_jump_hold(C.byref(s))
            else:
                name={0x41e710:'left_ledge',0x41e790:'right_ledge',0x417480:'enter_teeter'}[entry]
                actualReturn=getattr(h.lib,'claw_player_'+name)(C.byref(s),dependency,None)&0xffffffff;assert actualReturn==expectedReturn,(entry,case,'return',actualReturn,expectedReturn)
        expected=o.read_words(h.A,128);expected[3]=before.actor[3]
        if entry==0x41fc30:expected[0x174//4]=before.actor[0x174//4]
        assert list(s.actor)==expected,(hex(entry),case,'actor')
        assert list(s.privateWords)==o.read_words(h.P,78),(hex(entry),case,'private')
        assert bytes(s.physics)==o.u.mem_read(0x534db8,C.sizeof(h.Physics)),(hex(entry),case,'physics',[(j,x,y)for j,(x,y)in enumerate(zip(bytes(s.physics),o.u.mem_read(0x534db8,C.sizeof(h.Physics))))if x!=y][:8])
        assert s.logicState==o.read_words(h.L+0x1c,1)[0]and s.inputLatched==o.read_words(h.I+0xc,1)[0],(hex(entry),case,'logic/input')
        assert s.weaponLogicCallback==o.read_words(h.WL+0x14,1)[0],(hex(entry),case,'weapon callback')
        assert s.weaponDeleteFlags==o.read_words(0x100a000 if s.weaponDeleteCount>32 else h.WL+0x300,1)[0],(hex(entry),case,'weapon flags')
        assert h.nativeEvents==o.events,(hex(entry),case,'events',h.nativeEvents,o.events)
    print(f'PASS 2000 separately recovered helper {hex(entry)}; full state, return and dependency events',flush=True)
realHelpers=set();mutateHelpers=True;responses={};teeterProbe=False;h.collisionMode=o.mode=2;h.platform=(0,0)
directed=[(8,0x3000000,0,[0x4183e0,0x41d850]),(9,0x3000000,0,[0x418790,0x41d850]),
    (8,0x2000000,1,[0x4183e0,0x41d850,0x417590]),(8,0x8000000,1,[0x4171d0,0x419030,0x41d850,0x417590]),
    (5003,0,1,[0x417590,0x41b630]),(5003,0,0,[0x41a490]),(24,0x2000000,0,[0x4cd1c0,0x41e710,0x41d850,0x419030]),
    (24,0,0x3000000,[0x41c4e0,0x4c79e0,0x4cbb60,0x4c82a0]),(24,0x3000000,1,[0x41c4e0,0x4c79e0,0x41f4c0,0x4cbb60,0x4c82a0])]
for case,(logic,held,pressed,expected)in enumerate(directed):
    s=state(logic);s.actor[8//4]&=~0x400010;s.inputHeld=held;s.privateWords[1]=0;s.privateWords[8]=1;s.privateWords[33]=0;s.privateWords[69]=1500;s.powerup=0;s.stageDelta=s.animationDelta=0
    i=Input(pressed,0,(-1000000)&0xffffffff,1000000,(-1000000)&0xffffffff,1000000,1,0)
    check(s,i,('directed inputs',case));actual=[e[0]for e in h.nativeEvents];assert actual[:len(expected)]==expected,(case,actual,expected)
print('PASS directed simultaneous directions, stand pressed-vs-held, walk-before-jump, Down interruption and lookup jump ordering',flush=True)
states=(4,8,9,24,25,26,27,5002,5003,5006)
for history in range(32):
    s=state(states[history%len(states)]);s.privateWords[1]=0;s.privateWords[8]=1;s.powerup=0
    i=Input(0,1500,(-10000)&0xffffffff,10000,(-10000)&0xffffffff,10000,1,0)
    for tick in range(120):
        if tick%40==0:s.logicState=states[(history+tick//40)%len(states)]
        i.pressed=[0,1,8,0x1000000,0x2000000,0x3000001][tick%6]
        s.inputHeld=[0,1,0x1000000,0x2000000,0x3000000,0x8000000,0x4000000][tick%7]
        s.stageDelta=[0,1,7,16,33,80,200][(history+tick)%7];s.animationDelta=[1,7,17,80][tick%4]
        h.collisionMode=o.mode=[1,2,3,4,6,7][tick%6]
        check(s,i,('chained dispatch',history,tick))
print('PASS 3840 chained original callback branches with explicit helper-state adapters and independently varying pressed/held/timing',flush=True)
print(f'{len(o.executed)} original instruction addresses. High-level helper/resource/combat boundaries remain explicit where not separately recovered; inline physics executes.')
