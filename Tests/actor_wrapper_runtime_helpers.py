"""Full-state oracle for the six additive actor/resource wrappers."""
import ctypes as C,random,struct,json,subprocess,hashlib
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/actor-wrapper-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/ActorWrapperRuntime.cpp'),str(ROOT/'Sources/SpriteGeometry.cpp'),'-o',str(WORK/'libActorWrapperRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32);Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32);Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure):_fields_=[('scene',Host),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*2),('localMask',C.c_uint32),('output',C.POINTER(C.c_uint32))]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
class Geometry(C.Structure):_fields_=[(n,C.c_uint32)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surfaceToken','compressedToken','surfaceKind')]
BASE,SIZE=0x3000000,0x20000
A,F,ROOTIMAGE,TABLE,WRAPPER,SC,REG,NAME,OUTER=[BASE+i*0x1000 for i in range(1,10)]
heap=(C.c_uint8*SIZE)();native=True;events=[];calls=eventCount=0;deniedToken=0;policy=0;output=0;dictionaryBool=1;legacy=False
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(BASE,SIZE);u.mem_map(0,4096);m.executed.clear()
lib=C.CDLL(str(WORK/'libActorWrapperRuntime.dylib'));lib.claw_actor_wrapper_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_actor_wrapper_entry.restype=C.c_uint32
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32]
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-BASE if t!=deniedToken and BASE<=t and t+n*4<=BASE+SIZE else None
def words(t,n=1):return list((C.c_uint32*n).from_address(C.addressof(heap)+t-BASE))if native else m.read_words(t,n)
def put(t,values):
 b=struct.pack('<'+'I'*len(values),*(x&0xffffffff for x in values))
 if native:C.memmove(C.addressof(heap)+t-BASE,b,len(b))
 else:u.mem_write(t,b)
def snapshot():return bytes(heap)if native else bytes(u.mem_read(BASE,SIZE))
def effect():
 if policy==1:put(A+0x170,[0]);put(A+0x174,[F+0x100])
 if policy==2:put(WRAPPER+4,[OUTER]);put(OUTER+12,[SC]);put(SC+0x2c,[REG+0x100])
 if policy==3:put(A+0x128,[0xfeed1234]*4)
 return output
@Dependency
def dependency(_,e,user):
 e=e.contents;events.append(((e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.localMask,e.output[0]),snapshot()));e.output[0]=effect();return dictionaryBool
@Invoke
def legacyCall(_,e):
 # Established SceneActorHost namedlookup returns the token, not dictionarybool.
 events.append(((e.function,e.receiver,(e.arguments[0],0),2,0),snapshot()));return effect()
ctx=Context(Host(None,lookup,Allocate(),Free(),legacyCall,Clock()),0)
def returned(pop,value):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(u,address,size,user):
 if address!=0x4f6286:return
 sp=u.reg_read(UC_X86_REG_ESP);name,out=m.read_words(sp+4,2);r=u.reg_read(UC_X86_REG_ECX);events.append(((address,r,(name,0),2,m.read_words(out,1)[0]),snapshot()));m.write_words(out,[effect()]);returned(8,dictionaryBool)
u.hook_add(UC_HOOK_CODE,hook)
def setup(seed=0):
 global native,heap,deniedToken,policy,output,dictionaryBool,legacy
 native=True;heap=(C.c_uint8*SIZE).from_buffer_copy(random.Random(seed).randbytes(SIZE));deniedToken=policy=0;output=F;dictionaryBool=1;legacy=False;ctx.fault=0
 put(A+0x174,[F]);put(A+0x170,[ROOTIMAGE]);put(ROOTIMAGE+0x14,[TABLE]);put(ROOTIMAGE+0x64,[-9,9]);put(WRAPPER+4,[A]);put(A+12,[SC]);put(SC+0x2c,[REG]);put(F+0x18,[16,4,-10,-20]);put(NAME,list(struct.unpack('<4I',b'CLAW_CYCLE100\0\0\0')))
 for i in range(-10,11):put(TABLE+i*4,[0 if i%3==0 else F+i*0x40])
