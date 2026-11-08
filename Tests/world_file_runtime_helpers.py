"""Raw world loader oracle. Resource/codec/object-record seams are explicit."""
import ctypes as C,hashlib,json,random,struct,subprocess,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/world-file-agent';U=C.c_uint32
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['WorldFileRuntime.cpp','WorldPlaneRuntime.cpp','CArrayRuntime.cpp','SpatialGridRuntime.cpp','SceneCameraRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']],'-o',str(WORK/'libWorldFileRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libWorldFileRuntime.dylib'))
class Args(C.Structure):_fields_=[('words',U*4),('count',U)]
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class SceneHost(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class ArrayContext(C.Structure):_fields_=[('scene',SceneHost)]+[(n,U)for n in ('composeAllocator','globalNewHandler','fault','crtNewMode','smallBlockThreshold','heapHandle','heapAllocFunction')]
class Context(C.Structure):_fields_=[('scene',SceneHost),('arrays',C.POINTER(ArrayContext)),('composeSpatial',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U),('name',C.c_char_p),('size',C.POINTER(U)),('temporary',C.POINTER(U))]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_world_file_entry.argtypes=[U,U,Args,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(U)];lib.claw_carray_defaults.argtypes=[C.POINTER(ArrayContext)]
BASE,SIZE=0x3000000,0x1000000;WORLD,PARENT,SCENE,REGISTRY,MANAGER,TABLE,IMAGE,RECORD,OLD,FILE=[BASE+i*0x1000 for i in range(1,11)];RAW=BASE+0x10000;ALLOC=BASE+0x400000;FILEFN=BASE+0xf000
heap=(C.c_uint8*SIZE)();m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.write_words(0x546d58,[0x10fd0c0]);m.write_words(0x546d5c,[0x10fd0d0]);m.executed.clear();rng=random.Random(0x4cb200)
native=True;events=[];calls=eventCount=0;cursor=ALLOC;allocations=[];frees=[];policy=0;allocationFailures=0;array=ArrayContext();ctx=Context();errors=[];filePayload=b'';recordCount=0;resourceFail=False;codecFail=False
# Every event hashes the entire declared16MiB heap, including unused seed bytes.
def snapshot():return hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest()
def log(event):events.append((event,snapshot()))
def words(t,n=1):return list((U*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(U*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def write(t,b):C.memmove(C.addressof(heap)+t-BASE,b,len(b))if native else u.mem_write(t,b)
def read(t,n):return bytes(heap[t-BASE:t-BASE+n])if native else bytes(u.mem_read(t,n))
def text(t):
 out=bytearray()
 for i in range(256):
  b=read(t+i,1)[0]
  if not b:return out.decode('ascii')
  out.append(b)
 raise AssertionError('unbounded name')
@Lookup
def lookup(_,t,n):
 if t%4 or not(BASE<=t and t+n*4<=BASE+SIZE):errors.append(('lookup',hex(t),n));return None
 return C.addressof(heap)+t-BASE
@Allocate
def allocate(_,n):
 global cursor,allocationFailures
 log(('allocate',n))
 if allocationFailures:allocationFailures-=1;return 0
 result=cursor;cursor+=max(16,(n+15)&~15);assert cursor<BASE+SIZE,(hex(cursor),n);allocations.append((result,n));return result
@Free
def free(_,t):log(('free',t));frees.append(t)
@Clock
def clock(_):raise AssertionError('world loader does not read clocks')
def effect(fn,receiver,args,name=None,size=None,temporary=None):
 global recordCount
 log(('call',fn,receiver,args,name,size[0]if size is not None else None,None if fn==0x4f72c9 else tuple(temporary)if temporary is not None else None))
 if fn==0x4f6286:return MANAGER if not resourceFail else 0
 if fn==0x4d1620:
  at=args[0];records=[]
  for i in range(args[1]):
   length=284+sum(words(at+4,4));records.append((at,length,hashlib.sha256(read(at,length)).hexdigest()));at+=length
  log(('records-boundary',tuple(records)));recordCount+=len(records)
  return 1
 if fn==0x4d17e0:
  record=args[0];length=284+sum(words(record+4,4));recordCount+=1
  # Entire raw record/string ownership is sampled before decoded buffer free.
  log(('record',record,length,hashlib.sha256(read(record,length)).hexdigest()))
  return length
 if fn==0x4d5fe0:
  assert size is not None and args[1]==0
  if codecFail:return 0xfffffffd
  decoded=zlib.decompress(read(args[2],args[3]));assert len(decoded)<=size[0];write(args[0],decoded);size[0]=len(decoded);return 0
 if fn==0x4d2210:
  if policy==2:put(receiver+0x50,[77])
  return receiver
 if fn==0x4f58ab:put(receiver,[0x5108fc,0,0,0,0]);return receiver
 if fn==0x4f5915:
  p=words(receiver,5)
  if p[1]:free(None,p[1])
  put(receiver+4,[0,0,0]);return 0
 if fn==0x4f582f:
  p=words(receiver,5);index,value=args
  if not p[1]:p[1]=allocate(None,256);p[3]=64
  write(p[1]+index*4,struct.pack('<I',value));p[2]=max(p[2],index+1);put(receiver,p);return 0
 if fn==0x4b61c0:return RAW if not resourceFail else 0
 if fn==0x4b6230:return 0
 if fn==0x4f72c9:temporary[:]=[0x510844,0xffffffff,0,0x52e1c4];return 0
 if fn==0x4f7448:
  if resourceFail:return 0
  temporary[1]=0xabcd;temporary[2]=1;return 1
 if fn==0x4f774d:return len(filePayload)
 if fn==0x4f7570:write(args[0],filePayload[:args[1]]);return args[1]
 if fn==0x4f7369:temporary[0]=0x50becc;return 0
 raise AssertionError(('unrepresented service',hex(fn),hex(receiver),args))
@Dependency
def dependency(context,c,_):
 try:
  c=c.contents;size=[c.size[0]]if c.size else None;temp=[c.temporary[i]for i in range(4)]if c.temporary else None;result=effect(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]),c.name.decode('ascii')if c.name else None,size,temp)
  if size is not None:c.size[0]=size[0]
  if temp is not None:
   for i,x in enumerate(temp):c.temporary[i]=x
  return result
 except BaseException as error:errors.append(error);context.contents.fault=1;return 0
@Invoke
def invoke(_,c):return effect(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]))
host=SceneHost(None,lookup,allocate,free,invoke,clock);ctx.scene=host;array.scene=host;ctx.arrays=C.pointer(array);ctx.composeSpatial=0
#4f6286 original bool/output call adapts only temporaryname/outpointer identities.
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x10fd0d0:
  values=m.read_words(sp+4,5);m.write_words(values[0],values[1:]);returned(20,1);return
 if address==0x10fd0c0:
  out,src=m.read_words(sp+4,2);u.mem_write(out,bytes(u.mem_read(src,16)));returned(8,1);return
 if address==0x4f63ec:returned(0,allocate(None,m.read_words(sp+4,1)[0]));return
 if address==0x4f6428:free(None,m.read_words(sp+4,1)[0]);returned(0);return
 if address==0x4f6286:
  a=m.read_words(sp+4,2);result=effect(address,receiver,(),text(a[0]));m.write_words(a[1],[result]);returned(8,1 if result else 0);return
 if address==0x4d5fe0:
  a=m.read_words(sp+4,4);length=[m.read_words(a[1],1)[0]];a[1]=0;result=effect(address,0,tuple(a),size=length);m.write_words(m.read_words(sp+8,1)[0],length);returned(0,result);return
 if address==0x4d1620 and not ctx.composeSpatial:
  returned(8,effect(address,receiver,tuple(m.read_words(sp+4,2))));return
 if address==0x4d17e0:returned(4,effect(address,receiver,tuple(m.read_words(sp+4,1))));return
 if not bool(ctx.arrays)and(address in(0x4f5915,0x4f582f)or address==0x4f58ab and receiver in(WORLD+0x20,WORLD+0x34,WORLD+0x48)):
  n=0 if address==0x4f58ab else 2;returned(n*4,effect(address,receiver,tuple(m.read_words(sp+4,n))));return
 if address in(0x4b61c0,0x4b6230):returned(0,effect(address,receiver,()));return
 if address in(0x4f72c9,0x4f7448,0x4f774d,0x4f7570,0x4f7369):
  n={0x4f72c9:0,0x4f7448:3,0x4f774d:0,0x4f7570:2,0x4f7369:0}[address];temp=m.read_words(receiver,4);result=effect(address,0,tuple(m.read_words(sp+4,n)),temporary=temp);m.write_words(receiver,temp);returned(n*4,result)
