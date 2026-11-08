"""Fingerprint-pinned original audio routing with explicit registry/voice-pool
selection/DirectSound/error-report adapters; no host playback is claimed."""
import ctypes as C
from pathlib import Path
import random, struct, subprocess
from unicorn import UcError, UC_ERR_EXCEPTION, UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/audio-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-ffp-contract=off','-O2','-dynamiclib',str(ROOT/'Sources/AudioEvents.cpp'),'-o',str(WORK/'libAudioEvents.dylib')],check=True)
lib=C.CDLL(str(WORK/'libAudioEvents.dylib'))
class Sound(C.Structure):_fields_=[('resourceToken',C.c_uint32),('voicePoolToken',C.c_uint32)]
class Registry(C.Structure):_fields_=[('token',C.c_uint32),('disabled',C.c_uint32)]
class Routing(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('managerAvailable','masterVolume','defaultReferenceX','sceneWidth','speechActorPresent','speechLogicPresent','speechBusy','playerPresent','playerLogicState','speechRegistryToken','queuedSpeechToken','speechLogicState')]
class Request(C.Structure):_fields_=[(n,C.c_uint32)for n in ('volume','pan','pitchPercent','looping')]
Resolve=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(Sound))
Play=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,Request)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('resolve',Resolve),('play',Play)]
class Voice(C.Structure):_fields_=[('words',C.c_uint32*14)]
class Pool(C.Structure):_fields_=[('token',C.c_uint32),('deviceAvailable',C.c_uint32)]
Select=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32)
DS=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32)
Report=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32)
class Backend(C.Structure):_fields_=[('context',C.c_void_p),('selectVoice',Select),('directSound',DS),('report',Report)]
lib.claw_audio_play_direct.argtypes=[C.POINTER(Routing),C.POINTER(Sound),Request,Host]
lib.claw_audio_play_name.argtypes=[C.POINTER(Routing),Registry,C.c_uint32,Host]
lib.claw_audio_play_spatial.argtypes=[C.POINTER(Routing),C.POINTER(Sound),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,Host,C.POINTER(C.c_uint32)]
lib.claw_audio_queue_speech.argtypes=[C.POINTER(Routing),C.c_uint32,C.c_uint32]
lib.claw_audio_queue_speech_name.argtypes=[C.POINTER(Routing),C.c_uint32,C.c_uint32,Host]
lib.claw_audio_play_pool.argtypes=[Pool,Request,Backend]
lib.claw_audio_volume_table.argtypes=[C.c_uint32];lib.claw_audio_volume_table.restype=C.c_int32
S,POOL,M,SC,CM,WP,VP,VM,SA,SL,PA,PL,REG,VOICE,BUFFER,VT=[0x1000000+i*0x1000 for i in range(16)]
DS_METHODS={0x10f0000:0x3c,0x10f0010:0x40,0x10f0020:0x44,0x10f0030:0x30}
def requestWords(r):return [getattr(r,n)for n,_ in Request._fields_]
class OriginalAudio(OriginalV10):
    def __init__(self):
        self.events=[];self.found=True;self.playReturn=1;self.realPool=False;self.voicePresent=True;self.results={}
        super().__init__(ROOT/'Original/claw10/CLAW.EXE')
        self.call(0x4b3c80,0) # entire original table initialization, math helpers included
        self.fault=0
        self.u.hook_add(UC_HOOK_INTR,self.interrupt)
        self.write_words(BUFFER,[VT]);self.write_words(VT+0x3c,[0x10f0000,0x10f0010,0x10f0020]);self.write_words(VT+0x30,[0x10f0030])
    def interrupt(self,u,number,user):
        assert number==0
        self.fault=1 if u.reg_read(UC_X86_REG_ESI)==0 else 2
        u.emu_stop()
    def hook(self,u,address,size,user):
        super().hook(u,address,size,user)
        if address not in (0x4f6286,0x4b45f0,0x4b4430,0x4b4ed0)and address not in DS_METHODS:return
        if address==0x4b45f0 and self.realPool:return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
        n={0x4f6286:2,0x4b45f0:4,0x4b4430:0,0x4b4ed0:3}.get(address,4 if DS_METHODS.get(address)==0x30 else 2)
        args=self.read_words(sp+4,n);ret=0
        if address==0x4f6286:
            self.events.append(('resolve',receiver,args[0]));self.write_words(args[1],[S if self.found else 0])
        elif address==0x4b45f0:self.events.append(('play',receiver,*args));ret=self.playReturn
        elif address==0x4b4430:self.events.append(('select',receiver));ret=VOICE if self.voicePresent else 0
        elif address==0x4b4ed0:
            assert args[0]==0x53228c;self.events.append(('report',args[1],args[2]))
        else:
            method=DS_METHODS[address];assert args[0]==BUFFER
            self.events.append(('ds',BUFFER,method,*(args[1:]+[0]*(4-len(args)))))
            ret=self.results[method]
        u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address==0x4b4ed0 else n*4))
