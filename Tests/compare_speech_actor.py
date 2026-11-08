"""Original ClawDialogSound instructions with registry/voice-selection/COM adapters.
Full actor, logic, player, settings, resource and voice buffers are compared.
"""
import ctypes as C
from pathlib import Path
import random, struct, subprocess
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/speech-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-ffp-contract=off','-O2','-dynamiclib',str(ROOT/'Sources/SpeechActor.cpp'),str(ROOT/'Sources/AudioEvents.cpp'),'-o',str(WORK/'libSpeechActor.dylib')],check=True)
lib=C.CDLL(str(WORK/'libSpeechActor.dylib'))
class State(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*128)]
class Context(C.Structure):
    _fields_=[(n,C.c_uint32)for n in('actorToken','imageRegistryToken','registeredActorToken','busy','managerAvailable','speechEnabled','speechVolume','stageDelta','playerPresent','playerX','playerY','playerHeight','playerLayer','playerLogicState','queuedSoundPoolToken','queuedSoundDuration')]
class Image(C.Structure):_fields_=[(n,C.c_uint32)for n in('token','firstIndex','lastIndex','firstFrameToken')]
Resolve=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(Image))
Play=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('resolveImage',Resolve),('play',Play)]
class Request(C.Structure):_fields_=[(n,C.c_uint32)for n in('volume','pan','pitchPercent','looping')]
class Voice(C.Structure):_fields_=[('words',C.c_uint32*14)]
class Pool(C.Structure):_fields_=[('token',C.c_uint32),('deviceAvailable',C.c_uint32)]
Select=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32)
DS=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32)
Report=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32)
class Backend(C.Structure):_fields_=[('context',C.c_void_p),('selectVoice',Select),('directSound',DS),('report',Report)]
class Routing(C.Structure):
    _fields_=[(n,C.c_uint32)for n in('managerAvailable','masterVolume','defaultReferenceX','sceneWidth','speechActorPresent','speechLogicPresent','speechBusy','playerPresent','playerLogicState','speechRegistryToken','queuedSpeechToken','speechLogicState')]
lib.claw_speech_actor_update.argtypes=[C.POINTER(State),C.POINTER(Context),Host]
lib.claw_audio_play_pool.argtypes=[Pool,Request,Backend]
lib.claw_audio_queue_speech.argtypes=[C.POINTER(Routing),C.c_uint32,C.c_uint32]
SA,SL,PA,PL,SC,IR,IM,FR,SO,POOL,M,CFG,VO,BUF,VT=[0x1000000+i*0x1000 for i in range(15)]
METHODS={0x10f0000:0x3c,0x10f0010:0x40,0x10f0020:0x44,0x10f0030:0x30}
MASK=0xffffffff
def packed(*values):return struct.pack('<'+'I'*len(values),*(v&MASK for v in values))
class OriginalSpeech(OriginalV10):
    def __init__(self):
        self.events=[];self.snapshots=[];self.realPlayback=False;self.found=True;self.voicePresent=True;self.playReturn=1;self.results={}
        super().__init__(ROOT/'Original/claw10/CLAW.EXE')
        self.call(0x4b3c80,0)
        self.write_words(BUF,[VT]);self.write_words(VT+0x30,[0x10f0030]);self.write_words(VT+0x3c,[0x10f0000,0x10f0010,0x10f0020])
    def hook(self,u,address,size,user):
        super().hook(u,address,size,user)
        if address not in(0x4f6286,0x4b45f0,0x4b4430,0x4b4ed0)and address not in METHODS:return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
        n={0x4f6286:2,0x4b45f0:4,0x4b4430:0,0x4b4ed0:3}.get(address,4 if METHODS.get(address)==0x30 else 2)
        args=self.read_words(sp+4,n);ret=0
        if address in(0x4f6286,0x4b45f0):
            self.snapshots.append((self.read_words(SA,128),self.read_words(SL,128),self.read_words(0x53c9a0,2)))
        if address==0x4f6286:
            self.events.append(('resolve',receiver,args[0]));self.write_words(args[1],[IM if self.found else 0])
        elif address==0x4b45f0:
            self.events.append(('play',receiver,*args))
            if self.realPlayback:return
            ret=self.playReturn
        elif address==0x4b4430:
            self.events.append(('select',receiver));ret=VO if self.voicePresent else 0
        elif address==0x4b4ed0:
            assert args[0]==0x53228c;self.events.append(('report',args[1],args[2]))
        else:
            method=METHODS[address];assert args[0]==BUF
            self.events.append(('ds',BUF,method,*(args[1:]+[0]*(4-len(args)))))
            ret=self.results[method]
        u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address==0x4b4ed0 else n*4))
