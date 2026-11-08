"""Original-instruction command oracle; whole 512KiB heap and97 global words."""
from pathlib import Path
source=Path(__file__).with_name('elevator_logic_helpers.py').read_text().split('class LevelProfile')[0]
source=source.replace("WORK=ROOT/'work/elevator-agent'","WORK=ROOT/'work/special-command-agent'")
source=source.replace("'ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'","'SpecialCommandRuntime.cpp','GameTiming.cpp','ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp'")
source=source.replace('u.hook_add(UC_HOOK_CODE,original_hook)','baseHook=u.hook_add(UC_HOOK_CODE,original_hook)')
exec(compile(source,str(Path(__file__).with_name('elevator_logic_helpers.py')),'exec'),globals())
u.hook_del(baseHook)
class SpecialGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','warpX','warpY','audioVolume','fadeBypass','inputMappingToken','mouseToken','accumulatedTick')]+[('clock',C.c_uint32*5),('stage',C.c_uint32*2),('animation',C.c_uint32*2),('capturedPlayer',C.c_uint32*78),('displayRankings',C.c_uint32)]
class SpecialContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(SpecialGlobals)),('fault',C.c_uint32)]
class SpecialCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*8),('name',C.c_char_p),('localMask',C.c_uint32),('buffer',C.POINTER(C.c_uint32)),('bufferWords',C.c_uint32)]
SpecialDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(SpecialContext),C.POINTER(SpecialCall),C.c_void_p)
lib.claw_special_command_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(SpecialContext),SpecialDependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_special_command_entry.restype=C.c_uint32
GLOBAL_ADDRESSES=(0x5371fc,0x537e88,0x529fa0,0x529fa4,0x532c10,0x537238,0x537204,0x537200,0x537210,*range(0x541328,0x54133c,4),0x537208,0x53720c,0x5430c8,0x5430c4,*range(0x534c80,0x534db8,4),0x525518)
O,VT,CONTAINER,CVT,WORLD,WVT,SURFACE,BACK,FRONT,RENDER,RVT,SOUNDS,FADERM,FADER,FVT,FDATA,SHELL,INPUT,MOUSE,WINDOW,SAVE,OPTIONS,SETTINGS,SERVICE,PAL,STATS,IMAGE,IVT,ANI=[BASE+i*0x1000 for i in range(14,43)]
ALLOC=BASE+0x50000;nextAllocation=ALLOC;allocationIndex=failAllocation=policy=clockIndex=0;modes=[3];showCounts=[-1];leafFailure=0;faultedOriginal=False
RETURNS={};resource=True;g=SpecialGlobals();context=SpecialContext();currentFunction=0
labels={0x52a07c:b'GAME_WARP',0x5258a8:b'Status Layout',0x525860:b'Display Rankings',0x523b1c:b'STATES_BOOTY',0x523734:b'CLAW',0x52372c:b'SOUNDS',0x523b14:b'BOOTY'}
# Literal/vtable reads are immutable source bytes, never host pointer guesses.
pe=(C.c_ubyte*0x40000).from_buffer_copy(bytes(u.mem_read(0x500000,0x40000)))
@Lookup
def lookup(_,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if 0x500000<=t and t+n*4<=0x540000:return C.addressof(pe)+t-0x500000
 return None

def snap():return(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(g)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRESSES))
def set_global(field,value):
 if native:setattr(g,field,value)
 else:m.write_words(GLOBAL_ADDRESSES[[n for n,_ in SpecialGlobals._fields_].index(field)],[value])
def event(f,r,args,name=None,mask=0,buf=None):events.append(((f,r,tuple(args),name,mask,buf),snap()))
def allocate(size):
 global allocationIndex,nextAllocation
 event(0x4f63ec,0,(size,));allocationIndex+=1
 if allocationIndex==failAllocation:return 0
 t=nextAllocation;nextAllocation+=(size+15)&~15;assert nextAllocation<BASE+SIZE;return t
@Allocate
def alloc(_,size):return allocate(size)
@Free
def free(_,token):event(0x4f6428,0,(token,))
def time():
 global clockIndex
 value=(0xffffff00+clockIndex*17)&0xffffffff;clockIndex+=1;event(0x546df0,0,());return value
