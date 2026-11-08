"""Checkpoint instruction oracle. Frozen loader/geometry reused read-only."""
from pathlib import Path
source=Path(__file__).with_name('elevator_logic_helpers.py').read_text().split('class LevelProfile')[0]
source=source.replace("WORK=ROOT/'work/elevator-agent'","WORK=ROOT/'work/checkpoint-agent'")
source=source.replace("'ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'","'CheckpointLogicRuntime.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp','AudioEvents.cpp','ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'")
source=source.replace('u.hook_add(UC_HOOK_CODE,original_hook)','checkpoint_base_hook=u.hook_add(UC_HOOK_CODE,original_hook)')
exec(compile(source,str(Path(__file__).with_name('elevator_logic_helpers.py')),'exec'),globals())
u.hook_del(checkpoint_base_hook)
class CheckpointGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','animationDelta','tick','timerRemaining','timerBonus','superKind','skipNextSuper','defaultHealth')]+[('defaultAmmo',C.c_uint32*4),('levelTreasures',C.c_uint32*10),('totalTreasures',C.c_uint32*10),('audioPosition',C.c_uint32)]
class CheckpointContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(CheckpointGlobals))]+[(n,C.c_uint32)for n in('composeAnimation','composeContactBinding','composeSave','composeSaveCache','fault')]
class CheckpointCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p),('localMask',C.c_uint32),('bufferCount',C.c_uint32),('buffers',C.POINTER(C.c_uint32)*2),('bufferWords',C.c_uint32*2)]
CheckpointDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(CheckpointContext),C.POINTER(CheckpointCall),C.c_void_p)
lib.claw_checkpoint_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(CheckpointContext),CheckpointDependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_checkpoint_entry.restype=C.c_uint32
GLOBAL_ADDRESSES=(0x5371fc,0x537e88,0x5430c4,0x537210,0x53c9f8,0x52c6e8,0x536efc,0x536f00,0x534cc8,0x534cf0,0x534cf4,0x534cf8,0x534cfc)+tuple(0x534d08+i*4 for i in range(20))+(0x532c10,)
REG,VT,CHEATS,SAVE,TM,CONTACT,EXISTING,ASSOC,AVT,CSTR,CACHE,OUT,COUNTS=[BASE+i*0x1000 for i in range(14,27)]
FORWARD,BACKWARD,TABLE_F,TABLE_B,RECORDS_F,RECORDS_B,FRAMES=[BASE+i*0x1000 for i in range(32,39)]
SAVE=BASE+0x40000
DECODE_DATA=0x10e8000
SOUND,POOL=BASE+0x27000,BASE+0x28000
g=CheckpointGlobals();context=CheckpointContext();packetToken=0;standaloneOutput=0;calendarIndex=0;allocationSuccess=resourceFound=True;stopAnimation=0;animationCode=0;modeResult=3;policy=0;saveResult=1;decoder_calls=0;calls=event_count=0
labels={0x522838:b'CheckpointAttack',0x5227e0:b'SuperCheckpointAttack',0x525378:b'GAME_CHECKPOINT_WAVE',0x525390:b'GAME_CHECKPOINT_RISE',0x5253a8:b'Your game has been saved',0x5253c4:b'Your game was not saved because you cheated!'}
def snap():return(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(g)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRESSES))
def set_global(field,value):
 if native:setattr(g,field,value)
 else:m.write_words(GLOBAL_ADDRESSES[[n for n,_ in CheckpointGlobals._fields_].index(field)],[value])
