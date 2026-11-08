"""Additive Peg oracle, reusing frozen loader/geometry/profile fixtures read-only."""
from pathlib import Path
source=Path(__file__).with_name('elevator_logic_helpers.py').read_text().replace("WORK=ROOT/'work/elevator-agent'","WORK=ROOT/'work/peg-agent'")
source=source.replace("'ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'","'PegLogicRuntime.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp','AudioEvents.cpp','ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'")
source=source.replace('u.hook_add(UC_HOOK_CODE,original_hook)','peg_base_hook=u.hook_add(UC_HOOK_CODE,original_hook)')
source=source.replace('META,callbacks[kind],1)','META,callbacks[kind],2)')
exec(compile(source,str(Path(__file__).with_name('elevator_logic_helpers.py')),'exec'),globals())
class PegGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('defaultsToken','playerToken','tick','animationDelta','gate','audioManagerToken','audioVolume','wrapperMode')]
class PegContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(PegGlobals)),('composeAnimation',C.c_uint32),('fault',C.c_uint32)]
class PegCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p)]
PegDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(PegContext),C.POINTER(PegCall),C.c_void_p)
lib.claw_peg_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(PegContext),PegDependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_peg_entry.restype=C.c_uint32
GLOBAL_ADDRESSES=(0x537960,0x537e88,0x537210,0x5430c4,0x53725c,0x532c0c,0x532c10,0x53ebf0)
REG=BASE+0x14000;COLLISION=BASE+0x15000;PLANE=BASE+0x16000;SOUND=BASE+0x17000;POOL=BASE+0x18000;FRAMES=BASE+0x19000
FORWARD,BACKWARD=BASE+0x20000,BASE+0x21000;TABLE_F,TABLE_B=BASE+0x22000,BASE+0x23000;RECORDS_F,RECORDS_B=BASE+0x24000,BASE+0x28000;DECODE_DATA=0x10e8000
g=PegGlobals();context=PegContext();compose=0;stopAnimation=0;animationImage=6;policy=0;resourceFound=True;calls=event_count=decoder_calls=0
labels={0x52dd04:b'GAME_FORWARD50',0x52dd14:b'GAME_BACKWARD50',0x52dd24:b'LEVEL_PEGCRUMBLE',0x528a3c:b'LEVEL_PEGSLIDE'}
def snap():return(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(g)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRESSES))
def effect(token):
 if policy==1:put(A+0x170,[IMAGE]);put(IMAGE+0x64,[3,17]);put(DEFAULTS+0x78,[-11,-12,13,14])
 if policy==2:put(A+0x64,[123]);put(A+8,[0xfeed0001]);put(L+0x10,[0x49e7f0])
 if not resourceFound:return 0
 return FORWARD if token==0x52dd04 else BACKWARD if token==0x52dd14 else SOUND
@PegDependency
def dependency(_,e,user):
 e=e.contents;events.append(((e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name),snap()))
 if e.function==0x4f6286:return effect(e.arguments[0])
 if e.function==0x4c79e0:put(A+0x1a4,[0]);put(A+0x19c,[0]);return 1
 if e.function==0x4c82a0:put(A+0x16c,[animationImage]);put(A+0x1a4,[stopAnimation]);put(A+0x19c,[0]);return 1
 assert e.function in(0x4b45f0,0x4c88e0);return 1
u.hook_del(peg_base_hook)
def peg_hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if not context.composeAnimation and address in(0x4c79e0,0x4c82a0):
  n=2 if address==0x4c79e0 else 1;args=tuple(m.read_words(sp+4,n));events.append(((address,receiver,args,labels.get(args[0])if address==0x4c79e0 else None),snap()))
  if address==0x4c79e0:put(A+0x1a4,[0]);put(A+0x19c,[0])
  else:put(A+0x16c,[animationImage]);put(A+0x1a4,[stopAnimation]);put(A+0x19c,[0])
  returned(n*4,1);return
 if address==0x4f6286:
  token,out=m.read_words(sp+4,2);name=bytes(u.mem_read(token,100)).split(b'\0')[0];events.append(((address,receiver,(token,),name),snap()));value=effect(token);m.write_words(out,[value]);returned(8,int(bool(value)));return
 if address in(0x4b45f0,0x4c88e0):
  args=tuple(m.read_words(sp+4,4));events.append(((address,receiver,args,None),snap()));returned(16,1);return
