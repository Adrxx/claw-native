"""Original v1.0 state transitions; external dependencies are recorded, not proven."""
import ctypes as C
import pathlib, random, struct, subprocess, sys, zlib
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from original_v10 import OriginalV10
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=ROOT/'work/player-agent'
WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-dynamiclib','-ffp-contract=off',
    str(ROOT/'Sources/PlayerLocomotion.cpp'),str(ROOT/'Sources/PlayerEngine.cpp'),
    str(ROOT/'Sources/PlayerPhysics.cpp'),str(ROOT/'Sources/CollisionResponse.cpp'),str(ROOT/'Sources/TileCollision.cpp'),'-o',str(WORK/'libPlayerLocomotion.dylib')],check=True)
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
Callback=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p)
lib=C.CDLL(str(WORK/'libPlayerLocomotion.dylib'))
lib.claw_collision_move.argtypes=[C.POINTER(World),C.POINTER(Actor),C.c_uint32,C.c_uint32,C.c_uint32]
lib.claw_collision_move.restype=None
entries={0x4171d0:'enter_stand',0x417dd0:'enter_walk_left',0x417f20:'enter_walk_right',
         0x417590:'enter_jump',0x4183e0:'update_walk_right',0x418790:'update_walk_left',0x41c4e0:'cleanup_move',0x41b630:'update_jump',0x418b40:'update_fall'}
for name in entries.values():
    f=getattr(lib,'claw_player_'+name); f.argtypes=[C.POINTER(State),Callback,C.c_void_p];f.restype=C.c_uint32
lib.claw_player_enter_fall.argtypes=[C.POINTER(State),C.c_uint32,Callback,C.c_void_p]
lib.claw_player_enter_fall.restype=None
A,L,P,SC,M,I,W,WC,WL,R=(0x1000000+x*0x1000 for x in range(10))
rng=random.Random(0x415df0)
class Original(OriginalV10):
    def __init__(self):
        self.events=[]; self.mode=2;self.platform=(0,0);self.realCollision=False
        super().__init__(ROOT/'Original/claw10/CLAW.EXE')
    def hook(self,u,addr,size,user):
        super().hook(u,addr,size,user)
        if addr not in (0x4c79e0,0x420a10,0x4c8220,0x420fc0,0x421010,0x4c82a0,0x4cbb60,0x4dbd20,0x4f6286,0x4061b0,0x41c5a0,0x4208e0,0x4209d0):return
        sp=u.reg_read(UC_X86_REG_ESP); receiver=u.reg_read(UC_X86_REG_ECX)
        n={0x4c79e0:2,0x420a10:2,0x4c8220:1,0x420fc0:1,0x421010:2,
           0x4c82a0:1,0x4cbb60:4,0x4dbd20:1,0x4f6286:2,0x4061b0:1,0x41c5a0:3,0x4208e0:4,0x4209d0:1}[addr]
        args=self.read_words(sp+4,n)
        if addr==0x4c79e0:
            assert receiver==A;values=args+[0]
        elif addr==0x420a10:
            assert receiver==A;values=args+[0]
        elif addr==0x4c8220:
            assert receiver==A+0x188;values=args+[0,0]
        elif addr==0x420fc0:
            assert receiver==WL+0x2f4;values=[W,args[0],0]
        elif addr==0x421010:
            assert receiver==WL;values=[W]+args
        elif addr==0x4c82a0:
            assert receiver==A+0x188;values=args+[0,0]
        elif addr==0x4cbb60:
            assert receiver==M and args[0]==A;values=args[1:]
            if self.realCollision:
                self.events.append((addr,*values));return
            self.write_words(A+0x4c,args[1:3]);self.write_words(A+0xcc,[self.mode])
        elif addr==0x4dbd20:
            assert receiver==WL+0x2f4;values=[W,args[0],0]
        elif addr==0x4f6286:
            assert receiver==R+0x10;values=[args[0],0,0];self.write_words(args[1],[0x12345678])
        elif addr==0x4061b0:
            assert receiver==R;values=args+[0,0]
        elif addr==0x41c5a0:
            assert args==[A,L,P];values=[0,0,0]
        elif addr==0x4208e0:
            assert receiver==0x12345678 and args[1:]==[0,0,0];values=[receiver,args[0],0]
        elif addr==0x4209d0:
            assert receiver==A;values=args+[0,0]
        self.events.append((addr,*values))
        u.reg_write(UC_X86_REG_EAX,0x12345678 if addr in (0x4f6286,0x4061b0) else 0)
        u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0])
        u.reg_write(UC_X86_REG_ESP,sp+4+(0 if addr==0x41c5a0 else n*4))

