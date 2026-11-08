"""Type2 whole-instruction oracle composing the frozen source fade runner."""
from pathlib import Path
source=Path(__file__).with_name('player_fade_runtime_helpers.py').read_text()
source=source[:source.index('prefixFunction=0;')]
source=source.replace("WORK=ROOT/'work/player-fade-agent'","WORK=ROOT/'work/scene-fade-agent'")
line=next(x for x in source.splitlines()if x.startswith('subprocess.run('))
source=source.replace(line,"subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{name}.cpp')for name in('SceneFadeRuntime','PlayerFadeRuntime','PlayerFadeBlendRuntime','CArrayRuntime','ActorDestruction','WorldLootRuntime','SceneActorRuntime','GameTiming','WorldObjectRuntime','ActorResourceBindings')],'-o',str(WORK/'libPlayerFadeRuntime.dylib')],check=True)")
source=source.replace('m.u.hook_add(UC_HOOK_CODE,hook)','oldHook=m.u.hook_add(UC_HOOK_CODE,hook)')
exec(compile(source,str(Path(__file__).with_name('player_fade_runtime_helpers.py')),'exec'),globals())
m.u.hook_del(oldHook)
class BlendContext(C.Structure):_fields_=[('fade',C.POINTER(Context)),('temporaryStringToken',C.c_uint32),('emptyStringToken',C.c_uint32),('uninitializedCapturePixelToken',C.c_uint32)]
class SceneFadeContext(C.Structure):_fields_=[('blend',C.POINTER(BlendContext))]
NEWARRAY=BASE+0x3000
TEMP,EMPTY,STRING,THREAD,TEMPARRAY=BASE+0x2300,BASE+0x2400,BASE+0x2500,BASE+0x2600,BASE+0x2800
blend=BlendContext(C.pointer(ctx),TEMP,EMPTY+12,0);context=SceneFadeContext(C.pointer(blend))
lib.claw_scene_fade_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(SceneFadeContext),Dep,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_scene_fade_entry.restype=C.c_uint32
baseEffect=effect
rngCalls=[0,0];allocationCount=[0,0];failAllocation=0;seed=0;blockCache={};currentFunction=0;currentSteps=[];failure=None

def effect(fn,receiver,args,native):
 global seed
 i=0 if native else 1
 if fn==0x4f63ec:
  allocationCount[i]+=1
  if allocationCount[i]==failAllocation:return 0
  if args[0]==0x7d5c:return EFFECT
  if args[0]>8000:return PIXELCAP
  return TEMPARRAY if args[0]>200 else(STRING if args[0]>32 else NEWARRAY)
 if fn==0x4a7dc0:
  rngCalls[i]+=1
  if mutation==3 and rngCalls[i]==3:put(EFFECT+0x4c,[22],native);put(EFFECT+0x54,[17],native)
  if mutation==2 and rngCalls[i]==3:put(EFFECT+0x50,[29],native)
  if mutation==1 and rngCalls[i]==3:put(EFFECT+0x40,[0],native)
  return THREAD
 if fn==RESTORE and mutation==4:put(EFFECT+0x2c,[0],native)
 if fn==0x5469e4:
  data=(C.string_at(C.addressof(image)+args[0]-0x400000,4096)if 0x400000<=args[0]<0x548000 else C.string_at(C.addressof(heap)+args[0]-BASE,4096))if native else bytes(m.u.mem_read(args[0],4096));return len(data.split(b'\0')[0])
 if fn==0x5469e8:
  value=get(args[0],native=native)[0]-1;put(args[0],[value],native);return value
 return baseEffect(fn,receiver,args,native)

def raw(native):
 b=bytearray(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)));b[SCRATCH-BASE:SCRATCH-BASE+36]=bytes(36);b[TEMP-BASE:TEMP-BASE+4]=bytes(4);return bytes(b)
def snapshot(native):
 # Lossless block interning preserves the complete bytes for every event;
 # repeated2000RNG prefixes share equal blocks instead of retaining gigabytes.
 b=raw(native)+globalsRaw(native);blocks=tuple(blockCache.setdefault(b[i:i+4096],b[i:i+4096])for i in range(0,len(b),4096));return blocks,tuple(freed[0 if native else 1])
@Dep
def dependency(_,e,user):
 q=e.contents;args=tuple(q.arguments[:q.argumentCount]);ne.append((q.function,q.receiver,args,snapshot(True)))
 try:return effect(q.function,q.receiver,args,True)
 except Exception as x:errors.append(x);ctx.fault=1;return 0

def returned(pop,value):
 sp=m.u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];m.u.reg_write(UC_X86_REG_EAX,value&0xffffffff);m.u.reg_write(UC_X86_REG_ESP,sp+4+pop);m.u.reg_write(UC_X86_REG_EIP,ret)
RNG=0x4a7dc0;STRLEN,DECREMENT=0x10ff150,0x10ff160
m.write_words(0x5469e4,[STRLEN]);m.write_words(0x5469e8,[DECREMENT]);COUNTS.pop(0x4c61f0);COUNTS.pop(0x4c7510);COUNTS.update({RNG:0,STRLEN:1,DECREMENT:1});CDECL.update({RNG,STRLEN,DECREMENT})

