"""Original command/respawn/transition comparisons with explicit leaf adapters."""
import ctypes as C
from pathlib import Path
import random,subprocess
from unicorn import UcError
from death_command_original import *
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/death-command-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-O2','-dynamiclib',str(ROOT/'Sources/PlayerDeathCommands.cpp'),str(ROOT/'Sources/GameTiming.cpp'),'-o',str(WORK/'libPlayerDeathCommands.dylib')],check=True)
lib=C.CDLL(str(WORK/'libPlayerDeathCommands.dylib'))
class ClockState(C.Structure):_fields_=[(n,C.c_uint32)for n in('now','delta','start','countdown','reload')]
class FrameState(C.Structure):_fields_=[('now',C.c_uint32),('delta',C.c_uint32)]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in('player','volume','keyboard','mouse')]+[('clock',ClockState),('stage',FrameState),('animation',FrameState)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
lib.claw_player_death_command.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32)]
lib.claw_player_respawn.argtypes=[C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32)]
lib.claw_player_game_over_transition.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32)]
for name in('cleanup','cleanup_actor','clear_history'):getattr(lib,'claw_player_death_'+name).argtypes=[C.c_uint32,Host,C.POINTER(C.c_uint32)]
o=OriginalDeath(ROOT/'Original/claw10/CLAW.EXE');rng=random.Random(0x8006);memory={};events=[];snapshots=[];currentGlobals=None;readonly={};allocIndex=0;errors=[]
def put(t,v):memory[t]=(C.c_uint32*len(v))(*v);o.write_words(t,v);o.memory[t]=len(v)
def span(t,n):
    for b,a in memory.items():
        if b<=t and t+n*4<=b+len(a)*4:return C.addressof(a)+t-b
    if 0x400000<=t and t+n*4<0x547000:
        key=(t,n)
        if key not in readonly:readonly[key]=(C.c_uint32*n)(*o.read_words(t,n))
        return C.addressof(readonly[key])
    return None
def read(t,n):return list((C.c_uint32*n).from_address(span(t,n)))
def write(t,v):(C.c_uint32*len(v)).from_address(span(t,len(v)))[:]=v
def globalsWords(g):return list((C.c_uint32*13).from_address(C.addressof(g)))
def observe(event):events.append(event);snapshots.append(({t:list(a)for t,a in memory.items()},globalsWords(currentGlobals)))
@Lookup
def lookup(_,t,n):return span(t,n)
@Allocate
def allocate(_,n):
    global allocIndex
    observe(('allocate',n));token,expected,seed=o.allocations[allocIndex];allocIndex+=1
    if expected!=n:errors.append(('allocation size',expected,n))
    if token:memory[token]=(C.c_uint32*len(seed))(*seed)
    return token
@Free
def free(_,t):observe(('free',t))
@Invoke
def invoke(_,c):
    args=list(c.arguments[:c.argumentCount]);observe(('call',c.function,c.receiver,tuple(args)))
    oldRead,oldWrite=o.read_words,o.write_words;o.read_words,o.write_words=read,write
    try:return o.service(c.function,c.receiver,args)
    except Exception as e:errors.append(repr(e));return 0
    finally:o.read_words,o.write_words=oldRead,oldWrite
