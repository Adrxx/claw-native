"""Additive checkpoint timer oracle with frozen resource and common actor fixtures."""
from pathlib import Path
source=Path(__file__).with_name('elevator_logic_helpers.py').read_text().split('class LevelProfile')[0]
source=source.replace("WORK=ROOT/'work/elevator-agent'","WORK=ROOT/'work/checkpoint-timer-agent'")
source=source.replace("'ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'","'CheckpointTimerRuntime.cpp','ActorDestruction.cpp','PickupPointsRuntime.cpp','SceneActorRuntime.cpp','GameTiming.cpp','ActorAnimationRuntime.cpp','AnimationEngine.cpp','AnimationOperations.cpp','AudioEvents.cpp','ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'")
source=source.replace('u.hook_add(UC_HOOK_CODE,original_hook)','timer_base_hook=u.hook_add(UC_HOOK_CODE,original_hook)')
exec(compile(source,str(Path(__file__).with_name('elevator_logic_helpers.py')),'exec'),globals())
u.hook_del(timer_base_hook)
class TimerGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','stageDelta','animationDelta','remaining','initialDuration','expired','multiStatsToken','left','top','right','bottom','audioPosition')]
class TimerContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(TimerGlobals))]+[(n,C.c_uint32)for n in('composeAnimation','composeImages','composeHierarchy','composeFormatting','fault')]
class TimerCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*8),('name',C.c_char_p),('localMask',C.c_uint32),('buffer',C.c_void_p),('bufferBytes',C.c_uint32)]
TimerDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(TimerContext),C.POINTER(TimerCall),C.c_void_p)
lib.claw_checkpoint_timer_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(TimerContext),TimerDependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_checkpoint_timer_entry.restype=C.c_uint32
GLOBAL_ADDRESSES=(0x5371fc,0x537e88,0x53720c,0x5430c4,0x53c9f8,0x52c6e4,0x53c9f4,0x53c9fc,0x5370c8,0x5370cc,0x5370d0,0x5370d4,0x532c10)
STATS,STATSL,HUD,VT,DISPLAY,DVT,APP,TIMEIMG,NUMIMG,TIMEFRAME,TIMEFRAMES,NUMFRAMES,NUMGEOMETRY,DIGMETA,STATMETA,FRAMEMETA=[BASE+i*0x1000 for i in range(14,30)]
D=[BASE+0x20000+i*0x1000 for i in range(10)];DL=[BASE+0x30000+i*0x1000 for i in range(10)];DH=[BASE+0x40000+i*0x1000 for i in range(10)]
CONTAINER=BASE+0x3b000
FRAME_METADATA=[FRAMEMETA+i*32 for i in range(5)]
FRAME_NAMES=[0x5229d8,0x5229cc,0x5229c0,0x5229b4,0x5229a8]
FRAME_CALLBACKS=[0x4908b0,0x490f80,0x490c50,0x4912a0,0x491540]
ALLOC_BASE=BASE+0x50000;nextAllocation=ALLOC_BASE;allocationIndex=childIndex=0;failAllocation=0;failChild=0;policy=0;resourceFound=True;hudPresent=True;virtualModes=[3];calls=event_count=0;originalFormattingCalls=0;g=TimerGlobals();context=TimerContext()
labels={0x52c8b4:b'GAME_INTERFACE_TIME',0x52c700:b'GAME_INTERFACE_SCORENUMBERS',0x522994:b'StatusNumberDigit',0x52297c:b'MultiStats',0x5229d8:b'ScoreFrame',0x5229cc:b'WeaponFrame',0x5229c0:b'HealthFrame',0x5229b4:b'LivesFrame',0x5229a8:b'TimerFrame',0x52c6f8:b'%010i'}
def snap():return(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(g)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRESSES))
def set_global(field,value):
 if native:setattr(g,field,value)
 else:m.write_words(GLOBAL_ADDRESSES[[n for n,_ in TimerGlobals._fields_].index(field)],[value])
def allocate(size):
 global allocationIndex,nextAllocation
 allocationIndex+=1
 if allocationIndex==failAllocation:return 0
 out=nextAllocation;nextAllocation+=(size+15)&~15
 if policy==1:put(A+8,[0x2468]);put(META+0x10,[0x4919f0]);put(A+0x64,[321])
 assert nextAllocation<BASE+SIZE
 return out
