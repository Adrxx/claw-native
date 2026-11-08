"""Hash-pinned original audio resource metadata and intrusive voice pool.
Only allocator, initialized Windows FS/SEH environment and DirectSound/report
services are adapted. No reference gameplay source or host audio is used.
"""
import ctypes as C
from pathlib import Path
import random, struct, subprocess
from unicorn import UcError, UC_HOOK_INTR, UC_ERR_READ_UNMAPPED, UC_ERR_WRITE_UNMAPPED
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_GDTR, UC_X86_REG_FS, UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_CS
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/audio-resource-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-ffp-contract=off','-O2','-dynamiclib',str(ROOT/'Sources/AudioResourceRuntime.cpp'),'-o',str(WORK/'libAudioResourceRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libAudioResourceRuntime.dylib'))
class Context(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','deviceToken','deviceAvailable','resourceHead','resourceTail')]
class RiffResult(C.Structure):_fields_=[(n,C.c_uint32)for n in('formatOffset','dataOffset','dataBytes')]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32)
Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32)
Create=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32,C.POINTER(C.c_uint32))
Duplicate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32))
Get=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32))
Set=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32)
Report=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_uint32)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('createBuffer',Create),('duplicateBuffer',Duplicate),('get',Get),('set',Set),('report',Report)]
lib.claw_audio_parse_riff.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.POINTER(RiffResult),C.POINTER(C.c_uint32)]
lib.claw_audio_create_resource.argtypes=[C.POINTER(Context),C.POINTER(C.c_uint8),C.c_uint32,Host,C.POINTER(C.c_uint32)]
lib.claw_audio_allocate_voice.argtypes=[C.POINTER(Context),C.c_uint32,C.c_uint32,Host,C.POINTER(C.c_uint32)]
lib.claw_audio_select_voice.argtypes=[C.POINTER(Context),C.c_uint32,Host,C.POINTER(C.c_uint32)]
M,POOL,BUF,VT,DEVICE,DVT,OUT,FMT,RIFF=[0x1000000+i*0x1000 for i in range(9)]
GETS={0x10f0200:0x20,0x10f01c0:0x1c,0x10f0180:0x18,0x10f0240:0x24}
SETS={0x10f03c0:0x3c,0x10f0400:0x40,0x10f0440:0x44}
CREATE,DUP=0x10f0800,0x10f0810
TEB,GDT=0x10ed000,0x10ee000
MASK=0xffffffff;rng=random.Random(0x4b4430)
def packed(*v):return struct.pack('<'+'I'*len(v),*(x&MASK for x in v))
class OriginalAudioResource(OriginalV10):
    def __init__(self):
        self.events=[];self.objects={};self.nativeObjects={};self.allocToken=0;self.allocWords=[]
        self.createResult=0;self.createdBuffer=BUF;self.dupResult=0;self.duplicateOutput=BUF;self.getResults={};self.values={};self.setResults={};self.fault=0
        super().__init__(ROOT/'Original/claw10/CLAW.EXE')
        # Establish a real FS segment base, leaving the null page unmapped so
        # the original's null intrusive nodes produce actual memory faults.
        base=TEB
        self.u.mem_write(GDT+8,struct.pack('<HHBBBB',0xffff,0,0,0x9b,0xcf,0))
        self.u.mem_write(GDT+0x10,struct.pack('<HHBBBB',0xffff,0,0,0x93,0xcf,0))
        self.u.mem_write(GDT+0x18,struct.pack('<HHBBBB',0xffff,base&0xffff,(base>>16)&0xff,0x93,0xcf,(base>>24)&0xff))
        self.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
        for register in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):self.u.reg_write(register,0x10)
        self.u.reg_write(UC_X86_REG_CS,8);self.u.reg_write(UC_X86_REG_FS,0x18)
        self.write_words(TEB,[0xdeadbeef]);self.u.hook_add(UC_HOOK_INTR,self.interrupt)
        for b in range(0x1002000,0x1002100,4):self.write_words(b,[VT])
        self.write_words(DEVICE,[DVT]);self.write_words(DVT+0xc,[CREATE]);self.write_words(DVT+0x14,[DUP])
        for address,method in {**GETS,**SETS}.items():self.write_words(VT+method,[address])
    def interrupt(self,u,number,user):
        assert number==0;self.fault=1;u.emu_stop()
    def hook(self,u,address,size,user):
        super().hook(u,address,size,user)
        if address not in GETS and address not in SETS and address not in(CREATE,DUP,0x4f63ec,0x4b4ed0):return
        sp=u.reg_read(UC_X86_REG_ESP)
        n=2 if address in GETS or address in SETS else {CREATE:4,DUP:3,0x4f63ec:1,0x4b4ed0:3}[address]
        args=self.read_words(sp+4,n);ret=0
        if address in GETS:
            method=GETS[address];self.events.append(('get',args[0],method))
            self.write_words(args[1],[self.values.get((args[0],method),self.values.get(method,0))]);ret=self.getResults.get((args[0],method),self.getResults.get(method,0))
        elif address in SETS:
            method=SETS[address];self.events.append(('set',args[0],method,args[1]));ret=self.setResults.get(method,0)
        elif address==CREATE:
            desc=self.read_words(args[1],5);assert args[0]==DEVICE and args[3]==0
            assert desc[:2]==[20,0xe0]and desc[3]==0
            fmt=bytes(u.mem_read(desc[4],18));self.events.append(('create',DEVICE,fmt,desc[2]))
            self.write_words(args[2],[self.createdBuffer]);ret=self.createResult
        elif address==DUP:
            self.events.append(('duplicate',args[0],args[1]));self.write_words(args[2],[self.duplicateOutput]);ret=self.dupResult
        elif address==0x4f63ec:
            assert args[0]==56;self.events.append(('allocate',args[0]));ret=self.allocToken
            if ret:self.write_words(ret,self.allocWords);self.objects[ret]=True
        else:
            assert args[0]==0x53228c;self.events.append(('report',args[1],args[2]))
        u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in(0x4f63ec,0x4b4ed0)else n*4))
