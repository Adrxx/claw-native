#!/usr/bin/env python3
"""Original CRT/state bootstrap plus mutable trie/CString arrays and heap."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/state-registry-agent';WORK.mkdir(parents=True,exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Tests/logic_state_registry_test_helpers.cpp'),'-o',str(WORK/'libLogicStateRegistry.dylib')],check=True)
profile=json.loads((ROOT/'Tests/logic_state_registry_profile.json').read_text());specs=profile['constructors'];tokens=[x[2]for x in specs];HEAP,SIZE,META,SC,REG,VT,KEY=0x3000000,0x100000,0x10ff000,0x1001000,0x1002000,0x1003000,0x1010000
class Table(C.Structure):_fields_=[('token',C.c_uint32),('kind',C.c_uint32),('words',C.c_uint32*12)]
class Literal(C.Structure):_fields_=[('state',C.c_int32),('literalToken',C.c_uint32)]
class State(C.Structure):_fields_=[('nextId',C.c_uint32),('tableCount',C.c_uint32),('tables',Table*96),('literalCount',C.c_uint32),('literals',Literal*256),('errorGlobals',C.c_uint32*15)]
class Context(C.Structure):_fields_=[('heap',C.POINTER(C.c_uint8))]+[(n,C.c_uint32)for n in('heapBase','heapCapacity','heapUsed','emptyStringToken','metadataReceiverToken','metadataFunctionToken','errorLocation','fault')]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*4),('name',C.c_char_p)]
class View(C.Structure):_fields_=[('state',C.c_int32),('function',C.c_uint32),('nameToken',C.c_uint32),('literalToken',C.c_uint32),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(State),C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(WORK/'libLogicStateRegistry.dylib'))
lib.claw_logic_state_context_defaults.argtypes=[C.POINTER(State),C.POINTER(Context)]
for name in('initialize','bootstrap'):
 f=getattr(lib,'claw_logic_state_'+name);f.argtypes=[C.POINTER(State),C.POINTER(Context),Dependency,C.c_void_p];f.restype=C.c_uint32
lib.claw_logic_state_find_id.argtypes=[C.POINTER(State),C.POINTER(Context),C.c_char_p,Dependency,C.c_void_p];lib.claw_logic_state_find_id.restype=C.c_uint32
lib.claw_logic_state_register.argtypes=[C.POINTER(State),C.POINTER(Context),C.c_uint32,C.c_char_p,C.c_uint32,C.c_uint32,Dependency,C.c_void_p];lib.claw_logic_state_register.restype=C.c_uint32
lib.claw_logic_state_resolve.argtypes=[C.POINTER(State),C.POINTER(Context),C.c_uint32,C.c_int32,C.POINTER(View),Dependency,C.c_void_p];lib.claw_logic_state_resolve.restype=C.c_uint32
lib.claw_logic_state_test_assign.argtypes=[C.POINTER(State),C.POINTER(Context),C.c_uint32,C.c_char_p,Dependency,C.c_void_p];lib.claw_logic_state_test_assign.restype=C.c_uint32
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(HEAP,SIZE);m.executed.clear()
rng=random.Random(52712);state=State();heap=(C.c_uint8*SIZE)();context=Context(heap,HEAP,SIZE,0,0,REG,META,0,0);events=[];original_events=[];allocation_sizes={};cursor=0;total=0;event_total=0
for i,(f,k,t,args)in enumerate(specs):state.tables[i].token=t;state.tables[i].kind=1 if k==0x440ee0 else 2 if k==0x440f30 else 3
lib.claw_logic_state_context_defaults(C.byref(state),C.byref(context))
def native_snapshot():return (state.nextId,tuple(tuple(state.tables[i].words)for i in range(len(specs))),tuple(state.errorGlobals),hashlib.sha256(bytes(heap)).digest())
def original_snapshot():return (m.read_words(0x52712c,1)[0],tuple(tuple(m.read_words(t,12))for t in tokens),tuple(m.read_words(0x544b14,15)),hashlib.sha256(bytes(u.mem_read(HEAP,SIZE))).digest())
def text(a):return bytes(u.mem_read(a,1024)).split(b'\0',1)[0]
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);address=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,address)
def allocate(f,args,native):
 global cursor
 n=args[-1];token=HEAP+cursor;cursor+=(n+15)&~15;assert cursor<=SIZE
 if f==0x4a9070 and args[0]:
  ncopy=min(n,allocation_sizes[args[0]])
  if native:C.memmove(C.addressof(heap)+token-HEAP,C.addressof(heap)+args[0]-HEAP,ncopy)
  else:u.mem_write(token,bytes(u.mem_read(args[0],ncopy)))
 allocation_sizes[token]=n;return token
@Dependency
def dependency(s,c,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);events.append((event,native_snapshot()))
 if e.function in(0x4f63ec,0x4a48e0,0x4a9070):return allocate(e.function,event[2],True)
 return 0

atomic_events=[];atomic_total=0;runtime_events=[];runtime_result=1;APP,SCVT,TILEMAN,WINDOW,CLOSE,OPEN=0x1004000,0x1005000,0x1006000,0x1007000,0x10fd000,0x10fc000
def hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address in(CLOSE,OPEN,0x4bd090,0x42cab0,0x42c0b0):
  n,pop,result={CLOSE:(0,0,0),OPEN:(5,20,runtime_result),0x4bd090:(1,0,0),0x42cab0:(0,0,0),0x42c0b0:(1,4,0)}[address]
  runtime_events.append(((address,u.reg_read(UC_X86_REG_ECX),tuple(m.read_words(sp+4,n))),original_snapshot()))
  returned(pop,result);return
 if address==0x10fb000:
  token=m.read_words(sp+4,1)[0];value=(m.read_words(token,1)[0]-1)&0xffffffff;atomic_events.append(((address,(token,),value),original_snapshot()));m.write_words(token,[value]);returned(4,value);return
 if address==0x10fe000:returned(4,len(text(m.read_words(sp+4,1)[0])));return
 config={0x4f63ec:(1,0),0x4a48e0:(1,0),0x4a9070:(2,0),0x4f6428:(1,0),0x4a35f0:(1,0),0x4db4d0:(3,12),META:(3,12)}
 if address not in config:return
 n,pop=config[address];args=tuple(m.read_words(sp+4,n));receiver=u.reg_read(UC_X86_REG_ECX)if address in(META,0x4db4d0)else 0
 name=text(args[1])if address in(META,0x4db4d0)else None;event=(address,receiver,args,name);original_events.append((event,original_snapshot()))
 result=allocate(address,args,False)if address in(0x4f63ec,0x4a48e0,0x4a9070)else 0;returned(pop,result)
u.hook_add(UC_HOOK_CODE,hook)
def install(before,old_heap):
 for i,t in enumerate(tokens):m.write_words(t,before.tables[i].words)
 m.write_words(0x52712c,[before.nextId]);m.write_words(0x544b14,before.errorGlobals);u.mem_write(HEAP,old_heap);m.write_words(0,[0x12345678]);m.write_words(0x5469e4,[0x10fe000,0x10fb000]);m.write_words(SC+0x14,[REG]);m.write_words(REG,[VT]);m.write_words(VT+0x24,[META])
def check(kind,label,*args):
 global cursor,allocation_sizes,total,event_total,runtime_result,atomic_total
 before=State.from_buffer_copy(bytes(state));old_heap=bytes(heap);old_cursor=cursor;old_sizes=dict(allocation_sizes);events.clear();view=View()
 if kind=='runtime':
  present,previous,desired,success,flags=args;result=lib.claw_logic_state_bootstrap(C.byref(state),C.byref(context),dependency,None)if present and previous!=desired and desired in(8,16)and success else 0
 elif kind=='initialize':result=lib.claw_logic_state_initialize(C.byref(state),C.byref(context),dependency,None)
 elif kind=='bootstrap':result=lib.claw_logic_state_bootstrap(C.byref(state),C.byref(context),dependency,None)
 elif kind=='assign':result=lib.claw_logic_state_test_assign(C.byref(state),C.byref(context),args[0],args[1],dependency,None)
 elif kind=='find':result=lib.claw_logic_state_find_id(C.byref(state),C.byref(context),args[0],dependency,None)
 elif kind=='register':result=lib.claw_logic_state_register(C.byref(state),C.byref(context),args[0],args[1],args[2],args[3],dependency,None)
 elif kind=='resolve':result=lib.claw_logic_state_resolve(C.byref(state),C.byref(context),args[0],args[1],C.byref(view),dependency,None)
 assert not context.fault,(label,'native fault',context.fault)
 expected=native_snapshot();expected_heap=bytes(heap);expected_events=list(events);new_cursor=cursor;new_sizes=dict(allocation_sizes)
 install(before,old_heap);cursor=old_cursor;allocation_sizes=old_sizes;original_events.clear();atomic_events.clear()
 if kind=='runtime':
  present,previous,desired,success,flags=args;runtime_result=success;runtime_events.clear()
  m.write_words(APP+4,[WINDOW]);m.write_words(APP+0x30,[SC if present else 0,0]);m.write_words(APP+0x5c,[0]);m.write_words(APP+0x78,[previous]);m.write_words(WINDOW+4,[0x12345678]);m.write_words(SC,[SCVT]);m.write_words(SC+0x24,[TILEMAN]);m.write_words(SCVT+0x18,[OPEN,CLOSE]);m.write_words(0x537234,[flags])
  value=m.call(0x42ce90,APP,struct.pack('<I',desired))
  assert value==(1 if present and previous==desired else 0),(label,'runtime return',value)
  if present and previous!=desired and desired in(8,16):
   expected_calls=[(CLOSE,SC,()),(OPEN,SC,(0x12345678,640,480,desired,5 if flags else 1))]
   expected_calls+= [(0x4bd090,SC,(0x428bc0,)),(0x42cab0,APP,())]if success else [(0x42c0b0,APP,(0x3ea,))]
   assert [x[0]for x in runtime_events]==expected_calls,(label,'runtime ordered services',runtime_events)
   if success:assert m.read_words(TILEMAN+0x64,2)==[14,14]
  else:assert not runtime_events
 elif kind=='initialize':
  for f,k,t,values in specs:m.call(f,0,b'')
 elif kind=='bootstrap':m.call(0x401000,0,struct.pack('<I',SC))
 elif kind=='assign':
  u.mem_write(KEY,args[1]+b'\0');m.call(0x4f66cc,args[0],struct.pack('<I',KEY));assert m.read_words(args[0],1)[0]==result,(label,'CString pointer')
 elif kind=='find':
  if args[0]is not None:u.mem_write(KEY,args[0]+b'\0')
  ret=m.call(0x4dba00,0x537668,struct.pack('<I',KEY if args[0]is not None else 0));assert ret==result,(label,'find return',ret,result)
 elif kind=='resolve':
  id=args[1];namesSlot=m.call(0x441030,0x537698,struct.pack('<I',id&0xffffffff));ptr,count=m.read_words(0x537698+0x1c,2)
  for n in range(count):m.call(0x4f6439,ptr+n*4,b'')
  token=m.read_words(namesSlot,1)[0];assert view.nameToken==token and view.name==text(token),(label,'name view')
  if args[0]:slot=m.call(0x441030,args[0],struct.pack('<I',id&0xffffffff));assert view.function==m.read_words(slot,1)[0]
 elif kind=='register':
  table,name,literal,function=args;u.mem_write(KEY,name+b'\0');id=m.call(0x4dba00,0x537668,struct.pack('<I',KEY))
  if not id:
   id=m.read_words(0x52712c,1)[0];m.call(0x4db7f0,0x537668,struct.pack('<2I',KEY,id));slot=m.call(0x441030,0x537698,struct.pack('<I',id));ptr,count=m.read_words(0x537698+0x1c,2)
   for n in range(count):m.call(0x4f6439,ptr+n*4,b'')
   m.call(0x4f66cc,slot,struct.pack('<I',KEY));m.write_words(0x52712c,[(id+1)&0xffffffff])
  slot=m.call(0x441030,table,struct.pack('<I',id));m.write_words(slot,[function]);assert id==result
 actual=original_snapshot()
 if expected!=actual:
  for i,t in enumerate(tokens):
   diffs=[(n*4,hex(a),hex(b))for n,(a,b)in enumerate(zip(state.tables[i].words,m.read_words(t,12)))if a!=b]
   if diffs:print(label,'table',hex(t),diffs)
  if expected_heap!=bytes(u.mem_read(HEAP,SIZE)):
   diffs=[(hex(HEAP+i),a,b)for i,(a,b)in enumerate(zip(expected_heap,bytes(u.mem_read(HEAP,SIZE))))if a!=b];print(label,'heap',diffs[:20])
  print('GLOBALS',expected[0],actual[0],expected[2],actual[2]);raise AssertionError((label,'complete raw objects/heap mismatch'))
 if expected_events!=original_events:
  print('Event count',len(expected_events),len(original_events))
  for i,(a,b)in enumerate(zip(expected_events,original_events)):
   if a!=b:print('EVENT',label,i,a[0],b[0],'snap equal',a[1]==b[1]);break
  raise AssertionError((label,'ordered full heap snapshots mismatch'))
 if kind=='assign':
  ptr=struct.unpack_from('<I',old_heap,args[0]-HEAP)[0];refs,length,capacity=struct.unpack_from('<3i',old_heap,ptr-12-HEAP)
  expected_atomic=[]
  if ptr!=context.emptyStringToken and (refs>1 or capacity<len(args[1])):
   expected_atomic=[((0x10fb000,(ptr-12,),(refs-1)&0xffffffff),(before.nextId,tuple(tuple(before.tables[i].words)for i in range(len(specs))),tuple(before.errorGlobals),hashlib.sha256(old_heap).digest()))]
  assert atomic_events==expected_atomic,(label,'exact atomic decrement arguments/buffer snapshot')
 else:assert not atomic_events,(label,'unexpected atomic service')
 atomic_total+=len(atomic_events)
 assert cursor==new_cursor and allocation_sizes==new_sizes and m.read_words(0,1)==[0x12345678]
 cursor=new_cursor;allocation_sizes=new_sizes;total+=1;event_total+=len(events)
 return view if kind=='resolve'else result
def reset_profile(seed):
 global state,heap,context,cursor,allocation_sizes
 state=State();heap=(C.c_uint8*SIZE)();context=Context(heap,HEAP,SIZE,0,0,REG,META,0,0);cursor=0;allocation_sizes={}
 if seed:
  rng=random.Random(seed);C.memmove(heap,rng.randbytes(SIZE),SIZE);raw={}
  for i,(f,k,t,args)in enumerate(specs):
   for n in range(12):raw.setdefault(t+n*4,rng.getrandbits(32))
  for i,(f,k,t,args)in enumerate(specs):state.tables[i].words[:]=[raw[t+n*4]for n in range(12)]
 for i,(f,k,t,args)in enumerate(specs):state.tables[i].token=t;state.tables[i].kind=1 if k==0x440ee0 else 2 if k==0x440f30 else 3
 lib.claw_logic_state_context_defaults(C.byref(state),C.byref(context))
def native_arena_check(before,old_heap):
 arena=(C.c_uint8*SIZE).from_buffer_copy(old_heap);live=State.from_buffer_copy(bytes(before));c=Context(arena,HEAP,SIZE,0,0,REG,META,0,0)
 assert lib.claw_logic_state_initialize(C.byref(live),C.byref(c),Dependency(),None)==1
 assert lib.claw_logic_state_bootstrap(C.byref(live),C.byref(c),Dependency(),None)==1 and not c.fault
 assert bytes(live)==bytes(state) and bytes(arena)==bytes(heap) and c.heapUsed==cursor,'native bounded arena disagrees with original-service allocator profile'
if __name__=='__main__':
 for seed in(0,52712,401000):
  reset_profile(seed);before=State.from_buffer_copy(bytes(state));old_heap=bytes(heap)
  check('initialize',('actual PE CRT registry constructor order',seed));print('PASS exact CRT raw objects/heap/events seed',seed,flush=True)
  check('bootstrap',('whole401000',seed));print('PASS whole401000 full raw trie/CStrings/class tables/heap/events',state.nextId,flush=True)
  native_arena_check(before,old_heap)
  if not seed:
   for case in[(0,0,8,1,0),(1,8,8,1,0),(1,0,7,1,0),(1,0,8,0,0),(1,0,8,1,0),(1,0,16,1,1)]:check('runtime',('actual runtime42ce90',case),*case)
   print('PASS actual runtime registration caller: absent/same/invalid/failure/modes8+16',flush=True)
  check('bootstrap',('whole401000 repeated aliases',seed))
  assert check('find','null lookup dependency ABI',None)==0
  for id,name in profile['names']:assert check('find',('boot-name',id),name.encode())==id
  for id,literal,name in profile['introductions']:
   view=check('resolve',('original canonical identity',id),0,id);assert view.literalToken==literal and view.nameToken!=literal and view.name==name.encode()
  for name in(b'',b'LS',b'LS_HOME_MORE',b'ls_idle',b'LS_NOT_REGISTERED',b'\x80',b'\xff\xfe'):assert check('find',('missing',name),name)==0
  for token in(0,0x537638,0x537878,0x537ba0,0x53c0e8,0x53c118,0x538428):
   for id in(1000,999,0,-1,1999,2000,2001,2002,2006,2007,2018,2030,2118,2200):check('resolve',('resolved',token,id),token,id)
  names=[('LS_CUSTOM_%02d'%n).encode()for n in range(40)]+[b'',b'L',b'LS_',b'LS_H',b'LS_HO',b'LS_HOME_MORE',b'\x80',b'\xff\xfe',b'A'*127,b'A'*126+b'B']
  for n,name in enumerate(names):
   literal=0x11000000+n*16;function=0x440000+n*16;id=state.nextId
   check('register',('new',seed,n),0x53c0e8,name,literal,function)
   assert check('find',('new-found',seed,n),name)==id
   check('register',('alias',seed,n),0x53c118,name,literal+1,function+1)
   view=check('resolve',('canonical-literal',seed,n),0x53c118,id);assert view.literalToken==literal and view.function==function+1
  for refs in(-2,-1,0,1,2,3,0x7fffffff):
   for capacity in(0,1,8,32):
    for value in(b'',b'Z',b'LS_COW_STRING'):
     cell,base=HEAP+SIZE-256,HEAP+SIZE-128
     C.memmove(C.addressof(heap)+cell-HEAP,struct.pack('<I',base+12),4)
     C.memmove(C.addressof(heap)+base-HEAP,struct.pack('<3I',refs&0xffffffff,capacity,capacity)+b'x'*capacity+b'\0',13+capacity)
     check('assign',('CString retained/COW',seed,refs,capacity,value),cell,value)
  print('PASS retained mutable/alias/empty/prefix/high-byte/CString histories seed',seed,flush=True)
 print('PASS',total,'complete original operations;',event_total,'ordered full raw object/heap snapshots;',atomic_total,'additional atomic argument/full-buffer snapshots;',len(m.executed),'original instruction addresses; three preserved-memory profiles, 84 CRT constructors each, native arena equivalence')