def effect(f,args):
 global calendarIndex
 if f==0x4f6286:
  if policy==1:put(A+0x8,[0xfeed1111]);put(A+0x6c,[PL]);put(L+0x10,[0x4232e0])
  if not resourceFound:return 0
  return META if args[0]in(0x522838,0x5227e0)else FORWARD if args[0]==0x525390 else BACKWARD if args[0]==0x525378 else SOUND
 if f==0x4f63ec:
  if policy==2:put(A+0x110,[0xabc]);put(CONTACT+0x64,[0x2468])
  return CONTACT if allocationSuccess else 0
 if f==0x4c79e0:
  put(A+0x1a4,[0]);put(A+0x19c,[0])
  if policy==3:put(A+0x6c,[PL]);put(PL+0x10,[0x4232e0]);set_global('timerBonus',17)
  return 1
 if f==0x4c82a0:put(A+0x1a4,[stopAnimation]);put(A+0x19c,[animationCode]);return 1
 if f==0x4000020:return modeResult
 if f==0x4a5c60:
  calendarIndex+=1;put(TM+0xc,[11+calendarIndex,4+calendarIndex,126+calendarIndex]);return TM
 if f==0x46d620:return saveResult
 if f==0x49ae60:return CACHE if resourceFound else 0
 if f in(0x4f6428,0x4000010,0x4000014,0x49a860,0x49a800,0x49bbc0,0x42af70,0x42abf0,0x4c88e0,0x4208e0):
  if f==0x4f6428 and policy==5:put(META+0x10,[0x4231a0]);put(AVT,[0x4000014])
  if f==0x49a860 and policy==4:put(CONFIG+0x14,[7]);return 0
  return 1
 raise AssertionError(hex(f))
def event(f,receiver,args,name=None,mask=0,buffers=()):events.append(((f,receiver,tuple(args),name,mask,tuple(tuple(b)for b in buffers)),snap()))
@CheckpointDependency
def dependency(_,e,user):
 e=e.contents;args=tuple(e.arguments[:e.argumentCount]);buffers=tuple(tuple(e.buffers[i][:e.bufferWords[i]])for i in range(e.bufferCount));event(e.function,e.receiver,args,e.name,e.localMask,buffers)
 if e.function==0x4a3b10:return 0x12345678
 return effect(e.function,args)
def oracle_payload():
 return tuple(m.read_words(packetToken,44))if packetToken else tuple(m.read_words(standaloneOutput,17))
def checkpoint_hook(uc,address,size,user):
 global packetToken
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x49a9d0 and currentFunction in(0x46d620,0x4231a0)and context.composeSave:
  output=m.read_words(sp+4,1)[0]
  if not packetToken:packetToken=output-80
 if address in(0x4c79e0,0x4c82a0)and not context.composeAnimation:
  n=2 if address==0x4c79e0 else 1;args=tuple(m.read_words(sp+4,n));event(address,receiver,args,labels.get(args[0])if address==0x4c79e0 else None);returned(4*n,effect(address,args));return
 if address==0x4c8060 and not context.composeContactBinding:
  args=tuple(m.read_words(sp+4,1));event(address,receiver,args,labels.get(args[0]));returned(4,1);return
 if address==0x46d620 and currentFunction!=0x46d620 and not context.composeSave:
  args=tuple(m.read_words(sp+4,3));event(address,receiver,args);returned(12,effect(address,args));return
 if address==0x4f6286:
  token,out=m.read_words(sp+4,2);name=bytes(u.mem_read(token,100)).split(b'\0')[0];event(address,receiver,(token,),name);value=effect(address,(token,));m.write_words(out,[value]);returned(8,int(bool(value)));return
 if address==0x4000020:event(address,receiver,());returned(0,modeResult);return
 if address in(0x4f63ec,0x4f6428,0x4000010,0x4000014):
  args=tuple(m.read_words(sp+4,1));event(address,receiver if address in(0x4000010,0x4000014)else 0,args);returned(4 if address in(0x4000010,0x4000014)else 0,effect(address,args));return
 if address==0x4f504f:
  global calendarTimeToken
  calendarTimeToken=m.read_words(sp+4,1)[0]
 if address in(0x4a3b10,0x4a5c60):
  stamp=m.read_words(calendarTimeToken,1)[0]
  if packetToken and stamp in(packetToken+80,packetToken+12):stamp=0
  event(address,0,(0,),None,0 if address==0x4a3b10 else 1,((stamp,),oracle_payload()))
  returned(0,0x12345678 if address==0x4a3b10 else effect(address,(0,)));return
 if address in(0x49a860,0x49a800)and currentFunction not in(0x49a860,0x49a800)and not context.composeSaveCache:
  n=3 if address==0x49a860 else 2;args=list(m.read_words(sp+4,n));buffer=m.read_words(args[1],44 if n==3 else 17);args[1]=0;event(address,receiver,args,None,2,(buffer,));returned(n*4,effect(address,args));return
 if address==0x49ae60 and (currentFunction in(0x49a860,0x49a800,0x49ae60,0x49a720)or context.composeSaveCache):return
 if address in(0x49ae60,0x49bbc0,0x42af70,0x42abf0,0x4c88e0,0x4208e0):
  n={0x49ae60:2,0x49bbc0:0,0x42af70:1,0x42abf0:0,0x4c88e0:4,0x4208e0:4}[address];args=tuple(m.read_words(sp+4,n));event(address,receiver,args,labels.get(args[0])if n else None);returned(n*4,effect(address,args));return
