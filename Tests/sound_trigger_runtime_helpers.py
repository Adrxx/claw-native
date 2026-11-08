"""Pinned original actor/ambient helper oracle; list/voice transport is explicit."""
import collections,ctypes as C,gzip,hashlib,io,json,random,struct,subprocess,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EDI,UC_X86_REG_ESI
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/sound-trigger-agent';U=C.c_uint32
sourceFiles=['SoundTriggerLogicRuntime.cpp','EnemySpeechRuntime.cpp','SpeechActor.cpp','AudioEvents.cpp','ActorResourceBindings.cpp','ActorDestruction.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s)for s in sourceFiles],'-o',str(WORK/'libSoundTrigger.dylib')],check=True);lib=C.CDLL(str(WORK/'libSoundTrigger.dylib'))
class Args(C.Structure):_fields_=[('words',U*9),('count',U)]
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,U)for n in('managerToken','playerToken','audioManagerToken','clawBusy','clawActorToken','enemyBusy','enemyActorToken','speakerToken','stageDelta')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals))]+[(n,U)for n in('masterVolume','triggerProfile','ambientProfile','composeSpeech','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*9),('argumentCount',U),('temporary',C.POINTER(U)),('temporaryWords',U)]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_sound_trigger_entry.argtypes=[U,U,Args,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x20000;A,L,P,PL,PP,CL,SL,SC,MANAGER,AMBIENT,AUDIO,SOUND,POOL,RECT,ENTRY=[BASE+n*0x400 for n in range(1,16)];ALLOC=BASE+0x10000
GLOBAL_ADDRS=(0x5371fc,0x537e88,0x532c0c,0x53c9a0,0x53c9a4,0x53c9a8,0x53c9ac,0x53c9b0,0x53720c,0x532c10,0x53c9b4,0x534810)
heap=(C.c_uint8*SIZE)();m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);u.mem_map(0x7000000,4096);m.write_words(0x546d58,[0x7000000]);m.write_words(0x546d5c,[0x7000100]);m.executed.clear()
imageStart,imageEnd,_=next(v for v in u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(u.mem_read(imageStart,imageEnd-imageStart+1)))
native=True;globals=Globals();context=Context();events=[];errors=[];cursor=ALLOC;calls=eventCount=0;allocationFailures=[];randomWords=[];randomIndex=0;mutation=0;replay=io.BytesIO();replayWriter=gzip.GzipFile(fileobj=replay,mode='wb',mtime=0);replayCases=0;replayFunctions=set();unsafeStop=0;unsafePrefixes=0;listFailure=False
ADAPTERS={0x4f63ec,0x4f6428,0x4f51c5,0x4f5212,0x4f5172,0x4b45f0,0x4b3dc0,0x4b3e30,0x4b3f40,0x4b3fe0,0x4b4110,0x4b4b80,0x4b4c10,0x4a3050}
def read(t,n):return bytes(heap[t-BASE:t-BASE+n])if native and BASE<=t and t+n<=BASE+SIZE else bytes(u.mem_read(t,n))
def write(t,b):assert BASE<=t and t+len(b)<=BASE+SIZE;(C.memmove(C.addressof(heap)+t-BASE,b,len(b))if native else u.mem_write(t,b))
def words(t,n=1):return list(struct.unpack('<'+'I'*n,read(t,n*4)))
def put(t,v):write(t,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
def globalBytes():return bytes(globals)+struct.pack('<3I',context.masterVolume,context.triggerProfile,context.ambientProfile)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRS)
def snap():return hashlib.sha256((bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+globalBytes()).digest()
@Lookup
def lookup(_,t,n):
 if t%4:return None
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return None
@Allocate
def allocate(_,n):
 global cursor
 events.append((('allocate',n),snap()))
 if allocationFailures and allocationFailures[0]==n:allocationFailures.pop(0);return 0
 t=cursor;cursor+=max(16,(n+15)&~15);assert cursor<BASE+SIZE;return t
@Free
def free(_,t):events.append((('free',t),snap()))
@Clock
def clock(_):errors.append('unexpected OS clock');return 0
def effect(f,t,a,temp=()):
 global cursor,randomIndex
 events.append((('call',f,t,a,temp),snap()))
 if f==0x4a3050:value=randomWords[randomIndex%len(randomWords)];randomIndex+=1;return value
 if f==0x4f51c5:
  if listFailure:return 0
  node=cursor;cursor+=16;tail=words(t+8)[0];put(node,[0,tail,a[0]])
  if tail:put(tail,[node])
  else:put(t+4,[node])
  put(t+8,[node]);put(t+12,[words(t+12)[0]+1]);return node
 if f==0x4f5212:
  node=a[0];nextNode,previous=words(node,2)
  if previous:put(previous,[nextNode])
  else:put(t+4,[nextNode])
  if nextNode:put(nextNode+4,[previous])
  else:put(t+8,[previous])
  put(t+12,[words(t+12)[0]-1]);return 0
 if f==0x4f5172:put(t+4,[0,0,0,0,0]);return 0
 if f in(0x4b45f0,0x4b3dc0,0x4b3e30,0x4b3f40,0x4b3fe0,0x4b4110,0x4b4b80,0x4b4c10):
  if mutation==1:put(A+0x108,[words(A+0x108)[0]+1]);put(PP+0x80,[words(PP+0x80)[0]+1])
  if mutation==2:put(MANAGER+16,[0]);put(AMBIENT+36,[0])
  if mutation==3:put(AMBIENT+40,[words(AMBIENT+40)[0]+7,words(AMBIENT+44)[0]+9])
  return 1
 raise AssertionError(('unknown dependency',hex(f),hex(t),a,temp))
@Dependency
def dependency(c,e,_):
 try:e=e.contents;return effect(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),tuple(e.temporary[:e.temporaryWords])if e.temporaryWords else())
 except BaseException as ex:errors.append(ex);context.fault=1;return 0
@Invoke
def invoke(_,e):
 try:return effect(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]))
 except BaseException as ex:errors.append(ex);context.fault=1;return 0