@Clock
def clock(_):observe(('clock',));o.clockReads+=1;return (o.clock+o.clockReads*17)&MASK
host=Host(None,lookup,allocate,free,invoke,clock)
def initialize(iteration):
    global memory,currentGlobals
    memory={};o.memory={};o.events=[];o.snapshots=[];o.allocations=[];o.heap=HEAP;o.rng=random.Random(iteration)
    o.queryIndex=o.frameCalls=o.clockReads=0;o.types=rng.choice([[3],[4],[6],[1],[0,4],[1,1,6],[8,8,8]])
    o.initSuccess=rng.choice([True,True,False]);o.soundFound=rng.choice([True,False]);o.failAllocation=None;o.callbackMutation=True;o.clock=rng.getrandbits(32)
    for t,n in((APP,85),(OWNER,485),(PARENT,32),(MAP,32),(PLANE,48),(PLAYER,128),(LOGIC,93),(PRIVATE,78),(CONTAINER,11),(RENDER,16),(WINDOW,160),(KEYBOARD,32),(MOUSE,144),(SOUND,16),(MUSIC,16),(TREE,16),(OLDVT,16),(FRAMEVT,16),(RENDERVT,16)):
        put(t,[rng.getrandbits(32)for _ in range(n)])
    write(APP,[0x50bee4]);write(APP+4,[WINDOW,WINDOW]);write(APP+0x14,[rng.choice([0,1])]);write(APP+0x2c,[OWNER]);write(APP+0x30,[rng.choice([0,PARENT])]);write(APP+0x50,[rng.choice([0,MUSIC])]);write(APP+0x7c,[rng.choice([480,640,0xffffffff])]);write(APP+0x80,[rng.choice([480,1000,0x7fffffff])]);write(APP+0x9c,[rng.choice([0,1,0xffffffff])]);write(APP+0xa0,[rng.choice([0,0,0,1])])
    write(OWNER,[OLDVT]);write(OWNER+4,[APP]);write(OWNER+0xc,[PARENT]);write(OWNER+0x2c,[rng.choice([0,1])]);write(OWNER+0x44,[rng.choice([0,0xffffffff])]);write(PARENT+4,[WINDOW,CONTAINER,RENDER]);write(PARENT+0x24,[MAP,SOUND]);write(MAP+0x5c,[rng.choice([0,PLANE])]);write(SOUND+0x30,[rng.choice([0,1])]);write(PLANE+8,[rng.randrange(16)]);write(PLANE+0x30,[rng.choice([0,512,1024,0xffffffff]),rng.choice([0,256,1024,0x80000000])]);write(PLANE+0xb0,[rng.choice([0,TREE])])
    write(PLAYER+0x6c,[LOGIC]);write(LOGIC+0x10,[PRIMARY,PRIVATE]);write(LOGIC+0x1c,[rng.choice([5004,5005,28])]);write(CONTAINER,[FRAMEVT]);write(RENDER,[RENDERVT]);write(OLDVT,[DESTRUCT]);write(OLDVT+0x10,[QUERY]);write(OLDVT+0x28,[LEAVE]);write(FRAMEVT+0x24,[FRAME]);write(RENDERVT+0x34,[RENDERFN])
    actors=[PLAYER]
    for i in range(rng.randrange(7)):
        t=0x1030000+i*0x400;put(t,[rng.getrandbits(32)for _ in range(128)]);actors.append(t)
    for i,t in enumerate(actors):
        node=0x1020000+i*0x100;put(node,[0x1020000+(i+1)*0x100 if i+1<len(actors)else 0,0,t])
    write(CONTAINER+0x14,[0x1020000]);count=rng.randrange(8)
    history=0x1040000
    put(history,[rng.getrandbits(32)for _ in range(20)])
    for i in range(count):write(history+i*4,[rng.choice([0,OWNER])])
    write(APP+0xdc,[0x5108fc,history if count else 0,count,rng.randrange(count,20)if count else 0,rng.choice([0,2,10])])
    for t,a in memory.items():o.write_words(t,list(a))
    g=Globals();g.player=rng.choice([PLAYER,PLAYER,0]);g.volume=rng.getrandbits(32);g.keyboard=KEYBOARD;g.mouse=MOUSE
    v=globalsWords(g)
    for i in range(4,13):v[i]=rng.getrandbits(32)
    C.memmove(C.addressof(g),packed(*v),52);currentGlobals=g
    o.write_words(0x537e88,[g.player]);o.write_words(0x532c10,[g.volume]);o.write_words(0x537204,[KEYBOARD]);o.write_words(0x537200,[MOUSE]);o.write_words(0x541328,v[4:9]);o.write_words(0x537208,v[9:11]);o.write_words(0x5430c8,[v[11]]);o.write_words(0x5430c4,[v[12]])
    return g
