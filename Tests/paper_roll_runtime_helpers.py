"""Private original instruction oracle for the bounded circle fade graph."""
import ctypes as C, hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/paper-roll-agent'
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(ROOT/'Sources'/f'{name}.cpp')for name in('PaperRollRuntime','LightPaletteRuntime','PlayerFadeRuntime','PlayerFadeBlendRuntime','CArrayRuntime','ActorDestruction')],'-o',str(WORK/'libPlayerFadeBlendRuntime.dylib')],check=True)

class SCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Alloc=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('bypass',C.c_uint32)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('descriptorWord3',C.c_uint32),('temporaryDescriptorToken',C.c_uint32),('maximumClockReads',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6)]
Dep=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x120000
OWNER,PARENT,CTRL,IMAGE0,IMAGE1,SURFACE0,SURFACE1,DD0,DD1,DDVT,APP,MUSIC,MANAGER,ARRAY,DESC,SCRATCH,HOLDER,PALETTE,CAPTURE=[BASE+0x1000+i*0x100 for i in range(19)]
EFFECT=BASE+0x4000;PIXEL0=BASE+0x10000;PIXEL1=BASE+0x60000;PIXELCAP=BASE+0xb0000;NEWARRAY=BASE+0x2800
LOCK,UNLOCK,RESTORE=0x4b9730,0x10ff100,0x10ff110
CLOCK0,CLOCK1,PT,STRLEN,DECREMENT=0x10ff120,0x10ff130,0x10ff140,0x10ff150,0x10ff160
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);m.u.mem_map(BASE,SIZE);m.write_words(0x546a24,[CLOCK0]);m.write_words(0x546df0,[CLOCK1]);m.write_words(0x546cd4,[PT]);m.write_words(0x5469e4,[STRLEN]);m.write_words(0x5469e8,[DECREMENT]);m.executed.clear()
image=(C.c_uint8*0x148000).from_buffer_copy(m.u.mem_read(0x400000,0x148000));heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g);ctx.temporaryDescriptorToken=SCRATCH;ctx.maximumClockReads=10000
lib=C.CDLL(str(WORK/'libPlayerFadeBlendRuntime.dylib'))
class BlendContext(C.Structure):_fields_=[('fade',C.POINTER(Context)),('temporaryStringToken',C.c_uint32),('emptyStringToken',C.c_uint32),('uninitializedCapturePixelToken',C.c_uint32)]
PALOBJECT=BASE+0x2500;COLORS=BASE+0xa000
TEMP=BASE+0x2300;EMPTY=BASE+0x2400;STRING=BASE+0x9000;PALETTEPIX=BASE+0x100000
blend=BlendContext(C.pointer(ctx),TEMP,EMPTY+12,PIXELCAP)
lib.claw_player_fade_blend_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(BlendContext),Dep,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_player_fade_blend_entry.restype=C.c_uint32
lib.claw_player_fade_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_player_fade_entry.restype=C.c_uint32

rng=random.Random(0x48fae0);ne=[];oe=[];errors=[];calls=events=0;freed=[[],[]];clockState=[0,0];clockStart=100;clockDelta=25;clockSequence=None;clockIndices=[0,0];mutation=0;allocationFailure=False;globalSeed=b'';width=height=0;allocationCount=[0,0];allocationFailureOrdinal=-1;pixelMappings=None
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
 b=bytearray(bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)));b[SCRATCH-BASE:SCRATCH-BASE+36]=bytes(36);b[TEMP-BASE:TEMP-BASE+4]=bytes(4);return bytes(b)
def globalsRaw(native):
 if not native:return bytes(m.u.mem_read(0x528000,0x1c000))
 b=bytearray(globalSeed);struct.pack_into('<I',b,0x537238-0x528000,g.bypass);return bytes(b)
