"""Owned oracle composition; unchanged original pixels/CRT with physical surface/TLS transport."""
from pathlib import Path
source=Path(__file__).with_name('player_fade_blend_runtime_helpers.py').read_text()
source=source.replace("'work/player-fade-blend-agent'","'work/warp-fade-agent'")
start=source.index('# Demonstrate');end=source.index('class SCall')
source=source[:start]+'''subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(ROOT/'Sources'/f'{name}.cpp')for name in('PlayerFadeBlendRuntime','CArrayRuntime','ActorDestruction','CRTRandomRuntime','WorldLootRuntime','SceneActorRuntime','WorldObjectRuntime','GameTiming')],str(WORK/'numeric-probe.cpp'),str(WORK/'warp-numeric-probe.cpp'),'-o',str(WORK/'libPlayerFadeBlendRuntime.dylib')],check=True)

'''+source[end:]
exec(compile(source,str(Path(__file__).with_name('player_fade_blend_runtime_helpers.py')),'exec'),globals())
class WarpContext(C.Structure):_fields_=[('common',C.POINTER(BlendContext)),('maximumOperations',C.c_uint32)]
warp=WarpContext(C.pointer(blend),1000000)
lib.claw_warp_fade_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(WarpContext),Dep,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_warp_fade_entry.restype=C.c_uint32
class CRTGlobals(C.Structure):_fields_=[('tlsIndex',C.c_uint32)]
class CRTContext(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(CRTGlobals)),('fault',C.c_uint32)]
class CRTCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('count',C.c_uint32),('arguments',C.c_uint32*2)]
CRTDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(CRTContext),C.POINTER(CRTCall),C.c_void_p)
lib.claw_crt_random_entry.argtypes=[C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(CRTContext),CRTDependency,C.c_void_p,C.POINTER(C.c_uint32)]
crtGlobals=CRTGlobals(1);crtContext=CRTContext(ctx.scene,C.pointer(crtGlobals),0)
THREAD=BASE+0x2c00;OS=BASE+0x2d00;PERM=BASE+0xd000
STRING=BASE+0xc000
GATES={0x10ff200:0x546b0c,0x10ff210:0x546a7c,0x10ff220:0x546ab8}
for address,slot in GATES.items():m.write_words(slot,[address])
baseEffect=effect

def effect(fn,r,args,native):
 if fn==0x546b0c:return get(OS,native=native)[0]
 if fn==0x546a7c:put(OS,[0x1234],native);return THREAD
 if fn==0x546ab8:put(OS,[args[0]],native);return 0
 if fn==0x4f63ec:
  i=0 if native else 1;ordinal=allocationCount[i];allocationCount[i]+=1
  if allocationFailure or ordinal==allocationFailureOrdinal:return 0
  if args[0]==0x7d5c:return EFFECT
  if args[0]>=4 and args[0]%4==0 and args[0]<0x2000:return PERM
  return STRING
 return baseEffect(fn,r,args,native)
@CRTDependency
def crtDependency(_,ep,user):
 q=ep.contents;a=list(q.arguments[:q.count]);ne.append((q.function,0,tuple(a),snapshot(True)));return effect(q.function,0,a,True)
@Dep
def dependency(_,ep,user):
 q=ep.contents
 if q.function==0x4a3050:
  out=C.c_uint32();assert lib.claw_crt_random_entry(0x4a3050,None,0,C.byref(crtContext),crtDependency,None,C.byref(out));return out.value
 a=list(q.arguments[:q.argumentCount]);ne.append((q.function,q.receiver,tuple(a),snapshot(True)))
 try:return effect(q.function,q.receiver,a,True)
 except Exception as error:errors.append(error);return 0

def tlsHook(u,address,size,user):
 if address not in GATES:return
 f=GATES[address];sp=u.reg_read(UC_X86_REG_ESP);n={0x546b0c:0,0x546a7c:1,0x546ab8:1}[f];a=m.read_words(sp+4,n);oe.append((f,0,tuple(a),snapshot(False)));v=effect(f,0,a,False);u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+n*4)
