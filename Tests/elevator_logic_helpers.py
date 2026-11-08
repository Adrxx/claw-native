"""Whole original Elevator controllers with live, fully compared token heap."""
import ctypes as C,random,struct,subprocess,json,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/elevator-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/x)for x in('ElevatorLogicRuntime.cpp','WorldObjectRuntime.cpp','SpriteGeometry.cpp','ActorResourceBindings.cpp')],'-o',str(WORK/'libElevatorLogicRuntime.dylib')],check=True)
lib=C.CDLL(str(WORK/'libElevatorLogicRuntime.dylib'))
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','defaultsToken','playerToken','tick','animationDelta','wrapperMode')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*3),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_elevator_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_elevator_entry.restype=C.c_uint32
class ObjectState(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class ObjectContext(C.Structure):_fields_=[(n,C.c_uint32)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[(n,C.c_int32)for n in('worldWidth','worldHeight')]+[('registryToken',C.c_uint32),('layers',C.c_uint32*3)]+[(n,C.c_uint32)for n in('entryToken','entryCallback','entryFlags')]
class ObjectCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('text',C.c_char_p)]
ObjectDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(ObjectState),C.POINTER(ObjectContext),C.POINTER(ObjectCall),C.c_void_p)
class Info(C.Structure):_fields_=[('consumed',C.c_uint32),('created',C.c_uint32)]
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(ObjectState),C.POINTER(ObjectContext),ObjectDependency,C.c_void_p,C.POINTER(Info)];lib.claw_world_object_load.restype=C.c_uint32
class Geometry(C.Structure):_fields_=[(n,C.c_uint32)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surfaceToken','compressedToken','surfaceKind')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32]
BASE,SIZE=0x3000000,0x80000
A,L,SC,MANAGER,CONFIG,DEFAULTS,P,PL,PP,FRAME,IMAGE,ALTDEFAULTS,META=[BASE+i*0x1000 for i in range(1,14)]
GLOBAL_ADDRESSES=(0x5371fc,0x537960,0x537e88,0x537210,0x5430c4,0x53ebf0)
heap=(C.c_uint8*SIZE)();g=Globals();context=Context();native=True;events=[];policy=0;resourceFound=True;calls=event_count=0;loaderCalls=0;loadedProfile='Elevator';default_source='explicit fixture rectangle profile'
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(BASE,SIZE);u.mem_map(0,4096);m.executed.clear()
def words(t,n=1):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,values):
 b=struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def snap():return(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+(bytes(g)if native else b''.join(struct.pack('<I',m.read_words(t,1)[0])for t in GLOBAL_ADDRESSES))
def set_global(field,value):
 if native:setattr(g,field,value)
 else:m.write_words(GLOBAL_ADDRESSES[[n for n,_ in Globals._fields_].index(field)],[value])
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if BASE<=t and t+n*4<=BASE+SIZE else None
host=Host(None,lookup,Allocate(),Free(),Invoke(),Clock());context.scene=host

def effect(token):
 if policy==1:put(A+0x170,[0xfeed1234]);put(L+0x10,[0x49e810])
 if policy==2:set_global('defaultsToken',ALTDEFAULTS)
 if policy==3:put(A+0x148,[321]);put(A+0x110,[8]);put(PP+0x80,[123])
 return IMAGE if resourceFound else 0
@Dependency
def dependency(_,e,user):
 e=e.contents;events.append(((e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name),snap()));assert e.function==0x4f6286;return effect(e.arguments[0])
def returned(pop,value):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def original_hook(uc,address,size,user):
 if address!=0x4f6286:return
 sp=u.reg_read(UC_X86_REG_ESP);token,out=m.read_words(sp+4,2);name=bytes(u.mem_read(token,100)).split(b'\0')[0];events.append(((address,u.reg_read(UC_X86_REG_ECX),(token,),name),snap()));value=effect(token);m.write_words(out,[value]);returned(8,int(bool(value)))
u.hook_add(UC_HOOK_CODE,original_hook)
def setup(seed=0):
 global heap,g,context,native,policy,resourceFound
 native=True;heap=(C.c_uint8*SIZE).from_buffer_copy(random.Random(seed).randbytes(SIZE));g=Globals(MANAGER,DEFAULTS,P,0,16,0xdeadbeef);context=Context(host,C.pointer(g),0);policy=0;resourceFound=True
 put(A+0xc,[SC]);put(A+0x6c,[L]);put(A+0x170,[IMAGE,FRAME]);put(A+0x164,[0]);put(A+0x110,[0]);put(A+0x4c,[100,200]);put(A+0xe8,[100,200]);put(A+0x64,[0]);put(A+0x148,[125,125]);put(L+0x1c,[0]);put(L+0x10,[0x49e2a0]);put(L+0x2c,[0,200,0,400]);put(L+0xc8,[0,0]);put(P+8,[0]);put(P+0x80,[A]);put(P+0x6c,[PL]);put(PL+0x14,[PP]);put(PP+0x80,[7]);put(SC+0x10,[BASE+0xe000]);put(MANAGER+0x2c,[CONFIG]);put(CONFIG+0x14,[1]);put(FRAME+0x18,[32,8,0,0]);put(DEFAULTS+0x68,[-30,-4,30,4]);put(DEFAULTS+0x88,[-20,-6,20,6]);put(DEFAULTS+0x98,[-10,-8,10,8]);put(ALTDEFAULTS+0x68,[-27,-3,27,3]);put(ALTDEFAULTS+0x88,[-17,-5,17,5]);put(ALTDEFAULTS+0x98,[-7,-7,7,7])
def compare(f,label,args=None,fault_expected=False):
 global native,calls,event_count
 native=True;before,bg=bytes(heap),bytes(g);events.clear();context.fault=0;result=C.c_uint32();arguments=tuple(args if args is not None else(A,));argv=(C.c_uint32*len(arguments))(*(v&0xffffffff for v in arguments));assert lib.claw_elevator_entry(f,0,argv,len(arguments),C.byref(context),dependency,None,C.byref(result))
 assert bool(context.fault)==fault_expected,(label,'native fault',context.fault);expected,ee=snap(),list(events);afterHeap,afterGlobals=bytes(heap),bytes(g);native=False;events.clear();u.mem_write(BASE,before)
 for token,value in zip(GLOBAL_ADDRESSES,struct.unpack('<6I',bg)):m.write_words(token,[value])
 failed=False;ret=None
 try:ret=m.call(f,0,struct.pack('<'+'I'*len(arguments),*(v&0xffffffff for v in arguments)))
 except Exception:
  failed=True
  if not fault_expected:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault_expected,(label,'original fault',failed)
 actual=snap()
 if actual!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(struct.unpack('<'+'I'*(len(expected)//4),expected),struct.unpack('<'+'I'*(len(actual)//4),actual)))if x!=y][:20]);raise AssertionError('full Elevator heap/globals')
 if events!=ee:
  for i,(x,y)in enumerate(zip(ee,events)):
   if x!=y:print(label,'event',i,x[0],y[0],x[1]==y[1]);break
  raise AssertionError(('ordered full events',label,len(ee),len(events)))
 if not failed and f not in(0x49e060,0x49e1c0):assert ret==result.value==1,(label,'EAX',ret,result.value)
 if not failed:assert u.reg_read(UC_X86_REG_ESP)==m.stack+4,(label,'cdecl cleanup')
 native=True;C.memmove(C.addressof(heap),afterHeap,SIZE);C.memmove(C.addressof(g),afterGlobals,24);calls+=1;event_count+=len(ee);return result.value
@ObjectDependency
def object_dependency(s,c,e,_):
 e=e.contents
 if e.function==0x4f6286:return META
 if e.function in(0x4c7970,0x4c7900):s.contents.actor[0x170//4]=IMAGE;s.contents.actor[0x174//4]=FRAME;s.contents.actor[0x16c//4]=1
 return 1
callbacks={'Elevator':0x49e2a0,'StartElevator':0x49daf0,'TriggerElevator':0x49db10}
def records():
 raw=(ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
 if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
 out=[]
 for plane in range(struct.unpack_from('<I',raw,732)[0]):
  ph=struct.unpack_from('<40I',raw,offset+plane*160);pos=ph[35]
  for index in range(ph[32]):
   w=struct.unpack_from('<71I',raw,pos);end=pos+284+sum(w[1:5]);start=pos+284+w[1];kind=raw[start:start+w[2]].split(b'\0')[0].decode()
   if kind in callbacks:out.append((kind,index,raw[pos:end]))
   pos=end
 return out

def record_profile(kind,data):
 global loaderCalls
 s=ObjectState((C.c_uint32*128)(*words(A,128)),(C.c_uint32*93)(*words(L,93)));c=ObjectContext(SC,A,L,2,24576,6144,BASE+0xf000,(C.c_uint32*3)(BASE+0x10000,BASE+0x11000,BASE+0x12000),META,callbacks[kind],1);buf=(C.c_uint8*len(data)).from_buffer_copy(data);info=Info()
 assert lib.claw_world_object_load(buf,len(data),C.byref(s),C.byref(c),object_dependency,None,C.byref(info))==len(data)and info.created==1;put(A,list(s.actor));put(L,list(s.logic));loaderCalls+=1
 # Actual retail PID image geometry. File transport is explicit; frozen source
 # geometry constructor interprets dimensions/hotspots without raster decoding.
 data=(ROOT/'Original/cd-assets/LEVEL1/IMAGES/ELEVATORS/1.PID').read_bytes();signature,flags,w,h,x,y=struct.unpack_from('<6I',data);geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),w,h,x,y);put(FRAME+0x10,[geometry.width,geometry.height,geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY]);return s,c

class LevelProfile(C.Structure):_fields_=[('words',C.c_uint32*48),('selectedToken',C.c_uint32),('levelWord',C.c_uint32),('scaleWords',C.c_uint32*3)]
SetRect=C.CFUNCTYPE(C.c_uint32,C.POINTER(LevelProfile),C.c_uint32,C.POINTER(C.c_uint32),C.c_void_p)
lib.claw_elevator_initialize_profile.argtypes=[C.c_uint32,C.POINTER(LevelProfile),SetRect,C.c_void_p];lib.claw_elevator_initialize_profile.restype=C.c_uint32
levelProfile=LevelProfile();profilePolicy=0;profileEvents=[];profile_calls=profile_events=0;profilePhase=False
def profile_snapshot():return bytes(levelProfile)if native else bytes(u.mem_read(0x5378a0,192))+struct.pack('<2I',m.read_words(0x537960,1)[0],m.read_words(0x537964,1)[0])+bytes(u.mem_read(0x5262b0,12))
def profile_rect_effect(offset,values):
 if profilePolicy==1:
  if native:levelProfile.words[0]^=0xfeed;levelProfile.words[17]^=0xf00d;levelProfile.selectedToken^=0x100
  else:m.write_words(0x5378a0,[m.read_words(0x5378a0,1)[0]^0xfeed]);m.write_words(0x5378a0+0x44,[m.read_words(0x5378a0+0x44,1)[0]^0xf00d]);m.write_words(0x537960,[m.read_words(0x537960,1)[0]^0x100])
 if profilePolicy==2:return 0
 if native:levelProfile.words[offset//4:offset//4+4]=values
 else:m.write_words(0x5378a0+offset,values)
 return 1
@SetRect
def set_rect(_,offset,values,user):
 values=tuple(values[:4]);profileEvents.append(((0x546d5c,0x5378a0+offset,values),profile_snapshot()));return profile_rect_effect(offset,values)
u.mem_map(0x4000000,4096);m.write_words(0x546d5c,[0x4000000])
def profile_hook(uc,address,size,user):
 if address!=0x4000000 or not profilePhase:return
 sp=u.reg_read(UC_X86_REG_ESP);destination,*values=m.read_words(sp+4,5);profileEvents.append(((0x546d5c,destination,tuple(values)),profile_snapshot()));returned(20,profile_rect_effect(destination-0x5378a0,tuple(values)))
u.hook_add(UC_HOOK_CODE,profile_hook)
def compare_profile(level,label):
 global native,profilePhase,profile_calls,profile_events
 native=True;before=bytes(levelProfile);profileEvents.clear();result=lib.claw_elevator_initialize_profile(level&0xffffffff,C.byref(levelProfile),set_rect,None);expected,ee=profile_snapshot(),list(profileEvents);after=bytes(levelProfile);old=LevelProfile.from_buffer_copy(before)
 u.mem_write(0x5378a0,bytes(old.words));m.write_words(0x537960,[old.selectedToken]);m.write_words(0x537964,[old.levelWord]);m.write_words(0x5262b0,old.scaleWords);native=False;profilePhase=True;profileEvents.clear()
 try:original=m.call(0x452b00,0,struct.pack('<I',level&0xffffffff))
 finally:profilePhase=False
 assert original==result and profile_snapshot()==expected,(label,'whole profile result/state',original,result)
 assert profileEvents==ee,(label,'ordered complete profile SetRect snapshots')
 native=True;C.memmove(C.addressof(levelProfile),after,len(after));profile_calls+=1;profile_events+=len(ee);return result
def source_defaults(level=1):
 lib.claw_elevator_initialize_profile(level,C.byref(levelProfile),SetRect(),None);put(DEFAULTS,list(levelProfile.words));return levelProfile