o=OriginalAudio();nativeEvents=[];rng=random.Random(0x4c88e0)
@Resolve
def resolve(_,registry,name,result):
    nativeEvents.append(('resolve',registry,name));result[0]=Sound(S if o.found else 0,POOL)
@Play
def play(_,pool,request):nativeEvents.append(('play',pool,*requestWords(request)));return o.playReturn
host=Host(None,resolve,play)
sound=Sound(S,POOL)
def prepare(routing):
    o.events=[];nativeEvents.clear();o.fault=0
    o.write_words(0x532c0c,[M if routing.managerAvailable else 0]);o.write_words(0x532c10,[routing.masterVolume])
    o.write_words(S+0xc,[SC,POOL]);o.write_words(SC+0x24,[CM]);o.write_words(CM+0x5c,[WP]);o.write_words(WP+0x84,[routing.defaultReferenceX])
    o.write_words(SC+4,[VP]);o.write_words(VP+0x10,[VM]);o.write_words(VM+0x10,[routing.sceneWidth]);o.write_words(SC+0x28,[REG])
    o.write_words(0x53c9a4,[SA if routing.speechActorPresent else 0]);o.write_words(0x53c9a0,[routing.speechBusy]);o.write_words(0x537e88,[PA if routing.playerPresent else 0])
    actor=[rng.getrandbits(32)for _ in range(128)];actor[3]=SC;actor[0x6c//4]=SL if routing.speechLogicPresent else 0;actor[0x184//4]=routing.queuedSpeechToken
    logic=[rng.getrandbits(32)for _ in range(128)];logic[7]=routing.speechLogicState
    o.write_words(SA,actor);o.write_words(SL,logic);o.write_words(PA+0x6c,[PL]);o.write_words(PL+0x1c,[routing.playerLogicState])
    return actor,logic
def routingState():
    return Routing(rng.choice([0,1]),rng.choice([0,1,50,99,100,0xffffffff,0x80000000,rng.getrandbits(32)]),
        rng.getrandbits(32),rng.choice([0,1,2,3,320,640,1920,0x80000000,0xffffffff]),
        rng.choice([0,1]),rng.choice([0,1]),rng.choice([0,1]),rng.choice([0,1]),rng.choice([0,24,28,5003,5004,5005,5006]),
        REG+0x10,rng.getrandbits(32),rng.getrandbits(32))
def compare(entry,routing,args):
    actor,logic=prepare(routing)
    if entry==0x4208e0:
        expected=o.call(entry,S,struct.pack('<4I',*args));actual=lib.claw_audio_play_direct(C.byref(routing),C.byref(sound),Request(*args),host)
    elif entry==0x420910:
        name,disabled=args;o.write_words(REG+0x30,[disabled]);expected=o.call(entry,REG,struct.pack('<I',name))
        actual=lib.claw_audio_play_name(C.byref(routing),Registry(REG+0x10,disabled),name,host)
    elif entry==0x4c88e0:
        fault=C.c_uint32(0);expectedFault=0
        try:expected=o.call(entry,S,struct.pack('<4I',*args))
        except AssertionError:
            assert o.fault and o.u.reg_read(UC_X86_REG_EIP)==0x4c898c
            expectedFault=o.fault;expected=0
        except UcError as e:
            assert e.errno==UC_ERR_EXCEPTION and o.u.reg_read(UC_X86_REG_EIP)==0x4c898c
            expectedFault=1 # Zero denominator cases selected below; overflow checked separately.
            expected=0
        actual=lib.claw_audio_play_spatial(C.byref(routing),C.byref(sound),*args,host,C.byref(fault));assert fault.value==expectedFault
    else:
        name,force=args
        if entry==0x48c820:
            expected=o.call(entry,0,struct.pack('<II',name,force));actual=lib.claw_audio_queue_speech(C.byref(routing),name,force)
        else:
            expected=o.call(entry,0,struct.pack('<II',name,force));actual=lib.claw_audio_queue_speech_name(C.byref(routing),name,force,host)
    assert expected==actual,(hex(entry),args,expected,actual)
    assert o.events==nativeEvents,(hex(entry),args,o.events,nativeEvents)
    actor[0x184//4]=routing.queuedSpeechToken;logic[7]=routing.speechLogicState
    assert o.read_words(SA,128)==actor and o.read_words(SL,128)==logic
    assert o.read_words(0x532c10,1)==[routing.masterVolume]

for i in range(6000):
    o.found=rng.choice([False,True]);o.playReturn=rng.choice([0,1]);r=routingState()
    entry=[0x4208e0,0x420910,0x4c88e0,0x48c820,0x48c8a0][i%5]
    if entry==0x4208e0:args=[rng.getrandbits(32)for _ in range(4)]
    elif entry==0x420910:args=[rng.getrandbits(32),rng.choice([0,1])]
    elif entry==0x4c88e0:
        r.sceneWidth=rng.choice([320,640,1920])
        args=[rng.getrandbits(32),rng.choice([0,1,0xffffffff,rng.getrandbits(32)]),rng.choice([0,1,160,640,0xffffffff]),rng.choice([0,1,106,320,0xffffffff])]
    else:args=[rng.choice([0,S,rng.getrandbits(32)]),rng.choice([0,1,0xffffffff])]
    compare(entry,r,args)
print('PASS 6,000 direct/name/spatial/queued speech routing calls, complete speech buffers and ordered external arguments',flush=True)

assert [lib.claw_audio_volume_table(i)for i in range(101)]==[struct.unpack('<i',o.u.mem_read(0x541178+i*4,4))[0]for i in range(101)]
print('PASS all 101 volume table entries against complete original table initializer and CRT math',flush=True)
# Spatial volume's float0.01 scaling is not exact integer identity. Registry
# disable gates resolution, but audio disable happens after name resolution.
o.found=True;o.playReturn=1
r=Routing(1,50,100,640,1,1,0,1,24,REG+0x10,0,0)
compare(0x4c88e0,r,[100,100,160,160]);assert nativeEvents==[('play',POOL,49,0,0,0)]
r.managerAvailable=0;compare(0x420910,r,[0x524724,0]);assert nativeEvents==[('resolve',REG+0x10,0x524724)]
compare(0x420910,r,[0x524724,1]);assert nativeEvents==[]
# Speech queue remains independent of master audio availability. Force bypasses
# busy/death gates; it still requires the speech actor's logic pointer.
r.speechBusy=1;r.playerLogicState=5005
compare(0x48c820,r,[S,0]);assert r.queuedSpeechToken==0
compare(0x48c820,r,[S,1]);assert r.queuedSpeechToken==S and r.speechLogicState==1001
r.speechLogicPresent=0;compare(0x48c820,r,[0x12345678,1]);assert r.queuedSpeechToken==S
print('PASS directed spatial rounding, registry/audio disable order, and speech force/death/busy gates',flush=True)
# Each original division fault uses a fresh CPU: stopping on an x86 interrupt
# leaves emulator exception state that must not contaminate later comparisons.
executed=set(o.executed)
for width in(0,1,2):
    o=OriginalAudio();r=Routing(1,100,100,width,0,0,0,0,0,REG+0x10,0,0)
    compare(0x4c88e0,r,[100,100,0,0]);assert o.fault==1
    executed.update(o.executed)
o=OriginalAudio();o.executed.update(executed)
print('PASS original integer divide-by-zero interrupt boundaries with explicit portable fault output',flush=True)

voice=Voice()
@Select
def select(_,pool):nativeEvents.append(('select',pool));return C.addressof(voice)if o.voicePresent else None
@DS
def directSound(_,buffer,method,a,b,c):nativeEvents.append(('ds',buffer,method,a,b,c));return o.results[method]
@Report
def report(_,code,result):nativeEvents.append(('report',code,result))
backend=Backend(None,select,directSound,report)
o.realPool=True
for i in range(5000):
    o.voicePresent=rng.choice([False,True]);available=rng.choice([0,1]);o.results={m:rng.choice([0,0,1,0x80004005,0xffffffff])for m in(0x3c,0x40,0x44,0x30)}
    fields=[rng.getrandbits(32)for _ in range(14)];fields[3]=BUFFER;fields[4]=M
    fields[6]=rng.choice([0,1,100,101,11025,22050,44100,99999,100000,0x80000000,0xffffffff])
    voice.words[:]=fields;o.write_words(VOICE,fields);o.write_words(POOL+0x10,[M]);o.write_words(M+0x78,[available])
    request=Request(rng.randrange(101),rng.randint(-100,100)&0xffffffff,rng.choice([0,1,-1,100,-100,0x80000000,0x7fffffff])&0xffffffff,rng.choice([0,1,0xffffffff]))
    o.events=[];nativeEvents.clear();expected=o.call(0x4b45f0,POOL,struct.pack('<4I',*requestWords(request)))
    actual=lib.claw_audio_play_pool(Pool(POOL,available),request,backend)
    assert expected==actual and list(voice.words)==o.read_words(VOICE,14),(i,'voice/return')
    assert o.events==nativeEvents,(i,o.events,nativeEvents)
print('PASS 5,000 voice dispatches through original setters/play wrapper, DirectSound HRESULT cases, full voice buffers and exact error order',flush=True)
print(f'{len(o.executed)} original instruction addresses; registry, voice selection, DirectSound COM methods, and error reporter adapted explicitly')
