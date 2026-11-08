"""Whole original PAL/palette graph; physical COM/GDI/resource/map transports explicit."""
import ctypes as C,struct,random,subprocess,hashlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_ESI
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/palette-resource-agent';SOURCES=['PaletteResourceRuntime','AmbientAudioBackendRuntime','AudioEvents']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in SOURCES],'-o',str(WORK/'libPaletteResource.dylib')],check=True)
U=C.c_uint32;UP=C.POINTER(U)
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[('cooperativeHolder',U)]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals))]+[(n,U)for n in('systemPaletteScratchToken','composeLists','maximumSteps','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('argumentCount',U),('arguments',U*8),('localMask',U),('bufferCount',U),('buffers',UP*2),('bufferBytes',U*2)]
Dependency=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(WORK/'libPaletteResource.dylib'));lib.claw_palette_resource_entry.argtypes=[U,U,UP,U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_palette_resource_entry.restype=U
lib.claw_palette_resource_capture_owner.argtypes=[U,C.POINTER(Context),Dependency,C.c_void_p,UP];lib.claw_palette_resource_capture_owner.restype=U
BASE,SIZE=0x1000000,0x100000;GS,GN=0x500000,0x50000
MANAGER,BACKEND,OBJECT,SCENE,OWNER,HOLDER,TARGET,SURFACE,DEVICE,DVT,PVT,DD,SVT,RESOURCE,DATA,NAME,MAPSLOT,SCRATCH,QUAD=[BASE+0x1000*(i+1)for i in range(19)];DATA=BASE+0x50000;QUAD=DATA+0x1000
CREATE,GET,SET,COOP,ASSIGN=[BASE+0xee000+i*16 for i in range(5)];PAL=BASE+0x18000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);m.executed.clear();seedGlobals=bytes(u.mem_read(GS,GN));raw=(C.c_uint8*GN).from_buffer_copy(seedGlobals);heap=(C.c_uint8*SIZE)();native=True;events=[];errors=[];cursor=0x20000;allocCount=0;live=[];allocationFail=0;calls=snapshots=0;physical={};clockValues=[];clockLast=0;dcValue=1;capsSize=256;capsReserved=20;systemReturns=[1,1];hrCreate=hrGet=hrSet=hrAssign=0;lockValue=0;prefixStop=0;stopped=False
G=Globals();ctx=None
imports={n:BASE+0xed100+i*16 for i,n in enumerate((0x546910,0x546894,0x546914,0x5468b0,0x546df0))}
def addr(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if GS<=t and t+n*4<=GS+GN:return C.addressof(raw)+t-GS
 return None
def get(t,n=1):return list((U*n).from_address(addr(t,n)))if native else m.read_words(t,n)
def put(t,v):
 if native:(U*len(v)).from_address(addr(t,len(v)))[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
 if t==0x541374:G.cooperativeHolder=v[0]if native else G.cooperativeHolder

def getBytes(t,n):return C.string_at(addr(t&~3)+t%4,n)if native else bytes(u.mem_read(t,n))
def putBytes(t,b):
 if native:C.memmove(addr(t&~3)+t%4,b,len(b))
 else:u.mem_write(t,b)
def snapshot():
 b=bytearray(heap if native else u.mem_read(BASE,SIZE));b[SCRATCH-BASE:SCRATCH-BASE+1024]=bytes(1024);g=bytes(raw)if native else bytes(u.mem_read(GS,GN));return(hashlib.sha256(b).digest(),hashlib.sha256(g).digest(),cursor,allocCount,tuple(live),tuple(sorted(physical.items())),tuple(clockValues),clockLast)
@Lookup
def lookup(_,t,n):return addr(t,n)
@Allocate
def allocate(_,n):return effect(0x4f63ec,0,[n])
@Free
def free(_,t):effect(0x4f6428,0,[t])
@Invoke
def invoke(_,e):return effect(e.function,e.receiver,list(e.arguments[:e.argumentCount]))
@Clock
def clock(_):return effect(0x546df0,0,[])
host=Host(None,lookup,allocate,free,invoke,clock);ctx=Context(host,C.pointer(G),SCRATCH,1,1000000,0)
def effect(f,t,a,mask=0,buffer=None):
 global cursor,allocCount,clockLast,systemReturns
 payload=bytes(buffer)if buffer is not None else b''
 #GetSystemPaletteEntries output-only local contents have no input semantics;
 #positive fixture services write the complete requested span.
 if f==0x546914:payload=b''
 events.append(((f,t,tuple(a),mask,payload),snapshot()))
 if f==0x4f63ec:
  allocCount+=1
  if allocationFail==allocCount:return 0
  n=a[0];assert n<0x80000;out=BASE+cursor;cursor=(cursor+n+31)&~15;assert cursor<0xee000;live.append(out);return out
 if f==0x4f6428:
  assert a[0]in live,hex(a[0]);live.remove(a[0]);return 0
 if f==CREATE:
  assert a[1]==0x44 or a[1]==0x1234 or a[1]==0 or a[1]==0xffffffff
  token=PAL+len(physical)*16;put(token,[PVT]);put(a[3],[token if not hrCreate else 0]);physical[token]=payload;return hrCreate
 if f==GET:
  token,flags,start,count,dst=a;data=physical.get(token,b'\x5a'*1024)[start*4:(start+count)*4]
  if buffer is not None:buffer[:]=data
  else:putBytes(dst,data)
  return hrGet
 if f==SET:
  token,flags,start,count,entries=a;previous=bytearray(physical.get(token,b'\x5a'*1024));previous[start*4:(start+count)*4]=payload;physical[token]=bytes(previous);return hrSet
 if f==COOP:return 0
 if f==ASSIGN:return hrAssign
 if f==0x4bd260:return 0
 if f==0x4b61c0:return lockValue
 if f==0x4b6230:return 0
 if f==0x4d6560:
  #Explicit unrecovered file-loading boundary for the optional wrapper route.
  #The transport writes the same configured existing backend identity.
  put(t+16,[get(MAPSLOT+4)[0]]);return int(get(MAPSLOT+4)[0]!=0)
 if f==0x4f62a8:return MAPSLOT
 if f==0x546df0:
  clockLast=clockValues.pop(0)if clockValues else (clockLast+7)&0xffffffff;return clockLast
 if f==0x546910:return dcValue
 if f==0x546894:return capsSize if a[1]==104 else capsReserved
 if f==0x5468b0:return 1
 if f==0x546914:
  start,count=a[1:3];ret=systemReturns.pop(0)if systemReturns else 1
  if ret and buffer is not None:buffer[:]=bytes(v for i in range(count)for v in(((start+i)*3&255,(start+i)*5&255,(start+i)*7&255,0xaa)))
  return ret
 raise AssertionError((hex(f),hex(t),a,mask))
@Dependency
def dependency(c,e,_):
 try:
  q=e.contents;buf=(C.c_uint8*q.bufferBytes[0]).from_address(C.addressof(q.buffers[0].contents))if q.bufferCount else None
  return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]),q.localMask,buf)
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0

