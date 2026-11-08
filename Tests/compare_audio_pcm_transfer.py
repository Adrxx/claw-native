"""Complete original sound/file/load/PCM-transfer/teardown comparisons."""
import ctypes as C
from pathlib import Path
import hashlib,json,random,struct,subprocess
from audio_pcm_original import *
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/audio-pcm-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-ffp-contract=off','-O2','-dynamiclib',str(ROOT/'Sources/AudioPCMTransfer.cpp'),str(ROOT/'Sources/AudioResourceRuntime.cpp'),'-o',str(WORK/'libAudioPCMTransfer.dylib')],check=True)
lib=C.CDLL(str(WORK/'libAudioPCMTransfer.dylib'))
class ResourceContext(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','deviceToken','deviceAvailable','resourceHead','resourceTail')]
class Context(C.Structure):_fields_=[('resource',ResourceContext),('fadeHead',C.c_uint32),('fadeTail',C.c_uint32)]
class Regions(C.Structure):_fields_=[(n,C.c_uint32)for n in('firstToken','firstBytes','secondToken','secondBytes')]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
Create=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32,C.POINTER(C.c_uint32))
Duplicate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32))
Get=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32))
Set=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32);Report=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32)
class ResourceHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('createBuffer',Create),('duplicateBuffer',Duplicate),('get',Get),('set',Set),('report',Report)]
LookupBytes=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32)
Seek=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32)
Read=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32)
Retry=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
Lock=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Regions))
Unlock=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,Regions);Release=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
class Host(C.Structure):_fields_=[('resource',ResourceHost),('lookupBytes',LookupBytes),('free',Free),('seek',Seek),('read',Read),('retry',Retry),('lock',Lock),('unlock',Unlock),('release',Release)]
P=C.POINTER(Context);F=C.POINTER(C.c_uint32)
lib.claw_audio_read_file.argtypes=[Host,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,F]
lib.claw_audio_acquire_file.argtypes=[Host,C.c_uint32,F];lib.claw_audio_release_file.argtypes=[Host,C.c_uint32,F]
lib.claw_audio_transfer_pcm.argtypes=[P,C.c_uint32,C.c_uint32,C.c_uint32,Host,F]
lib.claw_audio_load_pcm.argtypes=[P,C.c_uint32,C.c_uint32,Host,F]
lib.claw_audio_destroy_resource.argtypes=[P,C.c_uint32,Host,F];lib.claw_audio_destroy_resource.restype=None
lib.claw_audio_load_sound.argtypes=[P,C.c_uint32,C.c_uint32,Host,F]
lib.claw_audio_unload_sound.argtypes=[P,C.c_uint32,Host,F];lib.claw_audio_unload_sound.restype=None
o=OriginalPCM(ROOT/'Original/claw10/CLAW.EXE');rng=random.Random(0x4b44f0)
objects={};spans={};events=[];freed=[];indices={};currentContext=None;manager=[]
snapshots=[]
class ObservedEvents(list):
    def append(self,event):
        super().append(event)
        m=list(manager)
        if currentContext is not None:
            c=currentContext;m[1:5]=[c.resource.resourceHead,c.resource.resourceTail,c.fadeHead,c.fadeTail]
        pcm=(C.string_at(lookupBytes(None,event[2],event[3]),event[3])if event[3]else b'',C.string_at(lookupBytes(None,event[4],event[5]),event[5])if event[5]else b'')if event[0]=='unlock'else None
        snapshots.append(({token:list(array)for token,array in objects.items()},m,pcm))
events=ObservedEvents()
def addObject(token,words):objects[token]=(C.c_uint32*len(words))(*words);o.write_words(token,words);o.objects[token]=True
def addSpan(token,data):spans[token]=(C.c_uint8*len(data)).from_buffer_copy(data);o.u.mem_write(token,data);o.byteSpans[token]=len(data)
@Lookup
def lookup(_,token):return C.addressof(objects[token])if token in objects else None
@LookupBytes
def lookupBytes(_,token,size):
    for base,array in spans.items():
        if base<=token and token+size<=base+len(array):return C.addressof(array)+(token-base)
    return None
