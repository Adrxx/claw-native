"""Private full-buffer oracle for GameFrameServices; external services declared."""
import ctypes as C, struct, random, subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/game-frame-services-agent';WORK.mkdir(exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/GameFrameServices.cpp'),'-o',str(WORK/'libGameFrameServices.dylib')],check=True)
lib=C.CDLL(str(WORK/'libGameFrameServices.dylib'))
class ActorCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,ActorCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in('stageDelta','playerToken','accumulatedTick','debugFlags')]+[('overlayRect',C.c_uint32*4),('posePacket',C.c_uint32*5),('lastPose',C.c_uint32*4),('rankingTimer',C.c_uint32),('audioEnabled',C.c_uint32),('overallVolume',C.c_uint32)]
GADDR=[0x53720c,0x537e88,0x537210,0x537264,*range(0x5370c8,0x5370d8,4),*range(0x53abc0,0x53abd4,4),*range(0x52a7bc,0x52a7cc,4),0x52a7cc,0x532c0c,0x532c10]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*8),('localMask',C.c_uint32),('bufferCount',C.c_uint32),('buffers',C.c_void_p*4),('bufferBytes',C.c_uint32*4)]
class Context(C.Structure):_fields_=[('host',Host),('globals',C.POINTER(Globals)),('composeMessages',C.c_uint32),('fault',C.c_uint32)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),Call,C.c_void_p)
lib.claw_game_frame_service_entry.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_game_frame_service_entry.restype=C.c_uint32
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);m.executed.clear()
BASE,SIZE=0x1000000,0x10000;heap=(C.c_uint8*SIZE)();globals=Globals();native=True;events=[];policy=0;receiveIndex=0;calls=eventCount=0;errors=[]
OWNER=BASE+0x1000;MGR=BASE+0x3000;CFG=BASE+0x3100;SCENE=BASE+0x3200;SURFACE=BASE+0x3300;DRAW=BASE+0x3400;BACKEND=BASE+0x3500;IFACE=BASE+0x3600;CONT=BASE+0x3700;OTHER=BASE+0x3800;OTHERCONT=BASE+0x3900;SOUNDREG=BASE+0x3a00;RESOURCE=BASE+0x3b00
NET=BASE+0x4000;COM=BASE+0x4100;PEER=BASE+0x5000;PACKET=BASE+0x5100;PLAYER=BASE+0x6000;LOGIC=BASE+0x6200;PRIVATE=BASE+0x6400;STRING=BASE+0x6500;VT=BASE+0x100;CVT=BASE+0x200;IVT=BASE+0x300
ITEMS=[BASE+0x7000+i*0x100 for i in range(10)];ACTORS=[BASE+0x8000+i*0x200 for i in range(10)];NODES=[BASE+0xa000+i*0x20 for i in range(10)]
FSTATE,FCOUNT,FFONT,FQUERY,FRECEIVE,FGETDC,FRELEASE=[0x10f0000+i*0x10 for i in range(7)]
IMPORTS={0x546888:0x10f0100,0x546880:0x10f0110,0x546890:0x10f0120,0x546d30:0x10f0130};REVIMPORTS={v:k for k,v in IMPORTS.items()}
for slot,fn in IMPORTS.items():m.write_words(slot,[fn])
def words(t,n=1):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,v):
 if native:(C.c_uint32*len(v)).from_address(C.addressof(heap)+t-BASE)[:]=[x&0xffffffff for x in v]
 else:m.write_words(t,v)
def gv():return list(struct.unpack('<20I',bytes(globals)))if native else [m.read_words(a,1)[0]for a in GADDR]
def setg(i,v):
 if native:(C.c_uint32*20).from_address(C.addressof(globals))[i]=v&0xffffffff
 else:m.write_words(GADDR[i],[v])