m.u.hook_add(UC_HOOK_CODE,tlsHook)
baseSync=sync
def sync():
 baseSync();m.write_words(0x52edd8,[1]);crtContext.fault=0
basePrepare=prepare

def prepare(w=31,h=23,bpp=1,direction=1,pad=5,percent=15,seed=1):
 basePrepare(w,h,bpp,direction,pad);put(EFFECT,[0xa5a5a5a5]*(0x7d5c//4));put(EFFECT,[0x514228]);put(EFFECT+0x24,[SURFACE0,SURFACE1,HOLDER]);put(DESC,[3,SURFACE0,SURFACE1,direction,percent]);put(THREAD,[0]*29);put(THREAD+0x14,[seed]);put(OS,[0xbeef]);sync()
RETURNS.update({0x4ed060,0x4ed080,0x4ed0b0,0x4ed5d0,0x4ecc00,0x4efc40})
# Exact source EAX only for meaningful constructors/init/maximum/primality.
def compare(fn,t,a,label):
 global calls,events
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();argv=(C.c_uint32*len(a))(*a)
 assert lib.claw_warp_fade_entry(fn,t,argv,len(a),C.byref(warp),dependency,None,C.byref(result)),(label,ctx.fault,errors)
 assert not errors,errors
 m.call(fn,t,struct.pack('<'+'I'*len(a),*a),max_instructions=30000000)
 if fn in RETURNS:assert m.u.reg_read(UC_X86_REG_EAX)==result.value,(label,'EAX',m.u.reg_read(UC_X86_REG_EAX),result.value)
 if ne!=oe:
  for i,(x,y)in enumerate(zip(ne,oe)):
   if x!=y:print(label,'event',i,x[:3],y[:3],x[3]==y[3]);break
  raise AssertionError((label,'ordered full snapshots',len(ne),len(oe)))
 assert raw(True)==raw(False),(label,'heap',[(hex(BASE+i),a,b)for i,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:12])
 assert globalsRaw(True)==globalsRaw(False),(label,'globals')
 pop={0x4ed080:4,0x4ed0b0:4,0x4ed1a0:4,0x4ec050:8,0x4ec9c0:12,0x4ec600:4}.get(fn,0);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+pop
 calls+=1;events+=len(ne);return result.value

#Observe exact original no-op entry; its original RET executes unchanged.
def noOpHook(u,address,size,user):
 if address==0x4c96b0:oe.append((address,u.reg_read(UC_X86_REG_ECX),(),snapshot(False)))
m.u.hook_add(UC_HOOK_CODE,noOpHook)
oldEffect=effect
def effect(fn,r,args,native):
 if fn==0x4c96b0:return 0
 return oldEffect(fn,r,args,native)
prefixAddress=0;prefixes=0
def warpPrefixHook(u,address,size,user):
 if prefixAddress and address==prefixAddress:u.emu_stop()
m.u.hook_add(UC_HOOK_CODE,warpPrefixHook)
def comparePrefix(fn,t,a,label,fault,address):
 global prefixAddress,prefixes,events
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();argv=(C.c_uint32*len(a))(*a)
 assert not lib.claw_warp_fade_entry(fn,t,argv,len(a),C.byref(warp),dependency,None,C.byref(result)),label
 assert ctx.fault==fault,(label,ctx.fault,errors)
 assert not errors or all(isinstance(e,tuple)and e[0]=='lookup missing'for e in errors),errors
 prefixAddress=address;m.u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(a),*a));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);m.u.emu_start(fn,m.stop,count=30000000);assert m.u.reg_read(UC_X86_REG_EIP)==address,(label,hex(m.u.reg_read(UC_X86_REG_EIP)));prefixAddress=0
 assert ne==oe,(label,'prefixevents',len(ne),len(oe));assert raw(True)==raw(False),(label,'prefixheap');assert globalsRaw(True)==globalsRaw(False),(label,'prefixglobals');prefixes+=1;events+=len(ne)