@Allocate
def allocate(_,size):
    events.append(('allocate',size));index=indices['allocate'];indices['allocate']+=1
    token,expected,contents,kind=o.allocPlan[index];assert size==expected
    if token:
        if kind=='object':objects[token]=(C.c_uint32*14)(*contents)
        else:spans[token]=(C.c_uint8*len(contents)).from_buffer_copy(contents)
    return token
@Create
def create(_,device,fmt,count,out):events.append(('create',device,C.string_at(fmt,18),count));out[0]=o.createdBuffer;return o.createResult
@Duplicate
def duplicate(_,device,source,out):raise AssertionError('No duplicate service expected in PCM loading/teardown')
@Get
def get(_,buffer,method,out):events.append(('get',buffer,method));out[0]=o.values[method];return o.getResults.get(method,0)
@Set
def setParameter(_,buffer,method,value):raise AssertionError('No setter expected in PCM loading/teardown')
@Report
def report(_,line,result):events.append(('report',line,result))
@Free
def free(_,token):events.append(('free',token));freed.append(token)
def nextResult(kind,default):
    index=indices[kind];indices[kind]+=1;values=getattr(o,kind+'Results');return values[index]if index<len(values)else default
@Seek
def seek(_,handle,offset,whence):events.append(('seek',handle,offset,whence));return nextResult('seek',0)
@Read
def read(_,destination,itemBytes,count,handle):
    events.append(('read',destination,itemBytes,count,handle));actual=nextResult('read',count)
    if actual:C.memmove(lookupBytes(None,destination,actual),o.fileData[:actual],actual)
    return actual
@Retry
def retry(_,stream):
    events.append(('retry',stream));result=nextResult('retry',0)
    if result:objects[stream][3]=(objects[stream][3]+1)&MASK
    return result
@Lock
def lock(_,buffer,offset,count,flags,out):events.append(('lock',buffer,offset,count,flags));out[0]=Regions(*o.regions);return o.lockResult
@Unlock
def unlock(_,buffer,regions):events.append(('unlock',buffer,regions.firstToken,regions.firstBytes,regions.secondToken,regions.secondBytes));return o.unlockResult
@Release
def release(_,buffer):events.append(('release',buffer));return 1
host=Host(ResourceHost(None,lookup,allocate,create,duplicate,get,setParameter,report),lookupBytes,free,seek,read,retry,lock,unlock,release)
def randWords(n=14):return [rng.getrandbits(32)for _ in range(n)]
def fixture(pcmBytes=0):
    fmt=struct.pack('<HHIIHH',1,rng.choice([1,2]),22050,rng.choice([22050,44100,88200]),rng.choice([1,2,4]),rng.choice([8,16]))
    samples=bytes(rng.randrange(256)for _ in range(pcmBytes))
    body=b'WAVE'+b'fmt '+struct.pack('<I',len(fmt))+fmt+b'data'+struct.pack('<I',len(samples))+samples+(b'\0'if pcmBytes&1 else b'')
    return b'RIFF'+struct.pack('<I',len(body))+body,samples
