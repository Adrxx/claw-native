"""Whole impact roots; original scene creator/ANI/RNG can execute end to end."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/impact-particle-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in('ImpactParticleRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','AnimationEngine','AnimationOperations','ActorResourceBindings','WorldLootRuntime','ActorDestruction')],'-o',str(WORK/'libImpactParticleRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Animation(C.Structure):_fields_=[('animationDelta',C.c_uint32),('audioPosition',C.c_uint32)]
class Context(C.Structure):_fields_=[('scene',Host),('animation',Animation),('composeCreation',C.c_uint32),('composeAnimation',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
class BindingState(C.Structure):_fields_=[('actor',C.c_uint32*128),('secondary',C.c_uint32*93)]
class ImageBinding(C.Structure):_fields_=[('token',C.c_uint32),('minimum',C.c_int32),('maximum',C.c_int32),('firstImageIndex',C.c_int32),('images',C.POINTER(C.c_uint32)),('imageCount',C.c_size_t)]
class BindingContext(C.Structure):_fields_=[('imageRegistryToken',C.c_uint32),('logicRegistryToken',C.c_uint32),('image',ImageBinding)]+[(n,C.c_uint32)for n in('metadataToken','metadataCallback','metadataFlags','associatedDestructor')]
class BindingCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argument',C.c_uint32),('name',C.c_char_p)]
BindingDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(BindingState),C.POINTER(BindingContext),C.POINTER(BindingCall),C.c_void_p)
class Destruction(C.Structure):_fields_=[(n,C.c_uint32)for n in ('holderActorToken','heldActorToken','emptyStringToken')]
class Record(C.Structure):_fields_=[(n,C.c_uint32)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
BASE,SIZE=0x3000000,0x60000
A,L,SOURCE,SOURCE2,SC,CONTAINER,REG,IR,AR,SR,IM,IMAGES,PID,TLS,META,SOUND=[BASE+0x1000+i*0x1000 for i in range(16)]
IM2,IM3,IMAGES2,IMAGES3,PID2,PID3=IM+0x200,IM+0x400,IMAGES+0x200,IMAGES+0x400,PID+0x400,PID+0x800
imageManagers={0x5294dc:IM,0x5294ec:IM2,0x529538:IM3}
DATA=BASE+0x20000;NEW=BASE+0x40000;SPLASHMETA=META+0x100
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
imageStart,imageEnd,_=next(v for v in u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(u.mem_read(imageStart,imageEnd-imageStart+1)))
heap=(C.c_uint8*SIZE)();ctx=Context();rng=random.Random(0x461a90);native=True;events=[];errors=[];cursor=0x40000;created=[];freed=[];mode=0;missingImage=False;missingANI=False;missingLogic=False;missingCreation=False;randomWord=0;realRNG=False;bindingName=0;calls=eventCount=0;selectedEntry=0
GLOBAL_START,GLOBAL_SIZE=0x520000,0x30000;seedGlobals=bytes(u.mem_read(GLOBAL_START,GLOBAL_SIZE))
lib=C.CDLL(str(WORK/'libImpactParticleRuntime.dylib'));lib.claw_impact_particle_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_impact_particle_entry.restype=C.c_uint32
lib.claw_actor_bind_default_image.argtypes=[C.POINTER(BindingState),C.POINTER(BindingContext),C.c_char_p,BindingDependency,C.c_void_p];lib.claw_actor_bind_default_image.restype=C.c_uint32
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(Record),C.POINTER(C.c_uint32)];lib.claw_animation_decode_record.restype=C.c_uint32
lib.claw_world_loot_next_random.argtypes=[C.POINTER(C.c_uint32)];lib.claw_world_loot_next_random.restype=C.c_uint32
lib.claw_actor_destruction_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Destruction),Host,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lib.claw_actor_destruction_entry.restype=C.c_uint32
sequences={0x5294fc:DATA,0x529524:DATA+0x2000,0x529510:DATA+0x4000,0x5266ec:DATA+0x6000}
def put(t,v):
 b=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def get(t,n=1):
 if not native:return m.read_words(t,n)
 if BASE<=t and t+n*4<=BASE+SIZE:return list(struct.unpack_from('<'+'I'*n,heap,t-BASE))
 return list(struct.unpack_from('<'+'I'*n,image,t-imageStart))
def globalBytes():
 if not native:return bytes(u.mem_read(GLOBAL_START,GLOBAL_SIZE))
 b=bytearray(seedGlobals)
 for addr,value in((0x5430c4,ctx.animation.animationDelta),(0x532c10,ctx.animation.audioPosition)):struct.pack_into('<I',b,addr-GLOBAL_START,value)
 return bytes(b)
def snapshot():return (hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),hashlib.sha256(globalBytes()).digest(),cursor,tuple(created),tuple(freed))
@Lookup
def lookup(_,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return None

def allocateBody(n):
 global cursor
 token=BASE+cursor;cursor+=max(512,(n+15)&~15);assert cursor<SIZE
 if n==0x1b4:created.append(token)
 return token
@Allocate
def allocate(_,n):events.append((0x4f63ec,0,(n,),snapshot()));return allocateBody(n)
@Free
def free(_,t):events.append((0x4f6428,0,(t,),snapshot()));freed.append(t)

def resource(receiver,name):
 if receiver==REG+16:return 0 if missingLogic else META if name==0x522570 else SPLASHMETA
 if receiver==IR+16:return 0 if missingImage else imageManagers.get(name,IM)
 if receiver==AR+16:return 0 if missingANI else sequences.get(name,0)
 return SOUND
@BindingDependency
def bindingDependency(s,c,event,_):
 e=event.contents;events.append((e.function,e.receiver,(bindingName,),snapshot()));return resource(e.receiver,bindingName)

def bind(actor,name):
 global bindingName
 bindingName=name;s=BindingState((C.c_uint32*128)(*get(actor,128)),(C.c_uint32*93)());c=BindingContext();c.imageRegistryToken=get(get(actor+0xc)[0]+0x10)[0]+16;manager=imageManagers.get(name,IM);first,last=get(manager+0x64,2);table=get(manager+0x14)[0];c.image=ImageBinding(manager,first,last,0,C.cast(C.addressof(heap)+table-BASE,C.POINTER(C.c_uint32)),last+1)
 text=bytes(u.mem_read(name,100)).split(b'\0')[0];assert lib.claw_actor_bind_default_image(C.byref(s),C.byref(c),text,bindingDependency,None);put(actor,list(s.actor));return 1

def rngResult():
 if not realRNG:return randomWord
 events.append((0x4a7dc0,0,(),snapshot()));return lib.claw_world_loot_next_random(C.cast(C.addressof(heap)+TLS+0x14-BASE,C.POINTER(C.c_uint32)))

def effect(f,receiver,args):
 if f==0x4f6286:return resource(receiver,args[0])
 if f==0x4a3050:return rngResult()if native else None if realRNG else randomWord
 if f==0x4c8da0:
  if missingCreation:return 0
  a=NEW;l=NEW+0x800;created.append(a);put(a+0xc,[SC]);put(a+0x4c,args[1:3]);put(a+0x64,[args[3]]);put(a+0x6c,[l]);put(l+0x10,[0x461a90 if args[4]==0x522570 else 0x461bc0]);put(l+0x1c,[0]);put(a+0x188,[0x513870,a,0,0,0,0,0,1,0,0,0x3f800000]);return a
 if f==0x4c7970:
  if mode&1 and native:return bind(receiver,args[0])
  manager=imageManagers.get(args[0],IM);put(receiver+0x170,[0 if missingImage else manager]);
  if not missingImage:put(receiver+0x16c,[get(manager+0x64)[0],manager,get(get(manager+0x14)[0]+4)[0]])
  if mode==4:put(SOURCE+8,[get(SOURCE+8)[0]|0x10000])
  return 1
 if f==0x4c79e0:
  put(receiver+0x190,[0 if missingANI else sequences[args[0]]])
  if mode==4:put(receiver+0x80,[SOURCE2]);put(SOURCE+0x4c,[get(SOURCE+0x4c)[0]+7])
  return 1
 if f==0x4c82a0:
  actor=receiver-0x188
  if mode==4:put(actor+0x1a4,[1]);put(actor+0x19c,[0])
  return 0
 if f in(0x4208e0,0x4c88e0):return 1
 raise AssertionError(('unrepresented impact dependency',hex(f),hex(receiver),args))
@Dependency
def dependency(c,event,_):
 e=event.contents;args=list(e.arguments[:e.argumentCount])
 if e.function==0x4c7970 and mode&1:return bind(e.receiver,args[0])
 events.append((e.function,e.receiver,tuple(args),snapshot()))
 try:return effect(e.function,e.receiver,args)or 0
 except BaseException as error:errors.append(error);return 0
@Invoke
def invoke(_,event):
 e=event;args=list(e.arguments[:e.argumentCount]);events.append((e.function,e.receiver,tuple(args),snapshot()))
 try:return effect(e.function,e.receiver,args)or 0
 except BaseException as error:errors.append(error);return 0
ctx.scene=Host(None,lookup,allocate,free,invoke,Clock())
COUNTS={0x4c8da0:6,0x4c7970:1,0x4c79e0:2,0x4c82a0:1,0x4a3050:0,0x4208e0:4,0x4c88e0:4}

def returned(pop,value):
 sp=u.reg_read(UC_X86_REG_ESP);u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+pop)
def hook(uc,address,size,_):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4f63ec:args=get(sp+4);events.append((address,0,tuple(args),snapshot()));returned(0,allocateBody(args[0]));return
 if address==0x4f6428:t=get(sp+4)[0];events.append((address,0,(t,),snapshot()));freed.append(t);returned(0,0);return
 if address==0x4f6286:
  name,out=get(sp+4,2);receiver=u.reg_read(UC_X86_REG_ECX);events.append((address,receiver,(name,),snapshot()));value=resource(receiver,name);put(out,[value]);returned(8,int(bool(value)));return
 if address==0x4a7dc0 and realRNG:events.append((address,0,(),snapshot()));returned(0,TLS);return
 if address not in COUNTS:return
 if address==0x4c8da0 and ctx.composeCreation:return
 if address==0x4c7970 and mode&1:return
 if address in(0x4c79e0,0x4c82a0)and ctx.composeAnimation:return
 args=get(sp+4,COUNTS[address]);receiver=0 if address==0x4a3050 else u.reg_read(UC_X86_REG_ECX);events.append((address,receiver,tuple(args),snapshot()));value=effect(address,receiver,args)
 if value is None:return
 returned(0 if address==0x4a3050 else len(args)*4,value)
u.hook_add(UC_HOOK_CODE,hook)

def prepare():
 global native,cursor,created,freed,mode,missingImage,missingANI,missingLogic,missingCreation,randomWord,realRNG
 native=True;cursor=0x40000;created=[];freed=[];mode=0;missingImage=missingANI=missingLogic=missingCreation=False;randomWord=0;realRNG=False;ctx.composeCreation=ctx.composeAnimation=ctx.fault=0;ctx.animation=Animation(18,70);C.memset(C.addressof(heap),0xa5,SIZE)
 for t,n in((A,128),(L,93),(SOURCE,128),(SOURCE2,128),(SC,32),(CONTAINER,11)):put(t,[rng.getrandbits(32)for _ in range(n)])
 put(A+0xc,[SC]);put(A+0x6c,[L]);put(A+0x80,[SOURCE]);put(A+0x4c,[350,270]);put(A+0x16c,[1,IM,PID]);put(A+0x188,[0x513870,A,0,0,0,0,0,1,0,0,0x3f800000]);put(L+0x10,[0x461a90]);put(L+0x1c,[0]);put(SOURCE+0x38,[1]);put(SOURCE+8,[0]);put(SOURCE+0x4c,[320,240]);put(SOURCE2+8,[0]);put(SOURCE2+0x38,[1]);put(SOURCE2+0x4c,[300,200]);put(SC+8,[CONTAINER]);put(SC+0x10,[IR]);put(SC+0x14,[REG]);put(SC+0x24,[IR,SR,AR]);put(SC+0x20,[IR]);put(CONTAINER+0xc,[SC]);put(CONTAINER+0x10,[0x5107bc,0,0,0,0,0,10]);put(META,[0,0,2,0,0x461a90]);put(SPLASHMETA,[0,0,2,0,0x461bc0]);put(IM+0x14,[IMAGES]);put(IM+0x64,[1,5]);put(IMAGES,[0]+[PID+i*0x80 for i in range(5)]);put(TLS+0x14,[rng.getrandbits(32)])
 for manager,table,pid,last in ((IM2,IMAGES2,PID2,5),(IM3,IMAGES3,PID3,7)):
  put(manager+0x14,[table]);put(manager+0x64,[1,last]);put(table,[0]+[pid+i*0x80 for i in range(last)])
 for seq in sequences.values():put(seq+12,[seq+0x100,1]);put(seq+0x100,[seq+0x200]);put(seq+0x200,[0,0,1,0,0,0,18,0,0,0,0,0])
 u.mem_write(BASE,bytes(heap))

def compare(f,args,receiver=0,label=None):
 global native,events,cursor,created,freed,calls,eventCount,selectedEntry
 native=True;before=bytes(heap);bg=globalBytes();old=(cursor,created[:],freed[:]);events=[];selectedEntry=f;out=C.c_uint32();aa=(C.c_uint32*len(args))(*args);ok=lib.claw_actor_destruction_entry(f,receiver,args[0],C.byref(Destruction(0,0,0x52e1c4)),ctx.scene,C.cast(C.byref(ctx,C.sizeof(Context)-4),C.POINTER(C.c_uint32)),C.byref(out))if f==0x4c9be0 else lib.claw_impact_particle_entry(f,receiver,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,(hex(f),label,ok,ctx.fault,errors)
 expected=bytes(heap);eg=globalBytes();ne=list(events);after=(cursor,created[:],freed[:]);native=False;u.mem_write(BASE,before);u.mem_write(GLOBAL_START,bg);cursor,created,freed=old;events=[]
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(args),*(v&0xffffffff for v in args)))
 except BaseException as error:raise AssertionError(('original',hex(f),label,hex(u.reg_read(UC_X86_REG_EIP)),events[-2:]))from error
 actual=bytes(u.mem_read(BASE,SIZE));assert actual==expected,('heap',hex(f),label,[(hex(BASE+i),expected[i:i+4].hex(),actual[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=actual[i:i+4]][:15]);assert events==ne,('events',hex(f),label,[(hex(e[0]),hex(e[1]),e[2])for e in ne],[(hex(e[0]),hex(e[1]),e[2])for e in events]);assert globalBytes()==eg;assert (cursor,created,freed)==after;assert ret==out.value,('EAX',hex(f),label,ret,out.value)
 native=True;C.memmove(C.addressof(heap),actual,SIZE);calls+=1;eventCount+=len(ne);return out.value

decodes=0;assetProfiles=[]
def installAssets():
 """Use file-decoded records with full original4d76e0 writes verified separately."""
 global native,events,decodes
 for name,seq in sequences.items():
  text=bytes(u.mem_read(name,100)).split(b'\0')[0].decode();file=ROOT/'App/GameData/GAME/ANIS'/f'{text[5:]}.ANI';data=file.read_bytes();header=struct.unpack_from('<8I',data);count,pathLength=header[3:5];position=32+pathLength
  put(seq+12,[seq+0x100,count]);put(seq+0x100,[seq+0x200+i*0x40 for i in range(count)])
  for index in range(count):
   encoded=data[position:];buf=(C.c_uint8*len(encoded)).from_buffer_copy(encoded);record=Record();length=C.c_uint32();used=lib.claw_animation_decode_record(buf,len(encoded),SOUND,C.byref(record),C.byref(length));assert used
   token=seq+0x200+index*0x40;seed=get(token,12);u.mem_write(token,struct.pack('<12I',*seed));u.mem_write(DATA+0x9000,encoded);events=[];native=False
   m.call(0x4d76e0,token,struct.pack('<2I',SR,DATA+0x9000));raw=m.read_words(token,12);native=True
   assert [record.flags]+[getattr(record,k)for k,_ in Record._fields_[1:-1]]+[record.event]==[raw[1]&0xffff]+raw[2:10]+[raw[11]]
   assert used==20+m.read_words(0x543174,1)[0];assert raw[0]==seed[0]and raw[10]==((seed[10]&0xffff0000)|struct.unpack_from('<H',encoded,18)[0]);put(token,raw);position+=used;decodes+=1
  assert position==len(data);assetProfiles.append({'name':text,'path':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'count':count,'imagePath':data[32:32+pathLength].rstrip(b'\0').decode()})
 # Actual Level1 hit resource image inventory determines the binder range.
 for resourceName in ('CLAWHIT','ENEMYHIT'):
  files=sorted((ROOT/'App/GameData/GAME/IMAGES'/resourceName).glob('*.PID'));assert len(files)==5
  for index,file in enumerate(files):
   data=file.read_bytes();token=(PID2 if resourceName=='CLAWHIT'else PID)+index*0x80;put(token,[0x513a70]+list(struct.unpack_from('<15I',data,4)))
   assetProfiles.append({'name':'GAME_'+resourceName,'path':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'opaquePreservationBytes':True})
 events=[]
