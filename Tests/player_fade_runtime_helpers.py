"""Private original instruction oracle for the bounded circle fade graph."""
import ctypes as C, hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/player-fade-agent'
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib',str(WORK/'numeric-probe.cpp'),str(ROOT/'Sources/CArrayRuntime.cpp'),'-o',str(WORK/'libPlayerFadeRuntime.dylib')],check=True)
class SCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Alloc=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('bypass',C.c_uint32)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('descriptorWord3',C.c_uint32),('temporaryDescriptorToken',C.c_uint32),('maximumClockReads',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6)]
Dep=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x120000
OWNER,PARENT,CTRL,IMAGE0,IMAGE1,SURFACE0,SURFACE1,DD0,DD1,DDVT,APP,MUSIC,MANAGER,ARRAY,DESC,SCRATCH,HOLDER,PALETTE,CAPTURE=[BASE+0x1000+i*0x100 for i in range(19)]
EFFECT=BASE+0x4000;PIXEL0=BASE+0x10000;PIXEL1=BASE+0x60000;PIXELCAP=BASE+0xb0000;NEWARRAY=BASE+0x2000
LOCK,UNLOCK,RESTORE=0x4b9730,0x10ff100,0x10ff110
CLOCK0,CLOCK1,PT=0x10ff120,0x10ff130,0x10ff140
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.write_words(0x546a24,[CLOCK0]);m.write_words(0x546df0,[CLOCK1]);m.write_words(0x546cd4,[PT]);m.executed.clear()
image=(C.c_uint8*0x148000).from_buffer_copy(m.u.mem_read(0x400000,0x148000));heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g);ctx.temporaryDescriptorToken=SCRATCH;ctx.maximumClockReads=10000
lib=C.CDLL(str(WORK/'libPlayerFadeRuntime.dylib'));lib.claw_player_fade_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_player_fade_entry.restype=C.c_uint32
rng=random.Random(0x48fae0);ne=[];oe=[];errors=[];calls=events=0;freed=[[],[]];clockState=[0,0];clockStart=100;clockDelta=25;clockSequence=None;clockIndices=[0,0];mutation=0;allocationFailure=False;globalSeed=b'';width=height=0
@Lookup
def lookup(user,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if 0x400000<=t and t+n*4<=0x548000:return C.addressof(image)+t-0x400000
 errors.append(('lookup missing',hex(t),n));return None
ctx.scene=Host(None,lookup,Alloc(),Free(),Invoke(),Clock())
def put(t,v,native=True):
 data=struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
 if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
 else:m.u.mem_write(t,data)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(C.addressof(heap)+t-BASE,n*4)if native else bytes(m.u.mem_read(t,n*4))))
def raw(native):
 b=bytearray(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)));b[SCRATCH-BASE:SCRATCH-BASE+36]=bytes(36);return bytes(b)
def globalsRaw(native):
 if not native:return bytes(m.u.mem_read(0x528000,0x1c000))
 b=bytearray(globalSeed);struct.pack_into('<I',b,0x537238-0x528000,g.bypass);return bytes(b)
