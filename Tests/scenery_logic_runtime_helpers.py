"""Scenery callback oracle composed with original actor animation; resource seams explicit."""
import argparse,collections,ctypes as C,hashlib,io,json,random,struct,subprocess,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/scenery-logic-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');options=p.parse_args()
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in ['SceneryLogicRuntime.cpp','WorldObjectRuntime.cpp','ActorResourceBindings.cpp','ActorDestruction.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp']],'-o',str(WORK/'libSceneryLogicRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libSceneryLogicRuntime.dylib'))
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,Call);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('animationDelta',C.c_uint32),('audioPosition',C.c_uint32)]
class SceneryContext(C.Structure):_fields_=[('scene',Host),('animation',Globals),('settingsToken',C.c_uint32),('composeAnimation',C.c_uint32),('fault',C.c_uint32)]
class ObjectState(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class ObjectContext(C.Structure):_fields_=[(x,C.c_uint32)for x in ('sceneToken','actorToken','logicToken','sceneDefaultType')]+[(x,C.c_int32)for x in ('worldWidth','worldHeight')]+[('registryToken',C.c_uint32),('layers',C.c_uint32*3)]+[(x,C.c_uint32)for x in ('entryToken','entryCallback','entryFlags')]
class DestructionGlobals(C.Structure):_fields_=[(x,C.c_uint32)for x in ('holderActorToken','heldActorToken','emptyStringToken')]
class BindingState(C.Structure):_fields_=[('actor',C.c_uint32*128),('secondary',C.c_uint32*93)]
class ImageBinding(C.Structure):_fields_=[('token',C.c_uint32),('minimum',C.c_int32),('maximum',C.c_int32),('firstImageIndex',C.c_int32),('images',C.POINTER(C.c_uint32)),('imageCount',C.c_size_t)]
class BindingContext(C.Structure):_fields_=[('imageRegistryToken',C.c_uint32),('logicRegistryToken',C.c_uint32),('image',ImageBinding)]+[(n,C.c_uint32)for n in ('metadataToken','metadataCallback','metadataFlags','associatedDestructor')]
class BindingCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argument',C.c_uint32),('name',C.c_char_p)]
BindingDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(BindingState),C.POINTER(BindingContext),C.POINTER(BindingCall),C.c_void_p)
class Record(C.Structure):_fields_=[(x,C.c_uint32)for x in ['flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event']]
lib.claw_actor_animation_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Globals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_actor_animation_entry.restype=C.c_uint32
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(Record),C.POINTER(C.c_uint32)];lib.claw_animation_decode_record.restype=C.c_uint32
lib.claw_scenery_logic_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(SceneryContext),C.POINTER(C.c_uint32)]
lib.claw_world_object_construct.argtypes=[C.POINTER(ObjectState),C.POINTER(ObjectContext),C.c_uint32]
lib.claw_world_object_initialize.argtypes=[C.POINTER(ObjectState),C.POINTER(ObjectContext),C.c_uint32,C.c_uint32,C.c_uint32]
lib.claw_actor_destruction_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(DestructionGlobals),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
lib.claw_actor_bind_default_image.argtypes=[C.POINTER(BindingState),C.POINTER(BindingContext),C.c_char_p,BindingDependency,C.c_void_p]
lib.claw_actor_bind_indexed_image.argtypes=[C.POINTER(BindingState),C.POINTER(BindingContext),C.c_char_p,C.c_int32,BindingDependency,C.c_void_p]
m=OriginalV10(options.exe);u=m.u;u.mem_map(0,4096);m.executed.clear()
IMAGE_BASE,IMAGE_END,_=next(v for v in u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(IMAGE_END-IMAGE_BASE+1)).from_buffer_copy(bytes(u.mem_read(IMAGE_BASE,IMAGE_END-IMAGE_BASE+1)))
BASE,SIZE=0x1000000,0x10000;heap=(C.c_uint8*SIZE)();rng=random.Random(0x4c79e0)
A,SC,SEQ,PTRS,RECORDS,IM,IMAGES,NAME,STANDALONE,ALT=[BASE+i*0x1000 for i in range(1,11)]
ANI=A+0x188;DATA=0x1010000
L,SETTINGS,ENTRY=ALT,BASE+0xe000,BASE+0xf000
native=True;globals=Globals();events=[];lookupResult=SEQ;policy=0;calls=event_count=decodes=0;decoderMode=False;decodedEvent=0;ctorMode=False;allocationResult=L;constructorCalls=0;constructorAllocationProfile=[]
replay=io.BytesIO();replayCases=0;replayFunctions=set()
rates=[0,0x3f800000,0x3f000000,0x40000000,0x3faaaaab,0xbf800000,0x7f800000,0x7fc00000,0x00800000,0x4f000000,0x3f7fffff]
def words(t,n):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=v
 else:m.write_words(t,v)