@Clock
def clock(_):return time()
host=Host(None,lookup,alloc,free,Invoke(),clock)
def base_ctor(t):
 put(t,[0x50b4ec])
 for off in(4,8,12,0x1c,0x20,0x24,0x2c,0x30,0x3c,0x40,0x34,0x18,0x150):put(t+off,[0])
 put(t+0x4c,[words(t+0x4c)[0]&0xffffff00])

def effect(f,r,args):
 global resource
 if f==0x4ec050:
  if not resource:return 0
  data=words(r+0x14)[0];count=words(r+0x18)[0];put(data+count*4,[FADER]);put(r+0x18,[count+1]);return FADER
 if f==0x4f6286:return SOUNDS+0x300 if resource else 0
 if f==0x4000000:return modes.pop(0)if len(modes)>1 else modes[0]
 if f==0x546d54:return showCounts.pop(0)if len(showCounts)>1 else showCounts[0]
 if f==0x40b5c0:base_ctor(r);return 0
 if f==0x48f0d0:
  put(r+4,[args[0],STATS,SC]);return 0 if leafFailure==f else 1
 if f in(0x4b7f20,0x4b68c0):return 0 if leafFailure==f else STATS
 if f==0x4f6439:put(r,[0x52e1c4]);return 0
 if f in(0x40b6a0,0x40d470):return 0 if leafFailure==f else 1
 if f==0x42bfd0:return 0 if leafFailure==f else 1
 if f==0x42af50:return 0 if leafFailure==f else 1
 if f==0x4ec9c0 and policy==1:put(O+4,[MANAGER+0x400]);put(MANAGER+0x400+0x50,[SERVICE]);put(MANAGER+0x400+0x14,[1]);put(BACK+0x2c,[SERVICE+0x400])
 if f==0x4b5c10 and policy==2:put(MANAGER+0x3c,[SERVICE+0x400])
 if f==0x4d2000 and policy==3:put(WORLD+0x5c,[0])
 if f==0x4ec9c0 and policy==4:set_global('warpX',777);set_global('warpY',888)
 if f==0x4d1fd0 and policy==5:put(P+0x6c,[PL+0x400]);put(PL+0x400+0x14,[PP+0x400])
 if f==0x4000060 and policy==6:put(MANAGER+0x2c,[O+0x400]);put(O+0x400,[VT]);put(O+0x400+4,[MANAGER]);put(O+0x400+0xc,[SC]);put(O+0x400+0x14,[2])
 if f==0x428c40:return 0 if leafFailure==f else 1
 return RETURNS.get(f,0)
@SpecialDependency
def dependency(_,e,user):
 e=e.contents;args=tuple(e.arguments[:e.argumentCount]);buf=tuple(e.buffer[:e.bufferWords])if e.buffer else None;event(e.function,e.receiver,args,e.name,e.localMask,buf);return effect(e.function,e.receiver,args)
# Services only. Covered entries and native body nested calls execute originally.
ABI={0x4ec050:(2,8),0x4ec9c0:(3,12),0x4b55a0:(0,0),0x4b55b0:(1,4),0x4b8960:(1,0),0x4b97c0:(1,4),0x4b98b0:(1,4),0x4b9c50:(1,4),0x4208e0:(4,16),0x4d2000:(0,0),0x4d1fd0:(0,0),0x4cb9b0:(2,8),0x4b5e50:(2,8),0x4c7510:(1,4),0x4b4b40:(0,0),0x4ca300:(0,0),0x4b5c10:(0,0),0x4b5340:(0,0),0x4022a0:(0,0),0x4cdf40:(0,0),0x4c89e0:(0,0),0x422350:(0,0),0x46d620:(3,12),0x49bbc0:(0,0),0x4bb870:(0,0),0x4bb990:(6,24),0x42b910:(0,0),0x42abb0:(0,0),0x429e10:(2,8),0x431300:(0,0),0x4b3ab0:(0,0),0x40b5c0:(0,0),0x42bfd0:(0,0),0x48f0d0:(3,12),0x42af50:(0,0),0x42a000:(1,4),0x429ed0:(3,12),0x4b7f20:(1,4),0x4b68c0:(1,4),0x4ca440:(3,12),0x4b8910:(2,8),0x4f6439:(0,0),0x40b6a0:(3,12),0x40d470:(3,12),0x40b720:(1,4),0x40dca0:(1,4),0x429790:(1,4),0x4000000:(0,0),0x4000010:(0,0),0x4000020:(1,4),0x4000030:(2,8),0x4000040:(0,0),0x4000050:(0,0),0x4000060:(1,4),0x4000070:(1,4),0x4000080:(1,4),0x4000090:(0,0)}
CDECL={0x4b8960}