o=OriginalAudioResource();events=[];nativeObjects={}
@Lookup
def lookup(_,token):return C.addressof(nativeObjects[token])if token in nativeObjects else None
@Allocate
def allocate(_,size):
    events.append(('allocate',size))
    if o.allocToken:nativeObjects[o.allocToken]=(C.c_uint32*14)(*o.allocWords)
    return o.allocToken
@Create
def create(_,device,fmt,bytes,out):
    events.append(('create',device,C.string_at(fmt,18),bytes));out[0]=o.createdBuffer;return o.createResult
@Duplicate
def duplicate(_,device,source,out):
    events.append(('duplicate',device,source));out[0]=o.duplicateOutput;return o.dupResult
@Get
def get(_,buffer,method,out):
    events.append(('get',buffer,method));out[0]=o.values.get((buffer,method),o.values.get(method,0));return o.getResults.get((buffer,method),o.getResults.get(method,0))
@Set
def setParameter(_,buffer,method,value):events.append(('set',buffer,method,value));return o.setResults.get(method,0)
@Report
def report(_,line,result):events.append(('report',line,result))
host=Host(None,lookup,allocate,create,duplicate,get,setParameter,report)
def words(n):return [rng.getrandbits(32)for _ in range(n)]
def putObject(token,values):nativeObjects[token]=(C.c_uint32*14)(*values);o.write_words(token,values);o.objects[token]=True
def prepare(count=0):
    nativeObjects.clear();o.objects={};o.events=[];events.clear();o.fault=0
    manager=words(32);manager[0x14//4]=DEVICE;manager[0x78//4]=rng.choice([0,1]);manager[1]=manager[2]=0
    c=Context(M,DEVICE,manager[0x78//4],0,0);o.write_words(M,manager)
    p=words(14);p[3]=BUF;p[4]=M;p[12]=0;p[13]=0;p[6]=rng.choice([11025,22050,44100]);putObject(POOL,p)
    tokens=[0x1010000+i*0x100 for i in range(count)]
    for i,token in enumerate(tokens):
        v=words(14);v[0]=0x513510;v[1]=tokens[i+1]+4 if i+1<count else 0;v[2]=tokens[i-1]+4 if i else 0
        v[3]=BUF+4*(i+1);v[4]=M;v[12]=rng.choice([0,1,0xffffffff]);v[13]=POOL;putObject(token,v)
    if tokens:nativeObjects[POOL][12]=tokens[0]+4;nativeObjects[POOL][13]=tokens[-1]+4;o.write_words(POOL+0x30,[tokens[0]+4,tokens[-1]+4])
    o.allocToken=0x1050000;o.allocWords=words(14)
    o.createResult=rng.choice([0,0,1,0x80004005]);o.createdBuffer=rng.choice([0,BUF]);o.dupResult=rng.choice([0,0,1,0x80004005]);o.duplicateOutput=BUF+0xfc
    o.values={0x20:rng.getrandbits(32),0x1c:rng.getrandbits(32),0x18:rng.getrandbits(32)};o.getResults={m:rng.choice([0,0,1,0x80004005])for m in(0x20,0x1c,0x18)}
    for i,token in enumerate(tokens):
        buffer=BUF+4*(i+1);o.values[(buffer,0x24)]=rng.choice([0,1,2,3,4,5,0x80000000,0xffffffff]);o.getResults[(buffer,0x24)]=rng.choice([0,0,1,0x80004005])
    o.setResults={m:rng.choice([0,0,1,0x80004005,0xffffffff])for m in(0x3c,0x40,0x44)}
    return c,manager
def compare(entry,c,manager,args=(),fmt=None,expectedFault=0):
    o.events=[];events.clear();o.fault=0;fault=C.c_uint32(0)
    if fmt is not None:o.u.mem_write(FMT,fmt)
    try:expected=o.call(entry,M if entry==0x4b48b0 else POOL,packed(*args))
    except AssertionError:
        assert expectedFault==1 and o.fault==1 and o.u.reg_read(UC_X86_REG_EIP)==0x4b49f1;expected=0
    except UcError as e:
        assert expectedFault==2 and e.errno in(UC_ERR_READ_UNMAPPED,UC_ERR_WRITE_UNMAPPED),(hex(entry),hex(o.u.reg_read(UC_X86_REG_EIP)),e)
        assert o.u.reg_read(UC_X86_REG_EIP)in(0x4b5216,0x4b5275);expected=0
    if entry==0x4b48b0:
        data=(C.c_uint8*len(fmt)).from_buffer_copy(fmt)if fmt is not None else None
        actual=lib.claw_audio_create_resource(C.byref(c),data,args[1],host,C.byref(fault))
    elif entry==0x4b42e0:actual=lib.claw_audio_allocate_voice(C.byref(c),POOL,args[0],host,C.byref(fault))
    else:actual=lib.claw_audio_select_voice(C.byref(c),POOL,host,C.byref(fault))
    assert fault.value==expectedFault,(hex(entry),'fault',fault.value,expectedFault)
    assert expected==actual,(hex(entry),'return',expected,actual)
    assert o.events==events,(hex(entry),'events',o.events,events)
    for token,array in nativeObjects.items():assert list(array)==o.read_words(token,14),(hex(entry),'object',hex(token),list(array),o.read_words(token,14))
    assert o.objects.keys()==nativeObjects.keys()
    manager[1]=c.resourceHead;manager[2]=c.resourceTail
    assert o.read_words(M,32)==manager
    assert o.read_words(TEB,1)==[0xdeadbeef]or expectedFault,'SEH chain restored'
    return actual

# PCM format field assumptions and wrapped duration. Whole constructor output
# and resource list insertion are checked, including failing getters.
for i in range(4000):
    c,manager=prepare();fmt=struct.pack('<HHIIHHH',rng.choice([1,1,2,3,0xffff]),rng.choice([0,1,2,17]),rng.getrandbits(32),rng.choice([1,1000,11025,22050,44100,88200,176400,0xffffffff]),rng.randrange(65536),rng.randrange(65536),rng.randrange(65536))
    size=rng.choice([0,1,3,11025,88200,0x400000,0x7fffffff,0xffffffff,rng.getrandbits(32)])
    token=compare(0x4b48b0,c,manager,(FMT,size,0),fmt)
    if token:assert nativeObjects[token][10]==((size*1000)&MASK)//struct.unpack_from('<I',fmt,8)[0]
print('PASS 4,000 PCM resource creation calls: complete constructors/list buffers, format copy, HRESULT ordering, wrapped duration',flush=True)
for i in range(20):
    c,manager=prepare();c.deviceAvailable=1;manager[0x78//4]=1;o.write_words(M+0x78,[1])
    compare(0x4b48b0,c,manager,(0,rng.randrange(1,100000),0))
c,manager=prepare();c.deviceAvailable=1;manager[0x78//4]=1;o.write_words(M+0x78,[1]);o.createResult=0;o.createdBuffer=BUF
fmt=struct.pack('<HHIIHHH',1,1,22050,44100,2,16,32)
created=[]
for i in range(64):
    o.allocToken=0x1050000+i*0x100;o.allocWords=words(14)
    created.append(compare(0x4b48b0,c,manager,(FMT,44100+i,0),fmt))
assert c.resourceHead==created[-1]+4 and c.resourceTail==created[0]+4
print('PASS 64 consecutive resource creations: complete manager resource-list links and metadata; 20 null-format gates',flush=True)

# Allocation is tested directly so its clean failure returns can be compared
# separately from selection's subsequent null-node failure.
for i in range(3000):
    c,manager=prepare(rng.randrange(9));o.allocToken=rng.choice([0,0x1050000]);reusable=rng.getrandbits(32)
    compare(0x4b42e0,c,manager,(reusable,))
print('PASS 3,000 direct voice allocations/duplicates: complete new/existing objects and head insertion, reusable flags, failure returns',flush=True)

for i in range(5000):
    c,manager=prepare(rng.randrange(9));o.dupResult=0
    compare(0x4b4430,c,manager)
print('PASS 5,000 voice selections: eligibility/status/error gates, raw default restoration, full list reordering and allocations',flush=True)

# Real RIFF parsing: duplicate fmt, odd padding, unknown chunks, data-first,
# missing data and non-RIFF inputs. Header reads never leave the mapped file.
def chunk(tag,payload):return tag+struct.pack('<I',len(payload))+payload+(b'\0'if len(payload)%2 else b'')
for i in range(5000):
    chunks=[]
    for j in range(rng.randrange(8)):
        tag=rng.choice([b'fmt ',b'data',b'JUNK',b'LIST']);chunks.append(chunk(tag,bytes(rng.randrange(256)for _ in range(rng.randrange(30)))))
    body=b'WAVE'+b''.join(chunks);data=b'RIFF'+struct.pack('<I',len(body))+body
    if i%7==0:data=b'NOPE'+data[4:]
    if i%11==0:data=data[:8]+b'NOPE'+data[12:]
    o.u.mem_write(RIFF,data);initial=[0xdead0001,0xdead0002,0xdead0003];o.write_words(OUT,initial)
    expected=o.call(0x4b4e30,0,packed(RIFF,OUT,OUT+4,OUT+8));out=RiffResult(*initial);fault=C.c_uint32();nativeData=(C.c_uint8*len(data)).from_buffer_copy(data)
    actual=lib.claw_audio_parse_riff(nativeData,len(data),C.byref(out),C.byref(fault));assert not fault.value and expected==actual
    original=o.read_words(OUT,3)
    for index in(0,1):
        if original[index]not in(0,initial[index]):original[index]-=RIFF
    assert original==[out.formatOffset,out.dataOffset,out.dataBytes]
print('PASS 5,000 RIFF parser calls: complete outputs, first-data semantics, latest preceding fmt, odd-size padding',flush=True)

# Consecutive head→tail selections form a round-robin only for stopped eligible
# voices. All-playing cases grow the list without any hard cap here.
for playing in(0,1):
    c,manager=prepare(6);c.deviceAvailable=1;manager[0x78//4]=1;o.write_words(M+0x78,[1]);o.dupResult=0
    initialOrder=[0x1010000+i*0x100 for i in range(6)];chosen=[]
    for token in initialOrder:nativeObjects[token][12]=1;o.write_words(token+0x30,[1]);o.values[(nativeObjects[token][3],0x24)]=playing;o.getResults[(nativeObjects[token][3],0x24)]=0
    for i in range(48):
        o.allocToken=0x1050000+i*0x100;o.allocWords=words(14)
        if playing:o.values[(o.duplicateOutput,0x24)]=1;o.getResults[(o.duplicateOutput,0x24)]=0
        token=compare(0x4b4430,c,manager);chosen.append(token)
    if not playing:assert chosen==initialOrder*8
    else:assert len(nativeObjects)==55 and len(set(chosen))==48
print('PASS 96 chained list selections: stopped-voice ordering and uncapped allocation while all voices report playing',flush=True)

# Actual original faults: fresh CPUs after division interrupts. Preserve all
# observable side effects before each fault, with native diagnostics scoped.
coverage=set(o.executed)
for entry,allocationFailure in((0x4b48b0,False),(0x4b48b0,True),(0x4b4430,True),(0x4b4430,False)):
    o=OriginalAudioResource();c,manager=prepare();c.deviceAvailable=1;manager[0x78//4]=1;o.write_words(M+0x78,[1]);o.createResult=0;o.createdBuffer=BUF
    fmt=struct.pack('<HHIIHHH',1,1,22050,0,2,16,0)
    if entry==0x4b48b0:
        if allocationFailure:o.allocToken=0
        compare(entry,c,manager,(FMT,44100,0),fmt,2 if allocationFailure else 1)
    else:
        if allocationFailure:o.allocToken=0
        else:o.dupResult=1
        compare(entry,c,manager,expectedFault=2)
    coverage.update(o.executed)
o.executed.update(coverage)
# Bounded parser diagnostics are host extensions; an invalid header retains
# outputs, whereas an accepted but truncated chunk header would overread.
out=RiffResult(1,2,3);fault=C.c_uint32();truncated=b'RIFF'+struct.pack('<I',20)+b'WAVE'+b'fmt '
buf=(C.c_uint8*len(truncated)).from_buffer_copy(truncated)
assert lib.claw_audio_parse_riff(buf,len(truncated),C.byref(out),C.byref(fault))==0 and fault.value==1
print('PASS real original divide-by-zero/null-node fault boundaries and pre-fault buffers; bounded parser diagnostics',flush=True)
print(f'{len(o.executed)} original instruction addresses; allocator, Windows FS/SEH, DirectSound COM methods, error reporting adapted explicitly')