def compare(kind,iteration,command=None,transition=None,reset=True,realType=False):
    global allocIndex,events,snapshots
    g=initialize(iteration)if reset else currentGlobals
    if realType:write(OWNER,[0x50c264]);o.write_words(OWNER,[0x50c264])
    events=[];snapshots=[];errors.clear();allocIndex=len(o.allocations);o.events=[];o.snapshots=[];fault=C.c_uint32()
    beforeCounters=(o.queryIndex,o.frameCalls,o.clockReads)
    if reset and iteration%31==0:o.failAllocation='state'
    if kind=='command':result=o.call(0x426e30,APP,packed(0,command,0))
    elif kind=='respawn':result=o.call(0x46be40,OWNER)
    elif kind=='transition':result=o.call(0x428c40,APP,packed(transition[0],transition[1],transition[2],0))
    elif kind=='cleanup':result=o.call(0x46e2d0,OWNER)
    elif kind=='actor':result=o.call(0x46e340,0,packed(PLAYER))
    else:result=o.call(0x42c060,APP)
    expected=({t:o.read_words(t,n)for t,n in o.memory.items()},o.globals())
    o.queryIndex,o.frameCalls,o.clockReads=beforeCounters
    if kind=='command':actual=lib.claw_player_death_command(APP,command,C.byref(g),host,C.byref(fault))
    elif kind=='respawn':actual=lib.claw_player_respawn(OWNER,C.byref(g),host,C.byref(fault))
    elif kind=='transition':actual=lib.claw_player_game_over_transition(APP,*transition,C.byref(g),host,C.byref(fault))
    else:
        fn={'cleanup':lib.claw_player_death_cleanup,'actor':lib.claw_player_death_cleanup_actor,'clear':lib.claw_player_death_clear_history}[kind];fn(PLAYER if kind=='actor'else OWNER if kind=='cleanup'else APP,host,C.byref(fault));actual=result
    label=(kind,iteration,command,transition)
    assert not errors,(label,errors)
    assert fault.value==0,(label,'fault',fault.value)
    assert result==actual,(label,'return',result,actual)
    assert events==o.events,(label,'events',events,o.events)
    got=({t:list(a)for t,a in memory.items()},globalsWords(g))
    if got!=expected:
        for t in set(got[0])|set(expected[0]):
            if got[0].get(t)!=expected[0].get(t):print(label,hex(t),[(i,hex(x),hex(y))for i,(x,y)in enumerate(zip(got[0][t],expected[0][t]))if x!=y][:10])
        raise AssertionError((label,'buffer/global',got[1],expected[1]))
    assert snapshots==o.snapshots,(label,'callback snapshot',next((i for i,(a,b)in enumerate(zip(snapshots,o.snapshots))if a!=b),None))
for i in range(1500):compare('command',i,0x803a)
for i in range(1500):compare('command',2000+i,0x8006)
for i in range(1500):compare('respawn',4000+i)
for i in range(1500):compare('transition',6000+i,transition=(rng.choice([5,12]),rng.getrandbits(32),rng.randrange(2)))
for i in range(300):
    compare('cleanup',8000+i);compare('actor',9000+i);compare('clear',10000+i)
# Consecutive retained transitions preserve earlier states and exact array
# capacity/tails, then non-retained transitions destroy the entire history.
for history in range(96):
    compare('transition',12001+history,transition=(12,1,1))
    o.failAllocation=None;o.initSuccess=True
    for step in range(5):compare('transition',13000+step,transition=(rng.choice([5,12]),step,1),reset=False)
    compare('transition',14000,transition=(5,1,0),reset=False)