host=Host(None,lookup,allocate,free,invoke,clock);context.scene=host;context.globals=C.pointer(globals)
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 if unsafeStop and address==unsafeStop:u.emu_stop();return
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX)
 if address in(0x7000000,0x7000100):
  a=m.read_words(sp+4,2 if address==0x7000000 else 5)
  m.write_words(a[0],m.read_words(a[1],4)if address==0x7000000 else a[1:]);returned(len(a)*4,1);return
 if address==0x4f63ec:returned(0,allocate(None,m.read_words(sp+4,1)[0]));return
 if address==0x4f6428:free(None,m.read_words(sp+4,1)[0]);returned(0);return
 counts={0x4f51c5:1,0x4f5212:1,0x4f5172:0,0x4b45f0:4,0x4b3dc0:4,0x4b3e30:0,0x4b3f40:1,0x4b3fe0:3,0x4b4110:1,0x4b4b80:0,0x4b4c10:0,0x4a3050:0}
 if address in counts:n=counts[address];returned(n*4,effect(address,0 if address==0x4a3050 else t,tuple(m.read_words(sp+4,n))))
u.hook_add(UC_HOOK_CODE,hook)
def setup(seed=0,callback=0x48c1e0):
 global native,cursor,events,errors,allocationFailures,randomWords,randomIndex,mutation,listFailure
 native=True;pattern=random.Random(seed).randbytes(1024);write(BASE,pattern*(SIZE//1024));cursor=ALLOC;events=[];errors=[];allocationFailures=[];randomWords=[random.Random(seed+i).randrange(32768)for i in range(16)];randomIndex=0;mutation=0;listFailure=False
 C.memmove(C.addressof(globals),bytes(Globals(MANAGER,P,AUDIO,0,CL,0,0,0,16)),C.sizeof(globals));context.masterVolume=70;context.triggerProfile=51;context.ambientProfile=92;context.composeSpeech=1;context.fault=0
 put(A+0x6c,[L]);put(A+12,[SC]);put(A+8,[0x40000]);put(A+0x40,[0]);put(A+76,[100,200]);put(A+0x104,[100,2]);put(A+0x184,[SOUND]);put(A+0x118,[0x80000000,0,0,0]);put(A+0x128,[0xffffffc0,0xffffffc0,64,64]);put(A+0x138,[0x80000000,0,0,0]);put(L+16,[callback]);put(L+28,[0]);put(L+44,[0,0,0,0]);put(L+0x168,[0]);put(P+0x6c,[PL]);put(PL+0x14,[PP]);put(PL+28,[4]);put(P+76,[100,200]);put(PP+0x80,[3]);put(CL+0x6c,[SL]);put(SL+28,[5]);put(SOUND+16,[POOL]);put(POOL+40,[1000]);put(MANAGER+16,[AUDIO]);put(MANAGER+0x5c,[AMBIENT]);put(AMBIENT,[AUDIO,70,0x51000c,0,0,0,0,0,10,1,0,0]);put(AUDIO+44,[BASE+0x8000]);put(RECT,[10,20,300,400]);put(SC+0x28,[BASE+0x7000]);put(SC+0x2c,[BASE+0x7800])
def compare(f,t,args,label,void=False):
 global native,events,cursor,allocationFailures,randomIndex,calls,eventCount,replayCases
 before=bytes(heap);bg=globalBytes();old=(cursor,allocationFailures[:],randomIndex);events=[];context.fault=0;a=Args();a.count=len(args);a.words[:len(args)]=args;result=U();ok=lib.claw_enemy_speech_entry(f,t,a.words,len(args),C.byref(speechContext),speechDependency,None,C.byref(result)) if f==0x48c630 else lib.claw_sound_trigger_entry(f,t,a,C.byref(context),dependency,None,C.byref(result));assert ok and not context.fault and not errors,(label,'native',ok,context.fault,errors)
 expected=bytes(heap);eg=globalBytes();ee=events[:];after=(cursor,allocationFailures[:],randomIndex);native=False;u.mem_write(BASE,before)
 for address,value in zip(GLOBAL_ADDRS,struct.unpack('<12I',bg)):m.write_words(address,[value])
 cursor,allocationFailures,randomIndex=old;events=[];original=m.call(f,t,struct.pack('<'+'I'*len(args),*args));actual=bytes(u.mem_read(BASE,SIZE));ag=globalBytes()
 assert actual==expected,(label,'full heap',[(hex(BASE+i),hex(x),hex(y))for i,(x,y)in enumerate(zip(expected,actual))if x!=y][:20]);assert ag==eg,(label,'globals',struct.unpack('<12I',eg),struct.unpack('<12I',ag));assert events==ee,(label,'ordered full snapshots',[(e,es==s)for(e,es),(e2,s)in zip(events,ee)if e!=e2 or es!=s][:6],len(events),len(ee));assert after==(cursor,allocationFailures,randomIndex),(label,'external service state')
 if not void:assert original==result.value,(label,'meaningful EAX',original,result.value)
 assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(0 if t==0 else len(args)*4),(label,'original ESP',hex(u.reg_read(UC_X86_REG_ESP)))
 if not ee and(f not in replayFunctions or calls%17==0 or label.startswith('directed/')):replayWriter.write(struct.pack('<16I',f,t,*a.words,len(args),original,int(void),context.composeSpeech,0)+bg+eg+before+actual);replayCases+=1;replayFunctions.add(f)
 native=True;calls+=1;eventCount+=len(events);return result.value

class AnimationGlobals(C.Structure):_fields_=[('animationDelta',U),('audioPosition',U)]
class ObjectState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class ObjectContext(C.Structure):_fields_=[(n,U)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('worldWidth',C.c_int32),('worldHeight',C.c_int32),('registryToken',U),('layers',U*3),('entryToken',U),('entryCallback',U),('entryFlags',U)]
class ObjectCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U),('text',C.c_char_p)]
class ObjectInfo(C.Structure):_fields_=[('consumed',U),('created',U)]
ObjectDependency=C.CFUNCTYPE(U,C.POINTER(ObjectState),C.POINTER(ObjectContext),C.POINTER(ObjectCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(ObjectState),C.POINTER(ObjectContext),ObjectDependency,C.c_void_p,C.POINTER(ObjectInfo)]
lib.claw_actor_animation_entry.argtypes=[U,U,U,U,C.POINTER(AnimationGlobals),Host,C.POINTER(U),C.POINTER(U)]
NAME=BASE+0x5000;lookupResult=0
old_effect=effect
def effect(f,t,a,temp=()):
 if f==0x4f6286:
  events.append((('lookup',t,read(a[0],150).split(b'\0',1)[0]),snap()));return lookupResult
 return old_effect(f,t,a,temp)
old_hook=hook
def bindingHook(uc,address,size,user):
 if address!=0x4f6286:return
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX);name,out=m.read_words(sp+4,2);result=effect(address,t,(name,));m.write_words(out,[result]);returned(8,int(bool(result)))
u.hook_add(UC_HOOK_CODE,bindingHook);ADAPTERS.add(0x4f6286)
def bindSound(name,found,label):
 global native,events,lookupResult,calls,eventCount
 b=name.encode()+b'\0';write(NAME,b);lookupResult=SOUND if found else 0;before=bytes(heap);bg=globalBytes();events=[];a=AnimationGlobals(16,context.masterVolume);fault=U();result=U();assert lib.claw_actor_animation_entry(0x4c7a40,A,NAME,0,C.byref(a),host,C.byref(fault),C.byref(result))==1 and not fault.value
 expected=bytes(heap);ee=events[:];native=False;u.mem_write(BASE,before)
 for address,value in zip(GLOBAL_ADDRS,struct.unpack('<12I',bg)):m.write_words(address,[value])
 events=[];original=m.call(0x4c7a40,A,struct.pack('<I',NAME));assert original==result.value and bytes(u.mem_read(BASE,SIZE))==expected and events==ee,(label,'original auxiliary sound binding');native=True;calls+=1;eventCount+=len(events)
