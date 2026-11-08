"""Complete generic creator, scene list and frame scheduling comparisons."""
import ctypes as C
from pathlib import Path
import random,struct,subprocess
from unicorn import UcError,UC_ERR_READ_UNMAPPED,UC_ERR_WRITE_UNMAPPED
from scene_actor_original import *
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/scene-actor-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-O2','-dynamiclib',str(ROOT/'Sources/SceneActorRuntime.cpp'),str(ROOT/'Sources/WorldObjectRuntime.cpp'),str(ROOT/'Sources/GameTiming.cpp'),str(ROOT/'Sources/ActorInteractions.cpp'),'-o',str(WORK/'libSceneActorRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libSceneActorRuntime.dylib'))
class Frame(C.Structure):_fields_=[('nowMilliseconds',C.c_uint32),('deltaMilliseconds',C.c_uint32)]
class Globals(C.Structure):_fields_=[('initializationFlags',C.c_uint32),('deletionArray',C.c_uint32*5),('reorderArray',C.c_uint32*5),('animation',Frame)]
class Stage(C.Structure):_fields_=[('stage',Frame),('accumulatedMilliseconds',C.c_uint32),('playerToken',C.c_uint32)]
class CreateArgs(C.Structure):_fields_=[(n,C.c_uint32)for n in('id','x','y','z','entryToken','flags')]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Interaction(C.Structure):_fields_=[('token',C.c_uint32)]+[(n,C.c_uint32*count)for n,count in(('actor',128),('primary',93),('secondary',93),('contact',93))]
class InteractionCall(C.Structure):_fields_=[(n,C.c_uint32)for n in('function','actorToken','peerToken','logicToken','kind')]
InteractionDependency=C.CFUNCTYPE(None,C.POINTER(Interaction),C.c_size_t,C.POINTER(InteractionCall),C.c_void_p)
lib.claw_actor_interactions.argtypes=[C.POINTER(Interaction),C.c_size_t,InteractionDependency,C.c_void_p]
lib.claw_scene_actor_create.argtypes=[C.c_uint32,CreateArgs,Host,C.POINTER(C.c_uint32)]
lib.claw_scene_actor_create_named.argtypes=[C.c_uint32,CreateArgs,C.c_uint32,Host,C.POINTER(C.c_uint32)]
lib.claw_scene_actor_insert.argtypes=[C.c_uint32,C.c_uint32,Host,C.POINTER(C.c_uint32)];lib.claw_scene_actor_insert.restype=None
lib.claw_scene_actor_update.argtypes=[C.c_uint32,C.POINTER(Globals),C.c_uint32,Host,C.POINTER(C.c_uint32)];lib.claw_scene_actor_update.restype=None
lib.claw_scene_stage_run.argtypes=[C.c_uint32,C.POINTER(Stage),C.POINTER(Globals),C.c_uint32,Host,C.POINTER(C.c_uint32)]
lib.claw_scene_stage_update.argtypes=[C.c_uint32,C.POINTER(Stage),C.POINTER(Globals),Host,C.POINTER(C.c_uint32)]
o=OriginalScene(ROOT/'Original/claw10/CLAW.EXE');rng=random.Random(0x4c8fc0);memory={};events=[];allocIndex=0;clockReads=0;currentGlobals=None;currentStage=None;spawned=False
snapshots=[]
class ObservedEvents(list):
    def append(self,event):
        super().append(event);g=currentGlobals;s=currentStage
        snapshots.append(({t:list(a)for t,a in memory.items()},[g.initializationFlags],list(g.deletionArray),list(g.reorderArray),[g.animation.nowMilliseconds],[g.animation.deltaMilliseconds],[s.stage.nowMilliseconds,s.stage.deltaMilliseconds,s.accumulatedMilliseconds]))