def snapshot():return (bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+struct.pack('<20I',*gv())
def blob(p,n):return C.string_at(p,n)if native else bytes(u.mem_read(p,n))
def writebuf(p,v):
 data=struct.pack('<'+'I'*len(v),*v)
 if native:C.memmove(p,data,len(data))
 else:u.mem_write(p,data)
def string(t):
 if native:return C.string_at(C.addressof(heap)+t-BASE).decode('ascii')
 return bytes(u.mem_read(t,256)).split(b'\0')[0].decode('ascii')
def effect(fn,receiver,args,buffers):
 global receiveIndex
 payload=()
 if fn in(0x546890,0x546d30):payload=(blob(buffers[0],args[4]+1)if fn==0x546890 else blob(buffers[0],512).split(b'\0')[0]+b'\0',)
 if fn==0x4226b0:payload=(blob(buffers[0],16),)
 if fn==0x546d30:payload+=(blob(buffers[1],16),)
 if fn in(0x4e0d70,0x477790):payload=(struct.pack('<5I',*gv()[8:13]),)
 if fn==0x4f6584 and receiver==0:payload=(blob(buffers[0],4),)
 if fn==0x4f6920:payload=(blob(buffers[0],4),)
 if fn==FRECEIVE:payload=tuple(blob(b,4)for b in buffers)
 events.append(((fn,receiver,tuple(args),payload),snapshot()))
 if fn==FQUERY:
  writebuf(buffers[0],[policy if policy in(1,2,3,4,5)else 0]);return 7 if policy==5 else 0
 if fn==FCOUNT:return 3 if policy!=8 else 1
 if fn==FSTATE:return 4 if policy in(2,3,4,5,6,7)else 1
 if fn==FGETDC:writebuf(buffers[0],[0 if policy==9 else 123]);return 0
 if fn==0x4226b0:return 1
 if fn in(FFONT,FRELEASE,0x546888,0x546880,0x546890,0x546d30):return 1
 if fn==FRECEIVE:
  writebuf(buffers[0],[words(PEER+4)[0]if receiveIndex%2==0 else 77]);writebuf(buffers[1],[42]);writebuf(buffers[2],[8+receiveIndex]);put(PACKET,[1001,100+receiveIndex]);receiveIndex+=1
  return 0x80001234 if policy==4 and receiveIndex==2 else 0
 if fn==0x477a10:
  if policy==3:put(PEER+4,[43]);put(PEER+0x1c,[24])
  return 1
 if fn==0x4e10d0:return 0
 if fn==0x422370:put(CFG+0xc,[words(CFG+0xc)[0]+1]);return 1
 if fn==0x4f6286:writebuf(buffers[0],[0 if policy==10 else RESOURCE]);return 1
 if fn==0x4b45f0:return 1
 if fn in(0x4e0d70,0x477790):
  if policy==11:put(OWNER+0xbfc,[17])
  return 1
 if fn==0x4f650f:put(receiver,[STRING]);return 0
 if fn==0x4f53eb:writebuf(buffers[0],[STRING]);put(receiver+0xc,[words(receiver+0xc)[0]-1]);return 0
 if fn==0x4f6584:return 0
 if fn==0x49c860:writebuf(buffers[0],[STRING]);return 0
 if fn==0x4f6920:return 0
 if fn==0x4a3920:
  fmt=bytes(u.mem_read(args[1],100)).split(b'\0')[0].decode('ascii');ints=[x if x<0x80000000 else x-0x100000000 for x in args[2:]];s=(fmt%tuple(ints)).encode()+b'\0'
  if native:C.memmove(buffers[0],s,len(s))
  else:u.mem_write(buffers[0],s)
  if policy==12:setg(3,gv()[3]|4)
  return len(s)-1
 raise AssertionError(('unknown service',hex(fn),hex(receiver),args))
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
@Dependency
def dependency(_,q,user):
 try:return effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]),list(q.buffers[:q.bufferCount]))
 except Exception as e:errors.append(e);return 0
host=Host(None,lookup,Allocate(),Free(),Invoke(),Clock());context=Context(host,C.pointer(globals),1,0)
# function -> (argument count, callee cleanup words, local argument mask,
# automatic receiver flag). COM methods explicitly receive their object on stack.
META={0x4226b0:(4,4,4,False),0x4e0d70:(4,4,0,False),0x477790:(3,3,0,False),0x477a10:(3,3,0,False),0x4e10d0:(4,0,0,False),0x422370:(2,2,0,False),0x4f6286:(2,2,2,False),0x4b45f0:(4,4,0,False),0x4f650f:(0,0,0,False),0x4f53eb:(1,1,1,False),0x4f6584:(0,0,0,True),0x49c860:(2,0,1,False),0x4f6920:(1,1,0,True),FSTATE:(0,0,0,False),FCOUNT:(0,0,0,False),FFONT:(1,1,0,False),FQUERY:(3,3,4,False),FRECEIVE:(6,6,38,False),FGETDC:(2,2,2,False),FRELEASE:(2,2,0,False),0x546888:(2,2,0,False),0x546880:(2,2,0,False),0x546890:(5,5,8,False),0x546d30:(5,5,10,False)}
def hook(uc,addr,size,user):
 fn=REVIMPORTS.get(addr,addr)
 if fn==0x4a3920:
  sp=uc.reg_read(UC_X86_REG_ESP);raw=m.read_words(sp+4,2);n={0x52a044:1,0x52a070:1,0x52a060:2,0x52a01c:3}[raw[1]];meta=(2+n,0,1,False)
 elif fn in META:meta=META[fn]
 else:return
 sp=uc.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];argc,pop,mask,localReceiver=meta;args=m.read_words(sp+4,argc);receiver=uc.reg_read(UC_X86_REG_ECX)
 if fn in REVIMPORTS.values() or fn in(0x49c860,0x4a3920,0x4e10d0,FQUERY,FRECEIVE,FGETDC,FRELEASE):receiver=0
 buffers=[]
 for i in range(argc):
  if mask&(1<<i):buffers.append(args[i]);args[i]=0
 if localReceiver:buffers.append(receiver);receiver=0
 if fn in(0x4e0d70,0x477790):buffers.append(0x53abc0)
 result=effect(fn,receiver,args,buffers);uc.reg_write(UC_X86_REG_EAX,result);uc.reg_write(UC_X86_REG_ESP,sp+4+4*pop);uc.reg_write(UC_X86_REG_EIP,ret)