@ObjectDependency
def objectDependency(state,c,event,_):
 e=event.contents
 if e.function==0x4f6286:return ENTRY
 if e.function in(0x4c7970,0x4c7900,0x4c79e0,0x4c7a40,0x4f4630):return 0
 raise AssertionError(('unrepresented WWD fixture dependency',hex(e.function)))
def sourceRecord(record,callback,flags):
 state=ObjectState((U*128)(*words(A,128)),(U*93)(*words(L,93)));c=ObjectContext(SC,A,L,2,24576,6144,BASE+0x6400,(U*3)(0,0,0),ENTRY,callback,flags);v=record['words'];ss=record['strings'];raw=struct.pack('<71I',*v)+b''.join(s.encode()+b'\0'for s in ss)
 # JSON strings remove stored NUL padding; preserve exact original raw record
 # lengths by rebuilding each originally sized string, not changing word sizes.
 raw=struct.pack('<71I',*v)+b''.join(s.encode()+bytes(n-len(s))for s,n in zip(ss,v[1:5]));assert hashlib.sha256(raw).hexdigest()==record['rawSHA256']
 data=(C.c_uint8*len(raw)).from_buffer_copy(raw);info=ObjectInfo();assert lib.claw_world_object_load(data,len(raw),C.byref(state),C.byref(c),objectDependency,None,C.byref(info))==len(raw)and info.created
 put(A,list(state.actor));put(L,list(state.logic))