o=OriginalSpeech();rng=random.Random(0x48c630);events=[];snapshots=[];image=Image();voice=Voice();deviceAvailable=1
currentState=None;currentContext=None
def snapshot():
    snapshots.append((list(currentState.actor),list(currentState.logic),[currentContext.busy,currentContext.registeredActorToken]))
@Resolve
def resolve(_,registry,name,result):
    snapshot();events.append(('resolve',registry,name));result[0]=image
@Select
def select(_,pool):events.append(('select',pool));return C.addressof(voice)if o.voicePresent else None
@DS
def directSound(_,buffer,method,a,b,c):events.append(('ds',buffer,method,a,b,c));return o.results[method]
@Report
def report(_,code,result):events.append(('report',code,result))
backend=Backend(None,select,directSound,report)
@Play
def play(_,pool,volume,pan,pitch,loop):
    snapshot()
    events.append(('play',pool,volume,pan,pitch,loop))
    return lib.claw_audio_play_pool(Pool(pool,deviceAvailable),Request(volume,pan,pitch,loop),backend)if o.realPlayback else o.playReturn
host=Host(None,resolve,play)
def randWords(n):return [rng.getrandbits(32)for _ in range(n)]
def makeState(logicState):
    s=State();s.actor[:]=randWords(128);s.logic[:]=randWords(128)
    s.actor[3]=SC;s.actor[0x6c//4]=SL;s.actor[0x184//4]=rng.choice([0,SO]);s.logic[7]=logicState
    c=Context(SA,IR+0x10,rng.choice([0,SA,PA]),rng.getrandbits(32),rng.choice([0,1]),rng.choice([0,1]),
        rng.choice([0,1,79,80,99,100,0x7fffffff,0x80000000,0xffffffff,rng.getrandbits(32)]),rng.getrandbits(32),
        rng.choice([0,1]),*randWords(4),rng.choice([0,28,5004,5005,5006,rng.getrandbits(32)]),POOL,rng.getrandbits(32))
    return s,c
def prepare(s,c):
    global image,deviceAvailable
    first=rng.randint(-5,5)&MASK;last=rng.choice([first,0,5,0xfffffffb,0x80000000,0x7fffffff])
    o.found=rng.choice([False,True]);image=Image(IM if o.found else 0,first,last,rng.getrandbits(32))
    actor=list(s.actor);logic=list(s.logic);player=randWords(128);playerLogic=randWords(128);settings=randWords(128);scene=randWords(128);resource=randWords(128);pool=randWords(128);imageWords=randWords(128)
    player[0x6c//4]=PL;player[0x4c//4]=c.playerX;player[0x50//4]=c.playerY;player[0x11c//4]=c.playerHeight;player[0x64//4]=c.playerLayer;playerLogic[7]=c.playerLogicState
    settings[0x118//4]=c.speechEnabled;settings[0x12c//4]=c.speechVolume
    scene[0x10//4]=IR;resource[0x10//4]=POOL;pool[0x10//4]=M;pool[0x28//4]=c.queuedSoundDuration
    imageWords[0x64//4]=first;imageWords[0x68//4]=last;imageWords[0x14//4]=FR
    o.write_words(SA,actor);o.write_words(SL,logic)
    immutable={PA:player,PL:playerLogic,CFG:settings,SC:scene,SO:resource,POOL:pool,IM:imageWords}
    for address,words in immutable.items():o.write_words(address,words)
    offset=first if first<0x80000000 else first-0x100000000
    o.write_words(FR+offset*4,[image.firstFrameToken])
    o.write_words(0x5371fc,[CFG]);o.write_words(0x537e88,[PA if c.playerPresent else 0]);o.write_words(0x53720c,[c.stageDelta]);o.write_words(0x532c0c,[M if c.managerAvailable else 0])
    o.write_words(0x53c9a4,[c.registeredActorToken]);o.write_words(0x53c9a0,[c.busy])
    o.voicePresent=rng.choice([False,True]);deviceAvailable=rng.choice([0,1]);o.write_words(M+0x78,[deviceAvailable])
    o.results={m:rng.choice([0,0,1,0x80004005,0xffffffff])for m in(0x3c,0x40,0x44,0x30)}
    words=randWords(14);words[3]=BUF;words[4]=M;words[6]=rng.choice([11025,22050,44100]);voice.words[:]=words;o.write_words(VO,words)
    return immutable
def compareTick(s,c,immutable=None):
    global currentState,currentContext
    currentState=s;currentContext=c
    o.events=[];o.snapshots=[];events.clear();snapshots.clear();expected=o.call(0x48c630,0,packed(SA))
    actual=lib.claw_speech_actor_update(C.byref(s),C.byref(c),host)
    assert expected==actual==1
    assert list(s.actor)==o.read_words(SA,128),('actor',s.logic[7])
    assert list(s.logic)==o.read_words(SL,128),('logic',s.logic[7])
    assert [c.registeredActorToken,c.busy]==o.read_words(0x53c9a0,2)[::-1]
    assert o.events==events,('events',o.events,events)
    assert o.snapshots==snapshots,'callback-time state ordering'
    assert list(voice.words)==o.read_words(VO,14)
    if immutable:
        for address,words in immutable.items():assert o.read_words(address,128)==words,('unexpected external mutation',hex(address))
    assert o.read_words(0x53720c,1)==[c.stageDelta]
    assert o.read_words(0x537e88,1)==[PA if c.playerPresent else 0]
    assert o.read_words(0x532c0c,1)==[M if c.managerAvailable else 0]
for i in range(8000):
    s,c=makeState(rng.choice([0,5,15,29,1001,1,4,6,28,1000,1002,0x80000000,0xffffffff,rng.getrandbits(32)]))
    compareTick(s,c,prepare(s,c))
print('PASS 8,000 full speech actor/logic and external buffer comparisons; exact image/play event arguments',flush=True)

# Queue calls are the actual original 0x48c820 and the already recovered native
# AudioEvents helper. Keep the actor and globals synchronized between ticks.
def queue(s,c,sound,force):
    routing=Routing(c.managerAvailable,100,0,640,c.registeredActorToken!=0,1,c.busy,c.playerPresent,c.playerLogicState,0,s.actor[0x184//4],s.logic[7])
    expected=o.call(0x48c820,0,packed(sound,force));actual=lib.claw_audio_queue_speech(C.byref(routing),sound,force)
    s.actor[0x184//4]=routing.queuedSpeechToken;s.logic[7]=routing.speechLogicState
    assert expected==actual and list(s.actor)==o.read_words(SA,128)and list(s.logic)==o.read_words(SL,128)
    return actual
o.realPlayback=True
ticks=0;queueCalls=0
for i in range(1600):
    s,c=makeState(0);c.speechEnabled=1;c.speechVolume=rng.randrange(101);c.playerPresent=1;c.playerLogicState=24;c.queuedSoundDuration=rng.choice([0,1,16,33,500,1000,0xffffffff])
    immutable=prepare(s,c);compareTick(s,c,immutable);ticks+=1
    compareTick(s,c,immutable);ticks+=1 # Idle clears any inherited busy flag.
    assert queue(s,c,SO,0)==1;queueCalls+=1
    compareTick(s,c,immutable);ticks+=1 # Starts sound, state15; no busy write yet.
    assert s.logic[7]==15 and c.busy==0
    assert queue(s,c,SO,0)==1;queueCalls+=1 # Original accepts replacement in this gap.
    compareTick(s,c,immutable);ticks+=1
    c.stageDelta=0;o.write_words(0x53720c,[0]);compareTick(s,c,immutable);ticks+=1
    assert c.busy==1
    if s.logic[7]==15:
        assert queue(s,c,SO,0)==0;queueCalls+=1
        if i%3==0:
            assert queue(s,c,SO,1)==1;queueCalls+=1
            compareTick(s,c,immutable);ticks+=1
        for dt in(1,16,33,1000,0xffffffff):
            c.stageDelta=dt;o.write_words(0x53720c,[dt]);compareTick(s,c,immutable);ticks+=1
            if s.logic[7]==5:break
    assert s.logic[7]==5 and s.actor[0x184//4]==0
    assert c.busy==1 and not(s.actor[0x40//4]&1) # Clear is delayed until state5.
    compareTick(s,c,immutable);ticks+=1;assert c.busy==0 and s.actor[0x40//4]&1
    s.logic[7]=29;o.write_words(SL+0x1c,[29]);compareTick(s,c,immutable);ticks+=1;assert c.registeredActorToken==0
print(f'PASS 1,600 initialization/queue/play/follow/expiry/delete chains: {ticks:,} ticks, {queueCalls:,} original/native queue calls, real original voice setters and COM failure ordering',flush=True)

# Directed cancellation/freeze, signed volume wrap and missing-image retention.
o.realPlayback=False
for death in(28,5004,5005):
    s,c=makeState(15);c.playerPresent=1;c.playerLogicState=death;c.stageDelta=0;s.logic[0x130//4]=100
    compareTick(s,c,prepare(s,c));assert s.logic[7]==(15 if death==28 else 5)
    if death!=28:assert s.actor[0x184//4]==0 and c.busy==1
    s,c=makeState(5);c.registeredActorToken=SA;c.busy=0;c.playerPresent=1;c.playerLogicState=death
    prepare(s,c);assert queue(s,c,SO,0)==0;assert queue(s,c,SO,1)==1
for playerPresent in(0,1):
    s,c=makeState(15);c.playerPresent=playerPresent;c.stageDelta=0xffffffff;s.logic[0x130//4]=100
    compareTick(s,c,prepare(s,c));assert s.logic[7]==(5 if playerPresent else 15)
for volume in(0,79,80,100,0x7fffffff,0x80000000,0xffffffec,0xffffffff):
    s,c=makeState(1001);s.actor[0x184//4]=SO;c.speechEnabled=1;c.speechVolume=volume;c.managerAvailable=1
    compareTick(s,c,prepare(s,c));assert events and events[0][0]=='play'
for enabled,manager in((0,1),(1,0)):
    s,c=makeState(1001);s.actor[0x184//4]=SO;c.speechEnabled=enabled;c.managerAvailable=manager
    compareTick(s,c,prepare(s,c));assert not events and s.logic[7]==(15 if enabled else 5)
s,c=makeState(0);immutable=prepare(s,c);o.found=False;image.token=0
oldIndex=s.actor[0x16c//4];oldFrame=s.actor[0x174//4];compareTick(s,c,immutable)
assert s.actor[0x170//4]==0 and s.actor[0x16c//4]==oldIndex and s.actor[0x174//4]==oldFrame
print('PASS directed death28/5004/5005 distinction, absent-player freeze, signed volume wrap, disable gates, missing-image retention',flush=True)
print(f'{len(o.executed)} original instruction addresses; only registry resolution, voice selection, DirectSound COM, error reporting adapted in playback chains')