events=ObservedEvents()
def put(token,words):memory[token]=(C.c_uint32*len(words))(*words);o.write_words(token,words);o.memory[token]=len(words)
def span(token,count):
    for base,array in memory.items():
        if base<=token and token+4*count<=base+4*len(array):return C.addressof(array)+token-base
    return None
def readWords(token,count):return list((C.c_uint32*count).from_address(span(token,count)))
def writeWords(token,values):array=(C.c_uint32*len(values)).from_address(span(token,len(values)));array[:]=values
@Lookup
def lookup(_,token,count):return span(token,count)
@Allocate
def allocate(_,count):
    global allocIndex
    events.append(('allocate',count));token,expected,seed=o.allocations[allocIndex];allocIndex+=1;assert expected==count
    if token:memory[token]=(C.c_uint32*len(seed))(*seed)
    return token
@Free
def free(_,token):events.append(('free',token))
def mutate(actor):
    a=readWords(actor,128);logic=a[0x6c//4];l=readWords(logic,93);l[0x44//4]=(l[0x44//4]+1)&MASK
    if o.callbackMode==1:a[2]|=0x10000
    elif o.callbackMode==2:a[2]|=0x20000;a[0x64//4]=(a[0x64//4]-13)&MASK
    elif o.callbackMode==3 and l[7]!=29:a[2]|=0x90000
    writeWords(actor,a);writeWords(logic,l)
@InteractionDependency
def interactionDependency(actors,count,event,_):raise AssertionError('Generic masks are zero in this scheduler test domain')
def interactions(container):
    tokens=[];node=readWords(container,11)[5]
    while node:next,previous,actor=readWords(node,3);tokens.append(actor);node=next
    actors=(Interaction*len(tokens))()
    for i,token in enumerate(tokens):
        a=readWords(token,128);actors[i].token=token;actors[i].actor[:]=a;actors[i].primary[:]=readWords(a[0x6c//4],93)
    assert lib.claw_actor_interactions(actors,len(tokens),interactionDependency,None)==1
    for i,token in enumerate(tokens):writeWords(token,list(actors[i].actor));writeWords(readWords(token,128)[0x6c//4],list(actors[i].primary))
@Invoke
def invoke(_,call):
    args=tuple(call.arguments[:call.argumentCount]);events.append(('call',call.function,call.receiver,args))
    if call.function==0x4f6286:return ENTRY if o.found else 0
    if call.function==CALLBACK:
        global spawned
        mutate(args[0])
        if o.callbackMode==4 and not spawned:
            spawned=True;fault=C.c_uint32();lib.claw_scene_actor_create(CONTAINER,CreateArgs(99,320,350,100,ENTRY,0),host,C.byref(fault));assert not fault.value
        return 1
    if call.function==0x4c9be0:writeWords(call.receiver+0x168,[0xfedcba98]);return call.receiver
    if call.function==0x4c9390:interactions(call.receiver)
    return 0
@Clock
def clock(_):
    global clockReads
    events.append(('clock',));clockReads+=1;return o.clock
host=Host(None,lookup,allocate,free,invoke,clock)
def words(n):return [rng.getrandbits(32)for _ in range(n)]
def prepare(count=0):
    global allocIndex,clockReads,currentGlobals,currentStage,spawned
    memory.clear();o.memory={};o.events=[];o.allocations=[];o.heap=HEAP;events.clear();allocIndex=0;o.clockReads=clockReads=0
    c=words(11);c[0]=0x513c20;c[3]=PARENT;c[4]=0x5107bc;c[5:10]=[0,0,0,0,0];c[10]=10;put(CONTAINER,c)
    parent=words(32);parent[2]=CONTAINER;parent[5]=REGISTRY;parent[9]=MAP;put(PARENT,parent)
    entry=words(5);entry[2]=rng.randrange(4);entry[4]=CALLBACK;put(ENTRY,entry)
    owner=words(474);owner[1]=0x1050000;owner[3]=PARENT;owner[0x764//4]=0;put(OWNER,owner)
    map=words(24);map[0x5c//4]=rng.choice([0,PLANE]);put(MAP,map)
    g=Globals(rng.choice([0,3,0xab000003]),(C.c_uint32*5)(0x5108fc,0,0,0,0),(C.c_uint32*5)(0x5108fc,0,0,0,0),Frame(rng.getrandbits(32),rng.choice([0,1,16,18,99,0xffffffff])))
    s=Stage(Frame(rng.getrandbits(32),rng.choice([0,1,18,19,35,36,37,99,100,0xffffffff])),rng.getrandbits(32),ACTOR_BASE)
    currentGlobals=g;currentStage=s
    o.write_words(0x5430d0,[g.initializationFlags]);o.write_words(0x5430f0,list(g.deletionArray));o.write_words(0x5430d8,list(g.reorderArray));o.write_words(0x5430c8,[g.animation.nowMilliseconds]);o.write_words(0x5430c4,[g.animation.deltaMilliseconds])
    o.write_words(0x537208,[s.stage.nowMilliseconds,s.stage.deltaMilliseconds,s.accumulatedMilliseconds]);o.write_words(0x537e88,[s.playerToken])
    o.clock=rng.getrandbits(32);o.found=True;o.callbackMode=0;spawned=False;o.failAllocation=None;o.write_words(SPAWNFLAG,[0])
    # Use actual MFC list insertion for original fixture preparation; the
    # matching native node pool seed is copied before the compared call.
    for i in range(count):
        actor=ACTOR_BASE+i*0x400;logic=LOGIC_BASE+i*0x400;a=words(128);l=words(93)
        a[0]=0x5137f0;a[2]=rng.choice([0,1,0x10000,0x20000,0x90000,0x30000,0x40000]);a[3]=PARENT;a[0x6c//4]=logic;a[0x70//4]=a[0x78//4]=0
        a[0xd0//4]=a[0xd4//4]=a[0xd8//4]=0;a[0x64//4]=rng.getrandbits(32)
        l[4]=CALLBACK;l[7]=rng.randrange(30);l[8]=rng.choice([0,0,1,16,99,rng.getrandbits(32)]);l[9]=rng.choice([0,0,1,3,rng.getrandbits(32)]);put(actor,a);put(logic,l)
        token=o.call(0x4f51c5,CONTAINER+16,packed(actor));o.write_words(actor+0x68,[token])
    for token,count in o.memory.items():memory[token]=(C.c_uint32*count)(*o.read_words(token,count))
    o.events=[];o.allocations=[];o.heap=HEAP+0x10000
    return g,s
def compare(entry,g,s,args=(),automatic=False,expectedFault=0):
    global allocIndex,clockReads
    o.events=[];o.snapshots=[];o.allocations=[];events.clear();snapshots.clear();allocIndex=0;o.clockReads=clockReads=0
    try:expected=o.call(entry,OWNER if entry in(0x46ace0,0x46ad70)else CONTAINER,packed(*args))
    except UcError as error:
        assert expectedFault==2 and error.errno in(UC_ERR_READ_UNMAPPED,UC_ERR_WRITE_UNMAPPED)
        assert o.u.reg_read(UC_X86_REG_EIP)in(0x4c8d02,0x4c7e8b,0x4f5ac1),(o.failAllocation,hex(o.u.reg_read(UC_X86_REG_EIP)));expected=0
    fault=C.c_uint32(0)
    if entry in(0x4c8be0,0x4c8da0):
        creation=CreateArgs(*args)
        if entry==0x4c8da0:creation.entryToken=0;actual=lib.claw_scene_actor_create_named(CONTAINER,creation,args[4],host,C.byref(fault))
        else:actual=lib.claw_scene_actor_create(CONTAINER,creation,host,C.byref(fault))
        assert actual==expected
    elif entry==0x4c9320:lib.claw_scene_actor_insert(CONTAINER,args[0],host,C.byref(fault))
    elif entry==0x4c8fc0:lib.claw_scene_actor_update(CONTAINER,C.byref(g),args[0],host,C.byref(fault))
    else:
        actual=lib.claw_scene_stage_update(OWNER,C.byref(s),C.byref(g),host,C.byref(fault))if automatic else lib.claw_scene_stage_run(OWNER,C.byref(s),C.byref(g),int(entry==0x46ad70),host,C.byref(fault))
        if entry==0x46ad70:assert actual==expected
    assert fault.value==expectedFault,(hex(entry),'fault',fault.value,expectedFault)
    assert events==o.events,(hex(entry),'events',events,o.events)
    assert snapshots==o.snapshots,(hex(entry),'callback/heap boundary state',next((i for i,(a,b)in enumerate(zip(snapshots,o.snapshots))if a!=b),None))
    assert clockReads==o.clockReads
    assert memory.keys()==o.memory.keys()
    for token,array in memory.items():
        original=o.read_words(token,len(array));assert list(array)==original,(hex(entry),hex(token),[(i,hex(a),hex(b))for i,(a,b)in enumerate(zip(array,original))if a!=b])
    assert g.initializationFlags==o.read_words(0x5430d0,1)[0]
    assert list(g.deletionArray)==o.read_words(0x5430f0,5)and list(g.reorderArray)==o.read_words(0x5430d8,5)
    assert [g.animation.nowMilliseconds,g.animation.deltaMilliseconds]==[o.read_words(0x5430c8,1)[0],o.read_words(0x5430c4,1)[0]]
    assert [s.stage.nowMilliseconds,s.stage.deltaMilliseconds,s.accumulatedMilliseconds]==o.read_words(0x537208,3)
    assert o.read_words(TEB,1)==[0xdeadbeef]or expectedFault
for i in range(1500):
    g,s=prepare(rng.randrange(9));entry=rng.choice([0x4c8be0,0x4c8da0]);o.found=rng.choice([True,True,False])
    if i%11==0:memory[ENTRY][4]=0;o.write_words(ENTRY+16,[0])
    flags=rng.choice([0,0x40002,0x200000,0x240002,0x20000,rng.getrandbits(32)])
    compare(entry,g,s,(rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),ENTRY if entry==0x4c8be0 else 0x522e80,flags))
print('PASS 1,500 creators/named creators: complete actor/logic, constructor flags, initialization rejection, signed-Z insertion and immediate callback ordering',flush=True)
for i in range(1500):
    g,s=prepare(rng.randrange(1,13));o.callbackMode=rng.randrange(4)
    compare(0x4c8fc0,g,s,(rng.choice([0,1,0xffffffff]),))
print('PASS 1,500 complete frame dispatches: timer/skip-counter gates, callback flags, deferred delete/29 callbacks, reorder and pooled list/array buffers',flush=True)
for i in range(500):
    g,s=prepare(rng.randrange(1,9));o.callbackMode=rng.choice([0,2])
    for j in range(8):compare(0x4c8fc0,g,s,(j%2,))
print('PASS 4,000 chained frames: scratch resets/free/growth, repeated callbacks and list reorder state',flush=True)
for i in range(1000):
    g,s=prepare(rng.randrange(1,9));o.callbackMode=rng.randrange(4);s.stage.deltaMilliseconds=rng.choice([0,1,17,18,19,20,35,36,37,99,100,101]);o.write_words(0x53720c,[s.stage.deltaMilliseconds])
    entry=0x46ad70 if 18<s.stage.deltaMilliseconds<100 else 0x46ace0;compare(entry,g,s,automatic=True)
print('PASS 1,000 full normal/substep scheduler calls: actual actor/interaction entries, services, clock reads, 18ms remainder phases and restoration',flush=True)
# Actual CaptainClaw caller arguments:4c8da0 from46b439, flag40002.
g,s=prepare();memory[ENTRY][2]=0;memory[ENTRY][4]=0x415df0;o.write_words(ENTRY+8,[0]);o.write_words(ENTRY+16,[0x415df0])
compare(0x4c8da0,g,s,(1,320,350,100,0x522e80,0x40002))
created=o.allocations[0][0];assert readWords(created,128)[2]==0x40002
assert not any(event[:2]==('call',0x415df0)for event in events)
g,s=prepare();memory[ENTRY][2]=0;o.write_words(ENTRY+8,[0]);compare(0x4c8be0,g,s,(1,320,350,100,ENTRY,0))
assert readWords(o.allocations[0][0],128)[2]==0
for i in range(500):
    g,s=prepare(rng.randrange(13));a=words(128);a[0x64//4]=rng.getrandbits(32);put(0x1058000,a)
    compare(0x4c9320,g,s,(0x1058000,))
for count in(1,2):
    g,s=prepare(count);o.callbackMode=4
    for i in range(count):
        actor=ACTOR_BASE+i*0x400;logic=LOGIC_BASE+i*0x400
        writeWords(actor+8,[0]);o.write_words(actor+8,[0]);writeWords(actor+0x64,[i]);o.write_words(actor+0x64,[i]);writeWords(logic+0x20,[0,0]);o.write_words(logic+0x20,[0,0])
    compare(0x4c8fc0,g,s,(0,))
    newActor=o.allocations[0][0]
    callbacks=[event[3][0]for event in events if event[:2]==('call',CALLBACK)]
    assert (newActor in callbacks)==(count==2) # Current next node is cached.
for first,last,subdivide in((90,110,0),(101,110,0),(90,99,1),(90,110,1),(-100,100,1)):
    g,s=prepare(1);writeWords(ACTOR_BASE+8,[0]);o.write_words(ACTOR_BASE+8,[0]);put(IMAGE,words(27));put(FRAMES,words(101))
    for token,offset,value in((ACTOR_BASE,0x170,IMAGE),(IMAGE,0x14,FRAMES),(IMAGE,0x64,first&MASK),(IMAGE,0x68,last),(OWNER,0x764,1)):
        writeWords(token+offset,[value]);o.write_words(token+offset,[value])
    s.stage.deltaMilliseconds=37;o.write_words(0x53720c,[37]);compare(0x46ad70 if subdivide else 0x46ace0,g,s)
    actor=readWords(ACTOR_BASE,128);assert actor[0x16c//4]==100 and actor[0x174//4]==(readWords(FRAMES+400,1)[0]if first<=100<=last else 0)
print('PASS actual player caller flags/coordinates/binding and generic zero-flags preservation; all heap/callback boundary snapshots',flush=True)
print('PASS 500 direct insertions, callback-spawn membership with cached successors, and image100 override in both scheduler modes',flush=True)
g,s=prepare(1);put(0x1047000,[0,0x4c9be0]);writeWords(ACTOR_BASE,[0x1047000]);o.write_words(ACTOR_BASE,[0x1047000]);writeWords(ACTOR_BASE+8,[0x10000]);o.write_words(ACTOR_BASE+8,[0x10000])
compare(0x4c8fc0,g,s,(0,))
coverage=set(o.executed)
for failedAllocation,callback in((0,CALLBACK),(1,CALLBACK),(2,CALLBACK),(1,0)):
    o=OriginalScene(ROOT/'Original/claw10/CLAW.EXE');g,s=prepare();o.failAllocation=failedAllocation
    memory[ENTRY][4]=callback;o.write_words(ENTRY+16,[callback])
    compare(0x4c8be0,g,s,(1,320,350,100,ENTRY,0x40002),expectedFault=2)
    coverage.update(o.executed)
o.executed.update(coverage)
print('PASS virtual destructor resolution and real actor/logic/node allocation fault boundaries with complete pre-fault buffers',flush=True)
print(f'{len([a for a in o.executed if 0x400000<=a<0x530000])} original-image instruction addresses; registry/gameplay/destruction, heap and clock external services adapted explicitly')