u.hook_add(UC_HOOK_CODE,peg_hook)
old_setup=setup
def setup(seed=0):
 global g,context,compose,policy,stopAnimation,resourceFound
 old_setup(seed);g=PegGlobals(DEFAULTS,P,0,16,0,1,100,0xdeadbeef);context=PegContext(host,C.pointer(g),0,0);compose=policy=stopAnimation=0;resourceFound=True
 put(SC+0x28,[REG]);put(SC+0x2c,[REG]);put(REG+0xc,[SC]);put(REG+0x30,[0]);put(SC+0x24,[COLLISION]);put(COLLISION+0x5c,[PLANE]);put(SOUND+0x10,[POOL]);put(A+0x108,[0]);put(A+0x1a4,[0]);put(A+0x19c,[0]);put(A+0x18c,[A]);put(A+0x1a0,[1]);put(IMAGE+0x14,[FRAMES]);put(IMAGE+0x64,[1,12]);put(FRAMES,[0]+[BASE+0x1a000+i*0x40 for i in range(12)]);put(L+0x10,[0x49d860]);put(DEFAULTS+0x58,[-24,-8,24,32]);put(DEFAULTS+0x78,[-24,-46,24,32])
def compare(f,label,args=None,fault_expected=False,receiver=0):
 global native,calls,event_count
 native=True;before,bg=bytes(heap),bytes(g);events.clear();context.fault=0;result=C.c_uint32();arguments=tuple(args if args is not None else(A,));argv=(C.c_uint32*len(arguments))(*(v&0xffffffff for v in arguments));assert lib.claw_peg_entry(f,receiver,argv,len(arguments),C.byref(context),dependency,None,C.byref(result))
 assert bool(context.fault)==fault_expected,(label,'native fault',context.fault);expected,ee=snap(),list(events);afterHeap,afterGlobals=bytes(heap),bytes(g);native=False;events.clear();u.mem_write(BASE,before)
 for token,value in zip(GLOBAL_ADDRESSES,struct.unpack('<8I',bg)):m.write_words(token,[value])
 failed=False;ret=None
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(arguments),*(v&0xffffffff for v in arguments)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'original fault',failed)
 actual=snap()
 if actual!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('full Peg heap/globals')
 if events!=ee:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(('ordered full events',label,len(ee),len(events)))
 if not failed and f!=0x49e470:assert ret==result.value,(label,'EAX',ret,result.value)
 if not failed:assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(16 if f==0x4ca610 else 0),(label,'calling convention')
 native=True;C.memmove(C.addressof(heap),afterHeap,SIZE);C.memmove(C.addressof(g),afterGlobals,32);calls+=1;event_count+=len(ee);return result.value
callbacks={'CrumblingPeg':0x49d860,'TogglePeg':0x49e4e0,'TogglePeg2':0x49e7b0,'TogglePeg3':0x49e7d0,'TogglePeg4':0x49e7f0}
class Record(C.Structure):_fields_=[(n,C.c_uint32)for n in('flags','imageCommand','controlCommand','movementCommand','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(Record),C.POINTER(C.c_uint32)];lib.claw_animation_decode_record.restype=C.c_uint32

def load_sequences():
 global decoder_calls
 for name,root,table,recordsToken in(('FORWARD50',FORWARD,TABLE_F,RECORDS_F),('BACKWARD50',BACKWARD,TABLE_B,RECORDS_B)):
  data=(ROOT/'work/original-disc-assets/GAME/ANIS'/f'{name}.ANI').read_bytes();count,pathLength=struct.unpack_from('<2I',data,12);pos=32+pathLength;put(root+0xc,[table,count]);put(table,[recordsToken+i*0x40 for i in range(count)])
  for index in range(count):
   remaining=data[pos:];buf=(C.c_uint8*len(remaining)).from_buffer_copy(remaining);record=Record();length=C.c_uint32();used=lib.claw_animation_decode_record(buf,len(remaining),0,C.byref(record),C.byref(length));assert used
   token=recordsToken+index*0x40;raw=words(token,12);m.write_words(token,raw);u.mem_write(DECODE_DATA,remaining);m.call(0x4d76e0,token,struct.pack('<2I',REG,DECODE_DATA));actual=m.read_words(token,12);assert [getattr(record,n)for n,_ in Record._fields_]==[actual[1]&0xffff]+actual[2:10]+[actual[11]];put(token,actual);pos+=used;decoder_calls+=1
  assert pos==len(data)
old_record_profile=record_profile
def record_profile(kind,data):
 s,c=old_record_profile(kind,data);source_defaults(1);stem='CRUMBLINGPEG'if kind=='CrumblingPeg'else'PEG'
 files=sorted((ROOT/'Original/cd-assets/LEVEL1/IMAGES'/stem).glob('*.PID'));assert len(files)==12
 for index,path in enumerate(files):
  _,_,width,height,x,y=struct.unpack_from('<6I',path.read_bytes());geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),width,height,x,y);token=BASE+0x1a000+index*0x40;put(token+0x10,[geometry.width,geometry.height,geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY])
 put(A+0x170,[IMAGE]);put(IMAGE+0x64,[1,12]);put(A+0x188,[0x513704,A,0,0,0,0,1,0,0,0,0x3f800000]);load_sequences();context.composeAnimation=1;return s,c