def snapshot(native):return hashlib.sha256(raw(native)).digest(),hashlib.sha256(globalsRaw(native)).digest(),tuple(freed[0 if native else 1]),tuple(get(EFFECT,24,native))
def effect(fn,receiver,args,native):
 i=0 if native else 1
 if fn==0x5469e4:
  text=args[0];data=(C.string_at(C.addressof(heap)+text-BASE,4096)if BASE<=text<BASE+SIZE else C.string_at(C.addressof(image)+text-0x400000,4096))if native else bytes(m.u.mem_read(text,4096));return len(data.split(b'\0',1)[0])
 if fn==0x4fb253:put(receiver,[EMPTY+12],native);return 0
 if fn in(0x546a24,0x546df0):
  if clockSequence:
   index=clockIndices[i];value=clockSequence[min(index,len(clockSequence)-1)];clockIndices[i]+=1
  else:value=clockState[i];clockState[i]=(value+clockDelta)&0xffffffff
  return value
 if fn==0x4f63ec:
  ordinal=allocationCount[i];allocationCount[i]+=1
  if allocationFailure or ordinal==allocationFailureOrdinal:return 0
  return EFFECT if args[0]==0x206c else PALOBJECT if args[0]==12 else PALETTEPIX if args[0]>=256 and args[0]%256==0 else NEWARRAY+ordinal*64 if args[0]in(4,16,32)else STRING
 if fn==0x4f6428:
  freed[i].append(args[0])
  if mutation==3:put(EFFECT+12,[NEWARRAY],native);put(NEWARRAY,[PALETTE],native);put(PALETTE,[0,77,PIXEL1],native)
  return 0
 if fn==0x4b9730:return (pixelMappings or {SURFACE0:PIXEL0,SURFACE1:PIXEL1,CAPTURE:PIXELCAP})[receiver]
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
 q=c.contents;a=list(q.arguments[:q.argumentCount]);
 if q.function in(0x4ec050,0x4ed800,0x4c6bd0,0x4c7510,0x4c61f0):
  result=C.c_uint32();values=(C.c_uint32*len(a))(*a)
  assert lib.claw_player_fade_blend_entry(q.function,q.receiver,values,len(a),C.byref(blend),dependency,None,C.byref(result)),(hex(q.function),ctx.fault)
  return result.value
 ne.append((q.function,q.receiver,tuple(a),snapshot(True)))
 try:return effect(q.function,q.receiver,a,True)
 except Exception as e:errors.append(e);return 0
COUNTS={0x4f63ec:1,0x4f6428:1,LOCK:1,UNLOCK:2,RESTORE:3,0x4b55a0:0,0x4b55b0:1,0x4bc960:5,0x4bc4f0:1,0x4b97c0:1,0x4b9c50:1,CLOCK0:0,CLOCK1:0,STRLEN:1,0x4fb253:1}
CDECL={0x4f63ec,0x4f6428,UNLOCK,RESTORE,CLOCK0,CLOCK1,STRLEN}
def hook(u,address,size,user):
 if address==0x4ed800:m.write_words(u.reg_read(UC_X86_REG_ESP)-0x1c,[blend.uninitializedCapturePixelToken])
 if address==DECREMENT:
  sp=u.reg_read(UC_X86_REG_ESP);token=m.read_words(sp+4,1)[0];value=(get(token,native=False)[0]-1)&0xffffffff;put(token,[value],False);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+8);return
 if address==0x4ecbc0:
  receiver=u.reg_read(UC_X86_REG_ECX)
  if 0x2000000<=receiver<0x2010000:m.write_words(receiver+12,[ctx.descriptorWord3])
 if address==PT:
  sp=u.reg_read(UC_X86_REG_ESP);rect,x,y=m.read_words(sp+4,3);l,t,r,b=m.read_words(rect,4);si=lambda v:C.c_int32(v).value;value=int(si(l)<=si(x)<si(r)and si(t)<=si(y)<si(b));u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+16);return
 if address not in COUNTS:return
 sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,COUNTS[address]);receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX);fn={CLOCK0:0x546a24,CLOCK1:0x546df0,STRLEN:0x5469e4}.get(address,address);oe.append((fn,receiver,tuple(a),snapshot(False)));v=effect(fn,receiver,a,False);u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in CDECL and address not in(UNLOCK,RESTORE,CLOCK0,CLOCK1,STRLEN)else COUNTS[address]*4))
