"""Private original/native player damage harness."""
import ctypes as C
import pathlib, random, struct, subprocess, sys, zlib
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from original_v10 import OriginalV10
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=ROOT/'work/player-damage-agent'
WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-dynamiclib','-ffp-contract=off',
    str(ROOT/'Sources/PlayerLocomotion.cpp'),str(ROOT/'Sources/PlayerAirStates.cpp'),str(ROOT/'Sources/PlayerDamage.cpp'),str(ROOT/'Sources/PlayerEngine.cpp'),
    str(ROOT/'Sources/PlayerPhysics.cpp'),str(ROOT/'Sources/CollisionResponse.cpp'),str(ROOT/'Sources/TileCollision.cpp'),'-o',str(WORK/'libPlayerDamage.dylib')],check=True)
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
class Input(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('pressed','invulnerabilityTimer','minimumX','maximumX','minimumY','maximumY','ignoreHazards','cheat')]
class Damage(C.Structure):
    _fields_=[('attackerToken',C.c_uint32),('attackerActor',C.c_uint32*128)]+[(n,C.c_uint32)for n in ('configurationToken','configurationWord764','logicWord20','infiniteLives','overlayMode','overlayOffsetY','windowToken','audioManagerAvailable','resolvedSoundPoolToken')]
Callback=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p)
lib=C.CDLL(str(WORK/'libPlayerDamage.dylib'))
for name in ('hit','dispatch_damage'):
    f=getattr(lib,'claw_player_'+name);f.argtypes=[C.POINTER(State),C.POINTER(Damage),C.POINTER(Input),Callback,C.c_void_p];f.restype=C.c_uint32
for name in ('enter_spike_death','update_fall_death','update_spike_death'):
    getattr(lib,'claw_player_'+name).argtypes=[C.POINTER(State),C.POINTER(Damage),Callback,C.c_void_p]
lib.claw_player_enter_fall_death.argtypes=[C.POINTER(State),C.POINTER(Damage),C.c_uint32,Callback,C.c_void_p]
lib.claw_player_update_hurt.argtypes=[C.POINTER(State),Callback,C.c_void_p]
lib.claw_collision_move.argtypes=[C.POINTER(World),C.POINTER(Actor),C.c_uint32,C.c_uint32,C.c_uint32]
A,L,P,SC,M,I,W,WC,WL,R=(0x1000000+x*0x1000 for x in range(10))
CONFIG,GAME,CONFIG_VTABLE,WINDOW,OVERLAY=0x100e000,0x100f000,0x1010000,0x1023000,0x1024000
ATTACKER,ATTACKER_CONTAINER,ATTACKER_LOGIC,ATTACKER_VTABLE=0x101c000,0x101d000,0x101e000,0x101f000
SOUND,POOL=0x1021000,0x1022000
MODE_METHOD,ATTACKER_METHOD,POST_METHOD=0x10ff010,0x10ff020,0x10ff030
rng=random.Random(0x41ce80)
state=damage=input=None;nativeEvents=[];marker=0;gameMode=0;randomResults=[0];randomIndex=0;resolvedSound=SOUND;collectReturn=0;collisionMode=1;hazard=1;platform=(0,0);realCollision=False;world=None;realRandom=False;nativeRandomSeed=1
RNG_TLS=0x1025000