def snapshot(native):return hashlib.sha256(raw(native)).digest(),hashlib.sha256(globalsRaw(native)).digest(),tuple(freed[0 if native else 1]),tuple(get(EFFECT,24,native))
def effect(fn,receiver,args,native):
 i=0 if native else 1
 if fn in(0x546a24,0x546df0):
  if clockSequence:
   index=clockIndices[i];value=clockSequence[min(index,len(clockSequence)-1)];clockIndices[i]+=1
  else:value=clockState[i];clockState[i]=(value+clockDelta)&0xffffffff
  return value
 if fn==0x4f63ec:
  if allocationFailure:return 0
  return EFFECT if args[0]==0x206c else NEWARRAY
 if fn==0x4f6428:freed[i].append(args[0]);return 0
 if fn==0x4b9730:return {SURFACE0:PIXEL0,SURFACE1:PIXEL1,CAPTURE:PIXELCAP}[receiver]
 if fn in(UNLOCK,RESTORE):return 0
 if fn==0x4b55a0:
  if mutation==1:put(CTRL+0x10,[IMAGE1],native)
  if mutation==2:
   if native:g.bypass=1
   else:m.write_words(0x537238,[1])
  return 0
 if fn==0x4b55b0:return 0
 if fn==0x4c61f0:return 0
 if fn==0x4c7510:return 0
 if fn==0x4c6bd0:return PALETTE
 if fn==0x4bc960:return CAPTURE
 if fn==0x4bc4f0:return 0
 if fn==0x4b97c0:
  pixels={SURFACE0:PIXEL0,SURFACE1:PIXEL1}[receiver];pitch=get(receiver+0x1c,native=native)[0];h=get(receiver+0x14,native=native)[0]
  data=bytes([args[0]&255])*(pitch*h)
  if native:C.memmove(C.addressof(heap)+pixels-BASE,data,len(data))
  else:m.u.mem_write(pixels,data)
  return 0
 if fn==0x4b9c50:
  tokens={SURFACE0:PIXEL0,SURFACE1:PIXEL1,CAPTURE:PIXELCAP};dst,src=tokens[receiver],tokens[args[0]];h=get(receiver+0x14,native=native)[0];pitch=get(receiver+0x1c,native=native)[0];data=C.string_at(C.addressof(heap)+src-BASE,h*pitch)if native else bytes(m.u.mem_read(src,h*pitch))
  if native:C.memmove(C.addressof(heap)+dst-BASE,data,len(data))
  else:m.u.mem_write(dst,data)
  return 0
 raise AssertionError(('unknown',hex(fn),hex(receiver),args))
@Dep
def dependency(context,c,user):
 q=c.contents;a=list(q.arguments[:q.argumentCount]);ne.append((q.function,q.receiver,tuple(a),snapshot(True)))
 try:return effect(q.function,q.receiver,a,True)
 except Exception as e:errors.append(e);return 0
COUNTS={0x4f63ec:1,0x4f6428:1,LOCK:1,UNLOCK:2,RESTORE:3,0x4b55a0:0,0x4b55b0:1,0x4c61f0:0,0x4c7510:1,0x4c6bd0:3,0x4bc960:5,0x4bc4f0:1,0x4b97c0:1,0x4b9c50:1,CLOCK0:0,CLOCK1:0}
CDECL={0x4f63ec,0x4f6428,UNLOCK,RESTORE,CLOCK0,CLOCK1}
def hook(u,address,size,user):
 if address==0x4ecbc0:
  receiver=u.reg_read(UC_X86_REG_ECX)
  if 0x2000000<=receiver<0x2010000:m.write_words(receiver+12,[ctx.descriptorWord3])
 if address==PT:
  sp=u.reg_read(UC_X86_REG_ESP);rect,x,y=m.read_words(sp+4,3);l,t,r,b=m.read_words(rect,4);si=lambda v:C.c_int32(v).value;value=int(si(l)<=si(x)<si(r)and si(t)<=si(y)<si(b));u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+16);return
 if address not in COUNTS:return
 sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,COUNTS[address]);receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX);fn={CLOCK0:0x546a24,CLOCK1:0x546df0}.get(address,address);oe.append((fn,receiver,tuple(a),snapshot(False)));v=effect(fn,receiver,a,False);u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in CDECL and address not in(UNLOCK,RESTORE,CLOCK0,CLOCK1)else COUNTS[address]*4))
m.u.hook_add(UC_HOOK_CODE,hook)
def sync():
 global globalSeed
 m.u.mem_write(BASE,bytes(heap));m.write_words(0x537238,[g.bypass]);globalSeed=bytes(m.u.mem_read(0x528000,0x1c000));clockState[:]=[clockStart,clockStart];clockIndices[:]=[0,0]