def returned(pop,v):
 sp=u.reg_read(UC_X86_REG_ESP);ip=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_ESP,sp+4+pop*4);u.reg_write(UC_X86_REG_EIP,ip)
services={0x4f63ec:(1,0,True),0x4f6428:(1,0,True),CREATE:(5,5,True),GET:(5,5,True),SET:(5,5,True),COOP:(3,3,True),ASSIGN:(2,2,True),0x4bd260:(3,0,True),0x4b61c0:(0,0,False),0x4b6230:(0,0,False),0x4f62a8:(1,1,False),0x4d6560:(2,2,False)}
for slot,n in((0x546910,4),(0x546894,2),(0x546914,4),(0x5468b0,1),(0x546df0,0)):services[imports[slot]]=(n,n,True)
def hook(_,f,n,user):
 global stopped
 if f==0x4bbf60:
  #Explicit caller-stack seed profile for the original uninitialized local.
  #This initializes fixture memory before the unchanged function allocates it.
  u.mem_write(u.reg_read(UC_X86_REG_ESP)-1024,getBytes(SCRATCH,1024))
 if f==prefixStop:stopped=True;u.emu_stop();return
 if f not in services:return
 count,pop,cdecl=services[f];a=m.read_words(u.reg_read(UC_X86_REG_ESP)+4,count);t=0 if cdecl else u.reg_read(UC_X86_REG_ECX);logical=next((slot for slot,value in imports.items()if f==value),f);mask=0;buf=None;token=None;size=0
 if logical==CREATE:
  token=a[2];size=1024
  if token>=0x2000000:mask=4;a[2]=0
 elif logical in(GET,SET):token=a[4];size=a[3]*4
 elif logical==0x4f62a8:
  token=a[0];size=0
  while bytes(u.mem_read(token+size,1))!=b'\0':size+=1
  size+=1
  if token>=0x2000000:mask=1;a[0]=0
 elif logical==0x546914:token=a[3];size=a[2]*4;mask=8;a[3]=0
 if token is not None:buf=(C.c_uint8*size).from_buffer_copy(bytes(u.mem_read(token,size)))
 v=effect(logical,t,a,mask,buf)
 if token is not None and size:u.mem_write(token,bytes(buf))
 returned(pop,v)
