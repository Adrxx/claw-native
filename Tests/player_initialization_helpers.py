"""Private initialization original/native harness."""
import ctypes as C
import pathlib, random, struct, subprocess, sys, zlib
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from original_v10 import OriginalV10
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=ROOT/'work/player-init-agent'
WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-dynamiclib','-ffp-contract=off',
    str(ROOT/'Sources/PlayerLocomotion.cpp'),str(ROOT/'Sources/PlayerAirStates.cpp'),str(ROOT/'Sources/PlayerInitialization.cpp'),str(ROOT/'Sources/WorldObjectRuntime.cpp'),str(ROOT/'Sources/PlayerEngine.cpp'),
    str(ROOT/'Sources/PlayerPhysics.cpp'),str(ROOT/'Sources/CollisionResponse.cpp'),str(ROOT/'Sources/TileCollision.cpp'),'-o',str(WORK/'libPlayerInitialization.dylib')],check=True)
class Physics(C.Structure):
    _fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3) for n in
        ('acceleration','velocity','position','minimum','maximum','delta')]+[
        ('stopped',C.c_uint32),('unused',C.c_uint32)]+[(n,C.c_double*3) for n in
        ('remainder','maximumDelta','maximumVelocity')]
class State(C.Structure):
    _fields_=[('actor',C.c_uint32*128),('privateWords',C.c_uint32*78)]+[(n,C.c_uint32) for n in
        ('logicState','inputLatched','inputHeld','stageDelta','animationDelta','powerup','pixelScratch')]+[
        ('physics',Physics),('weaponLogicStatus',C.c_int32),('weaponLogicCallback',C.c_uint32),('weaponDeleteCount',C.c_uint32),('weaponDeleteFlags',C.c_uint32)]+[(n,C.c_uint32)for n in ('highJump','pixelScratchY','audioRegistryDisabled','audioPosition')]
class Rect(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('left','top','right','bottom')]
class Actor(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('flags','x','y','mode','type','stepX','stepY','supportToken','token','deltaX','deltaY')]+[('moveRect',Rect),('hitRect',Rect)]
class Description(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('type','width','height','insideAttribute','outsideAttribute')]+[(n,C.c_int32)for n in ('left','top','right','bottom')]
class World(C.Structure):
    _fields_=[('cells',C.POINTER(C.c_uint32)),('rowOffsets',C.POINTER(C.c_uint32)),('width',C.c_int32),('height',C.c_int32),('shiftX',C.c_uint32),('shiftY',C.c_uint32),('descriptions',C.POINTER(Description)),('descriptionCount',C.c_uint32),('actors',C.POINTER(Actor)),('actorCount',C.c_uint32),('maximumStepX',C.c_uint32),('maximumStepY',C.c_uint32)]
class ObjectRuntime(C.Structure):
    _fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class ObjectContext(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('sceneToken','actorToken','logicToken','sceneDefaultType')]+[(n,C.c_int32)for n in ('worldWidth','worldHeight')]+[('registryToken',C.c_uint32),('layerTokens',C.c_uint32*3)]+[(n,C.c_uint32)for n in ('entryToken','entryCallback','entryFlags')]
class Input(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('pressed','invulnerabilityTimer','minimumX','maximumX','minimumY','maximumY','ignoreHazards','cheat')]
class Initialization(C.Structure):
    _fields_=[('defaults',C.c_uint32*78)]+[(n,C.c_uint32)for n in ('difficulty','worldWidth','worldHeight','startX','startY','checkpointX','checkpointY','privateToken','cachedX','cachedY','powerupRemaining','powerupAuxiliary','accumulator','accumulatorMinimum','accumulatorStep','imageOffsetsAdjusted')]+[('ladderImageTokens',C.c_uint32*7),('ladderImageWord24',C.c_uint32*7)]+[(n,C.c_uint32)for n in ('configurationToken','resetObjectToken')]