def prepare(w=31,h=23,bpp=1,direction=1,pad=5):
 global width,height,mutation,allocationFailure
 width,height=w,h;mutation=0;allocationFailure=False;ctx.fault=0;ctx.descriptorWord3=rng.getrandbits(32);g.bypass=0;C.memset(heap,0xa5,SIZE)
 for token,n in((EFFECT,2075),(MANAGER,10),(DESC,9),(OWNER,474),(APP,24)):
  put(token,[rng.getrandbits(32)for _ in range(n)])
 for surface,pixel,dd in((SURFACE0,PIXEL0,DD0),(SURFACE1,PIXEL1,DD1),(CAPTURE,PIXELCAP,DD1)):
  put(surface,[0]*48);put(surface+8,[dd]);put(surface+0x14,[h,w,w*bpp+pad]);put(surface+0xac,[bpp]);put(dd,[DDVT]);put(pixel,[rng.getrandbits(32)for _ in range((h*(w*bpp+pad)+3)//4)])
 put(DDVT+0x80,[UNLOCK]);put(DDVT+0x58,[RESTORE]);put(HOLDER,[DD0]);put(OWNER+4,[APP]);put(OWNER+0xc,[PARENT,MANAGER]);put(PARENT+4,[CTRL]);put(PARENT+0x1c,[1]);put(CTRL+0x10,[IMAGE0,IMAGE1]);put(IMAGE0+0x2c,[SURFACE0]);put(IMAGE1+0x2c,[SURFACE1]);put(APP+0x14,[1]);put(APP+0x50,[MUSIC]);put(MANAGER,[SURFACE0,SURFACE1,0,0,0x5141c0,ARRAY,0,4,0,HOLDER]);put(ARRAY,[0]*8);put(PALETTE+8,[PIXELCAP]);put(DESC,[2,SURFACE0,SURFACE1,ctx.descriptorWord3,direction,0,w//2,h//2,0]);put(EFFECT+0x1c,[0,0,SURFACE0,SURFACE1,HOLDER,1,0,SURFACE0,SURFACE1,0,ctx.descriptorWord3,direction,w//2,h//2,PIXEL0,PIXEL1,100]);put(EFFECT,[0x514250]);put(EFFECT+0x2060,[0,w,h]);freed[0].clear();freed[1].clear();sync()
RETURNS={0x48fae0,0x48fbe0,0x4ec050,0x4ecbc0,0x4ecb30,0x4c61d0,0x4ec8d0,0x4ed5e0,0x4ed670,0x4ee6b0,0x4ed600,0x4ebf80}
def compare(fn,t,a,label):
 global calls,events
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();args=(C.c_uint32*len(a))(*a)
 assert lib.claw_player_fade_entry(fn,t,args,len(a),C.byref(ctx),dependency,None,C.byref(result)),(label,'native fault',ctx.fault,errors,[(hex(x[0]),hex(x[1]),x[2])for x in ne[-3:]])
 assert not errors,errors
 m.u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(a),*a));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);m.u.emu_start(fn,m.stop,count=20000000);assert m.u.reg_read(UC_X86_REG_EIP)==m.stop,(label,'original bound')
 original=m.u.reg_read(UC_X86_REG_EAX)
 if fn in RETURNS:assert original==result.value,(label,'return',original,result.value)
 assert len(ne)==len(oe),(label,'event count',len(ne),len(oe))
 for i,(x,y)in enumerate(zip(ne,oe)):
  assert x==y,(label,'event',i,x[:3],y[:3],'snapshot differing',[(i,hex(a),hex(b))for i,(a,b)in enumerate(zip(x[3][3],y[3][3]))if a!=b])
 assert raw(True)==raw(False),(label,'complete heap',[(hex(BASE+i),a,b)for i,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:12])
 assert globalsRaw(True)==globalsRaw(False),(label,'globals')
 calls+=1;events+=len(ne)
prefixFunction=0;prefixClocks=0;prefixClockCallsite=0;prefixCount=0
# Stop BEFORE an unrecovered source instruction/service, preserving the entire
# reached heap/event prefix; this does not simulate an original safe return.
def prefixHook(u,address,size,user):
 if prefixFunction and address==prefixFunction:u.emu_stop()
 if prefixClockCallsite and address==prefixClockCallsite and len([e for e in oe if e[0]in(0x546a24,0x546df0)])>=prefixClocks:u.emu_stop()
# A stop hook must run before the service adapter hook at the same address.
# For clock bound use the callsite's original indirect call instruction instead.
m.u.hook_add(UC_HOOK_CODE,prefixHook)
def comparePrefix(fn,t,a,label,fault,stopAddress):
 global prefixFunction,prefixCount,events
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();args=(C.c_uint32*len(a))(*a)
 assert not lib.claw_player_fade_entry(fn,t,args,len(a),C.byref(ctx),dependency,None,C.byref(result)),label
 assert ctx.fault==fault,(label,ctx.fault);assert not errors or(fault==1 and all(isinstance(e,tuple)and e[0]=='lookup missing'for e in errors)),errors
 prefixFunction=stopAddress;m.u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(a),*a));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);m.u.emu_start(fn,m.stop,count=1000000);assert m.u.reg_read(UC_X86_REG_EIP)==stopAddress,(label,hex(m.u.reg_read(UC_X86_REG_EIP)));prefixFunction=0
 assert ne==oe,(label,'events prefix',[(x[:3],y[:3])for x,y in zip(ne,oe)if x!=y])
 assert raw(True)==raw(False),(label,'heap prefix',[(hex(BASE+i),a,b)for i,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:12])
 assert globalsRaw(True)==globalsRaw(False),(label,'globals prefix');prefixCount+=1;events+=len(ne)