def snap():return (bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(globals)if native else struct.pack('<2I',m.read_words(0x5430c4,1)[0],m.read_words(0x532c10,1)[0]))
def name(t):
 if native and BASE<=t<BASE+SIZE:return bytes(heap[t-BASE:t-BASE+100]).split(b'\0')[0]
 return bytes(u.mem_read(t,100)).split(b'\0')[0]
def effect(fn,receiver,args):
 global globals
 if fn==0x4f6286:
  if policy==1:
   a=words(A,128);a[0x40//4]^=2;a[0x190//4]^=0xfeed;put(A,a)
   if native:globals.animationDelta=81
   else:m.write_words(0x5430c4,[81])
  if policy==4:
   put(A+0x64,[123]);put(A+8,[words(A+8,1)[0]|0x400000]);put(L+0x1c,[99]);put(SETTINGS+0x124,[0])
  return lookupResult
 if policy==2:
  # Audio may change its own external globals, not actor/ANI records.
  if native:globals.audioPosition^=1
  else:m.write_words(0x532c10,[m.read_words(0x532c10,1)[0]^1])
 if policy==3:
  a=words(A,128);a[2]^=1;put(A,a)
 return 0
@Lookup
def lookup(_,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_BASE<=t and t+n*4<=IMAGE_END+1:return C.addressof(image)+t-IMAGE_BASE
 return None
@Allocate
def allocate(_,n):raise AssertionError('scenery callbacks do not allocate gameplay heap')
@Free
def free(_,t):events.append(((0x4f6428,0,(t,),None),snap()))
@Invoke
def invoke(_,c):
 args=tuple(c.arguments[:c.argumentCount]);ev=(c.function,c.receiver,args,name(args[0])if c.function==0x4f6286 else None);events.append((ev,snap()));return effect(c.function,c.receiver,args)
@Clock
def clock(_):raise AssertionError('actor-animation wrappers do not read OS clocks')
host=Host(None,lookup,allocate,free,invoke,clock)
context=SceneryContext(host,Globals(),SETTINGS,1,0)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def original_hook(uc,address,size,user):
 if not context.composeAnimation and address in(0x4c79e0,0x4c82a0):
  receiver=u.reg_read(UC_X86_REG_ECX);n=2 if address==0x4c79e0 else 1;args=tuple(m.read_words(u.reg_read(UC_X86_REG_ESP)+4,n));events.append(((address,receiver,args,None),snap()));returned(n*4,effect(address,receiver,args));return
 if address==0x4f63ec and ctorMode:
  n=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)[0];assert n==0x174;constructorAllocationProfile.append(n);returned(0,allocationResult);return
 if address==0x4f6428:
  free(None,m.read_words(u.reg_read(UC_X86_REG_ESP)+4,1)[0]);returned(0);return
 if address not in(0x4f6286,0x4c88e0,0x4208e0):return
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f6286:
  token,out=m.read_words(sp+4,2)
  if decoderMode:m.write_words(out,[decodedEvent]);returned(8,int(bool(decodedEvent)));return
  args=(token,);ev=(address,receiver,args,name(token));events.append((ev,snap()));r=effect(address,receiver,args);m.write_words(out,[r]);returned(8,int(bool(r)));return
 args=tuple(m.read_words(sp+4,4));events.append(((address,receiver,args,None),snap()));returned(16,effect(address,receiver,args))
u.hook_add(UC_HOOK_CODE,original_hook)
def setup(count=4):
 global native,globals,lookupResult,policy
 native=True;heap[:]=rng.randbytes(SIZE);globals=Globals(rng.choice([0,1,16,80,0xffffffff]),rng.getrandbits(32));lookupResult=SEQ;policy=0
 put(A+0xc,[SC]);put(SC+0x10,[BASE+0xb000]);put(SC+0x28,[BASE+0xb000]);put(SC+0x2c,[BASE+0xc000]);put(SEQ+0xc,[PTRS,count]);put(PTRS,[RECORDS+i*0x40 for i in range(count)])
 put(IM+0x14,[IMAGES]);put(IM+0x64,[1,12]);put(IMAGES,[0]+[0x100d000+i*0x20 if rng.randrange(5)else 0 for i in range(12)])
 put(A+0x170,[IM]);put(A+0x16c,[rng.choice([1,2,11,12,0xffffffff])]);put(A+0x40,[rng.getrandbits(32)]);put(A+0x4c,[rng.getrandbits(32),rng.getrandbits(32)])
 for i in range(count):
  put(RECORDS+i*0x40,[rng.getrandbits(32),rng.getrandbits(32),rng.randrange(9),rng.choice(list(range(10))+[0x10009]),rng.randrange(4),rng.choice([0,1,2,11,12,0xffffffff]),rng.choice([0,1,16,80,0xffffffff]),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),BASE+0xd000 if rng.randrange(3)==0 else 0])
 for state in(ANI,STANDALONE):
  idx=rng.randrange(count);put(state+4,[A,SEQ,RECORDS+idx*0x40,idx,rng.choice([0,0,1,16,0xffffffff]),rng.randrange(2),rng.randrange(2),rng.getrandbits(32),rng.getrandbits(32),rng.choice(rates)])
 heap[NAME-BASE:NAME-BASE+15]=b'LEVEL_RAT_IDLE\0'
 put(A+0x6c,[L]);put(L,[0x513740,1,2,SC,0x461970,0,0,0]);put(SETTINGS+0x124,[1]);context.settingsToken=SETTINGS;context.composeAnimation=1;context.fault=0