Callback=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p)
lib=C.CDLL(str(WORK/'libPlayerInitialization.dylib'))
lib.claw_player_construct_defaults.argtypes=[C.POINTER(State),C.POINTER(Initialization)]
lib.claw_player_dispatch_initialization.argtypes=[C.POINTER(State),C.POINTER(Initialization),C.POINTER(Input),Callback,C.c_void_p];lib.claw_player_dispatch_initialization.restype=C.c_uint32
lib.claw_collision_place_on_ground.argtypes=[C.POINTER(World),C.POINTER(Actor)];lib.claw_collision_place_on_ground.restype=C.c_uint32
lib.claw_world_object_construct.argtypes=[C.POINTER(ObjectRuntime),C.POINTER(ObjectContext),C.c_uint32]
lib.claw_world_object_initialize.argtypes=[C.POINTER(ObjectRuntime),C.POINTER(ObjectContext),C.c_uint32,C.c_uint32,C.c_uint32];lib.claw_world_object_initialize.restype=C.c_uint32
lib.claw_physics_construct.argtypes=[C.POINTER(Physics)]
A,L,P,SC,M,I,W,WC,WL,R=(0x1000000+x*0x1000 for x in range(10))
CONFIG,GAME,CONFIG_VTABLE,IMAGE_MANAGER,RESET_VTABLE=0x100e000,0x100f000,0x1010000,0x1019000,0x101a000
MODE_METHOD,RESET_METHOD=0x10ff010,0x10ff020
rng=random.Random(0x415df0)
state=initialization=input=None;nativeEvents=[];world=None;realGround=False;groundDelta=7;imageManager=IMAGE_MANAGER;gameMode=0;hazard=1