def compareStalledRunner(label,duration,start):
 global prefixClockCallsite,prefixClocks,prefixCount,events,clockSequence
 prepare();compare(0x4ed670,EFFECT,[DESC],label+'init');clockSequence=[start];ctx.maximumClockReads=12;sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();args=(C.c_uint32*3)(duration,0,0)
 assert not lib.claw_player_fade_entry(0x4ec9c0,EFFECT,args,3,C.byref(ctx),dependency,None,C.byref(result)),label
 assert ctx.fault==2 and not errors,(label,ctx.fault,errors)
 prefixClockCallsite=0x4eca42;prefixClocks=12;m.u.mem_write(m.stack,struct.pack('<IIII',m.stop,duration,0,0));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,EFFECT);m.u.emu_start(0x4ec9c0,m.stop,count=1000000)
 assert m.u.reg_read(UC_X86_REG_EIP)==prefixClockCallsite,(label,hex(m.u.reg_read(UC_X86_REG_EIP)),len(oe))
 assert ne==oe,(label,'events');assert raw(True)==raw(False),(label,'heap');assert globalsRaw(True)==globalsRaw(False),(label,'globals')
 prefixClockCallsite=0;prefixClocks=0;clockSequence=None;ctx.maximumClockReads=10000;prefixCount+=1;events+=len(ne)

def verifyNumericProfile():
 # Independently execute all1025 actual CRT pow operand profiles, excluding
 # source wrapper EAX. No copied math implementation is the oracle.
 lib.claw_fade_test_square_bits.argtypes=[C.c_uint32];lib.claw_fade_test_square_bits.restype=C.c_uint64
 stub,inputToken,result=0x10fe000,0x10fe100,0x10fe120
 code=b'\xdd\x05'+struct.pack('<I',inputToken)+b'\xdd\x05'+struct.pack('<I',inputToken+8)+b'\xe8'+struct.pack('<i',0x4f1b30-(stub+17))+b'\xdd\x1d'+struct.pack('<I',result)+b'\xe9'+struct.pack('<i',m.stop-(stub+28))
 m.u.mem_write(stub,code)
 for x in range(1025):
  m.u.mem_write(inputToken,struct.pack('<dd',x,2));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.emu_start(stub,m.stop,count=100000)
  assert lib.claw_fade_test_square_bits(x)==struct.unpack('<Q',m.u.mem_read(result,8))[0],('original square bits',x)
 return 1025
