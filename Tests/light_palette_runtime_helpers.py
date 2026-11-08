"""Private hash-pinned light-palette whole-entry oracle. Numeric/MFC services explicit."""
import ctypes as C,struct,random,subprocess,hashlib,math
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_FPSW,UC_X86_REG_FP0
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/light-palette-agent'
SOURCES=['LightPaletteRuntime','PlayerFadeBlendRuntime','PlayerFadeRuntime','CArrayRuntime','ActorDestruction','SpriteGeometry','PIDBlitter','PIDRaster','PIDSurfaceRaster']
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{s}.cpp')for s in SOURCES],'-o',str(WORK/'libLightPalette.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,U)for n in('temporaryFileToken','composeCore','maximumSteps','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',UP*2),('bufferBytes',U*2),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(WORK/'libLightPalette.dylib'));lib.claw_light_palette_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_light_palette_entry.restype=U
BASE,SIZE=0x1000000,0x100000;GS,GN=0x500000,0x50000
OWNER,APP,MANAGER,DATA,RESOURCE,RESOURCE2,SCRATCH,OBJECT,ARRAY,PALETTE,LEFT,RIGHT=[BASE+0x1000+i*0x1000 for i in range(12)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);m.executed.clear();seedGlobals=bytes(u.mem_read(GS,GN));raw=(C.c_uint8*GN).from_buffer_copy(seedGlobals);heap=(C.c_uint8*SIZE)();native=True;events=[];errors=[];calls=snapshots=0;cursor=0x20000;allocCount=0;live=[];allocationFail=0;resources={};localFile=0;maxRead=None;tableGrowth=0;numericCalls=0;hashEvents=False;prefixStop=0;sourceStopped=False
DATA=BASE+0x50000
READ=m.read_words(0x5142f4+60,1)[0]
def addr(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if GS<=t and t+n*4<=GS+GN:return C.addressof(raw)+t-GS
 return None
def get(t,n=1):return list((U*n).from_address(addr(t,n)))if native else m.read_words(t,n)
def put(t,v):
 if native:(U*len(v)).from_address(addr(t,len(v)))[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def getBytes(t,n):return C.string_at(addr(t&~3)+t%4,n)if native else bytes(u.mem_read(t,n))
def putBytes(t,b):
 if native:C.memmove(addr(t&~3)+t%4,b,len(b))
 else:u.mem_write(t,b)
def image():
 b=bytearray(heap if native else bytes(u.mem_read(BASE,SIZE)))
 #Native caller scratch represents the original local object, no heapidentity.
 b[SCRATCH-BASE:SCRATCH-BASE+40]=bytes(40);return bytes(b)
def snapshot():
 a=image();b=bytes(raw)if native else bytes(u.mem_read(GS,GN));return(a,b,cursor,allocCount,tuple(live))
def eventSnapshot():
 s=snapshot();return(hashlib.sha256(s[0]).digest(),hashlib.sha256(s[1]).digest(),*s[2:])if hashEvents else s
@Lookup
def lookup(_,t,n):return addr(t,n)
@Allocate
def allocate(_,n):return effect(0x4f63ec,0,[n])
@Free
def free(_,t):effect(0x4f6428,0,[t])
@Invoke
def invoke(_,e):return effect(e.function,e.receiver,list(e.arguments[:e.argumentCount]))
@Clock
def clock(_):raise AssertionError('unexpected clock')
host=Host(None,lookup,allocate,free,invoke,clock);ctx=Context(host,SCRATCH,1,1000000,0)
# Exact numeric source services have independent hash-pinned executable state.
num=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');nu=num.u;num.executed.clear()
NUCODE,NUBASE,NUEXP,NUOUT=0x10ff000,0x10ff100,0x10ff108,0x10ff110
powCache={};sortCalls=0

def sourcePow(base,exponent):
 key=struct.pack('<2d',base,exponent)
 if key in powCache:return powCache[key]
 nu.mem_write(NUBASE,key);code=b'\xdd\x05'+struct.pack('<I',NUBASE)+b'\xdd\x05'+struct.pack('<I',NUEXP);callAt=NUCODE+len(code);code+=b'\xe8'+struct.pack('<i',0x4f1b30-(callAt+5));code+=b'\xdd\x1d'+struct.pack('<I',NUOUT);code+=b'\xc3';nu.mem_write(NUCODE,code);num.call(NUCODE,0);v=struct.unpack('<Q',nu.mem_read(NUOUT,8))[0];powCache[key]=v;return v

def sourceSort(data,count,size,compare):
 global sortCalls
 s=snapshot();nu.mem_write(BASE,s[0]);nu.mem_write(GS,s[1]);num.call(0x4f1e20,0,struct.pack('<4I',data,count,size,compare));putBytes(data,bytes(nu.mem_read(data,count*size)));sortCalls+=1

def effect(f,t,args,local=False,fileBuffer=None):
 global cursor,allocCount,localFile,numericCalls
 extra=tuple(fileBuffer)if local and f!=0x4ff5f9 else ();events.append(((f,0 if local else t,tuple(args),extra),eventSnapshot()))
 if f==0x4f63ec:
  allocCount+=1
  if allocationFail==allocCount:return 0
  n=args[0];assert n<=0x40000,('allocation size',n);token=BASE+cursor;cursor=(cursor+n+31)&~15;assert cursor<SIZE;live.append(token);return token
 if f==0x4f6428:
  token=args[0];assert token in live,hex(token);live.remove(token);return 0
 if f==0x4b7dc0:return resources.get(args[0],0)
 if f==0x4b61c0:return get(t+0x10)[0]
 if f==0x4b6230:return 0
 if f==0x4ff5f9:
  fileBuffer[:]=[0x5142f4,0xffffffff,0,0,args[0],0,0,0,0,1];return 0
 if f==0x4ff645:
  data,size,grow=args;fileBuffer[4:10]=[grow,0,size,size if not grow else 0,data,0];return 0
 if f==READ:
  buffer=fileBuffer if local else get(t,10);target,n=args;left=max(0,buffer[7]-buffer[5]);actual=min(n,left,maxRead if maxRead is not None else n);putBytes(target,getBytes(buffer[8]+buffer[5],actual));buffer[5]+=actual
  if not local:put(t,buffer)
  return actual
 if f==0x4ff682:fileBuffer[4:10]=[0,0,0,0,0,0];return 0
 if f==0x4f1b30:numericCalls+=1;return sourcePow(*struct.unpack('<2d',struct.pack('<4I',*args)))
 if f==0x4f1e20:sourceSort(*args);return 0
 raise AssertionError((hex(f),hex(t),args,local))
@Dependency
def dependency(c,e,_):
 try:
  q=e.contents;buf=(U*10).from_address(C.addressof(q.buffers[0].contents))if q.localMask else None
  return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]),bool(q.localMask),buf)
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0

