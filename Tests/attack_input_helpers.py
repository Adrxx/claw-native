"""Private attack-input original/native comparison harness."""
import ctypes as C
import pathlib, random, struct, subprocess, sys, zlib
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from original_v10 import OriginalV10
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=ROOT/'work/attack-input-agent'
WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-dynamiclib','-ffp-contract=off',
    str(ROOT/'Sources/PlayerLocomotion.cpp'),str(ROOT/'Sources/PlayerAirStates.cpp'),str(ROOT/'Sources/PlayerAttackInput.cpp'),str(ROOT/'Sources/PlayerEngine.cpp'),
    str(ROOT/'Sources/PlayerPhysics.cpp'),str(ROOT/'Sources/CollisionResponse.cpp'),str(ROOT/'Sources/TileCollision.cpp'),'-o',str(WORK/'libPlayerAttackInput.dylib')],check=True)
class Physics(C.Structure):
    _fields_=[('elapsed',C.c_double),('timestep',C.c_double)]+[(n,C.c_double*3) for n in
        ('acceleration','velocity','position','minimum','maximum','delta')]+[
        ('stopped',C.c_uint32),('unused',C.c_uint32)]+[(n,C.c_double*3) for n in
        ('remainder','maximumDelta','maximumVelocity')]
class State(C.Structure):
    _fields_=[('actor',C.c_uint32*128),('privateWords',C.c_uint32*78)]+[(n,C.c_uint32) for n in
        ('logicState','inputLatched','inputHeld','stageDelta','animationDelta','powerup','pixelScratch')]+[
        ('physics',Physics),('weaponLogicStatus',C.c_int32),('weaponLogicCallback',C.c_uint32),('weaponDeleteCount',C.c_uint32),('weaponDeleteFlags',C.c_uint32)]+[(n,C.c_uint32)for n in ('highJump','pixelScratchY','audioRegistryDisabled','audioPosition')]
class Candidate(C.Structure):
    _fields_=[('token',C.c_uint32),('actor',C.c_uint32*128)]
class Attack(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('pressed','difficulty','damage100','damage0','targetToken')]+[('targetActor',C.c_uint32*128),('projectileToken',C.c_uint32),('projectileActor',C.c_uint32*128)]+[(n,C.c_uint32)for n in ('projectileLogicRepeat','spawnX','spawnY','spawnZ','spawnName','spawnFlags')]
Callback=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p)
lib=C.CDLL(str(WORK/'libPlayerAttackInput.dylib'))
for name in ('select_attack','select_weapon_attack','update_attack'):
    f=getattr(lib,'claw_player_'+name);f.argtypes=[C.POINTER(State),C.POINTER(Attack),Callback,C.c_void_p];f.restype=C.c_uint32
lib.claw_player_nearest_attack_target.argtypes=[C.POINTER(State),C.POINTER(Attack),C.POINTER(Candidate),C.c_uint32];lib.claw_player_nearest_attack_target.restype=C.c_int32
lib.claw_player_attack_random_range.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,Callback,C.c_void_p];lib.claw_player_attack_random_range.restype=C.c_uint32
lib.claw_player_start_attack.argtypes=[C.POINTER(State),C.POINTER(Attack),C.c_uint32,Callback,C.c_void_p]
lib.claw_player_enter_climb.argtypes=[C.POINTER(State),Callback,C.c_void_p]
lib.claw_player_enter_attack_stand.argtypes=[C.POINTER(State),Callback,C.c_void_p]
lib.claw_player_can_lift.argtypes=[C.POINTER(State),C.POINTER(Attack)];lib.claw_player_can_lift.restype=C.c_uint32
A,L,P,SC,M,I,W,WC,WL,R=(0x1000000+x*0x1000 for x in range(10))
TARGET,PROJECTILE,PROJECTILE_LOGIC,OBJECTS=0x100b000,0x100c000,0x100d000,0x100e000
rng=random.Random(0x41d850)
class Original(OriginalV10):
    def __init__(self):
        self.events=[];self.randomIndex=0;self.rangeIndex=0;self.realTargetQuery=False
        super().__init__(ROOT/'Original/claw10/CLAW.EXE')
    def hook(self,u,addr,size,user):
        super().hook(u,addr,size,user)
        if addr==0x41d750 and self.realTargetQuery:return
        counts={0x4c79e0:2,0x4c8220:1,0x420a10:2,0x420fc0:1,0x421010:2,0x4dbd20:1,0x4c82a0:1,0x420970:1,0x4f6286:2,0x41d750:4,0x41dc50:4,0x4a3050:0,0x48c8a0:2,0x4c8da0:6,0x4c7970:1,0x41cc60:3}
        if addr not in counts:return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);n=counts[addr];args=self.read_words(sp+4,n)
        result=0;values=[0,0,0];cdecl=addr in (0x41d750,0x4207b0,0x41dc50,0x4a3050,0x48c8a0,0x41cc60)
        if addr in (0x4c79e0,0x420a10):assert receiver==A;values=args+[0]
        elif addr in (0x4c8220,0x420970,0x4c82a0):
            assert receiver==A+0x188;values=args+[0,0]
            if addr==0x4c82a0:result=marker
        elif addr in (0x420fc0,0x4dbd20):assert receiver==WL+0x2f4;values=[W,args[0],0]
        elif addr==0x421010:assert receiver==WL;values=[W]+args
        elif addr==0x4f6286:assert receiver==R+0x10;values=[args[0],0,0];self.write_words(args[1],[0x12345678]);result=0x12345678
        elif addr==0x41d750:
            assert args[:3]==[A,L,P];self.write_words(args[3],[targetToken]);result=distance&0xffffffff
        elif addr==0x4207b0:
            values=args+[0];result=rangeResults[self.rangeIndex%len(rangeResults)];self.rangeIndex+=1
        elif addr==0x41dc50:assert args[:3]==[A,L,P];values=[args[3],0,0];self.write_words(P+4,[liftResult])
        elif addr==0x4a3050:result=randomResults[self.randomIndex%len(randomResults)];self.randomIndex+=1
        elif addr==0x48c8a0:values=args+[0]
        elif addr==0x4c8da0:
            assert receiver==OBJECTS and args[0]==0 and args[5]==0x40000
            values=[args[4],args[1],args[2]];result=projectileToken
            self.spawn=tuple(args[1:])
        elif addr==0x4c7970:assert receiver==PROJECTILE;values=[PROJECTILE,args[0],0]
        elif addr==0x41cc60:assert args==[A,L,P]
        snapshot=tuple(self.read_words(P+4,1)+[self.read_words(A+0x104,1)[0]]+self.read_words(P+20,4))
        self.events.append((addr,*values,snapshot))
        u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if cdecl else n*4))