def effect(f,receiver,args):
 global childIndex
 if f==0x4f63ec:return allocate(args[0])
 if f==0x4f6286:
  if not resourceFound:return 0
  token=args[0]
  if token==0x52c8b4:return TIMEIMG
  if token==0x52c700:return NUMIMG
  if token==0x522994:return DIGMETA
  if token==0x52297c:return STATMETA
  return FRAME_METADATA[FRAME_NAMES.index(token)]
 if f in(0x4c7900,0x4c7970):
  root=TIMEIMG if args[0]==0x52c8b4 else NUMIMG
  put(receiver+0x170,[root]);index=args[1]if len(args)>1 else(1 if root==TIMEIMG else 0);put(receiver+0x16c,[index]);put(receiver+0x174,[TIMEFRAME if root==TIMEIMG else NUMGEOMETRY+index*0x40]);return 1
 if f==0x4d3e50:
  childIndex+=1
  if failChild==childIndex:return 0
  out=D[childIndex-1];put(out+0x64,[args[3]]);return out
 if f==0x4c82a0:return 0
 if f in(0x4f6428,0x4c9be0,0x4c9fc0,0x4c9e00,0x546d50,0x417b00,0x4000010,0x4000020):
  if f==0x4000010 and policy==2:put(HUD+0x24,[D[0]]);put(D[0]+0x40,[0xfeed0000]);set_global('remaining',1499)
  if f==0x546d50 and policy==3:put(A+0x6c,[STATSL]);put(L+0x18,[0]);set_global('playerToken',0)
  if f==0x4000020:return virtualModes.pop(0)if len(virtualModes)>1 else virtualModes[0]
  return 0
 # Remaining MultiStats leaves remain exact registered callback services.
 if f in FRAME_CALLBACKS:return 1
 raise AssertionError((hex(f),hex(receiver),args))
def event(f,receiver,args,name=None,mask=0,buffer=None):events.append(((f,receiver,tuple(args),name,mask,buffer),snap()))
@TimerDependency
def dependency(_,e,user):
 e=e.contents;args=tuple(e.arguments[:e.argumentCount]);buffer=C.string_at(e.buffer,e.bufferBytes)if e.buffer else None;event(e.function,e.receiver,args,e.name,e.localMask,buffer)
 if e.function==0x4a3920:
  s=f'{C.c_int32(args[2]).value:010d}'.encode()+b'\0';C.memmove(e.buffer,s,len(s));return len(s)-1
 return effect(e.function,e.receiver,args)
ABI={0x4c7900:(2,8),0x4c7970:(1,4),0x4d3e50:(6,24),0x4c82a0:(1,4),0x4c9be0:(1,4),0x4c9fc0:(1,4),0x4c9e00:(1,4),0x417b00:(4,0),**{f:(1,0)for f in FRAME_CALLBACKS},0x4000010:(3,12),0x4000020:(0,0)}
currentFunction=0

def timer_hook(uc,address,size,user):
 global originalFormattingCalls
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4a3920:
  originalFormattingCalls+=1
  if context.composeFormatting:return
  buffer,fmt,value=m.read_words(sp+4,3);before=bytes(u.mem_read(buffer,16));# Native scratch startszero: tail is not an argument of sprintf and is normalized.
  event(address,0,(0,fmt,value),labels.get(fmt),1,b'\0'*16);out=f'{C.c_int32(value).value:010d}'.encode()+b'\0';u.mem_write(buffer,out);returned(0,len(out)-1);return
 if address in(0x4f63ec,0x4f6428):
  args=tuple(m.read_words(sp+4,1));event(address,0,args);returned(0,effect(address,0,args));return
 if address==0x4f6286:
  token,out=m.read_words(sp+4,2);name=bytes(u.mem_read(token,100)).split(b'\0')[0];event(address,receiver,(token,),name);value=effect(address,receiver,(token,));m.write_words(out,[value]);returned(8,int(bool(value)));return
 if address==0x546d50:return
 if address==0x4000030:
  args=tuple(m.read_words(sp+4,4));event(0x546d50,0,args);returned(16,effect(0x546d50,0,args));return
 if address in ABI:
  if address==currentFunction:return
  if (currentFunction in(0x4c9fc0,0x4c9fe0,0x4d3eb0)or context.composeHierarchy)and address in(0x4c9be0,0x4c9fc0):return
  if address in(0x4c7900,0x4c7970)and context.composeImages:return
  if address==0x4d3e50 and context.composeHierarchy:return
  if address==0x4c82a0 and context.composeAnimation:return
  n,pop=ABI[address];args=tuple(m.read_words(sp+4,n));name=next((labels[v]for v in args if v in labels),None);normalized=0 if address in(0x417b00,*FRAME_CALLBACKS)else receiver;event(address,normalized,args,name);returned(pop,effect(address,normalized,args));return