def normalized_actor(words):
    result=list(words);result[3]=state.actor[3];result[0x6c//4]=state.actor[0x6c//4];return result

def original_snapshot(o):
    words=o.read_words(L,93)
    inputs=[o.read_words(I+4,1)[0],words[0x130//4]]+words[0x2c//4:0x3c//4]+[input.ignoreHazards,input.cheat]
    globals_=tuple(o.read_words(0x52be14,2)+o.read_words(0x534ea8,1)+o.read_words(0x534eb0,1)+o.read_words(0x53c9f8,1)+[words[0x14//4]])
    return (tuple(normalized_actor(o.read_words(A,128))),tuple(o.read_words(P,78)),bytes(o.u.mem_read(0x534db8,C.sizeof(Physics))),tuple(inputs),globals_)

def native_snapshot(s):
    j=initialization
    return (tuple(s.actor),tuple(s.privateWords),bytes(s.physics),tuple(getattr(input,n)for n,_ in Input._fields_),tuple([j.cachedX,j.cachedY,j.powerupRemaining,j.powerupAuxiliary,j.accumulator,j.privateToken]))
class Original(OriginalV10):
    def __init__(self):self.events=[];super().__init__(ROOT/'Original/claw10/CLAW.EXE')
    def hook(self,u,entry,size,user):
        super().hook(u,entry,size,user)
        counts={0x4f63ec:1,0x4c7900:2,0x4c7fa0:1,0x4cd800:2,0x4c79e0:2,0x420fc0:1,0x420a10:2,0x421010:2,0x4bc110:0,0x40f680:1,0x420910:1,0x41f990:5,0x41fc30:4,0x4cd740:2,0x417c50:3,MODE_METHOD:0,RESET_METHOD:0}
        if entry not in counts:return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);n=counts[entry];args=self.read_words(sp+4,n);result=0;values=[0,0,0];operation=entry
        if entry==0x4f63ec:assert args==[0x138];values=[args[0],0,0];result=P
        elif entry==0x4c7900:assert receiver==A;values=args+[0]
        elif entry in (0x4c7fa0,0x4c79e0,0x420a10):assert receiver==A;values=args+([0,0]if n==1 else [0])
        elif entry==0x4cd800:assert receiver==M and args==[A,0]
        elif entry==0x420fc0:assert receiver==WL+0x2f4;values=[W,args[0],0]
        elif entry==0x421010:assert receiver==WL;values=[W]+args
        elif entry==0x4bc110:assert receiver==GAME
        elif entry==0x40f680:assert receiver==IMAGE_MANAGER;values=[receiver,args[0],0];result=initialization.ladderImageTokens[args[0]-383]
        elif entry==0x420910:assert receiver==R;values=args+[0,0]
        elif entry==0x41f990:assert args==[A,L,P,0,0]
        elif entry==0x41fc30:assert args==[A,L,P,state.stageDelta];values=[args[3],0,0]
        elif entry==0x4cd740:assert receiver==M and args==[A,0];result=hazard
        elif entry==0x417c50:assert args==[A,L,P]
        elif entry==MODE_METHOD:assert receiver==CONFIG;operation=0x10;values=[CONFIG,0,0];result=gameMode
        elif entry==RESET_METHOD:assert receiver==WL;operation=0xb0;values=[W,0,0]
        self.events.append((operation,*values,original_snapshot(self)))
        if entry==0x4cd800 and realGround:return
        if entry==0x4cd800:self.write_words(A+0x50,[(self.read_words(A+0x50,1)[0]+groundDelta)&0xffffffff])
        if entry==0x4c7900:self.write_words(A+0x170,[imageManager]);self.write_words(A+0x16c,[11]);self.write_words(A+0x174,[0xabcdef00])
        cdecl=entry in (0x4f63ec,0x41f990,0x41fc30,0x417c50)
        u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if cdecl else n*4))
o=Original()
@Callback
def dependency(ptr,entry,a,b,c,context):
    s=ptr.contents;nativeEvents.append((entry,a,b,c,native_snapshot(s)))
    if entry==0x4f63ec:return P
    if entry==0x10:return gameMode
    if entry==0x4c7900:s.actor[0x170//4]=imageManager;s.actor[0x16c//4]=11;s.actor[0x174//4]=0xabcdef00
    if entry==0x40f680:return initialization.ladderImageTokens[b-383]
    if entry==0x4cd740:return hazard
    if entry==0x4cd800:
        if realGround:
            v=Actor();fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
            for name,offset in fields.items():setattr(v,name,s.actor[offset//4])
            v.token=1;v.moveRect=Rect(*s.actor[0x118//4:0x128//4]);v.hitRect=Rect(*s.actor[0x128//4:0x138//4])
            result=lib.claw_collision_place_on_ground(C.byref(world),C.byref(v))
            for name,offset in fields.items():s.actor[offset//4]=getattr(v,name)
            return result
        s.actor[0x50//4]=(s.actor[0x50//4]+groundDelta)&0xffffffff
    return 0

def new():
    s,j,i=State(),Initialization(),Input()
    for n in range(128):s.actor[n]=rng.getrandbits(32)
    for n in range(78):s.privateWords[n]=rng.getrandbits(32);j.defaults[n]=rng.getrandbits(32)
    for n,_ in Initialization._fields_:
        if n not in ('defaults','ladderImageTokens','ladderImageWord24'):setattr(j,n,rng.getrandbits(32))
    for n,_ in Input._fields_:setattr(i,n,rng.getrandbits(32))
    for name in ('acceleration','velocity','position','minimum','maximum','delta','remainder','maximumDelta','maximumVelocity'):
        for n in range(3):getattr(s.physics,name)[n]=rng.uniform(-10000,10000)
    s.physics.elapsed=rng.uniform(-10000,10000);s.physics.timestep=rng.uniform(-10000,10000);s.physics.unused=rng.getrandbits(32);s.physics.stopped=rng.choice([0,1])
    s.logicState=rng.choice([0,23]);s.inputHeld=rng.getrandbits(32);s.inputLatched=rng.getrandbits(32);s.stageDelta=rng.choice([0,1,16,33,2001,0xffffffff]);s.animationDelta=rng.choice([0,1,17,80]);s.powerup=rng.getrandbits(32)
    s.privateWords[75]=rng.choice([0,W]);s.privateWords[1]=rng.choice([0,1]);s.privateWords[0]=rng.choice([0,1,2,0xffffffff]);s.weaponLogicStatus=rng.choice([-1,0,1]);s.weaponLogicCallback=rng.getrandbits(32)
    j.difficulty=rng.choice([0,1,0xffffffff]);j.defaults[9]=rng.choice([0,1]);j.privateToken=rng.choice([0,P])if s.logicState==0 else P;j.configurationToken=CONFIG;j.resetObjectToken=rng.choice([0,W]);j.checkpointX=rng.choice([0xffffffff,j.checkpointX]);j.checkpointY=rng.choice([0xffffffff,j.checkpointY]);j.imageOffsetsAdjusted=rng.choice([0,1])
    for n in range(7):j.ladderImageTokens[n]=rng.choice([0,0x1011000+n*0x1000]);j.ladderImageWord24[n]=rng.getrandbits(32)
    return s,j,i

def prepare(s,j,i):
    global state,initialization,input
    state=s;initialization=j;input=i;o.events=[];nativeEvents.clear()
    o.write_words(A,s.actor);o.write_words(A+0xc,[SC]);o.write_words(A+0x6c,[L]);o.write_words(P,s.privateWords)
    logic=[rng.getrandbits(32)for _ in range(93)];logic[0x14//4]=j.privateToken;logic[0x1c//4]=s.logicState;logic[0x130//4]=i.invulnerabilityTimer;logic[0x2c//4:0x3c//4]=[i.minimumX,i.maximumX,i.minimumY,i.maximumY];o.write_words(L,logic)
    o.write_words(0x534c80,j.defaults);o.write_words(0x53725c,[j.difficulty]);o.write_words(0x537204,[I]);o.write_words(I+4,[i.pressed,s.inputHeld,s.inputLatched]);o.write_words(0x53720c,[s.stageDelta]);o.write_words(0x5430c4,[s.animationDelta]);o.write_words(0x534eac,[s.powerup]);o.u.mem_write(0x534db8,bytes(s.physics))
    o.write_words(0x52be14,[j.cachedX,j.cachedY]);o.write_words(0x534ea8,[j.powerupRemaining]);o.write_words(0x534eb0,[j.powerupAuxiliary]);o.write_words(0x53c9f8,[j.accumulator]);o.write_words(0x52c6e4,[j.accumulatorMinimum]);o.write_words(0x52c6ec,[j.accumulatorStep]);o.write_words(0x534eb4,[j.imageOffsetsAdjusted]);o.write_words(0x537230,[i.ignoreHazards]);o.write_words(0x537214,[i.cheat])
    o.write_words(0x5371fc,[GAME]);o.write_words(GAME+0x2c,[CONFIG]);o.write_words(CONFIG,[CONFIG_VTABLE]);o.write_words(CONFIG_VTABLE+0x10,[MODE_METHOD]);o.write_words(CONFIG+0x44,[j.checkpointX,j.checkpointY]);o.write_words(SC+0x24,[M]);o.write_words(M+0x5c,[0x100c000]);o.write_words(0x100c000+0x30,[j.worldWidth,j.worldHeight]);o.write_words(0x100c000+0x84,[j.startX,j.startY]);o.write_words(SC+0x28,[R])
    o.write_words(W+0x6c,[WC]);o.write_words(WC+0x18,[WL]);o.write_words(WL,[RESET_VTABLE]);o.write_words(RESET_VTABLE+0xb0,[RESET_METHOD]);o.write_words(0x5349dc,[j.resetObjectToken]);o.write_words(WL+0x20,[s.weaponLogicStatus]);o.write_words(WL+0x14,[s.weaponLogicCallback])
    for n in range(7):
        if j.ladderImageTokens[n]:o.write_words(j.ladderImageTokens[n]+0x24,[j.ladderImageWord24[n]])
    return logic

def compare(s,j,i,case,constructor=False):
    before=State.from_buffer_copy(s);beforeJ=Initialization.from_buffer_copy(j);logic=prepare(s,j,i)
    result=o.call(0x415ce0 if constructor else 0x415df0,0,b''if constructor else struct.pack('<I',A))
    if constructor:lib.claw_player_construct_defaults(C.byref(s),C.byref(j))
    else:assert result==lib.claw_player_dispatch_initialization(C.byref(s),C.byref(j),C.byref(i),dependency,None)==1,(case,'return')
    assert list(s.actor)==normalized_actor(o.read_words(A,128)),(case,'actor',[(hex(n*4),hex(x),hex(y))for n,(x,y)in enumerate(zip(s.actor,normalized_actor(o.read_words(A,128))))if x!=y])
    expected=o.read_words(P,78);assert list(s.privateWords)==expected,(case,'private',[(n,hex(x),hex(y))for n,(x,y)in enumerate(zip(s.privateWords,expected))if x!=y])
    assert bytes(s.physics)==o.u.mem_read(0x534db8,C.sizeof(Physics)),(case,'physics')
    assert s.powerup==o.read_words(0x534eac,1)[0],(case,'powerup')
    assert s.inputLatched==o.read_words(I+12,1)[0]and s.inputHeld==o.read_words(I+8,1)[0],(case,'input')
    actualLogic=list(logic);actualLogic[0x14//4]=j.privateToken;actualLogic[0x1c//4]=s.logicState;actualLogic[0x130//4]=i.invulnerabilityTimer;actualLogic[0x2c//4:0x3c//4]=[i.minimumX,i.maximumX,i.minimumY,i.maximumY]
    assert actualLogic==o.read_words(L,93),(case,'logic buffer')
    assert tuple(getattr(i,n)for n,_ in Input._fields_)==original_snapshot(o)[3],(case,'input context')
    assert list(j.defaults)==o.read_words(0x534c80,78),(case,'defaults')
    for n,addr in [('cachedX',0x52be14),('cachedY',0x52be18),('powerupRemaining',0x534ea8),('powerupAuxiliary',0x534eb0),('accumulator',0x53c9f8)]:assert getattr(j,n)==o.read_words(addr,1)[0],(case,n)
    for n in range(7):
        if beforeJ.ladderImageTokens[n]:assert j.ladderImageWord24[n]==o.read_words(beforeJ.ladderImageTokens[n]+0x24,1)[0],(case,'ladder',n)
    assert s.weaponLogicCallback==o.read_words(WL+0x14,1)[0],(case,'weapon callback')
    expectedState=State.from_buffer_copy(before);expectedState.actor[:]=normalized_actor(o.read_words(A,128));expectedState.privateWords[:]=o.read_words(P,78)
    expectedState.physics=Physics.from_buffer_copy(o.u.mem_read(0x534db8,C.sizeof(Physics)));expectedState.logicState=o.read_words(L+0x1c,1)[0]
    expectedState.powerup=o.read_words(0x534eac,1)[0];expectedState.inputHeld=o.read_words(I+8,1)[0];expectedState.inputLatched=o.read_words(I+12,1)[0];expectedState.weaponLogicCallback=o.read_words(WL+0x14,1)[0]
    assert bytes(s)==bytes(expectedState),(case,'complete portable state')
    expectedJ=Initialization.from_buffer_copy(beforeJ);expectedJ.defaults[:]=o.read_words(0x534c80,78);expectedJ.privateToken=o.read_words(L+0x14,1)[0]
    for n,addr in [('cachedX',0x52be14),('cachedY',0x52be18),('powerupRemaining',0x534ea8),('powerupAuxiliary',0x534eb0),('accumulator',0x53c9f8)]:setattr(expectedJ,n,o.read_words(addr,1)[0])
    for n in range(7):
        if beforeJ.ladderImageTokens[n]:expectedJ.ladderImageWord24[n]=o.read_words(beforeJ.ladderImageTokens[n]+0x24,1)[0]
    assert bytes(j)==bytes(expectedJ),(case,'complete initialization context')
    assert nativeEvents==o.events,(case,'event diff',[(n,hex(x[0]),hex(y[0]))for n,(x,y)in enumerate(zip(nativeEvents,o.events))if x!=y],len(nativeEvents),len(o.events))
def install_world(levelOne=False):
    columns,rows=16,12
    cells=[0]*(columns*rows)
    for x in range(columns):cells[8*columns+x]=1
    for x in (8,9):cells[8*columns+x]=0
    for y in range(3,8):cells[y*columns+4]=3
    cells[8*columns+2]=4
    descriptions=[Description(1,64,64,i,0,0,0,0,0)for i in range(5)]
    if levelOne:
        raw=(ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes()
        offset=struct.unpack_from('<I',raw,736)[0]
        if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
        for i in range(struct.unpack_from('<I',raw,732)[0]):
            ph=struct.unpack_from('<40I',raw,offset+160*i)
            if ph[2]&1:
                columns,rows=ph[24:26];assert ph[22:24]==(64,64)
                cells=list(struct.unpack_from('<'+'I'*(columns*rows),raw,ph[33]));break
        descOffset=struct.unpack_from('<I',raw,740)[0];count=struct.unpack_from('<I',raw,descOffset+8)[0];pos=descOffset+32
        descriptions=[]
        for _ in range(count):
            kind,unknown,width,height=struct.unpack_from('<4I',raw,pos)
            if kind==1:
                descriptions.append(Description(kind,width,height,struct.unpack_from('<I',raw,pos+16)[0],0,0,0,0,0));pos+=20
            else:
                assert kind==2
                outside,inside=struct.unpack_from('<2I',raw,pos+16)
                descriptions.append(Description(kind,width,height,inside,outside,*struct.unpack_from('<4i',raw,pos+24)));pos+=40
    offsets=[x*columns for x in range(rows)]
    owner,actorList,plane,descPtrs,descData,cellData,rowData=0x100b000,0x100d000,0x100c000,0x1020000,0x1030000,0x1040000,0x1080000
    o.write_words(M+0xc,[owner]);o.write_words(owner+8,[actorList]);o.write_words(actorList+0x14,[0])
    o.write_words(M+0x4c,[descPtrs]);o.write_words(M+0x5c,[plane]);o.write_words(M+0x64,[64,64])
    o.write_words(plane+0x20,[cellData,rowData]);o.write_words(plane+0x30,[columns*64,rows*64]);o.write_words(plane+0x8c,[6,6])
    o.write_words(cellData,cells);o.write_words(rowData,offsets)
    for i,d in enumerate(descriptions):o.write_words(descData+i*0x40,[0x513980 if d.type==1 else 0x5139c8,d.width,d.height,d.insideAttribute if d.type==1 else d.outsideAttribute,d.insideAttribute,d.left,d.top,d.right,d.bottom])
    o.write_words(descPtrs,[descData+i*0x40 for i in range(len(descriptions))])
    cs,rs,ds=(C.c_uint32*len(cells))(*cells),(C.c_uint32*len(offsets))(*offsets),(Description*len(descriptions))(*descriptions)
    world=World(cs,rs,columns*64,rows*64,6,6,ds,len(descriptions),None,0,64,64);world.storage=(cs,rs,ds)
    return world