def normalized_actor(words):
    result=list(words);result[3]=state.actor[3];result[0x6c//4]=state.actor[0x6c//4];return result

def normalized_attacker(words):
    result=list(words);result[0x6c//4]=damage.attackerActor[0x6c//4];return result

def original_snapshot(o):
    words=o.read_words(L,93)
    inputs=[o.read_words(I+4,1)[0],words[0x130//4]]+words[0x2c//4:0x3c//4]+[input.ignoreHazards,input.cheat]
    return (tuple(normalized_actor(o.read_words(A,128))),tuple(o.read_words(P,78)),bytes(o.u.mem_read(0x534db8,C.sizeof(Physics))),tuple(inputs),tuple(normalized_attacker(o.read_words(ATTACKER,128))),words[0x20//4],o.read_words(CONFIG+0x764,1)[0])

def native_snapshot(s):
    return (tuple(s.actor),tuple(s.privateWords),bytes(s.physics),tuple(getattr(input,n)for n,_ in Input._fields_),tuple(damage.attackerActor),damage.logicWord20,damage.configurationWord764)
class Original(OriginalV10):
    def __init__(self):self.events=[];self.randomIndex=0;super().__init__(ROOT/'Original/claw10/CLAW.EXE')
    def hook(self,u,entry,size,user):
        super().hook(u,entry,size,user)
        counts={0x4c79e0:2,0x4c8220:1,0x420a10:2,0x421010:2,0x420fc0:1,0x4a3050:0,0x4a7dc0:0,0x4061b0:1,0x4f6286:2,0x4208e0:4,0x4b45f0:4,0x461a00:6,0x461c40:4,0x4c82a0:1,0x4cbb60:4,0x41ebd0:0,0x4b7aa0:1,0x41f990:5,0x41ee60:4,0x41d6f0:1,0x41f850:2,0x473ae0:1,0x41fc30:4,0x420910:1,0x4cd740:2,MODE_METHOD:0,ATTACKER_METHOD:0,POST_METHOD:4}
        if entry not in counts:return
        if entry==0x4a3050 and realRandom:
            self.events.append((entry,0,0,0,original_snapshot(self)));self.randomIndex+=1;return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);n=counts[entry];args=self.read_words(sp+4,n);result=0;values=[0,0,0];operation=entry
        if entry in (0x4c79e0,0x420a10):assert receiver==A;values=args+[0]
        elif entry in (0x4c8220,0x4c82a0):assert receiver==A+0x188;values=args+[0,0];result=marker if entry==0x4c82a0 else 0
        elif entry==0x421010:assert receiver in (WL,ATTACKER_LOGIC);values=[W if receiver==WL else ATTACKER]+args
        elif entry==0x420fc0:assert receiver in (WL+0x2f4,ATTACKER_LOGIC+0x2f4);values=[W if receiver==WL+0x2f4 else ATTACKER,args[0],0]
        elif entry==0x4a7dc0:result=RNG_TLS
        elif entry==0x4a3050:result=randomResults[self.randomIndex%len(randomResults)];self.randomIndex+=1
        elif entry==0x4061b0:assert receiver==R;values=args+[0,0];result=resolvedSound
        elif entry==0x4f6286:assert receiver==R+0x10;values=[args[0],0,0];self.write_words(args[1],[resolvedSound]);result=resolvedSound
        elif entry==0x4208e0:assert receiver==SOUND and args[1:]==[0,0,0];values=[SOUND,args[0],0]
        elif entry==0x4b45f0:assert receiver==POOL and args[1:]==[0,0,0];values=[POOL,args[0],0]
        elif entry==0x461a00:assert args[0]==SC and args[4:]==[1,A];values=args[1:4]
        elif entry==0x461c40:assert args[0]==SC;values=args[1:]
        elif entry==0x4cbb60:assert receiver==M and args[0]==A;values=args[1:]
        elif entry==0x4b7aa0:assert receiver==GAME and args==[0]
        elif entry==0x41f990:assert args[:3]==[A,L,P];values=args[3:]+[0]
        elif entry==0x41ee60:assert args[:3]==[A,L,P];values=[args[3],0,0]
        elif entry==0x41d6f0:assert args==[ATTACKER];values=args+[0,0]
        elif entry==0x41f850:assert args==[ATTACKER,P];values=[ATTACKER,0,0]
        elif entry==0x473ae0:assert args==[ATTACKER];values=args+[0,0];result=collectReturn
        elif entry==0x41fc30:assert args==[A,L,P,state.stageDelta];values=[args[3],0,0]
        elif entry==0x420910:assert receiver==R;values=args+[0,0]
        elif entry==0x4cd740:assert receiver==M and args==[A,0];result=hazard
        elif entry==MODE_METHOD:assert receiver==CONFIG;operation=0x10;values=[CONFIG,0,0];result=gameMode
        elif entry==ATTACKER_METHOD:assert receiver==ATTACKER_LOGIC;operation=0x2c;values=[ATTACKER,0,0]
        elif entry==POST_METHOD:assert args[1]==0x111 and args[3]==0;operation=0x546d50;values=args[:3]
        self.events.append((operation,*values,original_snapshot(self)))
        if entry==0x4cbb60:
            if realCollision:return
            self.write_words(A+0x4c,args[1:3]);self.write_words(A+0xcc,[collisionMode])
        cdecl=entry in (0x4a3050,0x4a7dc0,0x461a00,0x461c40,0x41ebd0,0x41f990,0x41ee60,0x41d6f0,0x41f850,0x473ae0,0x41fc30)
        u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if cdecl else n*4))
o=Original()
@Callback
def dependency(ptr,entry,a,b,c,context):
    global randomIndex,nativeRandomSeed
    s=ptr.contents
    if entry==0x158:return platform[0]
    if entry==0x15c:return platform[1]
    if entry==0x417c50:
        lib.claw_player_enter_spike_death(ptr,C.byref(damage),dependency,None)
        return 0
    nativeEvents.append((entry,a,b,c,native_snapshot(s)))
    if entry==0x10:return gameMode
    if entry==0x4a3050:
        randomIndex+=1
        if realRandom:
            nativeEvents.append((0x4a7dc0,0,0,0,native_snapshot(s)));nativeRandomSeed=(nativeRandomSeed*214013+2531011)&0xffffffff;return (nativeRandomSeed>>16)&0x7fff
        return randomResults[(randomIndex-1)%len(randomResults)]
    if entry in (0x4061b0,0x4f6286):return resolvedSound
    if entry==0x473ae0:return collectReturn
    if entry==0x4c82a0:return marker
    if entry==0x4cd740:return hazard
    if entry==0x4cbb60:
        if realCollision:
            v=Actor();fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
            for name,offset in fields.items():setattr(v,name,s.actor[offset//4])
            v.token=1;v.moveRect=Rect(*s.actor[0x118//4:0x128//4]);v.hitRect=Rect(*s.actor[0x128//4:0x138//4])
            lib.claw_collision_move(C.byref(world),C.byref(v),a,b,c)
            for name,offset in fields.items():s.actor[offset//4]=getattr(v,name)
            s.actor[0x118//4:0x128//4]=[getattr(v.moveRect,n)for n,_ in Rect._fields_];s.actor[0x128//4:0x138//4]=[getattr(v.hitRect,n)for n,_ in Rect._fields_]
        else:s.actor[0x4c//4]=a;s.actor[0x50//4]=b;s.actor[0xcc//4]=collisionMode
    return 0

def new():
    s,t,i=State(),Damage(),Input()
    for n in range(128):s.actor[n]=rng.getrandbits(32);t.attackerActor[n]=rng.getrandbits(32)
    for n in range(78):s.privateWords[n]=rng.getrandbits(32)
    for n,_ in Damage._fields_:
        if n!='attackerActor':setattr(t,n,rng.getrandbits(32))
    for n,_ in Input._fields_:setattr(i,n,rng.getrandbits(32))
    for name in ('acceleration','velocity','position','minimum','maximum','delta','remainder','maximumDelta','maximumVelocity'):
        for n in range(3):getattr(s.physics,name)[n]=rng.uniform(-10000,10000)
    s.physics.elapsed=rng.uniform(-10000,10000);s.physics.timestep=rng.uniform(-10000,10000);s.physics.unused=rng.getrandbits(32);s.physics.stopped=rng.choice([0,1])
    s.actor[0x74//4]=t.attackerToken=rng.choice([0,ATTACKER]);s.actor[0x80//4]=rng.choice([0,W]);s.actor[0x1a4//4]=rng.choice([0,1]);s.actor[0x19c//4]=rng.choice([0,1,9]);s.actor[0xcc//4]=rng.choice([1,2,3,4,5,8]);s.actor[0x10c//4]=rng.choice([0,1,99,100,101,0xffffffff,0x80000000,0x7fffffff]);s.actor[0x148//4]=rng.getrandbits(32)
    t.attackerActor[0xd0//4]=rng.choice([0,1,4,0x10,0x40,0x100,0x10000,0x40000,0x100000,0x200000,0x800000,0x1000000,0xffffffff]);t.attackerActor[0xfc//4]=rng.choice([0,1,100,101,0x26bf,0xffffffff,0x80000000,0x7fffffff]);t.attackerActor[0x104//4]=rng.choice([0,1,100,0xffffffff,0x80000000,0x7fffffff]);t.attackerActor[0x138//4]=rng.choice([0x80000000,rng.getrandbits(32)])
    s.privateWords[75]=rng.choice([0,W,ATTACKER]);s.privateWords[1]=rng.choice([0,1]);s.privateWords[0]=rng.choice([0,1,2,0xffffffff]);s.privateWords[6]=rng.choice([0,1]);s.privateWords[16]=rng.choice([0,799,800,801,0xffffffff,0x80000000,0x7fffffff]);s.privateWords[31]=rng.choice([0,1,3,9,0xffffffff,0x80000000,0x7fffffff]);s.weaponLogicStatus=rng.choice([-1,0,1]);s.weaponLogicCallback=rng.getrandbits(32)
    s.logicState=rng.choice([4,8,24,25,26,27,28,31,5004,5005]);s.inputHeld=rng.getrandbits(32);s.inputLatched=rng.getrandbits(32);s.stageDelta=rng.choice([0,1,16,33,2001,0xffffffff]);s.animationDelta=rng.choice([0,1,17,80,0xffffffff]);s.powerup=rng.getrandbits(32);s.audioRegistryDisabled=rng.choice([0,1]);s.audioPosition=rng.randrange(101)
    t.configurationToken=CONFIG;t.infiniteLives=rng.choice([0,1]);t.overlayMode=rng.choice([0,1,2]);t.audioManagerAvailable=rng.choice([0,1]);t.resolvedSoundPoolToken=POOL
    return s,t,i

def prepare(s,t,i):
    global state,damage,input,randomIndex
    state=s;damage=t;input=i;o.events=[];nativeEvents.clear();o.randomIndex=0;randomIndex=0
    o.write_words(A,s.actor);o.write_words(A+0xc,[SC]);o.write_words(A+0x6c,[L]);o.write_words(P,s.privateWords)
    logic=[rng.getrandbits(32)for _ in range(93)];logic[0x14//4]=P;logic[0x1c//4]=s.logicState;logic[0x20//4]=t.logicWord20;logic[0x130//4]=i.invulnerabilityTimer;logic[0x2c//4:0x3c//4]=[i.minimumX,i.maximumX,i.minimumY,i.maximumY];o.write_words(L,logic)
    o.write_words(ATTACKER,t.attackerActor);o.write_words(ATTACKER+0x6c,[ATTACKER_CONTAINER]);o.write_words(ATTACKER_CONTAINER+0x18,[ATTACKER_LOGIC]);o.write_words(ATTACKER_LOGIC,[ATTACKER_VTABLE]);o.write_words(ATTACKER_VTABLE+0x2c,[ATTACKER_METHOD])
    if s.privateWords[75]==ATTACKER:o.write_words(ATTACKER_LOGIC+0x20,[s.weaponLogicStatus]);o.write_words(ATTACKER_LOGIC+0x14,[s.weaponLogicCallback])
    o.write_words(0x537204,[I]);o.write_words(I+4,[i.pressed,s.inputHeld,s.inputLatched]);o.write_words(0x53720c,[s.stageDelta]);o.write_words(0x5430c4,[s.animationDelta]);o.write_words(0x534eac,[s.powerup]);o.write_words(0x544e88,[s.pixelScratchY]);o.u.mem_write(0x534db8,bytes(s.physics));o.write_words(0x537230,[i.ignoreHazards]);o.write_words(0x537214,[i.cheat]);o.write_words(0x53722c,[t.infiniteLives])
    o.write_words(0x5371fc,[GAME]);o.write_words(GAME+0x2c,[t.configurationToken]);o.write_words(CONFIG,[CONFIG_VTABLE]);o.write_words(CONFIG_VTABLE+0x10,[MODE_METHOD]);o.write_words(CONFIG+0x764,[t.configurationWord764]);o.write_words(GAME+4,[WINDOW]);o.write_words(WINDOW+4,[t.windowToken]);o.write_words(0x546d50,[POST_METHOD]);o.write_words(0x537960,[OVERLAY]);o.write_words(OVERLAY+0x44,[t.overlayMode]);o.write_words(OVERLAY+0xb0,[t.overlayOffsetY])
    o.write_words(SC+0x24,[M]);o.write_words(SC+0x28,[R]);o.write_words(R+0x30,[s.audioRegistryDisabled]);o.write_words(0x532c10,[s.audioPosition]);o.write_words(0x532c0c,[t.audioManagerAvailable]);o.write_words(SOUND+0x10,[POOL]);o.write_words(W+0x6c,[WC]);o.write_words(WC+0x18,[WL]);o.write_words(WL+0x20,[s.weaponLogicStatus]);o.write_words(WL+0x14,[s.weaponLogicCallback]);o.write_words(W+0x158,platform)
    if realRandom:o.write_words(RNG_TLS+0x14,[nativeRandomSeed])
    return logic

def compare(s,t,i,entry,case,notice=0):
    before=State.from_buffer_copy(s);beforeT=Damage.from_buffer_copy(t);logic=prepare(s,t,i)
    args=struct.pack('<I',A)if entry in (0x41ce80,0x415df0)else struct.pack('<III',A,L,P)+(struct.pack('<I',notice)if entry==0x417b00 else b'')
    result=o.call(entry,0,args)
    if entry==0x41ce80:actual=lib.claw_player_hit(C.byref(s),C.byref(t),C.byref(i),dependency,None);assert result==actual,(case,'hit return')
    elif entry==0x415df0:assert result==lib.claw_player_dispatch_damage(C.byref(s),C.byref(t),C.byref(i),dependency,None)==1,(case,'dispatch return')
    elif entry==0x417b00:lib.claw_player_enter_fall_death(C.byref(s),C.byref(t),notice,dependency,None)
    elif entry==0x417c50:lib.claw_player_enter_spike_death(C.byref(s),C.byref(t),dependency,None)
    elif entry==0x41c030:lib.claw_player_update_hurt(C.byref(s),dependency,None)
    else:getattr(lib,'claw_player_'+{0x41c2b0:'update_fall_death',0x41c440:'update_spike_death'}[entry])(C.byref(s),C.byref(t),dependency,None)
    expected=normalized_actor(o.read_words(A,128));assert list(s.actor)==expected,(case,'actor',[(hex(n*4),hex(x),hex(y))for n,(x,y)in enumerate(zip(s.actor,expected))if x!=y])
    expected=o.read_words(P,78);assert list(s.privateWords)==expected,(case,'private',[(n,hex(x),hex(y))for n,(x,y)in enumerate(zip(s.privateWords,expected))if x!=y])
    assert bytes(s.physics)==o.u.mem_read(0x534db8,C.sizeof(Physics)),(case,'physics')
    expectedT=Damage.from_buffer_copy(beforeT);expectedT.attackerActor[:]=normalized_attacker(o.read_words(ATTACKER,128));expectedT.logicWord20=o.read_words(L+0x20,1)[0];expectedT.configurationWord764=o.read_words(CONFIG+0x764,1)[0]
    assert bytes(t)==bytes(expectedT),(case,'complete damage context')
    actualLogic=list(logic);actualLogic[0x1c//4]=s.logicState;actualLogic[0x20//4]=t.logicWord20;actualLogic[0x130//4]=i.invulnerabilityTimer
    assert actualLogic==o.read_words(L,93),(case,'logic buffer')
    assert tuple(getattr(i,n)for n,_ in Input._fields_)==original_snapshot(o)[3],(case,'input context')
    expectedS=State.from_buffer_copy(before);expectedS.actor[:]=normalized_actor(o.read_words(A,128));expectedS.privateWords[:]=o.read_words(P,78);expectedS.physics=Physics.from_buffer_copy(o.u.mem_read(0x534db8,C.sizeof(Physics)));expectedS.logicState=o.read_words(L+0x1c,1)[0];expectedS.inputHeld=o.read_words(I+8,1)[0];expectedS.inputLatched=o.read_words(I+12,1)[0];expectedS.pixelScratchY=o.read_words(0x544e88,1)[0]if entry in (0x41c2b0,0x415df0)else before.pixelScratchY
    assert bytes(s)==bytes(expectedS),(case,'complete state')
    assert nativeEvents==o.events,(case,'event diff',[(n,hex(x[0]),hex(y[0]),x[1:4],y[1:4])for n,(x,y)in enumerate(zip(nativeEvents,o.events))if x!=y],len(nativeEvents),len(o.events))
    assert randomIndex==o.randomIndex,(case,'random calls')
    if realRandom:assert nativeRandomSeed==o.read_words(RNG_TLS+0x14,1)[0],(case,'original RNG state')
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