u.hook_add(UC_HOOK_CODE,timer_hook);u.mem_map(0x4000000,4096);m.write_words(0x546d50,[0x4000030])
def setup(seed=0):
 global heap,g,context,native,policy,resourceFound,failAllocation,failChild,allocationIndex,childIndex,nextAllocation,virtualModes
 native=True;heap=(C.c_uint8*SIZE).from_buffer_copy(random.Random(seed).randbytes(SIZE));g=TimerGlobals(MANAGER,P,16,16,12345,35000,0,STATS,0,0,640,480,100);context=TimerContext(host,C.pointer(g),0,0,0,1,0);policy=failAllocation=failChild=allocationIndex=childIndex=0;resourceFound=True;nextAllocation=ALLOC_BASE;virtualModes=[3]
 put(A+0xc,[SC]);put(A+0x6c,[L]);put(A+8,[0x200000]);put(A+0x64,[9999]);put(A+0x170,[TIMEIMG,TIMEFRAME]);put(A+0x188,[0x513870,A,0,0,0,0,1,0,0,0,0x3f800000]);put(L+0x18,[HUD,0]);put(L+0x10,[0x491b30]);put(P+0x6c,[PL]);put(PL+0x14,[PP]);put(P+0x10c,[100]);put(SC+0xc,[DISPLAY]);put(SC+0x10,[BASE+0xe000]);put(SC+0x14,[BASE+0xf000]);put(SC+0x24,[2]);put(MANAGER+4,[APP]);put(MANAGER+0x2c,[CONFIG]);put(MANAGER+0x68,[2,0]);put(CONFIG,[VT]);put(VT+16,[0x40af90]);put(APP+4,[0xabc]);put(DISPLAY,[DVT]);put(DVT+0x28,[0x4000010]);put(STATS+0xc,[SC]);put(STATS+0x6c,[STATSL]);put(STATSL+0x10,[0x491ed0]);put(STATSL+0x1c,[0]);put(STATS+0x1b4,[0x5107bc,0,0,0,0,0,10]);put(HUD,[0x50b5c4,3,10,4,15,2,99,0,1,A,0x50b5cc,0,3,*D[:3]]);put(META+8,[0,0,0x4919f0]);put(DIGMETA+8,[0,0,0x4919f0]);put(STATMETA+8,[0,0,0x491ed0]);
 for token,callback in zip(FRAME_METADATA,FRAME_CALLBACKS):put(token+8,[0,0,callback])
 put(CONTAINER+0xc,[SC]);put(CONTAINER+0x10,[0x5107bc,0,0,0,0,0,10]);put(TIMEIMG+0x14,[TIMEFRAMES]);put(TIMEIMG+0x64,[1,1]);put(TIMEFRAMES,[0,TIMEFRAME]);put(NUMIMG+0x14,[NUMFRAMES]);put(NUMIMG+0x64,[0,9]);put(NUMFRAMES,[NUMGEOMETRY+i*0x40 for i in range(10)]);put(TIMEFRAME+0x18,[16,16,0,0])
 for i in range(10):
  put(D[i]+0xc,[SC]);put(D[i]+0x6c,[DL[i]]);put(D[i]+0x170,[NUMIMG,NUMGEOMETRY]);put(D[i]+0x64,[10000]);put(DL[i]+0x10,[0x4919f0]);put(DL[i]+0x18,[DH[i],0]);put(DH[i],[0x50b5c4,3,40+i*11,4,15,2,99,0,1,D[i],0x50b5cc])

def compare(f,label,args=None,receiver=0,fault_expected=False):
 global native,calls,event_count,allocationIndex,childIndex,nextAllocation,currentFunction,virtualModes
 native=True;before,bg=bytes(heap),bytes(g);events.clear();context.fault=0;allocationIndex=childIndex=0;allocationStart=nextAllocation;modes=list(virtualModes);result=C.c_uint32();arguments=tuple(args if args is not None else(A,));argv=(C.c_uint32*len(arguments))(*(v&0xffffffff for v in arguments));assert lib.claw_checkpoint_timer_entry(f,receiver,argv,len(arguments),C.byref(context),dependency,None,C.byref(result))
 assert bool(context.fault)==fault_expected,(label,'native fault',context.fault);expected,ee=snap(),list(events);afterHeap,afterGlobals=bytes(heap),bytes(g);allocationEnd=nextAllocation;native=False;events.clear();u.mem_write(BASE,before)
 for token,value in zip(GLOBAL_ADDRESSES,struct.unpack('<13I',bg)):m.write_words(token,[value])
 failed=False;ret=None;allocationIndex=childIndex=0;nextAllocation=allocationStart;currentFunction=f;virtualModes=modes
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(arguments),*(v&0xffffffff for v in arguments)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'original fault',failed)
 actual=snap()
 if actual!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('full timer heap/globals')
 if events!=ee:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(('ordered full events',label,len(ee),len(events)))
 if not failed and f not in(0x490c40,0x490c00,0x40db50,0x4d3f20,0x4c9fe0,0x4d3eb0,0x4f5172,0x41f490):assert ret==result.value,(label,'EAX',ret,result.value)
 if not failed:assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+{0x490590:32,0x490760:28,0x40db30:4,0x40f680:4,0x4d3f20:4,0x4c9fc0:4,0x4d3e50:24,0x4d3ca0:24,0x4c8e00:24,0x4c8f60:24,0x426e30:12}.get(f,0),(label,'calling convention')
 native=True;nextAllocation=allocationEnd;C.memmove(C.addressof(heap),afterHeap,SIZE);C.memmove(C.addressof(g),afterGlobals,len(afterGlobals));calls+=1;event_count+=len(ee);return result.value

