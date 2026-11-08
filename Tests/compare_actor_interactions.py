#!/usr/bin/env python3
"""Original4c9390 complete pair scanner and4c9ae0 damage selection."""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');a=p.parse_args()
library=ROOT/'work/actor-interactions-agent/libActorInteractions.dylib'
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/ActorInteractions.cpp'),'-o',str(library)],check=True)
class Actor(C.Structure):_fields_=[('token',C.c_uint32),('actor',C.c_uint32*128)]+[(x,C.c_uint32*93)for x in('primary','secondary','contact')]
class Call(C.Structure):_fields_=[(x,C.c_uint32)for x in('function','actorToken','peerToken','logicToken','kind')]
Dependency=C.CFUNCTYPE(None,C.POINTER(Actor),C.c_size_t,C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(library));scan=lib.claw_actor_interactions
scan.argtypes=[C.POINTER(Actor),C.c_size_t,Dependency,C.c_void_p];scan.restype=C.c_uint32
hurt=lib.claw_actor_interaction_hurt;hurt.argtypes=[C.POINTER(Actor),C.c_size_t,C.c_uint32,C.c_uint32,Dependency,C.c_void_p];hurt.restype=C.c_uint32
overlap=lib.claw_actor_interaction_overlap;overlap.argtypes=[C.POINTER(Actor),C.POINTER(Actor)];overlap.restype=C.c_uint32
m=OriginalV10(a.exe);u=m.u;m.executed.clear()
scene,nodes=0x1000000,0x1001000
def actor_address(i):return 0x1010000+i*0x2000
def primary_address(i):return actor_address(i)+0x400
def secondary_address(i):return actor_address(i)+0x800
def contact_address(i):return actor_address(i)+0xc00
def packed(*x):return struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x))
callbacks={0x41ce80:0,0x498f40:1};events=[];policy=0;current_count=0;callback_total=0;calls=0
def words(i,member):return m.read_words(actor_address(i)+{'actor':0,'primary':0x400,'secondary':0x800,'contact':0xc00}[member],128 if member=='actor'else 93)
def mutate(actors,count,event):
    receiver=next(i for i in range(count)if actors[i].token==event[1]);peer=next(i for i in range(count)if actors[i].token==event[2])
    r,p=actors[receiver],actors[peer]
    if policy==1:
        # Contact mutates cached gates/geometry. Hit then reads current damage
        # fields; reverse pass reads current masks/flags and geometry anew.
        if event[4]==1:
            p.actor[0xd4//4]=0;r.actor[0xd8//4]=0;p.actor[2]^=8
            p.actor[0x10c//4]=3;r.actor[0x104//4]=5
            r.actor[0x4c//4]=(r.actor[0x4c//4]+3)&0xffffffff
        else:
            r.actor[2]^=0x80;r.actor[0x10c//4]^=0x55
            r.secondary[0x2c//4]^=0x33;p.contact[0x30//4]^=0x44
    elif policy==2:
        # Flag1 set during a callback must NOT skip remaining inner pairs or
        # reverse direction. Future outer actors do observe the new flag.
        r.actor[2]|=1;p.actor[2]^=0x40000
        r.actor[0xd0//4]^=3;p.actor[0xd4//4]^=3
    elif policy==3:
        r.actor[0x128//4]=0x80000000;p.actor[0x138//4]=0x80000000
        r.actor[0x70//4]=0;p.actor[0x78//4]=0
@Dependency
def dependency(actors,count,event,user):
    e=event.contents;record=(e.function,e.actorToken,e.peerToken,e.logicToken,e.kind);events.append(record);mutate(actors,count,record)
def host(uc,address,size,user):
    if address not in callbacks:return
    sp=u.reg_read(UC_X86_REG_ESP);token=m.read_words(sp+4,1)[0];i=(token-0x1010000)//0x2000
    assert token==actor_address(i)and 0<=i<current_count
    kind=callbacks[address];aw=words(i,'actor');peer=aw[(0x7c if kind else 0x74)//4];logic=aw[(0x78 if kind else 0x70)//4]
    record=(address,token,peer,logic,kind);events.append(record)
    temporary=(Actor*current_count)()
    for j in range(current_count):
        temporary[j].token=actor_address(j)
        for member in('actor','primary','secondary','contact'):getattr(temporary[j],member)[:]=words(j,member)
    mutate(temporary,current_count,record)
    for j in range(current_count):
        for member,offset in [('actor',0),('primary',0x400),('secondary',0x800),('contact',0xc00)]:m.write_words(actor_address(j)+offset,getattr(temporary[j],member))
    ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,0);u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EIP,ret)
u.hook_add(UC_HOOK_CODE,host)
rng=random.Random(1997)
def make(count,random_bits=False):
    state=(Actor*count)()
    for i in range(count):
        state[i].token=actor_address(i)
        for member,length in [('actor',128),('primary',93),('secondary',93),('contact',93)]:getattr(state[i],member)[:]=[rng.getrandbits(32)for _ in range(length)]
        aw=state[i].actor;aw[2]=rng.choice([0,4,8,0x80,1,0x40000,0x40008,0x40080])
        aw[0x6c//4]=primary_address(i);aw[0x70//4]=secondary_address(i)if rng.randrange(4)else 0;aw[0x78//4]=contact_address(i)if rng.randrange(4)else 0
        state[i].secondary[4]=0x41ce80;state[i].contact[4]=0x498f40
        for offset in(0xd0,0xd4,0xd8):aw[offset//4]=rng.randrange(16)
        aw[0x4c//4]=rng.getrandbits(32)if random_bits else rng.randrange(-15,16)&0xffffffff
        aw[0x50//4]=rng.getrandbits(32)if random_bits else rng.randrange(-15,16)&0xffffffff
        aw[0x104//4]=rng.getrandbits(32)if random_bits else rng.randrange(-3,10)&0xffffffff
        aw[0x10c//4]=rng.getrandbits(32)if random_bits else rng.randrange(-3,20)&0xffffffff
        for rect in(0x128,0x138):
            values=[rng.getrandbits(32)for _ in range(4)]if random_bits else[rng.randrange(-10,4)&0xffffffff,rng.randrange(-10,4)&0xffffffff,rng.randrange(3,11),rng.randrange(3,11)]
            aw[rect//4:rect//4+4]=values
            if rng.randrange(9)==0:aw[rect//4]=0x80000000
    return state
def check(state,label,direct=None):
    global calls,current_count,callback_total
    count=len(state);current_count=count;before=bytes(state);events.clear()
    if direct is None:assert scan(state,count,dependency,None)==1
    else:assert hurt(state,count,*direct,dependency,None)==1
    expected=bytes(state);expected_events=list(events);state_from_before=(Actor*count).from_buffer_copy(before)
    for i in range(count):
        for member,offset in [('actor',0),('primary',0x400),('secondary',0x800),('contact',0xc00)]:m.write_words(actor_address(i)+offset,getattr(state_from_before[i],member))
        m.write_words(nodes+i*16,[nodes+(i+1)*16 if i<count-1 else 0,0,actor_address(i),0])
    m.write_words(scene+0x14,[nodes if count else 0]);node_snapshot=bytes(u.mem_read(nodes,count*16));events.clear()
    if direct is None:m.call(0x4c9390,scene)
    else:m.call(0x4c9ae0,actor_address(direct[0]),packed(actor_address(direct[1])))
    assert events==expected_events,(label,'events',events,expected_events)
    original=(Actor*count)()
    for i in range(count):
        original[i].token=actor_address(i)
        for member in('actor','primary','secondary','contact'):getattr(original[i],member)[:]=words(i,member)
    assert bytes(original)==expected,(label,'full buffers',[(i,bytes(original)[i],expected[i])for i in range(len(expected))if bytes(original)[i]!=expected[i]][:12])
    assert bytes(u.mem_read(nodes,count*16))==node_snapshot,(label,'list node mutation')
    callback_total+=len(events);calls+=1
    return state

# Both directions, inclusive touching boundaries, disabled rectangles and generic
# health exhaustion. Full masks make callback ordering explicit.
for shift in(-21,-20,-19,0,19,20,21):
    for flags_a in(0,1,4,8,0x80,0x40000):
        for flags_b in(0,1,4,8,0x80,0x40000):
            state=make(2)
            for i in range(2):
                aw=state[i].actor;aw[2]=flags_a if i==0 else flags_b;aw[0x4c//4]=0 if i==0 else shift&0xffffffff;aw[0x50//4]=0
                for rect in(0x128,0x138):aw[rect//4:rect//4+4]=[0xfffffff6,0xfffffff6,10,10]
                for offset in(0xd0,0xd4,0xd8):aw[offset//4]=3
                aw[0x70//4]=secondary_address(i);aw[0x78//4]=contact_address(i);aw[0x10c//4]=1;aw[0x104//4]=2
            policy=0;check(state,('directed',shift,flags_a,flags_b))
for policy in(1,2,3):
    state=make(4)
    for i in range(4):
        aw=state[i].actor;aw[2]=0;aw[0x4c//4]=aw[0x50//4]=0
        for rect in(0x128,0x138):aw[rect//4:rect//4+4]=[0xfffffff6,0xfffffff6,10,10]
        for offset in(0xd0,0xd4,0xd8):aw[offset//4]=3
        aw[0x70//4]=secondary_address(i);aw[0x78//4]=contact_address(i)
    check(state,('mutation ordering',policy))
print('PASS directed masks/flags/inclusive edges, genericdamage exhaustion and callback mutation/order histories',flush=True)
for i in range(5000):
    policy=i%4;check(make(rng.randrange(0,7),i%5==0),('scene',i))
print('PASS5000 generated fixed-list scene scans (0...6actors), wrapped/sentinel coordinates and callback mutations',flush=True)
for i in range(2000):
    policy=i%4;state=make(2,i%3==0);check(state,('directhurt',i),direct=(i%2,(i+1)%2))
    native=overlap(C.byref(state[0]),C.byref(state[1]));m.write_words(actor_address(0),state[0].actor);m.write_words(actor_address(1),state[1].actor)
    original=m.call(0x4c95b0,scene,packed(actor_address(0),actor_address(1)));assert native==bool(original),('overlap',i)
print('PASS2000 directhurt calls and independent original4c95b0 overlap comparisons',flush=True)
state=make(2);before=bytes(state);events.clear();assert hurt(state,2,2,0,dependency,None)==0 and bytes(state)==before and events==[]
assert {0x4c9390,0x4c9ae0,0x4c95b0,0x4ca230}<=m.executed
addresses=m.executed-set(callbacks)-{m.stop}
print(f'PASS{calls} complete original scan/hurt calls;{callback_total} ordered adaptedgameplay callbacks;{len(addresses)} original interactioninstruction addresses. Fullactor+three logicbuffers and listnodes agree; onlycallback bodies adapted.',flush=True)