transportHook=m.u.hook_add(UC_HOOK_CODE,hook)
def sync():
 global globalSeed
 m.u.mem_write(BASE,bytes(heap));m.write_words(0x537238,[g.bypass]);m.write_words(0x52e1c8,[EMPTY,EMPTY+12]);globalSeed=bytes(m.u.mem_read(0x528000,0x1c000));clockState[:]=[clockStart,clockStart];clockIndices[:]=[0,0];allocationCount[:]=[0,0]
def prepare(w=31,h=23,bpp=1,direction=1,pad=5):
 global width,height,mutation,allocationFailure,allocationFailureOrdinal
 width,height=w,h;mutation=0;allocationFailure=False;allocationFailureOrdinal=-1;ctx.fault=0;ctx.descriptorWord3=rng.getrandbits(32);g.bypass=0;C.memset(heap,0xa5,SIZE)
 for token,n in((EFFECT,2075),(MANAGER,10),(DESC,9),(OWNER,474),(APP,24)):
  put(token,[rng.getrandbits(32)for _ in range(n)])
 for surface,pixel,dd in((SURFACE0,PIXEL0,DD0),(SURFACE1,PIXEL1,DD1),(CAPTURE,PIXELCAP,DD1)):
  put(surface,[0]*48);put(surface+8,[dd]);put(surface+0x14,[h,w,w*bpp+pad]);put(surface+0xac,[bpp]);put(dd,[DDVT]);put(pixel,[rng.getrandbits(32)for _ in range((h*(w*bpp+pad)+3)//4)])
 put(DDVT+0x80,[UNLOCK]);put(DDVT+0x58,[RESTORE]);put(HOLDER,[DD0]);put(OWNER+4,[APP]);put(OWNER+0xc,[PARENT,MANAGER]);put(PARENT+4,[CTRL]);put(PARENT+0x1c,[1]);put(CTRL+0x10,[IMAGE0,IMAGE1]);put(IMAGE0+0x2c,[SURFACE0]);put(IMAGE1+0x2c,[SURFACE1]);put(APP+0x14,[1]);put(APP+0x50,[MUSIC]);put(MANAGER,[SURFACE0,SURFACE1,0,0,0x5141c0,ARRAY,0,4,0,HOLDER]);put(ARRAY,[0]*8);put(PALETTE+8,[PIXELCAP]);put(DESC,[2,SURFACE0,SURFACE1,ctx.descriptorWord3,direction,0,w//2,h//2,0]);put(EFFECT+0x1c,[0,0,SURFACE0,SURFACE1,HOLDER,1,0,SURFACE0,SURFACE1,0,ctx.descriptorWord3,direction,w//2,h//2,PIXEL0,PIXEL1,100]);put(EFFECT,[0x514250]);put(EFFECT+0x2060,[0,w,h]);put(EMPTY,[0xffffffff,0,0,0]);put(TEMP,[0xa5a5a5a5]);freed[0].clear();freed[1].clear();sync()
RETURNS={0x48fae0,0x48fbe0,0x4ec050,0x4ecbc0,0x4ecb30,0x4c61d0,0x4ec8d0,0x4ed5e0,0x4ed670,0x4ee6b0,0x4ed600,0x4ebf80,0x4f65f2,0x4f6433,0x4c76d0,0x4c76f0,0x4c7580,0x4c6bd0}
def compare(fn,t,a,label):
 global calls,events
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();args=(C.c_uint32*len(a))(*a)
 assert (lib.claw_player_fade_blend_entry(fn,t,args,len(a),C.byref(blend),dependency,None,C.byref(result))if fn in(0x4ed800,0x4ee170,0x4ec050,0x4ec6b0,0x4f65f2,0x4f6480,0x4f6433,0x4c6bd0,0x4c76d0,0x4c76f0,0x4c7580,0x4dee30,0x4c78d0,0x4c76e0,0x4c7510,0x4c6270,0x4c61f0)else lib.claw_player_fade_entry(fn,t,args,len(a),C.byref(ctx),dependency,None,C.byref(result))),(label,'native fault',ctx.fault,errors,[(hex(x[0]),hex(x[1]),x[2])for x in ne[-3:]])
 assert not errors,errors
 m.u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(a),*a));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);m.u.emu_start(fn,m.stop,count=100000000);assert m.u.reg_read(UC_X86_REG_EIP)==m.stop,(label,'original bound')
 original=m.u.reg_read(UC_X86_REG_EAX)
 if fn in RETURNS:assert original==result.value,(label,'return',original,result.value)
 if fn in(0x4f65f2,0x4f6480)and t==TEMP:assert get(TEMP)==get(TEMP,native=False),(label,'rawCStringcell')
 assert len(ne)==len(oe),(label,'event count',len(ne),len(oe))
 for i,(x,y)in enumerate(zip(ne,oe)):
  assert x==y,(label,'event',i,x[:3],y[:3],'snapshot differing',[(i,hex(a),hex(b))for i,(a,b)in enumerate(zip(x[3][3],y[3][3]))if a!=b])
 assert raw(True)==raw(False),(label,'complete heap',[(hex(BASE+i),a,b)for i,(a,b)in enumerate(zip(raw(True),raw(False)))if a!=b][:12])
 assert globalsRaw(True)==globalsRaw(False),(label,'globals')
 calls+=1;events+=len(ne)
 if calls%500==0:print('verified complete calls',calls,flush=True)

def gradientProfile(w=31,h=23,bpp=1,direction=1,gradient=3,pad=5,cx=None,cy=None):
 prepare(w,h,bpp,direction,pad);put(PALETTE+8,[PALETTEPIX]);data=bytes(rng.randrange(256)for _ in range(256*max(gradient,1)+16));C.memmove(C.addressof(heap)+PALETTEPIX-BASE,data,len(data));put(DESC+12,[PALETTE]);put(DESC+20,[gradient&0xffffffff]);put(DESC+32,[PALETTE]);put(DESC+24,[w//2 if cx is None else cx,h//2 if cy is None else cy]);compare(0x4ed670,EFFECT,[DESC],'initialize-gradient');compare(0x4ee6b0,EFFECT,[],'gradient-radius');compare(0x4ee820,EFFECT,[],'gradient-pre')

ByteLookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32)
class PaperContext(C.Structure):_fields_=[('common',C.POINTER(BlendContext)),('descriptorToken',C.c_uint32),('nameToken',C.c_uint32),('lookupToken',C.c_uint32),('stringToken',C.c_uint32),('maximumOperations',C.c_uint32),('soundEnabled',C.POINTER(C.c_uint32)),('soundVolume',C.POINTER(C.c_uint32)),('byteContext',C.c_void_p),('bytes',ByteLookup)]
NAME,OUTPUT,CSTRING,TABLE,ROWMEM=BASE+0x2a00,BASE+0x2b00,BASE+0x2c00,BASE+0x104000,BASE+0xd000
enabled=C.c_uint32(1);volume=C.c_uint32(70);paper=PaperContext(C.pointer(blend),SCRATCH,NAME,OUTPUT,CSTRING,1000000,C.pointer(enabled),C.pointer(volume))
lib.claw_paper_roll_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(PaperContext),Dep,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_paper_roll_entry.restype=C.c_uint32
oldEffect=effect
cursors=[ROWMEM,ROWMEM]
def effect(fn,r,a,native):
 i=0 if native else 1
 if fn==0x4f63ec:
  ordinal=allocationCount[i];allocationCount[i]+=1
  if allocationFailure or ordinal==allocationFailureOrdinal:return 0
  if a[0]==0x494:return EFFECT
  result=cursors[i];cursors[i]+=(a[0]+15)&~15;return result
 if fn==0x4f6439:put(r,[EMPTY+12],native);return r
 if fn==0x4f66cc:
  assert a[0]==0x534938;return r
 if fn==0x4c96b0:return 0
 return oldEffect(fn,r,a,native)
COUNTS.update({0x4f6439:0,0x4f66cc:1})
@Dep
def dependency(context,ep,user):
 q=ep.contents;a=list(q.arguments[:q.argumentCount])
 if q.function in(0x4ee880,0x4ee8e0,0x4ee8c0,0x4ee9a0,0x4eecc0,0x4efac0,0x4ec050,0x4c6260):
  out=C.c_uint32();args=(C.c_uint32*len(a))(*a);assert lib.claw_paper_roll_entry(q.function,q.receiver,args,len(a),C.byref(paper),dependency,None,C.byref(out)),(hex(q.function),ctx.fault);return out.value
 ne.append((q.function,q.receiver,tuple(a),snapshot(True)))
 try:return effect(q.function,q.receiver,a,True)
 except Exception as e:errors.append(e);return 0
baseSync=sync
def sync():
 baseSync();cursors[:]=[ROWMEM,ROWMEM]
baseRaw=raw
def raw(native):
 b=bytearray(baseRaw(native));b[SCRATCH-BASE:SCRATCH-BASE+52]=bytes(52);return bytes(b)
basePrepare=prepare
def prepare(w=320,h=17,bpp=1,direction=0,pad=5,radius=40,mode=3,lit=0):
 basePrepare(w,h,bpp,direction,pad);put(EFFECT,[0xa5a5a5a5]*(0x494//4));put(EFFECT,[0x514270]);put(EFFECT+0x24,[SURFACE0,SURFACE1,HOLDER]);put(DESC,[1,SURFACE0,SURFACE1,CAPTURE,radius,mode,direction,lit,TABLE,EMPTY+12,0,0x12345678,0xfedcba98]);
 for s in(SURFACE0,SURFACE1,CAPTURE):put(s+0xa4,[8 if bpp==1 else bpp*8])
 put(TABLE,[1,16384,PALETTEPIX]);data=bytes((x*17+x//64)%256 for x in range(16384));C.memmove(C.addressof(heap)+PALETTEPIX-BASE,data,len(data));sync()
RETURNS.update({0x4ee880,0x4ee8c0,0x4ee9a0,0x4efac0,0x4ecb40,0x42a4f0,0x48f500,0x48f740})
captures=[]
def compare(fn,t,a,label):
 global calls,events
 sync();before=bytes(heap);ctx.fault=0;ne.clear();oe.clear();errors.clear();result=C.c_uint32();argv=(C.c_uint32*len(a))(*a)
 assert lib.claw_paper_roll_entry(fn,t,argv,len(a),C.byref(paper),dependency,None,C.byref(result)),(label,ctx.fault,errors)
 assert not errors,errors
 m.call(fn,t,struct.pack('<'+'I'*len(a),*a),max_instructions=100000000)
 if fn in RETURNS:assert m.u.reg_read(UC_X86_REG_EAX)==result.value,(label,'EAX',m.u.reg_read(UC_X86_REG_EAX),result.value)
 if ne!=oe:
  for i,(x,y)in enumerate(zip(ne,oe)):
   if x!=y:print(label,'event',i,x[:3],y[:3],x[3]==y[3]);break
  raise AssertionError((label,'ordered snapshots',len(ne),len(oe)))
 assert raw(True)==raw(False),(label,'heap',[(hex(BASE+i),x,y)for i,(x,y)in enumerate(zip(raw(True),raw(False)))if x!=y][:12])
 assert globalsRaw(True)==globalsRaw(False),(label,'globals')
 pop={0x4ee8c0:4,0x4ee9a0:4,0x4eecc0:4,0x4ef010:8,0x4ef7d0:8,0x4ec050:8,0x4ec9c0:12,0x4ec600:4,0x48f500:4,0x48f740:20}.get(fn,0);assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+pop
 calls+=1;events+=len(ne)
 if fn==0x4eecc0 and isinstance(label,tuple) and label[0]=='retainedPixels' and label[1]in(1,3) and label[2]in(0,1) and label[3]in(1,3,4) and label[4]==321 and a[0]in(1,get(EFFECT+0x60)[0]//3):
  #Serialize only exact source allocations and physical buffers. Source pixel
  #body already compared whole heap; sanitizer replays these exact spans.
  blocks=[(EFFECT,0x494),(SURFACE0,188),(SURFACE1,188),(CAPTURE,188),(DD0,4),(DD1,4),(DDVT,132),(TABLE,12),(PALETTEPIX,16384)]
  for surface,pixels in((SURFACE0,PIXEL0),(SURFACE1,PIXEL1),(CAPTURE,PIXELCAP)):blocks.append((pixels,get(surface+20)[0]*get(surface+28)[0]))
  radius=get(EFFECT+0x58)[0];height=get(EFFECT+0x64)[0];width=get(EFFECT+0x60)[0];bpp=get(SURFACE0+0xac)[0]
  for field,count in((0x478,radius*8),(0x44,height*4),(0x48,height*4),(0x4c,height*4),(0x488,bpp*max(width,height)),(0x48c,radius*2)):
   token=get(EFFECT+field)[0]
   if token and count:blocks.append((token,count))
  path=WORK/'captures'/f'{len(captures)}.bin';path.parent.mkdir(exist_ok=True);payload=bytearray(struct.pack('<IIII',fn,t,a[0],len(blocks)))
  for token,count in blocks:payload+=struct.pack('<II',token,count)+before[token-BASE:token-BASE+count]+bytes(heap)[token-BASE:token-BASE+count]
  path.write_bytes(payload);captures.append(str(path));(WORK/'capture-manifest.txt').write_text('\n'.join(captures)+'\n')
 return result.value
RESOURCE,RESOURCEPCX,NAMESPACE,SOUNDREG,PALETTECTRL,PALETTEVT,APPVT=BASE+0x3000,BASE+0x3100,BASE+0x3200,BASE+0x3300,BASE+0x3400,BASE+0x3500,BASE+0x3600
READY,LOADPAL,INSTALLPAL=0x10ff180,0x10ff190,0x10ff1a0
resourceFailure=0;surfaceFailure=0;paletteFailure=0;copyFailure=0;lookupResult=0
bodyEffect=effect
def effect(fn,r,a,native):
 if fn==0x4bc670:return 0 if surfaceFailure else CAPTURE
 if fn==0x4bc520:return 0 if surfaceFailure else(CAPTURE if a[0]==PIXEL1 else SURFACE1)
 if fn==0x4b7f00:return 0 if resourceFailure else RESOURCE
 if fn==0x4b7dc0:return 0 if resourceFailure else RESOURCEPCX
 if fn==0x4b61c0:return get(r+16,native=native)[0]
 if fn==0x4b6230:return 0
 if fn==0x4b9c50 and copyFailure:return copyFailure
 if fn==0x4a3920:
  data=(('_SCREENS_'+bytes(m.u.mem_read(a[2],32)).split(b'\0')[0].decode())+'\0').encode()
  if native:C.memmove(C.addressof(heap)+a[0]-BASE,data,len(data))
  else:m.u.mem_write(a[0],data)
  return len(data)-1
 if fn==0x4f6286:put(a[1],[lookupResult],native);return int(bool(lookupResult))
 if fn==0x4f6584:return 0
 if fn==READY:return 1
 if fn==LOADPAL:return 0 if paletteFailure else PALETTE
 if fn in(INSTALLPAL,0x4bbf60,0x4bb870,0x4bb990,0x4b98b0,0x4bb8c0,0x4b45f0):return 0
 return bodyEffect(fn,r,a,native)
COUNTS.update({0x4bc670:5,0x4bc520:5,0x4b7f00:2,0x4b7dc0:2,0x4b61c0:0,0x4b6230:0,0x4a3920:3,0x4f6286:2,0x4f6584:0,READY:0,LOADPAL:3,INSTALLPAL:0,0x4bbf60:0,0x4bb870:0,0x4bb990:6,0x4b98b0:1,0x4bb8c0:1,0x4b45f0:4})
CDECL.add(0x4a3920)
#Normalize only synchronous stack-local transport addresses to caller scratch.
#Original descriptors/runners still execute; local initial11/12 are seeded
#through the observed stack descriptor boundary, not guessed heap ownership.
oldHook=hook;m.u.hook_del(transportHook)
localsMap={}
def norm(t):
 for source,(dest,length)in localsMap.items():
  if source<=t<source+length:return dest+t-source
 return t

def paperHook(u,address,size,user):
 if address==0x4ecb40:
  t=u.reg_read(UC_X86_REG_ECX)
  if 0x2000000<=t<0x2010000:localsMap[t]=(SCRATCH,52);m.write_words(t+44,get(SCRATCH+44,2))
 if address==0x4c96b0:oe.append((address,u.reg_read(UC_X86_REG_ECX),(),snapshot(False)))
 if address not in COUNTS:return oldHook(u,address,size,user)
 sp=u.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,COUNTS[address]);r=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX)
 if address==0x4a3920 and 0x2000000<=a[0]<0x2010000:localsMap[a[0]]=(NAME,64)
 if address==0x4f6286 and 0x2000000<=a[1]<0x2010000:localsMap[a[1]]=(OUTPUT,4)
 if address==0x4f6584 and norm(r)!=SCRATCH+36:return
 fn={CLOCK0:0x546a24,CLOCK1:0x546df0,STRLEN:0x5469e4}.get(address,address)
 oe.append((fn,norm(r),tuple(norm(v)for v in a),snapshot(False)))
 value=effect(fn,r,a,False);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in CDECL and address not in(UNLOCK,RESTORE,CLOCK0,CLOCK1,STRLEN)else COUNTS[address]*4))
m.u.hook_add(UC_HOOK_CODE,paperHook)
previousRaw=raw
def raw(native):
 b=bytearray(previousRaw(native));
 for token,size in[(NAME,64),(OUTPUT,4),(CSTRING,4)]:b[token-BASE:token-BASE+size]=bytes(size)
 return bytes(b)
previousSync=sync
def sync():
 previousSync();localsMap.clear();m.write_words(0x532c0c,[enabled.value,volume.value]);
 global globalSeed
 globalSeed=bytes(m.u.mem_read(0x528000,0x1c000))
previousPrepare=prepare
def prepare(w=320,h=17,bpp=1,direction=0,pad=5,radius=40,mode=3,lit=0):
 global resourceFailure,surfaceFailure,paletteFailure,copyFailure,lookupResult
 previousPrepare(w,h,bpp,direction,pad,radius,mode,lit)
 resourceFailure=surfaceFailure=paletteFailure=copyFailure=lookupResult=0
 put(APP,[APPVT]);put(APPVT+12,[READY]);put(APP+0x58,[1]);put(APP+0x8c,[TABLE]);put(OWNER+8,[NAMESPACE]);put(OWNER+32,[NAMESPACE]);put(OWNER+44,[PALETTE]);put(OWNER+60,[0,SURFACE1]);put(PARENT+24,[PALETTECTRL,1]);put(PARENT+40,[SOUNDREG]);put(SOUNDREG+48,[0]);put(PALETTECTRL,[PALETTEVT]);put(PALETTECTRL+100,[0]);put(PALETTEVT+48,[LOADPAL]);put(PALETTE,[PALETTEVT]);put(PALETTE+16,[1]);put(PALETTEVT+52,[INSTALLPAL]);put(RESOURCE+16,[PIXELCAP,300]);put(RESOURCEPCX+16,[PIXEL1,301]);sync()
loadEffect=effect
getterFailure=0
payloadFailure=0
paletteLoadFailure=0
def effect(fn,r,a,native):
 if fn==READY:return 0 if getterFailure else 1
 if fn==0x4b61c0 and payloadFailure:return 0
 if fn==0x4c7360:return 0 if paletteLoadFailure else TABLE
 return loadEffect(fn,r,a,native)
COUNTS[0x4c7360]=2
prefixAddress=0;prefixes=0
def prefixHook(u,address,size,user):
 if prefixAddress and address==prefixAddress:u.emu_stop()
m.u.hook_add(UC_HOOK_CODE,prefixHook)
def comparePrefix(fn,t,a,label,fault,address):
 global prefixAddress,prefixes,events
 sync();ctx.fault=0;ne.clear();oe.clear();errors.clear();out=C.c_uint32();argv=(C.c_uint32*len(a))(*a)
 assert not lib.claw_paper_roll_entry(fn,t,argv,len(a),C.byref(paper),dependency,None,C.byref(out)),label
 assert ctx.fault==fault,(label,ctx.fault,errors)
 prefixAddress=address;m.u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(a),*a));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);m.u.emu_start(fn,m.stop,count=100000000);assert m.u.reg_read(UC_X86_REG_EIP)==address,(label,hex(m.u.reg_read(UC_X86_REG_EIP)));prefixAddress=0
 assert ne==oe,(label,'prefixEvents');assert raw(True)==raw(False),(label,'prefixHeap');assert globalsRaw(True)==globalsRaw(False),(label,'prefixGlobals');prefixes+=1;events+=len(ne)