def real_resources():
 paths=[(ROOT/'work/original-disc-assets/GAME/IMAGES/INTERFACE/TIME/TIME1.PID',TIMEFRAME)]+[(ROOT/'work/original-disc-assets/GAME/IMAGES/INTERFACE/SCORENUMBERS'/f'{i:03}.PID',NUMGEOMETRY+i*0x40)for i in range(10)]
 for path,token in paths:
  _,_,width,height,x,y=struct.unpack_from('<6I',path.read_bytes());geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),width,height,x,y);put(token+0x10,[geometry.width,geometry.height,geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY])
def null_page_off():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 cpu=u.context_save();teb,gdt=0x10ed000,0x10ee000
 def descriptor(base,access):return struct.pack('<I',(0xffff|(base&0xffff)<<16))+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 u.mem_write(gdt+8,descriptor(0,0x9b));u.mem_write(gdt+16,descriptor(0,0x93));u.mem_write(gdt+24,descriptor(teb,0x93));u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):u.reg_write(reg,0x10)
 u.reg_write(UC_X86_REG_CS,8);u.reg_write(UC_X86_REG_FS,0x18);m.write_words(teb,[0xdeadbeef]);u.mem_unmap(0,4096);return cpu
def null_page_on(cpu):u.mem_map(0,4096);u.context_restore(cpu)
TIMEMETA=BASE+0x1e000
class Create(C.Structure):_fields_=[(n,C.c_uint32)for n in('id','x','y','z','entryToken','flags')]
lib.claw_scene_actor_create_named.argtypes=[C.c_uint32,Create,C.c_uint32,Host,C.POINTER(C.c_uint32)];lib.claw_scene_actor_create_named.restype=C.c_uint32
@Allocate
def scene_allocate(_,size):event(0x4f63ec,0,(size,));return allocate(size)
@Free
def scene_free(_,token):event(0x4f6428,0,(token,))
@Invoke
def scene_call(_,e):
 args=tuple(e.arguments[:e.argumentCount])
 if e.function==0x491b30:
  result=C.c_uint32();argv=(C.c_uint32*len(args))(*args);assert lib.claw_checkpoint_timer_entry(e.function,e.receiver,argv,len(args),C.byref(context),dependency,None,C.byref(result));return result.value
 name=next((labels[v]for v in args if v in labels),None);event(e.function,e.receiver,args,name);return effect(e.function,e.receiver,args)
sceneHost=Host(None,lookup,scene_allocate,scene_free,scene_call,Clock())
priorEffect=effect
def effect(f,receiver,args):
 if f==0x4f6286 and args[0]==0x522828:return TIMEMETA if resourceFound else 0
 return priorEffect(f,receiver,args)
labels[0x522828]=b'CheckpointTimer'

def create_timer(label):
 global native,calls,event_count,allocationIndex,childIndex,nextAllocation,currentFunction
 put(TIMEMETA+8,[2,0,0x491b30]);before,bg=bytes(heap),bytes(g);allocationStart=nextAllocation;allocationIndex=childIndex=0;events.clear();fault=C.c_uint32();native=True
 token=lib.claw_scene_actor_create_named(CONTAINER,Create(0,0,0,9999,0,0x200000),0x522828,sceneHost,C.byref(fault));assert token and not fault.value and not context.fault
 expected,ee=snap(),list(events);afterHeap,afterGlobals=bytes(heap),bytes(g);allocationEnd=nextAllocation;native=False;events.clear();u.mem_write(BASE,before)
 for address,value in zip(GLOBAL_ADDRESSES,struct.unpack('<13I',bg)):m.write_words(address,[value])
 allocationIndex=childIndex=0;nextAllocation=allocationStart;currentFunction=0x4c8da0;original=m.call(0x4c8da0,CONTAINER,struct.pack('<6I',0,0,0,9999,0x522828,0x200000));assert original==token,(label,'creator return')
 if snap()!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(expected)//4),snap())))if x!=y][:15]);raise AssertionError('real scene timer creator full heap/globals')
 if ee!=events:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(('real creator events',len(ee),len(events)))
 native=True;nextAllocation=allocationEnd;C.memmove(C.addressof(heap),afterHeap,SIZE);C.memmove(C.addressof(g),afterGlobals,len(afterGlobals));calls+=1;event_count+=len(ee);return token