def hook(uc,address,size,user):
 global nextAllocation
 sp=u.reg_read(UC_X86_REG_ESP);r=u.reg_read(UC_X86_REG_ECX)
 if address in(0x4f63ec,0x4f6428):
  value=m.read_words(sp+4,1)[0]
  if address==0x4f63ec:ret=allocate(value)
  else:event(address,0,(value,));ret=0
  returned(0,ret);return
 if address==0x40000b0:returned(0,time());return
 if address in(0x40000c0,0x40000d0,0x40000e0):
  f={0x40000c0:0x546d50,0x40000d0:0x546d44,0x40000e0:0x546d54}[address];n=1 if f==0x546d54 else 4;args=tuple(m.read_words(sp+4,n));event(f,0,args);returned(n*4,effect(f,0,args));return
 if address==0x4f6286:
  token,out=m.read_words(sp+4,2);event(address,r,(token,),labels.get(token));value=effect(address,r,(token,));m.write_words(out,[value]);returned(8,bool(value));return
 if address==0x428c40 and m.read_words(sp+4,1)[0]!=10:
  args=tuple(m.read_words(sp+4,4));event(address,r,args);returned(16,effect(address,r,args));return
 if address in ABI and address!=currentFunction:
  n,pop=ABI[address];args=tuple(m.read_words(sp+4,n));nr=0 if address in CDECL else r;buf=None;mask=0
  if address==0x4ec050:buf=tuple(m.read_words(args[1],5));args=(args[0],0);mask=2
  name=next((labels[a]for a in args if a in labels),None);event(address,nr,args,name,mask,buf);returned(pop,effect(address,nr,args));return
u.hook_add(UC_HOOK_CODE,hook);u.mem_map(0x4000000,4096)
for t,v in((0x546df0,0x40000b0),(0x546d50,0x40000c0),(0x546d44,0x40000d0),(0x546d54,0x40000e0)):m.write_words(t,[v])

def setup(seed=0):
 global heap,g,context,native,nextAllocation,allocationIndex,failAllocation,policy,clockIndex,modes,showCounts,leafFailure,resource,RETURNS
 native=True;heap=(C.c_uint8*SIZE).from_buffer_copy(random.Random(seed).randbytes(SIZE));g=SpecialGlobals(MANAGER,P,100,200,100,0,INPUT,MOUSE,12345);g.clock[:]=(1,2,3,4,5);g.stage[:]=(11,12);g.animation[:]=(13,14);g.capturedPlayer[:]=[0xbeef]*78;context=SpecialContext(host,C.pointer(g),0);nextAllocation=ALLOC;allocationIndex=failAllocation=policy=clockIndex=leafFailure=0;modes=[3];showCounts=[-1];resource=True;RETURNS={0x4000010:1}
 put(O,[VT]);put(VT+0xc,[0x4000010,0x40af90]);put(VT+0x28,[0x4000060]);put(VT+0x40,[0x46c900]);put(VT+0x54,[0x46c630]);put(O+4,[MANAGER]);put(O+12,[SC,FADERM,1]);put(O+0x258,[0,0]);put(O+0x2c,[PAL]);put(PAL+0x10,[SERVICE]);put(O+0x160,[100,0,0]);
 for level in range(1,15):put(O+0x160+level*16,[0,0,0,0])
 put(O+0x150,[SERVICE]);put(O+0x768,[SERVICE,SERVICE+4,SERVICE+8]);put(MANAGER+4,[WINDOW,SHELL]);put(WINDOW+4,[0xabc]);put(MANAGER+0x14,[1]);put(MANAGER+0x2c,[O,1]);put(MANAGER+0x38,[SETTINGS,SERVICE]);put(MANAGER+0x48,[OPTIONS,SERVICE,SERVICE,SERVICE,SERVICE,SAVE]);put(OPTIONS+0x128,[1]);put(MANAGER+0x9c,[0,0]);put(MANAGER+0xdc,[0x5107bc,0,0,0,10]);put(MANAGER+0x68,[2]);put(MANAGER+0x130,[0]);put(SC+4,[SURFACE,CONTAINER,RENDER,IMAGE]);put(IMAGE,[IVT]);put(IVT+0x58,[0x4000040]);put(SC+0x1c,[1]);put(SC+0x24,[WORLD,SOUNDS,ANI]);put(SOUNDS+0x2c,[SERVICE,0]);put(WORLD,[WVT]);put(WVT+0x44,[0x4000050]);put(WORLD+0x5c,[FRAME]);put(CONTAINER,[CVT]);put(CVT+0x24,[0x4000020]);put(RENDER,[RVT]);put(RVT+0x34,[0x4000030]);put(SURFACE+0x10,[BACK,FRONT,FRONT]);put(BACK+0x2c,[BACK+0x400]);put(FRONT+0x2c,[FRONT+0x400]);put(FADERM+0x14,[FDATA,0,16]);put(FADER,[FVT]);put(FVT,[0x4000070]);put(P+0x6c,[PL]);put(PL+0x14,[PP]);put(P+0xf8,[5678]);put(P+0x10c,[100]);put(O+0x400,[VT]);put(O+0x400+4,[MANAGER]);put(O+0x400+12,[SC]);put(O+0x400+0x14,[2]);put(O+0x400+0x160,[100,0,0]);put(MANAGER+0x400+0x30,[1]);put(MANAGER+0x400+0x50,[SERVICE]);put(MANAGER+0x400+0x14,[1])