u.hook_add(UC_HOOK_CODE,hook)
rng=random.Random(0x475dc0)
def setup(seed=0,flags=0):
 global native,receiveIndex
 native=True;receiveIndex=0;r=random.Random(seed);C.memmove(C.addressof(heap),r.randbytes(SIZE),SIZE)
 for t,n in((OWNER,770),(MGR,45),(CFG,13),(SCENE,12),(NET,35),(PEER,8)):put(t,[0]*n)
 put(OWNER,[VT]);put(VT+0x10,[FSTATE]);put(VT+0x50,[FCOUNT]);put(VT+0x64,[FFONT]);put(CVT+0x44,[FQUERY]);put(CVT+0x64,[FRECEIVE]);put(IVT+0x44,[FGETDC]);put(IVT+0x68,[FRELEASE]);put(COM,[CVT]);put(IFACE,[IVT]);put(OWNER+4,[MGR]);put(OWNER+0xc,[SCENE]);put(MGR+0x4c,[CFG]);put(MGR+0x30,[OTHER]);put(OTHER+8,[OTHERCONT]);put(OTHERCONT+0x1c,[123]);put(MGR+0x18,[60]);put(SCENE+4,[SURFACE]);put(SURFACE+0x14,[DRAW]);put(DRAW+0x2c,[BACKEND]);put(BACKEND+8,[IFACE]);put(SCENE+8,[CONT]);put(CONT+0x1c,[77]);put(SCENE+0x28,[SOUNDREG]);put(SOUNDREG+0x30,[0]);put(RESOURCE+0x10,[BASE+0x3c00]);put(OWNER+0x780,[NET,PEER]);put(NET+0x18,[COM]);put(NET+0x60,[3]);put(PEER+4,[42]);put(PEER+0x18,[PACKET,32]);put(PLAYER+0x6c,[LOGIC]);put(LOGIC+0x14,[PRIVATE]);put(PRIVATE,[0]);put(PLAYER+0x4c,[689,4730]);put(PLAYER+0xf8,[10]);put(OWNER+0x7ac,[1]);put(OWNER+0xbf0,[60000,25,10000,25,5,0]);put(OWNER+0xbc0,[5]);put(OWNER+0xbcc,[1]);put(CFG+0x24,[1000,500]);put(OWNER+0x794,[1]);put(NET+0x58,[NODES[0]])
 for i in range(5):
  put(NODES[i],[NODES[i+1]if i<4 else 0,0,ITEMS[i]]);put(ITEMS[i]+0x14,[ITEMS[i]+0x20]);put(ITEMS[i]+0x20,[ACTORS[i]]);put(ACTORS[i]+0xf8,[r.choice([0,1,2,2,3,0xffffffff])]);put(OWNER+0x7c0+4*i,[ITEMS[i]])
 C.memmove(C.addressof(heap)+STRING-BASE,b'01:02:03\0',9)
 globals.stageDelta=18;globals.playerToken=PLAYER;globals.accumulatedTick=3723000;globals.debugFlags=flags;globals.overlayRect[:]=[0,0,640,480];globals.posePacket[:]=[0]*5;globals.lastPose[:]=[0x80000000]*4;globals.rankingTimer=500;globals.audioEnabled=1;globals.overallVolume=87
 return bytes(heap),bytes(globals)
def load(h,g):
 global receiveIndex
 receiveIndex=0
 if native:C.memmove(heap,h,SIZE);C.memmove(C.byref(globals),g,len(g))
 else:u.mem_write(BASE,h);vals=struct.unpack('<20I',g);[m.write_words(a,[v])for a,v in zip(GADDR,vals)];m.write_words(0,[0x12345678])
def execute(fn,arg=0,receiver=None):
 global calls,eventCount
 receiver=receiver or(CFG if fn==0x4224f0 else OWNER)
 events.clear();errors.clear()
 if native:
  result=C.c_uint32();assert lib.claw_game_frame_service_entry(fn,receiver,arg,C.byref(context),dependency,None,C.byref(result));assert not context.fault,context.fault;assert not errors,errors;ret=result.value
 else:
  ret=m.call(fn,receiver,struct.pack('<I',arg)if fn in(0x4224f0,0x478290,0x46ca50)else b'');assert m.read_words(0,1)[0]==0x12345678
  assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+(4 if fn in(0x4224f0,0x478290,0x46ca50)else 0)
 calls+=1;eventCount+=len(events);return snapshot(),list(events),ret if fn in(0x477840,0x40af90,0x4750d0,0x4750e0,0x4bb030)else 0
def compare(fn,arg=0):
 global native
 native=True;h,g=bytes(heap),bytes(globals);load(h,g);a=execute(fn,arg);native=False;load(h,g);b=execute(fn,arg)
 assert a==b,(hex(fn),policy,arg, next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None),[(x[0],y[0])for x,y in zip(a[1],b[1])if x!=y][:2],a[2],b[2])
 native=True;load(a[0][:SIZE],a[0][SIZE:]);return a