u.hook_add(UC_HOOK_CODE,hook)
def callMachine(f,receiver,args=()):
 u.mem_write(m.stack,struct.pack('<'+'I'*(len(args)+1),m.stop,*args));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,receiver);
 try:u.emu_start(f,m.stop,count=100000000)
 except BaseException as error:raise AssertionError((hex(u.reg_read(UC_X86_REG_EIP)),hex(u.reg_read(UC_X86_REG_ESP)),[e[0]for e in events[-4:]]))from error
 assert u.reg_read(UC_X86_REG_EIP)==m.stop;return u.reg_read(UC_X86_REG_EAX)
def reset(data=None):
 global native,cursor,allocations,frees,policy,allocationFailures,errors,filePayload,recordCount,resourceFail,codecFail,events
 native=True;cursor=ALLOC;allocations=[];frees=[];policy=allocationFailures=0;errors=[];recordCount=0;resourceFail=codecFail=False;events=[];pattern=rng.randbytes(4096);C.memmove(C.addressof(heap),pattern*(SIZE//4096),SIZE)
 ctx.fault=0;ctx.arrays=C.pointer(array);ctx.composeSpatial=0;array.composeAllocator=0;array.fault=0;lib.claw_carray_defaults(C.byref(array));array.scene=host
 put(WORLD,[0]*56);put(WORLD,[0x513938,42,0,PARENT]);put(WORLD+0x10,[0,0,639,479]);put(WORLD+0x20,[0x5108fc,0,0,0,0]);put(WORLD+0x34,[0x5108fc,0,0,0,0]);put(WORLD+0x48,[0x5108fc,0,0,0,0]);put(WORLD+0x60,[0xffffffff]);put(WORLD+0xb0,[500,250,1000,1000,250,125,1600,1200,2560,1920,768,576]);put(PARENT,[0]*12);put(PARENT+8,[SCENE]);put(PARENT+0x10,[REGISTRY]);put(PARENT+0x24,[WORLD]);put(SCENE,[0]*12);put(SCENE,[0x513c20,0,0,PARENT]);put(MANAGER,[0]*27);put(MANAGER+0x14,[TABLE,16]);put(MANAGER+0x64,[0,15]);put(TABLE,[IMAGE]*16);put(IMAGE,[0x513a70,0,0,PARENT,64,64,32,32,0,0,0x10,0,0]);filePayload=data or b''
 if data:assert len(data)<ALLOC-RAW;write(RAW,data)
def compare(f,receiver,args,label,expectedFault=0):
 global native,events,calls,eventCount,cursor,allocations,frees,allocationFailures,recordCount
 before=bytes(heap);old=(cursor,allocations[:],frees[:],allocationFailures,recordCount);events=[];ctx.fault=0;array.fault=0;a=Args();a.count=len(args);a.words[:len(args)]=args;result=U();recognized=lib.claw_world_file_entry(f,receiver,a,C.byref(ctx),dependency,None,C.byref(result));assert not errors,(label,errors);assert ctx.fault==expectedFault and recognized==(not expectedFault),(label,ctx.fault,recognized)
 expected=snapshot();expectedEvents=events[:];expectedHeap=bytes(heap);ownership=(cursor,allocations[:],frees[:],allocationFailures,recordCount);native=False;u.mem_write(BASE,before);cursor,allocations,frees,allocationFailures,recordCount=old;events=[];original=callMachine(f,receiver,args)
 assert events==expectedEvents,(label,'events',[(a[0],b[0],a[1]==b[1])for a,b in zip(expectedEvents,events)if a!=b][:3],len(expectedEvents),len(events))
 actual=snapshot()
 if actual!=expected:
  originalHeap=bytes(u.mem_read(BASE,SIZE));raise AssertionError((label,'heap',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(SIZE//4),expectedHeap),struct.unpack('<'+'I'*(SIZE//4),originalHeap)))if x!=y][:15]))
 assert ownership==(cursor,allocations,frees,allocationFailures,recordCount),(label,'ownership',ownership,(cursor,allocations,frees,allocationFailures,recordCount))
 if f not in(0x4cb180,0x4cb5f0,0x4cde90,0x423f00,0x4d0a00,0x4d2230,0x4f58de,0x4cdd30):assert result.value==original,(label,'return',result.value,original)
 native=True;events=expectedEvents;calls+=1;eventCount+=len(events);return result.value

def worlds():
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';result=[]
 def w(o):return struct.unpack_from('<I',blob,o)[0]
 def walk(offset,size,parent=()):
  end=offset+size
  while offset<end:
   kind,target,length=w(offset),w(offset+4),w(offset+8);start=offset+(16 if kind else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode('ascii')
   if kind:walk(target,length,parent+(name,));offset=nul+1
   else:
    extension=blob[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii');offset=nul+2
    if len(parent)==2 and parent[0].startswith('LEVEL')and parent[1]=='WORLDS'and name=='WORLD'and extension=='WWD':result.append(('/'.join(parent),blob[target:target+length]))
 walk(w(131),w(135));assert len(result)==14;return sorted(result,key=lambda x:int(x[0].split('/')[0][5:]))

def synthetic(seed=0,compressed=False):
 rr=random.Random(seed);h=bytearray(1524);struct.pack_into('<I',h,0,1524);struct.pack_into('<I',h,8,3 if compressed else 1);h[16:23]=b'TestMap'
 records=[];body=bytearray(480)
 for i in range(3):
  w=[0]*40;w[0]=160;w[2]=(1 if i==1 else 4 if i==0 else 8);w[22:26]=[64,64,16,12];w[26:30]=[rr.randrange(2048),rr.randrange(1536),[30,100,200][i],[40,100,150][i]];w[30]=0x12345678;w[31]=1;w[32]=0;w[33]=1524+len(body);w[35]=0;w[36]=i*500
  body.extend(bytes((-len(body))%4));w[33]=1524+len(body);body.extend(struct.pack('<192I',*range(192)));w[34]=1524+len(body);body.extend([b'BACK\0',b'ACTION\0',b'FRONT\0'][i]);record=bytearray(struct.pack('<40I',*w));record[16:24]=[b'Back\0\0\0\0',b'Main\0\0\0\0',b'Front\0\0\0'][i];body[i*160:(i+1)*160]=record
 # Deliberately unaligned tile descriptions, including owned byte mask.
 tableOffset=1524+len(body);table=bytearray(32);struct.pack_into('<I',table,8,3);body.extend(table);body.extend(struct.pack('<5I',1,0,4,16,2));body.extend(struct.pack('<10I',2,0,64,64,0,0,63,63,4,16));body.extend(struct.pack('<4I',3,0,4,4)+bytes(range(16)))
 struct.pack_into('<2I',h,720,rr.randrange(2048),rr.randrange(1536));struct.pack_into('<5I',h,732,3,1524,tableOffset,len(body),0xdeadbeef)
 return bytes(h)+(zlib.compress(bytes(body))if compressed else bytes(body))