o=Original();nativeEvents=[];attack=None;randomIndex=rangeIndex=0
marker=0;distance=999999;targetToken=0;projectileToken=0;liftResult=0;rangeResults=[0];randomResults=[0]
@Callback
def dependency(ptr,entry,a,b,c,context):
    global randomIndex,rangeIndex
    s=ptr.contents;result=0
    if entry==0x41d750:attack.targetToken=targetToken;result=distance&0xffffffff
    elif entry==0x41dc50:s.privateWords[1]=liftResult
    elif entry==0x4207b0:result=rangeResults[rangeIndex%len(rangeResults)];rangeIndex+=1
    elif entry==0x4a3050:result=randomResults[randomIndex%len(randomResults)];randomIndex+=1
    elif entry==0x4c8da0:result=projectileToken
    elif entry==0x4c82a0:result=marker
    elif entry==0x4f6286:result=0x12345678
    snapshot=tuple([s.privateWords[1],s.actor[0x104//4]]+list(s.privateWords[5:9]))
    nativeEvents.append((entry,a,b,c,snapshot));return result

def new():
    s=State();t=Attack()
    for i in range(128):s.actor[i]=rng.getrandbits(32);t.targetActor[i]=rng.getrandbits(32);t.projectileActor[i]=rng.getrandbits(32)
    for i in range(78):s.privateWords[i]=rng.getrandbits(32)
    s.actor[0x4c//4]=rng.getrandbits(32);s.actor[0x50//4]=rng.getrandbits(32);s.actor[0xcc//4]=rng.choice([1,2,4,5,6]);s.actor[0x1a4//4]=rng.choice([0,1]);s.actor[0x19c//4]=rng.choice([0,1,9])
    s.logicState=rng.choice([4,8,9,24,25,26,27,5002,5003]);s.privateWords[0]=rng.choice([0,1,2,0xffffffff]);s.privateWords[1]=rng.choice([0,0,0,1]);s.privateWords[12]=rng.choice([0,1,2,3,4,0xffffffff]);s.privateWords[75]=rng.choice([0,W])
    s.weaponLogicStatus=rng.choice([-1,0,1,5]);s.weaponDeleteCount=rng.choice([0,1,32,33,100]);s.weaponDeleteFlags=rng.getrandbits(32);s.weaponLogicCallback=rng.getrandbits(32)
    for i in (28,29,30):s.privateWords[i]=rng.choice([0,1,2,0xffffffff,0x80000000,0x7fffffff])
    for i in (4,7,8):s.privateWords[i]=rng.choice([0,1])
    s.privateWords[64]=rng.choice([0,49,50,51,500,1999,2000,2001,0xffffffff]);s.privateWords[65]=rng.choice([0,50,2000]);s.privateWords[66]=rng.choice([0,50,2000,0xffffffff])
    s.inputHeld=rng.getrandbits(32);s.inputLatched=rng.getrandbits(32);s.stageDelta=rng.choice([0,1,16,33,0xffffffff]);s.animationDelta=rng.choice([0,1,17,80]);s.powerup=rng.choice([0,0x26b8,0x26b9,0x26ba,0x26bb,0x26bc]);s.physics.acceleration[1]=rng.uniform(-9999,9999)
    t.pressed=rng.getrandbits(32);t.difficulty=rng.choice([0,1]);t.damage100=rng.choice([0,0,1]);t.damage0=rng.choice([0,0,1]);t.projectileToken=rng.getrandbits(32);t.targetToken=rng.getrandbits(32);t.projectileLogicRepeat=rng.getrandbits(32);t.projectileActor[0x6c//4]=PROJECTILE_LOGIC
    return s,t

def prepare(s,t):
    o.events=[];o.randomIndex=0;o.rangeIndex=0;o.spawn=None
    o.write_words(A,s.actor);o.write_words(P,s.privateWords);o.write_words(L+0x1c,[s.logicState]);o.write_words(I+4,[t.pressed,s.inputHeld,s.inputLatched]);o.write_words(0x537204,[I]);o.write_words(0x53720c,[s.stageDelta]);o.write_words(0x5430c4,[s.animationDelta]);o.write_words(0x534eac,[s.powerup]);o.write_words(0x53725c,[t.difficulty]);o.write_words(0x537218,[t.damage100]);o.write_words(0x537228,[t.damage0]);o.u.mem_write(0x534db8,bytes(s.physics))
    o.write_words(A+0xc,[SC]);o.write_words(SC+0x2c,[R]);o.write_words(SC+8,[OBJECTS]);o.write_words(W+0x6c,[WC]);o.write_words(WC+0x18,[WL]);o.write_words(WL+0x20,[s.weaponLogicStatus]);o.write_words(WL+0x14,[s.weaponLogicCallback]);o.write_words(WL+0x2fc,[s.weaponDeleteCount]);o.write_words(WL+0x300,[0x100a000 if s.weaponDeleteCount>32 else s.weaponDeleteFlags]);o.write_words(0x100a000,[s.weaponDeleteFlags])
    o.write_words(TARGET,t.targetActor);o.write_words(PROJECTILE,t.projectileActor);o.write_words(PROJECTILE_LOGIC+0xb8,[t.projectileLogicRepeat])

def compare(s,t,entry,case,code=0):
    global attack,randomIndex,rangeIndex
    attack=t;prepare(s,t);before=State.from_buffer_copy(s);nativeEvents.clear();randomIndex=rangeIndex=0
    args=struct.pack('<III',A,L,P)+(struct.pack('<I',code)if entry==0x41de90 else struct.pack('<I',TARGET)if entry==0x41e660 else b'')
    result=o.call(entry,0,args)
    if entry==0x41de90:lib.claw_player_start_attack(C.byref(s),C.byref(t),code,dependency,None)
    elif entry==0x4170f0:lib.claw_player_enter_climb(C.byref(s),dependency,None)
    elif entry==0x417380:lib.claw_player_enter_attack_stand(C.byref(s),dependency,None)
    elif entry==0x41e660:assert result==lib.claw_player_can_lift(C.byref(s),C.byref(t)),(case,'canLift')
    else:
        name={0x41d850:'select_attack',0x41dd80:'select_weapon_attack',0x41c5a0:'update_attack'}[entry]
        actual=getattr(lib,'claw_player_'+name)(C.byref(s),C.byref(t),dependency,None)
        if entry==0x41d850:assert result==actual,(case,'return',result,actual)
    expected=o.read_words(A,128);expected[3]=before.actor[3]
    assert list(s.actor)==expected,(hex(entry),case,'actor',[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(s.actor,expected))if x!=y])
    expected=o.read_words(P,78)
    assert list(s.privateWords)==expected,(hex(entry),case,'private',[(i,hex(x),hex(y))for i,(x,y)in enumerate(zip(s.privateWords,expected))if x!=y])
    assert s.logicState==o.read_words(L+0x1c,1)[0],(case,'logic')
    assert s.inputLatched==o.read_words(I+12,1)[0],(case,'latched')
    assert s.inputHeld==o.read_words(I+8,1)[0] and t.pressed==o.read_words(I+4,1)[0],(case,'input')
    assert bytes(s.physics)==o.u.mem_read(0x534db8,C.sizeof(Physics)),(case,'physics')
    assert s.weaponLogicCallback==o.read_words(WL+0x14,1)[0],(case,'weaponCallback')
    assert s.weaponDeleteFlags==o.read_words(0x100a000 if s.weaponDeleteCount>32 else WL+0x300,1)[0],(case,'weaponDeleteFlags')
    assert list(t.projectileActor)==o.read_words(PROJECTILE,128),(case,'projectile')
    assert t.projectileLogicRepeat==o.read_words(PROJECTILE_LOGIC+0xb8,1)[0],(case,'projectileRepeat')
    assert list(t.targetActor)==o.read_words(TARGET,128),(case,'target')
    assert nativeEvents==o.events,(hex(entry),case,'events',nativeEvents,o.events)
    if o.spawn:assert o.spawn==(t.spawnX,t.spawnY,t.spawnZ,t.spawnName,t.spawnFlags),(case,'spawn',o.spawn,(t.spawnX,t.spawnY,t.spawnZ,t.spawnName,t.spawnFlags))
    assert randomIndex==o.randomIndex and rangeIndex==o.rangeIndex,(case,'rngCount')