# Genuine Win32 callback4b8500 -> window virtual48/4b8810 -> app virtual14/
#426e30. Both notification-word and low command are routed as original.
# The three pre-handlers below return0 and retain all buffers unchanged.
for command in(0x803a,0x8006):
    for high in(0,1,0xffff):
        for iteration in range(32):
            g=initialize(15000+iteration);o.failAllocation=None
            win,wrapper,wvt,svt=0x1011000,0x1012000,0x10e0300,0x10e0400
            put(win,[0]*32);put(wrapper,[0]*32);put(wvt,[0]*32);put(svt,[0]*32)
            write(win,[wvt]);write(win+8,[wrapper]);write(wrapper,[svt]);write(wrapper+8,[APP])
            write(wvt+4,[WMPRE]);write(wvt+8,[COMMANDHOOK]);write(wvt+0x48,[0x4b8810]);write(svt+0x28,[COMMANDPRE])
            for t in(win,wrapper,wvt,svt):o.write_words(t,list(memory[t]))
            o.write_words(0x54133c,[win]);events=[];snapshots=[];allocIndex=0;errors.clear();f=C.c_uint32()
            result=o.call(0x4b8500,0,packed(0x1234,0x111,command|(high<<16),0))
            assert result==0
            assert o.events[:3]==[('call',WMPRE,win,(0x111,command|(high<<16),0)),('call',COMMANDPRE,wrapper,(high,command,0)),('call',COMMANDHOOK,win,(high,command,0))]
            expected=({t:o.read_words(t,n)for t,n in o.memory.items()},o.globals())
            o.queryIndex=o.frameCalls=o.clockReads=0
            assert lib.claw_player_death_command(APP,command,C.byref(g),host,C.byref(f))==1 and f.value==0
            assert not errors and events==o.events[3:]
            assert ({t:list(a)for t,a in memory.items()},globalsWords(g))==expected
            assert snapshots==o.snapshots[3:]
for i in range(64):compare('command',16000+i,0x803a,realType=True)
for command in(0x803a,0x8006):
    initialize(17001);write(APP+0x2c,[0]);o.write_words(APP+0x2c,[0]);write(APP+0x9c,[1]);o.write_words(APP+0x9c,[1]);o.failAllocation=None
    compare('command',17001,command,reset=False)
# Actual original faults are not converted to normal command returns. Compare
# their complete prefixes while preserving the original NULL-page boundary.
for scenario in('null-current','history-oom','bad-list-next'):
    g=initialize(18001);events=[];snapshots=[];errors.clear();allocIndex=0;f=C.c_uint32()
    if scenario=='null-current':
        for t,v in((APP+0x2c,0),(APP+0x9c,0)):write(t,[v]);o.write_words(t,[v])
        entry,receiver,args=0x426e30,APP,packed(0,0x8006,0);expectedFault=1
    elif scenario=='history-oom':
        for t,v in((APP+0x9c,1),(APP+0xa0,0),(APP+0xe0,0),(APP+0xe4,0),(APP+0xe8,0)):write(t,[v]);o.write_words(t,[v])
        o.failAllocation=0;entry,receiver,args=0x426e30,APP,packed(0,0x8006,0);expectedFault=2
    else:
        write(0x1020000,[0xfedcba98]);o.write_words(0x1020000,[0xfedcba98]);entry,receiver,args=0x46e2d0,OWNER,b'';expectedFault=1
    savedCPU=o.u.context_save()
    try:o.call(entry,receiver,args);raise AssertionError('Original expected fault did not occur')
    except UcError:pass
    expected=({t:o.read_words(t,n)for t,n in o.memory.items()},o.globals());o.u.context_restore(savedCPU);o.queryIndex=o.frameCalls=o.clockReads=0
    if scenario=='bad-list-next':lib.claw_player_death_cleanup(OWNER,host,C.byref(f))
    else:lib.claw_player_death_command(APP,0x8006,C.byref(g),host,C.byref(f))
    assert not errors and f.value==expectedFault,(scenario,errors,f.value)
    assert events==o.events and snapshots==o.snapshots,scenario
    assert ({t:list(a)for t,a in memory.items()},globalsWords(g))==expected,scenario
print('PASS 6000 controller cases, 900 cleanup/history cases, 672 retained transition-chain passes, 192 complete WM_COMMAND routing cases, 64 actual gameplay-vtable respawns, null-current and 3 actual fault-prefix cases; complete buffers/globals/ordered calls/callback snapshots;',len([a for a in o.executed if 0x400000<=a<0x547000]),'original-image instruction addresses')