def compare(f,label,args=(),receiver=O,fault_expected=False):
 global native,calls,event_count,clockIndex,allocationIndex,nextAllocation,currentFunction,modes,showCounts
 native=True;before,bg=bytes(heap),bytes(g);events.clear();context.fault=0;clockStart=clockIndex;allocStart=nextAllocation;allocationIndex=0;modeStart=list(modes);showStart=list(showCounts);out=C.c_uint32();argv=(C.c_uint32*len(args))(*(v&0xffffffff for v in args));assert lib.claw_special_command_entry(f,receiver,argv,len(args),C.byref(context),dependency,None,C.byref(out));assert bool(context.fault)==fault_expected,(label,'nativefault',context.fault);expected,ee=snap(),list(events);afterHeap,afterGlobals=bytes(heap),bytes(g);allocEnd=nextAllocation;clockEnd=clockIndex
 native=False;events.clear();u.mem_write(BASE,before)
 for t,v in zip(GLOBAL_ADDRESSES,struct.unpack('<97I',bg)):m.write_words(t,[v])
 clockIndex=clockStart;allocationIndex=0;nextAllocation=allocStart;modes=modeStart;showCounts=showStart;currentFunction=f;failed=False
 try:ret=m.call(f,receiver,struct.pack('<'+'I'*len(args),*(v&0xffffffff for v in args)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'original fault',failed)
 actual=snap()
 if actual!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('complete heap/globals')
 if events!=ee:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(('ordered full snapshots',label,len(ee),len(events)))
 if not failed and f in(0x426e30,0x46c630,0x46c900,0x48feb0,0x48fda0,0x428c40,0x40ac20,0x40b120,0x4ecc00):assert ret==out.value,(label,'EAX',ret,out.value)
 if not failed:assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+{0x426e30:12,0x48feb0:12,0x48fda0:12,0x428c40:16,0x40ac20:12,0x40b120:4,0x46c7b0:4,0x4ec600:4}.get(f,0),(label,'callingconvention')
 native=True;nextAllocation=allocEnd;clockIndex=clockEnd;C.memmove(C.addressof(heap),afterHeap,SIZE);C.memmove(C.addressof(g),afterGlobals,len(afterGlobals));calls+=1;event_count+=len(ee);return out.value

def null_page_off():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 cpu=u.context_save();teb,gdt=0x10ed000,0x10ee000
 def descriptor(base,access):return struct.pack('<I',(0xffff|(base&0xffff)<<16))+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 u.mem_write(gdt+8,descriptor(0,0x9b));u.mem_write(gdt+16,descriptor(0,0x93));u.mem_write(gdt+24,descriptor(teb,0x93));u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):u.reg_write(reg,16)
 u.reg_write(UC_X86_REG_CS,8);u.reg_write(UC_X86_REG_FS,24);m.write_words(teb,[0xdeadbeef]);u.mem_unmap(0,4096);return cpu