def returned(pop,value):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop*4);u.reg_write(UC_X86_REG_EIP,ret)
services={0x4f63ec:(1,0,True),0x4f6428:(1,0,True),0x4b7dc0:(2,2,False),0x4b61c0:(0,0,False),0x4b6230:(0,0,False),0x4ff5f9:(1,1,False),0x4ff645:(3,3,False),0x4ff682:(0,0,False),READ:(2,2,False)}
def hook(_,address,size,user):
 global localFile,sourceStopped
 if address==prefixStop:sourceStopped=True;u.emu_stop();return
 if address==0x4f1b30:
  top=(u.reg_read(UC_X86_REG_FPSW)>>11)&7
  def floating(i):
   mantissa,exponent=u.reg_read(UC_X86_REG_FP0+((top+i)&7));v=math.ldexp(mantissa,(exponent&0x7fff)-16383-63);return -v if exponent&0x8000 else v
  exponent,base=floating(0),floating(1)
  if exponent!=1:effect(address,0,list(struct.unpack('<4I',struct.pack('<2d',base,exponent))))
 if address in services:
  n,pop,cdecl=services[address];t=0 if cdecl else u.reg_read(UC_X86_REG_ECX);a=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,n)
  if address==0x4ff5f9:localFile=t
  isLocal=t==localFile and t!=0;buf=(U*10)(*m.read_words(t,10))if isLocal else None
  if address==0x4ff5f9:buf=(U*10)(*([0]*10)) #Caller-local seed is explicit.
  value=effect(address,t,a,isLocal,buf)
  if isLocal:m.write_words(t,list(buf))
  returned(pop,value)