def compare(f,t,label,a=0,b=0):
 global native,globals,calls,event_count
 native=True;oldHeap=bytes(heap);oldGlobals=bytes(globals);events.clear();fault=C.c_uint32();result=C.c_uint32()
 rr=lib.claw_actor_animation_entry(f,t,a,b,C.byref(globals),host,C.byref(fault),C.byref(result));assert rr and not fault.value,(label,'native fault',fault.value)
 expected=snap();expectedEvents=list(events);u.mem_write(BASE,oldHeap);m.write_words(0,[0x12345678]);m.write_words(0x5430c4,[struct.unpack_from('<I',oldGlobals,0)[0]]);m.write_words(0x532c10,[struct.unpack_from('<I',oldGlobals,4)[0]]);native=False;events.clear()
 args=struct.pack('<2I',a,b)if f in(0x4c79e0,0x420a10)else struct.pack('<I',a)if f in(0x4c7a40,0x4c8220,0x4c8260,0x4c82a0)else b''
 try:ret=m.call(f,t,args)
 except Exception:print('original fault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 if snap()!=expected:
  actual=snap()
  for i in range(0,len(actual),4):
   x,y=struct.unpack_from('<I',actual,i)[0],struct.unpack_from('<I',expected,i)[0]
   if x!=y:print(label,hex(i),hex(x),hex(y))
  raise AssertionError((label,'full actor/animation/record/image/guard buffers'))
 if f in(0x4c79e0,0x4c7a40,0x4c82a0,0x4c8210):assert ret==result.value,(label,'meaningful EAX',hex(ret),hex(result.value))
 if events!=expectedEvents:
  print(label,'original',[e for e,s in events]);print('native',[e for e,s in expectedEvents]);
  for i,(x,y)in enumerate(zip(events,expectedEvents)):
   if x!=y:print('boundary mismatch',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError((label,'ordered full buffer events'))
 assert m.read_words(0,1)==[0x12345678]
 native=True;calls+=1;event_count+=len(events)
def decode(data,event,index):
 global native,decoderMode,decodedEvent,decodes
 native=True;record=Record();length=C.c_uint32();buf=(C.c_uint8*len(data)).from_buffer_copy(data);used=lib.claw_animation_decode_record(buf,len(data),event,C.byref(record),C.byref(length));assert used
 token=RECORDS+index*0x40;seed=words(token,12);u.mem_write(DATA,data);m.write_words(token,seed);decoderMode=True;decodedEvent=event
 try:m.call(0x4d76e0,token,struct.pack('<2I',BASE+0xb000,DATA))
 finally:decoderMode=False
 raw=m.read_words(token,12);vals=[record.flags]+[getattr(record,k)for k,_ in Record._fields_[1:-1]]+[record.event]
 assert vals==[raw[1]&0xffff]+raw[2:10]+[raw[11]];assert used==20+m.read_words(0x543174,1)[0]
 put(token,raw);decodes+=1;return used

def compareScenery(f,label):
 global native,globals,calls,event_count,replayCases
 native=True;oldHeap=bytes(heap);oldGlobals=bytes(globals);events.clear();context.animation=globals;globals=context.animation;context.fault=0;result=C.c_uint32()
 assert lib.claw_scenery_logic_entry(f,A,C.byref(context),C.byref(result))==1 and context.fault==0,(label,context.fault)
 expected=snap();expectedEvents=list(events);u.mem_write(BASE,oldHeap);m.write_words(0x5430c4,[struct.unpack_from('<I',oldGlobals)[0]]);m.write_words(0x532c10,[struct.unpack_from('<I',oldGlobals,4)[0]]);m.write_words(0x5371fc,[context.settingsToken]);native=False;events.clear()
 original=m.call(f,0,struct.pack('<I',A));actual=snap()
 if expected!=actual:raise AssertionError((label,'heap',[(hex(BASE+i),hex(x),hex(y))for i,(x,y)in enumerate(zip(expected,actual))if x!=y][:16]))
 assert original==result.value,(label,'EAX',original,result.value)
 assert u.reg_read(UC_X86_REG_ESP)==m.stack+4,(label,'cdecl callback ESP')
 assert events==expectedEvents,(label,'events',[(e,len(s))for e,s in events],[(e,len(s))for e,s in expectedEvents])
 if f not in replayFunctions or calls%43==0 or label.startswith('directed/'):
  delta,volume=struct.unpack('<2I',oldGlobals);afterDelta,afterVolume=struct.unpack('<2I',expected[-8:]);replay.write(struct.pack('<10I',f,delta,volume,context.settingsToken,context.composeAnimation,policy,lookupResult,original,afterDelta,afterVolume)+oldHeap+actual[:SIZE]);replayCases+=1;replayFunctions.add(f)
 native=True;calls+=1;event_count+=len(events);return original

def constructor(id,x,y,z,callback,flags=2,fail=False):
 global native,ctorMode,allocationResult,constructorCalls
 c=ObjectContext(SC,A,0 if fail else L,BASE+0xb000,24576,6144,BASE+0xc000,(C.c_uint32*3)(),ENTRY,callback,flags)
 old=bytes(heap);s=ObjectState((C.c_uint32*128)(*words(A,128)),(C.c_uint32*93)(*words(L,93)))
 lib.claw_world_object_construct(C.byref(s),C.byref(c),id);put(A,list(s.actor))
 if not fail:put(L,list(s.logic))
 expected=bytes(heap);native=False;u.mem_write(BASE,old);ctorMode=True;allocationResult=0 if fail else L;constructorAllocationProfile.clear()
 try:
  r=m.call(0x4c98c0,A,struct.pack('<3I',SC,id,0))
  # Actual4d17e0 inlines the animation-derived constructor after its base
  # constructor returns. Execute that verified caller block, with its real
  # EBX actor register, rather than pretending4c98c0 includes those stores.
  u.reg_write(UC_X86_REG_EBX,A);u.emu_start(0x4d18a7,0x4d1905,count=1000)
  assert u.reg_read(UC_X86_REG_EIP)==0x4d1905
 finally:ctorMode=False
 actual=bytes(u.mem_read(BASE,SIZE));assert r==A and actual==expected,('constructor',id,fail,hex(r),[(hex(BASE+i),hex(x),hex(y))for i,(x,y)in enumerate(zip(expected,actual))if x!=y][:16])
 assert constructorAllocationProfile==[0x174]
 native=True;constructorCalls+=1
 if fail:return c
 old=bytes(heap);put(SC+0x24,[c.sceneDefaultType]);put(ENTRY+8,[flags,0,callback]);old=bytes(heap)
 lib.claw_world_object_initialize(C.byref(s),C.byref(c),x,y,z);put(A,list(s.actor));put(L,list(s.logic));expected=bytes(heap)
 native=False;u.mem_write(BASE,old);r=m.call(0x4c9d40,A,struct.pack('<4I',x,y,z,ENTRY));assert r==1 and bytes(u.mem_read(BASE,SIZE))==expected,('initializer',id)
 native=True;constructorCalls+=1;return c

def destroy(label):
 global native,calls,event_count
 oldHeap=bytes(heap);events.clear();fault=C.c_uint32();result=C.c_uint32();g=DestructionGlobals(0,0,0x533470)
 assert lib.claw_actor_destruction_entry(0x4c9be0,A,1,C.byref(g),host,C.byref(fault),C.byref(result))==1 and not fault.value
 expected=snap();expectedEvents=list(events);native=False;u.mem_write(BASE,oldHeap);events.clear();r=m.call(0x4c9be0,A,struct.pack('<I',1))
 assert expected==snap() and expectedEvents==events and r==result.value,(label,'destruction')
 native=True;calls+=1;event_count+=len(events)

def assetFiles():
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';assets={}
 def w(o):return struct.unpack_from('<I',blob,o)[0]
 def walk(offset,size,parent=()):
  end=offset+size
  while offset<end:
   kind,target,length=w(offset),w(offset+4),w(offset+8);start=offset+(16 if kind else 28);nul=blob.index(0,start,end);text=blob[start:nul].decode('ascii')
   if kind:walk(target,length,parent+(text,));offset=nul+1
   else:
    ext=blob[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii');offset=nul+2;assets['/'.join(parent+(text+'.'+ext,))]=blob[target:target+length]
 walk(w(131),w(135));return assets

def actualLevel1(assets):
 b=assets['LEVEL1/WORLDS/WORLD.WWD'];h=struct.unpack_from('<188I',b);raw=b[:h[0]]+zlib.decompress(b[h[0]:]);counts=collections.Counter();records=[]
 for plane in range(h[183]):
  p=struct.unpack_from('<40I',raw,h[184]+plane*160);at=p[35]
  for index in range(p[32]):
   values=struct.unpack_from('<71I',raw,at);pos=at+284;strings=[]
   for length in values[1:5]:strings.append(raw[pos:pos+length].split(b'\0')[0].decode('ascii'));pos+=length
   counts[strings[1]]+=1;records.append((plane,index,values,strings,raw[at:pos]));at=pos
 assert len(records)==1479;return records,counts

def installANI(data):
 count=struct.unpack_from('<I',data,12)[0];pathLength=struct.unpack_from('<I',data,16)[0];assert 0<count<60
 put(SEQ+12,[PTRS,count]);put(PTRS,[RECORDS+i*0x40 for i in range(count)]);at=32+pathLength
 for i in range(count):
  flags=struct.unpack_from('<H',data,at)[0];at+=decode(data[at:],BASE+0xd000+i*0x20 if flags&2 else 0,i)
 assert at==len(data);return count

@BindingDependency
def bindingDependency(state,context,c,user):
 c=c.contents;assert c.function==0x4f6286
 event=(c.function,c.receiver,(NAME,),c.name);events.append((event,snap()));return lookupResult
def bindImages(imageName,imageIDs,imageID,label,missing=False):
 global native,calls,event_count,lookupResult
 first,last=min(imageIDs),max(imageIDs);table=[0]*(last+1)
 for n in imageIDs:table[n]=BASE+0xd000+n*0x20
 put(IM+0x14,[IMAGES]);put(IM+0x64,[first,last]);put(IMAGES,table)
 encoded=imageName.encode()+b'\0';heap[NAME-BASE:NAME-BASE+len(encoded)]=encoded
 c=BindingContext();c.imageRegistryToken=BASE+0xb000+16;c.image=ImageBinding(0,first,last,0,C.cast(C.addressof(heap)+IMAGES-BASE,C.POINTER(C.c_uint32)),last+1)
 s=BindingState((C.c_uint32*128)(*words(A,128)),(C.c_uint32*93)());old=bytes(heap);events.clear();lookupResult=0 if missing else IM
 if imageID==0xffffffff:ret=lib.claw_actor_bind_default_image(C.byref(s),C.byref(c),encoded,bindingDependency,None);f=0x4c7970;args=struct.pack('<I',NAME)
 else:ret=lib.claw_actor_bind_indexed_image(C.byref(s),C.byref(c),encoded,C.c_int32(imageID).value,bindingDependency,None);f=0x4c7900;args=struct.pack('<2I',NAME,imageID)
 assert ret==1;put(A,list(s.actor));expected=snap();expectedEvents=list(events);native=False;u.mem_write(BASE,old);m.write_words(0x5430c4,[globals.animationDelta]);m.write_words(0x532c10,[globals.audioPosition]);events.clear();m.call(f,A,args)
 actual=snap();assert expected==actual and expectedEvents==events,(label,'image binder/full heap/event',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(expected,actual))if x!=y][:10],[(e,s==es)for (e,s),(ee,es)in zip(events,expectedEvents)if e!=ee or s!=es])
 native=True;calls+=1;event_count+=len(events);lookupResult=SEQ