o=Original()
nativeEvents=[]; collisionMode=2;platform=(0,0);nativeWorld=None
@Callback
def dependency(ptr,entry,a,b,c,context):
    s=ptr.contents
    if entry==0x158:return platform[0]
    if entry==0x15c:return platform[1]
    nativeEvents.append((entry,a,b,c))
    if entry==0x4cbb60:
        if o.realCollision:
            v=Actor()
            fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
            for n,offset in fields.items():setattr(v,n,s.actor[offset//4])
            v.token=1;v.moveRect=Rect(*s.actor[0x118//4:0x128//4]);v.hitRect=Rect(*s.actor[0x128//4:0x138//4])
            lib.claw_collision_move(C.byref(nativeWorld),C.byref(v),a,b,c)
            for n,offset in fields.items():s.actor[offset//4]=getattr(v,n)
            s.actor[0x118//4:0x128//4]=[getattr(v.moveRect,n)for n,_ in Rect._fields_]
            s.actor[0x128//4:0x138//4]=[getattr(v.hitRect,n)for n,_ in Rect._fields_]
        else:s.actor[0x4c//4]=a;s.actor[0x50//4]=b;s.actor[0xcc//4]=collisionMode
    return 0x12345678 if entry in (0x4f6286,0x4061b0) else 0

def prepare(s):
    o.events=[]
    o.write_words(A,s.actor);o.write_words(P,s.privateWords)
    o.write_words(L+0x1c,[s.logicState]);o.write_words(I+0xc,[s.inputLatched])
    o.write_words(I+8,[s.inputHeld]);o.write_words(0x537204,[I]);o.write_words(0x53720c,[s.stageDelta])
    o.write_words(0x5430c4,[s.animationDelta]);o.write_words(0x534eac,[s.powerup]);o.write_words(0x544e8c,[s.pixelScratch])
    o.write_words(0x544e88,[s.pixelScratchY]);o.write_words(0x537220,[s.highJump]);o.write_words(0x532c10,[s.audioPosition])
    o.u.mem_write(0x534db8,bytes(s.physics));o.write_words(A+0xc,[SC]);o.write_words(SC+0x24,[M]);o.write_words(SC+0x2c,[R])
    o.write_words(SC+0x28,[R]);o.write_words(R+0x30,[s.audioRegistryDisabled])
    o.write_words(W+0x6c,[WC]);o.write_words(WC+0x18,[WL]);o.write_words(WL+0x20,[s.weaponLogicStatus]);o.write_words(WL+0x14,[s.weaponLogicCallback])
    o.write_words(W+0x158,platform)
    o.write_words(WL+0x2fc,[s.weaponDeleteCount]);o.write_words(WL+0x300,[0x100a000 if s.weaponDeleteCount>32 else s.weaponDeleteFlags])
    o.write_words(0x100a000,[s.weaponDeleteFlags])

def compare(s,entry,case,skipAnimation=0):
    prepare(s);before=State.from_buffer_copy(s);nativeEvents.clear()
    result=o.call(entry,0,struct.pack('<III',A,L,P)+(struct.pack('<I',skipAnimation)if entry==0x417930 else b''))
    if entry==0x417930:lib.claw_player_enter_fall(C.byref(s),skipAnimation,dependency,None)
    else:
        actualReturn=getattr(lib,'claw_player_'+entries[entry])(C.byref(s),dependency,None)
        if entry==0x4171d0:assert result==actualReturn,(case,'stand return')
    expected=o.read_words(A,128);expected[3]=before.actor[3] # normalize the original scene pointer to the preserved portable token
    actual=list(s.actor)
    assert actual==expected,(hex(entry),case,'actor',[(hex(i*4),hex(x),hex(y)) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    assert list(s.privateWords)==o.read_words(P,78),(hex(entry),case,'private')
    assert s.logicState==o.read_words(L+0x1c,1)[0],(hex(entry),case,'logic')
    assert s.inputLatched==o.read_words(I+0xc,1)[0],(hex(entry),case,'latched')
    assert bytes(s.physics)==o.u.mem_read(0x534db8,C.sizeof(Physics)),(hex(entry),case,'physics',[(i,x,y) for i,(x,y) in enumerate(zip(bytes(s.physics),o.u.mem_read(0x534db8,C.sizeof(Physics)))) if x!=y][:8])
    assert s.pixelScratch==o.read_words(0x544e8c,1)[0],(hex(entry),case,'scratch')
    assert s.pixelScratchY==o.read_words(0x544e88,1)[0],(hex(entry),case,'scratchY')
    assert s.weaponLogicCallback==o.read_words(WL+0x14,1)[0],(hex(entry),case,'weaponCallback')
    assert s.weaponDeleteFlags==o.read_words(0x100a000 if s.weaponDeleteCount>32 else WL+0x300,1)[0],(hex(entry),case,'weaponDeleteFlags')
    assert nativeEvents==o.events,(hex(entry),case,'events',nativeEvents,o.events)
    return before

def new():
    s=State()
    for i in range(128):s.actor[i]=rng.getrandbits(32)
    for i in range(78):s.privateWords[i]=rng.getrandbits(32)
    s.actor[0x4c//4]=rng.randint(-1000,1000)&0xffffffff;s.actor[0x50//4]=rng.randint(-1000,1000)&0xffffffff
    s.actor[0x80//4]=rng.choice([0,W]);s.privateWords[75]=rng.choice([0,W]);s.privateWords[1]=rng.choice([0,1]);s.privateWords[0]=rng.choice([0,1,2,0xffffffff]);s.privateWords[69]=rng.choice([0,1,50,1500])
    s.privateWords[33]=rng.randint(-100,100)&0xffffffff;s.privateWords[15]=rng.choice([0,8,9,10,18,24])
    s.logicState=rng.getrandbits(32);s.inputLatched=rng.getrandbits(32);s.inputHeld=rng.getrandbits(32)
    s.stageDelta=rng.choice([0,1,7,16,33,200]);s.animationDelta=rng.choice([0,1,7,17,80,200]);s.powerup=rng.choice([0,0x26bc]);s.pixelScratch=rng.getrandbits(32)
    s.weaponLogicStatus=rng.choice([-1,0,1,2]);s.weaponLogicCallback=rng.getrandbits(32)
    s.weaponDeleteCount=rng.choice([0,1,32,33,100]);s.weaponDeleteFlags=rng.getrandbits(32)
    s.highJump=rng.choice([0,1]);s.pixelScratchY=rng.getrandbits(32);s.audioRegistryDisabled=rng.choice([0,1]);s.audioPosition=rng.getrandbits(32)
    for name in ('acceleration','velocity','position','minimum','maximum','delta','remainder','maximumDelta','maximumVelocity'):
        array=getattr(s.physics,name)
        for i in range(3):array[i]=rng.uniform(-10,10)
    s.physics.elapsed=rng.uniform(0,10);s.physics.timestep=.016;s.physics.acceleration[1]=2250
    s.physics.minimum[:]=[-2147483647.]*3;s.physics.maximum[:]=[2147483646.]*3
    s.physics.maximumDelta[:]=[32.,32.,2147483646.];s.physics.maximumVelocity[:]=[1000.]*3
    s.physics.stopped=rng.choice([0,0,0,1]);s.physics.unused=rng.getrandbits(32)
    return s

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

if __name__=='__main__':
    for entry in entries:
        for case in range(1000):
            collisionMode=o.mode=rng.choice([1,2,3,4,6,7]);platform=o.platform=(rng.randint(-20,20)&0xffffffff,rng.randint(-20,20)&0xffffffff)
            compare(new(),entry,case)
        print(f'PASS 1000 {entries[entry]} complete actor/private/physics/input/logic buffers and ordered dependency arguments',flush=True)
    for case in range(1000):compare(new(),0x417930,case,case%2)
    print('PASS 1000 enter_fall; skip-animation, weapon/attack cleanup and all fields/arguments agree',flush=True)
    # Directed equal starting state, unequal clocks: preserve the asymmetry.
    for entry,expected in ((0x4183e0,93),(0x418790,69)):
        s=new();s.privateWords[69]=100;s.stageDelta=31;s.animationDelta=7;s.powerup=0
        collisionMode=o.mode=2;compare(s,entry,'unequal-clock');assert s.privateWords[69]==expected
    print('PASS unequal stage/animation clock countdown asymmetry',flush=True)
    nativeWorld=install_world();o.realCollision=True;platform=(0,0)
    seenStates=set();histories=32;steps=240
    for history in range(histories*2):
        if history in (0,histories):nativeWorld=install_world(history>=histories)
        s=State();lib.claw_physics_construct(C.byref(s.physics));s.physics.acceleration[1]=2250
        s.physics.maximumDelta[0]=s.physics.maximumDelta[1]=32;s.physics.maximumVelocity[:]=[1000.]*3
        s.actor[8//4]=0x80;s.actor[0x40//4]=2;s.actor[0x4c//4]=689 if history>=histories else 320;s.actor[0x50//4]=4730 if history>=histories else 451;s.actor[0xdc//4]=s.actor[0xe0//4]=8;s.actor[0xd0//4]=2
        s.stageDelta=s.animationDelta=16;s.audioRegistryDisabled=1
        compare(s,0x4171d0,(history,'initialize'))
        for tick in range(steps):
            s.stageDelta=([16] if history%2==0 else [0,1,7,13,33,80,200])[tick%(1 if history%2==0 else 7)]
            s.animationDelta=([16] if history%3==0 else [1,7,17,33,80])[tick%(1 if history%3==0 else 5)]
            s.inputHeld=(0x2000000 if tick%100<50 else 0x1000000)|(1 if tick%80<30 else 0)
            if tick in(0,100,200):entry=0x417f20 if s.inputHeld&0x2000000 else 0x417dd0
            elif tick in(20,120,220):entry=0x417590
            else:entry={24:0x4171d0,8:0x4183e0,9:0x418790,4:0x41b630,25:0x418b40}.get(s.logicState)
            if entry is None:raise AssertionError(('unhandled chain state',s.logicState))
            compare(s,entry,(history,tick));seenStates.add(s.logicState)
    print(f'PASS {histories*steps} synthetic-map and {histories*steps} CD-rip Level 1 chained movement/physics/collision transitions with full original collision bodies, states {sorted(seenStates)}',flush=True)
    print(f'{len(o.executed)} original instruction addresses. Generated calls stub collision; chained calls execute collision. Animation/weapon/registry/audio/attack dependency bodies are stubbed and explicitly recorded.')