def hook(u,address,size,user):
 if address==0x4ecc00:
  r=u.reg_read(UC_X86_REG_ECX)
  if 0x2000000<=r<0x2010000:pass
 if address==DECREMENT:
  sp=u.reg_read(UC_X86_REG_ESP);token=m.read_words(sp+4,1)[0];value=(get(token,native=False)[0]-1)&0xffffffff;put(token,[value],False);returned(4,value);return
 if address not in COUNTS:return
 sp=u.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,COUNTS[address]));r=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX);fn={CLOCK0:0x546a24,CLOCK1:0x546df0,STRLEN:0x5469e4,DECREMENT:0x5469e8}.get(address,address)
 oe.append((fn,r,args,snapshot(False)));returned(0 if address in CDECL and address not in(UNLOCK,RESTORE,CLOCK0,CLOCK1,STRLEN,DECREMENT)else len(args)*4,effect(fn,r,args,False))
m.u.hook_add(UC_HOOK_CODE,hook)
basePrepare=prepare

def prepare(w=31,h=23,bpp=1,direction=1,pad=5,percent=80):
 global blockCache,failAllocation,currentFunction
 basePrepare(w,h,bpp,direction,pad);blockCache={};allocationCount[:]=[0,0];failAllocation=0;currentFunction=0
 put(EMPTY,[0xffffffff,0,0,0]);put(TEMP,[EMPTY+12]);put(THREAD+0x14,[0x12345678]);put(DESC,[3,SURFACE0,SURFACE1,direction,percent]);put(EFFECT,[0x514228]);put(EFFECT+0x1c,[0]);put(EFFECT+0x30,[1]);put(EFFECT+0x50,[w]);sync()
RETURNS.update({0x4ed060,0x4ed0b0,0x4ed5d0,0x4ed080,0x4efc40,0x4ecc00})

# Full retained native and original call transaction.
def compare(fn,t,args,label,fault=False,originalStop=0):
 global calls,events,currentFunction,blockCache
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();allocationCount[:]=[0,0];rngCalls[:]=[0,0];blockCache={};result=C.c_uint32();argv=(C.c_uint32*len(args))(*args);currentFunction=fn
 ok=lib.claw_scene_fade_entry(fn,t,argv,len(args),C.byref(context),dependency,None,C.byref(result));assert bool(ok)!=bool(fault),(label,'native fault',ctx.fault,errors);expected=raw(True),globalsRaw(True);nativeAllocEnd=allocationCount[0];nativeClockEnd=clockState[0]
 m.u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(args),*args));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);failed=False
 try:m.u.emu_start(fn,m.stop,count=20000000)
 except Exception:
  failed=True
  if not fault:print(label,'originalfault',hex(m.u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==bool(fault),(label,'originalfault',failed)
 original=m.u.reg_read(UC_X86_REG_EAX)
 if not failed and fn in RETURNS:assert original==result.value,(label,'return',original,result.value)
 assert len(ne)==len(oe),(label,'event counts',len(ne),len(oe))
 for i,(x,y)in enumerate(zip(ne,oe)):
  if x!=y:
   diff=next(((j,a[:16],b[:16])for j,(a,b)in enumerate(zip(x[3][0],y[3][0]))if a!=b),None);print(label,'event',i,x[:3],y[:3],'blockdiff',diff);raise AssertionError('ordered full snapshots')
 actual=raw(False),globalsRaw(False)
 if expected!=actual:
  print(label,'heapdiff',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(expected[0],actual[0]))if x!=y][:20]);raise AssertionError('full final heap/globals')
 assert not errors or fault,(label,errors);calls+=1;events+=len(ne);clockStartValue=clockState[0]
 # Preserve original completed lifetimes without resetting RNG/objects nextcall.
 m.u.mem_write(BASE,bytes(heap));return result.value

# Original null-page faults with a valid Windows SEH/TIB adapter.
u=m.u
import ast
nullSource=Path(__file__).with_name('special_command_helpers.py').read_text();nullTree=ast.parse(nullSource)
for node in nullTree.body:
 if isinstance(node,ast.FunctionDef)and node.name in('null_page_off','null_page_on'):exec(ast.get_source_segment(nullSource,node),globals())
prefixStop=0;prefixClocks=0;prefixCount=0

def prefixHook(u,address,size,user):
 if prefixStop and address==prefixStop and clockIndices[1]>=prefixClocks:u.emu_stop()
m.u.hook_add(UC_HOOK_CODE,prefixHook)
def stalled(duration,start,label):
 global prefixStop,prefixClocks,prefixCount,clockSequence,events,blockCache
 prepare();compare(0x4ed0b0,EFFECT,[DESC],label+' init');clockSequence=[start];ctx.maximumClockReads=12;sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();blockCache={};out=C.c_uint32();args=(C.c_uint32*3)(duration,0,0)
 assert not lib.claw_scene_fade_entry(0x4ec9c0,EFFECT,args,3,C.byref(context),dependency,None,C.byref(out));assert ctx.fault==2 and not errors
 prefixStop=0x4eca42;prefixClocks=12;m.u.mem_write(m.stack,struct.pack('<4I',m.stop,duration,0,0));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,EFFECT);m.u.emu_start(0x4ec9c0,m.stop,count=1000000);assert m.u.reg_read(UC_X86_REG_EIP)==prefixStop and ne==oe and raw(True)==raw(False)and globalsRaw(True)==globalsRaw(False),(label,'exact stalled instruction prefix')
 prefixStop=prefixClocks=0;clockSequence=None;ctx.maximumClockReads=10000;prefixCount+=1;events+=len(ne)