u.hook_add(UC_HOOK_CODE,checkpoint_hook)
u.mem_map(0x4000000,4096)
def setup(seed=0):
 global heap,g,context,native,policy,resourceFound,allocationSuccess,stopAnimation,animationCode,modeResult,saveResult,calendarIndex
 native=True;heap=(C.c_uint8*SIZE).from_buffer_copy(random.Random(seed).randbytes(SIZE));g=CheckpointGlobals();g.managerToken=MANAGER;g.playerToken=P;g.animationDelta=16;g.timerRemaining=35000;g.timerBonus=25000;g.superKind=0xabcdef;g.skipNextSuper=0;g.defaultHealth=99;g.defaultAmmo[:]=[10,20,30,40];g.levelTreasures[:]=range(10);g.totalTreasures[:]=range(10,20);context=CheckpointContext(host,C.pointer(g),0,1,1,0,0);policy=stopAnimation=calendarIndex=animationCode=0;modeResult=3;resourceFound=allocationSuccess=True;saveResult=1
 put(A+0xc,[SC]);put(A+0x6c,[L]);put(A+0x78,[0]);put(A+0x170,[IMAGE,FRAME]);put(A+0x164,[0]);put(A+0x110,[0]);put(A+0x4c,[100,200]);put(A+8,[0x40000]);put(L+0x1c,[0]);put(L+0x10,[0x422ef0]);put(P+0x6c,[PL]);put(PL+0x14,[PP]);put(P+0x4c,[321,654]);put(P+0x10c,[77]);put(PP+0x70,[21,22,23,24]);put(PP+0x80,[7]);put(PP+0x88,list(range(10)));put(PP+0xb0,list(range(10,20)));put(SC+0x14,[REG]);put(SC+0x2c,[REG]);put(MANAGER+0x2c,[CONFIG]);put(MANAGER+0x48,[CHEATS]);put(MANAGER+0x60,[SAVE]);put(MANAGER+0x64,[SAVE]);put(MANAGER+0xc0,[CSTR+8]);put(CSTR,[0]);put(CONFIG,[VT,MANAGER]);put(CONFIG+0x14,[1]);put(CONFIG+0x164,[200,0]);put(CONFIG+0x258,[0]);put(VT+16,[0x40af90]);put(CHEATS+0x128,[0]);put(META+0xc,[2,0x422ff0]);put(FRAME+0x18,[32,8,7,9]);put(A+0x1a4,[0]);put(A+0x19c,[0]);put(EXISTING,[0x513740]);put(EXISTING+0x14,[0,0]);put(ASSOC,[AVT]);put(AVT,[0x4000010]);put(IMAGE+0x14,[FRAMES]);put(IMAGE+0x64,[1,13]);put(FRAMES,[0]+[BASE+0x3a000+i*0x40 for i in range(13)]);put(TM,list(range(9)));put(CACHE,[0]);put(COUNTS,list(range(10)))
currentFunction=0