def prepare(pcmBytes=100):
    global manager,currentContext
    objects.clear();spans.clear();o.objects={};o.byteSpans={};o.events=[];o.frees=[];events.clear();freed.clear()
    indices.update(allocate=0,seek=0,read=0,retry=0);o.allocIndex=o.seekIndex=o.readIndex=o.retryIndex=0
    manager=randWords(32);manager[1:5]=[0,0,0,0];manager[0x14//4]=DEVICE;manager[0x78//4]=rng.choice([0,1]);o.write_words(M,manager)
    c=Context(ResourceContext(M,DEVICE,manager[0x78//4],0,0),0,0);currentContext=c
    sound=randWords();sound[3]=SCENE;sound[4]=0;scene=randWords();scene[8]=rng.choice([0,M])
    file=randWords();file[5]=0;file[6]=0;file[9]=ARCHIVE;file[10]=0x12340000
    archive=randWords();archive[3]=file[10];archive[6]=STREAM;archive[8]=0
    stream=randWords();stream[0]=STREAMVT;stream[3]=0x60000001
    for token,data in((SOUND,sound),(SCENE,scene),(FILE,file),(ARCHIVE,archive),(STREAM,stream)):addObject(token,data)
    wav,pcm=fixture(pcmBytes);file[5]=len(wav);objects[FILE][5]=len(wav);o.write_words(FILE+0x14,[len(wav)])
    addSpan(SOURCE,wav);addSpan(FIRST,bytes(rng.randrange(256)for _ in range(4096)));addSpan(SECOND,bytes(rng.randrange(256)for _ in range(4096)))
    o.fileData=wav;o.allocPlan=[];o.createResult=rng.choice([0,0,1,0x80004005]);o.createdBuffer=rng.choice([0,BUF])
    o.getResults={m:rng.choice([0,0,1,0x80004005])for m in(0x20,0x1c,0x18)}
    o.values={0x20:rng.choice([11025,22050,44100]),0x1c:rng.getrandbits(32),0x18:rng.getrandbits(32)}
    o.seekResults=[];o.readResults=[];o.retryResults=[];o.lockResult=rng.choice([0,0,1,0x80004005]);o.unlockResult=rng.choice([0,0,1,0x80004005])
    split=rng.randrange(pcmBytes+1);o.regions=[FIRST,split,SECOND,pcmBytes-split]
    return c,wav,pcm
def putWord(token,index,value):objects[token][index]=value;o.write_words(token+4*index,[value])
def enable(c):c.resource.deviceAvailable=1;manager[0x78//4]=1;o.write_words(M+0x78,[1]);putWord(SCENE,8,M)
def poolFixture(token,voiceCount=0,resourceNext=0,resourcePrev=0):
    pool=randWords();pool[0]=0x51350c;pool[1]=resourceNext;pool[2]=resourcePrev;pool[3]=BUF;pool[4]=M;pool[12]=pool[13]=0
    voices=[token+0x100+i*0x100 for i in range(voiceCount)]
    for i,v in enumerate(voices):
        words=randWords();words[0]=0x513510;words[1]=voices[i+1]+4 if i+1<voiceCount else 0;words[2]=voices[i-1]+4 if i else 0;words[3]=BUF+4*(i+1);words[4]=M;words[13]=token;addObject(v,words)
    if voices:pool[12]=voices[0]+4;pool[13]=voices[-1]+4
    addObject(token,pool)
def linkResources(c,tokens):
    c.resource.resourceHead=tokens[0]+4 if tokens else 0;c.resource.resourceTail=tokens[-1]+4 if tokens else 0
    o.write_words(M+4,[c.resource.resourceHead,c.resource.resourceTail])
    for i,t in enumerate(tokens):putWord(t,1,tokens[i+1]+4 if i+1<len(tokens)else 0);putWord(t,2,tokens[i-1]+4 if i else 0)
def addFades(c,targets):
    tokens=[0x1060000+i*0x100 for i in range(len(targets))]
    for i,token in enumerate(tokens):
        words=randWords();words[0]=0x513520;words[1]=tokens[i+1]+4 if i+1<len(tokens)else 0;words[2]=tokens[i-1]+4 if i else 0;words[4]=targets[i];addObject(token,words)
    c.fadeHead=tokens[0]+4 if tokens else 0;c.fadeTail=tokens[-1]+4 if tokens else 0;o.write_words(M+0xc,[c.fadeHead,c.fadeTail])
def compare(entry,c,args=(),sourceBytes=0):
    o.events=[];o.snapshots=[];o.frees=[];events.clear();snapshots.clear();freed.clear();indices.update(allocate=0,seek=0,read=0,retry=0)
    o.allocIndex=o.seekIndex=o.readIndex=o.retryIndex=0
    receiver={0x4b7ab0:STREAM,0x4b61c0:FILE,0x4b6230:FILE,0x4b4a20:M,0x4c8850:SOUND,0x4c88b0:SOUND,0x4b4ae0:M}.get(entry,args[0]if args else 0)
    originalArgs=args[1:]if entry==0x4b44f0 else args
    expected=o.call(entry,receiver,packed(*originalArgs));fault=C.c_uint32(0)
    if entry==0x4b7ab0:actual=lib.claw_audio_read_file(host,STREAM,*args,C.byref(fault))
    elif entry==0x4b61c0:actual=lib.claw_audio_acquire_file(host,FILE,C.byref(fault))
    elif entry==0x4b6230:actual=lib.claw_audio_release_file(host,FILE,C.byref(fault))
    elif entry==0x4b44f0:actual=lib.claw_audio_transfer_pcm(C.byref(c),*args,host,C.byref(fault))
    elif entry==0x4b4a20:actual=lib.claw_audio_load_pcm(C.byref(c),args[0],sourceBytes,host,C.byref(fault))
    elif entry==0x4c8850:actual=lib.claw_audio_load_sound(C.byref(c),SOUND,FILE,host,C.byref(fault))
    elif entry==0x4b4ae0:lib.claw_audio_destroy_resource(C.byref(c),args[0],host,C.byref(fault));actual=expected
    else:lib.claw_audio_unload_sound(C.byref(c),SOUND,host,C.byref(fault));actual=expected
    assert not fault.value,(hex(entry),'fault',fault.value)
    assert expected==actual,(hex(entry),'return',expected,actual)
    assert o.events==events,(hex(entry),'events',o.events,events)
    assert o.snapshots==snapshots,(hex(entry),'callback-time object/list changes')
    assert o.frees==freed
    assert o.objects.keys()==objects.keys()
    for token,array in objects.items():assert list(array)==o.read_words(token,len(array)),(hex(entry),'object',hex(token))
    assert o.byteSpans.keys()==spans.keys()
    for token,array in spans.items():assert bytes(array)==bytes(o.u.mem_read(token,len(array))),(hex(entry),'PCM/source/file bytes',hex(token))
    manager[1:5]=[c.resource.resourceHead,c.resource.resourceTail,c.fadeHead,c.fadeTail]
    assert manager==o.read_words(M,32),'manager lists/private fields'
    assert o.read_words(TEB,1)==[0xdeadbeef],'SEH chain restored'
    return actual
for i in range(2000):
    c,wav,pcm=prepare(rng.randrange(1025));putWord(ARCHIVE,8,rng.choice([0,SOURCE]));cached=rng.choice([0,CACHE]);putWord(FILE,6,cached)
    if cached:addSpan(CACHE,wav)
    if i%7==0:putWord(FILE,5,0)
    o.allocPlan=[(rng.choice([0,CACHE]),len(wav),bytes(rng.randrange(256)for _ in range(len(wav))),'bytes')]
    o.seekResults=rng.choice([[],[1],[1,1,0]]);o.readResults=rng.choice([[],[0],[len(wav)//2,len(wav)]]);o.retryResults=rng.choice([[],[0],[1,1,1,0]])
    compare(0x4b61c0,c);compare(0x4b6230,c)
print('PASS 2,000 complete file acquire/release pairs: mapped/cache/allocation/read/retry/free gates',flush=True)
for i in range(2000):
    c,wav,pcm=prepare(rng.randrange(1025));count=len(wav);addSpan(CACHE,bytes(count));o.seekResults=rng.choice([[],[1],[1,1,0]]);o.readResults=rng.choice([[],[0],[count//2,count]]);o.retryResults=rng.choice([[],[0],[1,1,1,0]])
    compare(0x4b7ab0,c,(0x12340000,count if i%11 else 0,CACHE))
print('PASS 2,000 direct file reads: complete bytes/stream fields, repeated seek versus repeated full-read ordering',flush=True)
for i in range(3000):
    c,wav,pcm=prepare(rng.randrange(1025));poolFixture(0x1010000);compare(0x4b44f0,c,(0x1010000,SOURCE+44,len(pcm)))
print('PASS 3,000 PCM transfers: one/two/zero spans, word/tail-byte copies, HRESULT/report and Unlock ordering',flush=True)
for i in range(2000):
    c,wav,pcm=prepare(rng.randrange(1,1025));enable(c)
    for token in(0x1010000,0x1030000):poolFixture(token)
    linkResources(c,[0x1010000,0x1030000]);o.allocPlan=[(0x1050000,56,randWords(),'object')]
    if i%9==0:
        invalid=b'NOPE'+wav[4:];addSpan(SOURCE,invalid)
    compare(0x4b4a20,c,(SOURCE,0),len(wav))
print('PASS 2,000 complete manager parse/create/transfer/failure-cleanup wrappers; frozen metadata routines execute unchanged',flush=True)
for i in range(2000):
    c,wav,pcm=prepare(rng.randrange(1,1025));poolFixture(0x1010000);linkResources(c,[0x1010000]);putWord(SOUND,4,0x1010000)
    mapped=rng.choice([False,True]);cached=rng.choice([False,True])
    if mapped:putWord(ARCHIVE,8,SOURCE)
    if cached:putWord(FILE,6,CACHE);addSpan(CACHE,wav)
    o.allocPlan=[]
    if not mapped and not cached:o.allocPlan.append((rng.choice([0,CACHE]),len(wav),bytes(len(wav)),'bytes'))
    o.allocPlan.append((0x1050000,56,randWords(),'object'))
    o.seekResults=rng.choice([[],[1]]);o.readResults=rng.choice([[],[0]]);o.retryResults=[]
    compare(0x4c8850,c,(FILE,))
    compare(0x4c88b0,c)
print('PASS 2,000 complete sound load/unload pairs: old-pool retention/overwrite, file cache release, device/manager gates',flush=True)
for i in range(1500):
    c,wav,pcm=prepare();count=rng.randrange(9);poolFixture(0x1010000,count);poolFixture(0x1030000);linkResources(c,rng.choice([[0x1010000,0x1030000],[0x1030000,0x1010000]]))
    addFades(c,[rng.choice([0x1010000,0x1030000,0xabcdef01])for _ in range(rng.randrange(10))])
    compare(0x4b4ae0,c,(0x1010000,))
print('PASS 1,500 complete resource teardowns: fade matching/free order, pool and voice Release, list removals and destructor buffers',flush=True)
# Directed distinction: a missing scene manager retains old sound ownership;
# an existing but disabled manager clears it after processing available bytes.
for present,available in((0,0),(0,1),(1,0),(1,1)):
    c,wav,pcm=prepare(33);c.resource.deviceAvailable=available;manager[0x78//4]=available;o.write_words(M+0x78,[available]);putWord(SCENE,8,M if present else 0)
    poolFixture(0x1010000);linkResources(c,[0x1010000]);putWord(SOUND,4,0x1010000);putWord(ARCHIVE,8,SOURCE)
    o.createResult=0;o.createdBuffer=BUF;o.lockResult=0;o.unlockResult=0;o.allocPlan=[(0x1050000,56,randWords(),'object')]
    result=compare(0x4c8850,c,(FILE,))
    assert objects[SOUND][4]==(0x1010000 if not present else 0x1050000 if available else 0)
    assert result==bool(present and available)
    compare(0x4c88b0,c)
    assert objects[SOUND][4]==(0 if present else 0x1010000)
# Existing cached bytes are released even when archive mapping wins acquisition.
c,wav,pcm=prepare(35);enable(c);putWord(ARCHIVE,8,SOURCE);putWord(FILE,6,CACHE);addSpan(CACHE,wav)
o.createResult=0;o.createdBuffer=BUF;o.lockResult=0;o.unlockResult=1;o.allocPlan=[(0x1050000,56,randWords(),'object')]
assert compare(0x4c8850,c,(FILE,))==0
assert freed[-1]==CACHE and bytes(spans[FIRST])[:o.regions[1]]==pcm[:o.regions[1]]
assert ('report',0x213,1)in events and ('release',BUF)in events
for available in(0,1):
    c,wav,pcm=prepare();poolFixture(0x1010000,3);linkResources(c,[0x1010000]);putWord(SOUND,4,0x1010000);putWord(SCENE,8,M)
    c.resource.deviceAvailable=available;manager[0x78//4]=available;o.write_words(M+0x78,[available])
    compare(0x4c88b0,c);assert objects[SOUND][4]==0
    assert bool(freed)==bool(available) and bool(c.resource.resourceHead)==(not bool(available))
print('PASS callback-time full object/list snapshots and directed manager/device, stale-cache and copied-before-Unlock-failure behavior',flush=True)
# Actual original-disc payloads supplied by the parent's immutable REZ extract.
# Cover each observed format, plus player footsteps/landing/voice/weapon events.
disc=ROOT/'Original/claw-disc/files/DATA/CLAW.REZ'
with disc.open('rb')as f:discHash=hashlib.file_digest(f,'sha256').hexdigest()
assert discHash=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
assetRoot=ROOT/'work/original-disc-assets'
names=['CLAW/SOUNDS/LAND.WAV','CLAW/SOUNDS/1054.WAV','CLAW/SOUNDS/1110035.WAV','CLAW/SOUNDS/LEFTFOOT1.WAV','CLAW/SOUNDS/DRYGUNSHOT1.WAV',
    'STATES/MENU/SOUNDS/CLAW/RIGHTFOOT1.WAV','GAME/SOUNDS/HIT4.WAV','GAME/SOUNDS/MLF.WAV','LEVEL1/SOUNDS/TRIGGER/WDOORCLOS1.WAV',
    'LEVEL1/SOUNDS/OFFICER/OFCSWSTB8-22.WAV','STATES/BOOTY/SOUNDS/PERFECT.WAV','CLAW/SOUNDS/NULL.WAV']
RS,RF,RB,RC=0x3000000,0x3100000,0x3200000,0x3300000
for address in(RS,RF,RB,RC):o.u.mem_map(address,0x100000)
realCases=0;manifest=[];formats=set()
for name in names:
    wav=(assetRoot/name).read_bytes();cursor=12;fmt=None
    while cursor+8<=len(wav):
        tag,size=struct.unpack_from('<4sI',wav,cursor);cursor+=8
        if tag==b'fmt ':fmt=struct.unpack_from('<HHIIHH',wav,cursor)
        if tag==b'data':dataOffset=cursor;pcm=wav[cursor:cursor+size];assert len(pcm)==size;break
        cursor+=(size+1)&~1
    assert fmt and fmt[0]==1;formats.add(fmt)
    duration=((len(pcm)*1000)&MASK)//fmt[3]
    manifest.append(dict(path=name,wav_sha256=hashlib.sha256(wav).hexdigest(),pcm_sha256=hashlib.sha256(pcm).hexdigest(),format=list(fmt),pcm_bytes=len(pcm),duration_ms=duration))
    for soundLoad in(False,True):
        for split in(0,len(pcm)//3,len(pcm)):
            for unlockFails in(False,True):
                c,_,_=prepare(1);enable(c);o.createResult=0;o.createdBuffer=BUF;o.lockResult=0;o.unlockResult=int(unlockFails)
                o.values={0x20:fmt[2],0x1c:0,0x18:0};o.getResults={};o.regions=[RF,split,RB,len(pcm)-split]
                addSpan(RS,wav);addSpan(RF,bytes([0x71])*(len(pcm)+32));addSpan(RB,bytes([0x93])*(len(pcm)+32));o.fileData=wav
                putWord(FILE,5,len(wav));o.allocPlan=[(0x1050000,56,randWords(),'object')]
                if soundLoad:
                    # Alternate actual mapped and cached-file acquisition.
                    if(realCases//2)%2:putWord(FILE,6,RC);addSpan(RC,wav)
                    else:putWord(ARCHIVE,8,RS)
                    result=compare(0x4c8850,c,(FILE,))
                    assert result==int(not unlockFails)
                else:
                    result=compare(0x4b4a20,c,(RS,0),len(wav));assert result==(0 if unlockFails else 0x1050000)
                assert objects[0x1050000][10]==duration and objects[0x1050000][11]==len(pcm)
                assert bytes(spans[RF])[:split]==pcm[:split] and bytes(spans[RB])[:len(pcm)-split]==pcm[split:]
                if soundLoad and not unlockFails:compare(0x4c88b0,c)
                elif not soundLoad and not unlockFails:compare(0x4b4ae0,c,(result,))
                realCases+=1
assert len(formats)==7
(WORK/'original-disc-pcm-cases.json').write_text(json.dumps(dict(rez_sha256=discHash,wav_files=manifest,load_cases=realCases),indent=2)+'\n')
print(f'PASS {realCases} actual-disc manager/sound load cases: 12 complete WAV payloads, all 7 observed PCM formats, exact bytes/duration, split locks, Unlock failure and teardown',flush=True)
print(f'{len(o.executed)} original instruction addresses; allocator/free, initialized Windows FS/SEH, file seek/read/retry and DirectSound/report adapted explicitly')