def assets():
 # Read-only format inventory, not an emulated REZ transport implementation.
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';out={}
 def w(t):return struct.unpack_from('<I',blob,t)[0]
 def walk(at,size,path=()):
  end=at+size
  while at<end:
   kind,target,length=w(at),w(at+4),w(at+8);start=at+(16 if kind else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode()
   if kind:walk(target,length,path+(name,));at=nul+1
   else:ext=blob[at+20:at+24].split(b'\0')[0][::-1].decode();out['/'.join(path+(name+'.'+ext,))]=blob[target:target+length];at=nul+2
 walk(w(131),w(135));return out

def failure(f,t,args,label,stop,fault):
 global native,events,cursor,allocationFailures,randomIndex,unsafeStop,unsafePrefixes
 before=bytes(heap);bg=globalBytes();old=(cursor,allocationFailures[:],randomIndex);events=[];context.fault=0;a=Args();a.count=len(args);a.words[:len(args)]=args;result=U();assert lib.claw_sound_trigger_entry(f,t,a,C.byref(context),dependency,None,C.byref(result))==0 and context.fault==fault
 expected=bytes(heap);eg=globalBytes();ee=events[:];after=(cursor,allocationFailures[:],randomIndex);native=False;u.mem_write(BASE,before)
 for address,value in zip(GLOBAL_ADDRS,struct.unpack('<12I',bg)):m.write_words(address,[value])
 cursor,allocationFailures,randomIndex=old;events=[];unsafeStop=stop
 try:m.call(f,t,struct.pack('<'+'I'*len(args),*args))
 except AssertionError:assert u.reg_read(UC_X86_REG_EIP)==stop,(label,'unsafe original prefix stop')
 else:raise AssertionError((label,'original unexpectedly returned'))
 finally:unsafeStop=0;m.write_words(0,[0])
 assert bytes(u.mem_read(BASE,SIZE))==expected and globalBytes()==eg and events==ee and after==(cursor,allocationFailures,randomIndex),(label,'unsafe original prefix buffers/events')
 native=True;context.fault=0;unsafePrefixes+=1;ADAPTERS.add(stop)

lib.claw_sound_trigger_construct_manager.argtypes=[U,C.POINTER(Context)]
constructorBlocks=0
def constructManager(seed):
 global native,constructorBlocks
 setup(seed);before=bytes(heap);assert lib.claw_sound_trigger_construct_manager(AMBIENT,C.byref(context))==1;expected=bytes(heap);native=False;u.mem_write(BASE,before);u.reg_write(UC_X86_REG_EDI,AMBIENT);u.reg_write(UC_X86_REG_ESI,0);u.reg_write(UC_X86_REG_ESP,m.stack);u.emu_start(0x4262c4,0x4262d7,count=1000);assert u.reg_read(UC_X86_REG_EIP)==0x4262d7 and u.reg_read(UC_X86_REG_ESP)==m.stack and bytes(u.mem_read(BASE,SIZE))==expected
 native=True;constructorBlocks+=1

class SpeechContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('nameHint',C.c_char_p),('fault',U)]
class SpeechCall(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*4),('name',C.c_char_p)]
SpeechDependency=C.CFUNCTYPE(U,C.POINTER(SpeechContext),C.POINTER(SpeechCall),C.c_void_p)
@SpeechDependency
def speechDependency(c,e,_):
 try:e=e.contents;return effect(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]))
 except BaseException as ex:errors.append(ex);speechContext.fault=1;return 0
speechContext=SpeechContext(host,C.pointer(globals),None,0)
lib.claw_enemy_speech_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(SpeechContext),SpeechDependency,C.c_void_p,C.POINTER(U)]
