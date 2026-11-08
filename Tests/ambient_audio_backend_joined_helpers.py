"""Frozen ambient actors/manager connected to real recovered backend/list bodies."""
import ambient_audio_backend_runtime_helpers as h
C=h.C;U=C.c_uint32
class Arguments(C.Structure):_fields_=[('words',U*9),('count',U)]
class Globals(C.Structure):_fields_=[(n,U)for n in('managerToken','playerToken','audioManagerToken','clawBusy','clawActorToken','enemyBusy','enemyActorToken','speakerToken','stageDelta')]
class Context(C.Structure):_fields_=[('scene',h.Host),('globals',C.POINTER(Globals))]+[(n,U)for n in('masterVolume','triggerProfile','ambientProfile','composeSpeech','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*9),('argumentCount',U),('temporary',C.POINTER(U)),('temporaryWords',U)]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
h.lib.claw_sound_trigger_entry.argtypes=[U,U,Arguments,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(U)];h.lib.claw_sound_trigger_entry.restype=U
GAME,AMBIENT,AUDIO,ACTOR,LOGIC,SOUND=h.BASE+0xa000,h.BASE+0xb000,h.BASE+0xc000,h.BASE+0xd000,h.BASE+0xe000,h.BASE+0xf000
sg=Globals();sc=Context();sc.scene=h.ctx.scene;sc.globals=C.pointer(sg)
addresses=[0x5371fc,0x537e88,0x532c0c,0x53c9a0,0x53c9a4,0x53c9a8,0x53c9ac,0x53c9b0,0x53720c,0x532c10,0x53c9b4,0x534810]
randomIndex=0;randomWords=[7,41,199,999,300];joinedCalls=0;joinedEvents=0
@Dependency
def dependency(context,event,_):
 global randomIndex
 e=event.contents;a=list(e.arguments[:e.argumentCount]);result=U();aa=(U*len(a))(*a)
 if e.function==0x4a3050:
  h.events.append((e.function,0,(),0,None,h.snapshot()));value=randomWords[randomIndex%len(randomWords)];randomIndex+=1;return value
 ok=h.lib.claw_ambient_audio_backend_entry(e.function,e.receiver,aa,len(a),C.byref(h.ctx),h.dependency,None,C.byref(result))
 if not ok:sc.fault=h.ctx.fault or 2
 return result.value

def native(fn,receiver,args,result):
 a=Arguments();a.count=len(args);a.words[:len(args)]=args;ok=h.lib.claw_sound_trigger_entry(fn,receiver,a,C.byref(sc),dependency,None,C.byref(result));return bool(ok and not sc.fault)
def globals(b):
 values=[getattr(sg,n)for n,_ in Globals._fields_]+[sc.masterVolume,sc.triggerProfile,sc.ambientProfile]
 for t,v in zip(addresses,values):h.struct.pack_into('<I',b,t-h.GLOBAL_START,v)

# Pure CopyRect / SetRect platform transport; actual source caller body runs.
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
COPYRECT,SETRECT=0x10fff00,0x10fff10
h.u.mem_write(COPYRECT,b"\xc3");h.u.mem_write(SETRECT,b"\xc3")
h.m.write_words(0x546d58,[COPYRECT]);h.m.write_words(0x546d5c,[SETRECT]);h.seedGlobals=bytes(h.u.mem_read(h.GLOBAL_START,h.GLOBAL_SIZE))
def hook(uc,address,size,_):
 global randomIndex
 if address==0x4a3050:
  h.events.append((address,0,(),0,None,h.snapshot()));value=randomWords[randomIndex%len(randomWords)];randomIndex+=1;h.returned(0,value);return
 if address not in(COPYRECT,SETRECT):return
 args=h.m.read_words(h.u.reg_read(UC_X86_REG_ESP)+4,2 if address==COPYRECT else 5);h.put(args[0],h.get(args[1],4)if address==COPYRECT else args[1:]);h.returned(len(args)*4,1)
h.u.hook_add(UC_HOOK_CODE,hook)
def prepare():
 global randomIndex
 h.prepare();sg.managerToken=GAME;sg.playerToken=ACTOR;sg.audioManagerToken=AUDIO;sg.stageDelta=18;sg.clawBusy=sg.enemyBusy=sg.clawActorToken=sg.enemyActorToken=sg.speakerToken=0
 sc.masterVolume=70;sc.triggerProfile=51;sc.ambientProfile=92;sc.composeSpeech=0;sc.fault=0;randomIndex=0
 h.put(GAME+0x10,[AUDIO]);h.put(GAME+0x5c,[AMBIENT]);h.put(AUDIO+0x2c,[h.MANAGER]);h.put(AMBIENT,[AUDIO,70,0x51000c,0,0,0,0,0,10,1,0,0]);h.put(SOUND+0x10,[h.VOICE]);h.put(ACTOR+0x6c,[LOGIC]);h.put(ACTOR+0x184,[SOUND]);h.extraGlobals=globals;h.nativeOverride=native

def compare(fn,args=(),receiver=0,label=None,void=False):
 global randomIndex,joinedCalls,joinedEvents
 oldRandom=randomIndex;old=(bytes(sg),sc.masterVolume,sc.triggerProfile,sc.ambientProfile,sc.fault)
 # Source ordinary compare reruns original after native. Restore RNG cursor
 # exactly at that transition while retaining frozen native global result.
 nativeEntry=h.nativeOverride
 def wrapped(fn,t,a,result):return nativeEntry(fn,t,a,result)
 oldMCall=h.m.call
 def original(fn,t,a=b''):
  global randomIndex
  expected=randomIndex;randomIndex=oldRandom
  value=oldMCall(fn,t,a)
  assert randomIndex==expected,('RNG order',label)
  return value
 h.m.call=original
 try:result=h.compare(fn,args,receiver,label,void)
 finally:h.m.call=oldMCall
 joinedCalls+=1;joinedEvents=h.eventCount;return result

class ObjectState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class ObjectContext(C.Structure):_fields_=[(n,U)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('worldWidth',C.c_int32),('worldHeight',C.c_int32),('registryToken',U),('layers',U*3)]+[(n,U)for n in('entryToken','entryCallback','entryFlags')]
class ObjectCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U),('text',C.c_char_p)]
class Info(C.Structure):_fields_=[('consumed',U),('created',U)]
ObjectDependency=C.CFUNCTYPE(U,C.POINTER(ObjectState),C.POINTER(ObjectContext),C.POINTER(ObjectCall),C.c_void_p)
h.lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(ObjectState),C.POINTER(ObjectContext),ObjectDependency,C.c_void_p,C.POINTER(Info)]
@ObjectDependency
def objectDependency(s,c,event,_):
 e=event.contents
 if e.function==0x4f6286:return SOUND
 if e.function==0x4c7a40:s.contents.actor[0x184//4]=SOUND;return 1
 if e.function in(0x4c7970,0x4c7900,0x4c79e0,0x4f4630):return 1
 raise AssertionError(('unrepresented world resource boundary',hex(e.function)))
def sourceRecord(row):
 state=ObjectState((U*128)(*h.get(ACTOR,128)),(U*93)(*h.get(LOGIC,93)));callback={'AmbientSound':0x402cc0,'GlobalAmbientSound':0x402ca0,'SpotAmbientSound':0x402e20}[row['strings'][1]]
 c=ObjectContext(GAME,ACTOR,LOGIC,GAME,24576,6144,GAME,(U*3)(0,0,0),SOUND,callback,2);v=row['words'];ss=row['strings'];raw=h.struct.pack('<71I',*v)+b''.join(s.encode()+bytes(n-len(s))for s,n in zip(ss,v[1:5]));assert h.hashlib.sha256(raw).hexdigest()==row['rawSHA256'];data=(C.c_uint8*len(raw)).from_buffer_copy(raw);info=Info();assert h.lib.claw_world_object_load(data,len(raw),C.byref(state),C.byref(c),objectDependency,None,C.byref(info))==len(raw)and info.created
 h.put(ACTOR,list(state.actor));h.put(LOGIC,list(state.logic));return callback