def compare(f,t,args,label,fault=False):
 global native,calls,eventCount
 native=True;before=bytes(heap);events.clear();argv=(C.c_uint32*len(args))(*(v&0xffffffff for v in args));result=C.c_uint32();assert lib.claw_actor_wrapper_entry(f,t,argv,len(args),C.byref(ctx),Dependency()if legacy else dependency,None,C.byref(result));assert bool(ctx.fault)==fault,(label,'nativefault',ctx.fault);expected,ee=bytes(heap),list(events);native=False;events.clear();u.mem_write(BASE,before);failed=False
 try:ret=m.call(f,t,struct.pack('<'+'I'*len(args),*(v&0xffffffff for v in args)))
 except Exception:
  failed=True
  if not fault:print(label,'original fault',hex(u.reg_read(UC_X86_REG_EIP)));raise
 assert failed==fault,(label,'originalfault',failed)
 if snapshot()!=expected:
  print(label,'diff',[(hex(BASE+i*4),hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(SIZE//4),expected),m.read_words(BASE,SIZE//4)))if a!=b][:15]);raise AssertionError('full wrapper heap')
 assert events==ee,(label,'ordered full service snapshots',[(x[0],y[0])for x,y in zip(ee,events)if x!=y])
 if not failed and f in(0x4061b0,0x4062e0):assert ret==result.value,(label,'EAX',ret,result.value)
 if not failed:assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+{0x40f6c0:16,0x4209d0:4,0x4061b0:4,0x4062e0:4}.get(f,0),(label,'calling convention')
 native=True;C.memmove(C.addressof(heap),expected,SIZE);calls+=1;eventCount+=len(ee);return result.value
# Fault prefixes deliberately deny one exact source read/store in native and
# invalidate the same word in original with Unicorn protection. Exact heap
# snapshots exclude the four poisoned bytes themselves before/after the call.
import ast
nullSource=Path(__file__).with_name('special_command_helpers.py').read_text();nullTree=ast.parse(nullSource)
for node in nullTree.body:
 if isinstance(node,ast.FunctionDef)and node.name in('null_page_off','null_page_on'):exec(ast.get_source_segment(nullSource,node),globals())
def prefix(f,t,args,missing,label):
 global deniedToken,native
 deniedToken=missing
 # Poison the precise original memory load/store via a memory hook; stop before
 # that instruction rather than calling it an original safe fault/return.
 from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
 stopped=[False]
 def stop(u,access,address,size,value,user):
  if address<=missing<address+size:stopped[0]=True;u.emu_stop()
 handler=u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,stop);u.ctl_remove_cache(f,f+256);native=True;before=bytes(heap);events.clear();result=C.c_uint32();argv=(C.c_uint32*len(args))(*args);assert lib.claw_actor_wrapper_entry(f,t,argv,len(args),C.byref(ctx),dependency,None,C.byref(result))and ctx.fault==1;expected,ee=bytes(heap),list(events);native=False;events.clear();u.mem_write(BASE,before)
 try:
  u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(args),*args));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,t);u.emu_start(f,m.stop,count=10000);assert stopped[0],label
 finally:u.hook_del(handler)
 # Unicorn commits a hooked write after emu_stop, so store faults use an
 # instruction-address stop in tests; only read failures use this helper.
 assert snapshot()==expected and events==ee,(label,'exact stopped original read prefix');native=True;C.memmove(C.addressof(heap),expected,SIZE);deniedToken=0
profiles=[];prefixCount=0

def fault_prefix(f,t,args,missing,label):
 global deniedToken,native,prefixCount
 prefix(f,t,args,missing,label);prefixCount+=1

def store_prefix(f,t,args,missing,instruction,label):
 global deniedToken,native,prefixCount
 deniedToken=missing;native=True;before=bytes(heap);events.clear();out=C.c_uint32();argv=(C.c_uint32*len(args))(*(x&0xffffffff for x in args));assert lib.claw_actor_wrapper_entry(f,t,argv,len(args),C.byref(ctx),dependency,None,C.byref(out))and ctx.fault==1;expected,ee=bytes(heap),list(events);native=False;events.clear();u.mem_write(BASE,before)
 def stop(u,address,size,user):
  if address==instruction:u.emu_stop()
 handler=u.hook_add(UC_HOOK_CODE,stop)
 try:
  u.mem_write(m.stack,struct.pack('<I',m.stop)+struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)));u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ECX,t);u.emu_start(f,m.stop,count=10000);assert u.reg_read(UC_X86_REG_EIP)==instruction
 finally:u.hook_del(handler)
 assert snapshot()==expected and events==ee,(label,'exact original stopped store prefix');native=True;C.memmove(C.addressof(heap),expected,SIZE);deniedToken=0;prefixCount+=1

def retail_images(kind):
 path=ROOT/'work/original-disc-assets/LEVEL1/IMAGES'/kind
 for file in sorted(path.glob('*.PID')):
  data=file.read_bytes();signature,flags,width,height,x,y=struct.unpack_from('<6I',data);geometry=Geometry();lib.claw_sprite_set_geometry(C.byref(geometry),width,height,x,y);frame=F+int(file.stem[-3:])*0x40;put(frame+0x10,[geometry.width,geometry.height,geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY]);index=int(file.stem[-3:]);put(TABLE+index*4,[frame]);profiles.append({'path':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'id':index,'geometry':[geometry.width,geometry.height,geometry.halfWidth,geometry.halfHeight,geometry.offsetX,geometry.offsetY]})
 return sorted(p['id']for p in profiles if '/'+kind+'/'in p['path'])