u.hook_add(UC_HOOK_CODE,hook)
def setup(seed=0):
 global native,cursor,allocCount,live,allocationFail,resources,localFile,maxRead,hashEvents,prefixStop,sourceStopped
 native=True;r=random.Random(seed);C.memmove(heap,r.randbytes(SIZE),SIZE);C.memmove(raw,seedGlobals,GN);cursor=0x20000;allocCount=0;live=[];allocationFail=0;resources={};localFile=0;maxRead=None;hashEvents=False;prefixStop=0;sourceStopped=False;ctx.composeCore=1;ctx.maximumSteps=1000000;ctx.temporaryFileToken=SCRATCH;put(SCRATCH,[0]*10);put(OWNER,[0]*478);put(OWNER+4,[APP]);put(OWNER+28,[BASE+0x12000]);put(APP,[0]*77);put(APP+0x58,[MANAGER]);put(APP+0x78,[8]);put(MANAGER,[0,0x5136e8,0,0,0,0]);put(PALETTE,[r.getrandbits(32)for _ in range(256)]);put(OWNER+0x360,get(PALETTE,256));put(OBJECT,[0,0,0]);put(RESOURCE,[0]*6);put(RESOURCE2,[0]*6)
cdecl={0x4c7580,0x4c70b0,0x4c60a0};meaningful={0x46e160,0x4c61d0,0x4c6260,0x4c7360,0x4c7730,0x4c7850,0x4c68e0,0x4c6d90,0x4c6fa0,0x4c70b0,0x4c76d0,0x4c76f0,0x4c7580}
def execute(f,t,args=(),allowFault=False):
 global calls,snapshots
 events.clear();errors.clear()
 if native:
  aa=(U*len(args))(*(a&0xffffffff for a in args));out=U();assert lib.claw_light_palette_entry(f,t,aa,len(args),C.byref(ctx),dependency,None,C.byref(out));ret=out.value
  if not allowFault:assert not ctx.fault,(hex(f),ctx.fault,errors);assert not errors,errors
 else:
  packed=struct.pack('<'+'I'*len(args),*(a&0xffffffff for a in args));u.mem_write(m.stack,struct.pack('<I',m.stop)+packed);u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,t);u.emu_start(f,m.stop,count=600000000);assert u.reg_read(UC_X86_REG_EIP)==m.stop,'original instruction bound';ret=u.reg_read(UC_X86_REG_EAX);assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(0 if f in cdecl else len(args)*4),(hex(f),'stack')
 calls+=1;snapshots+=len(events);return snapshot(),list(events),ret if f in meaningful else 0

def restore(s):
 global cursor,allocCount,live,localFile
 if native:C.memmove(heap,s[0],SIZE);C.memmove(raw,s[1],GN)
 else:u.mem_write(BASE,s[0]);u.mem_write(GS,s[1])
 cursor,allocCount,live=s[2],s[3],list(s[4]);localFile=0

def compare(f,t,args=()):
 global native
 native=True;before=snapshot();a=execute(f,t,args);native=False;restore(before);b=execute(f,t,args)
 if a!=b:
  for z,(x,y)in enumerate(zip(a[0][:2],b[0][:2])):
   print('diff',hex(f),z,[(hex((BASE if z==0 else GS)+i),x[i:i+4].hex(),y[i:i+4].hex())for i in range(0,len(x),4)if x[i:i+4]!=y[i:i+4]][:20])
  print('events',[e[0]for e in a[1]][:15],[e[0]for e in b[1]][:15]);print('results',a[2],b[2]);
  for i,(x,y)in enumerate(zip(a[1],b[1])):
   if x!=y:print('first event difference',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(hex(f))
 native=True;restore(a[0]);return a
prefixes=0

def comparePrefix(f,t,args,stop,fault):
 global native,prefixStop,sourceStopped,prefixes
 native=True;before=snapshot();a=execute(f,t,args,True);assert ctx.fault==fault and not errors,(ctx.fault,errors);native=False;restore(before);events.clear();sourceStopped=False;prefixStop=stop;packed=struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args));u.mem_write(m.stack,struct.pack('<I',m.stop)+packed);u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,t);u.emu_start(f,m.stop,count=500000);assert sourceStopped and u.reg_read(UC_X86_REG_EIP)==stop;assert a[0]==snapshot() and a[1]==events,(hex(f),'prefix mismatch');native=True;restore(a[0]);prefixStop=0;prefixes+=1
