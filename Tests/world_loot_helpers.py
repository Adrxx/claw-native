"""Private original-instruction oracle for world loot and host creation."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/world-loot-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f)for f in('WorldLootRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp')],'-o',str(WORK/'libWorldLootRuntime.dylib')],check=True)
class Globals(C.Structure):_fields_=[('words',C.c_uint32*341)]+[(n,C.c_uint32)for n in('itemCount','audioVolume','highLaunch','configurationWord')]
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host),('composeCreation',C.c_uint32),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*8),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Globals),C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x80000
INV,OWNER,SOURCE,SC,CT,IR,LR,SR,CFG,TLS,META=[BASE+0x1000+i*0x1000 for i in range(11)]
CALLBACK=0x40e690;GLOBALS_BASE=0x537ec8;profile=json.loads((ROOT/'Tests/world_loot_initializer_profile.json').read_text());rng=random.Random(42)
lib=C.CDLL(str(WORK/'libWorldLootRuntime.dylib'))
for name in('initialize','drop'):
 f=getattr(lib,'claw_world_loot_'+name);f.argtypes=[C.c_uint32,C.POINTER(Globals),C.POINTER(Context),Dependency,C.c_void_p];f.restype=C.c_uint32
lib.claw_world_loot_defaults.argtypes=[C.POINTER(Globals)];lib.claw_world_loot_name_token.argtypes=[C.c_int32,C.POINTER(Globals)];lib.claw_world_loot_name_token.restype=C.c_uint32
lib.claw_world_loot_next_random.argtypes=[C.POINTER(C.c_uint32)];lib.claw_world_loot_next_random.restype=C.c_uint32
lib.claw_world_loot_rebind_actor.argtypes=[C.c_uint32,C.c_int32,C.POINTER(Globals),C.POINTER(Context),Dependency,C.c_void_p];lib.claw_world_loot_rebind_actor.restype=C.c_uint32
class Create(C.Structure):_fields_=[(n,C.c_uint32)for n in('id','x','y','z','entryToken','flags')]
lib.claw_scene_actor_create_named.argtypes=[C.c_uint32,Create,C.c_uint32,Host,C.POINTER(C.c_uint32)];lib.claw_scene_actor_create_named.restype=C.c_uint32
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
# Original literal tokens and image-root inline strings are actual source
# identities. Synthetic resources/metadata are declared lookup service outputs.
strings={x['literal']:x['name'].encode()for x in profile['operations']if x['kind']==2};strings.update({0x522cc0:b'BouncingGoodie',0x5279b8:b'GAME_TREASURE_COINS'})
static_strings={token:C.create_string_buffer(text+b'\0\0\0\0')for token,text in strings.items()}
g=Globals();heap=(C.c_uint8*SIZE)();context=Context();native_events=[];original_events=[];native_tls=[];original_tls=[];tls_count=0;cursor=0x20000;actors=[];policy=0;callback_errors=[];calls=0;event_count=0;created_count=0
resource_keys=sorted({(x['registry'],x['literal'])for x in profile['operations']if x['kind']==2});resources={key:BASE+0x10000+i*0x100 for i,key in enumerate(resource_keys)}
def get(t,n=1,native=True):return list(struct.unpack_from('<'+'I'*n,bytes(heap),t-BASE))if native else m.read_words(t,n)
def put(t,values,native=True):
 b=struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def snapshot(native):return (tuple(g.words)if native else tuple(m.read_words(GLOBALS_BASE,341)),(g.itemCount,g.audioVolume,g.highLaunch,g.configurationWord)if native else(m.read_words(0x52a190,1)[0],m.read_words(0x532c10,1)[0],m.read_words(0x53721c,1)[0],get(CFG,1,False)[0]),hashlib.sha256(bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))).digest(),tuple(actors))
@Lookup
def lookup(user,t,n):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if t in static_strings:return C.addressof(static_strings[t])
 return None

def allocate_bytes(n,native):
 global cursor
 token=BASE+cursor;cursor+=max(0x400,(n+15)&~15);assert cursor<SIZE;return token
@Allocate
def allocate(user,n):native_events.append(((0x4f63ec,0,(n,),None),snapshot(True)));return allocate_bytes(n,True)
@Free
def free(user,t):native_events.append(((0x4f6428,0,(t,),None),snapshot(True)))
@Clock
def clock(user):return 0

def lookup_result(receiver,name,native):
 table={SR+16:0,LR+16:1,IR+16:2}[receiver]
 if name==0x522cc0:return META
 token=resources[(table,name)]
 return 0 if policy==2 and name%3==0 else token

def effects(event,native):
 global created_count
 fn,receiver,args,name=event
 if fn==0x4f6286:
  value=lookup_result(receiver,args[0],native)
  if policy==1 and args[0]==0x524d1c:
   if native:g.configurationWord=13;put(CFG,[13],True)
   else:put(CFG,[13],False)
  return value
 if fn==0x4208e0:
  if policy==3:put(INV+0x28,[2],native)
  return 0
 if fn==0x4c8da0:
  token=BASE+0x20000+created_count*0x1000;logic=token+0x400;created_count+=1;actors.append(token)
  # Explicit creator adapter effect, separate from composed real creator proof.
  put(token+4,[args[0],args[-1],SC],native);put(token+0x4c,args[1:3],native);put(token+0x64,[args[3]],native);put(token+0x6c,[logic],native);put(logic+0x10,[CALLBACK],native);put(logic+0x1c,[0],native);return token
 if fn==0x4c7970:
  if context.composeCreation and receiver not in actors:actors.append(receiver)
  # Resource service owns image selection. This finite effect deliberately
  # preserves unrelated fields and creates no pickup/gameplay stand-in.
  put(receiver+0x170,[args[0]-36,1,args[0]+256],native);return 0
 if fn==CALLBACK or fn==0x10fd000:
  actor=args[0];logic=get(actor+0x6c,native=native)[0];body=BASE+0x60000+actors.index(actor)*0x400 if actor in actors else BASE+0x60000
  put(logic+0x18,[body],native);put(logic+0x1c,[1000],native);put(body+0x28,[0x12345678,0x87654321],native)
  if policy==3:put(INV+0x24,[min(3,get(INV+0x24,native=native)[0]+1)],native)
  return 1
 return 0
@Dependency
def dependency(globals,ctx,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);native_events.append((event,snapshot(True)))
 try:
  if e.function==0x4a3050:
   native_tls.append(((0x4a7dc0,0,(),TLS),snapshot(True)))
   seed=C.cast(C.addressof(heap)+TLS+0x14-BASE,C.POINTER(C.c_uint32));return lib.claw_world_loot_next_random(seed)
  return effects(event,True)
 except BaseException as exc:callback_errors.append(exc);return 0
@Invoke
def invoke(user,e):
 event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),strings.get(e.arguments[0])if e.argumentCount and e.arguments[0]in strings else None)
 native_events.append((event,snapshot(True)));return effects(event,True)
scene=Host(None,lookup,allocate,free,invoke,clock);context.scene=scene

def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def text(t):return bytes(u.mem_read(t,128)).split(b'\0',1)[0]if t else None

def hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4a7dc0:original_tls.append(((address,0,(),TLS),snapshot(False)));returned(0,TLS);return
 if address==0x4a3050:original_events.append(((address,0,(),None),snapshot(False)));return
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);receiver=u.reg_read(UC_X86_REG_ECX);event=(address,receiver,(name,),text(name));original_events.append((event,snapshot(False)));result=effects(event,False);m.write_words(out,[result]);returned(8,int(bool(result)));return
 if address==0x4c8da0 and context.composeCreation:return
 config={0x4c8da0:(6,24),0x4c7970:(1,4),0x4208e0:(4,16),CALLBACK:(1,0),0x10fd000:(1,0),0x4f63ec:(1,0),0x4f6428:(1,0)}
 if address not in config:return
 n,pop=config[address];args=tuple(m.read_words(sp+4,n));receiver=0 if address in(CALLBACK,0x10fd000,0x4f63ec,0x4f6428)else u.reg_read(UC_X86_REG_ECX)
 name=text(args[4])if address==0x4c8da0 else text(args[0])if address==0x4c7970 and(BASE<=args[0]<BASE+SIZE or args[0]in strings)else None
 event=(address,receiver,args,name);original_events.append((event,snapshot(False)))
 result=allocate_bytes(args[0],False)if address==0x4f63ec else effects(event,False);returned(pop,result)
u.hook_add(UC_HOOK_CODE,hook)
def prepare(seed=None):
 global g,heap,cursor,actors,created_count,policy
 if seed is None:seed=rng.getrandbits(32)
 local=random.Random(seed);g=Globals();g.words[:]=[local.getrandbits(32)for _ in range(341)];lib.claw_world_loot_defaults(C.byref(g));g.configurationWord=local.choice([0,1,13,14]);heap=(C.c_uint8*SIZE).from_buffer_copy(local.randbytes(SIZE));cursor=0x20000;actors=[];created_count=0;policy=0;context.fault=0;context.composeCreation=0
 put(INV+8,[OWNER]);put(INV+0x20,[BASE+0x1f000,9,2]);put(INV+0x2c,[1,2,0,0,0,0,0,0,0]);put(INV+0x6c,[SOURCE]);put(OWNER+0xc,[SC]);put(SC+8,[CT]);put(SC+0x10,[IR,LR]);put(SC+0x24,[2,SR]);put(CT,[0x513c20,0,0,SC,0x5107bc,0,0,0,0,0,10]);put(SOURCE+0x4c,[local.randrange(-1000,1000),local.randrange(-1000,1000)]);put(SOURCE+0x100,[32 if seed%2 else 0]);put(SOURCE+0x148,[seed,seed^0x11223344]);put(SOURCE+0xfc,[seed^0xfedcba98]);put(CFG,[g.configurationWord]);put(TLS+0x14,[seed]);put(META,[0,0,0,0,CALLBACK])
 for (registry,literal),token in resources.items():
  put(token,[0]*9)
  if registry==1:put(token+0x10,[0x10fd000])
  name=strings[literal]+b'\0';C.memmove(C.addressof(heap)+token+0x24-BASE,name,len(name))
 for n in range(66):g.words[n]=resources[2,0x5279b8];g.words[208+n]=META
 return seed

def compare(kind,label,*args):
 global cursor,actors,created_count,calls,event_count,tls_count
 before=Globals.from_buffer_copy(bytes(g));old_heap=bytes(heap);old_cursor=cursor;old_actors=list(actors);old_created=created_count;native_events.clear();native_tls.clear();callback_errors.clear();context.fault=0
 if kind=='initialize':result=lib.claw_world_loot_initialize(SC,C.byref(g),C.byref(context),dependency,None)
 elif kind=='drop':result=lib.claw_world_loot_drop(INV,C.byref(g),C.byref(context),dependency,None)
 elif kind=='name':result=lib.claw_world_loot_name_token(args[0],C.byref(g))
 elif kind=='rebind':result=lib.claw_world_loot_rebind_actor(args[0],args[1],C.byref(g),C.byref(context),dependency,None)
 assert not context.fault and not callback_errors,(label,'native fault',context.fault,callback_errors)
 expected=snapshot(True);expected_events=list(native_events);expected_heap=bytes(heap);next_cursor=cursor;next_actors=list(actors);next_created=created_count
 cursor=old_cursor;actors=old_actors;created_count=old_created;u.mem_write(BASE,old_heap);m.write_words(GLOBALS_BASE,before.words);m.write_words(0x52a190,[before.itemCount]);m.write_words(0x532c10,[before.audioVolume]);m.write_words(0x53721c,[before.highLaunch]);m.write_words(0x537960,[CFG]);put(CFG,[before.configurationWord],False);m.write_words(0,[0x12345678]);original_events.clear();original_tls.clear()
 if kind=='initialize':m.call(0x4719e0,0,struct.pack('<I',SC));assert result==1
 elif kind=='drop':m.call(0x42df90,INV);assert result==1
 elif kind=='name':value=m.call(0x473630,0,struct.pack('<I',args[0]&0xffffffff));assert value==result
 elif kind=='rebind':value=m.call(0x473660,0,struct.pack('<2I',args[0],args[1]&0xffffffff));assert value==result
 if snapshot(False)!=expected:
  diffs=[(i,hex(a),hex(b))for i,(a,b)in enumerate(zip(g.words,m.read_words(GLOBALS_BASE,341)))if a!=b];print(label,'globals',diffs[:15])
  diffs=[(hex(BASE+i),a,b)for i,(a,b)in enumerate(zip(expected_heap,bytes(u.mem_read(BASE,SIZE))))if a!=b];print(label,'heap',diffs[:15]);raise AssertionError((label,'complete buffers'))
 if original_events!=expected_events:
  print(label,'events',len(expected_events),len(original_events))
  for i,(a,b)in enumerate(zip(expected_events,original_events)):
   if a!=b:print('EVENT',i,a[0],b[0],'snapshot',a[1]==b[1]);break
  raise AssertionError((label,'complete callback snapshots'))
 assert native_tls==original_tls,(label,'exact TLS arguments/return/full snapshots')
 tls_count+=len(native_tls)
 assert cursor==next_cursor and actors==next_actors and created_count==next_created and m.read_words(0,1)==[0x12345678]
 cursor=next_cursor;actors=next_actors;created_count=next_created;calls+=1;event_count+=len(native_events);return result