def null_page_on(cpu):u.mem_map(0,4096);u.context_restore(cpu)
# Source caller composition. Build only into this worker's private directory;
# existing frozen source/header files and shared verification outputs untouched.
class PowerGlobals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','powerup','remaining','expired','musicDisabled','cycleRemaining','cycleIndex')]
class PowerContext(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(PowerGlobals)),('fault',C.c_uint32)]
class ObjectPowerContext(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('loot','items','powerups','physics','animation')]+[(n,C.c_uint32)for n in('inputToken','curseEnabled','warpX','warpY','composeAnimation','composeCreation','fault')]
class ObjectPowerArguments(C.Structure):_fields_=[('words',C.c_uint32*6),('count',C.c_uint32)]
class ObjectPowerCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*6),('argumentCount',C.c_uint32),('name',C.c_char_p)]
ObjectPowerDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(ObjectPowerContext),C.POINTER(ObjectPowerCall),C.c_void_p)
# Recompile the frozen family into an owned output rather than import its
# helper (which would write the other worker's private verification library).
import ast
text=Path(__file__).with_name('powerup_object_runtime_helpers.py').read_text();tree=ast.parse(text);powerSources=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='sources'for t in n.targets))
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f'{name}.cpp')for name in powerSources],str(ROOT/'work/powerup-object-agent/image-effect-adapter.cpp'),'-o',str(WORK/'libSpecialPowerupCaller.dylib')],check=True)
powerlib=C.CDLL(str(WORK/'libSpecialPowerupCaller.dylib'));powerlib.claw_powerup_object_entry.argtypes=[C.c_uint32,C.c_uint32,ObjectPowerArguments,C.POINTER(ObjectPowerContext),ObjectPowerDependency,C.c_void_p,C.POINTER(C.c_uint32)];powerlib.claw_powerup_object_entry.restype=C.c_uint32
@ObjectPowerDependency
def publication_dependency(_,e,user):
 e=e.contents;event(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);return effect(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]))
publication_calls=0

def publish_warp(label):
 global native,publication_calls,event_count,calls
 native=True;before,bg=bytes(heap),bytes(g);pg=PowerGlobals(MANAGER,P,0,0,0,0,0,0);pc=PowerContext(host,C.pointer(pg),0);oc=ObjectPowerContext();oc.scene=host;oc.powerups=C.addressof(pc);oc.warpX=g.warpX;oc.warpY=g.warpY;args=(P,PL,PP,A);out=C.c_uint32();events.clear();assert powerlib.claw_powerup_object_entry(0x41ee60,0,ObjectPowerArguments((C.c_uint32*6)(*args,0,0),4),C.byref(oc),publication_dependency,None,C.byref(out))and not oc.fault
 g.warpX=oc.warpX;g.warpY=oc.warpY;expected=snap();after=bytes(heap),bytes(g);ee=list(events)
 # Globals publication is performed inside source caller before PostMessage;
 # expose its live aliases when the native dependency observes that event.
 for index,(e,s)in enumerate(ee):
  if e[0]==0x546d50:
   a=bytearray(s);off=SIZE+8;struct.pack_into('<2I',a,off,oc.warpX,oc.warpY);ee[index]=(e,bytes(a))
 native=False;events.clear();u.mem_write(BASE,before)
 for t,v in zip(GLOBAL_ADDRESSES,struct.unpack('<97I',bg)):m.write_words(t,[v])
 m.call(0x41ee60,0,struct.pack('<4I',*args));assert snap()==expected,(label,'source publication full heap/globals');assert events==ee,(label,'source publication event snapshots');native=True;C.memmove(C.addressof(heap),after[0],SIZE);C.memmove(C.addressof(g),after[1],len(after[1]));publication_calls+=1;calls+=1;event_count+=len(ee)