def compare(f,label,args=None,receiver=0,fault_expected=False):
 global native,calls,event_count,packetToken,standaloneOutput,calendarIndex,currentFunction
 native=True;before,bg=bytes(heap),bytes(g);events.clear();context.fault=0;calendarIndex=0;result=C.c_uint32();arguments=tuple(args if args is not None else(A,));argv=(C.c_uint32*len(arguments))(*(v&0xffffffff for v in arguments));assert lib.claw_checkpoint_entry(f,receiver,argv,len(arguments),C.byref(context),dependency,None,C.byref(result))
 assert bool(context.fault)==fault_expected,(label,'native fault',context.fault);expected,ee=snap(),list(events);afterHeap,afterGlobals=bytes(heap),bytes(g);native=False;events.clear();u.mem_write(BASE,before)
 for token,value in zip(GLOBAL_ADDRESSES,struct.unpack('<34I',bg)):m.write_words(token,[value])
 failed=False;ret=None;calendarIndex=packetToken=0;standaloneOutput=arguments[0]if f in(0x49a9d0,0x49aa40)else 0;currentFunction=f
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(arguments),*(v&0xffffffff for v in arguments)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'original fault',failed)
 actual=snap()
 if actual!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('full Checkpoint heap/globals')
 if events!=ee:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(('ordered full events',label,len(ee),len(events)))
 if not failed and f not in(0x422ff0,0x49a720):assert ret==result.value,(label,'EAX',ret,result.value)
 if not failed:assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(12 if f in(0x46d620,0x49a860)else 8 if f in(0x49ae60,0x49a800)else 0),(label,'calling convention')
 native=True;C.memmove(C.addressof(heap),afterHeap,SIZE);C.memmove(C.addressof(g),afterGlobals,len(afterGlobals));calls+=1;event_count+=len(ee);return result.value
callbacks={'Checkpoint':0x422ef0,'FirstSuperCheckpoint':0x4232c0,'SecondSuperCheckpoint':0x4232e0}
class Record(C.Structure):_fields_=[(n,C.c_uint32)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(Record),C.POINTER(C.c_uint32)];lib.claw_animation_decode_record.restype=C.c_uint32
def load_sequences():
 global decoder_calls
 for name,root,table,recordsToken in(('RISE',FORWARD,TABLE_F,RECORDS_F),('WAVE',BACKWARD,TABLE_B,RECORDS_B)):
  data=(ROOT/'work/original-disc-assets/GAME/ANIS/CHECKPOINT'/f'{name}.ANI').read_bytes();count,pathLength=struct.unpack_from('<2I',data,12);pos=32+pathLength;put(root+0xc,[table,count]);put(table,[recordsToken+i*0x40 for i in range(count)])
  for index in range(count):
   remaining=data[pos:];buf=(C.c_uint8*len(remaining)).from_buffer_copy(remaining);record=Record();length=C.c_uint32();used=lib.claw_animation_decode_record(buf,len(remaining),SOUND,C.byref(record),C.byref(length));assert used
   token=recordsToken+index*0x40;raw=words(token,12);m.write_words(token,raw);u.mem_write(DECODE_DATA,remaining);m.call(0x4d76e0,token,struct.pack('<2I',REG,DECODE_DATA));actual=m.read_words(token,12);assert [getattr(record,n)for n,_ in Record._fields_]==[actual[1]&0xffff]+actual[2:10]+[actual[11]];put(token,actual);pos+=used;decoder_calls+=1
  assert pos==len(data)

old_record_profile=record_profile
def record_profile(kind,data):
 s=ObjectState((C.c_uint32*128)(*words(A,128)),(C.c_uint32*93)(*words(L,93)));c=ObjectContext(SC,A,L,2,24576,6144,BASE+0xf000,(C.c_uint32*3)(BASE+0x10000,BASE+0x11000,BASE+0x12000),META,callbacks[kind],2);buf=(C.c_uint8*len(data)).from_buffer_copy(data);info=Info();assert lib.claw_world_object_load(buf,len(data),C.byref(s),C.byref(c),object_dependency,None,C.byref(info))==len(data)and info.created==1;put(A,list(s.actor));put(L,list(s.logic))
 stem='CHECKPOINTFLAG'if kind=='Checkpoint'else'SUPERCHECKPOINT';files=sorted((ROOT/'work/original-disc-assets/GAME/IMAGES'/stem).glob('*.PID'));assert len(files)==13
 for index,path in enumerate(files):
  _,_,width,height,x,y=struct.unpack_from('<6I',path.read_bytes());geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),width,height,x,y);token=BASE+0x3a000+index*0x40;put(token+0x10,[geometry.width,geometry.height,geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY])
 put(A+0x170,[IMAGE,BASE+0x3a000]);put(A+0x188,[0x513704,A,0,0,0,0,1,0,0,0,0x3f800000]);put(A+0x78,[0]);put(META+0x10,[0x422ff0 if kind=='Checkpoint'else 0x4231a0]);load_sequences();context.composeAnimation=1;return s,c