u.hook_add(UC_HOOK_CODE,hook)
def setup(seed=0):
 global native,cursor,allocCount,live,allocationFail,physical,clockValues,clockLast,dcValue,capsSize,capsReserved,systemReturns,hrCreate,hrGet,hrSet,hrAssign,lockValue,prefixStop,stopped
 native=True;r=random.Random(seed);C.memmove(heap,r.randbytes(SIZE),SIZE);C.memmove(raw,seedGlobals,GN);cursor=0x20000;allocCount=0;live=[];allocationFail=0;physical={};clockValues=[];clockLast=0;dcValue=1;capsSize=256;capsReserved=20;systemReturns=[1,1];hrCreate=hrGet=hrSet=hrAssign=0;lockValue=DATA;prefixStop=0;stopped=False;ctx.fault=0
 for slot,token in imports.items():put(slot,[token]);putBytes(token,b'\xc3')
 put(MANAGER,[0]*26);put(MANAGER,[0x513b28]);put(MANAGER+12,[SCENE]);put(MANAGER+28,[BACKEND]);put(BACKEND,[0]*543);put(BACKEND,[DEVICE]);put(BACKEND+0x3d4,[0x51000c,0,0,0,0,0,10]);put(SCENE,[0]*12);put(SCENE+4,[HOLDER]);put(SCENE+28,[BACKEND]);put(OBJECT,[0x513d78,0x1234,0,SCENE,0]);put(RESOURCE,[NAME,0,0,0,DATA,768]);putBytes(NAME,b'MAIN\0');put(DEVICE,[DVT]);put(DVT,[0]*24);put(DVT+20,[CREATE]);put(DVT+0x58,[COOP]);put(PVT,[0]*8);put(PVT+16,[GET,0,SET]);put(HOLDER,[DD,0,0,0,TARGET]);put(DD,[DVT]);put(TARGET,[0]*12);put(TARGET+24,[8]);put(TARGET+44,[SURFACE]);put(SURFACE,[0,0,DD]);put(DVT+0x7c,[ASSIGN]);put(OWNER,[0]*478);put(OWNER+44,[OBJECT]);put(0x541374,[0]);put(SCRATCH,[0]*256);putBytes(DATA,bytes(i%256 for i in range(768)));putBytes(QUAD,bytes(i%256 for i in range(1024)))
meaningful={0x4bcac0,0x4bcbc0,0x4bcb40,0x4bb100,0x4bb240,0x4bb5a0,0x4d65a0,0x4d65e0,0x4d6620,0x4d4420,0x4d44f0,0x4d4570,0x4d47f0,0x4bb800,0x4bb910,0x4bbf60,0x4b96f0,0x4d6690}
def state():return(bytes(heap),bytes(raw),cursor,allocCount,live.copy(),physical.copy(),clockValues.copy(),clockLast,systemReturns.copy())
def restore(s):
 global cursor,allocCount,live,physical,clockValues,clockLast,systemReturns
 b,g,cursor,allocCount,live,physical,clockValues,clockLast,systemReturns=s;C.memmove(heap,b,SIZE);C.memmove(raw,g,GN);live=live.copy();physical=physical.copy();clockValues=clockValues.copy();systemReturns=systemReturns.copy();G.cooperativeHolder=get(0x541374)[0]
def execute(f,t,a=(),allowFault=False):
 global calls,snapshots
 events.clear();errors.clear();out=U();args=(U*len(a))(*[v&0xffffffff for v in a])
 if native:
  recognized=lib.claw_palette_resource_capture_owner(t,C.byref(ctx),dependency,None,C.byref(out))if f==0x46afe9 else lib.claw_palette_resource_entry(f,t,args,len(a),C.byref(ctx),dependency,None,C.byref(out));assert recognized and (not ctx.fault or allowFault),(hex(f),ctx.fault,errors);assert not errors,errors;value=out.value
 else:
  if f==0x46afe9:
   m.write_words(m.stack,[m.stop]);u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ESI,t);u.reg_write(UC_X86_REG_EAX,get(t+44)[0]);u.emu_start(f,0x46b003,count=1000);assert u.reg_read(UC_X86_REG_EIP)==0x46b003;value=u.reg_read(UC_X86_REG_EAX)
  elif prefixStop:
   m.write_words(m.stack,[m.stop,*a]);u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,t);u.emu_start(f,m.stop,count=10000000);assert stopped and u.reg_read(UC_X86_REG_EIP)==prefixStop;value=u.reg_read(UC_X86_REG_EAX)
  else:value=m.call(f,t,struct.pack('<'+'I'*len(a),*[v&0xffffffff for v in a]),max_instructions=10000000)
 calls+=1;snapshots+=len(events);return(snapshot(),events.copy(),value if f in meaningful or f==0x46afe9 else None)
def compare(f,t,a=()):
 global native
 native=True;before=state();one=execute(f,t,a);after=state();native=False;b,g,*_=before;u.mem_write(BASE,b);u.mem_write(GS,g);restore(before);native=False;two=execute(f,t,a)
 assert one==two,(hex(f),'state/ordered events/result mismatch',one[2],two[2],len(one[1]),len(two[1]),[(i,one[1][i][0],two[1][i][0])for i in range(min(len(one[1]),len(two[1])))if one[1][i]!=two[1][i]][:2])
 native=True;restore(after);return one
def comparePrefix(f,t,a,stop,fault):
 global native,prefixStop
 native=True;before=state();one=execute(f,t,a,True);assert ctx.fault==fault;after=state();native=False;b,g,*_=before;u.mem_write(BASE,b);u.mem_write(GS,g);restore(before);native=False;prefixStop=stop;two=execute(f,t,a);prefixStop=0;assert one[:2]==two[:2],(hex(f),'unsafe prefix mismatch');native=True;restore(after)
